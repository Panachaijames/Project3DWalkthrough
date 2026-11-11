"""R1: rooms and names on synthetic plans (docs/rooms/DESIGN.md R-3, R-14; ACCEPTANCE RA-3 and RA-7's unit rows).

  * which faces are rooms (R-3.1): half the edge is structure; a bed, a table and a sofa drawn as lines on a wall layer
    are not rooms; the label point and the ids;
  * which texts are names (R-3.2): short names kept, tags and stair words dropped, an area written in the name split
    off (comma decimals), the tag line below a name paired as today;
  * which room a name belongs to (R-3.2's five rules), several names in one room, the room's own name, staff names.
"""
from __future__ import annotations

import math

import pytest
from shapely.geometry import Point, Polygon

from test_r1_helpers import box, context, floor, line, room, room_at, run, span, text
from walkthrough_builder.build import rooms as RM

DOOR = span((6.0, 0.1), (7.0, 0.1))


def circle(cx, cy, r, n=24):
    return [(cx + r * math.cos(2 * math.pi * k / n), cy + r * math.sin(2 * math.pi * k / n)) for k in range(n)]


# ---------------------------------------------------------------------------------------------- which faces are rooms
def test_furniture_drawn_on_a_wall_layer_is_not_a_room() -> None:
    """RA-3 (unit): a bed, a table and a sofa corner drawn as lines on a wall layer inside a room leave it one room;
    the report counts them as enclosed shapes."""
    bed = line('wall', [(0.2, 4.0), (2.3, 4.0), (2.3, 5.8), (0.2, 5.8)])              # three lines against the west wall
    table = line('wall', circle(6.0, 6.0, 0.8), closed=True, t='CIRCLE')              # free in the room, 2.0 m2
    sofa = line('wall', [(7.2, 9.75), (9.75, 9.75), (9.75, 7.2), (8.85, 7.2), (8.85, 8.85), (7.2, 8.85)], closed=True)  # an L in the corner
    r = run(floor(walls=room(0, 0, 10, 10), items=[bed, table, sofa], spans=[DOOR]))
    assert len(r['net']['spaces']) == 1 and r['net']['shapes'] == 3
    one = r['net']['spaces'][0]
    assert one['poly'].area == pytest.approx(9.6 * 9.6, abs=0.6), 'the shapes are part of the room'
    for x, y in ((1.2, 4.9), (6.0, 6.0), (9.3, 9.3), (5.0, 2.0)):
        assert room_at(r, x, y) is one, (x, y)
    assert r['net']['ring'].area == pytest.approx(100.0, abs=0.6), 'the floor is not affected'
    assert len(r['net']['faces']) == 4, 'every face of 1 m2 or more is still listed'


def test_a_face_is_a_room_when_half_its_edge_is_structure() -> None:
    """R-3.1: built parts, spans, doorway closings, outline edges and staff lines count; single-line parts, loose drawn
    lines and bridges do not."""
    # a corner cut off by one loose line: two walls of its three sides -> more than half structure: a room
    cut = line('wall', [(0.2, 3.0), (3.0, 0.2)])
    r = run(floor(walls=room(0, 0, 10, 10), items=[cut], spans=[DOOR]))
    assert len(r['net']['spaces']) == 2 and r['net']['shapes'] == 0
    # a 4 x 4 m square of loose lines standing free in the room (16 m2: no object): none of its edge is structure, so
    # it is an enclosed shape, part of the room round it
    square = [(3, 3), (7, 3), (7, 7), (3, 7)]
    r2 = run(floor(walls=room(0, 0, 10, 10), items=[line('wall', square, closed=True)], spans=[DOOR]))
    assert len(r2['net']['spaces']) == 1 and r2['net']['shapes'] == 1 and room_at(r2, 5, 5) is room_at(r2, 1, 1)
    # the same square drawn as a room outline is structure: a room of its own, cut out of the room round it
    r3 = run(floor(walls=room(0, 0, 10, 10), items=[line('room-outline', square, closed=True)], spans=[DOOR]))
    assert len(r3['net']['spaces']) == 2 and r3['net']['shapes'] == 0
    assert room_at(r3, 5, 5)['source'] == 'outline' and room_at(r3, 1, 1)['source'] == 'network'
    assert room_at(r3, 5, 5)['poly'].area == pytest.approx(16.0, abs=0.2)


