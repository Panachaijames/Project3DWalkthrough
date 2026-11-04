import collections, json
from ezdxf import recover, bbox
doc, _ = recover.readfile('plan.dxf'); msp = doc.modelspace()
XS, YS = 68171, 34160
cache = bbox.Cache(); q = collections.defaultdict(collections.Counter); qt = collections.defaultdict(collections.Counter)
for e in msp:
    b = bbox.extents([e], cache=cache)
    if not b.has_data: continue
    k = ('plan' if b.center.y <= YS else 'elev') + ('_left' if b.center.x < XS else '_right')
    q[k][e.dxf.layer] += 1
    if e.dxf.layer == '0': qt[k][e.dxftype()] += 1
for k in ('plan_left','plan_right','elev_left','elev_right'):
    print(f"\n{k}: {sum(q[k].values())} entities")
    print("   ", ", ".join(f"{l}:{n}" for l,n in q[k].most_common(16)))
    if qt[k]: print("    layer-0 types:", dict(qt[k]))
