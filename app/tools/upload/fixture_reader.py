"""A PROVISIONAL reader for the scaffold's drawing and plan fixtures (WORK_BREAKDOWN U0 step 8; ACCEPTANCE 2.5): the walk
of detector/tools/prims.py `_flatten` (the same items, the same order, the same arithmetic) with the nested key `k` of
U-7.2, and from it a DrawingRead (U-7.3, after docs/upload/reference/read_drawing.py and areas_propose.py) and a
PlanGeometry (U-7.5) with sig / rsig / eid per entry (keys.py, names.py). Not app code: U2 writes the real reader
(walkthrough_builder/read.py ...) and lists any difference with these fixtures in its U2.md.
"""
from __future__ import annotations

import collections
import gzip
import json
import math
import re
import statistics
import time
from pathlib import Path

from ezdxf import path as ezpath
from ezdxf import recover
from shapely.geometry import LineString

from walkthrough_builder import READER_VERSION, keys, names

SKIP = ('POINT', 'ATTDEF', 'WIPEOUT', 'IMAGE', 'VIEWPORT', 'OLE2FRAME', '3DSOLID', 'REGION', 'BODY', 'MESH')
UNIT_OF = {1: 'in', 2: 'ft', 4: 'mm', 5: 'cm', 6: 'm'}
M_PER_UNIT = {'mm': 0.001, 'cm': 0.01, 'm': 1.0, 'in': 0.0254, 'ft': 0.3048}
UNITS_K = {'mm': 1.0, 'cm': 10.0, 'm': 1000.0, 'in': 25.4, 'ft': 304.8}        # openings.UNITS: prims frame -> m
# verbatim from docs/upload/reference/read_drawing.py (U-7.3)
LEVEL_RE = re.compile(r'^\s*(?:(?:F\.?F\.?L|S\.?S\.?L|T\.?O\.?S|FL|EL|LEVEL|LVL|LV)\.?\s*[:=]?\s*)?([+\-±]?\s*\d{1,3}(?:[.,]\d{2,3}))\s*(?:M|m)?\s*$')
GRID_RE = re.compile(r'^[A-Z]{1,2}[\'′]?$|^\d{1,2}[\'′]?$|^[A-Z]{1,2}[.\-]?\d{1,2}$|^\d{1,2}[.\-/]\d{1,2}$')
LEVEL_TAGS = ('LEVEL', 'ELEV', 'EL', 'LV', 'FFL')


