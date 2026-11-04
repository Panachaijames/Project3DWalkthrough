"""Geometry and drawing-reading helpers for openings.py (shapely + numpy; all lengths in metres).

Nothing in here knows about a particular drawing: the only inputs are the flattened items (tools/prims.py) and the
layer roles from the mapping file.
"""
import fnmatch, math
import numpy as np
from shapely.geometry import Polygon, LineString, Point, MultiPolygon, box
from shapely.ops import unary_union
from shapely.strtree import STRtree
from shapely.geometry.polygon import orient

ROLES = ('wall', 'column', 'glass', 'window', 'screen', 'door', 'stair', 'ignore')


# ------------------------------------------------------------------------------------------------ small helpers
def polys(g):
    """Polygons of any geometry (Polygon, MultiPolygon, GeometryCollection)."""
    if g is None or g.is_empty: return []
    if g.geom_type == 'Polygon': return [g]
    if hasattr(g, 'geoms'): return [p for x in g.geoms for p in polys(x)]
    return []


def lines_of(g):
    if g is None or g.is_empty: return []
    if g.geom_type == 'LineString': return [g]
    if hasattr(g, 'geoms'): return [p for x in g.geoms for p in lines_of(x)]
    return []


def even_odd(loops):
    """A HATCH's boundary loops -> its filled area (nested loops alternate fill / hole)."""
    g = Polygon()
    for l in loops:
        if len(l) < 3: continue
        p = Polygon(l).buffer(0)
        if not p.is_empty: g = g.symmetric_difference(p)
    return g.buffer(0)


def mean_width(p):
    """2 * area / perimeter: about the thickness of a long thin shape."""
    return 2 * p.area / p.length if p.length else 0


def unit(v):
    n = math.hypot(v[0], v[1])
    return (v[0] / n, v[1] / n) if n > 1e-12 else (1.0, 0.0)


def perp(u): return (-u[1], u[0])
def dot(a, b): return a[0] * b[0] + a[1] * b[1]
def cross(a, b): return a[0] * b[1] - a[1] * b[0]
def sub(a, b): return (a[0] - b[0], a[1] - b[1])
def add(a, b): return (a[0] + b[0], a[1] + b[1])
def mul(a, s): return (a[0] * s, a[1] * s)


def ang_diff(u, v):
    """Angle between two directions, ignoring sense (0..90 deg)."""
    c = abs(dot(unit(u), unit(v)))
    return math.degrees(math.acos(min(1.0, c)))


def circle3(p0, p1, p2):
    """Circle through three points -> ((centre x, y), radius). Worked out relative to p0: far from the origin (georeferenced
    drawings, a million metres out) the absolute formula loses millimetres."""
    bx, by = p1[0] - p0[0], p1[1] - p0[1]
    cx, cy = p2[0] - p0[0], p2[1] - p0[1]
    d = 2 * (bx * cy - by * cx)
    if abs(d) < 1e-12: return None
    b2, c2 = bx * bx + by * by, cx * cx + cy * cy
    ux = (cy * b2 - by * c2) / d
    uy = (bx * c2 - cx * b2) / d
    return (p0[0] + ux, p0[1] + uy), math.hypot(ux, uy)


def role_matcher(layer_roles):
    """mapping 'layers' {role: [layer name or glob pattern, ...]} -> function(layer) -> set of roles."""
    exact, pats = {}, []
    for role, names in (layer_roles or {}).items():
        if role not in ROLES: raise SystemExit(f'unknown layer role {role!r} (allowed: {", ".join(ROLES)})')
        for n in names:
            if any(ch in n for ch in '*?['): pats.append((n.upper(), role))
            else: exact.setdefault(n.upper(), set()).add(role)
    cache = {}

    def roles(layer):
        if layer not in cache:
            U = layer.upper()
            r = set(exact.get(U, ()))
            for p, role in pats:
                if fnmatch.fnmatchcase(U, p): r.add(role)
            cache[layer] = frozenset(r)
        return cache[layer]
    return roles


