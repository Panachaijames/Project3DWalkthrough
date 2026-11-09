"""Reading a source's cache items into floors (docs/upload/DESIGN.md U-9.1, U-10.3 step 1).

The cache (U-7.1; the prototype prims.pkl has the same items without `k`) holds every model-space item with blocks
unpacked, in the prims frame (DXF units / 1000): {t, lay, depth, path, h, k, pts | loops | ins + text | name + ins +
rot + sx + sy, closed, lt}. A floor gets two readings of it:

* the PER-ITEM reading (the detector and the line readers: walls, glass, stairs, railings, room names): an item belongs
  to the first floor of its source whose area holds it (`area_tagger` semantics, after scaling to metres); an item with
  no points belongs to no floor; then `plan_items.load_floor`'s dedupe (`_signature`, on the item as cached) and its
  scaling, in cache order;
* the WHOLE-SUBTREE reading (the INSERT readers: furniture pieces, door blocks, `block_kids`, `drawn_inside`): every
  INSERT goes with its whole subtree to the floor whose area holds the majority of its subtree's drawn points; a
  subtree that holds other INSERTs and has no majority is walked into (its own INSERT item read per item); one that
  holds none is left out and counted (`subtreesOutside`, on the floor that held most of it). Under `wholeFile` both
  readings are the same items in the same order (the bank cannot move).

The functions here are ports of `bank_test/src/plan_items.py` (linetype, is_continuous, _signature, _scaled,
closed_ring, item_points), unchanged in what they compute.
"""
from __future__ import annotations

import math
import pickle
from collections.abc import Callable, Mapping
from pathlib import Path

import numpy as np

from .. import roles as R

#: prims frame -> metres factor per unit (openings.UNITS / plan_items.UNITS: the cache is DXF units / 1000)
UNITS = {'mm': 1.0, 'cm': 10.0, 'm': 1000.0, 'in': 25.4, 'inch': 25.4, 'ft': 304.8}
#: metres per drawing unit (the bank builder's UNITS_M: for sizes read from names, e.g. 1000X2400 in a mm drawing)
UNITS_M = {'mm': 0.001, 'cm': 0.01, 'm': 1.0, 'in': 0.0254, 'inch': 0.0254, 'ft': 0.3048}
CONTINUOUS = {'CONTINUOUS', 'BYLAYER', 'BYBLOCK', ''}


# ------------------------------------------------------------------------------------- plan_items.py, unchanged
def linetype(d, layer_lt):
    lt = d.get('lt') or 'BYLAYER'
    if lt.upper() == 'BYLAYER': lt = layer_lt.get(d['lay'], 'Continuous') or 'Continuous'
    if lt.upper() == 'BYBLOCK': lt = 'Continuous'
    return lt


def is_continuous(lt):
    u = lt.upper().split('$')[-1]
    return u in CONTINUOUS or u.startswith('CONTINUOUS')


def signature(d, nd=3):
    """Identical geometry on the same layer (a block inserted twice, copies) -> the same signature."""
    t = d['t']
    if t == 'INSERT':
        return (t, d['lay'], d['name'], round(d['ins'][0], nd), round(d['ins'][1], nd), round(d['rot'], 1), d['sx'], d['sy'], d['path'])
    if 'pts' in d:
        p = [(round(x, nd), round(y, nd)) for x, y in d['pts']]
        if t == 'LINE' or (not d.get('closed') and len(p) > 1 and p[0] > p[-1]): p = p[::-1]
        if d.get('closed') and len(p) > 2:
            k = p.index(min(p)); p = p[k:] + p[:k]
        return (t, d['lay'], tuple(p))
    if 'loops' in d:
        return (t, d['lay'], tuple(tuple((round(x, nd), round(y, nd)) for x, y in l) for l in d['loops']))
    if 'text' in d:
        return (t, d['lay'], d['text'], round(d['ins'][0], nd), round(d['ins'][1], nd))
    return (t, d['lay'], id(d))


def scaled(d, k):
    if k == 1.0: return d
    d = dict(d)
    if 'pts' in d: d['pts'] = [[x * k, y * k] for x, y in d['pts']]
    if 'loops' in d: d['loops'] = [[[x * k, y * k] for x, y in l] for l in d['loops']]
    if 'ins' in d: d['ins'] = [d['ins'][0] * k, d['ins'][1] * k]
    return d


def closed_ring(d):
    """The closed outline of a polyline / circle item, or None."""
    p = d.get('pts')
    if not p or len(p) < 3: return None
    if d.get('closed') or (len(p) > 3 and math.dist(p[0], p[-1]) < 1e-3): return p
    return None


