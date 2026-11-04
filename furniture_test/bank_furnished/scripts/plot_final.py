"""The two pictures of analysis.md: the eight models over the bank drawing (desk area and lounge, level 1), and each model in
its matched piece's block frame.

    python -B plot_final.py <work folder> <analysis.json> <out folder>
"""
import json
import math
import pickle
import sys
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
import numpy as np

W, AJ, OUT = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
A = json.loads(AJ.read_text(encoding='utf-8'))
pieces = {p['id']: p for p in json.loads((W / 'dxf_pieces.json').read_text(encoding='utf-8'))}
geo = pickle.loads((W / 'dxf_geometry.pkl').read_bytes())
LABEL = {'working table': (-2.5, -1.33), 'monitor': (-2.5, -1.72), 'visitor chair01': (-0.62, -1.4), 'visitor chair02': (-0.55, -3.25),
         'banquet': (4.3, -1.35), 'sofa': (4.2, -1.85), 'stool': (1.6, 0.05), 'side table': (1.6, -1.55)}
COL = {'working table': '#8c6d1f', 'monitor': '#d62728', 'visitor chair01': '#e377c2', 'visitor chair02': '#17becf',
       'banquet': '#1f77b4', 'sofa': '#9467bd', 'stool': '#8c564b', 'side table': '#2ca02c'}


def tris_of(name, M=None):
    z = np.load(W / f'{name}.npz')
    out = []
    for k in sorted([k for k in z.files if k.endswith('_v')], key=lambda k: int(k[1:-2])):
        v = z[k][:, :2]
        if M is not None:
            v = v @ M[:2, :2].T + M[:2, 3]
        t = z[k[:-2] + '_i']
        tr = v[t]
        if len(tr) > 25000:
            tr = tr[np.random.default_rng(0).choice(len(tr), 25000, replace=False)]
        out.append(tr)
    return np.concatenate(out)


def short(v):
    for k, w in (('right (off by 180', 'right (half turn does not show)'), ('right', 'right'), ('off by 90', 'off by 90'),
                 ('off by 180', 'off by 180'), ('any turn', 'any (round)'), ('no front', 'any (no front)'),
                 ('not comparable', 'none (round drawing)')):
        if v.startswith(k):
            return w
    return v


def rect(b):
    a = math.radians(b['rot']); c, s = math.cos(a), math.sin(a)
    hw, hd = b['w'] / 2, b['d'] / 2
    return np.array([(b['x'] + sx * hw * c - sy * hd * s, b['y'] + sx * hw * s + sy * hd * c) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1), (-1, -1))])


# ---------------------------------------------------------------- picture 1: the models over the drawing
areas = [('Desk area: working table, monitor, visitor chairs', (-2.55, 0.05, -3.35, -1.15), ['working table', 'monitor', 'visitor chair01', 'visitor chair02']),
         ('Lounge: banquet, sofa, stool, side table', (1.55, 6.35, -3.85, 0.25), ['banquet', 'sofa', 'stool', 'side table'])]
