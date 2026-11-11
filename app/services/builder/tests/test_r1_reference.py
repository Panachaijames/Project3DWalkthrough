"""R1: the reference building built from its drawings with the real rules, against what its definition says
(docs/rooms/ACCEPTANCE.md 2.5; tools/rooms/make-reference-building.py; docs/rooms/contract-issues/R1.md section 4).

The reference building holds one case of each of R1's rules: a doorway closing (a door-sized gap between two wall ends
in a 0.06 m partition), an unfloored area with a mouth (the garage's 2.9 m opening from a wall's end to a wall's side),
a room with two names, a name in no room, a terrace fenced by railings with a door onto it, an X void upstairs and an X
mark on the lowest floor. The frozen fixtures were made through the tracer's wiring from the building's definition;
this test builds the drawings through build() and compares R1's part with that definition, to the tolerances R1.md
section 4 explains (the 2 cm strips of the drawn lines; the opening's own band). The stairs are R2's contract test.
"""
from __future__ import annotations

import json

import pytest
from shapely.geometry import Point, Polygon, box
from shapely.ops import unary_union

import kit
from test_contracts import walk
from test_u3_helpers import run_build, write_and_check
from walkthrough_builder import contracts, oslock

HALL = Polygon([(0.2, 0.2), (6.9, 0.2), (6.9, 4.6), (6.97, 4.6), (6.97, 8.8), (0.2, 8.8)])
KITCHEN, GARAGE, LOUNGE = box(7.1, 0.2, 11.8, 4.4), box(7.03, 4.6, 11.8, 8.8), box(0.2, 0.2, 6.9, 8.8)
TERRACE = box(7.1, 0.1, 11.9, 4.5)
XBOX = {'ground': box(9.4, 0.5, 11.6, 2.5), 'upper': box(3.4, 0.8, 6.0, 2.8)}


@pytest.fixture(scope='module')
def built(reference_building, tmp_path_factory) -> dict:
    tmp = tmp_path_factory.mktemp('r1-reference')
    with oslock.hold():                                     # the door finder runs in this process (U-3.5)
        res, _logs = run_build(reference_building['settings'], reference_building['sources'], tmp / 'build', 'rooms-reference')
    return {'res': res, 'tmp': tmp, 'ref': reference_building}


def sheet(built, key, poly_or_points):
    """Model-frame rings -> the sheet (both plans share one frame: the offset)."""
    ox, oy = built['res']['model']['offset']
    return [(x + ox, y + oy) for x, y in poly_or_points]


def space(built, sid):
    s = next(x for x in built['res']['model']['spaces'] if x['id'] == sid)
    return s, Polygon(sheet(built, s['floor'], s['o']), [sheet(built, s['floor'], h) for h in s['h']])


def floor_report(built, key):
    return built['res']['report']['floors'][key]


def test_the_rooms_are_the_buildings(built) -> None:
    """The hall (closed by the doorway closing only), the kitchen, the lounge: the fixture's ids, names and areas."""
    fixture = json.loads((kit.FIXTURES / 'models' / 'rooms-reference.model.json').read_text(encoding='utf-8'))
    m = built['res']['model']
    assert [(s['id'], s['name'], s['names'], s['area'], s['source'], s['ceiling']) for s in m['spaces']] == \
        [(s['id'], s['name'], s['names'], s['area'], s['source'], s['ceiling']) for s in fixture['spaces']]
    for sid, truth in (('ground-R001', HALL), ('ground-R002', KITCHEN), ('upper-R001', LOUNGE)):
        _s, g = space(built, sid)
        assert g.symmetric_difference(truth).area < 0.35, sid
    assert {r['name']: r.get('space') for r in m['rooms']} == {
        'LIVING': 'ground-R001', 'DINING': 'ground-R001', 'KITCHEN': 'ground-R002', 'GARAGE': None, 'LOUNGE': 'upper-R001'}
    # R-3.4: a name alone in its room carries the room's area; two names in one room carry none
    assert {r['name']: r['area'] for r in m['rooms']} == {'LIVING': None, 'DINING': None, 'KITCHEN': 19.7, 'GARAGE': None, 'LOUNGE': 57.6}
    g = floor_report(built, 'ground')['rooms']
    assert g == {'spaces': 2, 'named': 2, 'shapes': 0, 'open': [{'name': 'GARAGE', 'at': [9.0, 6.6]}],
                 'several': [{'space': 'ground-R001', 'names': ['LIVING', 'DINING']}]}
    assert floor_report(built, 'upper')['rooms'] == {'spaces': 1, 'named': 1, 'shapes': 0, 'open': [], 'several': []}


