"""Cut the detected doors and windows into the merged house model; build their lintels, sills and panes
(26 Oct 2026; rules revised 27 Oct 2026 after the round-3 review).

merge_cad.py calls cut_floor() once per floor, AFTER the floor plates are computed (so the plates, including the
upper balcony's floor, stay exactly as they were). The openings come from openings.json (find_openings.py, drawing
metres) and are used as they are: nothing is added, removed or moved here.

What each kind becomes (decided 26 Oct 2026):
  door     open from the floor to its head; a lintel from the head to the top of the wall; no leaf is drawn (so
           there is never a leaf to bump into); walls, glass and single-line pieces are cut away in its footprint
  window   a 3 cm glass pane from the sill to the head (a collider: you cannot walk through it); a sill wall only
           when the sill is above 0; a lintel from the head to the top unless the head reaches the top; walls,
           glass and single-line pieces are cut away in its footprint. Sliding glazing that may be a door or a
           window (eitherKind) is glazed like a window whatever kind the detector gave it: the sliding glass doors
           onto the terraces get a pane too (one rule for all of them)
  passage  left as it is (no cut, no lintel): a passage is a gap that is already open, so a false one is harmless.
           cut_floor() checks this: the walls, glass and single lines inside every passage are the same after the cut

Footprint of an opening: its line a-b (the detector's ends, on the wall centre line) across the depth of the wall.
  wall depth (lintels and sills): the walls beside the two jambs, read in sections across the line 0.05, 0.10,
           0.20 and 0.30 m beyond each (one wall interval meeting the opening, at most 0.6 m deep; another opening's
           footprint does not count). A jamb wall is steady when the sections from 0.10 m on agree and the nearest
           lies inside them (a wall that runs on past a jamb nib); a jamb return, a block or a cross wall is not. Steady walls
           at both jambs: the deeper one when the other lies inside it (a thin wall meeting a thick one), else the
           faces they share; a steady wall at one jamb: that one; none steady: the faces the nearest good sections
           share; no wall at either jamb: the detector's wall thickness. The glazing and walls drawn straight
           through the opening are always inside it. So a lintel neither sticks out past the wall beside it nor
           leaves a slot in a wall that is deeper than the detector's strip.
  cut:     the wall depth, the detector's wall thickness and, for a glazed opening, its glazing band (the
           detector's 'glazing' field). Other glass is not cut, so a grille or screen standing outside the wall
           faces stays (A_Grill / W_Grill are 'screen' layers, not glazing). An opening without glazing information
           (doors) also takes glass and single lines within 0.1 m of the wall faces (a room outline across a
           doorway). Only material within 0.45 m of the line counts.
  pane:    in the middle of the glazing band (the detector's 'glazing'), kept inside the wall depth; on the line
           when there is no band.
Lintels and sills are as deep as the wall and span from jamb to jamb, filling a slot of up to 0.15 m where the wall
stops short of the opening's end. A lintel needs something to sit on at both ends: a wall or glass (a single line
is only 1 m high) or the next door or window within 0.15 m; otherwise the opening gets none.
Post-less glass corners: two glazed openings at right angles whose ends meet (within 0.15 m) close the corner: both
panes run on to where the two panes cross (plus half a pane), the cut and the first one's lintel and sill run on
over the corner square, the second's up to the first's. find_openings.py gives both legs the same heights.

Leaves drawn as solids are removed after the cut ("fins"): door leaves and casement sashes drawn open on the window
layer were paired into thin glass strips standing in front of their opening, up to the full glass height, and a
swing drawn on a wall layer leaves single-line pieces. Removed are (a) thin glass pieces (at most 8 cm) that stand
across a door's or window's line (within 20 degrees), within its width, starting at the wall face and reaching out
no further than the opening is wide, and (b) glass and single-line pieces lying mostly (60 %) in the floor a hinged
leaf sweeps (the detector's hinge and swing side; a double door has two half-width leaves).

The pieces are written to house3d_merged.json under new keys (the solids keys stay wall / glass / single):
  pieces:   {floor: [{kind: 'lintel'|'sill'|'pane', id, o, h, z0, z1, top?}]}   z above the floor level (m);
            a lintel's z1 is the wall height ('to the top'): the viewer stretches it with the wall-height setting;
            top: true on a pane that reaches the top of the wall (it follows the wall top as well)
  openings: {floor: [{id, kind, subtype, glazed, a, b, x, y, nx, ny, width, sill, head, hinge, swing, eitherKind,
            floorSide, leaves, depth, cut, pane, lintel, jambGap, corner}]} in centred model metres; (nx, ny) is the
            unit normal on the left of a->b; glazed = it gets a pane (windows and eitherKind); floorSide = [floor
            plate 0.9 m out on the -n side, on the +n side]; leaves = [{hinge, closed, open, r}] (directions of the
            closed and the open leaf, its width); depth / cut = the wall's and the cut's extent across the line;
            pane = the pane's offset across the line (glazed only); corner = the opening it meets at a glass corner
            (passages: no depth, no cut)
  removed:  {floor: [{id, kind: 'glass'|'single', o, h, why}]} the fins taken out (for checking)
"""
import math
from shapely.geometry import Polygon, LineString, Point
from shapely.ops import unary_union

