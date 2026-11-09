"""Clean-up (docs/upload/DESIGN.md U-4.1) and paths (ACCEPTANCE 2.2): finished runs past the ones a build needs, builds
saved over 7 days ago, open builds untouched for 30 days, at start-up and before a run; a prepare under a 40-character id
at app/data's depth writes every file under 260 characters; camelCase answers; the Host check in front of the new routes."""
from __future__ import annotations

import os
import shutil
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from kit import APP, RUN, make_client
from test_routes import camel
from test_u5_builds import new_project, ready, save_settings, start
from upkit import FakeJobRunner, load
from walkthrough_api.jsonio import dumps_pretty

P = '/api/projects'
SAVE = {'label': 'saved', 'carryHeights': True, 'rememberMapping': False}


@pytest.fixture
def fake() -> FakeJobRunner:
    return FakeJobRunner()


@pytest.fixture
def api(data_copy: Path, template_file: Path, fake: FakeJobRunner) -> Iterator[TestClient]:
    with make_client(data_copy, template_file, jobs=fake) as c:
        yield c


def age(data: Path, project_id: str, build_id: str, days: float, status: str | None = None) -> None:
    path = data / 'projects' / project_id / 'builds' / build_id / 'build.json'
    record = load(path)
    record['updatedAt'] = '2026-01-01T00:00:00Z' if days > 0 else record['updatedAt']
    if status:
        record['status'] = status
    path.write_bytes(dumps_pretty(record))


def test_old_runs_go_before_a_new_run(api: TestClient, data_copy: Path) -> None:
    b = ready(api)
    for _ in range(4):
        b = api.post(f'{b["url"]}/run', json={}).json()
    runs = data_copy / 'projects' / b['projectId'] / 'builds' / b['id'] / 'runs'
    # 0001-prepare, then builds 0002 ... 0005: before each run, builds older than the two newest done ones went
    assert sorted(p.name for p in runs.iterdir()) == ['0001-prepare', '0003-build', '0004-build', '0005-build']
    b = api.post(f'{b["url"]}/run', json={}).json()
    assert sorted(p.name for p in runs.iterdir()) == ['0001-prepare', '0004-build', '0005-build', '0006-build']
    assert b['result']['runId'] == '0006-build'


def test_the_prepares_a_build_needs_stay(api: TestClient, data_copy: Path) -> None:
    b = ready(api)
    for units in ('cm', 'm', 'mm'):                                    # three one-source prepares of the second file
        s = b['settings']
        s['sources'][1]['units'] = units
        b = save_settings(api, b, s).json()
    b = api.post(f'{b["url"]}/run', json={}).json()
    runs = data_copy / 'projects' / b['projectId'] / 'builds' / b['id'] / 'runs'
    # the full prepare (the first file's reading and the suggestions) and the newest one-source prepare stay
    assert sorted(p.name for p in runs.iterdir()) == ['0001-prepare', '0004-prepare', '0005-build']
    d = api.get(b['url']).json()
    assert all(src['urls'] for src in d['sources']) and d['suggestions']


def test_old_builds_go(data_copy: Path, template_file: Path, fake: FakeJobRunner) -> None:
    with make_client(data_copy, template_file, jobs=fake) as api:
        pid = new_project(api)
        saved = ready(api, pid)
        saved = api.post(f'{saved["url"]}/run', json={}).json()
        assert api.post(f'{saved["url"]}/save', json=SAVE).status_code == 201
        stale_open = start(api, pid, both=False)
        fresh = start(api, pid, both=False)
        age(data_copy, pid, saved['id'], 10)
        age(data_copy, pid, stale_open['id'], 40)
        builds = data_copy / 'projects' / pid / 'builds'
        assert len(list(builds.iterdir())) == 3
        newest = start(api, pid, both=False)                          # before a new run: the old two go
        assert sorted(p.name for p in builds.iterdir()) == sorted([fresh['id'], newest['id']])
        assert not (builds / saved['id']).exists() and not (builds / stale_open['id']).exists()
        assert (builds / fresh['id']).exists()
        assert api.get(f'{P}/{pid}/versions/1').status_code == 200    # the version keeps what matters


def test_start_up_cleans_up(data_copy: Path, template_file: Path, fake: FakeJobRunner) -> None:
    with make_client(data_copy, template_file, jobs=fake) as api:
        pid = new_project(api)
        b = start(api, pid, both=False)
        s = api.post('/api/uploads', json={'projectId': pid, 'fileName': 'a.dwg', 'bytes': 5}).json()
    session = data_copy / '.uploads' / s['id'] / 'session.json'
    record = load(session)
    record['expiresAt'] = '2026-01-01T00:00:00Z'
    session.write_bytes(dumps_pretty(record))
    age(data_copy, pid, b['id'], 40)
    with make_client(data_copy, template_file, jobs=fake):
        pass
    assert not session.parent.exists()
    assert not (data_copy / 'projects' / pid / 'builds' / b['id']).exists()


def test_a_build_with_a_run_going_is_never_cleaned(data_copy: Path, template_file: Path) -> None:
    fake = FakeJobRunner('running')
    with make_client(data_copy, template_file, jobs=fake) as api:
        pid = new_project(api)
        b = start(api, pid, both=False)
    age(data_copy, pid, b['id'], 40)
    with make_client(data_copy, template_file, jobs=fake) as api:
        assert api.get(b['url']).json()['run']['status'] == 'running'


def test_a_prepare_under_a_40_character_id_at_the_store_depth_of_app_data(template_file: Path) -> None:
    depth = len(str(APP / 'data'))
    base = str(RUN.parent / 'd40')
    if len(base) > depth:
        pytest.skip(f'WT_TMP is deeper than app/data ({len(base)} > {depth} characters)')
    data = Path(base.ljust(depth, 'x'))
    assert len(str(data)) == depth
    if data.exists():
        shutil.rmtree(data)
    with make_client(data, template_file, jobs=FakeJobRunner()) as api:
        r = api.post(P, json={'name': 'x', 'id': 'p' * 40})
        assert r.status_code == 201, r.text[:200]
        b = start(api, 'p' * 40)
        assert b['run']['status'] == 'done' and b['settingsRevision'] == 1
        b = api.get(b['url']).json()
        s = b['settings']
        b = save_settings(api, b, s).json()
        b = api.post(f'{b["url"]}/run', json={}).json()
        assert b['result'] is not None
    paths = [os.path.abspath(p) for p in data.rglob('*')]
    longest = max(paths, key=len)
    assert len(longest) < 260 - 16, (len(longest), longest)
    assert any(p.endswith('conversion.json') and len(p) > 200 for p in paths)


def test_answers_are_camel_case(api: TestClient) -> None:
    b = ready(api)
    b = api.post(f'{b["url"]}/run', json={}).json()
    for body in (b, api.get(f'{P}/{b["projectId"]}/builds').json(), api.get('/api/offices').json()):
        camel({k: v for k, v in body.items() if k not in ('settings', 'suggestions')}, '')
    assert set(b) == {'id', 'projectId', 'createdAt', 'updatedAt', 'status', 'savedVersion', 'sourceNames', 'runStatus',
                      'url', 'sources', 'settings', 'settingsRevision', 'layersReviewedAt', 'suggestions', 'run',
                      'result', 'urls'}


def test_the_host_check_is_still_in_front(api: TestClient) -> None:
    r = api.post(P, json={'name': 'x'}, headers={'Host': 'evil.example'})
    assert r.status_code == 400
    r = api.get('/api/offices', headers={'Host': 'evil.example:8735'})
    assert r.status_code == 400
