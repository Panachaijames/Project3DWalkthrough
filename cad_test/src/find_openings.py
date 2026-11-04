"""Find the doors, windows and passages in the house plan (26 Oct 2026) -> openings.json.

Runs the Phase 0 opening detector (openings.py, used as it is: no edits to its output, nothing added or removed) on
this folder's plan.dxf with the drawing's layer mapping, then adds the door and window heights read from the
elevations. Run it after build3d.py (it copies the frozen model frame from house3d.json) and before merge_cad.py.

openings.json, in DRAWING metres like the detector (the upper plan where it sits on the sheet; model metres are
X = x + shift[floor] - centre[0], Y = y - centre[1]):
  {source, detector, mapping, frame: {centre, shift}, heights: {<floor>: {doorHead, windowSill, windowHead}},
   doorLayers: [the mapping's door layers, for the replay],
   openings: [{<every detector field: id, floor, kind, subtype, a, b, width, wallThickness, host, hinge, swing,
                confidence, evidence, eitherKind>, floorKey: 'ground'|'upper', sill, head, heightFrom}],
   heightRows: [{floor, a, b, sill, head, kind, matched: [ids]}]}
  head / sill are metres above the floor level; a door's sill is 0.

Usage: python -B find_openings.py [--detector DIR] [--mapping FILE] [--heights FILE] [--png DIR]
  --detector  folder with openings.py and geomkit.py, and tools/prims.py in it or in a folder above it (default:
              $OPENINGS_DETECTOR, else the first of these that holds openings.py: <project>/detector (two folders
              up from this script: the project layout), then ../detector)
  --mapping   the drawing's layer roles for the detector (default: openings_mapping.json here)
  --heights   heights from the elevations (default: heights.json here; without it the plan's defaults,
              walkthrough_app_plan.md section 3.2: doors to 2.10 m, windows 0.90-2.10 m, and a note says so)
  --png DIR   also draw the detector's marked plans (openings_<floor>.png)
The detector reads a flattened copy of the drawing (prims.pkl); it is rebuilt here from plan.dxf and regions.json
whenever either is newer than it (about 10 s).
Glass corners: two glazed openings at right angles whose ends meet within 0.15 m (a post-less corner) take the same
heights: when an elevation row matched only one leg (the elevations show one face of a corner), the other takes its
sill and head.
"""
import argparse, hashlib, json, math, os, pickle, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
CANDIDATES = [HERE.parent.parent / 'detector', HERE.parent / 'detector']

ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
ap.add_argument('--detector', default=os.environ.get('OPENINGS_DETECTOR') or
                next((str(d) for d in CANDIDATES if (d / 'openings.py').exists()), str(CANDIDATES[0])))
ap.add_argument('--mapping', default='openings_mapping.json')
ap.add_argument('--heights', default='heights.json')
ap.add_argument('--png')
args = ap.parse_args()
t0 = time.time()

DET = Path(args.detector).resolve()
TOOLS = next((p / 'tools' for p in [DET] + list(DET.parents) if (p / 'tools' / 'prims.py').exists()), None)
if not (DET / 'openings.py').exists() or TOOLS is None:
    raise SystemExit(f'opening detector not found in {DET} (needs openings.py and geomkit.py, and tools/prims.py in it '
                     f'or above it; pass --detector DIR or set OPENINGS_DETECTOR)')
sys.path[:0] = [str(DET), str(TOOLS)]
import prims                                   # the detector's drawing reader (flattens blocks, keeps inserts)
import openings as detector                    # the detector itself, unchanged

