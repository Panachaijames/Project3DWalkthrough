"""Dependencies (DESIGN.md 9.3). Routes take `store: Store = Depends(get_store)`, never a module global."""
from __future__ import annotations

from fastapi import Request

from .settings import Settings
from .store.base import Store


def get_store(request: Request) -> Store:
    """Today: the app's one LocalStore (app.state.store). Later: a request-scoped store carrying the caller's token."""
    store: Store = request.app.state.store
    return store


def get_settings(request: Request) -> Settings:
    settings: Settings = request.app.state.settings
    return settings
