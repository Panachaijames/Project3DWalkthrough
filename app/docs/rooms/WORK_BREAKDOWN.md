# Work breakdown: rooms and slabs, then stairs you can climb (10 Nov 2026; revised on 11 Nov 2026 after the review by three critics)

The steps run in this order:
1. one **scaffold** step (R0), alone;
2. seven **builders** (R1 – R7) in parallel;
3. a **smoke step** (RI-0) as soon as R1 and R2 report, while the other builders still run;
4. one **integration** step (RI);
5. an **independent review and fix** step (RR).

Builders do not talk to each other. Their interfaces are:
* the frozen contracts as R0 leaves them (DESIGN R-12.7);
* `walkthrough_builder/contracts.py` (DESIGN R-12.3, the calls between R1 and R2);
* the working tracer R0 leaves behind: the chain from a drawing to a model with a stairway, green on a two-floor test
  drawing;
* `DESIGN.md` (cited R-n);
* the fixtures of ACCEPTANCE 2.5, all derived from one reference building.

Each builder owns a disjoint set of files; it may read anything and write only what it owns.

## 0. Rules for every step

* **The upload milestone's rules still hold** (`../upload/WORK_BREAKDOWN.md` section 0):
  * write only inside `app/` and your own `%TEMP%\wt-<step>`;
  * never deploy, publish or release;
  * no installs (no new library is needed);
  * exact versions;
  * drawing text as text only;
  * the Bash tool collapses double backslashes, so code with backslashes goes into files;
  * `PYTHONIOENCODING=utf-8`;
  * one headless Edge at a time through `tools/edge-lock.mjs`;
  * prototype Python only with `-B`;
  * your own ports and temp folder;
  * frozen files are frozen: a defect goes in **your own** `docs/rooms/contract-issues/R<n>.md`.
* **Git**: the branch is `milestone-rooms`. No step commits, switches branches or pushes; the main session commits.
  `git show`, `git diff` and `git status` are fine.
* **The prototypes are read-only, and so is running them** (only in a scratch copy).
* **Never start a server on 5710 or 8710**: the owner may be using `npm run dev`. Use your own ports (section 1).
* **No reload.** `npm run dev` and `node tools/run-api.mjs` no longer reload the API when its code changes
  (`../upload/contract-issues/UI.md`, UI-5: on Windows the reload stopped the whole app; `run-api.mjs` refuses
  `--reload`). So:
  * after a change to API code (`services/api/**`), stop your server with Ctrl+C and start it again. A check made
    before the restart tested the old code;
  * builder code needs no restart: the worker is a new process for every build (`jobs/local.py:194`);
  * the web dev server still hot-reloads web code;
  * the e2e config starts its own servers for every run (`reuseExistingServer: false`), so no spec relies on a reload.
* **The store and the cache**: never use `app/data` or the default cache in a test. Set
  `WALKTHROUGH_DATA_DIR=<WT_TMP>\data` and `WALKTHROUGH_CACHE_DIR=<WT_TMP>\cache`. Browser specs run with
  `WT_DATA_DIR` and `WT_OFFLINE_DIR` on a freshly seeded temp store. Every project a spec makes is saved under an
  `e2e-` id (`tests/e2e/web.spec.ts:75` reads every card).
* **Nobody writes `dist/` while the builders run in parallel.** A builder that needs the viewer template builds it into
  its own temp folder (`--outDir`, as `packages/viewer/test/harness/core/make-e2e-offline.mjs:5-9`).
