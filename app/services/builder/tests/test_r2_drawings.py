"""R2: the stairs of the house, the bank and the tower (docs/rooms/ACCEPTANCE.md RA-9's two tables; DESIGN R-7.7).

First the reader alone, before any solid is built: the riser count of every flight (docs/rooms/contract-issues/R2.md
section 1 has the table and the plots). Then the stairs across the floors: which climb, which stay as lines and why.
Then the models of the session's builds (conftest.py: bank_rooms, house_rooms, tower_rooms).

The reader and the builder run here on the floors after prepare_floors, floor_walls, network_of and plate_of
(test_r2_helpers.stages_of), made once per drawing; every test is `heavy` (the door finder runs in this process).
"""
from __future__ import annotations

import math

import pytest
from shapely.geometry import Point, Polygon, box
from shapely.ops import unary_union

from test_r2_helpers import counts, mid, model_poly, row_at, stages_of
from walkthrough_builder.build import stairs_build as SB

pytestmark = pytest.mark.heavy


@pytest.fixture(scope='module')
def stages(ref, tmp_path_factory):
    made = {}

    def get(name: str) -> dict:
        if name not in made:
            made[name] = stages_of(name, ref, tmp_path_factory.mktemp(f'r2-{name}'))
        return made[name]
    return get


def built_of(st, sid='S1'):
    return next(sb for sb in st['stairs']['built'] if sb['stairway']['id'] == sid)


def left_of(st, row):
    return next(s for s in st['stairs']['left'] if s['id'] == row['id'])


# ------------------------------------------------------------------------------- the reader alone (RA-9, first table)
def test_ra9_the_house_ground_plan(stages) -> None:
    """The main stair: 7 (the first 0.40 m before the second, flared), then 14 (6 on STAIR, 8 on TREE); one L."""
    rows = stages('house')['found']['ground']
    main = row_at(rows, 20.4, 22.0)
    assert counts(main) == [7, 14] and main['more']['kind'] == 'L' and len(main['landings']) == 1
    a, b = main['flights']
    assert math.isclose(mid(a['risers'][1])[1] - mid(a['risers'][0])[1], 0.40, abs_tol=0.02), 'the first step is 0.40 m deep'
    assert math.dist(*a['risers'][0]) > math.dist(*a['risers'][3]) + 0.4, '... and flared'
    assert sum(1 for v in b['beyond'] if v) == 8 and not any(b['inserted']) and not any(a['inserted'])
    assert [round(v, 2) for v in main['landings'][0].bounds] == [19.67, 23.05, 21.05, 24.25] or \
        max(abs(p - q) for p, q in zip(main['landings'][0].bounds, (19.67, 23.05, 21.05, 24.25))) <= 0.02
    assert main['more']['by'] == 'arrow' and math.dist(main['floorEnd'], (20.40, 21.15)) <= 0.3, 'the walking line: the bottom'
    assert counts(row_at(rows, 20.2, 12.4)) == [7], 'ST-05'
    assert counts(row_at(rows, 40.9, 21.4)) == [6], 'the service stair ST-02'
    assert sum(1 for r in rows if r['flights']) == 3, 'no other flight (the flared steps\' side edges are no flight)'


def test_ra9_the_house_upper_plan(stages) -> None:
    """The main stair's upper flight again: every riser within 5 cm of the ground plan's. (Nine riser lines are on
    STAIR; the ninth is a 0.32 m stub that goes on on TREE: the reader counts it with the continuation.)"""
    st = stages('house')
    upper = row_at(st['found']['upper'], 23.0, 23.7)
    ground = row_at(st['found']['ground'], 20.4, 22.0)
    assert counts(upper) == [14] and sum(1 for v in upper['flights'][0]['beyond'] if not v) == 8
    below = [r for f in ground['flights'] for r in f['risers']]
    assert all(any(SB._near(r, q) for q in below) for r in upper['flights'][0]['risers'])
    assert upper['more']['by'] == 'arrow'
    assert counts(row_at(st['found']['upper'], 41.0, 19.5)) == [7, 4], 'the service stair upstairs (an L)'


