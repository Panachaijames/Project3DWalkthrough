"""The prototype chain, run in a scratch copy, as the oracle for the upload milestone (WORK_BREAKDOWN U0 step 4;
docs/upload/DESIGN.md U-0, U-7.1, U-8.2; ACCEPTANCE 2.1).

    node tools/run-builder-py.mjs tools/upload/make-reference.py --out <dir> [--only bank|house|suite|tower ...]
    npm run make:reference -- --out %TEMP%\\wt-u0\\ref

Copies into <dir>/proj/ exactly the prototype files the chain needs (as docs/upload/reference/bank_chain.ps1 did:
detector/{openings.py, geomkit.py, tools/prims.py, mappings/, mappings_with_areas/, sukhumvit/regions.json},
bank_test/src/{build_model.py, plan_items.py, bank_project.json, generate_maxscript.py}, cad_test/src/merge_cad.py,
presidential_test/src/geom.py, furniture/{furniture_kit.py, furniture_max.py}), then inside the copy only:
  1. converts each DWG with the vendored LibreDWG (app/vendor/libredwg-0.14-win64/dwg2dxf.exe; the DWG copied in as
     input.dwg, as U-6.2 does) into proj/detector/<name>/plan.dxf (stdout / stderr in <dir>/logs/);
  2. runs prims.py <name> with OPENINGS_DATA=<dir>/proj/detector -> proj/detector/<name>/prims.pkl;
  3. runs the detector with the mapping that made detector/output/ (mappings_with_areas/{bank1, bank2, sukhumvit,
     presidential}.json, mappings/{l29, l30}.json) -> proj/detector/output/<name>_openings.json and _log.txt;
  4. for the bank: copies the two detector outputs to bank_test/src/detector_out/openings_L{1,2}.json, runs the bank's
     build_model.py and generate_maxscript.py (-> bank_test/Bangkok_Bank_Sampeng.ms);
  5. writes <dir>/manifest.json (sha1 and size of every output; per drawing the DWG, the DXF, seconds, item counts;
     the checks) and checks: the bank's model, stages, CSV, top view and .ms equal v2's (U-0's sha1s); the DXFs equal
     the 26 Oct conversions; each detector output equals detector/output/<name>_openings.json; the prototype folders'
     listing (outside app/, sizes and times) is unchanged. Exit 1 when a check fails.

Names: bank1, bank2 (I1201 / I1202), sukhumvit (the house), presidential (the suite), l29, l30 (the tower); --only takes
the groups bank (bank1 + bank2 + the build), house, suite, tower, or the names themselves. A run with --only updates
those entries of an existing manifest. Every prototype script runs with the builder Python and -B, cwd inside the
copy; nothing is written outside <dir>. It holds the machine run lock (U-3.5) while it converts and reads.
WT_REF (default %TEMP%\\wt-u0\\ref) is the scaffold's run of this: shared and read-only for every builder.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

APP = Path(__file__).resolve().parents[2]
PROJECT = APP.parent
sys.path.insert(0, str(APP / 'services' / 'builder'))
from walkthrough_builder import oslock  # noqa: E402

DWG2DXF = APP / 'vendor' / 'libredwg-0.14-win64' / 'dwg2dxf.exe'

#: name -> (DWG in the project folder, the mapping (relative to detector/) that made detector/output/<name>_openings.json)
DRAWINGS: dict[str, tuple[str, str]] = {
    'bank1': ('I1201 - LEVEL 1 GENERAL ARRANGEMENT.dwg', 'mappings_with_areas/bank1.json'),
    'bank2': ('I1202 - LEVEL 2 GENERAL ARRANGEMENT.dwg', 'mappings_with_areas/bank2.json'),
    'sukhumvit': ('Test Sukhumvit Residence.dwg', 'mappings_with_areas/sukhumvit.json'),
    'presidential': ('layout presidential test.dwg', 'mappings_with_areas/presidential.json'),
    'l29': ('L29.dwg', 'mappings/l29.json'),
    'l30': ('L30.dwg', 'mappings/l30.json'),
}
GROUPS: dict[str, list[str]] = {'bank': ['bank1', 'bank2'], 'house': ['sukhumvit'], 'suite': ['presidential'],
                                'tower': ['l29', 'l30']}

#: The prototype files the chain needs, relative to the project folder (copied to <dir>/proj/ at the same paths).
CODE = [
    'detector/openings.py', 'detector/geomkit.py', 'detector/tools/prims.py', 'detector/sukhumvit/regions.json',
    'bank_test/src/build_model.py', 'bank_test/src/plan_items.py', 'bank_test/src/bank_project.json',
    'bank_test/src/generate_maxscript.py', 'cad_test/src/merge_cad.py', 'presidential_test/src/geom.py',
    'furniture/furniture_kit.py', 'furniture/furniture_max.py',
]
CODE_DIRS = ['detector/mappings', 'detector/mappings_with_areas']

#: v2's bytes (U-0; ACCEPTANCE A-1): output in the copy -> (the prototype's file, its sha1)
BANK_GOLDEN = {
    'bank_test/src/bank_model.json': ('bank_test/src/bank_model.json', 'c3a9408304a240b83c36f5c5c53db56b50a72c64'),
    'bank_test/src/bank_stages.json': ('bank_test/src/bank_stages.json', 'c7c01b67e97335ea3103179175534af919ae4aa8'),
    'bank_test/bank_furniture_list.csv': ('bank_test/bank_furniture_list.csv', 'b528bb2320ef4a5e04ad3c1ad1e04ee09af67861'),
    'bank_test/src/bank_topview.png': ('bank_test/src/bank_topview.png', 'f084b556503c4d5959e02d1dd55e84c607800775'),
    'bank_test/Bangkok_Bank_Sampeng.ms': ('bank_test/Bangkok_Bank_Sampeng.ms', '615d50137bdbe12d3f473cdcdc39cc09aca588e4'),
}
#: the 26 Oct conversions (U-0)
DXF_GOLDEN = {'bank1': ('9167d084f7e311b59e7c2cdb2bae8506d96a4cfa', 2817940),
              'bank2': ('c88491df', 7923920)}


def sha1_file(p: Path) -> str:
    h = hashlib.sha1()
    with open(p, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def listing(root: Path) -> dict[str, tuple[int, int]]:
    """Every file outside app/ and .git/: relative path -> (bytes, mtime ns)."""
    out = {}
    for dirpath, dirnames, filenames in os.walk(root):
        rel = Path(dirpath).relative_to(root).as_posix()
        if rel == '.':
            dirnames[:] = [d for d in dirnames if d not in ('app', '.git')]
        for fn in filenames:
            p = Path(dirpath) / fn
            st = p.stat()
            out[p.relative_to(root).as_posix()] = (st.st_size, st.st_mtime_ns)
    return out


def run(cmd: list[str], cwd: Path, env: dict, out_path: Path, err_path: Path | None, timeout: float) -> float:
    t0 = time.perf_counter()
    with open(out_path, 'wb') as fo, open(err_path or os.devnull, 'wb') as fe:
        r = subprocess.run(cmd, cwd=cwd, env=env, stdin=subprocess.DEVNULL, stdout=fo,
                           stderr=fe if err_path else subprocess.STDOUT, timeout=timeout,
                           creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    secs = time.perf_counter() - t0
    if r.returncode != 0:
        tail = out_path.read_text(encoding='utf-8', errors='replace')[-2000:]
        raise SystemExit(f'make-reference: {" ".join(cmd[1:3])} stopped with exit {r.returncode} (see {out_path}):\n{tail}')
    return secs


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--out', required=True, help='the reference folder (e.g. %%TEMP%%\\wt-u0\\ref)')
    ap.add_argument('--only', nargs='+', help='groups (bank, house, suite, tower) or names (bank1 ... l30)')
    a = ap.parse_args()

    names: list[str] = []
    for x in (a.only or list(GROUPS)):
        for n in GROUPS.get(x, [x]):
            if n not in DRAWINGS:
                print(f'make-reference: unknown drawing {x!r} (groups {", ".join(GROUPS)}; names {", ".join(DRAWINGS)})',
                      file=sys.stderr)
                return 2
            if n not in names:
                names.append(n)
    with_bank = 'bank1' in names and 'bank2' in names

    out = Path(a.out).resolve()
    if out == APP or APP in out.parents or out == PROJECT or (PROJECT in out.parents and APP not in out.parents):
        print(f'make-reference: --out {out} lies in the project folder: use a temp folder', file=sys.stderr)
        return 2
    if not DWG2DXF.exists():
        print(f'make-reference: no {DWG2DXF}: run npm run vendor:libredwg first', file=sys.stderr)
        return 1
    proj = out / 'proj'
    logs = out / 'logs'
    det = proj / 'detector'
    logs.mkdir(parents=True, exist_ok=True)
    (det / 'output').mkdir(parents=True, exist_ok=True)

    before = listing(PROJECT)
    # 0. the prototype code the chain needs (always copied again: small)
    for rel in CODE:
        dst = proj / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(PROJECT / rel, dst)
    for rel in CODE_DIRS:
        dst = proj / rel
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(PROJECT / rel, dst)
    (proj / 'bank_test' / 'src' / 'detector_out').mkdir(parents=True, exist_ok=True)

    py = sys.executable
    env = dict(os.environ, PYTHONIOENCODING='utf-8', PYTHONUTF8='1', PYTHONDONTWRITEBYTECODE='1', MPLBACKEND='Agg',
               OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1', OPENINGS_DATA=str(det))
    env.pop('PYTHONNOUSERSITE', None)

    man_path = out / 'manifest.json'
    manifest = json.loads(man_path.read_text(encoding='utf-8')) if man_path.exists() else {}
    manifest.setdefault('format', 'reference-manifest/1')
    manifest.setdefault('drawings', {})
    manifest.setdefault('outputs', {})
    checks: list[dict] = []

    def check(name: str, ok: bool, detail: str) -> None:
        checks.append({'name': name, 'ok': bool(ok), 'detail': detail})
        print(f'  {"ok  " if ok else "FAIL"} {name}: {detail}', flush=True)

    t_all = time.perf_counter()

    def waiting(secs: float) -> None:
        print(f'make-reference: waiting for the machine run lock (another build or heavy test holds it, {secs:.0f} s)',
              flush=True)

    with oslock.hold(wait=waiting):
        for n in names:
            dwg_name, mapping = DRAWINGS[n]
            dwg = PROJECT / dwg_name
            folder = det / n
            if folder.exists():
                for p in folder.iterdir():
                    if p.name != 'regions.json':
                        p.unlink()
            folder.mkdir(parents=True, exist_ok=True)
            print(f'{n}: {dwg_name}', flush=True)
            rec: dict = {'dwg': dwg_name, 'dwgBytes': dwg.stat().st_size, 'dwgSha1': sha1_file(dwg), 'mapping': mapping,
                         'seconds': {}}
            # 1. convert (the DWG copied in as input.dwg, U-6.2)
            shutil.copyfile(dwg, folder / 'input.dwg')
            rec['seconds']['convert'] = round(run([str(DWG2DXF), '-y', '-o', 'plan.dxf', 'input.dwg'], folder, env,
                                                  logs / f'{n}.dwg2dxf.out.txt', logs / f'{n}.dwg2dxf.err.txt', 600), 2)
            (folder / 'input.dwg').unlink()
            dxf = folder / 'plan.dxf'
            rec['dxfSha1'], rec['dxfBytes'] = sha1_file(dxf), dxf.stat().st_size
            if n in DXF_GOLDEN:
                want, size = DXF_GOLDEN[n]
                check(f'{n} DXF', rec['dxfSha1'].startswith(want) and rec['dxfBytes'] == size,
                      f'{rec["dxfSha1"][:12]} {rec["dxfBytes"]} B (26 Oct: {want[:8]}... {size} B)')
            # 2. prims
            rec['seconds']['prims'] = round(run([py, '-B', 'detector/tools/prims.py', n], proj, env,
                                                logs / f'{n}.prims.txt', None, 1200), 2)
            # 3. detector, with the mapping that made detector/output/
            rec['seconds']['detector'] = round(run([py, '-B', 'openings.py', mapping, f'output/{n}_openings.json'], det,
                                                   env, det / 'output' / f'{n}_log.txt', None, 1200), 2)
            mine = json.loads((det / 'output' / f'{n}_openings.json').read_text(encoding='utf-8'))['openings']
            oracle = json.loads((PROJECT / 'detector' / 'output' / f'{n}_openings.json').read_text(encoding='utf-8'))['openings']
            rec['detector'] = {'records': len(mine), 'oracleRecords': len(oracle), 'equal': mine == oracle}
            check(f'{n} openings', mine == oracle, f'{len(mine)} records, detector/output/{n}_openings.json has {len(oracle)}')
            import pickle
            with open(folder / 'prims.pkl', 'rb') as f:
                D = pickle.load(f)
            rec['items'] = len(D['items'])
            rec['itemsInArea'] = sum(1 for d in D['items'] if d.get('area'))
            rec['layers'] = len(D['layers'])
            del D
            manifest['drawings'][n] = rec

        if with_bank:
            print('bank: build_model.py, generate_maxscript.py', flush=True)
            for n, key in (('bank1', 'L1'), ('bank2', 'L2')):
                shutil.copyfile(det / 'output' / f'{n}_openings.json',
                                proj / 'bank_test' / 'src' / 'detector_out' / f'openings_{key}.json')
            bank = {'seconds': {}}
            bank['seconds']['build'] = round(run([py, '-B', 'bank_test/src/build_model.py'], proj, env,
                                                 logs / 'bank.build_model.txt', None, 1200), 2)
            bank['seconds']['maxscript'] = round(run([py, '-B', 'bank_test/src/generate_maxscript.py',
                                                      'bank_test/Bangkok_Bank_Sampeng.ms'], proj, env,
                                                     logs / 'bank.generate_maxscript.txt', None, 600), 2)
            for rel, (proto, want) in BANK_GOLDEN.items():
                got = sha1_file(proj / rel)
                bank.setdefault('sha1', {})[rel] = got
                check(f'bank {Path(rel).name}', got == want == sha1_file(PROJECT / proto),
                      f'{got[:12]} (v2 {want[:12]})')
            manifest['bank'] = bank

    after = listing(PROJECT)
    changed = sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))
    check('prototype folders unchanged', not changed, f'{len(after)} files outside app/'
          + (f'; changed: {", ".join(changed[:10])}' if changed else ''))

    # the manifest: every output of the copy
    outputs = {}
    for p in sorted(out.rglob('*')):
        if p.is_file() and p.name != 'manifest.json':
            rel = p.relative_to(out).as_posix()
            outputs[rel] = {'bytes': p.stat().st_size, 'sha1': sha1_file(p)}
    manifest['outputs'] = outputs
    manifest['madeAt'] = datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%SZ')
    manifest['python'] = {'executable': sys.executable, 'version': sys.version.split()[0]}
    manifest['libredwg'] = json.loads((APP / 'vendor' / 'libredwg.manifest.json').read_text(encoding='utf-8'))['zip']
    prev = [c for c in manifest.get('checks', []) if not any(c['name'] == d['name'] for d in checks)]
    manifest['checks'] = prev + checks
    manifest['lastRun'] = {'only': names, 'seconds': round(time.perf_counter() - t_all, 1)}
    man_path.write_text(json.dumps(manifest, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    failed = [c for c in checks if not c['ok']]
    print(f'make-reference: {len(checks) - len(failed)} of {len(checks)} checks pass; {time.perf_counter() - t_all:.0f} s '
          f'-> {man_path}')
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
