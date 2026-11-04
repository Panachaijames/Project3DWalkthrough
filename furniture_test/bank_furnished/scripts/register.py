"""Fit a model's plan silhouette to a block's drawing: the best quarter turn and shift (3 Nov 2026).

register(tris, blocks_polylines, box_centre) -> per quarter turn k (0, 90, 180, 270 degrees, counter-clockwise, about the
model's footprint centre) the best shift (the model's footprint centre put on the box centre, then searched +-0.10 m in
1 cm steps) and its scores, plus the score of the model as exported (not moved). Scores, lower is better except IoU:
  toModel  mean distance (m) from the drawing's lines to the model's silhouette outline (capped at 0.15 m)
  toLines  mean distance (m) from the model's silhouette outline to the drawing's lines (capped at 0.15 m)
  mean     (toModel + toLines) / 2
  iou      the silhouette against the drawing's filled outline (lines closed by flood fill from outside)
"""
import math

import numpy as np
from PIL import Image, ImageDraw

CELL = 0.01
CAP = 0.15


def _grid(lo, hi, margin):
    lo = np.floor((np.asarray(lo) - margin) / CELL) * CELL
    hi = np.asarray(hi) + margin
    shape = (int(math.ceil((hi[1] - lo[1]) / CELL)) + 1, int(math.ceil((hi[0] - lo[0]) / CELL)) + 1)   # rows (y), cols (x)
    return lo, shape


def _to_px(p, lo):
    return (p - lo) / CELL


def silhouette(tris, lo, shape):
    """Projected triangles (N, 3, 2) filled into a bool raster (row = y)."""
    img = Image.new('1', (shape[1], shape[0]), 0)
    dr = ImageDraw.Draw(img)
    px = _to_px(tris.reshape(-1, 2), lo).reshape(-1, 3, 2)
    for t in px:
        dr.polygon([tuple(t[0]), tuple(t[1]), tuple(t[2])], fill=1, outline=1)
    return np.array(img, dtype=bool)


def lines_raster(polylines, lo, shape, width=1):
    img = Image.new('L', (shape[1], shape[0]), 0)
    dr = ImageDraw.Draw(img)
    for pl in polylines:
        q = [tuple(v) for v in _to_px(np.asarray(pl), lo)]
        if len(q) == 1:
            dr.point(q, fill=255)
        else:
            dr.line(q, fill=255, width=width)
    return np.array(img) > 0


def filled(lines_mask):
    """The drawing's outline filled: every cell not reachable from the border without crossing a line."""
    img = Image.fromarray(np.where(lines_mask, 255, 0).astype(np.uint8))
    big = Image.new('L', (img.width + 2, img.height + 2), 0)
    big.paste(img, (1, 1))
    ImageDraw.floodfill(big, (0, 0), 128)
    a = np.array(big)[1:-1, 1:-1]
    return a != 128


def boundary(mask):
    m = mask
    er = m.copy()
    er[1:, :] &= m[:-1, :]; er[:-1, :] &= m[1:, :]; er[:, 1:] &= m[:, :-1]; er[:, :-1] &= m[:, 1:]
    return m & ~er


def dist_field(mask, cap_cells):
    """Approximate Euclidean distance (cells) to the nearest True cell, capped: alternating 4- and 8-neighbour dilation
    (an octagonal metric, within 8 % of Euclidean)."""
    d = np.full(mask.shape, float(cap_cells), dtype=np.float32)
    d[mask] = 0
    cur = mask.copy()
    for i in range(1, cap_cells + 1):
        nxt = cur.copy()
        nxt[1:, :] |= cur[:-1, :]; nxt[:-1, :] |= cur[1:, :]; nxt[:, 1:] |= cur[:, :-1]; nxt[:, :-1] |= cur[:, 1:]
        if i % 2 == 0:
            nxt[1:, 1:] |= cur[:-1, :-1]; nxt[:-1, :-1] |= cur[1:, 1:]; nxt[1:, :-1] |= cur[:-1, 1:]; nxt[:-1, 1:] |= cur[1:, :-1]
        new = nxt & ~cur
        d[new] = i * (1.0 if i % 2 else 1.0)
        cur = nxt
    return d * 0.96          # octagon -> Euclidean on average


def _lookup(field, lo, pts):
    px = np.round(_to_px(pts, lo)).astype(int)
    ok = (px[:, 0] >= 0) & (px[:, 0] < field.shape[1]) & (px[:, 1] >= 0) & (px[:, 1] < field.shape[0])
    out = np.full(len(pts), CAP / CELL, dtype=np.float32)
    out[ok] = field[px[ok, 1], px[ok, 0]]
    return np.minimum(out * CELL, CAP)


