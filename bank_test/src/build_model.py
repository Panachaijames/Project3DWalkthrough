"""Bank branch test (26 Oct 2026; rules revised 27 Oct 2026 after the round-3 review; furniture boxes added 28 Oct 2026):
a CAD plan set + its layer mapping + the detected openings -> bank_model.json, bank_stages.json (build replay),
bank_summary.json, bank_topview.png, and the furniture proxies' family list bank_furniture_list.csv and picture
bank_furniture_boxes.png (the boxes themselves are in bank_model.json).

The first model built with NO drawing-specific rules: this script knows the drawing only through bank_project.json (the
layer roles staff confirm once per office, the floors with their decided levels and wall heights) and the openings
the detector found (detector_out/openings_<floor>.json, used exactly as they are). There are no coordinates, handles,
block names or layer names in here. The rules, all generic, with physical sizes in metres:
 1. WALLS from the wall and column layers (continuous line types only): solid fills, thin closed outlines (mean width
    <= 0.35 m; bigger ones are room outlines), face lines paired 4-45 cm apart (cad_test/src/merge_cad.py) and
    concentric arcs 4-45 cm apart (curved walls). A lone arc on a wall layer is a door swing and is left out. Cracks
    and corner squares are closed (3 cm). A run that is nearly all column-layer geometry is a column.
    A wall-layer line that pairs with nothing and lies in no wall is a single-line item ("wall, railing or edge?"),
    built 1.0 m high, as in the house test.
 2. REVIT WALL TYPES (Revit exports). Revit exports some wall elements as blocks named after the element:
    '<family> _ <type> - ...-<element id>-<view>' (its ':' becomes '_'). A block on a wall layer is such an element
    and its type name is read the way door heads are read from door names (a fixed vocabulary, no per-drawing data):
    a type that says GLASS, GLAZED, GLAZING or CURTAIN is a glass wall, and '<n>H' in it is its height in drawing
    units (2600H = 2.60 m in a millimetre drawing; no '<n>H': full height). Revit draws the glass layer's cut fill
    outside the block, so the glass is the thin fill (<= 3 cm) within 10 cm of the block's own lines, and any thin
    fill joined to it (a T or L joint). The wall's band is each pane widened to the type's faces (the block's lines
    parallel to it). The band is not wall: the pane is built as glass of the type's height with nothing above it, and
    a corner square left between two bands is a frame post of the same height.
    A thin fill (<= 3 cm) on a wall layer at the jamb of a door whose block name says GLASS is a frameless glass screen:
    glass, full height.
 3. GLASS from the glass layers: fills, thin outlines and lines paired 5 mm-30 cm apart; full wall height.
 4. OPENINGS (detector output, no edits):
    door    - the wall, glass and single-line pieces in its footprint are cut away; open from the floor to the door
              head; above it a lintel to the top of the wall, or a glass transom when both jambs are glass (up to the
              lower glass top: a 2.60 m glass wall's door gets a transom to 2.60 m and nothing above), none when nothing
              bounds it; no leaf. Head: the height in the name of the door block standing in the opening
              (...1000X2400 -> 2.40 m); a door whose block name has no height gets the most common height among all
              door names of the drawing; with no heights in any name, defaults.doorHead. The lintel is as deep as the
              walls beside its jambs (sections 5-30 cm beyond each jamb, as in the house model): it never hangs in
              front of or behind the wall line it closes.
    window  - its footprint is cut; a glass pane from the sill to the head (a collider). Glazing on a glass layer
              (curtain wall) runs the full height; other windows use defaults.windowSill / windowHead, with a sill wall
              below a sill above 0 and a lintel above a head below the top. The pane sits on the detector's glazing
              band when it gives one.
    passage - left as it is: no cut, no lintel (a passage is a gap that is already open).
 5. WALL GAPS CLOSED BY AN OBJECT: two wall ends facing each other along one wall line (at most 1.2 m apart, the same
    thickness), with no detected opening between them and an object block standing in the gap (a block on a layer
    that builds nothing, with nothing of the building in it, reaching out of both wall faces: a through-wall ATM, an
    air-conditioning unit) - the gap is closed with wall of the full height. Each closure is listed.
 6. PARAPETS: a wall piece with no cut fill (Revit fills every wall it cuts) whose ends both meet railings is part of
    the balustrade, below the cut plane: built at the railing height and kept at that height when walls change.
 7. RAILINGS: railing-layer lines paired (2-20 cm) or thickened (5 cm) into thin bands, defaults.railingHeight high;
    a railing that does not come out as a thin band is left out (reported). On an upper level a railing that stands
    mostly off the floor plate belongs to a stair below the floor (it would hang in the air) and is left out.
 8. STAIRS: stair lines (below the cut) and stair-above lines (above it) are grouped into stairs and their riser lines
    (3+ parallel lines 0.20-0.36 m apart) into flights. A stair word (UP, DN, DOWN) at the end of a flight gives its
    direction: the flight is built as solid steps rising (UP) or falling (DOWN) from that end, one riser each, the
    riser being the floor-to-floor height divided into steps of at most 0.18 m. Flights without a word are drawn as
    flat tread lines. On an upper level the floor is open over every stair (the outline of its lines: flights and
    landings), and stair lines away from the floor are not drawn (they are below it).
 9. ROOM NAMES from the room-name layers. A name with its area (or Revit's "Not Enclosed") on the line below is a room
    tag and shows its area; a free label needs 4+ letters and must not be a stair word (UP, DN, DOWN).
10. FLOOR PLATES: the inside of the walls, glass and openings (every detected opening spans its gap), plus the areas a
    railing bounds only where they are floor: an area outside the walls is kept when you can stand in it (0.8 m),
    a detected door or passage opens onto it and it is not mostly stair (a terrace is kept; the outside of a stair and
    the rounded corners a closing would add are not). A slab defaults.slabThickness thick under each level. On an
    upper level the floor is open over the stairs and over lift shafts (a room whose only opening is a lift door:
    a door block named LIFT or ELEVATOR).
11. LEVELS lined up on the first by the labels on the grid layer (median shift, applied in memory).
12. FURNITURE from the layers with the furniture role: one box per piece, the proxy the 3D team swaps for their own model
    by family name (furniture/README.md is the contract; furniture/furniture_kit.py holds the vocabulary, the sizes and the
    merging rules, this script only reads the drawing). A piece is a block insert on a furniture layer that is not inside
    another one (a chair's parts are not pieces), at any depth, so the fittings of a linked Revit model count too. Its
    footprint is the minimum rotated rectangle of the geometry drawn inside it: the items the cache lists right after the
    insert, so two same-named inserts side by side each get their own. The kind comes from the family name (a fixed
    vocabulary of words), else from the layer name's words (SANR, PLNT, CASE), else 'other'. Left out and counted, by
    reason: a name on the skip list (outlets, covers, mullions, rugs), no geometry drawn inside, a point or a line, a long
    side under furniture.minSize (0.08 m) or over 12 m. Cabinet fronts (door and drawer panels under 6 cm thick) are
    absorbed into the cabinet they stand on (within 15 cm), or, with no cabinet drawn, a run of them edge to edge becomes
    one 0.45 m deep box. Loose shapes (not in a block) on a furniture layer that touch within 1 cm form a cluster; a
    cluster whose hull fills 70 % of its minimum rectangle, and that has 3 or more shapes or a closed one, is a box of the
    kind the layer's words give; the other clusters are left out and counted.
    A computer, printer, telephone, lamp or plant stands on the nearest table, counter or cabinet whose box holds its centre or
    lies within 10 cm of it (a printer on a counter's overhang; inside several boxes: the smallest). A tall cabinet is no support.
    A box standing in the approach of a door or passage (what a person needs to walk straight through: the opening's width plus
    0.30 m each side along the wall, by 0.90 m each side across it; a box reaching 25 cm2 into the clear width counts wherever its
    centre is; windows have none) lists that opening in its 'approach' and says so in its note, for the 3D team to move.
    The boxes change nothing above: walls, openings, closures and the replay's picture are as without them.
Usage: python build_model.py [bank_project.json]
"""
import collections, json, math, re, statistics, sys, time
from pathlib import Path
from shapely.geometry import Polygon, LineString, Point, MultiPoint
from shapely.ops import unary_union

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent.parent                                       # the project folder: cad_test/ and presidential_test/ live there
for sub, mod in (('cad_test/src', 'merge_cad.py'), ('presidential_test/src', 'geom.py'), ('furniture', 'furniture_kit.py')):
    for d in (PROJECT / sub,):
        if (d / mod).exists():
            sys.path.insert(0, str(d)); break
    else:
        raise SystemExit(f'{sub}/{mod} not found (expected in the project folder)')
sys.path.insert(0, str(HERE))
from merge_cad import strips, solidify                  # face-line pairing, as in the house and the presidential suite
from geom import polys, even_odd, mean_width, clean      # presidential_test/src/geom.py
from plan_items import load_floor, closed_ring
import furniture_kit as fk                               # furniture/furniture_kit.py: kinds, vocabulary, merging, CSV (rule 12)

t_start = time.time()
CFG_PATH = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else HERE / 'bank_project.json'
CFG = json.loads(CFG_PATH.read_text(encoding='utf-8'))
DEF = CFG['defaults']
FURN = CFG.get('furniture', {})                                    # heights, bases, words, skip, minSize (rule 12)
rel = lambda p: Path(p) if Path(p).is_absolute() else CFG_PATH.parent / p

# Physical sizes (metres), the same for every drawing.
PAIR = (0.04, 0.45)        # wall face lines / concentric arcs paired this far apart
GLASS_PAIR = (0.005, 0.30)  # glass lines paired this far apart (a 10 mm pane is two lines 10 mm apart)
RAIL_PAIR = (0.02, 0.20)
SMALL, THIN = 0.15, 0.35   # closed shapes: under SMALL = not a wall; mean width over THIN = a room outline
CLOSE = 0.03               # cracks and corner squares closed in the wall solid
CUT_MARGIN = 0.15          # an opening's footprint reaches this far past the wall faces when it cuts (only within its
                           # width): frames and glazing drawn a little off the opening's line go too
PANE = 0.02                # a window pane built in an opening
SINGLE_W = 0.06            # a single-line item's width
THIN_FILL = 0.03           # a fill no thicker than this on a wall layer is glass when a glass wall type or a glass door owns it
PANE_REACH = 0.10          # a glass wall type's pane lies within this of the type's own lines
POST_MAX = 0.25            # a piece left between glass-wall bands no bigger than this (both ways) is a frame post
POST_MIN = 0.002           # ... and no smaller than this (20 cm2); smaller bits are slivers at a joint
GAP_MAX = 1.2              # wall ends this close, facing each other with an object between them: closed
PLATE_CLOSE = 1.5          # floor plate: areas a railing bounds come from a closing with a 1.5 m disc (gaps under 3 m)
STAND = 0.4                # ... and are floor only if a 0.8 m disc fits in them
SLAB_EDGE = 0.03           # the slab edge stands 3 cm out from the outline (no face in the plane of a wall face)
RISER_MAX = 0.18           # the steepest riser a stair is built with (the floor-to-floor height is split into these)
TREAD = (0.19, 0.37)       # riser lines of one flight are this far apart (the tread depth)
END_PROBES = (0.05, 0.10, 0.20, 0.30)   # sections beyond each jamb that give a lintel's depth (as in the house model)
REACH = 0.45               # material further than this from an opening's line is not its wall
MIN_PIECE = FURN.get('minSize', 0.08)   # furniture: a piece whose long side is shorter than this is left out (more in furniture_kit.py)
STAIR_UP, STAIR_DOWN = {'UP', 'UP.', 'UPSTAIRS'}, {'DN', 'DN.', 'DOWN', 'DOWNSTAIRS'}
STAIR_WORDS = STAIR_UP | STAIR_DOWN
TAG_LINE = re.compile(r'^\s*(\d+([.,]\d+)?\s*(m²|m2|sq\.?\s*m|sqm)|not enclosed|not placed|redundant room)\s*$', re.I)
SIZE_IN_NAME = re.compile(r'(\d{3,4})\s*[xX×]\s*(\d{3,4})')     # <width>x<height> in mm, e.g. 1000X2400, 650x2000
GLASS_WORD = re.compile(r'(?<![A-Z])(GLASS|GLAZED|GLAZING|CURTAIN)(?![A-Z])', re.I)   # in a type or door name
LIFT_WORD = re.compile(r'(?<![A-Z])(LIFT|ELEVATOR)(?![A-Z])', re.I)
TYPE_HEIGHT = re.compile(r'(?<![\d.])(\d{3,5})\s*H(?![A-Z])', re.I)               # '2600H' in a type name
BUILD_ROLES = {'wall', 'column', 'glass', 'window', 'door', 'stair', 'stair-above', 'railing', 'room-name', 'grid'}
UNITS_M = {'mm': 0.001, 'cm': 0.01, 'm': 1.0, 'in': 0.0254, 'inch': 0.0254, 'ft': 0.3048}
if CFG.get('units', 'mm') not in UNITS_M:
    raise SystemExit(f"unknown units {CFG.get('units')!r} in {CFG_PATH.name} (allowed: {', '.join(UNITS_M)})")
