"""One command in a Windows Job Object, time and memory capped (docs/upload/DESIGN.md U-3.2, U-3.5; after
docs/upload/reference/run_isolated.py).

    res = run([exe, *args], cwd=work, env=env, seconds=120, memory_mb=2048, stdout=work / 'out.txt',
              stderr=work / 'err.txt', leaf=True, cancelled=lambda: stop_file.exists(), poll=tick)

The child is created suspended (`CREATE_SUSPENDED | CREATE_NO_WINDOW`, stdin DEVNULL, an argument list, never a shell),
put in a fresh Job Object and only then resumed, so it never runs a moment without its limits:
  * `JOB_OBJECT_LIMIT_PROCESS_MEMORY` (`memory_mb` per process: an allocation past it FAILS, it does not kill),
    `KILL_ON_JOB_CLOSE` (the child and anything it started die with the job handle, also when the worker dies),
    `DIE_ON_UNHANDLED_EXCEPTION` (no error dialog), and `ActiveProcessLimit` 1 for leaf tools (`dwg2dxf.exe`) or a small
    limit for Python children (the venv's `python.exe` is a launcher that starts the interpreter as its own child);
  * a completion port on the job that receives `JOB_OBJECT_MSG_PROCESS_MEMORY_LIMIT`;
  * a wall-clock limit, a `cancelled()` callback and an output-size watchdog (`watch_file` above `watch_max_bytes`), each
    ending the whole job with `TerminateJobObject`; `poll()` is called about four times a second while it waits.
Result (a dict): exit_code, seconds, cpu_seconds, peak_mb, memory_hit, memory_message, timed_out, cancelled,
killed_for_size, active_limit_hit. `memory_hit` is the `*_memory` classification of U-3.5: the memory-limit message
arrived, or the exit code was 75 (a step child that ended on MemoryError), or the peak reached 95 % of the cap.

Owner: U1. Windows only (elsewhere a plain subprocess with a timeout, so the module still imports).
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
from collections.abc import Callable
from pathlib import Path

#: a step child's exit code after a MemoryError (step.py)
EXIT_MEMORY = 75
#: the exit code TerminateJobObject gives every process of a job this module ends
KILLED_EXIT = 0xC000013A & 0xFFFFFFFF          # STATUS_CONTROL_C_EXIT: "stopped from outside"
#: ActiveProcessLimit for a non-leaf (Python) child: the venv launcher, the interpreter and one tool (dwgread)
PYTHON_PROCESS_LIMIT = 4
POLL_S = 0.25

if sys.platform == 'win32':
    import ctypes
    import ctypes.wintypes as wt

    _k32 = ctypes.WinDLL('kernel32', use_last_error=True)
    _ntdll = ctypes.WinDLL('ntdll')

    CREATE_SUSPENDED = 0x00000004
    CREATE_NO_WINDOW = 0x08000000
    JOB_OBJECT_LIMIT_ACTIVE_PROCESS = 0x00000008
    JOB_OBJECT_LIMIT_PROCESS_MEMORY = 0x00000100
    JOB_OBJECT_LIMIT_DIE_ON_UNHANDLED_EXCEPTION = 0x00000400
    JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000
    JobObjectBasicAccountingInformation = 1
    JobObjectAssociateCompletionPortInformation = 7
    JobObjectExtendedLimitInformation = 9
    JOB_OBJECT_MSG_ACTIVE_PROCESS_LIMIT = 3
    JOB_OBJECT_MSG_ACTIVE_PROCESS_ZERO = 4
    JOB_OBJECT_MSG_PROCESS_MEMORY_LIMIT = 9
    JOB_OBJECT_MSG_JOB_MEMORY_LIMIT = 10
    WAIT_TIMEOUT = 0x102
    INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value

    class IO_COUNTERS(ctypes.Structure):
        _fields_ = [(n, ctypes.c_ulonglong) for n in (
            'ReadOperationCount', 'WriteOperationCount', 'OtherOperationCount',
            'ReadTransferCount', 'WriteTransferCount', 'OtherTransferCount')]

    class JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
        _fields_ = [('PerProcessUserTimeLimit', ctypes.c_longlong), ('PerJobUserTimeLimit', ctypes.c_longlong),
                    ('LimitFlags', wt.DWORD), ('MinimumWorkingSetSize', ctypes.c_size_t),
                    ('MaximumWorkingSetSize', ctypes.c_size_t), ('ActiveProcessLimit', wt.DWORD),
                    ('Affinity', ctypes.c_size_t), ('PriorityClass', wt.DWORD), ('SchedulingClass', wt.DWORD)]

    class JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
        _fields_ = [('BasicLimitInformation', JOBOBJECT_BASIC_LIMIT_INFORMATION), ('IoInfo', IO_COUNTERS),
                    ('ProcessMemoryLimit', ctypes.c_size_t), ('JobMemoryLimit', ctypes.c_size_t),
                    ('PeakProcessMemoryUsed', ctypes.c_size_t), ('PeakJobMemoryUsed', ctypes.c_size_t)]

    class JOBOBJECT_BASIC_ACCOUNTING_INFORMATION(ctypes.Structure):
        _fields_ = [('TotalUserTime', ctypes.c_longlong), ('TotalKernelTime', ctypes.c_longlong),
                    ('ThisPeriodTotalUserTime', ctypes.c_longlong), ('ThisPeriodTotalKernelTime', ctypes.c_longlong),
                    ('TotalPageFaultCount', wt.DWORD), ('TotalProcesses', wt.DWORD),
                    ('ActiveProcesses', wt.DWORD), ('TotalTerminatedProcesses', wt.DWORD)]

    class JOBOBJECT_ASSOCIATE_COMPLETION_PORT(ctypes.Structure):
        _fields_ = [('CompletionKey', ctypes.c_void_p), ('CompletionPort', wt.HANDLE)]

    _k32.CreateJobObjectW.argtypes = [ctypes.c_void_p, wt.LPCWSTR]
    _k32.CreateJobObjectW.restype = wt.HANDLE
    _k32.SetInformationJobObject.argtypes = [wt.HANDLE, ctypes.c_int, ctypes.c_void_p, wt.DWORD]
    _k32.SetInformationJobObject.restype = wt.BOOL
    _k32.QueryInformationJobObject.argtypes = [wt.HANDLE, ctypes.c_int, ctypes.c_void_p, wt.DWORD, ctypes.c_void_p]
    _k32.QueryInformationJobObject.restype = wt.BOOL
    _k32.AssignProcessToJobObject.argtypes = [wt.HANDLE, wt.HANDLE]
    _k32.AssignProcessToJobObject.restype = wt.BOOL
    _k32.TerminateJobObject.argtypes = [wt.HANDLE, wt.UINT]
    _k32.TerminateJobObject.restype = wt.BOOL
    _k32.CreateIoCompletionPort.argtypes = [wt.HANDLE, wt.HANDLE, ctypes.c_size_t, wt.DWORD]
    _k32.CreateIoCompletionPort.restype = wt.HANDLE
    _k32.GetQueuedCompletionStatus.argtypes = [wt.HANDLE, ctypes.POINTER(wt.DWORD), ctypes.POINTER(ctypes.c_size_t),
                                               ctypes.POINTER(ctypes.c_void_p), wt.DWORD]
    _k32.GetQueuedCompletionStatus.restype = wt.BOOL
    _k32.WaitForSingleObject.argtypes = [wt.HANDLE, wt.DWORD]
    _k32.WaitForSingleObject.restype = wt.DWORD
    _k32.CloseHandle.argtypes = [wt.HANDLE]
    _k32.CloseHandle.restype = wt.BOOL
    _ntdll.NtResumeProcess.argtypes = [wt.HANDLE]
    _ntdll.NtResumeProcess.restype = ctypes.c_long


class IsolateError(RuntimeError):
    """The child could not be started inside its limits (it never ran without them)."""


def _check(ok: object, what: str) -> None:
    if not ok:
        raise IsolateError(f'{what} failed (Windows error {ctypes.get_last_error()})')


class _Job:
    """A Job Object with limits and a completion port (Windows)."""

    def __init__(self, memory_mb: int, process_limit: int | None) -> None:
        self.memory_bytes = int(memory_mb) * 1024 * 1024
        self.job = _k32.CreateJobObjectW(None, None)
        _check(self.job, 'CreateJobObject')
        self.port = None
        try:
            info = JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
            flags = (JOB_OBJECT_LIMIT_PROCESS_MEMORY | JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
                     | JOB_OBJECT_LIMIT_DIE_ON_UNHANDLED_EXCEPTION)
            if process_limit:
                flags |= JOB_OBJECT_LIMIT_ACTIVE_PROCESS
                info.BasicLimitInformation.ActiveProcessLimit = process_limit
            info.BasicLimitInformation.LimitFlags = flags
            info.ProcessMemoryLimit = self.memory_bytes
            _check(_k32.SetInformationJobObject(self.job, JobObjectExtendedLimitInformation, ctypes.byref(info),
                                                ctypes.sizeof(info)), 'SetInformationJobObject(limits)')
            self.port = _k32.CreateIoCompletionPort(INVALID_HANDLE_VALUE, None, 0, 1)
            _check(self.port, 'CreateIoCompletionPort')
            assoc = JOBOBJECT_ASSOCIATE_COMPLETION_PORT(ctypes.c_void_p(1), self.port)
            _check(_k32.SetInformationJobObject(self.job, JobObjectAssociateCompletionPortInformation,
                                                ctypes.byref(assoc), ctypes.sizeof(assoc)),
                   'SetInformationJobObject(completion port)')
        except BaseException:
            self.close()
            raise
        self.memory_message = False
        self.active_limit = False

    def assign(self, handle: int) -> None:
        _check(_k32.AssignProcessToJobObject(self.job, handle), 'AssignProcessToJobObject')

    def drain(self) -> None:
        """Reads every message waiting on the completion port (no wait)."""
        msg = wt.DWORD()
        key = ctypes.c_size_t()
        ov = ctypes.c_void_p()
        while _k32.GetQueuedCompletionStatus(self.port, ctypes.byref(msg), ctypes.byref(key), ctypes.byref(ov), 0):
            if msg.value in (JOB_OBJECT_MSG_PROCESS_MEMORY_LIMIT, JOB_OBJECT_MSG_JOB_MEMORY_LIMIT):
                self.memory_message = True
            elif msg.value == JOB_OBJECT_MSG_ACTIVE_PROCESS_LIMIT:
                self.active_limit = True

    def terminate(self) -> None:
        _k32.TerminateJobObject(self.job, KILLED_EXIT)

    def accounting(self) -> tuple[float, float]:
        """(peak MB of any one process, CPU seconds user + kernel)."""
        ext = JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
        _k32.QueryInformationJobObject(self.job, JobObjectExtendedLimitInformation, ctypes.byref(ext),
                                       ctypes.sizeof(ext), None)
        acct = JOBOBJECT_BASIC_ACCOUNTING_INFORMATION()
        _k32.QueryInformationJobObject(self.job, JobObjectBasicAccountingInformation, ctypes.byref(acct),
                                       ctypes.sizeof(acct), None)
        return ext.PeakProcessMemoryUsed / 2 ** 20, (acct.TotalUserTime + acct.TotalKernelTime) / 1e7

    def close(self) -> None:
        """Closing the job handle kills whatever is still in it (KILL_ON_JOB_CLOSE)."""
        if self.job:
            _k32.CloseHandle(self.job)
            self.job = None
        if self.port:
            _k32.CloseHandle(self.port)
            self.port = None


def _size(path: Path | None) -> int:
    if path is None:
        return 0
    try:
        return path.stat().st_size
    except OSError:
        return 0


def run(cmd: list[str], *, cwd: Path, env: dict, seconds: float, memory_mb: int, stdout: Path, stderr: Path,
        cancelled: Callable[[], object] | None = None, watch_file: Path | None = None,
        watch_max_bytes: int | None = None, leaf: bool = False, poll: Callable[[], None] | None = None) -> dict:
    """Runs `cmd` (an argument list) in a Job Object; see the module text. stdout and stderr go to the two files (made
    or truncated). Raises IsolateError when the child cannot be started inside its limits; `poll()` exceptions end the
    job and pass through."""
    if not isinstance(cmd, (list, tuple)) or not cmd:
        raise ValueError('cmd must be a non-empty argument list (never a shell string)')
    if sys.platform != 'win32':                                    # pragma: no cover - the app runs on Windows
        return _run_plain(cmd, cwd=cwd, env=env, seconds=seconds, stdout=stdout, stderr=stderr, cancelled=cancelled)
    job = _Job(memory_mb, 1 if leaf else PYTHON_PROCESS_LIMIT)
    t0 = time.perf_counter()
    timed_out = was_cancelled = too_big = False
    try:
        with open(stdout, 'wb') as fo, open(stderr, 'wb') as fe:
            try:
                p = subprocess.Popen([str(c) for c in cmd], cwd=str(cwd), env=env, stdin=subprocess.DEVNULL,
                                     stdout=fo, stderr=fe, shell=False,
                                     creationflags=CREATE_SUSPENDED | CREATE_NO_WINDOW)
            except OSError as exc:
                raise IsolateError(f'could not start {Path(str(cmd[0])).name}: {exc}') from exc
            handle = int(p._handle)                                # noqa: SLF001 - the process handle Popen holds
            try:
                job.assign(handle)
            except BaseException:
                p.kill()
                p.wait()
                raise
            if _ntdll.NtResumeProcess(handle) < 0:
                p.kill()
                p.wait()
                raise IsolateError('NtResumeProcess failed')
            try:
                while _k32.WaitForSingleObject(handle, int(POLL_S * 1000)) == WAIT_TIMEOUT:
                    job.drain()
                    if time.perf_counter() - t0 > seconds:
                        timed_out = True
                    elif cancelled is not None and cancelled():
                        was_cancelled = True
                    elif watch_max_bytes is not None and _size(watch_file) > watch_max_bytes:
                        too_big = True
                    if timed_out or was_cancelled or too_big:
                        job.terminate()
                        break
                    if poll is not None:
                        poll()
            except BaseException:
                job.terminate()
                p.wait()
                raise
            exit_code = p.wait()
        elapsed = time.perf_counter() - t0
        time.sleep(0.02)                                           # let the last job messages reach the port
        job.drain()
        peak_mb, cpu = job.accounting()
    finally:
        job.close()
    memory_hit = bool(job.memory_message or exit_code == EXIT_MEMORY
                      or peak_mb * 2 ** 20 >= 0.95 * job.memory_bytes)
    return {'exit_code': exit_code if not (timed_out or was_cancelled or too_big) else None,
            'raw_exit_code': exit_code, 'seconds': round(elapsed, 3), 'cpu_seconds': round(cpu, 3),
            'peak_mb': round(peak_mb, 1), 'memory_hit': memory_hit, 'memory_message': job.memory_message,
            'timed_out': timed_out, 'cancelled': was_cancelled, 'killed_for_size': too_big,
            'active_limit_hit': job.active_limit}


def _run_plain(cmd, *, cwd, env, seconds, stdout, stderr, cancelled):  # pragma: no cover - not Windows
    t0 = time.perf_counter()
    timed_out = was_cancelled = False
    with open(stdout, 'wb') as fo, open(stderr, 'wb') as fe:
        p = subprocess.Popen([str(c) for c in cmd], cwd=str(cwd), env=env, stdin=subprocess.DEVNULL, stdout=fo,
                             stderr=fe)
        while p.poll() is None:
            if time.perf_counter() - t0 > seconds:
                timed_out = True
            elif cancelled is not None and cancelled():
                was_cancelled = True
            if timed_out or was_cancelled:
                p.kill()
                break
            time.sleep(POLL_S)
        code = p.wait()
    return {'exit_code': None if (timed_out or was_cancelled) else code, 'raw_exit_code': code,
            'seconds': round(time.perf_counter() - t0, 3), 'cpu_seconds': 0.0, 'peak_mb': 0.0,
            'memory_hit': code == EXIT_MEMORY, 'memory_message': False, 'timed_out': timed_out,
            'cancelled': was_cancelled, 'killed_for_size': False, 'active_limit_hit': False}


def child_env(base: dict | None = None, **extra: str) -> dict:
    """The environment of every child (U-3.5): the builder's PYTHONPATH, UTF-8 I/O, no bytecode, one OpenBLAS / OpenMP
    thread, matplotlib's Agg backend; the user site never hidden (a stand-in system Python keeps its libraries there)."""
    builder = str(Path(__file__).resolve().parents[1])
    env = dict(os.environ if base is None else base)
    paths = [builder] + [p for p in env.get('PYTHONPATH', '').split(os.pathsep) if p and os.path.normcase(p) !=
                         os.path.normcase(builder)]
    env.update(PYTHONPATH=os.pathsep.join(paths), PYTHONIOENCODING='utf-8', PYTHONUTF8='1',
               PYTHONDONTWRITEBYTECODE='1', OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1', MPLBACKEND='Agg')
    env.pop('PYTHONNOUSERSITE', None)
    env.pop('PYTHONSTARTUP', None)
    env.update(extra)
    return env


def classify(res: dict, prefix: str) -> str | None:
    """The RunErrorCode of a finished child, or None when it succeeded: `<prefix>_timeout`, `<prefix>_memory` (U-3.5's
    rule) or `<prefix>_failed`. A cancelled child returns 'cancelled'."""
    if res.get('cancelled'):
        return 'cancelled'
    if res.get('timed_out'):
        return f'{prefix}_timeout'
    if res.get('exit_code') == 0 and not res.get('killed_for_size'):
        return None
    if res.get('memory_hit'):
        return f'{prefix}_memory'
    return f'{prefix}_failed'
