"""R1: the wall network on synthetic plans (docs/rooms/DESIGN.md R-2, R-14; ACCEPTANCE RA-3, RA-18's unit rows).

Hand-made floors (test_r1_helpers.floor: no drawing, no door finder), one rule at a time:
  * what bounds a space (R-2.1): built walls and spans, a lone glass line, a curtain-wall band, a closed room outline,
    an open outline line, a set-aside line with and without "the floor runs past it";
  * bridges (R-2.2): a corner gap bridged; a corner fillet, a free column and a slot between two walls not; a chain
    of specks left open; what a 1.0 m disc reaches in line at thicknesses 0.02 / 0.10 / 0.20 m;
  * doorway closings (R-2.6): end to end, unequal thicknesses, end to face only where the ring needs it; openings of
    0.8, 1.6 and 2.9 m in 0.1 and 0.2 m outside walls give floor or a flag with its mouth;
  * the ring (R-2.5): a detached 3 x 4 m room gets its floor, a detached 2 x 3 m shape only with a door on it.
"""
from __future__ import annotations

import math

import pytest
from shapely.geometry import LineString, Point
from shapely.ops import unary_union

from test_r1_helpers import box, closings, context, floor, line, room, room_at, run, span
from walkthrough_builder.build import network as NW
from walkthrough_builder.build.bank import polys

ROOM = (0, 0, 10, 10)                   # a 10 x 10 m room (outer faces)


def three_sided(t=0.2):
    """A 10 x 10 m room with no east wall: the south and north walls end at x 10 (two wall ends 9.6 m apart)."""
    return [box(0, 0, 10, t), box(0, 10 - t, 10, 10), box(0, t, t, 10 - t)]


# ----------------------------------------------------------------------------------------------- what bounds a space
def test_walls_and_spans_bound_a_room_and_rooms_divide_at_doors() -> None:
    walls = room(*ROOM) + [box(4.9, 0.2, 5.1, 4.0), box(4.9, 5.0, 5.1, 9.8)]              # a partition with a doorway
    r = run(floor(walls=walls, spans=[span((5.0, 4.0), (5.0, 5.0)), span((2.0, 0.1), (3.0, 0.1), rid='F1-002')]))
    assert len(r['net']['spaces']) == 2 and closings(r) == [], 'a detected opening still closes its doorway'
    assert room_at(r, 2.5, 5)['id'] != room_at(r, 7.5, 5)['id']
    assert r['net']['ring'].area == pytest.approx(100.0, abs=0.6) and r['plate0'].area == pytest.approx(100.0, abs=0.6)
    assert r['report']['ring'] == r['report']['plate'] and r['report']['unfloored'] == []


def test_a_lone_glass_line_closes_a_room() -> None:
    """R-2.1 point 4: a continuous line on a glass layer bounds a space; it is never built."""
    fb = floor(walls=three_sided(), items=[line('glass', [(9.9, 0.1), (9.9, 9.9)])],
               spans=[span((2.0, 0.1), (3.0, 0.1))])
    r = run(fb)
    assert len(r['net']['spaces']) == 1 and room_at(r, 5, 5) is not None
    assert not any(p['kind'] == 'glass' for p in fb['parts'])
    # a dashed line (the outline of the floor above, a beam) bounds nothing
    r2 = run(floor(walls=three_sided(), items=[line('glass', [(9.9, 0.1), (9.9, 9.9)], cont=False)],
                   spans=[span((2.0, 0.1), (3.0, 0.1))]))
    assert r2['net']['spaces'] == []
    # nor does a line on a layer that bounds nothing (furniture, other)
    r3 = run(floor(walls=three_sided(), items=[line('other', [(9.9, 0.1), (9.9, 9.9)])], spans=[span((2.0, 0.1), (3.0, 0.1))]))
    assert r3['net']['spaces'] == []


def test_a_curtain_wall_band_bounds_the_room_and_is_no_room_itself() -> None:
    """R-2.3: the two face lines of a 0.5 m curtain-wall band with mullions between them close the room; the band is an
    enclosed shape (its edge is drawn lines), not a room."""
    band = [line('glass', [(9.5, 0.1), (9.5, 9.9)]), line('glass', [(10.0, 0.1), (10.0, 9.9)])]
    band += [line('glass', [(9.5, y), (10.0, y)]) for y in (3.4, 6.6)]
    r = run(floor(walls=three_sided(), items=band, spans=[span((2.0, 0.1), (3.0, 0.1))]))
    assert len(r['net']['spaces']) == 1, 'one room; the cells of the band are not rooms'
    assert r['net']['shapes'] == 3 and len(r['net']['faces']) == 4, 'three cells of 1.5 m2 between the mullions'
    assert r['net']['ring'].area == pytest.approx(100.0, abs=1.0)
    assert room_at(r, 9.75, 5.0) is room_at(r, 5, 5), 'the cells are joined to the room across the inner face line'


