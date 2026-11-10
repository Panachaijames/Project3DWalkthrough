"""Full three-way comparison of lists A, B and C of the suite_revit drawing (held-out test, step 4 of 7).

tools/three_way.py (run as it is, output suite_revit.json next to this file) only compares A with B on kind and ends,
and only checks the inventory (C) for kind. The step also counts as a dispute a different optional flag, a different
subtype and a width beyond tolerance between ANY two lists, so this script clusters the same way (the scorer's
matching from tools/score.py, pairwise, joined transitively) and checks every cluster on:
  presence   all three lists have it
  kind       same kind (C's trailing '?' stripped, as three_way does)
  optional   same optional flag
  ends       every pair's ends within 5 cm (three_way's rule for agreement)
  width      every pair's width difference within the scorer's tolerance max(0.10 m, 0.10 x width)
The subtypes are printed side by side for reading (they are free text, so a subtype dispute is judged by eye).

Usage (from detector/): python -B keys/suite_revit/disputes/compare_full.py
Writes keys/suite_revit/disputes/comparison_full.json.
"""
import json, math, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DET = HERE.parents[2]                                   # detector/
sys.path.insert(0, str(DET / 'tools'))
from score import centre, width, match                  # noqa: E402  (the scorer's own matching, not edited)

LAB = HERE.parent / 'labels'


def end_err(a, b):
    return min(max(math.dist(a['a'], b['a']), math.dist(a['b'], b['b'])), max(math.dist(a['a'], b['b']), math.dist(a['b'], b['a'])))


def kind_of(o): return o['kind'].rstrip('?')


def main():
    L = {'A': json.load(open(LAB / 'A.json', encoding='utf-8'))['openings'],
         'B': json.load(open(LAB / 'B.json', encoding='utf-8'))['openings'],
         'C': [o for o in json.load(open(LAB / 'C.json', encoding='utf-8')) if o.get('floor') == 'suite_revit']}
    names = list(L)
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
    clusters = []
    for g in groups.values():
        mem = {n: L[n][i] for n, i in sorted(g)}
        issues = []
        missing = [n for n in names if n not in mem]
        if missing: issues.append('not in ' + '+'.join(missing))
        kinds = {n: kind_of(o) for n, o in mem.items()}
        if len(set(kinds.values())) > 1: issues.append('kind ' + ' / '.join(f'{n} {k}' for n, k in kinds.items()))
        opts = {n: bool(o.get('optional')) for n, o in mem.items()}
        if len(set(opts.values())) > 1: issues.append('optional ' + ' / '.join(f'{n} {v}' for n, v in opts.items()))
        ns = list(mem)
        worst_end, worst_w = 0.0, 0.0
        for p in range(len(ns)):
            for q in range(p + 1, len(ns)):
                a, b = mem[ns[p]], mem[ns[q]]
                e = end_err(a, b)
                dw = abs(width(a) - width(b))
                tol = max(0.10, 0.10 * min(width(a), width(b)))
                worst_end = max(worst_end, e)
                if dw > tol + 1e-9: issues.append(f'width {ns[p]} {width(a):.3f} / {ns[q]} {width(b):.3f} beyond tolerance {tol:.3f}')
                worst_w = max(worst_w, dw)
        if worst_end > 0.05 + 1e-9: issues.append(f'ends differ by up to {worst_end:.3f} m')
        c = centre(next(iter(mem.values())))
        clusters.append({'at': [round(c[0], 3), round(c[1], 3)],
                         'ids': {n: o['id'] for n, o in mem.items()},
                         'kind': kinds, 'optional': opts,
                         'width': {n: round(width(o), 4) for n, o in mem.items()},
                         'maxEndDiff': round(worst_end, 4), 'maxWidthDiff': round(worst_w, 4),
                         'subtype': {n: o.get('subtype', '') for n, o in mem.items()},
                         'issues': issues})
    clusters.sort(key=lambda c: (bool(not c['issues']), c['at'][0], c['at'][1]))
    out = {'what': 'every cluster of the three lists (scorer matching, transitive) with its members and the checks of the '
                   'step: presence, kind, optional flag, ends within 5 cm, width within the scorer tolerance',
           'counts': {n: len(L[n]) for n in names}, 'clusters': len(clusters),
           'withIssues': sum(1 for c in clusters if c['issues']), 'list': clusters}
    (HERE / 'comparison_full.json').write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding='utf-8')
    print(f"lists {out['counts']}  clusters {len(clusters)}  with issues {out['withIssues']}")
    for c in clusters:
        flag = '; '.join(c['issues']) if c['issues'] else 'agree'
        print(f"{str(c['at']):18} {c['ids']}  {flag}  (max end diff {c['maxEndDiff']}, width {c['width']})")


if __name__ == '__main__':
    main()
