"""Atomic JSON files that another process reads while they are written (docs/upload/DESIGN.md U-3.2).

`os.replace` fails with PermissionError (WinError 5) while another process has the target open, and the API reads
job.json on every poll: `write` therefore retries the replace with back-off (10 ms doubling, capped at 0.5 s) for at
least 5 s, as the API's `jsonio.atomic_write_bytes` does with `retry_on_sharing`. A caller whose write still fails
(`SharingTimeout`) logs it and writes again at its next change; it never stops the worker. Reads are strict (UTF-8
without a BOM, no NaN / Infinity, no repeated key) and retried on a sharing violation the same way.

Files: UTF-8 without a BOM; `indent=2` + one trailing newline by default (upload-contracts.ts section 2), or compact.
Scaffold U0; owned by U1 after the scaffold (a defect found by another builder goes in its own contract-issues file).
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any, TypeVar

T = TypeVar('T')

#: At least this long a sharing violation on the replace is retried (seconds; U-3.2).
RETRY_S = 5.0
FIRST_DELAY_S = 0.010
MAX_DELAY_S = 0.5


class SharingTimeout(PermissionError):
    """The target stayed open in another process for longer than the retry allowed."""


class JsonError(ValueError):
    """Not strict JSON (a BOM, NaN / Infinity, a repeated key, bad UTF-8, bad syntax)."""


def retry_on_sharing(action: Callable[[], T], timeout: float = RETRY_S,
                     sleep: Callable[[float], None] = time.sleep) -> T:
    """Runs `action`; on Windows a PermissionError (a sharing violation) is retried with back-off (10 ms doubling, at most
    0.5 s apart) until at least `timeout` seconds have passed, then raised as SharingTimeout. Elsewhere it is raised at
    once (there it is a real permission problem)."""
    if sys.platform != 'win32':
        return action()
    deadline = time.monotonic() + timeout
    delay = FIRST_DELAY_S
    while True:
        try:
            return action()
        except PermissionError as exc:
            if time.monotonic() >= deadline:
                raise SharingTimeout(f'{exc} (still shared after {timeout:.0f} s)') from exc
            sleep(delay)
            delay = min(delay * 2, MAX_DELAY_S)


def dumps(obj: Any, *, pretty: bool = True) -> bytes:
    if pretty:
        text = json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False) + '\n'
    else:
        text = json.dumps(obj, ensure_ascii=False, separators=(',', ':'), allow_nan=False)
    return text.encode('utf-8')


def write_bytes(path: Path | str, data: bytes, *, timeout: float = RETRY_S) -> None:
    """`data` to `path` atomically: a temp file in the same folder (flushed and synced), then `os.replace`, the replace
    retried on sharing violations for at least `timeout` seconds. The temp file is removed on any failure."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix='.tmp-', suffix='-' + path.name, dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        retry_on_sharing(lambda: os.replace(tmp, path), timeout)
    except BaseException:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass
        raise


def write(path: Path | str, obj: Any, *, pretty: bool = True, timeout: float = RETRY_S) -> None:
    """A JSON value to `path` atomically (see write_bytes)."""
    write_bytes(path, dumps(obj, pretty=pretty), timeout=timeout)


def _no_constants(name: str) -> Any:
    raise JsonError(f'{name} is not JSON')


def _no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise JsonError(f'repeated key {key!r}')
        out[key] = value
    return out


def loads(data: bytes | str) -> Any:
    """Strict JSON: UTF-8 without a BOM, no NaN / Infinity, no repeated keys."""
    if isinstance(data, bytes):
        if data.startswith(b'\xef\xbb\xbf'):
            raise JsonError('starts with a byte-order mark')
        try:
            data = data.decode('utf-8')
        except UnicodeDecodeError as exc:
            raise JsonError(f'not UTF-8: {exc}') from exc
    try:
        return json.loads(data, parse_constant=_no_constants, object_pairs_hook=_no_duplicates)
    except json.JSONDecodeError as exc:
        raise JsonError(str(exc)) from exc


def read(path: Path | str, *, timeout: float = RETRY_S) -> Any:
    """A JSON file, strictly; a sharing violation retried (FileNotFoundError passes through)."""
    return loads(retry_on_sharing(Path(path).read_bytes, timeout))
