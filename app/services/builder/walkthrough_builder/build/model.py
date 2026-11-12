"""The second half of the port of bank_test/src/build_model.py (lines 1083 - 1278): the offset, the parts cleaned into
the model frame, the opening records and the Walk probes, the self-check, the collider skins, the rooms, the furniture
boxes, model.json (keys in the bank's order) and the summary (exactly bank_summary.json's structure: U-10.8). Unchanged
in arithmetic and order; the offset is the bank rule unless the settings pin one (U-9.6); the model's floors carry
`sheetShift` only when it is not zero and the plinth floor's `slabThickness` is its level (U-9.3, U-9.5).
"""
from __future__ import annotations

import collections
import math
import re

from shapely.geometry import LinearRing, LineString, Point, Polygon
from shapely.ops import split as _split
from shapely.ops import unary_union

from . import furniture as FU
from .bank import CUT_MARGIN, R3, axis_of, clean, fk, polys, rect, unit
from .errors import BuildError

BLOCKING = ('wall', 'column', 'glass', 'single', 'railing', 'sill', 'parapet', 'mullion')
SKIN = 0.08
MIN_AREA = {'slab': 1.0, 'glass': 0.0002, 'mullion': 0.0002, 'lintel': 0.002, 'sill': 0.002}
MAX_GAP = 5e-4              # m: the 3ds Max script refuses a hole this close to its outline or to another hole (U-11.5)
MAX_CUTS = 64               # at most this many cuts per part (a guard; one is the rule)


def _max_problem(r) -> int | None:
    """The index of a hole the 3ds Max script would refuse (out/maxscript.py: within 0.5 mm of the outline, or of
    another hole: Extrude cannot cap it), or None."""
    if not r['h']:
        return None
    outer = LinearRing(r['o'])
    rings = [LinearRing(h) for h in r['h']]
    for i, h in enumerate(rings):
        if h.distance(outer) < MAX_GAP:
            return i
    for i in range(len(rings)):
        for j in range(i + 1, len(rings)):
            if rings[i].distance(rings[j]) < MAX_GAP:
                return i
    return None


def max_safe(rings: list[dict], min_area: float) -> list[dict]:
    """Cleaned outlines ({o, h}, model frame) the 3ds Max script can extrude: a part with a hole that touches its outline
    or another hole at a point (the tower: a wall network per floor) is cut in two along a line through that hole
    (vertical, else horizontal), as often as needed. Valid shapely polygons, but Max's Extrude cannot cap them, and the
    generator refuses the model (U-11.5). Nothing changes when no hole touches (the bank)."""
    out, todo, cuts = [], list(rings), 0
    while todo:
        r = todo.pop(0)
        i = _max_problem(r)
        if i is None or cuts >= MAX_CUTS:
            out.append(r)
            continue
        cuts += 1
        g = Polygon(r['o'], r['h'])
        c = Polygon(r['h'][i]).representative_point()
        x0, y0, x1, y1 = g.bounds
        pieces = []
        for line in (LineString([(c.x, y0 - 1.0), (c.x, y1 + 1.0)]), LineString([(x0 - 1.0, c.y), (x1 + 1.0, c.y)])):
            pieces = polys(_split(g, line))
            if len(pieces) > 1:
                break
        if len(pieces) < 2:
            out.append(r)
            continue
        todo[:0] = clean(pieces, min_area, 0.0, 0.0)
    return out


