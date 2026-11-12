# Walkthrough application: foundation design (3 Nov 2026)

Architect's design for the milestone the owner decided on 3 Nov 2026: from prototypes to the real application, the plan's
Phase 0.5 and the start of Phase 1 (`walkthrough_app_plan.md` sections 3.5, 4; decisions B, H, I, J). Five or six builders
implement it in parallel from this file, `contracts.ts` (types), `built-model.schema.json` (the model format) and
`WORK_BREAKDOWN.md` (who does what). Where this file and `contracts.ts` disagree, `contracts.ts` wins for types and this
file for behaviour; report the disagreement (section 18.0).

**In:** the viewer as one framework-free TypeScript package doing everything the four prototype pages do; one model format
(BuiltModel v1) with converters; a FastAPI service over a local file store seeded from the four prototypes; the staff web
app (project list, project page, versions, downloads, furniture heights saved); the offline single HTML per version; unit,
API and browser tests. **Out (seams left for them):** uploading and building a DWG in the app and the layer-mapping /
check-and-fix screen (next milestone, section 9.5), rooms / slabs / climbable stairs, login, share links, anything in the
cloud. **Never:** deploys, publishes, releases (`~/.claude/CLAUDE.md`), changes outside `app/`.

Contents: 1 layout . 2 npm scripts . 3 ports . 4 frozen libraries . 5 BuiltModel v1 . 6 conversions . 7 replay data v1 .
8 presentation v1 . 9 store and seed . 10 REST API . 11 packages/viewer . 12 port map . 13 constants . 14 per-project
differences . 15 apps/web . 16 offline single HTML . 17 test plan . 18 decisions made here . 19 risks . 20 review notes

Revised on 3 Nov after two independent reviews (parity and engineering, 40 findings): every finding was checked against the
prototypes, the plan and the registries; what changed and the alternatives not taken are in section 20.

---

## 1. Folder layout

```
app/
  CLAUDE.md                     rules for agents + the frozen library list (scaffold, from section 4)
  README.md                     how to run (scaffold)
  package.json                  npm workspaces ["packages/*", "apps/*"], root scripts and root devDependencies
  package-lock.json             written by the scaffold only
  .npmrc                        save-exact=true, audit=false, fund=false, update-notifier=false
  tsconfig.base.json            strict compiler settings (section 4.4)
  vitest.config.ts              test.projects: packages/viewer, apps/web
  docs/                         DESIGN.md, built-model.schema.json, contracts.ts, WORK_BREAKDOWN.md
    reference/provisional_v1.py           the architect's provisional suite / house / mini conversion (run once by the scaffold, 17.1)
    contract-issues/<step>.md             one file per step (S, A-F, I), each written only by its step (18.0)
  packages/viewer/              @walkthrough/viewer (builders A, B, C, D, by folder: section 11.1)
    package.json  tsconfig.json  tsconfig.test.json  vite.offline.config.ts  vite.harness.config.ts
    offline/viewer-template.html          the offline page's source (A)
    scripts/make-offline.mjs              template + store -> dist/offline/<project>-v<n>.html (A)
    src/                                  section 11.1
    test/unit/<area>/*.test.ts            vitest, per owner folder (core, model, modes, furniture, ui, replay)
    test/harness/<area>/*.html|ts         browser harness pages per owner, served by `npm run harness`
    test/harness/<area>/*.spec.ts         Playwright specs against those pages (project `harness` of the e2e config, 17.4)
    test/fixtures/                        package fixtures (A: features.model.json; C: furniture goldens)
  apps/web/                     @walkthrough/web (builder F)
    package.json  index.html  vite.config.ts  tsconfig.json  tsconfig.test.json  components.json  openapi-ts.config.ts
    openapi.json                          exported from FastAPI by `npm run gen:api` (generated, committed)
    src/main.tsx  src/router.tsx  src/index.css
    src/api/client.ts  src/api/generated/**      Hey API output (generated; never hand-edited)
    src/components/ui/**                  shadcn components (added once by the scaffold, then ours)
    src/components/*.tsx  src/pages/*.tsx  src/lib/*.ts
    test/**                               vitest (happy-dom); test/fake-viewer.ts (F) is what VITE_FAKE_VIEWER=1 loads
  services/api/                 FastAPI service (builder E)
    pyproject.toml  requirements.lock.txt  .venv/ (Python 3.14.3, created by the scaffold)
    walkthrough_api/                      section 10.6
    tests/                                pytest
  data/                         the local store (section 9), written by `npm run seed`; never edited by hand
  dist/                         build outputs: web/, offline-template/viewer-template.html, offline/<project>-v<n>.html
  fixtures/                     shared read-only fixtures made by the scaffold (section 17.1)
  tests/e2e/                    Playwright: config, tsconfig.json and lib/ by the scaffold, specs by builders A-F
  tools/                        run-py.mjs, run-api.mjs, check-pins.mjs, check-generated.mjs, edge-lock.mjs,
                                capture-prototype-facts.mjs, make-presentation-fixtures.mjs, make-csv-goldens.py, cdp.mjs (copy)
```

Paths in scripts are relative to `app/`. The prototype folder is `..` from `app/`. No file outside `app/` is ever written,
and that includes Python bytecode: anything that imports or runs prototype Python does it with `python -B` (or
`PYTHONDONTWRITEBYTECODE=1`, which `tools/run-py.mjs` sets), so no `__pycache__` appears in a prototype folder.

## 2. npm scripts (root `app/package.json`)

