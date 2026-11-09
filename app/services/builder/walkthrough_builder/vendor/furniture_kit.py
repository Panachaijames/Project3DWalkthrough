"""Furniture proxy boxes: the logic the bank, house and presidential-suite builders share (28 Oct 2026).

One oriented box per furniture piece: the minimum rotated rectangle of the piece's drawn geometry, stood up to its kind's
height (README.md in this folder has the model JSON, the kinds and the CSV this module writes). Pure Python 3 + shapely 2,
no project imports: a builder puts this folder on sys.path and imports it. Nothing in here names a drawing, a handle, a
layer or a block: only fixed vocabularies of words and physical sizes in metres.
  KINDS ............ the kinds table in legend order (key, label, colour, height mm, base mm, onTop, support, blocks)
  classify() ....... family name -> kind: the office's own words (the project file's furniture.words) first, then the ordered word
                     rules, then the layer name's words, else 'other'; None = not furniture (an outlet, a cover, a skip word ...)
  box_of() ......... points -> the box: centre, w >= d, rot in [0, 180)
  merge_fronts() ... cabinet door / drawer fronts (thin panels) are absorbed into the cabinet they stand on, or form a run
  loose_boxes() .... shapes drawn loose (not as a block) that touch form clusters; a cluster that is a good rectangle is a box
  assign_supports()  the support each onTop piece stands on: the nearest table, counter or cabinet whose box holds its centre or
                     lies within OVERHANG (10 cm) of it (a printer on a counter's overhang), else None; supports stand on nothing
  mark_approaches()  the doors and passages whose approach a box stands in (the zone a person needs to walk straight through):
                     the box's 'approach' list and a note, from the model's openings
  finish() ......... rounding, ids, supports, approaches, the kinds table with counts and the office's heights
  csv_text(), write_csv()  the family list for the 3D team
A piece is a dict: floor, kind, family, block, layer, handle, x, y, w, d, rot, on, n, note (the model JSON's keys without id and
approach, which finish() works out).
"""
import collections, functools, json, math, re
from pathlib import Path
from shapely import get_coordinates
from shapely.geometry import MultiPoint, Polygon
from shapely.strtree import STRtree

# Physical sizes (metres)
MIN_SIDE = 0.01       # a box is never thinner than this
NO_AREA = 0.001       # points whose rectangle is thinner than this enclose no area (one point, one line): no box
MAX_SIDE = 12.0       # a box longer than this is not a piece of furniture (a run of cabinets along a wall is under it)
THIN = 0.06           # a cabinet panel thinner than this is a door / drawer front, not a cabinet
NEAR = 0.15           # a front belongs to the cabinet box within this distance
GOOD_FILL = 0.9       # a cabinet box grows to take in a front only if the two together still fill this much of their rectangle
RUN_GAP = 0.05        # fronts with no cabinet behind them: neighbours this close (and parallel) are one run
RUN_ANGLE = 5.0       # ... parallel within this many degrees
RUN_DEPTH = 0.45      # ... and the run gets a typical casework depth (the fronts only show its face)
TOUCH = 0.01          # loose shapes closer than this belong to one cluster
LOOSE_FILL = 0.7      # a loose cluster is a box if its hull fills this much of its rectangle
OVERHANG = 0.10       # an onTop piece stands on a support whose box holds its centre or lies within this of it (a counter's worktop overhangs)
PERSON = 0.30         # a person's radius: the approach of a door or passage is its width plus this on each side, along the wall
APPROACH_SIDE = 0.90  # ... and reaches this far out of the wall's line on each side (1.80 m across it)
APPROACH_AREA = 0.0025   # a box that overlaps the opening's own width within that reach by this much (25 cm2) is in the approach, wherever its centre is

