"""Render part of a plan (from prims.pkl) as a PNG with a metre grid, coloured by what each layer holds.

Usage: python render.py <sukhumvit|presidential|bank1|bank2|l29|l30> <xmin> <ymin> <xmax> <ymax> <out.png> [options]
  coordinates are DRAWING METRES (DXF millimetres / 1000), the same as prims.pkl
  --px N          long side in pixels (default 2400)
  --grid G        grid step in metres (default 1.0); labels on every line
  --area A        only items tagged with this area (ground | upper | suite | L1 | L2)
  --inserts       label door / window / jamb inserts with their block name
  --text          draw TEXT / MTEXT / ATTRIB strings
  --mark x,y[,label]   a numbered marker (repeatable)
  --only cats     comma list of categories to draw (wall,glass,window,door,jamb,stair,other)
Colours: wall black, glass cyan, window blue, door red, jamb magenta, stair green, everything else light grey.
"""
import argparse, math, sys
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
sys.path.insert(0, str(Path(__file__).resolve().parent))
import prims

COLORS = {'wall': ('#111111', 1.1), 'glass': ('#00a5c8', 1.0), 'window': ('#1f4fff', 0.9), 'door': ('#e01b1b', 0.9),
          'jamb': ('#b000b0', 0.9), 'stair': ('#139a3a', 0.8), 'other': ('#c4c4c4', 0.35)}

SUK = {'wall': {'COL', 'STRUCTURE', 'WALL', 'XR_L44 Plan$0$A-WALL', 'XR_L55 Plan$0$A-WALL'}, 'glass': {'WALL-GL'},
       'window': {'WIN', 'W_Grill', 'A_Grill'}, 'door': {'DOOR', 'XR_L44 Plan$0$A-DOOR', 'XR_L44$0$I-DOOR', 'OPEN', 'DSYM'},
       'jamb': {'D-JAMB'}, 'stair': {'STAIR'}}


