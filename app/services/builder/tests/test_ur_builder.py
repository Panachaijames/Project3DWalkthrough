"""UR (the review-and-fix step of the upload milestone, docs/upload/contract-issues/UR.md): the builder's fixes, each
with the case the verifiers found.

  * V3-6  scrub(): a path whose folders hold spaces (this laptop's 'Project walkthrough') is removed whole, and the
          worker's final error message is scrubbed like every message;
  * V3-3  the loss check: dwgread's exit code and the end of its JSON decide whether the DWG side is whole (a prefix of
          the drawing passed as `ok` with 1,588 'extra' handles); extra handles never pass as `ok`;
  * V3-7  the converter's text output is capped (isolate.run's text watchdog, convert's plain sentence), and a child's
          output goes into log.txt as its head and tail only;
  * V1-5  layer 0's evidence says what layer 0 holds (top-level line work, or what blocks drew there);
  * V1-1  a large area inside the walls with no floor plate is flagged (`plate-dropped`, check), and the plate-dropped
          info flag says what the dropped areas are;
  * V2-6  texts that look like room names on a layer set to ignore / other inside the plate are flagged (`room-label`).
"""
from __future__ import annotations

import io
import sys
from pathlib import Path

import pytest

from walkthrough_builder import convert, isolate, job as J, losscheck as L, suggest as S
from walkthrough_builder.out import overlay as O


# =============================================================================================================== V3-6
@pytest.mark.parametrize('text,want', [
    (r'the converted drawing could not be opened: C:\Users\DWP2\Desktop\Project walkthrough\app\data\projects\bank-sampeng'
     r'\builds\20261109T101500-0a1b2c\runs\0002-build\out\model.json', 'the converted drawing could not be opened: model.json'),
    ("[WinError 2] cannot find: 'C:\\\\Users\\\\DWP2\\\\Desktop\\\\Project walkthrough\\\\model.json'",
     "[WinError 2] cannot find: 'model.json'"),
    (r'OSError: denied: C:\Users\DWP2\Desktop\Project walkthrough\app\data\x.json', 'OSError: denied: x.json'),
    (r'C:\Program Files\x\dwg2dxf.exe: error at C:\Temp\y z\input.dwg (3)', 'dwg2dxf.exe: error at input.dwg (3)'),
    # prose after a backslash path is never taken for a folder (a slash later in the sentence is not its separator)
    (r'C:\a\b.txt and also see logs/x', 'b.txt and also see logs/x'),
    # the four cases of the U1 test still hold
    (r'failed at C:\Users\x\AppData\Local\Temp\run\plan.dxf line 3', 'failed at plan.dxf line 3'),
    ('see c:/data/projects/p/builds/b/out/model.json.', 'see model.json.'),
    (r'share \\server\share\folder\f.dwg here', 'share f.dwg here'),
    ('no path here', 'no path here'),
])
def test_scrub_paths_with_spaces(text: str, want: str) -> None:
    assert L.scrub(text) == want


def test_the_final_error_message_is_scrubbed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    written: list[dict] = []
    monkeypatch.setattr(J.runio, 'write_job', lambda d, rec: written.append(rec))
    r = J.Run(tmp_path / 'run')
    r.dir.mkdir()
    r.rec = {'format': 'job/1', 'kind': 'build', 'runId': '0002-build', 'status': 'running', 'messages': []}
    where = r'C:\Users\DWP2\Desktop\Project walkthrough\app\data\projects\p\builds\b\runs\0002-build\out\model.json'
    r.finish('failed', {'code': 'internal', 'message': f'The converted drawing could not be opened: {where}.', 'step': None})
    rec = written[-1]
    assert rec['error']['message'] == 'The converted drawing could not be opened: model.json.'
    assert all('Project walkthrough' not in m['text'] and 'C:\\' not in m['text'] for m in rec['messages'])


# =============================================================================================================== V3-3
def _objects_json(n: int) -> str:
    """dwgread 0.14's layout: sections at 2 spaces, OBJECTS closed by '  ],', the document by '  }}'."""
    out = ['{', '  "created_by": "LibreDWG 0.14",', '  "HEADER": {', '    "handle": [0,1,99]', '  },', '  "OBJECTS": [',
           '    {', '      "object": "BLOCK_HEADER",', '      "handle": [0,1,2],', '      "name": "*Model_Space"', '    },',
           '    {', '      "object": "LAYER",', '      "handle": [0,1,5],', '      "name": "0"', '    },']
    for i in range(n):
        out += ['    {', '      "entity": "LINE",', f'      "handle": [0,2,{256 + i}],', '      "entmode": 2,',
                '      "layer": [5,1,5]', '    }' + (',' if i < n - 1 else '')]
    out += ['  ],', '  "AcDs": {', '    "handle": [0,1,5]', '  }}']
    return '\n'.join(out) + '\n'


