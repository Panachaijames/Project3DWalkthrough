"""Units of a drawing: what its header declares, what its doors say, and which the reader uses (docs/upload/DESIGN.md U-7.4).

* `declared` comes from `$INSUNITS` (1 in, 2 ft, 4 mm, 5 cm, 6 m; any other code: none).
* **Door votes**: per unit hypothesis, the quarter arcs (80 - 100 degrees) that have a straight leaf from the arc's centre
  (the hinge) to one of its ends, as long as the radius within 10 %, counted where 0.6 m <= radius x the unit <= 1.25 m.
  The hinge and the tip may lie 8 % of the radius off (the drawn leaf meets the arc at the jamb line, not exactly at
  its centre). The arc ranges of the five units do not overlap, so one door votes for one unit at most.
* `used` = the declared units when their votes are the most or no hypothesis has 3 votes; otherwise the hypothesis with
  the most votes (`votes-win`: "the file says inches, its doors say millimetres"). With no declared units: the votes'
  winner when it has 3 or more (`votes-win`), else millimetres (`unknown`).
* Coordinates in here are the reader's own frame (prims: DXF units / 1000); `UNITS_K[u]` turns them into metres exactly
  as the detector's `openings.scaled` does.

The reader decides before its walk (`quick()`: the same vote on the block definitions and model space, as drawn, with no
block unpacked) so that it can flatten curves at 10 mm expressed in the drawing's units, then votes again on the walked
items (`door_votes()`) and walks again only when the two disagree (U-7.4). Owner: U2.
"""
from __future__ import annotations

import collections
import math
from collections.abc import Iterable, Sequence

#: The five units of the contract, in its order (upload-contracts.ts Units).
UNITS: tuple[str, ...] = ('mm', 'cm', 'm', 'in', 'ft')
#: Reader frame (DXF units / 1000) -> metres: detector/openings.py UNITS for the contract's units.
UNITS_K: dict[str, float] = {'mm': 1.0, 'cm': 10.0, 'm': 1000.0, 'in': 25.4, 'ft': 304.8}
#: Metres per DXF unit.
M_PER_UNIT: dict[str, float] = {'mm': 0.001, 'cm': 0.01, 'm': 1.0, 'in': 0.0254, 'ft': 0.3048}
#: $INSUNITS code -> units (U-7.4); every other code declares nothing the reader can use.
INSUNITS: dict[int, str] = {1: 'in', 2: 'ft', 4: 'mm', 5: 'cm', 6: 'm'}
#: Plain names for the notes.
WORDS: dict[str, str] = {'mm': 'millimetres', 'cm': 'centimetres', 'm': 'metres', 'in': 'inches', 'ft': 'feet'}

#: A door leaf is 0.6 - 1.25 m wide (U-7.4).
VOTE_MIN, VOTE_MAX = 0.6, 1.25
#: A quarter arc sweeps 80 - 100 degrees.
QUARTER = (80.0, 100.0)
#: Door-size arcs of the layer statistics (upload-contracts.ts LayerRead.doorArcs): 0.28 - 2 m, 20 - 125 degrees.
DOOR_ARC_R = (0.28, 2.0)
DOOR_ARC_SWEEP = (20.0, 125.0)
#: The leaf: its hinge and tip within 8 % of the radius of the arc's centre and end, its length within 10 %.
NEAR, LONG = 0.08, 0.10
#: Enough doors to say something.
ENOUGH = 3

#: Every radius (reader frame) that can be door-like in some unit: 0.28 m in metres .. 2 m in millimetres (the
#: reader frame is DXF units / 1000, so metres take the smallest radii and millimetres the largest).
_R_MIN = min(DOOR_ARC_R[0], VOTE_MIN) / max(UNITS_K.values())
_R_MAX = max(DOOR_ARC_R[1], VOTE_MAX) / min(UNITS_K.values())


def flatten_distance(units: str) -> float:
    """Curves are flattened at 10 mm expressed in the drawing's units (U-7.1): exactly `10` (an int, as prims passes it)
    for millimetres, so a millimetre drawing gives prims' own points."""
    if units == 'mm':
        return 10
    return 10 / UNITS_K[units]


def zero_votes() -> dict[str, int]:
    return {u: 0 for u in UNITS}


def votes_of(radii: Iterable[float]) -> dict[str, int]:
    """Door votes per unit from the radii (reader frame) of quarter arcs that have a leaf."""
    votes = zero_votes()
    for r in radii:
        for u in UNITS:
            if VOTE_MIN <= r * UNITS_K[u] <= VOTE_MAX:
                votes[u] += 1
    return votes


