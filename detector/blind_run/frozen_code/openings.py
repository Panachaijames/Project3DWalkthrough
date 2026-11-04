"""Find door, window and passage openings in a CAD floor plan (Phase 0 of the walkthrough tool).

Usage:  python openings.py <mapping.json> <out.json> [--png DIR]

Input: the flattened drawing cache (tools/prims.py) named in the mapping, and the mapping's layer roles (wall, column,
glass, window, door, stair, ignore). Everything else is read from the geometry, on any layer that is not ignored.
Output: {"openings": [{id, floor, kind, subtype, a, b, width, wallThickness, host, hinge, swing, confidence, evidence,
eitherKind}, ...]} with a and b on the wall centre line at the wall ends (drawing metres), plus a PNG per floor.

Rules, in order:
 1. Wall solid: wall/column-layer fills, thin closed outlines (mean width <= 0.35 m) and face lines paired 4-45 cm
    apart (continuous linetypes only); cracks and corner squares closed.
 2. Gaps: wall strips are pairs of opposite faces of the wall solid. From each strip end, look along its centre line
    for the next wall material; the stretch between is a gap, typed by its near end (cap / L-corner / T) and far end
    (the end of a collinear strip of the same thickness, or the face of another wall).
 3. Door swings: arcs on any layer (r 0.28-2 m, sweep 20-125 deg); which end is the closed leaf comes from a leaf
    drawn toward the other end (line or thin rectangle) and from the closed tip lying on the wall.
 4. Each swing goes to the gap that fits it best; the leaves must account for the gap (else the door is narrower and
    is read from the symbol). Two leaves whose closed tips meet are a double door, also when drawn in front of a
    deep reveal. A swing in no gap (wall drawn through, wall not drawn, glazed screen) is a door from the symbol,
    snapped to wall ends, glazing or jambs (small closed shapes on any layer) within 0.35 m.
 5. Glazing: parallel lines on window/glass layers grouped into bands. A band in a gap makes it glazed; a band in no
    gap is a bay when wall ends / columns in its own line (or a post-less glass corner) bound it within 0.25 m, and a
    window inside a drawn-through wall when the wall is thinner over it or jambs bound it. Glass running from the side
    of one cross wall to another is a glass wall, not an opening. Fixed glazing is a window; sliding sashes are a
    window unless they open straight onto a hatched floor (terrace) with no planting, then a sliding door.
 6. Other gap contents: a thin panel or a centre-line leaf running into a wall pocket = sliding / pocket door; both
    wall faces drawn on across the gap = opening over a low wall (window); frame pieces standing inside = frame-only
    sliding unit (window). A sliding leaf half out of a pocket where the wall simply ends = pocket door.
 7. A gap with nothing in it is a passage only when it looks like one: both ends wall ends of one wall line (<= 3.6 m;
    <= 2.5 m from an L-corner), or a short gap (<= 1.6 m) from a wall end to a wall face that carries on; not at a
    free-standing post, not across a stair, not on walls thinner than 7 cm, with building on both sides.
 8. Duplicates (both faces, two leaves of a double wall, gap + symbol) are fused: door > window > passage.
"""
import argparse, json, math, sys, time
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
for up in [HERE] + list(HERE.parents):
    if (up / 'tools' / 'prims.py').exists():
        sys.path.insert(0, str(up / 'tools')); break
sys.path.insert(0, str(HERE))
import prims                                   # noqa: E402  (the flattened-drawing cache reader)
from geomkit import *                           # noqa: E402,F401,F403
from geomkit import orient                      # noqa: E402

UNITS = {'mm': 1.0, 'cm': 10.0, 'm': 1000.0, 'in': 25.4, 'inch': 25.4, 'ft': 304.8}   # prims coords are DXF units / 1000


class Floor:
    def __init__(self, name, items, layer_lt, roles_of, scale):
        self.name = name
        self.P = []
        for d in items:
            if scale != 1.0: d = scaled(d, scale)
            r = roles_of(d['lay'])
            if 'ignore' in r: continue
            self.P.append(Prim(len(self.P), d, r, eff_linetype(d, layer_lt)))


def scaled(d, k):
    d = dict(d)
    if 'pts' in d: d['pts'] = [[x * k, y * k] for x, y in d['pts']]
    if 'loops' in d: d['loops'] = [[[x * k, y * k] for x, y in l] for l in d['loops']]
    if 'ins' in d: d['ins'] = [d['ins'][0] * k, d['ins'][1] * k]
    return d


# ================================================================================================ 1. the wall model
def build_walls(fl):
    """Wall solid from the wall and column layers: fills, thin closed outlines and paired face lines (continuous
    linetypes only). Also keeps the single wall-layer lines and small closed shapes."""
    pieces, segs, small, wide = [], [], [], []
    for p in fl.P:
        if not (p.roles & {'wall', 'column'}) or not p.cont: continue
        d = p.d
        if 'loops' in d:
            g = even_odd(d['loops'])
            if not g.is_empty: pieces.append(g)
            continue
        if not p.pts: continue
        if p.poly is not None:
            g = p.poly
            x0, y0, x1, y1 = g.bounds
            big = max(x1 - x0, y1 - y0)
            if big < 0.15: small.append(g); continue                   # jamb returns, posts: not walls
            if mean_width(g) <= 0.35 or ('column' in p.roles and big <= 1.5): pieces.append(g); continue
            wide.append(g); continue                                    # room outlines, zones: not walls
        if p.t == 'ARC' and p.arc and p.arc['sweep'] <= 125: continue  # swings drawn on a wall layer
        pts = simplify_pts(p.pts)
        segs += [(a, b) for a, b in zip(pts, pts[1:]) if math.dist(a, b) > 0.02]
    pieces += [s[0] for s in pair_strips(segs, 0.04, 0.45)]
    W = unary_union([g.buffer(0) for g in pieces]) if pieces else Polygon()
    W = W.buffer(0.03, join_style='mitre').buffer(-0.03, join_style='mitre')     # close cracks and corner squares
    W = W.simplify(0.003, preserve_topology=True)
    W = unary_union([g for g in polys(W) if g.area > 0.004])
    fl.W, fl.wall_segs, fl.wide_shapes = W, segs, wide
    cov = W.buffer(0.02)
    fl.singles = [part for a, b in segs for part in lines_of(LineString([a, b]).difference(cov)) if part.length > 0.2]
    fl.wall_small = small
    return W


class Geo:
    """Fast-ish line queries against a polygon set (shapely STRtree over the parts)."""
    def __init__(self, g):
        self.parts = polys(g)
        self.tree = STRtree(self.parts) if self.parts else None
        self.g = g

    def cover(self, p, u, L):
        """Covered intervals (sorted, merged) along the ray p + s*u, 0 <= s <= L."""
        if not self.tree: return []
        q = (p[0] + u[0] * L, p[1] + u[1] * L)
        ln = LineString([p, q])
        out = []
        for k in self.tree.query(ln):
            cut = ln.intersection(self.parts[k])
            for g in lines_of(cut):
                s = sorted(dot(sub(xy, p), u) for xy in g.coords)
                if s[-1] - s[0] > 1e-5: out.append((s[0], s[-1]))
        out.sort()
        m = []
        for a, b in out:
            if m and a <= m[-1][1] + 1e-4: m[-1] = (m[-1][0], max(m[-1][1], b))
            else: m.append((a, b))
        return m

    def section(self, p, n, half):
        """Covered intervals across: along n from p - half*n to p + half*n, relative to p."""
        iv = self.cover(sub(p, mul(n, half)), n, 2 * half)
        return [(a - half, b - half) for a, b in iv]

    def contains(self, p):
        if not self.tree: return False
        pt = Point(p)
        return any(self.parts[k].contains(pt) for k in self.tree.query(pt))

    def dist(self, p):
        if not self.tree: return 9e9
        pt = Point(p)
        k = self.tree.nearest(pt)
        return self.parts[k].distance(pt)


class Strip:
    """A stretch of wall: centre line c + s*u for s in [s0, s1], thickness t."""
    __slots__ = ('c', 'u', 'n', 's0', 's1', 't')

    def __init__(self, c, u, s0, s1, t):
        self.c, self.u, self.n, self.s0, self.s1, self.t = c, u, perp(u), s0, s1, t

    def at(self, s, l=0.0):
        return (self.c[0] + self.u[0] * s + self.n[0] * l, self.c[1] + self.u[1] * s + self.n[1] * l)


