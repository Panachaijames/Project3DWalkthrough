"""Compare two detector outputs: python cmp_ops.py A.json B.json -> openings only in A, only in B, and changed fields of matched ones."""
import json, sys, math
A = json.load(open(sys.argv[1], encoding='utf-8'))['openings']
B = json.load(open(sys.argv[2], encoding='utf-8'))['openings']
def key(o): return (o['floor'], o['kind'], round((o['a'][0] + o['b'][0]) / 2, 2), round((o['a'][1] + o['b'][1]) / 2, 2))
def mid(o): return ((o['a'][0] + o['b'][0]) / 2, (o['a'][1] + o['b'][1]) / 2)
usedB = set()
onlyA, changed = [], []
for o in A:
    best = None
    for j, q in enumerate(B):
        if j in usedB or q['floor'] != o['floor']: continue
        d = math.dist(mid(o), mid(q))
        if d < 0.3 and (best is None or d < best[0]): best = (d, j)
    if best is None: onlyA.append(o); continue
    usedB.add(best[1]); q = B[best[1]]
    diff = {k: (o.get(k), q.get(k)) for k in set(o) | set(q) if k not in ('id',) and o.get(k) != q.get(k)}
    if diff: changed.append((o['id'], q['id'], diff))
onlyB = [q for j, q in enumerate(B) if j not in usedB]
print('only in A:', [(o['id'], o['kind'], o['width']) for o in onlyA])
print('only in B:', [(o['id'], o['kind'], o['width']) for o in onlyB])
for i, j, d in changed:
    print('changed', i, '->', j, {k: v for k, v in d.items()})
