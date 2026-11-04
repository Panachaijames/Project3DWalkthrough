"""Read plan.dxf (LibreDWG's conversion of 'layout presidential test.dwg') into a flat list of entities, in metres.

Every model-space entity is flattened to points (curves at 10 mm, 25 mm inside blocks); blocks are unpacked with their
transforms, and layer 0 inside a block takes the INSERT's layer. HATCH fills keep their boundary loops; TEXT/MTEXT keep
their insert point and text. The result is cached next to the DXF (plan_entities.pkl) and re-read when the DXF changes.
Each entity: {t, lay, depth, blk, h, pts | loops | text+ins, closed?, solid?}  (h = handle, or the top-level INSERT's).
"""
import os, pickle, time
from ezdxf import recover, path as ezpath

SKIP = ('POINT', 'ATTDEF', 'WIPEOUT', 'IMAGE', 'VIEWPORT', 'OLE2FRAME', '3DSOLID', 'REGION', 'BODY', 'MESH')


def _flatten(dxf_path):
    doc, _ = recover.readfile(dxf_path)
    ents = []

    def walk(e, inh=None, depth=0, blk=None, h=None):
        lay = e.dxf.get('layer', '0')
        if lay == '0' and inh: lay = inh
        t = e.dxftype()
        if t in ('INSERT', 'DIMENSION') and depth < 7:
            nm = e.dxf.get('name', '') if t == 'INSERT' else '*DIM'
            try:
                for v in e.virtual_entities(): walk(v, lay, depth + 1, blk or nm, h or e.dxf.handle)
            except Exception:
                pass
            return
        d = {'t': t, 'lay': lay, 'depth': depth, 'blk': blk, 'h': h or e.dxf.get('handle')}
        if t in ('TEXT', 'MTEXT', 'ATTRIB'):
            try:
                p = e.dxf.insert
                s = (e.plain_text() if t == 'MTEXT' else e.dxf.get('text', '')).strip()
                ents.append({**d, 'ins': [p.x / 1000, p.y / 1000], 'text': s})
            except Exception:
                pass
            return
        if t == 'HATCH':
            try:
                loops = [[[v.x / 1000, v.y / 1000] for v in bp.flattening(distance=10)] for bp in ezpath.from_hatch(e)]
                ents.append({**d, 'loops': loops, 'solid': bool(e.dxf.get('solid_fill', 0)), 'pattern': e.dxf.get('pattern_name', '')})
            except Exception:
                pass
            return
        if t in SKIP: return
        try:
            pts = [[v.x / 1000, v.y / 1000] for v in ezpath.make_path(e).flattening(distance=10 if depth == 0 else 25)]
        except Exception:
            return
        if not pts: return
        closed = False
        try:
            closed = bool(e.closed) if t == 'LWPOLYLINE' else (t == 'CIRCLE' or (t == 'POLYLINE' and e.is_closed))
        except Exception:
            pass
        ents.append({**d, 'pts': pts, 'closed': closed})

    for e in doc.modelspace(): walk(e)
    return ents, len(doc.layers)


def read(dxf_path):
    """-> (entities, number of layers in the drawing). Cached in plan_entities.pkl beside the DXF."""
    cache = os.path.join(os.path.dirname(os.path.abspath(dxf_path)), 'plan_entities.pkl')
    if os.path.exists(cache) and os.path.getmtime(cache) >= os.path.getmtime(dxf_path):
        with open(cache, 'rb') as f:
            return pickle.load(f)
    t0 = time.time()
    out = _flatten(dxf_path)
    with open(cache, 'wb') as f:
        pickle.dump(out, f)
    print(f'read {dxf_path}: {len(out[0])} entities in {time.time() - t0:.0f} s (cached in {cache})')
    return out
