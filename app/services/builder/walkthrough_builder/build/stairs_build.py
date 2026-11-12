"""Building the stairs across floors (docs/rooms/DESIGN.md R-7.5, R-7.6, R-8), with options.stairs 'climb'. Owner: R2.

    build_stairs(floors, found, nets, plate0, fixes, X) -> contracts.StairsResult              pass 2, across floors

For every stair the reader found (stairs_read.py), from the lowest floor up:

  * the stairs of the next floor's plan that are the same stair are matched (footprints overlapping by 30 %, or a riser
    within 5 cm of a riser or stair line of the other) and read by the four rows of R-7.5: the top of the stair from
    below (a DOWN word, or the end at its own floor is its far end: its risers extend the stair, those within 5 cm
    merged), the same stair seen from above (every riser on a riser from below, no floor above: nothing of its own),
    another stair (tried on its own turn), or undecided (lines, flagged);
  * the riser height is the rise to the first floor above that it fits (0.14 - 0.21 m; staff's "climb it as drawn" up
    to 0.25 m) and on whose plate it arrives; the bottom stands on its own floor's plate (R-7.5, R-7.6);
  * a climbable stair gets its treads (each between two riser lines with their own ends, two risers deep, the last one
    0.05 m past riser n), its landings (0.15 m), the well of every floor it passes or reaches (the steps that need
    2.10 m of headroom, grown 0.05 m but cut at riser n on the arrival side, plus the band railings fence off), the
    headroom region of its own floor's ceiling, the clash cuts of the lower floor's parts (2 cm and 0.01 m2 or more),
    and its stairway record with a walking line whose ends stand 0.3 m clear of walls, on the plates (R-8);
  * every other row stays as lines with its reason, text and severity, and today's opening in an upper floor: the
    group's hull, or only the row's own footprint where a climbable stair arrives in its group (R-7.6, R-4.3).

`pairs`: the neighbouring floors no climbable stair joins. `fixes`: one { fix, matched } row per stair fix.
With options.stairs 'lines' every row of the reader stays as lines ("kept as lines", today's opening): the tracer's rule.
"""
from __future__ import annotations

import math
import statistics

from shapely.geometry import Point, Polygon
from shapely.ops import nearest_points, unary_union

from . import stairs_read as SR
from .bank import R3, polys
from .ceilings import ceiling_height

RISER = (0.14, 0.21)        # m: a plausible riser height (R-7.5)
CLIMB_MAX = 0.25            # m: staff's "climb it as drawn" up to this (the walker's step, R-9.2)
MISCOUNT = 0.30             # m: a riser up to this reads as steps not drawn; a higher one as no floor at the top
HEADROOM = 2.10             # m (R-8.2)
LAP = 0.05                  # m: the last tread runs this far past riser n, under the upper slab (R-8.1)
GROW = 0.05                 # m: the well's margin, except at the arrival (R-8.2)
RUN = 1.0                   # m: the walking line starts before riser 1 and ends past riser n (R-8.5)
CLEAR = 0.3                 # m: ... its ends this clear of walls
LANDING_DEPTH = 0.15        # m (R-8.1)
ON_PLATE = 0.25             # m: the bottom and the arrival stand on the plate within this (R-7.6)
NEAR = 0.05                 # m: risers of two plans this close are one riser (R-7.5)
MATCH = 0.3                 # footprints overlapping by this share are one stair (R-7.5)
CUT_KINDS = ('wall', 'column', 'glass', 'mullion', 'single', 'railing', 'parapet', 'lintel', 'sill')
CUT_AREA, CUT_DEPTH = 0.01, 0.02            # m2, m: a smaller overlap cuts nothing (R-8.3)
BAND = (0.2, 8.0)           # m2: a fenced band of this size joins the well (R-8.2)
EPS = 1e-9


def _mid(seg):
    (x0, y0), (x1, y1) = seg
    return ((x0 + x1) / 2, (y0 + y1) / 2)


def _unit(v):
    n = math.hypot(v[0], v[1]) or 1.0
    return (v[0] / n, v[1] / n)


def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1])


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1]


def _way(a, b):
    """The way from riser a to riser b: square to riser a (a flared step's middle is not the flight's middle)."""
    u = _unit(_sub(a[1], a[0]))
    n = (-u[1], u[0])
    return n if _dot(_sub(_mid(b), _mid(a)), n) >= 0 else (-n[0], -n[1])


