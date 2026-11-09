"""The furniture list CSV (DESIGN.md 18.8): a port of furniture/furniture_kit.py csv_text, the same bytes, with the
saved heights applied.

The family list exactly as furniture/README.md describes it: the 18 columns, CRLF after every row (the last too), sorted by
floor (the model's order), kind (the kinds table's order), id. x_m, y_m are drawing coordinates (model x, y + offset,
3 decimals); sizes, heights and bases are whole mm rounded half up (floor(v + 0.5), JavaScript's Math.round); base_mm is
the resolved underside (a piece on a table stands at the table's top: the support's base + its height, one level, as the
kit); rotation_deg has 1 decimal; RFC 4180 quoting; never '-0.000'. `csv_text` has no byte-order mark: the download
(`csv_bytes`) puts EF BB BF in front, as furniture_kit.write_csv does.

The formula guard (docs/upload/DESIGN.md U-11.6, step U5; uploads bring other offices' block names): in the text
columns (id, level, kind, kind_label, family, block, layer, dxf_handle, on_top_of, note) a value starting with `=`, `+`,
`-`, `@`, TAB or CR gets a leading `'` before the RFC 4180 quoting, so a spreadsheet never reads it as a formula; the
number columns never change. The viewer's CSV (packages/viewer/src/furniture/logic.ts) applies the same rule. No text
field of the four seeded projects starts that way: their CSVs are byte for byte as before.
"""
from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

BOM = b'\xef\xbb\xbf'
CSV_COLUMNS = ('id', 'level', 'kind', 'kind_label', 'family', 'block', 'layer', 'dxf_handle', 'x_m', 'y_m', 'width_mm',
               'depth_mm', 'height_mm', 'base_mm', 'rotation_deg', 'on_top_of', 'merged', 'note')
TEXT_COLUMNS = frozenset({'id', 'level', 'kind', 'kind_label', 'family', 'block', 'layer', 'dxf_handle', 'on_top_of',
                          'note'})
_TEXT_AT = tuple(c in TEXT_COLUMNS for c in CSV_COLUMNS)
FORMULA_START = ('=', '+', '-', '@', '\t', '\r')


def guard(v: Any) -> str:
    """A text value a spreadsheet would take for a formula gets a leading ' (U-11.6)."""
    s = str(v)
    return "'" + s if s.startswith(FORMULA_START) else s


def field(v: Any) -> str:
    """RFC 4180: a field with a comma, a double quote, CR or LF goes in double quotes, inner quotes doubled."""
    s = str(v)
    return '"' + s.replace('"', '""') + '"' if any(ch in s for ch in ',"\r\n') else s


def fixed(v: float, nd: int) -> str:
    """Fixed notation (Python f'{v:.nf}'), never '-0.000'."""
    s = f'{v:.{nd}f}'
    return s[1:] if s.startswith('-') and not s.strip('-0.') else s


def whole(v: float) -> int:
    """Whole mm, half up (JavaScript Math.round): 62.5 -> 63, 460.5 -> 461."""
    return int(math.floor(v + 0.5))


def csv_text(furniture: list[dict[str, Any]], kinds: list[dict[str, Any]], floors: list[Any], offset: list[float],
             heights: Mapping[str, float] | None = None) -> str:
    """furniture_kit.csv_text, line for line: `heights` = {kind: mm} replaces the kinds' heights (the saved heights)."""
    floor_keys = [f['key'] if isinstance(f, dict) else f for f in floors]
    by = {k['key']: k for k in kinds}
    order = {k['key']: i for i, k in enumerate(kinds)}
    height = lambda kind: whole((heights or {}).get(kind, by[kind]['height']))   # noqa: E731
    ids = {p['id']: p for p in furniture}
    lines = [','.join(CSV_COLUMNS)]
    for p in sorted(furniture, key=lambda p: (floor_keys.index(p['floor']), order[p['kind']], p['id'])):
        k = by[p['kind']]
        base = by[ids[p['on']]['kind']]['base'] + height(ids[p['on']]['kind']) if p['on'] else k['base']
        row = [p['id'], p['floor'], p['kind'], k['label'], p['family'], p['block'], p['layer'], p['handle'],
               fixed(p['x'] + offset[0], 3), fixed(p['y'] + offset[1], 3), whole(p['w'] * 1000), whole(p['d'] * 1000),
               height(p['kind']), whole(base), fixed(p['rot'], 1), p['on'] or '', p['n'], p['note'] or '']
        lines.append(','.join(field(guard(v) if text else v) for v, text in zip(row, _TEXT_AT, strict=True)))
    return '\r\n'.join(lines) + '\r\n'


def model_csv_text(model: Mapping[str, Any], heights: Mapping[str, float] | None = None) -> str:
    """The list of a BuiltModel v1 (no BOM). A model without furniture has none: ValueError."""
    if not model.get('furniture'):
        raise ValueError('the model has no furniture')
    return csv_text(model['furniture'], model['furnitureKinds'], model['floors'], model.get('offset', [0, 0]), heights)


def csv_bytes(model: Mapping[str, Any], heights: Mapping[str, float] | None = None) -> bytes:
    """The download: BOM + the list as UTF-8 (CRLF kept)."""
    return BOM + model_csv_text(model, heights).encode('utf-8')


def file_name(model: Mapping[str, Any]) -> str:
    """`<photoName>_furniture_list.csv` (DESIGN.md 13)."""
    return f'{model["photoName"]}_furniture_list.csv'
