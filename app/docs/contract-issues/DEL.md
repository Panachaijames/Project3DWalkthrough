# DEL: delete a project, a version, a draft (12 Nov 2026)

The owner asked on 12 Nov 2026 for **Delete buttons in the staff app: delete a project, delete a version, delete a
draft**. The main session decided the design (two additive routes, version numbers never reused, the buttons and their
confirms) and authorised the two routes against `app/CLAUDE.md`'s freeze of the API's routes; this step built it on the
branch `deletes` (not committed: the main session reviews and commits). Nothing was deployed.

## 1. Contract changes (all additive)

| What | Change |
|---|---|
| `DELETE /api/projects/{projectId}` | new, operationId `deleteProject`, tag `projects`, 204 (no body). 404 `project_not_found`; 409 `busy` (details.builds: the drafts with a run going) |
| `DELETE /api/projects/{projectId}/versions/{version}` | new, operationId `deleteVersion`, tag `versions`, 204. 404 `project_not_found`, `version_not_found`; 409 `only_version`, 409 `busy` |
| `models.py`, `models_upload.py` | **unchanged**: both routes answer 204 or the existing `ErrorResponse`; no new response or error model was needed |
| `apps/web/openapi.json` | the two operations added; nothing else moved (`gen:api` run twice: the second run changed no byte) |
| `apps/web/src/api/generated/**` | regenerated: `deleteProject`, `deleteVersion`, `deleteProjectMutation`, `deleteVersionMutation` and their types added; every earlier exported symbol identical (the additive check) |
| `services/api/walkthrough_api/store/base.py` | the `Store` protocol gains `delete_project(project_id, check)` and `delete_version(project_id, n, check)`; constants `DELETED_VERSION_FILE = 'deleted.json'`, `DELETED_VERSION_FORMAT = 'walkthrough-deleted-version/1'`. No record changed |
| `services/api/tests/test_openapi.py`, `test_smoke.py`, `test_routes.py` | their frozen operation lists and route count gain the two (`DELETE_OPERATION_IDS = {deleteProject, deleteVersion}`; 37 -> 39 operations and routes) |
| `contracts.ts` (both copies), `upload-contracts.ts` (both copies), the schema | unchanged |

`node tools/check-openapi-additive.mjs` passes against both bases: `66b4c06` (37 old operations and 69 old schemas
unchanged; 39 operations now) and `9eb2d58` (13 old operations, 18 old schemas unchanged).

## 2. Behaviour (API and store)

**deleteProject.** Under the store's writers' lock: 404 when unknown; 409 `busy` while a run of one of the project's
drafts (a file reading or a build) is queued or running, "Wait for the build to finish (or cancel it), then delete the
project."; else the project's folder is renamed to `projects/.del-<8 hex>` (it leaves every listing at once: no project id
starts with a dot; a project made later with the same id starts empty) and then removed. The project's unfinished upload
sessions (`data/.uploads/`) go too. Shared things stay: the offices' layer memory (`data/mappings/`) and the converter's
cache. A seeded project can be deleted; `npm run seed` brings it back.

