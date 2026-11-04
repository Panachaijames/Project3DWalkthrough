"""Furniture proxy boxes for the Sukhumvit house (29 Oct 2026): the plan's furniture layers -> furniture_house.json, ../house_furniture_list.csv
(the family list for the 3D team) and ../house_furniture_boxes.png (both floors, one box per piece, colour = kind).

furniture/README.md is the contract and furniture/furniture_kit.py holds the vocabulary, the sizes and the merging rules; like the bank
builder (bank_test/src/build_model.py, rule 12) this script only reads the drawing. What it knows about THIS drawing is in furniture.json
(the furniture layers, the office's words, the smallest piece): no coordinates, handles or block names in here. house3d.json,
house3d_merged.json and openings.json are only read: the walls, the openings and the model frame stay as they were.

The sheet holds two plans and two elevations; the furniture in the plans is the interior designer's linked drawing (layer XR_L44$0$I-FURN):
blocks with cryptic names, and loose lines where a block was exploded. Rules, all generic, with physical sizes in metres:
 1. PIECES are block inserts on a furniture layer that are not inside another piece, at any depth. The footprint is the minimum rotated
    rectangle of the geometry drawn inside the insert (the items the cache lists right after it). The family is the name after the last
    '$0$' (the link's name goes in front of a block of a linked drawing); the kind comes from furniture_kit.classify (furniture.words
    first, then the vocabulary, then the layer's words, else 'other'). A piece is on the plan its centre is in. Left out and counted, by
    reason: a skip word, no geometry, a point or a line, outside the two plans, a long side under furniture.minSize or over 12 m, a short
    side under furniture.minDepth (a panel or a strip along a wall), or the same box twice (the linked drawing is bound in twice).
 2. An ASSEMBLY is a block whose name says nothing (kind 'other') but which holds two or more blocks that the vocabulary or the office's
    words know and that stand on the floor (not a computer or a lamp on a desk): a kitchen with its fridges, base cabinets and sink.
    Its parts are the pieces; its own loose lines outline the same casework again and are left out (counted). A block that has a kind
    is one piece even if it is made of nested blocks (an island of base cabinets): its note lists what it holds.
 3. LOOSE SHAPES on the furniture layers that are not inside a piece, drawn with a continuous line type (a dashed line is above the cut
    plane or hidden: not standing on the floor), without the duplicates a bound-in drawing makes: shapes that touch within 1 cm form a
    cluster and, as in the bank builder, a cluster whose hull fills 70 % of its minimum rectangle and that has 3 or more shapes or a closed
    one is a box (furniture_kit.loose_boxes; the clustering is repeated here to know each cluster's members). On top of that: closed
    outlines that only touch (a row of wardrobes, an L or a U of benches) are left out unless the outlines themselves fill 70 % of the
    rectangle, the same size limits as in rule 1 apply, and an outline that encloses the centre of a smaller piece is a rug or a zone, not a
    piece. A loose cluster has no name, so its kind is what furniture.words and the layer's words say about 'loose shapes on <layer>'
    (here: 'other'). Every cluster left out is listed with its reason.
 4. FRAME: pieces are worked out in drawing metres, then moved into the model frame of house3d_merged.json: X = x + shift[floor] - centre[0],
    Y = y - centre[1] (the upper plan is shifted onto the ground plan, as for the walls). The model's doors and passages (same frame) go to
    furniture_kit.finish, which writes each box's 'approach' and the note.
Output: furniture_house.json = {source, offset, frame, floors, furnitureKinds, furniture, furnitureReport}. 'offset' is the model's
centre (what furniture_boxes.js and the family list add to x, y); x_m of an upper-floor row is on the ground plan's grid, add 74.021 for
the place on the sheet.
Usage: python -B build_furniture.py [--config furniture.json] [--cache prims.pkl]
Run it last, in the folder with prims.pkl (the flatten cache find_openings.py writes), regions.json, house3d.json, house3d_merged.json and
openings.json (and plan.dxf, if it is there: openings.json is checked against it); the list and the picture go to the folder above (cad_test/).
"""
import argparse, collections, fnmatch, json, math, pickle, sys, time
from pathlib import Path
from shapely import get_coordinates
from shapely.geometry import LineString, Polygon
from shapely.ops import unary_union
from shapely.strtree import STRtree