def find_strips(W, tmin=0.03, tmax=0.55):
    """Pairs of opposite faces of the wall solid (parallel boundary edges with opposite outward normals, tmin..tmax
    apart, overlapping) -> wall strips, whatever the walls were drawn with (lines, outlines, fills)."""
    E = []
    for poly in polys(W):
        poly = orient(poly, 1.0)
        for ring in [poly.exterior] + list(poly.interiors):
            cs = [tuple(c) for c in ring.coords]
            for a, b in zip(cs, cs[1:]):
                if math.dist(a, b) >= 0.02: E.append((a, b))
    if not E: return []
    A = np.array([[a[0], a[1], b[0], b[1]] for a, b in E])
    D = A[:, 2:] - A[:, :2]
    L = np.hypot(D[:, 0], D[:, 1])
    U = D / L[:, None]
    N = np.stack([U[:, 1], -U[:, 0]], 1)                     # outward normals (material on the left)
    mn = np.minimum(A[:, :2], A[:, 2:]) - tmax; mx = np.maximum(A[:, :2], A[:, 2:]) + tmax
    strips = []
    for i in range(len(E)):
        if L[i] < 0.03: continue
        cand = np.nonzero((mx[:, 0] >= min(A[i, 0], A[i, 2])) & (mn[:, 0] <= max(A[i, 0], A[i, 2])) &
                          (mx[:, 1] >= min(A[i, 1], A[i, 3])) & (mn[:, 1] <= max(A[i, 1], A[i, 3])))[0]
        cand = cand[(N[cand] @ N[i]) < -0.9994]                 # opposite faces, within ~2 degrees
        if not len(cand): continue
        a = A[i, :2]; u = U[i]; n = N[i]
        ta = -((A[cand, 0] - a[0]) * n[0] + (A[cand, 1] - a[1]) * n[1])
        tb = -((A[cand, 2] - a[0]) * n[0] + (A[cand, 3] - a[1]) * n[1])
        t = (ta + tb) / 2
        sa = (A[cand, 0] - a[0]) * u[0] + (A[cand, 1] - a[1]) * u[1]
        sb = (A[cand, 2] - a[0]) * u[0] + (A[cand, 3] - a[1]) * u[1]
        lo = np.maximum(np.minimum(sa, sb), 0); hi = np.minimum(np.maximum(sa, sb), L[i])
        ok = (t >= tmin) & (t <= tmax) & (np.abs(ta - tb) < 0.01) & (hi - lo >= 0.03)
        if not ok.any(): continue
        k = np.nonzero(ok)[0]
        tbest = t[k].min()
        for kk in k[t[k] <= tbest + 0.003]:
            c = (a[0] - n[0] * t[kk] / 2, a[1] - n[1] * t[kk] / 2)
            strips.append(Strip(c, (float(u[0]), float(u[1])), float(lo[kk]), float(hi[kk]), float(t[kk])))
    return strips


class Gap:
    __slots__ = ('a', 'b', 'u', 'n', 't', 'w', 'near', 'far', 'swings', 'bands', 'panels', 'kind', 'sub', 'ev', 'conf',
                 'jambs', 'notes', 'either')

    def __init__(self, a, b, t, near, far):
        self.a, self.b, self.t, self.near, self.far = a, b, t, near, far
        self.u = unit(sub(b, a)); self.n = perp(self.u); self.w = math.dist(a, b)
        self.swings, self.bands, self.panels, self.kind, self.sub, self.ev, self.conf = [], [], [], None, '', [], 0.0
        self.jambs, self.notes, self.either = [], [], False

    def frame(self, p):
        d = sub(p, self.a)
        return dot(d, self.u), dot(d, self.n)

    def at(self, s, l=0.0):
        return (self.a[0] + self.u[0] * s + self.n[0] * l, self.a[1] + self.u[1] * s + self.n[1] * l)


def end_profile(G, p, u, n, t, L=7.5):
    """From p (a strip end on its centre line) looking along u: material run d0 straight after p (0 if free), the
    free stretch after it up to d1 (the next material), for three lines across the band."""
    out = []
    for lat in (-0.35 * t, 0.0, 0.35 * t):
        q = add(p, mul(n, lat))
        iv = G.cover(sub(q, mul(u, 0.004)), u, L + 0.004)
        iv = [(a - 0.004, b - 0.004) for a, b in iv]
        d0 = 0.0
        rest = iv
        if iv and iv[0][0] <= 0.006:
            d0 = max(0.0, iv[0][1]); rest = iv[1:]
        d1 = rest[0][0] if rest else None
        out.append((d0, d1))
    return out


def strip_gaps(fl, G, strips, dmin=0.3, dmax=7.0):
    """From every wall end (a strip that stops, with or without a perpendicular wall right after it) look along the
    wall's centre line for the next wall material: the stretch between is a candidate opening on that wall line."""
    gaps = []
    for S in strips:
        if S.s1 - S.s0 < 0.04: continue
        for sgn in (1, -1):
            u = S.u if sgn > 0 else (-S.u[0], -S.u[1])
            n = perp(u)
            p = S.at(S.s1 if sgn > 0 else S.s0)
            prof = end_profile(G, p, u, n, S.t, dmax + 0.7)
            d0s = [x[0] for x in prof]; d1s = [x[1] for x in prof]
            if any(d is None for d in d1s): continue
            d0 = d0s[1]
            if d0 > 0.6 or max(d0s) - min(d0s) > 0.03: continue          # wall goes on / end not square
            d1 = min(d1s)
            w = d1 - d0
            if not (dmin <= w <= dmax): continue
            flat = max(d1s) - min(d1s) <= 0.03
            near = 'cap'
            if d0 > 0.02:                                               # a wall across the end: L-corner or T
                sec = G.section(add(p, mul(u, d0 / 2)), n, 1.5)
                own = [s for s in sec if s[0] <= 0 <= s[1]]
                if own:
                    lo, hi = own[0]
                    ext_lo, ext_hi = -lo - S.t / 2, hi - S.t / 2
                    near = 'T' if (ext_lo > 0.15 and ext_hi > 0.15) else 'L'
                else:
                    near = 'L'
            a = add(p, mul(u, d0)); b = add(p, mul(u, d1))
            g = Gap(a, b, S.t, near, 'face' if flat else 'corner')
            gaps.append(g)
    # far end on a collinear wall strip of about the same thickness -> 'wall end'
    for g in gaps:
        for S in strips:
            if abs(S.t - g.t) > 0.04 or ang_diff(S.u, g.u) > 2: continue
            s, l = dot(sub(g.b, S.c), S.u), dot(sub(g.b, S.c), S.n)
            if abs(l) > 0.03: continue
            if min(abs(s - S.s0), abs(s - S.s1)) <= 0.03 or (S.s0 - 0.03 <= s <= S.s1 + 0.03):
                g.far = 'end'; break
    # the same gap is found from both of its ends: keep one
    out = []
    for g in sorted(gaps, key=lambda g: ({'cap': 0, 'L': 1, 'T': 2}[g.near], {'end': 0, 'face': 1, 'corner': 2}[g.far])):
        dup = False
        for h in out:
            if ang_diff(g.u, h.u) < 3 and ((math.dist(g.a, h.a) < 0.06 and math.dist(g.b, h.b) < 0.06) or
                                           (math.dist(g.a, h.b) < 0.06 and math.dist(g.b, h.a) < 0.06)):
                dup = True
                # found from both sides: both ends are wall ends
                if h.far != 'end' and g.near in ('cap', 'L'): h.far = 'end'
                break
        if not dup: out.append(g)
    return out


# ================================================================================================ 2. line work
class SegIndex:
    """Every straight segment of every kept item (curves excluded), for leaf, content and band queries."""
    def __init__(self, fl):
        rows, pid = [], []
        for p in fl.P:
            if not p.pts or p.t in ('ARC', 'CIRCLE', 'ELLIPSE'): continue
            pts = simplify_pts(p.pts, 0.002) if p.t == 'SPLINE' else p.pts
            q = list(zip(pts, pts[1:]))
            if p.closed and math.dist(pts[0], pts[-1]) > 1e-6: q.append((pts[-1], pts[0]))
            for a, b in q:
                if math.dist(a, b) < 0.005: continue
                rows.append((a[0], a[1], b[0], b[1])); pid.append(p.i)
        self.A = np.array(rows, dtype=float).reshape(-1, 4)
        self.pid = np.array(pid, dtype=int)
        d = self.A[:, 2:] - self.A[:, :2]
        self.L = np.hypot(d[:, 0], d[:, 1])
        self.U = d / np.maximum(self.L, 1e-12)[:, None]
        self.mn = np.minimum(self.A[:, :2], self.A[:, 2:])
        self.mx = np.maximum(self.A[:, :2], self.A[:, 2:])

    def near_box(self, x0, y0, x1, y1):
        return np.nonzero((self.mx[:, 0] >= x0) & (self.mn[:, 0] <= x1) & (self.mx[:, 1] >= y0) & (self.mn[:, 1] <= y1))[0]

    def in_frame(self, idx, c, u):
        n = perp(u)
        A = self.A[idx]
        s_a = (A[:, 0] - c[0]) * u[0] + (A[:, 1] - c[1]) * u[1]
        s_b = (A[:, 2] - c[0]) * u[0] + (A[:, 3] - c[1]) * u[1]
        l_a = (A[:, 0] - c[0]) * n[0] + (A[:, 1] - c[1]) * n[1]
        l_b = (A[:, 2] - c[0]) * n[0] + (A[:, 3] - c[1]) * n[1]
        cs = np.abs(self.U[idx, 0] * u[0] + self.U[idx, 1] * u[1])
        return np.minimum(s_a, s_b), np.maximum(s_a, s_b), l_a, l_b, cs


