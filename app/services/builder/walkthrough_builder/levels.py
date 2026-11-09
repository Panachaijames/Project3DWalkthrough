"""Level tags: the marks such as `+0.90` that staff pick floor levels from (docs/upload/DESIGN.md U-7.3, U-9.2).

A level tag is an ATTRIB tagged LEVEL, ELEV, EL, LV or FFL, or a text matching `LEVEL_RE` (copied verbatim from
docs/upload/reference/read_drawing.py: Python `re`, no flags; the sign class `[+\\-±]` is escaped, so it is the three
signs, not a range from '+' to '±' that would take digits and letters). Door and window tags never match (`W1.20`,
`D2.10`, `A1.00`, `R1.50`, `x0.900`).
* `value`: metres; a value above 100 is read as millimetres. A tagged ATTRIB whose text does not match `LEVEL_RE` gives
  the first number in its text; one with no number at all (a blank level mark: the house has two, on layer `0`) says
  no level and is left out, since LevelTag.value is a number (U2.md).
* `label`: the nearest other text within 3 m that is not itself a level tag and not blank (the house: `+0.90` beside
  "ระดับพื้นชั้นที่ 1"), else null.
Texts are untrusted: they are only matched and copied, never interpreted. Owner: U2.
"""
from __future__ import annotations

import collections
import math
import re

# verbatim from docs/upload/reference/read_drawing.py (U-7.3)
LEVEL_RE = re.compile(r'^\s*(?:(?:F\.?F\.?L|S\.?S\.?L|T\.?O\.?S|FL|EL|LEVEL|LVL|LV)\.?\s*[:=]?\s*)?([+\-±]?\s*\d{1,3}(?:[.,]\d{2,3}))\s*(?:M|m)?\s*$')
#: ATTRIB tags that make a level tag (U-7.3)
LEVEL_TAGS = ('LEVEL', 'ELEV', 'EL', 'LV', 'FFL')
#: the first signed number in a tagged ATTRIB's text that LEVEL_RE does not take
NUMBER_RE = re.compile(r'[+\-±]?\s*\d+(?:[.,]\d+)?')
#: a label lies within this many metres
LABEL_REACH = 3.0


def _number(raw: str) -> float | None:
    s = raw.replace(' ', '').replace('±', '').replace(',', '.')
    try:
        v = float(s)
    except ValueError:
        return None
    if not math.isfinite(v):
        return None
    if abs(v) > 100:                                   # millimetres
        v /= 1000
    return round(v, 4) + 0.0


def value_of(text: str, tag: str | None) -> float | None:
    """The level a text or a tagged ATTRIB says, in metres, or None when it is not a level tag."""
    m = LEVEL_RE.match(text or '')
    if m:
        return _number(m.group(1))
    if tag is not None and tag.strip().upper() in LEVEL_TAGS:
        n = NUMBER_RE.search(text or '')
        return _number(n.group(0)) if n else None
    return None


def level_tags(texts: list[dict]) -> list[dict]:
    """texts: [{layer, x, y, text, kind ('TEXT' | 'MTEXT' | 'ATTRIB'), tag}] in sheet metres -> LevelTag[], sorted by
    value, then position."""
    tags, others = [], []
    for t in texts:
        v = value_of(t.get('text') or '', t.get('tag') if t.get('kind') == 'ATTRIB' else None)
        if v is not None:
            tags.append((t, v))
        elif (t.get('text') or '').strip() and math.isfinite(t['x']) and math.isfinite(t['y']):
            others.append(t)
    # labels: the nearest other text within LABEL_REACH, through a grid of LABEL_REACH cells
    grid: dict[tuple[int, int], list[dict]] = collections.defaultdict(list)
    for o in others:
        grid[(math.floor(o['x'] / LABEL_REACH), math.floor(o['y'] / LABEL_REACH))].append(o)
    out = []
    for t, v in tags:
        best, best_d = None, None
        if math.isfinite(t['x']) and math.isfinite(t['y']):
            gx, gy = math.floor(t['x'] / LABEL_REACH), math.floor(t['y'] / LABEL_REACH)
            for i in (-1, 0, 1):
                for j in (-1, 0, 1):
                    for o in grid.get((gx + i, gy + j), ()):
                        d = math.dist((o['x'], o['y']), (t['x'], t['y']))
                        if d <= LABEL_REACH and (best_d is None or d < best_d
                                                 or (d == best_d and (o['text'], o['x'], o['y']) < (best['text'], best['x'], best['y']))):
                            best, best_d = o, d
        out.append({'x': t['x'], 'y': t['y'], 'value': v, 'text': (t.get('text') or '').strip(), 'layer': t['layer'],
                    'source': 'attrib' if t.get('kind') == 'ATTRIB' else 'text',
                    'label': best['text'].strip() if best is not None else None})
    out.sort(key=lambda r: (r['value'], r['x'], r['y'], r['layer'], r['text']))
    return out
