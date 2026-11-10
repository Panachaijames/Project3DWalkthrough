"""List every cache item (prims.pkl) that touches a box: type, layer, handle, linetype, extent and points.

  python -B q.py x0,y0,x1,y1 [--layers 0,A-WALL] [--max 40]

Reads prims.pkl from $OPENINGS_DATA/suite_revit (the WORK folder of drawing.json). Items are sorted by layer and position.
HATCH items print each loop's bounding box (and its vertices when it has at most 8); lines and polylines print their
points (at most 8, else the extent). Coordinates are drawing metres (DXF mm / 1000).
"""
import os, pickle, sys
from pathlib import Path

args = sys.argv[1:]
layers = None
mx = 40
if '--layers' in args:
    i = args.index('--layers'); layers = set(args[i + 1].split(',')); del args[i:i + 2]
if '--max' in args:
    i = args.index('--max'); mx = int(args[i + 1]); del args[i:i + 2]
x0, y0, x1, y1 = (float(v) for v in args[0].split(','))
D = pickle.load(open(Path(os.environ['OPENINGS_DATA']) / 'suite_revit' / 'prims.pkl', 'rb'))


def pts(d):
    return d.get('pts') or [q for l in d.get('loops', []) for q in l] or ([d['ins']] if 'ins' in d else [])


def touches(P):
    if not P: return False
    xs = [p[0] for p in P]; ys = [p[1] for p in P]
    return min(xs) <= x1 and max(xs) >= x0 and min(ys) <= y1 and max(ys) >= y0


def fmt(P):
    return ' '.join(f'({p[0]:.4f},{p[1]:.4f})' for p in P)


rows = []
for d in D['items']:
    if layers and d['lay'] not in layers: continue
    P = pts(d)
    if not touches(P): continue
    xs = [p[0] for p in P]; ys = [p[1] for p in P]
    rows.append((d['lay'], round(min(xs), 3), round(min(ys), 3), d, P))
rows.sort(key=lambda r: (r[0], r[1], r[2]))
print(f'{len(rows)} items touch x {x0}..{x1}, y {y0}..{y1}')
for lay, _, _, d, P in rows:
    xs = [p[0] for p in P]; ys = [p[1] for p in P]
    head = f"{lay:12} {d['t']:10} h={d.get('h')} {('path=' + d['path'][:40]) if d.get('path') else ''} lt={d.get('lt', '')}"
    ext = f"x {min(xs):.4f}..{max(xs):.4f}  y {min(ys):.4f}..{max(ys):.4f}"
    if 'loops' in d:
        print(head, 'solid' if d.get('solid') else d.get('pattern', ''), ext)
        for l in d['loops']:
            lx = [p[0] for p in l]; ly = [p[1] for p in l]
            print(f"      loop x {min(lx):.4f}..{max(lx):.4f}  y {min(ly):.4f}..{max(ly):.4f}" + (f"  {fmt(l)}" if len(l) <= 8 else f'  ({len(l)} vertices)'))
    elif d['t'] in ('INSERT', 'TEXT', 'MTEXT', 'ATTRIB'):
        print(head, d.get('name', d.get('text', ''))[:70], f"ins ({d['ins'][0]:.4f},{d['ins'][1]:.4f})", f"rot {d.get('rot', '')}")
    else:
        print(head, ext, fmt(P) if len(P) <= 8 else f'({len(P)} points, closed={d.get("closed")})')
    mx -= 1
    if mx <= 0:
        print('... (more; raise --max)'); break
