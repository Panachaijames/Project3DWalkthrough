"""Read the 3D team's banquet/*.glb files without running anything in them (3 Nov 2026).

    python -I -B glb_read.py <banquet folder> <out folder>

Writes <out>/glb_facts.json (per model: header, parts, triangles, vertices, materials, attributes, spare bytes per vertex and
what they hold, root node transforms in glTF and in 3ds Max terms, world bounding box in glTF and Max coordinates) and
<out>/<model>.npz (world vertices in Max coordinates, metres, Z up, and the triangle indices, per part) for the next steps.
glTF is Y-up: Max x = glTF x, Max y = -glTF z, Max z = glTF y.
"""
import json
import math
import struct
import sys
from pathlib import Path

import numpy as np

sys.stdout.reconfigure(encoding='utf-8')
COMP = {5120: np.int8, 5121: np.uint8, 5122: np.int16, 5123: np.uint16, 5125: np.uint32, 5126: np.float32}
NCOMP = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT2': 4, 'MAT3': 9, 'MAT4': 16}
C = np.array([[1.0, 0, 0], [0, 0, 1.0], [0, -1.0, 0]])      # Max (Z up) -> glTF (Y up): (x, y, z) -> (x, z, -y)


def read_glb(path):
    data = Path(path).read_bytes()
    magic, version, length = struct.unpack_from('<III', data, 0)
    assert magic == 0x46546C67, 'not a GLB'
    off, gltf, binc, chunks = 12, None, b'', []
    while off < length:
        clen, ctype = struct.unpack_from('<II', data, off)
        chunk = data[off + 8: off + 8 + clen]
        chunks.append({'type': {0x4E4F534A: 'JSON', 0x004E4942: 'BIN'}.get(ctype, hex(ctype)), 'bytes': clen})
        if ctype == 0x4E4F534A:
            gltf = json.loads(chunk.decode('utf-8'))
        elif ctype == 0x004E4942:
            binc = chunk
        off += 8 + clen
    return {'version': version, 'length': length, 'fileBytes': len(data), 'chunks': chunks}, gltf, binc


def accessor(g, binc, i):
    a = g['accessors'][i]
    bv = g['bufferViews'][a['bufferView']]
    dt = np.dtype(COMP[a['componentType']]).newbyteorder('<')
    n = NCOMP[a['type']]
    start = bv.get('byteOffset', 0) + a.get('byteOffset', 0)
    stride = bv.get('byteStride', dt.itemsize * n)
    arr = np.ndarray(shape=(a['count'], n), dtype=dt, buffer=binc, offset=start, strides=(stride, dt.itemsize))
    return np.array(arr, dtype=np.float64 if dt.kind == 'f' else np.int64)


def node_matrix(node):
    if 'matrix' in node:
        return np.array(node['matrix'], dtype=float).reshape(4, 4).T          # glTF stores column-major
    t = np.array(node.get('translation', [0, 0, 0]), dtype=float)
    x, y, z, w = node.get('rotation', [0, 0, 0, 1])
    r = np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                  [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                  [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])
    s = np.array(node.get('scale', [1, 1, 1]), dtype=float)
    m = np.eye(4)
    m[:3, :3] = r * s
    m[:3, 3] = t
    return m


def decompose(m):
    """4x4 -> translation, scale (per axis, signed so that the rotation is proper), rotation matrix, quaternion (x, y, z, w)."""
    t = m[:3, 3].copy()
    lin = m[:3, :3]
    s = np.linalg.norm(lin, axis=0)
    r = lin / s
    if np.linalg.det(r) < 0:                     # a mirror: put it on the first axis' scale
        s[0] = -s[0]
        r[:, 0] = -r[:, 0]
    tr = np.trace(r)
    if tr > 0:
        q = 0.5 / math.sqrt(tr + 1.0)
        w, x, y, z = 0.25 / q, (r[2, 1] - r[1, 2]) * q, (r[0, 2] - r[2, 0]) * q, (r[1, 0] - r[0, 1]) * q
    else:
        i = int(np.argmax(np.diag(r)))
        j, k = (i + 1) % 3, (i + 2) % 3
        sq = math.sqrt(max(1.0 + r[i, i] - r[j, j] - r[k, k], 0.0)) * 2
        qv = [0.0, 0.0, 0.0]
        qv[i] = 0.25 * sq
        qv[j] = (r[j, i] + r[i, j]) / sq
        qv[k] = (r[k, i] + r[i, k]) / sq
        w = (r[k, j] - r[j, k]) / sq
        x, y, z = qv
    return t, s, r, [x, y, z, w]


