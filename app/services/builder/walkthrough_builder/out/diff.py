"""diff.json: this build against the previous build run of the draft and against the latest version (docs/upload/DESIGN.md
U-12.4; upload-contracts.ts BuildDiff).

Both sides are compared in SHEET coordinates (model + offset + the floor's sheetShift), so a version in another frame (a
seeded project's, whose offset came from a frozen centre) still matches part for part. Parts are matched by (floor, kind,
outline and holes rounded to 1 cm), then, for what is left, by the same floor, kind and point count with every point within
1.1 cm (a value on a rounding boundary may round either way in two frames); openings by (floor, kind, centre within 0.1 m),
the nearest first, and a matched opening whose width, head, sill, subtype, lintel or wall thickness differs is listed as
changed; furniture by kind counts; rooms by name. Outlines in the diff are in the floor's sheet metres. `counts[floor]`
gives [before, after] for each part kind, each opening kind, `furniture` and `rooms` that either side has.

The rooms milestone (docs/rooms/DESIGN.md R-3.4, R-6.4): when either side is a BuiltModel v2 (it has `stairways`),
`counts[floor]` also gives, when either side has any, `rooms closed` (its `spaces`), `plate area (m2)` (the slabs with
their holes, and the holes cut on purpose added back: the floor's `voids` records, so a stair well, a shaft, a marked
void or a "no floor" room is no lost floor; to 0.1 m2; contract-issues/R3.md D-3, put in by RI) and `stairs you can
climb` (the stairways rising from the floor); names are compared as before. A floor whose plate is LOST_FLOOR m2 or more
smaller comes first in `counts`, its plate row first, so the first row of the list of changes is the lost floor (R-6.4;
the web app's DiffPanel judges the same row the same way). Two v1 models give the same bytes as before.
"""
from __future__ import annotations

import json
import math
from collections import Counter
from pathlib import Path
from typing import Any

PART_ND = 2                    # 1 cm
PART_TOL = 0.011               # m: the second pass
OPENING_TOL = 0.1              # m: centres
OPENING_FIELDS = ('width', 'head', 'sill', 'subtype', 'lintel', 'lintelTop', 'wallThickness')
NUM_TOL = 0.0005
#: m2: a floor whose plate shrinks by this much or more is a lost floor (R-6.4)
LOST_FLOOR = 2.0
#: the v2 rows of counts[floor] (R-3.4)
ROOMS_CLOSED, PLATE_AREA, CLIMBABLE = 'rooms closed', 'plate area (m2)', 'stairs you can climb'


def plate_area(model: dict, floor: str, holes_back: bool = False) -> float:
    """The area of a floor's slabs with their holes (m2, to 0.1); 0.0 without slabs. With `holes_back`, the holes cut on
    purpose are added back (`_holes_back`: the floor's `voids` records, i.e. stair wells, kept stair voids, shafts, marked
    voids, "no floor"): the floor at its outline, what the diff's `plate area (m2)` row shows and a lost floor is judged
    by (R3.md D-3, decided 11 Nov)."""
    from shapely.geometry import Polygon
    from shapely.ops import unary_union
    polys = []
    for p in model['parts']:
        if p['floor'] != floor or p['kind'] != 'slab':
            continue
        try:
            g = Polygon(p['o'], p.get('h') or [])
        except (ValueError, TypeError):
            continue
        g = g if g.is_valid else g.buffer(0)
        if not g.is_empty:
            polys.append(g)
    if not polys:
        return 0.0
    plate = unary_union(polys)
    area = _holes_back(plate, (model.get('voids') or {}).get(floor) or []) if holes_back else plate.area
    return round(area, 1) + 0.0


def _holes_back(plate, voids: list) -> float:
    """The area of `plate` with every hole that holds a void record's point filled, plus the recorded area of each void
    whose point lies in no hole (a void at the plate's edge is a notch, not a hole). Two voids in one hole (a stair well
    inside a marked void) are counted once; a hole that holds no void's point (floor that is not there) stays a hole."""
    from shapely.geometry import Point, Polygon
    from shapely.ops import unary_union
    pts = [Point(v['x'], v['y']) for v in voids]
    used: set[int] = set()
    filled = []
    for p in getattr(plate, 'geoms', [plate]):
        keep = []
        for ring in p.interiors:
            h = Polygon(ring)
            inside = [i for i, q in enumerate(pts) if h.contains(q)]
            used.update(inside)
            if not inside:
                keep.append(ring)
        filled.append(Polygon(p.exterior, keep))
    return unary_union(filled).area + sum(float(v.get('area') or 0.0) for i, v in enumerate(voids) if i not in used)


