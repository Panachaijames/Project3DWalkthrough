"""The rooms milestone through the API, with the FakeJobRunner (docs/rooms/ACCEPTANCE.md 2.2; DESIGN R-1.2, R-1.3, R-6.3,
R-12.2 - R-12.5; step R5): which rules a new draft gets, old settings coming back with the old values, the new fields'
ranges, the illegal combinations, the fix limits, the rescale of the new fixes, create_version's modelFormat, and the v2
checks (the presentation's new names, the overlay's new fields, the broken-model corpus). RA-1's four cases with the real
worker are in test_r5_builder.py."""
from __future__ import annotations

import copy
import json
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from kit import FIXTURES, make_client, read_json
from test_u5_builds import bank_for, err, new_project, ready, save_settings, start
from upkit import ROOMS_RUNS, SHA1, SHA2, FakeJobRunner, bank_settings, load
from walkthrough_api import builtmodel, check_file, checks
from walkthrough_api.drafts.adopt import RULE_KEYS, carries_rules
from walkthrough_api.jsonio import dumps_pretty, sha1_hex
from walkthrough_api.models_upload import NEW_RULES, OLD_RULES, BuildSettings
from walkthrough_api.settings_check import settings_issues
from walkthrough_api.store.base import NewProject, VersionDraft
from walkthrough_api.store.local import LocalStore

P = '/api/projects'
SAVE = {'label': 'rooms milestone', 'carryHeights': True, 'rememberMapping': False}
MIXED = {'slabs': 'network', 'ceilings': 'off', 'stairs': 'climb'}           # a legal mix nobody proposes


@pytest.fixture
def fake() -> FakeJobRunner:
    return FakeJobRunner()


@pytest.fixture
def api(data_copy: Path, template_file: Path, fake: FakeJobRunner) -> Iterator[TestClient]:
    with make_client(data_copy, template_file, jobs=fake) as c:
        yield c


def rules(settings: dict) -> dict:
    return {k: settings['options'][k] for k in RULE_KEYS}


def before_the_milestone(s: dict) -> dict:
    """A settings document as written before the rooms milestone: none of its keys."""
    s = copy.deepcopy(s)
    for k in RULE_KEYS:
        s['options'].pop(k, None)
    for f in s['floors']:
        f.pop('ceilingHeight', None)
    for k in ('closings', 'rooms', 'stairs'):
        s['fixes'].pop(k, None)
    for x in s['fixes']['setAside']:
        x.pop('floorPast', None)
    return s


def saved_v1(api: TestClient, data_copy: Path) -> tuple[str, Path]:
    """A new project with version 1 saved from the bank's settings: (project id, v1's project-data.json)."""
    pid = new_project(api)
    b = ready(api, pid)
    b = api.post(f'{b["url"]}/run', json={}).json()
    r = api.post(f'{b["url"]}/save', json=SAVE)
    assert r.status_code == 201, r.text[:400]
    return pid, data_copy / 'projects' / pid / 'versions' / '1' / 'project-data.json'


def prepare_spec(fake: FakeJobRunner) -> dict:
    """The settings the newest prepare was started with (revision 0)."""
    run = next(p for p in reversed(fake.started) if p.name.endswith('-prepare'))
    return load(run / 'spec.json')['settings']


# =============================================================================================== which rules (R-1.3)
def test_a_new_project_gets_the_new_rules(api: TestClient, fake: FakeJobRunner) -> None:
    proposal = load(FIXTURES / 'upload' / 'runs' / 'bank-prepare' / 'out' / 'proposed-settings.json')
    assert not carries_rules(proposal)                     # the fake worker proposes no rule: the API writes them
    b = start(api, new_project(api))
    assert b['settingsRevision'] == 1 and rules(b['settings']) == NEW_RULES
    assert rules(prepare_spec(fake)) == NEW_RULES          # revision 0 had them too (the proposal's base)


def test_a_seeded_project_with_no_recipe_gets_the_new_rules(api: TestClient, data_copy: Path) -> None:
    b = start(api, 'bank-sampeng')
    assert rules(b['settings']) == NEW_RULES
    assert load(data_copy / 'projects' / 'bank-sampeng' / 'builds' / b['id'] / 'build.json')['from'] == {'kind': 'none'}


@pytest.mark.parametrize('how', [{'sources': None}, {'sources': None, 'from': {'kind': 'version', 'version': 1}}],
                         ids=['latest', 'version-1'])
