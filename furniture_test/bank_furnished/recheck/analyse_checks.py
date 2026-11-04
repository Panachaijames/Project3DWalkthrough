# Reads recheck_checks*.json and prints the verdicts of the placement, box and count checks.
import json, sys
from collections import defaultdict
R = json.load(open(sys.argv[1], encoding='utf-8'))
C = R['checks']
print('gpu', C['gpu'], 'canvas', C['canvas'])
print('counts in the page', C['counts0'])

# ---- boxes
A = C['boxesA']
furnished = set()
for name in ['B', 'C20000', 'C10000', 'C5000', 'C2500', 'D', 'E']:
    S = C['boxes' + name]
    hidden = {k for k, v in S.items() if not v['matVisible']}
    if not furnished:
        furnished = hidden
    bad = []
    for k, v in S.items():
        a = A[k]
        if k in hidden:
            if v['lineVisible']:
                bad.append((k, 'outline still drawn'))
        else:
            if v['mat'] != a['mat'] or v['line'] != a['line']:
                bad.append((k, 'material changed'))
        for f in ('visible', 'collider', 'pos', 'scale'):
            if v[f] != a[f]:
                bad.append((k, f + ' changed'))
    print(f'{name}: hidden {len(hidden)} boxes (same set as B: {hidden == furnished}), problems: {bad[:5]}')
SP = C['boxesPfull']
print('Pfull: hidden', sum(1 for v in SP.values() if not v['matVisible']), 'of', len(SP), '; colliders unchanged:', all(SP[k]['collider'] == A[k]['collider'] for k in A))
A2 = C['boxesA2']
print('back in A: all as at the start:', all(A2[k] == A[k] for k in A), '; drawn', sum(1 for v in A2.values() if v['matVisible']))
print('colliders among the furnished boxes:', sum(1 for k in furnished if A[k]['collider']), 'of', len(furnished),
      '; not colliders:', sorted(k for k in furnished if not A[k]['collider']))

# ---- counts
for name in ['A', 'B', 'C20000', 'C10000', 'C5000', 'C2500', 'D', 'E', 'Pfull', 'P5000', 'A2']:
    c = C['counts' + name]
    i, e, p = c['info'], c['expected'], c['panel']
    pt = int(p['tris'].replace(',', '')); pc = int(p['calls'].replace(',', ''))
    print(f"{name:7} info {i['triangles']:>9,} / {i['calls']:>3}  independent {e['triangles']:>9,} / {e['calls']:>3}  panel {pt:>9,} / {pc:>3}  "
          f"models all {e['modelTrianglesAll']:>9,} panel '{p['modelTris']}'  live {c['live']['modelTriangles']:>9,}  dl '{p['dl']}'  mem '{p['mem']}'")

# ---- copies
for name in ['B', 'C20000', 'C10000', 'C5000', 'C2500', 'D', 'E', 'Pfull', 'P5000']:
    rows = C['copies' + name]['copies']
    print(f'\n== {name}: {len(rows)} copies')
    by = defaultdict(list)
    for r in rows:
        by[r['model']].append(r)
    for m, rs in by.items():
        bot = [r['bottomVsBox_mm'] for r in rs]
        ins = [r['insideBox'] for r in rs]
        cen = [r['centreFromBox_m'] for r in rs]
        fo = [r['frontOff'] for r in rs if 'frontOff' in r]
        fl = all(r['inFloorGroup'] for r in rs) and all(r['visible'] for r in rs)
        line = f"  {m:16} n={len(rs):3}  bottom {min(bot):7.1f} .. {max(bot):6.1f} mm  inside box {min(ins):.2f} .. {max(ins):.2f}  centre off {min(cen):.3f} .. {max(cen):.3f} m  floor group+visible {fl}"
        if fo:
            line += f"  facing off {min(fo):6.1f} .. {max(fo):6.1f} deg"
        print(line)
    if name == 'B':
        for r in rows:
            if r['model'] == 'monitor':
                print(f"     {r['key']:16} on {r['support']}: screen over it {r['screenOverSupport']}, keyboard+mouse over it {r['keyboardMouseOverSupport']}, facing {r['front']} expected {r['expected']}")
            if r['model'] == 'sofa':
                print(f"     {r['key']:16} back pad {r['backPad']}")
            if r['model'] in ('visitor chair01', 'working table') and abs(r.get('frontOff', 0)) > 10:
                print('     !!', r)
            if r['insideBox'] < 0.97 and r['model'] != 'monitor':
                print('     outside:', r['key'], r['model'], r['insideBox'], r['centreFromBox_m'])

# ---- the same piece, B against the slimmed ways: the bounding boxes
B = {r['key']: r for r in C['copiesB']['copies']}
for name in ['C20000', 'C10000', 'C5000', 'C2500', 'D', 'E']:
    worst = max((max(abs(a - b) for a, b in zip(r['bbox'], B[r['key']]['bbox'])), r['key'], r['model']) for r in C['copies' + name]['copies'])
    print(f'{name}: largest bbox difference from B {worst[0] * 1000:.1f} mm at {worst[1]} ({worst[2]})')
print('\nwalk', json.dumps(C['walk'], indent=0))
print('page errors', R['pageErrors'])