def _thickness(X, index):
    f = X.settings['floors'][index]
    return f['slabThickness'] if f['slabThickness'] is not None else X.DEF['slabThickness']


def _shift(X, key):
    return tuple(((getattr(X, 'floor_info', None) or {}).get(key) or {}).get('shift') or (0.0, 0.0))


def _walls(fb):
    gs = [g for g in fb['e_walls'] if g is not None and not g.is_empty]
    return unary_union(gs) if gs else Polygon()


# ------------------------------------------------------------------------------------------------ a stair, in working form
def _stair(row) -> dict:
    """A reader's row as the builder works with it: flights of riser segments in walking order, the landings between
    them, and what is known of its direction."""
    more = row.get('more') or {}
    chain = more.get('chain')
    flights = []
    for k, f in enumerate(row['flights']):
        flights.append({'risers': [tuple(map(tuple, r)) for r in f['risers']],
                        'inserted': list(f.get('inserted') or [False] * len(f['risers'])),
                        'src': chain['flights'][k] if chain else None})
    senses = [f.get('sense') for f in row['flights'] if f.get('sense')]
    sense = more.get('sense') or (senses[0] if senses else '')
    lands = list(row.get('landings') or [])
    ok = len(lands) == max(0, len(flights) - 1)
    return {'row': row, 'flights': flights if ok else [], 'lands': lands if ok else [],
            'kinds': [J['kind'] for J in chain['joints']] if chain else ['L'] * len(lands),
            'oriented': bool(more.get('oriented')) if chain else bool(sense), 'sense': sense,
            'by': more.get('by') if chain else ('word' if sense else None), 'floorAt': more.get('floorAt'),
            'fix': more.get('fix') or (None, None)}


def _reversed(st) -> dict:
    fl = [{'risers': f['risers'][::-1], 'inserted': f['inserted'][::-1], 'src': (f['src'][0], not f['src'][1]) if f['src'] else None}
          for f in st['flights'][::-1]]
    return {**st, 'flights': fl, 'lands': st['lands'][::-1], 'kinds': st['kinds'][::-1],
            'floorAt': {'start': 'end', 'end': 'start'}.get(st['floorAt'])}


def _count(st) -> int:
    return sum(len(f['risers']) for f in st['flights'])


def _risers(st) -> list:
    return [r for f in st['flights'] for r in f['risers']]


def _near(a, b) -> bool:
    """Two riser lines of two plans are one line: parallel, within 5 cm, overlapping by half of the shorter."""
    ua, ub = _unit(_sub(a[1], a[0])), _unit(_sub(b[1], b[0]))
    if abs(ua[0] * ub[1] - ua[1] * ub[0]) > math.sin(math.radians(3.0)):
        return False
    n = (-ub[1], ub[0])
    if abs(_dot(_sub(_mid(a), b[0]), n)) > NEAR:
        return False
    sa = sorted(_dot(_sub(p, b[0]), ub) for p in a)
    lb = math.dist(*b)
    return min(sa[1], lb) - max(sa[0], 0.0) >= 0.5 * min(sa[1] - sa[0], lb)


def _lines(fb, row) -> list:
    L = fb['old_stairs'].get('lines') or []
    return [tuple(L[i].coords[k] for k in (0, -1)) for i in row.get('lines') or [] if i is not None and i < len(L)]


def _matched(lo, fb_lo, up, fb_up) -> bool:
    """R-7.5: the stairs of two neighbouring floors are one stair."""
    a, b = lo['outline'], up['outline']
    if a is not None and b is not None and not a.is_empty and not b.is_empty and min(a.area, b.area) > 0 \
            and a.intersection(b).area >= MATCH * min(a.area, b.area):
        return True
    ra, rb = [r for f in lo['flights'] for r in f['risers']], [r for f in up['flights'] for r in f['risers']]
    la, lb = _lines(fb_lo, lo), _lines(fb_up, up)
    return any(_near(r, q) for r in rb for q in ra + la) or any(_near(r, q) for r in ra for q in lb)


def _coincides(ust, st) -> bool:
    """Every drawn riser of the upper plan's stair lies on a riser of the stair from below."""
    below = _risers(st)
    mine = [r for f in ust['flights'] for r, ins in zip(f['risers'], f['inserted']) if not ins]
    return bool(mine) and all(any(_near(r, q) for q in below) for r in mine)


