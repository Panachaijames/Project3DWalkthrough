"""JSON and file helpers shared by the store, the seed and the downloads (DESIGN.md 9.1).

Files are bytes on disk, always: text-mode reads and writes on Windows translate line ends, and the offline file, the
CSV and the stamps depend on the stored bytes. JSON files are UTF-8 without a byte-order mark; the seed writes models and
stages compact (`separators=(',', ':')`) and meta.json / version.json / overrides.json with `indent=2`, each with one
trailing newline. Writes are atomic: a temp file in the same folder, then `os.replace`.

Windows: a file another thread or process has open (a request reading overrides.json, the indexer, antivirus) cannot be
replaced, and a file in the middle of being replaced cannot be opened, for a moment: both raise PermissionError (a sharing
violation). `retry_on_sharing` retries such an action briefly; the store's reads and `atomic_write_bytes` use it, so a
heights save and a concurrent read of the same file never fail each other (fix step, review finding "code" 1).
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import sys
import tempfile
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TypeVar

T = TypeVar('T')

#: How long a sharing violation is retried before it is reported (seconds).
SHARING_RETRY_S = 2.0


def retry_on_sharing(action: Callable[[], T], timeout: float = SHARING_RETRY_S) -> T:
    """Runs `action`; on Windows a PermissionError (a sharing violation: the file is open elsewhere or being replaced) is
    retried with a short back-off for up to `timeout` seconds, then raised. Elsewhere it is raised at once (there it is a
    real permission problem)."""
    if sys.platform != 'win32':
        return action()
    deadline = time.monotonic() + timeout
    delay = 0.002
    while True:
        try:
            return action()
        except PermissionError:
            if time.monotonic() >= deadline:
                raise
            time.sleep(delay)
            delay = min(delay * 2, 0.05)


def read_bytes(path: Path) -> bytes:
    """A file's bytes, a sharing violation retried (FileNotFoundError passes through)."""
    return retry_on_sharing(Path(path).read_bytes)


class JsonError(ValueError):
    """A file that is not strict JSON (BOM, NaN / Infinity, a repeated key, bad UTF-8, bad syntax)."""


def _no_constants(name: str) -> Any:
    raise JsonError(f'{name} is not JSON')


def _no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise JsonError(f'repeated key {key!r}')
        out[key] = value
    return out


def loads_strict(data: bytes | str) -> Any:
    """Parse strict JSON: UTF-8 without a BOM, no NaN / Infinity, no repeated keys."""
    if isinstance(data, bytes):
        if data.startswith(b'\xef\xbb\xbf'):
            raise JsonError('starts with a byte-order mark')
        try:
            text = data.decode('utf-8')
        except UnicodeDecodeError as exc:
            raise JsonError(f'not UTF-8: {exc}') from exc
    else:
        text = data
    try:
        return json.loads(text, parse_constant=_no_constants, object_pairs_hook=_no_duplicates)
    except json.JSONDecodeError as exc:
        raise JsonError(str(exc)) from exc


def read_json(path: Path) -> Any:
    return loads_strict(Path(path).read_bytes())


def dumps_compact(obj: Any) -> bytes:
    """Models and stages: `json.dumps(..., ensure_ascii=False, separators=(',', ':'))` + newline, UTF-8."""
    return (json.dumps(obj, ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n').encode('utf-8')


def dumps_pretty(obj: Any) -> bytes:
    """meta.json, version.json, overrides.json: `indent=2` + newline, UTF-8."""
    return (json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode('utf-8')


def sha1_hex(data: bytes) -> str:
    return hashlib.sha1(data).hexdigest()


def sha1_file(path: Path) -> str:
    h = hashlib.sha1()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def atomic_write_bytes(path: Path, data: bytes) -> None:
    """Write `data` to `path` atomically (temp file in the same folder, then os.replace; a sharing violation on the
    replace, a reader having the old file open for a moment, is retried)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix='.tmp-', suffix='-' + path.name, dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        retry_on_sharing(lambda: os.replace(tmp, path))
    except BaseException:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass
        raise


def iso_utc(ts: float | datetime | None = None) -> str:
    """ISO 8601 UTC, whole seconds: 2026-10-29T03:24:53Z (seconds are truncated, never rounded up)."""
    if ts is None:
        dt = datetime.now(UTC)
    elif isinstance(ts, datetime):
        dt = ts.astimezone(UTC)
    else:
        dt = datetime.fromtimestamp(math.floor(ts), UTC)
    return dt.strftime('%Y-%m-%dT%H:%M:%SZ')


#: The picture types an asset may be (a plan picture or the thumbnail): raster images only. An SVG (or anything else a
#: browser would run script in) is never stored as an asset, so /api/.../assets/<name> can never serve a document that
#: runs in the staff app's origin (fix step, review finding "code" 11).
RASTER_MEDIA_TYPES = ('image/png', 'image/jpeg', 'image/webp', 'image/gif')


def media_type_of(data: bytes, name: str = '') -> str:
    """The media type of an asset from its first bytes (as the hotel generator tells PNG from JPEG): one of
    RASTER_MEDIA_TYPES, else application/octet-stream. The name is not trusted (an SVG named .png is not a PNG)."""
    del name
    if data[:8] == b'\x89PNG\r\n\x1a\n':
        return 'image/png'
    if data[:3] == b'\xff\xd8\xff':
        return 'image/jpeg'
    if data[:6] in (b'GIF87a', b'GIF89a'):
        return 'image/gif'
    if data[:4] == b'RIFF' and data[8:12] == b'WEBP':
        return 'image/webp'
    return 'application/octet-stream'
