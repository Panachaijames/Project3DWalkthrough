"""Uploads in raw 8 MiB parts (docs/upload/DESIGN.md U-5, U-13.1).

createUpload -> PUT each part to partUrls[i] (application/octet-stream) -> completeUpload -> a SourceFile. Every state
change is a PUT, a DELETE or a POST with a JSON body (even `{}`), so another origin cannot send one without a CORS
preflight (U-5.2). The body guard (main.py) answers 411 / 413 before a body is read (U-13.5).

Decorators frozen at the scaffold U0 (they are apps/web/openapi.json); U5 writes the bodies.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Body, Depends
from fastapi.responses import Response

from ..deps import get_settings, get_store
from ..drafts import uploads as drafts_uploads
from ..models_upload import CompleteUploadRequest, SourceFile, UploadPartResult, UploadRequest, UploadSession
from ..settings import Settings
from ..store.base import Store
from .params import PartNo, UploadId, error, error_or_validation

router = APIRouter()

PartBody = Annotated[bytes, Body(media_type='application/octet-stream',
                                 description='The bytes of the part: every part but the last exactly partBytes, the last '
                                             'the rest.')]


@router.post(
    '/api/uploads',
    operation_id='createUpload',
    tags=['uploads'],
    status_code=201,
    response_model=UploadSession,
    responses={
        404: error('project_not_found'),
        413: error('too_large: above WALKTHROUGH_UPLOAD_MAX_BYTES (300 MiB)'),
        422: error_or_validation('bad_kind: the name must end in .dwg or .dxf, be 1 - 255 characters and hold no control '
                                 'character'),
    },
    summary='Start an upload',
    description='Opens an upload session for one DWG or DXF file of a project: the file goes up in parts of partBytes '
                '(8 MiB) to partUrls, then completeUrl makes it a source. A session not completed within 24 h is removed.',
    response_description='The upload session.',
)
def create_upload(body: UploadRequest, store: Store = Depends(get_store),
                  settings: Settings = Depends(get_settings)) -> UploadSession:
    return drafts_uploads.create_upload(store, settings, body)


@router.get(
    '/api/uploads/{uploadId}',
    operation_id='getUpload',
    tags=['uploads'],
    response_model=UploadSession,
    responses={404: error('upload_not_found')},
    summary='Get an upload',
    description='An upload session with the parts received so far (to resume an upload after a page reload).',
    response_description='The upload session.',
)
def get_upload(upload_id: UploadId, store: Store = Depends(get_store)) -> UploadSession:
    return drafts_uploads.get_upload(store, upload_id)


@router.put(
    '/api/uploads/{uploadId}/parts/{part}',
    operation_id='putUploadPart',
    tags=['uploads'],
    response_model=UploadPartResult,
    responses={
        404: error('upload_not_found'),
        411: error('length_required: a part needs Content-Length (the body guard)'),
        413: error('part_too_large: above partBytes (the body guard)'),
        422: error_or_validation('bad_part: a part number past the last, or a size other than the part\'s'),
    },
    summary='Send one part of an upload',
    description='The bytes of part <part> (application/octet-stream). Idempotent: a part sent again replaces itself.',
    response_description='The part as stored.',
)
def put_upload_part(upload_id: UploadId, part: PartNo, body: PartBody, store: Store = Depends(get_store),
                    settings: Settings = Depends(get_settings)) -> UploadPartResult:
    return drafts_uploads.put_part(store, upload_id, part, body)


@router.post(
    '/api/uploads/{uploadId}/complete',
    operation_id='completeUpload',
    tags=['uploads'],
    status_code=201,
    response_model=SourceFile,
    responses={
        404: error('upload_not_found'),
        409: error('incomplete: parts are missing (details.missing)'),
        422: error_or_validation('bad_kind (not a DWG or DXF), unsupported_version (a DWG older than R13: save it as a '
                                 'newer DWG, or export a DXF)'),
    },
    summary='Complete an upload',
    description='Joins the parts, checks the first bytes (a DWG of R13 or newer, an ASCII or binary DXF) and stores the '
                'file as a source of the project, named by its sha1 (the same file uploaded twice is one source).',
    response_description='The stored source.',
)
def complete_upload(upload_id: UploadId, body: CompleteUploadRequest, store: Store = Depends(get_store),
                    settings: Settings = Depends(get_settings)) -> SourceFile:
    return drafts_uploads.complete(store, upload_id)


@router.delete(
    '/api/uploads/{uploadId}',
    operation_id='cancelUpload',
    tags=['uploads'],
    status_code=204,
    response_class=Response,
    responses={404: error('upload_not_found')},
    summary='Cancel an upload',
    description='Removes an upload session and the parts received.',
    response_description='The session is gone.',
)
def cancel_upload(upload_id: UploadId, store: Store = Depends(get_store)) -> Response:
    drafts_uploads.cancel(store, upload_id)
    return Response(status_code=204)