# ================================================================================================ 3. glazing bands
class Band:
    __slots__ = ('c', 'u', 'n', 's0', 's1', 'l0', 'l1', 'offs', 'segs', 'lays', 'roles', 'used')

    def __init__(self, c, u, s0, s1, l0, l1, offs, segs, lays, roles):
        self.c, self.u, self.n = c, u, perp(u)
        self.s0, self.s1, self.l0, self.l1, self.offs, self.segs, self.lays, self.roles = s0, s1, l0, l1, offs, segs, lays, roles
        self.used = False

    @property
    def length(self): return self.s1 - self.s0

    def at(self, s, l=None):
        l = (self.l0 + self.l1) / 2 if l is None else l
        return (self.c[0] + self.u[0] * s + self.n[0] * l, self.c[1] + self.u[1] * s + self.n[1] * l)

    def poly(self, pad=0.0):
        return rect(self.c, self.u, self.s0, self.s1, self.l0 - pad, self.l1 + pad)


def glazing_bands(fl, SI):
    """Thin parallel lines on window / glass layers (2-6 lines 17-75 mm apart, or a single glass line) grouped into
    bands along a wall line. Small closed pieces (frame stubs, 50x50 stiles) are left out: they are not glass."""
    keep = []
    for k in range(len(SI.A)):
        p = fl.P[SI.pid[k]]
        if not (p.roles & {'window', 'glass'}) or (p.roles & {'wall', 'column'}): continue
        if p.poly is not None:
            x0, y0, x1, y1 = p.poly.bounds
            if max(x1 - x0, y1 - y0) < 0.3: continue
        if SI.L[k] < 0.08: continue
        keep.append(k)
    keep = np.array(keep, dtype=int)
    if not len(keep): return []
    par = list(range(len(keep)))

    def find(i):
        while par[i] != i:
            par[i] = par[par[i]]; i = par[i]
        return i
    A = SI.A[keep]; U = SI.U[keep]; L = SI.L[keep]
    mid = (A[:, :2] + A[:, 2:]) / 2
    for i in range(len(keep)):
        u = U[i]; n = (-u[1], u[0])
        lat = np.abs((mid[:, 0] - A[i, 0]) * n[0] + (mid[:, 1] - A[i, 1]) * n[1])
        cs = np.abs(U[:, 0] * u[0] + U[:, 1] * u[1])
        sa = (A[:, 0] - A[i, 0]) * u[0] + (A[:, 1] - A[i, 1]) * u[1]
        sb = (A[:, 2] - A[i, 0]) * u[0] + (A[:, 3] - A[i, 1]) * u[1]
        lo = np.minimum(sa, sb); hi = np.maximum(sa, sb)
        ok = (cs > math.cos(math.radians(2.5))) & (lat <= 0.16) & (hi >= -0.06) & (lo <= L[i] + 0.06)
        for j in np.nonzero(ok)[0]:
            if j != i: par[find(j)] = find(i)
    groups = {}
    for i in range(len(keep)): groups.setdefault(find(i), []).append(i)
    bands = []
    for g in groups.values():
        g = np.array(g)
        w = L[g]
        ref = U[g[int(np.argmax(w))]]
        sg = np.sign(U[g] @ ref); sg[sg == 0] = 1
        u = unit(tuple((U[g] * sg[:, None] * w[:, None]).sum(0)))
        c = tuple(mid[g[int(np.argmax(w))]])
        n = perp(u)
        sa = (A[g, 0] - c[0]) * u[0] + (A[g, 1] - c[1]) * u[1]
        sb = (A[g, 2] - c[0]) * u[0] + (A[g, 3] - c[1]) * u[1]
        la = (A[g, 0] - c[0]) * n[0] + (A[g, 1] - c[1]) * n[1]
        lb = (A[g, 2] - c[0]) * n[0] + (A[g, 3] - c[1]) * n[1]
        lo, hi, lat = np.minimum(sa, sb), np.maximum(sa, sb), (la + lb) / 2
        order = np.argsort(lo)
        runs, cur, reach = [], [order[0]], hi[order[0]]
        for k in order[1:]:
            if lo[k] <= reach + 0.12: cur.append(k); reach = max(reach, hi[k])
            else: runs.append(cur); cur = [k]; reach = hi[k]
        runs.append(cur)
        for r in runs:
            r = np.array(r)
            s0, s1 = float(lo[r].min()), float(hi[r].max())
            if s1 - s0 < 0.25: continue
            offs = []
            for o in sorted(float(v) for v in lat[r]):
                if offs and o - offs[-1] <= 0.004: continue
                offs.append(round(o, 3))
            segk = [int(keep[g[k]]) for k in r]
            lays = sorted(set(fl.P[SI.pid[k]].lay for k in segk))
            roles = set().union(*[fl.P[SI.pid[k]].roles for k in segk])
            bands.append(Band(c, u, s0, s1, float(lat[r].min()), float(lat[r].max()), offs, segk, lays, roles))
    return bands


# ================================================================================================ 4. door swings
class Swing:
    """A door swing arc read as hinge -> closed tip (along the wall) with the open tip off the wall."""
    __slots__ = ('p', 'c', 'r', 'sweep', 'hinge', 'closed', 'open', 'leaf', 'used', 'mate')

    def __init__(self, p, hinge, closed, open_, leaf):
        self.p, self.c, self.r, self.sweep = p, p.arc['c'], p.arc['r'], p.arc['sweep']
        self.hinge, self.closed, self.open, self.leaf = hinge, closed, open_, leaf
        self.used, self.mate = False, None

    @property
    def u(self): return unit(sub(self.closed, self.hinge))

    @property
    def chord(self): return math.dist(self.hinge, self.closed)


def find_leaf(SI, fl, hinge, tip, r):
    """A straight leaf from the hinge toward the open tip: a line or a thin rectangle's long edges, any layer except
    walls. -> (segment index, length, 2 if a thin rectangle / line pair else 1) or None."""
    w = unit(sub(tip, hinge))
    idx = SI.near_box(min(hinge[0], tip[0]) - 0.15, min(hinge[1], tip[1]) - 0.15, max(hinge[0], tip[0]) + 0.15, max(hinge[1], tip[1]) + 0.15)
    if not len(idx): return None
    s0, s1, la, lb, cs = SI.in_frame(idx, hinge, w)
    lat = np.maximum(np.abs(la), np.abs(lb))
    ok = (cs > math.cos(math.radians(14))) & (lat <= 0.08) & (s0 >= -0.10) & (s0 <= 0.12) & (s1 - s0 >= 0.4 * r) & (s1 <= r + 0.15)
    best, lats = None, []
    for k in np.nonzero(ok)[0]:
        p = fl.P[SI.pid[idx[k]]]
        if p.roles & {'wall', 'column'}: continue
        L = float(s1[k] - s0[k])
        lats.append((la[k] + lb[k]) / 2)
        if best is None or L > best[1]: best = (int(idx[k]), L)
    if best is None: return None
    pair = any(0.012 <= abs(x - y) <= 0.07 for i, x in enumerate(lats) for y in lats[i + 1:])
    return (best[0], best[1], 2 if pair else 1)


def pick_swing(hyps, G):
    """Which arc end is the closed leaf: a leaf drawn toward the other end (a thin rectangle beats a single line),
    the closed tip lying on the wall and the open tip off it. -> the chosen hypothesis or None if undecided."""
    scored = []
    for h in hyps:
        s = (h.leaf[2] if h.leaf else 0)
        s += 1 if G.dist(h.closed) <= 0.12 else 0
        s -= 1 if G.dist(h.open) <= 0.05 else 0
        scored.append((s, h))
    scored.sort(key=lambda x: -x[0])
    if scored[0][0] <= 0 or (len(scored) > 1 and scored[0][0] == scored[1][0]): return None
    return scored[0][1]


def door_swings(fl, SI):
    """-> list of [hypothesis A, hypothesis B] per arc (which arc end is the closed leaf is decided later)."""
    out = []
    for p in fl.P:
        a = p.arc
        if not a or not (0.28 <= a['r'] <= 2.0) or not (20 <= a['sweep'] <= 125): continue
        hyps = []
        for closed, open_ in ((a['e0'], a['e1']), (a['e1'], a['e0'])):
            hyps.append(Swing(p, a['c'], closed, open_, find_leaf(SI, fl, a['c'], open_, a['r'])))
        out.append(hyps)
    return out


# ================================================================================================ 5. jambs, frames
def small_shapes(fl):
    """Closed shapes up to 0.30 m on any kept layer (jambs, frame stubs, wall returns, posts)."""
    out = []
    for p in fl.P:
        if p.poly is None: continue
        x0, y0, x1, y1 = p.poly.bounds
        big, sm = max(x1 - x0, y1 - y0), min(x1 - x0, y1 - y0)
        if 0.025 <= big <= 0.30 and sm >= 0.012:
            mrr = p.poly.minimum_rotated_rectangle
            out.append((p.poly, p))
    return out


