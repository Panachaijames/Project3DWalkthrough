"""Every furniture piece of the bank model with its block insert read back from the DXF by its handle (3 Nov 2026).

    python -B dxf_pieces.py <L1.dxf> <L2.dxf> <bank_model.json> <out folder>

Writes <out>/dxf_pieces.json: per piece the model's box (drawing coordinates, metres, = Max coordinates of the bank script) and
the INSERT: block name, insertion point (m), rotation (degrees), x / y / z scale, extrusion, mirrored or not, the block's
own drawn geometry in its own frame (bounding box and minimum rotated rectangle, m), and the box's centre and turn seen
from the block's frame. And <out>/dxf_geometry.pkl: the drawn primitives of every furniture piece in drawing coordinates
(m), for the pictures. The DXFs are LibreDWG 0.14 conversions of I1201 / I1202 in a temp folder (units mm).
"""
import json
import math
import pickle
import sys
from pathlib import Path

import ezdxf
from ezdxf import disassemble
from ezdxf.math import Matrix44
from shapely.geometry import MultiPoint

sys.stdout.reconfigure(encoding='utf-8')
MM = 0.001


def prim_points(entities, flatten=0.5):
    """Drawn primitives of entities (nested inserts unpacked) -> list of point lists (drawing units)."""
    out = []
    for prim in disassemble.to_primitives(disassemble.recursive_decompose(entities)):
        try:
            pts = [(v.x, v.y) for v in prim.vertices()]
        except Exception:
            continue
        if pts:
            out.append(pts)
    return out


def min_rect(points):
    hull = MultiPoint(sorted({(round(x, 6), round(y, 6)) for x, y in points})).convex_hull
    if hull.geom_type != 'Polygon':
        return None
    c = list(hull.minimum_rotated_rectangle.exterior.coords)[:4]
    e1, e2 = math.dist(c[0], c[1]), math.dist(c[1], c[2])
    a, b, w, d = (c[0], c[1], e1, e2) if e1 >= e2 else (c[1], c[2], e2, e1)
    rot = math.degrees(math.atan2(b[1] - a[1], b[0] - a[0])) % 180
    if w - d < 0.001:
        rot %= 90
    return {'x': (c[0][0] + c[2][0]) / 2, 'y': (c[0][1] + c[2][1]) / 2, 'w': w, 'd': d, 'rot': rot}


def main(l1, l2, model_path, out):
    out = Path(out)
    model = json.loads(Path(model_path).read_text(encoding='utf-8'))
    ox, oy = model['offset']
    docs = {'L1': ezdxf.readfile(l1), 'L2': ezdxf.readfile(l2)}
    block_cache = {}
    rows, geometry = [], {}
    for p in model['furniture']:
        doc = docs[p['floor']]
        rec = {'id': p['id'], 'floor': p['floor'], 'kind': p['kind'], 'family': p['family'], 'block': p['block'],
               'handle': p['handle'], 'box': {'x': round(p['x'] + ox, 4), 'y': round(p['y'] + oy, 4), 'w': p['w'], 'd': p['d'],
                                              'rot': p['rot']}, 'on': p['on'], 'n': p.get('n', 1), 'note': p.get('note', '')}
        e = doc.entitydb.get(p['handle']) if p['handle'] else None
        if e is None or e.dxftype() != 'INSERT':
            rec['insert'] = None
            rows.append(rec)
            continue
        d = e.dxf
        sx, sy, sz = d.xscale, d.yscale, d.zscale
        ext = tuple(round(v, 9) for v in d.extrusion)
        mirrored = (sx * sy * sz < 0) != (ext[2] < 0)
        ins = {'name': d.name, 'layer': d.layer, 'x': round(d.insert[0] * MM, 5), 'y': round(d.insert[1] * MM, 5),
               'z': round(d.insert[2] * MM, 5), 'rotation': round(d.rotation % 360, 4), 'xscale': sx, 'yscale': sy, 'zscale': sz,
               'extrusion': list(ext), 'mirrored': mirrored, 'blockNameMatches': d.name == p['block'],
               'inModelSpace': e.dxf.owner == doc.modelspace().block_record_handle}
        # the block's own drawing, in its own frame (before the insert's scale, turn and move)
        if d.name not in block_cache:
            blk = doc.blocks.get(d.name)
            pts = [q for pl in prim_points(list(blk)) for q in pl]
            base = blk.block.dxf.base_point
            local = [((x - base[0]) * MM, (y - base[1]) * MM) for x, y in pts]
            xs, ys = [q[0] for q in local], [q[1] for q in local]
            block_cache[d.name] = {'points': len(local), 'bbox': [round(min(xs), 4), round(min(ys), 4), round(max(xs), 4), round(max(ys), 4)] if local else None,
                                   'minRect': {k: round(v, 4) for k, v in (min_rect(local) or {}).items()} or None}
        ins['blockLocal'] = block_cache[d.name]
        # the box seen from the block's frame: its centre in block coordinates and its turn minus the insert's turn
        m = e.matrix44()
        inv = m.copy()
        inv.inverse()
        cx, cy, _ = inv.transform((rec['box']['x'] / MM, rec['box']['y'] / MM, 0))
        ins['boxCentreInBlock'] = [round(cx * MM / abs(sx), 4), round(cy * MM / abs(sy), 4)]
        ins['boxRotMinusInsertRotation'] = round((p['rot'] - d.rotation) % 360, 3)
        rec['insert'] = ins
        # the drawn geometry of the piece in drawing coordinates (m), for the pictures
        geometry[p['id']] = [[(x * MM, y * MM) for x, y in pl] for pl in prim_points([e])]
        rows.append(rec)
    # the other entities on the furniture layers near the models, for the pictures: everything in model space on those layers
    furn_layers = {'I-FURN', 'Q-CASE', 'Q-CASE-HDLN', 'Q-SPCQ', 'P-SANR-FIXT', 'L-PLNT', 'E-COMM', 'A-GENM'}
    context = {}
    for fl, doc in docs.items():
        ctx = []
        for e in doc.modelspace():
            if e.dxf.layer in furn_layers or e.dxf.layer.startswith('A-WALL') or e.dxf.layer in ('A-DOOR', 'A-GLAZ-CURT', 'S-COLS'):
                for pl in prim_points([e]):
                    ctx.append((e.dxf.layer, e.dxftype(), e.dxf.handle, [(x * MM, y * MM) for x, y in pl]))
        context[fl] = ctx
    with open(out / 'dxf_geometry.pkl', 'wb') as fh:
        pickle.dump({'pieces': geometry, 'context': context}, fh)
    (out / 'dxf_pieces.json').write_text(json.dumps(rows, indent=1, ensure_ascii=False), encoding='utf-8')
    n_ins = sum(1 for r in rows if r['insert'])
    print(f'{len(rows)} pieces, {n_ins} with their INSERT read back, {sum(1 for r in rows if r["insert"] and r["insert"]["mirrored"])} mirrored, '
          f'{sum(1 for r in rows if r["insert"] and not r["insert"]["blockNameMatches"])} block name mismatches, '
          f'{sum(1 for r in rows if r["insert"] and not r["insert"]["inModelSpace"])} not in model space')


if __name__ == '__main__':
    main(*sys.argv[1:5])
