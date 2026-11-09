"""U3: the builder's rules on a synthetic plan (ACCEPTANCE 2.1 U3; docs/upload/DESIGN.md U-9, U-10).

One-floor and three-floor builds (the real detector); with a fake detector giving chosen records: the door-head order
(U-10.4), W x W x H heads, eitherKind glazing, the low-wall sill, screens never cut (U-10.5), the plinth (U-9.5); the
fixes (U-10.6): set-aside by key, by an INSERT's subtree, by element id + rsig, by sig, an ambiguous match, an unmatched
ref; opening fixes; outline suggestions accepted; the errors (area_empty, align_failed, bad_settings, no_floors).
"""
from __future__ import annotations

import collections
import json
import pickle

import pytest
from shapely.geometry import Polygon

from test_contracts import walk
from test_u3_helpers import (fake_detector, plan_dxf, plan_records, plan_settings, read_plan, run_build,  # noqa: F401
                             source_ctx)
from walkthrough_builder import contracts, keys as K, names as N
from walkthrough_builder.build import BuildError
from walkthrough_builder.build.bank import Vocab, head_in_name

SHA = ['a' * 40, 'b' * 40, 'c' * 40]


@pytest.fixture(scope='module')
def plan(tmp_path_factory):
    d = tmp_path_factory.mktemp('u3plan')
    out = {}
    for name, kw in (('base', {}), ('moved', {'dx': 5000.0}), ('reexport', {'extra_first': 3, 'chair_dx': 500.0}),
                     ('extras', {'parapet': True, 'free_glass': True}),
                     ('pattern', {'parapet': True, 'free_glass': True, 'fill': 'pattern'})):
        out[name] = read_plan(plan_dxf(d / f'{name}.dxf', **kw), d / name)
    return out


def one(plan, which='base', sha=SHA[0]):
    return source_ctx(sha, 'plan1.dxf', plan[which]['items'], drawing=plan[which]['drawing'], kind='dxf')


def parts(res, kind=None, label=None, floor='F1'):
    return [p for p in res['model']['parts'] if p['floor'] == floor and (kind is None or p['kind'] == kind)
            and (label is None or p.get('label') == label)]


def opening(res, rid):
    return next((o for o in res['model']['openings'] if o['id'] == rid), None)


# ---------------------------------------------------------------------------------------------------- whole builds
def test_one_floor_build_with_the_real_detector(plan, scratch):
    res, logs = run_build(plan_settings([SHA[0]]), [one(plan)], scratch)
    assert walk({k: v for k, v in res.items() if k != '_steps'}, contracts.BuildResult) == []
    json.dumps(res, allow_nan=False)
    m = res['model']
    assert [f['key'] for f in m['floors']] == ['F1'] and m['source'] == ['plan1.dxf']
    assert {'wall', 'slab'} <= {p['kind'] for p in m['parts']}
    assert res['report']['floors']['F1']['alignment']['method'] == 'none'
    assert res['replay']['floors']['F1']['sheet'] == [0.0, 0.0]
    names = [s for s, _ in res['_steps']]
    assert names[0] == 'align' and 'detect:F1' in names and 'walls' in names and names[-1] == 'furniture'


