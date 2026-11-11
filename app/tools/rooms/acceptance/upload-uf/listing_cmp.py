"""Final check (UF): compares two listings made by listing.py. python -B listing_cmp.py <before.json> <after.json>"""
import json
import sys

a = json.load(open(sys.argv[1], encoding='utf-8'))
b = json.load(open(sys.argv[2], encoding='utf-8'))
A = {r[0]: r[1:] for r in a['files']}
B = {r[0]: r[1:] for r in b['files']}
added = sorted(set(B) - set(A))
removed = sorted(set(A) - set(B))
changed = sorted(k for k in set(A) & set(B) if A[k] != B[k])
print(f"before {len(A)} files, after {len(B)}; added {len(added)}, removed {len(removed)}, changed {len(changed)}")
for k in added[:40]:
    print('  +', k)
for k in removed[:40]:
    print('  -', k)
for k in changed[:40]:
    print('  ~', k, A[k], B[k])
print('__pycache__ before', a['pycache'], 'after', b['pycache'])
sys.exit(0 if not (added or removed or changed) and a['pycache'] == b['pycache'] else 1)
