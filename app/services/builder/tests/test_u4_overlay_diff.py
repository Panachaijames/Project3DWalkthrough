"""U4: overlay.json with its flags (docs/upload/DESIGN.md U-12.2) and diff.json (U-12.4).

* the bank's overlay from `fixtures/upload/build-result.bank.json`: geometry in each floor's sheet coordinates equal to
  the scaffold's `overlay/bank.overlay.json`; every flag kind of U-12.2 (detector-skipped included) raised from a
  report that holds each case; ids stable and unique; the API's checker passes;
* the diff in sheet coordinates: nothing for the same model, a removed part, a changed opening, a moved opening, a
  version in another frame (offset and sheetShift) matching part for part; BuildDiff refs from the paths.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

import test_u4_common as c
from walkthrough_builder.out import diff as df
from walkthrough_builder.out import overlay as ov

FLAG_KINDS = ('opening', 'single-line', 'lost', 'outline-wall', 'outline-glass', 'grey-furniture', 'rail-left-out',
              'room-label', 'plate-dropped', 'alignment', 'units', 'fix-unmatched', 'detector-skipped', 'slow')


def test_bank_overlay_geometry_equals_the_scaffold_fixture(tmp_path: Path):
    br = c.build_result()
    got = ov.overlay(br, c.bank_ctx(tmp_path))
    want = c.load_json(c.FX / 'overlay' / 'bank.overlay.json')
    assert [f['key'] for f in got['floors']] == ['L1', 'L2']
    for g, w in zip(got['floors'], want['floors']):
        for k in ('source', 'toSheet', 'area', 'parts', 'slabs', 'furniture', 'rooms', 'setAside'):
            assert g[k] == w[k], (g['key'], k)
        assert [(o['id'], o['kind'], o['a'], o['b'], o['flagged']) for o in g['openings']] == \
               [(o['id'], o['kind'], o['a'], o['b'], o['flagged']) for o in w['openings']]
    kinds = sorted({f['kind'] for f in got['flags']})
    assert kinds == ['opening', 'plate-dropped', 'room-label']
    assert {f['ref'].get('openingId') for f in got['flags'] if f['kind'] == 'opening'} == \
           {f['ref'].get('openingId') for f in want['flags'] if f['kind'] == 'opening'}


def flagged_case(tmp: Path) -> tuple[dict, dict]:
    """The bank's result and context with one of each flag case added."""
    br = c.build_result()
    ctx = c.bank_ctx(tmp)
    m = br['model']
    rep = br['report']
    l1 = rep['floors']['L1']
    l2 = rep['floors']['L2']
    i_part = next(i for i, p in enumerate(m['parts']) if p['floor'] == 'L1' and p['kind'] == 'wall')
    l1['singles'] = [{'part': i_part, 'keys': ['BA/2C4'], 'layer': 'A-FLOR', 'a': [1.0, 2.0], 'b': [3.0, 2.0]}]
    l1['lost'] = [{'block': 'A$C59a32014', 'at': [5.0, 6.0], 'layer': 'A-FURN'}]
    l1['outlineSuggestions'] = [{'edge': [[0.0, 0.0], [4.0, 0.0]], 'kind': 'wall', 'length': 4.0, 'state': 'open'},
                                {'edge': [[0.0, 1.0], [4.0, 1.0]], 'kind': 'glass', 'length': 4.0, 'state': 'open'},
                                {'edge': [[0.0, 2.0], [4.0, 2.0]], 'kind': 'wall', 'length': 4.0, 'state': 'accepted'}]
    l1['railsLeftOut'] = [{'keys': ['77'], 'at': [7.0, 7.0]}]
    l1['detector']['frameRowsSkipped'] = 42
    l2['detector']['slow'] = True
    l2['detector']['seconds'] = 75.0
    l2['alignment']['spread'] = 0.012
    l2['alignment']['families'] = 1
    for f in m['furniture'][:3]:
        f['kind'] = 'other'
        f['family'] = 'Mystery chair <b>'
    drawing = c.load_json(Path(ctx['sources'][1]['drawing']))
    drawing['units'].update(declared='in', used='mm', verdict='votes-win', votes={'mm': 22, 'cm': 0, 'm': 4, 'in': 0, 'ft': 0})
    dp = tmp / 'drawing-l2.json'
    dp.write_text(json.dumps(drawing), encoding='utf-8')
    ctx['sources'][1]['drawing'] = str(dp)
    s = ctx['spec']['settings']
    s['fixes'] = {
        'setAside': [{'floor': 'L1', 'source': c.BANK_SHA['L1'], 'key': 'F6D', 'sig': 'a' * 12, 'rsig': '', 'elementId': None,
                      'layer': 'A-GENM', 'note': ''},
                     {'floor': 'L1', 'source': c.BANK_SHA['L1'], 'key': 'XX1', 'sig': 'b' * 12, 'rsig': '', 'elementId': None,
                      'layer': 'A-WALL', 'note': ''},
                     {'floor': 'L2', 'source': c.BANK_SHA['L2'], 'key': 'XX2', 'sig': 'c' * 12, 'rsig': '', 'elementId': None,
                      'layer': 'A-WALL', 'note': ''}],
        'openings': [{'floor': 'L1', 'a': [0.0, 0.0], 'b': [1.0, 0.0], 'kind': 'none', 'head': None, 'sill': None}],
        'outlineEdges': [{'floor': 'L1', 'a': [0.0, 9.0], 'b': [4.0, 9.0], 'as': 'wall'}],
    }
    rep['fixes'] = {'setAside': [{'fix': 0, 'matchedBy': 'key', 'items': 1, 'ambiguous': 0},
                                 {'fix': 1, 'matchedBy': None, 'items': 0, 'ambiguous': 0},
                                 {'fix': 2, 'matchedBy': None, 'items': 0, 'ambiguous': 3}],
                    'openings': [{'fix': 0, 'matched': None}], 'outlineEdges': [{'fix': 0, 'matched': False}]}
    br['detector']['L1'][1]['fix'] = 0
    return br, ctx