_COLS = ('key', 'label', 'colour', 'height', 'base', 'onTop', 'support', 'blocks')
KINDS = [dict(zip(_COLS, row)) for row in (        # the README's table: legend order; height / base in mm are the office defaults
    ('atm', 'ATM / kiosk', '#c0392b', 1500, 0, False, False, True),
    ('computer', 'Computer / monitor', '#7b3fb5', 450, 0, True, False, True),
    ('printer', 'Printer / copier', '#8e8e8e', 300, 0, True, False, True),
    ('phone', 'Telephone', '#d1306a', 150, 0, True, False, True),
    ('tv', 'TV / wall screen', '#34408f', 600, 900, False, False, True),
    ('partition', 'Privacy screen / panel', '#4fb99f', 1200, 0, False, False, True),
    ('curtain', 'Curtain', '#c9a0dc', 2400, 0, False, False, False),
    ('lamp', 'Lamp', '#ffd23f', 500, 0, True, False, True),
    ('plant', 'Plant', '#2e9e4f', 600, 0, True, False, True),
    ('sanitary', 'Sanitary fitting', '#17a2a2', 850, 0, False, False, True),
    ('appliance', 'Appliance', '#b8860b', 900, 0, False, False, True),
    ('bed', 'Bed', '#e377c2', 500, 0, False, False, True),
    ('seat', 'Chair / stool', '#e07b00', 450, 0, False, False, True),
    ('sofa', 'Sofa / armchair', '#ffb347', 800, 0, False, False, True),
    ('seat-back', 'Seat back', '#fa8072', 800, 0, False, False, True),
    ('table', 'Table / desk', '#8a5a2b', 750, 0, False, True, True),
    ('coffee-table', 'Coffee / side table', '#c9a37a', 450, 0, False, True, True),
    ('bar-table', 'Bar table', '#5a3a1a', 1000, 0, False, True, True),
    ('counter', 'Counter top', '#a0522d', 850, 0, False, True, True),
    ('cabinet', 'Cabinet / casework', '#2f7fc1', 900, 0, False, True, True),
    ('tall-cabinet', 'Tall cabinet / wardrobe', '#1b4f8a', 2100, 0, False, False, True),
    ('other', 'Other furniture', '#6b6b6b', 750, 0, False, False, True),
)]
FRONT_KINDS = ('cabinet', 'tall-cabinet')            # a thin panel of these kinds is a front
CASE_KINDS = ('cabinet', 'tall-cabinet', 'counter')  # fronts are absorbed into a box of these kinds
APPROACH_KINDS = ('door', 'passage')                 # the openings you walk through: a window has no approach
APPROACH_NOTE = 'in the approach of '                # the note's sentence, then the opening ids joined by ', '

