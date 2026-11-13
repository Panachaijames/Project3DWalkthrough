"""deleteProject and deleteVersion (the owner's request of 12 Nov 2026; docs/contract-issues/DEL.md): the 204s, 404s and
409s (only_version, busy with a queued or a running run, a file held open), the tombstone (the files gone, the number
never given again, the listings skip it, latestVersion drops when the latest goes), a draft made from a deleted version,
and the readers of version folders with a tombstone present (the seed, the offline file's version list)."""
from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from kit import FIXTURES, PROTOTYPES, make_client, read_json
from test_u5_builds import bank_for, err, new_project, ready, save_settings
from upkit import FakeJobRunner, load, upload_bank
from walkthrough_api.seed.build import seed
from walkthrough_api.seed.sources import SEED_TABLE
from walkthrough_api.store import local as local_store
from walkthrough_api.store.base import NewProject, NotFound, StoreConflict, VersionDraft
from walkthrough_api.store.local import LocalStore

P = '/api/projects'
SAVE = {'label': '12 Nov 2026: a version to delete', 'carryHeights': True, 'rememberMapping': False}


@pytest.fixture
def fake() -> FakeJobRunner:
    return FakeJobRunner()


@pytest.fixture
def api(data_copy: Path, template_file: Path, fake: FakeJobRunner) -> Iterator[TestClient]:
    with make_client(data_copy, template_file, jobs=fake) as c:
        yield c


def files_of(folder: Path) -> list[str]:
    return sorted(p.relative_to(folder).as_posix() for p in folder.rglob('*') if p.is_file())


def draft(n: int) -> VersionDraft:
    """The bank's v2 model as a version of a store-made project (the hotel's presentation would not fit it)."""
    return VersionDraft(label=f'version {n}', source_kind='cad', source_files=[],
                        model_json=(FIXTURES / 'models' / 'bank-v2.model.json').read_bytes(), stages_json=None,
                        presentation=read_json(FIXTURES / 'presentation' / 'bank-sampeng-v2.json'))


def saved_version(api: TestClient, pid: str) -> int:
    """A build of the bank (FakeJobRunner) saved as the project's next version: its number."""
    b = ready(api, pid)
    b = api.post(f'{b["url"]}/run', json={}).json()
    r = api.post(f'{b["url"]}/save', json=SAVE)
    assert r.status_code == 201, r.text[:400]
    return r.json()['version']


# ================================================================================================= the store
def test_numbers_are_never_given_twice(tmp_path: Path) -> None:
    store = LocalStore(tmp_path / 'data')
    store.create_project(NewProject(id='three', name='Three', short_name='3', source_kind='cad'))
    assert [store.create_version('three', draft(n)).version for n in (1, 2, 3)] == [1, 2, 3]
    vdir = tmp_path / 'data' / 'projects' / 'three' / 'versions'
    meta = store.delete_version('three', 2)
    assert (meta.versions, meta.latest_version) == ([1, 3], 3)
    assert files_of(vdir / '2') == ['deleted.json']                          # the files gone, the folder kept
    tomb = load(vdir / '2' / 'deleted.json')
    assert tomb['format'] == 'walkthrough-deleted-version/1' and tomb['version'] == 2 and tomb['label'] == 'version 2'
    assert tomb['stamp'] == 'c3a9408304a2' and tomb['deletedAt']
    assert [v.version for v in store.list_versions('three')] == [1, 3]       # the listing skips it
    with pytest.raises(NotFound, match='was deleted') as e:
        store.get_version('three', 2)
    assert e.value.code == 'version_not_found'
    assert store.version_folder_numbers('three') == [1, 2, 3]
    assert store.create_version('three', draft(4)).version == 4              # delete v2 of three: the next is v4
    # the latest deleted: latestVersion drops, and its number is not given again either
    assert store.delete_version('three', 4).latest_version == 3
    assert store.get_project('three').versions == [1, 3]
    assert store.create_version('three', draft(5)).version == 5
    assert not list(vdir.glob('.staging-*')) and not list(vdir.glob('.old-*'))


def test_the_only_version_and_unknown_ones(tmp_path: Path) -> None:
    store = LocalStore(tmp_path / 'data')
    store.create_project(NewProject(id='one-only', name='One', short_name='1', source_kind='cad'))
    store.create_version('one-only', draft(1))
    with pytest.raises(StoreConflict):
        store.delete_version('one-only', 1)
    assert store.get_project('one-only').versions == [1] and (store.version_dir('one-only', 1) / 'model.json').is_file()
    with pytest.raises(NotFound) as e:
        store.delete_version('one-only', 7)
    assert e.value.code == 'version_not_found'
    with pytest.raises(NotFound) as e:
        store.delete_project('no-such-one')
    assert e.value.code == 'project_not_found'


