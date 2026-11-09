"""The worker (job.py) as the API runs it: its own process, the machine lock, the steps of both run kinds, job.json, the
cache, cancel, self-stop and the wall clock (docs/upload/DESIGN.md U-3, U-4.2; ACCEPTANCE A-3 and 2.1 U1).

Marker `worker`: these tests spawn job.py and never take the machine run lock themselves (the worker does); a wait
behind another builder's run is reported as "queued", not as a failure. U2's reader and suggestions, U3's build and
U4's outputs are FAKES (step.py's registry, test_u1_support.FAKES) writing the scaffold's fixtures, so the worker's own
parts run for real: dwg2dxf, the loss check, the ezdxf audit, the cache, job.json, and `validate` with the API's
check_file. Tests about the lock itself use a private lock (WALKTHROUGH_RUN_LOCK)."""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

import kit
import test_u1_support as S
from walkthrough_builder import READER_VERSION, cache, jsonfile, oslock, runio

pytestmark = pytest.mark.worker
FINAL = ('done', 'failed', 'cancelled', 'interrupted')
ABS_PATH = re.compile(r'[A-Za-z]:[\\/]')
PREPARE_OUT = {'proposed-settings.json', 'suggestions.json'}
BUILD_OUT = {'Bangkok_Bank_Sampeng.ms', 'diff.json', 'inputs.json', 'model.json', 'openings.json', 'overlay.json',
             'pieces.json', 'presentation.json', 'report.json', 'stages.json', 'topview.png'}


@pytest.fixture(scope='module')
def small_dxf(tmp_path_factory: pytest.TempPathFactory) -> Path:
    out = S.make_small_dxf(tmp_path_factory.mktemp('small') / 'small.dxf')
    assert cache.sha1_file(out) == S.SMALL_SHA1
    return out


@pytest.fixture
def fakes(tmp_path: Path) -> Path:
    return S.write_fakes(tmp_path / 'fakes')


def run(tmp: Path, worker, run_dir: Path, fakes: Path | None, mode: dict | None = None, **env) -> tuple[dict, subprocess.Popen]:
    p = S.start_worker(run_dir, S.worker_env(fakes, mode, **env), tmp / 'logs')
    rec = S.wait_status(run_dir, worker, FINAL, proc=p)
    return rec, p


def steps(rec: dict) -> list[tuple[str, str]]:
    return [(s['name'], s['status']) for s in rec['steps']]


def assert_clean_record(run_dir: Path, rec: dict) -> None:
    """job.json passes the API's record check; no message names a server path; out/tmp is gone."""
    code, out = S.check_file('job', run_dir / 'job.json')
    assert code == 0, out
    for m in rec['messages']:
        assert not ABS_PATH.search(m['text']), m
    if rec.get('error'):
        assert not ABS_PATH.search(rec['error']['message']), rec['error']
    assert not (run_dir / 'out' / 'tmp').exists()


def assert_outputs(run_dir: Path, rec: dict) -> None:
    for name, row in rec['outputs'].items():
        p = run_dir / 'out' / name
        assert p.is_file() and p.stat().st_size == row['bytes'] and cache.sha1_file(p) == row['sha1'], name


