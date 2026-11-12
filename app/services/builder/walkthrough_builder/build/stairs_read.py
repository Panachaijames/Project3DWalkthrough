"""Reading the stairs of a floor (docs/rooms/DESIGN.md R-7.1 - R-7.4), with options.stairs 'climb'. Owner: R2.

    find_stairs(fb, net, fixes, X) -> [contracts.StairFound]                                  pass 1, per floor

One row per stair of the floor's plan: a chain of flights with its landings, or a group of stair lines that forms no
flight (`flights: []`). The steps, in the order of the design:

  * the lines of the `stair` and `stair-above` layers, every linetype (their order is today's reader's, so a line's
    index is its index in FloorBuilt.old_stairs['lines']); groups of lines within 0.3 m of each other, three or more;
  * the walking lines with an arrowhead are found first and are no risers (R-7.4 rule 2);
  * per 2 degree band of direction: lines that are a nosing pair (0.05 m apart or less, overlapping by 60 %) or pieces
    of one line (the same offset within 1 cm, end to end within 5 cm) are ONE riser, at the middle of the pair, with
    the whole span (R-7.1 points 2 and 3); risers are 0.5 m or longer;
  * lanes by mutual overlap (60 % of both); a line that runs on past a lane (a landing's edge, a string of the next
    flight: longer than the lane / 0.6) is that lane's riser too, cut to the lane (R-7.1 points 6 and 8);
  * chains of three or more risers 0.19 - 0.37 m apart; a skipped going inserts a riser, which is counted; the first
    or the last step may be 0.45 m deep (R-7.1 point 5, R-7.2);
  * the continuation on any layer but furniture and ignore, at the going within 2 cm, covering 60 % of the lane,
    within two goings of the last riser found, repeated (R-7.1 point 4);
  * a word (UP / DN) at a flight's end gives its sense before anything is chained (R-7.3 point 1);
  * flights are chained at an L turn (end risers meeting at a corner), a straight landing or a U turn (side by side,
    their ends on one side, a landing beyond them); a flight that arrives and one that leaves never (R-7.3);
  * which end is at this floor: staff's bottom point, a word, a walking line with an arrowhead, the cut (R-7.4).

A row's `flights` are in walking order and, when `more.oriented`, from the bottom to the top. `more` is R2's working
data for stairs_build.py (the flights with their frames, the joints, what gave the direction): nobody else reads it.
With options.stairs 'lines' the rows are today's reader's groups, as the scaffold's tracer made them.
"""
from __future__ import annotations

import math
import statistics

import numpy as np
from shapely.geometry import LineString, MultiPoint, Point, Polygon
from shapely.ops import unary_union

from .bank import polys, segs_of

ANGLE = 2.0                 # degrees: one direction band (R-7.2); parallel for the continuation (R-7.1 point 4)
NOSE = 0.05                 # m: lines this close, overlapping by 60 %, are one riser (R-7.1 point 2)
SAME_LINE = 0.01            # m: pieces of one riser lie on one line within this (R-7.1 point 3) ...
PIECE_GAP = 0.05            # ... and end to end within this
OVERLAP = 0.6               # the share of overlap of a nosing pair, a lane, a continuation
MIN_RISER = 0.5             # m: a riser line is this long or longer
SHORT = 0.4                 # a riser cut short by a break line is still this share of its lane
GOING = (0.19, 0.37)        # m: the spacing of risers
END_STEP = 0.45             # m: the first or the last step of a flight may be this deep (R-7.1 point 5)
SKIP = 0.15                 # a going of twice the last one (within this share) is one skipped riser
CONT_TOL = 0.02             # m: a continuation stands at the going within this
GROUP = 0.3                 # m: lines within this of each other are one stair group
WORD_ACROSS, WORD_ALONG = 0.3, (-0.3, 0.8)      # m: where a word stands at a flight's end (R-7.4 rule 1)
CHAIN_REACH = 1.5           # x the wider flight's width: end risers this close may be chained (R-7.3 point 2)
CORNER = 0.4                # m: the end risers of an L turn meet at a corner within this
U_WELL = 0.6                # m: the two flights of a U turn stand this far apart or less
U_SHIFT = 1.2               # m: ... their ends this far apart along the going, or less
LANDING_REACH = (0.5, 3.0)  # m: a U landing's far edge is this far beyond the flights' ends
STROKE = (0.08, 0.45)       # m: the two strokes of an arrowhead
SNAP = 0.03                 # m: line ends this close meet
WALK_SHARE = 0.5            # a walking line covers this share of the flights' length (R-7.4 rule 2)
FIX_NEAR = 0.5              # m: a stair fix's point lies in the stair's outline, or this close (R-6.3; the web's reach)


# ------------------------------------------------------------------------------------------------------ small helpers
def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1]


def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1])


def _unit(v):
    n = math.hypot(v[0], v[1]) or 1.0
    return (v[0] / n, v[1] / n)


def _mid(seg):
    (x0, y0), (x1, y1) = seg
    return ((x0 + x1) / 2, (y0 + y1) / 2)


def _pt(s, o, u, n):
    return (u[0] * s + n[0] * o, u[1] * s + n[1] * o)


def _seg_len(s):
    return math.dist(s['a'], s['b'])


def stair_segments(fb) -> list:
    """The floor's stair lines, in today's reader's order (the `stair` layers, then the `stair-above` ones): a line's
    place in the list is its index in FloorBuilt.old_stairs['lines']."""
    out = []
    for role in ('stair', 'stair-above'):
        for d in fb['items']:
            if role in d['roles'] and 'ignore' not in d['roles'] and 'pts' in d:
                for s in segs_of(d, False):
                    out.append({'i': len(out), 'a': (s[0], s[1]), 'b': (s[2], s[3]), 'role': role,
                                'cont': d.get('cont', True) is not False, 'other': False})
    return out


