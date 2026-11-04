"""Analyse the blind audit: calibration on the controls, verdicts on the detector extras, extra finds, convention reviews."""
import json, sys
from collections import Counter, defaultdict
from pathlib import Path

T = Path('C:/Users/DWP2/AppData/Local/Temp/claude/c--Users-DWP2-Desktop-Project-walkthrough/e1e2f8a1-5b17-462a-bbe8-01925d989674/tasks/wzeuxoymq.output')
P0 = Path('C:/Users/DWP2/AppData/Local/Temp/claude/c--Users-DWP2-Desktop-Project-walkthrough/e1e2f8a1-5b17-462a-bbe8-01925d989674/scratchpad/p0')
res = json.loads(T.read_text(encoding='utf-8'))['result']
(P0 / 'results' / 't_audit_results.json').write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding='utf-8')
secret = json.loads((P0 / 'audit4_private' / 'secret_map.json').read_text(encoding='utf-8'))
KEY = {o['id']: o for o in json.loads((P0 / 'keys4' / 'final' / 'tower.json').read_text(encoding='utf-8'))['openings']}

audits = defaultdict(dict)   # floor -> who -> {cid: decision}
for x in res:
    if x['kind'] == 'audit':
        audits[x['floor']][x['who']] = {d['cid']: d for d in x['r']['decisions']}
        print(f"audit {x['floor']}-{x['who']}: {len(x['r']['decisions'])} decisions, {sum(1 for d in x['r']['decisions'] if d['verdict'] == 'opening')} openings, {len(x['r']['extraFinds'])} extra finds")

print('\n=== CALIBRATION on the controls (known-real key openings, not identifiable by the auditors) ===')
for fl, priv in secret.items():
    for who in 'AB':
        dec = audits[fl].get(who, {})
        ctrl = {c: v for c, v in priv.items() if v['src'] == 'key-control'}
        said_open = [c for c in ctrl if dec.get(c, {}).get('verdict') == 'opening']
        kind_ok = [c for c in said_open if dec[c]['kind'] == KEY[ctrl[c]['orig']]['kind']]
        print(f'{fl}-{who}: said "opening" on {len(said_open)}/{len(ctrl)} controls; kind agrees with the key on {len(kind_ok)}')
        for c in ctrl:
            if c not in said_open:
                print('    MISSED CONTROL', c, ctrl[c]['orig'], KEY[ctrl[c]['orig']]['kind'], '|', dec.get(c, {}).get('reasonNotOpening'), '|', dec.get(c, {}).get('evidence', '')[:150])

print('\n=== VERDICTS on the detector extras ===')
tally = Counter()
rows = []
for fl, priv in secret.items():
    ex = {c: v for c, v in priv.items() if v['src'] == 'detector-extra'}
    for c, v in ex.items():
        a, b = audits[fl].get('A', {}).get(c), audits[fl].get('B', {}).get(c)
        va, vb = (a or {}).get('verdict'), (b or {}).get('verdict')
        if va == vb == 'opening': cls = 'REAL (both auditors)'
        elif va == vb == 'not-opening': cls = 'false positive (both)'
        else: cls = 'split'
        tally[(fl, cls)] += 1
        rows.append((fl, c, v['orig'], cls, a, b))
for k, n in sorted(tally.items()): print(k, n)
print()
for fl, c, orig, cls, a, b in rows:
    if cls != 'false positive (both)':
        print(f'{fl} {c} det {orig:9s} {cls}')
        for tag, d in (('A', a), ('B', b)):
            if d: print(f"     {tag}: {d['verdict']:11s} {d['kind']:8s} a={d.get('a')} b={d.get('b')} w={d.get('width')} opt={d.get('optional')} | {d['evidence'][:170]}")

print('\n=== why the extras that both auditors rejected are not openings ===')
why = Counter()
for fl, c, orig, cls, a, b in rows:
    if cls == 'false positive (both)': why[(a['reasonNotOpening'], b['reasonNotOpening'])] += 1
for k, n in why.most_common(): print(n, k)

print('\n=== EXTRA FINDS (openings the auditors saw that no candidate covers) ===')
for x in res:
    if x['kind'] == 'audit':
        for e in x['r']['extraFinds']:
            print(f"{x['floor']}-{x['who']}: {e['kind']} a={e['a']} b={e['b']} w={e['width']} opt={e.get('optional')} | {e['evidence'][:200]}")

print('\n=== CONVENTION REVIEW (key entries to change) ===')
for x in res:
    if x['kind'] == 'conv':
        r = x['r']
        print(f"-- {x['floor']}: {len(r['reviews'])} reviewed, {sum(1 for v in r['reviews'] if not v['ok'])} to change. Summary: {r['summary'][:900]}")
        for v in r['reviews']:
            if not v['ok']:
                k = KEY.get(v['id'])
                print(f"   {v['id']} {k['kind'] if k else '?'} key w={k['width'] if k else '?'} -> new {v.get('newKind', '')} a={v.get('newA')} b={v.get('newB')} w={v.get('newWidth')} | {v['reason'][:210]}")
