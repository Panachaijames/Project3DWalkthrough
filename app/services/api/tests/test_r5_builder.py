"""The rooms milestone with the real worker (docs/rooms/ACCEPTANCE.md 2.2 "Which rules a draft gets" and "Integration";
RA-1's four cases of DESIGN R-1.3 as one test; RA-12 point 4; step R5), marker `builder`. The API's LocalJobRunner starts
`walkthrough_builder.job` in the builder's Python through test_u5_builder.py's `real` fixture: a fresh store under
WT_TMP, the cache under WT_TMP; skipped when the builder Python or LibreDWG is missing, failing instead under
WT_INTEGRATION=1. They run against whatever builder is in the tree; the house's and the bank's stair asserts need R1's
and R2's rules (landed on 11 Nov: the tracer built no stair on the real drawings).

The house (RA-1) takes three builds of the drawing (old, new, old again) and four prepares; the bank one new-rule build;
the reference building one.

Until R1 - R3 landed they ran only under WT_INTEGRATION=1 (as test_u5_builder.py did in the upload milestone): the
builder's out/** was being written in parallel (R3). Without the flag they were DESELECTED (conftest.py, marker
`rooms_worker`), so a plain run skipped nothing. R1 - R3 have landed: the integration step RI turned
RUN_WITHOUT_THE_FLAG on (contract-issues/R5.md D-1, RI.md), so they run in every `npm run test:api` and fail, not skip,
under WT_INTEGRATION=1 when the worker is missing."""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from kit import APP, FIXTURES, PROTOTYPES, RUN
from test_u5_builder import described, real, wait  # noqa: F401 (real: the fixture)
from upkit import FX, load, upload, upload_bank
from walkthrough_api.models_upload import NEW_RULES, OLD_RULES

pytestmark = [pytest.mark.builder, pytest.mark.rooms_worker]

#: Was False until R1 - R3 had landed (the tests ran only under WT_INTEGRATION=1, deselected otherwise, conftest.py).
#: Turned on by the integration step RI (docs/rooms/contract-issues/R5.md D-1).
RUN_WITHOUT_THE_FLAG = True

P = '/api/projects'
SAVE = {'label': 'rooms milestone', 'carryHeights': True, 'rememberMapping': False}
RULE_KEYS = tuple(NEW_RULES)
HOUSE = PROTOTYPES / 'Test Sukhumvit Residence.dwg'
#: The house as saved on 9 Nov (the upload acceptance store's house-upload v1): its recipe and its model's stamp.
HOUSE_RECIPE = FX / 'settings' / 'recipes' / 'house.json'
HOUSE_OLD_STAMP = '1c07bfeef580'
#: RA-3 / RA-1: a point of the house's living room, on the ground plan's sheet (m), which the old rule leaves unfloored.
LIVING_ROOM = (26.2, 11.1)
#: RA-12 point 4: the bank's new-rule model must equal the reference RI pins in services/builder/tests/
#: test_r_rooms_golden.py (RA-15). Pinned by RI (11 Nov, provisional with the references; contract-issues/R5.md D-2):
#: the bank built through this API and the real worker with the defaults (= bank-rooms.json), stamp 54ef1ac240bb, the
#: same as R7's build of 11 Nov through the API on 8747. A move during the review is explained in contract-issues/RR.md.
#: 16 Nov 2026: 77468e44.. -> a36e1535.. with the north stair's floored strip (test_r_rooms_golden.py's PINS note).
BANK_NEW_RULE_SHA1: str | None = 'a36e15351068532b33409240275d0d57a1d799fc'


def rules(settings: dict) -> dict:
    return {k: settings['options'][k] for k in RULE_KEYS}


def put(api: TestClient, b: dict, settings: dict) -> dict:
    r = api.put(f'{b["url"]}/settings', json={'settings': settings, 'layersReviewed': True},
                headers={'If-Match': f'"{b["settingsRevision"]}"'})
    assert r.status_code == 200, r.text[:600]
    return r.json()


