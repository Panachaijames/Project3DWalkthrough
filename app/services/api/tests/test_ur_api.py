"""UR (the review-and-fix step of the upload milestone, docs/upload/contract-issues/UR.md): the API's fixes, each with the
case the verifiers found, through the API with the FakeJobRunner.

  * V3-1  picking the office on the Save step of a project with none (a settings save after the build) no longer makes
          the finished build stale: Save works, and the version, project-settings.json and the office memory take the
          office; any other change still makes it stale;
  * V3-4  a draft whose first reading ended interrupted, cancelled or failed is read again by runBuild (it answered 409
          not_prepared for ever);
  * V3-9  a failed conversion's report reaches the Files step (verdict 'failed' with its notes);
  * V2-10 the upload size refusal is said in MB, as the screen shows sizes.
"""
from __future__ import annotations

import copy
import json
import re
import shutil
import subprocess
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from kit import APP, make_client
from test_u5_builds import err, new_project, ready, runs_dir, save_settings, start
from upkit import DEAD_PID, SHA1, FakeJobRunner, load
from walkthrough_api.jsonio import dumps_pretty

P = '/api/projects'
MIB = 1024 * 1024
SAVE = {'label': '9 Nov 2026: built from the two bank drawings', 'carryHeights': True, 'rememberMapping': True}


@pytest.fixture
def fake() -> FakeJobRunner:
    return FakeJobRunner()


@pytest.fixture
def api(data_copy: Path, template_file: Path, fake: FakeJobRunner) -> Iterator[TestClient]:
    with make_client(data_copy, template_file, jobs=fake) as c:
        yield c


def built_without_office(api: TestClient) -> dict:
    pid = new_project(api)                                        # no office
    b = ready(api, pid)
    assert b['settings']['office'] is None
    r = api.post(f'{b["url"]}/run', json={})
    assert r.status_code == 202 and r.json()['result'] is not None, r.text[:300]
    return r.json()


# ================================================================================================================ V3-1
def test_the_office_picked_at_save_keeps_the_build_saveable(api: TestClient, data_copy: Path) -> None:
    b = built_without_office(api)
    assert b['result']['stale'] is False
    s = copy.deepcopy(b['settings'])
    s['office'] = 'ur-office'
    r = save_settings(api, b, s, reviewed=False)
    assert r.status_code == 200, r.text[:300]
    d = r.json()
    assert d['settingsRevision'] == b['settingsRevision'] + 1
    assert d['result']['stale'] is False and d['result']['settingsRevision'] == b['settingsRevision']
    r = api.post(f'{b["url"]}/save', json=SAVE)
    assert r.status_code == 201, r.text[:400]
    pid = b['projectId']
    vdir = data_copy / 'projects' / pid / 'versions' / '1'
    assert load(vdir / 'project-data.json')['office'] == 'ur-office'
    assert load(data_copy / 'projects' / pid / 'project-settings.json')['office'] == 'ur-office'
    office = load(data_copy / 'mappings' / 'ur-office.json')
    assert office['id'] == 'ur-office' and office['layers']['A-WALL']['role'] == 'wall'


def test_any_other_change_still_makes_the_build_stale(api: TestClient) -> None:
    b = built_without_office(api)
    s = copy.deepcopy(b['settings'])
    s['office'] = 'ur-office'
    s['layers']['A-WALL'] = 'other'
    d = save_settings(api, b, s, reviewed=False).json()
    assert d['result']['stale'] is True
    err(api.post(f'{b["url"]}/save', json=SAVE), 409, 'stale')
    # back to the built recipe, the office kept: saveable again
    s['layers']['A-WALL'] = 'wall'
    d = save_settings(api, d, s, reviewed=False).json()
    assert d['result']['stale'] is False


# ================================================================================================================ V3-4
def _first_prepare_ends(api: TestClient, fake: FakeJobRunner, data_copy: Path, how: str) -> dict:
    fake.mode = 'running'
    pid = new_project(api)
    b = start(api, pid)
    run = runs_dir(data_copy, pid, b['id']) / '0001-prepare'
    job = load(run / 'job.json')
    if how == 'interrupted':
        job.update(pid=DEAD_PID, procStart='133000000000000000')   # the worker is gone (a restart): marked interrupted
    else:
        job.update(status=how, finishedAt='2026-11-09T00:00:01Z',
                   error={'code': 'cancelled' if how == 'cancelled' else 'convert_failed', 'message': 'It stopped.',
                          'step': 'convert:0'})
    (run / 'job.json').write_bytes(dumps_pretty(job))
    fake.mode = 'done'
    d = api.get(b['url']).json()
    assert d['run']['status'] == how and d['settingsRevision'] == 0
    return d


@pytest.mark.parametrize('how', ['interrupted', 'cancelled', 'failed'])
def test_a_first_reading_that_did_not_finish_is_read_again(api: TestClient, fake: FakeJobRunner, data_copy: Path,
                                                           how: str) -> None:
    d = _first_prepare_ends(api, fake, data_copy, how)
    r = api.post(f'{d["url"]}/run', json={})
    assert r.status_code == 202, r.text[:300]
    assert fake.started[-1].name == '0002-prepare'
    spec = load(fake.started[-1] / 'spec.json')
    assert spec['kind'] == 'prepare' and spec['only'] is None
    d = api.get(d['url']).json()
    assert d['run']['id'] == '0002-prepare' and d['run']['status'] == 'done' and d['settingsRevision'] == 1


