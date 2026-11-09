"""U2: the reading step on synthetic drawings (docs/upload/DESIGN.md U-7.1, U-7.2, U-7.5, U-3.5; ACCEPTANCE A-4, A-7,
2.1 U2): the walk equals the vendored prims.py `_flatten` item for item, the nested keys, MemoryError and RecursionError
re-raised, plain failures, the three outputs (checked by the API's own check_file), the plan geometry round trip with
an anchor per INSERT at every depth and sig / rsig / eid per entry."""
from __future__ import annotations

import json
import math
import types

import pytest

import test_u2_kit as K
from walkthrough_builder import keys, names, plangeom
from walkthrough_builder import read as R

REVIT = 'Inner-1234567-Level 1'


def build_nested(doc, msp) -> None:
    for name in ('A-WALL', 'A-WALL-PATT', 'I-FURN', 'A-AREA-IDEN', 'A-DOOR'):
        doc.layers.add(name)
    inner = doc.blocks.new(REVIT)
    inner.add_line((0, 0), (500, 0))
    inner.add_arc((0, 0), 300, 0, 90)
    inner.add_circle((250, 250), 100, dxfattribs={'layer': 'A-DOOR'})
    inner.add_lwpolyline([(0, 0), (500, 0), (500, 400), (0, 400)], close=True)
    outer = doc.blocks.new('Outer')
    outer.add_line((0, 0), (1000, 0))
    outer.add_blockref(REVIT, (100, 0))
    outer.add_text('in block', height=100).set_placement((10, 10))
    outer.add_attdef('TAG', (0, -200), dxfattribs={'height': 100})
    deep = [doc.blocks.new(f'Deep{i}') for i in range(11)]
    for i, b in enumerate(deep):
        b.add_line((0, 0), (10 * (i + 1), 0))
        if i + 1 < len(deep):
            b.add_blockref(f'Deep{i + 1}', (5, 5))
    twice = doc.blocks.new('Twice')
    twice.add_blockref('Outer', (0, 0))
    twice.add_blockref('Outer', (0, 3000), dxfattribs={'rotation': 30})

    msp.add_line((0, 0), (10000, 0), dxfattribs={'layer': 'A-WALL'})
    msp.add_text('LOBBY', height=250, dxfattribs={'layer': 'A-AREA-IDEN'}).set_placement((3000, 2600))
    msp.add_mtext('ROOM\\PNAME', dxfattribs={'layer': 'A-AREA-IDEN', 'char_height': 200}).set_location((3000, 1000))
    h = msp.add_hatch(dxfattribs={'layer': 'A-WALL-PATT'})
    h.set_solid_fill()
    h.paths.add_polyline_path([(0, 0), (1000, 0), (1000, 200), (0, 200)], is_closed=True)
    h.paths.add_polyline_path([(2000, 0), (3000, 0), (3000, 200), (2000, 200)], is_closed=True)
    ref = msp.add_blockref('Outer', (5000, 5000), dxfattribs={'layer': 'I-FURN'})
    ref.add_auto_attribs({'TAG': 'X1'})
    msp.add_blockref('Outer', (8000, 5000), dxfattribs={'layer': 'I-FURN', 'rotation': 90, 'yscale': -1})
    msp.add_blockref(REVIT, (0, 8000), dxfattribs={'layer': 'I-FURN', 'xscale': 2, 'yscale': 1})   # non-uniform
    mi = msp.add_blockref(REVIT, (0, 12000), dxfattribs={'layer': 'I-FURN'})
    mi.dxf.row_count, mi.dxf.column_count, mi.dxf.row_spacing, mi.dxf.column_spacing = 2, 2, 1000, 1000   # MINSERT
    msp.add_blockref('Deep0', (20000, 0), dxfattribs={'layer': 'A-WALL'})
    msp.add_blockref('Twice', (30000, 0), dxfattribs={'layer': 'I-FURN'})


@pytest.fixture(scope='module')
def nested(tmp_path_factory):
    d = tmp_path_factory.mktemp('nested')
    dxf = K.synthetic(d / 'nested.dxf', build_nested)
    return dxf, K.read(dxf, d / 'out')


