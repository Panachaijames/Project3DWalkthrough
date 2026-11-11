"""Fixes applied by the builder on every run (docs/upload/DESIGN.md U-10.6).

1. Set aside (`fixes.setAside`, ItemRefs): the matched items leave the source's items BEFORE everything (the detector
   included). A ref whose key is an INSERT's sets aside the INSERT, its attributes (`key@...`) and every item whose key
   starts with `key + '/'` (its whole subtree). Matching, first that applies:
     (a) the exact key on the same source;
     (b) the same element id TOGETHER WITH the same layer and `rsig` (rsig hashes the type and the points relative to
         the element's INSERT; an element id alone names a whole family instance, so it is never matched alone);
     (c) the same `sig` on the same layer;
   else the fix is unmatched (`matchedBy: None`, flag fix-unmatched, kept in the settings). When (b) or (c) matches more
   than one item nothing is removed (`ambiguous` = how many matched: "pick again"). The items' sig, rsig and element id
   are the reader's own (`plangeom.ref_of`, U2), the values the plan entries carry and the browser copies into the
   ItemRef (U-7.5), so both sides are made by one function.
2. Openings (`fixes.openings`): matched to a detector record of the floor when both ends lie within 0.15 m of the fix's
   a, b (either order), else when they overlap 50 % on the same line within 0.1 m; `kind` replaces the detector's
   (`none` drops it: nothing is cut), `head` / `sill` replace the computed ones.
3. Outline edges (`fixes.outlineEdges`): an accepted suggestion (the same edge within 0.05 m) becomes a wall or glass
   segment before the cut (build/outline.py).
Coordinates of fixes are sheet metres (a source's own frame, before any alignment shift).

The rooms milestone (docs/rooms/DESIGN.md R-2.1 point 7, R-6.2, R-6.3; owner R1), with options.slabs 'network':
4. A line staff set aside still bounds the floor (`set_aside_split` hands the removed items back, `bounding_aside`
   picks those that still bound) unless its record says `floorPast: true` ("the floor runs past it").
5. Closing fixes (`fixes.closings`): `use: 'line'` is a line staff drew (a 2 cm strip in the network, each end
   extended to the network within 0.5 m: network.network_of); `use: 'none'` leaves out the app's bridge or doorway
   closing whose two ends lie within 0.3 m of a and b (`removed_closings`); none there: the fix is unmatched.
6. Room fixes (`fixes.rooms`): `room_target` finds what the point names: the room containing it; else the unfloored
   area containing it; else the room within 0.5 m; else, for "floor here", the fenced face containing it; else the fix
   is unmatched. These fixes are points and lines, not item keys, so they survive a re-export with other handles.
"""
from __future__ import annotations

import math
from collections.abc import Mapping

from .. import keys as K
from .. import names as N

ENDS = 0.15         # m: an opening fix's ends lie this close to the record's
LINE = 0.10         # m: ... or it lies on the same line within this
OVERLAP = 0.5       # ... overlapping this share of the shorter


def _names(d) -> list[str]:
    path = N.split_path(d.get('path') or '')
    if d['t'] == 'INSERT':
        return path + [d['name']]
    if d['t'] == 'ATTRIB' and d.get('block'):
        return path + [d['block']]
    return path


def _reader_ref_of():
    """The reader's own (sig, rsig, element id) of a cache item, `plangeom.ref_of(item, inserts_by_key, k)` (U2), so a
    set-aside's ItemRef (copied by the browser from the plan entry, U-7.5) and the matcher compare values made by ONE
    function (A-4: every plan entry's sig / rsig / eid equal what the builder computes). None when the reader's module
    cannot be imported: the matcher then computes the same rule itself (keys.py, names.py: `_own_ref`)."""
    try:
        from ..plangeom import ref_of
    except ImportError:
        return None
    return ref_of