def prepared(api: TestClient, project_id: str, body: dict) -> dict:
    r = api.post(f'{P}/{project_id}/builds', json=body)
    assert r.status_code == 201, r.text[:600]
    b = wait(api, r.json()['url'])
    assert b['run']['status'] == 'done' and b['settingsRevision'] == 1, described(b)
    return b


def built(api: TestClient, b: dict) -> tuple[dict, bytes]:
    r = api.post(f'{b["url"]}/run', json={})
    assert r.status_code == 202, r.text[:600]
    b = wait(api, b['url'])
    assert b['run']['status'] == 'done' and b['result'] is not None, described(b)
    model = api.get(f'{b["url"]}/model').content
    assert hashlib.sha1(model).hexdigest()[:12] == b['result']['stamp']
    return b, model


def inside(pt: tuple[float, float], ring: list) -> bool:
    x, y, hit = pt[0], pt[1], False
    for (x0, y0), (x1, y1) in zip(ring, ring[1:] + ring[:1], strict=True):
        if (y0 > y) != (y1 > y) and x < x0 + (y - y0) * (x1 - x0) / (y1 - y0):
            hit = not hit
    return hit


def on_the_plate(model: dict, floor: str, sheet_pt: tuple[float, float]) -> bool:
    """Is the sheet point (the floor's own sheet, m) on one of the floor's slab parts (outside their holes)?"""
    f = next(f for f in model['floors'] if f['key'] == floor)
    shift = f.get('sheetShift') or [0.0, 0.0]
    ox, oy = model['offset']
    pt = (sheet_pt[0] - ox - shift[0], sheet_pt[1] - oy - shift[1])         # sheet = model + offset + sheetShift
    return any(inside(pt, p['o']) and not any(inside(pt, h) for h in p['h'])
               for p in model['parts'] if p['floor'] == floor and p['kind'] == 'slab')


def tree_sha1(folder: Path) -> dict[str, str]:
    return {p.relative_to(folder).as_posix(): hashlib.sha1(p.read_bytes()).hexdigest()
            for p in sorted(folder.rglob('*')) if p.is_file()}