def jamb_at(fl, c, u, n_lat, s_lo, s_hi, lat_lo, lat_hi):
    """Small shapes whose centre lies in the frame box (along u from c: s_lo..s_hi; across: lat_lo..lat_hi).
    -> list of (s_min, s_max, along-size) of each shape along u."""
    res = []
    n = perp(u)
    for g, p in fl.jambs:
        cx, cy = g.centroid.x, g.centroid.y
        s, l = dot(sub((cx, cy), c), u), dot(sub((cx, cy), c), n)
        if not (s_lo <= s <= s_hi and lat_lo <= l <= lat_hi): continue
        ss = [dot(sub(q, c), u) for q in g.exterior.coords]
        res.append((min(ss), max(ss), max(ss) - min(ss), p))
    return res


# ================================================================================================ 6. one floor
def detect_floor(fl):
    T = {}
    t0 = time.time()
    W = build_walls(fl)
    G = Geo(W)
    strips = find_strips(W)
    gaps = strip_gaps(fl, G, strips)
    T['walls'] = time.time() - t0
    SI = SegIndex(fl)
    bands = glazing_bands(fl, SI)
    swings = door_swings(fl, SI)
    fl.jambs = small_shapes(fl)
    fl.floor_hatches = [g for g in (even_odd(p.d['loops']) for p in fl.P if 'loops' in p.d and not (p.roles & {'wall', 'column'}))
                        if not g.is_empty and g.area >= 2.0]
    fl.SI, fl.G, fl.bands, fl.swings, fl.strips, fl.gaps = SI, G, bands, swings, strips, gaps

    OB = Geo(unary_union([W] + [b.poly(0.01) for b in bands]))
    fl.OB = OB
    gaps = [g for g in gaps if g.near != 'T']
    fl.gaps = gaps
    # ---- swings that sit in a gap: each arc goes to its best gap, read the way that fits it
    cand = []
    for ai, hyps in enumerate(swings):
        leafy = any(h.leaf for h in hyps)
        for h in hyps:
            if leafy and not h.leaf: continue                               # the other end has the leaf drawn
            for gi, g in enumerate(gaps):
                if h.r > g.w + 0.45: continue
                sh, lh = g.frame(h.hinge); sc, lc = g.frame(h.closed); so, lo_ = g.frame(h.open)
                if not (-0.3 <= sh <= g.w + 0.3 and -0.3 <= sc <= g.w + 0.3): continue
                if abs(lh) > g.t / 2 + 0.25 or abs(lc) > g.t / 2 + 0.25: continue
                if abs(lo_) < 0.25 * h.r: continue                          # the open leaf stands off the wall
                if ang_diff(sub(h.closed, h.hinge), g.u) > 25: continue
                score = (h.leaf[2] if h.leaf else 0) + (abs(lc) <= g.t / 2 + 0.05) + (abs(lh) <= g.t / 2 + 0.05) \
                    + (abs(h.r - g.w) <= 0.25 * g.w) - abs(lh) - abs(lc)
                cand.append((score, ai, gi, h))
    cand.sort(key=lambda x: -x[0])
    taken = set()
    for score, ai, gi, h in cand:
        if ai in taken: continue
        taken.add(ai); gaps[gi].swings.append(h)
    for g in gaps:                     # the leaves must account for the gap; otherwise the door is narrower (below)
        if g.swings and sum(min(h.r, g.w) for h in g.swings) < 0.55 * g.w:
            g.swings = []
    used_arcs = {id(h.p) for g in gaps for h in g.swings}
    # ---- two leaves whose closed tips meet (a double door) drawn in front of a gap of the same span (deep reveal)
    free = [hyps for hyps in swings if id(hyps[0].p) not in used_arcs]
    for i in range(len(free)):
        for j in range(i + 1, len(free)):
            for hi in free[i]:
                for hj in free[j]:
                    if math.dist(hi.closed, hj.closed) > 0.12 or dot(hi.u, hj.u) > -0.95: continue
                    u = unit(sub(hj.hinge, hi.hinge))
                    if abs(dot(sub(hj.hinge, hi.hinge), perp(hi.u))) > 0.08: continue
                    span = math.dist(hi.hinge, hj.hinge)
                    for g in gaps:
                        if g.swings or ang_diff(g.u, u) > 5: continue
                        s0, l0 = g.frame(hi.hinge); s1, l1 = g.frame(hj.hinge)
                        if abs(l0) > 1.0 or abs(l1 - l0) > 0.05: continue
                        if min(abs(s0), abs(s0 - g.w)) <= 0.15 and min(abs(s1), abs(s1 - g.w)) <= 0.15 and abs(span - g.w) <= 0.15:
                            g.swings = [hi, hj]
                            g.notes.append('double swing drawn %.2f m in front of the gap' % abs(l0))
                            used_arcs |= {id(hi.p), id(hj.p)}
                            break
    for g in gaps:
        for b in bands:
            if ang_diff(b.u, g.u) > 5: continue
            s0, l0 = g.frame(b.at(b.s0)); s1, l1 = g.frame(b.at(b.s1))
            if max(abs(l0), abs(l1)) > g.t / 2 + 0.12: continue
            lo, hi = max(min(s0, s1), 0.0), min(max(s0, s1), g.w)
            if hi - lo >= 0.4 * g.w: g.bands.append(b)
        gap_contents(fl, g)

    openings = []
    fl.used_panels = set()
    for g in gaps:
        if g.near == 'T': continue
        base = f'wall gap ({g.near}-{g.far})'
        if g.swings:
            g.kind = 'door'
            nsw = len(g.swings)
            g.sub = 'hinged single' if nsw == 1 else ('hinged double' if nsw == 2 else f'{nsw}-leaf set')
            g.ev = [base, f'{nsw} swing arc(s)'] + sorted(set('arc on ' + h.p.lay for h in g.swings)) + g.notes
            g.conf = 0.9
            narrow_to_symbol(fl, g)
        elif any(p[0] in ('sliding panel', 'pocket panel') for p in g.panels):
            g.kind, g.sub = 'door', 'sliding' if not any(p[0].startswith('pocket') for p in g.panels) else 'pocket sliding'
            g.ev = [base] + sorted(set(f'{k} on {lay}' for k, lay in g.panels if k != 'low wall'))
            g.conf = 0.75
        elif g.bands:
            for b in g.bands: b.used = True
            lays = sorted(set(l for b in g.bands for l in b.lays))
            for s0, s1, kind, nl in glazing_units(fl, g.bands, g.a, g.u, g.w):
                a, b = g.at(s0), g.at(s1)
                o = glazed_opening(fl, a, b, g.t, kind, nl, [base, 'glazing band'] + lays, 0.8)
                o['far'] = g.far
                openings.append(o)
            continue
        elif any(p[0] == 'low wall' for p in g.panels):
            g.kind, g.sub, g.ev, g.conf = 'window', 'opening over a low wall (no glass drawn)', [base] + g.notes, 0.5
        elif any(p[0] == 'pocket line' for p in g.panels):
            g.kind, g.sub = 'door', 'pocket sliding'
            g.ev = [base] + sorted(set(f'{k} on {lay}' for k, lay in g.panels))
            g.conf = 0.65
        elif g.jambs:
            g.kind, g.sub, g.ev, g.conf = 'window', 'sliding (frame only, no glass drawn)', [base, f'{len(g.jambs)} frame piece(s) inside the gap'], 0.55
        else:
            if not passage_ok(fl, g): continue
            g.kind, g.sub, g.ev, g.conf = 'passage', 'open', [base + ', nothing drawn in it'], 0.5 if g.far == 'end' else 0.4
        for h in g.swings: h.used = True
        for b in g.bands: b.used = True
        if g.kind == 'door': fl.used_panels |= {int(x[6:]) for x in g.notes if x.startswith('panel#')}
        g.ev = [e for e in g.ev if not e.startswith('panel#')]
        openings.append(dict(kind=g.kind, subtype=g.sub, a=g.a, b=g.b, t=g.t, host='wall', ev=g.ev, conf=g.conf,
                             swings=g.swings, src='gap', far=g.far))

    # ---- swings in no gap: the door comes from the symbol, snapped to whatever bounds it
    free = [hyps for hyps in swings if not any(h.used for h in hyps)]
    done = set()
    for i in range(len(free)):                                  # double doors: two leaves whose closed tips meet
        for j in range(i + 1, len(free)):
            if i in done or j in done: continue
            for hi in free[i]:
                for hj in free[j]:
                    if i in done or j in done: break
                    if math.dist(hi.closed, hj.closed) > 0.12 or dot(hi.u, hj.u) > -0.95: continue
                    if abs(dot(sub(hj.hinge, hi.hinge), perp(hi.u))) > 0.08: continue
                    if not (0.3 <= hi.r <= 1.3 and 0.3 <= hj.r <= 1.3): continue
                    o = symbol_door(fl, hi, hj)
                    if o:
                        openings.append(o); done |= {i, j}; hi.used = hj.used = True
    for k, hyps in enumerate(free):
        if k in done: continue
        h = pick_swing(hyps, OB)
        if h is None or not h.leaf: continue
        if not (0.45 <= h.r <= 1.6 and 25 <= h.sweep <= 110): continue
        o = symbol_door(fl, h)
        if o: openings.append(o); h.used = True

    openings += pocket_doors(fl)

    # ---- glazing bands in no gap: bays between columns or wall faces, and glass set inside a drawn-through wall
    for b in bands:
        if b.used or b.length < 0.5: continue
        lm = (b.l0 + b.l1) / 2
        mid = b.at((b.s0 + b.s1) / 2, lm)
        if G.contains(mid):
            o = hidden_window(fl, b)
            if o: openings.append(o); b.used = True
            continue
        iv = [(x - 0.4 + b.s0, y - 0.4 + b.s0) for x, y in G.cover(b.at(b.s0 - 0.4, lm), b.u, b.length + 0.8)]
        sm = (b.s0 + b.s1) / 2
        left = [y for x, y in iv if y <= sm]; right = [x for x, y in iv if x >= sm]
        s0 = max(left) if left and b.s0 - 0.25 <= max(left) <= b.s0 + 0.05 else None
        s1 = min(right) if right and b.s1 - 0.05 <= min(right) <= b.s1 + 0.25 else None
        ends = ['wall' if s0 is not None else None, 'wall' if s1 is not None else None]
        if s0 is None: s0 = corner_end(b, bands, b.s0, lm); ends[0] = 'corner' if s0 is not None else None
        if s1 is None: s1 = corner_end(b, bands, b.s1, lm); ends[1] = 'corner' if s1 is not None else None
        if s0 is None or s1 is None or ends == ['corner', 'corner'] or s1 - s0 > 7.0: continue
        # glass that runs from the face of one cross wall to another (a glazed corridor side, a shower screen,
        # pool glass) is a glass wall, not a window: at least one end must be a wall end / column in its own line
        inline = [e == 'wall' and in_line_end(G, b, se, lm) for e, se in ((ends[0], s0 - 0.03), (ends[1], s1 + 0.03))]
        if not any(inline): continue
        t, mid_l = 0.1, 0.0
        for se in ((s0 - 0.05) if ends[0] == 'wall' else None, (s1 + 0.05) if ends[1] == 'wall' else None):
            if se is None: continue
            sec = [s for s in G.section(b.at(se, lm), b.n, 0.6) if s[0] <= 0.15 and s[1] >= -0.15]
            if sec and sec[0][1] - sec[0][0] <= 0.6:
                t, mid_l = sec[0][1] - sec[0][0], (sec[0][0] + sec[0][1]) / 2; break
        a0 = add(b.at(s0, lm), mul(b.n, mid_l))
        b.used = True
        for u0, u1, kind, nl in glazing_units(fl, [b], a0, b.u, s1 - s0):
            openings.append(glazed_opening(fl, add(a0, mul(b.u, u0)), add(a0, mul(b.u, u1)), t, kind, nl,
                                           ['glazing between wall ends (bay)'] + b.lays, 0.65))
    openings = fuse(openings)
    T['total'] = time.time() - t0
    fl.T = T
    return openings