# ---------------------------------------------------------------------------------------------------- vocabulary
# Words are matched whole, ignoring case: no letter right before or after (digits, '_' and '-' are fine), a trailing 's' is
# allowed, and a space in a phrase matches any run of spaces, '_' and '-'. So 'table' is not in 'ADJUSTABLE' or 'TABLET', 'bed' not in
# 'BEDSIDE', 'desk' not in 'DESKTOP'. CamelCase names are split first ('SmartToilet' -> 'Smart Toilet').
# Each rule is (kind, words, words that rule the kind out): the first rule that matches wins, so the specific come before the
# general (a table lamp is a lamp, a potted plant on a stool is a plant, a sofa bench is a sofa, a chair bench-back stool is a seat,
# a sofa back cushion is a seat back: the back drawn as a piece of its own, tried before the sofa and seat rules).
RULES = [
    ('atm', 'atm|kiosk|cash machine|cash dispenser', ''),
    ('computer', 'computer|monitor|laptop|notebook|imac|thin client', 'desk|table|chair|stool|stand|trolley|cart|cabinet|rack|bag|case'),
    ('printer', 'printer|copier|photocopier|scanner|plotter|fax', 'desk|table|stand|cabinet|trolley|cart'),
    ('phone', 'telephone|phone|handset|intercom', 'booth|desk|table|stand|cabinet'),
    ('tv', 'tv|television|projector|wall screen|flat screen', 'stand|unit|cabinet|console|table|bench|credenza|sideboard|rack|cart|trolley'),
    ('partition', 'partition|privacy screen|screen|divider|movable panel|movable wall|folding wall', ''),
    ('curtain', 'curtain|drape|blind', ''),
    ('lamp', 'lamp|lantern|torchiere', ''),
    ('plant', 'plant|planter|potted|tree|flower|bush|fern|vase|shrub|palm|bamboo|ficus|orchid|cactus|topiary|foliage', ''),
    ('sanitary', 'toilet|wc|water closet|urinal|bidet|basin|lavatory|sink|shower|bathtub|bath tub|bath'
                 '|สุขภัณฑ์|อ่างล้างหน้า|โถส้วม|ชักโครก|โถปัสสาวะ', 'cabinet|unit|counter|table|chair|stool|bench|mat'),
    ('appliance', 'appliance|refrigerator|fridge|minibar|mini bar|freezer|oven|microwave|cooker|stove|hob|dishwasher|washing machine|washer|dryer'
                  '|water cooler|water dispenser|vending|coffee machine|coffee maker', 'cabinet|unit|counter|table'),
    ('bed', 'bed|mattress|cot|crib|headboard', 'side|room|bench|table|stool|chair|sofa|cabinet|cover'),
    ('tall-cabinet', 'tall cabinet|tall unit|tall storage|tall locker|tall shelf|wardrobe|closet|armoire|locker|bookcase|bookshelf|book shelf'
                     '|shelving|display case|data racks?|server racks?|network racks?|racks? data|racks? server', ''),
    ('counter', 'counter top|countertop|worktop|work top|reception desk|reception counter|teller counter|service counter|bar counter|counter',
     'stool|chair|seat|bench'),
    ('bar-table', 'bar table|bar height table|high table|bistro table|poseur table', ''),
    ('coffee-table', 'coffee table|side table|end table|cocktail table|tea table|occasional table|bedside|bed side|nightstand|night stand'
                     '|table occasional|table side|table coffee', ''),
    ('cabinet', 'cabinet|cupboard|drawer|casework|credenza|sideboard|buffet|shelf|shelves|dresser|vanity unit|pantry|chest|tv unit|tv stand'
                '|tv console|media console', 'chair|stool|seat|bench|sofa'),
    ('table', 'table|desk|worktable|work table|workstation|trestle', 'chair|stool|seat|seating|bench|sofa|armchair'),
    ('seat-back', 'seat back|backrest|back rest|back cushion', ''),
    ('sofa', 'sofa|couch|settee|loveseat|love seat|armchair|arm chair|lounge chair|lounger|recliner|chaise|chesterfield|banquette|sectional', ''),
    ('seat', 'chair|stool|bench|seat|seating|ottoman|pouf|pouffe', ''),
]
# What the layer name's words say when the block's name says nothing (the AIA layer names the Revit export uses).
LAYER_WORDS = [('sanitary', 'sanr|sanitary|plumbing'), ('plant', 'plnt|plant|planting'), ('cabinet', 'case|casework|joinery|millwork')]
# Things on furniture layers that are not furniture.
SKIP = ('outlet|socket|switch|cover|mullion|grille|diffuser|sprinkler|detector|junction box|floor box|rug|carpet|doormat|floor mat')


def _rx(words, literal=False):
    """'a|b c' -> the regex of those whole words (see the vocabulary note); literal: the words are text, not regex."""
    sep = r'[\s_\-]*'
    alts = '|'.join(sep.join(re.escape(t) if literal else t for t in w.split()) for w in words.split('|') if w.strip())
    return re.compile(r'(?<![a-z])(?:' + alts + r')s?(?![a-z])', re.I)


_RULES = [(k, _rx(w), _rx(n) if n else None) for k, w, n in RULES]
_LAYERS = [(k, _rx(w)) for k, w in LAYER_WORDS]
_SKIP = _rx(SKIP)
_KEYS = [k['key'] for k in KINDS]


def _camel(s):
    """'SmartToilet' -> 'Smart Toilet', 'TVStand' -> 'TV Stand'."""
    return re.sub(r'(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])', ' ', s)


@functools.lru_cache(maxsize=16)
def _office(key):
    """The office's own words from the project file ({kind: [word, ...]} and a skip list), compiled once. They are plain text, not
    regex, matched whole like the vocabulary's words (a hyphen in a word is a hyphen; a space matches a run of spaces, '_' and '-')."""
    words, skip = json.loads(key)
    words = {k: ws for k, ws in words.items() if not k.startswith('_')}        # '_why' and the like are notes in the project file
    for kind in words:
        if kind not in _KEYS: raise ValueError(f'furniture.words: unknown kind {kind!r} (allowed: {", ".join(_KEYS)})')
    return [(k, _rx('|'.join(ws), True)) for k, ws in words.items() if ws], (_rx('|'.join(skip), True) if skip else None)


