"""Presidential suite from 'layout presidential test.dwg' (19 Oct 2026; furniture boxes added 29 Oct 2026) -> pres2_model.json,
pres2_stages.json, top view, and the furniture proxies' family list presidential_furniture_list.csv and picture
presidential_furniture_boxes.png (the boxes themselves are in pres2_model.json).

How the drawing is read (worked out on 19 Oct; see README):
- WALLS are the wall layer 'A-1.Netcat - tuong' ("cut line - wall"): its solid fills (HATCH), its thin closed outlines
  and its double lines paired 40-400 mm apart. Its single lines (terrace edges) and wide closed outlines (the outdoor
  dining pergola, the toilet's room outline) are not walls. Two outdoor features drawn on it are built separately.
- The core / corridor side has no wall on any layer (only the designer's room outlines on Defpoints): those walls are
  added along the room outlines, 0.20 m thick. The entrance door's jambs are on 'A-4. Dim'.
- GLASS: the octagonal facade is the 0.18 m band between two 'A-4. Dim' polylines, cut by two solid stubs and a door to
  the terrace; the north and south facades are glazed behind the balustrade (not drawn, inferred from the room
  outlines and curtains); a fixed glass panel by the bath; the study/living movable glass panels (drawn open, stacked).
- DOORS are gaps in the walls; a lintel fills each door from 2.10 m to the ceiling (none over the wide open passages).
- The BALUSTRADE (block on KT-Lancan) is frameless glass, 1.10 m (height assumed).
- The SLAB follows the balustrade's outer edge around the terraces and the suite's walls on the east.
- FURNITURE: one box per piece, the proxy the 3D team swaps for their own model by family name (furniture/README.md is the
  contract, furniture/furniture_kit.py the vocabulary, the sizes and the merging rules; furniture.json says which layers hold
  furniture, the office's own words for the names the vocabulary cannot read, skip words, heights and bases). A piece is a
  block insert (the drawn items that share one top-level handle) on a furniture layer, the layer most of it is drawn on; its box
  is the minimum rotated rectangle of everything drawn in it. The kind comes from the family name (the text after the last
  '$0$' of an xref-bound name), else from the layer name's words, else 'other'. Three blocks on 'A-4. Dim' read as furniture drawn
  on the facade layer; the terrace lounge drawn as one block of 1,123 items is left out by name. Shapes drawn loose on
  'A-2.Noi That' that touch within 1 cm form clusters, and a cluster whose hull fills 70 % of its rectangle (3 or more shapes, or
  one closed) is a box of kind 'other' (nothing names it), unless it lies on a part built above (a pergola post). A computer,
  lamp or plant stands on the nearest table, counter or cabinet. A box in the approach of a door or an open passage (what a
  person needs to walk straight through it: 0.30 m either side along the wall, 0.90 m across it) says so, for the 3D team to move.
  The boxes change nothing above: walls, glass, doors and the slab are as without them.
Usage: python build_model.py <plan.dxf>      (plan.dxf = LibreDWG dwg2dxf of the DWG)
"""
import collections, json, math, os, sys
from pathlib import Path
from shapely.geometry import Polygon, LineString, Point, box
from shapely.ops import unary_union

HERE = Path(__file__).resolve().parent
for d in (HERE, HERE.parent.parent / 'cad_test' / 'src', HERE.parent.parent / 'furniture',
          Path(r'C:\Users\DWP2\Desktop\Project walkthrough\cad_test\src')):
    sys.path.insert(0, str(d))
from merge_cad import strips, solidify                     # the same face-line pairing as the DWG house
from read_dxf import read
from geom import polys, even_odd, mean_width, circularity, strip, clean
import furniture_kit as fk                                 # furniture/furniture_kit.py: kinds, vocabulary, merging, CSV (section 6)

DXF = sys.argv[1] if len(sys.argv) > 1 else str(HERE / 'plan.dxf')
FLOOR_TO_FLOOR = 3.0                        # given by the project (19 Oct): 3 m floor to floor
DOOR_HEAD = 2.10                            # no door heights in the drawing: 2.10 m everywhere
BALUSTRADE = 1.10                           # balustrade height (assumed; not in the drawing)
WALL = 'A-1.Netcat - tuong'

ALL, n_layers = read(DXF)

def pts(d): return d.get('pts') or [q for l in d.get('loops', []) for q in l] or ([d['ins']] if 'ins' in d else [])
# The suite: the wall layer's cluster (a stray fill 200 m north is ignored) plus 2 m.
W = [p for d in ALL if d['lay'] == WALL for p in pts(d) if p[1] < -3450]
R = (min(p[0] for p in W) - 2, min(p[1] for p in W) - 2, max(p[0] for p in W) + 2, max(p[1] for p in W) + 2)
E = [d for d in ALL if any(R[0] <= x <= R[2] and R[1] <= y <= R[3] for x, y in pts(d))]
REGION = box(*R)
by_h = collections.defaultdict(list)
for d in E: by_h[d['h']].append(d)
def ent(h, t=None):
    """The direct entity with this DXF handle."""
    c = [d for d in by_h[h] if d['depth'] == 0 and (t is None or d['t'] == t)]
    if len(c) != 1: raise SystemExit(f'handle {h}: expected one entity, found {len(c)}')
    return c[0]

