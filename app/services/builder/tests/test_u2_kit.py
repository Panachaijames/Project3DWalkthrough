"""Helpers shared by U2's tests (the reader and the suggestions); no tests of its own.

* `ref_read(name)`: the reader run on a reference drawing's DXF (WT_REF, read-only) into WT_TMP\\u2-reads\\<name>, once per
  test session. Call it only inside a `heavy` test (the test holds the machine run lock while it reads).
* `synthetic(path, build)`: an ezdxf document made by `build(doc, msp)`, saved as R2013 with fixed meta data.
* `small_dxf(path, kind)`: tools/upload/make-test-dxf.py small | hostile.
* `api_issues([(kind, path), ...])`: the API's own record checks (walkthrough_api.check_file.issues) run in the API's
  Python (node tools/run-py.mjs), one process for all the files; skips when the API's environment is not there.
* `prims_flatten(dxf)`: the vendored detector/tools/prims.py `_flatten`, the reader's oracle on any DXF.
"""
from __future__ import annotations

import gzip
import json
import os
import pickle
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

import kit
from walkthrough_builder import read as R

READS = kit.RUN / 'u2-reads'
_cache: dict[str, dict] = {}


def manifest() -> dict:
    return json.loads((kit.REF / 'manifest.json').read_text(encoding='utf-8'))


def load_read(out: Path) -> dict:
    with open(out / R.ITEMS_FILE, 'rb') as f:
        cache = pickle.load(f)
    return {'out': out, 'cache': cache, 'items': cache['items'],
            'drawing': json.loads((out / R.DRAWING_FILE).read_text(encoding='utf-8')),
            'plan': json.loads(gzip.decompress((out / R.PLAN_FILE).read_bytes()).decode('utf-8'))}


def ref_read(name: str) -> dict:
    """The reader on reference drawing `name` (bank1, bank2, sukhumvit, presidential, l29, l30), once per session."""
    if name in _cache:
        return _cache[name]
    dxf = kit.ref_dxf(name)
    if not dxf.exists():
        pytest.skip(f'no reference DXF for {name} at {dxf} (WT_REF)')
    out = READS / name
    shutil.rmtree(out, ignore_errors=True)
    lines: list[str] = []
    res = R.read_source(dxf, None, out, source={'sha1': manifest()['drawings'][name]['dwgSha1'],
                                                'name': kit.DRAWINGS[name]}, log=lines.append)
    r = load_read(out)
    r['result'] = res
    r['log'] = lines
    _cache[name] = r
    return r


def ref_prims(name: str) -> dict:
    with open(kit.ref_prims(name), 'rb') as f:
        return pickle.load(f)


def synthetic(path: Path, build, *, insunits: int = 4) -> Path:
    """An R2013 DXF made by build(doc, msp), saved with ezdxf's fixed meta data (the same bytes every time)."""
    import ezdxf
    ezdxf.options.write_fixed_meta_data_for_testing = True
    doc = ezdxf.new('R2013', setup=False)
    doc.header['$INSUNITS'] = insunits
    build(doc, doc.modelspace())
    path.parent.mkdir(parents=True, exist_ok=True)
    doc.saveas(path)
    return path


def small_dxf(path: Path, kind: str = 'small') -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([sys.executable, '-B', str(kit.APP / 'tools' / 'upload' / 'make-test-dxf.py'), kind, str(path)],
                   check=True, env=kit.child_env(PYTHONHASHSEED='0'), stdout=subprocess.DEVNULL)
    return path


def read(dxf: Path, out: Path, units: str | None = None, name: str | None = None, sha1: str = '0' * 40) -> dict:
    lines: list[str] = []
    res = R.read_source(dxf, units, out, source={'sha1': sha1, 'name': name or dxf.name}, log=lines.append)
    r = load_read(out)
    r['result'] = res
    r['log'] = lines
    return r


_API_CODE = r'''
import json, sys
from pathlib import Path
from walkthrough_api.check_file import issues
out = {}
for kind, path in json.loads(sys.argv[1]):
    out[path] = issues(kind, Path(path).read_bytes())
print('U2-ISSUES ' + json.dumps(out))
'''


def api_issues(files: list[tuple[str, Path]]) -> dict[str, list[str]]:
    """{path: issues} from the API's check_file in the API's own Python (empty list: the file passes)."""
    node = shutil.which('node')
    if node is None or not (kit.APP / 'services' / 'api' / '.venv').exists():
        pytest.skip('the API environment (node, services/api/.venv) is not there: check_file cannot run')
    arg = json.dumps([[k, str(p)] for k, p in files])
    env = dict(os.environ, PYTHONIOENCODING='utf-8')
    run = subprocess.run([node, str(kit.APP / 'tools' / 'run-py.mjs'), '-c', _API_CODE, arg], cwd=kit.APP, env=env,
                         stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding='utf-8', timeout=600)
    line = next((ln for ln in run.stdout.splitlines() if ln.startswith('U2-ISSUES ')), None)
    assert line is not None, f'check_file did not run: {run.stdout[-2000:]} {run.stderr[-2000:]}'
    return json.loads(line[len('U2-ISSUES '):])


def prims_flatten(dxf: Path) -> tuple[list[dict], dict]:
    """The vendored prims.py `_flatten` (the walk the reader reproduces) on any DXF. prims reads OPENINGS_DATA once when
    it loads and never uses it here: a folder of this run's own."""
    from walkthrough_builder.vendor.load import load
    data = kit.RUN / 'openings-data'
    data.mkdir(parents=True, exist_ok=True)
    prims = load('prims', openings_data=data)
    return prims._flatten(str(dxf))


def strip(items: list[dict], drop=('k', 'area')) -> list[dict]:
    return [{k: v for k, v in d.items() if k not in drop} for d in items]
