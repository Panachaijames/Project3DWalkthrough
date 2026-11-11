"""Presentation v1 for an uploaded version, from facts and text runs (docs/upload/DESIGN.md U-11.2; D-8). No HTML anywhere:
every text is a plain run (`&`, `<` and Thai stay as they are; the viewer shows runs with textContent).

| field | value |
| documentTitle | the model's shortName |
| heading | the model's project (no "(test)", no "CAD -> 3D") |
| intro | one run: "Built from <n> drawing(s) (<file names>): walls from the wall layers, glass from the glass layers, and <d>
|         doors, <w> windows and <p> passages from the openings detector." + " <k> furniture boxes in <j> kinds." (when
|         furnished) + " Levels <levels> m." + " No AI used." |
| accent | #2f6f8f |
| legend | inline; for the part kinds present, in this order and these colours (D-5.4): Walls and lintels #e3ddd3, Glass
|          #9cc3d5, Glass frames #5d6b74, Railings #6f6a75, Stairs #b9c7b4, Single-line items #e0a458, Floor plates #d4d8d2 |
| floorButtons | none for one floor; {all: 'Both floors'} for two; 'All floors' for three or more (labels: the floors' names, the
|               viewer's default) |
| camera | fitSlabs, away [0.52 d, 0.53 d, 0.63 d] x s, targetY 2.5, panForPanel, far max(600, 6 d); d = the slabs'
|          bounding-box diagonal, at least 20 m; s = 1, 1.05, 1.1 ... the first for which every slab corner projects
|          inside the 1400 x 880 canvas, clear of the panel (the viewer's own camera maths, `camera_view`; with s = 1 the
|          rule fails on every model tried: contract issue U4-1) |
| creaseAngle, partStyles, toggles | the viewer's defaults (left out) |
| groundPlane | a plinth project: {size: [w + 20, d + 20] rounded up to 10 m, colour #dfe3e0}; else null |

BuiltModel v2 (docs/rooms/DESIGN.md R-11): the legend row "Stairs" covers `step`, `tread` and `landing`; ceilings get no
row (they are not seen in Orbit); the Ceilings tick keeps the viewer's own label, "Ceilings" (labels are left to the
viewer, as every tick's); the fitSlabs camera and the ground plane are measured on the slabs, so the new, larger plates
move them.
"""
from __future__ import annotations

import math
from typing import Any

ACCENT = '#2f6f8f'
GROUND_COLOUR = '#dfe3e0'
#: legend rows: (part kinds, colour, text), in this order (D-5.4); the v1 kinds outside the bank's join their kin
LEGEND = (
    (('wall', 'column', 'lintel', 'sill', 'parapet', 'low', 'builtin', 'post'), '#e3ddd3', 'Walls and lintels'),
    (('glass', 'pane', 'balustrade'), '#9cc3d5', 'Glass'),
    (('mullion',), '#5d6b74', 'Glass frames'),
    (('railing',), '#6f6a75', 'Railings'),
    (('step', 'tread', 'landing'), '#b9c7b4', 'Stairs'),           # v2: treads and landings are stairs (R-11)
    (('single',), '#e0a458', 'Single-line items'),
    (('slab', 'deck'), '#d4d8d2', 'Floor plates'),
)
MIN_DIAGONAL = 20.0


def _words(v: list[str]) -> str:
    return ', '.join(v[:-1]) + ' and ' + v[-1] if len(v) > 1 else ''.join(v)


def _count(n: int, word: str, plural: str | None = None) -> str:
    return f'{n:,} {word if n == 1 else (plural or word + "s")}'


def slab_bounds(model: dict) -> tuple[float, float, float, float] | None:
    """x0, y0, x1, y1 of every slab outline point (model m), or None without slabs (the viewer's fitSlabs rule)."""
    xs = [q[0] for p in model['parts'] if p['kind'] == 'slab' for q in p['o']]
    ys = [q[1] for p in model['parts'] if p['kind'] == 'slab' for q in p['o']]
    return (min(xs), min(ys), max(xs), max(ys)) if xs else None


