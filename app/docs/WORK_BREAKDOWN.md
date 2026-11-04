# Work breakdown: the foundation milestone (3 Nov 2026)

One **scaffold** step, then six **builders** (A - F) in parallel, then one **integration** step. Builders do not talk to
each other: the interfaces are `contracts.ts`, `built-model.schema.json` and `DESIGN.md` (sections cited as D-n). Each
builder owns a disjoint set of files; it may read anything, write only what it owns.

## 0. Rules for every step

* Write only inside `app/` (and your own temp folder, `%TEMP%\wt-<step>`). The prototype folders are the reference: read
  them, run their tests, never change them. Their tests must keep passing.
* **Never deploy, publish or release** (no gcloud, firebase, wrangler, vercel, netlify, docker push, npm publish, gh
  release). Local builds, tests and local servers only. No cloud accounts. No git commits (the folder is not a repository).
* **No `npm install`, `npx <new package>`, `pip install` after the scaffold.** The library list is frozen (D-4, `CLAUDE.md`).
  `npx` may run only binaries already in `node_modules/.bin`.
* Exact versions only. Drawing text (room, layer, block, family names, floor names, captions) goes into the DOM with
  `textContent`, never as HTML.
* Windows: the Bash tool collapses double backslashes, so code with backslashes goes into files written with the Write
  tool; Python prints through cp1252, so set `PYTHONIOENCODING=utf-8` (`tools/run-py.mjs` does); headless Edge with software
  WebGL runs at 10 - 20 frames a second and timed checks can flake under load: re-run before diagnosing (a timed check that
  failed below 12 fps is re-run alone first).
* Python that imports or runs prototype code runs with `-B` (no `__pycache__` in a prototype folder), and with the
  **system** Python when it needs the prototypes' libraries (shapely); the app's own Python runs through `tools/run-py.mjs`
  (venv, `PYTHONDONTWRITEBYTECODE=1`).
* Use only your ports and temp folder (D-3): set `WT_WEB_PORT`, `WT_API_PORT` and `WT_TMP` to your row for every test run,
  and bind and call `127.0.0.1`, never `localhost`. Every runner checks its port is free first and stops with a message if
  not. Every headless Edge run (Playwright, a CDP runner) holds the machine-wide Edge lock (`tools/edge-lock.mjs`, D-3);
  when it waits, let it wait: another builder's browser run is going.
