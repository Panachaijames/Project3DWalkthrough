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
| alignment | spread over 5 mm, one grid direction only (report.floors[k].alignment) | check |
| units | a source whose declared units the door votes overruled (its drawing.json, through BuildContext) | check |
| fix-unmatched | a remembered fix that matched nothing, or more than one item (report.fixes) | check |
| detector-skipped | the detector skipped its frame-only sliding units on a floor (detector.frameRowsSkipped) | check |
| slow | the detector took over 60 s on a floor (detector.slow) | info |

Flag ids are `<kind>:<floor or ->:<12 hex of what it is about>`: the same drawing and settings give the same ids. Every
title and detail may quote drawing names: they are plain text for the check screen (textContent / fillText).
"""
from __future__ import annotations

import gzip
import hashlib
import json
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
    floors, flags = [], []
    model_floors = [f['key'] for f in M['floors']]
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
        flags += floor_flags(fl, rep, M)
        floors.append({'key': fl, 'source': frame['source'], 'toSheet': [tx, ty], 'area': frame['area'], 'parts': parts,
                       'slabs': slabs, 'openings': openings, 'furniture': furniture, 'rooms': rooms, 'setAside': set_aside})
    flags += grey_furniture_flags(M, result['floors_frame'])
    flags += units_flags(ctx)
    flags += fix_flags(fixes, report.get('fixes') or {})
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
    for p in rep.get('platesDropped') or []:
        out.append(flag('plate-dropped', fl, p, 'info', 'A floor area was left out',
                        f'An area of {p["area"]} m2 inside a railing was left out of the floor plate.',
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
    return out


def flag_counts(ov: dict) -> dict[str, Any]:
    """{total, check, byKind} of an overlay's flags (BuildResultInfo.flags)."""
    by: dict[str, int] = {}
    for f in ov['flags']:
        by[f['kind']] = by.get(f['kind'], 0) + 1
    return {'total': len(ov['flags']), 'check': sum(1 for f in ov['flags'] if f['severity'] == 'check'), 'byKind': by}