def test_a_whole_dwgread_output_is_complete() -> None:
    side = L.DwgSide.scan(io.StringIO(_objects_json(50)))
    assert side.complete and len(side.ents) == 50


@pytest.mark.parametrize('cut', [0.3, 0.6, 0.95])
def test_a_cut_dwgread_output_is_not(cut: float) -> None:
    text = _objects_json(50)
    side = L.DwgSide.scan(io.StringIO(text[:int(len(text) * cut)]))
    assert not side.complete


class _FakeDwgread:
    """Stands in for subprocess.Popen(dwgread ...): its stdout is the given text, its exit code the given one."""

    def __init__(self, text: str, code: int) -> None:
        self.stdout = io.BytesIO(text.encode('utf-8'))
        self._code = code

    def wait(self) -> int:
        return self._code

    def kill(self) -> None:
        pass


def _dwgread(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, text: str, code: int):
    monkeypatch.setattr(L.subprocess, 'Popen', lambda *a, **k: _FakeDwgread(text, code))
    dwg = tmp_path / 'input.dwg'
    dwg.write_bytes(b'AC1032')
    return L.dwgread_side(dwg, tmp_path, tmp_path / 'dwgread.err.txt')


def test_dwgread_side_takes_a_whole_output(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    side, code, _ = _dwgread(monkeypatch, tmp_path, _objects_json(10), 0)
    assert code == 0 and len(side.ents) == 10


def test_dwgread_side_refuses_a_crash(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # the verifier's case: an access violation (0xC0000005) under a small memory cap, the JSON whole or not
    with pytest.raises(L.CheckError, match='exit code 0xc0000005'):
        _dwgread(monkeypatch, tmp_path, _objects_json(10), 0xC0000005)
    with pytest.raises(L.CheckError, match='exit code 3'):
        _dwgread(monkeypatch, tmp_path, _objects_json(10), 3)


def test_dwgread_side_refuses_a_cut_output(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    text = _objects_json(40)
    with pytest.raises(L.CheckError, match='part way'):
        _dwgread(monkeypatch, tmp_path, text[:int(len(text) * 0.6)], 0)


def test_extra_handles_never_pass_as_ok() -> None:
    c = {'missing': [], 'missingPlan': [], 'typeChanged': [], 'layerChanged': [], 'ownerChanged': [], 'benignLayer': [],
         'extra': list(range(1588)), 'lostBlocks': []}
    verdict, notes = L.verdict_and_notes(c, [], 2885)
    assert verdict == 'minor'
    assert any('1,588 items of the converted file are not in the drawing as decoded' in n for n in notes)
    c['extra'] = []
    assert L.verdict_and_notes(c, [], 2885) == ('ok', [])


# =============================================================================================================== V3-7
def test_isolate_stops_a_child_that_prints_without_end(tmp_path: Path) -> None:
    # about 10 MB a second (a damaged drawing's warnings), so the 0.25 s watchdog stops it soon after 2 MB
    code = ('import sys, time\nwhile True:\n    sys.stdout.write("Warning: Unknown flag 0x9f\\n" * 4000)\n'
            '    sys.stdout.flush()\n    time.sleep(0.01)\n')
    res = isolate.run([sys.executable, '-c', code], cwd=tmp_path, env=isolate.child_env(), seconds=60, memory_mb=1024,
                      stdout=tmp_path / 'out.txt', stderr=tmp_path / 'err.txt', watch_text_max_bytes=2 * 1024 * 1024)
    assert res['killed_for_text'] and res['exit_code'] is None
    assert isolate.classify(res, 'convert') == 'convert_failed'
    assert (tmp_path / 'out.txt').stat().st_size < 64 * 1024 * 1024


def test_convert_names_the_text_cap(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(cmd, *, stdout, stderr, **kw):
        assert kw['watch_text_max_bytes'] == convert.MAX_TEXT_BYTES
        Path(stdout).write_bytes(b'Warning: x\n' * 10)
        Path(stderr).write_bytes(b'ERROR: y\n')
        return {'exit_code': None, 'raw_exit_code': 1, 'seconds': 1.0, 'cpu_seconds': 1.0, 'peak_mb': 10.0,
                'memory_hit': False, 'memory_message': False, 'timed_out': False, 'cancelled': False,
                'killed_for_size': False, 'killed_for_text': True, 'active_limit_hit': False}
    monkeypatch.setattr(convert.isolate, 'run', fake_run)
    (tmp_path / 'input.dwg').write_bytes(b'AC1032')
    res = convert.convert(tmp_path / 'input.dwg', tmp_path, libredwg=tmp_path, seconds=10, memory_mb=100)
    assert res['code'] == 'convert_failed' and 'printed more than 64 MB of messages' in res['detail']
    assert (tmp_path / 'convert.log').read_bytes() == b'Warning: x\n' * 10 + b'ERROR: y\n'


def test_a_large_child_output_goes_into_the_log_as_head_and_tail(tmp_path: Path) -> None:
    big = tmp_path / 'stdout.txt'
    big.write_bytes(b'HEAD\n' + b'x' * (3 * J.CHILD_LOG_KEEP) + b'\nTAIL\n')
    text = J._head_and_tail(big, J.CHILD_LOG_KEEP)
    assert text.startswith('HEAD') and text.rstrip().endswith('TAIL') and 'bytes left out' in text
    assert len(text) < 2 * J.CHILD_LOG_KEEP + 200
    small = tmp_path / 'small.txt'
    small.write_bytes(b'all of it\n')
    assert J._head_and_tail(small, J.CHILD_LOG_KEEP) == 'all of it\n'
    r = J.Run(tmp_path / 'run')
    r.dir.mkdir()
    r.append_child_log('dwg2dxf (convert:0)', None, [big])
    assert (r.dir / 'log.txt').stat().st_size < 2 * J.CHILD_LOG_KEEP + 1000


# =============================================================================================================== V1-5
def _layer0(**kw) -> dict:
    base = {'name': '0', 'items': 0, 'byType': {}, 'inBlocks': 0, 'solidHatches': 0, 'closedShapes': 0, 'length': 0.0,
            'doorArcs': 0, 'doorArcsWithLeaf': 0, 'texts': 0, 'inserts': 0, 'topBlocks': [],
            'pairs': {'glassLike': 0, 'wallLike': 0}}
    base.update(kw)
    return base


def _suggest0(**kw) -> dict:
    return S.suggest([{'layers': [_layer0(**kw)], 'levelTags': [], 'gridLabels': [], 'texts': []}], None)['layers']['0']


def test_layer0_of_a_revit_export_names_its_top_level_line_work() -> None:
    # presidential suite_layout.dwg (A-12): 2,634 items on layer 0, none in blocks, the suite's partitions
    got = _suggest0(items=2634, inBlocks=0, solidHatches=99, pairs={'glassLike': 238, 'wallLike': 84},
                    byType={'LINE': 1640, 'ARC': 787, 'HATCH': 99, 'LWPOLYLINE': 83, 'CIRCLE': 24, 'SOLID': 1})
    assert (got['role'], got['from']) == ('other', 'default')
    ev = got['evidence'][0]
    assert ev.startswith('layer 0 holds 2634 items drawn at the top level, not inside blocks (99 solid fills, '
                         '84 wall-like line pairs, 238 glass-like line pairs)')
    assert 'check whether walls or other parts are drawn here' in ev and 'whatever blocks drew there' not in ev


def test_layer0_of_blocks_says_so() -> None:
    got = _suggest0(items=314, inBlocks=311, inserts=314, byType={'INSERT': 314})          # the tower's L29
    assert got['evidence'][0].startswith('layer 0 holds what blocks drew there (311 of its 314 items are inside blocks)')
    assert _suggest0()['evidence'][0].startswith('layer 0 holds nothing')
    plain = _suggest0(items=40, byType={'LINE': 30, 'ARC': 10})
    assert '(30 lines, 10 arcs)' in plain['evidence'][0]


# =============================================================================================================== V1-1
def _ring(x0, y0, x1, y1, t=0.2) -> list[dict]:
    """Four wall parts round a box (overlay part footprints, sheet m)."""
    def rect(a, b, c, d):
        return {'i': 0, 'kind': 'wall', 'label': None, 'o': [[a, b], [c, b], [c, d], [a, d]], 'h': []}
    return [rect(x0, y0, x1, y0 + t), rect(x0, y1 - t, x1, y1), rect(x0, y0, x0 + t, y1), rect(x1 - t, y0, x1, y1)]


def _slab(x0, y0, x1, y1) -> dict:
    return {'o': [[x0, y0], [x1, y0], [x1, y1], [x0, y1]], 'h': []}


def test_an_unfloored_area_inside_closed_walls_is_flagged() -> None:
    walls = _ring(0, 0, 30, 20)
    assert O.unfloored_flags('L1', walls, [_slab(0, 0, 30, 20)]) == []
    flags = O.unfloored_flags('L29', walls, [_slab(0, 0, 10, 20)])               # two thirds of the floor has none
    assert len(flags) == 1
    f = flags[0]
    assert (f['kind'], f['severity'], f['floor']) == ('plate-dropped', 'check', 'L29')
    assert f['title'].startswith('L29: about') and 'inside the walls has no floor' in f['title']
    # the part of the box east of the plate, less 0.3 m along the plate and the walls: 19.2 x 19.0 m
    assert 355 <= float(f['title'].split('about ')[1].split(' m2')[0]) <= 375
    assert 'Layers step' in f['detail'] and f['at'] is not None and f['bbox'] is not None
    # under the threshold (a 2 x 2 m stair void in the plate, as the bank's L2 has): nothing
    void = {'o': [[0, 0], [30, 0], [30, 20], [0, 20]], 'h': [[[14, 9], [16, 9], [16, 11], [14, 11]]]}
    assert O.unfloored_flags('L2', walls, [void]) == []


def test_walls_that_never_close_with_a_small_plate_are_flagged() -> None:
    # two long parallel walls 20 m apart (no ends): the closing cannot fill them, the plate is a small corner
    walls = [{'i': 0, 'kind': 'wall', 'label': None, 'o': [[0, 0], [30, 0], [30, 0.2], [0, 0.2]], 'h': []},
             {'i': 1, 'kind': 'wall', 'label': None, 'o': [[0, 20], [30, 20], [30, 20.2], [0, 20.2]], 'h': []}]
    flags = O.unfloored_flags('suite', walls, [_slab(0, 0.2, 5, 5)])
    assert len(flags) == 1 and flags[0]['title'].startswith('suite: the floor plate is 24 m2 of the about')
    assert O.unfloored_flags('suite', walls, [_slab(0, 0.2, 30, 20)]) == []


def test_the_plate_dropped_info_flag_says_why() -> None:
    rep = {'platesDropped': [{'area': 1.03, 'at': [3.0, 4.0], 'why': 'no door or passage opens onto it'}]}
    f = O.floor_flags('upper', rep, {'parts': []})
    assert len(f) == 1 and f[0]['kind'] == 'plate-dropped' and f[0]['severity'] == 'info'
    assert 'inside a railing' not in f[0]['detail']
    assert f[0]['detail'] == ('An area of 1.03 m2 next to the walls, outside the rooms they close, was left out of the '
                              'floor plate (no door or passage opens onto it).')
    # the flag id does not depend on the reason (the same drawing and settings keep their ids)
    same = O.floor_flags('upper', {'platesDropped': [{'area': 1.03, 'at': [3.0, 4.0]}]}, {'parts': []})
    assert same[0]['id'] == f[0]['id']


# =============================================================================================================== V2-6
def _texts(layer, items, kind='TEXT', block=None) -> list[dict]:
    return [{'layer': layer, 'x': x, 'y': y, 'height': 0.3, 'text': t, 'kind': kind, 'tag': None, 'block': block}
            for t, x, y in items]


def test_room_names_on_an_ignored_layer_are_flagged() -> None:
    slabs = [_slab(0, 0, 30, 20)]
    names = [('MANAGER', 5, 5), ('WAITING AREA', 10, 5), ('MINI BAR / WEALTH ROOM', 20, 15), ('ATM', 25, 5)]
    drawing = {'texts': _texts('G-ANNO-TEXT', names) + _texts('G-ANNO-TEXT', [('BANGKOK BANK TITLE', 50, 50)])
               + _texts('A-DOOR-IDEN', [('D1', 3, 3), ('D2', 4, 3), ('W12', 6, 3)])}
    flags = O.room_name_flags('L2', 's' * 40, slabs, {'G-ANNO-TEXT': 'ignore', 'A-DOOR-IDEN': 'other'}, drawing)
    assert len(flags) == 1
    f = flags[0]
    assert (f['kind'], f['severity'], f['floor']) == ('room-label', 'check', 'L2')
    assert f['title'] == '4 texts on G-ANNO-TEXT look like room names'
    assert 'set to Ignore' in f['detail'] and 'Room names on the Layers step' in f['detail']
    assert 'BANGKOK' not in f['detail']                                       # outside the plate: a title block
    # the same layer set to room names: nothing; texts of blocks (attributes, furniture labels): nothing
    assert O.room_name_flags('L2', 's' * 40, slabs, {'G-ANNO-TEXT': 'room-name'}, drawing) == []
    attribs = {'texts': _texts('I-FURN', names, kind='ATTRIB', block='Chair') + _texts('I-FURN', names, block='Desk')}
    assert O.room_name_flags('L2', 's' * 40, slabs, {'I-FURN': 'other'}, attribs) == []
    assert O.room_name_flags('L2', 's' * 40, slabs, {}, None) == []