def classify(name, layer='', words=None, skip=None):
    """The kind of a block from its family name: the office's own words first (the project file's furniture.words, e.g. {'seat':
    ['Maker-Name']} for a name the vocabulary cannot know: they win over the vocabulary above), then the vocabulary, then the layer
    name's words, else 'other'. None when the block is not furniture: its name has a skip word, the office's or ours (checked first,
    so it also beats the office's words)."""
    text = _camel(name or '')
    mine, mine_skip = _office(json.dumps([words or {}, list(skip or [])], sort_keys=True))
    if _SKIP.search(text) or (mine_skip and mine_skip.search(text)): return None
    for kind, rx in mine:
        if rx.search(text): return kind
    for kind, rx, no in _RULES:
        if rx.search(text) and not (no and no.search(text)): return kind
    for kind, rx in _LAYERS:
        if rx.search(layer or ''): return kind
    return 'other'


# ---------------------------------------------------------------------------------------------------- the boxes
def box_of(points):
    """The minimum rotated rectangle of the points: {'x', 'y' (its centre), 'w' >= 'd', 'rot'}, rot in degrees counter-clockwise
    from +x to the long side, in [0, 180); a square has no long side, its rot is taken in [0, 90). A rectangle thinner than MIN_SIDE
    is given MIN_SIDE. None when the points enclose no area (fewer than two distinct points, or all on one line)."""
    hull = MultiPoint(sorted({(round(x, 6), round(y, 6)) for x, y in points})).convex_hull
    if hull.geom_type != 'Polygon': return None
    c = list(hull.minimum_rotated_rectangle.exterior.coords)[:4]
    e1, e2 = math.dist(c[0], c[1]), math.dist(c[1], c[2])
    a, b, w, d = (c[0], c[1], e1, e2) if e1 >= e2 else (c[1], c[2], e2, e1)
    if d < NO_AREA: return None
    rot = math.degrees(math.atan2(b[1] - a[1], b[0] - a[0])) % 180
    if w - d < 0.001: rot %= 90
    return {'x': (c[0][0] + c[2][0]) / 2, 'y': (c[0][1] + c[2][1]) / 2, 'w': w, 'd': max(d, MIN_SIDE), 'rot': rot}


def rect_of(p):
    """The oriented rectangle of a box (x, y, w, d, rot) as a shapely polygon."""
    a = math.radians(p['rot']); c, s = math.cos(a), math.sin(a)
    hw, hd = p['w'] / 2, p['d'] / 2
    return Polygon([(p['x'] + sx * hw * c - sy * hd * s, p['y'] + sx * hw * s + sy * hd * c) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))])


def _gap(p, s):
    """How far the centre of box p is from the oriented box s: 0 inside it, else the distance to its nearest edge or corner."""
    a = math.radians(s['rot']); dx, dy = p['x'] - s['x'], p['y'] - s['y']
    along, across = abs(dx * math.cos(a) + dy * math.sin(a)) - s['w'] / 2, abs(-dx * math.sin(a) + dy * math.cos(a)) - s['d'] / 2   # past its edges (< 0: inside them)
    return math.hypot(max(along, 0), max(across, 0))


def _turn(a, b):
    """The angle between the long axes of two boxes, 0-90 degrees."""
    t = abs(a['rot'] - b['rot']) % 180
    return min(t, 180 - t)


# ---------------------------------------------------------------------------------------------------- merging
def _is_front(p):
    return p['kind'] in FRONT_KINDS and p['d'] < THIN


def _tally(fams):
    return '; '.join(f'{n} x {f}' for f, n in fams.most_common())