def walk_drawing(dxf_path: Path, flatten_mm: float = 10.0) -> dict:
    """prims._flatten plus `k` (and side tables the DrawingRead needs). Coordinates: DXF units / 1000, as prims."""
    t0 = time.perf_counter()
    doc, aud = recover.readfile(str(dxf_path))
    items: list[dict] = []
    extra: list[dict] = []          # per item: {'blays': layers of the enclosing INSERTs}
    arcs: list[tuple] = []          # (cx, cy, r, sweep, ends) in DXF units
    dims: list[float] = []
    dist = flatten_mm               # flattening distance in DXF units (10 for mm: prims' own)

    def add(d, blays):
        items.append(d)
        extra.append({'blays': blays})

    def child_key(parent_key, v, i, seen):
        src = getattr(v, 'source_of_copy', None)
        h = src.dxf.get('handle') if src is not None else None
        part = h if h else f'~{i}'
        if part in seen:                               # a MINSERT's copies share their source handle
            part = f'{part}~{i}'
        seen.add(part)
        return f'{parent_key}/{part}'

    def walk(e, inh=None, depth=0, path=(), h=None, k=None, blays=()):
        lay = e.dxf.get('layer', '0')
        if lay == '0' and inh:
            lay = inh
        t = e.dxftype()
        top_h = h or e.dxf.get('handle')
        key = k or e.dxf.get('handle') or '~top'
        base = {'t': t, 'lay': lay, 'depth': depth, 'path': '>'.join(path), 'h': top_h, 'k': key}
        if t == 'INSERT':
            nm = e.dxf.get('name', '')
            try:
                p = e.dxf.insert
                m = e.matrix44()
                ux, uy = m.transform_direction((1, 0, 0)), m.transform_direction((0, 1, 0))
                sx, sy = math.hypot(ux.x, ux.y), math.hypot(uy.x, uy.y)
                if ux.x * uy.y - ux.y * uy.x < 0:
                    sy = -sy
                rot = math.degrees(math.atan2(ux.y, ux.x))
                add({**base, 'name': nm, 'ins': [p.x / 1000, p.y / 1000], 'rot': round(rot, 3),
                     'sx': round(sx, 4), 'sy': round(sy, 4)}, blays)
            except Exception:
                pass
            try:
                for j, a in enumerate(e.attribs):
                    ip = a.dxf.insert
                    ah = a.dxf.get('handle') or f'~{j}'
                    add({**base, 't': 'ATTRIB', 'lay': a.dxf.get('layer', lay), 'ins': [ip.x / 1000, ip.y / 1000],
                         'text': a.dxf.get('text', ''), 'tag': a.dxf.get('tag', ''), 'block': nm,
                         'k': f'{key}@{ah}'}, blays)
            except Exception:
                pass
            if depth < 8:
                try:
                    seen: set[str] = set()
                    for i, v in enumerate(e.virtual_entities()):
                        walk(v, lay, depth + 1, path + (nm,), top_h, child_key(key, v, i, seen), blays + (lay,))
                except Exception:
                    pass
            return
        if t == 'DIMENSION':
            try:
                am = e.dxf.get('actual_measurement', None)
                if am:
                    dims.append(float(am))
            except Exception:
                pass
            return
        if t in ('TEXT', 'MTEXT', 'ATTRIB'):
            try:
                p = e.dxf.insert
                s = (e.plain_text() if t == 'MTEXT' else e.dxf.get('text', '')).strip()
                hgt = e.dxf.get('char_height' if t == 'MTEXT' else 'height', None)
                d = {**base, 'ins': [p.x / 1000, p.y / 1000], 'text': s}
                add(d, blays)
                extra[-1]['height'] = hgt
            except Exception:
                pass
            return
        if t == 'HATCH':
            try:
                loops = [[[v.x / 1000, v.y / 1000] for v in bp.flattening(distance=dist)] for bp in ezpath.from_hatch(e)]
                add({**base, 'loops': loops, 'solid': bool(e.dxf.get('solid_fill', 0)),
                     'pattern': e.dxf.get('pattern_name', '')}, blays)
            except Exception:
                pass
            return
        if t in SKIP:
            return
        try:
            pts = [[v.x / 1000, v.y / 1000] for v in ezpath.make_path(e).flattening(distance=dist)]
        except Exception:
            return
        if not pts:
            return
        closed = False
        try:
            closed = bool(e.closed) if t == 'LWPOLYLINE' else (t == 'CIRCLE' or (t == 'POLYLINE' and e.is_closed))
        except Exception:
            pass
        add({**base, 'pts': pts, 'closed': closed, 'lt': e.dxf.get('linetype', 'BYLAYER')}, blays)
        if t == 'ARC':
            try:
                c = e.dxf.center
                sweep = (e.dxf.end_angle - e.dxf.start_angle) % 360
                arcs.append((c.x, c.y, e.dxf.radius, sweep, (tuple(pts[0]), tuple(pts[-1])), len(items) - 1))
            except Exception:
                pass

    for e in doc.modelspace():
        walk(e)
    table = {}
    for la in doc.layers:
        table[la.dxf.name] = {'on': not la.is_off(), 'frozen': la.is_frozen(), 'locked': la.is_locked(),
                              'plot': bool(la.dxf.get('plot', 1)), 'linetype': la.dxf.get('linetype', 'Continuous'),
                              'colour': la.dxf.get('color', None)}
    ins_units = doc.header.get('$INSUNITS', None)
    return {'items': items, 'extra': extra, 'arcs': arcs, 'dims': dims, 'table': table,
            'layers': {la.dxf.name: la.dxf.get('linetype', 'Continuous') for la in doc.layers},
            'acad': doc.dxfversion, 'insUnits': ins_units, 'auditErrors': len(aud.errors), 'auditFixes': len(aud.fixes),
            'seconds': time.perf_counter() - t0}