def item_points(d):
    """prims._pts: the points that tag an item (polyline points, hatch loops, else the insertion point)."""
    return d.get('pts') or [q for l in d.get('loops', []) for q in l] or ([d['ins']] if 'ins' in d else [])


def drawn_points(d):
    """The points of a drawn item (a polyline, an arc, a circle, a hatch's loops); an insert or a text draws nothing."""
    if d['t'] in ('INSERT', 'ATTRIB') or 'text' in d: return []
    return d.get('pts') or [q for l in d.get('loops', []) for q in l]


def drawn_inside(items, i):
    """build_model.drawn_inside: the items drawn inside the INSERT at items[i] and the index after it (its own ATTRIBs,
    at its own depth, come first and are skipped)."""
    depth, j, n = items[i]['depth'], i + 1, len(items)
    while j < n and items[j]['t'] == 'ATTRIB' and items[j]['depth'] == depth: j += 1
    k = j
    while j < n and items[j]['depth'] > depth: j += 1
    return items[k:j], j


# ------------------------------------------------------------------------------------------------- the cache
def load_cache(path: str | Path) -> dict:
    """items.pkl (U-7.1: {items, layers, units}) or a prototype prims.pkl ({items, layers}). Only ever a pickle the
    worker or the reference tool wrote (U-4.2): never a file from an upload."""
    with open(path, 'rb') as f:
        D = pickle.load(f)
    if not isinstance(D, dict) or not isinstance(D.get('items'), list) or not isinstance(D.get('layers'), dict):
        raise ValueError(f'{Path(path).name} is not an items cache')
    return D


class RoleOf:
    """BuildSettings.layers (exact layer name -> staff role) -> function(layer) -> frozenset of builder roles (U-8.2).
    A layer the settings do not list is `other`. Cached per name."""

    def __init__(self, layers: Mapping[str, str]):
        self.layers = dict(layers)
        self._cache: dict[str, frozenset] = {}

    def __call__(self, layer: str) -> frozenset:
        r = self._cache.get(layer)
        if r is None:
            r = self._cache[layer] = frozenset({R.builder_role(self.layers, layer)})
        return r


# ------------------------------------------------------------------------------------------------- areas
def area_box(area: Mapping) -> tuple | None:
    """FloorArea -> (x0, y0, x1, y1, pad, match) in sheet m, or None for wholeFile."""
    if area['kind'] == 'wholeFile':
        return None
    x0, y0, x1, y1 = (float(v) for v in area['bbox'])
    return (x0, y0, x1, y1, float(area.get('pad', 0.0)), area.get('match', 'all'))


def tagger(floors: list[dict], k: float) -> Callable[[dict], str | None]:
    """openings.area_tagger's rule over a source's floors (in floor order), on the item's points scaled to metres:
    the first floor whose area holds all (or any) of them, padded; None when it has no points (U-9.1)."""
    boxes = [(f['key'], area_box(f['area'])) for f in floors]

    def tag(d):
        P = item_points(d)
        if not P: return None
        for key, b in boxes:
            if b is None: return key
            x0, y0, x1, y1, pad, match = b
            inside = (x0 - pad <= x * k <= x1 + pad and y0 - pad <= y * k <= y1 + pad for x, y in P)
            if (all if match == 'all' else any)(inside): return key
        return None
    return tag


# ------------------------------------------------------------------------------------------------- the readings
def _point_counts(items: list[dict], floors: list[dict], k: float):
    """Per item: drawn points, all points, and the drawn (else all) points inside each floor's area box + pad, as
    prefix sums so that a subtree's counts are a subtraction."""
    n = len(items)
    nf = len(floors)
    drawn = np.zeros(n + 1, dtype=np.int64)
    allp = np.zeros(n + 1, dtype=np.int64)
    ins_d = np.zeros((nf, n + 1), dtype=np.int64)
    ins_a = np.zeros((nf, n + 1), dtype=np.int64)
    boxes = [area_box(f['area']) for f in floors]
    for i, d in enumerate(items):
        dp = drawn_points(d)
        ap = item_points(d)
        drawn[i + 1] = len(dp)
        allp[i + 1] = len(ap)
        if not ap:
            continue
        for fi, b in enumerate(boxes):
            if b is None:
                ins_d[fi, i + 1] = len(dp); ins_a[fi, i + 1] = len(ap)
                continue
            x0, y0, x1, y1, pad, _ = b
            for arr, P in ((ins_d, dp), (ins_a, ap)):
                if not P: continue
                a = np.asarray(P, dtype=float) * k
                arr[fi, i + 1] = int(np.count_nonzero((a[:, 0] >= x0 - pad) & (a[:, 0] <= x1 + pad)
                                                      & (a[:, 1] >= y0 - pad) & (a[:, 1] <= y1 + pad)))
    return np.cumsum(drawn), np.cumsum(allp), np.cumsum(ins_d, axis=1), np.cumsum(ins_a, axis=1)


