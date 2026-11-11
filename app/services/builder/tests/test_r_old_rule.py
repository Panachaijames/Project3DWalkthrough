"""R0: the old-rule guard (docs/rooms/DESIGN.md R-13, ACCEPTANCE RA-1; WORK_BREAKDOWN R0 item 2). Frozen after R0:
R1 and R3 change the code it guards and may not edit it or its fixture.

Every output file of the five old-rule builds, as the builder of commit 66b4c06 wrote them, by sha1
(fixtures/rooms/old-rule.sha1.json): the bank from fixtures/upload/settings/bank.json, and the house, the old suite, the
tower and the new suite from their saved versions' recipes (fixtures/upload/settings/recipes/: the project-data.json of
the upload milestone's versions whose models are 1c07bfeef580, 205e9c2c46e8, 91414f408cb2, 1d90d91ef949), none of
which carries a key of the rooms milestone. Each is built in this process from the reference caches (WT_REF; the new
suite from R0's reader cache, WT_REF_R0) and written by U4's write_outputs with the build's moment fixed at
9 Nov 2026 12:00 UTC:

    model.json  stages.json  presentation.json  overlay.json  diff.json  topview.png  openings.json  pieces.json
    maxscript (the .ms, date "9 Nov 2026")   flags (overlay.flags)   report (report.json less the detector's timings)
    furniture.csv (the CSV download)

diff.json is made against a model that differs (the bank's v1, the prototypes' house and suite), so the diff writer's
rows are pinned too. The detector's timings (`seconds`, `slow`, a `slow` flag) are left out: they are not outputs of the
rule. Also here: the bank from settings with the three new options written out at their old values gives the same
bytes.

With WT_INTEGRATION=1 a missing reference fails; it does not skip (conftest.py `ref`, `ref_r0`).

Recording (R0 only; the fixture is frozen): WT_RECORD_OLD_RULE=1 writes the fixture, and refuses unless
services/builder/walkthrough_builder is exactly as at 66b4c06.
"""
from __future__ import annotations

import copy
import datetime as dt
import json
import os
import subprocess
from pathlib import Path

import pytest

import kit
from test_u3_bank import _drawings
from test_u3_helpers import GOLDEN_MODEL, build_ctx, csv_bytes, model_bytes, ref_sources, run_build, settings, sha1
from walkthrough_builder import contracts, jsonfile, oslock

pytestmark = pytest.mark.heavy

FIXTURE = kit.ROOMS_FIXTURES / 'old-rule.sha1.json'
BASE = '66b4c06'
BUILT_AT = dt.datetime(2026, 11, 9, 12, 0, 0, tzinfo=dt.timezone.utc)
CONVERTER = {'name': 'libredwg', 'version': '0.14', 'exeSha1': '0' * 40}
#: name -> (settings fixture, project id, model stamp, the model the diff is made against or None)
BUILDS = {
    'bank': ('bank', 'bank-sampeng', 'c3a9408304a2', 'bank-v1'),
    'house': ('recipes/house', 'house-upload', '1c07bfeef580', 'house'),
    'suite': ('recipes/suite', 'suite-upload', '205e9c2c46e8', 'suite'),
    'tower': ('recipes/tower', 'tower-upload', '91414f408cb2', None),
    'suite-revit': ('recipes/suite-revit', 'suite-revit', '1d90d91ef949', None),
}
FILES = ('model.json', 'stages.json', 'presentation.json', 'overlay.json', 'diff.json', 'topview.png', 'openings.json',
         'pieces.json', 'maxscript', 'flags', 'report', 'furniture.csv')
OLD_VALUES = {'slabs': 'closed-rooms', 'ceilings': 'off', 'stairs': 'lines'}


