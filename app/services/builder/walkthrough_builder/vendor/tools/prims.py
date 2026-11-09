"""Flatten a plan DXF into a cached list of primitives AND block inserts, in drawing metres (DXF mm / 1000).

Like presidential_test/src/read_dxf.py, but it also keeps every INSERT met at any depth (name, full block path,
insert point, rotation, scale signs, in world coordinates) and every ATTRIB, because door and window blocks are often
nested (the Sukhumvit upper floor is one bound xref block).

Each item: {t, lay, depth, path, h, area}
  t = entity type; lay = effective layer (layer 0 inside a block takes the INSERT's layer); depth = nesting depth;
  path = block names from the top-level INSERT down ('' at top level); h = the top-level entity's DXF handle;
  area = 'ground' | 'upper' (Sukhumvit plan regions) | 'suite' (presidential) | None (outside the plans)
  primitives: pts [[x, y], ...] (curves flattened at 10 mm), closed; HATCH: loops, solid; TEXT/MTEXT/ATTRIB: ins, text
  INSERT: name, ins [x, y], rot (deg), sx, sy (world scale factors incl. sign; sx*sy < 0 = mirrored)
  (bank1 / bank2: the bank branch's Level 1 / Level 2 files, one floor each: area 'L1' / 'L2' for every model-space item)
Usage: python prims.py sukhumvit|presidential|bank1|bank2      -> <data folder>/<name>/prims.pkl  (read back with load(name))
Any other name is read as one plan per file: every item gets the area tag <name> (like bank1 / bank2, which are 'L1' / 'L2').
The data folder holds one folder per drawing with its plan.dxf (made from the DWG with LibreDWG's dwg2dxf: see
cad_test/src/README.md); it is the folder above tools/ (detector/) unless OPENINGS_DATA names another. The Sukhumvit
folder also needs regions.json (where the two plans sit on the sheet).
"""
import json, math, os, pickle, sys, time
from pathlib import Path
from ezdxf import recover, path as ezpath

ROOT = Path(__file__).resolve().parent.parent          # the detector folder
DATA = Path(os.environ['OPENINGS_DATA']) if os.environ.get('OPENINGS_DATA') else ROOT     # <name>/plan.dxf, <name>/prims.pkl
SKIP = ('POINT', 'ATTDEF', 'WIPEOUT', 'IMAGE', 'VIEWPORT', 'OLE2FRAME', '3DSOLID', 'REGION', 'BODY', 'MESH')


def _areas(name):
    """-> function(points in m) -> area tag."""
    if name == 'sukhumvit':
        R = json.loads((DATA / 'sukhumvit' / 'regions.json').read_text())
        regs = {'ground': [v / 1000 for v in R['plan_left']], 'upper': [v / 1000 for v in R['plan_right']]}
        def area(pts, pad=0.5):
            for k, r in regs.items():
                if all(r[0] - pad <= x <= r[2] + pad and r[1] - pad <= y <= r[3] + pad for x, y in pts): return k
            return None
        return area
    # presidential: the suite = the wall layer's cluster (y < -3450 m) plus 2 m, as in build_model.py
    return None


