# Contract issues: integration (I), 3 Nov 2026

Written only by the integration step (WORK_BREAKDOWN I). It reads every `docs/contract-issues/*.md` and settles each issue
with the smallest change (DESIGN.md 18.0). **`contracts.ts` (both copies) and `built-model.schema.json` are unchanged**;
`apps/web/openapi.json` and `apps/web/src/api/generated/**` are byte-identical to the scaffold's (checked with sha1 before
and after `npm run gen:api`, twice: before and after the one frozen-file change below). Where an issue is information only
(the builder recorded how its port differs from the prototype on purpose), "accepted" means the design is read that way
from now on; nothing was changed for it.

## Changes made here (all inside `app/`)

| File | Change | For |
|---|---|---|
| `services/api/walkthrough_api/models.py` (frozen) | `HeightsUpdate.heights: dict[str, StrictInt]` (was `int`): `"600"`, `true` and `600.0` now get FastAPI's 422 instead of being taken as 600 / 1. Same JSON schema: `openapi.json` and the generated client did not move | E-2b |
| `services/api/tests/test_routes.py` | those three bodies added to `test_heights_validation` | E-2b |
| `packages/viewer/src/core/context.ts` | dispose finds OrbitControls' capturing key listeners on the document even when the host detached the container first: the canvas's root node of connect time is handed to `controls.dispose()` when the canvas is no longer connected | F-5 (fixed at the cause) |
| `tests/e2e/leak.spec.ts` | new check "dispose after the host detached the container leaves nothing behind" (3 mounts; detach, dispose, compare the registration set, contexts, roots, sheets, hooks with the baseline) | F-5 |
| `app/CLAUDE.md` | the two Playwright example lines use `--project=e2e` / `--project=harness`, with a note why (and that `npm run test:e2e` takes no spec path) | B-9, C-9, D-1 |
| `packages/viewer/test/harness/core/viewer.spec.ts` | its header's run line uses `--project=harness` | B-9, C-9, D-1 |
| `app/README.md` | `npm run build:offline:template` listed before `npm run dev` (the template the offline download needs) | F-1 |
| `packages/viewer/src/core/build.ts` | parts walked on or over (`collider: false`, the decks) get `polygonOffset` -2 / -2, so they draw in front of the floor plate's own -1 (as the plan pictures do) | I-1 below |
| `packages/viewer/test/unit/core/build.test.ts` | asserts it: the deck has -2 / -2 and no other part an offset | I-1 |
| `tests/e2e/furniture.spec.ts` | the hover check's `spotOf` counts a box as seen when it is among the nearest furniture hits (two coplanar boxes tie) | I-2 |
| `tests/e2e/web.spec.ts` | the project-page check waits for the list before it counts canvases | I-3 |
| `packages/viewer/test/unit/core/make-offline.test.ts`, `visibility.test.ts` | explicit 60 s timeouts for the tests that spawn node / build six scenes | I-4 |
| `docs/DESIGN.md` | 5.4's deck row and 18.13 say the deck offset; one paragraph after 18.50 points here | I-1 |

## Found at integration (I-1 to I-4)

* **I-1 (the suite's terrace decks were not drawn; DESIGN.md 18.13).** The prototype / app screenshots (WORK_BREAKDOWN
  I.8) showed the suite's two terrace decks (`deck` parts, 0.00 - 0.02 m) missing in the offline file in every view: 18.13
  gives every floor plate `polygonOffset -1` ("no visible change"), and that pulls the plate in front of a part lying 2 cm
  above it (checked in Edge: with the plate's offset off, or the deck's at -2, the decks are back). The suite page had no
  plate offset. Fix: in `buildScene`, a part style with `collider: false` (walked on or over: lies on the plate) gets
  polygonOffset -2 / -2, the value the hotel's plan pictures already use. No other part kind is that thin (the bank's and
  hotel's tread lines lie at 1.2 cm, but their pages had the plate offset too, so they look as before). 18.13 now reads:
  floor plates -1, parts walked on or over -2.
* **I-2 (house hover check, test only).** On the app target the house's hover check found no doorway-approach box the
  Orbit camera sees: the L-shaped sofa is two boxes (`ground-sofa-004`, `-005`, same family, size and approach) whose
  0.80 m tops lie in one plane over each other's middles, so which one a ray meets first is floating-point noise, and with
  three 0.186 it went the other way for both. `spotOf` now counts a box as seen when it is among the nearest furniture hits
  (within 0.1 mm); the label shown is the twin's, which reads the same. House describe re-run: 16 of 16.
* **I-3 (web project page, test only).** `toHaveURL('/projects')` resolves when the navigation commits; React renders the
  list a moment later, so the canvas count right after it saw the old page once under load (1 canvas). The check now waits
  for the four cards (as the Back check before it does) and polls the canvas count to 0; a canvas that stayed would still
  fail it.
* **I-4 (unit tests timing out under load, test only).** `make-offline.test.ts`'s command-line tests (each spawns node) and
  `visibility.test.ts`'s `has()` (six scenes with their BVHs) took 6 s with the browser runs going, over vitest's 5 s
  default (B saw the same). Both groups have a 60 s timeout now, as B's heavy groups do.

## Settlements

### Scaffold

