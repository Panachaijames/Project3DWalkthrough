"""Labeller C, step 5: find every gap in the wall solid geometrically.
Wall material W = union of the fills on layer 0 (minus two furniture fills, two specks and the 10 mm glass pane),
A-WALL and S-COLS. For each fill piece at least 40 mm thick, march along its axis from each end through W: skip the
material that continues the wall, then measure the first stretch with no material in the wall's band, up to 3.5 m.
A gap is kept when material resumes within 3.5 m (wall end -> wall end in line, or wall end -> side of another wall).
Output: gaps with both ends on the wall centre line, the band test used, and what bounds the far end."""
import pickle, math, json, sys
import numpy as np
import shapely
from shapely.geometry import Polygon, Point, LineString
from shapely.ops import unary_union
P = 'C:/Users/DWP2/AppData/Local/Temp/claude/1a2f3fc736ce552c/e1e2f8a1-5b17-462a-bbe8-01925d989674/scratchpad/suite_revit_work/suite_revit/prims.pkl'
D = pickle.load(open(P, 'rb'))
EXCL = {'4FF1', '502C', '4E08', '4E09', '4DEB'}   # sofa back fill, sofa frame fill, two 5 mm specks, 10 mm glass pane
polys = []
for d in D['items']:
    if d['t'] != 'HATCH' or d['lay'] not in ('0', 'A-WALL', 'S-COLS'): continue
    if d['h'] in EXCL and d['lay'] == '0': continue
    for lp in d['loops']:
        if len(lp) < 3: continue
        p = Polygon(lp).buffer(0)
        if p.is_empty or p.area < 1e-5: continue
        polys.append((d['lay'], d['h'], p))
W = unary_union([p for _, _, p in polys])
Wb = W.buffer(0.0005)          # 0.5 mm tolerance: pieces that touch are one
shapely.prepare(Wb)
def inside(xs, ys): return shapely.contains_xy(Wb, xs, ys)
gaps = []
STEP = 0.0025
for lay, h, p in polys:
    r = p.minimum_rotated_rectangle
    cs = list(r.exterior.coords)[:4]
    e1 = (cs[1][0] - cs[0][0], cs[1][1] - cs[0][1]); e2 = (cs[2][0] - cs[1][0], cs[2][1] - cs[1][1])
    l1, l2 = math.hypot(*e1), math.hypot(*e2)
    if l1 >= l2: L, T, u = l1, l2, (e1[0] / l1, e1[1] / l1)
    else: L, T, u = l2, l1, (e2[0] / l2, e2[1] / l2)
    if T < 0.04 or L < 0.05: continue
    v = (-u[1], u[0])
    c = r.centroid.coords[0]
    offs = np.array([-0.3 * T, 0.0, 0.3 * T])
    for s in (1, -1):
        e = (c[0] + s * u[0] * L / 2, c[1] + s * u[1] * L / 2)
        d = np.arange(-0.01, 3.5, STEP)
        X = e[0] + s * u[0] * d[:, None] + v[0] * offs[None, :]
        Y = e[1] + s * u[1] * d[:, None] + v[1] * offs[None, :]
        ins = inside(X.ravel(), Y.ravel()).reshape(X.shape)
        anyin = ins.any(axis=1)        # some of the band is wall
        allout = ~anyin
        # skip material contiguous with the piece
        k = 0
        while k < len(d) and anyin[k]: k += 1
        if k >= len(d): continue
        g0 = d[k]
        if g0 > 0.03: continue          # the wall goes on past this piece's end through other material: that piece's end is tested itself
        k2 = k
        while k2 < len(d) and allout[k2]: k2 += 1
        if k2 >= len(d): continue        # open end: no material within 3.5 m
        g1 = d[k2]
        a = (e[0] + s * u[0] * g0, e[1] + s * u[1] * g0); b = (e[0] + s * u[0] * g1, e[1] + s * u[1] * g1)
        hit = ins[k2]
        gaps.append(dict(lay=lay, h=h, T=round(T, 3), ang=round(math.degrees(math.atan2(u[1], u[0])) % 180, 2),
                         a=[round(a[0], 4), round(a[1], 4)], b=[round(b[0], 4), round(b[1], 4)], w=round(g1 - g0, 4),
                         hitband=''.join('1' if x else '0' for x in hit)))
# dedupe: same gap found from both ends
out = []
for g in sorted(gaps, key=lambda g: g['w']):
    dup = False
    for o in out:
        ca = ((g['a'][0] + g['b'][0]) / 2, (g['a'][1] + g['b'][1]) / 2); co = ((o['a'][0] + o['b'][0]) / 2, (o['a'][1] + o['b'][1]) / 2)
        if math.dist(ca, co) < 0.06 and abs(g['w'] - o['w']) < 0.06 and min(abs(g['ang'] - o['ang']), 180 - abs(g['ang'] - o['ang'])) < 5:
            dup = True; o.setdefault('also', []).append(g['h']); break
    if not dup: out.append(g)
out.sort(key=lambda g: (round(min(g['a'][1], g['b'][1]), 1), min(g['a'][0], g['b'][0])))
for i, g in enumerate(out, 1):
    print(f"G{i:02d} {g['lay']:7} h {g['h']:5} T {g['T']:.3f} ang {g['ang']:6.2f}  a ({g['a'][0]:.4f},{g['a'][1]:.4f}) b ({g['b'][0]:.4f},{g['b'][1]:.4f}) w {g['w']:.4f}  far-band {g['hitband']} also {g.get('also', [])}")
json.dump(out, open(sys.argv[1], 'w'), indent=1)
