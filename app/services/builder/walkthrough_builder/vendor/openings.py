"""Find door, window and passage openings in a CAD floor plan (Phase 0 of the walkthrough tool).

Usage:  python openings.py <mapping.json> <out.json> [--png DIR]
        (DIR gets one top-view PNG per floor: doors red, windows blue, passages green, ids labelled)

Input: the flattened drawing cache (tools/prims.py) named in the mapping, and the mapping's layer roles (wall, column,
glass, window, screen, door, stair, ignore). Ignored layers are dropped; everything else is read from the geometry, on
any layer. The roles are used for the wall solid (wall, column), for glazing bands (window, glass), for screens
(grilles, louvres: never glazing), as a tie-breaker hint (door, window) and to keep stair flights out of passages.
Block names are not used. Optional: the mapping's "areas" say where each floor's plan sits on the sheet ({area: {"bbox": [x0,
y0, x1, y1] in drawing metres, "pad", "match": "all" | "any"} or {"wholeFile": true}}); without them the area tags of
the drawing cache are used (the four Phase 0 mappings give layer roles only); with them a new drawing needs no code.
Output: {"openings": [{id, floor, kind, subtype, a, b, width, wallThickness, host, hinge, swing, confidence, evidence,
eitherKind, glazing[, sidelights]}, ...]} with a and b on the wall centre line at the faces of the wall ends (drawing
metres); glazing = [lo, hi], where the glazing lines lie across the line a->b (metres, + = left of a->b), or null;
sidelights (doors only, when fixed glass beside the leaf was cut off, rule 4) = [{a, b, layers}, ...].

Rules (all lengths are physical sizes in metres, the same for every drawing):
 1. Wall solid: wall/column-layer fills, thin closed outlines (mean width <= 0.35 m) and face lines paired 4-45 cm
    apart (continuous linetypes only); cracks and corner squares closed. Wider closed outlines (room outlines) and
    small pieces (< 0.15 m) are not walls.
 2. Gaps: wall strips are pairs of opposite faces of the wall solid. From each strip end, look along its centre line
    for the next wall material; the stretch between is a gap, typed by its near end (cap / L-corner / T) and far end
    (the end of a collinear strip of the same thickness, or the face of another wall). A strip is 3 cm long at least:
    a door set against a cross wall leaves wall ends of 3-8 cm. A jamb return or pier (a stub up to 0.275 m deep
    standing proud of a wall end on ONE face, the centre line and the other face ending together) does not move the
    end: the gap is measured on the centre line, between the wall end faces.
 3. Door swings: arcs on any layer (r 0.28-2 m, sweep 20-125 deg). Which end is the closed leaf: a leaf (line or thin
    rectangle) drawn toward the other end, and the closed tip lying on the wall. Leaves of swings are never read as
    sliding panels.
 4. Each swing goes to the gap that fits it best; the leaves must account for at least 55 % of the gap. Two leaves
    whose closed tips meet are a double door, also when drawn in front of a deep reveal. Swings on a window/glass layer
    in a gap whose glazing is drawn across the whole gap (closed position) are casement windows. A swing in no gap
    (wall drawn through, wall not drawn, glazed screen) is a door from the symbol: its chord is turned onto the
    nearest wall face direction around it (up to 10 deg: a flattened arc gives a skewed chord) and snapped to wall
    ends, glazing or jambs (small closed shapes on any layer) within 0.35 m. Dropped: glass doors in glass (shower)
    screens, leaves closing against a single wall-layer line drawn unbroken through the chord (a door in a one-line
    screen), and pairs of arcs with nothing to bound them (furniture).
    Fixed sidelights: a door ends at its leaf (hinge to closed tip) where fixed glass stands beside it. The opening (the
    gap's wall ends, or the wall end / jamb a symbol snapped to) stands 0.17 m or more beyond the leaf and glass-layer
    lines (window / glass roles, 0.08 m or more long) cover half of that stretch or more: a sidelight, drawn as part of
    the glass partition. It is no part of the door; it is listed in the door's record (sidelights: ends and layers) and
    named in its evidence, and it is no window either (a glazing band under 0.5 m is no bay, rule 5). Frames, reveals
    and mullions (under 0.17 m beyond the leaf) stay part of the door. Not trimmed: glass drawn only as hatch, as pieces
    under 0.08 m, or lying more than 5 cm outside the wall faces; a leaf outside its gap; a door that would be left under
    0.5 m wide.
 5. Glazing: parallel lines on window/glass layers grouped into bands. A band in a gap glazes it; when the gap was
    measured from a block shorter than it is thick (a corner block) and the glazing stands outside that block, the
    window takes the glazing's own line. A band in no gap is a bay when wall ends / columns in its own line (or a
    post-less glass corner) bound it within 0.25 m, or a window inside a drawn-through wall when the wall is thinner
    over it or jambs bound it. Glass walls, not openings: a glass screen from one cross wall to another; glass from
    the side of a cross wall round a post-less corner (a shower, a glass box); one side of an all-glass corridor (a
    parallel band opposite), also when it stands in a gap that is not between two wall ends of one wall line.
    Curtain walls, not openings (glazing on glass layers with no window-layer line; the mullions, caps and fins of a
    curtain wall are wall-layer pieces standing on its glass line): a window's glazing stops at its wall ends, so glass
    that runs on past them by more than 0.7 m is not the gap's own, and a gap whose own glazing does not fill 80 % of
    it is no opening; glass-only glazing lying along a wall strip that runs on unbroken (the frame of a module)
    is no bay; a bay needs wall ends / columns in its own line at both ends, not a corner or a cross wall at one.
    Fixed glazing is a window; sliding sashes are a window (flagged eitherKind) unless they open straight onto a
    hatched floor (terrace, deck) with no planting, then a sliding glass door.
 6. Other gap contents: a thin panel or a centre-line leaf running into a wall pocket (the line's part past the gap
    lies in the wall), or a leaf drawn shut across the gap on a door layer (lift doors) = sliding door. So is a leaf
    drawn as line work (two long lines 15-70 mm apart on a door layer, ends level) within the wall depth + 0.10 m (in
    a wall pocket, or on a track just outside the wall face) that runs on past a gap end or across 60 % of the gap,
    when the leaves together make up 70 % of the gap and the gap is not between two stubs (pocket sliding when the
    leaf lies inside the wall faces). Both wall faces drawn on across a gap between two wall ends = opening over a
    low wall (window); two or more frame pieces standing inside = frame-only sliding unit (window); screen lines
    along the gap = closed by a screen (no opening).
    Elsewhere: a sliding leaf half out of a pocket where the wall simply ends = pocket door (to the next wall or to
    the line of a second pocket door met at a corner); three or more frame pieces in a row from one wall face to
    another = frame-only sliding unit.
    Thin glass screens: a screen drawn as a wall strip under 3 cm (a thin closed outline or a hatch, 5-30 mm; two
    separate lines that thin are not paired into a strip) is no wall for rules
    2-7 (a window or passage in every gap of every screen would be false). Only a gap of 0.6-6 m that starts at a free
    end of such a screen (0.3 m or more of it) is read, and only with sliding leaves in it: thin rectangles on a door
    layer (two parallel lines 12-70 mm apart, 0.4-2 m long, within 0.15 m of the gap's line, 0.1 m or more of each
    inside it; a hinged leaf's lines excluded) that are together at least 80 % as long as the gap = sliding door. The
    leaves are often drawn half open over the fixed glass beside the gap, so they run past its ends.
 7. A gap with nothing in it is a passage only when it looks like one: both ends wall ends of one wall line (<= 3.6 m;
    <= 2.75 m from an L-corner), or a short gap (<= 1.6 m) from a wall end to a wall face that carries on; not stub
    to stub (wall ends under 0.3 m: pilasters, kerbs) unless the opening's frame is drawn (door-layer lines across
    the wall at both ends) or both free ends are found as wall ends of their own, each belonging to a wall of 0.8 m or
    more (not a row of free-standing piers), and the gap is <= 1.6 m (a doorway set against cross walls); not at a
    free-standing post (a small piece of any orientation, up to 0.9 m long and at least half as wide, with nothing within
    15 cm); not across a stair (stair lines coming more than 3 cm
    into the wall band: an outline along a face, or treads stopping at it, mean a stair hall beside the gap, whose
    door it is); not on walls thinner than 7 cm; building on both sides; not in front of a glass wall (glazing along the
    gap over 90 % of it within 0.6 m behind it: a recess, nowhere to go).
    A passage interrupts a wall line: an opening cuts the wall through and the wall carries on past it. Mouths are not
    passages: one wall end or corner facing the side of another wall across an aisle or a corridor (a partition end
    short of the wall, a corridor seen in section). So a gap is kept when the faces of its wall go on in line past the
    far end for 0.6 m or more, after a jamb piece of 0.225 m at most (the free end of a wall of the same thickness, or of
    another thickness with one face in line; the corner of a wall that turns away is not that: its end face is as long as
    the wall is thick, and 0.6 m is more than the thickest wall); or when its opening frame is drawn; or when its far
    end is a wall end of the same thickness found as such; or when the far end is centred on the line and goes on along
    it for 0.6 m (a wall of another thickness, a pier, a column: it stands out 0.35 m at most past each face, evenly;
    the side of a wall across the line stands out by metres); or when the centre line meets no face at the far end (a
    diagonal or ragged end: no mouth to speak of); or when it is door-sized (<= 1.45 m) and its far end is a corner
    whose face is flush with a face of the gap's wall. Not a passage whatever the ends: a face of the wall drawn
    unbroken across the gap (a recess or niche, a fitting standing in the wall: the wall is not cut through).
    Known limits: a far wall turned away from the line by more than 2 degrees (a kinked facade) is not a continuation;
    a doorway beside a cross wall thicker than 0.225 m with the wall carrying on beyond it cannot be told from a corridor
    crossing and is dropped; thick-cornered, ragged-end and framed mouths are kept (no geometry tells them apart).
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
MULLION = 0.20      # m: widest mullion, frame member or reveal (curtain-wall mullions, caps and fins are 50-200 mm)
RUNS_ON = 0.7       # m: glass-layer glazing that runs on past a gap's wall ends by more than this is a longer glazed line (a
                    #    curtain wall with its wall pieces standing on it), not the gap's own window. The six floors give the
                    #    same result from 0.2 to 1.1 m (frames and reveals run on by 0.2 m at most; the smallest overshoot of a
                    #    curtain-wall gap is 0.98 m, the others 1.15 m or more; at 1.2 m a false window enters on L30); 0.7 m is
                    #    off the drawn sizes 0.5 / 0.6 m (a window drawn into a deep reveal is still a window)
EPS = 0.0005        # m: a limit is compared 0.5 mm generous in the direction its author meant (coordinates are rounded: a 0.1 m
                    #    overlap comes out as 0.09999999999999931 m on one sheet position and 0.1000000000000003 m on another).
                    #    Inclusive limits get + EPS; a thickness limit that must exclude a drawn size (STRIP_MAX) gets - EPS


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
    try:
        W = unary_union([g.buffer(0) for g in pieces]) if pieces else Polygon()
    except Exception:                       # GEOS 'found two shells in EdgeRing list' on near-degenerate pieces: snap to a 1 micrometre grid
                                            # (the same openings to within 5 mm; ids may be numbered in another order)
        import shapely
        W = shapely.union_all([g.buffer(0) for g in pieces], grid_size=1e-6)
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


STRIP_MAX = 0.55 - EPS        # m: a wall piece this thick is no wall strip (bank1: a 0.55 m pier beside a double door read as a gap end of 2.42 m)
SCREEN_MAX = 0.03 + EPS       # m: thin glass screens are 5-30 mm; walls start just above, so no thickness falls between the two calls


def find_strips(W, tmin=SCREEN_MAX, tmax=STRIP_MAX, min_len=0.03):
    """Pairs of opposite faces of the wall solid (parallel boundary edges with opposite outward normals, tmin..tmax
    apart, overlapping) -> wall strips, whatever the walls were drawn with (lines, outlines, fills). Faces shorter
    than min_len are not looked at."""
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
        if L[i] < min_len: continue
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
        ok = (t >= tmin) & (t < tmax) & (np.abs(ta - tb) < 0.01) & (hi - lo >= 0.03)
        if not ok.any(): continue
        k = np.nonzero(ok)[0]
        tbest = t[k].min()
        for kk in k[t[k] <= tbest + 0.003]:
            c = (a[0] - n[0] * t[kk] / 2, a[1] - n[1] * t[kk] / 2)
            strips.append(Strip(c, (float(u[0]), float(u[1])), float(lo[kk]), float(hi[kk]), float(t[kk])))
    return strips


class Gap:
    __slots__ = ('a', 'b', 'u', 'n', 't', 'w', 'near', 'far', 'swings', 'bands', 'through', 'panels', 'kind', 'sub', 'ev',
                 'conf', 'jambs', 'notes', 'either', 'nlen', 'flen', 'how_end')

    def __init__(self, a, b, t, near, far):
        self.a, self.b, self.t, self.near, self.far = a, b, t, near, far
        self.u = unit(sub(b, a)); self.n = perp(self.u); self.w = math.dist(a, b)
        self.swings, self.bands, self.panels, self.kind, self.sub, self.ev, self.conf = [], [], [], None, '', [], 0.0
        self.through = []                      # glass-layer bands that run on past the wall ends (see detect_floor)
        self.jambs, self.notes, self.either = [], [], False
        self.nlen, self.flen, self.how_end = 0.0, 0.0, ''

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


# Limit checked against the answer keys (fourth office, L29 / L30; the nearest cases in brackets): the 0.115 m
# return of the L30 cavity slider's thin skin (0.12 m already finds it), the 0.21 m jamb piers of the L29 lift doors
# (0.22 m finds them), and the first change on an older drawing, a presidential passage whose far end has a 0.34 m
# step (from 0.34 m on). The six floors are identical from 0.21 to 0.33 m; 0.275 m is the middle of that and off the
# drawn sizes 0.25 / 0.30 m (L29 has a stub of exactly 0.25 m, which a limit of 0.25 m decided by rounding).
JAMB_RETURN = 0.275        # m: a stub up to this deep on one face of a wall end is a jamb return or pier, not wall


def one_face_step(v):
    """v: the three lines across a wall end (face, centre, face). When the centre line and one face agree (3 cm) and the
    other face differs: how far that other face stands off from the centre line's value, else None (a stub on ONE face)."""
    for odd, same in ((0, 2), (2, 0)):
        if abs(v[same] - v[1]) <= 0.03 and abs(v[odd] - v[1]) > 0.03: return v[odd] - v[1]
    return None


