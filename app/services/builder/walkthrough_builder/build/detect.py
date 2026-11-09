"""The detector wrapper (docs/upload/DESIGN.md U-10.7).

Per floor: the floor's items (the per-item reading, after set-aside) scaled to metres with `openings.scaled`, deduped with
`geomkit.dedupe`; `geomkit.role_matcher` of the DERIVED detector roles (roles.detector_layers: `other` and
`room-outline` layers are read as context, `ignore` and the non-detector roles dropped); `openings.Floor(
'<projectId>:<key>', items, layer_linetypes, roles, 1.0)`, `openings.detect_floor`, `openings.finish` -> records with
ids `<key>-NNN`, in drawing metres before any alignment shift (as the bank builder reads them). Both stdout and stderr
of the detector are captured into the run log; `slow` comes from `fl.T['total'] > openings.SLOW_FLOOR`; the
FRAME_ROWS_MAX warning (a whole detection rule skipped) is recognised by its fixed wording and recorded as
`frameRowsSkipped`. The swings that went to no opening are kept for the check screen.
"""
from __future__ import annotations

import contextlib
import io
import re
import time
from collections.abc import Callable, Mapping
from pathlib import Path

from .. import roles as R
from ..vendor.load import load
from .errors import BuildError

FRAME_ROWS = re.compile(r'WARNING .*?: (\d+) small shapes stand against walls \(more than \d+\); frame-only sliding units '
                        r'are not looked for')


def detect(key: str, floor_label: str, items: list[dict], k: float, layer_lt: Mapping, layers: Mapping[str, str],
           project_id: str, tmp: str | Path, log: Callable[[str], None]) -> dict:
    """`items`: the floor's cache items (prims frame, per-item reading, in cache order). -> {records, seconds, slow,
    frameRowsSkipped, swingsUnmatched, output}. MemoryError and RecursionError pass through (the step child exits 75)."""
    op = load('openings', openings_data=tmp)
    gk = load('geomkit')
    roles = gk.role_matcher(R.detector_layers(layers))
    name = f'{project_id}:{key}'
    buf = io.StringIO()
    t0 = time.perf_counter()
    try:
        its = gk.dedupe([op.scaled(d, k) for d in items])
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            fl = op.Floor(name, its, dict(layer_lt), roles, 1.0)
            ops = op.detect_floor(fl)
            recs = op.finish(fl, ops, name)
    except (MemoryError, RecursionError):
        raise
    except Exception as e:  # noqa: BLE001 - any detector failure is the run's detect_failed
        text = buf.getvalue().strip()
        if text:
            log(text)
        raise BuildError('detect_failed', f'finding the doors and windows of {floor_label} failed: '
                         f'{type(e).__name__}: {e}', step=f'detect:{key}') from e
    secs = time.perf_counter() - t0
    text = buf.getvalue()
    for line in text.splitlines():
        if line.strip():
            log(f'detector, {floor_label}: {line.strip()}')
    m = FRAME_ROWS.search(text)
    used = {id(h.p) for o in ops for h in o.get('swings', [])}
    unmatched = []
    for hyps in getattr(fl, 'swings', []):
        p = hyps[0].p
        if id(p) in used:
            continue
        c = p.arc['c']
        unmatched.append({'keys': [p.d['k']] if p.d.get('k') else [], 'at': [round(float(c[0]), 3), round(float(c[1]), 3)]})
    total = float(fl.T.get('total', secs))
    return {'records': recs, 'seconds': round(secs, 2), 'slow': total > op.SLOW_FLOOR,
            'frameRowsSkipped': int(m.group(1)) if m else None, 'swingsUnmatched': unmatched, 'output': text}