# ========================================================================================================= prepare
def test_prepare_then_build_a_dwg(worker, tmp_path: Path, fakes: Path, libredwg: Path) -> None:
    """Prepare: convert, check, read (fake), suggest (fake) -> the per-source files, the suggestions and the proposal;
    then a build from the proposal: ensure (cache hits), the build child (fake), validate (the API's checks)."""
    cache_dir = tmp_path / 'cache'
    src = [S.source(S.BANK1, S.BANK1_SHA1)]
    run_dir = S.make_run(tmp_path, 'prepare', src, cache=cache_dir)
    rec, p = run(tmp_path, worker, run_dir, fakes)
    assert rec['status'] == 'done', rec['error']
    assert steps(rec) == [('convert:0', 'done'), ('check:0', 'done'), ('read:0', 'done'), ('suggest', 'done')]
    assert rec['steps'][1]['note'] == 'ok' and rec['progress'] == 1.0 and rec['error'] is None
    assert rec['startedAt'] and rec['finishedAt'] and rec['queuedAt'] <= rec['startedAt'] <= rec['finishedAt']
    assert rec['pid'] == p.pid and rec['procStart'].isdigit()      # the launcher's pair, as launch.json has it
    base = f'sources/{S.BANK1_SHA1}'
    assert set(rec['outputs']) == PREPARE_OUT | {f'{base}/conversion.json', f'{base}/drawing.json',
                                                 f'{base}/plan.json.gz'}
    assert_outputs(run_dir, rec)
    assert_clean_record(run_dir, rec)
    out = run_dir / 'out'
    conv = jsonfile.read(out / base / 'conversion.json')
    assert conv['verdict'] == 'ok' and conv['dxf']['sha1'] == '9167d084f7e311b59e7c2cdb2bae8506d96a4cfa'
    assert conv['dxf']['auditFixes'] == 24 and conv['source']['formatVersion'] == 'AC1024'
    assert conv['source']['name'] == S.BANK1.name and conv['converter']['version'] == '0.14'
    for kind, f in (('conversion', out / base / 'conversion.json'), ('drawing', out / base / 'drawing.json'),
                    ('plan', out / base / 'plan.json.gz'), ('suggestions', out / 'suggestions.json')):
        code, msg = S.check_file(kind, f)
        assert code == 0, (kind, msg)
    # the cache: one conversion entry, one read entry and its auto pointer
    entry = cache_dir / S.BANK1_SHA1
    conv_dir = cache.conversion_entry(cache_dir, S.BANK1_SHA1, 'libredwg-0.14')
    assert conv_dir is not None and cache.sha1_file(conv_dir / 'plan.dxf') == conv['dxf']['sha1']
    assert cache.read_entry(cache_dir, S.BANK1_SHA1, None) == entry / f'read-{READER_VERSION}-mm'
    assert (out / base / 'plan.json.gz').read_bytes() == (entry / f'read-{READER_VERSION}-mm' / 'plan.json.gz').read_bytes()
    assert not [d for d in entry.iterdir() if 'tmp' in d.name]
    log = (run_dir / 'log.txt').read_text(encoding='utf-8')
    assert 'dwg2dxf (convert:0)' in log and 'check (check:0)' in log and 'audit (check:0)' in log

    # ---- the build, from the proposal
    settings = jsonfile.read(out / 'proposed-settings.json')
    brun = S.make_run(tmp_path, 'build', src, cache=cache_dir, settings=settings)
    ctxfile = tmp_path / 'ctx.json'
    brec, _ = run(tmp_path, worker, brun, fakes, {'ctxfile': str(ctxfile)})
    ctx = jsonfile.read(ctxfile)
    assert ctx['converter'] == conv['converter']
    (s,) = ctx['sources']
    assert s['dxfSha1'] == conv['dxf']['sha1'] and s['units'] == 'mm' and s['kind'] == 'dwg'
    assert ctx['_conversions'] == [conv]                          # the report in sheet metres, as published
    assert brec['status'] == 'done', brec['error']
    assert steps(brec) == [(n, 'done') for n in ('ensure', 'align', 'detect:L1', 'walls', 'openings', 'furniture',
                                                 'outputs', 'validate')]
    assert set(brec['outputs']) == BUILD_OUT
    assert_outputs(brun, brec)
    assert_clean_record(brun, brec)
    assert any(m['text'] == 'fake build with 1 sources' for m in brec['messages'])
    assert brec['steps'][2]['seconds'] is not None
    # the BuildContext the build child got (U-10.8)
    log = (brun / 'log.txt').read_text(encoding='utf-8')
    assert 'build (build)' in log and 'check_file (validate)' in log

    # ---- a second prepare of the same file: every step a cache hit
    run2 = S.make_run(tmp_path / 'again', 'prepare', src, cache=cache_dir)
    rec2, _ = run(tmp_path, worker, run2, fakes)
    assert rec2['status'] == 'done'
    assert [s['note'] for s in rec2['steps'][:3]] == ['already converted', 'already checked', 'already read']
    assert jsonfile.read(run2 / 'out' / base / 'conversion.json') == conv