class LeafFinder:
    """Finds, for an arc, a straight segment from its centre to one of its ends (the door leaf). Segments are indexed by
    both end points in square cells whose side is a power of ten at least the search tolerance, one grid per cell size,
    made when first needed; only segments whose length can be a candidate radius are kept."""

    def __init__(self, segs: Iterable[tuple[Sequence[float], Sequence[float]]], r_min: float, r_max: float) -> None:
        lo, hi = (1 - LONG) * r_min, (1 + LONG) * r_max
        self.segs = []
        for a, b in segs:
            n = math.dist(a, b)
            if lo <= n <= hi and all(map(math.isfinite, (a[0], a[1], b[0], b[1]))):
                self.segs.append(((a[0], a[1]), (b[0], b[1]), n))
        self.grids: dict[float, dict[tuple[int, int], list[int]]] = {}

    def _grid(self, cs: float) -> dict[tuple[int, int], list[int]]:
        g = self.grids.get(cs)
        if g is None:
            g = collections.defaultdict(list)
            for i, (a, b, _n) in enumerate(self.segs):
                ca = (math.floor(a[0] / cs), math.floor(a[1] / cs))
                cb = (math.floor(b[0] / cs), math.floor(b[1] / cs))
                g[ca].append(i)
                if cb != ca:
                    g[cb].append(i)
            self.grids[cs] = g
        return g

    def has_leaf(self, cx: float, cy: float, r: float, ends: Sequence[Sequence[float]]) -> bool:
        if not (r > 0 and math.isfinite(r) and math.isfinite(cx) and math.isfinite(cy)):
            return False
        tol = NEAR * r
        cs = 10.0 ** math.ceil(math.log10(tol))
        g = self._grid(cs)
        gx, gy = math.floor(cx / cs), math.floor(cy / cs)
        c = (cx, cy)
        for i in (-1, 0, 1):
            for j in (-1, 0, 1):
                for s in g.get((gx + i, gy + j), ()):
                    a, b, n = self.segs[s]
                    if abs(n - r) > LONG * r:
                        continue
                    for hinge, tip in ((a, b), (b, a)):
                        if math.dist(hinge, c) <= tol and any(math.dist(tip, q) <= tol for q in ends):
                            return True
        return False


def door_votes(arcs: Sequence[tuple], segs: Iterable[tuple[Sequence[float], Sequence[float]]]) -> tuple[dict[str, int], list[bool]]:
    """The door votes of the walked items, and per arc whether it has a leaf.

    `arcs`: (cx, cy, r, sweep, end_a, end_b) in the reader frame, sweep in degrees; `segs`: straight segments of the
    line work (LINE, LWPOLYLINE, POLYLINE), end-point pairs in the reader frame. The leaf test runs on every arc that
    can be a door in some unit (20 - 125 degrees; 0.28 m in feet .. 2 m in millimetres), so the layer statistics
    (`doorArcsWithLeaf`) reuse it; the votes count the quarter arcs among them."""
    cand = [i for i, a in enumerate(arcs)
            if DOOR_ARC_SWEEP[0] <= a[3] <= DOOR_ARC_SWEEP[1] and _R_MIN <= a[2] <= _R_MAX]
    leaf = [False] * len(arcs)
    if not cand:
        return zero_votes(), leaf
    finder = LeafFinder(segs, min(arcs[i][2] for i in cand), max(arcs[i][2] for i in cand))
    for i in cand:
        cx, cy, r, _sweep, ea, eb = arcs[i][:6]
        leaf[i] = finder.has_leaf(cx, cy, r, (ea, eb))
    radii = [arcs[i][2] for i in cand if leaf[i] and QUARTER[0] <= arcs[i][3] <= QUARTER[1]]
    return votes_of(radii), leaf