def test_a_recipe_saved_before_the_milestone_gets_the_new_rules(api: TestClient, fake: FakeJobRunner,
                                                                 data_copy: Path, how: dict) -> None:
    pid, recipe_file = saved_v1(api, data_copy)
    assert rules(load(recipe_file)) == OLD_RULES          # the bank's settings, put without the keys: the old rules
    recipe = before_the_milestone(load(recipe_file))
    recipe_file.write_bytes(dumps_pretty(recipe))         # as a version saved on 9 Nov has it
    v1 = {p.relative_to(recipe_file.parent).as_posix(): p.read_bytes() for p in recipe_file.parent.rglob('*')
          if p.is_file()}
    r = api.post(f'{P}/{pid}/builds', json=how)
    assert r.status_code == 201, r.text[:400]
    b = r.json()
    assert rules(prepare_spec(fake)) == NEW_RULES          # chosen at revision 0 ...
    assert b['settingsRevision'] == 1 and rules(b['settings']) == NEW_RULES          # ... and kept by the adoption
    assert b['layersReviewedAt'] is not None              # a draft from a version skips the Floors step (builds.py)
    s = b['settings']
    assert s['layers'] == recipe['layers'] and [f['key'] for f in s['floors']] == [f['key'] for f in recipe['floors']]
    kept = (*RULE_KEYS, 'offset')                         # the offset: pinned to v1's model (U-9.6)
    assert {k: v for k, v in s['options'].items() if k not in kept} == \
        {k: v for k, v in recipe['options'].items() if k not in kept}
    assert s['options']['offset'] == [1.212, 0.348]
    assert load(data_copy / 'projects' / pid / 'builds' / b['id'] / 'build.json')['from'] == \
        {'kind': 'version', 'version': 1}
    # built and saved as v2; v1 is untouched (saved versions never change)
    b = api.post(f'{b["url"]}/run', json={}).json()
    assert rules(load(fake.started[-1] / 'spec.json')['settings']) == NEW_RULES
    assert api.post(f'{b["url"]}/save', json=SAVE).status_code == 201
    assert {p.relative_to(recipe_file.parent).as_posix(): p.read_bytes() for p in recipe_file.parent.rglob('*')
            if p.is_file()} == v1
    assert rules(load(recipe_file.parent.parent / '2' / 'project-data.json')) == NEW_RULES      # written out


@pytest.mark.parametrize('options', [OLD_RULES, NEW_RULES, MIXED, {'slabs': 'network'}],
                         ids=['old', 'new', 'mixed', 'one-key'])
def test_a_recipe_that_carries_the_keys_is_kept(api: TestClient, data_copy: Path, options: dict) -> None:
    pid, recipe_file = saved_v1(api, data_copy)
    recipe = before_the_milestone(load(recipe_file))
    recipe['options'].update(options)
    recipe_file.write_bytes(dumps_pretty(recipe))
    b = api.post(f'{P}/{pid}/builds', json={'sources': None}).json()
    assert rules(b['settings']) == {**OLD_RULES, **options}                 # a missing key is the old rule (R-1.2)


def test_a_draft_from_another_build(api: TestClient, data_copy: Path) -> None:
    b = ready(api)                                        # the bank's settings put: written out with the old rules
    pid = b['projectId']
    settings_file = data_copy / 'projects' / pid / 'builds' / b['id'] / 'settings.json'
    assert rules(load(settings_file)['settings']) == OLD_RULES
    c = api.post(f'{P}/{pid}/builds', json={'sources': None, 'from': {'kind': 'build', 'build': b['id']}}).json()
    assert rules(c['settings']) == OLD_RULES                                # its keys: kept
    # an open draft from before the milestone: its settings.json has none of the keys
    stored = load(settings_file)
    stored['settings'] = before_the_milestone(stored['settings'])
    settings_file.write_bytes(dumps_pretty(stored))
    assert rules(api.get(b['url']).json()['settings']) == OLD_RULES         # it reads as the earlier way (R-1.2) ...
    d = api.post(f'{P}/{pid}/builds', json={'sources': None, 'from': {'kind': 'build', 'build': b['id']}}).json()
    assert rules(d['settings']) == NEW_RULES                                # ... and a new draft from it is new


