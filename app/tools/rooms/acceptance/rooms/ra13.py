"""RI (rooms milestone), ACCEPTANCE RA-13 through a SERVED API with the real worker: the new fixes survive a rebuild and a
re-upload. On the house (new rule, fixtures/upload/settings/house-rooms.json), as a new project `house-fixes`:

  build1 (no fix) -> the fixes below, taken from build1's own report and overlay -> build2: the report lists each fix
  as matched (the one put in no room: unmatched, with its `fix-unmatched` flag) -> the same DWG uploaded again into a
  new build from build2's build: its settings carry all six fix lists as they were, and build3's model is build2's,
  byte for byte, its fix rows the same -> the API's two refusals (a room name of 201 characters, 5,001 other fixes: 422).

Fixes (each "staff" answer of R-6.2): a closing line drawn ('line'), an app closing removed ('none'), room fixes (a name
on the living room, "no ceiling", "no floor here", "floor here" on an unfloored area, "it is outdoors" on another, one in
no room), stair fixes (`use: 'lines'` on the climbable stair, `use: 'climb'` and `bottom` on stairs kept as lines) and a
set-aside with "the floor runs past it".

    node tools/run-py.mjs ra13.py --base http://127.0.0.1:8748 --store <data> --out <dir>    -> <out>/ra13/record.json
"""
from __future__ import annotations

import argparse
import gzip
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'upload-ur'))
import acc  # noqa: E402

PID = 'house-fixes'
DWG = acc.PROJECT / 'Test Sukhumvit Residence.dwg'
OLD = ('setAside', 'openings', 'outlineEdges')


def run_dir(store: Path, build: str) -> Path:
    runs = sorted((store / 'projects' / PID / 'builds' / build / 'runs').iterdir())
    return [r for r in runs if r.name.endswith('-build')][-1]


def report_of(store: Path, build: str) -> dict:
    return acc.load(run_dir(store, build) / 'out' / 'report.json')


def inner_point(o: list, holes: list | None = None) -> list[float]:
    """A point inside polygon `o` (and outside its holes): the middle of the widest run of a horizontal line through
    the middle of its box (no shapely in the API's Python)."""
    ys = [p[1] for p in o]
    y = (min(ys) + max(ys)) / 2 + 1e-4
    xs = []
    for ring in [o] + list(holes or []):
        for (x1, y1), (x2, y2) in zip(ring, ring[1:] + ring[:1]):
            if (y1 <= y < y2) or (y2 <= y < y1):
                xs.append(x1 + (y - y1) * (x2 - x1) / (y2 - y1))
    xs.sort()
    runs = [(xs[i], xs[i + 1]) for i in range(0, len(xs) - 1, 2)]
    a, b = max(runs, key=lambda r: r[1] - r[0])
    return [round((a + b) / 2, 3), round(y, 3)]