def pts_of(d):
    return d.get('pts') or [q for l in d.get('loops', []) for q in l] or ([d['ins']] if 'ins' in d else [])


# ------------------------------------------------------------------------------------------------------------- units
def door_votes(W: dict) -> tuple[dict, set[int]]:
    """U-7.4: quarter arcs (80 - 100 deg) with a straight leaf from the centre to an arc end, the leaf as long as the
    radius within 10 %, counted per unit hypothesis where 0.6 <= r k <= 1.25. Coordinates in DXF units."""
    segs = []
    for d in W['items']:
        if d['t'] in ('LINE', 'LWPOLYLINE', 'POLYLINE') and d.get('pts'):
            P = [(x * 1000, y * 1000) for x, y in d['pts']]
            segs += list(zip(P, P[1:]))
    quarter = [(cx, cy, r, ends, idx) for cx, cy, r, sweep, ends, idx in W['arcs'] if 80 <= sweep <= 100 and r > 0]
    if not quarter:
        return {u: 0 for u in M_PER_UNIT}, set()
    cell = max(1e-9, 0.08 * statistics.median(r for _, _, r, _, _ in quarter))
    grid = collections.defaultdict(list)
    for a, b in segs:
        for p in (a, b):
            grid[(math.floor(p[0] / cell), math.floor(p[1] / cell))].append((a, b))
    with_leaf, leaf_idx = [], set()
    for cx, cy, r, ends, idx in quarter:
        tol = 0.08 * r
        n = max(1, math.ceil(tol / cell))
        gx, gy = math.floor(cx / cell), math.floor(cy / cell)
        ok = False
        ends_u = [(x * 1000, y * 1000) for x, y in ends]
        for i in range(-n, n + 1):
            for j in range(-n, n + 1):
                for a, b in grid.get((gx + i, gy + j), ()):
                    for hp, tp in ((a, b), (b, a)):
                        if math.dist(hp, (cx, cy)) <= tol and any(math.dist(tp, q) <= tol for q in ends_u) \
                                and abs(math.dist(hp, tp) - r) <= 0.1 * r:
                            ok = True
                            break
                    if ok:
                        break
                if ok:
                    break
            if ok:
                break
        if ok:
            with_leaf.append(r)
            leaf_idx.add(idx)
    votes = {u: sum(1 for r in with_leaf if 0.6 <= r * k <= 1.25) for u, k in M_PER_UNIT.items()}
    return votes, leaf_idx


def decide_units(ins_units, votes, dim_median) -> dict:
    declared = UNIT_OF.get(ins_units)
    best = max(votes, key=lambda u: (votes[u], u == declared))
    if declared is None:
        if votes[best] >= 3:
            return {'declared': None, 'votes': votes, 'dimensionMedian': dim_median, 'used': best, 'verdict': 'votes-win',
                    'note': f'the file names no units; its doors say {best}'}
        return {'declared': None, 'votes': votes, 'dimensionMedian': dim_median, 'used': 'mm', 'verdict': 'unknown',
                'note': 'the file names no units and its doors do not say: millimetres assumed'}
    if votes[declared] >= votes[best] or votes[best] < 3:
        verdict = 'agree' if votes[declared] >= 3 else 'declared-only'
        return {'declared': declared, 'votes': votes, 'dimensionMedian': dim_median, 'used': declared,
                'verdict': verdict, 'note': '' if verdict == 'agree' else f'the file says {declared}; too few doors to check'}
    names_ = {'mm': 'millimetres', 'cm': 'centimetres', 'm': 'metres', 'in': 'inches', 'ft': 'feet'}
    return {'declared': declared, 'votes': votes, 'dimensionMedian': dim_median, 'used': best, 'verdict': 'votes-win',
            'note': f'the file says {names_[declared]}, its doors say {names_[best]}'}


# ------------------------------------------------------------------------------------------------------ drawing.json
def robust_box(P, k):
    if not P:
        return None
    xs = sorted(p[0] for p in P)
    ys = sorted(p[1] for p in P)
    lo, hi = int(len(xs) * 0.01), max(0, int(len(xs) * 0.99) - 1)
    return [round(xs[lo] * k, 3), round(ys[lo] * k, 3), round(xs[hi] * k, 3), round(ys[hi] * k, 3)]


