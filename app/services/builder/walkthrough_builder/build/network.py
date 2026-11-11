"""The wall network of a floor, and the plate before its holes (docs/rooms/DESIGN.md R-2, R-4.1, R-4.2, R-6.2, R-6.3,
R-12.3). Owner: R1.

    network_of(fb, fixes, X) -> contracts.NetworkResult          pass 1
    plate_of(fb, net, fixes, X) -> (plate0, [contracts.Unfloored], contracts.FloorSlabReport)

Geometry is shapely, in sheet metres AFTER alignment (the build frame). Fix points and report rows are in the floor's OWN
sheet frame (the build frame less the floor's alignment shift, as every other report row: build/report.py), so the
functions here add the shift to a fix and take it off a row; the shift and the lines staff set aside come from
`X.floor_info[key]` (build/__init__.py; a missing entry is "no shift, nothing set aside").

The network N of a floor (R-2.1) is the union of
  1. everything built that bounds a space (FloorBuilt.e_walls) and 2. every opening's span: STRUCTURE;
  3. the single-line parts and 4. every continuous line on a wall, column, glass, window or screen layer, as a strip
     2 cm wide, the lines staff set aside among them unless their record says "the floor runs past it": LOOSE;
  5. room outlines, closed (their edges) or open, 2 cm wide, and 6. staff closing lines, each end extended to the
     network within 0.5 m: STRUCTURE.
Then, in this order (R-2.5): cracks under 10 cm closed (a mitre closing of 0.05 m); the doorway closings (R-2.6); the
bridges (R-2.2); less the app's closings staff removed. From the result N': the faces (holes of 1 m2 or more), which are
rooms when half their edge is structure (R-3.1, rooms.py), and the ring (the filled outside outlines over 4 m2; a
detached piece under 12 m2 only with an opening on it).

`NetworkResult` carries one key more than the contract names, `more`: R1's own working data for its later passes
(plate_of, slabs.cut_slab, ceilings.ceilings_of, bank.build_floors_network). Nobody else reads it, and every reader
here copes with a net that has none (the reference tool's nets, a test's hand-made net).
"""
from __future__ import annotations

import math

import numpy as np
import shapely
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import nearest_points, unary_union
from shapely.strtree import STRtree

from . import fixes as FX
from . import rooms as RM
from .bank import R3, plates_of, polys
from .rooms import merged_lines

CRACK = 0.05                # m: close_mitre(N, 0.05) closes gaps under 10 cm, as today's plate rule does
MIN_FACE = 1.0              # m2: a face smaller than this is no room
MIN_RING = 4.0              # m2: the filled area of a piece of the outside ring
DETACHED = 12.0             # m2: a detached piece under this needs an opening on it (R-2.5)
STRIP = 0.02                # m: the width of a drawn line, an outline edge, a bridge, a closing in the network
LAP = 0.02                  # m: a strip runs this far into what it joins
PAD = 0.03                  # m: the radius of the pad at each end of a closing (see closing_geom)
BOUND_ROLES = frozenset({'wall', 'column', 'glass', 'window', 'screen'})
OUTLINE_CLOSED = 0.10       # m: a room outline whose ends are this close counts as closed (R-2.4)
DISC = 0.5                  # m: the radius of the bridge rule's disc (1.0 m wide, R-2.2)
SPECK_AREA = 0.05           # m2: a free-standing piece under this, filled, takes no part in the bridges
SPECK_LINE = 0.3            # m: ... and a lone drawn line shorter than this
LINE_WIDTH = 0.035          # m: a piece this thin on average is a lone drawn line (a 2 cm strip)
SIMPLIFY = 0.01             # m: the working copy's outline is simplified by this
END_EDGE = (0.04, 0.5)      # m: a wall end is an edge this long (the wall's thickness, R-2.6)
END_BEHIND = 0.3            # m: ... with wall behind it this far
END_FRONT = 0.10            # m: ... and nothing of the network this far in front of it
DOORWAY = (0.10, 2.0)       # m: two wall ends this far apart get a doorway closing
FACING = -math.cos(math.radians(5))     # two wall ends face each other: opposite within 5 degrees
IN_FRONT = 0.6              # the thinner end lies at least this share in front of the other
RING_NEED = 1.0             # m2: an end-to-face closing is kept where the ring would lose this much without it
STAFF_REACH = 0.5           # m: a staff closing line's end is extended to the network within this
DOOR_NEAR = 0.05            # m: a terrace has a door, a passage or a doorway closing within this (R-4.2)
STAND = 0.4                 # m: standing room is a 0.8 m disc
UNFLOORED_MIN = 4.0         # m2: an unfloored area is reported from this (R-2.5)
UNFLOORED_CLOSE = 1.5       # m: the round closing and the erosion of the two unfloored rules
MOUTH_MAX = 3.0             # m: a mouth is one stretch of this or less
FRAME = 5.0                 # m: the frame round the floor for the pockets
BIG_ROOM = 150.0            # m2: a room over this with no opening on its edge is asked about (R-4.1)


# ------------------------------------------------------------------------------------------------------ small helpers
def close_mitre(g, r: float):
    return g.buffer(r, join_style='mitre').buffer(-r, join_style='mitre')


def close_round(g, r: float):
    return g.buffer(r, join_style='round', quad_segs=8).buffer(-r, join_style='round', quad_segs=8)


