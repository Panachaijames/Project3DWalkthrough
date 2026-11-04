# Furniture goldens (builder C, 3 Nov 2026)

Made once by `make-goldens.mjs` (this folder; run from `app/` with the system Python 3.14.3 on PATH:
`node packages/viewer/test/fixtures/furniture/make-goldens.mjs`). It reads the prototype's hand-made model
`furniture/fixtures/mini_model.json` read-only, builds the variants of `furniture/test_boxes.mjs` exactly as that test
builds them, and runs the prototype's own CSV writers read-only (`python -B furniture/fixtures/expected_csv.py ...`, and
with `--kit` `furniture_kit.csv_text`), from a temp folder with `PYTHONDONTWRITEBYTECODE=1`: nothing is written into the
prototype folder (the script checks that no `__pycache__` appeared there). `goldens.json` lists every file's sha1 and size
and whether Python's writer and the kit agree (they do, for all three).

These models are not BuiltModel v1 (DESIGN.md 17.1): the unit tests pass them straight to the pure helpers
(`furnitureCsv`, `undersideMm`, `furnitureData`), never to `parseBuiltModel`.

| File | What |
|---|---|
| `mini-original.json` | `furniture/fixtures/mini_model.json` as it is (17 pieces, 10 kinds, floors L1 / L2, offset 1, 2) |
| `awkward.json` | test_boxes.mjs's awkward variant: a comma and quotes in a family, line breaks in a block and a layer, a note with both, an empty family and handle, x_m of -0.0004, exact ties (12.25 -> 12.2, 0.0625 m -> 63 mm), a kind height of 460.5 mm and a base of 10.5 mm, a kind nobody uses (atm), floors Z1, A2 (not alphabetical), pieces in reverse order |
| `broken.json` | test_boxes.mjs's broken variant: a support that is not there, a floor the model lacks, a kind it does not list (no golden: Python refuses it; the viewer's leniency is checked by the unit tests) |
| `mini-typed-heights.json` | the heights test_boxes.mjs types in: table 600, coffee-table 300, seat 480, tv 650 |
| `mini.csv`, `mini.kit.csv` | the family list of `mini-original.json`, model heights (expected_csv.py / furniture_kit.csv_text) |
| `mini-typed.csv`, `mini-typed.kit.csv` | the same with `mini-typed-heights.json` |
| `awkward.csv`, `awkward.kit.csv` | the family list of `awkward.json`, model heights |
| `goldens.json` | the manifest: sha1 and bytes per file, python / kit agreement |

The CSV files hold the text the writers print: UTF-8, CRLF, **no byte-order mark** (`csv()` and `furnitureCsv()` give the
bytes after it; the download adds `EF BB BF`). The four projects' prototype CSVs and their typed goldens are the scaffold's
(`app/fixtures/csv/`).
