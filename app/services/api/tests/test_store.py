"""LocalStore behind Store (DESIGN.md 9.3): list, get, the NotFound codes, saved heights (atomic, revision, updatedAt),
the mtime cache, the reserved names left alone, and the next milestone's create_project / stage / create_version."""
from __future__ import annotations

import json
import threading

import pytest

from kit import FIXTURES, read_json
from walkthrough_api.builtmodel import ModelInvalid
from walkthrough_api.jsonio import dumps_compact, dumps_pretty, sha1_hex
from walkthrough_api.store.base import NewProject, NotFound, StagedRef, StoreConflict, StoreError, VersionDraft
from walkthrough_api.store.local import LocalStore, asset_roles, carry_heights, safe_name

IDS = ['bank-sampeng', 'hotel-lobby', 'presidential-suite', 'sukhumvit-house']


@pytest.fixture
def store(data_copy) -> LocalStore:
    return LocalStore(data_copy)


def code(fn, *args) -> str:
    with pytest.raises(NotFound) as e:
        fn(*args)
    return e.value.code


def test_list_and_get(store: LocalStore) -> None:
    assert [p.id for p in store.list_projects()] == IDS
    p = store.get_project('bank-sampeng')
    assert (p.latest_version, p.versions, p.name, p.short_name, p.project_no, p.source_kind) == \
           (2, [1, 2], 'Bangkok Bank, Sampeng Branch', 'Bank branch', '26-0216', 'cad')
    assert [v.version for v in store.list_versions('bank-sampeng')] == [1, 2]
    v = store.get_version('hotel-lobby', 1)
    assert v.source_kind == 'pictures' and v.thumbnail() and v.thumbnail().name == 'topview.png'
    assert store.get_project('hotel-lobby').source_kind == 'pictures'


def test_not_found_codes(store: LocalStore) -> None:
    assert code(store.get_project, 'nope-x') == 'project_not_found'
    assert code(store.get_project, '../data') == 'project_not_found'
    assert code(store.get_project, 'Bank') == 'project_not_found'
    assert code(store.get_version, 'bank-sampeng', 3) == 'version_not_found'
    assert code(store.get_version, 'bank-sampeng', 0) == 'version_not_found'
    assert code(store.get_version, 'nope-x', 1) == 'project_not_found'
    assert code(store.read_json_bytes, 'hotel-lobby', 1, 'stages.json') == 'no_stages'
    assert code(store.asset, 'hotel-lobby', 1, 'nope.png') == 'asset_not_found'
    assert code(store.asset, 'hotel-lobby', 1, '../model.json') == 'asset_not_found'
    assert code(store.asset, 'hotel-lobby', 1, 'model.json') == 'asset_not_found'        # not an asset of version.json
    assert code(store.download, 'hotel-lobby', 1, 'nope.ms') == 'download_not_found'
    assert code(store.download, 'hotel-lobby', 1, '..') == 'download_not_found'
    for odd in ('.', '...', 'Hotel_Lobby.ms.', 'a/b.ms', 'a\\b.ms', '', None):       # Windows drops trailing dots
        assert code(store.download, 'hotel-lobby', 1, odd) == 'download_not_found', odd
    assert code(store.asset, 'hotel-lobby', 1, 'floor1_plan.png.') == 'asset_not_found'
    assert code(store.read_file_bytes, 'sukhumvit-house', 1, 'overrides.json') == 'file_not_found'
    assert store.read_file_bytes('sukhumvit-house', 1, 'overrides.json', missing_ok=True) is None
    with pytest.raises(ValueError):
        store.read_json_bytes('hotel-lobby', 1, 'version.json')  # type: ignore[arg-type]


def test_files_as_stored(store: LocalStore, data_copy) -> None:
    d = data_copy / 'projects' / 'hotel-lobby' / 'versions' / '1'
    assert store.read_json_bytes('hotel-lobby', 1, 'model.json') == (d / 'model.json').read_bytes()
    assert store.read_file_bytes('hotel-lobby', None, 'meta.json') == (d.parent.parent / 'meta.json').read_bytes()
    assert store.read_file_bytes('hotel-lobby', 1, 'version.json') == (d / 'version.json').read_bytes()
    b = store.asset('hotel-lobby', 1, 'floor1_plan.png')
    assert (b.media_type, b.size, b.path) == ('image/png', 609351, d / 'assets' / 'floor1_plan.png')
    assert b.sha1 == sha1_hex((FIXTURES / 'pictures' / 'floor1_plan.png').read_bytes())
    m = store.download('hotel-lobby', 1, 'Hotel_Lobby.ms')
    assert m.media_type == 'text/plain; charset=utf-8' and m.sha1 == sha1_hex((d / 'downloads' / 'Hotel_Lobby.ms').read_bytes())


