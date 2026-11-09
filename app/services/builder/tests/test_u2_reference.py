"""U2 on the six reference drawings (heavy: each read in this process under the machine run lock; WT_REF read-only)
(docs/upload/DESIGN.md U-7, U-8.3, U-3.3; ACCEPTANCE A-4, A-8, A-10, 2.1 U2):
* the cache's items equal the prototype prims.py items made by make:reference, field for field, `k` and `area` aside;
* keys unique within a source and equal across two conversions of the same DWG (I1201 converted again here);
* units: the votes and verdicts; level tags; grid labels and their lines; area proposals;
* every plan entry: points, anchors per INSERT at every depth, sig / rsig / eid as worked out from the cache item;
* every output passes the API's check_file;
* suggestions for the bank against bank_project.json (>= 80 %), the office memory on L29 (A-8), the proposals;
* the scaffold's provisional drawing and plan fixtures re-made and compared (the differences are in U2.md).
The presidential drawing needs about 1 GB and 40 s: it is read once, in the first test that needs it.
"""
from __future__ import annotations

import json
import math
import shutil
import subprocess

import pytest

import kit
import test_u2_kit as K
from test_u2_propose import rule_issues
from test_u2_read import check_plan
from walkthrough_builder import propose as P
from walkthrough_builder import suggest as S

pytestmark = pytest.mark.heavy

NAMES = ('bank1', 'bank2', 'sukhumvit', 'presidential', 'l29', 'l30')
#: name -> (declared, used, verdict, votes): 4 Nov's measurement placed mirrored arcs at their OCS centre (house 22 mm,
#: suite 7 mm); the reader places them at their world centre, which finds the mirrored doors too (U2.md)
UNITS = {'bank1': ('mm', 'mm', 'agree', {'mm': 16}), 'bank2': ('mm', 'mm', 'agree', {'mm': 31}),
         'sukhumvit': ('in', 'mm', 'votes-win', {'mm': 28, 'm': 4}), 'presidential': ('mm', 'mm', 'agree', {'mm': 10}),
         'l29': ('mm', 'mm', 'agree', {'mm': 19}), 'l30': ('mm', 'mm', 'agree', {'mm': 17})}
GRID = {'bank1': 10, 'bank2': 10, 'sukhumvit': 63, 'presidential': 0, 'l29': 0, 'l30': 0}
HOUSE_PLANS = {'ground': [7.74826, 5.601038, 53.870897, 25.854851], 'upper': [81.769533, 6.617993, 127.848522, 24.809115]}
SUITE_BOX = [174.840173, -3508.518094, 209.056439, -3480.305594]


def _cover(box, region) -> float:
    w = min(box[2], region[2]) - max(box[0], region[0])
    h = min(box[3], region[3]) - max(box[1], region[1])
    return max(0.0, w) * max(0.0, h) / ((region[2] - region[0]) * (region[3] - region[1]))


@pytest.mark.parametrize('name', NAMES)
def test_items_equal_prims_and_keys_are_unique(ref, name) -> None:
    r = K.ref_read(name)
    D = K.ref_prims(name)
    assert len(r['items']) == len(D['items'])
    assert K.strip(r['items']) == K.strip(D['items'])
    assert r['cache']['layers'] == {k: v for k, v in D['layers'].items() if k != '__suite_bbox__'}
    assert all('area' not in d for d in r['items'])
    ks = [d['k'] for d in r['items']]
    assert len(set(ks)) == len(ks)
    # an item with no points belongs to no floor (U-9.1): the six drawings have none
    assert not [d for d in r['items'] if not (d.get('pts') or [q for lp in d.get('loops', []) for q in lp]
                                              or d.get('ins'))]


@pytest.mark.parametrize('name', NAMES)
def test_units(ref, name) -> None:
    declared, used, verdict, votes = UNITS[name]
    u = K.ref_read(name)['drawing']['units']
    assert (u['declared'], u['used'], u['verdict']) == (declared, used, verdict)
    assert u['votes'] == {**{x: 0 for x in ('mm', 'cm', 'm', 'in', 'ft')}, **votes}
    assert K.ref_read(name)['cache']['units'] == used


