"""overlay.json (BuildOverlay) and the flags of the check screen (docs/upload/DESIGN.md U-12.2; upload-contracts.ts
section 4).

Per floor, in THAT floor's sheet coordinates (sheet = model + toSheet, toSheet = the model offset + the floor's
sheetShift, from `BuildResult.floors_frame`): the parts' footprints (no slabs), the slabs, the model's openings (a, b from
the detector record they came from, which is in drawing metres = sheet coordinates; else from the model opening), the
furniture boxes, the room names and the keys of the items set aside. Flags (`Flag`), one per thing to look at:

| kind | from | severity |
| opening | a detector record that became a model opening: a passage; confidence <= 0.55; eitherKind; host none or line
|           work; evidence "ends from the swing"; a door with sidelights | check |
| single-line | each `single` part (report.floors[k].singles) | check |
| lost | each lost block insert inside the floor's area (report.floors[k].lost) | check |
| outline-wall, outline-glass | each outline suggestion still open (report.floors[k].outlineSuggestions) | check |
| grey-furniture | each family the kit classified `other`, with its count | info |
| rail-left-out, room-label, plate-dropped | report.floors[k].railsLeftOut, roomLabels, platesDropped | info |
| plate-dropped | a large area inside the walls with no floor plate (`unfloored_flags`, UR) | check |
| room-label | 3+ texts like room names inside the plate on a layer set to ignore / other (`room_name_flags`, UR) | check |
| alignment | spread over 5 mm, one grid direction only (report.floors[k].alignment) | check |
| units | a source whose declared units the door votes overruled (its drawing.json, through BuildContext) | check |
| fix-unmatched | a remembered fix that matched nothing, or more than one item (report.fixes) | check |
| detector-skipped | the detector skipped its frame-only sliding units on a floor (detector.frameRowsSkipped) | check |
| slow | the detector took over 60 s on a floor (detector.slow) | info |

Flag ids are `<kind>:<floor or ->:<12 hex of what it is about>`: the same drawing and settings give the same ids. Every
title and detail may quote drawing names: they are plain text for the check screen (textContent / fillText).

The rooms milestone (docs/rooms/DESIGN.md R-6.1, R-12.4; R3): a floor built with the new rule (its report carries
`slab`) gets the floor fields `spaces` (the model's, in sheet m), `holes` (the cut ones), `stairs`, `closings`,
`unfloored` (the report's rows, already in the floor's sheet frame), and, after every flag above, its new flags:

| kind | from | severity |
| slab-gap | the walls never close round the floor (plate0 under half the walls' hull, 100 m2 short); an unfloored area of 4 m2
|            or more that staff have not answered (with its mouth's two ends in `ref` when it has one) | check |
| room-open | a name in no room; a closed area of over 150 m2 with no door (rooms.open) | check |
| room-names | a room with two names or more (rooms.several) | info |
| doorway | each doorway closing (slab.closings) | info |
| stair | each stair group kept as lines (stairways), its own text | the row's |
| stairs-none | two floors of a stack next to each other that no climbable stair joins (with `stairs: 'climb'`) | check |
| stair-clash | the parts of a floor cut under a stair, one flag per stair (stairClash) | info |
| hole-skipped | an X void on the lowest floor (info); an X shape too large to cut by itself (check) (slab.holes) | info/check |
| fix-unmatched | also a closing, room or stair fix that matched nothing (fixes.closings / rooms / stairs) | check |

`plate-dropped` is the old rule's only: a floor built with the new rule raises none (its stored text is unchanged).
"""
from __future__ import annotations

import gzip
import hashlib
import json
import re
from pathlib import Path
from typing import Any

ALIGN_SPREAD = 0.005          # m: an alignment whose largest residual is over 5 mm is flagged
LOW_CONFIDENCE = 0.55
UNIT_WORDS = {'mm': 'millimetres', 'cm': 'centimetres', 'm': 'metres', 'in': 'inches', 'ft': 'feet'}


def _r(v: float, nd: int = 4) -> float:
    return round(v, nd) + 0.0


def flag(kind: str, floor: str | None, what: Any, severity: str, title: str, detail: str, at=None, bbox=None,
         ref: dict | None = None) -> dict:
    h = hashlib.sha1(json.dumps(what, sort_keys=True, ensure_ascii=False).encode('utf-8')).hexdigest()[:12]
    return {'id': f'{kind}:{floor if floor is not None else "-"}:{h}', 'kind': kind, 'floor': floor, 'severity': severity,
            'title': title, 'detail': detail, 'at': at, 'bbox': bbox, 'ref': ref or {}}


def _mid(a, b) -> list[float]:
    return [_r((a[0] + b[0]) / 2, 3), _r((a[1] + b[1]) / 2, 3)]


def _bbox(points) -> list[float] | None:
    pts = list(points)
    if not pts:
        return None
    return [_r(min(p[0] for p in pts), 3), _r(min(p[1] for p in pts), 3), _r(max(p[0] for p in pts), 3), _r(max(p[1] for p in pts), 3)]


def opening_reasons(r: dict) -> list[str]:
    """Why a detector record is worth a look (U-12.2), in plain words; empty: nothing to check."""
    why = []
    if r.get('kind') == 'passage':
        why.append('a passage')
    if isinstance(r.get('confidence'), (int, float)) and r['confidence'] <= LOW_CONFIDENCE:
        why.append(f'confidence {r["confidence"]}')
    if r.get('eitherKind'):
        why.append('a door or a window')
    if r.get('host') in ('none', 'line work'):
        why.append(f'host {r["host"]}')
    if any('ends from the swing' in str(e) for e in r.get('evidence') or []):
        why.append('ends from the swing')
    if r.get('kind') == 'door' and r.get('sidelights'):
        why.append('sidelights')
    return why


