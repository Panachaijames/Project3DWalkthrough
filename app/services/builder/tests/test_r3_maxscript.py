"""R3: the 3ds Max script of a BuiltModel v2 (docs/rooms/DESIGN.md R-10; ACCEPTANCE 2.1 R3, RA-11).

* the two goldens (`bank-27oct`, `hotel-2nov`) stay byte for byte: nothing of v2 is written without v2 parts;
* the kinds `tread`, `landing`, `ceiling`: one case line and one material each, only when the model uses them;
* one storey statement after each part call of a stair's part (treads, landings, the walls cut under a flight), never
  inside `__PX___part` (the part function is the golden's, line for line);
* `__STOREYFIT__` inside "Update levels and heights", there with treads and gone without;
* the Ceilings layers hidden after the parts, the window's two lines and the upload profile's `stairs` and `ceilings`
  notes, the stair sentence;
* no Poly anywhere: every part through the part function (spline + Extrude, mesh output);
* the mock 3ds Max (furniture/fixtures/maxscript_mock.py, loaded by path, never changed) runs Build on the reference
  building and on the stair models, then "Update levels and heights" with REAL Extrude amounts: a stair's parts scale
  with their storey, the rest as before. The mock knows no Extrude amount and no layer visibility, so this test gives it
  both for its own run (monkeypatched, put back after the test): a stand-in Extrude with an `amount`, and a layer's
  `isHidden`.
"""
from __future__ import annotations

import copy
import json
import re

import pytest

import test_u4_common as c
from walkthrough_builder.out import maxscript as ms

REF = c.MODELS / 'rooms-reference.model.json'
STAIRS = [c.MODELS / f'stairs-{v}.model.json' for v in ('straight', 'L', 'U')]


