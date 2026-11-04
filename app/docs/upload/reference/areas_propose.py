"""Propose sheet areas (separate drawings on one sheet) from a prims cache: occupied 1 m cells, grown by GAP m, connected.
Usage: python areas_propose.py <prims.pkl> [gap_m] [layer substring to use, e.g. WALL]"""
import collections, math, pickle, sys
D = pickle.load(open(sys.argv[1], 'rb'))
gap = float(sys.argv[2]) if len(sys.argv) > 2 else 3.0
only = sys.argv[3].upper() if len(sys.argv) > 3 else None
cells = collections.Counter()
for d in D['items']:
    if d['t'] in ('TEXT', 'MTEXT', 'ATTRIB', 'INSERT'): continue
    if only and only not in d['lay'].upper(): continue
    P = d.get('pts') or [q for l in d.get('loops', []) for q in l]
    for x, y in P[:: max(1, len(P) // 20)]:
        cells[(math.floor(x), math.floor(y))] += 1
occ = {c for c, n in cells.items()}
g = int(math.ceil(gap))
seen, comps = set(), []
for c in occ:
    if c in seen: continue
    stack, comp = [c], []
    seen.add(c)
    while stack:
        x, y = stack.pop(); comp.append((x, y))
        for dx in range(-g, g + 1):
            for dy in range(-g, g + 1):
                q = (x + dx, y + dy)
                if q in occ and q not in seen: seen.add(q); stack.append(q)
    xs = [p[0] for p in comp]; ys = [p[1] for p in comp]
    comps.append((sum(cells[p] for p in comp), [min(xs), min(ys), max(xs) + 1, max(ys) + 1]))
comps.sort(key=lambda c: -c[0])
for n, b in comps[:12]: print(f'{n:7} points  box {b}  size {b[2] - b[0]} x {b[3] - b[1]} m')
print(len(comps), 'areas in all')
