"""Labeller C, step 7: list every item (all layers) that has a vertex or crosses into a box. Usage: c07_box.py x0 y0 x1 y1 [layers,...]"""
import pickle, sys, math
from shapely.geometry import box, LineString, Point, Polygon
P = 'C:/Users/DWP2/AppData/Local/Temp/claude/1a2f3fc736ce552c/e1e2f8a1-5b17-462a-bbe8-01925d989674/scratchpad/suite_revit_work/suite_revit/prims.pkl'
D = pickle.load(open(P, 'rb'))
x0, y0, x1, y1 = map(float, sys.argv[1:5])
lays = set(sys.argv[5].split(',')) if len(sys.argv) > 5 else None
B = box(x0, y0, x1, y1)
for d in D['items']:
    if lays and d['lay'] not in lays: continue
    if d['t'] == 'INSERT':
        if B.contains(Point(d['ins'])): print(f"INSERT {d['lay']} {d['name'][:60]} at ({d['ins'][0]:.4f},{d['ins'][1]:.4f}) rot {d['rot']}")
        continue
    if 'text' in d:
        if B.contains(Point(d['ins'])): print(f"TEXT {d['lay']} {d['text'][:40]!r} at {d['ins']}")
        continue
    if 'pts' in d:
        p = d['pts']
        g = LineString(p) if len(p) > 1 else Point(p[0])
        if not g.intersects(B): continue
        if d['t'] in ('ARC', 'CIRCLE', 'ELLIPSE', 'SPLINE') or len(p) > 6:
            xs = [q[0] for q in p]; ys = [q[1] for q in p]
            print(f"{d['t']:10} {d['lay']:12} h {d['h']:5} n {len(p)} bbox x {min(xs):.4f}-{max(xs):.4f} y {min(ys):.4f}-{max(ys):.4f} first ({p[0][0]:.4f},{p[0][1]:.4f}) last ({p[-1][0]:.4f},{p[-1][1]:.4f}) lt {d.get('lt')} closed {d.get('closed')} {d['path'][:25]}")
        else:
            s = ' '.join(f'({x:.4f},{y:.4f})' for x, y in p)
            L = sum(math.dist(a, b) for a, b in zip(p, p[1:]))
            print(f"{d['t']:10} {d['lay']:12} h {d['h']:5} L {L:.3f} {s} lt {d.get('lt')} {'closed' if d.get('closed') else ''} {d['path'][:25]}")
    elif 'loops' in d:
        for lp in d['loops']:
            g = Polygon(lp) if len(lp) > 2 else None
            if g is None or not g.buffer(0).intersects(B): continue
            xs = [q[0] for q in lp]; ys = [q[1] for q in lp]
            print(f"HATCH      {d['lay']:12} h {d['h']:5} x {min(xs):.4f}-{max(xs):.4f} y {min(ys):.4f}-{max(ys):.4f} n {len(lp)} {d['path'][:25]}")
