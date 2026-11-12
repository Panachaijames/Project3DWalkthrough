"""R1: terraces, X marks, holes, the finished slab and the ceilings on synthetic plans (docs/rooms/DESIGN.md R-4, R-5,
R-14; ACCEPTANCE RA-4, RA-5, RA-8's unit rows).

  * terraces (R-4.2): an area fenced by railings with a door onto it is floor; with no door it is not, and is asked about;
  * X marks (R-4.3): four corners; three corners and a side; a narrow slot; a column symbol; a void on the lowest floor;
    a shape over 60 m2 or over 30 % of the floor; a line is a diagonal of one X only; and what must not cut: grid
    lines, a rectangle with a divider, lines that cross with no outline drawn round them;
  * holes (R-4.3): the lift shaft on every floor, a shaft joined with an X, the stair well, the kept stair void, the
    arrival of a climbable stair, holes under 0.5 m2; the slab parts are safe for 3ds Max; small pieces are reported;
  * ceilings (R-5): the default height, a typed one, the floor above; a double-height space, a stair's headroom, a
    terrace, this floor's shafts; no hole over a low part.
"""
from __future__ import annotations

import pytest
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union

from test_r1_helpers import box, context, floor, line, room, run, slab, span
from walkthrough_builder.build import ceilings as CE
from walkthrough_builder.build import slabs as SL
from walkthrough_builder.build import xmarks as XM
from walkthrough_builder.build.bank import clean
from walkthrough_builder.build.model import _max_problem, max_safe

DOOR = span((2.0, 0.1), (3.0, 0.1))
UPPER = [{'key': 'F1', 'level': 0.0, 'wallHeight': 3.0}, {'key': 'F2', 'level': 3.2, 'wallHeight': 3.0}]


def rect_lines(x0, y0, x1, y1, role='other'):
    return [line(role, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], closed=True)]


def x_lines(x0, y0, x1, y1, role='other'):
    """A rectangle with its two diagonals: an X mark."""
    return rect_lines(x0, y0, x1, y1, role) + [line(role, [(x0, y0), (x1, y1)]), line(role, [(x0, y1), (x1, y0)])]


def upper(items=(), walls=None, **kw):
    """A 12 x 10 m upper floor (not the lowest of its stack) with one door."""
    return floor('F2', walls=walls if walls is not None else room(0, 0, 12, 10), items=list(items), spans=[DOOR], index=1,
                 level=3.2, **kw)


def run_upper(items=(), **kw):
    return run(upper(items, **kw), context(floors=UPPER))


def covered(parts, x, y) -> bool:
    return any(p['poly'].contains(Point(x, y)) for p in parts)


# --------------------------------------------------------------------------------------------------------- terraces
def railings(x0, y0, x1, y1):
    """The railing pieces round three sides of a terrace east of a wall (5 cm bands, as bank.railings_of builds them)."""
    path = LineString([(x0, y0), (x1, y0), (x1, y1), (x0, y1)])
    return [path.buffer(0.025, cap_style='flat', join_style='mitre')]


def test_a_fenced_area_with_a_door_is_a_terrace() -> None:
    """R-4.2: floor, no ceiling, no room; the plate is one piece with the building's."""
    walls = room(0, 0, 10, 10, gaps={'E': [(4.0, 5.0)]})
    door = span((9.9, 4.0), (9.9, 5.0), rid='F1-002')
    r = run(floor(walls=walls, spans=[DOOR, door], rails=railings(10.0, 2.0, 14.0, 8.0)))
    assert r['report']['terraces'] == pytest.approx(4.0 * 6.0, abs=0.6) and r['report']['ring'] == pytest.approx(100.0, abs=0.6)
    assert r['plate0'].contains(Point(12, 5)) and r['plate0'].contains(Point(13.99, 7.99)), 'the floor runs under the railings'
    assert len(r['net']['spaces']) == 1 and r['unfloored'] == [] and r['report']['dropped'] == []
    s = slab(r)
    assert len(s['parts']) == 1, 'one slab part: the terrace is joined to the ring'
    assert covered(s['ceilings'], 5, 5) and not covered(s['ceilings'], 12, 5), 'no ceiling over a terrace'


