"""R2: the stair builder on the synthetic drawings of tools/rooms/make-stair-dxf.py, read by the app's reader and built
through build() (docs/rooms/DESIGN.md R-7.5, R-7.6, R-8, R-14; ACCEPTANCE 2.1 R2), and the clash rule on hand-made
parts. Each drawing is a 10 x 8 m building; a build takes under a second."""
from __future__ import annotations

import math

import pytest
from shapely.geometry import Point, Polygon, box
from shapely.ops import unary_union

from test_r2_helpers import close, counts, mid, model_poly, synthetic
from walkthrough_builder.build import stairs_build as SB

R = 3.0 / 16


@pytest.fixture(scope='module')
def straight(tmp_path_factory) -> dict:
    return synthetic('straight', tmp_path_factory.mktemp('r2-straight'))


def parts(b, kind):
    return [p for p in b['res']['model']['parts'] if p['kind'] == kind]


# ------------------------------------------------------------------------------------------- treads, well, stairway
def test_treads_heights_and_the_lap_at_the_top(straight) -> None:
    sb = straight['stairs']['built'][0]
    assert len(sb['treads']) == 15 and sb['landings'] == []
    for j, t in enumerate(sb['treads'], 1):
        assert t['kind'] == 'tread' and t['label'] == f'stair S1 tread {j}' and t['floor'] == 'ground' and t['follow'] is False
        assert t['extra'] == {'fit': 'storey', 'stair': 'S1'}
        assert math.isclose(t['z1'], round(j * R, 3)) and math.isclose(t['z0'], round(max(0.0, (j - 2) * R), 3)), j
        x0, y0, x1, y1 = t['poly'].bounds
        assert math.isclose(y0, 1.5 + 0.28 * (j - 1), abs_tol=1e-6) and (x0, x1) == (1.0, 2.2)
        assert math.isclose(y1, 1.5 + 0.28 * j + (0.05 if j == 15 else 0.0), abs_tol=1e-6), 'the last tread laps 0.05 m past riser n'
    assert not parts(straight, 'step') and len(parts(straight, 'tread')) == 15


def test_the_well_by_headroom_not_grown_at_the_arrival(straight) -> None:
    """The treads whose top is higher than rise - slab - 2.10 m (0.70 m here: from tread 4), grown 0.05 m at the sides
    and the low end; at the arrival its edge is riser n. The upper slab then laps the last tread by 0.05 m."""
    sb = straight['stairs']['built'][0]
    top = 1.5 + 0.28 * 15
    assert close(sb['wellOf']['upper'], box(0.95, 1.5 + 0.28 * 3 - 0.05, 2.25, top), 1e-6)
    from walkthrough_builder.build.ceilings import ceiling_height
    low = next(j for j in range(1, 16) if j * R > ceiling_height(0, straight['X']) - 2.10)
    assert close(sb['headroom'], box(1.0, 1.5 + 0.28 * (low - 1), 2.2, top), 1e-6), "the lower floor's ceiling is open over these"
    m = straight['res']['model']
    off = m['offset']
    slab = unary_union([model_poly(p, off) for p in m['parts'] if p['kind'] == 'slab' and p['floor'] == 'upper'])
    lap = box(1.05, top + 0.005, 2.15, top + 0.045)
    assert slab.contains(lap), 'the slab of the upper floor laps the last tread'
    assert not slab.intersects(box(1.05, top - 0.5, 2.15, top - 0.01)), 'and is open over the treads below riser n'
    assert [v['what'] for v in m['voids']['upper']] == ['stair well']


def test_the_stairway_record(straight) -> None:
    sw = straight['res']['model']['stairways'][0]
    off = straight['res']['model']['offset']
    assert (sw['id'], sw['from'], sw['to'], sw['kind'], sw['risers'], sw['treads'], sw['landings'], sw['direction']) == \
        ('S1', 'ground', 'upper', 'straight', 16, 15, 0, 'word')
    assert (sw['riser'], sw['going'], sw['width']) == (0.188, 0.28, 1.2)
    walk = [(x + off[0], y + off[1]) for x, y in sw['walk']]
    assert [tuple(round(c, 3) for c in p) for p in walk] == [(1.6, 0.5), (1.6, 1.5), (1.6, 5.7), (1.6, 6.7)]
    assert sw['bottom'] == sw['walk'][0] and sw['top'] == sw['walk'][-1]
    lo, up = straight['plate0']['ground'], straight['plate0']['upper']
    assert lo.contains(Point(walk[0])) and up.contains(Point(walk[-1]))
    for fb, p in ((straight['floors'][0], walk[0]), (straight['floors'][1], walk[-1])):
        assert SB._walls(fb).distance(Point(p)) >= 0.3 - 1e-6, 'the walking line ends 0.3 m clear of walls'
    rep = straight['res']['report']['floors']['ground']['stairways']
    assert [(r['id'], r['state'], r['to'], r['risers'], r['riser']) for r in rep] == [('S1', 'climb', 'upper', 16, 0.188)]
    assert straight['stairs']['pairs'] == [] and straight['stairs']['left'] == []


