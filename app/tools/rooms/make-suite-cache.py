"""The reader cache of one drawing, made with the app's own converter and reader in the cache layout of U-4.2
(docs/rooms/WORK_BREAKDOWN.md R0 item 9). Scaffold R0.

    node tools/run-builder-py.mjs tools/rooms/make-suite-cache.py --out <cache root> [--dwg <file>] [--compare <root>]

Default drawing: the project folder's `presidential suite_layout.dwg` (the new suite, the fifth drawing); default
cache root: %TEMP%\\wt-r0\\ref\\suite-revit. It writes

    <root>/<source sha1>/libredwg-0.14/plan.dxf + convert.log + conversion.json + .done
    <root>/<source sha1>/read-1-<units>/items.pkl + drawing.json + plan.json.gz + .done
    <root>/<source sha1>/read-1-auto.json
    <root>/manifest.json            { name, sha1, units, read: <folder>, itemsSha1, dxfSha1, seconds }

exactly as the worker's prepare run does (job.py do_convert, do_check, ensure_read), in this process, holding the
machine run lock. An entry that is already complete is kept (the cache's own rule). `--compare <root>` checks that
items.pkl and plan.dxf equal another cache's entry for the same source (the upload acceptance store's cache) and exits
1 when they differ. Nothing is written outside <root>.
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

APP = Path(__file__).resolve().parents[2]
PROJECT = APP.parent
sys.path.insert(0, str(APP / 'services' / 'builder'))
sys.dont_write_bytecode = True

from walkthrough_builder import cache, contracts, convert, jsonfile, losscheck, oslock  # noqa: E402

LIBREDWG = APP / 'vendor' / 'libredwg-0.14-win64'
DEFAULT_DWG = PROJECT / 'presidential suite_layout.dwg'
DEFAULT_OUT = Path(os.environ.get('TEMP') or tempfile.gettempdir()) / 'wt-r0' / 'ref' / 'suite-revit'


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=str(DEFAULT_OUT))
    ap.add_argument('--dwg', default=str(DEFAULT_DWG))
    ap.add_argument('--compare', default=None)
    a = ap.parse_args()
    dwg, root = Path(a.dwg), Path(a.out)
    if not dwg.is_file():
        print(f'no drawing at {dwg}', file=sys.stderr)
        return 1
    if not (LIBREDWG / 'dwg2dxf.exe').is_file():
        print(f'LibreDWG is not extracted at {LIBREDWG}: npm run vendor:libredwg', file=sys.stderr)
        return 1
    root.mkdir(parents=True, exist_ok=True)
    sha = cache.sha1_file(dwg)
    t0 = time.perf_counter()
    info = convert.converter_info(LIBREDWG)
    folder = cache.converter_folder(info['version'])
    say = lambda s: print(s, flush=True)  # noqa: E731

    with oslock.hold(wait=lambda secs: say(f'waiting for the machine run lock ({secs:.0f} s)') if int(secs) % 30 == 0 else None):
        conv = cache.conversion_entry(root, sha, folder)
        if conv is None:
            work = root / '.work'
            shutil.rmtree(work, ignore_errors=True)
            res = convert.convert(dwg, work, libredwg=LIBREDWG, seconds=300, memory_mb=2048)
            if res['code']:
                print(f'the conversion failed: {res["code"]} {res["detail"]}', file=sys.stderr)
                return 1
            aud = convert.audit(Path(res['dxf']))
            src = {'sha1': sha, 'name': dwg.name, 'bytes': dwg.stat().st_size, 'kind': 'dwg',
                   'formatVersion': convert.check_header(dwg)}
            rep = losscheck.check(work / 'input.dwg', Path(res['dxf']), Path(res['log']), libredwg=LIBREDWG, source=src,
                                  converter=info, convert={'seconds': res['seconds'], 'peak_mb': res['peak_mb'],
                                                           'exit_code': res['exit_code']}, audit=aud, log=say)
            jsonfile.write(work / 'conversion.json', rep)
            conv = cache.commit_conversion(root, sha, folder, {'plan.dxf': work / 'plan.dxf',
                                                               'convert.log': work / 'convert.log',
                                                               'conversion.json': work / 'conversion.json'}, 'r0')
            shutil.rmtree(work, ignore_errors=True)
            say(f'converted {dwg.name}: verdict {rep["verdict"]}, {rep["totals"]["missing"]} items missing')
        else:
            say(f'conversion: cache hit {conv}')
        read = cache.read_entry(root, sha, None)
        if read is None:
            staging = cache.read_staging(root, sha, 'r0')
            got = contracts.read_source(conv / 'plan.dxf', None, staging, source={'sha1': sha, 'name': dwg.name}, log=say)
            read = cache.commit_read(root, sha, staging, got['units']['used'], auto=True)
        else:
            say(f'read: cache hit {read}')

    units = jsonfile.read(read / 'drawing.json')['units']['used']
    manifest = {'name': dwg.name, 'sha1': sha, 'units': units, 'read': read.name,
                'itemsSha1': cache.sha1_file(read / 'items.pkl'), 'dxfSha1': cache.sha1_file(conv / 'plan.dxf'),
                'seconds': round(time.perf_counter() - t0, 1)}
    jsonfile.write(root / 'manifest.json', manifest)
    say(f'{root}: {manifest}')
    if a.compare:
        other = Path(a.compare) / sha
        bad = []
        for mine, theirs in ((conv / 'plan.dxf', other / folder / 'plan.dxf'),
                             (read / 'items.pkl', other / read.name / 'items.pkl'),
                             (read / 'plan.json.gz', other / read.name / 'plan.json.gz')):
            if not theirs.is_file():
                bad.append(f'missing {theirs}')
            elif cache.sha1_file(mine) != cache.sha1_file(theirs):
                bad.append(f'different {mine.name}')
        say(f'compared with {other}: ' + ('equal (plan.dxf, items.pkl, plan.json.gz)' if not bad else '; '.join(bad)))
        return 1 if bad else 0
    return 0


if __name__ == '__main__':
    sys.exit(main())