# =============================================================================================== RA-1: which rules
def test_which_rules_a_draft_gets(real: TestClient) -> None:  # noqa: F811
    """ACCEPTANCE RA-1, the four cases of DESIGN R-1.3 with the real worker, on the house as saved on 9 Nov."""
    api = real
    pid = 'house-rules'
    assert api.post(P, json={'name': 'Test Sukhumvit Residence', 'shortName': 'Sukhumvit house', 'id': pid}
                    ).status_code == 201
    recipe_raw = HOUSE_RECIPE.read_bytes()
    recipe = json.loads(recipe_raw)
    assert not any(k in recipe['options'] for k in RULE_KEYS)                # a recipe of before the milestone
    sha1 = upload(api, pid, HOUSE.read_bytes(), HOUSE.name)['sha1']
    assert sha1 == recipe['sources'][0]['sha1']

    # 1. a new project's adopted settings carry the new values
    b = prepared(api, pid, {'sources': [sha1]})
    assert rules(b['settings']) == NEW_RULES

    # version 1 = the house as saved on 9 Nov: its recipe put through the API (no keys: the old rules), the old stamp
    b = put(api, b, recipe)
    assert rules(b['settings']) == OLD_RULES
    b, model = built(api, b)
    assert b['result']['stamp'] == HOUSE_OLD_STAMP and 'stairways' not in json.loads(model)
    r = api.post(f'{b["url"]}/save', json=SAVE)
    assert r.status_code == 201, r.text[:600]
    v1 = RUN / 'real-data' / 'projects' / pid / 'versions' / '1'
    assert load(v1 / 'version.json')['modelFormat'] == 'built-model/1'
    (v1 / 'project-data.json').write_bytes(recipe_raw)                      # the file exactly as saved on 9 Nov
    v1_files = tree_sha1(v1)

    # 2. a new version from that recipe gets the new values and builds a v2 model, without opening the Floors step
    d = prepared(api, pid, {'sources': None})
    assert rules(d['settings']) == NEW_RULES and d['layersReviewedAt'] is not None
    layers = d['settings']['layers']                      # the recipe's roles kept; a layer it does not name gets the
    assert {k: layers[k] for k in recipe['layers']} == recipe['layers']     # proposal's role (U-3.3): here 'other'
    assert all(role == 'other' for k, role in layers.items() if k not in recipe['layers'])
    assert [(f['key'], f['level'], f['wallHeight']) for f in d['settings']['floors']] == \
        [(f['key'], f['level'], f['wallHeight']) for f in recipe['floors']]
    d, model_raw = built(api, d)                                            # no settings saved before the build
    model = json.loads(model_raw)
    assert 'stairways' in model, 'a new-rule model has the stairways key (the v2 mark)'
    assert on_the_plate(model, 'ground', LIVING_ROOM), 'the living room (26.2, 11.1) has its floor'
    main = [s for s in model['stairways'] if (s['from'], s['to']) == ('ground', 'upper')]
    assert main, f'no stairway from ground to upper: {model["stairways"]}'
    assert main[0]['risers'] == 21 and any(p.get('stair') == main[0]['id'] for p in model['parts'])   # RA-9

    # 3. the same draft switched to the earlier way (one saved change of the three options) builds the old stamp
    s = d['settings']
    s['options'].update(OLD_RULES)
    d = put(api, d, s)
    assert rules(d['settings']) == OLD_RULES
    d, model_raw = built(api, d)
    assert d['result']['stamp'] == HOUSE_OLD_STAMP
    r = api.post(f'{d["url"]}/save', json=SAVE)
    assert r.status_code == 201, r.text[:600]
    v2 = RUN / 'real-data' / 'projects' / pid / 'versions' / '2'
    assert load(v2 / 'version.json')['modelFormat'] == 'built-model/1' and rules(load(v2 / 'project-data.json')) == \
        OLD_RULES
    assert tree_sha1(v1) == v1_files                                        # saved versions never change

    # 4. a recipe that carries the keys is kept as it is: old (v2's, written out at the save) and new (a mix nobody
    #    proposes, given to v1's recipe by hand)
    e = prepared(api, pid, {'sources': None})
    assert rules(e['settings']) == OLD_RULES
    mixed = {'slabs': 'network', 'ceilings': 'off', 'stairs': 'climb'}
    (v1 / 'project-data.json').write_bytes(json.dumps({**recipe, 'options': {**recipe['options'], **mixed}}).encode())
    f = prepared(api, pid, {'sources': None, 'from': {'kind': 'version', 'version': 1}})
    assert rules(f['settings']) == mixed


