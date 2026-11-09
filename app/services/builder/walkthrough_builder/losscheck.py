"""The "nothing lost" check: dwgread's JSON against the DXF, by handle (docs/upload/DESIGN.md U-6.3; a port of
docs/upload/reference/nothing_lost_stream.py, with the lost inserts of reference/missing_plot.py).

1. **DWG side** (`DwgSide.scan`): `dwgread.exe -O JSON input.dwg` with stdout piped into a line scanner (never written
   to disk: about 20x the DWG). Only the `OBJECTS` section: per handle the type (DWG names mapped to DXF names), layer,
   owner (`entmode` 2 model space, 1 paper space, else the owner block, or the parent: VERTEX -> POLYLINE, ATTRIB ->
   INSERT); layer and block names; each block's base point; each INSERT / MINSERT's placement; UNKNOWN / proxy counts.
2. **DXF side** (`DxfSide.scan`): a raw group-code scan (no ezdxf) of TABLES (LAYER; BLOCK_RECORD handle -> name),
   BLOCKS and ENTITIES: per entity code 5 (handle), 8 (layer), the first 330 outside `{ACAD_REACTORS}` (owner).
3. **Compare** (`compare`): missing and extra handles; type, layer and owner changes; layers; renamed blocks (DWG
   anonymous names `*D`, `*U`, `*X` are unnumbered, the DXF numbers them); blocks whose definition came out empty or
   short, each with its model-space placements composed through nested inserts.
4. **Messages** of the converter by class (`classify`); one example line each, paths removed.
5. **Verdict from the comparison only**: `loss` when an entity of model space or of a block placed (at any depth) in
   model space is missing; `minor` when nothing there is missing but something changed (layers or owners the decode did
   not know, written to layer 0; empty layers on ATTRIB / ATTDEF; items of unplaced blocks); `ok` otherwise. Message
   classes never decide it; `error:*`, `unknown-object` and `other` add one note unless something is missing.

The cached report keeps the lost inserts in DRAWING units (the units are known only after the read); `publish()` gives
the copy in sheet metres. `not_converted()` is a DXF upload's report, `failed_report()` a failed conversion's.

Owner: U1.
"""
from __future__ import annotations

import collections
import io
import json
import math
import os
import re
import subprocess
import sys
import time
from collections.abc import Callable, Iterable
from pathlib import Path

# ============================================================================================================ messages
#: (class, pattern), first match wins; the classes of U-6.3 (+ `todo` / `segment` lines counted as unhandled-class)
MESSAGE_CLASSES: list[tuple[str, re.Pattern]] = [
    ('hatch-short-handles', re.compile(r'Skip HATCH common handles')),
    ('handle-not-found', re.compile(r'Object handle not found')),
    ('unstable-class', re.compile(r'Unstable Class')),
    ('unhandled-class', re.compile(r'Unhandled (Class|Object)|^Warning: TODO |segment yet unhandled')),
    ('unknown-flag', re.compile(r'Unknown flag')),
    ('unknown-object', re.compile(r'Unknown object')),
    ('wrong-layer', re.compile(r'Wrong [A-Za-z_0-9]+\.layer')),
]
#: classes that never add a note (U-6.3)
QUIET = {'hatch-short-handles', 'handle-not-found', 'unstable-class', 'unhandled-class', 'unknown-flag', 'wrong-layer'}
_ERROR = re.compile(r'^\s*ERROR:?\s*(.*)$')
_INVALID = re.compile(r'^(Invalid\s+[A-Za-z_][A-Za-z_0-9]*(?:\.[A-Za-z_][A-Za-z_0-9]*)?)')
_KIND_HEAD = re.compile(r'^([^:0-9]+?)\s*(?::|\d|$)')
_WIN_PATH = re.compile(r'(?:[A-Za-z]:[\\/]|\\\\)[^\s"\'<>|*?]*')
_SKIP = ('Reading DWG file', 'Writing DXF file', 'Reading DXF file', 'Writing DWG file', 'SUCCESS')


def scrub(text: str) -> str:
    """`text` with every absolute Windows path replaced by its last part (messages never carry a server path)."""
    def last(m: re.Match) -> str:
        p = m.group(0).rstrip('\\/.,;:)')
        tail = m.group(0)[len(p):]
        return re.split(r'[\\/]', p)[-1] + tail if p else m.group(0)
    return _WIN_PATH.sub(last, text)