# ---------------------------------------------------------------------------------------------- what is what
GLASS_FACE_IN, GLASS_FACE_OUT = '1BB40C', '1BB40D'           # 'A-4. Dim': octagon facade, room-side and outer face
TERRACE_DOOR_JAMBS = ('1B24B2', '1B24B3')                     # 'A-4. Dim': jambs of the study's door to the terrace
PARTITION_FACES = ('1B239D', '1B239E')                        # study / living movable glass partition (track, open)
PARTITION_PANELS = ['1B234A', '1B234D', '1B234F', '1B2351', '1B2353', '1B2355', '1B2357', '1B2359', '1B235B']
BATH_GLASS = ('1B22F1', '1B22F2')                             # fixed glass panel between the bedroom and the jacuzzi
ENTRANCE_JAMBS = ('1B245B', '1B245C')                         # 'A-4. Dim': the entrance double door's jambs
FEATURE_PANEL = '1B2377'                                      # 'DA-WALL-FULL': full-height panel behind the console
C_WALL = {'1B2288', '1B2289', '1B228A'}                       # outdoor C-shaped wall round a built-in sofa
CABANA = '1B2298'                                             # block 'ggrgr' on the wall layer: the terrace daybed frame
NOT_WALLS = {'1B2278', '1B2299', '1B229A', '1B226D', '1B3CDF'}  # pergola rectangle, terrace edge lines, toilet outline
JACUZZI_KERBS = {'1B23E8', '1B23E9', '1B23EA', '1B23EB', '1B23EC', '1B23ED'}   # unfilled edge of the jacuzzi zone: low kerbs
# Core / corridor side: walls missing from every layer, drawn here along the designer's room outlines (inner face),
# on the outer side (direction given), with the thicknesses of the walls in the office's earlier drawing of this floor.
CORE_SIDE = [
    # gym/yoga east notch; starts at the outer corner of the drawn NE wall so the corner is closed
    ([(203.775, -3485.706), (202.536, -3486.421)], 0.18, (0.5, -0.866)),
    # gym and kitchen east (line B), run on to the foyer's north wall
    ([(202.536, -3486.421), (206.936, -3494.042)], 0.25, (0.866, 0.5)),
    # party wall: one straight 60-degree line from the foyer corner past the service room (door D14), the massage room,
    # sauna, toilet and the jacuzzi corner, down to the south facade
    ([(206.98, -3496.20), (206.033, -3497.834), (204.963, -3499.686), (203.843, -3501.627), (201.019, -3506.518)], 0.25, (0.866, -0.5)),
]
# Doors and openings (centre-line ends, drawing metres). lintel: True = 2.10 m head; False = full-height opening.
DOORS = [
    ('D1', 'entrance double door', (206.973, -3494.356), (206.973, -3495.956), True),
    ('D2', 'double door, living / foyer', (201.75, -3494.36), (201.75, -3495.96), True),
    ('D3', 'door, foyer / massage', (202.044, -3496.24), (202.89, -3496.24), True),
    ('D4', 'door, living / bedroom hall', (196.41, -3500.478), (197.314, -3500.478), True),
    ('D5', 'door, living / gym', (198.086, -3490.833), (198.986, -3490.833), True),
    ('D6', 'door, foyer / kitchen passage', (205.64, -3494.07), (206.44, -3494.07), True),
    ('D7', 'pocket door, foyer / powder', (203.2, -3494.02), (204.0, -3494.02), True),
    ('D8', 'door, bar / kitchen', (201.402, -3489.796), (201.877, -3490.618), True),
    ('D9', 'door, steam', (202.125, -3499.14), (201.745, -3499.79), True),
    ('D10', 'door, shower', (201.535, -3500.17), (201.155, -3500.82), True),
    ('D11', 'door, sauna', (203.63, -3499.12), (203.25, -3499.77), True),
    ('D12', 'door, toilet', (202.47, -3501.04), (202.02, -3501.82), True),
    ('D13', 'door, foyer / service room', (204.84, -3496.24), (205.64, -3496.24), True),
    ('D14', 'service door (east)', (206.256, -3497.697), (206.758, -3496.832), True),
    ('D15', 'door, study / terrace', (187.486, -3487.426), (188.036, -3486.474), 'glass'),
    ('O1', 'open counter, bar / living', (199.817, -3490.873), (201.351, -3493.568), False),
    ('O2', 'open, massage / spa passage', (202.633, -3498.341), (203.68, -3498.95), False),
    ('O3', 'open, bedroom hall / bath', (197.87, -3500.518), (197.87, -3501.718), True),
    ('O4', 'open, spa passage / bath', (200.88, -3501.385), (201.93, -3501.99), False),
    ('O5', 'open, walk-in closet (north)', (195.91, -3501.76), (197.01, -3501.76), True),
    ('O6', 'open, walk-in closet (south)', (195.91, -3505.28), (197.01, -3505.28), True),
    ('D16', 'movable glass partition (open)', (187.773, -3488.121), (191.984, -3490.552), False),
]
ROOMS = [   # English name, area as written in the drawing, centre of the room (the drawing's labels sit beside them)
    ('Living & Dining', '153', (192.93, -3495.23)), ('Study & Meeting', '56', (193.16, -3487.11)),
    ('Gym & Yoga', '33', (199.89, -3486.71)), ('Kitchen', '14', (203.75, -3490.82)), ('Bar', '7.6', (201.20, -3491.39)),
    ('Powder', '1.8', (203.75, -3493.44)), ('Foyer', '10', (204.40, -3495.16)), ('Massage', '9', (203.65, -3497.72)),
    ('Steam', '3', (201.38, -3498.71)), ('Shower', '2.3', (200.50, -3500.26)), ('Sauna', '3', (203.77, -3500.33)),
    ('Toilet', '2.7', (202.73, -3502.16)), ('Master Bath', '16', (199.38, -3502.01)), ('Jacuzzi', '3.5', (199.67, -3505.67)),
    ('Walk-in Closet', '8.5', (196.46, -3503.52)), ('Master Bedroom', '47', (192.72, -3503.06)),
]
SPEC = json.loads((HERE / 'floor_spec.json').read_text(encoding='utf-8')) if (HERE / 'floor_spec.json').exists() else {}

# ---------------------------------------------------------------------------------------------- 1. walls
def in_cabana(d): return d['h'] == CABANA
wall_ents = [d for d in E if d['lay'] == WALL and d['h'] not in NOT_WALLS | C_WALL | JACUZZI_KERBS and not in_cabana(d)]
hatch, thin, wide, segs = [], [], [], []
for d in wall_ents:
    if 'loops' in d:
        g = even_odd(d['loops'])
        if not g.is_empty: hatch.append(g)
        continue
    p = d['pts']
    if (d.get('closed') or (len(p) > 3 and math.dist(p[0], p[-1]) < 1e-3)) and len(p) >= 4:
        g = Polygon(p).buffer(0)
        if g.area > 0:
            (thin if mean_width(g) <= 0.35 else wide).append(g)
            continue
    segs += [[a[0], a[1], b[0], b[1]] for a, b in zip(p, p[1:]) if math.dist(a, b) > 0.02]
