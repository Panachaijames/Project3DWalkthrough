"""U4: stages.json (ReplayData v1) from the build's ReplayInput (docs/upload/DESIGN.md U-11.3; ACCEPTANCE A-1's stages row).

* the bank: `lines`, `rings`, `sheet` and `source.files / layersInUse / units` equal v2's stages.json;
* texts for 1, 2 and 3 floors: every floor named, the placeholders {<key>level} and {<key>height} for every floor, a
  sentence only when its fact holds (no shift, exported from, the lift shaft, the furniture), no panelIntro;
* each validated by the API's checker (`check_file stages --model`).
"""
from __future__ import annotations

import copy
import json
import re
from pathlib import Path

import test_u4_common as c
from walkthrough_builder.out import replay

V2 = c.load_json(c.MODELS.parent / 'stages' / 'bank-v2.stages.json')
PLACEHOLDER = re.compile(r'\{(\w+?)(level|height)(\+)?\}')


def bank():
    br = c.build_result()
    return br['model'], br['replay'], br['report']


def one_floor():
    """The bank's Level 1 alone, as a one-floor upload."""
    m, r, rep = bank()
    m['floors'] = m['floors'][:1]
    m['source'] = m['source'][:1]
    for k in ('parts', 'openings', 'rooms', 'furniture', 'probes'):
        m[k] = [x for x in m.get(k) or [] if x.get('floor') == 'L1']
    for k in ('stairs', 'voids', 'closures', 'stairOutlines', 'colliderSkins'):
        m[k] = {fl: v for fl, v in (m.get(k) or {}).items() if fl == 'L1'}
    m['furniture'] = []
    m['furnitureKinds'] = []
    r['floors'] = {'L1': r['floors']['L1']}
    f = r['facts']
    f['floors'] = f['floors'][:1]
    f['sources'] = f['sources'][:1]
    for k in ('counts', 'parts', 'openings'):
        f[k] = {'L1': f[k]['L1']}
    f['liftShaft'] = False
    f['stairs'] = 0
    f['exportedFrom'] = None
    f['furniturePieces'] = f['furnitureKinds'] = 0
    rep['summary']['floors'] = {'L1': rep['summary']['floors']['L1']}
    return m, r, rep


def three_floors():
    """The bank with a third floor L3 (a copy of Level 2, 3.70 m higher, from a third file, lined up by origin)."""
    m, r, rep = bank()
    m['floors'].append({**copy.deepcopy(m['floors'][1]), 'key': 'L3', 'name': 'Level 3', 'level': 7.4})
    m['source'] = m['source'] + ['L3.dwg']
    for k in ('parts', 'rooms'):
        m[k] += [{**copy.deepcopy(x), 'floor': 'L3'} for x in m[k] if x['floor'] == 'L2']
    m['openings'] += [{**copy.deepcopy(o), 'floor': 'L3', 'id': o['id'].replace('L2-', 'L3-')} for o in m['openings']
                      if o['floor'] == 'L2']
    m['probes'] = [p for p in m['probes'] if p.get('floor') != 'L3']
    m['furniture'] = []
    m['furnitureKinds'] = []
    r['floors']['L3'] = {**copy.deepcopy(r['floors']['L2']), 'sheet': [40.0, 0.0]}
    f = r['facts']
    f['floors'].append({'key': 'L3', 'name': 'Level 3', 'level': 7.4, 'wallHeight': 3.7, 'source': 'L3.dwg',
                        'align': {'method': 'origin', 'shift': [0.0, 0.0], 'spread': None, 'labels': [], 'families': 0}})
    f['sources'].append({'name': 'L3.dwg', 'units': 'mm', 'kind': 'dwg'})
    for k in ('counts', 'parts', 'openings'):
        f[k]['L3'] = copy.deepcopy(f[k]['L2'])
    f['furniturePieces'] = f['furnitureKinds'] = 0
    rep['summary']['floors']['L3'] = copy.deepcopy(rep['summary']['floors']['L2'])
    return m, r, rep


def texts(st: dict) -> str:
    return '\n'.join([*st['intro'], *(' '.join(row) for row in st['layers']), *st['captions'].values()])


def check_placeholders(st: dict, model: dict) -> None:
    caps = ' '.join(st['captions'].values())
    found = {(m.group(1), m.group(2)) for m in PLACEHOLDER.finditer(caps)}
    keys = [f['key'] for f in model['floors']]
    for k in keys:
        assert (k, 'level') in found, f'no {{{k}level}}'
        assert (k, 'height') in found, f'no {{{k}height}}'
    assert {k for k, _ in found} <= set(keys)


