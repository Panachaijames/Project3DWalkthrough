"""losscheck.py: the "nothing lost" check on synthetic inputs (docs/upload/DESIGN.md U-6.3; ACCEPTANCE A-3, 2.1 U1).

A dwgread-style JSON stream and a DXF are made here with the same handles; the tests remove or change items on one
side and look at the verdict (from the comparison only), the notes, the lost blocks with their composed model-space
placements, and the reports' shapes (the API's check_file `conversion`). The real drawings are in test_u1_heavy.py."""
from __future__ import annotations

import json
import math
import subprocess
import sys
from pathlib import Path

import pytest

import kit
import test_u1_support as S
from walkthrough_builder import jsonfile, losscheck as L

# ============================================================================================================ messages
LINES = [
    ('Warning: Skip HATCH common handles due to short handle stream', 'hatch-short-handles'),
    ('Warning: Object handle not found 7326/0x1C9E in 5244 objects of max 0x1EBF handles', 'handle-not-found'),
    ('Warning: Unstable Class object 501 MATERIAL (0x481) 14/0', 'unstable-class'),
    ('Warning: Unhandled Object TABLESTYLE in out_dxf 98/65', 'unhandled-class'),
    ('Warning: Unhandled Class object 561 ACDB_MTEXTATTRIBUTEOBJECTCONTEXTDATA_CLASS (0x481) 98877/0', 'unhandled-class'),
    ('Warning: TODO TABLESTYLE r2010+ missing fields', 'unhandled-class'),
    ('Warning: AcDs _data_ segment yet unhandled', 'unhandled-class'),
    ('Warning: Unknown flag (0x8)', 'unknown-flag'),
    ('Warning: Unknown object, skipping eed/reactors/xdic', 'unknown-object'),
    ('Warning: Wrong POLYLINE.layer 7BE4', 'wrong-layer'),
    ('ERROR: Invalid ATTRIB.keep_duplicate_records 144', 'error:Invalid ATTRIB.keep_duplicate_records'),
    ('ERROR: bit_read_RC buffer overflow at 300.3 + 1 > 301', 'error:buffer overflow'),
    ("ERROR: bit_read_BL: unexpected 2-bit code: '11'", 'error:bit_read_*'),
    ('ERROR: Invalid CMC method 0x0 ignored', 'error:Invalid CMC'),
    ('ERROR: Invalid CMC flag 0x9f ignored', 'error:Invalid CMC'),
    ('ERROR: Invalid REGION.silhouettes x 256', 'error:Invalid REGION.silhouettes'),
    ('ERROR: Invalid MTEXT.class_version 256', 'error:Invalid MTEXT.class_version'),
    ('ERROR: something odd happened: 7', 'error:something odd happened'),
    ('Warning: a sentence nobody classified', 'other'),
    ('Reading DWG file input.dwg', None),
    ('Writing DXF file plan.dxf', None),
    ('   ', None),
]


@pytest.mark.parametrize('line,cls', LINES)
def test_classify(line: str, cls: str | None) -> None:
    assert L.classify(line) == cls


def test_messages_count_and_scrub_paths() -> None:
    lines = ['Warning: Skip HATCH common handles due to short handle stream'] * 3 + [
        r'ERROR: Invalid ATTRIB.keep_duplicate_records 81 in C:\Users\someone\data\projects\p\input.dwg',
        'ERROR: Invalid ATTRIB.keep_duplicate_records 82', 'Reading DWG file input.dwg']
    got = L.messages(lines)
    assert got[0] == {'class': 'hatch-short-handles', 'count': 3,
                      'example': 'Warning: Skip HATCH common handles due to short handle stream'}
    assert got[1]['class'] == 'error:Invalid ATTRIB.keep_duplicate_records' and got[1]['count'] == 2
    assert 'C:\\' not in got[1]['example'] and got[1]['example'].endswith('in input.dwg')


@pytest.mark.parametrize('text,want', [
    (r'failed at C:\Users\x\AppData\Local\Temp\run\plan.dxf line 3', 'failed at plan.dxf line 3'),
    ('see c:/data/projects/p/builds/b/out/model.json.', 'see model.json.'),
    (r'share \\server\share\folder\f.dwg here', 'share f.dwg here'),
    ('no path here', 'no path here'),
])
def test_scrub(text: str, want: str) -> None:
    assert L.scrub(text) == want