HERE = Path(__file__).resolve().parent
for d in (HERE.parent.parent / 'furniture', HERE.parent / 'furniture', HERE / 'furniture'):      # the project layout, then the scratch layouts
    if (d / 'furniture_kit.py').exists():
        sys.path.insert(0, str(d)); break
else:
    raise SystemExit('furniture/furniture_kit.py not found (expected in the project folder)')
sys.path.insert(0, str(HERE))
import furniture_kit as fk                      # furniture/furniture_kit.py: kinds, vocabulary, merging, approaches, CSV
from merge_cad import openings_for              # openings.json, checked against this plan.dxf and this model frame

ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
ap.add_argument('--config', default=str(HERE / 'furniture.json'))
ap.add_argument('--cache', default='prims.pkl')
args = ap.parse_args()
t0 = time.time()

CFG = json.loads(Path(args.config).read_text(encoding='utf-8'))
LAYERS = [l.upper() for l in CFG['layers']]
HEIGHTS, BASES, WORDS, SKIP = CFG.get('heights'), CFG.get('bases'), CFG.get('words'), CFG.get('skip')
MIN_PIECE, MIN_DEPTH = CFG.get('minSize', 0.08), CFG.get('minDepth', 0.0)
FLOORS = ('ground', 'upper')
kind_by = {k['key']: k for k in fk.KINDS}
try:                                                             # a kind the kit does not know or a bad height stops here, before the drawing is read
    fk.classify('', '', WORDS, SKIP); fk.kinds_table(HEIGHTS, BASES)
except ValueError as e:
    raise SystemExit(f'{Path(args.config).name}: {e}')
CONTINUOUS = {'CONTINUOUS', 'BYLAYER', 'BYBLOCK', ''}
ZONE_MARGIN = 0.10      # a loose outline is a rug or a zone if it holds a smaller piece with this much to spare all round (nested outlines sit a few cm apart)
TWIN_SHARE = 0.9        # two loose boxes are one piece drawn twice (an outline and an inner one) if the smaller lies this much inside the larger ...
TWIN_SIZE = 0.7         # ... and is at least this share of its area

# ---------------------------------------------------------------------------------------------------- the model frame, the plans, the cache
H = json.loads(Path('house3d.json').read_text())                 # the frozen model frame: centre, shift, levels
O = openings_for(H)                                              # openings.json, checked against plan.dxf and this frame
if O is None: raise SystemExit('openings.json not found: run find_openings.py (the boxes in a doorway need the openings)')
M = json.loads(Path('house3d_merged.json').read_text())          # the model the viewer shows: its openings and walls, in the same frame
if M.get('centre') != H['centre']:
    raise SystemExit(f"house3d_merged.json is in another model frame ({M.get('centre')}, house3d.json has {H['centre']}): run merge_cad.py")
CX, CY = H['centre']
SHIFT = H['shift']
R = json.loads(Path('regions.json').read_text())
REGION = {'ground': [v / 1000 for v in R['plan_left']], 'upper': [v / 1000 for v in R['plan_right']]}     # regions.json is in mm

# The doors, windows and passages of both floors in model metres (house3d_merged.json: what the viewer walks through), each with its
# floor; checked against openings.json (drawing metres) moved into the model frame the way merge_cad.py does it.
openings = [{**o, 'floor': f} for f in FLOORS for o in M['openings'][f]]
by_id = {o['id']: o for o in openings}
for o in O['openings']:
    m = by_id.get(o['id'])
    mid = ((o['a'][0] + o['b'][0]) / 2 + SHIFT[o['floorKey']] - CX, (o['a'][1] + o['b'][1]) / 2 - CY)
    if m is None or m['floor'] != o['floorKey'] or math.dist(mid, (m['x'], m['y'])) > 0.002:
        raise SystemExit(f"openings.json and house3d_merged.json disagree about {o['id']}: re-run merge_cad.py")
if len(by_id) != len(O['openings']): raise SystemExit('openings.json and house3d_merged.json list different openings: re-run merge_cad.py')

cache = Path(args.cache)
if not cache.exists(): raise SystemExit(f'{cache} not found: run find_openings.py first (it flattens plan.dxf into prims.pkl)')
for dep in ('plan.dxf', 'regions.json'):
    if Path(dep).exists() and Path(dep).stat().st_mtime > cache.stat().st_mtime:
        raise SystemExit(f'{cache} is older than {dep}: run find_openings.py again')
