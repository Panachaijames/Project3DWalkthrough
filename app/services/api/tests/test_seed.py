"""The seed (DESIGN.md 9.2, 17.3): the table of 9.2, the version.json and meta.json it writes, idempotent with and without
--force, saved heights kept (or reset), the reserved files kept, nothing written outside --data, no __pycache__ in a
prototype folder, and a refused version changing nothing."""
from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest

from kit import FIXTURES, PROTOTYPES, pycache_dirs, read_json, tree
from walkthrough_api.jsonio import dumps_pretty, iso_utc, loads_strict, sha1_hex
from walkthrough_api.seed.__main__ import main
from walkthrough_api.seed.build import SEED_VERSION, SeedCommitError, SeedError, ms_stamp, seed
from walkthrough_api.seed.sources import SEED_TABLE, reads
from walkthrough_api.store.local import LocalStore

IDS = [f'{v.project_id}-v{v.version}' for v in SEED_TABLE]
quiet = {'log': lambda _line: None}


def vdir(data: Path, v) -> Path:
    return data / 'projects' / v.project_id / 'versions' / str(v.version)


@pytest.mark.parametrize('v', SEED_TABLE, ids=IDS)
def test_version_folder_follows_the_table(seeded, v) -> None:
    d = vdir(seeded, v)
    want = {'version.json', 'model.json', *(['stages.json'] if v.stages else []),
            *(f'assets/{a.name}' for a in v.assets), *(f'downloads/{Path(r).name}' for r in v.downloads),
            *(f'source/{Path(r).name}' for r in v.source)}
    assert set(tree(d)) == want
    for a in v.assets:
        assert (d / 'assets' / a.name).read_bytes() == (PROTOTYPES / v.path(a.src)).read_bytes()
    for rel in (*v.downloads, *v.source):
        folder = 'downloads' if rel in v.downloads else 'source'
        assert (d / folder / Path(rel).name).read_bytes() == (PROTOTYPES / v.path(rel)).read_bytes(), rel


@pytest.mark.parametrize('v', SEED_TABLE, ids=IDS)
def test_version_json(seeded, v) -> None:
    d = vdir(seeded, v)
    r = read_json(d / 'version.json')
    m = read_json(d / 'model.json')
    assert (d / 'version.json').read_bytes() == dumps_pretty(r)
    assert (r['format'], r['projectId'], r['version'], r['label'], r['sourceKind'], r['modelFormat']) == \
           ('walkthrough-version/1', v.project_id, v.version, v.label, v.source_kind, 'built-model/1')
    assert r['createdAt'] == iso_utc(max(os.stat(PROTOTYPES / v.path(f)).st_mtime for f in v.model_files))
    assert r['sourceFiles'] == m['source']
    assert r['floors'] == [{'key': f['key'], 'name': f['name'], 'level': f['level']} for f in m['floors']]
    assert r['hasStages'] == bool(v.stages) == (d / 'stages.json').is_file()
    assert r['downloads'] == {'maxScript': v.max_script, 'furnitureCsv': bool(m.get('furniture'))}
    assert r['seed']['from'] == reads(v) and r['seed']['seedVersion'] == SEED_VERSION
    assert all(p.startswith(v.folder + '/') for p in r['seed']['from'])
    assert [(a['name'], a['role'], a.get('floor'), a.get('modelRef')) for a in r['assets']] == \
           [(a.name, a.role, a.floor, a.model_ref) for a in v.assets]
    for a in r['assets']:
        data = (d / 'assets' / a['name']).read_bytes()
        assert (a['mediaType'], a['bytes'], a['sha1']) == ('image/png', len(data), sha1_hex(data))
        if a['role'] == 'plan-picture':
            assert m['pictureFrame'][a['floor']]['file'] == a['modelRef']
            assert data == (FIXTURES / 'pictures' / a['name']).read_bytes()
    assert set(r['presentation']) >= {'documentTitle', 'heading', 'intro', 'accent', 'legend', 'camera'}
    assert not (d / 'overrides.json').exists() and not (d / 'project-data.json').exists()


