"""topview.png from the model alone (docs/upload/DESIGN.md U-11.4).

The bank builder's top view (`bank_test/src/build_model.py` lines 1407-1455) drawn from `model.json` only: parts by kind
(the bank's styles and order; the v1 kinds the bank never had get styles of their own, drawn in the same pass, so the
bank's picture cannot move), stair lines, voids, openings with their numbers, room names and a title per floor;
matplotlib Agg, one panel per floor. The prototype crashed on one floor (`plt.subplots(1, 1)` gives a single Axes): the
axes come as a row here (`squeeze=False`), which draws the same picture. For the bank's v2 model the bytes equal
`bank_test/src/bank_topview.png` (sha1 f084b556503c, the pinned matplotlib 3.11.2 and its fonts). The furniture picture
is not made (no use in the app). Drawing text (room labels, floor names) is put on the picture as text: `$` is escaped,
so matplotlib never reads it as mathtext.
"""
from __future__ import annotations

import io
from typing import Any

STY: dict[str, dict[str, Any]] = {
    'slab': dict(facecolor='#eef0ec', edgecolor='#999', lw=0.8), 'wall': dict(facecolor='#8c7b6a', edgecolor='none'),
    'column': dict(facecolor='#5d5045', edgecolor='none'), 'lintel': dict(facecolor='#d8a25e', edgecolor='none'),
    'sill': dict(facecolor='#b8a68a', edgecolor='none'), 'glass': dict(facecolor='#3f9fd0', edgecolor='#1f6f9f', lw=0.6),
    'railing': dict(facecolor='#b04ab8', edgecolor='none'), 'single': dict(facecolor='#e0a458', edgecolor='none'),
    'parapet': dict(facecolor='#c9a0d0', edgecolor='#8a4a96', lw=0.6), 'mullion': dict(facecolor='#2c5a74', edgecolor='none'),
    'step': dict(facecolor='#7cc48a', edgecolor='#2e8b47', lw=0.5),
    # BuiltModel v1 kinds outside the bank's (D-5.4 colours, darkened like the bank's for a plan)
    'deck': dict(facecolor='#d9c3a5', edgecolor='#8a6a44', lw=0.5), 'balustrade': dict(facecolor='#3f9fd0', edgecolor='#1f6f9f', lw=0.6),
    'low': dict(facecolor='#b3a58f', edgecolor='none'), 'builtin': dict(facecolor='#a8865e', edgecolor='none'),
    'post': dict(facecolor='#4a4038', edgecolor='none'), 'pane': dict(facecolor='#6fb6e0', edgecolor='#1f6f9f', lw=0.6),
}
#: the bank's drawing order, with the extra kinds slotted in where they belong (the bank has none of them)
ORDER = ('slab', 'deck', 'step', 'single', 'railing', 'balustrade', 'parapet', 'low', 'wall', 'builtin', 'column', 'post',
         'glass', 'pane', 'mullion', 'sill', 'lintel')
TITLE_TAIL = ('walls brown, lintels tan, glass blue (glass partitions bold cyan), '
              'railings purple, parapet lilac, closures red,\nstairs green (steps filled); opening numbers: doors red, windows blue, '
              'passages green; "open" = no floor (stair, lift shaft)')
OPENING_COLOUR = {'door': '#c0392b', 'window': '#1f6fb2', 'passage': '#2e8b47'}


def _text(s: str) -> str:
    """Drawing text as matplotlib text, never mathtext."""
    return str(s).replace('$', r'\$')


def topview_png(model: dict) -> bytes:
    """The top view of `model` as PNG bytes."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import PathPatch
    from matplotlib.path import Path as MPath

    floors = model['floors']
    parts = model['parts']
    cx, cy = model['offset']
    stairs = model.get('stairs') or {}
    voids = model.get('voids') or {}
    fig, axs = plt.subplots(1, len(floors), figsize=(11 * len(floors), 17), dpi=90, squeeze=False)
    try:
        for ax, F in zip(axs[0], floors):
            k = F['key']
            for kind in ORDER:
                for p in parts:
                    if p['floor'] != k or p['kind'] != kind:
                        continue
                    verts, codes = [], []
                    for loop in [p['o']] + p['h']:
                        verts += [(x + cx, y + cy) for x, y in loop] + [(loop[0][0] + cx, loop[0][1] + cy)]
                        codes += [MPath.MOVETO] + [MPath.LINETO] * (len(loop) - 1) + [MPath.CLOSEPOLY]
                    sty = dict(STY[kind])
                    if kind == 'glass' and p.get('label') and not p['label'].endswith((' pane', ' transom')):
                        sty.update(facecolor='#00b5e2', edgecolor='#00b5e2', lw=1.6)      # glass partitions: drawn bold (10 mm)
                    if kind == 'wall' and (p.get('label') or '').startswith('closure'):
                        sty.update(facecolor='#d0442c')
                    ax.add_patch(PathPatch(MPath(verts, codes), **sty))
            st = stairs.get(k) or {}
            for arr, col, lw in ((st.get('below') or [], '#2e8b47', 0.8), (st.get('above') or [], '#a8d8b0', 0.6)):
                for i in range(0, len(arr), 4):
                    ax.plot([arr[i] + cx, arr[i + 2] + cx], [arr[i + 1] + cy, arr[i + 3] + cy], color=col, lw=lw)
            for v in voids.get(k) or []:
                ax.text(v['x'] + cx, v['y'] + cy, _text(f"open: {v['what']}"), fontsize=7, color='#666', ha='center', style='italic')
            for o in model['openings']:
                if o['floor'] != k:
                    continue
                col = OPENING_COLOUR[o['kind']]
                ux, uy = o['ny'], -o['nx']
                h = o['width'] / 2
                if o['kind'] == 'passage':
                    ax.plot([o['x'] - ux * h + cx, o['x'] + ux * h + cx], [o['y'] - uy * h + cy, o['y'] + uy * h + cy], color=col,
                            lw=1.6, ls='--')
                ax.text(o['x'] + cx + o['nx'] * 0.22, o['y'] + cy + o['ny'] * 0.22, _text(o['id'].split('-')[-1]), fontsize=6.5,
                        color=col, ha='center', va='center')
            for r in model['rooms']:
                if r['floor'] == k:
                    ax.text(r['x'] + cx, r['y'] + cy, _text(r.get('label') or r.get('name') or ''), fontsize=8, color='#1f4e79',
                            ha='center')
            ax.set_title(f"{_text(F['name'])} ({F['level']:+.2f} m): " + TITLE_TAIL, fontsize=9)
            ax.autoscale()
            ax.set_aspect('equal')
            ax.axis('off')
        plt.tight_layout()
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
    finally:
        plt.close(fig)
    return buf.getvalue()
