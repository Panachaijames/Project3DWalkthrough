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
npm run test:builder (pytest in the builder's own Python: services/builder/tests)
npm run test:e2e    (Playwright in headless Edge; needs `npm run seed` and `npm run build:offline` first)
npm test            (all of the above)
```

Browser tests take a machine-wide lock (one headless Edge at a time); a run that waits says who holds it. They draw with
software WebGL (10 - 20 frames a second): a timed check that fails on a busy machine is run again before anything else.

## Uploading a drawing (the upload milestone, being built from 4 Nov 2026)

Staff make a project (or a new version of one), upload its DWG files (or DXF exported from AutoCAD), check the layer
roles, set up the floors, build, check and fix, and save a version that opens in the viewer with its downloads
(`docs/upload/DESIGN.md`). The screens: **New project** (`/projects/new`), **Upload** (`/projects/<id>/builds/new`) and
the **Build** page with its six steps, Files . Layers . Floors . Build . Check . Save (`/projects/<id>/builds/<buildId>`).
Until the milestone's builders finish, those pages say "not built yet" and the API's new routes answer 501.

What happens to a drawing:
* The upload goes up in 8 MiB parts and is stored once per project under its sha1 (`data/projects/<id>/sources/`, never
  served, never in git).
* A DWG is converted to DXF by LibreDWG (a separate GPL program in `vendor/`, see below) and checked: nothing lost (`ok`),
  only items moved to layer 0 (`minor`), or parts lost in conversion (`loss`: export a DXF from AutoCAD instead).
* The drawing is read once (layers, blocks, texts, level tags, grid labels, areas); the layer roles are suggested from
  the office's memory, the layer names and the contents (no AI), and staff confirm them.
* The build runs as its own process, one at a time on this computer, and writes the model, the replay, the top view,
  the 3ds Max script (live parts, never Editable Poly) and the check screen's overlay. Derived files (DXFs, readings) go
  to a cache outside the project (`%LOCALAPPDATA%\walkthrough\cache`, `WALKTHROUGH_CACHE_DIR`).

Setup for it (once; done on this machine by the milestone's scaffold on 4 Nov):

```
python -m venv services/builder/.venv                 (Python 3.14.3: the builder's own pinned environment)
services/builder/.venv/Scripts/python -m pip install -r services/builder/requirements.lock.txt
npm run vendor:libredwg -- --zip <path of libredwg-0.14-win64.zip>     (LibreDWG 0.14 from its GitHub release)
npm run check:pins                                    (now also the builder's pins and LibreDWG's files)
npm run test:builder                                  (the builder's own tests)
```

LibreDWG is GPL-3.0-or-later (`vendor/LIBREDWG-LICENCE.txt`): it only ever runs as a separate program, and the staff app
and the offline files never contain it. Its full licence text is fetched by the owner from gnu.org and recorded with
`npm run vendor:libredwg -- --add-licence <file>`.

## The offline viewer (one HTML file per project version)

```
npm run build:offline        (dist/offline/<projectId>-v<n>.html: opens from disk, no network)
```

The staff app's Downloads menu gives the same file with the furniture heights saved in the app. `npm run build` makes
everything: the type check, the web app (`dist/web/`) and the offline files.
