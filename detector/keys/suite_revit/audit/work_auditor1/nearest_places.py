"""auditor1 helper: distance from each opening noticed near the places (segment between its ends) to the nearest place segment."""
import json, math
from pathlib import Path
P = json.loads(Path(__file__).resolve().parent.parent.joinpath('places.json').read_text(encoding='utf-8'))['places']

def pd(p, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]; L2 = dx * dx + dy * dy
    t = 0 if L2 == 0 else max(0, min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L2))
    return math.hypot(p[0] - a[0] - t * dx, p[1] - a[1] - t * dy)

def sd(a, b, c, d):   # segment-segment distance (no crossing among these)
    return min(pd(a, c, d), pd(b, c, d), pd(c, a, b), pd(d, a, b))

N = {'N1 WC glass door': ((9.517, 5.351), (9.517, 6.051)), 'N2 east-room glass door': ((23.002, 4.775), (23.702, 4.775)),
     'N3 shower glass door (south)': ((9.517, 7.165), (9.517, 7.865)), 'N4 shower glass door (north)': ((9.517, 9.434), (9.517, 10.134)),
     'N5 D22-V25 service double door': ((23.987, 1.159), (25.787, 1.159)), 'N6 D22-2804302 service double door': ((23.987, 3.259), (25.787, 3.259)),
     'N7 dressing-area open side': ((7.554, 3.259), (9.387, 3.259)), 'lobby / bedroom 2 open side': ((20.612, 6.924), (22.737, 6.924))}
for k, (a, b) in N.items():
    ds = sorted((sd(a, b, p['ends'][0], p['ends'][1]), p['place']) for p in P)
    print(f'{k:38s} nearest: ' + ', '.join(f'{n} {d:.2f} m' for d, n in ds[:3]))
