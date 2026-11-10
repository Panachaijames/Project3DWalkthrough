"""For each door swing arc (A-DOOR, A-DOOR-HDLN) of the drawing cache, look for a layer-0 line lying along either radius
of the arc (the leaf's open or closed position), i.e. a line drawn across the doorway on layer 0.

Reads the drawing cache only (prims.pkl), never the detector's output.
Usage: python -B door_lines_on_0.py <prims.pkl> [tolerance in m, default 0.02]
"""
import math, pickle, sys
TOL = float(sys.argv[2]) if len(sys.argv) > 2 else 0.02     # m: how far off the leaf position a layer-0 line may lie


def circle3(p0, p1, p2):
    bx, by = p1[0] - p0[0], p1[1] - p0[1]
    cx, cy = p2[0] - p0[0], p2[1] - p0[1]
    d = 2 * (bx * cy - by * cx)
    if abs(d) < 1e-12: return None
    b2, c2 = bx * bx + by * by, cx * cx + cy * cy
    ux = (cy * b2 - by * c2) / d
    uy = (bx * c2 - cx * b2) / d
    return (p0[0] + ux, p0[1] + uy), math.hypot(ux, uy)


def cover(seg, line, tol=TOL, ang=3.0):
    """Fraction of segment seg covered by line (parallel within ang degrees, within tol of it)."""
    (ax, ay), (bx, by) = seg
    L = math.hypot(bx - ax, by - ay)
    ux, uy = (bx - ax) / L, (by - ay) / L
    (px, py), (qx, qy) = line
    l2 = math.hypot(qx - px, qy - py)
    if l2 < 1e-6: return 0.0
    c = abs(ux * (qx - px) / l2 + uy * (qy - py) / l2)
    if c < math.cos(math.radians(ang)): return 0.0
    for x, y in ((px, py), (qx, qy)):
        if abs(-uy * (x - ax) + ux * (y - ay)) > tol: return 0.0
    s0, s1 = sorted(((px - ax) * ux + (py - ay) * uy, (qx - ax) * ux + (qy - ay) * uy))
    return max(0.0, min(L, s1) - max(0.0, s0)) / L


def main():
    D = pickle.load(open(sys.argv[1], 'rb'))
    lines0 = []
    for d in D['items']:
        if d['lay'] == '0' and d['t'] in ('LINE', 'LWPOLYLINE', 'POLYLINE') and 'pts' in d:
            P = d['pts'] + ([d['pts'][0]] if d.get('closed') else [])
            lines0 += list(zip(P, P[1:]))
    n, hits = 0, []
    for d in D['items']:
        if d['t'] != 'ARC' or d['lay'] not in ('A-DOOR', 'A-DOOR-HDLN') or len(d.get('pts', [])) < 3: continue
        P = d['pts']
        c = circle3(P[0], P[len(P) // 2], P[-1])
        if not c: continue
        C, r = c
        if not 0.28 <= r <= 2.0: continue
        n += 1
        best = []
        for end in (P[0], P[-1]):
            seg = (C, end)
            f = sum(cover(seg, ln) for ln in lines0)
            best.append(round(min(f, 9.99), 2))
        hits.append((round(C[0], 2), round(C[1], 2), round(r, 3), d['lay'], best))
    print(f'door-size arcs on A-DOOR / A-DOOR-HDLN: {n}')
    print('hinge x, y | radius | layer | layer-0 cover of radius to each arc end (1.0 = a layer-0 line along the whole leaf position)')
    for h in sorted(hits): print('  ', h)
    k = sum(1 for h in hits if max(h[4]) >= 0.8)
    print(f'arcs with a layer-0 line along 80 % or more of one leaf position: {k} of {n}')


if __name__ == '__main__':
    main()
