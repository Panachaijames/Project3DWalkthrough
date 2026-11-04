import json, math, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection, Line3DCollection
D = json.load(open('srisawan3d.json', encoding='utf-8'))
COL = {'wall': '#dcd8cf', 'core': '#9ea8af', 'envelope': '#dcd8cf', 'glass': '#7dc2d3'}
def box_faces(b):
    x1, y1, x2, y2, t, z0, h = b
    dx, dy = x2 - x1, y2 - y1; L = math.hypot(dx, dy); ox, oy = -dy / L * t / 2, dx / L * t / 2
    p = [(x1 - ox, y1 - oy), (x2 - ox, y2 - oy), (x2 + ox, y2 + oy), (x1 + ox, y1 + oy)]
    lo = [(x, y, z0) for x, y in p]; hi = [(x, y, z0 + h) for x, y in p]
    return [hi] + [[lo[i], lo[(i+1) % 4], hi[(i+1) % 4], hi[i]] for i in range(4)]
for name, floors in (('check_both.png', ('L1', 'L2')), ('check_L2.png', ('L2',)), ('check_F6.png', ('F6',))):
    fig = plt.figure(figsize=(15, 9), dpi=100); ax = fig.add_subplot(111, projection='3d')
    for f in floors:
        if f in D['slabs']:
            sl = D['slabs'][f]; z = sl['z'] + 0.25
            ax.add_collection3d(Poly3DCollection([[(x, y, z) for x, y in sl['outer']]], facecolors='#b9c1c6', alpha=0.55, edgecolors='#7d868c', linewidths=0.4))
            if sl['holes']: ax.add_collection3d(Line3DCollection([[(x, y, z + 0.02) for x, y in h + h[:1]] for h in sl['holes']], colors='#1f8a4c', linewidths=1.2))
        for kind in ('wall', 'envelope', 'core', 'glass'):
            bx = D['boxes'].get(f'{f}:{kind}', [])
            faces = [fc for b in bx for fc in box_faces(b)]
            if faces: ax.add_collection3d(Poly3DCollection(faces, facecolors=COL[kind], edgecolors='#6f6a61' if kind != 'glass' else '#4f9fb3', linewidths=0.12, alpha=0.35 if kind == 'glass' else 1.0))
    W, H = (D['size6'] if floors == ('F6',) else D['size'])
    ax.set_xlim(-W/2, W/2); ax.set_ylim(-H/2, H/2); ax.set_zlim(-1, 10); ax.set_box_aspect((W, H, 11))
    ax.view_init(elev=38, azim=-62); ax.set_axis_off()
    fig.savefig(name, bbox_inches='tight', facecolor='white'); plt.close(fig); print('saved', name)
