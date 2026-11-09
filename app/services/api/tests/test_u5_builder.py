"""Integration with the real worker (docs/upload/ACCEPTANCE.md 2.2 "Integration tests", marker `builder`): the API's
LocalJobRunner starts `walkthrough_builder.job` in the builder's Python on the small synthetic DXF (always) and on the
bank's two DWGs (heavy: the prototype's model bytes, A-1). Like the builder's `worker` tests they never hold the machine
run lock themselves (the worker takes it); a wait for it is reported as a queue wait, not a failure. They skip while the
builder Python, LibreDWG or the builder's modules are missing (stubs), and fail instead under WT_INTEGRATION=1.

Until U1 - U4 land (WORK_BREAKDOWN U5: "written now and skip until U1 - U4 land"), they run only under WT_INTEGRATION=1:
the builder's modules are being written in parallel, and a plain `npm run test:api` must not depend on their state.
The integration step turns RUN_WITHOUT_THE_FLAG on once they have landed (docs/upload/contract-issues/U5.md).
"""
from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import time
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from kit import APP, FIXTURES, RUN, make_client
from upkit import FX, load, upload, upload_bank
from walkthrough_api.settings import Settings

pytestmark = pytest.mark.builder

P = '/api/projects'
BUILDER = APP / 'services' / 'builder' / 'walkthrough_builder'
STUB = 'not built yet (stub by the scaffold U0)'
RUN_TIMEOUT_S = 15 * 60
#: False until U1 - U4 land: without WT_INTEGRATION=1 these tests skip (see the module text)
RUN_WITHOUT_THE_FLAG = False


def builder_missing() -> str | None:
    """Why the real worker cannot run here (None: it can)."""
    if not RUN_WITHOUT_THE_FLAG and os.environ.get('WT_INTEGRATION') != '1':
        return 'the real worker runs under WT_INTEGRATION=1 until U1 - U4 land (WORK_BREAKDOWN U5)'
    s = Settings.from_env({})
    if not s.builder_python.is_file():
        return f'no builder Python at {s.display_path(s.builder_python)}'
    if not (s.libredwg_dir / 'dwg2dxf.exe').is_file():
        return f'no LibreDWG in {s.display_path(s.libredwg_dir)}'
    stubs = sorted(p.relative_to(BUILDER).as_posix() for p in BUILDER.rglob('*.py')
                   if 'vendor' not in p.parts and STUB in p.read_text(encoding='utf-8', errors='replace'))
    if stubs:
        return f'the builder is not built yet (stubs: {", ".join(stubs)})'
    return None


@pytest.fixture
def real(template_file: Path) -> Iterator[TestClient]:
    why = builder_missing()
    if why:
        if os.environ.get('WT_INTEGRATION') == '1':
            pytest.fail(f'WT_INTEGRATION=1: {why}')
        pytest.skip(why)
    data = RUN / 'real-data'
    if data.exists():
        shutil.rmtree(data)
    with make_client(data, template_file) as c:                  # the LocalJobRunner; cache under WT_TMP
        try:
            yield c
        finally:
            c.app.state.jobs.stop_all()


def wait(api: TestClient, url: str, timeout: float = RUN_TIMEOUT_S) -> dict:
    """Polls the build until its run ends; a long queue wait (another builder's drawing) is reported, not failed."""
    t0 = time.monotonic()
    queued = 0.0
    while True:
        d = api.get(url, params={'withSettings': 'false'}).json()
        status = d['run']['status']
        if status not in ('queued', 'running'):
            return api.get(url).json()
        if status == 'queued':
            queued = time.monotonic() - t0
        if time.monotonic() - t0 > timeout + queued:
            pytest.fail(f'run {d["run"]["id"]} still {status} after {time.monotonic() - t0:.0f} s '
                        f'({queued:.0f} s of it queued behind another run)')
        time.sleep(0.5)


def small_dxf(tmp_path: Path) -> bytes:
    out = tmp_path / 'small.dxf'
    subprocess.run(['node', 'tools/run-builder-py.mjs', 'tools/upload/make-test-dxf.py', 'small', str(out)], cwd=APP,
                   check=True, capture_output=True, timeout=300)
    return out.read_bytes()


def described(d: dict) -> str:
    run = d['run'] or {}
    return f'{run.get("status")}: {run.get("error")}; last messages {[m["text"] for m in run.get("messages", [])[-5:]]}'


