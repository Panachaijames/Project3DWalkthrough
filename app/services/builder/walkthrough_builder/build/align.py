"""Floor alignment: origin, per-gridline, two points, auto (docs/upload/DESIGN.md U-9.4).

Every floor i > 0 is moved by its shift s_i onto floor 0's frame (translation only). Methods:
  * origin: no shift;
  * grid: the source's grid labels (DrawingRead.gridLabels, sheet m) whose `line` crosses the floor's area (box + pad;
    under wholeFile every label with a line) belong to that floor; a label with no line, or whose line enters no area,
    is dropped (elevation labels). Labels of floors i and 0 are paired by the same text and the same direction family
    (within 2 degrees). Each pair gives the offset along the line's normal n . (p_i - p_0); with two families the shift
    is the least-squares solution of all of them, with one the shift along its normal only. Spread = the largest
    residual;
  * points: two point pairs picked on both sheets: the mean of the two differences; spread = how far each is from it;
  * auto: grid when at least two labels with lines are shared, else origin when floor i is in another file than floor 0,
    else the run fails (align_failed).
A shift under 0.5 mm in both axes is no shift (no transform at all), so floating-point noise never moves the bank.
"""
from __future__ import annotations

import math
from collections.abc import Mapping

from .errors import BuildError

FAMILY_DEG = 2.0            # lines within this many degrees are one direction family
NO_SHIFT = 0.0005           # m: a shift under this in both axes is none


def _unit(v):
    n = math.hypot(v[0], v[1])
    return (v[0] / n, v[1] / n) if n > 1e-12 else None


EXTEND = 10.0               # m: a label's line that crosses no area is continued this far away from its bubble


def _entry(seg, box) -> float | None:
    """Where (0..1 along seg) the segment first enters the box, or None."""
    (ax, ay), (bx, by) = seg
    x0, y0, x1, y1 = box
    t0, t1 = 0.0, 1.0
    dx, dy = bx - ax, by - ay
    for p, q in ((-dx, ax - x0), (dx, x1 - ax), (-dy, ay - y0), (dy, y1 - ay)):
        if abs(p) < 1e-15:
            if q < 0: return None
            continue
        r = q / p
        if p < 0:
            if r > t1: return None
            t0 = max(t0, r)
        else:
            if r < t0: return None
            t1 = min(t1, r)
    return t0 if t0 <= t1 else None


def assign_labels(floors: list[Mapping], labels: list[dict]) -> dict[str, list[dict]]:
    """U-9.4: which of a source's grid labels belong to which of its floors. A label needs a line; under wholeFile it
    belongs to the floor; with box areas it belongs to the floor whose area (box + pad) its line crosses (the first one
    met going from the bubble along the line). A line that crosses no area (a reader may give only the bubble's leader
    stub: the house's are 1.5 m long and end 2.7 m short of the plans) is continued away from the bubble for up to
    EXTEND m. A label whose line enters no area is dropped (elevation labels: their lines run away from the plans)."""
    out: dict[str, list[dict]] = {f['key']: [] for f in floors}
    boxes = []
    for f in floors:
        area = f['area']
        if area['kind'] == 'box':
            x0, y0, x1, y1 = (float(v) for v in area['bbox'])
            pad = float(area.get('pad', 0.0))
            boxes.append((f['key'], (x0 - pad, y0 - pad, x1 + pad, y1 + pad)))
        else:
            boxes.append((f['key'], None))
    for g in labels or []:
        ln = g.get('line')
        if not ln or len(ln) != 2:
            continue
        a, b = (float(ln[0][0]), float(ln[0][1])), (float(ln[1][0]), float(ln[1][1]))
        if 'x' in g and 'y' in g and math.dist((float(g['x']), float(g['y'])), b) < math.dist((float(g['x']), float(g['y'])), a):
            a, b = b, a                                     # a: the end at the bubble
        u = _unit((b[0] - a[0], b[1] - a[1]))
        if u is None:
            continue
        lab = {'text': str(g.get('text', '')).strip(), 'a': a, 'b': b}
        whole = next((k for k, bx in boxes if bx is None), None)
        if whole is not None:
            out[whole].append(lab)
            continue
        far = (b[0] + u[0] * EXTEND, b[1] + u[1] * EXTEND)
        best = None
        for k, bx in boxes:
            t = _entry((a, b), bx)
            d = None if t is None else t * math.dist(a, b)
            if d is None:
                t = _entry((b, far), bx)
                d = None if t is None else math.dist(a, b) + t * EXTEND
            if d is not None and (best is None or d < best[0]):
                best = (d, k)
        if best is not None:
            out[best[1]].append(lab)
    return out


def floor_labels(floor: Mapping, labels: list[dict], floors: list[Mapping] | None = None) -> list[dict]:
    """The grid labels that belong to one floor (assign_labels over the floors of its source)."""
    same = [f for f in (floors or [floor]) if f['source'] == floor['source']]
    return assign_labels(same, labels)[floor['key']]


