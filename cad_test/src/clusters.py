import collections, json, ezdxf
from ezdxf import recover, bbox
doc, _ = recover.readfile('plan.dxf')
msp = doc.modelspace()
# entity bounding-box centres
cache = bbox.Cache()
pts = []
for e in msp:
    try:
        b = bbox.extents([e], cache=cache)
        if b.has_data:
            c = b.center; pts.append((c.x, c.y, e.dxf.layer, e.dxftype(), b.extmin.x, b.extmin.y, b.extmax.x, b.extmax.y))
    except Exception:
        pass
print("entities with bbox:", len(pts))
# coarse grid clustering (cell = 20 m if units are mm)
CELL = 20000
cells = collections.defaultdict(list)
for p in pts: cells[(int(p[0]//CELL), int(p[1]//CELL))].append(p)
# merge neighbouring occupied cells into clusters (flood fill)
seen=set(); clusters=[]
for k in cells:
    if k in seen: continue
    stack=[k]; comp=[]; seen.add(k)
    while stack:
        c=stack.pop(); comp.append(c)
        for dx in (-1,0,1):
            for dy in (-1,0,1):
                n=(c[0]+dx,c[1]+dy)
                if n in cells and n not in seen: seen.add(n); stack.append(n)
    items=[p for c in comp for p in cells[c]]
    xs0=min(p[4] for p in items); ys0=min(p[5] for p in items); xs1=max(p[6] for p in items); ys1=max(p[7] for p in items)
    lay=collections.Counter(p[2] for p in items)
    clusters.append(dict(n=len(items), bbox=[round(xs0),round(ys0),round(xs1),round(ys1)], size_m=[round((xs1-xs0)/1000,1), round((ys1-ys0)/1000,1)], top_layers=lay.most_common(8)))
clusters.sort(key=lambda c:-c['n'])
for i,c in enumerate(clusters):
    print(f"#{i}: {c['n']} entities, size {c['size_m'][0]} x {c['size_m'][1]} m, bbox {c['bbox']}\n     layers: {c['top_layers']}")
json.dump(clusters, open('clusters.json','w'), ensure_ascii=False)
# attributes inside RNAME / other tag inserts
print("\nAttributes on block inserts (room tags etc.):")
seenattr=collections.Counter()
for ins in msp.query('INSERT'):
    for a in ins.attribs:
        seenattr[(ins.dxf.layer, a.dxf.tag, a.dxf.text)] += 1
for (lay,tag,txt),n in list(seenattr.items())[:60]:
    print(f"  [{lay}] {tag} = {txt!r} x{n}")
