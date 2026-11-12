"""Rooms (spaces) and the names that belong to them (docs/rooms/DESIGN.md R-3). Owner: R1.

* `rooms_of_network`: which faces of the network are rooms (R-3.1). A face is a room when it is 1 m2 or more and at
  least half of its edge runs along structure (built parts, opening spans, doorway closings, outline edges, staff
  lines); a face that fails is an enclosed shape (a bed, a table, a sofa corner drawn on a wall layer), joined to the
  room across its longest stretch of edge that is not structure, and counted. The faces of a free-standing object (a
  detached piece under 12 m2 with no opening on it) are not rooms either.
* `spaces_of`: the rooms as contracts.SpaceGeo rows, ids `<floor key>-R<nnn>` numbered by each room's label point.
* `names_of`: the drawn room names of a floor (R-3.2): short names kept, tags dropped, an area written in the name
  split off (a comma or a point as the decimal mark).
* `name_rooms`: which room each name belongs to (R-3.2's five rules), the room's own name, the staff names (R-3.3).
"""
from __future__ import annotations

import math
import re

from shapely.geometry import Point, Polygon
from shapely.ops import linemerge, polylabel, unary_union
from shapely.strtree import STRtree

from .bank import polys

ROW = 0.5                   # m: the rows the ids are numbered in (R-3.1)
MIN_FACE = 1.0              # m2
HALF = 0.5                  # a room's edge is at least this share structure
ON_STRUCT = 0.03            # m: an edge within this of structure runs along it
ASIDE_LEFT = 0.25           # a face with less than this share of its edge off the set-aside lines is no room
NEAR_WALL = 0.3             # m: a label point this close to a wall moves to the representative point
JOIN = 0.04                 # m: the closing that joins an enclosed shape to its room (strips of up to 6 cm between them)
HALF_STRIP = 0.01           # m: a room reaches the drawn line, the middle of its 2 cm strip (see rooms_of_network)
ACROSS = 0.10               # m: the room on the other side of a loose edge lies within this
FIT = (0.15, 0.5)           # a written area fits a room within 15 %, or 0.5 m2
BY_AREA = 3.0               # m: a name placed by its written area looks for rooms this near
BY_DISTANCE = 1.5           # m: a name in no room takes the nearest room within this
#: an area written at the end of a name: "Bar 7,6m2", "Master Bedroom: 47m2", "Foyer 10 m²"
AREA_IN_NAME = re.compile(r'[\s:]*(\d+(?:[.,]\d+)?)\s*(m²|m2|sq\.?\s*m\.?|sqm)\s*$', re.I)
NUMBER = re.compile(r'\d+(?:[.,]\d+)?')


def lines_in(g) -> list:
    """Every LineString of a geometry (a line, a multi-line, a collection)."""
    if g is None or g.is_empty:
        return []
    if g.geom_type == 'LineString':
        return [g]
    return [x for y in getattr(g, 'geoms', []) for x in lines_in(y)]


def merged_lines(g) -> list:
    """The line work of a geometry joined into its longest runs."""
    ls = [l for l in lines_in(g) if l.length > 0]
    if not ls:
        return []
    return lines_in(linemerge(ls) if len(ls) > 1 else ls[0])


def label_point(poly) -> Point:
    """A room's label point (R-3.1): its pole of inaccessibility (tolerance 0.05 m); a point within 0.3 m of a wall
    moves to the room's representative point."""
    p = max(polys(poly), key=lambda q: q.area) if poly.geom_type != 'Polygon' else poly
    try:
        at = polylabel(p, tolerance=0.05)
    except Exception:                                      # a degenerate outline: shapely's own point
        return p.representative_point()
    if not p.contains(at) or p.boundary.distance(at) < NEAR_WALL:
        return p.representative_point()
    return at


def spaces_of(fb, faces, X):
    """The floor's rooms -> [contracts.SpaceGeo], ids `<floor key>-R<nnn>` numbered by each room's label point: rows
    from the top of the plan (y falling, 0.5 m rows), left to right within a row (R-3.1)."""
    rows = []
    for f in faces:
        at = label_point(f)
        rows.append((-math.floor(at.y / ROW), round(at.x, 3), round(at.y, 3), f, at))
    rows.sort(key=lambda r: r[:3])
    return [{'id': f'{fb["key"]}-R{n:03d}', 'poly': f, 'area': round(f.area, 1), 'at': (at.x, at.y), 'source': 'network',
             'name': '', 'names': [], 'ceiling': True} for n, (_r, _x, _y, f, at) in enumerate(rows, 1)]