def error_kind(rest: str) -> str:
    """The `<kind>` of an `ERROR:` line: 'buffer overflow', 'bit_read_*', 'Invalid ATTRIB.keep_duplicate_records',
    'Invalid CMC', ... (numbers and positions dropped)."""
    rest = rest.strip()
    if 'buffer overflow' in rest:
        return 'buffer overflow'
    if rest.startswith('bit_read_'):
        return 'bit_read_*'
    m = _INVALID.match(rest)
    if m:
        return m.group(1)
    m = _KIND_HEAD.match(rest)
    head = (m.group(1) if m else rest).strip()
    return head[:60] or 'unknown'


def classify(line: str) -> str | None:
    """The message class of one converter line (U-6.3), or None for a line that is not a message."""
    s = line.strip()
    if not s or s.startswith(_SKIP):
        return None
    for name, rx in MESSAGE_CLASSES:
        if rx.search(s):
            return name
    m = _ERROR.match(s)
    if m:
        return 'error:' + error_kind(m.group(1))
    return 'other'


def messages(lines: Iterable[str]) -> list[dict]:
    """[{class, count, example}] by count (most first), one example line each with paths removed."""
    out: dict[str, dict] = {}
    for line in lines:
        c = classify(line)
        if c is None:
            continue
        row = out.get(c)
        if row is None:
            out[c] = row = {'class': c, 'count': 0, 'example': scrub(line.strip())[:300]}
        row['count'] += 1
    return sorted(out.values(), key=lambda r: (-r['count'], r['class']))


def read_log(path: Path) -> list[str]:
    try:
        return Path(path).read_text(encoding='utf-8', errors='replace').splitlines()
    except FileNotFoundError:
        return []


# ============================================================================================================== names
_DIM = re.compile(r'^DIMENSION_')
TYPE_MAP = {'VERTEX_2D': 'VERTEX', 'VERTEX_3D': 'VERTEX', 'VERTEX_MESH': 'VERTEX', 'VERTEX_PFACE': 'VERTEX',
            'VERTEX_PFACE_FACE': 'VERTEX', 'POLYLINE_2D': 'POLYLINE', 'POLYLINE_3D': 'POLYLINE',
            'POLYLINE_PFACE': 'POLYLINE', 'POLYLINE_MESH': 'POLYLINE', '_3DFACE': '3DFACE', '_3DSOLID': '3DSOLID',
            'TABLE': 'ACAD_TABLE', 'PROXY_ENTITY': 'ACAD_PROXY_ENTITY'}
STRUCT = {'BLOCK', 'ENDBLK', 'SEQEND'}
_ANON = re.compile(r'^(\*[A-Z])\d*$')
_UPLUS = re.compile(r'\\U\+([0-9A-Fa-f]{4})')
MODEL = '*MODEL_SPACE'
PAPER = '*PAPER_SPACE'


def anon(name: str) -> str:
    """Upper case, an anonymous block's number dropped (`*U12` -> `*U`: DWG anonymous names are unnumbered), and a
    layout block's number too (`*Paper_Space0` -> `*PAPER_SPACE`: the DXF numbers the layouts)."""
    up = name.upper()
    if up.startswith(PAPER):
        return PAPER
    return _ANON.sub(lambda m: m.group(1), up)


def dxf_type(t: str) -> str:
    return 'DIMENSION' if _DIM.match(t) else TYPE_MAP.get(t, t)


def _is_paper(name: str) -> bool:
    return name.upper().startswith(PAPER)


# =========================================================================================================== DWG side
_STR_KEYS = frozenset({'entity', 'object', 'name'})
_REF_KEYS = frozenset({'handle', 'layer', 'ownerhandle', 'block_header'})
_INT_KEYS = frozenset({'entmode', 'num_cols', 'num_rows'})
_VEC_KEYS = frozenset({'ins_pt', 'scale', 'extrusion', 'base_pt'})
_NUM_KEYS = frozenset({'rotation', 'col_spacing', 'row_spacing'})
_WANTED = _STR_KEYS | _REF_KEYS | _INT_KEYS | _VEC_KEYS | _NUM_KEYS
_INSERTS = ('INSERT', 'MINSERT')