@pytest.mark.parametrize('name', NAMES)
def test_level_tags(ref, name) -> None:
    r = K.ref_read(name)
    tags = r['drawing']['levelTags']
    if name != 'sukhumvit':
        assert tags == []
        return
    # 28 marks: 18 on SPEC and 10 on layer 0, of which two on layer 0 are blank LEVEL attributes (no value: left out)
    by = {}
    for t in tags:
        by[t['layer']] = by.get(t['layer'], 0) + 1
    assert by == {'SPEC': 18, '0': 8}
    blank = [d for d in r['items'] if d['t'] == 'ATTRIB' and d.get('tag') == 'LEVEL' and not d['text'].strip()]
    assert len(blank) == 2 and {d['lay'] for d in blank} == {'0'}
    assert all(28.3 <= t['y'] <= 61.1 for t in tags)                       # all in the elevations
    assert {t['value'] for t in tags} >= {0.7, 0.9, 4.8, 7.95, 9.05}
    assert any(t['value'] == 0.9 and t['label'] == 'ระดับพื้นชั้นที่ 1' for t in tags)
    assert not any(t['text'] in ('W1.20', 'D2.10', 'A1.00', 'R1.50', 'x0.900') for t in tags)


@pytest.mark.parametrize('name', NAMES)
def test_grid_labels(ref, name) -> None:
    labels = K.ref_read(name)['drawing']['gridLabels']
    assert len(labels) == GRID[name]
    if name in ('bank1', 'bank2'):
        assert {g['layer'] for g in labels} == {'S-GRID-IDEN'}
        assert all(g['line'] and math.dist(*g['line']) > 10 for g in labels)        # the grid lines themselves


def test_house_grid_lines_give_the_shift_between_its_plans(ref) -> None:
    """The house draws its grid lines as 1.5 m ticks in the bubble blocks: read from the bubble along `direction`, a
    label's line enters a plan; the numbered lines 2 - 12 of the two plans lie 74.021 m apart in x and the lettered
    lines D E F H J at the same y (U-9.4's measurement). Which floor a label belongs to is U3's rule (U2.md: the
    lettered ticks left of the ground plan point across both plans)."""
    labels = K.ref_read('sukhumvit')['drawing']['gridLabels']
    from shapely.geometry import LineString, box

    def floors_of(g):
        (sx, sy), _e = g['line']
        ray = LineString([(sx, sy), (sx + 200 * g['direction'][0], sy + 200 * g['direction'][1])])
        return [k for k, b in HOUSE_PLANS.items() if ray.intersects(box(b[0] - .5, b[1] - .5, b[2] + .5, b[3] + .5))]
    numbered = {'ground': {}, 'upper': {}}
    for g in labels:
        if g['line'] and g['text'].isdigit():
            fl = floors_of(g)
            if len(fl) == 1:
                numbered[fl[0]][g['text']] = g
    shared = sorted(set(numbered['ground']) & set(numbered['upper']), key=int)
    assert shared == [str(i) for i in range(2, 13)]
    for n in shared:
        a, b = numbered['ground'][n], numbered['upper'][n]
        assert a['direction'] == b['direction'] == [0.0, -1.0]
        assert b['line'][0][0] - a['line'][0][0] == pytest.approx(74.021, abs=0.002)
    lettered = {}
    for g in labels:
        if g['line'] and g['text'] in ('D', 'E', 'F', 'H', 'J') and g['direction'][1] == 0.0 and floors_of(g):
            lettered.setdefault(g['text'], []).append(g['line'][0][1])
    assert sorted(lettered) == ['D', 'E', 'F', 'H', 'J']
    assert all(len(ys) >= 2 and max(ys) - min(ys) <= 0.002 for ys in lettered.values())
    # the elevations' labels (y 34.3 - 34.7) reach no plan
    assert not any(floors_of(g) for g in labels if g['line'] and 34 <= g['y'] <= 35)


