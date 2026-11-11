"""R2: the stair reader on hand-made lines (docs/rooms/DESIGN.md R-7.1 - R-7.4, R-14; ACCEPTANCE 2.1 R2). One rule per
test, in milliseconds: no drawing, no door finder. A floor is a list of reader items; the context has the options,
the vocabulary and the stair fixes."""
from __future__ import annotations

import math
import types

from shapely.geometry import Polygon

from test_r2_helpers import close, counts, mid
from walkthrough_builder.build import bank as BK
from walkthrough_builder.build import stairs_read as SR

G, W = 0.28, 1.2


def line(a, b, role='stair', cont=True, lay=None):
    return {'t': 'LINE', 'lay': lay or {'stair': 'S-STRS', 'stair-above': 'S-STRS-ABOV'}.get(role, 'A-ANNO'), 'roles': frozenset({role}),
            'cont': cont, 'pts': [[float(a[0]), float(a[1])], [float(b[0]), float(b[1])]], 'closed': False, 'depth': 0, 'path': '', 'h': 'H'}


def word(s, at):
    return {'t': 'TEXT', 'lay': 'A-ANNO', 'roles': frozenset({'other'}), 'cont': True, 'text': s, 'ins': [float(at[0]), float(at[1])],
            'depth': 0, 'path': '', 'h': 'H'}


def north(x0, y0, n, *, width=W, going=G, pair=False, role='stair', cont=True, skip=()):
    """n risers going up the sheet from y0, x0 .. x0 + width."""
    out = []
    for k in range(n):
        if k in skip:
            continue
        y = y0 + going * k
        for dy in ((-0.0075, 0.0075) if pair else (0.0,)):
            out.append(line((x0, y + dy), (x0 + width, y + dy), role, cont))
    return out


def east(x0, y0, n, *, width=W, going=G, pair=False):
    """n risers going to the right from x0, y0 .. y0 + width."""
    out = []
    for k in range(n):
        x = x0 + going * k
        for dx in ((-0.0075, 0.0075) if pair else (0.0,)):
            out.append(line((x + dx, y0), (x + dx, y0 + width)))
    return out


def read(items, *, lowest=True, fixes=None, net=None):
    fb = {'key': 'F1', 'items': list(items), 'lowest': lowest, 'old_stairs': {}}
    X = types.SimpleNamespace(options={'stairs': 'climb'}, V=BK.Vocab(None), floor_info={})
    return SR.find_stairs(fb, net, {'stairs': fixes or []}, X)


def ys(flight):
    return [round(mid(r)[1], 4) for r in flight['risers']]


# ----------------------------------------------------------------------------------------------- lines, risers, lanes
def test_a_nosing_pair_is_one_riser_at_its_middle() -> None:
    rows = read(north(1.0, 1.0, 6, pair=True))
    assert len(rows) == 1 and counts(rows[0]) == [6]
    f = rows[0]['flights'][0]
    assert sorted(ys(f)) == [round(1.0 + G * k, 4) for k in range(6)] and f['width'] == W and f['going'] == G
    assert rows[0]['id'] == 'F1-ST1' and rows[0]['floor'] == 'F1'


def test_the_pieces_of_one_riser_are_joined_before_chaining() -> None:
    """A break line cuts a riser in two: half on the stair layer, half hidden on the stair-above layer (the bank's
    riser at x 3.01). It is one riser with its whole span; the flight is not split and not narrowed."""
    items = north(1.0, 1.0, 3) + [line((1.0, 1.0 + 3 * G), (1.6, 1.0 + 3 * G)), line((1.6, 1.0 + 3 * G), (2.2, 1.0 + 3 * G), 'stair-above', False)]
    items += north(1.0, 1.0 + 4 * G, 3, role='stair-above', cont=False)
    rows = read(items)
    assert len(rows) == 1 and counts(rows[0]) == [7]
    f = rows[0]['flights'][0]
    assert f['width'] == W and all(math.isclose(math.dist(*r), W, abs_tol=1e-6) for r in f['risers'])
    assert sum(1 for b in f['beyond'] if b) == 3, 'the three risers beyond the cut'


def test_short_pieces_make_no_phantom_flight_and_the_width_is_the_median() -> None:
    """Every riser is a nosing pair whose second line is drawn in a short piece only (the tower's L30): one flight of
    the full width, no second flight of the short pieces."""
    items = []
    for k in range(8):
        y = 1.0 + G * k
        items += [line((1.0, y), (2.65, y)), line((2.0, y + 0.025), (2.65, y + 0.025))]
    rows = read(items)
    assert len(rows) == 1 and counts(rows[0]) == [8] and rows[0]['flights'][0]['width'] == 1.65


