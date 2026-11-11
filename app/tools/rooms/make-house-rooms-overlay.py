"""fixtures/upload/overlay/house-rooms.overlay.json (docs/rooms/ACCEPTANCE.md 2.5). Scaffold R0; re-made by RI.

    node tools/run-builder-py.mjs tools/rooms/make-house-rooms-overlay.py [--ref <WT_REF>] [--tmp <dir>] [--check]

The house built with fixtures/upload/settings/house-rooms.json by build(), written by the builder's own overlay writer.
At R0 that was THE TRACER (its rooms every face of today's walls and spans, its plate today's plate and the ring, no
stair of the house climbing), with the new floor fields of DESIGN R-12.4 (spaces, holes, stairs, closings, unfloored)
and the new flags added from the build's report by tools/rooms/make-reference-building.py's `overlay_rooms`: a
PROVISIONAL fixture for the staff app's screens (R6) and the API's checks (R5) before the real rules existed. The
integration step RI (11 Nov, after R1 - R7; WORK_BREAKDOWN RI-0, R6.md D-3) re-made it with the real rules (R1's and
R2's) and R3's out/overlay.py, which writes the new fields and flags itself, every one in the floor's sheet metres.

The house is read from the reference cache (WT_REF, default %TEMP%\\wt-u0\\ref: the prototype prims.pkl of the
Sukhumvit drawing) with fixtures/upload/drawing/sukhumvit.drawing.json, as the builder's tests read it.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import sys
import tempfile
from pathlib import Path

APP = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(APP / 'services' / 'builder'))
sys.dont_write_bytecode = True
OUT = APP / 'fixtures' / 'upload' / 'overlay' / 'house-rooms.overlay.json'


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    temp = Path(os.environ.get('TEMP') or tempfile.gettempdir())
    ap.add_argument('--ref', default=os.environ.get('WT_REF') or str(temp / 'wt-u0' / 'ref'))
    ap.add_argument('--tmp', default=None)
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args(argv)
    spec = importlib.util.spec_from_file_location('make_reference_building', Path(__file__).with_name('make-reference-building.py'))
    REF = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(REF)
    from walkthrough_builder import oslock
    from walkthrough_builder.build import build
    tmp = Path(a.tmp) if a.tmp else Path(tempfile.mkdtemp(prefix='wt-house-rooms-'))
    s = json.loads((APP / 'fixtures' / 'upload' / 'settings' / 'house-rooms.json').read_text(encoding='utf-8'))
    prims = Path(a.ref) / 'proj' / 'detector' / 'sukhumvit' / 'prims.pkl'
    if not prims.is_file():
        print(f'no reference cache at {prims} (WT_REF)', file=sys.stderr)
        return 1
    src = s['sources'][0]
    sources = [{'sha1': src['sha1'], 'name': src['name'], 'kind': 'dwg', 'units': 'mm', 'conversion': None,
                'drawing': str(APP / 'fixtures' / 'upload' / 'drawing' / 'sukhumvit.drawing.json'), 'items': str(prims),
                'plan': '', 'dxfSha1': None}]
    ctx = REF.context(s, sources, tmp, 'house-upload')
    with oslock.hold():
        res = build(ctx, lambda _m: None, lambda _s, _f: None)
    written = REF.write_outputs(res, ctx)
    ov = json.loads(written['overlay.json'].read_bytes())
    if not all('spaces' in fl for fl in ov['floors']):      # before R3's out/overlay.py wrote the new fields and flags
        ov = REF.overlay_rooms(ov, res)
    data = REF.compact(ov)
    kinds = {}
    for f in ov['flags']:
        kinds[f['kind']] = kinds.get(f['kind'], 0) + 1
    print(f'house-rooms overlay: {[(f["key"], len(f["spaces"]), len(f["holes"]), len(f["stairs"])) for f in ov["floors"]]} '
          f'(floor, spaces, holes, stairs); flags {kinds}; {len(data):,} B  {hashlib.sha1(data).hexdigest()[:12]}')
    if a.check:
        same = OUT.is_file() and OUT.read_bytes() == data
        print('as this tool writes it' if same else 'DIFFERENT (or missing)')
        return 0 if same else 1
    OUT.write_bytes(data)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