# ---------------------------------------------------------------------------------------------- 1. the drawing cache
# The same flattening as tools/prims.py build('sukhumvit'), but from this folder's plan.dxf and regions.json.
CACHE = Path('prims.pkl')
if not CACHE.exists() or CACHE.stat().st_mtime < max(Path('plan.dxf').stat().st_mtime, Path('regions.json').stat().st_mtime):
    items, layers = prims._flatten('plan.dxf')
    R = json.loads(Path('regions.json').read_text())
    regs = {'ground': [v / 1000 for v in R['plan_left']], 'upper': [v / 1000 for v in R['plan_right']]}
    def area(pts, pad=0.5):
        for k, r in regs.items():
            if all(r[0] - pad <= x <= r[2] + pad and r[1] - pad <= y <= r[3] + pad for x, y in pts): return k
        return None
    for d in items:
        P = prims._pts(d)
        d['area'] = area(P) if P else None
    CACHE.write_bytes(pickle.dumps({'items': items, 'layers': layers}))
    print(f'drawing cache: {len(items)} items, {sum(1 for d in items if d["area"])} in the two plans ({time.time() - t0:.0f} s)')
prims.load = lambda name: pickle.loads(CACHE.read_bytes())       # the detector reads this drawing's cache

# ---------------------------------------------------------------------------------------------- 2. detect
MAP = Path(args.mapping)
raw_path = Path('openings_detected.json')                      # the detector's own output file, as it wrote it
detector.run(str(MAP), str(raw_path), args.png)
found = json.loads(raw_path.read_text(encoding='utf-8'))['openings']
mapping = json.loads(MAP.read_text(encoding='utf-8'))
floor_key = {v: k for k, v in mapping['floors'].items()}       # 'sukhumvit:ground' -> 'ground'

# ---------------------------------------------------------------------------------------------- 3. heights
# Per floor defaults from the elevations, then the rows read off the elevations for particular openings: a row
# applies to every detected opening on the same wall line (parallel, centre lines <= 0.2 m apart) that it overlaps
# by at least half of the shorter of the two.
PLAN_DEFAULTS = {'doorHead': 2.10, 'windowSill': 0.90, 'windowHead': 2.10}   # walkthrough_app_plan.md section 3.2
if Path(args.heights).exists():
    H = json.loads(Path(args.heights).read_text(encoding='utf-8'))
else:
    print(f'note: {args.heights} not found, so the plan defaults are used on every floor (doors to 2.10 m, windows 0.90-2.10 m)')
    H = {'source': 'plan defaults (walkthrough_app_plan.md section 3.2): no heights file', 'defaults': {}, 'matched': []}
# every floor of the mapping gets the plan defaults for whatever its heights file does not give
DEF = {f: {**PLAN_DEFAULTS, **H['defaults'].get(f, {})} for f in list(floor_key.values()) + [f for f in H['defaults'] if f not in floor_key.values()]}
# A window the detector reads as an opening over a low wall (both wall faces drawn on across the gap, no glass) has a
# low wall below it in the drawing; no elevation shows such inner openings, so it takes the plan's default sill
# (walkthrough_app_plan.md section 3.2): 0.90 m. Rows read off the elevations still override it.
LOW_WALL_SILL = 0.90

def frame(a, b):
    L = math.dist(a, b); u = ((b[0] - a[0]) / L, (b[1] - a[1]) / L)
    return u, L

def same_line(o, row):
    (ua, La), (ub, Lb) = frame(o['a'], o['b']), frame(row['a'], row['b'])
    if abs(ua[0] * ub[0] + ua[1] * ub[1]) < 0.98: return False
    n = (-ua[1], ua[0])
    off = [(p[0] - o['a'][0]) * n[0] + (p[1] - o['a'][1]) * n[1] for p in (row['a'], row['b'])]
    if max(abs(v) for v in off) > 0.2: return False
    s = sorted((p[0] - o['a'][0]) * ua[0] + (p[1] - o['a'][1]) * ua[1] for p in (row['a'], row['b']))
    overlap = min(La, s[1]) - max(0.0, s[0])
    return overlap >= 0.5 * min(La, Lb)

rows = []
for row in H.get('matched', []):
    rows.append({**row, 'matched': []})
