"""job.py's own rules, in the test process (no worker spawned; docs/upload/DESIGN.md U-3.1, U-3.3, U-6.1, U-13.5):
the planned steps of both run kinds, the latest-version fallback for a seeded project (no project-settings.json and no
project-data.json, the rule of the API's adoption), the LibreDWG folder (the spec, else WALKTHROUGH_LIBREDWG_DIR
relative to app/, else the vendored one), and `validate`'s own checks (the API's record checks are covered by the
worker tests)."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

import kit
from walkthrough_builder import jsonfile
from walkthrough_builder.job import BUILD_OUTPUTS, Run, RunError, plan_steps

DWG = {'sha1': 'a' * 40, 'name': 'L1.dwg', 'kind': 'dwg', 'path': 'x', 'units': None}
DXF = {'sha1': 'b' * 40, 'name': 'L2.dxf', 'kind': 'dxf', 'path': 'y', 'units': None}


def names(steps: list[dict]) -> list[str]:
    return [s['name'] for s in steps]


def test_plan_steps_prepare() -> None:
    steps = plan_steps({'kind': 'prepare', 'sources': [DWG, DXF], 'only': None})
    assert names(steps) == ['convert:0', 'check:0', 'read:0', 'read:1', 'suggest']
    assert all(s['status'] == 'waiting' and s['seconds'] is None and s['note'] == '' for s in steps)
    assert steps[0]['label'] == 'Converting L1.dwg' and steps[3]['label'] == 'Reading L2.dxf'
    # a one-source prepare after a units change: that source's read only, no suggest (U-3.1, U-7.4)
    assert names(plan_steps({'kind': 'prepare', 'sources': [DWG, DXF], 'only': [DWG['sha1']]})) == ['read:0']


def test_plan_steps_build() -> None:
    spec = {'kind': 'build', 'sources': [DWG], 'settings': {'floors': [{'key': 'L1', 'name': 'Level 1'},
                                                                        {'key': 'L2', 'name': ''}]}}
    steps = plan_steps(spec)
    assert names(steps) == ['ensure', 'align', 'detect:L1', 'detect:L2', 'walls', 'openings', 'furniture', 'outputs',
                            'validate']
    assert steps[2]['label'] == 'Finding doors and windows on Level 1'
    assert steps[3]['label'] == 'Finding doors and windows on L2'           # an empty name falls back to the key


# ------------------------------------------------------------------------------------------------ latest version
def store_version(root: Path, *, data: bool = False, settings: bool = False, ms: str | None = 'Bank.ms') -> Path:
    vdir = root / 'projects' / 'p' / 'versions' / '2'
    vdir.mkdir(parents=True)
    (vdir / 'model.json').write_bytes(b'{}')
    if ms is not None:
        jsonfile.write(vdir / 'version.json', {'downloads': {'maxScript': ms, 'furnitureCsv': True}})
    if data:
        jsonfile.write(vdir / 'project-data.json', {})
    if settings:
        jsonfile.write(root / 'projects' / 'p' / 'project-settings.json', {})
    return vdir / 'model.json'


def run_with(tmp: Path, paths: dict) -> Run:
    r = Run(tmp / 'run')
    r.spec = {'kind': 'prepare', 'sources': [], 'paths': paths}
    return r


def test_latest_version_of_a_seeded_project(tmp_path: Path) -> None:
    vm = store_version(tmp_path)
    assert run_with(tmp_path, {'versionModel': str(vm)}).latest_version() == {'model': str(vm), 'msName': 'Bank.ms'}


@pytest.mark.parametrize('kw', [{'data': True}, {'settings': True}, {'data': True, 'settings': True}])
def test_no_latest_version_for_a_project_with_its_own_settings(tmp_path: Path, kw: dict) -> None:
    """U-3.3: only a project with no project-settings.json and no project-data.json takes from its latest version."""
    vm = store_version(tmp_path, **kw)
    assert run_with(tmp_path, {'versionModel': str(vm)}).latest_version() is None


def test_latest_version_without_a_version_record(tmp_path: Path) -> None:
    vm = store_version(tmp_path, ms=None)
    assert run_with(tmp_path, {'versionModel': str(vm)}).latest_version() == {'model': str(vm), 'msName': None}
    assert run_with(tmp_path, {'versionModel': None}).latest_version() is None
    assert run_with(tmp_path, {'versionModel': str(tmp_path / 'gone' / 'model.json')}).latest_version() is None
    assert run_with(tmp_path, {}).latest_version() is None


# ------------------------------------------------------------------------------------------------------ LibreDWG
def test_libredwg_folder(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv('WALKTHROUGH_LIBREDWG_DIR', raising=False)
    assert run_with(tmp_path, {}).libredwg() == kit.APP / 'vendor' / 'libredwg-0.14-win64'
    monkeypatch.setenv('WALKTHROUGH_LIBREDWG_DIR', 'vendor/other-build')             # relative to app/ (U-13.5)
    assert run_with(tmp_path, {}).libredwg() == kit.APP / 'vendor' / 'other-build'
    monkeypatch.setenv('WALKTHROUGH_LIBREDWG_DIR', str(tmp_path / 'abs'))
    assert run_with(tmp_path, {'libredwg': None}).libredwg() == tmp_path / 'abs'
    assert run_with(tmp_path, {'libredwg': str(tmp_path / 'spec')}).libredwg() == tmp_path / 'spec'   # the spec wins


# ------------------------------------------------------------------------------------------------------ validate
MS_NAME = 'Bank.ms'


def outputs_run(tmp: Path, monkeypatch: pytest.MonkeyPatch, *, model: dict | None = None,
                ms_stamp: str | None = None) -> Run:
    """A build run whose out/ holds every output of U-3.1, minimal but sound; the API's record checks are stubbed."""
    r = Run(tmp / 'run')
    r.spec = {'kind': 'build', 'sources': [], 'settings': {'project': {'maxFileName': MS_NAME}}}
    r.out.mkdir(parents=True)
    mb = json.dumps(model if model is not None else {'floors': [{'key': 'L1'}], 'parts': [{'kind': 'wall'}]},
                    separators=(',', ':')).encode()
    (r.out / 'model.json').write_bytes(mb)
    for n in BUILD_OUTPUTS:
        if n not in ('model.json', 'topview.png'):
            jsonfile.write(r.out / n, {})
    (r.out / 'topview.png').write_bytes(b'\x89PNG\r\n\x1a\n' + b'\x00' * 16)
    stamp = ms_stamp or hashlib.sha1(mb).hexdigest()[:12]
    (r.out / MS_NAME).write_bytes(f'-- header\r\n-- (model data {stamp})\r\nlast\r\n'.encode())
    monkeypatch.setattr(r, 'api_checks', lambda: [])
    return r