def _continue(fa, fb):
    """Flight fb (the upper plan's) goes on where flight fa (from below) stops: the same lane, the same way, risers
    shared or one going on -> (the merged flight, the risers it adds) or None."""
    if len(fa['risers']) < 2 or len(fb['risers']) < 2:
        return None
    a0, a1 = _mid(fa['risers'][0]), _mid(fa['risers'][-1])
    da, db = _unit(_sub(a1, a0)), _unit(_sub(_mid(fb['risers'][-1]), _mid(fb['risers'][0])))
    if _dot(da, db) < 0.95:
        return None
    ua = _unit(_sub(fa['risers'][-1][1], fa['risers'][-1][0]))

    def lane(f):
        lo = statistics.median(min(_dot(p, ua) for p in r) for r in f['risers'])
        hi = statistics.median(max(_dot(p, ua) for p in r) for r in f['risers'])
        return lo, hi
    (la0, la1), (lb0, lb1) = lane(fa), lane(fb)
    if min(la1, lb1) - max(la0, lb0) < 0.6 * min(la1 - la0, lb1 - lb0):
        return None
    ta = [_dot(_sub(_mid(r), a0), da) for r in fa['risers']]
    tb = [_dot(_sub(_mid(r), a0), da) for r in fb['risers']]
    shared = sum(1 for t in tb if any(abs(t - x) <= NEAR for x in ta))
    new = [(r, ins) for t, r, ins in zip(tb, fb['risers'], fb['inserted']) if t > ta[-1] + NEAR]
    if not shared:
        if not new:
            return None
        step = min(t for t in tb if t > ta[-1] + NEAR) - ta[-1]
        if not (SR.GOING[0] - 0.02 <= step <= SR.END_STEP):
            return None
    merged = {'risers': fa['risers'] + [r for r, _ in new], 'inserted': fa['inserted'] + [i for _, i in new], 'src': None}
    return merged, len(new)


def _connect(st, ust):
    """The upper plan's stair joined to the top of the stair from below -> { stair, new, turned, floorAtEnd } or None.
    Tried at the top of `st` (both its ends when its direction is not known) and at the bottom of `ust` (both ends when
    not known): the first flight of the upper stair goes on along the last flight from below, or a landing joins them."""
    found = []
    for turned in ((False,) if st['oriented'] else (False, True)):
        A = _reversed(st) if turned else st
        for flipped in ((False,) if ust['oriented'] else (False, True)):
            B = _reversed(ust) if flipped else ust
            if not A['flights'] or not B['flights']:
                continue
            fa, fb = A['flights'][-1], B['flights'][0]
            got = _continue(fa, fb)
            if got is not None:
                merged, new = got
                found.append((0, {'stair': {**A, 'flights': A['flights'][:-1] + [merged] + B['flights'][1:], 'lands': A['lands'] + B['lands'],
                                            'kinds': A['kinds'] + B['kinds'], 'oriented': True},
                                  'new': new + sum(len(f['risers']) for f in B['flights'][1:]), 'turned': turned,
                                  'floorAtEnd': B['floorAt'] == 'end'}))
                continue
            if fa['src'] is None or fb['src'] is None:
                continue
            J = SR.joint(fa['src'][0], 0 if fa['src'][1] else 1, fb['src'][0], 1 if fb['src'][1] else 0)
            if J is not None:
                found.append((1, {'stair': {**A, 'flights': A['flights'] + B['flights'], 'lands': A['lands'] + [J['poly']] + B['lands'],
                                            'kinds': A['kinds'] + [J['kind']] + B['kinds'], 'oriented': True},
                                  'new': _count(B), 'turned': turned, 'floorAtEnd': B['floorAt'] == 'end'}))
    if not found:
        return None
    best = min(f[0] for f in found)
    found = [f[1] for f in found if f[0] == best]
    return found[0] if len(found) == 1 else None


# --------------------------------------------------------------------------------------------------- what is built (R-8)
def _aligned(risers) -> list:
    """The riser segments with their ends on the same sides (so a tread's polygon does not cross itself)."""
    out = [risers[0]]
    for r in risers[1:]:
        ref = _sub(out[-1][1], out[-1][0])
        out.append(r if _dot(_sub(r[1], r[0]), ref) >= 0 else (r[1], r[0]))
    return out


