"""R1: the rooms, plates, holes, names and ceilings of the five drawings (docs/rooms/ACCEPTANCE.md RA-3, RA-4, RA-5,
RA-6's builder part, RA-7, RA-8, RA-18; DESIGN R-14).

The five new-rule builds are the session's (conftest.py: `bank_rooms`, `house_rooms`, `suite_rooms`, `tower_rooms`,
`suite_revit_rooms`: read only). Tests that run a rule again on a floor (another disc, today's plate against the new
one, a door undone) take the floors after prepare_floors and floor_walls (`floors`: the door finder runs, so they are
marked `heavy`); every door undone in turn is marked `acceptance` as well (84 s).

Coordinates. ACCEPTANCE gives points in sheet metres after alignment (the build frame: for the house both plans in the
ground plan's frame): `aligned()` turns one into the model frame. The answer keys and the report's rows are in each
floor's own sheet frame: `own()`.

Two assertions waited for a decision (docs/rooms/contract-issues/R1.md), settled by the main session on 11 Nov and put in
by RI (docs/rooms/contract-issues/RI.md): D-1, the bank counts 23 labels (test_ra7_the_banks_labels_as_built pins them;
the strict xfail for 18 is gone); D-2, the probe ground-034 is out of RA-6's must list and is checked as outdoors with no
floor on either side (test_ra6_ground_034_is_outdoors_with_no_floor, in place of its two strict xfails).
The stairs are R2's: nothing here depends on which stairs climb (a well, today's void or neither over a stair).
"""
from __future__ import annotations

import json
import math

import pytest
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union

import kit
from test_contracts import walk
from test_r1_helpers import floors_of, undone
from walkthrough_builder import contracts
from walkthrough_builder.build import network as NW
from walkthrough_builder.build.model import _max_problem

KEYS = kit.ROOMS_FIXTURES / 'keys'
#: ACCEPTANCE RA-4: plate0 per floor: (must at least, must at most, should from, should to); None: today's plate
PLATE = {('bank', 'L1'): (None, 243, 234, 241), ('bank', 'L2'): (None, 307, 293, 303),
         ('house', 'ground'): (483, 545, 495, 530), ('house', 'upper'): (431, 497, 435, 460),
         ('tower', 'L29'): (814, 885, 840, 875), ('tower', 'L30'): (704, 772, 725, 765),
         ('suite', 'suite'): (400, 660, 460, 480), ('suite-revit', 'L1'): (260, 284, 262, 280)}   # old suite: R1.md D-3
TODAY = {('bank', 'L1'): 235.3, ('bank', 'L2'): 295.4}
MUST = ('bank', 'house', 'suite', 'tower')               # the new suite's rows are shoulds, by position


def load(p):
    return json.loads(p.read_text(encoding='utf-8'))


def model(b):
    return b['res']['model']


def report(b, key):
    return b['res']['report']['floors'][key]


def aligned(b, p):
    """A point given in sheet metres after alignment (ACCEPTANCE's frame) -> the model frame."""
    ox, oy = model(b)['offset']
    return (p[0] - ox, p[1] - oy)


def own(b, key, p):
    """A point of a floor's own sheet (an answer key, a report row) -> the model frame."""
    tx, ty = b['res']['floors_frame'][key]['toSheet']
    return (p[0] - tx, p[1] - ty)


def parts(b, key, kind):
    return [Polygon(p['o'], p['h']) for p in model(b)['parts'] if p['floor'] == key and p['kind'] == kind]


def plate(b, key):
    return unary_union(parts(b, key, 'slab'))


def spaces(b, key):
    return [(s, Polygon(s['o'], s['h'])) for s in model(b)['spaces'] if s['floor'] == key]


def space_at(b, key, p):
    """The room that contains a model-frame point, or None."""
    return next((s for s, g in spaces(b, key) if g.contains(Point(p))), None)


def hole_bounds(b, key, row):
    """A hole row's outline in the aligned frame (min x, min y, max x, max y)."""
    ox, oy = model(b)['offset']
    return Polygon([(x + ox, y + oy) for x, y in (own(b, key, p) for p in row['o'])]).bounds


def cut_holes(b, key, what=None):
    return [h for h in report(b, key)['slab']['holes'] if h['cut'] and (what is None or h['what'] == what)]


@pytest.fixture(scope='module')
def builds(bank_rooms, house_rooms, suite_rooms, tower_rooms, suite_revit_rooms) -> dict:
    return {'bank': bank_rooms, 'house': house_rooms, 'suite': suite_rooms, 'tower': tower_rooms, 'suite-revit': suite_revit_rooms}