def test_three_floor_build_aligns_a_moved_file_by_its_grid(plan, scratch):
    s = plan_settings(SHA, levels=[0.0, 3.0, 6.5], heights=[3.0, 3.5, 3.2])
    srcs = [one(plan, 'base', SHA[0]), one(plan, 'base', SHA[1]), one(plan, 'moved', SHA[2])]
    res, _ = run_build(s, srcs, scratch)
    assert walk({k: v for k, v in res.items() if k != '_steps'}, contracts.BuildResult) == []
    fl = res['model']['floors']
    assert [f['key'] for f in fl] == ['F1', 'F2', 'F3']
    assert 'sheetShift' not in fl[1] and fl[2]['sheetShift'] == [5.0, 0.0]
    al = res['report']['floors']['F3']['alignment']
    assert al['method'] == 'grid' and al['families'] == 2 and set(al['labels']) == {'1', '2', 'A', 'B'}
    assert al['shift'] == pytest.approx([-5.0, 0.0]) and al['spread'] < 1e-6
    assert res['report']['floors']['F2']['alignment']['shift'] == [0.0, 0.0]
    # F3's walls land on F1's: the same plan, moved 5 m on its sheet
    w1 = sum(Polygon(p['o'], p['h']).area for p in parts(res, 'wall', floor='F1'))
    w3 = sum(Polygon(p['o'], p['h']).area for p in parts(res, 'wall', floor='F3'))
    assert w3 == pytest.approx(w1, rel=1e-6)
    b1 = Polygon(parts(res, 'slab', floor='F1')[0]['o']).bounds
    b3 = Polygon(parts(res, 'slab', floor='F3')[0]['o']).bounds
    assert b1 == pytest.approx(b3, abs=0.002)
    assert res['floors_frame']['F3']['toSheet'] == pytest.approx([res['model']['offset'][0] + 5.0, res['model']['offset'][1]])
    # the replay: three files side by side; the facts name every floor
    sheets = [res['replay']['floors'][k]['sheet'] for k in ('F1', 'F2', 'F3')]
    assert sheets[0] == [0.0, 0.0] and 0 < sheets[1][0] < sheets[2][0] - 5.0 + 1e-9
    assert [f['key'] for f in res['replay']['facts']['floors']] == ['F1', 'F2', 'F3']


# ---------------------------------------------------------------------------------------------------- openings
def test_door_heads_name_then_floor_then_drawing_then_default(plan, scratch, fake_detector):
    fake_detector({'F1': plan_records()})
    res, _ = run_build(plan_settings([SHA[0]]), [one(plan)], scratch)
    d1, d2 = opening(res, 'F1-001'), opening(res, 'F1-002')
    assert (d1['head'], d1['headFrom']) == (3.1, 'name')                 # 920x920x3100: the run's last number
    assert (d2['head'], d2['headFrom']) == (3.1, 'most common')          # the drawing's most common named height
    assert res['report']['doorHeadsFrom']['F1-002'] == 'drawing'
    s = plan_settings([SHA[0]], doorHead=2.2)
    res, _ = run_build(s, [one(plan)], scratch / 'b')
    d1, d2 = opening(res, 'F1-001'), opening(res, 'F1-002')
    assert (d1['head'], d1['headFrom']) == (3.1, 'name')                 # its own name first
    assert (d2['head'], d2['headFrom']) == (2.2, 'floor')                # a typed floor head beats the drawing's names
    assert res['report']['doorHeadsFrom'] == {'F1-001': 'name', 'F1-002': 'floor', 'F1-004': 'floor'}


def test_head_in_name_reads_w_x_w_x_h_runs():
    V = Vocab({})
    assert head_in_name('Cavity slider 920x920x3100', 0.001, V) == pytest.approx(3.1)
    assert head_in_name('DOOR_GEN_SWING - 1000X2400 _black_', 0.001, V) == pytest.approx(2.4)
    assert head_in_name('Door 900x2100x50', 0.001, V) == pytest.approx(2.1)          # a depth last: the pair still reads
    assert head_in_name('Door plain', 0.001, V) is None
    assert head_in_name('Door 36x84', 0.0254, V) is None                           # 2-digit: not a size run


def test_either_kind_door_is_glazed_like_a_window(plan, scratch, fake_detector):
    fake_detector({'F1': plan_records()})
    res, _ = run_build(plan_settings([SHA[0]]), [one(plan)], scratch)
    o = opening(res, 'F1-004')
    assert o['kind'] == 'door' and o['eitherKind'] is True
    pane = parts(res, 'glass', 'F1-004 pane')
    assert pane and all(p['z0'] == 0.0 and p['z1'] == o['head'] for p in pane)
    assert not parts(res, 'glass', 'F1-001 pane')                         # a plain door gets none


def test_low_wall_window_gets_a_090_sill(plan, scratch, fake_detector):
    fake_detector({'F1': plan_records()})
    res, _ = run_build(plan_settings([SHA[0]]), [one(plan)], scratch)
    o = opening(res, 'F1-005')
    assert o['sill'] == 0.9 and o['curtain'] is False
    sill = parts(res, 'sill', 'F1-005')
    assert sill and all(p['z1'] == 0.9 for p in sill)
    w = opening(res, 'F1-003')                                           # glass drawn in the gap: a curtain-wall window
    assert w['sill'] == 0.0


