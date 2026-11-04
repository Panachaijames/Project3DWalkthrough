import json, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
d = json.load(open('house3d_pdf.json'))
STYLE = {'wall': ('#d9d4cc', 1.0, '#8a857c'), 'glass': ('#9fd8e6', 0.35, '#5aa9bd'),
         'window': ('#9fd8e6', 0.35, '#5aa9bd'), 'stair': ('#7fbf7f', 1.0, '#3d7a3d')}
def quads(floor, cat):
    z0 = d['levels'][floor]; z1 = d['tops'][floor]
    if cat == 'stair': z1 = z0 + 0.15
    if cat == 'window': z0, z1 = z0 + 0.0, z1 - 0.6
    return [[(x1, y1, z0), (x2, y2, z0), (x2, y2, z1), (x1, y1, z1)] for x1, y1, x2, y2 in d['segments'].get(f'{floor}:{cat}', [])]
for name, floors, elev, azim in (('pdf_preview_both.png', ('ground', 'upper'), 32, -60), ('pdf_preview_ground.png', ('ground',), 50, -60)):
    fig = plt.figure(figsize=(14, 8), dpi=110); ax = fig.add_subplot(111, projection='3d')
    for f in floors:
        for cat, (fc, al, ec) in STYLE.items():
            q = quads(f, cat)
            if q: ax.add_collection3d(Poly3DCollection(q, facecolors=fc, edgecolors=ec, linewidths=0.15, alpha=al))
    ax.set_xlim(-19, 19); ax.set_ylim(-12, 12); ax.set_zlim(0, 10); ax.set_box_aspect((38, 24, 10))
    ax.view_init(elev=elev, azim=azim); ax.set_axis_off()
    fig.savefig(name, bbox_inches='tight', facecolor='white'); plt.close(fig); print('saved', name)