def _read_json(path: str | None) -> Any:
    if not path:
        return None
    p = Path(path)
    if not p.exists():
        return None
    data = p.read_bytes()
    if data[:2] == b'\x1f\x8b':
        data = gzip.decompress(data)
    return json.loads(data.decode('utf-8'))


def units_flags(ctx: dict) -> list[dict]:
    """A `units` flag per source whose declared units were overruled by the door votes (drawing.json of BuildContext)."""
    out = []
    for s in ctx.get('sources') or []:
        try:
            dr = _read_json(s.get('drawing'))
        except (OSError, ValueError):
            dr = None
        u = (dr or {}).get('units') or {}
        declared, used, verdict = u.get('declared'), u.get('used') or s.get('units'), u.get('verdict')
        if verdict == 'votes-win' or (declared and used and declared != used):
            votes = u.get('votes') or {}
            vote_txt = ', '.join(f'{k} {v}' for k, v in votes.items() if v)
            out.append(flag('units', None, {'source': s['sha1'], 'declared': declared, 'used': used}, 'check',
                            f'{s["name"]}: read in {UNIT_WORDS.get(used, used)}, not the {UNIT_WORDS.get(declared, declared)} '
                            f'its header declares',
                            f'The door symbols measure right in {UNIT_WORDS.get(used, used)} (door votes: {vote_txt or "none"}). '
                            f'{u.get("note") or ""} Check the units on the Files step.'.strip(),
                            None, None, {}))
    return out


def overlay(result: dict, ctx: dict) -> dict:
    """BuildOverlay of a build: per floor in its sheet coordinates, and every flag (U-12.2)."""
    M = result['model']
    report = result['report']
    settings = (ctx.get('spec') or {}).get('settings') or {}
    fixes = settings.get('fixes') or {'setAside': [], 'openings': [], 'outlineEdges': []}
    floors, flags, rooms_flags_ = [], [], []
    model_floors = [f['key'] for f in M['floors']]
    names = {f['key']: f['name'] for f in M['floors']}
    for fl in model_floors:
        frame = result['floors_frame'][fl]
        tx, ty = frame['toSheet']
        sh = lambda p: [_r(p[0] + tx), _r(p[1] + ty)]                          # noqa: E731
        recs = {}
        for r in result['detector'].get(fl, []):
            if r.get('modelId'):
                recs[r['modelId']] = r
        parts = [{'i': i, 'kind': p['kind'], 'label': p.get('label'), 'o': [sh(q) for q in p['o']],
                  'h': [[sh(q) for q in hole] for hole in p.get('h', [])]}
                 for i, p in enumerate(M['parts']) if p['floor'] == fl and p['kind'] != 'slab']
        slabs = [{'o': [sh(q) for q in p['o']], 'h': [[sh(q) for q in hole] for hole in p.get('h', [])]}
                 for p in M['parts'] if p['floor'] == fl and p['kind'] == 'slab']
        openings = []
        for o in M['openings']:
            if o['floor'] != fl:
                continue
            out = recs.get(o['id'])
            r = out['record'] if out else None
            if r is not None and isinstance(r.get('a'), list) and isinstance(r.get('b'), list):
                a, b = [_r(r['a'][0]), _r(r['a'][1])], [_r(r['b'][0]), _r(r['b'][1])]
            else:
                dx, dy = o['ny'] * o['width'] / 2, -o['nx'] * o['width'] / 2
                a, b = sh((o['x'] - dx, o['y'] - dy)), sh((o['x'] + dx, o['y'] + dy))
            why = opening_reasons(r) if r is not None else []
            fixed = out is not None and out.get('fix') is not None
            openings.append({'id': o['id'], 'kind': o['kind'], 'a': a, 'b': b, 'flagged': bool(why), 'fixed': fixed})
            if why:
                flags.append(flag('opening', fl, o['id'], 'check', f'{o["id"]}: {o["kind"]} to check',
                                  'Check this opening: ' + ', '.join(why) + '.', _mid(a, b), _bbox([a, b]),
                                  {'openingId': o['id']}))
        furniture = [{'id': f['id'], 'kind': f['kind'], 'x': _r(f['x'] + tx), 'y': _r(f['y'] + ty), 'w': f['w'], 'd': f['d'],
                      'rot': f['rot']} for f in (M.get('furniture') or []) if f['floor'] == fl]
        rooms = [{'name': r['name'], 'x': _r(r['x'] + tx), 'y': _r(r['y'] + ty)} for r in M['rooms'] if r['floor'] == fl]
        rep = report['floors'].get(fl) or {}
        set_aside = []
        for _, fx, fr in fix_pairs(fixes.get('setAside'), (report.get('fixes') or {}).get('setAside')):
            # the key the fix matched in THIS drawing (U3's report row `key`, contract issues U4-2 / U3-3, settled at
            # integration): it differs from the ref's own key when the match was by element id or signature
            key = fr.get('key') or fx['key']
            if fx.get('floor') == fl and fr.get('matchedBy') and fr.get('items', 0) > 0 and key not in set_aside:
                set_aside.append(key)
        new_rule = is_new_rule(rep)
        flags += floor_flags(fl, rep, M)
        if not new_rule:                               # the old rule's flag (UR, V1-1); the new rule says slab-gap
            flags += unfloored_flags(fl, parts, slabs)
        flags += room_name_flags(fl, frame['source'], slabs, settings.get('layers') or {}, _drawing_of(ctx, frame['source']))
        floor = {'key': fl, 'source': frame['source'], 'toSheet': [tx, ty], 'area': frame['area'], 'parts': parts,
                 'slabs': slabs, 'openings': openings, 'furniture': furniture, 'rooms': rooms, 'setAside': set_aside}
        if new_rule:
            floor.update(rooms_fields(fl, rep, M, sh))
            rooms_flags_ += rooms_flags(fl, rep, M, parts, names[fl], sh)
        floors.append(floor)
    flags += grey_furniture_flags(M, result['floors_frame'])
    flags += units_flags(ctx)
    flags += fix_flags(fixes, report.get('fixes') or {})
    flags += rooms_flags_
    flags += stairs_none_flags(M, report, settings)
    return {'format': 'build-overlay/1', 'floors': floors, 'flags': flags}