def category(name, lay):
    if name == 'sukhumvit':
        for k, v in SUK.items():
            if lay in v: return k
        return 'other'
    if name not in ('sukhumvit', 'presidential'):    # Revit exports with AIA / NCS layer names (bank branch, tower floors L29 / L30)
        U = lay.upper()
        if U.startswith('A-WALL') or U.startswith('S-COLS'): return 'wall'
        if 'GLAZ' in U or 'CURT' in U: return 'glass'
        if U.startswith('A-DOOR'): return 'door'
        if 'WIND' in U: return 'window'
        if 'STRS' in U or 'STAIR' in U: return 'stair'
        return 'other'
    L = lay.lower()                                  # presidential: Vietnamese / mixed layer names
    if lay == 'A-1.Netcat - tuong': return 'wall'
    if 'kinh' in L or 'glass' in L or 'kính' in L: return 'glass'
    if 'cua' in L or 'door' in L or 'cửa' in L: return 'door'
    if 'win' in L: return 'window'
    if 'stair' in L or 'thang' in L: return 'stair'
    if lay == 'A-4. Dim': return 'jamb'
    return 'other'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('file'); ap.add_argument('x0', type=float); ap.add_argument('y0', type=float)
    ap.add_argument('x1', type=float); ap.add_argument('y1', type=float); ap.add_argument('out')
    ap.add_argument('--px', type=int, default=2400); ap.add_argument('--grid', type=float, default=1.0)
    ap.add_argument('--area'); ap.add_argument('--inserts', action='store_true'); ap.add_argument('--text', action='store_true')
    ap.add_argument('--mark', action='append', default=[]); ap.add_argument('--only')
    a = ap.parse_args()
    D = prims.load(a.file)
    x0, y0, x1, y1 = a.x0, a.y0, a.x1, a.y1
    only = set(a.only.split(',')) if a.only else None
    segs = {k: [] for k in COLORS}
    texts, inserts = [], []
    for d in D['items']:
        if a.area and d.get('area') != a.area: continue
        cat = category(a.file, d['lay'])
        if only and cat not in only: continue
        if d['t'] == 'INSERT':
            x, y = d['ins']
            if x0 <= x <= x1 and y0 <= y <= y1 and cat in ('door', 'window', 'jamb', 'glass') or (
                    x0 <= x <= x1 and y0 <= y <= y1 and any(k in d['name'].upper() for k in ('1D', 'LEAF', 'SWING', 'JAMB', 'FRAME', 'DOOR', 'WIN'))):
                inserts.append(d)
            continue
        if 'text' in d:
            x, y = d['ins']
            if x0 <= x <= x1 and y0 <= y <= y1 and d['text']: texts.append(d)
            continue
        polys = [d['pts']] if 'pts' in d else d.get('loops', [])
        for p in polys:
            if not p: continue
            xs = [q[0] for q in p]; ys = [q[1] for q in p]
            if max(xs) < x0 or min(xs) > x1 or max(ys) < y0 or min(ys) > y1: continue
            pp = p + [p[0]] if (d.get('closed') or 'loops' in d) and len(p) > 2 else p
            segs[cat].extend(zip(pp, pp[1:]))
    w, h = x1 - x0, y1 - y0
    s = a.px / max(w, h)
    fig = plt.figure(figsize=(w * s / 100 + 1.2, h * s / 100 + 1.0), dpi=100)
    ax = fig.add_axes([0.6 / (w * s / 100 + 1.2), 0.5 / (h * s / 100 + 1.0), (w * s / 100) / (w * s / 100 + 1.2), (h * s / 100) / (h * s / 100 + 1.0)])
    g = a.grid
    for gx in [math.floor(x0 / g) * g + i * g for i in range(int(w / g) + 2)]:
        if x0 <= gx <= x1: ax.axvline(gx, color='#f0d9b0', lw=0.5, zorder=0)
    for gy in [math.floor(y0 / g) * g + i * g for i in range(int(h / g) + 2)]:
        if y0 <= gy <= y1: ax.axhline(gy, color='#f0d9b0', lw=0.5, zorder=0)
    for cat in ('other', 'stair', 'jamb', 'window', 'glass', 'door', 'wall'):
        if segs[cat]:
            c, lw = COLORS[cat]
            ax.add_collection(LineCollection(segs[cat], colors=c, linewidths=lw, zorder={'other': 1}.get(cat, 2)))
    for d in texts if a.text else []:
        ax.text(d['ins'][0], d['ins'][1], d['text'][:40], fontsize=6, color='#555', zorder=4)
    for d in inserts if a.inserts else []:
        ax.plot(*d['ins'], marker='+', color='#ff7f00', ms=6, zorder=5)
        ax.text(d['ins'][0], d['ins'][1], f" {d['name']}", fontsize=5.5, color='#ff7f00', zorder=5)
    for i, m in enumerate(a.mark, 1):
        parts = m.split(',')
        mx, my = float(parts[0]), float(parts[1]); lab = parts[2] if len(parts) > 2 else str(i)
        ax.plot(mx, my, marker='o', mfc='none', mec='#ff00aa', ms=14, mew=1.5, zorder=6)
        ax.text(mx, my, f'  {lab}', fontsize=8, color='#ff00aa', weight='bold', zorder=6)
    ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_aspect('equal')
    step = g if w / g <= 40 else g * math.ceil(w / g / 40)
    ax.set_xticks([math.ceil(x0 / step) * step + i * step for i in range(int(w / step) + 1) if math.ceil(x0 / step) * step + i * step <= x1])
    ax.set_yticks([math.ceil(y0 / step) * step + i * step for i in range(int(h / step) + 1) if math.ceil(y0 / step) * step + i * step <= y1])
    ax.tick_params(labelsize=6); plt.setp(ax.get_xticklabels(), rotation=90)
    ax.set_title(f'{a.file} {a.area or ""}  x {x0:.1f}-{x1:.1f}  y {y0:.1f}-{y1:.1f} m   black wall, cyan glass, blue window, red door, magenta jamb, green stair', fontsize=7)
    fig.savefig(a.out); plt.close(fig)
    print(a.out)


if __name__ == '__main__':
    main()