def merge_fronts(pieces):
    """Revit casework draws every cabinet door and drawer as a thin panel (a few cm thick, 0.2-0.6 m long) on the face of the
    cabinet: a piece of a cabinet kind thinner than THIN (6 cm) is a front, not a cabinet. On each floor:
      - a front within NEAR (15 cm) of a cabinet, tall cabinet or counter box (the nearest; the smaller box if tied) is absorbed
        into it: its n grows, its note lists the fronts' families, and the box grows to include the front only when the two
        together still fill GOOD_FILL (90 %) of their minimum rectangle (a door in the cabinet's face, or a few cm proud of it;
        a door drawn swung open would make the box an L, so then the front is only counted).
      - fronts with no cabinet near them that lie edge to edge (parallel within RUN_ANGLE, gaps up to RUN_GAP, 5 cm) are one run:
        a box as long as the run and RUN_DEPTH (0.45 m, a typical casework depth) deep, centred on the fronts' line (the drawing
        shows only the face, not which side the cabinet stands on). A lone front stays as it is.
    -> (the new list of pieces, {'absorbed': fronts absorbed, 'grown': boxes that grew, 'runs': runs made, 'inRuns': fronts in them})"""
    out = [dict(p) for p in pieces]
    keep = [True] * len(out)
    stats = {'absorbed': 0, 'grown': 0, 'runs': 0, 'inRuns': 0}
    notes = collections.defaultdict(collections.Counter)
    for floor in dict.fromkeys(p['floor'] for p in out):
        ids = [i for i, p in enumerate(out) if p['floor'] == floor]
        cases = [i for i in ids if out[i]['kind'] in CASE_KINDS and out[i]['d'] >= THIN]
        loose = []
        for i in sorted((i for i in ids if _is_front(out[i])), key=lambda i: (out[i]['x'], out[i]['y'])):
            f = out[i]; fr = rect_of(f)
            near = sorted((fr.distance(rect_of(out[c])), out[c]['w'] * out[c]['d'], c) for c in cases)
            if not near or near[0][0] > NEAR:
                loose.append(i); continue
            c = out[near[0][2]]; cr = rect_of(c)
            if not cr.buffer(0.005).contains(fr):
                u = cr.union(fr)
                grown = box_of(list(u.exterior.coords)) if u.geom_type == 'Polygon' else None
                if grown and u.area >= GOOD_FILL * grown['w'] * grown['d']:
                    c.update(grown); stats['grown'] += 1
            c['n'] += f['n']; keep[i] = False; stats['absorbed'] += 1
            notes[near[0][2]][f['family']] += f['n']
        rects = {i: rect_of(out[i]) for i in loose}              # edge-to-edge neighbours, by union-find
        root = {i: i for i in loose}
        find = lambda i: i if root[i] == i else find(root[i])
        for k, a in enumerate(loose):
            for b in loose[k + 1:]:
                if _turn(out[a], out[b]) <= RUN_ANGLE and rects[a].distance(rects[b]) <= RUN_GAP: root[find(b)] = find(a)
        runs = collections.defaultdict(list)
        for i in loose: runs[find(i)].append(i)
        for members in runs.values():
            if len(members) < 2: continue
            ps = [out[i] for i in members]
            sx = sum(p['w'] * math.cos(2 * math.radians(p['rot'])) for p in ps); sy = sum(p['w'] * math.sin(2 * math.radians(p['rot'])) for p in ps)
            ang = (math.degrees(math.atan2(sy, sx)) / 2) % 180
            u = (math.cos(math.radians(ang)), math.sin(math.radians(ang))); n = (-u[1], u[0])
            s = [x * u[0] + y * u[1] for i in members for x, y in rects[i].exterior.coords]
            t = sum(p['w'] * (p['x'] * n[0] + p['y'] * n[1]) for p in ps) / sum(p['w'] for p in ps)
            w, mid = max(s) - min(s), (max(s) + min(s)) / 2
            fams = collections.Counter(p['family'] for p in ps)
            top = next(p for p in ps if p['family'] == fams.most_common(1)[0][0])       # the run is named after its commonest front
            first = out[members[0]]
            first.update(x=u[0] * mid + n[0] * t, y=u[1] * mid + n[1] * t, w=w, d=RUN_DEPTH, rot=ang, n=sum(p['n'] for p in ps), handle='',
                         kind=top['kind'], family=top['family'], block=top['block'], layer=top['layer'], note=f'run of {len(ps)} fronts: {_tally(fams)}')
            if w < RUN_DEPTH: first.update(w=RUN_DEPTH, d=w, rot=(ang + 90) % 180)
            for i in members[1:]: keep[i] = False
            stats['runs'] += 1; stats['inRuns'] += len(ps)
    for c, fams in notes.items():
        out[c]['note'] = '; '.join(x for x in (out[c].get('note', ''), f'fronts merged: {_tally(fams)}') if x)
    return [p for p, k in zip(out, keep) if k], stats


