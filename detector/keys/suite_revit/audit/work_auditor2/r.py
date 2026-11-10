"""auditor2 helper: draw a box of the drawing (from prims.pkl) with layer colours, fills shaded, dashed linetypes dashed.

Usage: python -B r.py x0 y0 x1 y1 out.png [--px 2000] [--grid 0.5] [--minor 0.1] [--mark x,y,label ...] [--seg x0,y0,x1,y1 ...]
Reads only the drawing cache (prims.pkl); no detector output.
"""
import os, sys, pickle, math, argparse
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.patches import Polygon

WORK = Path(os.environ.get('OPENINGS_DATA', r'C:/Users/DWP2/AppData/Local/Temp/claude/1a2f3fc736ce552c/e1e2f8a1-5b17-462a-bbe8-01925d989674/scratchpad/suite_revit_work'))
D = pickle.load(open(WORK / 'suite_revit' / 'prims.pkl', 'rb'))

COL = {
    '0': '#8b4513', 'A-WALL': '#000000', 'S-COLS': '#333333',
    'A-DOOR': '#e01b1b', 'A-DOOR-FRAM': '#c000c0', 'A-DOOR-HDLN': '#ff5050',
    'A-GLAZ-CURT': '#00a5c8', 'A-GLAZ-CWMG': '#006070',
    'A-DETL': '#b8860b', 'A-DETL-GENF': '#ff8c00',
}
DASHED_LAYERS = {'A-DOOR-HDLN', 'A-GENM-HDLN', 'Q-CASE-HDLN'}


def colour(lay):
    return COL.get(lay, '#9aa0a6')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('x0', type=float); ap.add_argument('y0', type=float); ap.add_argument('x1', type=float); ap.add_argument('y1', type=float)
    ap.add_argument('out'); ap.add_argument('--px', type=int, default=2000)
    ap.add_argument('--grid', type=float, default=0.5); ap.add_argument('--minor', type=float, default=0.1)
    ap.add_argument('--mark', action='append', default=[]); ap.add_argument('--seg', action='append', default=[])
    ap.add_argument('--hide', default='')
    ap.add_argument('--title', default='')
    a = ap.parse_args()
    x0, y0, x1, y1 = a.x0, a.y0, a.x1, a.y1
    hide = set(a.hide.split(',')) if a.hide else set()
    w, h = x1 - x0, y1 - y0
    s = a.px / max(w, h)
    fig = plt.figure(figsize=(w * s / 100 + 1.2, h * s / 100 + 1.0), dpi=100)
    ax = fig.add_axes([0.6 / (w * s / 100 + 1.2), 0.5 / (h * s / 100 + 1.0), (w * s / 100) / (w * s / 100 + 1.2), (h * s / 100) / (h * s / 100 + 1.0)])
    g, m = a.grid, a.minor
    k = math.floor(x0 / m)
    while k * m <= x1:
        v = k * m
        major = abs(v / g - round(v / g)) < 1e-6
        ax.axvline(v, color='#e8c890' if major else '#f6ecd8', lw=0.7 if major else 0.4, zorder=0); k += 1
    k = math.floor(y0 / m)
    while k * m <= y1:
        v = k * m
        major = abs(v / g - round(v / g)) < 1e-6
        ax.axhline(v, color='#e8c890' if major else '#f6ecd8', lw=0.7 if major else 0.4, zorder=0); k += 1
    solid_segs, dashed_segs = {}, {}
    for d in D['items']:
        if d['lay'] in hide: continue
        if d['t'] in ('INSERT', 'TEXT', 'MTEXT', 'ATTRIB'): continue
        polys = [d['pts']] if 'pts' in d else d.get('loops', [])
        for p in polys:
            if not p: continue
            xs = [q[0] for q in p]; ys = [q[1] for q in p]
            if max(xs) < x0 or min(xs) > x1 or max(ys) < y0 or min(ys) > y1: continue
            if d['t'] == 'HATCH' and d.get('solid') and len(p) > 2:
                ax.add_patch(Polygon(p, closed=True, fc=colour(d['lay']), ec='none', alpha=0.28, zorder=1))
            pp = p + [p[0]] if (d.get('closed') or 'loops' in d) and len(p) > 2 else p
            lt = str(d.get('lt', 'BYLAYER')).upper()
            dashed = d['lay'] in DASHED_LAYERS or (lt not in ('BYLAYER', 'CONTINUOUS', 'BYBLOCK', ''))
            tgt = dashed_segs if dashed else solid_segs
            tgt.setdefault(d['lay'], []).extend(zip(pp, pp[1:]))
    for lay, segs in solid_segs.items():
        ax.add_collection(LineCollection(segs, colors=colour(lay), linewidths=1.0 if lay in ('0', 'A-WALL') else 0.8, zorder=3 if lay in COL else 2))
    for lay, segs in dashed_segs.items():
        ax.add_collection(LineCollection(segs, colors=colour(lay), linewidths=0.9, linestyles=(0, (4, 3)), zorder=3 if lay in COL else 2))
    for sg in a.seg:
        u = [float(t) for t in sg.split(',')]
        ax.plot([u[0], u[2]], [u[1], u[3]], color='#ffd400', lw=6, alpha=0.45, zorder=4, solid_capstyle='butt')
    for i, mk in enumerate(a.mark, 1):
        parts = mk.split(',')
        mx, my = float(parts[0]), float(parts[1]); lab = parts[2] if len(parts) > 2 else str(i)
        ax.plot(mx, my, marker='o', mfc='none', mec='#ff00aa', ms=10, mew=1.2, zorder=6)
        ax.text(mx, my, f'  {lab}', fontsize=8, color='#ff00aa', weight='bold', zorder=6)
    ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_aspect('equal')
    ax.set_xticks([round(math.ceil(x0 / g) * g + i * g, 6) for i in range(int(w / g) + 1) if math.ceil(x0 / g) * g + i * g <= x1 + 1e-9])
    ax.set_yticks([round(math.ceil(y0 / g) * g + i * g, 6) for i in range(int(h / g) + 1) if math.ceil(y0 / g) * g + i * g <= y1 + 1e-9])
    ax.tick_params(labelsize=7, top=True, right=True, labeltop=True, labelright=True); plt.setp(ax.get_xticklabels(), rotation=90)
    ax.set_title(f'{a.title}  x {x0:.2f}-{x1:.2f}  y {y0:.2f}-{y1:.2f}  black A-WALL, brown layer 0, red A-DOOR, magenta frame, cyan glass, grey other; dashed = dashed linetype', fontsize=7)
    fig.savefig(a.out); plt.close(fig)
    print(a.out)


if __name__ == '__main__':
    main()