def test_ra9_the_bank(stages) -> None:
    """Level 1: 4 (east), 5 (north), 3 (west), one chain of two L turns; Level 2: 9 (DOWN) and 9 (UP): two stairs,
    never one chain; the north stair: 18 on both levels."""
    st = stages('bank')
    l1, l2 = st['found']['L1'], st['found']['L2']
    main = row_at(l1, 2.8, 8.9)
    assert counts(main) == [4, 5, 3] and main['more']['kind'] == 'L' and len(main['landings']) == 2
    assert main['more']['by'] == 'cut' and math.dist(main['floorEnd'], (3.74, 7.88)) <= 0.05, "Level 1's cut: the east flight's foot"
    assert [round(f['width'], 1) for f in main['flights']] == [0.9, 1.0, 0.9]
    down, up = row_at(l2, 3.5, 7.6), row_at(l2, 3.5, 9.5)
    assert down['id'] != up['id'] and counts(down) == [9] and counts(up) == [9]
    assert down['flights'][0]['sense'] == 'arrives' and up['flights'][0]['sense'] == 'leaves'
    assert down['more']['by'] == 'word' and up['more']['by'] == 'word'
    assert counts(row_at(l1, -2.3, 12.2)) == [18] and counts(row_at(l2, -2.3, 12.2)) == [18]
    assert sum(1 for r in l1 if r['flights']) == 2 and sum(1 for r in l2 if r['flights']) == 3


def test_ra9_the_tower(stages) -> None:
    """Stair A: 10 + 10 on both floors, flights 1.65 m wide (not 0.46 m), no third flight. Stair B: 10 + 8 on L29,
    8 + 8 on L30, flights 1.2 - 1.35 m wide (a should; RA-9 says 1.2 - 1.3: R2.md)."""
    st = stages('tower')
    for key in ('L29', 'L30'):
        a = [r for r in st['found'][key] if r['flights'] and r['hull'].centroid.x > 5]
        assert sorted(c for r in a for c in counts(r)) == [10, 10], key
        assert all(f['width'] == 1.65 for r in a for f in r['flights']), key
    b29 = [r for r in st['found']['L29'] if r['flights'] and r['hull'].centroid.x < 5]
    b30 = [r for r in st['found']['L30'] if r['flights'] and r['hull'].centroid.x < 5]
    assert sorted(c for r in b29 for c in counts(r)) == [8, 10] and sorted(c for r in b30 for c in counts(r)) == [8, 8]
    assert all(1.2 <= f['width'] <= 1.35 for r in b29 + b30 for f in r['flights'])
    a29 = next(r for r in st['found']['L29'] if r['hull'].centroid.x > 5)
    assert a29['more']['kind'] == 'U' and counts(a29) == [10, 10] and a29['more']['by'] == 'cut'


# ---------------------------------------------------------------------------------- the stairs (RA-9, second table)
def check_solid(st, sb) -> None:
    """A climbable stair: every tread between its two riser lines (within 0.02 m of their own ends), the walking line
    from the lower plate to the upper plate, 0.3 m clear of walls; the top riser's middle before its end (R1's patch)."""
    sw = sb['stairway']
    by = {fb['key']: fb for fb in st['fbs']}
    assert st['plate0'][sw['from']].contains(Point(sw['walk'][0])) and st['plate0'][sw['to']].contains(Point(sw['walk'][-1]))
    assert SB._walls(by[sw['from']]).distance(Point(sw['walk'][0])) >= 0.3 - 1e-6
    assert SB._walls(by[sw['to']]).distance(Point(sw['walk'][-1])) >= 0.3 - 1e-6
    assert sw['bottom'] == sw['walk'][0] and sw['top'] == sw['walk'][-1] and sw['top'] == sb['arrival']
    assert 0.3 - 1e-6 <= math.dist(sw['walk'][-2], sw['walk'][-1]) <= 1.0 + 1e-6
    r = sw['riser']
    assert sw['treads'] == len(sb['treads']) and sw['landings'] == len(sb['landings']) and sw['risers'] == sw['treads'] + sw['landings'] + 1
    tops = sorted(p['z1'] for p in sb['treads'] + sb['landings'])
    assert all(abs(z - (k + 1) * (by[sw['to']]['level'] - by[sw['from']]['level']) / sw['risers']) <= 0.001 for k, z in enumerate(tops))
    assert abs(tops[0] - r) <= 0.001
    for t in sb['treads']:
        assert t['poly'].is_valid and 0.05 < t['poly'].area < 1.5 and t['z0'] < t['z1'], t['label']
    well = sb['wellOf'][sw['to']]
    last = sb['treads'][-1]['poly']
    assert last.difference(well.buffer(0.001)).area >= 0.04 * sw['width'], 'the last tread laps 0.05 m past the well: under the slab'


