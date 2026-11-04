"""Run the opening detector on all six drawings, merge the results and score them against the answer keys.

Usage: python -B run_all.py [OUT] [--png] [--only sukhumvit presidential bank1 bank2 l29 l30]
  OUT     where the results go (default: last_run/ next to this file; output/ holds the saved results and is not
          overwritten unless you name it)
  --png   also write one marked top-view PNG per floor (doors red, windows blue, passages green)
Needs <name>/prims.pkl for each drawing in the data folder (this folder, or OPENINGS_DATA): make it with
`python tools/prims.py <name>` from the drawing's plan.dxf (see README.md). Writes <name>_openings.json, <name>_log.txt, and
for each group of drawings a merged file and a score:
  the four older drawings (Sukhumvit house, presidential suite, bank branch)  -> scored against keys/final/all.json
  the tower floors l29, l30 (the fourth drawing)                              -> scored against keys/tower/tower_audited.json
and prints both scores and the number of detections each key does not list.
"""
import json, os, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OLD = ('sukhumvit', 'presidential', 'bank1', 'bank2')
NEW = ('l29', 'l30')
NAMES = OLD + NEW
KEYS = {'older': (OLD, HERE / 'keys' / 'final' / 'all.json'), 'tower': (NEW, HERE / 'keys' / 'tower' / 'tower_audited.json')}
argv = sys.argv[1:]
only = NAMES
if '--only' in argv:
    i = argv.index('--only')
    only = tuple(a for a in argv[i + 1:] if not a.startswith('--'))
    argv = argv[:i] + [a for a in argv[i + 1:] if a.startswith('--')]
    bad = [n for n in only if n not in NAMES]
    if bad: sys.exit(f'unknown drawing {bad}; choose from {NAMES}')
args = [a for a in argv if not a.startswith('--')]
OUT = Path(args[0]) if args else HERE / 'last_run'
OUT.mkdir(parents=True, exist_ok=True)
png = '--png' in argv
env = dict(os.environ, PYTHONIOENCODING='utf-8')
ops = {}
for nm in only:
    cmd = [sys.executable, '-B', 'openings.py', f'mappings/{nm}.json', str(OUT / f'{nm}_openings.json')]
    if png: cmd += ['--png', str(OUT)]
    r = subprocess.run(cmd, capture_output=True, text=True, env=env, cwd=str(HERE))
    (OUT / f'{nm}_log.txt').write_text(r.stdout + r.stderr, encoding='utf-8')
    if r.returncode:
        print(r.stdout, r.stderr)
        sys.exit(f'{nm}: the detector stopped (exit {r.returncode}); has {nm}/prims.pkl been made? See README.md')
    print(r.stdout.strip())
    ops[nm] = json.loads((OUT / f'{nm}_openings.json').read_text(encoding='utf-8'))['openings']
for group, (names, key) in KEYS.items():
    have = [n for n in names if n in ops]
    if not have: continue
    merged = OUT / f'all_{group}.json'
    merged.write_text(json.dumps({'openings': [o for n in have for o in ops[n]]}, indent=1), encoding='utf-8')
    r = subprocess.run([sys.executable, '-B', str(HERE / 'tools' / 'score.py'), str(key), str(merged), '--out', str(OUT / f'score_{group}.json')],
                       capture_output=True, text=True, env=env)
    (OUT / f'score_{group}.txt').write_text(r.stdout, encoding='utf-8')
    print(f'\n=== {group}: {", ".join(have)}  (key {key.parent.name}/{key.name}) ===')
    print(r.stdout)
    if len(have) < len(names): print('(only', ', '.join(have), 'were run, so the key rows of the other drawings count as missed)')
    S = json.loads((OUT / f'score_{group}.json').read_text(encoding='utf-8'))
    print('detections the key does not list:', {f: len(v['extra']) for f, v in S['floors'].items()}, 'total', sum(len(v['extra']) for v in S['floors'].values()))
