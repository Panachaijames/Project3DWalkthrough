"""Rooms (spaces) and the names that belong to them (docs/rooms/DESIGN.md R-3). Owner: R1.

THE TRACER of the rooms scaffold R0 (see network.py): every face is a room, and a drawn name belongs to the room its
point stands in. R1's: which faces are rooms (R-3.1), names by written area and one-to-one (R-3.2), staff names
(R-3.3), the names in no room and the rooms with several names as flags.
"""
from __future__ import annotations

import math

from shapely.geometry import Point


ROW = 0.5                   # m: the rows the ids are numbered in (R-3.1)


def spaces_of(fb, faces, X):
    """The floor's rooms -> [contracts.SpaceGeo], ids `<floor key>-R<nnn>` numbered by each room's label point: rows
    from the top of the plan (y falling, 0.5 m rows), left to right within a row (R-3.1). The tracer's label point is
    the centroid when it lies in the room, else shapely's representative point (R1: the pole of inaccessibility)."""
    rows = []
    for f in faces:
        at = f.centroid if f.contains(f.centroid) else f.representative_point()
        rows.append((-math.floor(at.y / ROW), round(at.x, 3), round(at.y, 3), f, at))
    rows.sort(key=lambda r: r[:3])
    return [{'id': f'{fb["key"]}-R{n:03d}', 'poly': f, 'area': round(f.area, 1), 'at': (at.x, at.y), 'source': 'network',
             'name': '', 'names': [], 'ceiling': True} for n, (_r, _x, _y, f, at) in enumerate(rows, 1)]


def name_rooms(spaces, rooms):
    """Gives each drawn name (bank.rooms_of's rows { name, area, x, y }, sheet m) the room it stands in: sets
    room['space'] and adds the name to the space's `names`; a space's own `name` is its first drawn name.
    -> (the names in no room, the spaces with several names)."""
    homeless = []
    for r in rooms:
        p = Point(r['x'], r['y'])
        home = next((s for s in spaces if s['poly'].contains(p)), None)
        if home is None:
            homeless.append(r)
            continue
        r['space'] = home['id']
        home['names'].append(r['name'])
        if not home['name']:
            home['name'] = r['name']
    return homeless, [s for s in spaces if len(s['names']) > 1]