class DwgSide:
    """What dwgread decoded, by handle."""

    def __init__(self) -> None:
        self.objects = 0
        self.layers: dict[int, str] = {}           # LAYER handle -> name
        self.blocks: dict[int, str] = {}           # BLOCK_HEADER handle -> name
        self.base: dict[int, list] = {}            # BLOCK_HEADER handle -> base point
        self.raw: dict[int, dict] = {}             # entity handle -> fields (every entity, structure ones included)
        self.unknown = 0
        self.model: int | None = None
        self.ents: dict[int, tuple[str, str, str]] = {}   # handle -> (type, layer, owner name) for the comparison
        self.owner_h: dict[int, int | None] = {}  # handle -> owner block handle (model space included)

    @classmethod
    def scan(cls, lines: Iterable[str]) -> DwgSide:
        """Scans dwgread's pretty-printed JSON (object keys at 6 spaces) line by line, keeping only what it needs."""
        side = cls()
        in_objects = False
        cur: dict | None = None
        objs: list[dict] = []
        for line in lines:
            if line.startswith('  "') and not line.startswith('   '):
                in_objects = line.startswith('  "OBJECTS"')
                cur = None
                continue
            if not in_objects:
                continue
            if line.startswith('    {'):
                cur = {}
                objs.append(cur)
                continue
            if cur is None or not line.startswith('      "') or line.startswith('       '):
                continue
            q = line.find('"', 7)
            if q < 0:
                continue
            key = line[7:q]
            if key not in _WANTED:
                continue
            v = line[q + 2:].strip()
            if v.endswith(','):
                v = v[:-1].rstrip()
            try:
                if key in _STR_KEYS:
                    cur[key] = json.loads(v)
                elif key in _REF_KEYS:
                    cur[key] = json.loads(v)[-1]
                elif key in _INT_KEYS:
                    cur[key] = int(v)
                elif key in _VEC_KEYS:
                    cur[key] = [float(x) for x in json.loads(v)]
                else:
                    cur[key] = float(v)
            except (ValueError, TypeError, IndexError):
                if key in _STR_KEYS and v.startswith('"'):
                    cur[key] = v.strip('"')
        side.objects = len(objs)
        for o in objs:
            kind = o.get('entity') or o.get('object')
            if kind and ('UNKNOWN' in kind or 'PROXY' in kind):
                side.unknown += 1
            h = o.get('handle')
            if h is None:
                continue
            if o.get('object') == 'LAYER':
                side.layers[h] = o.get('name', '?')
            elif o.get('object') == 'BLOCK_HEADER':
                name = o.get('name', '?')
                side.blocks[h] = name
                side.base[h] = o.get('base_pt') or [0.0, 0.0, 0.0]
                if name.upper() == MODEL:
                    side.model = h
            elif 'entity' in o:
                side.raw[h] = o
        side._resolve()
        return side

    def owner_of(self, o: dict, depth: int = 0) -> int | None:
        """The block (header handle) an entity belongs to: its owner block, model space by entmode 2, else its
        parent's (VERTEX -> POLYLINE, ATTRIB -> INSERT)."""
        oh = o.get('ownerhandle')
        if oh in self.blocks:
            return oh
        em = o.get('entmode')
        if em == 2:
            return self.model
        if em == 1:
            return None
        par = self.raw.get(oh)
        if par is not None and depth < 4:
            return self.owner_of(par, depth + 1)
        return None

    def _resolve(self) -> None:
        for h, o in self.raw.items():
            t = dxf_type(o.get('entity', '?'))
            own = self.owner_of(o)
            self.owner_h[h] = own
            if t in STRUCT:
                continue
            if own is not None:
                name = self.blocks.get(own, '?')
            elif o.get('entmode') == 1:
                name = '*Paper_Space'
            else:
                name = '?'
            self.ents[h] = (t, self.layers.get(o.get('layer'), '?'), anon(name))

    def reachable(self) -> set[int]:
        """Block handles placed in model space at any depth (model space itself included)."""
        if self.model is None:
            return set()
        by_owner: dict[int | None, set[int]] = collections.defaultdict(set)
        for h, o in self.raw.items():
            if o.get('entity') in _INSERTS and o.get('block_header') in self.blocks:
                by_owner[self.owner_h.get(h)].add(o['block_header'])
        seen = {self.model}
        todo = [self.model]
        while todo:
            b = todo.pop()
            for nxt in by_owner.get(b, ()):
                if nxt not in seen:
                    seen.add(nxt)
                    todo.append(nxt)
        return seen

    def _insert_index(self) -> dict[int, list[dict]]:
        idx = getattr(self, '_inserts', None)
        if idx is None:
            idx = collections.defaultdict(list)
            for h, o in self.raw.items():
                if o.get('entity') in _INSERTS and o.get('block_header') is not None:
                    idx[o['block_header']].append({**o, '_h': h})
            self._inserts = idx
        return idx

    def placements(self, block: int, limit: int = 200) -> list[tuple[float, float, str]]:
        """Model-space placements of `block` composed through nested inserts: [(x, y, layer)] in drawing units, the
        block's base point mapped into model space; at most `limit`."""
        inserts = self._insert_index()
        memo: dict[int, list[tuple[tuple, str]]] = {}

        def world(b: int, depth: int) -> list[tuple[tuple, str]]:
            if b in memo:
                return memo[b]
            out: list[tuple[tuple, str]] = []
            memo[b] = out                                          # a cycle ends here
            for ins in inserts.get(b, ()):
                own = self.owner_h.get(ins['_h'])
                lay = self.layers.get(ins.get('layer'), '?')
                copies = _copies(ins, self.base.get(b))
                if own == self.model and own is not None:
                    out.extend((m, lay) for m in copies)
                elif own in self.blocks and not _is_paper(self.blocks[own]) and depth < 8:
                    for parent, play in world(own, depth + 1):
                        for m in copies:
                            out.append((_compose(parent, m), lay if lay != '0' else play))
                            if len(out) >= limit:
                                break
                if len(out) >= limit:
                    break
            return out

        base = self.base.get(block) or [0.0, 0.0, 0.0]
        res = []
        for m, lay in world(block, 0)[:limit]:
            x, y = _apply(m, base)
            res.append((x, y, lay))
        return res