def strip_gaps(fl, G, strips, dmin=0.3, dmax=7.0):
    """From every wall end (a strip that stops, with or without a perpendicular wall right after it) look along the
    wall's centre line for the next wall material: the stretch between is a candidate opening on that wall line.
    Every strip counts, down to the 3 cm of find_strips: a door set against a cross wall leaves a wall end of 3-4 cm
    (the reveal between the frame and the cross wall)."""
    gaps = []
    for S in sorted(strips, key=lambda S: S.s1 - S.s0 < 0.04):               # ends under 4 cm last: gaps are added, not reordered
        for sgn in (1, -1):
            u = S.u if sgn > 0 else (-S.u[0], -S.u[1])
            n = perp(u)
            p = S.at(S.s1 if sgn > 0 else S.s0)
            prof = end_profile(G, p, u, n, S.t, dmax + 0.7)
            d0s = [x[0] for x in prof]; d1s = [x[1] for x in prof]
            if any(d is None for d in d1s): continue
            d0 = d0s[1]
            # A jamb return or pier (a stub up to JAMB_RETURN deep standing proud of the wall end on ONE face; the
            # centre line and the other face end together) does not move the end: measure on the centre line.
            st0, st1 = one_face_step(d0s), one_face_step(d1s)
            jamb0 = d0 <= 0.02 and st0 is not None and 0 < st0 <= JAMB_RETURN + EPS
            if d0 > 0.6 or (max(d0s) - min(d0s) > 0.03 and not jamb0): continue   # wall goes on / end not square
            d1 = d1s[1] if st1 is not None and -JAMB_RETURN - EPS <= st1 < 0 else min(d1s)   # the same stub at the far end
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
            g.nlen = S.s1 - S.s0
            gaps.append(g)
    # far end on a collinear wall strip of about the same thickness -> 'wall end'
    # (numpy pre-filter on thickness, direction and lateral offset, then the exact tests on the survivors: the same result
    # as the plain double loop, which costs 10 us per gap-strip pair - 800 thin screens took 24 s)
    if gaps and strips:
        ST = np.array([S.t for S in strips]); SUx = np.array([S.u[0] for S in strips]); SUy = np.array([S.u[1] for S in strips])
        SCx = np.array([S.c[0] for S in strips]); SCy = np.array([S.c[1] for S in strips])
        SNx = np.array([S.n[0] for S in strips]); SNy = np.array([S.n[1] for S in strips])
    cos2 = math.cos(math.radians(2.0)) - 1e-6
    for g in gaps:
        pre = ()
        if strips:
            lat = (g.b[0] - SCx) * SNx + (g.b[1] - SCy) * SNy                       # across the strip's centre line
            pre = np.nonzero((np.abs(ST - g.t) <= 0.04 + 1e-9) & (np.abs(SUx * g.u[0] + SUy * g.u[1]) >= cos2) &
                             (np.abs(lat) <= 0.03 + 1e-9))[0]
        for i in pre:
            S = strips[i]
            if abs(S.t - g.t) > 0.04 or ang_diff(S.u, g.u) > 2: continue
            s, l = dot(sub(g.b, S.c), S.u), dot(sub(g.b, S.c), S.n)
            if abs(l) > 0.03: continue
            if min(abs(s - S.s0), abs(s - S.s1)) <= 0.03 or (S.s0 - 0.03 <= s <= S.s1 + 0.03):
                g.far = 'end'; g.flen = S.s1 - S.s0; g.how_end = 'collinear strip'; break
    # the same gap is found from both of its ends: keep one
    out = []
    for g in sorted(gaps, key=lambda g: ({'cap': 0, 'L': 1, 'T': 2}[g.near], {'end': 0, 'face': 1, 'corner': 2}[g.far])):
        dup = False
        for h in out:
            if ((math.dist(g.a, h.a) < 0.06 and math.dist(g.b, h.b) < 0.06) or
                    (math.dist(g.a, h.b) < 0.06 and math.dist(g.b, h.a) < 0.06)) and ang_diff(g.u, h.u) < 3:    # cheap test first
                dup = True
                # Found twice. Every strip comes in two oriented copies (one per face pair), so the same near end is found
                # twice as a rule and says nothing about the far end: 'end' here only means "not typed by a strip". Whether
                # the wall carries on past the far end is judged by passage_ok (interrupts_wall_line).
                if h.far != 'end' and g.near in ('cap', 'L'): h.far = 'end'; h.how_end = 'found from both ends'
                h.flen = max(h.flen, g.nlen)
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
    ok = (cs > math.cos(math.radians(14))) & (lat <= 0.10) & (s0 >= -0.10) & (s0 <= 0.2) & (s1 - s0 >= 0.4 * r) & (s1 <= r + 0.15)
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
        s -= 1 if G.dist(h.open) <= 0.05 + EPS else 0
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
            out += [(g, p) for g in polys(p.poly)]                  # a self-crossing outline buffers to several polygons
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
    fl.edges = wall_edges(G)
    strips = find_strips(W)
    gaps = strip_gaps(fl, G, strips)
    T['walls'] = time.time() - t0
    SI = SegIndex(fl)
    bands = glazing_bands(fl, SI)
    swings = door_swings(fl, SI)
    fl.jambs = small_shapes(fl)
    fl.leaf_prims = {int(SI.pid[h.leaf[0]]) for hyps in swings for h in hyps if h.leaf}   # leaves hinged on an arc
    fl.floor_hatches = [g for g in (even_odd(p.d['loops']) for p in fl.P if 'loops' in p.d and not (p.roles & {'wall', 'column'}))
                        if not g.is_empty and g.area >= 2.0]
    fl.SI, fl.G, fl.bands, fl.swings, fl.strips, fl.gaps = SI, G, bands, swings, strips, gaps
    T['line work'] = time.time() - t0

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
            if hi - lo >= 0.4 * g.w:
                # A window's glazing stops at the wall ends. Glass-layer glazing that runs on past them (by more than
                # RUNS_ON) is a longer glazed line with the wall pieces standing on it, not this gap's glazing.
                runs_on = max(-min(s0, s1), max(s0, s1) - g.w) > RUNS_ON + EPS and 'window' not in b.roles
                (g.through if runs_on else g.bands).append(b)
        gap_contents(fl, g)

    openings = []
    fl.used_panels = set()
    for g in gaps:
        if g.near == 'T': continue
        base = f'wall gap ({g.near}-{g.far})'
        if g.swings and band_cover(g) >= 0.8 * g.w and not any('door' in h.p.roles for h in g.swings):
            # sashes with frame and glass lines drawn across the whole gap in the closed position: casement window
            # (80 % cover: Sukhumvit UE-05's glazing covers 86 % of its gap, so 0.9 would lose it)
            g.kind, g.sub = 'window', 'casement' + (f' ({len(g.swings)} sashes)' if len(g.swings) > 1 else '')
            g.ev = [base, f'{len(g.swings)} swing arc(s)', 'glazing drawn across the whole gap (closed position)'] +                 sorted(set(l for b in g.bands for l in b.lays))
            g.conf = 0.7
        elif g.swings:
            g.kind = 'door'
            nsw = len(g.swings)
            g.sub = 'hinged single' if nsw == 1 else ('hinged double' if nsw == 2 else f'{nsw}-leaf set')
            g.ev = [base, f'{nsw} swing arc(s)'] + sorted(set('arc on ' + h.p.lay for h in g.swings)) + g.notes
            g.conf = 0.9
            narrow_to_symbol(fl, g)
        elif any(p[0] in ('sliding panel', 'pocket panel', 'closed leaf') for p in g.panels) and not (
                g.bands and not any(p[0] in ('sliding panel', 'pocket panel') for p in g.panels)):
            g.kind, g.sub = 'door', 'sliding' if not any(p[0].startswith('pocket') for p in g.panels) else 'pocket sliding'
            if any(p[0] == 'closed leaf' for p in g.panels) and g.sub == 'sliding': g.sub = 'sliding (leaf drawn closed)'
            g.ev = [base] + sorted(set(f'{k} on {lay}' for k, lay in g.panels if k != 'low wall'))
            g.conf = 0.75
        elif g.through and band_cover(g) < 0.8 * g.w:
            # the glazing runs on past the wall pieces and nothing of its own fills the gap: a curtain wall (fins, caps
            # and mullions standing on a long glass line), not a window in a wall
            for b in g.through + g.bands: b.used = True
            continue
        elif g.bands:
            for b in g.through + g.bands: b.used = True
            if not (g.near == 'cap' and g.far == 'end') and any(glazed_corridor(b, bands) for b in g.bands):
                # one side of an all-glass corridor (a link or bridge) running from a wall corner to a wall face: a
                # glass wall, as when the same glass stands in no gap (below). A window in a wall line sits between
                # two wall ends of that line (cap-end).
                continue
            lays = sorted(set(l for b in g.bands for l in b.lays))
            # A gap measured from a block shorter than it is thick (a corner block, the end of a cross wall) has no
            # wall line of its own: when the glazing stands outside that block, the window is set on the glazing's
            # own line (as deep as the glazing, at least 0.1 m).
            off, t_win, ev_line = 0.0, g.t, []
            if g.nlen < g.t:
                ls = [g.frame(b.at(b.s0, l))[1] for b in g.bands for l in (b.l0, b.l1)]
                lo_, hi_ = min(ls), max(ls)
                if abs((lo_ + hi_) / 2) > g.t / 2:
                    off, t_win, ev_line = (lo_ + hi_) / 2, max(hi_ - lo_, 0.1), ['on the line of its glazing (outside the block it was measured from)']
            for s0, s1, kind, nl in glazing_units(fl, g.bands, g.a, g.u, g.w):
                a, b = g.at(s0, off), g.at(s1, off)
                o = glazed_opening(fl, a, b, t_win, kind, nl, [base, 'glazing band'] + lays + ev_line, 0.8)
                o['far'] = g.far
                openings.append(o)
            continue
        elif any(p[0] == 'low wall' for p in g.panels):
            g.kind, g.sub, g.ev, g.conf = 'window', 'opening over a low wall (no glass drawn)', [base] + g.notes, 0.5
        elif any(p[0] == 'pocket line' for p in g.panels):
            g.kind, g.sub = 'door', 'pocket sliding'
            g.ev = [base] + sorted(set(f'{k} on {lay}' for k, lay in g.panels))
            g.conf = 0.65
        elif len(g.jambs) >= 2:
            g.kind, g.sub, g.ev, g.conf = 'window', 'sliding (frame only, no glass drawn)', [base, f'{len(g.jambs)} frame pieces inside the gap'], 0.55
        elif screened(fl, g):
            continue                    # a grille or screen drawn across the gap closes it: no opening to cut
        else:
            if not passage_ok(fl, g): continue
            g.kind, g.sub, g.ev, g.conf = 'passage', 'open', [base + ', nothing drawn in it'], 0.5 if g.far == 'end' else 0.4
            if framed(fl, g): g.ev.append('opening frame drawn (door-layer jamb lines at both ends)'); g.conf = 0.6
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
                    if not (0.3 - EPS <= hi.r <= 1.3 + EPS and 0.3 - EPS <= hj.r <= 1.3 + EPS): continue
                    o = symbol_door(fl, hi, hj) or symbol_door(fl, hj, hi)      # not symmetric in its two leaves: try both orders
                    if o:
                        openings.append(o); done |= {i, j}; hi.used = hj.used = True
    for k, hyps in enumerate(free):
        if k in done: continue
        h = pick_swing(hyps, OB)
        if h is None or not h.leaf: continue
        if not (0.45 - EPS <= h.r <= 1.6 + EPS and 25 <= h.sweep <= 110): continue
        o = symbol_door(fl, h)
        if o: openings.append(o); h.used = True

    T['gaps and swings'] = time.time() - t0
    openings += pocket_doors(fl)
    openings += frame_rows(fl)
    T['pockets and frames'] = time.time() - t0

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
        # glass that runs from the face of one cross wall to another is a glass wall, not a window, when it is a
        # screen on a glass layer (shower screens, pool glass) or one side of a glazed corridor (a parallel band
        # opposite it); a window in a wall line has a wall end / column in its own line at one end at least. Glass
        # that turns a post-less corner is a window corner only when its other end is such a wall end: glass from
        # the side of a cross wall round a corner is a glass enclosure (a shower, a glass box), whatever its layer.
        # Glazing on glass layers only (no window-layer line: curtain walls, screens, fins) is a window between wall
        # ends in line at both ends only.
        inline = [e == 'wall' and in_line_end(G, b, se, lm) for e, se in ((ends[0], s0 - 0.03), (ends[1], s1 + 0.03))]
        glass_only = 'window' not in b.roles
        if glazed_corridor(b, bands) or not (all(inline) if glass_only else (any(inline) or 'corner' not in ends)): continue
        if glass_only and along_wall(fl, b): continue   # glass against a wall that runs on unbroken: nothing is cut in that wall
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
    openings += screen_doors(fl)                                # sliding leaves in a gap of a thin glass screen
    for o in openings:                                          # fixed glass beside a leaf is part of the partition
        if o['kind'] == 'door' and o['swings']: trim_to_leaf(fl, o)
    openings = fuse(openings)
    T['total'] = time.time() - t0
    fl.T = T
    if T['total'] > SLOW_FLOOR:
        steps = list(T.items()); prev = 0.0; parts = []
        for k, v in steps[:-1]: parts.append(f'{k} {v - prev:.0f} s'); prev = v
        print(f'WARNING {fl.name}: detection took {T["total"]:.0f} s ({", ".join(parts)}); a layer of many small shapes '
              f'(tiles, hatch lines, symbols) that is not mapped to "ignore" is the usual cause.', file=sys.stderr)
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


