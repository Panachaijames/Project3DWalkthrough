"""The slab of a floor: plate0 less its holes, finished (docs/rooms/DESIGN.md R-4.3, R-4.4). Owner: R1.

    cut_slab(fb, net, plate0, stairs, fixes, X) -> ([contracts.PartGeo] the slab parts, [(what, polygon)] the voids,
                                                    { holes, dropped }: the slab report's rows)            pass 3

The holes, in this order (R-4.3):
  * `stair well`: the well of every climbable stair that passes through or arrives at this floor (R2's
    StairBuilt.wellOf); always cut;
  * `stair`: the kept void of every stair that stays as lines (R2's StairLeft.keptVoid: today's opening);
  * `lift shaft`: today's rule (a cell of 12 m2 or less touching a lift door and no other opening), on EVERY floor: the
    lowest floor of a model is not always the bottom of the building;
  * `shaft` and `void`: the X marks (xmarks.py); a void on the lowest floor is not cut (`hole-skipped`, info);
  * `no floor`: the rooms staff marked "no floor here" (they are out of plate0 already: network.plate_of).
Holes of the lift and X family that overlap or touch are one hole, their union. Every hole except a well and a staff
hole stops at the arrival of a climbable stair (the 1.2 m past its top riser stays floor, R-8.2). A hole under 0.5 m2
is reported and not cut; an X hole of over 60 m2 or over 30 % of plate0 is never cut by itself (`hole-skipped`, check).

Finishing (R-4.4): simplify by 2 cm, grow by 3 cm, cut the holes again, keep the pieces over 4 m2 (the others go into
`dropped`: nothing is lost silently); build/model.py then cleans the parts and makes them safe for 3ds Max.
"""
from __future__ import annotations

import math

from shapely.geometry import Polygon
from shapely.ops import unary_union

from . import xmarks as XM
from .bank import SLAB_EDGE, lift_shafts, polys
from .network import floor_info, more_of, sheet_ring, to_sheet, union

MIN_HOLE = 0.5              # m2: a smaller hole is reported, not cut
MIN_PIECE = 4.0             # m2: a slab piece of this or less is dropped (and reported)
REPORT_PIECE = 0.01         # m2: ... a sliver under this is not worth a row
MAX_HOLE = 60.0             # m2: an X hole over this is never cut by itself
MAX_SHARE = 0.30            # ... nor one over this share of plate0
ARRIVAL = 1.2               # m: the arrival of a climbable stair: this far past its top riser stays floor
TOUCH = 0.02                # m: holes this close are one hole
FAMILY = ('lift shaft', 'shaft', 'void')


def ring(g) -> list:
    """The outline of a hole (build frame, 3 decimals, the last point not repeated): of the polygon, or of the largest
    piece of a geometry in several pieces; [] when there is none."""
    return sheet_ring(g, (0.0, 0.0))


def slab_frame(fb, X):
    """(z0, extra keys) of the floor's slab parts: its thickness, or the plinth down to the ground (U-9.5)."""
    f = X.settings['floors'][fb['index']]
    if X.options['plinth'] == 'auto' and fb['index'] == 0 and f['level'] > 0:
        return -f['level'], {'plinth': True}
    t = f['slabThickness'] if f['slabThickness'] is not None else X.DEF['slabThickness']
    return -t, {}


def arrival_of(sb):
    """The arrival patch of a climbable stair: from its top riser 1.2 m on, as wide as the stair and 5 cm more on each
    side (the stairway's walking line ends 1.0 m past the middle of the top riser, R-8.5), or None."""
    sw = sb['stairway']
    walk = sw.get('walk') or []
    if len(walk) < 2:
        return None
    (x0, y0), (x1, y1) = walk[-2], walk[-1]
    L = math.hypot(x1 - x0, y1 - y0)
    if L < 1e-6:
        return None
    dx, dy = (x1 - x0) / L, (y1 - y0) / L
    half = float(sw.get('width') or 1.0) / 2 + 0.05
    nx, ny = -dy * half, dx * half
    ex, ey = x0 + dx * ARRIVAL, y0 + dy * ARRIVAL
    return Polygon([(x0 + nx, y0 + ny), (x0 - nx, y0 - ny), (ex - nx, ey - ny), (ex + nx, ey + ny)])


def _merge(holes: list) -> list:
    """[(what, polygon)] of the lift and X family -> the same with overlapping or touching ones joined: one hole, their
    union; a lift shaft among them names it, else a void, else it is a shaft."""
    n = len(holes)
    group = list(range(n))

    def root(i):
        while group[i] != i:
            group[i] = group[group[i]]
            i = group[i]
        return i
    for i in range(n):
        for j in range(i + 1, n):
            if holes[i][1].distance(holes[j][1]) <= TOUCH:
                group[root(j)] = root(i)
    out = []
    for r in sorted({root(i) for i in range(n)}):
        mine = [holes[i] for i in range(n) if root(i) == r]
        whats = {w for w, _ in mine}
        what = 'lift shaft' if 'lift shaft' in whats else 'void' if 'void' in whats else 'shaft'
        out.append((what, unary_union([g for _, g in mine]) if len(mine) > 1 else mine[0][1]))
    out.sort(key=lambda h: (round(h[1].bounds[0], 3), round(h[1].bounds[1], 3), round(h[1].area, 3)))
    return out