def test_a_fenced_area_with_no_door_gets_no_floor_and_is_asked_about() -> None:
    r = run(floor(walls=room(0, 0, 10, 10), spans=[DOOR], rails=railings(10.0, 2.0, 14.0, 8.0)))
    assert r['report']['terraces'] == 0.0 and not r['plate0'].contains(Point(12, 5))
    assert [d['why'] for d in r['report']['dropped']] == ['no door or passage opens onto it']
    assert len(r['unfloored']) == 1 and r['unfloored'][0]['poly'].contains(Point(12, 5))
    assert r['report']['unfloored'][0]['area'] == pytest.approx(24.0, abs=1.5)


def test_railing_lines_alone_fence_a_terrace() -> None:
    """A balustrade that is not built as pieces still fences: its lines are 2 cm strips in the larger network."""
    fence = line('railing', [(10.0, 2.0), (14.0, 2.0), (14.0, 8.0), (10.0, 8.0)])
    walls = room(0, 0, 10, 10, gaps={'E': [(4.0, 5.0)]})
    r = run(floor(walls=walls, spans=[DOOR, span((9.9, 4.0), (9.9, 5.0), rid='F1-002')], items=[fence]))
    assert r['report']['terraces'] == pytest.approx(24.0, abs=0.6) and r['plate0'].contains(Point(12, 5))
    assert len(r['net']['spaces']) == 1, 'railings bound terraces, not rooms'


# ---------------------------------------------------------------------------------------------------------- X marks
def marks(items, **kw):
    fb = upper(items, **kw)
    r = run(fb, context(floors=UPPER))
    return XM.x_marks(fb, r['net'], r['X']), r


def test_an_x_with_four_ends_at_the_corners_is_a_void_or_a_shaft() -> None:
    got, r = marks(x_lines(4, 3, 7, 5) + x_lines(8, 6, 9.4, 7.4))
    assert [(m['what'], round(m['area'], 2), m['why']) for m in got] == [('void', 6.0, None), ('shaft', 1.96, None)]
    assert got[0]['poly'].equals(box(4, 3, 7, 5))
    s = slab(r)
    assert [(w, round(v.area, 2)) for w, v in s['voids']] == [('void', 6.0), ('shaft', 1.96)]
    assert [(h['what'], h['area'], h['cut']) for h in s['holes']] == [('void', 6.0, True), ('shaft', 1.96, True)]
    assert Polygon(s['holes'][0]['o']).equals(box(4, 3, 7, 5)) and s['holes'][0]['at'] == [5.5, 4.0]
    assert not covered(s['parts'], 5.5, 4) and not covered(s['parts'], 8.7, 6.7) and covered(s['parts'], 2, 8)


def test_three_ends_at_corners_and_the_fourth_on_a_side() -> None:
    """The house's stair hall: one diagonal stops at the flight. The hole is the rectangle, not the hull of the ends."""
    items = rect_lines(3, 3, 8.45, 6.05) + [line('other', [(3, 3), (8.45, 6.05)]), line('other', [(3, 6.05), (8.45, 3.6)])]
    got, _r = marks(items)
    assert len(got) == 1 and got[0]['what'] == 'void' and got[0]['poly'].equals(box(3, 3, 8.45, 6.05))
    assert got[0]['area'] == pytest.approx(16.62, abs=0.01)
    # with the fourth end in the middle of the shape it is no X
    loose = rect_lines(3, 3, 8.45, 6.05) + [line('other', [(3, 3), (8.45, 6.05)]), line('other', [(3, 6.05), (7.0, 4.3)])]
    assert marks(loose)[0] == []