def pair_classes(segs, k):
    """Parallel LINE pairs (within 3 degrees, overlapping half the shorter) by spacing: hints only."""
    glass = wall = 0
    S = [(a, b) for a, b in segs if math.dist(a, b) * k > 0.2][:3000]
    for i in range(len(S)):
        a, b = S[i]
        ux, uy = b[0] - a[0], b[1] - a[1]
        n = math.hypot(ux, uy)
        ux, uy = ux / n, uy / n
        for j in range(i + 1, min(len(S), i + 60)):
            c, d = S[j]
            vx, vy = d[0] - c[0], d[1] - c[1]
            m = math.hypot(vx, vy)
            if abs(ux * vy - uy * vx) / m > math.sin(math.radians(3)):
                continue
            t0, t1 = sorted(((c[0] - a[0]) * ux + (c[1] - a[1]) * uy, (d[0] - a[0]) * ux + (d[1] - a[1]) * uy))
            if min(n, t1) - max(0.0, t0) < 0.5 * min(n, m):
                continue
            dist = abs((c[0] - a[0]) * -uy + (c[1] - a[1]) * ux) * k
            if 0.005 <= dist < 0.07:
                glass += 1
            elif 0.07 <= dist <= 0.45:
                wall += 1
    return {'glassLike': glass, 'wallLike': wall}


