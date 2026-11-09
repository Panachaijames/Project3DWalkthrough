"""Rule 12, the furniture boxes: the port of build_model.furniture_of (bank) with the reader rules of the house
(cad_test/src/build_furniture.py) and the suite (presidential_test/src/build_model.py), each inert on the bank
(docs/upload/DESIGN.md U-10.5; measured: 0 assemblies, 0 dashed loose lines, 0 duplicate boxes, the single loose box
not on a part):

  * an `other` block holding 2+ blocks the vocabulary knows that stand on the floor is an ASSEMBLY: its parts are the
    pieces, its own loose lines are left out (house rule 2);
  * loose lines drawn with a dashed line type are left out (above the cut or hidden; house rule 3);
  * the same box twice (a drawing bound in twice) is one piece (house);
  * `furniture.minDepth`: a box thinner than it is left out (house: 0.25 m);
  * `furniture.looseLayers`: the layers whose loose lines become boxes (suite); empty: the furniture layers (bank);
  * a loose box lying on a built wall or column (half its area) is that part's own drawing: dropped (suite);
  * `furniture.pieceLayer: 'drawn'`: an INSERT whose own layer has no furniture role is a piece when the layer most of
    its drawing is on has the furniture role (the piece's layer is that layer), unless it holds furniture-candidate
    INSERTs (it is walked into, as the bank's Revit view block on layer 0 is) (suite).
The report keys these rules add appear only when they counted something, so the bank's summary is unchanged.

The kit (vendor/furniture_kit.py) is unchanged. Each piece carries `_src` (its INSERT item, or None for loose lines)
and `_kids` (what is drawn in it) for the placements (U-11.7); finish() never copies those keys into the model.
"""
from __future__ import annotations

import collections
import math

from shapely.geometry import LineString, Polygon

from ..vendor.load import load
from . import items as I
from .bank import family, translate

fk = load('furniture_kit')
_geom = load('geom')
even_odd = _geom.even_odd
KIND_BY = {k['key']: k for k in fk.KINDS}


def shape_of(d):
    """A loose drawn item as a shapely shape: a closed outline or a hatch is a polygon, anything else a line."""
    if 'loops' in d:
        g = even_odd(d['loops'])
        return None if g.is_empty else g
    ring = I.closed_ring(d)
    if ring:
        g = Polygon(ring).buffer(0)
        return None if g.is_empty else g
    p = d.get('pts') or []
    return LineString(p) if len({tuple(q) for q in p}) > 1 else None


def _majority_layer(kids):
    n = collections.Counter(k['lay'] for k in kids if I.drawn_points(k))
    return min(n, key=lambda l: (-n[l], l)) if n else None