* **Shared and read-only**: the reference caches `WT_REF` (`%TEMP%\wt-u0\ref`, the six drawings of the upload milestone)
  and `%TEMP%\wt-r0\ref` (R0's: the new suite); R0's copy of the upload acceptance store `%TEMP%\wt-r0\acc-9nov`.
* **Heavy and worker tests**: heavy tests take the machine run lock (`%TEMP%\walkthrough-run.lock`); `worker` tests never
  do (U-3.5). The costliest runs (every door undone, two-process builds, `upload-walk` on 13 files) run only with
  `WT_ACCEPTANCE=1`.
* **The door finder is frozen** in this milestone (`services/builder/tests/test_vendor.py` pins the vendored copy). The
  fifth drawing was scored on 10 Nov, so its openings may be cited (the key's ids `SR-nn`); nothing is tuned on them,
  and its acceptance rows are shoulds, by position.
* **Your final report**: files written, what passes (commands and counts), what does not, and the contract issues you
  raised.

## 1. Ports and temp folders (the free range: nothing of 5710 – 5739 / 8710 – 8739 / 4710 – 4739 / 9710 – 9739, nothing of the prototypes' 93xx – 94xx)

| Step | Web dev / harness | API | Preview | CDP | `WT_TMP` |
|---|---|---|---|---|---|
| R0 scaffold | 5740 | 8740 | 4740 | 9740 | `%TEMP%\wt-r0` |
| R1 network, rooms, slabs, ceilings | 5741 | 8741 | 4741 | 9741 | `%TEMP%\wt-r1` |
| R2 stairs | 5742 | 8742 | 4742 | 9742 | `%TEMP%\wt-r2` |
| R3 outputs | 5743 | 8743 | 4743 | 9743 | `%TEMP%\wt-r3` |
| R4 viewer | 5744 | 8744 | 4744 | 9744 | `%TEMP%\wt-r4` |
| R5 API | 5745 | 8745 | 4745 | 9745 | `%TEMP%\wt-r5` |
| R6 staff app, plan canvas and their specs | 5746 | 8746 (mock) | 4746 | 9746 | `%TEMP%\wt-r6` |
| R7 viewer browser tests | 5747 | 8747 | 4747 | 9747 | `%TEMP%\wt-r7` |
| RI integration | 5748 (the owner's path), the e2e config's 5711 / 8711 | 8748 | 4748 | 9748 | `%TEMP%\wt-ri` |
| RR review and fix | 5749 | 8749 | 4749 | 9749 | `%TEMP%\wt-rr` |

---

## R0. Scaffold (runs first, alone; ports 5740 / 8740 / 4740 / 9740; temp `%TEMP%\wt-r0`)

Goal: a workspace where every later step writes code against frozen contracts, fixtures and a working tracer, and where
"nothing old moved" is pinned before anyone changes anything.

0. **The first hour: two cheap checks and the references.**
   * Add one optional field with a default to the real `models_upload.py` and run `npm run gen:api`: the schemas must not
     split into `-Input` and `-Output` (DESIGN R-12.5). If they do, stop and report.
   * Time `npm run test:unit` and `npm run test:api` (the budgets of RA-14 rest on estimates).
   * Record `docs/rooms/reference/versions.sha1` (the 49 files under `app/data/projects/*/versions/`) and
     `docs/rooms/reference/outside.txt` (DESIGN R-13).
   * Copy, from temp folders that can be cleared:
     * the upload acceptance store `%TEMP%\wt-ur\acc\data` → `%TEMP%\wt-r0\acc-9nov`;
     * the walk reports of 9 Nov `%TEMP%\wt-uf\e2e\upload-walk\*.json` → `docs/rooms/reference/upload-walk-9nov/`;
     * the upload milestone's acceptance scripts `%TEMP%\wt-uf\scripts` and `%TEMP%\wt-ur\scripts` →
       `tools/rooms/acceptance/`, with a `run.mjs` that runs them and writes one JSON result (RI fills the new steps).

     If a source is gone, say so in `R0.md`; RI then rebuilds it from the saved recipes.
1. **The walk-parity golden, before any viewer file changes** (DESIGN R-13).
   * `packages/viewer/test/tools/record-walk-parity.ts` drives only the frozen `ModesApi` and the probe. It refuses to
     run unless `git diff 66b4c06 -- packages/viewer/src` is empty, and writes that tree's hash into the golden.
   * `packages/viewer/test/fixtures/walk-parity.json`: the six model files that `fixtures/models` holds today
     (`bank-v1`, `bank-v2`, `hotel`, `house`, `mini`, `suite`) with their sha1; the wall, door
     and glass recipes and floor edges with `clearance`, `open` and `findFree`; key-driven walks through `tick(now)`
     with a made-up clock; PgUp, a double-click landing, a Ghost → Walk landing, one eye-height change; the walk north
     into the hotel's F1 flight (today it stops 1.3 m in, at `F1 step:own`).
   * `packages/viewer/test/unit/modes/walk-parity.test.ts` pins the golden's own sha1 and passes on the unchanged
     viewer.
2. **The old-rule guard, from the unchanged code.**
   * `fixtures/upload/settings/recipes/{house,suite,tower,suite-revit}.json`: the `project-data.json` of the saved
     versions whose models are `1c07bfeef580`, `205e9c2c46e8`, `91414f408cb2`, `1d90d91ef949`.
   * `fixtures/rooms/old-rule.sha1.json`: the sha1 of every output file of the five old-rule builds (model, stages,
     overlay, flags, diff, top view, Max script with a fixed date).
   * `services/builder/tests/test_r_old_rule.py` (heavy) compares them all, and the bank built from settings with the
     three options written out at their old values. With `WT_INTEGRATION=1` a missing reference fails. It is green
     before step 3.
3. **The extraction, with no change in behaviour**: `prepare_floors(ctx)` out of `build()` and a per-floor
   `floor_walls(F, X)` out of the loop of `bank.py:874-958` (DESIGN R-12.3). Step 2's test and `test_u3_bank.py` stay
   green.
4. **Contracts** (DESIGN R-12.7), all in one step:
   * the v2 schema (both copies) **and its cross rules in the three checkers** (the schema, `model/parse.ts`,
     `builtmodel.py`), with one broken-model case per rule (`tools/make-broken-fixtures.mjs`): one owner for "the three
     checkers change together";
   * `docs/contracts.ts` and the viewer copy;
   * `docs/upload/upload-contracts.ts` and the web copy, **every new member optional**;
   * `models_upload.py`, with the new fields optional and their defaults: the options at their old values, the fix
     lists `[]`, `ceilingHeight` None, `floorPast` false; the constants `OLD_RULES` and `NEW_RULES`;
   * `store/base.py` (`model_format`);
   * the builder's `contracts.py` (R-12.3), the new report keys in `total=False` subclasses, and `test_contracts.py`
     extended to read the block of DESIGN R-12.3;
   * **a placeholder in every file that lists every kind, toggle or flag**, so the workspace type-checks:
     `apps/web/src/build/FlagList.tsx:10` (a text per new flag kind), `apps/web/src/plan/colours.ts:57`,
     `packages/viewer/src/model/styles.ts:9`, `model/presentation.ts:52, 64`, `core/build.ts:127` (`surfaces: []`),
     `apps/web/test/fake-viewer.ts:263`, `packages/viewer/test/harness/context.ts:192, 359`, and the objects that
     implement `ModesState` (`foot`), `ModesProbe` (`foot`, `ground`) and `ReadoutsApi` (`groundAt`);
   * **the tests with exact sets**, updated: `packages/viewer/test/unit/core/visibility.test.ts:37, 41`,
     `test/unit/model/presentation.test.ts:103`, `test/harness/core/viewer.spec.ts:74, 200`,
     `apps/web/test/plan/colours.test.ts:12, 50`;
   * the tests that the two copies of each contract file are identical.
5. **API, frozen part.**
   * `npm run gen:api`.
   * `tools/check-openapi-additive.mjs`:
     * the default base becomes `66b4c06`;
     * a new rule: a component schema may gain a property that is not required; an interface may gain optional members;
     * a test of its two failing cases.
   * The pinned counts (`test_openapi.py`'s schemas).
   * `check_file overlay` accepts the new optional overlay fields.
6. **The plan canvas's signatures and the test aids** (DESIGN R-12.6): `apps/web/src/plan/index.ts` (the tools
   `'draw-line'` and `'rooms'`, the callbacks, `show`, the `window.__plan` hook) and `apps/web/src/build/testids.ts`.
   Placeholder behaviour only; R6 fills the bodies.
7. **The tracer** (DESIGN R-12.3): thin but working `build/network.py`, `rooms.py`, `slabs.py`, `xmarks.py`,
   `ceilings.py` (R1's) and `build/stairs_read.py`, `stairs_build.py` (R2's), wired into `build_floors` behind
   `slabs: 'network'`: the network is today's walls and spans, the stairs are one straight flight with a word. One
   end-to-end test builds a two-floor drawing with one straight stair (`make-stair-dxf.py straight`) through `build()`
   with the new options and gets a v2 model with one stairway. It is green before R0 reports. (The reference building
   needs the real rules; its model fixture is computed by its own script, not by the tracer.)
8. **Fixtures** (ACCEPTANCE 2.5):
   * the `*-rooms.json` settings: each upload fixture plus the three options. The new suite's comes from the A-12 run's
     saved recipe (`suite-revit` v1) with layer 0 set to wall, and no set-asides, since that recipe has none;
   * `tools/rooms/make-reference-building.py` and everything derived from it: the DXFs, the v2 model with its
     presentation, `tools/rooms/make-fixture-store.mjs`, a build result with every new report key and flag kind, the
     overlay, a FakeJobRunner run folder;
   * `fixtures/models/stairs-{straight,L,U}.model.json`;
   * `tools/rooms/make-stair-dxf.py straight|L|U|two-floor|no-direction|down-up-pair|split-level`: risers as nosing
     pairs, a word, an arrow with a dot, a break line that cuts a riser in two, hidden continuations with one riser
     missing, a deeper first step, two floors with a shared riser (R2 owns it after R0);
   * the provisional `house-rooms` overlay, marked provisional in `fixtures/README.md`;
   * the answer keys: `fixtures/rooms/keys/bank.json` (each room tag's own point, from the drawing), `probes.json`
     (the probes of RA-6 by floor, sheet point and side, from the reports of 9 Nov), and empty `house.json` and
     `suite.json` for R1 and RI.
9. **The new suite's reader cache**: read `presidential suite_layout.dwg` with the app's reader into
   `%TEMP%\wt-r0\ref\suite-revit\` (the cache layout of U-4.2). `test_u3_helpers.py`'s `CACHE_OF` (`:32`) learns the new
   suite and the reader's `items.pkl`.
10. **Shared test set-up**: session-wide fixtures in `services/builder/tests/conftest.py` (one new-rule build per
    drawing, shared by R1's and R2's tests and the golden); the `WT_ACCEPTANCE=1` flag; `kit.python_child` for the
    two-process builds.
11. **Docs**:
    * `app/CLAUDE.md`: the ports of section 1, the owners below, the no-reload rule, "nobody writes `dist/`";
    * `docs/rooms/contract-issues/R0.md` (yours) and empty `R1.md` … `R7.md`, `RI.md`, `RR.md`.

**Done when** all of these pass:
* `npm run check:pins`;
* `npm run typecheck`;
* `npm run test:unit` (851 + the scaffold's, the walk-parity golden passing on the unchanged viewer);
* `npm run test:api` (471 + the scaffold's, counts updated);
* `npm run test:builder` (722 + the scaffold's: the old-rule guard, the tracer, the old fixtures' bank key structure
  unchanged; none skipped);
* `npm run gen:api` twice, with no diff the second time;
* `node tools/check-openapi-additive.mjs`, against both bases;
* `npm run seed` (5 stamps);
* `npx playwright test -c tests/e2e/playwright.config.ts --list`;
* no file of `docs/rooms/reference/outside.txt` changed.

**Owns:**
* every file named above. Frozen after R0, for everyone: `services/builder/tests/conftest.py`, `kit.py`,
  `test_contracts.py`, `test_u3_helpers.py`, `test_r_old_rule.py` and its fixture, `package.json`,
  `tools/make-broken-fixtures.mjs`, `tools/rooms/make-reference-building.py` and what is derived from it,
  `apps/web/src/build/testids.ts`, the parity golden and its recorder;
* after R0: `fixtures/models/**` (the new ones), `fixtures/rooms/old-rule.sha1.json`, `docs/rooms/reference/**`.

**Hours:** 26 h (20 – 34).

---

## R1. Network, rooms, slabs, ceilings (ports 5741 / 8741 / 4741 / 9741; `%TEMP%\wt-r1`)

**Owns:**
* `services/builder/walkthrough_builder/build/{network.py, rooms.py, slabs.py, xmarks.py, ceilings.py}` (the tracer's
  bodies replaced);
* `build/__init__.py` (the three new fix lists passed through; `report['fixes']`);
* the `slabs: 'network'` branch of `build/bank.py` `build_floors` (DESIGN R-12.3's three passes; the `'closed-rooms'`
  loop and `floor_walls` untouched);
* `build/model.py`:
  * `spaces` and `rooms[].space`;
  * the slab and ceiling parts;
  * `stairways`, the tread and landing parts and the clash cuts, from R2's `StairsResult`;
  * `stairOutlines` and the summary's `stairs` block under the new rule;
* `build/settings.py` (the new options, `ceilingHeight`, `floorPast`, the three fix lists kept);
* `build/fixes.py` (closing lines, removed closings, room fixes; set-aside lines kept in the network);
* `build/report.py` (the new report keys and replay facts);
* `propose.py` (`NEW_RULES`);
* `services/builder/tests/test_r1_*.py`;
* `fixtures/upload/settings/*-rooms.json` (after R0), `fixtures/rooms/keys/house.json`.

**Reads:**
* DESIGN R-1 – R-6, R-12.3, R-13;
* `build/bank.py`, `model.py`, `outline.py`, `out/overlay.py` (the old `plate-dropped` rule);
* the scratch trials, as a reference and never imported: `design_step\`, `geo_critique\` (`g2_lib.py` for the fast
  closing, `g2_missdoor2.py`), `revise_step\` (`doorgap3.py`, `x3.py`), `critique_owner_staff\pockets.py`;
* `../upload/GAPS.md`.

**First task, before building on the rules:** run them on the eight floors with your own code and write the figures in
`R1.md`: rings, plate0, rooms and enclosed shapes, the strips (bridges, doorway closings), the unfloored areas with
their mouths, the X holes, the old suite's terrace, one point per room of the house's east building (into
`keys/house.json`), and the bank and the house with each door undone. Compare them with ACCEPTANCE RA-3 – RA-5 and
RA-18. Three rules of DESIGN R-2 were designed from measurements of an earlier rule and never run (the bridge as a strip
between two open areas, the speck limit, the pockets): where a figure differs by more than 2 %, or a pinned point
falls the other way, raise it in `R1.md` and wait for RI's answer on that rule; do not tune silently.

**Delivers:**
* `network_of`: the network of R-2.1 with set-aside lines and open outline lines; the doorway closings; the bridges by
  the fast recipe; faces; rooms and enclosed shapes; the ring;
* `plate_of` (plate0, before holes) and the unfloored areas with their mouths;
* rooms and names (R-3): where a name stands, written areas one-to-one, several names kept;
* terraces (R-4.2);
* X marks (R-4.3);
* `cut_slab`: the wells and kept stair voids from R2's result, shafts, X holes, staff holes; finishing; small pieces
  reported;
* `ceilings_of` (R-5), cut from the plate's outline;
* the report data for the flags `slab-gap`, `room-open`, `room-names`, `doorway`, `hole-skipped`;
* the room and closing fixes with their report rows;
* RA-3, RA-4, RA-5 and RA-18 asserted in heavy tests.

**Tests alone:** ACCEPTANCE 2.1 R1. It needs:
* the reference caches;
* synthetic plans built in the tests;
* the tracer's stairs, while R2 is unfinished.

`test_r_old_rule.py` (R0's) stays green after every change. You may not edit it.

**Must not touch:** R2's modules, `out/**`, the vendored files, `roles.py` / `names.py` / `keys.py`, the API, the viewer,
the web app, R0's frozen test files.

**Depends on:** R0. **Hours:** 36 h (26 – 50).

## R2. Stairs (ports 5742 / 8742 / 4742 / 9742; `%TEMP%\wt-r2`)

**Owns:** `services/builder/walkthrough_builder/build/{stairs_read.py, stairs_build.py}` (the tracer's bodies
replaced), `services/builder/tests/test_r2_*.py`, `tools/rooms/make-stair-dxf.py` (after R0).

**Reads:**
* DESIGN R-7, R-8, R-12.3;
* `build/bank.py:692-799` (today's reader, kept for the old rule);
* the plots (`drawings_inventory/png/house_*_stair.png`, `bank*_stair.png`, `l29_stair*.png`, `l30_stair*.png`) and the
  geometry critic's run of the first version's rules (`geo_critique/run2/flights.txt`);
* `hotel_test/README.md` (its stair, for heights).

**First task, before any solid is built:** read the stairs of the house, the bank and the tower with your reader and
write the riser count of every flight in `R2.md`, against ACCEPTANCE RA-9's reader table. Plot what you read. A count
the drawing does not bear out is a contract issue.

**Delivers:**
* `find_stairs`: riser pieces joined; nosing pairs; lanes by mutual overlap; chains split only by a clear gap; the
  median width; skipped risers counted; the continuation on any layer; deeper first steps and landing edges; the sense
  of each flight; landings for straight, L and U turns; the end of each stair that is at this floor;
* `build_stairs`:
  * matching across floors and the four rows of R-7.5; the riser count and height; the floor a stair rises to;
  * treads with their own riser ends; landings; the lap at the top;
  * the well by headroom in every floor it passes, not grown at the arrival; the fenced band; the arrival patch;
  * the clash cuts (a list of part edits for R1's `model.py`), with their minimum overlap;
  * the `Stairway` record with a clear `walk`;
  * `StairLeft` for every other stair group, with its reason, text, severity and kept void; the pairs of floors with
    no climbable stair;
  * the stair fixes (`bottom`, `lines`, `climb`) and their rows;
* **the contract test**: built from the reference building's DXFs, the treads, landings, well and stairway equal the
  model fixture within 1 mm.

**Tests alone:** ACCEPTANCE 2.1 R2, on:
* the synthetic DXFs, read by the app's own reader into your temp cache;
* the reference caches of the house, the bank and the tower (heavy);
* `FloorBuilt`, `NetworkResult` and plate0 from the tracer, or built in the tests.

**Must not touch:** R1's modules and the orchestration in `bank.py` / `model.py` / `build/__init__.py` (a need goes in
`R2.md`); `out/**`; the API; the viewer; the web app; R0's frozen test files.

**Depends on:** R0. **Hours:** 34 h (25 – 48).

## R3. Outputs (ports 5743 / 8743 / 4743 / 9743; `%TEMP%\wt-r3`)

**Owns:**
* `services/builder/walkthrough_builder/out/**`: `maxscript.py`, `pictures.py`, `presentation.py`, `replay.py`,
  `overlay.py`, `diff.py`;
* `fixtures/upload/max-texts/upload.json` (the `stairs` and `ceilings` notes);
* `tools/upload/gap-report.py` (the new rows);
* `services/builder/tests/test_r3_*.py`.

**Reads:** DESIGN R-3.4, R-6.1, R-10, R-11; the reference building's build result and model;
`bank_test/test_bank_maxscript.py:653` (Extrude amounts in the mock); `furniture/fixtures/maxscript_mock.py` (loaded by
path, `-B`, never changed).

**Delivers:**
* Max:
  * the kinds `tread`, `landing`, `ceiling` in `EXTRA_KINDS`;
  * the Ceilings layers hidden after Build, with the note;
  * the storey statement after each tread, landing and cut-wall part call (not inside `__PX___part`);
  * the `__STOREYFIT__` block placeholder;
  * the stair sentence; the `stairs` and `ceilings` notes;
* the top view's new styles; the legend; the replay's facts and captions;
* the overlay's `spaces`, `holes`, `stairs`, `closings`, `unfloored`;
* the new flags with their texts, `a` and `b`, and `fix-unmatched` for the new fixes. The stored text of `plate-dropped`
  does not change;
* the diff (names, rooms, plate areas, climbable stairs), and a lost floor first;
* the gap report's rows for RA-3 – RA-6 and the tower's storey window.

**Tests alone:** ACCEPTANCE 2.1 R3: both Max goldens and the bank's top view unchanged; every output through
`node tools/run-py.mjs -m walkthrough_api.check_file <kind>`. **`test_r_old_rule.py` (R0's) pins every old-rule output
you touch**: it stays green after every change, and you may not edit it.

**Must not touch:** `build/**`, the vendored files, the API, the viewer.

**Depends on:** R0. **Hours:** 14 h (10 – 19).

## R4. Viewer (ports 5744 / 8744 / 4744 / 9744; `%TEMP%\wt-r4`)

**Owns:**
* `packages/viewer/src/**` except `furniture/**` and `contracts.ts`:
  * `model/parse.ts` (after R0 wrote the v2 rules), `model/styles.ts`;
  * `core/build.ts`, `core/heights.ts`, `core/readouts.ts`, `core/visibility.ts`;
  * `modes/**`;
  * `ui/panel.ts` (the Ceilings tick);
  * `viewer.ts`;
* `packages/viewer/test/**` except the parity golden, its recorder and its test (R0's).

**Reads:** DESIGN R-9, R-12.1 – R-12.2; `../DESIGN.md` 5, 11 – 13; the viewer reader's scripts (`viewer_walk/climb.ts`,
`sim.ts`, `boxes.ts`); the geometry critic's `geo_critique/side.ts` (the walk into a flight's side); the reference
building's model and the synthetic stairs.

**First task, reported before anything else:** a tracer climb in Node on the reference building's model: up the stair
onto the upper slab and down again, with the constants of DESIGN R-9.10.

**Delivers:**
* surfaces;
* single-sided treads and landings that are not colliders;
* the per-floor ceiling meshes with their visibility and tick;
* the `'storey'` fit for treads, landings and cut wall pieces; ceilings fixed;
* the walker of R-9.2 – R-9.5 (the ground ray from foot + 1.0 m), active only with `stairways`;
* floor naming with hysteresis; camera easing;
* `groundAt`; the probe's `foot`, `ground` and horizontal `walk`, and the rule that a probe call starts from where the
  test put the walker (R-9.8);
* the box proxy only if R-9.9's condition is met;
* in `R4.md`: the text of the D-13 "Climbing" row, for RI to put in `../DESIGN.md`.

**Tests alone:** ACCEPTANCE 2.3 R4. The walk-parity golden must pass at every commit-ready point. The template is built
into your own temp folder (`--outDir`), never into `dist/`; its size is reported.

**Must not touch:** `furniture/**`, the contracts, `services/**`, `apps/web/**`.

**Depends on:** R0. **Hours:** 30 h (22 – 40).

## R5. API (ports 5745 / 8745 / 4745 / 9745; `%TEMP%\wt-r5`)

**Owns:** `services/api/walkthrough_api/**` except `models.py`, `models_upload.py`, `store/base.py`'s records and the
route decorators (R0's); and `services/api/tests/**`. That covers:
* `settings_check.py`;
* `drafts/builds.py` and `drafts/adopt.py` (which rules a new draft gets, DESIGN R-1.3; rescale; recipes with keys
  kept);
* `store/local.py` (`create_version` writing `modelFormat` from the `stairways` key);
* `builtmodel.py` (after R0 wrote the v2 rules);
* `check_file`;
* the FakeJobRunner fixtures.

**Reads:** DESIGN R-1.2 – R-1.3, R-6.3, R-12.2 – R-12.5; `upload-contracts.ts`.

**Delivers:** ACCEPTANCE 2.2, with RA-1's four cases of "which rules a draft gets" as one integration test with the
real worker. In your report: the list of tests that build a new version from a pre-milestone recipe and compare bytes,
each now writing the old values first.

**Tests alone:** with the FakeJobRunner. The integration tests with the real worker run against the tracer until
R1 – R3 land, and fail (not skip) under `WT_INTEGRATION=1` when the worker is missing. **After any change to API code,
stop your dev server and start it again before you test by hand** (section 0).

**Must not touch:** the frozen files, the builder, the viewer, the web app.

**Depends on:** R0. **Hours:** 12 h (9 – 17).

## R6. Staff app, plan canvas and their specs (ports 5746 / 8746 mock / 4746 / 9746; `%TEMP%\wt-r6`)

**Owns:**
* `apps/web/src/**` except `src/api/generated/**`, `src/upload/contracts.ts`, `src/build/testids.ts` and the signatures
  of `src/plan/index.ts` (R0's);
* `apps/web/test/**` except the scaffold's contract tests;
* `tests/e2e/rooms.spec.ts`, `tests/e2e/plan-canvas.spec.ts`, and the change in `tests/e2e/upload.spec.ts` (the fold's
  choice, the options read before and after). The builder of the screens writes the spec that clicks them, as U6 did.

That covers:
* `build/FloorsStep.tsx`, `CheckStep.tsx`, `FlagList.tsx`, `steps.ts` (the checklist line), `settingsEdit.ts`, the Build
  and Save steps' counts, new panel components;
* `plan/**` bodies behind R0's signatures;
* the mock API.

**Reads:** DESIGN R-1.3, R-5.1, R-6 (the path table of R-6.4), R-12.4, R-12.6; the overlay fixtures.

**Delivers:**
* the line and its button on the Floors, Build and Check steps; the checklist's warning line; the hint under the old
  `plate-dropped` flag;
* the Floors step's ceiling heights and the fold **Earlier build rules**;
* the three counts on the Build and Save steps;
* the Check step: the three ticks; rooms, holes, stairs, closings and unfloored areas drawn; areas on hover; the counts
  in the page; the tools **Draw a line** (snapping) and **Rooms and stairs**; the room and stair panels; the flag cards'
  buttons; the list **Fixes on this floor** with Remove; the "waiting for Rebuild" marks; the set-aside tick; the
  Heights panel's ceiling height; a lost floor first in the list of changes;
* `settingsEdit` changes; the mock API's new overlay;
* the three specs. A spec merges only layers, floors and furniture from a fixture into the settings the draft already
  has. Canvas clicks go through the `window.__plan` hook. Every project is saved under an `e2e-` id.

**Tests alone:** ACCEPTANCE 2.3 R6 (vitest, mock API) and 2.4 R6 under the mock (`WT_SERVE=web`: the panels and tools
write the right fixes). The steps that need a rebuild run against the tracer's worker, and against the real rules at
integration.

**Must not touch:** `packages/**`, `services/**`, generated files, configs, `package.json` files, the other e2e specs.

**Depends on:** R0. **Hours:** 30 h (22 – 40).

## R7. Viewer browser tests (ports 5747 / 8747 / 4747 / 9747; `%TEMP%\wt-r7`)

**Owns:**
* `tests/e2e/stairs.spec.ts` (the climb, the ceilings' visibility per mode);
* the `stairWalks` addition to `tests/e2e/lib/walks.ts` (the existing helpers unchanged);
* `tests/e2e/lib/target.ts` and `tests/e2e/upload-walk.spec.ts` (the new versions' store and offline folder);
* the scripted frame-rate measure with `tests/e2e/lib/fps.ts`.

**Reads:** ACCEPTANCE RA-8, RA-10, RA-14; the viewer reader's stair-probe proposal; the reference building's fixture
store.

**Delivers:**
* the climb, the keyboard start, the probe-after-a-climb case and the ceiling checks against the reference building's
  offline file, made in the spec's set-up into your own temp folder with the template you built there;
* the comparison of `upload-walk` on the eight old versions with `docs/rooms/reference/upload-walk-9nov/`.

**Tests alone:** the specs on the synthetic files. The real files come at the smoke step (`WT_ROOMS_OFFLINE_DIR`).

**Must not touch:** everything else in `tests/e2e`, `apps/**`, `packages/**`, `services/**`, `dist/`.

**Depends on:** R0 (the R4 code for green runs). **Hours:** 7 h (5 – 10).

---

## RI. Integration (ports 5748 / 8748 and the e2e config's 5711 / 8711; `%TEMP%\wt-ri`)

**RI-0, the smoke step: as soon as R1 and R2 report, while R3 – R7 still run.** Build the house and the bank with the
`-rooms` fixtures. Hand the real offline files, overlay and build result to R4, R6 and R7 (`%TEMP%\wt-ri\smoke`), and
replace the provisional `house-rooms` overlay. Answer the rules R1 raised from its first task. Report within the hour
what fails: this is where the builder's stairs first meet the walker.

Then, after R1 – R7:

1. Read every `docs/rooms/contract-issues/R*.md` and settle each with the smallest change. Only here may a frozen file
   change, with a note in `RI.md`.
2. Run the five drawings with the `*-rooms` fixtures.
3. Run the commands of ACCEPTANCE 3:
   * `check:pins`, `typecheck`, `test:unit`, `test:builder` (with `WT_REF`);
   * `seed`, `test:api` and `WT_INTEGRATION=1 test:api`;
   * `gen:api` (no change), the additive check (both bases), `build`.
4. **The acceptance runs**, with `node tools/rooms/acceptance/run.mjs`, into `%TEMP%\wt-ri\acc` (started as a copy of
   `%TEMP%\wt-r0\acc-9nov`):
   * RA-1 both ways, the five old-rule builds, the four cases of "which rules a draft gets";
   * RA-3 – RA-9 on the five drawings with the new rule, and the tower and the new suite again with their single-line
     flags set aside;
   * RA-13;
   * RA-14 (times and memory from `job.json`; the frame-rate script);
   * RA-15: every new-rule build in two processes. Pin the references in
     `services/builder/tests/test_r_rooms_golden.py` as provisional when the runs pass;
   * RA-18, with `WT_ACCEPTANCE=1`;
   * the old suite's 16 key points, picked once from its plot into `fixtures/rooms/keys/suite.json`.

   Write `docs/rooms/GAPS.md` from the result file. It holds:
   * the new rule against the old rule per drawing (plate, holes, rooms, names, ceilings, stairs);
   * the walk checks (RA-6);
   * the tower's storey window and stair B's counts;
   * every difference classed as option now / option later / check-and-fix now or later / accepted difference.

   If a file cannot be written, return it in a fenced block for the main session.
5. `npm run test:e2e`, every spec, with `WT_DATA_DIR` and `WT_OFFLINE_DIR` on a freshly seeded temp store:
   * `stairs.spec.ts` and `upload-walk.spec.ts` on the new-rule offline files made by `make-offline.mjs` from step 4's
     store (`WT_ROOMS_OFFLINE_DIR`, `WT_UPLOAD_OFFLINE_DIR`);
   * `upload-walk.spec.ts` on the eight old versions, compared probe by probe with 9 Nov;
   * `rooms.spec.ts` against the real API and worker.
6. The prototypes' tests, unchanged, one at a time. The listing of `docs/rooms/reference/outside.txt` and
   `versions.sha1` checked; no `__pycache__`.
7. **The owner's path by hand in Edge**, on 5748 / 8748 (never 5710 / 8710) with a store copy. **Start the servers
   after the last code change; after any fix to API code, stop them (Ctrl+C), start them again and repeat the step:
   nothing reloads by itself.**
   * the house and the bank from their DWGs, through every screen, to the viewer: climb both stairs, and look at the
     ceilings in Walk;
   * the house as saved on 9 Nov → New version, without opening Floors (RA-12 point 2);
   * **the tower and the new suite, timed** (RA-17): the flags before and after, the fixes made, the minutes until
     every room is closed or answered, and the same for a second version with the fixes carried over;
   * screenshots of each step in `%TEMP%\wt-ri\path`.
8. Put the D-13 "Climbing" row (from `R4.md`) into `../DESIGN.md`.
9. **Report**: what passes (commands and counts), the acceptance table with numbers, the gaps, what does not pass and
   why, and the contract issues and how they were settled. There is nothing to deploy; any later deploy is the owner's
   to run.

**Hours:** 30 h (22 – 40), the smoke step included.

## RR. Independent review and fix (after RI; ports 5749 / 8749 / 4749 / 9749; `%TEMP%\wt-rr`)

The independent reviewers are:
* **fidelity**: the floors, holes, rooms and stairs against the drawings' plots, drawing by drawing, with the answer
  keys of `fixtures/rooms/keys/`;
* **code**;
* **breaking it**: open networks, crossing lines that are not X marks, a missed door in an outside wall, a stair with
  no direction, a stair over a door, levels changed in Build settings while on a stair, Ghost → Walk over a stair
  well, a probe after a climb;
* **the staff path**, seen by a non-programmer, with the timed task of RA-17 on the tower and the new suite.

They report their findings. Each finding is verified, then fixed with a test or answered in
`docs/rooms/contract-issues/RR.md`. Every move of a pinned reference is explained there. Then RI's steps 3 – 6 run again
from a clean start: one command for the acceptance runs, servers started fresh. Nothing is deployed.

**Hours:** 18 h (13 – 25).

---

## 8. Order, critical path and checks

* **Order**:
  * R0 runs alone and leaves the tracer green.
  * Then R1 – R7 run at once.
  * R1 and R2 meet through `contracts.py` and the tracer: each replaces its own half and keeps the end-to-end test
    green.
  * R3, R5 and R6 work from the reference building's fixtures; R4 and R7 from its model and the synthetic stairs.
  * RI-0 as soon as R1 and R2 report.
  * Then RI, then RR.
  * Then the main session updates `../STATUS.md`, commits on `milestone-rooms` and merges to `main`, and updates the
    plan and the product document together (the measured agent hours).
  * After this milestone: the door finder's second fix round, then the box editing (the owner's order of 10 Nov).
* **Critical path**: R0 (26 h) → R1 (36 h) → RI (30 h) → RR (18 h) = about 110 h of the 237 h, if the builders run in
  parallel as in the last two milestones.
* **Checkpoints**:
  * after R0: the done-list above; the parity golden and the old-rule guard recorded; the tracer green;
  * after R1's and R2's first tasks: the figures of RA-3 – RA-5, RA-9 and RA-18 in `R1.md` and `R2.md`;
  * after RI-0: the real house and bank built, their stairs climbed in Node;
  * after the builders: each one's report and `R<n>.md`;
  * after RI: ACCEPTANCE RA-1 – RA-18 with numbers;
  * after RR: the re-run from a clean start.

---

## 9. Hours

### 9.1 This milestone (hands-on developer hours, as the plan counts them)

| Part | Likely | Range | What drives it |
|---|---|---|---|
| R0 scaffold | 26 h | 20 – 34 | the walk-parity golden through the frame path; every old-rule output pinned; the extraction of `floor_walls`; the v2 schema and its rules in three checkers; optional settings fields and the additive check's new rule; placeholders in a dozen files; the reference building with everything derived from it; the tracer; the answer keys and the acceptance scripts brought into the repository |
| R1 network, rooms, slabs, ceilings | 36 h | 26 – 50 | three closing rules (bridges as strips, doorway closings, staff lines) and two flag rules; rooms that are not furniture; names; terraces; X marks; holes and kept stair voids; ceilings; the three-pass orchestration; five drawings re-measured first; every door undone as a test |
| R2 stairs | 34 h | 25 – 48 | the hardest reading: riser pieces, nosing pairs, counts pinned per flight, senses, landings, five direction rules, matching across two files, the floor a stair rises to, the well, the clash cuts; the bank's spiral and the tower's U as heavy tests |
| R3 outputs | 14 h | 10 – 19 | three Max kinds, hidden layers and the storey block without moving two goldens; top view, legend, replay, overlay, eight flag kinds, diff, gap rows |
| R4 viewer | 30 h | 22 – 40 | the foot-based walker beside today's exact one, the ground / head / body rays across two floors, the probe's rule, naming, easing, storey fit, ceilings and their tick, parity |
| R5 API | 12 h | 9 – 17 | which rules a draft gets, defaults, combinations, rescale, `modelFormat`, v2 checks |
| R6 staff app, plan canvas and their specs | 30 h | 22 – 40 | the line on three steps, the fold, two canvas tools, panels, flag buttons, the fixes list, ticks, counts, mock overlays, and the owner's-path, canvas and A-7 specs |
| R7 viewer browser tests | 7 h | 5 – 10 | the stair probe in Edge, the ceiling checks, the comparison with 9 Nov, the frame-rate script |
| RI integration, acceptance runs, gap report | 30 h | 22 – 40 | the smoke step; five drawings under both rules; two-process builds; the keys; GAPS.md; every suite (a full check is over an hour); the owner's path by hand with two timed drawings |
| RR independent review and fix | 18 h | 13 – 25 | as the last two milestones (37 and 32 findings) |
| **Total** | **~237 h** | **174 – 323 h** | |

The first version of this plan came to ~194 h (142 – 268). The review added about 43 h: the scaffold and the
integration were too small for what they must leave behind (+22 h), and the door-sized gaps, the flags with their
openings, the set-aside change, the pinned stair counts and the screens' tools are new work (+21 h).

**Two measures of time, both honest.**

| Milestone | Estimate, hands-on developer hours (the plan's measure) | Agent working time (measured) | Agent time as a share of the estimate |
|---|---|---|---|
| foundation | ~40 h | about 13 h | 33 % |
| upload | ~205 h | about 15 h | 7 % |
| **this milestone** | **~237 h** | **forecast 25 – 40 h** | 11 – 17 % |

* The owner reads hours as the plan counts them: **~237 hands-on developer hours.**
* The upload milestone's 7 % came from ports checked against byte-exact prototypes. Here the network, the stairs and
  the walker (R1, R2, R4: 100 h) are new rules judged by ranges and by eye, nearer the foundation's 33 %; the rest is
  nearer the upload's 7 %. That gives **25 – 40 h of agent working time**, of which about 4 h are full check runs.
* The agent time of the design itself (four readers, the design, three critics, this revision) is already spent and is
  not in the forecast. The reviews and the account's usage-limit waits come on top in calendar time: perhaps three to
  five days of the owner's calendar.
* The memory notes hold the two measured figures; `../STATUS.md` and the plan record them in prose only. The main
  session should record this milestone's measured agent hours when it is done.

The owner's part:
* a look at the staff path;
* nothing else (DESIGN R-15: no question is open).

### 9.2 Against the plan (`walkthrough_app_plan.md` sections 4 and 5)

| Plan item | Plan's hours | In this milestone |
|---|---|---|
| Phase 0 "Remaining" (plan :61 – 68, :381, :398): slabs, ceilings and room polygons; stair solids with a ramp collider and the slab void; walking up and down the stairs and hiding walls / ceilings; real floor plates | inside "~75 h (60 – 90), which still includes the openings item" | all of it except hiding walls and the ramp collider (dropped, DESIGN R-18 decision 9); the openings item is done for four drawings (26 – 28 Oct) and open again for the fifth (plan next action 16, its own round after this milestone) |
| Phase 1 "robust builder (openings, rooms, slabs, stairs)" | inside the unitemised base: about 63 h left after the upload milestone, plus the ~90 h upload-overrun line (plan :406). Together these were meant for this and four other items (furniture import and library, materials and lighting, saved views and presentation mode, the layered PDF), put at 110 – 200 h (`../upload/WORK_BREAKDOWN.md` 9.2) | the rooms, slabs and stairs part |
| Phase 1 "Check-and-fix screen" | not itemised | its room, stair and gap tools |

The plan has no line of its own for this work, so how much it holds can only be estimated, on two assumptions:
* this milestone takes Phase 0's remaining ~75 h;
* it takes none of Phase 1's base, which the four other items need in full.

**What the milestone adds to the plan's totals**, on those assumptions: the plan holds **about 75 h (60 – 90)** for a
milestone of **~237 h (174 – 323)**, so it adds **about 160 h** (likely; 85 – 265 h with the ranges).

| Plan total (plan :409 – 412) | Today | With this milestone |
|---|---|---|
| First working version (Phases 0 – 1) | ~616 h | about **776 h** |
| Full internal tool (Phases 0 – 2) | ~821 h | about 981 h |
| Everything | ~1,251 h | about 1,411 h |

The door finder's second fix round (plan next action 16) is not in these figures; it has no estimate yet.

The plan's tables and the product document's Cost table were updated with these figures on 11 Nov (the keep-in-sync
rule: about 776 / 981 / 1,411 h); the main session re-estimates with the measured agent hours once this milestone is
done.
