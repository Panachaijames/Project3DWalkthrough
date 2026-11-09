"""LocalJobRunner (docs/upload/DESIGN.md U-3.4, U-13.4; ACCEPTANCE 2.2): launch.json with the FILETIME procStart (checked
against Windows' own figure), alive(), the cancel timer killing a worker that does not answer (it waits for the pid to
exit, then writes `cancelled`; cancelRequested meanwhile), an honest worker left to cancel itself, the start-up marking of
runs whose worker is gone, and 503 builder_missing. The workers here are small scripts run by the API's own Python."""
from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from kit import api_settings, make_client
from test_u5_builds import err, new_project, ready
from upkit import FakeJobRunner, load, upload_bank
from walkthrough_api.drafts.runs import read_run, run_info
from walkthrough_api.jobs.local import LocalJobRunner, alive, proc_start, worker_env
from walkthrough_api.jsonio import dumps_pretty

pytestmark = pytest.mark.skipif(sys.platform != 'win32', reason='the job runner is Windows-specific (Job Objects, FILETIME)')

#: a worker that writes job.json `running` and then ignores everything (cancel included)
DEAF = r'''
import json, os, sys, time, pathlib
d = pathlib.Path(sys.argv[1])
rec = {"format": "job/1", "kind": "build", "runId": d.name, "status": "running", "pid": os.getpid(), "procStart": None,
       "queuedAt": "2026-11-04T00:00:00Z", "startedAt": "2026-11-04T00:00:00Z", "finishedAt": None, "step": "walls",
       "progress": 0.3, "steps": [{"name": "walls", "label": "Building walls", "status": "running", "seconds": None,
       "note": ""}], "messages": [], "error": None, "outputs": {}}
(d / "job.json").write_text(json.dumps(rec), encoding="utf-8")
while True:
    time.sleep(0.05)
'''

#: a worker that honours the cancel file: `cancelled` is its last write
HONEST = DEAF.replace('''while True:
    time.sleep(0.05)''', '''while not (d / "cancel").exists():
    time.sleep(0.05)
rec.update(status="cancelled", finishedAt="2026-11-04T00:00:01Z")
(d / "job.json").write_text(json.dumps(rec), encoding="utf-8")''')


def script_runner(tmp_path: Path, script: str, grace: float = 1.0) -> LocalJobRunner:
    path = tmp_path / 'worker.py'
    path.write_text(script, encoding='utf-8')
    settings = api_settings(tmp_path / 'data', tmp_path / 't.html')
    return LocalJobRunner(settings, command=lambda d: [sys.executable, '-B', str(path), str(d)], cancel_grace=grace,
                          exit_wait=20.0)


def run_folder(tmp_path: Path, run_id: str = '0002-build') -> Path:
    d = tmp_path / 'runs' / run_id
    (d / 'out').mkdir(parents=True)
    return d


def wait_for(cond, timeout: float = 20.0) -> None:
    deadline = time.monotonic() + timeout
    while not cond():
        assert time.monotonic() < deadline, 'timed out'
        time.sleep(0.05)


def windows_start(pid: int) -> str:
    """The process's creation time as Windows reports it (FILETIME ticks, UTC), through PowerShell."""
    out = subprocess.run(['powershell', '-NoProfile', '-Command', f'(Get-Process -Id {pid}).StartTime.ToFileTimeUtc()'],
                         capture_output=True, text=True, timeout=60, check=True)
    return out.stdout.strip()


def test_proc_start_is_the_filetime(tmp_path: Path) -> None:
    p = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'])
    try:
        ours = proc_start(p.pid)
        assert ours is not None and ours.isdigit() and proc_start(p.pid) == ours
        theirs = windows_start(p.pid)
        # PowerShell's StartTime is the same FILETIME (it may drop the sub-millisecond ticks on some builds)
        assert abs(int(ours) - int(theirs)) < 10_000, (ours, theirs)
        assert alive({'pid': p.pid, 'procStart': ours})
        assert not alive({'pid': p.pid, 'procStart': str(int(ours) + 1)})        # another process got the pid
    finally:
        p.kill()
        p.wait()
    assert proc_start(p.pid) is None and not alive({'pid': p.pid, 'procStart': ours})
    assert proc_start(0) is None and proc_start(-5) is None and not alive({'pid': None, 'procStart': None})


def test_worker_env() -> None:
    os.environ['PYTHONNOUSERSITE'] = '1'
    try:
        env = worker_env(api_settings(Path('C:/x'), Path('C:/t.html'), run_lock=Path('C:/locks/r.lock')))
    finally:
        del os.environ['PYTHONNOUSERSITE']
    assert env['PYTHONPATH'].endswith(os.path.join('services', 'builder')) and 'PYTHONNOUSERSITE' not in env
    assert (env['OPENBLAS_NUM_THREADS'], env['OMP_NUM_THREADS'], env['MPLBACKEND'], env['PYTHONUTF8']) == ('1', '1', 'Agg', '1')
    assert env['WALKTHROUGH_RUN_LOCK'] == str(Path('C:/locks/r.lock')) and env['WALKTHROUGH_CACHE_DIR'].endswith('cache')
    runner = LocalJobRunner(api_settings(Path('C:/x'), Path('C:/t.html')))
    cmd = runner.command(Path('C:/r'))
    assert cmd[1:] == ['-B', '-P', '-m', 'walkthrough_builder.job', '--run', str(Path('C:/r'))]


