"""The FastAPI app (DESIGN.md 10). `create_app(settings)` builds it; `app` is what uvicorn serves
(`node tools/run-api.mjs` runs `uvicorn walkthrough_api.main:app --host 127.0.0.1`).

Middleware, outermost first: the Host check (settings.allowed_hosts: a request for any other name, a DNS-rebinding page,
gets 400 before anything else), `X-Content-Type-Options: nosniff` on every answer (a stored file is never sniffed into
something that runs), CORS for the dev origins, then the body guard (docs/upload/DESIGN.md U-13.5: 411 / 413 before a
body is read). Fix step, review findings "code" 7 and 11. The upload milestone's scaffold U0 added the routers of
uploads, builds and offices, POST and DELETE to CORS, the body guard and `app.state.jobs` (the job runner behind
`deps.get_jobs`); step U5 made it the LocalJobRunner (jobs/local.py; a test passes its own runner) and added the start-up
work of docs/upload/DESIGN.md U-13.5: runs whose worker is gone marked interrupted (U-3.4), then the clean-up (U-4.1).
The start-up work runs in the app's lifespan, so `create_app()` alone (openapi_export, a TestClient used without
`with`) touches no store.
"""
from __future__ import annotations

import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from . import API_VERSION
from .bodyguard import BodyGuard
from .drafts import cleanup
from .errors import install_error_handlers
from .jobs.base import JobRunner
from .jobs.local import LocalJobRunner
from .routes import builds, downloads, furniture, offices, projects, uploads, versions
from .settings import Settings
from .store.local import LocalStore


log = logging.getLogger('walkthrough_api.main')


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    try:
        cleanup.startup(app.state.store, app.state.jobs)
    except Exception:                                   # the API still starts; the next start or run cleans up
        log.exception('the start-up clean-up failed')
    yield


def create_app(settings: Settings | None = None, jobs: JobRunner | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    app = FastAPI(
        title='Walkthrough API',
        version=API_VERSION,
        description='Projects, versions, downloads and saved furniture heights for the walkthrough staff app '
                    '(app/docs/DESIGN.md section 10).',
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.store = LocalStore(settings.data_dir)
    app.state.jobs = jobs if jobs is not None else LocalJobRunner(settings)
    install_error_handlers(app)
    app.add_middleware(BodyGuard)                         # innermost: CORS headers still go on its 411 / 413
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_methods=['GET', 'PUT', 'POST', 'DELETE'],
        allow_headers=['content-type', 'if-match'],
        expose_headers=['etag', 'x-model-stamp', 'content-disposition'],
    )

    @app.middleware('http')
    async def _nosniff(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        response = await call_next(request)
        response.headers.setdefault('X-Content-Type-Options', 'nosniff')
        return response

    app.add_middleware(TrustedHostMiddleware, allowed_hosts=list(settings.allowed_hosts), www_redirect=False)
    for module in (projects, versions, downloads, furniture, uploads, builds, offices):
        app.include_router(module.router)
    return app


app = create_app()