@pytest.fixture(scope='module')
def floors(ref, tmp_path_factory):
    """name -> the drawing's floors after prepare_floors and floor_walls (made once; the calling test is `heavy`: it
    holds the machine run lock while the door finder runs)."""
    cache: dict[str, dict] = {}

    def get(name: str) -> dict:
        if name not in cache:
            cache[name] = floors_of(name, ref, tmp_path_factory.mktemp(f'r1-floors-{name.replace("-", "_")}'))
        return cache[name]
    return get


def pass1(fb, X):
    net = NW.network_of(fb, X.settings['fixes'], X)
    plate0, unfloored, rep = NW.plate_of(fb, net, X.settings['fixes'], X)
    return net, plate0, unfloored, rep


# ------------------------------------------------------------------------------------------------------ RA-3: rooms
def test_the_report_and_the_model_have_the_new_keys(builds) -> None:
    """RA-3: the report gives, per floor, the rooms, the named ones, the enclosed shapes left out, the names in no
    room and the rooms with several names; RA-15: every new-rule model has `stairways` and `spaces`."""
    for name, b in builds.items():
        m = model(b)
        assert 'stairways' in m and 'spaces' in m, name
        assert walk({k: v for k, v in b['res'].items() if not k.startswith('_')}, contracts.BuildResult) == [], name
        ids = [s['id'] for s in m['spaces']]
        assert len(ids) == len(set(ids)), name
        for key, fl in b['res']['report']['floors'].items():
            assert walk(fl, contracts.FloorUploadReportRooms) == [], (name, key)
            rm = fl['rooms']
            mine = [s for s in m['spaces'] if s['floor'] == key]
            assert rm['spaces'] == len(mine) and rm['named'] == sum(1 for s in mine if s['name']), (name, key)
            assert all(s['id'].startswith(f'{key}-R') and s['area'] >= 1.0 and s['source'] in ('network', 'outline', 'staff')
                       and s['ceiling'] is True for s in mine), (name, key)
            assert all(r.get('space') in {s['id'] for s in mine} for r in m['rooms'] if r['floor'] == key and 'space' in r)
            assert fl['platesDropped'] == [], 'the plate-dropped rows are the old rule\'s'
        assert set(b['res']['report']['fixes']) == {'setAside', 'openings', 'outlineEdges', 'closings', 'rooms', 'stairs'}
        assert b['res']['report']['fixes']['closings'] == [] and b['res']['report']['fixes']['rooms'] == []
        facts = b['res']['replay']['facts']
        assert facts['ceilings'] is True and set(facts['rooms']) == {f['key'] for f in m['floors']}


def test_ra3_the_banks_names_stand_in_their_rooms(builds) -> None:
    """RA-3 / RA-7 (must): each of the 7 + 11 names' own point lies in a room, and that room carries the name."""
    b = builds['bank']
    key = load(KEYS / 'bank.json')['floors']
    assert {k: len(v) for k, v in key.items()} == {'L1': 7, 'L2': 11}
    for fl, rows in key.items():
        for row in rows:
            s = space_at(b, fl, own(b, fl, row['at']))
            assert s is not None and row['name'] in s['names'], (fl, row['name'])
            # the label stays where the designer wrote it
            at = own(b, fl, row['at'])
            assert any(r['floor'] == fl and r['label'] == row['label'] and math.dist((r['x'], r['y']), at) < 2e-3
                       and r.get('space') == s['id'] for r in model(b)['rooms']), (fl, row['label'])
    assert report(b, 'L1')['rooms']['open'] == [] and report(b, 'L2')['rooms']['open'] == []


def test_ra3_the_houses_living_room_and_its_east_building(builds) -> None:
    """RA-3 (must): the glass-walled living room is one room that contains (26.2, 11.1) and is 60 - 90 m2; every room
    of the small east building is a room (fixtures/rooms/keys/house.json: one point each, each in a room of its own)."""
    b = builds['house']
    rows = load(KEYS / 'house.json')['floors']['ground']
    assert len(rows) == 5
    got = []
    for row in rows:
        s = space_at(b, 'ground', own(b, 'ground', row['at']))
        assert s is not None, row['what']
        assert row['area'][0] <= s['area'] <= row['area'][1], (row['what'], s['area'])
        got.append(s['id'])
    assert len(set(got)) == 5, 'each point stands in a room of its own'
    living = space_at(b, 'ground', aligned(b, (26.2, 11.1)))
    assert living is not None and 60 <= living['area'] <= 90 and living['id'] == got[-1]


