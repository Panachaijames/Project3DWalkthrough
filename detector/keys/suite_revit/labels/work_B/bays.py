"""Labeller B: the curtain-wall facets of the six bays, measured from the drawing cache.

For every curtain panel (A-GLAZ-CURT insert 'System Panel - GLAZED-...'): the pane is the two 10 mm lines; its centre
line runs between the two 10 mm end lines. A facet runs from solid face to solid face: the pane plus a 50 mm mullion
box (A-GLAZ-CWMG 'Rectangular Mullion - 100X50-2447682/83', four lines) at each end where one touches the pane end.
The facet's ends are then checked against the A-WALL pieces (wall ends, the 'Walls 13' corner wedges): each end must
lie on (within 5 mm of) an A-WALL outline. Prints a, b (midpoints of the end faces), width, direction.
"""
import math, pickle, sys
from collections import defaultdict

PKL = 'C:/Users/DWP2/AppData/Local/Temp/claude/1a2f3fc736ce552c/e1e2f8a1-5b17-462a-bbe8-01925d989674/scratchpad/suite_revit_work/suite_revit/prims.pkl'
D = pickle.load(open(PKL, 'rb'))
items = D['items']


def seg_dist(p, a, b):
    ax, ay = a; bx, by = b; px, py = p
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    t = 0 if L2 == 0 else max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / L2))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


# panes: group A-GLAZ-CURT lines by their top-level handle (one panel per insert)
panels = defaultdict(list)
for d in items:
    if d['lay'] == 'A-GLAZ-CURT' and d['t'] == 'LINE' and d.get('path'):
        panels[d['h']].append(d['pts'])
# mullion boxes: 4-line blocks 'Rectangular Mullion - 100X50-2447682/83'
boxes = defaultdict(list)
for d in items:
    if d['lay'] == 'A-GLAZ-CWMG' and d['t'] == 'LINE' and ('2447682' in d['path'] or '2447683' in d['path']):
        boxes[d['h']].append(d['pts'])
box_polys = []
for h, segs in boxes.items():
    pts = [tuple(p) for s in segs for p in s]
    box_polys.append((h, segs, pts))
# A-WALL outline segments (lines + hatch loops), for the end check
wall_segs = []
for d in items:
    if d['lay'] != 'A-WALL':
        continue
    if d['t'] == 'LINE' or 'pts' in d:
        P = d['pts']
        wall_segs += list(zip(P, P[1:]))
    elif d['t'] == 'HATCH':
        for l in d['loops']:
            wall_segs += list(zip(l, l[1:] + l[:1]))

facets = []
for h, segs in panels.items():
    longs = [s for s in segs if math.dist(*s) > 0.05]
    shorts = [s for s in segs if math.dist(*s) <= 0.05]
    if len(longs) != 2 or len(shorts) != 2:
        print('skip panel', h, len(longs), len(shorts)); continue
    e0 = ((shorts[0][0][0] + shorts[0][1][0]) / 2, (shorts[0][0][1] + shorts[0][1][1]) / 2)
    e1 = ((shorts[1][0][0] + shorts[1][1][0]) / 2, (shorts[1][0][1] + shorts[1][1][1]) / 2)
    L = math.dist(e0, e1)
    ux, uy = (e1[0] - e0[0]) / L, (e1[1] - e0[1]) / L
    ends = []
    for e, sgn in ((e0, -1), (e1, 1)):
        # a mullion box touching this pane end: one of its corners within 0.08 of the pane end
        ext = 0.0
        for bh, bsegs, bpts in box_polys:
            if min(math.dist(e, p) for p in bpts) < 0.08:
                # only a box in line with the pane: every corner within 51 mm of the pane line, beyond this end
                proj = [((p[0] - e[0]) * ux + (p[1] - e[1]) * uy) * sgn for p in bpts]
                lat = [abs(-(p[0] - e[0]) * uy + (p[1] - e[1]) * ux) for p in bpts]
                if max(lat) <= 0.051 and min(proj) >= -0.001 and max(proj) <= 0.06:
                    ext = max(ext, max(proj))
        q = (e[0] + sgn * ext * ux, e[1] + sgn * ext * uy)
        dwall = min(seg_dist(q, a, b) for a, b in wall_segs)
        ends.append((q, ext, dwall))
    (a, xa, da), (b, xb, db) = ends
    w = math.dist(a, b)
    ang = math.degrees(math.atan2(b[1] - a[1], b[0] - a[0])) % 180
    facets.append((a, b, w, ang, L, xa, xb, da, db, h))

for a, b, w, ang, L, xa, xb, da, db, h in sorted(facets, key=lambda f: ((f[0][0] + f[1][0]) / 2)):
    print(f"panel h={h} pane {L:.4f}  facet a=({a[0]:.4f},{a[1]:.4f}) b=({b[0]:.4f},{b[1]:.4f}) width={w:.4f} dir={ang:.2f} "
          f"box ext {xa:.3f}/{xb:.3f} end-to-wall {da*1000:.1f}/{db*1000:.1f} mm")
