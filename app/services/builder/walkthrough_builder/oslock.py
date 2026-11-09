"""An operating-system file lock (docs/upload/DESIGN.md U-3.5): one run at a time on the machine.

The worker takes an OS lock on one byte of `%TEMP%\\walkthrough-run.lock` (WALKTHROUGH_RUN_LOCK) before its first step and
shows `queued` while it waits. `msvcrt.locking` (fcntl.flock elsewhere) is released by the operating system when the
process ends, so a crashed or killed worker never leaves a stale lock. The lock belongs to a process: a test that holds
it must never spawn a worker that waits on it (ACCEPTANCE 2.1, the `heavy` and `worker` markers).

    with hold(path, wait=lambda waited: ..., timeout=None, cancelled=lambda: False):
        ...  # the lock is held

`wait` is called about once a second while another process holds the lock (the worker writes `queued` there and checks
its cancel file); `cancelled()` returning true stops the wait with LockCancelled; `timeout` (seconds, None = no limit)
stops it with LockTimeout. Not re-entrant within a process: a second `hold` on the same path waits for the first.
Scaffold U0; owned by U1 after the scaffold.
"""
from __future__ import annotations

import os
import sys
import tempfile
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path

LOCK_NAME = 'walkthrough-run.lock'

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
else:  # pragma: no cover - the app runs on Windows; kept so the module imports elsewhere
    import fcntl

    def _try_lock(fd: int) -> bool:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            return False
        return True

    def _unlock(fd: int) -> None:
        fcntl.flock(fd, fcntl.LOCK_UN)


class LockTimeout(TimeoutError):
    """The lock stayed held by another process for longer than the timeout."""


class LockCancelled(Exception):
    """The wait was stopped by `cancelled()`."""


def default_path() -> Path:
    """WALKTHROUGH_RUN_LOCK, else %TEMP%\\walkthrough-run.lock (U-13.5)."""
    set_ = os.environ.get('WALKTHROUGH_RUN_LOCK')
    return Path(set_) if set_ else Path(tempfile.gettempdir()) / LOCK_NAME


def try_acquire(path: Path | str | None = None) -> int | None:
    """Takes the lock without waiting: the open descriptor (pass it to release) or None when another process holds it."""
    p = Path(path) if path else default_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(p, os.O_RDWR | os.O_CREAT | getattr(os, 'O_BINARY', 0) | getattr(os, 'O_NOINHERIT', 0), 0o644)
    if _try_lock(fd):
        return fd
    os.close(fd)
    return None


def release(fd: int) -> None:
    try:
        _unlock(fd)
    finally:
        os.close(fd)


@contextmanager
def hold(path: Path | str | None = None, *, wait: Callable[[float], None] | None = None,
         timeout: float | None = None, cancelled: Callable[[], bool] | None = None,
         poll: float = 0.05) -> Iterator[Path]:
    """Holds the lock for the `with` block (see the module text). Yields the lock file's path."""
    p = Path(path) if path else default_path()
    start = time.monotonic()
    last_call = None
    while True:
        fd = try_acquire(p)
        if fd is not None:
            break
        now = time.monotonic()
        if cancelled is not None and cancelled():
            raise LockCancelled(f'stopped while waiting for {p}')
        if timeout is not None and now - start >= timeout:
            raise LockTimeout(f'{p} was held by another process for over {timeout:.0f} s')
        if wait is not None and (last_call is None or now - last_call >= 1.0):
            last_call = now
            wait(now - start)
        time.sleep(poll)
    try:
        yield p
    finally:
        release(fd)
