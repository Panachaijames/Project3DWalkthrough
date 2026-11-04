"""Replay data conversions (DESIGN.md 7.4): bank copied, suite renamed, house built from house3d_stages.json.

|             | bank v1, v2 | suite                                                     | house                                    |
|-------------|-------------|-----------------------------------------------------------|------------------------------------------|
| file        | copied      | `floor` -> `floors.suite`; {level} -> {suitelevel}, {height} -> {suiteheight}; rest as is | built from house3d_stages.json, the model and the page's code |
| stepTitles  | default     | Read the drawing / Sort the line work / Check the floor / Find the wall faces / Merge into wall runs / Raise the walls / Slab and room names | Read the drawing / Sort the layers / Line up the floors / Pair the wall faces / Merge into wall runs / Raise the walls / Floors, stairs, done |
| colors      | default     | wall #7a6650, glass #3f8fb0, door #c0702a, railing #9b3fa0 | wall #7a6650, glass #2f86a8, window #4a9cc0, stair #2e8b47, door #c0702a |
| layersTitle | default     | default                                                   | Layers found                             |

The suite page filled its two placeholders with String.prototype.replace (the first `{level}` of the align caption, the
first `{height}` of the raise caption): exactly those become `{suitelevel}` / `{suiteheight}`, so the filled captions
stay the page's (DESIGN.md 7.3 placeholders; the oracle tests compare them with fixtures/prototype).

The house, as make_html_cad_merged.py does at generation and in its page script: lines rounded to 2 decimals (Python
round), noise cut to its first 6,000 lines; the pairs (rounded) become the pieces; rings.wall = the model's solids, rings.glass
= the glass solids + the panes' {o, h}; the layer rows from stats.layers with layer_list(); source.layersUsed =
stats.planLayers; the intro = the page's three facts; the captions = the page's seven caption functions rendered once
with the stats (JavaScript number formatting: jsfmt) and the Build settings left as placeholders.
"""
from __future__ import annotations

import copy
from typing import Any

from ..jsfmt import js_locale, js_pct, js_str, js_to_fixed

NOISE_LINES = 6000            # make_html_cad_merged.py: the longest ignored lines kept for the replay

SUITE_STEP_TITLES = {'read': 'Read the drawing', 'sort': 'Sort the line work', 'align': 'Check the floor',
                     'pair': 'Find the wall faces', 'merge': 'Merge into wall runs', 'raise': 'Raise the walls',
                     'finish': 'Slab and room names'}
SUITE_COLORS = {'wall': '#7a6650', 'glass': '#3f8fb0', 'door': '#c0702a', 'railing': '#9b3fa0'}

HOUSE_STEP_TITLES = {'read': 'Read the drawing', 'sort': 'Sort the layers', 'align': 'Line up the floors',
                     'pair': 'Pair the wall faces', 'merge': 'Merge into wall runs', 'raise': 'Raise the walls',
                     'finish': 'Floors, stairs, done'}
HOUSE_COLORS = {'wall': '#7a6650', 'glass': '#2f86a8', 'window': '#4a9cc0', 'stair': '#2e8b47', 'door': '#c0702a'}
HOUSE_LAYERS_TITLE = 'Layers found'      # the page passed no layersTitle: build_replay.js's own default


# ---------------------------------------------------------------------------------------------------- suite
def suite(S: dict[str, Any]) -> dict[str, Any]:
    """pres2_stages.json -> ReplayData v1 (key order kept; stepTitles and colors appended)."""
    out: dict[str, Any] = {}
    for key, value in S.items():
        if key == 'floor':
            out['floors'] = {'suite': value}
        elif key == 'captions':
            caps = dict(value)
            caps['align'] = caps['align'].replace('{level}', '{suitelevel}', 1)     # the page: .replace('{level}', ...)
            caps['raise'] = caps['raise'].replace('{height}', '{suiteheight}', 1)   # the page: .replace('{height}', ...)
            out['captions'] = caps
        else:
            out[key] = value
    out['stepTitles'] = dict(SUITE_STEP_TITLES)
    out['colors'] = dict(SUITE_COLORS)
    return out