**deleteVersion.** Under the same lock: 404 when the project or the version is unknown (a deleted one answers
`version_not_found` "version <n> of '<project>' was deleted"); 409 `only_version` for the project's only version, "This is
the project's only version: delete the project instead."; 409 `busy` as above ("... then delete the version."). Else
`meta.json` is written first (the version leaves `versions`; `latestVersion` = the highest version left; `updatedAt` =
now), then `versions/<n>/` is swapped (the store's existing folder swap, `commit_version`) for a folder holding only
`deleted.json` `{format, version, label, stamp, deletedAt}`: the tombstone.

**Numbers are never reused.** `create_version` now allocates `max(latestVersion, every listed version, every numbered
folder under versions/ (tombstones included)) + 1` (was `latestVersion + 1`). Delete v2 of three: the next is v4. Delete
the latest (v3 of three): `latestVersion` drops to 2 and the next is still v4.

**A file held open.** On Windows a folder whose file is open (a download being sent) cannot be renamed. The store retries
for 5 s (as for every folder swap); then nothing has changed (for a version, `meta.json` is put back) and the API answers
409 `busy` "A file of this project is in use (a download being sent?): try again in a moment."

## 3. Decisions made here

1. **A draft and a deleted version (the smallest sound behaviour).**
   * An **open draft made from the version** ("Use the files of v<n> again", `from: {kind: 'version'}`) **keeps
     working**: its recipe was copied into its own `settings.json` when it was made, and its drawings are the project's
     uploaded sources, which a version delete does not touch. It reads, builds and saves as before (tested: saved as the
     next new number).
   * A **new draft from the deleted version** gets 404 `version_not_found` "version <n> of '<project>' was deleted". The
     Upload screen offers "Use the files of v<n> again" only for the latest version, which is never a deleted one, so the
     staff app never asks for it.
   * The **draft that was saved as the deleted version** (status saved, kept 7 days so that "Use the files of v<n>
     again" can be offered) **goes with it**, best effort after the version (it would only point at a version that is
     gone; the 7-day clean-up removes one that could not be removed then).
   * Drafts of a project are always deleted with the project.
2. **Where the buttons sit.**
   * Project list: a small trash button over the top-right corner of each card's thumbnail (`card-delete`, both card
     kinds), a sibling of the card's link, never inside it.
   * Project page: a quiet "..." icon button right after the version picker (`project-actions`) opens a menu with
     **Delete this version (v<n>)** (for the version on screen) and, below a separator, **Delete project** (red). Not
     next to New version, not a primary button. For the only version the version item is disabled and says "This is the
     project's only version: delete the project instead." (a disabled menu item shows no tooltip, so the text is in the
     item).
   * After a version is deleted the page opens the project's latest remaining version (the project read again first);
     after the project, the project list. Both replace the history entry of the page that is gone (Back does not lead to
     a Not found).
   * The Drafts (n) menu: each draft has a **Delete** beside it (`draft-item-delete`), the existing `deleteBuild`, the
     same confirm as the drafts list of a project with no version ("Delete this draft? Its uploaded files stay with the
     project."). The menu stays open, so a refusal shows its reason inside it; a draft whose run is going has its Delete
     disabled (the API would say run_in_progress).
   * A project with no version yet (its page lists its drafts): a quiet **Delete project** beside Back to projects.
3. **The confirm texts** (the browser's own confirm, as `DraftList`): "Delete <name>? Its <n> versions, <n> drafts and
   uploaded drawings are removed from this computer. This cannot be undone." (open drafts counted from listBuilds when
   the button is pressed; zero counts left out; "drafts" without a number when the list cannot be read) and "Delete
   version <n> of <name>? This cannot be undone. Version numbers are not reused." Cancel sends nothing.
4. **A refusal** shows the API's reason: on the card (under it), on the project page (an alert under the app bar with
   Close), in the Drafts menu.
5. **The seed and a tombstone.** `npm run seed` builds every seed-table version that is missing; a deleted **seeded**
   version is missing, so the seed brings it back under its own number with the same files (a restore of the seed
   table, not a reuse: the seed table fixes those numbers), as it brings back a deleted seeded project. A deleted
   uploaded version is never brought back (the seed does not know it), and its tombstone keeps its number taken.
6. **`updatedAt`** of a project becomes the time of a version delete (the project changed then; it moves up the list).
7. **Caches in the browser.** After a delete the app drops its cached answers for what is gone and any furniture heights
   this browser kept unsent for it (`heightsOutbox`), and reads the project list again.

## 4. Readers of version folders, checked with a tombstone present