def test_every_flag_kind(tmp_path: Path):
    br, ctx = flagged_case(tmp_path)
    got = ov.overlay(br, ctx)
    kinds = {f['kind'] for f in got['flags']}
    assert kinds == set(FLAG_KINDS), set(FLAG_KINDS) - kinds
    by = {k: [f for f in got['flags'] if f['kind'] == k] for k in FLAG_KINDS}
    assert [f['severity'] for f in by['detector-skipped']] == ['check'] and '42 small shapes' in by['detector-skipped'][0]['detail']
    assert 'ignore' in by['detector-skipped'][0]['detail'] and by['detector-skipped'][0]['floor'] == 'L1'
    assert by['slow'][0]['severity'] == 'info' and by['slow'][0]['floor'] == 'L2'
    assert len(by['alignment']) == 2 and all(f['floor'] == 'L2' for f in by['alignment'])
    assert len(by['outline-wall']) == 1 and len(by['outline-glass']) == 1                    # the accepted one is not flagged
    assert by['outline-wall'][0]['ref'] == {'edge': [[0.0, 0.0], [4.0, 0.0]]}
    assert by['single-line'][0]['ref'] == {'keys': ['BA/2C4']} and by['single-line'][0]['at'] == [2.0, 2.0]
    assert by['lost'][0]['at'] == [5.0, 6.0] and 'A$C59a32014' in by['lost'][0]['title']
    assert by['grey-furniture'][0]['ref'] == {'family': 'Mystery chair <b>'} and by['grey-furniture'][0]['severity'] == 'info'
    assert by['units'][0]['floor'] is None and 'votes' in by['units'][0]['detail']
    assert sorted((f['floor'], f['ref'].get('fix')) for f in by['fix-unmatched']) == [('L1', 0), ('L1', 0), ('L1', 1), ('L2', 2)]
    assert any('matches 3 items' in f['title'] for f in by['fix-unmatched'])
    l1 = next(f for f in got['floors'] if f['key'] == 'L1')
    assert l1['setAside'] == ['F6D']
    assert sum(1 for o in l1['openings'] if o['fixed']) == 1
    ids = [f['id'] for f in got['flags']]
    assert len(ids) == len(set(ids))
    for f in got['flags']:
        kind, floor, h = f['id'].split(':')
        assert kind == f['kind'] and floor == (f['floor'] or '-') and len(h) == 12
    assert [f['id'] for f in ov.overlay(*flagged_case(tmp_path / 'again'))['flags']] == ids          # stable
    p = tmp_path / 'overlay.json'
    p.write_text(json.dumps(got, ensure_ascii=False), encoding='utf-8')
    c.assert_checked([('overlay', p)])
    counts = ov.flag_counts(got)
    assert counts['total'] == len(ids) and set(counts['byKind']) == set(FLAG_KINDS)


def test_opening_reasons():
    assert ov.opening_reasons({'kind': 'door', 'confidence': 0.9, 'host': 'wall', 'evidence': []}) == []
    r = {'kind': 'passage', 'confidence': 0.5, 'eitherKind': True, 'host': 'line work', 'evidence': ['ends from the swing']}
    assert ov.opening_reasons(r) == ['a passage', 'confidence 0.5', 'a door or a window', 'host line work', 'ends from the swing']
    assert ov.opening_reasons({'kind': 'door', 'confidence': 1, 'host': 'wall', 'sidelights': [1]}) == ['sidelights']


# ---------------------------------------------------------------------------------------------------------------- diff
def bank() -> dict:
    return c.model('bank-v2')


