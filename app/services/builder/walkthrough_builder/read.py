"""The reading step: one ezdxf pass over a source's DXF, three outputs (docs/upload/DESIGN.md U-7.1, U-7.2, U-7.4).

    read_source(dxf_path, units, out_dir, source={sha1, name}, log=print) -> ReadResult
      out_dir/items.pkl     {items, layers, units}: detector/tools/prims.py's items plus `k`, in its frame (DXF units / 1000)
      out_dir/drawing.json  DrawingRead (drawing.py)
      out_dir/plan.json.gz  PlanGeometry (plangeom.py)

The walk is prims.py's `_flatten` unchanged in what it keeps and in its arithmetic (model space only; INSERTs unpacked
with `virtual_entities()` to depth 8; layer `0` inside a block takes the INSERT's layer; an ATTRIB keeps its own layer;
DIMENSION and the SKIP types not kept; coordinates `v.x / 1000`; every exception per entity swallowed), with these
changes only:
  1. curves are flattened at 10 mm expressed in the drawing's units (`units.flatten_distance`: exactly 10 for mm);
  2. each item gets `k`, its nested key (U-7.2): the top-level entity's handle, then per level of nesting the handle of
     the block entity it was copied from (`source_of_copy`), joined by '/'; a level whose entity has no such handle is
     `~<index in virtual_entities order>`, and a handle met twice under one INSERT (a block reached through an INSERT
     that cannot be transformed, a proxy's pieces) gets `~<index>` appended, so keys are unique within a source. An
     ATTRIB is `<insert key>@<attrib handle>`. Hatch loops share their hatch's key (the hatch is one item);
  3. `MemoryError` and `RecursionError` are re-raised from the per-entity handlers (U-3.5: a memory cap fails
     allocations instead of killing); every other exception is still swallowed, and counted;
  4. the same pass keeps, beside the items, what drawing.json needs: text heights and the layers of the INSERTs around
     each text, the arcs (centre in world coordinates, radius, sweep), the DIMENSIONs per layer and their measurements.
Units (U-7.4): the quick decision before the walk (`units.quick`, or the units staff chose), the full door vote on the
walked items, and a second walk when the two disagree.

A drawing the reader cannot open raises `ReadFailed` with a plain sentence naming the upload (never a server path);
`MemoryError` propagates (the step child exits with 75, U-3.5). Owner: U2.
"""
from __future__ import annotations

import collections
import gzip
import json
import math
import pickle
import statistics
import time
from collections.abc import Callable
from pathlib import Path

from ezdxf import path as ezpath

from . import units as U
from .contracts import ReadResult

#: prims.py's SKIP, verbatim: types never kept as items
SKIP = ('POINT', 'ATTDEF', 'WIPEOUT', 'IMAGE', 'VIEWPORT', 'OLE2FRAME', '3DSOLID', 'REGION', 'BODY', 'MESH')
#: re-raised from every per-entity handler (U-3.5, U-7.1)
FATAL = (MemoryError, RecursionError)
#: the walk's depth limit, prims' own
MAX_DEPTH = 8

ITEMS_FILE, DRAWING_FILE, PLAN_FILE = 'items.pkl', 'drawing.json', 'plan.json.gz'


class ReadFailed(RuntimeError):
    """The drawing cannot be read. The message is a plain sentence for staff (it names the upload, never a path)."""


# ===================================================================================================================== walk
def _handle(ent) -> str | None:
    """The entity's own handle, or for a virtual copy the handle of the block entity it was copied from."""
    try:
        h = ent.dxf.get('handle')
        if h:
            return str(h)
        src = ent.source_of_copy
        if src is not None:
            h = src.dxf.get('handle')
            return str(h) if h else None
    except FATAL:
        raise
    except Exception:
        return None
    return None


def _part(ent, i: int, seen: set[str]) -> str:
    part = _handle(ent) or f'~{i}'
    if part in seen:
        part = f'{part}~{i}'
    seen.add(part)
    return part