def test_room_outlines_closed_or_open_bound_a_room() -> None:
    """R-2.4: the edges of a closed outline of 1 m2 or more, and an open outline line."""
    outline = line('room-outline', [(0.2, 0.2), (9.9, 0.2), (9.9, 9.8), (0.2, 9.8)], closed=True)
    r = run(floor(walls=three_sided(), items=[outline], spans=[span((2.0, 0.1), (3.0, 0.1))]))
    assert len(r['net']['spaces']) == 1 and r['net']['spaces'][0]['source'] == 'outline'
    almost = line('room-outline', [(0.2, 0.2), (9.9, 0.2), (9.9, 9.8), (0.2, 9.8), (0.2, 0.27)])     # ends 7 cm apart: closed
    assert len(run(floor(walls=three_sided(), items=[almost], spans=[span((2.0, 0.1), (3.0, 0.1))]))['net']['spaces']) == 1
    opened = line('room-outline', [(9.9, 0.1), (9.9, 9.9)])
    r3 = run(floor(walls=three_sided(), items=[opened], spans=[span((2.0, 0.1), (3.0, 0.1))]))
    assert len(r3['net']['spaces']) == 1 and r3['net']['spaces'][0]['source'] == 'network'
    tiny = line('room-outline', [(9.0, 4.0), (9.5, 4.0), (9.5, 4.5), (9.0, 4.5)], closed=True)      # under 1 m2: not used
    assert run(floor(walls=three_sided(), items=[tiny], spans=[span((2.0, 0.1), (3.0, 0.1))]))['net']['spaces'] == []


def test_a_set_aside_line_still_bounds_the_floor_unless_the_floor_runs_past_it() -> None:
    """R-2.1 point 7: the line is not among the floor's items any more (it is not built), but the network keeps it."""
    fb = floor(walls=three_sided(), spans=[span((2.0, 0.1), (3.0, 0.1))])
    aside = line('wall', [(9.9, 0.1), (9.9, 9.9)])
    kept = run(fb, context(aside={'F1': [aside]}))
    assert len(kept['net']['spaces']) == 1 and kept['plate0'].area > 95
    past = run(fb, context())                                # "the floor runs past it": the builder hands no line over
    assert past['net']['spaces'] == [] and past['plate0'].area < 10
    # a set-aside line of a layer that bounds nothing does not bound anything either
    assert run(fb, context(aside={'F1': [line('furniture', [(9.9, 0.1), (9.9, 9.9)])]}))['net']['spaces'] == []


# -------------------------------------------------------------------------------------------------------- bridges
def test_a_corner_gap_is_bridged_by_a_strip() -> None:
    """R-2.2: the east wall stops 0.4 m short of the north wall; the piece of the closing there lies between the room
    and the outside, so it becomes one straight 2 cm strip between the two parts."""
    walls = [box(0, 0, 10, 0.2), box(0, 9.8, 10, 10), box(0, 0.2, 0.2, 9.8), box(9.8, 0.2, 10, 9.4)]
    r = run(floor(walls=walls, spans=[span((2.0, 0.1), (3.0, 0.1))]))
    assert [c['kind'] for c in closings(r)] == ['bridge'] and len(r['net']['spaces']) == 1
    c = closings(r)[0]
    assert c['width'] == pytest.approx(0.4, abs=0.03) and 9.38 <= c['a'][1] <= 9.82 and 9.38 <= c['b'][1] <= 9.82
    assert r['net']['spaces'][0]['poly'].area == pytest.approx(9.6 * 9.6, abs=0.3), 'no area is taken out of the room'
    assert r['net']['ring'].area == pytest.approx(100.0, abs=0.6)
    assert r['report']['closings'] == [{'kind': 'bridge', 'a': [round(v, 3) for v in c['a']], 'b': [round(v, 3) for v in c['b']],
                                        'width': round(c['width'], 3)}]