REACH = 0.45          # material further than this from an opening's line is not its wall (m)
GLASS_NEAR = 0.10     # openings without glazing information: glass / single lines this near the wall are cut too (m)
GLAZING_PAD = 0.02    # the cut runs this far past the glazing band (m)
MARGIN = 0.01         # the cut goes this far past the faces (m)
PANE = 0.03           # window pane thickness (m)
FIN_MAX = 0.08        # a fin is at most this thick (m)
SLIVER = 0.012        # cut pieces thinner than this on average are dropped (m)
SECTIONS = 8          # cross sections inside an opening
END_PROBES = (0.05, 0.10, 0.20, 0.30)   # sections beyond each jamb for the wall's depth (m)
CORNER_GAP = 0.15     # ends of two glazed openings at right angles this close: a post-less glass corner (m)


def polys(g):
    if g is None or g.is_empty: return []
    if g.geom_type == 'Polygon': return [g]
    if hasattr(g, 'geoms'): return [p for x in g.geoms for p in polys(x)]
    return []


def lines(g):
    if g is None or g.is_empty: return []
    if g.geom_type == 'LineString': return [g]
    if hasattr(g, 'geoms'): return [p for x in g.geoms for p in lines(x)]
    return []


class Frame:
    """An opening's line: a + s*u along (0..L), c*n across (n = left normal of a->b)."""
    def __init__(self, a, b):
        self.a, self.b = a, b
        self.L = math.dist(a, b)
        self.u = ((b[0] - a[0]) / self.L, (b[1] - a[1]) / self.L)
        self.n = (-self.u[1], self.u[0])

    def at(self, s, c=0.0):
        return (self.a[0] + self.u[0] * s + self.n[0] * c, self.a[1] + self.u[1] * s + self.n[1] * c)

    def local(self, x, y):
        dx, dy = x - self.a[0], y - self.a[1]
        return dx * self.u[0] + dy * self.u[1], dx * self.n[0] + dy * self.n[1]

    def rect(self, s0, s1, c0, c1):
        return Polygon([self.at(s0, c0), self.at(s1, c0), self.at(s1, c1), self.at(s0, c1)])

    def across(self, geom, s, half=0.6):
        """Intervals (lo, hi) of geom on the line across the opening at s, relative to the opening's line (pieces
        that touch are joined)."""
        out = []
        for g in lines(LineString([self.at(s, -half), self.at(s, half)]).intersection(geom)):
            cs = sorted(self.local(x, y)[1] for x, y in g.coords)
            if cs[-1] - cs[0] > 1e-4: out.append((cs[0], cs[-1]))
        out.sort()
        merged = []
        for lo, hi in out:
            if merged and lo <= merged[-1][1] + 1e-3: merged[-1] = (merged[-1][0], max(merged[-1][1], hi))
            else: merged.append((lo, hi))
        return merged


def to_model(p, shift, centre):
    return (p[0] + shift - centre[0], p[1] - centre[1])


