"""The result of the held-out run drawn over the plan: ../result_marked.png (step 7 of 7).

  OPENINGS_DATA=<WORK> python -B blind_run_suite_revit/diagnosis/mark_result.py [out.png]     (Git Bash, from detector/)

Reads the audited key, the score against it (../score_first_mapping_audited.json) and, for the two ends of the eight
detections the key does not list, the audit's secret map. The plan is drawn faintly (walls, columns, curtain wall,
door layers). Scored key openings: green = right, orange = found but not right, red = missed. Detections the key does
not list: purple. Optional key entries (not counted either way): thin blue when a detection matches them, thin grey
dashed when none does.
"""
import json, os, pickle, sys
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection, PolyCollection
from matplotlib.lines import Line2D

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
RUN = HERE.parent
DETECTOR = RUN.parent
key = json.load(open(DETECTOR / 'keys' / 'suite_revit' / 'suite_revit_audited.json', encoding='utf-8'))
sc = json.load(open(RUN / 'score_first_mapping_audited.json', encoding='utf-8'))['floors']['suite_revit']
secret = json.load(open(DETECTOR / 'keys' / 'suite_revit' / 'audit' / 'secret_map.json', encoding='utf-8'))['places']
D = pickle.load(open(Path(os.environ['OPENINGS_DATA']) / 'suite_revit' / 'prims.pkl', 'rb'))
out = Path(sys.argv[1]) if len(sys.argv) > 1 else RUN / 'result_marked.png'

RIGHT, WRONG, MISSED, EXTRA, OPT_FOUND, OPT_NOT = '#0a8f2a', '#f08c00', '#d00000', '#8a2be2', '#3f7fff', '#8c8c8c'
PLAN = {'A-WALL': '#555555', '0': '#c9a58c', 'S-COLS': '#555555', 'A-GLAZ-CURT': '#7fc8dc', 'A-GLAZ-CWMG': '#9ab9b9',
        'A-DOOR': '#e8a0a0', 'A-DOOR-FRAM': '#d9a0d9', 'A-DOOR-HDLN': '#e8a0a0'}
x0, y0, x1, y1 = 1.0, -0.5, 26.0, 13.6
s = 120                                                  # pixels per metre
W, H = (x1 - x0) * s / 100 + 1.2, (y1 - y0) * s / 100 + 2.3
fig = plt.figure(figsize=(W, H), dpi=100)
ax = fig.add_axes([0.6 / W, 1.6 / H, (x1 - x0) * s / 100 / W, (y1 - y0) * s / 100 / H])
segs, fills = {}, {}
for d in D['items']:
    if d['lay'] not in PLAN or d['t'] == 'INSERT' or 'text' in d: continue
    for p in ([d['pts']] if 'pts' in d else d.get('loops', [])):
        if len(p) < 2: continue
        if d['t'] == 'HATCH' and d.get('solid') and len(p) > 2: fills.setdefault(d['lay'], []).append(p)
        pp = p + [p[0]] if (d.get('closed') or 'loops' in d) and len(p) > 2 else p
        segs.setdefault(d['lay'], []).extend(zip(pp, pp[1:]))
for lay, c in PLAN.items():
    if lay in fills: ax.add_collection(PolyCollection(fills[lay], facecolors=c, edgecolors='none', alpha=0.35, zorder=1))
    if lay in segs: ax.add_collection(LineCollection(segs[lay], colors=c, linewidths=0.5, zorder=2))

pairs = {p['key']: p for p in sc['pairs']}
missed = {m['key'] for m in sc['missed']}
opt_found = {x['key'] for x in sc['optionalFound']}


def seg(a, b, c, lw, ls='-', z=5):
    ax.plot([a[0], b[0]], [a[1], b[1]], color=c, lw=lw, ls=ls, solid_capstyle='butt', zorder=z)


def label(a, b, text, c, dy=0.0, size=7.0):
    ax.text((a[0] + b[0]) / 2, (a[1] + b[1]) / 2 + dy, ' ' + text, fontsize=size, color=c, zorder=8, weight='bold',
            bbox=dict(boxstyle='square,pad=0.05', fc='white', ec='none', alpha=0.75))


n = {'right': 0, 'wrong': 0, 'missed': 0}
for o in key['openings']:
    a, b = o['a'], o['b']
    if o.get('optional'):
        f = o['id'] in opt_found
        seg(a, b, OPT_FOUND if f else OPT_NOT, 1.6, '-' if f else '--', 4)
        continue
    if o['id'] in missed:
        c, what = MISSED, 'missed'; n['missed'] += 1
    elif pairs[o['id']]['right']:
        c, what = RIGHT, ''; n['right'] += 1
    else:
        p = pairs[o['id']]
        c, what = WRONG, f"found {p['widthDet']:.2f} m, key {p['widthKey']:.2f} m"; n['wrong'] += 1
    seg(a, b, c, 4.0)
    for q in (a, b): ax.plot(*q, marker='|', color=c, ms=7, zorder=6)
    label(a, b, o['id'] + (' ' + what if what else ''), c)
extras = [v['detection'] for v in secret.values() if v['source'] == 'detector extra']
assert len(extras) == len(sc['extra'])
scored_mid = [((o['a'][0] + o['b'][0]) / 2, (o['a'][1] + o['b'][1]) / 2) for o in key['openings'] if not o.get('optional')]
for d in extras:
    seg(d['a'], d['b'], EXTRA, 2.6, '-', 6)
    m = ((d['a'][0] + d['b'][0]) / 2, (d['a'][1] + d['b'][1]) / 2)
    crowded = any(abs(m[0] - q[0]) < 0.6 and 0 < m[1] - q[1] < 0.45 for q in scored_mid)     # a scored opening just below: label above
    label(d['a'], d['b'], f"{d['id'].split('-')[-1]} {d['kind']} {d['width']:.2f} m", EXTRA, dy=0.2 if crowded else -0.22, size=6.3)
ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_aspect('equal')
ax.set_xticks(range(2, 26)); ax.set_yticks(range(0, 14)); ax.tick_params(labelsize=7, top=True, right=True, labeltop=True, labelright=True)
ax.grid(color='#eadbc0', lw=0.4, zorder=0)
ax.set_title(f"Held-out run on 'presidential suite_layout.dwg' (frozen detector, 10 Nov 2026): {n['right']} of {sc['keyCount']} scored "
             f"openings right, {n['wrong']} found but not right, {n['missed']} missed; {len(extras)} detections the key does not list",
             fontsize=10)
fig.legend([Line2D([0], [0], color=RIGHT, lw=4), Line2D([0], [0], color=WRONG, lw=4), Line2D([0], [0], color=MISSED, lw=4),
            Line2D([0], [0], color=EXTRA, lw=2.6), Line2D([0], [0], color=OPT_FOUND, lw=1.6), Line2D([0], [0], color=OPT_NOT, lw=1.6, ls='--')],
           ['scored key opening: right', 'scored key opening: found, width not right', 'scored key opening: missed',
            'detection the key does not list (all eight judged not an opening by both auditors)',
            'optional key entry with a detection (glass-screen doors, cropped riser doors, curtain-wall facets): not counted',
            'optional key entry with no detection: not counted'],
           loc='lower left', ncol=2, fontsize=8, frameon=False, bbox_to_anchor=(0.6 / W, 0.15 / H))
fig.savefig(out)
print(out)