def test_bank_geometry_and_source_equal_v2():
    m, r, rep = bank()
    st = replay.stages(r, m, rep)
    assert list(st['floors']) == ['L1', 'L2']
    for k in ('L1', 'L2'):
        for f in ('lines', 'rings', 'sheet'):
            assert st['floors'][k][f] == V2['floors'][k][f], (k, f)
    assert st['source'] == {'files': V2['source']['files'], 'layersInUse': V2['source']['layersInUse'], 'units': V2['source']['units']}
    assert 'panelIntro' not in st and 'stepTitles' not in st and 'colors' not in st and 'layersTitle' not in st
    assert set(st['captions']) == {'read', 'sort', 'align', 'pair', 'merge', 'raise', 'finish'}


def test_lines_are_rounded_and_noise_cut():
    m, r, rep = bank()
    r['floors']['L1']['lines']['wall'][0] = [1.23456, 2.34567, 3.45678, 4.56789]
    r['floors']['L1']['lines']['noise'] = [[0.123, 0.456, 0.789, 1.011]] * 6999 + [[0.0, 0.0, 9.0, 0.0]]
    r['floors']['L1']['pieces']['wall'][0] = [[1.00049, 2.0], [3.0, 4.0], [5.0, 6.0], [7.0, 8.00051], [1.00049, 2.0]]
    st = replay.stages(r, m, rep)
    f = st['floors']['L1']
    assert f['lines']['wall'][:4] == [1.235, 2.346, 3.457, 4.568]
    assert len(f['lines']['noise']) == replay.NOISE_LINES * 4 and f['lines']['noise'][:8] == [0.0, 0.0, 9.0, 0.0, 0.12, 0.46, 0.79, 1.01]
    assert f['pieces']['wall'][:8] == [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.001]           # four corners, 3 decimals


def test_two_floor_texts():
    m, r, rep = bank()
    st = replay.stages(r, m, rep)
    t = texts(st)
    check_placeholders(st, m)
    assert 'on Level 1 and' in st['captions']['read'] and 'on Level 2' in st['captions']['read']
    assert 'with no shift' in st['captions']['align'] and 'with no shift' in st['intro'][2]
    assert 'exported from Revit' in st['intro'][0]
    assert 'the lift shaft' in st['captions']['finish']
    assert 'Done: 2 levels,' in st['captions']['finish']
    assert '185 furniture' in t
    # a shift said only when there is one
    r2 = copy.deepcopy(r)
    r2['facts']['floors'][1]['align']['shift'] = [-0.25, 0.0]
    r2['facts']['floors'][1]['align']['spread'] = 0.0012
    st2 = replay.stages(r2, m, rep)
    assert 'no shift' not in st2['captions']['align'] and 'moves 0.25, -0.00 m' in st2['captions']['align']
    assert 'no shift' not in st2['intro'][2] and 'moved -0.250, 0.000 m' in st2['intro'][2]
    # exported from, the lift shaft: only when the facts say so
    r3 = copy.deepcopy(r)
    r3['facts']['exportedFrom'] = None
    r3['facts']['liftShaft'] = False
    st3 = replay.stages(r3, m, rep)
    assert 'exported from' not in texts(st3) and 'lift shaft' not in texts(st3)


def test_one_floor_texts():
    m, r, rep = one_floor()
    st = replay.stages(r, m, rep)
    check_placeholders(st, m)
    t = texts(st)
    assert st['captions']['align'] == 'One floor, at {L1level} m: nothing to line up.'
    assert 'Done: 1 level,' in st['captions']['finish'] and 'furniture' not in st['captions']['finish']
    assert 'exported from' not in t and 'lift shaft' not in t and 'grid labels' not in t
    assert st['intro'][0].startswith('1 plan (Level 1) from 1 drawing, in millimetres')
    assert 'on Level 1, read from 1 drawing' in st['captions']['read']
    assert list(st['floors']) == ['L1'] and st['source']['files'] == m['source']


def test_three_floor_texts():
    m, r, rep = three_floors()
    st = replay.stages(r, m, rep)
    check_placeholders(st, m)
    assert 'on 3 floors' in st['captions']['read']
    assert 'Done: 3 levels,' in st['captions']['finish']
    assert "Level 3 shares Level 1's origin" in st['intro'][2]
    assert list(st['floors']) == ['L1', 'L2', 'L3']


def test_every_stages_file_passes_the_api_checker(tmp_path: Path):
    items = []
    for name, (m, r, rep) in (('two', bank()), ('one', one_floor()), ('three', three_floors())):
        mp = tmp_path / f'{name}.model.json'
        mp.write_bytes(json.dumps(m, ensure_ascii=False, separators=(',', ':')).encode('utf-8'))
        sp = tmp_path / f'{name}.stages.json'
        sp.write_bytes(replay.stages_bytes(replay.stages(r, m, rep)))
        items += [('model', mp), ('stages', sp, mp)]
    c.assert_checked(items)


def test_stages_bytes_are_compact_utf8():
    m, r, rep = bank()
    b = replay.stages_bytes(replay.stages(r, m, rep))
    assert not b.endswith(b'\n') and b.startswith(b'{"source":{"files":["I1201')
    assert json.loads(b) == replay.stages(r, m, rep)