# ---------------------------------------------------------------------------------------------------- house
def layer_list(names: list[str]) -> str:
    """make_html_cad_merged.py: 'XR_L44 Plan$0$A-WALL' is a layer from a linked drawing: show it as A-WALL."""
    plain: list[str] = []
    linked = 0
    for n in names:
        if '$0$' in n:
            linked += 1
            n = n.split('$0$')[-1]
        if n not in plain:
            plain.append(n)
    return ', '.join(plain) + (f' (incl. {linked} from linked drawings)' if linked else '')


def js_truthy(v: Any) -> bool:
    """JavaScript truthiness (an empty object or list is truthy, unlike Python)."""
    if v is None or v is False:
        return False
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return v == v and v != 0                          # NaN and 0 are falsy
    if isinstance(v, str):
        return v != ''
    return True


def house(S: dict[str, Any], D: dict[str, Any], furniture: dict[str, Any], floor_order: list[str]) -> dict[str, Any]:
    """house3d_stages.json (S), house3d_merged.json (D) and furniture_house.json -> ReplayData v1."""
    S = copy.deepcopy(S)
    st = S['stats']
    FS = st['floors']
    both = lambda fn: fn(FS['ground']) + fn(FS['upper'])            # noqa: E731 (the page's both())
    kept = lambda c: both(lambda f: f['kept'].get(c) or 0)          # noqa: E731 (f.kept[c] || 0)
    found = js_truthy(FS['ground'].get('openings')) and js_truthy(FS['upper'].get('openings'))
    metres = lambda hs: ' / '.join(js_to_fixed(h, 2) for h in hs) + ' m' if hs else 'none'   # noqa: E731
    openings_of = lambda f: (f"{js_str(f['openings']['door'])} doors, {js_str(f['openings']['window'])} windows and "  # noqa: E731
                             f"{js_str(f['openings']['passage'])} passages")
    has_furniture = bool(furniture.get('furniture'))

    # The generator's own changes to S, before the page sees it.
    L = st['layers']
    layers = [['Walls', layer_list(L['wall'])], ['Glass', layer_list(L['glass'])],
              ['Windows', layer_list(L['window'])], ['Stairs', layer_list(L['stair'])]]
    if L.get('door'):
        layers.append(['Doors', layer_list(L['door'])])
    layers.append(['Ignored', f"{len(L['ignored'])} other layers: furniture, floor patterns, "
                              f"{'' if L.get('door') else 'doors, '}grid, dimensions, labels"])
    source = dict(S['source'])
    source['layersUsed'] = st['planLayers']

    def panes(k: str) -> list[dict[str, Any]]:
        return [{'o': p['o'], 'h': p['h']} for p in (D.get('pieces') or {}).get(k, []) if p['kind'] == 'pane']

    floors: dict[str, Any] = {}
    for k in floor_order:
        f = S['floors'][k]
        floors[k] = {
            'sheet': f['sheet'],
            'lines': {c: [round(v, 2) for v in (a[:NOISE_LINES * 4] if c == 'noise' else a)] for c, a in f['lines'].items()},
            'pieces': {c: [round(v, 2) for v in q] for c, q in f['pairs'].items()},
            'rings': {'wall': D['solids'].get(f'{k}:wall') or [],
                      'glass': [*(D['solids'].get(f'{k}:glass') or []), *panes(k)]},
        }

    intro = [
        'Two floor plans side by side on one sheet, in millimetres',
        f"{js_locale(both(lambda f: f['read']))} drawing items in the plan areas, on {js_str(source['layersUsed'])} layers in use",
        f"Floors lined up by {js_str(st['gridLabels'])} grid labels; levels from the elevation tags",
    ]

    furniture_finish = (f", and last the furniture: {len(furniture['furniture'])} coloured boxes, one per piece, "
                        f"{len(furniture['furnitureKinds'])} kinds") if has_furniture else ''
    gd = both(lambda f: f.get('glazedDoors') or 0)
    captions = {
        'read': f"{js_locale(both(lambda f: f['read']))} drawing items in the two plan areas, on "
                f"{js_str(source['layersUsed'])} layers, in millimetres.",
        'sort': f"Walls {js_locale(kept('wall'))} lines, windows and glass {js_locale(kept('window') + kept('glass'))}, "
                f"stairs {js_locale(kept('stair'))}"
                + (f", door symbols {js_locale(kept('door'))}. {js_locale(both(lambda f: f['ignoredLines']))} lines ignored: "
                   f"furniture, floor patterns, grid and dimensions." if kept('door')
                   else f". {js_locale(both(lambda f: f['ignoredLines']))} lines ignored: furniture, floor patterns, doors, "
                        f"grid and dimensions."),
        'align': f"The upper plan sits beside the ground plan on the sheet. {js_str(st['gridLabels'])} grid labels match on "
                 f"both, so it moves {js_to_fixed(S['floors']['upper']['sheet'][0], 2)} m onto the ground plan and rises to "
                 f"its level: ground {{groundlevel+}} m, upper {{upperlevel+}} m.",
        'pair': f"Each wall is drawn as two lines. Pairing them gives {js_locale(both(lambda f: f['pieces']['wall']))} wall "
                f"pieces and {js_locale(both(lambda f: f['pieces']['glass']))} glass pieces; "
                f"{js_pct(FS['ground']['pairedShare'])} of the ground-floor wall lines and "
                f"{js_pct(FS['upper']['pairedShare'])} of the upper ones found their partner.",
        'merge': f"{js_locale(both(lambda f: f['pieces']['wall'] + f['pieces']['glass']))} pieces merge into "
                 f"{js_str(both(lambda f: f['runs']['wall']))} wall runs and {js_str(both(lambda f: f['runs']['glass']))} "
                 f"glass runs: one solid each, no seams."
                 + ((f" The {js_str(both(lambda f: f['openings']['door']))} doors and "
                     f"{js_str(both(lambda f: f['openings']['window']))} windows found in the plan are cut through them; "
                     f"window glass goes in each window"
                     + (f" and in the {js_str(gd)} sliding glass doors that may be windows." if js_truthy(gd) else '.'))
                    if found else ''),
        'raise': "The walls rise to their height: ground floor {groundheight} m, upper floor {upperheight} m."
                 + ((f" Doors stay open to their heads (ground {metres(FS['ground']['doorHeads'])}, upper "
                     f"{metres(FS['upper']['doorHeads'])}, from the elevations) with "
                     f"{js_str(both(lambda f: f['pieces']['lintel']))} lintels above doors and windows; windows get glass "
                     f"from {'the sill' if js_truthy(both(lambda f: f['pieces']['sill'])) else 'the floor'} to the head "
                     f"(ground {metres(FS['ground']['windowHeads'])}, upper {metres(FS['upper']['windowHeads'])}).")
                    if found else ''),
        'finish': f"Floor plates and stairs go in{furniture_finish}. Done: 2 floors, "
                  f"{js_str(both(lambda f: f['runs']['wall']))} wall runs, {js_str(both(lambda f: f['runs']['glass']))} glass runs"
                  + (f"; found on the ground floor {openings_of(FS['ground'])}, upstairs {openings_of(FS['upper'])}."
                     if found else '.')
                  + ' The real build takes seconds; this replay slows it down so you can follow it.',
    }
    return {
        'source': source,
        'intro': intro,
        'layers': layers,
        'floors': floors,
        'captions': captions,
        'stats': st,
        'layersTitle': HOUSE_LAYERS_TITLE,
        'stepTitles': dict(HOUSE_STEP_TITLES),
        'colors': dict(HOUSE_COLORS),
    }