def other_segments(fb) -> list:
    """Every other drawn line of the floor that a flight may continue on (R-7.1 point 4): any layer but furniture,
    ignore and the stair layers."""
    out = []
    for d in fb['items']:
        if 'pts' not in d or d['roles'] & {'furniture', 'ignore', 'stair', 'stair-above'}:
            continue
        for s in segs_of(d, False):
            out.append({'i': None, 'a': (s[0], s[1]), 'b': (s[2], s[3]), 'role': 'other', 'cont': d.get('cont', True) is not False,
                        'other': True})
    return out


class _Others:
    """The other layers' lines as arrays, for the continuation's search."""

    def __init__(self, segs):
        self.segs = segs
        a = np.array([s['a'] for s in segs], dtype=float).reshape(-1, 2)
        b = np.array([s['b'] for s in segs], dtype=float).reshape(-1, 2)
        self.a, self.b = a, b
        d = b - a
        self.len = np.hypot(d[:, 0], d[:, 1]) if len(segs) else np.zeros(0)
        self.d = d

    def near(self, u, n, target, s0, s1):
        """The lines parallel to u (2 degrees) that stand at offset `target` (within CONT_TOL) and overlap s0 .. s1."""
        if not len(self.segs):
            return []
        cross = np.abs(u[0] * self.d[:, 1] - u[1] * self.d[:, 0])
        oa = self.a @ np.array(n)
        ob = self.b @ np.array(n)
        sa = self.a @ np.array(u)
        sb = self.b @ np.array(u)
        lo, hi = np.minimum(sa, sb), np.maximum(sa, sb)
        m = ((cross <= math.sin(math.radians(ANGLE)) * np.maximum(self.len, 1e-9)) & (np.abs(oa - target) <= CONT_TOL + 0.01)
             & (np.abs(ob - target) <= CONT_TOL + 0.01) & (hi > s0) & (lo < s1))
        return [(self.segs[k], float((oa[k] + ob[k]) / 2), float(lo[k]), float(hi[k])) for k in np.nonzero(m)[0]]


# --------------------------------------------------------------------------------------------- walking lines (arrows)
def find_arrows(segs) -> list:
    """Walking lines with an arrowhead among the lines (R-7.4 rule 2): two strokes of 0.1 - 0.4 m meeting at the end
    of a line, both pointing back along it. -> [{ path: [tip ... tail], segs: the lines of the path and the strokes }]."""
    strokes = [s for s in segs if STROKE[0] <= _seg_len(s) <= STROKE[1]]
    out, taken = [], set()
    for k, s1 in enumerate(strokes):
        for s2 in strokes[k + 1:]:
            if id(s1) in taken or id(s2) in taken:
                continue
            tip = other1 = other2 = None
            for p, q in ((s1['a'], s1['b']), (s1['b'], s1['a'])):
                for p2, q2 in ((s2['a'], s2['b']), (s2['b'], s2['a'])):
                    if math.dist(p, p2) <= SNAP:
                        tip, other1, other2 = p, q, q2
            if tip is None:
                continue
            for sh in segs:
                if sh is s1 or sh is s2 or _seg_len(sh) < 0.3:
                    continue
                far = sh['b'] if math.dist(sh['a'], tip) <= SNAP else sh['a'] if math.dist(sh['b'], tip) <= SNAP else None
                if far is None:
                    continue
                back = _unit(_sub(far, tip))
                ok, sides = True, []
                for q in (other1, other2):
                    v = _unit(_sub(q, tip))
                    ang = math.degrees(math.acos(max(-1.0, min(1.0, _dot(v, back)))))
                    ok = ok and 10.0 <= ang <= 70.0
                    sides.append(back[0] * v[1] - back[1] * v[0])
                if not ok or sides[0] * sides[1] >= 0:
                    continue
                path, used, end, prev = [tip, far], [sh, s1, s2], far, sh
                for _ in range(40):                           # the line goes on through the segments that meet its end
                    nxt = None
                    for t in segs:
                        if any(t is q for q in used) or _seg_len(t) < 0.05:
                            continue
                        e = t['b'] if math.dist(t['a'], end) <= SNAP else t['a'] if math.dist(t['b'], end) <= SNAP else None
                        if e is None:
                            continue
                        if STROKE[0] <= _seg_len(t) <= 0.2 and abs(_dot(_unit(_sub(e, end)), _unit(_sub(path[-1], path[-2])))) < 0.5:
                            continue                          # a tick across the tail (a dot's cross), not the line
                        if nxt is None or _seg_len(t) > _seg_len(nxt[0]):
                            nxt = (t, e)
                    if nxt is None:
                        break
                    used.append(nxt[0])
                    path.append(nxt[1])
                    end, prev = nxt[1], nxt[0]
                taken.update((id(s1), id(s2)))
                out.append({'path': path, 'segs': used})
                break
    return out


# ------------------------------------------------------------------------------------------- risers, lanes and flights
def _bands(segs) -> list:
    """The lines by direction, in bands of 2 degrees -> [(u, [line])]."""
    rows = []
    for s in segs:
        dx, dy = s['b'][0] - s['a'][0], s['b'][1] - s['a'][1]
        L = math.hypot(dx, dy)
        if L < 0.03:
            continue
        rows.append((math.degrees(math.atan2(dy, dx)) % 180.0, L, s))
    rows.sort(key=lambda r: (r[0], -r[1], r[2]['a'], r[2]['b']))
    bands = []
    for r in rows:
        if bands and r[0] - bands[-1][0][0] <= ANGLE:
            bands[-1].append(r)
        else:
            bands.append([r])
    if len(bands) > 1 and bands[0][0][0] + 180.0 - bands[-1][0][0] <= ANGLE:
        bands[0] = bands.pop() + bands[0]
    out = []
    for b in bands:
        base = b[0][0]                                        # the band's direction: the median by length
        angs = sorted((((r[0] - base + 90.0) % 180.0) - 90.0, r[1]) for r in b)
        half, acc, med = sum(a[1] for a in angs) / 2, 0.0, angs[-1][0]
        for a, L in angs:
            acc += L
            if acc >= half:
                med = a
                break
        ra = math.radians(base + med)
        out.append(((math.cos(ra), math.sin(ra)), [r[2] for r in b]))
    return out


