"""Grid labels and their lines: what the grid alignment pairs between floors (docs/upload/DESIGN.md U-7.3, U-9.4).

A grid label is a text matching `GRID_RE` (copied verbatim from docs/upload/reference/read_drawing.py: `1`, `A`, `A'`,
`A1`, `A.1`, `1/2`, `H2`) on a layer whose name contains GRID or AXIS (any case), or inside a block inserted on such a
layer (the bank's MTEXT in "Grid - CIRCLE" on S-GRID-IDEN; the house's `_GRID` attributes on GRID-01).
`line` = the longest grid-layer line with an end within 1.0 m of the label's insertion point, or passing within 0.3 m of
it, written from its end nearer the label to its far end; `direction` = its unit vector; both null when there is none
(the bubbles may lie outside the plan: which floor a label belongs to is decided at build time by its line, U-9.4).
Grid-layer lines: LINE items and the straight segments of open polylines on GRID / AXIS layers (circles and closed
shapes are the bubbles, never lines). Texts are untrusted: only matched and copied. Owner: U2.
"""
from __future__ import annotations

import collections
import math
import re

# verbatim from docs/upload/reference/read_drawing.py (U-7.3)
GRID_RE = re.compile(r'^[A-Z]{1,2}[\'′]?$|^\d{1,2}[\'′]?$|^[A-Z]{1,2}[.\-]?\d{1,2}$|^\d{1,2}[.\-/]\d{1,2}$')
END_REACH = 1.0          # a line ends within this of the label
PASS_REACH = 0.3         # ... or passes within this
CELL = 2.0               # the line index's cell (m)
MAX_CELLS = 4000         # cells one line is indexed in (a line longer than ~8 km is indexed by its ends only)


def is_grid_layer(name: str) -> bool:
    u = (name or '').upper()
    return 'GRID' in u or 'AXIS' in u


def is_label(text: str, layer: str, block_layers=()) -> bool:
    """A grid label: GRID_RE on the text (trimmed) and a grid layer, its own or an enclosing INSERT's."""
    return bool(GRID_RE.match((text or '').strip())) and (is_grid_layer(layer) or any(is_grid_layer(b) for b in block_layers))


def _cells_of(a, b, reach: float):
    """The CELL cells within `reach` of segment ab (sampled along it)."""
    n = math.dist(a, b)
    steps = max(1, math.ceil(n / (CELL / 2)))
    if steps > MAX_CELLS:
        pts = (a, b)
    else:
        pts = [(a[0] + (b[0] - a[0]) * i / steps, a[1] + (b[1] - a[1]) * i / steps) for i in range(steps + 1)]
    out = set()
    r = math.ceil(reach / CELL)
    for x, y in pts:
        gx, gy = math.floor(x / CELL), math.floor(y / CELL)
        for i in range(-r, r + 1):
            for j in range(-r, r + 1):
                out.add((gx + i, gy + j))
    return out


def grid_labels(texts: list[dict], lines: list[tuple]) -> list[dict]:
    """texts: [{text, x, y, layer, block, blays}] (sheet m; blays = layers of the enclosing INSERTs); lines: grid-layer
    segments ((x0, y0), (x1, y1)) in sheet m. -> GridLabel[] in the order of `texts`."""
    L = [((float(a[0]), float(a[1])), (float(b[0]), float(b[1]))) for a, b in lines
         if all(map(math.isfinite, (a[0], a[1], b[0], b[1]))) and math.dist(a, b) > 1e-6]
    index: dict[tuple[int, int], list[int]] = collections.defaultdict(list)
    for i, (a, b) in enumerate(L):
        for c in _cells_of(a, b, max(END_REACH, PASS_REACH)):
            index[c].append(i)
    out = []
    for t in texts:
        txt = (t.get('text') or '').strip()
        if not is_label(txt, t.get('layer', ''), t.get('blays', ())):
            continue
        p = (t['x'], t['y'])
        if not (math.isfinite(p[0]) and math.isfinite(p[1])):
            continue
        best = None
        for i in sorted(set(index.get((math.floor(p[0] / CELL), math.floor(p[1] / CELL)), ()))):
            a, b = L[i]
            n = math.dist(a, b)
            near_end = min(math.dist(p, a), math.dist(p, b))
            u = max(0.0, min(1.0, ((p[0] - a[0]) * (b[0] - a[0]) + (p[1] - a[1]) * (b[1] - a[1])) / n ** 2))
            off = math.dist(p, (a[0] + u * (b[0] - a[0]), a[1] + u * (b[1] - a[1])))
            if (near_end <= END_REACH or off <= PASS_REACH) and (best is None or n > best[0]):
                s, e = (a, b) if math.dist(p, a) <= math.dist(p, b) else (b, a)
                best = (n, s, e)
        line = direction = None
        if best is not None:
            n, s, e = best
            line = [[round(s[0], 3), round(s[1], 3)], [round(e[0], 3), round(e[1], 3)]]
            direction = [round((e[0] - s[0]) / n, 6) + 0.0, round((e[1] - s[1]) / n, 6) + 0.0]
        out.append({'text': txt, 'x': round(p[0], 3), 'y': round(p[1], 3), 'layer': t.get('layer', ''),
                    'block': t.get('block'), 'direction': direction, 'line': line})
    return out