def filled(g):
    """The outlines of a geometry's pieces, filled."""
    ps = polys(g)
    return unary_union([Polygon(p.exterior) for p in ps]) if ps else Polygon()


def union(geoms):
    gs = [g for g in geoms if g is not None and not g.is_empty]
    return unary_union(gs) if gs else Polygon()


def floor_info(X, key: str) -> dict:
    """{ shift: the floor's alignment shift (sheet -> build frame), aside: the lines staff set aside that still bound
    the floor } of one floor (build/__init__.py fills it; absent: no shift, nothing set aside)."""
    info = (getattr(X, 'floor_info', None) or {}).get(key) or {}
    return {'shift': tuple(info.get('shift') or (0.0, 0.0)), 'aside': info.get('aside') or []}


def to_build(p, shift):
    return (float(p[0]) + shift[0], float(p[1]) + shift[1])


def to_sheet(p, shift) -> list:
    return [R3(p[0] - shift[0]), R3(p[1] - shift[1])]


def sheet_ring(g, shift) -> list:
    """The outline of the largest piece of a geometry in the floor's sheet frame ([[x, y], ...], the last point not
    repeated); [] when there is none."""
    ps = polys(g) if g is not None and not g.is_empty else []
    if not ps:
        return []
    p = max(ps, key=lambda q: q.area)
    return [to_sheet(c, shift) for c in list(p.exterior.coords)[:-1]]


def strip(a, b, lap: float = LAP):
    """A 2 cm strip from a to b, running `lap` into what it joins at both ends."""
    L = math.dist(a, b)
    if L < 1e-9:
        return Point(a).buffer(STRIP / 2)
    ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
    return LineString([(a[0] - ux * lap, a[1] - uy * lap), (b[0] + ux * lap, b[1] + uy * lap)]).buffer(STRIP / 2, cap_style='flat')


def item_path(d):
    """The points of a drawn item as one path (closed when the item is), or None."""
    p = d.get('pts')
    if not p or len(p) < 2:
        return None
    out = [(float(p[0][0]), float(p[0][1]))]
    for x, y in p[1:]:
        q = (float(x), float(y))
        if q != out[-1]:
            out.append(q)
    if d.get('closed') and len(out) > 2 and out[0] != out[-1]:
        out.append(out[0])
    return out if len(out) >= 2 else None


def line_strips(paths: list) -> list:
    """Paths -> strips 2 cm wide (one polygon per path)."""
    if not paths:
        return []
    out = shapely.buffer(np.asarray([LineString(p) for p in paths], dtype=object), STRIP / 2, cap_style='flat',
                         join_style='mitre', mitre_limit=2.0)
    return [g for g in out.tolist() if not g.is_empty]


def boundary_paths(items) -> list:
    """R-2.1 point 4: every continuous line on a wall, column, glass, window or screen layer."""
    out = []
    for d in items:
        r = d['roles']
        if 'ignore' in r or not (r & BOUND_ROLES) or not d.get('cont'):
            continue
        p = item_path(d)
        if p is not None:
            out.append(p)
    return out


def outline_items(items):
    """R-2.4 -> (the closed room outlines of 1 m2 or more as polygons, the paths of the open ones)."""
    closed, open_ = [], []
    for d in items:
        if 'room-outline' not in d['roles'] or 'ignore' in d['roles']:
            continue
        p = item_path(d)
        if p is None:
            continue
        if len(p) >= 4 and (p[0] == p[-1] or math.dist(p[0], p[-1]) <= OUTLINE_CLOSED):
            g = Polygon(p).buffer(0)
            if g.area >= MIN_FACE:
                closed.extend(q for q in polys(g) if q.area >= MIN_FACE)
            continue
        open_.append(p)
    return closed, open_


def railing_paths(items) -> list:
    return [p for p in (item_path(d) for d in items if 'railing' in d['roles'] and 'ignore' not in d['roles']) if p is not None]


# ------------------------------------------------------------------------------------------------ doorway closings
def wall_ends(W, N) -> list:
    """R-2.6: the wall ends of the built pieces W: a short edge (the wall's thickness) with wall behind it for 0.3 m
    and nothing of the network N in the 0.10 m in front of it -> [{ a, b, m, n (outward), u, L }]."""
    out = []
    if W.is_empty:
        return out
    shapely.prepare(N)
    for p in polys(W.simplify(0.005)):
        if not p.is_valid:
            continue
        shapely.prepare(p)
        for k, ring in enumerate([p.exterior] + list(p.interiors)):
            cs = list(ring.coords)
            left = ring.is_ccw == (k == 0)                 # the material lies on the left of the edge
            for a, b in zip(cs, cs[1:]):
                L = math.dist(a, b)
                if not (END_EDGE[0] <= L <= END_EDGE[1]):
                    continue
                ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
                nx, ny = (uy, -ux) if left else (-uy, ux)
                behind = Polygon([a, b, (b[0] - nx * END_BEHIND, b[1] - ny * END_BEHIND), (a[0] - nx * END_BEHIND, a[1] - ny * END_BEHIND)])
                if not p.contains(behind) and behind.intersection(p).area < 0.85 * behind.area:
                    continue
                front = Polygon([(a[0] + nx * 0.01, a[1] + ny * 0.01), (b[0] + nx * 0.01, b[1] + ny * 0.01),
                                 (b[0] + nx * (0.01 + END_FRONT), b[1] + ny * (0.01 + END_FRONT)),
                                 (a[0] + nx * (0.01 + END_FRONT), a[1] + ny * (0.01 + END_FRONT))])
                if N.intersects(front) and front.intersection(N).area > 0.2 * front.area:
                    continue
                out.append({'a': a, 'b': b, 'm': ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2), 'n': (nx, ny), 'u': (ux, uy), 'L': L})
    return out