def furniture_of(F, X, solid_model=None, cxy=(0.0, 0.0)):
    """Rule 12 for one floor -> (pieces in drawing coordinates, what was read and left out). `solid_model`: the floor's
    built walls and columns (model frame) for the suite's built-over rule; `cxy` the model offset."""
    items, key = F['src'], F['cfg']['key']
    FURN = X.FURN
    MIN_PIECE = FURN['minSize']
    MIN_DEPTH = FURN.get('minDepth')
    drawn_rule = FURN.get('pieceLayer', 'insert') == 'drawn'
    loose_layers = set(FURN.get('looseLayers') or [])
    furn_role = lambda lay: 'furniture' in X.role_of(lay) and 'ignore' not in X.role_of(lay)  # noqa: E731
    furn = lambda d: 'furniture' in d['roles'] and 'ignore' not in d['roles']  # noqa: E731

    def drawn_candidate(i):
        """pieceLayer 'drawn': the INSERT at i (own layer not furniture) -> the layer it is mostly drawn on, when that
        layer is a furniture layer and nothing inside it is a furniture candidate itself; else None."""
        kids, _ = I.drawn_inside(items, i)
        lay = _majority_layer(kids)
        if lay is None or not furn_role(lay):
            return None
        for j, k in enumerate(kids):
            if k['t'] != 'INSERT':
                continue
            if furn(k):
                return None
            sub, _ = I.drawn_inside(kids, j)
            sl = _majority_layer(sub)
            if sl is not None and furn_role(sl):
                return None
        return lay

    pieces, skipped, loose = [], collections.defaultdict(collections.Counter), collections.defaultdict(list)
    n_inserts = n_nested = 0
    extra = collections.Counter()
    opened = []                                             # assemblies being read: (end index, name)
    i = 0
    while i < len(items):
        d = items[i]
        if d['t'] == 'INSERT':
            lay = d['lay']
            piece = furn(d)
            if not piece and drawn_rule:
                dl = drawn_candidate(i)
                if dl is not None:
                    piece, lay = True, dl
                    extra['drawnPieces'] += 1
            if piece:
                kids, j = I.drawn_inside(items, i)
                fam = family(d['name'])
                kind = fk.classify(fam, lay, FURN.get('words'), FURN.get('skip'))
                nested = [k for k in kids if k['t'] == 'INSERT' and furn(k)]
                parts = [fk.classify(family(k['name']), k['lay'], FURN.get('words'), FURN.get('skip')) for k in nested]
                known = [kd for kd in parts if kd not in (None, 'other') and not KIND_BY[kd]['onTop']]
                if kind == 'other' and len(known) >= 2:     # an assembly: its parts are met next (house rule 2)
                    extra['assemblies'] += 1
                    opened.append((j, d['name']))
                    i += 1
                    continue
                i = j
                n_inserts += 1
                pts = [q for k in kids for q in I.drawn_points(k)]
                box = fk.box_of(pts) if pts else None
                if kind is None: why = 'name on the skip list'
                elif not pts: why = 'no geometry drawn inside the block'
                elif box is None: why = 'a point or a line (no area)'
                elif box['w'] < MIN_PIECE: why = f'shorter than {MIN_PIECE:g} m'
                elif box['w'] > fk.MAX_SIDE: why = f'longer than {fk.MAX_SIDE:g} m'
                elif MIN_DEPTH is not None and box['d'] < MIN_DEPTH: why = f'thinner than {MIN_DEPTH:g} m'
                else: why = None
                if why:
                    skipped[why][fam] += 1
                    continue
                n_nested += d['depth'] > 0
                pieces.append({'floor': key, 'kind': kind, 'family': fam, 'block': d['name'], 'layer': lay,
                               'handle': d['h'] if d['depth'] == 0 else '', **box, 'on': None, 'n': 1,
                               'note': f"inside block {d['path'].split('>')[0]}" if d['depth'] else '',
                               '_src': d, '_kids': kids})
                continue
        at = i
        i += 1
        # looseLayers (the suite): lines drawn loose on those layers, outside every block; else the bank's rule: lines on
        # furniture layers not inside a piece (in a Revit export everything sits inside the view block)
        is_loose = (d['lay'] in loose_layers and d['depth'] == 0) if loose_layers else furn(d)
        if not (is_loose and ('pts' in d or 'loops' in d)):
            continue
        opened = [(end, name) for end, name in opened if end > at]
        if opened:
            extra['inAssembly'] += 1
            skipped['loose shapes inside an assembly (they outline its parts again)'][family(opened[-1][1])] += 1
            continue
        if not d['cont']:
            extra['dashed'] += 1
            skipped['loose shapes drawn with a dashed line type (above the cut plane or hidden)'][d['lay']] += 1
            continue
        loose[d['lay']].append(d)
    n_loose, loose_boxes, left_out = 0, 0, []
    for lay, ds in sorted(loose.items()):
        shapes = [g for g in map(shape_of, ds) if g is not None]
        n_loose += len(shapes)
        boxes, rest = fk.loose_boxes(shapes)
        left_out += [{'layer': lay, 'shapes': n, 'why': why} for n, why in rest]
        for b in boxes:
            if not MIN_PIECE <= b['w'] <= fk.MAX_SIDE:
                left_out.append({'layer': lay, 'shapes': b['n'], 'why': f"long side {b['w']:.2f} m is not between {MIN_PIECE:g} and {fk.MAX_SIDE:g} m"})
                continue
            if MIN_DEPTH is not None and b['d'] < MIN_DEPTH:
                left_out.append({'layer': lay, 'shapes': b['n'], 'why': f"short side {b['d']:.2f} m is under {MIN_DEPTH:g} m"})
                continue
            if solid_model is not None and not solid_model.is_empty:
                r = translate(fk.rect_of(b), -cxy[0], -cxy[1])
                if r.intersection(solid_model).area >= 0.5 * b['w'] * b['d']:      # the suite: a built part's own drawing
                    extra['builtOver'] += 1
                    continue
            loose_boxes += 1
            pieces.append({'floor': key, 'kind': fk.classify('', lay), 'family': f'loose shapes on {lay}', 'block': '', 'layer': lay,
                           'handle': '', **b, 'on': None, 'note': 'drawn loose, not as a block', '_src': None, '_kids': None})
    # the same box twice (a drawing bound in twice): one piece (house)
    unique, dup = {}, 0
    for p in pieces:
        k = (p['floor'], p['family'], p['layer'], round(p['x'], 3), round(p['y'], 3), round(p['w'], 3), round(p['d'], 3),
             round(p['rot'] % 180, 1))
        if k in unique: dup += 1
        else: unique[k] = p
    if dup:
        pieces = list(unique.values())
        extra['duplicateBoxes'] = dup
    report = {'insertsRead': n_inserts, 'nestedInAnotherBlock': n_nested,
              'skipped': {why: {'count': sum(c.values()), 'families': dict(c.most_common())} for why, c in skipped.items()},
              'looseShapes': {'shapes': n_loose, 'boxes': loose_boxes, 'leftOut': left_out}}
    for k, v in extra.items():                              # only what counted something: the bank's report is unchanged
        if v: report[k] = v
    return pieces, report