def test_ra9_the_house_main_stair_climbs(stages) -> None:
    st = stages('house')
    sb = built_of(st)
    sw = sb['stairway']
    assert (sw['from'], sw['to'], sw['risers'], sw['kind'], sw['landings'], sw['treads'], sw['direction']) == \
        ('ground', 'upper', 21, 'L', 1, 19, 'arrow')
    assert abs(sw['riser'] - 0.186) <= 0.002
    check_solid(st, sb)
    # RA-9 as decided on 11 Nov (R2.md D-1): riser 1's middle, walk[1], within 0.3 m of (20.40, 21.15); `bottom` is the
    # walking line's first point, 1.0 m before riser 1 (R-8.5). The strict xfail on `bottom` was removed by RI.
    assert math.dist(sw['walk'][1], (20.40, 21.15)) <= 0.3, "riser 1's middle"
    upper = row_at(st['found']['upper'], 23.0, 23.7)
    assert all(s['id'] != upper['id'] for s in st['stairs']['left']), "the upper plan's drawing adds no stair and no flag"
    assert len(st['stairs']['built']) == 1 and st['stairs']['pairs'] == []
    assert sb['linesUsed']['ground'] and sb['linesUsed']['upper']


def test_ra9_the_house_other_stairs_stay_lines(stages) -> None:
    st = stages('house')
    st05 = left_of(st, row_at(st['found']['ground'], 20.2, 12.4))
    assert (st05['why'], st05['severity'], st05['risers'], st05['keptVoid']) == ('no floor at its top', 'info', 7, None)
    assert st05['text'].endswith('its 7 steps would rise about 1.0–1.5 m: no floor of the model is at that height.')
    st02 = left_of(st, row_at(st['found']['ground'], 40.9, 21.4))
    assert (st02['why'], st02['severity'], st02['risers']) == ('the riser does not fit', 'check', 16)
    assert '16 steps for 3.90 m give 0.24 m each' in st02['text'] and 'A storey of 2.94–3.36 m would fit every stair' in st02['text']
    up02 = left_of(st, row_at(st['found']['upper'], 41.0, 19.5))
    assert up02['why'] == 'the riser does not fit' and abs(up02['keptVoid'].area - 3.93) <= 0.05, "today's void stays over it upstairs"
    assert all(s['why'] in ('no floor at its top', 'the riser does not fit', 'turning or curved steps') for s in st['stairs']['left'])
    rows = [r for key in ('ground', 'upper') for r in st['found'][key]]
    done = {s['id'] for s in st['stairs']['left']}
    assert sum(1 for r in rows if r['id'] not in done) == 2, 'every stair group is climbable (both plans of the main stair) or flagged'


def test_ra9_the_bank_main_stair_climbs(stages) -> None:
    st = stages('bank')
    sb = built_of(st)
    sw = sb['stairway']
    assert (sw['from'], sw['to'], sw['risers'], sw['landings'], sw['treads'], sw['kind']) == ('L1', 'L2', 21, 3, 17, 'L')
    assert abs(sw['riser'] - 0.176) <= 0.002 and sw['direction'] == 'cut'
    check_solid(st, sb)
    assert [p['label'] for p in sb['landings']] == ['stair S1 landing 4', 'stair S1 landing 9', 'stair S1 landing 12']
    down = row_at(st['found']['L2'], 3.5, 7.6)
    assert all(s['id'] != down['id'] for s in st['stairs']['left']), 'matched across the two files: flight 4 is its top'
    assert set(down['flights'][0]['lines']) <= set(sb['linesUsed']['L2'])
    up = left_of(st, row_at(st['found']['L2'], 3.5, 9.5))
    assert (up['why'], up['severity'], up['risers']) == ('it leaves the top floor', 'info', 9)
    assert up['text'].endswith('it leads to a floor that is not in the model.')
    assert 1.8 <= up['keptVoid'].area <= 2.4 and not up['keptVoid'].intersects(box(4.6, 7.0, 5.7, 8.2)), 'never the arrival'
    north = left_of(st, row_at(st['found']['L1'], -2.3, 12.2))
    assert (north['why'], north['severity'], north['risers']) == ('off the plate', 'check', 18), 'built or flagged, the reason recorded'
    assert st['stairs']['pairs'] == []
    # the well: flight 4, the landings from the second on and the band the handrails fence off between the two flights;
    # Level 2 keeps its floor over the first flight (headroom allows it)
    well = sb['wellOf']['L2']
    assert well.contains(box(2.7, 7.1, 4.4, 8.1)) and well.contains(box(1.5, 7.1, 2.4, 8.0)), 'flight 4 and the third landing'
    assert well.intersection(box(2.6, 8.25, 4.5, 8.8)).area >= 0.9, 'the fenced band'
    assert not well.intersects(box(4.6, 7.0, 5.7, 8.2)), 'the arrival stays floor'
    # the parts in the way: the toilet's walls under flights 3 and 4
    feet = unary_union([c['footprint'] for c in sb['cuts'] if st['fbs'][0]['parts'][c['part']]['kind'] == 'wall'])
    assert feet.intersection(box(1.37, 8.11, 2.27, 8.62)).area >= 0.03, 'under flight 3'
    assert feet.intersection(box(2.53, 7.01, 4.53, 8.16)).area >= 0.03, 'under flight 4'
    assert all(c['footprint'].area >= 0.01 for c in sb['cuts']) and len(sb['cuts']) <= 10


