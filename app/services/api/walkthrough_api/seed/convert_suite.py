"""presidential_test/src/pres2_model.json -> BuiltModel v1 (DESIGN.md 6.3).

| v1 field          | from                                                                                           |
|-------------------|------------------------------------------------------------------------------------------------|
| project/shortName | "Presidential suite" (the page's heading and title); projectNo null; source [M.source]          |
| photoName         | "Presidential" (the page's `project` for photos, CSV and storage); maxPrefix "PS" (the .ms)     |
| floors            | one floor "suite", "Suite (FL-01)", level M.level, wallHeight M.floorToFloor, slab M.slabThickness |
| railingHeight     | M.balustradeHeight (1.1); singleLineHeight 1.0; doorHeadDefault M.doorHead (2.1)               |
| parts             | + floor "suite"; follow = the part's own, else by kind (the page's KIND table); label kept     |
| rooms             | + floor "suite"; area = float of the string ("153" -> 153.0), null when empty                 |
| openings          | from doors: id, floor, kind door (id starts with D) or passage, label = name, x, y, nx, ny, width (+ exterior) |
| probes            | the living room's west glass (the page walked from 1 m east of that face, westwards)           |
| per-floor maps    | {suite: empty}; furnitureKinds, furniture as they are (floor already "suite")                  |

Stamp: the .ms was made from pres2_model.json, so version.stamp = sha1(source/pres2_model.json)[:12] (f1b95c53eb3d).
"""
from __future__ import annotations

from typing import Any

FLOOR = 'suite'
FLOOR_NAME = 'Suite (FL-01)'
# The page's KIND table (presidential_test/src/make_html.py): whose top follows the wall height setting.
FOLLOW_BY_KIND = {'wall': True, 'column': True, 'lintel': True, 'glass': True, 'low': False, 'builtin': False,
                  'balustrade': False, 'deck': False, 'post': False, 'slab': False}
PROBE_LABEL = "the living room's west glass (its room-side face)"


def _area(a: Any) -> float | None:
    return None if a in (None, '') else float(a)


def convert(M: dict[str, Any]) -> dict[str, Any]:
    parts = []
    for p in M['parts']:
        q = {'floor': FLOOR, 'kind': p['kind'], 'z0': p['z0'], 'z1': p['z1'],
             'follow': p['follow'] if 'follow' in p else FOLLOW_BY_KIND[p['kind']], 'o': p['o'], 'h': p['h']}
        if 'label' in p:
            q['label'] = p['label']
        parts.append(q)
    openings = []
    for d in M['doors']:
        o = {'id': d['id'], 'floor': FLOOR, 'kind': 'door' if d['id'].startswith('D') else 'passage', 'label': d['name'],
             'x': d['x'], 'y': d['y'], 'nx': d['nx'], 'ny': d['ny'], 'width': d['width']}
        if d.get('exterior'):
            o['exterior'] = True
        openings.append(o)
    return {
        'project': 'Presidential suite', 'shortName': 'Presidential suite', 'projectNo': None, 'source': [M['source']],
        'units': M['units'], 'offset': M['offset'], 'photoName': 'Presidential', 'maxPrefix': 'PS',
        'floors': [{'key': FLOOR, 'name': FLOOR_NAME, 'level': M['level'], 'wallHeight': M['floorToFloor'],
                    'slabThickness': M['slabThickness']}],
        'railingHeight': M['balustradeHeight'], 'singleLineHeight': 1.0, 'doorHeadDefault': M['doorHead'],
        'parts': parts,
        'stairs': {FLOOR: {'below': [], 'above': []}}, 'voids': {FLOOR: []}, 'closures': {FLOOR: []},
        'stairOutlines': {FLOOR: []},
        'rooms': [{'floor': FLOOR, 'name': r['name'], 'label': r['label'], 'area': _area(r.get('area')), 'x': r['x'],
                   'y': r['y']} for r in M['rooms']],
        'openings': openings,
        'probes': [{'floor': FLOOR, 'id': 'suite-glass-west', 'what': 'glass facade', 'x': M['probe']['glassWestX'],
                    'y': M['probe']['glassWestY'], 'nx': 1.0, 'ny': 0.0, 'inside': [1], 'label': PROBE_LABEL}],
        'colliderSkins': {FLOOR: []},
        'furnitureKinds': M['furnitureKinds'], 'furniture': M['furniture'],
    }