def test_the_doorway_closing_and_the_garage(built) -> None:
    """R-2.6: the 1.2 m gap between two wall ends of the 0.06 m partition, which the door finder does not take, is closed
    as a doorway. R-2.5: the garage, open 2.9 m wide from a wall's end to a wall's side, has no floor and is an
    unfloored area whose mouth lies on the opening; its name stands in no room."""
    sl = floor_report(built, 'ground')['slab']
    assert sl['closings'] == [{'kind': 'doorway', 'a': [7.0, 5.6], 'b': [7.0, 6.8], 'width': 1.2}]
    assert len(sl['unfloored']) == 1
    u = sl['unfloored'][0]
    assert u['answered'] is False and u['kind'] == 'pocket' and u['area'] == pytest.approx(20.0, abs=0.8)
    area = Polygon(u['o'])
    assert area.symmetric_difference(GARAGE).area < 1.2 and area.contains(Point(u['at']))
    (ax, ay), (bx, by) = sorted(u['mouth'])
    assert (ax, bx) == pytest.approx((8.9, 11.8), abs=0.06) and 8.8 <= ay <= 9.0 and 8.8 <= by <= 9.0, 'the mouth lies on the opening'
    ox, oy = built['res']['model']['offset']
    slab = unary_union([Polygon(p['o'], p['h']) for p in built['res']['model']['parts'] if p['floor'] == 'ground' and p['kind'] == 'slab'])
    assert not slab.contains(Point(9.4 - ox, 6.7 - oy)) and slab.contains(Point(3.0 - ox, 6.0 - oy)) and slab.contains(Point(9.0 - ox, 2.0 - oy))
    assert [o['kind'] for o in built['res']['model']['openings']] == ['door', 'door', 'door'], 'no opening is invented'


def test_the_ring_the_terrace_and_the_plates(built) -> None:
    """R-4.1, R-4.2: the ground plate is the building less its garage; upstairs the lounge and the terrace fenced by
    railings, which a door opens onto: one plate, the terrace with no ceiling and no room."""
    g, u = floor_report(built, 'ground')['slab'], floor_report(built, 'upper')['slab']
    assert g['ring'] == pytest.approx(87.4, abs=0.8) and g['terraces'] == 0.0 and g['plate'] == g['ring']
    assert g['old'] == pytest.approx(g['plate'], abs=0.8), 'today\'s rule floors the hall too once the closing is its passage'
    assert u['ring'] == pytest.approx(63.9, abs=0.5) and u['terraces'] == pytest.approx(21.1, abs=0.8)
    assert u['plate'] == pytest.approx(85.0, abs=1.2) and u['unfloored'] == [] and u['dropped'] == [] and g['dropped'] == []
    m = built['res']['model']
    ox, oy = m['offset']
    upper = [Polygon(p['o'], p['h']) for p in m['parts'] if p['floor'] == 'upper' and p['kind'] == 'slab']
    assert len(upper) == 1 and upper[0].contains(Point(9.5 - ox, 2.3 - oy)) and upper[0].contains(Point(3 - ox, 6 - oy))
    lids = [Polygon(p['o'], p['h']) for p in m['parts'] if p['floor'] == 'upper' and p['kind'] == 'ceiling']
    assert len(lids) == 1 and lids[0].contains(Point(3 - ox, 6 - oy)) and not lids[0].contains(Point(9.5 - ox, 2.3 - oy))
    assert not any(Polygon(s['o'], s['h']).contains(Point(9.5 - ox, 2.3 - oy)) for s in m['spaces'] if s['floor'] == 'upper')
    assert sum(1 for p in m['parts'] if p['floor'] == 'upper' and p['kind'] == 'railing') >= 1


def test_the_x_marks(built) -> None:
    """R-4.3: the upper floor's X is a void of 5.2 m2, cut; the lowest floor's X of 4.4 m2 is a void mark that is not
    cut there and is reported; the ground ceiling is open under the upper void."""
    g, u = floor_report(built, 'ground')['slab']['holes'], floor_report(built, 'upper')['slab']['holes']
    assert [(h['what'], h['area'], h['cut'], h.get('why')) for h in g] == [('void', 4.4, False, 'the lowest floor')]
    assert Polygon(g[0]['o']).equals(XBOX['ground']) and g[0]['at'] == [10.5, 1.5]
    voids = [h for h in u if h['what'] == 'void']
    assert [(h['area'], h['cut']) for h in voids] == [(5.2, True)] and Polygon(voids[0]['o']).equals(XBOX['upper'])
    m = built['res']['model']
    ox, oy = m['offset']
    assert m['voids']['ground'] == [] and [v for v in m['voids']['upper'] if v['what'] == 'void'] == [
        {'what': 'void', 'x': round(4.7 - ox, 3), 'y': round(1.8 - oy, 3), 'area': 5.2}]
    upper = unary_union([Polygon(p['o'], p['h']) for p in m['parts'] if p['floor'] == 'upper' and p['kind'] == 'slab'])
    lid = unary_union([Polygon(p['o'], p['h']) for p in m['parts'] if p['floor'] == 'ground' and p['kind'] == 'ceiling'])
    p = Point(4.7 - ox, 1.8 - oy)
    assert not upper.contains(p) and not lid.contains(p), 'a double-height space is open up to the upper ceiling'
    assert lid.contains(Point(10.5 - ox, 1.5 - oy)), 'the kitchen keeps its ceiling under its own X mark'


def test_the_result_has_the_typed_shape_and_passes_the_apis_checks(built) -> None:
    res = built['res']
    assert walk({k: v for k, v in res.items() if not k.startswith('_')}, contracts.BuildResult) == []
    for key, fl in res['report']['floors'].items():
        assert walk(fl, contracts.FloorUploadReportRooms) == [], key
    ref = built['ref']
    _written, problems = write_and_check(res, ref['settings'], ref['sources'], built['tmp'] / 'outputs', 'rooms-reference')
    assert problems == []
