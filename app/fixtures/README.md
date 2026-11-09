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

`node tools/run-builder-py.mjs tools/upload/make-fixtures.py [--only settings mapping drawing conversion result runs
maxtexts]` (the builder Python; reads `WT_REF`, the `make:reference` output, read only; deterministic). Every file passes
the API's record check (`node tools/run-py.mjs -m walkthrough_api.check_file <kind> <file>`) and its type
(`apps/web/test/upload-fixtures.test-d.ts`; `services/builder/tests/test_contracts.py` for the builder's own types).
Owners after the scaffold: `settings/**` U3, `max-texts/**` U4; the provisional drawing, plan and conversion fixtures are
re-made by U2 / U1, who list any difference in their contract-issues file. Each settings fixture's derived detector
mapping reproduces `detector/output/<name>_openings.json` record for record, `floor` aside
(`tools/upload/check-derived-mapping.py`: 24, 25, 86, 25, 31, 34 records, all equal). The synthetic drawings
(`tools/upload/make-test-dxf.py small|hostile <out.dxf>`) are made at test time (the root `.gitignore` ignores `*.dxf`):
small `fb8e7283ab205c8e49ecc057f6019c1e9fd2f6d0`, hostile `7d2193d20052ac4171e42d8887270551cfa1d0b8`.

| File | Source | sha1 |
|---|---|---|
| `build-result.bank.json` | contracts.BuildResult of the bank (compact JSON): the v2 model, bank_summary.json, the detector outputs, the stages regrouped, placements found by block and handle in the reference DXFs | `d566a7bea98f069a8591015ca0cf89ff619a1ba0` |
| `conversion/bank1.conversion.json` | **provisional** ConversionReport of I1201 (dwgread -O JSON streamed against the DXF, nothing_lost_stream.py; the converter log by class): ok | `20f2b322d74dffe32535121beb1b0eb89181461b` |
| `conversion/presidential.conversion.json` | **provisional** ConversionReport of the suite: loss, 8,254 of 142,182 missing; U1 makes the real one | `308a6d64167ab14b9486d1feacb223778b083e06` |
| `drawing/bank1.drawing.json` | **provisional** DrawingRead of I1201 (`tools/upload/fixture_reader.py`: the prims walk with U-7.2 keys + read_drawing.py / areas_propose.py); U2 makes the real one | `c4c9d4857c37f1e1ddfb40cab81006b0f6bb1f10` |
| `drawing/sukhumvit.drawing.json` | **provisional** DrawingRead of the house (same); 26 level tags where U-7.3 measured 28 (U2 settles) | `ed8d68e9ee410b3a3db26c443ab18e3e4004b864` |
| `mappings/dwp-revit.json` | OfficeMapping after the bank is saved for office dwp-revit (every bank layer by normalised name) | `484a50a4b84e8d2dfed5ded65081503e771c8a00` |
| `max-texts/bank-27oct.json` | **provisional** MaxTexts profile: the verbatim header, tooltip and datum lines of `bank_test/Bangkok_Bank_Sampeng.ms`; U4 owns and completes it | `9db380a335ace16dc352d3ef3a2f40b649fd5dfd` |
| `max-texts/hotel-2nov.json` | **provisional** MaxTexts profile from `hotel_test/Hotel_Lobby.ms` (same) | `12ecd5391ab8fd4c6109cb66d473d5fdd4bebe91` |
| `max-texts/upload.json` | **provisional** the upload profile of U-11.5 in outline (placeholders); U4 owns it | `17c736a47a47c5b558230f856121146876a2640b` |
| `overlay/bank.overlay.json` | BuildOverlay of the bank from the v2 model and the detector records (sheet m = model + offset), with the opening, room-label and plate flags the data raise | `01893517d1be77a958ef1cf7bd843084731fcf1c` |
| `plan/bank1.plan.json.gz` | **provisional** PlanGeometry of I1201 with nested keys, sig / rsig / eid per entry (gzip, mtime 0) | `9c7c8ef6a338ebe1ada0913f143750861599e9a3` |
| `plan/sukhumvit.plan.json.gz` | **provisional** PlanGeometry of the house (same) | `e5688ac600f80c4b4f70a14ff1d9fc4184d3ddee` |
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
| `runs/bank-prepare/job.json` | `daa3360b877ce2e34e083672ab61708d21542731` |
| `runs/bank-prepare/out/proposed-settings.json` | `523360a3855d60a6362214dcfa62b60f79a375c4` |
| `runs/bank-prepare/out/sources/6551bdc6f0cff4e31e83b68a55d22cf42703029a/conversion.json` | `269d79ae7ccd48700bc864935fb594cd9f5c82f5` |
| `runs/bank-prepare/out/sources/6551bdc6f0cff4e31e83b68a55d22cf42703029a/drawing.json` | `30e28f37eca6c1e773768feaa3315c44667e6736` |
| `runs/bank-prepare/out/sources/6551bdc6f0cff4e31e83b68a55d22cf42703029a/plan.json.gz` | `0c81727c9c9c512ab757190269bfe8aefb2cec33` |
| `runs/bank-prepare/out/suggestions.json` | `e79eab9027aaf098c91e77d1d56f070c7655ffcc` |
| `runs/bank-prepare/run.json` | `9480f399ec17f146d309056b4e352fcb55243f1f` |