def test_build_context_of_a_dxf_upload(worker, tmp_path: Path, fakes: Path, small_dxf: Path) -> None:
    """The BuildContext of U-10.8 (exactly its keys) that the build child receives, from the cache; a DXF upload has
    no conversion; the previous run's and the latest version's models; the child's environment (U-3.5)."""
    from walkthrough_builder.contracts import BuildContext, SourceContext
    cache_dir = tmp_path / 'cache'
    d = S.seed_read(cache_dir, S.SMALL_SHA1, 'small.dxf', 'mm')
    src = [S.source(small_dxf, S.SMALL_SHA1, kind='dxf', name='small.dxf', units='mm')]
    prev = tmp_path / 'prev-run'
    (prev / 'out').mkdir(parents=True)
    shutil.copyfile(kit.FIXTURES / 'models' / 'bank-v2.model.json', prev / 'out' / 'model.json')
    vm = kit.FIXTURES / 'models' / 'bank-v2.model.json'
    run_dir = S.make_run(tmp_path, 'build', src, cache=cache_dir, previous_run=str(prev), version_model=str(vm))
    ctxfile = tmp_path / 'ctx.json'
    rec, _ = run(tmp_path, worker, run_dir, fakes, {'ctxfile': str(ctxfile)})
    assert rec['status'] == 'done', rec['error']
    ctx = jsonfile.read(ctxfile)
    env = ctx.pop('_env')
    conversions = ctx.pop('_conversions')
    assert set(ctx) == set(BuildContext.__annotations__)
    assert ctx['spec'] == jsonfile.read(run_dir / 'spec.json')
    (s,) = ctx['sources']
    assert set(s) == set(SourceContext.__annotations__)
    assert s == {'sha1': S.SMALL_SHA1, 'name': 'small.dxf', 'kind': 'dxf', 'units': 'mm', 'conversion': None,
                 'drawing': str(d / 'drawing.json'), 'items': str(d / 'items.pkl'), 'plan': str(d / 'plan.json.gz'),
                 'dxfSha1': None}
    assert conversions == [None] and ctx['converter'] is None
    assert ctx['previousRunModel'] == str(prev / 'out' / 'model.json') and ctx['versionModel'] == str(vm)
    assert ctx['outDir'] == str(run_dir / 'out') and ctx['tmpDir'] == str(run_dir / 'out' / 'tmp' / 'build')
    assert env['OPENINGS_DATA'].startswith(str(run_dir / 'out' / 'tmp'))
    assert env['OPENBLAS_NUM_THREADS'] == '1' and env['MPLBACKEND'] == 'Agg' and env['PYTHONDONTWRITEBYTECODE'] == '1'


def test_dxf_upload_is_not_converted(worker, tmp_path: Path, fakes: Path, small_dxf: Path) -> None:
    src = [S.source(small_dxf, S.SMALL_SHA1, kind='dxf', name='small.dxf')]
    run_dir = S.make_run(tmp_path, 'prepare', src, cache=tmp_path / 'cache')
    rec, _ = run(tmp_path, worker, run_dir, fakes)
    assert rec['status'] == 'done', rec['error']
    assert steps(rec) == [('read:0', 'done'), ('suggest', 'done')]
    conv = jsonfile.read(run_dir / 'out' / 'sources' / S.SMALL_SHA1 / 'conversion.json')
    assert conv['verdict'] == 'not-converted' and conv['converter'] is None
    assert conv['notes'] == ["Exported by the drawing's own program: no conversion to check."]
    assert conv['dxf']['sha1'] == S.SMALL_SHA1 and conv['dxf']['bytes'] == small_dxf.stat().st_size
    assert conv['dxf']['auditFixes'] == jsonfile.read(kit.UPLOAD_FIXTURES / 'drawing' / 'bank1.drawing.json')['dxf'][
        'auditFixes']                                              # from the read (the fake's drawing.json)
    code, out = S.check_file('conversion', run_dir / 'out' / 'sources' / S.SMALL_SHA1 / 'conversion.json')
    assert code == 0, out
    assert_clean_record(run_dir, rec)


