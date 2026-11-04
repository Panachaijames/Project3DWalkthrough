# Semantic check of the block-turn placement: do the placed visitor chairs face a desk / table, and do the monitors' screens
# face the user's side (the task chair)? Uses placements.json (insert turn + mirror) and bank_model.json only.
import json, math, sys
from collections import Counter
P = sys.argv[1]
bank = json.load(open(P + '/bank_test/src/bank_model.json', encoding='utf-8'))
pl = json.load(open(P + '/furniture_test/bank_furnished/placements.json', encoding='utf-8'))
fur = {f['id']: f for f in bank['furniture']}
print('kinds:', Counter(f['kind'] for f in bank['furniture']))


def front_angle(turn, mirror, model_turn_in_block=0.0):
    # in the block frame the model faces -Y (270 deg) turned by model_turn_in_block; a 'mirror y' flips it to +Y
    a = 270 + model_turn_in_block
    if mirror == 'mirror y':
        a = -a  # reflect across the x axis
    return (a + turn) % 360


def ang(dx, dy):
    return math.degrees(math.atan2(dy, dx)) % 360


def diff(a, b):
    return (a - b + 180) % 360 - 180


def nearest(fid, kinds, maxd=3.0):
    me = fur[fid]
    best = None
    for f in bank['furniture']:
        if f['floor'] != me['floor'] or f['kind'] not in kinds or f['id'] == fid:
            continue
        d = math.hypot(f['x'] - me['x'], f['y'] - me['y'])
        if d <= maxd and (best is None or d < best[0]):
            best = (d, f)
    return best


def report(model, kinds, turn_in_block=0.0, label='faces'):
    m = pl['models'][model]
    print(f'\n== {model} ({m["family"]})')
    ok = 0
    for p in m['pieces']:
        f = fur[p['key']]
        fa = front_angle(p['insert']['turn'], p['mirror'], turn_in_block)
        nb = nearest(p['key'], kinds)
        if nb is None:
            print(f'  {p["key"]:<16} turn {p["insert"]["turn"]:>6} {p["mirror"]:<9} front {fa:6.1f}  no {"/".join(kinds)} within 3 m')
            continue
        d, t = nb
        to = ang(t['x'] - f['x'], t['y'] - f['y'])
        dd = diff(to, fa)
        good = abs(dd) <= 60
        ok += good
        print(f'  {p["key"]:<16} turn {p["insert"]["turn"]:>6} {p["mirror"]:<9} front {fa:6.1f}  nearest {t["id"]:<20} {d:4.2f} m at {to:6.1f}  off {dd:7.1f}  {"OK" if good else "AWAY"}')
    print(f'  {ok} of {len(m["pieces"])} {label} the nearest one')


report('visitor chair01', {'table', 'coffee-table'})
report('working table', {'seat'})
# the monitor: in the block frame the screen faces -Y turned by 0.4 deg (analysis); the user sits on that side: nearest seat
report('monitor', {'seat'}, 0.4, 'face the seat')
report('sofa', {'coffee-table', 'table'})


def report_fam(model, famsub, turn_in_block=0.0, label='faces', maxd=3.0, side=1):
    m = pl['models'][model]
    print(f'\n== {model} against the nearest piece whose family contains {famsub!r}')
    ok = 0
    for p in m['pieces']:
        f = fur[p['key']]
        fa = (front_angle(p['insert']['turn'], p['mirror'], turn_in_block) + (0 if side == 1 else 180)) % 360
        best = None
        for g in bank['furniture']:
            if g['floor'] != f['floor'] or famsub not in g['family'] or g['id'] == f['id']:
                continue
            d = math.hypot(g['x'] - f['x'], g['y'] - f['y'])
            if d <= maxd and (best is None or d < best[0]):
                best = (d, g)
        if best is None:
            print(f'  {p["key"]:<16} front {fa:6.1f}  none within {maxd} m')
            continue
        d, t = best
        to = ang(t['x'] - f['x'], t['y'] - f['y'])
        dd = diff(to, fa)
        good = abs(dd) <= 60
        ok += good
        print(f'  {p["key"]:<16} front {fa:6.1f}  nearest {t["id"]:<20} {d:4.2f} m at {to:6.1f}  off {dd:7.1f}  {"OK" if good else "AWAY"}')
    print(f'  {ok} of {len(m["pieces"])} {label}')


report_fam('monitor', 'AER1A', 0.4, 'screens face the nearest Aeron task chair')
report_fam('working table', 'mollie', 0.0, 'desks have their visitor (-Y, modesty panel) side towards the nearest mollie chair')

# what stands in front of the four L2 mollie chairs that face no table?
print('\n== in front of L2-seat-014 .. 017 (within 2.5 m, within 45 deg of the front)')
for pid in ['L2-seat-014', 'L2-seat-015', 'L2-seat-016', 'L2-seat-017']:
    f = fur[pid]
    p = next(q for q in pl['models']['visitor chair01']['pieces'] if q['key'] == pid)
    fa = front_angle(p['insert']['turn'], p['mirror'])
    seen = []
    for g in bank['furniture']:
        if g['floor'] != f['floor'] or g['id'] == pid:
            continue
        d = math.hypot(g['x'] - f['x'], g['y'] - f['y'])
        if d > 2.5:
            continue
        to = ang(g['x'] - f['x'], g['y'] - f['y'])
        if abs(diff(to, fa)) <= 45:
            seen.append((round(d, 2), g['id'], g['family'][:40]))
    print(' ', pid, f'at ({f["x"]}, {f["y"]}) front {fa}:', sorted(seen)[:5])