def written_of(r: Run) -> dict:
    return {n: str(r.out / n) for n in (*BUILD_OUTPUTS, MS_NAME)}


def test_validate_passes_sound_outputs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    r = outputs_run(tmp_path, monkeypatch)
    r.validate(written_of(r))


def test_validate_refuses(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    r = outputs_run(tmp_path, monkeypatch, model={'floors': [], 'parts': []})
    with pytest.raises(RunError) as e:
        r.validate(written_of(r))
    assert e.value.code == 'invalid_output' and e.value.step == 'validate'
    assert 'the model has no floors' in e.value.message and 'the model has no parts' in e.value.message

    r = outputs_run(tmp_path / 'b', monkeypatch, ms_stamp='0' * 12)
    with pytest.raises(RunError, match='line 2 does not carry the model stamp'):
        r.validate(written_of(r))

    r = outputs_run(tmp_path / 'c', monkeypatch)
    (r.out / 'topview.png').write_bytes(b'GIF89a')
    (r.out / MS_NAME).write_bytes((r.out / MS_NAME).read_bytes() + b'unix line\n')
    with pytest.raises(RunError) as e:
        r.validate(written_of(r))
    assert 'topview.png: not a PNG picture' in e.value.message and 'a line does not end with CRLF' in e.value.message

    r = outputs_run(tmp_path / 'd', monkeypatch)
    (r.out / 'pieces.json').unlink()
    with pytest.raises(RunError, match='The build did not write pieces.json'):
        r.validate(written_of(r))


def test_validate_checks_what_the_build_says_it_wrote(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Every file the build child reports must be a file directly in out/ (never elsewhere, never missing)."""
    r = outputs_run(tmp_path, monkeypatch)
    elsewhere = tmp_path / 'elsewhere.json'
    elsewhere.write_text('{}', encoding='utf-8')
    for extra in ({'stray.json': str(elsewhere)}, {'ghost.json': str(r.out / 'ghost.json')}):
        with pytest.raises(RunError) as e:
            r.validate({**written_of(r), **extra})
        name = next(iter(extra))
        assert f'{name}: reported by the build but not written in its out folder' in e.value.message
        assert str(tmp_path) not in e.value.message                              # no server path in the message
