"""PlanGeometry (plan.json.gz): the whole sheet for the browser's canvas (docs/upload/DESIGN.md U-7.5, U-7.2;
upload-contracts.ts section 4).

Every item (no area filter), in sheet metres (reader frame x `units.UNITS_K[units]`), curves already flattened by the
reader, polylines and hatch loops of 3 or more points simplified at 5 mm (shapely `simplify(0.005,
preserve_topology=False)`; a closed ring simplified closed and written without its repeated last point, the scaffold's
fixture convention), quantised to 1 cm from `origin` (the drawing extents' lower-left corner floored to 1 m). Parallel
arrays, one entry per polyline:
  type 0 open line or polyline, 1 closed polyline or circle, 2 solid hatch loop, 3 pattern hatch loop (one entry per
  loop, all with the hatch's key), 4 text anchor (TEXT, MTEXT, ATTRIB: the insertion point), 5 insert anchor (every
  INSERT at every depth: its insertion point, so the canvas can pick a whole block by key prefix).
Per entry the item's `sig`, `rsig` and element id (an index into `elementIds`, -1 for none), computed here from the
cache item through keys.py and names.py (`refs()`), so the browser copies them into an ItemRef and never derives them
from the lossy points (U-7.5):
  * elementId = names.element_id of the item's block chain: its `path`, plus its own block name for an INSERT (its
    INSERT's block name for an ATTRIB, which belongs to that INSERT);
  * the element's INSERT is the item whose key is the first `depth + 1` parts of the item's key (names.element_depth;
    an ATTRIB's key is read up to its '@');
  * sig = keys.sig(item, k); rsig = keys.rsig(item, element INSERT, k), '' without an element id (or when the element's
    INSERT left no item).
Points that are not finite or lie beyond 1e9 m (a broken or hostile file) drop their entry; its key is then absent.
Owner: U2.
"""
from __future__ import annotations

import math

import shapely

from . import keys, names
from . import units as U
from .areas import LIMIT
from .drawing import robust_box

QUANTUM = 0.01
SIMPLIFY = 0.005
TEXT_TYPES = ('TEXT', 'MTEXT', 'ATTRIB')


def element_chain(d: dict) -> list[str]:
    """The block names an item's element id is read from (module text)."""
    chain = names.split_path(d.get('path', ''))
    if d['t'] == 'INSERT':
        chain.append(d.get('name', ''))
    elif d['t'] == 'ATTRIB' and d.get('block'):
        chain.append(d['block'])
    return chain


def element_key(d: dict) -> tuple[str | None, str | None]:
    """-> (element id, the key of the element's INSERT) of one cache item, or (None, None)."""
    chain = element_chain(d)
    depth = names.element_depth(chain)
    if depth is None:
        return None, None
    parts = d['k'].split('@', 1)[0].split('/')
    return names.element_id(chain), '/'.join(parts[:depth + 1])


def ref_of(d: dict, inserts: dict[str, dict], k: float) -> tuple[str, str, str | None]:
    """(sig, rsig, element id) of one cache item; `inserts` = INSERT items by key. A signature that cannot be made (a
    coordinate that is not a finite number: keys.py hashes strict JSON) is '' (such an item has no plan entry)."""
    eid, ekey = element_key(d)
    el = inserts.get(ekey) if ekey is not None else None
    try:
        sig = keys.sig(d, k)
    except (ValueError, TypeError, OverflowError):
        sig = ''
    try:
        rsig = keys.rsig(d, el, k) if el is not None else ''
    except (ValueError, TypeError, OverflowError):
        rsig = ''
    return sig, rsig, eid


def refs(items: list[dict], k: float) -> list[tuple[str, str, str | None]]:
    """(sig, rsig, element id) per cache item, in order (U-7.2). `k` = reader frame -> metres."""
    inserts = {d['k']: d for d in items if d['t'] == 'INSERT'}
    return [ref_of(d, inserts, k) for d in items]


def _finite(P) -> bool:
    for x, y in P:
        if not (math.isfinite(x) and math.isfinite(y) and abs(x) < LIMIT and abs(y) < LIMIT):
            return False
    return True


