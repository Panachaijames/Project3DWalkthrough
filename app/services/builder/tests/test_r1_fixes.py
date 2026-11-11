"""R1: the staff fixes of the rooms milestone (docs/rooms/DESIGN.md R-6.2, R-6.3, R-2.1 points 6 and 7; ACCEPTANCE RA-13,
RA-18's set-aside row).

On hand-made floors: a closing line (and one that stops 0.4 m short of a thin line), a removed closing, the room fixes
(a name, "no floor here", "no ceiling", "it is outdoors", "floor here"), an unmatched fix, a floor with an alignment
shift (fix points and report rows are in the floor's own sheet frame). Through prepare_floors and build() on a small
drawing with keys: a wall drawn across a doorway, set aside, with and without "the floor runs past it"; the report's
fix rows; a staff name in a room with no drawn name. And the settings: the new fixes' choices and the options.
"""
from __future__ import annotations

import pytest
from shapely.geometry import Point, Polygon

from test_r1_helpers import ROOMS_LAYERS, box, closings, context, floor, line, room, room_at, rooms_dxf, run, slab, span
from test_u3_helpers import fake_detector, plan_settings, read_plan, run_build, source_ctx  # noqa: F401
from walkthrough_builder import contracts, keys as K, names as N
from walkthrough_builder.build import BuildError, prepare_floors
from walkthrough_builder.build import fixes as FX
from walkthrough_builder.build import settings as ST

SHA = 'd' * 40
DOOR = span((2.0, 0.1), (3.0, 0.1))


def three_sided():
    return [box(0, 0, 10, 0.2), box(0, 9.8, 10, 10), box(0, 0.2, 0.2, 9.8)]


def closing(a, b, use='line', floor_key='F1'):
    return {'floor': floor_key, 'a': list(a), 'b': list(b), 'use': use}


def room_fix(at, name=None, slab='auto', ceiling='auto', floor_key='F1'):
    return {'floor': floor_key, 'at': list(at), 'name': name, 'slab': slab, 'ceiling': ceiling}


# ---------------------------------------------------------------------------------------------------- closing lines
def test_a_closing_line_closes_a_room_and_builds_nothing() -> None:
    """R-6.2: a 2 cm strip from a to b in the network; the room it closes is a staff room; the report lists the line."""
    fb = floor(walls=three_sided(), spans=[DOOR])
    assert run(fb)['net']['spaces'] == []
    r = run(fb, context(fixes={'closings': [closing((9.9, 0.1), (9.9, 9.9))]}))
    assert len(r['net']['spaces']) == 1 and r['net']['spaces'][0]['source'] == 'staff' and r['plate0'].contains(Point(5, 5))
    assert r['report']['closings'] == [{'kind': 'staff', 'a': [9.9, 0.1], 'b': [9.9, 9.9], 'width': 9.8, 'fix': 0}]
    assert r['net']['more']['closingFixes'] == [{'fix': 0, 'matched': True}]
    assert len(fb['parts']) == 3, 'nothing is built'
    assert r['net']['closings'] == [{'kind': 'staff', 'a': (9.9, 0.1), 'b': (9.9, 9.9), 'width': pytest.approx(9.8), 'fix': 0}]


def test_a_closing_line_that_stops_short_is_extended_to_the_network() -> None:
    """R-2.1 point 6: each end is extended to the nearest part of the network within 0.5 m, so a line that stops 0.4 m
    short of a thin facade line still closes; one that stops 0.7 m short does not."""
    facade = line('glass', [(9.9, 0.1), (9.9, 6.0)])
    fb = floor(walls=three_sided(), items=[facade], spans=[DOOR])
    assert run(fb)['net']['spaces'] == []
    near = run(fb, context(fixes={'closings': [closing((9.9, 9.7), (9.9, 6.4))]}))
    assert len(near['net']['spaces']) == 1
    far = run(fb, context(fixes={'closings': [closing((9.9, 9.7), (9.9, 6.7))]}))
    assert far['net']['spaces'] == [] and far['net']['more']['closingFixes'] == [{'fix': 0, 'matched': True}]