C = pickle.loads(cache.read_bytes())
items, layer_lt = C['items'], C['layers']


def floor_of(pts, pad=0.5):
    """The plan whose region (+ 0.5 m, as the cache's 'area') holds all the points, else None: on the elevations or the site."""
    for k in FLOORS:
        r = REGION[k]
        if all(r[0] - pad <= x <= r[2] + pad and r[1] - pad <= y <= r[3] + pad for x, y in pts): return k
    return None


# ---------------------------------------------------------------------------------------------------- reading the drawing
def furn(d):
    return any(fnmatch.fnmatchcase(d['lay'].upper(), p) for p in LAYERS)


def family(name):
    """'XR_L44$0$FRIDGE-600' -> 'FRIDGE-600': a block of a linked drawing has the link's name and '$0$' in front of its own."""
    return name.split('$0$')[-1].strip()


def continuous(d):
    lt = d.get('lt') or 'BYLAYER'
    if lt.upper() == 'BYLAYER': lt = layer_lt.get(d['lay']) or 'Continuous'
    u = lt.upper().split('$')[-1]
    return u in CONTINUOUS or u.startswith('CONTINUOUS')


def drawn_inside(items, i):
    """The items drawn inside the INSERT at items[i], and the index after it (as in bank_test/src/build_model.py: the cache lists an
    insert and then everything inside it, deeper by one level or more, so this is right for each instance)."""
    depth, j, n = items[i]['depth'], i + 1, len(items)
    while j < n and items[j]['t'] == 'ATTRIB' and items[j]['depth'] == depth: j += 1
    k = j
    while j < n and items[j]['depth'] > depth: j += 1
    return items[k:j], j


def drawn_points(d):
    """The points of a drawn item (a polyline, an arc, a circle, a hatch's loops); an insert or a text draws nothing itself."""
    if d['t'] in ('INSERT', 'ATTRIB') or 'text' in d: return []
    return d.get('pts') or [q for l in d.get('loops', []) for q in l]


def even_odd(loops):
    """A HATCH's boundary loops -> its filled area (nested loops alternate fill / hole)."""
    g = Polygon()
    for l in loops:
        if len(l) < 3: continue
        p = Polygon(l).buffer(0)
        if not p.is_empty: g = g.symmetric_difference(p)
    return g.buffer(0)


def shape_of(d):
    """A loose drawn item as a shapely shape: a closed outline or a hatch is a polygon, anything else a line (None: a point)."""
    if 'loops' in d:
        g = even_odd(d['loops'])
        return None if g.is_empty else g
    p = d.get('pts') or []
    if len(p) > 2 and (d.get('closed') or (len(p) > 3 and math.dist(p[0], p[-1]) < 1e-3)):
        g = Polygon(p).buffer(0)
        return None if g.is_empty else g
    return LineString(p) if len({tuple(q) for q in p}) > 1 else None


def signature(d, nd=3):
    """Identical geometry on the same layer (the linked drawing bound in twice, copies) -> the same signature."""
    if 'loops' in d: return (d['t'], d['lay'], tuple(tuple((round(x, nd), round(y, nd)) for x, y in l) for l in d['loops']))
    p = [(round(x, nd), round(y, nd)) for x, y in d['pts']]
    if d['t'] == 'LINE' or (not d.get('closed') and len(p) > 1 and p[0] > p[-1]): p = p[::-1]
    if d.get('closed') and len(p) > 2:
        k = p.index(min(p)); p = p[k:] + p[:k]
    return (d['t'], d['lay'], tuple(p))


def clusters(shapes):
    """Indices of shapes that touch within fk.TOUCH, grouped: the clustering inside fk.loose_boxes, repeated to know each cluster's members."""
    buf = [s.buffer(fk.TOUCH / 2) for s in shapes]
    tree = STRtree(buf)
    root = list(range(len(shapes)))

    def find(i):
        while root[i] != i: root[i] = root[root[i]]; i = root[i]
        return i
    for i, b in enumerate(buf):
        for j in tree.query(b, predicate='intersects'): root[find(int(j))] = find(i)
    groups = collections.defaultdict(list)
    for i in range(len(shapes)): groups[find(i)].append(i)
    return sorted(groups.values(), key=min)


