"""JavaScript's number formatting in Python, for texts the prototype pages computed in the browser (DESIGN.md 7.4): the
house page's caption functions are rendered once by the seed and must equal what the page showed, character for
character; and the caption placeholders of DESIGN.md 7.3, filled as the viewer fills them (for the oracle tests).

    js_round(x)        Math.round: the nearest integer, a tie towards +infinity (exact, also for 0.49999999999999994)
    js_to_fixed(x, d)  Number.prototype.toFixed: the exact decimal value of the double, a tie away from zero, no '-0.00'
    js_locale(n)       Math.round(n).toLocaleString('en-US'): thousands with commas
    js_pct(x)          Math.round(x * 100) + '%'
    js_str(x)          String(x) for the integers and plain decimals a template literal prints
    fill_caption       /\\{(\\w+?)(level|height)(\\+)?\\}/g -> the setting toFixed(2), '+' in front for {<key>level+} when >= 0
"""
from __future__ import annotations

import math
import re
from collections.abc import Mapping
from decimal import ROUND_HALF_UP, Decimal
from typing import Any


def js_round(x: float) -> int:
    f = math.floor(x)
    return int(f + 1 if x - f >= 0.5 else f)


def js_to_fixed(x: float, digits: int) -> str:
    if not math.isfinite(x):
        return 'NaN' if math.isnan(x) else ('Infinity' if x > 0 else '-Infinity')
    if abs(x) >= 1e21:
        return js_str(x)
    if x == 0:
        x = 0.0                                         # (-0).toFixed(2) is '0.00'
    q = Decimal(x).quantize(Decimal(1).scaleb(-digits), rounding=ROUND_HALF_UP)
    return format(q, 'f')


def js_str(x: Any) -> str:
    if isinstance(x, bool):
        return 'true' if x else 'false'
    if isinstance(x, int):
        return str(x)
    if isinstance(x, float):
        if x.is_integer() and abs(x) < 1e21:
            return str(int(x))
        r = repr(x)
        if 'e' in r or 'E' in r:
            raise ValueError(f'js_str: {x!r} would need JavaScript exponent formatting')
        return r
    return str(x)


def js_locale(n: float) -> str:
    return format(js_round(n), ',')


def js_pct(x: float) -> str:
    return f'{js_round(x * 100)}%'


# JavaScript's \w is ASCII only: [A-Za-z0-9_]
CAPTION_PLACEHOLDER = re.compile(r'\{([A-Za-z0-9_]+?)(level|height)(\+)?\}')


def fill_caption(template: str, settings: Mapping[str, Mapping[str, float]]) -> str:
    """DESIGN.md 7.3: {<key>level} and {<key>height} -> toFixed(2); {<key>level+} signed when >= 0; unknown key kept."""
    def rep(m: re.Match[str]) -> str:
        key, prop, plus = m.group(1), m.group(2), m.group(3)
        s = settings.get(key)
        if not s:
            return m.group(0)
        v = s[prop]
        return ('+' if plus and v >= 0 else '') + js_to_fixed(v, 2)
    return CAPTION_PLACEHOLDER.sub(rep, template)


def model_settings(model: Mapping[str, Any]) -> dict[str, dict[str, float]]:
    """The Build settings a model starts with: each floor's level and wall height."""
    return {f['key']: {'level': f['level'], 'height': f['wallHeight']} for f in model['floors']}
