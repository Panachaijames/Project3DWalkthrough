"""Final check (UF): sha1 of every file under a folder (relative paths), or the comparison of two folders.
    python -B tree_sha1.py <dir> <out.json>                 writes {relpath: [bytes, sha1]}
    python -B tree_sha1.py --cmp <a.json|dir> <b.json|dir>  prints the differences; exit 1 when any
Paths use forward slashes. The store's .lock (an empty file made on first use) is listed like any file."""
import hashlib
import json
import os
import sys


def tree(d):
    out = {}
    for dp, dns, fns in os.walk(d):
        for f in fns:
            p = os.path.join(dp, f)
            with open(p, 'rb') as fh:
                data = fh.read()
            out[os.path.relpath(p, d).replace(os.sep, '/')] = [len(data), hashlib.sha1(data).hexdigest()]
    return dict(sorted(out.items()))


def load(x):
    if os.path.isdir(x):
        return tree(x)
    with open(x, encoding='utf-8') as fh:
        return json.load(fh)


if sys.argv[1] == '--cmp':
    A, B = load(sys.argv[2]), load(sys.argv[3])
    added = sorted(set(B) - set(A))
    removed = sorted(set(A) - set(B))
    changed = sorted(k for k in set(A) & set(B) if A[k] != B[k])
    print(f'{len(A)} files vs {len(B)}; only in the second {len(added)}, only in the first {len(removed)}, different {len(changed)}')
    for k in added[:50]:
        print('  +', k, B[k])
    for k in removed[:50]:
        print('  -', k, A[k])
    for k in changed[:50]:
        print('  ~', k, A[k], B[k])
    sys.exit(1 if added or removed or changed else 0)
else:
    t = tree(sys.argv[1])
    with open(sys.argv[2], 'w', encoding='utf-8') as fh:
        json.dump(t, fh, indent=1)
    print(len(t), 'files,', sum(v[0] for v in t.values()), 'bytes')
