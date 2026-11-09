"""The derived-file cache: converted DXFs and reads, keyed by source sha1 (docs/upload/DESIGN.md U-4.2).

    <cache>/<source sha1>/libredwg-0.14/plan.dxf + convert.log + conversion.json + .done
    <cache>/<source sha1>/read-<readerVersion>-<units>/items.pkl + drawing.json + plan.json.gz + .done
    <cache>/<source sha1>/read-<readerVersion>-auto.json            { "units": <what the reader chose with units null> }

* **The `.done` rule:** an entry counts only when its `.done` lists exactly the entry's files with their sizes and sha1s
  and every file is there with that size and sha1 (checked at every lookup: hashing the largest DXF, 105 MB, takes about
  0.2 s); anything else is recomputed. A cache hit touches `.done` (its mtime is the entry's last use). A pickle in the
  cache is only ever one the worker wrote.
* **Naming a read before it has run:** the reader writes into `read-<rv>-tmp-<runId>/`; `commit_read` writes `.done`
  there and renames the folder to `read-<rv>-<used units>/`, and, for a read whose units the reader chose
  (`units: null`), writes the `auto` pointer beside it. A rename that finds the target already complete keeps the
  existing entry. A conversion is committed the same way (`libredwg-0.14.tmp-<runId>/` -> `libredwg-0.14/`).
* **The cached conversion report** keeps the lost blocks' insert positions in the DRAWING's units (the units are known
  only after the read); `losscheck.publish()` turns them into sheet metres for the copies the run publishes.
* **Eviction** (`evict`, by the worker at the start of each run while it holds the machine lock): whole `<sha1>/`
  entries, least recently used first (the newest `.done` mtime inside), until the cache is under
  `WALKTHROUGH_CACHE_MAX_GB` (default 5); the run's own sources are never removed. `clean_stale` removes staging folders
  a killed worker left behind.

Owner: U1.
"""
from __future__ import annotations

import hashlib
import os
import re
import shutil
import time
from pathlib import Path

from . import READER_VERSION, jsonfile

DONE = '.done'
CONVERSION_FILES = ('plan.dxf', 'convert.log', 'conversion.json')
READ_FILES = ('items.pkl', 'drawing.json', 'plan.json.gz')
UNITS = ('mm', 'cm', 'm', 'in', 'ft')
SHA1_RE = re.compile(r'^[0-9a-f]{40}$')
DEFAULT_MAX_GB = 5.0


def cache_root() -> Path:
    """WALKTHROUGH_CACHE_DIR, default %LOCALAPPDATA%\\walkthrough\\cache (U-4.2)."""
    set_ = os.environ.get('WALKTHROUGH_CACHE_DIR')
    if set_:
        return Path(set_)
    base = os.environ.get('LOCALAPPDATA') or os.environ.get('TEMP') or '.'
    return Path(base) / 'walkthrough' / 'cache'


def max_gb() -> float:
    """WALKTHROUGH_CACHE_MAX_GB (default 5)."""
    try:
        v = float(os.environ.get('WALKTHROUGH_CACHE_MAX_GB') or DEFAULT_MAX_GB)
    except ValueError:
        return DEFAULT_MAX_GB
    return v if v > 0 else DEFAULT_MAX_GB