def assemble(floors, X, parts_geo, built, log) -> dict:
    """-> {model, summary, cx, cy, parts, counts, single_parts, openings, furniture, furn_kinds, furn_pieces, perm,
    furn_report, rooms_out, skins}."""
    slabs = [p for _, k, p, *_ in parts_geo if k == 'slab']
    allp = unary_union(slabs) if slabs else unary_union([p for _, _, p, *_ in parts_geo])
    if allp.is_empty:
        raise BuildError('build_failed', 'nothing was built: no walls, glass or floor plates were found on any floor '
                         '(check the layer roles and the floor areas)', step='walls')
    if X.options['offset'] == 'auto':
        minx, miny, maxx, maxy = allp.bounds
        cx, cy = round((minx + maxx) / 2, 3), round((miny + maxy) / 2, 3)
    else:
        cx, cy = X.options['offset']
    parts, counts = [], collections.defaultdict(collections.Counter)
    single_parts = []                                  # (index into parts, floor key)
    n_cut = 0
    for key, kind, p, z0, z1, follow, label, ex in parts_geo:
        min_area = MIN_AREA.get(kind, 0.002)
        rings = clean([p], min_area, cx, cy)
        if any(r['h'] for r in rings):
            safe = max_safe(rings, min_area)
            n_cut += len(safe) - len(rings)
            rings = safe
        for r in rings:
            q = Polygon(r['o'], r['h'])
            if not q.is_valid:
                raise BuildError('build_failed', f'a {kind} part of {key} is not a valid outline after rounding', step='walls')
            parts.append({'floor': key, 'kind': kind, 'z0': R3(z0), 'z1': R3(z1), 'follow': follow, **r,
                          **({'label': label} if label else {}), **{k: v for k, v in ex.items() if not k.startswith('_')}})
            counts[key][kind] += 1
            if ex.get('_single'):
                single_parts.append((len(parts) - 1, key))

    plates_by = {k: [Polygon(p['o'], p['h']) for p in parts if p['floor'] == k and p['kind'] == 'slab'] for k in built}
    inside = lambda k, x, y: any(pl.contains(Point(x - cx, y - cy)) for pl in plates_by[k])  # noqa: E731
    openings, probes = [], []
    heads_by_family = collections.defaultdict(lambda: collections.Counter())
    for F in floors:
        key = F['cfg']['key']
        for r in built[key]['recs']:
            o, a, u, nrm, w = r['o'], r['a'], r['u'], r['n'], r['w']
            mx, my = a[0] + u[0] * w / 2, a[1] + u[1] * w / 2
            sides = [inside(key, mx + nrm[0] * s * 0.6, my + nrm[1] * s * 0.6) for s in (1, -1)]
            rec = {'id': o['id'], 'floor': key, 'kind': o['kind'], 'subtype': o['subtype'], 'x': R3(mx - cx), 'y': R3(my - cy),
                   'nx': R3(nrm[0]), 'ny': R3(nrm[1]), 'width': R3(w), 'wallThickness': R3(r['t']),
                   'eitherKind': o.get('eitherKind', False), 'inside': [s for s, ok in zip((1, -1), sides) if ok]}
            if o['kind'] == 'door':
                rec.update(head=R3(r['head']), headFrom=r['headFrom'], lintel=r['lintel'],
                           lintelTop=R3(r['lintelTop']) if r['lintelTop'] else None, glassDoor=r['glassDoor'],
                           liftDoor=r['liftDoor'], jambs=[j[0] for j in r['jambs']])
                if rec['lintelTop'] is None:
                    del rec['lintelTop']                 # nothing above the head: the schema's lintelTop is a number or absent
                if r.get('depth'): rec['lintelDepth'] = [R3(r['depth'][0]), R3(r['depth'][1])]
                for fam in sorted({FU.family(nm) for nm in r['blocks']} or {'(no door block in the opening)'}):
                    heads_by_family[(fam, r['head'], r['headFrom'])][key] += 1
            if o['kind'] == 'window':
                rec.update(sill=R3(r['sill']), head=R3(r['head']), curtain=r['curtain'], paneOffset=R3(r['offset']))
                off = r['offset']
                probes.append({'floor': key, 'id': o['id'], 'what': 'window pane', 'x': R3(mx + nrm[0] * off - cx),
                               'y': R3(my + nrm[1] * off - cy), 'nx': rec['nx'], 'ny': rec['ny'], 'inside': rec['inside']})
            openings.append(rec)
        for p in parts:
            if p['floor'] != key or p['kind'] != 'glass' or p['z0'] > 0.01 or (p.get('label') or '').startswith(key): continue
            if p.get('label') and (p['label'].endswith(' pane') or p['label'].endswith(' transom')): continue
            g = Polygon(p['o'], p['h'])
            mrr = g.minimum_rotated_rectangle
            cs = list(mrr.exterior.coords)[:4]
            e1, e2 = math.dist(cs[0], cs[1]), math.dist(cs[1], cs[2])
            if max(e1, e2) < 0.6 or min(e1, e2) > 0.2: continue
            a0, a1 = (cs[0], cs[1]) if e1 >= e2 else (cs[1], cs[2])
            uu = unit((a1[0] - a0[0], a1[1] - a0[1])); nn = (-uu[1], uu[0])
            c = g.representative_point()
            side = [s for s in (1, -1) if inside(key, c.x + cx + nn[0] * s * 0.7, c.y + cy + nn[1] * s * 0.7)]
            what = 'glass partition' if p.get('label') and p['label'] != 'glass screen' else ('glass screen' if p.get('label') else 'curtain-wall glass')
            probes.append({'floor': key, 'id': f'{key} glass {len(probes) + 1}', 'what': what, 'x': R3(c.x), 'y': R3(c.y),
                           'nx': R3(nn[0]), 'ny': R3(nn[1]), 'inside': side, 'top': p['z1'], 'label': p.get('label')})
    for rec in openings:
        if rec['kind'] in ('door', 'passage'):
            rec['exterior'] = len(rec['inside']) == 1
    # a probe with floor on neither side cannot be walked at (the schema wants a side): left out, counted
    n_probes = len(probes)
    probes = [p for p in probes if p['inside']]
    if n_cut:
        log(f'{n_cut} part(s) added by cutting parts through a hole that touched their outline (the 3ds Max script '
            f'cannot extrude those)')
    if len(probes) < n_probes:
        log(f'{n_probes - len(probes)} glass probe(s) with no floor on either side left out')

    blockers = collections.defaultdict(list)
    for p in parts:
        if p['kind'] in BLOCKING and p['z0'] < 1.5:
            blockers[p['floor']].append(Polygon(p['o'], p['h']))
    blocked = []
    for rec in openings:
        if rec['kind'] not in ('door', 'passage'): continue
        ux, uy = rec['ny'], -rec['nx']
        h = rec['width'] / 2 * 0.8
        a0 = (rec['x'] - ux * h, rec['y'] - uy * h)
        zone = (rect(a0, (ux, uy), 0, 2 * h, -(rec['wallThickness'] / 2 + CUT_MARGIN), rec['wallThickness'] / 2 + CUT_MARGIN)
                if rec['kind'] == 'door' else LineString([a0, (rec['x'] + ux * h, rec['y'] + uy * h)]))
        hits = [g for g in blockers[rec['floor']] if g.intersects(zone) and (zone.geom_type == 'LineString' or g.intersection(zone).area > 1e-5)]
        if hits: blocked.append((rec['id'], rec['kind'], len(hits)))
    log(f'self-check: doors and passages with something solid across them: {blocked or "none"}')

    skins = collections.defaultdict(list)
    for p in parts:
        if p['kind'] not in BLOCKING or p['z0'] >= 1.5: continue
        g = Polygon(p['o'], p['h'])
        thin = g.difference(g.buffer(-SKIN / 2, join_style='mitre').buffer(SKIN / 2, join_style='mitre'))
        thin = [q for q in polys(thin) if q.area > 0.0002 and q.length > 0.12]
        if not thin: continue
        for r in clean([unary_union(thin).buffer(0.035, join_style='mitre')], 0.0005, 0, 0):
            skins[p['floor']].append({**r, 'z0': p['z0'], 'z1': R3(min(p['z1'], 2.0)), 'glass': p['kind'] == 'glass'})

    rooms_out = []
    for k, B in built.items():
        for r in B['rooms']:
            # the new rule's names carry their area as a number (R-3.4: the written area, comma decimals read, else the
            # room's area when the name is alone in its room); the old rule reads the number off the tag line, as before
            area = r['areaValue'] if 'areaValue' in r else (
                float(re.match(r'[\d.]+', r['area']).group()) if r['area'] and re.match(r'[\d.]+', r['area']) else None)
            rooms_out.append({'floor': k, 'name': r['name'], 'label': r['name'] + (f" · {r['area']}" if r['area'] else ''),
                              'area': area,
                              'x': R3(r['x'] - cx), 'y': R3(r['y'] - cy),
                              **({'space': r['space']} if r.get('space') else {})})   # v2: the room the name belongs to
    flat = lambda segs, nd=3: [round(v - (cx if i % 2 == 0 else cy), nd) for s in segs for i, v in enumerate(s)]  # noqa: E731

    # Rule 12: the furniture boxes, worked out in drawing coordinates, merged floor by floor, then into the model frame.
    keys = [F['cfg']['key'] for F in floors]
    furn_pieces, furn_report = [], {}
    try:
        for F in floors:
            k = F['cfg']['key']
            solid = unary_union([Polygon(p['o'], p['h']) for p in parts if p['floor'] == k and p['kind'] in ('wall', 'column')])
            ps, rep = FU.furniture_of(F, X, solid, (cx, cy))
            ps, rep['fronts'] = fk.merge_fronts(ps)
            furn_pieces += ps; furn_report[k] = rep
        for p in furn_pieces: p['x'], p['y'] = p['x'] - cx, p['y'] - cy
        furniture, furn_kinds = fk.finish(furn_pieces, keys, X.FURN.get('heights'), X.FURN.get('bases'), openings)
    except ValueError as e:
        raise BuildError('bad_settings', f'the furniture settings: {e}', step='furniture') from e
    if X.options.get('slabs') == 'network':
        # The new rules (the owner, 12 Nov): chairs and stools do not stop the walker by default (around desks and
        # counters they left no way through); the viewer's "stops" tick still makes them. The old rule keeps every kind
        # as the office table says, so a version built the old way stays byte for byte.
        furn_kinds = [{**k, 'blocks': False} if k['key'] == 'seat' else k for k in furn_kinds]
    perm = FU.finish_order(furn_pieces, keys)
    approach = {k: {'pieces': sum(1 for p in furniture if p['floor'] == k and p['approach']),
                    'openingIds': sorted({o for p in furniture if p['floor'] == k for o in p['approach']})} for k in furn_report}
    S = X.settings
    model = {
        'project': S['project']['name'], 'shortName': S['project'].get('shortName') or S['project']['name'],
        'projectNo': S['project'].get('projectNo'),
        'source': X.source_names,
        'units': 'm', 'offset': [cx, cy], 'photoName': S['project'].get('photoName') or 'Model',
        'maxPrefix': S['project'].get('maxPrefix') or 'M',
        'floors': [{'key': F['cfg']['key'], 'name': F['cfg']['name'], 'level': F['cfg']['level'], 'wallHeight': F['cfg']['wallHeight'],
                    'slabThickness': F['cfg']['level'] if F.get('plinth') else F['slabThickness'],
                    **({'sheetShift': F['sheetShift']} if F.get('sheetShift') else {})} for F in floors],
        'railingHeight': X.DEF['railingHeight'], 'singleLineHeight': X.DEF['singleLineHeight'], 'doorHeadDefault': X.DEFAULT_HEAD,
        'parts': parts,
        'stairs': {k: {'below': flat(B['stairs']), 'above': flat(B['above'])} for k, B in built.items()},
        'voids': {k: [{'what': w, 'x': R3(v.representative_point().x - cx), 'y': R3(v.representative_point().y - cy),
                       'area': round(v.area, 2)} for w, v in B['voids']] for k, B in built.items()},
        'closures': {k: [{'object': c['object'], 'width': c['width'], 'x': R3(c['poly'].centroid.x - cx),
                          'y': R3(c['poly'].centroid.y - cy)} for c in B['closures']] for k, B in built.items()},
        'stairOutlines': {k: [{'x': R3(s['hull'].representative_point().x - cx), 'y': R3(s['hull'].representative_point().y - cy),
                               'bbox': [R3(v - (cx if i % 2 == 0 else cy)) for i, v in enumerate(s['hull'].bounds)],
                               'flights': len(s['flights']), 'withWord': sum(1 for f in s['flights'] if f['dir'])}
                              for s in B['S']['stairs']] for k, B in built.items()},
        'rooms': rooms_out, 'openings': openings, 'probes': probes, 'colliderSkins': skins,
        'furnitureKinds': furn_kinds, 'furniture': furniture,
    }
    if X.options.get('slabs') == 'network':
        # BuiltModel v2 (docs/rooms/DESIGN.md R-12.1, R-3.4, R-8.5): `stairways` (always, [] when no stair climbs: the
        # v2 mark) from R2's StairsResult, and `spaces`, one record per room, named or not, in the model frame.
        pt = lambda p: [R3(p[0] - cx), R3(p[1] - cy)]  # noqa: E731
        model['stairways'] = [{**sw, 'bottom': pt(sw['bottom']), 'top': pt(sw['top']), 'walk': [pt(p) for p in sw['walk']]}
                              for B in built.values() for sw in B.get('stairways') or []]
        spaces = []
        for k, B in built.items():
            for s in B.get('spaces') or []:
                rings = clean([s['poly']], 0.5, cx, cy)
                if not rings: continue
                r = max(rings, key=lambda q: Polygon(q['o'], q['h']).area)
                spaces.append({'id': s['id'], 'floor': k, **r, 'area': s['area'], 'name': s['name'], 'names': list(s['names']),
                               'source': s['source'], 'ceiling': s['ceiling']})
        model['spaces'] = spaces
        kept = {s['id'] for s in spaces}
        for r in rooms_out:
            if r.get('space') not in kept: r.pop('space', None)

    summary = {'floors': {}, 'doorHeads': [], 'offset': [cx, cy]}
    for F in floors:
        k = F['cfg']['key']; B = built[k]
        ops = [o for o in openings if o['floor'] == k]
        gw_types = collections.Counter(g['type'] for g in B['GWc'])
        summary['floors'][k] = {
            'items': len(F['items']), 'layers': F['n_layers'], 'counts': dict(counts[k]),
            'wallSources': {'fills': F['n']['fills'], 'outlines': F['n']['thin'], 'pairings': F['n']['pairs'], 'lines': F['n']['segs'],
                            'curved': F['n']['curved'], 'roomOutlinesLeftOut': F['n']['wide']},
            'openings': dict(collections.Counter(o['kind'] for o in ops)),
            'doorsWith': dict(collections.Counter(o['lintel'] or 'no lintel' for o in ops if o['kind'] == 'door')),
            'transoms': {o['id']: o['lintelTop'] for o in ops if o.get('lintel') == 'transom'},
            'exterior': [o['id'] for o in ops if o.get('exterior')],
            'rooms': [r['name'] for r in B['rooms']], 'notRoomNames': B['skipped'],
            'railingsLeftOut': B['rails_dropped'], 'stairRailsOffTheFloor': B['rails_off'], 'grid': F['grid'],
            'glassWalls': {'elements': F['n']['glassWallTypes'], 'panes': len(B['GWc']), 'types': dict(gw_types),
                           'heights': sorted({g['height'] for g in B['GWc'] if g['height']}),
                           'length': round(sum(math.dist(*axis_of(g['pane'])[:2]) for g in B['GWc'] if not g['pane'].is_empty), 1),
                           'screens': len(B['screens']), 'posts': len(B['posts'])},
            'parapets': [{'length': round(p.length / 2, 1), 'bbox': [R3(v) for v in p.bounds]} for p in B['parapets']],
            'closures': [{'object': c['object'], 'width': c['width'], 'bbox': [R3(v) for v in c['poly'].bounds]} for c in B['closures']],
            'voids': [{'what': w, 'area': round(v.area, 1), 'bbox': [R3(x) for x in v.bounds]} for w, v in B['voids']],
            'plate': B['plate_report'],
            'stairs': {'stairs': len(B['S']['stairs']), 'flights': sum(len(s['flights']) for s in B['S']['stairs']),
                       'flightsWithWord': [{'dir': f['dir'], 'risers': f['risers']} for s in B['S']['stairs'] for f in s['flights'] if f['dir']],
                       'steps': len(B['S']['steps']), 'riser': R3(B['S'].get('riser', 0)), 'words': B['S'].get('words', 0)},
            'wallArea': round(sum(Polygon(p['o'], p['h']).area for p in parts if p['floor'] == k and p['kind'] in ('wall', 'column')), 2),
            'plateArea': round(sum(Polygon(p['o'], p['h']).area for p in parts if p['floor'] == k and p['kind'] == 'slab'), 1),
            'stairLines': len(B['stairs']), 'stairAboveLines': len(B['above']),
            'stairLinesInDrawing': B['stairs_all_below'], 'stairAboveLinesInDrawing': B['stairs_all_above'],
        }
    for (fam, head, how), by in sorted(heads_by_family.items(), key=lambda x: (-x[0][1], x[0][0])):
        summary['doorHeads'].append({'family': fam, 'head': R3(head), 'from': how, **{k: v for k, v in by.items()}})
    summary['dominantHead'] = X.DOMINANT
    summary['blocked'] = blocked
    # float keys as JSON writes them (repr), so the summary equals bank_summary.json in memory too
    summary['namedHeads'] = {repr(k): v for k, v in collections.Counter(R3(h) for h in X.named).items()}
    kind_order = [k['key'] for k in furn_kinds]
    summary['furniture'] = {'pieces': len(furniture), 'kinds': {k['key']: k['count'] for k in furn_kinds}, 'floors': {}}
    for k, rep in furn_report.items():
        mine = collections.Counter(p['kind'] for p in furniture if p['floor'] == k)
        summary['furniture']['floors'][k] = {'pieces': sum(mine.values()), 'kinds': {c: mine[c] for c in kind_order if mine[c]},
                                             'approach': {'pieces': approach[k]['pieces'], 'openings': len(approach[k]['openingIds']),
                                                          'openingIds': approach[k]['openingIds']}, **rep}
    return {'model': model, 'summary': summary, 'cx': cx, 'cy': cy, 'parts': parts, 'counts': counts,
            'single_parts': single_parts, 'openings': openings, 'furniture': furniture, 'furn_kinds': furn_kinds,
            'furn_pieces': furn_pieces, 'perm': perm, 'furn_report': furn_report, 'rooms_out': rooms_out,
            'allp': allp, 'blocked': blocked}

