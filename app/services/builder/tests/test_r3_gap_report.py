"""R3: tools/upload/gap-report.py's rows for the rooms milestone (docs/rooms/ACCEPTANCE.md RA-3 - RA-6; WORK_BREAKDOWN
R3), run as the integration step runs it (`node tools/run-builder-py.mjs tools/upload/gap-report.py <prototype dir>
<uploaded dir> ...`):

* a v2 upload (the reference building's frozen model, its build report beside it) against its v1 self: the rows of RA-3
  - RA-5 in each floor's table (rooms closed and named, names in no room, rooms with several names, plate0, terraces,
  unfloored areas, closings, holes by what, stairs);
* the storeys and stairs section: the window of storeys that fits every stair between two floors, and a storey outside
  it as a gap row (the tower's case: a stair kept as lines because 18 risers cannot rise 4.00 m);
* RA-6 with --probes / --drawing: each probe's sides on the plate, and a probe with no floor as a gap row;
* two v1 models give the section they gave (test_u4_gap_report.py, unchanged, says the rest).
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

import kit
import test_r3_outputs_unit as u
import test_u4_common as c
import test_u4_gap_report as g4


def folders(tmp: Path, report: dict | None = None) -> tuple[Path, Path]:
    m = u.ref_model()
    proto = g4.version_dir(tmp, 'reference-v1', u.as_v1(m))
    up = g4.version_dir(tmp, 'reference-v2', m)
    res = c.load_json(kit.ROOMS_FIXTURES / 'build-result.reference.json')
    (up / 'source').mkdir()
    (up / 'source' / 'build-report.json').write_text(json.dumps(report or res['report'], ensure_ascii=False), encoding='utf-8')
    return proto, up


def summary_of(r) -> dict:
    return json.loads(r.stderr.strip().splitlines()[-1])


def test_the_rooms_rows_of_a_v2_upload(tmp_path: Path):
    proto, up = folders(tmp_path)
    r = g4.run(str(proto), str(up), '--title', 'Reference: v2 against v1', '--json')
    assert r.returncode == 0, r.stderr
    text = r.stdout
    for row in ('| rooms closed | 0 | 2 | +2 |', '| rooms named | 0 | 2 | +2 |', '| names in no room | - | 1 | - |',
                '| rooms with several names | 0 | 1 | +1 |', '| plate0 (m2) | - | 87.4 | - |', '| terraces (m2) | - | 0.0 | - |',
                '| unfloored areas | - | 1 (20.0 m2) | - |', '| closings (doorway / bridge / staff) | - | 1 / 0 / 0 | - |',
                '| stairs you can climb | 0 | 1 | +1 |', '| stairs kept as lines | - | 1 | - |',
                '| holes | none | none | - |',
                '| holes | stair well 1 (5.63 m2); void 1 (5.20 m2) | stair well 1 (5.63 m2); void 1 (5.20 m2) | - |',
                '| terraces (m2) | - | 21.1 | - |'):
        assert row in text, row
    s = summary_of(r)
    assert s['floors']['ground']['rooms']['rooms closed'] == 2 and s['floors']['upper']['rooms']['plate0 (m2)'] == '85.0'
    # the storeys: 16 risers fit 2.24 - 3.36 m, the storey is 3.00 m: no gap row
    assert '| ground - upper | 3.00 | 2.24 - 3.36 | S1 16 risers (climbable) |' in text
    assert s['storeyWindows'][0]['window'] == [2.24, 3.36] and not any('storey window' in x for x in text.splitlines())


def test_a_storey_outside_the_window_is_a_gap_row(tmp_path: Path):
    res = c.load_json(kit.ROOMS_FIXTURES / 'build-result.reference.json')
    rep = copy.deepcopy(res['report'])
    st = rep['floors']['ground']['stairways'][1]
    st.update(why='the riser does not fit', risers=22)            # 22 x 0.14 = 3.08 m: the 3.00 m storey is too low for it
    proto, up = folders(tmp_path, rep)
    r = g4.run(str(proto), str(up), '--json')
    assert r.returncode == 0, r.stderr
    assert ('| ground - upper | 3.00 | 3.08 - 3.36 | S1 16 risers (climbable), ground-ST2 22 risers (kept as lines, does not fit) |'
            in r.stdout)
    assert '| ground | storey window | - | 3.00 | outside 3.08 - 3.36 |  | to classify |' in r.stdout
    assert summary_of(r)['gaps'] >= 1


def test_the_probes_that_had_no_floor(tmp_path: Path):
    proto, up = folders(tmp_path)
    key = {'format': 'probes-key/1', 'drawings': {'reference': {'grade': 'must', 'probes': [
        {'id9Nov': 'ground-001', 'kind': 'door', 'floor': 'ground', 'at': [5.0, 0.1], 'n': [0.0, 1.0], 'sides': [1]},
        {'id9Nov': 'garage', 'kind': 'door', 'floor': 'ground', 'at': [10.35, 8.9], 'n': [0.0, 1.0], 'sides': [-1]},
        {'id9Nov': 'outside', 'kind': 'door', 'floor': 'ground', 'at': [5.0, 0.1], 'n': [0.0, 1.0], 'sides': [-1, 1]}]}}}
    kp = tmp_path / 'probes.json'
    kp.write_text(json.dumps(key), encoding='utf-8')
    r = g4.run(str(proto), str(up), '--probes', str(kp), '--drawing', 'reference', '--json')
    assert r.returncode == 0, r.stderr
    assert '1 of 3 stand on the plate.' in r.stdout
    assert '| ground-001 | ground | must | +1: floor |' in r.stdout
    assert '| garage | ground | must | -1: no floor |' in r.stdout and '| ground | probe garage | - | no floor | -1: no floor |' in r.stdout
    assert summary_of(r)['probes'] == {'total': 3, 'passed': 1, 'failing': ['garage', 'outside']}
    r = g4.run(str(proto), str(up), '--probes', str(kp))
    assert r.returncode == 2 and '--drawing' in r.stderr
    r = g4.run(str(proto), str(up), '--probes', str(kp), '--drawing', 'tower')
    assert r.returncode == 2 and 'no drawing' in r.stderr


def test_the_real_probes_key_reads(tmp_path: Path):
    """The frozen key's tower probes against the reference model: the tool reads the key and names each probe."""
    proto, up = folders(tmp_path)
    r = g4.run(str(proto), str(up), '--probes', str(kit.ROOMS_FIXTURES / 'keys' / 'probes.json'), '--drawing', 'tower', '--json')
    assert r.returncode == 0, r.stderr
    assert summary_of(r)['probes']['total'] == 8 and '| L29-001 | L29 | must |' in r.stdout
