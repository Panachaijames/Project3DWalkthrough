"""LocalJobRunner: the builder's worker as a process on this machine (docs/upload/DESIGN.md U-3.2, U-3.4, U-3.5, U-13.4).

* **start(run dir):** `<builder python> -B -P -m walkthrough_builder.job --run <run dir>`, its working folder `app/`
  (never inside the store: Windows could not then delete the store or the build), `CREATE_NEW_PROCESS_GROUP |
  CREATE_NO_WINDOW` (it is its own process group: uvicorn's reload and Ctrl+C do not reach it), stdin, stdout and stderr
  to DEVNULL (the worker writes its own log.txt; an open log handle would hold the run folder), an argument list (no
  shell), and the environment of U-3.5: `PYTHONPATH=services/builder`, UTF-8, no bytecode, one OpenBLAS / OpenMP
  thread, `MPLBACKEND=Agg`, and the builder settings (WALKTHROUGH_*). Right after Popen it writes `launch.json`
  (`LaunchRecord {pid, procStart}`).
* **procStart:** the process creation time from GetProcessTimes, the raw FILETIME (100 ns ticks since 1601-01-01 UTC)
  as a decimal string, compared exactly (`proc_start`; the builder's `runio.proc_start` computes the same, and a U1 test
  compares both on a live child). A process that has exited has none (None), so a reused pid never passes as the worker.
* **cancel(run dir):** creates `cancel` (the worker looks for it every second and writes `cancelled` as its last write),
  then a timer thread: when the run is still queued or running `cancel_grace` (15) s later, it checks that the pid's
  creation time is still procStart, kills the worker's tree (`taskkill /T /F /PID`), waits until that process has exited,
  and only then writes `cancelled` into job.json itself.
"""
from __future__ import annotations

import logging
import os
import subprocess
import sys
import threading
import time
from collections.abc import Callable, Collection
from pathlib import Path
from typing import Any

from ..jsonio import iso_utc
from ..settings import APP_ROOT, Settings

log = logging.getLogger('walkthrough_api.jobs')

CANCEL_GRACE_S = 15.0
EXIT_WAIT_S = 30.0
WORKER_MODULE = 'walkthrough_builder.job'
BUILDER_PACKAGE = APP_ROOT / 'services' / 'builder' / 'walkthrough_builder'
CONVERTERS = ('dwg2dxf.exe', 'dwgread.exe')
#: never handed to the worker: its own Python and venv must not be told about the API's
_DROP_ENV = ('PYTHONNOUSERSITE', 'PYTHONHOME', 'PYTHONSTARTUP', 'PYTHONINSPECT', 'PYTHONEXECUTABLE', 'PYTHONSAFEPATH',
             '__PYVENV_LAUNCHER__', 'VIRTUAL_ENV', 'PYTEST_ADDOPTS', 'PYTEST_CURRENT_TEST')

if sys.platform == 'win32':
    import ctypes
    from ctypes import wintypes

    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    SYNCHRONIZE = 0x00100000
    WAIT_OBJECT_0 = 0x0
    WAIT_TIMEOUT = 0x102
    CREATE_NO_WINDOW = 0x08000000
    CREATE_NEW_PROCESS_GROUP = 0x00000200

    _k32 = ctypes.WinDLL('kernel32', use_last_error=True)
    _k32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    _k32.OpenProcess.restype = wintypes.HANDLE
    _k32.GetProcessTimes.argtypes = [wintypes.HANDLE] + [ctypes.POINTER(wintypes.FILETIME)] * 4
    _k32.GetProcessTimes.restype = wintypes.BOOL
    _k32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    _k32.WaitForSingleObject.restype = wintypes.DWORD
    _k32.CloseHandle.argtypes = [wintypes.HANDLE]
    _k32.CloseHandle.restype = wintypes.BOOL

    def _creation(handle: Any) -> str | None:
        times = [wintypes.FILETIME() for _ in range(4)]
        if not _k32.GetProcessTimes(handle, *(ctypes.byref(t) for t in times)):
            return None
        c = times[0]
        return str((c.dwHighDateTime << 32) | c.dwLowDateTime)

    def proc_start(pid: int) -> str | None:
        """The creation time of the RUNNING process `pid` (FILETIME as a decimal string), or None when no such process
        runs (gone, exited, or not ours to open)."""
        if not isinstance(pid, int) or pid <= 0:
            return None
        h = _k32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION | SYNCHRONIZE, False, pid)
        if not h:
            return None
        try:
            if _k32.WaitForSingleObject(h, 0) != WAIT_TIMEOUT:      # signalled: it has exited
                return None
            return _creation(h)
        finally:
            _k32.CloseHandle(h)

    def wait_exit(pid: int, started: str, timeout: float) -> bool:
        """Waits until the process `pid` whose creation time is `started` has exited: True when it has (or was never
        there), False after `timeout` seconds."""
        h = _k32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION | SYNCHRONIZE, False, pid)
        if not h:
            return True
        try:
            if _creation(h) != started:                     # another process got the pid: ours is gone
                return True
            return _k32.WaitForSingleObject(h, max(0, int(timeout * 1000))) == WAIT_OBJECT_0
        finally:
            _k32.CloseHandle(h)

    def kill_tree(pid: int) -> None:
        subprocess.run(['taskkill', '/T', '/F', '/PID', str(pid)], stdin=subprocess.DEVNULL, capture_output=True,
                       creationflags=CREATE_NO_WINDOW, timeout=60, check=False)

    POPEN_FLAGS = CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW
