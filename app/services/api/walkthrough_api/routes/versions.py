"""One version: its detail, model, stages and assets (DESIGN.md 10.2). Bodies: builder E. deleteVersion: the owner's
request of 12 Nov 2026 (docs/contract-issues/DEL.md; deletes.py).

Raw files are returned as stored with `ETag: "<sha1>"`, `Cache-Control: no-cache`; If-None-Match -> 304 (DESIGN.md 10.1).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import Response

from .. import deletes, views
from ..deps import get_jobs, get_store
from ..jobs.base import JobRunner
from ..jsonio import sha1_hex
from ..models import VersionDetail
from ..store.base import Store
from .params import NOT_MODIFIED, RAW_HEADERS, FileName, IfNoneMatch, ProjectId, VersionNo, error

router = APIRouter()

_JSON_OBJECT = {'type': 'object', 'additionalProperties': True}
_BINARY = {'type': 'string', 'format': 'binary'}


@router.get(
    '/api/projects/{projectId}/versions/{version}',
    operation_id='getVersion',
    tags=['versions'],
    response_model=VersionDetail,
    responses={404: error('project_not_found, version_not_found')},
    summary='Get a version',
    description='Everything the project page needs about one version: counts, floors, URLs of its files, assets, '
                'downloads, the presentation and the saved furniture heights.',
    response_description='The version.',
)
def get_version(project_id: ProjectId, version: VersionNo, store: Store = Depends(get_store)) -> VersionDetail:
    return views.version_detail(store, store.get_version(project_id, version))


@router.get(
    '/api/projects/{projectId}/versions/{version}/model',
    operation_id='getModel',
    tags=['versions'],
    response_class=Response,
    responses={
        200: {
            'content': {'application/json': {'schema': _JSON_OBJECT}},
            'headers': {**RAW_HEADERS, 'X-Model-Stamp': {'description': 'The 12-hex model-data stamp.', 'schema': {'type': 'string'}}},
        },
        304: NOT_MODIFIED,
        404: error('project_not_found, version_not_found'),
    },
    summary="Get a version's model",
    description='model.json as stored: BuiltModel v1 (built-model.schema.json).',
    response_description='The model (application/json).',
)
def get_model(project_id: ProjectId, version: VersionNo, if_none_match: IfNoneMatch = None,
              store: Store = Depends(get_store)) -> Response:
    v = store.get_version(project_id, version)
    data = views.model_bytes(store, v)                                   # 500 store_error when it is not the version's
    return views.raw_bytes(data, 'application/json', v.model_sha1, if_none_match, {'X-Model-Stamp': v.stamp})


@router.get(
    '/api/projects/{projectId}/versions/{version}/stages',
    operation_id='getStages',
    tags=['versions'],
    response_class=Response,
    responses={
        200: {'content': {'application/json': {'schema': _JSON_OBJECT}}, 'headers': RAW_HEADERS},
        304: NOT_MODIFIED,
        404: error('project_not_found, version_not_found, no_stages'),
    },
    summary="Get a version's build replay data",
    description='stages.json as stored: ReplayData v1. Versions without a build replay answer 404 no_stages.',
    response_description='The replay data (application/json).',
)
def get_stages(project_id: ProjectId, version: VersionNo, if_none_match: IfNoneMatch = None,
               store: Store = Depends(get_store)) -> Response:
    data = store.read_json_bytes(project_id, version, 'stages.json')     # NotFound('no_stages') for the hotel
    return views.raw_bytes(data, 'application/json', sha1_hex(data), if_none_match)


@router.get(
    '/api/projects/{projectId}/versions/{version}/assets/{name}',
    operation_id='getAsset',
    tags=['versions'],
    response_class=Response,
    responses={
        200: {'content': {'image/png': {'schema': _BINARY}, 'application/octet-stream': {'schema': _BINARY}},
              'headers': RAW_HEADERS},
        304: NOT_MODIFIED,
        404: error('project_not_found, version_not_found, asset_not_found'),
    },
    summary='Get an asset',
    description="A file of the version's assets (plan pictures, the thumbnail), as stored, with the media type from version.json.",
    response_description='The file.',
)
def get_asset(project_id: ProjectId, version: VersionNo, name: FileName, if_none_match: IfNoneMatch = None,
              store: Store = Depends(get_store)) -> Response:
    return views.raw_blob(store.asset(project_id, version, name), if_none_match)


# The owner's request of 12 Nov 2026 (docs/contract-issues/DEL.md): an additive route, authorised by the main session.
@router.delete(
    '/api/projects/{projectId}/versions/{version}',
    operation_id='deleteVersion',
    tags=['versions'],
    status_code=204,
    response_class=Response,
    responses={
        404: error('project_not_found, version_not_found'),
        409: error("only_version: it is the project's only version (delete the project instead); busy: a file reading "
                   'or a build of one of its drafts is queued or running (details.builds), or a file of the version is '
                   'in use; nothing was deleted'),
    },
    summary='Delete a version',
    description="Removes one version's files from this computer; the project's latest version becomes the highest one "
                'left. Version numbers are not reused: the next version saved gets a new number. The draft saved as '
                'this version goes with it. Refused for the only version and while a run of a draft is going. Cannot '
                'be undone.',
    response_description='The version is gone.',
)
def delete_version(project_id: ProjectId, version: VersionNo, store: Store = Depends(get_store),
                   jobs: JobRunner = Depends(get_jobs)) -> Response:
    deletes.delete_version(store, jobs, project_id, version)
    return Response(status_code=204)