def test_one_of_the_apps_closings_removed() -> None:
    """R-6.2: "Not a doorway: one room" leaves out the doorway closing whose two ends lie within 0.3 m of a and b; a
    removed closing that is not there is unmatched."""
    fb = floor(walls=room(0, 0, 10, 10, gaps={'S': [(4.4, 5.6)]}))
    assert [c['kind'] for c in closings(run(fb))] == ['doorway']
    r = run(fb, context(fixes={'closings': [closing((5.5, 0.2), (4.5, 0.0), 'none'), closing((1.0, 5.0), (2.0, 5.0), 'none')]}))
    assert closings(r) == [] and r['net']['spaces'] == [] and not r['plate0'].contains(Point(5, 5))
    assert r['net']['more']['closingFixes'] == [{'fix': 0, 'matched': True}, {'fix': 1, 'matched': False}]
    assert len(r['unfloored']) == 1 and r['unfloored'][0]['mouth'] is not None, 'the room is asked about instead'
    # a bridge is removed the same way
    walls = [box(0, 0, 10, 0.2), box(0, 9.8, 10, 10), box(0, 0.2, 0.2, 9.8), box(9.8, 0.2, 10, 9.4)]
    fb2 = floor(walls=walls, spans=[DOOR])
    c = closings(run(fb2))[0]
    r2 = run(fb2, context(fixes={'closings': [closing(c['a'], c['b'], 'none')]}))
    assert closings(r2, 'bridge') == [] and r2['net']['more']['closingFixes'] == [{'fix': 0, 'matched': True}]


def test_the_removed_closings_matcher() -> None:
    cs = [{'a': (0.0, 0.0), 'b': (1.0, 0.0)}, {'a': (5.0, 0.0), 'b': (5.0, 1.2)}]
    assert FX.removed_closings(cs, (5.1, 1.0), (4.9, 0.2)) == [cs[1]]
    assert FX.removed_closings(cs, (0.0, 0.31), (1.0, 0.0)) == []
    assert FX.floor_fixes({'rooms': [{'floor': 'A'}, {'floor': 'B'}, {'floor': 'A'}]}, 'rooms', 'A') == [(0, {'floor': 'A'}), (2, {'floor': 'A'})]
    assert FX.floor_fixes(None, 'rooms', 'A') == [] and FX.floor_fixes({}, 'closings', 'A') == []


# -------------------------------------------------------------------------------------------------------- room fixes
def two_rooms(items=()):
    walls = room(0, 0, 10, 10) + [box(4.9, 0.2, 5.1, 4.0), box(4.9, 5.0, 5.1, 9.8)]
    return floor(walls=walls, items=list(items), spans=[span((5.0, 4.0), (5.0, 5.0)), DOOR])


def test_a_room_fix_names_a_room_and_marks_no_floor_and_no_ceiling() -> None:
    fb = two_rooms()
    fixes = {'rooms': [room_fix((2.5, 5.0), name='Archive'), room_fix((7.5, 5.0), slab='none', ceiling='none')]}
    r = run(fb, context(fixes=fixes))
    west, east = room_at(r, 2.5, 5), room_at(r, 7.5, 5)
    assert r['net']['more']['roomFixes'] == [{'fix': 0, 'matched': True}, {'fix': 1, 'matched': True}]
    assert r['net']['more']['staffNames'] == [(west['id'], 'Archive')]
    assert east['ceiling'] is False and west['ceiling'] is True
    assert not r['plate0'].contains(Point(7.5, 5)) and r['plate0'].contains(Point(2.5, 5))
    assert r['report']['plate'] == pytest.approx(100.0 - 4.7 * 9.6, abs=1.0)
    s = slab(r)
    assert [(w, round(v.area, 1)) for w, v in s['voids']] == [('no floor', round(east['poly'].area, 1))]
    assert [(h['what'], h['cut']) for h in s['holes']] == [('no floor', True)]
    assert not any(c['poly'].contains(Point(7.5, 5)) for c in s['ceilings']) and any(c['poly'].contains(Point(2.5, 5)) for c in s['ceilings'])
    assert not any(p['poly'].contains(Point(7.5, 5)) for p in s['parts'])


