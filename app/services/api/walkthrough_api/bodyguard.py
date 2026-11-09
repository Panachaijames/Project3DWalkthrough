"""The body guard (docs/upload/DESIGN.md U-13.5): a pure-ASGI middleware in front of the routes, so FastAPI never reads a
large body into memory.

* `PUT /api/uploads/<id>/parts/<n>`: needs Content-Length (else 411 length_required) not above the part size (else 413
  part_too_large), checked before a byte of the body is read.
* `PUT /api/projects/<id>/builds/<id>/settings`: at most 8 MiB (else 413 body_too_large).
* any other POST or PUT: at most 2 MiB (else 413 body_too_large).
A declared Content-Length over the limit is refused at once. A body with no Content-Length (chunked) is read up to the
limit and refused the moment it passes it; under the limit it is handed on unchanged. Answers are ErrorResponse JSON.
Complete at the scaffold U0 (small); U5 owns it afterwards.
"""
from __future__ import annotations

import json
import re
from collections.abc import Awaitable, Callable, MutableMapping
from typing import Any

Scope = MutableMapping[str, Any]
Message = MutableMapping[str, Any]
Receive = Callable[[], Awaitable[Message]]
Send = Callable[[Message], Awaitable[None]]
ASGIApp = Callable[[Scope, Receive, Send], Awaitable[None]]

MIB = 1024 * 1024
PART_BYTES = 8 * MIB
SETTINGS_MAX = 8 * MIB
DEFAULT_MAX = 2 * MIB

_PART = re.compile(r'^/api/uploads/[^/]+/parts/[^/]+/?$')
_SETTINGS = re.compile(r'^/api/projects/[^/]+/builds/[^/]+/settings/?$')


def limit_for(method: str, path: str, part_bytes: int = PART_BYTES) -> tuple[int, str] | None:
    """(limit, error code) for a request whose body is guarded, else None."""
    if method == 'PUT' and _PART.match(path):
        return part_bytes, 'part_too_large'
    if method == 'PUT' and _SETTINGS.match(path):
        return SETTINGS_MAX, 'body_too_large'
    if method in ('POST', 'PUT', 'PATCH'):
        return DEFAULT_MAX, 'body_too_large'
    return None


async def _answer(send: Send, status: int, code: str, message: str) -> None:
    body = json.dumps({'error': {'code': code, 'message': message, 'details': None}}).encode('utf-8')
    await send({'type': 'http.response.start', 'status': status,
                'headers': [(b'content-type', b'application/json'), (b'content-length', str(len(body)).encode()),
                            (b'connection', b'close')]})
    await send({'type': 'http.response.body', 'body': body})


class BodyGuard:
    def __init__(self, app: ASGIApp, part_bytes: int = PART_BYTES) -> None:
        self.app = app
        self.part_bytes = part_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope['type'] != 'http':
            await self.app(scope, receive, send)
            return
        rule = limit_for(scope['method'], scope['path'], self.part_bytes)
        if rule is None:
            await self.app(scope, receive, send)
            return
        limit, code = rule
        length: int | None = None
        for k, v in scope.get('headers', []):
            if k == b'content-length':
                try:
                    length = int(v)
                except ValueError:
                    await _answer(send, 400, 'bad_request', 'Content-Length is not a number')
                    return
        is_part = code == 'part_too_large'
        if length is None and is_part:
            await _answer(send, 411, 'length_required', 'an upload part needs a Content-Length header')
            return
        if length is not None and length > limit:
            await _answer(send, 413, code, f'the body is {length} bytes; at most {limit} are taken here')
            return
        if length is not None:
            await self.app(scope, receive, send)
            return
        # no Content-Length (chunked): read it here up to the limit, then hand it on
        chunks: list[bytes] = []
        size = 0
        while True:
            msg = await receive()
            if msg['type'] == 'http.disconnect':
                return
            chunk = msg.get('body', b'')
            size += len(chunk)
            if size > limit:
                await _answer(send, 413, code, f'the body passed {limit} bytes; at most {limit} are taken here')
                return
            chunks.append(chunk)
            if not msg.get('more_body', False):
                break
        body = b''.join(chunks)
        sent = False

        async def replay() -> Message:
            nonlocal sent
            if not sent:
                sent = True
                return {'type': 'http.request', 'body': body, 'more_body': False}
            return await receive()

        await self.app(scope, replay, send)
