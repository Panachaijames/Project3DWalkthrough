"""R0: the fixtures of the rooms milestone (docs/rooms/ACCEPTANCE.md 2.5; WORK_BREAKDOWN R0 item 8). Frozen after R0.

The reference building's fixtures say what DESIGN R-8 builds for its stair, pass the API's own record checks and hang
together (the run folder, the overlay, the flags); the synthetic drawings are the same bytes on every run; the settings
fixtures carry what R-1.3 says; the answer keys hold what ACCEPTANCE names. The reference drawings also build through
build() with whatever rules are in place (the tracer's at the scaffold, the real ones later): that test asserts only
what holds for both.
"""
from __future__ import annotations

import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from shapely.geometry import Polygon

import kit
import rooms_kit
from test_contracts import walk
from test_u3_helpers import check_file, run_build, write_and_check
from walkthrough_builder import contracts, oslock

FX = kit.FIXTURES
ROOMS = kit.ROOMS_FIXTURES
MODEL = FX / 'models' / 'rooms-reference.model.json'
RUN = ROOMS / 'runs' / 'reference-build'
R = 3.0 / 16
NEW_KINDS = {'slab-gap', 'room-open', 'room-names', 'doorway', 'stair', 'stairs-none', 'stair-clash', 'hole-skipped'}


def load(p: Path) -> dict:
    return json.loads(p.read_text(encoding='utf-8'))


@pytest.fixture(scope='module')
def model() -> dict:
    return load(MODEL)


@pytest.fixture(scope='module')
def result() -> dict:
    return load(ROOMS / 'build-result.reference.json')


# ------------------------------------------------------------------------------------------------ the settings fixtures
@pytest.mark.parametrize('name', ['bank', 'house', 'suite', 'tower', 'suite-revit'])
def test_rooms_settings_carry_the_new_rules(name: str) -> None:
    s = rooms_kit.rooms_settings(name)
    assert {k: s['options'][k] for k in contracts.NEW_RULES} == contracts.NEW_RULES
    base = load(kit.UPLOAD_FIXTURES / 'settings' / ('recipes/suite-revit.json' if name == 'suite-revit' else f'{name}.json'))
    assert not (set(base['options']) & set(contracts.NEW_RULES)), 'the fixture it comes from keeps the old rule'
    assert [f['key'] for f in s['floors']] == [f['key'] for f in base['floors']] and s['sources'] == base['sources']
    if name == 'house':
        assert [f['ceilingHeight'] for f in s['floors']] == [3.0, 2.9]
    if name == 'suite-revit':
        assert s['layers']['0'] == 'wall' and base['layers']['0'] == 'other' and s['fixes']['setAside'] == []


# --------------------------------------------------------------------------------------- the reference building's files
def test_every_fixture_passes_the_apis_checks() -> None:
    items = [('model', MODEL, None), ('stages', FX / 'stages' / 'rooms-reference.stages.json', MODEL),
             ('presentation', FX / 'presentation' / 'rooms-reference.json', MODEL),
             ('overlay', ROOMS / 'overlay.reference.json', None), ('settings', ROOMS / 'settings.reference.json', None),
             ('overlay', kit.UPLOAD_FIXTURES / 'overlay' / 'house-rooms.overlay.json', None),
             ('job', RUN / 'job.json', None), ('diff', RUN / 'out' / 'diff.json', None),
             ('openings', RUN / 'out' / 'openings.json', None), ('pieces', RUN / 'out' / 'pieces.json', None),
             ('inputs', RUN / 'out' / 'inputs.json', None)]
    items += [('model', FX / 'models' / f'stairs-{v}.model.json', None) for v in ('straight', 'L', 'U')]
    with ThreadPoolExecutor(max_workers=4) as pool:
        got = list(pool.map(lambda it: check_file(*it), items))
    assert [f'{it[0]} {it[1].name}: {out[-800:]}' for it, (code, out) in zip(items, got) if code != 0] == []


