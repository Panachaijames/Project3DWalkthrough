"""U4: write_outputs end to end on the bank's BuildResult (docs/upload/DESIGN.md U-10.9, U-11; contracts.write_outputs).

Every output written into BuildContext.outDir and checked by the API's checker (`check_file`); model.json is v2's bytes
(c3a9408304a2); the .ms is the `upload` profile's script with the build's date and line 2's stamp; the top view is v2's
bytes; pieces.json passes the placements through (insertMirrored, drawnVariant); openings.json and report.json are the
result's; inputs.json records the build, the sources and the builder; a Max refusal writes nothing.
"""
from __future__ import annotations

import copy
import datetime as dt
import json
from pathlib import Path

import pytest

import test_u4_common as c
from walkthrough_builder import contracts
from walkthrough_builder import out as outputs
from walkthrough_builder.out import maxscript as ms

WHEN = dt.datetime(2026, 11, 4, 5, 6, 7, tzinfo=dt.timezone.utc)
NAMES = {'model.json', 'stages.json', 'presentation.json', 'topview.png', 'Bangkok_Bank_Sampeng.ms', 'overlay.json',
         'diff.json', 'openings.json', 'pieces.json', 'report.json', 'inputs.json'}


@pytest.fixture
def fixed_now(monkeypatch):
    monkeypatch.setattr(outputs, '_now', lambda: WHEN)
    return WHEN


def test_write_outputs_bank(tmp_path: Path, fixed_now):
    prev = tmp_path / 'runs' / '0001-build' / 'out' / 'model.json'
    prev.parent.mkdir(parents=True)
    before = c.model('bank-v2')
    before['parts'].pop(0)
    prev.write_text(json.dumps(before), encoding='utf-8')
    ctx = c.bank_ctx(tmp_path / 'run', previous=prev)
    br = c.build_result()
    br['placements'][0]['drawnVariant'] = 'mirrorX'
    br['placements'][1]['insertMirrored'] = True
    logs: list[str] = []
    written = contracts.write_outputs(br, ctx, logs.append)
    out = Path(ctx['outDir'])
    assert set(written) == NAMES and all(p == out / n for n, p in written.items())
    assert {p.name for p in out.iterdir()} == NAMES                                  # no temp file left
    mb = (out / 'model.json').read_bytes()
    assert c.sha1(mb) == c.BANK_MODEL_SHA1 and not mb.endswith(b'\n')
    expected_ms = ms.maxscript(mb, ms.load_profile('upload'), date=ms.date_text(WHEN.astimezone()),
                               sources=[{'kind': 'dwg', 'units': 'mm'}] * 2, converter=ctx['converter'])
    got_ms = (out / 'Bangkok_Bank_Sampeng.ms').read_bytes()
    assert got_ms == expected_ms
    assert ms.stamp_of(got_ms) == 'c3a9408304a2'
    assert f'built by the walkthrough app from "I1201' in got_ms.split(b'\r\n')[0].decode()
    assert c.sha1((out / 'topview.png').read_bytes()) == c.BANK_TOPVIEW_SHA1
    pieces = c.load_json(out / 'pieces.json')
    assert pieces == {'format': 'furniture-placements/1', 'pieces': br['placements']}
    assert pieces['pieces'][0]['drawnVariant'] == 'mirrorX' and pieces['pieces'][1]['insertMirrored'] is True
    assert c.load_json(out / 'openings.json') == {'format': 'openings/1', 'floors': br['detector']}
    assert c.load_json(out / 'report.json') == br['report']
    inp = c.load_json(out / 'inputs.json')
    assert inp['buildId'] == ctx['spec']['buildId'] and inp['runId'] == '0002-build' and inp['settingsRevision'] == 3
    assert inp['builtAt'] == '2026-11-04T05:06:07Z'
    assert [(s['sha1'], s['verdict'], s['units'], s['kind']) for s in inp['sources']] == \
           [(c.BANK_SHA['L1'], 'ok', 'mm', 'dwg'), (c.BANK_SHA['L2'], 'ok', 'mm', 'dwg')]
    assert inp['sources'][0]['bytes'] > 0 and inp['converter']['version'] == '0.14'
    assert inp['builder']['packages']['shapely'] == '2.1.2' and inp['builder']['packages']['matplotlib'] == '3.11.2'
    assert inp['builder']['vendor']['openings.py'].startswith('14a570251f6d')
    assert set(inp['seconds']) >= {'build', 'detect:L1', 'detect:L2', 'outputs'}
    d = c.load_json(out / 'diff.json')
    assert [(a['kind'], a['ref']) for a in d['against']] == [('previous-run', '0001-build'), ('version', 'models')]
    assert len(d['against'][0]['diff']['partsAdded']) == 1 and d['against'][1]['diff']['partsAdded'] == []
    st = c.load_json(out / 'stages.json')
    v2 = c.load_json(c.MODELS.parent / 'stages' / 'bank-v2.stages.json')
    assert all(st['floors'][k][f] == v2['floors'][k][f] for k in ('L1', 'L2') for f in ('lines', 'rings', 'sheet'))
    assert any(x.startswith('flags: ') for x in logs) and not any(':\\' in x or '/Users/' in x for x in logs)
    m = out / 'model.json'
    c.assert_checked([('model', m), ('stages', out / 'stages.json', m), ('presentation', out / 'presentation.json', m),
                      ('overlay', out / 'overlay.json'), ('diff', out / 'diff.json'), ('pieces', out / 'pieces.json'),
                      ('openings', out / 'openings.json'), ('inputs', out / 'inputs.json')])