* **S-1 (house collider vertex totals).** Settled as recorded in `fixtures/README.md`: the captured house page (three r160)
  has 6,936 / 6,372 collider vertices, the same as v1 with three 0.186.1, so D-17.2's page numbers (6,924 / 6,348) and its
  earcut explanation for the house do not hold; the mesh COUNT differences (grouping) stand. Risk 19's earcut row is moot
  for the house's totals. No code or test change: A's build test checks the v1 values, which pass.
* **S-2 (JSON Pointer of a duplicate id).** Settled by DESIGN.md 18.49 (the later occurrence, `/openings/5/id`; a missing
  property at its parent). A's `parseBuiltModel` and E's `builtmodel.validate` both report the manifest's pointers (their
  tests run over `fixtures/models/broken/`).

### A (viewer core)

* **A-1 (three 0.186's DFG lookup texture).** Accepted as worked around in `core/context.ts` (`rendererTextures`): the
  self-check reaches 0 textures; the leak spec (20 mounts, gpu() 0 / 0, no `[viewer] dispose left` warning) passes on the
  app target. Note for D-11.8 / risk 19: a three upgrade may add renderer-owned textures; the self-check will say so.
* **A-2 (`Presentation.accent` required, D-8 gives a default).** No change. `Presentation` is the stored shape, which the
  seed always writes in full and E's `checks.py` requires (`accent` among the required fields); `parsePresentation`
  additionally accepts a presentation without it and fills `#2f6f8f`, the same lenient-viewer / strict-API split as 18.34.
  D-8's "Default" column is read as the parser's fallback.
* **A-3 (which ticks show).** Settled: `VisibilityApi.has()` follows D-8 (plates and glass always). Closes C-1.
* **A-4 (room labels, error box).** Accepted; consistent with C-4 and C-5 (checked in Edge by C's harness and the app-target
  structure checks).
* **A-5 (placeholders, `firstFrame`, `__wtvMount`, first `heights.apply` refits, `resolveOptions`).** Accepted as
  information. `LoopApi.firstFrame` and `window.__wtvMount` (only with `?test=1`) stay outside the public contract.
* **A-6 (e2e kit opens only `dist/offline`).** Settled by this step's build: `dist/offline/*.html` exist and every spec ran on
  them; the `WT_OFFLINE_DIR` / `WT_DATA_DIR` overrides stay for a builder's own runs.
* **A-7 (`__host.rayHit` missing on the suite's prototype page).** Accepted (prototype-target only; see C-7).
* **A-8 (Node and Python give the same offline file).** Confirmed here on the real template: `WT_INTEGRATION=1 npm run
  test:api` runs E's byte-equality tests (hand-made corpus with the hostile names, and the seeded store) without a skip.

### B (modes)

* **B-1 (40 random slides >= 90 %).** Accepted as B's spec does it: D-17.4's share is read as >= 90 % for the house and the
  bank, and for the suite and the hotel at least what the prototype's own walking reaches (85 % and 70 %: 35 and 30 of 40,
  inside corners of small rooms). The walking is the prototype's, behaviour for behaviour (pinned by B's unit tests).
* **B-2 (wall crossing judged on the straight line).** Accepted: every leg of the sampled path is checked.
* **B-3 (fixed-time key holds measure the frame rate).** Accepted: the checks hold a key until it has done its job; exact
  speeds stay in the unit tests.
