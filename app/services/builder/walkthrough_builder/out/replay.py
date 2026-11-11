"""ReplayData v1 (stages.json) from the build's ReplayInput, with fact-driven texts (docs/upload/DESIGN.md U-11.3; D-7).

Geometry, for any number of floors, as the bank builder wrote it (`bank_test/src/build_model.py` lines 1296-1346):
`lines` rounded to 3 decimals (noise to 2, at most 6,000 noise lines a floor), `pieces` flattened and rounded to 3
decimals (the rectangles the build really paired, U-10.8), `rings` and `sheet` as the build gives them. For the bank the
lines, rings and sheet equal v2's `stages.json`, and so do `source.files`, `source.layersInUse` and `source.units`.

Texts: every sentence is said only when its fact holds (ReplayFacts, U-10.8; the counts of the report's summary where it
has them): "with no shift" only when there is none, "exported from Revit" only when exportedFrom says so, "and the lift
shaft" only when one exists, "Done: <n> levels"; every floor is named (one: its name; two: "on Level 1 and Level 2";
more: "on 3 floors"), and the captions carry the placeholders {<key>level} and {<key>height} for every floor (D-7.3).
No panelIntro; stepTitles, colors and layersTitle are left to the viewer's defaults (D-7.2). Drawing names (layers,
floors, files) are quoted as text; the viewer shows them with textContent.

The rooms milestone (docs/rooms/DESIGN.md R-11): with the new rule the facts carry `rooms` (per floor: the rooms closed
and the named ones), `climbable` and `ceilings` (contracts.ReplayFactsRooms, made by the build); the finish caption adds
"N rooms closed" and "M stairs you can climb" only when they hold. Lines, pieces and rings are unchanged.
"""
from __future__ import annotations

import json
import math
from typing import Any

NOISE_LINES = 6000          # per floor: the longest lines the build sets aside, enough to read as a drawing
CATEGORIES = ('wall', 'glass', 'door', 'stair', 'railing', 'noise')
UNIT_WORDS = {'mm': 'millimetres', 'cm': 'centimetres', 'm': 'metres', 'in': 'inches', 'ft': 'feet'}


def fmt(v: int) -> str:
    return f'{v:,}'


def words(v: list[str]) -> str:
    """'A', 'A and B', 'A, B and C'."""
    v = [x for x in v if x]
    return ', '.join(v[:-1]) + ' and ' + v[-1] if len(v) > 1 else ''.join(v)


def count(n: int, word: str, plural: str | None = None) -> str:
    return f'{fmt(n)} {word if n == 1 else (plural or word + "s")}'


def _flat_lines(segs: list[list[float]], nd: int) -> list[float]:
    return [round(v, nd) for s in segs for v in s]


def _longest(segs: list[list[float]]) -> list[list[float]]:
    """The noise lines as the bank kept them: the longest NOISE_LINES (U3 gives them cut already; a longer list is cut
    here the bank's way, a stable sort by length, longest first)."""
    if len(segs) <= NOISE_LINES:
        return segs
    return sorted(segs, key=lambda q: -math.hypot(q[2] - q[0], q[3] - q[1]))[:NOISE_LINES]


def _flat_quads(quads: list[list[list[float]]]) -> list[float]:
    return [round(v, 3) for q in quads for x, y in q[:4] for v in (x, y)]


def replay_floors(replay: dict, model: dict) -> dict[str, Any]:
    """The geometry of every model floor, in the model's floor order."""
    out = {}
    for f in model['floors']:
        rf = replay['floors'][f['key']]
        cats = [c for c in CATEGORIES if rf['lines'].get(c)] + sorted(c for c in rf['lines'] if c not in CATEGORIES and rf['lines'][c])
        lines = {c: _flat_lines(_longest(rf['lines'][c]) if c == 'noise' else rf['lines'][c], 2 if c == 'noise' else 3)
                 for c in cats}
        pieces = {'wall': _flat_quads(rf['pieces'].get('wall') or [])}
        for c in sorted(rf['pieces']):
            if c != 'wall' and rf['pieces'][c]:
                pieces[c] = _flat_quads(rf['pieces'][c])
        out[f['key']] = {'sheet': [rf['sheet'][0], rf['sheet'][1]], 'lines': lines, 'pieces': pieces,
                         'rings': {c: v for c, v in rf['rings'].items()}}
    return out