else:  # pragma: no cover - the app runs on Windows; kept so the module imports elsewhere
    def proc_start(pid: int) -> str | None:
        try:
            with open(f'/proc/{int(pid)}/stat', encoding='ascii') as f:
                return f.read().rsplit(')', 1)[1].split()[19]
        except (OSError, IndexError, ValueError):
            return None

    def wait_exit(pid: int, started: str, timeout: float) -> bool:
        deadline = time.monotonic() + timeout
        while proc_start(pid) == started:
            if time.monotonic() >= deadline:
                return False
            time.sleep(0.1)
        return True

    def kill_tree(pid: int) -> None:
        import signal
        try:
            os.killpg(pid, signal.SIGKILL)
        except OSError:
            pass

    POPEN_FLAGS = 0


def alive(record: dict[str, Any] | None) -> bool:
    """True when record.pid runs and its creation time equals record.procStart (a LaunchRecord or a JobRecord)."""
    if not record:
        return False
    pid, started = record.get('pid'), record.get('procStart')
    return isinstance(pid, int) and bool(started) and proc_start(pid) == started


def worker_env(settings: Settings) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if k not in _DROP_ENV}
    env.update({
        'PYTHONPATH': str(APP_ROOT / 'services' / 'builder'),
        'PYTHONIOENCODING': 'utf-8',
        'PYTHONUTF8': '1',
        'PYTHONDONTWRITEBYTECODE': '1',
        'OPENBLAS_NUM_THREADS': '1',
        'OMP_NUM_THREADS': '1',
        'MPLBACKEND': 'Agg',
        'WALKTHROUGH_BUILDER_PYTHON': str(settings.builder_python),
        'WALKTHROUGH_LIBREDWG_DIR': str(settings.libredwg_dir),
        'WALKTHROUGH_CACHE_DIR': str(settings.cache_dir),
        'WALKTHROUGH_CACHE_MAX_GB': repr(float(settings.cache_max_gb)),
        'WALKTHROUGH_RUN_LOCK': str(settings.run_lock),
    })
    return env