def _mat(o: dict, base: list | None) -> tuple:
    """An INSERT as a 2D affine map (a, b, c, d, e, f): x' = a x + b y + e, y' = c x + d y + f, the inserted block's base
    point included; an OCS extrusion of -z mirrors x (reference/missing_plot.py)."""
    sx, sy = (o.get('scale') or [1.0, 1.0, 1.0])[:2]
    r = o.get('rotation') or 0.0
    ip = o.get('ins_pt') or [0.0, 0.0, 0.0]
    bp = base or [0.0, 0.0, 0.0]
    ca, sa = math.cos(r), math.sin(r)
    a, b, c, d = ca * sx, -sa * sy, sa * sx, ca * sy
    e = ip[0] - (a * bp[0] + b * bp[1])
    f = ip[1] - (c * bp[0] + d * bp[1])
    if (o.get('extrusion') or [0.0, 0.0, 1.0])[2] < 0:
        a, b, e = -a, -b, -e
    return a, b, c, d, e, f


def _copies(o: dict, base: list | None, limit: int = 200) -> list[tuple]:
    """The INSERT's map, or a MINSERT's one per array copy (columns and rows in the insert's turned frame)."""
    m = _mat(o, base)
    if o.get('entity') != 'MINSERT':
        return [m]
    cols, rows = max(1, int(o.get('num_cols') or 1)), max(1, int(o.get('num_rows') or 1))
    cs, rs = o.get('col_spacing') or 0.0, o.get('row_spacing') or 0.0
    r = o.get('rotation') or 0.0
    ca, sa = math.cos(r), math.sin(r)
    flip = -1.0 if (o.get('extrusion') or [0.0, 0.0, 1.0])[2] < 0 else 1.0
    out = []
    for i in range(rows):
        for j in range(cols):
            dx, dy = j * cs, i * rs
            out.append((m[0], m[1], m[2], m[3], m[4] + flip * (ca * dx - sa * dy), m[5] + (sa * dx + ca * dy)))
            if len(out) >= limit:
                return out
    return out


def _compose(m1: tuple, m2: tuple) -> tuple:
    """m1 after m2."""
    a, b, c, d, e, f = m1
    A, B, C, D, E, F = m2
    return (a * A + b * C, a * B + b * D, c * A + d * C, c * B + d * D, a * E + b * F + e, c * E + d * F + f)


def _apply(m: tuple, p: list) -> tuple[float, float]:
    return m[0] * p[0] + m[1] * p[1] + m[4], m[2] * p[0] + m[3] * p[1] + m[5]


# =========================================================================================================== DXF side
_CODEPAGES = {'ANSI_874': 'cp874', 'ANSI_932': 'cp932', 'ANSI_936': 'gbk', 'ANSI_949': 'cp949', 'ANSI_950': 'cp950',
              'ANSI_1250': 'cp1250', 'ANSI_1251': 'cp1251', 'ANSI_1252': 'cp1252', 'ANSI_1253': 'cp1253',
              'ANSI_1254': 'cp1254', 'ANSI_1255': 'cp1255', 'ANSI_1256': 'cp1256', 'ANSI_1257': 'cp1257',
              'ANSI_1258': 'cp1258'}


def _header(path: Path, size: int = 1 << 20) -> dict[str, str]:
    """$ACADVER, $DWGCODEPAGE and $INSUNITS from the start of an ASCII DXF."""
    with open(path, 'rb') as f:
        head = f.read(size).decode('latin-1')
    lines = head.splitlines()
    out: dict[str, str] = {}
    for i in range(0, len(lines) - 3):
        if lines[i].strip() == '9' and lines[i + 1].strip() in ('$ACADVER', '$DWGCODEPAGE', '$INSUNITS'):
            out.setdefault(lines[i + 1].strip(), lines[i + 3].strip())
        if lines[i].strip() == '0' and lines[i + 1].strip() == 'ENDSEC':
            break
    return out