def test_ra3_the_old_suites_names_belong_to_rooms(builds) -> None:
    """RA-3 (must): at least 13 of its 16 names belong to a room; the others are flagged room-open. RA-7's pairs:
    Steam 3m2 stays in its 2.8 m2 room; Foyer 10m2 and Massage Room 9m2 do not both go to one room; a name carrying
    its area gives the name and keeps the area in its label."""
    b = builds['suite']
    rooms = model(b)['rooms']
    assert len(rooms) == 16
    placed = [r for r in rooms if r.get('space')]
    opened = report(b, 'suite')['rooms']['open']
    assert len(placed) >= 13 and len(placed) + len([o for o in opened if 'space' not in o]) == 16
    by = {r['name']: r for r in rooms}
    area = {s['id']: s['area'] for s in model(b)['spaces']}
    assert area[by['Steam']['space']] == pytest.approx(2.8, abs=0.15) and by['Steam']['area'] == 3.0
    assert by['Foyer']['space'] != by['Massage Room']['space']
    assert (by['Bar']['label'], by['Bar']['area']) == ('Bar · 7,6m2', 7.6)
    assert all('m2' not in r['name'] for r in rooms), 'no name keeps a trailing area'
    assert {r['name'] for r in rooms} >= {'Bar', 'Foyer', 'Kitchen', 'Sauna', 'Steam', 'Powder', 'Master Bedroom'}


def test_ra3_ra7_names_that_are_tags_are_dropped(builds) -> None:
    """RA-7: BAR, BOH. are names (the new suite); D1, ST-05, R-01 are not (the house)."""
    house = builds['house']['res']['report']['summary']['floors']
    assert house['ground']['notRoomNames'] == ['R-01', 'ST-05'] and house['upper']['notRoomNames'] == ['ST-02']
    assert model(builds['house'])['rooms'] == []
    names = [r['name'] for r in model(builds['suite-revit'])['rooms']]
    assert 'BAR' in names and 'BOH.' in names and all(r.get('space') for r in model(builds['suite-revit'])['rooms'])


def test_ra3_the_new_suites_furniture_is_not_rooms(builds) -> None:
    """RA-3 (should, by position): the bed at (5.38, 5.84) and the sofa corner at (13.61, 8.34) are not rooms of their
    own; the report counts enclosed shapes."""
    b = builds['suite-revit']
    bed, sofa = space_at(b, 'L1', aligned(b, (5.38, 5.84))), space_at(b, 'L1', aligned(b, (13.61, 8.34)))
    assert bed is not None and bed['area'] > 30 and 'MASTER BEDROOM' in bed['names']
    assert sofa is not None and sofa['area'] > 30
    assert report(b, 'L1')['rooms']['shapes'] >= 2


def test_ra3_the_gate_line_as_it_stands(builds) -> None:
    """RA-3: "every room closed on both floors with no staff fix", for the bank and for the house. The bank: no
    unfloored area, no name in no room, no closing of the app's. The house: its rooms close with 2 doorway closings and
    7 bridges; two areas beside the walls are asked about (the terrace strip south of the living room; the loop
    upstairs, RA-4)."""
    bank, house = builds['bank'], builds['house']
    for key in ('L1', 'L2'):
        fl = report(bank, key)
        assert fl['slab']['unfloored'] == [] and fl['slab']['closings'] == [] and fl['rooms']['open'] == [], key
    assert [report(bank, k)['rooms']['spaces'] for k in ('L1', 'L2')] == [15, 14]
    assert [report(house, k)['rooms']['spaces'] for k in ('ground', 'upper')] == [22, 24]
    assert [len(report(house, k)['slab']['unfloored']) for k in ('ground', 'upper')] == [1, 1]
    assert [report(house, k)['rooms']['open'] for k in ('ground', 'upper')] == [[], []]


# ------------------------------------------------------------------------------------------------- RA-4: slab areas
def test_ra4_plate0_is_inside_its_bounds(builds) -> None:
    """RA-4 (must): plate0 per floor (report `slab.plate`) is at least 95 % of the trial's (the bank: today's plate) and
    at most a 1.5 m round closing of the network plus 2 %. The new suite's row is a should."""
    for (name, key), (low, high, _a, _b) in PLATE.items():
        got = report(builds[name], key)['slab']['plate']
        low = TODAY[(name, key)] if low is None else low
        if name in MUST:
            assert low <= got <= high, (name, key, got)
        sl = report(builds[name], key)['slab']
        assert sl['plate'] >= sl['ring'] - 0.11 and sl['plate'] >= sl['old'] - 0.11, (name, key)


@pytest.mark.heavy
@pytest.mark.parametrize('name', ['bank', 'house', 'suite', 'tower', 'suite-revit'])
def test_ra4_plate0_is_never_smaller_than_todays(name, floors, ref_r0) -> None:
    """RA-4 / R-4.1 (must, all eight floors): the area of today's plate (the old rule, the same drawing) outside plate0
    is under 0.5 m2. It holds by construction and guards the union."""
    d = floors(name)
    for fb in d['fbs']:
        _net, plate0, _unfloored, rep = pass1(fb, d['X'])
        assert fb['old_plate'].difference(plate0).area < 0.5, (name, fb['key'])
        assert rep['plate'] == round(plate0.area, 1)


