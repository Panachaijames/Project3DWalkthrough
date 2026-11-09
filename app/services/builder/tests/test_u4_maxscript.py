"""U4: the one 3ds Max generator (docs/upload/DESIGN.md U-11.5; ACCEPTANCE A-1's Max rows, A-2).

* the `bank-27oct` profile on the bank's v2 model gives `bank_test/Bangkok_Bank_Sampeng.ms` byte for byte, the `hotel-2nov`
  profile on `fixtures/models/hotel.model.json` gives `hotel_test/Hotel_Lobby.ms` byte for byte (its computed follow /
  keep, stair-width and lift-door sentences, tooltip, "Placed at" lines and datum Picture lines included);
* the `upload` profile on the bank's model equals the bank-profile script except the profile's lines, with line 2's stamp;
* the "two holes touch" refusal (and the bank's checks), every model;
* a synthetic model with every part kind (packages/viewer/test/fixtures/features.model.json minus fit / panels): CRLF, no
  placeholder left, a kind outside the bank's 11 adds exactly its case line and material, and the mock 3ds Max
  (furniture/fixtures/maxscript_mock.py, loaded by path) runs Build with no error and the expected object count;
* names: Thai falls back to ids, hostile text stays text (no placeholder is filled inside a drawing name).
"""
from __future__ import annotations

import copy
import difflib
import json
import re

import pytest

import test_u4_common as c
from walkthrough_builder.out import maxscript as ms

BANK_RAW = (c.MODELS / 'bank-v2.model.json').read_bytes()
HOTEL_RAW = (c.MODELS / 'hotel.model.json').read_bytes()


