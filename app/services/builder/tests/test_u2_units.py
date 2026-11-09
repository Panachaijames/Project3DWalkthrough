"""U2: units (docs/upload/DESIGN.md U-7.4; ACCEPTANCE A-4, 2.1 U2): the decision table, the door votes, the quick
decision before the walk and the second walk when the full vote disagrees."""
from __future__ import annotations

import math

import pytest

import test_u2_kit as K
from walkthrough_builder import units as U


def test_reader_frame_factors_equal_the_detectors() -> None:
    from walkthrough_builder.vendor.load import load
    import kit
    data = kit.RUN / 'openings-data'
    data.mkdir(parents=True, exist_ok=True)
    op = load('openings', openings_data=data)
    assert {u: op.UNITS[u] for u in U.UNITS} == U.UNITS_K
    assert all(math.isclose(U.M_PER_UNIT[u], U.UNITS_K[u] / 1000) for u in U.UNITS)


def test_flattening_is_ten_millimetres_in_drawing_units() -> None:
    assert U.flatten_distance('mm') == 10 and isinstance(U.flatten_distance('mm'), int)   # prims' own argument
    assert U.flatten_distance('m') == pytest.approx(0.01)
    assert U.flatten_distance('in') == pytest.approx(10 / 25.4)
    assert U.flatten_distance('cm') == pytest.approx(1.0)


def test_votes_per_unit_hypothesis() -> None:
    # radii in the reader frame (DXF units / 1000): 900 mm, 0.9 m, 36 in, 3 ft, 90 cm
    assert U.votes_of([0.9]) == {'mm': 1, 'cm': 0, 'm': 0, 'in': 0, 'ft': 0}
    assert U.votes_of([0.0009]) == {'mm': 0, 'cm': 0, 'm': 1, 'in': 0, 'ft': 0}
    assert U.votes_of([0.036]) == {'mm': 0, 'cm': 0, 'm': 0, 'in': 1, 'ft': 0}
    assert U.votes_of([0.003]) == {'mm': 0, 'cm': 0, 'm': 0, 'in': 0, 'ft': 1}
    assert U.votes_of([0.09]) == {'mm': 0, 'cm': 1, 'm': 0, 'in': 0, 'ft': 0}
    assert U.votes_of([0.5, 1.3]) == U.zero_votes()                       # 0.5 m and 1.3 m leaves: no door


@pytest.mark.parametrize('ins, votes, used, verdict', [
    (4, {'mm': 16}, 'mm', 'agree'),                                        # bank1
    (1, {'mm': 22, 'm': 4}, 'mm', 'votes-win'),                            # the house: inches declared, mm doors
    (4, {'mm': 2}, 'mm', 'declared-only'),
    (4, {}, 'mm', 'declared-only'),
    (6, {'mm': 2}, 'm', 'declared-only'),                                  # too few to overrule
    (6, {'mm': 3}, 'mm', 'votes-win'),
    (0, {'in': 5}, 'in', 'votes-win'),                                     # nothing declared, the doors say
    (None, {'mm': 2}, 'mm', 'unknown'),
    (14, {}, 'mm', 'unknown'),                                             # decimetres: not a contract unit
    (4, {'mm': 3, 'cm': 3}, 'mm', 'agree'),                                # a tie goes to the declared units
])
def test_decision_table(ins, votes, used, verdict) -> None:
    d = U.decide(ins, votes, None)
    assert (d['used'], d['verdict']) == (used, verdict)
    assert set(d['votes']) == set(U.UNITS) and d['note']
    assert d['declared'] == U.INSUNITS.get(ins)


def test_votes_win_note_names_both_units() -> None:
    d = U.decide(1, {'mm': 22, 'm': 4}, 3487.5)
    assert d['note'].startswith('the file says inches, its doors say millimetres')
    assert d['dimensionMedian'] == 3487.5


def test_forced_units_keep_the_verdict_and_say_so() -> None:
    d = U.decide(1, {'mm': 22}, None, forced='in')
    assert d['used'] == 'in' and d['verdict'] == 'votes-win' and 'as chosen' in d['note']
    with pytest.raises(ValueError):
        U.decide(4, {}, None, forced='yd')


def test_door_votes_need_a_leaf_from_the_hinge() -> None:
    # a 900 mm quarter arc about (0, 0) from (0.9, 0) to (0, 0.9) (reader frame = m for mm drawings)
    arc = (0.0, 0.0, 0.9, 90.0, (0.9, 0.0), (0.0, 0.9))
    leaf = [((0.0, 0.0), (0.9, 0.0))]
    assert U.door_votes([arc], leaf) == ({'mm': 1, 'cm': 0, 'm': 0, 'in': 0, 'ft': 0}, [True])
    assert U.door_votes([arc], [((0.0, 0.0), (0.5, 0.0))])[1] == [False]          # too short
    assert U.door_votes([arc], [((0.3, 0.3), (0.9, 0.0))])[1] == [False]          # not from the hinge
    assert U.door_votes([arc], [((0.06, 0.0), (0.9, 0.05))])[1] == [True]         # within 8 % of the radius
    # an arc of 120 degrees has a leaf (door-size arc) but is no quarter: no vote
    wide = (0.0, 0.0, 0.9, 120.0, (0.9, 0.0), (-0.45, 0.78))
    assert U.door_votes([wide], leaf) == (U.zero_votes(), [True])