* `contracts.ts`, the schema, the API's routes and models, `package.json` files, configs and the lock files are frozen after
  the scaffold. A defect goes in **your own** file `app/docs/contract-issues/<your step>.md` (`S.md`, `A.md` ... `F.md`,
  created empty by the scaffold; never write another step's file); work around it inside your own files and say so in your
  final report.
* Your final report: files written, what passes (commands and counts), what does not, contract issues raised.

---

## S. Scaffold (runs first, alone; ports 5700 / 8700 / 4700 / 9700; temp `%TEMP%\wt-scaffold`)

Goal: a workspace where every later step only writes code. Order matters: 1-6 first (they unblock everyone), then 7-10.

1. **Workspace.** The folders of D-1. Root `package.json` (`"private": true`, `"workspaces": ["packages/*", "apps/*"]`,
   `"engines": { "node": ">=24.14" }`, the scripts of D-2), `.npmrc` (`save-exact=true`, `audit=false`, `fund=false`,
   `update-notifier=false`), `tsconfig.base.json` and the five tsconfigs of the D-4.4 table (no `baseUrl` anywhere),
   `vitest.config.ts` (projects: `packages/viewer` environment `node` with per-file `// @vitest-environment happy-dom`,
   `apps/web` environment `happy-dom`, the web project with the same `VITE_FAKE_VIEWER` alias as step 6),
   `packages/viewer/package.json`
   (`@walkthrough/viewer`, `"type": "module"`, `"exports": { ".": "./src/index.ts", "./offline": "./src/offline/entry.ts" }`,
   deps three, three-mesh-bvh), `apps/web/package.json` (`@walkthrough/web`, deps react, react-dom, react-router,
   @tanstack/react-query, radix-ui, class-variance-authority, cn, lucide-react, `@walkthrough/viewer: "*"` (workspace)),
   root devDependencies for everything else of D-4.2.
2. **Install** with exact versions (`npm install -E ...` per workspace), every package of D-4.1 / D-4.2. Then
   `apps/web/components.json` (style `new-york`, `rsc: false`, `tsx: true`, tailwind css `src/index.css`, baseColor
   `neutral`, cssVariables, iconLibrary `lucide`, aliases `@/components`, `@/components/ui`, `@/lib`, `@/lib/utils`,
   `@/hooks`) and run the shadcn CLI 4.22.1 once (`node_modules/.bin/shadcn add button card badge select dropdown-menu
   separator skeleton tooltip alert --yes`, in `apps/web`). Re-pin anything the CLI changed (`npm install -E` with the
   D-4 versions) and take out the `baseUrl` it writes into the web tsconfig (TS5101; `paths` stays), then
   `tools/check-pins.mjs` (installed versions of every D-4 package == the table; exits 1 otherwise) must pass.
   `@playwright/test` must not download browsers (`PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1` during install; tests use
   `channel: 'msedge'`).
3. **Python.** `python -m venv services/api/.venv` (3.14.3), `requirements.lock.txt` with the 28 pins of D-4.5,
   `.venv/Scripts/python -m pip install -r requirements.lock.txt`, `pip check`, and `pip freeze` equal to the lock with names
   compared PEP 503-normalised (pip prints `pydantic_core`, `Pygments`, `typing_extensions`; `check:pins` checks this too).
   `services/api/pyproject.toml`: project metadata and `[tool.pytest.ini_options]`
   (`testpaths = ["tests"]`, `pythonpath = ["."]`, `filterwarnings = ["error", "ignore:Using .httpx. with
   .starlette.testclient. is deprecated"]`: Starlette 1.9's `StarletteDeprecationWarning`, a UserWarning, verified 3 Nov).
4. **Viewer stubs.** Copy `docs/contracts.ts` to `packages/viewer/src/contracts.ts` verbatim. Create every file of D-11.1
   with its exports typed by the contract aliases; bodies are the working stubs of D-11.1 (Orbit-only modes, `null`
   furniture and replay, a slot panel, a minimal root) or `throw new Error('not implemented: <name>')` for A's core
   functions. Write **complete** implementations of `core/disposer.ts`, `core/events.ts` and `ui/dom.ts` (they are small and
   everyone uses them) with unit tests. `test/contracts.test-d.ts` assigns every export to its alias. `packages/viewer/
   tsconfig.json` and `tsconfig.test.json` (D-4.4), `vite.offline.config.ts` (D-16: `root` packages/viewer/offline and
   `build.outDir` app/dist/offline-template, both absolute from `import.meta.url`, `emptyOutDir: true`, host `127.0.0.1`),
   `vite.harness.config.ts` (root `test/harness` (absolute), `server.host` and `preview.host` `127.0.0.1`,
   `server.strictPort`, `fs.allow` = `app/`, `cacheDir` under `WT_TMP` when set). A unit test that reads a fixture through
   `node:fs` (so the test tsconfig's Node types are exercised from the start).
5. **API stubs.** `services/api/walkthrough_api/` with the module list of D-10.6: `main.py`, `settings.py`, `errors.py`,
   `deps.py` (`get_store`, returning the app's `LocalStore` from `app.state`), `models.py` (every model of D-10.3, camelCase
   aliases), the routes of D-10.2 as plain `def` functions taking `store: Store = Depends(get_store)`, with their exact
   operationIds, paths, params, `response_model`s and `responses` (404 / 422 / 503 with `ErrorResponse`) **and explicit
   `summary=`, `description=` and `response_description=`** (so E's docstrings and names cannot move `openapi.json`, D-10.1);
   `/api/health` works, every other route raises `ApiError(501, 'not_implemented', ...)`. `openapi_export.py` (writes
   `create_app().openapi()` with sorted keys, indent 2). `schema/built-model.schema.json` = copy of `docs/`. Empty packages
   for `store/`, `seed/`. A smoke test (`tests/test_smoke.py`: health 200, OpenAPI has the 13 operationIds).
6. **Typed client.** `apps/web/openapi-ts.config.ts` (D-10.5), the web workspace script `gen:client`, `tools/check-generated.mjs`
   (`src/api/generated/sdk.gen.ts` exists and exports a function for every operationId of `openapi.json`; exits 1
   otherwise), `npm run gen:api` -> `apps/web/openapi.json` and `apps/web/src/api/generated/**`; `apps/web/src/api/client.ts`.
   `apps/web` minimal app (index.html, `src/main.tsx` with `QueryClientProvider` and a router whose pages say "not built
   yet", `src/index.css` with Tailwind and the shadcn theme), `vite.config.ts` (react plugin, tailwind plugin, `@` alias,
   `server.host` and `preview.host` `127.0.0.1`, port 5710, proxy `/api` -> `http://127.0.0.1:${WT_API_PORT ?? 8710}`, the
   same proxy for `preview`, `cacheDir` under `WT_TMP` when set, and **when `process.env.VITE_FAKE_VIEWER === '1'` a
   `resolve.alias` `{ find: /^@walkthrough\/viewer$/, replacement: <abs>/apps/web/test/fake-viewer.ts }`**), the two web
   tsconfigs (D-4.4), and `apps/web/test/fake-viewer.ts` as a stub that re-exports nothing yet (F owns and fills it).
7. **Tools.** `tools/run-py.mjs` (with `PYTHONDONTWRITEBYTECODE=1`), `tools/run-api.mjs` (D-2), `tools/check-pins.mjs`,
   `tools/check-generated.mjs`, `tools/edge-lock.mjs` (D-3: `acquire(step)` / `release()`, `%TEMP%\wt-edge.lock` with the
   `wx` flag, stale when its pid is gone, waits up to 45 min and prints the holder), `tools/cdp.mjs` (copy of
   `viewer-modes/cdp.mjs`, taking the Edge lock around its browser), `tools/capture-prototype-facts.mjs` (D-17.1, with the
   capture methods given there; launches Edge on port 9700 against each prototype page:
   `bank_test/previous_before_fix_round_2026-10-27/bank_3d_preview.html` (bank v1), `bank_test/bank_3d_preview.html`,
   `presidential_test/presidential_3d_preview.html`, `cad_test/house_3d_preview.html`, `hotel_test/hotel_3d_preview.html`;
   writes `fixtures/prototype/<projectId>[-v<n>].json`), `tools/make-presentation-fixtures.mjs`, `tools/make-csv-goldens.py`.
8. **Fixtures** (D-17.1), each listed in `fixtures/README.md` with its source, how it was made and its sha1:
   * copies into `fixtures/models` (bank v1, v2, hotel), `fixtures/stages`, `fixtures/pictures`, `fixtures/csv` (the four
     prototype CSVs), `fixtures/prototype/house_openings_before.json` (copy of `cad_test/test_house_openings_before.json`);
   * the provisional `suite`, `house` and `mini` models: `python -B docs/reference/provisional_v1.py --prototypes .. --out
     fixtures/models` (system Python; it validates before writing and exits 1 on any issue);
   * `fixtures/models/broken/` (schema and cross-reference faults, one per file, and `expected.json` with the JSON Pointer
     each checker must report; D-17.1);
   * the typed-height CSV goldens: `python -B tools/make-csv-goldens.py` (system Python: it loads `furniture/furniture_kit.py`
     by path with `sys.dont_write_bytecode = True`, calls `csv_text` read-only and writes into `fixtures/csv`; afterwards
     `furniture/` still has no `__pycache__`);
   * run the capture tool, then `tools/make-presentation-fixtures.mjs` (`fixtures/presentation/*.json` from the facts and
     D-8's fixed values);
   * in `fixtures/README.md`, the house's expected v1 values of D-17.2 next to the page's captured ones, with the reason
     for each difference (grouping; earcut 2.2.4 vs 3.0.2).
9. **Shared test kit.**
   * `packages/viewer/test/harness/context.ts`: `makeTestContext({ model, presentation?, stages?, renderer?: 'webgl' |
     'fake', container? }): ViewerContext`, a working context built **naively** (one mesh per part with the 5.4 extrude
     rule, kinds' colours, colliders / walkables / late / rise / skins / stairs as in D-5.4, BVH per mesh), a minimal root
     and slot panel, simple working `visibility`, `heights.apply` (group position, `scale` items, Walk level), `loop` with a
     manual `frame()`, `readouts`, disposer and buses; `renderer: 'fake'` (Node) is a stub object with the methods modes and
     the replay call. B, C and D test against it until A's real modules land; it is replaced by nothing (it stays a test kit).
   * `tests/e2e/playwright.config.ts` (D-17.4: `outputDir` `<WT_TMP>/pw-results`, reporter files under `WT_TMP`, projects
     `e2e` and `harness`, no `hasTouch` / `isMobile`, baseURLs on 127.0.0.1), `tests/e2e/tsconfig.json`,
     `tests/e2e/global-setup.ts` (takes the Edge lock; checks the seed and `dist/offline` exist when `E2E_TARGET=app`; makes
     the temp data copy under `WT_TMP` for the web specs) and `global-teardown.ts` (releases the lock), `lib/fps.ts` (reads
     the page's frame rate and attaches it to a `@timed` check), `tests/e2e/lib/target.ts` (`E2E_TARGET` app | prototype:
     the file URL of each project version, the selector map of D-11.6 for both, `isOn(el)`, `meshClass(name)` for the
     house's ray hits, `fitted` / `plates` per target, the no-network rule for the app target only, and skipping `@app-only`
     checks on the prototype target), `lib/prototype-shim.ts` (after load on the prototype pages: `__walkthrough = { THREE:
     await import('three'), ... }`, `__host.openings` / `probes` in v1 shape for the suite and the house, `__host.FL` for
     pages that lack it), `lib/page.ts` (press, hold, click, dblclick, touch, tap, shot, waitReady on a Playwright Page, as
     `cdp.mjs` pageApi; touch and tap through `context.newCDPSession(page)` and `Input.dispatchTouchEvent`),
     `lib/walks.ts` (the page-side helpers of the prototype tests, ported once: `wallWalks`, `doorWalks`, `glassWalks`, the
     house's `walkThrough` / `cross`, the furniture `pageHelpers` lanes, using `__walkthrough.THREE`).
10. **Docs for agents.** `app/CLAUDE.md` (the frozen library table of D-4, the rules of section 0, the ports, the folder
    owners, the commands); `app/README.md` (setup, `npm run seed`, `npm run dev`, tests); `docs/contract-issues/S.md`,
    `A.md`, `B.md`, `C.md`, `D.md`, `E.md`, `F.md`, empty.

**Done when:** `npm run check:pins`, `npm run typecheck` (all five tsconfigs), `npm run test:unit` (the scaffold's own
tests, the `node:fs` one included), `npm run test:api` (smoke), `npx playwright test -c tests/e2e/playwright.config.ts
--list`, `npm run gen:api` (and `tools/check-generated.mjs` passes; no diff on a second run), `npm run
build:offline:template` (the stub viewer builds into one file **at exactly `dist/offline-template/viewer-template.html`**,
each marker once), `npm run dev` (API health and the web page answer on 127.0.0.1; stop it after) all pass,
`E2E_TARGET=prototype npx playwright test -c tests/e2e/playwright.config.ts tests/e2e/lib/smoke-prototype.spec.ts`
(scaffold's: opens the four prototype pages through the target lib, under the Edge lock) passes, the provisional models
validate, and no prototype folder has gained a file (compare a listing taken before the scaffold started). The scaffold
never writes viewer, API or web logic beyond the stubs and the kit above.

---

## A. Viewer core, assembly, offline (ports 5721 / 4721 / 9721; `%TEMP%\wt-a`)

**Owns:** `packages/viewer/src/{index.ts, viewer.ts, address.ts, version.ts}`, `src/model/**`, `src/core/**` (except the
scaffold's complete `disposer.ts`, `events.ts`), `src/testhook/**`, `src/offline/**`, `packages/viewer/offline/**`,
`packages/viewer/scripts/make-offline.mjs`, `test/unit/{model,core,testhook}/**`, `test/harness/core/**`,
`test/fixtures/features.model.json` (+ others it adds there), `tests/e2e/{structure,offline,leak}.spec.ts`.
**Reads:** D-5, 8, 11, 12, 13, 14, 16, 17; the four generators' page scripts; `viewer_modes.js` and `build_replay.js` only
where they call the host (restoreVisibility, applySettings, restore, late); `fixtures/prototype/*.json`.
**Delivers:**
* `parseBuiltModel` / `parseReplayData` / `parsePresentation` / `resolvePresentation` / `parseAddressOptions` (D-5.6, 7,
  8, 11.3); `DEFAULT_PART_STYLES`, `DEFAULT_REPLAY_TEXTS`.
* `buildScene` (D-5.4) matching the prototype facts as D-17.2 says (the house against its v1 values); slab materials
  FrontSide, `renderOrder` from the style; `createContext` (the container must be connected; canvas in the root before
  `new OrbitControls`; renderer, lights, camera start incl. fitSlabs, resize, pixel ratio); `createVisibility`,
  `createHeights` (D-5.5 incl. fit and plinth), `createLabels` (declutter; shown when `ctx.replay` is null or `done`),
  `createPictures` (D-5.7), `createReadouts`, `createLoop`, `withBvh`; `createViewer` in the init order of D-11.4 (step 8:
  `replay.start` before `modes.applyAddress`, then the loop hooks, registered only here) working with the stubs of B / C / D
  and with their real modules; the failure path (any throw after step 1 disposes what exists and rethrows; `testFailAt`);
  `Viewer` handle (events per D-11.5: `modechange` only on a change, `heightschange` only for `typed` / `reset`;
  setHeights / getHeights through `ctx.furniture`), dispose rules (D-11.8) with the self-check; `installTestHook` (D-11.7,
  with `fitted` and `THREE.Color`).
* The offline template, `src/offline/entry.ts`, `scripts/make-offline.mjs` (D-16: markers checked once each, the stamp
  first, then split / join; never `String.prototype.replace` with the payload).
* `test/fixtures/features.model.json`: a small v1 model (two floors) that has every part kind, `fit` top and clip, a
  plinth slab, `stairs.panels`, a deck, skins of both kinds, a picture frame, rooms, openings, probes and 6 furniture
  pieces, valid against the schema.
**Tests alone:** vitest in Node (`buildScene` on every `fixtures/models/*.json` + `features.model.json` against
`fixtures/prototype/*.json` and, for the house, the v1 values of D-17.2; heights; labels layout; readouts by raycast;
`parseBuiltModel` over `fixtures/models/broken/` at the manifest's paths; `parseAddressOptions`); the harness page (5721)
mounting `createViewer` on the bank, hotel, suite and house fixtures with `fixtures/presentation/*.json` (the stubs of
B / C / D in place); `make-offline.mjs` on a temp store you write by hand from the fixtures in `%TEMP%\wt-a\data` (D-9.1
layout, `meta.json`), including names with `</script>`, `$'`, `$&`, `` $` ``, `$$` and the marker texts;
`structure.spec.ts`, `offline.spec.ts` and `leak.spec.ts` with `E2E_TARGET=prototype` where they apply (the structure
checks, with `meshClass` for the house and the hotel checks D-17.4 adds), and the leak spec on your harness page (the
registration set; the failing mounts).
**Must not touch:** `src/modes/**`, `src/furniture/**`, `src/replay/**`, `src/ui/**`, the scaffold's kit files,
`services/**`, `apps/**`, any config or `package.json`.

## B. Viewer modes (ports 5722 / 4722 / 9722; `%TEMP%\wt-b`)

**Owns:** `packages/viewer/src/modes/**`, `test/unit/modes/**`, `test/harness/modes/**`, `tests/e2e/modes.spec.ts`.
**Reads:** `viewer-modes/viewer_modes.js` (port it, behaviour for behaviour), `viewer-modes/test_viewers.mjs`,
`viewer-modes/README.md`, D-11, 12 (the VM rows), 13.
**Delivers:** `installModes` (Orbit / Walk / Ghost, the Camera tool and photos, touch controls kept as they are, the HUD,
the hint texts, `probe`, `lock`, `applyAddress`, `tick`) as a TypeScript port inside the root: absolute overlays, root
flags via `ctx.ui.setFlag`, listeners only through `ctx.disposer`, keys per D-11.5, screen maths root-relative via
`ctx.size()` / `ctx.rectOf()` (`narrow()` = `ctx.size().width <= 700`), CSS without `vh` / `vw` or size media queries
(D-11.6: `%`, `@container wtv`), `restoreVisibility` = `ctx.visibility.applyFloor()`, `onChange` = bus `mode` (on every HUD
update, as the prototype; the viewer filters), photo downloads via `ctx.options.download` unless `noDownload`, the `photo`
event; `applyAddress` exactly as `applyUrl` with D-11.3's `point` rule, called after `replay.start` (so `cam=1` during the
build screen only sets `camWanted`); `faceOpen` over the 23 other headings (D-13); no `ctx.loop.add` (viewer.ts registers
`tick`); the pure helpers `lensFov`, `viewFov`, `frameRect`, `outSize`, `photoName`. The modes row in slot `modes`, the
selectors of D-11.6, the texts word for word.
**Tests alone:** vitest (pure maths; Walk collision in Node with `makeTestContext` on the bank fixture and a synthetic
room; `faceOpen` turns away from a wall even when the current heading would score best); the harness page (5722) with
`makeTestContext({ renderer: 'webgl' })` for keys, pointer lock, wheel, double-click, touch through `lib/page.ts` (CDP),
photos and their exact sizes (downloads read from `testInfo.outputPath()`), and `cam=1` with a locked context;
`modes.spec.ts` with `E2E_TARGET=prototype` (house, bank, suite, hotel; the photo checks without `nodownload`).
**Must not touch:** everything outside the owned files (A's core, C's panel and root, D's replay, the kit).

## C. Viewer furniture and panel UI (ports 5723 / 4723 / 9723; `%TEMP%\wt-c`)

**Owns:** `packages/viewer/src/ui/{root.ts, css.ts, panel.ts}`, `src/furniture/**`, `test/unit/{ui,furniture}/**`,
`test/harness/furniture/**`, `test/fixtures/furniture/**`, `tests/e2e/furniture.spec.ts`.
**Reads:** `furniture/furniture_boxes.js`, `furniture/README.md`, `furniture/test_boxes.mjs`, `furniture/fixtures/**`,
the furniture sections of the four page tests, the four generators' HTML / CSS / panel code, D-8, 11.6, 12, 13, 17.
**Delivers:** `createRoot` (the root with `container: wtv / size`, its constructed stylesheet in
`document.adoptedStyleSheets` with the `<style>` fallback, hint, error box, flags, CSS variables, BASE_CSS starting with
D-11.6's `all: revert` rule), `createPanel` (heading `[data-wt=heading]`, intro runs `[data-wt=intro]`, floors row with the
D-11.5 behaviour, ticks row from `ctx.visibility.has()`, legend inline / lines, slots in order, `markFloors` on bus `mode` /
`floorMode`), all with root-relative sizes (D-11.6); `installFurniture` (the port of `furniture_boxes.js`: boxes, legend
with typing behaviour, Keep doorways clear, hover label, CSV, the leniency of D-5.6, storage modes local / host per D-11.2:
the key with the stamp, differences from the starting heights, bus `furniture` with its source), the pure helpers of
`furniture/logic.ts` and `storage.ts`. Goldens for the awkward model of `test_boxes.mjs` in `test/fixtures/furniture/`
(made once with the prototype's `furniture/fixtures/expected_csv.py`, run read-only with the system Python and `-B`; keep
the script that made them).
**Tests alone:** vitest (logic against `fixtures/csv/*` and the goldens, the awkward / broken variants straight into the
helpers; storage rules incl. the baseline and the stamped key; legend and panel DOM in happy-dom; the CSS rules of D-17.2
ui); the harness page (5723) with `makeTestContext` on `fixtures/models/mini.model.json` (v1, with its doorway records) and
the bank v2 model: typing with real keys (select on focus, 640 not 40, Enter / Escape / leave, junk), colliders and the
doorways rule, hover; the panel at 1366 x 768 / 1920 x 1080; `furniture.spec.ts` with `E2E_TARGET=prototype` (bank, suite,
house, hotel; the stamped storage key `@app-only`).
**Must not touch:** `ui/dom.ts` (scaffold's), modes, replay, core, the kit, `services/**`, `apps/**`.

## D. Viewer build replay (ports 5724 / 4724 / 9724; `%TEMP%\wt-d`)

**Owns:** `packages/viewer/src/replay/**`, `test/unit/replay/**`, `test/harness/replay/**`, `tests/e2e/replay.spec.ts`.
**Reads:** `viewer-modes/build_replay.js` (port it), the replay sections of `test_viewers.mjs` and the page tests,
D-7, 11, 12 (BR rows), 13; `fixtures/stages/*`, `fixtures/prototype/*.json` (replay facts).
**Delivers:** `installReplay` (settings card with `[data-wt=replay-file]` and `[data-wt=replay-layers-title]`, play,
captions with `fillCaption`, steps list and bar, Build row in slot `build`, the rise shader patch on every RiseItem with
marker assertions, replay objects, camera framing root-relative, CSS without `vh` / `vw` or size media queries, phases,
seek, Esc, `start(build, address)` exactly as D-11.4 says: `'skip'` = phase `done` + `ctx.heights.apply(settings)`,
nothing else), calling `ctx.heights.apply(settings)` for every settings change and, at the end, `ctx.visibility.applyFloor()`,
`applyToggles()`, `ctx.furniture?.apply()`; fades `ctx.built.groundPlane` with the late objects (the house page's `hide`
list: hidden on the settings screen and while playing, faded in during finish, opaque after); locks modes; bus
`replayPhase`; the `replayphase` event; no `ctx.loop.add` (viewer.ts registers `tick`). Pure helpers `stepTimes`,
`fillCaption`, `ease`. Defaults from `DEFAULT_REPLAY_TEXTS` (A) when `stages` lacks titles or colours: until A lands, read
them from D-7.2.
**Tests alone:** vitest (timeline, captions incl. the bank's against the facts, input clamping, `apply(T)` on
`makeTestContext` with the bank v2 stages, `start` for each of the three values, the ground plane's fade); the harness page
(5724) for the card, play, skip, replay again, camera path; `replay.spec.ts` with `E2E_TARGET=prototype` (bank, suite,
house: the house's captions are checked there in the browser, and by E on the converted stages).
**Must not touch:** everything outside the owned files.

## E. API, store, seed and converters (ports 8725 / 9725; `%TEMP%\wt-e`)

**Owns:** `services/api/walkthrough_api/**` and `services/api/tests/**` (not `.venv`, `requirements.lock.txt`,
`pyproject.toml`); the contents of `app/data/` (written only by your seed).
**Reads:** D-5 to 10, 16, 17.3; the prototype data files and generators named in D-9.2; `furniture/furniture_kit.py`
(csv_text, to port); `fixtures/prototype/*.json` (oracles).
**Delivers:** `LocalStore` behind `Store` (D-9.3: `meta.json`, the reserved names left alone, `stage()` and
`create_version` with `BlobSource` per D-9.5), reached by routes only through `Depends(get_store)`; the seed (D-9.2) with the
converters (D-6, incl. the house's `sheetShift`), the replay conversions (D-7.4) and the presentation ports (D-8);
`builtmodel.validate` (D-5.6, strict); every route's body (D-10.2) without changing a path, operationId, parameter,
model, decorator text or `models.py` (routes stay plain `def`; the scaffold's `openapi.json` must stay byte-identical: a
test re-exports and compares); `furniture_csv.py`; `offline.py` (D-16, reading the template from settings: markers once
each, stamp first, then `str.split`); the pytest suite of D-17.3.
**Tests alone:** pytest with `TestClient` on a temp store seeded from the prototypes into `%TEMP%\wt-e\data`; the
converters against the provisional `fixtures/models/suite.model.json` and `house.model.json` (deep equality) and the
presentation port against `fixtures/presentation/*.json`, each difference written to `docs/contract-issues/E.md`; the
house, bank and suite caption oracles against `fixtures/prototype/*.json`; `fixtures/models/broken/` at the manifest's
paths; for the offline assembly a hand-made template string with the two markers and the D-16 corpus of names; `uvicorn`
on 8725 for manual checks. The byte-equality test against `make-offline.mjs` is written now and skips when
`dist/offline-template/viewer-template.html` or the Node script is missing, **but fails instead when `WT_INTEGRATION=1`**.
**Must not touch:** anything outside the owned files; the API's public shapes, route decorators and `models.py`;
`apps/web/openapi.json`.

## F. Web app (ports 5726 / 8726 / 4726 / 9726; `%TEMP%\wt-f`)

**Owns:** `apps/web/src/**` except `src/api/generated/**` (generated), `apps/web/test/**` (incl. `test/fake-viewer.ts`,
whose stub the scaffold created), `apps/web/index.html`, `tests/e2e/{web,web-leak}.spec.ts`; the shadcn files in
`src/components/ui/` after the scaffold added them.
**Reads:** D-10 (the API as the generated client sees it), 11.2 (the viewer's public API), 15, 17.4; `apps/web/openapi.json`.
**Delivers:** the routes, screens and wrapper of D-15: `router.tsx`, `pages/ProjectsPage.tsx`, `pages/ProjectRedirect.tsx`,
`pages/ProjectVersionPage.tsx`, `pages/NotFound.tsx`, `components/{AppBar, ProjectCard, VersionPicker, DownloadsMenu,
HeightsStatus, ViewerHost}.tsx` (ViewerHost as D-15.4, with `useEffectEvent`, no ref written during render),
`lib/{useHeightsSaver.ts, format.ts, viewerProject.ts}`; StrictMode on in `main.tsx`.
**Tests alone:** vitest (ViewerHost with a fake `create`, StrictMode double mount, recreation on version change, a `create`
that throws, the saver); Playwright on the dev server (5726, `127.0.0.1`) with the API answered by `page.route` from typed
fixtures (the bank and hotel fixture models are real v1, `fixtures/presentation/*.json` for the presentations; version /
project JSON hand-written to the generated types) and, for the page flow before the viewer exists, `VITE_FAKE_VIEWER=1`,
which the scaffold's `vite.config.ts` (and vitest's web project) already turns into an alias of `@walkthrough/viewer` to
`test/fake-viewer.ts`: F writes that file (the names `src/index.ts` exports: `createViewer` as a div that records create /
dispose and can emit `heightschange`, the `parse*` functions as plain casts, `parseAddressOptions`, `ModelError`); a small
mock server on 8726 if needed. `web.spec.ts` / `web-leak.spec.ts` must also run unchanged against the real viewer and API
at integration (they read ports from `WT_WEB_PORT` / `WT_API_PORT`), including D-17.4's computed-style check (`@app-only`).
**Must not touch:** `packages/**`, `services/**`, generated files, configs, `package.json`.

---

## I. Integration (after A - F; ports 5711 / 8711 / 4711 and the defaults 5710 / 8710 / 4710)

1. Read every `docs/contract-issues/*.md` (E's includes any difference between its converters and the provisional
   fixtures); settle each with the smallest change (only here may `contracts.ts` change, together with
   `docs/contracts.ts`, and only with the architect's note in the issue).
2. `npm run check:pins`, `npm run typecheck`, `npm run test:unit`.
3. `npm run seed` (real `data/`), `npm run test:api`.
4. `npm run gen:api` and confirm no change in `apps/web/openapi.json` or `src/api/generated/**`.
5. `npm run build` (web + offline template + one file per version); `WT_INTEGRATION=1 npm run test:api` (the Node / Python
   offline byte-equality test now fails rather than skips if anything is missing).
6. `npm run test:e2e` with `E2E_TARGET=app`: every spec (structure, offline, leak, modes, replay, furniture, web,
   web-leak), `@app-only` included. Timed specs may be re-run once before diagnosing (alone if they failed below 12 fps).
7. Run the prototype tests unchanged, one at a time (`node viewer-modes/test_viewers.mjs`, `node bank_test/test_bank.mjs`,
   `node presidential_test/test_presidential.mjs`, `node cad_test/test_house_openings.mjs`, `node
   cad_test/test_house_furniture.mjs`, `node hotel_test/test_hotel.mjs`, `node furniture/test_boxes.mjs`, the
   `*_maxscript.py` checks with the system Python and `-B`): they must still pass (nothing outside `app/` changed; no
   `__pycache__` appeared in a prototype folder).
8. Screenshots of the same four views per project (Orbit start, Walk at a fixed spot, Ghost, top view) from the prototype
   pages and from the offline files, side by side in `%TEMP%\wt-i\compare`; list visible differences (three 0.160 -> 0.186).
9. `npm run dev`: one command starts the API and the web app (on 127.0.0.1); `/projects` lists the four projects with their
   cards; a project opens with the viewer filling the window below the app bar and looking as it does in the offline file;
   heights save. Stop it.
10. Report: what passes (commands and counts), what does not and why, the contract issues and how they were settled. There
    is nothing to deploy in this milestone; any later deploy is the owner's to run.