class SourceIndex:
    """One source's cache items with what the matcher needs: key -> index, element ids, sig and rsig (lazily)."""

    def __init__(self, items: list[dict], k: float):
        self.items, self.k = items, k
        self.by_key: dict[str, int] = {}
        for i, d in enumerate(items):
            kk = d.get('k')
            if kk is not None and kk not in self.by_key:
                self.by_key[kk] = i
        self._refs: dict[int, tuple[str, str, str | None]] = {}
        self._inserts: dict[str, dict] | None = None
        self._ref_of = _reader_ref_of()

    def ref(self, i: int) -> tuple[str, str, str | None]:
        """(sig, rsig, element id) of item i; a signature that cannot be made (a coordinate that is not a finite number)
        is '' and matches nothing."""
        r = self._refs.get(i)
        if r is None:
            d = self.items[i]
            if self._ref_of is not None and d.get('k') is not None:
                if self._inserts is None:
                    self._inserts = {x['k']: x for x in self.items if x['t'] == 'INSERT' and x.get('k') is not None}
                r = tuple(self._ref_of(d, self._inserts, self.k))
            else:
                r = self._own_ref(i)
            self._refs[i] = r
        return r

    def _own_ref(self, i: int) -> tuple[str, str, str | None]:
        d = self.items[i]
        try:
            s = K.sig(d, self.k)
        except (ValueError, TypeError, OverflowError):
            s = ''
        try:
            el = self.element_insert(i)
            rs = K.rsig(d, el, self.k) if el is not None else ''
        except (ValueError, TypeError, OverflowError):
            rs = ''
        return s, rs, N.element_id(_names(d))

    def eid(self, i: int) -> str | None:
        return self.ref(i)[2]

    def sig(self, i: int) -> str:
        return self.ref(i)[0]

    def element_insert(self, i: int) -> dict | None:
        d = self.items[i]
        names = _names(d)
        e = N.element_depth(names)
        if e is None:
            return None
        if d['t'] == 'INSERT' and e == len(names) - 1:
            return d
        base = (d.get('k') or '').split('@')[0]
        comps = base.split('/')
        if d['t'] == 'ATTRIB' and e == len(names) - 1:
            j = self.by_key.get(base)
            return self.items[j] if j is not None else None
        if e + 1 > len(comps):
            return None
        j = self.by_key.get('/'.join(comps[:e + 1]))
        return self.items[j] if j is not None and self.items[j]['t'] == 'INSERT' else None

    def rsig(self, i: int) -> str:
        return self.ref(i)[1]

    def subtree(self, i: int) -> list[int]:
        """The item, and for an INSERT its attributes and whole subtree (by key prefix: in cache order they follow it)."""
        d = self.items[i]
        kk = d.get('k')
        if d['t'] != 'INSERT' or not kk:
            return [i]
        pre = (kk + '/', kk + '@')
        out, j = [i], i + 1
        while j < len(self.items) and (self.items[j].get('k') or '').startswith(pre):
            out.append(j); j += 1
        return out

    def by_element(self, layer: str, eid: str) -> list[int]:
        """The items of one element on one layer (indexed by names.element_id of the item's block chain, the rule the
        reader's element id follows; each candidate's own element id and rsig then come from `ref`)."""
        if not hasattr(self, '_by_eid'):
            self._by_eid: dict[tuple, list[int]] = {}
            for i, d in enumerate(self.items):
                e = N.element_id(_names(d))
                if e is not None:
                    self._by_eid.setdefault((d['lay'], e), []).append(i)
        return [i for i in self._by_eid.get((layer, eid), []) if self.eid(i) == eid]

    def by_sig(self, layer: str, sig: str) -> list[int]:
        """The items with one signature on one layer (indexed by keys.sig, the function the reader's sig is; each
        candidate's own sig then comes from `ref`)."""
        if not hasattr(self, '_by_sig'):
            self._by_sig: dict[tuple, list[int]] = {}
            for i, d in enumerate(self.items):
                try:
                    s = K.sig(d, self.k)
                except (ValueError, TypeError, OverflowError):
                    continue
                self._by_sig.setdefault((d['lay'], s), []).append(i)
        return [i for i in self._by_sig.get((layer, sig), []) if self.sig(i) == sig]