def test_floor_window_defaults_replace_the_project_defaults(plan, scratch, fake_detector):
    recs = [r for r in plan_records() if r['id'] == 'F1-005']
    recs[0]['subtype'] = 'fixed'
    fake_detector({'F1': recs})
    res, _ = run_build(plan_settings([SHA[0]], windowSill=0.0, windowHead=2.6), [one(plan)], scratch)
    o = opening(res, 'F1-005')
    assert (o['sill'], o['head']) == (0.0, 2.6)
    res, _ = run_build(plan_settings([SHA[0]]), [one(plan)], scratch / 'b')
    o = opening(res, 'F1-005')
    assert (o['sill'], o['head']) == (0.9, 2.1)


def test_screen_is_glass_never_cut(plan, scratch, fake_detector):
    fake_detector({'F1': plan_records()})
    res, _ = run_build(plan_settings([SHA[0]], heights=[3.5]), [one(plan)], scratch)
    scr = parts(res, 'glass', 'screen')
    assert len(scr) == 1
    ox, oy = res['model']['offset']
    x0, y0, x1, y1 = Polygon(scr[0]['o']).bounds
    assert (x0 + ox, x1 + ox) == pytest.approx((3.5, 5.5), abs=0.01)       # unbroken across door 1's footprint
    assert scr[0]['z1'] == 3.5 and scr[0]['follow'] is True
    # door 1 still cut its wall
    assert opening(res, 'F1-001')['lintel'] == 'lintel'


def test_plinth_when_the_lowest_level_is_above_zero(plan, scratch, fake_detector):
    fake_detector({'F1': plan_records()})
    s = plan_settings([SHA[0]], levels=[0.9])
    res, _ = run_build(s, [one(plan)], scratch)
    slabs = parts(res, 'slab')
    assert slabs and all(p['z0'] == -0.9 and p.get('plinth') is True for p in slabs)
    assert list(slabs[0])[-1] == 'plinth'
    assert res['model']['floors'][0]['slabThickness'] == 0.9
    s['options']['plinth'] = 'off'
    res, _ = run_build(s, [one(plan)], scratch / 'b')
    slabs = parts(res, 'slab')
    assert all(p['z0'] == -0.25 and 'plinth' not in p for p in slabs)
    assert res['model']['floors'][0]['slabThickness'] == 0.25


def test_settings_numbers_are_coerced(plan, scratch, fake_detector):
    fake_detector({'F1': []})
    s = plan_settings([SHA[0]], levels=[0], heights=[3])
    s['defaults'] = {k: int(v) if float(v).is_integer() else v for k, v in s['defaults'].items()}
    res, _ = run_build(s, [one(plan)], scratch)
    f = res['model']['floors'][0]
    assert type(f['level']) is float and type(f['wallHeight']) is float and type(f['slabThickness']) is float
    assert type(res['model']['singleLineHeight']) is float


# ---------------------------------------------------------------------------------------------------- parapets, probes
def test_parapets_auto_runs_only_where_walls_carry_solid_fills(plan, scratch, fake_detector):
    """U-10.5: the parapet rule (an unfilled wall piece whose ends both meet railings) runs only on a floor whose wall
    layers carry SOLID fills (Revit fills every wall it cuts); with pattern hatches or none, the low wall is a wall."""
    fake_detector({'F1': []})
    ox = lambda res: res['model']['offset'][0]                                    # noqa: E731
    low = lambda res, kind: [p for p in parts(res, kind) if Polygon(p['o']).bounds[0] + ox(res) > 16.9]  # noqa: E731
    res, _ = run_build(plan_settings([SHA[0]]), [one(plan, 'extras')], scratch / 'solid')
    assert len(low(res, 'parapet')) == 1 and not low(res, 'wall')
    assert low(res, 'parapet')[0]['z1'] == 1.1 and low(res, 'parapet')[0]['follow'] is False
    res, _ = run_build(plan_settings([SHA[0]]), [one(plan, 'pattern')], scratch / 'pattern')
    assert res['report']['summary']['floors']['F1']['wallSources']['fills'] == 9          # the fills are read ...
    assert not low(res, 'parapet') and len(low(res, 'wall')) == 1                          # ... but none is solid
    s = plan_settings([SHA[0]])
    s['options']['parapets'] = 'off'
    res, _ = run_build(s, [one(plan, 'extras')], scratch / 'off')
    assert not parts(res, 'parapet') and len(low(res, 'wall')) == 1


