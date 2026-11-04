"""Score detected openings against an answer key (the Phase 0 gate figure: openings right with no manual fixing).

Usage: python score.py <answer_key.json> <detected.json> [--out report.json] [--quiet]
Both files: {"openings": [{"id", "floor", "kind": "door"|"window"|"passage", "a": [x, y], "b": [x, y], ...}, ...]}
in drawing metres. "floor" groups the openings (e.g. 'sukhumvit:ground', 'presidential:suite', 'bank:L1').

Matching, one to one, per floor, nearest first: a detection matches a key opening when its centre is within
max(0.30 m, 0.30 x key width) of the key centre and the two lie along the same wall (angle within 15 degrees).
For a matched pair:
  width right = |width difference| <= max(0.10 m, 0.10 x key width)
  ends right  = each detected end within 0.15 m of the nearest key end
  class right = both walkable (door or passage) or both window
  kind right  = the same kind (door / passage / window)
RIGHT (the gate) = matched and width right and class right. Door vs passage mix-ups are reported, not failed: both
are walkable gaps, and the difference (a lintel or not) is a height setting.
Key flags: "optional": true = not counted either way (found -> reported as optional found, never as extra; missed ->
not a miss): passage mouths and disputed items in a provisional key. "eitherKind": true = door or window both count as
the right class (floor-to-ceiling sliding glazing that the plan cannot settle; both become glass in 3D).
"""
import argparse, json, math, sys
from collections import defaultdict


def centre(o): return ((o['a'][0] + o['b'][0]) / 2, (o['a'][1] + o['b'][1]) / 2)
def width(o): return math.dist(o['a'], o['b'])
def angle(o): return math.degrees(math.atan2(o['b'][1] - o['a'][1], o['b'][0] - o['a'][0])) % 180
def walkable(o): return o['kind'] in ('door', 'passage')


def same_wall(k, d):
    if width(k) < 1e-6 or width(d) < 1e-6: return True
    da = abs(angle(k) - angle(d)) % 180
    return min(da, 180 - da) <= 15


def match(keys, dets):
    pairs = []
    for i, k in enumerate(keys):
        tol = max(0.30, 0.30 * width(k))
        for j, d in enumerate(dets):
            dist = math.dist(centre(k), centre(d))
            if dist <= tol and same_wall(k, d): pairs.append((dist, i, j))
    pairs.sort()
    ki, dj, out = set(), set(), []
    for dist, i, j in pairs:
        if i in ki or j in dj: continue
        ki.add(i); dj.add(j); out.append((i, j, dist))
    return out


