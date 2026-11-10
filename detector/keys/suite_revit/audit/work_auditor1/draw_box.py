"""auditor1 helper: draw a box of the drawing cache (prims.pkl) with every layer in its own colour, SOLID fills shaded,
dashed linetypes dashed, a labelled 0.5 m grid with 0.1 m minor lines, and optional marked segments.

Usage: python -B draw_box.py x0 y0 x1 y1 out.png [--seg "x1,y1,x2,y2,label" ...] [--title T]
"""
import os, sys, pickle, argparse, math
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.patches import Polygon

ap = argparse.ArgumentParser()
for k in ('x0', 'y0', 'x1', 'y1'): ap.add_argument(k, type=float)
ap.add_argument('out'); ap.add_argument('--seg', action='append', default=[]); ap.add_argument('--title', default='')
a = ap.parse_args()
D = pickle.load(open(Path(os.environ['OPENINGS_DATA']) / 'suite_revit' / 'prims.pkl', 'rb'))
COL = {'0': '#a0522d', 'A-WALL': '#000000', 'S-COLS': '#333333', 'A-GLAZ-CURT': '#00a5c8', 'A-GLAZ-CWMG': '#006d6d',
       'A-DOOR': '#e01b1b', 'A-DOOR-FRAM': '#c000c0', 'A-DOOR-HDLN': '#e01b1b', 'A-DETL': '#b8860b', 'A-GENM-HDLN': '#8a7bd8',
       'P-SANR-FIXT': '#1f4fff', 'I-FURN': '#1f8a4c', 'I-FURN-CHAR': '#1f8a4c', 'M-EQPM': '#3070b0'}
SKIP = {'Q-SPCQ', 'Q-CASE', 'Q-CASE-HDLN', 'E-LITE-EQPM', 'A-DETL-GENF', 'A-ANNO-IDEN', 'A-ANNO-NOTE'}
DASH = {'A-DOOR-HDLN', 'A-GENM-HDLN'}
x0, y0, x1, y1 = a.x0, a.y0, a.x1, a.y1
w, h = x1 - x0, y1 - y0
s = 1600 / max(w, h)
fig = plt.figure(figsize=(w * s / 100 + 1.4, h * s / 100 + 1.2), dpi=100)
ax = fig.add_axes([0.7 / (w * s / 100 + 1.4), 0.6 / (h * s / 100 + 1.2), (w * s / 100) / (w * s / 100 + 1.4), (h * s / 100) / (h * s / 100 + 1.2)])
for i in range(int(math.floor(x0 * 10)), int(math.ceil(x1 * 10)) + 1):
    v = i / 10
    ax.axvline(v, color='#f6e7cc' if i % 5 else '#e8c88c', lw=0.4 if i % 5 else 0.8, zorder=0)
for i in range(int(math.floor(y0 * 10)), int(math.ceil(y1 * 10)) + 1):
    v = i / 10
    ax.axhline(v, color='#f6e7cc' if i % 5 else '#e8c88c', lw=0.4 if i % 5 else 0.8, zorder=0)
segs = {}
for d in D['items']:
    lay = d['lay']
    if lay in SKIP or d['t'] in ('INSERT', 'MTEXT', 'TEXT', 'ATTRIB'): continue
    c = COL.get(lay, '#9a9a9a')
    if 'loops' in d:
        for L in d['loops']:
            if not L: continue
            xs = [p[0] for p in L]; ys = [p[1] for p in L]
            if max(xs) < x0 or min(xs) > x1 or max(ys) < y0 or min(ys) > y1: continue
            ax.add_patch(Polygon(L, closed=True, facecolor=c, alpha=0.35, edgecolor='none', zorder=1))
        continue
    p = d.get('pts')
    if not p: continue
    xs = [q[0] for q in p]; ys = [q[1] for q in p]
    if max(xs) < x0 or min(xs) > x1 or max(ys) < y0 or min(ys) > y1: continue
    pp = p + [p[0]] if d.get('closed') and len(p) > 2 else p
    dashed = lay in DASH or str(d.get('lt', '')).upper() not in ('BYLAYER', 'CONTINUOUS', 'BYBLOCK', '')
    segs.setdefault((c, dashed), []).extend(zip(pp, pp[1:]))
for (c, dashed), S in segs.items():
    ax.add_collection(LineCollection(S, colors=c, linewidths=1.0, linestyles='--' if dashed else '-', zorder=2))
for sg in a.seg:
    v = sg.split(',')
    ax.plot([float(v[0]), float(v[2])], [float(v[1]), float(v[3])], color='#ffbf00', lw=6, alpha=0.55, solid_capstyle='butt', zorder=3)
    for k in (0, 2):
        ax.plot(float(v[k]), float(v[k + 1]), marker='o', mfc='none', mec='#ff6a00', ms=7, zorder=4)
    if len(v) > 4: ax.text((float(v[0]) + float(v[2])) / 2, (float(v[1]) + float(v[3])) / 2, '  ' + v[4], fontsize=8, color='#d04000', weight='bold', zorder=5)
ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_aspect('equal')
ax.set_xticks([i / 2 for i in range(int(math.ceil(x0 * 2)), int(math.floor(x1 * 2)) + 1)])
ax.set_yticks([i / 2 for i in range(int(math.ceil(y0 * 2)), int(math.floor(y1 * 2)) + 1)])
ax.tick_params(labelsize=7)
ax.set_title(a.title or f'x {x0}-{x1}, y {y0}-{y1} (drawing metres); brown layer 0, black A-WALL, red A-DOOR(-HDLN), magenta A-DOOR-FRAM, cyan glass', fontsize=8)
fig.savefig(a.out); plt.close(fig)
print(a.out)