def _doors(msp, n: int, r: float, layer: str = 'A-DOOR', x0: float = 0.0) -> None:
    for i in range(n):
        x = x0 + i * 3 * r
        msp.add_arc((x, 0), r, 0, 90, dxfattribs={'layer': layer})
        msp.add_line((x, 0), (x + r, 0), dxfattribs={'layer': layer})


def test_inches_header_with_millimetre_doors_reads_in_mm_once(tmp_path) -> None:
    def build(doc, msp):
        _doors(msp, 4, 900.0)
        msp.add_circle((0, 5000), 500, dxfattribs={'layer': 'A-WALL'})
    dxf = K.synthetic(tmp_path / 'inches.dxf', build, insunits=1)
    r = K.read(dxf, tmp_path / 'out')
    u = r['drawing']['units']
    assert (u['declared'], u['used'], u['verdict'], u['votes']['mm']) == ('in', 'mm', 'votes-win', 4)
    assert r['cache']['units'] == 'mm'
    assert not any('read again' in s for s in r['log'])                   # the quick decision already said mm
    circle = next(d for d in r['items'] if d['t'] == 'CIRCLE')
    flat = next(d for d in K.prims_flatten(dxf)[0] if d['t'] == 'CIRCLE')
    assert circle['pts'] == flat['pts']                                    # flattened at 10 mm: prims' own points


def test_metre_doors_flatten_at_ten_millimetres(tmp_path) -> None:
    def build(doc, msp):
        _doors(msp, 3, 0.9)
        msp.add_circle((0, 5), 0.5, dxfattribs={'layer': 'A-WALL'})
    dxf = K.synthetic(tmp_path / 'metres.dxf', build, insunits=6)
    r = K.read(dxf, tmp_path / 'out')
    assert (r['drawing']['units']['used'], r['drawing']['units']['verdict']) == ('m', 'agree')
    circle = next(d for d in r['items'] if d['t'] == 'CIRCLE')
    # a 0.5 m circle flattened at 10 mm has many points; at prims' 10 drawing units (10 m) it would have a handful
    assert len(circle['pts']) > 20
    assert len(next(d for d in K.prims_flatten(dxf)[0] if d['t'] == 'CIRCLE')['pts']) < len(circle['pts'])


def test_full_vote_overrules_the_quick_one_and_walks_again(tmp_path) -> None:
    # three door blocks drawn in metres, inserted 1000 times larger: as drawn (one vote per definition) they say
    # metres, on the sheet millimetres
    def build(doc, msp):
        for i in range(3):
            blk = doc.blocks.new(f'DOOR-M{i}')
            blk.add_arc((0, 0), 0.9 + 0.05 * i, 0, 90)
            blk.add_line((0, 0), (0.9 + 0.05 * i, 0))
            msp.add_blockref(f'DOOR-M{i}', (i * 3000, 0), dxfattribs={'layer': 'A-DOOR', 'xscale': 1000,
                                                                       'yscale': 1000, 'zscale': 1000})
    dxf = K.synthetic(tmp_path / 'scaled.dxf', build, insunits=4)
    import ezdxf
    assert U.quick(ezdxf.readfile(dxf))['used'] == 'm'
    r = K.read(dxf, tmp_path / 'out')
    assert (r['drawing']['units']['used'], r['drawing']['units']['verdict']) == ('mm', 'agree')
    assert any('read again in millimetres' in s for s in r['log'])
    assert r['cache']['units'] == 'mm'
    assert K.strip(r['items']) == K.strip(K.prims_flatten(dxf)[0])


def test_forced_units_read_in_those_units(tmp_path) -> None:
    def build(doc, msp):
        _doors(msp, 3, 900.0)
    dxf = K.synthetic(tmp_path / 'forced.dxf', build, insunits=4)
    r = K.read(dxf, tmp_path / 'out', units='cm')
    assert r['drawing']['units']['used'] == 'cm' and r['result']['units']['used'] == 'cm'
    assert r['cache']['units'] == 'cm'
    assert r['drawing']['units']['verdict'] == 'agree'                    # what the file and its doors say
    with pytest.raises(ValueError):
        K.read(dxf, tmp_path / 'out2', units='furlong')


def test_mirrored_door_arcs_vote_at_their_world_centre(tmp_path) -> None:
    # a door block inserted mirrored: its arc's extrusion turns over; the hinge is the world centre (U2.md)
    def build(doc, msp):
        blk = doc.blocks.new('DOOR')
        blk.add_arc((0, 0), 900, 0, 90)
        blk.add_line((0, 0), (900, 0))
        for i in range(3):
            msp.add_blockref('DOOR', (i * 3000 + 1000, 0), dxfattribs={'layer': 'A-DOOR', 'xscale': -1})
    dxf = K.synthetic(tmp_path / 'mirrored.dxf', build, insunits=4)
    r = K.read(dxf, tmp_path / 'out')
    assert r['drawing']['units']['votes']['mm'] == 3
    lay = next(la for la in r['drawing']['layers'] if la['name'] == 'A-DOOR')
    assert (lay['doorArcs'], lay['doorArcsWithLeaf']) == (3, 3)
