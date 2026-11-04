# Independent re-derivation of model -> piece matches, from the GLB files and bank_model.json only.
# Written from scratch (does not reuse the analysis scripts). Usage: python rederive.py <project folder>
import json, struct, sys, math
import numpy as np

PROJECT = sys.argv[1]
GLB_DIR = PROJECT + '/banquet'
bank = json.load(open(PROJECT + '/bank_test/src/bank_model.json', encoding='utf-8'))
OX, OY = bank['offset']
LEVEL = {f['key']: f['level'] for f in bank['floors']}

COMP = {5120: np.int8, 5121: np.uint8, 5122: np.int16, 5123: np.uint16, 5125: np.uint32, 5126: np.float32}
NCOMP = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT4': 16}


def read_glb(path):
    b = open(path, 'rb').read()
    magic, ver, length = struct.unpack_from('<4sII', b, 0)
    assert magic == b'glTF' and ver == 2
    off = 12
    js, binc = None, None
    while off < length:
        clen, ctype = struct.unpack_from('<I4s', b, off)
        data = b[off + 8: off + 8 + clen]
        if ctype == b'JSON':
            js = json.loads(data.decode('utf-8'))
        elif ctype == b'BIN\x00':
            binc = data
        off += 8 + clen
    return js, binc


def accessor(js, binc, i):
    a = js['accessors'][i]
    bv = js['bufferViews'][a['bufferView']]
    dt = np.dtype(COMP[a['componentType']])
    n = NCOMP[a['type']]
    start = bv.get('byteOffset', 0) + a.get('byteOffset', 0)
    stride = bv.get('byteStride', 0) or dt.itemsize * n
    cnt = a['count']
    raw = np.frombuffer(binc, dtype=np.uint8, count=stride * (cnt - 1) + dt.itemsize * n, offset=start)
    out = np.lib.stride_tricks.as_strided(raw, shape=(cnt, dt.itemsize * n), strides=(stride, 1)).copy()
    return out.view(dt).reshape(cnt, n) if n > 1 else out.view(dt).reshape(cnt)


def quat_mat(q):
    x, y, z, w = q
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


def local(node):
    if 'matrix' in node:
        return np.array(node['matrix'], dtype=float).reshape(4, 4).T  # column-major in glTF
    m = np.eye(4)
    s = np.array(node.get('scale', [1, 1, 1]), float)
    r = quat_mat(node.get('rotation', [0, 0, 0, 1]))
    m[:3, :3] = r @ np.diag(s)
    m[:3, 3] = node.get('translation', [0, 0, 0])
    return m


def world_points(js, binc):
    pts, tris = [], 0
    meshes = []

    def walk(ni, parent):
        node = js['nodes'][ni]
        w = parent @ local(node)
        if 'mesh' in node:
            for prim in js['meshes'][node['mesh']]['primitives']:
                p = accessor(js, binc, prim['attributes']['POSITION']).astype(float)
                ph = np.c_[p, np.ones(len(p))] @ w.T
                idx = accessor(js, binc, prim['indices']) if 'indices' in prim else np.arange(len(p))
                meshes.append({'name': node.get('name', ''), 'pts': ph[:, :3], 'tris': len(idx) // 3, 'det': np.linalg.det(w[:3, :3])})
        for c in node.get('children', []):
            walk(c, w)
    sc = js['scenes'][js.get('scene', 0)]
    for r in sc['nodes']:
        walk(r, np.eye(4))
    return meshes


def min_area_rect(xy):
    # rotating calipers over the convex hull: returns (w, d, angle_deg of the long side 0-180, centre)
    from math import atan2
    pts = np.unique(np.round(xy, 6), axis=0)
    # convex hull (monotone chain)
    P = sorted(map(tuple, pts))
    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lower, upper = [], []
    for p in P:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    for p in reversed(P):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    hull = np.array(lower[:-1] + upper[:-1])
    best = None
    for i in range(len(hull)):
        e = hull[(i + 1) % len(hull)] - hull[i]
        a = atan2(e[1], e[0])
        c, s = math.cos(a), math.sin(a)
        R = np.array([[c, s], [-s, c]])
        q = hull @ R.T
        mn, mx = q.min(0), q.max(0)
        area = (mx - mn).prod()
        if best is None or area < best[0]:
            ctr = ((mn + mx) / 2) @ R
            best = (area, mx - mn, a, ctr)
    _, size, a, ctr = best
    w, d = size
    ang = math.degrees(a)
    if d > w:
        w, d = d, w
        ang += 90
    return w, d, ang % 180, ctr


rows = []
names = ['working table', 'visitor chair01', 'visitor chair02', 'monitor', 'banquet', 'sofa', 'stool', 'side table']
for name in names:
    js, binc = read_glb(f'{GLB_DIR}/{name}.glb')
    meshes = world_points(js, binc)
    P = np.vstack([m['pts'] for m in meshes])
    tris = sum(m['tris'] for m in meshes)
    # glTF Y-up -> Max: x = gx, y = -gz, z = gy
    mx = np.c_[P[:, 0], -P[:, 2], P[:, 1]]
    lo, hi = mx.min(0), mx.max(0)
    w, d, ang, ctr = min_area_rect(mx[:, :2])
    level = 'L1' if lo[2] < 1.5 else 'L2'
    # bank model coordinates = DWG - offset
    cx, cy = ctr[0] - OX, ctr[1] - OY
    bx, by = (lo[0] + hi[0]) / 2 - OX, (lo[1] + hi[1]) / 2 - OY
    cands = []
    for f in bank['furniture']:
        if f['floor'] != level:
            continue
        dist = math.hypot(f['x'] - cx, f['y'] - cy)
        # size difference, allowing a quarter turn
        s1 = abs(f['w'] - w) + abs(f['d'] - d)
        s2 = abs(f['w'] - d) + abs(f['d'] - w)
        cands.append((dist, min(s1, s2), f))
    cands.sort(key=lambda c: c[0])
    near = [(round(c[0], 3), round(c[1], 3), c[2]['id'], c[2]['family'][:45], f"{c[2]['w']}x{c[2]['d']}@{c[2]['rot']}") for c in cands[:4]]
    # turn check: (a) the long side's angle against the box rot; (b) for chairs: where the backrest is (top 25 % of height)
    z = mx[:, 2]
    top = mx[z > lo[2] + 0.8 * (hi[2] - lo[2])]
    back = top[:, :2].mean(0) - ctr
    back_dir = math.degrees(math.atan2(back[1], back[0])) % 360
    rows.append({'model': name, 'triangles': tris, 'meshes': len(meshes), 'mirroredMeshes': sum(1 for m in meshes if m['det'] < 0),
                 'size_m': [round(float(hi[i] - lo[i]), 3) for i in range(3)], 'baseZ': round(float(lo[2]), 4), 'topZ': round(float(hi[2]), 4),
                 'footprint': f'{w:.3f} x {d:.3f}, long side at {ang:.1f} deg', 'centreDWG': [round(float(ctr[0]), 3), round(float(ctr[1]), 3)],
                 'centreBank': [round(float(cx), 3), round(float(cy), 3)], 'bboxCentreBank': [round(float(bx), 3), round(float(by), 3)],
                 'level': level, 'nearest': near, 'topPartsFromCentre_deg': round(back_dir, 1), 'topOffset_m': round(float(np.hypot(*back)), 3)})
for r in rows:
    print(json.dumps(r, ensure_ascii=False))