def _rooms_counts(after: dict, before: dict, floors: list[str], counts: dict) -> dict:
    """counts with the v2 rows added, and a lost floor first (R-3.4, R-6.4)."""
    for fl in floors:
        c = counts[fl]
        for key, of in ((ROOMS_CLOSED, lambda m: sum(1 for s in m.get('spaces') or [] if s['floor'] == fl)),     # noqa: B023
                        (PLATE_AREA, lambda m: plate_area(m, fl, holes_back=True)),                            # noqa: B023
                        (CLIMBABLE, lambda m: sum(1 for s in m.get('stairways') or [] if s['from'] == fl))):  # noqa: B023
            pair = [of(before), of(after)]
            if any(pair):
                c[key] = pair
    lost = [fl for fl in floors if PLATE_AREA in counts[fl] and counts[fl][PLATE_AREA][0] - counts[fl][PLATE_AREA][1] >= LOST_FLOOR - 1e-9]
    if not lost:
        return counts
    out = {fl: {PLATE_AREA: counts[fl][PLATE_AREA], **{k: v for k, v in counts[fl].items() if k != PLATE_AREA}} for fl in lost}
    out.update({fl: counts[fl] for fl in floors if fl not in lost})
    return out


def to_sheet(model: dict) -> dict[str, tuple[float, float]]:
    """floor -> (dx, dy) with sheet = model + (dx, dy) = model + offset + sheetShift."""
    ox, oy = model['offset']
    out = {}
    for f in model['floors']:
        sx, sy = f.get('sheetShift') or (0.0, 0.0)
        out[f['key']] = (ox + sx, oy + sy)
    return out


def _r(v: float, nd: int = 4) -> float:
    return round(v, nd) + 0.0


def _parts(model: dict) -> list[dict]:
    t = to_sheet(model)
    out = []
    for p in model['parts']:
        dx, dy = t.get(p['floor'], (0.0, 0.0))
        o = [[x + dx, y + dy] for x, y in p['o']]
        h = [[[x + dx, y + dy] for x, y in hole] for hole in p.get('h') or []]
        key = (p['floor'], p['kind'], tuple((_r(x, PART_ND), _r(y, PART_ND)) for x, y in o),
               tuple(tuple((_r(x, PART_ND), _r(y, PART_ND)) for x, y in hole) for hole in h))
        out.append({'floor': p['floor'], 'kind': p['kind'], 'o': o, 'h': h, 'key': key})
    return out


def _close(a: dict, b: dict) -> bool:
    if a['floor'] != b['floor'] or a['kind'] != b['kind'] or len(a['o']) != len(b['o']) or len(a['h']) != len(b['h']):
        return False
    pairs = list(zip(a['o'], b['o'])) + [pq for ha, hb in zip(a['h'], b['h']) if len(ha) == len(hb) for pq in zip(ha, hb)]
    if any(len(ha) != len(hb) for ha, hb in zip(a['h'], b['h'])):
        return False
    return all(abs(p[0] - q[0]) <= PART_TOL and abs(p[1] - q[1]) <= PART_TOL for p, q in pairs)


def _match_parts(before: list[dict], after: list[dict]) -> tuple[list[dict], list[dict]]:
    """-> (added, removed) after the exact pass and the tolerance pass."""
    left_b = Counter(p['key'] for p in before)
    added = []
    for p in after:
        if left_b[p['key']] > 0:
            left_b[p['key']] -= 1
        else:
            added.append(p)
    left_a = Counter(p['key'] for p in after)
    removed = []
    for p in before:
        if left_a[p['key']] > 0:
            left_a[p['key']] -= 1
        else:
            removed.append(p)
    still_added = []
    for p in added:
        q = next((q for q in removed if _close(p, q)), None)
        if q is None:
            still_added.append(p)
        else:
            removed.remove(q)
    return still_added, removed


def _openings(model: dict) -> list[dict]:
    t = to_sheet(model)
    out = []
    for o in model['openings']:
        dx, dy = t.get(o['floor'], (0.0, 0.0))
        cx, cy = o['x'] + dx, o['y'] + dy
        ux, uy = o.get('ny', 0.0), -o.get('nx', 0.0)
        h = (o.get('width') or 0.0) / 2
        out.append({'o': o, 'c': (cx, cy), 'a': [_r(cx - ux * h), _r(cy - uy * h)], 'b': [_r(cx + ux * h), _r(cy + uy * h)]})
    return out


def _differs(a: Any, b: Any) -> bool:
    if isinstance(a, (int, float)) and isinstance(b, (int, float)) and not isinstance(a, bool) and not isinstance(b, bool):
        return abs(a - b) > NUM_TOL
    return a != b


