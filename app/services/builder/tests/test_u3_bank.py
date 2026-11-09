"""U3: the bank golden (ACCEPTANCE A-1, 2.1 U3; docs/upload/DESIGN.md U-10.3, U-10.8).

The bank built by the port from the reference caches (WT_REF: the prototype prims.pkl of both DWGs) with
fixtures/upload/settings/bank.json and the vendored detector: model.json byte for byte v2's (c3a9408304a2), the
report's summary equal to bank_summary.json, the CSV v2's, the BuildResult of exactly the typed shape (and the key
structure of the scaffold's build-result.bank.json), the detector records equal to detector/output (floor aside), the
replay's lines / rings / sheet equal to v2's stages, integer-valued settings giving the same bytes, every furniture
option at its default giving the same model and CSV, the builder options switching their rules off, the placements
and drawnVariant (the analysis's 26 mirrored pieces in 9 families).
"""
from __future__ import annotations

import collections
import json
import os
import re
import sys

import pytest

import kit
from test_contracts import walk
from test_u3_helpers import (GOLDEN_CSV, GOLDEN_MODEL, csv_bytes, model_bytes, ref_sources, run_build, settings, sha1,
                             strip_floor, write_and_check)
from walkthrough_builder import contracts, oslock

pytestmark = pytest.mark.heavy


def _drawings(ref, out):
    """DrawingRead of both bank DXFs (grid labels with their lines) by the scaffold's provisional reader."""
    sys.path.insert(0, str(kit.APP / 'tools' / 'upload'))
    import fixture_reader as FR
    units = {'declared': 'mm', 'votes': {}, 'dimensionMedian': None, 'used': 'mm', 'verdict': 'agree', 'note': ''}
    paths = {}
    for name in ('bank1', 'bank2'):
        p = out / f'{name}.drawing.json'
        if not p.exists():
            W = FR.walk_drawing(ref / 'proj' / 'detector' / name / 'plan.dxf')
            p.write_text(json.dumps(FR.drawing_read(W, {'sha1': '0' * 40, 'name': name}, units)), encoding='utf-8')
        paths[name] = p
    return paths


@pytest.fixture(scope='module')
def bank(ref, tmp_path_factory):
    tmp = tmp_path_factory.mktemp('u3bank')
    with oslock.hold():                                   # the machine run lock while the module's build runs (U-3.5)
        drawings = _drawings(ref, kit.RUN)
        s = settings('bank')
        res, logs = run_build(s, ref_sources('bank', s, ref, drawings=drawings), tmp, 'bank-sampeng')
    return {'res': res, 'logs': logs, 'drawings': drawings, 'tmp': tmp}


def other_build(ref, bank, s, name):
    return run_build(s, ref_sources('bank', s, ref, drawings=bank['drawings']), bank['tmp'] / name, 'bank-sampeng')[0]


def test_model_is_v2_byte_for_byte(bank):
    assert sha1(model_bytes(bank['res']['model'])) == GOLDEN_MODEL


def test_summary_equals_bank_summary(bank, ref):
    proto = json.loads((kit.PROJECT / 'bank_test' / 'src' / 'bank_summary.json').read_text(encoding='utf-8'))
    again = json.loads((ref / 'proj' / 'bank_test' / 'src' / 'bank_summary.json').read_text(encoding='utf-8'))
    assert bank['res']['report']['summary'] == proto == again
    assert bank['res']['report']['summary']['furniture']['pieces'] == 185
    assert len(bank['res']['report']['summary']['furniture']['kinds']) == 14


def test_furniture_csv_is_v2(bank):
    assert sha1(csv_bytes(bank['res']['model'])) == GOLDEN_CSV


def _shape(v, depth):
    if isinstance(v, dict) and depth:
        return {k: _shape(x, depth - 1) for k, x in v.items()}
    if isinstance(v, list) and v and depth:
        return [_shape(v[0], depth - 1)]
    return type(v).__name__ if not isinstance(v, (int, float)) or isinstance(v, bool) else 'number'