def test_one_source_prepare_after_a_units_change(worker, tmp_path: Path, fakes: Path, libredwg: Path) -> None:
    """spec.only = [sha1] with new units: that source's read only (the conversion a cache hit), no suggest (U-3.1,
    U-7.4); the read lands in read-<rv>-cm and the auto pointer still names what the reader chose."""
    cache_dir = tmp_path / 'cache'
    src = [S.source(S.BANK1, S.BANK1_SHA1)]
    rec, _ = run(tmp_path, worker, S.make_run(tmp_path, 'prepare', src, cache=cache_dir), fakes)
    assert rec['status'] == 'done'
    src_cm = [dict(src[0], units='cm')]
    run_dir = S.make_run(tmp_path, 'prepare', src_cm, cache=cache_dir, run_id='0002-prepare', only=[S.BANK1_SHA1])
    rec, _ = run(tmp_path, worker, run_dir, fakes)
    assert rec['status'] == 'done', rec['error']
    assert steps(rec) == [('read:0', 'done')]
    out = run_dir / 'out'
    assert not (out / 'suggestions.json').exists() and not (out / 'proposed-settings.json').exists()
    assert set(rec['outputs']) == {f'sources/{S.BANK1_SHA1}/{n}' for n in ('conversion.json', 'drawing.json',
                                                                          'plan.json.gz')}
    assert jsonfile.read(out / 'sources' / S.BANK1_SHA1 / 'drawing.json')['units']['used'] == 'cm'
    assert jsonfile.read(out / 'sources' / S.BANK1_SHA1 / 'conversion.json')['verdict'] == 'ok'
    assert cache.read_entry(cache_dir, S.BANK1_SHA1, 'cm') is not None
    assert jsonfile.read(cache.auto_pointer(cache_dir, S.BANK1_SHA1)) == {'units': 'mm'}
    assert_clean_record(run_dir, rec)


def test_conversion_cleared_from_the_cache_is_converted_again(worker, tmp_path: Path, fakes: Path,
                                                              libredwg: Path) -> None:
    """A build whose cache entry was evicted converts, checks and reads again in its `ensure` step."""
    cache_dir = tmp_path / 'cache'
    src = [S.source(S.BANK1, S.BANK1_SHA1, units='mm')]
    run_dir = S.make_run(tmp_path, 'build', src, cache=cache_dir)
    rec, _ = run(tmp_path, worker, run_dir, fakes)
    assert rec['status'] == 'done', rec['error']
    assert any('converted again' in m['text'] for m in rec['messages'])
    assert cache.conversion_entry(cache_dir, S.BANK1_SHA1, 'libredwg-0.14') is not None
    assert cache.read_entry(cache_dir, S.BANK1_SHA1, 'mm') is not None


# ========================================================================================================= failures
def test_read_memory(worker, tmp_path: Path, fakes: Path, small_dxf: Path) -> None:
    """A MemoryError inside the read (U2's walk re-raises it): exit 75 -> read_memory; never a partial done."""
    src = [S.source(small_dxf, S.SMALL_SHA1, kind='dxf', name='small.dxf')]
    run_dir = S.make_run(tmp_path, 'prepare', src, cache=tmp_path / 'cache')
    rec, p = run(tmp_path, worker, run_dir, fakes, {'read': 'memory'})
    assert rec['status'] == 'failed' and rec['error']['code'] == 'read_memory' and rec['error']['step'] == 'read:0'
    assert steps(rec) == [('read:0', 'failed'), ('suggest', 'skipped')]
    assert rec['outputs'] == {} and p.returncode == 1
    assert not list((tmp_path / 'cache' / S.SMALL_SHA1).glob('read-*-mm'))
    assert_clean_record(run_dir, rec)


def test_read_failure_names_no_server_path(worker, tmp_path: Path, fakes: Path, small_dxf: Path) -> None:
    src = [S.source(small_dxf, S.SMALL_SHA1, kind='dxf', name='small.dxf')]
    run_dir = S.make_run(tmp_path, 'prepare', src, cache=tmp_path / 'cache')
    rec, _ = run(tmp_path, worker, run_dir, fakes, {'read': 'fail'})
    assert rec['error']['code'] == 'read_failed'
    assert rec['error']['message'] == 'small.dxf could not be read: the walk broke at plan.dxf line 7.'
    assert_clean_record(run_dir, rec)
    assert 'C:\\Users\\someone' in (run_dir / 'log.txt').read_text(encoding='utf-8')     # the detail stays in the log


