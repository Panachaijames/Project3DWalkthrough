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
| `npm run dev` | API on 127.0.0.1:8710 and the web app on 127.0.0.1:5710 together (Ctrl+C stops both) |
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