def test_result_has_the_typed_shape_of_the_scaffold_fixture(bank):
    res = {k: v for k, v in bank['res'].items() if k != '_steps'}
    assert walk(res, contracts.BuildResult) == []
    json.dumps(res, allow_nan=False)                                          # plain JSON all through (U4 writes it)
    fx = json.loads((kit.UPLOAD_FIXTURES / 'build-result.bank.json').read_text(encoding='utf-8'))
    assert list(res) == list(fx)
    assert list(res['report']) == list(fx['report']) and list(res['report']['floors']) == ['L1', 'L2']
    assert list(res['report']['summary']) == list(fx['report']['summary'])
    for k in ('L1', 'L2'):
        assert list(res['report']['floors'][k]) == list(fx['report']['floors'][k])
        assert list(res['report']['floors'][k]['alignment']) == list(fx['report']['floors'][k]['alignment'])
        assert list(res['report']['floors'][k]['detector']) == list(fx['report']['floors'][k]['detector'])
        assert list(res['replay']['floors'][k]) == list(fx['replay']['floors'][k])
        assert list(res['floors_frame'][k]) == list(fx['floors_frame'][k])
        assert list(res['detector'][k][0]) == list(fx['detector'][k][0])
    assert list(res['replay']['facts']) == list(fx['replay']['facts'])
    assert list(res['placements'][0]) == list(fx['placements'][0])
    replay = json.loads((kit.UPLOAD_FIXTURES / 'replay-input.bank.json').read_text(encoding='utf-8'))
    assert walk(replay, contracts.ReplayInput) == [] and list(res['replay']) == list(replay)
    # the parts of the result the fixture took from v2 are equal
    assert res['model'] == fx['model']
    assert res['replay']['facts']['counts'] == fx['replay']['facts']['counts']
    assert res['replay']['facts']['parts'] == fx['replay']['facts']['parts']
    assert res['replay']['facts']['openings'] == fx['replay']['facts']['openings']
    assert res['replay']['facts']['layersByRole'] == fx['replay']['facts']['layersByRole']
    assert (res['replay']['facts']['stairs'], res['replay']['facts']['liftShaft']) == (4, True)
    assert res['floors_frame'] == fx['floors_frame']
    assert res['report']['doorHeadsFrom'] == fx['report']['doorHeadsFrom']
    summ = res['report']['summary']['floors']
    for k in ('L1', 'L2'):
        mine, theirs = res['report']['floors'][k], fx['report']['floors'][k]
        assert len(mine['railsLeftOut']) == summ[k]['railingsLeftOut'] + summ[k]['stairRailsOffTheFloor']   # L2: 3
        assert mine['singles'] == [] and mine['lost'] == [] and mine['outlineSuggestions'] == []
        assert mine['roomLabels'] == theirs['roomLabels']
        assert [p['area'] for p in mine['platesDropped']] == [p['area'] for p in theirs['platesDropped']]
        assert mine['alignment'] == theirs['alignment']
        assert (mine['items'], mine['itemsNoPoints'], mine['subtreesOutside']) == (theirs['items'], 0, 0)


def test_detector_records_equal_the_frozen_outputs(bank):
    for k, name in (('L1', 'bank1'), ('L2', 'bank2')):
        oracle = json.loads((kit.PROJECT / 'detector' / 'output' / f'{name}_openings.json').read_text(encoding='utf-8'))
        rows = bank['res']['detector'][k]
        assert strip_floor([r['record'] for r in rows]) == strip_floor(oracle['openings'])
        assert all(r['record']['floor'] == f'bank-sampeng:{k}' and r['modelId'] == r['record']['id'] and r['fix'] is None
                   for r in rows)
        rep = bank['res']['report']['floors'][k]['detector']
        assert rep['records'] == len(rows) and rep['slow'] is False and rep['frameRowsSkipped'] is None


def test_replay_lines_rings_sheet_equal_v2_stages(bank, ref):
    v2 = json.loads((ref / 'proj' / 'bank_test' / 'src' / 'bank_stages.json').read_text(encoding='utf-8'))
    for k in ('L1', 'L2'):
        mine, theirs = bank['res']['replay']['floors'][k], v2['floors'][k]
        flat = {c: [round(v, 2 if c == 'noise' else 3) for s in segs for v in s] for c, segs in mine['lines'].items()}
        assert flat == theirs['lines']
        assert mine['rings'] == theirs['rings']
        assert mine['sheet'] == theirs['sheet']
        assert {c: len(q) for c, q in mine['pieces'].items()} and all(len(q) == 4 for q in mine['pieces']['wall'])