def test_read_time_limit(worker, tmp_path: Path, fakes: Path, small_dxf: Path) -> None:
    src = [S.source(small_dxf, S.SMALL_SHA1, kind='dxf', name='small.dxf')]
    limits = {'convert': {'seconds': 120, 'memoryMB': 2048}, 'check': {'seconds': 180, 'memoryMB': 1024},
              'read': {'seconds': 2, 'memoryMB': 4096}, 'build': {'seconds': 900, 'memoryMB': 4096}}
    run_dir = S.make_run(tmp_path, 'prepare', src, cache=tmp_path / 'cache', limits=limits)
    rec, _ = run(tmp_path, worker, run_dir, fakes, {'read': 'sleep', 'sleep': 60})
    assert rec['error']['code'] == 'read_timeout' and 'longer than 2 s' in rec['error']['message']


def test_build_keeps_a_steps_own_error_code(worker, tmp_path: Path, fakes: Path, small_dxf: Path) -> None:
    cache_dir = tmp_path / 'cache'
    S.seed_read(cache_dir, S.SMALL_SHA1, 'small.dxf', 'mm')
    src = [S.source(small_dxf, S.SMALL_SHA1, kind='dxf', name='small.dxf', units='mm')]
    run_dir = S.make_run(tmp_path, 'build', src, cache=cache_dir)
    rec, _ = run(tmp_path, worker, run_dir, fakes, {'build': 'fail_code'})
    assert rec['status'] == 'failed'
    assert rec['error'] == {'code': 'area_empty', 'message': "Level 1's area holds no wall.", 'step': 'detect:L1'}
    assert dict(steps(rec))['detect:L1'] == 'failed' and dict(steps(rec))['validate'] == 'skipped'


def test_invalid_output(worker, tmp_path: Path, fakes: Path, small_dxf: Path) -> None:
    cache_dir = tmp_path / 'cache'
    S.seed_read(cache_dir, S.SMALL_SHA1, 'small.dxf', 'mm')
    src = [S.source(small_dxf, S.SMALL_SHA1, kind='dxf', name='small.dxf', units='mm')]
    run_dir = S.make_run(tmp_path, 'build', src, cache=cache_dir)
    rec, _ = run(tmp_path, worker, run_dir, fakes, {'outputs': 'no_parts'})
    assert rec['status'] == 'failed' and rec['error']['code'] == 'invalid_output' and rec['error']['step'] == 'validate'
    assert 'model.json: the model has no parts' in rec['error']['message']
    assert rec['outputs'] == {}


def test_no_floors_and_no_units(worker, tmp_path: Path, fakes: Path, small_dxf: Path) -> None:
    src = [S.source(small_dxf, S.SMALL_SHA1, kind='dxf', name='small.dxf')]
    st = S.bank_settings(src)
    st['floors'] = []
    rec, _ = run(tmp_path, worker, S.make_run(tmp_path, 'build', src, cache=tmp_path / 'c', settings=st), fakes)
    assert rec['error']['code'] == 'no_floors'
    st = S.bank_settings(src, units=None)
    rec, _ = run(tmp_path, worker, S.make_run(tmp_path / 'b', 'build', src, cache=tmp_path / 'c', settings=st), fakes)
    assert rec['error']['code'] == 'bad_settings' and 'no units yet' in rec['error']['message']


def test_pre_r13_dwg_is_refused(worker, tmp_path: Path, fakes: Path, libredwg: Path) -> None:
    old = tmp_path / 'old.dwg'
    old.write_bytes(b'AC1009' + b'\x00' * 2000)
    src = [S.source(old, 'd' * 40, name='old.dwg')]
    run_dir = S.make_run(tmp_path, 'prepare', src, cache=tmp_path / 'cache')
    rec, _ = run(tmp_path, worker, run_dir, fakes)
    assert rec['error']['code'] == 'unsupported_version' and rec['error']['step'] == 'convert:0'
    assert 'older than AutoCAD R13 (AC1009)' in rec['error']['message']
    conv = jsonfile.read(run_dir / 'out' / 'sources' / ('d' * 40) / 'conversion.json')
    assert conv['verdict'] == 'failed' and conv['source']['formatVersion'] == 'AC1009'
    code, out = S.check_file('conversion', run_dir / 'out' / 'sources' / ('d' * 40) / 'conversion.json')
    assert code == 0, out