out = []
for o in found:
    f = floor_key[o['floor']]
    d = DEF[f]
    if o['kind'] == 'door': sill, head = 0.0, d['doorHead']
    elif o['kind'] == 'window': sill, head = d['windowSill'], d['windowHead']
    else: sill, head = 0.0, d.get('doorHead')                  # passages are not cut; kept for reference
    src = f'elevations: {f} floor default'
    if o['kind'] == 'window' and 'low wall' in o['subtype']:
        sill, src = LOW_WALL_SILL, f'drawing: opening over a low wall, plan default sill {LOW_WALL_SILL:.2f} m; head: {src}'
    for r in rows:
        if r['floor'] == f and same_line(o, r):
            sill, head = (0.0 if o['kind'] == 'door' else float(r['sill'])), float(r['head'])
            src = f"elevations: {r['kind'].strip()} ({r['facade'].split(':')[0]})"
            r['matched'].append(o['id'])
    out.append({**o, 'floorKey': f, 'sill': round(sill, 3), 'head': round(head, 3), 'heightFrom': src})

# Post-less glass corners: both legs get the same heights. The elevations show one face of a corner, so when a row
# matched only one leg, the other takes its sill and head.
glazed = lambda o: o['kind'] == 'window' or bool(o.get('eitherKind'))
from_row = lambda o: o['heightFrom'].startswith('elevations:') and not o['heightFrom'].endswith('default')
corner_pairs = []
for i, o in enumerate(out):
    for q in out[i + 1:]:
        if o['floorKey'] != q['floorKey'] or not (glazed(o) and glazed(q)): continue
        (u, _), (v, _) = frame(o['a'], o['b']), frame(q['a'], q['b'])
        if abs(u[0] * v[0] + u[1] * v[1]) > math.sin(math.radians(10)): continue        # not at right angles
        if min(math.dist(p, r) for p in (o['a'], o['b']) for r in (q['a'], q['b'])) > 0.15: continue
        corner_pairs.append((o, q))
        if from_row(o) != from_row(q):
            src, dst = (o, q) if from_row(o) else (q, o)
            dst['sill'], dst['head'] = src['sill'], src['head']
            dst['heightFrom'] = f"glass corner with {src['id']}: {src['heightFrom']}"

# ---------------------------------------------------------------------------------------------- 4. write
house = json.loads(Path('house3d.json').read_text()) if Path('house3d.json').exists() else {}
sha = hashlib.sha1(Path('plan.dxf').read_bytes()).hexdigest()[:12]
res = {
    'source': {'file': 'plan.dxf', 'sha1': sha},
    'detector': {'folder': str(DET).replace('\\', '/'), 'sha1': hashlib.sha1((DET / 'openings.py').read_bytes()).hexdigest()[:12]},
    'mapping': mapping,
    'frame': {'centre': house.get('centre'), 'shift': house.get('shift'), 'units': 'drawing metres'},
    'heights': DEF, 'heightsSource': H.get('source', ''),
    'doorLayers': mapping['layers'].get('door', []),
    'openings': out,
    'heightRows': [{k: r[k] for k in ('floor', 'a', 'b', 'sill', 'head', 'kind', 'matched')} for r in rows],
}
Path('openings.json').write_text(json.dumps(res, indent=1), encoding='utf-8')
for f in ('ground', 'upper'):
    ops = [o for o in out if o['floorKey'] == f]
    print(f'{f}: ' + ', '.join(f"{sum(1 for o in ops if o['kind'] == k)} {k}s" for k in ('door', 'window', 'passage')))
unmatched = [r for r in rows if not r['matched']]
print(f"heights: {len(rows) - len(unmatched)} of {len(rows)} elevation rows matched a detected opening;"
      f" {sum(1 for o in out if not o['heightFrom'].endswith('default'))} openings take their heights from them")
for r in unmatched:
    print(f"   no opening found for: {r['floor']} {r['a']} - {r['b']} ({r['kind'].strip()})")
for o, q in corner_pairs:
    print(f"   glass corner {o['id']} + {q['id']}: sill / head {o['sill']:.2f}-{o['head']:.2f} and {q['sill']:.2f}-{q['head']:.2f} m")
print(f'openings.json: {len(out)} openings | {time.time() - t0:.1f} s')
