"""Final check (UF): a listing of every file outside app/ (and .git) with its size and modified time, plus every
__pycache__ folder outside app/. python -B listing.py <out.json>"""
import json
import os
import sys

ROOT = r"C:\Users\DWP2\Desktop\Project walkthrough"
out = sys.argv[1]
rows = []
pyc = []
for dp, dns, fns in os.walk(ROOT):
    rel = os.path.relpath(dp, ROOT)
    parts = rel.split(os.sep)
    if parts[0] in ('app', '.git'):
        dns[:] = []
        continue
    for d in dns:
        if d == '__pycache__':
            pyc.append(os.path.join(rel, d))
    for f in fns:
        p = os.path.join(dp, f)
        st = os.stat(p)
        rows.append([os.path.relpath(p, ROOT), st.st_size, st.st_mtime_ns])
rows.sort()
with open(out, 'w', encoding='utf-8') as fh:
    json.dump({'files': rows, 'pycache': sorted(pyc)}, fh)
print(len(rows), 'files;', len(pyc), '__pycache__ folders:', sorted(pyc))
