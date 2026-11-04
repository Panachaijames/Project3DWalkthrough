"""First look at a DXF: version, units, extents, layers by entity count, blocks, texts, xrefs, layouts."""
import sys, collections
from ezdxf import recover, bbox
doc, aud = recover.readfile(sys.argv[1])
h = doc.header
U = {0: 'unitless', 1: 'inches', 2: 'feet', 4: 'mm', 5: 'cm', 6: 'm'}
print('DXF', doc.dxfversion, '| audit errors', len(aud.errors), 'fixes', len(aud.fixes), '| INSUNITS', h.get('$INSUNITS'), U.get(h.get('$INSUNITS'), '?'),
      '| EXTMIN', tuple(round(v) for v in h.get('$EXTMIN', (0, 0, 0))), 'EXTMAX', tuple(round(v) for v in h.get('$EXTMAX', (0, 0, 0))))
msp = doc.modelspace(); ents = list(msp)
print('model-space entities', len(ents), '| layers', len(doc.layers), '| blocks', len(doc.blocks))
xr = [b.name for b in doc.blocks if b.block and (b.block.is_xref or b.block.is_xref_overlay)]
print('xref blocks:', xr[:20])
by = collections.defaultdict(collections.Counter)
for e in ents: by[e.dxf.get('layer', '0')][e.dxftype()] += 1
print('\nlayers (model space, top 60):')
for lay, c in sorted(by.items(), key=lambda kv: -sum(kv[1].values()))[:60]:
    print(f'  {lay:45} {sum(c.values()):6}  ' + ', '.join(f'{t}:{n}' for t, n in c.most_common(5)))
ins = collections.Counter((e.dxf.layer, e.dxf.name) for e in msp.query('INSERT'))
print('\ninserts (layer, block): top 50'); [print('  ', k, n) for k, n in ins.most_common(50)]
txt = [(e.dxf.layer, (e.dxf.text if e.dxftype() == 'TEXT' else e.plain_text()).replace('\n', ' ')[:50]) for e in msp.query('TEXT MTEXT')]
tl = collections.Counter(l for l, _ in txt)
print('\ntexts', len(txt), 'by layer', tl.most_common(12))
print('sample:', [t for _, t in txt[:80]])
try:
    b = bbox.extents(ents, fast=True); print('\nmodel-space bbox', [round(v) for v in (b.extmin.x, b.extmin.y, b.extmax.x, b.extmax.y)])
except Exception as ex: print('bbox failed', ex)
print('layouts', [(l.name, len(l)) for l in doc.layouts])
