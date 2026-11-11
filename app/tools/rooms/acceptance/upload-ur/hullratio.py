import json, sys, os
from shapely.geometry import Polygon, MultiPoint
from shapely.ops import unary_union
def poly(o, h):
    p = Polygon(o, h or [])
    return p if p.is_valid else p.buffer(0)
for f in sys.argv[1:]:
    ov = json.load(open(f, encoding='utf-8'))
    for fl in ov['floors']:
        parts = [poly(p['o'], p['h']) for p in fl['parts'] if p['kind'] in ('wall', 'glass', 'column')]
        walls = unary_union([p for p in parts if not p.is_empty])
        slabs = unary_union([poly(s['o'], s['h']) for s in fl['slabs']])
        hull = walls.convex_hull
        print(f.split("/")[0].ljust(30), fl['key'].ljust(7), f'hull {hull.area:7.0f} slab {slabs.area:6.0f} ratio {slabs.area / max(1, hull.area):.2f}')
