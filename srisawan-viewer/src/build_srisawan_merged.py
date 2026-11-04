"""Srisawan: merge traced wall segments into continuous solids (no seams, clean corners).

Same source and sizes as generate_maxscript.py (srisawan-rebuild): pixel -> metre transform,
wall thickness per kind, floor levels and heights. Floor 6 comes from floor6-dxf.
"""
import json, math, re, collections
import ezdxf
from shapely.geometry import LineString, LinearRing, MultiLineString, Point, Polygon, MultiPolygon
from shapely.ops import linemerge, unary_union
from shapely.strtree import STRtree

ROOT = 'C:/Users/DWP2/Desktop/Project walkthrough/'
g = json.load(open(ROOT + 'srisawan-rebuild/model_geometry.json', encoding='utf-8'))
S = g['scale']; d = g['data']

def xy(p):  # identical to generate_maxscript.py
    return ((p[0] - 754) * S, (301 - p[1]) * S)

THICK = {'wall': 0.18, 'core': 0.24, 'envelope': 0.22, 'glass': 0.06}
LEVEL = {'L1': 0.0, 'L2': 5.0, 'F6': 0.0}
HEIGHT = {'L1': 4.0, 'L2': 4.0, 'F6': 4.0}
PRIORITY = ['core', 'envelope', 'wall', 'glass']   # earlier kinds win where solids overlap
SNAP = 0.001        # 1 mm grid so shared end points match exactly
TOUCH = 0.06        # a wall end within 6 cm of another wall counts as joined
CLOSE = 0.03        # closes hairline gaps (< 6 cm) between touching pieces

def zone_of(name):
    m = re.match(r'SR_L\d_(.+?)_\d{3}(?:_\d+_\d+)?$', name)
    return (m.group(1) if m else name).replace('_', ' ')

# ---- collect raw segments: (floor, kind) -> [(a, b, zone)] ----
raw = collections.defaultdict(list)
for s in g['segments']:
    raw[(f"L{s['level']}", s['kind'])].append((xy(s['a']), xy(s['b']), zone_of(s['name'])))
doc = ezdxf.readfile(ROOT + 'floor6-dxf/Srisawan_Floor6_Interior_Walls.dxf')
for e in doc.modelspace().query('LINE'):
    if e.dxf.layer == 'AXIS_REFERENCE':
        continue
    kind = 'core' if e.dxf.layer == 'LIFT_CORE_REFERENCE' else 'wall'
    zone = 'Floor 6 lift core (reference)' if kind == 'core' else 'Floor 6 interior wall'
    raw[('F6', kind)].append(((e.dxf.start.x, e.dxf.start.y), (e.dxf.end.x, e.dxf.end.y), zone))

def q(p):
    return (round(p[0] / SNAP) * SNAP, round(p[1] / SNAP) * SNAP)

def chains_of(segs):
    lines = [LineString([q(a), q(b)]) for a, b, _ in segs if math.dist(q(a), q(b)) > 1e-6]
    merged = linemerge(MultiLineString(lines))
    return list(merged.geoms) if hasattr(merged, 'geoms') else [merged]

def turn_at(pts, i):
    """Signed turn (degrees) at vertex i of a closed or open point list (neighbours wrap)."""
    n = len(pts); p, v, q = pts[(i - 1) % n], pts[i], pts[(i + 1) % n]
    a1 = math.atan2(v[1] - p[1], v[0] - p[0]); a2 = math.atan2(q[1] - v[1], q[0] - v[0])
    return math.degrees((a2 - a1 + math.pi) % (2 * math.pi) - math.pi)

def smooth_curves(coords, closed, iters=3):
    """Round off traced curves: a vertex is smoothed only if it is a gentle bend (3-50 deg) next to
    another gentle bend in the same direction, i.e. part of a curve. 90-degree corners and lone
    chamfers stay sharp; open-chain end points never move. Chaikin corner cutting, 3 passes."""
    pts = [tuple(p) for p in (coords[:-1] if closed else coords)]
    for _ in range(iters):
        n = len(pts)
        idx = range(n) if closed else range(1, n - 1)
        turns = {i: turn_at(pts, i) for i in idx}
        soft = {i for i, t in turns.items() if 3 < abs(t) < 50}
        curve = {i for i in soft if any(j in soft and turns[j] * turns[i] > 0 for j in ((i - 1) % n, (i + 1) % n))}
        if not curve:
            break
        new = []
        for i in range(n):
            if i in curve:
                p, v, q = pts[(i - 1) % n], pts[i], pts[(i + 1) % n]
                new.append((v[0] + 0.25 * (p[0] - v[0]), v[1] + 0.25 * (p[1] - v[1])))
                new.append((v[0] + 0.25 * (q[0] - v[0]), v[1] + 0.25 * (q[1] - v[1])))
            else:
                new.append(pts[i])
        pts = new
        stats[('all', 'curve vertices smoothed')] += len(curve)
    return pts + [pts[0]] if closed else pts

def extend_end(coords, at_start, by):
    (x0, y0), (x1, y1) = (coords[1], coords[0]) if at_start else (coords[-2], coords[-1])
    L = math.hypot(x1 - x0, y1 - y0)
    if L < 1e-9:
        return coords
    p = (x1 + (x1 - x0) / L * by, y1 + (y1 - y0) / L * by)
    return [p] + coords[1:] if at_start else coords[:-1] + [p]

