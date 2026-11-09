"""Helpers of U1's tests (no tests in this file): the step fakes, run folders and a worker launcher.

The fakes stand in for U2's read / suggest / propose_settings, U3's build and U4's write_outputs through step.py's
registry (WALKTHROUGH_STEP_FAKES): they write the scaffold's fixtures (fixtures/upload/...) so that the worker's own
steps (conversion, the loss check, the cache, job.json, validate with the API's check_file) run for real. Behaviour is
chosen per test with WT_FAKE_MODE (JSON): {"read": "memory" | "sleep" | "fail", "build": "sleep" | "fail_code",
"outputs": "no_parts", "sleep": <s>, "used": <units>}.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import kit
from walkthrough_builder import jsonfile, runio

BANK1 = kit.PROJECT / kit.DRAWINGS['bank1']
BANK1_SHA1 = '459d40fc230607ffe35e2ee9d443cd2b0105dc36'
BANK2 = kit.PROJECT / kit.DRAWINGS['bank2']
BANK2_SHA1 = '6551bdc6f0cff4e31e83b68a55d22cf42703029a'
SMALL_SHA1 = 'fb8e7283ab205c8e49ecc057f6019c1e9fd2f6d0'
API_PYTHON = kit.APP / 'services' / 'api' / '.venv' / 'Scripts' / 'python.exe'

FAKES = r'''
import json, os, pickle, shutil, time
from pathlib import Path
from walkthrough_builder import jsonfile, step

FX = Path(os.environ['WT_FAKE_FIXTURES'])
PROJECT = Path(os.environ['WT_FAKE_PROJECT'])
MODE = json.loads(os.environ.get('WT_FAKE_MODE') or '{}')


class CodedError(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def read(dxf, units, out_dir, *, source, log):
    log('fake read of ' + source['name'] + ' from C:\\secret\\server\\folder\\plan.dxf')
    if MODE.get('read') == 'memory':
        raise MemoryError
    if MODE.get('read') == 'sleep':
        time.sleep(float(MODE.get('sleep', 60)))
    if MODE.get('read') == 'fail':
        raise ValueError('the walk broke at C:\\Users\\someone\\data\\plan.dxf line 7')
    d = jsonfile.read(FX / 'drawing' / 'bank1.drawing.json')
    d['source'] = {'sha1': source['sha1'], 'name': source['name']}
    used = units or MODE.get('used') or 'mm'
    d['units']['used'] = used
    out_dir = Path(out_dir)
    jsonfile.write(out_dir / 'drawing.json', d)
    shutil.copyfile(FX / 'plan' / 'bank1.plan.json.gz', out_dir / 'plan.json.gz')
    with open(out_dir / 'items.pkl', 'wb') as f:
        pickle.dump({'items': [], 'layers': {}, 'units': used, 'dxf': Path(dxf).name}, f)
    return {'items': str(out_dir / 'items.pkl'), 'drawing': str(out_dir / 'drawing.json'),
            'plan': str(out_dir / 'plan.json.gz'), 'units': d['units'], 'seconds': 0.01}


def suggest(drawings, office):
    layers = {}
    for d in drawings:
        for la in d['layers']:
            layers[la['name']] = {'role': 'other', 'from': 'default', 'evidence': ['fake']}
    return {'format': 'layer-suggestions/1', 'office': office['id'] if office else None, 'layers': layers}


def propose(spec, drawings, suggestions, conversions, latest_version):
    s = jsonfile.read(FX / 'settings' / 'bank.json')
    s['sources'] = [{'sha1': x['sha1'], 'name': x['name'], 'kind': x['kind'], 'units': d['units']['used'],
                     'unitsConfirmed': True} for x, d in zip(spec['sources'], drawings)]
    for f, x in zip(s['floors'], spec['sources'] * 2):
        f['source'] = x['sha1']
    s['floors'] = s['floors'][:len(spec['sources'])] or s['floors'][:1]
    if latest_version:
        s['project']['maxFileName'] = latest_version['msName']
    return s


def build(ctx, log, progress):
    log('fake build with ' + str(len(ctx['sources'])) + ' sources')
    if MODE.get('pidfile'):
        Path(MODE['pidfile']).write_text(str(os.getpid()), encoding='utf-8')
    if MODE.get('ctxfile'):
        seen = dict(ctx, _conversions=[jsonfile.read(s['conversion']) if s['conversion'] else None
                                       for s in ctx['sources']],
                    _env={k: os.environ.get(k) for k in ('OPENINGS_DATA', 'OPENBLAS_NUM_THREADS', 'MPLBACKEND',
                                                         'PYTHONDONTWRITEBYTECODE')})
        jsonfile.write(MODE['ctxfile'], seen)
    progress('align', 0.0)
    for f in ctx['spec']['settings']['floors']:
        progress('detect:' + f['key'], 0.5)
    if MODE.get('build') == 'sleep':
        end = time.time() + float(MODE.get('sleep', 60))
        while time.time() < end:
            progress('walls', 0.1)
            time.sleep(0.2)
    if MODE.get('build') == 'fail_code':
        raise CodedError('area_empty', "Level 1's area holds no wall.")
    progress('walls', 0.5)
    progress('openings', 0.5)
    progress('furniture', 0.5)
    return {'seconds': {'detect:L1': 0.25}, 'ctx': ctx}


def outputs(result, ctx, log):
    out = Path(ctx['outDir'])
    run = FX / 'runs' / 'bank-build'
    spec = jsonfile.read(run / 'run.json')
    got = {}
    for name, src in spec['outputs'].items():
        if 'fixture' in src:
            p = FX.parents[1] / src['fixture']
        elif 'prototype' in src:
            p = PROJECT / src['prototype']
        else:
            p = run / src['file']
        shutil.copyfile(p, out / name)
        got[name] = out / name
    if MODE.get('outputs') == 'no_parts':
        m = json.loads((out / 'model.json').read_bytes())
        m['parts'] = []
        (out / 'model.json').write_bytes(json.dumps(m, separators=(',', ':')).encode())
    log('fake outputs: ' + str(len(got)) + ' files')
    return got


step.REGISTRY.update(read=read, suggest=suggest, propose=propose, build=build, outputs=outputs)
'''


def write_fakes(folder: Path) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    p = folder / 'u1_fakes.py'
    p.write_text(FAKES, encoding='utf-8')
    return p


def bank_settings(sources: list[dict], *, units: str | None = 'mm') -> dict:
    """fixtures/upload/settings/bank.json with the test's sources (one floor per source)."""
    s = jsonfile.read(kit.UPLOAD_FIXTURES / 'settings' / 'bank.json')
    s['sources'] = [{'sha1': x['sha1'], 'name': x['name'], 'kind': x['kind'], 'units': units,
                     'unitsConfirmed': units is not None} for x in sources]
    floors = s['floors'][:len(sources)]
    for f, x in zip(floors, sources):
        f['source'] = x['sha1']
    s['floors'] = floors
    return s