def test_a_rotated_x() -> None:
    import math
    c, s = math.cos(math.radians(30)), math.sin(math.radians(30))
    rot = lambda x, y: (5 + x * c - y * s, 5 + x * s + y * c)  # noqa: E731
    corners = [rot(-1.5, -1), rot(1.5, -1), rot(1.5, 1), rot(-1.5, 1)]
    items = [line('other', corners, closed=True), line('other', [corners[0], corners[2]]), line('other', [corners[1], corners[3]])]
    got, _r = marks(items)
    assert len(got) == 1 and got[0]['area'] == pytest.approx(6.0, abs=0.01) and got[0]['what'] == 'void'
    assert got[0]['poly'].symmetric_difference(Polygon(corners)).area < 0.01


def test_marks_that_are_reported_and_never_cut() -> None:
    """A slot narrower than 0.6 m (its diagonals cross at 11 degrees), a shape under 1 m2."""
    got, r = marks(x_lines(2, 3, 2.3, 6) + x_lines(6, 6, 6.9, 6.9))
    assert [(m['what'], round(m['area'], 2), m['why']) for m in got] == [('mark', 0.9, 'narrower than 0.6 m'), ('mark', 0.81, 'under 1 m2')]
    s = slab(r)
    assert s['voids'] == [] and [(h['what'], h['cut'], h['why']) for h in s['holes']] == [
        ('X mark', False, 'narrower than 0.6 m'), ('X mark', False, 'under 1 m2')]
    assert covered(s['parts'], 2.15, 4.5) and covered(s['parts'], 6.45, 6.45)


def test_a_column_symbol_is_no_x_mark() -> None:
    """A rectangle 80 % covered by wall or column parts."""
    column = box(5, 5, 6, 6)
    got, _r = marks(x_lines(5, 5, 6, 6, role='column'), walls=room(0, 0, 12, 10) + [column])
    assert got == []


def test_what_must_not_cut() -> None:
    """The bank's grid lines; the old suite's rectangle with a divider; lines that cross with nothing drawn round them
    (the house's wall lines crossing TREE lines)."""
    grid = [line('grid', [(-2, y), (14, y)]) for y in (2.0, 5.0, 8.0)] + [line('grid', [(x, -2), (x, 12)]) for x in (3.0, 6.0, 9.0)]
    grid += [line('grid', [(0, 0), (10, 10)]), line('grid', [(0, 10), (10, 0)])]
    divider = rect_lines(4, 4, 7, 5.5) + [line('other', [(5.5, 4), (5.5, 5.5)])]
    crossing = [line('wall', [(8, 6), (11, 9)]), line('other', [(8, 9), (11, 6)])]
    got, r = marks(grid + divider + crossing)
    assert got == []
    assert slab(r)['voids'] == []


def test_a_tile_grid_is_no_x_mark() -> None:
    """RR CODE-1: a 0.3 m tile grid on a layer with no role (11 x 11 lines of 3 m): every "+" of two grid lines read as
    the diagonals of a diamond whose outline 'was drawn' (every point within 0.15 m of some line): a 4.5 m2 void. An
    outline stretch is drawn only by lines that run with it. Nor a 45-degree pattern inside a drawn rectangle (the
    room's two diagonals among its tile lines): other long lines run through the box's middle."""
    grid = [line('other', [(4 + i * 0.3, 3), (4 + i * 0.3, 6)]) for i in range(11)] +            [line('other', [(4, 3 + i * 0.3), (7, 3 + i * 0.3)]) for i in range(11)]
    got, r = marks(grid)
    assert got == [] and slab(r)['voids'] == []
    tiles = rect_lines(4, 3, 7, 6) + [line('other', [(4, 3), (7, 6)]), line('other', [(4, 6), (7, 3)])]
    for k in (0.6, 1.2):                                    # the lines beside the two diagonals, both ways
        tiles += [line('other', [(4 + k, 3), (7, 6 - k)]), line('other', [(4, 3 + k), (7 - k, 6)]),
                  line('other', [(4, 6 - k), (7 - k, 3)]), line('other', [(4 + k, 6), (7, 3 + k)])]
    got, r = marks(tiles)
    assert got == [] and slab(r)['voids'] == []
    # a plain X in its rectangle is still a void, also with stair lines running through it (a stair hall's void)
    hall = x_lines(4, 3, 7, 6) + [line('stair', [(4, 3 + k * 0.28), (7, 3 + k * 0.28)]) for k in range(1, 10)]
    got, _r = marks(hall)
    assert [(m['what'], round(m['area'], 2)) for m in got] == [('void', 9.0)]


