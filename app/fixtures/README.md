# Shared fixtures (read-only for builders)

Made by the scaffold on 3 Nov 2026 (DESIGN.md 17.1, WORK_BREAKDOWN S.8). Nobody edits these files; a builder who needs
another fixture adds it in its own folder (`packages/viewer/test/fixtures/`, `services/api/tests/`). Paths of sources are
relative to the project folder (`..` from `app/`). sha1 = the whole file's.

## models/ (BuiltModel v1; every file valid against `docs/built-model.schema.json` with ajv strict and jsonschema, and against the strict 5.6 rules)

| File | Source | How | sha1 |
|---|---|---|---|
| `bank-v1.model.json` | `bank_test/previous_before_fix_round_2026-10-27/src/bank_model.json` | copied byte for byte (stamp 4b02dc17f286) | `4b02dc17f286db688a55f0784d0b2fbb5642cb79` |
| `bank-v2.model.json` | `bank_test/src/bank_model.json` | copied byte for byte (stamp c3a9408304a2) | `c3a9408304a240b83c36f5c5c53db56b50a72c64` |
| `hotel.model.json` | `hotel_test/src/hotel_model.json` | copied byte for byte (stamp 6ab030750886); used as drawn (18.27) | `6ab03075088689f7b694f71c422927a289a7005e` |
| `suite.model.json` | `presidential_test/src/pres2_model.json` | **provisional**: `python -B docs/reference/provisional_v1.py --prototypes .. --out fixtures/models` (system Python 3.14.3; DESIGN.md 6.3): floors 1, parts 62, openings 22, probes 1, rooms 16, furniture 120 (13 kinds) | `34a02b1f6a28d8dce7ce660f720ea418f45b8f36` |
| `house.model.json` | `cad_test/src/house3d_merged.json` + `furniture_house.json` | **provisional**, same run (DESIGN.md 6.4): floors 2, parts 197, openings 86, probes 0, rooms 0, furniture 76 (9 kinds) | `e43270cc0c9be5c00025881f09762325cfc5f92f` |
| `mini.model.json` | `furniture/fixtures/mini_model.json` | **provisional**, same run (DESIGN.md 17.1): floors 2, parts 4, openings 3, furniture 17 (10 kinds) | `a469ffbe5a934e0d05a5ef7be6bd3dd83fbec45c` |

### models/broken/ (`node tools/make-broken-fixtures.mjs`, from `bank-v2.model.json`, one fault per file)

`broken/expected.json` names, per file, the JSON Pointer every checker must report (it may report more), whether the
viewer throws or only warns (the four furniture rules, DESIGN.md 5.6), and the fault. The tool checks each case before it
writes: the schema cases fail ajv (Ajv2020, strict) at exactly that path; the cross cases pass the schema and break exactly
one strict 5.6 rule. Checked again with Python jsonschema 4.26.0 (same paths) and with the architect's `cross_issues` in
`docs/reference/provisional_v1.py` (same paths, except that it names a duplicate id `/openings`, see conventions).
Conventions: a missing property is reported at its parent object (as ajv and jsonschema do); a duplicate at its **later**
occurrence (`/openings/5/id`); the unknown-kind case also lowers its old kind's count by one, so the counts still agree.

| File | Path | Viewer | sha1 |
|---|---|---|---|
| `schema/wrong-type.json` | `/parts/3/z1` | throws | `8db815cb2738009cfb2aca598af322926ff7ff82` |
| `schema/missing-field.json` | `/floors/1` | throws | `63ecba9fc85b66434f204de02fce1634937a3a92` |
| `schema/bad-pattern.json` | `/photoName` | throws | `978e283436cf406fb64f3f790208f4491297bdaa` |
| `schema/pattern-trailing-newline.json` (fix step, 4 Nov: photoName ends in `\n`; plain jsonschema took it) | `/photoName` | throws | `bf69d21544585d091249d8010056c7c295969b63` |
| `cross/unknown-floor.json` | `/parts/10/floor` | throws | `dd66decd2020f61ad19b071f5a949e9946af11f8` |
| `cross/duplicate-opening-id.json` | `/openings/5/id` | throws | `9a6d1d3cb694bec6c298cea1316bbebb71760c67` |
| `cross/z1-not-above-z0.json` | `/parts/3/z1` | throws | `591a095526490860c1234688cf0f61fd5bd0f750` |
| `cross/stair-6-numbers.json` | `/stairs/L1/below` | throws | `ae86ec7036fe8297d7ed8deb796bcbdc42d57c23` |
| `cross/furniture-unknown-kind.json` | `/furniture/0/kind` | warns | `adfcb7b8f42757e6ef7f2eacdd4df32e2a3db643` |
| `cross/furniture-missing-support.json` | `/furniture/3/on` | warns | `8816c8484c00778c64b9fa4264bb7699637b1e1e` |
| `cross/furniture-unknown-approach.json` | `/furniture/28/approach/0` | warns | `712b78cacd714e1b69305509b9ff74b3126824d9` |
| `cross/furniture-count.json` | `/furnitureKinds/0/count` | warns | `81a3df3dfcfebdfb2917592982f7dadaa1069bef` |
| `expected.json` | the manifest | | `a3294ba91c99e1c5396ca11aebf019acee6a4ba9` |