def dxf_encoding(header: dict[str, str]) -> str:
    """UTF-8 from R2007 (AC1021) on, else the drawing's code page."""
    ver = header.get('$ACADVER', 'AC1032')
    if ver >= 'AC1021':
        return 'utf-8'
    return _CODEPAGES.get(header.get('$DWGCODEPAGE', '').upper(), 'cp1252')


def _uplus(s: str) -> str:
    return _UPLUS.sub(lambda m: chr(int(m.group(1), 16)), s) if '\\U+' in s else s


class DxfSide:
    """What the DXF holds, by handle."""

    def __init__(self) -> None:
        self.ents: dict[int, tuple[str, str, str]] = {}   # handle -> (type, layer, owner name)
        self.owner_h: dict[int, int | None] = {}
        self.layers: set[str] = set()
        self.brec: dict[int, str] = {}                     # BLOCK_RECORD handle -> name
        self.header: dict[str, str] = {}

    @classmethod
    def scan(cls, path: Path) -> DxfSide:
        side = cls()
        side.header = _header(path)
        raw: dict[int, dict] = {}
        section = None
        cur: dict | None = None
        blk = None
        in102 = False
        with open(path, encoding=dxf_encoding(side.header), errors='replace') as f:
            it = iter(f)
            for code in it:
                code = code.strip()
                try:
                    val = next(it).rstrip('\r\n')
                except StopIteration:
                    break
                if code == '0':
                    if cur is not None and cur.get('h') is not None and section in ('ENTITIES', 'BLOCKS'):
                        raw[cur['h']] = cur
                    cur = None
                    in102 = False
                    if val == 'SECTION':
                        section = 'pending'
                        blk = None
                    elif val == 'ENDSEC':
                        section = None
                    elif val == 'EOF':
                        break
                    elif section in ('ENTITIES', 'BLOCKS'):
                        cur = {'t': val, 'lay': '0', 'own': None, 'blk': blk, 'ps': False}
                    elif section == 'TABLES':
                        cur = {'t': val, 'tab': True}
                    continue
                if section == 'pending':
                    if code == '2':
                        section = val.strip()
                    continue
                if cur is None:
                    continue
                if code == '102':
                    in102 = val.startswith('{')
                    continue
                if cur.get('tab'):
                    if code == '5' and 'h' not in cur:
                        try:
                            cur['h'] = int(val, 16)
                        except ValueError:
                            pass
                    elif code == '2':
                        if cur['t'] == 'LAYER':
                            side.layers.add(_uplus(val))
                        elif cur['t'] == 'BLOCK_RECORD' and 'h' in cur:
                            side.brec[cur['h']] = _uplus(val)
                    continue
                if code == '5' and 'h' not in cur:
                    try:
                        cur['h'] = int(val, 16)
                    except ValueError:
                        pass
                elif code == '8':
                    cur['lay'] = _uplus(val)
                elif code == '330' and not in102 and cur['own'] is None:
                    try:
                        cur['own'] = int(val, 16)
                    except ValueError:
                        pass
                elif code == '67' and val.strip() == '1':
                    cur['ps'] = True
                elif code == '2' and cur['t'] == 'BLOCK':
                    blk = _uplus(val)
                    cur['blk'] = blk
        model = next((h for h, n in side.brec.items() if n.upper() == MODEL), None)
        for h, c in raw.items():
            if c['t'] in STRUCT:
                continue
            k = c
            own = None
            for _ in range(5):                              # VERTEX -> POLYLINE, ATTRIB -> INSERT -> block record
                if k['own'] in side.brec:
                    own = k['own']
                    break
                if k['own'] not in raw:
                    break
                k = raw[k['own']]
            if own is not None:
                name = side.brec[own]
            elif c['blk']:
                name = c['blk']
            elif c['own'] is None:                          # an R12-style entity with no owner code
                name = '*Paper_Space' if c['ps'] else '*Model_Space'
                own = None if c['ps'] else model
            else:
                name = '?'
            side.owner_h[h] = own
            side.ents[h] = (c['t'], c['lay'], anon(name))
        return side