def test_a_line_is_a_diagonal_of_one_x_only() -> None:
    """The tower's lifts carry two X's, one inside the other: they are two marks, never paired across into larger
    boxes; the slab gets one hole, their union."""
    got, r = marks(x_lines(4, 4, 5.73, 5.6) + x_lines(4.2, 3.8, 5.6, 5.4))
    assert sorted(round(m['area'], 2) for m in got) == [2.24, 2.77]
    s = slab(r)
    assert [w for w, _v in s['voids']] == ['shaft'] and s['voids'][0][1].area == pytest.approx(3.0, abs=0.15)
    assert len(s['holes']) == 1 and s['holes'][0]['cut'] is True


def test_a_void_on_the_lowest_floor_is_not_cut_and_a_shaft_is() -> None:
    fb = floor(walls=room(0, 0, 12, 10), items=x_lines(4, 3, 7, 5) + x_lines(8, 6, 9.4, 7.4), spans=[DOOR])
    s = slab(run(fb))
    assert [(h['what'], h['cut'], h.get('why')) for h in s['holes']] == [('void', False, 'the lowest floor'), ('shaft', True, None)]
    assert [w for w, _v in s['voids']] == ['shaft'] and covered(s['parts'], 5.5, 4)


def test_a_shape_too_large_is_never_cut_by_itself() -> None:
    """Over 60 m2, or over 30 % of plate0: a hole-skipped flag asks."""
    big = run(floor('F2', walls=room(0, 0, 30, 20), items=x_lines(5, 5, 14, 13), spans=[DOOR], index=1, level=3.2), context(floors=UPPER))
    s = slab(big)
    assert s['voids'] == [] and [(h['what'], h['area'], h['cut'], h['why']) for h in s['holes']] == [('void', 72.0, False, 'over 60 m2')]
    third = slab(run_upper(x_lines(2, 2, 9, 8)))                    # 42 m2 of 120
    assert third['voids'] == [] and third['holes'][0]['why'] == 'over 30 % of the floor'


# ------------------------------------------------------------------------------------------------------------ holes
def lift_floor(key='F1', index=0, level=0.0, items=()):
    """A 12 x 10 m floor with a lift shaft of 2 x 2 m in its corner, behind a lift door."""
    walls = room(0, 0, 12, 10) + [box(2.2, 0.2, 2.4, 2.4), box(0.2, 2.2, 1.0, 2.4), box(1.9, 2.2, 2.2, 2.4)]
    lift = span((1.0, 2.3), (1.9, 2.3), rid=f'{key}-002', lift=True)
    return floor(key, walls=walls, spans=[span((5.0, 0.1), (6.0, 0.1), rid=f'{key}-001'), lift], items=list(items), index=index, level=level)


def test_the_lift_shaft_is_cut_on_every_floor() -> None:
    """R-4.3: today's rule (a cell of 12 m2 or less touching a lift door and no other opening), also on the lowest
    floor: the lowest floor of a model is not always the bottom of the building."""
    for fb in (lift_floor(), lift_floor('F2', 1, 3.2)):
        s = slab(run(fb, context(floors=UPPER)))
        assert [(w, round(v.area, 1)) for w, v in s['voids']] == [('lift shaft', 4.0)], fb['key']
        assert not covered(s['parts'], 1.2, 1.2) and covered(s['parts'], 6, 6)
    off = run(lift_floor(), context(floors=UPPER, options={'liftShafts': False}))
    assert slab(off)['voids'] == []