def test_the_label_point_and_the_ids() -> None:
    """R-3.1: the pole of inaccessibility; a point within 0.3 m of a wall moves to the representative point; ids
    `<floor key>-R<nnn>` by rows of 0.5 m from the top of the plan, left to right within a row."""
    ell = Polygon([(0, 0), (8, 0), (8, 2), (2, 2), (2, 8), (0, 8)])                    # its centroid lies near the corner
    p = RM.label_point(ell)
    assert ell.contains(p) and ell.boundary.distance(p) >= 0.9
    thin = box(0, 0, 6, 0.5)
    q = RM.label_point(thin)
    assert thin.contains(q)
    fb = floor(key='L2')
    faces = [box(0, 0, 3, 3), box(4, 0, 7, 3), box(0, 4, 3, 7), box(4, 4.2, 7, 7.2)]
    got = RM.spaces_of(fb, faces, context())
    assert [s['id'] for s in got] == ['L2-R001', 'L2-R002', 'L2-R003', 'L2-R004']
    # the two upper rooms share a 0.5 m row (y 5.5 and 5.7): left to right; then the lower row
    assert [(round(s['at'][0], 1), round(s['at'][1], 1)) for s in got] == [(1.5, 5.5), (5.5, 5.7), (1.5, 1.5), (5.5, 1.5)]
    assert all(s['source'] == 'network' and s['name'] == '' and s['names'] == [] and s['ceiling'] is True for s in got)
    assert [s['area'] for s in got] == [9.0, 9.0, 9.0, 9.0]


def test_a_building_standing_free_in_a_room_is_cut_out_of_it() -> None:
    """A core with its own rooms inside a hall: the hall's outline has a hole there, so a point stands in one room."""
    core = room(4, 4, 7, 7, t=0.1, gaps={'S': [(5.0, 5.9)]})
    r = run(floor(walls=room(0, 0, 10, 10) + core, spans=[DOOR, span((5.0, 4.05), (5.9, 4.05), t=0.1, rid='F1-002')]))
    assert len(r['net']['spaces']) == 2
    hall, inner = room_at(r, 2, 2), room_at(r, 5.5, 5.5)
    assert hall is not inner and len(hall['poly'].interiors) == 1
    assert hall['poly'].area == pytest.approx(9.6 * 9.6 - 9.0, abs=0.7) and inner['poly'].area == pytest.approx(2.8 * 2.8, abs=0.2)


# -------------------------------------------------------------------------------------------- which texts are names
def names(*texts):
    return RM.names_of(list(texts), context())


def test_short_names_are_kept_and_tags_are_not_names() -> None:
    """R-3.2 / RA-7: BAR, BOH., WC and F/C are names; D1, W12, ST-05 and R-01 are tags; UP and DN are stair words."""
    got, skipped, skipped_at = names(*[text(s, (i, 0.0)) for i, s in enumerate(
        ['BAR', 'BOH.', 'WC', 'F/C', 'D1', 'W12', 'ST-05', 'R-01', 'UP', 'DN', 'A', 'LIVING ROOM', '12'])])
    assert [r['name'] for r in got] == ['BAR', 'BOH.', 'WC', 'F/C', 'LIVING ROOM']
    assert skipped == ['D1', 'W12', 'ST-05', 'R-01', 'UP', 'DN', 'A', '12']
    assert [(t, x) for t, x, _y in skipped_at] == [('D1', 4.0), ('W12', 5.0), ('ST-05', 6.0), ('R-01', 7.0), ('UP', 8.0),
                                                   ('DN', 9.0), ('A', 10.0), ('12', 12.0)]
    assert all(r['area'] is None and r['areaValue'] is None for r in got)
    assert names(text('LOBBY', (0, 0), role='other'))[0] == [], 'only texts on room-name layers'