def floor_flags(fl: str, rep: dict, M: dict) -> list[dict]:
    """The flags a floor's upload report raises."""
    out = []
    parts = M['parts']
    for s in rep.get('singles') or []:
        lab = (parts[s['part']].get('label') if 0 <= s.get('part', -1) < len(parts) else None)
        out.append(flag('single-line', fl, {'part': s['part'], 'keys': s['keys']}, 'check',
                        f'Single line on {s["layer"]}' + (f' ({lab})' if lab else ''),
                        f'A line on {s["layer"]} with no partner face was built as a {M.get("singleLineHeight", 1.0):.2f} m '
                        f'single-line item: a wall, a railing or an edge? Set it aside if it is none of them.',
                        _mid(s['a'], s['b']), _bbox([s['a'], s['b']]), {'keys': list(s['keys'])}))
    for lo in rep.get('lost') or []:
        out.append(flag('lost', fl, {'block': lo['block'], 'at': lo['at']}, 'check',
                        f'Lost in conversion: {lo["block"]}',
                        f'An insert of the block {lo["block"]} (on {lo.get("layer") or "an unknown layer"}) came out empty in '
                        f'the conversion: whatever it draws is missing here. Export a DXF from AutoCAD to keep it.',
                        [_r(lo['at'][0], 3), _r(lo['at'][1], 3)], None, {'family': lo['block']}))
    for sg in rep.get('outlineSuggestions') or []:
        if sg.get('state') != 'open':
            continue
        e = sg['edge']
        kind = 'outline-glass' if sg.get('kind') == 'glass' else 'outline-wall'
        out.append(flag(kind, fl, {'edge': e}, 'check',
                        f'Suggested {"glass" if kind == "outline-glass" else "wall"} along a room outline ({sg["length"]:.2f} m)',
                        f'A free edge of a room outline: build it as {"glass" if kind == "outline-glass" else "a 0.20 m wall"}, '
                        f'or refuse it.', _mid(e[0], e[-1]), _bbox(e), {'edge': [list(e[0]), list(e[-1])]}))
    for rl in rep.get('railsLeftOut') or []:
        out.append(flag('rail-left-out', fl, {'keys': rl.get('keys'), 'at': rl.get('at')}, 'info', 'A railing was left out',
                        'A line on a railing layer was left out (off the floor, or on a stair).',
                        [_r(rl['at'][0], 3), _r(rl['at'][1], 3)] if rl.get('at') else None, None,
                        {'keys': list(rl.get('keys') or [])}))
    for lab in rep.get('roomLabels') or []:
        out.append(flag('room-label', fl, lab, 'info', f'"{lab["text"]}" is not a room name',
                        'A text on a room-name layer that names no room (a tag or a code): left out of the rooms.',
                        [_r(lab['at'][0], 3), _r(lab['at'][1], 3)] if lab.get('at') else None))
    for p in ([] if is_new_rule(rep) else rep.get('platesDropped') or []):     # the old rule's only (R-6.1)
        # (UR, V1-1: these are areas the bank's closing found next to the walls, outside the rooms the walls close, not
        # areas "inside a railing"; the report row says why each was left out)
        why = f' ({p["why"]})' if p.get('why') else ''
        out.append(flag('plate-dropped', fl, {k: v for k, v in p.items() if k != 'why'}, 'info',
                        'A floor area was left out',
                        f'An area of {p["area"]} m2 next to the walls, outside the rooms they close, was left out of the '
                        f'floor plate{why}.',
                        [_r(p['at'][0], 3), _r(p['at'][1], 3)] if p.get('at') else None))
    a = rep.get('alignment') or {}
    if a.get('method') in ('grid', 'points'):
        spread = a.get('spread')
        if isinstance(spread, (int, float)) and spread > ALIGN_SPREAD:
            out.append(flag('alignment', fl, {'spread': spread, 'method': a['method']}, 'check',
                            f'{fl}: lined up within {spread * 1000:.0f} mm only',
                            f'The {"grid labels" if a["method"] == "grid" else "two points"} disagree by up to {spread * 1000:.1f} mm '
                            f'after the shift ({a["shift"][0]:.3f}, {a["shift"][1]:.3f} m): check the floor lines up, or pick '
                            f'two points.'))
        if a['method'] == 'grid' and a.get('families') == 1:
            out.append(flag('alignment', fl, {'families': 1}, 'check', f'{fl}: lined up by one grid direction only',
                            'Only one direction of grid lines is shared with the reference floor, so the shift along those '
                            'lines is not checked: pick two points if the floor sits wrong.'))
    det = rep.get('detector') or {}
    if det.get('frameRowsSkipped'):
        out.append(flag('detector-skipped', fl, {'frameRowsSkipped': det['frameRowsSkipped']}, 'check',
                        f'{fl}: sliding units by their frames were not looked for',
                        f'{det["frameRowsSkipped"]} small shapes stand against walls on this floor, so the openings detector '
                        f'skipped its frame-only sliding units. Map the tile, hatch or symbol layer that draws them to ignore, '
                        f'then build again.'))
    if det.get('slow'):
        out.append(flag('slow', fl, {'seconds': det.get('seconds')}, 'info', f'{fl}: the openings detector was slow',
                        f'Finding the openings took {det.get("seconds", 0):.0f} s on this floor. Mapping busy layers '
                        f'(hatches, symbols) to ignore makes it faster.'))
    return out