def test_ra4_the_houses_upper_loop_gets_no_floor(builds) -> None:
    """RA-4 (must): the point (26.7, 13.0) is not on the plate, and a slab-gap flag covers it."""
    b = builds['house']
    p = aligned(b, (26.7, 13.0))
    assert not plate(b, 'upper').contains(Point(p))
    rows = report(b, 'upper')['slab']['unfloored']
    assert any(Polygon([own(b, 'upper', q) for q in u['o']]).contains(Point(p)) and u['area'] >= 4 and u['answered'] is False
               for u in rows)
    assert space_at(b, 'upper', p) is None


def test_ra4_the_old_suites_terrace(builds) -> None:
    """RA-4: the terrace by the rule of R-4.2, measured by R1's first task: 53.2 m2, within 3 m2 (R1.md D-3). The
    fenced areas with no door are listed, not floored."""
    sl = report(builds['suite'], 'suite')['slab']
    assert sl['terraces'] == pytest.approx(53.2, abs=3.0)
    assert sum(1 for d in sl['dropped'] if d['why'] == 'no door or passage opens onto it') == 2


def test_ra4_the_slab_parts_pass_the_max_checks_and_nothing_is_lost_silently(builds) -> None:
    """RA-4 (must): no hole within 0.5 mm of its outline or of another hole; every piece of 4 m2 or less is in the
    report's `slab.dropped` with its reason."""
    for name, b in builds.items():
        for p in model(b)['parts']:
            if p['kind'] in ('slab', 'ceiling'):
                assert _max_problem(p) is None, (name, p['floor'], p['kind'])
        for key, fl in b['res']['report']['floors'].items():
            assert all(d['why'] and d['area'] > 0 and len(d['at']) == 2 for d in fl['slab']['dropped']), (name, key)
            assert all(g.area > 4.0 for g in parts(b, key, 'slab')), (name, key)
            assert plate(b, key).area == pytest.approx(sum(g.area for g in parts(b, key, 'slab')), abs=0.01), 'no two slab parts overlap'


# ------------------------------------------------------------------------------------------------------ RA-5: holes
def test_ra5_the_houses_holes(builds) -> None:
    b = builds['house']
    voids = cut_holes(b, 'upper', 'void')
    assert len(voids) == 2, 'two X-marked holes'
    living, hall = sorted(voids, key=lambda h: hole_bounds(b, 'upper', h)[1])
    assert living['area'] == pytest.approx(26.1, abs=1.0) and hall['area'] == pytest.approx(16.6, abs=1.0)
    assert hole_bounds(b, 'upper', living) == pytest.approx((19.45, 14.51, 24.95, 19.26), abs=0.06)
    assert hole_bounds(b, 'upper', hall) == pytest.approx((19.50, 21.41, 24.95, 24.46), abs=0.06)
    assert 24.93 <= hole_bounds(b, 'upper', hall)[2] <= 24.96, 'its east edge is the top riser'
    # the service stair ST-02 keeps today's void while it stays as lines
    assert any(h['area'] == pytest.approx(3.9, abs=0.5) for h in cut_holes(b, 'upper', 'stair'))
    # the duct and the three roof slots are listed, not cut
    marks = [h for h in report(b, 'upper')['slab']['holes'] if h['what'] == 'X mark']
    assert len(marks) == 4 and all(not h['cut'] and h['why'] for h in marks)
    assert any(h['area'] == pytest.approx(0.84, abs=0.02) for h in marks)
    # the lowest floor: no hole; its three small X's are reported
    ground = report(b, 'ground')['slab']['holes']
    assert [h['cut'] for h in ground] == [False, False, False] and all(h['area'] < 0.8 for h in ground)
    assert model(b)['voids']['ground'] == [] and all(p['plinth'] for p in model(b)['parts'] if p['floor'] == 'ground' and p['kind'] == 'slab')


def test_ra5_the_banks_lift_shaft_and_its_grid(builds) -> None:
    """RA-5 (must): the lift shaft (the X of 1.4 x 1.4 m and the lift-door cell, merged) is cut on both floors, 1.9 -
    3.4 m2, within x -3.43 .. -1.63, y -8.58 .. -6.83. The grid lines cut nothing."""
    b = builds['bank']
    for key in ('L1', 'L2'):
        lifts = cut_holes(b, key, 'lift shaft')
        assert len(lifts) == 1 and 1.9 <= lifts[0]['area'] <= 3.4, key
        x0, y0, x1, y1 = hole_bounds(b, key, lifts[0])
        # (the box is Level 2's lift-door cell; Level 1's reaches y -6.807: its wall is drawn 2.3 cm further north)
        assert -3.48 <= x0 and x1 <= -1.58 and -8.63 <= y0 and y1 <= -6.78, key
        assert {h['what'] for h in cut_holes(b, key)} <= {'lift shaft', 'stair', 'stair well'}, 'nothing else is cut'
        assert not any(h['what'] in ('void', 'shaft', 'X mark') for h in report(b, key)['slab']['holes']), key
    assert cut_holes(b, 'L1') == cut_holes(b, 'L1', 'lift shaft'), 'the lowest floor: the shaft only'


