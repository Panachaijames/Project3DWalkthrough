"""Deleted furniture boxes (step BX, 16 Nov 2026; docs/boxes/DESIGN.md 3 - 5, docs/contract-issues/BX.md).

The per-piece edits of a built version live in its overrides.json beside the saved heights, same revision and lock:
`"pieceEdits": {"<piece id>": {"removed": true}, ...}`. The model, its stamp and every other version file never change:
the edits are an overlay. Pure functions over a BuiltModel (plain dicts) and plain maps, no I/O:

    close_removed(ids, pieces)      the closure rule (DESIGN 2.5): every piece whose `on` names a removed piece is removed
                                    too, transitively. The viewer has the same rule (furniture/logic.ts closeRemoved); both
                                    are tested against packages/viewer/test/fixtures/furniture/close-removed.cases.json.
    order(model, ids)               ids in the CSV order: floor in the model's order, kind in the kinds table's order, id.
    live(model, saved)              what every reader uses (GET, getVersion, the 412 details, CSV, Max, carry): model ids
                                    only, entries exactly {"removed": true}, closed, in the CSV order. Anything else in a
                                    saved file (an unknown id, a corrupt value, a field of a later step) is ignored, so an
                                    odd file never answers 500.
    canonical(model, edits)         the PUT: 422 invalid_piece_edits for an id that is not a model piece; `removed: false`
                                    and an empty edit dropped; closed; in the CSV order.
    carry(old_model, old_edits, new_model)
                                    a new version's carry-over (DESIGN 5.1): only the old live map's tops, matched by what
                                    the box is and where it stands (never by bare id: ids are ranks), one-to-one.
    carried_record(...)             versions/<n>/source/carried-edits.json, the record of a carry; carry_into(...) both
                                    the new version's pieceEdits and that record (create_version, the seed's re-map).
    carried_note(record)            (from, how many did not carry) for the version detail's `carriedEdits`, or None.
    filter_max_script(script, prefix, removed)
                                    the 3ds Max download without the removed pieces' furnBox lines, a comment naming their
                                    Max objects as the new line 3 (DESIGN 4); max_script_ids(script, prefix) its ids.
"""
from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping
from typing import Any, NamedTuple

from .errors import ApiError
from .store.base import StoreError

#: The one edit there is today. Written by hand wherever it is written (store/local.py), never from a model with Nones.
REMOVED: dict[str, bool] = {'removed': True}
CARRIED_FORMAT = 'walkthrough-carried-edits/1'
#: versions/<n>/source/<CARRIED_FILE>: written by create_version (and the seed's re-map) whenever the old version had edits
CARRIED_FILE = 'carried-edits.json'
MAX_UNKNOWN_IDS = 20                 # 422 invalid_piece_edits: details.unknownIds lists at most this many
MAX_NAMES = 30                       # the Max script's comment names at most this many objects, then ", and N more"

# The carry-over's fingerprint (DESIGN 5.1): the same floor key, kind and family; drawing-frame centres within 10 mm on each
# axis; w and d within 10 mm; turns within 0.5 degrees, modulo 180 (modulo 90 when both boxes are square: w - d under 1 mm,
# as vendor/furniture_kit.py finish() normalises them). Handle, block and layer are not compared (a Revit re-export
# renumbers handles and can rename blocks); the one-to-one rule covers the duplicates this lets in.
PLACE_TOL_M = 0.010
SIZE_TOL_M = 0.010
TURN_TOL_DEG = 0.5
SQUARE_M = 0.001
_EPS = 1e-9                          # model numbers are rounded to the mm: a difference of exactly 10 mm still matches

WHY_NO_MATCH = 'no match'
WHY_ON_A_DELETED_SUPPORT = 'was on a deleted support'


