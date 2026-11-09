"""DrawingRead (drawing.json): what the Layers and Floors steps show about one source (docs/upload/DESIGN.md U-7.3; port
of docs/upload/reference/read_drawing.py onto the reader's own walk, upload-contracts.ts section 4).

Every number is counted over the walked items (blocks unpacked, by effective layer), in sheet metres (reader frame x
`units.UNITS_K[used]`, the detector's own scaling). Rules worth stating:
* `extents`: the 1 - 99 % box of all item points (at most 20 points an item), so a header's `$EXTMAX` or a stray point
  far away never stretches it (the house's header says 13.5 km);
* layers: every layer of the layer table and every layer an item uses, by name. `items` counts the items; `byType`
  counts them by type and also lists `DIMENSION` (dimensions are not items, but a layer holding only dimensions is
  told by it, U-8.3); `pairs` = parallel LINE pairs (within 3 degrees, overlapping half the shorter, each line paired
  with its nearest such neighbour) by spacing: glass-like 0.5 - 7 cm, wall-like 7 - 45 cm (hints only: stairs and
  trees pair too); `doorArcs` = arcs 0.28 - 2 m, 20 - 125 degrees, `doorArcsWithLeaf` those with a leaf line from the
  centre (units.door_votes);
* blocks: every INSERT at every depth by name, family (names.family: no xref prefix, no Revit suffix), most inserted
  first, at most 2000;
* texts: TEXT, MTEXT (plain text), ATTRIB (tag, block), blank ones aside, longest first, at most 5000, each cut at
  1000 characters;
* levelTags (levels.py), gridLabels (grid.py), areas (areas.py).
Drawing text is untrusted: it is copied as text, never interpreted. Owner: U2.
"""
from __future__ import annotations

import collections
import math

from . import READER_VERSION
from . import areas as A
from . import grid as G
from . import levels as LV
from . import names
from . import units as U

MAX_BLOCKS = 2000
MAX_TEXTS = 5000
#: a listed text longer than this is cut (ending in an ellipsis), so a drawing of long notes cannot make drawing.json huge
#: (the six drawings' longest text has 43 characters); level tags and grid labels read the whole text
MAX_TEXT_CHARS = 1000
MAX_TOP_BLOCKS = 10
#: parallel pairs (LayerRead.pairs)
PAIR_MIN_LEN = 0.2
PAIR_ANGLE = math.sin(math.radians(3.0))
PAIR_GLASS = (0.005, 0.07)
PAIR_WALL = (0.07, 0.45)
PAIR_MAX_LINES = 20000
#: a layer looks like walls (AreaProposal.wallItems) with fills or this many wall-like pairs
WALL_PAIRS = 3


def ok(x: float, y: float) -> bool:
    return math.isfinite(x) and math.isfinite(y) and abs(x) < A.LIMIT and abs(y) < A.LIMIT


def robust_box(P: list, k: float) -> list[float] | None:
    """The 1 - 99 % box of points (reader frame) in sheet metres, rounded to the millimetre; None without points."""
    xs = sorted(x * k for x, y in P if ok(x * k, y * k))
    ys = sorted(y * k for x, y in P if ok(x * k, y * k))
    if not xs:
        return None
    lo = int(len(xs) * 0.01)
    hi = len(xs) - 1 - lo
    return [round(xs[lo], 3) + 0.0, round(ys[lo], 3) + 0.0, round(xs[hi], 3) + 0.0, round(ys[hi], 3) + 0.0]


