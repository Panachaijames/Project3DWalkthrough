"""Sweep one module constant of a detector copy over the six drawings.

Usage: python sweep_const.py <detector_dir> <NAME> <value> [<value> ...]
For each value: copies the detector, sets `NAME = value` in its openings.py (the first top-level assignment), runs run7.py and
prints the scores (older key, tower key), the extras and how many openings differ from the unmodified copy's output.
"""
import json, os, re, shutil, subprocess, sys
from pathlib import Path

P0 = Path('C:/Users/DWP2/AppData/Local/Temp/claude/c--Users-DWP2-Desktop-Project-walkthrough/e1e2f8a1-5b17-462a-bbe8-01925d989674/scratchpad/p0')
FIX = P0 / 'fix4'
det = Path(sys.argv[1]).resolve()
name = sys.argv[2]
vals = sys.argv[3:]
env = dict(os.environ, PYTHONIOENCODING='utf-8', TOWER_KEY=str(P0 / 'keys4' / 'final' / 'tower_audited.json'))
tmp_det = FIX / 'sweep_tmp' / 'detector'
base_out = FIX / 'sweep_tmp' / 'out_base'
if tmp_det.parent.exists(): shutil.rmtree(tmp_det.parent)
tmp_det.parent.mkdir(parents=True)


def run(det_dir, out):
    env2 = dict(env, BASELINE_DIR=str(base_out) if base_out.exists() else str(FIX / 'baseline_integrated_c'))
    r = subprocess.run([sys.executable, '-B', str(FIX / 'run7.py'), str(det_dir), str(out)], capture_output=True, text=True, env=env2)
    return r.stdout + r.stderr


def lines(txt):
    old = [l for l in txt.splitlines() if 'TOTAL old' in l]
    tw = [l for l in txt.splitlines() if 'TOTAL tower' in l]
    diff = [l.split()[0] for l in txt.splitlines() if 'DIFFERENT from the baseline' in l]
    return (old[0].strip() if old else '?'), (tw[0].strip() if tw else '?'), diff


shutil.copytree(det, tmp_det, ignore=shutil.ignore_patterns('__pycache__'))
out0 = FIX / 'sweep_tmp' / 'out_base'
txt = run(tmp_det, out0)
print('unmodified :', *lines(txt)[:2], flush=True)
src = (det / 'openings.py').read_text(encoding='utf-8')
pat = re.compile(r'^(' + re.escape(name) + r'\s*=\s*)([0-9.eE+-]+)', re.M)
m = pat.search(src)
assert m, f'{name} not found'
print(f'{name} is {m.group(2)} in the copy')
for v in vals:
    s2 = pat.sub(lambda mm: mm.group(1) + v, src, count=1)
    (tmp_det / 'openings.py').write_text(s2, encoding='utf-8')
    out = FIX / 'sweep_tmp' / f'out_{name}_{v}'
    txt = run(tmp_det, out)
    old, tw, diff = lines(txt)
    print(f'{name}={v:<6} {old} | {tw} | differs from unmodified: {diff}', flush=True)