def glazing_units(fl, bands, c, u, w):
    """Split the glazing lines of an opening (frame origin c, along u, length w) into units: a 'fixed' unit (one to
    three lines running through, 50 mm apart or a single glass line) or a 'sliding' unit (sashes in two tracks: lines
    25 mm apart, or the line set shifting from panel to panel). A change from one to the other is a full-depth frame
    between two units (a fixed pane beside a sliding door, say). -> [(s0, s1, kind, n_lines)] covering 0..w."""
    SI = fl.SI
    rows = []
    for b in bands:
        for k in b.segs:
            A = SI.A[k]
            sa = dot(sub((A[0], A[1]), c), u); sb = dot(sub((A[2], A[3]), c), u)
            la = dot(sub((A[0], A[1]), c), perp(u)); lb = dot(sub((A[2], A[3]), c), perp(u))
            lo, hi = max(min(sa, sb), 0.0), min(max(sa, sb), w)
            if hi - lo >= 0.05: rows.append((lo, hi, round((la + lb) / 2 / 0.005) * 0.005))
    if not rows: return [(0.0, w, 'fixed', 0)]
    rows.sort()
    pieces, cur, reach = [], [rows[0]], rows[0][1]
    for r in rows[1:]:
        if r[0] > reach + 0.03: pieces.append(cur); cur = [r]; reach = r[1]
        else: cur.append(r); reach = max(reach, r[1])
    pieces.append(cur)
    typed = []
    for p in pieces:
        offs = sorted(set(x[2] for x in p))
        sp = min((b - a for a, b in zip(offs, offs[1:])), default=1.0)
        kind = 'sliding' if len(offs) >= 4 or (len(offs) >= 2 and sp <= 0.032) else 'fixed'
        typed.append([min(x[0] for x in p), max(x[1] for x in p), kind, len(offs)])
    units = [typed[0]]
    for t in typed[1:]:
        if t[2] == units[-1][2]: units[-1][1] = t[1]; units[-1][3] = max(units[-1][3], t[3])
        else: units.append(t)
    units = [x for x in units if x[1] - x[0] >= 0.5] or [max(units, key=lambda x: x[1] - x[0])]
    # keep a split only between two substantial units (a fixed pane beside a sliding door); a short fixed lite
    # beside sashes is one window
    merged = [units[0]]
    for x in units[1:]:
        p = merged[-1]
        if min(p[1] - p[0], x[1] - x[0]) < 2.0:
            big = p if p[1] - p[0] >= x[1] - x[0] else x
            merged[-1] = [p[0], x[1], big[2], max(p[3], x[3])]
        else:
            merged.append(x)
    units = merged
    out = []
    for i, x in enumerate(units):
        s0 = 0.0 if i == 0 else (units[i - 1][1] + x[0]) / 2
        s1 = w if i == len(units) - 1 else (x[1] + units[i + 1][0]) / 2
        out.append((s0, s1, x[2], x[3]))
    return out


def in_line_end(G, b, s, lm):
    """Is the wall material just past a glazing end a wall end, pier or column standing in the glazing's own line
    (narrow across it), rather than the long side of a cross wall?"""
    sec = G.section(b.at(s, lm), b.n, 1.5)
    own = [x for x in sec if x[0] - 0.02 <= 0 <= x[1] + 0.02]
    if own and own[0][1] - own[0][0] <= 0.65: return True             # a pier / column / wall end
    sgn = 1 if s > (b.s0 + b.s1) / 2 else -1                          # or the wall line carries on past the end
    run = G.cover(b.at(s - sgn * 0.03, lm), mul(b.u, sgn), 0.6)
    return bool(run) and run[0][0] <= 0.04 and run[0][1] >= 0.33


def corner_end(b, bands, s_end, lm):
    """Glazing that turns a corner with no post: the band ends on the line of the band it meets at right angles.
    -> the end position along b, or None."""
    E = b.at(s_end, lm)
    best = None
    for b2 in bands:
        if b2 is b or ang_diff(b.u, b2.u) < 75: continue
        l2 = (b2.l0 + b2.l1) / 2
        d_line = dot(sub(E, b2.c), b2.n) - l2
        s_on = dot(sub(E, b2.c), b2.u)
        if abs(d_line) > 0.3 or not (b2.s0 - 0.35 <= s_on <= b2.s1 + 0.35): continue
        if min(abs(s_on - b2.s0), abs(s_on - b2.s1)) > 0.45: continue
        den = dot(b.u, b2.n)
        if abs(den) < 0.5: continue
        s = (l2 - dot(sub(add(b.c, mul(b.n, lm)), b2.c), b2.n)) / den
        if abs(s - s_end) <= 0.35 and (best is None or abs(d_line) < best[0]): best = (abs(d_line), s)
    return best[1] if best else None