def _riser_rows(u, segs) -> list:
    """Nosing pairs and the pieces of one line joined -> the band's riser lines [{ o, s0, s1, segs }] (0.5 m or more)."""
    n = (-u[1], u[0])
    rows = []
    for s in segs:
        sa, sb = _dot(s['a'], u), _dot(s['b'], u)
        rows.append({'o': (_dot(s['a'], n) + _dot(s['b'], n)) / 2, 's0': min(sa, sb), 's1': max(sa, sb), 'seg': s})
    rows.sort(key=lambda r: (r['o'], r['s0'], r['s1']))
    root = list(range(len(rows)))

    def find(i):
        while root[i] != i:
            root[i] = root[root[i]]
            i = root[i]
        return i
    for i, a in enumerate(rows):
        for j in range(i + 1, len(rows)):
            b = rows[j]
            do = b['o'] - a['o']
            if do > NOSE:
                break
            ov = min(a['s1'], b['s1']) - max(a['s0'], b['s0'])
            if ov >= OVERLAP * min(a['s1'] - a['s0'], b['s1'] - b['s0']) or (do <= SAME_LINE and -ov <= PIECE_GAP):
                root[find(j)] = find(i)
    groups = {}
    for i, r in enumerate(rows):
        groups.setdefault(find(i), []).append(r)
    out = []
    for g in groups.values():
        s0, s1 = min(r['s0'] for r in g), max(r['s1'] for r in g)
        if s1 - s0 < MIN_RISER:
            continue
        levels = []                                           # a nosing pair's riser is where both its lines run
        for r in g:
            for lv in levels:
                if abs(lv[0]['o'] - r['o']) <= 0.004:
                    lv.append(r)
                    break
            else:
                levels.append([r])
        if len(levels) >= 2:
            cuts = sorted({v for r in g for v in (r['s0'], r['s1'])})
            both = [(a, b) for a, b in zip(cuts, cuts[1:])
                    if sum(1 for lv in levels if any(r['s0'] <= a + 1e-9 and r['s1'] >= b - 1e-9 for r in lv)) >= 2]
            if both and sum(b - a for a, b in both) >= MIN_RISER:
                # ... so a line that only runs on from the pair's end (a string, a landing's edge) is not the riser
                keep = [r for r in g if any(min(r['s1'], b) - max(r['s0'], a) > 0.01 for a, b in both)]
                s0, s1 = min(r['s0'] for r in keep), max(r['s1'] for r in keep)
        long = [r for r in g if r['s1'] - r['s0'] >= 0.3 * (s1 - s0)] or g
        out.append({'o': (min(r['o'] for r in long) + max(r['o'] for r in long)) / 2, 's0': s0, 's1': s1,
                    'segs': [r['seg'] for r in g], 'inserted': False, 'runon': False})
    out.sort(key=lambda r: (r['o'], r['s0']))
    return out


def _lanes(rows) -> list:
    """Lanes by mutual overlap: a riser joins the lane it overlaps by 60 % (of the shorter of the two; a break line
    shortens some risers), the usual risers first. A line that runs on past a lane (longer than the lane / 0.6) is that
    lane's riser too, cut to the lane."""
    if not rows:
        return []
    typical = statistics.median(r['s1'] - r['s0'] for r in rows)
    lanes = []
    for r in sorted(rows, key=lambda r: (round(abs(r['s1'] - r['s0'] - typical), 3), round(r['s0'], 3), r['o'])):
        L = r['s1'] - r['s0']
        best = None
        for ln in lanes:
            W = ln['s1'] - ln['s0']
            ov = min(r['s1'], ln['s1']) - max(r['s0'], ln['s0'])
            if ov >= OVERLAP * min(L, W) and SHORT * W <= L <= W / OVERLAP:
                share = ov / max(L, W)
                if best is None or share > best[0]:
                    best = (share, ln)
        if best is None:
            lanes.append({'s0': r['s0'], 's1': r['s1'], 'rows': [r]})
        else:
            ln = best[1]
            ln['rows'].append(r)
            ln['s0'] = statistics.median(q['s0'] for q in ln['rows'])
            ln['s1'] = statistics.median(q['s1'] for q in ln['rows'])
    for ln in lanes:
        W = ln['s1'] - ln['s0']
        own = list(ln['rows'])
        if len(own) < 2:
            continue
        for r in rows:
            if any(r is q for q in own) or r['s1'] - r['s0'] <= W / OVERLAP:
                continue
            if min(r['s1'], ln['s1']) - max(r['s0'], ln['s0']) >= OVERLAP * W:
                ln['rows'].append({**r, 's0': ln['s0'], 's1': ln['s1'], 'runon': True})
    return lanes


def _chains(lane) -> list:
    """The lane's risers in chains: 0.19 - 0.37 m apart, one skipped going inserted, a deeper first or last step."""
    rows = sorted(lane['rows'], key=lambda r: r['o'])
    out, chain, deep_first = [], [], False

    def close():
        if len(chain) >= 3:
            out.append(list(chain))
    for k, r in enumerate(rows):
        if chain:
            step = r['o'] - chain[-1]['o']
            if step < 0.02:
                continue
            last = chain[-1]['o'] - chain[-2]['o'] if len(chain) >= 2 else None
            if GOING[0] <= step <= GOING[1]:
                chain.append(r)
                continue
            if last is not None and GOING[0] <= last <= GOING[1] and abs(step - 2 * last) <= SKIP * last:
                a = chain[-1]
                chain.append({'o': r['o'] - last, 's0': (a['s0'] + r['s0']) / 2, 's1': (a['s1'] + r['s1']) / 2, 'segs': [],
                              'inserted': True, 'runon': False})
                chain.append(r)
                continue
            if GOING[1] < step <= END_STEP:
                nxt = rows[k + 1]['o'] - r['o'] if k + 1 < len(rows) else None
                if len(chain) == 1 and nxt is not None and GOING[0] <= nxt <= GOING[1]:
                    chain.append(r)                           # a deeper first step
                    continue
                if len(chain) >= 2 and (nxt is None or not (GOING[0] <= nxt <= END_STEP)):
                    chain.append(r)                           # a deeper last step
                    close()
                    chain = []
                    continue
            close()
        chain = [r]
    close()
    return out