def test_a_walking_line_end_is_moved_clear_of_a_wall(tmp_path) -> None:
    """The upper floor 2.2 m higher makes no difference in plan; a stair fix that turns the stair round puts its top
    0.3 m ... here: the stair turned by staff ends at the south, 1.3 m from the wall: its top keeps 1.0 m."""
    b = synthetic('no-direction', tmp_path, fixes=[{'floor': 'ground', 'at': [1.6, 3.0], 'bottom': [1.6, 5.7], 'use': 'auto'}])
    sb = b['stairs']['built'][0]
    sw = sb['stairway']
    assert sw['direction'] == 'staff' and b['stairs']['fixes'] == [{'fix': 0, 'matched': True}]
    assert [round(c, 3) for c in sw['walk'][0]] == [1.6, 6.7] and [round(c, 3) for c in sw['walk'][-1]] == [1.6, 0.5]
    assert round(sb['wellOf']['upper'].bounds[1], 3) == 1.5, 'the well ends on riser n, now at the south'
    # the same stair with its bottom 0.6 m from the north wall: the start of the walking line moves toward the stair
    walls = SB._walls(b['floors'][0])
    assert walls.distance(Point(sw['walk'][0])) >= 0.3 - 1e-6 and walls.distance(Point(sw['walk'][-1])) >= 0.3 - 1e-6


# ----------------------------------------------------------------------------------------- two plans, senses, floors
def test_one_stair_over_two_plans(tmp_path) -> None:
    """two-floor: risers 1 - 9 on the ground plan (the first step 0.40 m deep and flared, no word), 9 - 16 on the upper
    plan with DN: one stair of 16 risers, the direction from the other floor; the upper drawing is no stair of its own."""
    b = synthetic('two-floor', tmp_path)
    g, u = b['found']['ground'], b['found']['upper']
    assert counts(g[0]) == [9] and g[0]['more']['by'] is None and counts(u[0]) == [8] and u[0]['flights'][0]['sense'] == 'arrives'
    res = b['stairs']
    assert len(res['built']) == 1 and res['left'] == [] and res['pairs'] == []
    sb = res['built'][0]
    sw = sb['stairway']
    assert (sw['risers'], sw['riser'], sw['direction'], sw['kind'], sw['treads']) == (16, 0.188, 'floors', 'straight', 15)
    first = sb['treads'][0]['poly']
    assert close(first, Polygon([(0.8, 1.5), (2.4, 1.5), (2.2, 1.9), (1.0, 1.9)]), 1e-6), 'the flared first step keeps its shape'
    assert sb['linesUsed']['ground'] and sb['linesUsed']['upper']
    m = b['res']['model']
    assert m['stairs']['upper']['below'] == [] and m['stairs']['ground']['below'] == [], 'the lines that became treads are gone'
    assert [r for r in b['res']['report']['floors']['upper']['stairways']] == []


def test_the_down_up_pair_is_two_stairs(tmp_path) -> None:
    """The upper plan: the top 9 risers of the stair from below (DN) and, 0.76 m beside it, the next stair up (UP)."""
    b = synthetic('down-up-pair', tmp_path)
    u = b['found']['upper']
    assert [counts(r) for r in u] == [[9], [9]] and [r['flights'][0]['sense'] for r in u] == ['arrives', 'leaves']
    res = b['stairs']
    assert [sb['stairway']['risers'] for sb in res['built']] == [16] and res['built'][0]['stairway']['direction'] == 'word'
    assert [(s['id'], s['why'], s['severity'], s['risers']) for s in res['left']] == [('upper-ST2', 'it leaves the top floor', 'info', 9)]
    assert res['left'][0]['text'] == 'Stair at (3.6, 4.6): it leads to a floor that is not in the model.'
    void = res['left'][0]['keptVoid']
    assert close(void, box(2.96, 3.46, 4.16, 5.7), 0.01), "only the other flight's own footprint is cut, never the arrival"
    top = 5.7
    slab = unary_union([model_poly(p, b['res']['model']['offset']) for p in b['res']['model']['parts']
                        if p['kind'] == 'slab' and p['floor'] == 'upper'])
    assert slab.contains(box(1.05, top + 0.01, 2.15, top + 1.1)), 'the arrival: 1.2 m of floor past the top riser'