def test_a_glass_probe_with_no_floor_on_either_side_is_left_out(plan, scratch, fake_detector):
    """The model schema wants a probe's `inside` to name a side (the walk test walks at the glass from there): glass
    standing alone, away from every floor plate, is built but gets no probe."""
    fake_detector({'F1': plan_records()})
    res, logs = run_build(plan_settings([SHA[0]]), [one(plan, 'extras')], scratch)
    ox, oy = res['model']['offset']
    alone = [p for p in parts(res, 'glass') if Polygon(p['o']).bounds[0] + ox > 21.9]
    assert len(alone) == 1
    assert res['model']['probes'] and all(p['inside'] for p in res['model']['probes'])
    assert not any(p['x'] + ox > 21.9 for p in res['model']['probes'])
    assert any('1 glass probe(s) with no floor on either side left out' in m for m in logs)


def test_a_door_with_nothing_above_its_head_has_no_lintel_top(plan, scratch, fake_detector):
    """The schema's lintelTop is a number or absent: a door whose head reaches the wall top has neither a lintel nor a
    lintelTop (the prototype wrote null there; no bank door has it)."""
    fake_detector({'F1': plan_records()})
    res, _ = run_build(plan_settings([SHA[0]], doorHead=3.0), [one(plan)], scratch)
    d1, d2 = opening(res, 'F1-001'), opening(res, 'F1-002')
    assert (d1['head'], d1['headFrom'], d2['head'], d2['headFrom']) == (3.1, 'name', 3.0, 'floor')
    for d in (d1, d2):
        assert d['lintel'] is None and 'lintelTop' not in d
        assert list(d)[list(d).index('lintel') + 1] == 'glassDoor'              # the other keys keep their order
    res, _ = run_build(plan_settings([SHA[0]], heights=[3.5]), [one(plan)], scratch / 'b')
    d2 = opening(res, 'F1-002')
    assert (d2['head'], d2['lintel'], d2['lintelTop']) == (3.1, 'lintel', 3.5)


def test_a_part_whose_hole_touches_its_outline_is_cut_for_max():
    """The 3ds Max script cannot extrude a part with a hole touching its outline or another hole (the tower: one wall
    network per floor): such a part is cut in two through that hole; any other part is as it was."""
    from shapely.geometry import LinearRing
    from walkthrough_builder.build.model import max_safe

    def problems(rs):
        out = 0
        for r in rs:
            outer, holes = LinearRing(r['o']), [LinearRing(h) for h in r['h']]
            out += sum(h.distance(outer) < 5e-4 for h in holes)
            out += sum(holes[i].distance(holes[j]) < 5e-4 for i in range(len(holes)) for j in range(i + 1, len(holes)))
        return out
    area = lambda rs: sum(Polygon(r['o'], r['h']).area for r in rs)          # noqa: E731
    sq = [[0.0, 0.0], [4.0, 0.0], [4.0, 4.0], [0.0, 4.0]]
    fine = {'o': sq, 'h': [[[1.0, 1.0], [1.0, 2.0], [2.0, 2.0], [2.0, 1.0]]]}
    assert max_safe([fine], 0.002) == [fine] and max_safe([fine], 0.002)[0] is fine
    touch = {'o': sq, 'h': [[[1.5, 1.0], [2.0, 0.0], [2.5, 1.0], [2.0, 2.0]]]}               # a corner on the outline
    assert Polygon(touch['o'], touch['h']).is_valid and problems([touch]) == 1
    cut = max_safe([touch], 0.002)
    assert len(cut) == 2 and problems(cut) == 0 and area(cut) == pytest.approx(area([touch]), abs=1e-4)
    assert all(Polygon(r['o'], r['h']).is_valid for r in cut)
    pair = {'o': sq, 'h': [[[1.0, 1.0], [1.0, 2.0], [2.0, 2.0], [2.0, 1.0]], [[2.0, 2.0], [2.0, 3.0], [3.0, 3.0], [3.0, 2.0]]]}
    assert Polygon(pair['o'], pair['h']).is_valid and problems([pair]) == 1      # two holes meeting at a corner
    cut = max_safe([pair], 0.002)
    assert problems(cut) == 0 and area(cut) == pytest.approx(area([pair]), abs=1e-4)
    assert all(Polygon(r['o'], r['h']).is_valid for r in cut)