def test_no_ceiling_alone_keeps_the_floor() -> None:
    r = run(two_rooms(), context(fixes={'rooms': [room_fix((7.5, 5.0), ceiling='none')]}))
    s = slab(r)
    assert r['plate0'].contains(Point(7.5, 5)) and s['voids'] == []
    assert not any(c['poly'].contains(Point(7.5, 5)) for c in s['ceilings'])


def test_an_unfloored_area_is_answered_outdoors_or_floored() -> None:
    """R-6.2: "It is outdoors" answers the unfloored area that contains the point (it is not flagged again); "Floor
    here" adds that area, closed across its mouth, to the plate."""
    fb = floor(walls=room(0, 0, 10, 10, gaps={'S': [(3.5, 6.4)]}))
    plain = run(fb)
    assert len(plain['unfloored']) == 1 and plain['unfloored'][0]['answered'] is False
    out = run(fb, context(fixes={'rooms': [room_fix((5, 5), slab='none')]}))
    assert [u['answered'] for u in out['unfloored']] == [True] and out['report']['unfloored'][0]['answered'] is True
    assert not out['plate0'].contains(Point(5, 5)) and out['net']['more']['roomFixes'] == [{'fix': 0, 'matched': True}]
    here = run(fb, context(fixes={'rooms': [room_fix((5, 5), slab='floor')]}))
    assert here['unfloored'] == [] and here['plate0'].contains(Point(5, 5)) and here['plate0'].contains(Point(0.5, 9.5))
    assert not here['plate0'].contains(Point(5, -0.3)), 'the floor ends on the line across the mouth'
    assert here['report']['plate'] == pytest.approx(100.0, abs=1.5)
    s = slab(here)
    assert any(c['poly'].contains(Point(5, 5)) for c in s['ceilings']), 'a floored area gets its ceiling'
    no_lid = run(fb, context(fixes={'rooms': [room_fix((5, 5), slab='floor', ceiling='none')]}))
    assert not any(c['poly'].contains(Point(5, 5)) for c in slab(no_lid)['ceilings'])


def test_a_room_fix_beside_a_room_and_in_a_fenced_area_and_nowhere() -> None:
    """R-6.3: the room containing the point; else the unfloored area containing it; else the room within 0.5 m; else,
    for "floor here", the fenced face containing it; else the fix is unmatched and changes nothing."""
    import shapely
    fence = [shapely.LineString([(10.0, 2.0), (14.0, 2.0), (14.0, 8.0), (10.0, 8.0)]).buffer(0.025, cap_style='flat', join_style='mitre')]
    fb = floor(walls=room(0, 0, 10, 10), spans=[DOOR], rails=fence)
    base = run(fb)
    fixes = {'rooms': [room_fix((5.0, -0.3), name='Hall'),           # 0.3 m outside the south wall: the room within 0.5 m
                       room_fix((30.0, 30.0), name='Nowhere'),       # nothing there
                       room_fix((12.0, 5.0), slab='floor')]}         # the fenced area with no door: its unfloored area
    r = run(fb, context(fixes=fixes))
    assert r['net']['more']['roomFixes'] == [{'fix': 0, 'matched': True}, {'fix': 1, 'matched': False}, {'fix': 2, 'matched': True}]
    assert r['net']['more']['staffNames'] == [(room_at(r, 5, 5)['id'], 'Hall')]
    assert not base['plate0'].contains(Point(12, 5)) and r['plate0'].contains(Point(12, 5)) and r['unfloored'] == []
    assert r['report']['dropped'] == [], 'floored now: no longer listed as a fenced area with no door'
    only_nowhere = run(fb, context(fixes={'rooms': [room_fix((30.0, 30.0), slab='none')]}))
    assert only_nowhere['plate0'].equals(base['plate0'])
    kind, what = FX.room_target(Point(12, 5), base['net']['spaces'], [], base['net']['more']['fenced'], 'floor')
    assert kind == 'fenced' and what.contains(Point(12, 5))
    assert FX.room_target(Point(12, 5), base['net']['spaces'], [], base['net']['more']['fenced'], 'auto') == (None, None)


