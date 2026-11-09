"""The port of bank_test/src/build_model.py (26 - 29 Oct 2026) into functions (docs/upload/DESIGN.md U-10.3, U-10.4,
U-10.5). Every arithmetic expression and every order of the prototype is kept; what was module state (CFG, DEF, FURN,
DOMINANT, the floors) is passed in a context `X`. What changed, each switching on only when its data is there (the bank's
model, summary and CSV are byte-identical, the goldens prove it):

  * any number of floors; the floor's own units for sizes read from names; per-floor door / window defaults; the door
    head order name -> floor -> the drawing's most common -> default (U-10.4); W x W x H runs in door names (the last
    number, U-10.3); the vocabulary's patterns from the settings (defaults: the bank's);
  * the INSERT readers (door blocks, Revit wall types, object closures, furniture) read the whole-subtree reading
    F['src'], the line readers the per-item reading F['items'] (U-9.1: the same list under wholeFile);
  * options (U-10.5): revitWallTypes, parapets 'auto' (only where the floor's wall layers carry solid fills), objectClosures,
    liftShafts, plinth, offset; the `screen` role (glass parts labelled 'screen', never cut, never glazing);
    eitherKind doors glazed like windows; a window "opening over a low wall" gets a 0.90 m sill; opening fixes
    (kind, head, sill) and accepted outline edges (U-10.6);
  * provenance kept for the report: the item keys of every single-line piece, the railings left out, the labels that
    are not room names, the plates dropped.

The rules themselves are the prototype's (its docstring, rules 1 - 12); read it there.
"""
from __future__ import annotations

import collections
import math
import re
import statistics

from shapely import affinity
from shapely.geometry import LineString, MultiPoint, Point, Polygon
from shapely.ops import unary_union

from ..names import family as _family
from ..vendor.load import load
from . import items as I

_mc = load('merge_cad')
_geom = load('geom')
fk = load('furniture_kit')
strips, solidify = _mc.strips, _mc.solidify
polys, even_odd, mean_width, clean = _geom.polys, _geom.even_odd, _geom.mean_width, _geom.clean
closed_ring = I.closed_ring

# Physical sizes (metres), the same for every drawing (the prototype's constants, unchanged).
PAIR = (0.04, 0.45)
GLASS_PAIR = (0.005, 0.30)
RAIL_PAIR = (0.02, 0.20)
SMALL, THIN = 0.15, 0.35
CLOSE = 0.03
CUT_MARGIN = 0.15
PANE = 0.02
SINGLE_W = 0.06
THIN_FILL = 0.03
PANE_REACH = 0.10
POST_MAX = 0.25
POST_MIN = 0.002
GAP_MAX = 1.2
PLATE_CLOSE = 1.5
STAND = 0.4
SLAB_EDGE = 0.03
RISER_MAX = 0.18
TREAD = (0.19, 0.37)
END_PROBES = (0.05, 0.10, 0.20, 0.30)
REACH = 0.45
BUILD_ROLES = {'wall', 'column', 'glass', 'window', 'door', 'stair', 'stair-above', 'railing', 'room-name', 'grid'}
LOW_WALL_SILL = 0.90        # cad_test/src/find_openings.py: a window over a low wall takes the plan's default sill
OUTLINE_WALL = 0.20         # m: an accepted outline wall's thickness (the suite's added corridor walls)
OUTLINE_GLASS = 0.02        # m: an accepted outline glass's thickness (a pane)
R3 = lambda v: round(v, 3)  # noqa: E731

# The bank builder's vocabulary (U-10.3): the defaults of settings.vocabulary.
VOCAB_DEFAULTS = {
    'stairUp': r'UP|UP\.|UPSTAIRS',
    'stairDown': r'DN|DN\.|DOWN|DOWNSTAIRS',
    'roomTagLine': r'^\s*(\d+([.,]\d+)?\s*(m²|m2|sq\.?\s*m|sqm)|not enclosed|not placed|redundant room)\s*$',
    'sizeInName': r'(\d{3,4})\s*[xX×]\s*(\d{3,4})',
    'glassWord': r'(?<![A-Z])(GLASS|GLAZED|GLAZING|CURTAIN)(?![A-Z])',
    'liftWord': r'(?<![A-Z])(LIFT|ELEVATOR)(?![A-Z])',
    'typeHeight': r'(?<![\d.])(\d{3,5})\s*H(?![A-Z])',
}