def doorway_candidates(W, N):
    """R-2.6 -> (the end-to-end closings, the end-to-face candidates), each { kind: 'doorway', a, b, width, how }.
    End to end: two wall ends that face each other 0.10 - 2.0 m apart, the thinner at least 60 % in front of the other,
    nothing of the network between them: a strip straight across from the thinner end's middle. End to face: a wall
    end that squarely faces another part of the network 0.10 - 2.0 m ahead."""
    E = wall_ends(W, N)
    ends, faces = [], []
    if not E:
        return ends, faces
    M = np.array([e['m'] for e in E]); Nn = np.array([e['n'] for e in E]); U = np.array([e['u'] for e in E])
    Ls = np.array([e['L'] for e in E])
    used = set()
    for i, e in enumerate(E):
        if i + 1 >= len(E):
            break
        d = M[i + 1:] - M[i]
        along = d @ Nn[i]
        off = np.abs(d @ U[i])
        ok = ((Nn[i + 1:] @ Nn[i]) <= FACING) & (along >= DOORWAY[0]) & (along <= DOORWAY[1]) & \
             (off <= (Ls[i] + Ls[i + 1:]) / 2 - IN_FRONT * np.minimum(Ls[i], Ls[i + 1:]) + 1e-9)
        idx = np.nonzero(ok)[0]
        if not len(idx):
            continue
        j = i + 1 + int(idx[np.argmin(along[idx])])
        f = E[j]
        thin = e if e['L'] <= f['L'] else f
        d0 = float(along[j - i - 1])
        far = (thin['m'][0] + thin['n'][0] * d0, thin['m'][1] + thin['n'][1] * d0)
        half = max(0.01, thin['L'] / 2 - 0.01)
        inner = LineString([(thin['m'][0] + thin['n'][0] * 0.02, thin['m'][1] + thin['n'][1] * 0.02),
                            (far[0] - thin['n'][0] * 0.02, far[1] - thin['n'][1] * 0.02)]).buffer(half, cap_style='flat')
        if N.intersects(inner) and inner.intersection(N).area > 0.05 * inner.area:
            continue
        ends.append(_closing('doorway', thin['m'], far, 'ends'))
        used.add(i); used.add(j)
    for i, e in enumerate(E):
        if i in used:
            continue
        m, n, u = e['m'], e['n'], e['u']

        def reach(o, far):
            hit = LineString([(o[0] + n[0] * 0.02, o[1] + n[1] * 0.02), (o[0] + n[0] * far, o[1] + n[1] * far)]).intersection(N)
            return None if hit.is_empty else Point(o).distance(hit)
        d = reach(m, DOORWAY[1])
        if d is None or not (DOORWAY[0] <= d <= DOORWAY[1]):
            continue
        square = True
        for t in (-0.4, 0.4):
            o = (m[0] + u[0] * e['L'] * t, m[1] + u[1] * e['L'] * t)
            d2 = reach(o, d + 0.05)
            if d2 is None or abs(d2 - d) > 0.05:
                square = False
        if square:
            faces.append(_closing('doorway', m, (m[0] + n[0] * d, m[1] + n[1] * d), 'face'))
    return ends, faces


def _closing(kind: str, a, b, how: str | None = None) -> dict:
    """A closing row { kind, a, b, width }, its ends in a fixed order (the lower by x, then y, first)."""
    a, b = (float(a[0]), float(a[1])), (float(b[0]), float(b[1]))
    if (round(b[0], 4), round(b[1], 4)) < (round(a[0], 4), round(a[1], 4)):
        a, b = b, a
    c = {'kind': kind, 'a': a, 'b': b, 'width': math.dist(a, b)}
    if how:
        c['how'] = how
    return c


# --------------------------------------------------------------------------------------------------------- bridges
def is_speck(p) -> bool:
    """R-2.2 step 1: a free-standing piece that takes no part in the bridges: under 0.05 m2 when filled, unless it is a
    lone drawn line (a 2 cm strip) of 0.3 m or more."""
    if Polygon(p.exterior).area >= SPECK_AREA:
        return False
    per = p.length
    if per > 0 and 2 * p.area / per <= LINE_WIDTH and per / 2 >= SPECK_LINE:
        return False                                       # a lone drawn line of 0.3 m or more
    return True


def working_copy(pieces: list, specks: bool = False):
    """R-2.2 step 1: the network for the closing only: free-standing specks left out (unless `specks`), the holes too
    small to hold the disc filled, the outline simplified by 1 cm."""
    lim = math.pi * DISC * DISC
    keep = [Polygon(p.exterior, [h for h in p.interiors if Polygon(h).area >= lim]) for p in pieces if specks or not is_speck(p)]
    if not keep:
        return Polygon()
    M = unary_union(keep).simplify(SIMPLIFY)
    if not M.is_valid:
        M = M.buffer(0)
    return M