def test_an_area_written_in_the_name_is_split_off() -> None:
    """R-3.2 / RA-7: "Bar 7,6m2" gives the name Bar and keeps "Bar . 7,6m2" as its label; comma decimals are read; no
    name keeps a trailing area."""
    got, _s, _a = names(text('Bar 7,6m2', (0, 0)), text('Master Bedroom: 47m2', (5, 0)), text('Foyer 10 m²', (9, 0)),
                        text('GYM&YOGA   33m2', (12, 0)), text('Store 2', (15, 0)), text('Hall 12.5 sqm', (18, 0)))
    assert [(r['name'], r['area'], r['areaValue']) for r in got] == [
        ('Bar', '7,6m2', 7.6), ('Master Bedroom', '47m2', 47.0), ('Foyer', '10 m²', 10.0), ('GYM&YOGA', '33m2', 33.0),
        ('Store 2', None, None), ('Hall', '12.5 sqm', 12.5)]


def test_the_tag_line_below_a_name_is_paired_as_today() -> None:
    """Revit's room tag: the name, and 0 - 0.35 m below it its area line ("12 m²", or "Not Enclosed")."""
    got, skipped, _a = names(text('TOILET', (1.0, 5.0)), text('3.2 m²', (1.0, 4.8)), text('BOH', (6.0, 5.0)),
                             text('Not Enclosed', (6.0, 4.8)), text('D1', (9.0, 5.0)), text('2.0 m²', (9.0, 4.8)))
    assert [(r['name'], r['area'], r['areaValue']) for r in got] == [('TOILET', '3.2 m²', 3.2), ('BOH', None, None),
                                                                     ('D1', '2.0 m²', 2.0)]
    assert skipped == [], 'a text with a tag line under it is a room tag whatever it reads'


# ----------------------------------------------------------------------------------- which room a name belongs to
def spaces(*boxes):
    """The rooms of these boxes, in the order given (their ids follow the label points, not this order)."""
    polys = [box(*b) for b in boxes]
    got = RM.spaces_of(floor(), polys, context())
    return [next(s for s in got if s['poly'] is p) for p in polys]


def name(s, x, y, area=None):
    return {'name': s, 'area': None if area is None else f'{area} m²', 'areaValue': area, 'x': x, 'y': y}


def test_a_name_belongs_where_it_stands() -> None:
    """Rule 1: no written area, or the room fits it (within 15 %, or 0.5 m2)."""
    sp = spaces((0, 0, 4, 3), (5, 0, 7, 1.55))                       # 12.0 and 3.1 m2
    rows = [name('LOBBY', 2, 1.5), name('TOILET', 6, 0.8, 3.2), name('OFFICE', 1, 1, 13.5)]
    homeless, several = RM.name_rooms(sp, rows)
    assert homeless == [] and [r['space'] for r in rows] == [sp[0]['id'], sp[1]['id'], sp[0]['id']]
    assert [s['id'] for s in several] == [sp[0]['id']] and sp[0]['names'] == ['LOBBY', 'OFFICE'], 'in reading order'
    assert sp[0]['name'] == 'OFFICE', 'the name whose written area fits the room is its own name'
    assert sp[1]['name'] == 'TOILET' and sp[1]['names'] == ['TOILET']


def test_names_beside_their_rooms_are_placed_by_written_area_one_to_one() -> None:
    """Rule 2 (the old suite's labels): among the rooms within 3.0 m in which no name stands by rule 1 and whose area
    fits; the smallest area error first, then the nearest; one name per room."""
    sp = spaces((0, 0, 4, 2.5), (5, 0, 8.52, 2.5), (10, 0, 14, 4))               # 10.0, 8.8 and 16.0 m2
    rows = [name('Foyer', 4.5, 3.2, 10.0), name('Massage Room', 4.6, 3.0, 9.0)]
    homeless, several = RM.name_rooms(sp, rows)
    assert homeless == [] and several == []
    assert {r['name']: r['space'] for r in rows} == {'Foyer': sp[0]['id'], 'Massage Room': sp[1]['id']}
    # a room with a name standing in it by rule 1 is not offered to a name beside it
    sp2 = spaces((0, 0, 4, 2.5), (5, 0, 8.52, 2.5))
    rows2 = [name('Hall', 2, 1, None), name('Foyer', 4.5, 3.2, 10.0)]
    RM.name_rooms(sp2, rows2)
    assert rows2[1]['space'] == sp2[1]['id'], 'the nearest room within 1.5 m (rule 4): the 10 m2 room is taken'