def loose_boxes(shapes):
    """Shapes drawn loose (not inside a block) on one layer, as shapely LineStrings (open outlines) and Polygons (closed outlines,
    hatches): shapes that touch within TOUCH (1 cm) form a cluster; a cluster whose convex hull fills LOOSE_FILL (70 %) of its
    minimum rectangle, and that has 3 or more shapes or a closed one, is a box (a casework run drawn as lines and arcs).
    -> ([box + 'n' = shapes in it], [(shapes, why) for the clusters left out])"""
    if not shapes: return [], []
    buf = [s.buffer(TOUCH / 2) for s in shapes]
    tree = STRtree(buf)
    root = list(range(len(shapes)))

    def find(i):
        while root[i] != i: root[i] = root[root[i]]; i = root[i]
        return i
    for i, b in enumerate(buf):
        for j in tree.query(b, predicate='intersects'): root[find(int(j))] = find(i)
    groups = collections.defaultdict(list)
    for i in range(len(shapes)): groups[find(i)].append(i)
    boxes, left = [], []
    for g in sorted(groups.values(), key=min):
        pts = [tuple(c) for i in g for c in get_coordinates(shapes[i])]
        box = box_of(pts)
        if box is None: left.append((len(g), 'no area')); continue
        fill = MultiPoint(pts).convex_hull.area / (box['w'] * box['d'])
        if fill < LOOSE_FILL: left.append((len(g), f'hull fills {fill:.0%} of its rectangle')); continue
        if len(g) < 3 and not any(shapes[i].geom_type in ('Polygon', 'MultiPolygon') for i in g):
            left.append((len(g), 'fewer than 3 shapes and none closed')); continue
        boxes.append({**box, 'n': len(g)})
    return boxes, left


# ---------------------------------------------------------------------------------------------------- the kinds table, ids, supports, approaches
def kinds_table(heights=None, bases=None):
    """A copy of KINDS with the office's heights and bases (mm, {kind: value}, from the project file's furniture section)."""
    table = [dict(k) for k in KINDS]
    by = {k['key']: k for k in table}
    for what, over, low in (('height', heights, 1), ('base', bases, 0)):
        for kind, v in (over or {}).items():
            if kind.startswith('_'): continue                         # a note in the project file
            if kind not in by: raise ValueError(f'furniture.{what}s: unknown kind {kind!r} (allowed: {", ".join(_KEYS)})')
            if isinstance(v, bool) or not isinstance(v, (int, float)) or not low <= v <= 10000:
                raise ValueError(f'furniture.{what}s.{kind}: {v!r} is not a number of mm from {low} to 10000')
            by[kind][what] = v
    return table


def assign_supports(pieces, kinds):
    """Each onTop piece (computer, printer, phone, lamp, plant) gets the id of the nearest support (table, counter, cabinet ...) on
    its floor whose box holds its centre or lies within OVERHANG (10 cm) of it: a printer on a counter's overhang. Nearest is the
    smallest distance from the centre to the support's rectangle (a piece inside a box is at 0), a tie going to the smaller box
    (then the lower id); no support that close -> None. Only support kinds count (a tall cabinet is none), and they, like every
    piece that is not onTop, never sit on anything, so there are no chains. The pieces need their ids."""
    by = kinds if isinstance(kinds, dict) else {k['key']: k for k in kinds}
    sup = [p for p in pieces if by[p['kind']]['support']]
    for p in pieces:
        p['on'] = None
        if not by[p['kind']]['onTop']: continue
        near = min(((round(_gap(p, s), 6), s['w'] * s['d'], s['id']) for s in sup if s['floor'] == p['floor']), default=None)    # distances to the micrometre, so that a tie is a tie
        if near and near[0] <= OVERHANG: p['on'] = near[2]