def test_a_stair_passes_a_split_level(tmp_path) -> None:
    """Three floors: the mezzanine at +1.50 m covers the east half only. 16 risers give 0.094 m to it (no fit) and
    0.1875 m to the upper floor, on whose plate the stair arrives: it rises there, and neither pair of floors is said
    to have no stair."""
    b = synthetic('split-level', tmp_path)
    res = b['stairs']
    sw = res['built'][0]['stairway']
    assert (sw['from'], sw['to'], sw['risers'], sw['riser']) == ('ground', 'upper', 16, 0.188)
    assert set(res['built'][0]['wellOf']) == {'mezz', 'upper'} and res['pairs'] == [] and res['left'] == []


# --------------------------------------------------------------------------------------- reasons, flags, staff fixes
def test_no_direction_and_the_flag_per_pair_of_floors(tmp_path) -> None:
    b = synthetic('no-direction', tmp_path)
    res = b['stairs']
    assert res['built'] == [] and res['pairs'] == [{'from': 'ground', 'to': 'upper'}]
    assert [(s['id'], s['why'], s['severity'], s['risers'], s['keptVoid']) for s in res['left']] == [('ground-ST1', 'no direction', 'check', 16, None)]
    assert res['left'][0]['text'] == 'Stair at (1.6, 3.6): kept as lines: which end is the bottom was not found.'
    m = b['res']['model']
    assert m['stairways'] == [] and not parts(b, 'tread') and not parts(b, 'step') and len(m['stairs']['ground']['below']) == 18 * 4
    row = b['res']['report']['floors']['ground']['stairways'][0]
    assert (row['state'], row['why'], row['to'], row['walk']) == ('lines', 'no direction', None, None)


def test_staff_keeps_a_stair_as_lines(tmp_path) -> None:
    b = synthetic('straight', tmp_path, fixes=[{'floor': 'ground', 'at': [1.6, 3.0], 'bottom': None, 'use': 'lines'},
                                               {'floor': 'ground', 'at': [8.0, 6.0], 'bottom': None, 'use': 'climb'}])
    res = b['stairs']
    assert res['built'] == [] and [(s['why'], s['severity'], s['text']) for s in res['left']] == \
        [('kept by staff', 'info', 'Stair at (1.6, 3.6): kept as lines.')]
    assert res['fixes'] == [{'fix': 0, 'matched': True}, {'fix': 1, 'matched': False}]
    assert b['res']['report']['fixes']['stairs'] == res['fixes']


def test_a_stair_fix_reaches_half_a_metre_as_the_design_and_the_web(tmp_path) -> None:
    """RR CODE-3: R-6.3: a stair fix applies to the stair whose outline holds its point or lies within 0.5 m (the reach
    was 0.3 m, the web's 0.5): 0.4 m east of the flight matches, 0.6 m does not."""
    b = synthetic('straight', tmp_path, fixes=[{'floor': 'ground', 'at': [2.6, 3.0], 'bottom': None, 'use': 'lines'},
                                               {'floor': 'ground', 'at': [2.8, 3.0], 'bottom': None, 'use': 'lines'}])
    assert [s['why'] for s in b['stairs']['left']] == ['kept by staff']
    assert b['stairs']['fixes'] == [{'fix': 0, 'matched': True}, {'fix': 1, 'matched': False}]


