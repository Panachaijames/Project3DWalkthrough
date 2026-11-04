"""The FastAPI app (DESIGN.md 10). `create_app(settings)` builds it; `app` is what uvicorn serves
(`node tools/run-api.mjs` runs `uvicorn walkthrough_api.main:app --host 127.0.0.1`).

Middleware, outermost first: the Host check (settings.allowed_hosts: a request for any other name, a DNS-rebinding page,
gets 400 before anything else), `X-Content-Type-Options: nosniff` on every answer (a stored file is never sniffed into
something that runs), CORS for the dev origins. Fix step, review findings "code" 7 and 11.
"""
from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from . import API_VERSION
from .errors import install_error_handlers
from .routes import downloads, furniture, projects, versions
from .settings import Settings
from .store.local import LocalStore


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    app = FastAPI(
        title='Walkthrough API',
        version=API_VERSION,
        description='Projects, versions, downloads and saved furniture heights for the walkthrough staff app '
                    '(app/docs/DESIGN.md section 10).',
    )
    app.state.settings = settings
    app.state.store = LocalStore(settings.data_dir)
    install_error_handlers(app)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_methods=['GET', 'PUT'],
        allow_headers=['content-type', 'if-match'],
        expose_headers=['etag', 'x-model-stamp', 'content-disposition'],
    )

    @app.middleware('http')
    async def _nosniff(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        response = await call_next(request)
        response.headers.setdefault('X-Content-Type-Options', 'nosniff')
        return response

    app.add_middleware(TrustedHostMiddleware, allowed_hosts=list(settings.allowed_hosts), www_redirect=False)
    for module in (projects, versions, downloads, furniture):
        app.include_router(module.router)
    return app


app = create_app()