class Vocab:
    """settings.vocabulary compiled (case-insensitive), a missing key = the bank's own pattern."""

    def __init__(self, vocabulary: dict | None):
        v = {**VOCAB_DEFAULTS, **{k: s for k, s in (vocabulary or {}).items() if s}}

        def rx(key):
            try:
                return re.compile(v[key], re.I)
            except re.error as e:
                from .errors import BuildError
                raise BuildError('bad_settings', f'vocabulary.{key} is not a regular expression: {e}') from e
        self.up, self.down, self.tag_line = rx('stairUp'), rx('stairDown'), rx('roomTagLine')
        self.size, self.glass, self.lift, self.type_height = rx('sizeInName'), rx('glassWord'), rx('liftWord'), rx('typeHeight')
        # a run of numbers joined by x (W x W x H): its last number is a height (U-10.3)
        self.size_run = re.compile(r'\d{3,4}(?:\s*[xX×]\s*\d{3,4}){2,}')

    def is_up(self, s: str) -> bool:
        return self.up.fullmatch(s) is not None

    def is_down(self, s: str) -> bool:
        return self.down.fullmatch(s) is not None

    def is_stair_word(self, s: str) -> bool:
        return self.is_up(s) or self.is_down(s)


# ---------------------------------------------------------------------------------------------------- small helpers
def unit(v):
    n = math.hypot(v[0], v[1])
    return (v[0] / n, v[1] / n) if n > 1e-12 else (1.0, 0.0)


def rect(a, u, s0, s1, l0, l1):
    """Rectangle in the frame of an opening (origin a, along u, across n = left of u)."""
    n = (-u[1], u[0])
    P = lambda s, l: (a[0] + u[0] * s + n[0] * l, a[1] + u[1] * s + n[1] * l)  # noqa: E731
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
    """'<family> - <type>-<element id or V#>-<view>' -> '<family> - <type>' (names.family: also drops an xref prefix)."""
    return _family(name)


def type_name(fam):
    m = re.match(r'^.*?\s_\s(.*?)(\s+-\s+[^A-Za-z0-9]*)?$', fam)
    return (m.group(1) if m else fam).strip()


def head_in_name(name, unit_m, V):
    """The height in a <width>x<height> size in a block name, in metres (1.8-3.5 m), or None; a W x W x H run also
    offers its last number (920x920x3100 -> 3.10 m, U-10.3)."""
    hs = [int(h) * unit_m for _, h in V.size.findall(name)]
    for m in V.size_run.finditer(name):
        hs.append(int(re.split(r'\s*[xX×]\s*', m.group(0))[-1]) * unit_m)
    hs = [h for h in hs if 1.8 <= h <= 3.5]
    return max(hs) if hs else None


def axis_of(g):
    cs = list(g.minimum_rotated_rectangle.exterior.coords)[:4]
    mid = lambda p, q: ((p[0] + q[0]) / 2, (p[1] + q[1]) / 2)  # noqa: E731
    if math.dist(cs[0], cs[1]) >= math.dist(cs[1], cs[2]):
        return mid(cs[0], cs[3]), mid(cs[1], cs[2]), math.dist(cs[1], cs[2])
    return mid(cs[0], cs[1]), mid(cs[3], cs[2]), math.dist(cs[0], cs[1])


def block_kids(by_h, ins):
    pre = (ins['path'] + '>' if ins['path'] else '') + ins['name']
    return [d for d in by_h[ins['h']] if d is not ins and d['depth'] > ins['depth']
            and (d['path'] == pre or d['path'].startswith(pre + '>'))]


def grid_labels(items):
    out = {}
    for d in items:
        if 'grid' in d['roles'] and 'text' in d and d['text'].strip() and len(d['text'].strip()) <= 4:
            out.setdefault(d['text'].strip(), d['ins'])
    return out


def grid_summary(items0, items, first):
    """The bank summary's `grid` field: the labels the two floors share, the median of their shifts and the spread
    (the bank's own reading, kept for the report; the shift applied comes from build/align.py, U-9.4)."""
    G0, gl = grid_labels(items0), grid_labels(items)
    common = sorted(set(gl) & set(G0))
    grid = {'labels': len(common), 'spread': 0.0, 'shift': [0.0, 0.0]}
    if not first and common:
        dx = statistics.median(G0[k][0] - gl[k][0] for k in common)
        dy = statistics.median(G0[k][1] - gl[k][1] for k in common)
        grid = {'labels': len(common), 'spread': max(math.hypot(G0[k][0] - gl[k][0] - dx, G0[k][1] - gl[k][1] - dy) for k in common),
                'shift': [R3(dx), R3(dy)]}
    return grid


