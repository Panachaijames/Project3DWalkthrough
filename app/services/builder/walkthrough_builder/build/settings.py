"""BuildSettings -> the numbers the builder computes with (docs/upload/DESIGN.md U-10.4).

`float()` on every metre value read from the settings (levels, wall heights, slab thickness, the defaults, door and
window heights, offsets, pads, boxes, fix points) and `int()` on the mm furniture heights and bases, before any
arithmetic: the browser sends `0` for a typed `0.00` (JSON.stringify(0) is "0"), the bank's model bytes carry `0.0`,
`3.7` and `1.0`, and the prototype's R3 keeps an int an int, so without this the golden breaks. Missing optional parts
take the bank's defaults (U-10.4). The settings given are never changed: a coerced deep copy is returned.
"""
from __future__ import annotations

import copy

from .errors import BuildError

DEFAULTS = {'doorHead': 2.1, 'windowSill': 0.9, 'windowHead': 2.1, 'railingHeight': 1.1, 'slabThickness': 0.25,
            'singleLineHeight': 1.0}
FURNITURE = {'heights': {}, 'bases': {}, 'words': {}, 'skip': [], 'minSize': 0.08, 'minDepth': None, 'looseLayers': [],
             'pieceLayer': 'insert'}
OPTIONS = {'revitWallTypes': 'auto', 'parapets': 'auto', 'objectClosures': True, 'liftShafts': True, 'plinth': 'auto',
           'outlineWalls': 'off', 'offset': 'auto'}


def _f(v, what):
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise BuildError('bad_settings', f'{what} is not a number: {v!r}')
    return float(v)


def _opt_f(v, what):
    return None if v is None else _f(v, what)


def _vec(v, what):
    if not isinstance(v, (list, tuple)) or len(v) != 2:
        raise BuildError('bad_settings', f'{what} is not a point [x, y]')
    return [_f(v[0], what), _f(v[1], what)]


def coerce(settings: dict) -> dict:
    s = copy.deepcopy(settings)
    if not isinstance(s, dict):
        raise BuildError('bad_settings', 'the build settings are not an object')
    s['defaults'] = {k: _f({**DEFAULTS, **(s.get('defaults') or {})}[k], f'defaults.{k}') for k in DEFAULTS}
    fu = {**FURNITURE, **(s.get('furniture') or {})}
    for what in ('heights', 'bases'):
        out = {}
        for kind, v in (fu.get(what) or {}).items():
            if str(kind).startswith('_'):
                continue
            if isinstance(v, bool) or not isinstance(v, (int, float)):
                raise BuildError('bad_settings', f'furniture.{what}.{kind} is not a number of mm: {v!r}')
            out[kind] = int(v)
        fu[what] = out
    fu['minSize'] = _f(fu['minSize'], 'furniture.minSize')
    fu['minDepth'] = _opt_f(fu.get('minDepth'), 'furniture.minDepth')
    fu['words'] = {k: list(v) for k, v in (fu.get('words') or {}).items() if not str(k).startswith('_')}
    fu['skip'] = list(fu.get('skip') or [])
    fu['looseLayers'] = list(fu.get('looseLayers') or [])
    s['furniture'] = fu
    op = {**OPTIONS, **(s.get('options') or {})}
    if op['offset'] != 'auto':
        op['offset'] = _vec(op['offset'], 'options.offset')
    s['options'] = op
    s['vocabulary'] = dict(s.get('vocabulary') or {})
    floors = s.get('floors') or []
    for i, f in enumerate(floors):
        w = f'floors[{i}]'
        f['level'] = _f(f.get('level'), f'{w}.level')
        f['wallHeight'] = _f(f.get('wallHeight'), f'{w}.wallHeight')
        for k in ('slabThickness', 'doorHead', 'windowSill', 'windowHead'):
            f[k] = _opt_f(f.get(k), f'{w}.{k}')
        a = f.get('area') or {'kind': 'wholeFile'}
        if a.get('kind') == 'box':
            a = {'kind': 'box', 'bbox': [_f(v, f'{w}.area.bbox') for v in a['bbox']], 'pad': _f(a.get('pad', 0.0), f'{w}.area.pad'),
                 'match': a.get('match', 'all')}
        else:
            a = {'kind': 'wholeFile'}
        f['area'] = a
        al = f.get('align') or {'method': 'auto'}
        if al.get('method') == 'points':
            al = {'method': 'points', 'pairs': [[_vec(p, f'{w}.align.pairs'), _vec(q, f'{w}.align.pairs')] for p, q in al['pairs']]}
        f['align'] = al
    s['floors'] = floors
    fx = s.get('fixes') or {}
    for o in fx.get('openings') or []:
        o['a'], o['b'] = _vec(o['a'], 'fixes.openings.a'), _vec(o['b'], 'fixes.openings.b')
        o['head'], o['sill'] = _opt_f(o.get('head'), 'fixes.openings.head'), _opt_f(o.get('sill'), 'fixes.openings.sill')
    for o in fx.get('outlineEdges') or []:
        o['a'], o['b'] = _vec(o['a'], 'fixes.outlineEdges.a'), _vec(o['b'], 'fixes.outlineEdges.b')
    s['fixes'] = {'setAside': list(fx.get('setAside') or []), 'openings': list(fx.get('openings') or []),
                  'outlineEdges': list(fx.get('outlineEdges') or [])}
    return s


def check(s: dict, source_shas: set[str]) -> None:
    """What the builder needs to go on at all (the API checks the rest, settings_issues): floors, their sources, levels
    lowest first and strictly increasing, positive wall heights, unique keys."""
    floors = s['floors']
    if not floors:
        raise BuildError('no_floors', 'the settings have no floors: add one on the Floors step')
    seen = set()
    for i, f in enumerate(floors):
        if f['key'] in seen:
            raise BuildError('bad_settings', f'two floors have the key {f["key"]!r}')
        seen.add(f['key'])
        if f['source'] not in source_shas:
            raise BuildError('bad_settings', f'{f["name"]} has no drawing: pick its source on the Floors step')
        if f['wallHeight'] <= 0:
            raise BuildError('bad_settings', f'{f["name"]} has no wall height')
        if i and f['level'] <= floors[i - 1]['level']:
            raise BuildError('bad_settings', f'the floors must be listed lowest first with rising levels '
                             f'({floors[i - 1]["name"]} {floors[i - 1]["level"]:+.2f} m, {f["name"]} {f["level"]:+.2f} m)')
