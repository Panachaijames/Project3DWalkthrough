"""Curtain-wall panes (A-GLAZ-CURT blocks): for each pane block, its long lines (the glass faces), centre line ends and length."""
import sys; sys.path.insert(0, '.')
from load import *
D = load()
blocks = {}
for d in D['items']:
    if d['lay'] == 'A-GLAZ-CURT' and d['t'] == 'LINE':
        blocks.setdefault(d['h'], []).append(d['pts'])
rows = []
for name, L in blocks.items():
    longs = [p for p in L if math.dist(p[0], p[-1]) > 0.05]
    # the two faces: take the longest line and the one parallel to it
    longs.sort(key=lambda p: -math.dist(p[0], p[-1]))
    a = longs[0]
    # centre line: average of the two longest lines (matched ends)
    b = longs[1]
    if math.dist(a[0], b[0]) > math.dist(a[0], b[-1]): b = b[::-1]
    c0 = ((a[0][0] + b[0][0]) / 2, (a[0][1] + b[0][1]) / 2); c1 = ((a[-1][0] + b[-1][0]) / 2, (a[-1][1] + b[-1][1]) / 2)
    ang = math.degrees(math.atan2(c1[1] - c0[1], c1[0] - c0[0])) % 180
    rows.append((round(min(c0[0], c1[0]), 3), name, [round(v, 4) for v in c0], [round(v, 4) for v in c1], round(math.dist(c0, c1), 4), round(ang, 1), round(math.dist(a[0], b[0]), 4)))
for r in sorted(rows): print(*r[1:])
print()
# mullion boxes and wedges: list A-GLAZ-CWMG blocks' extents, and Walls 13 hatch loops
mb = {}
for d in D['items']:
    if d['lay'] == 'A-GLAZ-CWMG' and d['t'] in ('LINE', 'HATCH'):
        mb.setdefault(d['h'], []).extend(pts(d))
for name, P in sorted(mb.items(), key=lambda kv: (min(p[0] for p in kv[1]), min(p[1] for p in kv[1]))):
    xs = [p[0] for p in P]; ys = [p[1] for p in P]
    print('CWMG', name, [round(min(xs), 3), round(min(ys), 3), round(max(xs), 3), round(max(ys), 3)])
