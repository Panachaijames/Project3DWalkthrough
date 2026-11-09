"""isolate.py: one command in a Job Object (docs/upload/DESIGN.md U-3.5; ACCEPTANCE A-3 and 2.1 U1).

A sleeping child is killed at its time limit; an allocating child and a MemoryError child are both classified
`*_memory` (the completion port's memory message; exit code 75); a leaf tool cannot start a second process; cancel and
the output-size watchdog end the whole job; nothing is left running; no shell, no window, stdin closed."""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import pytest

import kit
from walkthrough_builder import isolate, runio

pytestmark = pytest.mark.skipif(sys.platform != 'win32', reason='Job Objects are Windows')


def go(tmp: Path, code: str, **kw) -> dict:
    kw.setdefault('seconds', 60)
    kw.setdefault('memory_mb', 512)
    return isolate.run([sys.executable, '-B', '-P', '-c', code], cwd=tmp, env=isolate.child_env(),
                       stdout=tmp / 'out.txt', stderr=tmp / 'err.txt', **kw)


def test_ok_child_reports_time_cpu_and_peak(tmp_path: Path) -> None:
    res = go(tmp_path, 'import sys; print("hello"); print("to stderr", file=sys.stderr)')
    assert res['exit_code'] == 0 and not res['memory_hit'] and not res['timed_out'] and not res['cancelled']
    assert (tmp_path / 'out.txt').read_text().strip() == 'hello'
    assert 'to stderr' in (tmp_path / 'err.txt').read_text()
    assert res['peak_mb'] > 1 and res['seconds'] > 0
    assert isolate.classify(res, 'read') is None


def test_sleeping_child_is_killed_at_its_time_limit(tmp_path: Path) -> None:
    t0 = time.perf_counter()
    res = go(tmp_path, 'import os, time\nprint(os.getpid(), flush=True)\ntime.sleep(60)', seconds=1.5)
    took = time.perf_counter() - t0
    assert res['timed_out'] and res['exit_code'] is None
    assert 1.4 < took < 10
    assert isolate.classify(res, 'convert') == 'convert_timeout'


def test_allocating_child_is_a_memory_failure(tmp_path: Path) -> None:
    """An allocation past the cap FAILS (it does not kill): the completion port's memory message classifies it."""
    res = go(tmp_path, 'x = []\nwhile True:\n    x.append(bytearray(8 * 1024 * 1024))', memory_mb=200)
    assert res['exit_code'] not in (0, None)
    assert res['memory_message'] and res['memory_hit']
    assert isolate.classify(res, 'read') == 'read_memory'


def test_one_large_allocation_is_a_memory_failure(tmp_path: Path) -> None:
    res = go(tmp_path, 'b = bytearray(900 * 1024 * 1024)', memory_mb=200)
    assert res['memory_hit'] and isolate.classify(res, 'build') == 'build_memory'
    assert 'MemoryError' in (tmp_path / 'err.txt').read_text()


def test_exit_75_is_a_memory_failure(tmp_path: Path) -> None:
    """A step child that ended on MemoryError exits with 75 (step.py): `*_memory` even without the message."""
    res = go(tmp_path, 'import sys; sys.exit(75)')
    assert res['exit_code'] == 75 and res['memory_hit'] and not res['memory_message']
    assert isolate.classify(res, 'read') == 'read_memory'


def test_other_failure_is_failed(tmp_path: Path) -> None:
    res = go(tmp_path, 'raise SystemExit(3)')
    assert res['exit_code'] == 3 and not res['memory_hit']
    assert isolate.classify(res, 'convert') == 'convert_failed'


def test_leaf_tool_cannot_start_another_process(tmp_path: Path) -> None:
    """ActiveProcessLimit 1 for leaf tools (dwg2dxf): a second process in the job is refused. The child here is the
    real interpreter (sys._base_executable), so it is the job's only process until it tries to start another."""
    base = getattr(sys, '_base_executable', sys.executable)
    code = ('import subprocess, sys\ntry:\n    subprocess.run([sys.executable, "-c", "print(1)"], check=True)\n'
            '    print("started")\nexcept Exception as e:\n    print("refused", type(e).__name__)')
    env = isolate.child_env()
    res = isolate.run([base, '-B', '-I', '-c', code], cwd=tmp_path, env=env, seconds=60, memory_mb=256,
                      stdout=tmp_path / 'out.txt', stderr=tmp_path / 'err.txt', leaf=True)
    out = (tmp_path / 'out.txt').read_text()
    assert 'refused' in out, out
    assert res['active_limit_hit']


def test_python_child_may_start_a_tool(tmp_path: Path) -> None:
    """A Python step child (the venv launcher + the interpreter) may start one tool (the check child's dwgread)."""
    res = go(tmp_path, 'import subprocess, sys; print(subprocess.run([sys.executable, "-c", "print(2)"], '
                       'capture_output=True, text=True).stdout.strip())')
    assert res['exit_code'] == 0 and (tmp_path / 'out.txt').read_text().strip() == '2'