def test_the_stairway_is_what_the_design_builds(model: dict) -> None:
    assert len(model['stairways']) == 1
    sw = model['stairways'][0]
    assert {k: sw[k] for k in ('id', 'from', 'to', 'kind', 'risers', 'direction', 'treads', 'landings')} == {
        'id': 'S1', 'from': 'ground', 'to': 'upper', 'kind': 'L', 'risers': 16, 'direction': 'word', 'treads': 14, 'landings': 1}
    assert (sw['riser'], sw['going'], sw['width']) == (0.188, 0.28, 1.2)
    ox, oy = model['offset']
    walk_sheet = [[round(x + ox, 3), round(y + oy, 3)] for x, y in sw['walk']]
    # 1.0 m before riser 1, the middle of the first and last riser of each flight, the landing's middle, 1.0 m past riser 16
    assert walk_sheet == [[1.2, 0.8], [1.2, 1.8], [1.2, 3.48], [1.2, 4.08], [1.8, 4.08], [4.04, 4.08], [5.04, 4.08]]
    assert sw['bottom'] == sw['walk'][0] and sw['top'] == sw['walk'][-1]


def test_treads_landing_and_the_cut_wall(model: dict) -> None:
    ox, oy = model['offset']
    stair = [p for p in model['parts'] if p.get('stair') == 'S1']
    treads = sorted((p for p in stair if p['kind'] == 'tread'), key=lambda p: p['z1'])
    numbers = [int(t['label'].split()[-1]) for t in treads]
    assert numbers == [1, 2, 3, 4, 5, 6, 8, 9, 10, 11, 12, 13, 14, 15], 'tread 7 is the landing'
    for t, j in zip(treads, numbers):
        assert (t['floor'], t['fit'], t['follow']) == ('ground', 'storey', False)
        assert t['z1'] == pytest.approx(j * R, abs=1e-3) and t['z0'] == pytest.approx(max(0.0, (j - 2) * R), abs=1e-3)
    box = lambda p: [round(v, 3) for v in Polygon([(x + ox, y + oy) for x, y in p['o']]).bounds]      # noqa: E731
    assert box(treads[0]) == [0.6, 1.8, 1.8, 2.08] and box(treads[6]) == [1.8, 3.48, 2.08, 4.68]
    assert box(treads[-1]) == [3.76, 3.48, 4.09, 4.68], 'the last tread laps 0.05 m past riser 16'
    landing = [p for p in stair if p['kind'] == 'landing']
    assert len(landing) == 1 and box(landing[0]) == [0.6, 3.48, 1.8, 4.68] and landing[0]['label'] == 'stair S1 landing 7'
    assert landing[0]['z1'] == pytest.approx(7 * R, abs=1e-3) and landing[0]['z0'] == pytest.approx(7 * R - 0.15, abs=1e-3)
    cut = [p for p in stair if p['kind'] == 'wall']
    assert len(cut) == 1 and box(cut[0]) == [3.3, 3.48, 3.4, 4.68], 'the cupboard wall under tread 13'
    assert (cut[0]['z1'], cut[0]['fit'], cut[0]['follow']) == (pytest.approx(11 * R, abs=1e-3), 'storey', False)
    assert not any(p['kind'] == 'step' for p in model['parts'])


def test_the_well_the_void_and_the_ceilings(model: dict, result: dict) -> None:
    holes = {h['what']: h for h in result['report']['floors']['upper']['slab']['holes']}
    assert set(holes) == {'stair well', 'void'} and all(h['cut'] for h in holes.values())
    # treads 4 - 15 and the landing need headroom; grown 0.05 m, its edge at the arrival on riser 16 (x 4.04)
    assert Polygon(holes['stair well']['o']).equals(Polygon([(0.55, 2.59), (1.85, 2.59), (1.85, 3.43), (4.04, 3.43),
                                                             (4.04, 4.73), (0.55, 4.73)]))
    assert Polygon(holes['void']['o']).bounds == (3.4, 0.8, 6.0, 2.8)
    assert [v['what'] for v in model['voids']['upper']] == ['stair well', 'void'] and model['voids']['ground'] == []
    ground = result['report']['floors']['ground']
    assert [(h['what'], h['cut'], h['why']) for h in ground['slab']['holes']] == [('void', False, 'the lowest floor')]
    ceilings = {p['floor']: p for p in model['parts'] if p['kind'] == 'ceiling'}
    assert set(ceilings) == {'ground', 'upper'} and len(ceilings['ground']['h']) == 2 and ceilings['upper']['h'] == []
    assert all((p['z0'], p['z1'], p['follow']) == (2.68, 2.7, False) for p in ceilings.values())