def _flight(u, lane, chain) -> dict:
    n = (-u[1], u[0])
    real = [r for r in chain if not r['inserted']]
    steps = [b['o'] - a['o'] for a, b in zip(chain, chain[1:])]
    inner = [s for s in steps if GOING[0] <= s <= GOING[1]] or steps
    return {'u': u, 'n': n, 'rows': list(chain), 's0': lane['s0'], 's1': lane['s1'], 'going': statistics.median(inner),
            'width': statistics.median(r['s1'] - r['s0'] for r in real), 'sense': '', 'word': None}


def _no_flare_sides(flights) -> list:
    """Without the flights that are the side edges of another flight's flared steps: every one of their lines starts
    at the end of a riser of one other flight that runs across them (the house's bottom steps)."""
    out = []
    for f in flights:
        side = False
        for g in flights:
            if g is f or abs(_dot(f['u'], g['u'])) > 0.1 or len(g['rows']) < len(f['rows']):
                continue
            real = [r for r in f['rows'] if not r['inserted']]
            met = set()
            for r in real:                                    # each of its lines starts at the end of another riser of g
                ends = [p for s in r['segs'] for p in (s['a'], s['b'])]
                hit = next((k for k, q in enumerate(g['rows']) if k not in met and any(
                    math.dist(p, e) <= SNAP for p in ends for e in (_pt(q['s0'], q['o'], g['u'], g['n']), _pt(q['s1'], q['o'], g['u'], g['n'])))), None)
                if hit is None:
                    break
                met.add(hit)
            if len(met) == len(real):
                side = True
                break
        if not side:
            out.append(f)
    return out


def _refresh(f):
    real = [r for r in f['rows'] if not r['inserted']]
    f['width'] = statistics.median(r['s1'] - r['s0'] for r in real)


def _extend(f, group_segs, others: _Others) -> None:
    """The continuation on any layer (R-7.1 point 4): lines parallel to the flight's risers, at its going within 2 cm
    of the last riser found, covering 60 % of its lane, within two goings; one skipped going is inserted and counted.
    Repeated until nothing is added, at both ends."""
    u, n, W = f['u'], f['n'], f['s1'] - f['s0']
    used = {id(s) for r in f['rows'] for s in r['segs']}
    sin = math.sin(math.radians(ANGLE))
    for sign in (1, -1):
        for _ in range(60):
            last = f['rows'][-1] if sign > 0 else f['rows'][0]
            added = False
            for k in (1, 2):
                target = last['o'] + sign * k * f['going']
                hits = others.near(u, n, target, f['s0'], f['s1'])
                for s in group_segs:
                    if id(s) in used or _seg_len(s) < 0.05:
                        continue
                    d = _unit(_sub(s['b'], s['a']))
                    oa, ob = _dot(s['a'], n), _dot(s['b'], n)
                    if abs(u[0] * d[1] - u[1] * d[0]) > sin or abs(oa - target) > CONT_TOL + 0.01 or abs(ob - target) > CONT_TOL + 0.01:
                        continue
                    sa, sb = _dot(s['a'], u), _dot(s['b'], u)
                    if max(sa, sb) > f['s0'] and min(sa, sb) < f['s1']:
                        hits.append((s, (oa + ob) / 2, min(sa, sb), max(sa, sb)))
                if not hits:
                    continue
                cover = unary_union([LineString([(max(lo, f['s0']), 0), (min(hi, f['s1']), 0)]) for _s, _o, lo, hi in hits
                                     if min(hi, f['s1']) - max(lo, f['s0']) > 1e-6] or [LineString()]).length
                if cover < OVERLAP * W:
                    continue
                os_ = [o for _s, o, _lo, _hi in hits]
                o = (min(os_) + max(os_)) / 2
                if abs(o - target) > CONT_TOL:
                    continue
                s0, s1 = min(lo for _s, _o, lo, _hi in hits), max(hi for _s, _o, _lo, hi in hits)
                runon = s1 - s0 > W / OVERLAP
                row = {'o': o, 's0': f['s0'] if runon else s0, 's1': f['s1'] if runon else s1, 'segs': [h[0] for h in hits],
                       'inserted': False, 'runon': runon, 'continued': True}
                new = [row]
                if k == 2:
                    new.insert(0, {'o': (last['o'] + o) / 2, 's0': (last['s0'] + row['s0']) / 2, 's1': (last['s1'] + row['s1']) / 2,
                                   'segs': [], 'inserted': True, 'runon': False, 'continued': True})
                if sign > 0:
                    f['rows'] += new
                else:
                    f['rows'] = new[::-1] + f['rows']
                used.update(id(h[0]) for h in hits)
                added = True
                break
            if not added:
                break
    _refresh(f)


def _beyond(row):
    """Whether a riser is drawn beyond the cut: hidden, on a stair-above layer, or continued on another layer."""
    segs = row['segs']
    if not segs:
        return None
    far = sum(_seg_len(s) for s in segs if s['other'] or s['role'] == 'stair-above' or not s['cont'])
    return far > 0.5 * sum(_seg_len(s) for s in segs) + 1e-9