def hidden_window(fl, b):
    """Glass drawn inside a wall whose lines run on through the opening (frame lines drawn on the wall layer, or an
    untrimmed wall): the opening is where the wall is thinner than on both sides, or between the jambs at the ends
    of the glass."""
    G = fl.G
    lm = (b.l0 + b.l1) / 2
    sm = (b.s0 + b.s1) / 2
    def own(s):
        sec = G.section(b.at(s, lm), b.n, 0.6)
        inn = [x for x in sec if x[0] - 0.01 <= 0 <= x[1] + 0.01]
        return inn[0] if inn else None
    im = own(sm)
    if not im or im[1] - im[0] > 0.6: return None
    i0, i1 = own(b.s0 - 0.15), own(b.s1 + 0.15)
    ok_sides = [x for x in (i0, i1) if x and x[1] - x[0] <= 0.6]
    if len(ok_sides) == 2:
        lo, hi = max(i0[0], i1[0]), min(i0[1], i1[1])                 # the full wall on both sides
    elif len(ok_sides) == 1:
        lo, hi = ok_sides[0]
    else:
        lo, hi = im                                                    # the glass sits between cross walls
    if hi - lo < 0.04: return None
    t, mid_l = hi - lo, (lo + hi) / 2
    ev = ['glazing inside a drawn-through wall'] + b.lays
    s0 = s1 = None
    for a_, b_ in ((lo, im[0]), (im[1], hi)):                         # a strip of the wall missing over the glass
        if b_ - a_ >= 0.04 and ok_sides:
            probe = (a_ + b_) / 2
            iv = G.cover(b.at(b.s0 - 0.6, lm + probe), b.u, b.length + 1.2)
            iv = [(x - 0.6 + b.s0, y - 0.6 + b.s0) for x, y in iv]
            left = [y for x, y in iv if y <= sm]; right = [x for x, y in iv if x >= sm]
            if any(x <= sm <= y for x, y in iv): continue
            if left and right and b.s0 - 0.3 <= max(left) <= b.s0 + 0.05 and b.s1 - 0.05 <= min(right) <= b.s1 + 0.3:
                s0, s1 = max(left), min(right); ev.append('wall thinned over the glass'); break
    if s0 is None:
        c = b.at(0.0, lm + mid_l)
        hl = t / 2 + 0.05
        jl = jamb_at(fl, c, b.u, b.n, b.s0 - 0.12, b.s0 + 0.06, -hl, hl)
        jr = jamb_at(fl, c, b.u, b.n, b.s1 - 0.06, b.s1 + 0.12, -hl, hl)
        if not jl or not jr: return None
        s0 = min(j[0] for j in jl); s1 = max(j[1] for j in jr)
        ev.append('jambs at both ends of the glass')
    a, bb = b.at(s0, lm + mid_l), b.at(s1, lm + mid_l)
    return dict(kind='window', subtype='fixed', a=a, b=bb, t=t, host='wall', ev=ev, conf=0.6, swings=[], src='glazing')


def glazed_opening(fl, a, b, t, unit_kind, n_lines, ev, conf):
    """A glazed unit -> window or door. Fixed glazing is a window. A sliding unit is a sliding glass door when the
    floor outside it is free to walk onto, a window when a planter, kerb or strip edge runs along it outside, and
    either (flagged) when it sits between two enclosed spaces."""
    if unit_kind == 'fixed':
        return dict(kind='window', subtype='fixed', a=a, b=b, t=t, host='wall', ev=ev + ['fixed glazing'], conf=conf, swings=[], src='glazing')
    # A sliding unit drawn like a window may be a floor-length sliding door: the plan does not show sills. It is read
    # as a door when it opens straight onto a hatched floor (terrace / deck paving) with no planting on it; otherwise
    # it stays a window, flagged eitherKind for staff unless a planter / kerb / edge runs along it outside.
    if opens_onto_paving(fl, a, b, t):
        return dict(kind='door', subtype='sliding glass door', a=a, b=b, t=t, host='wall', either=True,
                    ev=ev + [f'sliding sashes ({n_lines} lines)', 'opens onto a hatched floor (terrace / deck)'],
                    conf=conf - 0.2, swings=[], src='glazing')
    side = outside_free(fl, a, b, t)
    return dict(kind='window', subtype='sliding', a=a, b=b, t=t, host='wall', either=(side != 'blocked'),
                ev=ev + [f'sliding sashes ({n_lines} lines)'] + (['planter / kerb / edge along it outside'] if side == 'blocked'
                                                                 else ['may be a floor-length sliding door (no sill in plan)']),
                conf=conf - (0.1 if side == 'blocked' else 0.25), swings=[], src='glazing')


def opens_onto_paving(fl, a, b, t):
    """A hatched floor area (paving, deck) directly against one face of the glazing over most of its width, with no
    planting (clusters of small loose shapes) on it within 2.5 m."""
    if not getattr(fl, 'floor_hatches', None): return False
    u = unit(sub(b, a)); w = math.dist(a, b)
    for sgn in (1, -1):
        zone = rect(a, u, 0.0, w, sgn * (t / 2 + 0.02), sgn * (t / 2 + 0.6))
        if not any(g.intersects(zone) and g.intersection(zone).area >= 0.3 * zone.area for g in fl.floor_hatches): continue
        far = rect(a, u, 0.0, w, sgn * (t / 2 + 0.02), sgn * (t / 2 + 2.5))
        if sum(1 for g, p in fl.jambs if far.contains(g.centroid)) >= 5: continue
        return True
    return False


def outside_free(fl, a, b, t):
    """For glazing on the building's edge: is the floor just outside it free to walk onto (no planter, kerb, strip
    edge, overhang line or wall running along it within 1.3 m)? -> 'free' | 'blocked' | 'interior' (enclosed both sides)."""
    u = unit(sub(b, a)); n = perp(u); w = math.dist(a, b)
    m = mul(add(a, b), 0.5)
    hits = []
    for sgn in (1, -1):
        hh = 0
        for ang in (0, 30, -30):
            ca, sa = math.cos(math.radians(ang)), math.sin(math.radians(ang))
            v = add(mul(n, sgn * ca), mul(u, sa))
            if fl.OB.cover(add(m, mul(n, sgn * (t / 2 + 0.05))), v, 8.0): hh += 1
        hits.append(hh)
    if hits[0] and hits[1] and min(hits) >= 2: return 'interior'
    sgn = 1 if hits[0] < hits[1] else -1                         # the open (outside) side
    SI = fl.SI
    x0, y0 = min(a[0], b[0]) - 1.6, min(a[1], b[1]) - 1.6
    idx = SI.near_box(x0, y0, max(a[0], b[0]) + 1.6, max(a[1], b[1]) + 1.6)
    if len(idx):
        s0, s1, la, lb, cs = SI.in_frame(idx, a, u)
        d = sgn * (la + lb) / 2 - t / 2
        ok = (cs > math.cos(math.radians(5))) & (d >= 0.12) & (d <= 1.3) & (np.minimum(s1, w) - np.maximum(s0, 0) >= 0.5 * w)
        if ok.any(): return 'blocked'
    side_w = fl.G.cover(add(m, mul(n, sgn * (t / 2 + 0.02))), mul(n, sgn), 1.3)
    return 'blocked' if side_w else 'free'


def pocket_doors(fl):
    """Sliding leaves drawn half out of a wall pocket where the wall simply ends (no gap to find): a thin panel
    partly inside the wall solid, leaving it through the wall's end. The door runs from that wall end along the
    panel to the next wall, to the line of a second such door met at a corner, or else to the panel's outer end."""
    G = fl.G
    cands = []
    for p in fl.P:
        if p.poly is None or p.i in fl.used_panels or p.roles & {'wall', 'column', 'window', 'glass'}: continue
        mrr = p.poly.minimum_rotated_rectangle
        xs = list(mrr.exterior.coords)
        e1, e2 = math.dist(xs[0], xs[1]), math.dist(xs[1], xs[2])
        thin, long_ = min(e1, e2), max(e1, e2)
        if not (0.015 <= thin <= 0.07 and 0.6 <= long_ <= 3.5): continue
        a_, b_ = (xs[0], xs[1]) if e1 >= e2 else (xs[1], xs[2])
        off = mul(sub(xs[2], xs[1]) if e1 >= e2 else sub(xs[0], xs[1]), 0.5)
        c0, c1 = add(a_, off), add(b_, off)                           # centre line of the panel
        u = unit(sub(c1, c0))
        iv = G.cover(c0, u, long_)
        inside = sum(y - x for x, y in iv)
        if not (0.2 * long_ <= inside <= 0.85 * long_): continue
        # it must leave the wall at one end only
        if iv[0][0] <= 0.02 and iv[-1][1] >= long_ - 0.02: continue
        if iv[0][0] <= 0.02:
            exit_s, d = iv[0][1], u
            start = add(c0, mul(u, exit_s)); outer = long_ - exit_s
        elif iv[-1][1] >= long_ - 0.02:
            exit_s, d = iv[-1][0], (-u[0], -u[1])
            start = add(c0, mul(u, exit_s)); outer = exit_s
        else:
            continue
        cands.append(dict(p=p, start=start, d=d, outer=outer, long=long_))
    out = []
    for k, c in enumerate(cands):
        n = perp(c['d'])
        far = G.cover(add(c['start'], mul(c['d'], 0.02)), c['d'], 3.0)
        end, how = None, None
        if far and far[0][0] <= max(2.6, c['outer'] + 0.6):
            end, how = far[0][0] + 0.02, 'next wall'
        for j, o in enumerate(cands):                                 # a second pocket door met at a corner
            if j == k or ang_diff(o['d'], c['d']) < 75: continue
            den = dot(c['d'], perp(o['d']))
            if abs(den) < 0.5: continue
            s = dot(sub(o['start'], c['start']), perp(o['d'])) / den
            if c['outer'] - 0.05 <= s <= c['outer'] + 1.0 and (end is None or s < end): end, how = s, 'corner with another pocket door'
        if end is None: end, how = c['outer'], 'outer end of the leaf'
        if end < 0.5: continue
        sec = G.section(add(c['start'], mul(c['d'], -0.05)), n, 0.6)
        own = [x for x in sec if x[0] - 0.05 <= 0 <= x[1] + 0.05]
        t, ml = (own[0][1] - own[0][0], (own[0][0] + own[0][1]) / 2) if own and own[0][1] - own[0][0] <= 0.6 else (0.1, 0.0)
        a = add(c['start'], mul(n, ml)); b = add(a, mul(c['d'], end))
        out.append(dict(kind='door', subtype='pocket sliding', a=a, b=b, t=t, host='wall', conf=0.6, swings=[], src='pocket',
                        ev=[f'sliding leaf on {c["p"].lay} half out of a wall pocket', 'far end: ' + how]))
    return out


