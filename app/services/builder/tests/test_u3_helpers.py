"""U3's test helpers (docs/upload/WORK_BREAKDOWN.md U3; ACCEPTANCE 2.1 U3), with their own self-checks.

* The reference caches (WT_REF, the scaffold's make:reference: prototype prims.pkl, no `k` keys) as SourceContexts.
* A synthetic plan drawn with ezdxf (deterministic), read by a minimal local reader: the scaffold's provisional reader
  `tools/upload/fixture_reader.py` (prims.py's walk plus the nested keys `k` of U-7.2, and a DrawingRead with grid
  labels), so the set-aside matcher can be tested before U2's reader lands.
* A fake detector (monkeypatched into walkthrough_builder.build) that returns chosen records, for the opening rules.
* `write_and_check`: a result through U4's contracts.write_outputs and the API's own record checks (check_file), the
  checks the API runs on a done run before it accepts it (U-3.2).
"""
from __future__ import annotations

import gzip
import hashlib
import json
import math
import pickle
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

import kit
from walkthrough_builder import contracts

SETTINGS = kit.UPLOAD_FIXTURES / 'settings'
GOLDEN_MODEL = 'c3a9408304a240b83c36f5c5c53db56b50a72c64'
GOLDEN_CSV = 'b528bb2320ef4a5e04ad3c1ad1e04ee09af67861'
CACHE_OF = {'bank': ['bank1', 'bank2'], 'house': ['sukhumvit'], 'suite': ['presidential'], 'tower': ['l29', 'l30']}
DRAWING_FIXTURE = {'bank1': kit.UPLOAD_FIXTURES / 'drawing' / 'bank1.drawing.json',
                   'sukhumvit': kit.UPLOAD_FIXTURES / 'drawing' / 'sukhumvit.drawing.json'}


def settings(name: str) -> dict:
    return json.loads((SETTINGS / f'{name}.json').read_text(encoding='utf-8'))


def model_bytes(model: dict) -> bytes:
    """U-10.9: model.json's bytes."""
    return json.dumps(model, separators=(',', ':'), ensure_ascii=False).encode('utf-8')


def sha1(b: bytes) -> str:
    return hashlib.sha1(b).hexdigest()


def source_ctx(sha: str, name: str, items: Path | str, *, drawing=None, conversion=None, units='mm', kind='dwg'):
    return {'sha1': sha, 'name': name, 'kind': kind, 'units': units, 'conversion': str(conversion) if conversion else None,
            'drawing': str(drawing) if drawing else None, 'items': str(items), 'plan': '', 'dxfSha1': None}


def build_ctx(s: dict, sources: list[dict], tmp: Path, project_id: str = 'test') -> dict:
    return {'spec': {'format': 'job-spec/1', 'kind': 'build', 'settings': s, 'projectId': project_id},
            'sources': sources, 'converter': None, 'previousRunModel': None, 'versionModel': None,
            'outDir': str(tmp / 'out'), 'tmpDir': str(tmp / 'tmp')}


def run_build(s: dict, sources: list[dict], tmp: Path, project_id: str = 'test') -> tuple[dict, list[str]]:
    from walkthrough_builder.build import build
    logs: list[str] = []
    steps: list[tuple[str, float]] = []
    res = build(build_ctx(s, sources, tmp, project_id), logs.append, lambda st, f: steps.append((st, f)))
    res['_steps'] = steps
    return res, logs


def ref_sources(name: str, s: dict, ref: Path, *, drawings: dict | None = None) -> list[dict]:
    """The SourceContexts of an acceptance drawing over the reference caches (prims.pkl: the reader's oracle)."""
    out = []
    for src, cache in zip(s['sources'], CACHE_OF[name]):
        dr = (drawings or {}).get(cache) or DRAWING_FIXTURE.get(cache)
        out.append(source_ctx(src['sha1'], src['name'], ref / 'proj' / 'detector' / cache / 'prims.pkl', drawing=dr))
    return out