def test_fix_points_and_report_rows_are_in_the_floors_own_sheet_frame() -> None:
    """A floor drawn 100 m to the east on its sheet (aligned onto the first floor by a shift of -100): its fixes are
    given, and its report rows come back, in its own drawing's metres."""
    fb = floor(walls=room(0, 0, 10, 10, gaps={'S': [(3.5, 6.4)]}) + [box(4.9, 3.0, 5.1, 9.8)])
    X = context(shift={'F1': (-100.0, 0.0)}, fixes={'rooms': [room_fix((105.0, 5.0), slab='none')],
                                                    'closings': [closing((103.5, 0.1), (106.4, 0.1))]})
    r = run(fb, X)
    assert r['net']['more']['closingFixes'] == [{'fix': 0, 'matched': True}] and r['net']['more']['roomFixes'] == [{'fix': 0, 'matched': True}]
    assert [c['kind'] for c in closings(r)] == ['staff'] and len(r['net']['spaces']) == 1
    assert r['report']['closings'][0]['a'] == [103.5, 0.1] and r['report']['closings'][0]['b'] == [106.4, 0.1]
    assert closings(r)[0]['a'] == pytest.approx((3.5, 0.1)), 'the network itself is in the build frame'
    hole = slab(r)['holes'][0]
    assert hole['what'] == 'no floor' and 100 < hole['at'][0] < 110 and all(100 <= x <= 110 for x, _y in hole['o'])
    gap = run(fb, context(shift={'F1': (-100.0, 0.0)}))
    row = gap['report']['unfloored'][0]
    assert 100 < row['at'][0] < 110 and all(103.4 <= p[0] <= 106.5 for p in row['mouth']) and all(100 <= x <= 110.1 for x, _y in row['o'])


def test_the_fixes_survive_a_re_export_with_two_centimetres_of_drift() -> None:
    """RA-13: the new fixes are points and lines, not item keys: the same drawing exported again, everything 2 cm off,
    matches all of them. A room with a doorway closing that staff removed ("Not a doorway") and then floored ("Floor
    here"), and an annex open to the east that staff closed with a line and named."""
    def plan(d):
        walls = room(0, 0, 10, 10, gaps={'S': [(4.4, 5.6)]}) + [box(10, 2, 13, 2.2), box(10, 5.8, 13, 6)]
        return floor(walls=[box(x0 + d, y0 + d, x1 + d, y1 + d) for x0, y0, x1, y1 in (g.bounds for g in walls)])
    fixes = {'closings': [closing((4.4, 0.1), (5.6, 0.1), 'none'), closing((13.0, 2.1), (13.0, 5.9))],
             'rooms': [room_fix((5.0, 5.0), slab='floor'), room_fix((11.5, 4.0), name='Annex')]}
    for d in (0.0, 0.02):
        r = run(plan(d), context(fixes=fixes))
        assert r['net']['more']['closingFixes'] == [{'fix': 0, 'matched': True}, {'fix': 1, 'matched': True}], d
        assert r['net']['more']['roomFixes'] == [{'fix': 0, 'matched': True}, {'fix': 1, 'matched': True}], d
        assert [c['kind'] for c in closings(r)] == ['staff'], 'the doorway closing is removed, the staff line is in'
        assert [(s['source'], round(s['poly'].area)) for s in r['net']['spaces']] == [('staff', 11)], d
        assert r['net']['more']['staffNames'] == [(r['net']['spaces'][0]['id'], 'Annex')]
        assert r['plate0'].contains(Point(5, 5)) and r['plate0'].contains(Point(11.5, 4)) and r['unfloored'] == [], d