def gap_contents(fl, g):
    """What is drawn inside a gap besides swings and glazing: sliding / pocket leaves (a thin panel or a single line
    along the gap that runs on into the wall) and frame pieces standing inside it (stiles of a sliding unit)."""
    SI = fl.SI
    box = rect(g.a, g.u, -0.8, g.w + 0.8, -g.t / 2 - 0.08, g.t / 2 + 0.08)
    x0, y0, x1, y1 = box.bounds
    idx = SI.near_box(x0, y0, x1, y1)
    if len(idx):
        s0, s1, la, lb, cs = SI.in_frame(idx, g.a, g.u)
        ok = (cs > math.cos(math.radians(3))) & (np.maximum(np.abs(la), np.abs(lb)) <= g.t / 2 + 0.05) & \
             (s1 - s0 >= 0.3) & (np.minimum(s1, g.w) - np.maximum(s0, 0) >= 0.1)
        seen = set()
        for k in np.nonzero(ok)[0]:
            p = fl.P[SI.pid[idx[k]]]
            if p.i in seen or p.roles & {'wall', 'column', 'window', 'glass'}: continue
            seen.add(p.i)
            in0, in1 = s0[k] < -0.15, s1[k] > g.w + 0.15
            into_wall = in0 or in1
            if p.poly is not None:
                mrr = p.poly.minimum_rotated_rectangle
                xs = list(mrr.exterior.coords)
                e1, e2 = math.dist(xs[0], xs[1]), math.dist(xs[1], xs[2])
                thin, long_ = min(e1, e2), max(e1, e2)
                if 0.015 <= thin <= 0.07 and long_ >= 0.4 and (into_wall or long_ >= 0.6 * g.w):
                    g.panels.append(('pocket panel' if into_wall else 'sliding panel', p.lay))
                    g.notes.append(f'panel#{p.i}')
            elif (in0 != in1) and abs((la[k] + lb[k]) / 2) <= 0.04 and p.cont:
                cover = min(s1[k], g.w) - max(s0[k], 0.0)
                if cover <= 0.85 * g.w:                     # a leaf slid part-way out of its pocket on one side
                    g.panels.append(('pocket line', p.lay))
        # both faces of the wall drawn on across the gap on another layer: a low wall / sill below the cut plane
        faces = {}
        for k in np.nonzero((cs > math.cos(math.radians(3))) & (s1 - s0 >= 0.3))[0]:
            p = fl.P[SI.pid[idx[k]]]
            if p.roles & {'wall', 'column', 'window', 'glass', 'door'} or not p.cont: continue
            if p.poly is not None and p.poly.area > 1.0: continue          # room / area outlines run along faces
            l = (la[k] + lb[k]) / 2
            for side in (1, -1):
                if abs(l - side * g.t / 2) <= 0.03 and abs(la[k] - lb[k]) <= 0.01:
                    faces.setdefault(side, []).append((max(s0[k], 0.0), min(s1[k], g.w)))
        def covered(iv):
            iv = sorted(x for x in iv if x[1] > x[0]); tot, reach = 0.0, 0.0
            for a_, b_ in iv:
                a_ = max(a_, reach)
                if b_ > a_: tot += b_ - a_; reach = b_
            return tot
        if len(faces) == 2 and g.w >= 0.6 and all(covered(v) >= 0.9 * g.w for v in faces.values()):
            g.notes.append('both wall faces drawn on across the gap (low wall or sill)')
            g.panels.append(('low wall', ''))
    hl = g.t / 2 + 0.03
    for poly, p in fl.jambs:
        if p.roles & {'wall', 'column'}: continue
        s, l = g.frame((poly.centroid.x, poly.centroid.y))
        if 0.15 <= s <= g.w - 0.15 and abs(l) <= hl: g.jambs.append(p)


def narrow_to_symbol(fl, g):
    """A door whose swings cover much less than the wall gap (jambs drawn on another layer, the wall stopping short):
    take the ends from the jambs beside the swings."""
    ss = [g.frame(q)[0] for h in g.swings for q in (h.hinge, h.closed)]
    lo, hi = min(ss), max(ss)
    if g.w - (hi - lo) <= 0.35: return
    hl = g.t / 2 + 0.1
    left = jamb_at(fl, g.a, g.u, g.n, lo - 0.3, lo + 0.05, -hl, hl)
    right = jamb_at(fl, g.a, g.u, g.n, hi - 0.05, hi + 0.3, -hl, hl)
    if not left or not right: return
    jl = max(left, key=lambda j: j[1]); jr = min(right, key=lambda j: j[0])
    s0 = jl[0] if jl[2] <= 0.08 else jl[1]
    s1 = jr[1] if jr[2] <= 0.08 else jr[0]
    if s1 - s0 < 0.4: return
    g.a, g.b = g.at(s0), g.at(s1)
    g.w = s1 - s0
    g.ev.append('ends on jambs beside the swings')


def is_free_post(fl, p):
    """The material at p is a free-standing post or column: a small squarish piece of the wall solid (glazing
    included) with nothing else within 0.15 m (carport columns, pergola posts)."""
    part = [q for q in fl.OB.parts if q.distance(Point(p)) < 0.03]
    if len(part) != 1: return False
    q = part[0]
    x0, y0, x1, y1 = q.bounds
    big, small = max(x1 - x0, y1 - y0), min(x1 - x0, y1 - y0)
    if big > 0.8 or small < 0.5 * big: return False
    near = q.buffer(0.15)
    return not any(r is not q and r.intersects(near) for r in fl.OB.parts)


def crosses_stair(fl, g):
    """Stair treads or flights (stair-role line work) inside the gap: a stair end, not an opening in a wall."""
    SI = fl.SI
    box = rect(g.a, g.u, 0.05, g.w - 0.05, -g.t / 2, g.t / 2)
    idx = SI.near_box(*box.bounds)
    for k in idx:
        p = fl.P[SI.pid[k]]
        if 'stair' not in p.roles: continue
        A = SI.A[k]
        if LineString([(A[0], A[1]), (A[2], A[3])]).intersects(box): return True
    return False


def passage_ok(fl, g):
    """A gap with nothing drawn in it is a passage only when it looks like one: both ends are wall ends on one wall
    line (up to 3.6 m), or a short gap (up to 1.6 m) from a wall end to the side of a wall or pier that carries on;
    and there is building on both sides of it."""
    if g.near == 'T' or g.t < 0.07: return False
    run = fl.G.cover(sub(g.b, mul(g.u, 0.005)), g.u, 0.5)
    far_run = run[0][1] if run and run[0][0] <= 0.01 else 0.0      # does the wall line carry on past the far end?
    if g.far == 'end':
        if not (0.6 <= g.w <= (3.6 if g.near == 'cap' else 2.5)): return False
        if g.near == 'L' and far_run < 0.2: return False
    elif g.far == 'face':
        if not (0.6 <= g.w <= 1.6) or far_run < 0.3: return False
    else:
        return False
    for p in (g.at(-0.02), g.at(g.w + 0.02)):                       # a free-standing post is not a wall end
        if is_free_post(fl, p): return False
    if crosses_stair(fl, g): return False
    if g.near == 'cap' and g.far == 'end': return True
    m = g.at(g.w / 2)
    for sgn in (1, -1):
        hit = False
        for ang in (0, 35, -35):
            ca, sa = math.cos(math.radians(ang)), math.sin(math.radians(ang))
            v = mul(add(mul(g.n, sgn * ca), mul(g.u, sa)), 1.0)
            if fl.OB.cover(add(m, mul(mul(g.n, sgn), g.t / 2 + 0.02)), v, 10.0):
                hit = True; break
        if not hit: return False
    return True