UNIT_M = UNITS_M[CFG.get('units', 'mm')]
R3 = lambda v: round(v, 3)


# ---------------------------------------------------------------------------------------------------- small helpers
def unit(v):
    n = math.hypot(v[0], v[1])
    return (v[0] / n, v[1] / n) if n > 1e-12 else (1.0, 0.0)


def rect(a, u, s0, s1, l0, l1):
    """Rectangle in the frame of an opening (origin a, along u, across n = left of u)."""
    n = (-u[1], u[0])
    P = lambda s, l: (a[0] + u[0] * s + n[0] * l, a[1] + u[1] * s + n[1] * l)
    return Polygon([P(s0, l0), P(s1, l0), P(s1, l1), P(s0, l1)])


def lines_of(g):
    if g is None or g.is_empty: return []
    if g.geom_type == 'LineString': return [g]
    return [x for y in getattr(g, 'geoms', []) for x in lines_of(y)]


class Frame:
    """An opening's line: a + s*u along (0..L), c*n across (n = left normal of a->b)."""
    def __init__(self, a, b):
        self.a, self.L = a, math.dist(a, b)
        self.u = unit((b[0] - a[0], b[1] - a[1]))
        self.n = (-self.u[1], self.u[0])

    def at(self, s, c=0.0):
        return (self.a[0] + self.u[0] * s + self.n[0] * c, self.a[1] + self.u[1] * s + self.n[1] * c)

    def local(self, x, y):
        dx, dy = x - self.a[0], y - self.a[1]
        return dx * self.u[0] + dy * self.u[1], dx * self.n[0] + dy * self.n[1]

    def across(self, geom, s, half=0.6):
        """Intervals (lo, hi) of geom on the line across the opening at s, relative to its line (touching pieces joined)."""
        out = []
        for g in lines_of(LineString([self.at(s, -half), self.at(s, half)]).intersection(geom)):
            cs = sorted(self.local(x, y)[1] for x, y in g.coords)
            if cs[-1] - cs[0] > 1e-4: out.append((cs[0], cs[-1]))
        out.sort()
        merged = []
        for lo, hi in out:
            if merged and lo <= merged[-1][1] + 1e-3: merged[-1] = (merged[-1][0], max(merged[-1][1], hi))
            else: merged.append((lo, hi))
        return merged


def simplify_pts(pts, tol=0.004):
    """Merge the 10 mm flattening chords of curves back into longer chords (straight runs become one segment)."""
    if len(pts) < 3: return [tuple(p) for p in pts]
    return [tuple(c) for c in LineString(pts).simplify(tol, preserve_topology=False).coords]


def segs_of(d, simplify=True):
    p = d.get('pts')
    if not p or len(p) < 2: return []
    p = simplify_pts(p) if simplify else [tuple(q) for q in p]
    out = [[a[0], a[1], b[0], b[1]] for a, b in zip(p, p[1:]) if math.dist(a, b) > 0.02]
    if d.get('closed') and len(p) > 2 and math.dist(p[0], p[-1]) > 0.02: out.append([p[-1][0], p[-1][1], p[0][0], p[0][1]])
    return out


def circle3(p0, p1, p2):
    ax, ay = p0; bx, by = p1; cx, cy = p2
    d = 2 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
    if abs(d) < 1e-12: return None
    ux = ((ax * ax + ay * ay) * (by - cy) + (bx * bx + by * by) * (cy - ay) + (cx * cx + cy * cy) * (ay - by)) / d
    uy = ((ax * ax + ay * ay) * (cx - bx) + (bx * bx + by * by) * (ax - cx) + (cx * cx + cy * cy) * (bx - ax)) / d
    return (ux, uy), math.dist((ux, uy), p0)


