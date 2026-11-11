"""R1: the network branch of the builder (docs/rooms/DESIGN.md R-8.3, R-8.4, R-12.3): what build/bank.py does with R2's
StairsResult, on hand-made data (no drawing, no door finder).

  * `apply_cuts`: the clash cuts applied to a floor's parts: the piece under the stair gets the cut's top, `follow:
    false`, `fit: 'storey'` and its stairway's id; a piece that would be 0.05 m high or less is dropped; the rest of
    the part is unchanged; where two cuts overlap on one part the lower underside wins;
  * `_stair_reading`: what the model's `stairOutlines` and the summary's `stairs` block are made from under the new
    rule: R2's built stairs and its groups kept as lines.
"""
from __future__ import annotations

import pytest
from shapely.geometry import Point

from test_r1_helpers import box, floor
from walkthrough_builder.build import bank as BK


def cut(part, footprint, z1, key='F1'):
    return {'floor': key, 'part': part, 'footprint': footprint, 'z1': z1}


def stairs(cuts, sid='S1', frm='F1'):
    return {'built': [{'stairway': {'id': sid, 'from': frm, 'to': 'F2', 'risers': 16, 'riser': 0.188, 'landings': 1},
                       'treads': [], 'landings': [], 'wellOf': {}, 'headroom': None, 'arrival': None, 'cuts': cuts,
                       'linesUsed': {}}], 'left': [], 'pairs': [], 'fixes': []}


def test_a_wall_under_a_stair_is_cut_to_its_underside() -> None:
    """R-8.3: the part is split along the stair's footprint; the piece under it gets the lowest underside over it; the
    rest of the part is unchanged."""
    fb = floor(walls=[box(0, 0, 6, 0.2), box(0, 3, 6, 3.2)])
    before = [dict(p) for p in fb['parts']]
    rows = BK.apply_cuts(fb, stairs([cut(0, box(2, -1, 3.5, 1), 1.316)]))
    walls = [p for p in fb['parts'] if p['kind'] == 'wall']
    assert len(walls) == 4, 'the first wall is in three pieces now, the second untouched'
    under = [p for p in walls if p['extra'].get('stair')]
    assert len(under) == 1 and under[0]['poly'].equals(box(2, 0, 3.5, 0.2))
    assert (under[0]['z0'], under[0]['z1'], under[0]['follow'], under[0]['extra']) == (0.0, 1.316, False, {'fit': 'storey', 'stair': 'S1'})
    rest = [p for p in walls if not p['extra'].get('stair')]
    assert sorted(round(p['poly'].area, 2) for p in rest) == [0.4, 0.5, 1.2] and all(p['z1'] == 3.0 and p['follow'] for p in rest)
    assert any(p['poly'].equals(before[1]['poly']) and p['extra'] == {} for p in rest), 'a part no cut names is the same object'
    assert rows == [{'stair': 'S1', 'kind': 'wall', 'label': None, 'area': 0.3, 'z1': 1.316, 'at': rows[0]['at']}]
    assert box(2, 0, 3.5, 0.2).contains(Point(rows[0]['at']))


def test_a_piece_too_low_is_dropped_and_overlapping_cuts_take_the_lower_underside() -> None:
    """R-8.3: a piece whose new top would be 0.05 m or less is dropped (the row says so: z1 null); two treads over one
    wall: each stretch gets the lowest underside over it."""
    fb = floor(walls=[box(0, 0, 6, 0.2)])
    rows = BK.apply_cuts(fb, stairs([cut(0, box(1, -1, 2, 1), 0.04), cut(0, box(3, -1, 5, 1), 1.5), cut(0, box(4, -1, 5.5, 1), 0.9)]))
    under = sorted((p for p in fb['parts'] if p['extra'].get('stair')), key=lambda p: p['poly'].bounds[0])
    assert [(p['poly'].bounds[0], p['poly'].bounds[2], p['z1']) for p in under] == [(3.0, 4.0, 1.5), (4.0, 5.5, 0.9)]
    assert not any(p['poly'].intersects(box(1.01, 0.01, 1.99, 0.19)) for p in fb['parts']), 'nothing left under the low tread'
    assert sorted(((r['area'], r['z1']) for r in rows), key=lambda t: (t[0], t[1] or 0.0)) == [(0.2, None), (0.2, 1.5), (0.3, 0.9)]
    total = sum(p['poly'].area for p in fb['parts'])
    assert total == pytest.approx(1.2 - 0.2, abs=1e-6), 'the pieces do not overlap and lose only the dropped one'