def along_wall(fl, b, share=0.8):
    """Does a wall strip run along glazing band b - parallel to it, its faces within a mullion width of the glass lines -
    over at least 80 % of the band? Glass standing against a wall that is not interrupted there (the frame of a
    curtain-wall module, a facing) is not a window in a gap of that wall."""
    iv = []
    for S in fl.strips:
        if ang_diff(S.u, b.u) > 3: continue
        ss = [dot(sub(S.at(x), b.c), b.u) for x in (S.s0, S.s1)]
        ds = [dot(sub(S.at(x), b.c), b.n) for x in (S.s0, S.s1)]
        lo, hi = max(min(ss), b.s0), min(max(ss), b.s1)
        if hi <= lo or ss[1] == ss[0]: continue
        d = ds[0] + (ds[1] - ds[0]) * (((lo + hi) / 2 - ss[0]) / (ss[1] - ss[0]))      # strip centre line, mid-overlap
        if max(d - S.t / 2 - b.l1, b.l0 - d - S.t / 2) <= MULLION: iv.append((lo, hi))
    covered, reach = 0.0, b.s0
    for lo, hi in sorted(iv):
        lo = max(lo, reach)
        if hi > lo: covered += hi - lo; reach = hi
    return covered >= share * b.length


def in_line_end(G, b, s, lm):
    """Is the wall material just past a glazing end a wall end, pier or column standing in the glazing's own line
    (narrow across it), rather than the long side of a cross wall?"""
    sec = G.section(b.at(s, lm), b.n, 1.5)
    own = [x for x in sec if x[0] - 0.02 <= 0 <= x[1] + 0.02]
    if own and own[0][1] - own[0][0] <= 0.65: return True             # a pier / column / wall end
    sgn = 1 if s > (b.s0 + b.s1) / 2 else -1                          # or the wall line carries on past the end
    run = G.cover(b.at(s - sgn * 0.03, lm), mul(b.u, sgn), 0.6)
    return bool(run) and run[0][0] <= 0.04 and run[0][1] >= 0.33


def glazed_corridor(b, bands):
    """Another glazing band parallel to b, 0.8-3.5 m away and overlapping most of it: b is one side of a glazed
    corridor (a link or bridge whose sides are all glass)."""
    if b.length < 2.5: return False
    for b2 in bands:
        if b2 is b or ang_diff(b.u, b2.u) > 3 or not (0.7 <= b2.length / b.length <= 1.43): continue
        d = abs(dot(sub(b2.at((b2.s0 + b2.s1) / 2), b.at((b.s0 + b.s1) / 2)), b.n))
        if not (0.8 <= d <= 3.5): continue
        s = sorted(dot(sub(b2.at(x), b.c), b.u) for x in (b2.s0, b2.s1))
        if min(s[1], b.s1) - max(s[0], b.s0) >= 0.6 * min(b.length, b2.length): return True
    return False


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


def edge_aligned(g, u, tol=5.0):
    """Is one of the polygon's rectangle edges parallel (or square) to u?"""
    xs = list(g.minimum_rotated_rectangle.exterior.coords)
    e = unit(sub(xs[1], xs[0]))
    a = ang_diff(e, u)
    return a <= tol or a >= 90 - tol


SLOW_FLOOR = 60.0          # seconds per floor above which a warning names the slow steps
FRAME_ROWS_MAX = 3000      # small shapes against walls above which frame-only units are not looked for (see the warning)