def test_ra5_the_towers_shafts(builds) -> None:
    """RA-5 (must): four shafts of 2.7 - 3.6 m2 on each floor; L30 keeps today's void over stair B (17 m2)."""
    b = builds['tower']
    for key in ('L29', 'L30'):
        shafts = [h for h in cut_holes(b, key) if h['what'] in ('shaft', 'lift shaft')]
        assert len(shafts) == 4 and all(2.7 <= h['area'] <= 3.6 for h in shafts), (key, [h['area'] for h in shafts])
        assert not any(h['what'] == 'void' for h in report(b, key)['slab']['holes'])
    assert any(h['area'] == pytest.approx(17.0, abs=1.0) for h in cut_holes(b, 'L30', 'stair'))
    assert not any(h['what'] in ('stair', 'stair well') for h in cut_holes(b, 'L29')), 'none on the lowest floor'


def test_ra5_the_suites_have_no_x_hole_and_every_hole_is_a_void_record(builds) -> None:
    """RA-5 (must): no X hole on either suite (the old suite's rectangle with a divider cuts nothing); each hole is a
    `voids[floor]` record with its `what`; holes under 0.5 m2 are reported, not cut; no hole of over 60 m2 or over
    30 % of the plate is cut by itself."""
    for name in ('suite', 'suite-revit'):
        b = builds[name]
        for key in b['res']['report']['floors']:
            assert cut_holes(b, key) == [] and model(b)['voids'][key] == [], (name, key)
    for name, b in builds.items():
        for key, fl in b['res']['report']['floors'].items():
            cut = [h for h in fl['slab']['holes'] if h['cut']]
            assert [(v['what'], v['area']) for v in model(b)['voids'][key]] == [(h['what'], h['area']) for h in cut], (name, key)
            assert all(h['area'] >= 0.5 or h['what'] == 'stair well' for h in cut), (name, key)
            assert all(h['what'] in ('stair well', 'stair', 'lift shaft', 'shaft', 'void', 'no floor') for h in cut)
            assert all(h['area'] <= 60 and h['area'] <= 0.3 * fl['slab']['plate'] for h in cut if h['what'] in ('void', 'shaft')), (name, key)
            assert all(set(h) >= {'what', 'area', 'at', 'o', 'cut'} and (h['cut'] or h.get('why')) for h in fl['slab']['holes'])
            for h in cut:
                at = own(b, key, h['at'])
                assert not plate(b, key).contains(Point(at)), (name, key, h['what'])


# --------------------------------------------------------------------------------------------- RA-6: the missing floors
#: R1.md D-2 (decided 11 Nov): out of RA-6's must list, checked as outdoors by test_ra6_ground_034_is_outdoors_with_no_floor
OUTDOORS = ('house', 'ground-034')


def probe_rows():
    out = []
    for name, d in load(KEYS / 'probes.json')['drawings'].items():
        for p in d['probes']:
            if (name, p['id9Nov']) == OUTDOORS:
                continue
            for side in p['sides']:
                out.append(pytest.param(name, p, side, id=f'{name}-{p["id9Nov"].replace(" ", "_")}{"+" if side > 0 else "-"}'))
    return out


@pytest.mark.parametrize('name, probe, side', probe_rows())
def test_ra6_the_probes_of_9_nov_stand_on_the_plate(name, probe, side, builds) -> None:
    """RA-6 (must; the new suite: should, reported by test_the_shoulds): the plate holds a point 0.4 - 0.9 m in front of
    the opening, on the side that had no floor. RA-3 (the tower, the house's upper floor): a room lies behind it."""
    b = builds[name]
    key = probe['floor']
    at = lambda d: own(b, key, (probe['at'][0] + side * d * probe['n'][0], probe['at'][1] + side * d * probe['n'][1]))  # noqa: E731
    on_plate = [plate(b, key).contains(Point(at(d))) for d in (0.4, 0.5, 0.6, 0.7, 0.8, 0.9)]
    if name in MUST:
        assert any(on_plate), f'no floor 0.4 - 0.9 m in front of {probe["id9Nov"]}'
    if name == 'tower' or (name, key) == ('house', 'upper'):
        assert any(space_at(b, key, at(d)) is not None for d in (0.6, 0.9, 1.2, 1.5, 2.0, 2.5)), 'a room behind the opening'