def test_a_swap_that_fails_changes_nothing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    store = LocalStore(tmp_path / 'data')
    store.create_project(NewProject(id='held', name='Held', short_name='H', source_kind='cad'))
    for n in (1, 2):
        store.create_version('held', draft(n))
    before = files_of(store.version_dir('held', 2))
    meta_before = (store.project_dir('held') / 'meta.json').read_bytes()

    def held_open(src: Path, dst: Path, tries: int = 25) -> None:
        raise PermissionError(13, 'The process cannot access the file because it is being used by another process')

    monkeypatch.setattr(local_store, '_rename_dir', held_open)
    with pytest.raises(PermissionError):
        store.delete_version('held', 2)
    with pytest.raises(PermissionError):
        store.delete_project('held')
    monkeypatch.undo()
    assert (store.project_dir('held') / 'meta.json').read_bytes() == meta_before   # listed again, as it was
    assert files_of(store.version_dir('held', 2)) == before
    assert not list((store.project_dir('held') / 'versions').glob('.staging-*'))
    assert store.get_version('held', 2).version == 2 and [p.id for p in store.list_projects()] == ['held']


# ================================================================================================= deleteVersion
def test_delete_a_version(api: TestClient, data_copy: Path) -> None:
    vdir = data_copy / 'projects' / 'bank-sampeng' / 'versions'
    r = api.delete(f'{P}/bank-sampeng/versions/1')
    assert r.status_code == 204 and r.content == b''
    p = api.get(f'{P}/bank-sampeng').json()
    assert [v['version'] for v in p['versions']] == [2] and p['latestVersion'] == 2 and p['versionCount'] == 1
    assert files_of(vdir / '1') == ['deleted.json'] and (vdir / '2' / 'model.json').is_file()
    e = err(api.get(f'{P}/bank-sampeng/versions/1'), 404, 'version_not_found')
    assert 'was deleted' in e['message']
    for tail in ('model', 'stages', 'downloads/max-script', 'furniture-heights'):
        err(api.get(f'{P}/bank-sampeng/versions/1/{tail}'), 404, 'version_not_found')
    err(api.put(f'{P}/bank-sampeng/versions/1/furniture-heights', json={'heights': {}}), 404, 'version_not_found')
    err(api.delete(f'{P}/bank-sampeng/versions/1'), 404, 'version_not_found')        # deleted already
    summary = next(s for s in api.get(P).json()['projects'] if s['id'] == 'bank-sampeng')
    assert summary['versionCount'] == 1 and summary['latestVersion'] == 2
    assert api.get(f'{P}/bank-sampeng/thumbnail').status_code == 200


def test_delete_the_latest_version(api: TestClient, data_copy: Path) -> None:
    v1 = api.get(f'{P}/bank-sampeng/versions/1').json()
    assert api.delete(f'{P}/bank-sampeng/versions/2').status_code == 204
    p = api.get(f'{P}/bank-sampeng').json()
    assert p['latestVersion'] == 1 and p['stamp'] == v1['stamp'] and [v['version'] for v in p['versions']] == [1]
    meta = load(data_copy / 'projects' / 'bank-sampeng' / 'meta.json')
    assert (meta['latestVersion'], meta['versions']) == (1, [1])
    thumb = api.get(f'{P}/bank-sampeng/thumbnail')
    assert thumb.status_code == 200 and thumb.headers['etag'] == f'"{next(a["sha1"] for a in v1["assets"] if a["name"] == "topview.png")}"'
    assert api.get(f'{P}/bank-sampeng/versions/1/downloads/offline-html').status_code == 200


def test_version_refusals(api: TestClient) -> None:
    err(api.delete(f'{P}/no-such-project/versions/1'), 404, 'project_not_found')
    err(api.delete(f'{P}/bank-sampeng/versions/9'), 404, 'version_not_found')
    e = err(api.delete(f'{P}/hotel-lobby/versions/1'), 409, 'only_version')
    assert e['message'] == "This is the project's only version: delete the project instead."
    assert api.get(f'{P}/hotel-lobby/versions/1').status_code == 200
    assert api.delete(f'{P}/bank-sampeng/versions/0').status_code == 422
    assert api.delete(f'{P}/Bank/versions/1').status_code == 422