def test_cancel_ends_the_child_and_everything_it_started(tmp_path: Path) -> None:
    """cancelled() ends the whole job: the child and its own child (a grandchild sleeping) are gone."""
    code = ('import subprocess, sys, time\n'
            'p = subprocess.Popen([sys.executable, "-c", "import time, os; print(os.getpid(), flush=True); '
            'time.sleep(60)"], stdout=subprocess.PIPE, text=True)\n'
            'print(p.stdout.readline().strip(), flush=True)\ntime.sleep(60)')
    flag = tmp_path / 'stop'
    t0 = time.perf_counter()

    def poll() -> None:                                   # cancel once the grandchild runs (its pid is written)
        if (tmp_path / 'out.txt').read_text().strip() or time.perf_counter() - t0 > 30:
            flag.touch()

    res = go(tmp_path, code, cancelled=flag.exists, poll=poll)
    assert res['cancelled'] and res['exit_code'] is None
    assert isolate.classify(res, 'build') == 'cancelled'
    assert time.perf_counter() - t0 < 35
    grandchild = int((tmp_path / 'out.txt').read_text().split()[0])
    time.sleep(0.3)
    assert not runio.running(grandchild)


def test_output_size_watchdog(tmp_path: Path) -> None:
    code = ('import time\nwith open("big.out", "wb") as f:\n    while True:\n        f.write(b"x" * 1048576)\n'
            '        f.flush()\n        time.sleep(0.01)')
    res = go(tmp_path, code, watch_file=tmp_path / 'big.out', watch_max_bytes=5 * 1024 * 1024)
    assert res['killed_for_size'] and res['exit_code'] is None
    assert isolate.classify(res, 'convert') == 'convert_failed'


def test_poll_exception_ends_the_job(tmp_path: Path) -> None:
    def poll() -> None:
        raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        go(tmp_path, 'import time; time.sleep(60)', poll=poll)


def test_no_shell_strings(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        isolate.run('echo hi', cwd=tmp_path, env={}, seconds=5, memory_mb=64, stdout=tmp_path / 'o',
                    stderr=tmp_path / 'e')                                     # type: ignore[arg-type]


def test_stdin_is_closed_and_no_window(tmp_path: Path) -> None:
    res = go(tmp_path, 'import sys; print(repr(sys.stdin.read()))')
    assert res['exit_code'] == 0 and (tmp_path / 'out.txt').read_text().strip() == "''"


def test_missing_program_is_an_isolate_error(tmp_path: Path) -> None:
    with pytest.raises(isolate.IsolateError):
        isolate.run([str(tmp_path / 'nothing.exe')], cwd=tmp_path, env=isolate.child_env(), seconds=5, memory_mb=64,
                    stdout=tmp_path / 'o', stderr=tmp_path / 'e')


def test_child_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('PYTHONNOUSERSITE', '1')
    monkeypatch.setenv('PYTHONPATH', 'C:\\elsewhere')
    env = isolate.child_env(EXTRA='1')
    assert env['PYTHONPATH'].split(';')[0] == str(kit.BUILDER) and 'C:\\elsewhere' in env['PYTHONPATH']
    for k, v in {'PYTHONIOENCODING': 'utf-8', 'PYTHONUTF8': '1', 'PYTHONDONTWRITEBYTECODE': '1',
                 'OPENBLAS_NUM_THREADS': '1', 'OMP_NUM_THREADS': '1', 'MPLBACKEND': 'Agg', 'EXTRA': '1'}.items():
        assert env[k] == v
    assert 'PYTHONNOUSERSITE' not in env


def test_step_child_memory_error_exits_75(tmp_path: Path) -> None:
    """step.py turns a MemoryError raised by a step into exit code 75 (U-3.5), classified read_memory."""
    fakes = tmp_path / 'fakes.py'
    fakes.write_text('from walkthrough_builder import step\n'
                     'def read(dxf, units, out_dir, *, source, log):\n    raise MemoryError\n'
                     'step.REGISTRY["read"] = read\n', encoding='utf-8')
    args = {'dxf': 'x.dxf', 'units': None, 'out_dir': str(tmp_path), 'source': {'sha1': '0' * 40, 'name': 'x'},
            'events': str(tmp_path / 'ev.jsonl'), 'result': str(tmp_path / 'result.json')}
    (tmp_path / 'args.json').write_text(json.dumps(args), encoding='utf-8')
    res = isolate.run([sys.executable, '-B', '-P', '-m', 'walkthrough_builder.step', 'read', str(tmp_path / 'args.json')],
                      cwd=tmp_path, env=isolate.child_env(WALKTHROUGH_STEP_FAKES=str(fakes)), seconds=60,
                      memory_mb=512, stdout=tmp_path / 'o.txt', stderr=tmp_path / 'e.txt')
    assert res['exit_code'] == 75 and isolate.classify(res, 'read') == 'read_memory'
    assert json.loads((tmp_path / 'result.json').read_text())['type'] == 'MemoryError'