def test_rooms_names_and_the_report(model: dict, result: dict) -> None:
    assert walk(result, contracts.BuildResult) == []
    assert [(s['id'], s['name'], s['names']) for s in model['spaces']] == [
        ('ground-R001', 'LIVING', ['LIVING', 'DINING']), ('ground-R002', 'KITCHEN', ['KITCHEN']), ('upper-R001', 'LOUNGE', ['LOUNGE'])]
    assert {r['name']: r.get('space') for r in model['rooms']} == {
        'LIVING': 'ground-R001', 'DINING': 'ground-R001', 'KITCHEN': 'ground-R002', 'GARAGE': None, 'LOUNGE': 'upper-R001'}
    g, u = result['report']['floors']['ground'], result['report']['floors']['upper']
    assert g['rooms']['open'] == [{'name': 'GARAGE', 'at': [9.0, 6.6]}]
    assert g['rooms']['several'] == [{'space': 'ground-R001', 'names': ['LIVING', 'DINING']}]
    assert [(c['kind'], c['a'], c['b'], c['width']) for c in g['slab']['closings']] == [('doorway', [7.0, 5.6], [7.0, 6.8], 1.2)]
    assert [(x['area'], x['mouth'], x['answered']) for x in g['slab']['unfloored']] == [(20.0, [[8.9, 8.9], [11.8, 8.9]], False)]
    assert [(r['id'], r['state'], r['why'], r['severity']) for r in g['stairways']] == [
        ('S1', 'climb', None, None), ('ground-ST2', 'lines', 'no direction', 'check')]
    assert [(c['stair'], c['kind'], c['area'], c['z1']) for c in g['stairClash']] == [('S1', 'wall', 0.12, 2.062)]
    assert (u['slab']['ring'], u['slab']['terraces'], u['slab']['plate']) == (63.9, 21.1, 85.0)
    assert result['report']['fixes']['closings'] == [] and result['replay']['facts']['climbable'] == 1
    assert [o['kind'] for o in model['openings']] == ['door', 'door', 'door'], 'the door finder finds the three doors only'


def test_the_overlay_and_one_flag_of_every_new_kind() -> None:
    ov = load(ROOMS / 'overlay.reference.json')
    for fl in ov['floors']:
        assert {'spaces', 'holes', 'stairs', 'closings', 'unfloored'} <= set(fl), fl['key']
    g = ov['floors'][0]
    assert [s['id'] for s in g['spaces']] == ['ground-R001', 'ground-R002'] and len(g['unfloored']) == 1
    assert [(s['id'], s['state']) for s in g['stairs']] == [('S1', 'climb'), ('ground-ST2', 'lines')]
    assert [c['kind'] for c in g['closings']] == ['doorway'] and [h['what'] for h in ov['floors'][1]['holes']] == ['stair well', 'void']
    kinds = {f['kind'] for f in ov['flags']}
    assert kinds & NEW_KINDS == NEW_KINDS - {'stairs-none'} and 'plate-dropped' not in kinds
    every = load(ROOMS / 'flags.every-kind.json')['flags']
    assert [f['kind'] for f in every] == ['slab-gap', 'room-open', 'room-names', 'doorway', 'stair', 'stairs-none', 'stair-clash',
                                          'hole-skipped']
    gap = every[0]
    assert gap['ref'] == {'a': [8.9, 8.9], 'b': [11.8, 8.9]} and gap['severity'] == 'check'


def test_the_run_folder_is_whole() -> None:
    run, job = load(RUN / 'run.json'), load(RUN / 'job.json')
    assert run['format'] == 'fake-run/1' and job['status'] == 'done' and set(job['outputs']) == set(run['outputs'])
    for name, src in run['outputs'].items():
        p = kit.APP / src['fixture'] if 'fixture' in src else RUN / src['file']
        data = p.read_bytes()
        assert job['outputs'][name] == {'bytes': len(data), 'sha1': hashlib.sha1(data).hexdigest()}, name
    assert (kit.APP / run['outputs']['model.json']['fixture']) == MODEL
    ms = (RUN / 'out' / 'Rooms_reference.ms').read_bytes()
    assert hashlib.sha1(MODEL.read_bytes()).hexdigest()[:12].encode() in ms.split(b'\n', 3)[1], 'line 2 carries the stamp'


