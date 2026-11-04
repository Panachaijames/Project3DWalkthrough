# Work breakdown: the upload milestone (4 Nov 2026; revised after two reviews, DESIGN "Review notes")

One **scaffold** step (U0), then seven **builders** (U1 - U7) in parallel, then one **integration** step (UI), then an
**independent review and fix** step (UR). Builders
do not talk to each other: the interfaces are `upload-contracts.ts` (shapes), `walkthrough_builder/contracts.py` (the
builder's internal calls, written by U0), `DESIGN.md` (cited U-n) and the foundation's frozen files. Each builder owns a
disjoint set of files; it may read anything, write only what it owns.

## 0. Rules for every step

* Everything in `../WORK_BREAKDOWN.md` section 0 still holds (write only inside `app/` and your own `%TEMP%\wt-<step>`;
  never deploy, publish or release; no installs after the scaffold; exact versions; drawing text as text only; the Bash
  tool collapses double backslashes, so code with backslashes goes into files; `PYTHONIOENCODING=utf-8`; one headless
  Edge at a time through `tools/edge-lock.mjs`; prototype Python only with `-B`; your own ports and temp folder; frozen
  files are frozen, a defect goes in **your own** `docs/contract-issues/U<n>.md`).
* **Git:** the project folder is a repository on branch `milestone-upload`. No step commits, switches branches or pushes
  (the main session commits). `git show`, `git diff` and `git status` are fine.
* **The prototypes are read-only, and so is running them:** the prototype builders write into their own folders, so
  they are only ever run in a scratch copy (`npm run make:reference -- --out <WT_TMP>/ref` does that). Never run
  `bank_test/src/build_model.py` or any prototype generator in place.
* **Heavy tests** (a real drawing converted, read or built in the test process, marker `heavy`) take the machine run
  lock `%TEMP%\walkthrough-run.lock` (the worker's own lock, U-3.5); tests that spawn the worker (marker `worker`) never
  take it themselves (the lock belongs to a process: the worker would wait on its own test). When one waits, another
  builder's drawing is running: let it wait. The presidential drawing needs about 1 GB and a minute: run it only in the
  tests that need it.
* Set for every run: `WT_TMP=%TEMP%\wt-u<n>`, `WALKTHROUGH_DATA_DIR=<WT_TMP>\data`, `WALKTHROUGH_CACHE_DIR=<WT_TMP>\cache`,
  and your ports. Never use `app/data` or the default cache in a test. **`WT_REF`** (default `%TEMP%\wt-u0\ref`) is the
  scaffold's `make:reference` output, shared and read-only: never write into it, never re-make it whole (a builder that
  needs a fresh copy of one drawing runs `make:reference -- --only <drawing> --out <WT_TMP>\ref`).
* Your final report: files written, what passes (commands and counts), what does not, contract issues raised.

## 1. Ports and temp folders (a new range: nothing of the foundation's 57x0 - 5726 / 87x0 - 8726 / 47x0 - 4726 / 97x0 -
9726, nothing of the prototypes' 93xx - 94xx)

| Step | Web dev / harness | API | Preview | CDP | `WT_TMP` |
|---|---|---|---|---|---|
| U0 scaffold | 5730 | 8730 | 4730 | 9730 | `%TEMP%\wt-u0` |
| U1 intake and jobs | 5731 | 8731 | 4731 | 9731 | `%TEMP%\wt-u1` |
| U2 reader and suggestions | 5732 | 8732 | 4732 | 9732 | `%TEMP%\wt-u2` |
| U3 model builder | 5733 | 8733 | 4733 | 9733 | `%TEMP%\wt-u3` |
| U4 outputs | 5734 | 8734 | 4734 | 9734 | `%TEMP%\wt-u4` |
| U5 API | 5735 | 8735 | 4735 | 9735 | `%TEMP%\wt-u5` |
| U6 web screens | 5736 | 8736 (mock) | 4736 | 9736 | `%TEMP%\wt-u6` |
| U7 plan canvas | 5737 | 8737 | 4737 | 9737 | `%TEMP%\wt-u7` |
| UI integration | 5711 (e2e), 5710 (dev) | 8711 (e2e), 8710 (dev) | 4711 / 4710 | 9738 | `%TEMP%\wt-ui` |
| UR review and fix | 5739 | 8739 | 4739 | 9739 | `%TEMP%\wt-ur` |

---

## U0. Scaffold (runs first, alone; ports 5730 / 8730 / 4730 / 9730; temp `%TEMP%\wt-u0`)

Goal: a workspace where every later step only writes code. The owner approved the builder venv on 4 Nov (plan decision
row of 4 Nov; DESIGN U-18.2); it is the only supported path. Its install needs PyPI once: if the network is not there,
stop at step 2 and report (the system Python lacks pytest and keeps its libraries in the user site).

1. **LibreDWG, from the zip.** Copy the release zip `%TEMP%\claude\c--Users-DWP2-Desktop-Project-walkthrough\e1e2f8a1-
   5b17-462a-bbe8-01925d989674\scratchpad\p0\tools\libredwg-0.14-win64.zip` to `app/vendor/libredwg-0.14-win64.zip`,
   check its sha1 (`edb5c01152c3ea9bcb46175aa3403fd18b941ff3`), and **extract** all 75 entries into
   `app/vendor/libredwg-0.14-win64/` with `tools/vendor-libredwg.py` (extract from the zip, verify against the manifest;
   the same script re-extracts later). Do not copy the extracted scratch folder beside the zip (it lacks `README.txt`,
   `dwgfilter` and the `share/` contents) nor the brief's `...fedf5601...\scratchpad\libredwg\` (no DLLs). Write
   `app/vendor/libredwg.manifest.json` (path, bytes, sha1 of every file; the zip's sha1) and
   `app/vendor/LIBREDWG-LICENCE.txt` (GPL-3.0-or-later as `README.txt` states, the release, where the licence text is;
   the full text is the owner's to fetch, listed in your report). If the zip is gone, stop and report. Check:
   `dwg2dxf.exe -y -o <WT_TMP>/l1.dxf "<project>/I1201 - LEVEL 1 GENERAL ARRANGEMENT.dwg"` gives sha1 `9167d084...`.
2. **Builder environment.** `services/builder/{pyproject.toml, requirements.lock.txt}` (U-10.1's pins), `python -m venv
   services/builder/.venv` (3.14.3), install the lock, `pip check`, `pip freeze` equal to the lock (PEP 503 names).
   `tools/run-builder-py.mjs` (the builder Python, `-B -P`, `cwd = app/`, `PYTHONPATH=services/builder`,
   `PYTHONIOENCODING=utf-8`, `PYTHONUTF8=1`, `PYTHONDONTWRITEBYTECODE=1`, `OPENBLAS_NUM_THREADS=1`, `OMP_NUM_THREADS=1`,
   `MPLBACKEND=Agg`, `PYTEST_ADDOPTS` with the cache under `WT_TMP` as `tools/lib.mjs pyEnv` does; never `-I`, `-E`,
   `-s`). `tools/check-pins.mjs` checks the builder lock (importing each pinned module in the set interpreter and
   resolving its `__file__` and version) and the LibreDWG manifest too.
3. **Builder package skeleton** `services/builder/walkthrough_builder/`:
   * `__init__.py` (`BUILDER_VERSION = '1'`, `READER_VERSION = '1'`);
   * `vendor/` with the byte-identical copies of U-10.2 and `vendor/VENDOR.json`; `vendor/load.py` (import by path,
     `sys.dont_write_bytecode = True`, `OPENINGS_DATA` set to a given folder before `openings` loads);
   * **complete** small shared modules, with tests: `roles.py` (the 17 roles, U-8.2's two derived tables, the
     builder-role `ROLES` tuple with `screen` and `room-outline`), `names.py` (normalise a layer name, `family()` of a
     block name, `element_id()`), `keys.py` (`sig(item)`, `rsig(item, element_insert)`), `jsonfile.py` (atomic JSON
     write that retries `os.replace` on `PermissionError` with back-off for at least 5 s, strict read; tested with a
     second process holding the target open, U-3.2), `oslock.py` (an OS file lock: `msvcrt.locking`, wait with a
     callback, released on process death). **After the scaffold U1 owns `jsonfile.py` and `oslock.py`** (a defect found
     by another builder goes in its `U<n>.md`);
   * `contracts.py` (below); every other module of U1 - U4 as a stub whose functions raise `NotImplementedError`;
   * `tests/conftest.py`: the `heavy` marker (in-process real drawings; its fixture takes the run lock), the `worker`
     marker (tests that spawn `job.py`; never takes the lock; long timeout, a queue wait reported as such), the `ref`
     fixture (reads `WT_REF`, default `%TEMP%\wt-u0\ref`, read-only; skips with a message when missing), the private
     lock fixture (`WALKTHROUGH_RUN_LOCK` under `WT_TMP`) for lock tests, `tests/test_vendor.py`.

   `contracts.py`, the calls between the builder's parts (TypedDicts, documented; U1 calls U2, U3 and U4 only through
   these):
   ```python
   class ReadResult(TypedDict):        # U2 -> U1
       items: str; drawing: str; plan: str          # paths of items.pkl, drawing.json, plan.json.gz (in out_dir)
       units: dict                                  # DrawingRead.units (its `used` names the cache folder, U-4.2)
       seconds: float
   # out_dir is a temporary folder (U1 renames it to read-<rv>-<used units> afterwards, U-4.2)
   def read_source(dxf_path: Path, units: str | None, out_dir: Path, *, source: dict, log: Callable[[str], None]) -> ReadResult
   def suggest(drawings: list[dict], office: dict | None) -> dict                                    # U2: LayerSuggestions
   def propose_settings(spec: dict, drawings: list[dict], suggestions: dict, conversions: list[dict],
                        latest_version: dict | None) -> dict   # U2: BuildSettings; latest_version = { model, msName } of a
                                                               # project with no project-data.json (U-3.3), else None
   class ConvertResult(TypedDict):     # U1 internal
       dxf: str; log: str; seconds: float; peak_mb: float | None; exit_code: int | None; memory_hit: bool
   def build(ctx: BuildContext, log: Callable[[str], None], progress: Callable[[str, float], None]) -> BuildResult  # U3
   def write_outputs(result: BuildResult, ctx: BuildContext, log: Callable[[str], None]) -> dict[str, Path]          # U4
   # BuildContext, SourceContext, BuildReport, FloorUploadReport, AlignReport, SingleLine, OutlineSuggestion,
   # FixesReport, DetectorRecordOut, ReplayFacts, ReplayFloor, ReplayInput, BuildResult: DESIGN U-10.8, verbatim
   ```
   U0 also writes the fixtures `fixtures/upload/build-result.bank.json` and `replay-input.bank.json` with exactly that
   key structure (from the v2 model, `bank_stages.json`, `bank_summary.json` and the detector outputs), and a test that
   they type-check against the TypedDicts (`typeguard`-free: a small recursive key and type walker in the test).
4. **Reference tool** `tools/upload/make-reference.py --out <dir> [--only bank|house|suite|tower]` (the builder Python,
   `-B`): copies into `<dir>/proj/` exactly the prototype files the chain needs (as
   `docs/upload/reference/bank_chain.ps1` did), converts the DWGs with the vendored LibreDWG, runs `prims.py` (with
   `OPENINGS_DATA=<dir>/proj/detector`), the detector with the mappings that made `detector/output/`
   (`mappings_with_areas/{bank1,bank2,sukhumvit,presidential}.json`, `mappings/{l29,l30}.json`), the bank's
   `build_model.py` and `generate_maxscript.py`, all inside the copy; writes `<dir>/manifest.json` (sha1 of every
   output). Done-check: the bank's model, stages, CSV, top view and `.ms` equal v2's (U-0's sha1s) under the builder
   Python; the six detector outputs equal `detector/output/<name>_openings.json`; the prototype folders' listing is
   unchanged. The scaffold runs it once into `%TEMP%\wt-u0\ref` (= `WT_REF` for every builder).
5. **API (frozen part).** `models_upload.py` (every type of `upload-contracts.ts` sections 1 and 5 as pydantic models with
   `models.py`'s `ApiModel` config; the raw-file records of section 4 and JobRecord as models not used in routes),
   `routes/uploads.py`, `routes/builds.py`, `routes/offices.py`, `createProject` in `routes/projects.py`, each route with
   its operationId, path, parameters (U-13.1's patterns), body, `response_model` or raw `response_class`, `responses`
   (`ErrorResponse` for every error status), `status_code` (201 / 202 / 204) and explicit `summary` / `description` /
   `response_description`; `getBuild`'s `withSettings` query parameter; bodies `raise ApiError(501, 'not_implemented',
   ...)`. `main.py`: the routers, CORS methods, the body guard (complete: it is small; U-13.5: 8 MiB for the settings
   PUT, 2 MiB for the rest), `deps.get_jobs` (returns `app.state.jobs`, a stub runner). `settings.py`: U-13.5's settings.
   `walkthrough_api/check_file.py` (CLI: `model|stages|presentation|drawing|plan|overlay|conversion|suggestions|settings|
   job|spec|launch|diff|pieces|openings <path> [--model <path>]`, exit 1 with the issues; `settings` runs
   `BuildSettings` and then `settings_issues()`, which U0 stubs to return `[]` in `walkthrough_api/settings_check.py`
   and U5 completes), so U1, U2 and U4 run the API's record checks on their own outputs before integration. Update the
   pinned counts (`test_openapi.py`, `test_routes.py`, `test_error_responses_are_typed`). `npm run gen:api`;
   `tools/check-openapi-additive.mjs` (U-15.2: by exported symbol, imports ignored) passes.
6. **Web (frozen part).** Copy `docs/upload/upload-contracts.ts` to `apps/web/src/upload/contracts.ts`; a test that the two
   are identical (`apps/web/test/upload-contracts-copy.test.ts`), a type test that the fixtures of step 8 satisfy the
   types (`apps/web/test/upload-fixtures.test-d.ts`, `satisfies`), and a type test that the generated `BuildSettings`,
   `BuildDetail`, `UploadSession`, `SourceFile` and the `contracts.ts` ones are mutually assignable
   (`apps/web/test/upload-generated-types.test-d.ts`). The three routes of U-14.1 in `router.tsx` with pages that say
   "not built yet" (U6 replaces them). **`apps/web/src/plan/index.ts`** with the final exported signatures of the U7
   module (the `PlanCanvasProps`, `DecodedPlan`, `PickMode` and function signatures of section U6 below; `PlanCanvas`
   renders a placeholder `<div>` with the plan's size; `decodePlan` decodes for real, as it is small; `proposeAreas` and
   `nearLayers` return empty results), so U6 imports from `@/plan` from day one and U7 replaces bodies, never
   signatures. `apps/web/test/plan/harness.html` + `harness.ts` stub (U7 fills it).
7. **Config and tools.** `tests/e2e/playwright.config.ts`: the API server command `node tools/run-api.mjs --port <api>
   --data "<WT_TMP>/data" --seed-fresh` (its `timeout` raised to 180 s for the seed), the builder settings and
   `WALKTHROUGH_CACHE_DIR=<WT_TMP>/cache` in its env, `WT_UPLOAD_OFFLINE_DIR` passed through, a global teardown that
   cancels every open run through the API (U-3.4); `tools/run-api.mjs --seed-fresh` (runs the seed into `--data`, then
   serves). Root `package.json` scripts:
   `test:builder`, `make:reference`, `vendor:libredwg`. `.gitignore` (U-4.1, U-15.1). `tools/upload/make-test-dxf.py
   small|hostile <out>` (ezdxf, deterministic: the small one is two rooms with fills, paired faces, a door arc and leaf, a
   window, a railing, a stair, two furniture blocks, a room name and grid labels; the hostile one the same with the
   names of ACCEPTANCE A-7).
8. **Fixtures** `fixtures/upload/` (ACCEPTANCE 2.5), each in `fixtures/README.md` with source and sha1. The settings for
   bank, house, suite and tower are made from `bank_project.json`, the detector mappings (`detector/mappings_with_areas/`,
   `detector/mappings/{l29,l30}.json`), the prototypes' layer lists (`cad_test/src/build3d.py cat_of`,
   `presidential_test/src/build_model.py`, the two `furniture.json`) and the levels and heights of ACCEPTANCE A-5, with
   the prototypes' floor keys (`L1`/`L2`, `ground`/`upper`, `suite`, `L29`/`L30`: the detector's ids carry them); each
   validates with `models_upload.BuildSettings`. `tools/upload/check-derived-mapping.py` runs the vendored detector with
   each fixture's **derived** mapping on the reference caches and compares the records with
   `detector/output/<name>_openings.json` (`floor` removed on both sides): the check is that the derived mapping
   **reproduces the output**, not that it lists the same layers (the bank's does not, and reproduces). U0 lists any
   difference in `U0.md`; U3 makes them exact.
9. **Docs.** `app/CLAUDE.md`: the builder pins, LibreDWG and its manifest, the ports of section 1, the owners below, the
   new commands; `app/README.md`: uploading a drawing; `docs/contract-issues/U0.md` ... `U7.md`, `UI.md` (U0 writes its
   own; the rest empty).

**Done when:** `npm run check:pins`; `npm run typecheck`; `npm run test:unit` (595 + the scaffold's); `npm run test:api`
(295 with the updated counts + the scaffold's); `npm run test:builder` (vendor, roles, names, keys, oslock, jsonfile);
`npm run gen:api` twice with no diff the second time; `node tools/check-openapi-additive.mjs`; `npm run make:reference --
--out %TEMP%\wt-u0\ref` (the bank equals v2; the six drawings' caches made and their detector outputs equal
`detector/output/`); `tools/upload/check-derived-mapping.py` (results in `U0.md`);
`npm run seed` (5 stamps); `npx playwright test -c tests/e2e/playwright.config.ts --list`; `npm run dev` answers (stop
it); no prototype file changed (listing before and after).

---

## U1. Intake and jobs (ports 5731 / 8731 / 4731 / 9731; `%TEMP%\wt-u1`)

**Owns:** `services/builder/walkthrough_builder/{job.py, step.py, isolate.py, convert.py, losscheck.py, cache.py,
runio.py}`, and after the scaffold `jsonfile.py` and `oslock.py`; `services/builder/tests/test_u1_*.py`.
**Reads:** U-3, U-4.2, U-6; `docs/upload/reference/{run_isolated.py, nothing_lost_stream.py, expand_probe.py,
missing_plot.py}`; `cad_test/src/dwg2dxf_convert_log.txt`; the readers' measured numbers in U-0.
**Delivers:**
* `job.py`: `python -B -P -m walkthrough_builder.job --run <run dir>`: reads `spec.json`, takes the machine lock (status
  `queued` while waiting), runs the steps of U-3.1 for its kind (a prepare with `spec.only` reads only those sources and
  skips `suggest`), writes `job.json` atomically after every status or step change and progress at most twice a second
  (with `pid`, `procStart` as U-3.4 defines it), honours `cancel` (U-3.4: `cancelled` is its last write), stops itself
  when its `spec.json` or run folder disappears or past `wallClockSeconds`, writes `outputs` with sizes and sha1s,
  `log.txt` with every child's stdout and stderr. At the start of each run, holding the lock, it evicts the cache above
  `WALKTHROUGH_CACHE_MAX_GB` (U-4.2). Prepare: per source convert (DWG), check (DWG), read (child; into a temporary
  folder renamed to `read-<rv>-<used>` with the `auto` pointer, U-4.2), then `suggest` and `propose_settings` (U2's
  functions, in a child) -> `out/suggestions.json`, `out/proposed-settings.json`. Build: `ensure` (re-read sources
  whose cache entry for their units is missing), builds the `BuildContext` (U-10.8), then one child running U3's
  `build` and U4's `write_outputs`, then `validate` (every output file passes `check_file` of its kind; the model has
  floors and parts).
* `step.py`: the child entry `python -B -P -m walkthrough_builder.step <read|suggest|build> <args.json>`, calling the
  `contracts.py` functions, exit code 75 on `MemoryError`; a test registry to run fakes.
* `isolate.py`: run one command in a Job Object (`ProcessMemoryLimit`, `KILL_ON_JOB_CLOSE`, `DIE_ON_UNHANDLED_EXCEPTION`,
  `ActiveProcessLimit` for leaf tools, wall-clock timeout then `TerminateJobObject`; a completion port for
  `JOB_OBJECT_MSG_PROCESS_MEMORY_LIMIT`; peak memory and CPU time reported; the `*_memory` classification of U-3.5;
  `CREATE_NO_WINDOW`; stdin DEVNULL; no shell); an output-size watchdog for the DXF.
* `convert.py` (U-6.2), `losscheck.py` (U-6.3: streaming dwgread scanner, raw DXF scanner, compare, message classes,
  lost-block inserts composed to sheet m, verdict from the comparison only, notes), `cache.py` (U-4.2's layout, `.done`
  rule, rename and pointer, eviction), `runio.py` (the JobRecord writer and reader; `proc_start(pid)` (the FILETIME
  decimal string) and `alive(record)`; U5 implements the same rule in the API, and a U1 test compares both on a live
  child through `walkthrough_api`'s function run with the API Python).
**Tests alone:** ACCEPTANCE 2.1 U1, with fake U2 / U3 / U4 functions through the step registry (`worker` marker); heavy
tests on the six DWGs (each verdict, I1201's 148 hatch messages, the suite's lost blocks and their inserts).
**Must not touch:** U2 - U4's modules, the vendored files, the API, the web app.

## U2. Reader and suggestions (ports 5732 / 8732 / 4732 / 9732; `%TEMP%\wt-u2`)

**Owns:** `services/builder/walkthrough_builder/{read.py, drawing.py, plangeom.py, units.py, levels.py, grid.py,
areas.py, suggest.py, propose.py}`, `services/builder/tests/test_u2_*.py`.
**Reads:** U-7, U-8, U-9.1 - 9.2, U-3.3; `detector/tools/prims.py` (the walk to reproduce), `docs/upload/reference/
{read_drawing.py, areas_propose.py, house_align.py}`, `cad_test/src/{levels_grid.py, regions2.py, regions3.py}`,
`detector/mappings*/`, `bank_test/src/bank_project.json`.
**Delivers:** `read_source` (one ezdxf pass: the items cache with `k` keys, DrawingRead, PlanGeometry with an anchor per
INSERT at every depth and `sig` / `rsig` / `eid` per entry (U-7.5, through `keys.py`); unit-aware flattening;
`MemoryError` and `RecursionError` re-raised from the per-entity handlers; the quick unit decision before the walk and
the full vote in it, re-walking on disagreement, U-7.4); `suggest` (U-8.3, with evidence: the `A-GLAZ` and `*-IDEN`
rules); `propose_settings` (U-3.3, including a new version of a project with no `project-data.json`: floor keys, names
and naming from its latest version); level tags (`LEVEL_RE` verbatim), grid labels (`GRID_RE` verbatim) with their
lines, area proposals.
**Tests alone:** ACCEPTANCE 2.1 U2 against `make:reference`'s caches (heavy); the fixtures `fixtures/upload/drawing/*`
and `plan/*` are re-made by your code and any difference with the scaffold's provisional ones is listed in `U2.md`.
**Must not touch:** `roles.py`, `names.py`, `keys.py` (scaffold's; a defect goes in `U2.md`), U1 / U3 / U4's modules.

## U3. The model builder (ports 5733 / 8733 / 4733 / 9733; `%TEMP%\wt-u3`)

**Owns:** `services/builder/walkthrough_builder/build/**`, `services/builder/tests/test_u3_*.py`,
`fixtures/upload/settings/**` (after the scaffold).
**Reads:** U-9.3 - 9.6, U-10; `bank_test/src/{build_model.py, plan_items.py, bank_project.json, README.md}`,
`bank_summary.json`; `cad_test/src/{merge_cad.py, openings3d.py, find_openings.py, build_furniture.py, README.md}`;
`presidential_test/src/{build_model.py, geom.py, read_dxf.py, furniture.json, floor_spec.json}`;
`furniture/{furniture_kit.py, README.md}`; `detector/{openings.py, geomkit.py, README.md}`;
`furniture_test/bank_furnished/{analysis.md, scripts/block_variants.py}`; `cad_test/src/heights.json`.
**Delivers:** `build(ctx, log, progress) -> BuildResult` (U-10.8, the TypedDicts exactly): the port of the bank builder
in the steps of U-10.3 (golden after each); the settings' numbers coerced (U-10.4); areas tagging after scaling, items
with no points in no floor, and the whole-subtree reading for the INSERT readers (U-9.1); alignment with grid labels
given to floors by their lines (U-9.4); the door-head order (U-10.4); the detector wrapper (U-10.7: stdout and stderr
captured, `slow` from `fl.T`, `frameRowsSkipped`); the options of U-10.5 (the musts, then the shoulds: `outlineWalls`,
the furniture reader rules, `pieceLayer`); the fixes (U-10.6) with the matcher (subtree refs, element id + `rsig`,
ambiguity); the report (`summary` = the bank summary's structure, plus the upload keys); `ReplayInput`; the placements
(U-11.7) from the INSERT items, with `insertMirrored` and `drawnVariant` (the port of `block_variants.py`, should);
the lost inserts placed in floors from the conversion reports; `floors_frame`. The acceptance settings made exact
(each drawing's derived detector mapping reproduces its `detector/output/` file, `floor` aside).
**Tests alone:** ACCEPTANCE 2.1 U3, on `make:reference`'s caches (no `k` keys there: fixes tests use the small synthetic
DXF read by a minimal local reader in the test, or wait for U2's at integration), the reference detector outputs, and
the settings fixtures. Golden: `sha1(model.json) == c3a9408304a240b83c36f5c5c53db56b50a72c64`.
**Must not touch:** the vendored files, `roles.py` / `names.py` / `keys.py`, U1 / U2 / U4's modules, the API.

## U4. Outputs (ports 5734 / 8734 / 4734 / 9734; `%TEMP%\wt-u4`)

**Owns:** `services/builder/walkthrough_builder/out/**`, `services/builder/tests/test_u4_*.py`,
`fixtures/upload/max-texts/**` (after the scaffold), `tools/upload/gap-report.py`.
**Reads:** U-11, U-12.2, U-12.4; `bank_test/src/{build_model.py (replay, top view: lines 1280-1487), generate_maxscript.py,
make_html.py}`, `hotel_test/src/generate_maxscript.py`, `presidential_test/src/generate_maxscript.py`,
`furniture/furniture_max.py`, `furniture/fixtures/maxscript_mock.py`, `app/services/api/walkthrough_api/seed/
{presentation.py, stages.py}` (what the viewer expects), D-7, D-8.
**Delivers:** `write_outputs(result, ctx, log)` (reading `BuildContext` for everything that is not in the result, never
a cache path of its own): `model.json` bytes (U-10.9), `stages.json` (U-11.3), `presentation.json` (U-11.2),
`topview.png` (U-11.4), the Max script (U-11.5: profiles `bank-27oct`, `hotel-2nov`, `upload` with their verbatim
header, tooltip, placed-at and datum lines; follow / keep, stair and door sentences computed from the model; picture
lines from `pictureFrame` for the hotel profile; the "two holes touch" refusal), `openings.json`, `pieces.json`,
`inputs.json`, `report.json` (as U3 returns it), `overlay.json` with the flags (U-12.2, `detector-skipped` included),
`diff.json` (U-12.4, in sheet coordinates); `gap-report.py <prototype version dir> <uploaded version dir>` -> a markdown
section (ACCEPTANCE A-5's metrics and its gap classes, A-6's failing probes).
**Tests alone:** ACCEPTANCE 2.1 U4 (fixtures: `build-result.bank.json`, `replay-input.bank.json`, `fixtures/models/*`);
every output through the API's checker (`node tools/run-py.mjs -m walkthrough_api.check_file <kind>`). The camera rule
(U-11.2) is checked in Python with the viewer's own camera maths (field of view, the fitSlabs target and pan, the panel
width: read from `packages/viewer/src/core/`), at 1400 x 880; the same rule in Edge is part of `upload-walk.spec.ts`
(U7).
**Must not touch:** U1 - U3's modules, the vendored files, the API, the viewer.

## U5. API (ports 5735 / 8735 / 4735 / 9735; `%TEMP%\wt-u5`)

**Owns:** `services/api/walkthrough_api/**` except `models.py`, `models_upload.py` and the route decorators (bodies
only), and `services/api/tests/**`; the contents of `data/` (by the seed only).
**Reads:** U-3.2 - 3.4, U-4, U-5, U-8.4, U-11.1, U-11.6, U-13, U-15.3; `upload-contracts.ts`; D-9, D-10; I.md.
**Delivers:** every new route's body (U-13.1); the store's upload, source, build, settings, office and project-settings
methods and `VersionDraft.project_data` (U-13.4); `LocalJobRunner` (spawn, `launch.json` with the FILETIME
`procStart`, cancel with the 15 s kill on a timer thread that waits for the pid to exit before writing `cancelled`,
`alive`, start-up marking including runs with no `job.json`) and `get_jobs`; the per-build lock and `api.json`; the
run-done validation of the worker's outputs (U-3.2) through `check_file`'s functions; the settings proposal adoption
(U-3.3: once, under the lock; 409 `not_prepared` before it; naming, floor keys and offset from the latest version for a
project with no settings); `settings_issues()` (in `settings_check.py`); a units change (rescale, one-source prepare,
U-7.4); `layersReviewed` and 409 `layers_not_reviewed`; `getBuild`'s `withSettings`; `saveBuild` (U-11.1: under the
lock, idempotent; the draft, `create_version`, project settings, office memory, the build marked saved);
`create_version`'s `.ms` stamp check after its name checks, and `test_store.py`'s draft given the real stamp; new
project ids at most 40 characters and the path-length check (U-4.1); the seed protections (U-15.3); the CSV guard in
`furniture_csv.py` (U-11.6); clean-up at start-up (U-4.1).
**Tests alone:** ACCEPTANCE 2.2 with a FakeJobRunner over `fixtures/upload/runs/`; the `builder` integration tests are
written now and skip until U1 - U4 land (they fail under `WT_INTEGRATION=1`). `uvicorn` on 8735 for manual checks.
**Must not touch:** the frozen files, the builder package, the web app.

## U6. Web screens (ports 5736 / 8736 / 4736 / 9736; `%TEMP%\wt-u6`)

**Owns:** `apps/web/src/**` except `src/plan/**`, `src/api/generated/**` and `src/upload/contracts.ts`; `apps/web/test/**`
except `test/plan/**` and the scaffold's three contract tests; `tests/e2e/upload.spec.ts` (with
`test.setTimeout(10 * 60_000)`), and the 8 count lines of `tests/e2e/web.spec.ts` / `web-leak.spec.ts` plus
`web.spec.ts` line 65 (the id list with `e2e-*` filtered out; U-15.3); the new `components/ui/` files (U-14.2).
**Reads:** U-2, U-5.3, U-8.1, U-12, U-14; the generated client; `upload-contracts.ts`; D-15; the U7 module's signatures
below.
**Delivers:** the routes and screens of U-2 / U-14 (NewProjectPage, UploadPage, BuildPage and its six steps), the role
labels and help, the close-to-walls chip, the Advanced pad / match, the level-tag list, the office select, the
pre-build checklist, "Stopping...", Save disabled in flight; the project card and the no-version page leading to drafts
(`ProjectCard.tsx`, `ProjectRedirect.tsx`, U-14.1); the upload client, the build poller (`withSettings: false`) and the
settings saver (413 message, `layersReviewed`), the draft preview, the app bar's New version and Drafts, the project
list's New project, the mock API's new routes. `ItemRef`s are filled from the plan entry's `sig` / `rsig` / `eid`.
**Uses from U7** (`apps/web/src/plan/index.ts`, written by the scaffold with these final signatures and placeholder
bodies, U-15.1; import from `@/plan` from day one):
```ts
export interface DecodedPlan {                        // fields U6 may read; U7 may add private ones
  source: Sha1; units: Units; origin: Vec2; quantum: number;
  layers: string[];                                   // index -> layer name
  extents: Bbox;                                      // sheet m
  count: number;                                      // entries
  keyAt(i: number): string; layerAt(i: number): number; typeAt(i: number): number;
  refOf(key: string): { sig: string; rsig: string; elementId: string | null; layer: string } | null;   // for ItemRef
}
export type PickMode = 'item' | 'block' | 'layer-in-box';
export interface PlanCanvasProps {
  plan: DecodedPlan;                                  // decodePlan(PlanGeometry)
  roleOf: (layerIndex: number) => LayerRole;
  highlightLayer?: number | null;
  area?: FloorArea | null;                            // lit; the rest dimmed
  overlay?: OverlayFloor | null;
  flags?: Flag[];
  selected: ReadonlySet<string>;                      // item keys
  setAside: ReadonlySet<string>;
  diff?: DiffBody | null;
  tool: 'pan' | 'select' | 'pick-point' | 'draw-box';
  pick?: PickMode;                                    // default 'item' (U-12.1)
  focus?: Bbox | null;                                // zoom to it when it changes
  onSelect?(keys: string[], mode: 'replace' | 'add' | 'toggle'): void;
  onPick?(p: Vec2): void;
  onBox?(bbox: Bbox): void;
  onOpening?(id: string): void;
  onFlag?(id: string): void;
  onHover?(info: { layer: string; type: number; key: string } | null): void;
}
export function PlanCanvas(props: PlanCanvasProps): JSX.Element;
export function decodePlan(json: PlanGeometry): DecodedPlan;
export function proposeAreas(plan: DecodedPlan, layers: ReadonlySet<number>): Bbox[];
/** For each layer index not in `wallLayers`: how many of its items lie within `dist` m of a wall-layer segment. */
export function nearLayers(plan: DecodedPlan, wallLayers: ReadonlySet<number>, dist: number): Map<number, number>;
```
(`Sha1`, `Units`, `Bbox`, `LayerRole`, `FloorArea`, `OverlayFloor`, `Flag`, `DiffBody`, `PlanGeometry` from
`@/upload/contracts`; `Vec2` from the viewer.)
**Tests alone:** ACCEPTANCE 2.3 U6 (vitest, mock API); `upload.spec.ts` against the mock API (`WT_SERVE=web`), the
real-API run at integration.
**Must not touch:** `packages/**`, `services/**`, generated files, configs, `package.json` files, `src/plan/**`.

## U7. Plan canvas and the viewer's CSV guard (ports 5737 / 8737 / 4737 / 9737; `%TEMP%\wt-u7`)

**Owns:** `apps/web/src/plan/**` (the bodies behind the scaffold's `index.ts` signatures, which do not change),
`apps/web/test/plan/**` (the harness page included), `tests/e2e/plan-canvas.spec.ts`, `tests/e2e/upload-walk.spec.ts`
(ACCEPTANCE A-6: generic, written against `dist/offline/bank-sampeng-v2.html`, pointed at other files by
`WT_UPLOAD_OFFLINE_DIR`; moved here from U6, whose load was the largest); in the viewer, only the CSV function of
`packages/viewer/src/furniture/logic.ts` (the guard of U-11.6) and `packages/viewer/test/unit/furniture/csv-guard.test.ts`.
**Reads:** U-7.5, U-12.1 - 12.2, U-14.3; `upload-contracts.ts`; `fixtures/upload/{plan,overlay}/*`; D-17.4;
`tests/e2e/lib/walks.ts` and the foundation's walk specs.
**Delivers:** `PlanCanvas`, `decodePlan`, `proposeAreas`, `nearLayers` (the signatures above), paths in local quanta
from `origin` and the overlay converted to that frame, line widths in screen pixels, the pick modes (`item`, `block`
climbing levels by key prefix, `layer-in-box`), the colours per role, the redraw budget (U-12.1), the harness page; the
walk spec of A-6; the viewer CSV guard with the four goldens unchanged.
**Tests alone:** ACCEPTANCE 2.3 U7 and 2.4 U7.
**Must not touch:** everything else in `apps/web/src`, the rest of `packages/viewer`, `services/**`.

---

## UI. Integration (after U1 - U7; ports 5711 / 8711 / 4711 and the defaults 5710 / 8710 / 4710; `%TEMP%\wt-ui`)

1. Read every `docs/contract-issues/U*.md`; settle each with the smallest change (only here may a frozen file change, with
   a note in `UI.md`).
2. `npm run check:pins`, `npm run typecheck`, `npm run test:unit`, `npm run test:builder` (with `WT_REF` in place),
   `npm run seed`, `npm run test:api` and `WT_INTEGRATION=1 npm run test:api`.
3. `npm run gen:api` (no change), `node tools/check-openapi-additive.mjs`, `npm run build`.
4. The acceptance runs, each into a temp store under `%TEMP%\wt-ui`: A-1 (both forms), A-3, A-4, A-5 (house, suite,
   tower, and the suite with every outline suggestion accepted), A-8, A-9, A-10 (times and memory from `job.json`).
   Write `docs/upload/GAPS.md` from `tools/upload/gap-report.py` with every gap classified (ACCEPTANCE A-5, and A-6's
   failing probes on the house, suite and tower); if a report file cannot be written, return it in a fenced block for
   the main session.
5. `npm run test:e2e` (every spec, the new ones included: `upload.spec.ts`, `plan-canvas.spec.ts`, and
   `upload-walk.spec.ts` with `WT_UPLOAD_OFFLINE_DIR` = the offline files `make-offline.mjs` made from step 4's store).
6. The prototypes' tests, unchanged, one at a time (the foundation's I.7 list); the listing of everything outside `app/`
   before and after; no `__pycache__`.
7. The staff path in Edge on `npm run dev` (5710 / 8710) with a store copy: the bank from its DWGs through every screen to
   the viewer and its downloads; screenshots of each step in `%TEMP%\wt-ui\path`. Put `app/data` back as it was.
8. Report: what passes (commands and counts), the acceptance table with numbers, the gaps, what does not pass and why, the
   contract issues and how they were settled. There is nothing to deploy; any later deploy is the owner's to run.

## UR. Independent review and fix (after UI; ports 5739 / 8739 / 4739 / 9739; `%TEMP%\wt-ur`)

The foundation needed one (four checkers, 37 findings, 32 fixed), so it is planned and counted here: independent
reviewers (fidelity against the prototypes; code; an attempt to break it with hostile and huge drawings; the staff path
seen by a non-programmer) report findings; each is verified, then fixed with a test or answered in
`docs/contract-issues/UR.md`; then the integration checks of UI steps 2 - 6 run again from a clean start. Nothing is
deployed.

---

## 9. Hours

### 9.1 This milestone (hands-on developer hours, as the plan counts them; re-estimated after the reviews)

| Part | Likely | Range | What drives it |
|---|---|---|---|
| U0 scaffold | 18 h | 14 - 24 | runs alone on the critical path: LibreDWG from the zip, the venv, ~60 pydantic models, 24 route stubs with OpenAPI metadata, the body guard, `check_file` with 15 kinds, `gen:api` and the symbol-level additive check, `plan/index.ts`, three type tests, `make:reference` over six drawings, the derived-mapping check, two synthetic DXF generators, a dozen fixture sets (a PlanGeometry with nested keys and signatures that no reference script makes, the typed build result), docs |
| U1 intake and jobs | 18 h | 14 - 24 | Job Objects with a completion port, the converter, the loss check, the cache (rename, pointer, eviction), the orchestrator with its Windows details (sharing retries, FILETIME identity, self-stop, cancel) |
| U2 reader and suggestions | 12 h | 9 - 16 | the walk equal to `prims` on six drawings, keys and signatures, units, tags, grid lines, areas, suggestions, proposals |
| U3 model builder | 30 h | 22 - 44 | the step-by-step port against the golden, subtree reading, alignment, options, fixes and the matcher, the typed report, `drawnVariant` |
| U4 outputs | 14 h | 10 - 20 | replay, presentation, top view, the merged Max generator with its profiles, sidecars, flags, diff, the gap tool |
| U5 API | 24 h | 18 - 30 | 24 route bodies, the store, `LocalJobRunner` (ctypes identity, timer kill, `taskkill`), the per-build lock, validation, adoption, the units change, an idempotent save, seed protection, clean-up |
| U6 web screens | 36 h | 28 - 48 | six steps, the upload client, the poller and saver, the checklist and the drafts path, a mock of 24 operations, vitest, `upload.spec.ts` |
| U7 plan canvas, A-6 walk spec, viewer CSV guard | 12 h | 9 - 16 | the canvas in local frames with pick modes and a budget, `upload-walk.spec.ts` (moved from U6) |
| UI integration, acceptance runs, gap report | 20 h | 15 - 28 | four drawings end to end, GAPS.md, every suite of checks |
| UR independent review and fix | 20 h | 15 - 25 | as the foundation's (37 findings, 32 fixed) |
| **Total** | **~205 h** | **155 - 275 h** | |

**Elapsed time.** The foundation (plan estimate ~40 h) took about 27 h elapsed, 14 of them waits for the usage limit, with
no hands-on hours from the owner: elapsed = about 0.68 x the estimate, **waits included** (the earlier figure of 35 - 50 h
counted only the active share and was wrong). On the same ratio this milestone takes **about 140 h elapsed (105 - 185
h)**, roughly half of it usage-limit waits. Assumptions: the same agent set-up and usage limit as on 3 - 4 Nov; U1 - U7
run in parallel as the foundation's builders did; the owner's part is a look at the staff path, fetching the GPL-3.0
text for `app/vendor/`, and whether to look at ODA for the suite's lost blocks (the builder venv was approved on 4 Nov).

### 9.2 Against the plan (`walkthrough_app_plan.md` sections 4 and 5)

| Plan item | Plan's hours | In this milestone |
|---|---|---|
| Set-aside tool (Phase 1) | ~10 h (5 - 20) | all of it except the "walls by shape" option: ~7 h |
| Build settings screen and build replay (Phase 1) | ~25 h (15 - 40) | recording from the real steps, N-floor texts: ~5 h (the player was the foundation's) |
| Check-and-fix screen: layer mapping per office, heights, alignment, unknown items (Phase 1) | not itemised | its first version |
| Robust builder: openings, rooms, slabs, stairs (Phase 1) | not itemised | openings wired in, the general builder; not rooms, slabs, stairs |
| Versions per project (Phase 1) | not itemised | uploads make versions |
| Export for 3ds Max (Phase 3) | ~45 h | the generator from the model, ~6 h, comes forward (Phase 3's share drops by as much; not Phase 1 base) |
| DWG intake (decision F) | not itemised | all of it |

Phase 1 is +~385 h, of which the items it names come to ~135 h (view modes 35, replay 25, furniture boxes 20, set-aside
10, models / finishes / lights 25, box editing 20), leaving **~250 h** for its unitemised base (check-and-fix, the robust
builder, furniture import and library, materials and lighting, versions, saved views and presentation mode, the layered
PDF tier). This milestone spends about **187 h of that base** (205 h less ~12 h that belong to named items, set-aside
and replay, and less the ~6 h of the Max generator, which is Phase 3 work brought forward), which leaves **~63 h** for
rooms, slabs and stairs, furniture import and the library, the base of materials and lighting, saved views and
presentation mode and the layered PDF, which need roughly 110 - 200 h. **Expect Phase 1 to run about 50 - 140 h over its
+385 h (likely ~90 h)**; with this milestone's own range (155 - 275 h) the overrun spans about 0 - 210 h. The plan's
Phase 1 and core totals should be updated by the main session (plan, product document and viewers kept in sync), and
re-estimated after this milestone with its measured hours.