def test_integer_valued_settings_give_the_same_bytes(bank, ref):
    s = settings('bank')
    text = re.sub(r'(?<=[:\[ ])(-?\d+)\.0(?=[,\]}])', lambda m: m.group(1), json.dumps(s))   # 0.0 -> 0 (JSON.stringify)
    s2 = json.loads(text)
    assert s2['floors'][0]['level'] == 0 and type(s2['floors'][0]['level']) is int
    assert s2['defaults']['singleLineHeight'] == 1 and type(s2['defaults']['singleLineHeight']) is int
    res = other_build(ref, bank, s2, 'ints')
    assert sha1(model_bytes(res['model'])) == GOLDEN_MODEL


def test_every_furniture_option_at_its_default(bank, ref):
    s = settings('bank')
    s['furniture'] = {'heights': {}, 'bases': {}, 'words': {'seat': ['Fritz-Hansen']}, 'skip': [], 'minSize': 0.08,
                      'minDepth': None, 'looseLayers': [], 'pieceLayer': 'insert'}
    res = other_build(ref, bank, s, 'furn-default')
    assert sha1(model_bytes(res['model'])) == GOLDEN_MODEL and sha1(csv_bytes(res['model'])) == GOLDEN_CSV


def test_piece_layer_drawn_keeps_the_bank(bank, ref):
    """Should (U-10.5): the suite's reader rules are inert on the bank: the majority-layer rule (the basins inserted on
    P-SANR-FIXT keep that layer; the view block on layer 0 holds furniture inserts and is walked into) and looseLayers
    (the bank's one loose-shape box is drawn outside every block). Measured: the same model and CSV."""
    s = settings('bank')
    s['furniture']['pieceLayer'] = 'drawn'
    s['furniture']['looseLayers'] = sorted(k for k, r in s['layers'].items() if r == 'furniture')   # the suite's rule too
    res = other_build(ref, bank, s, 'furn-drawn')
    assert sha1(model_bytes(res['model'])) == GOLDEN_MODEL and sha1(csv_bytes(res['model'])) == GOLDEN_CSV


def test_options_switch_their_rules_off(bank, ref):
    s = settings('bank')
    s['options'].update(parapets='off', objectClosures=False, liftShafts=False, revitWallTypes='off')
    res = other_build(ref, bank, s, 'options-off')
    kinds = collections.Counter(p['kind'] for p in res['model']['parts'])
    assert kinds['parapet'] == 0 and kinds['mullion'] == 0
    assert not any((p.get('label') or '').startswith('closure') or (p.get('label') or '').startswith('GLASS WALL')
                   for p in res['model']['parts'])
    assert not any(v['what'] == 'lift shaft' for vs in res['model']['voids'].values() for v in vs)
    assert res['report']['summary']['floors']['L1']['glassWalls']['elements'] == 0
    base = collections.Counter(p['kind'] for p in bank['res']['model']['parts'])
    assert base['parapet'] == 1 and base['mullion'] == 1


def test_offset_pinned_by_the_settings(bank, ref):
    s = settings('bank')
    s['options']['offset'] = [1.212, 0.348]
    res = other_build(ref, bank, s, 'pinned')
    assert sha1(model_bytes(res['model'])) == GOLDEN_MODEL
    s['options']['offset'] = [1, 0]
    res = other_build(ref, bank, s, 'pinned2')
    assert res['model']['offset'] == [1.0, 0.0]
    a = bank['res']['model']['parts'][0]['o'][0]
    b = res['model']['parts'][0]['o'][0]
    assert b == pytest.approx([a[0] + 0.212, a[1] + 0.348], abs=0.0011)


