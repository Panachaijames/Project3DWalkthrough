"""The wall network of a floor, and the plate before its holes (docs/rooms/DESIGN.md R-2, R-4.1, R-12.3). Owner: R1.

THE TRACER of the rooms scaffold R0: thin but working, so that the whole chain from a drawing to a v2 model is green
before R1 and R2 start (R-12.3). R1 replaces the bodies below; the signatures are contracts.py's and stay.

What the tracer does, and what it leaves to R1:
  * the network is today's walls and opening spans only (FloorBuilt.e_walls and the records' spans), cracks under 10 cm
    closed as today. Not yet: the drawn lines on wall, column, glass, window and screen layers, the single-line parts,
    room-outline edges, set-aside lines, doorway closings, bridges, staff closing lines (R-2.1 - R-2.6);
  * faces are the holes of that closing of 1 m2 or more, and every face is a room (R-3.1's "half its edge is structure"
    is R1's); the ring is the filled outside outline of each piece over 4 m2;
  * plate0 = ring | today's plate. Not yet: terraces, "floor here" and "no floor here", unfloored areas and their mouths.
"""
from __future__ import annotations

from shapely.geometry import Polygon
from shapely.ops import unary_union

from . import rooms as RM
from .bank import polys

CRACK = 0.05                # m: close_mitre(N, 0.05) closes gaps under 10 cm, as today's plate rule does
MIN_FACE = 1.0              # m2: a face smaller than this is no room
MIN_RING = 4.0              # m2: the filled area of a piece of the outside ring


def close_mitre(g, r: float):
    return g.buffer(r, join_style='mitre').buffer(-r, join_style='mitre')


def network_of(fb, fixes, X):
    """-> contracts.NetworkResult of one floor (pass 1)."""
    N = unary_union([g for g in fb['e_walls'] if g is not None and not g.is_empty] + [r['span'] for r in fb['recs']])
    pieces = polys(close_mitre(N, CRACK)) if not N.is_empty else []
    outlines = [Polygon(p.exterior) for p in pieces]
    ring = unary_union([o for o in outlines if o.area > MIN_RING]) if outlines else Polygon()
    faces = [f for f in (Polygon(h) for p in pieces for h in p.interiors) if f.area >= MIN_FACE]
    faces.sort(key=lambda f: (round(f.bounds[0], 3), round(f.bounds[1], 3), round(f.area, 3)))    # ids in a fixed order
    return {'N': N, 'closings': [], 'faces': faces, 'spaces': RM.spaces_of(fb, faces, X), 'shapes': 0, 'ring': ring}


def plate_of(fb, net, fixes, X):
    """-> (plate0, [contracts.Unfloored], contracts.FloorSlabReport) of one floor (pass 1): the plate before its holes."""
    old = fb['old_plate']
    plate0 = unary_union([g for g in (net['ring'], old) if g is not None and not g.is_empty]) if not (
        net['ring'].is_empty and old.is_empty) else Polygon()
    report = {'ring': round(net['ring'].area, 1), 'terraces': 0.0, 'old': round(old.area, 1), 'plate': round(plate0.area, 1),
              'holes': [], 'unfloored': [], 'closings': [], 'dropped': []}
    return plate0, [], report
