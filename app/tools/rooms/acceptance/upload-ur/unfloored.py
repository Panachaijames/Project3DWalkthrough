"""UR experiment: area inside each floor's walls with no floor plate, from a build's overlay.json (read-only)."""
import json, sys, glob, os
from shapely.geometry import Polygon
from shapely.ops import unary_union

def poly(o, h):
    try:
        p = Polygon(o, h or [])
        return p if p.is_valid else p.buffer(0)
    except Exception:
        return None

for f in sys.argv[1:]:
    ov = json.load(open(f, encoding='utf-8'))
    for fl in ov['floors']:
        parts = [poly(p['o'], p['h']) for p in fl['parts'] if p['kind'] in ('wall', 'glass', 'single', 'column', 'railing', 'lintel', 'balustrade', 'low', 'post', 'parapet')]
        parts = [p for p in parts if p is not None and not p.is_empty]
        slabs = unary_union([poly(s['o'], s['h']) for s in fl['slabs']])
        walls = unary_union(parts)
        out = []
        for R in (1.5, 2.5, 4.0):
            C = walls.buffer(R, join_style='round').buffer(-R, join_style='round')
            filled = unary_union([Polygon(g.exterior) for g in getattr(C, 'geoms', [C]) if not g.is_empty])
            miss = filled.difference(slabs.buffer(0.3)).difference(walls.buffer(0.3))
            comps = [g for g in getattr(miss, 'geoms', [miss]) if not g.is_empty and g.area >= 4 and not g.buffer(-0.6).is_empty]
            out.append(f'R{R}: filled {filled.area:.0f} slab {slabs.area:.0f} missing {sum(g.area for g in comps):.0f} m2 in {len(comps)} (largest {max([g.area for g in comps] or [0]):.0f})')
        print(os.path.basename(os.path.dirname(os.path.dirname(os.path.dirname(f))))[:28], fl['key'], ' | '.join(out))
