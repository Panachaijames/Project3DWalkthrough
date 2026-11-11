"""X marks: the two diagonals of one box mark a void or a shaft (docs/rooms/DESIGN.md R-4.3). Owner: R1.

An X mark is the two diagonals of one closed shape:
  * two straight lines, each 1.0 m or longer, their lengths within 15 % of each other;
  * crossing at 30 - 150 degrees, in the middle half of both (25 - 75 % along each);
  * their four ends mark a rectangle: four ends at its corners, or three at its corners and the fourth on one of its
    sides (tolerance: 0.15 m, or 10 % of the rectangle's longer side);
  * the rectangle's outline is drawn: at least 60 % of it runs along the network or along drawn lines within 0.15 m;
  * the rectangle is 0.6 m wide or more, and is not 80 % covered by wall or column parts (a column symbol);
  * the lines may be on any layer except furniture and grid layers (dimension layers have no role of their own: the
    drawn-outline test is what keeps crossing dimension lines out). Layers set to `ignore` are read.
The hole is that rectangle: 4 m2 and more is a `void`, 1.0 - 4 m2 a `shaft`; a smaller or narrower one is a `mark`,
reported and never cut (so is a long slot whose diagonals cross at less than 30 degrees: the house's duct and roof
slots). Two X marks are never joined into a larger shape: a line is a diagonal of one X only, the best-fitting box
first (two X's drawn over one lift, as on the tower, would otherwise also pair across); slabs.py cuts overlapping
holes as one.
"""
from __future__ import annotations

import math

from shapely.geometry import LineString, Polygon
from shapely.ops import unary_union
from shapely.strtree import STRtree

SKIP_ROLES = frozenset({'furniture', 'grid'})
STRAIGHT = ('LINE', 'LWPOLYLINE', 'POLYLINE')
MIN_LINE = 1.0              # m
LENGTHS = 0.15              # the two lines' lengths differ by at most this share
ANGLE = (30.0, 150.0)       # degrees
ANGLE_MARK = 5.0            # degrees: below ANGLE a crossing can still mark a slot, which is reported and never cut
MIDDLE = (0.25, 0.75)       # they cross in the middle half of both
TOL = (0.15, 0.10)          # m, or this share of the rectangle's longer side
DRAWN = 0.6                 # this share of the rectangle's outline is drawn
NEAR = 0.15                 # m: ... within this of it
MIN_WIDTH = 0.6             # m
COLUMN = 0.8                # a rectangle covered this much by wall or column parts is a column symbol
VOID = 4.0                  # m2 and more
SHAFT = 1.0                 # m2 and more


def _segments(items, min_len: float, straight_only: bool = True):
    out = []
    for d in items:
        if d['roles'] & SKIP_ROLES:
            continue
        p = d.get('pts')
        if not p or len(p) < 2 or (straight_only and d['t'] not in STRAIGHT):
            continue
        pts = [(float(x), float(y)) for x, y in p]
        if d.get('closed') and len(pts) > 2 and pts[0] != pts[-1]:
            pts.append(pts[0])
        for a, b in zip(pts, pts[1:]):
            if math.dist(a, b) >= min_len:
                out.append((a, b))
    return out


def _box(ends):
    """The rectangle the four ends mark -> (polygon, width, length, corners hit, misfit m) or None: four ends at its corners, or
    three at its corners and the fourth on a side. Tried in the sheet's axes first, then along each line between an
    end of one diagonal and an end of the other; the first frame with four corners wins, else the first with three."""
    a, b, c, d = ends
    frames = [(1.0, 0.0)]
    for p, q in ((a, c), (a, d), (b, c), (b, d)):
        L = math.dist(p, q)
        if L > 1e-6:
            frames.append(((q[0] - p[0]) / L, (q[1] - p[1]) / L))
    best = None
    for ux, uy in frames:
        loc = [(x * ux + y * uy, -x * uy + y * ux) for x, y in ends]
        x0, x1 = min(p[0] for p in loc), max(p[0] for p in loc)
        y0, y1 = min(p[1] for p in loc), max(p[1] for p in loc)
        w, h = x1 - x0, y1 - y0
        if min(w, h) < 1e-6:
            continue
        tol = max(TOL[0], TOL[1] * max(w, h))
        corners = [(x0, y0), (x0, y1), (x1, y0), (x1, y1)]
        hit = [min(range(4), key=lambda k: math.dist(p, corners[k])) for p in loc]
        at = [math.dist(p, corners[k]) <= tol for p, k in zip(loc, hit)]
        on_edge = [min(abs(p[0] - x0), abs(p[0] - x1), abs(p[1] - y0), abs(p[1] - y1)) <= tol for p in loc]
        n = sum(at)
        # the corners hit are different ones, and each diagonal's ends lie at opposite corners
        if n < 3 or not all(on_edge) or len({k for k, ok in zip(hit, at) if ok}) < n:
            continue
        world = [(x * ux - y * uy, x * uy + y * ux) for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1))]
        err = sum(math.dist(p, corners[k]) if ok else min(abs(p[0] - x0), abs(p[0] - x1), abs(p[1] - y0), abs(p[1] - y1))
                  for p, k, ok in zip(loc, hit, at))
        cand = (n, Polygon(world), min(w, h), max(w, h), err)
        if best is None or cand[0] > best[0]:
            best = cand
        if n == 4:
            break
    return None if best is None else (best[1], best[2], best[3], best[0], best[4])