# ---------------------------------------------------------------------------------------------------- the model's pieces
def pieces_of(model: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """The model's furniture pieces that have a string id (a validated model: all of them)."""
    furniture = model.get('furniture') or []
    if not isinstance(furniture, list):
        return []
    return [p for p in furniture if isinstance(p, Mapping) and isinstance(p.get('id'), str)]


def close_removed(ids: Iterable[str], pieces: Iterable[Mapping[str, Any]]) -> set[str]:
    """`ids` and every piece standing on one of them, transitively (a piece whose `on` names a removed piece is removed).
    Supports never stand on anything today; the loop is cheap anyway. The ids given are kept as they are (callers pass
    model ids only)."""
    standing: dict[str, list[str]] = defaultdict(list)
    for p in pieces:
        on = p.get('on')
        if isinstance(on, str) and isinstance(p.get('id'), str):
            standing[on].append(p['id'])
    removed = set(ids)
    todo = list(removed)
    while todo:
        for child in standing.get(todo.pop(), ()):
            if child not in removed:
                removed.add(child)
                todo.append(child)
    return removed


def order(model: Mapping[str, Any], ids: Iterable[str]) -> list[str]:
    """`ids` (once each) in the CSV order: floor in the model's order, kind in the kinds table's order, then id
    (furniture_csv.csv_text sorts its rows the same way). An id the model lacks sorts last, by its text."""
    floors = {f.get('key'): i for i, f in enumerate(model.get('floors') or []) if isinstance(f, Mapping)}
    kinds = {k.get('key'): i for i, k in enumerate(model.get('furnitureKinds') or []) if isinstance(k, Mapping)}
    by_id = {p['id']: p for p in pieces_of(model)}

    def key(pid: str) -> tuple[int, int, str]:
        p = by_id.get(pid)
        if p is None:
            return len(floors) + 1, len(kinds) + 1, pid
        return floors.get(p.get('floor'), len(floors)), kinds.get(p.get('kind'), len(kinds)), pid
    return sorted(set(ids), key=key)


def _is_removed(value: Any) -> bool:
    """An edit that removes its piece: exactly `removed: true` (a JSON object, or the API's PieceEdit)."""
    if isinstance(value, Mapping):
        return value.get('removed') is True
    return getattr(value, 'removed', None) is True


def as_map(model: Mapping[str, Any], ids: Iterable[str]) -> dict[str, dict[str, bool]]:
    """{id: {"removed": true}} for `ids`, in the CSV order."""
    return {pid: dict(REMOVED) for pid in order(model, ids)}


# ---------------------------------------------------------------------------------------------------- reading and the PUT
def live(model: Mapping[str, Any], saved: Any) -> dict[str, dict[str, bool]]:
    """The saved edits as every reader sees them: entries whose id is a piece of `model` and whose `removed` is exactly
    true (other fields of the entry ignored; a non-object value, an unknown id or a `removed` that is not true ignored),
    closed, in the CSV order. {} when `saved` is not a non-empty object."""
    if not isinstance(saved, Mapping) or not saved:
        return {}
    pieces = pieces_of(model)
    ids = {p['id'] for p in pieces}
    picked = [pid for pid, edit in saved.items() if pid in ids and _is_removed(edit)]
    if not picked:
        return {}
    return as_map(model, close_removed(picked, pieces))


def canonical(model: Mapping[str, Any], edits: Mapping[str, Any]) -> dict[str, dict[str, bool]]:
    """The PUT's `pieceEdits` (DESIGN 3.2): every key a piece of the model, else 422 invalid_piece_edits (details:
    unknownIds = the first 20 in order, count = how many); an edit that removes nothing (`removed: false`, `{}`) is
    dropped; the rest closed (2.5) and ordered (3.1). Non-object values and unknown inner keys never get here: the
    request model refuses them (FastAPI's 422)."""
    pieces = pieces_of(model)
    ids = {p['id'] for p in pieces}
    unknown = sorted(pid for pid in edits if pid not in ids)
    if unknown:
        shown = unknown[:MAX_UNKNOWN_IDS]
        more = f' and {len(unknown) - len(shown)} more' if len(unknown) > len(shown) else ''
        raise ApiError(422, 'invalid_piece_edits', 'not a furniture piece of the model: ' + ', '.join(shown) + more,
                       {'unknownIds': shown, 'count': len(unknown)})
    picked = [pid for pid, edit in edits.items() if _is_removed(edit)]
    if not picked:
        return {}
    return as_map(model, close_removed(picked, pieces))


# ---------------------------------------------------------------------------------------------------- carry-over (5.1)
class Carried(NamedTuple):
    """A carry's result: `carried` old top id -> new id; `cascaded` the new ids the closure added (CSV order);
    `not_carried` one row {id, floor, kind, family, why} per old removed piece whose deletion did not carry (old ids,
    in the old model's CSV order)."""

    carried: dict[str, str]
    cascaded: list[str]
    not_carried: list[dict[str, Any]]

    def edits(self, new_model: Mapping[str, Any]) -> dict[str, dict[str, bool]]:
        """The new version's pieceEdits: the carried tops and what stands on them, closed, ordered."""
        return as_map(new_model, [*self.carried.values(), *self.cascaded])


def _number(v: Any) -> bool:
    return isinstance(v, int | float) and not isinstance(v, bool) and math.isfinite(v)


def _offset(model: Mapping[str, Any]) -> tuple[float, float]:
    off = model.get('offset')
    if isinstance(off, list | tuple) and len(off) == 2 and all(_number(v) for v in off):
        return float(off[0]), float(off[1])
    return 0.0, 0.0


def _what(p: Mapping[str, Any]) -> tuple[Any, Any, Any]:
    return p.get('floor'), p.get('kind'), p.get('family')


def _same_place(p: Mapping[str, Any], p_off: tuple[float, float], q: Mapping[str, Any], q_off: tuple[float, float]) -> bool:
    """Old piece p and new piece q stand in the same place with the same size and turn (both already of the same floor,
    kind and family): drawing-frame centres within 10 mm on each axis, w and d within 10 mm, turns within 0.5 degrees
    modulo 180 (modulo 90 when both are square)."""
    if not all(_number(p.get(k)) and _number(q.get(k)) for k in ('x', 'y', 'w', 'd', 'rot')):
        return False
    if abs((p['x'] + p_off[0]) - (q['x'] + q_off[0])) > PLACE_TOL_M + _EPS:
        return False
    if abs((p['y'] + p_off[1]) - (q['y'] + q_off[1])) > PLACE_TOL_M + _EPS:
        return False
    if abs(p['w'] - q['w']) > SIZE_TOL_M + _EPS or abs(p['d'] - q['d']) > SIZE_TOL_M + _EPS:
        return False
    square = abs(p['w'] - p['d']) < SQUARE_M and abs(q['w'] - q['d']) < SQUARE_M
    period = 90.0 if square else 180.0
    turn = (p['rot'] - q['rot']) % period
    return min(turn, period - turn) <= TURN_TOL_DEG + _EPS


def _row(p: Mapping[str, Any], why: str) -> dict[str, Any]:
    return {'id': p['id'], 'floor': p.get('floor'), 'kind': p.get('kind'), 'family': p.get('family'), 'why': why}


def carry(old_model: Mapping[str, Any], old_edits: Any, new_model: Mapping[str, Any]) -> Carried:
    """The deletions a new version keeps (DESIGN 5.1). Only the TOPS of the old live map are carried (a removed piece
    whose support is not removed); a piece that went only with its support is not a deletion in its own right. A top P is
    carried to the new piece Q when Q is P's only match in the new model, P is the only old piece (removed or kept) that
    matches Q, and no other carried edit has claimed Q; otherwise P is not carried (its box shows again: never the wrong
    box deleted, the U-10.6 principle). The carried tops are closed in the new model; what the closure adds is
    `cascaded`. An old dependent that the new closure did not add back (no new piece in its place is removed) is listed
    as 'was on a deleted support'."""
    old_live = live(old_model, old_edits)
    if not old_live:
        return Carried({}, [], [])
    old_pieces, new_pieces = pieces_of(old_model), pieces_of(new_model)
    by_old = {p['id']: p for p in old_pieces}
    old_off, new_off = _offset(old_model), _offset(new_model)
    old_by_what: dict[tuple[Any, Any, Any], list[Mapping[str, Any]]] = defaultdict(list)
    new_by_what: dict[tuple[Any, Any, Any], list[Mapping[str, Any]]] = defaultdict(list)
    for p in old_pieces:
        old_by_what[_what(p)].append(p)
    for q in new_pieces:
        new_by_what[_what(q)].append(q)

    def new_matches(p: Mapping[str, Any]) -> list[Mapping[str, Any]]:
        return [q for q in new_by_what.get(_what(p), []) if _same_place(p, old_off, q, new_off)]

    def old_matches(q: Mapping[str, Any]) -> list[Mapping[str, Any]]:
        return [p for p in old_by_what.get(_what(q), []) if _same_place(p, old_off, q, new_off)]

    removed = set(old_live)
    carried: dict[str, str] = {}
    claimed: set[str] = set()
    not_carried: list[dict[str, Any]] = []
    for pid in old_live:                                       # the old CSV order
        p = by_old[pid]
        if p.get('on') in removed:
            continue                                           # a dependent: below
        found = new_matches(p)
        if not found:
            why = WHY_NO_MATCH
        elif len(found) > 1:
            why = f'{len(found)} matches'
        else:
            q = found[0]
            olds = old_matches(q)
            if len(olds) > 1:
                why = f'matches {len(olds)} old pieces'
            elif q['id'] in claimed:                           # cannot happen while matching is one-to-one; kept as the rule
                why = 'matches 2 old pieces'
            else:
                carried[pid] = q['id']
                claimed.add(q['id'])
                continue
        not_carried.append(_row(p, why))
    new_removed = close_removed(carried.values(), new_pieces)
    cascaded = [qid for qid in order(new_model, new_removed) if qid not in claimed]
    for pid in old_live:
        p = by_old[pid]
        if p.get('on') in removed and not any(q['id'] in new_removed for q in new_matches(p)):
            not_carried.append(_row(p, WHY_ON_A_DELETED_SUPPORT))
    rank = {pid: i for i, pid in enumerate(old_live)}
    not_carried.sort(key=lambda r: rank[r['id']])
    return Carried(carried, cascaded, not_carried)


def carried_record(from_version: int, result: Carried) -> dict[str, Any]:
    """versions/<n>/source/carried-edits.json: immutable, so "why did my chair come back?" can be answered."""
    return {'format': CARRIED_FORMAT, 'from': from_version, 'carried': dict(result.carried),
            'cascaded': list(result.cascaded), 'notCarried': [dict(r) for r in result.not_carried]}


def carry_into(old_model: Mapping[str, Any], old_edits: Any, new_model: Mapping[str, Any],
               from_version: int) -> tuple[dict[str, dict[str, bool]], dict[str, Any]] | None:
    """(the new version's pieceEdits, its carried-edits.json record), or None when the old version has no live edits
    (then no record is written: DESIGN 5.1 writes it whenever the old version had edits)."""
    if not live(old_model, old_edits):
        return None
    result = carry(old_model, old_edits, new_model)
    return result.edits(new_model), carried_record(from_version, result)


def carried_note(record: Any) -> tuple[int, int] | None:
    """(from, how many deleted boxes did not carry) of a carried-edits.json, or None when nothing failed to carry or the
    file is not one (read leniently: an odd file only loses the note)."""
    if not isinstance(record, Mapping) or record.get('format') != CARRIED_FORMAT:
        return None
    src, rows = record.get('from'), record.get('notCarried')
    if not isinstance(src, int) or isinstance(src, bool) or src < 1 or not isinstance(rows, list) or not rows:
        return None
    return src, len(rows)


# ---------------------------------------------------------------------------------------------------- the 3ds Max script (4)
def max_line(prefix: str) -> re.Pattern[bytes]:
    """A furnBox call of the generated script (vendor/furniture_max.py: kind, Max object name, floor index, id, ...)."""
    return re.compile(rb'    ' + re.escape(prefix.encode('utf-8')) + rb'_furnBox "[^"]*" "([^"]*)" \d+ "([^"]*)" ')


def max_script_ids(script: bytes, prefix: str) -> list[str]:
    """The piece ids of the script's furnBox lines, in the script's order (a test's and a check's view)."""
    line = max_line(prefix)
    return [m.group(2).decode('utf-8', 'replace') for m in (line.match(x) for x in script.split(b'\n')) if m]


def filter_max_script(script: bytes, prefix: str, removed: Iterable[str]) -> bytes:
    """The stored script without the furnBox line of each removed piece. The script is filtered, never regenerated (the
    API never imports the builder; the generator is vendor-pinned). Each removed id must have exactly one line, else
    StoreError "the 3ds Max script does not match its model" (500 store_error): the comment can never name a box that is
    still built. One comment line goes in as the new line 3 (line 2, the stamp, unchanged), ending as the file's lines do
    (CRLF), naming the Max objects left out (the names the 3D team deletes by in a scene built earlier): up to 30, then
    ", and N more". Kinds, spinners and materials stay. Nothing removed: the bytes as they are."""
    want = set(removed)
    if not want:
        return script
    line = max_line(prefix)
    lines = script.split(b'\n')
    kept: list[bytes] = []
    names: list[str] = []
    seen: Counter[str] = Counter()
    for text in lines:
        m = line.match(text)
        if m:
            pid = m.group(2).decode('utf-8', 'replace')
            if pid in want:
                seen[pid] += 1
                names.append(m.group(1).decode('utf-8', 'replace'))
                continue
        kept.append(text)
    wrong = sorted(pid for pid in want if seen[pid] != 1)
    if wrong:
        shown = ', '.join(f'{pid} ({seen[pid]} lines)' for pid in wrong[:5]) + (' ...' if len(wrong) > 5 else '')
        raise StoreError(f'the 3ds Max script does not match its model: a deleted box must have exactly one '
                         f'{prefix}_furnBox line ({shown})')
    count = len(names)
    listed = ', '.join(names[:MAX_NAMES]) + (f', and {count - MAX_NAMES} more' if count > MAX_NAMES else '')
    comment = (f'-- {count} furniture box{"es" if count != 1 else ""} deleted in the walkthrough app '
               f'{"are" if count != 1 else "is"} left out: {listed}')
    end = b'\r' if lines and lines[0].endswith(b'\r') else b''
    kept.insert(min(2, len(kept)), comment.encode('utf-8') + end)
    return b'\n'.join(kept)