* **B-4 (setMode while locked).** Accepted: Walk and Ghost are refused while the modes are locked (the contract's "Orbit
  only"); `applyAddress` leaves mode, floor, point and direction alone while locked.
* **B-5 - B-8 (blur only the viewer's own control; `ctx.size()` never 0; two no-download flags; client rectangles for
  event maths).** Accepted as information.
* **B-9 (`--project e2e <path>` fails in Playwright 1.64.1).** Fixed in `app/CLAUDE.md` (and A's harness spec header). The
  root script `test:e2e` (frozen `package.json`) ends in `--project e2e`, which is fine with no path after it.

### C (furniture and panel UI)

* **C-1 (ticks).** Settled by A-3. The scaffold's test kit still answers plates and glass from its tick lists: the same rows
  for the four projects, so the kit stays as it is.
* **C-2 (underside on a chain of supports; same as E-5).** No change in this milestone: every seeded model keeps supports on
  nothing, and the viewer's CSV, the API's CSV and the prototype CSVs are byte-identical for all four projects (default and
  typed heights). The two rules differ only for a hand-made chain, which no converter produces. For the next milestone's
  pipeline: add the 5.6 rule "a support has no `on` of its own" (API strict, viewer warns) together with the first model
  that could carry one; until then the divergence is known and documented here.
* **C-3, C-4, C-5 (hiding rules on the root flags in BASE_CSS; room-label CSS; error box through `hidden`).** Accepted:
  identical duplicate declarations in B's, C's and D's chunks are harmless; A's labels and `reportError` match.
* **C-6 (FurnitureApi edge cases).** Accepted: a bad value in `setHeights` counts as missing (back to the model's height);
  `setHeight` / `setVisible` / `setBlocks` for a kind without pieces return false.
* **C-7 (`lib/walks.ts` reads `__host.downHit` / `rayHit`, which two prototype pages lack).** Accepted: the specs carry their
  own portable helpers on the prototype target; on the app target every page has the full `__host`. The kit is unchanged.
* **C-8 (data-wt names given where the selector map had none).** Accepted as additions to D-11.6's map:
  `furniture-titlebar`, `furniture-head`, `furniture-door`, `shows`, `floors`, `[data-slot]`, `legend[data-layout]`.
* **C-9.** Same as B-9: fixed.

### D (replay)

* **D-1.** Same as B-9: fixed.
* **D-2 (the test kit shares one material per kind across floors).** Accepted: the replay clones a rise material already
  patched for another floor; the real `buildScene` makes one material per mesh, so the real viewer never clones.
* **D-3 - D-7 (Esc per D-11.5; one caption placeholder syntax; default glass colour; tick timestamps; repeated CSS).**
  Accepted as information.

### E (API, store, seed)

* **Comparisons:** no differences between E's converters and the provisional suite / house models, or between the
  presentation port and the provisional presentations; the replay and presentation oracles hold. Nothing to settle.
* **E-1 (`Store.read_file_bytes`).** Accepted as an addition to D-9.3 (the offline payload is the stored files' raw text; a
  later `SupabaseR2Store` keeps the text as objects). Only `offline.py` uses it.
* **E-2 (`503 offline_template_invalid`, `500 store_error`).** Accepted as additions to D-10.2's error codes (the frozen
  `responses` already declare 503 as `ErrorResponse`).
* **E-2b (lax `HeightsUpdate`).** Fixed: `StrictInt` in `models.py` (the one frozen file this step changed), with tests;
  `openapi.json` and the generated client byte-identical after `npm run gen:api`.
* **E-3, E-4, E-6, E-7, E-8.** Accepted: the not-found codes; createdAt = the newest mtime of the files a model is made from;
  pytest's store under `<WT_TMP>/api-tests`; the store records refuse unknown fields (a field added to contracts.ts sections
  2 - 4 must be added to `store/base.py` and `checks.py` too); the smaller readings.
* **E-5.** See C-2.

### F (web app)

* **F-1 (`downloads.offlineHtml` never null).** No contract change in this milestone. The template is a build product:
  `npm run build` and `npm run build:offline:template` make it, and the README now lists the template build before
  `npm run dev`; without it the API's 503 names the command. If a deployment can ever run without the template, the next
  milestone makes `offlineHtml` nullable (or adds `available`) together with the client.
* **F-2 (downloads wait for a pending save).** Accepted as an extension of D-15.3 (no shared type changes).
* **F-3 (page globals of specs merge).** Accepted, with the rule: a spec's page globals get a name unique across
  `tests/e2e`.
* **F-4 (smaller readings of D-15).** Accepted as information.
* **F-5 (dispose after the host detached the container leaves OrbitControls' document listener).** Fixed at the cause in
  `core/context.ts`, so `dispose()` is safe whatever a host did to the container first (D-11.2: dispose leaves nothing
  behind); covered by the new leak check on the app target. F's `useLayoutEffect` dispose in `ViewerHost` stays (harmless:
  dispose is idempotent; it also keeps the host's teardown order the same as before).
  The check fails without the fix: built from the old `context.ts` into a throwaway template (`%TEMP%\wt-i\nofix`), the
  detached-dispose check leaves `document keydown capture` registered; with the fix it passes.

## Results (3 Nov 2026, run by the integration step on the integration ports 5711 / 8711 / 4711 and the defaults 5710 / 8710)

| WORK_BREAKDOWN I | Command | Result |
|---|---|---|
| 2 | `npm run check:pins` | ok (28 npm, 28 pip pins) |
| 2, 5 | `npm run typecheck` (also inside `npm run build`) | 0 errors in the five tsconfigs |
| 2 | `npm run test:unit` | 43 files, 555 tests passed (final code) |
| 3 | `npm run seed` | 5 versions, stamps 4b02dc17f286, c3a9408304a2, f1b95c53eb3d, e43270cc0c9b, 6ab030750886 |
| 3 | `npm run test:api` | 260 passed |
| 4 | `npm run gen:api` (twice: before and after the `StrictInt` change) | `apps/web/openapi.json` and `src/api/generated/**` byte-identical (sha1 of all 18 files) |
| 5 | `npm run build` | web (`dist/web`), the template (780 KB, each marker once), 5 offline files |
| 5 | `WT_INTEGRATION=1 npm run test:api` | 260 passed, the Node / Python byte-equality tests ran (no skip), on the final template |
| 6 | `npm run test:e2e` (E2E_TARGET=app, final build) | 201 passed, 0 failed, 0 flaky, 0 skipped (17.7 min): furniture 68, leak 2, modes 40, offline 8, replay 19, structure 50, web 11, web-leak 3, `@app-only` included |
| 6 (extra) | `--project=harness` (all builders' harness pages, port 4711) | 67 passed, before and after the I-1 fix |
| 6 (extra) | the per-spec run before the fixes (r1) | 199 of 201: furniture's house hover (I-2) and web's project page (I-3) failed; both fixed and re-run (house 16 / 16, then the full run above) |
| 6 (extra) | `offline.spec.ts` + `leak.spec.ts` after `data/` was re-seeded and the offline files remade | 10 passed |
| 7 | the prototypes' own tests, unchanged, one at a time under the Edge lock | all pass: test_viewers 127, test_bank 49, test_presidential 37, test_house_openings 13, test_house_furniture 29, test_hotel 56, test_boxes 87; test_bank_maxscript 137, test_presidential_maxscript 151, test_hotel_maxscript 196 checks; also furniture/test_furniture_kit 459 and test_furniture_max 297 checks |
| 7 | prototype folders against a listing taken before the runs | same 450 files, sizes and times; no new `__pycache__` (see the note below) |
| 8 | screenshots, prototype against the offline file, 4 views x 5 versions | `%TEMP%\wt-i\compare` (`<version>-<view>-pair.png`); differences below |
| 9 | `npm run dev` + a browser check (`%TEMP%\wt-i\dev\dev-check.mjs`) | 18 of 18: the four projects listed, each opens below the 48 px bar with its stamp and title, a height typed with real keys is saved (PUT, "Heights saved") and is back after a reload, Max script byte-equal to the seeded file, CSV with the height, offline file with it in its payload and opening from disk; stopped after; `data/` re-seeded with `--reset-overrides` |

Note on item 7: `furniture/test_furniture_max.py` (not in I.7's list; run in addition) writes its two output scripts
`furniture/fixtures/mini_furniture.ms` and `mini_furniture_pres.ms` on every run, by design. Their bytes did not change (a
second run in a copy under `%TEMP%\wt-i\proto-copy` gives the same bytes, and every input is older than their last
write); only the modification time moved, and it was put back to 2 Nov 13:42:47, so the folder matches the listing.

## Visible differences, prototype pages (three 0.160) against the offline files (three 0.186)

Same camera on both targets (Orbit start, top view, the Walk spot and the Ghost spot equal to 2 dp), 1400 x 880, share of
the 3D area's pixels differing by more than 24 / 255:

| Version | Orbit | Walk | Ghost | Top | What differs |
|---|---|---|---|---|---|
| bank v1, bank v2 | 0.00 % | 0.00 % | 0.00 % | 0.30 % | in the top view one room label and one thin edge line lie a pixel apart |
| hotel | 0.00 % | 0.00 % | 0.00 % | 0.32 % | the same |
| suite | 1.40 % | 0.34 % | 0.22 % | 2.40 % | the room labels of the bath / steam / sauna cluster are decluttered (18.12; the page drew them over each other). Before I-1 the two terrace decks were missing (3.05 % Orbit) |
| house | 0.42 % | 0.97 % | 0.04 % | 1.15 % | a single-line piece seen through a window pane: the page drew it over the pane (solid orange), the app behind it (tinted by the 35 % glass). Both are transparent, renderOrder 0 and at the origin, so three's sort falls back to the order the meshes were made, which the one grouping rule (18.32) changed |

No lighting or colour difference shows (the bank and hotel views are identical at this threshold), so three 0.186's new
lighting terms change nothing visible here; walls, glass, edges, stairs, boxes and labels sit in the same places.

## Left open (none blocks this milestone)

* The house's transparent draw order (above): giving the house's `partStyles.single` `renderOrder: 1` would draw its
  single-line pieces after the panes, as the page did; not done here (it changes E's presentation port and the fixture, and
  the app's order is the physically truer one for pieces behind glass). The owner's call. **Settled in the fix step
  (below, parity-cad 1):** the cause was three 0.186's sort key, not the grouping; the viewer now sorts as three 0.160 did.
* Height box typing: the box selects its number in a `setTimeout(0)` after focus, as `furniture_boxes.js` does; a key
  pressed before that timeout (seen once from a script typing at once on a busy page) is appended (`750640`), which the
  box flags and Enter undoes. A person waits long enough; the prototype behaves the same.
* In the web specs the browser once reported `ResizeObserver loop completed with undelivered notifications` (forwarded by
  Vite) during a version switch; harmless (the notification arrives next frame), no test or behaviour depends on it.
  **Fix step (adversarial 14):** `apps/web/index.html` keeps that one message from Vite's terminal forwarding.
* C-2 / E-5 (a 5.6 rule for supports on supports) and F-1 (a nullable `offlineHtml`) wait for the next milestone's
  pipeline; phone and tablet layout stays parked (PC first); the web bundle is one 1.3 MB chunk (no code splitting asked).
* Nothing to deploy: this milestone runs on this computer only; any deploy later is the owner's to run.

## Fix step (3-4 Nov)

After integration four verifiers (parity-cad, parity-revit-pictures, code, adversarial) and an earlier run of the code
reviewer (3 Nov, 15:20 - 15:52: findings F1 - F17 below) reported 52 findings (several the same defect seen by two of them). This step reproduced each before changing
anything, fixed it at its cause in `app/` with a test that would have caught it, and rejected or deferred the rest with the
reason. A first attempt (3 Nov, 19:45 - 20:30) was cut off by a usage limit after changing 57 files: every one of its
changes was read again here (its own transcript gives each edit), kept where right, and finished or corrected (what is
marked "here" below is this run's own; everything else was the first attempt's, checked and kept).

**Frozen files:** `contracts.ts` (both copies), the schema, `models.py`, the route decorators, every `package.json`, the
configs, the lock files and `apps/web/openapi.json` did not change. `npm run gen:api` gives the same 18 files byte for byte
(sha1, before and after; the same as the integration's). Scaffold files changed here, each the smallest change for a
finding: `tools/edge-lock.mjs`, `tools/lib.mjs`, `tools/make-broken-fixtures.mjs` and the corpus it writes
(`fixtures/models/broken/`, one new case; the other eleven files byte-identical), `fixtures/README.md` (its row),
`packages/viewer/test/unit/scaffold/fixtures.test.ts` (the corpus count). Nothing outside `app/` changed.

**Reproduced first:** the API findings with the verifiers' scripts (copies in `%TEMP%\wt-i\fix\repro`, on this step's
port 8711); the viewer findings in Edge on the pre-fix build (kept in `%TEMP%\wt-i\fix2\old-dist`): the house's first
Walk view drew `ground single:own` before `ground pane:clip` (the pane over the piece), ten pinch events zoomed x 0.7738
(the page: x 0.9747). Each new browser check below was run on the old build (fails) and the new one (passes); the web
checks against the old behaviour put back for the run (the picker's condition, the menu's focus return, a plain
`fetchQuery`): each failed, and passes with the fix.

### Fixed

| Finding | Cause and fix | Test that would have caught it |
|---|---|---|
| parity-cad 1 (medium): the house's single-line piece drawn under a window pane in Walk / Ghost | three 0.186 sorts transparent objects by clip-space z, 0.160 by NDC z: a merged mesh whose centre lies behind the eye flips. `core/sort.ts`: the prototypes' comparator (groupOrder, renderOrder, NDC depth far to near, id) through `renderer.setTransparentSort`, the camera's projection taken in `scene.onBeforeRender` (every render, photos included). Not `partStyles.single.renderOrder 1`: that would change every view, this only restores the pages' order | `test/unit/core/sort.test.ts`; e2e `structure.spec` "house: in the first Walk view the single-line piece ... is drawn after the pane" (old build: pane 3rd, piece 1st) |
| parity-cad 2 (medium): a touchpad pinch zoomed about ten times as far; twice as far per notch at devicePixelRatio 2 | three 0.186 OrbitControls: `_customWheelEvent` multiplies a ctrl+wheel by 10 when Ctrl is not held, `_getZoomScale` ignores the pixel ratio. `core/controls.ts` replaces both on the instance (no prototype patching) with three 0.160's scale (0.95 ^ (zoomSpeed x abs(delta) / (100 x floor(dpr))), dpr below 1 read as 1); 0.186's line / page wheel modes kept (Edge always sends pixels). A three upgrade without the two methods logs a warning and the unit test fails | `test/unit/core/controls.test.ts`; e2e `structure.spec` "suite: a touchpad pinch ... zooms Orbit as far as on its page" (old x 0.7738, new 0.9747 = 0.95 ^ 0.5; a mouse notch x 1 / 0.95) |
| parity-cad 3, parity-revit-pictures 2, adversarial 13 (low): a 404 for /favicon.ico on every staff-app load | no icon in `apps/web/index.html`: a `data:` SVG icon there (the browser then asks for none) | `apps/web/test/indexHtml.test.ts`; e2e `web.spec` "a clean console" (no /favicon.ico request, no console error, four version switches) |
| parity-revit-pictures 1 (low): both bank versions downloaded their Max script as `Bangkok_Bank_Sampeng.ms` | the attachment name was the stored file's. `views.max_script_file_name`: `<stem>_v<n><suffix>` (`Bangkok_Bank_Sampeng_v2.ms`) for the Content-Disposition and the version detail's `downloads.maxScript.fileName`; the stored file and its bytes (line 2's stamp) unchanged. The mock API (`apps/web/test/mock-api/core.ts`) answers the same | `test_routes.py` (file name and header per version, the two bank names differ); e2e `web.spec` downloads check (name, bytes equal to the stored file) |
| code 1, adversarial 9, F1 (medium / low): a save and a read of the same file at once failed on Windows (500 text/plain) | no FILE_SHARE_DELETE: a reader blocks `os.replace`, a replace blocks a reader. `jsonio.retry_on_sharing` (2 s, short back-off) around every store read, stat and `os.replace`; what still fails is `StoreError` (500 store_error); `errors.py`: any OSError is 500 store_error, anything else 500 internal_error, always an ErrorResponse | `test_hardening.py` (threads saving and reading one version; a file that stays locked; any other failure); the verifier's real-HTTP race: 0 failures in about 3,200 requests (it had 3 - 8) |
| code 2, F2 (medium): a save the API acknowledged during `npm run seed`'s folder swap was lost | the seed and the API had separate per-process locks. `store/filelock.py`: an OS lock on `<store>/.lock` (released by the OS if a process dies), taken with the thread lock by `LocalStore.exclusive()` for every writer (`write_overrides`, `commit_version`, `create_project`, `create_version`); the seed's whole commit phase holds it. `data/.lock` is in `.gitignore` | `test_hardening.py` (a save during the swap is kept; the lock holds across processes; re-entrant). the save, from another thread inside the swap, waits for the lock and lands in the new folder (revision 2 kept). The verifier's script sends its PUT from inside the seed's own copy (same thread): it now waits and gives up with 500 store_error "the store is busy" instead of answering 200 and being lost |
| code 3, F4, F5 (low): a broken `model.json` answered 500 text/plain; the parsed-model cache trusted `modelSha1` | `views.model_bytes` checks the bytes' sha1 against `version.json`'s `modelSha1` (else 500 store_error on every route, GET model included: never bytes that are not the version's under its ETag); `model_of` parses strictly and checks `photoName` and `furnitureKinds`; the cache is keyed by the verified bytes. `offline.py` checks the same | `test_hardening.py` (not JSON, no photoName, replaced after caching; furnitureKinds not a list) |
| code 4, F3, F7 (low): one broken project took the list and health down; messages carried server paths | `LocalStore.list_projects` leaves out (and logs) a project whose `meta.json` is broken, `listProjects` one whose latest `version.json` is; every store message names files relative to the store (`LocalStore.rel`); the OSError answer has the reason only; here: the 503 `offline_template_missing` message names the template relative to `app/` (`Settings.display_path`) | `test_hardening.py` (one broken project; relative names); `test_routes.py` (the 503 message has no server folder) |
| code 5 (low): Python's `$` let a trailing newline through where the viewer refuses it | `builtmodel`: the schema's `pattern` with ECMA-262 semantics (`$` as `\Z`); `checks.py` and the store use `fullmatch`; `NewProject.id` checked. Here: the shared corpus has `schema/pattern-trailing-newline.json` (`photoName` ends in a newline; plain jsonschema 4.26.0 accepts it, as checked) | `test_hardening.py`; the corpus tests on both sides (`parse.test.ts`, `test_builtmodel.py`) |
| code 6, adversarial 10 (low): NaN / Infinity / 1e400 in a PUT gave a 500 | FastAPI's 422 echoes the input, which JSON could not carry: `errors.py` writes non-finite numbers in it as strings, so the 422 goes out | `test_hardening.py` (NaN, Infinity, -Infinity, 1e400 -> 422) |
| code 7, F6 (low): any Host was answered (DNS rebinding) | `main.py`: Starlette's TrustedHostMiddleware for `127.0.0.1` and `localhost` (any port; `WALKTHROUGH_ALLOWED_HOSTS` to change); another name gets 400 "Invalid host header" before any route. The tests' clients use `http://127.0.0.1` | `test_hardening.py`; the verifier's raw-HTTP script: 400 for `attacker.example` |
| code 8, F9 (low): a plan picture on another origin was refused by WebGL while `ready` said true | `core/pictures.ts`: http(s) pictures load with `crossOrigin = 'anonymous'` (data: and blob: as before), so a server that allows us works and one that does not fails the load (`ready` false) | `test/unit/core/visibility.test.ts` (the CORS mode per URL kind) |
| code 9, F8 (low), first half: the offline payload needed an asset's local path | `Store.asset_bytes` (in the protocol; `LocalStore` reads the file), used by `offline.py`, so a URL-backed store needs no change there | `test_hardening.py` (the payload reads pictures through the store; a missing one is a store error) |
| code 10, F11 (low): a project with no version yet led to Not found | the web app: its card says "No versions yet" and links nowhere; `/projects/<id>` says so instead of going on to `v/0`. The API lists it as before (latestVersion 0: the existing shape) | `pages.test.tsx` "a project with no version yet" |
| code 11 (low): an SVG asset would be served inline from the app's origin | `jsonio.media_type_of` tells only raster pictures (PNG, JPEG, WebP, GIF) by their bytes, never by name; `create_version` refuses any other asset; stored files are served with `Content-Security-Policy: sandbox`, every answer with `X-Content-Type-Options: nosniff` | `test_hardening.py` (raster only; never sniffed or run) |
| code 12, F12 (low): legend colours were not checked | `model/presentation.ts`: `#rrggbb` for legend items too (ModelError at `/legend/items/<i>/colour`) | `test/unit/model/presentation.test.ts` |
| code 13 (low): `Viewer.furniture` still wrote heights after dispose | `viewer.ts guardFurniture`: its writes do nothing once disposed (false), `meshOf` null, reads the last state | `test/unit/core/viewer-events.test.ts`; e2e `offline.spec` "the handle of a disposed viewer types no heights and stores nothing" |
| code 14 (low, here): the stale-lock takeover in `tools/edge-lock.mjs` was check-then-unlink | a takeover now happens only inside a mutex (`<lock>.takeover`, made with mkdir) and the holder is read again inside it; a mutex left by a crash is cleared after 30 s; `WT_EDGE_LOCK_FILE` names another lock file (for the test) | `packages/viewer/test/unit/scaffold/edge-lock.test.ts` (two waiters that read the same dead holder: one holder) |
| code 15 (low, here): `npm run test:api` wrote `services/api/.pytest_cache` | `pyproject.toml` is frozen, so `tools/lib.mjs pyEnv` adds `PYTEST_ADDOPTS`: the cache under `<WT_TMP>/pytest-cache`, or `-p no:cacheprovider` without WT_TMP. The old folder was removed | `packages/viewer/test/unit/scaffold/py-env.test.ts`; after every run here no `.pytest_cache` under `app/` |
| adversarial 1 (high): a height typed while the API did not answer was dropped on leaving the version | the saver sent it once (keepalive) and forgot it. `lib/heightsOutbox.ts`: the newest unsaved map and the saved revision it was typed over are kept in localStorage (`walkthrough-unsaved-heights:<projectId>:<version>`) until the API has it; the version's next visit starts from it (viewer and saver) and sends it; versions not on screen are sent by `startUnsentSender` (start-up, online, focus, every 30 s); while a save has failed the browser asks before the tab is closed or reloaded | `heightsSync.test.tsx` (the outbox); `pages.test.tsx` (the leave warning); e2e `web.spec` "a height typed while saves fail is kept" |
| adversarial 2 (medium): picking back the version on screen while another loaded did nothing | `VersionPicker` compared with the version on screen. It now shows the version being loaded (`useNavigation`) and a pick of the one on screen navigates back to it (replace), which drops the pending load | e2e `web.spec` "the last pick wins" (with the old condition it landed on v1) |
| adversarial 3 (medium): two tabs erased each other's heights | each PUT replaced the map. Every PUT sends `If-Match: "<revision>"`; the API (`routes/furniture.py`, `LocalStore.write_overrides(if_revision)`, under the store lock) answers 412 `revision_conflict` with what is saved now; the tab merges its own changes into it (`mergeChanges`), shows the result and sends again; heights saved elsewhere while the tab has nothing unsaved are taken over (refetch on focus and every 30 s). Here: a refetch older than the tab's own save is no longer taken over (`adopt` only takes a higher revision) | `test_hardening.py` (If-Match, under the lock); `heightsSync.test.tsx` (merge, takeover, the stale refetch); e2e `web.spec` "two tabs on one version" |
| adversarial 4 (medium): with the API stopped the app said "Bad Gateway", dropped the viewer on a refresh, kept the downloads on, and needed Retry | `api/client.ts`: the proxy's 502 / 503 / 504 without the API's body is "the API did not answer (is it running?)"; `fetchOrCached` (routeData) keeps a cached version when only its refresh fails that way; the Downloads menu asks `/api/health` when it opens and disables every item while the API does not answer; a failed save goes again by itself (2, 5, 10, 20, then every 30 s; at once on focus or online) | `format.test.ts` (the client); `pages.test.tsx` "a version already seen stays on screen" (fails with a plain fetchQuery); `DownloadsMenu.test.tsx`; `heightsSync.test.tsx`; e2e `web.spec` "an API that does not answer" |
| adversarial 5 (medium): heights typed into an older download were applied over a newer download's saved heights | one storage key per version. In the offline file a file that carries saved heights adds `:<8 hex of them>` (FNV-1a over `kind=mm`) to the key: what is typed stays with that download; a file without saved heights keeps the plain key | `test/unit/core/context.test.ts`; e2e `offline.spec` "two downloads of a version with other saved heights" |
| adversarial 6 (low): the CSV and offline items stayed on after a refused save | they waited only while saving: now also while a save has failed, with the reason | `DownloadsMenu.test.tsx`; e2e `web.spec` "while a save was refused" |
| adversarial 7 (low): Reset in an offline file threw the owner's saved heights away | design change (DESIGN.md 11.2 now says so): in the offline file Reset goes back to the file's own heights (model + saved); the staff app still resets to the model's (then saved). With no saved heights both are the model's, as on the prototypes | `test/unit/furniture/install.test.ts`; e2e `offline.spec` "two downloads" (Reset -> the file's) |
| adversarial 8 (low): an offline file cut short in its script opened as an empty grey page | a short classic script before the viewer's (static text, no data) shows "This file is incomplete or damaged ... download it again" at DOMContentLoaded unless the viewer started (`window.__wtvStarted`, set by `offline/entry.ts`) | e2e `offline.spec` "a file cut short says so" (in the script and in the data) |
| adversarial 11 (low): after a menu or the picker closed, the keys went to its button | Radix put the focus back on the trigger: both close without that (`onCloseAutoFocus` prevented), so the body has it and W A S D / Space reach Walk | e2e `web.spec` "the keys go to the viewer again" (with the focus return it stayed in the app bar) |
| adversarial 14 (low, here): `[vite] (client) [Unhandled error] ResizeObserver loop ...` in the dev terminal | Vite 8's dev client forwards every window `error` event; the browser's ResizeObserver-loop notification (no error object; the rest arrives next frame) is one. Not provoked here (12 switches, Back and two resizes in Edge); the likely source is a popper's ResizeObserver during a switch, not the viewer. A classic inline script in `apps/web/index.html` (it runs before every module script, Vite's client among them) stops that one message; every other error goes on. A capture-phase listener from `main.tsx` was tried first: Edge still ran Vite's earlier listener first | `apps/web/test/indexHtml.test.ts` (the shipped script); e2e `web.spec` "the browser's ResizeObserver-loop notification reaches no other error listener" (Vite forwarded only the real test error) |
| F13 (low): a ViewerHost test asserted the fake viewer's own heading | renamed to what it checks (ViewerHost's default `create` is the package's, here the fake); the fake's DOM assertions dropped; the real viewer's text-as-text is the offline hostile test's and the panel tests' | itself |
| F14 (low): furniture items were made with `mesh: null` cast to Mesh | `makeBoxes` makes each item with its box (`PieceDraft` before), kind by kind as before, the items in the model's order | the type check (`tsc -p packages/viewer`); the furniture unit tests unchanged |
| F16 (low, here): Node and Python refused different store files | Python (`offline.py`) checks the pictures' floor key and media type as `make-offline.mjs` does; `make-offline.mjs` reads as strictly as the API (UTF-8 with no BOM and no bad bytes, no repeated key: `repeatedKey`) and checks `modelSha1` | `test_offline.py` "Node and Python refuse the same broken files" (6 damaged stores, both refuse); `make-offline.test.ts` "strict reading" |

Tests changed because the behaviour did: `offline.spec` hostile test (the store's real `modelSha1`; three scripts in the
template), `web.spec` downloads check (`Bangkok_Bank_Sampeng_v2.ms`), the mock API's Max script name, the scaffold's corpus
count (4 schema cases), the API tests' clients on `http://127.0.0.1` (the Host check).

### Contract and behaviour notes (no frozen shape changed)

* **PUT furniture-heights** may answer **412 `revision_conflict`** (ErrorResponse; `details: { revision, heights,
  updatedAt }`) when an `If-Match` header names another revision; without the header it still replaces (last write wins).
  The header is read from the request in the route body, so the frozen decorator (which lists no 412) and `openapi.json` did
  not move. The Store protocol (`store/base.py`, E's) gained `write_overrides(..., if_revision=None)`,
  `RevisionConflict` and `asset_bytes`.
* **`downloads.maxScript.fileName`** is `<stem>_v<n>.ms` (same shape, new value); D-10.2's table says so.
* **The offline file's storage key** gains `:<tag>` when the file carries saved heights. `contracts.ts`'s comments on
  `ViewerOptions.furnitureHeights` and `ResolvedOptions.storageKey` still give `<prefix><photoName>:<stamp>` (the type is
  unchanged): for the architect to bring the comment up to date with 11.2.
* **Reset in the offline file** goes to the file's heights (DESIGN.md 11.2 updated). The owner may prefer the old rule.
* Assets are raster pictures only; stored files go out with `Content-Security-Policy: sandbox`; every answer with nosniff.
* Requests for another Host get Starlette's 400 "Invalid host header" (plain text, before any route).
* DESIGN.md: 10.2 (the Max script name, If-Match), 11.2 (Reset, the key), 15.5 (the saver), 18.14, 18.31, the risk table
  and the paragraph after 18.50 point here.

### Rejected

* **F17 (process: the integration changed the frozen `models.py` and ran `furniture/test_furniture_max.py`).** Not a defect
  in the code: both were disclosed in this file; `openapi.json` is still byte-identical (checked again here). This step
  changed no frozen file and did not run `test_furniture_max.py` (it is not in WORK_BREAKDOWN I.7's list and rewrites two
  prototype files).

### Deferred

* **parity-cad 4 (low): 9 - 22 % fewer frames than the pages under software WebGL.** three 0.186's renderer and shaders
  (the draw calls are the same); on the laptop's GPU both run at 60 fps, so clients do not see it. The library is pinned
  (D-4): only the owner can change it. The timed checks keep their rule (re-run alone below 12 fps).
* **code 9 / F10 (low), second half: a URL-backed store's downloads.** A 307 cannot carry the attachment headers, and
  `Store.download(name)` is not told the versioned attachment name: the first object store (next milestone) signs its URLs
  with `response-content-disposition` (and the asset URLs with their media type and nosniff), which needs the name passed
  in. `BlobRef`'s docstring says so; nothing here can test it before such a store exists.
* **F15 (low): CSV fields that a spreadsheet reads as formulas (`=`, `+`, `-`, `@`).** Neutralising them breaks D-18.8's
  byte equality with `furniture_kit.csv_text`; no text field of the four projects starts that way (the leading `-` are
  coordinates). The owner's call, best made with the next milestone's pipeline, which brings arbitrary drawing names.
* **adversarial 12 (low): the app bar below about 650 px.** Phones and tablets are parked (PC first, owner 19 Oct).

### Runs (4 Nov, integration ports 5711 / 8711, `%TEMP%\wt-e2e`, Edge lock held for every browser run)

| Command | Result |
|---|---|
| `npm run check:pins` | ok (28 npm, 28 pip pins) |
| `npm run typecheck` (also inside `npm run build`) | 0 errors in the five tsconfigs (final code) |
| `npm run test:unit` | 49 files, 595 tests passed (final code) |
| `npm run test:api` and `WT_INTEGRATION=1 npm run test:api` | 295 passed (the Node / Python byte-equality and refusal tests ran, no skip); no `.pytest_cache` under `app/` |
| `npm run gen:api` | exit 0; `apps/web/openapi.json` and `src/api/generated/**` byte-identical (sha1 of 18 files before and after; the same as the integration's) |
| `npm run seed` | 5 versions, the same stamps (4b02dc17f286, c3a9408304a2, f1b95c53eb3d, e43270cc0c9b, 6ab030750886); `data/.lock` made |
| `npm run build` | web, the template (783 KB, each marker once), 5 offline files |
| `npm run test:e2e` (E2E_TARGET=app) | 214 passed, 0 failed, 0 flaky, 0 retried (20.8 min): furniture 68, leak 2, modes 40, offline 11, replay 19, structure 52, web 19, web-leak 3; `@app-only` included |
| the new browser checks on the pre-fix build (`WT_OFFLINE_DIR`, `WT_OFFLINE_TEMPLATE` under `%TEMP%\wt-i\fix2\old-dist`) | the 2 new structure and 3 new offline checks fail there (pane drawn 3rd / piece 1st; x 0.7738; no message; the handle typed; 500 over 600), pass on the new build |
| the prototypes' own tests, unchanged, one at a time under the Edge lock (I.7's list) | all pass: test_viewers 127 (in the batch one timed Walk slide failed at 11 fps; re-run alone, as the rule says: 127 of 127), test_bank 49, test_presidential 37, test_house_openings 13, test_house_furniture 29, test_hotel 56, test_boxes 87; test_bank_maxscript 137, test_presidential_maxscript 151, test_hotel_maxscript 196 checks. `furniture/test_furniture_max.py` not run (it rewrites two prototype files; not in the list) |
| prototype folders and project-root files against a listing taken before the runs | the same 450 files, sizes and times; project-root files unchanged; no new `__pycache__` (the two outside `app/` date from 19 and 27 Oct) |