def test_walk_equals_prims_item_for_item(nested) -> None:
    dxf, r = nested
    prims_items, prims_layers = K.prims_flatten(dxf)
    assert K.strip(r['items']) == K.strip(prims_items)
    assert r['cache']['layers'] == prims_layers
    assert all('area' not in d for d in r['items'])                         # areas are build settings (U-9.1)
    assert max(d['depth'] for d in r['items']) == 8                         # prims' depth limit


def test_keys_are_unique_and_nested_by_source_handles(nested) -> None:
    dxf, r = nested
    import ezdxf
    doc = ezdxf.readfile(dxf)
    items = r['items']
    ks = [d['k'] for d in items]
    assert len(set(ks)) == len(ks)
    msp = {e.dxf.handle: e for e in doc.modelspace()}
    tops = [d for d in items if d['depth'] == 0 and d['t'] != 'ATTRIB']
    assert all(d['k'] == d['h'] and d['k'] in msp for d in tops)            # top level: the entity's handle
    outer = next(d for d in tops if d['t'] == 'INSERT' and d['name'] == 'Outer' and d['sy'] > 0)
    blk = doc.blocks.get('Outer')
    line = next(e for e in blk if e.dxftype() == 'LINE')
    inner_ref = next(e for e in blk if e.dxftype() == 'INSERT')
    inner_line = next(e for e in doc.blocks.get(REVIT) if e.dxftype() == 'LINE')
    by_key = {d['k']: d for d in items}
    assert by_key[f'{outer["k"]}/{line.dxf.handle}']['t'] == 'LINE'
    assert by_key[f'{outer["k"]}/{inner_ref.dxf.handle}']['name'] == REVIT
    assert by_key[f'{outer["k"]}/{inner_ref.dxf.handle}/{inner_line.dxf.handle}']['depth'] == 2
    attrib = next(d for d in items if d['t'] == 'ATTRIB' and d['h'] == outer['h'] and d['depth'] == 0)
    ref = doc.entitydb[outer['h']]
    assert attrib['k'] == f'{outer["k"]}@{ref.attribs[0].dxf.handle}' and attrib['text'] == 'X1'
    # every key part is a handle of the drawing or ~<index>; every child key extends its parent's
    for d in items:
        parts = d['k'].split('@')[0].split('/')
        assert len(parts) == d['depth'] + 1
        assert all(p.split('~')[0] in doc.entitydb or p.startswith('~') for p in parts), d['k']
    # the non-uniformly scaled insert's arc and circle become ellipses with no source handle: ~<index>
    nonuni = next(d for d in tops if d['t'] == 'INSERT' and d['sx'] == 2.0)
    kids = [d for d in items if d['k'].startswith(nonuni['k'] + '/')]
    assert {d['t'] for d in kids if d['k'].split('/')[-1].startswith('~')} == {'ELLIPSE'}


def test_keys_are_stable_between_reads_and_saves(nested, tmp_path) -> None:
    dxf, r = nested
    import ezdxf
    again = tmp_path / 'resaved.dxf'
    ezdxf.readfile(dxf).saveas(again)                                     # the same entities, written again
    r2 = K.read(again, tmp_path / 'out')
    assert [d['k'] for d in r2['items']] == [d['k'] for d in r['items']]


def test_a_handle_met_twice_under_one_insert_gets_its_index() -> None:
    class Src:
        def __init__(self, h):
            self.dxf = types.SimpleNamespace(get=lambda k, default=None, h=h: h if k == 'handle' else default)

    class Ent:
        def __init__(self, src):
            self.dxf = types.SimpleNamespace(get=lambda k, default=None: None)
            self.source_of_copy = src
    seen: set[str] = set()
    parts = [R._part(Ent(Src('2A')), 0, seen), R._part(Ent(Src('2A')), 1, seen), R._part(Ent(None), 2, seen),
             R._part(Ent(Src('2B')), 3, seen)]
    assert parts == ['2A', '2A~1', '~2', '2B']


