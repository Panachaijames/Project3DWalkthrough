"""Follow-up on the blind audit: which extra finds are NOT in the key (possible key false negatives), what the audit adds to the key,
and the sensitivity of the score to the width convention. Writes keys4/final/tower_audited.json (key + audit additions + altWidth)."""
import json, math, sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, 'C:/Users/DWP2/Desktop/Project walkthrough/detector/tools')
from score import match, centre, width, angle, same_wall

P0 = Path('C:/Users/DWP2/AppData/Local/Temp/claude/c--Users-DWP2-Desktop-Project-walkthrough/e1e2f8a1-5b17-462a-bbe8-01925d989674/scratchpad/p0')
res = json.loads(Path('C:/Users/DWP2/AppData/Local/Temp/claude/c--Users-DWP2-Desktop-Project-walkthrough/e1e2f8a1-5b17-462a-bbe8-01925d989674/tasks/wzeuxoymq.output').read_text(encoding='utf-8'))['result']
K = json.loads((P0 / 'keys4' / 'final' / 'tower.json').read_text(encoding='utf-8'))
KEY = K['openings']
secret = json.loads((P0 / 'audit4_private' / 'secret_map.json').read_text(encoding='utf-8'))
DET = {o['id']: o for o in json.loads((P0 / 'fix4' / 'baseline' / 'l29_openings.json').read_text(encoding='utf-8'))['openings'] +
       json.loads((P0 / 'fix4' / 'baseline' / 'l30_openings.json').read_text(encoding='utf-8'))['openings']}

audits = defaultdict(dict)
finds = defaultdict(list)
conv = {}
for x in res:
    if x['kind'] == 'audit':
        audits[x['floor']][x['who']] = {d['cid']: d for d in x['r']['decisions']}
        for e in x['r']['extraFinds']: finds[x['floor']].append({**e, 'who': x['who']})
    if x['kind'] == 'conv':
        for v in x['r']['reviews']: conv[v['id']] = v

# ---- 1. extra finds that match no key opening
print('=== extra finds not matched by any key entry (scored or optional) ===')
unmatched = []
for fl, lst in finds.items():
    keys = [o for o in KEY if o['floor'] == f'tower:{fl.upper()}']
    for e in lst:
        cand = {'a': e['a'], 'b': e['b'], 'kind': e['kind']}
        m = match(keys, [cand])
        if not m:
            unmatched.append((fl, e))
            print(f"  {fl}-{e['who']}: {e['kind']} a={e['a']} b={e['b']} w={e['width']} opt={e.get('optional')} | {e['evidence'][:230]}")
print(len(unmatched), 'unmatched find reports')

# ---- 2. detector extras that both auditors accepted as real; split ones
adds = []
print('\n=== extras both auditors accepted (key false negatives) ===')
for fl, priv in secret.items():
    for c, v in priv.items():
        if v['src'] != 'detector-extra': continue
        a, b = audits[fl].get('A', {}).get(c), audits[fl].get('B', {}).get(c)
        if a and b and a['verdict'] == b['verdict'] == 'opening':
            adds.append({'floor': f'tower:{fl.upper()}', 'from': c, 'det': v['orig'], 'A': a, 'B': b})
            print(f'  {fl} {c} (detector {v["orig"]}): A {a["kind"]} {a["a"]}-{a["b"]} w={a["width"]}; B {b["kind"]} {b["a"]}-{b["b"]} w={b["width"]}')
print('split verdicts (kept out of the key, would be optional at most):')
for fl, priv in secret.items():
    for c, v in priv.items():
        if v['src'] != 'detector-extra': continue
        a, b = audits[fl].get('A', {}).get(c), audits[fl].get('B', {}).get(c)
        if a and b and a['verdict'] != b['verdict']: print(f'  {fl} {c} (detector {v["orig"]})')

# ---- 3. build the audited key: original entries + audit additions; altWidth from the convention review
out = json.loads(json.dumps(K))
for o in out['openings']:
    r = conv.get(o['id'])
    if r and not r['ok'] and r.get('newWidth'):
        o['altWidth'] = r['newWidth']; o['altA'] = r.get('newA'); o['altB'] = r.get('newB'); o['altWhy'] = r['reason'][:240]
n = 0
for ad in adds:
    A, B = ad['A'], ad['B']
    a = A['a']; b = A['b']
    n += 1
    out['openings'].append({'id': f'AUD-{n:02d}', 'floor': ad['floor'], 'kind': A['kind'], 'subtype': 'added by the blind audit (both auditors)', 'a': a, 'b': b,
                            'width': math.dist(a, b), 'wallThickness': 0.1, 'host': 'wall', 'evidence': A['evidence'][:300], 'confidence': 'medium',
                            'optional': bool(A.get('optional') and B.get('optional')), 'agreement': 'audited'})
(P0 / 'keys4' / 'final' / 'tower_audited.json').write_text(json.dumps(out, indent=1), encoding='utf-8')
print('\naudited key written:', sum(1 for o in out['openings'] if not o.get('optional')), 'scored entries;', sum(1 for o in out['openings'] if o.get('altWidth')), 'with an alternative measured width')
