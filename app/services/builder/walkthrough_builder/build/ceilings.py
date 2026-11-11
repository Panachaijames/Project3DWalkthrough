"""Ceilings (docs/rooms/DESIGN.md R-5), with options.ceilings 'auto'. Owner: R1.

THE TRACER of the rooms scaffold R0 (see network.py): one `ceiling` part per connected piece of the ring's filled
outline, less the holes of the floor above and the stair headroom, at the floor's ceiling height (2 cm thick,
`follow: false`). Not yet (R1's): terraces and kept strips taken out, rooms marked "no ceiling", this floor's own
shafts, "floor here" areas.
"""
from __future__ import annotations

from shapely.geometry import Polygon
from shapely.ops import unary_union

from .bank import polys

DEFAULT_HEIGHT = 3.00       # m (R-5.1)
PLENUM = 0.30               # m under the wall top
THICKNESS = 0.02            # m
MIN_PIECE = 0.5             # m2


def ceiling_height(index: int, X) -> float:
    """The floor's ceiling height above its level (R-5.1): the typed one, else min(3.00, wall height - 0.30), and never
    above the underside of the floor above less 2 cm."""
    floors = X.settings['floors']
    f = floors[index]
    h = f.get('ceilingHeight')
    if h is None:
        h = min(DEFAULT_HEIGHT, f['wallHeight'] - PLENUM)
    if index + 1 < len(floors):
        nxt = floors[index + 1]
        t = nxt['slabThickness'] if nxt['slabThickness'] is not None else X.DEF['slabThickness']
        h = min(h, nxt['level'] - f['level'] - t - THICKNESS)
    return h


def ceilings_of(fb, net, plate0, holes_above, headroom, X) -> list:
    """-> [contracts.PartGeo] the ceiling parts of one floor (pass 3). holes_above: the union of the holes of the floor
    above (or None); headroom: the union of the stair-headroom regions of the stairs rising from this floor (or None)."""
    h = ceiling_height(fb['index'], X)
    if h - THICKNESS <= 0.5 or net['ring'].is_empty:
        return []
    area = unary_union([Polygon(p.exterior) for p in polys(net['ring'])])
    cut = [g for g in (holes_above, headroom) if g is not None and not g.is_empty]
    if cut:
        area = area.difference(unary_union(cut))
    return [{'floor': fb['key'], 'kind': 'ceiling', 'poly': p, 'z0': round(h - THICKNESS, 3), 'z1': round(h, 3),
             'follow': False, 'label': 'ceiling', 'extra': {}} for p in polys(area) if p.area >= MIN_PIECE]