def test_the_small_dxf_end_to_end(real: TestClient, tmp_path: Path) -> None:
    api = real
    data = small_dxf(tmp_path)
    assert real.post(P, json={'name': 'Small test drawing', 'shortName': 'Small', 'id': 'small-dxf'}).status_code == 201
    src = upload(api, 'small-dxf', data, 'small.dxf')
    assert src['kind'] == 'dxf' and src['sha1'] == load(FX / 'settings' / 'small.json')['sources'][0]['sha1']
    b = api.post(f'{P}/small-dxf/builds', json={'sources': [src['sha1']]}).json()
    launch = load(RUN / 'real-data' / 'projects' / 'small-dxf' / 'builds' / b['id'] / 'runs' / '0001-prepare' /
                  'launch.json')
    assert launch['pid'] > 0 and launch['procStart'].isdigit()
    b = wait(api, b['url'])
    assert b['run']['status'] == 'done', described(b)
    assert b['settingsRevision'] == 1 and b['sources'][0]['conversion']['verdict'] == 'not-converted'
    assert b['sources'][0]['units']['used'] == 'mm'
    for kind in ('conversion', 'drawing', 'plan'):
        assert api.get(b['sources'][0]['urls'][kind]).status_code == 200
    s = load(FX / 'settings' / 'small.json')
    s['project'] = {**s['project'], **{k: b['settings']['project'][k] for k in ('name', 'shortName', 'projectNo',
                                                                                 'photoName', 'maxPrefix', 'maxFileName')}}
    r = api.put(f'{b["url"]}/settings', json={'settings': s, 'layersReviewed': True}, headers={'If-Match': '"1"'})
    assert r.status_code == 200, r.text[:300]
    b = api.post(f'{b["url"]}/run', json={}).json()
    b = wait(api, b['url'])
    assert b['run']['status'] == 'done', described(b)
    assert b['result'] is not None and b['result']['counts']['floors'] == 1
    v = api.post(f'{b["url"]}/save', json={'label': 'small', 'carryHeights': True, 'rememberMapping': False})
    assert v.status_code == 201, v.text[:400]
    model = api.get(f'{P}/small-dxf/versions/1/model').content
    script = api.get(f'{P}/small-dxf/versions/1/downloads/max-script').content
    assert f'(model data {hashlib.sha1(model).hexdigest()[:12]})'.encode() in script.split(b'\n')[1]


def test_the_bank_from_its_dwgs(real: TestClient) -> None:
    """ACCEPTANCE A-1 (a), through the API: the two DWGs, the bank's settings, no fixes; the model bytes are v2's."""
    api = real
    assert api.post(P, json={'name': 'Bangkok Bank, Sampeng Branch', 'shortName': 'Bank branch',
                             'id': 'bank-reupload'}).status_code == 201
    sha1s = upload_bank(api, 'bank-reupload')
    b = api.post(f'{P}/bank-reupload/builds', json={'sources': sha1s}).json()
    b = wait(api, b['url'])
    assert b['run']['status'] == 'done', described(b)
    assert [src['conversion']['verdict'] for src in b['sources']] == ['ok', 'ok']
    s = load(FX / 'settings' / 'bank.json')                     # its own naming and offset, as the fixture has them
    r = api.put(f'{b["url"]}/settings', json={'settings': s, 'layersReviewed': True}, headers={'If-Match': '"1"'})
    assert r.status_code == 200, r.text[:300]
    b = api.post(f'{b["url"]}/run', json={}).json()
    b = wait(api, b['url'])
    assert b['run']['status'] == 'done', described(b)
    model = api.get(f'{b["url"]}/model').content
    assert hashlib.sha1(model).hexdigest() == 'c3a9408304a240b83c36f5c5c53db56b50a72c64'
    v = api.post(f'{b["url"]}/save', json={'label': 'bank re-upload', 'carryHeights': True, 'rememberMapping': False})
    assert v.status_code == 201, v.text[:400]
    assert v.json()['stamp'] == 'c3a9408304a2'
    csv = api.get(f'{P}/bank-reupload/versions/1/downloads/furniture-csv').content
    assert csv == (FIXTURES / 'csv' / 'bank-v2.csv').read_bytes()
    script = api.get(f'{P}/bank-reupload/versions/1/downloads/max-script').content
    assert b'(model data c3a9408304a2)' in script.split(b'\n')[1]