# --------------------------------------------------------------------------------- through prepare_floors and build()
@pytest.fixture(scope='module')
def drawing(tmp_path_factory):
    d = tmp_path_factory.mktemp('r1rooms')
    return read_plan(rooms_dxf(d / 'rooms.dxf'), d / 'read')


def settings(rules=None, **fixes):
    s = plan_settings([SHA])
    s['layers'] = dict(ROOMS_LAYERS)
    s['options'].update(contracts.NEW_RULES if rules is None else rules)
    s['fixes'].update(fixes)
    return s


def source(drawing):
    return source_ctx(SHA, 'rooms.dxf', drawing['items'], drawing=drawing['drawing'], kind='dxf')


def crossing(drawing) -> list[dict]:
    """The two wall lines drawn across the doorway."""
    return [d for d in drawing['W']['items'] if d['t'] == 'LINE' and d['lay'] == 'A-WALL']


def ref(d, **more):
    return {'floor': 'F1', 'source': SHA, 'key': d['k'], 'sig': K.sig(d, 1.0), 'rsig': K.rsig(d, None, 1.0),
            'elementId': N.element_id(N.split_path(d['path'])), 'layer': d['lay'], 'note': '', **more}


def doorway_parts(res) -> list[dict]:
    """The wall parts that stand in the doorway (x 4.9 - 5.1, y 1.5 - 2.5 on the sheet)."""
    ox, oy = res['model']['offset']
    way = box(4.95 - ox, 1.7 - oy, 5.05 - ox, 2.3 - oy)
    return [p for p in res['model']['parts'] if p['kind'] in ('wall', 'single') and Polygon(p['o'], p['h']).intersects(way)]


def test_the_set_aside_lines_reach_the_network(drawing, scratch, fake_detector) -> None:
    """build/__init__.py: prepare_floors hands the wall network the lines staff set aside (read like the floor's own
    items), unless their record says the floor runs past them; nothing with the old rule."""
    from test_u3_helpers import build_ctx
    fake_detector({'F1': []})
    a, b = crossing(drawing)
    floors = prepare_floors(build_ctx(settings(setAside=[ref(a), ref(b)]), [source(drawing)], scratch / 'a'))
    aside = floors.X.floor_info['F1']['aside']
    assert floors.X.floor_info['F1']['shift'] == (0.0, 0.0)
    assert sorted(tuple(map(tuple, d['pts'])) for d in aside) == [((4.9, 1.5), (4.9, 2.5)), ((5.1, 1.5), (5.1, 2.5))]
    assert all(d['roles'] == frozenset({'wall'}) and d['cont'] for d in aside), 'metres, with roles and line types'
    assert not any(d.get('k') in (a['k'], b['k']) for d in floors[0]['items']), 'they are not among the items that are built'
    past = prepare_floors(build_ctx(settings(setAside=[ref(a, floorPast=True), ref(b)]), [source(drawing)], scratch / 'b'))
    assert [tuple(map(tuple, d['pts'])) for d in past.X.floor_info['F1']['aside']] == [((5.1, 1.5), (5.1, 2.5))]
    old = prepare_floors(build_ctx(settings(rules={}, setAside=[ref(a), ref(b)]), [source(drawing)], scratch / 'c'))
    assert old.X.floor_info['F1']['aside'] == []
    assert FX.bounding_aside([(a, [0]), (b, [1, 2])], [{'floorPast': False}, {}, {'floorPast': True}]) == [a]