# ---------------------------------------------------------------------------------------------------- placements
def finish_order(pieces, floors):
    """The permutation fk.finish sorts the pieces by: out[j] was pieces[perm[j]] (its sort is stable, so sorting the
    indices by the same key gives the same order)."""
    floors = [f['key'] if isinstance(f, dict) else f for f in floors]
    order = {k['key']: i for i, k in enumerate(fk.KINDS)}
    r3 = lambda v: round(v, 3) + 0.0  # noqa: E731

    def key(i):
        p = pieces[i]
        turn = 90 if p['w'] - p['d'] < 0.001 else 180
        rot = round(p['rot'] % turn, 2)
        rot = 0.0 if rot >= turn else rot
        return (floors.index(p['floor']), order[p['kind']], r3(p['x']), r3(p['y']), p['family'], p['block'], r3(p['w']),
                r3(p['d']), rot)
    return sorted(range(len(pieces)), key=key)


def placements(furniture, pieces, perm, sources_of, shift_of, variants) -> list[dict]:
    """FurniturePlacements.pieces (U-11.7): per model piece, its INSERT's key, block, family, element id, insertion
    point (sheet m), world turn and scale with sign, insertMirrored, drawnVariant and the box's own turn."""
    from ..names import element_id
    out = []
    for j, f in enumerate(furniture):
        p = pieces[perm[j]]
        d = p.get('_src')
        s = shift_of[f['floor']]
        row = {'id': f['id'], 'floor': f['floor'], 'source': sources_of[f['floor']], 'key': None, 'block': None,
               'family': None, 'elementId': None, 'ins': None, 'rot': None, 'sx': None, 'sy': None,
               'insertMirrored': None, 'drawnVariant': None, 'boxRot': float(f['rot'])}
        if d is not None:
            path = [x for x in (d.get('path') or '').split('>') if x] + [d['name']]
            row.update(key=d.get('k'), block=d['name'], family=family(d['name']), elementId=element_id(path),
                       ins=[round(d['ins'][0] - s[0], 4), round(d['ins'][1] - s[1], 4)], rot=float(d['rot']),
                       sx=float(d['sx']), sy=float(d['sy']), insertMirrored=bool(d['sx'] * d['sy'] < 0),
                       drawnVariant=variants.get(id(p)))
        out.append(row)
    return out


