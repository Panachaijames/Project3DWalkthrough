"""Draw a plan from its cache (prims.pkl), with chosen layers in colour over everything else in light grey.

For deciding layer roles only (the drawing itself, never the detector's output).
Usage: python -B render_layers.py <prims.pkl> <out.png> <x0> <y0> <x1> <y1> LAYER[=colour] [LAYER[=colour] ...]
          [--px N] [--grid G] [--nobg] [--text] [--depth0 | --depthB]
  coordinates in drawing metres (DXF mm / 1000); a LAYER may be a glob pattern ('A-DOOR*'); '--depth0' draws only top-level
  items of the chosen layers, '--depthB' only items inside blocks.
"""
import argparse, fnmatch, math, pickle
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection

PAL = ['#e01b1b', '#1f4fff', '#139a3a', '#ff7f00', '#b000b0', '#00a5c8', '#8b5a00', '#111111', '#e6007e', '#6a6a00']


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('pkl'); ap.add_argument('out')
    for k in ('x0', 'y0', 'x1', 'y1'): ap.add_argument(k, type=float)
    ap.add_argument('layers', nargs='+')
    ap.add_argument('--px', type=int, default=3000); ap.add_argument('--grid', type=float, default=1.0)
    ap.add_argument('--nobg', action='store_true'); ap.add_argument('--text', action='store_true')
    ap.add_argument('--depth0', action='store_true'); ap.add_argument('--depthB', action='store_true')
    ap.add_argument('--lw', type=float, default=0.8)
    a = ap.parse_args()
    D = pickle.load(open(a.pkl, 'rb'))
    sel = []
    for i, s in enumerate(a.layers):
        nm, _, col = s.partition('=')
        sel.append((nm.upper(), col or PAL[i % len(PAL)], nm))
    x0, y0, x1, y1 = a.x0, a.y0, a.x1, a.y1
    bg, fg = [], {nm: [] for _, _, nm in sel}
    texts = []

    def pick(lay):
        U = lay.upper()
        for p, col, nm in sel:
            if fnmatch.fnmatchcase(U, p): return nm
        return None

    for d in D['items']:
        nm = pick(d['lay'])
        if nm and a.depth0 and d['depth'] > 0: nm = None
        if nm and a.depthB and d['depth'] == 0: nm = None
        if 'text' in d:
            if a.text and d.get('text') and x0 <= d['ins'][0] <= x1 and y0 <= d['ins'][1] <= y1: texts.append(d)
            continue
        polys = [d['pts']] if 'pts' in d else d.get('loops', [])
        for p in polys:
            if not p: continue
            xs = [q[0] for q in p]; ys = [q[1] for q in p]
            if max(xs) < x0 or min(xs) > x1 or max(ys) < y0 or min(ys) > y1: continue
            pp = p + [p[0]] if (d.get('closed') or 'loops' in d) and len(p) > 2 else p
            segs = list(zip(pp, pp[1:])) if len(pp) > 1 else [(pp[0], (pp[0][0] + 0.01, pp[0][1]))]
            (fg[nm] if nm else bg).extend(segs)
    w, h = x1 - x0, y1 - y0
    s = a.px / max(w, h)
    fig = plt.figure(figsize=(w * s / 100 + 1.2, h * s / 100 + 1.0), dpi=100)
    ax = fig.add_axes([0.6 / (w * s / 100 + 1.2), 0.5 / (h * s / 100 + 1.0), (w * s / 100) / (w * s / 100 + 1.2), (h * s / 100) / (h * s / 100 + 1.0)])
    g = a.grid
    for gx in [math.floor(x0 / g) * g + i * g for i in range(int(w / g) + 2)]:
        if x0 <= gx <= x1: ax.axvline(gx, color='#f0d9b0', lw=0.5, zorder=0)
    for gy in [math.floor(y0 / g) * g + i * g for i in range(int(h / g) + 2)]:
        if y0 <= gy <= y1: ax.axhline(gy, color='#f0d9b0', lw=0.5, zorder=0)
    if bg and not a.nobg: ax.add_collection(LineCollection(bg, colors='#c8c8c8', linewidths=0.35, zorder=1))
    for p, col, nm in sel:
        if fg[nm]: ax.add_collection(LineCollection(fg[nm], colors=col, linewidths=a.lw, zorder=2))
    for d in texts: ax.text(d['ins'][0], d['ins'][1], d['text'][:40], fontsize=6, color='#555', zorder=4)
    ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_aspect('equal')
    step = g if w / g <= 40 else g * math.ceil(w / g / 40)
    ax.set_xticks([math.ceil(x0 / step) * step + i * step for i in range(int(w / step) + 1) if math.ceil(x0 / step) * step + i * step <= x1])
    ax.set_yticks([math.ceil(y0 / step) * step + i * step for i in range(int(h / step) + 1) if math.ceil(y0 / step) * step + i * step <= y1])
    ax.tick_params(labelsize=6); plt.setp(ax.get_xticklabels(), rotation=90)
    ax.set_title('  '.join(f'{nm}={col}' for _, col, nm in sel) + f'   x {x0:.1f}-{x1:.1f} y {y0:.1f}-{y1:.1f} m', fontsize=7)
    fig.savefig(a.out); plt.close(fig)
    print(a.out, {nm: len(v) for nm, v in fg.items()}, 'bg', len(bg))


if __name__ == '__main__':
    main()