def source(path: Path, sha1: str, *, kind: str = 'dwg', name: str | None = None, units: str | None = None) -> dict:
    return {'sha1': sha1, 'name': name or path.name, 'kind': kind, 'path': str(path), 'units': units}


def make_run(root: Path, kind: str, sources: list[dict], *, run_id: str | None = None, cache: Path,
             settings: dict | None = None, only: list[str] | None = None, office: dict | None = None,
             limits: dict | None = None, wall: float = 3600.0, version_model: str | None = None,
             previous_run: str | None = None, libredwg: Path | None = None) -> Path:
    """A run folder with its spec.json (JobSpec), as the API writes it."""
    run_id = run_id or ('0001-prepare' if kind == 'prepare' else '0002-build')
    run_dir = root / 'runs' / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    spec = {
        'format': 'job-spec/1', 'kind': kind, 'runId': run_id, 'buildId': '20261104T120000-abcdef',
        'projectId': 'u1-test', 'settings': settings or bank_settings(sources, units=None if kind == 'prepare' else 'mm'),
        'settingsRevision': 0 if kind == 'prepare' else 1,
        'sources': sources, 'only': only, 'office': office,
        'paths': {'out': str(run_dir / 'out'), 'cache': str(cache), 'libredwg': str(libredwg or kit.LIBREDWG),
                  'previousRun': previous_run, 'versionModel': version_model},
        'limits': limits or {'convert': {'seconds': 120, 'memoryMB': 2048}, 'check': {'seconds': 180, 'memoryMB': 1024},
                             'read': {'seconds': 300, 'memoryMB': 4096}, 'build': {'seconds': 900, 'memoryMB': 4096}},
        'wallClockSeconds': wall,
    }
    jsonfile.write(run_dir / 'spec.json', spec)
    return run_dir


def worker_env(fakes: Path | None, mode: dict | None = None, **extra: str) -> dict:
    env = kit.child_env(WT_FAKE_FIXTURES=str(kit.UPLOAD_FIXTURES), WT_FAKE_PROJECT=str(kit.PROJECT),
                        WT_FAKE_MODE=json.dumps(mode or {}), **extra)
    if fakes is not None:
        env['WALKTHROUGH_STEP_FAKES'] = str(fakes)
    else:
        env.pop('WALKTHROUGH_STEP_FAKES', None)
    return env


