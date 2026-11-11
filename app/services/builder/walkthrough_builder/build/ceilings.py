"""Ceilings (docs/rooms/DESIGN.md R-5), with options.ceilings 'auto'. Owner: R1.

The ceiling is cut from the top down, out of the plate's outline (R-5.2): one `ceiling` part per connected piece of

    the filled outline of (ring | areas marked "floor here")     this floor's own holes filled: a void is open from
                                                                  the floor below up to this ceiling
    - terraces and kept strips                                    (they lie outside the ring)
    - rooms marked "no ceiling"
    - this floor's own shafts (lift, X shafts)
    - the holes of the floor above (stair wells, kept stair voids, voids, shafts, "no floor" areas)
    - the stair-headroom region of every climbable stair rising from this floor

No closing is used, so nothing is left out by a radius: walls and columns pass through the ceiling. Pieces under
0.5 m2 are dropped. z0 = ceiling height - 0.02, z1 = ceiling height, `follow: false`, label `ceiling`.
"""
from __future__ import annotations

from .bank import polys
from .network import filled, more_of, union

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
    more = more_of(net)
    area = filled(union([net['ring']] + [f['poly'] for f in more['floorHere'] if f.get('ceiling', True)]))
    if h - THICKNESS <= 0.5 or area.is_empty:
        return []
    cut = list(more['terraces']) + list(more['noCeiling']) + list(more['shafts'])
    cut += [g for g in (holes_above, headroom) if g is not None and not g.is_empty]
    if cut:
        area = area.difference(union(cut))
    pieces = sorted((p for p in polys(area) if p.area >= MIN_PIECE),
                    key=lambda p: (round(p.bounds[0], 3), round(p.bounds[1], 3), round(p.area, 3)))
    return [{'floor': fb['key'], 'kind': 'ceiling', 'poly': p, 'z0': round(h - THICKNESS, 3), 'z1': round(h, 3),
             'follow': False, 'label': 'ceiling', 'extra': {}} for p in pieces]