def _units(facts: dict) -> str:
    by_name = {s['name']: s for s in facts['sources']}
    units = [by_name.get(f['source'], {}).get('units') for f in facts['floors']]
    units = list(dict.fromkeys(u for u in units if u)) or list(dict.fromkeys(s['units'] for s in facts['sources']))
    return ' / '.join(units) if units else 'mm'


def _align_sentence(f: dict, ref: dict) -> str:
    """How floor f was put onto the reference floor (intro)."""
    a = f.get('align') or {}
    shift = a.get('shift') or [0.0, 0.0]
    moved = abs(shift[0]) >= 0.0005 or abs(shift[1]) >= 0.0005
    spread = a.get('spread')
    within = f' within {spread * 1000:.1f} mm' if isinstance(spread, (int, float)) else ''
    how = (', with no shift' if not moved else f', moved {shift[0]:.3f}, {shift[1]:.3f} m')
    m = a.get('method')
    if m == 'grid':
        return f"{f['name']} lined up on {ref['name']} by {count(len(a.get('labels') or []), 'grid label')}{within}{how}"
    if m == 'points':
        return f"{f['name']} lined up on {ref['name']} by two points picked on both{within}{how}"
    if m == 'origin':
        return f"{f['name']} shares {ref['name']}'s origin" + ('' if not moved else how)
    return f"{f['name']} placed as drawn{how if moved else ''}"