def reframed(m: dict, dx: float, dy: float, floor_shift: dict | None = None) -> dict:
    """The same building in another model frame: offset + (dx, dy) (and sheetShift per floor), coordinates moved back."""
    m = copy.deepcopy(m)
    m['offset'] = [m['offset'][0] + dx, m['offset'][1] + dy]
    moved = {}
    for f in m['floors']:
        old = f.get('sheetShift') or [0.0, 0.0]
        if floor_shift and f['key'] in floor_shift:
            f['sheetShift'] = list(floor_shift[f['key']])
        new = f.get('sheetShift') or [0.0, 0.0]
        moved[f['key']] = (dx + new[0] - old[0], dy + new[1] - old[1])
    sh = lambda fl: moved[fl]                                                    # noqa: E731
    for p in m['parts']:
        sx, sy = sh(p['floor'])
        p['o'] = [[round(x - sx, 3), round(y - sy, 3)] for x, y in p['o']]
        p['h'] = [[[round(x - sx, 3), round(y - sy, 3)] for x, y in h] for h in p['h']]
    for k in ('openings', 'rooms', 'furniture'):
        for o in m.get(k) or []:
            sx, sy = sh(o['floor'])
            o['x'], o['y'] = round(o['x'] - sx, 3), round(o['y'] - sy, 3)
    return m


def test_same_model_no_change():
    d = df.diff(bank(), bank())
    assert df.empty(d)
    assert d['counts']['L1']['wall'] == [10, 10] and d['furnitureByKind']['seat'] == [75, 75]


def test_removed_part_changed_and_moved_opening():
    before, after = bank(), bank()
    i = next(i for i, p in enumerate(after['parts']) if p['floor'] == 'L2' and p['kind'] == 'wall')
    gone = after['parts'].pop(i)
    o = next(o for o in after['openings'] if o['id'] == 'L1-002')
    o['head'] = round(o['head'] + 0.3, 3)
    moved = next(o for o in after['openings'] if o['id'] == 'L2-003')
    moved['x'] += 0.3
    after['rooms'][0]['name'] = 'NEW ROOM'
    after['furniture'] = [f for f in after['furniture'] if f['kind'] != 'tv']
    d = df.diff(after, before)
    ox, oy = before['offset']
    assert d['partsRemoved'] == [{'floor': 'L2', 'kind': 'wall', 'o': [[round(x + ox, 4), round(y + oy, 4)] for x, y in gone['o']]}]
    assert d['partsAdded'] == []
    assert d['counts']['L2']['wall'] == [14, 13]
    assert d['openingsChanged'] == [{'floor': 'L1', 'id': 'L1-002', 'field': 'head', 'before': round(o['head'] - 0.3, 3),
                                     'after': o['head']}]
    assert [x['id'] for x in d['openingsAdded']] == ['L2-003'] and [x['id'] for x in d['openingsRemoved']] == ['L2-003']
    assert d['roomsAdded'] == ['NEW ROOM'] and d['roomsRemoved'] == [before['rooms'][0]['name']]
    assert d['furnitureByKind']['tv'] == [2, 0]
    assert not df.empty(d)


def test_a_version_in_another_frame_matches_part_for_part():
    before = reframed(bank(), 12.345, -6.789)
    d = df.diff(bank(), before)
    assert df.empty(d), (d['partsAdded'][:1], d['partsRemoved'][:1], d['openingsAdded'][:1])
    shifted = reframed(bank(), -1.212, 0.5, {'L2': (74.021, 0.0)})
    assert shifted['floors'][1]['sheetShift'] == [74.021, 0.0]
    assert df.empty(df.diff(shifted, bank()))
    # a 2 cm move is a change, not a frame
    moved = bank()
    p = next(p for p in moved['parts'] if p['kind'] == 'column')
    p['o'] = [[x + 0.02, y] for x, y in p['o']]
    d = df.diff(moved, bank())
    assert len(d['partsAdded']) == 1 and len(d['partsRemoved']) == 1


def test_build_diff_refs_and_the_api_checker(tmp_path: Path):
    prev = tmp_path / 'runs' / '0001-build' / 'out' / 'model.json'
    ver = tmp_path / 'projects' / 'p' / 'versions' / '2' / 'model.json'
    for p, m in ((prev, bank()), (ver, reframed(bank(), 3.0, 4.0))):
        p.parent.mkdir(parents=True)
        p.write_text(json.dumps(m), encoding='utf-8')
    after = bank()
    after['parts'].pop(0)
    logs = []
    out = df.build_diff(after, {'previousRunModel': str(prev), 'versionModel': str(ver)}, logs.append)
    assert [(a['kind'], a['ref']) for a in out['against']] == [('previous-run', '0001-build'), ('version', 'v2')]
    assert all(len(a['diff']['partsRemoved']) == 1 for a in out['against'])
    path = tmp_path / 'diff.json'
    path.write_text(json.dumps(out), encoding='utf-8')
    c.assert_checked([('diff', path)])
    broken = tmp_path / 'broken.json'
    broken.write_text('{', encoding='utf-8')
    out2 = df.build_diff(after, {'previousRunModel': str(broken), 'versionModel': None}, logs.append)
    assert out2 == {'format': 'build-diff/1', 'against': []} and 'could not be read' in logs[-1]
    assert df.build_diff(after, {'previousRunModel': None, 'versionModel': None}) == {'format': 'build-diff/1', 'against': []}