def too_small_or_big(box):
    """Why a box is no piece by its size (rules 1 and 3), or None."""
    if box['w'] < MIN_PIECE: return f'shorter than {MIN_PIECE:g} m'
    if box['w'] > fk.MAX_SIDE: return f'longer than {fk.MAX_SIDE:g} m'
    if box['d'] < MIN_DEPTH: return f'thinner than {MIN_DEPTH:g} m'
    return None


def furniture_of():
    """Rules 1-3: the pieces of the sheet (drawing coordinates, with their floor), the loose shapes per floor, and what was read and left out."""
    pieces, skipped = [], collections.defaultdict(collections.Counter)
    loose = {k: [] for k in FLOORS}
    seen, opened, assemblies = set(), [], []                  # signatures of loose shapes met; assemblies being read: (end index, name)
    n = collections.Counter()
    i = 0
    while i < len(items):
        d = items[i]
        if d['t'] == 'INSERT' and furn(d):
            kids, j = drawn_inside(items, i)
            n['insertsRead'] += 1
            fam = family(d['name'])
            kind = fk.classify(fam, d['lay'], WORDS, SKIP)
            nested = [k for k in kids if k['t'] == 'INSERT' and furn(k)]
            parts = [fk.classify(family(k['name']), k['lay'], WORDS, SKIP) for k in nested]
            known = [kd for kd in parts if kd not in (None, 'other') and not kind_by[kd]['onTop']]       # parts that stand on the floor
            pts = [q for k in kids for q in drawn_points(k)]
            box = fk.box_of(pts) if pts else None
            if kind == 'other' and len(known) >= 2:          # rule 2: a room's worth of furniture; its parts are met next
                assemblies.append({'block': d['name'], 'parts': len(known), 'size': [round(box['w'], 2), round(box['d'], 2)] if box else None,
                                   'floor': floor_of([(box['x'], box['y'])]) if box else None})
                opened.append((j, d['name']))
                i += 1
                continue
            i = j                                            # the parts of a piece are not pieces: on to what follows the insert
            floor = floor_of([(box['x'], box['y'])]) if box else None
            if kind is None: why = 'name on the skip list'
            elif not pts: why = 'no geometry drawn inside the block'
            elif box is None: why = 'a point or a line (no area)'
            elif floor is None: why = 'outside the two plan areas'
            else: why = too_small_or_big(box)
            if why:
                skipped[why][fam] += 1
                continue
            holds = collections.Counter(family(k['name']) for k in nested)
            note = '; '.join(x for x in (f"inside block {d['path'].split('>')[0]}" if d['depth'] else '',
                                         'holds ' + ', '.join(f'{c} x {f}' for f, c in sorted(holds.items())) if holds else '') if x)
            pieces.append({'floor': floor, 'kind': kind, 'family': fam, 'block': d['name'], 'layer': d['lay'],
                           'handle': d['h'] if d['depth'] == 0 else '', **box, 'on': None, 'n': 1, 'note': note})
            continue
        at, i = i, i + 1
        if not (furn(d) and ('pts' in d or 'loops' in d)): continue
        n['looseShapes'] += 1
        n['layer ' + d['lay']] += 1
        sig = signature(d)
        if sig in seen: n['duplicates'] += 1; continue
        seen.add(sig)
        opened = [(end, name) for end, name in opened if end > at]
        P = drawn_points(d)
        floor = floor_of(P)
        if opened: n['inAssembly'] += 1; skipped['loose shapes inside an assembly (they outline its parts again)'][family(opened[-1][1])] += 1
        elif not continuous(d): n['dashed'] += 1; skipped['loose shapes drawn with a dashed line type (above the cut plane or hidden)'][d['lay']] += 1
        elif floor is None: n['outside'] += 1; skipped['loose shapes outside the two plan areas'][d['lay']] += 1
        else: loose[floor].append(d)
    return pieces, loose, skipped, assemblies, n