def test_the_stairways_row_carries_the_real_outline_not_the_hull(tmp_path) -> None:
    """RR CODE-3: the report's row (which the overlay copies and the web places and judges stair fixes by) holds the
    outside of the treads and landings joined: on an L stair the inner corner is not part of it."""
    b = synthetic('L', tmp_path)
    sb = b['stairs']['built'][0]
    real = unary_union([t['poly'] for t in sb['treads'] + sb['landings']])
    row = next(r for fl in b['res']['report']['floors'].values() for r in fl.get('stairways') or [] if r['state'] == 'climb')
    got = Polygon(row['outline'])
    assert got.is_valid and abs(got.area - real.area) <= 0.02 * real.area, (got.area, real.area)
    assert real.convex_hull.area > 1.2 * real.area, 'the L leaves an inner corner the hull would cover'
    assert got.contains(Point(row['at'])), 'the point of the row (where the web writes a new fix) lies on the stair'
    corner = real.convex_hull.difference(real.buffer(0.5)).representative_point()
    assert not got.buffer(0.5).contains(corner)


def test_the_riser_check_and_climb_it_as_drawn(tmp_path) -> None:
    """16 risers for 3.70 m give 0.231 m: lines, with the storeys that would fit; staff's "climb it as drawn" builds it
    (0.25 m or less). For 4.40 m (0.275 m) not even that; for 6.00 m no floor is at the stair's top."""
    b = synthetic('straight', tmp_path / 'a', levels={'upper': 3.7})
    left = b['stairs']['left']
    assert [(s['why'], s['severity'], s['risers']) for s in left] == [('the riser does not fit', 'check', 16)]
    assert left[0]['text'] == ('Stair at (1.6, 3.6): 16 steps for 3.70 m give 0.231 m each. The drawing may not show every step, or '
                               'the levels may be off. A storey of 2.24–3.36 m would fit every stair between these floors.')
    assert b['stairs']['pairs'] == [{'from': 'ground', 'to': 'upper'}]
    climb = [{'floor': 'ground', 'at': [1.6, 3.0], 'bottom': None, 'use': 'climb'}]
    b = synthetic('straight', tmp_path / 'b', levels={'upper': 3.7}, fixes=climb)
    sw = b['stairs']['built'][0]['stairway']
    assert (sw['risers'], sw['riser']) == (16, 0.231) and b['stairs']['left'] == [] and b['stairs']['fixes'] == [{'fix': 0, 'matched': True}]
    b = synthetic('straight', tmp_path / 'c', levels={'upper': 4.4}, fixes=climb)
    assert b['stairs']['built'] == [] and b['stairs']['left'][0]['why'] == 'the riser does not fit'
    # RR BRK-4: the refusal of staff's choice is said, with the riser to three decimals (0.275 is not "0.28")
    assert b['stairs']['left'][0]['text'] == (
        'Stair at (1.6, 3.6): "Climb it as drawn" is not possible: each step would be 0.275 m (the limit is 0.25 m). 16 steps '
        'for 4.40 m: the drawing may not show every step, or the levels may be off. A storey of 2.24–3.36 m would fit every '
        'stair between these floors.')
    assert b['stairs']['left'][0]['severity'] == 'check' and b['stairs']['fixes'] == [{'fix': 0, 'matched': True}]
    b = synthetic('straight', tmp_path / 'd', levels={'upper': 6.0})
    assert [(s['why'], s['severity']) for s in b['stairs']['left']] == [('no floor at its top', 'info')]
    assert b['stairs']['left'][0]['text'] == ('Stair at (1.6, 3.6): its 16 steps would rise about 2.2–3.4 m: no floor of the model '
                                              'is at that height.')


def test_the_lines_option_builds_no_stair(tmp_path) -> None:
    b = synthetic('straight', tmp_path, rules={'slabs': 'network', 'ceilings': 'auto', 'stairs': 'lines'})
    assert b['stairs']['built'] == [] and [s['why'] for s in b['stairs']['left']] == ['kept as lines']
    assert b['res']['model']['stairways'] == [] and len(parts(b, 'step')) == 15, "today's two-riser steps, with a word"


def test_the_riser_text_has_three_decimals(tmp_path) -> None:
    """RR BRK-4: 16 risers for 3.40 m are 0.2125 m: outside the 0.14 - 0.21 rule, and printed so (not as 0.21)."""
    b = synthetic('straight', tmp_path, levels={'upper': 3.4})
    assert [s['why'] for s in b['stairs']['left']] == ['the riser does not fit']
    assert '16 steps for 3.40 m give 0.212 m each' in b['stairs']['left'][0]['text'] or         '16 steps for 3.40 m give 0.213 m each' in b['stairs']['left'][0]['text']