def test_a_riser_cut_short_stays_in_its_flight() -> None:
    """A break line shortens some risers (the house's service stair: 1.15, 1.09, 0.80, 0.51 m): the chain is never
    split or dropped because the common span shrank, and the width is the median."""
    items = [line((1.0, 1.0 + G * k), (1.0 + w, 1.0 + G * k)) for k, w in enumerate((1.15, 1.15, 1.15, 1.09, 0.80, 0.52))]
    rows = read(items)
    assert counts(rows[0]) == [6] and rows[0]['flights'][0]['width'] == 1.12


def test_a_skipped_riser_is_inserted_and_counted() -> None:
    rows = read(north(1.0, 1.0, 8, skip=(4,)))
    f = rows[0]['flights'][0]
    assert counts(rows[0]) == [8] and f['inserted'].count(True) == 1 and math.isclose(sorted(ys(f))[4], 1.0 + 4 * G)


def test_a_deeper_flared_first_step_and_a_landing_edge_that_runs_on() -> None:
    """The house's lower flight: the first step 0.40 m deep and wider; the last riser is the landing's edge, a line that
    runs on along the landing: it is the flight's end riser, cut to the flight's width."""
    items = [line((0.8, 1.0), (2.4, 1.0))] + north(1.0, 1.4, 5) + [line((1.0, 1.4 + 5 * G), (4.0, 1.4 + 5 * G))]
    rows = read(items)
    f = rows[0]['flights'][0]
    assert counts(rows[0]) == [7]
    by_y = sorted(f['risers'], key=lambda r: mid(r)[1])
    assert math.isclose(math.dist(*by_y[0]), 1.6) and math.isclose(mid(by_y[1])[1] - mid(by_y[0])[1], 0.4), 'the flared first step'
    assert math.isclose(math.dist(*by_y[-1]), W) and f['width'] == W, 'the landing edge, cut to the lane'
    # a 0.40 m step in the middle of a run is no step: two flights
    two = read(north(1.0, 1.0, 4) + north(1.0, 1.0 + 3 * G + 0.42, 4))
    assert sorted(c for r in two for c in counts(r)) == [4, 4]


def test_the_continuation_on_another_layer() -> None:
    """R-7.1 point 4: the house's TREE treads beyond the break line: lines on any layer but furniture and ignore, at
    the going, one of them missing (inserted and counted); the flight grows until nothing is added."""
    more = [line((1.0, 1.0 + G * k), (2.2, 1.0 + G * k), 'other', False) for k in (6, 7, 9, 10)]
    rows = read(north(1.0, 1.0, 6) + more + [line((1.0, 1.0 + G * 20), (2.2, 1.0 + G * 20), 'other')])
    f = rows[0]['flights'][0]
    assert counts(rows[0]) == [11] and f['inserted'].count(True) == 1 and sum(1 for b in f['beyond'] if b) == 4
    furniture = [line((1.0, 1.0 + G * k), (2.2, 1.0 + G * k), 'furniture') for k in (6, 7)]
    assert counts(read(north(1.0, 1.0, 6) + furniture)[0]) == [6]
    off = [line((1.0, 1.0 + G * 6 + 0.05), (2.2, 1.0 + G * 6 + 0.05), 'other')]
    assert counts(read(north(1.0, 1.0, 6) + off)[0]) == [6], 'not at the going within 2 cm'
    half = [line((1.0, 1.0 + G * 6), (1.5, 1.0 + G * 6), 'other')]
    assert counts(read(north(1.0, 1.0, 6) + half)[0]) == [6], 'covers less than 60 % of the lane'


def test_two_flights_in_one_lane_are_two_flights() -> None:
    rows = read(north(1.0, 1.0, 5) + north(1.0, 1.0 + 4 * G + 1.5, 5))
    assert sorted(c for r in rows for c in counts(r)) == [5, 5]


def test_a_group_with_no_flight_is_still_a_row() -> None:
    rows = read([line((0, 0), (1, 0)), line((1, 0), (1, 1)), line((1, 1), (0, 0.4))])
    assert len(rows) == 1 and rows[0]['flights'] == [] and rows[0]['floorEnd'] is None and len(rows[0]['lines']) == 3
    assert read([line((0, 0), (1, 0)), line((5, 0), (6, 0))]) == [], 'fewer than three lines are no stair group'


