"""DWG test house: turn double-line CAD walls into merged wall solids.

CAD draws each wall as two face lines. Pair each line with the nearest parallel line 4-45 cm away
(on each side), fill the strip between them, fuse everything, close the corner squares where two
walls meet, and tidy. Input: house3d.json from build3d.py (metres, continuous lines only).
"""
import json, math, collections
from shapely.geometry import LineString, Polygon
from shapely.ops import unary_union
from shapely.strtree import STRtree

ANG = math.radians(3)

def strips(segs, tmin, tmax):
    lines = [((x1, y1), (x2, y2)) for x1, y1, x2, y2 in segs if math.dist((x1, y1), (x2, y2)) > 0.02]
    geoms = [LineString(l) for l in lines]
    tree = STRtree(geoms)
    rects, paired = [], 0
    for i, (a, b) in enumerate(lines):
        dx, dy = b[0] - a[0], b[1] - a[1]; L = math.hypot(dx, dy); ux, uy = dx / L, dy / L; nx, ny = -uy, ux
        cands = []
        for j in tree.query(geoms[i].buffer(tmax)):
            if j == i: continue
            c, e = lines[j]
            ex, ey = e[0] - c[0], e[1] - c[1]; L2 = math.hypot(ex, ey)
            if abs((ux * ex + uy * ey) / L2) < math.cos(ANG): continue           # not parallel
            dc = (c[0] - a[0]) * nx + (c[1] - a[1]) * ny; de = (e[0] - a[0]) * nx + (e[1] - a[1]) * ny
            if abs(dc - de) > 0.02: continue                                       # drifts apart
            t = (dc + de) / 2
            if not (tmin <= abs(t) <= tmax): continue
            pc = (c[0] - a[0]) * ux + (c[1] - a[1]) * uy; pe = (e[0] - a[0]) * ux + (e[1] - a[1]) * uy
            lo, hi = max(0.0, min(pc, pe)), min(L, max(pc, pe))
            if hi - lo < 0.05: continue                                            # no real overlap
            cands.append((t, lo, hi))
        # keep only the nearest partner(s) on each side: the other face of the same wall
        for side in (1, -1):
            s = [c for c in cands if c[0] * side > 0]
            if not s: continue
            near = min(abs(c[0]) for c in s)
            for t, lo, hi in s:
                if abs(t) - near > 0.03: continue
                p0 = (a[0] + ux * lo, a[1] + uy * lo); p1 = (a[0] + ux * hi, a[1] + uy * hi)
                rects.append(Polygon([p0, p1, (p1[0] + nx * t, p1[1] + ny * t), (p0[0] + nx * t, p0[1] + ny * t)]))
                paired += 1
    return rects, paired, len(lines)

def solidify(rects, close):
    u = unary_union(rects)
    u = u.buffer(close, join_style='mitre').buffer(-close, join_style='mitre')   # closes corner squares
    u = u.simplify(0.005, preserve_topology=True)
    items = u.geoms if hasattr(u, 'geoms') else [u]
    return [p for p in items if isinstance(p, Polygon) and p.area > 0.01]

def main():
  D = json.load(open('house3d.json'))
  out = {'levels': D['levels'], 'tops': D['tops'], 'solids': {}, 'stairs': {}, 'plates': {}}
  for floor in ('ground', 'upper'):
    walls, nw, lw = strips(D['segments'].get(f'{floor}:wall', []), 0.04, 0.45)
    glass, ng, lg = strips(D['segments'].get(f'{floor}:glass', []) + D['segments'].get(f'{floor}:window', []), 0.02, 0.30)
    wall_polys = solidify(walls, 0.12)
    wall_union = unary_union(wall_polys)
    glass_polys = [p for p in solidify(glass, 0.04) if not p.is_empty]
    # glass never overlaps the opaque walls
    glass_polys = [q for p in glass_polys for q in ([p.difference(wall_union)] if True else [])]
    glass_polys = [g for p in glass_polys for g in (p.geoms if hasattr(p, 'geoms') else [p]) if isinstance(g, Polygon) and g.area > 0.005]
    # single-line items: wall lines with no parallel partner (not covered by any wall solid)
    covered = wall_union.buffer(0.04)
    singles, total_len, single_len = [], 0.0, 0.0
    for x1, y1, x2, y2 in D['segments'].get(f'{floor}:wall', []):
        ln = LineString([(x1, y1), (x2, y2)]); total_len += ln.length
        rest = ln.difference(covered)
        for part in (rest.geoms if hasattr(rest, 'geoms') else [rest]):
            if not part.is_empty and part.length > 0.2:
                singles.append(part.buffer(0.03, cap_style='flat')); single_len += part.length
    single_polys = solidify(singles, 0.01) if singles else []
    print(f"   {floor}: single-line items {round(single_len, 1)} m of {round(total_len, 1)} m wall lines ({round(100 * single_len / total_len)}%) -> {len(single_polys)} pieces")
    # Floor plates (approximate): the building outline = all walls fused, gaps under 3 m closed, rooms filled.
    shell = unary_union(wall_polys + glass_polys).buffer(1.5, join_style='mitre').buffer(-1.5, join_style='mitre')
    plates = [Polygon(p.exterior).simplify(0.02) for p in (shell.geoms if hasattr(shell, 'geoms') else [shell]) if isinstance(p, Polygon) and p.area > 4]
    out['plates'][floor] = [{'o': [[round(x, 3), round(y, 3)] for x, y in list(p.exterior.coords)[:-1]], 'h': []} for p in plates]
    print(f"   {floor}: floor plates {len(plates)}, area {round(sum(p.area for p in plates))} m2")
    for kind, polys in (('wall', wall_polys), ('glass', glass_polys), ('single', single_polys)):
        out['solids'][f'{floor}:{kind}'] = [{'o': [[round(x, 3), round(y, 3)] for x, y in list(p.exterior.coords)[:-1]],
                                             'h': [[[round(x, 3), round(y, 3)] for x, y in list(r.coords)[:-1]] for r in p.interiors]} for p in polys]
    out['stairs'][floor] = D['segments'].get(f'{floor}:stair', [])
    print(f"{floor}: wall lines {lw} -> {nw} pairings -> {len(wall_polys)} wall solids | glass/window lines {lg} -> {ng} pairings -> {len(glass_polys)} glass solids")
  json.dump(out, open('house3d_merged.json', 'w'), separators=(',', ':'))


if __name__ == '__main__':
    main()
