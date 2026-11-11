"""RI: the new-rule references of the rooms milestone (docs/rooms/ACCEPTANCE.md RA-15; WORK_BREAKDOWN RI item 4).

The five drawings built with the new rule (fixtures/upload/settings/<name>-rooms.json; conftest.py's session builds,
rooms_kit.rooms_build) and written by U4's write_outputs with the build's moment fixed at 9 Nov 2026 12:00 UTC
(test_r_old_rule.write_fixed, no version model to diff against). Pinned here:
  * every model's sha1, and the sha1s of its stages.json, top view, Max script (fixed date) and furniture CSV;
  * per floor the summary rows: rooms (spaces), named rooms, plate0 (report `slab.plate`), the holes cut (count and m2)
    and the stairs you can climb that leave the floor.
The bank's model is the one the API and the real worker save from the bank's DWGs with the defaults
(services/api/tests/test_r5_builder.py BANK_NEW_RULE_SHA1, RA-12 point 4): the same bytes.

PROVISIONAL (11 Nov 2026, RI): pinned when the acceptance runs passed. The new suite's reference rests on the door
finder's output on a drawing it never saw (DESIGN R-13): it is expected to move with the door finder's round. Every move
during the review is explained in docs/rooms/contract-issues/RR.md.

Marked `acceptance` (deselected unless WT_ACCEPTANCE=1): each build again in two CHILD processes with different
PYTHONHASHSEED values gives the same model.json, CSV, stages.json, top view and Max script (fixed date), and those are
the pinned bytes (DESIGN R-13). Recording: WT_RECORD_ROOMS_GOLDEN=1 writes the figures of the current builder to
<WT_TMP>/rooms-golden.json (to be copied into PINS by hand; the test is not a recorder of its own pins).
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

import kit
from test_r_old_rule import write_fixed
from test_u3_helpers import csv_bytes, model_bytes, sha1
from walkthrough_builder import oslock

NAMES = ('bank', 'house', 'suite', 'tower', 'suite-revit')
FILES = ('model.json', 'stages.json', 'topview.png', 'maxscript', 'furniture.csv')
BANK_NEW_RULE_SHA1 = '54ef1ac240bbfa1421b0b49026ec26c16e3d1eed'     # = services/api/tests/test_r5_builder.py's

#: PROVISIONAL (RI, 11 Nov 2026): name -> {files: sha1 per FILES, floors: {key: summary row}}. Recorded with
#: WT_RECORD_ROOMS_GOLDEN=1 from the builder of the branch at 0209ab3 plus RI-A's changes; each model equals the one the
#: API and the real worker saved from the DWGs in the acceptance run (%TEMP%/wt-ri/acc, `rooms-builds`).
PINS: dict = {
    'bank': {
        'files': {
            'model.json': '54ef1ac240bbfa1421b0b49026ec26c16e3d1eed',
            'stages.json': '40c12469a7f27866bf71e566a5163eed05be93e9',
            'topview.png': 'fe813a4b4074a037689eb2762e02544703177d97',
            'maxscript': '934a1d26df35486f62f028102b567795c089505f',
            'furniture.csv': '66f53fb2636e7f465a91c0708de22bc45a9fe6c6',
        },
        'floors': {
            'L1': {'rooms': 15, 'named': 9, 'plate': 235.8, 'holes': 1, 'holesArea': 3.17, 'climb': 1},
            'L2': {'rooms': 14, 'named': 9, 'plate': 295.7, 'holes': 3, 'holesArea': 12.54, 'climb': 0},
        },
    },
    'house': {
        'files': {
            'model.json': 'c7824bca60086c43d010eebc5c1f3aaa654fdcf5',
            'stages.json': 'd0108e3c80db088fa433beaec21dc97e400c67d8',
            'topview.png': '9fb483f70903364e6e4a2038f3dbf2c925473559',
            'maxscript': '10148e2364460d7b95403c62217adcc89772d614',
            'furniture.csv': '5ebe79e4c341c9a4f3b53b4c55fe1867259e44f8',
        },
        'floors': {
            'ground': {'rooms': 22, 'named': 0, 'plate': 507.7, 'holes': 0, 'holesArea': 0, 'climb': 1},
            'upper': {'rooms': 24, 'named': 0, 'plate': 450.9, 'holes': 4, 'holesArea': 51.06, 'climb': 0},
        },
    },
    'suite': {
        'files': {
            'model.json': 'ed7774c64b9b3567df9a4dbdcb8b257f84064d69',
            'stages.json': '96d5858cbaf875a652070e866d1534881e31c8ce',
            'topview.png': '7224ebbc77f7237b7ffb1bafb78b0fc363f4e977',
            'maxscript': '03d548b3f68f425b9048210219aa14dacf135a26',
            'furniture.csv': 'f39f5f709f50a8dabb4cb4a70570322a17f9716c',
        },
        'floors': {
            'suite': {'rooms': 18, 'named': 14, 'plate': 471.1, 'holes': 0, 'holesArea': 0, 'climb': 0},
        },
    },
    'tower': {
        'files': {
            'model.json': '3d25cdf722fb699a1aaa83203205834c445620ca',
            'stages.json': 'f52a370f7228755478806b2927cccb434a609d6c',
            'topview.png': 'd7d95040ca1c05030178e18dfcca5e42078cb623',
            'maxscript': 'cd5e439dfc7ca943e851f579b0f27b99935ef52a',
            'furniture.csv': '8949ec63bd853622d29c453dd83ae2455a8b372b',
        },
        'floors': {
            'L29': {'rooms': 32, 'named': 0, 'plate': 848.7, 'holes': 4, 'holesArea': 11.99, 'climb': 1},
            'L30': {'rooms': 34, 'named': 0, 'plate': 739.8, 'holes': 6, 'holesArea': 39.91, 'climb': 0},
        },
    },
    'suite-revit': {
        'files': {
            'model.json': '424cc8cabd45318bb38b20f0ab1b509d69c3beb1',
            'stages.json': 'a809b35a62e49d729c98d3800da793ce8e1140a7',
            'topview.png': '93a76b7b1facc5de08c4758abf274ac347f13eeb',
            'maxscript': '719e517a2dc815ed3137b675867a018a56369114',
            'furniture.csv': '9777992757804676c020446f1828720c7e7e5cca',
        },
        'floors': {
            'L1': {'rooms': 17, 'named': 6, 'plate': 274.2, 'holes': 0, 'holesArea': 0, 'climb': 0},
        },
    },
}


def outputs(b: dict, tmp: Path) -> dict[str, str]:
    """The pinned outputs of one new-rule build (U4's writer, the moment fixed) -> {file: sha1}."""
    s = b['settings']
    written = write_fixed(b['res'], s, b['sources'], tmp, b['project'], None)
    data = written[s['project']['maxFileName']].read_bytes()
    assert b'9 Nov 2026' in data, 'the Max script carries the fixed date'
    return {'model.json': sha1(written['model.json'].read_bytes()), 'stages.json': sha1(written['stages.json'].read_bytes()),
            'topview.png': sha1(written['topview.png'].read_bytes()), 'maxscript': sha1(data),
            'furniture.csv': sha1(csv_bytes(b['res']['model']))}


def summary(res: dict) -> dict[str, dict]:
    """Per floor: rooms (spaces), named rooms, plate0 (m2), holes cut (count, m2), stairs you can climb that leave it."""
    out = {}
    for key, fl in res['report']['floors'].items():
        cut = [h for h in fl['slab']['holes'] if h.get('cut')]
        out[key] = {'rooms': fl['rooms']['spaces'], 'named': fl['rooms']['named'], 'plate': fl['slab']['plate'],
                    'holes': len(cut), 'holesArea': round(sum(h['area'] for h in cut), 2),
                    'climb': sum(1 for r in fl['stairways'] if r['state'] == 'climb')}
    return out


@pytest.fixture(scope='module')
def golden(bank_rooms, house_rooms, suite_rooms, tower_rooms, suite_revit_rooms, tmp_path_factory) -> dict[str, dict]:
    """The five builds' pinned outputs and rows, written once (the machine run lock held while they are written)."""
    builds = {'bank': bank_rooms, 'house': house_rooms, 'suite': suite_rooms, 'tower': tower_rooms,
              'suite-revit': suite_revit_rooms}
    tmp = tmp_path_factory.mktemp('rooms-golden')
    with oslock.hold():
        return {name: {'files': outputs(b, tmp / name), 'floors': summary(b['res']),
                       'model': b['res']['model']} for name, b in builds.items()}


if os.environ.get('WT_RECORD_ROOMS_GOLDEN') == '1':        # defined only then, so that a plain run has no skipped test
    def test_record_the_figures(golden) -> None:
        doc = {name: {'files': g['files'], 'floors': g['floors']} for name, g in golden.items()}
        (kit.RUN / 'rooms-golden.json').write_text(json.dumps(doc, indent=1), encoding='utf-8')


def test_the_pins_name_the_five_builds() -> None:
    assert tuple(PINS) == NAMES
    for name, p in PINS.items():
        assert tuple(p['files']) == FILES and all(len(v) == 40 for v in p['files'].values()), name
    assert PINS['bank']['files']['model.json'] == BANK_NEW_RULE_SHA1


@pytest.mark.parametrize('name', NAMES)
def test_the_new_rule_outputs_are_the_pinned_ones(name: str, golden) -> None:
    got = golden[name]
    moved = {k: (got['files'][k], PINS[name]['files'][k]) for k in FILES if got['files'][k] != PINS[name]['files'][k]}
    assert moved == {}, f'{name}: these new-rule outputs moved from the provisional references: {sorted(moved)}'


@pytest.mark.parametrize('name', NAMES)
def test_the_summary_rows_per_floor(name: str, golden) -> None:
    assert golden[name]['floors'] == PINS[name]['floors']


def test_every_new_rule_model_has_stairways(golden) -> None:
    """RA-15: every new-rule model has `stairways` (a list, empty when no stair climbs): a BuiltModel v2."""
    for name, g in golden.items():
        assert isinstance(g['model'].get('stairways'), list), name
    assert {n for n, g in golden.items() if g['model']['stairways']} == {'bank', 'house', 'tower'}


CHILD = r'''
import json, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import rooms_kit
import test_r_rooms_golden as G
from walkthrough_builder import oslock
import kit
name, tmp = sys.argv[2], Path(sys.argv[3])
with oslock.hold():
    b = rooms_kit.rooms_build(name, kit.REF, tmp)
    files = G.outputs(b, tmp / 'written')
print(json.dumps({'files': files, 'floors': G.summary(b['res'])}))
'''


def child_build(name: str, tmp: Path, hashseed: int) -> dict:
    tmp.mkdir(parents=True, exist_ok=True)
    p = kit.python_child(CHILD, str(Path(__file__).resolve().parent), name, str(tmp), hashseed=hashseed, cwd=kit.APP)
    out, err = p.communicate(timeout=3600)
    assert p.returncode == 0, f'the child build of {name} failed:\n{out[-2000:]}\n{err[-4000:]}'
    return json.loads(out.strip().splitlines()[-1])


@pytest.mark.acceptance
@pytest.mark.parametrize('name', NAMES)
def test_built_in_two_processes_the_same_bytes(name: str, ref, ref_r0, tmp_path) -> None:
    """RA-15: two child processes with different PYTHONHASHSEED values (each takes the machine run lock itself; this test
    holds none) give the same model, CSV, stages, top view and Max script, and they are the pinned ones."""
    one = child_build(name, tmp_path / 'one', 1)
    two = child_build(name, tmp_path / 'two', 4242)
    assert one['files'] == two['files'], f'{name}: two processes gave different bytes'
    assert one['floors'] == two['floors']
    assert one['files'] == PINS[name]['files'] and one['floors'] == PINS[name]['floors']