def sha1_file(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha1()
    with open(path, 'rb') as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def _check_sha1(sha1: str) -> str:
    if not isinstance(sha1, str) or not SHA1_RE.match(sha1):
        raise ValueError(f'not a source sha1: {sha1!r}')
    return sha1


# ============================================================================================================ the rule
def write_done(folder: Path, names: tuple[str, ...], **extra) -> dict:
    """Writes `.done` in `folder` listing `names` with their sizes and sha1s (the files must be there)."""
    files = {}
    for n in names:
        p = folder / n
        files[n] = {'bytes': p.stat().st_size, 'sha1': sha1_file(p)}
    done = {'format': 'cache-done/1', 'files': files, 'at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), **extra}
    jsonfile.write(folder / DONE, done)
    return done


def complete(folder: Path, names: tuple[str, ...]) -> bool:
    """True when `folder/.done` lists exactly `names` and each file is there with its listed size and sha1."""
    try:
        done = jsonfile.read(folder / DONE)
        files = done['files']
        if not isinstance(files, dict) or set(files) != set(names):
            return False
        for n in names:
            p = folder / n
            row = files[n]
            if p.stat().st_size != row['bytes'] or sha1_file(p) != row['sha1']:
                return False
    except (OSError, ValueError, KeyError, TypeError):
        return False
    return True


def touch(folder: Path) -> None:
    """A cache hit: `.done`'s mtime becomes now (the LRU order of `evict`)."""
    try:
        os.utime(folder / DONE)
    except OSError:
        pass


def _remove(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path, ignore_errors=True)
        if path.exists():                                   # a file still held open: one more try after a moment
            time.sleep(0.2)
            shutil.rmtree(path, ignore_errors=True)
    else:
        try:
            path.unlink()
        except FileNotFoundError:
            pass


def _commit(staging: Path, target: Path, names: tuple[str, ...], **extra) -> Path:
    """Writes `.done` in `staging` and renames it to `target`; a complete `target` is kept (the staging folder goes)."""
    write_done(staging, names, **extra)
    if complete(target, names):
        _remove(staging)
        touch(target)
        return target
    if target.exists():
        _remove(target)
    jsonfile.retry_on_sharing(lambda: os.replace(staging, target))
    return target


# ====================================================================================================== conversions
def converter_folder(version: str) -> str:
    """'libredwg-<version>' (the converter's folder in an entry, U-4.2)."""
    return f'libredwg-{version}'


def conversion_entry(root: Path, sha1: str, folder: str) -> Path | None:
    """The complete conversion folder of a source (touched), else None."""
    d = Path(root) / _check_sha1(sha1) / folder
    if complete(d, CONVERSION_FILES):
        touch(d)
        return d
    return None


def conversion_staging(root: Path, sha1: str, folder: str, run_id: str) -> Path:
    """A fresh, empty staging folder for a conversion of this run."""
    d = Path(root) / _check_sha1(sha1) / f'{folder}.tmp-{run_id}'
    _remove(d)
    d.mkdir(parents=True)
    return d


def commit_conversion(root: Path, sha1: str, folder: str, files: dict[str, Path], run_id: str) -> Path:
    """Moves `files` ({'plan.dxf': path, 'convert.log': path, 'conversion.json': path}) into the cache as one complete
    entry and returns its folder."""
    if set(files) != set(CONVERSION_FILES):
        raise ValueError(f'a conversion entry holds {CONVERSION_FILES}, not {sorted(files)}')
    staging = conversion_staging(root, sha1, folder, run_id)
    for name, src in files.items():
        shutil.move(str(src), str(staging / name))
    return _commit(staging, Path(root) / sha1 / folder, CONVERSION_FILES)


# ============================================================================================================ reads
def read_name(units: str) -> str:
    if units not in UNITS:
        raise ValueError(f'not a unit: {units!r}')
    return f'read-{READER_VERSION}-{units}'


def auto_pointer(root: Path, sha1: str) -> Path:
    return Path(root) / _check_sha1(sha1) / f'read-{READER_VERSION}-auto.json'


def read_entry(root: Path, sha1: str, units: str | None) -> Path | None:
    """The complete read-<rv>-<units> folder (or, for units None, the one the `auto` pointer names), touched; else
    None."""
    if units is None:
        try:
            units = jsonfile.read(auto_pointer(root, sha1)).get('units')
        except (OSError, ValueError, AttributeError):
            return None
        if units not in UNITS:
            return None
    d = Path(root) / _check_sha1(sha1) / read_name(units)
    if complete(d, READ_FILES):
        touch(d)
        return d
    return None


def read_staging(root: Path, sha1: str, run_id: str) -> Path:
    """A fresh, empty `read-<rv>-tmp-<runId>/` for the reader of this run."""
    d = Path(root) / _check_sha1(sha1) / f'read-{READER_VERSION}-tmp-{run_id}'
    _remove(d)
    d.mkdir(parents=True)
    return d


def commit_read(root: Path, sha1: str, staging: Path, used: str, *, auto: bool) -> Path:
    """`.done` in the staging folder, then renamed to read-<rv>-<used>; with `auto` (the reader chose the units) the
    pointer read-<rv>-auto.json says so. Returns the entry's folder."""
    for n in READ_FILES:
        if not (staging / n).is_file():
            raise FileNotFoundError(f'the reader did not write {n}')
    target = _commit(staging, Path(root) / _check_sha1(sha1) / read_name(used), READ_FILES, units=used)
    if auto:
        jsonfile.write(auto_pointer(root, sha1), {'units': used})
    return target


# ========================================================================================================= clean-up
def _entry_bytes(d: Path) -> int:
    total = 0
    for dirpath, _dirs, files in os.walk(d):
        for f in files:
            try:
                total += os.stat(os.path.join(dirpath, f)).st_size
            except OSError:
                pass
    return total


def _last_used(d: Path) -> float:
    newest = 0.0
    try:
        for sub in d.iterdir():
            try:
                newest = max(newest, (sub / DONE).stat().st_mtime)
            except OSError:
                pass
    except OSError:
        pass
    return newest


def entries(root: Path) -> list[dict]:
    """Every `<sha1>/` entry: {sha1, path, bytes, lastUsed}."""
    out = []
    try:
        subs = list(Path(root).iterdir())
    except OSError:
        return out
    for d in subs:
        if d.is_dir() and SHA1_RE.match(d.name):
            out.append({'sha1': d.name, 'path': d, 'bytes': _entry_bytes(d), 'lastUsed': _last_used(d)})
    return out


def evict(root: Path, keep: set[str], max_gb: float) -> list[str]:
    """Removes whole <sha1>/ entries, least recently used first (an entry with no `.done` counts as oldest), until the
    cache is under `max_gb`; never one in `keep`. Returns the removed sha1s."""
    limit = float(max_gb) * 1024 ** 3
    found = entries(root)
    total = sum(e['bytes'] for e in found)
    removed = []
    for e in sorted(found, key=lambda e: (e['lastUsed'], e['sha1'])):
        if total <= limit:
            break
        if e['sha1'] in keep:
            continue
        _remove(e['path'])
        if not e['path'].exists():
            total -= e['bytes']
            removed.append(e['sha1'])
    return removed


def clean_stale(root: Path) -> list[str]:
    """Removes staging folders (`read-<rv>-tmp-*`, `<converter>.tmp-*`) that a killed worker left behind. Only called
    while the machine lock is held (no other worker is writing)."""
    removed = []
    for e in entries(root):
        for sub in e['path'].iterdir():
            if sub.is_dir() and ('-tmp-' in sub.name or '.tmp-' in sub.name):
                _remove(sub)
                removed.append(f'{e["sha1"]}/{sub.name}')
    return removed
