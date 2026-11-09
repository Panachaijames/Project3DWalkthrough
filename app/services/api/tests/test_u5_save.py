"""saveBuild (docs/upload/DESIGN.md U-11.1), the office memory (U-8.4) and a new version of a seeded project (U-3.3,
U-9.6), through the API with the FakeJobRunner (ACCEPTANCE 2.2 "Save")."""
from __future__ import annotations

import copy
import json
import threading
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from kit import FIXTURES, PROTOTYPES, make_client
from test_u5_builds import bank_for, err, new_project, ready, save_settings, start
from upkit import SHA1, SHA2, FakeJobRunner, load
from walkthrough_api.jsonio import sha1_hex

P = '/api/projects'
SAVE = {'label': '4 Nov 2026: built from the two bank drawings', 'carryHeights': True, 'rememberMapping': True}


@pytest.fixture
def fake() -> FakeJobRunner:
    return FakeJobRunner()


@pytest.fixture
def api(data_copy: Path, template_file: Path, fake: FakeJobRunner) -> Iterator[TestClient]:
    with make_client(data_copy, template_file, jobs=fake) as c:
        yield c


def built(api: TestClient, project_id: str = '', **kw) -> dict:
    b = ready(api, project_id, **kw)
    r = api.post(f'{b["url"]}/run', json={})
    assert r.status_code == 202 and r.json()['result'] is not None, r.text[:300]
    return r.json()


def test_save_makes_the_version(api: TestClient, data_copy: Path) -> None:
    pid = new_project(api, newOfficeName='DWP Revit')
    b = built(api, pid)
    r = api.post(f'{b["url"]}/save', json=SAVE)
    assert r.status_code == 201, r.text[:400]
    v = r.json()
    assert (v['version'], v['label'], v['stamp'], v['stampSource'], v['sourceKind']) == \
           (1, SAVE['label'], 'c3a9408304a2', 'model.json', 'cad')
    assert v['modelSha1'] == 'c3a9408304a240b83c36f5c5c53db56b50a72c64' and v['hasStages'] and v['hasMaxScript']
    assert v['downloads']['maxScript']['fileName'] == 'Bank_re_upload_v1.ms'
    vdir = data_copy / 'projects' / pid / 'versions' / '1'
    assert (vdir / 'model.json').read_bytes() == (FIXTURES / 'models' / 'bank-v2.model.json').read_bytes()
    assert (vdir / 'downloads' / 'Bank_re_upload.ms').read_bytes() == \
        (PROTOTYPES / 'bank_test' / 'Bangkok_Bank_Sampeng.ms').read_bytes()
    assert sorted(p.name for p in (vdir / 'source').iterdir()) == sorted([
        'inputs.json', f'conversion-{SHA1[:12]}.json', f'conversion-{SHA2[:12]}.json', 'build-report.json',
        'openings.json', 'pieces.json', 'flags.json'])
    assert load(vdir / 'source' / 'flags.json')['format'] == 'build-flags/1'
    record = load(vdir / 'version.json')
    assert 'seed' not in record and record['sourceFiles'] == ['I1201 - LEVEL 1 GENERAL ARRANGEMENT.dwg',
                                                              'I1202 - LEVEL 2 GENERAL ARRANGEMENT.dwg']
    project_data = load(vdir / 'project-data.json')
    assert project_data == api.get(b['url']).json()['settings']
    ps = load(data_copy / 'projects' / pid / 'project-settings.json')
    assert ps['office'] == 'dwp-revit' and ps['offset'] == [1.212, 0.348]
    assert ps['naming'] == {'photoName': 'Bank-branch', 'maxPrefix': 'BRU', 'maxFileName': 'Bank_re_upload.ms'}
    d = api.get(b['url']).json()
    assert d['status'] == 'saved' and d['savedVersion'] == 1
    project = api.get(f'{P}/{pid}').json()
    assert project['latestVersion'] == 1 and project['stamp'] == 'c3a9408304a2'
    # a saved build is read-only
    e = err(api.post(f'{b["url"]}/save', json=SAVE), 409, 'build_saved')
    assert e['details'] == {'version': 1}
    err(api.post(f'{b["url"]}/run', json={}), 409, 'build_saved')
    err(save_settings(api, d, d['settings']), 409, 'build_saved')
    err(api.delete(b['url']), 409, 'build_saved')
    # the CSV of the saved version is the bank's (no heights)
    csv = api.get(f'{P}/{pid}/versions/1/downloads/furniture-csv')
    assert csv.content == (FIXTURES / 'csv' / 'bank-v2.csv').read_bytes()