rects, n_paired, n_segs = strips(segs, 0.04, 0.40)
paired = solidify(rects, 0.06)
jambs = [Polygon(ent(h)['pts']).buffer(0) for h in ENTRANCE_JAMBS]
added = []                                                   # the core-side walls nobody drew
for line, thick, (ox_, oy_) in CORE_SIDE:
    L = LineString(line)
    m = L.interpolate(0.5, normalized=True)
    bands = [L.buffer(s * thick, single_sided=True, cap_style='flat', join_style='mitre') for s in (1, -1)]
    # keep the band on the outer side (its centre lies in the given direction from the line)
    added.append(max(bands, key=lambda b: (b.centroid.x - m.x) * ox_ + (b.centroid.y - m.y) * oy_))
# Small corner pieces either side of the entrance, where the added walls meet the drawn ones.
CORNER_FILL = [box(206.973, -3494.16, 207.1527, -3493.90), box(206.973, -3496.40, 207.1527, -3496.15),   # beside the entrance
               box(197.69, -3501.798, 197.87, -3501.718), box(195.15, -3501.798, 195.23, -3501.718),     # closet north corners
               box(197.69, -3505.318, 197.87, -3505.238), box(195.15, -3505.318, 195.23, -3505.238)]     # closet south corners
walls_raw = unary_union(hatch + thin + paired + jambs + [a.buffer(0.001, join_style='mitre') for a in added] + CORNER_FILL)
walls_raw = walls_raw.buffer(0.002, join_style='mitre').buffer(-0.002, join_style='mitre')     # close hairline cracks
kerb_segs = [[a[0], a[1], b[0], b[1]] for d in E if d['h'] in JACUZZI_KERBS and d.get('pts')
             for a, b in zip(d['pts'], d['pts'][1:]) if math.dist(a, b) > 0.02]
KERB_CORNERS = [box(198.6226, -3503.7981, 198.7026, -3503.7181), box(200.6374, -3503.7981, 200.7174, -3503.7181)]
kerbs = unary_union(solidify(strips(kerb_segs, 0.04, 0.12)[0], 0.02) + KERB_CORNERS).difference(walls_raw)

# Door D14 sits in an added wall: cut its opening.
def opening(a, b, depth):
    """Rectangle on the line a-b, `depth` deep each side."""
    return LineString([a, b]).buffer(depth, cap_style='flat')
d14 = [x for x in DOORS if x[0] == 'D14'][0]
walls_raw = walls_raw.difference(opening(d14[2], d14[3], 0.3).buffer(0.001))

# ---------------------------------------------------------------------------------------------- 2. glass
def band_between(h_in, h_out):
    a, b = ent(h_in)['pts'], ent(h_out)['pts']
    return Polygon(a + b[::-1]).buffer(0)
octagon = band_between(GLASS_FACE_IN, GLASS_FACE_OUT)
j1, j2 = (ent(h)['pts'] for h in TERRACE_DOOR_JAMBS)
terrace_door = Polygon([j1[0], j1[-1], j2[-1], j2[0]]).buffer(0)
if not terrace_door.is_valid or terrace_door.area < 0.05: terrace_door = Polygon([j1[0], j1[-1], j2[0], j2[-1]]).convex_hull
octagon = octagon.difference(walls_raw.buffer(0.001)).difference(terrace_door.buffer(0.005))
north_glass = box(191.73, -3483.793, 202.46, -3483.756).union(LineString([(191.52, -3483.38), (191.73, -3483.775)]).buffer(0.02, cap_style='flat'))
south_glass = box(190.715, -3506.556, 201.019, -3506.518)
facade = unary_union([octagon, north_glass, south_glass]).difference(walls_raw.buffer(0.001))
bath_glass = Polygon([(197.69, -3506.483), (197.75, -3506.483), (197.75, -3505.318), (197.69, -3505.318)])
panels = []
for h in PARTITION_PANELS:
    for d in by_h[h]:
        if d['t'] == 'LWPOLYLINE' and d.get('pts'):
            g = Polygon(d['pts']).buffer(0)
            if g.area > 0.002: panels.append(g.buffer(0.008, join_style='mitre'))
glass_raw = unary_union([facade, bath_glass] + panels).difference(walls_raw.buffer(0.001))
transom = terrace_door                                       # glass above the terrace door, 2.10 m to the ceiling

# ---------------------------------------------------------------------------------------------- 3. lintels
solid_for_jambs = unary_union([walls_raw, glass_raw])
LINTEL_DEPTH = {'O3': (-0.18, 0.0)}   # bath west wall x 197.69-197.87 (the opening's jambs are corners of other walls)
EXTERIOR = {'D1', 'D14'}          # lead off the suite (corridor / back of house, not in this drawing)
lintels, door_tests = [], []
def jamb_section(ax, ay, ux, uy, nx, ny, t):
    """The wall's extent across the door line at distance t along it (just inside a jamb): the solid interval that
    contains, or is nearest to, the door line. -> (lo, hi) in metres across, or None."""
    p0 = (ax + ux * t - nx * 0.6, ay + uy * t - ny * 0.6); p1 = (ax + ux * t + nx * 0.6, ay + uy * t + ny * 0.6)
    cut = LineString([p0, p1]).intersection(solid_for_jambs)
    best = None
    for g in ([cut] if cut.geom_type == 'LineString' else getattr(cut, 'geoms', [])):
        if g.is_empty or g.geom_type != 'LineString': continue
        s = sorted(((x - ax) * nx + (y - ay) * ny) for x, y in g.coords)
        lo, hi = s[0], s[-1]
        gap = 0 if lo <= 0 <= hi else min(abs(lo), abs(hi))
        if gap <= 0.3 and (best is None or gap < best[0]): best = (gap, lo, hi)
    return best[1:] if best else None