def test_a_wall_drawn_across_a_doorway_set_aside(drawing, scratch, fake_detector) -> None:
    """RA-18 (unit) / R-2.6's last point: with the lines across it set aside, the two rooms stay two, the plate is
    unchanged, and no wall part stands in the doorway. With "the floor runs past it" the doorway is a door-sized gap
    between two wall ends, which the app closes as a doorway; "Not a doorway" then makes the two rooms one."""
    fake_detector({'F1': []})
    a, b = crossing(drawing)
    src = [source(drawing)]
    drawn, _ = run_build(settings(), src, scratch / 'a')
    assert len(doorway_parts(drawn)) == 1, 'the lines pair into a wall piece that stands in the doorway'
    assert [s['name'] for s in drawn['model']['spaces']] == ['WEST', 'EAST']
    aside, _ = run_build(settings(setAside=[ref(a), ref(b)]), src, scratch / 'b')
    assert doorway_parts(aside) == [], 'no wall part stands in the doorway'
    assert [(s['name'], s['names']) for s in aside['model']['spaces']] == [('WEST', ['WEST']), ('EAST', ['EAST'])]
    fl0, fl1 = drawn['report']['floors']['F1'], aside['report']['floors']['F1']
    assert fl1['slab']['plate'] == fl0['slab']['plate'] and fl1['rooms']['spaces'] == 2
    assert [r['matchedBy'] for r in aside['report']['fixes']['setAside']] == ['key', 'key']
    assert [c['kind'] for c in fl1['slab']['closings']] == ['doorway'], 'the gap between the wall ends is also noted'
    past, _ = run_build(settings(setAside=[ref(a, floorPast=True), ref(b, floorPast=True)]), src, scratch / 'c')
    fl2 = past['report']['floors']['F1']
    assert fl2['rooms']['spaces'] == 2 and [c['kind'] for c in fl2['slab']['closings']] == ['doorway']
    c = fl2['slab']['closings'][0]
    assert (c['a'], c['b'], c['width']) == ([5.0, 1.5], [5.0, 2.5], 1.0)
    one, _ = run_build(settings(setAside=[ref(a, floorPast=True), ref(b, floorPast=True)],
                                closings=[{'floor': 'F1', 'a': c['a'], 'b': c['b'], 'use': 'none'}]), src, scratch / 'd')
    fl3 = one['report']['floors']['F1']
    assert fl3['rooms']['spaces'] == 1 and fl3['slab']['closings'] == [] and one['report']['fixes']['closings'] == [{'fix': 0, 'matched': True}]
    assert fl3['rooms']['several'] == [{'space': 'F1-R001', 'names': ['WEST', 'EAST']}]
    assert fl3['slab']['plate'] == fl0['slab']['plate'], 'the floor was never lost'
    assert [r.get('space') for r in one['model']['rooms']] == ['F1-R001', 'F1-R001']


