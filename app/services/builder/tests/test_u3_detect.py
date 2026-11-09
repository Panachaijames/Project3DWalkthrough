"""U3: the detector wrapper (docs/upload/DESIGN.md U-10.7, U-8.2; ACCEPTANCE A-4, 2.1 U3).

The derived detector roles of each acceptance settings fixture, on the reference caches, give records equal to
detector/output/<name>_openings.json with `floor` removed (bank1 24, bank2 25, sukhumvit 86, presidential 25, l29 31,
l30 34); the detector's stdout and stderr go to the log, never to the console; `frameRowsSkipped` is read from the
FRAME_ROWS_MAX warning's fixed wording and `slow` from fl.T, on synthetic floors.
"""
from __future__ import annotations

import json
import pickle

import pytest

import kit
from test_u3_helpers import settings, strip_floor
from walkthrough_builder.build import items as I
from walkthrough_builder.build.detect import detect

ORACLE = {'bank1': 24, 'bank2': 25, 'sukhumvit': 86, 'presidential': 25, 'l29': 31, 'l30': 34}
CASES = [('bank', 'bank1', 0), ('bank', 'bank2', 1), ('house', 'sukhumvit', 0), ('suite', 'presidential', 0),
         ('tower', 'l29', 0), ('tower', 'l30', 1)]


@pytest.mark.heavy
@pytest.mark.parametrize('fixture,name,src', CASES, ids=[c[1] for c in CASES])
def test_records_equal_the_frozen_outputs(ref, scratch, capfd, fixture, name, src):
    s = settings(fixture)
    sha = s['sources'][src]['sha1']
    fl = [f for f in s['floors'] if f['source'] == sha]
    D = pickle.loads((ref / 'proj' / 'detector' / name / 'prims.pkl').read_bytes())
    k = I.UNITS['mm']
    tag = I.tagger(fl, k)
    logs: list[str] = []
    mine = []
    for f in fl:
        raw = [d for d in D['items'] if tag(d) == f['key']]
        res = detect(f['key'], f['name'], raw, k, D['layers'], s['layers'], 'proj', scratch, logs.append)
        assert all(r['floor'] == f'proj:{f["key"]}' and r['id'].startswith(f'{f["key"]}-') for r in res['records'])
        assert res['slow'] is False and res['frameRowsSkipped'] is None
        mine += res['records']
    oracle = json.loads((kit.PROJECT / 'detector' / 'output' / f'{name}_openings.json').read_text(encoding='utf-8'))
    assert len(mine) == ORACLE[name]
    assert strip_floor(mine) == strip_floor(oracle['openings'])
    out = capfd.readouterr()
    assert out.out == '' and out.err == ''                        # captured into the run log, never the console


def _square(x, y, s, lay):
    return {'t': 'LWPOLYLINE', 'lay': lay, 'depth': 0, 'path': '', 'h': 'X', 'k': f'{lay}{x:.3f}{y:.3f}',
            'pts': [[x, y], [x + s, y], [x + s, y + s], [x, y + s]], 'closed': True, 'lt': 'BYLAYER'}


def test_frame_rows_skipped_and_slow_on_synthetic_floors(scratch, monkeypatch):
    """3,001 small tiles standing against a wall: the detector skips its frame-only sliding units and says so on
    stderr; the wrapper records how many (and the flag of U-12.2 comes from it). With SLOW_FLOOR at -1 s, `slow`."""
    wall = [{'t': 'HATCH', 'lay': 'A-WALL', 'depth': 0, 'path': '', 'h': 'W', 'k': 'W',
             'loops': [[[0.0, 0.0], [0.2, 0.0], [0.2, 200.0], [0.0, 200.0]]], 'solid': True, 'pattern': 'SOLID'}]
    tiles = [_square(0.25 + 0.06 * (i % 2), 0.1 + 0.066 * i, 0.05, 'TILES') for i in range(3001)]
    layers = {'A-WALL': 'wall', 'TILES': 'other'}
    logs: list[str] = []
    res = detect('F1', 'Floor 1', wall + tiles, 1.0, {'A-WALL': 'Continuous', 'TILES': 'Continuous'}, layers, 'p',
                 scratch, logs.append)
    assert res['frameRowsSkipped'] == 3001
    assert any('frame-only sliding units are not looked for' in m for m in logs)
    res = detect('F1', 'Floor 1', wall + tiles[:10], 1.0, {}, {**layers, 'TILES': 'ignore'}, 'p', scratch, logs.append)
    assert res['frameRowsSkipped'] is None and res['slow'] is False
    from walkthrough_builder.vendor.load import load
    op = load('openings', openings_data=scratch)
    monkeypatch.setattr(op, 'SLOW_FLOOR', -1.0)
    logs.clear()
    res = detect('F1', 'Floor 1', wall, 1.0, {}, layers, 'p', scratch, logs.append)
    assert res['slow'] is True and any('detection took' in m for m in logs)


def test_detector_failure_is_detect_failed(scratch):
    from walkthrough_builder.build import BuildError
    bad = [{'t': 'LINE', 'lay': 'A-WALL', 'depth': 0, 'path': '', 'h': 'L', 'pts': 'not points'}]
    with pytest.raises(BuildError) as e:
        detect('F1', 'Floor 1', bad, 1.0, {}, {'A-WALL': 'wall'}, 'p', scratch, print)
    assert e.value.code == 'detect_failed' and e.value.step == 'detect:F1' and 'Floor 1' in e.value.message