def _solid(sid, st, lo, to_fb, floors, X, plate0, direction):
    """A climbable stair as R-8.1, R-8.2 and R-8.5 build it -> contracts.StairBuilt (`cuts` by clash_cuts)."""
    frm = lo['key']
    flights = [_aligned(f['risers']) for f in st['flights']]
    n = sum(len(f) for f in flights)
    rise = to_fb['level'] - lo['level']
    r = rise / n
    treads, lands, steps, walk = [], [], [], []
    j = 0

    def part(kind, poly, z0, z1, label):
        return {'floor': frm, 'kind': kind, 'poly': poly, 'z0': R3(z0), 'z1': R3(z1), 'follow': False, 'label': label,
                'extra': {'fit': 'storey', 'stair': sid}}
    for fi, risers in enumerate(flights):
        walk += [_mid(risers[0]), _mid(risers[-1])]
        for k in range(len(risers)):
            j += 1
            if k + 1 == len(risers):
                break
            (a0, a1), (b0, b1) = risers[k], risers[k + 1]
            base = Polygon([a0, a1, b1, b0])
            poly = base
            if j == n - 1:                                     # the last tread laps 0.05 m past riser n
                d = _way(risers[k + 1], risers[k])
                d = (-d[0], -d[1])
                poly = Polygon([a0, a1, (b1[0] + d[0] * LAP, b1[1] + d[1] * LAP), (b0[0] + d[0] * LAP, b0[1] + d[1] * LAP)])
            z0, z1 = max(0.0, (j - 2) * r), j * r
            treads.append(part('tread', poly, z0, z1, f'stair {sid} tread {j}'))
            steps.append((base, z0, z1, fi))
        if fi < len(st['lands']):
            L = st['lands'][fi]
            z1 = j * r
            z0 = max(0.0, z1 - LANDING_DEPTH)
            lands.append(part('landing', L, z0, z1, f'stair {sid} landing {j}'))
            steps.append((L, z0, z1, -1 - fi))
            c = L.centroid
            walk.append((c.x, c.y))
    first, last = flights[0], flights[-1]
    d1 = _way(first[0], first[1])
    dn = _way(last[-1], last[-2])
    dn = (-dn[0], -dn[1])

    def clear(p0, d, sign, fb):
        """The walking line's end: 1.0 m from the riser, moved toward the stair until it stands on the plate, 0.3 m
        clear of walls."""
        plate, walls = plate0[fb['key']], _walls(fb)
        t = RUN
        while t > CLEAR + EPS:
            p = Point(p0[0] + sign * d[0] * t, p0[1] + sign * d[1] * t)
            if plate.contains(p) and (walls.is_empty or walls.distance(p) >= CLEAR - 1e-6):
                break
            t -= 0.05
        t = max(t, CLEAR)
        end = (p0[0] + sign * d[0] * t, p0[1] + sign * d[1] * t)
        if t > CLEAR + EPS or plate.is_empty or plate.contains(Point(end)):
            return end
        # no spot 0.3 - 1.0 m from the riser stands on the plate (a stair that starts just inside a door, RR BRK-5):
        # never a point off the plate: the point 0.1 m from the riser (the one the ON_PLATE test looked at), or the
        # plate's nearest point to it, a little inside
        near = Point(p0[0] + sign * d[0] * 0.1, p0[1] + sign * d[1] * 0.1)
        if plate.contains(near):
            return (near.x, near.y)
        inner = plate.buffer(-0.05)
        q = nearest_points(inner if not inner.is_empty else plate, near)[0]
        return (q.x, q.y)
    bottom = clear(_mid(first[0]), d1, -1, lo)
    top = clear(_mid(last[-1]), dn, 1, to_fb)
    walk = [bottom] + walk + [top]
    (p0, p1) = last[-1]
    t = _unit(_sub(p1, p0))
    e = GROW + 0.01
    beyond = Polygon([(p0[0] - t[0] * e, p0[1] - t[1] * e), (p1[0] + t[0] * e, p1[1] + t[1] * e),
                      (p1[0] + t[0] * e + dn[0], p1[1] + t[1] * e + dn[1]), (p0[0] - t[0] * e + dn[0], p0[1] - t[1] * e + dn[1])])
    wells = {}
    for fb in floors[lo['index'] + 1: to_fb['index'] + 1]:     # every floor it passes, and the one it reaches
        need = (fb['level'] - lo['level']) - _thickness(X, fb['index']) - HEADROOM
        high = [b for b, _z0, z1, _g in steps if z1 > need + EPS]
        if not high:
            continue
        well = unary_union(high).buffer(GROW, join_style='mitre')
        wells[fb['key']] = well.difference(beyond) if fb is to_fb else well
    head = [b for b, _z0, z1, _g in steps if z1 > ceiling_height(lo['index'], X) - HEADROOM + EPS]
    goings = [math.dist(_mid(a), _mid(b)) for f in flights for a, b in zip(f, f[1:])]
    width = min(statistics.median([math.dist(a, b) for a, b in f]) for f in flights)
    kinds = set(st['kinds'])
    stairway = {'id': sid, 'from': frm, 'to': to_fb['key'], 'kind': 'straight' if not kinds else kinds.pop() if len(kinds) == 1 else 'other',
                'risers': n, 'riser': R3(r), 'going': R3(statistics.median(goings)), 'width': R3(width), 'bottom': bottom,
                'top': top, 'walk': walk, 'direction': direction, 'treads': len(treads), 'landings': len(lands)}
    return {'stairway': stairway, 'treads': treads, 'landings': lands, 'wellOf': wells,
            'headroom': unary_union(head) if head else None, 'arrival': top, 'cuts': clash_cuts(lo, steps), 'linesUsed': {},
            '_outline': unary_union([p['poly'] for p in treads + lands])}