def test_the_earlier_way_is_one_settings_save(api: TestClient, fake: FakeJobRunner, data_copy: Path) -> None:
    b = start(api, new_project(api))
    assert rules(b['settings']) == NEW_RULES
    s = copy.deepcopy(b['settings'])
    s['options'].update(OLD_RULES)
    r = save_settings(api, b, s)
    assert r.status_code == 200, r.text[:400]
    b = r.json()
    assert rules(b['settings']) == OLD_RULES
    stored = load(data_copy / 'projects' / b['projectId'] / 'builds' / b['id'] / 'settings.json')
    assert rules(stored['settings']) == OLD_RULES and stored['revision'] == 2
    b = api.post(f'{b["url"]}/run', json={}).json()
    assert rules(load(fake.started[-1] / 'spec.json')['settings']) == OLD_RULES
    s['options'].update(NEW_RULES)                                          # and back
    assert rules(save_settings(api, b, s).json()['settings']) == NEW_RULES


# =============================================================================================== old settings (R-1.2)
def test_old_settings_come_back_with_the_old_values(api: TestClient, data_copy: Path) -> None:
    b = start(api, new_project(api))
    s = bank_for(b)                                       # the upload milestone's fixture: none of the new keys
    s['fixes']['setAside'] = [{'floor': 'L1', 'source': SHA1, 'key': '2C4', 'sig': '0123456789ab', 'rsig': '',
                               'elementId': None, 'layer': 'A-WALL', 'note': 'old'}]
    assert not carries_rules(s) and 'closings' not in s['fixes']
    r = save_settings(api, b, s)
    assert r.status_code == 200, r.text[:400]
    got = r.json()['settings']
    assert rules(got) == OLD_RULES
    assert [f['ceilingHeight'] for f in got['floors']] == [None, None]
    assert (got['fixes']['closings'], got['fixes']['rooms'], got['fixes']['stairs']) == ([], [], [])
    assert got['fixes']['setAside'][0]['floorPast'] is False
    # written out at the save (R-1.3: "writes it out at the next save")
    stored = load(data_copy / 'projects' / b['projectId'] / 'builds' / b['id'] / 'settings.json')['settings']
    assert stored == got and carries_rules(stored)
    # the saved versions' recipes of 9 Nov validate the same way
    for name in ('house', 'suite', 'tower', 'suite-revit'):
        raw = (FIXTURES / 'upload' / 'settings' / 'recipes' / f'{name}.json').read_bytes()
        assert not carries_rules(json.loads(raw)) and check_file.issues('settings', raw) == []
        assert rules(BuildSettings.model_validate_json(raw).model_dump(mode='json', by_alias=True)) == OLD_RULES


# =============================================================================================== settings_issues
def issues(s: dict) -> dict[str, str]:
    return {i['path']: i['message'] for i in settings_issues(BuildSettings.model_validate(s))}


@pytest.mark.parametrize('options,bad', [
    ({'slabs': 'closed-rooms', 'ceilings': 'auto', 'stairs': 'lines'}, ['/options/ceilings']),
    ({'slabs': 'closed-rooms', 'ceilings': 'off', 'stairs': 'climb'}, ['/options/stairs']),
    ({'slabs': 'closed-rooms', 'ceilings': 'auto', 'stairs': 'climb'}, ['/options/ceilings', '/options/stairs']),
    (OLD_RULES, []), (NEW_RULES, []), (MIXED, []), ({'slabs': 'network', 'ceilings': 'auto', 'stairs': 'lines'}, []),
    ({'slabs': 'network', 'ceilings': 'off', 'stairs': 'lines'}, []),
], ids=['ceilings', 'stairs', 'both', 'old', 'new', 'mixed', 'ceilings-only', 'plates-only'])
def test_the_combinations(options: dict, bad: list[str]) -> None:
    s = bank_settings()
    s['options'].update(options)
    found = issues(s)
    assert sorted(found) == bad
    for path in bad:
        assert found[path].startswith('ceilings and climbable stairs need floor plates from the wall network')


def test_an_illegal_combination_answers_422_with_a_plain_message(api: TestClient) -> None:
    b = start(api, new_project(api))
    s = copy.deepcopy(b['settings'])
    s['options'].update(slabs='closed-rooms')                                # the stairs and ceilings stay new
    e = err(save_settings(api, b, s), 422, 'invalid_settings')
    assert {i['path'] for i in e['details']['issues']} == {'/options/ceilings', '/options/stairs'}
    assert 'ceilings and climbable stairs need floor plates from the wall network' in e['message']