def csv_bytes(model: dict) -> bytes:
    """The furniture CSV download (no heights), as the prototype wrote it."""
    from walkthrough_builder.vendor.load import load
    fk = load('furniture_kit')
    text = fk.csv_text(model['furniture'], model['furnitureKinds'], [f['key'] for f in model['floors']], model['offset'])
    return b'\xef\xbb\xbf' + text.encode('utf-8')


def strip_floor(records: list[dict]) -> list[dict]:
    return [{k: v for k, v in r.items() if k != 'floor'} for r in records]


# ------------------------------------------------------------------------------- the outputs and the API's checks
def check_file(kind: str, path: Path, model: Path | None = None) -> tuple[int, str]:
    """The API's own record check of one worker file, run as the design says: `node tools/run-py.mjs -m
    walkthrough_api.check_file <kind> <path> [--model <model>]` (the API's Python) -> (exit code, output)."""
    cmd = [shutil.which('node') or 'node', str(kit.APP / 'tools' / 'run-py.mjs'), '-m', 'walkthrough_api.check_file', kind,
           str(path)] + (['--model', str(model)] if model is not None else [])
    r = subprocess.run(cmd, cwd=kit.APP, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=300,
                       stdin=subprocess.DEVNULL)
    return r.returncode, (r.stdout + r.stderr).strip()


def write_and_check(res: dict, s: dict, sources: list[dict], tmp: Path, project_id: str = 'test') -> tuple[dict, list[str]]:
    """U4's contracts.write_outputs on a build's result, then the API's check of every output it validates when a run
    is done (U-3.2: the model with the schema and D-5.6, the replay and presentation against it, the sidecars) ->
    ({name: path}, the problems found: empty when the API would accept the run)."""
    from walkthrough_builder import contracts
    ctx = build_ctx(s, sources, tmp, project_id)
    ctx['spec'].update(runId='0002-build', buildId='20261109T120000-abcdef', settingsRevision=1, only=None, office=None,
                       sources=[{'sha1': x['sha1'], 'name': x['name'], 'kind': x['kind'], 'path': str(tmp / 'no-original'),
                                 'units': x['units']} for x in sources])
    for d in (ctx['outDir'], ctx['tmpDir']):
        Path(d).mkdir(parents=True, exist_ok=True)
    written = contracts.write_outputs({k: v for k, v in res.items() if not k.startswith('_')}, ctx, lambda m: None)
    m = written['model.json']
    items = [('model', m, None), ('stages', written['stages.json'], m), ('presentation', written['presentation.json'], m)]
    items += [(k, written[f'{k}.json'], None) for k in ('overlay', 'diff', 'pieces', 'openings', 'inputs')]
    with ThreadPoolExecutor(max_workers=4) as pool:
        got = list(pool.map(lambda it: check_file(*it), items))
    return written, [f'{it[0]}: {out[-1500:]}' for it, (code, out) in zip(items, got) if code != 0]