# ------------------------------------------------------------------------------------------------- senses and turns
def test_a_down_flight_and_an_up_flight_side_by_side_are_two_stairs() -> None:
    """The bank's Level 2: 0.76 m apart, never one chain (R-7.3 point 3)."""
    items = north(1.0, 1.0, 9) + north(1.0 + W + 0.76, 1.0, 9) + [line((1.0, 1.0 + 8 * G + 1.0), (4.16, 1.0 + 8 * G + 1.0))]
    items += [word('DN', (1.6, 1.0 + 8 * G + 0.25)), word('UP', (1.0 + W + 0.76 + 0.6, 1.0 + 8 * G + 0.25))]
    rows = read(items, lowest=False)
    assert [counts(r) for r in rows] == [[9], [9]]
    assert [r['flights'][0]['sense'] for r in rows] == ['arrives', 'leaves'] and [r['more']['by'] for r in rows] == ['word', 'word']
    down, up = rows
    assert math.isclose(down['floorEnd'][1], 1.0 + 8 * G) and math.isclose(up['floorEnd'][1], 1.0 + 8 * G)
    assert math.isclose(mid(down['flights'][0]['risers'][-1])[1], 1.0 + 8 * G), 'DN marks the top: listed from the bottom'
    assert math.isclose(mid(up['flights'][0]['risers'][0])[1], 1.0 + 8 * G), 'UP marks the bottom'


def test_an_l_turn_and_its_landing() -> None:
    """End risers meeting at a corner: the landing spans the first flight's width and the second's."""
    rows = read(north(1.0, 1.0, 7, pair=True) + east(1.0 + W, 1.0 + 6 * G, 9, pair=True))
    assert len(rows) == 1 and sorted(counts(rows[0])) == [7, 9] and rows[0]['more']['kind'] == 'L'
    y1 = 1.0 + 6 * G
    assert close(rows[0]['landings'][0], Polygon([(1.0, y1), (2.2, y1), (2.2, y1 + W), (1.0, y1 + W)]), 1e-6)
    assert rows[0]['more']['by'] is None and rows[0]['floorEnd'] is None


def test_a_straight_landing_needs_its_side_lines() -> None:
    a, b = north(1.0, 1.0, 5), north(1.0, 1.0 + 4 * G + 1.0, 5)
    assert sorted(c for r in read(a + b) for c in counts(r)) == [5, 5], 'nothing joins them'
    y0, y1 = 1.0 + 4 * G, 1.0 + 4 * G + 1.0
    rows = read(a + b + [line((1.0, y0), (1.0, y1)), line((2.2, y0), (2.2, y1))])
    assert len(rows) == 1 and counts(rows[0]) == [5, 5] and rows[0]['more']['kind'] == 'straight'
    assert close(rows[0]['landings'][0], Polygon([(1.0, y0), (2.2, y0), (2.2, y1), (1.0, y1)]), 1e-6)
    # with the same known sense no line is needed
    assert len(read(a + b + [word('UP', (1.6, 0.75))])) in (1, 2)


def test_a_u_turn_and_its_landing_depth() -> None:
    """Side by side, the ends on one side: the landing runs over both flights' ends and the well between them, out
    to the drawn landing line; with no line and no wall it is as deep as the flights' median width."""
    y1 = 1.0 + 7 * G
    a, b = north(1.0, 1.0, 8), north(2.3, 1.0, 8)
    edge = [line((1.0, y1 + 1.5), (3.5, y1 + 1.5)), line((1.0, y1), (1.0, y1 + 1.5)), line((3.5, y1), (3.5, y1 + 1.5))]
    rows = read(a + b + edge + [word('UP', (1.6, 0.75))])
    assert len(rows) == 1 and counts(rows[0]) == [8, 8] and rows[0]['more']['kind'] == 'U' and rows[0]['more']['by'] == 'word'
    assert close(rows[0]['landings'][0], Polygon([(1.0, y1), (3.5, y1), (3.5, y1 + 1.5), (1.0, y1 + 1.5)]), 1e-6)
    assert [f['sense'] for f in rows[0]['flights']] == ['leaves', 'leaves']
    assert math.isclose(rows[0]['floorEnd'][0], 1.6) and math.isclose(rows[0]['floorEnd'][1], 1.0)
    assert math.isclose(mid(rows[0]['flights'][1]['risers'][-1])[1], 1.0), 'the second flight comes back down the sheet'
    # no landing line: both senses known (two words), the landing as deep as the median width
    rows = read(a + b + [word('UP', (1.6, 0.75)), word('UP', (2.9, y1 + 0.3))])
    assert len(rows) == 2, 'two UP words at opposite ends: two stairs leaving, not one'