def pair_counts(segs: list) -> dict[str, int]:
    """LayerRead.pairs from straight LINE segments in metres: each line with its nearest parallel neighbour (within 3
    degrees, overlapping half the shorter, 5 mm - 45 cm apart), each pair once."""
    S = []
    for a, b in segs:
        n = math.dist(a, b)
        if n > PAIR_MIN_LEN and ok(*a) and ok(*b):
            S.append((a, b, n))
    if len(S) < 2:
        return {'glassLike': 0, 'wallLike': 0}
    S.sort(key=lambda s: -s[2])
    S = S[:PAIR_MAX_LINES]
    grid: dict[tuple[int, int], list[int]] = collections.defaultdict(list)
    cells_of: list[set] = []
    for i, (a, b, n) in enumerate(S):
        steps = min(max(1, math.ceil(n / 0.5)), 2000)
        cs = {(math.floor(a[0] + (b[0] - a[0]) * s / steps), math.floor(a[1] + (b[1] - a[1]) * s / steps))
              for s in range(steps + 1)}
        cells_of.append(cs)
        for c in cs:
            grid[c].append(i)
    pairs: dict[tuple[int, int], float] = {}
    for i, (a, b, n) in enumerate(S):
        ux, uy = (b[0] - a[0]) / n, (b[1] - a[1]) / n
        cand: set[int] = set()
        for cx, cy in cells_of[i]:
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    cand.update(grid.get((cx + dx, cy + dy), ()))
        best = None
        for j in sorted(cand):
            if j == i:
                continue
            c, d, m = S[j]
            vx, vy = (d[0] - c[0]) / m, (d[1] - c[1]) / m
            if abs(ux * vy - uy * vx) > PAIR_ANGLE:
                continue
            mx, my = (c[0] + d[0]) / 2, (c[1] + d[1]) / 2
            dist = abs((mx - a[0]) * -uy + (my - a[1]) * ux)
            if not PAIR_GLASS[0] <= dist <= PAIR_WALL[1]:
                continue
            t0, t1 = sorted(((c[0] - a[0]) * ux + (c[1] - a[1]) * uy, (d[0] - a[0]) * ux + (d[1] - a[1]) * uy))
            if min(n, t1) - max(0.0, t0) < 0.5 * min(n, m):
                continue
            if best is None or dist < best[0]:
                best = (dist, j)
        if best is not None:
            pairs[(min(i, best[1]), max(i, best[1]))] = best[0]
    glass = sum(1 for v in pairs.values() if v < PAIR_GLASS[1])
    return {'glassLike': glass, 'wallLike': len(pairs) - glass}


def text_rows(W: dict, k: float) -> list[dict]:
    """Every text item as {i, layer, x, y (sheet m), height (m or None), text, kind, tag, block, blays}."""
    mpu = k / 1000.0                                            # metres per DXF unit
    out = []
    for i, d in enumerate(W['items']):
        if d['t'] not in ('TEXT', 'MTEXT', 'ATTRIB'):
            continue
        h, blays = W['texts'].get(i, (None, ()))
        x, y = d['ins'][0] * k, d['ins'][1] * k
        if not ok(x, y):
            continue
        is_attrib = d['t'] == 'ATTRIB'
        path = names.split_path(d.get('path', ''))
        out.append({'i': i, 'layer': d['lay'], 'x': x, 'y': y,
                    'height': round(h * mpu, 4) + 0.0 if isinstance(h, (int, float)) and math.isfinite(h) else None,
                    'text': (d.get('text') or ''), 'kind': d['t'], 'tag': d.get('tag', '') if is_attrib else None,
                    'block': d.get('block') if is_attrib else (path[-1] if path else None), 'blays': blays})
    return out


def grid_lines(items: list[dict], k: float) -> list[tuple]:
    """Straight segments of the open line work on GRID / AXIS layers, sheet m."""
    out = []
    for d in items:
        if d['t'] not in ('LINE', 'LWPOLYLINE', 'POLYLINE') or d.get('closed') or not G.is_grid_layer(d['lay']):
            continue
        P = d.get('pts') or []
        if d['t'] == 'LINE' and len(P) >= 2:
            P = [P[0], P[-1]]
        for a, b in zip(P, P[1:]):
            out.append(((a[0] * k, a[1] * k), (b[0] * k, b[1] * k)))
    return out


