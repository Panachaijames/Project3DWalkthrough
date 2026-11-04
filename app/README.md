# Walkthrough application

The CAD-to-3D client walkthrough tool as a real application (foundation milestone, 3 Nov 2026): the 3D viewer as one
TypeScript package, the staff web app, and an API over a local file store seeded from the four prototype projects. The
design is in `docs/DESIGN.md`; agents read `CLAUDE.md` first.

| Folder | What |
|---|---|
| `packages/viewer` | `@walkthrough/viewer`: `createViewer(container, project)` and `dispose()`, framework-free (three.js bundled) |
| `apps/web` | `@walkthrough/web`: the staff app (React 19, React Router, TanStack Query, shadcn/ui on Tailwind) |
| `services/api` | the API (FastAPI) over `data/`, behind a storage interface |
| `data/` | the local store, made by `npm run seed` from the prototype folders |
| `dist/` | build outputs: `web/`, `offline-template/`, `offline/<project>-v<n>.html` |
| `fixtures/`, `tests/e2e/`, `tools/` | shared test fixtures, browser tests, scripts |

Status after the scaffold: the workspace, configs, stubs and test kit are in place; the viewer, the API bodies and the
web app's screens are built by the next steps (`docs/WORK_BREAKDOWN.md`). Nothing here deploys anything: it runs on this
computer only.

## Setup (once; already done on this machine)

Needs Node 24.14+ (npm 11), Python 3.14 and Microsoft Edge. From `app/`:

```
npm install                                   (PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1: the tests use the installed Edge)
python -m venv services/api/.venv
services/api/.venv/Scripts/python -m pip install -r services/api/requirements.lock.txt
npm run check:pins                            (every installed version equals the frozen list)
```

## Run the app (one command)

```
npm run seed                    (first time, and whenever the prototypes change: rebuilds data/; saved heights are kept)
npm run build:offline:template  (first time, and after a viewer change: the template the Downloads menu's offline file uses)
npm run dev                     (API on http://127.0.0.1:8710, web app on http://127.0.0.1:5710; Ctrl+C stops both)
```

Without the template the API answers the offline download with `503 offline_template_missing` (`npm run build` makes it
too).

Open http://127.0.0.1:5710 (use 127.0.0.1, not localhost). The API's own page is http://127.0.0.1:8710/docs.

## Tests

```
npm run typecheck   (strict TypeScript, five tsconfigs)
npm run test:unit   (vitest: viewer and web)
npm run test:api    (pytest)
npm run test:e2e    (Playwright in headless Edge; needs `npm run seed` and `npm run build:offline` first)
npm test            (all of the above)
```

Browser tests take a machine-wide lock (one headless Edge at a time); a run that waits says who holds it. They draw with
software WebGL (10 - 20 frames a second): a timed check that fails on a busy machine is run again before anything else.

## The offline viewer (one HTML file per project version)

```
npm run build:offline        (dist/offline/<projectId>-v<n>.html: opens from disk, no network)
```

The staff app's Downloads menu gives the same file with the furniture heights saved in the app. `npm run build` makes
everything: the type check, the web app (`dist/web/`) and the offline files.