def gen(model, profile='upload', **kw) -> bytes:
    raw = model if isinstance(model, bytes) else json.dumps(model, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    kw.setdefault('date', '4 Nov 2026')
    return ms.maxscript(raw, ms.load_profile(profile), **kw)


def lines(b: bytes) -> list[str]:
    assert b.endswith(b'\r\n')
    text = b.decode('ascii')
    assert '\n' not in text.replace('\r\n', ''), 'a bare LF'
    assert '\r' not in text.replace('\r\n', ''), 'a bare CR'
    return text.split('\r\n')[:-1]


# ------------------------------------------------------------------------------------------------------------ goldens
def test_bank_profile_gives_the_bank_script_byte_for_byte():
    assert c.sha1(BANK_RAW) == c.BANK_MODEL_SHA1
    got = gen(BANK_RAW, 'bank-27oct', date=None)
    assert c.sha1(got) == c.BANK_MS_SHA1
    proto = c.PROJECT / 'bank_test' / 'Bangkok_Bank_Sampeng.ms'
    if proto.exists():
        assert got == proto.read_bytes()
    assert len(lines(got)) == 867


def test_hotel_profile_gives_the_hotel_script_byte_for_byte():
    got = gen(HOTEL_RAW, 'hotel-2nov', date=None)
    assert c.sha1(got) == c.HOTEL_MS_SHA1
    proto = c.PROJECT / 'hotel_test' / 'Hotel_Lobby.ms'
    if proto.exists():
        assert got == proto.read_bytes()
    text = lines(got)
    # the computed sentences of the hotel's header, its tooltip, "Placed at" lines and datum Picture lines
    assert "-- the main stair's width, 2.50 m between its side walls; Floor 1's picture is drawn wider than tall (a scale per axis)." in text
    assert any(x.startswith('-- Sizes are approximate: at that scale the 4 lift doors measure 1.12 to 1.28 m as drawn') for x in text)
    assert '-- "Update levels and heights" sets the tops of the walls, mullions, glass and lintels to their level\'s wall height and keeps' in text
    assert "-- Placed at the drawing's own coordinates in metres (0,0 is the lift core's north-west corner on both floors, y up)," in text
    assert sum(1 for x in text if x.startswith('    setUserProp origin "Picture_')) == 2
    assert any('tooltip:"Metres from the lift core' in x for x in text)


def test_follow_keep_sentences_are_computed_from_the_parts():
    m = json.loads(BANK_RAW)
    f, k = ms._follow_keep(m)
    order = list(dict.fromkeys(p['kind'] for p in m['parts']))
    states = {kind: {bool(p.get('follow')) for p in m['parts'] if p['kind'] == kind} for kind in order}
    want_f = [ms.PLURAL[x] + (' (those marked to)' if len(states[x]) > 1 else '') for x in order if True in states[x]]
    want_k = ['the ' + ms.PLURAL[x] for x in order if states[x] == {False}]
    assert f == ms.words(want_f) and k == ms.words(want_k)
    assert 'walls' in f and 'the slabs' in k
    one = {'parts': [{'kind': 'wall', 'follow': False, 'floor': 'L1'}]}
    assert ms._follow_keep(one) == ('no part', 'the walls')
    none = {'parts': []}
    assert ms._follow_keep(none) == ('no part', 'nothing else')


def test_stair_and_door_sentences():
    m = json.loads(BANK_RAW)
    t = ms._scale_texts(m, m['floors'])
    assert t['DOORTXT'] == 'no lift door was measured' and t['AXISTXT'] == ''
    h = json.loads(HOTEL_RAW)
    t = ms._scale_texts(h, h['floors'])
    assert t['STAIRTXT'] == "the main stair's width, 2.50 m between its side walls"
    assert t['DOORTXT'].endswith('they are built 1.00 m')


# -------------------------------------------------------------------------------------------------- the upload profile
REVIEWED = [re.compile(p) for p in (
    r'^    setUserProp origin "Source" "[^"]*"$', r'^    setUserProp origin "Built" "[^"]*"$',
    r'^    checkbox dwg "At the drawing\'s own coordinates" checked:true tooltip:"[^"]*"$',
    r'^rollout BB_UI "[^"]*" width:340$')]


def test_upload_profile_differs_from_the_bank_script_only_in_the_profile_lines():
    bank = lines(gen(BANK_RAW, 'bank-27oct', date=None))
    up = lines(gen(BANK_RAW, 'upload', date='4 Nov 2026', sources=[{'kind': 'dwg', 'units': 'mm'}] * 2,
                   converter={'name': 'libredwg', 'version': '0.14', 'exeSha1': '0' * 40}))
    assert 'model data c3a9408304a2' in up[1]
    gb, gu = bank.index('global BB_UI'), up.index('global BB_UI')
    assert all(x.startswith('--') for x in up[:gu])
    ops = [o for o in difflib.SequenceMatcher(None, bank[gb:], up[gu:], autojunk=False).get_opcodes() if o[0] != 'equal']
    loose = [bank[gb + i] for _, i1, i2, _, _ in ops for i in range(i1, i2) if not any(r.match(bank[gb + i]) for r in REVIEWED)]
    loose += [up[gu + j] for _, _, _, j1, j2 in ops for j in range(j1, j2) if not any(r.match(up[gu + j]) for r in REVIEWED)]
    assert not loose, loose
    head = '\r\n'.join(up[:gu])
    assert up[0] == ('-- BANGKOK BANK, SAMPENG BRANCH / built by the walkthrough app from "I1201 - LEVEL 1 GENERAL ARRANGEMENT.dwg + '
                     'I1202 - LEVEL 2 GENERAL ARRANGEMENT.dwg", 4 Nov 2026')
    assert '(TEST)' not in head and '(test)' not in '\r\n'.join(up)
    assert '-- The drawings were converted with LibreDWG 0.14; drawing units mm.' in up
    assert 'Glass partitions (Revit glass wall types)' in head                    # the bank has Revit glass wall types
    assert '"Update levels and heights" sets the tops of the' in head
    assert 'rollout BB_UI "Bank branch" width:340' in up
    assert '    setUserProp origin "Source" "I1201 - LEVEL 1 GENERAL ARRANGEMENT.dwg + I1202 - LEVEL 2 GENERAL ARRANGEMENT.dwg, ' \
           'converted with LibreDWG 0.14; drawing units mm, model in metres"' in up


def test_upload_profile_notes_and_dxf_sentence():
    m = json.loads(BANK_RAW)
    for p in m['parts']:
        if ms.is_revit_glass(p):
            p['label'] = None
    t = '\r\n'.join(lines(gen(m, sources=[{'kind': 'dxf', 'units': 'm'}])))
    assert 'Glass partitions' not in t
    assert 'DXF exported by its own program; drawing units m' in t


def test_upload_profile_needs_the_build_date():
    with pytest.raises(ValueError, match='date'):
        ms.maxscript(BANK_RAW, ms.load_profile('upload'))


def test_profiles_are_checked():
    p = ms.load_profile('upload')
    for broken in ({**p, 'tooltip': 'a "quote"'}, {**p, 'pictures': 'yes'}, {**p, 'extra': 1}, {**p, 'format': 'x'},
                   {**p, 'notes': [{'when': 'never', 'lines': []}]}, {k: v for k, v in p.items() if k != 'header'}):
        with pytest.raises(ValueError):
            ms.check_profile(broken)
    bad = copy.deepcopy(p)
    bad['header'].append('-- __NOSUCH__')
    with pytest.raises(ValueError, match='NOSUCH'):
        ms.maxscript(BANK_RAW, bad, date='4 Nov 2026')


# --------------------------------------------------------------------------------------------------------- refusals
def square(x0, y0, s):
    return [[x0, y0], [x0 + s, y0], [x0 + s, y0 + s], [x0, y0 + s]]


def tiny_model(**extra):
    m = json.loads((c.MODELS / 'mini.model.json').read_bytes())
    m.update(extra)
    return m


def test_two_holes_that_touch_are_refused_and_nothing_is_made():
    m = tiny_model()
    slab = next(p for p in m['parts'] if p['kind'] == 'slab')
    x0, y0 = slab['o'][0]
    xs = [q[0] for q in slab['o']]
    ys = [q[1] for q in slab['o']]
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    slab['h'] = [square(cx - 1.0, cy, 1.0), square(cx + 0.0002, cy, 1.0)]       # 0.2 mm apart
    with pytest.raises(ms.MaxScriptRefused) as e:
        gen(m)
    assert any('two holes touch' in p for p in e.value.problems)
    slab['h'] = [square(cx - 1.0, cy, 0.9), square(cx + 0.1, cy, 0.9)]           # 0.2 m apart: fine
    gen(m)


def test_the_bank_checks_refuse_too():
    m = tiny_model()
    wall = next(p for p in m['parts'] if p['kind'] == 'wall')
    for o, why in ((wall['o'][:2], 'fewer than 3 points'), ([wall['o'][0], wall['o'][0], *wall['o'][1:]], 'repeated point')):
        mm = copy.deepcopy(m)
        next(p for p in mm['parts'] if p['kind'] == 'wall')['o'] = o
        with pytest.raises(ms.MaxScriptRefused, match=why):
            gen(mm)
    mm = copy.deepcopy(m)
    mm['parts'][0]['kind'] = 'roof'
    with pytest.raises(ms.MaxScriptRefused, match='unknown kind roof'):
        gen(mm)


# -------------------------------------------------------------------------------------------------- every part kind
def features_model() -> dict:
    m = json.loads((c.APP / 'packages' / 'viewer' / 'test' / 'fixtures' / 'features.model.json').read_bytes())
    for p in m['parts']:
        p.pop('fit', None)
    for st in m.get('stairs', {}).values():
        st.pop('panels', None)
    return m


def test_every_part_kind_case_lines_materials_crlf_no_placeholder():
    m = features_model()
    b = gen(m)
    text = lines(b)
    joined = '\n'.join(text)
    assert not ms.LEFT_OVER.search(joined.replace('__FURN', ''))
    assert all(ord(ch) < 128 for ch in joined)
    px = m['maxPrefix']
    base = lines(gen(tiny_model(maxPrefix=px)))
    for kind, (layer, mat, _) in ms.EXTRA_KINDS.items():
        case = f'        #{kind}: #("{layer}", "{mat}")'
        assert text.count(case) == 1, kind
        assert sum(1 for x in text if x.startswith(f'    append {px}_mats (standardMaterial name:"{px} {mat}" ')) == 1, kind
        assert case not in base
    # a model with one extra kind adds exactly its case line and its material, nothing else changes
    one = tiny_model()
    one['parts'].append({**copy.deepcopy(next(p for p in one['parts'] if p['kind'] == 'wall')), 'kind': 'low', 'z1': 0.45,
                         'follow': False})
    b0, b1 = lines(gen(tiny_model())), lines(gen(one))
    ops = [o for o in difflib.SequenceMatcher(None, b0, b1, autojunk=False).get_opcodes() if o[0] != 'equal']
    added = [b1[j] for _, _, _, j1, j2 in ops for j in range(j1, j2)]
    removed = [b0[i] for _, i1, i2, _, _ in ops for i in range(i1, i2)]
    # what else changed: the stamp (line 2 and the datum's Built line) and the header's keep / follow sentence
    assert all('model data' in x or x.startswith('--') for x in removed), removed
    assert all('model data' in x or x.startswith('--') or x in (
        '        #low: #("LowWalls", "Low")', '    append FX_mats (standardMaterial name:"FX Low" diffuse:(color 210 198 178))')
        or x.startswith('    FX_part #low ') for x in added), added
    assert '        #low: #("LowWalls", "Low")' in added
    assert '    append FX_mats (standardMaterial name:"FX Low" diffuse:(color 210 198 178))' in added
    assert sum(1 for x in added if x.startswith('    FX_part #low ')) == 1
    plinth = next(x for x in text if f'{px}_part #slab "{px}_G_Slab_001' in x)
    assert ' (-0.6000) 0.0000 ' in plinth                                        # a plinth slab builds from z0 = -level


def test_every_part_kind_runs_in_the_mock_max():
    loaded = c.mock()
    if loaded is None:
        pytest.skip('furniture/fixtures/maxscript_mock.py is not there (prototype folder)')
    mk, lite = loaded
    m = features_model()
    b = gen(m)
    text = b.decode('ascii').replace('\r\n', '\n')
    assert lite.lint(text) == []
    assert lite.arity_errors(text) == []
    bank = gen(BANK_RAW, 'bank-27oct', date=None).decode('ascii').replace('\r\n', '\n')
    assert {w.lower() for w in lite.unresolved(text)} <= {w.lower() for w in lite.unresolved(bank)}
    px = m['maxPrefix']
    it = mk.Interp(text)

    def node(cls, nm, fi, cc, z, base, **props):
        sh = it.get(f'{px}_shift')
        n = mk.Node(it.scene, mk.Cls(cls), nm)
        n.tm.rows[3] = mk.P(cc.v[0] - sh.v[0], cc.v[1] - sh.v[1], z)
        n.props.update({f'{px}_floor': str(fi), f'{px}_base': mk.tostr(base)})
        n.props.update(props)
        it.get(f'{px}_nodes').append(n)
        return n

    lv = lambda fi: it.get(f'{px}_levels')[fi - 1]                              # noqa: E731
    it.override(f'{px}_part', lambda it_, kind, nm, loops, z0, z1, follow, fi, cc, mn, mx: node(
        'SplineShape', nm, fi, cc, lv(fi) + z0, z0, **{f'{px}_kind': str(kind), f'{px}_follow': mk.tostr(follow)}))
    it.override(f'{px}_lines', lambda it_, nm, segs, fi, cc, lay: node('SplineShape', nm, fi, cc, lv(fi), 0.0))
    it.override(f'{px}_room', lambda it_, nm, p, fi: node('Text', f'{px}_Room_{nm}', fi, p, lv(fi) + 0.02, 0.02))
    tl = text.split('\n')
    i = next(k for k, x in enumerate(tl) if x.startswith(f'        {px}_shift = if dwg.checked'))
    kinds = [k['key'] for k in m['furnitureKinds'] if any(p['kind'] == k['key'] for p in m['furniture'])]
    controls = {f'fh{j + 1}': mk.Control(value=500) for j in range(len(kinds))}
    controls.update(fb=mk.Control(checked=True), fo=mk.Control(checked=False))
    it.run('\n'.join(tl[i + 1:i + 4]), **controls)
    it.set(f'{px}_shift', mk.P(0.0, 0.0))
    assert it.call(f'{px}_build') is True
    n_parts = len(m['parts'])
    n_stairs = sum(1 for st in m['stairs'].values() for k in ('below', 'above') if st.get(k))
    n_rooms = len(m['rooms'])
    n_boxes = len(m['furniture'])
    assert len(it.scene.objects) == n_parts + n_stairs + n_rooms + n_boxes + 1          # + the hidden datum
    assert it.get(f'{px}_failed') == []
    assert any(x.rstrip().endswith('0 failed checks') for x in it.scene.listener)
    # every case line's material exists once the materials are made
    it.call(f'{px}_makeMaterials')
    for kind in {p['kind'] for p in m['parts']}:
        mat = (ms.KINDS.get(kind) or ms.EXTRA_KINDS[kind][:2])[1]
        assert it.call(f'{px}_mat', mat) is not None, kind


# ---------------------------------------------------------------------------------------------------------- names
def test_thai_names_fall_back_to_ids_and_hostile_names_stay_text():
    m = tiny_model()
    m['project'] = 'โครงการทดสอบ'
    m['shortName'] = 'ทดสอบ'
    m['source'] = ['แบบ', 'แบบชั้น2.dwg']
    m['floors'][0]['name'] = 'ชั้นล่าง'
    wall = next(p for p in m['parts'] if p['kind'] == 'wall')
    wall['label'] = 'ผนัง'
    m['rooms'] = [{'floor': 'L1', 'name': 'ห้องนอน', 'label': 'ห้องนอน', 'area': None, 'x': 0.5, 'y': 0.5},
                  {'floor': 'L1', 'name': 'x', 'label': c.HOSTILE[0] + ' ' + c.HOSTILE[4] + ' ' + c.HOSTILE[5], 'area': None,
                   'x': 1.0, 'y': 1.0}]
    text = lines(gen(m))
    joined = '\r\n'.join(text)
    assert all(ord(ch) < 128 for ch in joined)
    assert any(x.startswith('    FX_part #wall "FX_L1_Wall_001" ') for x in text)          # no trailing _ for a Thai label
    assert any(x.startswith('    FX_room "room 001" ') for x in text)
    assert text[0].startswith(f"-- {m['photoName'].upper()} / built by")                     # the photo name for a Thai project
    assert 'spinner lv1 "L1 floor level (m):"' in joined                                      # the floor's key for its name
    assert 'rollout FX_UI "' in joined and 'rollout FX_UI ""' not in joined
    assert 'from "drawing 1 + 2.dwg"' in joined                                               # an all-Thai name: its place
    # the hostile label is one MAXScript string: quotes and backslashes made safe, no placeholder filled inside it
    room = next(x for x in text if x.startswith('    FX_room "<img'))
    assert "a 'quoted' / name" in room and '__SHA__ __PX__' in room


def test_summary_and_stamp():
    b = gen(BANK_RAW, 'bank-27oct', date=None)
    s = ms.summary(json.loads(BANK_RAW), b)
    assert s == {'parts': 124, 'stairShapes': 4, 'rooms': 18, 'boxes': 185, 'lines': 867, 'stamp': 'c3a9408304a2'}


def test_the_command_line(tmp_path):
    import shutil
    import subprocess
    node = shutil.which('node')
    assert node, 'node is not on PATH'
    run = lambda *a: subprocess.run([node, str(c.APP / 'tools' / 'run-builder-py.mjs'), '-m', 'walkthrough_builder.out', *a],  # noqa: E731
                                    cwd=c.APP, capture_output=True, text=True, encoding='utf-8', timeout=120, stdin=subprocess.DEVNULL)
    r = run(str(c.MODELS / 'bank-v2.model.json'), '--profile', 'bank-27oct', '--out', str(tmp_path / 'bank.ms'))
    assert r.returncode == 0, r.stderr
    assert c.sha1((tmp_path / 'bank.ms').read_bytes()) == c.BANK_MS_SHA1 and 'stamp c3a9408304a2' in r.stdout
    r = run(str(c.MODELS / 'bank-v2.model.json'), '--date', '4 Nov 2026', '--sources', 'dwg:mm,dwg:mm', '--converter-version', '0.14',
            '--out', str(tmp_path / 'up.ms'))
    assert r.returncode == 0, r.stderr
    assert (tmp_path / 'up.ms').read_bytes() == gen(BANK_RAW, sources=[{'kind': 'dwg', 'units': 'mm'}] * 2,
                                                   converter={'name': 'libredwg', 'version': '0.14'})
    r = run(str(c.MODELS / 'bank-v2.model.json'), '--out', str(tmp_path / 'x.ms'))
    assert r.returncode == 1 and 'date' in r.stderr and not (tmp_path / 'x.ms').exists()