def test_meta_json(seeded) -> None:
    for project_id in dict.fromkeys(v.project_id for v in SEED_TABLE):
        vs = [v for v in SEED_TABLE if v.project_id == project_id]
        meta_path = seeded / 'projects' / project_id / 'meta.json'
        meta = read_json(meta_path)
        records = [read_json(vdir(seeded, v) / 'version.json') for v in vs]
        latest = read_json(vdir(seeded, vs[-1]) / 'model.json')
        assert meta_path.read_bytes() == dumps_pretty(meta)
        assert meta == {'format': 'walkthrough-project/1', 'id': project_id, 'name': latest['project'],
                        'shortName': latest['shortName'], 'projectNo': latest.get('projectNo'),
                        'sourceKind': vs[0].source_kind, 'createdAt': records[0]['createdAt'],
                        'updatedAt': records[-1]['createdAt'], 'latestVersion': vs[-1].version,
                        'versions': [v.version for v in vs]}
    assert sorted(p.name for p in (seeded / 'projects').iterdir()) == ['bank-sampeng', 'hotel-lobby', 'presidential-suite',
                                                                       'sukhumvit-house']
    # mappings/, .staging/ are not made; .lock is the store's cross-process lock (an empty file, store/filelock.py)
    assert sorted(p.name for p in seeded.iterdir()) == ['.lock', 'projects']
    assert (seeded / '.lock').read_bytes() == b''


def test_no_pycache_appeared_in_a_prototype_folder(seeded, pycache_before) -> None:
    assert pycache_dirs() == pycache_before


def test_idempotent_without_force(data_copy) -> None:
    before = {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in data_copy.rglob('*') if p.is_file()}
    result = seed(PROTOTYPES, data_copy, **quiet)
    assert not result.built and len(result.left_alone) == 5
    assert {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in data_copy.rglob('*') if p.is_file()} == before


def test_idempotent_with_force(data_copy) -> None:
    before = tree(data_copy, skip_seeded_at=True)
    result = seed(PROTOTYPES, data_copy, force=True, **quiet)
    assert len(result.built) == 5 and tree(data_copy, skip_seeded_at=True) == before
    assert not list(data_copy.rglob('.staging-*')) and not list(data_copy.rglob('.old-*'))


def test_force_keeps_saved_heights_and_reserved_files(data_copy) -> None:
    store = LocalStore(data_copy)
    saved = store.write_overrides('bank-sampeng', 2, {'table': 600})
    v2 = data_copy / 'projects' / 'bank-sampeng' / 'versions' / '2'
    (v2 / 'project-data.json').write_bytes(b'{"walls": []}\n')
    kept = (v2 / 'overrides.json').read_bytes()
    seed(PROTOTYPES, data_copy, force=True, **quiet)
    assert (v2 / 'overrides.json').read_bytes() == kept and (v2 / 'project-data.json').is_file()
    assert read_json(data_copy / 'projects' / 'bank-sampeng' / 'meta.json')['updatedAt'] == saved.updated_at
    seed(PROTOTYPES, data_copy, force=True, reset_overrides=True, **quiet)
    assert not (v2 / 'overrides.json').exists() and (v2 / 'project-data.json').is_file()
    assert read_json(data_copy / 'projects' / 'bank-sampeng' / 'meta.json')['updatedAt'] == \
           read_json(v2 / 'version.json')['createdAt']


def test_reset_without_force_drops_only_the_heights(data_copy) -> None:
    LocalStore(data_copy).write_overrides('hotel-lobby', 1, {'table': 600})
    result = seed(PROTOTYPES, data_copy, reset_overrides=True, **quiet)
    assert not result.built and [v.project_id for v in result.reset] == ['hotel-lobby']
    assert not (data_copy / 'projects' / 'hotel-lobby' / 'versions' / '1' / 'overrides.json').exists()


