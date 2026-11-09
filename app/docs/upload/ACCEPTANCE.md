# Upload milestone: acceptance criteria and test plan (4 Nov 2026)

What "done" means for `DESIGN.md` (cited U-n), and the tests that show it. **Must** criteria gate the milestone;
**should** criteria are reported with numbers when they are missed. Measured values from 4 Nov are given where a
criterion is a reproduction.

## 1. Acceptance criteria

### A-1 The bank re-upload reproduces bank version 2 (must)

Upload `I1201 - LEVEL 1 GENERAL ARRANGEMENT.dwg` and `I1202 - LEVEL 2 GENERAL ARRANGEMENT.dwg` through the API into a
temp store, as (a) a new project `bank-reupload` and (b) version 3 of the seeded `bank-sampeng`, with the settings
`fixtures/upload/settings/bank.json` (the roles of `bank_test/src/bank_project.json` in the app's role names; floor keys
`L1` / `L2`; levels 0 / 3.70; wall heights 3.70; the furniture word `Fritz-Hansen`; the project names of v2), sent with
`layersReviewed: true`, no fixes; build; save. (U3's own test builds the bank from the settings rewritten with
integer-valued JSON numbers, `0` for `0.0`, and gets the same model bytes; A-7 does it through the browser.)

| Output | Must equal | Measured 4 Nov |
|---|---|---|
| the two DXFs (cache) | the 26 Oct conversions | sha1 `9167d084...` (2,817,940 B), `c88491df...` (7,923,920 B) |
| conversion verdicts | `ok` both (the `handle-not-found` and `unstable-class` lines change nothing, U-6.3); `hatch-short-handles` 148 on L1, 143 on L2 | L1 also 28 handle-not-found, 9 unstable-class (measured; the design's first count said 6) |
| `versions/<n>/model.json` | v2's bytes | sha1 `c3a9408304a240b83c36f5c5c53db56b50a72c64`, stamp `c3a9408304a2` |
| furniture CSV download (no heights) | v2's CSV download | sha1 `b528bb2320ef...` |
| `source/openings.json` records | the `openings` lists of `detector/output/bank1_openings.json` and `bank2_openings.json` (equal to `bank_test/src/detector_out/openings_L1.json`, `_L2.json`), Python list equality **with the `floor` field removed from every record on both sides** (the upload names floors `bank-reupload:L1` / `bank-sampeng:L1`, the files `bank:L1`); ids `L1-001` ... equal | 24 + 25 |
| the Max generator on this model with the `bank-27oct` text profile | `bank_test/Bangkok_Bank_Sampeng.ms` byte for byte | sha1 `615d50137bdb...` (867 CRLF lines) |
| the version's own `.ms` (the `upload` profile) | the bank-profile script except the profile's lines (header, title, built-by, page, rollout, tooltip, placed-at, datum source, notes); line 2's stamp `c3a9408304a2`; the expected bytes generated at test time with the build's date | |
| `stages.json` | v2's in `floors[k].lines`, `floors[k].rings`, `floors[k].sheet`, `source.files`, `source.layersInUse`, `source.units` | |
| `assets/topview.png` | v2's asset (**should**) | sha1 `f084b556503c...` |
| offline HTML download | opens from disk with no network and passes A-6's walk checks | |
| furniture CSV with every furniture option at its default, and with `pieceLayer: 'drawn'` and the suite's reader rules on (U-10.5) | `b528bb2320ef...` (default: must; suite rules on: should, a difference listed) | |

May differ, by design (listed in the bank's gap report): `stages.json` `pieces` (the build's own pairing, U-10.8) and
every text (`intro`, `layers`, `captions`, `stats`; no `panelIntro`); `version.json` `label`, `createdAt`, the
presentation (heading without "(test)", fact-built intro, fitSlabs camera; U-11.2), no `seed`; the `source/` sidecars; the
Max script's profile lines. For (b), v2's saved heights are carried to v3 only where they differ from the model's (none
when the seeded store has none).

### A-2 One Max generator (must)