def test_the_fix_rows_and_a_staff_name_through_build(drawing, scratch, fake_detector) -> None:
    """R-6.3: the report gains fixes.closings / rooms / stairs rows { fix, matched }; R-3.3: a staff name is the room's
    own name, and in a room with no drawn name it also becomes a label at the room's label point."""
    fake_detector({'F1': []})
    src = [source(drawing)]
    s = settings(rooms=[{'floor': 'F1', 'at': [7.0, 3.0], 'name': 'Meeting room', 'slab': 'auto', 'ceiling': 'auto'},
                        {'floor': 'F9', 'at': [7.0, 3.0], 'name': 'Elsewhere', 'slab': 'auto', 'ceiling': 'auto'},
                        {'floor': 'F1', 'at': [50.0, 50.0], 'name': None, 'slab': 'none', 'ceiling': 'auto'}],
                 closings=[{'floor': 'F1', 'a': [0.0, 50.0], 'b': [1.0, 50.0], 'use': 'none'}])
    res, _ = run_build(s, src, scratch / 'a')
    assert res['report']['fixes']['rooms'] == [{'fix': 0, 'matched': True}, {'fix': 1, 'matched': False}, {'fix': 2, 'matched': False}]
    assert res['report']['fixes']['closings'] == [{'fix': 0, 'matched': False}] and res['report']['fixes']['stairs'] == []
    east = next(sp for sp in res['model']['spaces'] if 'EAST' in sp['names'])
    assert east['name'] == 'Meeting room' and east['names'] == ['EAST'], 'the drawn name keeps its label'
    assert [r['name'] for r in res['model']['rooms']] == ['WEST', 'EAST']
    # a room with no drawn name: the staff name becomes a label there
    d2 = scratch / 'unnamed'
    d2.mkdir()
    plan2 = read_plan(rooms_dxf(d2 / 'rooms.dxf', names=('WEST',)), d2 / 'read')
    res2, _ = run_build(settings(rooms=[{'floor': 'F1', 'at': [7.0, 3.0], 'name': 'Meeting room', 'slab': 'auto', 'ceiling': 'auto'}]),
                        [source(plan2)], scratch / 'b')
    rooms = res2['model']['rooms']
    assert [r['name'] for r in rooms] == ['WEST', 'Meeting room'] and rooms[1]['label'] == 'Meeting room'
    east2 = next(sp for sp in res2['model']['spaces'] if sp['name'] == 'Meeting room')
    assert rooms[1]['space'] == east2['id'] and east2['names'] == ['Meeting room'] and rooms[1]['area'] == east2['area']
    assert Polygon(east2['o'], east2['h']).contains(Point(rooms[1]['x'], rooms[1]['y']))
    assert res2['report']['floors']['F1']['rooms']['named'] == 2


# ------------------------------------------------------------------------------------------------------ the settings
def test_the_new_fixes_are_coerced_and_checked() -> None:
    s = plan_settings([SHA])
    s['fixes'].update(closings=[{'floor': 'F1', 'a': [0, 1], 'b': [2, 3]}],
                      rooms=[{'floor': 'F1', 'at': [1, 2], 'name': '  Bar  '}, {'floor': 'F1', 'at': [1, 2], 'name': '', 'slab': 'floor'}],
                      stairs=[{'floor': 'F1', 'at': [1, 2], 'bottom': [3, 4]}, {'floor': 'F1', 'at': [1, 2]}],
                      setAside=[{'floor': 'F1', 'key': 'x', 'floorPast': 1}, {'floor': 'F1', 'key': 'y'}])
    c = ST.coerce(s)
    assert c['fixes']['closings'] == [{'floor': 'F1', 'a': [0.0, 1.0], 'b': [2.0, 3.0], 'use': 'line'}]
    assert c['fixes']['rooms'] == [{'floor': 'F1', 'at': [1.0, 2.0], 'name': 'Bar', 'slab': 'auto', 'ceiling': 'auto'},
                                   {'floor': 'F1', 'at': [1.0, 2.0], 'name': None, 'slab': 'floor', 'ceiling': 'auto'}]
    assert c['fixes']['stairs'] == [{'floor': 'F1', 'at': [1.0, 2.0], 'bottom': [3.0, 4.0], 'use': 'auto'},
                                    {'floor': 'F1', 'at': [1.0, 2.0], 'bottom': None, 'use': 'auto'}]
    assert c['fixes']['setAside'] == [{'floor': 'F1', 'key': 'x', 'floorPast': True}, {'floor': 'F1', 'key': 'y'}]
    assert isinstance(c['fixes']['closings'][0]['a'][0], float) and 'closings' not in s['fixes']['closings'][0]
    assert s['fixes']['closings'] == [{'floor': 'F1', 'a': [0, 1], 'b': [2, 3]}], 'the settings given are never changed'
    for kind, bad in (('closings', {'floor': 'F1', 'a': [0, 1], 'b': [2, 3], 'use': 'wall'}),
                      ('rooms', {'floor': 'F1', 'at': [1, 2], 'slab': 'maybe'}), ('rooms', {'floor': 'F1', 'at': [1, 2], 'ceiling': 'off'}),
                      ('rooms', {'floor': 'F1', 'at': [1, 2], 'name': 12}), ('stairs', {'floor': 'F1', 'at': [1, 2], 'use': 'ramp'})):
        t = plan_settings([SHA])
        t['fixes'][kind] = [bad]
        with pytest.raises(BuildError) as e:
            ST.coerce(t)
        assert e.value.code == 'bad_settings', (kind, bad)


