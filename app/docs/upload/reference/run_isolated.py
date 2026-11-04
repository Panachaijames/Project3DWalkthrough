"""Run one command as an isolated, time- and memory-limited child on Windows (Job Object), report time, peak memory, exit code.

Usage: python -I run_isolated.py <timeout_s> <mem_limit_mb> <stdout_file> <stderr_file> -- <exe> [args...]
Prints one JSON line: {exit, seconds, peakMB, userS, killed, stdoutBytes, stderrLines}
"""
import ctypes, ctypes.wintypes as wt, json, subprocess, sys, time

k32 = ctypes.WinDLL('kernel32', use_last_error=True)

class IO_COUNTERS(ctypes.Structure):
    _fields_ = [(n, ctypes.c_ulonglong) for n in ('ReadOperationCount', 'WriteOperationCount', 'OtherOperationCount',
                                                   'ReadTransferCount', 'WriteTransferCount', 'OtherTransferCount')]

class BASIC_LIMIT(ctypes.Structure):
    _fields_ = [('PerProcessUserTimeLimit', ctypes.c_longlong), ('PerJobUserTimeLimit', ctypes.c_longlong),
                ('LimitFlags', wt.DWORD), ('MinimumWorkingSetSize', ctypes.c_size_t), ('MaximumWorkingSetSize', ctypes.c_size_t),
                ('ActiveProcessLimit', wt.DWORD), ('Affinity', ctypes.c_size_t), ('PriorityClass', wt.DWORD),
                ('SchedulingClass', wt.DWORD)]

class EXT_LIMIT(ctypes.Structure):
    _fields_ = [('BasicLimitInformation', BASIC_LIMIT), ('IoInfo', IO_COUNTERS), ('ProcessMemoryLimit', ctypes.c_size_t),
                ('JobMemoryLimit', ctypes.c_size_t), ('PeakProcessMemoryUsed', ctypes.c_size_t), ('PeakJobMemoryUsed', ctypes.c_size_t)]

class BASIC_ACCT(ctypes.Structure):
    _fields_ = [('TotalUserTime', ctypes.c_longlong), ('TotalKernelTime', ctypes.c_longlong), ('ThisPeriodTotalUserTime', ctypes.c_longlong),
                ('ThisPeriodTotalKernelTime', ctypes.c_longlong), ('TotalPageFaultCount', wt.DWORD), ('TotalProcesses', wt.DWORD),
                ('ActiveProcesses', wt.DWORD), ('TotalTerminatedProcesses', wt.DWORD)]

JOB_OBJECT_LIMIT_PROCESS_MEMORY = 0x100
JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x2000
JOB_OBJECT_LIMIT_DIE_ON_UNHANDLED_EXCEPTION = 0x400
JOB_OBJECT_LIMIT_ACTIVE_PROCESS = 0x8
CREATE_SUSPENDED = 0x4
CREATE_NO_WINDOW = 0x08000000

k32.CreateJobObjectW.restype = wt.HANDLE
k32.SetInformationJobObject.argtypes = [wt.HANDLE, ctypes.c_int, ctypes.c_void_p, wt.DWORD]
k32.QueryInformationJobObject.argtypes = [wt.HANDLE, ctypes.c_int, ctypes.c_void_p, wt.DWORD, ctypes.c_void_p]
k32.AssignProcessToJobObject.argtypes = [wt.HANDLE, wt.HANDLE]
k32.TerminateJobObject.argtypes = [wt.HANDLE, wt.UINT]


def main():
    timeout, mem_mb, out_f, err_f = float(sys.argv[1]), int(sys.argv[2]), sys.argv[3], sys.argv[4]
    cmd = sys.argv[sys.argv.index('--') + 1:]
    job = k32.CreateJobObjectW(None, None)
    info = EXT_LIMIT()
    info.BasicLimitInformation.LimitFlags = (JOB_OBJECT_LIMIT_PROCESS_MEMORY | JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
                                             | JOB_OBJECT_LIMIT_DIE_ON_UNHANDLED_EXCEPTION | JOB_OBJECT_LIMIT_ACTIVE_PROCESS)
    info.BasicLimitInformation.ActiveProcessLimit = 1
    info.ProcessMemoryLimit = mem_mb * 1024 * 1024
    assert k32.SetInformationJobObject(job, 9, ctypes.byref(info), ctypes.sizeof(info)), ctypes.get_last_error()
    t0 = time.perf_counter()
    with open(out_f, 'wb') as fo, open(err_f, 'wb') as fe:
        p = subprocess.Popen(cmd, stdout=fo, stderr=fe, stdin=subprocess.DEVNULL, creationflags=CREATE_NO_WINDOW)
        k32.AssignProcessToJobObject(job, int(p._handle))      # tiny race: the converter spawns no children
        killed = False
        try:
            p.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            k32.TerminateJobObject(job, 1); killed = True; p.wait()
    secs = time.perf_counter() - t0
    q = EXT_LIMIT(); k32.QueryInformationJobObject(job, 9, ctypes.byref(q), ctypes.sizeof(q), None)
    a = BASIC_ACCT(); k32.QueryInformationJobObject(job, 1, ctypes.byref(a), ctypes.sizeof(a), None)
    import os
    nerr = sum(1 for _ in open(err_f, 'rb'))
    print(json.dumps({'exit': p.returncode, 'seconds': round(secs, 2), 'peakMB': round(q.PeakProcessMemoryUsed / 2**20, 1),
                      'userS': round(a.TotalUserTime / 1e7, 2), 'kernelS': round(a.TotalKernelTime / 1e7, 2), 'killed': killed,
                      'stdoutBytes': os.path.getsize(out_f), 'stderrLines': nerr}))


if __name__ == '__main__':
    main()