def test_placements(bank):
    pl = bank['res']['placements']
    furn = bank['res']['model']['furniture']
    assert [p['id'] for p in pl] == [f['id'] for f in furn] and len(pl) == 185
    assert all(p['boxRot'] == f['rot'] and p['floor'] == f['floor'] for p, f in zip(pl, furn))
    blocks = [p for p in pl if p['block']]
    assert all(p['insertMirrored'] is False and p['sx'] == 1.0 and p['sy'] == 1.0 for p in blocks)
    assert all(p['block'] == f['block'] and p['family'] == f['family'] for p, f in zip(pl, furn) if p['block'])
    assert {p['source'] for p in pl} == {s['sha1'] for s in settings('bank')['sources']}
    atm = next(p for p in pl if p['id'] == 'L1-atm-001')
    assert atm['elementId'] == '2371857' and atm['ins'] == [6.1183, -4.0194] and atm['rot'] == -90.0
    loose = [p for p in pl if not p['block']]
    assert all(p['key'] is None and p['insertMirrored'] is None and p['drawnVariant'] is None for p in loose)


ANALYSIS = {'mollie_chair_a685_revit - A685 2': 9, 'HermanMiller_Seating_AER1A_NewAeron_WorkChair_ASize - SE101_Size Low-Hgt Range': 6,
            'Fritz-Hansen_SH200 - Default': 4, 'Meeting chair_Haworth_Chair_Very-Task - SE14 GM CHAIR': 2,
            'CHAIR_BENCH BACK - SE107 STOOL LOW_VITRA_VISIONA STOOL': 1, 'CONSOLE_CABINET_BAKER - TA13 1800W 400D': 1,
            'Enscape AssetDefinition - Vase 003 Heracleum - Enscape AssetDefinition - Vase 003 Heracleum': 1,
            'Etta Armchair1 - TYPE 2': 1, 'IA_J10_WORK CABINET - IA_J10_WORK CABINET': 1}


def test_drawn_variant_finds_the_analysis_mirrors(bank):
    """Should (U-11.7): furniture_test/bank_furnished/analysis.md's 26 pieces in 9 families drawn as mirror images, all
    front to back (mirrored in y). Two more are found that the analysis does not list: a wall-hung basin drawn mirrored
    (0.2 mm against 0.37 m as drawn) and a printer turned 180 degrees (docs/upload/contract-issues/U3.md)."""
    pl = bank['res']['placements']
    odd = collections.Counter(p['family'] for p in pl if p['drawnVariant'] not in (None, 'same'))
    for fam, n in ANALYSIS.items():
        assert odd[fam] == n, fam
        assert all(p['drawnVariant'] == 'mirrorY' for p in pl if p['family'] == fam and p['drawnVariant'] != 'same')
    extra = {f: n for f, n in odd.items() if f not in ANALYSIS}
    assert sum(ANALYSIS.values()) == 26 and sum(extra.values()) <= 2
    one = {f for f, n in collections.Counter(p['family'] for p in pl if p['block']).items() if n == 1}
    assert all(p['drawnVariant'] is None for p in pl if p['family'] in one)


def test_outputs_pass_the_api_checks(bank, ref):
    """The bank's result through U4's contracts.write_outputs and the API's own checks of a done run (U-3.2): accepted,
    and model.json is v2's bytes."""
    s = settings('bank')
    written, problems = write_and_check(bank['res'], s, ref_sources('bank', s, ref, drawings=bank['drawings']),
                                        bank['tmp'] / 'outputs', 'bank-sampeng')
    assert problems == []
    assert sha1(written['model.json'].read_bytes()) == GOLDEN_MODEL


def test_steps_and_seconds(bank):
    steps = [s for s, _ in bank['res']['_steps']]
    assert steps[0] == 'align' and 'detect:L1' in steps and 'detect:L2' in steps and steps[-1] == 'furniture'
    assert {'read', 'align', 'detect:L1', 'detect:L2', 'walls', 'openings', 'furniture', 'build', 'total'} <= \
        set(bank['res']['seconds'])
    assert set(steps) == {'align', 'detect:L1', 'detect:L2', 'walls', 'openings', 'furniture'}   # U1's child step names
    if os.environ.get('WT_TIMINGS'):
        print(bank['res']['seconds'])