def test_an_x_in_a_lift_shaft_is_one_hole_with_it() -> None:
    """RA-5: the bank's lift: the X inside the lift door block and the lift-door cell, merged."""
    s = slab(run(lift_floor(items=x_lines(0.5, 0.5, 1.9, 1.9)), context(floors=UPPER)))
    assert [(w, round(v.area, 1)) for w, v in s['voids']] == [('lift shaft', 4.0)]
    assert [(h['what'], h['cut']) for h in s['holes']] == [('lift shaft', True)]


def stairs_with(key, *, well=None, kept=None, walk=None, width=1.0):
    built = []
    if well is not None:
        built.append({'stairway': {'id': 'S1', 'from': 'F1', 'to': key, 'walk': walk or [(0.0, 0.0), (1.0, 0.0)], 'width': width},
                      'treads': [], 'landings': [], 'wellOf': {key: well}, 'headroom': None, 'arrival': None, 'cuts': [],
                      'linesUsed': {}})
    left = [{'id': f'{key}-ST1', 'floor': key, 'why': 'no direction', 'text': '', 'severity': 'check', 'at': (0, 0),
             'outline': kept, 'keptVoid': kept, 'risers': 10}] if kept is not None else []
    return {'built': built, 'left': left, 'pairs': [], 'fixes': []}


def test_the_stair_well_and_the_kept_stair_void() -> None:
    """R-4.3: the well of a climbable stair is always cut; a stair that stays as lines keeps today's opening, on a floor
    that is not the lowest; a void under 0.5 m2 is reported, not cut."""
    r = run_upper()
    s = slab(r, stairs_with('F2', well=box(4, 4, 5.2, 7)))
    assert [(w, round(v.area, 2)) for w, v in s['voids']] == [('stair well', 3.6)] and not covered(s['parts'], 4.6, 5.5)
    s = slab(r, stairs_with('F2', kept=box(7, 4, 8.2, 7)))
    assert [(w, round(v.area, 2)) for w, v in s['voids']] == [('stair', 3.6)]
    s = slab(r, stairs_with('F2', kept=box(7, 4, 7.6, 4.6)))
    assert s['voids'] == [] and [(h['what'], h['cut'], h['why']) for h in s['holes']] == [('stair', False, 'under 0.5 m2')]
    low = run(floor(walls=room(0, 0, 12, 10), spans=[DOOR]), context(floors=UPPER))
    assert slab(low, stairs_with('F1', kept=box(7, 4, 8.2, 7)))['voids'] == [], 'none on the lowest floor'


def test_no_hole_takes_the_arrival_of_a_climbable_stair() -> None:
    """R-8.2: the 1.2 m past the top riser stays floor: an X hole and a kept void stop at the top riser's line."""
    walk = [(2.0, 5.0), (5.0, 5.0), (6.0, 5.0)]             # the top riser's middle at x 5, the walk's end 1.0 m past it
    r = run_upper(x_lines(4, 3, 5.6, 7))                    # an X over the stair that reaches 0.6 m past the top riser
    s = slab(r, stairs_with('F2', well=box(2, 4.45, 5, 5.55), walk=walk, width=1.0))
    by = {w: v for w, v in s['voids']}
    assert set(by) == {'stair well', 'void'}
    assert by['void'].area == pytest.approx(1.6 * 4.0 - 0.6 * 1.1, abs=0.01)
    assert covered(s['parts'], 5.3, 5.0) and covered(s['parts'], 5.9, 5.0), 'the arrival stands on the slab'
    assert not covered(s['parts'], 4.5, 5.0) and not covered(s['parts'], 5.3, 6.5) and not covered(s['parts'], 5.3, 3.5)
    # a kept void of another stair group does not take it either
    s2 = slab(run_upper(), {**stairs_with('F2', well=box(2, 4.45, 5, 5.55), walk=walk, width=1.0),
                            'left': stairs_with('F2', kept=box(4, 3, 5.6, 7))['left']})
    assert covered(s2['parts'], 5.3, 5.0) and not covered(s2['parts'], 5.3, 6.5)