def test_ra6_ground_034_is_outdoors_with_no_floor(builds) -> None:
    """R1.md D-2 (decided 11 Nov, RA-6): ground-034 is a garden gate in a free-standing wall, out of RA-6's must list; it
    stays in the walk report as "outdoors, no floor". So on both sides: no plate 0.4 - 0.9 m in front of it and no room
    behind it (nothing drawn encloses either side). The day a rule floors it, this says so."""
    name, pid = OUTDOORS
    b = builds[name]
    probe = next(p for p in load(KEYS / 'probes.json')['drawings'][name]['probes'] if p['id9Nov'] == pid)
    key = probe['floor']
    assert sorted(probe['sides']) == [-1, 1]
    for side in probe['sides']:
        at = lambda d: own(b, key, (probe['at'][0] + side * d * probe['n'][0], probe['at'][1] + side * d * probe['n'][1]))  # noqa: E731,B023
        assert not any(plate(b, key).contains(Point(at(d))) for d in (0.4, 0.5, 0.6, 0.7, 0.8, 0.9)), (pid, side, 'floor')
        assert all(space_at(b, key, at(d)) is None for d in (0.6, 0.9, 1.2, 1.5, 2.0, 2.5)), (pid, side, 'a room')


# -------------------------------------------------------------------------------------------------------- RA-7: names
def test_ra7_the_banks_named_pairs(builds) -> None:
    """RA-7: TOILET 3.2 stays in the 3.1 m2 room it stands in; FEMALE TOILET 6.4 stays in its 3.3 m2 face and the F/C
    room keeps one name; the hall with CSO 5PAX, WAITING AREA and FOR 1 PAX shows three labels and one room-names row."""
    b = builds['bank']
    area = {s['id']: s for s in model(b)['spaces']}
    rooms = model(b)['rooms']
    toilet = next(r for r in rooms if r['label'] == 'TOILET · 3.2 m²')
    assert area[toilet['space']]['area'] == pytest.approx(3.1, abs=0.15) and toilet['area'] == 3.2
    female = next(r for r in rooms if r['name'] == 'FEMALE TOILET')
    assert area[female['space']]['area'] == pytest.approx(3.3, abs=0.15) and area[female['space']]['names'] == ['FEMALE TOILET']
    fc = next(r for r in rooms if r['floor'] == 'L2' and r['name'] == 'F/C')
    assert area[fc['space']]['names'] == ['F/C']
    hall = next(s for s in model(b)['spaces'] if 'WAITING AREA' in s['names'])
    assert sorted(hall['names']) == ['CSO 5PAX', 'FOR 1 PAX', 'WAITING AREA'] and hall['area'] > 100
    assert [r for r in report(b, 'L2')['rooms']['several'] if r['space'] == hall['id']] == [
        {'space': hall['id'], 'names': hall['names']}]
    assert sum(1 for r in rooms if r.get('space') == hall['id']) == 3, 'three labels'


def test_ra7_the_banks_labels_as_built(builds) -> None:
    """RA-7 as decided on 11 Nov (R1.md D-1): 23 labels, the 18 names of the key and the five short ones the room-name
    layer carries (ATM three times, BA, BE)."""
    rooms = model(builds['bank'])['rooms']
    assert len(rooms) == 23
    key = load(KEYS / 'bank.json')['floors']
    old = sorted(r['label'] for rows in key.values() for r in rows)
    new = sorted(r['label'] for r in rooms)
    assert sorted(set(new) - set(old)) == ['ATM', 'BA', 'BE'] and [n for n in new if n == 'ATM'] == ['ATM'] * 3
    assert all(r.get('space') for r in rooms), 'every one of them belongs to a room'


# ----------------------------------------------------------------------------------------------------- RA-8: ceilings
HEIGHTS = {('bank', 'L1'): 3.0, ('bank', 'L2'): 3.0, ('house', 'ground'): 3.0, ('house', 'upper'): 2.9,
           ('tower', 'L29'): 3.0, ('tower', 'L30'): 3.0, ('suite', 'suite'): 2.7, ('suite-revit', 'L1'): 2.7}


def test_ra8_the_ceiling_heights(builds) -> None:
    """RA-8 (must): the house 3.00 m above +0.90 and 2.90 m above +4.80 (typed); the others the default rule (3.00 m;
    the two suites 2.70 m). Every ceiling is 2 cm thick, keeps its height, and lies at least 2 cm under the slab above."""
    for (name, key), h in HEIGHTS.items():
        m = model(builds[name])
        mine = [p for p in m['parts'] if p['floor'] == key and p['kind'] == 'ceiling']
        assert mine, (name, key)
        assert all((p['z1'], p['z0'], p['follow'], p['label']) == (h, round(h - 0.02, 3), False, 'ceiling') for p in mine), (name, key)
        fl = m['floors']
        i = next(k for k, f in enumerate(fl) if f['key'] == key)
        if i + 1 < len(fl):
            under = fl[i + 1]['level'] - fl[i]['level'] - fl[i + 1]['slabThickness']
            assert h <= under - 0.02 + 1e-9, (name, key)


