"""Labeller C, step 9: wall-layer lines (A-WALL, layer 0) longer than 0.3 m that do NOT lie on the boundary of the wall
fills: candidates for walls drawn without fill, lines carried across openings (heads, thresholds, core lines), glass,
and furniture. Prints each with how much of it is off the fill boundary."""
import pickle, math, sys
import shapely
from shapely.geometry import Polygon, LineString
from shapely.ops import unary_union
P = 'C:/Users/DWP2/AppData/Local/Temp/claude/1a2f3fc736ce552c/e1e2f8a1-5b17-462a-bbe8-01925d989674/scratchpad/suite_revit_work/suite_revit/prims.pkl'
D = pickle.load(open(P, 'rb'))
EXCL = {'4FF1', '502C', '4E08', '4E09'}
polys = []
for d in D['items']:
    if d['t'] == 'HATCH' and d['lay'] in ('0', 'A-WALL', 'S-COLS') and d['h'] not in EXCL:
        for lp in d['loops']:
            if len(lp) > 2:
                p = Polygon(lp).buffer(0)
                if p.area > 1e-6: polys.append(p)
W = unary_union(polys)
Wfat = W.buffer(0.002)
lay = sys.argv[1] if len(sys.argv) > 1 else 'A-WALL'
minL = float(sys.argv[2]) if len(sys.argv) > 2 else 0.3
box = [float(v) for v in sys.argv[3].split(',')] if len(sys.argv) > 3 else None
for d in D['items']:
    if d['lay'] != lay or 'pts' not in d or d['t'] not in ('LINE', 'LWPOLYLINE'): continue
    p = d['pts']
    for a, b in zip(p, p[1:] + ([p[0]] if d.get('closed') else [])):
        L = math.dist(a, b)
        if L < minL: continue
        if box and not (box[0] <= min(a[0], b[0]) and max(a[0], b[0]) <= box[2] and box[1] <= min(a[1], b[1]) and max(a[1], b[1]) <= box[3]): continue
        s = LineString([a, b])
        off = s.difference(Wfat).length
        inside = s.intersection(W.buffer(-0.002)).length
        if off > 0.05 or inside > 0.05:
            print(f"{d['t']:10} {lay} h {d['h']:5} ({a[0]:.4f},{a[1]:.4f})-({b[0]:.4f},{b[1]:.4f}) L {L:.3f} off-fill {off:.3f} inside-fill {inside:.3f} lt {d.get('lt')}")
