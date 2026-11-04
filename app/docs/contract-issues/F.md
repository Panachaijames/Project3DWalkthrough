# Contract issues: builder F (staff web app), 3 Nov 2026

Written only by builder F. The integration step settles each with the architect (DESIGN.md 18.0). None blocked F: each is
worked around inside F's own files, as said. F-1 is a gap in the API contract, F-5 a defect in the viewer's dispose when
the host detaches the container first (A's area); F-2 to F-4 are information for integration.

## F-1. The offline download cannot tell the page that the template is missing

`VersionDetail.downloads.offlineHtml` is a required `DownloadInfo` (never null), while `downloadOfflineHtml` answers
`503 offline_template_missing` until `npm run build:offline:template` has run (D-10.2). D-15.3 disables a download only
when its entry is null, so the app shows `Offline viewer (HTML)` as available and a click on its plain `<a download>`
ends in the browser's own failed-download notice (the app sees nothing: a download is not a fetch). Suggestion: the API
sets `downloads.offlineHtml` to null (or adds an `available` flag) when the template file is missing; the menu then
disables it as it does the others. F changes nothing until then (it shows the item as the contract says).

## F-2. Downloads made from the saved heights while a save is still pending (D-15.3, 15.5)

The CSV and the offline file are built by the API from the SAVED heights; the saver waits 600 ms of quiet before it
saves. A height typed and downloaded within that time (or while the PUT is in flight) would be missing from the file.
F's `DownloadsMenu` therefore sends a waiting save at once when the menu opens (`useHeightsSaver().flush`) and shows
`Furniture list (CSV)` and `Offline viewer (HTML)` disabled (`data-waiting`, tooltip `Waiting for the furniture heights
to be saved`) while the status is `Saving…`; they come back by themselves when the save lands. The Max script does not
depend on the heights (D-18.7) and never waits. An extension of D-15.3, not a change to any shared type.

## F-3. Two specs declared the same page global (tests/e2e, information)

`tests/e2e/tsconfig.json` includes every spec in one program, so `declare global { interface Window { ... } }` blocks of
different spec files merge. A's `leak.spec.ts` and F's first `web-leak.spec.ts` both declared `Window.__leak` with
different `LeakProbe` types (TS2717, then TS2339 on every use). F's spec now uses `__webLeak` / `WebLeakProbe`. Rule worth
keeping for later specs: page globals of a spec get a name unique across `tests/e2e`.

## F-4. Smaller readings of D-15 (information)

* `/projects` loader: `ensureQueryData(listProjectsOptions())` is started, not awaited, so the page itself shows the
  skeleton cards and the error Alert with Retry of D-15.2 (an awaited loader would keep the previous page on screen and
  turn a failure into the route's error page). A failed background refresh keeps the cards and shows the reason above them.
* `/projects/:projectId/v/:n` loader: besides `getVersion`, model and stages it reads `getProject`, because the version
  picker needs every version and `VersionDetail` has no list of them.
* `ViewerHost` has one prop beyond D-15.4's: `onCreated(viewer)`, an Effect Event like the other two, which the page uses
  to clear a failure once a viewer exists (StrictMode's second mount, or `Try again`); and one more effect (F-5).
* The project page memoises the `ViewerProject` on (projectId, version, stamp) as D-15.3 says, so a save (which updates
  the cached version detail's `overrides`) never re-creates the viewer. It also rebuilds it when the address query
  changes, because new options re-create the viewer anyway, and the loader has then read the detail again (from the
  cache every save updates): a viewer made for a new query starts from the heights saved meanwhile, not those of the
  first load.
* Web specs for F alone (no seed, no real API): a small mock API on 8726 (`apps/web/test/mock-api/server.ts`, behind the
  Vite proxy like the real one, so `<img>` thumbnails and `<a download>` downloads go the same way in both set-ups) over
  typed fixtures (`apps/web/test/mock-api/core.ts`, typed by `src/api/generated/types.gen.ts`), with `page.route` on top
  for the error cases. The mock has no suite or house stages (there are no provisional stages fixtures, D-17.1), so it
  reports `hasStages: false` for them; the seeded store has their converted replays.
* Playwright's own helper script in the page's main world (made by the first `page.waitForFunction`) adds capture
  listeners and `__playwright_global_listeners_check__` on `window` for the page's life; `web-leak.spec.ts` makes it
  before its baseline so they are not counted as the app's (A's `leak.spec.ts` may meet the same if it waits that way).

## F-5. dispose() after the host has detached the container leaves OrbitControls' document listener (A; D-11.8, 15.4)

Seen by `tests/e2e/web-leak.spec.ts` with the real viewer and E's API (3 Nov, 13:33): after every project page left, one
registration stayed, `document keydown capture` (three r186 OrbitControls' `_interceptControlDown`, holding the controls
and the camera). Version switches on a mounted page were clean; only an unmount leaked. Cause: React removes a page's DOM
from the document BEFORE it runs `useEffect` cleanups, so D-15.4's cleanup calls `viewer.dispose()` with the canvas
already detached; OrbitControls' `disconnect()` then calls `this.domElement.getRootNode().removeEventListener('keydown',
..., { capture: true })` on the detached subtree instead of the document. A's teardown order (controls before the root) is
right; the host simply detached first. Any host (Vue, a plain page replacing its body) can do the same, and D-11.2 says
dispose leaves nothing behind.
Work-around (F, `src/components/ViewerHost.tsx`): D-15.4's effect is unchanged; a `useLayoutEffect` cleanup (no deps,
unmount only) disposes the live viewer while the DOM is still in place, and the effect's cleanup then finds it disposed
(dispose is idempotent). Unit test: `ViewerHost.test.tsx` "on unmount disposes while its container is still in the
document". Suggestion for A: keep the canvas's root node from connect time (the document) and, in teardown, remove the
controls' capturing keydown listener from it when `!canvas.isConnected` (or call `controls.disconnect()` before anything
can detach), so `dispose()` is safe whatever the host did to the container first.