def test_the_office_memory(api: TestClient, data_copy: Path) -> None:
    pid = new_project(api, newOfficeName='DWP Revit')
    b = built(api, pid)
    assert api.post(f'{b["url"]}/save', json=SAVE).status_code == 201
    mapping = load(data_copy / 'mappings' / 'dwp-revit.json')
    layers = mapping['layers']
    assert layers['A-WALL']['role'] == 'wall' and layers['A-WALL']['names'] == ['A-WALL']
    assert layers['A-WALL']['uses'] == 1 and layers['A-WALL']['lastProject'] == pid and layers['A-WALL']['was'] is None
    assert layers['S-COLS']['role'] == 'column' and layers['A-GENM']['role'] == 'furniture'
    roles = load(data_copy / 'projects' / pid / 'versions' / '1' / 'project-data.json')['layers']
    for name, entry in layers.items():
        assert entry['role'] == roles.get(name, 'other')
    offices = api.get('/api/offices').json()['offices']
    assert [(o['id'], o['name'], o['layers']) for o in offices] == [('dwp-revit', 'DWP Revit', len(layers))]
    # a second build of the office with A-FLOR changed by hand: the latest wins, the old role kept
    b2 = ready(api, pid)
    s = copy.deepcopy(b2['settings'])
    was = layers.get('A-FLOR', {}).get('role')
    s['layers']['A-FLOR'] = 'ignore'
    s['layers']['A-WALL'] = 'column'
    b2 = save_settings(api, b2, s).json()
    b2 = api.post(f'{b2["url"]}/run', json={}).json()
    assert api.post(f'{b2["url"]}/save', json={**SAVE, 'label': 'second'}).status_code == 201
    layers = load(data_copy / 'mappings' / 'dwp-revit.json')['layers']
    assert layers['A-WALL']['role'] == 'column' and layers['A-WALL']['was'] == 'wall' and layers['A-WALL']['uses'] == 2
    assert layers['A-FLOR']['role'] == 'ignore' and layers['A-FLOR']['was'] == was


def test_no_memory_without_an_office_or_when_not_asked(api: TestClient, data_copy: Path) -> None:
    pid = new_project(api)
    b = built(api, pid)
    assert api.post(f'{b["url"]}/save', json={**SAVE, 'rememberMapping': True}).status_code == 201
    assert not (data_copy / 'mappings').exists()
    pid2 = new_project(api, 'Second bank', newOfficeName='Other office')
    b = built(api, pid2)
    assert api.post(f'{b["url"]}/save', json={**SAVE, 'rememberMapping': False}).status_code == 201
    assert load(data_copy / 'mappings' / 'other-office.json')['layers'] == {}


def test_a_new_version_of_a_seeded_project(api: TestClient, fake: FakeJobRunner, data_copy: Path) -> None:
    """bank-sampeng has no project-settings.json and no project-data.json: its proposal takes v2's naming, floor keys and
    offset (U-3.3, ACCEPTANCE A-8), and v3 carries v2's saved heights."""
    assert api.put(f'{P}/bank-sampeng/versions/2/furniture-heights', json={'heights': {'table': 600}}).status_code == 200
    proposal = load(Path(__file__).resolve().parents[3] / 'fixtures' / 'upload' / 'runs' / 'bank-prepare' / 'out' /
                    'proposed-settings.json')
    def rekey(raw: bytes) -> bytes:
        p = json.loads(raw)
        for i, f in enumerate(p['floors']):
            f['key'], f['name'] = f'a{i + 1}', 'Area'
        return json.dumps(p).encode()
    fake.mutate['proposed-settings.json'] = rekey
    b = start(api, 'bank-sampeng')
    s = b['settings']
    assert b['settingsRevision'] == 1 and proposal['project']['photoName'] == 'BangkokBank-Sampeng'
    assert (s['project']['photoName'], s['project']['maxPrefix'], s['project']['maxFileName']) == \
           ('BangkokBank-Sampeng', 'BB', 'Bangkok_Bank_Sampeng.ms')
    assert s['project']['name'] == 'Bangkok Bank, Sampeng Branch' and s['office'] is None
    assert [(f['key'], f['name']) for f in s['floors']] == [('L1', 'Level 1'), ('L2', 'Level 2')]
    assert s['options']['offset'] == [1.212, 0.348]
    b = save_settings(api, b, bank_for(b) | {'options': {**bank_for(b)['options'], 'offset': [1.212, 0.348]}}).json()
    b = api.post(f'{b["url"]}/run', json={}).json()
    r = api.post(f'{b["url"]}/save', json=SAVE)
    assert r.status_code == 201, r.text[:400]
    v = r.json()
    assert v['version'] == 3 and v['downloads']['maxScript']['fileName'] == 'Bangkok_Bank_Sampeng_v3.ms'
    assert v['overrides']['heights'] == {'table': 600}
    ps = load(data_copy / 'projects' / 'bank-sampeng' / 'project-settings.json')
    assert ps['offset'] == [1.212, 0.348] and ps['office'] is None
    # the next build starts from v3's recipe (reviewed)
    sha1s = [SHA1, SHA2]
    n = api.post(f'{P}/bank-sampeng/builds', json={'sources': sha1s}).json()
    assert n['layersReviewedAt'] is not None and n['settings']['layers'] == b['settings']['layers']
    assert load(data_copy / 'projects' / 'bank-sampeng' / 'builds' / n['id'] / 'build.json')['from'] == \
        {'kind': 'version', 'version': 3}


