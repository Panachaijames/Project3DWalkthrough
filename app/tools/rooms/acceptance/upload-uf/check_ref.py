"""Final check (UF): the shared reference WT_REF against its own manifest (read-only): every output listed is there
with its size and sha1, and nothing else is in proj/ (no stray file written by a builder).
    python -B check_ref.py <ref dir>"""
import hashlib
import json
import sys
from pathlib import Path

ref = Path(sys.argv[1])
man = json.loads((ref / 'manifest.json').read_text(encoding='utf-8'))
outs = man['outputs']
bad, seen = [], set()
for rel, rec in outs.items():
    p = ref / rel
    seen.add(rel.replace('\\', '/'))
    if not p.is_file():
        bad.append(('missing', rel))
        continue
    data = p.read_bytes()
    size = rec.get('bytes') if isinstance(rec, dict) else None
    sha = rec.get('sha1') if isinstance(rec, dict) else rec
    if (size is not None and size != len(data)) or (sha and hashlib.sha1(data).hexdigest() != sha):
        bad.append(('different', rel))
extra = []
for p in ref.rglob('*'):
    if p.is_file() and p.name != 'manifest.json':
        rel = p.relative_to(ref).as_posix()
        if rel not in seen and not rel.startswith('logs/'):
            extra.append(rel)
print(f"manifest made {man.get('madeAt')}; outputs {len(outs)}; missing or different {len(bad)}; files not in the manifest {len(extra)}")
for b in bad[:30]:
    print('  ', b)
for e in extra[:30]:
    print('   extra', e)
print('checks:', [(c['name'], c.get('ok')) for c in man.get('checks', [])])
sys.exit(1 if bad else 0)
