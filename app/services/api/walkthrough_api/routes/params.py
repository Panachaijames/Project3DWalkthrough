"""Path and header parameters shared by the routes (DESIGN.md 10.1) and the error responses they declare."""
from __future__ import annotations

from typing import Annotated, Any

from fastapi import Header, Path, Query

from ..models import ErrorResponse

PROJECT_ID_PATTERN = r'^[a-z0-9][a-z0-9-]{1,62}$'
FILE_NAME_PATTERN = r'^[A-Za-z0-9._-]{1,128}$'

ProjectId = Annotated[str, Path(alias='projectId', pattern=PROJECT_ID_PATTERN, description='Project id (kebab-case slug).')]
VersionNo = Annotated[int, Path(alias='version', ge=1, description='Version number, from 1.')]
FileName = Annotated[str, Path(alias='name', pattern=FILE_NAME_PATTERN, description='File name (no folders).')]
IfNoneMatch = Annotated[str | None, Header(alias='If-None-Match', description='An ETag from an earlier answer: 304 when it still matches.')]


def error(description: str) -> dict[str, Any]:
    """A declared domain error (ErrorResponse) for a route's `responses`."""
    return {'model': ErrorResponse, 'description': description}


NOT_MODIFIED: dict[str, Any] = {'description': 'Not modified: If-None-Match matched the ETag.'}

RAW_HEADERS: dict[str, Any] = {
    'ETag': {'description': 'The quoted sha1 of the bytes.', 'schema': {'type': 'string'}},
    'Cache-Control': {'description': 'no-cache', 'schema': {'type': 'string'}},
}

ATTACHMENT_HEADERS: dict[str, Any] = {
    'Content-Disposition': {
        'description': 'attachment; filename="<ascii>"; filename*=UTF-8\'\'<encoded>',
        'schema': {'type': 'string'},
    },
}


# ---------------------------------------------------------------------------- the upload milestone (scaffold U0, U-13.1)
UPLOAD_ID_PATTERN = r'^u[0-9a-f]{24}$'
BUILD_ID_PATTERN = r'^[0-9]{8}T[0-9]{6}-[0-9a-f]{6}$'
SHA1_PATTERN = r'^[0-9a-f]{40}$'

UploadId = Annotated[str, Path(alias='uploadId', pattern=UPLOAD_ID_PATTERN, description='Upload session id, u + 24 hex.')]
PartNo = Annotated[int, Path(alias='part', ge=1, le=10000, description='Part number, from 1 (partUrls[i] is part i + 1).')]
BuildId = Annotated[str, Path(alias='buildId', pattern=BUILD_ID_PATTERN, description='Build id, <yyyymmdd>T<hhmmss>-<6 hex>.')]
SourceSha1 = Annotated[str, Path(alias='sha1', pattern=SHA1_PATTERN, description="The source's sha1 (40 hex).")]
WithSettings = Annotated[bool, Query(alias='withSettings', description='false: settings is null in the answer (the 1 s '
                                                                       'poll asks without them, U-14.2).')]


def error_or_validation(description: str) -> dict[str, Any]:
    """A declared domain 422 (ErrorResponse) on a route whose malformed requests still get FastAPI's own 422
    (HTTPValidationError), as putFurnitureHeights declares it."""
    return {
        'description': f"{description} (ErrorResponse), or a malformed request (FastAPI's HTTPValidationError).",
        'content': {'application/json': {'schema': {'anyOf': [
            {'$ref': '#/components/schemas/ErrorResponse'},
            {'$ref': '#/components/schemas/HTTPValidationError'},
        ]}}},
    }