#: the unfloored-area flag (UR, V1-1): the walls closed by this radius (m), components of at least UNFLOORED_PIECE m2
#: with standing room, flagged from UNFLOORED_MIN m2 in all; or, when the walls do not close at all, a plate under
#: OPEN_SHARE of the walls' convex hull and at least OPEN_MIN m2 short of it. Measured on 9 Nov: the bank 0 / 6 m2 (its L2
#: stair, under the threshold) and plate / hull 0.97, 1.15: no flag; the house's ground floor 64 m2 (the glass-walled
#: living area), the tower 321 / 190 m2, the suite 113 of 505 m2 and the Revit suite 35 of 296 m2: flagged.
UNFLOORED_CLOSE = 1.5
UNFLOORED_PIECE = 4.0
UNFLOORED_MIN = 20.0
OPEN_SHARE = 0.5
OPEN_MIN = 100.0
UNFLOORED_DETAIL = ('The floor plate is made of the rooms the walls close (the bank\'s rule): where the walls or the '
                    'facade do not close (gaps at corners, glass that is not built, or walls on a layer that is not '
                    'built), the rooms between them get no floor and cannot be walked. Check the wall and glass layers '
                    'on the Layers step; plates from the wall network are a later option.')


def _poly(o, h):
    from shapely.geometry import Polygon
    try:
        p = Polygon(o, h or [])
    except (ValueError, TypeError):
        return None
    if not p.is_valid:
        p = p.buffer(0)
    return None if p.is_empty else p


def unfloored_flags(fl: str, parts: list[dict], slabs: list[dict]) -> list[dict]:
    """A `plate-dropped` check flag when a large area inside the floor's walls has no floor plate (UR, V1-1: the tower's
    rooms between the core and the facade, about half of each floor, had none and no flag said so)."""
    from shapely.ops import unary_union
    walls = [p for p in (_poly(x['o'], x['h']) for x in parts) if p is not None]
    if not walls:
        return []
    W = unary_union(walls)
    S = unary_union([p for p in (_poly(x['o'], x['h']) for x in slabs) if p is not None])
    C = W.buffer(UNFLOORED_CLOSE, join_style='round').buffer(-UNFLOORED_CLOSE, join_style='round')
    from shapely.geometry import Polygon
    filled = unary_union([Polygon(g.exterior) for g in getattr(C, 'geoms', [C]) if not g.is_empty])
    miss = filled.difference(S.buffer(0.3)).difference(W.buffer(0.3))
    pieces = sorted((g for g in getattr(miss, 'geoms', [miss])
                     if not g.is_empty and g.area >= UNFLOORED_PIECE and not g.buffer(-0.6).is_empty),
                    key=lambda g: -g.area)
    total = sum(g.area for g in pieces)
    if total >= UNFLOORED_MIN:
        big = pieces[0]
        c = big.representative_point()
        return [flag('plate-dropped', fl, {'unfloored': round(total)}, 'check',
                     f'{fl}: about {total:.0f} m2 inside the walls has no floor',
                     f'{len(pieces)} area{"s" if len(pieces) != 1 else ""} inside the walls, the largest {big.area:.0f} m2, '
                     f'{"have" if len(pieces) != 1 else "has"} no floor plate. ' + UNFLOORED_DETAIL,
                     [_r(c.x, 3), _r(c.y, 3)], [_r(v, 3) for v in big.bounds])]
    hull = W.convex_hull
    if hull.area >= OPEN_MIN and S.area < OPEN_SHARE * hull.area and hull.area - S.area >= OPEN_MIN:
        c = hull.representative_point()
        return [flag('plate-dropped', fl, {'open': round(hull.area), 'plate': round(S.area)}, 'check',
                     f'{fl}: the floor plate is {S.area:.0f} m2 of the about {hull.area:.0f} m2 the walls span',
                     'The walls do not close round the floor, so most of it has no floor plate. ' + UNFLOORED_DETAIL,
                     [_r(c.x, 3), _r(c.y, 3)], [_r(v, 3) for v in hull.bounds])]
    return []


def _drawing_of(ctx: dict, sha1: str) -> dict | None:
    """The drawing.json (DrawingRead) of a source of the build, through BuildContext, or None."""
    for s in ctx.get('sources') or []:
        if s.get('sha1') == sha1:
            try:
                return _read_json(s.get('drawing'))
            except (OSError, ValueError):
                return None
    return None


