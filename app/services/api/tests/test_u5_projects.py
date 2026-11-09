"""createProject and listOffices (docs/upload/DESIGN.md U-13.3, U-8.4, U-4.1; ACCEPTANCE 2.2): ids (given, derived, at most
40 characters for a new project, cut at a hyphen, reserved, taken -> 409 with the next free id), names refused, the naming
derived into project-settings.json, offices made and listed, and the path-length check."""
from __future__ import annotations

import shutil
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from kit import RUN, make_client, read_json
from upkit import FakeJobRunner
from walkthrough_api.drafts import naming
from walkthrough_api.store.base import PathTooLong
from walkthrough_api.store.local import LocalStore

P = '/api/projects'


@pytest.fixture
def shallow(template_file: Path) -> Iterator[TestClient]:
    """A client over an empty store at app/data's depth (50 characters), so a 40-character id fits (U-4.1)."""
    data = Path(str(RUN / 'sh').ljust(50, 'x'))
    if data.exists():
        shutil.rmtree(data)
    with make_client(data, template_file, jobs=FakeJobRunner()) as c:
        yield c


def err(r, status: int, code: str) -> dict:
    assert r.status_code == status, (r.status_code, r.text[:400])
    assert r.json()['error']['code'] == code, r.json()
    return r.json()['error']


def test_create_a_project(client: TestClient, data_copy: Path) -> None:
    r = client.post(P, json={'name': 'Siam Hotel, Lobby & Café', 'shortName': 'Siam lobby', 'projectNo': '26-0300'})
    assert r.status_code == 201, r.text[:300]
    d = r.json()
    assert d['id'] == 'siam-hotel-lobby-cafe' and d['latestVersion'] == 0 and d['versions'] == []
    assert (d['name'], d['shortName'], d['projectNo'], d['sourceKind']) == ('Siam Hotel, Lobby & Café', 'Siam lobby',
                                                                            '26-0300', 'cad')
    meta = read_json(data_copy / 'projects' / 'siam-hotel-lobby-cafe' / 'meta.json')
    assert meta['latestVersion'] == 0 and meta['versions'] == [] and meta['sourceKind'] == 'cad'
    ps = read_json(data_copy / 'projects' / 'siam-hotel-lobby-cafe' / 'project-settings.json')
    assert ps == {'format': 'walkthrough-project-settings/1', 'office': None,
                  'naming': {'photoName': 'Siam-lobby', 'maxPrefix': 'SHLC', 'maxFileName': 'Siam_Hotel_Lobby_Cafe.ms'},
                  'offset': None, 'updatedAt': ps['updatedAt']}
    assert client.get(f'{P}/siam-hotel-lobby-cafe').status_code == 200
    ids = [p['id'] for p in client.get(P).json()['projects']]
    assert 'siam-hotel-lobby-cafe' in ids and len(ids) == 5


def test_ids(shallow: TestClient) -> None:
    client = shallow
    long_name = 'The Grand Riverside Residence Tower Phase Two Podium And Retail'
    r = client.post(P, json={'name': long_name})
    assert r.status_code == 201
    assert r.json()['id'] == 'the-grand-riverside-residence-tower' and len(r.json()['id']) <= 40     # cut at a hyphen
    r = client.post(P, json={'name': 'โครงการทดสอบ'})                              # a Thai name: no ASCII
    assert r.status_code == 201 and r.json()['id'].startswith('project-') and len(r.json()['id']) == 14
    assert r.json()['name'] == 'โครงการทดสอบ'
    r = client.post(P, json={'name': 'x', 'id': 'a' * 40})
    assert r.status_code == 201 and r.json()['id'] == 'a' * 40
    err(client.post(P, json={'name': 'x', 'id': 'b' * 41}), 422, 'bad_project')              # 41 characters
    for bad in ('A-big', '-lead', 'x', 'with space', 'new\n'):
        err(client.post(P, json={'name': 'x', 'id': bad}), 422, 'bad_project')


def test_taken_and_reserved_ids(shallow: TestClient) -> None:
    client = shallow
    for reserved in ('new', 'bank-sampeng', 'hotel-lobby'):
        e = err(client.post(P, json={'name': 'x', 'id': reserved}), 409, 'project_exists')
        assert e['details']['suggested'] == f'{reserved}-2'
    e = err(client.post(P, json={'name': 'Bank Sampeng'}), 409, 'project_exists')         # derived, reserved
    assert e['details']['suggested'] == 'bank-sampeng-2'
    assert client.post(P, json={'name': 'Office tower'}).status_code == 201
    assert client.post(P, json={'name': 'x', 'id': 'office-tower-2'}).status_code == 201
    e = err(client.post(P, json={'name': 'Office tower'}), 409, 'project_exists')
    assert e['details']['suggested'] == 'office-tower-3'
    assert client.post(P, json={'name': 'x', 'id': 'c' * 40}).status_code == 201
    e = err(client.post(P, json={'name': 'x', 'id': 'c' * 40}), 409, 'project_exists')
    assert e['details']['suggested'] == 'c' * 38 + '-2'