def drawing_read(W: dict, source: dict, units: dict) -> dict:
    k = UNITS_K[units['used']]
    items, extra = W['items'], W['extra']
    allp = [p for d in items for p in pts_of(d)[:: max(1, len(pts_of(d)) // 20)]]
    by_layer = collections.defaultdict(list)
    for i, d in enumerate(items):
        by_layer[d['lay']].append(i)
    leaf_arcs = W.get('leafArcs', set())
    # door arcs with a leaf, per layer (radius 0.28 - 2 m, 20 - 125 deg)
    arcs_by_item = {idx: (r, sweep) for _, _, r, sweep, _, idx in W['arcs']}
    layers = []
    for name in sorted(set(by_layer) | set(W['table'])):
        idx = by_layer.get(name, [])
        st = W['table'].get(name, {'on': True, 'frozen': False, 'locked': False, 'plot': True,
                                   'linetype': 'Continuous', 'colour': None})
        bt = collections.Counter(items[i]['t'] for i in idx)
        segs = [((items[i]['pts'][0][0] * 1000, items[i]['pts'][0][1] * 1000),
                 (items[i]['pts'][-1][0] * 1000, items[i]['pts'][-1][1] * 1000))
                for i in idx if items[i]['t'] == 'LINE' and items[i].get('pts')]
        length = sum(math.dist(a, b) for i in idx for a, b in zip(items[i].get('pts', []), items[i].get('pts', [])[1:]))
        door_arcs = [i for i in idx if i in arcs_by_item and 0.28 <= arcs_by_item[i][0] * M_PER_UNIT[units['used']] <= 2.0
                     and 20 <= arcs_by_item[i][1] <= 125]
        fams = collections.Counter(names.family(items[i]['name']) for i in idx if items[i]['t'] == 'INSERT')
        lts = collections.Counter(items[i].get('lt', 'BYLAYER') for i in idx if 'lt' in items[i])
        P = [p for i in idx for p in pts_of(items[i])[:: max(1, len(pts_of(items[i])) // 8)]]
        layers.append({
            'name': name, 'normalised': names.normalise_layer(name),
            'state': {'on': bool(st['on']), 'frozen': bool(st['frozen']), 'locked': bool(st['locked']),
                      'plot': bool(st['plot'])},
            'linetype': st['linetype'] or 'Continuous', 'colour': st['colour'],
            'items': len(idx), 'byType': dict(sorted(bt.items())),
            'inBlocks': sum(1 for i in idx if items[i]['depth'] > 0),
            'closedShapes': sum(1 for i in idx if items[i].get('closed')),
            'solidHatches': sum(1 for i in idx if items[i]['t'] == 'HATCH' and items[i].get('solid')),
            'hatchPatterns': dict(sorted(collections.Counter(items[i].get('pattern', '') for i in idx
                                                             if items[i]['t'] == 'HATCH' and not items[i].get('solid')).items())),
            'length': round(length * k, 2),
            'doorArcs': len(door_arcs), 'doorArcsWithLeaf': sum(1 for i in door_arcs if i in leaf_arcs),
            'texts': sum(1 for i in idx if items[i]['t'] in ('TEXT', 'MTEXT', 'ATTRIB')),
            'inserts': bt.get('INSERT', 0),
            'topBlocks': [{'family': f, 'count': c} for f, c in sorted(fams.items(), key=lambda kv: (-kv[1], kv[0]))[:10]],
            'linetypes': dict(sorted(lts.items())),
            'pairs': pair_classes(segs, k * 0.001),
            'extents': robust_box(P, k),
        })
    # blocks
    blocks = collections.defaultdict(lambda: {'inserts': 0, 'byLayer': collections.Counter(), 'mirrored': 0,
                                              'maxDepth': 0, 'tags': set()})
    for d in items:
        if d['t'] == 'INSERT':
            b = blocks[d['name']]
            b['inserts'] += 1
            b['byLayer'][d['lay']] += 1
            b['mirrored'] += 1 if d['sx'] * d['sy'] < 0 else 0
            b['maxDepth'] = max(b['maxDepth'], d['depth'])
        elif d['t'] == 'ATTRIB' and d.get('block'):
            blocks[d['block']]['tags'].add(d.get('tag', ''))
    block_rows = [{'name': n, 'family': names.family(n), 'inserts': b['inserts'], 'byLayer': dict(sorted(b['byLayer'].items())),
                   'mirrored': b['mirrored'], 'maxDepth': b['maxDepth'], 'attribTags': sorted(b['tags'])}
                  for n, b in blocks.items()]
    block_rows.sort(key=lambda r: (-r['inserts'], r['name']))
    # texts
    texts = []
    for i, d in enumerate(items):
        if d['t'] in ('TEXT', 'MTEXT', 'ATTRIB'):
            h = extra[i].get('height')
            texts.append({'layer': d['lay'], 'x': round(d['ins'][0] * k, 3), 'y': round(d['ins'][1] * k, 3),
                          'height': None if h is None else round(h * k * 0.001, 3), 'text': d['text'],
                          'kind': d['t'], 'tag': d.get('tag') if d['t'] == 'ATTRIB' else None,
                          'block': d.get('block') if d['t'] == 'ATTRIB' else (d['path'].split('>')[-1] or None)})
    level_tags = []
    for t in texts:
        m = LEVEL_RE.match(t['text'] or '')
        is_tag = t['kind'] == 'ATTRIB' and (t['tag'] or '').upper() in LEVEL_TAGS
        if not (m or is_tag):
            continue
        raw = (m.group(1) if m else t['text']).replace(' ', '').replace('±', '').replace(',', '.')
        try:
            v = float(raw)
        except ValueError:
            continue
        if abs(v) > 100:
            v /= 1000
        near = [o for o in texts if o is not t and math.dist((o['x'], o['y']), (t['x'], t['y'])) <= 3.0
                and not LEVEL_RE.match(o['text'] or '')]
        label = min(near, key=lambda o: math.dist((o['x'], o['y']), (t['x'], t['y'])))['text'] if near else None
        level_tags.append({'x': t['x'], 'y': t['y'], 'value': round(v, 4), 'text': t['text'], 'layer': t['layer'],
                           'source': 'attrib' if t['kind'] == 'ATTRIB' else 'text', 'label': label})
    gridlike = lambda L: 'GRID' in L.upper() or 'AXIS' in L.upper()               # noqa: E731
    glines = [[(x * k, y * k) for x, y in (d['pts'][0], d['pts'][-1])] for d in items
              if gridlike(d['lay']) and d.get('pts') and len(d['pts']) >= 2 and not d.get('closed') and d['t'] != 'CIRCLE']
    grid = []
    for i, d in enumerate(items):
        if d['t'] not in ('TEXT', 'MTEXT', 'ATTRIB'):
            continue
        txt = (d['text'] or '').strip()
        on_grid = gridlike(d['lay']) or any(gridlike(b) for b in extra[i]['blays'])
        if not (on_grid and GRID_RE.match(txt)):
            continue
        p = (d['ins'][0] * k, d['ins'][1] * k)
        best = None
        for a, b in glines:
            L = math.dist(a, b)
            if L < 1e-6:
                continue
            near_end = min(math.dist(p, a), math.dist(p, b))
            t_ = max(0.0, min(1.0, ((p[0] - a[0]) * (b[0] - a[0]) + (p[1] - a[1]) * (b[1] - a[1])) / L ** 2))
            off = math.dist(p, (a[0] + t_ * (b[0] - a[0]), a[1] + t_ * (b[1] - a[1])))
            if (near_end <= 1.0 or off <= 0.3) and (best is None or L > best[0]):
                start, end = (a, b) if math.dist(p, a) <= math.dist(p, b) else (b, a)
                best = (L, start, end)
        line = direction = None
        if best:
            L, s, e = best
            line = [[round(s[0], 3), round(s[1], 3)], [round(e[0], 3), round(e[1], 3)]]
            direction = [round((e[0] - s[0]) / L, 6), round((e[1] - s[1]) / L, 6)]
        grid.append({'text': txt, 'x': round(p[0], 3), 'y': round(p[1], 3), 'layer': d['lay'],
                     'block': d['path'].split('>')[-1] or None, 'direction': direction, 'line': line})
    texts.sort(key=lambda t: (-len(t['text']), t['layer'], t['x'], t['y']))
    # areas (areas_propose.py: occupied 1 m cells, grown by 2 m, connected, boxes over 25 m2)
    cells = collections.Counter()
    cell_of_item = {}
    for i, d in enumerate(items):
        if d['t'] in ('TEXT', 'MTEXT', 'ATTRIB', 'INSERT'):
            continue
        P = d.get('pts') or [q for l in d.get('loops', []) for q in l]
        for x, y in P[:: max(1, len(P) // 20)]:
            c = (math.floor(x * k), math.floor(y * k))
            cells[c] += 1
            cell_of_item.setdefault(i, c)
    occ = set(cells)
    seen, comps = set(), []
    for c in sorted(occ):
        if c in seen:
            continue
        stack, comp = [c], []
        seen.add(c)
        while stack:
            x, y = stack.pop()
            comp.append((x, y))
            for dx in range(-2, 3):
                for dy in range(-2, 3):
                    q = (x + dx, y + dy)
                    if q in occ and q not in seen:
                        seen.add(q)
                        stack.append(q)
        xs = [p[0] for p in comp]
        ys = [p[1] for p in comp]
        box = [min(xs), min(ys), max(xs) + 1, max(ys) + 1]
        if (box[2] - box[0]) * (box[3] - box[1]) > 25:
            comps.append((set(comp), box))
    wall_layers = {la['name'] for la in layers if la['solidHatches'] > 0 or la['pairs']['wallLike'] >= 5}
    areas = []
    for comp, box in sorted(comps, key=lambda cb: (-cb[1][3], cb[1][0])):
        members = [i for i, c in cell_of_item.items() if c in comp]
        wall_items = sum(1 for i in members if items[i]['lay'] in wall_layers)
        tags_in = sum(1 for t in level_tags if box[0] <= t['x'] <= box[2] and box[1] <= t['y'] <= box[3])
        arcs_in = sum(1 for cx, cy, r, sweep, _, idx in W['arcs'] if 80 <= sweep <= 100 and idx in members)
        looks = 'plan' if arcs_in >= 2 and wall_items > 0 else ('elevation' if tags_in >= 2 else 'other')
        areas.append({'id': f'a{len(areas) + 1}', 'bbox': [float(v) for v in box], 'items': len(members),
                      'wallItems': wall_items, 'looks': looks})
    return {
        'format': 'drawing-read/1',
        'source': {'sha1': source['sha1'], 'name': source['name']},
        'reader': {'version': READER_VERSION, 'seconds': round(W['seconds'], 1), 'peakMemoryMB': None},
        'dxf': {'acadVersion': W['acad'], 'insUnits': W['insUnits'], 'auditErrors': W['auditErrors'],
                'auditFixes': W['auditFixes']},
        'units': units,
        'extents': robust_box(allp, k),
        'counts': {'items': len(items), 'byType': dict(sorted(collections.Counter(d['t'] for d in items).items())),
                   'dimensions': len(W['dims'])},
        'layers': layers,
        'blocks': block_rows[:2000],
        'texts': texts[:5000],
        'levelTags': level_tags,
        'gridLabels': grid,
        'areas': areas,
    }


# ------------------------------------------------------------------------------------------------- plan.json.gz
def plan_geometry(W: dict, sha1: str, units: str, extents) -> dict:
    k = UNITS_K[units]
    q = 0.01
    origin = [math.floor(extents[0]), math.floor(extents[1])] if extents else [0.0, 0.0]
    items = W['items']
    by_key = {d['k']: d for d in items if d['t'] == 'INSERT'}
    layers: list[str] = []
    lidx: dict[str, int] = {}
    eids: list[str] = []
    eidx: dict[str, int] = {}
    out = {'key': [], 'layer': [], 'type': [], 'first': [], 'count': [], 'sig': [], 'rsig': [], 'eid': []}
    pts: list[int] = []

    def element_of(d):
        comps = d['k'].split('@')[0].split('/')
        chain = names.split_path(d['path']) + ([d['name']] if d['t'] == 'INSERT' else [])
        depth = names.element_depth(chain)
        if depth is None:
            return None, None
        ek = '/'.join(comps[:depth + 1])
        return names.element_id(chain), by_key.get(ek)

    def emit(d, typ, P, sig, rsig, eid):
        if d['lay'] not in lidx:
            lidx[d['lay']] = len(layers)
            layers.append(d['lay'])
        out['key'].append(d['k'])
        out['layer'].append(lidx[d['lay']])
        out['type'].append(typ)
        out['first'].append(len(pts) // 2)
        out['count'].append(len(P))
        out['sig'].append(sig)
        out['rsig'].append(rsig)
        out['eid'].append(eid)
        for x, y in P:
            pts.append(round((x - origin[0]) / q))
            pts.append(round((y - origin[1]) / q))

    def simplified(P, closed):
        P = [(x * k, y * k) for x, y in P]
        if len(P) >= 3:
            ring = P + [P[0]] if closed and P[0] != P[-1] else P
            s = list(LineString(ring).simplify(0.005, preserve_topology=False).coords)
            if closed and len(s) > 1 and s[0] == s[-1]:
                s = s[:-1]
            if len(s) >= 2:
                P = s
        return P

    for d in items:
        eid_s, el = element_of(d)
        if eid_s is not None and eid_s not in eidx:
            eidx[eid_s] = len(eids)
            eids.append(eid_s)
        eid = eidx[eid_s] if eid_s is not None else -1
        sig = keys.sig(d, k)
        rsig = keys.rsig(d, el, k) if eid_s is not None and el is not None else ''
        if d['t'] == 'INSERT':
            emit(d, 5, [(d['ins'][0] * k, d['ins'][1] * k)], sig, rsig, eid)
        elif d['t'] in ('TEXT', 'MTEXT', 'ATTRIB'):
            emit(d, 4, [(d['ins'][0] * k, d['ins'][1] * k)], sig, rsig, eid)
        elif 'loops' in d:
            for loop in d['loops']:
                if loop:
                    emit(d, 2 if d.get('solid') else 3, simplified(loop, True), sig, rsig, eid)
        elif d.get('pts'):
            emit(d, 1 if d.get('closed') else 0, simplified(d['pts'], bool(d.get('closed'))), sig, rsig, eid)
    return {'format': 'plan-geometry/1', 'source': sha1, 'units': units, 'origin': [float(origin[0]), float(origin[1])],
            'quantum': q, 'layers': layers, 'items': out, 'elementIds': eids, 'pts': pts}


def gz(obj) -> bytes:
    raw = json.dumps(obj, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode('utf-8')
    return gzip.compress(raw, compresslevel=6, mtime=0)