def stages(replay: dict, model: dict, report: dict | None = None) -> dict[str, Any]:
    """stages.json (ReplayData v1) from the build's ReplayInput, its model and its report (for the per-floor item and
    layer counts of report.summary.floors, when present)."""
    facts = replay['facts']
    floors = model['floors']
    keys = [f['key'] for f in floors]
    fl_facts = {f['key']: f for f in facts['floors']}
    F = [{**f, 'align': (fl_facts.get(f['key']) or {}).get('align'), 'source': (fl_facts.get(f['key']) or {}).get('source')}
         for f in floors]
    summ = ((report or {}).get('summary') or {}).get('floors') or {}
    items = [summ.get(k, {}).get('items') for k in keys]
    layers_in_use = [summ.get(k, {}).get('layers') for k in keys]
    units = _units(facts)
    units_txt = ' / '.join(UNIT_WORDS.get(u, u) for u in units.split(' / '))
    L = facts['layersByRole']
    names = lambda *roles: ', '.join(x for r in roles for x in L.get(r, []))          # noqa: E731
    parts = facts['parts']
    ops = facts['openings']
    tot = lambda d, kind: sum((d.get(k) or {}).get(kind, 0) for k in keys)            # noqa: E731
    n_doors, n_windows, n_pass = tot(ops, 'door'), tot(ops, 'window'), tot(ops, 'passage')
    n_runs, n_cols, n_lintels = tot(parts, 'wall'), tot(parts, 'column'), tot(parts, 'lintel')
    n_glass, n_steps, n_parapets, n_rails = tot(parts, 'glass'), tot(parts, 'step'), tot(parts, 'parapet'), tot(parts, 'railing')
    n_rooms = len(model['rooms'])
    n_files = len(model['source'])
    n_furn, n_kinds = facts['furniturePieces'], facts['furnitureKinds']
    one_sheet = len({f['source'] for f in F}) < len(F)
    geo = replay_floors(replay, model)
    n_wall_pieces = sum(len(g['pieces'].get('wall', [])) // 8 for g in geo.values())
    n_glass_pieces = sum(len(g['pieces'].get('glass', [])) // 8 for g in geo.values())
    lv = lambda f: '{' + f['key'] + 'level}'                                        # noqa: E731
    ht = lambda f: '{' + f['key'] + 'height}'                                       # noqa: E731

    # ---- the Build settings card's facts
    if len(F) == 1:
        plans = f"1 plan ({F[0]['name']}) from {count(n_files, 'drawing')}, in {units_txt}"
    elif one_sheet and n_files == 1:
        plans = f"{len(F)} plans on one drawing ({' / '.join(f['name'] for f in F)}), in {units_txt}"
    elif n_files == len(F):
        plans = f"{len(F)} plans, one per drawing ({' / '.join(f['name'] for f in F)}), in {units_txt}"
    else:
        plans = f"{len(F)} plans from {count(n_files, 'drawing')} ({' / '.join(f['name'] for f in F)}), in {units_txt}"
    if facts.get('exportedFrom'):
        plans += f", exported from {facts['exportedFrom']}"
    intro = [plans]
    if all(isinstance(v, int) for v in items) and all(isinstance(v, int) for v in layers_in_use):
        intro.append(f"{' + '.join(fmt(v) for v in items)} drawing items, on {words([str(v) for v in layers_in_use])} "
                     f"layer{'s' if len(F) > 1 or layers_in_use[0] != 1 else ''} in use")
    if len(F) > 1:
        intro.append('; '.join(_align_sentence(f, F[0]) for f in F[1:]))
    intro.append(f"{count(n_doors, 'door')}, {count(n_windows, 'window')} and {count(n_pass, 'passage')} found by the "
                 f"openings detector")
    if n_furn:
        intro.append(f"{count(n_furn, 'furniture box', 'furniture boxes')} in {count(n_kinds, 'kind')}, one per piece")

    # ---- How the drawing was read
    rows: list[list[str]] = []
    if L.get('wall'):
        rows.append(['Walls', names('wall') + ' (cut fills, outlines, paired lines)'])
    if L.get('column'):
        rows.append(['Columns', names('column')])
    if L.get('glass'):
        rows.append(['Glass', names('glass') + (' (curtain wall); glass wall types on the wall layers (by their type name)'
                                                if any(model_glass_type(p) for p in model['parts']) else '')])
    if L.get('window'):
        rows.append(['Windows', names('window')])
    if L.get('screen'):
        rows.append(['Screens', names('screen') + ' (glass-like, never cut)'])
    if L.get('door'):
        rows.append(['Doors', names('door') + ' (head heights from the door names)'])
    if L.get('stair') or L.get('stair-above'):
        rows.append(['Stairs', names('stair') + (('; ' if L.get('stair') else '') + names('stair-above') + ' above the cut (faint)'
                                                 if L.get('stair-above') else '')])
    if L.get('railing'):
        rows.append(['Railings', names('railing') + f" ({model['railingHeight']:.2f} m)"])
    if L.get('room-name'):
        rows.append(['Room names', names('room-name')])
    if L.get('room-outline'):
        rows.append(['Room outlines', names('room-outline')])
    if L.get('furniture'):
        rows.append(['Furniture', names('furniture') + ' (one coloured box per piece, its height set per kind)'])
    left = names('other', 'ignore')
    grid_used = bool(L.get('grid')) and len(F) > 1
    if left:
        rows.append(['Left out', left + (' (and the grid, used only to line the levels up)' if grid_used else '')])
    elif grid_used:
        rows.append(['Left out', names('grid') + ' (the grid, used only to line the levels up)'])
    rows = [r for r in rows if r[1]]

    # ---- the captions (placeholders for every floor)
    if len(F) == 1:
        read = f"{fmt(items[0]) + ' drawing items' if isinstance(items[0], int) else 'The drawing items'} on {F[0]['name']}, read " \
               f"from {count(n_files, 'drawing')} in {units_txt}."
    elif len(F) == 2 and all(isinstance(v, int) for v in items):
        read = (f"{fmt(items[0])} drawing items on {F[0]['name']} and {fmt(items[1])} on {F[1]['name']}, read from "
                f"{count(n_files, 'drawing')} in {units_txt}.")
    else:
        total = sum(v for v in items if isinstance(v, int))
        read = f"{fmt(total)} drawing items on {len(F)} floors, read from {count(n_files, 'drawing')} in {units_txt}."
    counts = facts['counts']
    lines_of = lambda cat: sum((counts.get(k) or {}).get(cat, 0) for k in keys)          # noqa: E731
    sort = []
    if L.get('wall'):
        sort.append(f"Walls are on {names('wall')}: {count(lines_of('wall'), 'line')}.")
    else:
        sort.append('No layer is mapped to walls.')
    glassy = [x for x in (names('glass'), names('window')) if x]
    if glassy:
        sort.append(f"Glass and windows on {', '.join(glassy)}." if len(glassy) > 1 else f'Glass on {glassy[0]}.')
    if L.get('door'):
        sort.append(f"Door symbols on {count(len(L['door']), 'door layer')}.")
    if L.get('stair') or L.get('railing'):
        sort.append(('Stairs and railings' if L.get('stair') and L.get('railing') else 'Stairs' if L.get('stair') else 'Railings')
                    + ' on their own layers.')
    n_other = sum(len(L.get(r, [])) for r in ('room-name', 'grid', 'furniture', 'other', 'ignore', 'room-outline'))
    if n_other:
        sort.append(f"The {count(n_other, 'other layer')} (furniture, fittings, grid, labels and the like) build no walls"
                    + (f": the {count(n_furn, 'furniture piece')} among them become one coloured box each, the rest is left out."
                       if n_furn else '.'))
    if len(F) == 1:
        align = f"One floor, at {lv(F[0])} m: nothing to line up."
    elif len(F) == 2:
        f2, f1 = F[1], F[0]
        a = f2.get('align') or {}
        shift = a.get('shift') or [0.0, 0.0]
        moved = abs(shift[0]) >= 0.0005 or abs(shift[1]) >= 0.0005
        spread = a.get('spread')
        within = f" (within {spread * 1000:.1f} mm)" if isinstance(spread, (int, float)) else ''
        if a.get('method') == 'grid' and not moved:
            align = (f"The {count(len(a.get('labels') or []), 'grid label')} sit at the same coordinates in both "
                     f"{'plans' if one_sheet else 'drawings'}{within}, so {f2['name']} goes straight onto {f1['name']}, with no "
                     f"shift, and rises to {lv(f2)} m ({f1['name']} at {lv(f1)} m).")
        elif a.get('method') == 'grid':
            align = (f"{count(len(a.get('labels') or []), 'grid label')} match on both plans{within}, so {f2['name']} moves "
                     f"{-shift[0]:.2f}, {-shift[1]:.2f} m onto {f1['name']} and rises to {lv(f2)} m ({f1['name']} at {lv(f1)} m).")
        elif a.get('method') == 'points':
            align = (f"Two points picked on both plans put {f2['name']} onto {f1['name']}{within}"
                     + (f", moving it {-shift[0]:.2f}, {-shift[1]:.2f} m" if moved else ', with no shift')
                     + f"; it rises to {lv(f2)} m ({f1['name']} at {lv(f1)} m).")
        else:
            align = (f"{f2['name']} shares {f1['name']}'s origin, so it goes straight onto it"
                     + (f" (moved {-shift[0]:.2f}, {-shift[1]:.2f} m)" if moved else ', with no shift')
                     + f", and rises to {lv(f2)} m ({f1['name']} at {lv(f1)} m).")
    else:
        moved_any = any(abs(c) >= 0.0005 for f in F[1:] for c in ((f.get('align') or {}).get('shift') or [0.0, 0.0]))
        align = (f"The {len(F)} floors are lined up on {F[0]['name']}"
                 + (' with no shift' if not moved_any else '') + f" and rise to their levels: {' / '.join(lv(f) for f in F)} m.")
    pair = f"The wall layers give {count(n_wall_pieces, 'wall piece')}"
    pairings = [summ.get(k, {}).get('wallSources', {}).get('pairings') for k in keys]
    if all(isinstance(v, int) for v in pairings) and sum(pairings):
        pair += f" ({count(sum(pairings), 'line pairing')})"
    pair += (f" and the glass layers {count(n_glass_pieces, 'glass piece')}." if n_glass_pieces else '.')
    merge = f"The pieces merge into {count(n_runs, 'wall run')}" + (f" and {count(n_cols, 'column')}" if n_cols else '') + '.'
    cut = []
    if n_doors:
        cut.append(f"each of the {count(n_doors, 'door')} is cut out of its wall" if n_doors > 1 else 'the door is cut out of its wall')
    if n_windows:
        cut.append(f"the {count(n_windows, 'window')} get{'s' if n_windows == 1 else ''} panes")
    if n_pass:
        cut.append(f"the {count(n_pass, 'passage')} stay{'s' if n_pass == 1 else ''} as {'it is' if n_pass == 1 else 'they are'}")
    if cut:
        s = words(cut)
        merge += ' ' + s[0].upper() + s[1:] + '.'
    if len(F) == 1:
        raise_ = f"Walls rise to {ht(F[0])} m on {F[0]['name']}"
    elif len(F) == 2:
        raise_ = f"Walls rise to {ht(F[0])} m on {F[0]['name']} and {ht(F[1])} m on {F[1]['name']}"
    else:
        raise_ = f"Walls rise to {' / '.join(ht(f) for f in F)} m on the {len(F)} floors"
    if n_lintels:
        raise_ += f"; {count(n_lintels, 'lintel')} over the doors and windows"
    if n_rails or n_parapets:
        raise_ += ('; railings' if n_rails else '; the parapet' if n_parapets == 1 else '; parapets') \
                  + (' and the parapet' if n_rails and n_parapets == 1 else ' and parapets' if n_rails and n_parapets else '') \
                  + f" {model['railingHeight']:.2f} m"
    raise_ += '.'
    stairs_in = facts.get('stairs', 0) > 0 or n_steps > 0
    open_over = [x for x, on in (('the stairs', stairs_in), ('the lift shaft', facts.get('liftShaft'))) if on]
    goes_in = ['Floor plates' + (f" (open over {' and '.join(open_over)})" if open_over else '')]
    if stairs_in:
        goes_in.append('stairs')
    if n_rooms:
        goes_in.append('room names')
    finish = words(goes_in) + ' go in'
    if n_furn:
        finish += f", and last the furniture: {count(n_furn, 'coloured box', 'coloured boxes')}, one per piece, {count(n_kinds, 'kind')}"
    done = [count(len(F), 'level'), count(n_runs, 'wall run')]
    done += [x for x, n in ((count(n_lintels, 'lintel'), n_lintels), (count(n_glass, 'glass piece'), n_glass),
                            (count(n_steps, 'stair step'), n_steps), (f"{count(n_rooms, 'room')} named", n_rooms)) if n]
    # the new rule's facts (contracts.ReplayFactsRooms; docs/rooms/DESIGN.md R-11): said only when they hold
    rooms_by_floor = facts.get('rooms') if isinstance(facts.get('rooms'), dict) else {}
    n_closed = sum(int((rooms_by_floor.get(k) or {}).get('spaces') or 0) for k in keys)
    n_climb = int(facts.get('climbable') or 0)
    done += [x for x, n in ((f"{count(n_closed, 'room')} closed", n_closed), (f"{count(n_climb, 'stair')} you can climb", n_climb))
             if n]
    finish += '. Done: ' + ', '.join(done) + '.'

    files = list(model['source'])
    source: dict[str, Any] = {'files': files}
    if all(isinstance(v, int) for v in layers_in_use):
        source['layersInUse'] = layers_in_use
    source['units'] = units
    return {
        'source': source,
        'intro': intro,
        'layers': rows,
        'floors': geo,
        'captions': {'read': read, 'sort': ' '.join(sort), 'align': align, 'pair': pair, 'merge': merge, 'raise': raise_,
                     'finish': finish},
        'stats': {'doors': n_doors, 'windows': n_windows, 'passages': n_pass, 'lintels': n_lintels, 'rooms': n_rooms,
                  'runs': n_runs, 'columns': n_cols, 'steps': n_steps, 'glass': n_glass, 'furniture': n_furn,
                  'furnitureKinds': n_kinds},
    }


def model_glass_type(part: dict) -> bool:
    """A glass part from a Revit glass wall type (labelled with the type name; panes, transoms, screens are not)."""
    lab = part.get('label')
    return part['kind'] == 'glass' and bool(lab) and not lab.endswith((' pane', ' transom')) and lab != 'glass screen'


def stages_bytes(st: dict) -> bytes:
    """The bank's bytes: compact JSON, UTF-8, no trailing newline."""
    return json.dumps(st, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode('utf-8')
