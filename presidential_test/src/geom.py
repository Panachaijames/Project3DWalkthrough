"""Small geometry helpers for the presidential suite build (shapely; metres)."""
import math
from shapely.geometry import Polygon, LineString


def polys(g):
    """Polygons of any geometry (Polygon, MultiPolygon, GeometryCollection)."""
    if g is None or g.is_empty: return []
    if g.geom_type == 'Polygon': return [g]
    if hasattr(g, 'geoms'): return [p for x in g.geoms for p in polys(x)]
    return []


def even_odd(loops):
    """A HATCH's boundary loops -> its filled area (nested loops alternate fill / hole)."""
    g = Polygon()
    for l in loops:
        if len(l) < 3: continue
        p = Polygon(l).buffer(0)
        if not p.is_empty: g = g.symmetric_difference(p)
    return g.buffer(0)


def mean_width(p):
    """2 * area / perimeter: about the thickness of a long thin shape."""
    return 2 * p.area / p.length if p.length else 0


def circularity(p):
    return 4 * math.pi * p.area / (p.length ** 2) if p.length else 0


def strip(line, width, cap='flat'):
    """A polyline -> a band `width` wide centred on it (flat ends, mitred corners)."""
    return LineString(line).buffer(width / 2, cap_style=cap, join_style='mitre', mitre_limit=3)


def clean(geoms, min_area, cx=0.0, cy=0.0, nd=3):
    """Outlines that survive rounding to the millimetre, shifted by (-cx, -cy): repaired, simplified by 3 mm,
    no repeated points, valid. -> [{'o': [[x,y],...], 'h': [[[x,y],...], ...]}]"""
    R = lambda v: round(v, nd)
    out = []

    def loop(coords, sx, sy):
        pts = []
        for x, y in list(coords)[:-1]:
            q = (R(x - sx), R(y - sy))
            if not pts or q != pts[-1]: pts.append(q)
        while len(pts) > 1 and pts[0] == pts[-1]: pts.pop()
        return pts

    for p in geoms:
        g = p.buffer(0).simplify(0.003, preserve_topology=True)
        for part in polys(g):
            if part.area < min_area: continue
            o = loop(part.exterior.coords, cx, cy)
            # slivers left between merged outlines (< 0.01 m2) are filled; real voids are kept
            hs = [h for h in (loop(i.coords, cx, cy) for i in part.interiors if Polygon(i).area >= 0.01) if len(h) >= 3]
            if len(o) < 3: continue
            q = Polygon(o, hs)
            if q.is_valid:
                out.append({'o': [list(v) for v in o], 'h': [[list(v) for v in h] for h in hs]})
                continue
            for x in polys(q.buffer(0)):                 # rounding made it touch itself: repair once more
                if x.area < min_area: continue
                o2 = loop(x.exterior.coords, 0, 0)
                h2 = [h for h in (loop(i.coords, 0, 0) for i in x.interiors if Polygon(i).area >= 0.01) if len(h) >= 3]
                if len(o2) >= 3 and Polygon(o2, h2).is_valid:
                    out.append({'o': [list(v) for v in o2], 'h': [[list(v) for v in h] for h in h2]})
    return out


def to_shapely(r):
    return Polygon(r['o'], r['h'])
