import json, collections
from ezdxf import recover, bbox
doc, _ = recover.readfile('plan.dxf'); msp = doc.modelspace()
XS, YS = 68171, 34160
KEEP = ('WALL', 'WIN', 'STAIR', 'COL', 'D-JAMB', 'WALL-GL', 'DOOR')
layer_lt = {l.dxf.name: l.dxf.get('linetype', 'Continuous') for l in doc.layers}
boxes = collections.defaultdict(list)
def walk(e, inh=None):
    lay = e.dxf.get('layer', '0')
    if lay == '0' and inh: lay = inh
    if e.dxftype() == 'INSERT':
        try:
            for v in e.virtual_entities(): walk(v, lay)
        except Exception: pass
        return
    if lay.upper() not in KEEP: return
    lt = e.dxf.get('linetype', 'BYLAYER'); lt = layer_lt.get(lay, 'Continuous') if lt.upper() == 'BYLAYER' else lt
    if lt.upper() not in ('CONTINUOUS', 'BYBLOCK'): return
    try: b = bbox.extents([e])
    except Exception: return
    if not b.has_data or max(b.extmax.x - b.extmin.x, b.extmax.y - b.extmin.y) > 25000: return
    q = ('plan' if b.center.y <= YS else 'elev') + ('_left' if b.center.x < XS else '_right')
    boxes[q].append(b)
for e in msp: walk(e)
old = json.load(open('regions.json')); new = dict(old)
for q in ('plan_left', 'plan_right'):
    bs = boxes[q]
    r = [min(b.extmin.x for b in bs), min(b.extmin.y for b in bs), max(b.extmax.x for b in bs), max(b.extmax.y for b in bs)]
    new[q] = r
    print(f"{q}: {len(bs)} pieces, {round((r[2]-r[0])/1000,1)} x {round((r[3]-r[1])/1000,1)} m   old: {round((old[q][2]-old[q][0])/1000,1)} x {round((old[q][3]-old[q][1])/1000,1)} m")
r = new['plan_right']; print("upper floor shifted onto ground coords:", [round(r[0]-74021), round(r[1]), round(r[2]-74021), round(r[3])], " ground:", [round(v) for v in new['plan_left']])
json.dump(new, open('regions.json', 'w'))