fig, axs = plt.subplots(1, 2, figsize=(16, 8.6), gridspec_kw={'width_ratios': [2.6, 4.8]})
for ax, (title, (x0, x1, y0, y1), names) in zip(axs, areas):
    for lay, typ, h, pl in geo['context']['L1']:
        a = np.array(pl)
        if len(a) == 0 or a[:, 0].max() < x0 or a[:, 0].min() > x1 or a[:, 1].max() < y0 or a[:, 1].min() > y1:
            continue
        ax.plot(a[:, 0], a[:, 1], color='#b0b0b0' if lay.startswith(('A-', 'S-')) else '#4a6fc2', lw=0.55, zorder=1)
    for p in pieces.values():
        if p['floor'] != 'L1':
            continue
        r = rect(p['box'])
        if r[:, 0].max() < x0 or r[:, 0].min() > x1 or r[:, 1].max() < y0 or r[:, 1].min() > y1:
            continue
        ax.plot(r[:, 0], r[:, 1], color='#e07b00', lw=0.8, ls='--', zorder=2)
        ax.text(p['box']['x'], p['box']['y'], p['id'][3:], fontsize=6.5, ha='center', va='center', color='#7a3a00', zorder=6, clip_on=True)
    for n in names:
        ax.add_collection(PolyCollection(tris_of(n), facecolor=COL[n], edgecolor='none', alpha=0.28, zorder=3))
        m = A['models'][n]
        c = m['worldBox']['maxZup']['centre']
        lab = f"{n}\n-> {m['match']['piece']}"
        ax.annotate(lab, xy=(c[0], c[1]), xytext=LABEL[n], fontsize=8.5, color=COL[n], fontweight='bold',
                    arrowprops=dict(arrowstyle='-', color=COL[n], lw=0.8), zorder=7,
                    bbox=dict(boxstyle='round,pad=0.15', fc='white', ec='none', alpha=0.8))
    ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_aspect('equal'); ax.grid(alpha=0.25)
    ax.set_title(title, fontsize=11)
    ax.set_xlabel('x (m, DWG / Max)'); ax.set_ylabel('y (m)')
fig.suptitle('The 3D team\'s eight models (filled) as exported, over the bank drawing (blue: furniture blocks; grey: walls) and our boxes '
             '(orange, dashed), level 1', fontsize=11.5)
fig.tight_layout()
fig.savefig(OUT / 'models_on_drawing.png', dpi=78)
plt.close(fig)

# ---------------------------------------------------------------- picture 2: each model in its piece's block frame
order = ['working table', 'visitor chair01', 'monitor', 'visitor chair02', 'banquet', 'sofa', 'stool', 'side table']
fig, axs = plt.subplots(2, 4, figsize=(17, 8.8))
for ax, n in zip(axs.ravel(), order):
    m = A['models'][n]
    pid = m['match']['piece']
    Mi = np.array(m['relativeToBlock']['maxWorldToBlockFrame_rowMajor'])
    ax.add_collection(PolyCollection(tris_of(n, Mi), facecolor=COL[n], edgecolor='none', alpha=0.25))
    targets = m['match']['run'] or [pid]
    for q in targets:
        for pl in geo['pieces'][q]:
            a = np.array(pl)
            b = a @ Mi[:2, :2].T + Mi[:2, 3]
            ax.plot(b[:, 0], b[:, 1], color='#1f3f99', lw=0.8)
    ax.plot([0], [0], 'kx')
    ax.annotate('', xy=(0, -0.22), xytext=(0, 0), arrowprops=dict(arrowstyle='->', color='k', lw=1.2))
    allp = [tris_of(n, Mi).reshape(-1, 2)] + [np.array(pl) @ Mi[:2, :2].T + Mi[:2, 3] for q in targets for pl in geo['pieces'][q]]
    allp = np.vstack(allp)
    lo, hi = allp.min(0), allp.max(0)
    pad = 0.06 * max(hi - lo)
    ax.set_xlim(min(lo[0], -0.1) - pad, max(hi[0], 0.1) + pad); ax.set_ylim(min(lo[1], -0.27) - pad, max(hi[1], 0.05) + pad)
    ax.set_aspect('equal'); ax.grid(alpha=0.25)
    o = m['orientation']
    ax.set_title(f"{n} in {pid}'s block frame\nbox turn: {short(o['boxVerdict']['verdict'])}; block turn: {short(o['blockVerdict']['verdict'])}", fontsize=8.5)
fig.suptitle("Each model (filled) moved into its piece's block frame (the INSERT undone: x = the insertion point, arrow = the block's -Y, "
             "its front by the Revit convention) over that block's drawing (blue)", fontsize=11)
fig.tight_layout()
fig.savefig(OUT / 'models_in_block_frames.png', dpi=72)
plt.close(fig)
print('wrote models_on_drawing.png and models_in_block_frames.png')