def walk_doc(doc, units: str) -> dict:
    """prims._flatten over an opened document, with the keys and side tables of the module text. -> {
       items, layers (name -> linetype, prims'), table (name -> state, linetype, colour), texts (item index -> (height in
       DXF units or None, layers of the enclosing INSERTs)), arcs ([item index, cx, cy, r, sweep] reader frame),
       dims (layer -> count), dimValues (actual measurements), errors (type -> count), units, distance, seconds}."""
    t0 = time.perf_counter()
    dist = U.flatten_distance(units)
    items: list[dict] = []
    texts: dict[int, tuple] = {}
    arcs: list[list] = []
    dims: collections.Counter = collections.Counter()
    dim_values: list[float] = []
    errors: collections.Counter = collections.Counter()

    def swallow(exc: BaseException) -> None:
        errors[type(exc).__name__] += 1

    def text_side(height, blays) -> None:
        texts[len(items) - 1] = (height if isinstance(height, (int, float)) and math.isfinite(height) else None, blays)

    def walk(e, inh=None, depth=0, path=(), h=None, key='', blays=()):
        lay = e.dxf.get('layer', '0')
        if lay == '0' and inh:
            lay = inh
        t = e.dxftype()
        top_h = h or e.dxf.get('handle')
        base = {'t': t, 'lay': lay, 'depth': depth, 'path': '>'.join(path), 'h': top_h}
        if t == 'INSERT':
            nm = e.dxf.get('name', '')
            try:
                p = e.dxf.insert
                m = e.matrix44()
                ux, uy = m.transform_direction((1, 0, 0)), m.transform_direction((0, 1, 0))
                sx, sy = math.hypot(ux.x, ux.y), math.hypot(uy.x, uy.y)
                if ux.x * uy.y - ux.y * uy.x < 0:
                    sy = -sy                                                       # mirrored
                rot = math.degrees(math.atan2(ux.y, ux.x))
                items.append({**base, 'name': nm, 'ins': [p.x / 1000, p.y / 1000], 'rot': round(rot, 3),
                              'sx': round(sx, 4), 'sy': round(sy, 4), 'k': key})
            except FATAL:
                raise
            except Exception as exc:
                swallow(exc)
            try:
                seen_a: set[str] = set()
                for j, a in enumerate(e.attribs):
                    ip = a.dxf.insert
                    items.append({**base, 't': 'ATTRIB', 'lay': a.dxf.get('layer', lay), 'ins': [ip.x / 1000, ip.y / 1000],
                                  'text': a.dxf.get('text', ''), 'tag': a.dxf.get('tag', ''), 'block': nm,
                                  'k': f'{key}@{_part(a, j, seen_a)}'})
                    try:
                        text_side(a.dxf.get('height', None), blays + (lay,))
                    except FATAL:
                        raise
                    except Exception as exc:
                        swallow(exc)
            except FATAL:
                raise
            except Exception as exc:
                swallow(exc)
            if depth < MAX_DEPTH:
                try:
                    seen: set[str] = set()
                    for i, v in enumerate(e.virtual_entities()):
                        walk(v, lay, depth + 1, path + (nm,), top_h, f'{key}/{_part(v, i, seen)}', blays + (lay,))
                except FATAL:
                    raise
                except Exception as exc:
                    swallow(exc)
            return
        if t == 'DIMENSION':
            try:
                dims[lay] += 1
                am = e.dxf.get('actual_measurement', None)
                if isinstance(am, (int, float)) and math.isfinite(am) and am:
                    dim_values.append(float(am))
            except FATAL:
                raise
            except Exception as exc:
                swallow(exc)
            return                                                   # dimensions: not kept as items
        if t in ('TEXT', 'MTEXT', 'ATTRIB'):
            try:
                p = e.dxf.insert
                s = (e.plain_text() if t == 'MTEXT' else e.dxf.get('text', '')).strip()
                items.append({**base, 'ins': [p.x / 1000, p.y / 1000], 'text': s, 'k': key})
            except FATAL:
                raise
            except Exception as exc:
                swallow(exc)
                return
            try:
                text_side(e.dxf.get('char_height' if t == 'MTEXT' else 'height', None), blays)
            except FATAL:
                raise
            except Exception as exc:
                swallow(exc)
            return
        if t == 'HATCH':
            try:
                loops = [[[v.x / 1000, v.y / 1000] for v in bp.flattening(distance=dist)] for bp in ezpath.from_hatch(e)]
                items.append({**base, 'loops': loops, 'solid': bool(e.dxf.get('solid_fill', 0)),
                              'pattern': e.dxf.get('pattern_name', ''), 'k': key})
            except FATAL:
                raise
            except Exception as exc:
                swallow(exc)
            return
        if t in SKIP:
            return
        try:
            pts = [[v.x / 1000, v.y / 1000] for v in ezpath.make_path(e).flattening(distance=dist)]
        except FATAL:
            raise
        except Exception as exc:
            swallow(exc)
            return
        if not pts:
            return
        closed = False
        try:
            closed = bool(e.closed) if t == 'LWPOLYLINE' else (t == 'CIRCLE' or (t == 'POLYLINE' and e.is_closed))
        except FATAL:
            raise
        except Exception as exc:
            swallow(exc)
        items.append({**base, 'pts': pts, 'closed': closed, 'lt': e.dxf.get('linetype', 'BYLAYER'), 'k': key})
        if t == 'ARC':
            try:
                d = e.dxf
                c = d.center
                ext = d.get('extrusion', None)
                if ext is not None and (abs(ext[0]) > 1e-12 or abs(ext[1]) > 1e-12 or ext[2] < 0):
                    c = e.ocs().to_wcs(c)
                arcs.append([len(items) - 1, c.x / 1000, c.y / 1000, abs(d.radius) / 1000,
                             (d.end_angle - d.start_angle) % 360])
            except FATAL:
                raise
            except Exception as exc:
                swallow(exc)

    for i, e in enumerate(doc.modelspace()):
        walk(e, key=str(e.dxf.get('handle') or f'~t{i}'))
    layers = {la.dxf.name: la.dxf.get('linetype', 'Continuous') for la in doc.layers}
    table = {}
    for la in doc.layers:
        try:
            colour = la.dxf.get('color', None)
            table[la.dxf.name] = {'on': not la.is_off(), 'frozen': la.is_frozen(), 'locked': la.is_locked(),
                                  'plot': bool(la.dxf.get('plot', 1)),
                                  'linetype': str(la.dxf.get('linetype', 'Continuous') or 'Continuous'),
                                  'colour': abs(int(colour)) if isinstance(colour, int) else None}
        except FATAL:
            raise
        except Exception as exc:
            swallow(exc)
    return {'items': items, 'layers': layers, 'table': table, 'texts': texts, 'arcs': arcs, 'dims': dict(dims),
            'dimValues': dim_values, 'errors': dict(errors), 'units': units, 'distance': dist,
            'seconds': time.perf_counter() - t0}