def write_fixed(res: dict, s: dict, sources: list[dict], tmp: Path, project_id: str, against: str | None) -> dict[str, Path]:
    """U4's write_outputs on a build's result, the build's moment fixed (the Max script's date), the converter named and
    the diff made against `against` (a fixtures/models name)."""
    import walkthrough_builder.out as OUT
    ctx = build_ctx(s, sources, tmp, project_id)
    ctx['converter'] = dict(CONVERTER)
    ctx['versionModel'] = str(kit.FIXTURES / 'models' / f'{against}.model.json') if against else None
    ctx['spec'].update(runId='0002-build', buildId='20261109T120000-abcdef', settingsRevision=1, only=None, office=None,
                       sources=[{'sha1': x['sha1'], 'name': x['name'], 'kind': x['kind'], 'path': str(tmp / 'no-original'),
                                 'units': x['units']} for x in sources])
    for d in (ctx['outDir'], ctx['tmpDir']):
        Path(d).mkdir(parents=True, exist_ok=True)
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(OUT, '_now', lambda: BUILT_AT)
        return contracts.write_outputs({k: v for k, v in res.items() if not k.startswith('_')}, ctx, lambda m: None)


def output_sha1s(res: dict, written: dict[str, Path], s: dict) -> dict[str, str]:
    """The sha1 of each pinned output (FILES), the detector's timings left out."""
    out = {}
    for name in ('model.json', 'stages.json', 'presentation.json', 'diff.json', 'topview.png', 'openings.json', 'pieces.json'):
        out[name] = sha1(written[name].read_bytes())
    ms = s['project']['maxFileName']
    data = written[ms].read_bytes()
    assert b'9 Nov 2026' in data, 'the Max script carries the fixed date'
    out['maxscript'] = sha1(data)
    raw = written['overlay.json'].read_bytes()
    ov = json.loads(raw)
    flags = [f for f in ov['flags'] if f['kind'] != 'slow']
    if len(flags) == len(ov['flags']):
        assert jsonfile.dumps(ov, pretty=False) == raw                 # the canonical bytes are the file's own
    ov['flags'] = flags
    out['overlay.json'] = sha1(jsonfile.dumps(ov, pretty=False))
    out['flags'] = sha1(jsonfile.dumps(flags, pretty=False))
    rep = copy.deepcopy(json.loads(written['report.json'].read_bytes()))
    for fl in rep['floors'].values():
        fl['detector'] = {k: v for k, v in fl['detector'].items() if k not in ('seconds', 'slow')}
    out['report'] = sha1(jsonfile.dumps(rep, pretty=False))
    out['furniture.csv'] = sha1(csv_bytes(res['model']))
    assert tuple(out) and set(out) == set(FILES)
    return {k: out[k] for k in FILES}


def build_old(name: str, ref: Path, tmp: Path, *, options: dict | None = None) -> dict:
    fixture, project, stamp, against = BUILDS[name]
    s = settings(fixture)
    assert not (set(s['options']) & set(OLD_VALUES)), f'{fixture}.json carries no key of the rooms milestone'
    if options:
        s['options'].update(options)
    drawings = _drawings(ref, kit.RUN) if name == 'bank' else None
    sources = ref_sources(name, s, ref, drawings=drawings)
    res, _logs = run_build(s, sources, tmp, project)
    written = write_fixed(res, s, sources, tmp, project, against)
    return {'res': res, 'written': written, 'files': output_sha1s(res, written, s),
            'stamp': sha1(model_bytes(res['model']))[:12], 'maxFileName': s['project']['maxFileName']}


@pytest.fixture(scope='module')
def built(ref, ref_r0, tmp_path_factory) -> dict[str, dict]:
    """The five old-rule builds, once for the module (the machine run lock held while they run)."""
    tmp = tmp_path_factory.mktemp('oldrule')
    with oslock.hold():
        return {name: build_old(name, ref, tmp / name) for name in BUILDS}


def _unchanged_builder() -> str | None:
    """None when services/builder/walkthrough_builder is exactly as at BASE, else why not."""
    rel = 'services/builder/walkthrough_builder'
    if subprocess.run(['git', 'diff', '--quiet', BASE, '--', rel], cwd=kit.APP).returncode != 0:
        return f'{rel} differs from {BASE}'
    left = subprocess.run(['git', 'status', '--porcelain', '--', rel], cwd=kit.APP, capture_output=True, text=True).stdout.strip()
    return f'{rel} has changed or untracked files: {left}' if left else None