def plan_geometry(items: list[dict], *, source: str, units: str, extents: list[float] | None = None) -> dict:
    """Cache items (reader frame) -> PlanGeometry. `extents` (sheet m, DrawingRead.extents) gives the origin; computed
    here (the same 1 - 99 % rule) when not given."""
    k = U.UNITS_K[units]
    if extents is None:
        from .areas import item_points, sample
        extents = robust_box([p for d in items for p in sample(item_points(d))], k)
    origin = [float(math.floor(extents[0])), float(math.floor(extents[1]))] if extents else [0.0, 0.0]
    ox, oy = origin
    layers: list[str] = []
    lidx: dict[str, int] = {}
    eids: list[str] = []
    eidx: dict[str, int] = {}
    cols = {'key': [], 'layer': [], 'type': [], 'first': [], 'count': [], 'sig': [], 'rsig': [], 'eid': []}
    pts: list[int] = []
    # polylines of 3+ points, simplified together: (entry index in cols, points in sheet m, closed)
    pending: list[tuple[int, list, bool]] = []

    def emit(d: dict, typ: int, P: list, ref: tuple, simplify: bool = False, closed: bool = False) -> None:
        lay = d['lay']
        if lay not in lidx:
            lidx[lay] = len(layers)
            layers.append(lay)
        sig, rsig, eid = ref
        if eid is not None and eid not in eidx:
            eidx[eid] = len(eids)
            eids.append(eid)
        cols['key'].append(d['k'])
        cols['layer'].append(lidx[lay])
        cols['type'].append(typ)
        cols['first'].append(0)
        cols['count'].append(0)
        cols['sig'].append(sig)
        cols['rsig'].append(rsig)
        cols['eid'].append(eidx[eid] if eid is not None else -1)
        if simplify and len(P) >= 3:
            pending.append((len(cols['key']) - 1, P, closed))
        else:
            pending.append((len(cols['key']) - 1, P, None))

    inserts = {d['k']: d for d in items if d['t'] == 'INSERT'}
    for d in items:
        t = d['t']
        if t == 'INSERT' or t in TEXT_TYPES:
            P = [(d['ins'][0] * k, d['ins'][1] * k)]
            if _finite(P):
                emit(d, 5 if t == 'INSERT' else 4, P, ref_of(d, inserts, k))
        elif 'loops' in d:
            typ = 2 if d.get('solid') else 3
            loops = [[(x * k, y * k) for x, y in loop] for loop in d['loops']]
            loops = [P for P in loops if P and _finite(P)]
            ref = ref_of(d, inserts, k) if loops else None
            for P in loops:
                emit(d, typ, P, ref, simplify=True, closed=True)
        elif d.get('pts'):
            P = [(x * k, y * k) for x, y in d['pts']]
            if _finite(P):
                closed = bool(d.get('closed'))
                emit(d, 1 if closed else 0, P, ref_of(d, inserts, k), simplify=True, closed=closed)

    # simplify every polyline of 3+ points at 5 mm in one vectorised call (the same as one LineString at a time). A
    # closed ring is simplified closed (its first point appended when the walk did not repeat it) and written without
    # the repeated last point: a closed entry (types 1 - 3) is closed by the canvas, never by a point.
    todo = [(n, P + [P[0]] if closed and P[0] != P[-1] else P) for n, P, closed in pending if closed is not None]
    ring = {n for n, _P, closed in pending if closed}
    done = {}
    if todo:
        simple = shapely.simplify([shapely.LineString(P) for _n, P in todo], SIMPLIFY, preserve_topology=False)
        for (n, P), g in zip(todo, simple):
            s = [tuple(c) for c in shapely.get_coordinates(g).tolist()]
            if n in ring and len(s) > 1 and s[0] == s[-1]:
                s = s[:-1]
            if len(s) >= 2:
                done[n] = s
    for n, P, _closed in pending:
        P = done.get(n, P)
        cols['first'][n] = len(pts) // 2
        cols['count'][n] = len(P)
        for x, y in P:
            pts.append(round((x - ox) / QUANTUM))
            pts.append(round((y - oy) / QUANTUM))
    return {'format': 'plan-geometry/1', 'source': source, 'units': units, 'origin': origin, 'quantum': QUANTUM,
            'layers': layers, 'items': cols, 'elementIds': eids, 'pts': pts}


def decode(plan: dict) -> list[dict]:
    """PlanGeometry -> one dict per entry {key, layer, type, points (sheet m), sig, rsig, elementId} (tests, tools)."""
    it = plan['items']
    ox, oy = plan['origin']
    q = plan['quantum']
    out = []
    for i in range(len(it['key'])):
        f, c = it['first'][i], it['count'][i]
        P = [(ox + plan['pts'][2 * j] * q, oy + plan['pts'][2 * j + 1] * q) for j in range(f, f + c)]
        e = it['eid'][i]
        out.append({'key': it['key'][i], 'layer': plan['layers'][it['layer'][i]], 'type': it['type'][i], 'points': P,
                    'sig': it['sig'][i], 'rsig': it['rsig'][i], 'elementId': plan['elementIds'][e] if e >= 0 else None})
    return out
