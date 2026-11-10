"""List every SOLID fill loop on the wall layers (0, A-WALL, S-COLS) with its oriented size."""
import sys; sys.path.insert(0, '.')
from load import *
from shapely.geometry import Polygon
D = load()
rows = []
for d in D['items']:
    if d['lay'] not in ('0', 'A-WALL', 'S-COLS'): continue
    if d['t'] == 'HATCH':
        loops = d['loops']
    elif d['t'] == 'SOLID':
        loops = [d['pts']]
    else:
        continue
    for L in loops:
        if len(L) < 3: continue
        P = Polygon(L)
        if not P.is_valid: P = P.buffer(0)
        r = P.minimum_rotated_rectangle
        c = list(r.exterior.coords)
        e1 = math.dist(c[0], c[1]); e2 = math.dist(c[1], c[2])
        th, ln = min(e1, e2), max(e1, e2)
        # direction of the long side
        if e1 >= e2: ang = math.degrees(math.atan2(c[1][1]-c[0][1], c[1][0]-c[0][0])) % 180
        else: ang = math.degrees(math.atan2(c[2][1]-c[1][1], c[2][0]-c[1][0])) % 180
        b = P.bounds
        rows.append((d['lay'], d['t'], d['h'], d['path'][:30], round(th, 4), round(ln, 3), round(ang, 1), [round(v, 3) for v in b], len(L), round(P.area / max(r.area, 1e-12), 2)))
rows.sort(key=lambda r: (r[0], r[7][1], r[7][0]))
for r in rows: print(*r)
print(len(rows))
