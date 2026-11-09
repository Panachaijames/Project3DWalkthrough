"""The JobRecord writer and reader; process identity (docs/upload/DESIGN.md U-3.2, U-3.4).

* `proc_start(pid)`: the process creation time as `GetProcessTimes` returns it, the raw FILETIME (100 ns ticks since
  1601-01-01 UTC) written as a decimal string, compared exactly (no rounding question at all). The API computes the same
  value in `walkthrough_api/jobs/local.py` (U5); a U1 test compares both on a live child.
* `alive(record)`: the pid runs and its creation time equals `record['procStart']` (a reused pid is not the worker).
* `worker_identity()`: the (pid, procStart) the worker writes into job.json. On Windows the venv's `python.exe` is a
  LAUNCHER that starts the real interpreter as its own child (and kills it if the launcher dies), so the pid the API
  gets from `Popen` (launch.json) is the launcher's, not `os.getpid()`. When the worker runs under that launcher it
  reports the launcher's pair, so job.json and launch.json carry the same pair as U-3.4 asks; the two processes live
  and die together. Run directly by a plain interpreter, it reports its own.
* `write_job` / `read_job`: job.json through `jsonfile` (atomic, the replace retried on sharing violations, U-3.2).
* `now()`: the timestamps of the records (UTC, seconds, `Z`); `check_path()`: the 260-character rule of U-4.1.

Owner: U1.
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

from . import jsonfile

JOB = 'job.json'
#: Windows' path limit with long paths off (U-4.1): a full path must stay below this
MAX_PATH = 260
#: what a jsonfile temp name adds to a file name ('.tmp-' + 8 random characters + '-')
TEMP_EXTRA = 14
DEEP_MESSAGE = 'the project folder is too deep for Windows: move it or shorten its path'

if sys.platform == 'win32':
    import ctypes
    import ctypes.wintypes as wt

    _k32 = ctypes.WinDLL('kernel32', use_last_error=True)
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    SYNCHRONIZE = 0x00100000
    WAIT_TIMEOUT = 0x102

    _k32.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
    _k32.OpenProcess.restype = wt.HANDLE
    _k32.GetProcessTimes.argtypes = [wt.HANDLE] + [ctypes.POINTER(wt.FILETIME)] * 4
    _k32.GetProcessTimes.restype = wt.BOOL
    _k32.WaitForSingleObject.argtypes = [wt.HANDLE, wt.DWORD]
    _k32.WaitForSingleObject.restype = wt.DWORD
    _k32.CloseHandle.argtypes = [wt.HANDLE]
    _k32.CloseHandle.restype = wt.BOOL
    _k32.QueryFullProcessImageNameW.argtypes = [wt.HANDLE, wt.DWORD, wt.LPWSTR, ctypes.POINTER(wt.DWORD)]
    _k32.QueryFullProcessImageNameW.restype = wt.BOOL

    def _open(pid: int, access: int):
        if not isinstance(pid, int) or isinstance(pid, bool) or pid <= 0 or pid > 0xFFFFFFFF:
            return None
        return _k32.OpenProcess(access, False, pid) or None

    def _creation(h) -> str | None:
        c, e, k, u = wt.FILETIME(), wt.FILETIME(), wt.FILETIME(), wt.FILETIME()
        if not _k32.GetProcessTimes(h, ctypes.byref(c), ctypes.byref(e), ctypes.byref(k), ctypes.byref(u)):
            return None
        return str(((c.dwHighDateTime & 0xFFFFFFFF) << 32) | (c.dwLowDateTime & 0xFFFFFFFF))

    def proc_start(pid: int) -> str | None:
        """The creation time (FILETIME, 100 ns ticks since 1601 UTC) of the RUNNING process `pid` as a decimal string,
        or None when no such process runs (gone, exited, or not ours to open): the API's rule (jobs/local.py)."""
        h = _open(pid, PROCESS_QUERY_LIMITED_INFORMATION | SYNCHRONIZE)
        if h is None:
            return None
        try:
            if _k32.WaitForSingleObject(h, 0) != WAIT_TIMEOUT:      # signalled: it has exited
                return None
            return _creation(h)
        finally:
            _k32.CloseHandle(h)

    def running(pid: int) -> bool:
        """True while a process with this pid exists and has not exited."""
        h = _open(pid, PROCESS_QUERY_LIMITED_INFORMATION | SYNCHRONIZE)
        if h is None:
            return False
        try:
            return _k32.WaitForSingleObject(h, 0) == WAIT_TIMEOUT
        finally:
            _k32.CloseHandle(h)

    def alive(record: dict) -> bool:
        """True when record['pid'] runs and its creation time equals record['procStart'] (U-3.4)."""
        pid, ps = record.get('pid'), record.get('procStart')
        if not ps or not isinstance(ps, str):
            return False
        h = _open(pid, PROCESS_QUERY_LIMITED_INFORMATION | SYNCHRONIZE)
        if h is None:
            return False
        try:
            return _k32.WaitForSingleObject(h, 0) == WAIT_TIMEOUT and _creation(h) == ps
        finally:
            _k32.CloseHandle(h)

    def image_path(pid: int) -> str | None:
        """The full path of a process's executable, or None."""
        h = _open(pid, PROCESS_QUERY_LIMITED_INFORMATION)
        if h is None:
            return None
        try:
            size = wt.DWORD(32768)
            buf = ctypes.create_unicode_buffer(size.value)
            if not _k32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size)):
                return None
            return buf.value
        finally:
            _k32.CloseHandle(h)