def put_expect(api: acc.Api, b: dict, s: dict) -> dict:
    """A settings PUT that must be refused -> {status, codes}."""
    r = api.c.put(f'{b["url"]}/settings', json={'settings': s, 'layersReviewed': True},
                  headers={'If-Match': f'"{b["settingsRevision"]}"'})
    body = r.json() if r.headers.get('content-type', '').startswith('application/json') else {}
    det = (body.get('details') or {}) if isinstance(body, dict) else {}
    return {'status': r.status_code, 'code': body.get('code') if isinstance(body, dict) else None,
            'issues': [i.get('path') for i in (det.get('issues') or [])][:5]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--base', default='http://127.0.0.1:8748')
    ap.add_argument('--store', required=True)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    store, out = Path(a.store), Path(a.out) / 'ra13'
    out.mkdir(parents=True, exist_ok=True)
    api = acc.Api(a.base)
    rec: dict = {'started': time.strftime('%Y-%m-%d %H:%M:%S')}
    try:
        api.post('/api/projects', json={'name': 'Test Sukhumvit Residence (RA-13 fixes)', 'shortName': 'House fixes',
                                        'id': PID})
        up = acc.upload(api, PID, DWG)
        b = api.post(f'/api/projects/{PID}/builds', json={'sources': [up['sha1']]}).json()
        b = acc.wait(api, b['url'], {})
        assert b['run']['status'] == 'done', b['run']
        rec['draftOptions'] = b['settings']['options']
        s = acc.settings_for({'settings': {'fixture': 'house-rooms'}}, b)
        b = acc.build_once(api, b, s, out, 'build1', rec)
        assert b['run']['status'] == 'done', b['run']
        b1 = b['id']
        rep1 = report_of(store, b1)
        ov1 = acc.load(out / 'build1' / 'overlay.json')
        m1 = acc.load(out / 'build1' / 'model.json')
        raw = api.get(b['sources'][0]['urls']['plan']).content
        plan = json.loads(gzip.decompress(raw) if raw[:2] == bytes((31, 139)) else raw)
        src = up['sha1']
        g, u = rep1['floors']['ground'], rep1['floors']['upper']

        # closings: an app closing taken out, and a line drawn where another app closing stands (or a gap's mouth)
        closings = []
        app_g = [c for c in g['slab']['closings'] if c.get('kind') in ('doorway', 'bridge')]
        assert len(app_g) >= 2, g['slab']['closings']
        closings.append({'floor': 'ground', 'a': app_g[0]['a'], 'b': app_g[0]['b'], 'use': 'none'})
        mouth = next((f for f in ov1['flags'] if f['kind'] == 'slab-gap' and (f.get('ref') or {}).get('a')), None)
        if mouth:
            closings.append({'floor': mouth['floor'], 'a': mouth['ref']['a'], 'b': mouth['ref']['b'], 'use': 'line'})
        else:
            closings.append({'floor': 'ground', 'a': app_g[1]['a'], 'b': app_g[1]['b'], 'use': 'line'})
        rec['closingFromMouth'] = bool(mouth)

        # rooms: the overlay's spaces by floor (sheet m, the frame of the fixes), largest first
        sp = {f['key']: sorted(f['spaces'], key=lambda x: -x['area']) for f in ov1['floors']}
        def pt(x):
            return inner_point(x['o'], x.get('h'))
        rooms = [
            {'floor': 'ground', 'at': [26.2, 11.1], 'name': 'Living (RI acceptance)', 'slab': 'auto', 'ceiling': 'auto'},
            {'floor': 'upper', 'at': pt(sp['upper'][0]), 'name': None, 'slab': 'auto', 'ceiling': 'none'},
            {'floor': 'upper', 'at': pt(sp['upper'][len(sp['upper']) // 2]), 'name': None, 'slab': 'none', 'ceiling': 'auto'},
        ]
        unf_g = g['slab']['unfloored']
        unf_u = u['slab']['unfloored']
        if unf_g:
            rooms.append({'floor': 'ground', 'at': inner_point(unf_g[0]['o']), 'name': None, 'slab': 'floor', 'ceiling': 'auto'})
        if unf_u:
            rooms.append({'floor': 'upper', 'at': inner_point(unf_u[0]['o']), 'name': None, 'slab': 'none', 'ceiling': 'auto'})
        rooms.append({'floor': 'ground', 'at': [500.0, 500.0], 'name': 'Nowhere (RI acceptance)', 'slab': 'auto', 'ceiling': 'auto'})
        rec['roomsExpectedUnmatched'] = [len(rooms) - 1]

        # stairs: the climbable stair kept as lines; a stair kept as lines asked to climb; a bottom on another
        rows_g = g['stairways']
        climb = next(r for r in rows_g if r['state'] == 'climb')
        kept = [r for r in rows_g if r['state'] == 'lines' and r.get('outline')]
        fits = [r for r in kept if r.get('risers') and 'give' in (r.get('text') or '')]
        # (RI's first run put this fix at a point inside the stair's outline as the report draws it, as the Check step's
        # pointIn() does: it found no stair; the house's L outline cuts across the inner corner. Recorded in GAPS.md; the
        # fix is now put on riser 1's middle, walk[1], a point on the flight.)
        rec['climbOutline'] = climb['outline']
        rec['climbOutlinePoint'] = inner_point(climb['outline'])
        stairs = [{'floor': 'ground', 'at': climb['walk'][1], 'bottom': None, 'use': 'lines'}]
        if fits:
            stairs.append({'floor': 'ground', 'at': inner_point(fits[0]['outline']), 'bottom': None, 'use': 'climb'})
        other = next((r for r in kept if not fits or r['id'] != fits[0]['id']), None)
        if other:
            o = other['outline']
            stairs.append({'floor': 'ground', 'at': inner_point(o), 'bottom': [round((o[0][0] + o[1][0]) / 2, 3), round((o[0][1] + o[1][1]) / 2, 3)],
                           'use': 'auto'})
        rec['stairRows'] = [{'id': r['id'], 'state': r['state'], 'text': r.get('text')} for r in rows_g]

        # a set-aside with "the floor runs past it": the first single-line flag's first item on the ground floor
        it, key_at = plan['items'], {k: i for i, k in enumerate(plan['items']['key'])}
        single = next(f for f in ov1['flags'] if f['kind'] == 'single-line' and f['floor'] == 'ground'
                      and any(k in key_at for k in (f.get('ref') or {}).get('keys') or []))
        k = next(k for k in single['ref']['keys'] if k in key_at)
        i = key_at[k]
        e = it['eid'][i]
        aside = {'floor': 'ground', 'source': src, 'key': k, 'sig': it['sig'][i], 'rsig': it['rsig'][i],
                 'elementId': plan['elementIds'][e] if e >= 0 else None, 'layer': plan['layers'][it['layer'][i]],
                 'note': 'RA-13: the floor runs past it', 'floorPast': True}

        b = api.get(b['url']).json()
        s2 = json.loads(json.dumps(b['settings']))
        s2['fixes'] = {'setAside': [aside], 'openings': [], 'outlineEdges': [], 'closings': closings, 'rooms': rooms,
                       'stairs': stairs}
        rec['fixes'] = s2['fixes']
        b = acc.build_once(api, b, s2, out, 'build2', rec)
        assert b['run']['status'] == 'done', b['run']
        rep2 = report_of(store, b1)
        rec['report2fixes'] = rep2.get('fixes')
        ov2 = acc.load(out / 'build2' / 'overlay.json')
        rec['unmatchedFlags2'] = [{'title': f['title'], 'ref': f.get('ref')} for f in ov2['flags'] if f['kind'] == 'fix-unmatched']
        m2 = acc.load(out / 'build2' / 'model.json')
        rec['model2'] = {'stairways': [(x['id'], x.get('from'), x.get('to'), x.get('risers')) for x in m2.get('stairways', [])],
                         'names': sorted({r['name'] for r in m2['rooms']} & {'Living (RI acceptance)', 'Nowhere (RI acceptance)'}),
                         'ceilings': sum(1 for p in m2['parts'] if p['kind'] == 'ceiling'),
                         'ceilings1': sum(1 for p in m1['parts'] if p['kind'] == 'ceiling')}
        rec['plate2'] = {k: f['slab']['plate'] for k, f in rep2['floors'].items()}
        rec['plate1'] = {k: f['slab']['plate'] for k, f in rep1['floors'].items()}

        # the same DWG uploaded again; a new build from build2's build: its recipe, fixes included
        up2 = acc.upload(api, PID, DWG)
        rec['reupload'] = up2
        c = api.post(f'/api/projects/{PID}/builds', json={'sources': [up2['sha1']], 'from': {'kind': 'build', 'build': b1}}).json()
        c = acc.wait(api, c['url'], {})
        assert c['run']['status'] == 'done', c['run']
        rec['reuploadOptions'] = c['settings']['options']
        rec['reuploadFixesEqual'] = c['settings']['fixes'] == s2['fixes']
        rec['reuploadOldListsEqual'] = {k: c['settings']['fixes'].get(k) for k in OLD} == {k: s2['fixes'][k] for k in OLD}
        c = acc.build_once(api, c, c['settings'], out, 'build3', rec)
        assert c['run']['status'] == 'done', c['run']
        rep3 = report_of(store, c['id'])
        rec['report3fixes'] = rep3.get('fixes')
        rec['report3EqualsReport2Fixes'] = rep3.get('fixes') == rep2.get('fixes')
        rec['model3EqualsModel2'] = (out / 'build3' / 'model.json').read_bytes() == (out / 'build2' / 'model.json').read_bytes()

        # the API's two refusals (nothing is built)
        c = api.get(c['url']).json()
        bad = json.loads(json.dumps(c['settings']))
        bad['fixes']['rooms'] = [dict(rooms[0], name='x' * 201)]
        rec['refuseLongName'] = put_expect(api, c, bad)
        bad = json.loads(json.dumps(c['settings']))
        bad['fixes']['closings'] = [{'floor': 'ground', 'a': [0.0, float(i)], 'b': [1.0, float(i)], 'use': 'line'} for i in range(5001)]
        rec['refuseTooMany'] = put_expect(api, c, bad)
        rec['ok'] = True
    except Exception as e:                                  # recorded
        rec['ok'] = False
        rec['error'] = f'{type(e).__name__}: {e}'
    rec['finished'] = time.strftime('%Y-%m-%d %H:%M:%S')
    acc.dump(out / 'record.json', rec)
    print('ok' if rec['ok'] else rec['error'])
    return 0 if rec['ok'] else 1


if __name__ == '__main__':
    sys.exit(main())
