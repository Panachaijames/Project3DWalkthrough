"""Saved furniture heights (DESIGN.md 9.4, 10.2). Bodies: builder E.

PUT replaces the saved map: every key a kind of the model, every value an integer 10 - 5000; values equal to the model's
height are dropped (canonical); revision + 1; last write wins.

If-Match (fix step, review finding "adversarial" 3: two tabs erased each other's heights): a PUT that sends
`If-Match: "<revision>"` is applied only when the saved heights are still at that revision (0 = nothing saved yet); else
412 revision_conflict, `details: {revision, heights}` = what is saved now, so the staff app merges its own changes into
them and sends again. Without the header a PUT still replaces whatever is saved (last write wins). The header is read
from the request, not declared as a parameter: the frozen OpenAPI document and the generated client do not move.
"""
from __future__ import annotations

import re

from fastapi import APIRouter, Depends, Request

from .. import views
from ..deps import get_store
from ..errors import ApiError
from ..models import HeightOverrides, HeightsUpdate
from ..store.base import RevisionConflict, Store
from .params import ProjectId, VersionNo, error

router = APIRouter()

_IF_MATCH = re.compile(r'\s*(?:W/)?"?(\d{1,9})"?\s*')


def if_match_revision(request: Request) -> int | None:
    """The revision an If-Match header names ('"3"', 'W/"3"' or '3'), None without the header; anything else (a list,
    '*', not a number) cannot match a revision: 412."""
    raw = request.headers.get('if-match')
    if raw is None:
        return None
    m = _IF_MATCH.fullmatch(raw)
    if not m:
        raise ApiError(412, 'revision_conflict', f'If-Match {raw!r} does not name a revision of the saved heights')
    return int(m.group(1))


@router.get(
    '/api/projects/{projectId}/versions/{version}/furniture-heights',
    operation_id='getFurnitureHeights',
    tags=['furniture'],
    response_model=HeightOverrides,
    responses={404: error('project_not_found, version_not_found, no_furniture')},
    summary='Get the saved furniture heights',
    description="The kinds whose saved height differs from the model's ({} / 0 / null when nothing was saved).",
    response_description='The saved heights.',
)
def get_furniture_heights(project_id: ProjectId, version: VersionNo, store: Store = Depends(get_store)) -> HeightOverrides:
    v = store.get_version(project_id, version)
    if not views.has_furniture(v):
        raise views.no_furniture(v)
    return views.overrides_of(store.read_overrides(project_id, version))


@router.put(
    '/api/projects/{projectId}/versions/{version}/furniture-heights',
    operation_id='putFurnitureHeights',
    tags=['furniture'],
    response_model=HeightOverrides,
    responses={
        404: error('project_not_found, version_not_found, no_furniture'),
        422: {
            'description': 'invalid_heights (ErrorResponse; details.unknownKinds, details.outOfRange), or a malformed '
                           "request (FastAPI's HTTPValidationError).",
            'content': {'application/json': {'schema': {'anyOf': [
                {'$ref': '#/components/schemas/ErrorResponse'},
                {'$ref': '#/components/schemas/HTTPValidationError'},
            ]}}},
        },
    },
    summary='Save the furniture heights',
    description="Replaces the saved map. Every key must be a kind of the model and every value a whole number of mm, "
                "10 - 5000; values equal to the model's height are dropped; revision + 1; last write wins.",
    response_description='The saved heights after the change.',
)
def put_furniture_heights(project_id: ProjectId, version: VersionNo, body: HeightsUpdate, request: Request,
                          store: Store = Depends(get_store)) -> HeightOverrides:
    v = store.get_version(project_id, version)
    if not views.has_furniture(v):
        raise views.no_furniture(v)
    heights = views.canonical_heights(views.model_of(store, v), body.heights)     # 422 invalid_heights
    expected = if_match_revision(request)
    try:
        saved = store.write_overrides(project_id, version, heights, if_revision=expected)
    except RevisionConflict as exc:
        now = views.overrides_of(exc.current)
        raise ApiError(412, 'revision_conflict', str(exc),
                       {'revision': now.revision, 'heights': now.heights, 'updatedAt': now.updated_at}) from exc
    return views.overrides_of(saved)
