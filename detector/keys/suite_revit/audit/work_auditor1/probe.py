"""auditor1 helper: list the cache items (prims.pkl) that touch a box, with their geometry, for judging places.

Usage: python -B probe.py x0 y0 x1 y1 [--layers L1,L2] [--skip L1,L2] [--maxpts N]
Reads OPENINGS_DATA/suite_revit/prims.pkl (the flattened drawing). Prints layer, type, linetype and points (m).
"""
import os, sys, pickle, argparse
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument('x0', type=float); ap.add_argument('y0', type=float); ap.add_argument('x1', type=float); ap.add_argument('y1', type=float)
ap.add_argument('--layers'); ap.add_argument('--skip'); ap.add_argument('--maxpts', type=int, default=8)
a = ap.parse_args()
D = pickle.load(open(Path(os.environ['OPENINGS_DATA']) / 'suite_revit' / 'prims.pkl', 'rb'))
lay_ok = set(a.layers.split(',')) if a.layers else None
skip = set(a.skip.split(',')) if a.skip else set()

def touches(pts):
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    return not (max(xs) < a.x0 or min(xs) > a.x1 or max(ys) < a.y0 or min(ys) > a.y1)

rows = []
for d in D['items']:
    if lay_ok and d['lay'] not in lay_ok: continue
    if d['lay'] in skip: continue
    if d['t'] == 'INSERT':
        x, y = d['ins']
        if a.x0 <= x <= a.x1 and a.y0 <= y <= a.y1:
            rows.append((d['lay'], 'INSERT', '', f"{d['name']} ins=({x:.3f},{y:.3f}) rot={d.get('rot')}"))
        continue
    if 'text' in d:
        x, y = d['ins']
        if a.x0 <= x <= a.x1 and a.y0 <= y <= a.y1: rows.append((d['lay'], d['t'], '', f"'{d['text']}' at ({x:.3f},{y:.3f})"))
        continue
    if 'loops' in d:
        for L in d['loops']:
            if L and touches(L):
                xs = [p[0] for p in L]; ys = [p[1] for p in L]
                pts = ' '.join(f'({p[0]:.3f},{p[1]:.3f})' for p in L[:a.maxpts]) + (' ...' if len(L) > a.maxpts else '')
                rows.append((d['lay'], 'HATCH', d.get('path', ''), f"bbox x {min(xs):.3f}-{max(xs):.3f} y {min(ys):.3f}-{max(ys):.3f} n={len(L)} {pts}"))
        continue
    p = d.get('pts')
    if p and touches(p):
        pts = ' '.join(f'({q[0]:.3f},{q[1]:.3f})' for q in p[:a.maxpts]) + (' ...' if len(p) > a.maxpts else '')
        rows.append((d['lay'], d['t'], d.get('lt', ''), f"{'closed ' if d.get('closed') else ''}n={len(p)} {pts}" + (f" path={d['path'][:50]}" if d.get('path') else '')))
rows.sort()
for r in rows: print(' | '.join(str(v) for v in r))
print(len(rows), 'items')
