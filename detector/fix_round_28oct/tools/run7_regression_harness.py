"""Run a detector copy on all six drawings and compare with the baseline (the regression harness of the fourth-office fix round).

Usage: python -B run7.py <detector_dir> <out_dir> [--png]
  <detector_dir>  a folder holding openings.py, geomkit.py, render_openings.py and tools/ (a COPY of the project's detector that you may edit)
  <out_dir>       where the outputs go (created)
Runs the copy's openings.py with the project's mappings on: sukhumvit, presidential, bank1, bank2 (the four older drawings, scored
against the project's key detector/keys/final/all.json: baseline 139 of 143) and tower L29, L30 (the fourth office, scored against
the answer key P0/keys4/final/tower.json, or the file named by the environment variable TOWER_KEY).
Prints per-floor scores, the number of extras, whether each drawing's openings are identical to the baseline, and timings.
"""
import json, os, subprocess, sys, time
from pathlib import Path

PRJ = Path('C:/Users/DWP2/Desktop/Project walkthrough')
P0 = Path('C:/Users/DWP2/AppData/Local/Temp/claude/c--Users-DWP2-Desktop-Project-walkthrough/e1e2f8a1-5b17-462a-bbe8-01925d989674/scratchpad/p0')
BASE = Path(os.environ.get('BASELINE_DIR') or (P0 / 'fix4' / 'baseline'))      # outputs to compare with (default: the unmodified detector)
OLD = ('sukhumvit', 'presidential', 'bank1', 'bank2')
NEW = ('l29', 'l30')
MAP = {n: PRJ / 'detector' / 'mappings' / f'{n}.json' for n in OLD}
MAP.update({n: P0 / 'mappings_v2' / f'{n}.json' for n in NEW})
SCORE = PRJ / 'detector' / 'tools' / 'score.py'
OLDKEY = PRJ / 'detector' / 'keys' / 'final' / 'all.json'
NEWKEY = Path(os.environ.get('TOWER_KEY') or (P0 / 'keys4' / 'final' / 'tower.json'))

args = [a for a in sys.argv[1:] if not a.startswith('--')]
det, out = Path(args[0]).resolve(), Path(args[1]).resolve()
png = '--png' in sys.argv
out.mkdir(parents=True, exist_ok=True)
env = dict(os.environ, PYTHONIOENCODING='utf-8', OPENINGS_DATA=str(P0 / 'proj_data'))
ops = {}
t_all = time.time()
for n in OLD + NEW:
    cmd = [sys.executable, '-B', 'openings.py', str(MAP[n]), str(out / f'{n}_openings.json')]
    if png: cmd += ['--png', str(out)]
    t0 = time.time()
    r = subprocess.run(cmd, capture_output=True, text=True, env=env, cwd=str(det))
    (out / f'{n}_log.txt').write_text(r.stdout + r.stderr, encoding='utf-8')
    if r.returncode:
        print(f'{n}: THE DETECTOR STOPPED (exit {r.returncode})\n{r.stdout[-1500:]}\n{r.stderr[-1500:]}')
        sys.exit(1)
    ops[n] = json.loads((out / f'{n}_openings.json').read_text(encoding='utf-8'))['openings']
    bp = BASE / f'{n}_openings.json'
    same = bp.exists() and json.loads(bp.read_text(encoding='utf-8'))['openings'] == ops[n]       # the openings, not the recorded mapping path
    print(f'{n:13s} {len(ops[n]):3d} openings in {time.time() - t0:4.1f} s   {"identical to the baseline" if same else "DIFFERENT from the baseline"}')


def score(key, names, tag):
    merged = out / f'all_{tag}.json'
    merged.write_text(json.dumps({'openings': [o for n in names for o in ops[n]]}, indent=1), encoding='utf-8')
    r = subprocess.run([sys.executable, '-B', str(SCORE), str(key), str(merged), '--out', str(out / f'score_{tag}.json')],
                       capture_output=True, text=True, env=env)
    (out / f'score_{tag}.txt').write_text(r.stdout, encoding='utf-8')
    S = json.loads((out / f'score_{tag}.json').read_text(encoding='utf-8'))
    for f, v in S['floors'].items():
        print(f"  {f:22s} key {v['keyCount']:3d}  detected {v['detCount']:3d}  matched {v.get('matched', 0):3d}  RIGHT {v.get('right', 0):3d}/{v['keyCount']:<3d}  extras {len(v['extra']):2d}  missed {len(v['missed'])}")
    t = S['total']
    print(f"  TOTAL {tag}: key {t['keyCount']} right {t['right']} -> {t['rightShare']}   (extras {sum(len(v['extra']) for v in S['floors'].values())})")
    return S


print('--- the four older drawings against detector/keys/final/all.json (baseline 139 of 143) ---')
S_old = score(OLDKEY, OLD, 'old')
print('--- tower floors against', NEWKEY.name, '---')
S_new = score(NEWKEY, NEW, 'tower')
print(f'total {time.time() - t_all:.0f} s')
