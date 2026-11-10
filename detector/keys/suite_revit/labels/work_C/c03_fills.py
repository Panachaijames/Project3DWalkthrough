"""Labeller C, step 3: every wall-layer fill (HATCH on layer 0, A-WALL, S-COLS) as a polygon: bbox, area,
thickness (min rotated-rectangle side), direction. These are the wall solids; their ends bound the openings."""
import pickle, math, collections
from shapely.geometry import Polygon
from shapely.ops import unary_union
P = 'C:/Users/DWP2/AppData/Local/Temp/claude/1a2f3fc736ce552c/e1e2f8a1-5b17-462a-bbe8-01925d989674/scratchpad/suite_revit_work/suite_revit/prims.pkl'
D = pickle.load(open(P, 'rb'))
items = D['items']
rows = []
for d in items:
    if d['t'] != 'HATCH' or d['lay'] not in ('0', 'A-WALL', 'S-COLS', 'A-GLAZ-CWMG'): continue
    for lp in d['loops']:
        if len(lp) < 3: continue
        p = Polygon(lp).buffer(0)
        if p.is_empty: continue
        r = p.minimum_rotated_rectangle
        cs = list(r.exterior.coords)
        e1 = math.dist(cs[0], cs[1]); e2 = math.dist(cs[1], cs[2])
        if e1 >= e2: L, T, ang = e1, e2, math.degrees(math.atan2(cs[1][1]-cs[0][1], cs[1][0]-cs[0][0])) % 180
        else: L, T, ang = e2, e1, math.degrees(math.atan2(cs[2][1]-cs[1][1], cs[2][0]-cs[1][0])) % 180
        x0, y0, x1, y1 = p.bounds
        rows.append(dict(lay=d['lay'], h=d['h'], path=d['path'], x0=x0, y0=y0, x1=x1, y1=y1, L=L, T=T, ang=ang,
                         area=p.area, rect=abs(p.area - r.area) < 1e-6 + 0.01 * r.area, n=len(lp)))
print('fill loops', len(rows), collections.Counter(r['lay'] for r in rows))
for r in sorted(rows, key=lambda r: (r['lay'], round(r['y0'], 2), r['x0'])):
    print(f"{r['lay']:11} h {r['h']:5} x {r['x0']:7.3f}-{r['x1']:7.3f} y {r['y0']:7.3f}-{r['y1']:7.3f} L {r['L']:6.3f} T {r['T']:6.3f} ang {r['ang']:6.1f} "
          f"{'rect' if r['rect'] else 'poly'} n {r['n']} {r['path'][:30]}")