def test_anon_names() -> None:
    assert L.anon('*U12') == '*U' and L.anon('*d3') == '*D' and L.anon('*Paper_Space0') == '*PAPER_SPACE'
    assert L.anon('Chair-123') == 'CHAIR-123' and L.anon('*Model_Space') == '*MODEL_SPACE'


# ============================================================================================ synthetic DWG and DXF
MS, PS, BLK, OUTER, UNUSED, MBLK = 2, 3, 0x10, 0x20, 0x30, 0x40
LAYER0, WALL, FURN = 5, 6, 7


def _val(k: str, v) -> str:
    if k == 'handle':
        return f'[0,1,{v}]'
    if k in ('layer', 'ownerhandle', 'block_header'):
        return f'[5,1,{v},{v}]'
    if isinstance(v, list):
        return '[ ' + ', '.join(repr(float(x)) for x in v) + ' ] '
    if isinstance(v, str):
        return json.dumps(v)
    return repr(v)


def dwg_json(objs: list[dict]) -> str:
    """dwgread's pretty-printed layout: sections at 2 spaces, objects at 4, their keys at 6 (deeper keys at 8)."""
    out = ['{', '  "created_by": "LibreDWG 0.14",', '  "HEADER": {', '    "handle": [0,1,99]', '  },',
           '  "OBJECTS": [']
    for i, o in enumerate(objs):
        out.append('    {')
        items = list(o.items())
        for j, (k, v) in enumerate(items):
            out.append(f'      "{k}": {_val(k, v)}' + (',' if j < len(items) - 1 else ''))
            if k == 'handle':
                out += ['      "eed": [', '        {', '          "handle": [5,1,77],', '          "code": 2', '        }',
                        '      ],']
        out.append('    }' + (',' if i < len(objs) - 1 else ''))
    out += ['  ],', '  "AcDs": {', '    "handle": [0,1,5]', '  }', '}']
    return '\n'.join(out) + '\n'


def base_objects() -> list[dict]:
    """Model space: a wall LINE, an INSERT of OUTER (turned 90 degrees, scale 2, at 1000,2000), a MINSERT of MBLK
    (2 columns 50 apart), a POLYLINE with a VERTEX, an INSERT with an ATTRIB. OUTER holds an INSERT of BLK on layer 0
    (at 100,0); BLK (base point 10,0) holds a LINE and an ARC; UNUSED (never inserted) holds a LINE."""
    return [
        {'object': 'BLOCK_HEADER', 'handle': MS, 'name': '*Model_Space', 'base_pt': [0, 0, 0]},
        {'object': 'BLOCK_HEADER', 'handle': PS, 'name': '*Paper_Space', 'base_pt': [0, 0, 0]},
        {'object': 'BLOCK_HEADER', 'handle': BLK, 'name': 'Chair-1', 'base_pt': [10, 0, 0]},
        {'object': 'BLOCK_HEADER', 'handle': OUTER, 'name': 'Outer', 'base_pt': [0, 0, 0]},
        {'object': 'BLOCK_HEADER', 'handle': UNUSED, 'name': 'Unused', 'base_pt': [0, 0, 0]},
        {'object': 'BLOCK_HEADER', 'handle': MBLK, 'name': 'Tile', 'base_pt': [0, 0, 0]},
        {'object': 'LAYER', 'handle': LAYER0, 'name': '0'},
        {'object': 'LAYER', 'handle': WALL, 'name': 'A-WALL'},
        {'object': 'LAYER', 'handle': FURN, 'name': 'I-FURN'},
        {'entity': 'LINE', 'handle': 0x100, 'layer': WALL, 'entmode': 2},
        {'entity': 'INSERT', 'handle': 0x101, 'layer': FURN, 'entmode': 2, 'ins_pt': [1000, 2000, 0],
         'scale': [2, 2, 1], 'rotation': math.pi / 2, 'extrusion': [0, 0, 1], 'block_header': OUTER},
        {'entity': 'MINSERT', 'handle': 0x102, 'layer': FURN, 'entmode': 2, 'ins_pt': [0, 0, 0], 'scale': [1, 1, 1],
         'rotation': 0.0, 'extrusion': [0, 0, 1], 'num_cols': 2, 'num_rows': 1, 'col_spacing': 50.0,
         'row_spacing': 0.0, 'block_header': MBLK},
        {'entity': 'POLYLINE_2D', 'handle': 0x103, 'layer': WALL, 'entmode': 2},
        {'entity': 'VERTEX_2D', 'handle': 0x104, 'layer': WALL, 'entmode': 0, 'ownerhandle': 0x103},
        {'entity': 'SEQEND', 'handle': 0x105, 'layer': WALL, 'entmode': 0, 'ownerhandle': 0x103},
        {'entity': 'INSERT', 'handle': 0x106, 'layer': FURN, 'entmode': 2, 'ins_pt': [-100, 0, 0],
         'scale': [1, 1, 1], 'rotation': 0.0, 'extrusion': [0, 0, -1], 'block_header': BLK},
        {'entity': 'ATTRIB', 'handle': 0x107, 'layer': FURN, 'entmode': 0, 'ownerhandle': 0x106},
        {'entity': 'INSERT', 'handle': 0x200, 'layer': LAYER0, 'entmode': 0, 'ownerhandle': OUTER,
         'ins_pt': [100, 0, 0], 'scale': [1, 1, 1], 'rotation': 0.0, 'extrusion': [0, 0, 1], 'block_header': BLK},
        {'entity': 'LINE', 'handle': 0x300, 'layer': LAYER0, 'entmode': 0, 'ownerhandle': BLK},
        {'entity': 'ARC', 'handle': 0x301, 'layer': FURN, 'entmode': 0, 'ownerhandle': BLK},
        {'entity': 'LINE', 'handle': 0x400, 'layer': WALL, 'entmode': 0, 'ownerhandle': UNUSED},
        {'entity': 'LINE', 'handle': 0x500, 'layer': WALL, 'entmode': 0, 'ownerhandle': MBLK},
        {'entity': 'BLOCK', 'handle': 0x600, 'layer': LAYER0, 'entmode': 0, 'ownerhandle': BLK, 'name': 'Chair-1'},
        {'entity': 'UNKNOWN_ENT', 'handle': 0x700, 'layer': LAYER0, 'entmode': 2},
    ]