# ---------------------------------------------------------------------------------------------------- reading
def read_floor(F, X):
    items = F['items']
    use = lambda d, *roles: d['cont'] and 'ignore' not in d['roles'] and bool(d['roles'] & set(roles))  # noqa: E731

    # 1. walls and columns
    fills, thin, thin_fills, col_pieces, segs, col_segs, wall_segs, arcs = [], [], [], [], [], [], [], []
    wall_src = []                                   # (key, layer) of each wall segment (the report's single-line items)
    solid_fills = 0                                 # SOLID hatches among the fills (parapets 'auto', U-10.5)
    n = collections.Counter()
    for d in items:
        if not use(d, 'wall', 'column'): continue
        is_col = 'column' in d['roles'] and 'wall' not in d['roles']
        n['col' if is_col else 'wall'] += 1
        if 'loops' in d:
            g = even_odd(d['loops'])
            if g.is_empty: continue
            fills.append(g); n['fills'] += 1
            solid_fills += bool(d.get('solid'))
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
        if is_col:
            col_segs.extend(ss)
        else:
            wall_segs.extend(ss)
            wall_src += [(d.get('k'), d['lay'])] * len(ss)
    rects, n_pairs, n_segs = strips(segs, *PAIR)
    curved = arc_walls(arcs, *PAIR)
    col_pieces += strips(col_segs, *PAIR)[0] if col_segs else []
    W = solidify(fills + thin + rects + curved, CLOSE)
    COL = unary_union(col_pieces) if col_pieces else Polygon()
    n.update(pairs=n_pairs, segs=n_segs, arcs=len(arcs), curved=len(curved))

    # outline suggestions and accepted outline edges (U-10.5, U-10.6 fix 3): added before anything is cut (none on the bank)
    add_w, add_g = X.outline(F, W) if X.outline is not None else ([], [])
    if add_w:
        W = [p for p in polys(unary_union(W + add_w)) if p.area > 0.01]

    # single-line items: wall lines that pair with nothing and lie in no wall
    cov = unary_union(W).buffer(0.02)
    singles, single_src, single_lines = [], [], []
    for (x1, y1, x2, y2), src in zip(wall_segs, wall_src):
        for part in lines_of(LineString([(x1, y1), (x2, y2)]).difference(cov)):
            if part.length > 0.2:
                singles.append(part.buffer(SINGLE_W / 2, cap_style='flat')); single_src.append(src); single_lines.append(part)
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
    Gu = unary_union(gpieces + grects + add_g)
    Gu = Gu.buffer(0.002, join_style='mitre').buffer(-0.002, join_style='mitre').difference(W_all)
    G = [p for p in polys(Gu) if p.area > 0.0005]

    # screens (U-10.5): grilles and louvres, built as glass labelled 'screen', never cut, never glazing
    scr_pieces, scr_segs = [], []
    for d in items:
        if not use(d, 'screen') or (d['roles'] & {'wall', 'column', 'glass', 'window'}): continue
        if 'loops' in d:
            g = even_odd(d['loops'])
            if not g.is_empty: scr_pieces.append(g)
            continue
        ring = closed_ring(d)
        if ring:
            g = Polygon(ring).buffer(0)
            if not g.is_empty and mean_width(g) <= THIN: scr_pieces.append(g)
            continue
        scr_segs += segs_of(d)
    SCR = []
    if scr_pieces or scr_segs:
        srects = strips(scr_segs, *GLASS_PAIR)[0] if scr_segs else []
        Su = unary_union(scr_pieces + srects).buffer(0.002, join_style='mitre').buffer(-0.002, join_style='mitre')
        Su = Su.difference(unary_union([W_all] + G))
        SCR = [p for p in polys(Su) if p.area > 0.0005]

    # door blocks (the whole-subtree reading): the size in their names gives the door head
    door_blocks = [{'ins': d['ins'], 'name': d['name'], 'head': head_in_name(d['name'], F['unit_m'], X.V)}
                   for d in F['src'] if d['t'] == 'INSERT' and 'door' in d['roles'] and 'ignore' not in d['roles']]
    F.update({'W': W, 'COL': COL, 'S': S, 'G': G, 'n': n, 'door_blocks': door_blocks, 'rects': rects, 'fills': fills,
              'thin_fills': thin_fills, 'grects': grects, 'segs': segs, 'SCR': SCR, 'solid_fills': solid_fills,
              'singles_src': (singles, single_src, single_lines)})
    revit_wall_types(F, X)
    return F