def test_a_fillet_a_free_column_and_a_slot_are_not_bridged() -> None:
    """R-2.2 step 3: a piece of the closing with one open area round it is dropped."""
    column = box(4.0, 0.45, 4.4, 0.85)                                   # 0.25 m off the south wall, free in the room
    r = run(floor(walls=room(*ROOM) + [column], spans=[span((6.0, 0.1), (7.0, 0.1))]))
    assert closings(r) == [] and len(r['net']['spaces']) == 1
    slot = [box(20, 0, 26, 0.2), box(20, 0.7, 26, 0.9)]                  # two walls 0.5 m apart, open at both ends
    r2 = run(floor(walls=room(*ROOM) + slot, spans=[span((6.0, 0.1), (7.0, 0.1))]))
    assert closings(r2) == [] and len(r2['net']['spaces']) == 1
    assert r2['net']['ring'].area == pytest.approx(100.0, abs=0.6), 'the slot is no floor'


def test_a_chain_of_specks_is_left_open_and_asked_about() -> None:
    """R-2.2 step 1, R-4.2: a row of small free-standing pieces (fins, posts) takes no part in the bridges, so the area
    behind it is no room and gets no floor; with the specks taking part (the terrace rule) it is a fenced area with no
    door, which is flagged as an unfloored area."""
    fins = [box(9.9, y, 10.0, y + 0.1) for y in [0.4 + 0.35 * k for k in range(27)]]         # 0.1 x 0.1 m, 0.25 m apart
    r = run(floor(walls=three_sided() + fins))
    assert all(NW.is_speck(p) for p in fins)
    assert r['net']['spaces'] == [] and not r['net']['ring'].contains(Point(5, 5)) and closings(r) == []
    assert not r['plate0'].contains(Point(5, 5)), 'no floor'
    assert len(r['unfloored']) == 1 and r['unfloored'][0]['poly'].contains(Point(5, 5))
    assert r['report']['unfloored'][0]['area'] == pytest.approx(92.0, abs=4.0)
    assert [d['why'] for d in r['report']['dropped']] == ['no door or passage opens onto it']
    # with a door onto it the same fenced area is a terrace (R-4.2): a floor, and no room
    t = run(floor(walls=three_sided() + fins, spans=[span((2.0, 0.1), (3.0, 0.1))]))
    assert t['net']['spaces'] == [] and t['plate0'].contains(Point(5, 5)) and t['unfloored'] == []
    assert t['report']['terraces'] == pytest.approx(92.0, abs=4.0) and t['report']['dropped'] == []


@pytest.mark.parametrize('t, closes, opens', [(0.02, 0.18, 0.26), (0.10, 0.40, 0.50), (0.20, 0.55, 0.68)])
def test_what_the_one_metre_disc_reaches_in_line(t: float, closes: float, opens: float) -> None:
    """R-2.2: a gap in line closes up to 0.21 m between two drawn lines, 0.44 m in a 0.10 m wall, 0.60 m in a 0.20 m
    wall (the bridge rule alone, on a 10 x 10 m room with the gap in its south wall)."""
    for gap, want in ((closes, 1), (opens, 0)):
        walls = unary_union([box(0, 0, 5 - gap / 2, t), box(5 + gap / 2, 0, 10, t), box(0, 10 - t, 10, 10), box(0, 0, t, 10),
                             box(10 - t, 0, 10, 10)])
        got = NW.bridges_of(NW.working_copy(polys(walls)))
        assert len(got) == want, (t, gap)
        if want:
            assert got[0]['width'] == pytest.approx(gap, abs=0.02) and got[0]['a'][0] < 5 < got[0]['b'][0]


@pytest.mark.parametrize('gap', [0.3, 0.6, 0.9])
def test_in_line_gaps_in_the_network(gap: float) -> None:
    """The design's matrix (R-14) through the whole network: between two drawn lines none of the three gaps closes (a
    line has no wall end, and the disc reaches 0.21 m); in built walls of 0.10 and 0.20 m each one is a door-sized gap
    between two wall ends and gets a doorway closing (R-2.6), whatever the disc reaches."""
    lines = [line('wall', [(0, 0), (5 - gap / 2, 0)]), line('wall', [(5 + gap / 2, 0), (10, 0)]),
             line('wall', [(10, 0), (10, 10), (0, 10), (0, 0)])]
    thin = run(floor(items=lines))
    assert thin['net']['spaces'] == [] and closings(thin) == []
    for t in (0.10, 0.20):
        r = run(floor(walls=room(*ROOM, t=t, gaps={'S': [(5 - gap / 2, 5 + gap / 2)]})))
        assert [c['kind'] for c in closings(r)] == ['doorway'], (t, gap)
        assert closings(r)[0]['width'] == pytest.approx(gap, abs=0.01) and len(r['net']['spaces']) == 1