# ------------------------------------------------------------------------------------------------- ends, joints, chains
def flight_end(f, e) -> dict:
    """End e (0: the first riser by offset, 1: the last) of a flight: its riser, the middle, the way out of the flight."""
    r = f['rows'][0 if e == 0 else -1]
    u, n = f['u'], f['n']
    seg = (_pt(r['s0'], r['o'], u, n), _pt(r['s1'], r['o'], u, n))
    out = (-n[0], -n[1]) if e == 0 else n
    return {'seg': seg, 'mid': _mid(seg), 'out': out, 'row': r}


def flight_body(f) -> Polygon:
    u, n = f['u'], f['n']
    o0, o1 = f['rows'][0]['o'], f['rows'][-1]['o']
    return Polygon([_pt(f['s0'], o0, u, n), _pt(f['s1'], o0, u, n), _pt(f['s1'], o1, u, n), _pt(f['s0'], o1, u, n)])


def flight_shape(f) -> Polygon:
    """The flight's footprint with each riser's own ends."""
    u, n = f['u'], f['n']
    rows = f['rows']
    ps = [Polygon([_pt(a['s0'], a['o'], u, n), _pt(a['s1'], a['o'], u, n), _pt(b['s1'], b['o'], u, n), _pt(b['s0'], b['o'], u, n)])
          for a, b in zip(rows, rows[1:])]
    return unary_union([p.buffer(0) for p in ps if p.area > 1e-9] or [flight_body(f)])


def _rect(u, n, s0, s1, o0, o1) -> Polygon:
    return Polygon([_pt(s0, o0, u, n), _pt(s1, o0, u, n), _pt(s1, o1, u, n), _pt(s0, o1, u, n)])


def _largest(g):
    ps = polys(g) if g is not None and not g.is_empty else []
    return max(ps, key=lambda p: p.area) if ps else None


def joint(fa, ea, fb, eb, *, lines=(), flights=(), net=None):
    """The turn between end ea of flight fa and end eb of flight fb (R-7.3 point 4), or None ->
    { kind: 'L' | 'straight' | 'U', poly: the landing, drawn: landing lines or a corner say so, rank }."""
    A, B = flight_end(fa, ea), flight_end(fb, eb)
    wide = max(fa['width'], fb['width'])
    if LineString(A['seg']).distance(LineString(B['seg'])) > CHAIN_REACH * wide:
        return None
    u, n = fa['u'], fa['n']
    par = abs(_dot(u, fb['u']))
    bodies = unary_union([flight_body(fa), flight_body(fb)])
    if par < math.sin(math.radians(5.0)):                     # an L turn: the end risers meet at a corner
        corner = min(math.dist(p, q) for p in A['seg'] for q in B['seg'])
        if corner > CORNER:
            return None
        pts = list(A['seg']) + list(B['seg'])
        ss, oo = [_dot(p, u) for p in pts], [_dot(p, n) for p in pts]
        rect = _rect(u, n, min(ss), max(ss), min(oo), max(oo))
        c = (rect.centroid.x, rect.centroid.y)
        if _dot(_sub(c, A['mid']), A['out']) < 0.05 or _dot(_sub(c, B['mid']), B['out']) < 0.05:
            return None
        land = _largest(rect.difference(bodies))
        if land is None or land.area < 0.5 * rect.area:
            return None
        return {'kind': 'L', 'poly': land, 'drawn': True, 'rank': (0, corner)}
    if par < math.cos(math.radians(5.0)):
        return None
    facing = _dot(A['out'], B['out'])
    sb = sorted(_dot(p, u) for p in B['seg'])
    sa = sorted(_dot(p, u) for p in A['seg'])
    side = [s for s in lines if abs(_dot(_unit(_sub(s['b'], s['a'])), u)) < 0.1]         # lines along the going
    if facing < -0.9:                                          # a straight landing between two flights in line
        gap = _dot(_sub(B['mid'], A['mid']), A['out'])
        ov = min(fa['s1'], fb_s1(fb, u)) - max(fa['s0'], fb_s0(fb, u))
        if not (END_STEP < gap <= CHAIN_REACH * wide) or ov < OVERLAP * min(fa['width'], fb['width']):
            return None
        o0 = _dot(A['mid'], n)
        o1 = o0 + gap * (1 if _dot(A['out'], n) > 0 else -1)
        rect = _rect(u, n, min(sa[0], sb[0]), max(sa[1], sb[1]), min(o0, o1), max(o0, o1))
        zone = rect.buffer(0.06)
        drawn = sum(_seg_len(s) for s in side if zone.contains(Point(_mid((s['a'], s['b']))))) >= 0.8 * gap
        return {'kind': 'straight', 'poly': rect, 'drawn': drawn, 'rank': (1, gap)}
    if facing > 0.9:                                           # a U turn: side by side, the ends on one side
        b0, b1 = fb_s0(fb, u), fb_s1(fb, u)
        well = max(b0 - fa['s1'], fa['s0'] - b1)
        shift = _dot(_sub(B['mid'], A['mid']), A['out'])
        if well < -0.05 or well > U_WELL or abs(shift) > U_SHIFT:
            return None
        sgn = 1 if _dot(A['out'], n) > 0 else -1
        oA = _dot(A['mid'], n)
        inner, outer = oA + sgn * min(0.0, shift), oA + sgn * max(0.0, shift)
        smin, smax = min(fa['s0'], b0), max(fa['s1'], b1)
        edge, drawn, far, line = None, False, False, False
        for s in lines:                                        # the drawn landing line beyond the two ends
            if abs(_dot(_unit(_sub(s['b'], s['a'])), u)) < math.cos(math.radians(ANGLE)):
                continue
            t = ((_dot(s['a'], n) + _dot(s['b'], n)) / 2 - outer) * sgn
            lo, hi = sorted((_dot(s['a'], u), _dot(s['b'], u)))
            if LANDING_REACH[0] <= t <= LANDING_REACH[1] and min(hi, smax) - max(lo, smin) >= OVERLAP * (smax - smin):
                if edge is None or t < edge:
                    edge, drawn, line, far = t, True, True, s['role'] == 'stair-above' or not s['cont']
        if edge is None and net is not None and net.get('N') is not None and not net['N'].is_empty:
            m = _pt((smin + smax) / 2, outer + sgn * 0.05, u, n)       # the stair hall's edge: the first wall beyond
            ray = LineString([m, (m[0] + A['out'][0] * LANDING_REACH[1], m[1] + A['out'][1] * LANDING_REACH[1])])
            hit = ray.intersection(net['N'])
            if not hit.is_empty:
                t = Point(m).distance(hit) + 0.05
                if LANDING_REACH[0] <= t <= LANDING_REACH[1]:
                    edge, drawn = t, True
        if edge is None:
            edge = statistics.median([fa['width'], fb['width']])
        rect = _rect(u, n, smin, smax, min(inner, outer + sgn * edge), max(inner, outer + sgn * edge))
        land = _largest(rect.difference(bodies))
        if land is None:
            return None
        for g in flights:                                      # no other flight's steps stand in the landing
            if g is fa or g is fb:
                continue
            if land.intersection(flight_body(g)).area > 0.05:
                return None
        return {'kind': 'U', 'poly': land, 'drawn': drawn, 'rank': (2, well), 'far': far, 'line': line}
    return None


