"""Labeller C, step 8: curtain-wall bays. For each glazed panel insert (A-GLAZ-CURT): the pane lines (ends, direction),
the mullion boxes (A-GLAZ-CWMG closed 50x100 boxes) at its ends, and the wall pieces (A-WALL fills) that touch it."""
import pickle, math, collections
from shapely.geometry import Polygon, LineString, Point, MultiPoint
from shapely.ops import unary_union
P = 'C:/Users/DWP2/AppData/Local/Temp/claude/1a2f3fc736ce552c/e1e2f8a1-5b17-462a-bbe8-01925d989674/scratchpad/suite_revit_work/suite_revit/prims.pkl'
D = pickle.load(open(P, 'rb'))
items = D['items']
walls = []
for d in items:
    if d['t'] == 'HATCH' and d['lay'] in ('A-WALL', 'S-COLS', '0'):
        for lp in d['loops']:
            if len(lp) > 2:
                p = Polygon(lp).buffer(0)
                if p.area > 1e-5: walls.append((d['lay'], d['h'], p))
panes = collections.defaultdict(list)
for d in items:
    if d['lay'] == 'A-GLAZ-CURT' and d['t'] == 'LINE':
        panes[(d['h'], d['path'])].append(d['pts'])
for (h, path), segs in sorted(panes.items(), key=lambda kv: kv[0][0]):
    pts = [q for s in segs for q in s]
    long = [s for s in segs if math.dist(s[0], s[-1]) > 0.05]
    ang = math.degrees(math.atan2(long[0][-1][1] - long[0][0][1], long[0][-1][0] - long[0][0][0])) % 180
    u = (math.cos(math.radians(ang)), math.sin(math.radians(ang)))
    # pane extent along u, centre line
    proj = [q[0] * u[0] + q[1] * u[1] for q in pts]
    perp = [-q[0] * u[1] + q[1] * u[0] for q in pts]
    t0, t1 = min(proj), max(proj); n0, n1 = min(perp), max(perp)
    nm = (n0 + n1) / 2
    A = (t0 * u[0] - nm * u[1], t0 * u[1] + nm * u[0]); B = (t1 * u[0] - nm * u[1], t1 * u[1] + nm * u[0])
    # march outward along the pane's centre line to the first wall material on each side
    def march(P0, s):
        for k in range(0, 400):
            dd = k * 0.0025
            q = Point(P0[0] + s * u[0] * dd, P0[1] + s * u[1] * dd)
            for lay, hh, p in walls:
                if p.buffer(0.0005).contains(q): return dd, lay, hh
        return None, None, None
    da, la, ha = march(A, -1); db, lb, hb = march(B, 1)
    print(f"pane h {h} {path[:40]} ang {ang:6.2f} len {t1 - t0:.4f} thick {n1 - n0:.4f}  A ({A[0]:.4f},{A[1]:.4f}) B ({B[0]:.4f},{B[1]:.4f})")
    if da is not None and db is not None:
        WA = (A[0] - u[0] * da, A[1] - u[1] * da); WB = (B[0] + u[0] * db, B[1] + u[1] * db)
        print(f"      wall faces: ({WA[0]:.4f},{WA[1]:.4f}) [{la} {ha}, {da:.4f} from pane end]  ({WB[0]:.4f},{WB[1]:.4f}) [{lb} {hb}, {db:.4f}]  width {math.dist(WA, WB):.4f}")
    else:
        print('      wall faces: not found', da, db)