if os.environ.get('WT_RECORD_OLD_RULE') == '1':             # recording is R0's, once; defined only then, so that a plain
    def test_record_the_fixture_from_the_unchanged_builder(built) -> None:        # run has no skipped test
        why = _unchanged_builder()
        assert why is None, f'the old-rule fixture is recorded from the unchanged builder only: {why}'
        tree = subprocess.run(['git', 'rev-parse', f'{BASE}:app/services/builder/walkthrough_builder'], cwd=kit.APP,
                              capture_output=True, text=True, check=True).stdout.strip()
        doc = {'format': 'old-rule-outputs/1', 'base': BASE, 'builderTree': tree, 'builtAt': '2026-11-09T12:00:00Z',
               'note': 'sha1 of every output of the five old-rule builds; written by test_r_old_rule.py from the builder '
                       'of the base commit (docs/rooms/DESIGN.md R-13). Frozen.',
               'builds': {name: {'settings': f'fixtures/upload/settings/{BUILDS[name][0]}.json', 'project': BUILDS[name][1],
                                 'diffAgainst': BUILDS[name][3], 'stamp': b['stamp'], 'maxFileName': b['maxFileName'],
                                 'files': b['files']} for name, b in built.items()}}
        FIXTURE.parent.mkdir(parents=True, exist_ok=True)
        FIXTURE.write_bytes(jsonfile.dumps(doc))


def expected() -> dict:
    return json.loads(FIXTURE.read_text(encoding='utf-8'))


def test_the_fixture_names_the_five_builds_and_their_stamps() -> None:
    fx = expected()
    assert fx['format'] == 'old-rule-outputs/1' and fx['base'] == BASE and len(fx['builderTree']) == 40
    assert {k: v['stamp'] for k, v in fx['builds'].items()} == {k: v[2] for k, v in BUILDS.items()}
    for name, b in fx['builds'].items():
        assert tuple(b['files']) == FILES, name
        assert all(len(v) == 40 for v in b['files'].values()), name
        assert b['files']['model.json'].startswith(b['stamp']), name
    assert fx['builds']['bank']['files']['model.json'] == GOLDEN_MODEL
    # the recipes are the saved versions' own, and none carries a key of this milestone
    for name in ('house', 'suite', 'tower', 'suite-revit'):
        raw = json.loads((kit.UPLOAD_FIXTURES / 'settings' / 'recipes' / f'{name}.json').read_text(encoding='utf-8'))
        assert not (set(raw['options']) & set(OLD_VALUES)) and 'ceilingHeight' not in raw['floors'][0], name
        assert set(raw['fixes']) == {'setAside', 'openings', 'outlineEdges'}, name


@pytest.mark.parametrize('name', list(BUILDS))
def test_every_output_of_the_old_rule_build_is_unchanged(name: str, built) -> None:
    want = expected()['builds'][name]
    got = built[name]
    assert got['stamp'] == want['stamp'] == BUILDS[name][2]
    moved = {k: (got['files'][k], want['files'][k]) for k in FILES if got['files'][k] != want['files'][k]}
    assert moved == {}, f'{name}: these old-rule outputs changed: {sorted(moved)}'


def test_the_old_rule_models_are_v1(built) -> None:
    for name, b in built.items():
        m = b['res']['model']
        assert 'stairways' not in m and 'spaces' not in m, name
        assert not any(p['kind'] in ('tread', 'landing', 'ceiling') for p in m['parts']), name
        assert not any('space' in r for r in m['rooms']), name
        assert set(b['res']['report']['fixes']) == {'setAside', 'openings', 'outlineEdges'}, name
        for fl in b['res']['report']['floors'].values():
            assert not ({'rooms', 'slab', 'stairways', 'stairClash'} & set(fl)), name


def test_bank_with_the_options_written_out_at_their_old_values(ref, built, tmp_path) -> None:
    again = build_old('bank', ref, tmp_path / 'bank-old-values', options=OLD_VALUES)    # a heavy test: the lock is held
    assert sha1(model_bytes(again['res']['model'])) == GOLDEN_MODEL
    assert again['files'] == built['bank']['files'] == expected()['builds']['bank']['files']
