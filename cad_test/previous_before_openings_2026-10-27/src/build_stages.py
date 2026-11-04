"""Record what each build step sees, for the build replay in the viewer (16 Oct 2026).

Reads plan.dxf with the same rules as build3d.py and merge_cad.py and writes house3d_stages.json:
  floors.<f>.lines.<cat>  flat [x1, y1, x2, y2, ...] in model metres (the frame of house3d.json)
                          cat = wall | glass | window | stair (kept) or noise (everything the build ignores)
  floors.<f>.pairs.<kind> flat quads [x0, y0, ... x3, y3, ...]: the strips between paired wall faces
  floors.<f>.sheet        [dx, dy] from the floor's aligned place to where it sits on the drawing sheet
  stats                   the counts the captions quote
Usage: python build_stages.py   (in the folder with plan.dxf, regions.json, grid.json, house3d*.json)
"""
import collections, json, math, time
from ezdxf import recover, bbox, path as ezpath
from shapely.geometry import LineString
from shapely.ops import unary_union
from merge_cad import strips, solidify

t0 = time.time()
doc, _ = recover.readfile('plan.dxf'); msp = doc.modelspace()
layer_lt = {l.dxf.name: l.dxf.get('linetype', 'Continuous') for l in doc.layers}
regions = json.load(open('regions.json'))
DX_UPPER = -74021.0                     # same as build3d.py: the 24 shared grid labels
NOISE_CAP = 9000                        # per floor: keep the longest ignored lines, enough to read as a drawing

def eff_lt(e, lay, inh_lt):
    lt = e.dxf.get('linetype', 'BYLAYER')
    if lt.upper() == 'BYLAYER': return layer_lt.get(lay, 'Continuous')
    if lt.upper() == 'BYBLOCK': return inh_lt or 'Continuous'
    return lt

def cat_of(layer):                      # same as build3d.py
    L = layer.upper()
    if L.endswith('COLCL'): return None
    if 'WALL-GL' in L: return 'glass'
    if 'WALL' in L or L == 'COL' or 'STRUCTURE' in L: return 'wall'
    if L == 'WIN' or 'GRILL' in L: return 'window'
    if L == 'STAIR': return 'stair'
    return None

def noise_group(layer, kind):           # only for the caption: what the ignored lines were
    L = layer.upper()
    if kind == 'DIMENSION' or 'DIM' in L: return 'dimensions'
    if 'GRID' in L or L.endswith('COLCL'): return 'grid lines'
    if 'DOOR' in L: return 'doors'
    if 'FURN' in L or 'SANI' in L or 'FIX' in L or 'EQUIP' in L: return 'furniture'
    if 'HATCH' in L or 'PAT' in L or 'FLOOR' in L or 'TILE' in L or kind == 'HATCH': return 'floor patterns'
    if 'TEXT' in L or 'NAME' in L or 'TAG' in L: return 'labels'
    return 'other'

def region_of(b, pad=500):
    for name, floor in (('plan_left', 'ground'), ('plan_right', 'upper')):
        r = regions[name]
        if b.extmin.x >= r[0] - pad and b.extmax.x <= r[2] + pad and b.extmin.y >= r[1] - pad and b.extmax.y <= r[3] + pad:
            return floor
    return None

kept = collections.defaultdict(list)    # (floor, cat) -> [x1, y1, x2, y2] in m, shifted, not yet centred
noise = collections.defaultdict(list)   # floor -> [x1, y1, x2, y2, length]
read = collections.Counter()            # floor -> entities read in the plan areas
ignored = collections.defaultdict(collections.Counter)   # floor -> group -> entities
texts = collections.Counter()
plan_layers = set()                     # every layer with something in the two plan areas
kept_layers = collections.defaultdict(set)              # cat -> layers whose lines were kept

def segments_of(e, step):
    try: p = ezpath.make_path(e)
    except Exception: return []
    pts = list(p.flattening(distance=step))
    return [(a, c) for a, c in zip(pts, pts[1:])]

def add(e, lay, lt):
    kind = e.dxftype()
    if kind in ('POINT', 'ATTRIB', 'ATTDEF', 'VIEWPORT'): return
    try: b = bbox.extents([e])
    except Exception: return
    if not b.has_data: return
    floor = region_of(b)
    if not floor: return
    read[floor] += 1
    plan_layers.add(lay)
    if kind in ('TEXT', 'MTEXT'):
        texts[floor] += 1; ignored[floor]['labels'] += 1; return
    cat = cat_of(lay)
    keep = cat is not None and lt.upper() == 'CONTINUOUS' and kind not in ('HATCH', 'DIMENSION', 'SOLID')
    if keep and cat in ('wall', 'glass') and kind != 'LINE' and max(b.extmax.x - b.extmin.x, b.extmax.y - b.extmin.y) < 150:
        keep = False                     # tiny decorative shapes on the wall layer (build3d.py drops them too)
    shift = DX_UPPER if floor == 'upper' else 0.0
    if keep:
        kept_layers[cat].add(lay)
        for a, c in segments_of(e, 15):
            L = math.dist((a.x, a.y), (c.x, c.y))
            if L < 5 or L > 25000: continue
            kept[(floor, cat)].append([(a.x + shift) / 1000, a.y / 1000, (c.x + shift) / 1000, c.y / 1000])
        return
    ignored[floor][noise_group(lay, kind) if cat is None else 'hidden and centre lines'] += 1
    for a, c in segments_of(e, 40):
        L = math.dist((a.x, a.y), (c.x, c.y))
        if L < 5 or L > 60000: continue
        noise[floor].append([(a.x + shift) / 1000, a.y / 1000, (c.x + shift) / 1000, c.y / 1000, L])

