"""Fixes applied by the builder on every run (docs/upload/DESIGN.md U-10.6).

1. Set aside (`fixes.setAside`, ItemRefs): the matched items leave the source's items BEFORE everything (the detector
   included). A ref whose key is an INSERT's sets aside the INSERT, its attributes (`key@...`) and every item whose key
   starts with `key + '/'` (its whole subtree). Matching, first that applies:
     (a) the exact key on the same source;
     (b) the same element id TOGETHER WITH the same layer and `rsig` (rsig hashes the type and the points relative to
         the element's INSERT; an element id alone names a whole family instance, so it is never matched alone);
     (c) the same `sig` on the same layer;
   else the fix is unmatched (`matchedBy: None`, flag fix-unmatched, kept in the settings). When (b) or (c) matches more
   than one item nothing is removed (`ambiguous` = how many matched: "pick again").
2. Openings (`fixes.openings`): matched to a detector record of the floor when both ends lie within 0.15 m of the fix's
   a, b (either order), else when they overlap 50 % on the same line within 0.1 m; `kind` replaces the detector's
   (`none` drops it: nothing is cut), `head` / `sill` replace the computed ones.
3. Outline edges (`fixes.outlineEdges`): an accepted suggestion (the same edge within 0.05 m) becomes a wall or glass
   segment before the cut (build/outline.py).
Coordinates of fixes are sheet metres (a source's own frame, before any alignment shift).
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


class SourceIndex:
    """One source's cache items with what the matcher needs: key -> index, element ids, sig and rsig (lazily)."""

    def __init__(self, items: list[dict], k: float):
        self.items, self.k = items, k
        self.by_key: dict[str, int] = {}
        for i, d in enumerate(items):
            kk = d.get('k')
            if kk is not None and kk not in self.by_key:
                self.by_key[kk] = i
        self._eid: dict[int, str | None] = {}
        self._sig: dict[int, str] = {}
        self._rsig: dict[int, str] = {}

    def eid(self, i: int) -> str | None:
        if i not in self._eid:
            self._eid[i] = N.element_id(_names(self.items[i]))
        return self._eid[i]

    def sig(self, i: int) -> str:
        if i not in self._sig:
            self._sig[i] = K.sig(self.items[i], self.k)
        return self._sig[i]

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
        if i not in self._rsig:
            self._rsig[i] = K.rsig(self.items[i], self.element_insert(i), self.k)
        return self._rsig[i]

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
        if not hasattr(self, '_by_eid'):
            self._by_eid: dict[tuple, list[int]] = {}
            for i, d in enumerate(self.items):
                e = self.eid(i)
                if e is not None:
                    self._by_eid.setdefault((d['lay'], e), []).append(i)
        return self._by_eid.get((layer, eid), [])

    def by_sig(self, layer: str, sig: str) -> list[int]:
        if not hasattr(self, '_by_sig'):
            self._by_sig: dict[tuple, list[int]] = {}
            for i, d in enumerate(self.items):
                self._by_sig.setdefault((d['lay'], self.sig(i)), []).append(i)
        return self._by_sig.get((layer, sig), [])


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
    index = {sha: SourceIndex(its, k_of[sha]) for sha, its in sources.items()}
    gone: dict[str, set[int]] = {sha: set() for sha in sources}
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
        rows.append({'fix': fi, 'matchedBy': by, 'items': len(idx), 'ambiguous': amb,
                     'key': index[sha].items[idx[0]].get('k') if idx else None})
        if idx:
            keys_by_floor.setdefault(ref.get('floor'), []).extend(
                k for k in (index[sha].items[i].get('k') for i in idx) if k)
    kept = {sha: ([d for i, d in enumerate(its) if i not in gone[sha]] if gone[sha] else its) for sha, its in sources.items()}
    return kept, rows, keys_by_floor


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
