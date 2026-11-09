# Gap report: uploaded versions against their prototypes (9 Nov 2026)

Written by the integration step UI (docs/upload/ACCEPTANCE.md A-5, A-6, A-12) with `tools/upload/gap-report.py`. Every
version below was made through the app's own path: the DWGs uploaded in parts to a served API (`node tools/run-api.mjs
--port 8711 --seed-fresh`, a freshly seeded store in `%TEMP%\wt-ui\acc\data`, a fresh cache), prepared and built by the
real worker (`walkthrough_builder.job` in the builder's venv, LibreDWG 0.14), with the settings fixtures
`fixtures/upload/settings/<name>.json` and **no fixes** (A-5), saved with `saveBuild`, then made into offline files with
`make-offline.mjs` and walked in headless Edge by `tests/e2e/upload-walk.spec.ts` (A-6). The API validated every run
(schema, D-5.6, every record, the `.ms` stamp: `api.json` `validated: true` on every prepare and build run of these versions).

The metrics are compared in drawing coordinates (model + offset + the floor's sheetShift), per floor. Each difference over
0.05 m2, 1 opening or 1 piece is listed with its cause and one of: **option now** (U-10.5, available in this milestone),
**option later**, **check-and-fix now** / **later**, **accepted difference** (by design). A failing walk probe of the house,
the suite, the tower or the A-12 drawing is listed the same way (A-6: must run, should pass); the bank re-upload must pass
every walk check.

| Version | Drawing(s) | Model stamp | Parts | Openings | Furniture | Flags (to check) | Walk checks (A-6) |
|---|---|---|---|---|---|---|---|
| bank-reupload v1 (A-1 a) | I1201, I1202 | `c3a9408304a2` (v2's bytes) | 124 | 49 | 185 in 14 kinds | 20 (8) | loads ok; start ok; floors ok; walls ok (80); doors ok (39); glass ok (30 probes + 14 random parts) |
| bank-sampeng v3 (A-1 b) | I1201, I1202 | `c3a9408304a2` | 124 | 49 | 185 | 20 (8) | loads ok; start ok; floors ok; walls ok (80); doors ok (39); glass ok (30 probes + 14 random parts) |
| house-upload v1 (A-5) | Test Sukhumvit Residence | `730ca65a45d3` | 185 | 86 | 79 in 9 kinds | 64 (49) | loads ok; start ok; floors ok; walls ok (80); doors 4 failing of 32; glass 2 failing of 57 probes + 20 random parts |
| suite-upload v1 (A-5) | layout presidential test | `205e9c2c46e8` | 50 | 25 | 127 in 13 kinds | 47 (24) | loads ok; start ok; floors ok; walls ok (40); doors 1 failing of 15; glass no glass to probe |
| suite-outlines v1 (A-5, every outline suggestion accepted) | layout presidential test | `2c85c67fe80f` | 71 | 25 | 127 | 45 (25) | loads ok; start ok; floors ok; walls ok (40); doors 1 failing of 15; glass ok (2 probes + 2 random parts) |
| tower-upload v1 (A-5) | L29, L30 | `91414f408cb2` | 233 | 65 | 270 in 9 kinds | 98 (66) | loads ok; start ok; floors ok; walls ok (80); doors 7 failing of 44; glass 4 failing of 13 probes + 7 random parts |
| suite-revit v1 (A-12, new project) | presidential suite_layout | `1d90d91ef949` | 35 | 25 | 81 in 7 kinds | 33 (22) | loads ok; start ok; floors ok; walls ok (40); doors 3 failing of 9; glass no glass to probe |
| presidential-suite v2 (A-12, new version) | presidential suite_layout | `467d3f8444c0` | 35 | 25 | 81 | 33 (22) | loads ok; start ok; floors ok; walls no start spot found (0 of 40 tried); doors 3 failing of 9; glass no glass to probe |

## 1. The bank re-upload (A-1): no gap

Both forms (a new project `bank-reupload`, and version 3 of the seeded `bank-sampeng`) give v2's model byte for byte
(`c3a9408304a240b83c36f5c5c53db56b50a72c64`), v2's CSV (`b528bb2320ef`), v2's top view (`f084b556503c`), the detector's
24 + 25 records (equal to `detector/output/bank{1,2}_openings.json` with `floor` removed, ids equal), and v2's
`stages.json` in `floors[k].lines`, `rings`, `sheet` and `source.files`, `layersInUse`, `units`. The Max generator with the
`bank-27oct` profile on the uploaded model gives `bank_test/Bangkok_Bank_Sampeng.ms` byte for byte (`615d50137bdb`, 867
CRLF lines); the version's own script (profile `upload`) equals the generator's output with the build's date (9 Nov 2026)
and differs from the bank-profile script in its 13 profile lines only (header, built-by, converter, follow / keep, datum
Source and Built, rollout title). The gap report finds nothing over its thresholds on either floor.

Different by design (A-1 "may differ"): `stages.json` `pieces` (the build's own pairing) and every text; `version.json`
`label`, `createdAt`, no `seed`; the presentation (heading without "(test)", the fact-built intro, the fitSlabs camera);
the `source/` sidecars; the Max script's profile lines.

### Gap report: bank

Prototype: Bangkok Bank, Sampeng Branch (2 floor(s), 124 parts); upload: Bangkok Bank, Sampeng Branch (2 floor(s), 124 parts). Drawing coordinates (model + offset + sheetShift). Differences over 0.05 m2, 1 opening or 1 piece are listed below the table.

#### Floor L1 (prototype) / L1 (upload)

| Metric | Prototype | Upload | Difference |
|---|---|---|---|
| wall area (m2) | 22.42 | 22.42 | sym. difference 0.00 |
| wall runs | 10 | 10 | 0 |
| glass area (m2) | 0.48 | 0.48 | sym. difference 0.00 |
| glass pieces | 30 | 30 | 0 |
| doors | 15 | 15 | 0 |
| windows | 7 | 7 | 0 |
| passages | 2 | 2 | 0 |
| openings matched (centre within 0.2 m) | - | 24 of 24 | 0 prototype openings unmatched |
| lintels | 10 | 10 | 0 |
| sills | 0 | 0 | 0 |
| panes | 0 | 0 | 0 |
| plate area (m2) | 237.36 | 237.36 | sym. difference 0.00 |
| rooms | 7 | 7 | 7 names matched |
| furniture: atm | 3 | 3 | 0 |
| furniture: cabinet | 2 | 2 | 0 |
| furniture: coffee-table | 7 | 7 | 0 |
| furniture: computer | 7 | 7 | 0 |
| furniture: partition | 4 | 4 | 0 |
| furniture: phone | 4 | 4 | 0 |
| furniture: plant | 3 | 3 | 0 |
| furniture: printer | 2 | 2 | 0 |
| furniture: sanitary | 4 | 4 | 0 |
| furniture: seat | 37 | 37 | 0 |
| furniture: sofa | 4 | 4 | 0 |
| furniture: table | 7 | 7 | 0 |
| furniture: tall-cabinet | 2 | 2 | 0 |
| furniture: tv | 2 | 2 | 0 |

#### Floor L2 (prototype) / L2 (upload)

| Metric | Prototype | Upload | Difference |
|---|---|---|---|
| wall area (m2) | 18.02 | 18.02 | sym. difference 0.00 |
| wall runs | 14 | 14 | 0 |
| glass area (m2) | 0.09 | 0.09 | sym. difference 0.00 |
| glass pieces | 6 | 6 | 0 |
| doors | 24 | 24 | 0 |
| windows | 0 | 0 | 0 |
| passages | 1 | 1 | 0 |
| openings matched (centre within 0.2 m) | - | 25 of 25 | 0 prototype openings unmatched |
| lintels | 23 | 23 | 0 |
| sills | 0 | 0 | 0 |
| panes | 0 | 0 | 0 |
| plate area (m2) | 285.02 | 285.02 | sym. difference 0.00 |
| rooms | 11 | 11 | 11 names matched |
| furniture: cabinet | 10 | 10 | 0 |
| furniture: coffee-table | 6 | 6 | 0 |
| furniture: computer | 9 | 9 | 0 |
| furniture: phone | 5 | 5 | 0 |
| furniture: plant | 4 | 4 | 0 |
| furniture: printer | 5 | 5 | 0 |
| furniture: sanitary | 6 | 6 | 0 |
| furniture: seat | 38 | 38 | 0 |
| furniture: sofa | 6 | 6 | 0 |
| furniture: table | 5 | 5 | 0 |
| furniture: tall-cabinet | 3 | 3 | 0 |

#### Differences

None over the thresholds.


#### Walk checks (A-6)

Every walk probe passes (loads ok; start ok; floors ok; walls ok (80); doors ok (39); glass ok (30 probes + 14 random parts)).


## 2. The house (A-5): `Test Sukhumvit Residence.dwg` against `sukhumvit-house` v1

Settings `fixtures/upload/settings/house.json`: two area boxes on one sheet, floors `ground` / `upper` at 0.90 / 4.80
with walls of 3.90 / 3.50, alignment `auto`, no fixes. Conversion `minor` (1 item put on layer 0, 1 item changed block;
the 1,004 handle-not-found, 385 wrong-layer and 81 + 1 error lines leave it `minor`, with one note), units read as mm
(the header says inches, 28 doors say mm). The run is `done` and validated, and the version saves and opens.

* **Alignment (A-5, must):** `auto` picked `grid`: shift (-74.0221, 0.0) m, spread 0.9 mm, 16 labels shared in two
  families (`2` ... `12`, `D`, `E`, `F`, `H`, `J`); the model's upper floor has `sheetShift [74.022, 0]`. A-5 asks
  (-74.021 +- 0.002, 0.000 +- 0.002) with a spread under 2 mm: met. (A-4's "12 numbered and 12 lettered labels on each
  plan" is not: the drawing's grid lines are 1.5 m ticks and 27 of the 63 labels have none; U2.md 3, U3.md 2.)
* **Openings:** 86 (43 a floor), all 43 + 43 matched to the prototype's by kind and centre within 0.2 m. Their heads:
  28 floor-length sliding windows (`eitherKind`, no sill in plan: 10 ground, 18 upper) are glazed to the wall height by
  the bank's curtain rule (3.90 / 3.50 m) where the prototype gave them the floor's window head (3.00 / 2.60): **accepted
  difference** (U-10.5 "not adopted": glass full height against the prototype's lower glazing). The 5 openings whose
  heights the prototype took from the elevations (`cad_test/src/heights.json`: 3.90, 3.90, 2.90, 2.90, 2.55 m) get the
  floor defaults here: **check-and-fix now** (the opening editor's head and sill).
* **Stairs:** tread lines against the prototype's panels, and the upper stair void: **option later** (climbable stairs).
* **Furniture:** ground 47 = 47 kind for kind; upper 32 against 29 (`other` +3: the prototype's `settle()` of rug and zone
  outlines is not a U-10.5 rule): **option later**.

### Gap report: house

Prototype: Test Sukhumvit Residence (2 floor(s), 197 parts); upload: Test Sukhumvit Residence (2 floor(s), 185 parts). Drawing coordinates (model + offset + sheetShift). Differences over 0.05 m2, 1 opening or 1 piece are listed below the table.

#### Floor ground (prototype) / ground (upload)

| Metric | Prototype | Upload | Difference |
|---|---|---|---|
| wall area (m2) | 30.45 | 32.40 | sym. difference 3.22 |
| wall runs | 32 | 27 | -5 |
| glass area (m2) | 8.14 | 7.52 | sym. difference 0.65 |
| glass pieces | 23 | 24 | 1 |
| doors | 19 | 19 | 0 |
| windows | 16 | 16 | 0 |
| passages | 8 | 8 | 0 |
| openings matched (centre within 0.2 m) | - | 43 of 43 | 0 prototype openings unmatched |
| lintels | 31 | 25 | -6 |
| sills | 1 | 1 | 0 |
| panes | 19 | 0 | -19 |
| plate area (m2) | 493.81 | 428.02 | sym. difference 129.44 |
| rooms | 0 | 0 | 0 names matched |
| furniture: appliance | 2 | 2 | 0 |
| furniture: cabinet | 2 | 2 | 0 |
| furniture: coffee-table | 2 | 2 | 0 |
| furniture: counter | 1 | 1 | 0 |
| furniture: other | 26 | 26 | 0 |
| furniture: sanitary | 6 | 6 | 0 |
| furniture: seat | 1 | 1 | 0 |
| furniture: sofa | 7 | 7 | 0 |

#### Floor upper (prototype) / upper (upload)

| Metric | Prototype | Upload | Difference |
|---|---|---|---|
| wall area (m2) | 36.87 | 37.06 | sym. difference 1.25 |
| wall runs | 27 | 24 | -3 |
| glass area (m2) | 3.66 | 3.18 | sym. difference 0.90 |
| glass pieces | 28 | 43 | 15 |
| doors | 13 | 13 | 0 |
| windows | 21 | 21 | 0 |
| passages | 9 | 9 | 0 |
| openings matched (centre within 0.2 m) | - | 43 of 43 | 0 prototype openings unmatched |
| lintels | 34 | 16 | -18 |
| sills | 0 | 0 | 0 |
| panes | 21 | 0 | -21 |
| plate area (m2) | 439.08 | 421.08 | sym. difference 34.59 |
| rooms | 0 | 0 | 0 names matched |
| furniture: bed | 2 | 2 | 0 |
| furniture: other | 22 | 25 | 3 |
| furniture: sanitary | 4 | 4 | 0 |
| furniture: seat | 1 | 1 | 0 |

#### Differences

| Floor | Metric | Prototype | Upload | Difference | Cause | Class |
|---|---|---|---|---|---|---|
| ground | wall area | 30.45 | 32.40 | 3.22 m2 symmetric difference | the prototype's house cutter rules (fins, glass corners, jamb-section depth, lintel slots) and its 0.03 m closing against the bank's 0.12 m; on the ground floor also an 8.7 m x 0.8 m double line east of the main block (x 40.1 - 40.9) that the bank's pairing builds as a wall | option later |
| ground | glass area | 8.14 | 7.52 | 0.65 m2 symmetric difference | glass full height against the prototype's H - 0.6 m, and the glass corners of the cutter rules (U-10.5 not adopted) | accepted difference |
| ground | plate area | 493.81 | 428.02 | 129.44 m2 symmetric difference | the prototype's plates are the fused walls and glass with gaps under 3 m closed (cad_test/src/merge_cad.py); the general builder's come from the bank's room rule, which gives no plate to the glass-walled living area on the ground floor (75 + 18 m2 at x 19 - 32, y 6 - 14) and the glass room at the upper floor's east end (18.5 m2), and gives plates the prototype's shell left out (16 + 10 m2) | option later |
| ground | wall runs | 32 | 27 | -5 | the same cutter rules and closing (the prototype cut its runs at fins, glass corners and lintel slots) | option later |
| ground | glass pieces | 23 | 24 | +1 | window glass built as glass parts by the bank's rules where the prototype made panes, and the eitherKind sliding doors glazed like windows | accepted difference |
| ground | lintels | 31 | 25 | -6 | the lintel-bearing rule and the lintel slots of the house cutter (U-10.5 house cutter rules) | option later |
| ground | panes | 19 | 0 | -19 | the house prototype made each window's glass a pane part; the general builder (the bank's rules) glazes windows with glass parts (counted under glass pieces) | accepted difference |
| upper | wall area | 36.87 | 37.06 | 1.25 m2 symmetric difference | the prototype's house cutter rules (fins, glass corners, jamb-section depth, lintel slots) and its 0.03 m closing against the bank's 0.12 m; on the ground floor also an 8.7 m x 0.8 m double line east of the main block (x 40.1 - 40.9) that the bank's pairing builds as a wall | option later |
| upper | glass area | 3.66 | 3.18 | 0.90 m2 symmetric difference | glass full height against the prototype's H - 0.6 m, and the glass corners of the cutter rules (U-10.5 not adopted) | accepted difference |
| upper | plate area | 439.08 | 421.08 | 34.59 m2 symmetric difference | the prototype's plates are the fused walls and glass with gaps under 3 m closed (cad_test/src/merge_cad.py); the general builder's come from the bank's room rule, which gives no plate to the glass-walled living area on the ground floor (75 + 18 m2 at x 19 - 32, y 6 - 14) and the glass room at the upper floor's east end (18.5 m2), and gives plates the prototype's shell left out (16 + 10 m2) | option later |
| upper | wall runs | 27 | 24 | -3 | the same cutter rules and closing (the prototype cut its runs at fins, glass corners and lintel slots) | option later |
| upper | glass pieces | 28 | 43 | +15 | window glass built as glass parts by the bank's rules where the prototype made panes, and the eitherKind sliding doors glazed like windows | accepted difference |
| upper | lintels | 34 | 16 | -18 | the lintel-bearing rule and the lintel slots of the house cutter (U-10.5 house cutter rules) | option later |
| upper | panes | 21 | 0 | -21 | the house prototype made each window's glass a pane part; the general builder (the bank's rules) glazes windows with glass parts (counted under glass pieces) | accepted difference |
| upper | furniture: other | 22 | 25 | +3 | the prototype's settle() (rug and zone outlines that enclose a smaller piece) is not among U-10.5's rules (U3.md section 6) | option later |


#### Walk checks (A-6)

6 failing probes (loads ok; start ok; floors ok; walls ok (80); doors 4 failing of 32; glass 2 failing of 57 probes + 20 random parts).

| Floor | Probe | Id | Detail | Cause | Class |
|---|---|---|---|---|---|
| ground | walk: doors | ground-004 | exterior door; through one way: no start: no floor 0.40 - 0.90 m before the door; the other way: -0.45 m (stopped before the door) | one of the three sliding glass doors (eitherKind, glazed like windows by design, U3-6); it opens onto the glass-walled living area, which has no floor plate in this build (the plate gap above) | option later |
| ground | walk: doors | ground-006 | exterior door; through one way: no start: no floor 0.40 - 0.90 m before the door; the other way: -0.45 m (stopped before the door) | one of the three sliding glass doors (eitherKind, glazed like windows by design, U3-6); it opens onto the glass-walled living area, which has no floor plate in this build (the plate gap above) | option later |
| ground | walk: doors | ground-018 | exterior door; through one way: no start: no floor 0.40 - 0.90 m before the door; the other way: -0.45 m (stopped before the door) | one of the three sliding glass doors (eitherKind, glazed like windows by design, U3-6); it opens onto the glass-walled living area, which has no floor plate in this build (the plate gap above) | option later |
| ground | walk: doors | ground-034 | interior door; through one way: no start: no floor 0.40 - 0.90 m before the door; the other way: no start: no floor 0.40 - 0.90 m before the door | in the small east building, which gets no floor plate from the room rule | option later |
| ground | walk: glass | ground glass 18 | walked from side -1: stopped at 1 m, by ground glass:follow at 0.98 m | a second glass line 0.98 m in front of the probed pane stops the walk: glass still stops you, one line early | accepted difference |
| upper | walk: glass | upper glass 44 | walked from side 1: stopped at None m, nothing ahead (no start on a floor) | its probe spot is the 1.03 m2 area inside a railing that the plate rule left out (a plate-dropped flag) | option later |


## 3. The suite (A-5): `layout presidential test.dwg` against `presidential-suite` v1

Settings `fixtures/upload/settings/suite.json`: one area (the detector's), key `suite`, level 0, walls 3.00 m, door head
2.10, `furniture.pieceLayer: 'drawn'`, no fixes. Conversion `loss` as A-3 expects: 8,254 of 142,182 items missing, 4,290
of them in the plan; 15 blocks came out empty or short, the four placed in the suite listed with their inserts (sheet m):
`TG_artiscardio_2d_1283_8`, `_1345_11`, `_1388_13` (the gym machines, on `A-2.Noi That`) and `A$C59a32014` (on
`A-4. Dim`); `COT T7_HA` and the other unplaced blocks listed with no insert; the wall layer `A-1.Netcat - tuong` lost 221
of its 434 items outside the placed blocks. The Files step offers the AutoCAD DXF fallback. The run is `done` and
validated, and the version saves and opens.

* **Furniture (A-5, should):** 127 pieces against the prototype's 120 (+5.8 %, over the 5 % asked); every kind is present
  and plants 12, seats 14, sofas 7, curtains 21, lamps 9, tall cabinets 3, bed, TV, appliances and coffee tables equal
  the prototype's; `other` 50 against 41, sanitary 4 against 5, tables 1 against 2 (U3.md section 6: the design's own
  reading rules): **accepted difference**.
* **The prototype's hand rules** that made low or special parts (`C_WALL`, `CABANA`, `JACUZZI_KERBS`, `NOT_WALLS`,
  `FEATURE_PANEL`, `PARTITION_FACES` / `PARTITION_PANELS`, `BATH_GLASS`; v1 has low 7, post 4, deck 2, builtin 1,
  balustrade 1 parts from them): the upload has none of these kinds (walls, lintels, single-line parts, columns,
  slabs): **check-and-fix later** (this milestone can set items aside, not lower or re-kind them: U-16).
* **Terrace pieces at full height, room names as drawn (with their areas), the slab and balustrade from the general
  rules:** accepted difference. **The gym machines and `A$C59a32014`**: lost in conversion, absent in the prototype too:
  accepted difference (conversion; the AutoCAD DXF fallback).

### Gap report: suite

Prototype: Presidential suite (1 floor(s), 62 parts); upload: Presidential suite (1 floor(s), 50 parts). Drawing coordinates (model + offset + sheetShift). Differences over 0.05 m2, 1 opening or 1 piece are listed below the table.

#### Floor suite (prototype) / suite (upload)

| Metric | Prototype | Upload | Difference |
|---|---|---|---|
| wall area (m2) | 21.22 | 20.04 | sym. difference 9.26 |
| wall runs | 12 | 26 | 14 |
| glass area (m2) | 5.39 | 0.00 | sym. difference 5.39 |
| glass pieces | 15 | 0 | -15 |
| doors | 16 | 15 | -1 |
| windows | 0 | 0 | 0 |
| passages | 6 | 10 | 4 |
| openings matched (centre within 0.2 m) | - | 20 of 25 | 2 prototype openings unmatched |
| lintels | 17 | 13 | -4 |
| sills | 0 | 0 | 0 |
| panes | 0 | 0 | 0 |
| plate area (m2) | 647.57 | 112.79 | sym. difference 534.78 |
| rooms | 16 | 16 | 0 names matched |
| furniture: appliance | 2 | 2 | 0 |
| furniture: bed | 1 | 1 | 0 |
| furniture: coffee-table | 2 | 2 | 0 |
| furniture: curtain | 21 | 21 | 0 |
| furniture: lamp | 9 | 9 | 0 |
| furniture: other | 41 | 50 | 9 |
| furniture: plant | 12 | 12 | 0 |
| furniture: sanitary | 5 | 4 | -1 |
| furniture: seat | 14 | 14 | 0 |
| furniture: sofa | 7 | 7 | 0 |
| furniture: table | 2 | 1 | -1 |
| furniture: tall-cabinet | 3 | 3 | 0 |
| furniture: tv | 1 | 1 | 0 |

#### Differences

| Floor | Metric | Prototype | Upload | Difference | Cause | Class |
|---|---|---|---|---|---|---|
| suite | wall area | 21.22 | 20.04 | 9.26 m2 symmetric difference | the corridor walls on the east side (4.8 m2 at x 201 - 207) lie on room-outline edges and are not built without the outline option; walls at x 177 - 181 that the prototype's hand rules made low or built-in parts (C_WALL, CABANA, JACUZZI_KERBS) are full walls here | option now |
| suite | glass area | 5.39 | 0.00 | 5.39 m2 symmetric difference | the north and south facade glass lies on outline edges (not built without the outline option); the octagon faces (GLASS_FACE_IN / OUT on A-4. Dim) and BATH_GLASS were hand rules | option now |
| suite | plate area | 647.57 | 112.79 | 534.78 m2 symmetric difference | the slab from the general rules: without the corridor walls the wall network does not close, so 8 rooms' plates are dropped (5 with every outline accepted); the prototype's slab is the hand-made outline of presidential_test/src/floor_spec.json | accepted difference |
| suite | wall runs | 12 | 26 | +14 | the prototype's hand rules joined or re-kinded runs (C_WALL, CABANA, NOT_WALLS); the general builder keeps each paired run, and NOT_WALLS lines become 1.0 m single-line parts | check-and-fix later |
| suite | glass pieces | 15 | 0 | -15 | as glass area | option now |
| suite | lintels | 17 | 13 | -4 | lintels follow the detector's openings (15 doors, 10 passages) where the prototype had its own list (16 doors, 6 passages) and the FEATURE_PANEL / PARTITION_PANELS hand rules | check-and-fix now |
| suite | doors | 16 | 15 | -1 | the frozen detector's 25 records against the prototype's 22 hand-checked openings (20 match by centre) | check-and-fix now |
| suite | passages | 6 | 10 | +4 | as doors: the detector reads 4 more passages | check-and-fix now |
| suite | openings matched | 22 | 25 | 20 matched by centre | as doors | check-and-fix now |
| suite | rooms | 16 | 16 | Bar, Foyer, Gym & Yoga, Jacuzzi, Kitchen, Living & Dining, Massage, Master Bath | room names as drawn, with their areas ('Bar 7,6m2', 'Foyer 10m2'); the prototype tidied them by hand; 16 rooms both | accepted difference |
| suite | furniture: other | 41 | 50 | +9 | U3.md section 6: blocks holding chairs are walked into under pieceLayer 'drawn', 34 loose-shape boxes against 30 (the settings' box is the detector's area), three blocks on A-4. Dim (an 'other' layer) | accepted difference |
| suite | furniture: sanitary | 5 | 4 | -1 | as furniture: other (one piece read inside a walked-into block) | accepted difference |
| suite | furniture: table | 2 | 1 | -1 | as furniture: other (the meeting table's block walked into: its chairs and table become parts) | accepted difference |


#### Walk checks (A-6)

1 failing probes (loads ok; start ok; floors ok; walls ok (40); doors 1 failing of 15; glass no glass to probe).

| Floor | Probe | Id | Detail | Cause | Class |
|---|---|---|---|---|---|
| suite | walk: doors | suite-025 | interior door; through one way: no start: no floor 0.40 - 0.90 m before the door; the other way: no start: no floor 0.40 - 0.90 m before the door | no floor plate on either side: the slab from the general rules leaves those rooms out (8 plates dropped; 5 with the outlines accepted) | accepted difference |


### The second suite row (should): every outline suggestion accepted

The same drawing and settings with `options.outlineWalls: 'suggest'`: the first build flags 26 free room-outline edges
(20 walls, 6 glass; 67.8 m, U-10.5's measurement); all 26 accepted as offered (`fixes.outlineEdges`) and rebuilt: 71
parts against 50, one outline flag left, 5 plates dropped against 8. The corridor walls come in, but accepting EVERY
edge overshoots (wall area 27.43 against the prototype's 21.22 m2): some outline edges are open or glazed in the
prototype, so staff accept them one by one on the Check step.

### Gap report: suite-outlines

Prototype: Presidential suite (1 floor(s), 62 parts); upload: Presidential suite (1 floor(s), 71 parts). Drawing coordinates (model + offset + sheetShift). Differences over 0.05 m2, 1 opening or 1 piece are listed below the table.

#### Floor suite (prototype) / suite (upload)

| Metric | Prototype | Upload | Difference |
|---|---|---|---|
| wall area (m2) | 21.22 | 27.43 | sym. difference 12.73 |
| wall runs | 12 | 40 | 28 |
| glass area (m2) | 5.39 | 0.44 | sym. difference 5.06 |
| glass pieces | 15 | 6 | -9 |
| doors | 16 | 15 | -1 |
| windows | 0 | 0 | 0 |
| passages | 6 | 10 | 4 |
| openings matched (centre within 0.2 m) | - | 20 of 25 | 2 prototype openings unmatched |
| lintels | 17 | 14 | -3 |
| sills | 0 | 0 | 0 |
| panes | 0 | 0 | 0 |
| plate area (m2) | 647.57 | 145.86 | sym. difference 502.43 |
| rooms | 16 | 16 | 0 names matched |
| furniture: appliance | 2 | 2 | 0 |
| furniture: bed | 1 | 1 | 0 |
| furniture: coffee-table | 2 | 2 | 0 |
| furniture: curtain | 21 | 21 | 0 |
| furniture: lamp | 9 | 9 | 0 |
| furniture: other | 41 | 50 | 9 |
| furniture: plant | 12 | 12 | 0 |
| furniture: sanitary | 5 | 4 | -1 |
| furniture: seat | 14 | 14 | 0 |
| furniture: sofa | 7 | 7 | 0 |
| furniture: table | 2 | 1 | -1 |
| furniture: tall-cabinet | 3 | 3 | 0 |
| furniture: tv | 1 | 1 | 0 |

#### Differences

| Floor | Metric | Prototype | Upload | Difference | Cause | Class |
|---|---|---|---|---|---|---|
| suite | wall area | 21.22 | 27.43 | 12.73 m2 symmetric difference | every outline suggestion accepted as offered (26 edges: 20 walls, 6 glass): the corridor walls come in, but edges the prototype left open or glazed become 0.20 m walls too (27.43 against 21.22 m2); on the Check step staff accept them one by one | check-and-fix now |
| suite | glass area | 5.39 | 0.44 | 5.06 m2 symmetric difference | the 6 accepted glass edges give 0.44 m2 of 0.02 m panes; the facade glass of the prototype was a hand rule with its own thickness (GLASS_FACE_IN / OUT, BATH_GLASS) | check-and-fix later |
| suite | plate area | 647.57 | 145.86 | 502.43 m2 symmetric difference | the slab from the general rules: without the corridor walls the wall network does not close, so 8 rooms' plates are dropped (5 with every outline accepted); the prototype's slab is the hand-made outline of presidential_test/src/floor_spec.json | accepted difference |
| suite | wall runs | 12 | 40 | +28 | the 20 accepted wall edges are runs of their own, on top of the hand-rule runs of the first row | check-and-fix later |
| suite | glass pieces | 15 | 6 | -9 | as glass area | check-and-fix later |
| suite | lintels | 17 | 14 | -3 | lintels follow the detector's openings (15 doors, 10 passages) where the prototype had its own list (16 doors, 6 passages) and the FEATURE_PANEL / PARTITION_PANELS hand rules | check-and-fix now |
| suite | doors | 16 | 15 | -1 | the frozen detector's 25 records against the prototype's 22 hand-checked openings (20 match by centre) | check-and-fix now |
| suite | passages | 6 | 10 | +4 | as doors: the detector reads 4 more passages | check-and-fix now |
| suite | openings matched | 22 | 25 | 20 matched by centre | as doors | check-and-fix now |
| suite | rooms | 16 | 16 | Bar, Foyer, Gym & Yoga, Jacuzzi, Kitchen, Living & Dining, Massage, Master Bath | room names as drawn, with their areas ('Bar 7,6m2', 'Foyer 10m2'); the prototype tidied them by hand; 16 rooms both | accepted difference |
| suite | furniture: other | 41 | 50 | +9 | U3.md section 6: blocks holding chairs are walked into under pieceLayer 'drawn', 34 loose-shape boxes against 30 (the settings' box is the detector's area), three blocks on A-4. Dim (an 'other' layer) | accepted difference |
| suite | furniture: sanitary | 5 | 4 | -1 | as furniture: other (one piece read inside a walked-into block) | accepted difference |
| suite | furniture: table | 2 | 1 | -1 | as furniture: other (the meeting table's block walked into: its chairs and table become parts) | accepted difference |


#### Walk checks (A-6)

1 failing probes (loads ok; start ok; floors ok; walls ok (40); doors 1 failing of 15; glass ok (2 probes + 2 random parts)).

| Floor | Probe | Id | Detail | Cause | Class |
|---|---|---|---|---|---|
| suite | walk: doors | suite-025 | interior door; through one way: no start: no floor 0.40 - 0.90 m before the door; the other way: no start: no floor 0.40 - 0.90 m before the door | no floor plate on either side: the slab from the general rules leaves those rooms out (8 plates dropped; 5 with the outlines accepted) | accepted difference |


## 4. The tower (A-5): `L29.dwg`, `L30.dwg` (no prototype model)

Settings `fixtures/upload/settings/tower.json`: whole files, keys `L29` / `L30`, levels 0.00 / 4.00 and walls 4.00 m
(assumed and stated: the drawings give none), alignment `origin` (shared origin: three linked Revit models at 0,0), no
fixes. Uploaded as a new project of the office `acceptance-revit` that the bank re-upload had just saved (A-8): the
thirteen layers of U-8.4 came `from: 'office'`. Conversion `ok` both (0 missing; 248 / 261 hatch messages); units mm
(19 / 17 doors agree). The run is `done` and validated (the walls whose 2.1 m2 hole touched their outline are cut in
two, U3.md 5), and the version saves and opens.

| Floor | Parts | Walls | Glass | Single-line | Lintels | Columns | Slabs | Doors | Windows | Passages | Furniture |
|---|---|---|---|---|---|---|---|---|---|---|---|
| L29 | 115 | 24 | 49 | 20 | 15 | 5 | 2 | 24 | 0 | 7 | 144 (seats 62, sanitary 26, cabinets 13, sofas 12, other 10, tables 7, coffee tables 7, tall cabinets 7) |
| L30 | 118 | 32 | 43 | 19 | 19 | 3 | 2 | 20 | 2 | 12 | 126 (seats 73, sanitary 24, tables 8, cabinets 7, other 7, sofas 6, plant 1) |

The openings are exactly the frozen detector's (31 + 34 records = `detector/output/l29_openings.json`,
`l30_openings.json`, `floor` aside): the detector scored 72 % held out on this drawing (28 Oct: 54 of 54 after the fix
round, a development-set figure), so every doubtful one is flagged: **check-and-fix now** (the opening editor), reviewed by
count. Flags: 98, 66 to check: 27 openings, 39 single-line parts (lines on the wall layers with no partner face, built as
1.00 m items: set aside on the Check step where they are not walls), 21 plates dropped (areas inside railings), 11 grey
furniture families.

### Walk checks (A-6, should pass)

11 failing probes (loads ok, start ok, floors ok, walls ok (80), doors 7 failing of 44, glass 4 failing of 13 probes + 7 random parts).

| Floor | Probe | Id | Detail | Cause | Class |
|---|---|---|---|---|---|
| L29 | walk: doors | L29-001 | interior door; through one way: no start: no floor 0.40 - 0.90 m before the door; the other way: no start: no floor 0.40 - 0.90 m before the door | no floor on either side: the bank rule drops plate areas inside railings (21 plate-dropped flags) | option later |
| L29 | walk: doors | L29-016 | interior door; through one way: no start: no floor 0.40 - 0.90 m before the door; the other way: no start: no floor 0.40 - 0.90 m before the door | no floor on either side: the bank rule drops plate areas inside railings (21 plate-dropped flags) | option later |
| L29 | walk: doors | L29-025 | interior door; through one way: no start: no floor 0.40 - 0.90 m before the door; the other way: no start: no floor 0.40 - 0.90 m before the door | no floor on either side: the bank rule drops plate areas inside railings (21 plate-dropped flags) | option later |
| L29 | walk: doors | L29-026 | interior door; through one way: -0.1 m (stopped before the door); the other way: -0.55 m (stopped before the door) | something solid in the doorway stops you before the door line: a single-line part or a detected door over a wall end (the detector scored 72 % held out on this drawing) | check-and-fix now |
| L29 | walk: doors | L29-028 | interior door; through one way: no start: no floor 0.40 - 0.90 m before the door; the other way: no start: no floor 0.40 - 0.90 m before the door | no floor on either side: the bank rule drops plate areas inside railings (21 plate-dropped flags) | option later |
| L30 | walk: doors | L30-033 | interior door; through one way: no start: no floor 0.40 - 0.90 m before the door; the other way: no start: no floor 0.40 - 0.90 m before the door | no floor on either side: the bank rule drops plate areas inside railings (21 plate-dropped flags) | option later |
| L30 | walk: doors | L30-034 | interior door; through one way: -0.1 m (stopped before the door); the other way: -0.55 m (stopped before the door) | something solid in the doorway stops you before the door line: a single-line part or a detected door over a wall end (the detector scored 72 % held out on this drawing) | check-and-fix now |
| L30 | walk: glass | L30-032 | walked from side 1: stopped at None m, nothing ahead (no start on a floor) | no floor beside the glass (plates dropped) | option later |
| L30 | walk: glass | L30 glass 19 | walked from side 1: stopped at 0.65 m, by L30 solid:follow at 0.33 m | a solid part 0.33 m in front of the glass stops the walk first | check-and-fix now |
| L30 | walk: glass | L30 glass 24 | walked from side 1: stopped at None m, nothing ahead (no start on a floor) | no floor beside the glass (plates dropped) | option later |
| L30 | walk: glass | L30 glass 26 | walked from side 1: stopped at None m, nothing ahead (no start on a floor) | no floor beside the glass (plates dropped) | option later |


## 5. A new drawing from the 3D team (A-12, should): `presidential suite_layout.dwg`, the Revit export of 9 Nov

The 3D team's Revit export (2,280,952 B, AC1032), never seen by the builder or the detector, went through the app's own
upload path twice: as **version 2 of the seeded `presidential-suite`** and as a **new project `suite-revit`** of the
office `dwp-revit`. Settings: the proposal, the office mapping's roles (`dwp-revit`; on the new project they came from
the office at the prepare, 21 layers `from: 'office'`; on the seeded project, which has no office, they were applied as
staff would on the Layers step), `M_Arredi` set to furniture, one floor at level 0.00 with 3.00 m walls (whole file: the
reader proposed one plan, `a1`, 25 x 14 m), the units confirmed on the Files step (the header says inches, its 7 doors say
millimetres: read in mm, as the main session's preview found), no fixes.

* **Conversion:** `ok`, nothing missing (40,683 entities; 264 hatch-short-handles, 145 handle-not-found, 11
  unstable-class, 5 unhandled-class lines). Prepare 32.8 s (convert 1.8 s, check 13.9 s, read 15.7 s; peak 273 MB).
* **Read:** one plan area; no level tags, no grid labels; 9 room names on `A-ANNO-IDEN`; units mm.
* **Build, save, viewer, downloads:** both builds `done` (8.3 s and 8.8 s) and validated; both versions saved; the Max
  script (`.ms` line 2 = the stamp) and the furniture CSV download; the offline files open from disk (walk checks below).
  The two models are the same build apart from the frame and names (35 parts, 25 openings, 81 furniture pieces, 6 rooms).

**What the build is missing, and why (the causes, for the owner):**

1. **The interior walls are on layer `0`.** The export puts the suite's partitions at the top level on layer `0`
   (2,634 items: 99 solid fills, 84 wall-like line pairs, 1,640 lines, 787 arcs over the whole suite), which the office
   mapping and the proposal leave as `other`. Only `A-WALL` is built as walls (8.4 m2 at the floor, against the 19 Oct
   suite's 21.2 m2): the facade, the columns and a few walls stand; the bedrooms, bathroom and living area have no
   partitions. Tried once (a build of the new project's recipe with layer `0` set to `wall`, not saved): 126 parts (47
   walls, 23 glass, 13 lintels), 37 openings (14 doors, 15 windows, 8 passages), walls 35.2 m2 and a plate of 175 m2,
   so the partitions are there, but with 42 single-line items (layer `0`'s other line work) to set aside on the Check
   step. **Check-and-fix now** (map layer `0` to wall, set the single lines aside) or **option later** (walls found by
   shape on a mixed layer, U-16). Any Revit export whose partitions come out on layer `0` will do the same: worth
   asking the 3D team to export with the walls on their own layer (the 19 Oct "cleaner version ... with walls on their
   own layer" built with no hand fixes).
2. **The floor plate is 35 m2** (5 plates dropped): the bank's room rule needs a closed wall network, which item 1
   leaves open. Same cause, same class.
3. **Furniture: 81 pieces in 7 kinds**: curtains 24, sanitary 12, cabinets 9, TV 2, lamps 2, appliance 1 and `other`
   31 (16 loose shapes on `I-FURN`, 8 `Gruppo-19`, 6 loose shapes on `A-GENM`, 1 on `M_Arredi`). No bed, sofa, seat or
   table kind: the Revit family names of this export are not in the furniture vocabulary, so they fall to grey `other`
   (4 grey-furniture flags): **check-and-fix now** (pick a kind for each grey family on the Check step).
4. **The frame of the new version:** `presidential-suite` has no `project-settings.json`, so its new version keeps
   v1's offset `[190.523, -3494.655]` (U-9.6, by design) although the new drawing is in another frame: the model sits
   about 3.5 km from the origin (it builds, renders and walks; the Max script still places it at the drawing's own
   coordinates). The new project gets the bank rule's offset `[13.329, 6.575]`. For a re-drawn project staff should
   reset the offset on the Floors step; the diff against v1 compares two different sheets.
5. **Openings, from the frozen detector with no tuning** (for a later held-out scoring against an answer key made
   without the detector): 25 records: 9 doors (8 hinged single 0.70 - 0.98 m, 1 hinged double 1.80 m), 15 sliding windows
   in the five facade bays (three per bay: 1.417, 0.807, 0.807 m), 1 passage (0.80 m).

| Id | Kind | Subtype | Width (m) | a (drawing m) | b (drawing m) | Confidence |
|---|---|---|---|---|---|---|
| L1-001 | passage | open | 0.8 | [13.89, 1.11] | [14.69, 1.11] | 0.5 |
| L1-002 | door | hinged single | 0.85 | [16.19, 1.11] | [17.04, 1.11] | 0.9 |
| L1-003 | door | hinged double | 1.8 | [17.04, 3.43] | [15.24, 3.43] | 0.8 |
| L1-004 | door | hinged single | 0.9 | [23.99, 0.93] | [24.89, 0.93] | 0.65 |
| L1-005 | door | hinged single | 0.865 | [13.32, 3.31] | [14.19, 3.3] | 0.5 |
| L1-006 | door | hinged single | 0.98 | [15.17, 3.31] | [14.19, 3.3] | 0.65 |
| L1-007 | door | hinged single | 0.7 | [11.71, 3.23] | [12.41, 3.24] | 0.5 |
| L1-008 | door | hinged single | 0.7 | [20.57, 5.16] | [20.56, 4.46] | 0.5 |
| L1-009 | door | hinged single | 0.7 | [20.76, 3.39] | [21.46, 3.38] | 0.5 |
| L1-010 | door | hinged single | 0.9 | [11.51, 3.75] | [11.51, 4.65] | 0.5 |
| L1-011 | window | sliding | 1.417 | [5.3, 13.03] | [4.07, 12.32] | 0.4 |
| L1-012 | window | sliding | 0.807 | [6.13, 12.84] | [5.35, 13.05] | 0.4 |
| L1-013 | window | sliding | 0.807 | [3.76, 11.52] | [3.97, 12.3] | 0.4 |
| L1-014 | window | sliding | 1.417 | [9.67, 13.03] | [8.44, 12.32] | 0.4 |
| L1-015 | window | sliding | 0.807 | [10.51, 12.84] | [9.73, 13.05] | 0.4 |
| L1-016 | window | sliding | 0.807 | [8.13, 11.52] | [8.34, 12.3] | 0.4 |
| L1-017 | window | sliding | 1.417 | [14.05, 13.03] | [12.82, 12.32] | 0.4 |
| L1-018 | window | sliding | 0.807 | [14.88, 12.84] | [14.1, 13.05] | 0.4 |
| L1-019 | window | sliding | 0.807 | [12.51, 11.52] | [12.72, 12.3] | 0.55 |
| L1-020 | window | sliding | 1.417 | [18.42, 13.03] | [17.19, 12.32] | 0.4 |
| L1-021 | window | sliding | 0.807 | [19.26, 12.84] | [18.48, 13.05] | 0.4 |
| L1-022 | window | sliding | 0.807 | [16.88, 11.52] | [17.09, 12.3] | 0.4 |
| L1-023 | window | sliding | 1.417 | [22.8, 13.03] | [21.57, 12.32] | 0.4 |
| L1-024 | window | sliding | 0.807 | [23.63, 12.84] | [22.85, 13.05] | 0.4 |
| L1-025 | window | sliding | 0.807 | [21.26, 11.52] | [21.47, 12.3] | 0.55 |

Against the 19 Oct suite model (`presidential-suite` v1, the older drawing of a different, larger layout: 16 rooms against
the new drawing's 9 names): walls 8.4 against 21.2 m2 (11 runs against 12), glass 18 pieces (0.96 m2) against 15 (5.39
m2), doors 9 against 16, windows 15 against 0, passages 1 against 6, rooms 6 against 16 (`LIVING & DINING AREA`, `MASTER
BEDROOM`, `MASTER BATHROOM`, `BEDROOM FOYER`, `BEDROOM 2`, `FOYER`; `BOH.`, `BAR` and `FHC` gave no room: two are flagged
room labels), furniture 81 in 7 kinds against 120 in 13. New in this drawing: curtain-wall bays with sliding sashes
(`A-GLAZ-CURT`, `A-GLAZ-CWMG`), casework (`Q-CASE` 22,841 items, `Q-SPCQ`), lighting (`E-LITE-EQPM`), mechanical
(`M-EQPM`), Revit element ids on every block. The areas below are compared in each drawing's own coordinates, which do
not overlap (two different sheets), so only the counts mean anything.

### Gap report: a12-new

Prototype: Presidential suite (1 floor(s), 62 parts); upload: Presidential suite (Revit export, 9 Nov) (1 floor(s), 35 parts). Drawing coordinates (model + offset + sheetShift). Differences over 0.05 m2, 1 opening or 1 piece are listed below the table.

#### Floor suite (prototype) / L1 (upload)

| Metric | Prototype | Upload | Difference |
|---|---|---|---|
| wall area (m2) | 21.22 | 8.40 | sym. difference 29.63 |
| wall runs | 12 | 11 | -1 |
| glass area (m2) | 5.39 | 0.96 | sym. difference 6.35 |
| glass pieces | 15 | 18 | 3 |
| doors | 16 | 9 | -7 |
| windows | 0 | 15 | 15 |
| passages | 6 | 1 | -5 |
| openings matched (centre within 0.2 m) | - | 0 of 25 | 22 prototype openings unmatched |
| lintels | 17 | 4 | -13 |
| sills | 0 | 0 | 0 |
| panes | 0 | 0 | 0 |
| plate area (m2) | 647.57 | 35.10 | sym. difference 682.67 |
| rooms | 16 | 6 | 0 names matched |
| furniture: appliance | 2 | 1 | -1 |
| furniture: bed | 1 | 0 | -1 |
| furniture: cabinet | 0 | 9 | 9 |
| furniture: coffee-table | 2 | 0 | -2 |
| furniture: curtain | 21 | 24 | 3 |
| furniture: lamp | 9 | 2 | -7 |
| furniture: other | 41 | 31 | -10 |
| furniture: plant | 12 | 0 | -12 |
| furniture: sanitary | 5 | 12 | 7 |
| furniture: seat | 14 | 0 | -14 |
| furniture: sofa | 7 | 0 | -7 |
| furniture: table | 2 | 0 | -2 |
| furniture: tall-cabinet | 3 | 0 | -3 |
| furniture: tv | 1 | 2 | 1 |

#### Differences

| Floor | Metric | Prototype | Upload | Difference | Cause | Class |
|---|---|---|---|---|---|---|
| L1 | wall area | 21.22 | 8.40 | 29.63 m2 symmetric difference | the suite's partitions are on layer 0 in this export (99 solid fills, 84 wall-like pairs), left as other; and the two drawings are different sheets, so their areas do not overlap | option later |
| L1 | glass area | 5.39 | 0.96 | 6.35 m2 symmetric difference | a different drawing: the new suite's curtain-wall bays (A-GLAZ-CURT, A-GLAZ-CWMG) against the old suite's hand-made facade glass | accepted difference |
| L1 | plate area | 647.57 | 35.10 | 682.67 m2 symmetric difference | the wall network does not close without the partitions on layer 0 (5 plates dropped); the old suite's slab was hand-made | option later |
| L1 | wall runs | 12 | 11 | -1 | as wall area: only A-WALL is built | option later |
| L1 | glass pieces | 15 | 18 | +3 | as glass area | accepted difference |
| L1 | lintels | 17 | 4 | -13 | a different drawing (9 doors and 1 passage against 16 and 6) | accepted difference |
| L1 | doors | 16 | 9 | -7 | a different drawing; the frozen detector's records, untuned (listed above for a held-out scoring) | accepted difference |
| L1 | windows | 0 | 15 | +15 | the new drawing's 15 sliding sashes in five curtain-wall bays | accepted difference |
| L1 | passages | 6 | 1 | -5 | a different drawing | accepted difference |
| L1 | openings matched | 22 | 25 | 0 matched by centre | two different sheets: no centre can match | accepted difference |
| L1 | rooms | 16 | 6 | Bar, Foyer, Gym & Yoga, Jacuzzi, Kitchen, Living & Dining, Massage, Master Bath | a different layout: 9 room names, 6 made rooms (BOH., BAR, FHC gave none) | accepted difference |
| L1 | furniture: appliance | 2 | 1 | -1 | a different drawing | accepted difference |
| L1 | furniture: bed | 1 | 0 | -1 | this export's Revit family names are not in the furniture vocabulary: beds, sofas, seats and tables fall to grey other | check-and-fix now |
| L1 | furniture: cabinet | 0 | 9 | +9 | a different drawing: casework (Q-CASE) read as cabinets | accepted difference |
| L1 | furniture: coffee-table | 2 | 0 | -2 | as furniture: bed | check-and-fix now |
| L1 | furniture: curtain | 21 | 24 | +3 | a different drawing | accepted difference |
| L1 | furniture: lamp | 9 | 2 | -7 | a different drawing | accepted difference |
| L1 | furniture: other | 41 | 31 | -10 | grey families (Gruppo-19) and loose shapes on I-FURN, A-GENM, M_Arredi | check-and-fix now |
| L1 | furniture: plant | 12 | 0 | -12 | a different drawing: no plant blocks | accepted difference |
| L1 | furniture: sanitary | 5 | 12 | +7 | a different drawing (P-SANR-FIXT) | accepted difference |
| L1 | furniture: seat | 14 | 0 | -14 | as furniture: bed | check-and-fix now |
| L1 | furniture: sofa | 7 | 0 | -7 | as furniture: bed | check-and-fix now |
| L1 | furniture: table | 2 | 0 | -2 | as furniture: bed | check-and-fix now |
| L1 | furniture: tall-cabinet | 3 | 0 | -3 | a different drawing | accepted difference |
| L1 | furniture: tv | 1 | 2 | +1 | a different drawing | accepted difference |


#### Walk checks (A-6)

3 failing probes (loads ok; start ok; floors ok; walls ok (40); doors 3 failing of 9; glass no glass to probe).

| Floor | Probe | Id | Detail | Cause | Class |
|---|---|---|---|---|---|
| L1 | walk: doors | L1-004 | interior door; through one way: no start: no floor 0.40 - 0.90 m before the door; the other way: no start: no floor 0.40 - 0.90 m before the door | no floor plate around the door: the partitions on layer 0 leave the wall network open, so only 35 m2 of plate is built | option later |
| L1 | walk: doors | L1-008 | interior door; through one way: no start: no floor 0.40 - 0.90 m before the door; the other way: no start: no floor 0.40 - 0.90 m before the door | no floor plate around the door: the partitions on layer 0 leave the wall network open, so only 35 m2 of plate is built | option later |
| L1 | walk: doors | L1-010 | interior door; through one way: no start: no floor 0.40 - 0.90 m before the door; the other way: no start: no floor 0.40 - 0.90 m before the door | no floor plate around the door: the partitions on layer 0 leave the wall network open, so only 35 m2 of plate is built | option later |


### Walk checks of version 2 of `presidential-suite` (the same model in the old frame)

4 failing probes (loads ok; start ok; floors ok; walls no start spot found (0 of 40 tried); doors 3 failing of 9; glass no glass to probe).

| Floor | Probe | Id | Detail | Cause | Class |
|---|---|---|---|---|---|
| suite | walk: walls | walls-1 | {"tried": 0, "wentThrough": 0, "endedInsideWall": 0} | the walk sampler found no start spot on this version, which keeps v1 offset and sits 3.5 km from the origin (UI-3); the same model in its own frame (suite-revit v1) passes 40 of 40 | accepted difference |
| suite | walk: doors | suite-004 | interior door; through one way: no start: no floor 0.40 - 0.90 m before the door; the other way: no start: no floor 0.40 - 0.90 m before the door | no floor plate around the door: the partitions on layer 0 leave the wall network open, so only 35 m2 of plate is built | option later |
| suite | walk: doors | suite-008 | interior door; through one way: no start: no floor 0.40 - 0.90 m before the door; the other way: no start: no floor 0.40 - 0.90 m before the door | no floor plate around the door: the partitions on layer 0 leave the wall network open, so only 35 m2 of plate is built | option later |
| suite | walk: doors | suite-010 | interior door; through one way: no start: no floor 0.40 - 0.90 m before the door; the other way: no start: no floor 0.40 - 0.90 m before the door | no floor plate around the door: the partitions on layer 0 leave the wall network open, so only 35 m2 of plate is built | option later |

