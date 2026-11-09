"""Dependencies (DESIGN.md 9.3). Routes take `store: Store = Depends(get_store)`, never a module global."""
from __future__ import annotations

from fastapi import Request

from .settings import Settings
from .jobs.base import JobRunner
from .store.base import Store


def get_store(request: Request) -> Store:
    """Today: the app's one LocalStore (app.state.store). Later: a request-scoped store carrying the caller's token."""
    store: Store = request.app.state.store
    return store


def get_settings(request: Request) -> Settings:
    settings: Settings = request.app.state.settings
    return settings


def get_jobs(request: Request) -> JobRunner:
    """The app's job runner (app.state.jobs): the LocalJobRunner (jobs/local.py, U-13.4), or a test's own. Routes take
    `jobs: JobRunner = Depends(get_jobs)`, never app.state."""
    jobs: JobRunner = request.app.state.jobs
    return jobs
