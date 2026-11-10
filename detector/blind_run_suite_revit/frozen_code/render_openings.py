"""Top-view PNG of one floor with every detected opening marked (kind by colour, id labelled), for a human check.

Doors red, windows blue, passages green; a thick bar on the wall centre line from a to b, the id beside it.
The wall solid the detector used is grey; the rest of the drawing is light line work.
"""
import math
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.patches import PathPatch
from matplotlib.path import Path as MPath
from geomkit import polys

KIND_COL = {'door': '#d7191c', 'window': '#2c7bb6', 'passage': '#1a9641'}


def _patch(ax, p, **kw):
    verts, codes = [], []
    for ring in [p.exterior] + list(p.interiors):
        cs = list(ring.coords)
        if len(cs) < 3: continue
        verts += cs; codes += [MPath.MOVETO] + [MPath.LINETO] * (len(cs) - 2) + [MPath.CLOSEPOLY]
    if verts: ax.add_patch(PathPatch(MPath(verts, codes), **kw))


def draw(fl, res, path, key=None, box=None, px=3200, title=None):
    W = fl.W
    segs, lays = [], []
    for p in fl.P:
        if p.pts and len(p.pts) > 1:
            pts = p.pts + ([p.pts[0]] if p.closed else [])
            segs += list(zip(pts, pts[1:]))
    if box is None:
        xs = [q[0] for p in polys(W) for q in p.exterior.coords] + [c for o in res for c in (o['a'][0], o['b'][0])]
        ys = [q[1] for p in polys(W) for q in p.exterior.coords] + [c for o in res for c in (o['a'][1], o['b'][1])]
        if not xs: return
        box = (min(xs) - 1, min(ys) - 1, max(xs) + 1, max(ys) + 1)
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    s = px / max(w, h)
    fig = plt.figure(figsize=(w * s / 100, h * s / 100 + 0.4), dpi=100)
    ax = fig.add_axes([0, 0, 1, h * s / 100 / (h * s / 100 + 0.4)])
    segs = [sg for sg in segs if not (max(sg[0][0], sg[1][0]) < x0 or min(sg[0][0], sg[1][0]) > x1 or max(sg[0][1], sg[1][1]) < y0 or min(sg[0][1], sg[1][1]) > y1)]
    ax.add_collection(LineCollection(segs, colors='#c8c8c8', linewidths=0.35, zorder=1))
    for p in polys(W): _patch(ax, p, facecolor='#9a9a9a', edgecolor='#555', lw=0.4, zorder=2)
    fs = max(5, min(9, 900 / max(w, h)))
    if key:
        for o in key:
            col = '#ff9900' if not o.get('optional') else '#ffd27f'
            ax.plot([o['a'][0], o['b'][0]], [o['a'][1], o['b'][1]], color=col, lw=9, alpha=0.45, solid_capstyle='butt', zorder=3)
            mx, my = (o['a'][0] + o['b'][0]) / 2, (o['a'][1] + o['b'][1]) / 2
            ax.text(mx, my, ' ' + str(o.get('id')), fontsize=fs * 0.8, color='#b36b00', zorder=6, va='top')
    for o in res:
        col = KIND_COL.get(o['kind'], 'k')
        ax.plot([o['a'][0], o['b'][0]], [o['a'][1], o['b'][1]], color=col, lw=3.2, solid_capstyle='butt', zorder=4)
        for e in (o['a'], o['b']):
            ax.plot(*e, marker='|', color=col, ms=7, zorder=5)
        mx, my = (o['a'][0] + o['b'][0]) / 2, (o['a'][1] + o['b'][1]) / 2
        ax.text(mx, my, ' ' + o['id'] + ('?' if o.get('eitherKind') else ''), fontsize=fs, color=col, weight='bold', zorder=6, va='bottom')
    ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_aspect('equal'); ax.axis('off')
    n = {k: sum(1 for o in res if o['kind'] == k) for k in KIND_COL}
    fig.text(0.01, 0.995, (title or fl.name) + f"   doors {n['door']} (red), windows {n['window']} (blue), passages {n['passage']} (green)"
             + ('   key: orange (optional pale)' if key else ''), fontsize=10, va='top')
    fig.savefig(path)
    plt.close(fig)
    return path