# ============================================================================================================ compare
def compare(dwg: DwgSide, dxf: DxfSide, *, insert_limit: int = 200) -> dict:
    """Every difference class of U-6.3 and the verdict's inputs (lost inserts in drawing units)."""
    E1, E2 = dwg.ents, dxf.ents
    missing = [h for h in E1 if h not in E2]
    extra = [h for h in E2 if h not in E1]
    type_changed = [h for h in E1 if h in E2 and E1[h][0] != E2[h][0]]
    layer_changed = [h for h in E1 if h in E2 and E1[h][1] != E2[h][1]]
    owner_changed = [h for h in E1 if h in E2 and E1[h][2] != E2[h][2]]
    placed = dwg.reachable()
    missing_plan = [h for h in missing if dwg.owner_h.get(h) in placed]
    # layers the decode did not know ('?') written to layer 0, or empty layer names on ATTRIB / ATTDEF
    benign_layer = [h for h in layer_changed
                    if (E1[h][1] == '?' and E2[h][1] in ('0', '')) or (E2[h][1] == '' and E1[h][0] in ('ATTRIB', 'ATTDEF'))]
    benign_owner = [h for h in owner_changed if E1[h][2] == '?']
    lay1 = collections.Counter(la for _, la, _ in E1.values())
    lay2 = collections.Counter(la for _, la, _ in E2.values())
    by_layer = [{'layer': la, 'dwg': lay1.get(la, 0), 'dxf': lay2.get(la, 0)}
                for la in sorted(set(lay1) | set(lay2)) if lay1.get(la, 0) != lay2.get(la, 0)]
    # blocks whose definition came out empty or short
    n1 = collections.Counter(dwg.owner_h.get(h) for h in E1)
    n2 = collections.Counter(dxf.owner_h.get(h) for h in E2)
    miss_by_block: dict[int, list[int]] = collections.defaultdict(list)
    for h in missing:
        b = dwg.owner_h.get(h)
        if b is not None and b in dwg.blocks:
            miss_by_block[b].append(h)
    lost = []
    for b, hs in miss_by_block.items():
        name = dwg.blocks[b]
        if b == dwg.model or _is_paper(name) or n2.get(b, 0) >= n1.get(b, 0):
            continue
        dxf_name = dxf.brec.get(b)
        shown = dxf_name if (dxf_name and anon(dxf_name) == anon(name)) else name
        pl = dwg.placements(b, insert_limit) if b in placed else []
        lost.append({'name': shown, 'entities': len(hs), 'empty': n2.get(b, 0) == 0,
                     'byLayer': dict(sorted(collections.Counter(E1[h][1] for h in hs).items())),
                     'inserts': [{'x': x, 'y': y, 'layer': la} for x, y, la in pl]})
    lost.sort(key=lambda r: (-len(r['inserts']), -r['entities'], r['name']))
    renamed = []
    for h, dname in sorted(dwg.blocks.items()):
        xname = dxf.brec.get(h)
        if xname is not None and anon(xname) != anon(dname):
            renamed.append({'dwg': dname, 'dxf': xname})
    return {
        'missing': missing, 'extra': extra, 'typeChanged': type_changed, 'layerChanged': layer_changed,
        'ownerChanged': owner_changed, 'missingPlan': missing_plan, 'benignLayer': benign_layer,
        'benignOwner': benign_owner, 'byLayer': by_layer[:1000], 'lostBlocks': lost, 'renamedBlocks': renamed[:500],
        'emptyLayer': sum(1 for _, la, _ in E2.values() if la == ''),
    }


def _n(n: int, one: str, many: str | None = None) -> str:
    return f'{n:,} {one if n == 1 else (many or one + "s")}'