def clash_cuts(fb, steps) -> list:
    """R-8.3: the parts of the lower floor in the way of the stair -> [contracts.StairCut]. steps: [(footprint, z0, z1,
    which flight or landing)] of the treads (without the lap) and landings. A part is cut where steps whose underside
    is lower than its top overlap it by 0.01 m2 and 2 cm in depth or more; the piece under one flight (or one landing)
    gets the lowest underside over it."""
    cuts = []
    groups = sorted({g for _b, _z0, _z1, g in steps}, key=lambda g: (g < 0, abs(g)))
    for i, p in enumerate(fb['parts']):
        if p['kind'] not in CUT_KINDS:
            continue
        for g in groups:
            over = [(b, z0) for b, z0, _z1, gg in steps if gg == g and z0 < p['z1'] - EPS and b.intersection(p['poly']).area > 1e-6]
            if not over:
                continue
            foot = p['poly'].intersection(unary_union([b for b, _ in over]))
            if foot.area < CUT_AREA or foot.buffer(-CUT_DEPTH / 2).is_empty:
                continue
            cuts.append({'floor': fb['key'], 'part': i, 'footprint': foot, 'z1': min(z0 for _b, z0 in over)})
    return cuts


def _lines_used(fb, outline, rows) -> list:
    """The stair lines of a floor that became the stair (R-8.4): those in its footprint, and its rows' own."""
    zone = outline.buffer(0.06)
    L = fb['old_stairs'].get('lines') or []
    used = {i for i, ls in enumerate(L) if zone.contains(ls.interpolate(0.5, normalized=True))}
    for row in rows:
        used.update(i for f in row['flights'] for i in f.get('lines') or [] if i is not None)
    return sorted(used)


# ----------------------------------------------------------------------------------------------------------- the texts
def _where(row, X) -> str:
    s = _shift(X, row['floor'])
    at = (row['outline'] if row['outline'] is not None and not row['outline'].is_empty else row['hull']).representative_point()
    return f'Stair at ({at.x - s[0]:.1f}, {at.y - s[1]:.1f})'


def _tracer_left(st, why, text, severity, fb, plate0):
    """options.stairs 'lines': a group that stays as lines, with today's opening over it on an upper floor."""
    void = None
    if not fb['lowest']:
        walls = unary_union([g for g in fb['e_walls'][:2] if g is not None and not g.is_empty])
        v = st['hull'].intersection(plate0[fb['key']]).difference(walls)
        void = v if v.area > 0.5 else None
    at = st['hull'].representative_point()
    return {'id': st['id'], 'floor': st['floor'], 'why': why, 'text': text, 'severity': severity, 'at': (at.x, at.y),
            'outline': st['outline'], 'keptVoid': void, 'risers': sum(len(f['risers']) for f in st['flights'])}


