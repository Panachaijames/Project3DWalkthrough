"""U3: floor alignment (docs/upload/DESIGN.md U-9.4; ACCEPTANCE A-5, 2.1 U3).

Per-gridline least squares with two direction families, the one-family case, two point pairs, auto's choice, the
0.5 mm "no shift" rule, and the house: its grid labels go to the floor whose area their line meets (the elevation
labels to neither), and its upper floor's shift is (-74.021 +- 0.002, 0 +- 0.002) with a spread under 2 mm.
"""
from __future__ import annotations

import json

import pytest

import kit
from walkthrough_builder.build import BuildError
from walkthrough_builder.build import align as AL

HOUSE = json.loads((kit.UPLOAD_FIXTURES / 'drawing' / 'sukhumvit.drawing.json').read_text(encoding='utf-8'))
HOUSE_SETTINGS = json.loads((kit.UPLOAD_FIXTURES / 'settings' / 'house.json').read_text(encoding='utf-8'))
BANK1 = json.loads((kit.UPLOAD_FIXTURES / 'drawing' / 'bank1.drawing.json').read_text(encoding='utf-8'))


def lab(text, a, b, x=None, y=None):
    g = {'text': text, 'line': [list(a), list(b)], 'layer': 'S-GRID-IDEN', 'block': None, 'direction': None}
    g['x'], g['y'] = (a if x is None else (x, y))
    return g


def grid(dx=0.0, dy=0.0, rot_noise=0.0):
    """Lines 1 - 3 vertical (x 0, 6, 12), A - C horizontal (y 0, 5, 10), bubbles at their lower / left ends."""
    out = [lab(t, (x + dx, -1 + dy), (x + dx + rot_noise, 11 + dy)) for t, x in (('1', 0), ('2', 6), ('3', 12))]
    out += [lab(t, (-1 + dx, y + dy), (13 + dx, y + dy)) for t, y in (('A', 0), ('B', 5), ('C', 10))]
    return out


def floors(*srcs, areas=None, methods=None):
    out = []
    for i, s in enumerate(srcs):
        out.append({'key': f'F{i}', 'name': f'Floor {i}', 'source': s,
                    'area': (areas or {}).get(i, {'kind': 'wholeFile'}), 'align': {'method': (methods or {}).get(i, 'auto')}})
    return out


def test_two_families_least_squares():
    rep = AL.align(floors('a', 'b'), {'a': grid(), 'b': grid(3.25, -1.5)})
    assert rep[0] == {'method': 'none', 'shift': [0.0, 0.0], 'spread': None, 'labels': [], 'families': 0}
    r = rep[1]
    assert r['method'] == 'grid' and r['families'] == 2 and r['labels'] == ['1', '2', '3', 'A', 'B', 'C']
    assert r['shift'] == pytest.approx([-3.25, 1.5]) and r['spread'] == pytest.approx(0.0, abs=1e-9)


def test_one_family_only_moves_along_its_normal():
    g0 = [g for g in grid() if g['text'] in '123']
    gi = [g for g in grid(2.0, 7.0) if g['text'] in '123']
    r = AL.align(floors('a', 'b'), {'a': g0, 'b': gi})[1]
    assert r['families'] == 1 and r['shift'] == pytest.approx([-2.0, 0.0])     # the other axis is not checked


def test_spread_is_the_largest_residual():
    gi = grid(1.0, 0.0)
    gi[1] = lab('2', (7.004, -1), (7.004, 11))                                   # one line 4 mm off
    r = AL.align(floors('a', 'b'), {'a': grid(), 'b': gi})[1]
    assert r['spread'] == pytest.approx(0.004 * 2 / 3, abs=1e-6)
    assert r['shift'][0] == pytest.approx(-1.004 / 3 - 2.0 / 3, abs=1e-6)


def test_a_shift_under_half_a_millimetre_is_none():
    r = AL.align(floors('a', 'b'), {'a': grid(), 'b': grid(0.0004, -0.0003)})[1]
    assert r['method'] == 'grid' and r['shift'] == [0.0, 0.0]


def test_points_and_origin_and_auto():
    f = floors('a', 'b', methods={1: 'points'})
    f[1]['align'] = {'method': 'points', 'pairs': [[[0.0, 0.0], [10.0, 1.0]], [[5.0, 5.0], [15.04, 6.0]]]}
    r = AL.align(f, {})[1]
    assert r['method'] == 'points' and r['shift'] == pytest.approx([-10.02, -1.0]) and r['spread'] == pytest.approx(0.02)
    assert AL.align(floors('a', 'b', methods={1: 'origin'}), {'a': grid(), 'b': grid(5, 5)})[1]['shift'] == [0.0, 0.0]
    # auto: another file without shared labels -> origin; one sheet without them -> align_failed
    r = AL.align(floors('a', 'b'), {'a': grid(), 'b': []})[1]
    assert r['method'] == 'origin'
    box = lambda x: {'kind': 'box', 'bbox': [x, 0.0, x + 10, 10.0], 'pad': 0.5, 'match': 'all'}  # noqa: E731
    with pytest.raises(BuildError) as e:
        AL.align(floors('a', 'a', areas={0: box(0.0), 1: box(20.0)}), {'a': []})
    assert e.value.code == 'align_failed' and 'one sheet' in e.value.message
    with pytest.raises(BuildError) as e:
        AL.align(floors('a', 'b', methods={1: 'grid'}), {'a': grid(), 'b': []})
    assert e.value.code == 'align_failed'


def test_labels_go_to_the_floor_their_line_meets():
    fl = HOUSE_SETTINGS['floors']
    got = AL.assign_labels(fl, HOUSE['gridLabels'])
    for key in ('ground', 'upper'):
        texts = {g['text'] for g in got[key]}
        assert {str(n) for n in range(2, 13)} <= texts and {'D', 'E', 'F', 'H', 'J'} <= texts
    used = {(g['text'], g['a']) for k in got for g in got[k]}
    by_end = {(g['text'], tuple(e)): g for g in HOUSE['gridLabels'] if g['line'] for e in g['line']}
    # the elevation labels (y 34.3 - 34.7) go to neither plan
    assert sum(1 for g in HOUSE['gridLabels'] if 34.0 <= g['y'] <= 35.0) >= 12
    assert all(by_end[u]['y'] < 31.0 for u in used)
    # the ground's labels lie left of x 74, the upper's right of it
    assert all(min(g['a'][0], g['b'][0]) < 74.0 for g in got['ground'])
    assert all(max(g['a'][0], g['b'][0]) > 73.0 for g in got['upper'])


def test_house_upper_floor_shift():
    r = AL.align(HOUSE_SETTINGS['floors'], {HOUSE_SETTINGS['sources'][0]['sha1']: HOUSE['gridLabels']})
    assert r[1]['method'] == 'grid' and r[1]['families'] == 2
    assert r[1]['shift'][0] == pytest.approx(-74.021, abs=0.002) and r[1]['shift'][1] == pytest.approx(0.0, abs=0.002)
    assert r[1]['spread'] < 0.002
    assert len(r[1]['labels']) >= 12


def test_bank_labels_under_whole_file():
    f = floors('l1', 'l2')
    got = AL.assign_labels(f[:1], BANK1['gridLabels'])
    assert len(got['F0']) == len([g for g in BANK1['gridLabels'] if g['line']])
    r = AL.align(f, {'l1': BANK1['gridLabels'], 'l2': BANK1['gridLabels']})[1]
    assert r['method'] == 'grid' and r['shift'] == [0.0, 0.0] and r['spread'] == pytest.approx(0.0, abs=1e-9)
