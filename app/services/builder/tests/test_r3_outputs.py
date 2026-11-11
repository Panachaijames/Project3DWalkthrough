"""R3: the outputs of real new-rule builds (docs/rooms/WORK_BREAKDOWN.md R3, "Tests alone"; ACCEPTANCE 2.1 R3).

The reference building (built here from its drawings) and the house, the bank, the tower and the two suites (conftest's
session builds with their `*-rooms` settings, READ ONLY) go through U4's write_outputs, and every output the API validates goes through
its own check (`node tools/run-py.mjs -m walkthrough_api.check_file <kind>`: model, stages, presentation, overlay, diff,
pieces, openings, inputs). Then, on each:

* the overlay has the new floor fields, one flag per report row of each new kind (counted from the report, so the test
  follows R1's and R2's rules wherever they land), no `plate-dropped`, no `stairs-none` where a stair climbs;
* the Max script: a storey statement after each stair part, the Ceilings layers hidden, the notes; the house's and the
  bank's scripts run in the mock 3ds Max (Build, then "Update levels and heights" with real Extrude amounts);
* the bank's 23 names (R1.md D-1) are 23 labels in the top view and 23 text objects in the Max script;
* the replay says the rooms closed and the stairs you can climb; the presentation's start view holds every slab corner;
* the diff against the old-rule version has the rooms rows.
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import pytest

import kit
import test_r3_maxscript as r3ms
import test_u4_common as c
from test_u3_helpers import build_ctx, run_build
from walkthrough_builder import contracts, oslock
from walkthrough_builder.out import diff as df
from walkthrough_builder.out import maxscript as ms
from walkthrough_builder.out import pictures as pic
from walkthrough_builder.out import presentation as pres

BUILT_AT = dt.datetime(2026, 11, 11, 12, 0, 0, tzinfo=dt.timezone.utc)
FIXTURE = {'reference': 'reference_build', 'house': 'house_rooms', 'bank': 'bank_rooms', 'tower': 'tower_rooms',
           'suite': 'suite_rooms', 'suite-revit': 'suite_revit_rooms'}
#: the builds with two floors and a stair that climbs between them
CLIMBS = ['reference', 'house', 'bank', 'tower']
#: the old-rule model each is compared with (the saved version it would replace), or None
AGAINST = {'bank': c.MODELS / 'bank-v2.model.json', 'house': c.MODELS / 'house.model.json', 'suite': c.MODELS / 'suite.model.json'}
NEW_FIELDS = {'spaces', 'holes', 'stairs', 'closings', 'unfloored'}


@pytest.fixture(scope='module')
def reference_build(reference_building, tmp_path_factory) -> dict:
    tmp = tmp_path_factory.mktemp('r3-reference')
    with oslock.hold():                                       # the door finder runs in this process (U-3.5)
        res, logs = run_build(reference_building['settings'], reference_building['sources'], tmp / 'build', 'rooms-reference')
    return {'name': 'reference', 'settings': reference_building['settings'], 'sources': reference_building['sources'],
            'res': res, 'logs': logs, 'tmp': tmp, 'project': 'rooms-reference'}


@pytest.fixture(scope='module')
def outputs(request, tmp_path_factory) -> dict:
    """name -> {build, written: {output: path}, logs}, written once per module for each of the four builds."""
    cache: dict[str, dict] = {}

    def get(name: str) -> dict:
        if name not in cache:
            b = request.getfixturevalue(FIXTURE[name])
            tmp = tmp_path_factory.mktemp(f'r3-out-{name}')
            ctx = build_ctx(b['settings'], b['sources'], tmp, b['project'])
            ctx['converter'] = {'name': 'libredwg', 'version': '0.14', 'exeSha1': '0' * 40}
            ctx['versionModel'] = str(AGAINST[name]) if name in AGAINST else None
            ctx['spec'].update(runId='0002-build', buildId='20261111T120000-abcdef', settingsRevision=1, only=None, office=None,
                               sources=[{'sha1': x['sha1'], 'name': x['name'], 'kind': x['kind'], 'path': str(tmp / 'no-original'),
                                         'units': x['units']} for x in b['sources']])
            for d in (ctx['outDir'], ctx['tmpDir']):
                Path(d).mkdir(parents=True, exist_ok=True)
            import walkthrough_builder.out as OUT
            logs: list[str] = []
            with pytest.MonkeyPatch.context() as mp:
                mp.setattr(OUT, '_now', lambda: BUILT_AT)
                written = contracts.write_outputs({k: v for k, v in b['res'].items() if not k.startswith('_')}, ctx, logs.append)
            cache[name] = {'build': b, 'written': written, 'logs': logs}
        return cache[name]

    return get


def load(p: Path) -> dict:
    return json.loads(p.read_bytes().decode('utf-8'))


@pytest.mark.parametrize('name', list(FIXTURE))
def test_every_output_passes_the_apis_checks(name, outputs):
    w = outputs(name)['written']
    m = w['model.json']
    items = [('model', m, None), ('stages', w['stages.json'], m), ('presentation', w['presentation.json'], m)]
    items += [(k, w[f'{k}.json'], None) for k in ('overlay', 'diff', 'pieces', 'openings', 'inputs')]
    c.assert_checked(items)
    assert 'stairways' in load(m), 'a v2 model'


@pytest.mark.parametrize('name', list(FIXTURE))
def test_the_overlay_has_one_flag_per_report_row(name, outputs):
    o = outputs(name)
    ov = load(o['written']['overlay.json'])
    rep = o['build']['res']['report']
    kinds = [f['kind'] for f in ov['flags']]
    assert 'plate-dropped' not in kinds and 'stairs-none' not in kinds, 'a stair climbs between the floors, or one floor'
    want = {k: 0 for k in ('slab-gap', 'room-open', 'room-names', 'doorway', 'stair', 'stair-clash', 'hole-skipped')}
    for fl in ov['floors']:
        assert NEW_FIELDS <= set(fl), fl['key']
        r = rep['floors'][fl['key']]
        slab = r['slab']
        assert len(fl['spaces']) == r['rooms']['spaces'] and len(fl['stairs']) == len(r['stairways'])
        assert len(fl['holes']) == sum(1 for h in slab['holes'] if h['cut']) and len(fl['closings']) == len(slab['closings'])
        want['slab-gap'] += sum(1 for u in slab['unfloored'] if not u['answered'] and u['area'] >= 4)
        want['room-open'] += len(r['rooms']['open'])
        want['room-names'] += len(r['rooms']['several'])
        want['doorway'] += sum(1 for x in slab['closings'] if x['kind'] == 'doorway')
        want['stair'] += sum(1 for x in r['stairways'] if x['state'] == 'lines')
        want['stair-clash'] += len({x['stair'] for x in r['stairClash']})
        want['hole-skipped'] += sum(1 for h in slab['holes'] if not h['cut'] and h.get('why') in
                                    ('the lowest floor', 'over 60 m2', 'over 30 % of the floor'))
    got = {k: kinds.count(k) for k in want}
    whole = sum(1 for f in ov['flags'] if f['kind'] == 'slab-gap' and 'the walls span' in f['detail'])
    assert got == {**want, 'slab-gap': want['slab-gap'] + whole}
    for f in ov['flags']:
        if f['kind'] == 'stair':
            row = next(x for fl in rep['floors'].values() for x in fl['stairways'] if x['id'] == f['ref']['stair'])
            assert f['detail'] == row['text'] and f['severity'] == row['severity']


@pytest.mark.parametrize('name', CLIMBS)
def test_the_max_script_of_a_new_rule_build(name, outputs):
    o = outputs(name)
    model = o['build']['res']['model']
    data = o['written'][o['build']['settings']['project']['maxFileName']].read_bytes()
    text = data.decode('ascii').split('\r\n')
    px = model['maxPrefix']
    assert sum(1 for x in text if x.startswith(f'    setUserProp {px}_nodes[{px}_nodes.count] "{px}_storey" ')) == \
        sum(1 for p in model['parts'] if p.get('stair'))
    assert any(x.startswith('-- Stairs: ') for x in text) and any('Ceilings are on hidden layers' in x for x in text)
    assert f'        if ly != undefined do ly.isHidden = true' in text
    assert not [x for x in text if not x.startswith('--') and r3ms.POLY.search(x)]
    assert f'        local up = getUserProp o "{px}_storey"' in text
    sw = model['stairways'][0]
    assert f"Stairs: {sw['risers']} risers of {sw['riser']:.3f} m" in '\n'.join(text)
    # RA-11: the parts' kinds, and no Editable Poly anywhere in the text (the header's "(no Editable Poly)" aside)
    calls = [x for x in text if x.startswith(f'    {px}_part #')]
    assert sorted(x.split()[1][1:] for x in calls) == sorted(p['kind'] for p in model['parts'])
    assert all(x.count('),#(') == len(p['h']) for p, x in zip(model['parts'], calls) if p['kind'] == 'slab'), 'slabs with their holes'
    whole = data.decode('ascii').lower()
    assert not any(w in whole for w in ('converttopoly', 'edit_poly', 'editable_poly'))
    if name == 'house':
        assert '-- Stairs: 21 risers of 0.186 m, 19 treads and 1 landing.' in text


@pytest.mark.parametrize('name', ['reference', 'house', 'bank'])
def test_the_max_script_runs_in_the_mock_with_real_amounts(name, outputs, monkeypatch):
    """RA-11's mock run on the house's and the bank's new-rule scripts (and the reference building's): Build with no
    error and the expected objects per kind, the furniture as Box primitives on its kind layers; then the real
    "Update levels and heights" with the upper level 0.30 m higher (every stair part scaled: the top tread's top is the
    new upper level less one new riser, within 1 mm; ceilings keep their height above their level) and, from the levels
    of the build, 0.50 m lower (no cut wall piece higher than the stair's underside over it)."""
    from collections import Counter
    from shapely.geometry import Polygon
    mk, lite = r3ms._mock_with_amounts(monkeypatch)
    o = outputs(name)
    model = o['build']['res']['model']
    px = model['maxPrefix']
    text = o['written'][o['build']['settings']['project']['maxFileName']].read_bytes().decode('ascii').replace('\r\n', '\n')
    assert lite.lint(text) == [] and lite.arity_errors(text) == []
    it, seen = r3ms.run_build(mk, text, model, pre=furniture_controls(mk, model))
    # the objects per kind
    assert Counter(n.props[f'{px}_kind'] for n in seen) == Counter(p['kind'] for p in model['parts'])
    boxes = [n for n in it.scene.objects if n.cls.name == 'Box']
    assert len(boxes) == len(model.get('furniture') or [])
    assert all(n.layer is not None and n.layer.name.startswith(f'{px}_') and '_Furn_' in n.layer.name for n in boxes)
    n_lines = sum(1 for st in model['stairs'].values() for k in ('below', 'above') if st.get(k))
    assert len(it.scene.objects) == len(model['parts']) + n_lines + len(model['rooms']) + len(boxes) + 1      # + the datum
    fi = {f['key']: i + 1 for i, f in enumerate(model['floors'])}
    levels0 = list(it.get(f'{px}_levels'))
    heights0 = list(it.get(f'{px}_heights'))

    def update(levels):
        it.call(f'{px}_updateLevels', list(levels), list(heights0))

    def scale(sw, levels):
        f, t = fi[sw['from']] - 1, fi[sw['to']] - 1
        return (levels[t] - levels[f]) / (levels0[t] - levels0[f])

    raised = [levels0[0]] + [v + 0.30 for v in levels0[1:]]
    update(raised)
    for sw in model['stairways']:
        s = scale(sw, raised)
        mine = [(n, p) for n, p in zip(seen, model['parts']) if p.get('stair') == sw['id']]
        for n, p in mine:
            lv = raised[fi[p['floor']] - 1]
            assert n.tm.rows[3].v[2] == pytest.approx(lv + p['z0'] * s, abs=2e-5), n.name
            assert n.modifiers[0].amount == pytest.approx((p['z1'] - p['z0']) * s, abs=1e-9), n.name
        top = max((n for n, p in mine if p['kind'] == 'tread'), key=lambda n: n.tm.rows[3].v[2] + n.modifiers[0].amount)
        new_riser = (raised[fi[sw['to']] - 1] - raised[fi[sw['from']] - 1]) / sw['risers']
        assert top.tm.rows[3].v[2] + top.modifiers[0].amount == pytest.approx(raised[fi[sw['to']] - 1] - new_riser, abs=1e-3)
    for n, p in zip(seen, model['parts']):
        if p['kind'] == 'ceiling':
            assert n.tm.rows[3].v[2] == pytest.approx(raised[fi[p['floor']] - 1] + p['z0'], abs=1e-9)
            assert n.modifiers[0].amount == pytest.approx(p['z1'] - p['z0'], abs=1e-9)
    update(levels0)
    lowered = [levels0[0]] + [v - 0.50 for v in levels0[1:]]
    update(lowered)
    top_of = lambda n: n.tm.rows[3].v[2] + n.modifiers[0].amount                  # noqa: E731
    for sw in model['stairways']:
        steps = [(n, Polygon(p['o'], p['h'])) for n, p in zip(seen, model['parts'])
                 if p.get('stair') == sw['id'] and p['kind'] in ('tread', 'landing')]
        for n, p in zip(seen, model['parts']):
            if p.get('stair') == sw['id'] and p['kind'] not in ('tread', 'landing'):
                wall = Polygon(p['o'], p['h'])
                over = [m.tm.rows[3].v[2] for m, poly in steps if poly.intersection(wall).area > 1e-4]
                assert over and top_of(n) <= min(over) + 1e-3, n.name


def furniture_controls(mk, model: dict) -> dict:
    """The window's furniture controls the build handler reads (as test_u4_maxscript's mock run sets them)."""
    kinds = [k['key'] for k in model.get('furnitureKinds') or [] if any(p['kind'] == k['key'] for p in model.get('furniture') or [])]
    if not kinds:
        return {}
    ctl = {f'fh{j + 1}': mk.Control(value=500) for j in range(len(kinds))}
    ctl.update(fb=mk.Control(checked=True), fo=mk.Control(checked=False))
    return ctl


def test_the_banks_23_names_are_23_labels_in_the_top_view_and_the_max_script(outputs, monkeypatch):
    o = outputs('bank')
    model = o['build']['res']['model']
    assert len(model['rooms']) == 23
    data = o['written'][o['build']['settings']['project']['maxFileName']].read_bytes()
    assert ms.summary(model, data)['rooms'] == 23
    import matplotlib
    matplotlib.use('Agg')
    from matplotlib.axes import Axes
    seen = []
    orig = Axes.text
    monkeypatch.setattr(Axes, 'text', lambda self, x, y, s, *a, **kw: (seen.append((s, kw.get('color'))), orig(self, x, y, s, *a, **kw))[1])
    png = pic.topview_png(model)
    assert png == o['written']['topview.png'].read_bytes()
    assert sum(1 for s, col in seen if col == '#1f4e79') == 23
    assert sum(1 for s, _ in seen if s == 'open: stair well') == 1


@pytest.mark.parametrize('name', CLIMBS)
def test_the_replay_presentation_and_diff_of_a_new_rule_build(name, outputs):
    o = outputs(name)
    res = o['build']['res']
    model = res['model']
    st = load(o['written']['stages.json'])
    closed = sum(v['spaces'] for v in res['replay']['facts']['rooms'].values())
    assert st['captions']['finish'].endswith(f"{closed} rooms closed, 1 stair you can climb.")
    p = load(o['written']['presentation.json'])
    assert 'Stairs' in [it['text'] for it in p['legend']['items']]
    assert pres.camera_view(model, p, margin=pres.CAMERA_MARGIN_PX)['inside']
    d = load(o['written']['diff.json'])
    if name in AGAINST:
        counts = d['against'][0]['diff']['counts']
        for fl in model['floors']:
            row = counts[fl['key']]
            assert row[df.ROOMS_CLOSED] == [0, sum(1 for s in model['spaces'] if s['floor'] == fl['key'])]
            assert row[df.PLATE_AREA][1] == df.plate_area(model, fl['key'])
        assert counts[model['stairways'][0]['from']][df.CLIMBABLE] == [0, 1]
    else:
        assert d['against'] == []
    assert any('outputs written' in x for x in o['logs'])


def test_the_reference_overlay_against_the_frozen_fixture(outputs):
    """What R1's and R2's real rules make of the reference building differs from the frozen overlay only where R1.md
    section 4 says the build differs (areas, outlines to the millimetre): the same flags by kind and id."""
    ov = load(outputs('reference')['written']['overlay.json'])
    want = c.load_json(kit.ROOMS_FIXTURES / 'overlay.reference.json')
    assert [(f['kind'], f['floor']) for f in ov['flags']] == [(f['kind'], f['floor']) for f in want['flags']]
    same_id = {'room-open', 'room-names', 'doorway', 'stair', 'stair-clash', 'hole-skipped'}
    assert [f['id'] for f in ov['flags'] if f['kind'] in same_id] == [f['id'] for f in want['flags'] if f['kind'] in same_id]
    for g, w in zip(ov['floors'], want['floors']):
        assert [(s['id'], s['name'], s['names'], s['area']) for s in g['spaces']] == [(s['id'], s['name'], s['names'], s['area'])
                                                                                       for s in w['spaces']]
        assert [(s['id'], s['state'], s['why']) for s in g['stairs']] == [(s['id'], s['state'], s['why']) for s in w['stairs']]
        assert [h['what'] for h in g['holes']] == [h['what'] for h in w['holes']]
        assert [(x['kind'], x['a'], x['b']) for x in g['closings']] == [(x['kind'], x['a'], x['b']) for x in w['closings']]