def loose_pieces(floor, ds):
    """Rule 3 for one floor: the clusters of its loose shapes -> ([pieces], [clusters left out, with the reason],
    {layer: clusters that are a point or a line}, number of clusters)."""
    shapes = [shape_of(d) for d in ds]
    keep = [i for i, s in enumerate(shapes) if s is not None]
    ds, shapes = [ds[i] for i in keep], [shapes[i] for i in keep]
    pieces, left, points = [], [], collections.Counter()
    groups = clusters(shapes)
    for g in groups:
        sub = [shapes[i] for i in g]
        box = fk.box_of([tuple(c) for s in sub for c in get_coordinates(s)])
        lay = collections.Counter(ds[i]['lay'] for i in g).most_common(1)[0][0]
        if box is None: points[lay] += 1; continue
        boxes, rest = fk.loose_boxes(sub)                   # the kit's rule for this one cluster
        why = rest[0][1] if rest else None
        outlines = all(s.geom_type in ('Polygon', 'MultiPolygon') for s in sub)          # nothing but closed outlines: a table, a bench, a wardrobe, a rug ...
        if not why and len(sub) > 1 and outlines:
            solid = unary_union(sub).area / (box['w'] * box['d'])
            if solid < fk.LOOSE_FILL:
                why = f'closed outlines that touch but fill {solid:.0%} of their rectangle (a row, an L or a U of separate pieces)'
        if not why: why = too_small_or_big(box)
        fam = f'loose shapes on {lay}'
        kind = fk.classify(fam, lay, WORDS, SKIP)
        if not why and kind is None: why = 'layer name on the skip list'
        if why:
            left.append({'floor': floor, 'layer': lay, 'shapes': len(g), 'why': why, **{k: round(box[k], 3) for k in ('x', 'y', 'w', 'd', 'rot')}})
            continue
        pieces.append({'floor': floor, 'kind': kind, 'family': fam, 'block': '', 'layer': lay, 'handle': '',
                       **boxes[0], 'on': None,
                       'note': 'drawn loose, not as a block' + ('; plain outline: nothing says what it is' if outlines else '')})
    return pieces, left, points, len(groups)


def settle(ps, here):
    """The last two checks of rule 3 on one floor's loose boxes `ps`, given the floor's block pieces `here` -> (the boxes kept, the ones left out).
    A rug or a zone outline holds a smaller piece (not one that stands on something) with ZONE_MARGIN to spare; a second outline of the same
    piece (the inner one of two nested outlines) lies inside the larger one: both are drawn but only the outer one is the piece."""
    area = lambda p: p['w'] * p['d']
    rect = {id(p): fk.rect_of(p) for p in ps}
    gone = {}
    for p in ps:
        room = rect[id(p)].buffer(-ZONE_MARGIN)
        if any(q is not p and area(q) < area(p) and not kind_by[q['kind']]['onTop'] and room.contains(fk.rect_of(q)) for q in here + ps):
            gone[id(p)] = 'encloses another piece (a rug or a zone outline)'
    for q in ps:
        if id(q) in gone: continue
        if any(p is not q and id(p) not in gone and area(q) < area(p) and area(q) >= TWIN_SIZE * area(p)
               and rect[id(p)].intersection(rect[id(q)]).area >= TWIN_SHARE * area(q) for p in ps):
            gone[id(q)] = 'the inner outline of a piece drawn twice (its outer outline is the box)'
    left = [{'floor': p['floor'], 'layer': p['layer'], 'shapes': p['n'], 'why': gone[id(p)], **{k: round(p[k], 3) for k in ('x', 'y', 'w', 'd', 'rot')}}
            for p in ps if id(p) in gone]
    return [p for p in ps if id(p) not in gone], left


# ---------------------------------------------------------------------------------------------------- the pieces
pieces, loose, skipped, assemblies, n_read = furniture_of()
left_out, formed = [], 0                                      # loose clusters not made into boxes; clusters made
for floor in FLOORS:
    ps, left, points, n_clusters = loose_pieces(floor, loose[floor])
    formed += n_clusters
    for lay, c in points.items(): skipped['loose clusters that are a point or a line (no area)'][lay] += c
    ps, twice = settle(ps, [p for p in pieces if p['floor'] == floor])
    pieces += ps
    left_out += left + twice
unique, dup = {}, 0                                           # the same box twice (a block bound in twice)
for p in pieces:
    key = (p['floor'], p['family'], p['layer'], round(p['x'], 3), round(p['y'], 3), round(p['w'], 3), round(p['d'], 3), round(p['rot'] % 180, 1))
    if key in unique: dup += 1
    else: unique[key] = p