def decide(ins_units: int | None, votes: dict, dimension_median: float | None, forced: str | None = None) -> dict:
    """-> DrawingRead.units {declared, votes, dimensionMedian, used, verdict, note} (U-7.4). `forced`: the units staff
    chose on the Files step (the read is then made in them; the verdict still says what the file and its doors say)."""
    declared = INSUNITS.get(ins_units) if isinstance(ins_units, int) else None
    v = {u: int(votes.get(u, 0)) for u in UNITS}
    # the most votes; a tie goes to the declared units, then to the contract's order
    best = max(UNITS, key=lambda u: (v[u], u == declared, -UNITS.index(u)))
    if declared is not None:
        if v[declared] >= v[best] or v[best] < ENOUGH:
            used = declared
            if v[declared] >= ENOUGH:
                verdict = 'agree'
                note = f'the file says {WORDS[declared]} and {v[declared]} doors agree'
            else:
                verdict = 'declared-only'
                note = (f'the file says {WORDS[declared]}; too few doors to check it '
                        f'({v[declared]} door{"" if v[declared] == 1 else "s"} found)')
        else:
            used, verdict = best, 'votes-win'
            note = (f'the file says {WORDS[declared]}, its doors say {WORDS[best]} '
                    f'({v[best]} doors against {v[declared]}): read in {WORDS[best]}')
    elif v[best] >= ENOUGH:
        used, verdict = best, 'votes-win'
        note = f'the file names no units; {v[best]} doors say {WORDS[best]}'
    else:
        used, verdict = 'mm', 'unknown'
        note = 'the file names no units and has too few doors to tell: millimetres assumed'
    if forced is not None and forced != used:
        if forced not in UNITS_K:
            raise ValueError(f'unknown units {forced!r} (allowed: {", ".join(UNITS)})')
        note = f'{note}; read in {WORDS[forced]} as chosen'
        used = forced
    elif forced is not None:
        note = f'{note}; {WORDS[forced]} as chosen'
    dm = None if dimension_median is None or not math.isfinite(dimension_median) else float(dimension_median)
    return {'declared': declared, 'votes': v, 'dimensionMedian': dm, 'used': used, 'verdict': verdict, 'note': note}


# ------------------------------------------------------------------------------------------- the quick decision (U-7.4)
def _layout_votes(entities: Iterable) -> tuple[list[tuple], list[tuple]]:
    """Arcs and straight segments of one layout as drawn (its own coordinates, DXF units / 1000), no block unpacked."""
    arcs, segs = [], []
    for e in entities:
        try:
            t = e.dxftype()
            if t == 'ARC':
                d = e.dxf
                r = abs(d.radius) / 1000
                sweep = (d.end_angle - d.start_angle) % 360
                if not (DOOR_ARC_SWEEP[0] <= sweep <= DOOR_ARC_SWEEP[1]):
                    continue
                ocs = e.ocs()
                c = ocs.to_wcs(d.center)
                ends = []
                for ang in (d.start_angle, d.end_angle):
                    a = math.radians(ang)
                    p = ocs.to_wcs((d.center.x + d.radius * math.cos(a), d.center.y + d.radius * math.sin(a), d.center.z))
                    ends.append((p.x / 1000, p.y / 1000))
                arcs.append((c.x / 1000, c.y / 1000, r, sweep, ends[0], ends[1]))
            elif t == 'LINE':
                s, f = e.dxf.start, e.dxf.end
                segs.append(((s.x / 1000, s.y / 1000), (f.x / 1000, f.y / 1000)))
            elif t == 'LWPOLYLINE':
                P = [(x / 1000, y / 1000) for x, y in e.get_points('xy')]
                if e.closed and len(P) > 2:
                    P.append(P[0])
                segs.extend(zip(P, P[1:]))
            elif t == 'POLYLINE' and e.is_2d_polyline:
                P = [(v.dxf.location.x / 1000, v.dxf.location.y / 1000) for v in e.vertices]
                if e.is_closed and len(P) > 2:
                    P.append(P[0])
                segs.extend(zip(P, P[1:]))
        except (MemoryError, RecursionError):
            raise
        except Exception:
            continue
    return arcs, segs


def quick_votes(doc) -> dict[str, int]:
    """Door votes over the block definitions and model space as drawn: every definition counts once, in its own
    coordinates (a door block inserted 30 times is one vote), which is enough to choose the flattening distance."""
    total = zero_votes()
    layouts = [doc.modelspace()]
    try:
        layouts += [b for b in doc.blocks if not b.name.lower().startswith(('*model_space', '*paper_space'))]
    except (MemoryError, RecursionError):
        raise
    except Exception:
        pass
    for lay in layouts:
        arcs, segs = _layout_votes(lay)
        if not arcs:
            continue
        v, _leaf = door_votes(arcs, segs)
        for u in UNITS:
            total[u] += v[u]
    return total


def quick(doc) -> dict:
    """The quick decision before the walk: the header and the doors as drawn (`decide` on `quick_votes`)."""
    ins = doc.header.get('$INSUNITS', None)
    try:
        votes = quick_votes(doc)
    except (MemoryError, RecursionError):
        raise
    except Exception:
        votes = zero_votes()
    return decide(ins if isinstance(ins, int) else None, votes, None)