stats = collections.Counter()
solids = {}   # (floor, kind) -> shapely geometry
for floor in ('L1', 'L2', 'F6'):
    kinds = [k for k in PRIORITY if raw.get((floor, k))]
    chains = {k: chains_of(raw[(floor, k)]) for k in kinds}
    every = [(k, c) for k in kinds for c in chains[k]]
    tree = STRtree([c for _, c in every])
    for k in kinds:
        t = THICK[k]; parts = []
        for ch in chains[k]:
            coords = smooth_curves(list(ch.coords), ch.is_closed and len(ch.coords) >= 4)
            if ch.is_closed and len(coords) >= 4:
                parts.append(LinearRing(coords).buffer(t / 2, join_style='mitre', mitre_limit=3.0))
                stats[(floor, 'closed loops')] += 1
                continue
            for at_start in (True, False):
                end = Point(coords[0] if at_start else coords[-1])
                touching = False
                for j in tree.query(end.buffer(TOUCH)):
                    other = every[j][1]
                    if other is ch:
                        # touching its own body also counts (e.g. a hooked wall): ignore the end
                        # point and its neighbouring segment, which always touch the end
                        body = coords[2:] if at_start else coords[:-2]
                        if len(body) >= 2 and LineString(body).distance(end) < TOUCH:
                            touching = True
                        continue
                    if other.distance(end) < TOUCH:
                        touching = True
                        break
                if touching:
                    # half the thickest wall it may meet, so L and T joints close fully
                    coords = extend_end(coords, at_start, 0.12)
                    stats[(floor, 'joined ends')] += 1
                else:
                    stats[(floor, 'free ends')] += 1
            parts.append(LineString(coords).buffer(t / 2, cap_style='flat', join_style='mitre', mitre_limit=3.0))
        u = unary_union(parts).buffer(CLOSE, join_style='mitre').buffer(-CLOSE, join_style='mitre')
        solids[(floor, k)] = u
        stats[(floor, k + ' chains')] = len(chains[k]); stats[(floor, k + ' segments')] = len(raw[(floor, k)])
    # remove overlaps between kinds (core > envelope > wall > glass)
    taken = None
    for k in kinds:
        geom = solids[(floor, k)]
        if taken is not None:
            geom = geom.difference(taken)
        taken = solids[(floor, k)] if taken is None else unary_union([taken, solids[(floor, k)]])
        solids[(floor, k)] = geom.simplify(0.002, preserve_topology=True)   # light, keeps curves round

def polys(geom):
    if geom.is_empty:
        return []
    items = geom.geoms if hasattr(geom, 'geoms') else [geom]
    out = []
    for p in items:
        # drop slivers left where one kind is trimmed against another (< 150 cm2, or < 2 cm wide)
        if isinstance(p, Polygon) and p.area > 0.015 and 2 * p.area / p.length > 0.02:
            out.append(p)
        elif isinstance(p, Polygon):
            stats[('all', 'slivers dropped')] += 1
    return out

# ---- centre each building on its own footprint (hospital L1+L2, floor 6 separately) ----
def bounds(keys):
    b = unary_union([solids[k] for k in keys if k in solids]).bounds
    return ((b[0] + b[2]) / 2, (b[1] + b[3]) / 2, b[2] - b[0], b[3] - b[1])
hosp = bounds([k for k in solids if k[0] in ('L1', 'L2')])
f6 = bounds([k for k in solids if k[0] == 'F6'])
def shift(floor):
    return hosp if floor in ('L1', 'L2') else f6

out = {'solids': {}, 'segments': {}, 'zones': [], 'slabs': {}, 'size': [round(hosp[2], 1), round(hosp[3], 1)],
       'size6': [round(f6[2], 1), round(f6[3], 1)], 'levels': LEVEL, 'heights': HEIGHT,
       # add these back to get original coordinates (metres, origin at the lift core as in the MaxScript)
       'offset': {'hosp': [hosp[0], hosp[1]], 'f6': [f6[0], f6[1]]}}
zone_ix = {}
for (floor, k), geom in solids.items():
    cx, cy = shift(floor)[:2]
    rings = []
    for p in polys(geom):
        ext = [[round(x - cx, 3), round(y - cy, 3)] for x, y in list(p.exterior.coords)[:-1]]
        holes = [[[round(x - cx, 3), round(y - cy, 3)] for x, y in list(r.coords)[:-1]] for r in p.interiors]
        rings.append({'o': ext, 'h': holes})
    out['solids'][f'{floor}:{k}'] = rings
    segs = []
    for a, b, zone in raw[(floor, k)]:
        if zone not in zone_ix:
            zone_ix[zone] = len(out['zones']); out['zones'].append(zone)
        segs.append([round(a[0] - cx, 3), round(a[1] - cy, 3), round(b[0] - cx, 3), round(b[1] - cy, 3), zone_ix[zone]])
    out['segments'][f'{floor}:{k}'] = segs
    stats[(floor, k + ' solids')] = len(rings)

# slabs exactly as in the MaxScript: L1 outline; L2 outline + 2 voids + 6 shaft holes
cx, cy = hosp[:2]
def ring(pts):
    return [[round(x - cx, 3), round(y - cy, 3)] for x, y in pts]
out['slabs']['L1'] = {'outer': ring(xy(p) for p in d['outlines']['1']), 'holes': [], 'z': -0.25}
out['slabs']['L2'] = {'outer': ring(xy(p) for p in d['outlines']['2']),
                      'holes': [ring(xy(p) for p in h) for h in d['voids'] + g['shaft_holes']], 'z': 4.75}

json.dump(out, open('srisawan3d_merged.json', 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
for k in sorted(stats):
    print(k, stats[k])
print('hospital', out['size'], 'm | floor 6', out['size6'], 'm')
