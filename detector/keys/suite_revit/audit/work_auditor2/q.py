"""auditor2 helper: list drawing items (from the flattened cache prims.pkl) near a point or in a box.

Usage (Git Bash, from this folder):
  python -B q.py box  x0 y0 x1 y1 [--lay L1,L2] [--skip L1,L2] [--min LEN]
  python -B q.py near x  y  r       [--lay ...]   [--skip ...]
Coordinates are drawing metres. Prints one row per item: type, layer, linetype, and its points (lines) or bbox.
Reads only the drawing cache; no detector output.
"""
import os, sys, pickle, math, argparse
from pathlib import Path

WORK = Path(os.environ.get('OPENINGS_DATA', r'C:/Users/DWP2/AppData/Local/Temp/claude/1a2f3fc736ce552c/e1e2f8a1-5b17-462a-bbe8-01925d989674/scratchpad/suite_revit_work'))
D = pickle.load(open(WORK / 'suite_revit' / 'prims.pkl', 'rb'))
ITEMS = D['items']


def pts_of(d):
    if 'pts' in d: return [d['pts']]
    if 'loops' in d: return d['loops']
    if 'ins' in d: return [[d['ins']]]
    return []


def seg_dist(p, a, b):
    ax, ay = a; bx, by = b; px, py = p
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    t = 0 if L2 == 0 else max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / L2))
    return math.hypot(ax + t * dx - px, ay + t * dy - py)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('mode'); ap.add_argument('args', nargs='+', type=float)
    ap.add_argument('--lay'); ap.add_argument('--skip'); ap.add_argument('--min', type=float, default=0.0)
    ap.add_argument('--full', action='store_true')
    a = ap.parse_args()
    lay = set(a.lay.split(',')) if a.lay else None
    skip = set(a.skip.split(',')) if a.skip else set()
    rows = []
    for d in ITEMS:
        if lay and d['lay'] not in lay: continue
        if d['lay'] in skip: continue
        polys = pts_of(d)
        if not polys: continue
        allp = [q for p in polys for q in p]
        xs = [q[0] for q in allp]; ys = [q[1] for q in allp]
        if a.mode == 'box':
            x0, y0, x1, y1 = a.args
            if max(xs) < x0 or min(xs) > x1 or max(ys) < y0 or min(ys) > y1: continue
            key = (round(min(xs), 3), round(min(ys), 3))
        else:
            x, y, r = a.args
            dmin = 1e9
            for p in polys:
                if len(p) == 1: dmin = min(dmin, math.hypot(p[0][0] - x, p[0][1] - y))
                closed = d.get('closed') or 'loops' in d
                pp = p + [p[0]] if closed and len(p) > 2 else p
                for u, v in zip(pp, pp[1:]): dmin = min(dmin, seg_dist((x, y), u, v))
            if dmin > r: continue
            key = (round(dmin, 3),)
        length = 0.0
        for p in polys:
            length += sum(math.hypot(v[0] - u[0], v[1] - u[1]) for u, v in zip(p, p[1:]))
        if length < a.min and d['t'] not in ('INSERT', 'TEXT', 'MTEXT', 'ATTRIB', 'HATCH'): continue
        rows.append((key, d, xs, ys, length))
    rows.sort(key=lambda r: r[0])
    for key, d, xs, ys, length in rows:
        lt = d.get('lt', '')
        lt = '' if lt in ('BYLAYER', 'ByLayer', '') else f' lt={lt}'
        extra = ''
        if d['t'] == 'INSERT':
            extra = f" name={d.get('name')} ins=({d['ins'][0]:.3f},{d['ins'][1]:.3f}) rot={d.get('rot')}"
        elif 'text' in d:
            extra = f" text={d['text'][:40]!r}"
        elif d['t'] == 'LINE' or (len(d.get('pts', [])) == 2):
            p = d['pts']
            extra = f" ({p[0][0]:.4f},{p[0][1]:.4f})-({p[1][0]:.4f},{p[1][1]:.4f}) len={length:.4f}"
        else:
            extra = f" bbox x {min(xs):.4f}-{max(xs):.4f} y {min(ys):.4f}-{max(ys):.4f} n={len(xs)} len={length:.3f}"
            if d['t'] == 'HATCH': extra += f" solid={d.get('solid')} loops={len(d['loops'])}"
            if a.full and 'pts' in d: extra += ' pts=' + ' '.join(f'({q[0]:.4f},{q[1]:.4f})' for q in d['pts'])
            if a.full and 'loops' in d: extra += ' loops=' + ' | '.join(' '.join(f'({q[0]:.4f},{q[1]:.4f})' for q in l) for l in d['loops'])
        dep = f" d{d.get('depth')}" if d.get('depth') else ''
        print(f"{'/'.join(str(k) for k in key):>14} {d['t']:<10} {d['lay']:<14}{dep}{lt}{extra}")


if __name__ == '__main__':
    main()