def _nearest_pair(s1, s2):
    """The shortest segment between two stretches; ties: the lower midpoint by x, then y (R-2.2 step 4)."""
    best = None
    for src, dst, flip in ((s1, s2, False), (s2, s1, True)):
        for c in src.coords:
            v = Point(c)
            q = dst.interpolate(dst.project(v))
            a, b = ((q.x, q.y), (c[0], c[1])) if flip else ((c[0], c[1]), (q.x, q.y))
            key = (round(math.dist(a, b), 5), round((a[0] + b[0]) / 2, 5), round((a[1] + b[1]) / 2, 5))
            if best is None or key < best[0]:
                best = (key, a, b)
    return best[1], best[2]


def _piece_strips(G, M, areas, near) -> list:
    """R-2.2 steps 3 and 4 for one piece of the closing that lies between two or more open areas: its free edges (on
    the closing's outline) each face an open area and lie between two stretches of contact with the network; one
    strip joins each such pair of neighbouring stretches, and a strip the separation does not need is dropped again
    (the longest first) -> [(a, b)]."""
    x0, y0, x1, y1 = G.bounds
    Mb = M.intersection(box(x0 - 0.05, y0 - 0.05, x1 + 0.05, y1 + 0.05)).buffer(1e-4)
    edge = G.boundary
    contact = [l for l in merged_lines(edge.intersection(Mb)) if l.length > 1e-3]
    free = [l for l in merged_lines(edge.difference(Mb)) if l.length > 2e-3]
    if len(contact) < 2 or not free:
        return []
    arcs = []                                              # (pair of stretches, the open area the arc faces)
    for arc in free:
        ends = []
        for c in (arc.coords[0], arc.coords[-1]):
            pt = Point(c)
            ds = [s.distance(pt) for s in contact]
            k = int(np.argmin(ds))
            ends.append(k if ds[k] <= 5e-3 else None)
        if None in ends or ends[0] == ends[1]:
            continue
        mid = arc.interpolate(0.5, normalized=True)
        area = next((int(i) for i in near if areas[int(i)].distance(mid) <= 1e-3), None)
        if area is not None:
            arcs.append(((min(ends), max(ends)), area))
    if len({a for _, a in arcs}) < 2:
        return []
    segs = {pair: _nearest_pair(contact[pair[0]], contact[pair[1]]) for pair in sorted({p for p, _ in arcs})}
    keep = set(segs)
    for pair in sorted(segs, key=lambda q: (-round(math.dist(*segs[q]), 5), q)):
        if len({a for p, a in arcs if p not in keep - {pair}}) <= 1:
            keep.discard(pair)                             # the areas stay apart without it
    return [segs[p] for p in sorted(keep)]


def bridges_of(M) -> list:
    """R-2.2 steps 2 - 4 on the working copy M -> the bridges [{ kind: 'bridge', a, b, width }]: each connected piece of
    the round closing less M that lies between two different open areas (the rooms of 1 m2 or more outside the
    closing, and the outside) becomes a straight strip between the parts of M it joins."""
    if M.is_empty:
        return []
    C = close_round(M, DISC)
    pieces = [g for g in polys(C.difference(M)) if g.area >= 1e-5]
    if not pieces:
        return []
    x0, y0, x1, y1 = C.bounds
    areas = [a for a in polys(box(x0 - 3, y0 - 3, x1 + 3, y1 + 3).difference(C)) if a.area >= MIN_FACE]
    if len(areas) < 2:
        return []
    tree = STRtree(areas)
    out = []
    for G in pieces:
        near = sorted(int(i) for i in tree.query(G, predicate='dwithin', distance=1e-6))
        if len(near) < 2:
            continue
        for a, b in _piece_strips(G, M, areas, near):
            out.append(_closing('bridge', a, b))
    out.sort(key=lambda c: (round((c['a'][0] + c['b'][0]) / 2, 4), round((c['a'][1] + c['b'][1]) / 2, 4), round(c['width'], 4)))
    return out


def closing_geom(c):
    """A closing in the network: its 2 cm strip, with a 3 cm pad at each end. A bridge ends on the nearest points of
    two parts, often corner tips, which a bare strip would meet in a point (and the 10 cm crack rule does not join two
    corners that meet diagonally)."""
    g = c.get('geom')
    if g is None:
        g = c['geom'] = unary_union([strip(c['a'], c['b']), Point(c['a']).buffer(PAD, quad_segs=2), Point(c['b']).buffer(PAD, quad_segs=2)])
    return g


def all_bridges(N1) -> list:
    """The bridges of the network N1 (cracks closed, doorway closings in): the rule run again on its own result until
    no piece of the closing lies between two open areas any more (a piece that joins more than two parts can need a
    second strip once the first is in place; three rounds at most)."""
    out, cur = [], N1
    for _ in range(3):
        found = bridges_of(working_copy(polys(cur)))
        found = [c for c in found if not any(math.dist(c['a'], d['a']) < 1e-6 and math.dist(c['b'], d['b']) < 1e-6 for d in out)]
        if not found:
            break
        out += found
        cur = close_mitre(union([cur] + [closing_geom(c) for c in found]), CRACK)
    return out