for code, name, a, b, lintel in DOORS:
    a, b = Point(a), Point(b)
    ux, uy = (b.x - a.x), (b.y - a.y); Lg = math.hypot(ux, uy); ux, uy = ux / Lg, uy / Lg
    nx, ny = -uy, ux
    door_tests.append({'id': code, 'name': name, 'x': (a.x + b.x) / 2, 'y': (a.y + b.y) / 2, 'nx': nx, 'ny': ny, 'width': round(Lg, 2),
                       **({'exterior': True} if code in EXTERIOR else {})})
    if lintel is not True: continue
    # The lintel fills the gap between the two jambs, as deep as the wall there (2.10 m up to the ceiling).
    secs = [s for s in (jamb_section(a.x, a.y, ux, uy, nx, ny, -0.02), jamb_section(a.x, a.y, ux, uy, nx, ny, Lg + 0.02)) if s]
    if not secs:
        print(f'  lintel {code}: no jambs found, skipped'); continue
    lo, hi = min(s[0] for s in secs), max(s[1] for s in secs)
    if len(secs) == 2 and min(s[1] for s in secs) - max(s[0] for s in secs) > 0.04:      # both jambs: their common depth
        lo, hi = max(s[0] for s in secs), min(s[1] for s in secs)
    if code in LINTEL_DEPTH: lo, hi = LINTEL_DEPTH[code]
    P = lambda t, s: (a.x + ux * t + nx * s, a.y + uy * t + ny * s)
    rect = Polygon([P(-0.15, lo), P(Lg + 0.15, lo), P(Lg + 0.15, hi), P(-0.15, hi)])
    piece = rect.difference(walls_raw.buffer(0.001)).difference(glass_raw.buffer(0.001))
    mid = Point((a.x + b.x) / 2 + nx * (lo + hi) / 2, (a.y + b.y) / 2 + ny * (lo + hi) / 2)
    cand = [p for p in polys(piece) if p.area > 0.005]
    piece = min(cand, key=lambda p: p.distance(mid), default=None)
    if piece is None:
        print(f'  lintel {code}: nothing between the jambs, skipped'); continue
    lintels.append((code, piece))

# ---------------------------------------------------------------------------------------------- 4. features
feature_panel = Polygon(ent(FEATURE_PANEL)['pts']).buffer(0)
c_wall = unary_union([even_odd(d['loops']) for d in E if d['h'] in C_WALL and 'loops' in d])
features = SPEC.get('features', [])                         # from the floor reading (heights etc.), if present

# ---------------------------------------------------------------------------------------------- 5. balustrade and slab
TERRACE_RAIL = [(191.774, -3483.628), (191.197, -3482.628), (181.757, -3482.628), (180.999, -3482.728), (180.293, -3483.02),
                (179.687, -3483.486), (179.221, -3484.092), (174.256, -3492.692), (173.964, -3493.398), (173.864, -3494.156),
                (173.964, -3494.914), (174.256, -3495.62), (179.208, -3504.195), (179.681, -3504.811), (180.298, -3505.284),
                (181.015, -3505.582), (181.786, -3505.683), (186.918, -3505.683), (188.65, -3506.683), (190.715, -3506.683)]
rails = SPEC.get('balustrade') or [TERRACE_RAIL, [(191.774, -3483.628), (200.94, -3483.628)], [(190.715, -3506.683), (201.019, -3506.683)]]
balustrade = unary_union([strip(r, 0.04) for r in rails])
if SPEC.get('slab'):
    slab = Polygon(SPEC['slab']).buffer(0)
else:
    east = [(201.019, -3506.518), (203.803, -3501.696), (204.963, -3499.686), (206.033, -3497.834), (207.15, -3496.05),
            (207.15, -3494.26), (206.676, -3493.592), (203.269, -3487.69), (202.536, -3486.421), (203.619, -3485.796), (202.462, -3483.793)]
    outer = LineString(TERRACE_RAIL).offset_curve(-0.022, join_style='mitre')     # slab edge, 22 mm outside the glass
    ring = list(outer.coords) + [(201.019, -3506.705)] + east + [(202.462, -3483.606), (191.774, -3483.606)]
    slab = Polygon(ring).buffer(0)
slab = unary_union([slab, walls_raw.buffer(0.005), glass_raw.buffer(0.005)] + [p.buffer(0.005) for _, p in lintels]).buffer(0.05, join_style='mitre').buffer(-0.05, join_style='mitre')
slab = max(polys(slab), key=lambda p: p.area)
slab = Polygon(slab.exterior)

# ---------------------------------------------------------------------------------------------- 6. furniture
# One coloured box per piece, the proxy the 3D team swaps for their own model by family name. furniture/README.md is the contract
# and furniture/furniture_kit.py holds the vocabulary, the sizes and the merging rules; this reads the drawing. furniture.json says
# which layers hold furniture, the office's own words for names the vocabulary cannot read, skip words, heights and bases.
FURN = json.loads((HERE / 'furniture.json').read_text(encoding='utf-8'))
FLOOR_KEY = 'suite'                                          # the floor key of the page and of the family list
MIN_PIECE = FURN.get('minSize', 0.08)                        # a piece whose long side is shorter than this is left out (more in furniture_kit.py)
BUILT = ('wall', 'column', 'post', 'low', 'builtin')         # parts made above: a loose outline lying on one of them is that part's own drawing

def drawn_points(d):
    """The points of a drawn item (a polyline, an arc, a circle, a hatch's loops); a text draws nothing."""
    return d.get('pts') or [q for l in d.get('loops', []) for q in l]

def family(name):
    """An xref-bound block is named '<xref>$0$<block>' (nested: '<xref>$0$<xref>$0$<block>'): the family is the block's own name."""
    return name.split('$0$')[-1].strip()

