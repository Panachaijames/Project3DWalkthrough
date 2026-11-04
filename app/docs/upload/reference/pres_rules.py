import pickle, sys, collections, math
sys.path.insert(0, r'C:\Users\DWP2\Desktop\Project walkthrough\cad_test\src')
from merge_cad import strips, solidify
from shapely.geometry import Polygon, LineString, box, Point
from shapely.ops import unary_union
D = pickle.load(open(sys.argv[1], 'rb')); items = D['items']
E = [d for d in items if d.get('area') == 'suite']
def closed(d): return d.get('pts') and (d.get('closed') or math.dist(d['pts'][0], d['pts'][-1]) < 1e-3) and len(d['pts']) >= 4
rooms = [Polygon(d['pts']).buffer(0) for d in E if d['lay'] == 'Defpoints' and closed(d)]
edges = unary_union([r.exterior for r in rooms])
CORE_SIDE = [
    ([(203.775, -3485.706), (202.536, -3486.421)], 0.18),
    ([(202.536, -3486.421), (206.936, -3494.042)], 0.25),
    ([(206.98, -3496.20), (206.033, -3497.834), (204.963, -3499.686), (203.843, -3501.627), (201.019, -3506.518)], 0.25)]
for line, t in CORE_SIDE:
    L = LineString(line)
    cov = L.intersection(edges.buffer(0.03)).length
    print(f'core-side run {L.length:.2f} m (t {t}): {cov:.2f} m lies on a Defpoints room-outline edge (3 cm)')
# walls from the wall layer as the general builder would (fills, thin outlines, pairs 4-45 cm)
from shapely.geometry import MultiPolygon
def even_odd(loops):
    g = Polygon()
    for l in loops:
        if len(l) < 3: continue
        p = Polygon(l).buffer(0)
        if not p.is_empty: g = g.symmetric_difference(p)
    return g.buffer(0)
W = [d for d in E if d['lay'] == 'A-1.Netcat - tuong']
fills = [even_odd(d['loops']) for d in W if 'loops' in d]
thin, wide, segs = [], [], []
for d in W:
    if 'loops' in d or not d.get('pts'): continue
    if closed(d):
        g = Polygon(d['pts']).buffer(0)
        if g.area > 0 and 2 * g.area / g.length <= 0.35: thin.append(g)
        else: wide.append(round(g.area, 2))
        continue
    p = d['pts']; segs += [[a[0], a[1], b[0], b[1]] for a, b in zip(p, p[1:]) if math.dist(a, b) > 0.02]
rects, npair, nseg = strips(segs, 0.04, 0.45)
Wall = unary_union(solidify(fills + thin + rects, 0.03))
print('general wall solid area', round(Wall.area, 2), 'm2; fills', len(fills), 'thin', len(thin), 'wide outlines', wide, 'pairs', npair, 'of', nseg)
# room-outline edges with no wall within 0.35 m on either side
free = edges.difference(Wall.buffer(0.35))
parts = [g for g in getattr(free, 'geoms', [free]) if g.length > 0.5]
print('room-outline edge length', round(edges.length, 1), 'm; with no wall within 0.35 m:', round(sum(g.length for g in parts), 1), 'm in', len(parts), 'pieces')
for g in sorted(parts, key=lambda g: -g.length)[:12]:
    c = g.centroid; print(f'   {g.length:6.2f} m near ({c.x:.2f}, {c.y:.2f})')
# A-4. Dim as glass: pairs 5 mm-30 cm
dim = [d for d in E if d['lay'] == 'A-4. Dim' and d.get('pts') and d['depth'] == 0]
dsegs = [[a[0], a[1], b[0], b[1]] for d in dim for a, b in zip(d['pts'], d['pts'][1:]) if math.dist(a, b) > 0.02]
gr, ng, ns = strips(dsegs, 0.005, 0.30)
G = unary_union(gr)
oct_in = [d for d in E if d['h'] in ('1BB40C', '1BB40D')]
band = Polygon(oct_in[0]['pts'] + oct_in[1]['pts'][::-1]).buffer(0) if len(oct_in) == 2 else None
print('A-4. Dim depth-0 segments', ns, 'pairs', ng, 'paired area', round(G.area, 2), 'm2; octagon band area', round(band.area, 2) if band else None,
      '; paired area inside the band', round(G.intersection(band.buffer(0.01)).area, 2) if band else None, '; outside', round(G.difference(band.buffer(0.01)).area, 2) if band else None)
north = box(191.73, -3483.793, 202.46, -3483.756); south = box(190.715, -3506.556, 201.019, -3506.518)
for nm, g in (('north', north), ('south', south)):
    L = LineString([(g.bounds[0], (g.bounds[1] + g.bounds[3]) / 2), (g.bounds[2], (g.bounds[1] + g.bounds[3]) / 2)])
    print(f'{nm} glazing {L.length:.2f} m: on a room-outline edge (10 cm) {L.intersection(edges.buffer(0.10)).length:.2f} m; within 0.35 m of wall {L.intersection(Wall.buffer(0.35)).length:.2f} m')
rail = [d for d in E if d['lay'] == 'KT-Lancan' and d.get('pts')]
RL = unary_union([LineString(d['pts']) for d in rail if len(d['pts']) > 1])
for nm, g in (('north', north), ('south', south)):
    print(f'   {nm}: railing line within 0.5 m: {g.buffer(0.5).intersection(RL).length:.1f} m')
