"""Combine per-part answer keys into one key per floor, removing duplicates where neighbouring parts overlap.

Usage: python combine_keys.py <spec.json> <out.json>
spec: {"parts": [{"file": "<answer_key.json from a reconciler or labeller>", "floor": "sukhumvit:ground",
                  "box": [x0, y0, x1, y1], "own": [x0, y0, x1, y1]}, ...]}
  box = the box the part was labelled in (with its overlap); own = the part's share without the overlap (the split
  line in the middle of the overlap). Each output opening gets "floor" and "part"; glass walls and uncertain items are
  carried over the same way.
Two entries from different parts of the same floor are the same opening when their centres are within 0.4 m and
they lie along the same wall (15 degrees): the one whose centre falls in its own part's share is kept.
"""
import json, math, sys
sys.path.insert(0, __import__('os').path.dirname(__file__))
from score import centre, same_wall


def inside(p, r): return r[0] <= p[0] <= r[2] and r[1] <= p[1] <= r[3]


def main(spec_path, out_path):
    spec = json.load(open(spec_path, encoding='utf-8'))
    floors = {}
    for part in spec['parts']:
        data = json.load(open(part['file'], encoding='utf-8'))
        fl = floors.setdefault(part['floor'], {'openings': [], 'glassWalls': [], 'uncertain': [], 'rejected': []})
        for o in data.get('openings', []):
            fl['openings'].append({**o, 'floor': part['floor'], 'part': part['file'], '_own': inside(centre(o), part['own'])})
        for g in data.get('glassWalls', []): fl['glassWalls'].append({**g, 'floor': part['floor']})
        for u in data.get('uncertain', []): fl['uncertain'].append({**u, 'floor': part['floor']})
        for r in data.get('rejected', []): fl['rejected'].append({**r, 'floor': part['floor']})
    out = {'openings': [], 'glassWalls': [], 'uncertain': [], 'rejected': [], 'duplicatesRemoved': []}
    for f, fl in floors.items():
        keep = []
        for o in sorted(fl['openings'], key=lambda o: not o['_own']):          # own-share entries first
            dup = next((k for k in keep if k['part'] != o['part'] and math.dist(centre(k), centre(o)) <= 0.4 and same_wall(k, o)), None)
            if dup:
                out['duplicatesRemoved'].append({'kept': dup['id'], 'dropped': o['id'], 'floor': f,
                                                 'kindsAgree': dup['kind'] == o['kind'],
                                                 'centreOff': round(math.dist(centre(dup), centre(o)), 3)})
                continue
            keep.append(o)
        for o in keep: o.pop('_own', None)
        out['openings'] += keep
        out['glassWalls'] += fl['glassWalls']; out['uncertain'] += fl['uncertain']; out['rejected'] += fl['rejected']
    json.dump(out, open(out_path, 'w', encoding='utf-8'), indent=1)
    by = {}
    for o in out['openings']: by.setdefault(o['floor'], {}).setdefault(o['kind'], 0); by[o['floor']][o['kind']] += 1
    for f, c in by.items(): print(f, c, 'total', sum(c.values()))
    print('duplicates removed:', len(out['duplicatesRemoved']), [d for d in out['duplicatesRemoved'] if not d['kindsAgree']])


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
