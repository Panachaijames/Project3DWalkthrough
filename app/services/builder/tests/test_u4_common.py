"""Helpers shared by the U4 tests (outputs: docs/upload/WORK_BREAKDOWN.md U4; ACCEPTANCE 2.1 U4). No tests here.

* `check_file(kind, path, model=None)`: the API's own record check, run as the design says
  (`node tools/run-py.mjs -m walkthrough_api.check_file <kind> <path> [--model <model>]`, the API's Python), and
  `check_files([...])` for several files at once (a few processes in parallel).
* The scaffold's fixtures the U4 tests read (ACCEPTANCE 2.1: U4 reads only `build-result.bank.json`,
  `replay-input.bank.json` and `fixtures/models/*`, plus the bank's provisional conversion and drawing reports for
  BuildContext): `build_result()`, `replay_input()`, `bank_ctx(tmp)`.
* `mock()`: the prototype's mock 3ds Max interpreter (`furniture/fixtures/maxscript_mock.py` and its
  `maxscript_lite.py`), loaded by path with no bytecode written; None when the prototype folder is gone.
"""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import ModuleType

import kit

APP = kit.APP
PROJECT = kit.PROJECT
FX = kit.UPLOAD_FIXTURES
MODELS = kit.FIXTURES / 'models'
BANK_SHA = {'L1': '459d40fc230607ffe35e2ee9d443cd2b0105dc36', 'L2': '6551bdc6f0cff4e31e83b68a55d22cf42703029a'}
BANK_MODEL_SHA1 = 'c3a9408304a240b83c36f5c5c53db56b50a72c64'
BANK_MS_SHA1 = '615d50137bdbe12d3f473cdcdc39cc09aca588e4'
HOTEL_MS_SHA1 = '0a30014a84e066231e088b84792b4cda89d3bb0d'
BANK_TOPVIEW_SHA1 = 'f084b556503c4d5959e02d1dd55e84c607800775'
HOSTILE = ['<img src=x onerror=alert(1)>', '</script><b>x</b>', "$'", '&amp; & Co', 'a "quoted" \\ name', '__SHA__ __PX__',
           'ห้องนอน', 'Phòng Đôi', 'tab\there']


def sha1(b: bytes) -> str:
    return hashlib.sha1(b).hexdigest()


def load_json(p: Path):
    return json.loads(p.read_bytes().decode('utf-8'))


_CACHE: dict[str, object] = {}


def build_result() -> dict:
    """A fresh deep copy of fixtures/upload/build-result.bank.json (contracts.BuildResult of the bank)."""
    if 'br' not in _CACHE:
        _CACHE['br'] = load_json(FX / 'build-result.bank.json')
    return copy.deepcopy(_CACHE['br'])


def replay_input() -> dict:
    if 'ri' not in _CACHE:
        _CACHE['ri'] = load_json(FX / 'replay-input.bank.json')
    return copy.deepcopy(_CACHE['ri'])


def model(name: str) -> dict:
    """fixtures/models/<name>.model.json as a dict."""
    return load_json(MODELS / f'{name}.model.json')


def bank_settings() -> dict:
    return load_json(FX / 'settings' / 'bank.json')


