"""Saved furniture heights (DESIGN.md 9.4, 10.2). Bodies: builder E.

PUT replaces the saved map: every key a kind of the model, every value an integer 10 - 5000; values equal to the model's
height are dropped (canonical); revision + 1; last write wins.

If-Match (fix step, review finding "adversarial" 3: two tabs erased each other's heights): a PUT that sends
`If-Match: "<revision>"` is applied only when the saved heights are still at that revision (0 = nothing saved yet); else
412 revision_conflict, `details: {revision, heights}` = what is saved now, so the staff app merges its own changes into
them and sends again. Without the header a PUT still replaces whatever is saved (last write wins). The header is read
from the request, not declared as a parameter: the frozen OpenAPI document and the generated client do not move.

Deleted furniture boxes (step BX, 16 Nov 2026; docs/boxes/DESIGN.md 3.2, docs/contract-issues/BX.md): the same file,
revision and If-Match carry `pieceEdits` (piece id -> {removed: true}). A PUT that sends `pieceEdits` replaces the saved
edits (after the heights' checks: every key a piece of the model, else 422 invalid_piece_edits with details.unknownIds
(the first 20) and details.count; `removed: false` / {} dropped; closed: what stands on a removed piece goes with it;
in the CSV order); a PUT without it keeps them. Every answer, and the 412's details when there are any, carries the
LIVE map (piece_edits.live), never an id the model lacks. The route texts are frozen and still speak of heights only.
"""
from __future__ import annotations

import re

from fastapi import APIRouter, Depends, Request

from .. import piece_edits, views
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
    # the model is read only when piece edits are saved (their live map is taken against it)
    return views.overrides_of(store.read_overrides(project_id, version), lambda: views.model_of(store, v))


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
    model = views.model_of(store, v)
    heights = views.canonical_heights(model, body.heights)                          # 422 invalid_heights
    # sent: checked, closed and ordered (422 invalid_piece_edits); left out (None): the saved edits stay
    edits = piece_edits.canonical(model, body.piece_edits) if body.piece_edits is not None else None
    expected = if_match_revision(request)
    try:
        saved = store.write_overrides(project_id, version, heights, if_revision=expected, piece_edits=edits)
    except RevisionConflict as exc:
        raise ApiError(412, 'revision_conflict', str(exc), views.conflict_details(exc.current, model)) from exc
    return views.overrides_of(saved, model)
