"""What the build hands the outputs besides the model (docs/upload/DESIGN.md U-10.8, U-11.3, U-12.2): the per-floor
upload report, the replay input recorded from the real build, the detector records with the model opening each became.
Coordinates: report positions in each floor's SHEET metres (its source's own frame: the build frame minus the floor's
alignment shift); replay data in MODEL coordinates (sheet - toSheet), unrounded except `sheet` (the bank's 2 decimals).
"""
from __future__ import annotations

import collections
import math

from shapely.geometry import LineString, Polygon

from .. import roles as R
from .bank import axis_of, cat_of, lines_of, segs_of

NOISE_LINES = 6000          # per floor: the longest lines the build sets aside (the bank's)


def _at(x, y, s):
    return [round(float(x) - s[0], 3), round(float(y) - s[1], 3)]


def _keys_near(items, geom, role, reach=0.03):
    """Keys of the floor's items of one role whose line work touches `geom` (shifted frame)."""
    g = geom.buffer(reach)
    out = []
    for d in items:
        if role not in d['roles'] or not d.get('pts') or len(d['pts']) < 2:
            continue
        if LineString(d['pts']).intersects(g) and d.get('k'):
            out.append(d['k'])
    return sorted(set(out))


def _longest_run(lines, q):
    """The longest straight run of the line work `lines` that lies inside the part `q` -> (a, b), or None. A single part
    can be several lines joined (an L, a hook): its run, not its bounding rectangle's axis, says where the line is (the
    middle of the run lies on the part, where the check screen puts the flag)."""
    best = None
    inside = q.buffer(0.001)
    for ln in lines:
        for piece in lines_of(ln.intersection(inside)):
            cs = list(piece.coords)
            for a, b in zip(cs, cs[1:]):
                L = math.dist(a, b)
                if best is None or L > best[0]:
                    best = (L, a, b)
    return None if best is None else (best[1], best[2])


def singles(F, A, part_ids, s) -> list[dict]:
    """SingleLine: each `single` part with the wall-layer line work it came from (keys, layer) and the ends of its
    longest straight run (the part's long axis when no line work is found)."""
    out = []
    cx, cy = A['cx'], A['cy']
    pieces, src, lines = F['singles_src']
    for idx in part_ids:
        p = A['parts'][idx]
        q = Polygon([(x + cx, y + cy) for x, y in p['o']], [[(x + cx, y + cy) for x, y in h] for h in p['h']])
        touch = q.buffer(0.01)
        near = [i for i, g in enumerate(pieces) if g.intersects(touch)]
        keys = sorted({src[i][0] for i in near if src[i][0]})
        lays = collections.Counter(src[i][1] for i in near)
        run = _longest_run([lines[i] for i in near], q)
        a, b = run if run is not None else axis_of(q)[:2]
        out.append({'part': idx, 'keys': keys, 'layer': min(lays, key=lambda l: (-lays[l], l)) if lays else '',
                    'a': _at(*a, s), 'b': _at(*b, s)})
    return out


def floor_report(F, A, B, det, align_rep, lost, outline_sugg, s) -> dict:
    """FloorUploadReport (contracts.py) of one floor."""
    key = F['cfg']['key']
    rails = []
    for g in B['rails_dropped_polys'] + B['rails_off_polys']:
        c = g.representative_point()
        rails.append({'keys': _keys_near(F['items'], g, 'railing'), 'at': _at(c.x, c.y, s)})
    return {
        'source': F['source'], 'area': F['cfg']['area'], 'items': len(F['items']), 'itemsNoPoints': F['noPoints'],
        'subtreesOutside': F['subtreesOutside'], 'alignment': align_rep,
        'singles': singles(F, A, [i for i, k in A['single_parts'] if k == key], s),
        'outlineSuggestions': outline_sugg,
        'swingsUnmatched': det['swingsUnmatched'],
        'railsLeftOut': rails,
        'roomLabels': [{'text': t, 'at': _at(x, y, s)} for t, x, y in B['skipped_at']],
        'platesDropped': [{'area': round(x.area, 2), 'at': _at(x.representative_point().x, x.representative_point().y, s)}
                          for x, _ in B['plate_dropped']],
        'detector': {'seconds': det['seconds'], 'slow': det['slow'], 'frameRowsSkipped': det['frameRowsSkipped'],
                     'records': len(det['records'])},
        'lost': lost,
    }


def lost_inserts(conversion: dict | None, area: dict) -> list[dict]:
    """The lost blocks' model-space inserts (ConversionReport.lostBlocks, sheet m) that lie in the floor's area."""
    out = []
    if not conversion:
        return out
    box = None
    if area.get('kind') == 'box':
        x0, y0, x1, y1 = area['bbox']; pad = area.get('pad', 0.0)
        box = (x0 - pad, y0 - pad, x1 + pad, y1 + pad)
    for lb in conversion.get('lostBlocks') or []:
        for ins in lb.get('inserts') or []:
            x, y = float(ins['x']), float(ins['y'])
            if box is None or (box[0] <= x <= box[2] and box[1] <= y <= box[3]):
                out.append({'block': lb['name'], 'at': [round(x, 3), round(y, 3)], 'layer': ins.get('layer', '')})
    return out


