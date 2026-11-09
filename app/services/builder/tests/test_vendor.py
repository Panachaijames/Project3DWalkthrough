"""The vendored prototype code (docs/upload/DESIGN.md U-10.2; ACCEPTANCE 2.1 U0): every copy equals VENDOR.json and,
while the prototype folder exists, the prototype file; the loader imports by path without writing bytecode."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys

import pytest

import kit
from walkthrough_builder.vendor import load as vload

MAN = json.loads((kit.VENDOR / 'VENDOR.json').read_text(encoding='utf-8'))

#: U-10.2's list, with the sha1 prefixes the design quotes
EXPECTED = {
    'openings.py': ('detector/openings.py', '14a570251f6d'),
    'geomkit.py': ('detector/geomkit.py', '6d4f8178'),
    'tools/prims.py': ('detector/tools/prims.py', '0e5566a0'),
    'merge_cad.py': ('cad_test/src/merge_cad.py', None),
    'geom.py': ('presidential_test/src/geom.py', None),
    'furniture_kit.py': ('furniture/furniture_kit.py', None),
    'furniture_max.py': ('furniture/furniture_max.py', None),
}


def test_vendor_json_lists_the_design_files() -> None:
    assert {f['path']: f['from'] for f in MAN['files']} == {k: v[0] for k, v in EXPECTED.items()}
    for f in MAN['files']:
        want = EXPECTED[f['path']][1]
        if want:
            assert f['sha1'].startswith(want), f['path']


@pytest.mark.parametrize('row', MAN['files'], ids=lambda r: r['path'])
def test_copy_equals_vendor_json(row: dict) -> None:
    data = (kit.VENDOR / row['path']).read_bytes()
    assert hashlib.sha1(data).hexdigest() == row['sha1']
    assert len(data) == row['bytes']


@pytest.mark.parametrize('row', MAN['files'], ids=lambda r: r['path'])
def test_copy_equals_prototype(row: dict) -> None:
    proto = kit.PROJECT / row['from']
    if not proto.exists():
        pytest.skip(f'the prototype file {proto} is gone (the copy still matches VENDOR.json)')
    assert proto.read_bytes() == (kit.VENDOR / row['path']).read_bytes(), (
        f'{row["from"]} changed after it was vendored: copy it in on purpose and re-run the goldens (U-10.2)')


def test_every_vendored_module_is_listed() -> None:
    listed = {f['path'] for f in MAN['files']}
    on_disk = {p.relative_to(kit.VENDOR).as_posix() for p in kit.VENDOR.rglob('*.py')} - {'__init__.py', 'load.py'}
    assert on_disk == listed
    assert set(vload.MODULES.values()) == listed


def test_load_imports_by_path_in_a_fresh_process(tmp_path) -> None:
    """In a child (sys.path and sys.modules stay clean here): openings needs OPENINGS_DATA; every module loads from
    vendor/; no __pycache__ appears beside the copies."""
    code = '''
import os, sys, json
from walkthrough_builder.vendor.load import load, VENDOR
try:
    load('openings')
    print('NO-ERROR')
except RuntimeError as e:
    print('needs data:', 'openings_data' in str(e))
op = load('openings', openings_data=sys.argv[1])
mods = {n: load(n).__file__ for n in ('geomkit', 'prims', 'merge_cad', 'geom', 'furniture_kit', 'furniture_max')}
print(json.dumps({'openings': op.__file__, 'data': os.environ['OPENINGS_DATA'], 'slow': op.SLOW_FLOOR,
                  'frame': op.FRAME_ROWS_MAX, 'units': op.UNITS, 'mods': mods,
                  'same': sys.modules['geomkit'] is load('geomkit'), 'roles': list(sys.modules['geomkit'].ROLES)}))
'''
    r = subprocess.run([sys.executable, '-B', '-P', '-c', code, str(tmp_path)], env=kit.child_env(OPENINGS_DATA=''),
                       capture_output=True, text=True, encoding='utf-8', timeout=120)
    assert r.returncode == 0, r.stderr
    lines = r.stdout.strip().splitlines()
    assert lines[0] == 'needs data: True'
    info = json.loads(lines[-1])
    assert info['data'] == str(tmp_path)
    assert info['slow'] == 60.0 and info['frame'] == 3000
    assert info['units']['mm'] == 1.0 and info['units']['in'] == 25.4
    assert info['same'] is True
    assert info['roles'] == ['wall', 'column', 'glass', 'window', 'screen', 'door', 'stair', 'ignore']
    for f in [info['openings'], *info['mods'].values()]:
        assert os.path.commonpath([f, str(kit.VENDOR)]) == str(kit.VENDOR)
    assert not list(kit.VENDOR.rglob('__pycache__')), 'bytecode written beside the vendored copies'


def test_check_refuses_an_edited_copy(monkeypatch) -> None:
    rows = json.loads(json.dumps(MAN))
    rows['files'][0]['sha1'] = '0' * 40
    monkeypatch.setattr(vload, 'manifest', lambda: rows)
    with pytest.raises(RuntimeError, match='copied in by hand'):
        vload.check(next(n for n, p in vload.MODULES.items() if p == rows['files'][0]['path']))
