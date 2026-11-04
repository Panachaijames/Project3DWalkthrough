"""Geometry spot check: every LINE, ARC, CIRCLE, INSERT, MTEXT/TEXT, LWPOLYLINE, HATCH of the DWG (dwgread JSON) against the DXF.
Usage: python geom_check.py <dwgread.json> <plan.dxf>"""
import collections, json, math, sys
from ezdxf import recover
d = json.load(open(sys.argv[1], encoding='utf-8', errors='replace'))
O = {o['handle'][-1]: o for o in d['OBJECTS'] if 'entity' in o}
bh = {o['handle'][-1]: o['name'] for o in d['OBJECTS'] if o.get('object') == 'BLOCK_HEADER'}
doc, _ = recover.readfile(sys.argv[2])
X = {int(e.dxf.handle, 16): e for blk in doc.blocks for e in blk}
for e in list(X.values()):
    if e.dxftype() == 'INSERT':
        for a in e.attribs: X[int(a.dxf.handle, 16)] = a
def close(a, b, tol=1e-6): return all(abs(x - y) <= tol * max(1.0, abs(x)) for x, y in zip(a, b))
bad, n = collections.Counter(), collections.Counter()
ex = []
for h, o in O.items():
    t = o['entity']; e = X.get(h)
    if e is None: continue
    ok = True
    if t == 'LINE': ok = close(o['start'][:2], tuple(e.dxf.start)[:2]) and close(o['end'][:2], tuple(e.dxf.end)[:2])
    elif t in ('ARC', 'CIRCLE'):
        ok = close(o['center'][:2], tuple(e.dxf.center)[:2]) and close([o['radius']], [e.dxf.radius])
        if t == 'ARC': ok = ok and abs(math.degrees(o['start_angle']) - e.dxf.start_angle) % 360 < 1e-4 and abs(math.degrees(o['end_angle']) - e.dxf.end_angle) % 360 < 1e-4
    elif t == 'INSERT':
        ok = close(o['ins_pt'][:2], tuple(e.dxf.insert)[:2]) and abs(math.degrees(o['rotation']) - e.dxf.rotation) % 360 < 1e-6 \
            and close(o['scale'], [e.dxf.xscale, e.dxf.yscale, e.dxf.zscale]) and bh.get(o['block_header'][-1], '?').upper() == e.dxf.name.upper()
    elif t == 'MTEXT': ok = o['text'] == e.text
    elif t in ('TEXT', 'ATTRIB'): ok = o.get('text_value', o.get('text')) == e.dxf.text
    elif t == 'LWPOLYLINE': ok = len(o['points']) == len(e) and close([c for p in o['points'] for c in p], [c for p in e.get_points('xy') for c in p])
    elif t == 'HATCH': ok = len(o.get('paths', [])) == len(e.paths) and o.get('is_solid_fill') == e.dxf.solid_fill
    else: continue
    n[t] += 1
    if not ok: bad[t] += 1; ex.append((t, hex(h)))
print('checked', dict(n)); print('differing', dict(bad), ex[:10])