## stages/, pictures/ (copied byte for byte)

| File | Source | sha1 |
|---|---|---|
| `stages/bank-v1.stages.json` | `bank_test/previous_before_fix_round_2026-10-27/src/bank_stages.json` | `55810657defd4e2c5f80d737f6bd41195b85c579` |
| `stages/bank-v2.stages.json` | `bank_test/src/bank_stages.json` | `c7c01b67e97335ea3103179175534af919ae4aa8` |
| `pictures/floor1_plan.png` | `hotel_test/source/floor1_plan.png` | `be89e58da9b32c1fc9a2544f2d3a07f6c70811bf` |
| `pictures/floor2_plan.png` | `hotel_test/source/floor2_plan.png` | `1d6a3c99ee931a26680e56f9646acad17052584d` |

## csv/ (all with the byte-order mark, as downloaded; `csv()` / `furnitureCsv()` give the bytes after it)

| File | Source / how | sha1 |
|---|---|---|
| `bank-v2.csv` | `bank_test/bank_furniture_list.csv`, copied | `b528bb2320ef4a5e04ad3c1ad1e04ee09af67861` |
| `suite.csv` | `presidential_test/presidential_furniture_list.csv`, copied | `cd14efa1532588803396a3577ebf21cc047a65c2` |
| `house.csv` | `cad_test/house_furniture_list.csv`, copied | `c21b646f753705189e0d5229c1266c15df4f7b70` |
| `hotel.csv` | `hotel_test/hotel_furniture_list.csv`, copied | `047b56952e5bc070de72eea4a83a8a6df448028d` |
| `bank-v2-typed.csv` | `python -B tools/make-csv-goldens.py` (system Python; `furniture_kit.csv_text` loaded by path, read-only) on `models/bank-v2.model.json` with table 600, seat 300, cabinet 1000 | `2d64136949a63c798c958d0fa162246b00b986f8` |
| `suite-typed.csv` | same, `models/suite.model.json`, table 600, seat 300, other 2100 | `7d916a58110b1e2b02057f488a1096b8b31ff024` |
| `house-typed.csv` | same, `models/house.model.json`, seat 300, cabinet 1000, other 2100 (no table kind) | `7f1ee14654bb8c95df1bffbdbc7d277a4382b83b` |
| `hotel-typed.csv` | same, `models/hotel.model.json`, table 600, seat 300, cabinet 1000 | `975a51f9438c8a79ffba8da3ba38cd85b7476a6f` |

The same run checked that `csv_text` with no typed heights equals each copied prototype CSV byte for byte (all four
equal), and that `furniture/` has no `__pycache__` afterwards.

## prototype/ (facts read from the prototype pages: `npm run capture:prototype`, i.e. `node tools/capture-prototype-facts.mjs --port 9700`)

Headless Edge (SwiftShader), three.js 0.160.0 from the pages' import map (cdn.jsdelivr.net), 3 Nov 2026; the capture
methods of DESIGN.md 17.1 (scene facts with `?build=0&nodownload=1`, the Build settings card with the plain address; tick
sizes by toggling each tick and counting the objects under the floor groups whose `visible` flips, the plan pictures through
`__host.pictures.objs`; the bank v1 camera from `__viewer.probe.camera()` with target, near and far from its generator).
Colliders and late objects are listed without the furniture boxes (`furnitureColliders`, `lateWithoutFurniture`); the
furniture CSV is kept as its sha1 and byte length.

| File | Page | sha1 |
|---|---|---|
| `bank-sampeng-v1.json` | `bank_test/previous_before_fix_round_2026-10-27/bank_3d_preview.html` | `57fe5e983f06851f9325f02046459503463999fb` |
| `bank-sampeng-v2.json` | `bank_test/bank_3d_preview.html` | `4df5b24196415bae31ca1057fb0984a4642a4c8a` |
| `presidential-suite.json` | `presidential_test/presidential_3d_preview.html` | `4d6ebf2375debfea9980b9969362db8aaa7670a1` |
| `sukhumvit-house.json` | `cad_test/house_3d_preview.html` | `1a2f10bb3c52811bd6bb17565e0b7274ece198c1` |
| `hotel-lobby.json` | `hotel_test/hotel_3d_preview.html` | `0052ce3f8d8852227784872f4ee5ca0babcd0517` |
| `house_openings_before.json` | `cad_test/test_house_openings_before.json`, copied | `8185e6f02b3fbafbd96ca317df5656c34bee8cb5` |