def fb_s0(f, u):
    """The low edge of a flight's lane along u (a direction parallel to its risers)."""
    return min(_dot(_pt(s, f['rows'][0]['o'], f['u'], f['n']), u) for s in (f['s0'], f['s1']))


def fb_s1(f, u):
    return max(_dot(_pt(s, f['rows'][0]['o'], f['u'], f['n']), u) for s in (f['s0'], f['s1']))


def _chain_up(flights, lines, net) -> list:
    """Flights chained into stairs (R-7.3 points 2 and 3) -> [{ flights: [(flight, reversed)], joints: [...] }]."""
    cands = []
    for i, fa in enumerate(flights):
        for j in range(i + 1, len(flights)):
            fb = flights[j]
            if fa['sense'] and fb['sense'] and fa['sense'] != fb['sense']:
                continue                                       # one arrives, one leaves: the turn is the floor itself
            known = bool(fa['sense'] and fb['sense'])
            found = []
            for ea in (0, 1):
                for eb in (0, 1):
                    J = joint(fa, ea, fb, eb, lines=lines, flights=flights, net=net)
                    if J is not None and (known or J['drawn']):
                        found.append((J, i, ea, j, eb))
            if len(found) > 1:                                 # joined at one end only: the corner or the drawn landing
                best = min(f[0]['rank'] for f in found)
                found = [f for f in found if f[0]['rank'] == best]
                drawn = [f for f in found if f[0].get('line')]
                if len(found) > 1 and drawn:                   # a drawn landing line before a wall beyond the ends
                    found = drawn
                hidden = [f for f in found if f[0].get('far')]
                if len(found) > 1 and len(hidden) == 1:        # a U with a landing at both ends: the half landing is
                    found = hidden                             # the one drawn beyond the cut
                if len(found) > 1:                             # ... or the one at the end of a flight that is beyond

                    def past(f, e):
                        rows = f['rows'] if e == 1 else f['rows'][::-1]
                        return _beyond(rows[-1]) is True and _beyond(rows[0]) is False
                    cut = [f for f in found if past(fa, f[2]) or past(fb, f[4])]
                    if len(cut) == 1:
                        found = cut
            if len(found) == 1:
                cands.append(found[0])
    cands.sort(key=lambda c: (c[0]['rank'], c[1], c[3]))
    link = {}
    comp = list(range(len(flights)))

    def root(i):
        while comp[i] != i:
            i = comp[i]
        return i
    for J, i, ea, j, eb in cands:
        if (i, ea) in link or (j, eb) in link or root(i) == root(j):
            continue
        link[(i, ea)] = (j, eb, J)
        link[(j, eb)] = (i, ea, J)
        comp[root(j)] = root(i)
    out, seen = [], set()
    for i in range(len(flights)):
        if i in seen:
            continue
        free = [e for e in (0, 1) if (i, e) not in link]
        if not free:
            continue                                           # an inner flight: reached from its chain's end
        chain, joints = [], []
        k, entry = i, free[0]
        while True:
            seen.add(k)
            chain.append((flights[k], entry == 1))
            nxt = link.get((k, 1 - entry))
            if nxt is None:
                break
            joints.append(nxt[2])
            k, entry = nxt[0], nxt[1]
        out.append({'flights': chain, 'joints': joints})
    for i in range(len(flights)):                              # a ring of flights (never seen): each on its own
        if i not in seen:
            out.append({'flights': [(flights[i], False)], 'joints': []})
    return out


def _reverse(st):
    st['flights'] = [(f, not rev) for f, rev in st['flights'][::-1]]
    st['joints'] = st['joints'][::-1]


def _rows_of(f, rev):
    return f['rows'][::-1] if rev else f['rows']


def _riser_seg(f, r):
    return (_pt(r['s0'], r['o'], f['u'], f['n']), _pt(r['s1'], r['o'], f['u'], f['n']))


def chain_ends(st):
    """The middles of the first and the last riser of a chain, in walking order."""
    f0, r0 = st['flights'][0]
    f1, r1 = st['flights'][-1]
    return _mid(_riser_seg(f0, _rows_of(f0, r0)[0])), _mid(_riser_seg(f1, _rows_of(f1, r1)[-1]))


def chain_outline(st):
    return unary_union([flight_shape(f).buffer(0.001) for f, _ in st['flights']] + [J['poly'].buffer(0.001) for J in st['joints']])