`out/maxscript.py` with the `hotel-2nov` profile on `fixtures/models/hotel.model.json` gives `hotel_test/Hotel_Lobby.ms`
byte for byte (sha1 `0a30014a84e0...`): its computed header (follow / keep kinds from the parts, the stair width, the
lift doors' drawn widths), its tooltip, its "Placed at" lines and its datum Picture lines from `pictureFrame` included
(U-11.5). The "two holes touch" refusal fires on a synthetic part with two touching holes, and the bank's model passes
it (A-1's Max row). A synthetic model with every part kind (`packages/viewer/test/fixtures/
features.model.json` minus `fit`/`panels`) gives a script that the mock interpreter `furniture/fixtures/maxscript_mock.py`
(loaded by path, `-B`) runs with no error and the expected object count; a kind outside the bank's 11 adds exactly its
case line and material; CRLF on every line; no placeholder left.

### A-3 Intake (must)

* Every DWG in the project root converts; verdicts: bank L1, L2, L29, L30 `ok` (0 missing); house `minor` (1 hatch on
  layer 0); presidential `loss`, 8,254 missing, the four lost blocks inserted in the suite's area listed with their
  inserts (`TG_artiscardio_2d_1283_8`, `_1345_11`, `_1388_13`, `A$C59a32014`), `COT T7_HA` and the wall-layer pieces
  lost outside it.
* Verdicts come from the comparison only: the house's 1,004 handle-not-found, 385 wrong-layer and 81 `error:` lines do
  not make it worse than `minor`; the `error:` class adds one note.
* A DWG older than R13 (an `AC1009` header, and an `AC1.50` / `AC2.10` header), a renamed text file, an empty file and a
  truncated DWG are refused or fail with their codes (`unsupported_version`, `bad_kind`, `convert_failed`) and plain
  messages.
* A child that does not finish is killed at its time limit (`convert_timeout`); a child that allocates past its cap
  ends `*_memory` (an allocating child, and a `MemoryError` raised inside the reading walk: both classified by the
  completion port, exit code 75 or peak memory, U-3.5, never a partial `done`); Cancel stops a run within 15 s (status
  `cancelled`, no child left, "Stopping..." meanwhile, nothing written by the worker after `cancelled`); an API restart
  during a run leaves it running (status `done` later); a killed worker is shown `interrupted`, and so is a run whose
  worker died before writing `job.json` (`launch.json` pid dead, older than 60 s); a worker whose run folder is
  deleted exits within 2 s and frees the machine lock.
* `job.json` written while another process holds it open (a reader in a loop): the run still ends `done`.
* Upload: a 17.8 MB DWG in 3 parts; a part sent twice; a session resumed after a page reload (by re-picking the file);
  413 above 300 MiB; 411 / 413 from the body guard before the body is read; a session older than 24 h removed.

### A-4 Reading and the detector (must)

* For bank1, bank2, sukhumvit, presidential, l29, l30 the cache's items equal the prototype `prims.py` items made by
  `tools/upload/make-reference.py` (same order, every field, `k` and `area` aside).
* With the acceptance settings (floor keys `L1`/`L2`, `ground`/`upper`, `suite`, `L29`/`L30`), the derived detector
  mapping gives openings equal record for record to the `openings` lists of
  `detector/output/{bank1,bank2,sukhumvit,presidential,l29,l30}_openings.json` (24, 25, 86, 25, 31, 34 records), with the
  `floor` field removed on both sides (floors' areas as in `detector/mappings_with_areas/`). The blind-run outputs of 27
  Oct are not oracles (older code).
* Units: the house reads as mm although its header says inches (28 door votes for mm, 4 for m: measured; first written
  as 22); level tags: the house 26 (18 on `SPEC`, 8 on layer `0`; 28 `TAG-LEV` / `TAG-SEC` inserts at any depth, of
  which 2 have a blank `LEVEL` and are left out: measured; first written as 28), none of `W1.20`, `D2.10`, `A1.00`, `R1.50`, `x0.900` read as a tag; grid labels:
  bank 10, house 63, tower 0; keys unique within a source and equal across two conversions of the same DWG; every plan
  entry's `sig` / `rsig` / `eid` equal to what the builder computes from the cache item.
* Floors from grid labels (U-9.4, each line continued 10 m from its bubble): the house's 63 labels give 19 to the
  ground plan and 16 to the upper (16 shared; measured, first written as 12 + 12 on each), and the elevation labels to
  neither.

### A-5 The other drawings build from a mapping and a floors setup only (must), with a written gap report (must)

The house (`Test Sukhumvit Residence.dwg`: two areas on one sheet, floor keys `ground` / `upper`, levels 0.90 / 4.80
picked from the list of its level tags, wall heights 3.90 / 3.50, grid alignment), the suite (`layout presidential
test.dwg`: one area, key `suite`, level 0, wall height 3.00, door head 2.10, `furniture.pieceLayer: 'drawn'`) and the
tower (`L29.dwg`, `L30.dwg`: whole files, keys `L29` / `L30`, levels 0.00 / 4.00 and wall heights 4.00, assumed and
stated: the drawings give none; shared origin) each build with `fixtures/upload/settings/<name>.json` and **no fixes**:
the run is `done`, the model validates (schema and D-5.6), the version saves and opens in the viewer, and A-6's walk
checks run (must) and pass (should; each failing probe classified in the gap report). Alignment: the house's upper floor
shift is `(-74.021 +- 0.002, 0.000 +- 0.002)` m with a spread under 2 mm (`sheetShift [74.021, 0]`), found by `auto`
(which picks grid). Furniture: the suite's pieces by kind are reported against its prototype's 120 (12 plants, 14
seats, 7 sofas, 5 sanitary, 3 tall cabinets ...); with the whole-subtree reading (U-9.1) the plants, the balustrade
block and the lounge are no longer split from their inserts (should: within 5 % of 120, every kind present).

`docs/upload/GAPS.md` (written at integration with `tools/upload/gap-report.py`) compares each uploaded model with its
prototype model (bank v2, `sukhumvit-house` v1, `presidential-suite` v1), in drawing coordinates (model + offset +
sheetShift), per floor: wall area (union of wall, column and parapet footprints at `z0 < 0.01`) and the symmetric
difference; wall run count; glass area and pieces; openings by kind and how many match by centre within 0.2 m; lintels,
sills, panes; plate area and its symmetric difference; rooms (count, names matched); furniture by kind; the Walk checks.
Every difference over 0.05 m2, 1 opening or 1 piece is listed with its cause and one of: **option now** (U-10.5),
**option later**, **check-and-fix** (now / later), **accepted difference** (by design). The tower has no prototype model:
its section reviews the counts, the flags and the Walk checks. A second suite row with the outline suggestions accepted
(all of them) is added (should).

Expected (from the readers and the reviews), with their class, so that the gap report meets no surprise:

| Drawing | Gap | Class |
|---|---|---|
| house | closing 0.03 vs 0.12 m (+2 runs, 0.24 m2); glass full height vs H - 0.6 m | accepted difference (U-10.5 "not adopted") |
| house | tread lines vs panels; the upper stair void | option later (climbable stairs) |
| house | the lintel-bearing rule, fins, glass corners, jamb-section depth, lintel slots | option later (U-10.5 "house cutter rules") |
| house | 5 openings whose heights the prototype took from the elevations (`cad_test/src/heights.json`: 3.90, 3.90, 2.90, 2.90, 2.55 m against the floor defaults; 16 matched, 5 differ) | check-and-fix now (the opening editor's head and sill) |
| suite | the corridor walls and north / south facade glass missing without the outline option (~63 % of the hand-added length on outline edges) | option now (`outlineWalls: 'suggest'`, the second suite row) |
| suite | the `A-4. Dim` extras (0.48 m2) if that layer is given `glass`; the entrance and terrace door jambs on `A-4. Dim` (`ENTRANCE_JAMBS`, `TERRACE_DOOR_JAMBS`), the octagon facade faces (`GLASS_FACE_IN` / `OUT`) | check-and-fix now (set aside) or option later (per-item roles) |
| suite | the prototype's hand rules that make low or special parts: `C_WALL` (the C-shaped wall round the built-in sofa), `CABANA` (the daybed block on the wall layer), `JACUZZI_KERBS` (low kerbs), `NOT_WALLS` (pergola rectangle, terrace edge lines and a toilet outline, which the general builder turns into 1.0 m single-line parts), `FEATURE_PANEL`, `PARTITION_FACES` / `PARTITION_PANELS` (a movable glass partition drawn open), `BATH_GLASS`; the seeded v1 has low 7, balustrade 1, deck 2, post 4, builtin 1 parts from them | check-and-fix **later** (this milestone can set them aside, not lower or re-kind them: U-16 "per-piece roles and heights") |
| suite | the terrace pieces at full height; room names at the labels (15 of 16); the slab and balustrade from the general rules | accepted difference |
| suite | the gym machines and `A$C59a32014` lost in conversion (also absent in the prototype) | accepted difference (conversion; the AutoCAD DXF fallback) |
| tower | no prototype model; openings from a detector that scored 72 % held out | check-and-fix now (the opening editor), reviewed by count |

### A-6 Walk checks on every uploaded version (must for the bank re-upload; must run, should pass for the others)

For the house, the suite and the tower, a failing probe can come from a rule this milestone leaves out on purpose (the
house's cutter rules and stair void, the suite's corridor walls without the outline option, the tower's 72 % detector),
with nothing in scope to fix it; each failing door or wall probe is listed in `GAPS.md` with its class, as A-5's gaps
are. The bank re-upload must pass every check.

`tests/e2e/upload-walk.spec.ts` (U7) opens, from disk, the offline file of each uploaded version (bank re-upload, house,
suite, tower; made from the acceptance store with `make-offline.mjs` into `WT_UPLOAD_OFFLINE_DIR`): loads with no error
and no network; walls stop you at 40 random spots per floor (never through, never inside); every door is walkable
through its middle both ways (exterior doors from inside); glass stops you at every probe and at 10 random glass parts;
the floor buttons and PgUp / PgDn change floor; the stamp meta equals the version's and the `.ms` line 2; at 1400 x 880
the start view shows every slab corner inside the canvas, left of the panel (U-11.2). (The ported walk helpers of
`tests/e2e/lib/walks.ts`; generic, so they run on the seeded `bank-sampeng-v2.html` while being written.)

### A-7 The staff path in Edge (must)

`tests/e2e/upload.spec.ts` on the dev server and the API (fresh seeded store, real worker; `test.setTimeout(10 *
60_000)`): New project (new office `E2E Revit`) -> upload the two bank DWGs -> **leave** (back to the project list; the
new project's card leads to its draft; the draft is listed on its page with Continue) -> Files (verdicts `ok`) -> Layers
(three roles changed with the selects, the rest by applying the fixture settings through the API) -> Floors (levels
typed, `0` and `3.7`) -> Build (the pre-build checklist clear, progress seen, done) -> Check (set aside one item;
rebuild; the diff shows the change; restore; rebuild; no change against the first build; set aside one whole block with
the block pick mode: one ref in the settings) -> Save (a double click makes one version) -> the version page shows the
viewer with one canvas, `live() === 1` -> the Max script and CSV downloads are byte-equal to v2's (CSV) and to the
upload-profile script generated at test time with the build's date (Max). A second test uploads a synthetic DXF with hostile names
(`tools/upload/make-test-dxf.py hostile`: layer, block, text and file names containing `<img src=x onerror=...>`,
`</script>`, `$'`, `&amp;`) and walks every step: no element is injected, no dialog opens, the names show as text.

### A-8 Office memory (must)

After A-7 saves with "remember" ticked, `data/mappings/e2e-revit.json` holds the bank's roles; a new project of that
office uploading `L29.dwg` gets the thirteen layers of U-8.4 (`A-WALL` ... `P-SANR-FIXT`, `A-GENM`; L29 has no
`L-PLNT`) suggested `from: 'office'`, any other L29 layer in the bank's memory from the office too, and the rest by name
or contents. A new version of the seeded `bank-sampeng` (no office) offers the office select, and its proposal keeps the
floor keys `L1` / `L2`, v2's naming and the offset `[1.212, 0.348]`.

### A-9 Fixes survive a rebuild and a re-upload (must)

A set-aside, a whole-block set-aside (one INSERT ref removing its subtree), an opening fix and an accepted outline edge
are applied in the next run; uploading the same DWG again (same sha1) matches all of them by key; a DXF exported from
the same drawing with other handles matches the set-aside by `sig` (synthetic test), a Revit-style element block moved
and renumbered matches by element id + layer + type + `rsig` (synthetic test), and what cannot be matched, or matches
more than one item, is flagged (`fix-unmatched`) and removes nothing.

### A-10 Times on this laptop (should)

Upload complete -> prepare done: bank (both files) <= 30 s, presidential <= 150 s; build run: bank <= 45 s, house <= 60
s, presidential <= 90 s; the check canvas redraws the house sheet in <= 50 ms at 1400 x 880 in Edge; peak memory of any
child <= 1.5 GB on the six drawings.

### A-11 Nothing else moved (must)

The foundation's checks pass with only the changes listed in section 3; the prototypes' own tests pass unchanged; no
file outside `app/` changed (a listing before and after, sizes and times); no `__pycache__` in a prototype folder;
`npm run seed` gives the same 5 stamps; nothing deployed.

### A-12 A new drawing from the 3D team: the presidential suite as a Revit export (should; added 9 Nov 2026)

The owner put `presidential suite_layout.dwg` in the project root on 9 Nov 2026 (2,280,952 bytes, AC1032): the 3D team's
new drawing of the presidential suite, exported from Revit (REVIT xdata on about 20,600 of its 22,849 model-space
entities, all at z = 0, AIA layers such as `A-WALL`, `A-DOOR`, `A-GLAZ-CURT`, `S-COLS`, `I-FURN`, `Q-CASE`, `P-SANR-FIXT`,
`E-LITE-EQPM`, nine room names on `A-ANNO-IDEN`, views named GENERAL ARRANGEMENT PLAN and FURNITURE PLAN - EXECUTIVE
SUITE). It is not the 19 Oct `layout presidential test.dwg` and was never seen by the builder or the detector. A
preview by the main session with U2's reader (read-only, scratch folder): the header says inches and the doors say
millimetres (7 to 0), read in millimetres; nine room names; no level tags and no grid labels (one floor); with the
`dwp-revit` office mapping every structural and furniture layer is suggested from the office, and only `A-GENM-HDLN`,
`G-IMPT`, `I-WALL-HATT`, `M-EQPM`, `M_Arredi` (Italian for furnishings) and layer `0` fall to `other`.

* It goes through the app's own upload path as **a new version of the seeded `presidential-suite` project** (and once as
  a new project), with the office mapping, `M_Arredi` set to furniture, one floor at level 0.00 with 3.00 m walls (the
  suite's accepted height, 26 Oct), and no fixes.
* It converts with a verdict (record it and the messages), reads, builds, saves and opens in the viewer; its Max script
  and furniture CSV download; the walk checks of A-6 run on it (should pass; each failing probe classified).
* Its openings come from the frozen detector with no tuning on this drawing: list them (kind, width, where) for a
  later held-out scoring against an answer key made without the detector; do not change the detector for it.
* Add it to `GAPS.md` against the 19 Oct suite model (`app/data/projects/presidential-suite/versions/1/model.json`): walls,
  glass, doors, rooms, furniture counts by kind, and anything the new drawing has that the old one did not.
* It is a **should**: a failure here is reported with its cause and does not block the milestone, unless the cause is a
  fault that would also hit other Revit exports (then it is a must, like A-5).

## 2. Test plan

### 2.1 Builder tests (`npm run test:builder`, pytest in `services/builder/tests`, builder Python)

Two markers, because the machine run lock (U-3.5) belongs to a process:
* `heavy`: a real drawing converted, read or built **in the test process**; its fixture takes the run lock.
* `worker`: a test that spawns `job.py` (the worker takes the lock itself); its fixture never takes the lock, and its
  timeout covers the queue wait (a wait is reported as "queued behind another run", not as a failure). Tests of the
  lock itself use a private `WALKTHROUGH_RUN_LOCK`.

Both read the reference outputs from **`WT_REF`** (default `%TEMP%\wt-u0\ref`, made once by the scaffold with `npm run
make:reference -- --out %TEMP%\wt-u0\ref`; read-only for every builder; documented in
`services/builder/tests/conftest.py`); a builder
re-makes its own copy only with `--only <drawing>` into its own `WT_TMP` when it must.

| Owner | Tests |
|---|---|
| U0 | `test_vendor.py`: every vendored file equals `VENDOR.json` and the prototype file; `roles.py` tables (U-8.2) against the bank's derived mapping (`docs/upload/reference/derived_detector_mapping_bank1.json`); `names.py` (normalise, family, elementId) and `keys.sig` / `keys.rsig` on a table of cases; `jsonfile.write` with a second process holding the file open (the replace retried, then succeeds); `tools/upload/check-derived-mapping.py` on the reference caches (each fixture's derived mapping reproduces its `detector/output/*_openings.json`, `floor` aside; differences listed for U3) |
| U1 | conversion of I1201 / I1202 (DXF sha1s), message classes, verdicts for the six DWGs, the house `minor` despite its `error:` lines (heavy); pre-R13 headers refused; a DXF upload's `not-converted`; Job Object time and memory kills (a sleeping child; an allocating child and a `MemoryError` child, both `*_memory`); cancel (nothing written after `cancelled`); a worker whose run folder disappears exits; two workers on one lock (one `queued`; private lock); `job.json` always parses during writes and the run finishes with a **separate reader process** holding it open; `procStart` equal to the API's computation on a live child; a fake step module for the orchestration of both run kinds and the one-source prepare (`worker` marker); the cache's `.done` rule, the tmp-then-rename read folder and the `auto` pointer, LRU eviction above the cap |
| U2 | items vs reference for six drawings (heavy); items with no points carry no area; keys unique and stable; unit votes (A-4); level tags (the house 28: 18 `SPEC` + 10 layer `0`; the negative cases `W1.20`, `D2.10`, `A1.00`, `R1.50`, `x0.900`); grid labels and their lines (`A.1`, `1/2`, primes accepted); area proposals (the house's two plans each covered by one proposal at >= 90 % of `regions.json`'s box); plan geometry decode round trip, sizes, an anchor per INSERT at every depth, `sig` / `rsig` / `eid` per entry; suggestions for the bank's layers from an empty office agree with `bank_project.json` on >= 80 % of layers, the evidence for `RNAME`-style contradictions, `A-GLAZ` -> window and `A-GLAZ-CURT` -> glass; the settings proposal for bank, house, suite, tower, and for a new version of a seeded project (floor keys and naming from its latest model) |
| U3 | the bank golden from the reference caches and openings (model sha1), the report's `summary` equal to `bank_summary.json`, the `BuildResult` key structure equal to `fixtures/upload/build-result.bank.json` and `replay-input.bank.json`; the bank from integer-valued settings (same sha1); every furniture option at its default (same sha1 and CSV, must) and with `pieceLayer: 'drawn'` and the suite rules on (same, should); detector wrapper vs frozen outputs for six floors with `floor` removed (heavy); the `detector-skipped` and `slow` report fields on a synthetic floor; alignment (grid labels to floors by their lines: the house 19 / 16 (16 shared), shift (-74.021, 0), spread < 2 mm; bank none); door heads (a typed floor door head beats the drawing's most common named height); one-floor and three-floor synthetic builds; plinth; `parapets: 'auto'` on the house (no parapet); `screen` parts never cut; W x W x H heads; eitherKind glazing; low-wall sill; set-aside (the items gone before pairing and detection; an INSERT ref removes its subtree; element id + `rsig`; an ambiguous match removes nothing), opening fixes, outline suggestions on the suite (count and length of free edges); furniture: the bank's 185 pieces in 14 kinds unchanged, the suite by kind against its prototype's 120 with whole-subtree reading, the house reported; `drawnVariant`: the bank's 26 mirrored pieces in 9 families (should); the house's ground-floor walls on v1's with the pinned offset |
| U4 | Max goldens (A-2) with the profiles' verbatim lines and the computed follow / keep, stair and door sentences; the two-holes refusal; replay from `fixtures/upload/replay-input.bank.json` (lines, rings, sheet equal v2's; texts for 1, 2 and 3 floors with every placeholder; validated by `node tools/run-py.mjs -m walkthrough_api.check_file stages`); presentation for the bank, suite and house models validated the same way, the hostile names as plain runs; top view (bank bytes, one-floor no crash); overlay, flags (every kind of U-12.2, `detector-skipped` included, from `fixtures/upload/build-result.bank.json`), diff in sheet coordinates (a removed part, a changed opening, a version in another frame), placements (`insertMirrored`, `drawnVariant` passed through); every output checked with `check_file`; `gap-report.py` on two seeded models |

