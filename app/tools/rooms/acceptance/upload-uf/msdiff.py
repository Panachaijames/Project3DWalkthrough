"""Final check (UF): two 3ds Max scripts compared line by line (CRLF), as JSON on stdout:
equal bytes, line counts, the CRLF check, and the lines that differ (difflib, no context).
    python -B msdiff.py <a.ms> <b.ms>"""
import difflib
import hashlib
import json
import sys
from pathlib import Path

a, b = Path(sys.argv[1]).read_bytes(), Path(sys.argv[2]).read_bytes()
la, lb = a.decode('latin-1').split('\r\n'), b.decode('latin-1').split('\r\n')
diff = [l for l in difflib.unified_diff(la, lb, lineterm='', n=0) if l[:1] in '+-' and l[:3] not in ('---', '+++')]
print(json.dumps({
    'equal': a == b, 'sha1': [hashlib.sha1(a).hexdigest(), hashlib.sha1(b).hexdigest()],
    'lines': [a.count(b'\r\n'), b.count(b'\r\n')],
    'crlfOnly': [a.count(b'\r\n') == a.count(b'\n'), b.count(b'\r\n') == b.count(b'\n')],
    'removed': sum(1 for l in diff if l.startswith('-')), 'added': sum(1 for l in diff if l.startswith('+')),
    'diff': diff,
}, ensure_ascii=False))