@pytest.mark.parametrize('mode', ['queued', 'running'])
def test_busy_while_a_run_is_going(api: TestClient, fake: FakeJobRunner, data_copy: Path, mode: str) -> None:
    """A file reading (a prepare) or a build of one of the project's drafts queued or running: 409 busy, nothing
    deleted; once it has ended, the deletes go through."""
    b = ready(api, 'bank-sampeng')
    fake.mode = mode
    d = api.post(f'{b["url"]}/run', json={}).json()
    assert d['run']['status'] == mode
    e = err(api.delete(f'{P}/bank-sampeng/versions/1'), 409, 'busy')
    assert e['message'] == 'Wait for the build to finish (or cancel it), then delete the version.'
    assert e['details'] == {'builds': [b['id']]}
    e = err(api.delete(f'{P}/bank-sampeng'), 409, 'busy')
    assert e['message'] == 'Wait for the build to finish (or cancel it), then delete the project.'
    assert api.get(f'{P}/bank-sampeng').json()['versionCount'] == 2
    assert (data_copy / 'projects' / 'bank-sampeng' / 'versions' / '1' / 'model.json').is_file()
    fake.finish(fake.started[-1])
    assert api.get(b['url']).json()['run']['status'] == 'done'
    assert api.delete(f'{P}/bank-sampeng/versions/1').status_code == 204
    assert api.delete(f'{P}/bank-sampeng').status_code == 204


def test_busy_while_a_file_is_read(api: TestClient, fake: FakeJobRunner) -> None:
    pid = new_project(api)
    fake.mode = 'running'
    sha1s = upload_bank(api, pid)
    b = api.post(f'{P}/{pid}/builds', json={'sources': sha1s}).json()
    assert b['run']['kind'] == 'prepare' and b['run']['status'] == 'running'
    err(api.delete(f'{P}/{pid}'), 409, 'busy')
    assert api.get(f'{P}/{pid}').status_code == 200


def test_a_file_held_open_is_busy_and_changes_nothing(api: TestClient, monkeypatch: pytest.MonkeyPatch,
                                                      data_copy: Path) -> None:
    def held_open(src: Path, dst: Path, tries: int = 25) -> None:
        raise PermissionError(13, 'in use')

    monkeypatch.setattr(local_store, '_rename_dir', held_open)
    e = err(api.delete(f'{P}/bank-sampeng/versions/1'), 409, 'busy')
    assert 'in use' in e['message'] and 'try again' in e['message']
    err(api.delete(f'{P}/bank-sampeng'), 409, 'busy')
    monkeypatch.undo()
    assert [v['version'] for v in api.get(f'{P}/bank-sampeng').json()['versions']] == [1, 2]
    assert (data_copy / 'projects' / 'bank-sampeng' / 'versions' / '1' / 'model.json').is_file()


# ================================================================================================= a draft and a deleted version
def test_drafts_and_a_deleted_version(api: TestClient, fake: FakeJobRunner, data_copy: Path) -> None:
    """Decided (DEL.md): an open draft made from a version keeps working when that version is deleted (its recipe and
    files are its own); a new draft from the deleted version gets 404 'was deleted'; the draft saved AS the deleted
    version goes with it; and numbers are never given again, the latest's included."""
    pid = new_project(api, newOfficeName='DWP Revit')
    assert saved_version(api, pid) == 1
    assert saved_version(api, pid) == 2
    saved_as_1 = next(b for b in api.get(f'{P}/{pid}/builds').json()['builds'] if b['savedVersion'] == 1)
    # an open draft from v1's recipe ("Use the files of v1 again"), read and adopted
    o = api.post(f'{P}/{pid}/builds', json={'sources': None, 'from': {'kind': 'version', 'version': 1}})
    assert o.status_code == 201, o.text[:300]
    o = api.get(o.json()['url']).json()
    assert o['settingsRevision'] == 1 and load(data_copy / 'projects' / pid / 'builds' / o['id'] / 'build.json')['from'] \
        == {'kind': 'version', 'version': 1}

    assert api.delete(f'{P}/{pid}/versions/1').status_code == 204
    err(api.get(saved_as_1['url']), 404, 'build_not_found')                 # the draft saved as v1 went with it
    assert not (data_copy / 'projects' / pid / 'builds' / saved_as_1['id']).exists()
    e = err(api.post(f'{P}/{pid}/builds', json={'sources': None, 'from': {'kind': 'version', 'version': 1}}), 404,
            'version_not_found')
    assert e['message'] == f"version 1 of '{pid}' was deleted"
    assert (data_copy / 'projects' / pid / 'sources').is_dir()              # the uploaded drawings stay with the project

    # the open draft from v1 still works: settings, build, save (as v3: 1 is never given again)
    o = save_settings(api, o, bank_for(o)).json()
    o = api.post(f'{o["url"]}/run', json={}).json()
    assert o['result'] is not None
    r = api.post(f'{o["url"]}/save', json=SAVE)
    assert r.status_code == 201, r.text[:300]
    assert r.json()['version'] == 3
    # the latest deleted: latestVersion 2, and the next version is v4
    assert api.delete(f'{P}/{pid}/versions/3').status_code == 204
    assert api.get(f'{P}/{pid}').json()['latestVersion'] == 2
    assert saved_version(api, pid) == 4
    p = api.get(f'{P}/{pid}').json()
    assert [v['version'] for v in p['versions']] == [2, 4] and p['latestVersion'] == 4
    assert (data_copy / 'mappings' / 'dwp-revit.json').is_file()


