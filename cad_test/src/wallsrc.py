import json, collections
from ezdxf import recover, bbox
doc, _ = recover.readfile('plan.dxf'); msp = doc.modelspace()
regions = json.load(open('regions.json'))
layer_lt = {l.dxf.name: l.dxf.get('linetype', 'Continuous') for l in doc.layers}
stat = collections.Counter(); small = collections.Counter()
def inr(b, r, pad=500): return b.extmin.x >= r[0]-pad and b.extmax.x <= r[2]+pad and b.extmin.y >= r[1]-pad and b.extmax.y <= r[3]+pad
def walk(e, inh=None, path=''):
    lay = e.dxf.get('layer', '0')
    if lay == '0' and inh: lay = inh
    if e.dxftype() == 'INSERT':
        try:
            for v in e.virtual_entities(): walk(v, lay, e.dxf.name)
        except Exception: pass
        return
    if lay.upper() != 'WALL': return
    lt = e.dxf.get('linetype', 'BYLAYER'); lt = layer_lt.get(lay, 'Continuous') if lt.upper() == 'BYLAYER' else lt
    if lt.upper() not in ('CONTINUOUS', 'BYBLOCK'): return
    b = bbox.extents([e])
    if not b.has_data: return
    fl = 'ground' if inr(b, regions['plan_left']) else ('upper' if inr(b, regions['plan_right']) else None)
    if not fl: return
    size = max(b.extmax.x - b.extmin.x, b.extmax.y - b.extmin.y)
    bucket = '<150mm' if size < 150 else ('150-400mm' if size < 400 else '>=400mm')
    stat[(fl, e.dxftype(), bucket)] += 1
    if size < 400: small[(fl, e.dxftype(), path)] += 1
for e in msp: walk(e)
for k, n in sorted(stat.items()): print(k, n)
print("\nsmall pieces by source block:")
for k, n in small.most_common(10): print("  ", k, n)