@pytest.mark.parametrize('value,ok', [(None, True), (0.5, True), (3.0, True), (20.0, True), (0.49, False),
                                      (20.01, False), (0.0, False), (-3.0, False)])
def test_ceiling_heights(value: float | None, ok: bool) -> None:
    s = bank_settings()
    s['floors'][1]['ceilingHeight'] = value
    found = issues(s)
    assert ('/floors/1/ceilingHeight' not in found) is ok, found
    if not ok:
        assert found['/floors/1/ceilingHeight'] == f'a ceiling height must be 0.5 - 20 m, not {value:g}'


def test_floor_past(api: TestClient) -> None:
    b = start(api, new_project(api))
    s = copy.deepcopy(b['settings'])
    aside = {'floor': 'L1', 'source': SHA1, 'key': '2C4', 'sig': '0123456789ab', 'rsig': '', 'elementId': None,
             'layer': 'A-WALL', 'note': 'a line across a doorway'}
    s['fixes']['setAside'] = [{**aside, 'floorPast': True}, aside]
    b = save_settings(api, b, s).json()
    assert [x['floorPast'] for x in b['settings']['fixes']['setAside']] == [True, False]
    s['fixes']['setAside'] = [{**aside, 'floorPast': 'sometimes'}]
    r = save_settings(api, b, s)
    assert r.status_code == 422 and any(d['loc'][-1] == 'floorPast' for d in r.json()['detail'])


def room(i: int = 0, name: str | None = 'Living', floor: str = 'L1') -> dict:
    return {'floor': floor, 'at': [float(i), 1.0], 'name': name, 'slab': 'auto', 'ceiling': 'auto'}


def test_the_fix_cap_counts_the_new_fixes() -> None:
    s = bank_settings()
    s['fixes']['openings'] = [{'floor': 'L1', 'a': [i, 0.0], 'b': [i, 1.0], 'kind': None, 'head': None, 'sill': None}
                              for i in range(2000)]
    s['fixes']['closings'] = [{'floor': 'L1', 'a': [i, 0.0], 'b': [i, 1.0], 'use': 'line'} for i in range(1500)]
    s['fixes']['rooms'] = [room(i) for i in range(1000)]
    s['fixes']['stairs'] = [{'floor': 'L1', 'at': [i, 0.0], 'bottom': None, 'use': 'auto'} for i in range(500)]
    assert '/fixes' not in issues(s)                                         # 5,000: taken
    s['fixes']['stairs'].append({'floor': 'L2', 'at': [0.0, 0.0], 'bottom': [1.0, 1.0], 'use': 'lines'})
    assert issues(s)['/fixes'] == ('5,001 opening, outline, closing, room and stair fixes; at most 5,000 are taken')


@pytest.mark.parametrize('name,message', [
    ('Living', None), (None, None), ('', None), ('   ', None), ('x' * 200, None), ('ห้องนั่งเล่น <img src=x>', None),
    ('x' * 201, 'a room name of 201 characters; at most 200 are taken'),
    ('Bar\nBOH', 'a room name is one line of plain text (no line breaks, tabs or control characters)'),
    ('Bar\tBOH', 'a room name is one line of plain text (no line breaks, tabs or control characters)'),
], ids=['plain', 'null', 'empty', 'blank', '200', 'text', '201', 'newline', 'tab'])
def test_room_names(name: str | None, message: str | None) -> None:
    s = bank_settings()
    s['fixes']['rooms'] = [room(0, 'Kitchen'), room(1, name)]
    assert issues(s).get('/fixes/rooms/1/name') == message