def dxf_text(objs: list[dict], *, drop: set[int] = frozenset(), layer_of: dict | None = None,
             version: str = 'AC1032', codepage: str = 'ANSI_1252', encode: str = 'utf-8') -> bytes:
    """A DXF with the same handles as `objs` (minus `drop`), entities in ENTITIES or BLOCKS by their owner."""
    layer_of = layer_of or {}
    names = {o['handle']: o['name'] for o in objs if o.get('object') == 'LAYER'}
    blocks = {o['handle']: o['name'] for o in objs if o.get('object') == 'BLOCK_HEADER'}
    out = ['0', 'SECTION', '2', 'HEADER', '9', '$ACADVER', '1', version, '9', '$DWGCODEPAGE', '3', codepage,
           '9', '$INSUNITS', '70', '4', '0', 'ENDSEC', '0', 'SECTION', '2', 'TABLES', '0', 'TABLE', '2', 'LAYER']
    for h, n in names.items():
        out += ['0', 'LAYER', '5', f'{h:X}', '2', n, '70', '0']
    out += ['0', 'ENDTAB', '0', 'TABLE', '2', 'BLOCK_RECORD']
    for h, n in blocks.items():
        out += ['0', 'BLOCK_RECORD', '5', f'{h:X}', '330', '1', '100', 'AcDbSymbolTableRecord', '2', n]
    out += ['0', 'ENDTAB', '0', 'ENDSEC', '0', 'SECTION', '2', 'BLOCKS']
    ents = [o for o in objs if 'entity' in o and o['entity'] not in ('BLOCK',) and o['handle'] not in drop]

    def entity(o: dict) -> list[str]:
        t = L.dxf_type(o['entity'])
        own = o.get('ownerhandle')
        own = MS if o.get('entmode') == 2 else own
        lay = layer_of.get(o['handle'], names.get(o['layer'], '0'))
        return ['0', t, '5', f'{o["handle"]:X}', '102', '{ACAD_REACTORS', '330', 'FFFF', '102', '}', '330',
                f'{own:X}', '8', lay]

    for h, n in blocks.items():
        if h in (MS, PS):
            continue
        out += ['0', 'BLOCK', '5', f'{h + 0x1000:X}', '330', f'{h:X}', '8', '0', '2', n]
        for o in ents:
            if o.get('ownerhandle') == h and o.get('entmode') == 0:
                out += entity(o)
        out += ['0', 'ENDBLK', '5', f'{h + 0x2000:X}', '330', f'{h:X}', '8', '0']
    out += ['0', 'ENDSEC', '0', 'SECTION', '2', 'ENTITIES']
    for o in ents:
        if o.get('entmode') == 2 or o.get('ownerhandle') in (0x103, 0x106):
            out += entity(o)
    out += ['0', 'ENDSEC', '0', 'EOF']
    return ('\r\n'.join(out) + '\r\n').encode(encode)