def diff(after: dict, before: dict) -> dict:
    """DiffBody of `after` (this build's model) against `before` (the previous run's or the version's model)."""
    pa, pb = _parts(after), _parts(before)
    added, removed = _match_parts(pb, pa)
    oa, ob = _openings(after), _openings(before)
    pairs = []
    for i, x in enumerate(oa):
        for j, y in enumerate(ob):
            if x['o']['floor'] == y['o']['floor'] and x['o']['kind'] == y['o']['kind']:
                d = math.dist(x['c'], y['c'])
                if d <= OPENING_TOL:
                    pairs.append((d, i, j))
    used_a, used_b, matched = set(), set(), []
    for d, i, j in sorted(pairs):
        if i in used_a or j in used_b:
            continue
        used_a.add(i)
        used_b.add(j)
        matched.append((oa[i], ob[j]))
    changed = []
    for x, y in matched:
        for f in OPENING_FIELDS:
            if f in x['o'] or f in y['o']:
                if _differs(y['o'].get(f), x['o'].get(f)):
                    changed.append({'floor': x['o']['floor'], 'id': x['o']['id'], 'field': f, 'before': y['o'].get(f),
                                    'after': x['o'].get(f)})
    op = lambda e: {'floor': e['o']['floor'], 'id': e['o']['id'], 'kind': e['o']['kind'], 'a': e['a'], 'b': e['b']}  # noqa: E731
    floors = list(dict.fromkeys([f['key'] for f in after['floors']] + [f['key'] for f in before['floors']]))
    counts: dict[str, dict[str, list[int]]] = {}
    for fl in floors:
        c: dict[str, list[int]] = {}

        def add(key: str, side: int, n: int = 1) -> None:
            c.setdefault(key, [0, 0])[side] += n

        for side, m in ((0, before), (1, after)):
            for p in m['parts']:
                if p['floor'] == fl:
                    add(p['kind'], side)
            for o in m['openings']:
                if o['floor'] == fl:
                    add(o['kind'], side)
            n_f = sum(1 for f in m.get('furniture') or [] if f['floor'] == fl)
            n_r = sum(1 for r in m['rooms'] if r['floor'] == fl)
            if n_f:
                add('furniture', side, n_f)
            if n_r:
                add('rooms', side, n_r)
        counts[fl] = c
    if 'stairways' in after or 'stairways' in before:          # a BuiltModel v2 on either side (R-12.1)
        counts = _rooms_counts(after, before, floors, counts)
    kinds = list(dict.fromkeys([f['kind'] for f in after.get('furniture') or []] + [f['kind'] for f in before.get('furniture') or []]))
    fb = Counter(f['kind'] for f in before.get('furniture') or [])
    fa = Counter(f['kind'] for f in after.get('furniture') or [])
    rb = Counter((r['floor'], r['name']) for r in before['rooms'])
    ra = Counter((r['floor'], r['name']) for r in after['rooms'])
    rnd = lambda pts: [[_r(x), _r(y)] for x, y in pts]                       # noqa: E731
    return {
        'counts': counts,
        'partsAdded': [{'floor': p['floor'], 'kind': p['kind'], 'o': rnd(p['o'])} for p in added],
        'partsRemoved': [{'floor': p['floor'], 'kind': p['kind'], 'o': rnd(p['o'])} for p in removed],
        'openingsAdded': [op(x) for i, x in enumerate(oa) if i not in used_a],
        'openingsRemoved': [op(y) for j, y in enumerate(ob) if j not in used_b],
        'openingsChanged': changed,
        'furnitureByKind': {k: [fb[k], fa[k]] for k in kinds},
        'roomsAdded': [name for (fl, name), n in (ra - rb).items() for _ in range(n)],
        'roomsRemoved': [name for (fl, name), n in (rb - ra).items() for _ in range(n)],
    }


def empty(body: dict) -> bool:
    """True when nothing differs (counts equal on both sides, nothing added, removed or changed)."""
    return (not any(body[k] for k in ('partsAdded', 'partsRemoved', 'openingsAdded', 'openingsRemoved', 'openingsChanged',
                                      'roomsAdded', 'roomsRemoved'))
            and all(a == b for fl in body['counts'].values() for a, b in fl.values())
            and all(a == b for a, b in body['furnitureByKind'].values()))


def _ref_of_run(path: Path) -> str:
    """runs/<runId>/out/model.json -> <runId>."""
    return path.parent.parent.name if path.parent.name == 'out' else path.parent.name


def _ref_of_version(path: Path) -> str:
    """versions/<n>/model.json -> v<n>."""
    return f'v{path.parent.name}' if path.parent.parent.name == 'versions' and path.parent.name.isdigit() else path.parent.name


def build_diff(model: dict, ctx: dict, log=None) -> dict:
    """BuildDiff against BuildContext.previousRunModel and .versionModel (each when present and readable)."""
    against = []
    for kind, key, ref_of in (('previous-run', 'previousRunModel', _ref_of_run), ('version', 'versionModel', _ref_of_version)):
        p = ctx.get(key)
        if not p:
            continue
        path = Path(p)
        try:
            other = json.loads(path.read_bytes().decode('utf-8'))
        except (OSError, ValueError) as exc:
            if log:
                log(f'diff: the {kind.replace("-", " ")} model could not be read ({type(exc).__name__}); left out')
            continue
        against.append({'kind': kind, 'ref': ref_of(path), 'diff': diff(model, other)})
    return {'format': 'build-diff/1', 'against': against}
