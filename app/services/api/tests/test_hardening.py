"""The review findings of 3 Nov fixed in the API (the fix step after integration; docs/contract-issues/I.md "Fix step"):
saves and reads of the same file at once (Windows sharing violations), a save during the seed's folder swap (the
cross-process store lock), broken store files answering 500 store_error on every route, one broken project never taking the
list down, trailing newlines, non-finite numbers in a PUT, the Host check, If-Match, the object-store seam of the offline
payload, raster-only assets with nosniff and a sandbox, and a JSON answer for any 500."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from kit import FIXTURES, make_client, read_json
from walkthrough_api import builtmodel, checks, jsonio, offline
from walkthrough_api.settings import Settings
from walkthrough_api.store import local as local_mod
from walkthrough_api.store.base import BlobRef, NewProject, RevisionConflict, StoreError, VersionDraft
from walkthrough_api.store.filelock import StoreBusy, store_file_lock
from walkthrough_api.store.local import KEPT_ON_REBUILD, LocalStore, is_project_id, safe_name

API = '/api/projects'
V2 = f'{API}/bank-sampeng/versions/2'
HEIGHTS = f'{V2}/furniture-heights'


def err(r, status: int, code: str) -> dict:
    assert r.status_code == status, (r.status_code, r.text[:300])
    assert r.headers['content-type'].startswith('application/json'), r.headers['content-type']
    body = r.json()
    assert set(body) == {'error'} and body['error']['code'] == code and body['error']['message'], body
    return body['error']


# ---------------------------------------------------------------------------------------------------- code 1: sharing
def test_saves_and_reads_of_the_same_files_never_fail_each_other(data_copy: Path) -> None:
    """One thread saves heights (overrides.json and meta.json replaced each time) while three read them, for 4 s. On
    Windows a replace that meets an open reader, or a read that meets a replace, raised PermissionError (a 500) before."""
    store = LocalStore(data_copy)
    store.write_overrides('bank-sampeng', 2, {'table': 600})       # overrides.json exists before the readers start
    stop = time.monotonic() + 4
    errors: list[str] = []
    counts = {'write': 0, 'read': 0}

    def writer() -> None:
        i = 0
        while time.monotonic() < stop:
            i += 1
            try:
                store.write_overrides('bank-sampeng', 2, {'table': 600 + i % 50})
                counts['write'] += 1
            except Exception as exc:  # noqa: BLE001
                errors.append(f'write: {exc!r}')

    def reader(read) -> None:
        mine = LocalStore(data_copy)          # its own cache, as another request's view of the files
        while time.monotonic() < stop:
            try:
                read(mine)
                counts['read'] += 1
            except Exception as exc:  # noqa: BLE001
                errors.append(f'read: {exc!r}')

    reads = [lambda s: s.read_overrides('bank-sampeng', 2),
             lambda s: s.read_file_bytes('bank-sampeng', 2, 'overrides.json'),
             lambda s: s.read_file_bytes('bank-sampeng', None, 'meta.json')]
    threads = [threading.Thread(target=writer)] + [threading.Thread(target=reader, args=(r,)) for r in reads]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert errors == []
    assert counts['write'] > 20 and counts['read'] > 100, counts
    assert not list((data_copy / 'projects' / 'bank-sampeng' / 'versions' / '2').glob('.tmp-*'))


def test_a_file_that_stays_locked_is_a_store_error_not_a_bare_500(data_copy: Path, template_file: Path, monkeypatch) -> None:
    monkeypatch.setattr(jsonio, 'SHARING_RETRY_S', 0.05)
    real = Path.read_bytes

    def locked(self: Path) -> bytes:
        if self.name == 'overrides.json':
            raise PermissionError(13, 'Permission denied', str(self))
        return real(self)
    with make_client(data_copy, template_file) as c:
        assert c.put(HEIGHTS, json={'heights': {'table': 640}}).status_code == 200
        monkeypatch.setattr(Path, 'read_bytes', locked)
        for r in (c.get(V2), c.get(HEIGHTS), c.get(f'{V2}/downloads/furniture-csv')):
            e = err(r, 500, 'store_error')
            assert 'overrides.json' in e['message'] and str(data_copy) not in e['message']


def test_any_other_failure_is_still_an_error_response(data_copy: Path, template_file: Path, monkeypatch) -> None:
    def disk_full(*_a, **_k):
        raise OSError(28, 'No space left on device')

    def bug(*_a, **_k):
        raise RuntimeError('a bug')
    with make_client(data_copy, template_file, raise_server_exceptions=False) as c:
        monkeypatch.setattr(LocalStore, 'write_overrides', disk_full)
        e = err(c.put(HEIGHTS, json={'heights': {'table': 640}}), 500, 'store_error')
        assert 'No space left on device' in e['message']
        monkeypatch.setattr(LocalStore, 'write_overrides', bug)
        err(c.put(HEIGHTS, json={'heights': {'table': 640}}), 500, 'internal_error')


# ---------------------------------------------------------------------------------------------------- code 2: the seed's swap
def test_a_save_during_the_seeds_folder_swap_is_kept(data_copy: Path, template_file: Path, monkeypatch) -> None:
    """The seed copies overrides.json into the new folder, then swaps the folders. A save the API acknowledged in between
    was written into the old folder and deleted with it; now it waits for the store lock and lands in the new folder."""
    with make_client(data_copy, template_file) as api:
        assert api.put(HEIGHTS, json={'heights': {'table': 640}}).json()['revision'] == 1
        seed_store = LocalStore(data_copy)       # the seed's own store (another process in real life: the same file lock)
        vdir = seed_store.version_dir('bank-sampeng', 2)
        staging = seed_store.new_version_staging('bank-sampeng')
        for f in vdir.iterdir():                 # the rebuilt version: the same files, no overrides.json
            if f.name != 'overrides.json':
                (shutil.copytree if f.is_dir() else shutil.copy2)(f, staging / f.name)
        answered: dict = {}
        save = threading.Thread(target=lambda: answered.update(put=api.put(HEIGHTS, json={'heights': {'table': 600, 'seat': 300}})))
        real_copy2 = shutil.copy2

        def copy2_then_a_save(src, dst, *a, **kw):
            out = real_copy2(src, dst, *a, **kw)
            if Path(src).name == 'overrides.json':     # the seed has its copy: a staff member saves now
                save.start()
                time.sleep(1.0)                        # time enough for the save to land in the old folder (it did)
            return out
        monkeypatch.setattr(local_mod.shutil, 'copy2', copy2_then_a_save)
        seed_store.commit_version('bank-sampeng', 2, staging, keep=KEPT_ON_REBUILD)
        monkeypatch.undo()
        save.join(60)
        assert answered['put'].status_code == 200 and answered['put'].json()['revision'] == 2
        assert api.get(HEIGHTS).json()['heights'] == {'seat': 300, 'table': 600}


def test_the_store_lock_holds_across_processes(tmp_path: Path) -> None:
    root = tmp_path / 'data'
    code = ('import sys, time\nfrom pathlib import Path\nfrom walkthrough_api.store.filelock import store_file_lock\n'
            'with store_file_lock(Path(sys.argv[1])):\n    print("held", flush=True)\n    time.sleep(1.5)\n')
    with subprocess.Popen([sys.executable, '-B', '-c', code, str(root)], stdout=subprocess.PIPE, text=True,
                          env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'}) as holder:
        assert holder.stdout is not None and holder.stdout.readline().strip() == 'held'
        with pytest.raises(StoreBusy):
            with store_file_lock(root, timeout=0.2):
                pass
        t0 = time.monotonic()
        with store_file_lock(root):
            waited = time.monotonic() - t0
        assert waited > 0.5
        holder.wait(15)
    assert holder.returncode == 0


def test_exclusive_is_reentrant(data_copy: Path) -> None:
    store = LocalStore(data_copy)
    with store.exclusive():
        with store.exclusive():
            store.write_overrides('bank-sampeng', 2, {'table': 640})     # takes it a third time
    assert store.read_overrides('bank-sampeng', 2).heights == {'table': 640}


# ---------------------------------------------------------------------------------------------------- code 3: broken model
@pytest.mark.parametrize('case', ['not-json', 'no-photo-name', 'replaced-after-caching'])
def test_a_broken_model_is_a_store_error_on_every_route(data_copy: Path, template_file: Path, case: str) -> None:
    path = data_copy / 'projects' / 'bank-sampeng' / 'versions' / '2' / 'model.json'
    with make_client(data_copy, template_file) as c:
        if case == 'replaced-after-caching':
            assert c.get(f'{V2}/downloads/furniture-csv').status_code == 200          # parsed and cached
            path.write_bytes(b'{"broken": ')
        elif case == 'not-json':
            path.write_bytes(b'{"broken": ')
        else:
            m = read_json(path)
            del m['photoName']
            path.write_bytes(json.dumps(m).encode())
        for r in (c.get(V2), c.get(f'{V2}/model'), c.get(f'{V2}/downloads/furniture-csv'),
                  c.put(HEIGHTS, json={'heights': {'table': 640}}), c.get(f'{V2}/downloads/offline-html')):
            err(r, 500, 'store_error')
        assert c.get(HEIGHTS).json()['revision'] == 0                                  # the PUT saved nothing
        assert c.get(f'{API}/bank-sampeng/versions/1').status_code == 200              # the other version is fine


def test_the_furniture_kinds_must_be_a_list(data_copy: Path, template_file: Path) -> None:
    path = data_copy / 'projects' / 'bank-sampeng' / 'versions' / '2' / 'model.json'
    m = read_json(path)
    m['furnitureKinds'] = {'x': 1}
    path.write_bytes(json.dumps(m).encode())
    with make_client(data_copy, template_file) as c:
        err(c.get(V2), 500, 'store_error')
        err(c.put(HEIGHTS, json={'heights': {}}), 500, 'store_error')


# ---------------------------------------------------------------------------------------------------- code 4: the list
@pytest.mark.parametrize('broken', ['meta.json', 'versions/1/version.json'])
def test_one_broken_project_never_takes_the_list_down(data_copy: Path, template_file: Path, broken: str) -> None:
    (data_copy / 'projects' / 'hotel-lobby' / broken).write_bytes(b'not json')
    with make_client(data_copy, template_file) as c:
        health = c.get('/api/health')
        assert health.status_code == 200 and health.json()['projects'] in (3, 4)
        r = c.get(API)
        assert r.status_code == 200
        assert sorted(p['id'] for p in r.json()['projects']) == ['bank-sampeng', 'presidential-suite', 'sukhumvit-house']
        e = err(c.get(f'{API}/hotel-lobby'), 500, 'store_error')
        assert e['message'].startswith('projects/hotel-lobby/') and str(data_copy) not in e['message']
        assert ':\\' not in e['message'] and 'Users' not in e['message']             # no server paths


# ---------------------------------------------------------------------------------------------------- code 5: trailing newlines
def test_a_trailing_newline_is_refused_as_the_viewer_refuses_it() -> None:
    bank = read_json(FIXTURES / 'models' / 'bank-v2.model.json')
    for field, value in (('photoName', 'BangkokBank-Sampeng\n'), ('maxPrefix', 'BK\n')):
        m = json.loads(json.dumps(bank))
        m[field] = value
        assert f'/{field}' in [i.path for i in builtmodel.issues(m)], field
    m = json.loads(json.dumps(bank))
    m['furnitureKinds'][0]['colour'] = '#c0392b\n'
    assert '/furnitureKinds/0/colour' in [i.path for i in builtmodel.issues(m)]
    m = json.loads(json.dumps(bank))
    m['floors'][0]['key'] = 'L1\n'
    assert builtmodel.issues(m)
    pres = read_json(FIXTURES / 'presentation' / 'bank-sampeng-v2.json')
    pres['accent'] = '#2f6f8f\n'
    assert '/accent' in [i.path for i in checks.presentation_issues(pres, bank)]
    assert not checks.is_floor_key('L1\n') and checks.is_floor_key('L1')
    assert not is_project_id('new-upload\n') and is_project_id('new-upload')
    assert not safe_name('floor1_plan.png\n') and safe_name('floor1_plan.png')
    with pytest.raises(ValueError):
        NewProject(id='new-upload\n', name='x', short_name='x', source_kind='cad')


def test_ecma_pattern_turns_only_the_anchors() -> None:
    assert builtmodel.ecma_pattern('^[A-Z]{2,4}$') == r'^[A-Z]{2,4}\Z'
    assert builtmodel.ecma_pattern(r'^a\$b[$]$') == r'^a\$b[$]\Z'


# ---------------------------------------------------------------------------------------------------- code 6: NaN
@pytest.mark.parametrize('number', ['NaN', 'Infinity', '-Infinity', '1e400'])
def test_a_non_finite_number_gets_a_422(client: TestClient, number: str) -> None:
    r = client.put(HEIGHTS, content=f'{{"heights":{{"table":{number}}}}}'.encode(), headers={'Content-Type': 'application/json'})
    assert r.status_code == 422 and r.json()['detail'][0]['loc'] == ['body', 'heights', 'table']
    assert client.get(HEIGHTS).json()['revision'] == 0


# ---------------------------------------------------------------------------------------------------- code 7: the Host check
def test_another_host_name_is_refused(client: TestClient) -> None:
    for host in ('attacker.example:8711', 'attacker.example', '127.0.0.2:8711'):
        assert client.get(API, headers={'Host': host}).status_code == 400, host
        assert client.put(HEIGHTS, json={'heights': {'table': 640}}, headers={'Host': host}).status_code == 400, host
    assert client.get(HEIGHTS).json()['revision'] == 0
    for host in ('127.0.0.1:8710', '127.0.0.1:5710', 'localhost:5710', '127.0.0.1'):
        assert client.get('/api/health', headers={'Host': host}).status_code == 200, host


def test_the_allowed_hosts_come_from_the_environment() -> None:
    s = Settings.from_env({'WALKTHROUGH_ALLOWED_HOSTS': 'walkthrough.example, 127.0.0.1'})
    assert s.allowed_hosts == ('walkthrough.example', '127.0.0.1')
    assert Settings.from_env({}).allowed_hosts == ('127.0.0.1', 'localhost')


# ---------------------------------------------------------------------------------------------------- adversarial 3: If-Match
def test_if_match_refuses_a_save_over_heights_changed_elsewhere(client: TestClient) -> None:
    a = client.put(HEIGHTS, json={'heights': {'table': 600}}, headers={'If-Match': '"0"'})      # tab A, from nothing
    assert a.status_code == 200 and a.json()['revision'] == 1
    b = client.put(HEIGHTS, json={'heights': {'seat': 300}}, headers={'If-Match': '"0"'})       # tab B still thinks 0
    e = err(b, 412, 'revision_conflict')
    assert e['details'] == {'revision': 1, 'heights': {'table': 600}, 'updatedAt': a.json()['updatedAt']}
    merged = client.put(HEIGHTS, json={'heights': {'table': 600, 'seat': 300}}, headers={'If-Match': 'W/"1"'})
    assert merged.status_code == 200 and merged.json()['revision'] == 2
    err(client.put(HEIGHTS, json={'heights': {}}, headers={'If-Match': '*'}), 412, 'revision_conflict')
    assert client.put(HEIGHTS, json={'heights': {}}).json()['revision'] == 3                  # no header: last write wins


def test_write_overrides_checks_the_revision_under_the_lock(data_copy: Path) -> None:
    store = LocalStore(data_copy)
    store.write_overrides('bank-sampeng', 2, {'table': 600}, if_revision=0)
    with pytest.raises(RevisionConflict) as e:
        store.write_overrides('bank-sampeng', 2, {'seat': 300}, if_revision=0)
    assert e.value.current is not None and e.value.current.revision == 1 and e.value.current.heights == {'table': 600}


# ---------------------------------------------------------------------------------------------------- code 9: object store
class UrlStore(LocalStore):
    """A store whose assets are URLs (an object store later): no local path."""

    def asset(self, project_id: str, n: int, name: str) -> BlobRef:
        blob = super().asset(project_id, n, name)
        return BlobRef(media_type=blob.media_type, size=blob.size, sha1=blob.sha1, url=f'https://objects.example/{name}')


def test_the_offline_payload_reads_pictures_through_the_store(data_copy: Path) -> None:
    template = '<meta content="__WTV_STAMP__"><script type="application/json" id="wtv-data">__WTV_DATA__</script>'
    page = offline.offline_html(UrlStore(data_copy), 'hotel-lobby', 1, template)
    assert '"F1":"data:image/png;base64,' in page and '"F2":"data:image/png;base64,' in page
    assert page == offline.offline_html(LocalStore(data_copy), 'hotel-lobby', 1, template)


def test_a_missing_plan_picture_is_a_store_error(data_copy: Path, template_file: Path) -> None:
    (data_copy / 'projects' / 'hotel-lobby' / 'versions' / '1' / 'assets' / 'floor1_plan.png').unlink()
    with make_client(data_copy, template_file) as c:
        err(c.get(f'{API}/hotel-lobby/versions/1/downloads/offline-html'), 500, 'store_error')


# ---------------------------------------------------------------------------------------------------- code 11: assets
def test_assets_are_raster_pictures_only(tmp_path: Path) -> None:
    store = LocalStore(tmp_path / 'data')
    store.create_project(NewProject(id='svg-test', name='x', short_name='x', source_kind='pictures'))
    raw = (FIXTURES / 'models' / 'hotel.model.json').read_bytes()
    pres = read_json(FIXTURES / 'presentation' / 'hotel-lobby.json')
    svg = b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(document.domain)</script></svg>'
    for name in ('floor1_plan.png', 'topview.png'):
        with pytest.raises(ValueError, match='not a PNG'):
            store.create_version('svg-test', VersionDraft(label='x', source_kind='pictures', source_files=[], model_json=raw,
                                                          stages_json=None, presentation=pres, assets={name: svg}))
    assert store.get_project('svg-test').versions == []
    assert jsonio.media_type_of(svg, 'plan.svg') == 'application/octet-stream'
    assert jsonio.media_type_of((FIXTURES / 'pictures' / 'floor1_plan.png').read_bytes(), 'x.svg') == 'image/png'


def test_stored_files_are_never_sniffed_or_run(client: TestClient) -> None:
    for url in (f'{API}/hotel-lobby/versions/1/assets/floor1_plan.png', f'{API}/hotel-lobby/thumbnail',
                f'{V2}/downloads/max-script', f'{V2}/downloads/furniture-csv', f'{V2}/downloads/offline-html'):
        r = client.get(url)
        assert r.status_code == 200, url
        assert r.headers['x-content-type-options'] == 'nosniff', url
        assert r.headers['content-security-policy'] == 'sandbox', url
    assert client.get(API).headers['x-content-type-options'] == 'nosniff'


def test_store_errors_name_files_relative_to_the_store(data_copy: Path) -> None:
    store = LocalStore(data_copy)
    (data_copy / 'projects' / 'sukhumvit-house' / 'meta.json').write_bytes(b'{')
    with pytest.raises(StoreError) as e:
        store.get_project('sukhumvit-house')
    assert str(e.value).startswith('projects/sukhumvit-house/meta.json: ')