# ------------------------------------------------------------------------------------------------ doorway closings
@pytest.mark.parametrize('width', [0.8, 1.2, 1.88])
@pytest.mark.parametrize('thick', [(0.10, 0.10), (0.20, 0.20), (0.10, 0.20)])
def test_a_doorway_with_no_door_found_is_closed(width: float, thick: tuple) -> None:
    """RA-18 (unit): a doorway of 0.8, 1.2 or 1.88 m with no door found, between wall ends of equal thickness and of
    0.10 m against 0.20 m, is closed and the room keeps its floor. The strip runs straight across from the thinner
    end's middle; it builds nothing."""
    ta, tb = thick
    x0, x1 = 5 - width / 2, 5 + width / 2
    walls = [box(0, 0.1 - ta / 2, x0, 0.1 + ta / 2), box(x1, 0.1 - tb / 2, 10, 0.1 + tb / 2),      # the south wall, in two
             box(0, 9.8, 10, 10), box(0, 0.1, 0.2, 9.8), box(9.8, 0.1, 10, 9.8)]
    fb = floor(walls=walls)
    r = run(fb)
    assert [c['kind'] for c in closings(r)] == ['doorway']
    c = closings(r)[0]
    assert c['width'] == pytest.approx(width, abs=0.01)
    assert (c['a'][0], c['b'][0]) == pytest.approx((x0, x1), abs=0.01) and c['a'][1] == pytest.approx(0.1, abs=0.01)
    assert len(r['net']['spaces']) == 1 and r['plate0'].contains(Point(5, 5)) and r['unfloored'] == []
    assert len(fb['parts']) == 5, 'nothing is built in the doorway'
    assert r['net']['more']['doorways'][0]['how'] == 'ends'


def test_a_gap_of_two_and_a_half_metres_is_not_closed_and_is_flagged_with_its_mouth() -> None:
    """RA-18 (unit): wider than 2.0 m is no doorway; the room has no floor and a slab-gap flag carries its mouth."""
    r = run(floor(walls=room(*ROOM, gaps={'S': [(3.75, 6.25)]})))
    assert closings(r) == [] and r['net']['spaces'] == [] and not r['plate0'].contains(Point(5, 5))
    assert len(r['unfloored']) == 1
    u, row = r['unfloored'][0], r['report']['unfloored'][0]
    assert u['poly'].contains(Point(5, 5)) and u['area'] == pytest.approx(92.5, abs=2.0) and u['answered'] is False
    (ax, ay), (bx, by) = sorted(u['mouth'])
    assert (ax, bx) == pytest.approx((3.75, 6.25), abs=0.06) and 0.0 <= ay <= 0.2 and 0.0 <= by <= 0.2
    assert row['mouth'] == [[round(v, 3) for v in p] for p in u['mouth']] and row['kind'] == 'pocket'
    assert set(row) == {'area', 'at', 'o', 'mouth', 'answered', 'kind'}


@pytest.mark.parametrize('t', [0.10, 0.20])
@pytest.mark.parametrize('width', [0.8, 1.6, 2.9])
def test_a_room_that_does_not_close_is_floored_or_flagged(t: float, width: float) -> None:
    """RA-3 (unit): a 10 x 10 m room with one opening of 0.8, 1.6 or 2.9 m in its outside wall, in 0.10 m and in 0.20 m
    walls, with no door found: the room gets its floor (a doorway closing) or a slab-gap flag whose mouth lies on the
    opening."""
    x0, x1 = 5 - width / 2, 5 + width / 2
    r = run(floor(walls=room(*ROOM, t=t, gaps={'S': [(x0, x1)]})))
    opening = LineString([(x0, t / 2), (x1, t / 2)])
    if width <= 2.0:
        assert [c['kind'] for c in closings(r)] == ['doorway'] and r['plate0'].contains(Point(5, 5)) and r['unfloored'] == []
    else:
        assert closings(r) == [] and not r['plate0'].contains(Point(5, 5))
        assert len(r['unfloored']) == 1 and r['unfloored'][0]['mouth'] is not None
        assert all(opening.distance(Point(p)) <= t / 2 + 0.06 for p in r['unfloored'][0]['mouth'])
        assert math.dist(*r['unfloored'][0]['mouth']) == pytest.approx(width, abs=0.12)


