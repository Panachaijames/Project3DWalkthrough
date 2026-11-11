"""ACCEPTANCE A-9 through the served API (step UI): a set-aside, a whole-block set-aside, an opening fix and an accepted
outline edge on the suite; rebuilt; then the same DWG uploaded again into a new build from the first one, whose run must
match every fix by key. Writes <out>/a9/record.json.

    node tools/run-py.mjs a9.py --base http://127.0.0.1:8739 --store <data> --out <dir>
"""
from __future__ import annotations

import argparse
import gzip
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import acc  # noqa: E402

PID = 'suite-fixes'
DWG = acc.PROJECT / 'layout presidential test.dwg'


def run_dir(store: Path, build: str) -> Path:
    runs = sorted((store / 'projects' / PID / 'builds' / build / 'runs').iterdir())
    return [r for r in runs if r.name.endswith('-build')][-1]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--base', default='http://127.0.0.1:8739')
    ap.add_argument('--store', required=True)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    store, out = Path(a.store), Path(a.out) / 'a9'
    out.mkdir(parents=True, exist_ok=True)
    api = acc.Api(a.base)
    rec: dict = {}
    try:
        api.post('/api/projects', json={'name': 'Presidential suite (fixes)', 'shortName': 'Suite fixes', 'id': PID})
        up = acc.upload(api, PID, DWG)
        b = api.post(f'/api/projects/{PID}/builds', json={'sources': [up['sha1']]}).json()
        b = acc.wait(api, b['url'], {})
        assert b['run']['status'] == 'done', b['run']
        s = acc.load(acc.FX / 'settings' / 'suite.json')
        s['options']['outlineWalls'] = 'suggest'
        b = acc.build_once(api, b, s, out, 'build1', rec)
        assert b['run']['status'] == 'done', b['run']
        b1 = b['id']
        rd = run_dir(store, b1)
        ov = acc.load(out / 'build1' / 'overlay.json')
        pieces = acc.load(rd / 'out' / 'pieces.json')['pieces']
        raw = api.get(b['sources'][0]['urls']['plan']).content
        plan = json.loads(gzip.decompress(raw) if raw[:2] == bytes((31, 139)) else raw)
        it, layers = plan['items'], plan['layers']
        key_at = {k: i for i, k in enumerate(it['key'])}
        floor, src = s['floors'][0]['key'], up['sha1']

        def ref(i: int, note: str) -> dict:
            e = it['eid'][i]
            return {'floor': floor, 'source': src, 'key': it['key'][i], 'sig': it['sig'][i], 'rsig': it['rsig'][i],
                    'elementId': plan['elementIds'][e] if e >= 0 else None, 'layer': layers[it['layer'][i]], 'note': note}

        roles = s['layers']
        box = s['floors'][0]['area'].get('bbox')
        def inside(i: int) -> bool:
            if not box:
                return True
            j = it['first'][i] * 2
            x, y = plan['origin'][0] + plan['pts'][j] * plan['quantum'], plan['origin'][1] + plan['pts'][j + 1] * plan['quantum']
            return box[0] <= x <= box[2] and box[1] <= y <= box[3]
        # (1) one item: the first wall-layer line inside the area that is not part of a block
        one = next(i for i in range(len(it['key'])) if it['type'][i] == 0 and '/' not in it['key'][i]
                   and roles.get(layers[it['layer'][i]]) == 'wall' and inside(i))
        # (2) one whole block: the INSERT of the first furniture piece made from a block
        piece = next(p for p in pieces if p['key'] and p['key'] in key_at)
        blk = key_at[piece['key']]
        assert it['type'][blk] == 5, 'the piece key is not an insert anchor'
        # (3) one opening: the first door of the floor, made a window with its own head and sill
        op = next(o for f in ov['floors'] for o in f['openings'] if o['kind'] == 'door')
        # (4) one outline edge accepted as a wall
        edge = next(f for f in ov['flags'] if f['kind'] == 'outline-wall' and f['ref'].get('edge'))
        b = api.get(b['url']).json()
        s2 = json.loads(json.dumps(b['settings']))
        s2['fixes'] = {
            'setAside': [ref(one, 'A-9 one item'), ref(blk, 'A-9 one whole block')],
            'openings': [{'floor': floor, 'a': op['a'], 'b': op['b'], 'kind': 'window', 'head': 2.2, 'sill': 0.9}],
            'outlineEdges': [{'floor': edge['floor'], 'a': edge['ref']['edge'][0], 'b': edge['ref']['edge'][1], 'as': 'wall'}],
        }
        rec['fixes'] = s2['fixes']
        rec['piece'] = piece
        rec['opening'] = op
        b = acc.build_once(api, b, s2, out, 'build2', rec)
        assert b['run']['status'] == 'done', b['run']
        rep2 = acc.load(run_dir(store, b1) / 'out' / 'report.json')
        rec['report2fixes'] = rep2.get('fixes')
        rec['diff2'] = acc.load(out / 'build2' / 'diff.json')['against']
        m1, m2 = acc.load(out / 'build1' / 'model.json'), acc.load(out / 'build2' / 'model.json')
        rec['furniture'] = [len(m1['furniture']), len(m2['furniture'])]
        rec['parts'] = [len(m1['parts']), len(m2['parts'])]
        rec['openingKinds'] = [{k: sum(1 for o in m['openings'] if o['kind'] == k) for k in ('door', 'window', 'passage')}
                               for m in (m1, m2)]
        # (5) the same DWG uploaded again; a new build from the first build: its recipe, fixes included
        up2 = acc.upload(api, PID, DWG)
        rec['reupload'] = up2
        t = time.monotonic()
        c = api.post(f'/api/projects/{PID}/builds', json={'sources': [up2['sha1']], 'from': {'kind': 'build', 'build': b1}}).json()
        c = acc.wait(api, c['url'], {})
        rec['reuploadPrepareSeconds'] = round(time.monotonic() - t, 2)
        assert c['run']['status'] == 'done', c['run']
        rec['reuploadFixesEqual'] = c['settings']['fixes'] == s2['fixes']
        rec['reuploadLayersReviewedAt'] = c.get('layersReviewedAt')
        c = acc.build_once(api, c, c['settings'], out, 'build3', rec)
        assert c['run']['status'] == 'done', c['run']
        rep3 = acc.load(run_dir(store, c['id']) / 'out' / 'report.json')
        rec['report3fixes'] = rep3.get('fixes')
        rec['model3EqualsModel2'] = (out / 'build3' / 'model.json').read_bytes() == (out / 'build2' / 'model.json').read_bytes()
        rec['ok'] = True
    except Exception as e:
        rec['ok'] = False
        rec['error'] = f'{type(e).__name__}: {e}'
    acc.dump(out / 'record.json', rec)
    print('ok' if rec['ok'] else rec['error'])
    return 0 if rec['ok'] else 1


if __name__ == '__main__':
    sys.exit(main())
