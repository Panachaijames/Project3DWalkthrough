import collections, json
from ezdxf import recover, bbox
doc, _ = recover.readfile('plan.dxf'); msp = doc.modelspace()
cache = bbox.Cache()
for lay in ('0', 'XR_L44$0$I-FURN', 'WALL'):
    bs = [bbox.extents([e], cache=cache) for e in msp.query(f'*[layer=="{lay}"]')]
    bs = [b for b in bs if b.has_data]
    xs = sorted(b.center.x for b in bs); ys = sorted(b.center.y for b in bs)
    pct = lambda v, p: round(v[int(p*(len(v)-1))])
    print(f"{lay}: n={len(bs)}  x p1/p50/p99 = {pct(xs,.01)}/{pct(xs,.5)}/{pct(xs,.99)}   y p1/p50/p99 = {pct(ys,.01)}/{pct(ys,.5)}/{pct(ys,.99)}")
    # size of typical entity
    sz = sorted(max(b.extmax.x-b.extmin.x, b.extmax.y-b.extmin.y) for b in bs)
    print(f"      entity size p50={round(sz[len(sz)//2])}  p90={round(sz[int(.9*len(sz))])}  max={round(sz[-1])}")
print(json.load(open('regions.json')))
