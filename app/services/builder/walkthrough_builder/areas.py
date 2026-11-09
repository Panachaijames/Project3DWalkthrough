"""Area proposals: where the separate drawings of one sheet lie (docs/upload/DESIGN.md U-7.3; port of
docs/upload/reference/areas_propose.py).

The occupied 1 m cells of every item's points (texts and INSERT anchors aside; at most 20 points an item, every
len // 20-th, as the reference samples them), grown by 2 m (cells up to two apart are neighbours), connected; the boxes
[min x, min y, max x + 1, max y + 1] of the connected groups over 25 m2 are kept, nothing more: this is the clustering
the browser runs again on the wall-role layers (U-14.3, U7's `plan/areas.ts`, which reproduces these boxes in this
order), so the two never disagree. They are starting points for the Floors step: the house's are near regions.json but
not equal (its ground plan is a 92 % box and an overlapping sliver; the settings proposal joins such pieces when it
guesses the floors, propose.py), and the suite sits in a 163 x 70 m cluster with its neighbours.

Order (`id` a1, a2 ...): reading order, top edge first, then left edge (the scaffold's fixtures and U7's order). At
most 200 proposals are written (the most items first; a hostile sheet of thousands of islands stays small).
`looks` (a guess the settings proposal uses, U-3.3): `plan` when the area holds door-size arcs (2 or more) and items on
wall-like layers (fills or wall-like line pairs); `elevation` when it holds level tags (2 or more), or long horizontal
lines dominate its long lines and it has no door arcs; else `other`. Owner: U2.
"""
from __future__ import annotations

import collections
import math
from collections.abc import Iterable

GROW = 2                  # cells (m)
MIN_AREA = 25.0           # m2
SAMPLES = 20              # points an item contributes at most
NOT_DRAWN = ('TEXT', 'MTEXT', 'ATTRIB', 'INSERT')
LONG_LINE = 3.0           # m: a long line, for the elevation guess
LIMIT = 1e9               # m: points farther out are not sheet points (hostile or broken coordinates)
MAX_AREAS = 200           # proposals written at most (the most items first)


def item_points(d: dict) -> list:
    """prims' `_pts`: the item's points (reader frame)."""
    return d.get('pts') or [q for loop in d.get('loops', []) for q in loop] or ([d['ins']] if 'ins' in d else [])


def drawn_points(d: dict) -> list:
    """areas_propose.py's points: drawn items only (texts and inserts aside)."""
    if d['t'] in NOT_DRAWN:
        return []
    return d.get('pts') or [q for loop in d.get('loops', []) for q in loop]


def sample(P: list, n: int = SAMPLES) -> list:
    return P[:: max(1, len(P) // n)]


def _ok(x: float, y: float) -> bool:
    return math.isfinite(x) and math.isfinite(y) and abs(x) < LIMIT and abs(y) < LIMIT


def area_of(b: list[float]) -> float:
    return (b[2] - b[0]) * (b[3] - b[1])


def overlap(a: list[float], b: list[float]) -> float:
    """The area two boxes share."""
    return max(0.0, min(a[2], b[2]) - max(a[0], b[0])) * max(0.0, min(a[3], b[3]) - max(a[1], b[1]))


def reading_order(boxes: list[list[float]]) -> list[int]:
    """Indices of `boxes` top edge first, then left edge (a stable sort: ties keep the order they were found in)."""
    return sorted(range(len(boxes)), key=lambda i: (-boxes[i][3], boxes[i][0]))


def clusters(items: list[dict], k: float) -> tuple[list[tuple[set, list[float]]], dict[int, tuple[int, int]]]:
    """areas_propose.py's clustering: -> ([(cells, box)] of the groups over MIN_AREA in the order they were found
    (cells in sorted order), {item index: its first sampled cell})."""
    cells: collections.Counter = collections.Counter()
    first_cell: dict[int, tuple[int, int]] = {}
    for i, d in enumerate(items):
        for x, y in sample(drawn_points(d)):
            x, y = x * k, y * k
            if not _ok(x, y):
                continue
            c = (math.floor(x), math.floor(y))
            cells[c] += 1
            first_cell.setdefault(i, c)
    seen: set[tuple[int, int]] = set()
    comps: list[tuple[set, list[float]]] = []
    for c in sorted(cells):
        if c in seen:
            continue
        stack, comp = [c], []
        seen.add(c)
        while stack:
            x, y = stack.pop()
            comp.append((x, y))
            for dx in range(-GROW, GROW + 1):
                for dy in range(-GROW, GROW + 1):
                    q = (x + dx, y + dy)
                    if q in cells and q not in seen:
                        seen.add(q)
                        stack.append(q)
        xs = [p[0] for p in comp]
        ys = [p[1] for p in comp]
        box = [float(min(xs)), float(min(ys)), float(max(xs) + 1), float(max(ys) + 1)]
        if area_of(box) > MIN_AREA:
            comps.append((set(comp), box))
    return comps, first_cell


def propose_areas(items: list[dict], k: float, *, wall_layers: Iterable[str] = (),
                  door_points: Iterable[tuple[float, float]] = (), level_points: Iterable[tuple[float, float]] = ()) -> list[dict]:
    """items: reader items (reader frame), k: reader frame -> metres; wall_layers: names of the layers that look like
    walls; door_points / level_points: sheet metres of the door-size arcs' centres and of the level tags. ->
    AreaProposal[]."""
    walls = set(wall_layers)
    comps, first_cell = clusters(items, k)
    if not comps:
        return []
    owner = {}
    for n, (comp, _box) in enumerate(comps):
        for c in comp:
            owner[c] = n
    members: list[list[int]] = [[] for _ in comps]
    for i, c in first_cell.items():
        n = owner.get(c)
        if n is not None:
            members[n].append(i)
    if len(comps) > MAX_AREAS:
        keep = sorted(sorted(range(len(comps)), key=lambda n: (-len(members[n]), n))[:MAX_AREAS])
        comps = [comps[n] for n in keep]
        members = [members[n] for n in keep]
    long_h = [0] * len(comps)
    long_all = [0] * len(comps)
    wall_items = [0] * len(comps)
    for n, idx in enumerate(members):
        for i in idx:
            d = items[i]
            if d['lay'] in walls:
                wall_items[n] += 1
            if d['t'] == 'LINE' and d.get('pts') and len(d['pts']) >= 2:
                (x0, y0), (x1, y1) = d['pts'][0], d['pts'][-1]
                dx, dy = (x1 - x0) * k, (y1 - y0) * k
                n_ = math.hypot(dx, dy)
                if n_ >= LONG_LINE:
                    long_all[n] += 1
                    if abs(dy) <= 0.01 * n_:
                        long_h[n] += 1

    def count_in(points, box):
        return sum(1 for x, y in points if box[0] <= x <= box[2] and box[1] <= y <= box[3])

    doors = [p for p in door_points if _ok(*p)]
    levels = [p for p in level_points if _ok(*p)]
    boxes = [box for _comp, box in comps]
    out = []
    for n in reading_order(boxes):
        box = boxes[n]
        arcs_in = count_in(doors, box)
        tags_in = count_in(levels, box)
        if arcs_in >= 2 and wall_items[n] > 0:
            looks = 'plan'
        elif tags_in >= 2 or (arcs_in < 2 and long_all[n] >= 5 and long_h[n] >= 0.6 * long_all[n]):
            looks = 'elevation'
        else:
            looks = 'other'
        out.append({'id': f'a{len(out) + 1}', 'bbox': box, 'items': len(members[n]), 'wallItems': wall_items[n],
                    'looks': looks})
    return out
