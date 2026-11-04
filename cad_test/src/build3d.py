"""DWG test house: the wall, glass, window and stair lines of both floors -> house3d.json (see README.md).
house3d.json: {levels, tops, centre: [cx, cy] (frozen model origin, drawing metres), shift: {floor: dx (m)},
segments: {'<floor>:<cat>': [[x1, y1, x2, y2], ...]}} in model metres: X = x + shift[floor] - cx, Y = y - cy."""
import collections, json, math, time
from ezdxf import recover, bbox, path as ezpath
t0 = time.time()
doc, _ = recover.readfile('plan.dxf'); msp = doc.modelspace()
layer_lt = {l.dxf.name: l.dxf.get('linetype', 'Continuous') for l in doc.layers}
def eff_lt(e, lay, inh_lt):
    lt = e.dxf.get('linetype', 'BYLAYER')
    if lt.upper() == 'BYLAYER': return layer_lt.get(lay, 'Continuous')
    if lt.upper() == 'BYBLOCK': return inh_lt or 'Continuous'
    return lt
skipped = __import__('collections').Counter()
regions = json.load(open('regions.json'))
DX_UPPER = -74021.0                       # from the 24 shared grid labels (numbered gridlines)
LEVELS = {'ground': 0.90, 'upper': 4.80}  # from the elevation level tags (m)
TOP    = {'ground': 4.80, 'upper': 8.30}  # next floor level / roof beam (m)
def cat_of(layer):
    L = layer.upper()
    if L.endswith('COLCL'): return None
    if 'WALL-GL' in L: return 'glass'
    if 'WALL' in L or L == 'COL' or 'STRUCTURE' in L: return 'wall'
    if L == 'WIN' or 'GRILL' in L: return 'window'
    if L == 'STAIR': return 'stair'
    return None
def in_region(b, r, pad=500):
    return b.extmin.x >= r[0]-pad and b.extmax.x <= r[2]+pad and b.extmin.y >= r[1]-pad and b.extmax.y <= r[3]+pad
segs = collections.defaultdict(list)   # (floor, cat) -> [(x1,y1,x2,y2) in m]
counts = collections.Counter()
def add(e, lay, lt='Continuous'):
    cat = cat_of(lay)
    if cat and lt.upper() != 'CONTINUOUS':
        skipped[(lay, lt.upper())] += 1; return
    if not cat or e.dxftype() in ('HATCH', 'TEXT', 'MTEXT', 'ATTRIB', 'DIMENSION', 'SOLID', 'POINT'): return
    try: b = bbox.extents([e])
    except Exception: return
    if not b.has_data: return
    if cat in ('wall', 'glass') and e.dxftype() != 'LINE' and max(b.extmax.x - b.extmin.x, b.extmax.y - b.extmin.y) < 150:
        skipped[('tiny shape', e.dxftype())] += 1; return
    floor = 'ground' if in_region(b, regions['plan_left']) else ('upper' if in_region(b, regions['plan_right']) else None)
    if not floor: return
    try: p = ezpath.make_path(e)
    except Exception: return
    pts = list(p.flattening(distance=15))
    shift = DX_UPPER if floor == 'upper' else 0.0
    for a, c in zip(pts, pts[1:]):
        L = math.dist((a.x, a.y), (c.x, c.y))
        if L < 5 or L > 25000: continue            # drop tiny bits and very long site/boundary lines
        segs[(floor, cat)].append([round((a.x+shift)/1000, 3), round(a.y/1000, 3), round((c.x+shift)/1000, 3), round(c.y/1000, 3)])
        counts[(floor, cat)] += 1
def walk(e, inh=None, inh_lt=None):
    lay = e.dxf.get('layer', '0')
    if lay == '0' and inh: lay = inh
    lt = eff_lt(e, lay, inh_lt)
    if e.dxftype() == 'INSERT':
        try:
            for v in e.virtual_entities(): walk(v, lay, lt)
        except Exception: pass
    else:
        add(e, lay, lt)
for e in msp: walk(e)
for k, n in sorted(counts.items()): print(k, n, 'segments')
print('skipped non-continuous:', dict(skipped))
# centre on the ground floor footprint
allw = [s for (f, c), v in segs.items() for s in v if c in ('wall', 'glass')]
cx = (min(min(s[0], s[2]) for s in allw) + max(max(s[0], s[2]) for s in allw)) / 2
cy = (min(min(s[1], s[3]) for s in allw) + max(max(s[1], s[3]) for s in allw)) / 2
# The model's origin is frozen (26 Oct 2026): the openings, the tests and the viewer's start spots are placed in this
# frame, so a change in which lines count as walls must not move the model. It is the middle of the kept wall and
# glass lines of both floors, as computed above; if that ever differs, the frozen centre is used and a warning printed.
FROZEN_CENTRE = (30.8095, 16.3425)
if abs(cx - FROZEN_CENTRE[0]) > 1e-6 or abs(cy - FROZEN_CENTRE[1]) > 1e-6:
    print(f'WARNING: the wall and glass lines now centre on ({cx:.4f}, {cy:.4f}); keeping the frozen centre {FROZEN_CENTRE}')
    cx, cy = FROZEN_CENTRE
out = {'levels': LEVELS, 'tops': TOP, 'centre': [round(cx, 4), round(cy, 4)],
       'shift': {'ground': 0.0, 'upper': DX_UPPER / 1000}, 'segments': {}}
for (f, c), v in segs.items():
    out['segments'][f'{f}:{c}'] = [[round(s[0]-cx, 3), round(s[1]-cy, 3), round(s[2]-cx, 3), round(s[3]-cy, 3)] for s in v]
json.dump(out, open('house3d.json', 'w'))
print('extent (m):', round(max(max(s[0], s[2]) for s in allw) - min(min(s[0], s[2]) for s in allw), 1), 'x',
      round(max(max(s[1], s[3]) for s in allw) - min(min(s[1], s[3]) for s in allw), 1), '| time', round(time.time()-t0, 1), 's')
