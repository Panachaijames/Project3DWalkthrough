"""Fit centre / radius / sweep of every arc (from its flattened points); list door-layer arcs and swing-like arcs elsewhere."""
import sys; sys.path.insert(0, '.')
from load import *
import numpy as np
D = load()
def fit(P):
    P = np.array(P)
    if len(P) < 3: return None
    A = np.c_[2 * P[:, 0], 2 * P[:, 1], np.ones(len(P))]
    b = (P ** 2).sum(1)
    c, *_ = np.linalg.lstsq(A, b, rcond=None)
    cx, cy = c[0], c[1]; r = math.sqrt(c[2] + cx * cx + cy * cy)
    a0 = math.degrees(math.atan2(P[0][1] - cy, P[0][0] - cx)); a1 = math.degrees(math.atan2(P[-1][1] - cy, P[-1][0] - cx))
    sw = (a1 - a0) % 360
    if sw > 180: sw = 360 - sw
    return cx, cy, r, a0, a1, sw
rows = []
for d in D['items']:
    if d['t'] != 'ARC': continue
    f = fit(d['pts'])
    if not f: continue
    cx, cy, r, a0, a1, sw = f
    door = d['lay'].startswith('A-DOOR')
    if door or (0.5 <= r <= 1.3 and 15 <= sw <= 125):
        rows.append((d['lay'], d['h'], d['path'][:25], round(cx, 3), round(cy, 3), round(r, 3), round(a0, 1), round(a1, 1), round(sw, 1), d.get('lt')))
for r in sorted(rows, key=lambda r: (not r[0].startswith('A-DOOR'), r[3])): print(*r)