def fuse(openings):
    """The same opening found twice (both wall faces, two leaves of a double wall, a gap and a swing): keep one.
    Doors beat windows beat passages; then the better-founded gap; then the thicker wall."""
    rank = {'door': 0, 'window': 1, 'passage': 2}
    order = sorted(range(len(openings)), key=lambda i: (rank[openings[i]['kind']], -openings[i]['conf'],
                                                        {'end': 0, 'face': 1}.get(openings[i].get('far'), 2), -openings[i]['t']))
    keep = []
    for i in order:
        o = openings[i]
        u = unit(sub(o['b'], o['a'])); w = math.dist(o['a'], o['b'])
        dup = False
        for k in keep:
            q = openings[k]
            uq = unit(sub(q['b'], q['a'])); wq = math.dist(q['a'], q['b'])
            if ang_diff(u, uq) > 8: continue
            mo = mul(add(o['a'], o['b']), 0.5)
            lat = abs(dot(sub(mo, q['a']), perp(uq)))
            if lat > max(o['t'], q['t']) / 2 + 0.2: continue
            s = sorted((dot(sub(o['a'], q['a']), uq), dot(sub(o['b'], q['a']), uq)))
            ov = min(s[1], wq) - max(s[0], 0.0)
            if ov >= 0.5 * min(w, wq):
                dup = True; break
        if not dup: keep.append(i)
    return [openings[i] for i in sorted(keep)]


def host_lines(fl, c, u, L, lat=0.3):
    """Line work of any kept layer running along the chord (a wall or facade drawn on another layer, or a wall drawn
    straight through): -> (lines ending at / passing the start, lines ending at / passing the end)."""
    SI = fl.SI
    n = perp(u)
    e = add(c, mul(u, L))
    idx = SI.near_box(min(c[0], e[0]) - 0.5, min(c[1], e[1]) - 0.5, max(c[0], e[0]) + 0.5, max(c[1], e[1]) + 0.5)
    if not len(idx): return 0, 0
    s0, s1, la, lb, cs = SI.in_frame(idx, c, u)
    ok = (cs > math.cos(math.radians(3))) & (np.maximum(np.abs(la), np.abs(lb)) <= lat) & (s1 - s0 >= 0.15)
    at0 = ok & (s1 >= -0.25) & (s1 <= 0.12) | ok & (s0 < -0.05) & (s1 > 0.05)
    at1 = ok & (s0 >= L - 0.12) & (s0 <= L + 0.25) | ok & (s0 < L - 0.05) & (s1 > L + 0.05)
    return int(at0.sum()), int(at1.sum())


def symbol_door(fl, h, h2=None):
    """A door read from its swing(s) alone (no gap in the wall solid): the wall band beside the chord gives the
    centre line, wall ends, glazing or jambs within reach give the ends; otherwise the chord itself.
    h2: the second leaf of a double door (closed tips meeting)."""
    OB = fl.OB
    p0, p1 = (h.hinge, h.closed) if h2 is None else (h.hinge, h2.hinge)
    u = unit(sub(p1, p0))
    L = math.dist(p0, p1)
    n = perp(u)
    side = 1 if dot(sub(h.open, p0), n) < 0 else -1               # the wall lies on side*n of the chord
    band = None
    for s in (-0.08, L + 0.08, L / 2):                             # just outside each end; in the middle (drawn through)
        sec = OB.section(add(p0, mul(u, s)), n, 0.6)
        sec = [(a, b) for a, b in sec if b - a <= 0.6 and (a * side >= -0.03 or b * side >= -0.03) and min(abs(a), abs(b)) <= 0.08]
        if sec:
            band = min(sec, key=lambda ab: min(abs(ab[0]), abs(ab[1])))
            break
    if band:
        mlat, t = (band[0] + band[1]) / 2, band[1] - band[0]
    else:
        mlat, t = 0.0, 0.1
    c = add(p0, mul(n, mlat))
    iv = OB.cover(add(c, mul(u, -0.6)), u, L + 1.2)
    iv = [(x - 0.6, y - 0.6) for x, y in iv]
    inside = any(x <= L / 2 <= y for x, y in iv)
    s0, s1, how = 0.0, L, []
    end0 = end1 = False
    if not inside:
        left = [y for x, y in iv if y <= L / 2]
        right = [x for x, y in iv if x >= L / 2]
        if left and -0.35 <= max(left) <= 0.1: s0 = max(left); how.append('wall end'); end0 = True
        if right and L - 0.1 <= min(right) <= L + 0.35: s1 = min(right); how.append('wall end'); end1 = True
    hl = abs(t) / 2 + 0.06
    if not end0:                                                   # jambs: frame pieces or wall stubs, any layer
        js = jamb_at(fl, c, u, n, -0.3, 0.12, -hl, hl)
        if js:
            j = max(js, key=lambda j: j[1])
            s0 = j[0] if j[2] <= 0.08 else j[1]; how.append('jamb'); end0 = True
    if not end1:
        js = jamb_at(fl, c, u, n, L - 0.12, L + 0.3, -hl, hl)
        if js:
            j = min(js, key=lambda j: j[0])
            s1 = j[1] if j[2] <= 0.08 else j[0]; how.append('jamb'); end1 = True
    h0, h1 = host_lines(fl, c, u, L)
    if 'glass' in h.p.roles and fl.G.dist(p0) > 0.15 and fl.G.dist(p1) > 0.15:
        return None                                                # a glass door in a glass (shower) screen
    if h2 is not None and len(how) < 2:
        return None                                                # two arcs alone: furniture (fridge, cabinet)
    if not how and not band:
        # no wall, jamb or glazing anywhere near: only a well-drawn leaf in line work that runs past both ends
        if h2 is None and not (h.leaf and h.leaf[1] >= 0.8 * h.r and 40 <= h.sweep <= 100 and h0 and h1):
            if OB.dist(p0) > 0.6: return None
    a, b = add(c, mul(u, s0)), add(c, mul(u, s1))
    sub_ = 'hinged single' if h2 is None else 'hinged double'
    ev = [('swing arc + leaf on ' if h.leaf else 'swing arc on ') + h.p.lay] + (['second leaf, closed tips meet'] if h2 else [])
    ev += ['ends: ' + ', '.join(how)] if how else ['ends from the swing']
    if h0 and h1 and not band: ev.append('line work along the opening on ' + 'another layer')
    return dict(kind='door', subtype=sub_, a=a, b=b, t=t, host='wall' if band else ('line work' if (h0 and h1) else 'none'),
                ev=ev, conf=0.5 + 0.15 * len(how), swings=[h] if h2 is None else [h, h2], src='swing')


# ================================================================================================ 7. output
def finish(fl, ops, floor_name):
    out = []
    for k, o in enumerate(ops, 1):
        a, b = o['a'], o['b']
        hinge, swing = None, None
        if o['kind'] == 'door' and len(o['swings']) == 1:
            h = o['swings'][0]
            hinge = 'a' if math.dist(h.hinge, a) < math.dist(h.hinge, b) else 'b'
            side = cross(sub(b, a), sub(h.open, h.hinge))
            swing = 'left' if side > 0 else 'right'
        out.append({'id': f"{floor_name.split(':')[-1]}-{k:03d}", 'floor': floor_name, 'kind': o['kind'],
                    'subtype': o['subtype'], 'a': [round(float(a[0]), 4), round(float(a[1]), 4)],
                    'b': [round(float(b[0]), 4), round(float(b[1]), 4)],
                    'width': round(math.dist(a, b), 3), 'wallThickness': round(float(o['t']), 3), 'host': o['host'],
                    'hinge': hinge, 'swing': swing, 'confidence': round(o['conf'], 2), 'evidence': o['ev'],
                    'eitherKind': bool(o.get('either'))})
    return out


def run(mapping_path, out_path, png_dir=None):
    mp = json.loads(Path(mapping_path).read_text(encoding='utf-8'))
    t0 = time.time()
    D = prims.load(mp['cache'])
    scale = UNITS[mp.get('units', 'mm')]
    roles = role_matcher(mp['layers'])
    result, floors = [], {}
    for area, floor_name in mp['floors'].items():
        items = dedupe([d for d in D['items'] if d.get('area') == area])
        fl = Floor(floor_name, items, D['layers'], roles, scale)
        ops = detect_floor(fl)
        res = finish(fl, ops, floor_name)
        result += res
        floors[floor_name] = (fl, res)
        print(f'{floor_name}: {len(res)} openings ({", ".join(f"{k} {sum(1 for o in res if o["kind"] == k)}" for k in ("door", "window", "passage"))})'
              f'  {fl.T["total"]:.1f} s')
    Path(out_path).write_text(json.dumps({'openings': result, 'mapping': str(mapping_path)}, indent=1), encoding='utf-8')
    if png_dir:
        import render_openings
        Path(png_dir).mkdir(parents=True, exist_ok=True)
        for name, (fl, res) in floors.items():
            render_openings.draw(fl, res, Path(png_dir) / f"openings_{name.replace(':', '_')}.png")
    print(f'total {time.time() - t0:.1f} s -> {out_path}')
    return floors


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('mapping'); ap.add_argument('out'); ap.add_argument('--png')
    a = ap.parse_args()
    run(a.mapping, a.out, a.png)


if __name__ == '__main__':
    main()