def test_the_options_and_the_ceiling_height() -> None:
    """R-1.2: a missing key is the old rule; the ceiling height is read only with the new rule."""
    old = ST.coerce(plan_settings([SHA]))
    assert {k: old['options'][k] for k in contracts.OLD_RULES} == contracts.OLD_RULES
    assert 'ceilingHeight' not in old['floors'][0] and old['fixes']['closings'] == [] and old['fixes']['rooms'] == []
    new = plan_settings([SHA], ceilingHeight=2)
    new['options'].update(contracts.NEW_RULES)
    c = ST.coerce(new)
    assert c['floors'][0]['ceilingHeight'] == 2.0 and isinstance(c['floors'][0]['ceilingHeight'], float)
    assert {k: c['options'][k] for k in contracts.NEW_RULES} == contracts.NEW_RULES
    for bad in ({'slabs': 'closed-rooms', 'ceilings': 'auto'}, {'slabs': 'closed-rooms', 'stairs': 'climb'}, {'slabs': 'rooms'}):
        t = plan_settings([SHA])
        t['options'].update(bad)
        with pytest.raises(BuildError):
            ST.coerce(t)


def test_the_proposal_writes_the_new_rules_and_carries_the_new_fixes() -> None:
    """R-1.3: every new draft gets the new rules; a recipe that carries the keys is kept as it is."""
    from walkthrough_builder import propose as P
    assert {k: P.OPTIONS[k] for k in contracts.NEW_RULES} == contracts.NEW_RULES
    spec = {'projectId': 'p', 'office': None, 'settings': None,
            'sources': [{'sha1': SHA, 'name': 'a.dwg', 'kind': 'dwg', 'path': 'x', 'units': None}]}
    dr = {'source': {'sha1': SHA, 'name': 'a.dwg'}, 'units': {'used': 'mm', 'verdict': 'agree'}, 'areas': [], 'blocks': [], 'layers': []}
    fresh = P.propose_settings(spec, [dr], {'layers': {}}, [], None)
    assert {k: fresh['options'][k] for k in contracts.NEW_RULES} == contracts.NEW_RULES
    assert fresh['fixes'] == {'setAside': [], 'openings': [], 'outlineEdges': [], 'closings': [], 'rooms': [], 'stairs': []}
    kept = {'options': dict(contracts.OLD_RULES), 'fixes': {'closings': [closing((0, 0), (1, 0))], 'rooms': [room_fix((1, 1), name='Bar')]}}
    again = P.propose_settings({**spec, 'settings': kept}, [dr], {'layers': {}}, [], None)
    assert {k: again['options'][k] for k in contracts.OLD_RULES} == contracts.OLD_RULES, 'a recipe that carries the keys is kept'
    assert again['fixes']['closings'] == kept['fixes']['closings'] and again['fixes']['rooms'] == kept['fixes']['rooms']
    before = {'options': {'plinth': 'off'}}                                   # a recipe of before the milestone: no key
    assert {k: P.propose_settings({**spec, 'settings': before}, [dr], {'layers': {}}, [], None)['options'][k]
            for k in contracts.NEW_RULES} == contracts.NEW_RULES