def cut_slab(fb, net, plate0, stairs, fixes, X):
    """-> ([contracts.PartGeo] the slab parts, [(what, polygon)] the voids, the slab report's `holes` and `dropped`
    rows) of one floor (pass 3)."""
    key = fb['key']
    more = more_of(net)
    shift = more['shift'] if more['key'] is not None else floor_info(X, key)['shift']
    voids, rows = [], []

    def row(what, g, cut, why=None):
        at = g.representative_point()                      # the point of the model's `voids` record (build/model.py)
        r = {'what': what, 'area': round(g.area, 2), 'at': to_sheet((at.x, at.y), shift), 'o': sheet_ring(g, shift), 'cut': cut}
        if why:
            r['why'] = why
        rows.append(r)

    arrivals = union([a for a in (arrival_of(sb) for sb in stairs['built'] if sb['stairway'].get('to') == key) if a is not None])

    def clear(g):
        """A hole less the arrival patches (the hole itself, untouched, when it takes none of them)."""
        return g.difference(arrivals) if not arrivals.is_empty and arrivals.intersects(g) else g
    for sb in stairs['built']:                             # the wells of the stairs you can climb
        well = sb['wellOf'].get(key)
        if well is None or well.is_empty:
            continue
        v = well.intersection(plate0)
        if v.area > 0.01:
            voids.append(('stair well', v)); row('stair well', v, True)
    if not fb['lowest']:                                   # today's opening over a stair that stays as lines
        for sl in stairs['left']:
            v = sl['keptVoid']
            if sl['floor'] != key or v is None or v.is_empty:
                continue
            v = clear(v.intersection(plate0))
            if v.area >= MIN_HOLE:
                voids.append(('stair', v)); row('stair', v, True)
            elif v.area > 0.01:
                row('stair', v, False, 'under 0.5 m2')
    family = []
    if X.options['liftShafts']:
        cells = unary_union([g for g in fb['e_walls'] if g is not None and not g.is_empty] + [r['span'] for r in fb['recs']])
        family += [('lift shaft', c) for c in lift_shafts(plate0, cells, fb['recs'])]
    for x in XM.x_marks(fb, net, X):
        if x['what'] == 'mark':
            row('X mark', x['poly'], False, x.get('why') or 'too small')
        elif fb['lowest'] and x['what'] == 'void':
            row('void', x['poly'], False, 'the lowest floor')
        else:
            family.append((x['what'], x['poly']))
    shafts = []
    for what, g in _merge(family):
        whole = g
        g = clear(g.intersection(plate0))
        if what != 'lift shaft' and (whole.area > MAX_HOLE or (plate0.area > 0 and whole.area > MAX_SHARE * plate0.area)):
            row(what, whole, False, 'over 60 m2' if whole.area > MAX_HOLE else 'over 30 % of the floor')
        elif g.area < MIN_HOLE:
            if g.area > 0.01 or whole.area >= MIN_HOLE:
                row(what, whole, False, 'under 0.5 m2' if g.area > 0.01 else 'off the floor plate')
        else:
            voids.append((what, g)); row(what, g, True)
            if what != 'void':
                shafts.append(g)
    more['shafts'] = shafts
    for g in more['noFloor']:                              # staff: "no floor here" (already out of plate0)
        voids.append(('no floor', g)); row('no floor', g, True)

    plate = plate0
    cut = unary_union([v for _, v in voids]).buffer(0.001) if voids else None
    if cut is not None:
        plate = plate.difference(cut)
    pieces = [Polygon(p.exterior, [h for h in p.interiors if Polygon(h).area >= MIN_HOLE]).simplify(0.02).buffer(SLAB_EDGE, join_style='mitre')
              for p in polys(plate)]
    if cut is not None:
        pieces = [x for p in pieces for x in polys(p.difference(cut))]
    plates = [p for p in pieces if p.area > MIN_PIECE]
    dropped = []
    for p in pieces:
        if REPORT_PIECE <= p.area <= MIN_PIECE:
            at = p.representative_point()
            dropped.append({'area': round(p.area, 2), 'at': to_sheet((at.x, at.y), shift), 'why': 'under 4 m2'})
    z0, extra = slab_frame(fb, X)
    parts = [{'floor': key, 'kind': 'slab', 'poly': p, 'z0': z0, 'z1': 0.0, 'follow': False, 'label': None, 'extra': dict(extra)}
             for p in plates]
    return parts, voids, {'holes': rows, 'dropped': dropped}