def test_truncated_dwg_fails_to_convert(worker, tmp_path: Path, fakes: Path, libredwg: Path) -> None:
    bad = tmp_path / 'truncated.dwg'
    bad.write_bytes(S.BANK1.read_bytes()[:120_000])
    run_dir = S.make_run(tmp_path, 'prepare', [S.source(bad, 'e' * 40)], cache=tmp_path / 'cache')
    rec, _ = run(tmp_path, worker, run_dir, fakes)
    assert rec['error']['code'] == 'convert_failed' and 'could not be converted' in rec['error']['message']
    assert jsonfile.read(run_dir / 'out' / 'sources' / ('e' * 40) / 'conversion.json')['verdict'] == 'failed'


def test_spec_problems(worker, tmp_path: Path, fakes: Path) -> None:
    empty = tmp_path / 'runs' / 'empty'
    empty.mkdir(parents=True)
    p = S.start_worker(empty, S.worker_env(fakes), tmp_path / 'logs')
    assert p.wait(120) == 2 and not (empty / 'job.json').exists()
    bad = tmp_path / 'runs' / 'bad'
    bad.mkdir()
    (bad / 'spec.json').write_text('{"kind": "prepare", "sources": [', encoding='utf-8')
    p = S.start_worker(bad, S.worker_env(fakes), tmp_path / 'logs')
    assert p.wait(120) == 1
    rec = runio.read_job(bad)
    assert rec['status'] == 'failed' and rec['error']['code'] == 'internal'


def test_path_too_deep(worker, tmp_path: Path, fakes: Path, small_dxf: Path) -> None:
    src = [S.source(small_dxf, S.SMALL_SHA1, kind='dxf', name='small.dxf')]
    run_dir = S.make_run(tmp_path, 'prepare', src, cache=tmp_path / 'cache')
    spec = jsonfile.read(run_dir / 'spec.json')
    spec['paths']['out'] = str(run_dir / ('o' * max(10, 250 - len(str(run_dir)))))
    jsonfile.write(run_dir / 'spec.json', spec)
    rec, _ = run(tmp_path, worker, run_dir, fakes)
    assert rec['error'] == {'code': 'internal', 'step': None,
                            'message': 'The project folder is too deep for Windows: move it or shorten its path.'}


# ================================================================================================ stopping a run
def wait_step(run_dir: Path, worker, name: str, timeout: float | None = None) -> dict:
    t0 = time.monotonic()
    timeout = timeout or worker.timeout
    while time.monotonic() - t0 < timeout:
        rec = S.read_job(run_dir)
        if rec and rec['status'] == 'queued':
            worker.report_queue(time.monotonic() - t0)
        if rec and any(s['name'] == name and s['status'] == 'running' for s in rec['steps']):
            return rec
        if rec and rec['status'] in FINAL:
            raise AssertionError(f'the run ended ({rec["status"]}) before step {name}: {rec["error"]}')
        time.sleep(0.1)
    raise AssertionError(f'step {name} never ran')


def sleeping_build(tmp: Path, small_dxf: Path, **kw) -> Path:
    cache_dir = tmp / 'cache'
    S.seed_read(cache_dir, S.SMALL_SHA1, 'small.dxf', 'mm')
    src = [S.source(small_dxf, S.SMALL_SHA1, kind='dxf', name='small.dxf', units='mm')]
    return S.make_run(tmp, 'build', src, cache=cache_dir, **kw)


def test_cancel_stops_within_seconds_and_writes_nothing_after(worker, tmp_path: Path, fakes: Path,
                                                              small_dxf: Path) -> None:
    run_dir = sleeping_build(tmp_path, small_dxf)
    pidfile = tmp_path / 'build.pid'
    p = S.start_worker(run_dir, S.worker_env(fakes, {'build': 'sleep', 'sleep': 120, 'pidfile': str(pidfile)}),
                       tmp_path / 'logs')
    wait_step(run_dir, worker, 'walls')
    t0 = time.monotonic()
    (run_dir / 'cancel').touch()
    rec = S.wait_status(run_dir, worker, ('cancelled',), proc=p, timeout=30)
    took = time.monotonic() - t0
    assert took < 10, took                                        # U-3.4 promises 15 s (the API kills after it)
    assert rec['error']['code'] == 'cancelled' and rec['finishedAt']
    assert dict(steps(rec))['walls'] == 'skipped' and dict(steps(rec))['validate'] == 'skipped'
    child = int(pidfile.read_text())
    assert not runio.running(child)                               # the build child is gone
    snap = {f: (f.stat().st_size, f.stat().st_mtime_ns, f.read_bytes()) for f in run_dir.rglob('*') if f.is_file()}
    time.sleep(2.0)
    after = {f: (f.stat().st_size, f.stat().st_mtime_ns, f.read_bytes()) for f in run_dir.rglob('*') if f.is_file()}
    assert after == snap                                          # nothing written after `cancelled`
    assert p.returncode == 3
    assert_clean_record(run_dir, rec)