def test_the_stair_models(model: dict) -> None:
    for variant, treads, landings in (('straight', 15, 0), ('L', 14, 1), ('U', 14, 1)):
        m = load(FX / 'models' / f'stairs-{variant}.model.json')
        sw = m['stairways'][0]
        assert (sw['kind'], sw['risers'], sw['treads'], sw['landings']) == (variant, 16, treads, landings), variant
        assert sum(p['kind'] == 'tread' for p in m['parts']) == treads and sum(p['kind'] == 'landing' for p in m['parts']) == landings
        assert any(v['what'] == 'stair well' for v in m['voids']['upper']), variant


def test_the_answer_keys() -> None:
    bank = load(ROOMS / 'keys' / 'bank.json')
    assert sum(len(v) for v in bank['floors'].values()) == 18
    probes = load(ROOMS / 'keys' / 'probes.json')['drawings']
    assert [p['id9Nov'] for p in probes['house']['probes']] == ['ground-004', 'ground-006', 'ground-018', 'ground-034', 'upper glass 44']
    assert [p['id9Nov'] for p in probes['suite']['probes']] == ['suite-025']
    assert [p['id9Nov'] for p in probes['tower']['probes']] == ['L29-001', 'L29-016', 'L29-025', 'L29-028', 'L30-033', 'L30-032',
                                                                'L30 glass 24', 'L30 glass 26']
    for d in probes.values():
        for p in d['probes']:
            assert len(p['at']) == 2 and len(p['n']) == 2 and set(p['sides']) <= {-1, 1} and p['sides']
    for name in ('house', 'suite'):
        assert load(ROOMS / 'keys' / f'{name}.json')['format'] == 'rooms-key/1'


# ------------------------------------------------------------------------------------------- the drawings, at test time
def test_the_stair_drawings_repeat(tmp_path: Path) -> None:
    sha = {}
    for run in ('a', 'b'):
        rooms_kit._tool('make-stair-dxf.py', 'all', str(tmp_path / run))
        sha[run] = {p.name: hashlib.sha1(p.read_bytes()).hexdigest() for p in sorted((tmp_path / run).iterdir())}
    assert sha['a'] == sha['b'] and len(sha['a']) == 15 + 7                      # 15 plans and 7 manifests
    for variant in ('straight', 'L', 'U', 'two-floor', 'no-direction', 'down-up-pair', 'split-level'):
        m = load(tmp_path / 'a' / f'{variant}.json')
        assert m['format'] == 'stair-dxf/1' and all(f['sha1'] == sha['a'][f['file']] for f in m['floors']), variant
        assert sum(f['risers'] for f in m['stairs'][0]['flights']) in (16, 9), variant


def test_the_reference_drawings_build_with_the_rules_in_place(reference_building: dict, tmp_path: Path) -> None:
    plan, s = reference_building['plan'], reference_building['settings']
    assert [f['key'] for f in plan['floors']] == ['ground', 'upper'] and len(plan['stairs']) == 2
    with oslock.hold():                                       # the door finder runs in this process (U-3.5)
        res, _logs = run_build(s, reference_building['sources'], tmp_path / 'build', 'rooms-reference')
    m = res['model']
    assert 'stairways' in m and 'spaces' in m, 'a v2 model'
    assert [o['kind'] for o in m['openings']] == ['door', 'door', 'door']
    assert not any(p['kind'] == 'step' for p in m['parts'])
    assert walk({k: v for k, v in res.items() if not k.startswith('_')}, contracts.BuildResult) == []
    for key, fl in res['report']['floors'].items():
        assert walk(fl, contracts.FloorUploadReportRooms) == [], key
    _written, problems = write_and_check(res, s, reference_building['sources'], tmp_path / 'outputs', 'rooms-reference')
    assert problems == []