def test_ra8_every_room_has_a_ceiling_over_it(builds) -> None:
    """RA-8 (must): every room has a ceiling part over it, except where the floor above has a hole and where a stair
    needs headroom; no two ceiling parts overlap; one ceiling piece per piece of plate, less the holes above: the
    house's upper floor has no more ceiling pieces than plate pieces."""
    for name, b in builds.items():
        m = model(b)
        keys = [f['key'] for f in m['floors']]
        for i, key in enumerate(keys):
            lids = parts(b, key, 'ceiling')
            lid = unary_union(lids)
            assert lid.area == pytest.approx(sum(g.area for g in lids), abs=0.01), (name, key, 'no two ceiling parts overlap')
            above = keys[i + 1] if i + 1 < len(keys) else None
            holes_above = [Polygon([own(b, above, q) for q in h['o']]) for h in cut_holes(b, above)] if above else []
            treads = [Polygon(p['o'], p['h']) for p in m['parts'] if p['floor'] == key and p['kind'] in ('tread', 'landing')]
            shafts = [Polygon([own(b, key, q) for q in h['o']]) for h in cut_holes(b, key) if h['what'] in ('shaft', 'lift shaft')]
            open_above = unary_union(holes_above + treads + shafts).buffer(0.1) if holes_above or treads or shafts else None
            for s, g in spaces(b, key):
                room = g if open_above is None else g.difference(open_above)
                if room.area < 0.5:
                    continue
                missing = room.difference(lid.buffer(0.02)).area
                assert missing < 0.05 * room.area + 0.3, (name, key, s['id'], round(missing, 2))
    house = builds['house']
    assert len(parts(house, 'upper', 'ceiling')) <= len(parts(house, 'upper', 'slab'))


def test_ra8_no_ceiling_under_a_void_or_over_a_terrace(builds) -> None:
    """RA-8 (must): no ceiling over the house's ground-floor living room where the upper floor's X void is, and none
    over the terraces (the old suite's)."""
    house = builds['house']
    p = aligned(house, (22.2, 16.9))                         # under the middle of the double-height void
    assert not any(g.contains(Point(p)) for g in parts(house, 'ground', 'ceiling'))
    assert any(g.contains(Point(aligned(house, (28.0, 11.1)))) for g in parts(house, 'ground', 'ceiling')), 'the rest of the room has one'
    assert not plate(house, 'upper').contains(Point(p)) and plate(house, 'ground').contains(Point(p))
    suite = builds['suite']
    sl = report(suite, 'suite')['slab']
    lid, floor_area = sum(g.area for g in parts(suite, 'suite', 'ceiling')), plate(suite, 'suite').area
    assert floor_area - lid >= sl['terraces'] - 3.0, 'the terraces have a floor and no ceiling'
    terrace = aligned(suite, (182.0, -3486.0))
    assert plate(suite, 'suite').contains(Point(terrace)) and not any(g.contains(Point(terrace)) for g in parts(suite, 'suite', 'ceiling'))
    assert space_at(suite, 'suite', terrace) is None


# ---------------------------------------------------------------------------------------- R-14: the disc's plateau
@pytest.mark.heavy
@pytest.mark.parametrize('name', ['house', 'tower', 'suite-revit'])
def test_the_same_ring_at_disc_radii_04_and_06(name, floors, ref_r0, monkeypatch) -> None:
    """R-2.2 / R-14: the bridge rule's 0.5 m radius sits on a plateau: the house's ground floor, the tower and the new
    suite give the same ring with 0.4 and 0.6 m."""
    d = floors(name)
    for fb in d['fbs']:
        if name == 'house' and fb['key'] != 'ground':
            continue
        rings = []
        for r in (0.4, 0.5, 0.6):
            monkeypatch.setattr(NW, 'DISC', r)
            rings.append(NW.network_of(fb, d['X'].settings['fixes'], d['X'])['ring'])
        assert rings[0].symmetric_difference(rings[1]).area < 0.5 and rings[2].symmetric_difference(rings[1]).area < 0.5, (name, fb['key'])


