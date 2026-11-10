"""Labeller B helper: list the drawing items (prims.pkl of suite_revit) that touch a box.

  python -B q.py x0 y0 x1 y1 [--lay L1,L2] [--not L1,L2] [--t LINE,ARC] [--full] [--min LEN]

Prints one line per item: type, layer, linetype, handle, block path, and its points (or loops / insert data),
rounded to the millimetre. Items are clipped to nothing: an item is listed when any of its points lies in the box
or one of its segments crosses it. Reads only the drawing cache (no detector output).
"""
import math, os, pickle, sys

PKL = os.environ.get('SUITE_PKL', 'C:/Users/DWP2/AppData/Local/Temp/claude/1a2f3fc736ce552c/'
                      'e1e2f8a1-5b17-462a-bbe8-01925d989674/scratchpad/suite_revit_work/suite_revit/prims.pkl')


def load():
    with open(PKL, 'rb') as f:
        return pickle.load(f)


def seg_hits_box(p, q, box):
    x0, y0, x1, y1 = box
    # Liang-Barsky
    dx, dy = q[0] - p[0], q[1] - p[1]
    t0, t1 = 0.0, 1.0
    for pp, qq in ((-dx, p[0] - x0), (dx, x1 - p[0]), (-dy, p[1] - y0), (dy, y1 - p[1])):
        if pp == 0:
            if qq < 0:
                return False
        else:
            t = qq / pp
            if pp < 0:
                if t > t1: return False
                if t > t0: t0 = t
            else:
                if t < t0: return False
                if t < t1: t1 = t
    return True


def polylines(d):
    if 'pts' in d:
        return [d['pts'] + ([d['pts'][0]] if d.get('closed') else [])]
    if 'loops' in d:
        return [l + [l[0]] for l in d['loops'] if l]
    if 'ins' in d:
        return [[d['ins']]]
    return []


def hits(d, box):
    for pl in polylines(d):
        if len(pl) == 1:
            x, y = pl[0]
            if box[0] <= x <= box[2] and box[1] <= y <= box[3]:
                return True
        for a, b in zip(pl, pl[1:]):
            if seg_hits_box(a, b, box):
                return True
    return False


def length(d):
    L = 0
    for pl in polylines(d):
        for a, b in zip(pl, pl[1:]):
            L += math.dist(a, b)
    return L


def fmt_pts(P, full):
    if not full and len(P) > 6:
        P = P[:3] + [None] + P[-2:]
    return ' '.join('...' if p is None else f'({p[0]:.4f},{p[1]:.4f})' for p in P)


def main(argv):
    box = tuple(float(v) for v in argv[:4])
    args = argv[4:]
    lay = nlay = types = None
    full = '--full' in args
    minlen = 0
    if '--lay' in args: lay = set(args[args.index('--lay') + 1].split(','))
    if '--not' in args: nlay = set(args[args.index('--not') + 1].split(','))
    if '--t' in args: types = set(args[args.index('--t') + 1].split(','))
    if '--min' in args: minlen = float(args[args.index('--min') + 1])
    D = load()
    n = 0
    for d in D['items']:
        if lay and d['lay'] not in lay: continue
        if nlay and d['lay'] in nlay: continue
        if types and d['t'] not in types: continue
        if not hits(d, box): continue
        if minlen and d['t'] not in ('INSERT', 'TEXT', 'MTEXT') and length(d) < minlen: continue
        n += 1
        head = f"{d['t']:<10} {d['lay']:<14} lt={d.get('lt', '')!s:<12} h={d.get('h')} {('[' + d['path'][:40] + ']') if d.get('path') else ''}"
        if d['t'] == 'INSERT':
            print(head, f"name={d['name']} ins=({d['ins'][0]:.4f},{d['ins'][1]:.4f}) rot={d['rot']} sx={d['sx']} sy={d['sy']}")
        elif d['t'] == 'HATCH':
            for i, l in enumerate(d['loops']):
                xs = [p[0] for p in l]; ys = [p[1] for p in l]
                print(head, f"solid={d.get('solid')} loop{i} n={len(l)} bbox x {min(xs):.4f}-{max(xs):.4f} y {min(ys):.4f}-{max(ys):.4f}",
                      fmt_pts(l, full) if full or len(l) <= 8 else '')
        elif 'text' in d:
            print(head, f"text={d['text']!r} ins={d['ins']}")
        else:
            P = d['pts']
            print(head, f"closed={d.get('closed')} L={length(d):.4f}", fmt_pts(P, full))
    print(f'# {n} items')


if __name__ == '__main__':
    main(sys.argv[1:])