def test_end_to_face_is_closed_only_where_the_ring_needs_it() -> None:
    """R-2.6: a wall end that squarely faces a wall's side is a candidate; it is kept only where the outside ring would
    lose 1 m2 or more without it."""
    # inside a closed building: a partition stub ends 1.2 m short of the north wall: two rooms would be one, no floor
    # is lost, so nothing is closed
    inside = run(floor(walls=room(*ROOM) + [box(4.9, 0.2, 5.1, 8.6)], spans=[span((2.0, 0.1), (3.0, 0.1))]))
    assert closings(inside) == [] and len(inside['net']['spaces']) == 1
    # in the outside wall: the east wall ends 1.2 m short of the north wall's side; without a closing the room leaks
    walls = [box(0, 0, 10, 0.2), box(0, 9.8, 10, 10), box(0, 0.2, 0.2, 9.8), box(9.8, 0.2, 10, 8.6)]
    r = run(floor(walls=walls, spans=[span((2.0, 0.1), (3.0, 0.1))]))
    assert [c['kind'] for c in closings(r)] == ['doorway'] and r['net']['more']['doorways'][0]['how'] == 'face'
    c = closings(r)[0]
    assert c['width'] == pytest.approx(1.2, abs=0.01) and c['a'][0] == pytest.approx(9.9, abs=0.01)
    assert len(r['net']['spaces']) == 1 and r['plate0'].contains(Point(5, 5))


def test_a_doorway_closing_counts_as_a_door_for_the_rules_that_ask() -> None:
    """R-2.6: it is handed to today's plate rule as a passage span, and counts as structure for the room test."""
    r = run(floor(walls=room(*ROOM, gaps={'S': [(4.4, 5.6)]})))
    assert r['report']['old'] == pytest.approx(r['report']['plate'], abs=1.0), "today's rule floors the room with it"
    assert len(r['net']['spaces']) == 1 and r['net']['shapes'] == 0


# ------------------------------------------------------------------------------------------------------ the ring
def test_a_detached_room_gets_its_floor_and_a_detached_shape_only_with_a_door() -> None:
    """R-2.5: the ring's pieces are measured by their filled outline (a 3 x 4 m room with 0.10 m walls has 1.4 m2 of
    wall and 12 m2 of outline); a detached piece under 12 m2 counts only when an opening span or a doorway closing
    lies on it."""
    main = room(*ROOM)
    door = span((2.0, 0.1), (3.0, 0.1))
    r = run(floor(walls=main + room(20, 0, 23, 4, t=0.1), spans=[door]))
    assert r['net']['ring'].contains(Point(21.5, 2)) and r['plate0'].contains(Point(21.5, 2))
    assert len(r['net']['spaces']) == 2
    shape = run(floor(walls=main + room(20, 0, 22, 3, t=0.1), spans=[door]))
    assert not shape['net']['ring'].contains(Point(21, 1.5)) and not shape['plate0'].contains(Point(21, 1.5))
    assert len(shape['net']['spaces']) == 1 and shape['net']['shapes'] == 1, 'its face is an object, not a room'
    with_door = run(floor(walls=main + room(20, 0, 22, 3, t=0.1, gaps={'S': [(20.6, 21.4)]}),
                          spans=[door, span((20.6, 0.05), (21.4, 0.05), t=0.1, rid='F1-002')]))
    assert with_door['net']['ring'].contains(Point(21, 1.5)) and len(with_door['net']['spaces']) == 2


def test_the_ring_and_the_rooms_are_in_a_fixed_order() -> None:
    walls = room(*ROOM) + [box(4.9, 0.2, 5.1, 9.8), box(0.2, 4.9, 4.9, 5.1)]
    spans = [span((5.0, 2.0), (5.0, 3.0)), span((5.0, 7.0), (5.0, 8.0), rid='F1-002'), span((7.0, 0.1), (8.0, 0.1), rid='F1-003')]
    a, b = run(floor(walls=walls, spans=spans)), run(floor(walls=list(reversed(walls)), spans=list(reversed(spans))))
    ids = lambda r: [(s['id'], round(s['at'][0], 2), round(s['at'][1], 2), s['area']) for s in r['net']['spaces']]  # noqa: E731
    assert ids(a) == ids(b) and [i for i, *_ in ids(a)] == ['F1-R001', 'F1-R002', 'F1-R003']
    ys = [s['at'][1] for s in a['net']['spaces']]
    assert ys[0] > 7 and ys[1] == pytest.approx(5.0, abs=0.1) and ys[2] < 3, 'rows from the top of the plan'