def wall_at_end(F, t, Wj, end):
    """The wall beside one jamb: sections across the line END_PROBES beyond it; in each, the one interval of wall
    that meets the opening's band (the detector's thickness + 5 cm), no deeper than 0.6 m and within REACH (else the
    section is no good: a cross wall, a column row, nothing). -> ((lo, hi), steady) or None. Steady: the sections
    from 0.10 m on agree and the nearest one lies inside them (a wall that runs on, past a jamb nib or reveal; not a
    jamb return, a cross wall or a block): (lo, hi) is then that wall; otherwise the nearest good section."""
    sgn, s0 = (-1, 0.0) if end == 'a' else (1, F.L)
    got = []
    for d in END_PROBES:
        ivs = [iv for iv in F.across(Wj, s0 + sgn * d) if iv[1] >= -t / 2 - 0.05 and iv[0] <= t / 2 + 0.05]
        ok = len(ivs) == 1 and ivs[0][1] - ivs[0][0] <= 0.6 and ivs[0][0] > -REACH and ivs[0][1] < REACH
        got.append(ivs[0] if ok else None)
    good = [g for g in got if g]
    if not good: return None
    # steady: the sections from 0.10 m on agree, and the nearest one (0.05 m) is good and inside them (a jamb nib or a
    # reveal at most); its depth is then the wall's past the nib
    far = [g for g in got[1:] if g]
    agree = len(far) >= 2 and all(abs(g[0] - far[0][0]) <= 0.01 and abs(g[1] - far[0][1]) <= 0.01 for g in far)
    if agree and got[0] is not None and got[0][0] >= far[0][0] - 0.01 and got[0][1] <= far[0][1] + 0.01:
        return far[0], True
    return good[0], False


def depth(F, t, W, ALL, W_ends, glazing=None):
    """-> (wall lo, hi), (cut lo, hi): the opening's depth across its line (relative to it).
    The wall depth (lintels, sills) comes from the walls beside the two jambs (W_ends: walls with the other openings'
    footprints taken out): a steady wall at both jambs -> the deeper one when the other lies inside it (a thin wall
    meeting a thick one), else the faces they share; a steady wall at one jamb -> that one (the other end is a
    jamb return, a block, a cross wall or nothing); none steady -> the faces the nearest sections share. With no
    wall at either jamb, the detector's thickness. The glazing and walls drawn straight through the opening are
    always inside it. The cut adds the detector's thickness, and glass / single lines near the wall when the
    opening has no glazing information."""
    E = [wall_at_end(F, t, W_ends, e) for e in ('a', 'b')]
    st = [e[0] for e in E if e and e[1]]
    near = [e[0] for e in E if e]
    inside = lambda p, q: p[0] >= q[0] - 0.01 and p[1] <= q[1] + 0.01        # p within q
    if len(st) == 2:
        p, q = st
        if inside(p, q) or inside(q, p): lo, hi = max((p, q), key=lambda x: x[1] - x[0])
        else: lo, hi = max(p[0], q[0]), min(p[1], q[1])
    elif len(st) == 1:
        lo, hi = st[0]
    elif len(near) == 2:
        lo, hi = max(near[0][0], near[1][0]), min(near[0][1], near[1][1])
    elif near:
        lo, hi = near[0]
    else:
        lo, hi = -t / 2, t / 2
    if hi - lo < 0.04: lo, hi = min(x[0] for x in near), max(x[1] for x in near)   # no common faces: cover both
    if glazing: lo, hi = min(lo, glazing[0]), max(hi, glazing[1])     # the glazing always lies within the wall
    for k in range(1, SECTIONS):                                    # walls drawn straight through the opening
        for iv in F.across(W, F.L * k / SECTIONS):
            if iv[1] >= lo - 0.05 and iv[0] <= hi + 0.05 and iv[0] > -REACH and iv[1] < REACH: lo, hi = min(lo, iv[0]), max(hi, iv[1])
    wall = (lo, hi)
    lo, hi = min(lo, -t / 2), max(hi, t / 2)
    if glazing: lo, hi = min(lo, glazing[0] - GLAZING_PAD), max(hi, glazing[1] + GLAZING_PAD)
    else:                                                           # no glazing given: glass and single lines near it
        w0, w1 = lo, hi
        for k in range(1, SECTIONS):
            for iv in F.across(ALL, F.L * k / SECTIONS):
                if iv[1] >= w0 - GLASS_NEAR and iv[0] <= w1 + GLASS_NEAR and iv[0] > -REACH and iv[1] < REACH: lo, hi = min(lo, iv[0]), max(hi, iv[1])
    return wall, (lo, hi)