# ---------------------------------------------------------------------------------------------------- replay input
def replay_floor(F, A, sheet) -> dict:
    """ReplayFloor: the bank's line categories over the items (noise: the longest 6,000), the rectangles the build
    actually paired (walls at 0.04 - 0.45 m, glass at 0.005 - 0.30 m) and the built wall and glass rings."""
    cx, cy = A['cx'], A['cy']
    k = F['cfg']['key']
    lines = collections.defaultdict(list)
    for d in F['items']:
        if d['t'] in ('INSERT', 'ATTRIB') or 'text' in d: continue
        c = cat_of(d)
        if 'pts' in d: lines[c] += segs_of(d, False)
        elif 'loops' in d and c != 'noise':
            for lp in d['loops']: lines[c] += [[a[0], a[1], b[0], b[1]] for a, b in zip(lp, lp[1:]) if math.dist(a, b) > 0.01]
    lines['noise'] = sorted(lines['noise'], key=lambda q: -math.hypot(q[2] - q[0], q[3] - q[1]))[:NOISE_LINES]
    model = lambda segs: [[v - (cx if i % 2 == 0 else cy) for i, v in enumerate(s)] for s in segs]  # noqa: E731
    quads = lambda rects: [[[x - cx, y - cy] for x, y in list(r.exterior.coords)[:4]] for r in rects]  # noqa: E731
    ring_of = lambda kinds: [{'o': p['o'], 'h': p['h']} for p in A['parts'] if p['floor'] == k and p['kind'] in kinds and p['z0'] < 0.01]  # noqa: E731
    return {'lines': {c: model(lines[c]) for c in ('wall', 'glass', 'door', 'stair', 'railing', 'noise') if lines[c]},
            'pieces': {'wall': quads(F['rects']), **({'glass': quads(F['grects'])} if F['grects'] else {})},
            'rings': {'wall': ring_of(('wall', 'column', 'parapet')), 'glass': ring_of(('glass', 'mullion'))},
            'sheet': sheet}


def line_counts(replay_floor) -> dict:
    """ReplayFacts.counts: lines per category, as the replay draws them (noise: the longest 6,000)."""
    return {c: len(v) for c, v in replay_floor['lines'].items()}


def sheets(floors, A) -> dict[str, list[float]]:
    """Where each floor's lines are drawn in the replay's first steps: floors from separate files side by side in reading
    order (i * (width + 3 m), the bank rule), floors sharing a sheet at their sheetShift."""
    pminx, pminy, pmaxx, pmaxy = A['allp'].bounds
    order, out = [], {}
    for F in floors:
        if F['source'] not in order:
            order.append(F['source'])
        j = order.index(F['source'])
        sh = F.get('sheetShift') or [0.0, 0.0]
        out[F['cfg']['key']] = [round(j * (pmaxx - pminx + 3.0) + sh[0], 2), round(sh[1] + 0.0, 2)]
    return out


def facts(floors, A, built, X, align_reps, replay_floors) -> dict:
    S = X.settings
    names = {s['sha1']: s for s in S['sources']}
    seen, sources = set(), []
    for F in floors:
        if F['source'] in seen: continue
        seen.add(F['source'])
        src = names.get(F['source'], {})
        sources.append({'name': src.get('name', ''), 'units': F['units'], 'kind': src.get('kind', 'dwg')})
    opening_counts = {}
    for F in floors:
        k = F['cfg']['key']
        c = collections.Counter(o['kind'] for o in A['openings'] if o['floor'] == k)
        opening_counts[k] = {kind: c.get(kind, 0) for kind in ('door', 'window', 'passage')}
    return {
        'floors': [{'key': F['cfg']['key'], 'name': F['cfg']['name'], 'level': F['cfg']['level'],
                    'wallHeight': F['cfg']['wallHeight'], 'source': names.get(F['source'], {}).get('name', ''),
                    'align': align_reps[i]} for i, F in enumerate(floors)],
        'sources': sources,
        'exportedFrom': S['project'].get('exportedFrom'),
        'counts': {F['cfg']['key']: line_counts(replay_floors[F['cfg']['key']]) for F in floors},
        'parts': {k: dict(v) for k, v in A['counts'].items()},
        'openings': opening_counts,
        'layersByRole': R.builder_layers(S['layers']),
        'liftShaft': any(w == 'lift shaft' for B in built.values() for w, _ in B['voids']),
        'stairs': sum(len(B['S']['stairs']) for B in built.values()),
        'furniturePieces': len(A['furniture']),
        'furnitureKinds': len(A['furn_kinds']),
    }
