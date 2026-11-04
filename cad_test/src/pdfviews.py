import pymupdf, matplotlib, collections
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
doc = pymupdf.open('show.pdf'); page = doc[9]
def cat(layer, width):
    L = (layer or '').split('|')[-1].upper()
    if L in ('A-WALL', 'A-WALL-FULL', 'A-COLUMN', 'A-COLUMN-FULL'): return '#d62728' if width >= 0.7 else '#f2b8b8'
    if L in ('A-DW', 'I-DOOR', 'A-WALL-JAMB-DOOR'): return '#1f5fd6'
    if L == 'I-STAIR': return '#2ca02c'
    if L.startswith('I-FURN') or L in ('I-TOIL-NEWW', 'I-BLIND', 'I-FD'): return '#ff7f0e'
    return '#bdbdbd'
lines = collections.defaultdict(list)
for d in page.get_drawings():
    c = cat(d.get('layer'), d.get('width') or 0)
    for it in d['items']:
        if it[0] == 'l': lines[c].append([(it[1].x, -it[1].y), (it[2].x, -it[2].y)])
        elif it[0] == 'c': lines[c].append([(it[1].x, -it[1].y), (it[4].x, -it[4].y)])
        elif it[0] == 're':
            r = it[1]; p = [r.tl, r.tr, r.br, r.bl]; lines[c] += [[(p[i].x, -p[i].y), (p[(i+1)%4].x, -p[(i+1)%4].y)] for i in range(4)]
        elif it[0] == 'qu':
            q = it[1]; p = [q.ul, q.ur, q.lr, q.ll]; lines[c] += [[(p[i].x, -p[i].y), (p[(i+1)%4].x, -p[(i+1)%4].y)] for i in range(4)]
fig = plt.figure(figsize=(16, 11.3), dpi=110); ax = fig.add_axes([0, 0, 1, 1]); ax.set_aspect('equal'); ax.axis('off')
for c in ('#bdbdbd', '#f2b8b8', '#ff7f0e', '#2ca02c', '#1f5fd6', '#d62728'):
    ax.add_collection(LineCollection(lines[c], colors=c, linewidths=1.1 if c == '#d62728' else 0.5))
r = page.rect; ax.set_xlim(0, r.width); ax.set_ylim(-r.height, 0)
fig.savefig('pdf_ground_categories.png', dpi=110, facecolor='white'); plt.close(fig); print('saved pdf_ground_categories.png')