else:  # pragma: no cover - the app runs on Windows; kept so the module imports elsewhere
    def proc_start(pid: int) -> str | None:
        try:
            with open(f'/proc/{pid}/stat', encoding='ascii') as f:
                return f.read().rsplit(')', 1)[1].split()[19]
        except (OSError, IndexError):
            return None

    def running(pid: int) -> bool:
        try:
            os.kill(pid, 0)
        except OSError:
            return False
        return True

    def alive(record: dict) -> bool:
        pid, ps = record.get('pid'), record.get('procStart')
        return isinstance(pid, int) and bool(ps) and running(pid) and proc_start(pid) == ps

    def image_path(pid: int) -> str | None:
        try:
            return os.readlink(f'/proc/{pid}/exe')
        except OSError:
            return None


def _same_file(a: str, b: str) -> bool:
    try:
        return os.path.normcase(os.path.realpath(a)) == os.path.normcase(os.path.realpath(b))
    except OSError:
        return False


def worker_identity() -> tuple[int, str | None]:
    """(pid, procStart) for job.json: the venv launcher's when this interpreter runs under it (see the module text),
    else this process's own."""
    me = os.getpid()
    mine = proc_start(me)
    base = getattr(sys, '_base_executable', None) or sys.executable
    if sys.platform == 'win32' and sys.executable and not _same_file(sys.executable, base):
        try:
            parent = os.getppid()
        except OSError:
            parent = 0
        image = image_path(parent) if parent else None
        parent_start = proc_start(parent) if image else None
        if (image and parent_start and mine and _same_file(image, sys.executable)
                and int(parent_start) <= int(mine)):
            return parent, parent_start
    return me, mine


def now() -> str:
    """UTC, to the second, as the store's records write it (2026-11-04T08:15:00Z)."""
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())


def check_path(path: Path | str, *, extra: int = TEMP_EXTRA) -> None:
    """Raises OSError with U-4.1's plain message when `path` (plus a temp name's extra characters) would pass Windows'
    260-character limit."""
    if sys.platform == 'win32' and len(str(Path(path).resolve())) + extra >= MAX_PATH:
        raise OSError(DEEP_MESSAGE)


def write_job(run_dir: Path, record: dict, *, timeout: float = jsonfile.RETRY_S) -> None:
    """job.json atomically (jsonfile.write: temp file, then os.replace retried on sharing violations for `timeout` s).
    Raises jsonfile.SharingTimeout when the API held it open for longer: the caller writes again at its next change."""
    jsonfile.write(Path(run_dir) / JOB, record, timeout=timeout)


def read_job(run_dir: Path) -> dict | None:
    """job.json, or None when absent."""
    try:
        return jsonfile.read(Path(run_dir) / JOB)
    except FileNotFoundError:
        return None


def new_record(kind: str, run_id: str, steps: list[dict], *, pid: int | None, proc: str | None) -> dict:
    """A JobRecord (upload-contracts.ts section 3) in status `queued`."""
    return {'format': 'job/1', 'kind': kind, 'runId': run_id, 'status': 'queued', 'pid': pid, 'procStart': proc,
            'queuedAt': now(), 'startedAt': None, 'finishedAt': None, 'step': None, 'progress': 0.0,
            'steps': steps, 'messages': [], 'error': None, 'outputs': {}}
