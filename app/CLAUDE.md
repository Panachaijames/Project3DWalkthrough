# app/: rules for agents (scaffold, 3 Nov 2026)

The real application of the CAD-to-3D walkthrough tool: the viewer package, the staff web app and the API. The design is
final in `docs/` (read these first): `DESIGN.md` (behaviour; sections cited as D-n), `contracts.ts` (types),
`built-model.schema.json` (the model format), `WORK_BREAKDOWN.md` (who owns which files). Where `DESIGN.md` and
`contracts.ts` disagree, `contracts.ts` wins for types and `DESIGN.md` for behaviour.

## Hard rules

* **Never deploy, publish or release anything** (`~/.claude/CLAUDE.md`): no gcloud, firebase, wrangler, vercel, netlify,
  docker push, kubectl, terraform apply, npm publish, gh release, no CI that ships. Local builds, tests and local servers
  only. No cloud accounts. No git commits (the folder is not a repository). Any deploy later is the owner's to run.
* **Write only inside `app/`** (and your own temp folder `%TEMP%\wt-<step>`). The prototype folders (`..`) are the
  reference: read them, run their tests, never change them, never add a file there (that includes `__pycache__`).
* **No installs.** No `npm install`, `npx <new package>`, `pip install`. The library list below is frozen; nothing is added,
  removed or upgraded without the owner. `npx` may run only binaries already in `node_modules/.bin`. Exact versions only.
