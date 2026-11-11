"""Building the stairs across floors (docs/rooms/DESIGN.md R-7.5, R-7.6, R-8), with options.stairs 'climb'. Owner: R2.

THE TRACER of the rooms scaffold R0 (see stairs_read.py): one straight flight with a word. A stair group is built
climbable when it is one flight that leaves its floor (an UP word at its bottom), there is a floor above, and the rise
to that floor divided by its riser lines gives 0.14 - 0.21 m; every other group stays as lines with its reason. R2
replaces the body; the signature is contracts.py's and stays.

What the tracer builds for a climbable stair (R-8.1, R-8.2, R-8.5):
  * treads 1 .. n-1 between riser lines j and j + 1, top j x r, two risers deep, the last one 0.05 m past riser n; all
    on the lower floor, `follow: false`, `fit: 'storey'`, `stair: <id>`;
  * the well in the upper floor: the treads whose top is higher than rise - slab thickness - 2.10 m, grown 0.05 m at
    the sides and at its low end, its edge at the arrival on riser n;
  * the headroom region for the lower floor's ceiling: the treads whose top is higher than ceiling height - 2.10 m;
  * the stairway record with a four-point walking line (1.0 m before riser 1, its middle, riser n's middle, 1.0 m
    past it).
Not yet (R2's): matching one stair across two floors' drawings, landings and turns, the fenced band, the arrival
patch, clash cuts of the parts under a flight, a walking line moved clear of walls, the stair fixes.
"""
from __future__ import annotations

import math

from shapely.geometry import Polygon
from shapely.ops import unary_union

from .bank import R3
from .ceilings import ceiling_height

RISER = (0.14, 0.21)        # m: a plausible riser height (R-7.6)
HEADROOM = 2.10             # m (R-8.2)
LAP = 0.05                  # m: the last tread runs this far past riser n, under the upper slab (R-8.1)
GROW = 0.05                 # m: the well's margin, except at the arrival (R-8.2)
RUN = 1.0                   # m: the walking line starts before riser 1 and ends past riser n (R-8.5)


def _mid(seg):
    (x0, y0), (x1, y1) = seg
    return ((x0 + x1) / 2, (y0 + y1) / 2)


def _left(st, why, text, severity, fb, plate0):
    """A stair group that stays as lines (contracts.StairLeft), with today's opening over it on an upper floor."""
    void = None
    if not fb['lowest']:
        walls = unary_union([g for g in fb['e_walls'][:2] if g is not None and not g.is_empty])
        v = st['hull'].intersection(plate0[fb['key']]).difference(walls)
        void = v if v.area > 0.5 else None
    at = st['hull'].representative_point()
    return {'id': st['id'], 'floor': st['floor'], 'why': why, 'text': text, 'severity': severity, 'at': (at.x, at.y),
            'outline': st['outline'], 'keptVoid': void, 'risers': sum(len(f['risers']) for f in st['flights'])}


def _thickness(X, index):
    f = X.settings['floors'][index]
    return f['slabThickness'] if f['slabThickness'] is not None else X.DEF['slabThickness']