def gen(model, profile='upload', **kw) -> bytes:
    raw = model if isinstance(model, bytes) else json.dumps(model, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    kw.setdefault('date', '11 Nov 2026')
    return ms.maxscript(raw, ms.load_profile(profile), **kw)


def lines(b: bytes) -> list[str]:
    return b.decode('ascii').split('\r\n')[:-1]


def ref_model() -> dict:
    return json.loads(REF.read_bytes())


def without_stairs(m: dict) -> dict:
    """The same model with no stair to climb: no treads, landings or cut pieces, `stairways` empty (still v2)."""
    m = copy.deepcopy(m)
    m['parts'] = [p for p in m['parts'] if p['kind'] not in ('tread', 'landing') and p.get('stair') is None]
    m['stairways'] = []
    return m


def function(text: list[str], name: str) -> list[str]:
    """The lines of `fn <name> ... = ( ... )` (from its fn line to the first line that is a lone ')')."""
    i = next(k for k, x in enumerate(text) if x.startswith(f'fn {name} '))
    j = next(k for k in range(i + 1, len(text)) if text[k] == ')')
    return text[i:j + 1]


# --------------------------------------------------------------------------------------------------------- the goldens
def test_the_goldens_do_not_move_and_carry_nothing_of_v2():
    bank = gen((c.MODELS / 'bank-v2.model.json').read_bytes(), 'bank-27oct', date=None)
    hotel = gen((c.MODELS / 'hotel.model.json').read_bytes(), 'hotel-2nov', date=None)
    assert c.sha1(bank) == c.BANK_MS_SHA1 and c.sha1(hotel) == c.HOTEL_MS_SHA1
    for b in (bank, hotel):
        t = b.decode('ascii')
        assert '_storey' not in t and 'Ceilings' not in t and 'note2' not in t and '#tread' not in t


def test_the_three_kinds_only_when_used():
    m = ref_model()
    text = lines(gen(m))
    px = m['maxPrefix']
    for kind, (layer, mat, colour) in ms.V2_KINDS.items():
        assert text.count(f'        #{kind}: #("{layer}", "{mat}")') == 1, kind
        assert text.count(f'    append {px}_mats (standardMaterial name:"{px} {mat}" {colour})') == 1, kind
    assert ms.V2_KINDS['ceiling'][2] == 'diffuse:(color 244 243 239)'
    assert ms.V2_KINDS['tread'][2] == ms.V2_KINDS['landing'][2] == 'diffuse:(color 185 199 180)'
    # a v2 model with ceilings but no stair: the ceiling case and material, none of the stair's
    t2 = lines(gen(without_stairs(m)))
    assert '        #ceiling: #("Ceilings", "Ceiling")' in t2
    assert not any('#tread:' in x or '#landing:' in x or '"RF Tread"' in x for x in t2)
    # and the kinds are counted as parts
    s = ms.summary(m, gen(m))
    assert s['parts'] == len(m['parts'])


def test_one_storey_statement_after_each_stair_part_and_none_inside_the_part_function():
    m = ref_model()
    text = lines(gen(m))
    px = m['maxPrefix']
    fi = {f['key']: i + 1 for i, f in enumerate(m['floors'])}
    to = {sw['id']: sw['to'] for sw in m['stairways']}
    calls = [i for i, x in enumerate(text) if x.startswith(f'    {px}_part #')]
    assert len(calls) == len(m['parts'])
    storey = [i for i, x in enumerate(text) if '_storey" ' in x]
    want = [p for p in m['parts'] if p.get('stair')]
    assert len(storey) == len(want) == 16, 'the 14 treads, the landing and the cut cupboard wall'
    for i, p in zip(calls, m['parts']):
        nxt = text[i + 1]
        if p.get('stair'):
            assert nxt == f'    setUserProp {px}_nodes[{px}_nodes.count] "{px}_storey" {fi[to[p["stair"]]]}', text[i]
        else:
            assert 'storey' not in nxt
    # the part function is the golden's, line for line (with the prefix and the v2 case lines aside)
    bank = lines(gen((c.MODELS / 'bank-v2.model.json').read_bytes(), 'bank-27oct', date=None))
    mine = [x.replace(f'{px}_', 'BB_') for x in function(text, f'{px}_part') if not re.match(r'^        #(tread|landing|ceiling):', x)]
    assert mine == function(bank, 'BB_part')
    assert not any('storey' in x for x in function(text, f'{px}_part'))


def test_storeyfit_with_treads_and_not_without():
    m = ref_model()
    px = m['maxPrefix']
    upd = function(lines(gen(m)), f'{px}_updateLevels')
    assert f'        local up = getUserProp o "{px}_storey"' in upd
    assert '                local s = d1 / (d0 as float)' in upd
    assert upd.index(f'        local up = getUserProp o "{px}_storey"') < upd.index('        o.pos.z = newLevels[fi] + base')
    for other in (without_stairs(m), json.loads((c.MODELS / 'bank-v2.model.json').read_bytes())):
        t = lines(gen(other))
        assert not any('storey' in x or 'STOREYFIT' in x for x in t)
        p = other.get('maxPrefix', 'M')
        bank_upd = function(lines(gen((c.MODELS / 'bank-v2.model.json').read_bytes(), 'bank-27oct', date=None)), 'BB_updateLevels')
        assert [x.replace(f'{p}_', 'BB_') for x in function(t, f'{p}_updateLevels')] == bank_upd


def test_ceilings_hidden_the_window_and_the_notes():
    m = ref_model()
    px = m['maxPrefix']
    text = lines(gen(m))
    last_part = max(i for i, x in enumerate(text) if x.startswith(f'    {px}_part #') or '_storey" ' in x)
    assert text[last_part + 1:last_part + 6] == [
        f'    for f in {px}_floorNames do', '    (', f'        local ly = LayerManager.getLayerFromName ("{px}_" + f + "_Ceilings")',
        '        if ly != undefined do ly.isHidden = true', '    )']
    assert f'    label note2 "Ceilings are on hidden layers {px}_<level>_Ceilings:" align:#left' in text
    assert '    label note3 "switch them on for interior views." align:#left' in text
    head = text[:text.index(f'global {px}_UI')]
    assert '-- Stairs: 16 risers of 0.188 m, 14 treads and 1 landing.' in head
    assert any(x.startswith(f'-- Ceilings are on hidden layers {px}_<level>_Ceilings: switch them on for interior views.') for x in head)
    assert any(f'user property {px}_storey' in x for x in head)
    # the keep sentence no longer says the treads keep their heights
    assert not any('treads at their own' in x or 'the stair treads' in x for x in head)
    # without ceilings and stairs: none of it
    m2 = without_stairs(m)
    m2['parts'] = [p for p in m2['parts'] if p['kind'] != 'ceiling']
    t2 = lines(gen(m2))
    assert not any('Ceilings' in x or 'Stairs:' in x or 'storey' in x or 'note2' in x for x in t2)


def test_the_stair_sentence_counts_each_stairway():
    m = ref_model()
    assert ms.stair_sentence(m, m['floors']) == 'Stairs: 16 risers of 0.188 m, 14 treads and 1 landing'
    two = copy.deepcopy(m)
    two['floors'].append({**two['floors'][1], 'key': 'roof', 'name': 'Roof', 'level': 6.0})
    sw = {**two['stairways'][0], 'id': 'S2', 'from': 'upper', 'to': 'roof'}
    two['stairways'].append(sw)
    two['parts'].append({**next(p for p in two['parts'] if p['kind'] == 'tread'), 'floor': 'upper', 'stair': 'S2'})
    assert ms.stair_sentence(two, two['floors']) == ('Stairs: Ground floor to Upper floor, 16 risers of 0.188 m, 14 treads and 1 '
                                                     'landing; Upper floor to Roof, 16 risers of 0.188 m, 1 tread')
    assert ms.stair_sentence(without_stairs(m), m['floors']) is None
    assert ms._scale_texts(without_stairs(m), m['floors'])['STAIRTXT'] == 'no dimension'


def test_a_stair_part_whose_stairway_is_unknown_is_refused():
    m = ref_model()
    next(p for p in m['parts'] if p['kind'] == 'tread')['stair'] = 'S9'
    with pytest.raises(ms.MaxScriptRefused, match='rises to no floor'):
        gen(m)


POLY = re.compile(r'editable_?poly|edit_?poly|converttopoly|polyop|poly_', re.I)


@pytest.mark.parametrize('path', [REF, *STAIRS], ids=lambda p: p.stem)
def test_no_poly_anywhere_and_every_part_through_the_part_function(path):
    m = json.loads(path.read_bytes())
    text = lines(gen(m))
    code = [x for x in text if not x.startswith('--')]
    assert not [x for x in code if POLY.search(x)]
    assert '    addModifier o (Extrude amount:ht segs:1 capStart:true capEnd:true output:1 smooth:false)' in text
    assert sum(1 for x in text if x.startswith(f'    {m["maxPrefix"]}_part #')) == len(m['parts'])
    assert not any(re.search(r'\b(box|cylinder|plane|editable_mesh)\s', x, re.I) for x in code
                   if x.startswith(f'    {m["maxPrefix"]}_part') or '_storey' in x)


# ------------------------------------------------------------------------------------------------------ the mock Max
class Extrude:
    """The stand-in of an Extrude modifier in the mock: its amount, readable and settable."""

    def __init__(self, amount: float) -> None:
        self.amount = float(amount)


def _mock_with_amounts(monkeypatch):
    loaded = c.mock()
    if loaded is None:
        pytest.skip('furniture/fixtures/maxscript_mock.py is not there (prototype folder)')
    mk, lite = loaded
    get0, set0 = mk.getprop, mk.setprop

    def getprop(obj, name):
        if isinstance(obj, Extrude) and name == 'amount':
            return obj.amount
        if isinstance(obj, mk.Layer) and name == 'ishidden':
            return getattr(obj, 'hidden', False)
        return get0(obj, name)

    def setprop(obj, name, val):
        if isinstance(obj, Extrude) and name == 'amount':
            obj.amount = float(val)
            return
        if isinstance(obj, mk.Layer) and name == 'ishidden':
            obj.hidden = val
            return
        set0(obj, name, val)

    monkeypatch.setattr(mk, 'getprop', getprop)
    monkeypatch.setattr(mk, 'setprop', setprop)
    return mk, lite


def run_build(mk, text: str, m: dict, *, collapsed: set[int] = frozenset(), pre: dict | None = None):
    """Build in the mock: the part, lines and room functions are stand-ins (as test_u4_maxscript's), each part a node
    with a stand-in Extrude of the amount the real part function gives it (follow: its level's wall height - z0, else
    z1 - z0); the parts whose index is in `collapsed` have none (Editable Mesh). `pre`: the window's furniture controls,
    for a model with furniture (the build handler's lines that read them run first, as in test_u4_maxscript)."""
    px = m['maxPrefix']
    it = mk.Interp(text)
    if pre:
        tl = text.split('\n')
        i = next(k for k, x in enumerate(tl) if x.startswith(f'        {px}_shift = if dwg.checked'))
        it.run('\n'.join(tl[i + 1:i + 4]), **pre)
    ext_cls = it.get('extrude')
    lv = lambda fi: it.get(f'{px}_levels')[fi - 1]                                         # noqa: E731
    ht = lambda fi: it.get(f'{px}_heights')[fi - 1]                                        # noqa: E731
    seen = []

    def node(cls, nm, fi, cc, z, base, **props):
        sh = it.get(f'{px}_shift')
        n = mk.Node(it.scene, mk.Cls(cls), nm)
        n.tm.rows[3] = mk.P(cc.v[0] - sh.v[0], cc.v[1] - sh.v[1], z)
        n.props.update({f'{px}_floor': str(fi), f'{px}_base': mk.tostr(base)})
        n.props.update(props)
        it.get(f'{px}_nodes').append(n)
        return n

    def part(it_, kind, nm, loops, z0, z1, follow, fi, cc, mn, mx):
        n = node('SplineShape', nm, fi, cc, lv(fi) + z0, z0, **{f'{px}_kind': str(kind), f'{px}_follow': mk.tostr(follow)})
        if len(seen) not in collapsed:
            n.modifiers = [Extrude((ht(fi) if follow else z1) - z0)]
        n.part = len(seen)
        seen.append(n)
        layer = it.call(f'{px}_layer', f'{px}_{it.get(f"{px}_floorNames")[fi - 1]}_' + {**dict(ms.KINDS), **{k: v[:2] for k, v in ms.OTHER_KINDS.items()}}[str(kind)][0])
        layer.add(n)
        return n

    it.override(f'{px}_part', part)
    it.override(f'{px}_lines', lambda it_, nm, segs, fi, cc, lay: node('SplineShape', nm, fi, cc, lv(fi), 0.0))
    it.override(f'{px}_room', lambda it_, nm, p, fi: node('Text', f'{px}_Room_{nm}', fi, p, lv(fi) + 0.02, 0.02))
    classof0 = mk.BUILTINS['classof']
    it.override('classof', lambda it_, v: ext_cls if isinstance(v, Extrude) else classof0(it_, v))
    it.set(f'{px}_shift', mk.P(0.0, 0.0))
    assert it.call(f'{px}_build') is True
    assert it.get(f'{px}_failed') == [] and any(x.rstrip().endswith('0 failed checks') for x in it.scene.listener)
    return it, seen


@pytest.mark.parametrize('path', [REF, *STAIRS], ids=lambda p: p.stem)
def test_the_mock_builds_and_update_levels_scales_each_stair_with_its_storey(path, monkeypatch):
    mk, lite = _mock_with_amounts(monkeypatch)
    m = json.loads(path.read_bytes())
    px = m['maxPrefix']
    b = gen(m)
    text = b.decode('ascii').replace('\r\n', '\n')
    assert lite.lint(text) == [] and lite.arity_errors(text) == []
    bank = gen((c.MODELS / 'bank-v2.model.json').read_bytes(), 'bank-27oct', date=None).decode('ascii').replace('\r\n', '\n')
    assert {w.lower() for w in lite.unresolved(text)} <= {w.lower() for w in lite.unresolved(bank)}
    collapsed = {next(i for i, p in enumerate(m['parts']) if p['kind'] == 'tread')}          # one tread collapsed already
    it, seen = run_build(mk, text, m, collapsed=collapsed)
    fi = {f['key']: i + 1 for i, f in enumerate(m['floors'])}
    to = {sw['id']: sw['to'] for sw in m['stairways']}
    # the storey on every stair's part, and nothing else carries one
    for n, p in zip(seen, m['parts']):
        assert n.props.get(f'{px}_storey') == (str(fi[to[p['stair']]]) if p.get('stair') else None), n.name
    # the Ceilings layers are hidden, every other layer is not
    layers = it.scene.layers
    ceil = [ly for name, ly in layers.items() if name.endswith('_ceilings')]
    assert ceil and all(getattr(ly, 'hidden', False) is True for ly in ceil)
    assert not any(getattr(ly, 'hidden', False) for name, ly in layers.items() if not name.endswith('_ceilings'))
    assert {n.layer.name for n, p in zip(seen, m['parts']) if p['kind'] == 'ceiling'} == {ly.name for ly in ceil}
    # "Update levels and heights": the upper level 0.60 m higher and 0.10 m more of wall
    levels0 = list(it.get(f'{px}_levels'))
    heights0 = list(it.get(f'{px}_heights'))
    new_levels = [levels0[0] + 0.25] + [v + 0.85 for v in levels0[1:]]
    new_heights = [h + 0.1 for h in heights0]
    before = {n.part: (n.tm.rows[3].v[2], n.modifiers[0].amount if n.modifiers else None) for n in seen}
    r = it.call(f'{px}_updateLevels', list(new_levels), list(new_heights))
    n_follow = sum(1 for p in m['parts'] if p.get('follow'))
    assert r == [n_follow, 1], 'every follow part set; the collapsed tread kept its height'
    for n, p in zip(seen, m['parts']):
        f = fi[p['floor']]
        z0 = p['z0'] if not (p.get('plinth') and p['kind'] == 'slab') else -m['floors'][f - 1]['level']
        z, amount = n.tm.rows[3].v[2], (n.modifiers[0].amount if n.modifiers else None)
        if p.get('stair'):
            u = fi[to[p['stair']]]
            s = (new_levels[u - 1] - new_levels[f - 1]) / (levels0[u - 1] - levels0[f - 1])
            assert z == pytest.approx(new_levels[f - 1] + z0 * s, abs=2e-5), n.name
            if amount is not None:
                assert amount == pytest.approx((p['z1'] - z0) * s, abs=1e-9), n.name
                assert z + amount == pytest.approx(new_levels[f - 1] + p['z1'] * s, abs=2e-5), 'its top scales too'
            assert float(n.props[f'{px}_base']) == pytest.approx(z0 * s, abs=2e-5)
        elif p.get('follow'):
            assert z == pytest.approx(new_levels[f - 1] + z0, abs=1e-9) and amount == pytest.approx(new_heights[f - 1] - z0)
        else:
            assert z == pytest.approx(new_levels[f - 1] + z0, abs=1e-9) and amount == before[n.part][1], n.name
    # the stair's top tread still meets the floor above (within the lap under the slab)
    top = max((n for n, p in zip(seen, m['parts']) if p['kind'] == 'tread' and n.modifiers), key=lambda n: n.tm.rows[3].v[2])
    sw = m['stairways'][0]
    assert top.tm.rows[3].v[2] + top.modifiers[0].amount == pytest.approx(new_levels[fi[sw['to']] - 1] - sw['riser'] *
                                                                            (new_levels[fi[sw['to']] - 1] - new_levels[fi[sw['from']] - 1]) /
                                                                            (levels0[fi[sw['to']] - 1] - levels0[fi[sw['from']] - 1]), abs=0.02)
    # and back: the original amounts again
    it.call(f'{px}_updateLevels', list(levels0), list(heights0))
    for n in seen:
        z, amount = before[n.part]
        assert n.tm.rows[3].v[2] == pytest.approx(z, abs=5e-5), n.name
        if amount is not None:
            assert n.modifiers[0].amount == pytest.approx(amount, abs=1e-9), n.name