def mark_approaches(pieces, openings):
    """Each box gets 'approach', the sorted ids of the doors and passages of its floor whose approach it stands in ([] when none;
    windows do not count), and, when there are any, the note 'in the approach of L2-002, L2-004' (after any other note, joined
    by '; '), so that the 3D team can see which pieces to move. The approach of an opening is what a person of radius PERSON
    needs to walk straight through it: the zone Z, a rectangle centred on the opening, along the wall (its width + 2 x PERSON) by
    across it 2 x APPROACH_SIDE (1.80 m), turned by the opening's normal (nx, ny: only its direction counts). A box is in the
    approach when its centre lies in Z (the edge included) or when it overlaps the clear corridor (the opening's own width by the
    same 1.80 m) by at least APPROACH_AREA (25 cm2): a long box that only touches the margin of Z with its end is not in it, a desk
    lying across the corridor is, whatever its centre. Pieces and openings are in one frame (the model's), the pieces as finish()
    has rounded them, so the model JSON gives the same answer again. Distances are taken to the micrometre and areas to the mm2,
    so that an edge case is an edge case whatever the float noise. Marking again gives the same result (the old sentence goes)."""
    zones = collections.defaultdict(list)                               # floor -> its doors and passages with their corridors
    for o in openings:
        if o['kind'] not in APPROACH_KINDS: continue
        size = math.hypot(o['nx'], o['ny'])
        if not size: raise ValueError(f"opening {o['id']!r} has no normal (nx, ny) = (0, 0)")
        n = (o['nx'] / size, o['ny'] / size); u = (n[1], -n[0])         # across the wall, along it
        at = lambda s, c: (o['x'] + s * u[0] + c * n[0], o['y'] + s * u[1] + c * n[1])          # s metres along the wall from the opening's middle, c across it
        half = o['width'] / 2
        corridor = Polygon([at(sa * half, sc * APPROACH_SIDE) for sa, sc in ((-1, -1), (1, -1), (1, 1), (-1, 1))])
        zones[o['floor']].append((o, u, n, corridor))
    for p in pieces:
        box, ids = rect_of(p), []
        for o, u, n, corridor in zones.get(p['floor'], ()):
            dx, dy = p['x'] - o['x'], p['y'] - o['y']
            past_ends = abs(dx * u[0] + dy * u[1]) - o['width'] / 2 - PERSON                # beyond Z's ends along the wall (<= 0: inside Z)
            past_sides = abs(dx * n[0] + dy * n[1]) - APPROACH_SIDE                         # ... and past its sides across the wall
            centre_in_z = round(past_ends, 6) <= 0 and round(past_sides, 6) <= 0
            if centre_in_z or round(box.intersection(corridor).area, 6) >= APPROACH_AREA: ids.append(o['id'])
        note = re.sub(f'(?:^|; ){re.escape(APPROACH_NOTE)}[^;]*$', '', p.get('note') or '')
        p['approach'] = sorted(ids)
        p['note'] = '; '.join(x for x in (note, APPROACH_NOTE + ', '.join(p['approach'])) if x) if ids else note


def finish(pieces, floors, heights=None, bases=None, openings=None):
    """Pieces (model frame, metres) -> the model JSON's two lists. Numbers are rounded here (x, y, w, d to the millimetre, rot to 0.01
    degree, in [0, 180); a square or round box, w - d under 1 mm before the rounding, has no long axis and takes [0, 90)); the
    pieces are ordered by floor (as `floors`), kind (the table's order), then x and y, and numbered '<floor>-<kind>-<nnn>' in that
    order, so the same drawing always gives the same ids; supports are assigned, and the approaches of the model's `openings`
    (the doors and passages in the same frame; none: no approaches) are marked, on the rounded boxes: every box has 'approach'.
    -> (furniture: dicts in the README's key order, sorted by floor, kind, id; furnitureKinds: the table with the office's heights
    and bases and a 'count', only the kinds that occur)."""
    floors = [f['key'] if isinstance(f, dict) else f for f in floors]
    kinds = kinds_table(heights, bases)
    order = {k['key']: i for i, k in enumerate(kinds)}
    r3 = lambda v: round(v, 3) + 0.0
    rows = []
    for p in pieces:
        if p['floor'] not in floors or p['kind'] not in order: raise ValueError(f"piece on floor {p['floor']!r} of kind {p['kind']!r} is not in the floors / kinds")
        turn = 90 if p['w'] - p['d'] < 0.001 else 180                     # a square turned 90 degrees is the same box
        rot = round(p['rot'] % turn, 2)
        rows.append({'floor': p['floor'], 'kind': p['kind'], 'family': p['family'], 'block': p['block'], 'layer': p['layer'],
                     'handle': p['handle'], 'x': r3(p['x']), 'y': r3(p['y']), 'w': r3(p['w']), 'd': r3(p['d']),
                     'rot': 0.0 if rot >= turn else rot, 'on': None, 'approach': [], 'n': p['n'], 'note': p.get('note', '')})
    rows.sort(key=lambda r: (floors.index(r['floor']), order[r['kind']], r['x'], r['y'], r['family'], r['block'], r['w'], r['d'], r['rot']))
    seen = collections.Counter()
    out = []
    for r in rows:
        seen[r['floor'], r['kind']] += 1
        out.append({'id': f"{r['floor']}-{r['kind']}-{seen[r['floor'], r['kind']]:03d}", **r})
    assign_supports(out, kinds)
    mark_approaches(out, openings or [])
    count = collections.Counter(r['kind'] for r in out)
    return out, [{**k, 'count': count[k['key']]} for k in kinds if count[k['key']]]