The capture time inside each file changes on every run; the facts themselves do not.

### The house: expected v1 values (DESIGN.md 17.2) next to the page's captured ones

| Fact | v1 (three 0.186.1, provisional house model, D-17.2) | Page (captured) | Why they differ |
|---|---|---|---|
| ground colliders | 7 (`solid:follow`, `glass:follow`, `single:own`, `solid:top`, `sill:clip`, `pane:top`, `pane:clip`), 6,936 vertices | 5 (`wall`, `glass`, `single`, `lintels and sills`, `window panes`), **6,936** vertices | grouping: lintels apart from sills, panes split by fit |
| ground walkables | 3 (792 vertices) | 1 (792) | one mesh per slab part, not all plate rings merged |
| ground late | 51 (4 without the boxes) | 49 (2 without) | the 3 slab meshes |
| ground fitted / pieces | 4 | 2 (`lintels and sills`, `window panes`) | grouping |
| upper colliders | 5, 6,372 vertices | 5, **6,372** vertices | the names (grouping) |
| upper walkables | 1 (588) | 1 (588) | - |
| upper late | 31 (2) | 31 (2) | - |
| upper fitted / pieces | 2 | 2 | - |
| ticks: plates / glass / single | 4 / 10 / 4 objects | 2 / 8 / 4 | grouping (slab meshes; panes split by fit, each with its edges) |
| plinths | 3 | 1 | one mesh per plinth slab |

**Not reproduced:** D-17.2 gives the page 6,924 (ground) and 6,348 (upper) collider vertices and puts the 12 + 24 extra
vertices of v1 down to earcut 3.0.2 (three 0.186) against 2.2.4 (three 0.160). The page captured on 3 Nov, which runs
three r160 (checked: `THREE.REVISION` is `160`), already has 6,936 and 6,372, the same totals as the v1 values. The counts
differences (grouping) stand as D-17.2 says; the vertex totals agree. Recorded in `docs/contract-issues/S.md`.

## presentation/ (provisional Presentation v1: `node tools/make-presentation-fixtures.mjs`)

From the captured facts (title, heading, the intro HTML split into `{ text, bold }` runs, legend items and layout, floor
buttons, tick labels, accent) and DESIGN.md 8's fixed values (camera, creaseAngle, partStyles, groundPlane). Optional
fields are written where D-8's table gives a value and left out where it says "default": `floorButtons.labels` only for
buttons whose text differs from the model's floor name, tick `labels` only where they differ from the defaults, `toggles`
nowhere. Compare after filling the defaults (parsePresentation / resolvePresentation).

| File | sha1 |
|---|---|
| `bank-sampeng-v1.json` | `b407af26f4243f43eddc2ef3b506ea2398c9c4c5` |
| `bank-sampeng-v2.json` | `756326eac7a27fd6c9dd791a732f514a3f2e19ac` |
| `presidential-suite.json` | `5ddad039482b03490b48a2f2966f68d1224eabb6` |
| `sukhumvit-house.json` | `6bf06b3bad9007c8776c0594c3086be5f55fa17e` |
| `hotel-lobby.json` | `310a24a0e24d9c48292e4f9ec23607fe5a5633d5` |

## upload/ (the upload milestone; made by its scaffold U0 on 4 Nov 2026, ACCEPTANCE 2.5)