class LocalJobRunner:
    def __init__(self, settings: Settings, *, command: Callable[[Path], list[str]] | None = None,
                 cancel_grace: float = CANCEL_GRACE_S, exit_wait: float = EXIT_WAIT_S) -> None:
        self.settings = settings
        self._command = command
        self.cancel_grace = cancel_grace
        self.exit_wait = exit_wait
        self._procs: dict[str, subprocess.Popen[bytes]] = {}
        self._threads: list[threading.Thread] = []
        self._lock = threading.Lock()

    # ------------------------------------------------------------------------------------------------ the protocol
    def missing(self, kinds: Collection[str]) -> list[str]:
        out = []
        s = self.settings
        if not s.builder_python.is_file():
            out.append(f'the builder\'s Python is not at {s.display_path(s.builder_python)} (WALKTHROUGH_BUILDER_PYTHON; '
                       f'see app/README.md)')
        if not BUILDER_PACKAGE.is_dir():
            out.append('the builder (services/builder/walkthrough_builder) is not there')
        if 'dwg' in kinds:
            lacking = [exe for exe in CONVERTERS if not (s.libredwg_dir / exe).is_file()]
            if lacking:
                out.append(f'LibreDWG ({", ".join(lacking)}) is not in {s.display_path(s.libredwg_dir)} '
                           f'(WALKTHROUGH_LIBREDWG_DIR; npm run vendor:libredwg)')
        return out

    def command(self, run_dir: Path) -> list[str]:
        if self._command is not None:
            return self._command(Path(run_dir))
        return [str(self.settings.builder_python), '-B', '-P', '-m', WORKER_MODULE, '--run', str(run_dir)]

    def start(self, run_dir: Path) -> None:
        from ..drafts.runs import write_record             # noqa: PLC0415 (drafts imports this package's protocol)
        from ..models_upload import LaunchRecord          # noqa: PLC0415
        run_dir = Path(run_dir)
        p = subprocess.Popen(self.command(run_dir), cwd=APP_ROOT, env=worker_env(self.settings),
                             stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                             creationflags=POPEN_FLAGS, close_fds=True)
        with self._lock:
            self._reap()
            self._procs[str(run_dir)] = p
        started = proc_start(p.pid) or '0'                 # '0': it exited at once, and is not alive from now on
        write_record(run_dir / 'launch.json', LaunchRecord,
                     {'format': 'launch/1', 'pid': p.pid, 'procStart': started, 'launchedAt': iso_utc()})

    def cancel(self, run_dir: Path) -> None:
        run_dir = Path(run_dir)
        (run_dir / 'cancel').touch()
        t = threading.Thread(target=self._after_cancel, args=(run_dir,), name=f'cancel-{run_dir.name}', daemon=True)
        with self._lock:
            self._threads = [x for x in self._threads if x.is_alive()]
            self._threads.append(t)
        t.start()

    def alive(self, record: dict[str, Any]) -> bool:
        return alive(record)

    # ------------------------------------------------------------------------------------------------ the 15 s kill
    def _after_cancel(self, run_dir: Path) -> None:
        from ..drafts.runs import IN_PROGRESS, mark_cancelled, read_run   # noqa: PLC0415
        try:
            deadline = time.monotonic() + self.cancel_grace
            while time.monotonic() < deadline:
                rv = read_run(run_dir, self.alive)
                if rv.status not in IN_PROGRESS and not rv.gone:
                    return                                   # it stopped (cancelled, done, failed ...) by itself
                time.sleep(0.2)
            if not run_dir.is_dir():
                return
            rv = read_run(run_dir, self.alive)
            if rv.status not in IN_PROGRESS and not rv.gone:
                return
            record = rv.job if rv.job is not None and rv.job.get('pid') and rv.job.get('procStart') else rv.launch
            if record is not None and alive(record):
                pid, started = int(record['pid']), str(record['procStart'])
                log.warning('run %s did not stop %.0f s after cancel: killing worker %s', run_dir.name,
                            self.cancel_grace, pid)
                kill_tree(pid)
                if not wait_exit(pid, started, self.exit_wait):
                    log.error('run %s: worker %s still runs %.0f s after the kill; job.json left as it is', run_dir.name,
                              pid, self.exit_wait)
                    return
            if run_dir.is_dir():
                mark_cancelled(run_dir, self.alive)
        except Exception:                                    # a timer thread must never take the API down
            log.exception('cancelling run %s failed', run_dir)

    # ------------------------------------------------------------------------------------------------ housekeeping
    def _reap(self) -> None:
        """Drops the handles of workers that have ended (their exit status read)."""
        for key in [k for k, p in self._procs.items() if p.poll() is not None]:
            del self._procs[key]

    def wait_idle(self, timeout: float = 60.0) -> bool:
        """Waits for every cancel timer (tests): True when none is left running."""
        deadline = time.monotonic() + timeout
        for t in list(self._threads):
            t.join(max(0.0, deadline - time.monotonic()))
        return not any(t.is_alive() for t in self._threads)

    def stop_all(self, timeout: float = 30.0) -> None:
        """Kills every worker this runner started that still runs and reads their exit status (tests and shutdown of a
        test app; a served API never calls it: its workers outlive it by design, U-3.4)."""
        with self._lock:
            procs = list(self._procs.values())
        for p in procs:
            if p.poll() is None:
                kill_tree(p.pid)
            try:
                p.wait(timeout)
            except subprocess.TimeoutExpired:
                log.error('worker %s did not end', p.pid)
        with self._lock:
            self._reap()