def frame_rows(fl):
    """A sliding unit drawn with its frame pieces only (end pieces, stiles, meeting squares; no glass lines): three or
    more small frame shapes in a straight row spanning from one wall face to another with no wall between.
    A valid row ends on wall faces, so rows are only walked from pieces within 0.4 m of a wall (its end pieces), and
    neighbours are found through a grid of 1.65 m cells: the cost grows with the pieces near walls, not with the
    square of all small shapes (a floor with a tiled or symbol layer left unmapped stays fast)."""
    G = fl.G
    pcs = [(g, p) for g, p in fl.jambs if not (p.roles & {'wall', 'column'})]
    cen = [(g.centroid.x, g.centroid.y) for g, p in pcs]
    CELL = 1.65
    grid = {}
    for k, (x, y) in enumerate(cen): grid.setdefault((math.floor(x / CELL), math.floor(y / CELL)), []).append(k)

    def near(q):
        cx, cy = math.floor(q[0] / CELL), math.floor(q[1] / CELL)
        return sorted(k for dx in (-1, 0, 1) for dy in (-1, 0, 1) for k in grid.get((cx + dx, cy + dy), ()))
    aligned = {}

    def al(k, u):
        key = (k, round(u[0], 9), round(u[1], 9))
        if key not in aligned: aligned[key] = edge_aligned(pcs[k][0], u)
        return aligned[key]
    out, used = [], set()
    if not G.parts: return out
    starts = [k for k in range(len(pcs)) if G.dist(cen[k]) <= 0.4]
    if len(starts) > FRAME_ROWS_MAX:
        print(f'WARNING {fl.name}: {len(starts)} small shapes stand against walls (more than {FRAME_ROWS_MAX}); frame-only '
              f'sliding units are not looked for. Map tile, hatch or symbol layers to "ignore".', file=sys.stderr)
        return out
    free_memo = {}

    def free_between(k, q):
        key = (min(k, q), max(k, q))
        if key not in free_memo:
            dd = math.dist(cen[k], cen[q])
            free_memo[key] = not G.cover(cen[k], unit(sub(cen[q], cen[k])), dd) if dd > 1e-6 else True
        return free_memo[key]
    for i in starts:
        if i in used: continue
        for j in near(cen[i]):
            if j == i or j in used: continue
            d = math.dist(cen[i], cen[j])
            if not (0.3 <= d <= 1.6): continue
            u = unit(sub(cen[j], cen[i])); n = perp(u)
            # frame pieces are drawn square to their window: the row must run along their edges
            if not all(edge_aligned(pcs[k][0], u) for k in (i, j)): continue
            inrow = lambda k: abs(dot(sub(cen[k], cen[i]), n)) <= 0.06 and al(k, u)
            sv = lambda k: dot(sub(cen[k], cen[i]), u)
            # the connected run (steps <= 1.6 m, no wall between neighbours) that holds i, walked both ways from i
            run = [i]
            for sgn in (1, -1):
                end = i
                while True:
                    se = sv(end) * sgn
                    cands = [k for k in near(cen[end]) if k not in run and inrow(k) and sv(k) * sgn >= se]
                    if not cands: break
                    nxt = min(cands, key=lambda k: sv(k) * sgn)
                    step = sv(nxt) * sgn - se
                    if step > 1.6 or not free_between(end, nxt): break
                    run.append(nxt); end = nxt
            if len(run) < 3: continue
            run.sort(key=sv)
            k0, k1 = run[0], run[-1]
            g0, g1 = pcs[k0][0], pcs[k1][0]
            s_lo = min(dot(sub(q, cen[i]), u) for q in g0.exterior.coords)
            s_hi = max(dot(sub(q, cen[i]), u) for q in g1.exterior.coords)
            if s_hi - s_lo < 0.8: continue
            lat = sum(dot(sub(cen[k], cen[i]), n) for k in run) / len(run)
            c = add(cen[i], mul(n, lat))
            iv = G.cover(add(c, mul(u, s_lo - 0.1)), u, s_hi - s_lo + 0.2)
            iv = [(x + s_lo - 0.1, y + s_lo - 0.1) for x, y in iv]
            if any(x > s_lo + 0.05 and y < s_hi - 0.05 for x, y in iv): continue   # a wall in between
            left = [y for x, y in iv if y <= s_lo + 0.05]; right = [x for x, y in iv if x >= s_hi - 0.05]
            if not left or not right or abs(max(left) - s_lo) > 0.06 or abs(min(right) - s_hi) > 0.06: continue
            sec = G.section(add(c, mul(u, s_lo - 0.05)), n, 0.6)
            own = [x for x in sec if x[0] - 0.15 <= 0 <= x[1] + 0.15]
            t, ml = (own[0][1] - own[0][0], (own[0][0] + own[0][1]) / 2) if own and own[0][1] - own[0][0] <= 0.6 else (0.1, 0.0)
            a = add(add(c, mul(u, s_lo)), mul(n, ml)); b = add(add(c, mul(u, s_hi)), mul(n, ml))
            used |= set(run)
            out.append(dict(kind='window', subtype='sliding (frame only, no glass drawn)', a=a, b=b, t=t, host='wall',
                            ev=[f'{len(run)} frame pieces in a row between two wall faces'], conf=0.5, swings=[], src='frames'))
            break
    return out


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


def line_leaves(fl, g, idx, s0, s1, la, lb, cs):
    """Sliding leaves drawn with line work (CAD exports draw a leaf as four lines, not as one closed outline): two long
    straight lines 15-70 mm apart (a leaf's thickness) on a door layer, their ends level, running along the gap within
    the wall's depth + 0.10 m (a leaf in a wall pocket, or on a track just outside the wall face: its outer line lies
    at most 0.03 m of clearance + 0.07 m of thickness off the face) and on past a gap end, or across most of the gap.
    Together they must be able to close the gap: their lengths add up to at least 70 % of it (the clear opening of a
    leaf set is the gap less two frames or returns of 0.15 m at most, so 70 % holds for a gap of 1 m and up). Not
    between two stubs (jamb returns, posts: under 0.3 m of wall each side), as for a passage: there is no wall line for
    a leaf to run in. -> [(kind, layer)]: 'pocket panel' inside the wall faces, 'sliding panel' outside them.
    Checked on the six drawings: the face-mounted pair of L30 covers 100 % of its gap with its outer line 0.06 m off
    the face, the L30 cavity slider 86 % with the leaves inside the wall; changing 70 % to anything from 30 to 100 %
    changes no output, and the window must reach 0.06 m beyond the face for the face-mounted pair (0.10 m used;
    nothing else changes from 0.08 to 0.25 m)."""
    SI = fl.SI
    if max(g.nlen, g.flen) < 0.3: return []
    # a leaf line is level within 1 cm (5 mm lost L30's 4.8 m slider with 3 mm of noise on the vertices; the screen leaves use 1 cm too)
    ok = (cs > math.cos(math.radians(3))) & (np.abs(la - lb) <= 0.01) & (s1 - s0 >= 0.4) & \
         (np.minimum(s1, g.w) - np.maximum(s0, 0) >= 0.1 - EPS) & (np.maximum(np.abs(la), np.abs(lb)) <= g.t / 2 + 0.10)
    cand = []
    for k in np.nonzero(ok)[0]:
        p = fl.P[SI.pid[idx[k]]]
        if 'door' in p.roles and p.cont and not p.roles & {'wall', 'column', 'window', 'glass', 'screen'} and p.i not in fl.leaf_prims:
            cand.append(k)
    panels, total, used = [], 0.0, set()
    for i, k in enumerate(cand):
        for m in cand[i + 1:]:
            if k in used or m in used: continue
            if not (0.015 <= abs((la[k] + lb[k]) / 2 - (la[m] + lb[m]) / 2) <= 0.07): continue
            if abs(s0[k] - s0[m]) > 0.03 or abs(s1[k] - s1[m]) > 0.03: continue            # ends level: a rectangle
            lo, hi = float(min(s0[k], s0[m])), float(max(s1[k], s1[m]))
            into_wall = lo < -0.15 or hi > g.w + 0.15
            if not (into_wall or hi - lo >= 0.6 * g.w): continue
            used |= {k, m}
            inside = abs((la[k] + lb[k] + la[m] + lb[m]) / 4) <= g.t / 2
            panels.append(('pocket panel' if (inside and into_wall) else 'sliding panel', fl.P[SI.pid[idx[k]]].lay))
            total += hi - lo
    return panels if total >= 0.7 * g.w else []


def screen_leaves(fl, g, reach=0.15):
    """Sliding leaves along a gap: thin rectangles on a door layer (two parallel lines 12-70 mm apart, drawn the same
    length, 0.4-2 m long; the lines of a hinged leaf are left out) that run along the gap within `reach` of its centre
    line with at least 0.1 m of their length inside it. -> [(s0, s1), ...] along the gap, one per leaf (a leaf drawn
    half open over the fixed glass beside the gap runs past the gap's end)."""
    SI = fl.SI
    idx = SI.near_box(*rect(g.a, g.u, -2.0, g.w + 2.0, -reach, reach).bounds)
    if not len(idx): return []
    s0, s1, la, lb, cs = SI.in_frame(idx, g.a, g.u)
    ok = (cs > math.cos(math.radians(3))) & (np.abs(la - lb) <= 0.01) & (np.maximum(np.abs(la), np.abs(lb)) <= reach) & \
         (s1 - s0 >= 0.4) & (s1 - s0 <= 2.0) & (np.minimum(s1, g.w) - np.maximum(s0, 0.0) >= 0.1 - EPS)
    rows = []
    for k in np.nonzero(ok)[0]:
        p = fl.P[SI.pid[idx[k]]]
        if 'door' in p.roles and not p.roles & {'wall', 'column', 'window', 'glass'} and p.i not in fl.leaf_prims:
            rows.append((float(s0[k]), float(s1[k]), float((la[k] + lb[k]) / 2)))
    leaves = []
    for i, (a0, a1, al) in enumerate(rows):
        for b0, b1, bl in rows[i + 1:]:
            if abs(a0 - b0) <= 0.02 and abs(a1 - b1) <= 0.02 and 0.012 <= abs(al - bl) <= 0.07:
                lf = ((a0 + b0) / 2, (a1 + b1) / 2)
                if not any(abs(lf[0] - x[0]) <= 0.05 and abs(lf[1] - x[1]) <= 0.05 for x in leaves): leaves.append(lf)
    return sorted(leaves)


