"""Presentation v1 per version (DESIGN.md 8), ported from each generator's Python: the page-level things the four
generators wrote into their HTML (title, heading, intro, accent, legend, floor buttons, tick labels, camera start, styles),
as data. The viewer has no per-project code.

    bank(model, stages)         bank_test/src/make_html.py           (both versions)
    suite(pres2_model, stages)  presidential_test/src/make_html.py
    house(stages, furniture)    cad_test/src/make_html_cad_merged.py
    hotel(model)                hotel_test/src/make_html.py

Each function reads what its generator read (the source model or stages, not the converted v1 model) and computes the
texts the way the generator did, Python formatting included. Optional fields are written where DESIGN.md 8 gives a value
other than the default (floorButtons.labels only for buttons whose text differs from the floor's name, tick labels only
where they differ from the defaults, no toggles); `parsePresentation` fills the rest.

Intro runs: the stages' panelIntro is HTML with only <b>...</b>; `intro_runs` splits it into {text, bold} runs and fails on
any other tag, on nested or unclosed bold, and on any character reference it does not decode.
"""
from __future__ import annotations

import math
import re
from typing import Any

DEFAULT_ACCENT = '#2f6f8f'
DEFAULT_LABELS = {'plates': 'Floor plates', 'glass': 'Glass', 'rooms': 'Room names', 'single': 'Single-line items',
                  'picture': 'Plan picture',
                  'pictureTitle': "Each floor's source picture, laid on its floor plate at the model's scale and position"}


class IntroMarkupError(ValueError):
    pass


_TAG = re.compile(r'<(/?)([A-Za-z][A-Za-z0-9]*)\s*>')
_ENTITY = re.compile(r'&(#[0-9]{1,7}|#[xX][0-9a-fA-F]{1,6}|[A-Za-z][A-Za-z0-9]{1,31});')
_KNOWN_ENTITIES = {'amp': '&', 'lt': '<', 'gt': '>', 'quot': '"', 'apos': "'", 'nbsp': '\u00a0'}


def _reference(m: re.Match[str]) -> str:
    ref = m.group(1)
    if ref.startswith('#'):
        code = int(ref[2:], 16) if ref[1] in 'xX' else int(ref[1:])
        if not 0 < code <= 0x10FFFF or 0xD800 <= code <= 0xDFFF:
            raise IntroMarkupError(f'character reference &{ref}; is not a character')
        return chr(code)
    if ref in _KNOWN_ENTITIES:
        return _KNOWN_ENTITIES[ref]
    raise IntroMarkupError(f'unknown character reference &{ref};')


def page_text(text: str) -> str:
    """What a browser shows for text a generator pasted into its HTML (no tags in it): the character references decoded.
    Refused: any '<', and an '&' that starts something like a reference this does not decode (a bare '& ' is text)."""
    rest = _ENTITY.sub('', text)
    if '<' in rest:
        raise IntroMarkupError(f'markup in a page text: {text[:80]!r}')
    if re.search(r'&[A-Za-z0-9#]', rest):
        raise IntroMarkupError(f'a character reference that is not decoded in a page text: {text[:80]!r}')
    return _ENTITY.sub(_reference, text)


_decode = page_text


def intro_runs(markup: str) -> list[dict[str, Any]]:
    """'... of <b>Bangkok Bank</b>: ...' -> [{text}, {text, bold: true}, {text}] (empty runs left out)."""
    runs: list[dict[str, Any]] = []
    at, bold = 0, False
    for m in _TAG.finditer(markup):
        closing, name = m.group(1) == '/', m.group(2).lower()
        if name != 'b':
            raise IntroMarkupError(f'<{m.group(1)}{m.group(2)}> in the intro: only <b> is allowed')
        if closing != bold:
            raise IntroMarkupError(f'{"unopened </b>" if closing else "nested <b>"} in the intro')
        text = _decode(markup[at:m.start()])
        if text:
            runs.append({'text': text, 'bold': True} if bold else {'text': text})
        bold = not closing
        at = m.end()
    if bold:
        raise IntroMarkupError('unclosed <b> in the intro')
    text = _decode(markup[at:])
    if text:
        runs.append({'text': text})
    return runs


def _legend(layout: str, items: list[tuple[str, str]]) -> dict[str, Any]:
    return {'layout': layout, 'items': [{'colour': c, 'text': page_text(t)} for c, t in items]}