def test_the_slab_parts_are_safe_for_max_and_small_pieces_are_reported() -> None:
    """R-4.4: simplify, grow by 3 cm, cut the holes again, keep the pieces over 4 m2; a piece of 4 m2 or less goes into
    `dropped`; a hole that touches the outline does not reach the 3ds Max script (model.max_safe)."""
    # a kept void from wall to wall cuts a 0.3 m strip off the east end: 3 m2
    r = run_upper()
    s = slab(r, stairs_with('F2', kept=box(11.5, -1, 11.7, 11)))
    assert len(s['parts']) == 1 and [(d['why'], 2.5 < d['area'] <= 4.0) for d in s['dropped']] == [('under 4 m2', True)]
    assert s['dropped'][0]['at'][0] > 11.7
    # a wider strip stays, as a part of its own
    assert len(slab(r, stairs_with('F2', kept=box(10.3, -1, 10.5, 11)))['parts']) == 2
    # an X hole on the plate's edge
    r2 = run_upper(x_lines(4, 9.0, 7, 9.98))
    s2 = slab(r2)
    assert [w for w, _v in s2['voids']] == ['shaft']
    for p in s2['parts']:
        rings = clean([p['poly']], 1.0, 0.0, 0.0)
        for ring in max_safe(rings, 1.0):
            assert _max_problem(ring) is None
            assert Polygon(ring['o'], ring['h']).is_valid
    plate = unary_union([p['poly'] for p in s2['parts']])
    assert plate.area == pytest.approx(r2['plate0'].area - 2.94 + 0.03 * r2['plate0'].length, abs=1.0)


def test_the_slab_frame() -> None:
    """The slab's thickness; the plinth of a lowest floor above the ground (U-9.5)."""
    X = context(floors=[{'key': 'F1', 'level': 0.9, 'wallHeight': 3.0}, {'key': 'F2', 'level': 4.8, 'wallHeight': 3.0, 'slabThickness': 0.3}])
    assert SL.slab_frame({'index': 0}, X) == (-0.9, {'plinth': True})
    assert SL.slab_frame({'index': 1}, X) == (-0.3, {})
    X.options['plinth'] = 'off'
    assert SL.slab_frame({'index': 0}, X) == (-0.25, {})


# --------------------------------------------------------------------------------------------------------- ceilings
def test_the_ceiling_height() -> None:
    """R-5.1: the typed height, else min(3.00, wall height - 0.30), never above the underside of the floor above less
    2 cm. (The test projects: 3.00 m; the two suites, with 3.00 m walls, 2.70 m; the house typed 3.00 / 2.90.)"""
    X = context(floors=[{'key': 'A', 'level': 0.0, 'wallHeight': 3.7}, {'key': 'B', 'level': 3.7, 'wallHeight': 3.0},
                        {'key': 'C', 'level': 6.6, 'wallHeight': 4.0, 'ceilingHeight': 2.9},
                        {'key': 'D', 'level': 9.5, 'wallHeight': 2.6}])
    assert [round(CE.ceiling_height(i, X), 3) for i in range(4)] == [3.0, 2.63, 2.63, 2.3]
    # B: min(3.00, 2.70) = 2.70, but the floor above is 2.90 m up with a 0.25 m slab: 2.63. C: typed 2.90, capped too


def test_one_ceiling_piece_with_no_hole_over_a_low_part() -> None:
    """R-5.2 / RA-8: cut from the plate's outline, top down: walls, single-line parts and furniture drawn on a wall layer
    make no hole in it."""
    low = box(4, 4, 4.06, 7)
    fb = floor(walls=room(0, 0, 12, 10) + [box(6, 0.2, 6.2, 6)], singles=[low], spans=[DOOR],
               items=[line('wall', [(8, 7), (10, 7), (10, 9), (8, 9)], closed=True)])
    s = slab(run(fb))
    assert len(s['ceilings']) == 1
    c = s['ceilings'][0]
    assert (c['kind'], c['label'], c['follow'], c['z0'], c['z1']) == ('ceiling', 'ceiling', False, 2.68, 2.7)
    assert len(c['poly'].interiors) == 0 and c['poly'].area == pytest.approx(120.0, abs=1.0)
    assert c['poly'].contains(Point(4.03, 5.5)) and c['poly'].contains(Point(6.1, 3)) and c['poly'].contains(Point(9, 8))