def shape_of(d):
    """A loose drawn item as a shapely shape: a hatch or a closed outline is a polygon, anything else a line (None: a point)."""
    if 'loops' in d:
        g = even_odd(d['loops'])
        return None if g.is_empty else g
    p = d.get('pts') or []
    if (d.get('closed') or (len(p) > 3 and math.dist(p[0], p[-1]) < 1e-3)) and len(p) >= 4:
        g = Polygon(p).buffer(0)
        return None if g.is_empty else g
    return LineString(p) if len({tuple(q) for q in p}) > 1 else None

def furniture_of():
    """The furniture pieces of the suite -> (pieces in drawing coordinates, what was read and left out)."""
    inside = {d['h'] for d in E if d.get('blk')}
    blocks = collections.defaultdict(list)                   # all that is drawn in each block insert of the suite area (E keeps only what falls inside it)
    for d in ALL:
        if d.get('blk') and d['h'] in inside and drawn_points(d): blocks[d['h']].append(d)
    pieces, skipped, elsewhere = [], collections.defaultdict(collections.Counter), collections.Counter()
    n_read = 0
    for h, ds in sorted(blocks.items()):
        n = collections.Counter(d['lay'] for d in ds)
        lay = min(n, key=lambda l: (-n[l], l))                # layer 0 inside a block took the insert's layer: the piece is on the layer most of it is
        if lay not in FURN['layers']:
            elsewhere[lay] += 1
            continue
        n_read += 1
        name = ds[0]['blk']; fam = family(name)
        kind = fk.classify(fam, lay, FURN.get('words'), FURN.get('skip'))
        bx = fk.box_of([q for d in ds for q in drawn_points(d)])
        if kind is None: why = 'name on the skip list'
        elif bx is None: why = 'a point or a line (no area)'
        elif bx['w'] < MIN_PIECE: why = f'shorter than {MIN_PIECE:g} m'
        elif bx['w'] > fk.MAX_SIDE: why = f'longer than {fk.MAX_SIDE:g} m'
        else: why = None
        if why:
            skipped[why][fam] += 1
            continue
        pieces.append({'floor': FLOOR_KEY, 'kind': kind, 'family': fam, 'block': name, 'layer': lay, 'handle': h, **bx, 'on': None, 'n': 1, 'note': ''})
    loose = collections.defaultdict(list)                    # shapes drawn loose, not as a block
    for d in E:
        if not d.get('blk') and d['lay'] in FURN.get('looseLayers', []) and ('pts' in d or 'loops' in d): loose[d['lay']].append(d)
    n_loose, n_boxes, left_out = 0, 0, []
    for lay, ds in sorted(loose.items()):
        shapes = [g for g in map(shape_of, ds) if g is not None]
        n_loose += len(shapes)
        boxes, rest = fk.loose_boxes(shapes)
        left_out += [{'layer': lay, 'shapes': n, 'why': why} for n, why in rest]
        for b in boxes:
            if not MIN_PIECE <= b['w'] <= fk.MAX_SIDE:
                left_out.append({'layer': lay, 'shapes': b['n'], 'why': f"long side {b['w']:.2f} m is not between {MIN_PIECE:g} and {fk.MAX_SIDE:g} m"})
                continue
            n_boxes += 1
            pieces.append({'floor': FLOOR_KEY, 'kind': fk.classify('', lay), 'family': f'loose shapes on {lay}', 'block': '', 'layer': lay,
                           'handle': '', **b, 'on': None, 'note': 'drawn loose, not as a block'})
    report = {'blockInserts': len(blocks), 'onFurnitureLayers': n_read, 'elsewhere': dict(elsewhere.most_common()),
              'skipped': {why: {'count': sum(c.values()), 'families': dict(c.most_common())} for why, c in skipped.items()},
              'looseShapes': {'shapes': n_loose, 'boxes': n_boxes, 'leftOut': left_out}}
    return pieces, report

# ---------------------------------------------------------------------------------------------- 7. centre, clean, write
minx, miny, maxx, maxy = slab.bounds
cx, cy = round((minx + maxx) / 2, 3), round((miny + maxy) / 2, 3)
R3 = lambda v: round(v, 3)
parts = []
def add(kind, geoms, z0, z1, min_area=0.004, label=None, **extra):
    n = 0
    for r in clean(geoms if isinstance(geoms, list) else polys(geoms), min_area, cx, cy):
        parts.append({'kind': kind, 'z0': z0, 'z1': z1, **r, **({'label': label} if label else {}), **extra}); n += 1
    return n
wall_runs = polys(walls_raw)
columns = [p for p in wall_runs if circularity(p) > 0.85 and p.area < 1.2]
runs = [p for p in wall_runs if p not in columns]
counts = {
    'wall': add('wall', runs, 0.0, FLOOR_TO_FLOOR, 0.005),
    'column': add('column', columns, 0.0, FLOOR_TO_FLOOR, 0.01),
    'lintel': sum(add('lintel', [p], DOOR_HEAD, FLOOR_TO_FLOOR, 0.005, label=code) for code, p in lintels),
    'glass': add('glass', polys(glass_raw), 0.0, FLOOR_TO_FLOOR, 0.003) + add('glass', [transom], DOOR_HEAD, FLOOR_TO_FLOOR, 0.003, label='D15 transom'),
    'builtin': add('builtin', [feature_panel], 0.0, FLOOR_TO_FLOOR, 0.01, label='Full-height panel', follow=True),
    'low': add('low', polys(kerbs), 0.0, 0.10, 0.003, label='Jacuzzi kerb'),
    'balustrade': add('balustrade', polys(balustrade), 0.0, BALUSTRADE, 0.002),
}
if not features:     # until the floor reading says otherwise: the C-wall as a 2.40 m feature wall (assumed)
    counts['low'] += add('low', polys(c_wall), 0.0, 2.4, 0.01, label='Terrace C-wall')
for f in features:
    g = Polygon(f['polygon']).buffer(0)
    counts[f['kind']] = counts.get(f['kind'], 0) + add(f['kind'], [g], f.get('z0', 0.0), f['z1'], 0.002, label=f.get('label'))