# -------------------------------------------------------------------------------------------------- faces and the ring
def _door_tree(doors):
    ds = [g for g in doors if g is not None and not g.is_empty]
    return (STRtree(ds), ds) if ds else (None, [])


def _has_door(p, tree, ds) -> bool:
    if tree is None:
        return False
    return any(ds[int(i)].intersection(p).area > 1e-6 for i in tree.query(p, predicate='intersects'))


def pieces_of(Np, doors):
    """R-2.5: the pieces of close_mitre(N', 0.05) -> [{ poly, outline (filled), area, door, ring, object }]. A piece is
    part of the ring when its filled area is over 4 m2; a detached piece under 12 m2 only with an opening span or a
    doorway closing on it; such a piece without one is an object (R-3.1)."""
    tree, ds = _door_tree(doors)
    out = []
    for p in polys(close_mitre(Np, CRACK)):
        outline = Polygon(p.exterior)
        a = outline.area
        small = round(a, 3) < DETACHED
        door = _has_door(p, tree, ds) if small and a > 0.5 else not small
        out.append({'poly': p, 'outline': outline, 'area': a, 'door': door, 'ring': a > MIN_RING and (not small or door),
                    'object': small and not door})
    return out


def ring_of(pieces):
    return union([q['outline'] for q in pieces if q['ring']])


def _ring(M, extra, doors):
    """The ring of the working copy M with the closings `extra` added, bridges and all (the end-to-face test)."""
    N = union([M] + [closing_geom(c) for c in extra])
    N = union([N] + [closing_geom(c) for c in all_bridges(N)])
    return ring_of(pieces_of(N, doors + [closing_geom(c) for c in extra]))


def doorway_closings(W, Nc, spans) -> list:
    """R-2.6 -> the doorway closings of a floor: every end-to-end one, and the end-to-face candidates only where the
    outside ring would lose 1 m2 or more without them (each tested alone against all the others). A candidate that
    does not lie on the floor the candidates gain together cannot lose any, so only those on it are tested."""
    ends, faces = doorway_candidates(W, Nc)
    if not faces:
        return ends
    M = working_copy(polys(union([Nc] + [closing_geom(c) for c in ends])))
    full = _ring(M, faces, spans)
    gain = full.difference(_ring(M, [], spans))
    if gain.area < RING_NEED:
        return ends
    keep = []
    for k, c in enumerate(faces):
        if closing_geom(c).distance(gain) > 0.1:
            continue
        if full.area - _ring(M, faces[:k] + faces[k + 1:], spans).area >= RING_NEED:
            keep.append(c)
    return ends + keep


# ------------------------------------------------------------------------------------------------------- the network
def network_of(fb, fixes, X):
    """-> contracts.NetworkResult of one floor (pass 1), with R1's working data in `more`."""
    key = fb['key']
    info = floor_info(X, key)
    shift = info['shift']
    fixes = fixes or {}
    built = union(fb['e_walls'])
    spans = [r['span'] for r in fb['recs'] if r.get('span') is not None and not r['span'].is_empty]
    singles = list(fb.get('singles') or [])
    drawn = line_strips(boundary_paths(fb['items']) + boundary_paths(info['aside']))
    out_polys, out_open = outline_items(fb['items'])
    outlines = [p.exterior.buffer(STRIP / 2, join_style='mitre', mitre_limit=2.0) for p in out_polys] + line_strips(out_open)
    base = union([built] + spans + singles + drawn + outlines)

    # staff closing lines (R-6.2), each end extended to the nearest part of the network within 0.5 m
    staff, closing_rows = [], {}
    mine = FX.floor_fixes(fixes, 'closings', key)
    for k, f in mine:
        if f.get('use', 'line') != 'line':
            continue
        a, b = to_build(f['a'], shift), to_build(f['b'], shift)
        reach = [None, None]                               # where each end meets the network, when it stops short of it
        if not base.is_empty:
            for i, end in enumerate((a, b)):
                pt = Point(end)
                if 0 < base.distance(pt) <= STAFF_REACH:
                    q = nearest_points(pt, base)[1]
                    reach[i] = (q.x, q.y)
        path = ([reach[0]] if reach[0] else []) + [a, b] + ([reach[1]] if reach[1] else [])
        g = LineString(path).buffer(STRIP / 2, cap_style='square', join_style='mitre', mitre_limit=2.0)
        staff.append({'kind': 'staff', 'a': a, 'b': b, 'width': math.dist(a, b), 'fix': k, 'geom': g})
        closing_rows[k] = True

    N0 = union([base] + [c['geom'] for c in staff])
    if N0.is_empty:
        net = {'N': N0, 'closings': [], 'faces': [], 'spaces': [], 'shapes': 0, 'ring': Polygon()}
        net['more'] = _more(fb, [], [], [], [], [], Polygon(), shift, closing_rows, mine)
        return net
    Nc = close_mitre(N0, CRACK)                             # 1. the network, cracks closed
    doorways = doorway_closings(built, Nc, spans)           # 2. the doorway closings
    N1 = union([Nc] + [closing_geom(c) for c in doorways])
    bridges = all_bridges(N1)                               # 3. the bridges
    closings = doorways + bridges
    for k, f in mine:                                       # 4. less the app's closings staff removed
        if f.get('use', 'line') != 'none':
            continue
        a, b = to_build(f['a'], shift), to_build(f['b'], shift)
        hit = FX.removed_closings(closings, a, b)
        closing_rows[k] = bool(hit)
        closings = [c for c in closings if not any(c is h for h in hit)]
    doorways = [c for c in closings if c['kind'] == 'doorway']
    bridges = [c for c in closings if c['kind'] == 'bridge']
    Np = union([Nc] + [closing_geom(c) for c in closings])
    doors = spans + [closing_geom(c) for c in doorways]
    pieces = pieces_of(Np, doors)
    ring = ring_of(pieces)
    struct = union([built] + spans + outlines + [c['geom'] for c in staff] + [closing_geom(c) for c in doorways])
    faces, spaces, shapes = RM.rooms_of_network(fb, pieces, struct, out_polys, union([c['geom'] for c in staff]), X)
    out_closings = [{'kind': c['kind'], 'a': c['a'], 'b': c['b'], 'width': c['width'], **({'fix': c['fix']} if 'fix' in c else {})}
                    for c in doorways + bridges + staff]
    net = {'N': Np, 'closings': out_closings, 'faces': faces, 'spaces': spaces, 'shapes': shapes, 'ring': ring}
    net['more'] = _more(fb, pieces, doors, doorways, spans, out_polys, struct, shift, closing_rows, mine)
    return net


