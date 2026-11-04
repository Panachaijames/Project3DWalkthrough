"""The held-out score on the tower floors under each reading of the answer key and of 'width right'."""
import json, sys
from pathlib import Path

sys.path.insert(0, 'C:/Users/DWP2/Desktop/Project walkthrough/detector/tools')
from score import score, width

P0 = Path('C:/Users/DWP2/AppData/Local/Temp/claude/c--Users-DWP2-Desktop-Project-walkthrough/e1e2f8a1-5b17-462a-bbe8-01925d989674/scratchpad/p0')
HOLD = P0 / 'hold_blind_L29_L30'
K0 = json.loads((P0 / 'keys4' / 'final' / 'tower.json').read_text(encoding='utf-8'))
K1 = json.loads((P0 / 'keys4' / 'final' / 'tower_audited.json').read_text(encoding='utf-8'))
ALT = {o['id']: o['altWidth'] for o in K1['openings'] if o.get('altWidth')}


def run(key, det_path):
    det = json.loads(Path(det_path).read_text(encoding='utf-8'))
    return score(key, det)


def tol(w): return max(0.10, 0.10 * w)


def summarise(rep, with_alt):
    n = right = matched = 0
    rows = []
    for f, v in rep['floors'].items():
        n += v['keyCount']; matched += v.get('matched', 0)
        for p in v['pairs']:
            ok = p['right']
            if not ok and with_alt and p['classOk'] and p['key'] in ALT and abs(p['widthDet'] - ALT[p['key']]) <= tol(ALT[p['key']]): ok = True
            right += ok
            if not ok: rows.append(p)
    return n, matched, right, rows


print(f"{'mapping':34s} {'key':>10s} {'found':>12s} {'right (strict)':>16s} {'right (+clear width)':>22s}")
for tag, det, label in (('v1', HOLD / 'all_v1.json', 'first mapping (as run)'), ('v2', HOLD / 'v2' / 'all_v2.json', 'mapping from the independent reading')):
    for kname, key in (('as made', K0), ('audited', K1)):
        rep = run(key, det)
        n, matched, right, _ = summarise(rep, False)
        n2, _, right2, rows = summarise(rep, True)
        print(f"{label:34s} {kname:>10s}  {n:3d} keys  found {matched:3d} ({matched / n:5.1%})  right {right:3d} ({right / n:5.1%})  right+clear {right2:3d} ({right2 / n:5.1%})")
        if tag == 'v2' and kname == 'audited':
            print('    still not right with the clear-width reading:')
            for p in rows: print('      ', p['key'], '~', p['det'], 'widths key/det', p['widthKey'], p['widthDet'], 'class ok', p['classOk'])
            for f, v in rep['floors'].items():
                for m in v['missed']: print('       MISSED', m['key'], m['kind'], m['at'], m['width'], m['subtype'][:60])
                print('       ', f, 'extras', len(v['extra']), 'optional found', len(v['optionalFound']), '/', v['optionalKeys'])