# ------------------------------------------------------------------------------------------------ reading items
CONTINUOUS = {'CONTINUOUS', 'BYLAYER', 'BYBLOCK', ''}


def eff_linetype(d, layer_lt):
    lt = (d.get('lt') or 'BYLAYER')
    if lt.upper() == 'BYLAYER': lt = layer_lt.get(d['lay'], 'Continuous') or 'Continuous'
    if lt.upper() == 'BYBLOCK': lt = 'Continuous'
    return lt


def is_continuous(lt):
    u = lt.upper().split('$')[-1]
    return u in CONTINUOUS or u.startswith('CONTINUOUS')


def signature(d, nd=3):
    """Identical geometry on the same layer (blocks inserted twice, copies) -> same signature."""
    t = d['t']
    if t == 'INSERT':
        return (t, d['lay'], d['name'], round(d['ins'][0], nd), round(d['ins'][1], nd), round(d['rot'], 1), d['sx'], d['sy'], d['path'])
    if 'pts' in d:
        p = [(round(x, nd), round(y, nd)) for x, y in d['pts']]
        if t == 'LINE' or (not d.get('closed') and len(p) > 1 and p[0] > p[-1]): p = p[::-1]
        if d.get('closed') and len(p) > 2:                     # closed shapes: start anywhere
            k = p.index(min(p)); p = p[k:] + p[:k]
        return (t, d['lay'], tuple(p))
    if 'loops' in d:
        return (t, d['lay'], tuple(tuple((round(x, nd), round(y, nd)) for x, y in l) for l in d['loops']))
    if 'text' in d:
        return (t, d['lay'], d['text'], round(d['ins'][0], nd), round(d['ins'][1], nd))
    return (t, d['lay'], id(d))


def dedupe(items):
    seen, out = set(), []
    for d in items:
        s = signature(d)
        if s in seen: continue
        seen.add(s); out.append(d)
    return out


def simplify_pts(pts, tol=0.004):
    """Merge the 10 mm flattening chords of curves back into longer chords (straight runs become one segment)."""
    if len(pts) < 3: return pts
    ls = LineString(pts).simplify(tol, preserve_topology=False)
    return [tuple(c) for c in ls.coords]


