# Contract issues: RI, integration (rooms milestone)

Written only by RI (docs/rooms/WORK_BREAKDOWN.md). Each part of the integration step writes its own section.

## RI-A: settle the contract issues, re-make the frozen fixtures, run every suite (11 Nov 2026, from 22:20)

Ports 5748 / 8748 (and the e2e config's 5711 / 8711, not used), `WT_TMP=%TEMP%\wt-ri`, the store and the cache under it.
Nothing was deployed, pushed or committed; `app/data`, `dist/` (until `npm run build`) and the prototypes were not
written. RI-A covers WORK_BREAKDOWN RI items 1, 3 and 8 and the overlay of RI-0; the acceptance runs (item 4), the
browser suite (item 5), the prototypes' tests (item 6) and the owner's path (item 7) are not in it.

### 1. The contract issues, settled (each with the smallest change)

| Issue | Decided | What RI-A changed |
|---|---|---|
| R0 item 1 (`treads` counts parts) | accepted | `docs/rooms/DESIGN.md` R-8.5: the example says `treads: 19` (21 risers, one landing), and a bullet says how `treads` and `landings` count |
| R0 item 4 (a name on a terrace) | not decided here | nothing: no drawing or fixture has one, and what the builder does with one was not checked. For the main session or RR if it matters |
| R0 item 8 (`npm run seed` in "Done when") | read as the temp-folder seed | nothing (`seed.seededAt` stays the moment of the seed; RI-A seeded into `%TEMP%\wt-ri\seed`, section 3) |
| R0 items 0, 2, 3, 5 - 7, 9 | information | nothing; item 0's two notes on the acceptance scripts are for the acceptance runs |
| R1 D-1 (the bank counts 23 labels) | accepted | `services/builder/tests/test_r1_drawings.py`: the strict xfail `test_ra7_the_bank_shows_18_labels` removed (`test_ra7_the_banks_labels_as_built` pins the 23) |
| R1 D-2 (`ground-034` out of RA-6's must list) | accepted | the same file: the probe is no longer a parameter of `test_ra6_the_probes_of_9_nov_stand_on_the_plate` (its two strict xfails are gone); the new `test_ra6_ground_034_is_outdoors_with_no_floor` checks both sides: no plate 0.4 - 0.9 m in front, no room behind up to 2.5 m |
| R1 D-3 (the old suite's terrace and should range) | accepted | the same file: RA-4's should range for the old suite in `PLATE` is 460 - 480 (was 480 - 560), as ACCEPTANCE RA-4 now says; the assertion (7 of 8 inside) is unchanged |
| R1 D-4 | accepted, cure deferred | nothing |
| R2 D-1 (RA-9 pins `walk[1]`) | accepted | `services/builder/tests/test_r2_drawings.py`: the strict xfail `test_ra9_the_house_bottom_as_ra9_writes_it` removed; the `walk[1]` assertion stays, with a comment |
| R2 D-2, D-3 | accepted / kept as built | nothing |
| R3 D-1 (`V2_KINDS` beside `EXTRA_KINDS`) | accepted | `docs/rooms/DESIGN.md` R-10: "New kinds beside `EXTRA_KINDS` (`V2_KINDS`, read with it through `OTHER_KINDS`)" |
| R3 D-2 | accepted, with R6 | nothing (R6's `DiffPanel.tsx` sorts the lost floor first itself) |
| R3 D-3 (a hole cut on purpose is no lost floor) | accepted, for RI | `services/builder/walkthrough_builder/out/diff.py`: `plate_area(model, floor, holes_back=False)`; with `holes_back=True` every hole of the floor's slabs that holds a `voids` record's point is filled, and the recorded area of a void whose point lies in no hole (a notch at the plate's edge) is added. The `plate area (m2)` row of `counts[floor]` and the lost-floor order use it. **The row itself shows that figure** (not only the comparison): R6's `DiffPanel.tsx` judges a lost floor from the same row (`before - after >= 2`, R6.md N-14), so changing only the builder's order would have left the web app marking the bank's Level 1 "floor lost" and listing it first. Two voids in one hole (the house's stair well inside the stair-hall void) are counted once. `services/builder/tests/test_r3_outputs.py`: the existing check of the row uses `holes_back=True`; the new `test_a_hole_cut_on_purpose_is_no_lost_floor` builds the bank and the house and checks that the bank's Level 1 (its lift shaft) and the house's upper floor (the living-room void, the stair hall and the well) are 2 m2 or more smaller without the holes, not smaller by 2 m2 with them, keep the model's floor order and do not have their plate row first. `docs/rooms/DESIGN.md` R-6.4 says it. R3.md N-16 ("the plate area is the slabs less their holes") is superseded for the diff's row |
| R4 D-1 (`crosses` asked at the segment's start) | accepted | `docs/rooms/ACCEPTANCE.md` RA-10's Edge part says "asked when the walker stands at the segment's start" (R4.md section 5 asked RI for the wording) |
| R4 D-2 (a tread or landing is named from the foot) | accepted | `docs/rooms/DESIGN.md` R-9.5: Ghost to Walk and a double-click: a plate names its own floor (then `findFree`), a tread or landing is named from the foot with the 0.20 m hysteresis |
| R4 D-3 | accepted | nothing |
| R4 section 4 (the D-13 "Climbing" row) | WORK_BREAKDOWN RI item 8 | `docs/DESIGN.md` section 13: the row added after the Ghost row, as R4.md section 4 writes it; the existing rows do not change |
| R5 D-1 (`RUN_WITHOUT_THE_FLAG`) | for RI | `services/api/tests/test_r5_builder.py`: `RUN_WITHOUT_THE_FLAG = True` (docstring and comment say so): the three real-worker tests run in every `npm run test:api` |
| R5 D-2 (`BANK_NEW_RULE_SHA1`) | for RI | the same file: `BANK_NEW_RULE_SHA1 = '54ef1ac240bbfa1421b0b49026ec26c16e3d1eed'`, the model saved by `test_the_bank_with_the_defaults` itself (`WT_INTEGRATION=1 ... test_r5_builder.py -k bank`: 1 passed in 32 s; the API and the real worker, the defaults = `bank-rooms.json`). Its stamp `54ef1ac240bb` is the one R7 got from its own build through the API on 8747 hours earlier (R7.md section 4): the same bytes from another process and store. Provisional, with the references of RA-15 (`test_r_rooms_golden.py` must pin the same bank model) |
| R5 D-3 | accepted | nothing |
| R5 D-4 (the acceptance scripts) | for RI | **not done by RI-A**: the acceptance runs' part (the two `suite-*` cases' edit and `a9.py`'s `reuploadFixesEqual`) |
| R6 D-1 | accepted | nothing |
| R6 D-2 (`TID.drawLineHint`'s comment) | for RI | `apps/web/src/build/testids.ts` (**frozen**, R0): the comment reads "The hint shown while the tool Draw a line is on; the canvas itself marks the first end after the first click". A comment only: no id, key or value moved (`apps/web/test/rooms-testids.test.ts` does not read the text) |
| R6 D-3 (the house-rooms overlay) | for RI-0 | `fixtures/upload/overlay/house-rooms.overlay.json` re-made with the real rules (section 2); every field of the upper floor is in its sheet metres (x 81.9 - 123.9). `tests/e2e/plan-canvas.spec.ts`: its comment, and two expects: every hole of the upper floor lies inside the floor's area and there is at least one. The house hole probe then finds all 4 holes hatched (with the Floor plate tick, at least 8 more hatch pixels than without): the spec's four rooms-milestone tests passed in Edge (section 3) |
| R7 D-1 | accepted | nothing |
| R7 D-2 (RA-8's ray meets the underside) | accepted | `docs/rooms/ACCEPTANCE.md` RA-8: "a ray up from the middle of a room hits the ceiling's underside, at the ceiling height less the 2 cm plate" |
| R7 D-3 (`fpsGpu` in `stairs/<file>.json`) | for RI | **not done by RI-A**: the acceptance runner is the acceptance runs' part |

**The information sections (N-n of R1 - R7)** were read; nothing is objected to. Two notes: R3.md N-16 is superseded by D-3
above for the diff's row; R6.md N-14 ("R3.md D-3 changes the builder only") holds, because the row the web app reads now
carries the figure with the holes added back.

### 2. The frozen reference fixtures, re-made (R0's tools; R1.md section 4, R3.md section 4)

**The tools.** Two frozen scaffold tools changed, each by four lines: `tools/rooms/make-reference-building.py` and
`tools/rooms/make-house-rooms-overlay.py` now take the overlay that `out/overlay.py` writes when it already carries the new
floor fields, and call `overlay_rooms` (how R0 added the fields and flags before R3's code existed) only when it does
not: run on R3's overlay, `overlay_rooms` added every new flag a second time. Their docstrings say so. The definition of
the building (the injected rules, `truth`) did not change: the fixtures are still the contract, built from the
definition, now through the real wiring and outputs.

**Run**: `node tools/run-builder-py.mjs tools/rooms/make-reference-building.py fixtures` and `... stairs` (each a few
seconds), then `tools/rooms/make-house-rooms-overlay.py` (15 s, the house from `WT_REF`). `--check` on both modes now
holds. What moved, compared with HEAD field by field:

| File | What moved | Why |
|---|---|---|
| `models/rooms-reference.model.json` (stamp `2da587ccc0bd` -> `bfcd621e0a22`) | `rooms[2].area` 19.7 and `rooms[4].area` 57.6 (were null); `stairOutlines.ground[0]` x, y, bbox (the outline of S1's treads and landing); `stairOutlines.ground[1].flights` 0 (1); `stairOutlines.upper` empty (1 group) | R1's `build/model.py` and `bank.py` (R1.md 4.1): a name alone in its room carries the room's area (R-3.4); the stair outlines come from R2's StairsResult (R-8.4) |
| `rooms/build-result.reference.json` | the model's same rows; the summary's `stairs` block (ground `flights` 2, `flightsWithWord` one row of 16 risers, `riser` 0.188, `steps` 15; upper no stair); `floors.upper.slab.dropped` one row (1.18 m2, "no standing room"); `replay.facts.stairs` 2 (3) | R1.md 4.1: the block counts the new stairs; today's dropped strips the new plate does not floor are listed (R-4.4) |
| `rooms/runs/reference-build/out/report.json` | the summary's `stairs` block and `slab.dropped`, as above | the same |
| `stages/rooms-reference.stages.json` | the finish caption ends "..., 5 rooms named, 3 rooms closed, 1 stair you can climb." | R3's `replay.py` (R-11; R3.md 4) |
| `rooms/runs/reference-build/out/Rooms_reference.ms` | line 2's stamp; the stair sentence and the `stairs` and `ceilings` notes; the keep sentence without treads and landings; the ceiling material `244 243 239` (was the scaffold's `236 236 232`); `__STOREYFIT__`; 16 storey statements; the hidden Ceilings layers; the window's two lines | R3's `maxscript.py` (R3.md 4) and the new model's stamp |
| `rooms/runs/reference-build/out/topview.png` | treads and landings drawn; the title names them | R3's `pictures.py` (R3.md 4) |
| `rooms/runs/reference-build/job.json` | the sizes and sha1s of `model.json`, `stages.json`, `report.json`, `topview.png`, the script | they follow the files above |
| `models/stairs-straight.model.json`, `stairs-L`, `stairs-U` | `rooms[].area` 73.0 (null); `stairOutlines.ground[0]` (x, y, bbox; on the L `withWord` 1, not 0) | R1.md 4.1, the same two rules |
| `upload/overlay/house-rooms.overlay.json` (`2686027855...` -> `8338f2d50da8...`) | all of it: the house built with `house-rooms.json` by the real rules and written by `out/overlay.py`: ground 22 rooms, 0 holes, 7 stairs (S1 climbs, 6 kept as lines), 6 closings, 1 unfloored area; upper 24 rooms, 4 holes (stair well, the service stair's kept void, the two X voids), 1 stair kept as lines; flags `slab-gap` 2, `doorway` 2, `stair` 7 among the upload milestone's | RI-0 / R6.md D-3: the scaffold's was the tracer's, with the upper floor's holes and stairs 74.022 m off its sheet |
| `README.md` | the 13 sha1s of the files above and of `upload/max-texts/upload.json` (`1877c600...` -> `4d4ef2db...`: R3's two notes) and `rooms/keys/house.json` (R1 filled it); the texts of the house-rooms overlay's row, the house key's row and the section's opening (re-made once by RI) | the files moved; a script compares every row's sha1 with its file: 0 rows differ |

Did not move (the same bytes as at R0): `presentation/rooms-reference.json`, `rooms/settings.reference.json`,
`rooms/overlay.reference.json` (R3's overlay writer gives R0's bytes), `rooms/flags.every-kind.json`, the run folder's
`diff.json`, `openings.json`, `pieces.json`, `inputs.json`, `run.json`.

**Tests that pinned a moved byte**: `services/api/tests/test_r5_rules.py` (R5's) asserted the reference model's stamp
`2da587ccc0bd` twice (the FakeJobRunner's result and the saved version): now `bfcd621e0a22`. No other test, spec or tool
names an old sha1 (searched).

### 3. The commands (RI item 3), each run once from `app/`

The owner's `npm run dev` (5710 / 8710) was running throughout; nothing of RI-A touched it.

| Command | Result |
|---|---|
| `npm run check:pins` | ok: node 24.14.1, 28 npm pins, 28 API pip pins, 19 builder pins (imported at their versions), LibreDWG 64 files (3.7 s) |
| `npm run typecheck` | 0 errors, the five configs (21.6 s) |
| `npm run test:unit` (first run, 22:35) | 996 passed, **1 failed**, 86 files (24 s): `apps/web/test/upload/useBuild.test.tsx` "an answer of the API that starts a run (runBuild) restarts the poll" (`expected false to be true` on `active` right after `set()`). Run alone three times: failed twice, passed once. A timing race in the upload milestone's test, not in code RI-A changed: fixed in the test (below) |
| `npm run test:unit` (again, 23:06, after the fix) | **997 passed**, 86 files, none skipped (34 s) |
| `npm run test:builder` (`WT_REF=%TEMP%\wt-u0\ref`, 22:38 - 22:55) | **1037 passed, 4 deselected** (the `acceptance` tests, without `WT_ACCEPTANCE=1`), no xfail, no skip, in 17 min 19 s (R3's run: 1035 passed, 4 deselected, 4 xfailed; + 2 new tests, the 4 strict xfails gone). Over RA-14's 15 min (a should): vitest, Edge and the owner's dev server ran beside it. One line (the old suite's should range in `PLATE`) changed after the run had collected its tests: `test_r1_drawings.py -k "shoulds or ground_034"` alone then, 2 passed (61 s), all eight plate0 figures inside their should ranges |
| `npm run test:api` (alone, 22:56 - 23:00) | **561 passed** in 4 min 17 s, none deselected or skipped (R5: 558 + 3 deselected; the 3 real-worker tests now run) |
| `WT_INTEGRATION=1 npm run test:api` (alone, 23:00 - 23:05) | **561 passed** in 4 min 37 s |
| `npm run build` (23:05) | exit 0 in 32 s: typecheck clean, `dist/web/`, `dist/offline-template/viewer-template.html` 794,264 B (R4's figure; 9 Nov's was 783,405), and **six** offline files: the five seeded versions with their stamps and the owner's own `presidential-suite-layout-v1` (`9041e84fa2bb`, `built-model/1`), which `make:offline` reads from `app/data` (read only) |
| `tests/e2e/stairs.spec.ts`, the synthetic files (made from the re-made fixtures with the new `dist` template; the old versions from the new `dist/offline`), port 5748, `WT_SERVE=none` | 29 passed (2.1 min) |
| `tests/e2e/rooms.spec.ts` under the mock (`WT_SERVE=web VITE_FAKE_VIEWER=1`, port 5748) | 1 passed (point 3, the fixes written on the reference building), 2 skipped (points 1 and 2 need the real worker), 1.0 min |
| `node tools/rooms/reference.mjs versions --check` / `outside --check` (23:12) | 49 listed `app/data` version files unchanged (12 new files: the owner's project); 589 files outside `app/` with 0 differences, `__pycache__` folders 2 (2 at the start) |
| `tests/e2e/plan-canvas.spec.ts --grep "rooms milestone"` (`WT_SERVE=web`, port 5748, through the Edge lock) | 4 passed (18.6 s): the house hole probe finds the upper floor's 4 holes |
| seed into `%TEMP%\wt-ri\seed` (`node tools/run-py.mjs -m walkthrough_api.seed --prototypes .. --data <temp>/seed --force`) | 5 versions, the five stamps `4b02dc17f286`, `c3a9408304a2`, `f1b95c53eb3d`, `e43270cc0c9b`, `6ab030750886`; its 49 version files equal the committed `app/data` ones (`git show HEAD:`), 44 byte for byte and the five `version.json` but for `seed.seededAt` (2.5 s) |
| `npm run gen:api`, twice | exit 0 both times, `check-generated: ok (37 operations ...)`; `apps/web/openapi.json` and the 17 generated files unchanged against HEAD after each run (git status clean) |
| `node tools/check-openapi-additive.mjs` | ok against `66b4c06`: 37 old operations and 69 old schemas unchanged (4 gained optional properties), 72 schemas now; 722 exported symbols in 17 files; the two contract copies equal |
| `node tools/check-openapi-additive.mjs --base 9eb2d58` | ok: 13 old operations and 18 old schemas unchanged; 299 symbols |

**One more change, outside the contract issues**: the flaky web test above. `apps/web/test/upload/useBuild.test.tsx`
(the upload milestone's U6) read `out.current.active` at once after `act(() => set(...))`; TanStack Query tells the hook
of new cache data on its own schedule (a timeout), which can land after `act()` resolves. Now it waits for it
(`await waitFor(() => out.current?.active === true)`, the hook unchanged): the file alone passed 6 runs of 6 while the
builder suite loaded the machine. If `set()` stopped restarting the poll the wait would time out, so the test still
says what it said.

### 4. What the other parts of RI (and RR) must know

* **The bank's new-rule model** is `54ef1ac240bbfa1421b0b49026ec26c16e3d1eed` through the API and the real worker
  (`BANK_NEW_RULE_SHA1`); `test_r_rooms_golden.py` (RA-15) must pin the same bytes for the bank, or say why not.
* **The reference building's model** is now stamp `bfcd621e0a22` (was `2da587ccc0bd`): the FakeJobRunner's run folder,
  `make-fixture-store.mjs`'s store and the synthetic offline files of `stairs.spec.ts` carry it. No spec or test names
  the old one. `make-reference-building.py fixtures --check` and `stairs --check` hold again: run them after any change
  to `build/**` or `out/**` to see what a change moves.
* **The house-rooms overlay** is the real rules' (section 2). The plan canvas spec now fails if a hole of the house's
  upper floor lies outside the floor's area.
* **The diff's `plate area (m2)` row** is now the plate with the holes cut on purpose added back (R3.md D-3, section 1).
  For `GAPS.md`'s plate figures use the report's `slab.plate` (plate0) and `slab.holes`, not the diff's row.
* **The builder suite has no xfail left** (the four strict xfails of R1 D-1, D-2 and R2 D-1 are gone): a plain run
  reports passed and deselected only (the `acceptance` tests without `WT_ACCEPTANCE=1`).
* **A plain `npm run test:api` now runs the three real-worker tests** (`RUN_WITHOUT_THE_FLAG = True`): about two minutes
  more, three builds of the house, one of the bank and one of the reference building through LibreDWG and the machine
  run lock, under `<WT_TMP>/api-tests/real-data` and `<WT_TMP>/cache`.
* **Not done by RI-A, for the acceptance runs**: R5.md D-4 (write `OLD_RULES` in the edits of `cases/suite-revit.json`
  and `suite-v2.json` where an old stamp is compared; `a9.py`'s `reuploadFixesEqual` compares only the three fix lists of
  before); R7.md D-3 (read `fpsGpu` from `<WT_TMP>/stairs/<file>.json`); R0.md item 0 (the scripts name
  `/c/Python314/python.exe` and this machine's paths; `cases/` not read for paths); `fixtures/rooms/keys/suite.json`;
  `test_r_rooms_golden.py`; `GAPS.md`; RA-17. R0.md item 4 (a name on a terrace) is undecided.
* **R2.md D-3**: the house's four `info` flags "turning or curved steps" stay; the owner's path may find them noise
  (R2's one-line change is then the review's).

## RI-B: the acceptance runs and GAPS.md (11 Nov 2026, from about 23:20; WORK_BREAKDOWN RI items 2, 4 and 6)

Ports 8748 (the served API of the acceptance steps) and 5748 (nothing served: the browser steps open offline files),
`WT_TMP=%TEMP%\wt-ri`, the acceptance folder `%TEMP%\wt-ri\acc`. Nothing was deployed, pushed or committed; nothing was
written to `app/data`, `dist/` or the prototypes; the owner's 5710 / 8710 were not touched.

### 1. The acceptance scripts, settled (R5.md D-4, R7.md D-3, R0.md item 0)

| Item | What RI-B changed |
|---|---|
| R5 D-4, the two A-12 cases | `tools/rooms/acceptance/upload-{uf,ur}/cases/edit_a12.py` writes `OLD_RULES` into the settings (both cases rebuild the upload milestone's old stamps: a new draft now gets the new rules) |
| R5 D-4, `a9.py` | `upload-{uf,ur}/a9.py`: `reuploadFixesEqual` compares the three fix lists of before the milestone (`setAside`, `openings`, `outlineEdges`); the three new lists are recorded as `reuploadNewFixLists` (they must be empty) |
| R0 item 0, the cases' own paths | `upload-{uf,ur}/cases/{suite-revit,suite-v2,suite-outlines}.json` named their edit scripts in `%TEMP%\wt-ur\acc\cases\` (still there, but clearable): now a path relative to the case file, which `acc.py` resolves (`upload-{uf,ur}/acc.py`, `main()`). The other machine paths (`/c/Python314/python.exe`, the app folder in the `.py` files read in place) are this machine's and were left: the runner rewrites the shell scripts' |
| a latent fault of `acc.py` | a case with `fixes` read the plans only as `*.plan.json.gz`; the API serves them unzipped (`<sha>.plan.json`), so the fixes hook got no plan (`KeyError` on the first run of the set-aside cases). It now reads both |
| R7 D-3, the GPU frame rate | read by the new `rooms-checks` step from `<acceptance folder>\e2e-rooms\stairs\<file>.json` (`fpsGpu`), written by `stairs.spec.ts` with `WT_FPS_GPU=1` in the `rooms-walks` step |
| `run.mjs` | the new steps (below); with `--only`, the rows of the other steps already in the result file are kept and merged again before each save (the run was made in parts, some at the same time) |

**Frozen files changed** (scaffold tools and fixtures, each for the reason above): the twelve files under
`tools/rooms/acceptance/upload-{uf,ur}/` named in the table (`acc.py`, `a9.py`, `cases/edit_a12.py`,
`cases/{suite-revit,suite-v2,suite-outlines}.json`, each in both copies, kept identical), `tools/rooms/acceptance/run.mjs` (its `NEW_STEPS` are RI's;
the merge of rows is new), and `fixtures/README.md` (the sha1 and text of the `rooms/keys/suite.json` row).

### 2. The new steps of the runner (`tools/rooms/acceptance/rooms/`)

`node tools/rooms/acceptance/run.mjs --tmp %TEMP%\wt-ri\acc [--only <step>,...]`; the result is
`%TEMP%\wt-ri\acc\result.json` (one row per step) and `rooms-result.json` (the figures, from `rooms-checks`).

| Step | Script | What |
|---|---|---|
| `rooms-builds` | `builds.sh` | copies `%TEMP%\wt-r0\acc-9nov` (and its cache) to `<acc>\data` when missing; a served API on 8748; the cases `cases/{bank,house,suite,tower,suite-revit}-rooms.json` (the DWGs uploaded, the `*-rooms` settings fixture, saved as v1 of a new project), `tower-aside` and `suite-revit-aside` (the same, then every item of the first build's single-line flags set aside, `cases/set_aside_singles.py`, rebuilt and saved), then `ra13.py` |
| `rooms-offline` | `offline.sh` | the seven versions' offline files with `dist/offline-template` into `<acc>\offline-rooms` |
| `rooms-walks` | `walks.sh` | in Edge, nothing served: `upload-walk.spec.ts` with `WT_ROOMS_PROBES=1` on the seven files, then `stairs.spec.ts` with `WT_ROOMS_OFFLINE_DIR` and `WT_FPS_GPU=1` (the suites in `WT_ROOMS_NO_STAIRS`) |
| `rooms-node` | `node.sh` | R4's `climb.test.ts` on the real bank, house and tower models (`WT_ROOMS_MODELS`) with `WT_R4_TIMING=1` |
| `rooms-golden` | `golden.sh` | `WT_ACCEPTANCE=1`: `test_r_rooms_golden.py` (with its two-process test) and `test_r1_drawings.py::test_ra18_each_door_undone_in_turn` |
| `rooms-checks` | `checks.py` | the figures of RA-1 - RA-18 from every record into `<acc>\rooms-result.json`; `docs/rooms/GAPS.md` is written from it |
| `reference-checks` | `reference.sh` | `reference.mjs versions --check`, `outside --check`, and the store check of R0's copy and of `<acc>\data` against `acc-9nov.versions.sha1` |

`ra13.py` (RA-13 through the served API, the house as a new project `house-fixes`): build 1; then a set-aside with
`floorPast`, an app closing taken out and a closing line drawn, six room fixes (a name, "no ceiling", "no floor here",
"floor here", "it is outdoors", one in no room), three stair fixes (`lines` on the climbable stair, `climb` on the
service stair, a `bottom` on another); build 2; the same DWG uploaded again into a build from build 2's; build 3; the
API's two refusals.

**Also RI's, new**: `services/builder/tests/test_r_rooms_golden.py` (RA-15: the five new-rule builds' outputs pinned, the
summary rows per floor, every model with `stairways`; marked `acceptance`: each build in two child processes with
different `PYTHONHASHSEED` values), `fixtures/rooms/keys/suite.json` (the old suite's 16 key points, picked from the
drawing: its room outlines on Defpoints and the areas the names write; the builder's rooms were not used to pick) and
`docs/rooms/GAPS.md`.

### 3. The runs (11 Nov 2026, `--tmp %TEMP%\wt-ri\acc`; result rows in `result.json`, figures in `rooms-result.json`)

| Step | Result |
|---|---|
| `rooms-builds` (alone) | exit 0, 284 s: the seven cases and `ra13.py` passed. Stamps: bank `54ef1ac240bb` (= `BANK_NEW_RULE_SHA1`), house `c7824bca6008`, old suite `ed7774c64b9b`, tower `3d25cdf722fb`, new suite `424cc8cabd45` (each `built-model/2`), tower with single lines set aside `f6e6fcdf4725` (133 items of 39 flags), new suite so `6a0c916176a3` (59 items of 42 flags). The first run of the step (records kept in `%TEMP%\wt-ri\acc-first-run`) failed the two set-aside cases (the plan fault of `acc.py`, section 1) and showed the stair-fix finding below; the store was then cleared and the step run again whole |
| `acceptance` (the upload milestone's eleven cases, fresh seed under `<acc>\acc`) | exit 0, 1048 s (beside `rooms-golden`): every saved model has its 9 Nov stamp (`c3a9408304a2` twice, `1c07bfeef580`, `205e9c2c46e8`, `2c85c67fe80f`, `91414f408cb2`, `467d3f8444c0`, the last with `OLD_RULES` written by the edit); `suite-revit-prep` failed "there is no office 'dwp-revit'" in this step, as on 9 Nov, which is why the next step exists |
| `acceptance-a12` | exit 0, 17 s: `suite-revit` `1d90d91ef949` (= 9 Nov) |
| `checks` | exit 0: A-1 on both bank cases: model `c3a9408304a2`, CSV `b528bb2320ef` (= v2's), top view `f084b556503c` (= v2's), stages equal, `bank-27oct` script `615d50137bdb` = the prototype's, the version's own script equals the generator's. Its A-9 print failed (a `/c/...` path inside `python -c`; `run.mjs` now writes `C:/...`). A-9's record: `model3EqualsModel2` true; `reuploadFixesEqual` false, only because each set-aside comes back with `floorPast: false` (the rooms milestone's default): `a9.py` now fills that default on both sides, and `rooms-checks` made the comparison again from the run's files: equal |
| `rooms-offline` | exit 0, 2 s: 7 files, 1.07 - 2.43 MB |
| `rooms-walks` | exit 0, 472 s: `upload-walk.spec.ts` 49 passed (2.2 min), `stairs.spec.ts` 57 passed (5.6 min) |
| `rooms-node` | exit 0, 11 s: 9 passed (3 models x climb, times, random walks; the file's other 26 tests filtered out) |
| `rooms-golden` | exit 0, 857 s (beside `acceptance`): **21 passed**: the 12 pin tests, the 5 two-process builds (the same bytes, the pinned ones) and the 4 floors of every door undone |
| `proto-tests` (the prototypes' own tests, unchanged, one at a time under the Edge lock) | 619 s. bank 49, suite 37, house openings 13, house furniture 29, boxes 87 passed; Max checks 137 / 151 / 196; the detector 139 of 143 right and 54 of 54. **view modes 126 of 127** and **hotel 0 of 1** on this run: the viewer's failure was a timed check ("Walk slides along a wall ...", `slid` 0.18) while other runs loaded the machine; the hotel page could not load three.js from its CDN (`net::ERR_CACHE_READ_FAILURE`). Run again alone (`node <acc>\scripts\upload-ur--proto-tests.mjs viewers hotel`): hotel **56 passed**; view modes failed another timed check ("W walks forward", `moved` 0.38 of 0.4: two short steps ran beside it); a third time, nothing else running: **127 passed**. The runner's row says exit 0 for the first run (the script exits 0 whatever its tests say); the per-test logs are in `<acc>\proto\` (`summary-first-run.json`, `viewers-second-run.txt`) |
| `reference-checks` | exit 0: `versions.sha1` 49 unchanged (12 new files: the owner's project); `outside.txt` 589 files, 0 differences, `__pycache__` folders 2 (2 at the start); R0's copy of the 9 Nov store 148 unchanged; the acceptance store `<acc>\data` 148 unchanged (87 new files: the new projects) |
| `rooms-checks` | exit 0: `rooms-result.json`, the figures below and in `GAPS.md` |

### 4. What RI-B found (each also in GAPS.md, classed)

* **A stair fix at a point inside the house's L stair outline finds no stair** (RA-13, first run). The outline that the
  report and the overlay give for `S1` has no vertex at the L's inner corner: its last edge runs from (24.99, 23.15) back
  to (21.64, 21.16), across the empty corner. A point in that triangle (21.96, 22.71) is inside the outline the Check step
  draws but 0.9 m from any tread, and the stair fix there was unmatched (the builder matches a stair fix to the union of
  the stair's flights and landings, `FIX_NEAR` 0.3 m). The Check step's stair panel writes its fix at
  `pointIn(st.outline)`: worked out by hand with the same algorithm on this outline, its point is (21.34, 22.71), about
  0.29 m from the lower flight (the flights taken as rectangles): it should match, by about a centimetre. **For RR
  (check-and-fix now)**: the report's / overlay's outline of an L stair, or the stair panel's point.
* **A-9's `reuploadFixesEqual`** needed the `floorPast` default as well as the three lists (R5.md D-4 did not foresee it).
* **The house's three living-room doors** stop the walker 0.30 m short of their line from the new floor (and 0.45 m from
  the inside, as on 9 Nov): something stands in those openings; not caused by the floor.
* **The new suite's `L1-004`** has no floor on its south side (RA-6's should): the plate stops at the door and nothing
  is flagged there.

### 5. For RI-C (the browser suite and the owner's path) and RR

* **The acceptance store** is `%TEMP%\wt-ri\acc\data`: R0's copy of the upload milestone's store (the eight 9 Nov
  versions, unchanged: checked against `acc-9nov.versions.sha1`) plus seven new-rule projects, each version 1:
  `bank-rooms` (`54ef1ac240bb`), `house-rooms` (`c7824bca6008`), `suite-rooms` (`ed7774c64b9b`), `tower-rooms`
  (`3d25cdf722fb`), `suite-revit-rooms` (`424cc8cabd45`), `tower-aside` (`f6e6fcdf4725`), `suite-revit-aside`
  (`6a0c916176a3`); and `house-fixes` (RA-13's builds, no version saved). Its cache is `%TEMP%\wt-ri\acc\cache`. Use a
  copy of it for the owner's path (RA-12 point 2 by hand: `house-upload` as saved on 9 Nov is in it).
* **The new-rule offline files** (with `dist/offline-template`, 794,264 B) are `%TEMP%\wt-ri\acc\offline-rooms\*.html`
  (seven). For `stairs.spec.ts`: `WT_ROOMS_OFFLINE_DIR` = that folder, `WT_ROOMS_NO_STAIRS=suite-rooms-v1,
  suite-revit-rooms-v1,suite-revit-aside-v1`; for `upload-walk.spec.ts`: `WT_UPLOAD_OFFLINE_DIR` = that folder,
  `WT_UPLOAD_DATA_DIR=%TEMP%\wt-ri\acc\data`, `WT_ROOMS_PROBES=1`, the bank a must file (`WT_UPLOAD_WALK_SHOULD` = the six
  others). RI-B ran both there already (`rooms-walks`: 49 and 57 passed; reports in `%TEMP%\wt-ri\acc\e2e-rooms\`).
* **The eight old versions' offline files were not made by RI-B**: make them from the same store
  (`bank-reupload:1 bank-sampeng:3 house-upload:1 suite-upload:1 suite-outlines:1 tower-upload:1 suite-revit:1
  presidential-suite:2`, as `upload-uf/offline.sh` lists them) for RA-2's walk comparison with
  `docs/rooms/reference/upload-walk-9nov/`.
* **The old acceptance store** (a fresh seed and the upload milestone's eleven cases, re-made today with the same stamps)
  is `%TEMP%\wt-ri\acc\acc\data`; it is not the one to compare with 9 Nov.
* **Runner caveat**: two `run.mjs` processes of the earlier code at once overwrote each other's rows (the rows of
  `rooms-walks` and `rooms-golden` were put back from their logs, marked `restored`); the merge is in
  now. Run one runner at a time where you can; `acceptance` and `acceptance-a12` must both run (the second gives the new
  suite its office first). `rooms-builds` copies the store only when `<acc>\data` is missing; run on a store that already
  holds its projects, its cases fail at "create": clear `<acc>\data`, `cache` and `out` to run it again.

### 6. The acceptance table (RI-B's runs; "RI-A" = its runs of 11 Nov, section 3 of RI-A)

| RA | Grade | Verdict | Numbers |
|---|---|---|---|
| RA-1 old rule untouched, new drafts get the new rule | must | PASS | bank both ways `c3a9408304a2`, `built-model/1`; CSV `b528bb2320ef`, top view `f084b556503c`, stages, `bank-27oct` script `615d50137bdb` equal (check_a1); the other old cases' stamps through the API = 9 Nov (house, old suite, outlines, tower, new suite twice, the A-12 two with `OLD_RULES` written out); `test_r_old_rule.py`, the summary golden, `hotel-2nov` and the four draft cases (`test_r5_builder.py`): RI-A's runs; the seven new projects' drafts all got `NEW_RULES` |
| RA-2 saved versions never change; old versions look and walk as before | must | PARTLY (RI-B's part passes) | `versions.sha1` 49 unchanged; the 9 Nov store 148 files unchanged in both copies; the old versions show no Ceilings tick (stairs.spec, the six `dist/offline` files); seed and walk-parity: RI-A. Not run here: `upload-walk` on the eight old versions, the old browser specs (RI-C) |
| RA-3 rooms | must (new suite should) | PASS | bank 18 / 18 names in their rooms; the house's living room 81.6 m² holds (26.2, 11.1), the east building's 4 rooms 7.9 / 1.2 / 2.1 / 4.1; old suite 16 / 16 names in a room; tower: a room within 2.5 m of all 13 probe sides; new suite `BAR`, `BOH.` names. Gate line as it stands: the bank, every room closed with no staff fix; the house, not without two staff answers (`slab-gap` 16.8 and 28.8 m²) |
| RA-4 slab areas | must bounds, should ranges | PASS (2 shoulds explained) | plate0 235.8 / 295.7, 507.7 / 450.9, 848.7 / 739.8, 471.1 (53.2 of terrace), 274.2: all inside must and should; (26.7, 13.0) not on the plate; written areas 8 / 12 within 15 %; against the prototypes' slabs: the bank and the house's ground floor under 15 %, the house's upper floor 15.2 % and the old suite 27 % (explained in GAPS.md: the cut voids; the garden side) |
| RA-5 holes | must | PASS | house upper void 26.12, stair hall 16.62, well 4.39, service stair 3.93, duct and slots listed; bank lift shaft 3.17 / 3.13, L2 well 7.13 (+ 2.28 the next stair's own footprint); tower 4 shafts 2.81 - 3.06 per floor, stair A's well 11.52, stair B 17.24; no hole on the house's ground floor or the suites |
| RA-6 the floors that were missing | must (new suite should) | PASS (the new suite's should missed on one side) | builder: house 4 / 4, old suite 2 / 2 sides, tower 13 / 13; browser: house 4 / 4, old suite 1 / 1, tower 8 / 8 stand on floor; set aside: tower 13 / 13, plates 848.5 / 739.6, new suite 274.3; the bank's walk 80 walls, 39 doors, 30 + 14 glass, all pass; new suite 5 / 6 sides (`L1-004` south: no floor) |
| RA-7 names | must bank, should old suite | PASS | bank 18 / 18 and 23 names (labels); old suite 15 / 16 against `keys/suite.json` (`GYM&YOGA` goes with the study, where it is written) |
| RA-8 ceilings | must | PASS | heights (underside) 2.98 / 2.88 house, 2.98 bank and tower, 2.68 suites; in Edge the ray up meets them at 3.88 / 7.68 (house), 2.98 / 6.68 (bank), 2.98 / 6.98 (tower), 2.68 (suites); hidden in Orbit, shown in Ghost and Walk, the tick hides them |
| RA-9 stairs read | must house, bank; should tower | PASS | house `S1` L, 21 x 0.186, 19 treads, 1 landing, `walk[1]` 0.26 m from (20.40, 21.15); bank `S1` 21 x 0.176, 3 landings; tower `S1` U, 20 x 0.200; stair B, ST-05, ST-02, the bank's next stair and north stair flagged with their reasons; no `step` part |
| RA-10 climbing | must house, bank; should tower | PASS | Edge (57 passed): up and down every stairway, past the last riser 1.37 / 1.28 / 1.45 m, largest rise a move 0.186 / 0.177 / 0.200, `crosses` never; the keyboard climb, the stale foot, the floor buttons; Node (`climb.test.ts`, the real models): 9 passed |
| RA-11 the 3ds Max script | must | PASS (here: the texts) | `#tread`, `#landing`, `#ceiling` parts in the three stair scripts, the storey property on treads and landings, no Poly word, "21 risers of 0.186 m" on the house, the hidden Ceilings note; the mock interpreter: R3's tests in RI-A's run |
| RA-12 the owner's path | must | not RI-B's | RI-C (`rooms.spec.ts` with the real worker); point 4: the bank's defaults give `54ef1ac240bb` (RI-A), the bytes pinned here |
| RA-13 fixes survive | must | PASS (one finding) | 1 set-aside, 2 closings, 5 of 6 room fixes (the 6th, in no room, unmatched and flagged), 3 stair fixes matched; the re-upload carried all six lists, the same fix rows and the same model bytes; 422 for a 201-character name and 5,001 fixes. Finding: a stair fix at a point inside the house's L outline found no stair (section 4) |
| RA-14 times | should | PARTLY | builds 9.3 / 13.7 / 5.2 / 24.2 / 13.9 s (budgets 45 / 60 / 90 / 90 / 90; at most 8.8 s over the old rule); peak 221 MB; GPU 60 fps on the bank, house and tower (longest frame 17.2 ms); Node first view 17 - 76 ms (tower: 0.35 s allowed), a move on a stair 42 - 52 µs; new browser specs 5.6 + 2.2 min. Missed: `test:builder` 17 min 19 s under load (RI-A; 15 min). Not measured: the old versions' first view against the viewer of before |
| RA-15 determinism, references | must | PASS | the five builds in two processes: the same model, CSV, stages, top view, Max script, and those are the pins (provisional); every new-rule model has `stairways`, `built-model/2` |
| RA-16 suites, prototypes, nothing else moved | must | PASS (RI-B's part) | the prototypes' tests all pass (view modes 127 and hotel 56 when run alone; see section 3); `outside.txt` 0 differences, no new `__pycache__`; nothing deployed; the suites: RI-A |
| RA-17 staff fix time | should | not run | RI-C |
| RA-18 a missed doorway does not cost the floor | must | PASS | every door undone, the 4 floors (`WT_ACCEPTANCE=1`); with every door found: doorway closings bank 0, house 2 / 0, tower 2 / 1, old suite 1; new suite (reported): 6, and with its 59 single-line items set aside 3 passages found (8 before), 16 rooms, plate 274.3 m² |

## RI-C: the browser suite and the owner's path (12 Nov 2026, 00:14 - 01:30; WORK_BREAKDOWN RI items 5, 7 and 9)

Ports: the e2e config's 5711 / 8711 for `npm run test:e2e`, 5748 / 8748 for the owner's path. `WT_TMP=%TEMP%\wt-ri`, RI-C's
files under `%TEMP%\wt-ri\ric` (scripts in `ric\scripts`, logs in `ric\logs`), screenshots in `%TEMP%\wt-ri\path`. Nothing
deployed, pushed or committed; `app/data`, `dist/`, the prototypes and 5710 / 8710 untouched (at the end:
`reference.mjs versions --check` 49 unchanged, 12 new files, the owner's; `outside --check` 589 files, 0 differences,
`__pycache__` 2 as at the start). **No app file changed**: no code, test, fixture or config (so no frozen file); only this
section and `docs/rooms/GAPS.md` (section 7's RA-17 line and the new section 8).

### 1. `npm run test:e2e`, every spec (RI item 5)

Set-up (`ric\scripts\e2e.sh`):
* a fresh seed into `ric\seed` (the five stamps) and its five offline files made with `dist/offline-template` (RI-A's
  `npm run build` of 23:05; no viewer file changed after it) into `ric\seed-offline`: `WT_DATA_DIR`, `WT_OFFLINE_DIR`;
* `WT_UPLOAD_OFFLINE_DIR` = `ric\walk-offline`: the eight old versions (`bank-reupload:1 bank-sampeng:3 house-upload:1
  suite-upload:1 suite-outlines:1 tower-upload:1 suite-revit:1 presidential-suite:2`) and the seven new-rule versions, all
  made by `make-offline.mjs` from RI-B's store `%TEMP%\wt-ri\acc\data` (the seven equal RI-B's `acc\offline-rooms` byte
  for byte); `WT_UPLOAD_DATA_DIR` = that store; `WT_ROOMS_PROBES=1`; `WT_UPLOAD_WALK_SHOULD` = the six "should" files of
  9 Nov and the six new-rule drawings but the bank (a must file);
* `WT_ROOMS_OFFLINE_DIR` = the seven new-rule files, `WT_ROOMS_NO_STAIRS` = the three suites;
* the config's own servers: a freshly seeded store, the real API and worker.

**393 passed, 0 failed, 0 flaky, 0 skipped, in 35.2 min** (9 Nov: 278). Nothing failed, so nothing was fixed or re-run.

| Spec | Passed | Minutes | Spec | Passed | Minutes |
|---|---|---|---|---|---|
| furniture | 68 | 3.3 | stairs (the 7 new-rule files) | 50 | 3.5 |
| leak | 2 | 0.3 | structure | 52 | 1.9 |
| modes | 40 | 6.6 | upload-walk (15 files x 7) | 105 | 3.3 |
| offline | 11 | 0.6 | upload (real worker) | 3 | 4.5 |
| plan-canvas | 18 | 0.9 | web-leak | 3 | 0.6 |
| replay | 19 | 1.9 | web | 19 | 2.1 |
| rooms (real worker) | 3 | 4.7 | | | |

* **`rooms.spec.ts` with the real API and worker, for the first time** (R6.md section 4): point 3, the fixes on the
  reference building, each rebuilt (1.5 min); point 1, the house as a new project, named "Living", saved
  `built-model/2`, climbed (2.9 min); point 2, a recipe without the three keys gets the new rules without the Floors step
  (18 s). **`upload.spec.ts` A-7 with the real worker** (the fold's "earlier way" before the build): 3.6 min, and the
  hostile DXF and the grey-family tests: 3 passed.
* **The eight old versions, probe by probe against 9 Nov** (R7's `compare-upload-walk.mjs` against
  `docs/rooms/reference/upload-walk-9nov/`, result `ric\uw-compare.json`): 8 compared, **every report equal value for
  value**; the verdicts as on 9 Nov (the two bank files pass every check; the six "should" files keep their failing doors,
  glass and walls). All eight open with no error.
* **The new-rule files**: the seven `upload-walk` reports, the RA-6 probes included, equal RI-B's (`acc\e2e-rooms`) key
  for key; `stairs.spec.ts`'s climbs, stale-foot, floor-button and ceiling records equal RI-B's but for the file path.

### 2. The owner's path in Edge (RI item 7)

**Set-up.** A copy of RI-B's store (`ric\path-data`) and a fresh cache (`ric\path-cache`); the servers started at 00:54,
after the last code change (none was made during RI-C): `node tools/run-api.mjs --port 8748 --data ric\path-data` and
`npx vite -c apps/web/vite.config.ts --port 5748` with `WT_API_PORT=8748` and `VITE_WTV_TEST_HOOK=1` (the hooks `__plan`,
`__viewer`, `__host` were only read; the owner's `npm run dev` does not set it), `ric\scripts\path-servers.sh`. Headless
Edge drawing with the laptop's GPU (ANGLE, Intel Iris Xe, D3D11), 1400 x 880, under the Edge lock. Driven by
`ric\scripts\owner-path-rooms.mjs` (grown from the upload milestone's `tools/rooms/acceptance/upload-uf/owner-path.mjs`):
clicks, typing, the file picker, mouse drags and keys only; the API read only to wait for runs and read what was built.
93 screenshots and one JSON log per part (`%TEMP%\wt-ri\path\<part>.json`). No dialog, page error or console error in
any part.

**The house from its DWG** (`owner-house`, 2.1 min of screens):
* Files: verdict `minor`, read in 23 s, units confirmed with the button; the new draft's options are `NEW_RULES`.
* Layers: 55 rows, 13 roles set with their selects to the `house-rooms` fixture's.
* Floors: both areas drawn as boxes on the sheet, keys and names typed, levels picked from the level tags (+0.90 / +4.80),
  walls 3.90 / 3.50, door and window heads, **ceiling heights typed 3.00 / 2.90**; the line reads "Floor plates,
  ceilings and stairs are built the new way."; the fold "Earlier build rules" closed; no floor issue.
* Build (18.5 s): the checklist clear; the counts ground 22 rooms closed, 0 names, 1 stair to climb; upper 24, 0, 0.
* Check: the page's counts equal the overlay's (ground 22 rooms, 0 holes, 1 of 7 stairs climb; upper 24, 4, 0 of 1); the
  two areas with no floor (16.8 and 28.8 m², no mouth) answered **It is outdoors** (GAPS 5.2); 13 grey families given
  their kinds; Rebuild (20.4 s): no area left open, no lost-floor row.
* Save: `built-model/2` (stamp `cf72c28762e3`), the three counts on the Save step.
* Viewer, **Walk**: Orbit, the Ground floor button, the view dragged to look down, a double-click on the floor at `S1`'s
  foot (it landed 0.05 m from the aim), a drag to face the flight, **W held**, a drag at the landing's turn: up from 0.90
  to 4.80 m in 8.2 s, the Upper floor named and its button marked, 1.1 m past the top riser, never more than 0.186 m a
  move; down the same way in 7.6 s. **Ceilings**: in Walk both floors' ceilings show (looking up: the ceiling with the
  stair hall's opening), in Orbit none, the Ceilings tick hides and shows them. The Max download has `#tread`,
  `#landing`, `#ceiling`, "21 risers of 0.186 m" and no Poly word.
* The first run's climb failed **in the script, not the app**: its double-click aimed through the oblique Orbit view met
  a wall top and the walker landed 6.9 m away. The script now drags the view to look down and checks the aim point's ray
  first; the viewer part was run again on the saved version (`owner-path-rooms.mjs viewer owner-house 1`): the record above.

**The bank from its two DWGs** (`owner-bank`, a new office, 2.0 min): Files `ok` / `ok` (19 s); Layers 36 rows, 8 set;
Floors 0 / 3.70, walls 3.70, ceilings left to the default; the line "new"; Build 18.8 s (L1 15 rooms, 12 names, 1 stair;
L2 14, 11, 0); the Check counts equal the overlay's; the family `Fritz-Hansen_SH200 - Default` given "seat"; Rebuild:
**`54ef1ac240bb`, the bank's pinned new-rule model (`BANK_NEW_RULE_SHA1`) byte for byte, through the screens**; Save
`built-model/2`; `S1` climbed by W and the mouse, 0 -> 3.70 m, L2 marked, 8.9 s, and down in 8.3 s; ceilings shown in
Walk, hidden in Orbit, the tick works; the Max script says "21 risers of 0.176 m".

**The house as saved on 9 Nov, New version, without opening Floors** (RA-12 point 2 by hand, `house-upload` in the store
copy; its recipe has none of the three keys): **New version**, **Use the files of v1 again**, straight to Build: the
draft's options are `NEW_RULES`, the line says "new", built in 22.8 s (`bd0ddf674b9b`); Check: the living room
(`ground-R020`, 81.6 m²) holds (26.2, 11.1), `S1` climbs (21 x 0.186 m); Save: version 2 `built-model/2`, **version 1's 12
files unchanged**; the saved ground slab holds (26.2, 11.1); in Walk `S1` climbed by keys in 8.2 s.

**The tower and the new suite, timed (RA-17)**: GAPS.md section 8. In short: neither has a room left open after its
first build (no `slab-gap` flag, no unfloored area), so the minutes until every room is closed or answered are 0; the
review of their rooms flags (every `single-line` flag's items set aside, the doorway, stair and room-name flags looked
at) took 1.6 and 1.7 min scripted with one rebuild each, about 22 and 23 min estimated for a person (target 30); the second
versions, with the 133 and 59 set-asides carried over, built the same models and asked nothing: 0.8 and 0.4 min scripted,
about 2 min for a person (target 15). Through the screens the new suite gave the pinned `424cc8cabd45` and then RI-B's
`6a0c916176a3` byte for byte; the tower RI-B's `tower-aside` model but for two project fields this run left as proposed.

### 3. The acceptance rows RI-B left to RI-C

| RA | Grade | Verdict | Numbers |
|---|---|---|---|
| RA-2 saved versions never change; old versions look and walk as before | must | **PASS** (with RI-A's and RI-B's parts) | `upload-walk` on the eight old versions: 8 of 8 reports equal 9 Nov's value for value, all open with no error; structure 52, modes 40, furniture 68, replay 19, offline 11, upload-walk 105 passed unchanged on a fresh temp store; `versions.sha1` 49 unchanged after RI-C |
| RA-12 the owner's path through the screens | must | **PASS** | `rooms.spec.ts` points 1 - 3 with the real worker, `upload.spec.ts` A-7 with the real worker (point 5), no dialog or page error (point 6); point 4: `54ef1ac240bb` through the API (RI-A) and through the screens (above); by hand: the house and the bank from their DWGs to the viewer, both stairs climbed by keys up and down, ceilings in Walk only; the 9 Nov house's New version without Floors: `built-model/2`, (26.2, 11.1) on the plate, `S1` climbs, version 1 unchanged |
| RA-17 the staff's fix time | should | **PASS, estimated** | rooms closed at the first build on both; flag review 1.6 / 1.7 min scripted, about 22 / 23 min for a person (30); second versions 0.8 / 0.4 min scripted, about 2 min (15); a person's timing is the review's (RR's staff-path reviewer) |

### 4. Notes for RR

* **A second pass of set-asides**: after every item of the first build's `single-line` flags is set aside, the next
  build flags 1 (tower) and 6 (new suite) lines that were not in that list (lines whose partner face was set aside). A
  person makes a second pass; RI-B's `tower-aside` / `suite-revit-aside` versions have the same leftovers.
* **The Check step opens on the whole sheet**: the house's sheet holds the elevations and both plans, so the floor on
  screen is small until zoomed (as in the upload milestone; not new).
* **The Walk view at the top of the house's stair** faces a wall 1.1 m past the top riser (the picture is one colour): the
  walker stops there, as R7 measured (1.37 m in its probe walk).
* Not done by RI-C: a person's own timing of RA-17; Walk with W in software-drawn Edge (the owner's path used the GPU, as
  the owner's Edge does); the opening and grey-furniture flags of the tower and the suite (not rooms questions); phones
  and tablets (PC first).