### 2.2 API tests (`npm run test:api`, pytest in `services/api/tests`, the API venv; U5)

* Every new route: statuses, error codes, camelCase, ETag / 304 on the raw routes, gzip on the plan route, attachment
  names, `If-Match` and 412 on settings, 409s on run / save / delete; the body guard (411, 413) before the body is read;
  CORS methods; the Host check still in front.
* Uploads: part sizes, idempotent parts, completion with missing parts, magic bytes, dedupe by sha1, expiry clean-up.
* Builds with a **FakeJobRunner** (writes `job.json` and copies the fixture outputs of `fixtures/upload/runs/`): the
  proposal adopted once (two threads polling at once: one adoption, one validation, both recorded in `api.json`);
  `putBuildSettings` 409 `not_prepared` at revision 0; a units change rescales that source's boxes and points and starts
  a one-source prepare; `runBuild` 409 `layers_not_reviewed` until a save with `layersReviewed`; `getBuild` with
  `withSettings=false` has `settings: null`; stale results refused at save; invalid worker outputs (a broken model,
  stages with an unknown floor, a presentation that fails `validate_presentation`, an overlay that fails its record, a
  `.ms` with the wrong stamp) turned into `invalid_output`; interrupted runs marked on start-up (a dead worker; a
  `spec.json` with no `job.json` and a dead `launch.json` pid, older than 60 s); cancel with a worker that does not
  answer (the timer kills it, waits for the pid, then writes `cancelled`; `cancelRequested` meanwhile).
