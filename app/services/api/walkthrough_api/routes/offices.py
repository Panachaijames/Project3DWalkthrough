"""Offices: whose drawings a project's are, and their remembered layer roles (docs/upload/DESIGN.md U-8.4, U-13.1).

Decorators frozen at the scaffold U0 (they are apps/web/openapi.json); U5 writes the body.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from ..deps import get_store
from ..drafts import projects
from ..models_upload import OfficeList
from ..store.base import Store

router = APIRouter()


@router.get(
    '/api/offices',
    operation_id='listOffices',
    tags=['offices'],
    response_model=OfficeList,
    summary='List offices',
    description='Every office with remembered layer roles (data/mappings/<officeId>.json): id, name, how many layers it '
                'remembers and when it last changed.',
    response_description='The offices.',
)
def list_offices(store: Store = Depends(get_store)) -> OfficeList:
    return projects.list_offices(store)
