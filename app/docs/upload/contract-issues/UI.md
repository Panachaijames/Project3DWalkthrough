# Contract issues: UI, the integration step of the upload milestone (9 Nov 2026)

Written only by step UI (docs/upload/WORK_BREAKDOWN.md UI). It settles every item of `U0.md` ... `U7.md` with the smallest
change, says where a frozen or another step's file changed, and records what the acceptance runs measured
(`docs/upload/GAPS.md` holds the gap report). "Accepted" means the design is read the way the item says from now on;
"changed" names the file and the change. Nothing was committed, deployed, published or pushed.

## 1. Changes made here (each the smallest that settles its item)

| File (owner) | Change | Settles |
|---|---|---|
| `services/api/tests/test_u5_builder.py` (U5) | `RUN_WITHOUT_THE_FLAG = True`: the two real-worker tests run in every `npm run test:api` (they still skip with no builder Python or LibreDWG, and fail then under `WT_INTEGRATION=1`) | U5-8 |
| `services/builder/walkthrough_builder/step.py` (U1) | `_suggest` logs `propose.notes()` after the proposal: the prepare run's messages carry U-3.3's plain sentences ("The floors are a guess: ...", the units note); a failure there is a warning, never a failed proposal | U2.md section 1 (the proposal's notes) |
| `services/builder/walkthrough_builder/out/overlay.py` (U4) | `OverlayFloor.setAside` lists the key the fix matched in this drawing (U3's report row `key`), else the ref's own key | U4-2, U3-3 |
| `apps/web/test/e2e/upload-kit.ts` (U6) | `uploadProfileScript` runs U4's command line (`-m walkthrough_builder.out <model> --profile upload --date <d Mon yyyy> --sources dwg:mm,... --converter-version 0.14`), the way `write_outputs` calls the generator. The old code passed `files=` and `units=`, which U4's final `maxscript()` does not take (U4-6): A-7's real-API branch would have failed on a TypeError | U6-5, U4-3, U4-6 |
| `tools/upload/make-fixtures.py` (U0) | `maxtexts` is no longer a part, so neither a full run nor `--only` can overwrite U4's profiles | U4-5 |
| `fixtures/upload/{drawing/bank1, drawing/sukhumvit}.drawing.json`, `plan/sukhumvit.plan.json.gz` (U0) | replaced by U2's re-made reads (`%TEMP%\wt-u2\u2-fixtures`, U2.md section 4; `plan/bank1` was already equal) | U0-10, U2.md 4, ACCEPTANCE 2.5 |
| `fixtures/upload/conversion/{bank1,presidential}.conversion.json` (U0) | replaced by the worker's real published reports from the acceptance prepares (bank1 `ok` with no `other` class and no note; the suite's 15 lost blocks, 4 placed with their inserts in sheet m) | U0-10, U1-4, ACCEPTANCE 2.5 |
| `fixtures/upload/runs/bank-prepare/job.json` (U0) | its `outputs` sizes and sha1s for the three bank1 files above (the FakeJobRunner's record must match the bytes it copies) | follows from the two rows above |
| `services/builder/tests/test_u2_reference.py` (U2) | `test_provisional_fixtures_remade` now expects no key to differ: the fixtures it compares with are the reader's own re-made files since this step (it expected the house's two ATTRIB keys to differ from the provisional ones) | follows from the replaced fixtures |
| `fixtures/README.md` (U0) | the three `max-texts/*` rows carry U4's final profiles and their sha1s; the `--only` list without `maxtexts`; the six replaced fixtures and `runs/bank-prepare/job.json` with their new sources and sha1s | U4-5, U0-10 |

## 2. Items settled without a change (accepted readings, or done by a builder already)

* **U0-1** the folder: `docs/upload/contract-issues/` stays (WORK_BREAKDOWN's `docs/contract-issues/U<n>.md` is read as this
  folder for the upload milestone; the foundation's `docs/contract-issues/` keeps its own files).
* **U0-2, U0-3, U0-6, U0-8, U0-9** accepted as written. **U0-4** settled by U5 (the API conftest makes `<WT_TMP>/api-tests`).
  **U0-5** settled by U2 (`~<index>` for a repeated part; MINSERTs repeat nothing in ezdxf 1.4.4). **U0-7** settled by U2
  (`read.ReadFailed`, code `read_failed`, a plain sentence naming the upload).
* **U1-1** accepted; **U5-7 is superseded** by it: `launch.json` and `job.json` carry the same pair (the venv launcher's),
  as U1 checked through U5's own `LocalJobRunner` on 9 Nov. **U1-2, U1-3, U1-5, U1-6, U1-7, U1-9, U1-10, U1-12** accepted.
  **U1-8** done by U5 (prepares get `paths.versionModel`).
* **U2.md 1 - 3** accepted (keys, `read_failed`, the measured differences, the loose spots). Its proposal notes: changed
  above.
* **U3-1** confirmed: `build.errors.BuildError(code, message, step)` stays in U3's package; U1's `step.py` keeps any
  exception's RunErrorCode `code` and `step`. **U3-3** answers U4-2 (changed above). **U3-4, U3-5** accepted. **U3-6**: the
  house's three sliding glass doors (eitherKind, glazed like windows by design) are counted in GAPS.md, not skipped by
  the walk.
* **U4-1** accepted: the fitSlabs camera keeps U-11.2's direction and moves back 5 % at a time until every slab corner is
  8 px inside the 1400 x 880 canvas and clear of the panel (U-11.2's factors alone fail its own check on every model);
  `upload-walk.spec.ts` judges the same rule in Edge. **U4-3** accepted (the script's date is the local date of the
  moment `write_outputs` runs; A-7 compares with `formatDate(result.finishedAt)`, the same day unless a build crosses
  midnight). **U4-4, U4-6 - U4-9** accepted; `fixtures/upload/max-texts/upload.json` ships with the app (read at run time).
* **U5-1** fixed by U3 (a probe with no side is left out): the small DXF now builds end to end through the API (below).
  **U5-2** accepted: `versions/<n>/source/flags.json` stays `{format: 'build-flags/1', flags: Flag[]}`; nothing reads it
  yet, so no contract type is added in this milestone. **U5-3 / U6-3** accepted as a known gap: no field carries
  "remember this furniture word for the office", so `OfficeMapping.furnitureWords` is never written in this milestone
  (proposed for later: `SaveBuildRequest.rememberWords`). **U5-4, U5-5, U5-6** accepted.
* **U6-1** accepted for this milestone (proposals as buttons previewed through `area`, level tags and picked points as
  info flags; `marks` / `boxes` props proposed for later; the frozen `PlanCanvasProps` is not changed). **U6-2** settled by
  U5 as built: `settings_issues()` checks only the office id's pattern, and `saveBuild` with `rememberMapping` creates a
  missing office file (name = id). **U6-4** no change: both `upload.spec.ts` tests save a version, so every `e2e-*`
  project in the list has one (see the e2e run below). **U6-6 / U7-1** confirmed: the canvas leaves Delete to bubble and
  the Check step sets the selection aside. **U6-7 - U6-9** accepted.
* **U7-2 - U7-9** accepted: block picks leave out anchors holding 25 % or more of a sheet; `extents` kept; flags and diff
  drawn for the overlay's floor; A-6's "left of the panel" read as "clear of the panel" (the panel is on the left); the
  spec's own variables `WT_UPLOAD_DATA_DIR` and `WT_UPLOAD_WALK_SHOULD`; the redraw budget measured with a read-back;
  the API's CSV guard (`furniture_csv.py`) guards `str(value)` of the same ten text columns as the viewer's.

## 3. Found at integration (new items, each settled)

* **UI-1, A-7's expected Max script (fixed, see section 1):** U6's real-API helper called `maxscript(model, profile,
  files=..., units=...)`, U4's stub signature; U4's final one is `maxscript(model_bytes, profile, *, date, sources,
  converter)` (U4-6). The helper now runs U4's command line, as U4-3 documents.
* **UI-2, the A-12 drawing's partitions are on layer `0` (information, for the owner):** `presidential suite_layout.dwg`
  (the 3D team's Revit export of 9 Nov) has its interior walls at the top level on layer `0` (99 solid fills, 84
  wall-like pairs among 2,634 items). The office mapping leaves layer `0` as `other`, so the build has only the facade,
  columns and a few `A-WALL` walls, and its plate is 35 m2. Tried once with layer `0` set to `wall` (not saved): 47
  walls, a 175 m2 plate and 37 openings, plus 42 single-line items from layer `0`'s other line work to set aside on the
  Check step. Not a fault of the app: staff can do that now, the seam for doing it by itself is "walls found by shape on
  a mixed layer" (U-16), and the quickest answer is an export with the walls on their own layer. Details in
  `docs/upload/GAPS.md` section 5.
* **UI-3, a re-drawn seeded project keeps its old frame (information):** a new version of a seeded project pins its latest
  version's offset (U-9.6), also when the new drawing is in another frame: A-12's version 2 of `presidential-suite` sits
  about 3.5 km from the origin (it builds, renders and walks). By design; staff reset the offset on the Floors step for
  a re-drawn project. Recorded, no change.
* **UI-4, units on a Revit export (information):** `presidential suite_layout.dwg` says inches and its doors say
  millimetres (7 to 0), so `runBuild` answers 409 `units_unconfirmed` until the Files step's Confirm, as U-7.4 designs.
* **UI-5, the reload in a real terminal stopped the whole app (fixed 10 Nov; was "the headless reload", information):**
  `npm run dev`'s uvicorn `--reload` stops its server with `CTRL_C_EVENT` on Windows. In this session (no console) the
  event never reached the server, so a reload during a build run logged "Reloading..." but kept the old server, and the
  run ended `done`. In the owner's PowerShell (their check of 10 Nov) the event reached every program in the terminal:
  one `.py` file with a new date stopped the API, the web server and npm (both npm scripts asked "Terminate batch job
  (Y/N)?", concurrently ended the web side, the prompt came back, nothing restarted). **Fix:** `dev:api` no longer
  passes `--reload` (`app/package.json`, frozen after the scaffold, changed on the owner's report) and
  `tools/run-api.mjs` refuses `--reload` on Windows (exit 2): the restart's Ctrl+C also reaches `run-api.mjs`, whose
  SIGINT handler ends uvicorn, so a terminal of its own would not help either. After an API change: Ctrl+C, then
  `npm run dev`. **Checked the same day in real consoles** (hidden console windows, Ctrl+C sent with
  `GenerateConsoleCtrlEvent`, and once through a pseudo-terminal as Windows Terminal sends it), by two agents with
  separate harnesses on a temp copy of the store: the old pair with `--reload` died as in the owner's window (ports free
  within 3 s, nothing came back); `npm run dev` from the project folder and from `app/` kept both servers and the same
  API processes through new dates on three `.py` files and an edit-and-restore; Ctrl+C (also twice) freed both ports in
  under a second, and in PowerShell no prompt waits (in cmd.exe one waits for Y); Ctrl+C during a bank build run and
  during the reading: the worker (no console, its own process group) carried on, and after `npm run dev` the run was
  adopted and ended `done`; with the worker gone before the restart, the start-up marked it `interrupted` and "read
  the drawings again" worked. A second `npm run dev` while one runs stops at the port check without touching the store.

## 4. The integration runs (9 Nov 2026; details in the step's report and `docs/upload/GAPS.md`)

| Check | Result |
|---|---|
| A-1 bank re-upload, both forms | model `c3a9408304a2` (v2's bytes), CSV `b528bb2320ef`, top view `f084b556503c`, DXFs `9167d084` / `c88491df`, verdicts ok / ok (148 / 143 hatch lines), openings 24 + 25 equal to `detector/output` (`floor` aside), `bank-27oct` Max = `Bangkok_Bank_Sampeng.ms` (`615d50137bdb`), the version's `.ms` = the upload profile with the build's date, stages lines / rings / sheet / source equal v2's |
| A-5 house, suite, tower | all `done`, validated, saved, opened offline; house shift (-74.0221, 0) spread 0.9 mm; suite furniture 127 against 120 (should, +5.8 %); every gap classified in GAPS.md |
| A-6 walks (`upload-walk.spec.ts`, 8 offline files) | bank re-upload and bank v3 pass every check; the others run, their failing probes classified in GAPS.md |
| A-7 (`upload.spec.ts`, real API and worker) | both tests pass (5.2 min and 33 s) |
| A-8 office memory | `e2e-revit.json` (A-7) and `acceptance-revit.json` hold the bank's 31 roles; L29 gets the 13 layers `from: 'office'`; bank v3's proposal keeps L1 / L2, v2's naming, offset [1.212, 0.348] |
| A-9 fixes | set-aside, whole block (108 items), opening fix, outline edge: all matched by key, then again after the same DWG was uploaded into a new build (model bytes equal) |
| A-10 times | bank prepare 29.8 s, build 21.5 s; house build 15.5 s; suite prepare 90.7 s, build 7.8 s; house sheet redraw 12.4 ms median; peak child 675 MB |
| A-12 Revit suite (should) | converts `ok`, reads, builds, saves, opens, Max script and CSV download; partitions on layer `0` (UI-2) |
| A-11 nothing else moved | the prototypes' own tests pass unchanged (viewers 127, bank 49, suite 37, house openings 13, house furniture 29, hotel 56, boxes 87; Max checks bank 137, suite 151, hotel 196; detector 139 / 143 and 54 / 54); 616 files outside `app/` identical before and after (sizes and times), no new `__pycache__`; `npm run seed` the same 5 stamps, then `app/data` put back byte for byte |
| Suites | `check:pins` ok; `typecheck` 0 errors; `test:unit` 807 in 70 files; `test:builder` 677; `test:api` 458 and `WT_INTEGRATION=1` 458 (the real worker on the small DXF and the bank included); `gen:api` no change; `check-openapi-additive` ok; `build` ok; `test:e2e` 278 (27 min, none flaky); the staff path on `npm run dev` with a store copy in Edge, 15 screenshots in `%TEMP%\wt-ui\path` |