#: door / window tags (D1, W2, WD-01): the suggester's pattern (suggest.TAG_RE)
_TAG = re.compile(r'^[A-Z]{1,3}[-.]?\d{1,3}[A-Z]?$', re.I)
#: name-like texts on one layer inside a floor's plate before it is flagged
ROOM_NAMES_MIN = 3


def _name_like(text: str) -> bool:
    return sum(1 for ch in text if ch.isalpha()) >= 2 and not _TAG.match(text)


def room_name_flags(fl: str, source: str, slabs: list[dict], layers: dict, drawing: dict | None) -> list[dict]:
    """A `room-label` check flag per layer that is not built as room names (`ignore` or `other`) yet holds 3 or more
    texts that look like room names inside the floor's plate (UR, V2-6: the bank with its room-name layer G-ANNO-TEXT
    suggested `ignore` lost 5 of its 18 rooms and nothing said so). Texts of blocks and attributes are left out (furniture
    and tag values); title blocks and notes lie outside the plate. With the acceptance settings no floor gets one."""
    if not drawing:
        return []
    from shapely.geometry import Point
    from shapely.ops import unary_union
    plate = unary_union([p for p in (_poly(x['o'], x['h']) for x in slabs) if p is not None])
    if plate.is_empty:
        return []
    by: dict[str, list[dict]] = {}
    for t in drawing.get('texts') or []:
        layer = t.get('layer')
        role = layers.get(layer, 'other')
        if role not in ('ignore', 'other') or t.get('kind') == 'ATTRIB' or t.get('block'):
            continue
        text = str(t.get('text') or '').strip()
        if not _name_like(text) or not plate.contains(Point(float(t['x']), float(t['y']))):
            continue
        by.setdefault(str(layer), []).append(t)
    out = []
    for layer, ts in sorted(by.items()):
        if len(ts) < ROOM_NAMES_MIN:
            continue
        role = layers.get(layer, 'other')
        names_ = sorted({str(t['text']).strip() for t in ts}, key=lambda s: (len(s), s))
        shown = ', '.join(names_[:4]) + (' ...' if len(names_) > 4 else '')
        pts = [(float(t['x']), float(t['y'])) for t in ts]
        out.append(flag('room-label', fl, {'layer': layer, 'source': source, 'texts': len(ts)}, 'check',
                        f'{len(ts)} texts on {layer} look like room names',
                        f'{layer} is set to {"Ignore" if role == "ignore" else "Not built"}, so these texts name no room: '
                        f'{shown}. If they name rooms, set the layer to Room names on the Layers step and build again.',
                        [_r(pts[0][0], 3), _r(pts[0][1], 3)], _bbox(pts)))
    return out


# ------------------------------------------------------------------------------- the rooms milestone (R-6.1, R-12.4)
#: an unfloored area is flagged from this area (m2)
SLAB_GAP_MIN = 4.0
#: the parts that are no wall for the "walls never close" hull (they lie inside the floor)
NOT_WALLS = ('slab', 'ceiling', 'tread', 'landing')
#: a stairClash row's kind in words (one, several); any other kind: '<kind> piece(s)'
PIECE_WORDS = {'wall': ('wall piece', 'wall pieces'), 'lintel': ('lintel', 'lintels'), 'column': ('column', 'columns'),
               'glass': ('glass piece', 'glass pieces'), 'sill': ('sill', 'sills')}
#: why a mark was not cut -> the hole-skipped flag's severity (R1.md N-17); the other reasons are only listed
HOLE_SKIPPED = {'the lowest floor': 'info', 'over 60 m2': 'check', 'over 30 % of the floor': 'check'}
STAIR_KEYS = ('id', 'state', 'why', 'text', 'outline', 'walk', 'bottom', 'to', 'risers', 'riser')
NO_STAIR_LINES = "No stair lines were found: is the stair's layer set to Stair on the Layers step?"


def is_new_rule(rep: dict) -> bool:
    """A floor built with the new rule: its report carries the slab (contracts.FloorUploadReportRooms)."""
    return isinstance(rep.get('slab'), dict)


def _xy(p) -> list[float]:
    return [_r(p[0], 3), _r(p[1], 3)]


def rooms_fields(fl: str, rep: dict, M: dict, sh) -> dict:
    """OverlayFloor's fields of the new rule (R-12.4), sheet m: the rooms from the model (moved by `sh`), the holes cut,
    the stair groups, the closings and the unfloored areas from the report's rows, which are in the floor's sheet frame
    already (R1.md N-11)."""
    slab = rep.get('slab') or {}
    spaces = [{'id': s['id'], 'name': s.get('name') or '', 'names': list(s.get('names') or []), 'area': s['area'],
               'o': [sh(q) for q in s['o']], 'h': [[sh(q) for q in h] for h in s.get('h') or []],
               'ceiling': bool(s.get('ceiling', True)), 'source': s.get('source') or 'network'}
              for s in M.get('spaces') or [] if s['floor'] == fl]
    holes = [{'what': h['what'], 'o': [list(q) for q in h['o']], 'h': []} for h in slab.get('holes') or [] if h.get('cut') and h.get('o')]
    stairs = []
    for r in rep.get('stairways') or []:
        s = {k: r.get(k) for k in STAIR_KEYS}
        s['outline'] = s['outline'] or []
        stairs.append(s)
    closings = [{'kind': c['kind'], 'a': c['a'], 'b': c['b'], **({'fix': c['fix']} if isinstance(c.get('fix'), int) else {})}
                for c in slab.get('closings') or []]
    unfloored = [{'area': u['area'], 'o': u['o'], 'mouth': u.get('mouth') or None, 'answered': bool(u.get('answered'))}
                 for u in slab.get('unfloored') or []]
    return {'spaces': spaces, 'holes': holes, 'stairs': stairs, 'closings': closings, 'unfloored': unfloored}


