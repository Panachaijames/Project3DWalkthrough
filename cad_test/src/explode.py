import collections, json, pickle
from ezdxf import recover, bbox
doc, _ = recover.readfile('plan.dxf'); msp = doc.modelspace()
XS, YS = 68171, 34160
flat = []   # (effective_layer, type, entity, block_path)
def walk(entity, inherited_layer=None, path=()):
    lay = entity.dxf.get('layer', '0')
    if lay == '0' and inherited_layer: lay = inherited_layer
    if entity.dxftype() == 'INSERT':
        try:
            for v in entity.virtual_entities():
                walk(v, lay, path + (entity.dxf.name,))
        except Exception as ex:
            flat.append((lay, 'INSERT?', entity, path))
        for a in entity.attribs: flat.append((lay, 'ATTRIB', a, path))
    else:
        flat.append((lay, entity.dxftype(), entity, path))
for e in msp: walk(e)
print("exploded entities:", len(flat))
cache = bbox.Cache()
quad = collections.defaultdict(collections.Counter)
from_block = collections.defaultdict(collections.Counter)
for lay, t, e, path in flat:
    try: b = bbox.extents([e])
    except Exception: continue
    if not b.has_data: continue
    k = ('plan' if b.center.y <= YS else 'elev') + ('_left' if b.center.x < XS else '_right')
    quad[k][lay] += 1
    if path: from_block[k][lay] += 1
for k in ('plan_left','plan_right'):
    print(f"\n{k}: {sum(quad[k].values())} entities after exploding blocks")
    print("   ", ", ".join(f"{l}:{n}" for l,n in quad[k].most_common(18)))
    print("    (of which inside blocks):", ", ".join(f"{l}:{n}" for l,n in from_block[k].most_common(10)))