* Save: the version folder (`project-data.json`, `source/*`), version.json fields, carried heights, the pinned offset in
  `project-settings.json` (and, for a seeded project, the latest version's offset), the office memory merge (latest
  wins, `was`), the build marked saved; two concurrent saves of one build make one version (the second gets 409
  `build_saved` with the version); `create_version` checks names before the `.ms` stamp.
* Bodies and paths: a 6 MB settings PUT accepted, 9 MB refused with 413 before the body is read; 20,001 set-asides refused
  with 422; `createProject` refuses a 41-character id and cuts a long slug to 40; a prepare under a 40-character id at
  `app/data`'s depth writes every file (paths under 260 characters).
* Seed: refuses to replace an uploaded version even with `--force`; reserved ids refused by `createProject`; a fresh
  seed still lists `['.lock', 'projects']`.
* CSV guard: hostile model -> guarded fields; the four goldens unchanged.
* OpenAPI: byte-identical re-export; 37 operation ids; `tools/check-openapi-additive.mjs` passes.
* **Integration tests** (marked `builder`; like the builder's `worker` tests they never hold the run lock themselves):
  the real worker on the small synthetic DXF (always, ~10 s, plus any queue wait, reported as such) and on the bank
  (heavy). They skip when the builder Python or LibreDWG is missing, **except under `WT_INTEGRATION=1`, when they fail**.

### 2.3 Web unit tests (`npm run test:unit`, vitest, happy-dom)

* U6: NewProjectPage (validation, 409 with the suggested id, the 40-character limit), the upload client (parts, two in
  flight, retries with back-off, resume from `localStorage` with storage throwing, cancel), the settings saver (debounce,
  If-Match, 412 merge, 413 message), the poller (`withSettings: false`, a full fetch on a new revision), each step against
  the mock API (`apps/web/test/mock-api/core.ts` with the new routes): Files verdicts and the units control (disabled
  before the proposal), the Layers table (role labels and help, the close-to-walls chip, filters, apply to shown rows, 400
  rows windowed, `layersReviewed` on the first save), the Floors form (keys, levels increasing, area from a proposal,
  pad / match under Advanced, the level-tag list, align methods, the office select), the pre-build checklist, Build
  progress, "Stopping..." and errors, Check tools writing the right fixes (an `ItemRef` with `sig` / `rsig` /
  `elementId` from the plan entry; a whole-block ref), Save (disabled in flight); the project card and the no-version
  page leading to drafts; a grep that `dangerouslySetInnerHTML` and `innerHTML` appear nowhere in `apps/web/src`.
* U7: `decode.ts` (the fixture plans), `view.ts` (pan / zoom maths, fit), `hit.ts` (nearest item, box inside / touching,
  the block mode climbing levels, layer-in-box, at several zooms), `paths.ts` (one path per layer and type, built in
  local quanta from `origin`: a plan at y = -3,500 m picks the same keys as one at 0), `near.ts`, colours per role; the CSV
  guard in the viewer (`packages/viewer/test/unit/furniture/csv-guard.test.ts`: the hostile corpus, the four goldens
  unchanged).
* U0: `apps/web/test/upload-generated-types.test-d.ts`: the generated `BuildSettings`, `BuildDetail`, `UploadSession`,
  `SourceFile` and the `contracts.ts` ones are mutually assignable.

### 2.4 Browser tests (Playwright, installed Edge, the Edge lock)

* U7: `tests/e2e/plan-canvas.spec.ts` against `apps/web/test/plan/harness.html` on the web dev server (`WT_SERVE=web`):
  the bank and house fixture plans draw (pixel probes at known wall points), a layer highlight changes the pixels, click
  and box selection pick the expected keys, redraw time on the house sheet (A-10), devicePixelRatio 1 and 2.
* U6: `tests/e2e/upload.spec.ts` (A-7), with the mock API first (`WT_SERVE=web`), then at integration against the real
  API and worker.
* U7: `tests/e2e/upload-walk.spec.ts` (A-6), written against the seeded `dist/offline/bank-sampeng-v2.html` and run at
  integration on the uploaded versions' files (`WT_UPLOAD_OFFLINE_DIR`).

### 2.5 Fixtures (scaffold U0; owners after it in WORK_BREAKDOWN)

`fixtures/upload/`, each listed in `fixtures/README.md` with its source and sha1:
* `settings/{bank,house,suite,tower,small}.json` (BuildSettings; floor keys `L1`/`L2`, `ground`/`upper`, `suite`,
  `L29`/`L30`, as the frozen detector outputs' ids; U3 owns them after the scaffold);
* `mappings/dwp-revit.json` (OfficeMapping from the bank);
* `drawing/{bank1,sukhumvit}.drawing.json`, `plan/{bank1,sukhumvit}.plan.json.gz`, `conversion/{bank1,presidential}.conversion.json`
  (provisional, from the reference scripts, valid against the contracts; replaced by U2's / U1's real ones at
  integration if they differ);
* `overlay/bank.overlay.json`, `build-result.bank.json`, `replay-input.bank.json` (from the v2 model, `bank_stages.json`,
  `bank_summary.json` and the detector outputs);
* `runs/` (the FakeJobRunner's outputs for a prepare and a build of the bank; files referenced by path where they exist
  in `fixtures/models` and `fixtures/stages`);
* `max-texts/{bank-27oct,hotel-2nov,upload}.json` (U4 owns them);
* `tools/upload/make-test-dxf.py small|hostile <out.dxf>` (synthetic DXFs, made at test time: the root `.gitignore`
  ignores `*.dxf`).

## 3. Keeping the foundation's checks passing

| Command | Baseline (4 Nov) | After this milestone |
|---|---|---|
| `npm run check:pins` | 28 npm, 28 pip | the same, plus the builder lock and the LibreDWG manifest |
| `npm run typecheck` | 0 errors, 5 tsconfigs | 0 errors, the same 5 |
| `npm run test:unit` | 595 in 49 files | 595 unchanged + new (one existing assertion changes on purpose: the empty project list's text) |
| `npm run test:api` (+ `WT_INTEGRATION=1`) | 295, none skipped | 295 + new; changed on purpose: `test_openapi.py` (operation ids, 37), `test_routes.py` (route count, modules), `test_error_responses_are_typed` (the new statuses), `test_store.py` (its `notes.ms` draft gets the real stamp, U-11.1) |
| `npm run seed` | 5 stamps | the same 5 stamps |
| `npm run gen:api` | 18 files, no change | regenerated once by the scaffold (additive), then no change on a second run |
| `npm run build` | web, template 783 KB, 5 offline files | the same + one file per uploaded version |
| `npm run test:e2e` | 214 | 214 unchanged + new specs; changed on purpose: the 8 `toHaveCount(4)` lines of `web.spec.ts` and `web-leak.spec.ts` (the four seeded cards are present) and `web.spec.ts` line 65 (the id list with `e2e-*` filtered out), the e2e store seeded fresh, a global teardown that cancels open runs |
| prototype tests (viewers 127, bank 49, suite 37, house openings 13, house furniture 29, hotel 56, boxes 87; Max checks bank 137, suite 151, hotel 196; the detector's own scores 139 / 143 and 54 / 54) | all pass | unchanged, run one at a time under the Edge lock; `furniture/test_furniture_max.py` still not run (it rewrites prototype files) |
