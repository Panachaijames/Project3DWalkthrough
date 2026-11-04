"""Close-up check of the lift core: old per-segment boxes vs new merged solids."""
import json, math
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection, Line3DCollection

NEW = json.load(open('srisawan3d_merged.json', encoding='utf-8'))
OLD = json.load(open('srisawan3d.json', encoding='utf-8'))
COL = {'wall': '#dcd8cf', 'core': '#9ea8af', 'envelope': '#d2cdc3', 'glass': '#7dc2d3'}

# zoom window: the floor-2 core, in the merged file's (re-centred) coordinates
core = [p for r in NEW['solids']['L2:core'] for p in r['o']]
x0, x1 = min(p[0] for p in core) - 3, max(p[0] for p in core) + 3
y0, y1 = min(p[1] for p in core) - 3, max(p[1] for p in core) + 3

def in_win(x, y):
    return x0 <= x <= x1 and y0 <= y <= y1

def draw_new(ax):
    z0, h = NEW['levels']['L2'], NEW['heights']['L2']
    for kind in ('core', 'wall', 'envelope'):
        faces, tops = [], []
        for r in NEW['solids'].get(f'L2:{kind}', []):
            for ring in [r['o']] + r['h']:
                if not any(in_win(*p) for p in ring):
                    continue
                n = len(ring)
                for i in range(n):
                    (ax_, ay), (bx, by) = ring[i], ring[(i + 1) % n]
                    faces.append([(ax_, ay, z0), (bx, by, z0), (bx, by, z0 + h), (ax_, ay, z0 + h)])
                    tops.append([(ax_, ay, z0 + h), (bx, by, z0 + h)])
        if faces:
            ax.add_collection3d(Poly3DCollection(faces, facecolors=COL[kind], edgecolors='none', alpha=1))
            ax.add_collection3d(Line3DCollection(tops, colors='#3c4248', linewidths=0.9))

def draw_old(ax):
    # old boxes were centred differently: shift them onto the merged frame using the core bounds
    oc = [(b[0], b[1]) for b in OLD['boxes']['L2:core']] + [(b[2], b[3]) for b in OLD['boxes']['L2:core']]
    nc = [(s[0], s[1]) for s in NEW['segments']['L2:core']] + [(s[2], s[3]) for s in NEW['segments']['L2:core']]
    dx = min(p[0] for p in nc) - min(p[0] for p in oc); dy = min(p[1] for p in nc) - min(p[1] for p in oc)
    for kind in ('core', 'wall', 'envelope'):
        faces, tops = [], []
        for x1_, y1_, x2_, y2_, t, z0, h in OLD['boxes'].get(f'L2:{kind}', []):
            x1_, y1_, x2_, y2_ = x1_ + dx, y1_ + dy, x2_ + dx, y2_ + dy
            if not (in_win(x1_, y1_) or in_win(x2_, y2_)):
                continue
            L = math.hypot(x2_ - x1_, y2_ - y1_); ox, oy = -(y2_ - y1_) / L * t / 2, (x2_ - x1_) / L * t / 2
            p = [(x1_ - ox, y1_ - oy), (x2_ - ox, y2_ - oy), (x2_ + ox, y2_ + oy), (x1_ + ox, y1_ + oy)]
            for i in range(4):
                (a1, a2), (b1, b2) = p[i], p[(i + 1) % 4]
                faces.append([(a1, a2, z0), (b1, b2, z0), (b1, b2, z0 + h), (a1, a2, z0 + h)])
                tops.append([(a1, a2, z0 + h), (b1, b2, z0 + h)])
        if faces:
            ax.add_collection3d(Poly3DCollection(faces, facecolors=COL[kind], edgecolors='none'))
            ax.add_collection3d(Line3DCollection(tops, colors='#3c4248', linewidths=0.9))

fig = plt.figure(figsize=(16, 7.5), dpi=100)
for i, (title, fn) in enumerate((('Before: one box per traced segment', draw_old), ('After: merged walls', draw_new))):
    ax = fig.add_subplot(1, 2, i + 1, projection='3d')
    fn(ax)
    ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_zlim(5, 9.5)
    ax.set_box_aspect((x1 - x0, y1 - y0, 4.5)); ax.view_init(elev=55, azim=-70); ax.set_axis_off()
    ax.set_title(title, fontsize=13)
fig.savefig('core_before_after.png', bbox_inches='tight', facecolor='white')
print('saved core_before_after.png')
