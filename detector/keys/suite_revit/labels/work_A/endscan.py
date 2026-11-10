"""Wall-end scan (labeller A, geometry first): union of the wall fills (layers 0, A-WALL, S-COLS; furniture fills and
specks left out), then for every short cap edge of the union cast a ray along its outward normal and report the
distance to the next wall fill, glass line (A-GLAZ-*, 10 mm layer-0 glass) or the drawing edge."""
import sys; sys.path.insert(0, '.')
from load import *
from shapely.geometry import Polygon, LineString, Point, MultiPolygon
from shapely.ops import unary_union
D = load()
SKIP = {'4FF1', '502C', '4FD2', '4E08', '4E09', '58C5', '58C6'}     # sofa fills, 5 mm / 3 mm specks
polys = []
for d in D['items']:
    if d['lay'] not in ('0', 'A-WALL', 'S-COLS'): continue
    if d['h'] in SKIP and d['path'] == '': continue
    if d['t'] == 'HATCH': loops = d['loops']
    elif d['t'] == 'SOLID': loops = [d['pts']]
    else: continue
    for L in loops:
        if len(L) < 3: continue
        P = Polygon(L)
        if not P.is_valid: P = P.buffer(0)
        if P.area < 1e-5: continue
        polys.append(P.buffer(0.0008, join_style=2))
U = unary_union(polys).buffer(-0.0008, join_style=2).simplify(0.0006, preserve_topology=True)
print('union parts', len(U.geoms) if hasattr(U, 'geoms') else 1)
# obstacles for the rays: the wall union + glass lines
glass = []
for d in D['items']:
    if d['t'] in ('LINE', 'LWPOLYLINE') and d['lay'].startswith('A-GLAZ'):
        glass.append(LineString(d['pts']))
G = unary_union(glass)
rings = []
for g in (U.geoms if hasattr(U, 'geoms') else [U]):
    rings.append(list(g.exterior.coords))
    for i in g.interiors: rings.append(list(i.coords))
out = []
for R in rings:
    n = len(R) - 1
    for i in range(n):
        p, q = R[i], R[i + 1]
        L = math.dist(p, q)
        if not (0.03 <= L <= 0.6): continue
        # adjacent edges
        pp, qq = R[i - 1], R[(i + 2) % n]
        def unit(a, b):
            l = math.dist(a, b); return ((b[0] - a[0]) / l, (b[1] - a[1]) / l) if l > 0 else (0, 0)
        e = unit(p, q); e0 = unit(pp, p); e2 = unit(q, qq)
        # a cap: both neighbours perpendicular to the cap and anti-parallel to each other
        if abs(e[0] * e0[0] + e[1] * e0[1]) > 0.2 or abs(e[0] * e2[0] + e[1] * e2[1]) > 0.2: continue
        if e0[0] * e2[0] + e0[1] * e2[1] > -0.9: continue
        if math.dist(pp, p) < 0.02 or math.dist(q, qq) < 0.02: continue
        # outward normal: direction of e2 is away from the solid? the neighbour edge after q runs back into the wall
        nrm = (-e2[0], -e2[1])          # cap faces opposite to the direction the next edge runs
        m = ((p[0] + q[0]) / 2, (p[1] + q[1]) / 2)
        far = (m[0] + nrm[0] * 4.0, m[1] + nrm[1] * 4.0)
        start = (m[0] + nrm[0] * 0.003, m[1] + nrm[1] * 0.003)
        ray = LineString([start, far])
        best = None
        for obst, kind in ((U, 'wall'), (G, 'glass')):
            x = ray.intersection(obst)
            if x.is_empty: continue
            dd = Point(start).distance(x) + 0.003
            if best is None or dd < best[0]: best = (dd, kind)
        out.append((round(m[0], 3), round(m[1], 3), round(L, 3), (round(nrm[0], 2), round(nrm[1], 2)), best and round(best[0], 3), best and best[1]))
out.sort(key=lambda r: (r[4] if r[4] else 99))
for r in out:
    if r[4] is not None and r[4] <= 3.2: print(*r)
print('caps with no hit within 4 m:')
for r in out:
    if r[4] is None: print('  ', *r)