* **Frozen after the scaffold:** `docs/contracts.ts` (and its copy `packages/viewer/src/contracts.ts`), the schema, the
  API's routes (paths, operationIds, parameters, decorator texts) and `models.py`, every `package.json`, the configs
  (`tsconfig*.json`, `vite*.config.ts`, `vitest.config.ts`, `tests/e2e/playwright.config.ts`, `openapi-ts.config.ts`,
  `components.json`, `pyproject.toml`), the lock files and `apps/web/openapi.json`. A defect goes in **your own**
  `docs/contract-issues/<step>.md` (S, A ... F, I; never another step's); work around it in your own files and say so.
* **Drawing text is untrusted** (room, layer, block, family, floor names, captions): into the DOM with `textContent` only
  (`packages/viewer/src/ui/dom.ts` `el()` has no HTML input), never `innerHTML`.
* **Windows:** the Bash tool collapses double backslashes: put code with backslashes in files written with the Write tool.
  Python prints through cp1252: set `PYTHONIOENCODING=utf-8` (`tools/run-py.mjs` does).
* **Python:** the app's own Python runs through `node tools/run-py.mjs ...` (the venv, `PYTHONDONTWRITEBYTECODE=1`). Python
  that imports or runs prototype code uses the **system** Python 3.14.3 with `-B` (it has shapely; the venv does not).
* **Servers bind 127.0.0.1, URLs use 127.0.0.1**, never `localhost` (Vite's `localhost` is `[::1]` only here). Use only your
  ports (below); every runner checks its port is free first and stops with a message if not.
* **One headless Edge at a time** (`tools/edge-lock.mjs`, `%TEMP%\wt-edge.lock`): Playwright's globalSetup and every CDP
  runner (`tools/cdp.mjs`) hold it; when a run waits, let it wait. Software WebGL runs at 10 - 20 fps: a timed check that
  failed (below 12 fps) is re-run alone before diagnosing.
* **PC first:** phone and tablet layout work is parked; the touch controls are ported as they are.

## Frozen library list (DESIGN.md 4; `npm run check:pins` verifies all of it)

Node 24.14.1, npm 11.11.0, Python 3.14.3 (`services/api/.venv`).

| npm package | Version | Where |
|---|---|---|
| three | 0.186.1 | packages/viewer |
| three-mesh-bvh | 0.9.16 | packages/viewer |
| react, react-dom | 19.3.1 | apps/web |
| react-router | 8.5.0 | apps/web (data mode; `RouterProvider` from `react-router/dom`) |
| @tanstack/react-query | 5.104.5 | apps/web |
| radix-ui | 1.8.1 | apps/web (shadcn new-york components) |
| class-variance-authority | 0.7.1 | apps/web |
| cn | 0.5.0 | apps/web (the shadcn CLI's own copy, 0.2.6, sits in `app/node_modules/cn`: never import it from outside apps/web) |
| lucide-react | 1.59.0 | apps/web |
| tailwindcss | 4.3.3 | apps/web |
| tw-animate-css | 1.4.0 | apps/web |
| typescript | 6.0.3 | root (not 7.x: Hey API needs the compiler API, D-4.3) |
| vite | 8.3.4 | root |
| @vitejs/plugin-react | 6.1.2 | root |
| vite-plugin-singlefile | 2.3.4 | root |
| @tailwindcss/vite | 4.3.3 | root |
| @types/three | 0.186.0 | root |
| @types/react, @types/react-dom | 19.3.0 | root |
| @types/node | 24.19.2 | root |
| @hey-api/openapi-ts | 0.99.0 | root |
| shadcn (CLI) | 4.22.1 | root (run once by the scaffold; do not re-run it) |
| concurrently | 10.0.6 | root |
| vitest | 5.0.5 | root |
| happy-dom | 21.0.3 | root (not jsdom: it needs Node 24.15) |
| @playwright/test | 1.64.1 | root (installed Edge, `channel: 'msedge'`; no downloaded browsers) |
| ajv | 8.20.0 | root (tests only; the viewer has no validator at run time) |

| PyPI package (`services/api/requirements.lock.txt`, 28 pins) | Version |
|---|---|
| fastapi | 0.150.0 (fallback 0.142.4 if a fault shows; owner's call) |
| starlette | 1.9.0 |
| pydantic / pydantic-core | 2.14.1 / 2.50.1 |
| uvicorn | 0.54.0 (plain) |
| pytest | 9.1.1 |
| httpx / httpcore | 0.28.1 / 1.0.9 |
| jsonschema | 4.26.0 |
| closure | annotated-doc 0.0.5, annotated-types 0.8.0, anyio 4.15.1, attrs 26.1.0, certifi 2026.10.18, click 8.5.0, colorama 0.4.6, h11 0.16.0, idna 3.20, iniconfig 2.3.1, jsonschema-specifications 2025.9.1, opentelemetry-api 1.45.1, packaging 26.3, pluggy 1.7.0, pygments 2.21.0, referencing 0.37.0, rpds-py 2026.9.1, typing-extensions 4.16.0, typing-inspection 0.4.4 |

## Ports and temp folders (DESIGN.md 3)

| Who | Web dev / harness | API | Preview | CDP | `WT_TMP` |
|---|---|---|---|---|---|
| `npm run dev`, `preview` (owner, integration) | 5710 | 8710 | 4710 | - | - |
| Playwright e2e (integration) | 5711 | 8711 | 4711 | - | `%TEMP%\wt-e2e` |
| Scaffold | 5700 | 8700 | 4700 | 9700 | `%TEMP%\wt-scaffold` |
| A viewer core | 5721 | - | 4721 | 9721 | `%TEMP%\wt-a` |
| B modes | 5722 | - | 4722 | 9722 | `%TEMP%\wt-b` |
| C furniture + UI | 5723 | - | 4723 | 9723 | `%TEMP%\wt-c` |
| D replay | 5724 | - | 4724 | 9724 | `%TEMP%\wt-d` |
| E API, store, seed | - | 8725 | - | 9725 | `%TEMP%\wt-e` |
| F web app | 5726 | 8726 (mock) | 4726 | 9726 | `%TEMP%\wt-f` |

Set `WT_WEB_PORT`, `WT_API_PORT` and `WT_TMP` to your row for every test run. The prototype tests use 9333 - 9421:
nothing here uses 93xx - 94xx.

## Who owns what (WORK_BREAKDOWN.md; read anything, write only what you own)

* **A** viewer core: `packages/viewer/src/{index,viewer,address,version}.ts`, `src/model/**`, `src/core/**` (not
  `disposer.ts`, `events.ts`), `src/testhook/**`, `src/offline/**`, `packages/viewer/offline/**`, `scripts/make-offline.mjs`,
  `test/unit/{model,core,testhook}/**`, `test/harness/core/**`, `test/fixtures/features.model.json`,
  `tests/e2e/{structure,offline,leak}.spec.ts`.
* **B** modes: `src/modes/**`, `test/unit/modes/**`, `test/harness/modes/**`, `tests/e2e/modes.spec.ts`.
* **C** furniture + panel UI: `src/ui/{root,css,panel}.ts`, `src/furniture/**`, `test/unit/{ui,furniture}/**`,
  `test/harness/furniture/**`, `test/fixtures/furniture/**`, `tests/e2e/furniture.spec.ts`.
* **D** replay: `src/replay/**`, `test/unit/replay/**`, `test/harness/replay/**`, `tests/e2e/replay.spec.ts`.
* **E** API: `services/api/walkthrough_api/**` (bodies only for routes; never `models.py`, decorators, paths),
  `services/api/tests/**`, the contents of `data/` (by the seed only).
* **F** web app: `apps/web/src/**` (not `src/api/generated/**`), `apps/web/test/**`, `apps/web/index.html`,
  `tests/e2e/{web,web-leak}.spec.ts`, the shadcn files in `src/components/ui/`.
* **Scaffold (nobody edits):** `src/contracts.ts`, `src/core/disposer.ts`, `src/core/events.ts`, `src/ui/dom.ts`,
  `test/contracts.test-d.ts`, `test/harness/context.ts` (the shared test context), `test/unit/scaffold/**`,
  `test/harness/scaffold/**`, `test/harness/index.html`, `tests/e2e/lib/**`, the e2e config and global setup / teardown,
  `tools/**`, `fixtures/**`, the configs and `package.json` files.

## Commands (from `app/`)

| Command | Does |
|---|---|
| `npm run dev` | API on 127.0.0.1:8710 and the web app on 127.0.0.1:5710 together (Ctrl+C stops both); the API does not reload on code changes (no `--reload` since 10 Nov 2026, `docs/upload/contract-issues/UI.md` UI-5): restart it after an API change |
| `npm run seed` | rebuilds `data/` from the prototype folders (saved heights kept unless `--reset-overrides`) |
| `npm run build` | typecheck, `dist/web/`, the offline template and one offline HTML per version |
| `npm run build:offline:template` | `dist/offline-template/viewer-template.html` (one file) |
| `npm run gen:api` | `apps/web/openapi.json` from FastAPI, the typed client into `apps/web/src/api/generated/`, then a check |
| `npm run typecheck` | the five tsconfigs, strict |
| `npm run test:unit` | vitest, both projects (`npx vitest run --project viewer` or `web` for one) |
| `npm run test:api` | pytest (`services/api/tests`) |
| `npm run test:e2e` | Playwright `e2e` project (needs `seed` and `build:offline` first) |
| `npm run harness -- --port <yours>` | the viewer's browser harness pages (`packages/viewer/test/harness/**`) |
| `npm run check:pins` | installed versions == the frozen list (npm and pip) |
| `npm run capture:prototype` | re-reads the prototype facts into `fixtures/prototype/` (scaffold tool) |

Playwright runs, with your row's ports and temp folder (Git Bash syntax):

```
WT_WEB_PORT=5722 WT_TMP="$TEMP/wt-b" E2E_TARGET=prototype npx playwright test -c tests/e2e/playwright.config.ts --project=e2e tests/e2e/modes.spec.ts
WT_WEB_PORT=5722 WT_TMP="$TEMP/wt-b" npx playwright test -c tests/e2e/playwright.config.ts --project=harness
```

Write `--project=<name>` with the `=` when a spec path follows: Playwright 1.64.1 reads `--project e2e tests/e2e/x.spec.ts`
as two project names and stops (`Project(s) "tests/e2e/x.spec.ts" not found`; B-9, C-9, D-1). For the same reason
`npm run test:e2e` (its script ends in `--project e2e`) runs every e2e spec and takes no spec path: run one spec with the
`npx` form above.

`E2E_TARGET` = `app` (default: `dist/offline/*.html` and the web app) or `prototype` (the prototype pages, their selectors
and the shim; `@app-only` checks skipped). `WT_SERVE` = comma list of `api`, `web`, `harness` (servers to start; the default
follows the project and target). `WT_SKIP_STORE_CHECK=1` skips globalSetup's seed / offline check. Timed checks go inside
`timedDescribe()` (`tests/e2e/lib/fps.ts`).

## The shared test kit (scaffold)

* `packages/viewer/test/harness/context.ts`: `makeTestContext({ model, presentation?, stages?, renderer?, container? })`, a
  naive but working `ViewerContext` (renderer `'fake'` in Node or happy-dom, `'webgl'` in a harness page). Clean up with
  `ctx.disposer.dispose()`.
* `tests/e2e/lib/`: `target.ts` (file URLs, the selector map for both targets, `isOn`, `hasFlag`, `meshIs` / `meshClass`,
  `fittedNames`, `plates`, `noNetwork`, `waitReady`, `openVersion`), `prototype-shim.ts`, `page.ts` (keys, mouse, touch and
  tap through CDP), `walks.ts` (doorWalks, glassWalks, wallWalks, walkThrough, installPageHelpers), `fps.ts`.
* `fixtures/` (see its README): models (incl. `broken/` with `expected.json`), stages, pictures, CSVs and goldens,
  presentation, prototype facts.

---

# The upload milestone (4 Nov 2026): upload a DWG and build it in the app

Design: `docs/upload/DESIGN.md` (cited U-n), `docs/upload/ACCEPTANCE.md` (A-1 ... A-11), `docs/upload/WORK_BREAKDOWN.md`
(owners, ports; its section 0 binds every step), `docs/upload/upload-contracts.ts` (shapes; copied verbatim to
`apps/web/src/upload/contracts.ts`). Contract issues: `docs/upload/contract-issues/<U0 ... U7, UI, UR>.md`, each step its
own. Everything above still holds; this adds:

* **The builder** is its own process in its own pinned Python, `services/builder/.venv` (Python 3.14.3; approved by the
  owner on 4 Nov). It never imports `walkthrough_api` and the API never imports it: they meet only through a run folder's
  JSON files. Run it with `node tools/run-builder-py.mjs ...` (`-B -P`, cwd `app/`, `PYTHONPATH=services/builder`,
  UTF-8, no bytecode, one OpenBLAS / OpenMP thread, `MPLBACKEND=Agg`, pytest's cache under `WT_TMP`; never `-I`, `-E`,
  `-s`). The venv is the only supported path; `WALKTHROUGH_BUILDER_PYTHON=C:\Python314\python.exe` (user-site
  libraries, no pytest) stands in for a diagnosis only. **No installs after the scaffold.**
* **LibreDWG** lives in `vendor/libredwg-0.14-win64/`, extracted unchanged from `vendor/libredwg-0.14-win64.zip` (the
  release zip, sha1 `edb5c011...`; both gitignored) by `npm run vendor:libredwg -- --zip <zip>`; the tracked
  `vendor/libredwg.manifest.json` lists every file's size and sha1 and `npm run check:pins` verifies them. GPL-3.0-or-later
  (`vendor/LIBREDWG-LICENCE.txt`): it runs ONLY as a separate program (`dwg2dxf.exe`, `dwgread.exe`), never linked or
  loaded, and never ships in the web app or the offline files. The full licence text is the owner's to fetch.
* **Drawings and DXFs are never served to clients and never put in git** (the root `.gitignore` ignores `*.dwg`,
  `*.dxf`; `app/.gitignore` ignores the store's `sources/`, `builds/`, `.uploads/`). Drawing text is untrusted.
* **The machine run lock** `%TEMP%\walkthrough-run.lock` (`WALKTHROUGH_RUN_LOCK`): one run at a time on the machine. A
  builder test that converts, reads or builds a real drawing in the test process is marked `heavy` (its fixture takes the
  lock); a test that spawns the worker is marked `worker` (never takes the lock: the worker does). Never both.
* **The reference** `WT_REF` (default `%TEMP%\wt-u0\ref`) is the scaffold's `npm run make:reference` output: the
  prototype chain run in a scratch copy with the vendored LibreDWG and the builder Python (the six drawings' DXFs and
  `prims.pkl` caches under `proj/detector/<name>/`, their detector outputs under `proj/detector/output/`, the bank's v2
  outputs under `proj/bank_test/`; `manifest.json`). Shared and read-only: a builder that needs a fresh copy of one
  drawing runs `npm run make:reference -- --only <bank|house|suite|tower> --out <WT_TMP>\ref`.
* Set for every run: `WT_TMP=%TEMP%\wt-u<n>`, `WALKTHROUGH_DATA_DIR=<WT_TMP>\data`, `WALKTHROUGH_CACHE_DIR=<WT_TMP>\cache`
  and your ports. Never `app/data` or the default cache in a test. The API's pytest wants `<WT_TMP>\api-tests` to exist
  (`mkdir` it once).

## Builder library list (`services/builder/requirements.lock.txt`, 19 pins; `npm run check:pins` imports each)

| Package | Version | | Package | Version |
|---|---|---|---|---|
| ezdxf | 1.4.4 | | contourpy | 1.4.0 |
| shapely | 2.1.2 (GEOS 3.13.1) | | cycler | 0.12.1 |
| numpy | 2.4.4 | | fonttools | 4.62.1 |
| matplotlib | 3.11.2 (freetype 2.14.3) | | kiwisolver | 1.5.1 |
| pillow | 12.2.0 | | packaging, pyparsing | 26.3, 3.3.3 |
| pytest | 9.1.1 | | python-dateutil, six | 2.9.0.post0, 1.17.0 |
| iniconfig, pluggy | 2.3.1, 1.7.0 | | typing_extensions | 4.15.0 |
| pygments, colorama | 2.21.0, 0.4.6 | | | |

The prototypes' own versions: the byte-identical goldens (the bank's model `c3a9408304a2`, stages, CSV, top view, `.ms`)
depend on them. Builder tests do NOT turn warnings into errors (that would change the vendored detector's control flow).

## Ports and temp folders (docs/upload/WORK_BREAKDOWN.md section 1)

Nothing of the foundation's 57x0 - 5726, 87x0 - 8726, 47x0 - 4726, 97x0 - 9726, nothing of the prototypes' 93xx - 94xx.

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

## Who owns what in this milestone (docs/upload/WORK_BREAKDOWN.md; read anything, write only what you own)

* **U0 scaffold (frozen after it; nobody edits):** `services/builder/{pyproject.toml, requirements.lock.txt}`,
  `walkthrough_builder/{__init__, roles, names, keys, contracts}.py`, `walkthrough_builder/vendor/**`,
  `services/builder/tests/{conftest, kit, test_vendor, test_roles, test_names, test_keys, test_jsonfile, test_oslock,
  test_contracts}.py`; `services/api/walkthrough_api/models_upload.py` and the route decorators of
  `routes/{uploads, builds, offices}.py` and `createProject`; `apps/web/src/upload/contracts.ts`,
  `apps/web/src/plan/index.ts`'s signatures, `apps/web/test/upload-{contracts-copy.test.ts, fixtures.test-d.ts,
  generated-types.test-d.ts}`; `tools/{vendor-libredwg.py, run-builder-py.mjs, check-openapi-additive.mjs}`,
  `tools/upload/**` (except `gap-report.py`, U4's), `vendor/{libredwg.manifest.json, LIBREDWG-LICENCE.txt}`, the
  configs, `package.json` and `fixtures/upload/**` (except as below).
* **U1** `walkthrough_builder/{job, step, isolate, convert, losscheck, cache, runio}.py` and, after the scaffold,
  `jsonfile.py`, `oslock.py`; `services/builder/tests/test_u1_*.py`.
* **U2** `walkthrough_builder/{read, drawing, plangeom, units, levels, grid, areas, suggest, propose}.py`;
  `tests/test_u2_*.py`.
* **U3** `walkthrough_builder/build/**`, `tests/test_u3_*.py`, `fixtures/upload/settings/**` (after the scaffold).
* **U4** `walkthrough_builder/out/**`, `tests/test_u4_*.py`, `fixtures/upload/max-texts/**` (after the scaffold),
  `tools/upload/gap-report.py`.
* **U5** `services/api/walkthrough_api/**` except `models.py`, `models_upload.py` and the route decorators (bodies only:
  the 24 new routes answer 501 until then; `settings_check.py`, `jobs/**`, `bodyguard.py`, `check_file.py` are U5's
  after the scaffold), and `services/api/tests/**`.
* **U6** `apps/web/src/**` except `src/plan/**`, `src/api/generated/**`, `src/upload/contracts.ts`; `apps/web/test/**`
  except `test/plan/**` and the scaffold's three contract tests; `tests/e2e/upload.spec.ts`; the count lines of
  `web.spec.ts` / `web-leak.spec.ts`.
* **U7** `apps/web/src/plan/**` (bodies behind the scaffold's signatures), `apps/web/test/plan/**`,
  `tests/e2e/{plan-canvas, upload-walk}.spec.ts`, the viewer's CSV function in `furniture/logic.ts` and its test.

## Commands added (from `app/`)

| Command | Does |
|---|---|
| `npm run test:builder` | the builder's pytest (`services/builder/tests`) in the builder Python |
| `npm run make:reference -- --out <dir> [--only bank house suite tower]` | the prototype chain in a scratch copy (see above); exit 1 when a check fails |
| `npm run vendor:libredwg -- --zip <zip>` | copy, check, extract and (the first time) write the LibreDWG manifest; `-- --verify` checks the extraction; `-- --add-licence <file>` records the GPL text |
| `node tools/check-openapi-additive.mjs` | the API change is additive against the last commit (paths, schemas; the generated client by exported symbol) and the two contract copies are equal |
| `node tools/run-py.mjs -m walkthrough_api.check_file <kind> <file> [--model <model.json>]` | the API's record checks on one worker file (model, stages, presentation, drawing, plan, overlay, conversion, suggestions, settings, job, spec, launch, diff, pieces, openings, api, office, inputs) |
| `node tools/run-builder-py.mjs tools/upload/make-test-dxf.py small` or `hostile <out.dxf>` | the synthetic test drawings (deterministic) |
| `node tools/run-builder-py.mjs tools/upload/check-derived-mapping.py` | each settings fixture's derived detector mapping against `detector/output/` |
| `node tools/run-builder-py.mjs tools/upload/make-fixtures.py [--only <part>]` | re-makes `fixtures/upload/` (scaffold tool) |
| `node tools/run-api.mjs --port <p> --data <dir> --seed-fresh` | serves a freshly seeded store (the e2e config does this; refuses `app/data`) |

---

# The rooms milestone (10 - 11 Nov 2026): rooms and slabs, then stairs you can climb

Design: `docs/rooms/DESIGN.md` (cited R-n), `docs/rooms/ACCEPTANCE.md` (RA-1 ... RA-18), `docs/rooms/WORK_BREAKDOWN.md`
(owners, ports; its section 0 binds every step). Contract issues: `docs/rooms/contract-issues/<R0 ... R7, RI, RR>.md`, each
step its own. Everything above still holds; this adds:

* **Git**: the folder is a repository now, the branch is `milestone-rooms`. No step commits, switches branches, stashes
  or pushes; the main session commits. `git show`, `git diff` and `git status` are fine.
* **Never start a server on 5710 or 8710** (the owner's `npm run dev`). **Never write `app/data`** (the owner's store)
  and never the default cache: `WALKTHROUGH_DATA_DIR=<WT_TMP>\data`, `WALKTHROUGH_CACHE_DIR=<WT_TMP>\cache`. Browser specs
  run with `WT_DATA_DIR` and `WT_OFFLINE_DIR` on a freshly seeded temp store; a project a spec makes has an `e2e-` id.
* **No reload**: `npm run dev` and `node tools/run-api.mjs` do not reload the API when its code changes. After a change
  to `services/api/**`, stop your server and start it again: a check made before the restart tested the old code.
  Builder code needs no restart (the worker is a new process for every build); the web dev server still hot-reloads.
* **Nobody writes `dist/` while the builders run in parallel.** A builder that needs the viewer template builds it into
  its own temp folder (`--outDir`, as `packages/viewer/test/harness/core/make-e2e-offline.mjs:5-9`).
* **The new rules switch on through three options** (`BuildSettings.options.slabs / ceilings / stairs`). A missing key is
  the old rule (`OLD_RULES`: `closed-rooms`, `off`, `lines`); every new draft gets `NEW_RULES` (`network`, `auto`,
  `climb`). Both sets are named once in each contract (both TypeScript copies, `models_upload.py`,
  `walkthrough_builder/contracts.py`). A model is BuiltModel v2 when it has the `stairways` key.
* **Nothing old moves.** `services/builder/tests/test_r_old_rule.py` pins every output file of the five old-rule builds
  (`fixtures/rooms/old-rule.sha1.json`); `packages/viewer/test/unit/modes/walk-parity.test.ts` pins how the six old
  models walk (`test/fixtures/walk-parity.json`, within 1e-9 m). Both stay green after every change; nobody edits them
  or records them again. The door finder is frozen (`test_vendor.py`).
* **The tracer** (R-12.3): `build/network.py`, `rooms.py`, `slabs.py`, `xmarks.py`, `ceilings.py` (R1's) and
  `build/stairs_read.py`, `stairs_build.py` (R2's) are thin but working, wired into `bank.build_floors_network` behind
  `slabs: 'network'`. `services/builder/tests/test_r_tracer.py` builds `make-stair-dxf.py straight` through the app's
  reader, `build()`, the outputs and the API's checks: it stays green while the bodies are replaced.
* **The reference building** (`tools/rooms/make-reference-building.py`) and everything derived from it are the contract
  (`fixtures/README.md`, the rooms section): the builder's output must equal its model's treads, landings, well and
  stairway within 1 mm.
* **Shared and read-only**: `WT_REF` (`%TEMP%\wt-u0\ref`), `WT_REF_R0` (`%TEMP%\wt-r0\ref`: the new suite read by the
  app's reader; `node tools/run-builder-py.mjs tools/rooms/make-suite-cache.py` makes it again), the copy of the upload
  acceptance store `%TEMP%\wt-r0\acc-9nov`, and `docs/rooms/reference/**`.
* **`WT_INTEGRATION=1`**: a missing reference or worker fails instead of skipping. **`WT_ACCEPTANCE=1`**: runs the tests
  marked `acceptance` (every door undone, the two-process builds, `upload-walk` on 13 files); without it they are
  deselected, so a plain run skips nothing.
* **Frozen after the scaffold R0, for everyone** (besides the contracts of R-12.7, which R0 changed once): `services/
  builder/tests/{conftest, kit, rooms_kit, test_contracts, test_u3_helpers, test_r_old_rule, test_r_tracer,
  test_r_fixtures}.py`, `fixtures/rooms/old-rule.sha1.json`, `package.json`, `tools/make-broken-fixtures.mjs`,
  `tools/check-openapi-additive.mjs` and its rules, `tools/rooms/make-reference-building.py` and what is derived from it
  (`fixtures/models/{rooms-reference, stairs-*}.model.json`, `fixtures/rooms/**` except `keys/{house, suite}.json`),
  `apps/web/src/build/testids.ts`, the signatures of `apps/web/src/plan/index.ts`, `apps/web/test/rooms-testids.test.ts`,
  the parity golden, its recorder and its test, `docs/rooms/reference/**`.

## Ports and temp folders (docs/rooms/WORK_BREAKDOWN.md section 1)

Nothing of 5710 - 5739 / 8710 - 8739 / 4710 - 4739 / 9710 - 9739, nothing of the prototypes' 93xx - 94xx.

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

## Who owns what in this milestone (docs/rooms/WORK_BREAKDOWN.md; read anything, write only what you own)

* **R1** `walkthrough_builder/build/{network, rooms, slabs, xmarks, ceilings}.py`, `build/__init__.py`, the
  `slabs: 'network'` branch of `build/bank.py` (`build_floors_network`, `apply_cuts`; `floor_walls` and the
  `'closed-rooms'` loop untouched), `build/{model, settings, fixes, report}.py`, `propose.py`,
  `services/builder/tests/test_r1_*.py`, `fixtures/upload/settings/*-rooms.json`, `fixtures/rooms/keys/house.json`.
* **R2** `build/{stairs_read, stairs_build}.py`, `tests/test_r2_*.py`, `tools/rooms/make-stair-dxf.py`.
* **R3** `walkthrough_builder/out/**`, `fixtures/upload/max-texts/upload.json`, `tools/upload/gap-report.py`,
  `tests/test_r3_*.py`.
* **R4** `packages/viewer/src/**` except `furniture/**` and `contracts.ts`; `packages/viewer/test/**` except the parity
  golden, its recorder and its test.
* **R5** `services/api/walkthrough_api/**` except `models.py`, `models_upload.py`, `store/base.py`'s records and the
  route decorators; `services/api/tests/**`.
* **R6** `apps/web/src/**` except `src/api/generated/**`, `src/upload/contracts.ts`, `src/build/testids.ts` and the
  signatures of `src/plan/index.ts`; `apps/web/test/**` except the scaffold's contract tests;
  `tests/e2e/{rooms, plan-canvas}.spec.ts` and the change in `tests/e2e/upload.spec.ts`.
* **R7** `tests/e2e/stairs.spec.ts`, the `stairWalks` addition to `tests/e2e/lib/walks.ts`, `tests/e2e/lib/target.ts`,
  `tests/e2e/upload-walk.spec.ts`.
* **RI** integration; `services/builder/tests/test_r_rooms_golden.py`, `fixtures/rooms/keys/suite.json`,
  `docs/rooms/GAPS.md`, the new steps of `tools/rooms/acceptance/run.mjs`. **RR** review and fix.

## Commands added (from `app/`)

| Command | Does |
|---|---|
| `node tools/run-builder-py.mjs tools/rooms/make-stair-dxf.py <variant>\|all <dir>` | the synthetic stair drawings (straight, L, U, two-floor, no-direction, down-up-pair, split-level), one DXF per floor and a manifest of what was drawn and what is expected |
| `node tools/run-builder-py.mjs tools/rooms/make-reference-building.py dxf <dir>` | the reference building's two plans and its manifest (`fixtures` and `stairs` re-make the frozen fixtures: the scaffold's, not for builders) |
| `node tools/rooms/make-fixture-store.mjs --out <dir> [--stairs]` | a tiny store holding the reference building as one saved version (the browser specs' store) |
| `node tools/rooms/reference.mjs versions\|outside --check` | every saved version of `app/data` and every file outside `app/` is as it was when the milestone started |
| `node tools/rooms/reference.mjs store <dir> --check docs/rooms/reference/acc-9nov.versions.sha1` | the same for the upload acceptance store's copy |
| `node tools/rooms/acceptance/run.mjs --list` / `[--only ...] [--tmp <dir>]` | the upload milestone's acceptance scripts, pointed at your temp folder and ports, one JSON result (RI adds the new steps) |
| `node tools/check-openapi-additive.mjs [--base 9eb2d58]` | additive against `66b4c06` (the default: the API before this milestone) or the foundation |
| `node tools/run-builder-py.mjs tools/rooms/make-suite-cache.py` | the new suite's reader cache into `%TEMP%\wt-r0\ref\suite-revit` |
| `WT_ACCEPTANCE=1 npm run test:builder` | also the tests marked `acceptance` |