# ------------------------------------------------------------------------------------------- the synthetic plan
def plan_dxf(path: Path, *, dx: float = 0.0, dy: float = 0.0, chair_dx: float = 0.0, extra_first: int = 0,
             fill: str = 'solid', parapet: bool = False, free_glass: bool = False) -> Path:
    """A 10 x 6 m building (mm) with 200 mm walls drawn as solid fills on A-WALL, openings left in them:
         south wall: door 1 at x 4.0 - 5.0 (block 'Door slider 920x920x3100' on A-DOOR: W x W x H), door 2 at 7.0 - 8.0
                     (block 'Door plain', no size);
         north wall: a window at x 2.0 - 3.5 (glass lines on A-GLAZ 20 mm apart), a sliding glass door at 6.0 - 8.0;
         west wall:  an opening over a low wall at y 2.0 - 3.0.
       A grille (A_Grill, screen) of two lines 20 mm apart across door 1's footprint; a desk and a group block 'FurnGroup'
       (two 'Chair-Mollie-1234567-Level 1', one mirrored) on I-FURN; the room name LOBBY; grid lines 1, 2 (x 0, 10 m)
       and A, B (y 0, 6 m) with their bubbles; a corridor outline on A-AREA east of the building (x 10 - 14 m); a
       line drawn twice on A-ANNO. `dx, dy` move everything (mm); `chair_dx` moves the chair group only; `extra_first`
       adds that many lines first, so every handle changes (a re-export). Options that add to the drawing (off: the
       same file): `fill='pattern'` draws the wall fills as ANSI31 hatches instead of solid ones; `parapet` adds a
       low wall (a 2.0 x 0.2 m outline on A-WALL at x 17 - 19 m, y 1.0 - 1.2) with a railing line on A-HRAL meeting
       each of its ends; `free_glass` adds two A-GLAZ lines 20 mm apart standing alone at x 22 - 24 m, y 3.0."""
    import ezdxf
    from ezdxf import units
    doc = ezdxf.new('R2013')
    doc.units = units.MM
    for name in ('A-WALL', 'A-DOOR', 'A-GLAZ', 'A_Grill', 'I-FURN', 'A-AREA-IDEN', 'S-GRID', 'S-GRID-IDEN', 'A-AREA',
                 'A-ANNO', 'X-FIRST') + (('A-HRAL',) if parapet else ()):
        doc.layers.add(name)
    msp = doc.modelspace()
    for i in range(extra_first):
        msp.add_line((-5000 - i * 10, -5000), (-5000 - i * 10, -4000), dxfattribs={'layer': 'X-FIRST'})
    P = lambda x, y: (x + dx, y + dy)  # noqa: E731

    def wall(x0, y0, x1, y1):
        pts = [P(x0, y0), P(x1, y0), P(x1, y1), P(x0, y1)]
        h = msp.add_hatch(color=8, dxfattribs={'layer': 'A-WALL'})
        if fill == 'solid':
            h.set_solid_fill(color=8)
        else:
            h.set_pattern_fill('ANSI31', color=8, scale=10.0)
        h.paths.add_polyline_path(pts, is_closed=True)
    for r in ((0, 0, 4000, 200), (5000, 0, 7000, 200), (8000, 0, 10000, 200),
              (0, 5800, 2000, 6000), (3500, 5800, 6000, 6000), (8000, 5800, 10000, 6000),
              (0, 200, 200, 2000), (0, 3000, 200, 5800), (9800, 200, 10000, 5800)):
        wall(*r)
    door1 = doc.blocks.new('Door slider 920x920x3100')
    door1.add_line((0, 0), (900, 0))
    door1.add_arc((0, 0), 900, 0, 90)
    door2 = doc.blocks.new('Door plain')
    door2.add_line((0, 0), (900, 0))
    door2.add_arc((0, 0), 900, 0, 90)
    msp.add_blockref('Door slider 920x920x3100', P(4500, 100), dxfattribs={'layer': 'A-DOOR'})
    msp.add_blockref('Door plain', P(7500, 100), dxfattribs={'layer': 'A-DOOR'})
    msp.add_line(P(2000, 5890), P(3500, 5890), dxfattribs={'layer': 'A-GLAZ'})
    msp.add_line(P(2000, 5910), P(3500, 5910), dxfattribs={'layer': 'A-GLAZ'})
    msp.add_line(P(3500, 300), P(5500, 300), dxfattribs={'layer': 'A_Grill'})
    msp.add_line(P(3500, 320), P(5500, 320), dxfattribs={'layer': 'A_Grill'})
    desk = doc.blocks.new('Desk 1600x800')
    desk.add_lwpolyline([(0, 0), (1600, 0), (1600, 800), (0, 800)], close=True)
    chair = doc.blocks.new('Chair-Mollie-1234567-Level 1')
    chair.add_lwpolyline([(0, 0), (500, 0), (500, 500), (0, 500)], close=True)
    chair.add_line((0, 450), (500, 450))
    group = doc.blocks.new('FurnGroup')
    group.add_blockref('Chair-Mollie-1234567-Level 1', (0, 0))
    group.add_blockref('Chair-Mollie-1234567-Level 1', (1500, 0), dxfattribs={'xscale': -1})
    msp.add_blockref('Desk 1600x800', P(1000, 1000), dxfattribs={'layer': 'I-FURN'})
    msp.add_blockref('FurnGroup', P(6000 + chair_dx, 3000), dxfattribs={'layer': 'I-FURN'})
    msp.add_text('LOBBY', height=250, dxfattribs={'layer': 'A-AREA-IDEN'}).set_placement(P(3000, 2600))
    for x, label in ((0, '1'), (10000, '2')):
        msp.add_line(P(x, -1000), P(x, 7000), dxfattribs={'layer': 'S-GRID'})
        msp.add_text(label, height=300, dxfattribs={'layer': 'S-GRID-IDEN'}).set_placement(P(x, 7400))
    for y, label in ((0, 'A'), (6000, 'B')):
        msp.add_line(P(-1000, y), P(11000, y), dxfattribs={'layer': 'S-GRID'})
        msp.add_text(label, height=300, dxfattribs={'layer': 'S-GRID-IDEN'}).set_placement(P(-1400, y))
    msp.add_lwpolyline([P(10000, 1000), P(14000, 1000), P(14000, 5000), P(10000, 5000)], close=True,
                       dxfattribs={'layer': 'A-AREA'})
    for _ in range(2):
        msp.add_line(P(1000, 4000), P(2000, 4000), dxfattribs={'layer': 'A-ANNO'})
    if parapet:
        msp.add_lwpolyline([P(17000, 1000), P(19000, 1000), P(19000, 1200), P(17000, 1200)], close=True,
                           dxfattribs={'layer': 'A-WALL'})
        msp.add_line(P(15500, 1100), P(17000, 1100), dxfattribs={'layer': 'A-HRAL'})
        msp.add_line(P(19000, 1100), P(20500, 1100), dxfattribs={'layer': 'A-HRAL'})
    if free_glass:
        msp.add_line(P(22000, 3000), P(24000, 3000), dxfattribs={'layer': 'A-GLAZ'})
        msp.add_line(P(22000, 3020), P(24000, 3020), dxfattribs={'layer': 'A-GLAZ'})
    doc.saveas(path)
    return path