def _floor_buttons(all_text: str, floors: list[dict[str, Any]], texts: dict[str, str] | None = None) -> dict[str, Any]:
    """{all} plus labels only for the buttons whose text is not the floor's name (parsePresentation's default). The pages
    wrote each button as <button data-f="key">text</button>: the text a browser shows is compared."""
    shown = {f['key']: page_text((texts or {}).get(f['key'], f['name'])) for f in floors}
    labels = {f['key']: shown[f['key']] for f in floors if shown[f['key']] != f['name']}
    return {'all': page_text(all_text), 'labels': labels} if labels else {'all': page_text(all_text)}


# ---------------------------------------------------------------------------------------------------- bank (both versions)
def bank(M: dict[str, Any], S: dict[str, Any]) -> dict[str, Any]:
    """bank_test/src/make_html.py (the 27 Oct page came from the same generator: its facts agree)."""
    kinds = {p['kind'] for p in M['parts']}
    heights = sorted({f['wallHeight'] for f in M['floors']})
    items = [('#e3ddd3', 'Walls, columns and door lintels (' + ' / '.join(f'{h:.2f}' for h in heights) + ' m per level)')]
    gw_heights = sorted({p['z1'] for p in M['parts'] if p['kind'] == 'glass' and p.get('label')
                         and not p['label'].endswith((' pane', ' transom', 'glass screen'))})
    if 'glass' in kinds:
        items.append(('#9cc3d5', 'Glass: curtain wall, window panes' + (
            ', glass partitions (' + ' / '.join(f'{h:.2f}' for h in gw_heights) + ' m, from the Revit wall types)'
            if gw_heights else '')))
    if 'railing' in kinds:
        items.append(('#77727c', f"Railings ({M['railingHeight']:.2f} m)" + (' and the parapet' if 'parapet' in kinds else '')))
    items.append(('#b9c7b4' if 'step' in kinds else '#5aa65a',
                  ('Stairs: steps where the drawing says UP / DOWN, flat tread lines elsewhere' if 'step' in kinds
                   else 'Stairs') + ' (faint: flights above the cut)'))
    if 'single' in kinds:
        items.append(('#e0a458', 'Single line: wall, railing or edge?'))
    items.append(('#d4d8d2', 'Floor plate (approximate outline)'))
    p: dict[str, Any] = {
        'documentTitle': page_text(f"{M.get('shortName', M['project'])} test"),
        'heading': page_text(f"{M['project']} (test): CAD → 3D"),
        'intro': intro_runs(S['panelIntro']),
        'accent': '#2f6f8f',
        'legend': _legend('inline', items),
    }
    if len(M['floors']) > 1:
        p['floorButtons'] = _floor_buttons('Both levels', M['floors'])     # buttons named after the floors
    p['camera'] = {'kind': 'fixed', 'position': [24, 27, 29], 'target': [0, 2.5, 0], 'far': 600}
    p['creaseAngle'] = 25
    p['groundPlane'] = None
    return p


# ---------------------------------------------------------------------------------------------------- presidential suite
def suite(M: dict[str, Any], S: dict[str, Any]) -> dict[str, Any]:
    """presidential_test/src/make_html.py, from pres2_model.json (M) and pres2_stages.json (S). One floor: no floor row."""
    items = [('#e3ddd3', f"Walls and columns ({M['floorToFloor']:.2f} m)")]
    kinds = {p['kind'] for p in M['parts']}
    if 'glass' in kinds:
        items.append(('#9cc3d5', 'Glass'))
    if 'low' in kinds:
        items.append(('#d2c6b2', 'Low walls, built-in seats, kerbs'))
    if 'builtin' in kinds:
        items.append(('#c9a77f', 'Built-ins'))
    if 'balustrade' in kinds:
        items.append(('#9cc3d5', f"Balustrade ({M.get('balustradeHeight', 1.1):.2f} m)"))
    if 'deck' in kinds:
        items.append(('#b08a5c', 'Terrace decks'))
    if 'post' in kinds:
        items.append(('#6f6153', 'Pergola posts'))
    items.append(('#d4d8d2', 'Floor slab'))
    return {
        'documentTitle': 'Presidential suite test',
        'heading': 'Presidential suite (test): CAD → 3D',
        'intro': intro_runs(S['panelIntro']),
        'accent': '#8a6d3b',
        'legend': _legend('inline', items),
        'labels': {'plates': 'Floor slab'},
        'camera': {'kind': 'fixed', 'position': [-26, 32, 30], 'target': [0, 1.2, 0], 'far': 600},
        'creaseAngle': 25,
        'groundPlane': None,
    }