def copy_prototype_files(dst: Path) -> list[str]:
    """Only the files the seed table names (sources.reads), into dst."""
    files = sorted({p for v in SEED_TABLE for p in reads(v)})
    for rel in files:
        (dst / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(PROTOTYPES / rel, dst / rel)
    return files


def test_reads_only_the_table_and_writes_only_into_data(tmp_path, seeded) -> None:
    protos = tmp_path / 'prototypes'
    files = copy_prototype_files(protos)
    look = lambda: ({p: (p.read_bytes(), p.stat().st_mtime_ns) for p in protos.rglob('*') if p.is_file()},   # noqa: E731
                    sorted(protos.rglob('*')))
    snapshot = look()
    seed(protos, tmp_path / 'data', force=True, **quiet)
    assert look() == snapshot                              # nothing written, changed or added there (no folder either)
    assert not list(protos.rglob('__pycache__'))
    assert tree(tmp_path / 'data', skip_seeded_at=True) == tree(seeded, skip_seeded_at=True)
    assert len(files) == len({p for v in SEED_TABLE for p in reads(v)})


def corrupt(protos: Path, rel: str, edit) -> None:
    path = protos / rel
    obj = loads_strict(path.read_bytes())
    edit(obj)
    path.write_bytes(dumps_pretty(obj))


@pytest.mark.parametrize('rel, edit, says', [
    ('presidential_test/src/pres2_model.json', lambda m: m['parts'][0].update(z1=-5), '/parts/0/z1'),
    ('presidential_test/src/pres2_model.json', lambda m: m['parts'][0].update(kind='spaceship'), 'conversion failed'),
    ('cad_test/src/furniture_house.json', lambda m: m.update(offset=[0, 0]), 'centre'),
    ('cad_test/src/house3d_stages.json', lambda m: m['stats'].pop('gridLabels'), 'replay conversion failed'),
    ('bank_test/src/bank_stages.json', lambda m: m['captions'].pop('raise'), '/captions'),
    ('bank_test/src/bank_stages.json', lambda m: m.update(panelIntro='a <i>b</i>'), 'presentation'),
    ('hotel_test/src/hotel_model.json', lambda m: m['furnitureKinds'][0].update(count=999), '/furnitureKinds/0/count'),
], ids=['suite-z1', 'suite-kind', 'house-offset', 'house-stats', 'bank-caption', 'bank-intro', 'hotel-count'])
def test_a_refused_version_changes_nothing(tmp_path, seeded, rel, edit, says) -> None:
    protos = tmp_path / 'prototypes'
    copy_prototype_files(protos)
    corrupt(protos, rel, edit)
    data = tmp_path / 'data'
    shutil.copytree(seeded, data)
    before = tree(data)
    with pytest.raises(SeedError) as e:
        seed(protos, data, force=True, **quiet)
    assert says in str(e.value)
    assert tree(data) == before and not list(data.rglob('.staging-*'))


def test_a_max_script_that_does_not_pair_is_refused(tmp_path) -> None:
    protos = tmp_path / 'prototypes'
    copy_prototype_files(protos)
    ms = protos / 'hotel_test' / 'Hotel_Lobby.ms'
    ms.write_bytes(ms.read_bytes().replace(b'(model data 6ab030750886)', b'(model data 000000000000)', 1))
    with pytest.raises(SeedError, match='line 2 says model data 000000000000'):
        seed(protos, tmp_path / 'data', **quiet)
    assert not (tmp_path / 'data' / 'projects' / 'hotel-lobby' / 'versions' / '1').exists()


def test_a_folder_that_cannot_be_replaced_stops_the_seed_cleanly(data_copy, monkeypatch, capsys) -> None:
    """Every version passed its checks, but the third rename fails (on Windows: a file in the old folder is open). The two
    before it are in place, nothing staged is left behind, the folders on disk stay whole, and the message says so."""
    real = LocalStore.commit_version
    calls: list[tuple[str, int]] = []

    def flaky(self, project_id, n, staging, keep=()):
        calls.append((project_id, n))
        if len(calls) == 3:
            raise PermissionError(13, 'The process cannot access the file because it is being used by another process')
        return real(self, project_id, n, staging, keep)

    monkeypatch.setattr(LocalStore, 'commit_version', flaky)
    before = tree(data_copy, skip_seeded_at=True)
    with pytest.raises(SeedCommitError) as e:
        seed(PROTOTYPES, data_copy, force=True, **quiet)
    assert e.value.partial and 'Written before it: bank-sampeng v1, bank-sampeng v2' in str(e.value)
    assert not list(data_copy.rglob('.staging-*')) and not list(data_copy.rglob('.old-*'))
    assert tree(data_copy, skip_seeded_at=True) == before          # same files (each version folder whole)
    def always_busy(self, project_id, n, staging, keep=()):
        raise PermissionError(13, 'busy')

    monkeypatch.setattr(LocalStore, 'commit_version', always_busy)
    assert main(['--prototypes', str(PROTOTYPES), '--data', str(data_copy), '--force']) == 1
    err = capsys.readouterr().err
    assert 'could not be put in place' in err and 'nothing was changed' not in err


def test_ms_stamp() -> None:
    assert ms_stamp(b'-- title\n-- Same model (model data 0123456789ab). x\n') == '0123456789ab'
    assert ms_stamp(b'-- (model data 0123456789ab)\n-- line 2\n') is None
    assert ms_stamp(b'') is None


def test_cli(tmp_path, capsys) -> None:
    assert main(['--prototypes', str(PROTOTYPES), '--data', str(tmp_path / 'data')]) == 0
    out = capsys.readouterr().out
    assert 'bank-sampeng v1: floors 2, parts 124, openings 55' in out and '5 version(s) written, 0 left alone' in out
    assert main(['--prototypes', str(PROTOTYPES), '--data', str(tmp_path / 'data')]) == 0
    assert 'left alone (exists; --force rebuilds it)' in capsys.readouterr().out
    assert main(['--prototypes', str(tmp_path / 'nowhere'), '--data', str(tmp_path / 'data2')]) == 1
    assert 'nothing was changed' in capsys.readouterr().err
    with pytest.raises(SystemExit) as e:
        main(['--data', str(tmp_path)])
    assert e.value.code == 2