PLAN_LAYERS = {'A-WALL': 'wall', 'A-DOOR': 'door', 'A-GLAZ': 'window', 'A_Grill': 'screen', 'I-FURN': 'furniture',
               'A-AREA-IDEN': 'room-name', 'S-GRID': 'grid', 'S-GRID-IDEN': 'grid', 'A-AREA': 'room-outline',
               'A-ANNO': 'other', 'X-FIRST': 'other', '0': 'other', 'A-HRAL': 'railing'}


def read_plan(dxf: Path, out: Path) -> dict:
    """The minimal local reader: items.pkl (prims items + `k`) and drawing.json (grid labels) of a synthetic DXF."""
    sys.path.insert(0, str(kit.APP / 'tools' / 'upload'))
    import fixture_reader as FR
    out.mkdir(parents=True, exist_ok=True)
    W = FR.walk_drawing(dxf)
    units = {'declared': 'mm', 'votes': {u: 0 for u in ('mm', 'cm', 'm', 'in', 'ft')}, 'dimensionMedian': None,
             'used': 'mm', 'verdict': 'declared-only', 'note': ''}
    dr = FR.drawing_read(W, {'sha1': '0' * 40, 'name': dxf.name}, units)
    (out / 'items.pkl').write_bytes(pickle.dumps({'items': W['items'], 'layers': W['layers'], 'units': 'mm'}))
    (out / 'drawing.json').write_text(json.dumps(dr, ensure_ascii=False), encoding='utf-8')
    return {'items': out / 'items.pkl', 'drawing': out / 'drawing.json', 'W': W, 'read': dr}


def plan_settings(shas: list[str], *, levels=None, heights=None, **floor_extra) -> dict:
    """BuildSettings for synthetic plans: one floor per source (whole file)."""
    levels = levels or [3.0 * i for i in range(len(shas))]
    heights = heights or [3.0] * len(shas)
    s = settings('small')
    s['project'].update(name='Synthetic plan', shortName='Synthetic', photoName='Synthetic', maxPrefix='SY',
                        maxFileName='Synthetic.ms')
    s['sources'] = [{'sha1': sha, 'name': f'plan{i + 1}.dxf', 'kind': 'dxf', 'units': 'mm', 'unitsConfirmed': True}
                    for i, sha in enumerate(shas)]
    s['layers'] = dict(PLAN_LAYERS)
    s['floors'] = [{'key': f'F{i + 1}', 'name': f'Floor {i + 1}', 'source': sha, 'area': {'kind': 'wholeFile'},
                    'level': levels[i], 'wallHeight': heights[i], 'slabThickness': None, 'doorHead': None,
                    'windowSill': None, 'windowHead': None, 'align': {'method': 'auto'}, **floor_extra}
                   for i, sha in enumerate(shas)]
    return s