def verdict_and_notes(c: dict, msgs: list[dict], dwg_entities: int) -> tuple[str, list[str]]:
    """The verdict from the comparison only, and the plain sentences of the Files step (U-6.3)."""
    notes: list[str] = []
    missing, plan = len(c['missing']), len(c['missingPlan'])
    if plan:
        verdict = 'loss'
        notes.append(f'{missing:,} of {dwg_entities:,} drawing items did not come through the conversion; '
                     f'{plan:,} of them belong to the plan or to blocks placed in it.')
        lost = c['lostBlocks']
        placed = [b for b in lost if b['inserts']]
        if lost:
            names = ', '.join(b['name'] for b in placed[:6]) or ', '.join(b['name'] for b in lost[:6])
            more = '' if len(placed or lost) <= 6 else ' ...'
            notes.append(f'{_n(len(lost), "block")} came out empty or short; '
                         f'{_n(len(placed), "of them is", "of them are")} placed in the plan ({names}{more}).'
                         if placed else f'{_n(len(lost), "block")} came out empty or short ({names}{more}); none is '
                                         f'placed in the plan.')
        notes.append('Export a DXF from AutoCAD and upload it for a complete build.')
    else:
        changed = len(c['typeChanged']) + len(c['layerChanged']) + len(c['ownerChanged'])
        if missing or changed:
            verdict = 'minor'
            if missing:
                notes.append(f'{_n(missing, "item")} of blocks that are not placed in the plan, or of paper space, '
                             f'did not come through; the plan itself is complete.')
            parts = []
            if c['benignLayer']:
                parts.append(f'{_n(len(c["benignLayer"]), "item")} whose layer the converter could not read '
                             f'{"was" if len(c["benignLayer"]) == 1 else "were"} put on layer 0')
            other_layer = len(c['layerChanged']) - len(c['benignLayer'])
            if other_layer:
                parts.append(f'{_n(other_layer, "item")} changed layer')
            if c['ownerChanged']:
                parts.append(f'{_n(len(c["ownerChanged"]), "item")} changed block')
            if c['typeChanged']:
                parts.append(f'{_n(len(c["typeChanged"]), "item")} changed type')
            if parts:
                notes.append('Nothing in the plan is missing; ' + '; '.join(parts) + '.')
        else:
            verdict = 'ok'
    if verdict != 'loss':
        loud = [m for m in msgs if m['class'] not in QUIET]
        if loud:
            total = sum(m['count'] for m in loud)
            kinds = 'one kind' if len(loud) == 1 else f'{len(loud)} kinds'
            tail = 'nothing in the plan is missing' if missing else 'nothing is missing'
            notes.append(f'The converter reported {_n(total, "error")} of {kinds}; {tail}.')
    return verdict, notes


# ============================================================================================================= report
def report(*, source: dict, converter: dict | None, dxf: dict | None, convert: dict, msgs: list[dict],
           dwg: DwgSide, comparison: dict) -> dict:
    """A ConversionReport (upload-contracts.ts section 4); lost inserts in drawing units (see the module text)."""
    c = comparison
    verdict, notes = verdict_and_notes(c, msgs, len(dwg.ents))
    return {
        'format': 'conversion-report/1',
        'source': source,
        'converter': converter,
        'dxf': dxf,
        'seconds': round(float(convert.get('seconds') or 0.0), 2),
        'peakMemoryMB': None if convert.get('peak_mb') is None else round(float(convert['peak_mb']), 1),
        'exitCode': convert.get('exit_code'),
        'messages': msgs,
        'totals': {'dwgEntities': len(dwg.ents), 'dxfEntities': None, 'missing': len(c['missing']),
                   'extra': len(c['extra']), 'layerChanged': len(c['layerChanged']), 'emptyLayer': c['emptyLayer']},
        'byLayer': c['byLayer'],
        'lostBlocks': [{'name': b['name'], 'entities': b['entities'], 'byLayer': b['byLayer'], 'inserts': b['inserts']}
                       for b in c['lostBlocks']],
        'renamedBlocks': c['renamedBlocks'],
        'unknownObjects': dwg.unknown,
        'verdict': verdict,
        'notes': notes,
    }


#: metres per drawing unit (openings.UNITS / 1000: the reader's prims frame times the detector's scale, U-7.1)
UNIT_FACTOR = {'mm': 1.0, 'cm': 10.0, 'm': 1000.0, 'in': 25.4, 'ft': 304.8}


def publish(rep: dict, units: str) -> dict:
    """A copy of a cached report with the lost inserts in sheet metres (x / 1000 * the unit's factor, as the reader's
    frame and the detector's `scaled` compute it), rounded to the millimetre."""
    k = UNIT_FACTOR[units]
    out = json.loads(json.dumps(rep))
    for b in out.get('lostBlocks', []):
        for p in b['inserts']:
            p['x'] = round(p['x'] / 1000 * k, 3)
            p['y'] = round(p['y'] / 1000 * k, 3)
    return out


def not_converted(source: dict, drawing: dict | None, dxf_sha1: str, dxf_bytes: int) -> dict:
    """A DXF upload's report: verdict `not-converted`, its audit counts (from the read), no comparison (U-6.3)."""
    d = (drawing or {}).get('dxf') or {}
    return {
        'format': 'conversion-report/1', 'source': source, 'converter': None,
        'dxf': {'sha1': dxf_sha1, 'bytes': dxf_bytes, 'acadVersion': d.get('acadVersion'),
                'insUnits': d.get('insUnits'), 'auditErrors': int(d.get('auditErrors') or 0),
                'auditFixes': int(d.get('auditFixes') or 0)},
        'seconds': 0.0, 'peakMemoryMB': None, 'exitCode': None, 'messages': [],
        'totals': {'dwgEntities': None, 'dxfEntities': None, 'missing': 0, 'extra': 0, 'layerChanged': 0,
                   'emptyLayer': 0},
        'byLayer': [], 'lostBlocks': [], 'renamedBlocks': [], 'unknownObjects': 0, 'verdict': 'not-converted',
        'notes': ["Exported by the drawing's own program: no conversion to check."],
    }