def _label_point(o: list, h: list) -> list[float] | None:
    """A point of a room (sheet m) for its flag: the middle of its bounding box when that lies in the room, else a point
    inside it."""
    p = _poly(o, h)
    if p is None:
        return None
    x0, y0, x1, y1 = p.bounds
    from shapely.geometry import Point
    mid = Point((x0 + x1) / 2, (y0 + y1) / 2)
    q = mid if p.contains(mid) else p.representative_point()
    return [_r(q.x, 3), _r(q.y, 3)]


def _pieces(rows: list[dict]) -> tuple[str, int]:
    """'4 wall pieces and 1 lintel' of stairClash rows (one row per part and cut), and their number."""
    by: dict[str, int] = {}
    for c in rows:
        by[c.get('kind') or 'part'] = by.get(c.get('kind') or 'part', 0) + 1
    words_ = [f'{n} {PIECE_WORDS.get(k, (f"{k} piece", f"{k} pieces"))[0 if n == 1 else 1]}' for k, n in by.items()]
    text = ', '.join(words_[:-1]) + ' and ' + words_[-1] if len(words_) > 1 else words_[0]
    return text, len(rows)


def walls_never_close(fl: str, slab: dict, parts: list[dict]) -> dict | None:
    """The whole floor's `slab-gap` (R-2.5): plate0 under half of the walls' convex hull and 100 m2 or more short of it
    (the old rule's fallback, `unfloored_flags`, with the new rule's plate0)."""
    from shapely.ops import unary_union
    walls = [p for p in (_poly(x['o'], x['h']) for x in parts if x['kind'] not in NOT_WALLS) if p is not None]
    if not walls:
        return None
    hull = unary_union(walls).convex_hull
    plate = float(slab.get('plate') or 0.0)
    if hull.area >= OPEN_MIN and plate < OPEN_SHARE * hull.area and hull.area - plate >= OPEN_MIN:
        c = hull.representative_point()
        return flag('slab-gap', fl, {'open': round(hull.area), 'plate': round(plate)}, 'check', f'{fl}: the walls do not close',
                    f'The floor plate is {plate:.0f} m2 of the about {hull.area:.0f} m2 the walls span: check the wall and glass '
                    f'layers on the Layers step.', [_r(c.x, 3), _r(c.y, 3)], [_r(v, 3) for v in hull.bounds])
    return None


def rooms_flags(fl: str, rep: dict, M: dict, parts: list[dict], floor_name: str, sh) -> list[dict]:
    """The new flags of a floor built with the new rule (R-6.1), in this order: slab-gap, room-open, room-names,
    doorway, stair, stair-clash, hole-skipped. Points are the report's (sheet m)."""
    out = []
    slab = rep.get('slab') or {}
    rooms = rep.get('rooms') or {}
    whole = walls_never_close(fl, slab, parts)
    if whole is not None:
        out.append(whole)
    for u in slab.get('unfloored') or []:
        if u.get('answered') or (u.get('area') or 0) < SLAB_GAP_MIN:
            continue
        xs, ys = [p[0] for p in u['o']], [p[1] for p in u['o']]
        mouth = u.get('mouth')
        a, b = (mouth[0], mouth[1]) if mouth else (None, None)
        out.append(flag('slab-gap', fl, {'at': u['at']}, 'check', 'No floor beside the walls',
                        f'About {u["area"]:.0f} m2 beside the walls has no floor: the walls do not close here.'
                        + ('' if a else ' Draw a line across the gap if it is inside the building, or say it is outdoors.'),
                        _mid(a, b) if a else _xy(u['at']), _bbox(zip(xs, ys)), {'a': a, 'b': b} if a else {}))
    for r in rooms.get('open') or []:
        if r.get('space'):                             # a closed area of over 150 m2 with no door (R1.md N-12)
            out.append(flag('room-open', fl, {'space': r['space'], 'at': r['at']}, 'check', 'A closed area with no door',
                            f'A closed area of {r.get("area") or 0:.0f} m2 with no door: is it floor?', _xy(r['at']), None,
                            {'room': r['space']}))
        else:                                          # a name in no room
            out.append(flag('room-open', fl, {'name': r['name'], 'at': r['at']}, 'check', f'{r["name"]}: its room is not closed',
                            f'{r["name"]}: its room is not closed (a gap in its walls). Close the gap or place the name.',
                            _xy(r['at']), None, {}))
    spaces = {s['id']: s for s in M.get('spaces') or [] if s['floor'] == fl}
    for r in rooms.get('several') or []:
        sp = spaces.get(r['space'])
        at = _label_point([sh(q) for q in sp['o']], [[sh(q) for q in h] for h in sp.get('h') or []]) if sp else None
        n = len(r['names'])
        out.append(flag('room-names', fl, {'room': r['space']}, 'info', f'{n} names in one room',
                        f'{n} names in one room: an open-plan room, or a wall between them is missing.', at, None,
                        {'room': r['space']}))
    for c in slab.get('closings') or []:
        if c['kind'] == 'doorway':
            out.append(flag('doorway', fl, {'a': c['a'], 'b': c['b']}, 'info', 'A gap closed as a doorway',
                            f'A gap of {c["width"]:.2f} m between two wall ends was closed as a doorway: no door was found here.',
                            _mid(c['a'], c['b']), None, {'a': list(c['a']), 'b': list(c['b'])}))
    for r in rep.get('stairways') or []:
        if r.get('state') == 'lines':
            out.append(flag('stair', fl, {'stair': r['id']}, r.get('severity') or 'info', 'Stair kept as lines',
                            r.get('text') or f'Stair {r["id"]}: kept as lines.', _xy(r['at']) if r.get('at') else None, None,
                            {'stair': r['id']}))
    by: dict[str, list[dict]] = {}
    for c in rep.get('stairClash') or []:
        by.setdefault(c['stair'], []).append(c)
    for sid, rows in by.items():
        cut = [c for c in rows if c.get('z1') is not None]
        gone = [c for c in rows if c.get('z1') is None]   # a piece that would be 0.05 m high or less: taken out
        if cut:
            words_, n = _pieces(cut)
            text = f'{words_} of {floor_name} under the stair {"was" if n == 1 else "were"} cut to the stair\'s underside.'
            if gone:
                w2, n2 = _pieces(gone)
                text += f' {w2} {"was" if n2 == 1 else "were"} taken out: no room under the stair.'
        else:
            w2, n2 = _pieces(gone)
            text = f'{w2} of {floor_name} under the stair {"was" if n2 == 1 else "were"} taken out: no room under the stair.'
        out.append(flag('stair-clash', fl, {'stair': sid, 'n': len(rows)}, 'info', 'Walls cut under a stair', text,
                        _xy(rows[0]['at']), None, {'stair': sid}))
    for h in slab.get('holes') or []:
        sev = None if h.get('cut') else HOLE_SKIPPED.get(h.get('why'))
        if sev == 'info':
            out.append(flag('hole-skipped', fl, {'at': h['at']}, 'info', 'A void mark was not cut',
                            'An X marks a void on the lowest floor: not cut.', _xy(h['at']), None, {}))
        elif sev == 'check':
            xs, ys = [p[0] for p in h.get('o') or []], [p[1] for p in h.get('o') or []]
            out.append(flag('hole-skipped', fl, {'at': h['at']}, 'check', 'A large void mark was not cut',
                            f'An X marks {h.get("area") or 0:.0f} m2 as a void: is it one?', _xy(h['at']), _bbox(zip(xs, ys)), {}))
    return out


