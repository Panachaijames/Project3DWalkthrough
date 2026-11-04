"""Pixel tools for reading a rendered floor-plan picture (2 Nov 2026): numpy + Pillow + shapely only (no scipy, scikit-image or
OpenCV on this machine). Nothing in here knows a drawing: read_pictures.py holds the rules and the readings.
  load() ............ the picture as a float RGB array
  colour_classes() .. one boolean mask per colour class (wall grey, ink, red annotation, light, beige floor, grey floor, teal ...)
  inpaint() ......... masked pixels (red annotation strokes) filled with the colour around them, from the outside in
  dilate(), erode(), opening(), closing()  square-kernel morphology (separable shifts)
  runs(), components()   connected parts of a mask (8-connected), labelled through the runs of each row
  mask_polygons() .. a mask -> shapely polygons in pixel coordinates (pixel (c, r) is the square c..c+1, r..r+1)
  crossings() ...... sub-pixel places where a grey-level profile crosses a threshold (gap ends)
  dip(), first_dip()  sub-pixel centre of a dark stroke on a profile (a wall face drawn as an outline stroke)
  straighten() ...... outlines traced from pixels -> straight faces: the edges near the picture's axes snapped to shared levels,
                      each level moved onto the outline stroke drawn there (the wall's face), the corners rebuilt
Pixel coordinates: x = column, y = row, both growing right and down; a pixel's centre is at (c + 0.5, r + 0.5).
"""
import math
import numpy as np
from PIL import Image
from shapely.geometry import Polygon, box as sbox
from shapely.geometry.polygon import orient
from shapely.ops import unary_union


def load(path):
    """The picture as float RGB (H, W, 3)."""
    return np.asarray(Image.open(path).convert('RGB')).astype(np.float32)


# ---------------------------------------------------------------------------------------------------- colour classes
def colour_classes(a):
    """One boolean mask per colour class. The thresholds are the measured colours of this office's presentation renders
    (grey levels 0-255): walls are neutral dark grey (about 88-125), lettering and outlines near black, annotations red,
    furniture, glazing and the paper outside near white, floors beige (about 232, 216, 184), mid grey (168-184) or teal."""
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    mx, mn = a.max(axis=2), a.min(axis=2)
    m = a.mean(axis=2)
    sat = mx - mn
    neutral = sat <= 24
    return {
        'grey': m,                                                            # the grey level itself (for profiles)
        'red': (r >= 110) & (r - g >= 60) & (r - b >= 60) & (g < 150),        # annotations: dashed lines, dots, red text
        'ink': (m < 70) & (sat <= 40),                                        # lettering, arrows, furniture outlines
        'dark': (neutral & (m >= 60) & (m < 162)) | ((sat <= 45) & (m < 110)),   # wall grey, or a dark warm tint (the RED BOX's walls);
                                                                              # dark floor fills too, told apart by shape
        'light': neutral & (m >= 222),                                        # furniture, glazing, lift cars, stair treads, paper
        'midgrey': neutral & (m >= 162) & (m < 222),                          # grey floors (lounge, terrace, stairs)
        'beige': (r > g) & (g > b) & (r - b >= 18) & (m >= 150),              # the beige floor (and its shadows, darker)
        'brown': (r > g) & (g >= b) & (r - b >= 25) & (m >= 70) & (m < 150),  # timber-coloured bands (stair sides)
        'teal': (g - r >= 15) & (b - r >= 15),                                # toilet floors
        'orange': (r >= 215) & (r - b >= 60) & (g >= 140),                    # a zone beyond the plan (floor 2, top)
        'green': (g - r >= 12) & (g - b >= 12) & (m < 200),                   # plants
    }


