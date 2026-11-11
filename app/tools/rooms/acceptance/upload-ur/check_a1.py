"""ACCEPTANCE A-1 checks on the recorded cases bank-reupload (a) and bank-v3 (b) (step UI).

    python -B check_a1.py <acc out dir> <store> <cache>     (system or builder Python; runs the Max CLI through node)
"""
from __future__ import annotations

import datetime as dt
import difflib
import hashlib
import json
import subprocess
import sys
from pathlib import Path

PROJECT = Path(r'C:\Users\DWP2\Desktop\Project walkthrough')
APP = PROJECT / 'app'
V2 = APP / 'data' / 'projects' / 'bank-sampeng' / 'versions' / '2'


def sha1(b: bytes) -> str:
    return hashlib.sha1(b).hexdigest()


def load(p):
    return json.loads(Path(p).read_bytes())


def max_cli(model: Path, out: Path, *args: str) -> bytes:
    r = subprocess.run(['node', 'tools/run-builder-py.mjs', '-m', 'walkthrough_builder.out', str(model), *args,
                        '--out', str(out)], cwd=APP, capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(r.stderr or r.stdout)
    return out.read_bytes()


def no_floor(recs):
    return [{k: v for k, v in r.items() if k != 'floor'} for r in recs]


def check(case_dir: Path, store: Path, cache: Path, work: Path) -> dict:
    rec = load(case_dir / 'record.json')
    res: dict = {'case': rec['case'], 'ok': rec.get('ok'), 'error': rec.get('error')}
    if not rec.get('ok'):
        return res
    pid, n = rec['project'], rec['save']['version']
    vdir = store / 'projects' / pid / 'versions' / str(n)
    # the two DXFs in the cache
    res['dxf'] = {}
    for u in rec['uploads']:
        d = cache / u['sha1'] / 'libredwg-0.14' / 'plan.dxf'
        res['dxf'][u['name']] = {'sha1': sha1(d.read_bytes()) if d.is_file() else None, 'bytes': d.stat().st_size if d.is_file() else None}
    # conversion verdicts and message classes
    res['conversion'] = {}
    for u in rec['uploads']:
        c = load(case_dir / 'prepare' / f'{u["sha1"][:12]}.conversion.json')
        res['conversion'][u['name']] = {'verdict': c['verdict'], 'missing': c['totals']['missing'],
                                         'messages': {m['class']: m['count'] for m in c['messages']}, 'notes': c['notes']}
    # model, CSV, stamp
    model = (case_dir / 'version' / 'model.json').read_bytes()
    res['modelSha1'] = sha1(model)
    res['stamp'] = rec['save']['stamp']
    csv = (case_dir / 'version' / 'furniture.csv').read_bytes()
    res['csvSha1'] = sha1(csv)
    res['csvEqualsV2'] = csv == (APP / 'fixtures' / 'csv' / 'bank-v2.csv').read_bytes()
    # openings: the version's source/openings.json against detector/output, floor removed on both sides
    of = load(vdir / 'source' / 'openings.json')
    res['openings'] = {}
    for fl, name in (('L1', 'bank1'), ('L2', 'bank2')):
        mine = no_floor([r['record'] for r in of['floors'][fl]])
        oracle = no_floor(load(PROJECT / 'detector' / 'output' / f'{name}_openings.json')['openings'])
        res['openings'][fl] = {'records': len(mine), 'oracle': len(oracle), 'equal': mine == oracle,
                               'ids': [r['id'] for r in mine] == [r['id'] for r in oracle]}
    # the Max generator with the bank-27oct profile on this model
    ms27 = max_cli(case_dir / 'version' / 'model.json', work / f'{rec["case"]}.bank-27oct.ms', '--profile', 'bank-27oct')
    golden = (PROJECT / 'bank_test' / 'Bangkok_Bank_Sampeng.ms').read_bytes()
    res['max27'] = {'sha1': sha1(ms27), 'equalsPrototype': ms27 == golden, 'lines': ms27.count(b'\r\n')}
    # the version's own .ms: the upload profile with the build's date
    ver_ms = (case_dir / 'version' / 'version.ms').read_bytes()
    inputs = load(vdir / 'source' / 'inputs.json')
    built = dt.datetime.fromisoformat(inputs['builtAt'].replace('Z', '+00:00')).astimezone()
    date = f'{built.day} {built.strftime("%b %Y")}'
    exp = max_cli(case_dir / 'version' / 'model.json', work / f'{rec["case"]}.upload.ms', '--profile', 'upload', '--date',
                  date, '--sources', 'dwg:mm,dwg:mm', '--converter-version', '0.14')
    lines27, linesv = ms27.decode('ascii').split('\r\n'), ver_ms.decode('ascii').split('\r\n')
    diff = [l for l in difflib.unified_diff(lines27, linesv, lineterm='', n=0) if l[:1] in '+-' and l[:3] not in ('---', '+++')]
    res['versionMs'] = {'equalsGenerated': ver_ms == exp, 'date': date, 'line2': linesv[1], 'crlf': ver_ms.count(b'\r\n') == ver_ms.count(b'\n'),
                        'linesDifferingFromBankProfile': len(diff), 'diff': diff}
    # stages against v2's
    st, s2 = load(case_dir / 'version' / 'stages.json'), load(V2 / 'stages.json')
    res['stages'] = {f'floors.{k}.{f}': st['floors'][k][f] == s2['floors'][k][f]
                     for k in s2['floors'] for f in ('lines', 'rings', 'sheet')}
    res['stages'].update({f'source.{f}': st['source'].get(f) == s2['source'].get(f) for f in ('files', 'layersInUse', 'units')})
    # top view
    tv = (vdir / 'assets' / 'topview.png').read_bytes()
    res['topview'] = {'sha1': sha1(tv), 'equalsV2': tv == (V2 / 'assets' / 'topview.png').read_bytes()}
    # times
    res['times'] = {'prepareWall': rec['prepare']['wall'], 'prepareQueued': rec['prepare'].get('queuedSeconds'),
                    'prepareSteps': {s['name']: s['seconds'] for s in rec['prepare']['run']['steps']},
                    'buildWall': rec['build1']['wall'], 'buildSteps': {s['name']: s['seconds'] for s in rec['build1']['run']['steps']}}
    return res


def main() -> int:
    out, store, cache = map(Path, sys.argv[1:4])
    work = out / '_a1'
    work.mkdir(exist_ok=True)
    allres = [check(out / c, store, cache, work) for c in ('bank-reupload', 'bank-v3')]
    (work / 'a1.json').write_text(json.dumps(allres, indent=1, ensure_ascii=False), encoding='utf-8')
    for r in allres:
        print(json.dumps({k: v for k, v in r.items() if k != 'versionMs'}, ensure_ascii=False)[:3000])
        if 'versionMs' in r:
            print(json.dumps({k: v for k, v in r['versionMs'].items() if k != 'diff'}))
    return 0


if __name__ == '__main__':
    sys.exit(main())