def start_worker(run_dir: Path, env: dict, logs: Path) -> subprocess.Popen:
    """Starts the worker as the API does (its own process group, no window); its stdout and stderr go to `logs`."""
    logs.mkdir(parents=True, exist_ok=True)
    flags = getattr(subprocess, 'CREATE_NEW_PROCESS_GROUP', 0) | getattr(subprocess, 'CREATE_NO_WINDOW', 0)
    return subprocess.Popen([sys.executable, '-B', '-P', '-m', 'walkthrough_builder.job', '--run', str(run_dir)],
                            env=env, cwd=str(logs), stdin=subprocess.DEVNULL,
                            stdout=open(logs / 'worker.out.txt', 'ab'), stderr=open(logs / 'worker.err.txt', 'ab'),
                            creationflags=flags)


def read_job(run_dir: Path) -> dict | None:
    try:
        return runio.read_job(run_dir)
    except (OSError, ValueError):
        return None


def wait_status(run_dir: Path, worker, statuses: tuple[str, ...], *, proc: subprocess.Popen | None = None,
                timeout: float | None = None) -> dict:
    """Polls job.json until its status is one of `statuses` (and, given `proc`, the worker has exited). A `queued`
    status is reported through the worker fixture (another run holds the machine lock), not as a failure."""
    timeout = timeout or worker.timeout
    t0 = time.monotonic()
    last = None
    while time.monotonic() - t0 < timeout:
        rec = read_job(run_dir)
        if rec is not None:
            last = rec
            if rec['status'] == 'queued':
                worker.report_queue(time.monotonic() - t0)
            if rec['status'] in statuses and (proc is None or proc.poll() is not None):
                return rec
        if proc is not None and proc.poll() is not None and (rec is None or rec['status'] not in statuses):
            time.sleep(0.3)
            rec = read_job(run_dir)
            if rec is not None and rec['status'] in statuses:
                return rec
            raise AssertionError(f'the worker exited ({proc.returncode}) with job.json {rec and rec["status"]}: '
                                 f'{rec and rec.get("error")}')
        time.sleep(0.1)
    raise AssertionError(f'no status {statuses} after {timeout:.0f} s; last: {last and last["status"]}')


def seed_read(cache_root: Path, sha1: str, name: str, units: str = 'mm', *, auto: bool = True) -> Path:
    """A read entry in the cache as the (fake) reader writes it, without a run: the fixture drawing and plan."""
    import pickle
    import shutil
    from walkthrough_builder import cache
    st = cache.read_staging(cache_root, sha1, 'seed')
    d = jsonfile.read(kit.UPLOAD_FIXTURES / 'drawing' / 'bank1.drawing.json')
    d['source'] = {'sha1': sha1, 'name': name}
    d['units']['used'] = units
    jsonfile.write(st / 'drawing.json', d)
    shutil.copyfile(kit.UPLOAD_FIXTURES / 'plan' / 'bank1.plan.json.gz', st / 'plan.json.gz')
    with open(st / 'items.pkl', 'wb') as f:
        pickle.dump({'items': [], 'layers': {}, 'units': units}, f)
    return cache.commit_read(cache_root, sha1, st, units, auto=auto)


def make_small_dxf(out: Path) -> Path:
    """tools/upload/make-test-dxf.py small (deterministic, sha1 SMALL_SHA1)."""
    p = subprocess.run([sys.executable, '-B', '-P', str(kit.APP / 'tools' / 'upload' / 'make-test-dxf.py'), 'small',
                        str(out)], capture_output=True, text=True, env=kit.child_env(), timeout=300)
    assert p.returncode == 0, p.stderr
    return out


def check_file(kind: str, path: Path, model: Path | None = None) -> tuple[int, str]:
    """The API's record check (`walkthrough_api.check_file`) on one file, in the API's own Python."""
    env = dict(os.environ, PYTHONPATH=str(kit.APP / 'services' / 'api'), PYTHONIOENCODING='utf-8', PYTHONUTF8='1',
               PYTHONDONTWRITEBYTECODE='1')
    cmd = [str(API_PYTHON), '-B', '-m', 'walkthrough_api.check_file', kind, str(path)]
    if model is not None:
        cmd += ['--model', str(model)]
    p = subprocess.run(cmd, cwd=str(kit.APP), env=env, capture_output=True, text=True, encoding='utf-8',
                       timeout=300)
    return p.returncode, (p.stdout + p.stderr)
