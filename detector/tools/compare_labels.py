"""Compare two independent labellers' lists for one part: agreed / differing / only-one, by the scorer's matching."""
import json, math, sys
sys.path.insert(0, __import__('os').path.dirname(__file__))
from score import centre, width, match


def end_err(a, b):
    return min(max(math.dist(a['a'], b['a']), math.dist(a['b'], b['b'])), max(math.dist(a['a'], b['b']), math.dist(a['b'], b['a'])))


def compare(A, B):
    m = match(A['openings'], B['openings'])
    agree, differ = [], []
    for i, j, d in m:
        a, b = A['openings'][i], B['openings'][j]
        e = end_err(a, b)
        (agree if a['kind'] == b['kind'] and e <= 0.05 else differ).append((a, b, e))
    mi = {i for i, _, _ in m}; mj = {j for _, j, _ in m}
    onlyA = [o for i, o in enumerate(A['openings']) if i not in mi]
    onlyB = [o for j, o in enumerate(B['openings']) if j not in mj]
    return agree, differ, onlyA, onlyB


if __name__ == '__main__':
    A = json.load(open(sys.argv[1], encoding='utf-8')); B = json.load(open(sys.argv[2], encoding='utf-8'))
    agree, differ, onlyA, onlyB = compare(A, B)
    print(f'agree {len(agree)}  differ {len(differ)}  onlyA {len(onlyA)}  onlyB {len(onlyB)}')
    for a, b, e in differ:
        print(f"  DIFF {a['id']}/{b['id']}: {a['kind']}/{b['kind']} w {width(a):.3f}/{width(b):.3f} endErr {e:.3f} | A: {a['subtype'][:50]} | B: {b['subtype'][:50]}")
    for o in onlyA: print(f"  ONLY A {o['id']} {o['kind']} at {[round(v, 2) for v in centre(o)]} w {width(o):.2f} {o['subtype'][:60]}")
    for o in onlyB: print(f"  ONLY B {o['id']} {o['kind']} at {[round(v, 2) for v in centre(o)]} w {width(o):.2f} {o['subtype'][:60]}")