class _Path:
    """ezdxf.path with make_path raising `exc` for CIRCLEs (and working for everything else)."""

    def __init__(self, exc):
        import ezdxf.path as real
        self.real, self.exc = real, exc

    def __getattr__(self, name):
        return getattr(self.real, name)

    def make_path(self, e):
        if e.dxftype() == 'CIRCLE':
            raise self.exc
        return self.real.make_path(e)


def test_memory_error_is_raised_never_swallowed(nested, tmp_path, monkeypatch) -> None:
    dxf, _ = nested
    monkeypatch.setattr(R, 'ezpath', _Path(MemoryError()))
    with pytest.raises(MemoryError):
        R.read_source(dxf, None, tmp_path / 'out', source={'sha1': '0' * 40, 'name': 'nested.dxf'})


def test_recursion_error_fails_the_read_plainly(nested, tmp_path, monkeypatch) -> None:
    dxf, _ = nested
    monkeypatch.setattr(R, 'ezpath', _Path(RecursionError()))
    with pytest.raises(R.ReadFailed, match='nested too deeply'):
        R.read_source(dxf, None, tmp_path / 'out', source={'sha1': '0' * 40, 'name': 'nested.dxf'})


def test_other_errors_are_swallowed_and_counted(nested, monkeypatch) -> None:
    dxf, r = nested
    import ezdxf
    monkeypatch.setattr(R, 'ezpath', _Path(ValueError('broken')))
    W = R.walk_doc(ezdxf.readfile(dxf), 'mm')
    circles = sum(1 for d in r['items'] if d['t'] == 'CIRCLE')
    assert circles > 0 and W['errors'] == {'ValueError': circles}
    assert len(W['items']) == len(r['items']) - circles


