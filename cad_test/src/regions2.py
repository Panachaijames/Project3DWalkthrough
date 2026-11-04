import collections, json, ezdxf
from ezdxf import recover, bbox
doc, _ = recover.readfile('plan.dxf')
msp = doc.modelspace()
XS, YS = 68171, 34160
# what is inside the two inserts on layer 0?
for ins in msp.query('INSERT[layer=="0"]'):
    c = collections.Counter()
    def walk(i, depth=0):
        for v in i.virtual_entities():
            if v.dxftype()=='INSERT' and depth<4: walk(v, depth+1)
            else: c[(v.dxf.layer, v.dxftype())] += 1
    walk(ins)
    b = bbox.extents([ins])
    print(f"INSERT {ins.dxf.name} at {tuple(round(v) for v in ins.dxf.insert)} size {round((b.extmax.x-b.extmin.x)/1000,1)}x{round((b.extmax.y-b.extmin.y)/1000,1)} m, {sum(c.values())} entities inside")
    by_layer = collections.Counter()
    for (lay,t),n in c.items(): by_layer[lay]+=n
    print("   layers:", by_layer.most_common(12))
# Quadrant extents using everything except annotation layers
SKIP = ('GRID','DIM','TEXT','SPEC','COLCL','NORTH','RNAME','SECTION','ELEV')
cache = bbox.Cache(); quads = collections.defaultdict(list)
for e in msp:
    if any(k in e.dxf.layer.upper() for k in SKIP): continue
    b = bbox.extents([e], cache=cache)
    if not b.has_data: continue
    q = ('plan' if b.center.y <= YS else 'elev') + ('_left' if b.center.x < XS else '_right')
    quads[q].append(b)
regions = {}
for q, bs in quads.items():
    # robust: 1st-99th percentile of extents to drop strays
    xs0 = sorted(b.extmin.x for b in bs); ys0 = sorted(b.extmin.y for b in bs); xs1 = sorted(b.extmax.x for b in bs); ys1 = sorted(b.extmax.y for b in bs)
    k = max(0, int(len(bs)*0.005))
    r = [xs0[k], ys0[k], xs1[-1-k], ys1[-1-k]]
    regions[q] = r
    print(f"{q}: {len(bs)} entities, {round((r[2]-r[0])/1000,1)} x {round((r[3]-r[1])/1000,1)} m")
json.dump(regions, open('regions.json','w'))