# ---------------------------------------------------------------------------------------------------- set-aside
def _item(plan, which, pred):
    return next(d for d in plan[which]['W']['items'] if pred(d))


def _ref(d, sha, k=1.0 / 1.0, floor='F1', element_insert=None):
    path = N.split_path(d['path']) + ([d['name']] if d['t'] == 'INSERT' else [])
    return {'floor': floor, 'source': sha, 'key': d['k'], 'sig': K.sig(d, k), 'rsig': K.rsig(d, element_insert, k),
            'elementId': N.element_id(path), 'layer': d['lay'], 'note': ''}


def test_set_aside_by_key_goes_before_pairing_and_detection(plan, scratch, fake_detector):
    fake = fake_detector({'F1': []})
    wall = _item(plan, 'base', lambda d: d['t'] == 'HATCH' and d['lay'] == 'A-WALL')
    res0, _ = run_build(plan_settings([SHA[0]]), [one(plan)], scratch / 'a')
    area0 = sum(Polygon(p['o'], p['h']).area for p in parts(res0, 'wall'))
    s = plan_settings([SHA[0]])
    s['fixes']['setAside'] = [_ref(wall, SHA[0])]
    res, _ = run_build(s, [one(plan)], scratch / 'b')
    assert res['report']['fixes']['setAside'] == [{'fix': 0, 'matchedBy': 'key', 'items': 1, 'ambiguous': 0, 'key': wall['k']}]
    assert wall['k'] not in {d.get('k') for d in fake.items['F1']}                # the detector never saw it
    area = sum(Polygon(p['o'], p['h']).area for p in parts(res, 'wall'))
    assert area == pytest.approx(area0 - 4.0 * 0.2, abs=0.05)                   # the 4 m x 0.2 m fill is gone


def test_set_aside_an_insert_removes_its_subtree(plan, scratch, fake_detector):
    fake_detector({'F1': []})
    group = _item(plan, 'base', lambda d: d['t'] == 'INSERT' and d['name'] == 'FurnGroup')
    res0, _ = run_build(plan_settings([SHA[0]]), [one(plan)], scratch / 'a')
    s = plan_settings([SHA[0]])
    s['fixes']['setAside'] = [_ref(group, SHA[0])]
    res, _ = run_build(s, [one(plan)], scratch / 'b')
    n_sub = sum(1 for d in plan['base']['W']['items'] if d['k'].startswith(group['k'] + '/'))
    row = res['report']['fixes']['setAside'][0]
    assert row['matchedBy'] == 'key' and row['items'] == 1 + n_sub
    fams0 = collections.Counter(p['family'] for p in res0['model']['furniture'])
    fams = collections.Counter(p['family'] for p in res['model']['furniture'])
    assert fams0['Chair-Mollie'] == 2 and fams['Chair-Mollie'] == 0 and fams['Desk 1600x800'] == 1


def test_set_aside_matches_a_reexported_element_by_id_and_rsig(plan, scratch, fake_detector):
    fake = fake_detector({'F1': []})
    items = plan['base']['W']['items']
    by_key = {d['k']: d for d in items}
    line = _item(plan, 'base', lambda d: d['t'] == 'LINE' and d['path'].endswith('Chair-Mollie-1234567-Level 1'))
    chair = by_key['/'.join(line['k'].split('/')[:2])]
    assert chair['t'] == 'INSERT' and chair['sx'] * chair['sy'] > 0
    ref = _ref(line, SHA[0], element_insert=chair)
    assert ref['elementId'] == '1234567' and ref['rsig']
    s = plan_settings([SHA[1]])
    s['fixes']['setAside'] = [ref]
    res, _ = run_build(s, [one(plan, 'reexport', SHA[1])], scratch)
    row = res['report']['fixes']['setAside'][0]
    assert row['matchedBy'] == 'element' and row['items'] == 1 and row['key'] != line['k']
    moved = [d for d in fake.items['F1'] if d['lay'] == 'I-FURN' and d['t'] == 'LINE']
    assert len(moved) == 1                                                       # the mirrored chair's line stays


