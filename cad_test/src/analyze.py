import sys, collections, ezdxf
from ezdxf import recover
doc, auditor = recover.readfile('plan.dxf')
print("DXF version:", doc.dxfversion, "| audit errors:", len(auditor.errors), "fixes:", len(auditor.fixes))
h = doc.header
units = {0:'unitless',1:'inches',2:'feet',4:'mm',5:'cm',6:'m'}
print("INSUNITS:", h.get('$INSUNITS'), units.get(h.get('$INSUNITS'),'?'), "| MEASUREMENT:", h.get('$MEASUREMENT'), "| EXTMIN:", h.get('$EXTMIN'), "| EXTMAX:", h.get('$EXTMAX'))
msp = doc.modelspace()
ents = list(msp)
print("Model-space entities:", len(ents))
by_layer = collections.defaultdict(collections.Counter)
for e in ents:
    by_layer[e.dxf.get('layer','0')][e.dxftype()] += 1
print("\nEntities per layer (model space):")
for lay, c in sorted(by_layer.items(), key=lambda kv: -sum(kv[1].values())):
    print(f"  {lay:32} {sum(c.values()):6}  " + ", ".join(f"{t}:{n}" for t,n in c.most_common(6)))
print("\nLayouts (paper-space sheets):", [l.name for l in doc.layouts])
for l in doc.layouts:
    if l.name != 'Model':
        vps = [e for e in l if e.dxftype()=='VIEWPORT']
        print(f"  {l.name}: {len(l)} entities, {len(vps)} viewports")
# Blocks used by INSERTs per relevant layer
print("\nBlock inserts on key layers (block name: count):")
ins = collections.defaultdict(collections.Counter)
for e in msp.query('INSERT'):
    ins[e.dxf.layer][e.dxf.name] += 1
for lay in sorted(ins, key=lambda k: -sum(ins[k].values()))[:14]:
    c = ins[lay]
    print(f"  [{lay}] {sum(c.values())} inserts, {len(c)} block types: " + ", ".join(f"{n}:{k}" for n,k in c.most_common(8)))
# Texts on room-name / text layers
def texts(layer):
    out=[]
    for e in msp.query(f'TEXT MTEXT[layer=="{layer}"]'):
        t = e.dxf.text if e.dxftype()=='TEXT' else e.plain_text()
        out.append(t.replace('\n',' ').strip())
    return out
for lay in ('RNAME','TEXT','TEXT100'):
    t = texts(lay)
    print(f"\nText on {lay}: {len(t)} items. Sample:", t[:40])
# Dimensions
dims = list(msp.query('DIMENSION'))
print("\nDimensions:", len(dims), "on layers", collections.Counter(d.dxf.layer for d in dims).most_common(5))
vals=[]
for d in dims[:4000]:
    try:
        m = d.get_measurement()
        vals.append(round(m if isinstance(m,(int,float)) else m.magnitude, 1))
    except Exception: pass
print("  sample measured values:", sorted(set(vals))[:15], "...", sorted(set(vals))[-10:])