def test_the_fix_limits_through_the_api(api: TestClient) -> None:
    """ACCEPTANCE RA-13 "API checks": a room name over 200 characters and more than 5,000 other fixes answer 422."""
    b = start(api, new_project(api))
    s = copy.deepcopy(b['settings'])
    s['fixes']['rooms'] = [room(0, 'x' * 201)]
    e = err(save_settings(api, b, s), 422, 'invalid_settings')
    assert e['details']['issues'] == [{'path': '/fixes/rooms/0/name',
                                       'message': 'a room name of 201 characters; at most 200 are taken'}]
    s['fixes']['rooms'] = [room(i, None) for i in range(5001)]
    e = err(save_settings(api, b, s), 422, 'invalid_settings')
    assert [i['path'] for i in e['details']['issues']] == ['/fixes']
    s['fixes']['rooms'] = [room(0, 'Living'), room(1, None, 'L2')]
    s['fixes']['closings'] = [{'floor': 'L1', 'a': [1.0, 2.0], 'b': [3.0, 2.0], 'use': 'line'},
                              {'floor': 'L1', 'a': [5.0, 2.0], 'b': [6.0, 2.0], 'use': 'none'}]
    s['fixes']['stairs'] = [{'floor': 'L1', 'at': [4.0, 8.0], 'bottom': [4.0, 7.5], 'use': 'climb'}]
    r = save_settings(api, b, s)
    assert r.status_code == 200, r.text[:400]
    assert r.json()['settings']['fixes'] == s['fixes']


# =============================================================================================== rescale (R-6.3)
def test_a_units_change_rescales_the_new_fixes(api: TestClient, fake: FakeJobRunner) -> None:
    b = ready(api)
    s = copy.deepcopy(b['settings'])
    s['fixes']['closings'] = [{'floor': 'L2', 'a': [1.0, 2.0], 'b': [3.0, 4.0], 'use': 'line'},
                              {'floor': 'L1', 'a': [1.0, 2.0], 'b': [3.0, 4.0], 'use': 'none'}]
    s['fixes']['rooms'] = [{**room(0), 'floor': 'L2', 'at': [5.0, 6.0]}, {**room(0), 'at': [5.0, 6.0]}]
    s['fixes']['stairs'] = [{'floor': 'L2', 'at': [7.0, 8.0], 'bottom': [7.5, 8.5], 'use': 'auto'},
                            {'floor': 'L2', 'at': [1.0, 1.0], 'bottom': None, 'use': 'lines'},
                            {'floor': 'L1', 'at': [7.0, 8.0], 'bottom': [7.5, 8.5], 'use': 'climb'}]
    b = save_settings(api, b, s).json()
    s2 = copy.deepcopy(b['settings'])
    s2['sources'][1]['units'] = 'cm'                                        # mm -> cm: L2's sheet x 10
    r = save_settings(api, b, s2)
    assert r.status_code == 200, r.text[:300]
    fx = r.json()['settings']['fixes']
    assert [(c['a'], c['b']) for c in fx['closings']] == [([10.0, 20.0], [30.0, 40.0]), ([1.0, 2.0], [3.0, 4.0])]
    assert [x['at'] for x in fx['rooms']] == [[50.0, 60.0], [5.0, 6.0]]
    assert [(x['at'], x['bottom']) for x in fx['stairs']] == [([70.0, 80.0], [75.0, 85.0]), ([10.0, 10.0], None),
                                                             ([7.0, 8.0], [7.5, 8.5])]
    assert load(fake.started[-1] / 'spec.json')['only'] == [SHA2]


# =============================================================================================== create_version (R-12.2)
def draft_of(model: str, presentation: Path) -> VersionDraft:
    raw = (FIXTURES / 'models' / f'{model}.model.json').read_bytes()
    return VersionDraft(label='x', source_kind='cad', source_files=[], model_json=raw, stages_json=None,
                        presentation=read_json(presentation))


def test_create_version_writes_the_model_format(tmp_path: Path) -> None:
    store = LocalStore(tmp_path / 'data')
    store.create_project(NewProject(id='formats', name='x', short_name='x', source_kind='cad'))
    rows = [('bank-v2', FIXTURES / 'presentation' / 'bank-sampeng-v2.json', 'built-model/1'),
            ('rooms-reference', FIXTURES / 'presentation' / 'rooms-reference.json', 'built-model/2'),
            ('stairs-straight', FIXTURES / 'presentation' / 'rooms-reference.json', 'built-model/2')]
    for n, (model, pres, want) in enumerate(rows, start=1):
        v = store.create_version('formats', draft_of(model, pres))
        record = load(tmp_path / 'data' / 'projects' / 'formats' / 'versions' / str(n) / 'version.json')
        assert (v.version, v.model_format, record['modelFormat']) == (n, want, want), model
        m = read_json(FIXTURES / 'models' / f'{model}.model.json')
        assert record['counts']['rooms'] == len(m['rooms'])                # rooms[] still means drawn names
    # an empty `stairways` (a new-rule model where no stair climbs) is still the v2 mark
    m = read_json(FIXTURES / 'models' / 'rooms-reference.model.json')
    assert builtmodel.model_format({**m, 'stairways': []}) == 'built-model/2'
    assert builtmodel.model_format({k: v for k, v in m.items() if k != 'stairways'}) == 'built-model/1'