def test_start_writes_launch_and_a_deaf_worker_is_killed_after_the_grace(tmp_path: Path) -> None:
    runner = script_runner(tmp_path, DEAF, grace=1.0)
    d = run_folder(tmp_path)
    runner.start(d)
    launch = load(d / 'launch.json')
    assert launch['format'] == 'launch/1' and launch['procStart'] == proc_start(launch['pid'])
    assert runner.alive(launch)
    wait_for(lambda: (d / 'job.json').is_file())
    assert read_run(d, runner.alive).status == 'running'
    t0 = time.monotonic()
    runner.cancel(d)
    assert (d / 'cancel').is_file()
    info = run_info(read_run(d, runner.alive))
    assert info.cancel_requested is True and info.status == 'running'                 # "Stopping..."
    assert runner.wait_idle(60)
    job = load(d / 'job.json')
    assert job['status'] == 'cancelled' and job['error']['code'] == 'cancelled' and job['finishedAt']
    assert job['steps'][0]['status'] == 'failed'
    assert 0.9 < time.monotonic() - t0 < 30
    assert not alive(launch) and proc_start(launch['pid']) is None                    # it is gone, not just signalled
    runner.stop_all()


def test_an_honest_worker_cancels_itself(tmp_path: Path) -> None:
    runner = script_runner(tmp_path, HONEST, grace=5.0)
    d = run_folder(tmp_path)
    runner.start(d)
    wait_for(lambda: (d / 'job.json').is_file())
    runner.cancel(d)
    assert runner.wait_idle(30)
    job = load(d / 'job.json')
    assert job['status'] == 'cancelled' and job['error'] is None                       # the worker's own last write
    runner.stop_all()


def test_a_worker_that_dies_before_writing_is_interrupted(tmp_path: Path) -> None:
    runner = script_runner(tmp_path, 'import sys; sys.exit(3)')
    d = run_folder(tmp_path, '0001-prepare')
    runner.start(d)
    launch = load(d / 'launch.json')
    wait_for(lambda: not alive(launch))
    rv = read_run(d, runner.alive)
    assert rv.status == 'interrupted' and rv.gone
    assert run_info(rv).error.code == 'interrupted'
    runner.stop_all()


def dead_pid() -> tuple[int, str]:
    p = subprocess.Popen([sys.executable, '-c', 'pass'])
    started = proc_start(p.pid) or '133000000000000000'
    p.wait()
    return p.pid, started


def test_start_up_marks_runs_whose_worker_is_gone(data_copy: Path, template_file: Path) -> None:
    fake = FakeJobRunner()
    with make_client(data_copy, template_file, jobs=fake) as c:
        b = ready(c)
    runs = data_copy / 'projects' / b['projectId'] / 'builds' / b['id'] / 'runs'
    spec = load(runs / '0001-prepare' / 'spec.json')
    pid, started = dead_pid()
    old = time.time() - 120

    def fabricate(run_id: str, job: dict | None, launch: dict | None, age: float | None) -> Path:
        d = runs / run_id
        (d / 'out').mkdir(parents=True)
        (d / 'spec.json').write_bytes(dumps_pretty(dict(spec, runId=run_id, kind=run_id[5:])))
        if job is not None:
            (d / 'job.json').write_bytes(dumps_pretty(job))
        if launch is not None:
            (d / 'launch.json').write_bytes(dumps_pretty(launch))
        if age is not None:
            os.utime(d / 'spec.json', (age, age))
        return d
    base = load(runs / '0001-prepare' / 'job.json')
    a = fabricate('0002-build', dict(base, runId='0002-build', kind='build', status='running', pid=pid, procStart=started,
                                     finishedAt=None), None, None)
    launch = {'format': 'launch/1', 'pid': pid, 'procStart': started, 'launchedAt': '2026-11-04T00:00:00Z'}
    b2 = fabricate('0003-prepare', None, launch, old)
    c3 = fabricate('0004-prepare', None, None, old)
    d4 = fabricate('0005-prepare', None, None, None)                                     # young, never launched: queued
    with make_client(data_copy, template_file) as c:                                     # LocalJobRunner: real alive()
        for d in (a, b2, c3):
            job = load(d / 'job.json')
            assert job['status'] == 'interrupted' and job['error']['code'] == 'interrupted', d.name
        assert not (d4 / 'job.json').exists()
        detail = c.get(b['url']).json()
        assert detail['run']['id'] == '0005-prepare' and detail['run']['status'] == 'queued'
    assert load(a / 'job.json')['runId'] == '0002-build' and load(b2 / 'job.json')['kind'] == 'prepare'


def test_builder_missing(data_copy: Path, template_file: Path, tmp_path: Path) -> None:
    with make_client(data_copy, template_file, builder_python=tmp_path / 'no' / 'python.exe',
                     libredwg_dir=tmp_path / 'nolibre') as c:
        pid = new_project(c)
        sha1s = upload_bank(c, pid, both=False)
        e = err(c.post(f'/api/projects/{pid}/builds', json={'sources': sha1s}), 503, 'builder_missing')
        assert len(e['details']['missing']) == 2 and 'LibreDWG' in e['details']['missing'][1]
        assert str(tmp_path) not in e['message']                                         # no server folders
        assert not (data_copy / 'projects' / pid / 'builds').exists()


def test_a_worker_that_cannot_start_leaves_the_run_failed(data_copy: Path, template_file: Path, tmp_path: Path) -> None:
    fake_python = tmp_path / 'python.exe'
    fake_python.write_bytes(b'not a program')
    with make_client(data_copy, template_file, builder_python=fake_python) as c:
        pid = new_project(c)
        sha1s = upload_bank(c, pid, both=False)
        r = c.post(f'/api/projects/{pid}/builds', json={'sources': sha1s})
        assert r.status_code == 201, r.text[:300]
        run = r.json()['run']
        assert run['status'] == 'failed' and run['error']['code'] == 'internal'
        assert 'could not be started' in run['error']['message']
