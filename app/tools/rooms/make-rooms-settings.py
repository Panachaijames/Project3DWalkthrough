"""The new-rule settings fixtures of the rooms milestone (docs/rooms/DESIGN.md R-1.3; ACCEPTANCE 2.5). Scaffold R0;
R1 owns the five files afterwards.

    node tools/run-builder-py.mjs tools/rooms/make-rooms-settings.py [--check]

Writes fixtures/upload/settings/{bank,house,suite,tower,suite-revit}-rooms.json, each derived from a fixture that stays
as it is (the old rule):

  bank, house, suite, tower   the upload fixture <name>.json plus the three options at their new values
                              (contracts.NEW_RULES: slabs 'network', ceilings 'auto', stairs 'climb');
  house                       also its ceiling heights: ground 3.00 m, upper 2.90 m (the elevations,
                              cad_test/src/heights.json);
  suite-revit                 the saved recipe of the A-12 run (recipes/suite-revit.json: the project-data.json of
                              `suite-revit` v1) with layer 0 set to wall, where the new suite's partitions are, and
                              nothing set aside (the recipe sets nothing aside), plus the three options.

`--check` writes nothing and exits 1 when a file on disk differs from what this tool would write. Deterministic.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

APP = Path(__file__).resolve().parents[2]
SETTINGS = APP / 'fixtures' / 'upload' / 'settings'
NEW_RULES = {'slabs': 'network', 'ceilings': 'auto', 'stairs': 'climb'}
SOURCES = {'bank': 'bank', 'house': 'house', 'suite': 'suite', 'tower': 'tower', 'suite-revit': 'recipes/suite-revit'}
HOUSE_CEILINGS = {'ground': 3.0, 'upper': 2.9}


def derive(name: str) -> dict:
    s = json.loads((SETTINGS / f'{SOURCES[name]}.json').read_text(encoding='utf-8'))
    assert not (set(s['options']) & set(NEW_RULES)), f'{SOURCES[name]}.json already carries a key of the rooms milestone'
    s['options'].update(NEW_RULES)
    if name == 'house':
        for f in s['floors']:
            f['ceilingHeight'] = HOUSE_CEILINGS[f['key']]
    if name == 'suite-revit':
        assert s['layers']['0'] == 'other' and s['fixes']['setAside'] == []
        s['layers']['0'] = 'wall'
    return s


def main(argv: list[str]) -> int:
    check = '--check' in argv
    bad = 0
    for name in SOURCES:
        data = (json.dumps(derive(name), indent=2, ensure_ascii=False, allow_nan=False) + '\n').encode('utf-8')
        p = SETTINGS / f'{name}-rooms.json'
        if check:
            same = p.is_file() and p.read_bytes() == data
            bad += not same
            print(f'{p.name}: {"as this tool writes it" if same else "DIFFERENT (or missing)"}')
        else:
            p.write_bytes(data)
            print(f'{p.name}: {len(data):,} B')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