pieces = list(unique.values())
pieces, fronts = fk.merge_fronts(pieces)
for p in pieces: p['x'], p['y'] = p['x'] + SHIFT[p['floor']] - CX, p['y'] - CY       # rule 4: into the model frame
try:
    furniture, kinds = fk.finish(pieces, FLOORS, HEIGHTS, BASES, openings)
except ValueError as e:
    raise SystemExit(f'{Path(args.config).name}: {e}')
for r in left_out:                                            # the left-out clusters in the model frame too
    if 'x' in r: r['x'], r['y'] = round(r['x'] + SHIFT[r['floor']] - CX, 3), round(r['y'] - CY, 3)

# ---------------------------------------------------------------------------------------------------- numbers, model JSON
per = {k: collections.Counter(p['kind'] for p in furniture if p['floor'] == k) for k in FLOORS}
approach = {k: {'pieces': sum(1 for p in furniture if p['floor'] == k and p['approach']),
                'openingIds': sorted({o for p in furniture if p['floor'] == k for o in p['approach']})} for k in FLOORS}
n_doors = {k: sum(1 for o in openings if o['floor'] == k and o['kind'] in fk.APPROACH_KINDS) for k in FLOORS}
report = {'insertsRead': n_read['insertsRead'], 'assemblies': assemblies, 'duplicateBoxes': dup, 'fronts': fronts,
          'skipped': {why: {'count': sum(c.values()), 'families': dict(c.most_common())} for why, c in sorted(skipped.items())},
          'looseShapes': {'read': n_read['looseShapes'], 'duplicates': n_read['duplicates'], 'inAssembly': n_read['inAssembly'],
                          'dashed': n_read['dashed'], 'outsidePlans': n_read['outside'],
                          'byLayer': {k[6:]: v for k, v in sorted(n_read.items()) if k.startswith('layer ')},
                          'clusters': formed, 'boxes': sum(1 for p in furniture if not p['block']), 'clustersLeftOut': left_out},
          'approach': approach, 'doorsAndPassages': n_doors}
model = {'source': O['source'], 'offset': [CX, CY],
         'frame': {'centre': [CX, CY], 'shift': SHIFT, 'units': 'model metres = drawing metres + shift[floor] - centre'},
         'floors': [{'key': k, 'name': {'ground': 'Ground floor', 'upper': 'Upper floor'}[k], 'level': H['levels'][k]} for k in FLOORS],
         'furnitureKinds': kinds, 'furniture': furniture, 'furnitureReport': report}
Path('furniture_house.json').write_text(json.dumps(model, separators=(',', ':'), ensure_ascii=False), encoding='utf-8')
for k in FLOORS:
    print(f"{k}: {sum(per[k].values())} furniture boxes {dict(per[k])} | {approach[k]['pieces']} in the approach of "
          f"{len(approach[k]['openingIds'])} of {n_doors[k]} doors / passages {approach[k]['openingIds']}")
print(f"read {n_read['insertsRead']} blocks on the furniture layers ({len(assemblies)} assemblies, {dup} boxes twice, "
      f"{fronts['absorbed']} cabinet fronts absorbed), {n_read['looseShapes']} loose shapes ({n_read['duplicates']} duplicates, "
      f"{n_read['inAssembly']} inside an assembly, {n_read['dashed']} dashed, {n_read['outside']} outside the plans), "
      f"{formed} clusters -> {report['looseShapes']['boxes']} loose-shape boxes, {len(left_out)} clusters left out with a reason, "
      f"{sum(skipped['loose clusters that are a point or a line (no area)'].values())} points or lines")
print('blocks left out:', {why: v['count'] for why, v in report['skipped'].items() if not why.startswith('loose')})
for r in left_out: print('   cluster left out:', r)

# ---------------------------------------------------------------------------------------------------- family list and picture
fk.write_csv(Path('..') / 'house_furniture_list.csv', fk.csv_text(furniture, kinds, FLOORS, model['offset']))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import PathPatch, Patch, Polygon as MPoly
from matplotlib.path import Path as MPath

