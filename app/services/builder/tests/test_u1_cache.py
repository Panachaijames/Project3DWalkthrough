"""cache.py: the derived-file cache (docs/upload/DESIGN.md U-4.2; ACCEPTANCE 2.1 U1): the `.done` rule, the
tmp-then-rename read folder and its `auto` pointer, a rename that finds a complete target, conversions, LRU eviction above
the cap (never the run's own sources), stale staging folders."""
from __future__ import annotations

import os
import time
from pathlib import Path

import pytest

from walkthrough_builder import READER_VERSION, cache, jsonfile

A = 'a' * 40
B = 'b' * 40
C = 'c' * 40


def fill_read(folder: Path, tag: str = 'x', size: int = 100) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    (folder / 'items.pkl').write_bytes(tag.encode() * size)
    jsonfile.write(folder / 'drawing.json', {'tag': tag})
    (folder / 'plan.json.gz').write_bytes(b'\x1f\x8b' + tag.encode())


def read_entry_via_staging(root: Path, sha1: str, run_id: str, used: str, *, auto: bool, tag: str = 'x') -> Path:
    st = cache.read_staging(root, sha1, run_id)
    assert st.name == f'read-{READER_VERSION}-tmp-{run_id}' and not any(st.iterdir())
    fill_read(st, tag)
    return cache.commit_read(root, sha1, st, used, auto=auto)