def bank_ctx(tmp: Path, *, previous: Path | None = None, version: Path | None = MODELS / 'bank-v2.model.json') -> dict:
    """A BuildContext of the bank build run (U-10.8) over the scaffold's fixtures; out/ and tmp/ under `tmp`."""
    prep = FX / 'runs' / 'bank-prepare' / 'out' / 'sources'
    files = {
        'L1': (FX / 'conversion' / 'bank1.conversion.json', FX / 'drawing' / 'bank1.drawing.json', FX / 'plan' / 'bank1.plan.json.gz'),
        'L2': (prep / BANK_SHA['L2'] / 'conversion.json', prep / BANK_SHA['L2'] / 'drawing.json', prep / BANK_SHA['L2'] / 'plan.json.gz'),
    }
    settings = bank_settings()
    names = {s['sha1']: s['name'] for s in settings['sources']}
    out = tmp / 'out'
    out.mkdir(parents=True, exist_ok=True)
    (tmp / 'tmp').mkdir(exist_ok=True)
    spec = {
        'format': 'job-spec/1', 'kind': 'build', 'runId': '0002-build', 'buildId': '20261104T120000-abcdef',
        'projectId': 'bank-reupload', 'settings': settings, 'settingsRevision': 3,
        'sources': [{'sha1': BANK_SHA[k], 'name': names[BANK_SHA[k]], 'kind': 'dwg',
                     'path': str(tmp / 'no-original.dwg'), 'units': 'mm'} for k in ('L1', 'L2')],
        'only': None, 'office': None,
        'paths': {'out': str(out), 'cache': str(tmp / 'cache'), 'libredwg': str(kit.LIBREDWG),
                  'previousRun': str(previous.parent.parent) if previous else None,
                  'versionModel': str(version) if version else None},
        'limits': {k: {'seconds': 600, 'memoryMB': 4096} for k in ('convert', 'check', 'read', 'build')},
        'wallClockSeconds': 3600,
    }
    return {
        'spec': spec,
        'sources': [{'sha1': BANK_SHA[k], 'name': names[BANK_SHA[k]], 'kind': 'dwg', 'units': 'mm',
                     'conversion': str(files[k][0]), 'drawing': str(files[k][1]), 'items': str(tmp / 'cache' / 'items.pkl'),
                     'plan': str(files[k][2]), 'dxfSha1': '9167d084f7e311b59e7c2cdb2bae8506d96a4cfa' if k == 'L1' else
                     'c88491df00000000000000000000000000000000'} for k in ('L1', 'L2')],
        'converter': {'name': 'libredwg', 'version': '0.14', 'exeSha1': '07f9c8d95dc0' + '0' * 28},
        'previousRunModel': str(previous) if previous else None,
        'versionModel': str(version) if version else None,
        'outDir': str(out), 'tmpDir': str(tmp / 'tmp'),
    }


# ------------------------------------------------------------------------------------------------------- the API checker
def _node() -> str:
    exe = shutil.which('node')
    if exe is None:
        raise RuntimeError('node is not on PATH: the API checker runs through tools/run-py.mjs')
    return exe


def check_file(kind: str, path: Path, model: Path | None = None) -> tuple[int, str]:
    """`node tools/run-py.mjs -m walkthrough_api.check_file <kind> <path> [--model <model>]` -> (exit code, output)."""
    cmd = [_node(), str(APP / 'tools' / 'run-py.mjs'), '-m', 'walkthrough_api.check_file', kind, str(path)]
    if model is not None:
        cmd += ['--model', str(model)]
    r = subprocess.run(cmd, cwd=APP, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=300,
                       stdin=subprocess.DEVNULL)
    return r.returncode, (r.stdout + r.stderr).strip()


def check_files(items: list[tuple]) -> list[tuple[tuple, int, str]]:
    """check_file for each (kind, path[, model]), four at a time -> [(item, code, output)]."""
    with ThreadPoolExecutor(max_workers=4) as pool:
        res = list(pool.map(lambda it: check_file(*it), items))
    return [(it, code, out) for it, (code, out) in zip(items, res)]


def assert_checked(items: list[tuple]) -> None:
    bad = [f'{it[0]} {Path(it[1]).name}: exit {code}: {out[-800:]}' for it, code, out in check_files(items) if code != 0]
    assert not bad, '\n'.join(bad)


# ------------------------------------------------------------------------------------------------- the mock 3ds Max
def _load_by_path(name: str, path: Path) -> ModuleType:
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def mock() -> tuple[ModuleType, ModuleType] | None:
    """(maxscript_mock, maxscript_lite) of the prototype's furniture/fixtures, loaded by path (no bytecode); None when
    the files are not there."""
    if 'mock' in _CACHE:
        return _CACHE['mock']                                   # type: ignore[return-value]
    folder = PROJECT / 'furniture' / 'fixtures'
    if not (folder / 'maxscript_mock.py').exists() or not (folder / 'maxscript_lite.py').exists():
        _CACHE['mock'] = None
        return None
    lite = sys.modules.get('maxscript_lite') or _load_by_path('maxscript_lite', folder / 'maxscript_lite.py')
    mk = sys.modules.get('maxscript_mock') or _load_by_path('maxscript_mock', folder / 'maxscript_mock.py')
    _CACHE['mock'] = (mk, lite)
    return mk, lite
