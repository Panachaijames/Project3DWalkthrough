"""The slab of a floor: plate0 less its holes, finished (docs/rooms/DESIGN.md R-4.3, R-4.4). Owner: R1.

THE TRACER of the rooms scaffold R0 (see network.py). The holes it cuts: the wells of the climbable stairs that pass
through or arrive at this floor (StairBuilt.wellOf) and the kept void of every stair that stays as lines
(StairLeft.keptVoid: today's opening). Not yet (R1's): lift and X shafts, X voids, staff "no floor here" holes, the
fenced band, the hole limits (under 0.5 m2 reported, over 60 m2 or 30 % not cut by itself). The finishing is today's:
simplify by 2 cm, grow by 3 cm, cut the holes again, keep the pieces over 4 m2; smaller pieces go into the report.
"""
from __future__ import annotations

from shapely.geometry import Polygon
from shapely.ops import unary_union

from . import xmarks as XM
from .bank import R3, SLAB_EDGE, polys


def ring(g) -> list:
    """The outline of a hole for the report (sheet m, 3 decimals, the last point not repeated): of the polygon, or of
    the largest piece of a geometry in several pieces; [] when there is none."""
    ps = polys(g) if g is not None and not g.is_empty else []
    if not ps:
        return []
    p = max(ps, key=lambda q: q.area)
    return [[R3(x), R3(y)] for x, y in list(p.exterior.coords)[:-1]]


def slab_frame(fb, X):
    """(z0, extra keys) of the floor's slab parts: its thickness, or the plinth down to the ground (U-9.5)."""
    f = X.settings['floors'][fb['index']]
    if X.options['plinth'] == 'auto' and fb['index'] == 0 and f['level'] > 0:
        return -f['level'], {'plinth': True}
    t = f['slabThickness'] if f['slabThickness'] is not None else X.DEF['slabThickness']
    return -t, {}


def cut_slab(fb, net, plate0, stairs, fixes, X):
    """-> ([contracts.PartGeo] the slab parts, [(what, polygon)] the voids, the slab report's `holes` and `dropped`
    rows) of one floor (pass 3)."""
    key = fb['key']
    voids, skipped = [], []
    if not fb['lowest']:
        for sb in stairs['built']:
            well = sb['wellOf'].get(key)
            if well is not None and not well.is_empty and well.intersection(plate0).area > 0.01:
                voids.append(('stair well', well.intersection(plate0)))
        for sl in stairs['left']:
            v = sl['keptVoid']
            if sl['floor'] == key and v is not None and not v.is_empty:
                voids.append(('stair', v))
    for x in XM.x_marks(fb, net, X):                       # R-4.3: shafts are cut on every floor, voids not on the lowest
        if fb['lowest'] and x['what'] != 'shaft':
            at = x['poly'].representative_point()
            skipped.append({'what': x['what'], 'area': round(x['poly'].area, 2), 'at': [R3(at.x), R3(at.y)],
                            'o': ring(x['poly']), 'cut': False, 'why': 'the lowest floor'})
        else:
            voids.append((x['what'], x['poly'].intersection(plate0)))
    plate = plate0
    cut = unary_union([v for _, v in voids]).buffer(0.001) if voids else None
    if cut is not None:
        plate = plate.difference(cut)
    plates = [Polygon(p.exterior, [h for h in p.interiors if Polygon(h).area >= 0.5]).simplify(0.02).buffer(SLAB_EDGE, join_style='mitre')
              for p in polys(plate) if p.area > 4]
    if cut is not None:
        plates = [x for p in plates for x in polys(p.difference(cut))]
    dropped = [{'area': round(p.area, 2), 'at': [R3(p.representative_point().x), R3(p.representative_point().y)],
                'why': 'under 4 m2'} for p in polys(plate) if 0.5 <= p.area <= 4]
    z0, extra = slab_frame(fb, X)
    parts = [{'floor': key, 'kind': 'slab', 'poly': p, 'z0': z0, 'z1': 0.0, 'follow': False, 'label': None, 'extra': extra}
             for p in plates]
    holes = [{'what': w, 'area': round(v.area, 2), 'at': [R3(v.representative_point().x), R3(v.representative_point().y)],
              'o': ring(v), 'cut': True} for w, v in voids] + skipped
    return parts, voids, {'holes': holes, 'dropped': dropped}
