"""Builds through the API with a FakeJobRunner over fixtures/upload/runs/ (docs/upload/ACCEPTANCE.md 2.2; DESIGN.md U-3,
U-7.4, U-8.3, U-13.1): createBuild and its prepare, the proposal adopted once, settings saves (If-Match, 412, 422, 409
not_prepared, the units change), runBuild's refusals, the result, the draft's raw files, invalid worker outputs,
cancel, delete, listBuilds."""
from __future__ import annotations

import copy
import gzip
import json
import threading
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from kit import FIXTURES, PROTOTYPES, make_client
from upkit import DEAD_PID, FX, SHA1, SHA2, FakeJobRunner, bank_settings, load, upload_bank
from walkthrough_api.jsonio import dumps_pretty, sha1_hex

P = '/api/projects'


def err(r, status: int, code: str) -> dict:
    assert r.status_code == status, (r.status_code, r.text[:400])
    body = r.json()
    assert body['error']['code'] == code, body
    return body['error']


@pytest.fixture
def fake() -> FakeJobRunner:
    return FakeJobRunner()


@pytest.fixture
def api(data_copy: Path, template_file: Path, fake: FakeJobRunner) -> Iterator[TestClient]:
    with make_client(data_copy, template_file, jobs=fake) as c:
        yield c


def new_project(api: TestClient, name: str = 'Bank re-upload', **kw) -> str:
    r = api.post(P, json={'name': name, 'shortName': 'Bank branch', **kw})
    assert r.status_code == 201, r.text[:300]
    return r.json()['id']


def start(api: TestClient, project_id: str, both: bool = True, **body) -> dict:
    sha1s = upload_bank(api, project_id, both)
    r = api.post(f'{P}/{project_id}/builds', json={'sources': sha1s, **body})
    assert r.status_code == 201, r.text[:400]
    return r.json()


def runs_dir(data: Path, project_id: str, build_id: str) -> Path:
    return data / 'projects' / project_id / 'builds' / build_id / 'runs'


def save_settings(api: TestClient, b: dict, settings: dict, reviewed: bool = True, revision: int | None = None):
    rev = b['settingsRevision'] if revision is None else revision
    return api.put(f'{b["url"]}/settings', json={'settings': settings, 'layersReviewed': reviewed},
                   headers={'If-Match': f'"{rev}"'})


def bank_for(b: dict) -> dict:
    """The fixture bank settings with the build's naming (as the Layers / Floors steps would send them)."""
    s = bank_settings()
    s['project'] = {**s['project'], **{k: b['settings']['project'][k] for k in ('name', 'shortName', 'projectNo',
                                                                                 'photoName', 'maxPrefix', 'maxFileName')}}
    s['office'] = b['settings']['office']
    return s


def ready(api: TestClient, project_id: str = '', **kw) -> dict:
    """A new project's build, prepared, adopted and saved once with the bank's settings (reviewed): ready to build."""
    pid = project_id or new_project(api)
    b = start(api, pid, **kw)
    b = api.get(b['url']).json()
    assert b['settingsRevision'] == 1
    r = save_settings(api, b, bank_for(b))
    assert r.status_code == 200, r.text[:400]
    return r.json()


# ------------------------------------------------------------------------------------------------ create, adopt
def test_create_build_prepares_and_adopts_once(api: TestClient, fake: FakeJobRunner, data_copy: Path) -> None:
    pid = new_project(api)
    b = start(api, pid)
    assert b['status'] == 'open' and b['sourceNames'] == ['I1201 - LEVEL 1 GENERAL ARRANGEMENT.dwg',
                                                          'I1202 - LEVEL 2 GENERAL ARRANGEMENT.dwg']
    assert len(fake.started) == 1 and fake.started[0].name == '0001-prepare'
    spec = load(fake.started[0] / 'spec.json')
    assert spec['kind'] == 'prepare' and spec['only'] is None and spec['settingsRevision'] == 0
    assert [s['units'] for s in spec['sources']] == [None, None]
    assert all(Path(s['path']).is_file() and Path(s['path']).name == 'original.dwg' for s in spec['sources'])
    assert spec['paths']['cache'].endswith('cache') and spec['paths']['previousRun'] is None
    assert spec['wallClockSeconds'] == 3600 and spec['limits']['read'] == {'seconds': 300, 'memoryMB': 4096}
    # the first answer already adopted the proposal (the fake's run is done at once)
    assert b['settingsRevision'] == 1 and b['run']['status'] == 'done' and b['run']['kind'] == 'prepare'
    s = b['settings']
    assert [src['units'] for src in s['sources']] == ['mm', 'mm'] and all(src['unitsConfirmed'] for src in s['sources'])
    assert s['project']['name'] == 'Bank re-upload' and s['project']['photoName'] == 'Bank-branch'
    assert s['project']['maxFileName'] == 'Bank_re_upload.ms' and s['project']['maxPrefix'] == 'BRU'
    assert [f['key'] for f in s['floors']] == ['L1', 'L2'] and s['layers']['A-WALL'] == 'wall'
    assert b['suggestions']['A-WALL']['role'] == 'wall' and b['layersReviewedAt'] is None
    api_json = load(runs_dir(data_copy, pid, b['id']) / '0001-prepare' / 'api.json')
    assert api_json['validated'] is True and api_json['adoptedRevision'] == 1 and api_json['issues'] == []
    for src in b['sources']:
        assert src['conversion']['verdict'] == 'ok' and src['units']['used'] == 'mm'
        assert src['urls']['plan'] == f"{b['url']}/sources/{src['sha1']}/plan"
    again = api.get(b['url']).json()
    assert again['settingsRevision'] == 1                                   # adopted once