`node tools/run-builder-py.mjs tools/upload/make-fixtures.py [--only settings mapping drawing conversion result runs]`
(no `maxtexts` part since the integration step: U4's profiles are not the tool's to write, U4-5) (the builder Python; reads `WT_REF`, the `make:reference` output, read only; deterministic). Every file passes
the API's record check (`node tools/run-py.mjs -m walkthrough_api.check_file <kind> <file>`) and its type
(`apps/web/test/upload-fixtures.test-d.ts`; `services/builder/tests/test_contracts.py` for the builder's own types).
Owners after the scaffold: `settings/**` U3, `max-texts/**` U4; the provisional drawing, plan and conversion fixtures were
re-made by U2 / U1, who listed the differences in their contract-issues files, and the integration step put the real ones
in their place (9 Nov 2026, `docs/upload/contract-issues/UI.md`). Each settings fixture's derived detector
mapping reproduces `detector/output/<name>_openings.json` record for record, `floor` aside
(`tools/upload/check-derived-mapping.py`: 24, 25, 86, 25, 31, 34 records, all equal). The synthetic drawings
(`tools/upload/make-test-dxf.py small|hostile <out.dxf>`) are made at test time (the root `.gitignore` ignores `*.dxf`):
small `fb8e7283ab205c8e49ecc057f6019c1e9fd2f6d0`, hostile `7d2193d20052ac4171e42d8887270551cfa1d0b8`.

| File | Source | sha1 |
|---|---|---|
| `build-result.bank.json` | contracts.BuildResult of the bank (compact JSON): the v2 model, bank_summary.json, the detector outputs, the stages regrouped, placements found by block and handle in the reference DXFs | `d566a7bea98f069a8591015ca0cf89ff619a1ba0` |
| `conversion/bank1.conversion.json` | ConversionReport of I1201 as the worker publishes it (U1's loss check; positions in sheet m), from the integration step's acceptance prepare (9 Nov): ok, 0 missing; 148 hatch-short-handles, 28 handle-not-found, 9 unstable-class, 2 unhandled-class; no note | `041048a684c43a2c285cfa99824b36abefaef9d7` |
| `conversion/presidential.conversion.json` | ConversionReport of the suite as the worker publishes it (integration, 9 Nov): loss, 8,254 of 142,182 missing (4,290 in the plan); 15 lost blocks, the 4 placed in the plan with their inserts (sheet m) | `555d5b961ec2f1d143e04624f7da33f2cd80c587` |
| `drawing/bank1.drawing.json` | DrawingRead of I1201 made by U2's `read_source` (re-made 9 Nov, U2.md section 4; JSON indented 2) | `a10897178ce720ed3d055724b9e823a3f8450ebb` |
| `drawing/sukhumvit.drawing.json` | DrawingRead of the house made by U2's `read_source` (re-made 9 Nov): 26 level tags (18 on SPEC, 8 on layer 0; the 2 blank marks left out), door votes 28 mm / 4 m, 15 area proposals; its units note re-worded by UR (V2-15) | `c620779c4c42ca366e4fd437c377cad01e58c391` |
| `mappings/dwp-revit.json` | OfficeMapping after the bank is saved for office dwp-revit (every bank layer by normalised name) | `484a50a4b84e8d2dfed5ded65081503e771c8a00` |
| `max-texts/bank-27oct.json` | MaxTexts profile (format max-texts/1, U4's final; U4-4): the bank's verbatim header, tooltip, placed-at and datum lines; with it the generator gives `bank_test/Bangkok_Bank_Sampeng.ms` byte for byte (golden only) | `b04a506c29b8391084bf11c143908035a23817c8` |
| `max-texts/hotel-2nov.json` | MaxTexts profile (U4's final): with it the generator gives `hotel_test/Hotel_Lobby.ms` byte for byte (golden only) | `c203796254960cf6c95c83c849250c5eada5dc93` |
| `max-texts/upload.json` | MaxTexts profile `upload` (U4's final, U-11.5): read AT RUN TIME by every build's Max script, so it ships with the app (U4-4); the rooms milestone's R3 added the `stairs` and `ceilings` notes (sha1 updated by RI) | `4d4ef2dbb195abf52c33b46d64efdbbfaf76ea6b` |
| `overlay/bank.overlay.json` | BuildOverlay of the bank from the v2 model and the detector records (sheet m = model + offset), with the opening, room-label and plate flags the data raise | `01893517d1be77a958ef1cf7bd843084731fcf1c` |
| `plan/bank1.plan.json.gz` | PlanGeometry of I1201 made by U2's `read_source` (nested keys, sig / rsig / eid per entry; gzip, mtime 0): equal to the scaffold's provisional one | `9c7c8ef6a338ebe1ada0913f143750861599e9a3` |
| `plan/sukhumvit.plan.json.gz` | PlanGeometry of the house made by U2's `read_source` (re-made 9 Nov): two ATTRIB keys now carry their source handle | `96a5b105feb1be774735619a356a9faeea92298d` |
| `replay-input.bank.json` | contracts.ReplayInput: build-result.bank.json's `replay` (compact JSON) | `9ad979ad33bfb9f71bcbfb097b21813df3c090ed` |
| `settings/bank.json` | BuildSettings: `bank_test/src/bank_project.json` (roles, names, furniture word Fritz-Hansen) + A-1 (keys L1 / L2, levels 0 / 3.70, wall heights 3.70, whole files) | `c7e09054b4271dec5316eda634d622ee8f2abd46` |
| `settings/house.json` | BuildSettings: `detector/mappings_with_areas/sukhumvit.json` (roles, the two area boxes, pad 0.5, match all) + `cad_test/src/{build3d.py, furniture.json, heights.json}` + A-5 (ground / upper, levels 0.90 / 4.80, wall heights 3.90 / 3.50, door / window 3.00 / 0.00 / 3.00 and 2.60 / 0.00 / 2.60) | `4ddf3bc30096016cae821c6a864241bd93be2940` |
| `settings/small.json` | BuildSettings for the synthetic `make-test-dxf.py small` drawing (its sha1 `fb8e7283ab20...`) | `808dbb4cb919ef55e51fade57bfc2776a83318d2` |
| `settings/suite.json` | BuildSettings: `detector/mappings_with_areas/presidential.json` (roles, area, match any) + `presidential_test/src/furniture.json` + A-5 (suite, level 0, wall height 3.00, door head 2.10, pieceLayer drawn; Defpoints room-outline) | `cc0399ca88b4eddb54b76890e4bf0f72668bd82c` |
| `settings/tower.json` | BuildSettings: `detector/mappings/{l29,l30}.json` + A-5 (L29 / L30 whole files, levels 0 / 4.00, wall heights 4.00, align origin); A-GENM furniture, A-AREA room-outline | `aff02e71d8526dfca2f5f50d6d2c6e4b4592f54f` |

### upload/runs/ (what a FakeJobRunner copies: a prepare and a build of the bank)

`runs/<run>/run.json` lists each output of the run and where its bytes are: `{"fixture": <path under app/>}`,
`{"prototype": <path under the project folder>}` or `{"file": <path under the run folder>}`; `runs/<run>/job.json` is the
JobRecord of the finished run, its `outputs` the sizes and sha1s of exactly those bytes (a test checks it). The build's
model and stages are `fixtures/models/bank-v2.model.json` and `fixtures/stages/bank-v2.stages.json`, its top view and
`.ms` the prototype's (`bank_test/src/bank_topview.png`, `bank_test/Bangkok_Bank_Sampeng.ms`).

| File | sha1 |
|---|---|
| `runs/bank-build/job.json` | `934b5f4ec5b35ff318a77ed1562f60ffd91bbbab` |
| `runs/bank-build/out/diff.json` | `f1443890213a4d7c3d05da0329a75efd93635750` |
| `runs/bank-build/out/inputs.json` | `a9908f5a1bb69e8262630101d8963620c000ebbf` |
| `runs/bank-build/out/openings.json` | `f030b1c1457c1d3a6eefb8a236808f6b107d18a5` |
| `runs/bank-build/out/pieces.json` | `2b596b8ca7c52bf5620a131b98bc513f11c2d4e5` |
| `runs/bank-build/out/presentation.json` | `c994c446162ed528af73461edfe441e4dc3d6bde` |
| `runs/bank-build/out/report.json` | `520bd8081b0a19ec4e84065c49a36a190d66a3bb` |
| `runs/bank-build/run.json` | `0b10ae5d2de760ea92a5c49dc25d3376f434f2fb` |
| `runs/bank-prepare/job.json` | `4178d8728355b93cea803d156d82146594fa9c1e` |
| `runs/bank-prepare/out/proposed-settings.json` | `523360a3855d60a6362214dcfa62b60f79a375c4` |
| `runs/bank-prepare/out/sources/6551bdc6f0cff4e31e83b68a55d22cf42703029a/conversion.json` | `269d79ae7ccd48700bc864935fb594cd9f5c82f5` |
| `runs/bank-prepare/out/sources/6551bdc6f0cff4e31e83b68a55d22cf42703029a/drawing.json` | `30e28f37eca6c1e773768feaa3315c44667e6736` |
| `runs/bank-prepare/out/sources/6551bdc6f0cff4e31e83b68a55d22cf42703029a/plan.json.gz` | `0c81727c9c9c512ab757190269bfe8aefb2cec33` |
| `runs/bank-prepare/out/suggestions.json` | `e79eab9027aaf098c91e77d1d56f070c7655ffcc` |
| `runs/bank-prepare/run.json` | `9480f399ec17f146d309056b4e352fcb55243f1f` |

## The rooms milestone (made by its scaffold R0 on 11 Nov 2026; docs/rooms/ACCEPTANCE.md 2.5)

Read-only for the builders, as everything here. Owners after the scaffold (docs/rooms/WORK_BREAKDOWN.md): R1 the
`*-rooms.json` settings and `rooms/keys/house.json`; R2 `tools/rooms/make-stair-dxf.py`; R5 the FakeJobRunner fixtures;
RI `rooms/keys/suite.json` and the smoke step's replacement of the provisional overlay. Everything derived from the
reference building is frozen with its tool. **Re-made once by the integration step RI (11 Nov 2026, after R1 - R7)**
with the same tools and the same definition, so that what the real code now writes is in them: the rooms' areas, the
stair outlines and the summary's stairs block (R1's `build/model.py` and `bank.py`, contract-issues/R1.md 4.1), R3's
outputs (the finish caption, the Max script, the top view; R3.md 4), and the run folder's `job.json` and this file's
sha1s with them; the house-rooms overlay from a real new-rule build. `docs/rooms/contract-issues/RI.md` lists every
file that moved and why. The overlay, the flags, the presentation, the settings and the other run-folder files did not
move.

### The reference building (`node tools/run-builder-py.mjs tools/rooms/make-reference-building.py fixtures` and `stairs`)

One synthetic building, drawn and described in `tools/rooms/make-reference-building.py`: two floors of 3.00 m; an L
stair S1 of 16 risers with nosing pairs, risers 1 - 12 on the ground plan (UP, a break line) and 12 - 16 on the upper
plan (DN); a second, straight stair drawn with no word, arrow or break line; a 2.9 m opening with no door in an outside
wall (the garage: an unfloored area with a mouth); a door-sized gap of 1.2 m between two wall ends (a doorway closing);
an X void upstairs and an X mark on the lowest floor; a terrace fenced by railings; two names in one room; a cupboard
wall under the stair (a clash cut). Its plans are DXFs made at test time (`... make-reference-building.py dxf <dir>`;
the root `.gitignore` ignores `*.dxf`): `services/builder/tests/rooms_kit.py` `reference_plan()` and conftest's
`reference_building`. The fixtures were built through the app's reader and `build()`, the walls and openings by the
unchanged code and the real door finder, the rooms, plates, holes and stairs from the building's own definition by the
rules of DESIGN R-8 (the tool's text says how). They are the contract for R1 - R7: the builder's output must equal the
model's treads, landings, well and stairway within 1 mm (ACCEPTANCE RA-9).

| File | What | sha1 |
|---|---|---|
| `models/rooms-reference.model.json` | BuiltModel v2: 1 stairway (L, 16 risers of 0.188 m, 14 treads, 1 landing), 3 spaces, 2 ceilings, a wall piece cut under the stair; stamp `bfcd621e0a22` | `bfcd621e0a22de68a0b1e36bcf8242cd54d1343d` |
| `presentation/rooms-reference.json` | its Presentation, as U4's `out/presentation.py` writes it | `eab1b408eb323328b55bf4cb3253b1bf66daedc2` |
| `stages/rooms-reference.stages.json` | its ReplayData | `fab0e3e55ea5dced749980d2df96307f05859f93` |
| `rooms/settings.reference.json` | the BuildSettings it was built with (the two DXFs by sha1, the three options at their new values) | `a712632175fffb8ccb19da57d01f3c146e30c016` |
| `rooms/build-result.reference.json` | contracts.BuildResult with every new report key: `floors[*].rooms / slab / stairways / stairClash`, `fixes.closings / rooms / stairs`, `replay.facts.rooms / climbable / ceilings` (timings zero) | `ee304f37d115c1d2b72c68f72a0c6cf5493d7889` |
| `rooms/overlay.reference.json` | BuildOverlay with the new floor fields (`spaces`, `holes`, `stairs`, `closings`, `unfloored`, sheet m) and the new flags `slab-gap`, `room-open`, `room-names`, `doorway`, `stair`, `stair-clash`, `hole-skipped`, written by the tool from the report with the texts of DESIGN R-6.1 (R3 wrote the real overlay code against it; since RI the tool takes `out/overlay.py`'s own, the same bytes) | `b0949a81e26eb0bc118513b75154ce4177d4ea48` |
| `rooms/flags.every-kind.json` | one Flag of each of the eight new kinds: the seven above and a hand-written `stairs-none` (a building whose stair climbs raises none) | `636a6a428bd02a7f70ab976d52c2cade70ad4355` |
| `models/stairs-straight.model.json` | BuiltModel v2 of `make-stair-dxf.py straight`: 16 risers, 15 treads | `f9e2f8952cf5c107861b98c64f9632988192f8b1` |
| `models/stairs-L.model.json` | BuiltModel v2 of `make-stair-dxf.py L`: 7 + 9 risers, 14 treads, 1 landing | `85d27c8623cca441fc24288d94406d56bca36a52` |
| `models/stairs-U.model.json` | BuiltModel v2 of `make-stair-dxf.py U`: 8 + 8 risers, 14 treads, 1 half landing | `bb2e29818643e3eca938963c24b4c6012dbf38d9` |

`rooms/runs/reference-build/` is a FakeJobRunner run folder of that build, in the format of `upload/runs/` (`run.json`
names each output's bytes, `job.json` their sizes and sha1s; `services/builder/tests/test_r_fixtures.py` checks it):

| File | What | sha1 |
|---|---|---|
| `rooms/runs/reference-build/job.json` | run folder | `1e9679fd81c1fc7f976b96b92e6b3771fd857846` |
| `rooms/runs/reference-build/out/Rooms_reference.ms` | run folder | `bdc63917a3730cd09a512fe5bcb6d0ee7fe5a0bb` |
| `rooms/runs/reference-build/out/diff.json` | run folder | `975b4b76be497b7ee8eee52fd95b32fc2140b3fd` |
| `rooms/runs/reference-build/out/inputs.json` | run folder | `873a26603082c958c193f0c10f11941e8d7dd17e` |
| `rooms/runs/reference-build/out/openings.json` | run folder | `07d1e3edd71125c9bfa4de17069699759d057d4a` |
| `rooms/runs/reference-build/out/pieces.json` | run folder | `e83771137ffd8eab4056cd23198e16326bbf1fa2` |
| `rooms/runs/reference-build/out/report.json` | run folder | `4cce60d0227faf45b759b35b5bd28d8e0659f9ea` |
| `rooms/runs/reference-build/out/topview.png` | run folder | `578948481a1ea6ce85125d60333ce9643a5a2647` |
| `rooms/runs/reference-build/run.json` | run folder | `b5939cfdf6abf0b7a65f626c4518e32878b7ffc7` |

A tiny store with the reference building as one saved version (and, with `--stairs`, the three stair models) is made at
test time, never committed: `node tools/rooms/make-fixture-store.mjs --out <dir> [--stairs]`.

The row shapes of the new report keys are these fixtures' (the builder's `contracts.py` types them only as lists):
`rooms.open` `{ name, at }`; `rooms.several` `{ space, names }`; `slab.holes` `{ what, area, at, o, cut, why? }` (`cut: false`
with `why` = a mark that was not cut); `slab.unfloored` `{ area, at, o, mouth, answered }`; `slab.closings`
`{ kind, a, b, width }`; `slab.dropped` `{ area, at, why }`; `stairways` `{ id, state, why, text, severity, at, outline, walk,
bottom, to, risers, riser }`; `stairClash` `{ stair, kind, label, area, z1, at }`; `fixes.closings / rooms / stairs`
`{ fix, matched }`. Points are sheet metres. Since RR (12 Nov): `rooms.open` also holds rows with `why` and no room of
their own, `{ name: '', at, area, why: 'not a room' }` (a closed area of 10 m2 or more in no room) and `{ name, at, room,
area, why: 'placed by distance' }` (a name given to a room under 4 m2); a `slab.holes` row with `cut: false` may have
`why: 'kept as floor by staff'`; the `stairways` row's `outline` is the outside of the treads and landings joined (no
longer their convex hull). The five sha1s above that moved in RR are explained in `docs/rooms/contract-issues/RR.md`.

### Settings, the house-rooms overlay, the old-rule outputs, the keys

| File | What | sha1 |
|---|---|---|
| `upload/settings/bank-rooms.json` | `settings/bank.json` plus the three options at their new values (`node tools/run-builder-py.mjs tools/rooms/make-rooms-settings.py`) | `97350b392413ea35122bf8f191c4cc04fbaf671c` |
| `upload/settings/house-rooms.json` | `settings/house.json` plus the options and the ceiling heights 3.00 / 2.90 m | `7aa6468f4262ddc6462eab1b8f7aee4fe797d227` |
| `upload/settings/suite-rooms.json` | `settings/suite.json` plus the options | `4bbcc2ac7a1930a3c572837e0a600645be9db785` |
| `upload/settings/tower-rooms.json` | `settings/tower.json` plus the options | `c03168fc2d5652ab505973ca5a9250d58df4b8ae` |
| `upload/settings/suite-revit-rooms.json` | `settings/recipes/suite-revit.json` with layer 0 set to wall, nothing set aside, plus the options | `9b1888c022d268c6b44dfd11ee75e7798a3b4dfc` |
| `upload/settings/recipes/house.json` | the `project-data.json` of the upload acceptance store's `house-upload` v1 (model `1c07bfeef580`): no key of this milestone | `0c8168301ce3fd4a3c0e376cff2b04af7fe0250f` |
| `upload/settings/recipes/suite.json` | the same of `suite-upload` v1 (`205e9c2c46e8`) | `5da2fccf57f6ba46e8a8c52d908f530c6ef42ca6` |
| `upload/settings/recipes/tower.json` | the same of `tower-upload` v1 (`91414f408cb2`) | `0d6a427e9381a687471f96bb9a2630d004a64a40` |
| `upload/settings/recipes/suite-revit.json` | the same of `suite-revit` v1 (`1d90d91ef949`), the A-12 run | `faf0f4d04301f8f50665fbe261c95a045f80ebb4` |
| `upload/overlay/house-rooms.overlay.json` | the house built with `house-rooms.json` by the real rules (R1's and R2's) and written by `out/overlay.py` (R3's), every field in the floor's sheet metres (`node tools/run-builder-py.mjs tools/rooms/make-house-rooms-overlay.py`; re-made by RI, WORK_BREAKDOWN RI-0, R6.md D-3: the scaffold's was the tracer's, provisional): ground 22 rooms, 7 stairs (S1 climbs); upper 24 rooms, 4 holes | `8338f2d50da8ab80715918485579cc6358030be6` |
| `rooms/old-rule.sha1.json` | the sha1 of every output of the five old-rule builds, recorded from the builder of `66b4c06` (`services/builder/tests/test_r_old_rule.py`); frozen | `c0b7bf53f499773998f278d2a3c0251f68060d5c` |
| `rooms/keys/bank.json` | each of the bank's 18 room tags with its own point on the sheet (`node tools/run-builder-py.mjs tools/rooms/make-keys.py`) | `7dfacd23c53e2b8392b3f4917fb73484c76ca112` |
| `rooms/keys/probes.json` | the walk probes of 9 Nov that had no floor at their start, by floor, sheet point, normal and side (ACCEPTANCE RA-6) | `cc4702d765b33fc98ab0b3754306e11d7e4f541f` |
| `rooms/keys/house.json` | one point per room of the house's east building, written by R1 (R1.md 1.1; the scaffold's was empty) | `f3b8e2c650bef72164a30f4a10d0854690d091f9` |
| `rooms/keys/suite.json` | the old suite's 16 names, each with a point in the room the drawing means, picked once by RI from the plot of the drawing (its room outlines on Defpoints and the written areas; RA-7) | `b45dbdc49ea342173c49935d7a9c71e59502dc65` |

### models/broken/: the v2 cases (`node tools/make-broken-fixtures.mjs`, one per rule of DESIGN R-12.1)

| File | What | sha1 |
|---|---|---|
| `models/broken/cross/v2-duplicate-space-id.json` | see `models/broken/expected.json` for the path each is rejected at | `2c426f8712b6bde703a6de35ae63e986cdf0b027` |
| `models/broken/cross/v2-duplicate-stairway-id.json` | see `models/broken/expected.json` for the path each is rejected at | `6a2e8cb93af6e909f7ac5da7b2ddc1a354bb17c7` |
| `models/broken/cross/v2-part-stair-on-another-floor.json` | see `models/broken/expected.json` for the path each is rejected at | `6a1cad7733a83a89fe0ebf66439a165ea7330248` |
| `models/broken/cross/v2-part-unknown-stairway.json` | see `models/broken/expected.json` for the path each is rejected at | `d6272102f3004ded6bc9bd62f6c7e1ec07022844` |
| `models/broken/cross/v2-room-space-on-another-floor.json` | see `models/broken/expected.json` for the path each is rejected at | `0128f24aacaf855e0dc3affff2c33eb4ec33f540` |
| `models/broken/cross/v2-room-unknown-space.json` | see `models/broken/expected.json` for the path each is rejected at | `ebdf6ba544e1f69bb556ff70cfeae7329b20b45a` |
| `models/broken/cross/v2-space-unknown-floor.json` | see `models/broken/expected.json` for the path each is rejected at | `b80424892a1c4d18b3a30568f112e3765594244f` |
| `models/broken/cross/v2-stairway-not-above.json` | see `models/broken/expected.json` for the path each is rejected at | `e3d49e1f3bd14c691bbc0b379394951f17d27398` |
| `models/broken/cross/v2-stairway-other-stack.json` | see `models/broken/expected.json` for the path each is rejected at | `0f1238da0d2eba32b59852175da00f2aa3388e1b` |
| `models/broken/cross/v2-stairway-unknown-floor.json` | see `models/broken/expected.json` for the path each is rejected at | `87321d9f3b51061729bd662aa262d20e16eb5531` |
| `models/broken/cross/v2-tread-without-stair.json` | see `models/broken/expected.json` for the path each is rejected at | `ac126442f43007001e7c31188e81d069f9798ced` |
| `models/broken/schema/v2-walk-one-point.json` | see `models/broken/expected.json` for the path each is rejected at | `6bf611b3b448845593c47dfcffeaaa9247b767e5` |

Also by the scaffold, outside this folder: `packages/viewer/test/fixtures/walk-parity.json` (the walk-parity golden, with
its recorder `packages/viewer/test/tools/record-walk-parity.ts`) and `docs/rooms/reference/` (`versions.sha1`,
`acc-9nov.versions.sha1`, `outside.txt`, `upload-walk-9nov/`).