def test_a_name_whose_area_does_not_fit_stays_where_it_stands() -> None:
    """Rule 3 / RA-7: the bank's FEMALE TOILET 6.4 stays in the 3.3 m2 face it stands in, and the F/C room next door,
    whose area would fit, keeps one name."""
    sp = spaces((0, 0, 2.2, 1.5), (2.4, 0, 5.4, 2.07))                          # 3.3 and 6.2 m2
    rows = [name('FEMALE TOILET', 1.1, 0.7, 6.4), name('F/C', 3.9, 1.0, 5.5)]
    homeless, several = RM.name_rooms(sp, rows)
    assert homeless == [] and several == []
    assert [r['space'] for r in rows] == [sp[0]['id'], sp[1]['id']] and sp[1]['names'] == ['F/C']
    # with no name in the room next door the name does go there by its area (rule 2)
    sp2 = spaces((0, 0, 2.2, 1.5), (2.4, 0, 5.4, 2.07))
    rows2 = [name('FEMALE TOILET', 1.1, 0.7, 6.4)]
    RM.name_rooms(sp2, rows2)
    assert rows2[0]['space'] == sp2[1]['id']


def test_by_distance_and_no_room() -> None:
    """Rule 4: the nearest room within 1.5 m; rule 5: else the name belongs to no room (flag room-open)."""
    sp = spaces((0, 0, 4, 3), (10, 0, 14, 3))
    rows = [name('PORCH', 5.2, 1.5), name('GARAGE', 7.0, 1.5), name('YARD', 8.7, 1.5)]
    homeless, _several = RM.name_rooms(sp, rows)
    assert [r['name'] for r in homeless] == ['GARAGE'] and 'space' not in rows[1]
    assert rows[0]['space'] == sp[0]['id'] and rows[2]['space'] == sp[1]['id']


def test_several_names_in_one_room_are_all_kept_in_reading_order() -> None:
    """R-3.2: an open-plan room carries several names on purpose; its own name is the staff name, else the name whose
    written area fits, else the first in reading order (rows from the top, left to right)."""
    sp = spaces((0, 0, 12, 10))
    rows = [name('WAITING AREA', 6, 2), name('CSO 5PAX', 8, 8), name('FOR 1 PAX', 2, 8.1)]
    homeless, several = RM.name_rooms(sp, rows)
    assert homeless == [] and [s['id'] for s in several] == [sp[0]['id']]
    assert sp[0]['names'] == ['FOR 1 PAX', 'CSO 5PAX', 'WAITING AREA'] and sp[0]['name'] == 'FOR 1 PAX'
    assert all(r['space'] == sp[0]['id'] for r in rows)
    sp2 = spaces((0, 0, 12, 10))
    RM.name_rooms(sp2, [name('WAITING AREA', 6, 2), name('HALL', 8, 8, 118.0)], staff_names=[(sp2[0]['id'], 'Banking hall')])
    assert sp2[0]['name'] == 'Banking hall' and sp2[0]['names'] == ['HALL', 'WAITING AREA']
    sp3 = spaces((0, 0, 12, 10))
    RM.name_rooms(sp3, [name('WAITING AREA', 6, 8), name('HALL', 8, 2, 118.0)])
    assert sp3[0]['name'] == 'HALL', 'the name whose written area fits comes before reading order'


def test_names_in_a_built_floor() -> None:
    """Through the network: the names of a floor's items, each in the room it stands in."""
    walls = room(0, 0, 10, 10) + [box(4.9, 0.2, 5.1, 4.0), box(4.9, 5.0, 5.1, 9.8)]
    items = [text('LOBBY', (2.5, 5.0)), text('Bar 7,6m2', (7.5, 5.0)), text('ST-05', (7.5, 8.0))]
    fb = floor(walls=walls, items=items, spans=[span((5.0, 4.0), (5.0, 5.0)), DOOR])
    r = run(fb)
    rows, skipped, _at = RM.names_of(fb['items'], r['X'])
    homeless, several = RM.name_rooms(r['net']['spaces'], rows)
    assert skipped == ['ST-05'] and homeless == [] and several == []
    assert room_at(r, 2.5, 5)['name'] == 'LOBBY' and room_at(r, 7.5, 5)['name'] == 'Bar'
    assert Point(rows[1]['x'], rows[1]['y']).within(room_at(r, 7.5, 5)['poly'])
