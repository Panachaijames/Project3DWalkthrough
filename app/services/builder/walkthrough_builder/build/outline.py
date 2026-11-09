"""Outline suggestions (docs/upload/DESIGN.md U-10.5 `outlineWalls: 'suggest'`, U-10.6 fix 3).

The free edges of the room outlines (closed polylines on `room-outline` layers): edge stretches of 0.5 m or more with no
wall within 0.35 m. Each becomes a flagged suggestion: a 0.20 m wall on the side away from the room, or glass when a
railing lies within 0.5 m outside. Nothing is built until staff accept it (`fixes.outlineEdges`, the same edge within
0.05 m, either order): an accepted edge is added to the wall solid (or the glass) before the openings are cut. The
suite's three hand-added corridor runs lie 63 % on such edges.
"""
from __future__ import annotations

import math

from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union

from . import items as I
from .bank import OUTLINE_GLASS, OUTLINE_WALL, lines_of, rect, segs_of, unit

FREE = 0.35         # m: no wall within this of a free edge
MIN_EDGE = 0.5      # m: a free stretch at least this long is suggested
RAIL_NEAR = 0.5     # m: a railing this close outside makes it glass
SAME = 0.05         # m: an accepted fix's edge matches a suggestion within this


def _same_edge(e, f) -> bool:
    (a, b), (c, d) = e, f
    return (math.dist(a, c) <= SAME and math.dist(b, d) <= SAME) or (math.dist(a, d) <= SAME and math.dist(b, c) <= SAME)


def suggestions(items: list[dict], W: list, shift=(0.0, 0.0)) -> list[dict]:
    """Free outline edges of one floor -> [{edge (sheet m), kind, length, state: 'open', a, b, out (in the shifted
    frame, for building)}]. `items`: the floor's per-item reading (shifted by `shift` onto floor 0's frame)."""
    rooms = []
    for d in items:
        if 'room-outline' not in d['roles']:
            continue
        ring = I.closed_ring(d)
        if not ring:
            continue
        g = Polygon(ring).buffer(0)
        if g.is_empty or g.area < 0.5:
            continue
        rooms.append((d, g))
    if not rooms:
        return []
    near = unary_union(W).buffer(FREE) if W else Polygon()
    rails = unary_union([LineString([(s[0], s[1]), (s[2], s[3])]) for d in items
                         if 'railing' in d['roles'] and 'pts' in d for s in segs_of(d, False)])
    out = []
    for d, room in rooms:
        for x1, y1, x2, y2 in segs_of(d):
            for part in lines_of(LineString([(x1, y1), (x2, y2)]).difference(near)):
                if part.length < MIN_EDGE:
                    continue
                (ax, ay), (bx, by) = part.coords[0], part.coords[-1]
                u = unit((bx - ax, by - ay))
                n = (-u[1], u[0])
                m = ((ax + bx) / 2, (ay + by) / 2)
                sgn = -1.0 if room.contains(Point(m[0] + n[0] * 0.05, m[1] + n[1] * 0.05)) else 1.0
                outside = rect((ax, ay), u, 0, part.length, 0.0, RAIL_NEAR) if sgn > 0 else \
                    rect((ax, ay), u, 0, part.length, -RAIL_NEAR, 0.0)
                kind = 'glass' if not rails.is_empty and rails.intersects(outside) else 'wall'
                out.append({'edge': [[round(ax - shift[0], 3), round(ay - shift[1], 3)],
                                     [round(bx - shift[0], 3), round(by - shift[1], 3)]],
                            'kind': kind, 'length': round(part.length, 3), 'state': 'open',
                            '_a': (ax, ay), '_u': u, '_L': part.length, '_sgn': sgn})
    return out


def apply_fixes(sugg: list[dict], fixes: list[tuple[int, dict]]) -> tuple[list, list, list[dict]]:
    """Matches the floor's outline-edge fixes [(fix index, OutlineEdgeFix)] to the suggestions -> (walls to add, glass
    to add (shifted frame), FixesReport.outlineEdges rows). A matched suggestion's state becomes 'accepted' (as wall or
    glass) or 'refused' (as 'none')."""
    walls, glass, rows = [], [], []
    for fi, f in fixes:
        e = ((float(f['a'][0]), float(f['a'][1])), (float(f['b'][0]), float(f['b'][1])))
        s = next((s for s in sugg if _same_edge(e, (tuple(s['edge'][0]), tuple(s['edge'][1])))), None)
        rows.append({'fix': fi, 'matched': s is not None})
        if s is None:
            continue
        as_ = f.get('as')
        if as_ == 'none':
            s['state'] = 'refused'
            continue
        s['state'] = 'accepted'
        t = OUTLINE_WALL if as_ == 'wall' else OUTLINE_GLASS
        poly = rect(s['_a'], s['_u'], 0, s['_L'], 0.0, t) if s['_sgn'] > 0 else rect(s['_a'], s['_u'], 0, s['_L'], -t, 0.0)
        (walls if as_ == 'wall' else glass).append(poly)
    return walls, glass, rows


def public(sugg: list[dict]) -> list[dict]:
    """The OutlineSuggestion records (contracts.py) without the private build keys."""
    return [{'edge': s['edge'], 'kind': s['kind'], 'length': s['length'], 'state': s['state']} for s in sugg]