STY = {'plate': dict(facecolor='#f4f4f1', edgecolor='#cfcfc9', lw=0.6), 'wall': dict(facecolor='#8f8a84', edgecolor='none'),
       'glass': dict(facecolor='#b9dcea', edgecolor='#7fb3cc', lw=0.5), 'single': dict(facecolor='#c9a46b', edgecolor='none')}


def ring_patch(rings, **sty):
    verts, codes = [], []
    for loop in rings:
        verts += list(map(tuple, loop)) + [tuple(loop[0])]
        codes += [MPath.MOVETO] + [MPath.LINETO] * (len(loop) - 1) + [MPath.CLOSEPOLY]
    return PathPatch(MPath(verts, codes), **sty)


kind_info = {k['key']: k for k in kinds}
fig, axs = plt.subplots(len(FLOORS), 1, figsize=(20, 9 * len(FLOORS) + 2.5), dpi=90)
for ax, key in zip(axs, FLOORS):
    for part, sty in (('plates', 'plate'), ('wall', 'wall'), ('single', 'single'), ('glass', 'glass')):
        for p in (M['plates'][key] if part == 'plates' else M['solids'][f'{key}:{part}']): ax.add_patch(ring_patch([p['o']] + p['h'], **STY[sty]))
    for s in M['stairs'][key]: ax.plot([s[0], s[2]], [s[1], s[3]], color='#5aa65a', lw=0.5)
    for o in openings:
        if o['floor'] == key and o['kind'] in fk.APPROACH_KINDS:
            u = (o['ny'], -o['nx']); h = o['width'] / 2
            ax.plot([o['x'] - u[0] * h, o['x'] + u[0] * h], [o['y'] - u[1] * h, o['y'] + u[1] * h],
                    color='#c0392b' if o['kind'] == 'door' else '#2e9e4f', lw=2.2, zorder=2)
    for r in left_out:                                        # clusters left out: dotted, so the picture shows what was not made into a box
        if r['floor'] == key and 'x' in r:
            ax.add_patch(MPoly(list(fk.rect_of(r).exterior.coords), closed=True, fill=False, ec='#444444', lw=0.8, ls=':', zorder=2))
    for f in sorted((f for f in furniture if f['floor'] == key), key=lambda f: kind_info[f['kind']]['onTop']):      # tops after their supports
        ax.add_patch(MPoly(list(fk.rect_of(f).exterior.coords), closed=True, fc=kind_info[f['kind']]['colour'], ec='#c0392b' if f['approach'] else 'black',
                           lw=1.6 if f['approach'] else 0.4, alpha=0.92, zorder=3 + kind_info[f['kind']]['onTop'],
                           hatch='////' if 'plain outline' in f['note'] else None))
    ax.set_title(f"{ {'ground': 'Ground floor', 'upper': 'Upper floor'}[key]} ({H['levels'][key]:+.2f} m): {sum(per[key].values())} furniture boxes, "
                 f"one per piece, colour = kind (red outline: in the approach of a door; dotted: a cluster of loose lines left out; "
                 f"red / green ticks: doors / passages)", fontsize=11)
    ax.autoscale(); ax.set_aspect('equal'); ax.axis('off')
legend = [Patch(fc=k['colour'], ec='black', label=f"{k['label']}: {' + '.join(str(per[f][k['key']]) for f in FLOORS)}, {k['height']} mm"
                                                  + (f", base {k['base']} mm" if k['base'] else '')) for k in kinds]
n_plain = sum(1 for f in furniture if 'plain outline' in f['note'])
if n_plain: legend.append(Patch(fc='white', ec='black', hatch='////', label=f'hatched: a plain outline, nothing says what it is ({n_plain})'))
cols = 4
fig.legend(handles=legend, loc='lower center', ncol=cols, fontsize=11, frameon=False, title=f"Kind: pieces on {' + '.join(FLOORS)}, default height")
fig.tight_layout(rect=(0, 0.02 * math.ceil(len(legend) / cols) + 0.03, 1, 1))
fig.savefig(Path('..') / 'house_furniture_boxes.png'); plt.close()
print(f"furniture_house.json {round(Path('furniture_house.json').stat().st_size / 1024)} KB, house_furniture_list.csv ({len(furniture)} rows) "
      f"and house_furniture_boxes.png in {Path('..').resolve().name}/ | {time.time() - t0:.1f} s")