def test_root_and_cap(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv('WALKTHROUGH_CACHE_DIR', str(tmp_path / 'c'))
    assert cache.cache_root() == tmp_path / 'c'
    monkeypatch.delenv('WALKTHROUGH_CACHE_DIR')
    monkeypatch.setenv('LOCALAPPDATA', str(tmp_path / 'lad'))
    assert cache.cache_root() == tmp_path / 'lad' / 'walkthrough' / 'cache'
    monkeypatch.delenv('WALKTHROUGH_CACHE_MAX_GB', raising=False)
    assert cache.max_gb() == 5.0
    monkeypatch.setenv('WALKTHROUGH_CACHE_MAX_GB', '0.5')
    assert cache.max_gb() == 0.5
    monkeypatch.setenv('WALKTHROUGH_CACHE_MAX_GB', 'lots')
    assert cache.max_gb() == 5.0


def test_done_rule(tmp_path: Path) -> None:
    d = tmp_path / 'e'
    fill_read(d)
    names = cache.READ_FILES
    assert not cache.complete(d, names)                       # no .done yet
    cache.write_done(d, names)
    assert cache.complete(d, names)
    done = jsonfile.read(d / '.done')
    assert set(done['files']) == set(names) and all(len(r['sha1']) == 40 for r in done['files'].values())
    # same size, other bytes
    (d / 'items.pkl').write_bytes(b'y' * 100)
    assert not cache.complete(d, names)
    fill_read(d)
    assert cache.complete(d, names)
    # other size
    (d / 'drawing.json').write_text('{}', encoding='utf-8')
    assert not cache.complete(d, names)
    fill_read(d)
    # a missing file
    (d / 'plan.json.gz').unlink()
    assert not cache.complete(d, names)
    fill_read(d)
    # a .done that lists other files, or is not JSON
    jsonfile.write(d / '.done', {'files': {'items.pkl': {'bytes': 100, 'sha1': '0' * 40}}})
    assert not cache.complete(d, names)
    (d / '.done').write_text('garbage', encoding='utf-8')
    assert not cache.complete(d, names)


def test_read_staging_rename_and_auto_pointer(tmp_path: Path) -> None:
    root = tmp_path / 'cache'
    assert cache.read_entry(root, A, None) is None
    assert cache.read_entry(root, A, 'mm') is None
    d = read_entry_via_staging(root, A, '0001-prepare', 'mm', auto=True)
    assert d == root / A / f'read-{READER_VERSION}-mm'
    assert not (root / A / f'read-{READER_VERSION}-tmp-0001-prepare').exists()
    assert jsonfile.read(root / A / f'read-{READER_VERSION}-auto.json') == {'units': 'mm'}
    assert cache.read_entry(root, A, None) == d                 # null units follow the pointer
    assert cache.read_entry(root, A, 'mm') == d
    assert cache.read_entry(root, A, 'cm') is None
    # an explicit read in other units does not move the pointer
    d_cm = read_entry_via_staging(root, A, '0002-prepare', 'cm', auto=False, tag='c')
    assert d_cm.name == f'read-{READER_VERSION}-cm'
    assert cache.read_entry(root, A, None) == d
    assert cache.read_entry(root, A, 'cm') == d_cm


def test_rename_onto_a_complete_entry_keeps_it(tmp_path: Path) -> None:
    root = tmp_path / 'cache'
    first = read_entry_via_staging(root, A, '0001-prepare', 'mm', auto=True, tag='first')
    before = (first / 'items.pkl').read_bytes()
    second = read_entry_via_staging(root, A, '0002-prepare', 'mm', auto=True, tag='second')
    assert second == first and (first / 'items.pkl').read_bytes() == before
    assert sorted(p.name for p in (root / A).iterdir()) == [f'read-{READER_VERSION}-auto.json',
                                                           f'read-{READER_VERSION}-mm']


def test_rename_onto_an_incomplete_entry_replaces_it(tmp_path: Path) -> None:
    root = tmp_path / 'cache'
    broken = root / A / f'read-{READER_VERSION}-mm'
    fill_read(broken, 'broken')                                # no .done: does not count
    d = read_entry_via_staging(root, A, '0001-prepare', 'mm', auto=False, tag='good')
    assert jsonfile.read(d / 'drawing.json') == {'tag': 'good'} and cache.complete(d, cache.READ_FILES)


def test_commit_read_needs_the_three_files(tmp_path: Path) -> None:
    root = tmp_path / 'cache'
    st = cache.read_staging(root, A, 'r1')
    (st / 'items.pkl').write_bytes(b'x')
    with pytest.raises(FileNotFoundError, match='drawing.json'):
        cache.commit_read(root, A, st, 'mm', auto=True)
    with pytest.raises(ValueError):
        cache.read_name('furlongs')
    with pytest.raises(ValueError):
        cache.read_entry(root, '../../etc', 'mm')


def test_pointer_to_missing_or_bad_units(tmp_path: Path) -> None:
    root = tmp_path / 'cache'
    (root / A).mkdir(parents=True)
    jsonfile.write(cache.auto_pointer(root, A), {'units': 'mm'})
    assert cache.read_entry(root, A, None) is None              # the entry it names is not there
    jsonfile.write(cache.auto_pointer(root, A), {'units': '../x'})
    assert cache.read_entry(root, A, None) is None


def test_conversion_entry(tmp_path: Path) -> None:
    root = tmp_path / 'cache'
    folder = cache.converter_folder('0.14')
    assert folder == 'libredwg-0.14'
    assert cache.conversion_entry(root, A, folder) is None
    work = tmp_path / 'work'
    work.mkdir()
    (work / 'plan.dxf').write_bytes(b'0\nSECTION\n')
    (work / 'convert.log').write_text('Warning: x\n', encoding='utf-8')
    jsonfile.write(work / 'conversion.json', {'verdict': 'ok'})
    d = cache.commit_conversion(root, A, folder, {n: work / n for n in cache.CONVERSION_FILES}, '0001-prepare')
    assert d == root / A / folder and cache.conversion_entry(root, A, folder) == d
    assert not (work / 'plan.dxf').exists()                     # moved, not copied
    assert not (root / A / f'{folder}.tmp-0001-prepare').exists()
    with pytest.raises(ValueError):
        cache.commit_conversion(root, B, folder, {'plan.dxf': work / 'x'}, 'r')


def test_hit_touches_done(tmp_path: Path) -> None:
    root = tmp_path / 'cache'
    d = read_entry_via_staging(root, A, 'r1', 'mm', auto=True)
    old = time.time() - 3600
    os.utime(d / '.done', (old, old))
    assert cache.read_entry(root, A, 'mm') == d
    assert (d / '.done').stat().st_mtime > old + 3000


def test_evict_lru_above_the_cap_never_the_runs_own(tmp_path: Path) -> None:
    root = tmp_path / 'cache'
    for i, sha in enumerate((A, B, C)):
        d = root / sha / f'read-{READER_VERSION}-mm'
        fill_read(d, sha[0], size=400_000)                     # ~0.4 MB each
        cache.write_done(d, cache.READ_FILES)
        t = time.time() - 3600 * (3 - i)                       # A oldest, C newest
        os.utime(d / '.done', (t, t))
    (root / 'not-an-entry').mkdir()
    sizes = {e['sha1']: e['bytes'] for e in cache.entries(root)}
    assert set(sizes) == {A, B, C} and all(s > 400_000 for s in sizes.values())
    # cap above the total: nothing goes
    assert cache.evict(root, set(), 1.0) == []
    # cap for about two entries: the oldest goes
    cap = (sizes[B] + sizes[C] + 1000) / 1024 ** 3
    assert cache.evict(root, set(), cap) == [A]
    assert not (root / A).exists() and (root / B).exists()
    # the run's own source is kept even when it is the oldest; the next one goes instead
    assert cache.evict(root, {B}, sizes[B] / 1024 ** 3) == [C]
    assert (root / B).exists() and not (root / C).exists()
    assert (root / 'not-an-entry').exists()


def test_evict_incomplete_entries_first(tmp_path: Path) -> None:
    root = tmp_path / 'cache'
    fill_read(root / A / f'read-{READER_VERSION}-mm', size=300_000)        # no .done: counts as oldest
    d = root / B / f'read-{READER_VERSION}-mm'
    fill_read(d, size=300_000)
    cache.write_done(d, cache.READ_FILES)
    assert cache.evict(root, set(), 0.0004) == [A]


def test_clean_stale(tmp_path: Path) -> None:
    root = tmp_path / 'cache'
    good = read_entry_via_staging(root, A, 'r1', 'mm', auto=True)
    (root / A / f'read-{READER_VERSION}-tmp-0009-prepare').mkdir()
    (root / A / 'libredwg-0.14.tmp-0009-prepare').mkdir()
    removed = cache.clean_stale(root)
    assert sorted(removed) == sorted([f'{A}/read-{READER_VERSION}-tmp-0009-prepare',
                                      f'{A}/libredwg-0.14.tmp-0009-prepare'])
    assert good.exists() and cache.read_entry(root, A, None) == good