# -------------------------------------------------------------------------- RA-18: a missed doorway does not cost the floor
def test_ra18_with_every_door_found(builds) -> None:
    """RA-18 (should, as measured): no doorway closing on the bank; at most 2 per floor on the house, the tower and the
    old suite (the trial: 2 / 0, 2 / 1, 1). Each one is in the report, and builds nothing."""
    count = lambda name, key: sum(c['kind'] == 'doorway' for c in report(builds[name], key)['slab']['closings'])  # noqa: E731
    assert [count('bank', k) for k in ('L1', 'L2')] == [0, 0]
    assert [count('house', k) for k in ('ground', 'upper')] == [2, 0]
    assert [count('tower', k) for k in ('L29', 'L30')] == [2, 1]
    assert count('suite', 'suite') == 1
    for name, b in builds.items():
        for key, fl in b['res']['report']['floors'].items():
            for c in fl['slab']['closings']:
                assert c['kind'] in ('doorway', 'bridge') and set(c) == {'kind', 'a', 'b', 'width'}, (name, key)
                assert c['width'] == pytest.approx(math.dist(c['a'], c['b']), abs=2e-3) and (c['kind'] != 'doorway' or c['width'] <= 2.0)


@pytest.mark.acceptance
@pytest.mark.heavy
@pytest.mark.parametrize('name, key, doors, lose', [('bank', 'L1', 17, {'L1-018'}), ('bank', 'L2', 25, set()),
                                                    ('house', 'ground', 27, {'ground-032'}), ('house', 'upper', 22, set())])
def test_ra18_each_door_undone_in_turn(name, key, doors, lose, floors) -> None:
    """RA-18 (must): each door and passage undone in turn (its span out of the records, what is built in its footprint
    out of the walls). Bank L2: plate0 loses less than 2 m2 for every one of its 25; bank L1 and the house's ground
    floor: at most one each loses more (the trial: L1-018, ground-032), and it carries a slab-gap flag whose mouth lies
    within 0.3 m of the undone doorway; the house's upper floor: none."""
    d = floors(name)
    fb = next(f for f in d['fbs'] if f['key'] == key)
    _net, plate0, _u, _rep = pass1(fb, d['X'])
    todo = [i for i, r in enumerate(fb['recs']) if r['o']['kind'] != 'window']
    assert len(todo) == doors
    lost = {}
    for i in todo:
        r = fb['recs'][i]
        _n, plate, unfloored, _r = pass1(undone(fb, i), d['X'])
        gone = plate0.difference(plate).area
        if gone > 2.0:
            lost[r['o']['id']] = gone
            mouths = [LineString(u['mouth']) for u in unfloored if u['mouth'] is not None]
            assert any(m.distance(r['span']) <= 0.3 for m in mouths), f'{r["o"]["id"]}: no slab-gap flag at the undone doorway'
    assert set(lost) == lose, {k: round(v, 1) for k, v in lost.items()}


# -------------------------------------------------------------------------------------------------- the shoulds, reported
def test_the_shoulds_are_reported(builds) -> None:
    """ACCEPTANCE 2.1 (R1): the shoulds are reported: written to <WT_TMP>/r1/shoulds.json (and R1.md section 1): RA-4's
    ranges and written areas, RA-6's new-suite probes, the closings per floor."""
    out = {'plate': {}, 'writtenAreas': {}, 'closings': {}, 'newSuiteProbes': []}
    for (name, key), (_low, _high, a, b) in PLATE.items():
        got = report(builds[name], key)['slab']['plate']
        out['plate'][f'{name}/{key}'] = {'plate0': got, 'should': [a, b], 'inside': a <= got <= b}
        out['closings'][f'{name}/{key}'] = sorted((c['kind'], c['width']) for c in report(builds[name], key)['slab']['closings'])
    for name in ('bank', 'suite'):
        m = model(builds[name])
        area = {s['id']: s['area'] for s in m['spaces']}
        rows = [(r['label'], r['area'], area[r['space']]) for r in m['rooms'] if r.get('space') and '·' in r['label']]
        out['writtenAreas'][name] = {'with': len(rows), 'within15': sum(1 for _l, w, a in rows if abs(a - w) <= 0.15 * w), 'rows': rows}
    b = builds['suite-revit']
    for p in load(KEYS / 'probes.json')['drawings']['suite-revit']['probes']:
        for side in p['sides']:
            at = [own(b, 'L1', (p['at'][0] + side * d * p['n'][0], p['at'][1] + side * d * p['n'][1])) for d in (0.4, 0.6, 0.9)]
            out['newSuiteProbes'].append({'id': p['id9Nov'], 'side': side, 'onThePlate': any(plate(b, 'L1').contains(Point(q)) for q in at)})
    d = kit.RUN / 'r1'
    d.mkdir(parents=True, exist_ok=True)
    (d / 'shoulds.json').write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding='utf-8')
    assert out['writtenAreas']['bank']['within15'] >= 8, "RA-4: at least 8 of the bank's 12 written areas within 15 %"
    assert sum(1 for v in out['plate'].values() if v['inside']) >= 7, 'RA-4: the should ranges (the old suite\'s is 460 - 480 since R1.md D-3)'