def screen_doors(fl):
    """Sliding doors in thin glass screens (a screen here is a wall strip thinner than 3 cm: a glass pane drawn as a
    hatch or a double line, 5-30 mm; not the 'screen' layer role). Such a strip is no wall for rules 2-7, which would
    make a window or a passage of every gap in every glass screen. Only a gap of 0.6-6 m that starts at a free end of
    a screen (0.3 m or more of screen) is read, and only when sliding leaves stand in it: leaf panels (screen_leaves)
    that are together at least 80 % as long as the gap, leaves that could close it. The gap runs from the screen end
    to the next wall material (the other screen end, a wall, a column)."""
    out = []
    screens = [S for S in find_strips(fl.W, 0.005, SCREEN_MAX, 0.3) if S.s1 - S.s0 >= 0.3]
    for g in strip_gaps(fl, fl.G, screens, 0.6, 6.0):
        if g.near != 'cap': continue
        leaves = screen_leaves(fl, g)
        total = sum(b - a for a, b in leaves)
        if total < 0.8 * g.w: continue
        out.append(dict(kind='door', subtype='sliding (leaves beside a glass screen)', a=g.a, b=g.b, t=g.t, host='wall',
                        ev=[f'gap in a thin glass screen (cap-{g.far})', f'{len(leaves)} leaf panel(s) on a door layer, '
                            f'{total:.2f} m of leaf for a {g.w:.2f} m gap'],
                        conf=0.7, swings=[], src='screen', far=g.far))
    return out


def gap_contents(fl, g):
    """What is drawn inside a gap besides swings and glazing: sliding / pocket leaves (a thin panel, a leaf drawn as two
    lines, or a single line along the gap that runs on into the wall) and frame pieces standing inside it (stiles of a
    sliding unit)."""
    SI = fl.SI
    box = rect(g.a, g.u, -0.8, g.w + 0.8, -g.t / 2 - 0.12, g.t / 2 + 0.12)
    x0, y0, x1, y1 = box.bounds
    idx = SI.near_box(x0, y0, x1, y1)
    if len(idx):
        s0, s1, la, lb, cs = SI.in_frame(idx, g.a, g.u)
        ok = (cs > math.cos(math.radians(3))) & (np.maximum(np.abs(la), np.abs(lb)) <= g.t / 2 + 0.05) & \
             (s1 - s0 >= 0.3) & (np.minimum(s1, g.w) - np.maximum(s0, 0) >= 0.1 - EPS)
        seen = set()
        for k in np.nonzero(ok)[0]:
            p = fl.P[SI.pid[idx[k]]]
            if p.i in seen or p.roles & {'wall', 'column', 'window', 'glass'} or p.i in fl.leaf_prims: continue
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
                # the part past the gap's end must lie in the wall (the pocket): a line that runs on through the
                # wall and out of its far side is line work crossing the gap (planting, paving), not a leaf
                st, ln = (g.at(float(s0[k])), float(-s0[k])) if in0 else (g.at(g.w), float(s1[k] - g.w))
                in_pocket = sum(y - x for x, y in fl.G.cover(st, g.u, ln)) >= 0.8 * ln
                if cover <= 0.85 * g.w and in_pocket:       # a leaf slid part-way out of its pocket on one side
                    g.panels.append(('pocket line', p.lay))
        g.panels += line_leaves(fl, g, idx, s0, s1, la, lb, cs)
        # a leaf drawn closed across the gap on a door layer (lift doors, sliding doors shown shut)
        closed_leaf = []
        for k in np.nonzero((cs > math.cos(math.radians(3))) & (s1 - s0 >= 0.3))[0]:
            p = fl.P[SI.pid[idx[k]]]
            if 'door' not in p.roles or p.roles & {'wall', 'column', 'window', 'glass'}: continue
            if max(abs(la[k]), abs(lb[k])) > g.t / 2 + 0.03: continue
            closed_leaf.append((max(s0[k], 0.0), min(s1[k], g.w), p.lay))
        if closed_leaf:
            iv = sorted((a_, b_) for a_, b_, _ in closed_leaf if b_ > a_)
            tot, reach = 0.0, 0.0
            for a_, b_ in iv:
                a_ = max(a_, reach)
                if b_ > a_: tot += b_ - a_; reach = b_
            if tot >= 0.8 * g.w:
                g.panels.append(('closed leaf', closed_leaf[0][2]))
        # both faces of the wall drawn on across the gap on another layer: a low wall / sill below the cut plane
        faces = {}
        for k in np.nonzero((cs > math.cos(math.radians(3))) & (s1 - s0 >= 0.3))[0]:
            p = fl.P[SI.pid[idx[k]]]
            if p.roles & {'wall', 'column', 'window', 'glass', 'door', 'screen'} or not p.cont: continue
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
        if len(faces) == 2 and g.w >= 0.6 and g.near == 'cap' and g.far == 'end' and                 all(covered(v) >= 0.9 * g.w for v in faces.values()):
            g.notes.append('both wall faces drawn on across the gap (low wall or sill)')
            g.panels.append(('low wall', ''))
    hl = g.t / 2 + 0.03
    for poly, p in fl.jambs:
        if p.roles & {'wall', 'column'}: continue
        s, l = g.frame((poly.centroid.x, poly.centroid.y))
        if 0.15 <= s <= g.w - 0.15 and abs(l) <= hl: g.jambs.append(p)


def screened(fl, g):
    """Lines on a screen layer (grilles, louvres) running along the gap within its wall faces (0.1 m beyond them at
    most) over at least 80 % of it: the gap is closed by a screen, like a wall drawn in another way."""
    SI = fl.SI
    box = rect(g.a, g.u, -0.2, g.w + 0.2, -g.t / 2 - 0.12, g.t / 2 + 0.12)
    idx = SI.near_box(*box.bounds)
    if not len(idx): return False
    s0, s1, la, lb, cs = SI.in_frame(idx, g.a, g.u)
    iv = []
    for k in np.nonzero((cs > math.cos(math.radians(3))) & (np.maximum(np.abs(la), np.abs(lb)) <= g.t / 2 + 0.1))[0]:
        if 'screen' in fl.P[SI.pid[idx[k]]].roles: iv.append((max(float(s0[k]), 0.0), min(float(s1[k]), g.w)))
    tot, reach = 0.0, 0.0
    for a_, b_ in sorted(iv):
        a_ = max(a_, reach)
        if b_ > a_: tot += b_ - a_; reach = b_
    return tot >= 0.8 * g.w


def band_cover(g):
    """Length of the gap covered by its glazing bands."""
    iv = []
    for b in g.bands:
        s = sorted(g.frame(b.at(x))[0] for x in (b.s0, b.s1))
        iv.append((max(s[0], 0.0), min(s[1], g.w)))
    tot, reach = 0.0, 0.0
    for a_, b_ in sorted(iv):
        a_ = max(a_, reach)
        if b_ > a_: tot += b_ - a_; reach = b_
    return tot


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


# Limits checked on the six drawings (fixed sidelights, rule 4). SIDELIGHT_MIN: every door end of the older drawings and
# of L30 stands 0.14 m or less beyond its leaf (frames, reveals, 0.10 m mullions), the four sidelit doors of L29 stand
# 0.20-0.28 m beyond (panes 0.20-0.28 m wide). Nothing changes for any value from 0.02 to 0.20 m; from 0.2005 m the 0.20 m
# panes are lost (tower 53, from 0.201 m 50 of 54 right). 0.17 m is in the middle of the empty stretch between the widest
# frame (0.14 m) and the narrowest pane (0.20 m), and away from the drawn size 0.15 m, which float noise would split (a
# symmetric door with two 150 mm panes came out trimmed on one side only in half of the placements on the sheet).
# SIDELIGHT_SHARE: a pane is drawn as two glass lines that stop at the wall end and at the hinge hardware, so the stretch
# beside the hinge is covered 85 % (0.17 of 0.20 m) and the one beside the closed tip 100 %; no other door end stands
# 0.15 m or more beyond its leaf, so any share from 0 to 0.84 gives the same result: 0.5 asks for "mostly glass".
SIDELIGHT_MIN = 0.17       # m: a fixed pane beside a leaf is wider than a frame, reveal or mullion
SIDELIGHT_SHARE = 0.5      # share of that stretch the glass-layer lines must cover
NARROWEST_DOOR = 0.5       # m: a door cut down to its leaf is at least this wide (and four fifths of the chord of its swing)


def glass_share(fl, c, u, s0, s1, lat):
    """The glass beside a door: -> (share, layers). share: how much of the stretch s0..s1 (along u from c) glass covers:
    straight lines of 0.08 m or more (shorter ones are frame stubs, as in glazing_bands) on window / glass layers running
    along it, within lat of its line (a pane is two lines a few mm apart). layers: the layers those lines are on."""
    SI = fl.SI
    if s1 <= s0: return 0.0, []
    p, q = add(c, mul(u, s0)), add(c, mul(u, s1))
    idx = SI.near_box(min(p[0], q[0]) - lat, min(p[1], q[1]) - lat, max(p[0], q[0]) + lat, max(p[1], q[1]) + lat)
    if not len(idx): return 0.0, []
    a0, a1, la, lb, cs = SI.in_frame(idx, c, u)
    ok = (cs > math.cos(math.radians(3))) & (np.maximum(np.abs(la), np.abs(lb)) <= lat) & (SI.L[idx] >= 0.08)
    iv, lays = [], set()
    for k in np.nonzero(ok)[0]:
        pr = fl.P[SI.pid[idx[k]]]
        if pr.roles & {'window', 'glass'} and not pr.roles & {'wall', 'column'}:
            lo_, hi_ = max(float(a0[k]), s0), min(float(a1[k]), s1)
            iv.append((lo_, hi_))
            if hi_ - lo_ > EPS: lays.add(pr.lay)
    tot, reach = 0.0, s0
    for a_, b_ in sorted(iv):
        a_ = max(a_, reach)
        if b_ > a_: tot += b_ - a_; reach = b_
    return tot / (s1 - s0), sorted(lays)