def test_area_proposals(ref) -> None:
    house = K.ref_read('sukhumvit')['drawing']['areas']
    plans = [a for a in house if a['looks'] == 'plan']
    for region in HOUSE_PLANS.values():
        assert max(_cover(a['bbox'], region) for a in plans) >= 0.9       # ACCEPTANCE 2.1 U2: one proposal, >= 90 %
    assert [a['id'] for a in house] == [f'a{i + 1}' for i in range(len(house))]
    assert [a['bbox'] for a in house] == sorted((a['bbox'] for a in house), key=lambda b: (-b[3], b[0]))
    assert sum(1 for a in house if a['looks'] == 'elevation') >= 2
    # the reference rule leaves the ground plan as a 92 % box and an overlapping plan-looking sliver (three plans);
    # the floor guess joins them: two boxes, each holding its plan whole
    assert len(plans) == 3
    joined = P.plan_boxes(house)
    assert len(joined) == 2 and [max(_cover(b, region) for b in joined) for region in HOUSE_PLANS.values()] == [1.0, 1.0]
    for name in ('bank1', 'bank2', 'l29', 'l30'):
        got = K.ref_read(name)['drawing']['areas']
        assert [a['looks'] for a in got].count('plan') == 1
    suite = K.ref_read('presidential')['drawing']['areas']
    assert max(_cover(a['bbox'], SUITE_BOX) for a in suite if a['looks'] == 'plan') >= 0.9


@pytest.mark.parametrize('name', NAMES)
def test_plan_geometry_entries(ref, name) -> None:
    r = K.ref_read(name)
    check_plan(r['items'], r['plan'], 1.0)
    size = (r['out'] / 'plan.json.gz').stat().st_size
    assert size < 1.5 * 2 ** 20, f'{name}: plan.json.gz is {size:,} B'


def test_outputs_pass_the_apis_record_checks(ref) -> None:
    files = []
    for name in NAMES:
        out = K.ref_read(name)['out']
        files += [('drawing', out / 'drawing.json'), ('plan', out / 'plan.json.gz')]
    assert K.api_issues(files) == {str(p): [] for _k, p in files}


def test_keys_equal_across_two_conversions_of_one_dwg(ref, libredwg, tmp_path) -> None:
    work = tmp_path / 'convert'
    work.mkdir()
    shutil.copyfile(kit.PROJECT / kit.DRAWINGS['bank1'], work / 'input.dwg')
    subprocess.run([str(libredwg / 'dwg2dxf.exe'), '-y', '-o', 'plan.dxf', 'input.dwg'], cwd=work, check=True,
                   stdin=subprocess.DEVNULL, capture_output=True, timeout=120)
    again = K.read(work / 'plan.dxf', tmp_path / 'out', name=kit.DRAWINGS['bank1'],
                   sha1=K.manifest()['drawings']['bank1']['dwgSha1'])
    first = K.ref_read('bank1')
    assert [d['k'] for d in again['items']] == [d['k'] for d in first['items']]
    assert again['items'] == first['items']
    assert again['plan'] == first['plan']


def _bank_roles() -> dict[str, str]:
    cfg = json.loads((kit.PROJECT / 'bank_test' / 'src' / 'bank_project.json').read_text(encoding='utf-8'))
    return {n: role for role, names in cfg['layers'].items() for n in names}


def test_bank_suggestions_agree_with_bank_project(ref) -> None:
    got = S.suggest([K.ref_read('bank1')['drawing'], K.ref_read('bank2')['drawing']], None)['layers']
    want = _bank_roles()
    agree = [n for n, role in want.items() if got.get(n, {}).get('role') == role]
    assert len(agree) >= 0.8 * len(want), sorted(set(want) - set(agree))
    assert got['A-GLAZ-CURT']['role'] == 'glass' and got['S-GRID-IDEN']['role'] == 'grid'
    assert got['A-AREA-IDEN']['role'] == 'room-name' and got['S-STRS-MBND']['role'] == 'stair-above'
    assert all(got[n]['from'] in ('name', 'contents', 'default') for n in got)