# ---------------------------------------------------------------------------------------------------- Sukhumvit house
HOUSE_INTRO_HEAD = ("Built automatically from the DWG. Each wall's two face lines are paired, filled and merged into one "
                    "solid per wall run, so there are no seams. ")
HOUSE_INTRO_TAIL = ' No AI used.'
HOUSE_FLOOR_BUTTONS = {'ground': 'Ground', 'upper': 'Upper'}
HOUSE_PART_STYLES = {
    'glass': {'color': '#8fd0e0', 'edge': '#4f9fb3', 'opacity': 0.35, 'roughness': 0.85, 'edgeOpacity': 0.6, 'renderOrder': 0},
    'pane': {'color': '#7fb8e8', 'edge': '#3f7fb3', 'opacity': 0.35, 'roughness': 0.85, 'edgeOpacity': 0.6, 'renderOrder': 0},
    'single': {'opacity': 0.9},
}


def house_intro(S: dict[str, Any], furniture: dict[str, Any]) -> tuple[str, bool]:
    """make_html_cad_merged.py's intro (what was found in the plan, the heights) and whether openings were found."""
    FS = S['stats']['floors']
    m2 = lambda v: f'{v:.2f}'                                            # noqa: E731
    found = all('openings' in FS[f] for f in ('ground', 'upper'))
    if found:
        n = {k: FS['ground']['openings'][k] + FS['upper']['openings'][k] for k in ('door', 'window', 'passage')}
        gd = sum(FS[f].get('glazedDoors', 0) for f in ('ground', 'upper'))
        heads = lambda f, k='doorHeads': ' / '.join(m2(h) for h in FS[f][k])   # noqa: E731
        intro = (f"{n['door']} doors and {n['window']} windows found in the plan are cut in (the {n['passage']} passages are gaps "
                 f"that are already open). Doors open to {heads('ground')} m (upper floor {heads('upper')} m) under a lintel; "
                 f"windows{f', and the {gd} sliding glass doors that may be windows,' if gd else ''} are glazed to their heads "
                 f"({heads('ground', 'windowHeads')} m; upper floor {heads('upper', 'windowHeads')} m). "
                 f"Heights from the elevations (floors +0.90 m, +4.80 m).")
    else:
        intro = 'Floor heights come from the elevations (+0.90 m, +4.80 m).'
    if furniture.get('furniture'):
        kinds = furniture['furnitureKinds']
        unnamed = sum(k['count'] for k in kinds if k['key'] == 'other')
        intro += (f" Furniture: {len(furniture['furniture'])} boxes, one per piece, coloured by kind ({len(kinds)} kinds)"
                  + (f"; {unnamed} are grey because the drawing does not say what they are" if unnamed else '')
                  + '. They come in at the end of the replay.')
    return intro, found


def house(S: dict[str, Any], furniture: dict[str, Any], floors: list[dict[str, Any]]) -> dict[str, Any]:
    """make_html_cad_merged.py, from house3d_stages.json (S, its stats) and furniture_house.json; `floors` = the model's."""
    intro, found = house_intro(S, furniture)
    if found:
        walls, glass = 'Walls and lintels', [('#8fd0e0', 'Glass walls'), ('#7fb8e8', 'Window glass')]
    else:
        walls, glass = 'Walls', [('#8fd0e0', 'Windows / glass')]
    items = [('#e3ddd3', walls), *glass, ('#5aa65a', 'Stairs'), ('#e0a458', 'Single line: wall, railing or edge?'),
             ('#d4d8d2', 'Floor plate (approximate outline)')]
    return {
        'documentTitle': 'CAD to 3D test',
        'heading': 'Test Sukhumvit Residence: CAD → 3D',
        'intro': intro_runs(HOUSE_INTRO_HEAD + intro + HOUSE_INTRO_TAIL),
        'accent': '#c9773e',
        'legend': _legend('inline', items),
        'floorButtons': _floor_buttons('Both floors', floors, HOUSE_FLOOR_BUTTONS),
        'camera': {'kind': 'fixed', 'position': [-28, 30, 34], 'target': [0, 3, 0], 'far': 500},
        'partStyles': {k: dict(v) for k, v in HOUSE_PART_STYLES.items()},
        'creaseAngle': 40,
        'groundPlane': {'size': [80, 50], 'colour': '#dfe3e0'},
    }