def build_stairs(floors, found, nets, plate0, fixes, X):
    """-> contracts.StairsResult (pass 2, across floors). floors: [FloorBuilt]; found: {floor key: [StairFound]};
    nets: {floor key: NetworkResult}; plate0: {floor key: geometry}."""
    built, left = [], []
    climb = X.options['stairs'] == 'climb'
    for i, fb in enumerate(floors):
        up = floors[i + 1] if i + 1 < len(floors) else None
        for st in found.get(fb['key']) or []:
            where = f'Stair at ({st["hull"].representative_point().x:.1f}, {st["hull"].representative_point().y:.1f})'
            if not climb:
                left.append(_left(st, 'kept as lines', f'{where}: kept as lines.', 'info', fb, plate0))
                continue
            fl = st['flights']
            if len(fl) != 1:
                left.append(_left(st, 'turning or curved steps', f'{where}: turning or curved steps: not built yet.',
                                  'info', fb, plate0))
                continue
            f = fl[0]
            if f['sense'] == 'arrives':
                continue                                  # the upper plan's drawing of a stair from below: no stair of its own
            if f['sense'] != 'leaves':
                left.append(_left(st, 'no direction', f'{where}: kept as lines: which end is the bottom was not found.',
                                  'check', fb, plate0))
                continue
            if up is None:
                left.append(_left(st, 'it leaves the top floor', f'{where}: it leads to a floor that is not in the model.',
                                  'info', fb, plate0))
                continue
            n = len(f['risers'])
            rise = up['level'] - fb['level']
            r = rise / n
            if not (RISER[0] <= r <= RISER[1]):
                left.append(_left(st, 'the riser does not fit', f'{where}: {n} steps for {rise:.2f} m give {r:.2f} m each. '
                                  f'The drawing may not show every step, or the levels may be off.', 'check', fb, plate0))
                continue
            sid = f'S{len(built) + 1}'
            risers = f['risers']
            (ax, ay), (bx, by) = _mid(risers[0]), _mid(risers[-1])
            length = math.hypot(bx - ax, by - ay) or 1.0
            d = ((bx - ax) / length, (by - ay) / length)   # along the flight, bottom to top
            treads = []
            for j in range(1, n):
                a0, a1 = risers[j - 1]
                b0, b1 = risers[j]
                if j == n - 1:
                    b0, b1 = (b0[0] + d[0] * LAP, b0[1] + d[1] * LAP), (b1[0] + d[0] * LAP, b1[1] + d[1] * LAP)
                treads.append({'floor': fb['key'], 'kind': 'tread', 'poly': Polygon([a0, a1, b1, b0]),
                               'z0': R3(max(0.0, (j - 2) * r)), 'z1': R3(j * r), 'follow': False,
                               'label': f'stair {sid} tread {j}', 'extra': {'fit': 'storey', 'stair': sid}})
            # the well in the floor above: from the first tread that needs headroom up to riser n
            need = rise - _thickness(X, i + 1) - HEADROOM
            j0 = next((j for j in range(1, n) if j * r > need), n - 1)
            a0, a1 = risers[j0 - 1]
            b0, b1 = risers[-1]
            side = (-d[1], d[0])
            sgn = 1.0 if (a1[0] - a0[0]) * side[0] + (a1[1] - a0[1]) * side[1] > 0 else -1.0

            def grown(p, along, across):
                return (p[0] + d[0] * along + side[0] * across * sgn, p[1] + d[1] * along + side[1] * across * sgn)
            well = Polygon([grown(a0, -GROW, -GROW), grown(a1, -GROW, GROW), grown(b1, 0.0, GROW), grown(b0, 0.0, -GROW)])
            high = [t['poly'] for j, t in enumerate(treads, 1) if j * r > ceiling_height(i, X) - HEADROOM]
            headroom = unary_union(high).buffer(GROW, join_style='mitre') if high else None
            bottom = (ax - d[0] * RUN, ay - d[1] * RUN)
            top = (bx + d[0] * RUN, by + d[1] * RUN)
            stairway = {'id': sid, 'from': fb['key'], 'to': up['key'], 'kind': 'straight', 'risers': n, 'riser': R3(r),
                        'going': R3(f['going']), 'width': R3(f['width']), 'bottom': bottom, 'top': top,
                        'walk': [bottom, (ax, ay), (bx, by), top], 'direction': 'word', 'treads': n - 1, 'landings': 0}
            built.append({'stairway': stairway, 'treads': treads, 'landings': [], 'wellOf': {up['key']: well},
                          'headroom': headroom, 'arrival': top, 'cuts': [], 'linesUsed': {fb['key']: list(f['lines'])}})
    pairs = []
    if climb:
        joined = {(b['stairway']['from'], b['stairway']['to']) for b in built}
        pairs = [{'from': a['key'], 'to': b['key']} for a, b in zip(floors, floors[1:]) if (a['key'], b['key']) not in joined]
    rows = [{'fix': k, 'matched': False} for k, _ in enumerate(fixes.get('stairs') or [])]     # the tracer applies none
    return {'built': built, 'left': left, 'pairs': pairs, 'fixes': rows}