# ---------------------------------------------------------------------------------------------------------- direction
def _words(fb, X) -> list:
    """The stair words (UP / DN) of the floor, on ANY layer, an ignored one too (the owner, 12 Nov: the bank keeps its
    "UP" on G-ANNO-TEXT, which the Layers step suggests ignoring, and its main stair then had no direction). A word only
    counts where it stands at a flight's end (_give_words), so stray text elsewhere changes nothing."""
    out = []
    for d in fb['items']:
        if 'text' in d and 'ins' in d and X.V.is_stair_word(d['text'].strip()):
            out.append({'at': (d['ins'][0], d['ins'][1]), 'up': X.V.is_up(d['text'].strip())})
    return out


def _give_words(flights, words) -> None:
    """R-7.4 rule 1: a word within 0.3 m across and -0.3 .. 0.8 m along a flight's end; the nearest flight takes it."""
    cands = []
    for fi, f in enumerate(flights):
        for wi, w in enumerate(words):
            ws, wo = _dot(w['at'], f['u']), _dot(w['at'], f['n'])
            if not (f['s0'] - WORD_ACROSS <= ws <= f['s1'] + WORD_ACROSS):
                continue
            for e, dd in ((0, f['rows'][0]['o'] - wo), (1, wo - f['rows'][-1]['o'])):
                if WORD_ALONG[0] <= dd <= WORD_ALONG[1]:
                    cands.append((abs(dd), fi, wi, e))
    used_f, used_w = set(), set()
    for _dd, fi, wi, e in sorted(cands):
        if fi in used_f or wi in used_w:
            continue
        used_f.add(fi)
        used_w.add(wi)
        flights[fi]['word'] = (e, 'up' if words[wi]['up'] else 'down')
        flights[fi]['sense'] = 'leaves' if words[wi]['up'] else 'arrives'


def _direct(st, arrows, fix_bottom, lowest, breaks=()) -> None:
    """Which end of the chain is at this floor, and which is the bottom (R-7.4): sets st['by'], st['sense'],
    st['oriented'] (the flights run from the bottom to the top) and st['floorAt'] ('start' | 'end' | None)."""
    st.update(by=None, sense='', oriented=False, floorAt=None)
    a, b = chain_ends(st)
    if fix_bottom is not None:                                 # rule 5: staff's bottom point wins
        if math.dist(fix_bottom, b) < math.dist(fix_bottom, a):
            _reverse(st)
        st.update(by='staff', oriented=True)
    for f, rev in st['flights']:
        if f['word'] is None:
            continue
        e, word = f['word']
        entry = 1 if rev else 0
        if st['by'] is None:
            up = (e == entry) if word == 'up' else (e != entry)
            if not up:
                _reverse(st)
            st.update(by='word', oriented=True)
        st['sense'] = 'leaves' if word == 'up' else 'arrives'
        break
    if st['by'] is not None:
        if not st['sense'] and lowest:
            st['sense'] = 'leaves'
        st['floorAt'] = {'leaves': 'start', 'arrives': 'end'}.get(st['sense'])
        return
    outline = chain_outline(st).buffer(0.05)
    length = sum(abs(f['rows'][-1]['o'] - f['rows'][0]['o']) for f, _ in st['flights'])
    for ar in arrows:                                          # rule 2: the end without the arrowhead is at this floor
        line = LineString(ar['path'][::-1])                    # from the tail to the tip
        if line.intersection(outline).length < WALK_SHARE * length:
            continue
        ta, tb = line.project(Point(a)), line.project(Point(b))
        if abs(ta - tb) < 0.3 * line.length:
            continue
        st.update(by='arrow', floorAt='start' if ta < tb else 'end')
        break
    if st['by'] is None:                                       # rule 3: the end drawn below the cut is at this floor
        rows = [r for f, rev in st['flights'] for r in _rows_of(f, rev) if _beyond(r) is not None]
        if rows and _beyond(rows[0]) != _beyond(rows[-1]):
            st.update(by='cut', floorAt='end' if _beyond(rows[0]) else 'start')
    if st['by'] is None and len(st['flights']) >= 2 and breaks:
        # ... or the flight a zig-zag break line crosses starts at this floor, when it is the chain's first or last
        cut = [any(flight_body(f).buffer(-0.05).intersects(ls) for ls in breaks) for f, _ in st['flights']]
        if cut[0] != cut[-1] and not any(cut[1:-1]):
            st.update(by='cut', floorAt='start' if cut[0] else 'end')
    if st['by'] is not None and lowest:                        # a stair on the lowest floor leaves it
        st['sense'] = 'leaves'
        if st['floorAt'] == 'end':
            _reverse(st)
        st.update(oriented=True, floorAt='start')


# -------------------------------------------------------------------------------------------------------- the floor
def _old_rows(fb) -> list:
    """options.stairs 'lines': today's reader's groups as rows (the scaffold's tracer, kept)."""
    S = fb['old_stairs']
    out = []
    for k, st in enumerate(S.get('stairs') or [], 1):
        flights = []
        for f in st['flights']:
            u, nrm, (s0, s1) = f['u'], f['n'], f['s']
            o = list(f['o'])
            sense = {'up': 'leaves', 'down': 'arrives'}.get(f['dir'], '')
            if (f['dir'] == 'up' and f['from'] == 'last') or (f['dir'] == 'down' and f['from'] == 'first'):
                o = o[::-1]
            risers = [(_pt(s0, oo, u, nrm), _pt(s1, oo, u, nrm)) for oo in o]
            steps = [abs(b - a) for a, b in zip(o, o[1:])]
            flights.append({'risers': risers, 'going': round(statistics.median(steps), 4) if steps else 0.0,
                            'width': round(s1 - s0, 4), 'sense': sense, 'lines': list(f['lines'])})
        hull = st['hull']
        out.append({'id': f'{fb["key"]}-ST{k}', 'floor': fb['key'], 'flights': flights, 'landings': [], 'outline': hull,
                    'hull': hull, 'floorEnd': None, 'lines': list(st['lines']), 'more': None})
    return out