def rooms_of_network(fb, pieces, struct, outlines, staff, X, aside=None):
    """R-3.1 on the pieces of the closed network (network.pieces_of) -> (every face of 1 m2 or more, the rooms as
    contracts.SpaceGeo, the number of enclosed shapes left out). `struct`: the structure (built parts, spans, doorway
    closings, outline edges, staff lines); `outlines`: the closed room outlines; `staff`: the staff lines; `aside`: the
    strips of the lines staff set aside that still bound the floor (R-2.1 point 7). The stretches of a face's edge that
    run along those lines alone are left out of BOTH sides of the half test (RR FID-1): a ring of set-aside furniture
    lines along a room's walls neither makes nor unmakes a room (the new suite's living room failed the test once its
    single lines were set aside); a face with under a quarter of its edge left to judge is an enclosed shape."""
    faces, rooms, shapes = [], [], []                      # rooms / shapes: indices into faces
    owner = []                                             # the piece each face is a hole of
    for pi, q in enumerate(pieces):
        for h in q['poly'].interiors:
            f = Polygon(h)
            if f.area >= MIN_FACE:
                faces.append(f); owner.append(pi)
    order = sorted(range(len(faces)), key=lambda i: (round(faces[i].bounds[0], 3), round(faces[i].bounds[1], 3), round(faces[i].area, 3)))
    faces, owner = [faces[i] for i in order], [owner[i] for i in order]
    if not faces:
        return [], [], 0
    near = struct.buffer(ON_STRUCT) if not struct.is_empty else None
    beside = aside.buffer(ON_STRUCT) if aside is not None and not aside.is_empty else None
    if beside is not None and near is not None:
        beside = beside.difference(near)
    free = {}
    for i, f in enumerate(faces):
        edge = f.exterior
        on = edge.intersection(near).length if near is not None else 0.0
        judged = edge.length - (edge.intersection(beside).length if beside is not None else 0.0)
        if pieces[owner[i]]['object'] or on < HALF * judged or judged < ASIDE_LEFT * edge.length:
            shapes.append(i)
            free[i] = edge.difference(near) if near is not None else edge
        else:
            rooms.append(i)
    # an enclosed shape joins the face across its longest stretch of edge that is not structure
    tree = STRtree(faces)
    joins = {}
    for i in shapes:
        runs = sorted(merged_lines(free[i]), key=lambda l: (-round(l.length, 4), round(l.bounds[0], 4), round(l.bounds[1], 4)))
        for run in runs[:3]:
            best = None
            for j in sorted(int(k) for k in tree.query(run, predicate='dwithin', distance=ACROSS)):
                if j == i:
                    continue
                share = run.intersection(faces[j].buffer(ACROSS)).length
                if share > 0.05 and (best is None or share > best[0] + 1e-9):
                    best = (share, j)
            if best is not None:
                joins[i] = best[1]
                break
    polys_of = {i: [faces[i]] for i in rooms}
    for i in shapes:                                       # follow the joins to a room (a ring of shapes joins nothing)
        seen, j = {i}, joins.get(i)
        while j is not None and j not in polys_of and j not in seen:
            seen.add(j); j = joins.get(j)
        if j in polys_of:
            polys_of[j].append(faces[i])
    # the rooms' polygons: the room and its shapes as one outline, less the buildings standing free inside it
    with_rooms = {owner[i] for i in rooms}
    islands = [(pi, pieces[pi]['outline']) for pi in sorted(with_rooms)]
    out_tree = STRtree(outlines) if outlines else None
    built = []
    for i in rooms:
        g = polys_of[i][0]
        if len(polys_of[i]) > 1:
            u = unary_union(polys_of[i]).buffer(JOIN, join_style='mitre').buffer(-JOIN, join_style='mitre')
            g = max(polys(u), key=lambda q: q.area)
            g = Polygon(g.exterior)
        inner = [o for pi, o in islands if pi != owner[i] and g.contains(o.representative_point()) and o.area < g.area]
        if inner:
            cut = g.difference(unary_union(inner))
            g = max(polys(cut), key=lambda q: q.area) if not cut.is_empty else g
        # a face ends on the inner edge of the 2 cm strips of the drawn lines; the room reaches the lines themselves
        # (so its area is the area between the wall faces, as a designer measures it)
        grown = g.buffer(HALF_STRIP, join_style='mitre')
        if grown.geom_type == 'Polygon' and grown.is_valid:
            g = grown
        source = 'network'
        if not staff.is_empty and g.exterior.distance(staff) <= ON_STRUCT:
            source = 'staff'
        elif out_tree is not None:
            edge = g.exterior
            along = sum(edge.intersection(outlines[int(k)].exterior.buffer(ON_STRUCT)).length
                        for k in out_tree.query(edge, predicate='intersects'))
            if along >= HALF * edge.length:
                source = 'outline'
        built.append((g, source))
    spaces = spaces_of(fb, [g for g, _ in built], X)
    by_id = {id(g): s for g, s in built}
    for s in spaces:
        s['source'] = by_id[id(s['poly'])]
    return faces, spaces, len(shapes)


# --------------------------------------------------------------------------------------------------------------- names
def area_value(text: str | None) -> float | None:
    """The number of a written area ("3.2 m²", "7,6m2"), a comma or a point as the decimal mark."""
    m = NUMBER.search(text or '')
    return float(m.group().replace(',', '.')) if m else None