def test_office_memory_on_l29(ref) -> None:
    """A-8: after the bank was saved for dwp-revit, L29's thirteen layers come from the office (it has no L-PLNT), and
    the other L29 layers the bank's memory holds too; the rest by name, contents or default."""
    office = json.loads((kit.UPLOAD_FIXTURES / 'mappings' / 'dwp-revit.json').read_text(encoding='utf-8'))
    got = S.suggest([K.ref_read('l29')['drawing']], office)
    L = got['layers']
    thirteen = ['A-WALL', 'A-WALL-PATT', 'S-COLS', 'A-GLAZ-CURT', 'A-DOOR', 'A-DOOR-FRAM', 'A-DOOR-HDLN', 'S-STRS',
                'S-STRS-MBND', 'I-FURN', 'Q-CASE', 'P-SANR-FIXT', 'A-GENM']
    assert 'L-PLNT' not in L
    assert all(L[n]['from'] == 'office' for n in thirteen), {n: L[n]['from'] for n in thirteen}
    remembered = {n for e in office['layers'].values() for n in e['names']}
    assert {n for n in L if L[n]['from'] == 'office'} == remembered & set(L)
    assert {L[n]['role'] for n in ('A-DETL', 'A-FLOR')} == {'other'} and L['A-FLOR']['from'] == 'office'
    assert got['office'] == 'dwp-revit'


def test_proposals_for_the_four_drawings(ref, tmp_path) -> None:
    cases = {'bank': ['bank1', 'bank2'], 'house': ['sukhumvit'], 'suite': ['presidential'], 'tower': ['l29', 'l30']}
    man = K.manifest()['drawings']
    files = []
    got = {}
    for case, names in cases.items():
        drs = [K.ref_read(n)['drawing'] for n in names]
        spec = {'projectId': f'{case}-upload', 'office': None, 'settings': None,
                'sources': [{'sha1': man[n]['dwgSha1'], 'name': kit.DRAWINGS[n], 'kind': 'dwg', 'path': 'x',
                             'units': None} for n in names]}
        s = P.propose_settings(spec, drs, S.suggest(drs, None), [], None)
        assert rule_issues(s) == []
        got[case] = s
        p = tmp_path / f'{case}.json'
        p.write_text(json.dumps(s, ensure_ascii=False), encoding='utf-8')
        files.append(('settings', p))
    assert K.api_issues(files) == {str(p): [] for _k, p in files}
    bank, house, suite, tower = got['bank'], got['house'], got['suite'], got['tower']
    assert [(f['key'], f['area']['kind']) for f in bank['floors']] == [('L1', 'wholeFile'), ('L2', 'wholeFile')]
    assert all(x['unitsConfirmed'] and x['units'] == 'mm' for x in bank['sources'] + tower['sources'])
    assert bank['project']['exportedFrom'] == 'Revit' == tower['project']['exportedFrom']
    assert house['project']['exportedFrom'] is None
    assert [f['area']['kind'] for f in house['floors']] == ['box', 'box']
    for f, region in zip(house['floors'], HOUSE_PLANS.values()):
        assert _cover(f['area']['bbox'], region) == 1.0 and f['area']['pad'] == 0.5 and f['area']['match'] == 'all'
    assert house['sources'][0] == {'sha1': man['sukhumvit']['dwgSha1'], 'name': kit.DRAWINGS['sukhumvit'],
                                   'kind': 'dwg', 'units': 'mm', 'unitsConfirmed': False}
    assert len(suite['floors']) == 1 and len(tower['floors']) == 2
    assert house['layers']['GRID-01'] == 'grid' and house['layers']['WALL'] == 'wall'