def end_gap(F, end, wall, WG, ends, ext=0.0):
    """How far the wall (or the next opening) is beyond one end of the opening: 0 when it starts right there,
    up to 0.15 m (a slot the lintel fills), None when no wall or glass is there (a single line is only 1 m
    high and carries nothing): with no jamb the lintel would hang free. ext: the end already runs on this far
    (a glass corner), measured from there."""
    sgn = -1 if end == 'a' else 1
    s0 = (0.0 - ext) if end == 'a' else F.L + ext
    probe = F.rect(min(s0, s0 + sgn * 0.15), max(s0, s0 + sgn * 0.15), wall[0] + 0.01, wall[1] - 0.01)
    hit = probe.intersection(WG)
    gaps = []
    if not hit.is_empty and hit.area > 2e-4:
        gaps.append(min(abs(F.local(x, y)[0] - s0) for g in polys(hit) for x, y in g.exterior.coords))
    p = F.at(0.0 if end == 'a' else F.L)
    for q in ends:                                      # another door or window starts here (a mullion not drawn)
        if math.dist(p, q) <= 0.15: gaps.append(0.0)
    return min(gaps) if gaps else None


def is_fin(P, F, cut):
    """A thin glass piece standing across the opening's line, in front of it: an open leaf or sash."""
    if P.area > 0.3: return False
    r = P.minimum_rotated_rectangle
    cs = list(r.exterior.coords)[:4]
    e = [(cs[1][0] - cs[0][0], cs[1][1] - cs[0][1]), (cs[2][0] - cs[1][0], cs[2][1] - cs[1][1])]
    ln = [math.hypot(*v) for v in e]
    k = 0 if ln[0] >= ln[1] else 1
    if ln[1 - k] > FIN_MAX or ln[k] < 0.25 or ln[k] > F.L + 0.15: return False
    d = (e[k][0] / ln[k], e[k][1] / ln[k])
    if abs(d[0] * F.n[0] + d[1] * F.n[1]) < math.cos(math.radians(20)): return False
    loc = [F.local(x, y) for x, y in P.exterior.coords]
    s0, s1 = min(p[0] for p in loc), max(p[0] for p in loc)
    c0, c1 = min(p[1] for p in loc), max(p[1] for p in loc)
    if s0 < -0.1 or s1 > F.L + 0.1: return False
    out_pos = c0 >= cut[1] - 0.12 and c0 <= cut[1] + 0.12 and c1 <= cut[1] + F.L + 0.1
    out_neg = c1 <= cut[0] + 0.12 and c1 >= cut[0] - 0.12 and c0 >= cut[0] - F.L - 0.1
    return out_pos or out_neg


def leaves(o, F):
    """The hinged leaves the detector found: [(hinge point, closed direction, open direction, width)]. A single
    leaf (or casement sash) is hinged at a or b; a double door (no hinge given) has two half-width leaves, one at
    each end. The open direction is the side the leaf swings to. [] when no swing side is known (sliding doors)."""
    if o['swing'] not in ('left', 'right'): return []
    k = 1 if o['swing'] == 'left' else -1
    nrm = (F.n[0] * k, F.n[1] * k)
    back = (-F.u[0], -F.u[1])
    if o['hinge'] == 'a': return [(F.a, F.u, nrm, F.L)]
    if o['hinge'] == 'b': return [(F.b, back, nrm, F.L)]
    if o['kind'] == 'door': return [(F.a, F.u, nrm, F.L / 2), (F.b, back, nrm, F.L / 2)]
    return []


def swing_area(lv):
    """The floor the leaves sweep: a quarter disc at each hinge, as wide as its leaf."""
    out = []
    for h, d, m, r in lv:
        arc = [(h[0] + r * (d[0] * math.cos(t) + m[0] * math.sin(t)), h[1] + r * (d[1] * math.cos(t) + m[1] * math.sin(t)))
               for t in (math.pi / 2 * i / 16 for i in range(17))]
        out.append(Polygon([h] + arc))
    return unary_union(out) if out else None


def ring(p, nd=3):
    R = lambda v: round(v, nd)
    o = [[R(x), R(y)] for x, y in list(p.exterior.coords)[:-1]]
    h = [[[R(x), R(y)] for x, y in list(i.coords)[:-1]] for i in p.interiors]
    return {'o': o, 'h': h}