def euler_xyz_deg(r):
    """Euler angles (degrees) for R = Rz(c) * Ry(b) * Rx(a), the order 3ds Max shows as XYZ."""
    b = math.asin(max(-1.0, min(1.0, -r[2, 0])))
    if abs(math.cos(b)) > 1e-6:
        a = math.atan2(r[2, 1], r[2, 2])
        c = math.atan2(r[1, 0], r[0, 0])
    else:
        a = math.atan2(-r[1, 2], r[1, 1])
        c = 0.0
    return [round(math.degrees(v), 3) + 0.0 for v in (a, b, c)]


def clean(v, nd=6):
    if isinstance(v, (list, tuple, np.ndarray)):
        return [clean(x, nd) for x in v]
    v = float(v)
    return 0.0 if abs(v) < 10 ** -nd else round(v, nd)


def spare_bytes(g, binc, prims):
    """Bytes in the interleaved vertex buffer views that no accessor declares. -> per buffer view: stride, declared byte ranges
    inside a vertex, the spare ranges, and what the spare bytes hold (read as float32)."""
    out = []
    used = {}
    for p in prims:
        for name, ai in p['attributes'].items():
            a = g['accessors'][ai]
            bvi = a['bufferView']
            bv = g['bufferViews'][bvi]
            stride = bv.get('byteStride')
            if not stride:
                continue
            dt = np.dtype(COMP[a['componentType']])
            within = a.get('byteOffset', 0) % stride
            used.setdefault(bvi, {'stride': stride, 'ranges': set(), 'blocks': set()})
            used[bvi]['ranges'].add((within, within + dt.itemsize * NCOMP[a['type']], name))
            used[bvi]['blocks'].add((a.get('byteOffset', 0) - within, a['count']))
    for bvi, u in sorted(used.items()):
        bv = g['bufferViews'][bvi]
        stride = u['stride']
        covered = np.zeros(stride, bool)
        for lo, hi, _ in u['ranges']:
            covered[lo:hi] = True
        spare = [i for i in range(stride) if not covered[i]]
        rec = {'bufferView': bvi, 'byteStride': stride, 'declared': sorted([[lo, hi, n] for lo, hi, n in u['ranges']]),
               'spareBytesPerVertex': len(spare), 'vertices': int(sum(c for _, c in u['blocks']))}
        if spare:
            lo, hi = min(spare), max(spare) + 1
            rec['spareRange'] = [lo, hi]
            vals = []
            for start, count in sorted(u['blocks']):
                base = bv.get('byteOffset', 0) + start
                arr = np.ndarray(shape=(count, (hi - lo) // 4), dtype='<f4', buffer=binc, offset=base + lo, strides=(stride, 4))
                vals.append(np.array(arr, dtype=np.float64))
            v = np.vstack(vals)
            raw = np.vstack([np.ndarray(shape=(c, hi - lo), dtype=np.uint8, buffer=binc, offset=bv.get('byteOffset', 0) + s + lo,
                                        strides=(stride, 1)) for s, c in sorted(u['blocks'])])
            fin = np.isfinite(v)
            rec['spareAsFloat32'] = {
                'allZeroBytes': bool((raw == 0).all()),
                'finiteShare': round(float(fin.mean()), 4),
                'perComponent': [{'min': clean(np.nanmin(np.where(fin[:, k], v[:, k], np.nan)), 5) if fin[:, k].any() else None,
                                  'max': clean(np.nanmax(np.where(fin[:, k], v[:, k], np.nan)), 5) if fin[:, k].any() else None,
                                  'distinct': int(len(np.unique(v[fin[:, k], k]))),
                                  'shareIn0to1': round(float(((v[:, k] >= -0.001) & (v[:, k] <= 1.001)).mean()), 4)}
                                 for k in range(v.shape[1])],
            }
            rec['spareBytes'] = int(len(spare) * rec['vertices'])
        out.append(rec)
    return out


def main(src, dst):
    src, dst = Path(src), Path(dst)
    dst.mkdir(parents=True, exist_ok=True)
    facts = {}
    for path in sorted(src.glob('*.glb')):
        head, g, binc = read_glb(path)
        model = path.stem
        scene = g['scenes'][g.get('scene', 0)]
        world, parent_of = {}, {}

        def walk(ni, parent):
            m = parent @ node_matrix(g['nodes'][ni])
            world[ni] = m
            for c in g['nodes'][ni].get('children', []):
                parent_of[c] = ni
                walk(c, m)

        for ni in scene['nodes']:
            walk(ni, np.eye(4))
        parts, prims_all, npz = [], [], {}
        lo_g, hi_g = np.full(3, np.inf), np.full(3, -np.inf)
        all_max = []
        for ni in sorted(world):
            node = g['nodes'][ni]
            if 'mesh' not in node:
                continue
            mesh = g['meshes'][node['mesh']]
            root = ni
            while root in parent_of:
                root = parent_of[root]
            for pi, p in enumerate(mesh['primitives']):
                prims_all.append(p)
                pos = accessor(g, binc, p['attributes']['POSITION'])
                idx = accessor(g, binc, p['indices']).ravel() if 'indices' in p else np.arange(len(pos))
                mode = p.get('mode', 4)
                tris = len(idx) // 3 if mode == 4 else 0
                wp = (world[ni] @ np.c_[pos, np.ones(len(pos))].T).T[:, :3]          # glTF world, metres
                mx = np.c_[wp[:, 0], -wp[:, 2], wp[:, 1]]                            # Max world, metres, Z up
                all_max.append(mx)
                lo_g, hi_g = np.minimum(lo_g, wp.min(0)), np.maximum(hi_g, wp.max(0))
                key = f'p{len(parts)}'
                npz[key + '_v'] = mx
                npz[key + '_i'] = idx.reshape(-1, 3) if mode == 4 else idx
                acc = g['accessors'][p['attributes']['POSITION']]
                nrm = accessor(g, binc, p['attributes']['NORMAL']) if 'NORMAL' in p['attributes'] else None
                parts.append({
                    'node': ni, 'rootNode': root, 'name': node.get('name') or mesh.get('name'), 'mesh': mesh.get('name'),
                    'primitive': pi, 'mode': mode, 'triangles': int(tris), 'vertices': int(len(pos)),
                    'indices': int(len(idx)), 'indexType': {5121: 'uint8', 5123: 'uint16', 5125: 'uint32'}.get(
                        g['accessors'][p['indices']]['componentType']) if 'indices' in p else None,
                    'attributes': sorted(p['attributes']), 'material': p.get('material'),
                    'localMinMax': [clean(acc.get('min'), 4), clean(acc.get('max'), 4)],
                    'normalsUnitLength': None if nrm is None else [round(float(np.linalg.norm(nrm, axis=1).min()), 4),
                                                                   round(float(np.linalg.norm(nrm, axis=1).max()), 4)],
                    'maxBox': {'min': clean(mx.min(0), 4), 'max': clean(mx.max(0), 4)},
                    'degenerateTriangles': int(((idx.reshape(-1, 3)[:, 0] == idx.reshape(-1, 3)[:, 1]) |
                                                (idx.reshape(-1, 3)[:, 1] == idx.reshape(-1, 3)[:, 2]) |
                                                (idx.reshape(-1, 3)[:, 0] == idx.reshape(-1, 3)[:, 2])).sum()) if mode == 4 else None,
                })
        np.savez_compressed(dst / f'{model}.npz', **npz)
        allm = np.vstack(all_max)
        roots = []
        for ni in scene['nodes']:
            n = g['nodes'][ni]
            m = node_matrix(n)
            t, s, r, q = decompose(m)
            # the same node in 3ds Max terms: the exporter wrote C * M_max (its children hold the mesh in the node's own frame)
            mmax = np.eye(4)
            mmax[:3, :3] = C.T @ m[:3, :3]
            mmax[:3, 3] = C.T @ m[:3, 3]
            tm, sm, rm, qm = decompose(mmax)
            kids = []
            for c in n.get('children', []):
                cn = g['nodes'][c]
                ct, cs, cr, cq = decompose(node_matrix(cn))
                kids.append({'node': c, 'name': cn.get('name'), 'mesh': cn.get('mesh'), 'scale': clean(cs, 6),
                             'rotationIsIdentity': bool(np.allclose(cr, np.eye(3), atol=1e-6)), 'translation': clean(ct, 6)})
            roots.append({
                'node': ni, 'name': n.get('name'), 'gltfMatrixColumnMajor': clean(n.get('matrix', []), 9) or None,
                'gltf': {'translation': clean(t, 5), 'scale': clean(s, 6), 'rotationQuaternionXYZW': clean(q, 6)},
                'max': {'position': clean(tm, 4), 'scale': clean(sm, 6), 'rotationEulerXYZdeg': euler_xyz_deg(rm),
                        'rotationQuaternionXYZW': clean(qm, 6), 'rotationMatrixRows': clean(rm, 6),
                        'turnAboutZdeg': round(math.degrees(math.atan2(rm[1, 0], rm[0, 0])), 3),
                        'localZisUp': bool(abs(rm[2, 2] - 1) < 1e-4)},
                'children': kids,
            })
        mats = []
        for i, m in enumerate(g.get('materials', [])):
            pbr = m.get('pbrMetallicRoughness', {})
            mats.append({'index': i, 'name': m.get('name'), 'baseColorFactor': pbr.get('baseColorFactor'),
                         'metallicFactor': pbr.get('metallicFactor'), 'roughnessFactor': pbr.get('roughnessFactor'),
                         'textures': sorted(k for k, v in list(pbr.items()) + list(m.items()) if isinstance(v, dict) and 'index' in v),
                         'alphaMode': m.get('alphaMode', 'OPAQUE'), 'doubleSided': m.get('doubleSided', False),
                         'extensions': sorted(m.get('extensions', {}))})
        sp = spare_bytes(g, binc, prims_all)
        facts[model] = {
            'file': path.name, 'fileBytes': head['fileBytes'], 'glbVersion': head['version'], 'chunks': head['chunks'],
            'gltfVersion': g.get('asset', {}).get('version'), 'generator': g.get('asset', {}).get('generator'),
            'copyright': g.get('asset', {}).get('copyright'), 'extensionsUsed': g.get('extensionsUsed', []),
            'extensionsRequired': g.get('extensionsRequired', []),
            'counts': {k: len(g.get(k, [])) for k in ('nodes', 'meshes', 'accessors', 'bufferViews', 'buffers', 'materials',
                                                      'textures', 'images', 'samplers', 'animations', 'skins', 'cameras')},
            'triangles': int(sum(p['triangles'] for p in parts)), 'vertices': int(sum(p['vertices'] for p in parts)),
            'parts': parts, 'materials': mats,
            'attributesUsed': sorted({a for p in parts for a in p['attributes']}),
            'texcoordsDeclared': any(a.startswith('TEXCOORD') for p in parts for a in p['attributes']),
            'interleavedBufferViews': sp,
            'rootNodes': roots,
            'worldBox': {'gltfYup': {'min': clean(lo_g, 4), 'max': clean(hi_g, 4)},
                         'maxZup': {'min': clean(allm.min(0), 4), 'max': clean(allm.max(0), 4),
                                    'centre': clean((allm.min(0) + allm.max(0)) / 2, 4), 'size': clean(allm.max(0) - allm.min(0), 4)}},
        }
        f = facts[model]
        print(f"{model:16s} {f['triangles']:>8,} tris {f['vertices']:>8,} verts parts {len(parts)} mats {len(mats)} "
              f"size {f['worldBox']['maxZup']['size']} centre {f['worldBox']['maxZup']['centre']} "
              f"spare {[(s['byteStride'], s['spareBytesPerVertex']) for s in sp]}")
    (dst / 'glb_facts.json').write_text(json.dumps(facts, indent=1, ensure_ascii=False), encoding='utf-8')


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