# ---------------------------------------------------------------------------------------------------- drawnVariant
def _sample(kids, ins, rot, sx, sy, step=0.005):
    """The piece's drawing brought back into its block's frame (minus the insertion point, turned back by the INSERT's
    turn, divided by its scale), sampled every 5 mm along its lines (block_variants.sample)."""
    import numpy as np
    a = math.radians(-rot)
    c, s = math.cos(a), math.sin(a)
    rot_m = np.array([[c, s], [-s, c]])
    scale = np.array([sx or 1.0, sy or 1.0])
    pts = []
    for k in kids:
        P = k.get('pts') or []
        loops = k.get('loops') or []
        for line in ([P] if P else []) + list(loops):
            if not line:
                continue
            v = ((np.asarray(line, dtype=float) - np.asarray(ins, dtype=float)) @ rot_m) / scale
            pts.append(v[:1])
            if len(v) < 2:
                continue
            seg = v[1:] - v[:-1]
            n = np.maximum(1, (np.hypot(seg[:, 0], seg[:, 1]) / step).astype(np.int64))
            idx = np.repeat(np.arange(len(seg)), n)
            kk = np.arange(int(n.sum())) - np.repeat(np.cumsum(n) - n, n) + 1
            t = (kk / np.repeat(n, n))[:, None]
            pts.append(v[:-1][idx] + seg[idx] * t)
    return np.vstack(pts) if pts else np.zeros((0, 2))


def _thin(p, cell=0.004):
    import numpy as np
    if len(p) == 0:
        return p
    k = np.unique(np.round(p / cell).astype(np.int64), axis=0, return_index=True)[1]
    return p[np.sort(k)]


def _nn_mean(a, b):
    """Mean distance from each point of a to its nearest point of b (block_variants.nn_mean, by GEOS's nearest query
    instead of a brute-force matrix: the same distances)."""
    import numpy as np
    import shapely
    if len(a) == 0 or len(b) == 0:
        return float('inf')
    tree = shapely.STRtree(shapely.points(b))
    _, dist = tree.query_nearest(shapely.points(a), return_distance=True, all_matches=False)
    return float(np.mean(dist))


def _sym(a, b):
    return (_nn_mean(a, b) + _nn_mean(b, a)) / 2


def drawn_variants(furniture, pieces, perm) -> dict[int, str | None]:
    """U-11.7, a port of furniture_test/bank_furnished/scripts/block_variants.py on the cache items: per family (with two
    or more block pieces) the pieces' drawings are grouped (the same drawing: point counts within 20 % and a mean
    distance under 2 mm), and each group is compared with the first group as it is, mirrored in x, mirrored in y and
    turned 180 degrees; the closest wins. -> {id(piece): 'same' | 'mirrorX' | 'mirrorY' | 'turned180'} (absent: null)."""
    by_fam = collections.defaultdict(list)
    for j in range(len(furniture)):
        p = pieces[perm[j]]
        if p.get('_src') is not None and p.get('_kids'):
            by_fam[p['family']].append(p)
    out = {}
    names = {'as drawn': 'same', 'mirrored in x': 'mirrorX', 'mirrored in y': 'mirrorY', 'turned 180': 'turned180'}
    for _, ps in by_fam.items():
        if len(ps) < 2:
            continue
        groups, by_block = [], {}
        for p in ps:
            d = p['_src']
            g = by_block.get(d['name'])
            if g is not None:                               # the same block definition: the same drawing
                g['pieces'].append(p)
                continue
            pts = _thin(_sample(p['_kids'], d['ins'], d['rot'], d['sx'], d['sy']))
            for g in groups:
                if len(g['points']) and abs(len(g['points']) - len(pts)) <= 0.2 * len(pts) and _sym(pts, g['points']) < 0.002:
                    g['pieces'].append(p)
                    break
            else:
                g = {'points': pts, 'pieces': [p]}
                groups.append(g)
            by_block[d['name']] = g
        ref = groups[0]['points']
        for gi, g in enumerate(groups):
            if gi == 0:
                best = 'as drawn'
            else:
                q = g['points']
                cmp = {'as drawn': _sym(q, ref), 'mirrored in x': _sym(q * [-1, 1], ref),
                       'mirrored in y': _sym(q * [1, -1], ref), 'turned 180': _sym(q * [-1, -1], ref)}
                best = min(cmp, key=cmp.get)
            for p in g['pieces']:
                out[id(p)] = names[best]
    return out