def record(rid, kind, a, b, *, subtype='', either=False, t=0.2, glazing=None):
    """A detector record (openings.finish's shape), drawing metres."""
    return {'id': rid, 'floor': f'test:{rid.split("-")[0]}', 'kind': kind, 'subtype': subtype, 'a': list(a), 'b': list(b),
            'width': round(math.dist(a, b), 3), 'wallThickness': t, 'host': 'wall', 'hinge': None, 'swing': None,
            'confidence': 0.9, 'evidence': ['synthetic'], 'eitherKind': either, 'glazing': glazing}


def plan_records(key='F1', dx=0.0, dy=0.0):
    """The synthetic plan's openings, as a detector would give them (metres)."""
    P = lambda x, y: (x + dx, y + dy)  # noqa: E731
    return [record(f'{key}-001', 'door', P(4.0, 0.1), P(5.0, 0.1), subtype='hinged single'),
            record(f'{key}-002', 'door', P(7.0, 0.1), P(8.0, 0.1), subtype='hinged single'),
            record(f'{key}-003', 'window', P(2.0, 5.9), P(3.5, 5.9), subtype='fixed', glazing=[-0.01, 0.01]),
            record(f'{key}-004', 'door', P(6.0, 5.9), P(8.0, 5.9), subtype='sliding glass door', either=True),
            record(f'{key}-005', 'window', P(0.1, 2.0), P(0.1, 3.0), subtype='opening over a low wall (no glass drawn)')]


class FakeDetector:
    """Monkeypatched in place of build.detect: records per floor key; remembers the items it was given."""

    def __init__(self, records: dict[str, list[dict]]):
        self.records = records
        self.items: dict[str, list[dict]] = {}

    def __call__(self, key, label, items, k, layer_lt, layers, project_id, tmp, log):
        self.items[key] = items
        recs = [dict(r, floor=f'{project_id}:{key}') for r in self.records.get(key, [])]
        return {'records': recs, 'seconds': 0.0, 'slow': False, 'frameRowsSkipped': None, 'swingsUnmatched': [],
                'output': ''}


@pytest.fixture
def fake_detector(monkeypatch):
    def install(records):
        fake = FakeDetector(records)
        import walkthrough_builder.build as B
        monkeypatch.setattr(B, 'detect', fake)
        return fake
    return install


# ------------------------------------------------------------------------------------------------ self-checks
def test_synthetic_plan_reads_with_keys(scratch: Path) -> None:
    dxf = plan_dxf(scratch / 'plan.dxf')
    r = read_plan(dxf, scratch / 'read')
    items = r['W']['items']
    keys = [d['k'] for d in items]
    assert len(keys) == len(set(keys)), 'keys unique within a source (U-7.2)'
    group = [d for d in items if d['t'] == 'INSERT' and d['name'] == 'FurnGroup']
    assert len(group) == 1
    sub = [d for d in items if d['k'].startswith(group[0]['k'] + '/')]
    assert sum(1 for d in sub if d['t'] == 'INSERT') == 2 and len(sub) >= 6
    labels = {g['text'] for g in r['read']['gridLabels'] if g['line']}
    assert labels == {'1', '2', 'A', 'B'}


def test_contract_walker_is_the_scaffolds() -> None:
    from test_contracts import walk
    assert walk({'method': 'none', 'shift': [0.0, 0.0], 'spread': None, 'labels': [], 'families': 0},
                contracts.AlignReport) == []


def gz_json(p: Path) -> dict:
    return json.loads(gzip.decompress(p.read_bytes()))
