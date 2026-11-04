import collections, math
from ezdxf import recover, bbox, path as ezpath
doc, _ = recover.readfile('plan.dxf'); msp = doc.modelspace()
layer_lt = {l.dxf.name: l.dxf.get('linetype', 'Continuous') for l in doc.layers}
stats = collections.defaultdict(lambda: [0, 0.0])
def eff_lt(e, lay, inh_lt):
    lt = e.dxf.get('linetype', 'BYLAYER')
    if lt.upper() == 'BYLAYER': return layer_lt.get(lay, 'Continuous')
    if lt.upper() == 'BYBLOCK': return inh_lt or 'Continuous'
    return lt
def walk(e, inh=None, inh_lt=None):
    lay = e.dxf.get('layer', '0')
    if lay == '0' and inh: lay = inh
    lt = eff_lt(e, lay, inh_lt)
    if e.dxftype() == 'INSERT':
        try:
            for v in e.virtual_entities(): walk(v, lay, lt)
        except Exception: pass
        return
    if lay.upper() in ('WALL', 'COL', 'WIN', 'WALL-GL', 'STAIR') or 'A-WALL' in lay.upper():
        try: p = list(ezpath.make_path(e).flattening(distance=15))
        except Exception: return
        L = sum(math.dist((a.x, a.y), (b.x, b.y)) for a, b in zip(p, p[1:]))
        s = stats[(lay, lt.upper())]; s[0] += 1; s[1] += L
for e in msp: walk(e)
for (lay, lt), (n, L) in sorted(stats.items(), key=lambda kv: -kv[1][1]):
    print(f"  {lay:22} {lt:18} {n:5} entities, {round(L/1000):6} m of line")