def trim_to_leaf(fl, o):
    """A door ends at its leaf where fixed glass stands beside it: the opening was read from the wall ends of the gap
    (or the wall end / jamb the symbol snapped to) and stands SIDELIGHT_MIN or more beyond the leaf, with glass-layer
    lines along that stretch (a sidelight, drawn as part of the glass partition). The glass is not part of the door; it
    is listed in the record ('sidelights') and the evidence, so that it is not lost."""
    a, b = o['a'], o['b']
    u = unit(sub(b, a)); w = math.dist(a, b)
    ss = [dot(sub(q, a), u) for h in o['swings'] for q in (h.hinge, h.closed)]
    lo, hi = min(ss), max(ss)
    lat = o['t'] / 2 + 0.05
    s0, s1, cut = 0.0, w, []
    if lo >= SIDELIGHT_MIN - EPS:
        share, lays = glass_share(fl, a, u, 0.0, lo, lat)
        if share >= SIDELIGHT_SHARE - 1e-9: s0 = lo; cut.append((0.0, lo, lays))
    if w - hi >= SIDELIGHT_MIN - EPS:
        share, lays = glass_share(fl, a, u, hi, w, lat)
        if share >= SIDELIGHT_SHARE - 1e-9: s1 = hi; cut.append((hi, w, lays))
    if not cut: return
    if not (0.0 <= s0 < s1 <= w) or s1 - s0 < max(NARROWEST_DOOR, 0.8 * (hi - lo)) - EPS: return     # a leaf outside its gap: no door left
    o['a'], o['b'] = add(a, mul(u, s0)), add(a, mul(u, s1))
    o['ev'] = o['ev'] + ['fixed glass beside the leaf (sidelight): the door ends at the leaf; glass left out: ' +
                         ' + '.join(f'{t1 - t0:.2f} m' for t0, t1, lays in cut) + ' of ' +
                         ', '.join(sorted({l for t0, t1, lays in cut for l in lays}))]
    o['sidelights'] = [{'a': [round(float(x), 4) for x in add(a, mul(u, t0))], 'b': [round(float(x), 4) for x in add(a, mul(u, t1))],
                        'layers': lays} for t0, t1, lays in cut]
    o['sidelit'] = True


def is_free_post(fl, p):
    """The material at p is a free-standing post or column: a small squarish piece (up to 0.9 m) of the wall solid
    (glazing included) with nothing else within 0.15 m (carport columns, pergola posts, round columns)."""
    part = [q for q in fl.OB.parts if q.distance(Point(p)) < 0.03]
    if len(part) != 1: return False
    q = part[0]
    x0, y0, x1, y1 = q.bounds
    if max(x1 - x0, y1 - y0) > 0.9 * math.sqrt(2) + EPS: return False                 # no post of 0.9 m is wider than its diagonal
    mrr = q.minimum_rotated_rectangle
    if mrr.geom_type != 'Polygon': return False
    xs = list(mrr.exterior.coords)
    e1, e2 = math.dist(xs[0], xs[1]), math.dist(xs[1], xs[2])
    big, small = max(e1, e2), min(e1, e2)
    if big > 0.9 + EPS or small < 0.5 * big - EPS: return False
    near = q.buffer(0.15)
    return not any(r is not q and r.intersects(near) for r in fl.OB.parts)


def crosses_stair(fl, g):
    """Stair treads or flights (stair-role line work) inside the gap: a stair end, not an opening in a wall. Only line
    work that comes into the wall band counts (more than 3 cm inside both faces): the outline of a stair hall drawn
    along a wall face, or treads that stop at it, say that the room beside the gap is a stair hall, and the gap is its
    door. (A hall outline lies 0 cm inside the face; the stair lines that cross a gap in the older plans cross the
    whole band or come 8 cm into it.)"""
    SI = fl.SI
    box = rect(g.a, g.u, 0.05, g.w - 0.05, -g.t / 2 + 0.03, g.t / 2 - 0.03)
    idx = SI.near_box(*box.bounds)
    for k in idx:
        p = fl.P[SI.pid[k]]
        if 'stair' not in p.roles: continue
        A = SI.A[k]
        if LineString([(A[0], A[1]), (A[2], A[3])]).intersects(box): return True
    return False


def framed(fl, g):
    """A doorless opening drawn with its frame: a line on a door layer across the wall band at each end of the gap
    (the jambs of an opening symbol, within 3 cm of the wall ends, spanning the wall thickness)."""
    SI = fl.SI
    box = rect(g.a, g.u, -0.05, g.w + 0.05, -g.t / 2 - 0.05, g.t / 2 + 0.05)
    idx = SI.near_box(*box.bounds)
    if not len(idx): return False
    s0, s1, la, lb, cs = SI.in_frame(idx, g.a, g.u)
    ends = set()
    for k in np.nonzero(cs < math.sin(math.radians(3)))[0]:                 # square to the wall line
        p = fl.P[SI.pid[idx[k]]]
        if 'door' not in p.roles or p.roles & {'wall', 'column', 'window', 'glass'}: continue
        lo, hi = sorted((float(la[k]), float(lb[k])))
        if hi - lo < 0.8 * g.t or lo < -g.t / 2 - 0.05 or hi > g.t / 2 + 0.05: continue
        for e, s in enumerate((0.0, g.w)):
            if abs((s0[k] + s1[k]) / 2 - s) <= 0.03: ends.add(e)
    return len(ends) == 2


def closed_by_glass(fl, g, depth=0.6, share=0.9):
    """Glazing running along the gap close behind it - within 0.6 m of its wall faces, the narrowest a person can pass -
    over at least 90 % of its width: the gap opens onto a sliver against a glass wall (a recess beside a facade), not
    onto somewhere to go."""
    m = g.at(g.w / 2)
    for b in fl.bands:
        if math.dist(b.at((b.s0 + b.s1) / 2), m) > (g.w + b.length) / 2 + depth + g.t + 0.3 or ang_diff(b.u, g.u) > 5: continue
        ls = [g.frame(b.at(b.s0, l))[1] for l in (b.l0, b.l1)]
        d = (min(abs(x) for x in ls) if min(ls) * max(ls) > 0 else 0.0) - g.t / 2
        s = sorted(g.frame(b.at(x))[0] for x in (b.s0, b.s1))
        if d <= depth and min(s[1], g.w) - max(s[0], 0.0) >= share * g.w: return True
    return False


# Limits of the mouth test (interrupts_wall_line), each swept alone over the six floors (28 Oct). Inside the range given every
# scored key passage is kept and the detections are the same (the extras listed come in, or a key goes, at the other side of
# it). Each value sits in the middle of its range, or on the safe side of it where a missed doorway costs more than an extra
# passage, AND away from the common drawn sizes (0.20 / 0.25 m walls, 1.40 m openings): a limit that sits on a drawn size is
# decided by floating-point noise in the coordinates (a 0.20 m cross wall is kept or dropped depending on where the sheet
# is placed), so every comparison below also carries EPS. The ranges are measured with the shipped code (EPS included).
CROSS_PIECE = 0.225     # m: the wall faces may start this far past the far end (a jamb return, a reveal, a thin cross wall: 0.10,
                        #    0.15 and 0.20 m pieces count, 0.25 m and up is a wall). Range 0.11-0.24: UE-23 needs 0.08 (its
                        #    corner piece is 0.07-0.08 m thick), L29W-06's 0.26 m cross wall is covered by its drawn frame;
                        #    from 0.25 m a false 1.65 m passage enters on each tower floor (the value sits 1.5 cm below the
                        #    edge: a missed doorway costs more than an extra passage)
WALL_RUN = 0.6          # m: a face that runs on this far is a wall carrying on, not the end face of a corner or of a cross
                        #    wall: longer than the thickest wall in the six drawings (0.5 m), whose end face then no longer
                        #    passes for a run. Range 0.26-0.90: at 0.25 the corner of the false Sukhumvit upper-039 passes for a
                        #    run; GW-10 carries on 0.90 m (0.91 loses it); the other real run-ons are 0.68 m (O3) and 0.88 m (AUD-01)
DOORWAY = 1.45          # m: a gap between two flush corners is a doorway only this wide at most (a pair of leaves).
                        #    Range 1.31-1.55: UW-06 is 1.30 m wide, the false upper-039 is 1.55 m (1.56 lets it in) and the false
                        #    L29-029 1.59 m
FACE_TOL = 0.035        # m: two faces are in line within this (a little over the 3 cm that closes cracks, rule 1; wall types
                        #    differ by 6 cm, half of that is 3 cm). Range 0.03-0.045: the keys do not mind (0.005-0.1), a false
                        #    passage comes in at 0.05 (Sukhumvit upper) and five at 0.08
FACE_REACH = 0.10       # m: the centre line meets the far wall within this of the gap's end, else the end is no face. Range
                        #    0.02-0.33: a face 1.6 cm off (presidential suite-024) is one. From 0.35 m the ragged end of the
                        #    false suite-021 (0.34 m off) would count as a face too, and O1's (1.0 m off) is lost from 1.0 m
CENTRED_OUT = 0.35      # m: a far end that stands out no more than this past each face of the gap's wall, evenly (within
                        #    FACE_TOL), is a wall of another thickness, a pier or a column ON the line, not the side of a
                        #    wall across it (that stands out by metres). Only for a gap that starts at a free wall end (a
                        #    corner at the near end is not enough: the one real-data case, Sukhumvit ground-033, a 0.2 m
                        #    stair wall's corner facing a 0.4 m column box, is a false passage). No scored key uses the clause
                        #    and the six floors do not mind any value from 0 to 0.8 m; 0.35 m takes a 0.2 m wall against a
                        #    square column up to 0.9 m wide (tested on synthetic scenes only)


def wall_edges(G):
    """The boundary edges of the wall solid (every edge of 2 cm or more): [x0, y0, x1, y1] rows and their unit directions."""
    E = [(a, b) for part in G.parts for ring in [part.exterior] + list(part.interiors)
         for a, b in zip(ring.coords, list(ring.coords)[1:]) if math.dist(a, b) >= 0.02]
    A = np.array([[a[0], a[1], b[0], b[1]] for a, b in E], dtype=float).reshape(-1, 4)
    D = A[:, 2:] - A[:, :2]
    return A, D / np.maximum(np.hypot(D[:, 0], D[:, 1]), 1e-12)[:, None]


def far_face(fl, g):
    """The wall face the far end of an empty gap runs into -> (face, lo, hi). face: the centre line of the gap meets wall
    material within FACE_REACH of the gap's end (a diagonal or ragged end that the line passes by is no face). lo, hi: how
    far that material goes on past the two faces of the gap's wall, to the right (lo) and left (hi) of a->b: 0 = flush
    with the face, 3 = the wall is still there 3 m on, negative = the far wall is thinner; both large is the side of a
    wall running across the line (a T); both small and equal is a block centred on the line."""
    d1 = end_profile(fl.G, g.a, g.u, g.n, g.t, g.w + FACE_REACH + 0.05)[1][1]
    if d1 is None or d1 > g.w + FACE_REACH: return False, 0.0, 0.0
    own = [s for s in fl.G.section(g.at(d1 + 0.004), g.n, 3.0) if s[0] - 0.02 <= 0 <= s[1] + 0.02]
    if not own: return False, 0.0, 0.0
    return True, -own[0][0] - g.t / 2, own[0][1] - g.t / 2