# =============================================================================================== RA-12 point 4
def test_the_bank_with_the_defaults(real: TestClient) -> None:  # noqa: F811
    """The bank from its two DWGs with the rules a new draft gets: its settings are then exactly
    fixtures/upload/settings/bank-rooms.json, and the saved version is built-model/2 with the main stair."""
    api = real
    pid = 'bank-rooms'
    assert api.post(P, json={'name': 'Bangkok Bank, Sampeng Branch', 'shortName': 'Bank branch', 'id': pid}
                    ).status_code == 201
    b = prepared(api, pid, {'sources': upload_bank(api, pid)})
    assert rules(b['settings']) == NEW_RULES                                 # the defaults
    s = load(FX / 'settings' / 'bank.json')                                 # the A-1 settings, the draft's options
    s['options'] = {**s['options'], **{k: b['settings']['options'][k] for k in RULE_KEYS}}
    assert s == load(FX / 'settings' / 'bank-rooms.json')
    b = put(api, b, s)
    b, model_raw = built(api, b)
    model = json.loads(model_raw)
    assert 'stairways' in model and any((x['from'], x['to']) == ('L1', 'L2') for x in model['stairways'])
    if BANK_NEW_RULE_SHA1 is not None:
        assert hashlib.sha1(model_raw).hexdigest() == BANK_NEW_RULE_SHA1
    r = api.post(f'{b["url"]}/save', json=SAVE)
    assert r.status_code == 201, r.text[:600]
    v = r.json()
    assert v['stamp'] == hashlib.sha1(model_raw).hexdigest()[:12] and v['counts']['rooms'] == len(model['rooms'])
    vdir = RUN / 'real-data' / 'projects' / pid / 'versions' / '1'
    assert load(vdir / 'version.json')['modelFormat'] == 'built-model/2'
    assert (vdir / 'model.json').read_bytes() == model_raw
    assert rules(load(vdir / 'project-data.json')) == NEW_RULES
    script = api.get(f'{P}/{pid}/versions/1/downloads/max-script').content
    assert f'(model data {v["stamp"]})'.encode() in script.split(b'\n')[1]


# =============================================================================================== 2.2 "Integration"
def test_the_reference_building_with_the_new_rules(real: TestClient, tmp_path: Path) -> None:  # noqa: F811
    """The reference building (ACCEPTANCE 2.5) from its two DXFs with its settings (the new rules): every output passes
    the API's checks, the model is v2 with its L stair, its rooms and ceilings, and the overlay carries the new fields."""
    api = real
    subprocess.run(['node', 'tools/run-builder-py.mjs', 'tools/rooms/make-reference-building.py', 'dxf',
                    str(tmp_path)], cwd=APP, check=True, capture_output=True, timeout=300)
    settings = load(FIXTURES / 'rooms' / 'settings.reference.json')
    pid = 'rooms-reference'
    assert api.post(P, json={'name': 'Reference building', 'shortName': 'Reference', 'id': pid}).status_code == 201
    sha1s = [upload(api, pid, (tmp_path / src['name']).read_bytes(), src['name'])['sha1'] for src in settings['sources']]
    assert sha1s == [src['sha1'] for src in settings['sources']]           # the DXFs are deterministic
    b = prepared(api, pid, {'sources': sha1s})
    assert rules(b['settings']) == NEW_RULES
    b = put(api, b, settings)
    b, model_raw = built(api, b)
    model = json.loads(model_raw)
    want = load(FIXTURES / 'models' / 'rooms-reference.model.json')
    s1 = next(x for x in model['stairways'] if x['id'] == 'S1')
    w1 = want['stairways'][0]
    assert (s1['from'], s1['to'], s1['kind'], s1['risers']) == (w1['from'], w1['to'], w1['kind'], w1['risers'])
    assert sum(p['kind'] == 'tread' for p in model['parts']) == w1['treads']
    assert sorted(x['id'] for x in model['spaces']) == sorted(x['id'] for x in want['spaces'])
    assert any(p['kind'] == 'ceiling' for p in model['parts'])
    r = api.post(f'{b["url"]}/save', json=SAVE)
    assert r.status_code == 201, r.text[:600]
    vdir = RUN / 'real-data' / 'projects' / pid / 'versions' / '1'
    assert load(vdir / 'version.json')['modelFormat'] == 'built-model/2'
    # the overlay carries the new floor fields (R3's out/overlay.py; R0's placeholder writes none of them)
    overlay = api.get(f'{b["url"]}/overlay').json()
    ground = next(f for f in overlay['floors'] if f['key'] == 'ground')
    assert all(k in ground for k in ('spaces', 'holes', 'stairs', 'closings', 'unfloored')), \
        f'the overlay has no rooms fields: {sorted(ground)}'
    assert ground['spaces'] and ground['stairs'] and ground['closings'] and ground['unfloored']
    assert {'slab-gap', 'doorway', 'room-names'} <= {f['kind'] for f in overlay['flags']}