def segments(items: list[dict]):
    """Straight segments of the line work (LINE, LWPOLYLINE, POLYLINE), reader frame: the door leaves' candidates."""
    for d in items:
        if d['t'] in ('LINE', 'LWPOLYLINE', 'POLYLINE'):
            P = d.get('pts') or ()
            yield from zip(P, P[1:])


def arcs_with_ends(W: dict) -> list[tuple]:
    """The walk's arcs as (cx, cy, r, sweep, end_a, end_b) for units.door_votes, the ends from the flattened item."""
    out = []
    for idx, cx, cy, r, sweep in W['arcs']:
        P = W['items'][idx]['pts']
        out.append((cx, cy, r, sweep, tuple(P[0]), tuple(P[-1])))
    return out


def vote(W: dict) -> None:
    """The full door vote on the walked items (U-7.4): fills W['votes'] and W['leaf'] (per arc: it has a leaf)."""
    votes, leaf = U.door_votes(arcs_with_ends(W), segments(W['items']))
    W['votes'], W['leaf'] = votes, leaf


# ============================================================================================================== read_source
def open_dxf(dxf_path: Path, name: str):
    """ezdxf.recover.readfile with plain failures (ReadFailed naming the upload; the file's own path never appears in
    the message): -> (doc, auditor)."""
    from ezdxf import recover
    from ezdxf.lldxf.const import DXFError

    def plain(exc: BaseException) -> str:
        what = (str(exc).splitlines() or [type(exc).__name__])[0][:200] or type(exc).__name__
        for p in {str(dxf_path), str(Path(dxf_path).resolve()), Path(dxf_path).name}:
            if p:
                what = what.replace(p, name)
        return what

    try:
        return recover.readfile(str(dxf_path))
    except FATAL:
        raise
    except FileNotFoundError as exc:
        raise ReadFailed(f'{name}: the converted drawing is missing, so it cannot be read') from exc
    except DXFError as exc:
        what = plain(exc)
        if 'attribute "layer"' in what or ('layer' in what.lower() and 'name' in what.lower()):
            raise ReadFailed(f'{name}: a layer name the reader cannot take ({what}); export the drawing again with '
                             f'plain layer names') from exc
        raise ReadFailed(f'{name}: the drawing cannot be read as a DXF ({what})') from exc
    except Exception as exc:                                  # OSError, UnicodeError, ValueError ... of a broken file
        raise ReadFailed(f'{name}: the drawing cannot be read ({type(exc).__name__})') from exc