def arc_of(d):
    """An ARC item -> centre, radius and its angle range (radians, increasing)."""
    p = d['pts']
    if len(p) < 3: return None
    c = circle3(p[0], p[len(p) // 2], p[-1])
    if not c or c[1] > 50: return None
    (cx, cy), r = c
    ang = [math.atan2(y - cy, x - cx) for x, y in p]
    un = [ang[0]]
    for v in ang[1:]:
        un.append(un[-1] + (v - un[-1] + math.pi) % (2 * math.pi) - math.pi)
    return {'c': (cx, cy), 'r': r, 'lo': min(un), 'hi': max(un)}


def arc_walls(arcs, tmin, tmax):
    """Concentric arcs tmin..tmax apart -> the curved wall between them (over the angles both cover)."""
    out = []
    for i, A in enumerate(arcs):
        for B in arcs[i + 1:]:
            if math.dist(A['c'], B['c']) > 0.02 or not (tmin <= abs(A['r'] - B['r']) <= tmax): continue
            best = None
            for k in (-1, 0, 1):
                lo, hi = max(A['lo'], B['lo'] + 2 * math.pi * k), min(A['hi'], B['hi'] + 2 * math.pi * k)
                if hi - lo > math.radians(5) and (best is None or hi - lo > best[1] - best[0]): best = (lo, hi)
            if not best: continue
            lo, hi = best
            n = max(2, math.ceil((hi - lo) / math.radians(3)))
            cx, cy = (A['c'][0] + B['c'][0]) / 2, (A['c'][1] + B['c'][1]) / 2
            ro, ri = max(A['r'], B['r']), min(A['r'], B['r'])
            ts = [lo + (hi - lo) * j / n for j in range(n + 1)]
            ring = [(cx + ro * math.cos(t), cy + ro * math.sin(t)) for t in ts] + \
                   [(cx + ri * math.cos(t), cy + ri * math.sin(t)) for t in reversed(ts)]
            g = Polygon(ring).buffer(0)
            if not g.is_empty: out.append(g)
    return out


def family(name):
    """Revit block names read '<family> - <type>-<element id or V#>-<view>': keep '<family> - <type>' for reports."""
    m = re.match(r'^(.*?)-(\d{5,}|V\d+)-', name)
    return (m.group(1) if m else name).strip()


def type_name(fam):
    """'Basic Wall _ GLASS WALL 2600H 20X100 - ___' -> 'GLASS WALL 2600H 20X100' (Revit's '<family>: <type>')."""
    m = re.match(r'^.*?\s_\s(.*?)(\s+-\s+[^A-Za-z0-9]*)?$', fam)
    return (m.group(1) if m else fam).strip()


def head_in_name(name):
    """The height in a <width>x<height> size in a block name, in metres (1.8-3.5 m), or None."""
    hs = [int(h) * UNIT_M for _, h in SIZE_IN_NAME.findall(name)]
    hs = [h for h in hs if 1.8 <= h <= 3.5]
    return max(hs) if hs else None


def axis_of(g):
    """A thin shape's long axis: (start, end, width) of its minimum rotated rectangle."""
    cs = list(g.minimum_rotated_rectangle.exterior.coords)[:4]
    mid = lambda p, q: ((p[0] + q[0]) / 2, (p[1] + q[1]) / 2)
    if math.dist(cs[0], cs[1]) >= math.dist(cs[1], cs[2]):
        return mid(cs[0], cs[3]), mid(cs[1], cs[2]), math.dist(cs[1], cs[2])
    return mid(cs[0], cs[1]), mid(cs[3], cs[2]), math.dist(cs[0], cs[1])


def block_kids(by_h, ins):
    """The items drawn inside one block insert (any depth below it)."""
    pre = (ins['path'] + '>' if ins['path'] else '') + ins['name']
    return [d for d in by_h[ins['h']] if d is not ins and d['depth'] > ins['depth']
            and (d['path'] == pre or d['path'].startswith(pre + '>'))]


# ---------------------------------------------------------------------------------------------------- reading
def shift_items(items, dx, dy):
    for d in items:
        if 'pts' in d: d['pts'] = [[x + dx, y + dy] for x, y in d['pts']]
        if 'loops' in d: d['loops'] = [[[x + dx, y + dy] for x, y in l] for l in d['loops']]
        if 'ins' in d: d['ins'] = [d['ins'][0] + dx, d['ins'][1] + dy]


def grid_labels(items):
    out = {}
    for d in items:
        if 'grid' in d['roles'] and 'text' in d and d['text'].strip() and len(d['text'].strip()) <= 4:
            out.setdefault(d['text'].strip(), d['ins'])
    return out


def read_floor(fc, items, n_layers):
    use = lambda d, *roles: d['cont'] and 'ignore' not in d['roles'] and bool(d['roles'] & set(roles))

    # 1. walls and columns
    fills, thin, thin_fills, col_pieces, segs, col_segs, wall_segs, arcs = [], [], [], [], [], [], [], []
    n = collections.Counter()
    for d in items:
        if not use(d, 'wall', 'column'): continue
        is_col = 'column' in d['roles'] and 'wall' not in d['roles']
        n['col' if is_col else 'wall'] += 1
        if 'loops' in d:
            g = even_odd(d['loops'])
            if g.is_empty: continue
            fills.append(g); n['fills'] += 1
            if is_col: col_pieces.append(g)
            elif 'wall' in d['roles']:
                for p in polys(g):
                    if p.area >= 2e-4 and mean_width(p) <= THIN_FILL: thin_fills.append(p)
            continue
        ring = closed_ring(d)
        if ring:
            g = Polygon(ring).buffer(0)
            if g.is_empty: continue
            x0, y0, x1, y1 = g.bounds
            big = max(x1 - x0, y1 - y0)
            if big < SMALL: n['small'] += 1; continue
            if mean_width(g) <= THIN or (is_col and big <= 1.5):
                thin.append(g); n['thin'] += 1
                if is_col: col_pieces.append(g)
            else:
                n['wide'] += 1
            continue
        if d['t'] == 'ARC':
            a = arc_of(d)
            if a: arcs.append(a)
            continue
        ss = segs_of(d)
        segs += ss
        (col_segs if is_col else wall_segs).extend(ss)
    rects, n_pairs, n_segs = strips(segs, *PAIR)
    curved = arc_walls(arcs, *PAIR)
    col_pieces += strips(col_segs, *PAIR)[0] if col_segs else []
    W = solidify(fills + thin + rects + curved, CLOSE)
    COL = unary_union(col_pieces) if col_pieces else Polygon()
    n.update(pairs=n_pairs, segs=n_segs, arcs=len(arcs), curved=len(curved))

    # single-line items: wall lines that pair with nothing and lie in no wall
    cov = unary_union(W).buffer(0.02)
    singles = []
    for x1, y1, x2, y2 in wall_segs:
        for part in lines_of(LineString([(x1, y1), (x2, y2)]).difference(cov)):
            if part.length > 0.2: singles.append(part.buffer(SINGLE_W / 2, cap_style='flat'))
    S = solidify(singles, 0.01) if singles else []

    # 2. glass (and window glazing, which only an opening's pane replaces)
    gpieces, gsegs = [], []
    for d in items:
        if not use(d, 'glass', 'window') or (d['roles'] & {'wall', 'column'}): continue
        n['glass'] += 1
        if 'loops' in d:
            g = even_odd(d['loops'])
            if not g.is_empty: gpieces.append(g)
            continue
        ring = closed_ring(d)
        if ring:
            g = Polygon(ring).buffer(0)
            if not g.is_empty and mean_width(g) <= THIN: gpieces.append(g)
            continue
        gsegs += segs_of(d)
    grects, n_gpairs, _ = strips(gsegs, *GLASS_PAIR) if gsegs else ([], 0, 0)
    W_all = unary_union(W)
    Gu = unary_union(gpieces + grects)
    Gu = Gu.buffer(0.002, join_style='mitre').buffer(-0.002, join_style='mitre').difference(W_all)
    G = [p for p in polys(Gu) if p.area > 0.0005]

    # door blocks: the size in their names gives the door head; GLASS / LIFT in their names say what the door is
    door_blocks = [{'ins': d['ins'], 'name': d['name'], 'head': head_in_name(d['name'])}
                   for d in items if d['t'] == 'INSERT' and 'door' in d['roles'] and 'ignore' not in d['roles']]
    F = {'items': items, 'n_layers': n_layers, 'W': W, 'COL': COL, 'S': S, 'G': G, 'n': n, 'door_blocks': door_blocks,
         'rects': rects, 'fills': fills, 'thin_fills': thin_fills, 'grects': grects, 'segs': segs}
    revit_wall_types(F)
    return F


def revit_wall_types(F):
    """Rule 2: wall elements exported as blocks; glass wall types become glass panes of their type's height."""
    items = F['items']
    by_h = collections.defaultdict(list)
    for d in items: by_h[d['h']].append(d)
    F['by_h'] = by_h
    elements = []
    for d in items:
        if d['t'] != 'INSERT' or 'wall' not in d['roles'] or 'ignore' in d['roles']: continue
        fam = family(d['name'])
        hs = [int(v) * UNIT_M for v in TYPE_HEIGHT.findall(fam)]
        hs = [h for h in hs if 1.0 <= h <= 8.0]
        lines = [LineString(k['pts']) for k in block_kids(by_h, d) if k.get('pts') and len(k['pts']) >= 2]
        elements.append({'type': type_name(fam), 'glass': bool(GLASS_WORD.search(fam)), 'height': hs[0] if hs else None,
                         'lines': lines, 'panes': []})
    F['wall_types'] = elements
    thin = F['thin_fills']
    owner = {}
    for ei, e in enumerate(elements):
        if not e['glass'] or not e['lines']: continue
        ml = unary_union(e['lines'])
        for i, g in enumerate(thin):
            if i not in owner and g.distance(ml) <= PANE_REACH: owner[i] = ei
    grew = True
    while grew:                                  # thin fills joined to a pane (T and L joints) are the same glass
        grew = False
        for i, g in enumerate(thin):
            if i in owner: continue
            j = next((j for j in owner if thin[j].distance(g) <= 0.005), None)
            if j is not None: owner[i] = owner[j]; grew = True
    F['pane_owner'] = owner
    # each pane widened to its type's faces: the type's own lines parallel to it (the nearest on either side)
    measured = collections.defaultdict(list)
    axes = {}
    for i, ei in owner.items():
        g = thin[i]
        p, q, w0 = axis_of(g)
        L = math.dist(p, q)
        if L < 0.02: continue
        u = unit((q[0] - p[0], q[1] - p[1])); nn = (-u[1], u[0])
        axes[i] = (p, u, L, w0)
        for ln in elements[ei]['lines']:
            cs = list(ln.coords)
            for a, b in zip(cs, cs[1:]):
                if math.dist(a, b) < 0.05: continue
                v = unit((b[0] - a[0], b[1] - a[1]))
                if abs(v[0] * u[0] + v[1] * u[1]) < math.cos(math.radians(3)): continue
                ds = [(c[0] - p[0]) * nn[0] + (c[1] - p[1]) * nn[1] for c in (a, b)]
                ss = sorted((c[0] - p[0]) * u[0] + (c[1] - p[1]) * u[1] for c in (a, b))
                if ss[1] < -0.01 or ss[0] > L + 0.01: continue
                d0 = abs(sum(ds) / 2)
                if w0 / 2 + 0.01 <= d0 <= 0.3: measured[ei].append(d0)
    every = [v for vs in measured.values() for v in vs]
    hw_all = statistics.median(every) if every else 0.05
    bands, glass_walls = [], []
    for i, ei in owner.items():
        if i not in axes: continue
        p, u, L, w0 = axes[i]
        hw = min(measured[ei]) if measured[ei] else hw_all
        band = rect(p, u, 0, L, -hw, hw)
        e = elements[ei]
        e['panes'].append(i)
        bands.append(band)
        glass_walls.append({'pane': thin[i], 'band': band, 'height': e['height'], 'type': e['type']})
    F['glass_walls'] = glass_walls
    F['n']['glassWallTypes'] = sum(1 for e in elements if e['glass'])
    if not bands:
        F['posts'] = []
        return
    # the bands, with the 1 cm slots where one pane runs through another (a T joint) closed
    GWB = unary_union(bands).buffer(0.008, join_style='mitre').buffer(-0.007, join_style='mitre')
    rest = unary_union(F['W']).difference(GWB)
    posts, walls = [], []
    for p in polys(rest):
        x0, y0, x1, y1 = p.bounds
        if p.area <= 0.03 and x1 - x0 <= POST_MAX and y1 - y0 <= POST_MAX and p.distance(GWB) <= 0.005:
            if p.area < POST_MIN: continue                     # a sliver left at a joint of two bands
            hs = [g['height'] for g in glass_walls if g['band'].distance(p) <= 0.005]
            posts.append({'poly': p, 'height': max((h for h in hs if h), default=None)})
        elif p.area > 0.004:
            walls.append(p)
    F['W'], F['posts'] = walls, posts


# ---------------------------------------------------------------------------------------------------- the floors
# Each level is lined up on the first by the grid labels both carry (the median shift; applied to its drawing items and
# its detected openings, in memory: the detector's files stay as they are).
loaded = [(fc, *load_floor(str(rel(fc['cache'])), fc['area'], CFG['layers'], CFG.get('units', 'mm'))) for fc in CFG['floors']]
G0 = grid_labels(loaded[0][1])
floors = []
for i, (fc, items, layer_lt, n_layers) in enumerate(loaded):
    gl = grid_labels(items)
    common = sorted(set(gl) & set(G0))
    shift, grid = (0.0, 0.0), {'labels': len(common), 'spread': 0.0, 'shift': [0.0, 0.0]}
    if i and common:
        dx = statistics.median(G0[k][0] - gl[k][0] for k in common)
        dy = statistics.median(G0[k][1] - gl[k][1] for k in common)
        grid = {'labels': len(common), 'spread': max(math.hypot(G0[k][0] - gl[k][0] - dx, G0[k][1] - gl[k][1] - dy) for k in common),
                'shift': [R3(dx), R3(dy)]}
        if math.hypot(dx, dy) > 0.001: shift = (dx, dy)
        print(f"{fc['key']}: {len(common)} grid labels match {loaded[0][0]['key']}; shift ({dx:.4f}, {dy:.4f}) m, "
              f"spread {grid['spread'] * 1000:.1f} mm{' (applied)' if shift != (0.0, 0.0) else ''}")
    if shift != (0.0, 0.0): shift_items(items, *shift)
    F = read_floor(fc, items, n_layers)
    F['cfg'], F['shift'], F['grid'] = fc, shift, grid
    F['ops'] = json.loads(rel(fc['openings']).read_text(encoding='utf-8'))['openings']
    for o in F['ops']:
        o['a'] = [o['a'][0] + shift[0], o['a'][1] + shift[1]]; o['b'] = [o['b'][0] + shift[0], o['b'][1] + shift[1]]
    floors.append(F)
    print(f"{fc['key']}: {len(F['items'])} items | walls: {F['n']['fills']} fills, {F['n']['thin']} outlines, "
          f"{F['n']['pairs']} pairings of {F['n']['segs']} lines, {F['n']['curved']} curved | {len(F['W'])} wall pieces, "
          f"{len(F['S'])} single-line items, {len(F['G'])} glass pieces, {len(F['glass_walls'])} glass-wall panes of "
          f"{F['n']['glassWallTypes']} glass wall elements, {len(F['posts'])} frame posts | {len(F['ops'])} openings")

# The detector must have read the drawing with the same roles.
for mp in CFG.get('detectorMappings', []):
    try:
        dm = json.loads(Path(mp).read_text(encoding='utf-8'))['layers']
    except OSError:
        continue
    for role in ('wall', 'column', 'glass', 'door'):
        a, b = {x.upper() for x in dm.get(role, [])}, {x.upper() for x in CFG['layers'].get(role, [])}
        if a != b: print(f'  WARNING: the detector mapping {Path(mp).name} reads {role} from {sorted(a)}, this build from {sorted(b)}')

# The most common door height among all door names of the drawing: the head for doors whose name has none.
named = [b['head'] for F in floors for b in F['door_blocks'] if b['head']]
DOMINANT = statistics.mode(sorted(named)) if named else None
DEFAULT_HEAD = DOMINANT or DEF['doorHead']
print('door heads in the names:', dict(collections.Counter(named)), '-> doors without one get', DEFAULT_HEAD,
      '(most common in the names)' if DOMINANT else '(project default)')


# ---------------------------------------------------------------------------------------------------- openings
def wall_at_end(Fr, t, M, end):
    """The material beside one jamb: sections across the line END_PROBES beyond it; in each, the one interval that
    meets the opening's band (its thickness + 5 cm), no deeper than 0.6 m and within REACH. -> ((lo, hi), steady) or
    None. Steady: the sections from 0.10 m on agree and the nearest lies inside them (a wall that runs on past a nib)."""
    sgn, s0 = (-1, 0.0) if end == 'a' else (1, Fr.L)
    got = []
    for d in END_PROBES:
        ivs = [iv for iv in Fr.across(M, s0 + sgn * d) if iv[1] >= -t / 2 - 0.05 and iv[0] <= t / 2 + 0.05]
        ok = len(ivs) == 1 and ivs[0][1] - ivs[0][0] <= 0.6 and ivs[0][0] > -REACH and ivs[0][1] < REACH
        got.append(ivs[0] if ok else None)
    good = [g for g in got if g]
    if not good: return None
    far = [g for g in got[1:] if g]
    agree = len(far) >= 2 and all(abs(g[0] - far[0][0]) <= 0.01 and abs(g[1] - far[0][1]) <= 0.01 for g in far)
    if agree and got[0] is not None and got[0][0] >= far[0][0] - 0.01 and got[0][1] <= far[0][1] + 0.01:
        return far[0], True
    return good[0], False


def lintel_depth(Fr, t, M):
    """The depth of a door's lintel across its line, from the walls beside its jambs (the house model's rule): steady
    walls at both jambs -> the deeper one when the other lies inside it, else the faces they share; one steady -> that
    one; none steady -> the faces the nearest good sections share; nothing at either jamb -> the detector's thickness."""
    E = [wall_at_end(Fr, t, M, e) for e in ('a', 'b')]
    st = [e[0] for e in E if e and e[1]]
    near = [e[0] for e in E if e]
    inside = lambda p, q: p[0] >= q[0] - 0.01 and p[1] <= q[1] + 0.01
    if len(st) == 2:
        p, q = st
        if inside(p, q) or inside(q, p): lo, hi = max((p, q), key=lambda x: x[1] - x[0])
        else: lo, hi = max(p[0], q[0]), min(p[1], q[1])
    elif len(st) == 1:
        lo, hi = st[0]
    elif len(near) == 2:
        lo, hi = max(near[0][0], near[1][0]), min(near[0][1], near[1][1])
    elif near:
        lo, hi = near[0]
    else:
        lo, hi = -t / 2, t / 2
    if hi - lo < 0.005: lo, hi = min(x[0] for x in near), max(x[1] for x in near)   # no common faces: cover both
    return lo, hi


def build_openings(F):
    fc, top = F['cfg'], F['cfg']['wallHeight']
    W0, G0u, S0 = unary_union(F['W']), unary_union(F['G']), unary_union(F['S'])
    recs = []
    for o in F['ops']:
        a, b = tuple(o['a']), tuple(o['b'])
        Fr = Frame(a, b)
        w, u, nrm = Fr.L, Fr.u, Fr.n
        t = max(o['wallThickness'], 0.01)
        foot = rect(a, u, 0, w, -(t / 2 + CUT_MARGIN), t / 2 + CUT_MARGIN)
        rec = {'o': o, 'a': a, 'b': b, 'u': u, 'n': nrm, 'w': w, 't': t, 'foot': foot, 'Fr': Fr,
               'span': rect(a, u, 0, w, -t / 2 - 0.02, t / 2 + 0.02)}        # the gap between the jambs (floor plates)
        if o['kind'] == 'door':
            near = [blk for blk in F['door_blocks']
                    if -0.15 <= (blk['ins'][0] - a[0]) * u[0] + (blk['ins'][1] - a[1]) * u[1] <= w + 0.15
                    and abs((blk['ins'][0] - a[0]) * nrm[0] + (blk['ins'][1] - a[1]) * nrm[1]) <= t / 2 + 0.2]
            hs = [blk['head'] for blk in near if blk['head']]
            rec['blocks'] = [blk['name'] for blk in near]
            rec['glassDoor'] = any(GLASS_WORD.search(family(nm)) for nm in rec['blocks'])
            rec['liftDoor'] = any(LIFT_WORD.search(family(nm)) for nm in rec['blocks'])
            rec['head'] = max(hs) if hs else DEFAULT_HEAD
            rec['headFrom'] = 'name' if hs else ('most common' if DOMINANT else 'default')
        recs.append(rec)

    # Frameless glass screens: thin wall fills (not panes of a glass wall type) at the jambs of a glass door.
    screens = []
    for r in recs:
        if r['o']['kind'] != 'door' or not r.get('glassDoor'): continue
        ends = [rect(r['a'], r['u'], -0.06, 0.0, -r['t'] / 2 - 0.03, r['t'] / 2 + 0.03),
                rect(r['a'], r['u'], r['w'], r['w'] + 0.06, -r['t'] / 2 - 0.03, r['t'] / 2 + 0.03)]
        for i, g in enumerate(F['thin_fills']):
            if i in F['pane_owner'] or any(g is s for s in screens): continue
            if any(g.intersects(e) for e in ends): screens.append(g)
    if screens: W0 = W0.difference(unary_union(screens).buffer(0.001, join_style='mitre'))
    F['screens'] = screens
    # what stands at a jamb: wall, or glass with its top (a glass wall type's height, else the full height)
    glass_at = [(g['band'], g['height'] or top) for g in F['glass_walls']] + [(s, top) for s in screens] + \
               [(p['poly'], p['height'] or top) for p in F['posts']]

    def mat(p):
        P = Point(p)
        if W0.distance(P) <= 0.01: return 'wall', top
        hs = [h for g, h in glass_at if g.distance(P) <= 0.01]
        if hs: return 'glass', min(hs)
        if G0u.distance(P) <= 0.01: return 'glass', top
        return None, None
    for r in recs:
        o = r['o']
        if o['kind'] != 'window': continue
        gz = G0u.intersection(r['foot'])
        r['curtain'] = gz.area > 1e-4
        r['sill'], r['head'] = (0.0, top) if r['curtain'] else (DEF['windowSill'], DEF['windowHead'])
        if o.get('glazing'):                                    # the detector's glazing band across the line
            r['offset'] = (o['glazing'][0] + o['glazing'][1]) / 2
        elif r['curtain']:
            c = gz.centroid
            r['offset'] = (c.x - r['a'][0]) * r['n'][0] + (c.y - r['a'][1]) * r['n'][1]
        else:
            r['offset'] = 0.0
    cuts = [r['foot'] for r in recs if r['o']['kind'] in ('door', 'window')]
    CUT = unary_union(cuts) if cuts else Polygon()
    Wc, Gc, Sc = W0.difference(CUT), G0u.difference(CUT), S0.difference(CUT)
    GWc = [{**g, 'pane': g['pane'].difference(CUT)} for g in F['glass_walls']]
    SCc = [s.difference(CUT) for s in screens]
    POc = [{**p, 'poly': p['poly'].difference(CUT)} for p in F['posts']]
    SOL = unary_union([Wc, Gc] + [g['pane'] for g in GWc] + SCc + [p['poly'] for p in POc])
    solid = SOL.buffer(0.001)
    extra = []                                   # (kind, polygon, z0, z1, follow, label)
    for r in recs:
        o, a, u, w, t = r['o'], r['a'], r['u'], r['w'], r['t']
        if o['kind'] == 'door':
            # The lintel's depth: from the walls beside the jambs, except that a column or block at a jamb (deeper than
            # the opening's own wall and containing it) does not make it deeper than that wall.
            J = lintel_depth(r['Fr'], t, SOL)
            D = (-t / 2, t / 2)
            if J[0] <= D[0] + 0.01 and J[1] >= D[1] - 0.01 and (J[1] - J[0]) > (D[1] - D[0]) + 0.02: J = D
            r['depth'] = lo, hi = J
            # what stands at each jamb, 3 cm beyond it in the lintel's line: wall, or glass with its top
            c = (lo + hi) / 2
            r['jambs'] = (mat(r['Fr'].at(-0.03, c)), mat(r['Fr'].at(w + 0.03, c)))
            (ja, ha), (jb, hb) = r['jambs']
            r['lintel'], r['lintelTop'] = None, None
            if r['head'] < top - 0.005 and (ja or jb):
                if 'wall' in (ja, jb): kind, z1 = 'lintel', top
                else: kind, z1 = 'glass', min(h for h in (ha, hb) if h)
                if z1 > r['head'] + 0.005:
                    piece = rect(a, u, 0, w, lo, hi).difference(solid)
                    ps = [p for p in polys(piece) if p.area > (0.002 if kind == 'lintel' else 0.0005)]
                    if ps:
                        r['lintel'], r['lintelTop'] = ('transom' if kind == 'glass' else 'lintel'), z1
                        for p in ps:
                            extra.append((kind, p, r['head'], z1, z1 >= top - 0.005, o['id'] + (' transom' if kind == 'glass' else '')))
        elif o['kind'] == 'window':
            off = r['offset']
            pane = rect(a, u, 0, w, off - PANE / 2, off + PANE / 2).difference(Wc.buffer(0.001))
            for p in polys(pane):
                if p.area > 0.001: extra.append(('glass', p, r['sill'], r['head'], r['head'] >= top - 0.005, o['id'] + ' pane'))
            band = rect(a, u, 0, w, -t / 2, t / 2).difference(Wc.buffer(0.001))
            if r['sill'] > 0.005:
                for p in polys(band): extra.append(('sill', p, 0.0, r['sill'], False, o['id']))
            if r['head'] < top - 0.005:
                for p in polys(band): extra.append(('lintel', p, r['head'], top, True, o['id']))
    return recs, Wc, Gc, Sc, extra, GWc, SCc, POc


# ---------------------------------------------------------------------------------------------------- gaps, parapets
def object_closures(F, W0, recs):
    """Rule 5: wall ends facing each other along one wall line, no opening between them, an object block standing in
    the gap and reaching out of both wall faces -> the gap is closed."""
    caps = []
    for p in polys(W0):
        for ring in [p.exterior] + list(p.interiors):
            cs = list(ring.coords)
            for a, b in zip(cs, cs[1:]):
                L = math.dist(a, b)
                if not (0.05 <= L <= PAIR[1]): continue
                u = unit((b[0] - a[0], b[1] - a[1]))
                m = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
                n = (u[1], -u[0])                                  # pointing out of the wall
                if W0.contains(Point(m[0] + n[0] * 0.01, m[1] + n[1] * 0.01)): n = (-n[0], -n[1])
                if not W0.contains(Point(m[0] - n[0] * 0.05, m[1] - n[1] * 0.05)): continue   # wall behind it
                caps.append((a, b, m, n, L))
    if not caps: return []
    ops = unary_union([r['span'].buffer(0.03) for r in recs])
    objects = []
    for d in F['items']:
        if d['t'] != 'INSERT' or (d['roles'] & BUILD_ROLES): continue
        kids = block_kids(F['by_h'], d)
        if any(k['roles'] & BUILD_ROLES for k in kids): continue        # a linked model or a group of the building
        pts = [q for k in kids for q in (k.get('pts') or [])]
        if len(pts) >= 3: objects.append((family(d['name']), MultiPoint(pts).convex_hull))
    out = []
    for i, (a, b, m, n, L) in enumerate(caps):
        for a2, b2, m2, n2, L2 in caps[i + 1:]:
            if n[0] * n2[0] + n[1] * n2[1] > -0.99: continue        # not facing each other
            d = (m2[0] - m[0]) * n[0] + (m2[1] - m[1]) * n[1]
            lat = abs((m2[0] - m[0]) * -n[1] + (m2[1] - m[1]) * n[0])
            if not (0.05 < d <= GAP_MAX) or lat > 0.06 or abs(L - L2) > 0.06: continue
            gap = MultiPoint([a, b, a2, b2]).convex_hull
            if gap.area < 1e-4 or gap.intersection(W0).area > 0.2 * gap.area or gap.intersects(ops): continue
            side = (-n[1], n[0])
            for name, hull in objects:
                if hull.intersection(gap).area < 0.5 * gap.area: continue
                ls = [(x - m[0]) * side[0] + (y - m[1]) * side[1] for x, y in hull.exterior.coords]
                if min(ls) < -L / 2 - 0.05 and max(ls) > L / 2 + 0.05:      # it reaches out of both wall faces
                    out.append({'poly': gap, 'object': name, 'width': R3(d)})
                    break
    return out


def parapets_of(walls, fills, rails):
    """Rule 6: unfilled wall pieces whose ends both meet railings."""
    if not rails: return []
    R = unary_union(rails)
    out = []
    for p in walls:
        if fills.intersection(p).area > 0.25 * p.area or mean_width(p) > THIN: continue
        touch = polys(p.buffer(0.06).intersection(R))
        if len(touch) >= 2 and max(x.distance(y) for x in touch for y in touch) >= 0.5:
            out.append(p)
    return out


# ---------------------------------------------------------------------------------------------------- stairs, railings, rooms
def stair_lines(F, role):
    return [s for d in F['items'] if role in d['roles'] and 'ignore' not in d['roles'] and 'pts' in d for s in segs_of(d, False)]


def find_flights(lines):
    """Riser lines (>= 0.5 m) in groups of 3+ parallel lines TREAD apart, with about the same extent -> flights:
    {'u', 'n', 'o': [riser offsets, increasing], 's': (s0, s1) common extent, 'lines': [indices]}"""
    L = [(i, ls) for i, ls in enumerate(lines) if ls.length >= 0.5]
    byang = collections.defaultdict(list)
    for i, ls in L:
        (x0, y0), (x1, y1) = ls.coords[0], ls.coords[-1]
        ang = math.degrees(math.atan2(y1 - y0, x1 - x0)) % 180
        byang[int(round(ang / 2)) % 90].append((i, ls))
    out, used = [], set()
    for key in sorted(byang):
        grp = byang[key] + [x for x in byang.get((key + 1) % 90, []) if x[0] not in {y[0] for y in byang[key]}]
        grp = [x for x in grp if x[0] not in used]
        if len(grp) < 3: continue
        (x0, y0), (x1, y1) = grp[0][1].coords[0], grp[0][1].coords[-1]
        u = unit((x1 - x0, y1 - y0)); n = (-u[1], u[0])
        rows = []
        for i, ls in grp:
            c = ls.interpolate(0.5, normalized=True)
            ss = sorted(x * u[0] + y * u[1] for x, y in ls.coords)
            rows.append((c.x * n[0] + c.y * n[1], ss[0], ss[-1], i))
        # lanes: lines with about the same extent (two flights side by side have the same offsets, not the same extent)
        lanes = []
        for row in sorted(rows, key=lambda r: (r[1], r[0])):
            for lane in lanes:
                ov = min(row[2], lane['s1']) - max(row[1], lane['s0'])
                if ov >= 0.6 * min(row[2] - row[1], lane['s1'] - lane['s0']):
                    lane['rows'].append(row); break
            else:
                lanes.append({'s0': row[1], 's1': row[2], 'rows': [row]})
        for lane in lanes:
            risers = []                               # nosing lines drawn double (a few cm apart) are one riser
            for o, s0, s1, i in sorted(lane['rows']):
                if risers and o - risers[-1]['o'][-1] <= 0.04:
                    risers[-1]['o'].append(o); risers[-1]['i'].append(i)
                    risers[-1]['s0'], risers[-1]['s1'] = min(s0, risers[-1]['s0']), max(s1, risers[-1]['s1'])
                else:
                    risers.append({'o': [o], 's0': s0, 's1': s1, 'i': [i]})
            chain = []

            def close():
                if len(chain) >= 3:
                    s0 = max(r['s0'] for r in chain); s1 = min(r['s1'] for r in chain)
                    if s1 - s0 >= 0.4:
                        out.append({'u': u, 'n': n, 'o': [statistics.mean(r['o']) for r in chain], 's': (s0, s1),
                                    'lines': [i for r in chain for i in r['i']]})
                        used.update(i for r in chain for i in r['i'])
            for r in risers:
                ro = statistics.mean(r['o'])
                if chain:
                    step = ro - statistics.mean(chain[-1]['o'])
                    if TREAD[0] <= step <= TREAD[1]:
                        chain.append(r); continue
                    if len(chain) >= 2:            # one riser hidden where the break line crosses the flight
                        last = statistics.mean(chain[-1]['o']) - statistics.mean(chain[-2]['o'])
                        if abs(step - 2 * last) <= 0.15 * last:
                            chain.append({'o': [ro - last], 's0': r['s0'], 's1': r['s1'], 'i': []}); chain.append(r); continue
                close()
                chain = [r]
            close()
    return out


def stairs_of(F, H):
    """Rule 8: stairs (groups of stair lines), their flights, the stair words at the flights' ends, and the steps of the
    flights a word gives a direction. H = this level's floor-to-floor height."""
    below = [LineString([(s[0], s[1]), (s[2], s[3])]) for s in stair_lines(F, 'stair')]
    above = [LineString([(s[0], s[1]), (s[2], s[3])]) for s in stair_lines(F, 'stair-above')]
    lines = below + above
    if not lines: return {'stairs': [], 'below': [], 'above': [], 'steps': []}
    words = [d for d in F['items'] if 'text' in d and 'ignore' not in d['roles'] and d['text'].strip().upper() in STAIR_WORDS]
    riser = H / math.ceil(H / RISER_MAX - 1e-9)
    stairs, steps, stepped = [], [], set()
    blob = unary_union([ls.buffer(0.3) for ls in lines])
    for g in polys(blob):
        mem = [i for i, ls in enumerate(lines) if g.contains(ls.interpolate(0.5, normalized=True))]
        if len(mem) < 3: continue
        hull = MultiPoint([c for i in mem for c in lines[i].coords]).convex_hull
        fl = find_flights([lines[i] for i in mem])
        st = {'hull': hull, 'flights': [], 'lines': mem}
        for k, f in enumerate(fl):
            f['lines'] = [mem[i] for i in f['lines']]
            u, n, o, (s0, s1) = f['u'], f['n'], f['o'], f['s']
            # the stair word at one end of the flight (beyond its first or last riser, within its extent)
            end, word = None, None
            for d in words:
                x, y = d['ins']
                wo, ws = x * n[0] + y * n[1], x * u[0] + y * u[1]
                if not (s0 - 0.3 <= ws <= s1 + 0.3): continue
                for e, dd in (('first', o[0] - wo), ('last', wo - o[-1])):
                    if -0.3 <= dd <= 0.8 and (end is None or abs(dd) < end[1]): end, word = (e, abs(dd)), d['text'].strip().upper()
            f['dir'] = None if word is None else ('up' if word in STAIR_UP else 'down')
            f['from'] = end[0] if end else None
            f['risers'] = len(o)
            st['flights'].append(f)
            if f['dir'] is None: continue
            seq = o if f['from'] == 'first' else o[::-1]
            for j in range(1, len(seq)):
                lo_o, hi_o = sorted((seq[j - 1], seq[j]))
                P = lambda s, oo: (u[0] * s + n[0] * oo, u[1] * s + n[1] * oo)
                poly = Polygon([P(s0, lo_o), P(s1, lo_o), P(s1, hi_o), P(s0, hi_o)])
                # each step a block two risers deep, its top one riser above (UP) or below (DOWN) the one before
                if f['dir'] == 'up': z0, z1 = (j - 2) * riser, j * riser
                else: z0, z1 = -(j + 2) * riser, -j * riser
                steps.append((poly, R3(z0), R3(z1), f"stair {len(stairs) + 1} flight {k + 1} step {j} {f['dir']}"))
            stepped.update(f['lines'])
        stairs.append(st)
    keep_b = [i for i in range(len(below)) if i not in stepped]
    keep_a = [len(below) + i for i in range(len(above)) if len(below) + i not in stepped]
    return {'stairs': stairs, 'lines': lines, 'below': keep_b, 'above': keep_a, 'steps': steps, 'riser': riser,
            'words': len(words)}


def railings_of(F, Wc):
    rsegs = [s for d in F['items'] if 'railing' in d['roles'] and 'ignore' not in d['roles'] and 'pts' in d for s in segs_of(d)]
    if not rsegs: return [], 0
    paired = strips(rsegs, *RAIL_PAIR)[0]
    bands = [LineString([(x1, y1), (x2, y2)]).buffer(0.025, cap_style='flat') for x1, y1, x2, y2 in rsegs
             if math.hypot(x2 - x1, y2 - y1) > 0.05]
    R = unary_union(paired + bands).buffer(0.01, join_style='mitre').buffer(-0.01, join_style='mitre').difference(Wc.buffer(0.001))
    keep = [p for p in polys(R) if p.area > 0.002 and mean_width(p) <= 0.2]
    dropped = sum(1 for p in polys(R) if p.area > 0.002 and mean_width(p) > 0.2)
    return keep, dropped


def rooms_of(F):
    texts = [d for d in F['items'] if 'room-name' in d['roles'] and 'ignore' not in d['roles'] and d.get('text', '').strip()]
    tags = [d for d in texts if TAG_LINE.match(d['text'])]
    out, skipped = [], []
    for d in texts:
        if d in tags: continue
        name = ' '.join(d['text'].split())
        x, y = d['ins']
        tag = min((t for t in tags if abs(t['ins'][0] - x) < 0.3 and 0 < y - t['ins'][1] < 0.35),
                  key=lambda t: y - t['ins'][1], default=None)
        letters = sum(ch.isalpha() for ch in name)
        if tag is None and (letters < 4 or name.upper() in STAIR_WORDS):
            skipped.append(name); continue
        area = None
        if tag is not None and not re.search('[a-zA-Z]{3}', tag['text'].replace('m²', '').replace('m2', '')):
            area = ' '.join(tag['text'].split())
        out.append({'name': name, 'area': area, 'x': x, 'y': y})
    return out, skipped


def plates_of(E_walls, rails_edge, recs, stairs, lowest):
    """Rule 10: the floor plate(s) of a level -> (plates, report)."""
    E_nr = unary_union(E_walls + [r['span'] for r in recs])
    P1 = E_nr.buffer(0.05, join_style='mitre').buffer(-0.05, join_style='mitre')
    inner = unary_union([Polygon(p.exterior) for p in polys(P1) if p.area > 4]) if not P1.is_empty else Polygon()
    E = unary_union([E_nr] + rails_edge)
    C = E.buffer(PLATE_CLOSE, join_style='round').buffer(-PLATE_CLOSE, join_style='round')
    stair_area = unary_union([s['hull'] for s in stairs]) if stairs else Polygon()
    doors = unary_union([r['span'].buffer(0.05) for r in recs if r['o']['kind'] in ('door', 'passage')])
    kept, dropped = [], []
    for X in polys(C.difference(inner.buffer(0.01, join_style='mitre')).buffer(-0.01).buffer(0.01)):
        if X.area < 0.5: continue
        stand = not X.buffer(-STAND).is_empty
        reached = X.distance(doors) <= 0.05
        stair = X.intersection(stair_area).area >= 0.5 * X.area
        why = None if (stand and reached and not stair) else ('no standing room' if not stand else
                                                               'mostly stair' if stair else 'no door or passage opens onto it')
        (kept if why is None else dropped).append((X, why))
    plate = unary_union([inner] + [x for x, _ in kept]).buffer(0.02, join_style='mitre').buffer(-0.02, join_style='mitre')
    report = {'kept': [{'area': round(x.area, 1), 'bbox': [R3(v) for v in x.bounds]} for x, _ in kept],
              'dropped': [{'area': round(x.area, 2), 'bbox': [R3(v) for v in x.bounds], 'why': w} for x, w in dropped if x.area >= 0.5]}
    return plate, report


def lift_shafts(plate, E_cells, recs):
    """Rooms whose only opening is a lift door -> lift shafts."""
    lifts = [r for r in recs if r['o']['kind'] == 'door' and r.get('liftDoor')]
    if not lifts: return []
    others = [r['span'].buffer(0.03) for r in recs if not (r['o']['kind'] == 'door' and r.get('liftDoor'))]
    cells = polys(plate.difference(E_cells))
    out = []
    for r in lifts:
        for c in cells:
            if c.distance(r['span']) > 0.03 or c.area > 12: continue
            if any(c.distance(x) <= 0 for x in others): continue
            out.append(c)
    return out


# ---------------------------------------------------------------------------------------------------- furniture
def drawn_inside(items, i):
    """The items drawn inside the INSERT at items[i], and the index after it. The cache lists an insert and then everything
    inside it, deeper by one level or more (the insert's own attribute texts come first, at its own level), so this is right
    for each instance even where same-named inserts stand under one parent: block_kids, which goes by name and path, cannot
    tell those apart."""
    depth, j, n = items[i]['depth'], i + 1, len(items)
    while j < n and items[j]['t'] == 'ATTRIB' and items[j]['depth'] == depth: j += 1
    k = j
    while j < n and items[j]['depth'] > depth: j += 1
    return items[k:j], j


def drawn_points(d):
    """The points of a drawn item (a polyline, an arc, a circle, a hatch's loops); an insert or a text draws nothing itself."""
    if d['t'] in ('INSERT', 'ATTRIB') or 'text' in d: return []
    return d.get('pts') or [q for l in d.get('loops', []) for q in l]


def shape_of(d):
    """A loose drawn item as a shapely shape: a closed outline or a hatch is a polygon, anything else a line (None: a point)."""
    if 'loops' in d:
        g = even_odd(d['loops'])
        return None if g.is_empty else g
    ring = closed_ring(d)
    if ring:
        g = Polygon(ring).buffer(0)
        return None if g.is_empty else g
    p = d.get('pts') or []
    return LineString(p) if len({tuple(q) for q in p}) > 1 else None


def furniture_of(F):
    """Rule 12: the furniture pieces of one floor -> (pieces in drawing coordinates, what was read and left out)."""
    items, key = F['items'], F['cfg']['key']
    furn = lambda d: 'furniture' in d['roles'] and 'ignore' not in d['roles']
    pieces, skipped, loose = [], collections.defaultdict(collections.Counter), collections.defaultdict(list)
    n_inserts = n_nested = 0
    i = 0
    while i < len(items):
        d = items[i]
        if d['t'] == 'INSERT' and furn(d):
            kids, i = drawn_inside(items, i)                    # the parts of a piece are not pieces: on to what follows the insert
            n_inserts += 1
            fam = family(d['name'])
            kind = fk.classify(fam, d['lay'], FURN.get('words'), FURN.get('skip'))
            pts = [q for k in kids for q in drawn_points(k)]
            box = fk.box_of(pts) if pts else None
            if kind is None: why = 'name on the skip list'
            elif not pts: why = 'no geometry drawn inside the block'
            elif box is None: why = 'a point or a line (no area)'
            elif box['w'] < MIN_PIECE: why = f'shorter than {MIN_PIECE:g} m'
            elif box['w'] > fk.MAX_SIDE: why = f'longer than {fk.MAX_SIDE:g} m'
            else: why = None
            if why:
                skipped[why][fam] += 1
                continue
            n_nested += d['depth'] > 0
            pieces.append({'floor': key, 'kind': kind, 'family': fam, 'block': d['name'], 'layer': d['lay'],
                           'handle': d['h'] if d['depth'] == 0 else '', **box, 'on': None, 'n': 1,
                           'note': f"inside block {d['path'].split('>')[0]}" if d['depth'] else ''})
            continue
        i += 1
        if furn(d) and ('pts' in d or 'loops' in d): loose[d['lay']].append(d)
    n_loose, loose_boxes, left_out = 0, 0, []
    for lay, ds in sorted(loose.items()):
        shapes = [g for g in map(shape_of, ds) if g is not None]
        n_loose += len(shapes)
        boxes, rest = fk.loose_boxes(shapes)
        left_out += [{'layer': lay, 'shapes': n, 'why': why} for n, why in rest]
        for b in boxes:
            if not MIN_PIECE <= b['w'] <= fk.MAX_SIDE:
                left_out.append({'layer': lay, 'shapes': b['n'], 'why': f"long side {b['w']:.2f} m is not between {MIN_PIECE:g} and {fk.MAX_SIDE:g} m"})
                continue
            loose_boxes += 1
            pieces.append({'floor': key, 'kind': fk.classify('', lay), 'family': f'loose shapes on {lay}', 'block': '', 'layer': lay,
                           'handle': '', **b, 'on': None, 'note': 'drawn loose, not as a block'})
    report = {'insertsRead': n_inserts, 'nestedInAnotherBlock': n_nested,
              'skipped': {why: {'count': sum(c.values()), 'families': dict(c.most_common())} for why, c in skipped.items()},
              'looseShapes': {'shapes': n_loose, 'boxes': loose_boxes, 'leftOut': left_out}}
    return pieces, report


# ---------------------------------------------------------------------------------------------------- build every floor
parts_geo = []          # (floor key, kind, polygon, z0, z1, follow, label)
built = {}
for fi, F in enumerate(floors):
    fc = F['cfg']; key, top = fc['key'], fc['wallHeight']
    H = (floors[fi + 1]['cfg']['level'] - fc['level']) if fi + 1 < len(floors) else top
    recs, Wc, Gc, Sc, extra, GWc, SCc, POc = build_openings(F)
    closures = object_closures(F, unary_union(F['W']).difference(unary_union(F['screens']).buffer(0.001)) if F['screens'] else unary_union(F['W']), recs)
    Wc = unary_union([Wc] + [c['poly'] for c in closures]).difference(unary_union([c['poly'] for c in closures])) if closures else Wc
    rails, rails_dropped = railings_of(F, unary_union([Wc] + [c['poly'] for c in closures]))
    walls = [p for p in polys(Wc) if p.area > 0.004]
    fills = unary_union(F['fills'])
    parapets = parapets_of(walls, fills, rails)
    cols = [p for p in walls if not F['COL'].is_empty and p.intersection(F['COL']).area >= 0.9 * p.area]
    runs = [p for p in walls if not any(p is q for q in cols) and not any(p is q for q in parapets)]
    S = stairs_of(F, H)
    # the floor plate: the inside of the walls, glass and openings, plus railing-bounded areas that are floor
    lowest = fi == 0
    E_walls = [Wc, Gc] + [x[1] for x in extra] + [g['pane'] for g in GWc] + SCc + [p['poly'] for p in POc] + \
              [c['poly'] for c in closures]
    plate, plate_report = plates_of(E_walls, rails + parapets, recs, S['stairs'], lowest)
    voids = []
    if not lowest:
        E_cells = unary_union(E_walls + [r['span'] for r in recs])
        for s in S['stairs']:
            v = s['hull'].intersection(plate).difference(unary_union([Wc, Gc]))
            if v.area > 0.5: voids.append(('stair', v))
        for v in lift_shafts(plate, E_cells, recs): voids.append(('lift shaft', v))
        if voids: plate = plate.difference(unary_union([v for _, v in voids]).buffer(0.001))
    plates = [Polygon(p.exterior, [h for h in p.interiors if Polygon(h).area >= 0.5]).simplify(0.02).buffer(SLAB_EDGE, join_style='mitre')
              for p in polys(plate) if p.area > 4]
    if voids:                               # the slab edge stands proud of the outline, not into a void
        plates = [x for p in plates for x in polys(p.difference(unary_union([v for _, v in voids]).buffer(0.001)))]
    plate_u = unary_union(plates) if plates else Polygon()
    # on an upper level, railings standing mostly off the floor belong to a stair below the floor: left out
    rails_off = []
    if not lowest:
        rails_off = [r for r in rails if r.intersection(plate_u).area < 0.5 * r.area]
        rails = [r for r in rails if not any(r is q for q in rails_off)]
    for p in runs: parts_geo.append((key, 'wall', p, 0.0, top, True, None))
    for p in cols: parts_geo.append((key, 'column', p, 0.0, top, True, None))
    for p in parapets: parts_geo.append((key, 'parapet', p, 0.0, DEF['railingHeight'], False, 'parapet'))
    for c in closures: parts_geo.append((key, 'wall', c['poly'], 0.0, top, True, f"closure ({c['object']})"))
    for p in polys(Gc):
        if p.area > 0.0005: parts_geo.append((key, 'glass', p, 0.0, top, True, None))
    for g in GWc:
        for p in polys(g['pane']):
            if p.area > 0.0002: parts_geo.append((key, 'glass', p, 0.0, g['height'] or top, g['height'] is None, g['type']))
    for s in SCc:
        for p in polys(s):
            if p.area > 0.0002: parts_geo.append((key, 'glass', p, 0.0, top, True, 'glass screen'))
    for pst in POc:
        for p in polys(pst['poly']):
            if p.area > 0.0002: parts_geo.append((key, 'mullion', p, 0.0, pst['height'] or top, pst['height'] is None, 'frame post'))
    for kind, p, z0, z1, follow, label in extra: parts_geo.append((key, kind, p, z0, z1, follow, label))
    for p in polys(Sc):
        if p.area > 0.002: parts_geo.append((key, 'single', p, 0.0, DEF['singleLineHeight'], False, None))
    for p in rails: parts_geo.append((key, 'railing', p, 0.0, DEF['railingHeight'], False, None))
    for poly, z0, z1, label in S['steps']: parts_geo.append((key, 'step', poly, z0, z1, False, label))
    for p in plates: parts_geo.append((key, 'slab', p, -DEF['slabThickness'], 0.0, False, None))
    rooms, skipped = rooms_of(F)
    # stair lines to draw: on an upper level only those over the floor (the rest are below it)
    near_floor = (lambda ls: True) if lowest else (lambda ls: plate_u.buffer(0.02).contains(ls))
    below = [list(S['lines'][i].coords[0]) + list(S['lines'][i].coords[-1]) for i in S['below'] if near_floor(S['lines'][i])]
    above = [list(S['lines'][i].coords[0]) + list(S['lines'][i].coords[-1]) for i in S['above'] if near_floor(S['lines'][i])]
    built[key] = {'recs': recs, 'rooms': rooms, 'skipped': skipped, 'plates': plates, 'rails': rails,
                  'rails_dropped': rails_dropped, 'rails_off': len(rails_off), 'runs': runs, 'cols': cols,
                  'parapets': parapets, 'closures': closures, 'voids': voids, 'plate_report': plate_report,
                  'stairs': below, 'above': above, 'S': S, 'GWc': GWc, 'screens': SCc, 'posts': POc,
                  'stairs_all_below': len(stair_lines(F, 'stair')), 'stairs_all_above': len(stair_lines(F, 'stair-above'))}
    print(f"{key}: {len(runs)} wall runs, {len(cols)} columns, {len(parapets)} parapets, {len(closures)} closures "
          f"{[(c['object'][:30], c['width']) for c in closures]}, {len(polys(Gc))} glass pieces, {len(GWc)} glass-wall panes, "
          f"{len(SCc)} glass screens, {len(POc)} frame posts, {len(rails)} railing pieces"
          f"{f' ({rails_dropped} not simple, left out)' if rails_dropped else ''}{f', {len(rails_off)} stair rails off the floor left out' if rails_off else ''}, "
          f"{len(rooms)} room names (not names: {skipped}), plate {sum(p.area for p in plates):.1f} m2, voids "
          f"{[(k, round(v.area, 1)) for k, v in voids]}, steps {len(S['steps'])} (riser {S.get('riser', 0):.3f} m)")
    print('   plate: kept', plate_report['kept'], '| dropped', plate_report['dropped'])

# ---------------------------------------------------------------------------------------------------- centre, clean, write
allp = unary_union([p for _, k, p, _, _, _, _ in parts_geo if k == 'slab'])
minx, miny, maxx, maxy = allp.bounds
cx, cy = round((minx + maxx) / 2, 3), round((miny + maxy) / 2, 3)
parts, counts = [], collections.defaultdict(collections.Counter)
for key, kind, p, z0, z1, follow, label in parts_geo:
    min_area = {'slab': 1.0, 'glass': 0.0002, 'mullion': 0.0002, 'lintel': 0.002, 'sill': 0.002}.get(kind, 0.002)
    for r in clean([p], min_area, cx, cy):
        q = Polygon(r['o'], r['h'])
        assert q.is_valid, (key, kind, label)
        parts.append({'floor': key, 'kind': kind, 'z0': R3(z0), 'z1': R3(z1), 'follow': follow, **r,
                      **({'label': label} if label else {})})
        counts[key][kind] += 1

plates_by = {k: [Polygon(p['o'], p['h']) for p in parts if p['floor'] == k and p['kind'] == 'slab'] for k in built}
inside = lambda k, x, y: any(pl.contains(Point(x - cx, y - cy)) for pl in plates_by[k])
openings, probes = [], []
heads_by_family = collections.defaultdict(lambda: collections.Counter())
for F in floors:
    key = F['cfg']['key']
    for r in built[key]['recs']:
        o, a, u, nrm, w = r['o'], r['a'], r['u'], r['n'], r['w']
        mx, my = a[0] + u[0] * w / 2, a[1] + u[1] * w / 2
        sides = [inside(key, mx + nrm[0] * s * 0.6, my + nrm[1] * s * 0.6) for s in (1, -1)]
        rec = {'id': o['id'], 'floor': key, 'kind': o['kind'], 'subtype': o['subtype'], 'x': R3(mx - cx), 'y': R3(my - cy),
               'nx': R3(nrm[0]), 'ny': R3(nrm[1]), 'width': R3(w), 'wallThickness': R3(r['t']),
               'eitherKind': o.get('eitherKind', False), 'inside': [s for s, ok in zip((1, -1), sides) if ok]}
        if o['kind'] == 'door':
            rec.update(head=R3(r['head']), headFrom=r['headFrom'], lintel=r['lintel'],
                       lintelTop=R3(r['lintelTop']) if r['lintelTop'] else None, glassDoor=r['glassDoor'],
                       liftDoor=r['liftDoor'], jambs=[j[0] for j in r['jambs']])
            if r.get('depth'): rec['lintelDepth'] = [R3(r['depth'][0]), R3(r['depth'][1])]
            for fam in sorted({family(nm) for nm in r['blocks']} or {'(no door block in the opening)'}):
                heads_by_family[(fam, r['head'], r['headFrom'])][key] += 1        # openings, not blocks
        if o['kind'] == 'window':
            rec.update(sill=R3(r['sill']), head=R3(r['head']), curtain=r['curtain'], paneOffset=R3(r['offset']))
            off = r['offset']
            probes.append({'floor': key, 'id': o['id'], 'what': 'window pane', 'x': R3(mx + nrm[0] * off - cx),
                           'y': R3(my + nrm[1] * off - cy), 'nx': rec['nx'], 'ny': rec['ny'], 'inside': rec['inside']})
        openings.append(rec)
    # drawn glass that is not in an opening (curtain wall, glass partitions, screens): a probe at the middle of each
    # long, thin piece
    for p in parts:
        if p['floor'] != key or p['kind'] != 'glass' or p['z0'] > 0.01 or (p.get('label') or '').startswith(key): continue
        if p.get('label') and (p['label'].endswith(' pane') or p['label'].endswith(' transom')): continue
        g = Polygon(p['o'], p['h'])
        mrr = g.minimum_rotated_rectangle
        cs = list(mrr.exterior.coords)[:4]
        e1, e2 = math.dist(cs[0], cs[1]), math.dist(cs[1], cs[2])
        if max(e1, e2) < 0.6 or min(e1, e2) > 0.2: continue
        a0, a1 = (cs[0], cs[1]) if e1 >= e2 else (cs[1], cs[2])
        uu = unit((a1[0] - a0[0], a1[1] - a0[1])); nn = (-uu[1], uu[0])
        c = g.representative_point()
        side = [s for s in (1, -1) if inside(key, c.x + cx + nn[0] * s * 0.7, c.y + cy + nn[1] * s * 0.7)]
        what = 'glass partition' if p.get('label') and p['label'] != 'glass screen' else ('glass screen' if p.get('label') else 'curtain-wall glass')
        probes.append({'floor': key, 'id': f'{key} glass {len(probes) + 1}', 'what': what, 'x': R3(c.x), 'y': R3(c.y),
                       'nx': R3(nn[0]), 'ny': R3(nn[1]), 'inside': side, 'top': p['z1'], 'label': p.get('label')})
for rec in openings:
    if rec['kind'] in ('door', 'passage'):
        rec['exterior'] = len(rec['inside']) == 1

# Self-check: in every door and passage, nothing that stops you (below the head) may cross the opening's line.
BLOCKING = ('wall', 'column', 'glass', 'single', 'railing', 'sill', 'parapet', 'mullion')
blockers = collections.defaultdict(list)
for p in parts:
    if p['kind'] in BLOCKING and p['z0'] < 1.5:
        blockers[p['floor']].append(Polygon(p['o'], p['h']))
blocked = []
for rec in openings:
    if rec['kind'] not in ('door', 'passage'): continue
    ux, uy = rec['ny'], -rec['nx']                       # along the opening (n is its normal)
    h = rec['width'] / 2 * 0.8
    a0 = (rec['x'] - ux * h, rec['y'] - uy * h)
    zone = (rect(a0, (ux, uy), 0, 2 * h, -(rec['wallThickness'] / 2 + CUT_MARGIN), rec['wallThickness'] / 2 + CUT_MARGIN)
            if rec['kind'] == 'door' else LineString([a0, (rec['x'] + ux * h, rec['y'] + uy * h)]))
    hits = [g for g in blockers[rec['floor']] if g.intersects(zone) and (zone.geom_type == 'LineString' or g.intersection(zone).area > 1e-5)]
    if hits: blocked.append((rec['id'], rec['kind'], len(hits)))
print('self-check: doors and passages with something solid across them:', blocked or 'none')

# Walk-collision skins (viewer only; not parts, so not in the 3ds Max script): Walk casts its shoulder rays 7.5 cm
# apart, so the free end of anything thinner (a 10 mm screen, a 2 cm pane, a 5 cm rail) can slip between two rays.
# The thin regions of every collider (what an 8 cm opening removes: a whole pane, or a screen joined to a wall run)
# get an invisible collider 3.5 cm thicker on each side, up to 2 m.
SKIN = 0.08
skins = collections.defaultdict(list)
for p in parts:
    if p['kind'] not in BLOCKING or p['z0'] >= 1.5: continue
    g = Polygon(p['o'], p['h'])
    thin = g.difference(g.buffer(-SKIN / 2, join_style='mitre').buffer(SKIN / 2, join_style='mitre'))
    thin = [q for q in polys(thin) if q.area > 0.0002 and q.length > 0.12]
    if not thin: continue
    for r in clean([unary_union(thin).buffer(0.035, join_style='mitre')], 0.0005, 0, 0):
        skins[p['floor']].append({**r, 'z0': p['z0'], 'z1': R3(min(p['z1'], 2.0)), 'glass': p['kind'] == 'glass'})
print('walk-collision skins (thinner than 8 cm):', {k: len(v) for k, v in skins.items()})

rooms_out = []
for k, B in built.items():
    for r in B['rooms']:
        rooms_out.append({'floor': k, 'name': r['name'], 'label': r['name'] + (f" · {r['area']}" if r['area'] else ''),
                          'area': float(re.match(r'[\d.]+', r['area']).group()) if r['area'] and re.match(r'[\d.]+', r['area']) else None,
                          'x': R3(r['x'] - cx), 'y': R3(r['y'] - cy)})
flat = lambda segs, nd=3: [round(v - (cx if i % 2 == 0 else cy), nd) for s in segs for i, v in enumerate(s)]

# Rule 12: the furniture boxes. Worked out in drawing coordinates, merged floor by floor, then moved into the model frame.
furn_pieces, furn_report = [], {}
try:
    for F in floors:
        ps, rep = furniture_of(F)
        ps, rep['fronts'] = fk.merge_fronts(ps)
        furn_pieces += ps; furn_report[F['cfg']['key']] = rep
    for p in furn_pieces: p['x'], p['y'] = p['x'] - cx, p['y'] - cy
    furniture, furn_kinds = fk.finish(furn_pieces, [f['key'] for f in CFG['floors']], FURN.get('heights'), FURN.get('bases'), openings)
except ValueError as e:
    raise SystemExit(f'{CFG_PATH.name}: {e}')
approach = {k: {'pieces': sum(1 for p in furniture if p['floor'] == k and p['approach']),
                'openingIds': sorted({o for p in furniture if p['floor'] == k for o in p['approach']})} for k in furn_report}   # boxes in a door's or passage's approach, per floor
for k, rep in furn_report.items():
    mine = collections.Counter(p['kind'] for p in furniture if p['floor'] == k)
    print(f"{k}: {sum(mine.values())} furniture boxes {dict(mine)} | {approach[k]['pieces']} in the approach of {len(approach[k]['openingIds'])} doors / passages "
          f"{approach[k]['openingIds']} | read {rep['insertsRead']} inserts ({rep['nestedInAnotherBlock']} inside another block), "
          f"{rep['fronts']['absorbed']} cabinet fronts absorbed ({rep['fronts']['grown']} grew its box), {rep['fronts']['runs']} runs of fronts, "
          f"{rep['looseShapes']['boxes']} loose-shape boxes, left out: "
          f"{ {why: v['count'] for why, v in rep['skipped'].items()} } | loose shapes not boxed: {rep['looseShapes']['leftOut'] or 'none'}")
model = {
    'project': CFG['project'], 'shortName': CFG.get('shortName', CFG['project']), 'projectNo': CFG.get('projectNo'),
    'source': [f['dwg'] for f in CFG['floors']],
    'units': 'm', 'offset': [cx, cy], 'photoName': CFG.get('photoName', 'Model'), 'maxPrefix': CFG.get('maxPrefix', 'M'),
    'floors': [{'key': f['key'], 'name': f['name'], 'level': f['level'], 'wallHeight': f['wallHeight'],
                'slabThickness': DEF['slabThickness']} for f in CFG['floors']],
    'railingHeight': DEF['railingHeight'], 'singleLineHeight': DEF['singleLineHeight'], 'doorHeadDefault': DEFAULT_HEAD,
    'parts': parts,
    'stairs': {k: {'below': flat(B['stairs']), 'above': flat(B['above'])} for k, B in built.items()},
    'voids': {k: [{'what': w, 'x': R3(v.representative_point().x - cx), 'y': R3(v.representative_point().y - cy),
                   'area': round(v.area, 2)} for w, v in B['voids']] for k, B in built.items()},
    'closures': {k: [{'object': c['object'], 'width': c['width'], 'x': R3(c['poly'].centroid.x - cx),
                      'y': R3(c['poly'].centroid.y - cy)} for c in B['closures']] for k, B in built.items()},
    'stairOutlines': {k: [{'x': R3(s['hull'].representative_point().x - cx), 'y': R3(s['hull'].representative_point().y - cy),
                           'bbox': [R3(v - (cx if i % 2 == 0 else cy)) for i, v in enumerate(s['hull'].bounds)],
                           'flights': len(s['flights']), 'withWord': sum(1 for f in s['flights'] if f['dir'])}
                          for s in B['S']['stairs']] for k, B in built.items()},
    'rooms': rooms_out, 'openings': openings, 'probes': probes, 'colliderSkins': skins,
    'furnitureKinds': furn_kinds, 'furniture': furniture,
}
out_model = HERE / 'bank_model.json'
out_model.write_text(json.dumps(model, separators=(',', ':'), ensure_ascii=False), encoding='utf-8')

# The numbers the README and the replay quote.
summary = {'floors': {}, 'doorHeads': [], 'offset': [cx, cy]}
for F in floors:
    k = F['cfg']['key']; B = built[k]
    ops = [o for o in openings if o['floor'] == k]
    gw_types = collections.Counter(g['type'] for g in B['GWc'])
    summary['floors'][k] = {
        'items': len(F['items']), 'layers': F['n_layers'], 'counts': dict(counts[k]),
        'wallSources': {'fills': F['n']['fills'], 'outlines': F['n']['thin'], 'pairings': F['n']['pairs'], 'lines': F['n']['segs'],
                        'curved': F['n']['curved'], 'roomOutlinesLeftOut': F['n']['wide']},
        'openings': dict(collections.Counter(o['kind'] for o in ops)),
        'doorsWith': dict(collections.Counter(o['lintel'] or 'no lintel' for o in ops if o['kind'] == 'door')),
        'transoms': {o['id']: o['lintelTop'] for o in ops if o.get('lintel') == 'transom'},
        'exterior': [o['id'] for o in ops if o.get('exterior')],
        'rooms': [r['name'] for r in B['rooms']], 'notRoomNames': B['skipped'],
        'railingsLeftOut': B['rails_dropped'], 'stairRailsOffTheFloor': B['rails_off'], 'grid': F['grid'],
        'glassWalls': {'elements': F['n']['glassWallTypes'], 'panes': len(B['GWc']), 'types': dict(gw_types),
                       'heights': sorted({g['height'] for g in B['GWc'] if g['height']}),
                       'length': round(sum(axis_of(g['pane'])[2] if False else math.dist(*axis_of(g['pane'])[:2]) for g in B['GWc']
                                           if not g['pane'].is_empty), 1),
                       'screens': len(B['screens']), 'posts': len(B['posts'])},
        'parapets': [{'length': round(p.length / 2, 1), 'bbox': [R3(v) for v in p.bounds]} for p in B['parapets']],
        'closures': [{'object': c['object'], 'width': c['width'], 'bbox': [R3(v) for v in c['poly'].bounds]} for c in B['closures']],
        'voids': [{'what': w, 'area': round(v.area, 1), 'bbox': [R3(x) for x in v.bounds]} for w, v in B['voids']],
        'plate': B['plate_report'],
        'stairs': {'stairs': len(B['S']['stairs']), 'flights': sum(len(s['flights']) for s in B['S']['stairs']),
                   'flightsWithWord': [{'dir': f['dir'], 'risers': f['risers']} for s in B['S']['stairs'] for f in s['flights'] if f['dir']],
                   'steps': len(B['S']['steps']), 'riser': R3(B['S'].get('riser', 0)), 'words': B['S'].get('words', 0)},
        'wallArea': round(sum(Polygon(p['o'], p['h']).area for p in parts if p['floor'] == k and p['kind'] in ('wall', 'column')), 2),
        'plateArea': round(sum(Polygon(p['o'], p['h']).area for p in parts if p['floor'] == k and p['kind'] == 'slab'), 1),
        'stairLines': len(B['stairs']), 'stairAboveLines': len(B['above']),
        'stairLinesInDrawing': B['stairs_all_below'], 'stairAboveLinesInDrawing': B['stairs_all_above'],
    }
for (fam, head, how), by in sorted(heads_by_family.items(), key=lambda x: (-x[0][1], x[0][0])):
    summary['doorHeads'].append({'family': fam, 'head': R3(head), 'from': how, **{k: v for k, v in by.items()}})
summary['dominantHead'] = DOMINANT
summary['blocked'] = blocked
summary['namedHeads'] = dict(collections.Counter(R3(h) for h in named))
kind_order = [k['key'] for k in furn_kinds]
summary['furniture'] = {'pieces': len(furniture), 'kinds': {k['key']: k['count'] for k in furn_kinds}, 'floors': {}}
for k, rep in furn_report.items():
    mine = collections.Counter(p['kind'] for p in furniture if p['floor'] == k)
    summary['furniture']['floors'][k] = {'pieces': sum(mine.values()), 'kinds': {c: mine[c] for c in kind_order if mine[c]},
                                         'approach': {'pieces': approach[k]['pieces'], 'openings': len(approach[k]['openingIds']), 'openingIds': approach[k]['openingIds']}, **rep}
(HERE / 'bank_summary.json').write_text(json.dumps(summary, indent=1, ensure_ascii=False), encoding='utf-8')
for k in built:
    print(k, dict(counts[k]), summary['floors'][k]['openings'], summary['floors'][k]['doorsWith'], 'exterior', summary['floors'][k]['exterior'])
print('door heads:', [(d['family'][:40], d['head'], d['from']) for d in summary['doorHeads']])
print(f'written {out_model.name} ({out_model.stat().st_size // 1024} KB), offset ({cx}, {cy}) | {time.time() - t_start:.1f} s')


# ---------------------------------------------------------------------------------------------------- build replay data
NOISE_LINES = 6000          # per floor: the longest lines the build sets aside, enough to read as a drawing
fmt = lambda v: f'{v:,}'


def cat_of(d):
    r = d['roles']
    if 'ignore' in r: return 'noise'
    if r & {'wall', 'column'}: return 'wall'
    if r & {'glass', 'window'}: return 'glass'
    if 'door' in r: return 'door'
    if r & {'stair', 'stair-above'}: return 'stair'
    if 'railing' in r: return 'railing'
    return 'noise'


stage_floors, sorted_counts = {}, {}
for F in floors:
    k = F['cfg']['key']
    lines, n_by = collections.defaultdict(list), collections.Counter()
    for d in F['items']:
        if d['t'] in ('INSERT', 'ATTRIB') or 'text' in d: continue
        c = cat_of(d)
        n_by[c] += 1
        if 'pts' in d: lines[c] += segs_of(d, False)
        elif 'loops' in d and c != 'noise':
            for lp in d['loops']: lines[c] += [[a[0], a[1], b[0], b[1]] for a, b in zip(lp, lp[1:]) if math.dist(a, b) > 0.01]
    n_noise = len(lines['noise'])
    lines['noise'] = sorted(lines['noise'], key=lambda q: -math.hypot(q[2] - q[0], q[3] - q[1]))[:NOISE_LINES]
    hatch_edges = [[a[0], a[1], b[0], b[1]] for g in F['fills'] for pp in polys(g) for ring in [pp.exterior] + list(pp.interiors)
                   for a, b in zip(ring.coords, list(ring.coords)[1:])]
    wall_pieces = strips(F['segs'] + hatch_edges, 0.04, 0.60)[0]
    glass_segs = [q for d in F['items'] if cat_of(d) == 'glass' and 'pts' in d for q in segs_of(d)]
    glass_pieces = strips(glass_segs, 0.005, 0.20)[0] if glass_segs else []
    quads = lambda rects: [round(v, 3) for r in rects for x, y in list(r.exterior.coords)[:4] for v in (x - cx, y - cy)]
    ring_of = lambda kinds: [{'o': p['o'], 'h': p['h']} for p in parts if p['floor'] == k and p['kind'] in kinds and p['z0'] < 0.01]
    stage_floors[k] = {'sheet': [0.0, 0.0],
                       'lines': {c: flat(lines[c], 2 if c == 'noise' else 3) for c in ('wall', 'glass', 'door', 'stair', 'railing', 'noise') if lines[c]},
                       'pieces': {'wall': quads(wall_pieces), **({'glass': quads(glass_pieces)} if glass_pieces else {})},
                       'rings': {'wall': ring_of(('wall', 'column', 'parapet')), 'glass': ring_of(('glass', 'mullion'))}}
    sorted_counts[k] = {'byCat': dict(n_by), 'noiseLines': n_noise, 'wallPieces': len(wall_pieces), 'glassPieces': len(glass_pieces)}

L = CFG['layers']
names = lambda *roles: ', '.join(x for r in roles for x in L.get(r, []))
F1, F2 = floors[0], floors[-1]
k1, k2 = F1['cfg']['key'], F2['cfg']['key']
both = lambda f: f(k1) + f(k2)
n_doors = both(lambda k: summary['floors'][k]['openings'].get('door', 0))
n_windows = both(lambda k: summary['floors'][k]['openings'].get('window', 0))
n_pass = both(lambda k: summary['floors'][k]['openings'].get('passage', 0))
n_lintels = both(lambda k: counts[k]['lintel'])
n_transoms = both(lambda k: len(summary['floors'][k]['transoms']))
n_gw = both(lambda k: summary['floors'][k]['glassWalls']['panes'])
gw_heights = sorted({h for k in (k1, k2) for h in summary['floors'][k]['glassWalls']['heights']})
n_parapets = both(lambda k: len(summary['floors'][k]['parapets']))
n_closures = both(lambda k: len(summary['floors'][k]['closures']))
n_steps = both(lambda k: summary['floors'][k]['stairs']['steps'])
runs = lambda k: counts[k]['wall']
heads = sorted({d['head'] for d in summary['doorHeads']}, reverse=True)
grid = F2['grid']
levels_txt = ' / '.join(f"{f['level']:+.2f}" for f in CFG['floors'])
units_txt = {'mm': 'millimetres', 'cm': 'centimetres', 'm': 'metres'}.get(CFG.get('units', 'mm'), CFG.get('units', 'mm'))
n_other_layers = len({d['lay'] for F in floors for d in F['items'] if cat_of(d) == 'noise' and 'text' not in d and d['t'] != 'INSERT'})
# The levels are separate drawings: the replay lays them side by side (in reading order) before it stacks them.
pminx, pminy, pmaxx, pmaxy = allp.bounds
for i, F in enumerate(floors):
    stage_floors[F['cfg']['key']]['sheet'] = [round(i * (pmaxx - pminx + 3.0), 2), 0.0]
gw_txt = (f"{n_gw} glass partition panes ({' / '.join(f'{h:.2f}' for h in gw_heights)} m, from the Revit wall type names)"
          if n_gw else '')
stages = {
    'source': {'files': [f['dwg'] for f in CFG['floors']], 'layersInUse': [F['n_layers'] for F in floors], 'units': CFG.get('units', 'mm')},
    'panelIntro': (f"Built automatically from the {len(floors)} Revit-exported DWGs of <b>{CFG['project']}</b>: walls from the wall "
                   f"layers, glass from the curtain-wall layers and from the glass wall types Revit names on its wall blocks, "
                   f"and the {n_doors} doors, {n_windows} windows and {n_pass} passages from the openings detector, used as found. "
                   f"Furniture: {len(furniture)} coloured boxes in {len(furn_kinds)} kinds, one per piece; they come in at the end of the replay. "
                   f"Levels {levels_txt} m. No drawing-specific rules; no AI used."),
    'intro': [f"{len(floors)} plans, one per DWG ({' / '.join(f['name'] for f in CFG['floors'])}), in {units_txt}"
              + (f", exported from {CFG['exportedFrom']}" if CFG.get('exportedFrom') else ''),
              f"{fmt(len(F1['items']))} + {fmt(len(F2['items']))} drawing items, on {F1['n_layers']} and {F2['n_layers']} layers in use",
              f"Both levels share one origin: {grid['labels']} grid labels match within {grid['spread'] * 1000:.1f} mm",
              f"{n_doors} doors, {n_windows} windows and {n_pass} passages found by the openings detector"],
    'layers': [['Walls', names('wall') + ' (cut fills, outlines, paired lines)'], ['Columns', names('column')],
               ['Glass', names('glass') + ' (curtain wall); glass wall types on the wall layers (by their Revit type name)'],
               ['Doors', names('door') + ' (head heights from the door names)'],
               ['Stairs', names('stair') + '; ' + names('stair-above') + ' above the cut (faint)'],
               ['Railings', names('railing') + f" ({DEF['railingHeight']:.2f} m)"], ['Room names', names('room-name')],
               ['Furniture', names('furniture') + ' (one coloured box per piece, its height set per kind)'],
               ['Left out', ', '.join(L.get('other', []) + L.get('ignore', [])) + ' (and the grid, used only to line the levels up)']],
    'floors': stage_floors,
    'captions': {
        'read': (f"{fmt(len(F1['items']))} drawing items on {F1['cfg']['name']} and {fmt(len(F2['items']))} on {F2['cfg']['name']}, "
                 f"read from {len(floors)} DWGs in {units_txt}."),
        'sort': (f"Walls are on {names('wall')}: {fmt(both(lambda k: sorted_counts[k]['byCat'].get('wall', 0)))} items, "
                 f"{both(lambda k: summary['floors'][k]['wallSources']['fills'])} of them cut fills. Glass on {names('glass')}, "
                 f"doors on {len(L.get('door', []))} door layers, stairs and railings on their own. "
                 f"{fmt(both(lambda k: sorted_counts[k]['byCat'].get('noise', 0)))} items on the {n_other_layers} other layers (furniture, fittings, "
                 f"grid, labels and the like) build no walls: the {len(furniture)} furniture pieces among them become one coloured box each, "
                 'the rest is left out.'),
        'align': (f"The {grid['labels']} grid labels sit at the same coordinates in both drawings (within {grid['spread'] * 1000:.1f} mm), so "
                  f"{F2['cfg']['name']} goes straight onto {F1['cfg']['name']}, with no shift, and rises to {{{k2}level}} m."),
        'pair': (f"The cut fills and the paired face lines give {fmt(both(lambda k: sorted_counts[k]['wallPieces']))} wall pieces "
                 f"({both(lambda k: summary['floors'][k]['wallSources']['pairings'])} line pairings); the curtain wall gives the glass"
                 + (f", and the Revit glass wall types give {gw_txt}." if n_gw else '.')),
        'merge': (f"The pieces merge into {both(runs)} wall runs and {both(lambda k: counts[k]['column'])} columns. Each of the "
                  f"{n_doors} doors is cut out of its wall and the {n_windows} windows get panes; the {n_pass} passages stay as they are."
                  + (f" {n_closures} wall gap{'s' if n_closures != 1 else ''} with an object standing in it {'are' if n_closures != 1 else 'is'} closed." if n_closures else '')),
        'raise': (f"Walls rise to {{{k1}height}} m on {F1['cfg']['name']} and {{{k2}height}} m on {F2['cfg']['name']}; {n_lintels} "
                  f"lintels over the doors from their heads ({' / '.join(f'{h:.2f}' for h in heads)} m)"
                  + (f", {n_transoms} glass transoms" if n_transoms else '')
                  + (f"; glass partitions {' / '.join(f'{h:.2f}' for h in gw_heights)} m" if gw_heights else '')
                  + f"; railings{' and the parapet' if n_parapets == 1 else ' and parapets' if n_parapets else ''} {DEF['railingHeight']:.2f} m."),
        'finish': (f"Floor plates (open over the stairs and the lift shaft above the ground floor), stairs and room names go in, and last "
                   f"the furniture: {len(furniture)} coloured boxes, one per piece, {len(furn_kinds)} kinds. "
                   f"Done: 2 levels, {both(runs)} wall runs, {n_lintels} lintels, "
                   f"{both(lambda k: counts[k]['glass'])} glass pieces, {n_steps} stair steps, {len(rooms_out)} rooms named."),
    },
    'stats': {'doors': n_doors, 'windows': n_windows, 'passages': n_pass, 'lintels': n_lintels, 'rooms': len(rooms_out),
              'runs': both(runs), 'columns': both(lambda k: counts[k]['column']), 'transoms': n_transoms,
              'glassPartitionPanes': n_gw, 'parapets': n_parapets, 'closures': n_closures, 'steps': n_steps,
              'furniture': len(furniture), 'furnitureKinds': len(furn_kinds), 'furnitureByKind': {k['key']: k['count'] for k in furn_kinds},
              'furnitureFrontsMerged': sum(r['fronts']['absorbed'] + r['fronts']['inRuns'] for r in furn_report.values()),
              'furnitureLeftOut': sum(v['count'] for r in furn_report.values() for v in r['skipped'].values())},
}
(HERE / 'bank_stages.json').write_text(json.dumps(stages, separators=(',', ':'), ensure_ascii=False), encoding='utf-8')
print('stages:', {k: {c: len(v) // 4 for c, v in f['lines'].items()} for k, f in stage_floors.items()},
      f"{(HERE / 'bank_stages.json').stat().st_size // 1024} KB")

# ---------------------------------------------------------------------------------------------------- top view
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import PathPatch, Patch, Polygon as MPoly
from matplotlib.path import Path as MPath
STY = {'slab': dict(facecolor='#eef0ec', edgecolor='#999', lw=0.8), 'wall': dict(facecolor='#8c7b6a', edgecolor='none'),
       'column': dict(facecolor='#5d5045', edgecolor='none'), 'lintel': dict(facecolor='#d8a25e', edgecolor='none'),
       'sill': dict(facecolor='#b8a68a', edgecolor='none'), 'glass': dict(facecolor='#3f9fd0', edgecolor='#1f6f9f', lw=0.6),
       'railing': dict(facecolor='#b04ab8', edgecolor='none'), 'single': dict(facecolor='#e0a458', edgecolor='none'),
       'parapet': dict(facecolor='#c9a0d0', edgecolor='#8a4a96', lw=0.6), 'mullion': dict(facecolor='#2c5a74', edgecolor='none'),
       'step': dict(facecolor='#7cc48a', edgecolor='#2e8b47', lw=0.5)}
fig, axs = plt.subplots(1, len(floors), figsize=(11 * len(floors), 17), dpi=90)
for ax, F in zip(axs, floors):
    k = F['cfg']['key']
    for kind in ('slab', 'step', 'single', 'railing', 'parapet', 'wall', 'column', 'glass', 'mullion', 'sill', 'lintel'):
        for p in parts:
            if p['floor'] != k or p['kind'] != kind: continue
            verts, codes = [], []
            for loop in [p['o']] + p['h']:
                verts += [(x + cx, y + cy) for x, y in loop] + [(loop[0][0] + cx, loop[0][1] + cy)]
                codes += [MPath.MOVETO] + [MPath.LINETO] * (len(loop) - 1) + [MPath.CLOSEPOLY]
            sty = dict(STY[kind])
            if kind == 'glass' and p.get('label') and not p['label'].endswith((' pane', ' transom')):
                sty.update(facecolor='#00b5e2', edgecolor='#00b5e2', lw=1.6)        # glass partitions: drawn bold (10 mm)
            if kind == 'wall' and (p.get('label') or '').startswith('closure'):
                sty.update(facecolor='#d0442c')
            ax.add_patch(PathPatch(MPath(verts, codes), **sty))
    for arr, col, lw in ((model['stairs'][k]['below'], '#2e8b47', 0.8), (model['stairs'][k]['above'], '#a8d8b0', 0.6)):
        for i in range(0, len(arr), 4):
            ax.plot([arr[i] + cx, arr[i + 2] + cx], [arr[i + 1] + cy, arr[i + 3] + cy], color=col, lw=lw)
    for v in model['voids'][k]:
        ax.text(v['x'] + cx, v['y'] + cy, f"open: {v['what']}", fontsize=7, color='#666', ha='center', style='italic')
    for o in openings:
        if o['floor'] != k: continue
        col = {'door': '#c0392b', 'window': '#1f6fb2', 'passage': '#2e8b47'}[o['kind']]
        ux, uy = o['ny'], -o['nx']; h = o['width'] / 2
        if o['kind'] == 'passage':
            ax.plot([o['x'] - ux * h + cx, o['x'] + ux * h + cx], [o['y'] - uy * h + cy, o['y'] + uy * h + cy], color=col, lw=1.6, ls='--')
        ax.text(o['x'] + cx + o['nx'] * 0.22, o['y'] + cy + o['ny'] * 0.22, o['id'].split('-')[-1], fontsize=6.5, color=col,
                ha='center', va='center')
    for r in rooms_out:
        if r['floor'] == k: ax.text(r['x'] + cx, r['y'] + cy, r['label'], fontsize=8, color='#1f4e79', ha='center')
    ax.set_title(f"{F['cfg']['name']} ({F['cfg']['level']:+.2f} m): walls brown, lintels tan, glass blue (glass partitions bold cyan), "
                 'railings purple, parapet lilac, closures red,\nstairs green (steps filled); opening numbers: doors red, windows blue, '
                 'passages green; "open" = no floor (stair, lift shaft)', fontsize=9)
    ax.autoscale(); ax.set_aspect('equal'); ax.axis('off')
plt.tight_layout(); plt.savefig(HERE / 'bank_topview.png'); plt.close()
import shutil; shutil.copyfile(HERE / 'bank_topview.png', HERE.parent / 'bank_topview.png')     # beside the viewer page
print('written bank_stages.json, bank_summary.json, bank_topview.png (also ../bank_topview.png)')

# ---------------------------------------------------------------------------------------------------- furniture list and picture
# The family list for the 3D team (the office-default heights), and both levels with one box per piece in its kind's colour.
fk.write_csv(HERE.parent / 'bank_furniture_list.csv', fk.csv_text(furniture, furn_kinds, CFG['floors'], model['offset']))
kind_by = {k['key']: k for k in furn_kinds}
n_by = {F['cfg']['key']: collections.Counter(p['kind'] for p in furniture if p['floor'] == F['cfg']['key']) for F in floors}
FUR_STY = {'slab': dict(facecolor='#f4f4f1', edgecolor='#cfcfc9', lw=0.6), 'wall': dict(facecolor='#8f8a84', edgecolor='none'),
           'column': dict(facecolor='#6b665f', edgecolor='none'), 'glass': dict(facecolor='#b9dcea', edgecolor='#7fb3cc', lw=0.5),
           'parapet': dict(facecolor='#b9b4ad', edgecolor='none'), 'mullion': dict(facecolor='#7fb3cc', edgecolor='none')}
fig, axs = plt.subplots(1, len(floors), figsize=(11 * len(floors), 15), dpi=90)
for ax, F in zip(axs, floors):
    k = F['cfg']['key']
    for kind, sty in FUR_STY.items():
        for p in parts:
            if p['floor'] != k or p['kind'] != kind: continue
            verts, codes = [], []
            for loop in [p['o']] + p['h']:
                verts += list(map(tuple, loop)) + [tuple(loop[0])]
                codes += [MPath.MOVETO] + [MPath.LINETO] * (len(loop) - 1) + [MPath.CLOSEPOLY]
            ax.add_patch(PathPatch(MPath(verts, codes), **sty))
    for f in sorted((f for f in furniture if f['floor'] == k), key=lambda f: kind_by[f['kind']]['onTop']):      # tops after their supports
        ax.add_patch(MPoly(list(fk.rect_of(f).exterior.coords), closed=True, fc=kind_by[f['kind']]['colour'], ec='black', lw=0.4,
                           alpha=0.92, zorder=3 + kind_by[f['kind']]['onTop']))
    ax.set_title(f"{F['cfg']['name']} ({F['cfg']['level']:+.2f} m): {sum(n_by[k].values())} furniture boxes, one per piece, colour = kind", fontsize=12)
    ax.autoscale(); ax.set_aspect('equal'); ax.axis('off')
legend = [Patch(fc=k['colour'], ec='black', label=f"{k['label']}: {' + '.join(str(n_by[F['cfg']['key']][k['key']]) for F in floors)}, "
                f"{k['height']} mm" + (f", base {k['base']} mm" if k['base'] else '')) for k in furn_kinds]
cols = 4
fig.legend(handles=legend, loc='lower center', ncol=cols, fontsize=11, frameon=False, title=f"Kind: pieces on {' + '.join(F['cfg']['key'] for F in floors)}, default height")
fig.tight_layout(rect=(0, 0.025 * math.ceil(len(legend) / cols) + 0.03, 1, 1))
fig.savefig(HERE.parent / 'bank_furniture_boxes.png'); plt.close()
print(f"written bank_furniture_list.csv ({len(furniture)} rows) and bank_furniture_boxes.png in {HERE.parent.name}/")