def inpaint(a, mask, max_iter=20):
    """The pixels under `mask` filled with the colour around them: each pass gives every masked pixel that touches a known one
    (8 neighbours) the mean of its known neighbours, from the outside in, until none is left (a red stroke 3-4 px wide takes 2
    passes). Deterministic; returns a new array."""
    out = a.astype(np.float32).copy()
    todo = mask.copy()
    H, W = todo.shape
    for _ in range(max_iter):
        if not todo.any(): break
        known = ~todo
        acc = np.zeros_like(out); cnt = np.zeros((H, W), np.float32)
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if not dy and not dx: continue
                ys = slice(max(dy, 0), H + min(dy, 0)); yd = slice(max(-dy, 0), H + min(-dy, 0))
                xs = slice(max(dx, 0), W + min(dx, 0)); xd = slice(max(-dx, 0), W + min(-dx, 0))
                k = known[ys, xs]
                acc[yd, xd] += out[ys, xs] * k[..., None]; cnt[yd, xd] += k
        fill = todo & (cnt > 0)
        out[fill] = acc[fill] / cnt[fill][:, None]
        todo &= ~fill
    return out


# ---------------------------------------------------------------------------------------------------- morphology
def _shift_or(m, r, axis):
    out = m.copy()
    for d in range(1, r + 1):
        if axis == 0:
            out[d:, :] |= m[:-d, :]; out[:-d, :] |= m[d:, :]
        else:
            out[:, d:] |= m[:, :-d]; out[:, :-d] |= m[:, d:]
    return out


def dilate(m, r):
    """Square (2r+1) dilation."""
    if r <= 0: return m.copy()
    return _shift_or(_shift_or(m, r, 0), r, 1)


def erode(m, r):
    """Square (2r+1) erosion (pixels beyond the picture's edge count as set, so a band cut by the edge keeps its end)."""
    if r <= 0: return m.copy()
    p = np.pad(~m, r, constant_values=False)
    return ~dilate(p, r)[r:-r, r:-r]


def opening(m, r):
    """Erode then dilate: removes every part thinner than 2r+1 pixels."""
    return dilate(erode(m, r), r) & m


def closing(m, r):
    """Dilate then erode: fills gaps narrower than 2r+1 pixels."""
    return erode(dilate(m, r), r)


# ---------------------------------------------------------------------------------------------------- connected parts
def runs(m):
    """Runs of set pixels per row: a list of (row, c0, c1) with c1 exclusive, in row order."""
    out = []
    pad = np.zeros((m.shape[0], m.shape[1] + 2), dtype=np.int8)
    pad[:, 1:-1] = m
    d = np.diff(pad, axis=1)
    for row in range(m.shape[0]):
        starts = np.flatnonzero(d[row] == 1); ends = np.flatnonzero(d[row] == -1)
        out += [(row, int(s), int(e)) for s, e in zip(starts, ends)]
    return out


