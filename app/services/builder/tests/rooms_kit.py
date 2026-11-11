"""Shared helpers of the rooms milestone's builder tests (docs/rooms/WORK_BREAKDOWN.md R0 items 7, 8 and 10). Written by
the scaffold R0 and frozen after it: R1 and R2 import it, nobody edits it (a need goes in your own contract-issues file).

* the synthetic stair drawings (`tools/rooms/make-stair-dxf.py`), made at test time and read by the APP'S OWN reader
  (contracts.read_source) into a folder of the test's own: `stair_plan(variant, out)`;
* the reference building (`tools/rooms/make-reference-building.py dxf`), the same way: `reference_plan(out)`;
* BuildSettings for such a plan (`plan_settings`), with the new rules (contracts.NEW_RULES) unless told otherwise;
* the `*-rooms.json` settings fixtures and their sources over the reference caches (`rooms_settings`, `rooms_sources`);
* one new-rule build in this process (`rooms_build`, used by conftest.py's session fixtures), and the same build in a
  child process with its own PYTHONHASHSEED (`rooms_child_build`: built twice means in two processes, DESIGN R-13).
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import kit
from walkthrough_builder import contracts

TOOLS = kit.APP / 'tools' / 'rooms'
SETTINGS = kit.UPLOAD_FIXTURES / 'settings'
#: the five drawings with a `<name>-rooms.json` settings fixture -> the project id their builds use
ROOMS_BUILDS = {'bank': 'bank-sampeng', 'house': 'house-upload', 'suite': 'suite-upload', 'tower': 'tower-upload',
                'suite-revit': 'suite-revit'}


def _tool(script: str, *args: str) -> None:
    r = subprocess.run([sys.executable, '-B', '-P', str(TOOLS / script), *args], env=kit.child_env(PYTHONHASHSEED='0'),
                       cwd=kit.APP, capture_output=True, text=True, encoding='utf-8', stdin=subprocess.DEVNULL, timeout=600)
    assert r.returncode == 0, f'{script} {" ".join(args)} failed:\n{r.stdout}\n{r.stderr}'


def read_dxf(dxf: Path, out: Path, *, name: str | None = None) -> dict:
    """One DXF read by the app's reader into `out` (items.pkl, drawing.json, plan.json.gz) -> its SourceContext."""
    from walkthrough_builder import cache
    out.mkdir(parents=True, exist_ok=True)
    sha = cache.sha1_file(dxf)
    got = contracts.read_source(dxf, 'mm', out, source={'sha1': sha, 'name': name or dxf.name}, log=lambda _m: None)
    return {'sha1': sha, 'name': name or dxf.name, 'kind': 'dxf', 'units': got['units']['used'], 'conversion': None,
            'drawing': got['drawing'], 'items': got['items'], 'plan': got['plan'], 'dxfSha1': sha}


def _plan(manifest: Path, out: Path) -> dict:
    doc = json.loads(manifest.read_text(encoding='utf-8'))
    sources = {}
    for f in doc['floors']:
        if f['file'] not in sources:
            sources[f['file']] = read_dxf(out / f['file'], out / 'read' / Path(f['file']).stem)
        assert sources[f['file']]['sha1'] == f['sha1'], f'{f["file"]}: not the bytes the manifest names'
    doc['sources'] = list(sources.values())
    doc['dir'] = str(out)
    return doc


def stair_plan(variant: str, out: Path) -> dict:
    """`make-stair-dxf.py <variant>` into `out`, each plan read by the app's reader -> the tool's manifest (floors,
    layers, stairs with what is expected of them) plus `sources` (the SourceContexts, one per file) and `dir`."""
    _tool('make-stair-dxf.py', variant, str(out))
    return _plan(out / f'{variant}.json', out)


def reference_plan(out: Path) -> dict:
    """The reference building's DXFs (`make-reference-building.py dxf`) into `out`, read by the app's reader -> its
    manifest (as stair_plan's) plus `sources` and `dir`."""
    _tool('make-reference-building.py', 'dxf', str(out))
    return _plan(out / 'rooms-reference.json', out)


