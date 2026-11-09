"""The six drawings through the converter and the loss check, in the test process (`heavy`: the fixture holds the
machine run lock). docs/upload/DESIGN.md U-0, U-6; ACCEPTANCE A-1 (the two bank DXFs and their verdicts), A-3 (every
verdict; the house `minor` despite its error lines; the suite's `loss`, 8,254 missing, the four lost blocks inside the
suite with their inserts, COT T7_HA lost outside it).

The presidential drawing needs about 1 GB and half a minute: only `test_presidential_loss` converts it."""
from __future__ import annotations

from pathlib import Path

import pytest

import kit
import test_u1_support as S
from walkthrough_builder import cache, convert, jsonfile, losscheck

pytestmark = pytest.mark.heavy

DXF = {'bank1': ('9167d084f7e311b59e7c2cdb2bae8506d96a4cfa', 2_817_940),
       'bank2': ('c88491df71a0b77835ce3557731e0ed7bfc2e1fe', 7_923_920)}
#: the reference conversions (WT_REF manifest; make-reference ran the same vendored converter)
SUITE_BOX = (174.840173, -3508.518094, 209.056439, -3480.305594)      # mappings_with_areas/presidential.json
LOST_IN_SUITE = {'TG_artiscardio_2d_1283_8', 'TG_artiscardio_2d_1345_11', 'TG_artiscardio_2d_1388_13', 'A$C59a32014'}


def run_chain(name: str, tmp: Path, libredwg: Path) -> tuple[dict, dict, dict]:
    """convert + audit + check as the worker runs them (in-process here) -> (convert result, report, published)."""
    dwg = kit.PROJECT / kit.DRAWINGS[name]
    work = tmp / name
    res = convert.convert(dwg, work, libredwg=libredwg, seconds=300, memory_mb=2048)
    assert res['code'] is None, res
    aud = convert.audit(Path(res['dxf']))
    src = {'sha1': cache.sha1_file(dwg), 'name': dwg.name, 'bytes': dwg.stat().st_size, 'kind': 'dwg',
           'formatVersion': convert.check_header(dwg)}
    rep = losscheck.check(work / 'input.dwg', Path(res['dxf']), Path(res['log']), libredwg=libredwg, source=src,
                          converter=convert.converter_info(libredwg),
                          convert={'seconds': res['seconds'], 'peak_mb': res['peak_mb'], 'exit_code': res['exit_code']},
                          audit=aud)
    pub = losscheck.publish(rep, 'mm')
    if S.API_PYTHON.is_file():
        p = work / 'published.json'
        jsonfile.write(p, pub)
        code, out = S.check_file('conversion', p)
        assert code == 0, out
    return res, rep, pub


def classes(rep: dict) -> dict[str, int]:
    return {m['class']: m['count'] for m in rep['messages']}


@pytest.mark.parametrize('name,hatch', [('bank1', 148), ('bank2', 143)])
def test_bank_conversions(name: str, hatch: int, libredwg: Path, tmp_path: Path) -> None:
    res, rep, pub = run_chain(name, tmp_path, libredwg)
    sha, size = DXF[name]
    assert cache.sha1_file(Path(res['dxf'])) == sha and Path(res['dxf']).stat().st_size == size
    assert rep['dxf']['sha1'] == sha and rep['dxf']['bytes'] == size
    assert rep['dxf']['acadVersion'] == 'AC1024' and rep['dxf']['insUnits'] == 4 and rep['dxf']['auditFixes'] == 24
    assert rep['verdict'] == 'ok' and rep['totals']['missing'] == 0 and rep['lostBlocks'] == []
    assert rep['totals']['dwgEntities'] == rep['totals']['dxfEntities']
    c = classes(rep)
    assert c['hatch-short-handles'] == hatch
    if name == 'bank1':
        assert c['handle-not-found'] == 28
        assert rep['notes'] == []                                   # handle-not-found and unstable-class change nothing
    else:
        assert all(n.startswith('The converter reported') for n in rep['notes'])
    assert rep['converter']['version'] == '0.14' and rep['exitCode'] == 0
    assert pub == rep                                               # nothing lost: nothing to rescale


@pytest.mark.parametrize('name', ['l29', 'l30'])
def test_tower_ok(name: str, libredwg: Path, tmp_path: Path, ref: Path) -> None:
    res, rep, _ = run_chain(name, tmp_path, libredwg)
    assert rep['verdict'] == 'ok' and rep['totals']['missing'] == 0
    man = jsonfile.read(ref / 'manifest.json')['drawings'][name]
    assert rep['dxf']['sha1'] == man['dxfSha1']                     # LibreDWG is deterministic (U-0)


def test_house_minor_despite_its_error_lines(libredwg: Path, tmp_path: Path) -> None:
    _, rep, _ = run_chain('sukhumvit', tmp_path, libredwg)
    assert rep['verdict'] == 'minor' and rep['totals']['missing'] == 0
    assert rep['totals']['layerChanged'] == 1
    c = classes(rep)
    assert c['handle-not-found'] == 1004 and c['wrong-layer'] == 385
    assert c['error:Invalid ATTRIB.keep_duplicate_records'] == 81
    error_notes = [n for n in rep['notes'] if n.startswith('The converter reported')]
    assert len(error_notes) == 1 and error_notes[0].endswith('nothing is missing.')
    assert any('put on layer 0' in n for n in rep['notes'])
    assert {'layer': '?', 'dwg': 1, 'dxf': 0} in rep['byLayer']


def test_presidential_loss(libredwg: Path, tmp_path: Path) -> None:
    _, rep, pub = run_chain('presidential', tmp_path, libredwg)
    t = rep['totals']
    assert rep['verdict'] == 'loss'
    assert (t['dwgEntities'], t['dxfEntities'], t['missing']) == (142_182, 133_928, 8_254)
    assert rep['notes'][0] == ('8,254 of 142,182 drawing items did not come through the conversion; 4,290 of them '
                               'belong to the plan or to blocks placed in it.')
    lost = {b['name']: b for b in pub['lostBlocks']}
    placed = {n for n, b in lost.items() if b['inserts']}
    assert placed == LOST_IN_SUITE
    x0, y0, x1, y1 = SUITE_BOX
    for n in LOST_IN_SUITE:
        for p in lost[n]['inserts']:
            assert x0 <= p['x'] <= x1 and y0 <= p['y'] <= y1, (n, p)
    assert lost['TG_artiscardio_2d_1283_8']['inserts'] == [{'x': 199.786, 'y': -3485.295, 'layer': 'A-2.Noi That'}]
    assert lost['A$C59a32014']['inserts'] == [{'x': 186.264, 'y': -3496.051, 'layer': 'A-4. Dim'}]
    # COT T7_HA is lost too, outside the plan (inserted only in a block that is never placed)
    assert 'COT T7_HA' in lost and lost['COT T7_HA']['inserts'] == []
    # the wall layer lost pieces (outside the suite: in blocks that are not placed)
    wall = next(r for r in rep['byLayer'] if r['layer'] == 'A-1.Netcat - tuong')
    assert wall['dwg'] > wall['dxf']
    # the 11 empty definitions of U-0, plus anonymous dimension blocks that came out short
    named = {n for n in lost if not n.startswith('*')}
    assert len(named) == 11
    assert not any('converter reported' in n for n in rep['notes'])
    assert rep['unknownObjects'] == 158 and classes(rep)['error:Invalid ATTRIB.keep_duplicate_records'] == 144
