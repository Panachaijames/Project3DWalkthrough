"""Names from drawings: layer names normalised for the office memory, block families, Revit element ids
(docs/upload/DESIGN.md U-7.2, U-7.3, U-8.4). Pure functions; every name is untrusted text and is only ever compared,
never interpreted. Scaffold U0; frozen after it.
"""
from __future__ import annotations

import re
from collections.abc import Sequence

#: The xref binding separator: AutoCAD binds `XREF$0$NAME`; the part up to the last one is the xref's name.
XREF_SEP = '$0$'
#: The bank builder's family() pattern (bank_test/src/build_model.py): '<family> - <type>-<element id or V#>-<view>'.
REVIT_SUFFIX = re.compile(r'^(.*?)-(\d{5,}|V\d+)-')
#: A Revit element id inside a block name: a run of 5+ digits between hyphens (U-7.2). Overlapping runs are all found
#: (a look-ahead), so the last one wins.
ELEMENT_ID = re.compile(r'(?=-(\d{5,})-)')
_SPACES = re.compile(r'\s+')


def strip_xref(name: str) -> str:
    """The name without an xref prefix (everything up to the last `$0$`)."""
    i = name.rfind(XREF_SEP)
    return name[i + len(XREF_SEP):] if i >= 0 else name


def normalise_layer(name: str) -> str:
    """U-8.4: upper case, xref prefix up to the last `$0$` removed, runs of whitespace as one space, trimmed.
    'Xr_SDC_DD_ID-PRS-ID wall$0$DA-DOOR-WIND' -> 'DA-DOOR-WIND'."""
    return _SPACES.sub(' ', strip_xref(name)).strip().upper()


def family(name: str) -> str:
    """A block's family (U-7.3): the name without an xref prefix (up to the last `$0$`) and without a Revit
    `-<5+ digits or V#>-<view>` suffix, by the bank builder's own rule (`^(.*?)-(\\d{5,}|V\\d+)-`, then stripped).
    'XR_L44$0$SINK-720-400' -> 'SINK-720-400'; 'Chair - Mollie-345678-Level 1' -> 'Chair - Mollie'."""
    base = strip_xref(name)
    m = REVIT_SUFFIX.match(base)
    return (m.group(1) if m else base).strip()


def element_id_of(name: str) -> str | None:
    """The last `-(\\d{5,})-` run of one block name, or None."""
    runs = ELEMENT_ID.findall(name)
    return runs[-1] if runs else None


def split_path(path: str | Sequence[str]) -> list[str]:
    """A prims item's `path` ('A>B>C', '' at top level) or a list of block names -> the list of names."""
    if isinstance(path, str):
        return [p for p in path.split('>') if p] if path else []
    return [p for p in path if p]


def element_id(path: str | Sequence[str]) -> str | None:
    """U-7.2: the element id of an item = the last `-(\\d{5,})-` run of the INNERMOST block name in its path that has one
    (it names a whole family instance: every line of one door block shares it, so it is never matched alone, U-10.6).
    `path` is the item's block path from the top-level INSERT down (prims' 'A>B>C', or a list). For an INSERT item, pass
    its path plus its own name, so that an element's own INSERT carries its id."""
    for name in reversed(split_path(path)):
        eid = element_id_of(name)
        if eid is not None:
            return eid
    return None


def element_depth(path: str | Sequence[str]) -> int | None:
    """The index (0 = outermost) of the innermost block name in the path that carries an element id, or None. The
    INSERT of that element is the one whose rsig frame keys.rsig uses (U-7.2)."""
    names = split_path(path)
    for i in range(len(names) - 1, -1, -1):
        if element_id_of(names[i]) is not None:
            return i
    return None