counts['slab'] = add('slab', [slab], -0.25, 0.0, 1.0)
for p in parts:            # the model is checked in Max against these; keep them valid after rounding
    q = Polygon(p['o'], p['h'])
    assert q.is_valid, (p['kind'], p.get('label'))
doors_out = [{**t, 'x': R3(t['x'] - cx), 'y': R3(t['y'] - cy), 'nx': R3(t['nx']), 'ny': R3(t['ny'])} for t in door_tests]
# The furniture boxes: worked out in drawing coordinates, moved into the model frame, then merged, supported, ordered and numbered by
# furniture_kit. A loose outline that lies on a part built above is that part's own drawing and is dropped (counted). The doors (D)
# and the open passages (O) are the openings whose approach a box may stand in.
try:
    furn_pieces, furn_report = furniture_of()
    for p in furn_pieces: p['x'], p['y'] = p['x'] - cx, p['y'] - cy
    solid = unary_union([Polygon(p['o'], p['h']) for p in parts if p['kind'] in BUILT])
    built_over = [p for p in furn_pieces if not p['block'] and fk.rect_of(p).intersection(solid).area >= 0.5 * p['w'] * p['d']]
    furn_pieces = [p for p in furn_pieces if all(p is not q for q in built_over)]
    furn_report['looseShapes']['builtOver'] = len(built_over)
    furn_pieces, furn_report['fronts'] = fk.merge_fronts(furn_pieces)
    openings = [{'id': t['id'], 'kind': 'passage' if t['id'].startswith('O') else 'door', 'floor': FLOOR_KEY, 'x': t['x'], 'y': t['y'],
                 'nx': t['nx'], 'ny': t['ny'], 'width': t['width']} for t in doors_out]
    furniture, furn_kinds = fk.finish(furn_pieces, [FLOOR_KEY], FURN.get('heights'), FURN.get('bases'), openings)
except ValueError as e:
    raise SystemExit(f'furniture.json: {e}')
in_approach = [p for p in furniture if p['approach']]
approach_ids = sorted({o for p in in_approach for o in p['approach']})
fr = furn_report
print(f"{FLOOR_KEY}: {len(furniture)} furniture boxes {dict(collections.Counter(p['kind'] for p in furniture))} | {len(in_approach)} in the approach of "
      f"{len(approach_ids)} of the {len(openings)} doors / passages {approach_ids} | read {fr['blockInserts']} block inserts: {fr['onFurnitureLayers']} on the "
      f"furniture layers ({fr['fronts']['absorbed']} cabinet fronts absorbed, {fr['fronts']['runs']} runs of fronts, left out: "
      f"{ {why: v['count'] for why, v in fr['skipped'].items()} }), the rest on other layers {fr['elsewhere']} | {fr['looseShapes']['shapes']} loose shapes: "
      f"{fr['looseShapes']['boxes'] - fr['looseShapes']['builtOver']} boxes ({fr['looseShapes']['builtOver']} more lie on a built part and are dropped), "
      f"not boxed: {fr['looseShapes']['leftOut'] or 'none'}")
model = {
    'source': 'layout presidential test.dwg', 'units': 'm', 'offset': [cx, cy], 'level': 0.0,
    'floorToFloor': FLOOR_TO_FLOOR, 'doorHead': DOOR_HEAD, 'balustradeHeight': BALUSTRADE, 'slabThickness': 0.25,
    'parts': parts,
    'rooms': [{'name': n, 'label': f'{n} · {a} m²', 'area': a, 'x': R3(x - cx), 'y': R3(y - cy)} for n, a, (x, y) in ROOMS],
    'doors': doors_out,
    'probe': {'glassWestX': R3(185.778 - cx), 'glassWestY': R3(-3495.15 - cy)},     # the octagon's west glass, room side
    'furnitureKinds': furn_kinds, 'furniture': furniture,
}
(HERE / 'pres2_model.json').write_text(json.dumps(model, separators=(',', ':'), ensure_ascii=False), encoding='utf-8')
wall_area = sum(Polygon(p['o'], p['h']).area for p in parts if p['kind'] in ('wall', 'column'))
print('parts:', counts, '| wall area', round(wall_area, 2), 'm2 | slab', round(slab.area, 1), 'm2 | offset', (cx, cy))
print('wall sources: hatch', len(hatch), 'thin outlines', len(thin), 'paired pieces', len(paired), f'({n_paired} pairs from {n_segs} segments)',
      '| wide outlines left out', [round(g.area, 1) for g in wide])

# ---------------------------------------------------------------------------------------------- 8. replay data
def seg_list(ds, step=1):
    out = []
    for d in ds:
        p = d.get('pts')
        if not p: continue
        for a, b in zip(p[::step], p[step::step] + ([p[-1]] if (len(p) - 1) % step else [])):
            if math.dist(a, b) > 0.01 and REGION.contains(Point(a)) and REGION.contains(Point(b)):
                out.append([a[0], a[1], b[0], b[1]])
    return out
glass_h = {GLASS_FACE_IN, GLASS_FACE_OUT, *PARTITION_FACES, *BATH_GLASS, '1B22F0', *PARTITION_PANELS}
cat_of = {}
for d in E:
    lay = d['lay'].lower()
    if d['h'] in glass_h: c = 'glass'
    elif d['lay'] == WALL: c = 'wall'
    elif 'door-wind' in lay or (d['t'] == 'ARC' and d['lay'].startswith('A-1.Netthay') and d['depth'] == 0): c = 'door'
    elif 'lancan' in lay: c = 'railing'
    else: c = 'noise'
    cat_of[id(d)] = c
lines = collections.defaultdict(list)
for d in E:
    if 'text' in d or 'loops' in d: continue
    lines[cat_of[id(d)]] += seg_list([d])