def stairs_none_flags(M: dict, report: dict, settings: dict) -> list[dict]:
    """`stairs-none` (R-6.1): two floors of a stack next to each other that no climbable stair joins, when the build
    climbs stairs (`stairs: 'climb'`). A stair that passes a floor joins both pairs it passes (R2.md N-16). Read from the
    model's stairways and the floors' stairways rows: the build's own list of such pairs is not in its result. The text
    lists the stair groups kept as lines on the lower floor (else on the upper one), each with its reason."""
    if (settings.get('options') or {}).get('stairs') != 'climb' or 'stairways' not in M:
        return []
    reps = report.get('floors') or {}
    joined = {(sw['from'], sw['to']) for sw in M.get('stairways') or []}
    for key, rep in reps.items():
        joined |= {(key, r['to']) for r in rep.get('stairways') or [] if r.get('state') == 'climb' and r.get('to')}
    stacks: dict[str, list[tuple[float, int, dict]]] = {}
    for i, f in enumerate(M['floors']):
        stacks.setdefault(f.get('stack') or 'main', []).append((f['level'], i, f))
    out = []
    for fs in stacks.values():
        fs_ = [f for _, _, f in sorted(fs, key=lambda t: (t[0], t[1]))]
        idx = {f['key']: i for i, f in enumerate(fs_)}
        spans = [(idx[a], idx[b]) for a, b in joined if a in idx and b in idx]
        for i, (lo, hi) in enumerate(zip(fs_, fs_[1:])):
            if any(a <= i and i + 1 <= b for a, b in spans):
                continue
            rows = [(lo['key'], r) for r in (reps.get(lo['key']) or {}).get('stairways') or [] if r.get('state') == 'lines']
            if not rows:
                rows = [(hi['key'], r) for r in (reps.get(hi['key']) or {}).get('stairways') or [] if r.get('state') == 'lines']
            text = f'No stair between {lo["name"]} and {hi["name"]} can be climbed. ' + (
                ' '.join(r.get('text') or f'Stair {r["id"]}: kept as lines.' for _, r in rows) if rows else NO_STAIR_LINES)
            floor, at = (rows[0][0], _xy(rows[0][1]['at'])) if rows and rows[0][1].get('at') else (lo['key'], None)
            out.append(flag('stairs-none', floor, {'from': lo['key'], 'to': hi['key']}, 'check', 'No stair can be climbed', text,
                            at, None, {}))
    return out


def grey_furniture_flags(M: dict, frames: dict) -> list[dict]:
    """One info flag per family the kit could not classify (kind `other`), with its count, per floor."""
    out = []
    groups: dict[tuple[str, str], list[dict]] = {}
    for f in M.get('furniture') or []:
        if f['kind'] == 'other':
            groups.setdefault((f['floor'], f.get('family') or f.get('block') or '(no name)'), []).append(f)
    for (fl, fam), ps in groups.items():
        tx, ty = frames.get(fl, {}).get('toSheet', [0.0, 0.0])
        pts = [(p['x'] + tx, p['y'] + ty) for p in ps]
        out.append(flag('grey-furniture', fl, {'family': fam}, 'info', f'{fam}: {len(ps)} grey box{"es" if len(ps) != 1 else ""}',
                        f'The furniture kit does not know what {fam} is, so its {len(ps)} piece{"s are" if len(ps) != 1 else " is"} '
                        f'grey. Pick a kind for the family.', [_r(pts[0][0], 3), _r(pts[0][1], 3)], _bbox(pts), {'family': fam}))
    return out


