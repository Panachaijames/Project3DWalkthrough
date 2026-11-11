import os, sys, json, hashlib
root = r"C:\Users\DWP2\Desktop\Project walkthrough"
out = sys.argv[1]
rows = []
pyc = []
for dp, dns, fns in os.walk(root):
    rel = os.path.relpath(dp, root)
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
        rows.append([os.path.relpath(p, root), st.st_size, st.st_mtime_ns])
rows.sort()
json.dump({'files': rows, 'pycache': sorted(pyc)}, open(out, 'w', encoding='utf-8'))
print(len(rows), 'files;', len(pyc), '__pycache__ dirs')