def sides(tmp: Path, objs=None, **kw) -> tuple[L.DwgSide, L.DxfSide]:
    objs = objs or base_objects()
    dwg = L.DwgSide.scan(dwg_json(objs).splitlines(keepends=True))
    p = tmp / 'plan.dxf'
    p.write_bytes(dxf_text(objs, **kw))
    return dwg, L.DxfSide.scan(p)


def test_dwg_side_scan(tmp_path: Path) -> None:
    dwg, _ = sides(tmp_path)
    assert dwg.model == MS and dwg.blocks[BLK] == 'Chair-1' and dwg.layers[WALL] == 'A-WALL'
    assert dwg.unknown == 1
    # BLOCK and SEQEND are structure, not compared; the eed's own "handle" keys (deeper) are not objects' handles
    assert 0x600 not in dwg.ents and 0x105 not in dwg.ents and 77 not in dwg.raw
    assert dwg.ents[0x100] == ('LINE', 'A-WALL', '*MODEL_SPACE')
    assert dwg.ents[0x104] == ('VERTEX', 'A-WALL', '*MODEL_SPACE')            # through its POLYLINE
    assert dwg.ents[0x107] == ('ATTRIB', 'I-FURN', '*MODEL_SPACE')            # through its INSERT
    assert dwg.ents[0x300] == ('LINE', '0', 'CHAIR-1')
    assert dwg.reachable() == {MS, OUTER, BLK, MBLK}


def test_identical_sides_are_ok(tmp_path: Path) -> None:
    dwg, dxf = sides(tmp_path)
    assert dxf.brec[OUTER] == 'Outer' and dxf.header['$ACADVER'] == 'AC1032'
    c = L.compare(dwg, dxf)
    assert not c['missing'] and not c['extra'] and not c['layerChanged'] and not c['ownerChanged'], c
    v, notes = L.verdict_and_notes(c, [], len(dwg.ents))
    assert v == 'ok' and notes == []
    msgs = L.messages(['ERROR: Invalid ATTRIB.keep_duplicate_records 1'] * 81 + ['Warning: Unknown flag (0x8)'])
    v, notes = L.verdict_and_notes(c, msgs, len(dwg.ents))
    assert v == 'ok' and notes == ['The converter reported 81 errors of one kind; nothing is missing.']


def test_missing_in_a_placed_block_is_a_loss_with_its_placements(tmp_path: Path) -> None:
    dwg, dxf = sides(tmp_path, drop={0x300, 0x301})              # BLK came out empty
    c = L.compare(dwg, dxf)
    assert sorted(c['missing']) == [0x300, 0x301] and sorted(c['missingPlan']) == [0x300, 0x301]
    v, notes = L.verdict_and_notes(c, L.messages(['ERROR: Invalid CMC flag 0x9f ignored']), len(dwg.ents))
    assert v == 'loss'
    assert notes[0].startswith('2 of 13 drawing items did not come through the conversion; 2 of them belong to the plan')
    assert 'Chair-1' in notes[1] and notes[-1].startswith('Export a DXF from AutoCAD')
    assert not any('converter reported' in n for n in notes)       # the loss notes say it
    (lost,) = c['lostBlocks']
    assert lost['name'] == 'Chair-1' and lost['entities'] == 2 and lost['empty']
    assert lost['byLayer'] == {'0': 1, 'I-FURN': 1}
    got = sorted((round(p['x'], 6), round(p['y'], 6), p['layer']) for p in lost['inserts'])
    # through OUTER (turned 90 degrees, scale 2, at 1000,2000): BLK's insert at 100,0 lands at 1000,2200, layer 0 ->
    # OUTER's I-FURN; and the model-space INSERT at -100,0 with an OCS extrusion of -z: x mirrored
    assert got == [(100.0, 0.0, 'I-FURN'), (1000.0, 2200.0, 'I-FURN')]