def x_marks(fb, net, X) -> list:
    """The floor's X marks -> [{ 'poly': the rectangle, 'area': m2, 'what': 'void' | 'shaft' | 'mark', 'why': None, or
    for a mark why it is never cut }] in a fixed order (by position)."""
    segs = _segments(fb['items'], MIN_LINE)
    if len(segs) < 2:
        return []
    lines = [LineString(s) for s in segs]
    tree = STRtree(lines)
    pairs = tree.query(lines, predicate='crosses')
    found = []
    for i, j in zip(pairs[0].tolist(), pairs[1].tolist()):
        if j <= i:
            continue
        si, sj = lines[i], lines[j]
        li, lj = si.length, sj.length
        if abs(li - lj) > LENGTHS * max(li, lj):
            continue
        p = si.intersection(sj)
        if p.geom_type != 'Point':
            continue
        ti, tj = si.project(p) / li, sj.project(p) / lj
        if not (MIDDLE[0] <= ti <= MIDDLE[1] and MIDDLE[0] <= tj <= MIDDLE[1]):
            continue
        (ax, ay), (bx, by) = segs[i]
        (cx, cy), (dx, dy) = segs[j]
        ang = abs(math.degrees(math.atan2(by - ay, bx - ax) - math.atan2(dy - cy, dx - cx))) % 180
        if not (ANGLE_MARK <= ang <= 180.0 - ANGLE_MARK):
            continue
        got = _box([(ax, ay), (bx, by), (cx, cy), (dx, dy)])
        if got is None:
            continue
        found.append((got, i, j, ANGLE[0] <= ang <= ANGLE[1]))
    if not found:
        return []
    # the best-fitting boxes first (four corners before three, then the smallest misfit); a line is used once
    found.sort(key=lambda f: (-f[0][3], round(f[0][4], 3), round(f[0][0].bounds[0], 3), round(f[0][0].bounds[1], 3), f[1], f[2]))
    every = _segments(fb['items'], 0.02, straight_only=False)        # everything drawn, for the outline test
    every_lines = [LineString(s) for s in every]
    etree = STRtree(every_lines) if every_lines else None
    N = net.get('N')
    solid = [p['poly'] for p in fb.get('parts') or [] if p['kind'] in ('wall', 'column')]
    solid_tree = STRtree(solid) if solid else None
    out, seen, used = [], set(), set()
    for (poly, width, _length, _n, _err), i, j, square in found:
        key = tuple(round(v, 1) for v in poly.bounds)
        if key in seen or i in used or j in used:
            continue
        edge = poly.exterior
        zone = edge.buffer(NEAR)
        own = {segs[i], segs[j]}
        near = [every_lines[int(k)] for k in etree.query(zone, predicate='intersects') if every[int(k)] not in own] if etree is not None else []
        cover = [l.buffer(NEAR) for l in near]
        if N is not None and not N.is_empty:
            cover.append(N.intersection(zone.envelope).buffer(NEAR))
        if not cover or edge.intersection(unary_union(cover)).length < DRAWN * edge.length:
            continue
        if solid_tree is not None:
            inside = sum(solid[int(k)].intersection(poly).area for k in solid_tree.query(poly, predicate='intersects'))
            if inside >= COLUMN * poly.area:
                continue
        seen.add(key); used.add(i); used.add(j)
        area = poly.area
        if width < MIN_WIDTH:
            what, why = 'mark', 'narrower than 0.6 m'
        elif not square:
            what, why = 'mark', 'its lines cross at less than 30 degrees'
        elif area < SHAFT:
            what, why = 'mark', 'under 1 m2'
        else:
            what, why = ('void' if area >= VOID else 'shaft'), None
        out.append({'poly': poly, 'area': area, 'what': what, 'why': why})
    out.sort(key=lambda r: (round(r['poly'].bounds[0], 3), round(r['poly'].bounds[1], 3), round(r['area'], 3)))
    return out