def _flatten(dxf_path):
    doc, _ = recover.readfile(dxf_path)
    items = []

    def walk(e, inh=None, depth=0, path=(), h=None):
        lay = e.dxf.get('layer', '0')
        if lay == '0' and inh: lay = inh
        t = e.dxftype()
        top_h = h or e.dxf.get('handle')
        base = {'t': t, 'lay': lay, 'depth': depth, 'path': '>'.join(path), 'h': top_h}
        if t == 'INSERT':
            nm = e.dxf.get('name', '')
            try:
                p = e.dxf.insert
                m = e.matrix44()
                ux, uy = m.transform_direction((1, 0, 0)), m.transform_direction((0, 1, 0))
                sx, sy = math.hypot(ux.x, ux.y), math.hypot(uy.x, uy.y)
                if ux.x * uy.y - ux.y * uy.x < 0: sy = -sy                     # mirrored
                rot = math.degrees(math.atan2(ux.y, ux.x))
                items.append({**base, 'name': nm, 'ins': [p.x / 1000, p.y / 1000], 'rot': round(rot, 3),
                              'sx': round(sx, 4), 'sy': round(sy, 4)})
            except Exception:
                pass
            try:
                for a in e.attribs:
                    ip = a.dxf.insert
                    items.append({**base, 't': 'ATTRIB', 'lay': a.dxf.get('layer', lay), 'ins': [ip.x / 1000, ip.y / 1000],
                                  'text': a.dxf.get('text', ''), 'tag': a.dxf.get('tag', ''), 'block': nm})
            except Exception:
                pass
            if depth < 8:
                try:
                    for v in e.virtual_entities(): walk(v, lay, depth + 1, path + (nm,), top_h)
                except Exception:
                    pass
            return
        if t == 'DIMENSION':
            return                                                   # dimensions: not needed for openings
        if t in ('TEXT', 'MTEXT', 'ATTRIB'):
            try:
                p = e.dxf.insert
                s = (e.plain_text() if t == 'MTEXT' else e.dxf.get('text', '')).strip()
                items.append({**base, 'ins': [p.x / 1000, p.y / 1000], 'text': s})
            except Exception:
                pass
            return
        if t == 'HATCH':
            try:
                loops = [[[v.x / 1000, v.y / 1000] for v in bp.flattening(distance=10)] for bp in ezpath.from_hatch(e)]
                items.append({**base, 'loops': loops, 'solid': bool(e.dxf.get('solid_fill', 0)), 'pattern': e.dxf.get('pattern_name', '')})
            except Exception:
                pass
            return
        if t in SKIP: return
        try:
            pts = [[v.x / 1000, v.y / 1000] for v in ezpath.make_path(e).flattening(distance=10)]
        except Exception:
            return
        if not pts: return
        closed = False
        try:
            closed = bool(e.closed) if t == 'LWPOLYLINE' else (t == 'CIRCLE' or (t == 'POLYLINE' and e.is_closed))
        except Exception:
            pass
        items.append({**base, 'pts': pts, 'closed': closed, 'lt': e.dxf.get('linetype', 'BYLAYER')})

    for e in doc.modelspace(): walk(e)
    layers = {l.dxf.name: l.dxf.get('linetype', 'Continuous') for l in doc.layers}
    return items, layers


def _pts(d):
    return d.get('pts') or [q for l in d.get('loops', []) for q in l] or ([d['ins']] if 'ins' in d else [])


def build(name):
    t0 = time.time()
    items, layers = _flatten(str(DATA / name / 'plan.dxf'))
    if name == 'sukhumvit':
        area = _areas(name)
        for d in items: d['area'] = area(_pts(d)) if _pts(d) else None
    elif name in ('bank1', 'bank2'):
        tag = 'L1' if name == 'bank1' else 'L2'
        for d in items: d['area'] = tag if _pts(d) else None
    elif name != 'presidential':
        for d in items: d['area'] = name if _pts(d) else None    # any other drawing is one plan per file: its items are tagged with the drawing's name
    else:
        W = [p for d in items if d['lay'] == 'A-1.Netcat - tuong' for p in _pts(d) if p[1] < -3450]
        R = (min(p[0] for p in W) - 2, min(p[1] for p in W) - 2, max(p[0] for p in W) + 2, max(p[1] for p in W) + 2)
        for d in items:
            P = _pts(d)
            d['area'] = 'suite' if P and any(R[0] <= x <= R[2] and R[1] <= y <= R[3] for x, y in P) else None
        layers['__suite_bbox__'] = R
    out = {'items': items, 'layers': layers}
    with open(DATA / name / 'prims.pkl', 'wb') as f: pickle.dump(out, f)
    n_in = sum(1 for d in items if d['area'])
    print(f'{name}: {len(items)} items ({n_in} inside the plans) in {time.time() - t0:.0f} s -> {DATA / name / "prims.pkl"}')


def load(name):
    with open(DATA / name / 'prims.pkl', 'rb') as f: return pickle.load(f)


if __name__ == '__main__':
    build(sys.argv[1])