def test_two_polls_at_once_adopt_once(api: TestClient, fake: FakeJobRunner, data_copy: Path) -> None:
    fake.mode = 'running'
    pid = new_project(api)
    b = start(api, pid)
    assert b['settingsRevision'] == 0 and b['run']['status'] == 'running' and b['settings']['sources'][0]['units'] is None
    fake.finish(fake.started[0])
    answers: list[dict] = []

    def poll() -> None:
        answers.append(api.get(b['url'], params={'withSettings': 'false'}).json())
    threads = [threading.Thread(target=poll) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert [a['settingsRevision'] for a in answers] == [1, 1, 1, 1] and all(a['settings'] is None for a in answers)
    settings_file = load(data_copy / 'projects' / pid / 'builds' / b['id'] / 'settings.json')
    assert settings_file['revision'] == 1
    api_json = load(runs_dir(data_copy, pid, b['id']) / '0001-prepare' / 'api.json')
    assert api_json['validated'] is True and api_json['adoptedRevision'] == 1


def test_settings_cannot_be_saved_before_the_proposal(api: TestClient, fake: FakeJobRunner) -> None:
    fake.mode = 'running'
    pid = new_project(api)
    b = start(api, pid)
    err(save_settings(api, b, bank_settings(), revision=0), 409, 'not_prepared')
    err(api.post(f'{b["url"]}/run', json={}), 409, 'run_in_progress')


def test_with_settings_false(api: TestClient) -> None:
    b = ready(api)
    lean = api.get(b['url'], params={'withSettings': 'false'}).json()
    assert lean['settings'] is None and lean['settingsRevision'] == b['settingsRevision']
    assert api.get(b['url']).json()['settings'] == b['settings']


# ------------------------------------------------------------------------------------------------ settings
def test_if_match_and_revisions(api: TestClient) -> None:
    b = ready(api)
    assert b['settingsRevision'] == 2 and b['layersReviewedAt']
    s = b['settings']
    e = err(save_settings(api, b, s, revision=1), 412, 'revision_conflict')
    assert e['details']['revision'] == 2 and e['details']['settings'] == s
    r = api.put(f'{b["url"]}/settings', json={'settings': s})             # no If-Match: last write wins
    assert r.status_code == 200 and r.json()['settingsRevision'] == 3
    err(api.put(f'{b["url"]}/settings', json={'settings': s}, headers={'If-Match': '*'}), 412, 'revision_conflict')


def test_invalid_settings_get_their_issues(api: TestClient) -> None:
    b = ready(api)
    s = copy.deepcopy(b['settings'])
    s['floors'][1]['level'] = -1.0
    s['floors'][0]['key'] = 'level one'
    s['project']['maxPrefix'] = 'bb'
    e = err(save_settings(api, b, s), 422, 'invalid_settings')
    paths = {i['path'] for i in e['details']['issues']}
    assert {'/floors/1/level', '/floors/0/key', '/project/maxPrefix'} <= paths
    s = copy.deepcopy(b['settings'])
    s['sources'] = s['sources'][::-1]
    e = err(save_settings(api, b, s), 422, 'invalid_settings')
    assert e['details']['issues'][0]['path'] == '/sources'


def test_layers_reviewed_gate(api: TestClient) -> None:
    pid = new_project(api)
    b = api.get(start(api, pid)['url']).json()
    err(api.post(f'{b["url"]}/run', json={}), 409, 'layers_not_reviewed')
    r = save_settings(api, b, b['settings'], reviewed=False)
    assert r.status_code == 200 and r.json()['layersReviewedAt'] is None
    err(api.post(f'{b["url"]}/run', json={}), 409, 'layers_not_reviewed')
    r = save_settings(api, r.json(), b['settings'], reviewed=True)
    stamp = r.json()['layersReviewedAt']
    assert stamp
    r = save_settings(api, r.json(), b['settings'], reviewed=True)
    assert r.json()['layersReviewedAt'] == stamp                          # set once


def test_units_unconfirmed(api: TestClient) -> None:
    b = ready(api)
    s = copy.deepcopy(b['settings'])
    s['sources'][1]['unitsConfirmed'] = False
    b = save_settings(api, b, s).json()
    e = err(api.post(f'{b["url"]}/run', json={}), 409, 'units_unconfirmed')
    assert 'I1202' in e['message']


def test_a_units_change_rescales_and_reads_that_source_again(api: TestClient, fake: FakeJobRunner) -> None:
    b = ready(api)
    s = copy.deepcopy(b['settings'])
    s['floors'][1]['area'] = {'kind': 'box', 'bbox': [1.0, 2.0, 30.0, 40.0], 'pad': 0.5, 'match': 'all'}
    s['floors'][1]['align'] = {'method': 'points', 'pairs': [[[1.0, 1.0], [2.0, 2.0]], [[3.0, 3.0], [4.0, 4.0]]]}
    s['fixes']['openings'] = [{'floor': 'L2', 'a': [1.0, 2.0], 'b': [3.0, 4.0], 'kind': 'none', 'head': None, 'sill': None},
                              {'floor': 'L1', 'a': [1.0, 2.0], 'b': [3.0, 4.0], 'kind': 'door', 'head': 2.2, 'sill': None}]
    s['fixes']['outlineEdges'] = [{'floor': 'L2', 'a': [5.0, 5.0], 'b': [6.0, 5.0], 'as': 'wall'}]
    b = save_settings(api, b, s).json()
    assert len(fake.started) == 1                                          # no units change: no run
    s2 = copy.deepcopy(b['settings'])
    s2['sources'][1]['units'] = 'cm'                                       # mm -> cm: everything of L2's sheet x 10
    r = save_settings(api, b, s2)
    assert r.status_code == 200, r.text[:300]
    got = r.json()['settings']
    assert got['floors'][1]['area']['bbox'] == [10.0, 20.0, 300.0, 400.0] and got['floors'][1]['area']['pad'] == 5.0
    assert got['floors'][1]['align']['pairs'] == [[[1.0, 1.0], [20.0, 20.0]], [[3.0, 3.0], [40.0, 40.0]]]
    assert got['fixes']['openings'][0]['a'] == [10.0, 20.0] and got['fixes']['openings'][1]['a'] == [1.0, 2.0]
    assert got['fixes']['outlineEdges'][0]['b'] == [60.0, 50.0]
    assert got['floors'][0]['area'] == {'kind': 'wholeFile'}
    run = fake.started[-1]
    spec = load(run / 'spec.json')
    assert run.name == '0002-prepare' and spec['only'] == [SHA2] and spec['sources'][1]['units'] == 'cm'
    assert sorted(p.name for p in (run / 'out' / 'sources').iterdir()) == [SHA2]
    assert not (run / 'out' / 'suggestions.json').exists()
    detail = api.get(b['url']).json()
    assert detail['run']['only'] == [SHA2] and detail['run']['status'] == 'done'
    assert detail['settingsRevision'] == 4 and detail['suggestions']            # the full prepare's suggestions stay
    assert detail['sources'][1]['urls'] is not None


def test_a_units_change_while_a_prepare_runs_is_refused(api: TestClient, fake: FakeJobRunner) -> None:
    b = ready(api)
    fake.mode = 'running'
    s = copy.deepcopy(b['settings'])
    s['sources'][0]['units'] = 'm'
    b = save_settings(api, b, s).json()
    assert b['run']['status'] == 'running' and b['run']['only'] == [SHA1]
    err(save_settings(api, b, b['settings']), 409, 'run_in_progress')


# ------------------------------------------------------------------------------------------------ build, result
def test_build_and_its_result(api: TestClient, fake: FakeJobRunner, data_copy: Path) -> None:
    b = ready(api)
    r = api.post(f'{b["url"]}/run', json={})
    assert r.status_code == 202, r.text[:400]
    d = r.json()
    assert d['run']['kind'] == 'build' and d['run']['id'] == '0002-build'
    spec = load(fake.started[-1] / 'spec.json')
    assert spec['kind'] == 'build' and spec['settingsRevision'] == 2 and spec['paths']['previousRun'] is None
    res = d['result']
    assert res['runId'] == '0002-build' and res['stale'] is False and res['stamp'] == 'c3a9408304a2'
    m = load(FIXTURES / 'models' / 'bank-v2.model.json')
    assert res['counts'] == {'floors': 2, 'parts': len(m['parts']), 'openings': len(m['openings']), 'furniture': 185,
                             'furnitureKinds': 14, 'rooms': len(m['rooms'])}
    l1 = [o for o in m['openings'] if o['floor'] == 'L1']
    assert [f['key'] for f in res['floors']] == ['L1', 'L2'] and res['floors'][0]['openings'] == \
        {k: sum(1 for o in l1 if o['kind'] == k) for k in ('door', 'window', 'passage')}
    assert sum(res['floors'][0]['openings'].values()) == 24 and res['floors'][0]['parts'] == \
        sum(1 for p in m['parts'] if p['floor'] == 'L1')
    assert res['flags']['total'] >= 1 and res['presentation']['heading'] == 'Bangkok Bank, Sampeng Branch'
    assert res['urls']['maxScript'] == f'{b["url"]}/max-script'
    # a second build points the diff at the first
    r = api.post(f'{b["url"]}/run', json={})
    spec = load(fake.started[-1] / 'spec.json')
    assert spec['paths']['previousRun'].endswith('0002-build') and r.json()['result']['runId'] == '0003-build'
    # a settings change makes the result stale
    d = save_settings(api, r.json(), r.json()['settings']).json()
    assert d['result']['stale'] is True


def test_raw_files(api: TestClient, data_copy: Path) -> None:
    b = ready(api)
    err(api.get(f'{b["url"]}/model'), 404, 'not_built')
    err(api.get(f'{b["url"]}/max-script'), 404, 'not_built')
    conv = api.get(f'{b["url"]}/sources/{SHA1}/conversion')
    want = (FX / 'conversion' / 'bank1.conversion.json').read_bytes()
    assert conv.status_code == 200 and conv.content == want and conv.headers['etag'] == f'"{sha1_hex(want)}"'
    assert conv.headers['cache-control'] == 'no-cache' and conv.headers['x-content-type-options'] == 'nosniff'
    assert api.get(conv.url, headers={'If-None-Match': conv.headers['etag']}).status_code == 304
    drawing = api.get(f'{b["url"]}/sources/{SHA2}/drawing')
    assert drawing.json()['source']['sha1'] == SHA2
    stored = (FX / 'plan' / 'bank1.plan.json.gz').read_bytes()
    plan = api.get(f'{b["url"]}/sources/{SHA1}/plan', headers={'Accept-Encoding': 'gzip'})
    assert plan.headers['content-encoding'] == 'gzip' and plan.headers['etag'] == f'"{sha1_hex(stored)}"'
    assert plan.content == gzip.decompress(stored)                             # httpx undoes the gzip
    plain = api.get(f'{b["url"]}/sources/{SHA1}/plan', headers={'Accept-Encoding': 'identity'})
    assert 'content-encoding' not in plain.headers and plain.content == gzip.decompress(stored)
    assert plain.headers['etag'] == f'"{sha1_hex(gzip.decompress(stored))}"' and 'Accept-Encoding' in plain.headers['vary']
    err(api.get(f'{b["url"]}/sources/{"0" * 40}/plan'), 404, 'not_ready')
    b = api.post(f'{b["url"]}/run', json={}).json()
    model = api.get(f'{b["url"]}/model')
    v2 = (FIXTURES / 'models' / 'bank-v2.model.json').read_bytes()
    assert model.content == v2 and model.headers['x-model-stamp'] == 'c3a9408304a2'
    assert api.get(f'{b["url"]}/model', headers={'If-None-Match': model.headers['etag']}).status_code == 304
    assert api.get(f'{b["url"]}/stages').content == (FIXTURES / 'stages' / 'bank-v2.stages.json').read_bytes()
    assert api.get(f'{b["url"]}/overlay').json()['format'] == 'build-overlay/1'
    assert api.get(f'{b["url"]}/diff').json()['format'] == 'build-diff/1'
    top = api.get(f'{b["url"]}/topview')
    assert top.headers['content-type'] == 'image/png' and top.content == (PROTOTYPES / 'bank_test' / 'src' / 'bank_topview.png').read_bytes()
    ms = api.get(f'{b["url"]}/max-script')
    assert ms.content == (PROTOTYPES / 'bank_test' / 'Bangkok_Bank_Sampeng.ms').read_bytes()
    assert ms.headers['content-type'] == 'text/plain; charset=utf-8'
    assert ms.headers['content-disposition'] == 'attachment; filename="Bank_re_upload_draft.ms"; ' \
                                                "filename*=UTF-8''Bank_re_upload_draft.ms"
    err(api.get(f'{P}/bank-sampeng/builds/20261104T101500-0a1b2c/model'), 404, 'build_not_found')


INVALID = {
    'model.json': lambda b: b.replace(b'"z1":3.7', b'"z1":-3.7', 1),
    'stages.json': lambda b: json.dumps(dict(json.loads(b), floors={**json.loads(b)['floors'], 'L9': json.loads(b)['floors']['L1']})).encode(),
    'presentation.json': lambda b: json.dumps(dict(json.loads(b), accent='blue')).encode(),
    'overlay.json': lambda b: json.dumps(dict(json.loads(b), floors=[{'key': 'L1'}])).encode(),
    'Bank_re_upload.ms': lambda b: b.replace(b'(model data c3a9408304a2)', b'(model data 000000000000)', 1),
    'topview.png': lambda b: b'GIF89a' + b[6:],
    'pieces.json': lambda _b: None,
}


@pytest.mark.parametrize('name', list(INVALID))
def test_invalid_worker_outputs_fail_the_run(api: TestClient, fake: FakeJobRunner, data_copy: Path, name: str) -> None:
    b = ready(api)
    fake.mutate[name] = INVALID[name]
    d = api.post(f'{b["url"]}/run', json={}).json()
    assert d['run']['status'] == 'failed' and d['run']['error']['code'] == 'invalid_output', d['run']
    assert d['result'] is None
    job = load(runs_dir(data_copy, d['projectId'], d['id']) / '0002-build' / 'job.json')
    api_json = load(runs_dir(data_copy, d['projectId'], d['id']) / '0002-build' / 'api.json')
    assert job['status'] == 'failed' and api_json['validated'] is False and api_json['issues']
    assert any(i.startswith(name.split('.')[0]) or name in i for i in api_json['issues']), api_json['issues']
    err(api.get(f'{b["url"]}/model'), 404, 'not_built')


def test_an_invalid_prepare_is_never_adopted(api: TestClient, fake: FakeJobRunner) -> None:
    fake.mutate[f'sources/{SHA1}/drawing.json'] = lambda b: b.replace(b'"drawing-read/1"', b'"drawing-read/2"', 1)
    pid = new_project(api)
    b = start(api, pid)
    assert b['run']['status'] == 'failed' and b['run']['error']['code'] == 'invalid_output'
    assert b['settingsRevision'] == 0 and b['suggestions'] == {} and b['sources'][0]['urls'] is None
    err(api.get(f'{b["url"]}/sources/{SHA1}/drawing'), 404, 'not_ready')


# ------------------------------------------------------------------------------------------------ in progress, cancel
def test_run_in_progress_and_cancel(api: TestClient, fake: FakeJobRunner) -> None:
    b = ready(api)
    err(api.post(f'{b["url"]}/cancel', json={}), 409, 'no_run')
    fake.mode, fake.honour_cancel = 'running', False
    d = api.post(f'{b["url"]}/run', json={}).json()
    assert d['run']['status'] == 'running' and d['run']['cancelRequested'] is False and d['runStatus'] == 'running'
    err(api.post(f'{b["url"]}/run', json={}), 409, 'run_in_progress')
    err(api.delete(b['url']), 409, 'run_in_progress')
    err(api.post(f'{b["url"]}/save', json={'label': 'x', 'carryHeights': True, 'rememberMapping': True}), 409,
        'run_in_progress')
    d = api.post(f'{b["url"]}/cancel', json={}).json()
    assert d['run']['cancelRequested'] is True and d['run']['status'] == 'running' and len(fake.cancelled) == 1
    d = api.post(f'{b["url"]}/cancel', json={}).json()                      # asked again: no second timer
    assert len(fake.cancelled) == 1 and d['run']['cancelRequested'] is True
    job = fake.cancelled[0] / 'job.json'                                   # the worker answers: its last write
    record = load(job)
    record.update(status='cancelled', finishedAt='2026-11-04T00:00:02Z')
    job.write_bytes(dumps_pretty(record))
    d = api.get(b['url']).json()
    assert d['run']['status'] == 'cancelled' and d['run']['cancelRequested'] is False


def test_a_gone_worker_is_shown_interrupted(api: TestClient, fake: FakeJobRunner, data_copy: Path) -> None:
    b = ready(api)
    fake.mode = 'running'
    api.post(f'{b["url"]}/run', json={})
    job = fake.started[-1] / 'job.json'
    record = load(job)
    record.update(pid=DEAD_PID, procStart='133000000000000000')
    job.write_bytes(dumps_pretty(record))
    d = api.get(b['url']).json()
    assert d['run']['status'] == 'interrupted' and d['run']['error']['code'] == 'interrupted'
    assert load(job)['status'] == 'interrupted'                              # marked on disk under the lock


# ------------------------------------------------------------------------------------------------ list, delete
def test_list_and_delete(api: TestClient, data_copy: Path) -> None:
    pid = new_project(api)
    a = start(api, pid)
    b = start(api, pid, both=False)
    r = api.get(f'{P}/{pid}/builds')
    ids = [x['id'] for x in r.json()['builds']]
    assert r.status_code == 200 and set(ids) == {a['id'], b['id']}
    assert r.json()['builds'][0]['runStatus'] == 'done' and r.json()['builds'][0]['url'].startswith(f'{P}/{pid}/builds/')
    assert api.delete(a['url']).status_code == 204
    assert not (data_copy / 'projects' / pid / 'builds' / a['id']).exists()
    err(api.get(a['url']), 404, 'build_not_found')
    err(api.delete(a['url']), 404, 'build_not_found')
    assert [x['id'] for x in api.get(f'{P}/{pid}/builds').json()['builds']] == [b['id']]
    err(api.get(f'{P}/no-such-project/builds'), 404, 'project_not_found')


# ------------------------------------------------------------------------------------------------ createBuild's refusals
def test_create_build_refusals(api: TestClient, fake: FakeJobRunner) -> None:
    pid = new_project(api)
    sha1s = upload_bank(api, pid)
    err(api.post(f'{P}/{pid}/builds', json={'sources': []}), 422, 'bad_sources')
    err(api.post(f'{P}/{pid}/builds', json={'sources': [sha1s[0], sha1s[0]]}), 422, 'bad_sources')
    err(api.post(f'{P}/{pid}/builds', json={'sources': None}), 422, 'bad_sources')
    err(api.post(f'{P}/{pid}/builds', json={'sources': ['a' * 40]}), 404, 'source_not_found')
    err(api.post(f'{P}/bank-sampeng/builds', json={'sources': sha1s}), 404, 'source_not_found')   # not that project's
    err(api.post(f'{P}/{pid}/builds', json={'sources': sha1s, 'from': {'kind': 'version', 'version': 1}}), 404,
        'version_not_found')
    err(api.post(f'{P}/{pid}/builds', json={'sources': sha1s, 'from': {'kind': 'build', 'build': '20261104T101500-0a1b2c'}}),
        404, 'build_not_found')
    err(api.post(f'{P}/nope-x/builds', json={'sources': sha1s}), 404, 'project_not_found')
    fake.missing_list = ['the builder\'s Python is not there']
    e = err(api.post(f'{P}/{pid}/builds', json={'sources': sha1s}), 503, 'builder_missing')
    assert e['details']['missing'] == fake.missing_list
    assert len(fake.started) == 0


def test_start_again_with_other_files_copies_the_settings(api: TestClient, fake: FakeJobRunner) -> None:
    b = ready(api)
    s = copy.deepcopy(b['settings'])
    s['floors'][0]['wallHeight'] = 3.33
    b = save_settings(api, b, s).json()
    pid = b['projectId']
    r = api.post(f'{P}/{pid}/builds', json={'sources': None, 'from': {'kind': 'build', 'build': b['id']}})
    assert r.status_code == 201, r.text[:300]
    n = r.json()
    assert n['layersReviewedAt'] is not None and n['settingsRevision'] == 1
    assert n['settings']['floors'][0]['wallHeight'] == 3.33 and [x['sha1'] for x in n['settings']['sources']] == [SHA1, SHA2]