# ================================================================================================= deleteProject
def test_delete_a_project(api: TestClient, fake: FakeJobRunner, data_copy: Path) -> None:
    pid = new_project(api, newOfficeName='DWP Revit')
    assert saved_version(api, pid) == 1
    open_draft = ready(api, pid)
    folder = data_copy / 'projects' / pid
    assert (folder / 'sources').is_dir() and (folder / 'builds' / open_draft['id']).is_dir()
    # an upload session of the project that was never finished goes too
    s = api.post('/api/uploads', json={'projectId': pid, 'fileName': 'later.dwg', 'bytes': 10})
    assert s.status_code == 201
    upload_url = s.json()['url']
    r = api.delete(f'{P}/{pid}')
    assert r.status_code == 204 and r.content == b''
    assert not folder.exists() and not list((data_copy / 'projects').glob('.del-*'))
    err(api.get(f'{P}/{pid}'), 404, 'project_not_found')
    err(api.get(f'{P}/{pid}/versions/1'), 404, 'project_not_found')
    err(api.get(open_draft['url']), 404, 'project_not_found')
    err(api.delete(f'{P}/{pid}'), 404, 'project_not_found')
    err(api.get(upload_url), 404, 'upload_not_found')
    assert pid not in [p['id'] for p in api.get(P).json()['projects']]
    assert (data_copy / 'mappings' / 'dwp-revit.json').is_file()            # the office memory is shared: it stays
    # a project made again with the id starts empty
    r = api.post(P, json={'name': 'Bank re-upload', 'shortName': 'Bank branch', 'id': pid})
    assert r.status_code == 201, r.text[:300]
    assert r.json()['versionCount'] == 0 and api.get(f'{P}/{pid}/builds').json()['builds'] == []


def test_delete_a_seeded_project(api: TestClient, data_copy: Path) -> None:
    before = sorted(p['id'] for p in api.get(P).json()['projects'])
    assert api.delete(f'{P}/hotel-lobby').status_code == 204
    assert sorted(p['id'] for p in api.get(P).json()['projects']) == [i for i in before if i != 'hotel-lobby']
    assert not (data_copy / 'projects' / 'hotel-lobby').exists()
    assert api.get('/api/health').json()['projects'] == len(before) - 1


# ================================================================================================= readers with a tombstone
def test_the_seed_with_a_tombstone(data_copy: Path) -> None:
    """A deleted seeded version comes back with the seed (the same number, the same files: a restore, not a reuse; DEL.md),
    and a deleted version of a project the seed does not know stays deleted."""
    store = LocalStore(data_copy)
    v1 = store.get_version('bank-sampeng', 1)
    store.delete_version('bank-sampeng', 1)
    assert store.get_project('bank-sampeng').versions == [2]
    bank = [v for v in SEED_TABLE if v.project_id == 'bank-sampeng']
    result = seed(PROTOTYPES, data_copy, table=bank, log=lambda _line: None)
    assert [(b.source.project_id, b.source.version) for b in result.built] == [('bank-sampeng', 1)]
    store = LocalStore(data_copy)
    p = store.get_project('bank-sampeng')
    assert (p.versions, p.latest_version) == ([1, 2], 2)
    again = store.get_version('bank-sampeng', 1)
    assert (again.stamp, again.model_sha1, again.label) == (v1.stamp, v1.model_sha1, v1.label)
    assert not (store.version_dir('bank-sampeng', 1) / 'deleted.json').exists()


def test_the_offline_list_skips_a_tombstone(data_copy: Path) -> None:
    """make-offline.mjs lists meta.json's versions (a tombstone is not among them): checked here on the files it reads."""
    store = LocalStore(data_copy)
    store.delete_version('bank-sampeng', 2)
    meta = load(data_copy / 'projects' / 'bank-sampeng' / 'meta.json')
    assert meta['versions'] == [1] and meta['latestVersion'] == 1
    assert not (data_copy / 'projects' / 'bank-sampeng' / 'versions' / '2' / 'version.json').exists()