def test_lost_block_placements_minsert(tmp_path: Path) -> None:
    dwg, dxf = sides(tmp_path, drop={0x500})
    c = L.compare(dwg, dxf)
    (lost,) = c['lostBlocks']
    assert lost['name'] == 'Tile'
    assert sorted((p['x'], p['y']) for p in lost['inserts']) == [(0.0, 0.0), (50.0, 0.0)]


def test_missing_in_an_unplaced_block_is_minor(tmp_path: Path) -> None:
    dwg, dxf = sides(tmp_path, drop={0x400})
    c = L.compare(dwg, dxf)
    assert c['missing'] == [0x400] and c['missingPlan'] == []
    v, notes = L.verdict_and_notes(c, L.messages(['ERROR: Invalid CMC flag 0x9f ignored']), len(dwg.ents))
    assert v == 'minor'
    assert notes[0].startswith('1 item of blocks that are not placed in the plan')
    assert notes[-1] == 'The converter reported 1 error of one kind; nothing in the plan is missing.'
    (lost,) = c['lostBlocks']
    assert lost['name'] == 'Unused' and lost['inserts'] == []


def test_unknown_layer_put_on_layer_0_is_minor(tmp_path: Path) -> None:
    objs = base_objects()
    objs[9] = dict(objs[9], layer=999)                          # the DWG decode did not know the layer: '?'
    dwg, dxf = sides(tmp_path, objs, layer_of={0x100: '0'})
    c = L.compare(dwg, dxf)
    assert c['layerChanged'] == [0x100] and c['benignLayer'] == [0x100]
    v, notes = L.verdict_and_notes(c, [], len(dwg.ents))
    assert v == 'minor'
    assert notes == ['Nothing in the plan is missing; 1 item whose layer the converter could not read was put on '
                     'layer 0.']
    assert {'layer': '?', 'dwg': 1, 'dxf': 0} in c['byLayer']


def test_messages_never_decide_the_verdict(tmp_path: Path) -> None:
    dwg, dxf = sides(tmp_path)
    c = L.compare(dwg, dxf)
    msgs = L.messages(['Warning: Object handle not found 1/0x1 in 2 objects of max 0x3 handles'] * 1004
                      + ['Warning: Wrong POLYLINE.layer 7BE4'] * 385 + ['Warning: Skip HATCH common handles due to '
                                                                         'short handle stream'] * 46)
    assert L.verdict_and_notes(c, msgs, len(dwg.ents)) == ('ok', [])


def test_dxf_side_old_codepage_and_unicode_escapes(tmp_path: Path) -> None:
    objs = base_objects()
    objs[8] = dict(objs[8], name='ชั้น')                          # a Thai layer name
    objs[7] = dict(objs[7], name='A-\\U+0E01')                    # written by an old DXF as an escape
    dwg = L.DwgSide.scan(dwg_json(objs).splitlines(keepends=True))
    p = tmp_path / 'old.dxf'
    p.write_bytes(dxf_text(objs, version='AC1018', codepage='ANSI_874', encode='cp874'))
    dxf = L.DxfSide.scan(p)
    assert L.dxf_encoding(dxf.header) == 'cp874'
    assert 'ชั้น' in dxf.layers and 'A-ก' in dxf.layers
    assert dxf.ents[0x101][1] == 'ชั้น'
    assert dwg.ents[0x101][1] == 'ชั้น'


def test_dxf_side_of_the_small_synthetic_drawing(tmp_path: Path) -> None:
    out = tmp_path / 'small.dxf'
    p = subprocess.run([sys.executable, '-B', '-P', str(kit.APP / 'tools' / 'upload' / 'make-test-dxf.py'), 'small',
                        str(out)], capture_output=True, text=True, env=kit.child_env(), timeout=300)
    assert p.returncode == 0, p.stderr
    dxf = L.DxfSide.scan(out)
    owners = {o for _, _, o in dxf.ents.values()}
    assert len(dxf.ents) > 20 and '*MODEL_SPACE' in owners and 'A-WALL' in dxf.layers