def match_ref(ix: SourceIndex, ref: Mapping, same_source: bool) -> tuple[str | None, list[int], int]:
    """-> (matchedBy, indices to remove, ambiguous count)."""
    if same_source:
        j = ix.by_key.get(ref.get('key'))
        if j is not None:
            return 'key', ix.subtree(j), 0
    eid, lay = ref.get('elementId'), ref.get('layer')
    if eid and ref.get('rsig'):
        cand = [i for i in ix.by_element(lay, eid) if ix.rsig(i) == ref['rsig']]
        if len(cand) == 1:
            return 'element', ix.subtree(cand[0]), 0
        if len(cand) > 1:
            return None, [], len(cand)
    if ref.get('sig'):
        cand = ix.by_sig(lay, ref['sig'])
        if len(cand) == 1:
            return 'sig', ix.subtree(cand[0]), 0
        if len(cand) > 1:
            return None, [], len(cand)
    return None, [], 0


def set_aside(sources: Mapping[str, list[dict]], k_of: Mapping[str, float], refs: list[dict],
              floor_source: Mapping[str, str]) -> tuple[dict[str, list[dict]], list[dict], dict[str, list[str]]]:
    """sources: sha1 -> cache items. -> (sha1 -> the items kept, FixesReport.setAside rows, floor -> the keys set aside).
    Each ref is matched on its own source when that is one of the build's, else on its floor's source."""
    kept, rows, keys_by_floor, _removed = set_aside_split(sources, k_of, refs, floor_source)
    return kept, rows, keys_by_floor


def set_aside_split(sources: Mapping[str, list[dict]], k_of: Mapping[str, float], refs: list[dict],
                    floor_source: Mapping[str, str]):
    """set_aside, and what it removed: -> (kept, rows, keys by floor, sha1 -> [(item, [the indices of the refs that
    removed it])] in cache order). The rooms milestone reads the removed lines back into the wall network (R-2.1
    point 7)."""
    index = {sha: SourceIndex(its, k_of[sha]) for sha, its in sources.items()}
    gone: dict[str, set[int]] = {sha: set() for sha in sources}
    by_ref: dict[str, dict[int, list[int]]] = {sha: {} for sha in sources}
    rows, keys_by_floor = [], {}
    for fi, ref in enumerate(refs):
        sha = ref.get('source')
        same = sha in index
        if not same:
            sha = floor_source.get(ref.get('floor'))
        if sha not in index:
            rows.append({'fix': fi, 'matchedBy': None, 'items': 0, 'ambiguous': 0, 'key': None})
            continue
        by, idx, amb = match_ref(index[sha], ref, same)
        gone[sha].update(idx)
        for i in idx:
            by_ref[sha].setdefault(i, []).append(fi)
        rows.append({'fix': fi, 'matchedBy': by, 'items': len(idx), 'ambiguous': amb,
                     'key': index[sha].items[idx[0]].get('k') if idx else None})
        if idx:
            keys_by_floor.setdefault(ref.get('floor'), []).extend(
                k for k in (index[sha].items[i].get('k') for i in idx) if k)
    kept = {sha: ([d for i, d in enumerate(its) if i not in gone[sha]] if gone[sha] else its) for sha, its in sources.items()}
    removed = {sha: [(its[i], by_ref[sha][i]) for i in sorted(gone[sha])] for sha, its in sources.items()}
    return kept, rows, keys_by_floor, removed


def bounding_aside(removed: list, refs: list[dict]) -> list[dict]:
    """The set-aside items of one source that still bound the floor (R-2.1 point 7): every removed item, unless a
    set-aside record that removed it says `floorPast` ("the floor runs past it"). removed: set_aside_split's rows of
    the source. The items are the cache's own (unscaled): the caller reads them into its floors."""
    return [d for d, fis in removed if not any(bool(refs[fi].get('floorPast')) for fi in fis)]


# ------------------------------------------------------------------------------------- closings and rooms (R-6.2, R-6.3)
REMOVE_REACH = 0.3  # m: a removed closing's two ends lie within this of the fix's a and b
ROOM_NEAR = 0.5     # m: a room fix whose point is in no room and no unfloored area takes the room within this


