"""Does each acceptance settings fixture's DERIVED detector mapping reproduce the frozen detector output?
(docs/upload/DESIGN.md U-8.2; WORK_BREAKDOWN U0 step 8; ACCEPTANCE A-4)

    node tools/run-builder-py.mjs tools/upload/check-derived-mapping.py [--ref <WT_REF>] [--out <dir>] [bank house ...]

For fixtures/upload/settings/{bank,house,suite,tower}.json: per source, a detector mapping made from the settings alone
(`layers` = roles.detector_layers(settings.layers): `other` and `room-outline` layers read as context, `ignore` and the
non-detector roles dropped; `areas` = the floors' areas of that source; `floors` = {key: 'check:<key>'}), run by the
VENDORED detector (walkthrough_builder/vendor/openings.py, in-process) on the reference caches of `make:reference`
(<WT_REF>/proj/detector/<name>/prims.pkl, read-only), and compared record for record with
detector/output/<name>_openings.json, the `floor` field removed on both sides. The check is that the derived mapping
REPRODUCES the output, not that it lists the same layers (the bank's does not, and reproduces).
Prints a markdown table (for docs/upload/contract-issues/U0.md) and every difference; exit 1 when any drawing differs.
The detector's own output files go to --out (default <WT_TMP>/derived-mapping), never into the reference.
"""
from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
APP = HERE.parents[1]
PROJECT = APP.parent
sys.path.insert(0, str(APP / 'services' / 'builder'))
sys.path.insert(0, str(HERE))

from walkthrough_builder import roles  # noqa: E402

SETTINGS = APP / 'fixtures' / 'upload' / 'settings'
FIXTURES = ('bank', 'house', 'suite', 'tower')


def area_spec(area: dict) -> dict:
    if area['kind'] == 'wholeFile':
        return {'wholeFile': True}
    return {'bbox': list(area['bbox']), 'pad': area['pad'], 'match': area['match']}


def strip_floor(records: list[dict]) -> list[dict]:
    return [{k: v for k, v in r.items() if k != 'floor'} for r in records]


def describe(mine: list[dict], oracle: list[dict]) -> list[str]:
    a = {r['id']: r for r in strip_floor(mine)}
    b = {r['id']: r for r in strip_floor(oracle)}
    out = []
    for i in sorted(set(a) | set(b)):
        if i not in a:
            out.append(f'{i}: missing ({b[i]["kind"]} at {b[i]["a"]} - {b[i]["b"]})')
        elif i not in b:
            out.append(f'{i}: extra ({a[i]["kind"]} at {a[i]["a"]} - {a[i]["b"]})')
        elif a[i] != b[i]:
            keys = sorted(k for k in set(a[i]) | set(b[i]) if a[i].get(k) != b[i].get(k))
            out.append(f'{i}: differs in {", ".join(keys)}')
    if not out and [r['id'] for r in mine] != [r['id'] for r in oracle]:
        out.append('the same records in another order')
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--ref', default=os.environ.get('WT_REF') or str(Path(tempfile.gettempdir()) / 'wt-u0' / 'ref'))
    ap.add_argument('--out', default=str(Path(os.environ.get('WT_TMP') or tempfile.gettempdir()) / 'derived-mapping'))
    ap.add_argument('fixtures', nargs='*', default=list(FIXTURES))
    a = ap.parse_args()
    ref = Path(a.ref)
    man = json.loads((ref / 'manifest.json').read_text(encoding='utf-8'))
    by_sha = {d['dwgSha1']: n for n, d in man['drawings'].items()}
    out_dir = Path(a.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    from walkthrough_builder.vendor.load import load
    op = load('openings', openings_data=ref / 'proj' / 'detector')

    rows, diffs, failed = [], [], False
    for fx in a.fixtures:
        s = json.loads((SETTINGS / f'{fx}.json').read_text(encoding='utf-8'))
        layers = roles.detector_layers(s['layers'])
        for src in s['sources']:
            name = by_sha.get(src['sha1'])
            if name is None:
                print(f'{fx}: source {src["name"]} ({src["sha1"][:12]}) is not in the reference', file=sys.stderr)
                failed = True
                continue
            floors = [f for f in s['floors'] if f['source'] == src['sha1']]
            mapping = {'cache': name, 'units': src['units'] or 'mm',
                       'floors': {f['key']: f'check:{f["key"]}' for f in floors},
                       'areas': {f['key']: area_spec(f['area']) for f in floors},
                       'layers': layers}
            mp = out_dir / f'{fx}_{name}_mapping.json'
            mp.write_text(json.dumps(mapping, indent=1, ensure_ascii=False), encoding='utf-8')
            res = out_dir / f'{fx}_{name}_openings.json'
            t0 = time.perf_counter()
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
                op.run(str(mp), str(res))
            secs = time.perf_counter() - t0
            mine = json.loads(res.read_text(encoding='utf-8'))['openings']
            oracle = json.loads((PROJECT / 'detector' / 'output' / f'{name}_openings.json')
                                .read_text(encoding='utf-8'))['openings']
            same = strip_floor(mine) == strip_floor(oracle)
            failed |= not same
            listed = {r: sorted(v) for r, v in layers.items()}
            rows.append(f'| {fx} | {name} | {", ".join(f["key"] for f in floors)} | {len(mine)} | {len(oracle)} | '
                        f'{"equal" if same else "DIFFERS"} | {secs:.1f} s |')
            if not same:
                diffs.append((fx, name, describe(mine, oracle), listed))
    print('| Fixture | Drawing | Floors | Records | detector/output | Result | Time |')
    print('|---|---|---|---|---|---|---|')
    for r in rows:
        print(r)
    for fx, name, d, listed in diffs:
        print(f'\n{fx} / {name}: {len(d)} difference(s)')
        for line in d[:40]:
            print(f'  {line}')
        print(f'  derived layers: {json.dumps(listed, ensure_ascii=False)}')
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