def test_the_bottom_point_never_leaves_the_plate(straight) -> None:
    """RR BRK-5: a stair that starts just inside a door: the floor ends 0.2 m before riser 1 (y 1.3), so no point 0.3 -
    1.0 m before it stands on the plate. The walking line then starts 0.1 m before the riser, on the plate (it was
    0.3 m before it, off the plate, where a walker cannot move)."""
    plate0 = dict(straight['plate0'])
    plate0['ground'] = plate0['ground'].intersection(box(-50, 1.3, 50, 50))
    res = SB.build_stairs(straight['floors'], straight['found'], straight['nets'], plate0, {}, straight['X'])
    sw = res['built'][0]['stairway']
    assert plate0['ground'].contains(Point(sw['walk'][0])) and sw['bottom'] == sw['walk'][0]
    assert tuple(round(c, 3) for c in sw['walk'][0]) == (1.6, 1.4)
    # the plate ends ON the riser: the nearest plate point beside the first going, a little inside
    plate0['ground'] = straight['plate0']['ground'].intersection(box(-50, 1.5, 50, 50))
    res = SB.build_stairs(straight['floors'], straight['found'], straight['nets'], plate0, {}, straight['X'])
    assert res['built'] and plate0['ground'].contains(Point(res['built'][0]['stairway']['walk'][0]))


def test_the_lines_option_text_is_in_the_floors_own_frame(straight) -> None:
    """RR CODE-6: with options.stairs 'lines' on a shifted (aligned) floor the text names the sheet point, as every
    other stair text does (_where), not the build frame's."""
    X = straight['X']

    class Shifted:
        options = {**X.options, 'stairs': 'lines'}
        floor_info = {k: {**v, 'shift': (5.0, 2.0)} for k, v in X.floor_info.items()}

    class Plain(Shifted):
        floor_info = X.floor_info
    args = (straight['floors'], straight['found'], straight['nets'], straight['plate0'], {})
    plain = [r['text'] for r in SB.build_stairs(*args, Plain)['left']]
    moved = [r['text'] for r in SB.build_stairs(*args, Shifted)['left']]
    assert plain and plain[0] == 'Stair at (1.6, 3.6): kept as lines.'
    assert moved[0] == 'Stair at (-3.4, 1.6): kept as lines.'


# ------------------------------------------------------------------------------------------------------ the clash cuts
def wall(poly, z1=3.0, kind='wall'):
    return {'floor': 'F1', 'kind': kind, 'poly': poly, 'z0': 0.0, 'z1': z1, 'follow': True, 'label': None, 'extra': {}}


def test_the_clash_cuts_and_their_minimum_overlap() -> None:
    """A part is cut where steps whose underside is lower than its top overlap it by 2 cm in depth and 0.01 m2 or
    more; a side wall that only touches the treads is not; the piece gets the lowest underside over it."""
    steps = [(box(0, 0.28 * k, 1.2, 0.28 * (k + 1)), max(0.0, (k - 1) * 0.1875), (k + 1) * 0.1875, 0) for k in range(10)]
    fb = {'key': 'F1', 'parts': [
        wall(box(-0.2, 0, 0.005, 2.8)),                       # the side wall: touches the treads by 5 mm along the flight
        wall(box(0.4, 1.5, 0.5, 2.5)),                        # a wall under treads 6 - 9
        wall(box(0.0, 2.0, 0.015, 2.5)),                      # 1.5 cm deep: under the 2 cm
        wall(box(0.6, 0.6, 0.69, 0.7)),                       # 0.009 m2: under the 0.01 m2
        wall(box(0.4, 0.3, 0.5, 0.5), z1=0.0),                # lower than every underside: nothing is in the way
        wall(box(0.7, 1.5, 0.8, 2.5), kind='slab'),           # not a kind a stair cuts
    ]}
    cuts = SB.clash_cuts(fb, steps)
    assert [(c['floor'], c['part']) for c in cuts] == [('F1', 1)]
    assert math.isclose(cuts[0]['z1'], 4 * 0.1875) and math.isclose(cuts[0]['footprint'].area, 0.1)
    # under two flights: one cut for each, with its own lowest underside
    two = steps[:5] + [(b_, z0, z1, 1) for b_, z0, z1, _g in steps[5:]]
    cuts = SB.clash_cuts({'key': 'F1', 'parts': [wall(box(0.4, 0.6, 0.5, 2.5))]}, two)
    assert [round(c['z1'], 4) for c in cuts] == [round(1 * 0.1875, 4), round(4 * 0.1875, 4)]