def test_the_seeded_versions_stay_built_model_1(seeded: Path) -> None:
    records = sorted(seeded.glob('projects/*/versions/*/version.json'))
    assert len(records) == 5
    for p in records:
        r, m = load(p), load(p.parent / 'model.json')
        assert r['modelFormat'] == 'built-model/1' and 'stairways' not in m
        assert r['counts'] == {'floors': len(m['floors']), 'parts': len(m['parts']), 'openings': len(m['openings']),
                               'furniture': len(m.get('furniture') or []),
                               'furnitureKinds': len(m.get('furnitureKinds') or []), 'rooms': len(m['rooms'])}


def test_a_v2_build_saves_as_built_model_2(data_copy: Path, template_file: Path) -> None:
    """The reference building's FakeJobRunner run folder (fixtures/rooms/runs/reference-build): the run passes the
    API's checks, the result counts it, Save writes version.json with 'built-model/2', and the version is served."""
    fake = FakeJobRunner(build_run=ROOMS_RUNS / 'reference-build')
    with make_client(data_copy, template_file, jobs=fake) as api:
        b = ready(api)
        b = api.post(f'{b["url"]}/run', json={}).json()
        assert b['run']['status'] == 'done' and b['result'] is not None, b['run']
        model_raw = (FIXTURES / 'models' / 'rooms-reference.model.json').read_bytes()
        m = json.loads(model_raw)
        res = b['result']
        assert res['stamp'] == '2da587ccc0bd' and res['counts']['rooms'] == len(m['rooms'])
        assert [(f['key'], f['rooms']) for f in res['floors']] == \
            [(f['key'], sum(1 for r in m['rooms'] if r['floor'] == f['key'])) for f in m['floors']]
        overlay = read_json(FIXTURES / 'rooms' / 'overlay.reference.json')
        assert res['flags']['total'] == len(overlay['flags'])                   # type: ignore[index]
        assert {'slab-gap', 'doorway', 'stair', 'room-names'} <= set(res['flags']['byKind'])
        r = api.post(f'{b["url"]}/save', json=SAVE)
        assert r.status_code == 201, r.text[:400]
        v = r.json()
        assert v['stamp'] == '2da587ccc0bd' and v['counts']['rooms'] == len(m['rooms'])
        vdir = data_copy / 'projects' / b['projectId'] / 'versions' / '1'
        assert load(vdir / 'version.json')['modelFormat'] == 'built-model/2'
        assert (vdir / 'model.json').read_bytes() == model_raw
        assert api.get(f'{P}/{b["projectId"]}/versions/1/model').content == model_raw
        assert api.get(f'{P}/{b["projectId"]}/versions/1/downloads/offline-html').status_code == 200


# =============================================================================================== v2 checks
def test_the_presentation_may_name_the_v2_toggle_and_part_kinds() -> None:
    m = read_json(FIXTURES / 'models' / 'rooms-reference.model.json')
    p = read_json(FIXTURES / 'presentation' / 'rooms-reference.json')
    p = {**p, 'labels': {'ceilings': 'Ceilings', 'plates': 'Floor plates'}, 'toggles': {'ceilings': True},
         'partStyles': {'tread': {'color': '#d8d2c4'}, 'landing': {'color': '#d8d2c4'}, 'ceiling': {'roughness': 0.95}}}
    assert checks.presentation_issues(p, m) == []                                # type: ignore[arg-type]
    bad = {**p, 'labels': {'roofs': 'Roofs'}, 'toggles': {'roofs': True}, 'partStyles': {'stair': {}}}
    assert {i.path for i in checks.presentation_issues(bad, m)} == {'/labels/roofs', '/toggles/roofs',  # type: ignore[arg-type]
                                                                    '/partStyles/stair'}


ROOMS_OVERLAYS = [FIXTURES / 'rooms' / 'overlay.reference.json', FIXTURES / 'upload' / 'overlay' / 'house-rooms.overlay.json']


@pytest.mark.parametrize('path', ROOMS_OVERLAYS, ids=lambda p: p.name)
def test_the_rooms_overlays_pass_check_file(path: Path) -> None:
    assert check_file.issues('overlay', path.read_bytes()) == []