def test_run_folder_removed_the_worker_exits_and_frees_the_lock(worker, tmp_path: Path, fakes: Path,
                                                                small_dxf: Path, private_lock: Path) -> None:
    run_dir = sleeping_build(tmp_path, small_dxf)
    p = S.start_worker(run_dir, S.worker_env(fakes, {'build': 'sleep', 'sleep': 120}), tmp_path / 'logs')
    wait_step(run_dir, worker, 'walls')
    assert oslock.try_acquire(private_lock) is None               # the worker holds it
    shutil.rmtree(run_dir, ignore_errors=True)                    # what a fresh e2e seed does to the data folder
    t0 = time.monotonic()
    p.wait(30)
    took = time.monotonic() - t0
    assert took < 2.0, took                                       # ACCEPTANCE A-3: exits within 2 s
    fd = oslock.try_acquire(private_lock)
    assert fd is not None
    oslock.release(fd)
    shutil.rmtree(run_dir, ignore_errors=True)
    assert not run_dir.exists()


def test_spec_removed_is_interrupted(worker, tmp_path: Path, fakes: Path, small_dxf: Path) -> None:
    run_dir = sleeping_build(tmp_path, small_dxf)
    p = S.start_worker(run_dir, S.worker_env(fakes, {'build': 'sleep', 'sleep': 120}), tmp_path / 'logs')
    wait_step(run_dir, worker, 'walls')
    (run_dir / 'spec.json').unlink()
    rec = S.wait_status(run_dir, worker, ('interrupted',), proc=p, timeout=30)
    assert rec['error']['code'] == 'interrupted' and 'files were removed' in rec['error']['message']
    assert p.returncode == 4


def test_wall_clock(worker, tmp_path: Path, fakes: Path, small_dxf: Path) -> None:
    run_dir = sleeping_build(tmp_path, small_dxf, wall=4)
    rec, p = run(tmp_path, worker, run_dir, fakes, {'build': 'sleep', 'sleep': 120})
    assert rec['status'] == 'interrupted' and rec['error']['code'] == 'interrupted'
    assert 'took longer than' in rec['error']['message'] and p.returncode == 4


def test_two_workers_on_one_lock(worker, tmp_path: Path, fakes: Path, small_dxf: Path, private_lock: Path) -> None:
    """One run at a time on the machine: the second shows `queued` with a message, then runs when the first is done."""
    a = sleeping_build(tmp_path / 'a', small_dxf)
    pa = S.start_worker(a, S.worker_env(fakes, {'build': 'sleep', 'sleep': 8}), tmp_path / 'logs')
    wait_step(a, worker, 'walls')
    src = [S.source(small_dxf, S.SMALL_SHA1, kind='dxf', name='small.dxf')]
    b = S.make_run(tmp_path / 'b', 'prepare', src, cache=tmp_path / 'b' / 'cache')
    pb = S.start_worker(b, S.worker_env(fakes), tmp_path / 'logs')
    queued = S.wait_status(b, worker, ('queued',), timeout=60)
    t0 = time.monotonic()
    while time.monotonic() - t0 < 10 and not any('another build is running' in m['text']
                                                 for m in (S.read_job(b) or {}).get('messages', [])):
        time.sleep(0.2)
    assert any('another build is running' in m['text'] for m in S.read_job(b)['messages'])
    assert queued['startedAt'] is None and S.read_job(a)['status'] == 'running'
    ra = S.wait_status(a, worker, ('done',), proc=pa)
    rb = S.wait_status(b, worker, ('done',), proc=pb)
    assert rb['startedAt'] >= ra['finishedAt']