def is_glazed(o):
    """Glazed in 3D: windows, and sliding glazing that may be a door or a window (eitherKind) whatever its kind."""
    return o['kind'] == 'window' or bool(o.get('eitherKind'))


def glass_corners(ops):
    """Post-less glass corners: pairs of glazed openings at right angles (within 10 degrees) with an end of each
    within CORNER_GAP of an end of the other. -> {id: (end 'a'|'b', other id, crossing point of the two lines,
    first: True for the opening that covers the corner square)}."""
    G = [o for o in ops if o['kind'] != 'passage' and is_glazed(o)]
    out = {}
    for i, p in enumerate(G):
        for q in G[i + 1:]:
            Fp, Fq = Frame(p['a'], p['b']), Frame(q['a'], q['b'])
            if abs(Fp.u[0] * Fq.u[0] + Fp.u[1] * Fq.u[1]) > math.sin(math.radians(10)): continue
            best = None
            for ep, P in (('a', p['a']), ('b', p['b'])):
                for eq, Q in (('a', q['a']), ('b', q['b'])):
                    d = math.dist(P, Q)
                    if d <= CORNER_GAP and (best is None or d < best[0]): best = (d, ep, eq)
            if best is None or p['id'] in out or q['id'] in out: continue
            den = Fp.u[0] * Fq.n[0] + Fp.u[1] * Fq.n[1]                  # where p's line crosses q's line
            s = ((Fq.a[0] - Fp.a[0]) * Fq.n[0] + (Fq.a[1] - Fp.a[1]) * Fq.n[1]) / den
            X = Fp.at(s)
            out[p['id']] = (best[1], q['id'], X, True)
            out[q['id']] = (best[2], p['id'], X, False)
    return out