def test_provisional_fixtures_remade(ref) -> None:
    """The scaffold's provisional drawing and plan fixtures, made again by the reader: the plan's keys, sig, rsig, eid,
    points and types and the drawing's blocks, level tags, grid labels and area boxes (U7's canvas tests pin these) are
    the same (two nested ATTRIB keys of the house now carry their source handle); the rest is listed in
    WT_TMP\\u2-fixture-diff.json and U2.md. The re-made fixtures are written to WT_TMP\\u2-fixtures\\{drawing,plan}\\ in
    the scaffold's format (drawing: JSON indented 2 + newline; plan: the reader's own gzip bytes) for the integration
    step, which owns fixtures/upload/, to copy."""
    import gzip
    report = {}
    made = kit.RUN / 'u2-fixtures'
    for name in ('bank1', 'sukhumvit'):
        r = K.ref_read(name)
        old_dr = json.loads((kit.UPLOAD_FIXTURES / 'drawing' / f'{name}.drawing.json').read_text(encoding='utf-8'))
        old_pl = json.loads(gzip.decompress((kit.UPLOAD_FIXTURES / 'plan' / f'{name}.plan.json.gz').read_bytes()))
        new_dr, new_pl = r['drawing'], r['plan']
        (made / 'drawing').mkdir(parents=True, exist_ok=True)
        (made / 'plan').mkdir(parents=True, exist_ok=True)
        (made / 'drawing' / f'{name}.drawing.json').write_bytes(
            (json.dumps(new_dr, indent=2, ensure_ascii=False, allow_nan=False) + '\n').encode('utf-8'))
        shutil.copyfile(r['out'] / 'plan.json.gz', made / 'plan' / f'{name}.plan.json.gz')
        assert [a['bbox'] for a in old_dr['areas']] == [a['bbox'] for a in new_dr['areas']]
        for f in ('sig', 'rsig', 'eid', 'type', 'layer', 'first', 'count'):
            assert old_pl['items'][f] == new_pl['items'][f], f
        assert (old_pl['pts'], old_pl['origin'], old_pl['elementIds'], old_pl['layers']) == (
            new_pl['pts'], new_pl['origin'], new_pl['elementIds'], new_pl['layers'])
        keys = [(a, b) for a, b in zip(old_pl['items']['key'], new_pl['items']['key']) if a != b]
        assert all('@~' in a and '@' in b and a.split('@')[0] == b.split('@')[0] for a, b in keys)
        # since the integration step (9 Nov 2026) fixtures/upload/{drawing,plan} ARE this reader's re-made files, so no
        # key differs any more (against the scaffold's provisional ones, the house's two nested ATTRIB keys did)
        assert len(keys) == 0
        for f in ('source', 'blocks', 'gridLabels', 'counts', 'dxf'):
            assert old_dr[f] == new_dr[f], f
        # sorted by value now; a blank text is never a label now (the provisional took one for +7.90)
        order = lambda t: (t['x'], t['y'], t['text'])                      # noqa: E731
        old_tags, new_tags = sorted(old_dr['levelTags'], key=order), sorted(new_dr['levelTags'], key=order)
        unlabelled = lambda ts: [{k: v for k, v in t.items() if k != 'label'} for t in ts]   # noqa: E731
        assert unlabelled(old_tags) == unlabelled(new_tags)
        labels = [(a['text'], a['label'], b['label']) for a, b in zip(old_tags, new_tags) if a['label'] != b['label']]
        assert all(old == '' and new for _t, old, new in labels)
        assert old_dr['units']['used'] == new_dr['units']['used'] and old_dr['units']['verdict'] == new_dr['units']['verdict']
        layer_fields = {}
        old_layers = {la['name']: la for la in old_dr['layers']}
        for la in new_dr['layers']:
            for f, v in la.items():
                if old_layers[la['name']][f] != v:
                    layer_fields.setdefault(f, []).append(la['name'])
        report[name] = {
            'keysChanged': keys, 'labelsChanged': labels, 'unitsVotes': [old_dr['units']['votes'], new_dr['units']['votes']],
            'texts': [len(old_dr['texts']), len(new_dr['texts'])],
            'areasLooksChanged': [(a['id'], a['bbox'], a['looks'], b['looks']) for a, b in zip(old_dr['areas'], new_dr['areas'])
                                  if a['looks'] != b['looks']],
            'areasCountsChanged': [(a['id'], [a['items'], a['wallItems']], [b['items'], b['wallItems']])
                                   for a, b in zip(old_dr['areas'], new_dr['areas'])
                                   if (a['items'], a['wallItems']) != (b['items'], b['wallItems'])],
            'extents': [old_dr['extents'], new_dr['extents']], 'layerFieldsChanged': layer_fields,
            'planBytes': (r['out'] / 'plan.json.gz').stat().st_size, 'readSeconds': r['drawing']['reader']['seconds'],
        }
    (kit.RUN / 'u2-fixture-diff.json').write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding='utf-8')