def test_no_ceiling_where_the_floor_above_is_open_or_a_stair_needs_headroom() -> None:
    """R-5.2: the holes of the floor above (a double-height space, a stair well), the headroom of a stair rising from
    this floor, this floor's own shafts. A void of this floor is open from the floor below up to this ceiling: the
    ceiling covers it."""
    r = run(lift_floor(items=x_lines(6, 4, 9, 7)), context(floors=UPPER))
    s = slab(r, holes_above=box(3, 6, 5, 9), headroom=box(9.5, 1, 10.5, 4))
    c = s['ceilings']
    assert not covered(c, 4, 7.5), 'the floor above has a hole here'
    assert not covered(c, 10, 2.5), 'a stair needs headroom here'
    assert not covered(c, 1.2, 1.2), "this floor's own lift shaft"
    assert covered(c, 7.5, 5.5), 'the X void of this floor is not cut on the lowest floor, and its ceiling stays'
    assert covered(c, 6, 9)
    upper_floor = run_upper(x_lines(6, 4, 9, 7))
    s2 = slab(upper_floor)
    assert not covered(s2['parts'], 7.5, 5.5) and covered(s2['ceilings'], 7.5, 5.5), 'the void is open up to this ceiling'
    off = run(lift_floor(), context(floors=UPPER, options={'ceilings': 'off'}))
    assert slab(off)['ceilings'] == []


def test_ceilings_never_overlap_and_small_pieces_are_dropped() -> None:
    r = run_upper()
    s = slab(r, holes_above=unary_union([box(-1, 4.6, 13, 5.4), box(11.85, -1, 11.95, 11)]))
    pieces = [c['poly'] for c in s['ceilings']]
    assert len(pieces) == 2, 'the two halves west of the slot; the two strips of 0.3 m2 east of it are dropped'
    assert all(a.intersection(b).area < 1e-9 for i, a in enumerate(pieces) for b in pieces[i + 1:])
    assert all(p.area >= 0.5 for p in pieces)


# ------------------------------------------------------------------------------------------ RR: the review's findings
def test_staff_keep_the_floor_in_an_x_hole() -> None:
    """RR BRK-2: an X in a drawn rectangle is cut as a hole (R-4.3) and nothing could undo it: a room fix with slab
    'floor' at a point in the hole keeps it as floor (the row stays, not cut, 'kept as floor by staff'); the X's drawn
    over the same lift go with it; another hole is still cut."""
    items = x_lines(4, 4, 5.73, 5.6) + x_lines(4.2, 3.8, 5.6, 5.4) + x_lines(8, 6, 9.4, 7.4)
    fx = {'rooms': [{'floor': 'F2', 'at': [4.9, 4.9], 'name': None, 'slab': 'floor', 'ceiling': 'auto'}]}
    r = run(upper(items), context(floors=UPPER, fixes=fx))
    s = slab(r)
    assert [(h['what'], h['cut'], h.get('why')) for h in s['holes']] == [
        ('shaft', False, 'kept as floor by staff'), ('shaft', False, 'kept as floor by staff'), ('shaft', True, None)]
    assert covered(s['parts'], 4.9, 4.9) and not covered(s['parts'], 8.7, 6.7)
    assert r['net']['more']['roomFixes'] == [{'fix': 0, 'matched': True}]
    # without the fix both are cut
    s = slab(run(upper(items), context(floors=UPPER)))
    assert [w for w, _v in s['voids']] == ['shaft', 'shaft'] and not covered(s['parts'], 4.9, 4.9)
