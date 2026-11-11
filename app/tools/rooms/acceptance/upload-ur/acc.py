"""Acceptance driver of the integration step UI (docs/upload/ACCEPTANCE.md): runs one case through a SERVED API (the real
LocalJobRunner and worker) and records everything it sees into <out>/<case name>/.

    node tools/run-py.mjs <this file> --base http://127.0.0.1:8739 --store <data dir> --out <dir> <case.json> ...

A case:
  name, project (id), create (NewProjectRequest or null: the project exists), files (paths, relative to the project
  folder or absolute), from (NewBuildRequest.from or null), settings: {"fixture": "bank"} | {"proposal": true} |
  {"file": path}, edit (a .py file with edit(settings, build) -> settings, applied last), acceptOutlines (bool: a second
  build with every outline suggestion accepted), fixes (a .py file with fixes(settings, build, overlay, plans) ->
  settings, then a rebuild), save ({label, carryHeights, rememberMapping} or null).
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import importlib.util
import json
import shutil
import sys
import time
from pathlib import Path

import httpx

PROJECT = Path(r'C:\Users\DWP2\Desktop\Project walkthrough')
APP = PROJECT / 'app'
FX = APP / 'fixtures' / 'upload'


def sha1(b: bytes) -> str:
    return hashlib.sha1(b).hexdigest()


def load(p) -> object:
    return json.loads(Path(p).read_bytes())


def dump(p: Path, obj) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=1, ensure_ascii=False), encoding='utf-8')


def module(path: str):
    spec = importlib.util.spec_from_file_location(Path(path).stem, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class Api:
    def __init__(self, base: str) -> None:
        self.c = httpx.Client(base_url=base, timeout=900)

    def req(self, method: str, url: str, ok=(200, 201, 202, 204), **kw) -> httpx.Response:
        r = self.c.request(method, url, **kw)
        if r.status_code not in ok:
            raise RuntimeError(f'{method} {url} -> {r.status_code}: {r.text[:800]}')
        return r

    def get(self, url, **kw):
        return self.req('GET', url, **kw)

    def post(self, url, **kw):
        return self.req('POST', url, **kw)

    def put(self, url, **kw):
        return self.req('PUT', url, **kw)


def wait(api: Api, url: str, rec: dict, timeout: float = 3600) -> dict:
    """Polls the build (withSettings=false) until its run ends; then the full detail (which adopts / validates)."""
    t0 = time.monotonic()
    seen_running = None
    while True:
        d = api.get(url, params={'withSettings': 'false'}).json()
        st = (d.get('run') or {}).get('status')
        if st == 'running' and seen_running is None:
            seen_running = time.monotonic() - t0
        if st not in ('queued', 'running'):
            break
        if time.monotonic() - t0 > timeout:
            raise RuntimeError(f'still {st} after {timeout} s')
        time.sleep(0.5)
    rec['pollSeconds'] = round(time.monotonic() - t0, 2)
    rec['queuedSeconds'] = round(seen_running, 2) if seen_running is not None else None
    return api.get(url).json()


def copy_runs(store: Path, project: str, build: str, out: Path) -> None:
    runs = store / 'projects' / project / 'builds' / build / 'runs'
    if not runs.is_dir():
        return
    for run in sorted(runs.iterdir()):
        for name in ('job.json', 'log.txt', 'api.json', 'launch.json', 'spec.json'):
            p = run / name
            if p.is_file():
                (out / 'runs' / run.name).mkdir(parents=True, exist_ok=True)
                shutil.copy2(p, out / 'runs' / run.name / name)


def upload(api: Api, project: str, path: Path) -> dict:
    data = path.read_bytes()
    t = time.monotonic()
    s = api.post('/api/uploads', json={'projectId': project, 'fileName': path.name, 'bytes': len(data)}).json()
    step = s['partBytes']
    for i, url in enumerate(s['partUrls']):
        api.put(url, content=data[i * step:(i + 1) * step], headers={'content-type': 'application/octet-stream'})
    src = api.post(s['completeUrl'], json={}).json()
    return {'name': path.name, 'bytes': len(data), 'parts': len(s['partUrls']), 'seconds': round(time.monotonic() - t, 2),
            'sha1': src['sha1'], 'kind': src['kind'], 'formatVersion': src.get('formatVersion'),
            'fileSha1': sha1(data)}


def settings_for(case: dict, b: dict) -> dict:
    spec = case.get('settings') or {'proposal': True}
    if 'fixture' in spec:
        s = load(FX / 'settings' / f'{spec["fixture"]}.json')
        by_name = {src['name']: src for src in b['settings']['sources']}
        mine = [src['sha1'] for src in b['settings']['sources']]
        theirs = [src['sha1'] for src in s['sources']]
        if sorted(mine) != sorted(theirs):
            raise RuntimeError(f'fixture sources {theirs} are not the build\'s {mine} ({list(by_name)})')
        if spec.get('keepProject'):
            s['project'] = b['settings']['project']
        if spec.get('keepOffice', True) and b['settings'].get('office') and not s.get('office'):
            s['office'] = b['settings']['office']
    elif 'file' in spec:
        s = load(spec['file'])
    else:
        s = json.loads(json.dumps(b['settings']))
    if case.get('edit'):
        s = module(case['edit']).edit(s, b)
    return s


def download_result(api: Api, b: dict, out: Path, tag: str) -> dict:
    res = b['result'] or {}
    got = {}
    for k, url in (res.get('urls') or {}).items():
        r = api.get(url)
        name = {'model': 'model.json', 'stages': 'stages.json', 'overlay': 'overlay.json', 'diff': 'diff.json',
                'topview': 'topview.png', 'maxScript': 'draft.ms'}[k]
        (out / tag).mkdir(parents=True, exist_ok=True)
        (out / tag / name).write_bytes(r.content)
        got[k] = {'bytes': len(r.content), 'sha1': sha1(r.content)}
    return got


def build_once(api: Api, b: dict, s: dict, out: Path, tag: str, rec: dict) -> dict:
    t = time.monotonic()
    r = api.put(f'{b["url"]}/settings', json={'settings': s, 'layersReviewed': True},
                headers={'If-Match': f'"{b["settingsRevision"]}"'})
    rec[f'{tag}SettingsPut'] = {'status': r.status_code, 'seconds': round(time.monotonic() - t, 2)}
    dump(out / tag / 'settings.json', s)
    t = time.monotonic()
    b = api.post(f'{b["url"]}/run', json={}).json()
    run_rec: dict = {}
    b = wait(api, b['url'], run_rec)
    run_rec['wall'] = round(time.monotonic() - t, 2)
    run_rec['run'] = b['run']
    run_rec['result'] = {k: v for k, v in (b.get('result') or {}).items() if k != 'presentation'}
    rec[tag] = run_rec
    if (b['run'] or {}).get('status') == 'done' and b.get('result'):
        rec[tag]['files'] = download_result(api, b, out, tag)
    return b


def finish_case(api: Api, case: dict, b: dict, out: Path, out_root: Path, rec: dict) -> None:
    pid = case['project']
    s = settings_for(case, b)
    b = build_once(api, b, s, out, 'build1', rec)
    if (b['run'] or {}).get('status') != 'done':
        raise RuntimeError(f'build ended {b["run"]["status"]}: {b["run"].get("error")}')
    if case.get('fixes'):
        ov = json.loads((out / 'build1' / 'overlay.json').read_bytes())
        plans = {p.name.split('.')[0]: json.loads(gzip.decompress(p.read_bytes()))
                 for p in (out / 'prepare').glob('*.plan.json.gz')}
        b = api.get(b['url']).json()
        s2 = module(case['fixes']).fixes(json.loads(json.dumps(b['settings'])), b, ov, plans)
        b = build_once(api, b, s2, out, 'build2', rec)
    if case.get('acceptOutlines'):
        ov = json.loads((out / 'build1' / 'overlay.json').read_bytes())
        b = api.get(b['url']).json()
        s2 = json.loads(json.dumps(b['settings']))
        edges = [{'floor': f['floor'], 'a': f['ref']['edge'][0], 'b': f['ref']['edge'][1],
                  'as': 'wall' if f['kind'] == 'outline-wall' else 'glass'}
                 for f in ov['flags'] if f['kind'] in ('outline-wall', 'outline-glass') and f['ref'].get('edge')]
        rec['outlinesAccepted'] = len(edges)
        s2['fixes']['outlineEdges'] = s2['fixes'].get('outlineEdges', []) + edges
        b = build_once(api, b, s2, out, 'build2', rec)
    if case.get('save') and (b['run'] or {}).get('status') == 'done':
        t = time.monotonic()
        v = api.post(f'{b["url"]}/save', json=case['save']).json()
        rec['save'] = {'seconds': round(time.monotonic() - t, 2), 'version': v.get('version'), 'stamp': v.get('stamp'),
                       'label': v.get('label'), 'modelSha1': v.get('modelSha1'), 'downloads': v.get('downloads'),
                       'urls': v.get('urls')}
        n = v['version']
        base = f'/api/projects/{pid}/versions/{n}'
        files = {'model.json': f'{base}/model', 'stages.json': f'{base}/stages',
                 'furniture.csv': f'{base}/downloads/furniture-csv', 'version.ms': f'{base}/downloads/max-script',
                 'offline.html': f'{base}/downloads/offline-html', 'version.json': base}
        rec['version'] = {}
        for name, url in files.items():
            r = api.c.get(url)
            (out / 'version').mkdir(exist_ok=True)
            (out / 'version' / name).write_bytes(r.content)
            rec['version'][name] = {'status': r.status_code, 'bytes': len(r.content), 'sha1': sha1(r.content),
                                    'disposition': r.headers.get('content-disposition')}


def run_case(api: Api, store: Path, case: dict, out_root: Path) -> dict:
    out = out_root / case['name']
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    pid = case['project']
    rec: dict = {'case': case['name'], 'project': pid, 'started': time.strftime('%Y-%m-%d %H:%M:%S')}
    try:
        if case.get('continueFrom'):                         # a case whose prepare ran before (stopAfterPrepare)
            prev = load(out_root / case['continueFrom'] / 'record.json')
            rec.update(uploads=prev['uploads'], build=prev['build'], prepare=prev['prepare'])
            b = api.get(f'/api/projects/{pid}/builds/{prev["build"]}').json()
            finish_case(api, case, b, out, out_root, rec)
            rec['ok'] = True
            return rec
        if case.get('create'):
            rec['create'] = api.post('/api/projects', json=case['create']).json()
        rec['uploads'] = []
        for f in case['files']:
            p = Path(f) if Path(f).is_absolute() else PROJECT / f
            rec['uploads'].append(upload(api, pid, p))
        t = time.monotonic()
        body = {'sources': [u['sha1'] for u in rec['uploads']]}
        if case.get('from') is not None:
            body['from'] = case['from']
        b = api.post(f'/api/projects/{pid}/builds', json=body).json()
        rec['build'] = b['id']
        prep: dict = {}
        b = wait(api, b['url'], prep)
        prep['wall'] = round(time.monotonic() - t, 2)
        prep['run'] = b['run']
        prep['sources'] = b['sources']
        prep['settingsRevision'] = b['settingsRevision']
        rec['prepare'] = prep
        dump(out / 'prepare' / 'build-detail.json', b)
        for src in b['sources']:
            for kind, url in (src.get('urls') or {}).items():
                r = api.get(url)
                data = r.content
                name = f'{src["sha1"][:12]}.{kind}.json' + ('.gz' if kind == 'plan' and data[:2] == b'\x1f\x8b' else '')
                (out / 'prepare' / name).write_bytes(data)
        if (b['run'] or {}).get('status') != 'done':
            raise RuntimeError(f'prepare ended {b["run"]["status"]}: {b["run"].get("error")}')
        if b['settingsRevision'] < 1:
            b = api.get(b['url']).json()
        dump(out / 'prepare' / 'adopted-settings.json', b['settings'])
        if case.get('stopAfterPrepare'):
            rec['ok'] = True
            return rec
        finish_case(api, case, b, out, out_root, rec)
        rec['ok'] = True
    except Exception as e:                                  # recorded, then the next case runs
        rec['ok'] = False
        rec['error'] = f'{type(e).__name__}: {e}'
    finally:
        if rec.get('build'):
            copy_runs(store, pid, rec['build'], out)
        rec['finished'] = time.strftime('%Y-%m-%d %H:%M:%S')
        dump(out / 'record.json', rec)
    return rec


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--base', default='http://127.0.0.1:8739')
    ap.add_argument('--store', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('cases', nargs='+')
    a = ap.parse_args()
    api = Api(a.base)
    ok = True
    for c in a.cases:
        case = load(c)
        t = time.monotonic()
        print(f'== {case["name"]}', flush=True)
        rec = run_case(api, Path(a.store), case, Path(a.out))
        print(f'   {"ok" if rec["ok"] else "FAILED " + rec.get("error", "")} in {time.monotonic() - t:.0f} s', flush=True)
        ok &= rec['ok']
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