def _angle(u) -> float:
    return math.degrees(math.atan2(u[1], u[0])) % 180.0


def _same_dir(u, v) -> bool:
    d = abs(_angle(u) - _angle(v)) % 180.0
    return min(d, 180.0 - d) <= FAMILY_DEG


def grid_shift(labels0: list[dict], labels_i: list[dict]) -> dict | None:
    """Per-gridline shift of floor i onto floor 0 -> {shift, spread, labels, families} or None when nothing is shared."""
    rows = []                   # (n, b): we want n . s = b
    used = set()
    for g0 in labels0:
        u0 = _unit((g0['b'][0] - g0['a'][0], g0['b'][1] - g0['a'][1]))
        for gi in labels_i:
            if gi['text'] != g0['text']:
                continue
            ui = _unit((gi['b'][0] - gi['a'][0], gi['b'][1] - gi['a'][1]))
            if not _same_dir(u0, ui):
                continue
            n = (-u0[1], u0[0])
            off = n[0] * (gi['a'][0] - g0['a'][0]) + n[1] * (gi['a'][1] - g0['a'][1])
            rows.append((n, -off, u0))
            used.add(g0['text'])
    if not rows:
        return None
    fams: list[tuple] = []
    for n, b, u in rows:
        if not any(_same_dir(u, f) for f in fams):
            fams.append(u)
    if len(fams) >= 2:
        a11 = sum(n[0] * n[0] for n, _, _ in rows); a12 = sum(n[0] * n[1] for n, _, _ in rows)
        a22 = sum(n[1] * n[1] for n, _, _ in rows)
        b1 = sum(n[0] * b for n, b, _ in rows); b2 = sum(n[1] * b for n, b, _ in rows)
        det = a11 * a22 - a12 * a12
        if abs(det) < 1e-12:
            fams = fams[:1]
        else:
            s = ((a22 * b1 - a12 * b2) / det, (a11 * b2 - a12 * b1) / det)
    if len(fams) == 1:
        n0 = rows[0][0]
        # one family: the shift along its normal only (each row's normal points the same way up to sign)
        vals = [b * (1 if n[0] * n0[0] + n[1] * n0[1] >= 0 else -1) for n, b, _ in rows]
        m = sum(vals) / len(vals)
        s = (n0[0] * m, n0[1] * m)
    spread = max(abs(n[0] * s[0] + n[1] * s[1] - b) for n, b, _ in rows)
    return {'shift': s, 'spread': spread, 'labels': sorted(used, key=lambda t: (len(t), t)), 'families': min(len(fams), 2)}


def _report(method, shift, spread, labels, families):
    return {'method': method, 'shift': [float(shift[0]), float(shift[1])], 'spread': spread, 'labels': labels,
            'families': families}


def _zeroed(s):
    return (0.0, 0.0) if abs(s[0]) < NO_SHIFT and abs(s[1]) < NO_SHIFT else (float(s[0]), float(s[1]))


def align(floors: list[dict], grid_labels: Mapping[str, list[dict]]) -> list[dict]:
    """floors (settings FloorSetup, in floor order) + grid labels per source sha1 -> one AlignReport per floor. The
    report's `shift` is the shift APPLIED to the floor's items ((0, 0) when under 0.5 mm). Raises BuildError
    align_failed when auto finds no method, or grid finds no shared label."""
    out = []
    if not floors:
        return out
    f0 = floors[0]
    l0 = floor_labels(f0, grid_labels.get(f0['source'], []), floors)
    out.append(_report('none', (0.0, 0.0), None, [], 0))
    for f in floors[1:]:
        al = f.get('align') or {'method': 'auto'}
        method = al.get('method', 'auto')
        if method == 'points':
            (p0, q0), (p1, q1) = al['pairs']
            d0 = (float(p0[0]) - float(q0[0]), float(p0[1]) - float(q0[1]))
            d1 = (float(p1[0]) - float(q1[0]), float(p1[1]) - float(q1[1]))
            s = ((d0[0] + d1[0]) / 2, (d0[1] + d1[1]) / 2)
            spread = max(math.dist(d0, s), math.dist(d1, s))
            out.append(_report('points', _zeroed(s), spread, [], 0))
            continue
        if method == 'origin':
            out.append(_report('origin', (0.0, 0.0), None, [], 0))
            continue
        li = floor_labels(f, grid_labels.get(f['source'], []), floors)
        g = grid_shift(l0, li)
        if method == 'grid':
            if g is None:
                raise BuildError('align_failed', f'{f["name"]} shares no grid label with {f0["name"]}: pick two points '
                                 f'or the origin', step='align')
        elif g is None or len(g['labels']) < 2:          # auto
            if f['source'] != f0['source']:
                out.append(_report('origin', (0.0, 0.0), None, [], 0))
                continue
            raise BuildError('align_failed', f'{f["name"]} and {f0["name"]} are on one sheet: pick grid or two points',
                             step='align')
        out.append(_report('grid', _zeroed(g['shift']), g['spread'], g['labels'], g['families']))
    return out