def names_of(items, X):
    """The drawn room names of a floor (R-3.2) -> ([{ name, area, areaValue, x, y }], the texts that are not names,
    [(text, x, y)] of those). Texts on room-name layers, as today, with three changes: a text is a name when it has 2
    or more letters, is not a stair word and is not a tag (3 letters or fewer and at least one digit); an area written
    in the name is split off; the written area stays as written for the label. The tag line below a name (Revit's
    "12 m²", "Not Enclosed") is paired as today, and a name with one is kept whatever it reads."""
    texts = [d for d in items if 'room-name' in d['roles'] and 'ignore' not in d['roles'] and d.get('text', '').strip()]
    tags = [d for d in texts if X.V.tag_line.match(d['text'])]
    tag_ids = {id(d) for d in tags}
    out, skipped, skipped_at = [], [], []
    for d in texts:
        if id(d) in tag_ids:
            continue
        name = ' '.join(d['text'].split())
        x, y = d['ins']
        tag = min((t for t in tags if abs(t['ins'][0] - x) < 0.3 and 0 < y - t['ins'][1] < 0.35),
                  key=lambda t: y - t['ins'][1], default=None)
        area = None
        if tag is not None and not re.search('[a-zA-Z]{3}', tag['text'].replace('m²', '').replace('m2', '')):
            area = ' '.join(tag['text'].split())
        m = AREA_IN_NAME.search(name)
        if m and name[:m.start()].strip(' :'):
            if area is None:
                area = name[m.start():].lstrip(' :').strip()
            name = name[:m.start()].rstrip(' :').strip()
        letters = sum(ch.isalpha() for ch in name)
        is_tag = letters <= 3 and any(ch.isdigit() for ch in name)
        if tag is None and (letters < 2 or X.V.is_stair_word(name) or is_tag):
            skipped.append(name); skipped_at.append((name, x, y))
            continue
        out.append({'name': name, 'area': area, 'areaValue': area_value(area), 'x': x, 'y': y})
    return out, skipped, skipped_at


def fits(room_area: float, written: float) -> bool:
    return abs(room_area - written) <= max(FIT[0] * written, FIT[1])


def name_rooms(spaces, rooms, staff_names=()):
    """Gives each drawn name (names_of's rows, or bank.rooms_of's) the room it belongs to, the first rule that applies
    (R-3.2): 1. where it stands, when it has no written area or the room fits it; 2. by written area, one-to-one for
    the whole floor, among the rooms within 3.0 m in which no name stands by rule 1 and whose area fits (the smallest
    area error first, then the nearest); 3. where it stands, though the area does not fit; 4. the nearest room within
    1.5 m; 5. no room. Sets room['space'], fills each space's `names` (reading order) and its own `name` (the staff
    name, else the name whose written area fits, else the first in reading order).
    staff_names: [(space id, name)] of the room fixes (R-3.3). -> (the names in no room, the spaces with several names)."""
    pts = [Point(r['x'], r['y']) for r in rooms]
    exact = [s['poly'].area for s in spaces]
    stand = [next((j for j, s in enumerate(spaces) if s['poly'].contains(p)), None) for p in pts]
    written = [r.get('areaValue') if 'areaValue' in r else area_of_text(r.get('area')) for r in rooms]
    home: dict[int, int] = {}
    for i, j in enumerate(stand):                          # rule 1
        if j is not None and (written[i] is None or fits(exact[j], written[i])):
            home[i] = j
    taken = set(home.values())
    pairs = []
    for i, w in enumerate(written):                        # rule 2
        if i in home or w is None:
            continue
        for j, s in enumerate(spaces):
            if j in taken or not fits(exact[j], w):
                continue
            d = s['poly'].distance(pts[i])
            if d <= BY_AREA:
                pairs.append((round(abs(exact[j] - w), 4), round(d, 4), i, j))
    used = set()
    for _err, _d, i, j in sorted(pairs):
        if i in home or j in used:
            continue
        home[i] = j; used.add(j)
    for i, j in enumerate(stand):                          # rule 3
        if i not in home and j is not None:
            home[i] = j
    homeless = []
    for i, r in enumerate(rooms):                          # rules 4 and 5
        if i in home:
            continue
        near = sorted((round(s['poly'].distance(pts[i]), 4), j) for j, s in enumerate(spaces))
        if near and near[0][0] <= BY_DISTANCE:
            home[i] = near[0][1]
        else:
            homeless.append(r)
    reading = sorted(home, key=lambda i: (-math.floor(rooms[i]['y'] / ROW), round(rooms[i]['x'], 3), round(rooms[i]['y'], 3), i))
    for s in spaces:
        s['names'] = []
    fitting: dict[int, str] = {}
    for i in reading:
        s = spaces[home[i]]
        rooms[i]['space'] = s['id']
        s['names'].append(rooms[i]['name'])
        if written[i] is not None and fits(exact[home[i]], written[i]) and home[i] not in fitting:
            fitting[home[i]] = rooms[i]['name']
    staff = dict(staff_names)
    for j, s in enumerate(spaces):
        s['name'] = staff.get(s['id']) or fitting.get(j) or (s['names'][0] if s['names'] else '')
    return homeless, [s for s in spaces if len(s['names']) > 1]


def area_of_text(text) -> float | None:
    """The written area of a bank.rooms_of row (its `area` text), or None."""
    return area_value(text) if text else None