def _fix_of(fixes, key, outline, shift):
    """The stair fix of this floor whose point lies in the outline (or 0.5 m from it) -> (index, fix) or (None, None)."""
    zone = outline.buffer(FIX_NEAR)
    for k, fx in enumerate((fixes or {}).get('stairs') or []):
        if fx.get('floor') != key or fx.get('at') is None:
            continue
        if zone.contains(Point(fx['at'][0] + shift[0], fx['at'][1] + shift[1])):
            return k, fx
    return None, None


def find_stairs(fb, net, fixes, X) -> list:
    """-> [contracts.StairFound] of one floor (pass 1), ids `<floor key>-ST<n>` from the west (then the south)."""
    if X.options.get('stairs') != 'climb':
        return _old_rows(fb)
    segs = stair_segments(fb)
    if not segs:
        return []
    shift = tuple(((getattr(X, 'floor_info', None) or {}).get(fb['key']) or {}).get('shift') or (0.0, 0.0))
    lines = [LineString([s['a'], s['b']]) for s in segs]
    blob = unary_union([ls.buffer(GROUP) for ls in lines])
    groups = []
    for g in polys(blob):
        mem = [s for s, ls in zip(segs, lines) if g.contains(ls.interpolate(0.5, normalized=True))]
        if len(mem) >= 3:
            hull = MultiPoint([p for s in mem for p in (s['a'], s['b'])]).convex_hull
            groups.append((mem, hull))
    groups.sort(key=lambda g: (round(g[1].bounds[0], 2), round(g[1].bounds[1], 2), round(g[1].bounds[2], 2)))
    other = other_segments(fb)
    others = _Others(other)
    words = _words(fb, X)
    out = []
    for gi, (mem, hull) in enumerate(groups):
        zone = hull.buffer(0.6)
        minx, miny, maxx, maxy = zone.bounds
        near = [s for s in other if minx <= s['a'][0] <= maxx and miny <= s['a'][1] <= maxy
                and minx <= s['b'][0] <= maxx and miny <= s['b'][1] <= maxy]
        arrows = find_arrows(mem + near)
        arrow_segs = {id(s) for ar in arrows for s in ar['segs']}
        usable = [s for s in mem if id(s) not in arrow_segs]
        flights = []
        for u, band in _bands(usable):
            for lane in _lanes(_riser_rows(u, band)):
                for chain in _chains(lane):
                    flights.append(_flight(u, lane, chain))
        flights = _no_flare_sides(flights)
        for f in flights:
            _extend(f, usable, others)
        flights.sort(key=lambda f: (round(flight_end(f, 0)['mid'][0], 2), round(flight_end(f, 0)['mid'][1], 2)))
        _give_words(flights, words)
        riser_segs = {id(s) for f in flights for r in f['rows'] for s in r['segs']}
        loose = [s for s in usable if id(s) not in riser_segs]
        chains = _chain_up(flights, loose, net) if flights else []
        breaks = []                                            # zig-zag break lines: oblique to every flight
        for s in loose:
            d = _unit(_sub(s['b'], s['a']))
            if _seg_len(s) >= 0.15 and flights and all(0.3 < abs(_dot(d, f['u'])) < 0.95 for f in flights):
                breaks.append(LineString([s['a'], s['b']]))
        if not chains:
            out.append({'floor': fb['key'], 'flights': [], 'landings': [], 'outline': hull, 'hull': hull, 'floorEnd': None,
                        'lines': [s['i'] for s in mem],
                        'more': {'group': gi, 'groupHull': hull, 'chain': None, 'fix': _fix_of(fixes, fb['key'], hull, shift)}})
            continue
        for st in chains:
            outline = chain_outline(st)
            k, fx = _fix_of(fixes, fb['key'], outline, shift)
            bottom = None
            if fx is not None and fx.get('bottom') is not None:
                bottom = (fx['bottom'][0] + shift[0], fx['bottom'][1] + shift[1])
            _direct(st, arrows, bottom, fb['lowest'], breaks)
            outline = chain_outline(st)
            a, b = chain_ends(st)
            zone2 = outline.buffer(0.06)
            used = sorted({s['i'] for s in mem if zone2.contains(Point(_mid((s['a'], s['b']))))}
                          | {s['i'] for f, _ in st['flights'] for r in f['rows'] for s in r['segs'] if s['i'] is not None})
            fl = []
            for f, rev in st['flights']:
                rows = _rows_of(f, rev)
                fl.append({'risers': [_riser_seg(f, r) for r in rows], 'going': round(f['going'], 4), 'width': round(f['width'], 4),
                           'sense': f['sense'] or st['sense'], 'lines': sorted({s['i'] for r in rows for s in r['segs'] if s['i'] is not None}),
                           'inserted': [bool(r['inserted']) for r in rows], 'beyond': [_beyond(r) for r in rows]})
            kinds = [J['kind'] for J in st['joints']]
            out.append({'floor': fb['key'], 'flights': fl, 'landings': [J['poly'] for J in st['joints']], 'outline': outline,
                        'hull': outline.convex_hull, 'floorEnd': {'start': a, 'end': b}.get(st['floorAt']), 'lines': used,
                        'more': {'group': gi, 'groupHull': hull, 'chain': st, 'fix': (k, fx), 'by': st['by'], 'sense': st['sense'],
                                 'oriented': st['oriented'], 'floorAt': st['floorAt'],
                                 'kind': 'straight' if not kinds else kinds[0] if len(set(kinds)) == 1 else 'other'}})
    for k, row in enumerate(out, 1):
        row['id'] = f'{fb["key"]}-ST{k}'
    return [{'id': r['id'], **{k: v for k, v in r.items() if k != 'id'}} for r in out]
