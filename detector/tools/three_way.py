"""Three-way comparison of independent opening lists for one part, to send only real disputes to an adjudicator.

Usage: python three_way.py <part key> <out.json> A.json [B.json] [--inv inventory.json --floor ground --box x0,y0,x1,y1]
Lists: {"openings": [...]} in the answer-key format; the inventory is the evidence agent's list (kinds may end in '?').
Clusters entries that are the same opening (the scorer's matching, pairwise, joined transitively), then:
  accepted = A and B both have it with the same kind and ends within 5 cm, and the inventory (if given) has it with a
             compatible kind or not at all -> taken as final (A's numbers)
  dispute  = everything else (one list only, different kinds, ends more than 5 cm apart)
"""
import argparse, json, math, sys
sys.path.insert(0, __import__('os').path.dirname(__file__))
from score import centre, match


def end_err(a, b):
    return min(max(math.dist(a['a'], b['a']), math.dist(a['b'], b['b'])), max(math.dist(a['a'], b['b']), math.dist(a['b'], b['a'])))


def kind_of(o): return o['kind'].rstrip('?')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('part'); ap.add_argument('out'); ap.add_argument('lists', nargs='+')
    ap.add_argument('--inv'); ap.add_argument('--floor'); ap.add_argument('--box')
    a = ap.parse_args()
    L = {}
    for name, path in zip('AB', a.lists): L[name] = json.load(open(path, encoding='utf-8'))['openings']
    if a.inv:
        box = [float(v) for v in a.box.split(',')]
        inv = json.load(open(a.inv, encoding='utf-8'))
        L['E'] = [dict(o, kind=kind_of(o)) for o in inv if o.get('floor') == a.floor
                  and box[0] <= centre(o)[0] <= box[2] and box[1] <= centre(o)[1] <= box[3]]
    names = list(L)
    # union-find over (list, index)
    parent = {(n, i): (n, i) for n in names for i in range(len(L[n]))}
    def find(x):
        while parent[x] != x: parent[x] = parent[parent[x]]; x = parent[x]
        return x
    for x in range(len(names)):
        for y in range(x + 1, len(names)):
            for i, j, _ in match(L[names[x]], L[names[y]]):
                parent[find((names[x], i))] = find((names[y], j))
    groups = {}
    for k in parent: groups.setdefault(find(k), []).append(k)
    accepted, disputes = [], []
    for g in groups.values():
        members = {n: L[n][i] for n, i in g}
        A, B, E = members.get('A'), members.get('B'), members.get('E')
        if 'B' not in L and E is not None:          # one labeller + the inventory: the inventory is the second opinion
            B, E = E, None
        ok = A is not None and B is not None and A['kind'] == B['kind'] and end_err(A, B) <= 0.05
        if ok and E is not None and kind_of(E) != A['kind']: ok = False
        entry = {n: members[n] for n in sorted(members)}
        if ok:
            accepted.append({**A, 'agreement': 'both', 'decision': 'A and B agree (kind, ends within 5 cm)' + ('; inventory agrees' if E else '; not in the inventory')})
        else:
            why = []
            if A is None or B is None: why.append('listed by ' + '+'.join(sorted(members)) + ' only')
            elif A['kind'] != B['kind']: why.append(f"kind A {A['kind']} / B {B['kind']}")
            elif end_err(A, B) > 0.05: why.append(f"ends differ by {end_err(A, B):.3f} m")
            if E is not None and A is not None and kind_of(E) != A['kind']: why.append(f"inventory kind {E['kind']}")
            disputes.append({'why': '; '.join(why), 'at': [round(v, 3) for v in centre(next(iter(members.values())))], 'versions': entry})
    disputes.sort(key=lambda d: (d['at'][0], d['at'][1]))
    json.dump({'part': a.part, 'accepted': accepted, 'disputes': disputes}, open(a.out, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    print(f'{a.part}: accepted {len(accepted)}, disputes {len(disputes)}')
    for d in disputes: print('   ', d['at'], d['why'])


if __name__ == '__main__':
    main()