| Script | Command | Does |
|---|---|---|
| `dev` | `concurrently -k -n api,web -c blue,green "npm:dev:api" "npm:dev:web"` | API on 8710 and the web app on 5710, one command, both stop together |
| `dev:api` | `node tools/run-api.mjs --port 8710` | uvicorn `walkthrough_api.main:app` from the venv, data `app/data`; no `--reload` since 10 Nov 2026 (on Windows its restart is a Ctrl+C to the whole terminal and stopped `npm run dev`: docs/upload/contract-issues/UI.md, UI-5): after an API change, Ctrl+C and `npm run dev` again |
| `dev:web` | `npm run dev -w @walkthrough/web` | `vite --port 5710 --strictPort` on 127.0.0.1, proxy `/api` -> `http://127.0.0.1:8710` |
| `build` | `npm run typecheck && npm run build:web && npm run build:offline` | everything that ships to `dist/` |
| `build:web` | `npm run build -w @walkthrough/web` | `vite build` -> `dist/web/` |
| `build:offline` | `npm run build:offline:template && npm run make:offline` | the template, then one file per version |
| `build:offline:template` | `vite build -c packages/viewer/vite.offline.config.ts` | `dist/offline-template/viewer-template.html` (vite-plugin-singlefile) |
| `make:offline` | `node packages/viewer/scripts/make-offline.mjs --data data --template dist/offline-template/viewer-template.html --out dist/offline` | `dist/offline/<projectId>-v<n>.html` for every version (section 16) |
| `seed` | `node tools/run-py.mjs -m walkthrough_api.seed --prototypes .. --data data --force` | rebuilds `data/` from the prototypes (section 9.2); saved heights are kept unless `--reset-overrides` |
| `gen:api` | `node tools/run-py.mjs -m walkthrough_api.openapi_export apps/web/openapi.json && npm run gen:client -w @walkthrough/web && node tools/check-generated.mjs` | OpenAPI from FastAPI (no server), then the typed client, generated **inside `apps/web`** (openapi-ts resolves the config's `input` / `output` against the working folder, and exits 0 when the input is missing: checked 3 Nov), then a check that `apps/web/src/api/generated/sdk.gen.ts` exists and exports a function for every operationId of `openapi.json` |
| `typecheck` | `tsc -p packages/viewer && tsc -p packages/viewer/tsconfig.test.json && tsc -p apps/web && tsc -p apps/web/tsconfig.test.json && tsc -p tests/e2e` | strict, `noEmit` in every tsconfig (4.4) |
| `test` | `npm run typecheck && npm run test:unit && npm run test:api && npm run test:e2e` | every test |
| `test:unit` | `vitest run` | both workspaces (projects) |
| `test:api` | `node tools/run-py.mjs -m pytest services/api/tests -q` | pytest |
| `test:e2e` | `playwright test -c tests/e2e/playwright.config.ts --project e2e` | needs `seed` and `build:offline` first (globalSetup checks and says so) |
| `harness` | `vite -c packages/viewer/vite.harness.config.ts` | serves `packages/viewer/test/harness/**` on 127.0.0.1 (each builder passes `--port`) |
| `preview` | `vite preview -c apps/web/vite.config.ts --port 4710 --strictPort` | the built web app on 127.0.0.1, proxy `/api` -> 8710 |
| `check:pins` | `node tools/check-pins.mjs` | installed npm versions and `pip freeze` equal section 4 exactly (Python names compared PEP 503-normalised: lower case, runs of `-`, `_`, `.` as one `-`; pip prints `pydantic_core`, `Pygments`, `typing_extensions`) |
| `capture:prototype` | `node tools/capture-prototype-facts.mjs --port 9700` | facts from the prototype pages -> `fixtures/prototype/*.json` (scaffold; methods in 17.1) |

Workspace scripts: `packages/viewer`: `test` = `vitest run`, `typecheck` = `tsc --noEmit`. `apps/web`: `dev` =
`vite --port 5710 --strictPort`, `build` = `tsc --noEmit && vite build`, `test` = `vitest run`, `gen:client` =
`openapi-ts -f openapi-ts.config.ts`.
`tools/run-py.mjs` runs `services/api/.venv/Scripts/python.exe` (or `.venv/bin/python`) with `cwd = app/`,
`PYTHONPATH=services/api`, `PYTHONIOENCODING=utf-8`, `PYTHONUTF8=1`, `PYTHONDONTWRITEBYTECODE=1`, and passes its arguments
through; it exits with Python's code. `tools/run-api.mjs` does the same for `-m uvicorn walkthrough_api.main:app --host
127.0.0.1 --port <p> [--reload --reload-dir services/api/walkthrough_api]` and sets `WALKTHROUGH_DATA_DIR` (default
`data`) unless set; it refuses `--reload` on Windows (since 10 Nov 2026: uvicorn's restart there is a Ctrl+C to the
whole terminal, which stops `run-api.mjs` too: docs/upload/contract-issues/UI.md, UI-5). Scripts that read prototype Python (the CSV goldens, the provisional fixtures, the prototype tests at
integration) run with the **system** Python 3.14.3 and `-B`: `furniture/furniture_kit.py` imports shapely, which the
venv does not have.

## 3. Ports

The prototype tests use 9333, 9344, 9366, 9377, 9411, 9419 and 9421; nothing here uses 93xx-94xx. Every test that
launches a browser or a server first checks that its port is free and stops with a message if not (as the prototypes do).
**Every server binds 127.0.0.1** (Vite `server.host` and `preview.host` = `'127.0.0.1'` in every Vite config, uvicorn
`--host 127.0.0.1`), and every URL, Playwright `baseURL` / `webServer.url` and port check uses `127.0.0.1`: on this machine
Vite's default host `localhost` listens on `[::1]` only (seen 3 Nov), so a 127.0.0.1 client gets "connection refused" and a
127.0.0.1 bind test wrongly reports the port free.

| Who | Web dev / harness | API | Preview / static | Browser debug (CDP) | Temp folder |
|---|---|---|---|---|---|
| `npm run dev`, `preview` (owner, integration) | 5710 | 8710 | 4710 | - | - |
| Playwright e2e (integration) | 5711 (web dev) | 8711 (temp data copy) | 4711 | - (Playwright pipes) | `%TEMP%\wt-e2e` |
| Scaffold | 5700 | 8700 | 4700 | 9700 (capture tool) | `%TEMP%\wt-scaffold` |
| A viewer core | 5721 | - | 4721 | 9721 | `%TEMP%\wt-a` |
| B modes | 5722 | - | 4722 | 9722 | `%TEMP%\wt-b` |
| C furniture + UI | 5723 | - | 4723 | 9723 | `%TEMP%\wt-c` |
| D replay | 5724 | - | 4724 | 9724 | `%TEMP%\wt-d` |
| E API, store, seed | - | 8725 | - | 9725 | `%TEMP%\wt-e` |
| F web app | 5726 | 8726 (mock API) | 4726 | 9726 | `%TEMP%\wt-f` |

Playwright configs take `WT_WEB_PORT`, `WT_API_PORT`, `WT_TMP` from the environment so each builder runs its own copy;
every builder sets all three to its row above. Everything a run writes goes under `WT_TMP` (default `%TEMP%\wt-e2e`):
Playwright's `outputDir` (`<WT_TMP>/pw-results`, which Playwright empties when a run starts, so a shared folder would delete
another builder's downloads and traces mid-run), the reporters' files, saved downloads (`testInfo.outputPath()`), the temp
data copy, and the Vite dependency cache (`cacheDir: <WT_TMP>/vite-<config>` in the web and harness configs when `WT_TMP` is
set).

**One headless Edge at a time.** This machine is a 12th Gen i7-1255U laptop (10 cores, 15 W) with 15.7 GB, and headless Edge
draws with SwiftShader at 10 - 20 frames a second; the prototypes' timed checks already failed at 10 - 12 fps on a busy
machine. `tools/edge-lock.mjs` (scaffold) is a machine-wide lock, `%TEMP%\wt-edge.lock` (created with the `wx` flag; holds
the step name, pid and start time): Playwright's globalSetup takes it and globalTeardown releases it, and every CDP runner
(the capture tool, any harness runner built on `tools/cdp.mjs`) does the same. A waiting run prints who holds it and waits up
to 45 minutes; a lock whose pid is no longer alive is stale and taken over. vitest and pytest do not take it.

## 4. Frozen library list

Rule used: the newest stable version published at least two weeks before 3 Nov 2026 (on or before 20 Oct 2026, 01:00 UTC),
checked with `npm view <pkg> time peerDependencies engines` and the PyPI JSON API on 3 Nov. Node 24.14.1, npm 11.11.0,
Python 3.14.3. Exact versions everywhere (`.npmrc save-exact=true`; Python lock with every package pinned).
`app/CLAUDE.md` repeats this table; nothing is added, removed or upgraded without the owner.

### 4.1 npm, runtime

| Package | Version (date) | Where | Compatibility checked |
|---|---|---|---|
| three | 0.186.1 (2026-09-24) | viewer | 0.187.0 is 30 Oct (too new). Prototypes used 0.160.0: see risks |
| three-mesh-bvh | 0.9.16 (2026-10-08) | viewer | peer `three >= 0.159.0` |
| react, react-dom | 19.3.1 (2026-10-14) | web | react-dom peer `react ^19.3.1` |
| react-router | 8.5.0 (2026-10-19) | web | peer react / react-dom `>= 19.2.7`; engines node `>= 22.22.0`; data mode, `RouterProvider` from `react-router/dom` |
| @tanstack/react-query | 5.104.5 (2026-10-19) | web | peer react `^18 \|\| ^19` |
| radix-ui | 1.8.1 (2026-10-12) | web | the one Radix package shadcn's new-york components import (`import { Select } from "radix-ui"`); it pins its `@radix-ui/react-*` exactly |
| class-variance-authority | 0.7.1 (2024-11-26) | web | shadcn button / badge |
| cn | 0.5.0 (2026-10-16) | web | shadcn's class merger (`import { cn } from "cn"`, the registry's utils), engines node `>= 22` |
| lucide-react | 1.59.0 (2026-10-17) | web | shadcn select / dropdown icons; peer react `^19` |
| tailwindcss | 4.3.3 (2026-07-16) | web | 4.3.4 is 2 Nov |
| tw-animate-css | 1.4.0 (2025-09-24) | web | shadcn animations (`@import "tw-animate-css"`) |

### 4.2 npm, build and test

| Package | Version (date) | Compatibility checked |
|---|---|---|
| typescript | **6.0.3** (2026-04-16) | see 4.3 |
| vite | 8.3.4 (2026-10-08) | engines node `^20.19 \|\| >= 22.12`; 8.3.5 is 21 Oct |
| @vitejs/plugin-react | 6.1.2 (2026-10-05) | peer vite `^8.0.0` |
| vite-plugin-singlefile | 2.3.4 (2026-10-17) | peer vite `^8.0.0`; a throwaway build on 3 Nov with vite 8.3.4, three 0.186.1 and three-mesh-bvh 0.9.16 gave one 628 KB HTML, no external references, data markers intact |
| @tailwindcss/vite | 4.3.3 (2026-07-16) | peer vite `^8` |
| @types/three | 0.186.0 (2026-09-11) | matches three 0.186.x; `contracts.ts` type-checks with it (3 Nov) |
| @types/react, @types/react-dom | 19.3.0 (2026-09-09) | react-router peer `>= 19.2.0` |
| @types/node | 24.19.2 (2026-10-09) | Node 24 line |
| @hey-api/openapi-ts | 0.99.0 (2026-06-22) | peer typescript `>= 5.5.3`; engines node `>= 22.18`; the fetch client and the `@tanstack/react-query` plugin are bundled inside it (the separate `@hey-api/client-fetch` package is deprecated since 0.73: not used) |
| shadcn (CLI) | 4.22.1 (2026-10-18) | run by the scaffold only, to add components (style new-york, registry new-york-v4) |
| concurrently | 10.0.6 (2026-10-08) | engines node `>= 22` |
| vitest | 5.0.5 (2026-10-15) | peer vite `^8`; engines node `^24.0.0` |
| happy-dom | 21.0.3 (2026-10-15) | vitest DOM environment. Not jsdom: jsdom 30.1.3 needs node `^24.15.0`, we have 24.14.1 |
| @playwright/test | 1.64.1 (2026-10-14) | channel `msedge` (the installed Edge), no browser download |
| ajv | 8.20.0 (2026-04-24) | vitest: validates fixtures against `built-model.schema.json` (`ajv/dist/2020`) |

### 4.3 Why TypeScript 6.0.3 and not 7.0.2

TypeScript 7.0.2 (8 Jul 2026) is the native compiler: its npm package exports only a version string at `"."` and an
unstable API under `./unstable/*`, no compiler API. `@hey-api/openapi-ts` 0.99.0 does `import ts from "typescript"` and
builds its output with `ts.factory`; with 7.0.2 it crashes at once (`TypeError: Cannot read properties of undefined
(reading 'AnyKeyword')`, reproduced on 3 Nov), with 6.0.3 it generates the sdk, the types and the react-query options (also
reproduced; 6.0.3 is the version Hey API itself develops with). Vite and vitest do not use TypeScript at all (they strip
types), so 6.0.3, the newest JavaScript-based compiler, satisfies all three. Move to 7.x when Hey API supports it.

### 4.4 Compiler settings (`tsconfig.base.json`)

`target es2022`, `module esnext`, `moduleResolution bundler`, `lib [es2022, dom, dom.iterable]`, `strict`,
`noUncheckedIndexedAccess`, `noImplicitOverride`, `noFallthroughCasesInSwitch`, `verbatimModuleSyntax`, `isolatedModules`,
`skipLibCheck`, `noEmit`, `resolveJsonModule`, `types []`. TypeScript 6.0 changed three defaults (each reproduced with tsc
6.0.3 on 3 Nov): no `@types` package is included unless `types` lists it (TS2591 for `process`, TS2339 for
`import.meta.env`); a side-effect import of a file it cannot resolve is an error (TS2882 for `import './index.css'`); and
`baseUrl` is a hard error (TS5101). So every tsconfig is spelled out, with `paths` and no `baseUrl`:

| tsconfig | extends | include | types | adds |
|---|---|---|---|---|
| `packages/viewer/tsconfig.json` | base | `src` | `[]` (browser code sees no Node or Vite types) | - |
| `packages/viewer/tsconfig.test.json` | the one above | `src`, `test`, `vite.*.config.ts` | `["node"]` | - |
| `apps/web/tsconfig.json` | base | `src` | `["vite/client"]` (`import.meta.env`, the CSS import) | `jsx react-jsx`, `paths { "@/*": ["./src/*"] }` |
| `apps/web/tsconfig.test.json` | the one above | `src`, `test`, `vite.config.ts`, `openapi-ts.config.ts` | `["vite/client", "node"]` | - |
| `tests/e2e/tsconfig.json` | base | `**/*.ts` | `["node"]` | - |

The shadcn CLI writes `baseUrl` into the web tsconfig: the scaffold removes it again and keeps `paths`. A scaffold unit test
reads a fixture through `node:fs`, so the typecheck gate covers that case from the start.

### 4.5 PyPI (`services/api/requirements.lock.txt`, every package of the closure pinned)

| Package | Version (date) | Note |
|---|---|---|
| fastapi | 0.150.0 (2026-10-19) | released in a burst (0.142 - 0.162 between 7 and 23 Oct); fallback 0.142.4 (7 Oct) if the scaffold finds a fault |
| starlette | 1.9.0 (2026-10-18) | fastapi needs `>= 0.46.0` |
| pydantic / pydantic-core | 2.14.1 / 2.50.1 (2026-10-11) | cp314 win_amd64 wheel exists |
| uvicorn | 0.54.0 (2026-09-25) | plain, no `[standard]` (no watchfiles: `--reload` would use StatReload; unused since 10 Nov, section 2) |
| pytest | 9.1.1 (2026-06-19) | 9.2.0 is 27 Oct |
| httpx / httpcore | 0.28.1 / 1.0.9 | FastAPI's TestClient. Starlette 1.9 prefers httpx2 and warns: the warning is filtered in pytest config |
| jsonschema | 4.26.0 (2026-01-07) | runtime: the seed and the store validate every model against the schema |
| closure | click 8.5.0, h11 0.16.0, anyio 4.15.1, idna 3.20, typing-extensions 4.16.0, typing-inspection 0.4.4, annotated-types 0.8.0, annotated-doc 0.0.5, opentelemetry-api 1.45.1 (fastapi needs it), referencing 0.37.0, rpds-py 2026.9.1 (cp314 wheel), jsonschema-specifications 2025.9.1, attrs 26.1.0, certifi 2026.10.18, pluggy 1.7.0, iniconfig 2.3.1, packaging 26.3, pygments 2.21.0, colorama 0.4.6 | `pip check` clean on 3 Nov; `pip freeze` lists exactly these 28 |

---

## 5. BuiltModel v1

### 5.1 What it is

The format of `bank_test/src/bank_model.json` and `hotel_test/src/hotel_model.json`, which the bank and hotel pages and
their Max generators already read. Those two files, and the bank's 27 Oct model, are valid v1 **byte for byte** (checked on
3 Nov against `built-model.schema.json` and the cross-reference rules of 5.6), so their model-data stamps still pair with
their `.ms` scripts. The format has **no version field**; `version.json` says `modelFormat: "built-model/1"`.
Everything v1 adds is optional, and none of it changes what an existing field means:

| v1 extension | For | Meaning |
|---|---|---|
| part kinds `pane` | house | window panes (glass look, own colour) |
| part kinds `balustrade`, `low`, `builtin`, `deck`, `post` | suite | the suite's kinds (5.4) |
| `parts[].fit: 'top' \| 'clip'` | house | how a part answers a wall-height change (5.5) |
| `parts[].plinth: true` | house | a slab standing on the ground (5.5) |
| `stairs[floor].panels` | house | tread lines drawn as 0.15 m upright panels |
| `floors[].stack` | future | default `"main"` |
| `floors[].sheetShift` | house | where the floor's plan sits on its source sheet: sheet coordinates = model + `offset` + `sheetShift` (the house's upper floor `[74.021, 0]`); provenance for the next milestone's pipeline, not read by the viewer, the CSV or the Max script |

### 5.2 Frame and units

Metres. Plan coordinates are the model frame: drawing coordinates minus `offset` (the CSV and the Max script add it back);
the drawing coordinates meant are those of the shared grid the floors are lined up on (a floor drawn elsewhere on its sheet
records that in `sheetShift`).
three.js: plan (x, y) -> (x, z = -y); heights z0 / z1 above the level of the part's floor (`floors[].level`). A floor's
geometry is built at its model level inside its floor group; Build settings move the group (5.5, 11.5).

### 5.3 Fields

| Field | Type | Read by the viewer for |
|---|---|---|
| `project`, `shortName`, `projectNo` | strings | cards, CSV file name fallbacks (display only) |
| `source` | string[] | display |
| `units` | `"m"` | checked |
| `offset` | [x, y] | CSV `x_m, y_m` (drawing coordinates) |
| `photoName` | `[A-Za-z0-9_.-]{1,64}` | photo names, CSV file name, storage key |
| `maxPrefix` | `[A-Z]{2,4}` | (Max script only) |
| `floors[]` | key, name, level, wallHeight, slabThickness, stack?, sheetShift? | floor records, buttons, Build settings, Walk levels (`sheetShift`: not read) |
| `railingHeight`, `singleLineHeight`, `doorHeadDefault` | m | (legend texts are precomputed; kept for the Max script and the pipeline) |
| `pictureFrame{floor}` | file, size, pxPerMetreX/Y, originPx, yDown | plan picture sheets (5.7) |
| `parts[]` | floor, kind, z0, z1, follow, o, h, label?, fit?, plinth? | all solid geometry (5.4) |
| `stairs{floor}` | below, above, panels? (flat x1,y1,x2,y2) | stair lines (5.4, item 4) |
| `voids{floor}`, `closures{floor}`, `stairOutlines{floor}` | records | tests only (the holes are already in the slab parts) |
| `rooms[]` | floor, name, label, area, x, y | room labels |
| `openings[]` | id, floor, kind, x, y, nx, ny, width, + builder fields | tests, furniture approach ids, hover text |
| `probes[]` | glass spots | tests |
| `colliderSkins{floor}` | o, h, z0, z1, glass | invisible Walk colliders |
| `furnitureKinds[]`, `furniture[]` | furniture/README.md contract, unchanged | boxes, legend, CSV |

Per-floor maps (`stairs`, `voids`, `closures`, `stairOutlines`, `colliderSkins`, `pictureFrame`) may lack a floor: missing
means empty. Floor keys are `[A-Za-z0-9_]{1,32}` (replay captions use `\w`).

### 5.4 Part kinds and how each is drawn (`model/styles.ts` DEFAULT_PART_STYLES; `presentation.partStyles` overrides per project)

| kind | colour / edge | mesh group | material | collider | tick | default `follow` when a converter has to choose |
|---|---|---|---|---|---|---|
| wall, column, lintel | #e3ddd3 / #7f786e | `solid` | standard, roughness 0.85, DoubleSide | yes | - | true |
| sill | same | `sill` | same | yes | - | false |
| parapet | same | `parapet` | same | yes | - | false |
| glass | #9cc3d5 / #5f8fa6 | `glass` | standard, roughness 0.15, metalness 0, transparent, opacity 0.3, depthWrite false, DoubleSide, renderOrder 3; edges opacity 0.45 (house: #8fd0e0 / #4f9fb3, opacity 0.35, roughness 0.85, edge opacity 0.6, renderOrder 0) | yes | Glass | (per part) |
| pane | #9cc3d5 / #5f8fa6 (house: #7fb8e8 / #3f7fb3) | `pane` | as glass (house: opacity 0.35, roughness 0.85, edge opacity 0.6, renderOrder 0) | yes | Glass | (per part) |
| mullion | #5d6b74 / #3d474e | `mullion` | standard | yes | - | (per part) |
| railing | #6f6a75 / #4a4550 | `railing` | standard, roughness 0.6, metalness 0.2, transparent, opacity 0.5 (`see`), depthWrite false, DoubleSide, renderOrder 2 | yes | - | false |
| balustrade | #9cc3d5 / #5f8fa6 | `balustrade` | as glass | yes | Glass | false |
| single | #e0a458 / #a86f2c | `single` | standard (house: opacity 0.9) | yes | Single-line items | false |
| step | #b9c7b4 / #6f8a6a | `step` | standard | yes | - | false |
| low | #d2c6b2 / #8d8170 | `low` | standard | yes | - | false |
| builtin | #c9a77f / #8a6d4b | `builtin` | standard | yes | - | false (the suite's full-height panel: true) |
| deck | #b08a5c / #8a6a44 | `deck` | standard, polygonOffset -2 / -2 (every `collider: false` style: drawn in front of the plate it lies on; integration I-1) | **no** (walked over) | - | false |
| post | #6f6153 / #4a4038 | `post` | standard | yes | - | false |
| slab | #d4d8d2 | one mesh per slab part | **not** "standard": `MeshStandardMaterial({ color: 0xd4d8d2, roughness: 0.95, polygonOffset: true, polygonOffsetFactor: -1, polygonOffsetUnits: -1 })`, **FrontSide** (three's default, as on all four pages), computeVertexNormals, no edges | walkable (not a collider) | Floor plates | false |

"standard" = `MeshStandardMaterial({ color, roughness: 0.85, side: DoubleSide })`, transparent with `depthWrite false` when
`opacity < 1`; edges `LineBasicMaterial({ color: edge, transparent: true, opacity: edgeOpacity ?? (glass ? 0.45 : 0.6) })`.
`mesh.renderOrder` = the style's `renderOrder` (`PartStyle.renderOrder`; defaults: glass, pane and balustrade 3, railing 2,
the rest 0). The house page set no renderOrder, so its glass, panes and half-transparent single-line pieces were depth-sorted
together; its `partStyles` give glass and pane `renderOrder: 0` to keep that (section 8).

**Building a floor** (`core/build.ts`, owner A), exactly the bank page's code generalised:
1. Non-slab parts of the floor are grouped by `style.mesh + ':' + fitName` (fitName: `follow` for fit `scale`, `own` for
   `fixed`, `top`, `clip`). Each part: `Shape(o)` with `h` as holes, `ExtrudeGeometry({ depth: z1 - z0, bevelEnabled:
   false, curveSegments: 1 })`, `rotateX(-PI/2)`, `translate(0, modelLevel + z0, 0)`, attribute `aDelay` (one value per
   vertex: the sweep of 13 below). Merged (`mergeGeometries`), `toCreasedNormals(merged, creaseAngle)`, edges
   `EdgesGeometry(merged, creaseAngle)` (fitted groups: per-part EdgesGeometry, merged, so every edge vertex knows its
   part), BVH per mesh (`withBvh`). Mesh name `<floorKey> <mesh>:<fitName>`, edges `<floorKey> <mesh>:<fitName> edges`.
   Mesh + edges go in the floor group; the mesh into `colliders` unless `collider: false`; both into the tick lists; a
   RiseItem `{ mesh, edges, scales: fit === 'scale', fit }`. This one rule serves all four models; the bank and hotel pages
   grouped the same way, the suite and house pages did not (the house merged lintels with sills, all panes, and all plate
   rings of a floor): what that changes, and the old-to-new names the ported checks use, is in 17.2 and 17.4.
2. Collider skins: per floor, glass and non-glass skins merged into one invisible mesh each
   (`MeshBasicMaterial({ visible: false })`), names `<key> walk skins` / `<key> walk skins (glass)`; colliders; the glass
   one goes in the Glass tick list.
3. Slabs: one mesh each, name `<key> floor plate`, into `walkables`, `late`, the Floor plates tick; `plinth` slabs also
   into `plinths`.
4. Stairs (all `late`): `below` as strips 0.03 m wide lying at `level + 0.012` (`#3f8f4f`, DoubleSide, name `<key> tread
   lines`); `above` as `LineSegments` at `level + 0.02` (`#5aa65a`, opacity 0.35, `<key> stair lines above`); `panels` as
   quads from `level` to `level + 0.15` (`#5aa65a`, DoubleSide, `<key> stair panels`).
5. Ground plane (presentation.groundPlane): `PlaneGeometry(w, d)` at y = 0, `MeshStandardMaterial({ color })` (FrontSide),
   name `ground plane`, in the scene (not a floor group). In the replay it fades with the late objects, as the house page's
   `hide: [ground]` did: hidden on the Build settings screen and while the replay plays, faded in during the finish step,
   opaque after (D, via `BuiltScene.groundPlane`).

### 5.5 Wall height, level and fit

Build settings (the replay card) change a floor's level `L0 -> L` and wall height `H0 -> H` (`H0 = floors[].wallHeight`).
`core/heights.ts` (`HeightsApi.apply`, owner A) does, per floor, all of it (the replay never scales geometry itself):

| What | Rule (prototype source) |
|---|---|
| floor group | `group.position.y = L - L0` (build_replay.js applySettings) |
| Walk level | `FloorRecord.level = L` (each page's applySettings) |
| fit `scale` (`follow`, no `fit`) | mesh and edges: `scale.y = H / H0`, `position.y = L0 * (1 - H / H0)` (build_replay.js) |
| fit `fixed` | unchanged |
| fit `top` | per vertex: z0 stays, z1 -> H (`z' = z0 + (z - z0)(H - z0)/(z1 - z0)`); when `H <= z0 + 1e-6` every vertex goes to (part centre, H): the mesh vanishes (house fitPieces, lintels and panes that reach the top) |
| fit `clip` | `z' = min(z, H)`; collapses like `top` when `H <= z0 + 1e-6` (house fitPieces, sills and other panes) |
| plinth slab | `scale.y = max(0.01, L / L0)`, `position.y = L0 - L` (house applySettings) |
| plan picture of the floor | follows the group's y |

Fitted meshes keep per-vertex base positions, z0 / z1 and part centre (core/build) and refit `boundsTree` after a change.
The bank's lintels are `follow` without `fit`, so they scale as on the bank page; the house's keep their heads, as on the
house page: each model behaves as its page did (decision 18.21).

### 5.6 Parse rules (the viewer's `parseBuiltModel` and the API's `builtmodel.validate`: same rules, the API stricter)

Schema first (structure, types, enums, patterns), then: floor keys unique and floors in level order; every `floor`
reference (parts, rooms, openings, probes, furniture, per-floor map keys) names a floor; `z1 > z0`; `plinth` only on slabs;
flat segment arrays have a multiple of 4 values; opening ids unique; furniture ids unique; every `furniture.kind` is in
`furnitureKinds`; `on` names a piece; every `approach` id is an opening id; `furnitureKinds[].count` equals the pieces of the
kind. Issue paths are JSON Pointers (`/parts/12/z1`), the same in all three checkers.

* **API** (`walkthrough_api.builtmodel.validate`, jsonschema + the rules): refuses on any issue; the seed fails loudly.
* **Viewer** (`parseBuiltModel`): **hand-written TypeScript** that mirrors the schema; no validator library at run time
  (ajv is a test-only dependency, and it compiles validators with `new Function`, which a strict Content-Security-Policy
  forbids). It throws `ModelError` (every issue listed) for any schema failure and any rule outside the furniture. The four
  furniture rules only warn (`console.warn('[viewer] model: <path>: <message>')`), and the furniture code (`installFurniture`,
  `furnitureCsv`) then does what `furniture_boxes.js` did: a piece whose kind or floor is unknown is left out; a piece whose
  `on` names no piece stands on its kind's base; approach ids that are not openings are kept as they are (the Keep doorways
  rule uses the list); a kind's `count` is ignored and the legend counts the pieces. The real models break none of these
  rules (0 issues each, 3 Nov); the leniency is for hand-made and older files.
* **Agreement:** every file of the shared corpus `fixtures/models/broken/` (17.1) must be rejected by `builtmodel.validate`
  and by `parseBuiltModel` (the four furniture cases: warned about instead), and the schema cases also by ajv, each at the
  path its manifest names.

### 5.7 Plan pictures (hotel)

`pictureFrame[floor]`: the picture lies flat `0.005 m` above the floor level, the whole sheet at the model's scale:
pixel `px = originPx[0] + pxPerMetreX * (x + offset[0])`, `py = originPx[1] - pxPerMetreY * (y + offset[1])`; the sheet is
`size[0] / pxPerMetreX` by `size[1] / pxPerMetreY` m, centred at `cx = (W/2 - ox)/kx - offset[0]`,
`cy = -(H/2 - oy)/ky - offset[1]`. `PlaneGeometry(w, h).rotateX(-PI/2).translate(cx, level + 0.005, -cy)`,
`MeshBasicMaterial({ map, polygonOffset: true, polygonOffsetFactor: -2, polygonOffsetUnits: -2 })`, texture `SRGBColorSpace`,
max anisotropy, name `<key> plan picture`, `userData { key, size, metres, centre }`. In a scene-level group `plan pictures`
(not the floor group: Walk, the boxes, the double-click and the room labels never see it). Visible = Picture tick and its
floor group visible (checked every frame). The image comes from `ViewerProject.pictures[floor]` (a URL in the app, a
`data:` URL in the offline file); `model.pictureFrame[].file` is only the builder's name for it.

---

## 6. Conversions to v1 (`walkthrough_api/seed/convert_*.py`, owner E)

The seed reads the prototypes and never writes there. A throwaway implementation of 6.3 and 6.4 validated against the
schema and 5.6 on 3 Nov (counts in 6.5).

### 6.1 Bank (both versions) and 6.2 hotel: copied byte for byte

`model.json` = the source file's bytes. Test: `sha1(model.json) == sha1(source)`, and the stamp in line 2 of the `.ms`
(`(model data <12 hex>)`) equals `sha1[:12]`.

### 6.3 Presidential suite (`presidential_test/src/pres2_model.json` -> v1)

| v1 field | From |
|---|---|
| project, shortName | `"Presidential suite"` (the page's heading and title) |
| projectNo | null |
| source | `[M.source]` |
| units, offset | as is |
| photoName | `"Presidential"` (the page's `project` for photos, CSV and storage) |
| maxPrefix | `"PS"` (the Max script's prefix) |
| floors | `[{ key: "suite", name: "Suite (FL-01)", level: M.level, wallHeight: M.floorToFloor, slabThickness: M.slabThickness }]` |
| railingHeight | `M.balustradeHeight` (1.1); singleLineHeight 1.0; doorHeadDefault `M.doorHead` (2.1) |
| parts | each part + `floor: "suite"`; `follow` = the part's own `follow` if it has one, else by kind: wall, column, lintel, glass true; low, builtin, balustrade, deck, post, slab false (the page's KIND table); keep `label` |
| rooms | + `floor: "suite"`; `area` = float of the string (`"153"` -> 153.0), null when empty |
| openings | from `doors`: `{ id, floor: "suite", kind: id starts with "D" ? "door" : "passage", label: name, x, y, nx, ny, width }` + `exterior: true` where set (furniture `approach` lists use these codes) |
| probes | `[{ floor: "suite", id: "suite-glass-west", what: "glass facade", x: probe.glassWestX, y: probe.glassWestY, nx: 1, ny: 0, inside: [1], label: "the living room's west glass (its room-side face)" }]` (the page walked from 1 m east of that face, westwards) |
| stairs, voids, closures, stairOutlines, colliderSkins | `{ suite: empty }` |
| furnitureKinds, furniture | as is (floor already `suite`) |

Stamp: the `.ms` was made from `pres2_model.json`, so `version.stamp = sha1(source/pres2_model.json)[:12]` =
`f1b95c53eb3d`, `stampSource = "source/pres2_model.json"`; `modelSha1` is the converted file's.

### 6.4 Sukhumvit house (`cad_test/src/house3d_merged.json` + `furniture_house.json` -> v1)

The page reads only these two and `house3d_stages.json`; `heights.json` and `openings.json` are already folded into
`house3d_merged.json` (openings, pieces, heights) and are copied to `source/` for the record.

| v1 field | From |
|---|---|
| project `"Test Sukhumvit Residence"`, shortName `"Sukhumvit house"`, projectNo null, source `["Test Sukhumvit Residence.dwg"]`, photoName `"Sukhumvit"`, maxPrefix `"SK"` | the page |
| offset | `furniture_house.offset` (= `house3d_merged.centre`; assert equal) |
| floors | order and names from `furniture_house.floors`; `level = levels[k]`; `wallHeight = round(tops[k] - levels[k], 6)` (3.9, 3.5); slabThickness: lowest floor `levels[k]` (the plinth), others 0.25; `sheetShift = [round(-frame.shift[k], 6), 0]` where the shift is not 0 (upper `[74.021, 0]`: `furniture_house.frame` says model = drawing + shift - centre, and `centre` = `offset`) |
| railingHeight, singleLineHeight | 1.0, 1.0 (the page's single lines are 1.0 m) |
| doorHeadDefault | `heights.defaults[lowest].doorHead` (3.0) |
| parts from `solids["<floor>:<kind>"]` | per ring: `{ floor, kind, z0: 0, z1, follow, o, h }` with wall `z1 = H0`, follow true; glass `z1 = round(H0 - 0.6, 6)`, follow true; single `z1 = 1.0`, follow false |
| parts from `pieces[floor]` | `{ floor, kind, z0, z1, follow, o, h, label: id, fit }`: lintel follow true fit `top`; pane with `top` follow true fit `top`; other panes and sills follow false fit `clip` |
| parts from `plates[floor]` | `{ floor, kind: "slab", z0: round(-thick, 6), z1: 0, follow: false, o, h }`, thick = `levels[k]` on the lowest floor (+ `plinth: true`), else 0.25 |
| stairs | `{ below: [], above: [], panels: flat(stairs[floor]) }` |
| openings | flatten `openings[floor]`, add `floor`; `lintel: true -> "lintel"`, `false -> null`; keep every other field (a, b, glazed, hinge, swing, floorSide, leaves, depth, cut, jambGap, pane, corner ...) |
| rooms, probes | `[]` (no room names in this DWG; windows are tested from `openings`) |
| voids, closures, stairOutlines, colliderSkins | `{ ground: [], upper: [] }` |
| furnitureKinds, furniture | `furniture_house.json` as is |
| not carried (all kept in `source/`) | `house3d_merged.removed` (pieces the cut took away: not shown), `house3d_merged.heights`, `furniture_house.frame` (its `centre` is `offset`, its `shift` is `sheetShift`), `furniture_house.furnitureReport` (how the furniture was read) |

Stamp: no Max script; `stamp = sha1(model.json)[:12]`, `stampSource = "model.json"`.
Presentation extras for the house (section 8): `creaseAngle 40`, `partStyles` glass / pane / single, the ground plane,
the floor button labels.

### 6.5 Conversion checks (pytest, E)

| Version | floors | parts | openings | probes | rooms | furniture (kinds) | stamp |
|---|---|---|---|---|---|---|---|
| bank-sampeng v1 (27 Oct) | 2 | 124 | 55 | 19 | 18 | 0 | 4b02dc17f286 |
| bank-sampeng v2 (29 Oct) | 2 | 124 | 49 | 19 | 18 | 185 (14) | c3a9408304a2 |
| presidential-suite v1 | 1 | 62 | 22 | 1 | 16 | 120 (13) | f1b95c53eb3d |
| sukhumvit-house v1 | 2 | 197 (87 solids + 106 pieces + 4 plates) | 86 | 0 | 0 | 76 (9) | sha1 of model.json |
| hotel-lobby v1 | 2 | 89 | 20 | 9 | 24 | 159 (8) | 6ab030750886 |

Plus: every model validates (schema + 5.6); bank and hotel byte-identical to the source; the house's slab outlines equal
`house3d_merged.json` plates exactly (the prototype test's plates fingerprint); every source ring appears exactly once in the
converted parts with the same points; the furniture CSV made from the converted model with no saved heights equals the
prototype's `<project>_furniture_list.csv` byte for byte (BOM included) for all four furnished versions (checked on 3 Nov
with the contract's reference writer `furniture/fixtures/expected_csv.py` on the provisional models: equal). The converted
suite and house equal `fixtures/models/suite.model.json` and `house.model.json` (the architect's provisional conversion,
`docs/reference/provisional_v1.py`, 17.1) as parsed JSON; a difference goes to `docs/contract-issues/E.md` and the
integration step settles which side is right.

---

## 7. Replay data v1 (`versions/<n>/stages.json`, optional; absent = no build replay, as the hotel)

### 7.1 Format

`contracts.ts` ReplayData: `source`, `intro[]` (the settings card's facts), `layers[[label, detail]]`,
`floors{key: { sheet, lines{cat: flat}, pieces{kind: flat quads}, rings{kind: [{o, h}]} }}`, `captions{step: template}`,
`stats?`, `panelIntro?` (legacy, unused) and the optional `introTitle`, `layersTitle`, `stepTitles`, `colors`.
`bank_stages.json` (both versions) is valid v1 as it is and is copied byte for byte.

### 7.2 Defaults (the bank page's values: the bank is the first model built with no drawing-specific rules)

`introTitle` = `source.files.join(' + ')`, else `source.file`, else `''`. `layersTitle` = `'How the drawing was read'`.
`stepTitles` = read `Read the drawing`, sort `Sort the layers`, align `Line up the levels`, pair `Find the wall faces`,
merge `Merge, cut the openings`, raise `Raise the walls`, finish `Floors, stairs, room names`.
`colors` = wall `#7a6650`, glass `#2f86a8`, door `#c0702a`, stair `#2e8b47`, railing `#9b3fa0`; and the replay's own
ink `#3b4148`, faint `#a4acb4`, piece `#cfc2b0`, pieceEdge `#8a7a66`, run `#e3ddd3`, runEdge `#6f675d`.

### 7.3 Caption placeholders

`{<key>level}` and `{<key>height}` -> the Build setting `toFixed(2)`; `{<key>level+}` -> the same with a `+` in front when
`>= 0` (the house's `lv()`). Regex `/\{(\w+?)(level|height)(\+)?\}/g`; an unknown key is left as written (bank page `fill`).

### 7.4 Conversions (`walkthrough_api/seed/stages.py`, E)

| | bank v1, v2 | suite | house |
|---|---|---|---|
| file | copied | `floor` -> `floors.suite`; `{level}` -> `{suitelevel}`, `{height}` -> `{suiteheight}`; rest as is | built from `house3d_stages.json`, the model and the page's code (below) |
| stepTitles | default | Read the drawing / Sort the line work / Check the floor / Find the wall faces / Merge into wall runs / Raise the walls / Slab and room names | Read the drawing / Sort the layers / Line up the floors / Pair the wall faces / Merge into wall runs / Raise the walls / Floors, stairs, done |
| colors | default | wall #7a6650, glass #3f8fb0, door #c0702a, railing #9b3fa0 | wall #7a6650, glass #2f86a8, window #4a9cc0, stair #2e8b47, door #c0702a |
| layersTitle | default | default | `Layers found` |

House, as `make_html_cad_merged.py` does at generation and in its page script: `lines` rounded to 2 decimals (Python
`round`), `noise` cut to its first 6,000 lines (24,000 numbers); `pairs` (rounded) become `pieces`; `rings.wall` =
the model's `solids["<k>:wall"]`, `rings.glass` = `solids["<k>:glass"]` + the panes `{o, h}`; `layers` from `stats.layers`
with `layer_list()`; `source.layersUsed = stats.planLayers`; `intro` = the three facts of the page; `captions` = the page's
seven caption functions rendered once with the stats (JS number formatting: `fmt` = round half up then thousands commas,
`pct` = round half up of x*100 + `%`, `toFixed` = round half up on the exact decimal value) and the settings left as
placeholders: `ground {groundlevel+} m, upper {upperlevel+} m`, `ground floor {groundheight} m, upper floor
{upperheight} m`. **Oracle:** with the default settings filled in, every caption, fact, layer row and step title equals,
character for character, what the prototype page shows (`fixtures/prototype/sukhumvit-house.json`, section 17.1); same for
the bank and the suite.

---

## 8. Presentation v1 (`version.json -> presentation`)

The page-level things the four generators wrote into their HTML, as data. The viewer has **no per-project code**; the seed
computes these by porting each generator's Python (`walkthrough_api/seed/presentation.py`, E); the next milestone's
pipeline writes them for new uploads. Types: `contracts.ts` Presentation; `parsePresentation` fills defaults.

| Field | Default | bank v1, v2 | suite | house | hotel |
|---|---|---|---|---|---|
| documentTitle | - | `Bank branch test` | `Presidential suite test` | `CAD to 3D test` | `Hotel test` |
| heading | - | `Bangkok Bank, Sampeng Branch (test): CAD → 3D` | `Presidential suite (test): CAD → 3D` | `Test Sukhumvit Residence: CAD → 3D` | `Hotel (test): two pictures → 3D` |
| intro (runs) | - | `stages.panelIntro`, `<b>` -> bold runs | same | `Built automatically from the DWG. Each wall's two face lines are paired, filled and merged into one solid per wall run, so there are no seams. ` + the generator's intro + ` No AI used.` | the generator's `intro` |
| accent | `#2f6f8f` | `#2f6f8f` | `#8a6d3b` | `#c9773e` | `#2f6f8f` |
| legend | - | inline, `make_html.py` legend_items | inline, its legend_items | inline: Walls and lintels #e3ddd3, Glass walls #8fd0e0, Window glass #7fb8e8, Stairs #5aa65a, Single line: wall, railing or edge? #e0a458, Floor plate (approximate outline) #d4d8d2 (no-openings variant: Walls / Windows / glass) | lines, its legend_items |
| floorButtons | all `Both floors`, labels = floor names | all `Both levels` | (one floor: no row) | all `Both floors`, labels ground `Ground`, upper `Upper` | all `Both floors` |
| labels | plates `Floor plates`, glass `Glass`, rooms `Room names`, single `Single-line items`, picture `Plan picture`, pictureTitle `Each floor's source picture, laid on its floor plate at the model's scale and position` | default | plates `Floor slab` | default | default |
| camera | - | fixed (24, 27, 29) -> (0, 2.5, 0), far 600 | fixed (-26, 32, 30) -> (0, 1.2, 0), far 600 | fixed (-28, 30, 34) -> (0, 3, 0), far 500 | fitSlabs away (21.6, 22.05, 26.1), targetY 2.5, panForPanel, far 600 |
| creaseAngle | 25 | 25 | 25 | 40 | 25 |
| partStyles | - | - | - | glass `{ color #8fd0e0, edge #4f9fb3, opacity 0.35, roughness 0.85, edgeOpacity 0.6, renderOrder 0 }`, pane `{ color #7fb8e8, edge #3f7fb3, opacity 0.35, roughness 0.85, edgeOpacity 0.6, renderOrder 0 }`, single `{ opacity 0.9 }` | - |
| groundPlane | null | null | null | `{ size: [80, 50], colour: #dfe3e0 }` | null |
| toggles | all on, picture off | default | default | default | picture off (`?picture=1` turns it on) |

Intro runs: the stages' `panelIntro` is HTML with only `<b>…</b>`; the seed splits it into `{ text, bold }` runs and fails
on any other tag or entity it does not decode. The viewer inserts every run with `textContent` (bold runs in `<b>`).
**Oracle:** for each version, heading, intro text, legend colours and texts, floor buttons, ticks and their labels, the
camera start and the title equal the prototype page's (`fixtures/prototype/<project>[-v<n>].json`). Ticks shown: Floor
plates and Glass always; Room names when the model has rooms; Single-line items when it has `single` parts; Plan picture
when a floor has a picture.

---

## 9. Store and seed

### 9.1 Layout (`app/data`, or `WALKTHROUGH_DATA_DIR`)

```
data/
  projects/
    <projectId>/                         ^[a-z0-9][a-z0-9-]{1,62}$
      meta.json                          ProjectMeta (contracts.ts 4)
      versions/
        <n>/                             1, 2, ... (immutable once written, except overrides.json)
          version.json                   VersionMeta (metadata + presentation)
          model.json                     BuiltModel v1
          stages.json                    ReplayData v1 (optional)
          overrides.json                 HeightOverridesFile (absent until heights are saved)
          project-data.json              reserved, not written in this milestone: the plan's "project.json" (3.2), the
                                         editable source of truth (wall segments keyed to DXF handles, staff fixes)
          assets/                        topview.png (thumbnail), plan pictures (byte-identical copies)
          downloads/                     the Max script (byte-identical), the prototype's furniture CSV (reference copy)
          source/                        the prototype files read for this version (byte-identical, provenance)
  mappings/                              reserved: per-office layer mappings (plan 3.1, "remembered per author"); next milestone
  .staging/                              reserved: uploads and drafts in progress (9.5); next milestone
```

The project's metadata file is `meta.json`, not `project.json`, so that name stays free for the plan's project data.
JSON files are UTF-8 without BOM; the seed writes the files it makes with `json.dumps(..., ensure_ascii=False,
separators=(',', ':'))` + `\n` (models, stages) or `indent=2` + `\n` (meta.json, version.json, overrides.json).
Writes are atomic (temp file in the same folder, then `os.replace`).

### 9.2 Seed table (`python -m walkthrough_api.seed --prototypes <project folder> --data <dir> [--force] [--reset-overrides]`)

| project / v | label | from | model.json | stages.json | assets | downloads | source/ |
|---|---|---|---|---|---|---|---|
| bank-sampeng / 1 | `27 Oct 2026: two levels, openings from the detector (before the fix round)` | `bank_test/previous_before_fix_round_2026-10-27/` | `src/bank_model.json` copied | `src/bank_stages.json` copied | `bank_topview.png` -> `topview.png` | `Bangkok_Bank_Sampeng.ms` | `src/bank_summary.json`, `README.md` |
| bank-sampeng / 2 | `29 Oct 2026: furniture boxes` | `bank_test/` | `src/bank_model.json` copied | `src/bank_stages.json` copied | `bank_topview.png` -> `topview.png` | `Bangkok_Bank_Sampeng.ms`, `bank_furniture_list.csv` | `src/bank_project.json`, `src/bank_summary.json`, `README.md` |
| presidential-suite / 1 | `29 Oct 2026: furniture boxes` | `presidential_test/` | converted (6.3) | converted (7.4) | `presidential_topview.png` -> `topview.png` | `Presidential_Suite.ms`, `presidential_furniture_list.csv` | `src/pres2_model.json`, `src/pres2_stages.json`, `src/furniture.json`, `src/floor_spec.json`, `README.md` |
| sukhumvit-house / 1 | `29 Oct 2026: openings and furniture boxes` | `cad_test/` | converted (6.4) | converted (7.4) | none (no top view: the card shows a placeholder) | `house_furniture_list.csv` | `src/house3d_merged.json`, `src/furniture_house.json`, `src/house3d_stages.json`, `src/heights.json`, `src/openings.json`, `OPENINGS_CHANGES.md` |
| hotel-lobby / 1 | `2 Nov 2026: read from two plan pictures` | `hotel_test/` | `src/hotel_model.json` copied (floor 2's furniture stays as drawn: the owner, 3 Nov) | none (no replay) | `source/floor1_plan.png` (plan-picture F1, modelRef `../source/floor1_plan.png`), `source/floor2_plan.png` (F2), `hotel_topview.png` -> `topview.png` | `Hotel_Lobby.ms`, `hotel_furniture_list.csv` | `src/hotel_project.json`, `src/hotel_summary.json`, `src/picture_readings.json`, `src/takeoff.json`, `README.md` |

`meta.json`: name = the v1 model's `project`, shortName, projectNo, sourceKind (`cad`, hotel `pictures`), createdAt =
the first version's, updatedAt = the latest version's createdAt (or a later overrides save), latestVersion, versions.
`version.json`: createdAt = the mtime of the version's model source file (UTC, seconds); sourceFiles = model `source`;
counts; floors; hasStages; assets with media type, bytes, sha1; downloads `{ maxScript: file name or null, furnitureCsv:
model has furniture }`; presentation (8); `seed { from: [prototype paths read], seededAt, seedVersion }`. `--force`
rebuilds every version folder but keeps each `overrides.json` (unless `--reset-overrides`); without `--force` an existing
version is left alone. The seed validates every model (5.6) and replay file and fails loudly.

### 9.3 Storage interface (`walkthrough_api/store/base.py`; routes use only this)

Routes get the store from a dependency, `store: Store = Depends(get_store)` (`walkthrough_api/deps.py`; today it returns the
app's one `LocalStore` from `app.state`), never from a module global, so a request-scoped store that carries the caller's
token (Supabase row-level security, decision H) can replace it later without touching a route. Store methods are
synchronous and **every route function is a plain `def`** (never `async def`): FastAPI runs plain routes in its threadpool,
so a network-backed store does not block the event loop.

```python
class Store(Protocol):
    def list_projects(self) -> list[ProjectMeta]: ...
    def get_project(self, project_id: str) -> ProjectMeta: ...                       # NotFound('project_not_found')
    def list_versions(self, project_id: str) -> list[VersionMeta]: ...
    def get_version(self, project_id: str, n: int) -> VersionMeta: ...                # NotFound('version_not_found')
    def read_json_bytes(self, project_id: str, n: int, name: Literal['model.json', 'stages.json']) -> bytes: ...  # NotFound('no_stages')
    def asset(self, project_id: str, n: int, name: str) -> BlobRef: ...              # NotFound('asset_not_found')
    def download(self, project_id: str, n: int, name: str) -> BlobRef: ...
    def read_overrides(self, project_id: str, n: int) -> HeightOverridesFile | None: ...
    def write_overrides(self, project_id: str, n: int, heights: dict[str, int]) -> HeightOverridesFile: ...  # revision + 1, atomic
    # next milestone (implemented by LocalStore now, not routed yet)
    def create_project(self, meta: NewProject) -> ProjectMeta: ...
    def stage(self, name: str, chunks: Iterable[bytes]) -> StagedRef: ...           # writes data/.staging/<key>, streamed
    def create_version(self, project_id: str, draft: VersionDraft) -> VersionMeta: ...

@dataclass(frozen=True)
class BlobRef:
    media_type: str; size: int; sha1: str
    path: Path | None = None          # local store: served with FileResponse
    url: str | None = None            # object store later: a short-lived signed URL, served as a 307 redirect
```

`LocalStore(root)` reads the files of 9.1 (meta and version JSON parsed into pydantic models, cached by mtime).
Asset and download names must match `^[A-Za-z0-9._-]+$` (no paths). Replacing it with Supabase + R2 later means a
`SupabaseR2Store` with the same methods: projects and versions as rows (the JSON of `meta.json` / `version.json`),
the files as R2 objects under `projects/<id>/versions/<n>/...`, `BlobRef.url` signed links; no route changes.

### 9.4 Saved heights

`overrides.json` holds only the kinds whose height differs from the model's (`heights{kind: whole mm}`), `revision` (+1 per
save) and `updatedAt`. The CSV download and the offline HTML use them; the viewer starts from them (11.2).

### 9.5 How the next milestone adds a version

Upload -> isolated DWG->DXF step -> the bank's builder made general -> check-and-fix screen -> the pipeline writes a draft:
`VersionDraft { label, source_kind, source_files, model_json: BlobSource, stages_json: BlobSource | None, presentation,
assets: {name: BlobSource}, downloads: {name: BlobSource}, source: {name: BlobSource}, carry_overrides_from: int | None }`
with `BlobSource = bytes | StagedRef(key)`: small files may come as bytes, while a large upload (interior sets reach 100 MB+,
over Cloud Run's 32 MiB request limit, plan 3.5) is written once by the browser straight to the store's staging area
(`data/.staging/<key>` locally, a private R2 prefix later) and the draft only names it, so it never passes through memory or
a request body. `Store.create_version` validates the model (5.6), allocates `n = latestVersion + 1`, writes or moves
everything into `versions/.staging-<uuid>/`, renames it to `versions/<n>/` (atomic), copies the previous version's saved
heights for the kinds the new model still has (when asked), then updates `meta.json` (latestVersion, versions, updatedAt)
last. Versions are never edited in place; a fix is a new version. The Max script is then generated from the model by the
pipeline (the three generators made one), so its stamp is `sha1(model.json)[:12]` from then on. The background build job
(Cloud Run Jobs later) is what writes the draft; `create_version` is its last step, not a request handler.

---

## 10. REST API (`services/api`, FastAPI 0.150.0, owner E; the scaffold freezes the routes and models)

### 10.1 Conventions

JSON is camelCase (pydantic `alias_generator=to_camel`, `populate_by_name=True`, `serialize_by_alias=True`). Every route has
an explicit `operation_id` (the client's function names) and, from the scaffold, an explicit `summary=`, `description=` and
`response_description=`: FastAPI otherwise copies the function name and docstring into the OpenAPI document (checked with
FastAPI 0.150.0 on 3 Nov: a docstring or a renamed handler changes `openapi.json`), and the committed `openapi.json` must not
move while E writes the bodies. Route functions are plain `def` and take the store through `Depends(get_store)` (9.3).
Domain errors: HTTP status + `{ "error": { "code", "message",
"details"? } }` (`ErrorResponse`, declared in each route's `responses` so the client types them). Malformed requests get
FastAPI's own 422 (`HTTPValidationError`). Path params: `projectId` `^[a-z0-9][a-z0-9-]{1,62}$`, `version` int >= 1,
`name` `^[A-Za-z0-9._-]{1,128}$`. Raw files (model, stages, assets) are returned as stored, `ETag: "<sha1>"`,
`Cache-Control: no-cache`, `If-None-Match` -> 304.

### 10.2 Routes

| Method, path | operationId | Response | Errors |
|---|---|---|---|
| GET `/api/health` | `health` | `Health { status: "ok", apiVersion, projects }` | - |
| GET `/api/projects` | `listProjects` | `ProjectList { projects: ProjectSummary[] }` sorted by updatedAt, newest first | - |
| GET `/api/projects/{projectId}` | `getProject` | `ProjectDetail` | 404 project_not_found |
| GET `/api/projects/{projectId}/thumbnail` | `getThumbnail` | the latest version's `topview.png` (image/png) | 404 no_thumbnail |
| GET `/api/projects/{projectId}/versions/{version}` | `getVersion` | `VersionDetail` | 404 project_not_found, version_not_found |
| GET `.../versions/{version}/model` | `getModel` | `model.json` bytes, application/json, header `X-Model-Stamp` | 404 |
| GET `.../versions/{version}/stages` | `getStages` | `stages.json` bytes | 404 no_stages |
| GET `.../versions/{version}/assets/{name}` | `getAsset` | the file (media type from version.json) | 404 asset_not_found |
| GET `.../versions/{version}/downloads/max-script` | `downloadMaxScript` | the `.ms`, `text/plain; charset=utf-8`, attachment `<file>_v<n>.ms` (the stored file's name with the version: fix step, I.md) | 404 no_max_script |
| GET `.../versions/{version}/downloads/furniture-csv` | `downloadFurnitureCsv` | BOM + CSV with the saved heights, `text/csv; charset=utf-8`, attachment `<photoName>_furniture_list.csv` | 404 no_furniture |
| GET `.../versions/{version}/downloads/offline-html` | `downloadOfflineHtml` | the offline single HTML with the saved heights (section 16), `text/html; charset=utf-8`, attachment `<projectId>-v<n>.html` | 503 offline_template_missing (`npm run build:offline:template`) |
| GET `.../versions/{version}/furniture-heights` | `getFurnitureHeights` | `HeightOverrides { heights, revision, updatedAt }` (`{}` / 0 / null when none) | 404 no_furniture |
| PUT `.../versions/{version}/furniture-heights` | `putFurnitureHeights` | body `HeightsUpdate { heights: {kind: int} }` -> `HeightOverrides` | 404 no_furniture; 422 invalid_heights (`details.unknownKinds`, `details.outOfRange`) |

PUT semantics: replaces the saved map; every key must be a kind of the model, every value an integer 10 - 5000; values equal
to the model's height are dropped (canonical); `revision` + 1; last write wins without If-Match. With `If-Match: "<revision>"`
(the staff app always sends it) the map is saved only while the saved heights are at that revision (0: none), else 412
`revision_conflict` with `details: { revision, heights, updatedAt }` (what is saved now); the header is read in the route
body, so `openapi.json` did not move (fix step, `docs/contract-issues/I.md`).
Attachment headers: `Content-Disposition: attachment; filename="<ascii>"; filename*=UTF-8''<encoded>`.

### 10.3 Models (pydantic, `walkthrough_api/models.py`)

`FloorInfo { key, name, level }`; `ProjectSummary { id, name, shortName, projectNo, sourceKind, floors, furnitureCount,
openingsCount, stamp, latestVersion, versionCount, createdAt, updatedAt, thumbnailUrl: str | None, url }` (counts and stamp
of the latest version; `url` = `/api/projects/<id>`); `ProjectDetail = ProjectSummary + { versions: VersionSummary[] }`;
`VersionSummary { version, label, createdAt, stamp, sourceKind, counts: VersionCounts, hasStages, hasMaxScript,
hasFurniture, url }`; `VersionDetail = VersionSummary + { projectId, modelSha1, stampSource, floors, urls: { model, stages:
str | None }, assets: AssetInfo[], downloads: { maxScript: DownloadInfo | None, furnitureCsv: DownloadInfo | None,
offlineHtml: DownloadInfo }, presentation: dict[str, Any], overrides: HeightOverrides }`;
`AssetInfo { name, role, floor, mediaType, bytes, sha1, url }`; `DownloadInfo { url, fileName, mediaType }`;
`HeightOverrides { heights: dict[str, int], revision: int, updatedAt: str | None }`; `HeightsUpdate { heights: dict[str,
int] }`; `ErrorResponse { error: { code, message, details: dict | None } }`; `Health { status, apiVersion, projects }`.
`presentation` is a plain JSON object in the OpenAPI: the viewer owns its type and `parsePresentation` checks it.
All URLs in responses are root-relative (`/api/...`); the web app never builds API paths itself.

### 10.4 CORS and the dev server

The web app calls `/api/...` on its own origin; Vite's dev server and `vite preview` proxy `/api` to the API (no CORS
needed). The API also allows `WALKTHROUGH_CORS_ORIGINS` (default `http://localhost:5710, http://127.0.0.1:5710,
http://localhost:4710, http://127.0.0.1:4710`; methods GET, PUT; headers content-type; exposed etag, x-model-stamp,
content-disposition) for tools and a client on another port.

### 10.5 Typed client (Hey API)

`npm run gen:api`: `walkthrough_api.openapi_export` writes `create_app().openapi()` to `apps/web/openapi.json` (sorted keys,
indent 2, no server needed), then, with `apps/web` as the working folder, `openapi-ts -f openapi-ts.config.ts` with `input
./openapi.json`, `output ./src/api/generated`, plugins `@hey-api/client-fetch`, `@hey-api/typescript`, `@hey-api/sdk`,
`@tanstack/react-query`, then `tools/check-generated.mjs` (section 2: openapi-ts exits 0 even when it generated nothing).
Result: `listProjects()`, `getVersion()`... and `listProjectsOptions()`, `getVersionOptions()`, `putFurnitureHeightsMutation()`
(names follow the operationIds). `src/api/client.ts` sets `client.setConfig({ baseUrl: import.meta.env.VITE_API_BASE ?? ''
})`. Generated files are committed and never edited; the integration step regenerates and diffs.

### 10.6 Python modules (`services/api/walkthrough_api/`)

`main.py` (`create_app(settings) -> FastAPI`, `app = create_app()`), `settings.py` (`WALKTHROUGH_DATA_DIR` default
`data`, `WALKTHROUGH_OFFLINE_TEMPLATE` default `dist/offline-template/viewer-template.html`, `WALKTHROUGH_CORS_ORIGINS`;
relative paths resolve against `app/`, found as two folders above `services/api`, whatever the working folder), `models.py`,
`deps.py` (`get_store`), `errors.py` (`ApiError(status, code, message, details)` + handler), `routes/projects.py`, `routes/versions.py`,
`routes/downloads.py`, `routes/furniture.py`, `store/base.py`, `store/local.py`, `builtmodel.py` (schema + 5.6),
`schema/built-model.schema.json` (copy of `docs/`, identical: a test checks), `furniture_csv.py` (port of
`furniture_kit.csv_text`, same bytes), `offline.py` (section 16), `openapi_export.py`, `seed/__main__.py`,
`seed/sources.py` (the seed table), `seed/convert_suite.py`, `seed/convert_house.py`, `seed/stages.py`,
`seed/presentation.py`.

---

## 11. packages/viewer

### 11.1 Module map (exports and owners; every export typed by a `contracts.ts` alias)

| File | Exports (contract type) | Owner |
|---|---|---|
| `src/index.ts` | `createViewer`, `parseAddressOptions`, `parseBuiltModel`, `parseReplayData`, `parsePresentation`, `ModelError`, `VIEWER_VERSION`, `export type * from './contracts'` | A |
| `src/contracts.ts` | copy of `docs/contracts.ts` | scaffold |
| `src/version.ts` | `VIEWER_VERSION = '0.1.0'` | A |
| `src/viewer.ts` | `createViewer: CreateViewer` (assembly, init order 11.4) | A |
| `src/address.ts` | `parseAddressOptions: ParseAddressOptions` | A |
| `src/model/parse.ts` | `parseBuiltModel`, `parseReplayData`, `ModelError` | A |
| `src/model/presentation.ts` | `parsePresentation`, `resolvePresentation: ResolvePresentationFn`, `DEFAULT_REPLAY_TEXTS` | A |
| `src/model/styles.ts` | `DEFAULT_PART_STYLES: Record<PartKind, PartStyle>` | A |
| `src/model/geometry.ts` | `extrudePart`, `sweepDelay`, `planBounds` | A |
| `src/core/context.ts` | `createContext: CreateContext` | A |
| `src/core/build.ts` | `buildScene: BuildScene` (pure three, Node-testable) | A |
| `src/core/heights.ts` | `createHeights: CreateHeights` | A |
| `src/core/visibility.ts` | `createVisibility: CreateVisibility` | A |
| `src/core/labels.ts` | `createLabels: CreateLabels`, `layoutLabels: LayoutLabels` | A |
| `src/core/pictures.ts` | `createPictures: CreatePictures` | A |
| `src/core/readouts.ts` | `createReadouts: CreateReadouts` | A |
| `src/core/loop.ts` | `createLoop: CreateLoop` | A |
| `src/core/bvh.ts` | `withBvh: WithBvh` | A |
| `src/core/disposer.ts`, `src/core/events.ts` | `createDisposer`, `createEventBus` | **scaffold (complete)** |
| `src/testhook/hook.ts` | `installTestHook: InstallTestHook` | A |
| `src/offline/entry.ts` | (the offline page's script) | A |
| `src/ui/dom.ts` | `el: El`, `clear(node)` | **scaffold (complete)** |
| `src/ui/root.ts`, `src/ui/css.ts` | `createRoot: CreateRoot`, `BASE_CSS` | C |
| `src/ui/panel.ts` | `createPanel: CreatePanel` (slots, floor buttons, ticks row, legend) | C |
| `src/modes/index.ts` (+ `state.ts`, `walk.ts`, `camera.ts`, `photo.ts`, `input.ts`, `ui.ts`, `probe.ts`, `css.ts`) | `installModes: InstallModes`; `camera.ts`: `lensFov`, `viewFov`, `frameRect`, `outSize`; `photo.ts`: `photoName` | B |
| `src/furniture/index.ts` (+ `logic.ts`, `boxes.ts`, `legend.ts`, `hover.ts`, `storage.ts`, `css.ts`) | `installFurniture: InstallFurniture`; `logic.ts`: `wholeMm`, `parseTypedHeight`, `fixedDecimals`, `csvField`, `furnitureCsv`, `undersideMm`, `stopsWalk`; `storage.ts`: `readStoredState`, `writeStoredState` | C |
| `src/replay/index.ts` (+ `timeline.ts`, `objects.ts`, `shader.ts`, `camera.ts`, `apply.ts`, `ui.ts`, `css.ts`) | `installReplay: InstallReplay`; `timeline.ts`: `stepTimes`, `fillCaption`, `ease` | D |

`test/contracts.test-d.ts` (scaffold) asserts each export against its alias (`const _: CreateViewer = createViewer`), so a
builder who drifts fails the typecheck. Until B, C, D land, the scaffold's stubs keep the viewer running:
`installModes` -> an Orbit-only ModesApi (`tick` = `controls.update()`, the rest no-ops, a default `state`),
`installFurniture` -> `null`, `installReplay` -> `null`, `createPanel` -> a panel with empty slots in order,
`createRoot` -> a root with hint and error box. Builders replace the stub bodies, never the signatures.

### 11.2 Public API (`contracts.ts` section 5)

`createViewer(container, project, options?) -> Viewer` builds everything synchronously (geometry included) and starts the
loop. It throws `ModelError` before touching the DOM if the project does not parse, and an `Error` before touching anything
if the container is not in the document (`container.isConnected`). **It either returns a handle or throws with nothing left
behind:** if any later init step throws (WebGL context creation, `buildScene`, a module's install), it runs its own
disposer first (root removed, WebGL context lost, listeners and timers off, adopted stylesheet removed, window hooks
removed, the live counter as before) and then rethrows. `ready` resolves after the plan pictures load and the first frame.

Heights. The **starting heights** are the model's, then `project.heights` (the saved ones) over them, then (local only) what
this browser stored. Reset goes back to the model's heights in the staff app (`'host'`) and to the starting heights, the
file's own (model + saved), in the offline file (`'local'`; fix step: a client's Reset no longer throws the owner's saved
heights away; with none saved both are the model's). `furnitureHeights: 'host'` (staff app): no
heights are stored in localStorage; `heightschange` carries the map of kinds whose height differs from the model's
(`source: 'typed' | 'reset'`). `'local'` (offline file): typed heights and the doorways tick are kept in localStorage under
`<storageKeyPrefix><photoName>:<stamp>`, with `:<8 hex of the saved heights>` after it when the file carries saved heights
(fix step: what was typed over one download's saved heights stays with that download) (a deliberate change from the
prototypes' `walkthrough-furniture-heights:<project>`,
18.31: heights typed on a prototype page do not carry over, and two versions never share a key). The stored JSON has the
prototypes' shape (`{ "<kind>": mm, ..., "keepDoorways": false }`, the key removed when there is nothing to keep), but its
heights are the kinds that differ from the **starting** heights (model + saved), not from the model's: so a Reset to the
model's heights, or the model's value typed over a saved one, still holds after a reload; `writeStoredState` gets that
baseline (contracts.ts 9). The Keep doorways tick is a per-browser preference in both modes (`{"keepDoorways": false}`, never
sent to the API). `setHeights(map)` (source `api`) applies a map without an event. `dispose()`: section 11.8.

### 11.3 Options and address options

`parseAddressOptions(search)` reads the prototypes' options exactly (viewer_modes.js `applyUrl`, build_replay.js start-up,
the hotel's `picture`), so that `applyAddress` reproduces them:

* `build`: any `mode` key (even `mode=orbit`, `mode=` or a typo) gives `'skip'`, and wins over `build=play` (the prototype
  tests `build === '0' || has('mode')` first); else `build=0` -> `'skip'`, `build=play` -> `'play'`; otherwise absent.
* `mode`: kept only for `walk` / `ghost`; `floor`: the key as written (an unknown key is ignored by `applyAddress`).
* `point`: present **whenever the address has an `x` key**, as `{ x, y, z }`, each the `parseFloat` value or `null` when its
  key is missing or unreadable. Walk starts at (x ?? 0, z ?? 0) (`x=abc`, or x without z, gives 0 there, as the prototype);
  Ghost then sets its position to (x ?? the current x, y ?? the current y, z ?? the current z). Without an `x` key, `y` and `z`
  are not read.
* `yaw`, `pitch` (degrees), `lens`, `eye`: `parseFloat`, unreadable values dropped (for these the prototype's fallback is the
  current or default value, so dropping is the same); lens clamped 12 - 85, eye 0.8 - 2.2.
* `frame` only one of the seven, `size` only `4k`, flags only as `=1` (`captions=0`, `picture=0|1`).

The offline page passes `parseAddressOptions(location.search)`; the staff app passes its own page's (`createViewer` never
reads `location` itself).

| Option | Effect | Applied by |
|---|---|---|
| `build` (`options.build` wins), `speed`, `captions` | replay start-up: settings / play / skip; speed quick 9 s, normal 20 s, slow 40 s; captions off | replay `start()` (D); default `settings` when stages exist, else `skip` |
| `mode`, `floor`, `point` (`x`, `y`, `z`), `yaw`, `pitch` | start in Walk / Ghost on a floor at a spot and direction (Ghost: y too) | modes `applyAddress` (B) |
| `lens`, `eye`, `straight` | lens mm, eye m, straight verticals | modes (B) |
| `cam`, `frame`, `size` | open the Camera panel (after the replay screen if one is up: `applyAddress` runs after `replay.start`, so `openCam(true)` finds modes locked and only sets `camWanted`), frame, 4K | modes (B) |
| `touch` | touch controls on | modes (B) |
| `nodownload` | photos and CSV not downloaded (`ResolvedOptions.noDownload`) | modes (B), furniture (C) |
| `shot` | a photo 300 ms after start-up | modes (B) |
| `picture` | Plan picture tick on (1) or off (0) | visibility (A) |
| `test` | offline page only: `testHook: true` | offline entry (A) |

### 11.4 Init order and the frame loop (`viewer.ts`)

1. `parseBuiltModel`, `resolvePresentation`, `parseReplayData` (throw before the DOM); the container must be connected.
2. `createContext`: root (`createRoot`, C) inside the container, renderer (`antialias: true`, pixel ratio `min(dpr, cap)`,
   size = root) with its canvas appended to the root **before** `new OrbitControls(camera, canvas)` (the controls put a
   capturing `keydown` listener on `canvas.getRootNode()`, which must already be the document), scene (background
   `#eef0f2`), `HemisphereLight(0xffffff, 0xe4dfd6, 1.6)`, `DirectionalLight(0xffffff, 1.6)` at (-20, 40, 15),
   `PerspectiveCamera(40, aspect, 0.1, camera.far)`, controls with damping on, camera start (fixed, or fitSlabs after the
   panel exists: step 4), `ResizeObserver` on the root and a pixel-ratio watcher -> `renderer.setSize(w, h, false)` + bus
   `resize`.
3. `buildScene` (5.4) -> `ctx.floors`, groups added to the scene, ground plane; `createPictures`; `createVisibility`
   (floor mode `all`, ticks from presentation.toggles and `address.picture`); `createHeights`; `createReadouts`.
4. `createPanel` (C): title, intro, floors row, ticks row, legend; slots. Then the fitSlabs camera start (needs the panel).
5. `installModes` (B): modes row into slot `modes`, HUD, Camera panel, touch controls, hint text, input listeners.
6. `installFurniture` (C): boxes into the floor groups, `colliders`, `late`; legend into slot `furniture` (last).
7. `installReplay` (D) when stages exist: Build row into slot `build`; its shader patch on every RiseItem; reads `late`.
8. `createLabels` (A); `installTestHook` (A) when asked; then the start-up, **in the prototypes' order** (each page called
   `installBuildReplay`, which started the replay inside the call, and only then `applyChecks()` and `modes.applyUrl()`):
   a. `replay.start(build, address)` when there is a replay, else `visibility.applyFloor()`;
   b. `visibility.applyToggles()` (the pages' `applyChecks()`; during the settings phase the replay's tick hides the late
      objects again before the first frame is drawn, as on the pages);
   c. `modes.applyAddress(address)`: with the replay on its settings screen, modes are locked, so `cam=1` only records
      `camWanted` and the Camera panel opens when the replay ends (`lock(false)`); and a `skip` start-up never runs after
      `?mode=walk` has already entered Walk;
   d. the loop hooks, registered here and only here: `replay` -> `replay.tick`, `modes` -> `modes.tick`, `sync` ->
      `pictures.sync`, `overlay` -> `labels.place` (no module calls `ctx.loop.add` for its own frame work, so nothing runs
      twice a frame);
   e. `loop.start()`.

   `replay.start(build, address)` (D) does exactly what build_replay.js did at start-up: `speed` and `captions` from the
   address; `'settings'`: `openSettings()` (enter: Orbit, `modes.lock(true)`, controls off, every floor shown, the replay
   objects, the card); `'play'`: the same, then `generate()`; **`'skip'`: `phase = 'done'` and
   `ctx.heights.apply(settings)` with the model's levels and heights, nothing else** (no enter, no finish: no camera pose,
   no change to the controls, no lock, no `applyFloor` / `applyToggles` / `furniture.apply`). The staff app's default start
   is `'skip'`.

If a step from 2 on throws, `createViewer` disposes what exists and rethrows (11.2). For the leak test, `testFailAt` (a
`ViewerOptions` field read only together with `testHook`) makes it throw at the start of a named step.

Each frame (`renderer.setAnimationLoop`): phase `replay` (replay.tick) -> `modes` (modes.tick) -> `sync` (pictures.sync)
-> `renderer.render(scene, camera)` -> `overlay` (labels.place). Errors in a hook go to `ctx.reportError` (error box +
`error` event) and the loop goes on.

### 11.5 Internal interfaces (`contracts.ts` section 6) and who changes what

* `FloorRecord` is shared: modes read `level`, `group`, `colliders`, `walkables`, `stack`; furniture adds boxes to `group`,
  `colliders` (only while they stop Walk) and `late`, and places them at `modelLevel`; the replay reads `rise` and `late`,
  moves `group` while it plays; `core/heights` sets `level` and the group's home position. Nobody replaces the arrays.
* `VisibilityApi` owns `group.visible` outside Walk (`setFloorMode`, `applyFloor`) and the ticks; modes set
  `group.visible` for the walked stack in Walk and call `applyFloor()` when leaving it (the prototypes'
  `restoreVisibility`); the replay shows every floor while it plays and calls `applyFloor()`, `applyToggles()` and
  `furniture.apply()` when it ends (the prototypes' `restore`).
* Bus events (`InternalEvents`): `mode` (modes -> panel marks the floor buttons, labels, test hook), `floorMode` and
  `toggles` (visibility -> panel), `settings` (heights -> modes, pictures), `replayPhase` (replay -> labels, panel),
  `furniture` (furniture -> viewer's public `heightschange`), `resize` (context -> modes, replay, labels).
* Public events (`ctx.events`, contracts.ts `ViewerEvents`), each with one emitter: `modechange` by `viewer.ts` (A) from bus
  `mode`, **only when the mode or the floor differs from the last one emitted** (B emits bus `mode` from every HUD update,
  as the prototype's `onChange`, so also on each lens change); `heightschange` by `viewer.ts` from bus `furniture`, **only for
  sources `typed` and `reset`** (`api` is `setHeights`, `tick` the doorways tick: neither may cause a save); `replayphase`
  by D; `photo` by B; `error` by `ctx.reportError`.
* Room labels show when the Room names tick is on, the mode is Orbit, and **`ctx.replay` is null or its phase is `done`**
  (the bank and suite pages' `replay.phase === 'done'`; the hotel had no replay), on the top visible floor only.
* `ViewerContext` fields set after a module's own install step (`panel`, `modes`, `furniture`, `replay`, `labels`, 11.4)
  are read only inside handlers and tick functions, never while that module installs.
* All screen maths is root-relative: `ctx.size()` replaces `innerWidth / innerHeight`, `ctx.rectOf(el)` replaces
  `getBoundingClientRect()` (frame rectangles, the replay's free rectangle, labels, the furniture label, the hotel camera).
* Keys: listeners on `window` / `document` through the disposer; a keydown counts only when its target is the body /
  document or inside the root, and not typing (`typing()` of viewer_modes.js), so the app's own controls keep their keys.

### 11.6 UI (`ui/`, C; the modes and replay parts by B and D)

Plain DOM inside `<div class="wtv" data-wt="root">` (position relative, 100 % of the container, overflow hidden,
`container: wtv / size`; every overlay is `position: absolute` in it, never `fixed`). Every selector starts with `.wtv`; the
custom properties `--bg #eef0f2`, `--panel #ffffffee`, `--ink #1d2329`, `--muted #5b6670`, `--line #d5dade`, `--accent
<presentation.accent>` are set on the root, with the pages' body font (`14px/1.4 system-ui, -apple-system, "Segoe UI",
sans-serif`) and colour. Body classes of the prototypes become root attributes (`data-fp`, `data-camopen`, `data-crowded`,
`data-touchui`, `data-replay`). Active buttons use `aria-pressed="true"` (styled like the prototypes' `.on`). Drawing text
(room labels, families, layers, floor names, legend and intro text, captions) is inserted with `textContent` only;
`ui/dom.ts el()` has no HTML input, and it sets styles through `element.style` (CSSOM), never a `style` attribute string.

* **Where the CSS lives.** One constructed `CSSStyleSheet` per viewer, added to `document.adoptedStyleSheets` and removed
  on dispose; each module adds its chunk once via `ui.addStyle` (the root keeps the text and calls `replaceSync`). Where
  constructed sheets are missing (happy-dom) `addStyle` falls back to one `<style>` inside the root. A strict
  `style-src 'self'` blocks a runtime `<style>` but not a constructed sheet or CSSOM styles (checked in Edge 156, 3 Nov), so
  the viewer itself needs no `'unsafe-inline'` on the later share page.
* **The host's reset is undone.** `BASE_CSS` starts with `.wtv, .wtv *, .wtv *::before, .wtv *::after { all: revert }`,
  then the root rule: every element inside the root starts from the browser's own defaults, exactly as on the prototype
  pages, whatever the host page resets. The staff app's Tailwind 4 preflight (in `@layer base`, which unlayered rules beat)
  would otherwise make everything border-box (the side panel, Camera panel and Build card 30 px narrower), zero margins and
  paddings (checkbox spacing), set `h1`-`h6` to `font-weight: inherit` (headings lose their bold) and `ul` to `list-style:
  none` (the Build facts lose their bullets). Rules the pages wrote as border-box (`#vm-hud`, `#br-sub`, `.fb-sw`, `.fb-h`,
  the step dots) keep it: they are more specific than `.wtv *`. The canvas gets `display: block; width: 100%; height: 100%`.
* **Root-relative sizes.** Every `vh` / `vw` of the pages' CSS becomes `%` of the root (all overlays are absolute children of
  the root, so `%` resolves against it: `#vm-cam` max-height `calc(100% - 60px)`, `- 70px` in Walk / Ghost, `- 270px` with the
  touch UI; `#br-card` `calc(100% - 110px)`; widths `calc(100% - 48px)` / `- 24px`), or `cqh` / `cqw` where an element's
  containing block is not the root; `100vmax` (the photo frame's shade, clipped by the root) stays. The pages' width and
  height media queries become `@container wtv (...)` queries with the same numbers, and viewer_modes.js `narrow()` reads
  `ctx.size().width <= 700`; `(pointer: coarse)` stays a media query (it is about the device). Below the staff app's 48 px
  bar the viewer is not full-window, so `vh` would overflow the root (at 1366 x 768 the Walk Camera panel could reach 756 px
  in a 720 px root).

The panel's CSS is the pages' (`#panel` -> `.wtv-panel`: top 12, left 12, width `min(330px, calc(100% - 48px))`,
content-box, max-height `calc(100% - 60px)`, or `- 90px` when the model has furniture, padding 12 / 14, radius 10).
Legend `inline`: line-height 1.9, swatch margin `0 4px 0 8px` (first `0`); `lines`: one item per div, line-height 1.45,
hanging indent 16 px.

**Selector map** (ported tests and the prototype adapter use exactly these):

| Prototype | App |
|---|---|
| `#panel`, `#hint`, `.legend`, `.room`, `#vm-err` | `[data-wt=panel]`, `[data-wt=hint]`, `[data-wt=legend]`, `[data-wt=room]`, `[data-wt=error]` |
| `h1` (the panel's heading), `#panel p` (its intro) | `[data-wt=heading]`, `[data-wt=intro]` |
| `#floors [data-f=both\|<key>]`, `.on` | `[data-wt=floors] [data-floor=all\|<key>]`, `aria-pressed="true"` |
| `#plates #glass #rooms #single #picture` | `input[data-wt=toggle][data-toggle=plates\|glass\|rooms\|single\|picture]` |
| `#vm-modes [data-m=orbit\|walk\|ghost]`, `#vm-cam-btn` | `[data-wt=modes] [data-mode=...]`, `[data-wt=camera-btn]` |
| `#vm-hud`, `#vm-hud-t`, `#vm-hud-cam`, `#vm-exit`, `#vm-cross` | `[data-wt=hud]`, `[data-wt=hud-text]`, `[data-wt=hud-camera]`, `[data-wt=exit]`, `[data-wt=cross]` |
| `#vm-cam`, `#vm-cam-close`, `#vm-lens`, `#vm-lens-v`, `[data-mm]`, `#vm-eye(-v)`, `#vm-tilt(-v)`, `#vm-straight`, `#vm-first`, `#vm-first-note` | `[data-wt=camera-panel]`, `camera-close`, `lens`, `lens-value`, `[data-wt=lens-preset][data-mm]`, `eye`, `eye-value`, `tilt`, `tilt-value`, `straight`, `first`, `first-note` |
| `#vm-frame-sel`, `#vm-size`, `#vm-px`, `#vm-grid`, `#vm-shot`, `#vm-photos`, `#vm-frame`, `#vm-flash` | `frame-select`, `size-select`, `px`, `grid`, `shot`, `photos`, `frame`, `flash` (all `[data-wt=...]`) |
| `#vm-stick`, `#vm-ud`, `#vm-up`, `#vm-down`, `#vm-snap` | `stick`, `updown`, `up`, `down`, `snap` |
| `#br-card`, `#br-settings`, `#br-play`, `#br-card ul`, `details` | `replay-card`, `replay-settings`, `replay-play`, `replay-facts`, `replay-layers` |
| `#br-card .br-file` (the intro title), `#br-card details summary` (the layers title) | `replay-file`, `replay-layers-title` |
| `#br-card input[data-k=<key>][data-p=level\|height]` | `[data-wt=replay-card] input[data-floor=<key>][data-prop=level\|height]` |
| `#br-speed [data-s=...]`, `#br-cap`, `#br-go`, `#br-skip0`, `#br-skip` | `[data-wt=replay-speed] [data-speed=...]`, `replay-captions`, `replay-go`, `replay-skip-settings`, `replay-skip` |
| `#br-steps li` (`.br-done`, `.br-now`), `#br-bar i`, `#br-sub`, `#br-again`, `#br-open` | `[data-wt=replay-steps] li[data-state=done\|now\|todo]`, `[data-wt=replay-bar] i`, `replay-caption`, `replay-again`, `replay-open` |
| `.fb-block`, `.fb-title span`, `.fb-note`, `.fb-all`, `.fb-keep`, `.fb-btns`, `.fb-reset`, `.fb-save`, `.fb-tip` | `furniture`, `furniture-title`, `furniture-note`, `furniture-all`, `furniture-keep`, `furniture-buttons`, `furniture-reset`, `furniture-save`, `furniture-tip` |
| `.fb-row[data-k=<key>]`, `.fb-show`, `.fb-sw`, `.fb-lab`, `.fb-h` (`.fb-edited`, `.fb-bad`), `.fb-blk` | `[data-wt=furniture-row][data-kind=<key>]`, `kind-show`, `kind-swatch`, `kind-label`, `kind-height` (`data-edited`, `data-bad`), `kind-stops` |
| `<meta name="model-data">` | offline page: the same meta; every page: `[data-wt=root][data-model-stamp]` |

Texts, labels, titles and tooltips stay word for word the prototypes' (the ported checks compare them).

### 11.7 Test hook (`testhook/hook.ts`, A; only with `testHook: true`)

Sets `window.__viewer` (TestHookViewer: the live ModesState, the probe, setMode, goToFloor, takePhoto, lock, mode),
`window.__host` (TestHookHost: `FL` records with the **model** level, `floors` = the FloorRecords with the **walk**
level, model, openings, probes, labels, upHit, downHit, rayHit, cast, furniture, camera, controls, pictures, rise, plinths,
groups, and `fitted` = `BuiltScene.fitted`, which replaces the house page's `__host.pieces`), `window.__build`
(TestHookBuild or `null`) and `window.__walkthrough` (a THREE subset: Vector2, Vector3, Raycaster, Box3, Plane, Matrix4,
Quaternion, Euler, MathUtils, Color; the Viewer handle; version; `live()`, `created()`, `gpu()`).
The prototypes' tests did `await import('three')`; the ported ones use `__walkthrough.THREE` (the bundled build has no
import map, and exposing the whole namespace would defeat tree-shaking). `dispose()` deletes these properties if they are
still this viewer's. The staff app turns the hook on only when `VITE_WTV_TEST_HOOK=1` (Playwright's web server sets it).

### 11.8 Dispose rules (`Viewer.dispose`, idempotent)

In order: stop the loop (`setAnimationLoop(null)`); exit pointer lock if the canvas holds it; `ResizeObserver.disconnect()`
and the pixel-ratio watcher off; every listener and timer registered through the disposer removed / cleared;
`OrbitControls.dispose()`; every geometry, material, texture and BVH of the scene graph and of the replay's objects disposed
(traversal + `disposer.track`); object URLs (photo thumbnails, CSV) revoked; image loads aborted (a late `onload` does
nothing); `renderer.dispose()`, `renderer.forceContextLoss()`; the viewer's adopted stylesheet taken out of
`document.adoptedStyleSheets` (or its fallback `<style>` removed with the root); the root element removed (the container is
left as it was); window hooks removed; the module's live counter decremented. The same steps run, for whatever exists, when
`createViewer` itself fails (11.2).

Listeners: our code adds every listener through the disposer. The two exceptions own theirs: `OrbitControls` (`pointerdown`,
`pointercancel`, `contextmenu`, `wheel` on the canvas, a capturing `keydown` on the document, and `pointermove` / `pointerup`
/ `keyup` only during a drag or while Ctrl is held) and `WebGLRenderer` (the context-lost / restored / creation-error
listeners on the canvas); their `dispose()` removes them. OrbitControls' `disconnect()` also removes listeners it never
added, which is why the leak test tracks registrations, not add / remove counts (17.4).

Self-check before `renderer.dispose()`: `renderer.info.memory.geometries === 0 && textures === 0`, else
`console.warn('[viewer] dispose left ...')` (the leak test fails on that warning).

---

## 12. Port map

Prototype code -> where it lives now. VM = `viewer-modes/viewer_modes.js`, BR = `viewer-modes/build_replay.js`,
FB = `furniture/furniture_boxes.js`, BK = `bank_test/src/make_html.py`, HT = `hotel_test/src/make_html.py`,
PS = `presidential_test/src/make_html.py`, HS = `cad_test/src/make_html_cad_merged.py`.

| Behaviour | Prototype | New owner |
|---|---|---|
| Constants (eye, radius, speeds, look rates, lens maths) | VM top | `modes/state.ts` (B), section 13 |
| Mode state `s` | VM `s` | `modes/state.ts` ModesState (B) |
| Mode buttons row, HUD, cross, photo frame, flash, stick, Up/Down, Camera panel markup and CSS | VM UI block | `modes/ui.ts`, `modes/css.ts` (B) into slot `modes` and the root |
| Error box and window `error` / `unhandledrejection` listeners | VM `showErr` | `ctx.reportError` + `[data-wt=error]` (A, C); no window listeners (18.14) |
| Walk collision: hitAhead, onFloor, clearance, findFree, openAhead, faceOpen, startPoint, walkMove | VM geometry helpers | `modes/walk.ts` (B) |
| Projection: lensFov, viewFov, wideAngle, frameRect, outSize, shiftPx (straight verticals), applyProjection, applyCamera, clampPitch | VM camera | `modes/camera.ts` (B) |
| Floors: pickFloor, stackOf, floorAtHeight, currentFloor (Ghost 0.3 m rule), applyVisibility, goToFloor, changeFloor | VM floors | `modes/index.ts` (B) with `visibility.applyFloor` (A) |
| setMode (Orbit save / restore, Ghost -> Walk landing, double-click point) | VM setMode | `modes/index.ts` (B) |
| updateHud (body classes, hint texts, touch buttons) | VM updateHud | `modes/ui.ts` (B), flags via `ui.setFlag` (C) |
| Camera panel sync, frame drawing, setLens, openCam (waits for the replay) | VM syncCamPanel, drawFrame, setLens, openCam | `modes/ui.ts` (B) |
| Photos: tiles at pixel ratio 1, stitch, flash, thumbnails (12), name, download | VM photoName, download, takePhoto | `modes/photo.ts` (B); download via `options.download` (A) |
| Keys, typing rule, pointer lock, drag look, wheel (lens / Ghost speed), double-click to Walk, stick, Up/Down | VM input | `modes/input.ts` (B), all through the disposer |
| Resize, pixel-ratio watcher | VM onResize, watchPixelRatio | `core/context.ts` (A) + modes on bus `resize` (B) |
| Frame tick (Walk / Ghost movement) | VM tick | `modes/index.ts` tick, loop phase `modes` (B) |
| Address options | VM applyUrl, BR start-up, FB params, HT picture param | `address.ts` parse (A); applied by modes (B), replay (D), visibility (A), furniture (C) |
| Probe read-outs, lock | VM probe, lock | `modes/probe.ts`, `modes/index.ts` (B) |
| `window.__viewer`, `__build`, `__host` | VM, BR, each page | `testhook/hook.ts` (A) |
| Step timing (KEYS, WEIGHT, SPEEDS), ease, span | BR top | `replay/timeline.ts` (D) |
| Rise shader patch (aDelay, uRise, discard) | BR onBeforeCompile | `replay/shader.ts` (D); `aDelay` written by `core/build` (A) |
| Settings card, steps list, bar, caption, Build row, input clamping | BR UI | `replay/ui.ts`, `replay/css.ts` (D) |
| Replay geometry: segments, quads, rings, bounds, make / unmake | BR objects | `replay/objects.ts` (D) |
| applySettings (group home, wall scale) + each page's applySettings (levels, plinth, fitPieces) | BR applySettings, BK/PS/HS applySettings | `core/heights.ts` (A), called by the replay (D) |
| Camera framing: freeRect, pose, sheetBox, stackBox, lerpPose, dirAt | BR camera | `replay/camera.ts` (D), root-relative |
| apply(T): floor slide / lift, line colours and fades, pieces, runs, solids, late fade, camera path, captions | BR apply | `replay/apply.ts` (D) |
| Phases: enter, openSettings, generate, finish (hand-over), skip, seek, tick, Esc | BR phases | `replay/index.ts` (D) |
| Furniture kinds, pieces, approach, Keep doorways rule, colliders sync | FB | `furniture/index.ts`, `boxes.ts`, `logic.ts` (C) |
| Underside (on top of a support), placement, unit box + outline materials | FB under, place | `furniture/boxes.ts`, `logic.ts` (C) |
| Typed heights and the doorways tick in localStorage | FB persist / restore | `furniture/storage.ts` (C), modes local / host |
| Legend: rows, master tick, Keep doorways clear, typing (select on focus, apply as typed, Enter / Esc / leave), Reset, Save | FB legend | `furniture/legend.ts`, `furniture/css.ts` (C), slot `furniture` |
| CSV (fixed, field, sort, BOM on download) | FB csv | `furniture/logic.ts` (C); Python port `furniture_csv.py` (E) |
| Hover label (Orbit only, 50 ms throttle, what hides a box) | FB hover | `furniture/hover.ts` (C) |
| Page head, CSS, panel markup (heading, intro, floors row, ticks row, legend) | BK/HT/PS/HS html | `ui/root.ts`, `ui/panel.ts`, `ui/css.ts` (C); texts from presentation (E) |
| Renderer, scene, lights, camera, controls; camera start (fixed / the hotel's fit) | BK/HT/PS/HS script top | `core/context.ts` (A); values in presentation.camera (E) |
| KIND / STYLE tables, mesh grouping, extrudePart, sweep, merged meshes, skins, slabs, stairs, ground plane | BK, HT, PS (meshes list), HS (solids, pieces, plates, stairs, ground) | `model/styles.ts`, `model/geometry.ts`, `core/build.ts` (A); per-project values in parts (E) and presentation.partStyles / creaseAngle / groundPlane (E) |
| House fitPieces, plinths | HS | `core/heights.ts` (A) via `fit`, `plinth` (E) |
| Plan pictures (data URLs, sheets, tick, `?picture=`) | HT | `core/pictures.ts` (A); assets (E); offline payload (A, E) |
| floorMode, applyFloor, applyChecks, markFloors, floor buttons, ticks | BK/HT/PS/HS | `core/visibility.ts` (A), `ui/panel.ts` (C) |
| Room labels with declutter (bank / hotel), plain (suite) | BK/HT placeLabels, PS placeLabels | `core/labels.ts` (A): the declutter for all |
| upHit, downHit, rayHit, cast | BK/HT, HS | `core/readouts.ts` (A) |
| Animation loop order | each page | `core/loop.ts` (A) |
| Panel intro, legend, title, captions with this drawing's numbers | BK/HT/PS/HS Python + page JS | `seed/presentation.py`, `seed/stages.py` (E) |
| Photo / CSV / storage name (`D.photoName`, `'Presidential'`, `'Sukhumvit'`) | each page | `model.photoName` (E converts) |

## 13. Constants to keep exactly

| Area | Values |
|---|---|
| Walk | eye 1.6 m; radius 0.3 m; walk 1.5 m/s, run (Shift) 3.4 m/s; look 0.0025 rad/px (mouse), 0.004 (touch); rays at 0.35 and 1.2 m with offsets 0, ±0.25, ±0.5, ±0.75, ±0.95 × radius, `far = step + radius`; onFloor ray from level + 1 m down, far 1.6; clearance 8 directions × 2 heights, far 3; findFree rings every 0.5 m, `n = max(8, round(r·6))`, passes `[[want, 6], [0.5, 12]]`, want 1.0 from a button, 0.5 from a point; faceOpen keeps the heading when 4 m are open, else scores the **23 other headings** at 15° steps (i = 1 - 23; the current one is never a candidate, so it always turns) by `open(15)·(0.7 + 0.3 cos Δ)`, the first best (strictly greater) winning; slide along a wall by removing the normal part; floor-edge slide tries the larger axis first; dt capped at 0.05 s; probe walk 5 cm steps |
| Ghost | speed 6 m/s default, 0.5 - 60, wheel `×1.2^(-px/100)`, Shift ×3; Space / E up, C / Q down; on a floor once the eye is 0.3 m above it; floorAtHeight tolerance 0.1 m |
| Climbing (only a model with `stairways`; any other model keeps the Walk row exactly) | the foot is the walker's own height, the eye is foot + eye; step up 0.25 m, step down 0.30 m (tolerance 0.1 mm); ground ray at the next centre from foot + 1.0 m down to foot - 0.30 m against the slabs, treads and landings of the walked stack, the first surface decides: within the window the foot goes there, higher the move is refused, none is an edge and the move is refused (never a fall), except on a floor with no slab of its own, where the floor's level within the step window is the ground (RR); gap bridge: no ground, then the ray again 0.08 m further along the move; head ray at the next centre from foot + 0.30 m up to foot + 1.90 m (fixed: the eye slider moves the camera only, RR) against the same surfaces, a hit refuses the move; body rays as Walk's, at foot + 0.35 and foot + 1.20 m, against the visible colliders of every floor of the stack whose range [level - slab thickness, level + wall height] overlaps [foot, foot + 2.0 m]; clearance, openAhead and crosses from the foot; findFree on the floor's own plate at its level, with ground under the spot and head room; the floor named is the nearest level, changing 0.20 m past mid-storey; the eye eases toward foot + eye with a 0.1 s time constant (`1 - e^(-dt/0.1)` a frame, snapped under 0.5 mm), never on a teleport or in a probe call; a probe call after `s.pos.x / z` or `s.floor` were written starts from the floor's level; treads and landings: one FrontSide mesh per floor, never a collider; fit `storey`: scale.y = S = (L(to) - L(from)) / (L0(to) - L0(from)) about the lower floor's model level; ceilings: `#f4f3ef`, roughness 0.95, FrontSide facing down, Walk and Ghost only, with the Ceilings tick |
| Camera | fov from `lensFov(mm) = 2·atan(12/mm)` (36 × 24 mm frame, the screen's short side); lens 12 - 85 mm, Walk default 24, Orbit lens from the camera fov 40 (33 mm); presets 16 / 24 / 35 / 50; wheel in Walk = 2 mm per 100 px; eye 0.8 - 2.2 m step 0.05; tilt slider -60 - 60°; pitch limit ±85°, ±35° with straight verticals; near 0.1 (0.05 in Walk / Ghost), far 600 (house 500) |
| Photos | long side 1920 (HD) or 3840 (4K); frames screen, 16:9, 3:2 (default), 4:3, 1:1, 4:5, 9:16; frame 94 % of the free width, at most 90 % of its height; 8 px from the panels; top 58 px in Walk / Ghost; 156 px kept at the bottom on touch devices; fall back to the whole screen when the free part is under 30 % wide or 22 % high; tiles of the screen size at pixel ratio 1; flash 350 ms (0.7 -> 0); 12 thumbnails; name `<photoName>_<Orbit\|Walk\|Ghost>_<overview\|floor name>_<lens>mm_<YYYY-MM-DD_HH-MM-SS>.png` with `[^\w.-]+` -> `-`; exact sizes 1920 × 1280, 3840 × 2560, 2160 × 3840 |
| Input | drag counts as a drag after 4 px (|dx| + |dy| from the start); mouse jumps over 300 px ignored; stick 116 px, knob 60 % of the radius, dead zone 0.15; pixel ratio cap 2 |
| Replay | weights read 1.2, sort 1.1, align 1.5, pair 1.3, merge 1.0, raise 2.3, finish 1.4; speeds 9 / 20 / 40 s; hold 700 ms at the end; dt cap 0.1 s; settings: height 1 - 12 m, level -10 - 200 m, step 0.05, empty or unreadable keeps the old value; scan bar 0.35 m; line heights +0.03 / +0.01 / +0.015; rise `brK = smoothstep((uRise - aDelay·0.6)/0.4)`, min 0.004, discard under 0.0005; camera search 36 steps over 0.5 - 20000 m, pad 1.08; top view direction (0, -1, -0.002); tilt 52°, final elevation clamped 20 - 60°; free rectangle leaves 86 px for captions (16 without) |
| Furniture | 10 - 5000 mm; whole mm = `floor(v + 0.5)`; underside = support's base + support's height (no chains; depth < 3); box = unit cube, base at 0, `MeshStandardMaterial(roughness 0.85, FrontSide, polygonOffset 1 / 1)`, edges colour × 0.4; knee ray 0.35 m (lower boxes are stepped over); Keep doorways clear on by default; hover throttle 50 ms, label at +14 / +18 px; CSV columns and rules of furniture/README.md; download name `<photoName>_furniture_list.csv` |
| Building | crease 25° (house 40°); sweep `clamp(0.8·(cx - x0)/(x1 - x0) + 0.2·(y1 - cy)/(y1 - y0))` over all non-slab parts; glass, railing, slab and stair values of 5.4; plan picture 0.005 m, polygonOffset -2; background #eef0f2; lights 1.6 / 1.6 |
| Labels | at level + 1.4 m; shown within |NDC| < 1.1, in front; rows 0, +1, -1, +2, -2 of (h + 2) px; gaps 2 px across, 1 px down; bigger area first; only the top visible floor |
| Hotel camera | away (24, 24.5, 29) × 0.9; target y 2.5; pan left by half of `min(panel right, width / 2)` × metres per px |

## 14. Per-project differences and how the one viewer handles them

| Difference | bank | hotel | suite | house | One viewer |
|---|---|---|---|---|---|
| Model file | v1 | v1 | own format | own format + furniture file | v1 for all (6) |
| Floors | 2 levels | 2 floors | 1 floor | 2 floors | floors row only with 2+; modes row after it, else after the ticks |
| Replay | yes | no | yes | yes | stages.json present or not |
| Captions | `{L1height}` | - | `{level}` | computed in JS | one placeholder syntax (7.3) |
| Part kinds, colours | bank table | bank table | own table | own STYLE, panes | one table + partStyles (5.4, 8) |
| Lintels on a wall-height change | scale | (no replay) | scale | heads stay | `fit` (5.5) |
| Ground plate | slab | slabs | slab | plinth from the ground | `plinth` |
| Stairs | strips + faint lines | strips | none | 0.15 m panels | `stairs.below / above / panels` |
| Ground plane | no | no | no | 80 × 50 m | presentation.groundPlane |
| Plan pictures | no | yes | no | no | pictureFrame + pictures |
| Room labels | declutter | declutter | all shown | none | declutter for all (18.12) |
| Camera start | fixed | fit to slabs | fixed | fixed, far 500 | presentation.camera |
| Legend | inline | one per line | inline | inline (static) | presentation.legend |
| Ticks | plates, glass, rooms (+ single) | + Plan picture | Floor slab, glass, rooms | plates, glass, single | presentation.labels + what the model has |
| Photo / CSV name | BangkokBank-Sampeng | Hotel-pictures | Presidential | Sukhumvit | model.photoName |
| Max script stamp | sha1 of model | sha1 of model | sha1 of the source model | (no script) | version.stamp + stampSource |
| Mesh groups | kind group + follow | the bank's | one mesh per kind group | lintels + sills, all panes, all plate rings of a floor merged | the bank's rule for all (5.4); the house's counts and names in 17.2 / 17.4 |
| Test read-outs | upHit, rayHit, downHit, probes | + pictures | doors, glassWest | cast, pieces, plates, plinths | one TestHookHost (11.7); `pieces` -> `fitted` |

---

## 15. apps/web (builder F)

### 15.1 Routes (React Router 8, data mode: `createBrowserRouter`, `RouterProvider` from `react-router/dom`)

| Path | Screen | Loader |
|---|---|---|
| `/` | redirect to `/projects` | - |
| `/projects` | project list | `queryClient.ensureQueryData(listProjectsOptions())` |
| `/projects/:projectId` | redirect to `/projects/:projectId/v/<latestVersion>` | `getProject` |
| `/projects/:projectId/v/:n` | project page | `getVersion` (detail), then model and stages |
| `*` | not found | - |

TanStack Query (`QueryClient` with `staleTime: 30_000`, `retry: 1`) and the generated `*Options()` / `*Mutation()`.
Document titles: `Projects · Walkthrough`, `<name> · v<n> · Walkthrough`.

### 15.2 Project list

A grid of cards (shadcn Card), one per project, newest first: thumbnail (`thumbnailUrl`, else a neutral placeholder with
the short name), name, a badge `CAD` or `Pictures`, floors (`2 floors: Level 1, Level 2`), furniture count, openings count,
the stamp (monospace), last updated (`29 Oct 2026`), versions count; the card links to `/projects/:id`. Loading: skeleton
cards; error: an Alert with Retry; empty: `No projects yet: run npm run seed`.

### 15.3 Project page

A 48 px app bar, the viewer filling the window below it (`position: fixed; top: 48px; inset-x: 0; bottom: 0`; the viewer
sizes everything from its root, 11.6). App bar: back to
projects, the project name, the version picker (shadcn Select: `v2 · 29 Oct 2026 · c3a9408304a2`, navigates), the
Downloads menu (shadcn DropdownMenu: `3ds Max script (.ms)`, `Furniture list (CSV)`, `Offline viewer (HTML)`, each a plain
`<a href download>` to the URL in `VersionDetail.downloads`, disabled when null), and the heights status (`Heights saved`,
`Saving…`, `Not saved: <reason>` + Retry; hidden when the model has no furniture). Building the `ViewerProject`:
`parseBuiltModel(model)`, `parsePresentation(version.presentation)`, `parseReplayData(stages, model)` when `hasStages`,
`pictures` = plan-picture assets by floor -> their URLs, `heights` = `version.overrides.heights`, `stamp`, `ids`; memoised
on `projectId`, `version`, `stamp`. Options: `{ address: parseAddressOptions(location.search), build: address.build ??
'skip', furnitureHeights: 'host', testHook: import.meta.env.VITE_WTV_TEST_HOOK === '1' }` (the app opens on the finished
model; `?build=play` etc. still work: 18.10).

### 15.4 The React wrapper (`src/components/ViewerHost.tsx`)

```tsx
export function ViewerHost({ project, options, onHeightsChange, onError, create = createViewer }: ViewerHostProps) {
  const ref = useRef<HTMLDivElement>(null);
  // React 19.2+ Effect Events: always the latest callbacks, without re-creating the viewer and without writing a ref
  // during render. Called only from the effect and from the viewer's event, never during render.
  const heightsChanged = useEffectEvent((heights: HeightMap) => onHeightsChange?.(heights));
  const failed = useEffectEvent((err: unknown) => onError?.(err));
  useEffect(() => {
    let viewer: Viewer;
    try { viewer = create(ref.current!, project, options); }
    catch (err) { failed(err); return; }                     // createViewer has already cleaned up after itself (11.2)
    const off = viewer.on('heightschange', e => heightsChanged(e.heights));
    return () => { off(); viewer.dispose(); };               // StrictMode: create -> dispose -> create on the same div
  }, [project, options, create]);                            // project and options memoised by the page
  return <div ref={ref} className="viewer-host" data-testid="viewer-host" />;
}
```

Safe under StrictMode because `dispose()` leaves the container exactly as it was and cancels pending image loads, and a
failed `createViewer` leaves nothing behind either. A version change gives a new `project` object: the old viewer is
disposed before the new one is made.

### 15.5 Saving heights

`heightschange` -> `useHeightsSaver(projectId, version)`: debounce 600 ms, one request in flight, the newest map wins;
`putFurnitureHeights({ path, body: { heights } })`; on success `setQueryData` for `getFurnitureHeights` and the version
detail's `overrides`; on error the status shows the reason and Retry re-sends the newest map. A pending save is flushed
when the page unmounts or the version changes. The CSV download and the offline file then carry the saved heights.
Fix step (`docs/contract-issues/I.md`): every PUT sends If-Match (its base revision) and a 412 merges this tab's changes into
the heights saved elsewhere; heights saved elsewhere while this tab has nothing unsaved are taken over (refetch on focus
and every 30 s); an unsaved map is kept in localStorage (`walkthrough-unsaved-heights:<projectId>:<version>`) until the
API has it, a failed save goes again by itself (2, 5, 10, 20, then every 30 s) and the browser asks before the tab is
closed while one has failed; the CSV and offline items wait while a save is going or failed, and every item is disabled
while the API does not answer.

### 15.6 Styling

Tailwind 4 (`@import "tailwindcss"; @import "tw-animate-css";` in `src/index.css`, the shadcn theme variables), shadcn
new-york components in `src/components/ui/` (button, card, badge, select, dropdown-menu, separator, skeleton, tooltip,
alert), `lucide-react` icons. The viewer's own UI is styled by the viewer (scoped `.wtv`), never by Tailwind, and the
viewer undoes Tailwind's preflight inside its root (11.6), so it looks the same in the staff app and in the offline file (a
web check compares computed styles, 17.4). For the later hosting (decision H, plan 3.5's strict Content-Security-Policy):
shadcn's Select and DropdownMenu use Radix's scroll lock (`react-remove-scroll` -> `react-style-singleton`), which adds a
`<style>` element at run time, so the staff app's `style-src` will need a nonce or `'unsafe-inline'`; the viewer needs neither.

## 16. Offline single HTML

**Template** (`packages/viewer/offline/viewer-template.html`, A), built once by `vite.offline.config.ts` (scaffold):
`root` = `packages/viewer/offline` and `build.outDir` = `app/dist/offline-template`, both absolute (from
`import.meta.url`), `emptyOutDir: true`, `base: './'`, `viteSingleFile()`, input `viewer-template.html`, host `127.0.0.1`.
The output is exactly `dist/offline-template/viewer-template.html`: with `root` left at `app/`, Vite keeps the input's
path under `outDir` (`dist/offline-template/packages/viewer/offline/viewer-template.html`, seen 3 Nov), and the API, the
Node script and E's test would all miss it. The scaffold's done-check tests that exact path.

```html
<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="model-data" content="__WTV_STAMP__"><title>Walkthrough</title>
<style>html, body { margin:0; height:100%; overflow:hidden; background:#eef0f2 } #wtv-app { position:fixed; inset:0 }</style></head>
<body><div id="wtv-app"></div><script type="application/json" id="wtv-data">__WTV_DATA__</script>
<script type="module" src="../src/offline/entry.ts"></script></body></html>
```

The two markers occur exactly once each in the built template (the entry code never contains them literally).
**Payload** (`OfflinePayload`, contracts.ts 11), made by plain concatenation of raw file text so that Node and Python give
the same bytes:

```
{"format":"walkthrough-offline/1","project":<meta.json>,"version":<version.json>,"model":<model.json>,
 "stages":<stages.json or null>,"pictures":{"<floor>":"data:<mediaType>;base64,<base64 of the asset>",...},
 "overrides":<overrides.json or null>}
```

(no line breaks; pictures in model floor order; each file's text as stored, trailing newline included, UTF-8). Then every
`<` in the payload is replaced by the six characters `\u003c` (valid JSON: `<` can only occur inside strings, and the result contains neither
`</script` nor `<!--`). `project` in the payload is the project's `meta.json`.

**Assembly: substitute in the template only, never search or rewrite the payload.**
1. Each marker must occur exactly once in the template; otherwise stop with an error.
2. Replace `__WTV_STAMP__` by the stamp (12 hex) in the template.
3. Split that template on `__WTV_DATA__` into exactly two pieces and write `piece0 + payload + piece1`.

Node must not use `template.replace('__WTV_DATA__', payload)`: a replacement string expands `$'`, `$&`, `` $` `` and `$$`,
and `$'` inserts the template's own tail (with its `</script>`) inside the data, so drawing text could close the data element
and run as HTML in a client's offline file (reproduced 3 Nov). Drawing text already contains `$` (`pres2_model.json` 102
times, e.g. `Xr_SDC_DD_ID-PRS-Fur$0$DA-FACILITIES`; `furniture_house.json` 129). Use `split` / `join` (or a replacer
function). Python does the same steps with `str.split` (its `str.replace` has no patterns but replaces every occurrence, so a
drawing name containing a marker's text would be rewritten; splitting the template once avoids both). Output
`<projectId>-v<n>.html`. **Node** (`scripts/make-offline.mjs`, A): every version of the store into `dist/offline/`.
**Python** (`walkthrough_api/offline.py`, E): the same algorithm on request, with the current `overrides.json`. Both are
tested with names containing `</script><script>alert(1)</script>`, `$'`, `$&`, `` $` ``, `$$`, `__WTV_DATA__` and
`__WTV_STAMP__` (17.3), and a test compares both outputs byte for byte, that corpus included (integration).
**Entry** (`src/offline/entry.ts`): parses the payload, sets
`document.title` = presentation.documentTitle, `address = parseAddressOptions(location.search)`, `createViewer(#wtv-app,
{ model, presentation, stages, pictures, heights: overrides?.heights, stamp: version.stamp, ids }, { address,
furnitureHeights: 'local', testHook: address.test === true })`, and shows a plain error if the payload is missing or does
not parse. It needs no network: everything (three, three-mesh-bvh, the viewer, the data, the pictures) is in the file.
**Seam for the client share page (later):** a second entry beside `offline/entry.ts`, also without React, that fetches the
same five files from the API with a share token and calls `createViewer` exactly as above.

---

## 17. Test plan

### 17.1 Shared fixtures (`app/fixtures`, made by the scaffold, read-only for builders)

Every file is listed in `fixtures/README.md` with its source, how it was made and its sha1.

* `models/` (all valid BuiltModel v1; A's model test parses every file here):
  * `bank-v1.model.json`, `bank-v2.model.json`, `hotel.model.json`: byte-identical copies.
  * `suite.model.json`, `house.model.json`, `mini.model.json`: **provisional**, made once by `python -B
    docs/reference/provisional_v1.py --prototypes .. --out fixtures/models` (system Python; it validates what it writes
    against the schema and the strict 5.6 rules). Suite and house follow 6.3 / 6.4 (two independent throwaway conversions
    agreed on 3 Nov: 62 parts, 22 openings, 1 probe, 16 rooms, 120 boxes; 197 parts, 86 openings, 76 boxes); they let A, C
    and D test the suite and the house before the seed exists, and E's converter is compared with them (6.5). `mini` is the
    v1 form of `furniture/fixtures/mini_model.json`: its fields kept, `photoName` `Fixture`, `slabThickness` 0.25, the
    three heights (1.0, 1.0, 2.1), empty per-floor maps, and as parts the bare scene `furniture/fixtures/harness.html` draws
    for a model without parts (per floor a 0.25 m plate over the furniture's extent plus 3 m, and a 0.2 m wall 1 m in from
    its east edge); and a door record (0.9 m wide, 0.45 m in front of the piece) for each id an approach list names
    (`L1-001`, `L1-002`, `L2-001`), so the approach rule holds. The test_boxes.mjs variants that are not v1 (the awkward
    model with a 460.5 mm kind height and a 10.5 mm base, the broken and the older ones) are not model fixtures: they go to
    the pure helpers (`furnitureCsv`, `readStoredState`, `wholeMm`) without `parseBuiltModel`.
  * `broken/schema/*.json` and `broken/cross/*.json` with `broken/expected.json` (file -> the JSON Pointer each checker must
    report): copies of the real models with one fault each (a wrong type, a missing field, a bad pattern; an unknown floor, a
    duplicate opening id, `z1 <= z0`, a stair array of 6 numbers, and the four furniture faults, which the viewer only warns
    about). `parseBuiltModel`, ajv (schema cases) and `walkthrough_api.builtmodel` all run over it (5.6).
* `stages/`: `bank-v1.stages.json`, `bank-v2.stages.json` (copies, valid v1). No provisional suite or house stages: no
  builder needs them before integration (the house's caption oracle is E's test, 17.3).
* `presentation/<projectId>[-v<n>].json`: provisional Presentation v1 for the five versions, assembled by
  `tools/make-presentation-fixtures.mjs` from the captured facts (title, heading, intro HTML split into runs, legend items
  and layout, floor buttons, tick labels, accent) plus section 8's fixed values (camera, creaseAngle, partStyles,
  groundPlane, toggles). E's `presentation.py` output is compared with them (17.3).
* `pictures/`: `floor1_plan.png`, `floor2_plan.png`.
* `csv/`: the four prototype CSVs (with BOM) and `<project>-typed.csv` goldens for typed heights (table 600, seat 300,
  cabinet 1000, other 2100 where present), made by `tools/make-csv-goldens.py` with the **system** Python and `-B`, which
  loads `furniture/furniture_kit.py` by path with `sys.dont_write_bytecode = True` and calls its `csv_text` (the kit needs
  shapely; nothing is written into `furniture/`).
* `prototype/<projectId>[-v<n>].json`: facts read from each prototype page in headless Edge by
  `tools/capture-prototype-facts.mjs` (copy of `viewer-modes/cdp.mjs`, port 9700, holding the Edge lock): `document.title`,
  the stamp meta, heading, intro text and HTML, floor buttons, ticks (label, checked), legend items (colour, text), panel
  order, accent, camera (position, target, fov, near, far), per floor the colliders (name, vertices, visible), walkables
  (vertices), late count, rise (name, scales), tick list sizes, label counts, the replay card (inputs, intro title, facts,
  layers title and rows, step titles and captions at the default settings), furniture `kinds()` and the sha1 of `csv()`,
  the hint text. How, where a page does not expose it: the scene facts are read with `?build=0&nodownload=1` and the card
  facts with the plain address; **tick list sizes** by toggling each tick and counting the objects under the floor groups
  whose `visible` flips (the pages keep `glassObjs`, `plateObjs`, `singleObjs` module-local); the **bank v1 camera** from
  `__viewer.probe.camera()` (position, fov) with target (0, 2.5, 0), near 0.1 and far 600 taken from its generator, as v2;
  the **house** page exposes no `model` and no labels (it has no rooms), so its facts come from `__host.groups`,
  `__host.FL`, `__host.floors`, `__host.rise`, `__host.plinths`, `__host.pieces`, `__host.camera`, `__host.controls`.
* `prototype/house_openings_before.json`: copy of `cad_test/test_house_openings_before.json`.

### 17.2 vitest (Node, happy-dom where a DOM is needed)

| Area (owner) | Checks |
|---|---|
| model (A) | every file of `fixtures/models/*.json` and `features.model.json` passes `parseBuiltModel` and ajv (Ajv2020, `strict: true`); every file of `fixtures/models/broken/` is rejected at the path `expected.json` names (the furniture cases warn instead, 5.6); `parseReplayData` on the bank stages; `parsePresentation` defaults; `parseAddressOptions` table (typos dropped, clamps, any `mode` key -> skip even with `build=play`, `point` whenever `x` is present with null for unreadable or missing coordinates) |
| build (A) | `buildScene` per project against the prototype facts per floor. **Bank v1, v2, hotel, suite:** collider and walkable vertex totals equal exactly (three 0.160 and 0.186 triangulate their outlines alike: checked on all 124 + 89 + 62 outlines, 3 Nov); mesh names, late counts and tick list sizes equal (bank / hotel names exactly; the suite's seven page meshes `solid`, `low` ... become `suite solid:follow`, `suite low:own` ...). **House:** the v1 rule groups differently and three 0.186's earcut 3.0.2 triangulates five wall outlines differently from 0.160's earcut 2.2.4, so the house is checked against these v1 values (three 0.186.1, provisional house model): ground colliders 7 (`solid:follow`, `glass:follow`, `single:own`, `solid:top`, `sill:clip`, `pane:top`, `pane:clip`) with 6,936 vertices, walkables 3 (792), late 51 (4 without the boxes), fitted 4; upper colliders 5 with 6,372 vertices, walkables 1 (588), late 31 (2), fitted 2; ticks: plates 4 objects, glass 10, single 4; plinths 3. The page had ground colliders 5 (6,924 vertices), walkables 1, late 49, upper 5 (6,348), plates 2, glass 8, plinths 1, `pieces` 2 + 2: the 36 vertices are the earcut difference, the counts the grouping (lintels apart from sills and panes split by fit; one mesh per slab part); `fixtures/README.md` records both. Walk, the ticks and the replay behave the same either way. `features.model.json` covers every kind, `fit`, `plinth`, `panels`, the ground plane, a deck that is not a collider; aDelay range 0 - 1; slab materials FrontSide; glass renderOrder from the style |
| heights (A) | `apply`: scale, top (heads stay at 3.50 / 2.00 / 4.50 / 3.90 m on the house, lintels gone at 2.00), clip, plinth foot at 0 for level 1.50, Walk level, picture y |
| labels, readouts (A) | `layoutLabels` rows and hiding; upHit / downHit / rayHit / cast against known parts (raycasts work in Node) |
| disposer, events (scaffold) | every listen / timeout / track undone; idempotent |
| modes (B) | lensFov, viewFov (portrait), frameRect / outSize for every frame and size (1920 × 1280, 3840 × 2560, 2160 × 3840, whole screen), photoName, typing rule, clampPitch; walk collision on a synthetic floor: stops 0.2 - 0.6 m from a wall, slides at 40° along it, never through a 7 cm partition, onFloor at a void edge, findFree from outside, Ghost floor rule |
| furniture (C) | `wholeMm` (62.5 -> 63, 460.5 -> 461, 10.5 -> 11), `parseTypedHeight` ('', '4,5', '-3', 'abc', 6, 9999 refused; 10 and 5000 taken), underside (computer on a 750 table at 0.75, printer, wall TV at 0.90), `stopsWalk` (hidden, stops off, curtain, approach with the tick on / off), `furnitureCsv` equal to the goldens (four projects from `fixtures/models`, default and typed heights, and the awkward model of `furniture/test_boxes.mjs` passed straight to the helper: commas, quotes, CR / LF, -0.0004, ties 12.25 -> 12.2, 0.0625 m -> 63 mm, a 460.5 mm kind height -> 461), storage read / write rules (junk ignored, only `false` keeps the tick off, nothing stored when nothing differs from the starting heights, a Reset to the model's heights over saved ones is stored, host mode stores no heights, the key `<prefix><photoName>:<stamp>`), a kind without pieces gets no row, the furniture leniency of 5.6 (unknown kind or floor: left out with a warning; missing support: on the kind's base; approach ids that are no opening: kept; count: the pieces'), no furniture -> null; legend DOM in happy-dom (rows, counts, swatches, ticks, typing state). The test_boxes.mjs "older" checks (no approach, approach not a list) stay with that prototype test: v1 requires `approach` |
| ui (C) | panel order with and without a floors row, ticks shown per model, legend inline / lines, intro runs as text (an `<img onerror>` in a run stays text), `addStyle` into an adopted sheet (and the `<style>` fallback), `BASE_CSS` starting with the `all: revert` rule, no `vh` / `vw` / `@media` size query in C's chunks (B and D test theirs the same way; the `100vmax` shade is the one exception) |
| replay (D) | `stepTimes` (weights), `fillCaption` (all three placeholder forms, unknown key kept; the bank's captions at default settings equal the facts), input clamping and empty value kept, `apply(T)` idempotent on a test context, phases settings -> play -> done, seek, the hand-over state (groups at home, solids full, late opaque, ground plane opaque), `start('skip')` (phase `done`, heights applied, camera, controls and lock untouched, no `applyFloor` / `applyToggles` / `furniture.apply`), the ground plane hidden in settings and play and fading in during finish. The house's captions are checked by E on the converted stages (17.3) and in the browser by `replay.spec.ts` |
| web (F) | ViewerHost with a fake `create`: one viewer after StrictMode's double mount, disposed on unmount and on project change, a `create` that throws reported through `onError` with nothing to dispose; heights saver debounce / in-flight / retry; card formatting |

### 17.3 pytest (`services/api/tests`, E)

Store (list, get, NotFound codes, atomic overrides write, revision; `get_store` is the only way routes reach it), seed (the
table of 9.2, idempotent with and without `--force`, overrides kept, nothing written outside `--data` and no `__pycache__`
in a prototype folder), converters (6.5: counts, byte-identical bank / hotel, stamps against the `.ms` line 2 and
`stampSource`, house plates and rings and `sheetShift`, suite openings and probe; the suite and house equal the provisional
`fixtures/models/*.model.json` as parsed JSON), `builtmodel.validate` rejects every file of `fixtures/models/broken/` at the
path its manifest names (furniture cases included: the API is strict), presentation against the prototype facts and the
provisional `fixtures/presentation/*.json`, stages against the prototype facts (17.1; the **house oracle** of 7.4: with the
default settings filled in, every caption, fact, layer row and step title equals the page's, character for character, and
the same for the bank and the suite), schema copy identical to `docs/`, CSV (`furniture_csv` equals the prototype CSVs
with no heights and the typed goldens), every route (status, headers, ETag / 304, attachment names, camelCase, errors and
their codes, PUT validation), OpenAPI (operationIds; `openapi.json` re-exported and compared byte for byte), offline
assembly (each marker exactly once, else an error; escaping: families, layers and room names containing
`</script><script>alert(1)</script>`, `$'`, `$&`, `` $` ``, `$$`, `__WTV_DATA__` and `__WTV_STAMP__` stay inside the JSON
and parse back equal) and the byte equality with `make-offline.mjs` on that corpus and the seeded store: it skips while the
template or the Node script is missing, **except when `WT_INTEGRATION=1`, when it fails instead**. Uses `TestClient` on a
temp copy of a seeded store.

### 17.4 Playwright (`tests/e2e`, installed Edge)

Config (`tests/e2e/playwright.config.ts`, scaffold): `use: { channel: 'msedge', headless: true, viewport: { width: 1400,
height: 880 }, acceptDownloads: true, launchOptions: { args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader',
'--ignore-gpu-blocklist', '--allow-file-access-from-files'] } }`, **never `hasTouch` or `isMobile`** (with `hasTouch`
Edge reports `maxTouchPoints` 1 and `(pointer: coarse)`, so the viewer would start in touch mode and keep 156 px free at the
bottom of every photo frame); `outputDir: <WT_TMP>/pw-results` and reporter files under `WT_TMP` (section 3); `workers: 1`;
`retries: 1` for specs tagged `@timed`; globalSetup takes the Edge lock (section 3) and globalTeardown releases it; no
browser download. Two projects: `e2e` (`tests/e2e/*.spec.ts`) and `harness` (`packages/viewer/test/harness/**/*.spec.ts`
against `npm run harness -- --port $WT_WEB_PORT`). Every `@timed` check attaches the page's measured frame rate; a failure
below 12 fps means "re-run alone", not a defect. `lib/page.ts` does touch and tap through `context.newCDPSession(page)` and
`Input.dispatchTouchEvent`, exactly as `cdp.mjs` does (pointerType `touch` while `maxTouchPoints` stays 0): Playwright's own
`touchscreen` refuses to work without `hasTouch`.

Offline specs open `dist/offline/<project>-v<n>.html` from disk with `?build=0&nodownload=1&test=1` (replay specs without
`build=0`; **the photo checks of `modes.spec.ts` without `nodownload`**: they read the downloaded PNG's name and size, as
`test_viewers.mjs` did, saving each download to `testInfo.outputPath()`), fail on any request that is not `file:`, `data:`
or `blob:`, and wait for `__walkthrough.viewer.ready`. Web specs run against `vite dev` on 5711 (StrictMode on) with the API
on 8711 over a temp copy of `data/`; all URLs use 127.0.0.1.

`lib/target.ts` (scaffold) also runs the offline specs against the **prototype pages** (`E2E_TARGET=prototype`), so each
builder proves the port of its checks before the app exists; `E2E_TARGET=app` (default) is the real run. For the prototype
target it supplies: the old selectors (11.6); a shim mapping the suite's `doors` / `glassWest` and the house's per-floor
openings to the v1 shapes and `__walkthrough.THREE` from the page's import map; **no network rule** (the pages load three.js
from cdn.jsdelivr.net); `fitted` (app `__host.fitted`: ground 4 meshes, upper 2; prototype `__host.pieces`: 2 and 2) and
`plates` (app: the slab parts' `{o, h}` per floor from `__host.model`; prototype `__host.plates`); and the house's **mesh
classes**, `meshClass(name)`, so the ported house checks classify ray hits by class, never by a literal mesh name:

| class | prototype name matches | app name matches |
|---|---|---|
| `wall` | `/:wall$/` | `/ solid:follow$/` |
| `lintel` | `/:lintels and sills$/` | `/ solid:top$/` |
| `piece` (lintel, sill or pane) | `/:(lintels and sills\|window panes)$/` | `/ (solid:top\|sill:clip\|pane:top\|pane:clip)$/` |
| `pane` | `/:window panes$/` | `/ pane:(top\|clip)$/` |
| `glass` | `/:glass$/` | `/ glass:follow$/` |
| `single` | `/:single$/` | `/ single:own$/` |

Checks of behaviour this design changes on purpose are tagged `@app-only` and skipped on the prototype target: the suite's
labels not overlapping (the declutter is new, 18.12), the storage key with the stamp (18.31), the slab polygonOffset
(18.13), the computed-style check below.

**Ported** (per project where it applies; spec owner in brackets):

* structure (A): loads without errors and without network; the stamp meta equals the version's (and the `.ms` stamp);
  room names over the top floor, none overlapping (bank, hotel, suite); floor buttons show / hide floors in Orbit and change
  the floor in Walk, PgUp / PgDn, Both -> first floor; walls stop you at 40 random spots per floor, never through, never
  inside; every door walkable through its middle both ways (exterior from inside) via the openings; passages left as
  they are (no lintel overhead, no pane, nothing built: bank, hotel, house); door heads with a lintel or transom at the head
  (bank, hotel) and lintels that stay at the heads when the house's ground walls go to 3.50 / 2.00 / 4.50 / 3.90 m, panes
  reaching the top follow; glass stops you at every probe (bank partitions, curtain wall, panes; hotel glazing; the suite's
  west glass) and every house window stops you (knee and chest rays hit its pane or sill, walking at it stops before it);
  the bank's glass partitions at 2.60 m with nothing above, the parapet at 1.10 m, the ATM gap closed to 3.70 m; no floor
  over the stair and lift voids on the upper floors (bank, hotel); stair steps one riser apart (bank, hotel); the house's
  no-fins and no-leaves-in-front-of-windows checks; the plinth stays on the ground at level 1.50; a 2.00 m wall height
  makes the walls 2.00 m; the house's passages no harder to walk through than before the openings (stored
  `test_house_openings_before.json` copied to fixtures); the Plan picture tick (off at start, each shown floor's sheet, both
  in Walk, off again, `?picture=1`), sheets byte-equal to the asset files, corners through the pictureFrame, 5 mm lift, and
  the walls-on-the-picture contrast check; untrusted text (a room / family / layer `<img src=x onerror=...>` model)
  renders as text. From `hotel_test/test_hotel.mjs`, the checks that measure what the viewer builds: the railings stop you
  (Walk at every railing part with `probe.walk`), the forecourt is floor and the entrance can be walked out
  (`probe.onFloor`, `probe.walk`), the lift doors are open 1.00 m between their drawn jambs (`rayHit` on the colliders), the
  hatches are open from the sill to the head (`rayHit`), and the invisible collision skins reach into no opening between
  wall jambs (`rayHit`).
* modes (B, house, bank, suite, hotel): Orbit at start; 2 -> Walk at eye height on the first floor with room around you;
  W walks; stops at a wall 0.2 - 0.6 m; slides at an angle; 40 random slides (>= 90 %); still on the floor; keys after
  clicking a tick; Space does not tick it; 3 -> Ghost through walls, Space rises, C sinks; Ghost floor button hides the
  other floor without moving you; Esc back to Orbit where you left it, floors visible again; the Camera panel, 3:2 frame and
  `1920 × 1280 px`; lens 50 -> fov; P in Orbit downloads `<photoName>_Orbit_overview_50mm_<stamp>.png` 1920 × 1280; tilt;
  straight verticals (level camera, picture shifted); eye height; Walk photo named after the floor; 4K 3840 × 2560; 9:16
  2160 × 3840; whole screen keeps the window shape; panel closed -> whole screen; double-click -> Walk at the spot; touch on
  a desktop (tap shows the stick, stick moves you, a second finger looks, letting go stops, Upstairs / Downstairs, the mouse
  hides them); the 16 Oct and 19 Oct fixes (Ghost then Walk lands on a floor; Ghost 1 m above the upper floor names the photo
  after it; holding P takes one photo; wheel follows scroll distance; a focused Frame list hands keys back; the frame fits
  between the panels and below the top bar; Exit clickable; a slow drag does not lock the pointer, a click does; the flash
  in Orbit; address typos ignored; the drawing buffer follows a pixel-ratio change; Ghost above a hidden floor names the
  floor showing; never closer than 0.25 m to the thin partition's end).
* replay (D, bank, suite, house): opens on Build settings with the drawing's levels and heights (house `0.90, 3.90, 4.80,
  3.50`); viewer keys do nothing there; Generate plays with captions quoting the numbers (bank: 39 doors, `rises to 3.70 m`,
  lintels, glass partitions); keys locked while it plays; ends in the normal viewer, unlocked, groups at home, both floors;
  the upper level set before Generate is the one walked (eye 6.60 m); Replay plays again; Esc skips; Build settings reopen
  with the changed values; Skip on the settings screen; a cleared Level box keeps its value; after a replay you are back
  at the view you left; `?cam=1` opens the Camera after the build screen; the card counts the house's 38 layers; all seven
  steps ticked at `seek(1)`; the camera tilts without turning while the floors line up; the boxes come in last (none before
  the walls rise, all opaque at the end, the blocking ones are colliders) and the doorways rule holds after a replay.
* furniture (C, bank v2, suite, house, hotel): the side panel at 1366 × 768 and 1920 × 1080 (on screen, scrolls or fits,
  title and Reset / Save reachable) and its bottom edge above the hint line at every height from 640 to 1080 px; the legend
  (rows in table order, label with count, colour, default height,
  show and stops ticks, Keep doorways clear ticked); one box per piece in its floor's group named `furn:<kind>:<id>`; the
  page's own ticks and floor buttons leave the boxes alone; typing 600 into the table box with real keys puts the table tops
  at 0.60 m and what stands on them follows; Walk starts clear of the boxes from many Orbit views; Walk stops at real boxes
  short of the face, never inside; Keep doorways clear on: boxes in an approach do not stop you, the others do; off: they
  do; the colliders against the approach lists; show off: walk through, stops off: walk through while drawn; 300 mm stepped
  over, the default stops; Ghost through a table and a cabinet; doors walkable with the boxes on; glass still stops you with
  the boxes on; 40 random wall-or-box walks; not trapped inside a box (entered at its middle, or switched on under you);
  `csv()` equals the prototype CSV byte for byte (no BOM) and its approach notes; the hover label (kind, family, size,
  floor; `does not stop you: in the approach of ...`).
* web (F): the project list (4 cards, fields, thumbnails, placeholder for the house); the project page (viewer canvas, one
  viewer, the version picker switches the bank between v1 and v2 and disposes the old viewer: one canvas, `live() === 1`);
  StrictMode on the dev server: `created() === 2`, `live() === 1`, one canvas; heights typed in the viewer are saved
  (PUT seen, status `Heights saved`), survive a reload, appear in the CSV download and in the offline download; the Max
  script download is byte-equal to the seeded file; the offline download opens from disk. `@app-only`: the viewer looks the
  same as in the offline file whatever the app's Tailwind does: in both, at 1400 px, the heading's `font-weight` is 700, the
  side panel's `offsetWidth` is 360 (330 + 28 + 2, content-box), the Camera panel's 300, the Build card's facts list has
  `list-style-type: disc` (opened with Build settings), and a tick's checkbox keeps the browser's default margin (A checks
  the offline file, F the staff app, the same numbers).

**New:** mount / unmount 20 times on one page (A, `leak.spec.ts`): live WebGL contexts back to the baseline (a
`getContext` / `WEBGL_lose_context` counter installed before mounting); listener **registrations** on window, document and
the container back to the baseline, tracked as a set keyed by (target, type, listener, capture) from wrapped
`addEventListener` / `removeEventListener`, with removals of registrations it never saw ignored (OrbitControls'
`disconnect()` removes listeners it may never have added, so plain counters go below the baseline or cancel a real leak); no
`.wtv` element, no viewer stylesheet left (none of ours in `document.adoptedStyleSheets`, no `<style>` from us), no window
hook left, no `[viewer] dispose left` warning, `gpu()` 0 / 0 before each dispose. The same checks after mounts that fail:
`getContext` stubbed to fail once (the renderer throws after the root exists) and `testFailAt` at each of the later steps
(11.4): `createViewer` throws and the baseline holds. The same 20 mounts through the web app's route changes (F).
Byte-equal offline files from Node and Python (integration).

**Left for later, and why:** the phone and landscape-phone sections and the parked layout problems (PC first, 19 Oct;
the touch code itself is ported and its desktop checks run); the Srisawan hospital sections (not one of the four projects);
the Max script checks of `test_*_maxscript.py` (the scripts are served byte for byte; their checks stay with the
prototypes until the pipeline generates scripts); the hotel's pure data checks (the lamp symbols without boxes, the
sculptural and the check-in seating kinds, the iconic stair's flight outline beyond the generic void check) because they
check furniture and stair data that is byte-identical and still checked by `hotel_test/test_hotel.mjs` (its checks that
measure the built viewer are ported, above); the furniture harness's storage-blocked and timing edge cases beyond those in
17.2 (the logic is unit-tested; the DOM timing case "640 not 40" is in C's harness spec); test_boxes.mjs's "older" model
checks (v1 requires `approach`).

---

## 18. Decisions made here

0. **Contract changes.** `contracts.ts`, `built-model.schema.json` and the API models are frozen at the scaffold. A builder
   who finds a defect writes it in its own file `docs/contract-issues/<step>.md` (S, A, B, C, D, E, F; created empty by the
   scaffold; nobody writes another step's file, so parallel writers cannot overwrite each other), works around it inside
   their own files, and the integration step reads all of them and settles each with the architect. Nobody edits another
   builder's files.
1. **TypeScript 6.0.3**, not 7.0.2 (4.3).
2. **BuiltModel v1 = the bank / hotel format**, extended only with optional fields (5.1); no version field in the model.
3. **A version sidecar (`version.json`) carries metadata and the presentation** (texts, legend, camera, styles), computed
   by the seed from each generator's own Python; the viewer has no per-project code.
4. **ReplayData v1 = the bank stages format** with optional fields defaulting to the bank page's values; the bank stages
   are copied byte for byte, the suite and the house converted.
5. **The bank is seeded with two versions** (27 Oct and 29 Oct, each with its own `.ms` and stamp): real version history
   for the picker, and a model without furniture.
6. **Stamp of a converted model** = sha1[:12] of the file its Max script was made from (`stampSource`); `modelSha1` is
   always the stored model's.
7. **The Max script is served as seeded**, not regenerated with saved heights (its window's height spinners set them in
   Max); generating scripts from v1 belongs to the next milestone's pipeline.
8. **The furniture CSV is generated by the API** (Python port of `furniture_kit.csv_text`) from the model and the saved
   heights; with none saved it equals the prototype CSV byte for byte.
9. **Offline HTML: raw-text payload** with `<` escaped as `\u003c`, assembled identically in Node (batch) and Python
   (download with the current heights) by substituting into the template only (each marker once; split, never a
   replacement-pattern `replace`, 16); tested byte for byte, with `$` patterns and marker texts in the names.
10. **The staff app opens a project on the finished model** (`build: 'skip'` unless the address says otherwise); the
    offline file keeps the prototypes' start (Build settings first when there is replay data).
11. **Heights:** the API is the store in the staff app (`furnitureHeights: 'host'`); the offline file keeps localStorage on
    top of the embedded saved heights; Keep doorways clear stays a per-browser preference; only heights are saved.
12. **Room-label declutter for every project** (the suite page showed all labels unsorted).
13. **Every floor plate gets polygonOffset -1** (the suite's and house's had none); no z-fighting. Parts walked on or over
    (`collider: false`, the decks) get -2, or the suite's 2 cm decks vanish under the plate (integration I-1).
14. **No page-wide error listeners**; the viewer reports its own errors (error box + `error` event). (The staff app's
    `index.html` has one inline filter, for the browser's harmless ResizeObserver-loop notification: fix step.)
15. **Keys are the viewer's only when the event target is the body or inside its root**, so the app bar's controls keep
    theirs.
16. **three-mesh-bvh per mesh** (`geometry.boundsTree`, `mesh.raycast`), no patching of three's prototypes.
17. **CSS in one constructed stylesheet per viewer** (`document.adoptedStyleSheets`, removed on dispose; a `<style>` in the
    root only where constructed sheets are missing), every selector under `.wtv`, the host's reset undone by `all: revert`,
    sizes root-relative (`%`, `cq*`, `@container`), `data-wt` test selectors, `aria-pressed` for active buttons (11.6). It
    works under a strict `style-src` and looks the same in any host page.
18. **Test hook names `__viewer`, `__host`, `__build` kept** (the ported checks change little) plus `__walkthrough`; only
    when asked (`?test=1` offline, `VITE_WTV_TEST_HOOK=1` in the web app).
19. **The web app reaches the API through the dev / preview proxy** (`/api`), CORS also open for the dev origins.
20. **happy-dom** for DOM unit tests (jsdom 30.1.3 needs Node 24.15); **no ESLint / Prettier** in this milestone (strict
    `tsc` is the gate; adding a linter is the owner's call); **no toast library** (shadcn's sonner pulls in next-themes).
21. **Each model keeps its page's behaviour on a wall-height change**: the bank's lintels scale (`follow`), the house's
    keep their heads (`fit`).
22. **shadcn style new-york** (registry new-york-v4) on the `radix-ui` package and shadcn's `cn` package, as the live
    registry requires; the components are added once by the scaffold and are ours from then on.
23. **Ids**: projects are kebab-case slugs (`bank-sampeng`, `presidential-suite`, `sukhumvit-house`, `hotel-lobby`),
    versions integers from 1; API JSON camelCase.
24. **The Python package is not installed into the venv**; `tools/run-py.mjs` sets `PYTHONPATH`. The lock pins all 28.
25. **httpx 0.28.1 as the plan lists**, Starlette's httpx2 deprecation warning filtered in pytest.
26. **Floor keys `[A-Za-z0-9_]{1,32}`** (caption placeholders).
27. **The hotel is used as drawn** (owner, 3 Nov: "keep it strictly as the drawing said"): no rescaling anywhere.
28. **The house has no thumbnail** (no top-view PNG in its folder): the card shows a placeholder.
29. **All viewer overlays are absolute inside the root**, and all screen maths root-relative, so the same code works full-
    window (offline) and below the app bar (staff app).
30. **Picture sheets live in a scene-level group** (as the hotel page), moved with their floor's level setting.
31. **The furniture storage key carries the stamp** (`walkthrough-furniture-heights:<photoName>:<stamp>`; the prototypes'
    was `walkthrough-furniture-heights:<project>`): typed heights never leak across model versions. Heights typed on the
    prototype pages do not carry over to the offline files. Local mode stores the differences from the starting heights
    (model + saved), so a Reset over saved heights survives a reload (11.2). A file that carries saved heights adds
    `:<8 hex of them>` to the key (fix step).
32. **One mesh-grouping rule for all models** (the bank's: `<mesh>:<fit>` per floor, one mesh per slab part), no
    per-model merge option: the house gets more, smaller meshes than its page (17.2 lists them) and the same behaviour.
33. **Start-up in the prototypes' order:** `replay.start` before `modes.applyAddress`; `start('skip')` only sets the phase
    and the heights (11.4).
34. **The viewer is lenient with furniture, the API strict** (5.6): the viewer does what `furniture_boxes.js` did; the seed
    refuses any inconsistent model.
35. **Provisional fixtures for the parallel phase:** the suite, house and mini v1 models from
    `docs/reference/provisional_v1.py`, and presentation JSON from the captured facts (17.1); E's real converters and
    presentation port are compared with them.
36. **One headless Edge at a time** on this machine (`tools/edge-lock.mjs`, section 3), and everything a test run writes
    under its own `WT_TMP`.
37. **`floors[].sheetShift`** (optional) keeps a floor's place on its source sheet (the house's upper floor), so the
    model's drawing coordinates stay exact for the next milestone's pipeline.
38. **The project metadata file is `meta.json`;** `project-data.json` (per version) and `mappings/` are reserved for the
    plan's project data and the per-office layer mappings (9.1).
39. **Routes are plain `def` with the store from `Depends(get_store)`; `VersionDraft` takes staged blob references** (9.3,
    9.5): the seams for Supabase row-level security, async network storage and direct-to-storage uploads.
40. **`createViewer` cleans up after itself when it fails** (11.2), and `ViewerHost` uses React's `useEffectEvent` (15.4).
41. **All servers on 127.0.0.1** (section 3); **touch in tests through CDP, never `hasTouch`** (17.4).

Added by the scaffold (3 Nov 2026), each the smallest fix for something the design could not do as written:

42. **Playwright starts its web servers before globalSetup** (Playwright 1.64.1 `createGlobalSetupTasks`: plugin setup,
    then globalSetup; read in its runner on 3 Nov), so globalSetup cannot make the temp data copy the API serves. The API
    server's own command makes it: `node tools/run-api.mjs --port <api> --data <WT_TMP>/data --copy-data-from data`.
    globalSetup takes the Edge lock and checks the seed and `dist/offline` (WORK_BREAKDOWN S.9 had it make the copy too).
    `WT_SERVE` (`api`, `web`, `harness`) picks the servers: `harness` for `--project harness`, none on the prototype
    target, else `api,web`; `WT_SKIP_STORE_CHECK=1` skips the check (web specs against a mock API before the seed).
43. **Workspace `test` scripts name the root vitest config and their project** (`vitest run --config
    ../../vitest.config.ts --project viewer`, `... --project web`): vitest does not look for a config above its working
    folder, so a plain `vitest run` inside `packages/viewer` used vitest's defaults and ran the harness's Playwright specs
    (seen 3 Nov). Section 2 had `test` = `vitest run`; `npm run test:unit` from `app/` is unchanged.
44. **`@timed` checks retry through `timedDescribe`** (`tests/e2e/lib/fps.ts`: the tag, `test.describe.configure({
    retries: 1 })` and the frame rate attached after each test); the config's `retries` is 0. Playwright sets retries per
    config, project or describe block, not per tag (17.4 had `retries: 1` for specs tagged `@timed`).
45. **A third Playwright project, `scaffold`** (`tests/e2e/lib/smoke-*.spec.ts`), so the scaffold's prototype smoke is
    found by its own command; `e2e` stays `tests/e2e/*.spec.ts`, `harness` the harness specs (17.4 had two projects).
46. **The shadcn theme is written by the scaffold.** `shadcn add` (with `components.json` present) added the nine
    components and changed nothing else (no `baseUrl` to remove, no dependency changed), but writes no theme, and the live
    new-york-v4 style imports `shadcn/tailwind.css` from the CLI package. `apps/web/src/index.css` holds the theme of the
    registry's neutral base colour (`@theme inline`, `:root`, `.dark`, the base layer) without that import: the nine
    components use none of its custom variants, and the CLI stays a scaffold-only tool. `src/lib/utils.ts` is the
    registry's `utils` item (`export { cn } from 'cn'`).
47. **Two copies of `cn`.** The shadcn CLI 4.22.1 depends on cn 0.2.6, which npm hoists to `app/node_modules/cn`; the web
    app resolves its own `apps/web/node_modules/cn` 0.5.0 (checked). `check:pins` resolves each pinned package from the
    workspace that owns it and lists other copies as notes.
48. **tailwindcss and tw-animate-css are dependencies of `apps/web`** (4.1 says "web"; S.1's list left them out).
49. **Broken-corpus pointers** (`fixtures/models/broken/expected.json`, 5.6): a missing property is reported at its parent
    object (as ajv and jsonschema do), a duplicate at its later occurrence (`/openings/5/id`; the provisional checker in
    `docs/reference` names it `/openings`).
50. **OpenAPI details fixed with the routes** (frozen): nested models `VersionUrls`, `VersionDownloads`, `ErrorBody`; the
    raw-file routes (getModel, getStages, getAsset, getThumbnail) declare the `If-None-Match` header and a 304, and their
    `ETag`, `Cache-Control` and `X-Model-Stamp` headers; downloads declare `Content-Disposition`; PUT furniture-heights
    declares 422 as `ErrorResponse` or `HTTPValidationError`; downloadOfflineHtml takes `Depends(get_settings)`; health
    is in `routes/projects.py`, the shared parameters in `routes/params.py`.

Settled by the integration step (3 Nov 2026): every builder's contract issue, with what changed and what is read
differently from now on, is in `docs/contract-issues/I.md`. `contracts.ts` and the schema did not change; `models.py`
did once (`HeightsUpdate.heights` is `dict[str, StrictInt]`, E-2b), with `openapi.json` byte-identical. The fix step after
the four verifiers (3 - 4 Nov) and what it changed in behaviour (If-Match, the Max script's file name, the offline Reset
and key, the Host check, raster-only assets, three 0.160's transparent order and zoom) is in the same file, under
"Fix step (3-4 Nov)"; `contracts.ts`, the schema, `models.py` and `openapi.json` did not change there.

## 19. Risks

| Risk | Handling |
|---|---|
| three 0.160 -> 0.186: the replay's shader chunk names (`#include <begin_vertex>`, `<clipping_planes_fragment>`, `<common>`), OrbitControls and lighting may differ | the shader patch asserts each marker and throws a clear error; the prototype facts and screenshots of the same views (prototype vs app) are compared and differences reported at integration |
| three 0.186 triangulates with earcut 3.0.2, 0.160 with 2.2.4: 5 of the house's 197 outlines come out differently (1,029 cap triangles instead of 1,023, 36 more collider vertices); the bank, hotel and suite outlines are identical | known and counted (17.2): the house is checked against the r186 values, not the page's |
| three-mesh-bvh 0.8.3 -> 0.9.16 | per-mesh BVH; Node raycast tests in core and modes |
| Parallel builders in one package: interfaces only meet at integration | `contracts.ts` aliases checked by `contracts.test-d.ts`; working stubs; the scaffold's test context and the prototype-target e2e run let each builder test alone |
| Timed browser checks flake under software WebGL (10 - 20 fps), worse with six builders on one laptop | one Edge run at a time machine-wide (`tools/edge-lock.mjs`), `workers: 1`, `retries: 1` on `@timed`, the frame rate attached to each timed check (below 12 fps: re-run alone before diagnosing) |
| Provisional fixtures and E's converters disagree | deep-equality tests in E's pytest; each difference is a contract issue the integration step settles |
| The house's converted captions / texts must match the page character for character | the captured prototype facts are the oracle |
| The shadcn registry is live (not pinned by the CLI version); `cn` 0.5.0 is new | the scaffold adds the components once, re-pins with `npm install -E`, and `check:pins` verifies |
| FastAPI was released in a burst around 0.150.0 | API tests at the scaffold; fallback 0.142.4 recorded in CLAUDE.md if needed |
| happy-dom 21 is a new major | used only for DOM unit tests; browser behaviour is tested in Edge |
| Prototype pages need the CDN (jsdelivr) for the prototype target and the facts capture | the capture runs once in the scaffold; the prototype target has no network rule; if the CDN is down, builders skip the prototype target |
| Offline file size (about 0.7 MB of viewer code; the hotel about 2.5 MB with its two pictures as base64) | fine for meeting rooms; Meshopt and per-floor loading later (plan 6) |
| Saved heights race between two tabs | If-Match on the revision, a 412 merges this tab's changes (fix step) |
| A port collides with another session | per-builder ranges; every runner checks its port first |

## 20. Review notes (3 Nov 2026)

Two independent reviewers (parity: P1 - P18; engineering: E1 - E22) read this design against the prototypes, the plan and
the registries. Each finding was checked again before anything changed: in the prototype code (viewer_modes.js applyUrl /
openCam / lock / faceOpen, build_replay.js start-up / fadeLate / finish, furniture_boxes.js, the four generators, the test
files), by re-running the reviewers' scratch checks (earcut r160 vs r186, the `$'` replacement, openapi-ts from the root,
tsc 6.0.3 defaults, ajv strict, the Vite output path) and with new ones (v1 mesh and vertex counts with three 0.186.1;
the provisional models against the schema; their CSVs against the prototype CSVs). **All 40 hold up; none is rejected
outright.** Where a finding offered alternatives, or one part did not fit, the choice and the reason are below.

After the edits: `bank_test/previous_before_fix_round_2026-10-27/src/bank_model.json` (4b02dc17f286),
`bank_test/src/bank_model.json` (c3a9408304a2) and `hotel_test/src/hotel_model.json` (6ab030750886) validate against the
revised schema byte for byte with jsonschema 4.26.0 and with ajv 8.20.0 in strict mode (which compiles the schema now), with
0 cross-reference issues; the provisional suite, house and mini models validate too, and the furniture CSV of every
furnished model equals its prototype CSV byte for byte.

| Finding | Verdict | Changed |
|---|---|---|
| P1, E2 start-up order (`?cam=1` never reopens) | holds (openCam defers only when locked; lock(true) does not set camWanted) | 11.3, 11.4 step 8, contracts `ModesApi.applyAddress`, `ReplayApi.start` |
| P2 house meshes differ from the v1 rule | holds (ground colliders 7 vs 5, late 4 vs 2, plates 4 vs 2, glass 10 vs 8, plinths 3 vs 1) | 5.4, 14, 17.2 house values, 17.4 mesh classes, `TestHookHost.fitted` |
| P3, E3 (part) mini model not v1 | holds (16 schema errors; no openings for its approach ids) | 17.1 mini conversion, `docs/reference/provisional_v1.py` |
| P4 Tailwind preflight reaches the viewer | holds | 11.6 (`all: revert`), 15.6, 17.4 computed-style check |
| P5 `start('skip')` undefined | holds | 11.4, 11.5 (labels rule), contracts |
| P6 address edge cases | holds | 11.3 (`point`, build precedence), contracts `AddressOptions.point` |
| P7 `vh` below the app bar | holds | 11.6 (root-relative sizes, `@container`, `narrow()`), 15.3 |
| P8 furniture leniency misdescribed | holds | 5.6, 17.2 furniture, schema descriptions |
| P9 storage key presented as unchanged | holds | 11.2, 18.31, 17.4 (`@app-only`) |
| P10 ground plane fade | holds (`hide: [ground]`) | 5.4 item 5, WORK_BREAKDOWN D |
| P11 hotel viewer-level checks dropped | holds | 17.4 structure: railings, forecourt, lift doors, hatches, skins |
| P12 `nodownload=1` vs the photo checks | holds | 17.4 |
| P13 selectors and `Color` | holds | 11.6 map, 11.7, contracts `TestHookThree` |
| P14 facts the pages do not expose | holds | 17.1 capture methods |
| P15 the house's `frame` lost | holds | schema `floors[].sheetShift`, 5.1, 5.2, 6.4 |
| P16 `__pycache__` in `furniture/` | holds | 1, 2, 17.1 (`-B`, `PYTHONDONTWRITEBYTECODE`, system Python) |
| P17 slab side, house renderOrder | holds | 5.4, 8, contracts `PartStyle.renderOrder` |
| P18 faceOpen scores 23 headings | holds | 13 |
| E1 `$'` in `String.replace` | holds (reproduced) | 16, 17.3, 18.9 |
| E3 fixtures missing in the parallel phase | holds | 17.1 provisional models and presentation, 6.5, 17.2, 17.3 |
| E4 earcut 2.2.4 vs 3.0.2 | holds (5 of 197 house outlines; bank, hotel, suite identical) | 17.2, 19 |
| E5 shared Playwright output folder | holds | 3, 17.4 |
| E6 six Edge runs on one laptop | holds | 3 (Edge lock), 17.4, 19 |
| E7 throw after the DOM is touched; ref written in render | holds | 11.2, 11.4, 15.4, 17.4, contracts `testFailAt` |
| E8 fake-viewer alias needs a config | holds | WORK_BREAKDOWN S.6, F |
| E9 `gen:api` from the root; pip names | holds (exit 0 reproduced) | 2, 10.5 |
| E10 template output path | holds | 16, WORK_BREAKDOWN S, 17.3 |
| E11 TypeScript 6.0 defaults | holds (all four errors reproduced) | 4.4 |
| E12 `localhost` is `[::1]` | holds | 3 |
| E13 Playwright touch needs `hasTouch` | holds | 17.4 |
| E14 OrbitControls' own listeners | holds (three 0.186.1 source) | 11.4 step 2, 11.8, 17.4 |
| E15 unowned events and loop hooks | holds | 11.4, 11.5, contracts |
| E16 local mode loses a Reset | holds | 11.2, contracts `WriteStoredState` |
| E17 runtime `<style>` vs a strict CSP | holds (checked in Edge 156 by the reviewer) | 11.6, 15.6, 18.17, contracts `RootApi.addStyle` |
| E18 schema not ajv-strict; parser at run time | holds (reproduced) | schema (`type: object` on five maps), 5.6, 17.1 broken corpus |
| E19 docstrings move `openapi.json` | holds | 10.1 |
| E20 store seams for decision H | holds | 9.1, 9.3, 9.5, 10.1, 18.38 - 39 |
| E21 prototype target fails by design | holds | 17.4 (`@app-only`, no network rule) |
| E22 one shared issues file | holds | 18.0, 1, WORK_BREAKDOWN 0 |

**Alternatives not taken, and parts not adopted:**

* **P2's per-model merge option** (keep the house page's meshes and names through presentation): not taken. One grouping rule
  is simpler for every later model, and the difference is in draw calls and names only (vertex totals, Walk, the ticks and
  the replay are unchanged); the counts and a name map are written down instead.
* **P4's list of defaults** (`box-sizing`, `font-weight`, `list-style`, margins, one by one): replaced by one
  `all: revert` rule, which restores every browser default the pages relied on, including ones neither list names.
* **P8, porting test_boxes.mjs's "older" checks** (no approach, approach not a list): not ported. v1 requires `approach`
  (every real model has it; the seed writes it), so such a file never reaches the viewer; the prototype test keeps them.
* **E3, provisional suite and house stages:** not made. No builder needs them before integration once the house caption
  oracle is E's test (E converts the stages); a provisional copy would duplicate E's hardest port (the page's seven caption
  functions). The reviewer's "ship the architect's throwaway outputs" became the architect's conversion script, run by the
  scaffold against the live prototype files, so the fixtures carry `sheetShift` and the mini model too.
* **E6, two Edge slots with an exclusive lock for timed specs:** not taken; one Edge run at a time is simpler to get right
  and the timed checks need the machine to themselves anyway.
* **E17, allowing `'unsafe-inline'` for styles:** not taken for the viewer (the share page can then run a strict
  `style-src`); recorded instead for the staff app, whose Radix components add a runtime `<style>` themselves (15.6).
* **E19, comparing a normalised OpenAPI document:** not taken; explicit route texts keep the byte comparison, which also
  guards the generated client.
* **E20, making the Store async now:** not taken; plain `def` routes in FastAPI's threadpool give the same protection with
  no change to the store's shape.
* **The owner's instruction of 3 Nov** ("for the ratio, keep it strictly as the drawing said") stands as 18.27: the hotel
  model, its pictures and floor 2's furniture are used as drawn; nothing here rescales them.