def failed_report(source: dict, converter: dict | None, convert: dict, log_lines: list[str], note: str) -> dict:
    """The report of a conversion that failed (verdict `failed`), so the Files step can say why."""
    return {
        'format': 'conversion-report/1', 'source': source, 'converter': converter, 'dxf': None,
        'seconds': round(float(convert.get('seconds') or 0.0), 2),
        'peakMemoryMB': None if convert.get('peak_mb') is None else round(float(convert['peak_mb']), 1),
        'exitCode': convert.get('exit_code'), 'messages': messages(log_lines),
        'totals': {'dwgEntities': None, 'dxfEntities': None, 'missing': 0, 'extra': 0, 'layerChanged': 0,
                   'emptyLayer': 0},
        'byLayer': [], 'lostBlocks': [], 'renamedBlocks': [], 'unknownObjects': 0, 'verdict': 'failed',
        'notes': [note],
    }


# ============================================================================================================== check
class CheckError(RuntimeError):
    code = 'check_failed'


def dwgread_side(dwg: Path, libredwg: Path, stderr: Path | None = None) -> tuple[DwgSide, int, float]:
    """Runs `dwgread -O JSON <dwg>` (in the DWG's folder, by its bare name) with stdout piped into the scanner. Returns
    (side, exit code, seconds). It runs inside the check child's Job Object (memory and time capped there)."""
    exe = Path(libredwg) / ('dwgread.exe' if sys.platform == 'win32' else 'dwgread')
    t0 = time.perf_counter()
    err = open(stderr, 'wb') if stderr else subprocess.DEVNULL
    try:
        p = subprocess.Popen([str(exe), '-O', 'JSON', dwg.name], cwd=str(dwg.parent), stdin=subprocess.DEVNULL,
                             stdout=subprocess.PIPE, stderr=err,
                             creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        try:
            side = DwgSide.scan(io.TextIOWrapper(p.stdout, encoding='utf-8', errors='replace'))
        finally:
            code = p.wait()
    finally:
        if stderr:
            err.close()
    if side.objects == 0 or not side.blocks:
        raise CheckError(f'the drawing reader found nothing to compare (exit code {code})')
    return side, code, time.perf_counter() - t0


def check(dwg: Path, dxf: Path, convert_log: Path, *, libredwg: Path, source: dict, converter: dict | None,
          convert: dict, audit: dict, log: Callable[[str], None] = lambda s: None,
          dwgread_stderr: Path | None = None) -> dict:
    """-> ConversionReport (lost inserts in drawing units). `convert` = {seconds, peak_mb, exit_code} of dwg2dxf,
    `audit` = {acadVersion, insUnits, auditErrors, auditFixes} from ezdxf.recover, `source` = ConversionReport.source."""
    from .cache import sha1_file
    side, code, secs = dwgread_side(Path(dwg), Path(libredwg), dwgread_stderr)
    log(f'read the drawing as decoded: {len(side.ents):,} items in {secs:.1f} s')
    t0 = time.perf_counter()
    x = DxfSide.scan(Path(dxf))
    log(f'scanned the converted file: {len(x.ents):,} items in {time.perf_counter() - t0:.1f} s')
    c = compare(side, x)
    msgs = messages(read_log(Path(convert_log)))
    dxf_info = {'sha1': sha1_file(Path(dxf)), 'bytes': os.path.getsize(dxf),
                'acadVersion': audit.get('acadVersion') or x.header.get('$ACADVER'),
                'insUnits': audit.get('insUnits'), 'auditErrors': int(audit.get('auditErrors') or 0),
                'auditFixes': int(audit.get('auditFixes') or 0)}
    if dxf_info['insUnits'] is None and x.header.get('$INSUNITS', '').strip().lstrip('-').isdigit():
        dxf_info['insUnits'] = int(x.header['$INSUNITS'])
    rep = report(source=source, converter=converter, dxf=dxf_info, convert=convert, msgs=msgs, dwg=side, comparison=c)
    rep['totals']['dxfEntities'] = len(x.ents)
    log(f'conversion check: {rep["verdict"]}; {rep["totals"]["missing"]:,} missing, '
        f'{len(rep["lostBlocks"])} blocks lost')
    return rep
