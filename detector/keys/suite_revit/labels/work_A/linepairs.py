"""Parallel layer-0 / A-WALL line pairs (6-25 cm apart, overlap >= 0.4 m) whose middle strip is NOT covered by a wall fill:
candidates for walls drawn with lines only (screens, kerbs, furniture)."""
import sys; sys.path.insert(0, '.')
from load import *
from shapely.geometry import Polygon, LineString, Point
from shapely.ops import unary_union
D = load()
SKIP = {'4FF1', '502C', '4FD2'}
fills = []
for d in D['items']:
    if d['lay'] in ('0', 'A-WALL', 'S-COLS') and d['t'] in ('HATCH', 'SOLID') and d['h'] not in SKIP:
        for L in (d.get('loops') or [d['pts']]):
            if len(L) >= 3:
                P = Polygon(L).buffer(0)
                if P.area > 1e-5: fills.append(P)
F = unary_union(fills).buffer(0.003)
segs = []
for d in D['items']:
    if d['lay'] not in ('0', 'A-WALL') or d['t'] not in ('LINE', 'LWPOLYLINE'): continue
    P = d['pts']
    for i in range(len(P) - 1):
        a, b = P[i], P[i + 1]
        if math.dist(a, b) < 0.4: continue
        ang = math.degrees(math.atan2(b[1] - a[1], b[0] - a[0])) % 180
        if min(ang % 90, 90 - ang % 90) > 0.5: continue        # axis-aligned only
        segs.append((d['h'], a, b, round(ang) % 180, d.get('lt')))
out = []
for i in range(len(segs)):
    for j in range(i + 1, len(segs)):
        hi, a1, b1, g1, lt1 = segs[i]; hj, a2, b2, g2, lt2 = segs[j]
        if g1 != g2: continue
        if g1 == 0:   # horizontal
            dy = abs(a1[1] - a2[1]);
            lo = max(min(a1[0], b1[0]), min(a2[0], b2[0])); hi_ = min(max(a1[0], b1[0]), max(a2[0], b2[0]))
            if not (0.06 <= dy <= 0.25) or hi_ - lo < 0.4: continue
            mid = LineString([(lo, (a1[1] + a2[1]) / 2), (hi_, (a1[1] + a2[1]) / 2)])
        else:
            dx = abs(a1[0] - a2[0]);
            lo = max(min(a1[1], b1[1]), min(a2[1], b2[1])); hi_ = min(max(a1[1], b1[1]), max(a2[1], b2[1]))
            if not (0.06 <= dx <= 0.25) or hi_ - lo < 0.4: continue
            mid = LineString([((a1[0] + a2[0]) / 2, lo), ((a1[0] + a2[0]) / 2, hi_)])
        unc = mid.difference(F)
        if unc.length < 0.3: continue
        out.append((round(unc.length, 2), hi, hj, [round(v, 3) for v in mid.coords[0]], [round(v, 3) for v in mid.coords[-1]], lt1, lt2))
for r in sorted(out, key=lambda r: (r[3][1], r[3][0])): print(*r)
print(len(out))