def _walk(doc, units: str, name: str) -> dict:
    """walk_doc with plain failures: RecursionError (re-raised by the per-entity handlers, U-3.5) and anything that
    escapes the walk's top level become ReadFailed; MemoryError propagates."""
    try:
        W = walk_doc(doc, units)
    except MemoryError:
        raise
    except RecursionError as exc:
        raise ReadFailed(f'{name}: its blocks are nested too deeply to read') from exc
    except Exception as exc:
        raise ReadFailed(f'{name}: the drawing cannot be read ({type(exc).__name__} in its entities)') from exc
    vote(W)
    return W


def peak_memory_mb() -> float | None:
    """This process's peak commit (PeakPagefileUsage) in MB, on Windows; None elsewhere or when unknown."""
    try:
        import ctypes
        from ctypes import wintypes

        class PMC(ctypes.Structure):
            _fields_ = [('cb', wintypes.DWORD), ('PageFaultCount', wintypes.DWORD),
                        ('PeakWorkingSetSize', ctypes.c_size_t), ('WorkingSetSize', ctypes.c_size_t),
                        ('QuotaPeakPagedPoolUsage', ctypes.c_size_t), ('QuotaPagedPoolUsage', ctypes.c_size_t),
                        ('QuotaPeakNonPagedPoolUsage', ctypes.c_size_t), ('QuotaNonPagedPoolUsage', ctypes.c_size_t),
                        ('PagefileUsage', ctypes.c_size_t), ('PeakPagefileUsage', ctypes.c_size_t)]
        pmc = PMC()
        pmc.cb = ctypes.sizeof(PMC)
        psapi = ctypes.WinDLL('psapi')
        k32 = ctypes.WinDLL('kernel32')
        k32.GetCurrentProcess.restype = wintypes.HANDLE
        psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(PMC), wintypes.DWORD]
        if not psapi.GetProcessMemoryInfo(k32.GetCurrentProcess(), ctypes.byref(pmc), pmc.cb):
            return None
        return round(pmc.PeakPagefileUsage / 2 ** 20, 1)
    except Exception:
        return None


def json_bytes(obj) -> bytes:
    """Compact UTF-8 JSON, no NaN (the browser's JSON.parse refuses them)."""
    return json.dumps(obj, ensure_ascii=False, allow_nan=False, separators=(',', ':')).encode('utf-8')