noise_all = len(lines['noise'])
lines['noise'] = sorted(lines['noise'], key=lambda s: -math.dist(s[:2], s[2:]))[:6000]
flat = lambda segs, nd: [round(v - (cx if i % 2 == 0 else cy), nd) for s in segs for i, v in enumerate(s)]
hatch_edges = [[a[0], a[1], b[0], b[1]] for g in hatch for p in polys(g) for ring in [p.exterior] + list(p.interiors)
               for a, b in zip(ring.coords, list(ring.coords)[1:])]
wall_pieces, _, _ = strips(segs + hatch_edges, 0.04, 0.60)
glass_segs = [s for d in E if d['h'] in {GLASS_FACE_IN, GLASS_FACE_OUT, *PARTITION_FACES} for s in seg_list([d])]
glass_pieces, _, _ = strips(glass_segs, 0.03, 0.20)
quads = lambda rects: [round(v, 3) for r in rects for x, y in list(r.exterior.coords)[:4] for v in (x - cx, y - cy)]
ring_of = lambda kinds: [{'o': p['o'], 'h': p['h']} for p in parts if p['kind'] in kinds]
n_wall_lines = sum(1 for d in E if d['lay'] == WALL)
n_runs = counts['wall']
fmt = lambda n: f'{n:,}'
stages = {
    'source': {'file': 'layout presidential test.dwg', 'layers': n_layers, 'units': 'mm'},
    'panelIntro': ('Built automatically from <b>layout presidential test.dwg</b>. Walls come from the drawing\'s wall layer '
                   '(its solid fills and outlines); the glass facade, doors, balustrade and floor from the rest of the plan. '
                   f'Furniture: {len(furniture)} coloured boxes in {len(furn_kinds)} kinds, one per piece; they come in at the end of the replay. '
                   'Floor to floor 3.00 m, as given for the project. No AI used.'),
    'intro': ['One floor plan (FL-01), in millimetres; the corridor beyond the entrance is left out',
              f'{fmt(len(E))} drawing items in the suite area, on {len({d["lay"] for d in E})} layers',
              'Walls on their own layer, with solid fills; furniture on separate layers',
              'Floor to floor 3.00 m, as given for the project'],
    'layers': [['Walls', f'{WALL} (fills, outlines and paired lines)'],
               ['Glass facade', "A-4. Dim double line (octagon); north and south glazing inferred from the room outlines"],
               ['Doors', 'Door blocks and door swings (A-1.Netthay)'], ['Balustrade', 'KT-Lancan (frameless glass, 1.10 m assumed)'],
               ['Added', 'Walls on the corridor side (not drawn on any layer), 0.20 m'],
               ['Furniture', f"Blocks on {len(FURN['layers'])} layers, {FURN['layers'][0]} first (one coloured box per piece, its height set per kind)"],
               ['Left out', 'Dimensions, door symbols, the pergola outline and terrace edge lines']],
    'floor': {'sheet': [0.0, 0.0],
              'lines': {k: flat(lines[k], 2) for k in ('wall', 'glass', 'door', 'railing', 'noise') if lines[k]},
              'pieces': {'wall': quads(wall_pieces), 'glass': quads(glass_pieces)},
              'rings': {'wall': ring_of(('wall', 'column')), 'glass': ring_of(('glass',))}},
    'captions': {
        'read': f'{fmt(len(E))} drawing items in the suite area, on {len({d["lay"] for d in E})} layers, in millimetres.',
        'sort': (f'Walls are on their own layer: {fmt(n_wall_lines)} items, {len(hatch)} of them solid fills. The glass facade is a '
                 f'double line around the octagon; doors and the balustrade have their own layers. {fmt(noise_all)} lines of '
                 f'furniture, fixtures, plants and dimensions build no walls: the {len(furniture)} furniture pieces among them become one '
                 'coloured box each, the rest is set aside.'),
        'align': 'One floor in this drawing (FL-01). Floor to floor 3.00 m, as given for the project; the floor is at {level} m.',
        'pair': (f'The wall fills and outlines give the wall pieces ({fmt(len(wall_pieces))}), and the facade\'s double line gives '
                 f'the glass. On the corridor side no wall is drawn, so {len(CORE_SIDE)} runs are added along the room outlines.'),
        'merge': f'The pieces merge into {n_runs} wall runs and {counts["column"]} columns; the glass into {counts["glass"]} panes and bands.',
        'raise': 'Walls and glass rise to {height} m (floor to floor); the balustrade to 1.10 m; a lintel over each door from 2.10 m.',
        'finish': f'The floor slab and terraces go in, and last the furniture: {len(furniture)} coloured boxes, one per piece, {len(furn_kinds)} kinds. Done: {n_runs} wall runs, {counts["glass"]} glass pieces, {counts["lintel"]} door lintels; {len(ROOMS)} rooms named.',
    },
    'stats': {'items': len(E), 'wallItems': n_wall_lines, 'fills': len(hatch), 'runs': n_runs, 'columns': counts['column'],
              'glass': counts['glass'], 'lintels': counts['lintel'], 'doors': len(DOORS), 'rooms': len(ROOMS),
              'wallArea': round(wall_area, 2), 'slabArea': round(slab.area, 1),
              'furniture': len(furniture), 'furnitureKinds': len(furn_kinds), 'furnitureByKind': {k['key']: k['count'] for k in furn_kinds}},
}
(HERE / 'pres2_stages.json').write_text(json.dumps(stages, separators=(',', ':'), ensure_ascii=False), encoding='utf-8')
print('stages:', {k: len(v) // 4 for k, v in stages['floor']['lines'].items()}, 'lines | pieces', {k: len(v) // 8 for k, v in stages['floor']['pieces'].items()})

# ---------------------------------------------------------------------------------------------- 9. top view
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import PathPatch
from matplotlib.path import Path as MPath
def patch(ax, r, **kw):
    verts, codes = [], []
    for loop in [r['o']] + r['h']:
        verts += [(x + cx, y + cy) for x, y in loop] + [(loop[0][0] + cx, loop[0][1] + cy)]
        codes += [MPath.MOVETO] + [MPath.LINETO] * (len(loop) - 1) + [MPath.CLOSEPOLY]
    ax.add_patch(PathPatch(MPath(verts, codes), **kw))
STY = {'slab': dict(facecolor='#eef0ec', edgecolor='#999', lw=0.8), 'wall': dict(facecolor='#8c7b6a', edgecolor='none'),
       'column': dict(facecolor='#6f6153', edgecolor='none'), 'lintel': dict(facecolor='#c49a6c', edgecolor='none'),
       'glass': dict(facecolor='#5fa8c8', edgecolor='none'), 'balustrade': dict(facecolor='#a8d0e0', edgecolor='none'),
       'builtin': dict(facecolor='#c9a77f', edgecolor='none'), 'low': dict(facecolor='#b8a68a', edgecolor='none'),
       'deck': dict(facecolor='#d9bf98', edgecolor='#b08a5c', lw=0.5), 'post': dict(facecolor='#4a4038', edgecolor='none')}
fig, ax = plt.subplots(figsize=(22, 18), dpi=90)
for kind in ('slab', 'deck', 'low', 'builtin', 'wall', 'column', 'post', 'glass', 'balustrade', 'lintel'):
    for p in parts:
        if p['kind'] == kind: patch(ax, p, **STY.get(kind, dict(facecolor='#999', edgecolor='none')))
for n, a, (x, y) in ROOMS: ax.text(x, y, n, fontsize=8, color='#1f4e79', ha='center')
ax.autoscale(); ax.set_aspect('equal'); plt.tight_layout(); plt.savefig(HERE / 'pres2_topview.png'); plt.close()
print('written pres2_model.json, pres2_stages.json, pres2_topview.png')

# ---------------------------------------------------------------------------------------------- 10. furniture list and picture
# The family list for the 3D team (the office-default heights), and the suite with one box per piece in its kind's colour. A red
# outline marks a box in the approach of a door or a passage; the number on a grey box is the id of a piece nobody could name
# (suite-other-<n>), so that the owner can name it.
from matplotlib.patches import Polygon as MPoly, Patch
fk.write_csv(HERE.parent / 'presidential_furniture_list.csv', fk.csv_text(furniture, furn_kinds, [FLOOR_KEY], model['offset']))
kind_by = {k['key']: k for k in furn_kinds}
FUR_STY = {'slab': dict(facecolor='#f4f4f1', edgecolor='#cfcfc9', lw=0.6), 'deck': dict(facecolor='#ebe4d6', edgecolor='none'),
           'wall': dict(facecolor='#8f8a84', edgecolor='none'), 'column': dict(facecolor='#6b665f', edgecolor='none'),
           'lintel': dict(facecolor='#bdb7ae', edgecolor='none'), 'glass': dict(facecolor='#b9dcea', edgecolor='#7fb3cc', lw=0.5),
           'balustrade': dict(facecolor='#d5e8f0', edgecolor='none'), 'builtin': dict(facecolor='#d8cdbd', edgecolor='none'),
           'low': dict(facecolor='#c9c1b4', edgecolor='none'), 'post': dict(facecolor='#6b665f', edgecolor='none')}
fig, ax = plt.subplots(figsize=(22, 19), dpi=90)
for kind, sty in FUR_STY.items():
    for p in parts:
        if p['kind'] == kind: patch(ax, p, **sty)
for n, a, (x, y) in ROOMS: ax.text(x, y, n, fontsize=8, color='#1f4e79', ha='center', alpha=0.55, zorder=2)
for t in door_tests:                                         # the doors (red) and the open passages (green), with their ids
    col = '#2e8b47' if t['id'].startswith('O') else '#c0392b'
    ux, uy, h = t['ny'], -t['nx'], t['width'] / 2
    ax.plot([t['x'] - ux * h, t['x'] + ux * h], [t['y'] - uy * h, t['y'] + uy * h], color=col, lw=1.6, ls='--' if t['id'].startswith('O') else '-', zorder=8)
    ax.text(t['x'] + t['nx'] * 0.3, t['y'] + t['ny'] * 0.3, t['id'], fontsize=7, color=col, ha='center', va='center', zorder=8)
for f in sorted(furniture, key=lambda f: (kind_by[f['kind']]['onTop'], f['kind'] != 'other')):      # the unnamed first, tops after their supports
    ax.add_patch(MPoly([(x + cx, y + cy) for x, y in fk.rect_of(f).exterior.coords], closed=True, fc=kind_by[f['kind']]['colour'],
                       ec='#d00000' if f['approach'] else 'black', lw=1.6 if f['approach'] else 0.4, alpha=0.92, zorder=3 + kind_by[f['kind']]['onTop']))
    if f['kind'] == 'other': ax.text(f['x'] + cx, f['y'] + cy, str(int(f['id'].rsplit('-', 1)[1])), fontsize=7, color='white', ha='center', va='center', zorder=9)
ax.set_title(f"Presidential suite ({model['level']:+.2f} m): {len(furniture)} furniture boxes, one per piece, colour = kind; red outline = in the approach "
             'of a door or a passage;\nthe number on a grey box is the id of a piece nobody could name (suite-other-<n>)', fontsize=12)
ax.autoscale(); ax.set_aspect('equal'); ax.axis('off')
legend = [Patch(fc=k['colour'], ec='black', label=f"{k['label']}: {k['count']}, {k['height']} mm" + (f", base {k['base']} mm" if k['base'] else '')) for k in furn_kinds]
legend.append(Patch(fc='white', ec='#d00000', lw=1.6, label=f"in the approach of a door or passage: {len(in_approach)}"))
cols = 4
fig.legend(handles=legend, loc='lower center', ncol=cols, fontsize=11, frameon=False, title='Kind: pieces, default height')
fig.tight_layout(rect=(0, 0.025 * math.ceil(len(legend) / cols) + 0.03, 1, 0.95))
fig.savefig(HERE.parent / 'presidential_furniture_boxes.png'); plt.close()
print(f"written presidential_furniture_list.csv ({len(furniture)} rows) and presidential_furniture_boxes.png in {HERE.parent.name}/")
