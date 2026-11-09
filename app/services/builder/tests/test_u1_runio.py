"""runio.py: process identity and the JobRecord files (docs/upload/DESIGN.md U-3.2, U-3.4; ACCEPTANCE 2.1 U1).

`procStart` is the raw FILETIME of GetProcessTimes as a decimal string. On a live child it equals (1) Windows' own
answer through .NET (`Get-Process ... StartTime.ToFileTimeUtc()`, an independent computation) and (2) the API's
`walkthrough_api.jobs.local.proc_start` run in the API's own Python (U5's copy of the rule)."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

import kit
import test_u1_support as S
from walkthrough_builder import runio

win = pytest.mark.skipif(sys.platform != 'win32', reason='Windows process identity')
SLEEPER = 'import os, sys, time; print(os.getpid(), flush=True); time.sleep(float(sys.argv[1]))'


def sleeper(seconds: float = 30) -> subprocess.Popen:
    p = kit.python_child(SLEEPER, str(seconds))
    p.stdout.readline()
    return p


def stop(p: subprocess.Popen) -> None:
    p.kill()
    p.communicate(timeout=30)


@win
def test_proc_start_equals_windows_own_answer() -> None:
    p = sleeper()
    try:
        mine = runio.proc_start(p.pid)
        ps = subprocess.run(['powershell', '-NoProfile', '-NonInteractive', '-Command',
                             f'(Get-Process -Id {p.pid}).StartTime.ToFileTimeUtc()'],
                            capture_output=True, text=True, timeout=120, stdin=subprocess.DEVNULL)
        assert ps.returncode == 0, ps.stderr
        assert mine is not None and mine.isdigit() and mine == ps.stdout.strip()
    finally:
        stop(p)


@win
def test_proc_start_equals_the_apis_on_a_live_child() -> None:
    """U-3.4: one function in each package, tested against the other on a live child."""
    if not S.API_PYTHON.is_file():
        pytest.skip(f'no API Python at {S.API_PYTHON}')
    p = sleeper()
    try:
        env = dict(os.environ, PYTHONPATH=str(kit.APP / 'services' / 'api'), PYTHONDONTWRITEBYTECODE='1',
                   PYTHONIOENCODING='utf-8')
        code = ('import sys\ntry:\n    from walkthrough_api.jobs.local import proc_start, alive\nexcept ImportError as e:\n'
                '    print("MISSING", e); raise SystemExit(0)\n'
                'pid = int(sys.argv[1]); ps = proc_start(pid)\n'
                'print(ps, alive({"pid": pid, "procStart": ps}), alive({"pid": pid, "procStart": sys.argv[2]}))')
        api = subprocess.run([str(S.API_PYTHON), '-B', '-c', code, str(p.pid), runio.proc_start(p.pid) or ''],
                             capture_output=True, text=True, timeout=120, env=env, cwd=str(kit.APP),
                             stdin=subprocess.DEVNULL)
        assert api.returncode == 0, api.stderr
        if api.stdout.startswith('MISSING'):
            pytest.skip(f"the API's proc_start is not there yet (U5): {api.stdout.strip()}")
        theirs, alive_own, alive_mine = api.stdout.split()
        assert theirs == runio.proc_start(p.pid)
        assert alive_own == alive_mine == 'True'
    finally:
        stop(p)
    assert runio.proc_start(p.pid) is None


@win
def test_alive() -> None:
    p = sleeper()
    try:
        ps = runio.proc_start(p.pid)
        assert runio.alive({'pid': p.pid, 'procStart': ps})
        assert runio.running(p.pid)
        assert not runio.alive({'pid': p.pid, 'procStart': str(int(ps) + 1)})       # a reused pid
        assert not runio.alive({'pid': p.pid, 'procStart': None})
    finally:
        stop(p)
    assert not runio.alive({'pid': p.pid, 'procStart': ps})
    assert not runio.running(p.pid)
    for bad in ({}, {'pid': None, 'procStart': '1'}, {'pid': 0, 'procStart': '1'}, {'pid': True, 'procStart': '1'},
                {'pid': '12', 'procStart': '1'}, {'pid': -5, 'procStart': '1'}, {'pid': 2 ** 40, 'procStart': '1'}):
        assert not runio.alive(bad)


@win
def test_exited_process_has_no_proc_start() -> None:
    """A process that has exited (its handle still held here) has no procStart, as the API's rule says."""
    p = sleeper(0.1)
    p.wait(30)
    assert runio.proc_start(p.pid) is None
    p.communicate()


@win
def test_worker_identity_under_the_venv_launcher_is_the_popen_pid() -> None:
    """The venv's python.exe is a launcher that starts the interpreter as its child: the pid the API gets from Popen
    (launch.json) is the launcher's, and the worker reports that pair (job.json), so both carry the same pair."""
    code = ('from walkthrough_builder import runio\nimport os\npid, ps = runio.worker_identity()\n'
            'print(pid, ps, os.getpid())')
    p = kit.python_child(code)
    out, err = p.communicate(timeout=60)
    assert p.returncode == 0, err
    pid, ps, own = out.split()
    base = os.path.normcase(os.path.realpath(getattr(sys, '_base_executable', sys.executable)))
    if base != os.path.normcase(os.path.realpath(sys.executable)):
        assert int(pid) == p.pid and int(own) != p.pid             # through the launcher
    else:
        assert int(pid) == int(own) == p.pid
    assert ps.isdigit()


@win
def test_worker_identity_of_a_plain_interpreter_is_its_own() -> None:
    base = getattr(sys, '_base_executable', sys.executable)
    env = kit.child_env()
    p = subprocess.Popen([base, '-B', '-P', '-c', 'from walkthrough_builder import runio; import os; '
                          'print(*runio.worker_identity(), os.getpid())'], env=env, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE, text=True, stdin=subprocess.DEVNULL)
    out, err = p.communicate(timeout=60)
    if p.returncode != 0 and 'ModuleNotFoundError' in err:
        pytest.skip('the base interpreter cannot import the builder outside its venv')
    pid, _ps, own = out.split()
    assert int(pid) == int(own) == p.pid


def test_job_round_trip_and_record_shape(tmp_path: Path) -> None:
    rec = runio.new_record('prepare', '0001-prepare', [{'name': 'read:0', 'label': 'Reading x.dwg',
                                                        'status': 'waiting', 'seconds': None, 'note': ''}],
                           pid=os.getpid(), proc=runio.proc_start(os.getpid()))
    assert set(rec) == {'format', 'kind', 'runId', 'status', 'pid', 'procStart', 'queuedAt', 'startedAt', 'finishedAt',
                        'step', 'progress', 'steps', 'messages', 'error', 'outputs'}
    assert runio.read_job(tmp_path) is None
    runio.write_job(tmp_path, rec)
    assert runio.read_job(tmp_path) == rec
    raw = (tmp_path / 'job.json').read_bytes()
    assert raw.endswith(b'}\n') and not raw.startswith(b'\xef\xbb\xbf')
    if S.API_PYTHON.is_file():
        code, out = S.check_file('job', tmp_path / 'job.json')
        assert code == 0, out


def test_now_format() -> None:
    import re
    assert re.fullmatch(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ', runio.now())


@win
def test_check_path_refuses_paths_past_260(tmp_path: Path) -> None:
    runio.check_path(tmp_path / 'job.json')
    deep = tmp_path / ('x' * (260 - len(str(tmp_path)) - 10)) / 'job.json'
    with pytest.raises(OSError, match='too deep for Windows: move it or shorten its path'):
        runio.check_path(deep)