class Prim:
    """One flattened drawing item with what the detector needs."""
    __slots__ = ('i', 'd', 't', 'lay', 'roles', 'cont', 'lt', 'pts', 'closed', 'poly', 'arc', 'depth', 'path', 'h')

    def __init__(self, i, d, roles, lt):
        self.i, self.d, self.t, self.lay, self.roles = i, d, d['t'], d['lay'], roles
        self.lt, self.cont = lt, is_continuous(lt)
        self.depth, self.path, self.h = d.get('depth', 0), d.get('path', ''), d.get('h')
        self.pts = [tuple(p) for p in d['pts']] if 'pts' in d else None
        self.closed = False
        self.poly = None
        self.arc = None
        if self.pts:
            p = self.pts
            self.closed = bool(d.get('closed')) or (len(p) > 3 and math.dist(p[0], p[-1]) < 1e-3)
            if self.closed and len(p) >= 3:
                try:
                    g = Polygon(p).buffer(0)
                    if not g.is_empty and g.area > 1e-6: self.poly = g       # a MultiPolygon for a self-crossing outline: small_shapes splits it
                except Exception:
                    pass
            if self.t == 'ARC' and len(p) >= 3:
                c = circle3(p[0], p[len(p) // 2], p[-1])
                if c:
                    (cx, cy), r = c
                    ch = math.dist(p[0], p[-1])
                    # sweep from the chord and the side the middle point lies on
                    half = math.degrees(math.asin(min(1.0, ch / (2 * r))))
                    mid = p[len(p) // 2]
                    chord_mid = ((p[0][0] + p[-1][0]) / 2, (p[0][1] + p[-1][1]) / 2)
                    big = dot(sub(mid, chord_mid), sub(chord_mid, (cx, cy))) < 0 and ch > 1e-6
                    sweep = 360 - 2 * half if big else 2 * half
                    self.arc = {'c': (cx, cy), 'r': r, 'e0': p[0], 'e1': p[-1], 'sweep': sweep, 'mid': mid}

    def segs(self):
        p = self.pts
        if not p or len(p) < 2: return []
        q = list(zip(p, p[1:]))
        if self.closed and math.dist(p[0], p[-1]) > 1e-6: q.append((p[-1], p[0]))
        return q


# ------------------------------------------------------------------------------------------------ wall pieces
def pair_strips(segs, tmin, tmax, ang=3.0, min_overlap=0.05):
    """CAD draws a wall as two face lines. Pair each line with its nearest parallel partner(s) tmin..tmax away on
    each side and fill the strip between them (the same rule as cad_test/src/merge_cad.py).
    segs: [((x1, y1), (x2, y2)), ...] -> list of (Polygon, thickness, i, j)."""
    lines = [s for s in segs if math.dist(s[0], s[1]) > 0.02]
    if not lines: return []
    geoms = [LineString(l) for l in lines]
    tree = STRtree(geoms)
    out = []
    cosang = math.cos(math.radians(ang))
    for i, (a, b) in enumerate(lines):
        dx, dy = b[0] - a[0], b[1] - a[1]; L = math.hypot(dx, dy); ux, uy = dx / L, dy / L; nx, ny = -uy, ux
        cands = []
        for j in tree.query(geoms[i].buffer(tmax)):
            if j == i: continue
            c, e = lines[j]
            ex, ey = e[0] - c[0], e[1] - c[1]; L2 = math.hypot(ex, ey)
            if abs((ux * ex + uy * ey) / L2) < cosang: continue
            dc = (c[0] - a[0]) * nx + (c[1] - a[1]) * ny; de = (e[0] - a[0]) * nx + (e[1] - a[1]) * ny
            if abs(dc - de) > 0.02: continue
            t = (dc + de) / 2
            if not (tmin <= abs(t) <= tmax): continue
            pc = (c[0] - a[0]) * ux + (c[1] - a[1]) * uy; pe = (e[0] - a[0]) * ux + (e[1] - a[1]) * uy
            lo, hi = max(0.0, min(pc, pe)), min(L, max(pc, pe))
            if hi - lo < min_overlap: continue
            cands.append((t, lo, hi, j))
        for side in (1, -1):
            s = [c for c in cands if c[0] * side > 0]
            if not s: continue
            near = min(abs(c[0]) for c in s)
            for t, lo, hi, j in s:
                if abs(t) - near > 0.03: continue
                p0 = (a[0] + ux * lo, a[1] + uy * lo); p1 = (a[0] + ux * hi, a[1] + uy * hi)
                out.append((Polygon([p0, p1, (p1[0] + nx * t, p1[1] + ny * t), (p0[0] + nx * t, p0[1] + ny * t)]), abs(t), i, j))
    return out


def section(geom, p, n, half):
    """Intervals (in metres along n, relative to p) where the line p + s*n, |s| <= half, is inside geom."""
    ln = LineString([(p[0] - n[0] * half, p[1] - n[1] * half), (p[0] + n[0] * half, p[1] + n[1] * half)])
    cut = ln.intersection(geom)
    out = []
    for g in lines_of(cut):
        cs = list(g.coords)
        s = sorted(dot(sub(c, p), n) for c in cs)
        if s[-1] - s[0] > 1e-4: out.append((s[0], s[-1]))
    out.sort()
    merged = []
    for a, b in out:
        if merged and a <= merged[-1][1] + 1e-4: merged[-1] = (merged[-1][0], max(merged[-1][1], b))
        else: merged.append((a, b))
    return merged


def rect(c, u, s0, s1, l0, l1):
    """Rectangle in the frame (origin c, along u, across perp(u)): s0..s1 along, l0..l1 across."""
    n = perp(u)
    P = lambda s, l: (c[0] + u[0] * s + n[0] * l, c[1] + u[1] * s + n[1] * l)
    return Polygon([P(s0, l0), P(s1, l0), P(s1, l1), P(s0, l1)])