def test_saved_heights(store: LocalStore, data_copy) -> None:
    assert store.read_overrides('bank-sampeng', 2) is None
    before = store.get_project('bank-sampeng').updated_at
    a = store.write_overrides('bank-sampeng', 2, {'table': 600})
    b = store.write_overrides('bank-sampeng', 2, {'seat': 300})
    assert (a.revision, b.revision, b.heights) == (1, 2, {'seat': 300})
    path = data_copy / 'projects' / 'bank-sampeng' / 'versions' / '2' / 'overrides.json'
    assert read_json(path) == {'format': 'walkthrough-overrides/1', 'heights': {'seat': 300}, 'revision': 2,
                               'updatedAt': b.updated_at}
    assert path.read_bytes() == dumps_pretty(read_json(path))
    assert store.get_project('bank-sampeng').updated_at == b.updated_at > before        # a later save moves updatedAt
    assert not list(path.parent.glob('.tmp-*'))                                          # atomic: no temp file left
    assert LocalStore(data_copy).read_overrides('bank-sampeng', 2) == b                  # on disk, not only cached


def test_saved_heights_under_concurrency(store: LocalStore) -> None:
    errors: list[BaseException] = []

    def save(i: int) -> None:
        try:
            store.write_overrides('hotel-lobby', 1, {'table': 600 + i})
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)
    threads = [threading.Thread(target=save, args=(i,)) for i in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors and store.read_overrides('hotel-lobby', 1).revision == 20


def test_cache_follows_the_file(store: LocalStore, data_copy) -> None:
    p = store.get_project('sukhumvit-house')
    assert store.get_project('sukhumvit-house') is p                                      # cached
    meta = data_copy / 'projects' / 'sukhumvit-house' / 'meta.json'
    raw = read_json(meta)
    raw['name'] = 'Renamed'
    meta.write_bytes(dumps_pretty(raw))
    assert store.get_project('sukhumvit-house').name == 'Renamed'


def test_broken_store_files_are_store_errors(store: LocalStore, data_copy) -> None:
    (data_copy / 'projects' / 'sukhumvit-house' / 'meta.json').write_bytes(b'{"format": "x"}')
    with pytest.raises(StoreError):
        store.get_project('sukhumvit-house')
    (data_copy / 'projects' / 'hotel-lobby' / 'versions' / '1' / 'version.json').unlink()    # listed in meta.json, gone
    with pytest.raises(StoreError, match='lists version 1'):
        store.get_version('hotel-lobby', 1)
    assert code(store.get_version, 'hotel-lobby', 2) == 'version_not_found'                  # not listed: a plain 404


def test_reserved_names_are_left_alone(store: LocalStore, data_copy) -> None:
    (data_copy / 'mappings').mkdir()
    (data_copy / '.staging').mkdir()
    (data_copy / 'projects' / 'not a project').mkdir()
    (data_copy / 'projects' / 'no-meta-here').mkdir()
    (data_copy / 'projects' / 'bank-sampeng' / 'versions' / '2' / 'project-data.json').write_bytes(b'{"walls": []}\n')
    (data_copy / 'projects' / 'bank-sampeng' / 'versions' / '.staging-abc').mkdir()
    assert [p.id for p in store.list_projects()] == IDS
    assert [v.version for v in store.list_versions('bank-sampeng')] == [1, 2]


def test_create_project_stage_and_versions(tmp_path) -> None:
    store = LocalStore(tmp_path / 'data')
    meta = store.create_project(NewProject(id='new-project', name='A new project', short_name='New', source_kind='cad'))
    assert (meta.latest_version, meta.versions) == (0, [])
    with pytest.raises(StoreConflict):
        store.create_project(NewProject(id='new-project', name='x', short_name='x', source_kind='cad'))
    model = read_json(FIXTURES / 'models' / 'hotel.model.json')
    raw = (FIXTURES / 'models' / 'hotel.model.json').read_bytes()
    staged = store.stage('hotel model.json', [raw[:1000], raw[1000:]])
    assert isinstance(staged, StagedRef) and (store.staging_dir / staged.key).read_bytes() == raw
    pres = read_json(FIXTURES / 'presentation' / 'hotel-lobby.json')
    pics = {name: (FIXTURES / 'pictures' / name).read_bytes() for name in ('floor1_plan.png', 'floor2_plan.png')}
    v1 = store.create_version('new-project', VersionDraft(
        label='first', source_kind='pictures', source_files=model['source'], model_json=staged, stages_json=None,
        presentation=pres, assets=pics,
        # the real stamp: create_version refuses a .ms whose line 2 does not pair with the model (docs/upload U-11.1)
        downloads={'notes.ms': b'-- line 1\n-- (model data ' + sha1_hex(raw)[:12].encode() + b')\n'},
        source={'readme.md': b'# hi\n'}))
    assert v1.version == 1 and v1.stamp == sha1_hex(raw)[:12] and v1.stamp_source == 'model.json'
    assert not (store.staging_dir / staged.key).exists()                    # moved, not copied
    assert [(a.name, a.role, a.floor, a.model_ref) for a in v1.assets] == [
        ('floor1_plan.png', 'plan-picture', 'F1', '../source/floor1_plan.png'),
        ('floor2_plan.png', 'plan-picture', 'F2', '../source/floor2_plan.png')]
    assert v1.downloads.max_script == 'notes.ms' and v1.downloads.furniture_csv is True and v1.seed is None
    store.write_overrides('new-project', 1, {'table': 700, 'seat': 300})
    m2 = json.loads(raw)
    m2['furnitureKinds'] = [k for k in m2['furnitureKinds'] if k['key'] != 'seat']
    m2['furniture'] = [p for p in m2['furniture'] if p['kind'] != 'seat']
    for p in m2['furniture']:
        if p['on'] and p['on'] not in {q['id'] for q in m2['furniture']}:
            p['on'] = None
    v2 = store.create_version('new-project', VersionDraft(
        label='second', source_kind='pictures', source_files=[], model_json=dumps_compact(m2), stages_json=None,
        presentation=pres, carry_overrides_from=1))
    assert v2.version == 2 and store.read_overrides('new-project', 2).heights == {'table': 700}   # seat is gone
    p = store.get_project('new-project')
    assert (p.latest_version, p.versions) == (2, [1, 2])
    assert not list((tmp_path / 'data' / 'projects' / 'new-project' / 'versions').glob('.staging-*'))


def test_create_version_refuses_a_bad_model_and_writes_nothing(tmp_path) -> None:
    store = LocalStore(tmp_path / 'data')
    store.create_project(NewProject(id='bad-one', name='x', short_name='x', source_kind='cad'))
    bad = read_json(FIXTURES / 'models' / 'broken' / 'cross' / 'unknown-floor.json')
    pres = read_json(FIXTURES / 'presentation' / 'bank-sampeng-v2.json')
    with pytest.raises(ModelInvalid):
        store.create_version('bad-one', VersionDraft(label='x', source_kind='cad', source_files=[],
                                                     model_json=dumps_compact(bad), stages_json=None, presentation=pres))
    assert store.get_project('bad-one').versions == []
    assert list((tmp_path / 'data' / 'projects' / 'bad-one' / 'versions').iterdir()) == []


def test_safe_names() -> None:
    assert safe_name('topview.png') and safe_name('Bangkok_Bank_Sampeng.ms') and safe_name('a-b_c.1')
    for bad in ('.', '..', '...', 'x.', 'a b', 'a/b', 'a\\b', '', None, 7):
        assert not safe_name(bad), bad


def test_create_version_refuses_odd_file_names(tmp_path) -> None:
    store = LocalStore(tmp_path / 'data')
    store.create_project(NewProject(id='names', name='x', short_name='x', source_kind='cad'))
    raw = (FIXTURES / 'models' / 'bank-v2.model.json').read_bytes()
    pres = read_json(FIXTURES / 'presentation' / 'bank-sampeng-v2.json')
    for bad in ('..', 'notes.ms.', 'a b.ms'):
        with pytest.raises(ValueError):
            store.create_version('names', VersionDraft(label='x', source_kind='cad', source_files=[], model_json=raw,
                                                       stages_json=None, presentation=pres, downloads={bad: b'x'}))
    assert store.get_project('names').versions == []


def test_asset_roles_and_carry() -> None:
    hotel = read_json(FIXTURES / 'models' / 'hotel.model.json')
    assert asset_roles(hotel, ['topview.png', 'floor2_plan.png']) == {
        'topview.png': ('thumbnail', None, None), 'floor2_plan.png': ('plan-picture', 'F2', '../source/floor2_plan.png')}
    with pytest.raises(ValueError):
        asset_roles(hotel, ['other.png'])
    assert carry_heights({'table': 750, 'seat': 300, 'gone': 1}, hotel) == {'seat': 300}   # 750 is the model's table
