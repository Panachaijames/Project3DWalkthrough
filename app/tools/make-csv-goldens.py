"""Typed-height furniture CSV goldens (DESIGN.md 17.1; WORK_BREAKDOWN S.8). Scaffold tool.

Run with the SYSTEM Python (furniture_kit imports shapely, which the API venv does not have), from app/:
    python -B tools/make-csv-goldens.py
It loads ../furniture/furniture_kit.py BY PATH with sys.dont_write_bytecode = True (no __pycache__ appears in furniture/),
calls its csv_text read-only, and writes fixtures/csv/<project>-typed.csv for the four furnished fixture models with the
typed heights table 600, seat 300, cabinet 1000, other 2100 (each where the model has that kind). The files carry the
byte-order mark, as the download does (furniture_kit.write_csv). It also checks that csv_text with no typed heights
equals each prototype CSV copied to fixtures/csv/<project>.csv, byte for byte after the BOM, and exits 1 if not.
"""
import importlib.util
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
APP = Path(__file__).resolve().parent.parent
KIT = APP.parent / 'furniture' / 'furniture_kit.py'
TYPED = {'table': 600, 'seat': 300, 'cabinet': 1000, 'other': 2100}
PROJECTS = ['bank-v2', 'suite', 'house', 'hotel']
BOM = b'\xef\xbb\xbf'


def load_kit():
    spec = importlib.util.spec_from_file_location('furniture_kit_readonly', KIT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    kit = load_kit()
    bad = 0
    for name in PROJECTS:
        model = json.loads((APP / 'fixtures' / 'models' / f'{name}.model.json').read_text(encoding='utf-8'))
        args = (model['furniture'], model['furnitureKinds'], model['floors'], model.get('offset', [0, 0]))
        plain = kit.csv_text(*args).encode('utf-8')
        proto = (APP / 'fixtures' / 'csv' / f'{name}.csv').read_bytes()
        same = proto == BOM + plain
        bad += not same
        kinds = {k['key'] for k in model['furnitureKinds']}
        heights = {k: v for k, v in TYPED.items() if k in kinds}
        typed = kit.csv_text(*args, heights).encode('utf-8')
        out = APP / 'fixtures' / 'csv' / f'{name}-typed.csv'
        out.write_bytes(BOM + typed)
        print(f'{name}: default heights {"equal" if same else "DIFFER from"} the prototype CSV; '
              f'{out.relative_to(APP).as_posix()} with {heights} ({len(typed)} bytes)')
    if (KIT.parent / '__pycache__').exists():
        print('furniture/__pycache__ exists: something wrote bytecode there', file=sys.stderr)
        bad += 1
    return 1 if bad else 0


if __name__ == '__main__':
    raise SystemExit(main())