def cut_floor(floor, ops, walls, glass, singles, plates, height, log=print):
    """ops: this floor's openings (openings.json records, already in model metres: a, b).
    walls / glass / singles: the merged polygons; plates: the floor plate polygons (for floorSide); height: the
    wall height (top - level). -> (walls, glass, singles, pieces, records, removed)."""
    W, G, S = unary_union(walls), unary_union(glass), unary_union(singles)
    ALL, WG = unary_union([W, G, S]), unary_union([W, G])
    plate = unary_union(plates)
    cuts, recs, pieces = [], [], []
    ends = {o['id']: [tuple(o['a']), tuple(o['b'])] for o in ops if o['kind'] != 'passage'}
    # the other openings' footprints are not the wall at a jamb (a fixed pane beside a slider, a mullion not drawn)
    foot = {o['id']: Frame(o['a'], o['b']).rect(0.0, math.dist(o['a'], o['b']), -o['wallThickness'] / 2 - 0.1, o['wallThickness'] / 2 + 0.1)
            for o in ops if o['kind'] != 'passage' and math.dist(o['a'], o['b']) > 1e-6}
    corners = glass_corners(ops)
    # first pass: each opening's wall depth and cut (the glass corners need their partner's)
    D = {}
    for o in ops:
        if o['kind'] == 'passage': continue
        F = Frame(o['a'], o['b'])
        box = F.rect(-0.45, F.L + 0.45, -0.7, 0.7)                     # the jamb sections only look this far
        oth = unary_union([g for k, g in foot.items() if k != o['id'] and g.intersects(box)])
        loc = W.intersection(box)
        glz = o.get('glazing') if is_glazed(o) else None
        wall, cut = depth(F, o['wallThickness'], W, ALL, loc.difference(oth) if not oth.is_empty else loc, glz)
        pane_c = min(max((glz[0] + glz[1]) / 2, wall[0] + PANE / 2), wall[1] - PANE / 2) if glz else 0.0
        D[o['id']] = (wall, cut, pane_c)
    for o in ops:
        F = Frame(o['a'], o['b'])
        nx, ny = F.n
        mid = F.at(F.L / 2)
        side = [plate.contains(Point(F.at(F.L / 2, c))) for c in (-0.9, 0.9)]
        lv = leaves(o, F) if o['kind'] != 'passage' else []
        glazed = o['kind'] != 'passage' and is_glazed(o)
        R3 = lambda v: [round(v[0], 3), round(v[1], 3)]
        rec = {'id': o['id'], 'kind': o['kind'], 'subtype': o['subtype'], 'glazed': glazed,
               'a': R3(o['a']), 'b': R3(o['b']),
               'x': round(mid[0], 3), 'y': round(mid[1], 3), 'nx': round(nx, 4), 'ny': round(ny, 4),
               'width': round(F.L, 3), 'sill': o['sill'], 'head': o['head'], 'hinge': o['hinge'], 'swing': o['swing'],
               'eitherKind': o['eitherKind'], 'floorSide': side,
               'leaves': [{'hinge': R3(h), 'closed': R3(d), 'open': R3(m), 'r': round(r, 3)} for h, d, m, r in lv]}
        if o['kind'] == 'passage':
            rec.update(depth=None, lintel=False)
            recs.append(rec); continue
        wall, cut, pane_c = D[o['id']]
        # a post-less glass corner: run on over the corner (see the docstring)
        ext = {'a': 0.0, 'b': 0.0}; pane_ext = {'a': 0.0, 'b': 0.0}
        if o['id'] in corners:
            end, other, X, is_first = corners[o['id']]
            sX = F.local(*X)[0]
            reach = -sX if end == 'a' else sX - F.L                     # from the end on to the crossing point
            q = next(x for x in ops if x['id'] == other)
            Fq = Frame(q['a'], q['b'])
            q_wall, q_cut, q_pane = D[other]
            run = F.u if end == 'b' else (-F.u[0], -F.u[1])
            k = 1 if (run[0] * Fq.n[0] + run[1] * Fq.n[1]) > 0 else -1  # running on crosses the other from its -n side (+1)
            at = lambda c: reach + k * c                                 # distance from this end to the other's line + c
            pane_ext[end] = max(0.0, at(q_pane) + PANE / 2)
            ext[end] = max(0.0, at(q_wall[1] if k > 0 else q_wall[0]) if is_first else at(q_wall[0] if k > 0 else q_wall[1]))
            rec['corner'] = other
        s_lo, s_hi = -ext['a'], F.L + ext['b']
        rect = F.rect(s_lo, s_hi, cut[0] - MARGIN, cut[1] + MARGIN)
        cuts.append((o, F, rect, cut, swing_area(lv)))
        rec['depth'] = [round(wall[0], 3), round(wall[1], 3)]
        rec['cut'] = [round(cut[0], 3), round(cut[1], 3)]
        oth_ends = [q for k, v in ends.items() if k != o['id'] for q in v]
        ga = end_gap(F, "a", wall, WG, oth_ends, ext['a'])
        gb = end_gap(F, "b", wall, WG, oth_ends, ext['b'])
        if o['id'] in corners:                                       # the corner end rests on the other opening
            e = corners[o['id']][0]
            if e == 'a': ga = 0.0 if ga is None else ga
            else: gb = 0.0 if gb is None else gb
        # Lintels and sills span from jamb to jamb: into a slot of up to 0.15 m where the wall stops short of the end.
        body = F.rect(s_lo - (ga or 0.0), s_hi + (gb or 0.0), wall[0], wall[1])
        head = min(o['head'], height)
        has_lintel = ga is not None and gb is not None and head < height - 0.005
        rec['lintel'] = has_lintel
        rec['jambGap'] = [None if g is None else round(g, 3) for g in (ga, gb)]
        if glazed:
            sill = min(max(o['sill'], 0.0), head)
            pp = {'kind': 'pane', 'id': o['id'], 'poly': F.rect(-pane_ext['a'], F.L + pane_ext['b'], pane_c - PANE / 2, pane_c + PANE / 2),
                  'z0': sill, 'z1': head}
            if head >= height - 0.005: pp['top'] = True                  # reaches the top: follows the wall top
            pieces.append(pp)
            rec['pane'] = round(pane_c, 3)
            if sill > 0.005:
                pieces.append({'kind': 'sill', 'id': o['id'], 'poly': body, 'z0': 0.0, 'z1': sill})
        if has_lintel:
            pieces.append({'kind': 'lintel', 'id': o['id'], 'poly': body, 'z0': head, 'z1': height})
        elif head < height - 0.005:
            where = 'either jamb' if ga is None and gb is None else 'one jamb'
            log(f'   {o["id"]} ({o["kind"]}): nothing at {where} for a lintel to sit on, so none')
        recs.append(rec)

    allcut = unary_union([c[2] for c in cuts]) if cuts else Polygon()

    def cut_all(items, min_area):
        out, n_cut = [], 0
        for p in items:
            if p.intersection(allcut).area < 1e-6:
                out.append(p); continue
            n_cut += 1
            for q in polys(p.difference(allcut)):
                if q.area >= min_area and 2 * q.area / q.length >= SLIVER: out.append(q)
        return out, n_cut

    walls2, nw = cut_all(walls, 0.003)
    glass2, ng = cut_all(glass, 0.005)
    singles2, ns = cut_all(singles, 0.003)
    # Leaves and swings drawn on a glass or wall layer: thin glass fins standing in front of an opening, and glass or
    # single-line pieces lying (mostly) in a hinged leaf's swing. Nothing solid can stand where a door swings.
    removed = []
    def swept(p):
        for o, F, rect, cut, area in cuts:
            if area is not None and p.intersection(area.buffer(0.05)).area >= 0.6 * p.area: return o['id']
        return None
    keep = []
    for p in glass2:
        hit = next((o['id'] for o, F, rect, cut, area in cuts if is_fin(p, F, cut)), None)
        why = 'a leaf or sash drawn open on the window layer (a glass fin)'
        if not hit:
            hit, why = swept(p), 'glass in a door\'s swing (part of the door symbol)'
        if hit: removed.append({'id': hit, 'poly': p, 'why': why, 'kind': 'glass'})
        else: keep.append(p)
    glass2, keep = keep, []
    for p in singles2:
        hit = swept(p)
        if hit: removed.append({'id': hit, 'poly': p, 'why': 'a single line in a door\'s swing (the door symbol drawn on a wall layer)', 'kind': 'single'})
        else: keep.append(p)
    singles2 = keep
    # Passages are left as they are: nothing inside their footprints may have changed (cut or removed as a fin), apart
    # from where a door or window of its own crosses or touches one (a detected passage can run through a doorway).
    W2, G2, S2 = unary_union(walls2), unary_union(glass2), unary_union(singles2)
    changed = []
    for o in ops:
        if o['kind'] != 'passage' or math.dist(o['a'], o['b']) < 0.05: continue
        F = Frame(o['a'], o['b'])
        fp = F.rect(0.02, F.L - 0.02, -o['wallThickness'] / 2 - 0.15, o['wallThickness'] / 2 + 0.15).difference(allcut)
        for name, before, after in (('walls', W, W2), ('glass', G, G2), ('single lines', S, S2)):
            d = abs(before.intersection(fp).area - after.intersection(fp).area)
            if d > 1e-6: changed.append(f'{o["id"]} {name} {d:.4f} m2')
    if changed:
        raise SystemExit(f'{floor}: the cut changed what stands inside passages (they must stay as they were): ' + '; '.join(changed))
    log(f'   {floor}: cut {sum(1 for c in cuts if c[0]["kind"] == "door" and not is_glazed(c[0]))} doors and '
        f'{sum(1 for c in cuts if is_glazed(c[0]))} glazed openings ({sum(1 for c in cuts if c[0]["kind"] == "door" and is_glazed(c[0]))} of them sliding glass doors)'
        f' through {nw} wall, {ng} glass and {ns} single-line solids; removed {sum(1 for r in removed if r["kind"] == "glass")} glass fins'
        f' and {sum(1 for r in removed if r["kind"] == "single")} single-line pieces of door symbols;'
        f' pieces: {sum(1 for p in pieces if p["kind"] == "lintel")} lintels, {sum(1 for p in pieces if p["kind"] == "sill")} sills,'
        f' {sum(1 for p in pieces if p["kind"] == "pane")} panes; passages unchanged ({sum(1 for o in ops if o["kind"] == "passage")})')
    out_pieces = [{'kind': p['kind'], 'id': p['id'], **ring(p['poly']), 'z0': round(p['z0'], 3), 'z1': round(p['z1'], 3),
                   **({'top': True} if p.get('top') else {})} for p in pieces]
    out_removed = [{'id': r['id'], 'kind': r['kind'], **ring(r['poly']), 'why': r['why']} for r in removed]
    return walls2, glass2, singles2, out_pieces, recs, out_removed