def drawing_read(walk: dict, *, source: dict, units: dict, seconds: float) -> dict:
    """The walk of read.py (items and side tables; `leaf` from read.vote) -> DrawingRead (upload-contracts.ts
    section 4). `units` = units.decide(...); `seconds` the read so far (read.py sets the final figure)."""
    W = walk
    items = W['items']
    used = units['used']
    k = U.UNITS_K[used]
    arcs = W['arcs']
    leaf = W.get('leaf') or [False] * len(arcs)

    by_layer: dict[str, list[int]] = collections.defaultdict(list)
    all_pts = []
    for i, d in enumerate(items):
        by_layer[d['lay']].append(i)
        all_pts.extend(A.sample(A.item_points(d)))
    arc_of = {a[0]: (a[3], a[4], leaf[n], a[1], a[2]) for n, a in enumerate(arcs)}   # item -> (r, sweep, leaf, cx, cy)

    def door_size(r: float, sweep: float) -> bool:
        return (U.DOOR_ARC_R[0] <= r * k <= U.DOOR_ARC_R[1]) and (U.DOOR_ARC_SWEEP[0] <= sweep <= U.DOOR_ARC_SWEEP[1])

    layers = []
    for name in sorted(set(by_layer) | set(W['table'])):
        idx = by_layer.get(name, [])
        st = W['table'].get(name, {'on': True, 'frozen': False, 'locked': False, 'plot': True,
                                   'linetype': 'Continuous', 'colour': None})
        bt = collections.Counter(items[i]['t'] for i in idx)
        if W['dims'].get(name):
            bt['DIMENSION'] += W['dims'][name]
        length = 0.0
        line_segs = []
        lts: collections.Counter = collections.Counter()
        closed = solid = 0
        patterns: collections.Counter = collections.Counter()
        fams: collections.Counter = collections.Counter()
        door_arcs = door_leaf = 0
        P = []
        for i in idx:
            d = items[i]
            P.extend(d_pts[:: max(1, len(d_pts) // 8)] if (d_pts := A.item_points(d)) else ())
            t = d['t']
            if 'pts' in d:
                pts = d['pts']
                for a, b in zip(pts, pts[1:]):
                    s = math.dist(a, b)
                    if math.isfinite(s):
                        length += s
                lts[str(d.get('lt', 'BYLAYER'))] += 1
                if d.get('closed'):
                    closed += 1
                if t == 'LINE' and len(pts) >= 2:
                    line_segs.append(((pts[0][0] * k, pts[0][1] * k), (pts[-1][0] * k, pts[-1][1] * k)))
                if i in arc_of:
                    r, sweep, has_leaf, _cx, _cy = arc_of[i]
                    if door_size(r, sweep):
                        door_arcs += 1
                        door_leaf += 1 if has_leaf else 0
            elif t == 'HATCH':
                if d.get('solid'):
                    solid += 1
                else:
                    patterns[str(d.get('pattern', ''))] += 1
            elif t == 'INSERT':
                fams[names.family(d['name'])] += 1
        layers.append({
            'name': name, 'normalised': names.normalise_layer(name),
            'state': {'on': bool(st['on']), 'frozen': bool(st['frozen']), 'locked': bool(st['locked']),
                      'plot': bool(st['plot'])},
            'linetype': st['linetype'] or 'Continuous', 'colour': st['colour'],
            'items': len(idx), 'byType': dict(sorted(bt.items())),
            'inBlocks': sum(1 for i in idx if items[i]['depth'] > 0),
            'closedShapes': closed, 'solidHatches': solid, 'hatchPatterns': dict(sorted(patterns.items())),
            'length': round(length * k, 2) + 0.0,
            'doorArcs': door_arcs, 'doorArcsWithLeaf': door_leaf,
            'texts': sum(1 for i in idx if items[i]['t'] in ('TEXT', 'MTEXT', 'ATTRIB')),
            'inserts': bt.get('INSERT', 0),
            'topBlocks': [{'family': f, 'count': c} for f, c in
                          sorted(fams.items(), key=lambda kv: (-kv[1], kv[0]))[:MAX_TOP_BLOCKS]],
            'linetypes': dict(sorted(lts.items())),
            'pairs': pair_counts(line_segs),
            'extents': robust_box(P, k),
        })

    # blocks
    blocks: dict[str, dict] = {}
    for d in items:
        if d['t'] == 'INSERT':
            b = blocks.setdefault(d['name'], {'inserts': 0, 'byLayer': collections.Counter(), 'mirrored': 0,
                                              'maxDepth': 0, 'tags': set()})
            b['inserts'] += 1
            b['byLayer'][d['lay']] += 1
            b['mirrored'] += 1 if d['sx'] * d['sy'] < 0 else 0
            b['maxDepth'] = max(b['maxDepth'], d['depth'])
    for d in items:
        if d['t'] == 'ATTRIB' and d.get('block') in blocks:
            blocks[d['block']]['tags'].add(str(d.get('tag', '')))
    block_rows = [{'name': n, 'family': names.family(n), 'inserts': b['inserts'],
                   'byLayer': dict(sorted(b['byLayer'].items())), 'mirrored': b['mirrored'],
                   'maxDepth': b['maxDepth'], 'attribTags': sorted(b['tags'])} for n, b in blocks.items()]
    block_rows.sort(key=lambda r: (-r['inserts'], r['name']))

    # texts, level tags, grid labels
    rows = text_rows(W, k)
    level = LV.level_tags(rows)
    labels = G.grid_labels(rows, grid_lines(items, k))
    texts = []
    for t in rows:
        s = t['text'].strip()
        if not s:
            continue
        if len(s) > MAX_TEXT_CHARS:
            s = s[:MAX_TEXT_CHARS - 1] + '\N{HORIZONTAL ELLIPSIS}'
        texts.append({'layer': t['layer'], 'x': round(t['x'], 3) + 0.0, 'y': round(t['y'], 3) + 0.0,
                      'height': t['height'], 'text': s, 'kind': t['kind'], 'tag': t['tag'], 'block': t['block']})
    texts.sort(key=lambda t: (-len(t['text']), t['layer'], t['x'], t['y'], t['text']))
    for t in level:
        t['x'] = round(t['x'], 3) + 0.0
        t['y'] = round(t['y'], 3) + 0.0

    # areas
    wall_layers = {la['name'] for la in layers if la['solidHatches'] > 0 or la['pairs']['wallLike'] >= WALL_PAIRS}
    doors = [(cx * k, cy * k) for _i, cx, cy, r, sweep in arcs if door_size(r, sweep)]
    areas = A.propose_areas(items, k, wall_layers=wall_layers, door_points=doors,
                            level_points=[(t['x'], t['y']) for t in level])

    ins = W.get('insUnits')
    return {
        'format': 'drawing-read/1',
        'source': {'sha1': source['sha1'], 'name': source.get('name', '')},
        'reader': {'version': READER_VERSION, 'seconds': round(float(seconds), 2), 'peakMemoryMB': None},
        'dxf': {'acadVersion': W.get('acad'), 'insUnits': ins if isinstance(ins, int) else None,
                'auditErrors': int(W.get('auditErrors', 0)), 'auditFixes': int(W.get('auditFixes', 0))},
        'units': units,
        'extents': robust_box(all_pts, k),
        'counts': {'items': len(items), 'byType': dict(sorted(collections.Counter(d['t'] for d in items).items())),
                   'dimensions': sum(W['dims'].values())},
        'layers': layers,
        'blocks': block_rows[:MAX_BLOCKS],
        'texts': texts[:MAX_TEXTS],
        'levelTags': level,
        'gridLabels': labels,
        'areas': areas,
    }
