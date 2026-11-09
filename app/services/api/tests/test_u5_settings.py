"""settings_issues() (docs/upload/DESIGN.md U-13.2) and the settings body limits (U-13.5; ACCEPTANCE 2.2 "Bodies and
paths"): a 6 MB settings PUT is taken, 9 MB is refused with 413 before the body is read, 20,001 set-asides get 422."""
from __future__ import annotations

import copy
import json
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from kit import make_client
from test_u5_builds import err, ready, save_settings
from upkit import FX, FakeJobRunner, SHA1, bank_settings
from walkthrough_api import check_file
from walkthrough_api.models_upload import BuildSettings
from walkthrough_api.settings_check import settings_issues

MIB = 1024 * 1024


def issues(s: dict, adopted: bool = True) -> dict[str, str]:
    return {i['path']: i['message'] for i in settings_issues(BuildSettings.model_validate(s), adopted=adopted)}


@pytest.mark.parametrize('name', ['bank', 'house', 'suite', 'tower', 'small'])
def test_the_fixtures_pass(name: str) -> None:
    assert issues(json.loads((FX / 'settings' / f'{name}.json').read_bytes())) == {}


def test_each_rule() -> None:
    s = bank_settings()
    s['office'] = 'Not An Id'
    s['project'].update(photoName='with space', maxPrefix='B', maxFileName='plan.max', name=' ')
    s['sources'].append(dict(s['sources'][0]))                                  # twice
    s['sources'][1]['units'] = None
    s['floors'][0]['key'] = 'L 1'
    s['floors'][1]['key'] = s['floors'][0]['key']
    s['floors'][1]['level'] = 0.0                                               # not above floor 0
    s['floors'][1]['source'] = 'f' * 40
    s['floors'][0]['area'] = {'kind': 'box', 'bbox': [10.0, 0.0, 5.0, 5.0], 'pad': -1.0, 'match': 'all'}
    s['floors'][0]['wallHeight'] = 0.01
    s['floors'][0]['windowSill'] = 2.5
    s['floors'][0]['windowHead'] = 2.0
    s['defaults']['railingHeight'] = 51.0
    s['furniture']['heights'] = {'table': 5}
    s['vocabulary'] = {'stairUp': '(unclosed'}
    s['fixes']['setAside'] = [{'floor': 'L1', 'source': SHA1, 'key': '', 'sig': 'XYZ', 'rsig': '12', 'elementId': None,
                               'layer': 'A-WALL', 'note': 'n' * 501}]
    s['fixes']['openings'] = [{'floor': 'L1', 'a': [0, 0], 'b': [1, 0], 'kind': 'door', 'head': 1.0, 'sill': 1.5}]
    found = issues(s)
    for path in ('/office', '/project/name', '/project/photoName', '/project/maxPrefix', '/project/maxFileName',
                 '/sources/2/sha1', '/sources/1/units', '/floors/0/key', '/floors/1/level', '/floors/1/source',
                 '/floors/0/area/bbox', '/floors/0/area/pad', '/floors/0/wallHeight', '/floors/0/windowSill',
                 '/defaults/railingHeight', '/furniture/heights/table', '/vocabulary/stairUp',
                 '/fixes/setAside/0/key', '/fixes/setAside/0/sig', '/fixes/setAside/0/rsig',
                 '/fixes/setAside/0/note', '/fixes/openings/0/sill'):
        assert path in found, (path, found)
    assert 'twice' in found['/sources/2/sha1']
    assert issues(s, adopted=False).get('/sources/1/units') is None                # revision 0: units may be null


def test_counts_and_numbers() -> None:
    s = bank_settings()
    s['layers'] = {f'L{i}': 'other' for i in range(5001)}
    assert '/layers' in issues(s)
    s = bank_settings()
    ref = {'floor': 'L1', 'source': SHA1, 'key': 'BA', 'sig': 'a' * 12, 'rsig': '', 'elementId': None, 'layer': 'x',
           'note': ''}
    s['fixes']['setAside'] = [ref] * 20_001
    assert '/fixes/setAside' in issues(s)
    s['fixes']['setAside'] = [ref] * 20_000
    assert issues(s) == {}
    s = bank_settings()
    s['fixes']['openings'] = [{'floor': 'L1', 'a': [0, 0], 'b': [1, 0], 'kind': None, 'head': None, 'sill': None}] * 5001
    assert '/fixes' in issues(s)
    s = bank_settings()
    s['floors'][0]['level'] = float('nan')
    s['options']['offset'] = [float('inf'), 0.0]
    found = issues(s)
    assert '/floors/0/level' in found and '/options/offset/0' in found


def test_check_file_runs_them(tmp_path: Path) -> None:
    s = bank_settings()
    s['floors'][1]['level'] = -3.0
    found = check_file.issues('settings', json.dumps(s).encode())
    assert found == ['/floors/1/level: floors are listed lowest first: each level must be above the one before']


@pytest.fixture
def api(data_copy: Path, template_file: Path) -> Iterator[TestClient]:
    with make_client(data_copy, template_file, jobs=FakeJobRunner()) as c:
        yield c


def big_settings(b: dict, n: int) -> dict:
    s = copy.deepcopy(b['settings'])
    s['fixes']['setAside'] = [{'floor': 'L1', 'source': SHA1, 'key': f'BA/{i:X}/2C4/1F3', 'sig': f'{i:012x}',
                               'rsig': f'{i * 7:012x}', 'elementId': '2371857', 'layer': 'I-FURN',
                               'note': 'set aside on the check screen: a chair drawn twice' + ' ' * 120}
                              for i in range(n)]
    return s


def test_a_6_mb_settings_put_is_taken_and_9_mb_refused(api: TestClient) -> None:
    b = ready(api)
    s = big_settings(b, 20_000)
    body = json.dumps({'settings': s, 'layersReviewed': True}).encode()
    assert 5.5 * MIB < len(body) < 8 * MIB, len(body)
    r = api.put(f'{b["url"]}/settings', content=body, headers={'content-type': 'application/json', 'If-Match': '"2"'})
    assert r.status_code == 200, r.text[:300]
    assert len(r.json()['settings']['fixes']['setAside']) == 20_000
    lean = api.get(b['url'], params={'withSettings': 'false'}).json()
    assert lean['settingsRevision'] == 3 and lean['settings'] is None
    nine = json.dumps({'settings': s, 'layersReviewed': True, 'pad': ' ' * (3 * MIB)}).encode()
    assert len(nine) > 9 * MIB - 1
    err(api.put(f'{b["url"]}/settings', content=nine, headers={'content-type': 'application/json'}), 413,
        'body_too_large')
    e = err(save_settings(api, r.json(), big_settings(b, 20_001)), 422, 'invalid_settings')
    assert e['details']['issues'][0]['path'] == '/fixes/setAside'
    assert api.get(b['url'], params={'withSettings': 'false'}).json()['settingsRevision'] == 3