def floor_fixes(fixes: Mapping | None, name: str, floor: str) -> list[tuple[int, dict]]:
    """[(index in settings.fixes[name], the fix)] of one floor."""
    return [(k, f) for k, f in enumerate((fixes or {}).get(name) or []) if f.get('floor') == floor]


def removed_closings(closings: list[dict], a, b) -> list[dict]:
    """The app's closings (bridges, doorway closings: { a, b }) a `use: 'none'` fix names: both ends within 0.3 m of the
    fix's a and b, in either order."""
    return [c for c in closings if (math.dist(c['a'], a) <= REMOVE_REACH and math.dist(c['b'], b) <= REMOVE_REACH)
            or (math.dist(c['a'], b) <= REMOVE_REACH and math.dist(c['b'], a) <= REMOVE_REACH)]


def room_target(pt, spaces: list[dict], unfloored: list[dict], fenced: list, slab: str):
    """What a room fix at the point `pt` (shapely, build frame) applies to (R-6.3) -> ('room', the space) |
    ('unfloored', the area) | ('fenced', the face) | (None, None): the room containing the point; else the unfloored
    area containing it; else the room within 0.5 m; else, with slab 'floor', the fenced face (a face of the network
    plus railings with no door) containing it."""
    room = next((s for s in spaces if s['poly'].contains(pt)), None)
    if room is not None:
        return 'room', room
    area = next((u for u in unfloored if u['poly'].contains(pt)), None)
    if area is not None:
        return 'unfloored', area
    near = sorted((round(s['poly'].distance(pt), 4), i) for i, s in enumerate(spaces))
    if near and near[0][0] <= ROOM_NEAR:
        return 'room', spaces[near[0][1]]
    if slab == 'floor':
        face = next((t for t in fenced if t.contains(pt)), None)
        if face is not None:
            return 'fenced', face
    return None, None


# ---------------------------------------------------------------------------------------------------- openings
def _frame(a, b):
    L = math.dist(a, b)
    if L < 1e-9:
        return None, 0.0
    return ((b[0] - a[0]) / L, (b[1] - a[1]) / L), L


def opening_matches(rec: Mapping, fix: Mapping) -> bool:
    a, b = tuple(rec['a']), tuple(rec['b'])
    fa, fb = (float(fix['a'][0]), float(fix['a'][1])), (float(fix['b'][0]), float(fix['b'][1]))
    if (math.dist(a, fa) <= ENDS and math.dist(b, fb) <= ENDS) or (math.dist(a, fb) <= ENDS and math.dist(b, fa) <= ENDS):
        return True
    return False


def opening_on_line(rec: Mapping, fix: Mapping) -> bool:
    a, b = tuple(rec['a']), tuple(rec['b'])
    fa, fb = (float(fix['a'][0]), float(fix['a'][1])), (float(fix['b'][0]), float(fix['b'][1]))
    u, L = _frame(a, b)
    v, L2 = _frame(fa, fb)
    if u is None or v is None or abs(u[0] * v[0] + u[1] * v[1]) < math.cos(math.radians(5)):
        return False
    n = (-u[1], u[0])
    if max(abs((p[0] - a[0]) * n[0] + (p[1] - a[1]) * n[1]) for p in (fa, fb)) > LINE:
        return False
    s = sorted((p[0] - a[0]) * u[0] + (p[1] - a[1]) * u[1] for p in (fa, fb))
    return min(L, s[1]) - max(0.0, s[0]) >= OVERLAP * min(L, L2)


def match_openings(records: list[dict], fixes: list[tuple[int, dict]]) -> dict[int, int]:
    """fixes: [(fix index, OpeningFix)] of one floor -> {fix index: record index}. Ends first, then the same line."""
    out, taken = {}, set()
    for fi, f in fixes:
        j = next((j for j, r in enumerate(records) if j not in taken and opening_matches(r, f)), None)
        if j is None:
            j = next((j for j, r in enumerate(records) if j not in taken and opening_on_line(r, f)), None)
        if j is not None:
            out[fi] = j
            taken.add(j)
    return out
