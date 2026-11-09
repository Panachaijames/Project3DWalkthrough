"""U4: tools/upload/gap-report.py on seeded models (ACCEPTANCE A-5's metrics and gap classes, A-6's failing probes).

Run as the integration step will run it (`node tools/run-builder-py.mjs tools/upload/gap-report.py <prototype dir>
<uploaded dir>`): the bank's v1 against v2 (the passages and the furniture differ), the house against itself in another
model frame (drawing coordinates: nothing differs), with a classes file and walk checks.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import test_u4_common as c
import test_u4_overlay_diff as od

TOOL = c.APP / 'tools' / 'upload' / 'gap-report.py'


def version_dir(root: Path, name: str, model: dict) -> Path:
    d = root / 'projects' / name / 'versions' / '1'
    d.mkdir(parents=True)
    (d / 'model.json').write_text(json.dumps(model, ensure_ascii=False), encoding='utf-8')
    return d


def run(*args: str) -> subprocess.CompletedProcess:
    node = shutil.which('node')
    assert node, 'node is not on PATH'
    return subprocess.run([node, str(c.APP / 'tools' / 'run-builder-py.mjs'), str(TOOL), *args], cwd=c.APP, capture_output=True,
                          text=True, encoding='utf-8', timeout=300, stdin=subprocess.DEVNULL)


def test_bank_v1_against_v2_with_classes_and_walk(tmp_path: Path):
    proto = version_dir(tmp_path, 'bank-v1', c.model('bank-v1'))
    up = version_dir(tmp_path, 'bank-v2', c.model('bank-v2'))
    classes = tmp_path / 'classes.json'
    classes.write_text(json.dumps([{'floor': None, 'metric': 'passages', 'class': 'accepted difference',
                                    'cause': 'v2 merged the passages into doors'}]), encoding='utf-8')
    walk = tmp_path / 'walk.json'
    walk.write_text(json.dumps({'probes': [{'floor': 'L1', 'kind': 'door', 'id': 'L1-002', 'passed': True},
                                           {'floor': 'L2', 'kind': 'wall', 'id': 'spot 7', 'passed': False, 'detail': 'went | through'}]}),
                    encoding='utf-8')
    out = tmp_path / 'gaps.md'
    r = run(str(proto), str(up), '--title', 'Bank: v2 against v1', '--classes', str(classes), '--walk', str(walk), '--out', str(out),
            '--json')
    assert r.returncode == 0, r.stderr
    text = out.read_text(encoding='utf-8')
    summary = json.loads(r.stderr.strip().splitlines()[-1])
    assert text.startswith('## Bank: v2 against v1\n')
    assert '### Floor L1 (prototype) / L1 (upload)' in text and '### Floor L2 (prototype) / L2 (upload)' in text
    for metric in ('wall area (m2)', 'wall runs', 'glass area (m2)', 'glass pieces', 'doors', 'windows', 'passages',
                   'openings matched (centre within 0.2 m)', 'lintels', 'sills', 'panes', 'plate area (m2)', 'rooms'):
        assert f'| {metric} |' in text, metric
    assert '| L1 | passages | 5 | 2 | -3 | v2 merged the passages into doors | accepted difference |' in text
    assert '| L1 | furniture: seat | 0 | 37 | +37 |  | to classify |' in text
    assert summary['floors']['L1']['wallSymDiff'] == 0.0 and summary['floors']['L1']['openingsMatched'] == 24
    assert '### Walk checks (A-6)' in text and '1 of 2 probes pass.' in text
    assert '| L2 | walk: wall | spot 7 | went \\| through |  | to classify |' in text
    assert summary['walk'] == {'probes': 2, 'failing': 1}


def test_the_house_in_another_frame_has_no_gap(tmp_path: Path):
    house = c.model('house')
    proto = version_dir(tmp_path, 'house', house)
    up = version_dir(tmp_path, 'house-up', od.reframed(house, 5.5, -2.25, {'upper': (80.0, 0.0)}))
    r = run(str(proto), str(up), '--json')
    assert r.returncode == 0, r.stderr
    summary = json.loads(r.stderr.strip().splitlines()[-1])
    assert summary['gaps'] == 0, r.stdout
    assert 'None over the thresholds.' in r.stdout
    assert summary['floors']['upper']['wallSymDiff'] < 0.01 and summary['floors']['ground']['plateSymDiff'] < 0.01


def test_floors_matched_by_order_and_a_missing_floor(tmp_path: Path):
    suite = c.model('suite')
    other = c.model('suite')
    other['floors'][0]['key'] = 'S1'
    for k in ('parts', 'openings', 'rooms', 'furniture', 'probes'):
        for x in other.get(k) or []:
            x['floor'] = 'S1'
    r = run(str(version_dir(tmp_path, 'a', suite)), str(version_dir(tmp_path, 'b', other)), '--json')
    assert r.returncode == 0, r.stderr
    assert '### Floor suite (prototype) / S1 (upload)' in r.stdout
    assert json.loads(r.stderr.strip().splitlines()[-1])['gaps'] == 0
    bad = tmp_path / 'classes.json'
    bad.write_text(json.dumps([{'floor': None, 'metric': 'floor', 'class': 'maybe'}]), encoding='utf-8')
    two = c.model('bank-v2')
    r = run(str(version_dir(tmp_path, 'c', suite)), str(version_dir(tmp_path, 'd', two)), '--classes', str(bad))
    assert r.returncode == 2 and 'not one of' in r.stderr
    r = run(str(tmp_path / 'nowhere'), str(tmp_path / 'nothing'))
    assert r.returncode == 2