def sample(polylines, step=0.005):
    pts = []
    for pl in polylines:
        v = np.asarray(pl, dtype=float)
        pts.append(v[:1])
        for a, b in zip(v[:-1], v[1:]):
            n = max(1, int(math.dist(a, b) / step))
            t = np.linspace(0, 1, n + 1)[1:, None]
            pts.append(a + (b - a) * t)
    return np.vstack(pts)


def rot(k):
    a = math.radians(k)
    return np.array([[math.cos(a), -math.sin(a)], [math.sin(a), math.cos(a)]])


def register(tris, polylines, box_centre, turns=(0, 90, 180, 270), search=0.10, step=0.01, fine_turns=None):
    tris = np.asarray(tris, dtype=float)
    area = 0.5 * np.abs((tris[:, 1, 0] - tris[:, 0, 0]) * (tris[:, 2, 1] - tris[:, 0, 1]) -
                        (tris[:, 2, 0] - tris[:, 0, 0]) * (tris[:, 1, 1] - tris[:, 0, 1]))
    tris = tris[area > 1e-9]
    allp = tris.reshape(-1, 2)
    mlo, mhi = allp.min(0), allp.max(0)
    c_m = (mlo + mhi) / 2
    # the model's own raster (as exported, world coordinates)
    glo, gshape = _grid(mlo, mhi, 0.6)
    sil = silhouette(tris, glo, gshape)
    sil_b = boundary(sil)
    d_model = dist_field(sil_b, int(CAP / CELL) + 1)
    ys, xs = np.nonzero(sil_b)
    m_pts = np.c_[xs, ys] * CELL + glo                     # silhouette outline points, world as exported
    # the drawing's raster (world coordinates), big enough for the model's shifted outline
    b_pts = sample(polylines)
    blo, bhi = b_pts.min(0), b_pts.max(0)
    ext = max(mhi[0] - mlo[0], mhi[1] - mlo[1])
    dlo, dshape = _grid(blo, bhi, ext + 0.3)
    lines = lines_raster(polylines, dlo, dshape)
    d_lines = dist_field(lines, int(CAP / CELL) + 1)
    fill = filled(lines_raster(polylines, dlo, dshape, width=2))
    box_centre = np.asarray(box_centre, dtype=float)

    def score(R, t):
        """Pose: p' = R (p - c_m) + c_m + t (t a shift of the model's centre)."""
        inv_b = (b_pts - c_m - t) @ R + c_m                 # R^T (b - c_m - t) + c_m, row vectors
        s1 = float(_lookup(d_model, glo, inv_b).mean())
        fw = (m_pts - c_m) @ R.T + c_m + t
        s2 = float(_lookup(d_lines, dlo, fw).mean())
        return s1, s2

    def iou(R, t):
        # model silhouette cells mapped into the drawing raster
        ys, xs = np.nonzero(sil)
        p = np.c_[xs, ys] * CELL + glo
        q = (p - c_m) @ R.T + c_m + t
        px = np.round(_to_px(q, dlo)).astype(int)
        ok = (px[:, 0] >= 0) & (px[:, 0] < dshape[1]) & (px[:, 1] >= 0) & (px[:, 1] < dshape[0])
        hit = np.zeros(dshape, bool)
        hit[px[ok, 1], px[ok, 0]] = True
        inter = (hit & fill).sum()
        union = (hit | fill).sum()
        return float(inter / union) if union else 0.0

    res = {'asExported': None, 'turns': []}
    s1, s2 = score(np.eye(2), np.zeros(2))
    res['asExported'] = {'toModel': round(s1, 4), 'toLines': round(s2, 4), 'mean': round((s1 + s2) / 2, 4), 'iou': round(iou(np.eye(2), np.zeros(2)), 3)}
    ks = list(turns) if fine_turns is None else list(fine_turns)
    best_all = None
    for k in ks:
        R = rot(k)
        base = box_centre - c_m
        best = None
        n = int(round(search / step))
        for i in range(-n, n + 1):
            for j in range(-n, n + 1):
                t = base + np.array([i * step, j * step])
                s1, s2 = score(R, t)
                m = (s1 + s2) / 2
                if best is None or m < best[0]:
                    best = (m, s1, s2, t)
        m, s1, s2, t = best
        rec = {'turn': k, 'shift': [round(float(v), 4) for v in t], 'centreAfter': [round(float(v), 4) for v in (c_m + t)],
               'toModel': round(s1, 4), 'toLines': round(s2, 4), 'mean': round(m, 4), 'iou': round(iou(R, t), 3)}
        res['turns'].append(rec)
        if best_all is None or m < best_all['mean']:
            best_all = rec
    res['best'] = best_all
    res['modelFootprintCentre'] = [round(float(v), 4) for v in c_m]
    return res