def test_cancel_while_queued(worker, tmp_path: Path, fakes: Path, small_dxf: Path, private_lock: Path) -> None:
    a = sleeping_build(tmp_path / 'a', small_dxf)
    pa = S.start_worker(a, S.worker_env(fakes, {'build': 'sleep', 'sleep': 120}), tmp_path / 'logs')
    wait_step(a, worker, 'walls')
    b = sleeping_build(tmp_path / 'b', small_dxf)
    pb = S.start_worker(b, S.worker_env(fakes), tmp_path / 'logs')
    S.wait_status(b, worker, ('queued',), timeout=60)
    (b / 'cancel').touch()
    rb = S.wait_status(b, worker, ('cancelled',), proc=pb, timeout=30)
    assert rb['startedAt'] is None and all(s['status'] == 'skipped' for s in rb['steps'])
    (a / 'cancel').touch()
    assert S.wait_status(a, worker, ('cancelled',), proc=pa, timeout=30)['status'] == 'cancelled'


READER = r'''
import json, sys, time
path, stop_on = sys.argv[1], sys.argv[2]
reads = bad = 0
t0 = time.time()
while time.time() - t0 < 600:
    try:
        f = open(path, 'rb')
    except (FileNotFoundError, PermissionError):
        time.sleep(0.002)
        continue
    try:
        data = f.read()
        time.sleep(0.03)                         # hold it open, as a slow poll would
    finally:
        f.close()
    try:
        rec = json.loads(data)
        reads += 1
    except ValueError:
        bad += 1
        continue
    if rec.get('status') in stop_on.split(','):
        break
    time.sleep(0.003)
print(json.dumps({'reads': reads, 'bad': bad}))
'''


def test_job_json_while_a_reader_holds_it_open(worker, tmp_path: Path, fakes: Path, small_dxf: Path) -> None:
    """job.json is replaced while a separate reader process keeps opening it (U-3.2): every read parses and the run
    still ends done."""
    run_dir = sleeping_build(tmp_path, small_dxf)
    reader = subprocess.Popen([sys.executable, '-B', '-c', READER, str(run_dir / 'job.json'), 'done,failed'],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, stdin=subprocess.DEVNULL)
    rec, _ = run(tmp_path, worker, run_dir, fakes, {'build': 'sleep', 'sleep': 3})
    out, err = reader.communicate(timeout=120)
    got = json.loads(out)
    assert rec['status'] == 'done', rec['error']
    assert got['bad'] == 0 and got['reads'] > 20, got


def test_eviction_at_the_start_of_a_run(worker, tmp_path: Path, fakes: Path, small_dxf: Path) -> None:
    """Holding the lock, the worker trims the cache under WALKTHROUGH_CACHE_MAX_GB, least recently used first, never
    the run's own sources; stale staging folders go too."""
    cache_dir = tmp_path / 'cache'
    old = cache_dir / ('f' * 40) / f'read-{READER_VERSION}-mm'
    old.mkdir(parents=True)
    for n in cache.READ_FILES:
        (old / n).write_bytes(os.urandom(600_000))
    cache.write_done(old, cache.READ_FILES)
    os.utime(old / '.done', (time.time() - 86400, time.time() - 86400))
    mine = S.seed_read(cache_dir, S.SMALL_SHA1, 'small.dxf', 'mm')
    os.utime(mine / '.done', (time.time() - 2 * 86400, time.time() - 2 * 86400))     # older still, but the run's own
    stale = cache_dir / S.SMALL_SHA1 / f'read-{READER_VERSION}-tmp-0007-prepare'
    stale.mkdir()
    src = [S.source(small_dxf, S.SMALL_SHA1, kind='dxf', name='small.dxf', units='mm')]
    run_dir = S.make_run(tmp_path, 'build', src, cache=cache_dir)
    rec, _ = run(tmp_path, worker, run_dir, fakes, WALKTHROUGH_CACHE_MAX_GB='0.001')
    assert rec['status'] == 'done', rec['error']
    assert not (cache_dir / ('f' * 40)).exists() and mine.exists() and not stale.exists()
    assert any('Freed space in the drawing cache' in m['text'] for m in rec['messages'])