def face_runs(fl, g):
    """Where the faces of the gap's wall go on along the line of the gap: the boundary edges of the wall solid that run
    along one of the two faces (FACE_TOL) -> {face: [(s0, s1), ...]}, merged, s from the start of the gap (face +1 / -1
    = the left / right face of a->b)."""
    A, U = fl.edges
    box = rect(g.a, g.u, -0.1, g.w + CROSS_PIECE + WALL_RUN + 0.1, -g.t / 2 - FACE_TOL - EPS, g.t / 2 + FACE_TOL + EPS).bounds
    sel = np.nonzero((np.maximum(A[:, 0], A[:, 2]) >= box[0]) & (np.minimum(A[:, 0], A[:, 2]) <= box[2]) &
                     (np.maximum(A[:, 1], A[:, 3]) >= box[1]) & (np.minimum(A[:, 1], A[:, 3]) <= box[3]) &
                     (np.abs(U[:, 0] * g.u[0] + U[:, 1] * g.u[1]) > math.cos(math.radians(2))))[0]
    runs = {1: [], -1: []}
    for k in sel:
        (sp, lp), (sq, lq) = g.frame(A[k, :2]), g.frame(A[k, 2:])
        for face in runs:
            if abs(lp - face * g.t / 2) <= FACE_TOL + EPS and abs(lq - face * g.t / 2) <= FACE_TOL + EPS:
                runs[face].append((min(sp, sq), max(sp, sq)))
    for face in runs:
        merged = []
        for s0, s1 in sorted(runs[face]):
            if merged and s0 <= merged[-1][1] + 0.02: merged[-1] = (merged[-1][0], max(merged[-1][1], s1))
            else: merged.append((s0, s1))
        runs[face] = merged
    return runs


def interrupts_wall_line(fl, g, framed_):
    """Is an empty gap an opening in a wall line, not the space between a wall end and another wall? An opening cuts
    the wall through, and the wall carries on past it. Not an opening: a face of the wall drawn unbroken across the gap
    (a recess or niche: a fitting stands in the wall); a gap that ends on the face of a wall that does not carry on,
    one wall end or corner facing the side of another wall (a mouth: a partition end across an aisle, a corridor seen
    in section). Open: the faces of the gap's wall go on in line past the far end (after a jamb piece of CROSS_PIECE at
    most) for WALL_RUN or more (that includes the free end of a wall of the same thickness, or of another thickness with
    one face in line); a drawn opening frame; an end with no face for the line to meet; a far end centred on the line
    (a wall of another thickness, a pier or a column, standing out CENTRED_OUT at most past each face) that goes on
    along it for WALL_RUN; and a door-sized gap (DOORWAY) whose far end is a corner face flush with a face of the
    gap's wall."""
    runs = face_runs(fl, g)
    if any(s0 <= FACE_TOL + EPS and s1 >= g.w - FACE_TOL - EPS for r in runs.values() for s0, s1 in r): return False
    if framed_ or g.how_end == 'collinear strip': return True
    face, lo, hi = far_face(fl, g)
    if not face: return True
    if any(s0 <= g.w + CROSS_PIECE + EPS and s1 - max(s0, g.w) >= WALL_RUN - EPS for r in runs.values() for s0, s1 in r): return True
    if g.near == 'cap' and abs(lo - hi) <= FACE_TOL + EPS and max(abs(lo), abs(hi)) <= CENTRED_OUT + EPS:      # a centred block on the line
        run = fl.G.cover(sub(g.b, mul(g.u, 0.005)), g.u, 1.0)
        if run and run[0][0] <= 0.01 and run[0][1] >= WALL_RUN - EPS: return True
    flush = (abs(lo) <= FACE_TOL + EPS and hi >= 0.15) or (abs(hi) <= FACE_TOL + EPS and lo >= 0.15)
    return flush and g.w <= DOORWAY + EPS


def attached_to_wall(fl, p, min_extent=0.8):
    """The wall piece touching p belongs to a connected wall of at least min_extent m (not a free-standing pier, fin or post)."""
    for q in fl.G.parts:
        if q.distance(Point(p)) < 0.03:
            x0, y0, x1, y1 = q.bounds
            if math.hypot(x1 - x0, y1 - y0) < min_extent - EPS: return False          # no side of it can reach that long
            mrr = q.minimum_rotated_rectangle
            if mrr.geom_type != 'Polygon': return max(x1 - x0, y1 - y0) >= min_extent - EPS
            xs = list(mrr.exterior.coords)
            return max(math.dist(xs[0], xs[1]), math.dist(xs[1], xs[2])) >= min_extent - EPS
    return False


def passage_ok(fl, g):
    """A gap with nothing drawn in it is a passage only when it looks like one: both ends are wall ends on one wall
    line (up to 3.6 m), or a short gap (up to 1.6 m) from a wall end to the side of a wall or pier that carries on;
    and there is building on both sides of it."""
    # Limits checked against the answer keys (round 3b sweep; the nearest key case in brackets): the 7 cm wall
    # minimum (presidential O5 / O6 stand in 8 cm walls), the 0.3 m stub-to-stub length (O1 passes up to 0.33 m), the
    # 3.6 m wall-end limit (Sukhumvit GW-10 is 3.30 m wide; 3.8 m adds three false passages) and the L-corner limit
    # (UE-23 is 2.50 m wide; 2.75 m keeps a margin above it and adds nothing on the five floors). A gap beside an
    # L-corner is more often the space between two separate walls than a doorway, hence the shorter limit.
    if g.near == 'T' or g.t < 0.07: return False
    # Stub to stub (pilasters, posts, kerbs): no wall line. A doorway set against cross walls also stands between two
    # short wall ends (reveals of 3-8 cm, nibs of 17 cm), so a stub-to-stub gap is kept when its frame is drawn, or
    # when both ends are free wall ends found on their own (a collinear strip of the same thickness at the far end:
    # "found from both ends" only sees the near end twice) that belong to a wall of 0.8 m or more (a row of free-standing
    # thin piers has no wall line either) and the gap is door-wide (1.6 m, the short-gap limit below; the plans fix it
    # only from 1.2 m up).
    fr = framed(fl, g)
    if max(g.nlen, g.flen) < 0.3 and not (fr or (g.near == 'cap' and g.how_end == 'collinear strip' and g.w <= 1.6 + EPS and
                                                 attached_to_wall(fl, g.at(-0.02)) and attached_to_wall(fl, g.at(g.w + 0.02)))):
        return False
    run = fl.G.cover(sub(g.b, mul(g.u, 0.005)), g.u, 0.5)
    far_run = run[0][1] if run and run[0][0] <= 0.01 else 0.0      # does the wall line carry on past the far end?
    if g.far == 'end':
        if not (0.6 - EPS <= g.w <= (3.6 if g.near == 'cap' else 2.75) + EPS): return False
        if g.near == 'L' and far_run < 0.2: return False
    elif g.far == 'face':
        if not (0.6 - EPS <= g.w <= 1.6 + EPS) or far_run < 0.3: return False
    else:
        return False
    for p in (g.at(-0.02), g.at(g.w + 0.02)):                       # a free-standing post is not a wall end
        if is_free_post(fl, p): return False
    if crosses_stair(fl, g): return False
    if not interrupts_wall_line(fl, g, fr): return False
    if closed_by_glass(fl, g): return False
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
    for o in openings:
        if o['kind'] != 'door' or o.get('src') != 'swing' or any('door' in h.p.roles for h in o['swings']): continue
        u = unit(sub(o['b'], o['a'])); w = math.dist(o['a'], o['b'])
        for q in openings:
            if q['kind'] != 'window' or ang_diff(u, unit(sub(q['b'], q['a']))) > 8: continue
            if abs(dot(sub(mul(add(q['a'], q['b']), 0.5), o['a']), perp(u))) > max(o['t'], q['t']) / 2 + 0.2: continue
            s = sorted((dot(sub(q['a'], o['a']), u), dot(sub(q['b'], o['a']), u)))
            if min(s[1], w) - max(s[0], 0.0) >= 0.8 * w:
                o['kind'], o['subtype'] = 'window', 'casement'
                o['ev'] = o['ev'] + ['glazing drawn across the opening (closed position): casement sash']
                break
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


def wall_direction(fl, p0, p1, u, max_off=10.0, min_len=0.2):
    """The direction of the wall faces (wall solid and glazing, jamb shapes) within 0.5 m of the chord p0-p1 that is
    nearest to u: -> a unit vector (same sense as u) when it is 0.3-max_off degrees off u and at least min_len of
    face runs that way; None when the chord already runs along a wall face or no face is near."""
    zone = LineString([p0, p1]).buffer(0.5)
    rows = []
    shapes = [fl.OB.parts[k] for k in fl.OB.tree.query(zone)] if fl.OB.tree else []
    shapes += [g for g, p in fl.jambs if g.intersects(zone)]
    for g in shapes:
        for ring in [g.exterior] + list(g.interiors):
            cs = list(ring.coords)
            for a, b in zip(cs, cs[1:]):
                if math.dist(a, b) < 0.03: continue
                seg = LineString([a, b]).intersection(zone)
                ln = sum(x.length for x in lines_of(seg))
                if ln < 0.02: continue
                rows.append((math.degrees(math.atan2(b[1] - a[1], b[0] - a[0])) % 180.0, ln))
    if not rows: return None
    au = math.degrees(math.atan2(u[1], u[0])) % 180.0
    best = None
    for ang, _ in rows:
        grp = [(a, l) for a, l in rows if min(abs(a - ang), 180 - abs(a - ang)) <= 1.0]
        tot = sum(l for _, l in grp)
        if tot < min_len: continue
        cx = sum(l * math.cos(math.radians(2 * a)) for a, l in grp); cy = sum(l * math.sin(math.radians(2 * a)) for a, l in grp)
        mean = math.degrees(math.atan2(cy, cx)) / 2 % 180.0
        off = min(abs(mean - au), 180 - abs(mean - au))
        if best is None or off < best[0]: best = (off, mean)
    if best is None or best[0] < 0.3 or best[0] > max_off: return None
    w = (math.cos(math.radians(best[1])), math.sin(math.radians(best[1])))
    return w if dot(w, u) > 0 else (-w[0], -w[1])


def single_wall_line_through(fl, c, u, L, lat=0.03):
    """A line on a wall / column layer running unbroken along the chord (c, along u, length L) past both ends."""
    SI = fl.SI
    e = add(c, mul(u, L))
    idx = SI.near_box(min(c[0], e[0]) - 0.2, min(c[1], e[1]) - 0.2, max(c[0], e[0]) + 0.2, max(c[1], e[1]) + 0.2)
    if not len(idx): return False
    s0, s1, la, lb, cs = SI.in_frame(idx, c, u)
    for k in np.nonzero((cs > math.cos(math.radians(3))) & (np.maximum(np.abs(la), np.abs(lb)) <= lat) &
                        (s0 < -0.05) & (s1 > L + 0.05))[0]:
        if fl.P[SI.pid[idx[k]]].roles & {'wall', 'column'}: return True
    return False