def plan_settings(plan: dict, *, rules: dict | None = None, **project) -> dict:
    """BuildSettings for a synthetic plan (stair_plan / reference_plan): one floor per manifest floor, whole file, the
    manifest's layers and levels; the three options = `rules` (default contracts.NEW_RULES; {} leaves the keys out: the
    old rule)."""
    s = json.loads((SETTINGS / 'small.json').read_text(encoding='utf-8'))
    name = plan.get('name') or f'Stair {plan["variant"]}'
    s['project'].update(name=name, shortName=name, photoName=name.replace(' ', '-'), maxPrefix='ST',
                        maxFileName=name.replace(' ', '_') + '.ms', **project)
    by_file = {src['name']: src for src in plan['sources']}
    s['sources'] = [{'sha1': src['sha1'], 'name': src['name'], 'kind': 'dxf', 'units': 'mm', 'unitsConfirmed': True}
                    for src in plan['sources']]
    s['layers'] = dict(plan['layers'])
    s['floors'] = [{'key': f['key'], 'name': f['name'], 'source': by_file[f['file']]['sha1'],
                    'area': f.get('area') or {'kind': 'wholeFile'}, 'level': f['level'], 'wallHeight': f['wallHeight'],
                    'slabThickness': None, 'doorHead': None, 'windowSill': None, 'windowHead': None,
                    'align': {'method': 'auto'}} for f in plan['floors']]
    s['options'].update(contracts.NEW_RULES if rules is None else rules)
    return s


def rooms_settings(name: str) -> dict:
    """fixtures/upload/settings/<name>-rooms.json (bank, house, suite, tower, suite-revit): the new rules."""
    return json.loads((SETTINGS / f'{name}-rooms.json').read_text(encoding='utf-8'))


def rooms_sources(name: str, s: dict, ref: Path) -> list[dict]:
    """The SourceContexts of a `*-rooms` build over the reference caches (WT_REF; the new suite: WT_REF_R0)."""
    from test_u3_bank import _drawings
    from test_u3_helpers import ref_sources
    return ref_sources(name, s, ref, drawings=_drawings(ref, kit.RUN) if name == 'bank' else None)


def rooms_build(name: str, ref: Path, tmp: Path) -> dict:
    """One new-rule build of a reference drawing in this process (the caller holds the machine run lock) ->
    { name, settings, sources, res, logs, tmp, project }."""
    from test_u3_helpers import run_build
    s = rooms_settings(name)
    sources = rooms_sources(name, s, ref)
    res, logs = run_build(s, sources, tmp, ROOMS_BUILDS[name])
    return {'name': name, 'settings': s, 'sources': sources, 'res': res, 'logs': logs, 'tmp': tmp,
            'project': ROOMS_BUILDS[name]}


CHILD = r'''
import hashlib, json, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import kit, rooms_kit
from test_u3_helpers import model_bytes
from walkthrough_builder import jsonfile, oslock
name, tmp = sys.argv[2], Path(sys.argv[3])
with oslock.hold():
    b = rooms_kit.rooms_build(name, kit.REF, tmp)
data = model_bytes(b['res']['model'])
(tmp / 'model.json').write_bytes(data)
rep = {k: v for k, v in b['res']['report'].items()}
for fl in rep['floors'].values():
    fl['detector'] = {k: v for k, v in fl['detector'].items() if k not in ('seconds', 'slow')}
(tmp / 'report.json').write_bytes(jsonfile.dumps(rep, pretty=False))
print(json.dumps({'model': hashlib.sha1(data).hexdigest(),
                  'report': hashlib.sha1((tmp / 'report.json').read_bytes()).hexdigest()}))
'''


def rooms_child_build(name: str, tmp: Path, hashseed: int, timeout: float = 3600) -> dict:
    """The new-rule build of a reference drawing in a CHILD process with PYTHONHASHSEED = `hashseed` (the child takes
    the machine run lock itself, so the calling test is marked `worker`-like: it must not hold the lock) ->
    { model: sha1 of model.json's bytes, report: sha1 of the report less the detector's timings }; the files are in
    `tmp`. Two calls with different seeds must give the same bytes (DESIGN R-13)."""
    tmp.mkdir(parents=True, exist_ok=True)
    p = kit.python_child(CHILD, str(Path(__file__).resolve().parent), name, str(tmp), hashseed=hashseed, cwd=kit.APP)
    out, err = p.communicate(timeout=timeout)
    assert p.returncode == 0, f'the child build of {name} failed:\n{out[-2000:]}\n{err[-4000:]}'
    return json.loads(out.strip().splitlines()[-1])
