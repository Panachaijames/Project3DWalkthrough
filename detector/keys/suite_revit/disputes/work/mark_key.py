"""Draw the answer key of the suite_revit drawing over the plan: one marked picture for checking the key by eye.

  python -B mark_key.py [out.png]          (default: key_marked.png next to this file)

Reads ../../suite_revit.json and prims.pkl from $OPENINGS_DATA/suite_revit. The plan is drawn faintly (walls, columns,
curtain wall, door layers); on it every key opening is a thick a-b segment with its id: scored door red, scored passage
green, optional door orange (dashed), optional passage light green (dashed), optional window blue (dashed). Glass walls of
the key are thin cyan lines, rejected places black crosses with their id. No detector output is read or drawn.
"""
import json, os, pickle, sys
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection, PolyCollection

HERE = Path(__file__).resolve().parent
key = json.load(open(HERE.parent.parent / 'suite_revit.json', encoding='utf-8'))
D = pickle.load(open(Path(os.environ['OPENINGS_DATA']) / 'suite_revit' / 'prims.pkl', 'rb'))
out = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / 'key_marked.png'

PLAN = {'A-WALL': '#555555', '0': '#c9a58c', 'S-COLS': '#555555', 'A-GLAZ-CURT': '#7fc8dc', 'A-GLAZ-CWMG': '#9ab9b9',
        'A-DOOR': '#e8a0a0', 'A-DOOR-FRAM': '#d9a0d9', 'A-DOOR-HDLN': '#e8a0a0'}
x0, y0, x1, y1 = 1.0, -0.5, 26.0, 13.6
s = 120                                                  # pixels per metre
W, H = (x1 - x0) * s / 100 + 1.2, (y1 - y0) * s / 100 + 1.4
fig = plt.figure(figsize=(W, H), dpi=100)
ax = fig.add_axes([0.6 / W, 0.7 / H, (x1 - x0) * s / 100 / W, (y1 - y0) * s / 100 / H])
segs, fills = {}, {}
for d in D['items']:
    if d['lay'] not in PLAN or d['t'] == 'INSERT' or 'text' in d: continue
    polys = [d['pts']] if 'pts' in d else d.get('loops', [])
    for p in polys:
        if len(p) < 2: continue
        if d['t'] == 'HATCH' and d.get('solid') and len(p) > 2: fills.setdefault(d['lay'], []).append(p)
        pp = p + [p[0]] if (d.get('closed') or 'loops' in d) and len(p) > 2 else p
        segs.setdefault(d['lay'], []).extend(zip(pp, pp[1:]))
for lay, c in PLAN.items():
    if lay in fills: ax.add_collection(PolyCollection(fills[lay], facecolors=c, edgecolors='none', alpha=0.35, zorder=1))
    if lay in segs: ax.add_collection(LineCollection(segs[lay], colors=c, linewidths=0.5, zorder=2))
for g in key['glassWalls']:
    if 'only mark' in g.get('notes', ''): continue       # the bays' entries give only the extent of a row of facets
    ax.plot([g['a'][0], g['b'][0]], [g['a'][1], g['b'][1]], color='#00b5d8', lw=0.8, zorder=3)
STY = {('door', False): ('#d00000', '-'), ('passage', False): ('#008a00', '-'), ('window', False): ('#0040ff', '-'),
       ('door', True): ('#ff8c00', '--'), ('passage', True): ('#5ccf5c', '--'), ('window', True): ('#3f7fff', '--')}
for o in key['openings']:
    c, ls = STY[(o['kind'], bool(o.get('optional')))]
    ax.plot([o['a'][0], o['b'][0]], [o['a'][1], o['b'][1]], color=c, lw=3.2, ls=ls, solid_capstyle='butt', zorder=5)
    for p in (o['a'], o['b']):
        ax.plot(*p, marker='|', color=c, ms=6, zorder=6)
    cx, cy = (o['a'][0] + o['b'][0]) / 2, (o['a'][1] + o['b'][1]) / 2
    ax.text(cx, cy, ' ' + o['id'] + (' (opt)' if o.get('optional') else ''), fontsize=6.5, color=c, zorder=7,
            weight='bold', bbox=dict(boxstyle='square,pad=0.05', fc='white', ec='none', alpha=0.7))
for r in key['rejected']:
    ax.plot(*r['where'], marker='x', color='black', ms=7, mew=1.6, zorder=6)
    ax.text(r['where'][0], r['where'][1] - 0.18, r['id'].split(' ')[0], fontsize=5.5, color='black', zorder=7)
ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_aspect('equal')
ax.set_xticks(range(2, 26)); ax.set_yticks(range(0, 14)); ax.tick_params(labelsize=7, top=True, right=True, labeltop=True, labelright=True)
ax.grid(color='#eadbc0', lw=0.4, zorder=0)
n_sc = sum(1 for o in key['openings'] if not o.get('optional'))
ax.set_title(f'suite_revit answer key: {len(key["openings"])} openings, {n_sc} scored (solid: door red, passage green), '
             f'{len(key["openings"]) - n_sc} optional (dashed: door orange, passage light green, window blue); '
             'glass walls cyan; x = rejected place', fontsize=9)
fig.savefig(out)
print(out)