def revit_wall_types(F, X):
    """Rule 2: wall elements exported as blocks; glass wall types become glass panes of their type's height."""
    src = F['src']
    by_h = collections.defaultdict(list)
    for d in src: by_h[d['h']].append(d)
    F['by_h'] = by_h
    elements = []
    if X.options['revitWallTypes'] != 'off':
        for d in src:
            if d['t'] != 'INSERT' or 'wall' not in d['roles'] or 'ignore' in d['roles']: continue
            fam = family(d['name'])
            hs = [int(v) * F['unit_m'] for v in X.V.type_height.findall(fam)]
            hs = [h for h in hs if 1.0 <= h <= 8.0]
            lines = [LineString(k['pts']) for k in block_kids(by_h, d) if k.get('pts') and len(k['pts']) >= 2]
            elements.append({'type': type_name(fam), 'glass': bool(X.V.glass.search(fam)), 'height': hs[0] if hs else None,
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
    while grew:
        grew = False
        for i, g in enumerate(thin):
            if i in owner: continue
            j = next((j for j in owner if thin[j].distance(g) <= 0.005), None)
            if j is not None: owner[i] = owner[j]; grew = True
    F['pane_owner'] = owner
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
    GWB = unary_union(bands).buffer(0.008, join_style='mitre').buffer(-0.007, join_style='mitre')
    rest = unary_union(F['W']).difference(GWB)
    posts, walls = [], []
    for p in polys(rest):
        x0, y0, x1, y1 = p.bounds
        if p.area <= 0.03 and x1 - x0 <= POST_MAX and y1 - y0 <= POST_MAX and p.distance(GWB) <= 0.005:
            if p.area < POST_MIN: continue
            hs = [g['height'] for g in glass_walls if g['band'].distance(p) <= 0.005]
            posts.append({'poly': p, 'height': max((h for h in hs if h), default=None)})
        elif p.area > 0.004:
            walls.append(p)
    F['W'], F['posts'] = walls, posts


# ---------------------------------------------------------------------------------------------------- openings
def wall_at_end(Fr, t, M, end):
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
    E = [wall_at_end(Fr, t, M, e) for e in ('a', 'b')]
    st = [e[0] for e in E if e and e[1]]
    near = [e[0] for e in E if e]
    inside = lambda p, q: p[0] >= q[0] - 0.01 and p[1] <= q[1] + 0.01  # noqa: E731
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
    if hi - lo < 0.005: lo, hi = min(x[0] for x in near), max(x[1] for x in near)
    return lo, hi


def build_openings(F, X):
    fc, top = F['cfg'], F['cfg']['wallHeight']
    DEF = X.DEF
    W0, G0u, S0 = unary_union(F['W']), unary_union(F['G']), unary_union(F['S'])
    sill0 = fc['windowSill'] if fc.get('windowSill') is not None else DEF['windowSill']
    head0 = fc['windowHead'] if fc.get('windowHead') is not None else DEF['windowHead']
    curtain_head = min(float(fc['windowHead']), top) if fc.get('windowHead') is not None else top
    recs = []
    for o in F['ops']:
        a, b = tuple(o['a']), tuple(o['b'])
        Fr = Frame(a, b)
        w, u, nrm = Fr.L, Fr.u, Fr.n
        t = max(o['wallThickness'], 0.01)
        foot = rect(a, u, 0, w, -(t / 2 + CUT_MARGIN), t / 2 + CUT_MARGIN)
        rec = {'o': o, 'a': a, 'b': b, 'u': u, 'n': nrm, 'w': w, 't': t, 'foot': foot, 'Fr': Fr,
               'span': rect(a, u, 0, w, -t / 2 - 0.02, t / 2 + 0.02)}
        if o['kind'] == 'door':
            near = [blk for blk in F['door_blocks']
                    if -0.15 <= (blk['ins'][0] - a[0]) * u[0] + (blk['ins'][1] - a[1]) * u[1] <= w + 0.15
                    and abs((blk['ins'][0] - a[0]) * nrm[0] + (blk['ins'][1] - a[1]) * nrm[1]) <= t / 2 + 0.2]
            hs = [blk['head'] for blk in near if blk['head']]
            rec['blocks'] = [blk['name'] for blk in near]
            rec['glassDoor'] = any(X.V.glass.search(family(nm)) for nm in rec['blocks'])
            rec['liftDoor'] = any(X.V.lift.search(family(nm)) for nm in rec['blocks'])
            if o.get('_head') is not None:                       # an opening fix (U-10.6): staff's head
                rec['head'], rec['headFrom'] = o['_head'], 'fix'
            elif hs:
                rec['head'], rec['headFrom'] = max(hs), 'name'
            elif fc.get('doorHead') is not None:                 # U-10.4: the floor's door head beats other doors' names
                rec['head'], rec['headFrom'] = fc['doorHead'], 'floor'
            else:
                rec['head'] = X.DEFAULT_HEAD
                rec['headFrom'] = 'most common' if X.DOMINANT else 'default'
        recs.append(rec)

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
        glazed_door = o['kind'] == 'door' and bool(o.get('eitherKind'))      # U-10.5: glazed like a window
        if o['kind'] != 'window' and not glazed_door: continue
        gz = G0u.intersection(r['foot'])
        if o['kind'] == 'window':
            r['curtain'] = gz.area > 1e-4
            # a curtain window (glass drawn in the opening) is glazed from the floor to the wall top (the bank's rule),
            # or to the floor's own window head when staff typed one (UR, V1-3: U-10.5's per-floor window defaults; the
            # house's 28 curtain windows reached 3.90 / 3.50 m with no lintel against its 3.00 / 2.60 m heads; the bank,
            # the suite and the tower set none, so their models are unchanged)
            r['sill'], r['head'] = (0.0, curtain_head) if r['curtain'] else (sill0, head0)
            if not r['curtain'] and 'low wall' in (o.get('subtype') or ''): r['sill'] = LOW_WALL_SILL
            if o.get('_sill') is not None: r['sill'] = o['_sill']
            if o.get('_head') is not None: r['head'] = o['_head']
        if o.get('glazing'):
            r['offset'] = (o['glazing'][0] + o['glazing'][1]) / 2
        elif gz.area > 1e-4:
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
    extra = []
    for r in recs:
        o, a, u, w, t = r['o'], r['a'], r['u'], r['w'], r['t']
        if o['kind'] == 'door':
            J = lintel_depth(r['Fr'], t, SOL)
            D = (-t / 2, t / 2)
            if J[0] <= D[0] + 0.01 and J[1] >= D[1] - 0.01 and (J[1] - J[0]) > (D[1] - D[0]) + 0.02: J = D
            r['depth'] = lo, hi = J
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
            if o.get('eitherKind'):                              # U-10.5: a sliding glass door gets a pane too
                off = r['offset']
                pane = rect(a, u, 0, w, off - PANE / 2, off + PANE / 2).difference(Wc.buffer(0.001))
                for p in polys(pane):
                    if p.area > 0.001: extra.append(('glass', p, 0.0, r['head'], r['head'] >= top - 0.005, o['id'] + ' pane'))
        elif o['kind'] == 'window':
            off = r['offset']
            pane = rect(a, u, 0, w, off - PANE / 2, off + PANE / 2).difference(Wc.buffer(0.001))
            for p in polys(pane):
                if p.area > 0.001 and r['head'] > r['sill'] + 0.005:     # (a sill at or over its head: no pane, no z1 <= z0)
                    extra.append(('glass', p, r['sill'], r['head'], r['head'] >= top - 0.005, o['id'] + ' pane'))
            band = rect(a, u, 0, w, -t / 2, t / 2).difference(Wc.buffer(0.001))
            if r['sill'] > 0.005:
                for p in polys(band): extra.append(('sill', p, 0.0, r['sill'], False, o['id']))
            if r['head'] < top - 0.005:
                for p in polys(band): extra.append(('lintel', p, r['head'], top, True, o['id']))
    return recs, Wc, Gc, Sc, extra, GWc, SCc, POc


# ---------------------------------------------------------------------------------------------------- gaps, parapets
def object_closures(F, W0, recs):
    caps = []
    for p in polys(W0):
        for ring in [p.exterior] + list(p.interiors):
            cs = list(ring.coords)
            for a, b in zip(cs, cs[1:]):
                L = math.dist(a, b)
                if not (0.05 <= L <= PAIR[1]): continue
                u = unit((b[0] - a[0], b[1] - a[1]))
                m = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
                n = (u[1], -u[0])
                if W0.contains(Point(m[0] + n[0] * 0.01, m[1] + n[1] * 0.01)): n = (-n[0], -n[1])
                if not W0.contains(Point(m[0] - n[0] * 0.05, m[1] - n[1] * 0.05)): continue
                caps.append((a, b, m, n, L))
    if not caps: return []
    ops = unary_union([r['span'].buffer(0.03) for r in recs])
    objects = []
    for d in F['src']:
        if d['t'] != 'INSERT' or (d['roles'] & BUILD_ROLES): continue
        kids = block_kids(F['by_h'], d)
        if any(k['roles'] & BUILD_ROLES for k in kids): continue
        pts = [q for k in kids for q in (k.get('pts') or [])]
        if len(pts) >= 3: objects.append((family(d['name']), MultiPoint(pts).convex_hull))
    out = []
    for i, (a, b, m, n, L) in enumerate(caps):
        for a2, b2, m2, n2, L2 in caps[i + 1:]:
            if n[0] * n2[0] + n[1] * n2[1] > -0.99: continue
            d = (m2[0] - m[0]) * n[0] + (m2[1] - m[1]) * n[1]
            lat = abs((m2[0] - m[0]) * -n[1] + (m2[1] - m[1]) * n[0])
            if not (0.05 < d <= GAP_MAX) or lat > 0.06 or abs(L - L2) > 0.06: continue
            gap = MultiPoint([a, b, a2, b2]).convex_hull
            if gap.area < 1e-4 or gap.intersection(W0).area > 0.2 * gap.area or gap.intersects(ops): continue
            side = (-n[1], n[0])
            for name, hull in objects:
                if hull.intersection(gap).area < 0.5 * gap.area: continue
                ls = [(x - m[0]) * side[0] + (y - m[1]) * side[1] for x, y in hull.exterior.coords]
                if min(ls) < -L / 2 - 0.05 and max(ls) > L / 2 + 0.05:
                    out.append({'poly': gap, 'object': name, 'width': R3(d)})
                    break
    return out


def parapets_of(walls, fills, rails):
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
        lanes = []
        for row in sorted(rows, key=lambda r: (r[1], r[0])):
            for lane in lanes:
                ov = min(row[2], lane['s1']) - max(row[1], lane['s0'])
                if ov >= 0.6 * min(row[2] - row[1], lane['s1'] - lane['s0']):
                    lane['rows'].append(row); break
            else:
                lanes.append({'s0': row[1], 's1': row[2], 'rows': [row]})
        for lane in lanes:
            risers = []
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
                    if len(chain) >= 2:
                        last = statistics.mean(chain[-1]['o']) - statistics.mean(chain[-2]['o'])
                        if abs(step - 2 * last) <= 0.15 * last:
                            chain.append({'o': [ro - last], 's0': r['s0'], 's1': r['s1'], 'i': []}); chain.append(r); continue
                close()
                chain = [r]
            close()
    return out


def stairs_of(F, H, X):
    below = [LineString([(s[0], s[1]), (s[2], s[3])]) for s in stair_lines(F, 'stair')]
    above = [LineString([(s[0], s[1]), (s[2], s[3])]) for s in stair_lines(F, 'stair-above')]
    lines = below + above
    if not lines: return {'stairs': [], 'below': [], 'above': [], 'steps': []}
    words = [d for d in F['items'] if 'text' in d and 'ignore' not in d['roles'] and X.V.is_stair_word(d['text'].strip())]
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
            end, word = None, None
            for d in words:
                x, y = d['ins']
                wo, ws = x * n[0] + y * n[1], x * u[0] + y * u[1]
                if not (s0 - 0.3 <= ws <= s1 + 0.3): continue
                for e, dd in (('first', o[0] - wo), ('last', wo - o[-1])):
                    if -0.3 <= dd <= 0.8 and (end is None or abs(dd) < end[1]): end, word = (e, abs(dd)), d['text'].strip()
            f['dir'] = None if word is None else ('up' if X.V.is_up(word) else 'down')
            f['from'] = end[0] if end else None
            f['risers'] = len(o)
            st['flights'].append(f)
            if f['dir'] is None: continue
            seq = o if f['from'] == 'first' else o[::-1]
            for j in range(1, len(seq)):
                lo_o, hi_o = sorted((seq[j - 1], seq[j]))
                P = lambda s, oo: (u[0] * s + n[0] * oo, u[1] * s + n[1] * oo)  # noqa: E731
                poly = Polygon([P(s0, lo_o), P(s1, lo_o), P(s1, hi_o), P(s0, hi_o)])
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
    rail_items = [d for d in F['items'] if 'railing' in d['roles'] and 'ignore' not in d['roles'] and 'pts' in d]
    rsegs = [s for d in rail_items for s in segs_of(d)]
    if not rsegs: return [], 0, []
    paired = strips(rsegs, *RAIL_PAIR)[0]
    bands = [LineString([(x1, y1), (x2, y2)]).buffer(0.025, cap_style='flat') for x1, y1, x2, y2 in rsegs
             if math.hypot(x2 - x1, y2 - y1) > 0.05]
    R = unary_union(paired + bands).buffer(0.01, join_style='mitre').buffer(-0.01, join_style='mitre').difference(Wc.buffer(0.001))
    keep = [p for p in polys(R) if p.area > 0.002 and mean_width(p) <= 0.2]
    dropped_polys = [p for p in polys(R) if p.area > 0.002 and mean_width(p) > 0.2]
    return keep, len(dropped_polys), dropped_polys


def rooms_of(F, X):
    texts = [d for d in F['items'] if 'room-name' in d['roles'] and 'ignore' not in d['roles'] and d.get('text', '').strip()]
    tags = [d for d in texts if X.V.tag_line.match(d['text'])]
    out, skipped, skipped_at = [], [], []
    for d in texts:
        if d in tags: continue
        name = ' '.join(d['text'].split())
        x, y = d['ins']
        tag = min((t for t in tags if abs(t['ins'][0] - x) < 0.3 and 0 < y - t['ins'][1] < 0.35),
                  key=lambda t: y - t['ins'][1], default=None)
        letters = sum(ch.isalpha() for ch in name)
        if tag is None and (letters < 4 or X.V.is_stair_word(name)):
            skipped.append(name); skipped_at.append((name, x, y)); continue
        area = None
        if tag is not None and not re.search('[a-zA-Z]{3}', tag['text'].replace('m²', '').replace('m2', '')):
            area = ' '.join(tag['text'].split())
        out.append({'name': name, 'area': area, 'x': x, 'y': y})
    return out, skipped, skipped_at


def plates_of(E_walls, rails_edge, recs, stairs, lowest):
    E_nr = unary_union(E_walls + [r['span'] for r in recs])
    P1 = E_nr.buffer(0.05, join_style='mitre').buffer(-0.05, join_style='mitre')
    inner = unary_union([Polygon(p.exterior) for p in polys(P1) if p.area > 4]) if not P1.is_empty else Polygon()
    E = unary_union([E_nr] + rails_edge)
    C = E.buffer(PLATE_CLOSE, join_style='round').buffer(-PLATE_CLOSE, join_style='round')
    stair_area = unary_union([s['hull'] for s in stairs]) if stairs else Polygon()
    doors = unary_union([r['span'].buffer(0.05) for r in recs if r['o']['kind'] in ('door', 'passage')])
    kept, dropped = [], []
    for Xp in polys(C.difference(inner.buffer(0.01, join_style='mitre')).buffer(-0.01).buffer(0.01)):
        if Xp.area < 0.5: continue
        stand = not Xp.buffer(-STAND).is_empty
        reached = Xp.distance(doors) <= 0.05
        stair = Xp.intersection(stair_area).area >= 0.5 * Xp.area
        why = None if (stand and reached and not stair) else ('no standing room' if not stand else
                                                              'mostly stair' if stair else 'no door or passage opens onto it')
        (kept if why is None else dropped).append((Xp, why))
    plate = unary_union([inner] + [x for x, _ in kept]).buffer(0.02, join_style='mitre').buffer(-0.02, join_style='mitre')
    report = {'kept': [{'area': round(x.area, 1), 'bbox': [R3(v) for v in x.bounds]} for x, _ in kept],
              'dropped': [{'area': round(x.area, 2), 'bbox': [R3(v) for v in x.bounds], 'why': w} for x, w in dropped if x.area >= 0.5]}
    dropped_at = [(x, w) for x, w in dropped if x.area >= 0.5]
    return plate, report, dropped_at


def lift_shafts(plate, E_cells, recs):
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


# ---------------------------------------------------------------------------------------------------- build every floor
def build_floors(floors, X, log):
    """The prototype's 'build every floor' loop -> (parts_geo, built). parts_geo rows: (floor key, kind, polygon, z0,
    z1, follow, label, extra keys)."""
    parts_geo, built = [], {}
    DEF = X.DEF
    for fi, F in enumerate(floors):
        fc = F['cfg']; key, top = fc['key'], fc['wallHeight']
        H = (floors[fi + 1]['cfg']['level'] - fc['level']) if fi + 1 < len(floors) else top
        recs, Wc, Gc, Sc, extra, GWc, SCc, POc = build_openings(F, X)
        closures = []
        if X.options['objectClosures']:
            closures = object_closures(F, unary_union(F['W']).difference(unary_union(F['screens']).buffer(0.001)) if F['screens'] else unary_union(F['W']), recs)
        Wc = unary_union([Wc] + [c['poly'] for c in closures]).difference(unary_union([c['poly'] for c in closures])) if closures else Wc
        rails, rails_dropped, rails_dropped_polys = railings_of(F, unary_union([Wc] + [c['poly'] for c in closures]))
        walls = [p for p in polys(Wc) if p.area > 0.004]
        fills = unary_union(F['fills'])
        run_parapets = X.options['parapets'] != 'off' and F['solid_fills'] > 0     # U-10.5: only where walls carry solid fills
        parapets = parapets_of(walls, fills, rails) if run_parapets else []
        cols = [p for p in walls if not F['COL'].is_empty and p.intersection(F['COL']).area >= 0.9 * p.area]
        runs = [p for p in walls if not any(p is q for q in cols) and not any(p is q for q in parapets)]
        S = stairs_of(F, H, X)
        lowest = fi == 0
        E_walls = [Wc, Gc] + [x[1] for x in extra] + [g['pane'] for g in GWc] + SCc + [p['poly'] for p in POc] + \
                  [c['poly'] for c in closures]
        plate, plate_report, plate_dropped = plates_of(E_walls, rails + parapets, recs, S['stairs'], lowest)
        voids = []
        if not lowest:
            E_cells = unary_union(E_walls + [r['span'] for r in recs])
            for s in S['stairs']:
                v = s['hull'].intersection(plate).difference(unary_union([Wc, Gc]))
                if v.area > 0.5: voids.append(('stair', v))
            if X.options['liftShafts']:
                for v in lift_shafts(plate, E_cells, recs): voids.append(('lift shaft', v))
            if voids: plate = plate.difference(unary_union([v for _, v in voids]).buffer(0.001))
        plates = [Polygon(p.exterior, [h for h in p.interiors if Polygon(h).area >= 0.5]).simplify(0.02).buffer(SLAB_EDGE, join_style='mitre')
                  for p in polys(plate) if p.area > 4]
        if voids:
            plates = [x for p in plates for x in polys(p.difference(unary_union([v for _, v in voids]).buffer(0.001)))]
        plate_u = unary_union(plates) if plates else Polygon()
        rails_off = []
        if not lowest:
            rails_off = [r for r in rails if r.intersection(plate_u).area < 0.5 * r.area]
            rails = [r for r in rails if not any(r is q for q in rails_off)]
        slab_z0, slab_extra = -F['slabThickness'], {}
        if F.get('plinth'):                                  # U-9.5: the lowest floor above 0 stands on the ground
            slab_z0, slab_extra = -fc['level'], {'plinth': True}
        for p in runs: parts_geo.append((key, 'wall', p, 0.0, top, True, None, {}))
        for p in cols: parts_geo.append((key, 'column', p, 0.0, top, True, None, {}))
        for p in parapets: parts_geo.append((key, 'parapet', p, 0.0, DEF['railingHeight'], False, 'parapet', {}))
        for c in closures: parts_geo.append((key, 'wall', c['poly'], 0.0, top, True, f"closure ({c['object']})", {}))
        for p in polys(Gc):
            if p.area > 0.0005: parts_geo.append((key, 'glass', p, 0.0, top, True, None, {}))
        for g in GWc:
            for p in polys(g['pane']):
                if p.area > 0.0002: parts_geo.append((key, 'glass', p, 0.0, g['height'] or top, g['height'] is None, g['type'], {}))
        for s in SCc:
            for p in polys(s):
                if p.area > 0.0002: parts_geo.append((key, 'glass', p, 0.0, top, True, 'glass screen', {}))
        for p in F['SCR']:                                   # the screen role: never cut (U-10.5)
            parts_geo.append((key, 'glass', p, 0.0, top, True, 'screen', {}))
        for pst in POc:
            for p in polys(pst['poly']):
                if p.area > 0.0002: parts_geo.append((key, 'mullion', p, 0.0, pst['height'] or top, pst['height'] is None, 'frame post', {}))
        for kind, p, z0, z1, follow, label in extra: parts_geo.append((key, kind, p, z0, z1, follow, label, {}))
        for p in polys(Sc):
            if p.area > 0.002: parts_geo.append((key, 'single', p, 0.0, DEF['singleLineHeight'], False, None, {'_single': True}))
        for p in rails: parts_geo.append((key, 'railing', p, 0.0, DEF['railingHeight'], False, None, {}))
        for poly, z0, z1, label in S['steps']: parts_geo.append((key, 'step', poly, z0, z1, False, label, {}))
        for p in plates: parts_geo.append((key, 'slab', p, slab_z0, 0.0, False, None, slab_extra))
        rooms, skipped, skipped_at = rooms_of(F, X)
        near_floor = (lambda ls: True) if lowest else (lambda ls: plate_u.buffer(0.02).contains(ls))  # noqa: E731
        below = [list(S['lines'][i].coords[0]) + list(S['lines'][i].coords[-1]) for i in S['below'] if near_floor(S['lines'][i])]
        above = [list(S['lines'][i].coords[0]) + list(S['lines'][i].coords[-1]) for i in S['above'] if near_floor(S['lines'][i])]
        built[key] = {'recs': recs, 'rooms': rooms, 'skipped': skipped, 'skipped_at': skipped_at, 'plates': plates,
                      'rails': rails, 'rails_dropped': rails_dropped, 'rails_dropped_polys': rails_dropped_polys,
                      'rails_off': len(rails_off), 'rails_off_polys': rails_off, 'runs': runs, 'cols': cols,
                      'parapets': parapets, 'closures': closures, 'voids': voids, 'plate_report': plate_report,
                      'plate_dropped': plate_dropped, 'stairs': below, 'above': above, 'S': S, 'GWc': GWc, 'screens': SCc,
                      'posts': POc, 'stairs_all_below': len(stair_lines(F, 'stair')),
                      'stairs_all_above': len(stair_lines(F, 'stair-above'))}
        log(f"{key}: {len(runs)} wall runs, {len(cols)} columns, {len(parapets)} parapets, {len(closures)} closures, "
            f"{len(polys(Gc))} glass pieces, {len(GWc)} glass-wall panes, {len(SCc)} glass screens, {len(F['SCR'])} screens, "
            f"{len(POc)} frame posts, {len(rails)} railing pieces, {len(rooms)} room names, plate "
            f"{sum(p.area for p in plates):.1f} m2, steps {len(S['steps'])}")
    return parts_geo, built


def cat_of(d):
    r = d['roles']
    if 'ignore' in r: return 'noise'
    if r & {'wall', 'column'}: return 'wall'
    if r & {'glass', 'window', 'screen'}: return 'glass'
    if 'door' in r: return 'door'
    if r & {'stair', 'stair-above'}: return 'stair'
    if 'railing' in r: return 'railing'
    return 'noise'


def translate(g, dx, dy):
    return affinity.translate(g, dx, dy)