def _more(fb, pieces, doors, doorways, spans, out_polys, struct, shift, closing_rows, mine) -> dict:
    return {'key': fb['key'], 'shift': shift, 'pieces': pieces, 'doors': doors, 'doorways': doorways, 'spans': spans,
            'outlines': out_polys, 'struct': struct,
            'closingFixes': [{'fix': k, 'matched': bool(closing_rows.get(k, False))} for k, _ in mine],
            'terraces': [], 'fenced': [], 'floorHere': [], 'noFloor': [], 'noCeiling': [], 'unfloored': [], 'roomFixes': [],
            'shafts': [], 'staffNames': []}


def more_of(net) -> dict:
    """R1's working data of a net, or its empty shape when the net has none (a hand-made net)."""
    m = net.get('more')
    if m is None:
        m = net['more'] = {'key': None, 'shift': (0.0, 0.0), 'pieces': [], 'doors': [], 'doorways': [], 'spans': [],
                           'outlines': [], 'struct': Polygon(), 'closingFixes': [], 'terraces': [], 'fenced': [],
                           'floorHere': [], 'noFloor': [], 'noCeiling': [], 'unfloored': [], 'roomFixes': [], 'shafts': [],
                           'staffNames': []}
    return m


# ------------------------------------------------------------------------------------------------ terraces, unfloored
def _fenced_faces(fb, net, more):
    """R-4.2 point 2: the faces of N' plus railings and parapets (railing lines as 2 cm strips; the same crack and
    bridge rules, free-standing specks taking part) that lie outside the ring and have standing room -> (the pieces
    of that larger network, cracks closed; [(area outside the ring, a door within 5 cm of it?)])."""
    ring = net['ring']
    rails = list(fb.get('rails') or []) + list(fb.get('parapets') or []) + line_strips(railing_paths(fb['items']))
    Np = net['N']
    if Np.is_empty and not rails:
        return [], []
    cp = polys(close_mitre(union([Np] + rails), CRACK)) if rails else ([q['poly'] for q in more['pieces']] or polys(close_mitre(Np, CRACK)))
    if not rails and not any(is_speck(p) for p in cp):
        return cp, []                                       # nothing more than the network's own faces
    extra = bridges_of(working_copy(cp, specks=True))
    if extra:
        cp = polys(close_mitre(union(cp + [closing_geom(c) for c in extra]), CRACK))
    objects = union([q['outline'] for q in more['pieces'] if q['object']])
    inside = union([ring.buffer(0.01), objects.buffer(0.01)]) if not objects.is_empty else ring.buffer(0.01)
    door_spans = union([r['span'].buffer(DOOR_NEAR) for r in fb['recs'] if r['o']['kind'] in ('door', 'passage')] +
                       [closing_geom(c).buffer(DOOR_NEAR) for c in more['doorways']])
    fence = union(rails)
    out = []
    for p in cp:
        for h in p.interiors:
            f = Polygon(h)
            if f.area < MIN_FACE:
                continue
            for t in polys(f.difference(inside)):
                if t.area < MIN_FACE or t.buffer(-STAND).is_empty:
                    continue
                door = (not door_spans.is_empty) and t.distance(door_spans) <= 0
                if not fence.is_empty:                     # the floor runs under the railings that fence it
                    grown = close_mitre(union([t, fence.intersection(t.buffer(0.2))]), 0.03).difference(ring)
                    t = max(polys(grown), key=lambda q: q.area) if not grown.is_empty else t
                out.append((t, door))
    out.sort(key=lambda r: (round(r[0].bounds[0], 3), round(r[0].bounds[1], 3), round(r[0].area, 3)))
    return cp, out


def _mouth(area, solid):
    """R-2.5: the mouth of an unfloored area: the stretch of its edge that is neither network nor plate, when it is one
    stretch of 3 m or less -> its two ends, or None."""
    x0, y0, x1, y1 = area.bounds
    near = solid.intersection(box(x0 - 0.2, y0 - 0.2, x1 + 0.2, y1 + 0.2)).buffer(0.03)
    free = [l for l in merged_lines(area.exterior.difference(near)) if l.length > 0.05]
    if len(free) != 1:
        return None
    a, b = free[0].coords[0], free[0].coords[-1]
    if free[0].length > MOUTH_MAX + 2.0 or math.dist(a, b) > MOUTH_MAX or math.dist(a, b) < 1e-6:
        return None
    return ((a[0], a[1]), (b[0], b[1]))