def walk(e, inh=None, inh_lt=None):
    lay = e.dxf.get('layer', '0')
    if lay == '0' and inh: lay = inh
    lt = eff_lt(e, lay, inh_lt)
    if e.dxftype() in ('INSERT', 'DIMENSION'):
        try:
            for v in e.virtual_entities(): walk(v, lay, lt)
        except Exception: pass
    else:
        add(e, lay, lt)

for e in msp: walk(e)

# Centre exactly as build3d.py does (wall + glass lines of both floors), then check against house3d.json.
allw = [s for (f, c), v in kept.items() for s in v if c in ('wall', 'glass')]
cx = (min(min(s[0], s[2]) for s in allw) + max(max(s[0], s[2]) for s in allw)) / 2
cy = (min(min(s[1], s[3]) for s in allw) + max(max(s[1], s[3]) for s in allw)) / 2
H = json.load(open('house3d.json'))
for (f, c), v in sorted(kept.items()):
    ref = H['segments'].get(f'{f}:{c}', [])
    same = len(ref) == len(v) and all(abs(round(v[0][i] - (cx, cy)[i % 2], 3) - ref[0][i]) < 0.002 for i in range(4))
    print(f'{f}:{c}: {len(v)} lines', 'matches house3d.json' if same else f'DIFFERS from house3d.json ({len(ref)})')

def flat(segs, nd):
    out = []
    for s in segs:
        out += [round(s[0] - cx, nd), round(s[1] - cy, nd), round(s[2] - cx, nd), round(s[3] - cy, nd)]
    return out

M = json.load(open('house3d_merged.json'))
grid = json.load(open('grid.json', encoding='utf-8'))
labels_matched = len({l for l, _, _ in grid.get('plan_left', [])} & {l for l, _, _ in grid.get('plan_right', [])})
kept_any = set().union(*kept_layers.values()) if kept_layers else set()
out = {'source': {'file': 'Test Sukhumvit Residence.dwg', 'layers': len(doc.layers), 'units': 'mm'},
       'floors': {}, 'stats': {'gridLabels': labels_matched, 'floors': {},
                               'planLayers': len(plan_layers),        # layers with anything in the two plan areas
                               'layers': {**{c: sorted(kept_layers[c]) for c in ('wall', 'glass', 'window', 'stair')},
                                          'ignored': sorted(plan_layers - kept_any)}}}
for floor in ('ground', 'upper'):
    lines = {c: flat(kept[(floor, c)], 3) for c in ('wall', 'glass', 'window', 'stair')}
    nz = sorted(noise[floor], key=lambda s: -s[4])
    lines['noise'] = flat(nz[:NOISE_CAP], 2)
    wl = H['segments'].get(f'{floor}:wall', [])
    gl = H['segments'].get(f'{floor}:glass', []) + H['segments'].get(f'{floor}:window', [])
    wrects, wpairs, _ = strips(wl, 0.04, 0.45)
    grects, gpairs, _ = strips(gl, 0.02, 0.30)
    quads = lambda rects: [round(v, 3) for r in rects for x, y in list(r.exterior.coords)[:4] for v in (x, y)]
    # Share of wall-line length that ended up inside a wall (the rest are single-line items), as merge_cad.py measures it.
    covered = unary_union(solidify(wrects, 0.12)).buffer(0.04)
    total = sum(LineString([(a, b), (c, d)]).length for a, b, c, d in wl)
    single = sum(p.length for a, b, c, d in wl for p in [LineString([(a, b), (c, d)]).difference(covered)] if p.length > 0.2)
    out['floors'][floor] = {
        'sheet': [round(-DX_UPPER / 1000, 3), 0.0] if floor == 'upper' else [0.0, 0.0],
        'lines': lines,
        'pairs': {'wall': quads(wrects), 'glass': quads(grects)},
    }
    out['stats']['floors'][floor] = {
        'read': read[floor], 'texts': texts[floor],
        'kept': {c: len(kept[(floor, c)]) for c in ('wall', 'glass', 'window', 'stair')},
        'ignored': dict(ignored[floor].most_common()), 'ignoredLines': len(noise[floor]), 'noiseShown': min(len(nz), NOISE_CAP),
        'pieces': {'wall': len(wrects), 'glass': len(grects)},
        'runs': {k: len(M['solids'].get(f'{floor}:{k}', [])) for k in ('wall', 'glass', 'single')},
        'pairedShare': round(1 - single / total, 3) if total else 0,
        'level': H['levels'][floor], 'height': round(H['tops'][floor] - H['levels'][floor], 3),
    }
json.dump(out, open('house3d_stages.json', 'w'), separators=(',', ':'))
print(json.dumps(out['stats'], indent=1))
import os
print('house3d_stages.json', round(os.path.getsize('house3d_stages.json') / 1024), 'KB |', round(time.time() - t0, 1), 's')