def presentation(model: dict) -> dict[str, Any]:
    """The Presentation of an uploaded version, from its model alone (its source names, counts, levels, slabs)."""
    files = list(model['source'])
    ops = model['openings']
    n = {k: sum(1 for o in ops if o['kind'] == k) for k in ('door', 'window', 'passage')}
    text = (f"Built from {_count(len(files), 'drawing')} ({_words(files)}): walls from the wall layers, glass from the glass "
            f"layers, and {_count(n['door'], 'door')}, {_count(n['window'], 'window')} and {_count(n['passage'], 'passage')} "
            f"from the openings detector.")
    furniture, kinds = model.get('furniture') or [], model.get('furnitureKinds') or []
    if furniture:
        text += f" {_count(len(furniture), 'furniture box', 'furniture boxes')} in {_count(len(kinds), 'kind')}."
    text += f" Levels {' / '.join(format(f['level'], '+.2f') for f in model['floors'])} m."
    text += ' No AI used.'
    present = {p['kind'] for p in model['parts']}
    has_stair_lines = any((st or {}).get('below') or (st or {}).get('above') for st in (model.get('stairs') or {}).values())
    items = [{'colour': c, 'text': t} for kinds_, c, t in LEGEND
             if present & set(kinds_) or (t == 'Stairs' and has_stair_lines)]
    p: dict[str, Any] = {
        'documentTitle': model.get('shortName') or model['project'],
        'heading': model['project'],
        'intro': [{'text': text}],
        'accent': ACCENT,
        'legend': {'layout': 'inline', 'items': items},
    }
    nf = len(model['floors'])
    if nf == 2:
        p['floorButtons'] = {'all': 'Both floors'}
    elif nf > 2:
        p['floorButtons'] = {'all': 'All floors'}
    b = slab_bounds(model)
    d = max(MIN_DIAGONAL, math.hypot(b[2] - b[0], b[3] - b[1]) if b else 0.0)
    # U-11.2's away [0.52 d, 0.53 d, 0.63 d] puts some slab corners outside the canvas or under the panel at 1400 x 880
    # for every model tried (contract issue U4-1): the same direction is moved back, 5 % at a time, until the rule holds
    for step in range(61):
        s = 1.0 + 0.05 * step
        p['camera'] = {'kind': 'fitSlabs', 'away': [round(0.52 * d * s, 3), round(0.53 * d * s, 3), round(0.63 * d * s, 3)],
                       'targetY': 2.5, 'panForPanel': True, 'far': round(max(600.0, 6 * d), 3)}
        if camera_view(model, p, margin=CAMERA_MARGIN_PX)['inside']:
            break
    if any(q.get('plinth') for q in model['parts']) and b:
        w, dd = b[2] - b[0], b[3] - b[1]
        up = lambda v: float(math.ceil((v + 20.0) / 10.0) * 10)          # noqa: E731
        p['groundPlane'] = {'size': [up(w), up(dd)], 'colour': GROUND_COLOUR}
    else:
        p['groundPlane'] = None
    return p


# ------------------------------------------------------------------------------------------------- the camera rule check
VIEW_FOV_DEG = 40.0          # packages/viewer/src/core/context.ts: new PerspectiveCamera(40, ...)
PANEL_RIGHT_PX = 12 + 1 + 14 + 330 + 14 + 1      # ui/css.ts .wtv-panel: left 12, border 1, padding 14, width 330 (content-box)
CAMERA_MARGIN_PX = 8         # the start view keeps every slab corner this far inside the free part of the canvas


def camera_view(model: dict, pres: dict, width: int = 1400, height: int = 880, margin: float = 0.0) -> dict[str, Any]:
    """The viewer's fitSlabs start (core/context.ts applyCameraStart) for this model at width x height: the target, the
    camera position and the screen position of every slab corner (top and bottom of each slab), as the viewer computes
    them; `inside` = every corner lies inside the canvas, clear of the panel (x >= the panel's right edge), `margin`
    pixels in from those edges."""
    cam = pres['camera']
    b = slab_bounds(model)
    mx, my = (((b[0] + b[2]) / 2, (b[1] + b[3]) / 2) if b else (0.0, 0.0))
    away = cam['away']
    rl = math.hypot(away[2], away[0])
    right = (away[2] / rl, 0.0, -away[0] / rl)                    # the screen's right, on the ground
    alen = math.sqrt(sum(v * v for v in away))
    mpp = 2 * alen * math.tan(VIEW_FOV_DEG * math.pi / 360) / height
    panel = min(PANEL_RIGHT_PX, width / 2) if cam.get('panForPanel') else 0.0
    target = [mx + right[0] * (-panel / 2 * mpp), cam['targetY'], -my + right[2] * (-panel / 2 * mpp)]
    eye = [target[i] + away[i] for i in range(3)]
    # look-at basis (three.js: camera looks down -z, up +y)
    zc = [eye[i] - target[i] for i in range(3)]
    zl = math.sqrt(sum(v * v for v in zc))
    zc = [v / zl for v in zc]
    up = (0.0, 1.0, 0.0)
    xc = [up[1] * zc[2] - up[2] * zc[1], up[2] * zc[0] - up[0] * zc[2], up[0] * zc[1] - up[1] * zc[0]]
    xl = math.sqrt(sum(v * v for v in xc))
    xc = [v / xl for v in xc]
    yc = [zc[1] * xc[2] - zc[2] * xc[1], zc[2] * xc[0] - zc[0] * xc[2], zc[0] * xc[1] - zc[1] * xc[0]]
    f = 1 / math.tan(VIEW_FOV_DEG * math.pi / 360)
    aspect = width / height
    level = {fl['key']: fl['level'] for fl in model['floors']}
    pts = []
    for p in model['parts']:
        if p['kind'] != 'slab':
            continue
        for x, y in p['o']:
            for z in (p['z0'], p['z1']):
                w = (x, level[p['floor']] + z, -y)
                d = [w[i] - eye[i] for i in range(3)]
                cxv, cyv, czv = (sum(d[i] * xc[i] for i in range(3)), sum(d[i] * yc[i] for i in range(3)),
                                 sum(d[i] * zc[i] for i in range(3)))
                if czv >= 0:
                    pts.append((math.inf, math.inf))
                    continue
                ndc_x, ndc_y = (f / aspect) * cxv / -czv, f * cyv / -czv
                pts.append(((ndc_x + 1) / 2 * width, (1 - ndc_y) / 2 * height))
    inside = all(panel + margin <= sx <= width - margin and margin <= sy <= height - margin for sx, sy in pts)
    return {'target': target, 'eye': eye, 'panelRight': panel, 'corners': pts, 'inside': inside}