def test_ra9_the_tower_stairs(stages) -> None:
    """A should: stair A climbs L29 -> L30 with the assumed levels; stair B stays as lines with the riser height and
    the storey that would fit; today's void stays over it on L30."""
    st = stages('tower')
    sb = built_of(st)
    sw = sb['stairway']
    assert (sw['from'], sw['to'], sw['risers'], sw['kind'], sw['landings']) == ('L29', 'L30', 20, 'U', 1)
    assert abs(sw['riser'] - 0.200) <= 0.002 and sw['width'] == 1.65
    check_solid(st, sb)
    b29 = next(s for s in st['stairs']['left'] if s['floor'] == 'L29')
    assert (b29['why'], b29['severity'], b29['risers']) == ('the riser does not fit', 'check', 18)
    assert '18 steps for 4.00 m give 0.22 m each' in b29['text'] and 'A storey of 2.80–3.78 m would fit' in b29['text']
    b30 = next(s for s in st['stairs']['left'] if s['floor'] == 'L30')
    assert b30['why'] == 'the riser does not fit' and abs(b30['keptVoid'].area - 17.24) <= 0.3
    assert len(st['stairs']['left']) == 2 and len(st['stairs']['built']) == 1, "L30's drawing of stair A is the same stair"


# --------------------------------------------------------------------------------------------- the models (build())
def model_stair(b, sid='S1'):
    m = b['res']['model']
    sw = next(s for s in m['stairways'] if s['id'] == sid)
    return m, sw, [p for p in m['parts'] if p.get('stair') == sid]


def check_model(b, frm, to, risers) -> None:
    m, sw, ps = model_stair(b)
    assert (sw['from'], sw['to'], sw['risers']) == (frm, to, risers)
    assert not [p for p in m['parts'] if p['kind'] == 'step'], 'no two-riser step part in a new-rule model'
    treads = sorted((p for p in ps if p['kind'] == 'tread'), key=lambda p: p['z1'])
    assert len(treads) == sw['treads'] and all(p['floor'] == frm and p['follow'] is False and p['fit'] == 'storey' for p in treads)
    slab = unary_union([model_poly(p) for p in m['parts'] if p['kind'] == 'slab' and p['floor'] == to])
    last = model_poly(treads[-1])
    assert 0.03 * sw['width'] <= last.intersection(slab).area <= 0.12 * sw['width'], 'the upper slab laps the last tread by 0.05 m'
    below = sum(model_poly(t).intersection(slab).area for t in treads[-4:-1])
    assert below <= 0.01, 'the well is open over the treads below it'
    assert any(v['what'] == 'stair well' for v in m['voids'][to])
    assert slab.contains(Point(sw['top'])), 'the walking line ends on the upper slab'
    rows = [r for fl in b['res']['report']['floors'].values() for r in fl['stairways']]
    assert sum(1 for r in rows if r['state'] == 'climb') == len(m['stairways'])
    assert all(r['state'] == 'climb' or (r['why'] and r['text'] and r['severity'] in ('info', 'check')) for r in rows)


def test_the_house_model(house_rooms) -> None:
    check_model(house_rooms, 'ground', 'upper', 21)
    _m, sw, ps = model_stair(house_rooms)
    assert sw['kind'] == 'L' and sw['direction'] == 'arrow' and abs(sw['riser'] - 0.186) <= 0.002
    assert [p['label'] for p in ps if p['kind'] == 'landing'] == ['stair S1 landing 7']


def test_the_bank_model(bank_rooms) -> None:
    check_model(bank_rooms, 'L1', 'L2', 21)
    m, sw, ps = model_stair(bank_rooms)
    assert sw['landings'] == 3 and abs(sw['riser'] - 0.176) <= 0.002
    clash = bank_rooms['res']['report']['floors']['L1']['stairClash']
    assert sum(1 for c in clash if c['kind'] == 'wall') >= 2 and all(c['stair'] == 'S1' for c in clash)
    cut = [p for p in ps if p['kind'] == 'wall']
    assert cut and all(p['follow'] is False and p['fit'] == 'storey' and p['z1'] < 3.7 for p in cut), 'cut to the stair\'s underside'


def test_the_tower_model(tower_rooms) -> None:
    check_model(tower_rooms, 'L29', 'L30', 20)