# ---------------------------------------------------------------------------------------------------------- direction
def arrow(tail, tip):
    d = BK.unit((tip[0] - tail[0], tip[1] - tail[1]))
    out = [line(tail, tip, 'other')]
    for s in (1, -1):
        a = math.radians(25) * s
        back = (-(d[0] * math.cos(a) - d[1] * math.sin(a)), -(d[0] * math.sin(a) + d[1] * math.cos(a)))
        out.append(line(tip, (tip[0] + back[0] * 0.2, tip[1] + back[1] * 0.2), 'other'))
    return out


def test_direction_by_word_by_arrow_by_cut_by_staff_or_not_at_all() -> None:
    flight = north(1.0, 1.0, 10)
    top = 1.0 + 9 * G
    none = read(flight)[0]
    assert none['more']['by'] is None and none['floorEnd'] is None and none['flights'][0]['sense'] == ''
    up = read(flight + [word('UP', (1.6, 0.75))])[0]
    assert up['more']['by'] == 'word' and up['flights'][0]['sense'] == 'leaves' and math.isclose(up['floorEnd'][1], 1.0)
    dn = read(flight + [word('DOWN', (1.6, 0.75))], lowest=False)[0]
    assert dn['flights'][0]['sense'] == 'arrives' and math.isclose(dn['floorEnd'][1], 1.0)
    assert math.isclose(mid(dn['flights'][0]['risers'][0])[1], top), 'DOWN marks the top: the flight is listed from its bottom'
    # a walking line with an arrowhead: the end without the arrowhead is at this floor
    ar = read(flight + arrow((1.6, 0.8), (1.6, top + 0.2)))[0]
    assert ar['more']['by'] == 'arrow' and math.isclose(ar['floorEnd'][1], 1.0) and ar['flights'][0]['sense'] == 'leaves'
    ar2 = read(flight + arrow((1.6, top + 0.2), (1.6, 0.8)), lowest=False)[0]
    assert ar2['more']['by'] == 'arrow' and math.isclose(ar2['floorEnd'][1], top) and ar2['more']['oriented'] is False
    short = read(flight + arrow((1.6, 0.8), (1.6, 1.6)))[0]
    assert short['more']['by'] is None, 'an arrow over less than half the flight says nothing'
    # the cut: continuous at one end, hidden at the other
    cut = read(north(1.0, 1.0, 5) + north(1.0, 1.0 + 5 * G, 5, role='stair-above', cont=False))[0]
    assert cut['more']['by'] == 'cut' and math.isclose(cut['floorEnd'][1], 1.0) and cut['more']['oriented'] is True
    # staff: the bottom point wins over the word
    st = read(flight + [word('UP', (1.6, 0.75))], fixes=[{'floor': 'F1', 'at': [1.6, 2.0], 'bottom': [1.6, top], 'use': 'auto'}])[0]
    assert st['more']['by'] == 'staff' and math.isclose(mid(st['flights'][0]['risers'][0])[1], top) and st['more']['fix'][0] == 0
    other = read(flight, fixes=[{'floor': 'F2', 'at': [1.6, 2.0], 'bottom': [1.6, top], 'use': 'auto'}])[0]
    assert other['more']['by'] is None and other['more']['fix'][0] is None, "another floor's fix"


def test_the_lines_option_keeps_todays_reading() -> None:
    fb = {'key': 'F1', 'items': north(1.0, 1.0, 6), 'lowest': True,
          'old_stairs': {'stairs': [{'hull': Polygon([(1, 1), (2.2, 1), (2.2, 2.4), (1, 2.4)]), 'flights': [], 'lines': [0, 1, 2]}]}}
    X = types.SimpleNamespace(options={'stairs': 'lines'}, V=BK.Vocab(None), floor_info={})
    rows = SR.find_stairs(fb, None, {}, X)
    assert [(r['id'], r['flights'], r['lines']) for r in rows] == [('F1-ST1', [], [0, 1, 2])]