# ---------------------------------------------------------------------------------------------------- the family list (CSV)
CSV_COLUMNS = ('id', 'level', 'kind', 'kind_label', 'family', 'block', 'layer', 'dxf_handle', 'x_m', 'y_m', 'width_mm', 'depth_mm',
               'height_mm', 'base_mm', 'rotation_deg', 'on_top_of', 'merged', 'note')


def _field(v):
    """RFC 4180: a field with a comma, a double quote, CR or LF goes in double quotes, inner quotes doubled."""
    s = str(v)
    return '"' + s.replace('"', '""') + '"' if any(ch in s for ch in ',"\r\n') else s


def _fixed(v, nd):
    """Fixed notation, never '-0.000'."""
    s = f'{v:.{nd}f}'
    return s[1:] if s.startswith('-') and not s.strip('-0.') else s


def csv_text(furniture, kinds, floors, offset, heights=None):
    """The family list exactly as README.md describes it: CSV_COLUMNS, CRLF after every row (the last too), sorted by floor (as
    `floors`), kind (the order of `kinds`), id. x_m, y_m are drawing coordinates (model x, y + offset, 3 decimals); sizes, heights
    and bases are whole mm (rounded half up, like JavaScript's Math.round); base_mm is the resolved underside (a piece on a table
    stands at the table's top); rotation_deg has 1 decimal. `heights` = {kind: mm} replaces the kinds' heights (what the viewer
    has typed in). The text has no byte-order mark: write_csv adds it."""
    floors = [f['key'] if isinstance(f, dict) else f for f in floors]
    by = {k['key']: k for k in kinds}
    order = {k['key']: i for i, k in enumerate(kinds)}
    whole = lambda v: int(math.floor(v + 0.5))
    height = lambda kind: whole((heights or {}).get(kind, by[kind]['height']))
    ids = {p['id']: p for p in furniture}
    lines = [','.join(CSV_COLUMNS)]
    for p in sorted(furniture, key=lambda p: (floors.index(p['floor']), order[p['kind']], p['id'])):
        k = by[p['kind']]
        base = by[ids[p['on']]['kind']]['base'] + height(ids[p['on']]['kind']) if p['on'] else k['base']
        row = [p['id'], p['floor'], p['kind'], k['label'], p['family'], p['block'], p['layer'], p['handle'],
               _fixed(p['x'] + offset[0], 3), _fixed(p['y'] + offset[1], 3), whole(p['w'] * 1000), whole(p['d'] * 1000),
               height(p['kind']), whole(base), _fixed(p['rot'], 1), p['on'] or '', p['n'], p['note'] or '']
        lines.append(','.join(_field(v) for v in row))
    return '\r\n'.join(lines) + '\r\n'


def write_csv(path, text):
    """The family list as UTF-8 with a byte-order mark (Excel then opens Thai text right); bytes, so the CRLF stay CRLF."""
    Path(path).write_bytes(b'\xef\xbb\xbf' + text.encode('utf-8'))
