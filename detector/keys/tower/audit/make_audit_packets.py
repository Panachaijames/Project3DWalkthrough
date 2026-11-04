"""Build the blind audit packets: candidate locations (detector extras mixed with known-real key openings as controls), shuffled
with a fixed seed and anonymised. The private map (which candidate is which) goes to audit4_private/, off limits to the auditors.
Run from anywhere. Reads the v2 score report (corrected mapping) and the detector output."""
import json, random
from pathlib import Path

P0 = Path('C:/Users/DWP2/AppData/Local/Temp/claude/c--Users-DWP2-Desktop-Project-walkthrough/e1e2f8a1-5b17-462a-bbe8-01925d989674/scratchpad/p0')
S = json.loads((P0 / 'hold_blind_L29_L30' / 'v2' / 'score_v2.json').read_text(encoding='utf-8'))
DET = {o['id']: o for o in json.loads((P0 / 'hold_blind_L29_L30' / 'v2' / 'all_v2.json').read_text(encoding='utf-8'))['openings']}
KEY = {o['id']: o for o in json.loads((P0 / 'keys4' / 'final' / 'tower.json').read_text(encoding='utf-8'))['openings']}
(P0 / 'audit4').mkdir(exist_ok=True)
(P0 / 'audit4_private').mkdir(exist_ok=True)
rng = random.Random(2710)
private = {}
for fl, short in (('tower:L29', 'l29'), ('tower:L30', 'l30')):
    rep = S['floors'][fl]
    cands = []
    for x in rep['extra']:
        o = DET[x['det']]
        cands.append({'src': 'detector-extra', 'orig': o['id'], 'kind': o['kind'], 'a': o['a'], 'b': o['b']})
    good = [p for p in rep['pairs'] if p['right']]
    pas = [p for p in good if KEY[p['key']]['kind'] == 'passage']          # real passages too, so the kind does not give the controls away
    rest = [p for p in good if p not in pas]
    ctrl = pas + rng.sample(rest, min(12 - len(pas), len(rest)))
    for p in ctrl:
        o = KEY[p['key']]
        cands.append({'src': 'key-control', 'orig': o['id'], 'kind': o['kind'], 'a': o['a'], 'b': o['b']})
    rng.shuffle(cands)
    pub, priv = [], {}
    for i, c in enumerate(cands, 1):
        cid = f'{short.upper()}-C{i:02d}'
        a, b = c['a'], c['b']
        w = ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5
        pub.append({'cid': cid, 'a': [round(v, 3) for v in a], 'b': [round(v, 3) for v in b],
                    'centre': [round((a[0] + b[0]) / 2, 3), round((a[1] + b[1]) / 2, 3)], 'width': round(w, 3)})
        priv[cid] = {'src': c['src'], 'orig': c['orig']}
    (P0 / 'audit4' / f'{short}_candidates.json').write_text(json.dumps(pub, indent=1), encoding='utf-8')
    private[short] = priv
    print(short, len(pub), 'candidates:', sum(1 for v in priv.values() if v['src'] == 'detector-extra'), 'detector extras +',
          sum(1 for v in priv.values() if v['src'] == 'key-control'), 'controls')
(P0 / 'audit4_private' / 'secret_map.json').write_text(json.dumps(private, indent=1), encoding='utf-8')