def fix_pairs(fixes: list | None, reports: list | None):
    """(index, fix, its report entry) for every FixesReport entry: by the entry's `fix` index, else by position."""
    fixes, reports = fixes or [], reports or []
    for pos, fr in enumerate(reports):
        i = fr.get('fix') if isinstance(fr.get('fix'), int) and 0 <= fr['fix'] < len(fixes) else pos
        if 0 <= i < len(fixes):
            yield i, fixes[i], fr


def fix_flags(fixes: dict, rep: dict) -> list[dict]:
    """fix-unmatched: a remembered fix that matched nothing in this drawing, or more than one item (U-10.6)."""
    out = []
    for i, fx, fr in fix_pairs(fixes.get('setAside'), rep.get('setAside')):
        if fr.get('ambiguous'):
            out.append(flag('fix-unmatched', fx.get('floor'), {'setAside': i, 'key': fx.get('key')}, 'check',
                            f'Set-aside {fx.get("key")} on {fx.get("layer")} matches {fr["ambiguous"]} items',
                            f'The item set aside matches {fr["ambiguous"]} items in this drawing, so nothing was removed: pick '
                            f'again.', None, None, {'fix': i, 'keys': [fx.get('key')]}))
        elif not fr.get('matchedBy'):
            out.append(flag('fix-unmatched', fx.get('floor'), {'setAside': i, 'key': fx.get('key')}, 'check',
                            f'Set-aside {fx.get("key")} on {fx.get("layer")} matches nothing',
                            'An item set aside in an earlier build is not in this drawing (not by key, element or shape): it is '
                            'kept in the settings until you drop it.', None, None, {'fix': i, 'keys': [fx.get('key')]}))
    for i, fx, fr in fix_pairs(fixes.get('openings'), rep.get('openings')):
        if not fr.get('matched'):
            a, b = fx.get('a') or [0, 0], fx.get('b') or [0, 0]
            out.append(flag('fix-unmatched', fx.get('floor'), {'opening': i, 'a': a, 'b': b}, 'check',
                            'An opening fix matches no opening',
                            'An opening changed in an earlier build is not found here (no detected opening within 0.15 m of '
                            'both ends): it is kept in the settings until you drop it.', _mid(a, b), _bbox([a, b]), {'fix': i}))
    for i, fx, fr in fix_pairs(fixes.get('outlineEdges'), rep.get('outlineEdges')):
        if not fr.get('matched'):
            a, b = fx.get('a') or [0, 0], fx.get('b') or [0, 0]
            out.append(flag('fix-unmatched', fx.get('floor'), {'outlineEdge': i, 'a': a, 'b': b}, 'check',
                            'An outline edge fix matches no suggestion',
                            'An outline edge accepted or refused in an earlier build is not suggested here: it is kept in the '
                            'settings until you drop it.', _mid(a, b), _bbox([a, b]), {'fix': i, 'edge': [list(a), list(b)]}))
    # the rooms milestone's fixes (R-6.2, R-6.3): rows { fix, matched } of fixes.closings / rooms / stairs
    for i, fx, fr in fix_pairs(fixes.get('closings'), rep.get('closings')):
        if fr.get('matched'):
            continue
        a, b = fx.get('a') or [0, 0], fx.get('b') or [0, 0]
        m = _mid(a, b)
        if fx.get('use') == 'none':
            title = 'A removed closing is no longer there'
            detail = (f'The removed closing at ({m[0]:.2f}, {m[1]:.2f}) is no longer there: the fix is kept in the settings until '
                      f'you drop it.')
        else:
            title = 'A closing line finds no floor'
            detail = (f'The closing line at ({m[0]:.2f}, {m[1]:.2f}) is on a floor that is not in this build: it is kept in the '
                      f'settings until you drop it.')
        out.append(flag('fix-unmatched', fx.get('floor'), {'closing': i, 'a': a, 'b': b}, 'check', title, detail, m, _bbox([a, b]),
                        {'fix': i, 'a': list(a), 'b': list(b)}))
    for list_, what, title in (('rooms', 'room', 'A room fix finds no room'), ('stairs', 'stair', 'A stair fix finds no stair')):
        for i, fx, fr in fix_pairs(fixes.get(list_), rep.get(list_)):
            if fr.get('matched'):
                continue
            at = fx.get('at') or [0, 0]
            out.append(flag('fix-unmatched', fx.get('floor'), {what: i, 'at': at}, 'check', title,
                            f'The {what} fix at ({at[0]:.2f}, {at[1]:.2f}) finds no {what}: it is kept in the settings until you '
                            f'drop it.', _xy(at), None, {'fix': i}))
    return out


def flag_counts(ov: dict) -> dict[str, Any]:
    """{total, check, byKind} of an overlay's flags (BuildResultInfo.flags)."""
    by: dict[str, int] = {}
    for f in ov['flags']:
        by[f['kind']] = by.get(f['kind'], 0) + 1
    return {'total': len(ov['flags']), 'check': sum(1 for f in ov['flags'] if f['severity'] == 'check'), 'byKind': by}
