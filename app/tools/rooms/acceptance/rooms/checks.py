"""RI (rooms milestone), step `rooms-checks`: the figures of ACCEPTANCE RA-1 - RA-18 from what the other steps recorded,
into <WT_TMP>/rooms-result.json (docs/rooms/GAPS.md is written from it), and a short text summary on stdout.

    node tools/run-builder-py.mjs tools/rooms/acceptance/rooms/checks.py        (WT_TMP = the acceptance folder)

Reads (all under WT_TMP unless said): data/ (the store: the new-rule versions v1 of the seven `rooms-builds` projects,
and the 9 Nov versions they are compared with), out/<case>/ (acc.py's records), acc/out/ (the old `acceptance` step's
records and check_a1's), e2e-rooms/ (upload-walk and stairs reports), node-rooms/ (climb.test.ts's times),
logs/rooms-golden.txt; the answer keys in fixtures/rooms/keys/. Nothing is written but the result file.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union

APP = Path(__file__).resolve().parents[4]
W = Path(os.environ['WT_TMP'])
DATA = W / 'data'
KEYS = APP / 'fixtures' / 'rooms' / 'keys'
NEW = {'bank': 'bank-rooms', 'house': 'house-rooms', 'suite': 'suite-rooms', 'tower': 'tower-rooms',
       'suite-revit': 'suite-revit-rooms'}
ASIDE = {'tower': 'tower-aside', 'suite-revit': 'suite-revit-aside'}
#: the 9 Nov versions (old rule) of the same drawings, in the copied acceptance store
OLD = {'bank': ('bank-sampeng', 3), 'house': ('house-upload', 1), 'suite': ('suite-upload', 1),
       'tower': ('tower-upload', 1), 'suite-revit': ('suite-revit', 1)}
#: ACCEPTANCE RA-4: floor -> (must at least, must at most, should lo, should hi)
PLATE = {('bank', 'L1'): (235.3, 243, 234, 241), ('bank', 'L2'): (295.4, 307, 293, 303),
         ('house', 'ground'): (483, 545, 495, 530), ('house', 'upper'): (431, 497, 435, 460),
         ('tower', 'L29'): (814, 885, 840, 875), ('tower', 'L30'): (704, 772, 725, 765),
         ('suite', 'suite'): (400, 660, 460, 480), ('suite-revit', 'L1'): (260, 284, 262, 280)}


def load(p):
    return json.loads(Path(p).read_bytes())


def maybe(p):
    try:
        return load(p)
    except (OSError, ValueError):
        return None


def poly(o, h=()):
    return Polygon(o, [x for x in (h or []) if len(x) >= 3]).buffer(0)


def version(pid: str, n: int = 1) -> dict:
    d = DATA / 'projects' / pid / 'versions' / str(n)
    v = {'dir': d, 'version': maybe(d / 'version.json'), 'model': maybe(d / 'model.json'),
         'report': maybe(d / 'source' / 'build-report.json'), 'flags': maybe(d / 'source' / 'flags.json')}
    return v


def overlay_of(case: str) -> dict | None:
    """The overlay of the build the case saved (build2 when it rebuilt)."""
    for tag in ('build2', 'build1'):
        o = maybe(W / 'out' / case / tag / 'overlay.json')
        if o is not None:
            return o
    return None


def flags_of(v: dict) -> list:
    f = v['flags'] or {}
    return f['flags'] if isinstance(f, dict) else f


# ------------------------------------------------------------------------------------------------------- per drawing
def drawing_rows(name: str) -> dict:
    """New rule against old rule, per floor: plate, holes, rooms, names, ceilings, stairs."""
    pid = NEW[name]
    new, old = version(pid), version(*OLD[name])
    ov = overlay_of(pid) or {'floors': [], 'flags': []}
    mn, mo = new['model'], old['model']
    rows = {}
    for key, fl in new['report']['floors'].items():
        ofl = (old['report'] or {}).get('floors', {}).get(key, {})
        osum = (old['report'] or {}).get('summary', {}).get('floors', {}).get(key, {})
        nsum = new['report']['summary']['floors'].get(key, {})
        slab = fl['slab']
        cut = [h for h in slab['holes'] if h.get('cut')]
        notcut = [h for h in slab['holes'] if not h.get('cut')]
        ceil = [p for p in mn['parts'] if p['kind'] == 'ceiling' and p['floor'] == key]
        ceil_area = round(sum(poly(p['o'], p.get('h')).area for p in ceil), 1)
        newslab = round(sum(poly(p['o'], p.get('h')).area for p in mn['parts'] if p['kind'] == 'slab' and p['floor'] == key), 1)
        oldslab = round(sum(poly(p['o'], p.get('h')).area for p in (mo or {}).get('parts', []) if p['kind'] == 'slab' and p['floor'] == key), 1)
        ways = [r for r in fl['stairways']]
        lo = PLATE.get((name, key))
        rows[key] = {
            'plate0': slab['plate'], 'ring': slab['ring'], 'terraces': slab['terraces'], 'todayInThisRun': slab['old'],
            'oldPlateArea': osum.get('plateArea'), 'oldSlabParts': oldslab, 'newSlabParts': newslab,
            'plateBounds': lo and {'mustAtLeast': lo[0], 'mustAtMost': lo[1], 'should': [lo[2], lo[3]],
                                   'must': lo[0] <= slab['plate'] <= lo[1], 'inShould': lo[2] <= slab['plate'] <= lo[3]},
            'holesCut': [{'what': h['what'], 'area': h['area'], 'at': h.get('at')} for h in cut],
            'holesNotCut': [{'what': h['what'], 'area': h['area'], 'why': h.get('why')} for h in notcut],
            'oldVoids': [{'what': x.get('what'), 'area': x.get('area')} for x in ((mo or {}).get('voids') or {}).get(key, [])],
            'unfloored': [{'area': u['area'], 'kind': u.get('kind'), 'mouth': bool(u.get('mouth')), 'at': u.get('at')} for u in slab['unfloored']],
            'closings': {k: sum(1 for c in slab['closings'] if c.get('kind') == k) for k in ('doorway', 'bridge', 'staff')},
            'closingWidths': [c.get('width') for c in slab['closings'] if c.get('kind') == 'doorway'],
            'dropped': [{'area': d['area'], 'why': d.get('why')} for d in slab['dropped']],
            'rooms': fl['rooms']['spaces'], 'named': fl['rooms']['named'], 'shapes': fl['rooms'].get('shapes'),
            'namesInNoRoom': [r.get('name') for r in fl['rooms']['open'] if r.get('name') and not r.get('space') and not r.get('why')],
            'closedNoDoor': [r for r in fl['rooms']['open'] if r.get('space')],
            # RR FID-1: a closed area of 10 m2 or more that is no room; a name given by distance to a room under 4 m2
            'notARoom': [r.get('area') for r in fl['rooms']['open'] if r.get('why') == 'not a room'],
            'namesInSmallRooms': [(r.get('name'), r.get('area')) for r in fl['rooms']['open'] if r.get('why') == 'placed by distance'],
            'several': fl['rooms']['several'],
            'namesNew': sum(1 for r in mn['rooms'] if r['floor'] == key),
            'namesOld': sum(1 for r in (mo or {}).get('rooms', []) if r['floor'] == key),
            'ceilingParts': len(ceil), 'ceilingArea': ceil_area,
            'ceilingZ0': sorted({p['z0'] for p in ceil}),
            'stairsClimb': [{'id': r['id'], 'to': r.get('to'), 'risers': r.get('risers'), 'riser': r.get('riser')} for r in ways if r['state'] == 'climb'],
            'stairsLines': [{'id': r['id'], 'why': r.get('why'), 'severity': r.get('severity'), 'text': r.get('text')} for r in ways if r['state'] != 'climb'],
            'stairClash': len(fl.get('stairClash') or []),
            'oldStairs': (osum.get('stairs') or {}),
            'oldStepParts': sum(1 for p in (mo or {}).get('parts', []) if p['kind'] == 'step' and p['floor'] == key),
            'newStepParts': sum(1 for p in mn['parts'] if p['kind'] == 'step' and p['floor'] == key),
            'treads': sum(1 for p in mn['parts'] if p['kind'] == 'tread' and p['floor'] == key),
            'landings': sum(1 for p in mn['parts'] if p['kind'] == 'landing' and p['floor'] == key),
            'platesDroppedOld': len(ofl.get('platesDropped') or []),
            'counts': nsum.get('counts'),
        }
    fk = {}
    for f in ov['flags']:
        fk[f['kind']] = fk.get(f['kind'], 0) + 1
    fo = {}
    for f in flags_of(old):
        fo[f['kind']] = fo.get(f['kind'], 0) + 1
    st = [{'id': s['id'], 'from': s['from'], 'to': s['to'], 'kind': s.get('kind'), 'risers': s['risers'], 'riser': s['riser'],
           'treads': s.get('treads'), 'landings': s.get('landings'), 'direction': s.get('direction'), 'walk1': s['walk'][1],
           'bottom': s.get('bottom')} for s in mn.get('stairways', [])]
    return {'project': pid, 'stamp': (new['version'] or {}).get('stamp') or (new['version'] or {}).get('modelSha1', '')[:12],
            'modelFormat': (new['version'] or {}).get('modelFormat'), 'oldVersion': f'{OLD[name][0]} v{OLD[name][1]}',
            'oldStamp': (old['version'] or {}).get('stamp') or (old['version'] or {}).get('modelSha1', '')[:12],
            'oldModelFormat': (old['version'] or {}).get('modelFormat'),
            'floors': rows, 'flagsNew': fk, 'flagsOld': fo, 'stairways': st,
            'roomsNew': len(mn['rooms']), 'roomsOld': len((mo or {}).get('rooms', [])), 'spaces': len(mn.get('spaces', []))}


def holds(ov: dict, key: str, field: str, pt) -> list:
    fl = next((f for f in ov['floors'] if f['key'] == key), None)
    if fl is None:
        return []
    return [x for x in fl.get(field) or [] if poly(x['o'], x.get('h')).covers(Point(pt))]


def on_plate(ov: dict, key: str, pt) -> bool:
    fl = next((f for f in ov['floors'] if f['key'] == key), None)
    return bool(fl) and any(poly(s['o'], s.get('h')).covers(Point(pt)) for s in fl['slabs'])


def probes(name: str, case: str) -> list:
    """RA-6 in the builder's terms: each probe of keys/probes.json, each side that had no floor on 9 Nov: is there plate
    at some of 0.4 ... 0.9 m in front (the overlay's slabs, sheet m), and a room within 2.5 m."""
    key = load(KEYS / 'probes.json')['drawings'].get(name)
    ov = overlay_of(case)
    if not key or ov is None:
        return []
    out = []
    for p in key['probes']:
        for side in p['sides']:
            pts = [(p['at'][0] + side * d * p['n'][0], p['at'][1] + side * d * p['n'][1]) for d in (0.4, 0.5, 0.6, 0.7, 0.8, 0.9)]
            far = [(p['at'][0] + side * d * p['n'][0], p['at'][1] + side * d * p['n'][1]) for d in (0.5, 1.0, 1.5, 2.0, 2.5)]
            out.append({'probe': p['id9Nov'], 'kind': p['kind'], 'floor': p['floor'], 'side': side,
                        'plate': any(on_plate(ov, p['floor'], q) for q in pts),
                        'room': any(holds(ov, p['floor'], 'spaces', q) for q in far)})
    return out


def bank_names() -> dict:
    ov = overlay_of('bank-rooms')
    key = load(KEYS / 'bank.json')['floors']
    ok, bad = 0, []
    for fk, rows in key.items():
        for r in rows:
            sp = holds(ov, fk, 'spaces', r['at'])
            if sp and any(r['name'] in (s.get('names') or [s.get('name')]) for s in sp):
                ok += 1
            else:
                bad.append({'floor': fk, 'name': r['name'], 'rooms': [s.get('names') for s in sp]})
    return {'ok': ok, 'of': sum(len(v) for v in key.values()), 'bad': bad}


def suite_names() -> dict:
    """RA-7's should: each of the 16 key points (keys/suite.json) stands in the room that carries its name."""
    ov = overlay_of('suite-rooms')
    key = load(KEYS / 'suite.json')['floors']
    ok, rows = 0, []
    for fk, ks in key.items():
        for r in ks:
            sp = holds(ov, fk, 'spaces', r['at'])
            names = [n for s in sp for n in (s.get('names') or [s.get('name')])]
            good = r['name'] in names
            ok += good
            rows.append({'name': r['name'], 'ok': good, 'roomHolds': names, 'space': [s['id'] for s in sp]})
    return {'ok': ok, 'of': sum(len(v) for v in key.values()), 'rows': rows}


def house_points() -> list:
    ov = overlay_of('house-rooms')
    out = []
    for fk, ks in load(KEYS / 'house.json')['floors'].items():
        for k in ks:
            sp = holds(ov, fk, 'spaces', k['at'])
            a = sp[0]['area'] if len(sp) == 1 else None
            out.append({'what': k['what'], 'rooms': len(sp), 'area': a, 'range': k['area'],
                        'ok': len(sp) == 1 and k['area'][0] <= a <= k['area'][1]})
    return out


def prototype_slabs() -> dict:
    """RA-4's should against the prototypes' slabs: per floor, the slab parts of the new-rule model and of the prototype's
    model (fixtures/models/{bank-v2,house,suite}.model.json), both as model + offset (the floors' aligned frame), the
    area in the new plate and not in the prototype's slab, and the other way (m2). No picture."""
    out = {}
    for name, proto in (('bank', 'bank-v2'), ('house', 'house'), ('suite', 'suite')):
        mn = version(NEW[name])['model']
        mp = load(APP / 'fixtures' / 'models' / f'{proto}.model.json')
        rows = {}
        for f in mn['floors']:
            k = f['key']

            def slab(m):
                ox, oy = m['offset']
                return unary_union([poly([(x + ox, y + oy) for x, y in p['o']], [[(x + ox, y + oy) for x, y in h] for h in p.get('h') or []])
                                    for p in m['parts'] if p['kind'] == 'slab' and p['floor'] == k])
            a, b = slab(mn), slab(mp)
            rows[k] = {'new': round(a.area, 1), 'prototype': round(b.area, 1), 'newNotPrototype': round(a.difference(b).area, 1),
                       'prototypeNotNew': round(b.difference(a).area, 1),
                       'over15pct': (a.symmetric_difference(b).area > 0.15 * b.area) if b.area else None}
        out[name] = rows
    return out


def bank_written_areas() -> dict:
    m = version('bank-rooms')['model']
    sp = {s['id']: s for s in m['spaces']}
    rows = []
    for r in m['rooms']:
        mt = re.search(r'([\d.,]+)\s*m', r['label'].split('·')[-1]) if '·' in r['label'] else None
        if not mt or not r.get('space'):
            continue
        w = float(mt.group(1).replace(',', '.'))
        a = sp[r['space']]['area']
        rows.append({'name': r['name'], 'written': w, 'room': a, 'within15': abs(a - w) <= 0.15 * w})
    return {'within15': sum(r['within15'] for r in rows), 'of': len(rows), 'rows': rows}


# --------------------------------------------------------------------------------------------------- times (RA-14)
CHILD = re.compile(r'==== (?P<title>.+?): exit (?P<exit>\S+), (?P<sec>[\d.]+|None) s, peak (?P<peak>[\d.]+|None) MB')


def times(out_dir: Path, case: str, tag: str = 'build1') -> dict | None:
    rec = maybe(out_dir / case / 'record.json')
    if not rec or not rec.get(tag):
        return None
    b = rec[tag]
    steps = {s['name']: s['seconds'] for s in (b.get('run') or {}).get('steps', [])}
    peaks = []
    for log in sorted((out_dir / case / 'runs').glob('*/log.txt')):
        for m in CHILD.finditer(log.read_text(encoding='utf-8', errors='replace')):
            if m['peak'] != 'None':
                peaks.append(float(m['peak']))
    job = sum(v for v in steps.values() if v)
    return {'wall': b.get('wall'), 'jobSeconds': round(job, 1), 'steps': steps, 'maxPeakMB': max(peaks, default=None)}


def gpu_fps() -> dict:
    out = {}
    for f in sorted((W / 'e2e-rooms' / 'stairs').glob('*.json')):
        d = maybe(f)
        if not isinstance(d, dict):                     # old-versions.json is a list
            continue
        g = d.get('fpsGpu')
        if g:
            wf = g.get('walkingFrames') or {}
            out[f.stem] = {'renderer': g.get('renderer'), 'standingFps': g.get('standingFps'), 'walkingFps': g.get('walkingFps'),
                           'p95Ms': wf.get('p95Ms'), 'maxMs': wf.get('maxMs'), 'over33': wf.get('over33'),
                           'footBeforeW': g.get('footBeforeW'), 'footAfterW': g.get('footAfterW')}
    return out


def stairs_reports() -> dict:
    """stairs.spec.ts's per-file results (RA-8, RA-10): up, down, the keyboard, the stale foot, the floors, ceilings."""
    out = {}
    for f in sorted((W / 'e2e-rooms' / 'stairs').glob('*.json')):
        d = maybe(f)
        if not isinstance(d, dict):                     # old-versions.json: the old versions' panels (RA-8)
            out[f.stem] = d
            continue
        out[f.stem] = {k: d.get(k) for k in ('up', 'down', 'keyboard', 'staleFoot', 'floors', 'ceilings', 'fps') if k in d}
    return out


def walk_reports() -> dict:
    out = {}
    for f in sorted((W / 'e2e-rooms' / 'upload-walk').glob('*.json')):
        d = maybe(f) or {}
        row = {'should': d.get('should'), 'loads': (d.get('loads') or {}).get('stamp'),
               'start': (d.get('start') or {}).get('ok'), 'floors': (d.get('floors') or {}).get('ok')}
        w = d.get('walls') or {}
        row['walls'] = {'ok': w.get('ok'), 'tried': sum(x.get('tried', 0) for x in w.get('detail') or [] if isinstance(x, dict)),
                        'wentThrough': sum(x.get('wentThrough', 0) for x in w.get('detail') or [] if isinstance(x, dict))}
        dr = d.get('doors') or {}
        row['doors'] = {'ok': dr.get('ok'), 'failures': [{k: x.get(k) for k in ('id', 'exterior', 'fwd', 'back')} for x in dr.get('failures') or []],
                        'detail': {k: v for k, v in (dr.get('detail') or {}).items() if not isinstance(v, list)} if isinstance(dr.get('detail'), dict) else None}
        gl = d.get('glass') or {}
        row['glass'] = {'ok': gl.get('ok'), 'failures': gl.get('failures') or [],
                        'probes': (gl.get('detail') or {}).get('probes') if isinstance(gl.get('detail'), dict) else None,
                        'parts': len((gl.get('detail') or {}).get('parts') or []) if isinstance(gl.get('detail'), dict) else None}
        ra6 = d.get('ra6') or {}
        row['ra6'] = {'judged': ra6.get('judged'), 'ok': ra6.get('ok'), 'failures': ra6.get('failures'),
                      'results': [{'id': x.get('id9Nov'), 'standsOnFloor': x.get('standsOnFloor'),
                                   'sides': [{k: s.get(k) for k in ('side', 'floorAt', 'walk', 'through')} for s in x.get('sides') or []]}
                                  for x in (ra6.get('detail') or {}).get('results') or []],
                      'notJudged': (ra6.get('detail') or {}).get('notJudged')}
        out[f.stem] = row
    return out


def aside_names(n: str, case: str) -> dict:
    """RR FID-1: each room name of the build without set-asides and the area of the room it names, against the build
    with them: `namesLost` are the names whose room is gone or under half its area (the new suite's 52 m2 living room
    became a 1.5 m2 piece on 11 Nov); the must is that there are none."""
    def areas(v):
        m = (v or {}).get('model') or {}
        area = {s['id']: s.get('area') or 0.0 for s in m.get('spaces') or []}
        return {(r['floor'], r['name']): area.get(r.get('space'), 0.0) for r in m.get('rooms') or []}
    try:
        base, now = areas(version(NEW[n])), areas(version(case))
    except Exception as e:  # noqa: BLE001 - a missing version is reported, not raised
        return {'error': f'{type(e).__name__}: {e}'}
    lost = [{'floor': k[0], 'name': k[1], 'was': a, 'now': now.get(k, 0.0)} for k, a in sorted(base.items())
            if a >= 4.0 and now.get(k, 0.0) < 0.5 * a]
    return {'names': len(base), 'namesLost': lost, 'must': not lost}


def main() -> int:
    res: dict = {'format': 'rooms-acceptance-checks/1', 'tmp': str(W)}
    res['drawings'] = {n: drawing_rows(n) for n in NEW}
    res['aside'] = {}
    for n, case in ASIDE.items():
        v = version(case)
        if not v['report']:
            res['aside'][n] = {'missing': True}
            continue
        sa = load(W / 'out' / case / 'build2' / 'settings.json')['fixes']['setAside'] if (W / 'out' / case / 'build2' / 'settings.json').exists() else []
        res['aside'][n] = {'setAside': len(sa), 'stamp': v['version'].get('stamp'),
                           # RR FID-1: the name checks of the set-aside builds: the names keep their rooms (a name
                           # whose room shrank to under half of what it was without the set-asides is `namesLost`)
                           'names': aside_names(n, case),
                           'floors': {k: {'plate0': f['slab']['plate'], 'rooms': f['rooms']['spaces'],
                                          'named': f['rooms']['named'], 'shapes': f['rooms'].get('shapes'),
                                          'several': f['rooms']['several'],
                                          'notARoom': [r.get('area') for r in f['rooms']['open'] if r.get('why') == 'not a room'],
                                          'namesInSmallRooms': [(r.get('name'), r.get('area')) for r in f['rooms']['open']
                                                                if r.get('why') == 'placed by distance'],
                                          'closings': {c: sum(1 for x in f['slab']['closings'] if x.get('kind') == c) for c in ('doorway', 'bridge')},
                                          'inShould': (lambda lo: lo and lo[2] <= f['slab']['plate'] <= lo[3])(PLATE.get((n, k))),
                                          'inMust': (lambda lo: lo and lo[0] <= f['slab']['plate'] <= lo[1])(PLATE.get((n, k)))}
                                      for k, f in v['report']['floors'].items()},
                           'probes': probes(n, case),
                           'singleLineFlagsAfter': sum(1 for f in (overlay_of(case) or {'flags': []})['flags'] if f['kind'] == 'single-line'),
                           'singleLineFlagsBefore': sum(1 for f in (overlay_of(NEW[n]) or {'flags': []})['flags'] if f['kind'] == 'single-line')}
    res['ra3'] = {'bankNames': bank_names(), 'housePoints': house_points()}
    res['ra4'] = {'bankWrittenAreas': bank_written_areas(), 'prototypes': prototype_slabs()}
    res['ra6'] = {n: probes(n, NEW[n]) for n in ('house', 'suite', 'tower', 'suite-revit')}
    res['ra7'] = {'suiteKey': suite_names(),
                  'newSuiteNames': sorted({r['name'] for r in version('suite-revit-rooms')['model']['rooms']}),
                  'bankLabels': len(version('bank-rooms')['model']['rooms'])}
    # RA-11: the new-rule versions' Max scripts
    ms = {}
    for n, pid in NEW.items():
        d = DATA / 'projects' / pid / 'versions' / '1' / 'downloads'
        f = next(iter(sorted(d.glob('*.ms'))), None)
        if f is None:
            continue
        t = f.read_text(encoding='utf-8', errors='replace')
        ms[n] = {'file': f.name, 'tread': t.count('#tread'), 'landing': t.count('#landing'), 'ceiling': t.count('#ceiling'),
                 'slab': t.count('#slab'), 'poly': sum(t.count(w) for w in ('convertToPoly', 'Edit_Poly', 'editable_poly', 'Editable_Poly')),
                 'storeyFit': '_storey"' in t, 'ceilingsHiddenNote': 'Ceilings are on hidden layers' in t, 'risersLine': next((l.strip() for l in t.splitlines() if 'risers of' in l), None)}
    res['ra11'] = ms
    res['ra13'] = maybe(W / 'out' / 'ra13' / 'record.json')
    res['ra14'] = {'new': {n: times(W / 'out', pid) for n, pid in NEW.items()},
                   'aside': {n: times(W / 'out', c, 'build2') for n, c in ASIDE.items()},
                   'old': {n: times(W / 'acc' / 'out', c) for n, c in (('bank', 'bank-reupload'), ('house', 'house'), ('suite', 'suite'),
                                                                     ('tower', 'tower'), ('suite-revit', 'suite-revit'))},
                   'fpsGpu': gpu_fps(),
                   'node': {f.stem: maybe(f) for f in sorted((W / 'node-rooms').glob('real-timing-*.json'))}}
    res['walks'] = walk_reports()
    res['stairs'] = stairs_reports()
    # RA-1: the old acceptance step's records (a fresh seed, the upload milestone's eleven cases)
    old = {}
    for rec_path in sorted((W / 'acc' / 'out').glob('*/record.json')):
        r = load(rec_path)
        old[r.get('case') or rec_path.parent.name] = {'ok': r.get('ok'), 'error': r.get('error'),
                                                      'stamp': (r.get('save') or {}).get('stamp')}
    a9 = maybe(W / 'acc' / 'out' / 'a9' / 'record.json') or {}
    s3 = maybe(W / 'acc' / 'out' / 'a9' / 'build3' / 'settings.json')
    if a9.get('fixes') and s3:                  # a9.py's comparison made again from its files (floorPast's default filled)
        def three(fx):
            o = {k: fx.get(k) for k in ('setAside', 'openings', 'outlineEdges')}
            o['setAside'] = [{**x, 'floorPast': x.get('floorPast', False)} for x in o['setAside'] or []]
            return o
        a9['reuploadFixesEqualAgain'] = three(s3['fixes']) == three(a9['fixes'])
    res['ra1'] = {'cases': old, 'a1': maybe(W / 'acc' / 'out' / '_a1' / 'a1.json'),
                  'a9': {k: v for k, v in a9.items() if k in ('ok', 'error', 'reuploadFixesEqual', 'reuploadFixesEqualAgain',
                                                             'model3EqualsModel2', 'reuploadNewFixLists', 'report3fixes')}}
    g = W / 'logs' / 'rooms-golden.txt'
    res['golden'] = g.read_text(encoding='utf-8', errors='replace')[-3000:] if g.exists() else None
    out = W / 'rooms-result.json'
    out.write_text(json.dumps(res, indent=1, ensure_ascii=False, default=str), encoding='utf-8')
    # a short summary
    for n, d in res['drawings'].items():
        print(n, d['stamp'], d['modelFormat'], 'old', d['oldStamp'])
        for k, f in d['floors'].items():
            print(f'   {k}: plate0 {f["plate0"]} (old slab parts {f["oldSlabParts"]}, new {f["newSlabParts"]}) must {f["plateBounds"] and f["plateBounds"]["must"]} '
                  f'should {f["plateBounds"] and f["plateBounds"]["inShould"]}; rooms {f["rooms"]} named {f["named"]}; holes '
                  f'{[(h["what"], h["area"]) for h in f["holesCut"]]}; ceilings {f["ceilingParts"]} ({f["ceilingArea"]} m2); '
                  f'climb {[s["id"] for s in f["stairsClimb"]]}; lines {len(f["stairsLines"])}')
    print('aside', json.dumps(res['aside'], default=str)[:1500])
    print('bank names', res['ra3']['bankNames']['ok'], '/', res['ra3']['bankNames']['of'], 'suite key', res['ra7']['suiteKey']['ok'], '/', res['ra7']['suiteKey']['of'])
    print('result', out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