def components(m, min_area=1):
    """Connected parts (8-connected) of a mask -> list of {'runs': [(row, c0, c1)], 'area', 'bbox': (x0, y0, x1, y1)}
    (bbox exclusive at the high end), in the order of their first pixel (top to bottom, left to right)."""
    rs = runs(m)
    parent = list(range(len(rs)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]; i = parent[i]
        return i
    by_row = {}
    for i, (row, c0, c1) in enumerate(rs):
        by_row.setdefault(row, []).append(i)
    for i, (row, c0, c1) in enumerate(rs):
        for j in by_row.get(row - 1, ()):
            _, d0, d1 = rs[j]
            if d0 <= c1 and c0 <= d1:                      # 8-connected: touching diagonally counts
                a, b = find(i), find(j)
                if a != b: parent[max(a, b)] = min(a, b)
    groups = {}
    for i in range(len(rs)):
        groups.setdefault(find(i), []).append(rs[i])
    out = []
    for k in sorted(groups):
        g = groups[k]
        area = sum(c1 - c0 for _, c0, c1 in g)
        if area < min_area: continue
        out.append({'runs': g, 'area': area, 'bbox': (min(c0 for _, c0, _ in g), min(r for r, _, _ in g),
                                                       max(c1 for _, _, c1 in g), max(r for r, _, _ in g) + 1)})
    return out


def comp_mask(comp, shape):
    m = np.zeros(shape, dtype=bool)
    for row, c0, c1 in comp['runs']: m[row, c0:c1] = True
    return m


def mask_polygons(m, simplify=0.75):
    """A mask -> shapely (Multi)Polygon in pixel coordinates: the union of its row runs, simplified by `simplify` px."""
    boxes = [sbox(c0, r, c1, r + 1) for r, c0, c1 in runs(m)]
    if not boxes: return None
    g = unary_union(boxes)
    return g.simplify(simplify, preserve_topology=True) if simplify else g


def comp_polygon(comp, simplify=0.75):
    g = unary_union([sbox(c0, r, c1, r + 1) for r, c0, c1 in comp['runs']])
    return g.simplify(simplify, preserve_topology=True) if simplify else g


# ---------------------------------------------------------------------------------------------------- profiles
def crossings(profile, start=0.0, thr=160.0):
    """Sub-pixel places where a profile (values at pixel centres) crosses thr: [(position, 'down' | 'up')], where
    position is in pixel-edge coordinates (the centre of pixel i is at start + i + 0.5); 'down' = into the dark."""
    out = []
    p = np.asarray(profile, dtype=float)
    for i in range(len(p) - 1):
        a, b = p[i], p[i + 1]
        if (a - thr) * (b - thr) < 0 or (b == thr and a != thr):
            t = (thr - a) / (b - a)
            out.append((float(start + i + 0.5 + t), 'down' if b < a else 'up'))
    return out


def profile(grey, p0, p1, step=0.25, half=1):
    """Grey levels sampled along the segment p0 -> p1 every `step` px (nearest pixel), averaged over a strip `half` px each
    side across it. -> (distances along, values)."""
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    L = float(np.hypot(*(p1 - p0)))
    u = (p1 - p0) / L; n = np.array([-u[1], u[0]])
    ts = np.arange(0.0, L + 1e-9, step)
    vals = []
    H, W = grey.shape
    for t in ts:
        acc = []
        for k in range(-half, half + 1):
            x, y = p0 + u * t + n * k
            c, r = int(np.floor(x)), int(np.floor(y))
            if 0 <= r < H and 0 <= c < W: acc.append(grey[r, c])
        vals.append(np.mean(acc) if acc else 255.0)
    return ts, np.array(vals)


# ---------------------------------------------------------------------------------------------------- outline strokes
def _vertex(p, i):
    """sub-pixel offset of a minimum at index i: the parabola through p[i-1], p[i], p[i+1] (0 at an end or a flat bottom)."""
    if i <= 0 or i >= len(p) - 1: return 0.0
    a, b, c = float(p[i - 1]), float(p[i]), float(p[i + 1])
    den = a - 2 * b + c
    return 0.5 * (a - c) / den if den > 1e-9 else 0.0


def first_dip(vals, min_dip=6.0, min_drop=30.0, behind=3):
    """The first dark stroke met walking along `vals` (grey levels at pixel centres, from the light side into the wall): the first
    index i with vals[i] <= its neighbours whose value lies min_drop or more below the first value (the floor) and min_dip or more
    below the lightest of the `behind` values after it (the wall's fill behind the stroke). -> (sub-pixel index, value) or None."""
    v = np.asarray(vals, dtype=float)
    for i in range(1, len(v) - 1):
        if v[i] > v[i - 1] or v[i] > v[i + 1]: continue
        if v[0] - v[i] < min_drop: continue
        if v[i + 1:i + 1 + behind].max() - v[i] < min_dip: continue
        return i + _vertex(v, i), float(v[i])
    return None


def dip(vals):
    """The darkest point of a profile, sub-pixel (index units). -> (index, value)."""
    v = np.asarray(vals, dtype=float)
    i = int(np.argmin(v))
    return i + _vertex(v, i), float(v[i])


def _across(grey, axis, level, inward, along, out=2.5, depth=7.0):
    """Grey levels at pixel centres on the line across a face: for an x-level, along row `along`, from `out` px on the open side
    to `depth` px into the wall (inward = +1: the wall lies at larger coordinates). -> (centres, values), open side first."""
    H, W = grey.shape
    if inward > 0: idx = np.arange(int(math.floor(level - out)), int(math.floor(level + depth)) + 1)
    else: idx = np.arange(int(math.floor(level + out)), int(math.floor(level - depth)) - 1, -1)
    r = int(math.floor(along))
    if axis == 'x':
        ok = (idx >= 0) & (idx < W) & (0 <= r < H)
        return idx[ok] + 0.5, (grey[r, idx[ok]] if ok.any() else np.array([]))
    ok = (idx >= 0) & (idx < H) & (0 <= r < W)
    return idx[ok] + 0.5, (grey[idx[ok], r] if ok.any() else np.array([]))


def _inside_run(mask, axis, level, inward, along, cap=30):
    """How many pixels of `mask` lie in a row inward from a face (the wall's thickness there, at most cap)."""
    H, W = mask.shape
    r = int(math.floor(along))
    c = int(math.floor(level + 0.5)) if inward > 0 else int(math.floor(level - 0.5))
    n = 0
    while n < cap:
        x, y = (c, r) if axis == 'x' else (r, c)
        if not (0 <= x < W and 0 <= y < H) or not mask[y, x]: break
        n += 1; c += inward
    return n


def straighten(polys, grey, mask=None, known=(), snap=1.6, tol_deg=12.0, min_len=2.5, reach=(-1.0, 5.0), min_share=0.4, step=1.0):
    """Outlines traced from a wall mask (pixel coordinates) -> straight faces, on the outline strokes. On every outline (all of
    them together, so that the faces of separate pieces in line come out in line):
      1. an edge within tol_deg of an axis and at least min_len px long is a face; a face within known[i]['tol'] px of a known
         level of its axis and facing ('axis', 'in' = +1 when the wall lies at larger coordinates, 'at', 'span' along the
         axis) takes that level as it is; the other faces of one axis that face the same way and lie within `snap` px of a
         level (the length-weighted mean of the faces gathered so far, in order of position) share that level;
      2. each level is moved onto the stroke drawn along it: on lines across its faces every `step` px (1.5 px clear of their
         ends) the first dark stroke met coming from the open side (first_dip), between reach[0] and reach[1] px of the level
         (+ = into the wall) and less than half the wall's thickness there (`mask`: so the two faces of a wall drawn as a
         single line never cross); when a stroke is found on min_share or more of the lines, the level moves by the median
         (a wall drawn as one dark band, with no stroke of its own, keeps its traced level);
      3. the corners are rebuilt: a vertical face meets a horizontal one at their two levels; two faces of one axis on different
         levels meet in a jog across the axis; anything else keeps its traced point.
    -> (polygons in the same order, the levels: [{'axis', 'facing', 'traced', 'level', 'moved', 'share', 'faces', 'length'}])"""
    tol = math.tan(math.radians(tol_deg))
    items = []
    for pi, p in enumerate(polys):
        p = orient(p, 1.0)                                              # exterior counter-clockwise: the wall lies to the left
        for ri, r in enumerate([p.exterior] + list(p.interiors)):
            items.append((pi, ri, list(r.coords)[:-1]))
    faces = []
    for it, (pi, ri, pts) in enumerate(items):
        n = len(pts)
        for k in range(n):
            (x0, y0), (x1, y1) = pts[k], pts[(k + 1) % n]
            dx, dy = x1 - x0, y1 - y0
            L = math.hypot(dx, dy)
            if L < min_len: continue
            if abs(dx) <= tol * abs(dy):
                faces.append({'it': it, 'k': k, 'axis': 'x', 'pos': (x0 + x1) / 2, 'len': L, 'in': 1 if dy < 0 else -1,
                              'span': (min(y0, y1), max(y0, y1))})
            elif abs(dy) <= tol * abs(dx):
                faces.append({'it': it, 'k': k, 'axis': 'y', 'pos': (y0 + y1) / 2, 'len': L, 'in': 1 if dx > 0 else -1,
                              'span': (min(x0, x1), max(x0, x1))})
    report, where = [], {}
    for kn in known:
        mine = [f for f in faces if f['axis'] == kn['axis'] and f['in'] == kn['in'] and abs(f['pos'] - kn['at']) <= kn['tol']
                and f['span'][1] >= kn['span'][0] and f['span'][0] <= kn['span'][1] and (f['it'], f['k']) not in where]
        for f in mine: where[(f['it'], f['k'])] = (kn['axis'], kn['at'])
        if mine:
            traced = sum(f['pos'] * f['len'] for f in mine) / sum(f['len'] for f in mine)
            report.append({'axis': kn['axis'], 'facing': ('-' if kn['in'] > 0 else '+') + kn['axis'], 'traced': round(traced, 2), 'level': round(kn['at'], 2),
                           'moved': round((kn['at'] - traced) * kn['in'], 2), 'share': None, 'faces': len(mine),
                           'length': round(sum(f['len'] for f in mine), 1), 'known': kn.get('why', True)})
    faces = [f for f in faces if (f['it'], f['k']) not in where]
    levels = []
    for axis in ('x', 'y'):
        for inward in (1, -1):
            cur = []
            for f in sorted((f for f in faces if f['axis'] == axis and f['in'] == inward), key=lambda f: (f['pos'], f['it'], f['k'])):
                if cur and abs(f['pos'] - sum(c['pos'] * c['len'] for c in cur) / sum(c['len'] for c in cur)) > snap:
                    levels.append(cur); cur = []
                cur.append(f)
            if cur: levels.append(cur)
    for lev in levels:
        axis, inward = lev[0]['axis'], lev[0]['in']
        traced = sum(f['pos'] * f['len'] for f in lev) / sum(f['len'] for f in lev)
        offs, lines = [], 0
        for f in lev:
            lo, hi = f['span']
            for s in np.arange(lo + 1.5, hi - 1.5 + 1e-9, step):
                cs, vs = _across(grey, axis, traced, inward, s)
                if len(vs) < 5: continue
                lines += 1
                hit = first_dip(vs)
                if hit is None: continue
                i, _ = hit
                j = int(math.floor(i)); fr = i - j
                c = cs[j] + (cs[min(j + 1, len(cs) - 1)] - cs[j]) * fr          # centre coordinate of the sub-pixel index
                o = (c - traced) * inward
                if not reach[0] <= o <= reach[1]: continue
                if mask is not None and o >= _inside_run(mask, axis, traced, inward, s) / 2 - 0.25: continue
                offs.append(o)
        share = len(offs) / lines if lines else 0.0
        moved = float(np.median(offs)) if offs and share >= min_share else 0.0
        level = traced + moved * inward
        report.append({'axis': axis, 'facing': ('-' if inward > 0 else '+') + axis, 'traced': round(traced, 2), 'level': round(level, 2),
                       'moved': round(moved, 2), 'share': round(share, 2), 'faces': len(lev), 'length': round(sum(f['len'] for f in lev), 1)})
        for f in lev: where[(f['it'], f['k'])] = (axis, level)
    rings = {}
    for it, (pi, ri, pts) in enumerate(items):
        n = len(pts); out = []
        for k in range(n):
            a, b = where.get((it, (k - 1) % n)), where.get((it, k))
            x, y = pts[k]
            if a and b and a[0] != b[0]:
                out.append((a[1], b[1]) if a[0] == 'x' else (b[1], a[1]))
            elif a and b:
                out += [(a[1], y), (b[1], y)] if a[0] == 'x' else [(x, a[1]), (x, b[1])]
            elif a or b:
                c = a or b
                out.append((c[1], y) if c[0] == 'x' else (x, c[1]))
            else:
                out.append((x, y))
        clean = []
        for q in out:
            if not clean or math.dist(q, clean[-1]) > 1e-6: clean.append(q)
        while len(clean) > 1 and math.dist(clean[0], clean[-1]) <= 1e-6: clean.pop()
        rings.setdefault(pi, {})[ri] = clean
    result = []
    for pi, p in enumerate(polys):
        rr = rings.get(pi, {})
        ext = rr.get(0, [])
        holes = [rr[k] for k in sorted(rr) if k > 0 and len(rr[k]) >= 3]
        g = Polygon(ext, holes) if len(ext) >= 3 else Polygon()
        if not g.is_valid: g = g.buffer(0)
        if g.is_empty or abs(g.area - p.area) > 0.5 * p.area + 3 * p.length:
            g = p                                                       # a rebuild that went wrong keeps the traced outline
        result.append(g)
    return result, report