def test_a_first_reading_still_going_is_not_read_twice(api: TestClient, fake: FakeJobRunner) -> None:
    fake.mode = 'running'
    pid = new_project(api)
    b = start(api, pid)
    err(api.post(f'{b["url"]}/run', json={}), 409, 'run_in_progress')
    assert len(fake.started) == 1


# ================================================================================================================ V3-9
def _failed_report(sha1: str, name: str, note: str) -> dict:
    return {
        'format': 'conversion-report/1',
        'source': {'sha1': sha1, 'name': name, 'bytes': 500287, 'kind': 'dwg', 'formatVersion': 'AC1032'},
        'converter': {'name': 'libredwg', 'version': '0.14', 'exeSha1': 'e' * 40}, 'dxf': None,
        'seconds': 120.0, 'peakMemoryMB': 2047.0, 'exitCode': None,
        'messages': [{'class': 'error:Invalid CMC', 'count': 3, 'example': 'ERROR: Invalid CMC flag 0x9f ignored'}],
        'totals': {'dwgEntities': None, 'dxfEntities': None, 'missing': 0, 'extra': 0, 'layerChanged': 0,
                   'emptyLayer': 0},
        'byLayer': [], 'lostBlocks': [], 'renamedBlocks': [], 'unknownObjects': 0, 'verdict': 'failed', 'notes': [note],
    }


def test_a_failed_conversion_reaches_the_files_step(api: TestClient, fake: FakeJobRunner, data_copy: Path) -> None:
    d = _first_prepare_ends(api, fake, data_copy, 'failed')
    note = (f'{d["sourceNames"][0]} could not be converted: the converter took longer than 120 s and was stopped. '
            f'Export a DXF from AutoCAD and upload it instead.')
    rep = runs_dir(data_copy, d['projectId'], d['id']) / '0001-prepare' / 'out' / 'sources' / SHA1 / 'conversion.json'
    rep.parent.mkdir(parents=True, exist_ok=True)
    rep.write_bytes(dumps_pretty(_failed_report(SHA1, d['sourceNames'][0], note)))
    src = api.get(d['url']).json()['sources'][0]
    assert src['conversion'] == {'verdict': 'failed', 'notes': [note], 'lostInModelSpace': 0}
    assert src['urls'] is None and src['units'] is None
    # a report that does not pass its record check is not used
    bad = _failed_report(SHA1, d['sourceNames'][0], note)
    bad['verdict'] = 'gone'
    rep.write_bytes(json.dumps(bad).encode('utf-8'))
    assert api.get(d['url']).json()['sources'][0]['conversion'] is None
    # once the drawings are read again, the new reading is what the step shows
    rep.write_bytes(dumps_pretty(_failed_report(SHA1, d['sourceNames'][0], note)))
    assert api.post(f'{d["url"]}/run', json={}).status_code == 202
    src = api.get(d['url']).json()['sources'][0]
    assert src['conversion']['verdict'] == 'ok' and src['urls'] is not None


# =============================================================================================================== V2-15
def test_a_name_without_letters_makes_no_id(api: TestClient) -> None:
    r = api.post(P, json={'name': 'บ้านสุขุมวิท ซอย 31'})
    assert r.status_code == 201, r.text[:300]
    assert re.fullmatch(r'project-[0-9a-f]{6}', r.json()['id'])
    assert api.post(P, json={'name': 'Sukhumvit 31'}).json()['id'] == 'sukhumvit-31'


@pytest.mark.parametrize('wanted', ['ab-', 'a--b', 'x-'])
def test_an_id_with_a_dangling_or_double_hyphen_is_refused(api: TestClient, wanted: str) -> None:
    e = err(api.post(P, json={'name': 'Bank', 'id': wanted}), 422, 'bad_project')
    assert 'hyphen' in e['message']


# =============================================================================================================== V3-10
def test_the_additive_check_compares_with_the_foundation() -> None:
    """`node tools/check-openapi-additive.mjs` with no --base compares the API with the foundation's baseline commit, not
    with HEAD (which holds the milestone itself since 12921b9, so it compared the API with itself)."""
    node = shutil.which('node')
    if node is None:
        pytest.skip('node is not on PATH')
    r = subprocess.run([node, 'tools/check-openapi-additive.mjs'], cwd=APP, capture_output=True, text=True,
                       encoding='utf-8', timeout=300)
    assert r.returncode == 0, (r.stdout + r.stderr)[-2000:]
    assert 'ok (additive against 9eb2d5819784472821ad6a8b0c11eba642a27d0b)' in r.stdout
    # the foundation's 13 operations, not the milestone's 37 compared with themselves
    assert 'openapi: 13 old operations and 18 old schemas unchanged' in r.stdout


# =============================================================================================================== V2-10
def test_the_size_refusal_is_said_in_mb(api: TestClient) -> None:
    e = err(api.post('/api/uploads', json={'projectId': 'bank-sampeng', 'fileName': 'site.dwg', 'bytes': 315_621_376}),
            413, 'too_large')
    assert e['message'] == 'site.dwg is 315.6 MB; at most 314.6 MB can be uploaded'
