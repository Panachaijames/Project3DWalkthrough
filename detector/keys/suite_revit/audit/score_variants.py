"""How much the held-out figure depends on the key's open conventions (the "Uncertain points" of ../README.md).
Done the way ../../tower/audit/score_variants.py did it for L29 / L30. Step 7 of 7; changes nothing.

  python -B keys/suite_revit/audit/score_variants.py            (Git Bash, from detector/)

Each variant flips the optional flag of some entries of the audited key in memory and scores the same held-out output
with tools/score.py. The key's own reading is the first line; the others are readings its README names as possible.
"""
import json, sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
DETECTOR = HERE.parents[2]
sys.path.insert(0, str(DETECTOR / 'tools'))
import score as scorer                          # noqa: E402

KEY = json.loads((HERE.parent / 'suite_revit_audited.json').read_text(encoding='utf-8'))
DET = json.loads((DETECTOR / 'blind_run_suite_revit' / 'output_first_mapping' / 'suite_revit.json').read_text(encoding='utf-8'))

CORRIDOR = ['SR-13', 'SR-14', 'SR-15', 'SR-16']          # doors outside the suite: two riser doors, two unit doors
GLASS = ['SR-19', 'SR-20', 'SR-21', 'SR-22']             # glass doors of the bathroom glass screens
BIFOLD = ['SR-03']                                       # the bi-fold of the walk-in wardrobe
FACETS = [f'SR-{n}' for n in range(25, 43)]              # the 18 curtain-wall facets

VARIANTS = [
    ('the key as it is', {}),
    ('suite only: the four corridor doors optional', {i: True for i in CORRIDOR}),
    ('glass-screen doors scored', {i: False for i in GLASS}),
    ('suite only, glass-screen doors scored', {**{i: True for i in CORRIDOR}, **{i: False for i in GLASS}}),
    ('the walk-in wardrobe bi-fold optional', {i: True for i in BIFOLD}),
    ('curtain-wall facets left out of the key (glass wall only, as the tower key)', {i: None for i in FACETS}),
    ('curtain-wall facets scored as windows', {i: False for i in FACETS}),
]

for name, flip in VARIANTS:
    k = json.loads(json.dumps(KEY))
    k['openings'] = [o for o in k['openings'] if flip.get(o['id'], 0) is not None]
    for o in k['openings']:
        if o['id'] in flip:
            o['optional'] = flip[o['id']]
    t = scorer.score(k, DET)['total']
    fr = scorer.score(k, DET)['floors']['suite_revit']
    print(f"{name:76} scored {t['keyCount']:2}  found {t['matched']:2}  right {t['right']:2} ({100 * t['right'] / t['keyCount']:.0f} %)  "
          f"not in the key {len(fr['extra']):2}")