def test_every_new_flag_kind_passes_check_file() -> None:
    flags = read_json(FIXTURES / 'rooms' / 'flags.every-kind.json')['flags']   # type: ignore[index]
    assert {f['kind'] for f in flags} == {'slab-gap', 'room-open', 'room-names', 'doorway', 'stair', 'stairs-none',
                                          'stair-clash', 'hole-skipped'}
    overlay = {'format': 'build-overlay/1', 'floors': [], 'flags': flags}
    assert check_file.issues('overlay', json.dumps(overlay).encode()) == []


def _broken(change) -> list[str]:
    o = read_json(FIXTURES / 'rooms' / 'overlay.reference.json')
    change(o)
    return check_file.issues('overlay', json.dumps(o).encode())


@pytest.mark.parametrize('change,path', [
    (lambda o: o['floors'][0].update(spaces=None), '/floors/0/spaces'),
    (lambda o: o['floors'][0]['spaces'][0].update(source='drawn'), '/floors/0/spaces/0/source'),
    (lambda o: o['floors'][0]['spaces'][0].pop('ceiling'), '/floors/0/spaces/0/ceiling'),
    (lambda o: o['floors'][0]['stairs'][0].update(state='flying'), '/floors/0/stairs/0/state'),
    (lambda o: o['floors'][0]['stairs'][0].update(risers=16.5), '/floors/0/stairs/0/risers'),
    (lambda o: o['floors'][0]['closings'][0].update(width=1.2), '/floors/0/closings/0/width'),
    (lambda o: o['floors'][0]['closings'][0].update(kind='wall'), '/floors/0/closings/0/kind'),
    (lambda o: o['floors'][0]['closings'][0].update(fix=None), '/floors/0/closings/0/fix'),
    (lambda o: o['floors'][0]['unfloored'][0].update(mouth=[[0, 0], [1, 0], [2, 0]]), '/floors/0/unfloored/0/mouth'),
    (lambda o: o['floors'][1]['holes'][0].pop('what'), '/floors/1/holes/0/what'),
    (lambda o: o['flags'][0]['ref'].update(space='ground-R001'), '/flags/0/ref/space'),
    (lambda o: o['flags'][0].update(kind='stair-gap'), '/flags/0/kind'),
], ids=['spaces-null', 'space-source', 'space-ceiling', 'stair-state', 'stair-risers', 'closing-extra',
        'closing-kind', 'closing-fix-null', 'mouth-3', 'hole-what', 'ref-extra', 'flag-kind'])
def test_check_file_refuses_broken_new_overlay_fields(change, path: str) -> None:
    found = _broken(change)
    assert any(i.startswith(path) for i in found), found


def test_the_v2_broken_cases_agree_with_the_viewer() -> None:
    """ACCEPTANCE 2.2 "Checks": each v2 case of the shared corpus (R0's, one per rule of R-12.1) is refused here at the
    path the viewer's parser reports, and the viewer throws on it too (none is a warning there)."""
    broken = FIXTURES / 'models' / 'broken'
    cases = {k: c for k, c in read_json(broken / 'expected.json')['cases'].items() if 'v2-' in k}  # type: ignore[index]
    assert len(cases) == 12
    for name, case in cases.items():
        assert case['viewer'] == 'throws', name
        assert case['path'] in [i.path for i in builtmodel.issues(read_json(broken / name))], name
    for name in ('rooms-reference', 'stairs-straight', 'stairs-L', 'stairs-U'):
        raw = (FIXTURES / 'models' / f'{name}.model.json').read_bytes()
        assert builtmodel.validate_bytes(raw)['stairways'] and check_file.issues('model', raw) == []


def test_the_rooms_settings_fixtures_pass() -> None:
    for name in ('bank', 'house', 'suite', 'tower', 'suite-revit'):
        raw = (FIXTURES / 'upload' / 'settings' / f'{name}-rooms.json').read_bytes()
        assert check_file.issues('settings', raw) == [], name
        assert rules(json.loads(raw)) == NEW_RULES
    raw = (FIXTURES / 'rooms' / 'settings.reference.json').read_bytes()
    assert check_file.issues('settings', raw) == [] and rules(json.loads(raw)) == NEW_RULES
    assert sha1_hex(raw) == 'a712632175fffb8ccb19da57d01f3c146e30c016'          # fixtures/README.md
