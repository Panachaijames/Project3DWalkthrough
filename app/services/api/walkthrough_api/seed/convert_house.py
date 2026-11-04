"""cad_test/src/house3d_merged.json + furniture_house.json -> BuiltModel v1 (DESIGN.md 6.4).

The page reads only these two (and house3d_stages.json); heights.json and openings.json are already folded into
house3d_merged.json (openings, pieces, heights) and go to source/ for the record.

| v1 field         | from                                                                                             |
|------------------|--------------------------------------------------------------------------------------------------|
| names            | project "Test Sukhumvit Residence", shortName "Sukhumvit house", photoName "Sukhumvit", maxPrefix "SK" |
| offset           | furniture_house.offset (= house3d_merged.centre; checked)                                         |
| floors           | furniture_house.floors order and names; level = levels[k]; wallHeight = round(tops[k] - levels[k], 6); |
|                  | slabThickness: lowest floor levels[k] (the plinth), others 0.25; sheetShift = [round(-frame.shift[k], 6), 0] |
|                  | where the shift is not 0 (furniture_house.frame: model = drawing + shift - centre; centre = offset) |
| heights          | railingHeight 1.0, singleLineHeight 1.0 (the page's single lines), doorHeadDefault defaults[lowest].doorHead |
| parts (solids)   | per ring {floor, kind, z0 0, z1, follow, o, h}: wall z1 = H0 follow; glass z1 = H0 - 0.6 follow; single 1.0 |
| parts (pieces)   | {floor, kind, z0, z1, follow, o, h, label: id, fit}: lintel and a pane reaching the top: follow, fit top; |
|                  | other panes and sills: fixed, fit clip (the page's fitPieces)                                     |
| parts (plates)   | {floor, kind slab, z0 -thick, z1 0, follow false, o, h}, thick = levels[k] on the lowest floor (+ plinth) |
| stairs           | {below [], above [], panels: the tread segments flattened}                                        |
| openings         | flattened per floor, + floor; lintel true -> "lintel", false -> null; every other field kept     |
| rooms, probes    | [] (no room names in this DWG; windows are tested from the openings)                             |
| not carried      | removed, heights, furniture_house.frame (centre = offset, shift = sheetShift), furnitureReport (source/) |

Stamp: no Max script; stamp = sha1(model.json)[:12], stampSource "model.json".
"""
from __future__ import annotations

from typing import Any


def r6(v: float) -> float:
    return round(v, 6)


class HouseSourceError(ValueError):
    pass


def convert(H: dict[str, Any], FH: dict[str, Any]) -> dict[str, Any]:
    if FH['offset'] != H['centre']:
        raise HouseSourceError(f"furniture_house.offset {FH['offset']} != house3d_merged.centre {H['centre']}")
    order = [f['key'] for f in FH['floors']]
    names = {f['key']: f['name'] for f in FH['floors']}
    if set(order) != set(H['levels']):
        raise HouseSourceError(f'furniture_house floors {order} != house3d_merged levels {list(H["levels"])}')
    lowest = order[0]
    H0 = {k: r6(H['tops'][k] - H['levels'][k]) for k in order}
    shift = (FH.get('frame') or {}).get('shift') or {}

    parts = []
    for key, rings in H['solids'].items():          # walls, glass walls and single lines, in the file's order
        fl, kind = key.split(':')
        z1 = {'wall': H0[fl], 'glass': r6(H0[fl] - 0.6), 'single': 1.0}[kind]
        for r in rings:
            parts.append({'floor': fl, 'kind': kind, 'z0': 0.0, 'z1': z1, 'follow': kind != 'single', 'o': r['o'],
                          'h': r['h']})
    for fl in order:                                 # lintels, sills and panes: heads stay (the page's fitPieces)
        for p in H['pieces'].get(fl, []):
            if p['kind'] == 'lintel' or (p['kind'] == 'pane' and p.get('top')):
                fit, follow = 'top', True
            else:
                fit, follow = 'clip', False
            parts.append({'floor': fl, 'kind': p['kind'], 'z0': p['z0'], 'z1': p['z1'], 'follow': follow, 'o': p['o'],
                          'h': p['h'], 'label': p['id'], 'fit': fit})
    for fl in order:                                 # floor plates: the ground one is a plinth from the ground up
        thick = H['levels'][fl] if fl == lowest else 0.25
        for r in H['plates'].get(fl, []):
            q = {'floor': fl, 'kind': 'slab', 'z0': r6(-thick), 'z1': 0.0, 'follow': False, 'o': r['o'], 'h': r['h']}
            if fl == lowest:
                q['plinth'] = True
            parts.append(q)

    openings = []
    for fl in order:
        for o in H['openings'].get(fl, []):
            openings.append({'id': o['id'], 'floor': fl, **{k: v for k, v in o.items() if k not in ('id', 'lintel')},
                             'lintel': 'lintel' if o['lintel'] else None})

    floors = []
    for k in order:
        f = {'key': k, 'name': names[k], 'level': H['levels'][k], 'wallHeight': H0[k],
             'slabThickness': H['levels'][k] if k == lowest else 0.25}
        if shift.get(k):
            f['sheetShift'] = [r6(-shift[k]), 0.0]   # sheet = model + offset + sheetShift
        floors.append(f)

    flat = lambda segs: [v for s in segs for v in s]   # noqa: E731
    return {
        'project': 'Test Sukhumvit Residence', 'shortName': 'Sukhumvit house', 'projectNo': None,
        'source': ['Test Sukhumvit Residence.dwg'], 'units': 'm', 'offset': FH['offset'], 'photoName': 'Sukhumvit',
        'maxPrefix': 'SK',
        'floors': floors,
        'railingHeight': 1.0, 'singleLineHeight': 1.0, 'doorHeadDefault': H['heights']['defaults'][lowest]['doorHead'],
        'parts': parts,
        'stairs': {k: {'below': [], 'above': [], 'panels': flat(H['stairs'].get(k, []))} for k in order},
        'voids': {k: [] for k in order}, 'closures': {k: [] for k in order}, 'stairOutlines': {k: [] for k in order},
        'rooms': [], 'openings': openings, 'probes': [], 'colliderSkins': {k: [] for k in order},
        'furnitureKinds': FH['furnitureKinds'], 'furniture': FH['furniture'],
    }
