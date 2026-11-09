"""The upload milestone's fixtures (docs/upload/ACCEPTANCE.md 2.5; WORK_BREAKDOWN U0 step 8), made by the scaffold U0:

    node tools/run-builder-py.mjs tools/upload/make-fixtures.py [--ref <WT_REF>] [--only <part> ...]

into app/fixtures/upload/ (each listed in fixtures/README.md with its source and sha1). Parts:
  settings   settings/{bank,house,suite,tower,small}.json (BuildSettings; fixture_settings.py), each validated by
             models_upload.BuildSettings (check_file settings) at the end
  mapping    mappings/dwp-revit.json (OfficeMapping after the bank was saved for office dwp-revit)
  drawing    drawing/{bank1,sukhumvit}.drawing.json and plan/{bank1,sukhumvit}.plan.json.gz: PROVISIONAL DrawingRead and
             PlanGeometry from the reference DXFs, by a compact port of docs/upload/reference/read_drawing.py,
             areas_propose.py and prims.py's walk with the nested keys of U-7.2 (keys.py, names.py); U2 makes the real
             ones and lists any difference
  conversion conversion/{bank1,presidential}.conversion.json: PROVISIONAL ConversionReport by the streaming check of
             docs/upload/reference/nothing_lost_stream.py (dwgread -O JSON piped, never written) and the reference
             converter logs; U1 makes the real ones
  result     build-result.bank.json, replay-input.bank.json (contracts.BuildResult / ReplayInput, from the v2 model,
             bank_stages.json, bank_summary.json and the detector outputs) and overlay/bank.overlay.json
  runs       runs/bank-prepare/ and runs/bank-build/: what a FakeJobRunner copies for a prepare and a build of the bank
             (job.json and the out/ files; files that exist in fixtures/models, fixtures/stages are referenced by path)
  maxtexts   max-texts/{bank-27oct,hotel-2nov,upload}.json: PROVISIONAL MaxTexts profiles (U-11.5), the verbatim lines
             read from the two prototype scripts; U4 owns and completes them
The reference folder (WT_REF, default %TEMP%\\wt-u0\\ref) is read only. Everything is deterministic: the same inputs give
the same bytes (dates are fixed at 2026-11-04).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
APP = HERE.parents[1]
PROJECT = APP.parent
sys.path.insert(0, str(APP / 'services' / 'builder'))
sys.path.insert(0, str(HERE))

import fixture_settings as fs  # noqa: E402

FX = APP / 'fixtures' / 'upload'
PARTS = ('settings', 'mapping', 'drawing', 'conversion', 'result', 'runs', 'maxtexts')
AT = '2026-11-04T00:00:00Z'


def dumps(obj, pretty=True) -> bytes:
    if pretty:
        return (json.dumps(obj, indent=2, ensure_ascii=False, allow_nan=False) + '\n').encode('utf-8')
    return json.dumps(obj, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode('utf-8')


def write(rel: str, data: bytes) -> Path:
    p = FX / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(data)
    print(f'  {rel}  {len(data):,} B  {hashlib.sha1(data).hexdigest()[:12]}')
    return p


def ref_manifest(ref: Path) -> dict:
    return json.loads((ref / 'manifest.json').read_text(encoding='utf-8'))


def used_layers(ref: Path, name: str) -> list[str]:
    import pickle
    with open(ref / 'proj' / 'detector' / name / 'prims.pkl', 'rb') as f:
        D = pickle.load(f)
    return sorted({d['lay'] for d in D['items']})


def small_dxf_sha1() -> str:
    with tempfile.TemporaryDirectory() as t:
        out = Path(t) / 'small.dxf'
        env = dict(os.environ, PYTHONHASHSEED='0')
        subprocess.run([sys.executable, '-B', str(HERE / 'make-test-dxf.py'), 'small', str(out)], env=env, check=True,
                       stdout=subprocess.DEVNULL)
        return hashlib.sha1(out.read_bytes()).hexdigest()


# ---------------------------------------------------------------------------------------------------------- settings
def part_settings(ref: Path) -> None:
    man = ref_manifest(ref)
    sha = {n: d['dwgSha1'] for n, d in man['drawings'].items()}
    for n, dwg in fs.DWGS.items():
        assert man['drawings'][n]['dwg'] == dwg, n
    write('settings/bank.json', dumps(fs.bank(sha)))
    write('settings/house.json', dumps(fs.house(sha, used_layers(ref, 'sukhumvit'))))
    write('settings/suite.json', dumps(fs.suite(sha, used_layers(ref, 'presidential'))))
    tower_used = sorted(set(used_layers(ref, 'l29')) | set(used_layers(ref, 'l30')))
    write('settings/tower.json', dumps(fs.tower(sha, tower_used)))
    write('settings/small.json', dumps(fs.small(small_dxf_sha1())))


def part_mapping(ref: Path) -> None:
    bank = json.loads((FX / 'settings' / 'bank.json').read_text(encoding='utf-8'))
    write('mappings/dwp-revit.json', dumps(fs.office_mapping(bank, AT)))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--ref', default=os.environ.get('WT_REF') or str(Path(tempfile.gettempdir()) / 'wt-u0' / 'ref'))
    ap.add_argument('--only', nargs='+', choices=PARTS)
    a = ap.parse_args()
    ref = Path(a.ref)
    if not (ref / 'manifest.json').exists():
        print(f'make-fixtures: no reference at {ref}: run npm run make:reference first', file=sys.stderr)
        return 1
    import fixture_parts as fp                               # the larger parts (drawing, conversion, result, runs, maxtexts)
    todo = a.only or list(PARTS)
    for part in PARTS:
        if part not in todo:
            continue
        print(f'{part}:')
        if part == 'settings':
            part_settings(ref)
        elif part == 'mapping':
            part_mapping(ref)
        else:
            getattr(fp, f'part_{part}')(ref, write, dumps)
    return 0


if __name__ == '__main__':
    sys.exit(main())
