"""Score the frozen detector's hidden output on the tower floors against the combined answer key (both mapping versions).

Usage: python score_blind.py   (run from anywhere; paths are absolute)
v1 = the detector run with the first layer mapping (my guess from layer names), v2 = the same frozen detector with the mapping
read from the independent description of the drawings.
"""
import json, subprocess, sys
from pathlib import Path

P0 = Path('C:/Users/DWP2/AppData/Local/Temp/claude/c--Users-DWP2-Desktop-Project-walkthrough/e1e2f8a1-5b17-462a-bbe8-01925d989674/scratchpad/p0')
HOLD = P0 / 'hold_blind_L29_L30'
KEY = P0 / 'keys4' / 'final' / 'tower.json'
env = {'PYTHONIOENCODING': 'utf-8', 'PATH': __import__('os').environ['PATH']}

for tag, folder in (('v1', HOLD), ('v2', HOLD / 'v2')):
    allops = []
    for n in (29, 30):
        allops += json.loads((folder / f'l{n}_openings.json').read_text(encoding='utf-8'))['openings']
    merged = folder / f'all_{tag}.json'
    merged.write_text(json.dumps({'openings': allops}, indent=1), encoding='utf-8')
    rep = folder / f'score_{tag}.json'
    r = subprocess.run([sys.executable, '-B', str(P0 / 'tools' / 'score.py'), str(KEY), str(merged), '--out', str(rep)],
                       capture_output=True, text=True, env=env)
    (folder / f'score_{tag}.txt').write_text(r.stdout, encoding='utf-8')
    print(f'################ {tag} ({"first mapping" if tag == "v1" else "mapping from the independent reading"}) ################')
    print(r.stdout)
    S = json.loads(rep.read_text(encoding='utf-8'))
    print('detections the key does not list (extras):', {f: len(v['extra']) for f, v in S['floors'].items()},
          'total', sum(len(v['extra']) for v in S['floors'].values()))
    print('by kind of extra:', {k: sum(1 for v in S['floors'].values() for x in v['extra'] if x['kind'] == k) for k in ('door', 'window', 'passage')})
    print()