def test_the_matcher_reads_each_item_as_the_plan_geometry_does(plan):
    """A-4 from the builder's side: the sig, rsig and element id the matcher compares are the reader's own
    (plangeom.refs, what the plan entries carry and the browser copies into an ItemRef), and the matcher's own rule
    (used when the reader's module cannot be imported) gives the same values."""
    from walkthrough_builder import plangeom
    from walkthrough_builder.build.fixes import SourceIndex
    for which in ('base', 'reexport'):
        items = plan[which]['W']['items']
        ix = SourceIndex(items, 1.0)
        want = plangeom.refs(items, 1.0)
        assert [ix.ref(i) for i in range(len(items))] == [tuple(r) for r in want]
        assert [ix._own_ref(i) for i in range(len(items))] == [tuple(r) for r in want]
        assert sum(1 for r in want if r[2]) >= 6 and sum(1 for r in want if r[1]) >= 6      # the chairs' lines have both


def test_set_aside_matches_by_sig_and_refuses_an_ambiguous_match(plan, scratch, fake_detector):
    fake = fake_detector({'F1': []})
    desk_ln = _item(plan, 'base', lambda d: d['path'] == 'Desk 1600x800')
    anno = _item(plan, 'base', lambda d: d['lay'] == 'A-ANNO')
    bogus = {'floor': 'F1', 'source': SHA[0], 'key': 'NOPE', 'sig': '000000000000', 'rsig': '', 'elementId': None,
             'layer': 'A-WALL', 'note': ''}
    s = plan_settings([SHA[1]])
    s['fixes']['setAside'] = [_ref(desk_ln, SHA[0]), _ref(anno, SHA[0]), bogus]
    res, _ = run_build(s, [one(plan, 'reexport', SHA[1])], scratch)
    rows = res['report']['fixes']['setAside']
    assert (rows[0]['matchedBy'], rows[0]['items']) == ('sig', 1)
    assert (rows[1]['matchedBy'], rows[1]['items'], rows[1]['ambiguous']) == (None, 0, 2)   # drawn twice: pick again
    assert (rows[2]['matchedBy'], rows[2]['items'], rows[2]['ambiguous']) == (None, 0, 0)   # unmatched
    assert sum(1 for d in fake.items['F1'] if d['lay'] == 'A-ANNO') == 2
    assert not any(p['family'] == 'Desk 1600x800' for p in res['model']['furniture'])


# ---------------------------------------------------------------------------------------------------- opening fixes
def test_opening_fixes_change_kind_and_head_or_drop(plan, scratch, fake_detector):
    fake_detector({'F1': plan_records()})
    s = plan_settings([SHA[0]])
    s['fixes']['openings'] = [
        {'floor': 'F1', 'a': [3.52, 5.9], 'b': [1.98, 5.9], 'kind': 'door', 'head': 2.5, 'sill': None},     # ends, either order
        {'floor': 'F1', 'a': [0.12, 2.2], 'b': [0.12, 2.8], 'kind': 'none', 'head': None, 'sill': None},    # on its line
        {'floor': 'F1', 'a': [20.0, 20.0], 'b': [21.0, 20.0], 'kind': 'door', 'head': None, 'sill': None},  # nothing there
    ]
    res, _ = run_build(s, [one(plan)], scratch)
    o = opening(res, 'F1-003')
    assert (o['kind'], o['head'], o['headFrom']) == ('door', 2.5, 'fix')
    assert opening(res, 'F1-005') is None and not parts(res, 'sill', 'F1-005')
    assert res['report']['fixes']['openings'] == [{'fix': 0, 'matched': 'F1-003'}, {'fix': 1, 'matched': 'F1-005'},
                                                  {'fix': 2, 'matched': None}]
    det = {r['record']['id']: r for r in res['detector']['F1']}
    assert det['F1-005']['modelId'] is None and det['F1-005']['fix'] == 1
    assert det['F1-003']['modelId'] == 'F1-003' and det['F1-003']['record']['kind'] == 'window'   # the record as detected
    assert det['F1-001']['fix'] is None