def test_cuts_of_another_floor_and_no_cuts_change_nothing() -> None:
    fb = floor(walls=[box(0, 0, 6, 0.2)])
    parts = list(fb['parts'])
    assert BK.apply_cuts(fb, stairs([cut(0, box(2, -1, 3, 1), 1.0, key='F2')])) == [] and fb['parts'] == parts
    assert BK.apply_cuts(fb, stairs([])) == [] and fb['parts'] == parts
    assert BK.apply_cuts(fb, stairs([cut(0, box(20, 20, 21, 21), 1.0)])) == [], 'a footprint that misses the part'
    assert [p['poly'].area for p in fb['parts']] == pytest.approx([1.2])


def test_the_stair_reading_of_the_new_rule() -> None:
    """R-8.4 / R-12.3: with stairs 'climb' the model's stairOutlines and the summary's stairs block come from R2's
    StairsResult: every stair built from the floor and every group kept as lines on it; with 'lines' today's reading."""
    old = {'stairs': [{'hull': box(0, 0, 1, 1), 'flights': [], 'lines': []}], 'steps': ['x'], 'riser': 0.176, 'words': 2, 'lines': []}
    assert BK._stair_reading(old, 'F1', stairs([]), [], False) is old
    tread = lambda x: {'poly': box(x, 0, x + 0.28, 1.2)}  # noqa: E731
    res = stairs([])
    res['built'][0].update(treads=[tread(0.28 * k) for k in range(14)], landings=[{'poly': box(3.92, 0, 5.12, 1.2)}])
    res['left'] = [{'id': 'F1-ST2', 'floor': 'F1', 'why': 'no direction', 'text': '', 'severity': 'check', 'at': (9, 9),
                    'outline': box(8, 8, 10, 10), 'keptVoid': None, 'risers': 12},
                   {'id': 'F2-ST1', 'floor': 'F2', 'why': 'no direction', 'text': '', 'severity': 'check', 'at': (0, 0),
                    'outline': box(0, 0, 1, 1), 'keptVoid': None, 'risers': 5}]
    found = [{'id': 'F1-ST2', 'hull': box(8, 8, 10, 10), 'lines': [4, 5],
              'flights': [{'risers': [0] * 7, 'sense': 'arrives'}, {'risers': [0] * 5, 'sense': ''}]}]
    got = BK._stair_reading(old, 'F1', res, found, True)
    assert len(got['stairs']) == 2 and got['words'] == 2 and got['riser'] == 0.188 and len(got['steps']) == 15
    climb, kept = got['stairs']
    assert climb['hull'].bounds == (0.0, 0.0, 5.12, 1.2) and climb['flights'] == [{'dir': 'up', 'risers': 16}, {'dir': None, 'risers': 0}]
    assert kept['hull'].equals(box(8, 8, 10, 10)) and kept['lines'] == [4, 5]
    assert kept['flights'] == [{'dir': 'down', 'risers': 7}, {'dir': None, 'risers': 5}]
    upper = BK._stair_reading(old, 'F2', res, [], True)
    assert [g['hull'].bounds for g in upper['stairs']] == [(0.0, 0.0, 1.0, 1.0)] and upper['steps'] == [] and upper['riser'] == 0.176
    assert upper['stairs'][0]['flights'] == [], 'a group kept as lines that the reader gave no row for'
