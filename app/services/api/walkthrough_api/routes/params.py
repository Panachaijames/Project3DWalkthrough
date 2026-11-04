"""Path and header parameters shared by the routes (DESIGN.md 10.1) and the error responses they declare."""
from __future__ import annotations

from typing import Annotated, Any

from fastapi import Header, Path

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