def _unfloored(net, plate, pieces, fenced_open):
    """R-2.5: the unfloored areas beside the plate `plate`, pieces of 4 m2 or more with standing room: beside a gap (the
    parts of a 1.5 m round closing of N' plus railings, filled, that are not on the plate), pockets (the space with
    no floor whose way out is under 3 m wide: cut off from the outside when it is shrunk by 1.5 m), and the fenced
    areas with no door -> [(polygon, kind)] in a fixed order. `pieces`: the network with its railings (_fenced_faces).

    A pocket is the whole of what a 1.5 m disc coming from outside cannot reach round a cut-off core: the core grown
    back (which bulges out through the opening) and the corners and nooks beside it."""
    Np = net['N']
    if Np.is_empty:
        return []
    solid = union([Np, plate])
    M = working_copy(pieces, specks=True)
    gap = filled(close_round(M, UNFLOORED_CLOSE)).difference(solid.buffer(0.02))
    x0, y0, x1, y1 = solid.bounds
    frame = box(x0 - FRAME, y0 - FRAME, x1 + FRAME, y1 + FRAME)
    U = frame.difference(solid.buffer(0.001))
    E = U.buffer(-UNFLOORED_CLOSE, join_style='round', quad_segs=8)
    rim = frame.exterior.buffer(UNFLOORED_CLOSE + 0.5)
    cores = [g for g in polys(E) if not g.intersects(rim)]
    pockets = []
    if cores:
        reach = union([g.buffer(UNFLOORED_CLOSE, join_style='round', quad_segs=8) for g in polys(E) if g.intersects(rim)])
        rest = polys(U.difference(reach))                  # what a 1.5 m disc from outside cannot reach
        back = union([g.buffer(UNFLOORED_CLOSE, join_style='round', quad_segs=8) for g in cores]).intersection(U)
        tree = STRtree(rest) if rest else None
        beside = [rest[int(i)] for i in tree.query(back, predicate='intersects')] if tree is not None else []
        pockets = [Polygon(p.exterior) for p in polys(union([back] + beside))]
    found = []
    for kind, geoms in (('gap', polys(gap)), ('pocket', pockets), ('fenced', fenced_open)):
        for g in geoms:
            if g.area >= UNFLOORED_MIN and not g.buffer(-STAND).is_empty:
                found.append((g, kind))
    # one row per place: a piece that overlaps an earlier, larger one is part of it
    found.sort(key=lambda r: (-round(r[0].area, 3), round(r[0].bounds[0], 3), round(r[0].bounds[1], 3)))
    out = []
    for g, kind in found:
        if any(g.intersection(h).area > 0.5 * g.area for h, _ in out):
            continue
        g = g.simplify(0.02)                               # the buffers' arcs leave hundreds of points
        if g.is_valid and g.geom_type == 'Polygon' and not g.is_empty:
            out.append((g, kind))
    out.sort(key=lambda r: (round(r[0].bounds[0], 3), round(r[0].bounds[1], 3), round(r[0].area, 3)))
    return out


def _closed_across(area, mouth):
    """An unfloored area closed across its mouth: the part on the area's side of the straight line between the
    mouth's two ends (the pocket rule's bulge through the opening is left off)."""
    if mouth is None:
        return area
    a, b = mouth
    L = math.dist(a, b)
    ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
    far = 1000.0
    halves = []
    for sgn in (1, -1):
        nx, ny = -uy * sgn, ux * sgn
        halves.append(Polygon([(a[0] - ux * far, a[1] - uy * far), (b[0] + ux * far, b[1] + uy * far),
                               (b[0] + ux * far + nx * far, b[1] + uy * far + ny * far),
                               (a[0] - ux * far + nx * far, a[1] - uy * far + ny * far)]))
    parts = [area.intersection(h) for h in halves]
    return max(parts, key=lambda g: g.area)


def unfloored_rows(unfloored: list, shift) -> list:
    """The report's `slab.unfloored` rows of a floor's contracts.Unfloored list, in the floor's own sheet frame."""
    return [{'area': round(u['area'], 1), 'at': to_sheet(u['at'], shift), 'o': sheet_ring(u['poly'], shift),
             'answered': bool(u['answered']), 'mouth': [to_sheet(p, shift) for p in u['mouth']] if u['mouth'] else None,
             **({'kind': u['kind']} if 'kind' in u else {})} for u in unfloored]


def closing_rows(closings: list, shift) -> list:
    """The report's `slab.closings` rows of a network's contracts.Closing list, in the floor's own sheet frame."""
    return [{'kind': c['kind'], 'a': to_sheet(c['a'], shift), 'b': to_sheet(c['b'], shift), 'width': R3(c['width']),
             **({'fix': c['fix']} if 'fix' in c else {})} for c in closings]


def _plate(parts):
    """The parts of a plate as one: joined, and the seams between them closed (2 cm, as today's plate rule does)."""
    return close_mitre(union(parts), 0.02)


