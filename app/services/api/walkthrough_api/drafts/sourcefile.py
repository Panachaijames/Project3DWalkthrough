"""What an uploaded file is, from its first bytes (docs/upload/DESIGN.md U-5.1).

* A DWG starts `AC10` + 2 digits and must be AC1012 (R13) or newer: `AC1001` - `AC1011` and the pre-R10 prefixes `AC1.`
  and `AC2.` (`AC1.40`, `AC1.50`, `AC2.10` ...) get 422 unsupported_version ("save it as a newer DWG, or export a DXF").
* An ASCII DXF starts, after optional whitespace (and a UTF-8 byte-order mark) and `999` comments, with group code `0`
  and `SECTION`; a binary DXF with `AutoCAD Binary DXF\\r\\n\\x1a\\x00`.
* Anything else is 422 bad_kind, and so is a file whose contents disagree with its name's extension (a DXF named .dwg):
  the converter is chosen by the kind, and staff see the name.

formatVersion: a DWG's first six bytes (AC1032 ...); a DXF's $ACADVER when it is found near the start, else null.
"""
from __future__ import annotations

import re

from ..errors import ApiError

HEAD_BYTES = 256 * 1024
BINARY_DXF = b'AutoCAD Binary DXF\r\n\x1a\x00'
_DWG = re.compile(rb'AC10([0-9]{2})')
_ACADVER_ASCII = re.compile(rb'\$ACADVER[ \t]*\r?\n[ \t]*1[ \t]*\r?\n[ \t]*(AC[0-9]{4})')
_ACADVER_VALUE = re.compile(r'AC[0-9]{4}')
UNSUPPORTED = 'save it as a newer DWG (R13 or later), or export a DXF'


def extension(file_name: str) -> str | None:
    low = file_name.lower()
    return 'dwg' if low.endswith('.dwg') else 'dxf' if low.endswith('.dxf') else None


def _ascii_dxf(head: bytes) -> bool:
    text = head.decode('latin-1')
    if text.startswith('\xef\xbb\xbf'):
        text = text[3:]
    lines = text.lstrip().splitlines()
    i = 0
    while i + 1 < len(lines):
        code, value = lines[i].strip(), lines[i + 1].strip()
        if code == '999':
            i += 2
            continue
        return code == '0' and value == 'SECTION'
    return False


def _binary_acadver(head: bytes) -> str | None:
    i = head.find(b'$ACADVER\x00')
    if i < 0:
        return None
    rest = head[i + 9:]
    for skip in (b'\x01\x00', b'\x01'):                      # R14+ two-byte group codes, older one-byte
        if rest.startswith(skip):
            end = rest.find(b'\x00', len(skip))
            value = rest[len(skip):end].decode('ascii', 'replace') if end > 0 else ''
            if _ACADVER_VALUE.fullmatch(value):
                return value
    return None


def sniff(head: bytes, file_name: str) -> tuple[str, str | None]:
    """(kind 'dwg' | 'dxf', formatVersion) of a file from its first bytes (at least the first 256 KiB, or all of it);
    ApiError 422 bad_kind / unsupported_version otherwise."""
    ext = extension(file_name)
    if not head:
        raise ApiError(422, 'bad_kind', f'{file_name} is empty: it is not a drawing')
    kind: str | None = None
    version: str | None = None
    if head.startswith((b'AC1.', b'AC2.')):
        raise ApiError(422, 'unsupported_version', f'{file_name} is a DWG from before AutoCAD R10 '
                                                   f'({head[:6].decode("ascii", "replace")}): {UNSUPPORTED}')
    m = _DWG.match(head)
    if m:
        if int(m.group(1)) < 12:
            raise ApiError(422, 'unsupported_version', f'{file_name} is a DWG older than AutoCAD R13 '
                                                       f'({head[:6].decode("ascii")}): {UNSUPPORTED}')
        kind, version = 'dwg', head[:6].decode('ascii')
    elif head.startswith(BINARY_DXF):
        kind, version = 'dxf', _binary_acadver(head)
    elif _ascii_dxf(head):
        found = _ACADVER_ASCII.search(head)
        kind, version = 'dxf', found.group(1).decode('ascii') if found else None
    if kind is None:
        what = 'a DWG drawing' if ext == 'dwg' else 'a DXF file' if ext == 'dxf' else 'a DWG or DXF drawing'
        raise ApiError(422, 'bad_kind', f'{file_name} is not {what}: its first bytes are not a drawing\'s header')
    if ext is not None and ext != kind:
        raise ApiError(422, 'bad_kind', f'{file_name} holds a {kind.upper()} drawing but its name ends in .{ext}: '
                                        f'rename it to .{kind} and upload it again')
    return kind, version