def subtree_reading(items: list[dict], floors: list[dict], k: float, tag) -> tuple[dict[str, list[int]], dict[str, int]]:
    """U-9.1's whole-subtree reading: floor key -> indices into `items` (cache order), and floor key -> subtrees left
    out that touched its area."""
    keys = [f['key'] for f in floors]
    out: dict[str, list[int]] = {key: [] for key in keys}
    outside = {key: 0 for key in keys}
    if not items:
        return out, outside
    drawn, allp, ins_d, ins_a = _point_counts(items, floors, k)

    def majority(i, j):
        tot = drawn[j] - drawn[i]
        ins = ins_d[:, j] - ins_d[:, i]
        if tot == 0:
            tot = allp[j] - allp[i]
            ins = ins_a[:, j] - ins_a[:, i]
        if tot == 0:
            return None, ins
        for fi in range(len(keys)):
            if 2 * ins[fi] > tot:
                return keys[fi], ins
        return None, ins

    def per_item(i):
        t = tag(items[i])
        if t is not None:
            out[t].append(i)

    def visit(lo, hi):
        i = lo
        while i < hi:
            d = items[i]
            if d['t'] != 'INSERT':
                per_item(i); i += 1
                continue
            _, j = drawn_inside(items, i)
            j = min(j, hi)
            f, ins = majority(i, j)
            if f is not None:
                out[f].extend(range(i, j)); i = j
                continue
            holds = any(items[q]['t'] == 'INSERT' and items[q]['depth'] > d['depth'] for q in range(i + 1, j))
            if holds:                                           # a container straddling floors: walked into
                a = i + 1
                per_item(i)
                while a < j and items[a]['t'] == 'ATTRIB' and items[a]['depth'] == d['depth']:
                    per_item(a); a += 1
                visit(a, j)
            elif ins.any():                                     # a piece in no floor: never split, left out, counted
                outside[keys[int(np.argmax(ins))]] += 1
            i = j

    visit(0, len(items))
    return out, outside


def floor_items(items: list[dict], idx: list[int], k: float, role_of: RoleOf, layer_lt: dict) -> list[dict]:
    """plan_items.load_floor on the chosen items: dedupe by `_signature` (on the cached item), then scale, then roles and
    the continuous-linetype flag. New dicts: the caller may shift them in place."""
    seen, out = set(), []
    for i in idx:
        d = items[i]
        s = signature(d)
        if s in seen: continue
        seen.add(s)
        d = dict(scaled(d, k))
        d['roles'] = role_of(d['lay'])
        d['cont'] = is_continuous(linetype(d, layer_lt))
        out.append(d)
    return out


def read_floors(items: list[dict], floors: list[dict], units: str, role_of: RoleOf, layer_lt: dict) -> dict[str, dict]:
    """One source's items -> per floor of that source: {items (per item), src (whole subtrees), n_layers,
    subtreesOutside, untagged} (U-9.1). `src` IS `items` (one list) when both readings chose the same items."""
    k = UNITS[units]
    tag = tagger(floors, k)
    per = {f['key']: [] for f in floors}
    no_points = 0
    for i, d in enumerate(items):
        t = tag(d)
        if t is not None:
            per[t].append(i)
        elif not item_points(d):
            no_points += 1
    sub, outside = subtree_reading(items, floors, k, tag)
    res = {}
    for f in floors:
        key = f['key']
        its = floor_items(items, per[key], k, role_of, layer_lt)
        src = its if sub[key] == per[key] else floor_items(items, sub[key], k, role_of, layer_lt)
        res[key] = {'items': its, 'src': src, 'n_layers': len({d['lay'] for d in its}),
                    'subtreesOutside': outside[key], 'noPoints': no_points}
    return res


def shift_items(items, dx, dy):
    """build_model.shift_items: moves items in place."""
    for d in items:
        if 'pts' in d: d['pts'] = [[x + dx, y + dy] for x, y in d['pts']]
        if 'loops' in d: d['loops'] = [[[x + dx, y + dy] for x, y in l] for l in d['loops']]
        if 'ins' in d: d['ins'] = [d['ins'][0] + dx, d['ins'][1] + dy]