def score(key, det):
    K, D = defaultdict(list), defaultdict(list)
    for o in key['openings']: K[o.get('floor', '?')].append(o)
    for o in det['openings']: D[o.get('floor', '?')].append(o)
    floors = sorted(set(K) | set(D))
    rep = {'floors': {}, 'total': {}}
    tot = defaultdict(int)
    for f in floors:
        allkeys, dets = K.get(f, []), D.get(f, [])
        keys = [o for o in allkeys if not o.get('optional')]
        opt = [o for o in allkeys if o.get('optional')]
        m = match(keys, dets)
        used = {j for _, j, _ in m}
        rest = [j for j in range(len(dets)) if j not in used]
        m_opt = match(opt, [dets[j] for j in rest])
        opt_found = [{'key': opt[i].get('id'), 'det': dets[rest[j]].get('id')} for i, j, _ in m_opt]
        opt_used = {rest[j] for _, j, _ in m_opt}
        rows = []
        n = defaultdict(int)
        for i, j, dist in m:
            k, d = keys[i], dets[j]
            wk = width(k)
            w_ok = abs(width(d) - wk) <= max(0.10, 0.10 * wk)
            e = min(max(math.dist(d['a'], k['a']), math.dist(d['b'], k['b'])), max(math.dist(d['a'], k['b']), math.dist(d['b'], k['a'])))
            e_ok = e <= 0.15
            c_ok = walkable(k) == walkable(d) or bool(k.get('eitherKind') and d['kind'] in ('door', 'window'))
            kind_ok = k['kind'] == d['kind']
            right = w_ok and c_ok
            n['matched'] += 1; n['width'] += w_ok; n['ends'] += e_ok; n['class'] += c_ok; n['kind'] += kind_ok; n['right'] += right
            rows.append({'key': k.get('id'), 'det': d.get('id'), 'kindKey': k['kind'], 'kindDet': d['kind'], 'centreOff': round(dist, 3),
                         'widthKey': round(wk, 3), 'widthDet': round(width(d), 3), 'endErr': round(e, 3),
                         'widthOk': w_ok, 'endsOk': e_ok, 'classOk': c_ok, 'kindOk': kind_ok, 'right': right})
        mk = {i for i, _, _ in m}; md = {j for _, j, _ in m}
        missed = [{'key': keys[i].get('id'), 'kind': keys[i]['kind'], 'at': [round(v, 3) for v in centre(keys[i])], 'width': round(width(keys[i]), 3),
                   'subtype': keys[i].get('subtype', '')} for i in range(len(keys)) if i not in mk]
        extra = [{'det': dets[j].get('id'), 'kind': dets[j]['kind'], 'at': [round(v, 3) for v in centre(dets[j])], 'width': round(width(dets[j]), 3),
                  'why': dets[j].get('evidence', '')} for j in range(len(dets)) if j not in md and j not in opt_used]
        nk, nd = len(keys), len(dets) - len(opt_used)
        fr = {'keyCount': nk, 'detCount': nd, 'optionalKeys': len(opt), 'optionalFound': opt_found, **{k: v for k, v in n.items()},
              'recall': round(n['matched'] / nk, 3) if nk else None, 'precision': round(n['matched'] / nd, 3) if nd else None,
              'rightShare': round(n['right'] / nk, 3) if nk else None,
              'byKind': {}, 'missed': missed, 'extra': extra, 'pairs': rows}
        for kind in ('door', 'window', 'passage'):
            kk = [o for o in keys if o['kind'] == kind]
            if not kk: continue
            ids = {o.get('id') for o in kk}
            rr = sum(1 for r in rows if r['key'] in ids and r['right'])
            fr['byKind'][kind] = {'key': len(kk), 'right': rr, 'share': round(rr / len(kk), 3)}
        rep['floors'][f] = fr
        tot['key'] += nk; tot['det'] += nd; tot['matched'] += n['matched']; tot['right'] += n['right']
    rep['total'] = {'keyCount': tot['key'], 'detCount': tot['det'], 'matched': tot['matched'], 'right': tot['right'],
                    'recall': round(tot['matched'] / tot['key'], 3) if tot['key'] else None,
                    'precision': round(tot['matched'] / tot['det'], 3) if tot['det'] else None,
                    'rightShare': round(tot['right'] / tot['key'], 3) if tot['key'] else None}
    return rep


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('key'); ap.add_argument('det'); ap.add_argument('--out'); ap.add_argument('--quiet', action='store_true')
    a = ap.parse_args()
    rep = score(json.load(open(a.key, encoding='utf-8')), json.load(open(a.det, encoding='utf-8')))
    if a.out: json.dump(rep, open(a.out, 'w', encoding='utf-8'), indent=1)
    for f, r in rep['floors'].items():
        print(f"{f:24} key {r['keyCount']:3}  detected {r['detCount']:3}  matched {r.get('matched', 0):3}  right {r.get('right', 0):3}"
              f"  recall {r['recall']}  precision {r['precision']}  RIGHT {r['rightShare']}  " +
              '  '.join(f"{k}: {v['right']}/{v['key']}" for k, v in r['byKind'].items()) +
              (f"  (optional {len(r['optionalFound'])}/{r['optionalKeys']} found)" if r['optionalKeys'] else ''))
        if not a.quiet:
            for x in r['missed']: print(f"    missed {x['key']} {x['kind']} at {x['at']} w {x['width']} {x['subtype']}")
            for x in r['extra']: print(f"    extra  {x['det']} {x['kind']} at {x['at']} w {x['width']}")
            for p in r['pairs']:
                if not p['right'] or not p['kindOk']:
                    print(f"    wrong  {p['key']}~{p['det']} kind {p['kindKey']}/{p['kindDet']} width {p['widthKey']}/{p['widthDet']} ends {p['endErr']}")
    t = rep['total']
    print(f"TOTAL key {t['keyCount']} detected {t['detCount']} matched {t['matched']} right {t['right']}  recall {t['recall']}  precision {t['precision']}  RIGHT {t['rightShare']}  (gate: >= 0.80)")


if __name__ == '__main__':
    sys.exit(main())