# ------------------------------------------------------------------------------------------------------------ the pass
def build_stairs(floors, found, nets, plate0, fixes, X):
    """-> contracts.StairsResult (pass 2, across floors). floors: [FloorBuilt]; found: {floor key: [StairFound]};
    nets: {floor key: NetworkResult}; plate0: {floor key: geometry}."""
    stair_fixes = (fixes or {}).get('stairs') or []
    if X.options.get('stairs') != 'climb':
        def at_hull(st):                                       # in the floor's own sheet frame, as _where (RR CODE-6)
            s, at = _shift(X, st['floor']), st['hull'].representative_point()
            return f'Stair at ({at.x - s[0]:.1f}, {at.y - s[1]:.1f})'
        left = [_tracer_left(st, 'kept as lines', f'{at_hull(st)}: kept as lines.', 'info', fb, plate0)
                for fb in floors for st in found.get(fb['key']) or []]
        return {'built': [], 'left': left, 'pairs': [], 'fixes': [{'fix': k, 'matched': False} for k, _ in enumerate(stair_fixes)]}
    built, left, taken, matched_fix = [], [], {}, set()
    arriving = set()                                           # (floor key, group): a climbable stair arrives there
    pending = []                                               # 'the riser does not fit' rows: their text is finished last

    def keep(row, why, text, severity, risers=None, fit=None):
        rec = {'id': row['id'], 'floor': row['floor'], 'why': why, 'text': text, 'severity': severity, 'at': None,
               'outline': row['outline'] if row['outline'] is not None and not row['outline'].is_empty else row['hull'],
               'keptVoid': None, 'risers': sum(len(f['risers']) for f in row['flights']) if risers is None else risers, '_row': row}
        at = rec['outline'].representative_point()
        rec['at'] = (at.x, at.y)
        left.append(rec)
        if fit is not None:
            pending.append((rec, fit))
        return rec

    for i, lo in enumerate(floors):
        key = lo['key']
        up = floors[i + 1] if i + 1 < len(floors) else None
        for row in found.get(key) or []:
            if row['id'] in taken:
                continue
            st = _stair(row)
            fk, fx = st['fix']
            if fk is not None:
                matched_fix.add(fk)
            use = (fx or {}).get('use') or 'auto'
            where = _where(row, X)
            ups = [u for u in (found.get(up['key']) or []) if u['id'] not in taken and _matched(row, lo, u, up)] if up is not None else []
            parts, same, undecided = [], [], []
            direction = st['by']
            if st['flights'] and st['sense'] != 'arrives':
                order = sorted(ups, key=lambda u: 0 if _stair(u)['sense'] == 'arrives' else 1)
                for u in order:
                    ust = _stair(u)
                    if not ust['flights']:
                        continue
                    c = _connect(st, ust)
                    if c is not None and (ust['sense'] == 'arrives' or c['floorAtEnd']):
                        if not st['oriented'] and direction is None:
                            direction = 'floors'               # R-7.4 rule 4: the other floor gives the direction
                        st = {**c['stair'], 'row': row, 'fix': st['fix'], 'sense': 'leaves', 'by': direction, 'floorAt': 'start'}
                        parts.append(u)
                    elif ust['sense'] == 'arrives':
                        undecided.append((u, None))
                    elif _coincides(ust, st) and i + 2 >= len(floors):
                        same.append(u)
                    else:
                        n0 = _count(st)
                        r0 = (up['level'] - lo['level']) / n0 if n0 else 0.0
                        complete = RISER[0] - EPS <= r0 <= RISER[1] + EPS
                        if complete and (ust['sense'] == 'leaves' or not _coincides(ust, st) or i + 2 < len(floors)):
                            continue                           # another stair, leaving the upper floor: on its own turn
                        undecided.append((u, c))
            n = _count(st)

            def also(why, text, severity, risers=None, fit=None):
                """The upper plan's drawings of this stair stay as lines with it (today's opening stays over it)."""
                for u in parts + same + [x[0] for x in undecided]:
                    taken[u['id']] = row['id']
                    keep(u, why, text.replace(where, _where(u, X), 1), severity, risers, fit)

            def lines(why, text, severity, risers=None, fit=None):
                keep(row, why, text, severity, risers, fit)
                also(why, text, severity, risers, fit)

            if use == 'lines':
                lines('kept by staff', f'{where}: kept as lines.', 'info')
                continue
            if not st['flights']:
                lines('turning or curved steps', f'{where}: turning or curved steps: not built yet.', 'info')
                continue
            if st['sense'] == 'arrives':                       # the top of a stair no plan below shows
                if i == 0:
                    lines('it leaves the top floor', f'{where}: it leads to a floor that is not in the model.', 'info')
                else:
                    lines('the floors do not line up', f"{where}: its two floors' drawings do not line up. Line the floors up "
                          'with two points on the Floors step.', 'check')
                continue
            if up is None:
                lines('it leaves the top floor', f'{where}: it leads to a floor that is not in the model.', 'info')
                continue
            # the direction (R-7.4): the reader's, the other floor's, or: a stair that is not the top of one from below
            # leaves its floor
            if not st['oriented'] and st['floorAt'] is not None:
                if st['floorAt'] == 'end':
                    st = _reversed(st)
                st = {**st, 'oriented': True, 'sense': 'leaves', 'floorAt': 'start'}
            # the count the two plans give together, for the riser check's words (R-7.5)
            count = n
            for _u, c in undecided:
                if c is not None:
                    count = max(count, _count(c['stair']))
            # which floor it rises to (R-7.5): the first above whose rise fits and on whose plate it arrives
            target, off = None, None
            cands = [up] if parts else floors[i + 1:]
            for fb in cands:
                r = (fb['level'] - lo['level']) / count
                fits = RISER[0] - EPS <= r <= RISER[1] + EPS or (use == 'climb' and fb is up and r <= CLIMB_MAX + EPS)
                if not fits:
                    continue
                if st['oriented'] and count == n:
                    last = st['flights'][-1]['risers']
                    dn = _way(last[-1], last[-2])
                    dn = (-dn[0], -dn[1])
                    m = _mid(last[-1])
                    if not plate0[fb['key']].buffer(ON_PLATE).contains(Point(m[0] + dn[0] * 0.1, m[1] + dn[1] * 0.1)):
                        off = off or 'top'
                        continue
                target = fb
                break
            if target is None and off is None:
                rise = up['level'] - lo['level']
                r = rise / count
                if use == 'climb' and r > CLIMB_MAX + EPS:   # staff's choice cannot be followed: say so (RR BRK-4)
                    lines('the riser does not fit', f'{where}: "Climb it as drawn" is not possible: each step would be '
                          f'{r:.3f} m (the limit is {CLIMB_MAX:.2f} m). {count} steps for {rise:.2f} m: the drawing may not '
                          'show every step, or the levels may be off.', 'check', count, (i, count))
                elif RISER[1] < r <= MISCOUNT or r < RISER[0]:
                    lines('the riser does not fit', f'{where}: {count} steps for {rise:.2f} m give {r:.3f} m each. The drawing '
                          'may not show every step, or the levels may be off.', 'check', count, (i, count))
                else:
                    lines('no floor at its top', f'{where}: its {count} steps would rise about {count * RISER[0]:.1f}–'
                          f'{count * RISER[1]:.1f} m: no floor of the model is at that height.', 'info', count)
                continue
            if not st['oriented'] or count != n:
                lines('no direction', f'{where}: kept as lines: which end is the bottom was not found.', 'check', count)
                continue
            first = st['flights'][0]['risers']
            d1 = _way(first[0], first[1])
            m = _mid(first[0])
            if target is None or not plate0[key].buffer(ON_PLATE).contains(Point(m[0] - d1[0] * 0.1, m[1] - d1[1] * 0.1)):
                which = 'top' if target is None else 'bottom'
                lines('off the plate', f'{where}: its {which} does not stand on a floor plate.', 'check', count)
                continue
            sid = f'S{len(built) + 1}'
            sb = _solid(sid, st, lo, target, floors, X, plate0, direction or 'floors')
            outline = sb.pop('_outline')
            sb['linesUsed'] = {key: _lines_used(lo, outline, [row])}
            if target is up:
                sb['linesUsed'][up['key']] = _lines_used(up, outline, parts + same)
            else:
                sb['linesUsed'][target['key']] = _lines_used(target, outline, [])
            sb['_groups'] = []
            for u in parts + same:
                taken[u['id']] = row['id']
                g = (u.get('more') or {}).get('group')
                arriving.add((up['key'], g))
                sb['_groups'].append((u.get('more') or {}).get('groupHull') or u['hull'])
            for u, _c in undecided:                            # R-7.5, the last row: this one stays as lines, flagged
                taken[u['id']] = row['id']
                arriving.add((up['key'], (u.get('more') or {}).get('group')))
                keep(u, 'no direction', f'{_where(u, X)}: kept as lines: which end is the bottom was not found.', 'check')
            built.append(sb)

    # 'the riser does not fit': the storeys that would fit every stair between the two floors (R-7.6)
    for rec, (i, count) in pending:
        lo_w, hi_w = count * RISER[0], count * RISER[1]
        every = True
        for sb in built:
            sw = sb['stairway']
            if sw['from'] == floors[i]['key'] and i + 1 < len(floors) and sw['to'] == floors[i + 1]['key']:
                lo_w, hi_w = max(lo_w, sw['risers'] * RISER[0]), min(hi_w, sw['risers'] * RISER[1])
        if lo_w > hi_w:
            lo_w, hi_w, every = count * RISER[0], count * RISER[1], False
        rec['text'] += (f' A storey of {lo_w:.2f}–{hi_w:.2f} m would fit '
                        + ('every stair between these floors.' if every else 'this stair.'))

    # today's opening over a stair that stays as lines (R-4.3): the group's hull, once; only the row's own footprint
    # where a climbable stair arrives in its group
    by_key = {fb['key']: fb for fb in floors}
    given = set()
    for rec in left:
        row = rec.pop('_row')
        fb = by_key[rec['floor']]
        if fb['lowest']:
            continue
        more = row.get('more') or {}
        g = (rec['floor'], more.get('group'))
        if g in arriving and row['flights']:
            shape = row['outline']
        elif g in given and more.get('group') is not None:
            continue
        else:
            shape = more.get('groupHull') or row['hull']
            given.add(g)
        walls = unary_union([w for w in fb['e_walls'][:2] if w is not None and not w.is_empty] or [Polygon()])
        v = shape.intersection(plate0[rec['floor']]).difference(walls)
        rec['keptVoid'] = v if v.area > 0.5 else None

    # the fenced band (R-8.2): what railings fence off beside the well, inside the upper plan's stair group
    from .slabs import arrival_of
    for sb in built:
        hulls = sb.pop('_groups')
        to = sb['stairway']['to']
        fb = by_key[to]
        well = sb['wellOf'].get(to)
        rails = [r for r in fb['rails'] if r is not None and not r.is_empty]
        if not hulls or well is None or well.is_empty or not rails:
            continue
        fence = unary_union(rails).buffer(0.06)
        patch = arrival_of(sb)
        taken_out = [well.buffer(0.01), _walls(fb)] + ([patch] if patch is not None else []) \
            + [rec['keptVoid'] for rec in left if rec['floor'] == to and rec['keptVoid'] is not None]
        region = unary_union(hulls).intersection(plate0[to]).difference(unary_union(taken_out)).difference(fence.buffer(-0.04))
        add = []
        for p in polys(region):
            if not (BAND[0] <= p.area <= BAND[1]) or p.distance(well) > 0.1:
                continue
            if p.exterior.intersection(fence).length >= max(1.0, 0.25 * p.exterior.length):
                add.append(p.buffer(0.03, join_style='mitre'))
        if add:
            grown = unary_union([well] + add)
            sb['wellOf'][to] = grown.difference(patch) if patch is not None else grown

    # the neighbouring floors no climbable stair joins; a stair that passes a floor (a split level) joins those it passes
    spans = [(by_key[sb['stairway']['from']]['index'], by_key[sb['stairway']['to']]['index']) for sb in built]
    pairs = [{'from': a['key'], 'to': b['key']} for a, b in zip(floors, floors[1:])
             if not any(lo <= a['index'] and b['index'] <= hi for lo, hi in spans)]
    rows = [{'fix': k, 'matched': k in matched_fix} for k, _ in enumerate(stair_fixes)]
    return {'built': built, 'left': left, 'pairs': pairs, 'fixes': rows}