def test_names_refused(client: TestClient) -> None:
    for body in ({'name': ''}, {'name': '   '}, {'name': 'x' * 201}, {'name': 'bad\x07name'},
                 {'name': 'ok', 'shortName': 'y' * 101}, {'name': 'ok', 'projectNo': 'z' * 65},
                 {'name': 'ok', 'office': 'no-such-office'}):
        err(client.post(P, json=body), 422, 'bad_project')
    assert client.post(P, json={}).status_code == 422                                         # FastAPI's own


def test_offices(client: TestClient, data_copy: Path) -> None:
    assert client.get('/api/offices').json() == {'offices': []}
    r = client.post(P, json={'name': 'Tower', 'newOfficeName': 'DWP Revit'})
    assert r.status_code == 201
    m = read_json(data_copy / 'mappings' / 'dwp-revit.json')
    assert (m['format'], m['id'], m['name'], m['layers'], m['furnitureWords']) == \
           ('office-mapping/1', 'dwp-revit', 'DWP Revit', {}, {})
    assert read_json(data_copy / 'projects' / 'tower' / 'project-settings.json')['office'] == 'dwp-revit'
    r = client.post(P, json={'name': 'Tower two', 'office': 'dwp-revit'})
    assert r.status_code == 201
    assert read_json(data_copy / 'projects' / 'tower-two' / 'project-settings.json')['office'] == 'dwp-revit'
    r = client.post(P, json={'name': 'Tower three', 'newOfficeName': 'DWP revit'})          # the same slug: reused
    assert r.status_code == 201 and read_json(data_copy / 'mappings' / 'dwp-revit.json')['name'] == 'DWP Revit'
    client.post(P, json={'name': 'Villa', 'newOfficeName': 'Atelier Zed'})
    offices = client.get('/api/offices').json()['offices']
    assert [(o['id'], o['name'], o['layers']) for o in offices] == [('atelier-zed', 'Atelier Zed', 0),
                                                                    ('dwp-revit', 'DWP Revit', 0)]
    (data_copy / 'mappings' / 'broken.json').write_bytes(b'{"format":')
    assert [o['id'] for o in client.get('/api/offices').json()['offices']] == ['atelier-zed', 'dwp-revit']


def test_naming_rules() -> None:
    assert naming.slug('Hôtel  Ëxample -- 2026!') == 'hotel-example-2026'
    assert naming.photo_name('Bank branch') == 'Bank-branch' and naming.photo_name('สาขา') == 'Project'
    assert naming.max_prefix('Bangkok Bank') == 'BB' and naming.max_prefix('Villa') == 'VX'
    assert naming.max_prefix('A B C D E') == 'ABCD' and naming.max_prefix('26 Tower') == 'TX'
    assert naming.max_prefix('ทดสอบ') == 'XX'
    assert naming.max_file_name('Bangkok Bank, Sampeng Branch') == 'Bangkok_Bank_Sampeng_Branch.ms'
    assert naming.max_file_name('ทดสอบ') == 'Project.ms'
    assert len(naming.max_file_name('word ' * 40)) <= 63
    assert naming.office_id('E2E Revit') == 'e2e-revit' and naming.office_id('ก').startswith('office-')
    assert naming.next_free('x' * 40, lambda _i: False) == 'x' * 38 + '-2'


def test_the_path_length_check(tmp_path: Path, template_file: Path) -> None:
    """U-4.1: a store so deep that a prepare's deepest path would pass 259 characters refuses with a plain message."""
    store = LocalStore(Path('C:/') / ('d' * 150) / 'data')
    with pytest.raises(PathTooLong, match='too deep for Windows'):
        store.check_path(store.deepest_run_path('a' * 40))
    deep = tmp_path / ('d' * max(1, 215 - len(str(tmp_path))))
    with make_client(deep, template_file, jobs=FakeJobRunner()) as c:
        e = err(c.post(P, json={'name': 'Deep project'}), 500, 'path_too_long')
        assert e['message'].startswith('the project folder is too deep for Windows')
    assert not (deep / 'projects' / 'deep-project').exists()
