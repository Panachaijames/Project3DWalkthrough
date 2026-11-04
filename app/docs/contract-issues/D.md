# Contract issues: builder D (viewer build replay), 3 Nov 2026

Written only by builder D. The integration step settles each with the architect (DESIGN.md 18.0). None of them blocked D:
each is worked around inside D's own files (`packages/viewer/src/replay/**`, its tests), as said. D-1 and D-2 are defects
in shared files (the scaffold's kit and its docs); the rest record where the port differs from build_replay.js on purpose,
so that the integration step does not take them for drift.

## D-1. Playwright 1.64.1 reads `--project harness <path>` as two project names (CLAUDE.md's example commands)

`--project <project-name...>` is variadic in Playwright 1.64.1 (`node_modules/playwright/lib/program.js`), so
`npx playwright test -c tests/e2e/playwright.config.ts --project harness packages/viewer/test/harness/replay/` stops with
`Project(s) "packages/viewer/test/harness/replay/" not found` (seen 3 Nov). The same holds for the e2e example in
`app/CLAUDE.md` (`--project e2e tests/e2e/modes.spec.ts`). With the `=` form it works:
`--project=e2e tests/e2e/replay.spec.ts`, `--project=harness packages/viewer/test/harness/replay/` (the config's
`projectArgs()` reads both forms). D's spec headers use the `=` form. Suggestion: fix the two example lines in CLAUDE.md.

## D-2. The test kit shares one material per part kind across floors; the rise patch needs one per floor

`test/harness/context.ts` (scaffold) caches materials by part kind (`material(p.kind)`), so the walls of both bank levels
share one `MeshStandardMaterial`. The rise shader patch (build_replay.js: per rise item, uniforms of its own floor, the
floors rising one after the other) hands a material its floor's uniforms in `onBeforeCompile`: on a shared material the
second floor's walls would rise with the first floor's `uRise`. A's `buildScene` makes one material per mesh (as DESIGN
5.4 says), so the real viewer never shares. Worked around in `replay/index.ts`: a rise material already patched for
another floor is cloned for this floor (`ctx.disposer.track`), with the real build no clone is made. No change needed.

## D-3. Esc follows DESIGN 11.5, not the page-wide listener of build_replay.js (information)

build_replay.js skipped on Escape from any target (`addEventListener('keydown', ...)` on the window, typing or not).
D-11.5 has viewer keys count only on the page (body / document) or inside the root and not while typing
(viewer_modes.js `typing()`); the replay's Esc follows it, so the staff app's own controls keep their Escape. On the
prototype pages the only focusable things during the replay are the viewer's own, so the ported checks see no difference.

## D-4. Captions: one placeholder syntax for every step (information)

The bank page filled `{<key>level}` / `{<key>height}` only in the align and raise captions, the suite page only the first
`{level}` / `{height}` (`String.replace`). The viewer runs DESIGN 7.3's `fillCaption` on all seven captions. Same text for the
real data: the bank's captions at the default settings equal the captured facts (`test/unit/replay/timeline.test.ts`), the
suite's align and raise captions have one placeholder each (`pres2_stages.json`), the house's captions come from E's seed.

## D-5. Replay colours a stages file leaves out (information)

As on the pages, `colors` given in a stages file replace the line colours (a category it does not name stays ink: the
suite's stairs), over the replay's own ink, faint, piece, pieceEdge, run, runEdge (build_replay.js `Object.assign`). One
difference: a file whose `colors` has no `glass` made the prototype pass `undefined` to three.js (a console warning, white
glass pieces); the viewer uses DEFAULT_REPLAY_TEXTS' glass instead. No real file lacks it.

## D-6. The frame time of `tick(now)` (information)

`ReplayApi.tick(now)` takes the loop's time (the animation frame's timestamp), while `generate()` stamps
`state.last = performance.now()` as the prototype did. The first frame after Generate can carry a timestamp a little before
that stamp; dt is clamped to 0 ... 0.1 s (DESIGN 13 caps it at 0.1 s; the replay never steps back).

## D-7. CSS rules repeated in REPLAY_CSS (information, see C-3)

REPLAY_CSS repeats, for the Build card and the Build row only, the pages' `button`, `button.on`, `label` rules and
viewer_modes.js's `.vm-label` / `.vm-row` (the card used those classes), and C's `.wtv[data-replay]` rule that hides the
panel and the hint (build_replay.js `.br-on`). Identical declarations, so whichever chunk comes first, nothing changes.
