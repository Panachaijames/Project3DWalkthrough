"""Labeller A's renderer: python draw.py x0 y0 x1 y1 out.png [--px N] [--grid G] [--mark x,y,label ...] [--seg x1,y1,x2,y2,label ...]
Layer 0 brown (fills shaded), A-WALL / S-COLS black (fills grey), glass cyan, A-DOOR red, A-DOOR-FRAM magenta,
A-DOOR-HDLN orange, everything else light grey. Dashed entities drawn dashed."""
import sys, math, argparse
sys.path.insert(0, '.')
from load import *
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection, PolyCollection

COL = {'0': '#8b4513', 'A-WALL': '#000000', 'S-COLS': '#000000', 'A-GLAZ-CURT': '#00a5c8', 'A-GLAZ-CWMG': '#0070a0',
       'A-DOOR': '#e01b1b', 'A-DOOR-FRAM': '#c000c0', 'A-DOOR-HDLN': '#ff8000', 'A-DETL': '#008000'}
FILL = {'0': '#d9a066', 'A-WALL': '#777777', 'S-COLS': '#555555', 'A-GLAZ-CWMG': '#66c0e0'}

def main():
    ap = argparse.ArgumentParser()
    for k in ('x0', 'y0', 'x1', 'y1'): ap.add_argument(k, type=float)
    ap.add_argument('out'); ap.add_argument('--px', type=int, default=2400); ap.add_argument('--grid', type=float, default=0.5)
    ap.add_argument('--mark', action='append', default=[]); ap.add_argument('--seg', action='append', default=[])
    ap.add_argument('--layers'); ap.add_argument('--nofurn', action='store_true')
    a = ap.parse_args()
    D = load()
    x0, y0, x1, y1 = a.x0, a.y0, a.x1, a.y1
    only = set(a.layers.split(',')) if a.layers else None
    segs = {}; fills = {}
    for d in D['items']:
        lay = d['lay']
        if only and lay not in only: continue
        if a.nofurn and lay not in COL: continue
        if d['t'] in ('INSERT', 'MTEXT', 'TEXT', 'ATTRIB'): continue
        if not inbox(d, x0, y0, x1, y1): continue
        dashed = 'DASH' in str(d.get('lt', '')).upper() or 'HIDDEN' in str(d.get('lt', '')).upper() or 'CENTRE' in str(d.get('lt', '')).upper() or lay.endswith('HDLN')
        if 'loops' in d or d['t'] == 'SOLID':
            loops = d.get('loops') or [d['pts']]
            for L in loops:
                fills.setdefault(lay, []).append(L)
            continue
        p = d['pts']
        pp = p + [p[0]] if d.get('closed') and len(p) > 2 else p
        segs.setdefault((lay, dashed), []).extend(zip(pp, pp[1:]))
    w, h = x1 - x0, y1 - y0
    s = a.px / max(w, h)
    fig = plt.figure(figsize=(w * s / 100 + 1.2, h * s / 100 + 1.0), dpi=100)
    ax = fig.add_axes([0.6 / (w * s / 100 + 1.2), 0.5 / (h * s / 100 + 1.0), (w * s / 100) / (w * s / 100 + 1.2), (h * s / 100) / (h * s / 100 + 1.0)])
    g = a.grid
    gx = math.floor(x0 / g) * g
    while gx <= x1:
        ax.axvline(gx, color='#f0d9b0', lw=0.5, zorder=0); gx += g
    gy = math.floor(y0 / g) * g
    while gy <= y1:
        ax.axhline(gy, color='#f0d9b0', lw=0.5, zorder=0); gy += g
    for lay, Ls in fills.items():
        ax.add_collection(PolyCollection(Ls, facecolors=FILL.get(lay, '#dddddd'), edgecolors='none', alpha=0.6, zorder=1))
    for (lay, dashed), S in segs.items():
        c = COL.get(lay, '#bbbbbb'); lw = 0.9 if lay in COL else 0.4
        ax.add_collection(LineCollection(S, colors=c, linewidths=lw, linestyles='--' if dashed else '-', zorder=3 if lay in COL else 2))
    for i, m in enumerate(a.mark, 1):
        parts = m.split(','); mx, my = float(parts[0]), float(parts[1]); lab = parts[2] if len(parts) > 2 else str(i)
        ax.plot(mx, my, marker='o', mfc='none', mec='#ff00aa', ms=12, mew=1.4, zorder=6)
        ax.text(mx, my, f'  {lab}', fontsize=8, color='#ff00aa', weight='bold', zorder=6)
    for sg in a.seg:
        parts = sg.split(','); xa, ya, xb, yb = map(float, parts[:4]); lab = parts[4] if len(parts) > 4 else ''
        ax.plot([xa, xb], [ya, yb], color='#00c000', lw=2.2, alpha=0.8, zorder=7)
        ax.plot([xa, xb], [ya, yb], 'o', color='#00c000', ms=4, zorder=7)
        ax.text((xa + xb) / 2, (ya + yb) / 2, f' {lab}', fontsize=8, color='#007000', weight='bold', zorder=7)
    ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_aspect('equal')
    step = g if w / g <= 50 else g * math.ceil(w / g / 50)
    xt = []; t = math.ceil(x0 / step) * step
    while t <= x1: xt.append(round(t, 3)); t += step
    yt = []; t = math.ceil(y0 / step) * step
    while t <= y1: yt.append(round(t, 3)); t += step
    ax.set_xticks(xt); ax.set_yticks(yt)
    ax.tick_params(labelsize=6); plt.setp(ax.get_xticklabels(), rotation=90)
    ax.set_title(f'suite_revit x {x0:.2f}-{x1:.2f} y {y0:.2f}-{y1:.2f}: brown layer 0, black A-WALL/S-COLS, cyan glass, red A-DOOR, magenta FRAM, orange HDLN', fontsize=7)
    fig.savefig(a.out); plt.close(fig)
    print(a.out)

if __name__ == '__main__':
    main()