def gzip_bytes(data: bytes) -> bytes:
    """gzip level 6 (U-7.5) with no time stamp: the same bytes for the same drawing."""
    return gzip.compress(data, compresslevel=6, mtime=0)


def read_source(dxf_path: Path, units: str | None, out_dir: Path, *, source: dict,
                log: Callable[[str], None] | None = None) -> ReadResult:
    """U-7: one ezdxf pass over `dxf_path` writing items.pkl, drawing.json and plan.json.gz into `out_dir`. `units` None
    lets the reader decide (U-7.4); otherwise the read is made in those units (a units change on the Files step).
    `source` = {sha1, name} of the upload. -> ReadResult (contracts.py)."""
    from .drawing import drawing_read
    from .plangeom import plan_geometry

    say = log or (lambda _s: None)
    t0 = time.perf_counter()
    name = str(source.get('name') or 'the drawing')
    if units is not None and units not in U.UNITS_K:
        raise ValueError(f'unknown units {units!r} (allowed: {", ".join(U.UNITS)})')
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    doc, auditor = open_dxf(Path(dxf_path), name)
    t_open = time.perf_counter() - t0
    ins = doc.header.get('$INSUNITS', None)
    ins = ins if isinstance(ins, int) else None
    if units is None:
        first = U.quick(doc)
        walk_units = first['used']
    else:
        walk_units = units
    W = _walk(doc, walk_units, name)
    if not W['items']:
        raise ReadFailed(f'{name}: the drawing has nothing in model space to read (an empty or cut-short file?)')
    dim_median = statistics.median(W['dimValues']) if W['dimValues'] else None
    decided = U.decide(ins, W['votes'], dim_median, forced=units)
    if decided['used'] != walk_units:
        # the full vote overrules the quick one: walk again, flattening in the decided units (U-7.4). The votes do not
        # depend on the flattening, so a second decision says the same; if it ever did not, the first one stands (the
        # items are flattened for it)
        say(f'{name}: read again in {U.WORDS[decided["used"]]} ({decided["note"]})')
        first = decided
        W = _walk(doc, first['used'], name)
        dim_median = statistics.median(W['dimValues']) if W['dimValues'] else None
        decided = U.decide(ins, W['votes'], dim_median, forced=units)
        if decided['used'] != first['used']:
            decided = first
    used = decided['used']
    W['acad'] = doc.dxfversion
    W['insUnits'] = ins
    W['auditErrors'] = len(auditor.errors)
    W['auditFixes'] = len(auditor.fixes)
    del doc, auditor

    items = W['items']
    with open(out_dir / ITEMS_FILE, 'wb') as f:
        pickle.dump({'items': items, 'layers': W['layers'], 'units': used}, f)
    seconds = time.perf_counter() - t0
    dr = drawing_read(W, source={'sha1': source['sha1'], 'name': source.get('name', '')}, units=decided,
                      seconds=seconds)
    plan = plan_geometry(items, source=source['sha1'], units=used, extents=dr['extents'])
    dr['reader']['seconds'] = round(time.perf_counter() - t0, 2)
    dr['reader']['peakMemoryMB'] = peak_memory_mb()
    (out_dir / DRAWING_FILE).write_bytes(json_bytes(dr))
    (out_dir / PLAN_FILE).write_bytes(gzip_bytes(json_bytes(plan)))
    seconds = round(time.perf_counter() - t0, 2)
    swallowed = sum(W['errors'].values())
    say(f'{name}: {len(items):,} items, {len(dr["layers"])} layers, {len(dr["levelTags"])} level tags, '
        f'{len(dr["gridLabels"])} grid labels, {len(dr["areas"])} areas in {seconds:.1f} s '
        f'(opened in {t_open:.1f} s); units {used}: {decided["note"]}'
        + (f'; {swallowed} entities could not be read and were left out' if swallowed else ''))
    return ReadResult(items=str(out_dir / ITEMS_FILE), drawing=str(out_dir / DRAWING_FILE),
                      plan=str(out_dir / PLAN_FILE), units=decided, seconds=seconds)
