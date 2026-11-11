"""UR (V1-3): the house's opening heads and sills and its lintels, upload against the prototype (read-only).

    python -B house_heads.py <prototype model.json> <upload model.json>
"""
import collections
import json
import math
import sys


def load(p):
    return json.load(open(p, encoding='utf-8'))


proto, up = load(sys.argv[1]), load(sys.argv[2])


def ops(m):
    return {o['id']: o for o in m['openings']}


po, uo = ops(proto), ops(up)


def key(o):
    return (o['floor'], round(o['x'], 1), round(o['y'], 1))


def lintel_kinds(m):
    by = {o['id']: o['kind'] for o in m['openings']}
    c = collections.Counter()
    for p in m['parts']:
        if p['kind'] != 'lintel':
            continue
        lab = (p.get('label') or '').split(' ')[0]
        c[(p['floor'], by.get(lab, '?'))] += 1
    return c


# match by floor and centre within 0.2 m (in the model frames: the upload's offset differs, so match by id order of the
# detector, which both share: the openings' ids are the detector's record ids)
same = [i for i in uo if i in po]
diff = []
for i in same:
    a, b = po[i], uo[i]
    if a['kind'] != b['kind']:
        continue
    if (a.get('head'), a.get('sill')) != (b.get('head'), b.get('sill')):
        diff.append((i, a['kind'], a.get('head'), a.get('sill'), b.get('head'), b.get('sill'), b.get('curtain')))
print(f'openings: prototype {len(po)}, upload {len(uo)}, same ids {len(same)}')
kinds = collections.Counter((d[1], d[6]) for d in diff)
print('head / sill differences by (kind, curtain):', dict(kinds))
for d in diff:
    if d[1] == 'window':
        print('  ', d)
cur = [o for o in up['openings'] if o['kind'] == 'window' and o.get('curtain')]
print('upload curtain windows:', len(cur), collections.Counter((o['floor'], o['head'], o['sill']) for o in cur))
print('lintels by (floor, opening kind): prototype', dict(lintel_kinds(proto)), 'upload', dict(lintel_kinds(up)))
