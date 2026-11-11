"""The answer keys of the rooms milestone (docs/rooms/ACCEPTANCE.md 2.5, RA-6, RA-7). Scaffold R0.

    node tools/run-builder-py.mjs tools/rooms/make-keys.py [--acc <the upload acceptance store's copy>]

Writes fixtures/rooms/keys/:
  bank.json    each room tag of the bank with its own point on the sheet (the drawing's text insertion point, sheet m,
               per floor), from fixtures/upload/build-result.bank.json (the model's rooms and the floors' frames): the
               18 names every one of which must end in the room that holds its point (RA-7).
  probes.json  the walk probes of 9 Nov that had no floor at their start (RA-6), each by its floor, sheet point, normal
               and the side that had no floor, so that the checks do not depend on the probes' running ids: from the
               walk reports docs/rooms/reference/upload-walk-9nov/ (the door walks whose `fwd` or `back` is "no start",
               the glass probes that never started), the saved versions' models and their builds' overlays in the
               acceptance store's copy (default %TEMP%\\wt-r0\\acc-9nov). The point to test is
               `at + side * d * n` for d = 0.4 ... 0.9 m: a door walk forward starts on the -n side (side -1), back on
               the +n side (side +1); a glass probe stands on `side` * n.
  house.json, suite.json   empty: R1 writes one point per room of the house's east building, RI picks the old suite's
               16 key points.
bank.json and probes.json are deterministic; the empty keys are written only when they are missing.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
import tempfile
from pathlib import Path

APP = Path(__file__).resolve().parents[2]
KEYS = APP / 'fixtures' / 'rooms' / 'keys'
WALKS = APP / 'docs' / 'rooms' / 'reference' / 'upload-walk-9nov'
#: drawing -> (project of the acceptance store, version, its walk report, a must or a should, the probes ACCEPTANCE names)
PROBES = {
    'house': ('house-upload', 1, 'house-upload-v1.json', 'must', ['ground-004', 'ground-006', 'ground-018', 'ground-034', 'upper glass 44']),
    'suite': ('suite-upload', 1, 'suite-upload-v1.json', 'must', ['suite-025']),
    'tower': ('tower-upload', 1, 'tower-upload-v1.json', 'must',
              ['L29-001', 'L29-016', 'L29-025', 'L29-028', 'L30-033', 'L30-032', 'L30 glass 24', 'L30 glass 26']),
    'suite-revit': ('suite-revit', 1, 'suite-revit-v1.json', 'should', None),          # every door probe with no start
}


def pretty(obj) -> bytes:
    return (json.dumps(obj, indent=2, ensure_ascii=False) + '\n').encode('utf-8')


def r3(v: float) -> float:
    return round(v, 3) + 0.0


def bank_key() -> dict:
    res = json.loads((APP / 'fixtures' / 'upload' / 'build-result.bank.json').read_text(encoding='utf-8'))
    floors = {}
    for r in res['model']['rooms']:
        tx, ty = res['floors_frame'][r['floor']]['toSheet']
        floors.setdefault(r['floor'], []).append({'name': r['name'], 'label': r['label'], 'at': [r3(r['x'] + tx), r3(r['y'] + ty)]})
    n = sum(len(v) for v in floors.values())
    assert n == 18, n
    return {'format': 'rooms-key/1', 'drawing': 'bank', 'settings': 'fixtures/upload/settings/bank-rooms.json',
            'note': "Each room tag's own point: the insertion point of its text in the drawing (sheet m, the floor's own "
                    'file). Every name must belong to the room that holds its point (ACCEPTANCE RA-7: 18 of 18). From '
                    'fixtures/upload/build-result.bank.json by tools/rooms/make-keys.py.',
            'floors': floors}


def probes_key(acc: Path) -> dict:
    out = {}
    for drawing, (project, version, report, grade, wanted) in PROBES.items():
        walk = json.loads((WALKS / report).read_text(encoding='utf-8'))
        model = json.loads((acc / 'projects' / project / 'versions' / str(version) / 'model.json').read_text(encoding='utf-8'))
        ovs = sorted(glob.glob(str(acc / 'projects' / project / 'builds' / '*' / 'runs' / '*' / 'out' / 'overlay.json')))
        frames = None
        for path in ovs:                                           # the build this version was saved from: the model's stamp
            run = Path(path).parent
            if (run / 'model.json').is_file() and (run / 'model.json').read_bytes() == (
                    acc / 'projects' / project / 'versions' / str(version) / 'model.json').read_bytes():
                frames = {f['key']: f['toSheet'] for f in json.loads(Path(path).read_text(encoding='utf-8'))['floors']}
        assert frames is not None, f'{project}: no build run holds version {version}\'s model'
        openings = {o['id']: o for o in model['openings']}
        glass = {p['id']: p for p in model['probes']}
        rows = []
        for f in walk['doors']['failures']:
            sides = [s for s, k in ((-1, 'fwd'), (1, 'back')) if f.get(k) == 'no start']
            if sides and f['id'] in openings:
                rows.append((f['id'], 'door', openings[f['id']], sides))
        for f in walk['glass']['failures']:
            if f.get('stoppedAt') is None and f['probe'] in glass:
                rows.append((f['probe'], 'glass', glass[f['probe']], [f['side']]))
        found = {r[0] for r in rows}
        if wanted is not None:
            assert set(wanted) <= found, f'{drawing}: not in the report of 9 Nov: {sorted(set(wanted) - found)}'
            rows = [r for r in rows if r[0] in wanted]
            rows.sort(key=lambda r: wanted.index(r[0]))
        probes = []
        for pid, kind, o, sides in rows:
            tx, ty = frames[o['floor']]
            probes.append({'id9Nov': pid, 'kind': kind, 'floor': o['floor'], 'at': [r3(o['x'] + tx), r3(o['y'] + ty)],
                           'n': [r3(o['nx']), r3(o['ny'])], 'sides': sides,
                           **({'width': o['width']} if kind == 'door' else {'what': o.get('what')})})
        out[drawing] = {'project': project, 'version': version, 'stamp': walk['loads']['stamp'], 'grade': grade,
                        'report': f'docs/rooms/reference/upload-walk-9nov/{report}', 'probes': probes}
    return {'format': 'probes-key/1',
            'note': 'The walk probes of 9 Nov 2026 that found no floor at their start (ACCEPTANCE RA-6). `at` is the '
                    "opening's or the glass probe's point on the sheet (m), `n` its normal, `sides` the sides that had no "
                    'floor: the plate must hold the point at + side * d * n, d = 0.4 ... 0.9 m. `id9Nov` is the running '
                    'id of that day and may have moved since. By tools/rooms/make-keys.py.',
            'drawings': out}


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--acc', default=str(Path(os.environ.get('TEMP') or tempfile.gettempdir()) / 'wt-r0' / 'acc-9nov'))
    a = ap.parse_args(argv)
    KEYS.mkdir(parents=True, exist_ok=True)
    files = {'bank.json': pretty(bank_key()), 'probes.json': pretty(probes_key(Path(a.acc)))}
    for drawing, who in (('house', "R1: one point per room of the house's east building"), ('suite', 'RI: 16 key points of the old suite')):
        if not (KEYS / f'{drawing}.json').exists():
            files[f'{drawing}.json'] = pretty({'format': 'rooms-key/1', 'drawing': drawing,
                                               'settings': f'fixtures/upload/settings/{drawing}-rooms.json',
                                               'note': f'Empty at the scaffold. {who} (docs/rooms/WORK_BREAKDOWN.md).',
                                               'floors': {}})
    for name, data in files.items():
        (KEYS / name).write_bytes(data)
        print(f'fixtures/rooms/keys/{name}  {len(data):,} B')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