def plate_of(fb, net, fixes, X):
    """-> (plate0, [contracts.Unfloored], contracts.FloorSlabReport) of one floor (pass 1): the plate before its holes
    (R-4.1): (ring | terraces | today's plate | "floor here") less "no floor here". The room fixes are matched here
    (R-6.3), since they name rooms and unfloored areas."""
    key = fb['key']
    more = more_of(net)
    shift = more['shift'] if more['key'] is not None else floor_info(X, key)['shift']
    fixes = fixes or {}
    ring = net['ring']
    old = fb['old_plate']
    if more['doorways']:                                   # the doorway closings handed to today's rule as passages
        recs = list(fb['recs']) + [{'span': closing_geom(c), 'o': {'kind': 'passage', 'id': 'closing'}} for c in more['doorways']]
        old = plates_of(fb['e_walls'], list(fb['rails']) + list(fb['parapets']), recs, fb['old_stairs'].get('stairs') or [],
                        fb['lowest'])[0]
    with_rails, fenced = _fenced_faces(fb, net, more)
    terraces = [t for t, door in fenced if door]
    fenced_open = [t for t, door in fenced if not door]
    plate_a = _plate([ring, old] + terraces)
    found = _unfloored(net, plate_a, with_rails, fenced_open)
    solid = union([net['N'], plate_a])
    # a place that is mostly stair has no floor by its nature (today's rule drops such strips too): listed, not flagged
    stair_area = union([st['hull'] for st in fb['old_stairs'].get('stairs') or []])
    on_stairs = [g for g, _kind in found if not stair_area.is_empty and g.intersection(stair_area).area >= 0.5 * g.area]
    found = [(g, kind) for g, kind in found if not any(g is h for h in on_stairs)]
    unfloored = []
    for g, kind in found:
        mouth = _mouth(g, solid)
        if mouth is not None:                              # the area ends on the line across its mouth
            closed = _closed_across(g, mouth)
            if closed.geom_type == 'Polygon' and closed.area >= UNFLOORED_MIN:
                g = closed
        at = RM.label_point(g)
        unfloored.append({'poly': g, 'area': g.area, 'at': (at.x, at.y), 'mouth': mouth, 'answered': False, 'kind': kind})

    # the room fixes (R-6.2, R-6.3): the room containing the point; else the unfloored area containing it; else the
    # room within 0.5 m; else, for "floor here", the fenced face containing it; else unmatched
    spaces = net['spaces']
    rows, floor_here, no_floor, no_ceiling, names = [], [], [], [], []
    for k, f in FX.floor_fixes(fixes, 'rooms', key):
        pt = Point(to_build(f['at'], shift))
        slab, ceiling, name = f.get('slab') or 'auto', f.get('ceiling') or 'auto', (f.get('name') or '').strip()
        kind, what = FX.room_target(pt, spaces, unfloored, fenced_open, slab)
        room = what if kind == 'room' else None
        area = what if kind == 'unfloored' else None
        target = None
        if room is not None:
            if name:
                names.append((room['id'], name))
            if slab == 'none':
                no_floor.append(room['poly'])
            if ceiling == 'none':
                room['ceiling'] = False
                no_ceiling.append(room['poly'])
            target = room['id']
        elif area is not None:
            if slab == 'none':
                area['answered'] = True
            elif slab == 'floor':
                floor_here.append({'poly': area['poly'], 'name': name, 'at': (pt.x, pt.y), 'ceiling': ceiling != 'none'})
                area['floored'] = True
            if ceiling == 'none':
                no_ceiling.append(area['poly'])
            target = 'unfloored'
        elif kind == 'fenced':
            floor_here.append({'poly': what, 'name': name, 'at': (pt.x, pt.y), 'ceiling': ceiling != 'none'})
            if ceiling == 'none':
                no_ceiling.append(what)
            target = 'fenced'
        rows.append({'fix': k, 'matched': target is not None})
    more.update(terraces=terraces, fenced=fenced_open, floorHere=floor_here, noFloor=no_floor, noCeiling=no_ceiling,
                roomFixes=rows, staffNames=names)
    plate0 = _plate([plate_a] + [h['poly'] for h in floor_here]) if floor_here else plate_a
    if no_floor:
        plate0 = plate0.difference(unary_union(no_floor))
    unfloored = [u for u in unfloored if not u.pop('floored', False)]
    more['unfloored'] = unfloored
    dropped = [{'area': round(t.area, 2), 'at': to_sheet(RM.label_point(t).coords[0], shift), 'why': 'no door or passage opens onto it'}
               for t in fenced_open if not any(h['poly'].intersection(t).area > 0.5 * t.area for h in floor_here)]
    dropped += [{'area': round(g.area, 2), 'at': to_sheet(RM.label_point(g).coords[0], shift), 'why': 'mostly stair'} for g in on_stairs]
    more['dropped'] = dropped
    out = [{k: u[k] for k in ('poly', 'area', 'at', 'mouth', 'answered', 'kind')} for u in unfloored]
    report = {'ring': round(ring.area, 1), 'terraces': round(union(terraces).area, 1), 'old': round(old.area, 1),
              'plate': round(plate0.area, 1), 'holes': [], 'unfloored': unfloored_rows(out, shift),
              'closings': closing_rows(net['closings'], shift), 'dropped': list(dropped)}
    return plate0, out, report
