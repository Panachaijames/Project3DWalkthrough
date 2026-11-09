"""LibreDWG in app/vendor/, from the release zip (docs/upload/DESIGN.md U-6.1; WORK_BREAKDOWN U0.1).

The zip is the authority. This script
  * copies the release zip to app/vendor/libredwg-0.14-win64.zip (when --zip names another copy) and checks its sha1;
  * extracts all of its entries into app/vendor/libredwg-0.14-win64/ (into a fresh folder beside it first, then renamed
    into place, so a half extraction never stands as the vendored copy);
  * writes app/vendor/libredwg.manifest.json (path, bytes and sha1 of every file; the zip's sha1 and entry count) when it
    does not exist, and otherwise checks the extraction against it;
  * --verify checks the extracted folder against the manifest without extracting (npm run check:pins does the same);
  * --add-licence <file> copies the GPL-3.0 text the owner fetched (gnu.org) in as libredwg-0.14-win64/COPYING and
    records its sha1 in the manifest (U-6.1).

Standard library only, so any Python runs it (npm run vendor:libredwg uses the builder Python, -B). Run from app/:
  node tools/run-builder-py.mjs tools/vendor-libredwg.py --zip <path of the release zip>
  node tools/run-builder-py.mjs tools/vendor-libredwg.py --verify
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import zipfile
from pathlib import Path, PurePosixPath

APP = Path(__file__).resolve().parent.parent
VENDOR = APP / 'vendor'
RELEASE = 'libredwg-0.14-win64'
ZIP_NAME = RELEASE + '.zip'
ZIP_SHA1 = 'edb5c01152c3ea9bcb46175aa3403fd18b941ff3'
ZIP_ENTRIES = 75
MANIFEST = VENDOR / 'libredwg.manifest.json'
TARGET = VENDOR / RELEASE
LICENCE_NAME = 'COPYING'


def sha1_file(p: Path) -> str:
    h = hashlib.sha1()
    with open(p, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def safe_name(name: str) -> PurePosixPath:
    """An entry name as a relative path that stays inside the target (the zip is downloaded data: no '..', no drive,
    no absolute path, no backslash)."""
    if '\\' in name or ':' in name or name.startswith('/'):
        raise SystemExit(f'vendor-libredwg: refusing the zip entry {name!r} (not a plain relative path)')
    p = PurePosixPath(name)
    if any(part in ('..', '') for part in p.parts if part != '.') or p.is_absolute():
        raise SystemExit(f'vendor-libredwg: refusing the zip entry {name!r} (leaves the folder)')
    return p


def list_files(root: Path) -> list[dict]:
    rows = []
    for p in sorted(root.rglob('*'), key=lambda q: q.relative_to(root).as_posix()):
        if p.is_file():
            rel = p.relative_to(root).as_posix()
            rows.append({'path': rel, 'bytes': p.stat().st_size, 'sha1': sha1_file(p)})
    return rows


def read_manifest() -> dict | None:
    if not MANIFEST.exists():
        return None
    return json.loads(MANIFEST.read_text(encoding='utf-8'))


def write_manifest(m: dict) -> None:
    tmp = MANIFEST.with_suffix('.json.tmp')
    tmp.write_text(json.dumps(m, indent=2, ensure_ascii=False) + '\n', encoding='utf-8', newline='\n')
    os.replace(tmp, MANIFEST)


def verify(manifest: dict, root: Path = TARGET) -> list[str]:
    """Problems of the extracted folder against the manifest (empty: it matches)."""
    problems = []
    if not root.is_dir():
        return [f'{root} does not exist: run npm run vendor:libredwg -- --zip <the release zip>']
    want = {f['path']: f for f in manifest['files']}
    lic = manifest.get('licence') or {}
    if lic.get('sha1'):
        want[lic['path']] = {'path': lic['path'], 'bytes': lic['bytes'], 'sha1': lic['sha1']}
    have = {f['path']: f for f in list_files(root)}
    for path, f in want.items():
        h = have.get(path)
        if h is None:
            problems.append(f'missing: {path}')
        elif h['bytes'] != f['bytes'] or h['sha1'] != f['sha1']:
            problems.append(f'differs: {path} ({h["bytes"]} B {h["sha1"][:12]}, manifest {f["bytes"]} B {f["sha1"][:12]})')
    for path in have:
        if path not in want and not (path == LICENCE_NAME and not lic.get('sha1')):
            problems.append(f'not in the manifest: {path}')
    return problems


def extract(zip_path: Path) -> None:
    with zipfile.ZipFile(zip_path) as z:
        infos = z.infolist()
        if len(infos) != ZIP_ENTRIES:
            raise SystemExit(f'vendor-libredwg: the zip has {len(infos)} entries, expected {ZIP_ENTRIES}')
        staging = VENDOR / (RELEASE + '.extracting')
        if staging.exists():
            shutil.rmtree(staging)
        staging.mkdir(parents=True)
        for info in infos:
            rel = safe_name(info.filename)
            dest = staging.joinpath(*rel.parts)
            if info.is_dir():
                dest.mkdir(parents=True, exist_ok=True)
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            with z.open(info) as src, open(dest, 'wb') as out:
                shutil.copyfileobj(src, out, 1 << 20)
    # keep a COPYING the owner added, then swap the folder in
    old_licence = TARGET / LICENCE_NAME
    if old_licence.exists():
        shutil.copy2(old_licence, staging / LICENCE_NAME)
    if TARGET.exists():
        shutil.rmtree(TARGET)
    os.replace(staging, TARGET)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--zip', help='the release zip to copy in (default: vendor/libredwg-0.14-win64.zip)')
    ap.add_argument('--verify', action='store_true', help='only check the extracted folder against the manifest')
    ap.add_argument('--add-licence', help='the GPL-3.0 text to copy in as COPYING (its sha1 goes into the manifest)')
    a = ap.parse_args()

    manifest = read_manifest()
    if a.verify:
        if manifest is None:
            print(f'vendor-libredwg: no manifest at {MANIFEST}', file=sys.stderr)
            return 1
        problems = verify(manifest)
        for p in problems:
            print(f'vendor-libredwg: {p}', file=sys.stderr)
        if problems:
            return 1
        print(f'vendor-libredwg: ok ({len(manifest["files"])} files equal the manifest)')
        return 0

    if a.add_licence:
        if manifest is None:
            print('vendor-libredwg: extract first (no manifest yet)', file=sys.stderr)
            return 1
        src = Path(a.add_licence)
        dst = TARGET / LICENCE_NAME
        shutil.copyfile(src, dst)
        manifest['licence'] = {'path': LICENCE_NAME, 'bytes': dst.stat().st_size, 'sha1': sha1_file(dst),
                               'note': 'GPL-3.0 text fetched by the owner (gnu.org); not in the release zip'}
        write_manifest(manifest)
        print(f'vendor-libredwg: {dst} recorded ({manifest["licence"]["sha1"]})')
        return 0

    VENDOR.mkdir(parents=True, exist_ok=True)
    local_zip = VENDOR / ZIP_NAME
    if a.zip:
        src = Path(a.zip)
        if not src.is_file():
            print(f'vendor-libredwg: the zip {src} is gone: re-download the GitHub release {RELEASE} (network) and '
                  f'pass it with --zip', file=sys.stderr)
            return 1
        if src.resolve() != local_zip.resolve():
            shutil.copyfile(src, local_zip)
    if not local_zip.is_file():
        print(f'vendor-libredwg: no {local_zip}: pass the release zip with --zip', file=sys.stderr)
        return 1
    got = sha1_file(local_zip)
    if got != ZIP_SHA1:
        print(f'vendor-libredwg: {local_zip} has sha1 {got}, expected {ZIP_SHA1}: not the 0.14 win64 release',
              file=sys.stderr)
        return 1
    extract(local_zip)

    files = [f for f in list_files(TARGET) if f['path'] != LICENCE_NAME]
    if manifest is None:
        lic = None
        if (TARGET / LICENCE_NAME).exists():
            d = TARGET / LICENCE_NAME
            lic = {'path': LICENCE_NAME, 'bytes': d.stat().st_size, 'sha1': sha1_file(d)}
        manifest = {
            'format': 'vendor-manifest/1',
            'name': 'LibreDWG',
            'release': '0.14 (win64 build, GitHub release libredwg-0.14-win64.zip)',
            'licence': lic or {'path': LICENCE_NAME, 'bytes': None, 'sha1': None,
                               'note': 'GPL-3.0-or-later (README.txt); the zip has no COPYING: the owner fetches the '
                                       'text from gnu.org and runs --add-licence'},
            'zip': {'path': 'vendor/' + ZIP_NAME, 'bytes': local_zip.stat().st_size, 'sha1': got,
                    'entries': ZIP_ENTRIES},
            'folder': 'vendor/' + RELEASE,
            'files': files,
        }
        write_manifest(manifest)
        print(f'vendor-libredwg: extracted {ZIP_ENTRIES} entries ({len(files)} files); manifest written')
        return 0
    problems = verify(manifest)
    for p in problems:
        print(f'vendor-libredwg: {p}', file=sys.stderr)
    if problems:
        return 1
    print(f'vendor-libredwg: extracted {ZIP_ENTRIES} entries; {len(files)} files equal the manifest')
    return 0


if __name__ == '__main__':
    sys.exit(main())