# ---------------------------------------------------------------------------------------------------- outline edges
def test_outline_suggestions_and_an_accepted_edge(plan, scratch, fake_detector):
    fake_detector({'F1': []})
    s = plan_settings([SHA[0]])
    s['options']['outlineWalls'] = 'suggest'
    res, _ = run_build(s, [one(plan)], scratch / 'a')
    sg = res['report']['floors']['F1']['outlineSuggestions']
    assert len(sg) == 3 and all(x['kind'] == 'wall' and x['state'] == 'open' for x in sg)
    assert sum(x['length'] for x in sg) == pytest.approx(4.0 + 2 * 3.65, abs=0.02)
    east = next(x for x in sg if abs(x['edge'][0][0] - 14.0) < 1e-6 and abs(x['edge'][1][0] - 14.0) < 1e-6)
    walls0 = len(parts(res, 'wall'))
    s['fixes']['outlineEdges'] = [{'floor': 'F1', 'a': east['edge'][1], 'b': east['edge'][0], 'as': 'wall'},
                                  {'floor': 'F1', 'a': [30.0, 0.0], 'b': [31.0, 0.0], 'as': 'wall'}]
    res, _ = run_build(s, [one(plan)], scratch / 'b')
    assert res['report']['fixes']['outlineEdges'] == [{'fix': 0, 'matched': True}, {'fix': 1, 'matched': False}]
    sg = res['report']['floors']['F1']['outlineSuggestions']
    assert sorted(x['state'] for x in sg) == ['accepted', 'open', 'open']
    ox = res['model']['offset'][0]
    new = [p for p in parts(res, 'wall') if Polygon(p['o']).bounds[0] + ox > 13.9]
    assert len(parts(res, 'wall')) == walls0 + 1 and len(new) == 1
    x0, _, x1, _ = Polygon(new[0]['o']).bounds
    assert (x0 + ox, x1 + ox) == pytest.approx((14.0, 14.2), abs=0.005)            # 0.20 m, away from the room


# ---------------------------------------------------------------------------------------------------- errors
def test_errors_are_typed(plan, scratch, fake_detector):
    fake_detector({'F1': [], 'F2': []})
    s = plan_settings([SHA[0]])
    s['floors'][0]['area'] = {'kind': 'box', 'bbox': [50.0, 50.0, 60.0, 60.0], 'pad': 0.5, 'match': 'all'}
    with pytest.raises(BuildError) as e:
        run_build(s, [one(plan)], scratch)
    assert e.value.code == 'area_empty' and 'Floor 1' in e.value.message
    s = plan_settings([SHA[0], SHA[1]], levels=[3.0, 3.0])
    with pytest.raises(BuildError) as e:
        run_build(s, [one(plan), one(plan, 'base', SHA[1])], scratch / 'c')
    assert e.value.code == 'bad_settings'
    s = plan_settings([SHA[0]])
    s['floors'] = []
    with pytest.raises(BuildError) as e:
        run_build(s, [one(plan)], scratch / 'd')
    assert e.value.code == 'no_floors'
    s = plan_settings([SHA[0]])
    s['vocabulary'] = {'stairUp': '(UP'}
    with pytest.raises(BuildError) as e:
        run_build(s, [one(plan)], scratch / 'e')
    assert e.value.code == 'bad_settings' and 'stairUp' in e.value.message
    assert BuildError('area_empty', 'x', 'align').record() == {'code': 'area_empty', 'message': 'x', 'step': 'align'}


def test_items_cache_is_only_ever_a_pickle_of_ours(scratch):
    from walkthrough_builder.build.items import load_cache
    p = scratch / 'items.pkl'
    p.write_bytes(pickle.dumps(['not', 'a', 'cache']))
    with pytest.raises(ValueError):
        load_cache(p)