# ======================================================================================================== the reports
def report_of(tmp: Path, drop=frozenset()) -> dict:
    dwg, dxf = sides(tmp, drop=set(drop))
    c = L.compare(dwg, dxf)
    rep = L.report(source={'sha1': S.BANK1_SHA1, 'name': 'x.dwg', 'bytes': 10, 'kind': 'dwg', 'formatVersion': 'AC1032'},
                   converter={'name': 'libredwg', 'version': '0.14', 'exeSha1': 'f' * 40},
                   dxf={'sha1': 'e' * 40, 'bytes': 99, 'acadVersion': 'AC1032', 'insUnits': 4, 'auditErrors': 0,
                        'auditFixes': 3},
                   convert={'seconds': 0.25, 'peak_mb': 12.0, 'exit_code': 0}, msgs=[], dwg=dwg, comparison=c)
    rep['totals']['dxfEntities'] = len(dxf.ents)
    return rep


@pytest.mark.parametrize('units,k', [('mm', 0.001), ('cm', 0.01), ('m', 1.0), ('in', 0.0254), ('ft', 0.3048)])
def test_publish_in_sheet_metres(tmp_path: Path, units: str, k: float) -> None:
    rep = report_of(tmp_path, {0x300, 0x301})
    pub = L.publish(rep, units)
    raw = sorted((p['x'], p['y']) for p in rep['lostBlocks'][0]['inserts'])
    got = sorted((p['x'], p['y']) for p in pub['lostBlocks'][0]['inserts'])
    assert got == [(round(x * k, 3), round(y * k, 3)) for x, y in raw]
    # the cached report keeps drawing units and is not changed by publishing
    assert [(round(x, 6), round(y, 6)) for x, y in raw] == [(100.0, 0.0), (1000.0, 2200.0)]
    assert sorted((p['x'], p['y']) for p in rep['lostBlocks'][0]['inserts']) == raw


def api_check(tmp: Path, rep: dict) -> None:
    if not S.API_PYTHON.is_file():
        pytest.skip('no API Python')
    p = tmp / 'conversion.json'
    jsonfile.write(p, rep)
    code, out = S.check_file('conversion', p)
    assert code == 0, out


def test_reports_pass_the_apis_check(tmp_path: Path) -> None:
    rep = report_of(tmp_path, {0x300, 0x301})
    assert rep['verdict'] == 'loss' and rep['totals'] == {'dwgEntities': 13, 'dxfEntities': 11, 'missing': 2,
                                                          'extra': 0, 'layerChanged': 0, 'emptyLayer': 0}
    assert set(rep) == {'format', 'source', 'converter', 'dxf', 'seconds', 'peakMemoryMB', 'exitCode', 'messages',
                        'totals', 'byLayer', 'lostBlocks', 'renamedBlocks', 'unknownObjects', 'verdict', 'notes'}
    api_check(tmp_path, L.publish(rep, 'mm'))
    src = {'sha1': S.SMALL_SHA1, 'name': 'small.dxf', 'bytes': 10, 'kind': 'dxf', 'formatVersion': 'AC1032'}
    nc = L.not_converted(src, {'dxf': {'acadVersion': 'AC1032', 'insUnits': 4, 'auditErrors': 1, 'auditFixes': 2}},
                         S.SMALL_SHA1, 10)
    assert nc['verdict'] == 'not-converted' and nc['converter'] is None and nc['dxf']['auditFixes'] == 2
    assert nc['notes'] == ["Exported by the drawing's own program: no conversion to check."]
    api_check(tmp_path, nc)
    fr = L.failed_report(dict(src, kind='dwg'), None, {'seconds': 1.0, 'peak_mb': 5.0, 'exit_code': 3},
                         ['ERROR: Invalid CMC flag 0x9f ignored'], 'x.dwg could not be converted.')
    assert fr['verdict'] == 'failed' and fr['dxf'] is None and fr['messages'][0]['class'] == 'error:Invalid CMC'
    api_check(tmp_path, fr)


def test_renamed_blocks(tmp_path: Path) -> None:
    objs = base_objects()
    dwg = L.DwgSide.scan(dwg_json(objs).splitlines(keepends=True))
    objs2 = [dict(o, name='Renamed') if o.get('handle') == UNUSED and o.get('object') else o for o in objs]
    p = tmp_path / 'r.dxf'
    p.write_bytes(dxf_text(objs2))
    c = L.compare(dwg, L.DxfSide.scan(p))
    assert c['renamedBlocks'] == [{'dwg': 'Unused', 'dxf': 'Renamed'}]