def symbol_door(fl, h, h2=None):
    """A door read from its swing(s) alone (no gap in the wall solid): the wall band beside the chord gives the
    centre line, wall ends, glazing or jambs within reach give the ends; otherwise the chord itself.
    h2: the second leaf of a double door (closed tips meeting)."""
    OB = fl.OB
    p0, p1 = (h.hinge, h.closed) if h2 is None else (h.hinge, h2.hinge)
    u = unit(sub(p1, p0))
    L = math.dist(p0, p1)
    # A swing drawn as a slightly flattened arc (or a spline) gives a chord a few degrees off its wall: the door runs
    # along the wall faces around it, so the chord is turned about its middle onto the nearest wall face direction.
    uw = wall_direction(fl, p0, p1, u)
    if uw is not None:
        m = mul(add(p0, p1), 0.5)
        u = uw
        p0, p1 = sub(m, mul(u, L / 2)), add(m, mul(u, L / 2))
    n = perp(u)
    side = 1 if dot(sub(h.open, p0), n) < 0 else -1               # the wall lies on side*n of the chord
    band = None
    for s in (-0.08, L + 0.08, L / 2):                             # just outside each end; in the middle (drawn through)
        q = add(p0, mul(u, s))
        sec = OB.section(q, n, 0.6)
        # a band that reaches the edge of the section window is a wall only if nothing goes on beyond it: a thicker wall or a core
        # block is cut short by the window, and its 'band' would be the window, not the wall (the tower's shaft doors stand on the
        # face of such a block: they are read on their chord, whatever 0.1 mm the face lies from it)
        sec = [(a, b) for a, b in sec if not (a <= -0.6 + 1e-4 and OB.contains(add(q, mul(n, -0.63)))) and
               not (b >= 0.6 - 1e-4 and OB.contains(add(q, mul(n, 0.63))))]
        sec = [(a, b) for a, b in sec if b - a <= 0.6 + EPS and (a * side >= -0.03 - EPS or b * side >= -0.03 - EPS) and min(abs(a), abs(b)) <= 0.08 + EPS]
        if sec:
            band = min(sec, key=lambda ab: min(abs(ab[0]), abs(ab[1])))
            break
    if band:
        mlat, t = (band[0] + band[1]) / 2, band[1] - band[0]
    else:
        mlat, t = 0.0, 0.1
    c = add(p0, mul(n, mlat))
    # The ray that looks for wall material along the chord runs 1 mm into the wall side when no band was found: a chord drawn
    # exactly on a wall face (the usual way a door symbol is drawn) would graze the face and see the wall in pieces, by rounding.
    ray = c if band else add(c, mul(n, side * 0.001))
    iv = OB.cover(add(ray, mul(u, -0.6)), u, L + 1.2)
    iv = [(x - 0.6, y - 0.6) for x, y in iv]
    inside = any(x <= L / 2 <= y for x, y in iv)
    s0, s1, how = 0.0, L, []
    end0 = end1 = False
    if not inside:
        left = [y for x, y in iv if y <= L / 2]
        right = [x for x, y in iv if x >= L / 2]
        if left and -0.35 - EPS <= max(left) <= 0.1 + EPS: s0 = max(left); how.append('wall end'); end0 = True
        if right and L - 0.1 - EPS <= min(right) <= L + 0.35 + EPS: s1 = min(right); how.append('wall end'); end1 = True
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
        # a single line on a wall layer drawn unbroken through the whole chord: the leaf closes against a one-line
        # screen or partition (a shower door), it is not an opening in a wall (an opening breaks its wall's lines)
        if single_wall_line_through(fl, c, u, L): return None
    a, b = add(c, mul(u, s0)), add(c, mul(u, s1))
    sub_ = 'hinged single' if h2 is None else 'hinged double'
    ev = [('swing arc + leaf on ' if h.leaf else 'swing arc on ') + h.p.lay] + (['second leaf, closed tips meet'] if h2 else [])
    ev += ['ends: ' + ', '.join(how)] if how else ['ends from the swing']
    if h0 and h1 and not band: ev.append('line work along the opening on ' + 'another layer')
    # host: read from the ends (finish / host_of) when a wall band or a wall end / jamb bounds the door
    return dict(kind='door', subtype=sub_, a=a, b=b, t=t, host='wall' if (band or how) else ('line work' if (h0 and h1) else 'none'),
                ev=ev, conf=0.5 + 0.15 * len(how), swings=[h] if h2 is None else [h, h2], src='swing')


# ================================================================================================ 7. output
def host_of(fl, a, b):
    """What the opening is cut in: 'wall' when wall material bounds an end, 'glass' when only glazing does (a door
    in a glazed screen or curtain wall), 'none' when nothing drawn bounds it (a wall that is not drawn)."""
    u = unit(sub(b, a))
    ends = [sub(a, mul(u, 0.03)), add(b, mul(u, 0.03))]
    if any(fl.G.dist(p) <= 0.03 for p in ends): return 'wall'
    if any(fl.OB.dist(p) <= 0.03 for p in ends): return 'glass'
    return 'none'


def glazing_extent(fl, a, b, t):
    """Where the glazing lines of an opening lie across its line a->b: [lo, hi] in metres on the left normal (the
    bands parallel to it within its wall depth + 0.15 m that cover at least 40 % of it), or None."""
    u = unit(sub(b, a)); n = perp(u); w = math.dist(a, b)
    lo = hi = None
    for bd in fl.bands:
        if ang_diff(bd.u, u) > 5: continue
        ls = [dot(sub(bd.at(bd.s0, l), a), n) for l in (bd.l0, bd.l1)]
        if min(ls) > t / 2 + 0.15 or max(ls) < -t / 2 - 0.15: continue
        ss = sorted(dot(sub(bd.at(x), a), u) for x in (bd.s0, bd.s1))
        if min(ss[1], w) - max(ss[0], 0.0) < 0.4 * w: continue
        lo = min(ls) if lo is None else min(lo, min(ls)); hi = max(ls) if hi is None else max(hi, max(ls))
    return None if lo is None else [round(float(lo), 3), round(float(hi), 3)]


def finish(fl, ops, floor_name):
    """Openings -> output records. hinge: the end the leaf is hinged at; swing: the side of a->b the leaf opens to
    ('left' / 'right'), for single hinged leaves (and casement sashes)."""
    out = []
    for k, o in enumerate(ops, 1):
        a, b = o['a'], o['b']
        hinge, swing = None, None
        if len(o['swings']) == 1:
            h = o['swings'][0]
            hinge = 'a' if math.dist(h.hinge, a) < math.dist(h.hinge, b) else 'b'
            side = cross(sub(b, a), sub(h.open, h.hinge))
            swing = 'left' if side > 0 else 'right'
        elif len(o['swings']) == 2 and o['kind'] == 'door':
            side = cross(sub(b, a), sub(o['swings'][0].open, o['swings'][0].hinge))
            swing = 'left' if side > 0 else 'right'
        host = o['host'] if o['host'] == 'none' else host_of(fl, a, b)
        if host == 'none' and o.get('sidelit'): host = 'glass'       # the sidelights bound it
        out.append({'id': f"{floor_name.split(':')[-1]}-{k:03d}", 'floor': floor_name, 'kind': o['kind'],
                    'subtype': o['subtype'], 'a': [round(float(a[0]), 4), round(float(a[1]), 4)],
                    'b': [round(float(b[0]), 4), round(float(b[1]), 4)],
                    'width': round(math.dist(a, b), 3), 'wallThickness': round(float(o['t']), 3), 'host': host,
                    'hinge': hinge, 'swing': swing, 'confidence': round(o['conf'], 2), 'evidence': o['ev'],
                    'eitherKind': bool(o.get('either')),
                    'glazing': glazing_extent(fl, a, b, o['t']) if (o['kind'] == 'window' or o.get('src') == 'glazing') else None})
        if o.get('sidelights'): out[-1]['sidelights'] = o['sidelights']     # fixed glass cut off beside the leaf (rule 4)
    return out


def area_tagger(areas):
    """The mapping's 'areas': {area: {"bbox": [x0, y0, x1, y1] (drawing metres), "pad": m, "match": "all" | "any"}
    or {"wholeFile": true}} -> function(item) -> the first area whose box holds all (or any) of the item's points
    (padded), or None. Items with no points belong to no area."""
    for name, spec in areas.items():
        if not spec.get('wholeFile') and len(spec.get('bbox', [])) != 4:
            raise SystemExit(f'area {name!r}: give "bbox": [x0, y0, x1, y1] (drawing metres) or "wholeFile": true')
        if spec.get('match', 'all') not in ('all', 'any'): raise SystemExit(f'area {name!r}: "match" is "all" or "any"')

    def tag(d):
        P = d.get('pts') or [q for l in d.get('loops', []) for q in l] or ([d['ins']] if 'ins' in d else [])
        if not P: return None
        for name, spec in areas.items():
            if spec.get('wholeFile'): return name
            x0, y0, x1, y1 = spec['bbox']; pad = spec.get('pad', 0.0)
            inside = (x0 - pad <= x <= x1 + pad and y0 - pad <= y <= y1 + pad for x, y in P)
            if (all if spec.get('match', 'all') == 'all' else any)(inside): return name
        return None
    return tag


def run(mapping_path, out_path, png_dir=None):
    mp = json.loads(Path(mapping_path).read_text(encoding='utf-8'))
    t0 = time.time()
    D = prims.load(mp['cache'])
    units = mp.get('units', 'mm')
    if units not in UNITS: raise SystemExit(f'unknown units {units!r} in {mapping_path} (allowed: {", ".join(UNITS)})')
    scale = UNITS[units]
    roles = role_matcher(mp['layers'])
    result, floors = [], {}
    # Which drawing items belong to which floor: the mapping's 'areas' (data: where each plan sits on the sheet), else
    # the area tags the drawing cache was built with (tools/prims.py).
    tag = area_tagger(mp['areas']) if mp.get('areas') else (lambda d: d.get('area'))
    for area, floor_name in mp['floors'].items():
        items = [d for d in D['items'] if tag(d) == area]
        if scale != 1.0: items = [scaled(d, scale) for d in items]      # dedupe works in metres (its 3 decimals are 1 mm for every unit)
        items = dedupe(items)
        fl = Floor(floor_name, items, D['layers'], roles, 1.0)
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