# ---------------------------------------------------------------------------------------------------- hotel
def _inside(pt: tuple[float, float], ring: list[list[float]]) -> bool:
    """Even-odd rule: is the plan point inside the ring? (hotel_test/src/make_html.py)"""
    x, y = pt
    c = False
    for (x1, y1), (x2, y2) in zip(ring, ring[1:] + ring[:1]):
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
            c = not c
    return c


def hotel(M: dict[str, Any]) -> dict[str, Any]:
    """hotel_test/src/make_html.py: the panel's words, from the model (no build replay; the picture tick starts off)."""
    kinds = {p['kind'] for p in M['parts']}
    heights = sorted({f['wallHeight'] for f in M['floors']})
    levels = ' and '.join(f"{f['name']} at {f['level']:+.2f} m".replace('+0.00', '0.00') for f in M['floors'])
    frames = M.get('pictureFrame', {})
    NAME = {f['key']: f['name'] for f in M['floors']}

    def slabs(key: str, label: str | None = None) -> list[dict[str, Any]]:
        return [p for p in M['parts'] if p['kind'] == 'slab' and p['floor'] == key
                and (label is None or (p.get('label') or '').startswith(label))]

    def on_plate(plates: list[dict[str, Any]], x: float, y: float) -> bool:
        return any(_inside((x, y), p['o']) and not any(_inside((x, y), h) for h in p['h']) for p in plates)

    def steps_of(key: str) -> list[dict[str, Any]]:
        return [p for p in M['parts'] if p['kind'] == 'step' and p['floor'] == key]

    def scale_words(key: str, first: bool) -> str:
        pf = frames[key]
        kx, ky = pf['pxPerMetreX'], pf['pxPerMetreY']
        if abs(kx - ky) < 0.005:
            return f"{NAME[key]}'s {kx:.2f}" + (' px per metre' if first else '')
        return f"{NAME[key]}'s picture has {kx:.2f} px per metre across and {ky:.2f} down"

    first = M['floors'][0]['key']
    flight = steps_of(first)
    stair_w = max(max(max(x for x, _ in p['o']) - min(x for x, _ in p['o']), max(y for _, y in p['o']) - min(y for _, y in p['o']))
                  for p in flight) if flight else None
    scale_txt = ', '.join(scale_words(f['key'], i == 0) for i, f in enumerate(f for f in M['floors'] if f['key'] in frames))
    lift_w = sorted({o['width'] for o in M['openings'] if o.get('liftDoor')})
    if stair_w is None:
        raise ValueError('hotel: no steps on the lowest floor, so the scale sentence has no stair width (the generator fails here too)')
    intro = (f"No CAD: read from two presentation pictures, {levels}, scaled from the one real size the owner gave, the main "
             f"stair's width between its side walls, {stair_w:.2f} m: {scale_txt}."
             + (f" Lift doors built {lift_w[0]:.2f} m wide (the owner's)." if len(lift_w) == 1 else '')
             + (" The circles with a cross are lights, not furniture." if not any(k['key'] == 'lamp' for k in M.get('furnitureKinds') or []) else '')
             + " Tick Plan picture to see each picture under the model.")
    hatches = [o for o in M['openings'] if o.get('hatch')]
    sills = sorted({o['sill'] for o in hatches})
    items = [('#e3ddd3', 'Walls and door lintels, ' + ' / '.join(f'{h:.2f}' for h in heights) + ' m (up to the next floor)'
              + (f"; {len(hatches)} hatch{'es' if len(hatches) > 1 else ''} ({', '.join(o['subtype'] for o in hatches)}), open from "
                 f"{' / '.join(f'{s:.2f}' for s in sills)} to {max(o['head'] for o in hatches):.2f} m" if hatches else ''))]
    if 'parapet' in kinds:
        lows = [p for p in M['parts'] if p['kind'] == 'parapet']
        low_h = ' / '.join(sorted({'%.2f' % (p['z1'] - p['z0']) for p in lows}))
        low_what = ', '.join(sorted({(p.get('label') or 'low wall').replace(' (low wall)', '') for p in lows}))
        items.append(('#e3ddd3', f'Low walls, {low_h} m: {low_what}'))
    if 'glass' in kinds:
        items.append(('#9cc3d5', 'Glass read from the pictures, full height' + (', and its frame posts' if 'mullion' in kinds else '')))
    if 'railing' in kinds:
        rails = [(p.get('label') or '') for p in M['parts'] if p['kind'] == 'railing']
        where = [w for w, n in (('round the open stair', sum('open stair' in r for r in rails)),
                                ("on the terrace's open edges", sum('terrace' in r for r in rails))) if n]
        items.append(('#77727c', f"Railings, {M['railingHeight']:.2f} m" + (', ' + ' and '.join(where) if where else '')))
    flat = [(f['key'], M['stairs'][f['key']]['below']) for f in M['floors'] if f['key'] in M['stairs'] and M['stairs'][f['key']]['below']]
    if any(steps_of(f['key']) for f in M['floors']) or flat:
        said = []
        for i, f in enumerate(M['floors']):
            st = steps_of(f['key'])
            if not st:
                continue
            top = max(p['z1'] for p in st)
            nxt = M['floors'][i + 1] if i + 1 < len(M['floors']) else None
            if nxt and abs(f['level'] + top + (top / len(st)) - nxt['level']) < 0.01:      # the last riser lands on the next floor
                said.append(f"{len(st)} steps from {f['name']} up to {nxt['name']}"
                            + ("'s open stair" if any(v['what'] == 'stair' for v in M['voids'].get(nxt['key'], [])) else ''))
            else:
                said.append(f"{len(st)} steps from {f['name']} up toward the floor above (not in the pictures), ending at {top:+.2f} m")
        for key, a in flat:                    # flat tread lines: named by the nearest room name (within 3 m of their middle)
            xs, ys = a[0::2], a[1::2]
            cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
            near = sorted((math.hypot(r['x'] - cx, r['y'] - cy), r['label']) for r in M['rooms'] if r['floor'] == key)
            what = f"the {near[0][1].lower()}" if near and near[0][0] < 3 else f"{NAME[key]}'s other stair"
            said.append(f"{what} as flat tread lines (up or down not known)")
        items.append(('#b9c7b4', 'Stairs: ' + '; '.join(said)))
    plate_txt = 'Floor plates: the inside of the walls and glass'
    outdoor = []
    for f in M['floors']:
        fc = slabs(f['key'], 'forecourt')
        if not fc:
            continue
        allp, depth = slabs(f['key']), []
        for o in M['openings']:
            if o['floor'] != f['key'] or o['kind'] not in ('door', 'passage'):
                continue
            for sgn in (1, -1):                # the side whose spot 0.3 m beyond the wall face is on the forecourt
                nx, ny, t = o['nx'] * sgn, o['ny'] * sgn, o['wallThickness'] / 2
                if on_plate(fc, o['x'] + nx * (t + 0.3), o['y'] + ny * (t + 0.3)):
                    d = 0.0
                    while d < 20 and on_plate(allp, o['x'] + nx * (t + d + 0.005), o['y'] + ny * (t + d + 0.005)):
                        d += 0.01
                    depth.append(d)
        outdoor.append(f"{f['name']}'s forecourt" + (f" ({min(depth):.2f} m deep in front of the entrance doors, as drawn)" if depth else ''))
    if any('terrace' in (p.get('label') or '') for p in M['parts'] if p['kind'] == 'railing'):
        outdoor.append(f"{NAME[next(p['floor'] for p in M['parts'] if p['kind'] == 'railing' and 'terrace' in (p.get('label') or ''))]}'s terrace")
    if outdoor:
        plate_txt += '; outdoors at the same level, ' + ' and '.join(outdoor)
    items.append(('#d4d8d2', plate_txt))
    short = M.get('shortName', M['project'])
    p: dict[str, Any] = {
        'documentTitle': page_text(f'{short} test'),
        'heading': page_text(f'{short} (test): two pictures → 3D'),
        'intro': intro_runs(intro),
        'accent': '#2f6f8f',
        'legend': _legend('lines', items),
    }
    if len(M['floors']) > 1:
        p['floorButtons'] = _floor_buttons('Both floors', M['floors'])
    # The usual view: from the south-east, above (the bank page's angle, 0.9 of its distance), aimed at the middle of the
    # floor plates and panned by half the side panel's width (the viewer computes the target from the slabs).
    p['camera'] = {'kind': 'fitSlabs', 'away': [round(v * 0.9, 6) for v in (24, 24.5, 29)], 'targetY': 2.5,
                   'panForPanel': True, 'far': 600}
    p['creaseAngle'] = 25
    p['groundPlane'] = None
    return p
