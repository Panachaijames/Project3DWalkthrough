"""One lock shared by every PROCESS that writes a store: the API's heights saves and `npm run seed`'s version-folder swap
(fix step, review finding "code" 2). The API's own threading lock is per process; without this, a save the API
acknowledged between the seed copying overrides.json into its new version folder and swapping the folders in was written
into the old folder and deleted with it.

The lock is an operating-system lock on one byte of `<store root>/.lock` (msvcrt.locking on Windows, fcntl.flock
elsewhere), so it is released by the OS when its process ends: a crashed seed or API never leaves a stale lock behind. The
file itself stays (an empty file; nothing reads it). A waiter polls with a short back-off; after `timeout` seconds it gives
up with StoreBusy (the API answers 500 store_error, the seed stops with the message).
"""
from __future__ import annotations

import os
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from .base import StoreError

LOCK_NAME = '.lock'
DEFAULT_TIMEOUT_S = 60.0

if sys.platform == 'win32':
    import msvcrt

    def _try_lock(fd: int) -> bool:
        os.lseek(fd, 0, os.SEEK_SET)
        try:
            msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)       # one byte (it may lie past the end of the empty file)
        except OSError:
            return False
        return True

    def _unlock(fd: int) -> None:
        os.lseek(fd, 0, os.SEEK_SET)
        msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
else:
    import fcntl

    def _try_lock(fd: int) -> bool:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            return False
        return True

    def _unlock(fd: int) -> None:
        fcntl.flock(fd, fcntl.LOCK_UN)


class StoreBusy(StoreError):
    """Another process held the store's lock for longer than the wait allowed."""


@contextmanager
def file_lock(path: Path, timeout: float, busy: str) -> Iterator[None]:
    """Holds an OS lock on one byte of `path` (created when missing) for the `with` block; StoreBusy(busy) after `timeout`
    seconds of waiting. Each call opens its own handle, so two threads of one process exclude each other too; not
    re-entrant. The handle is not inherited by child processes (a worker started under the lock never holds it)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_RDWR | os.O_CREAT | getattr(os, 'O_BINARY', 0) | getattr(os, 'O_NOINHERIT', 0), 0o644)
    try:
        deadline = time.monotonic() + timeout
        delay = 0.005
        while not _try_lock(fd):
            if time.monotonic() >= deadline:
                raise StoreBusy(busy)
            time.sleep(delay)
            delay = min(delay * 2, 0.2)
        try:
            yield
        finally:
            _unlock(fd)
    finally:
        os.close(fd)


@contextmanager
def store_file_lock(root: Path, timeout: float = DEFAULT_TIMEOUT_S) -> Iterator[None]:
    """Holds the store's cross-process lock for the `with` block. Not re-entrant: LocalStore.exclusive() nests it."""
    with file_lock(Path(root) / LOCK_NAME, timeout,
                   f'the store is busy: another process (the seed?) held its lock for over {timeout:.0f} s'):
        yield