| Reader | With a tombstone |
|---|---|
| The store (`list_versions`, `get_version`, every route) | reads `meta.json`'s `versions` only: the tombstone is never listed or read; `get_version` names it "was deleted" |
| The seed (`version_folders`, `uploaded_version`, `project_meta`) | counts only folders with a `version.json`; a deleted seeded version is rebuilt (decision 5); tested |
| `packages/viewer/scripts/make-offline.mjs` (`npm run build`'s offline files) | lists `meta.json`'s `versions`; its fallback (a meta.json without `versions`) now also skips a folder without `version.json` |
| Furniture heights, downloads, the offline download, the thumbnail | all through `get_version` / `latestVersion`: 404 for the deleted one; the thumbnail is the latest remaining version's (tested) |
| Drafts (`adopt.project_frame`, a run's `versionModel`, save's carried heights) | use the latest remaining version |
| `ProjectRedirect` | `latestVersion` is always a listed version |
| `tools/rooms/reference.mjs versions --check` | lists every file under `versions/`: after a delete it reports the version's files as missing and `deleted.json` as new, which is right for a "nothing changed since the milestone" check (it is not a reader of versions) |
| `tools/rooms/acceptance/**` (`version_rows.py`, `checks.py`) | read named versions of their own temp stores; nothing deletes there |

## 5. Files

Changed: `services/api/walkthrough_api/store/{base,local}.py`, `routes/{projects,versions}.py`,
`services/api/tests/{test_openapi,test_smoke,test_routes}.py` (the operation lists and the route count),
`packages/viewer/scripts/make-offline.mjs` (the fallback only),
`apps/web/src/components/{DraftsMenu,ProjectCard}.tsx`, `apps/web/src/pages/{ProjectVersionPage,ProjectRedirect}.tsx`,
`apps/web/test/mock-api/{core,builds}.ts` (the two routes in the mock; its saved versions numbered after every number
the project had), `apps/web/openapi.json`, `apps/web/src/api/generated/**` (generated).

Added: `services/api/walkthrough_api/deletes.py`, `services/api/tests/test_del_deletes.py`,
`apps/web/src/components/DeleteActions.tsx`, `apps/web/test/deletes.test.tsx`, `tests/e2e/deletes.spec.ts`, this file.

## 6. Checks (12 Nov 2026, ports 5749 / 8749, `WT_TMP=%TEMP%\wt-del`; `app/data` only read, by `npm run build`)

| Command | Result |
|---|---|
| `npm run check:pins` | ok (28 npm, 28 Python, the builder's 19, LibreDWG's 64 files) |
| `npm run typecheck` | 0 errors (the five tsconfigs) |
| `npm run test:unit` | **1044 passed** (91 files; 1033 before + 11 in `apps/web/test/deletes.test.tsx`) |
| `npm run test:api` (alone; `WT_TMP`, `WALKTHROUGH_DATA_DIR`, `WALKTHROUGH_CACHE_DIR` in the temp folder) | first run 2 failed, 574 passed: `test_smoke.py` and `test_routes.py` pin the 37 operations / routes; both now count the two new ones. Then **576 passed** (561 before + 15 in `test_del_deletes.py`) |
| `WT_INTEGRATION=1 npm run test:api` | **576 passed**, nothing skipped |
| `npm run gen:api`, then twice more | the first wrote the two operations; the next two changed no byte (sha1 of `openapi.json` and the 5 generated files) |
| `node tools/check-openapi-additive.mjs` / `--base 9eb2d58` | ok / ok |
| `npm run build` | ok (the offline template; 7 offline files from `app/data`, read only) |
| `make-offline.mjs` on a temp store with a tombstone, `meta.json` without `versions` (the fallback) | lists bank-sampeng v2 only and writes its file |
| `tests/e2e/deletes.spec.ts` + `web.spec.ts`, mock API (`WT_SERVE=web`, fake viewer) | **18 passed**, 3 skipped (the `@app-only` checks that need the real viewer, as in builder F's runs) |
| `tests/e2e/deletes.spec.ts` + `web.spec.ts`, the real API on a freshly seeded temp store and the real viewer | **21 passed** (2.7 min) |
| `tests/e2e/web-leak.spec.ts`, mock API | 3 passed (the project page's app bar changed) |

Not done here: `docs/DESIGN.md` (9.5's "n = latestVersion + 1", 10.2's route table, 15.2 / 15.3) and `docs/STATUS.md` still
describe the app before the deletes (this file is the record); the whole browser suite (`npm run test:e2e`) was not run,
only the specs above.
