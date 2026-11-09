"""Geometry signatures of drawing items, for set-asides that survive a re-export (docs/upload/DESIGN.md U-7.2, U-10.6).

* `sig(item)`: sha1[:12] of the item's type, layer and points rounded to 1 mm in metres, by the bank builder's
  `plan_items._signature` rule (lines and open polylines read in one direction, closed rings from their lowest point,
  hatch loops as drawn, texts by text and insertion point, INSERTs by name, insertion point, turn, scale and path).
* `rsig(item, element_insert)`: the same hash with the points taken relative to the element's INSERT (minus its
  insertion point, turned back by its world turn, rounded to 1 mm), so it survives a re-export that moves or renumbers
  the element; '' when the item has no element. For INSERT items the relative form keeps the block's family instead of
  its name and drops the path (both carry element ids that a renumbering changes).

Items are prims items (detector/tools/prims.py: t, lay, path, pts | loops | ins + text | name + ins + rot + sx + sy).
`k` is the factor to metres: 1.0 for items already in metres (the builder's scaled items), `UNITS[units]` for cache
items (DXF units / 1000), applied exactly as `openings.scaled` does (`x * k`), so both give the same floats.
The reader (U2) computes these per item for PlanGeometry; the builder's matcher (U3) computes them again from the cache:
both through this module. Scaffold U0; frozen after it.
"""
from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping
from typing import Any

from .names import family

ND = 3          # 1 mm in metres


def _r(v: float) -> float:
    # rounded to 1 mm; -0.0 and 0.0 are the same coordinate
    return round(v, ND) + 0.0


def _hash(parts: Any) -> str:
    data = json.dumps(parts, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode('utf-8')
    return hashlib.sha1(data).hexdigest()[:12]


def _ring(p: list[tuple[float, float]], t: str, closed: bool) -> list[tuple[float, float]]:
    # plan_items._signature: a LINE or an open polyline whose first point lies after its last is read backwards; a closed
    # one starts at its lowest point
    if t == 'LINE' or (not closed and len(p) > 1 and p[0] > p[-1]):
        p = p[::-1]
    if closed and len(p) > 2:
        k = p.index(min(p))
        p = p[k:] + p[:k]
    return p


def _parts(d: Mapping[str, Any], f, rot0: float | None) -> list[Any]:
    """The signature tuple of one item with its points mapped by f (metres in, metres out)."""
    t, lay = d['t'], d['lay']
    if t == 'INSERT':
        x, y = f(d['ins'])
        if rot0 is None:
            return [t, lay, d['name'], _r(x), _r(y), round(d['rot'], 1) + 0.0, d['sx'], d['sy'], d.get('path', '')]
        turn = round((d['rot'] - rot0) % 360.0, 1) % 360.0 + 0.0
        return [t, lay, family(d['name']), _r(x), _r(y), turn, d['sx'], d['sy']]
    if d.get('pts'):
        p = [(_r(x), _r(y)) for x, y in (f(q) for q in d['pts'])]
        return [t, lay, _ring(p, t, bool(d.get('closed')))]
    if 'loops' in d:
        return [t, lay, [[[_r(x), _r(y)] for x, y in (f(q) for q in loop)] for loop in d['loops']]]
    if 'text' in d and 'ins' in d:
        x, y = f(d['ins'])
        return [t, lay, d['text'], _r(x), _r(y)]
    return [t, lay]


def sig(item: Mapping[str, Any], k: float = 1.0) -> str:
    """ItemRef.sig: 12 hex of the item's type, layer and points rounded to 1 mm (sheet metres)."""
    def f(q):
        return (q[0] * k, q[1] * k)
    return _hash(_parts(item, f, None))


def rsig(item: Mapping[str, Any], element_insert: Mapping[str, Any] | None, k: float = 1.0) -> str:
    """ItemRef.rsig: 12 hex, the signature with points relative to `element_insert` (the INSERT item of the item's
    element: minus its insertion point, turned back by its world turn `rot`), or '' without an element."""
    if not element_insert:
        return ''
    ox, oy = element_insert['ins'][0] * k, element_insert['ins'][1] * k
    rot0 = float(element_insert.get('rot', 0.0))
    a = math.radians(-rot0)
    c, s = math.cos(a), math.sin(a)

    def f(q):
        x, y = q[0] * k - ox, q[1] * k - oy
        return (x * c - y * s, x * s + y * c)
    return _hash(_parts(item, f, rot0))