def test_a_dxf_source_and_no_converter(tmp_path: Path, fixed_now):
    ctx = c.bank_ctx(tmp_path, version=None)
    for s in ctx['sources']:
        s['kind'], s['conversion'], s['dxfSha1'] = 'dxf', None, None
    ctx['converter'] = None
    ctx['spec']['settings']['project']['maxFileName'] = 'Bank.ms'
    written = outputs.write_outputs(c.build_result(), ctx, lambda s: None)
    inp = c.load_json(written['inputs.json'])
    assert inp['converter'] is None and {s['verdict'] for s in inp['sources']} == {'not-converted'}
    text = written['Bank.ms'].read_bytes().decode('ascii')
    assert 'DXF exported by its own program; drawing units mm' in text
    assert c.load_json(written['diff.json']) == {'format': 'build-diff/1', 'against': []}
    c.assert_checked([('inputs', written['inputs.json'])])


def test_a_max_refusal_writes_nothing(tmp_path: Path, fixed_now):
    ctx = c.bank_ctx(tmp_path)
    br = c.build_result()
    br['model']['parts'][0]['o'] = br['model']['parts'][0]['o'][:2]
    with pytest.raises(ms.MaxScriptRefused, match='fewer than 3 points'):
        outputs.write_outputs(br, ctx, lambda s: None)
    assert list(Path(ctx['outDir']).iterdir()) == []


def test_model_bytes_keep_floats():
    m = {'a': 0.0, 'b': 3.7, 'c': 'Đ ห้อง', 'd': [1.0, -0.5]}
    assert outputs.model_bytes(m) == '{"a":0.0,"b":3.7,"c":"Đ ห้อง","d":[1.0,-0.5]}'.encode('utf-8')


def test_one_floor_and_three_floor_results(tmp_path: Path, fixed_now):
    import test_u4_replay as rp
    for name, make in (('one', rp.one_floor), ('three', rp.three_floors)):
        m, r, rep = make()
        br = c.build_result()
        keys = [f['key'] for f in m['floors']]
        br['model'], br['replay'], br['report'] = m, r, rep
        br['detector'] = {k: br['detector'].get(k) or [] for k in keys}
        br['placements'] = [p for p in br['placements'] if p['floor'] in keys and any(f['id'] == p['id'] for f in m['furniture'])]
        br['floors_frame'] = {k: br['floors_frame'].get(k) or {**br['floors_frame']['L2'], 'source': 'f' * 40} for k in keys}
        for k in keys:
            rep['floors'].setdefault(k, copy.deepcopy(rep['floors']['L2']))
        ctx = c.bank_ctx(tmp_path / name, version=None)
        written = outputs.write_outputs(br, ctx, lambda s: None)
        out = Path(ctx['outDir'])
        assert set(written) == NAMES
        assert c.load_json(out / 'presentation.json').get('floorButtons') == (None if name == 'one' else {'all': 'All floors'})
        assert ms.stamp_of((out / 'Bangkok_Bank_Sampeng.ms').read_bytes()) == c.sha1((out / 'model.json').read_bytes())[:12]
        mp = out / 'model.json'
        c.assert_checked([('model', mp), ('stages', out / 'stages.json', mp), ('presentation', out / 'presentation.json', mp),
                          ('overlay', out / 'overlay.json'), ('pieces', out / 'pieces.json'), ('openings', out / 'openings.json'),
                          ('inputs', out / 'inputs.json'), ('diff', out / 'diff.json')])
