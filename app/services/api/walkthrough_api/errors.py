"""Domain errors: HTTP status + `{"error": {"code", "message", "details"}}` (ErrorResponse, DESIGN.md 10.1).

Malformed requests keep FastAPI's own 422 (HTTPValidationError). A store's NotFound becomes a 404 with its code
(project_not_found, version_not_found, no_stages, asset_not_found ...); a store whose files are broken answers 500
store_error. The handlers change nothing in the OpenAPI document.

Every other failure is still an ErrorResponse, never a bare 'Internal Server Error' (fix step, review findings "code" 1,
3 and 6): an OSError that reached a route (a file the store could not read or write) is 500 store_error; anything else 500
internal_error (the traceback still goes to the server log). FastAPI's 422 echoes the request's input, and a body with
NaN or Infinity (which Python's json reads) could not be written back as JSON (ValueError, a 500): those numbers are
echoed as the strings 'NaN', 'Infinity', '-Infinity', so such a body gets its 422 like any other wrong value.
"""
from __future__ import annotations

import logging
import math
from typing import Any

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .store.base import NotFound, PathTooLong, StoreError

log = logging.getLogger('walkthrough_api.errors')


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(f'{status} {code}: {message}')
        self.status = status
        self.code = code
        self.message = message
        self.details = details


def not_implemented(operation_id: str) -> ApiError:
    """The scaffold's stub answer for a route whose body was not written (none is left)."""
    return ApiError(501, 'not_implemented', f'{operation_id} is not implemented yet')


def error_body(code: str, message: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    return {'error': {'code': code, 'message': message, 'details': details}}


def finite_json(value: Any) -> Any:
    """`value` with every float that JSON cannot carry (NaN, Infinity, -Infinity) as a string."""
    if isinstance(value, float) and not math.isfinite(value):
        return 'NaN' if math.isnan(value) else ('Infinity' if value > 0 else '-Infinity')
    if isinstance(value, dict):
        return {k: finite_json(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [finite_json(v) for v in value]
    return value


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _api_error(_request: Request, exc: ApiError) -> JSONResponse:
        return JSONResponse(status_code=exc.status, content=error_body(exc.code, exc.message, exc.details))

    @app.exception_handler(NotFound)
    async def _not_found(_request: Request, exc: NotFound) -> JSONResponse:
        return JSONResponse(status_code=404, content=error_body(exc.code, exc.message))

    @app.exception_handler(StoreError)
    async def _store_error(_request: Request, exc: StoreError) -> JSONResponse:
        return JSONResponse(status_code=500, content=error_body('store_error', str(exc)))

    @app.exception_handler(PathTooLong)
    async def _path_too_long(_request: Request, exc: PathTooLong) -> JSONResponse:
        # docs/upload/DESIGN.md U-4.1: a plain message instead of a FileNotFoundError when a path would pass 259
        return JSONResponse(status_code=500, content=error_body('path_too_long', str(exc), {'length': exc.length}))

    @app.exception_handler(RequestValidationError)
    async def _validation(_request: Request, exc: RequestValidationError) -> JSONResponse:
        # FastAPI's own 422 (HTTPValidationError), its input echoed with non-finite numbers as strings
        return JSONResponse(status_code=422, content={'detail': finite_json(jsonable_encoder(exc.errors()))})

    @app.exception_handler(OSError)
    async def _os_error(request: Request, exc: OSError) -> JSONResponse:
        log.error('a store file could not be read or written (%s %s)', request.method, request.url.path, exc_info=exc)
        reason = exc.strerror or type(exc).__name__          # no server paths in the answer
        return JSONResponse(status_code=500, content=error_body('store_error', f'a store file could not be read or '
                                                                               f'written: {reason}'))

    @app.exception_handler(Exception)
    async def _internal(_request: Request, _exc: Exception) -> JSONResponse:
        # Starlette's ServerErrorMiddleware answers with this and still raises the exception (the server logs it)
        return JSONResponse(status_code=500, content=error_body('internal_error', 'the API failed unexpectedly (see its log)'))
