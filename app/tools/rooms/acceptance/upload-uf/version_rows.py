"""UR: the gap report's head table numbers of each uploaded version, from the acceptance store (read-only).

    python -B version_rows.py <store data dir>
Prints one line per version: stamp, parts, openings, furniture (kinds), flags (to check), and per floor the plate area
and the plate-dropped check flags' titles.
"""
import collections
import json
import sys
from pathlib import Path

from shapely.geometry import Polygon
from shapely.ops import unary_union

store = Path(sys.argv[1]) / 'projects'
ROWS = [('bank-reupload', 1), ('bank-sampeng', 3), ('house-upload', 1), ('suite-upload', 1), ('suite-outlines', 1),
        ('tower-upload', 1), ('suite-revit', 1), ('presidential-suite', 2)]


def load(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))


for pid, n in ROWS:
    v = store / pid / 'versions' / str(n)
    if not v.is_dir():
        print(pid, n, 'missing')
        continue
    m, ver = load(v / 'model.json'), load(v / 'version.json')
    flags = load(v / 'source' / 'flags.json')['flags']
    kinds = collections.Counter(f['kind'] for f in m.get('furniture') or [])
    check = sum(1 for f in flags if f['severity'] == 'check')
    by = collections.Counter(f['kind'] for f in flags)
    print(f"{pid} v{n}: stamp {ver['stamp']}, parts {len(m['parts'])}, openings {len(m['openings'])}, "
          f"furniture {len(m.get('furniture') or [])} in {len(kinds)} kinds, flags {len(flags)} ({check}), by kind {dict(by)}")
    for fl in m['floors']:
        slabs = [Polygon(p['o'], p.get('h') or []).buffer(0) for p in m['parts'] if p['floor'] == fl['key'] and p['kind'] == 'slab']
        area = unary_union(slabs).area if slabs else 0.0
        pd = [f['title'] for f in flags if f['kind'] == 'plate-dropped' and f['floor'] == fl['key'] and f['severity'] == 'check']
        rl = [f['title'] for f in flags if f['kind'] == 'room-label' and f['floor'] == fl['key'] and f['severity'] == 'check']
        lint = sum(1 for p in m['parts'] if p['floor'] == fl['key'] and p['kind'] == 'lintel')
        print(f"    {fl['key']}: plate {area:.1f} m2, lintels {lint}, unfloored flags {pd}, room-name flags {rl}")