def test_save_refusals(api: TestClient, fake: FakeJobRunner, data_copy: Path) -> None:
    b = ready(api)
    err(api.post(f'{b["url"]}/save', json=SAVE), 409, 'not_built')
    b = api.post(f'{b["url"]}/run', json={}).json()
    err(api.post(f'{b["url"]}/save', json={**SAVE, 'label': ' '}), 422, 'bad_label')
    err(api.post(f'{b["url"]}/save', json={**SAVE, 'label': 'x' * 201}), 422, 'bad_label')
    stale = save_settings(api, b, b['settings']).json()
    err(api.post(f'{b["url"]}/save', json=SAVE), 409, 'stale')
    b = api.post(f'{stale["url"]}/run', json={}).json()
    out = data_copy / 'projects' / b['projectId'] / 'builds' / b['id'] / 'runs' / b['result']['runId'] / 'out'
    (out / 'stages.json').write_bytes(b'{}')                                # changed after it was validated
    e = err(api.post(f'{b["url"]}/save', json=SAVE), 422, 'invalid_output')
    assert any('stages.json' in i for i in e['details']['issues'])
    d = api.get(b['url']).json()
    assert d['run']['status'] == 'failed' and d['run']['error']['code'] == 'invalid_output'
    assert api.get(f'{P}/{b["projectId"]}').json()['versionCount'] == 0


def test_two_saves_at_once_make_one_version(api: TestClient) -> None:
    b = built(api)
    answers: list = []

    def save() -> None:
        answers.append(api.post(f'{b["url"]}/save', json=SAVE))
    threads = [threading.Thread(target=save) for _ in range(3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    codes = sorted(r.status_code for r in answers)
    assert codes == [201, 409, 409], [r.text[:200] for r in answers]
    assert all(r.json()['error'] == {'code': 'build_saved', 'message': r.json()['error']['message'],
                                     'details': {'version': 1}} for r in answers if r.status_code == 409)
    assert api.get(f'{P}/{b["projectId"]}').json()['versionCount'] == 1


def test_save_carries_heights_only_when_asked(api: TestClient) -> None:
    pid = new_project(api)
    b = built(api, pid)
    assert api.post(f'{b["url"]}/save', json=SAVE).status_code == 201
    assert api.put(f'{P}/{pid}/versions/1/furniture-heights', json={'heights': {'seat': 300}}).status_code == 200
    b2 = api.post(f'{P}/{pid}/builds', json={'sources': None}).json()     # from the latest version's recipe and files
    assert b2['settingsRevision'] == 1 and b2['layersReviewedAt']
    b2 = api.post(f'{b2["url"]}/run', json={}).json()
    v2 = api.post(f'{b2["url"]}/save', json={**SAVE, 'carryHeights': False}).json()
    assert v2['version'] == 2 and v2['overrides']['heights'] == {}
    b3 = api.post(f'{P}/{pid}/builds', json={'sources': None, 'from': {'kind': 'version', 'version': 1}}).json()
    b3 = api.post(f'{b3["url"]}/run', json={}).json()
    assert api.put(f'{P}/{pid}/versions/2/furniture-heights', json={'heights': {'seat': 310}}).status_code == 200
    v3 = api.post(f'{b3["url"]}/save', json=SAVE).json()
    assert v3['version'] == 3 and v3['overrides']['heights'] == {'seat': 310}
    assert sha1_hex(api.get(f'{P}/{pid}/versions/3/model').content) == 'c3a9408304a240b83c36f5c5c53db56b50a72c64'