@pytest.mark.parametrize('case, match', [
    ('text', 'cannot be read as a DXF'),
    ('empty', 'nothing in model space'),
    ('truncated', 'nothing in model space'),
    ('insert-layer', 'a layer name the reader cannot take'),
    ('missing', 'missing'),
])
def test_unreadable_drawings_fail_with_a_plain_sentence(case, match, tmp_path) -> None:
    small = K.small_dxf(tmp_path / 'small.dxf').read_bytes()
    data = {'text': b'hello, this is not a drawing\n', 'empty': b'', 'truncated': small[: len(small) // 3],
            'insert-layer': small.replace(b'I-FURN', b'I-FURN<x>'), 'missing': None}[case]
    p = tmp_path / 'case.dxf'
    if data is not None:
        p.write_bytes(data)
    with pytest.raises(R.ReadFailed, match=match) as err:
        R.read_source(p, None, tmp_path / 'out', source={'sha1': '0' * 40, 'name': 'Plan B.dwg'})
    msg = str(err.value)
    assert msg.startswith('Plan B.dwg: ') and str(tmp_path) not in msg and 'case.dxf' not in msg


@pytest.fixture(scope='module')
def small(tmp_path_factory):
    d = tmp_path_factory.mktemp('small')
    dxf = K.small_dxf(d / 'small.dxf')
    return dxf, K.read(dxf, d / 'out', name='Small test.dxf', sha1='a' * 40)


def test_read_result_and_its_three_files(small) -> None:
    dxf, r = small
    res = r['result']
    assert set(res) == {'items', 'drawing', 'plan', 'units', 'seconds'}
    assert sorted(p.name for p in r['out'].iterdir()) == ['drawing.json', 'items.pkl', 'plan.json.gz']
    assert res['units'] == r['drawing']['units'] and res['units']['used'] == 'mm'
    assert set(r['cache']) == {'items', 'layers', 'units'} and r['cache']['units'] == 'mm'
    assert K.strip(r['items']) == K.strip(K.prims_flatten(dxf)[0])
    assert r['drawing']['source'] == {'sha1': 'a' * 40, 'name': 'Small test.dxf'}
    assert r['plan']['source'] == 'a' * 40 and r['plan']['units'] == 'mm'
    assert any('Small test.dxf' in s for s in r['log']) and not any(str(r['out']) in s for s in r['log'])


def test_drawing_read_of_the_small_drawing(small) -> None:
    _, r = small
    dr = r['drawing']
    L = {la['name']: la for la in dr['layers']}
    assert L['A-WALL-PATT']['solidHatches'] == 5 and L['A-WALL-PATT']['byType'] == {'HATCH': 5}
    assert L['A-WALL']['pairs']['wallLike'] == 3 and L['A-WALL']['closedShapes'] == 5
    assert L['A-GLAZ']['pairs'] == {'glassLike': 1, 'wallLike': 0}
    assert (L['A-DOOR']['doorArcs'], L['A-DOOR']['doorArcsWithLeaf']) == (1, 1)
    assert L['I-FURN']['inserts'] == 4 and L['I-FURN']['inBlocks'] > 0
    assert {b['family']: b['count'] for b in L['I-FURN']['topBlocks']} == {'Chair-Mollie': 2, 'Desk 1600x800': 1,
                                                                            'FurnGroup': 1}
    assert L['A-AREA-IDEN']['texts'] == 2 and L['A-WALL']['normalised'] == 'A-WALL'
    assert L['S-GRID']['length'] == pytest.approx(2 * 8 + 2 * 14, abs=0.01)
    chair = next(b for b in dr['blocks'] if b['name'] == 'Chair-Mollie-1234567-Level 1')
    assert (chair['inserts'], chair['mirrored'], chair['maxDepth'], chair['family']) == (2, 1, 1, 'Chair-Mollie')
    assert [t['text'] for t in dr['texts']][:2] == ['OFFICE', 'LOBBY']
    assert {g['text']: g['direction'] for g in dr['gridLabels']} == {'1': [0.0, -1.0], '2': [0.0, -1.0],
                                                                     'A': [1.0, 0.0], 'B': [1.0, 0.0]}
    one = next(g for g in dr['gridLabels'] if g['text'] == '1')
    assert one['line'] == [[0.0, 6.0], [0.0, -2.0]] and one['layer'] == 'S-GRID-IDEN'
    assert dr['levelTags'] == []
    assert dr['counts']['items'] == len(r['items']) and dr['counts']['dimensions'] == 0
    x0, y0, x1, y1 = dr['extents']
    assert -2.8 <= x0 <= 0 and -2.1 <= y0 <= 0 and 10 <= x1 <= 12.1 and 4 <= y1 <= 6.8   # bubbles r 0.4 included
    assert dr['units']['verdict'] == 'declared-only' and dr['units']['votes']['mm'] == 1
    assert dr['reader']['version'] == '1' and dr['dxf']['insUnits'] == 4


def test_reads_are_deterministic(small, tmp_path) -> None:
    dxf, r = small
    r2 = K.read(dxf, tmp_path / 'again', name='Small test.dxf', sha1='a' * 40)
    assert (r2['out'] / 'plan.json.gz').read_bytes() == (r['out'] / 'plan.json.gz').read_bytes()
    a, b = dict(r['drawing']), dict(r2['drawing'])
    a.pop('reader'), b.pop('reader')
    assert a == b
    assert r2['items'] == r['items']


def independent_refs(items: list[dict], k: float) -> list[tuple]:
    """sig / rsig / element id per item, worked out from the key prefixes (the INSERTs around an item, innermost
    first, the item itself when it is one; an ATTRIB belongs to its INSERT), not through plangeom."""
    by_key = {d['k']: d for d in items if d['t'] == 'INSERT'}
    out = []
    for d in items:
        base = d['k'].split('@')[0]
        parts = base.split('/')
        around = [by_key.get('/'.join(parts[:j + 1])) for j in range(len(parts))]
        if d['t'] not in ('INSERT', 'ATTRIB'):
            around = around[:-1]
        eid, el = None, None
        for ins in reversed(around):
            if ins is not None and names.element_id_of(ins['name']) is not None:
                eid, el = names.element_id_of(ins['name']), ins
                break
        out.append((keys.sig(d, k), keys.rsig(d, el, k) if el is not None else '', eid))
    return out


def check_plan(items: list[dict], plan: dict, k: float) -> None:
    """Every entry against its cache item: points, types, anchors, sig / rsig / eid."""
    entries = plangeom.decode(plan)
    by_key: dict[str, list[dict]] = {}
    for e in entries:
        by_key.setdefault(e['key'], []).append(e)
    refs = dict(zip((d['k'] for d in items), independent_refs(items, k)))
    q = plan['quantum']
    assert q == 0.01 and all(isinstance(v, int) for v in plan['pts'][:1000])
    assert plan['origin'] == [float(math.floor(v)) for v in plan['origin']]
    inserts = 0
    for d in items:
        got = by_key.get(d['k'], [])
        sig, rsig, eid = refs[d['k']]
        for e in got:
            assert (e['sig'], e['rsig'], e['elementId']) == (sig, rsig, eid), d['k']
            assert e['layer'] == d['lay']
        if d['t'] == 'INSERT':
            inserts += 1
            assert [e['type'] for e in got] == [5]
            assert math.dist(got[0]['points'][0], (d['ins'][0] * k, d['ins'][1] * k)) <= q
        elif d['t'] in ('TEXT', 'MTEXT', 'ATTRIB'):
            assert [e['type'] for e in got] == [4]
        elif 'loops' in d:
            assert [e['type'] for e in got] == [2 if d['solid'] else 3] * len([lp for lp in d['loops'] if lp])
        else:
            assert len(got) == 1 and got[0]['type'] == (1 if d['closed'] else 0)
            P = [(x * k, y * k) for x, y in d['pts']]
            dec = got[0]['points']
            assert len(dec) <= len(P)
            assert math.dist(dec[0], P[0]) <= q
            if not d['closed']:                                     # a ring is written without its repeated last point
                assert math.dist(dec[-1], P[-1]) <= q
            if len(P) <= 400:                                       # each kept point lies on the drawn polyline
                from shapely.geometry import LineString, Point
                line = LineString(P) if len(P) > 1 else Point(P[0])
                assert all(line.distance(Point(p)) <= 0.0051 + q for p in dec), d['k']
    assert sum(1 for t in plan['items']['type'] if t == 5) == inserts
    eids = plan['elementIds']
    assert len(set(eids)) == len(eids)


def test_plan_geometry_round_trip_and_references(small, nested) -> None:
    for _, r in (small, nested):
        check_plan(r['items'], r['plan'], 1.0)
    _, r = nested
    eid_entries = [e for e in plangeom.decode(r['plan']) if e['elementId'] == '1234567']
    assert eid_entries and all(e['rsig'] for e in eid_entries)
    assert {e['type'] for e in eid_entries} >= {0, 1, 5}
    assert all(e['rsig'] == '' for e in plangeom.decode(r['plan']) if e['elementId'] is None)


def test_rsig_survives_moving_and_turning_the_element(nested) -> None:
    _, r = nested
    items = r['items']
    refs = dict(zip((d['k'] for d in items), plangeom.refs(items, 1.0)))
    # the same inner LINE under the plain Outer insert and under the mirrored-and-turned one: different sig, same rsig
    plain = next(d for d in items if d['t'] == 'INSERT' and d['name'] == 'Outer' and d['depth'] == 0 and d['sy'] > 0)
    turned = next(d for d in items if d['t'] == 'INSERT' and d['name'] == 'Outer' and d['depth'] == 0 and d['sy'] < 0)

    def inner_line(top):
        return next(d for d in items if d['t'] == 'LINE' and d['depth'] == 2 and d['k'].startswith(top['k'] + '/'))
    a, b = refs[inner_line(plain)['k']], refs[inner_line(turned)['k']]
    assert a[2] == b[2] == '1234567' and a[0] != b[0]
    # mirrored: the relative signature tells the drawn mirror image apart (U-11.7's drawnVariant is U3's)
    twice = [d for d in items if d['t'] == 'INSERT' and d['name'] == 'Outer' and d['depth'] == 1]
    assert len(twice) == 2
    x, y = refs[inner_line(twice[0])['k']], refs[inner_line(twice[1])['k']]
    assert x[1] == y[1] and x[0] != y[0]                                   # moved and turned 30 degrees: same rsig


def test_a_drawing_with_broken_coordinates_still_reads(tmp_path) -> None:
    small = K.small_dxf(tmp_path / 'small.dxf').read_bytes()
    # the stair's first tread (600, 600) - (1600, 600): its end x becomes NaN, its start y infinity
    nl = b'\r\n'                                                          # ezdxf writes CRLF on Windows
    assert nl.join([b' 11', b'1600.0', b' 21', b'600.0']) in small
    broken = small.replace(nl.join([b' 11', b'1600.0', b' 21', b'600.0', b'']),
                           nl.join([b' 11', b'nan', b' 21', b'600.0', b'']), 1)
    broken = broken.replace(nl.join([b' 10', b'600.0', b' 20', b'600.0', b'']),
                            nl.join([b' 10', b'600.0', b' 20', b'inf', b'']), 1)
    assert broken.count(b'nan') == 1 and broken.count(nl + b'inf' + nl) == 1
    p = tmp_path / 'broken.dxf'
    p.write_bytes(broken)
    r = K.read(p, tmp_path / 'out')
    bad = [d for d in r['items'] if d['t'] == 'LINE' and not all(math.isfinite(v) for q in d['pts'] for v in q)]
    assert len(bad) == 1 and bad[0]['k'] not in r['plan']['items']['key']
    json.dumps(r['drawing'], allow_nan=False)
    assert r['drawing']['extents'] is not None


def test_plan_drops_points_that_are_not_on_any_sheet() -> None:
    items = [{'t': 'LINE', 'lay': 'A', 'path': '', 'k': 'A1', 'pts': [[float('nan'), 0.0], [1.0, 1.0]], 'closed': False},
             {'t': 'LINE', 'lay': 'A', 'path': '', 'k': 'A2', 'pts': [[1e10, 0.0], [1.0, 1.0]], 'closed': False},
             {'t': 'LINE', 'lay': 'B', 'path': '', 'k': 'A3', 'pts': [[0.0, 0.0], [1.0, 1.0]], 'closed': False}]
    plan = plangeom.plan_geometry(items, source='0' * 40, units='mm', extents=[0.0, 0.0, 1.0, 1.0])
    assert plan['items']['key'] == ['A3'] and plan['layers'] == ['B'] and plan['pts'] == [0, 0, 100, 100]
    json.dumps(plan, allow_nan=False)


@pytest.fixture(scope='module')
def hostile(tmp_path_factory):
    d = tmp_path_factory.mktemp('hostile')
    dxf = K.small_dxf(d / 'hostile.dxf', 'hostile')
    return dxf, K.read(dxf, d / 'out', name="<img src=x onerror=alert(5)>.dxf")


def test_hostile_names_are_read_as_text(hostile) -> None:
    dxf, r = hostile
    assert K.strip(r['items']) == K.strip(K.prims_flatten(dxf)[0])
    dr = r['drawing']
    layers = {la['name'] for la in dr['layers']}
    assert 'A-WALL<img src=x onerror=alert(1)>' in layers and "A-DOOR</script><script>alert(2)</script>" in layers
    assert any(t['text'] == '<img src=x onerror=alert(4)>LOBBY' for t in dr['texts'])
    assert any(b['name'] == 'Desk<img src=x onerror=alert(3)> 1600x800' for b in dr['blocks'])
    assert dr['source']['name'] == '<img src=x onerror=alert(5)>.dxf'
    assert 'A-WALL<img src=x onerror=alert(1)>' in r['plan']['layers']


def test_outputs_pass_the_apis_record_checks(small, nested, hostile) -> None:
    files = []
    for _, r in (small, nested, hostile):
        files += [('drawing', r['out'] / 'drawing.json'), ('plan', r['out'] / 'plan.json.gz')]
    got = K.api_issues(files)
    assert got == {str(p): [] for _k, p in files}
