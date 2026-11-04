# Contract issues: builder C (viewer furniture and panel UI), 3 Nov 2026

Written only by builder C. The integration step settles each with the architect (DESIGN.md 18.0). None of them blocked C:
each is worked around inside C's own files, as said.

## C-1. Which ticks the panel shows: D-8 "Floor plates and Glass always" against `VisibilityApi.has()`

D-8 says "Ticks shown: Floor plates and Glass always; Room names when the model has rooms; Single-line items when it has
`single` parts; Plan picture when a floor has a picture". WORK_BREAKDOWN C says "ticks row from `ctx.visibility.has()`", and
contracts.ts `VisibilityApi.has` says "a tick without anything is not shown". C's `createPanel` shows a tick exactly when
`ctx.visibility.has(name)` is true, for all five, so the policy is A's `has()`. For the four projects both readings give the
same rows (checked against `fixtures/prototype/*.json` in `test/unit/ui/panel.test.ts`, on the kit's `has()`); they differ
only for a model without slabs or without glass. Suggestion: A's `has('plates')` / `has('glass')` return true (D-8), or D-8 is
reworded; no change in C either way.
Update (continuation, 3 Nov): A's `core/visibility.ts` `has()` now returns true for plates and glass and follows D-8 for the
other three, so the viewer shows D-8's ticks; the scaffold's test kit still answers from the tick lists (same rows for the
four projects). Nothing left to settle unless the kit should match.

## C-2. The underside of a piece on a chain of supports: furniture_boxes.js and furniture_kit.csv_text differ

D-13 "underside = support's base + support's height (no chains; depth < 3)". furniture_boxes.js (ported by C, for the boxes
and the viewer's `csv()` / `furnitureCsv`) takes the support's own resolved underside (recursive, at most 3 steps);
`furniture_kit.csv_text` (which E's `furniture_csv.py` ports) takes the support's KIND base. They agree whenever supports
stand on nothing, which every real model keeps (the four fixture CSVs, default and typed, are byte-identical to C's
`furnitureCsv`: `test/unit/furniture/logic.test.ts`). For a hand-made chain (a lamp on a printer on a table) the viewer's CSV
and the API's CSV would differ, and none of the D-5.6 rules refuses such a model. Suggestion: a 5.6 rule "an `on` support
has no `on` itself" (the API refuses, the viewer warns), or both sides on one rule. C keeps the prototype's.

## C-3. The panel's hiding rules sit in C's BASE_CSS (keyed on B's and D's root flags)

viewer_modes.js hid the side panel and the hint through body classes (`.vm-crowded .vm-panel`, `.vm-fp .vm-panel` /
`.vm-hint` on small screens, `.vm-camopen .vm-panel`; z-index 6 on both) and build_replay.js through `.br-on`. The panel
and the hint are C's elements, so C's BASE_CSS carries these rules on the root flags (`.wtv[data-crowded] .wtv-panel`,
`.wtv[data-replay] ...`, `@container wtv (max-width: 700px) or (max-height: 500px)` for fp / camopen). B and D may port the
same rules into their chunks: identical duplicates, harmless. Only the flags' names (contracts `RootApi.setFlag`) join them.

## C-4. Room labels: their CSS is in BASE_CSS, the elements are A's

The pages' `.room` rule (head CSS: C per D-12) is in BASE_CSS as `.wtv [data-wt=room]` (absolute, translate(-50%, -50%),
`display: none` until shown). A's `core/labels.ts` must create the labels as children of the root with `data-wt="room"` and
toggle them with `style.display`, positions root-relative (as the pages did with fixed positions). A may add its own chunk;
the same declarations twice do no harm.
Update (continuation): A's `core/labels.ts` does so and adds `LABELS_CSS` (the same rule plus `left: 0; top: 0`): consistent.

## C-5. The error box is shown through `hidden`

`createRoot` creates `[data-wt=error]` with `hidden = true`; BASE_CSS shows it (`display: block`) unless `[hidden]` (needed:
the root's `all: revert` keeps the user-agent `[hidden]` rule, but any author `display` would beat it). `ctx.reportError` (A)
should set `errorBox.hidden = false` and the text (`'Viewer error: ' + message`, the prototype's showErr), as the scaffold's
test context does. Setting `style.display = 'block'` instead works too (inline styles win).
Update (continuation): A's `core/context.ts` `reportError` does both; C's harness spec checks in Edge that the box is
`display: none` until reported and `block`, absolute in the root, with `Viewer error: <message>` after.

## C-6. FurnitureApi edge cases the contract leaves open

* `setHeights(h)`: "unknown kinds and bad values are ignored" (Viewer.setHeights) read as: a bad value counts as missing, so
  that kind goes back to the model's height ("the map replaces the typed set").
* `setHeight` / `setVisible` / `setBlocks` for a kind that has no pieces (no row): `false` (furniture_boxes.js threw a
  TypeError on its missing row).

## C-7. lib/walks.ts reads `__host.downHit` / `__host.rayHit`, which two prototype pages do not have

`installPageHelpers().topSpots` calls `__host.downHit` and `glassWalks` calls `__host.rayHit`; the suite's and the house's
prototype pages expose neither (only the bank and hotel pages have upHit / downHit / rayHit; the house has `cast`, the suite
nothing), so on `E2E_TARGET=prototype` they throw there. `tests/e2e/furniture.spec.ts` carries its own portable look-down,
top-spot and glass-walk helpers (`window.__fh`, raycasting `__host.FL[floor].colliders` with `__walkthrough.THREE`) and uses
walks.ts only for what works on all four pages. The house page also has no `__host.model`: the spec reads the model facts
from `fixtures/models/*.model.json` (the furniture is the same data on both targets). Scaffold kit, read-only for C: noted,
not changed.
Also: walks.ts `hoverSpots` is the bank / hotel / suite tests' version (every visible collider hides a box, glass included);
`cad_test/test_house_furniture.mjs` had its own (kinds asked in order, a grey box first, transparent glass hides nothing, after
`goHome()` back to the page's opening view). The spec ports the house's as `window.__fh.kindSpots` / `goHome` for the house
(with the house's numbers: 4 spots, the first an `other` box, a doorway box among the hovers) and uses walks.ts for the others.

## C-8. Names given where the selector map has none (information)

The map names `.fb-title span` (`furniture-title`) but not its container, the head row or the doorways label; C calls them
`[data-wt=furniture-titlebar]`, `[data-wt=furniture-head]`, `[data-wt=furniture-door]`. The ticks row (`#shows`) is
`[data-wt=shows]`, the floors row `[data-wt=floors]`, slots `[data-slot=<name>]`, the legend `[data-wt=legend][data-layout]`.

## C-9. The Playwright commands in `app/CLAUDE.md` need `--project=<name>` when a spec file follows (scaffold doc)

`npx playwright test -c tests/e2e/playwright.config.ts --project e2e tests/e2e/modes.spec.ts` (CLAUDE.md "Commands") fails
with Playwright 1.64.1: `--project` takes several names, so the file becomes a second project name ("Project(s)
"tests/e2e/furniture.spec.ts" not found", seen 3 Nov). `--project=e2e tests/e2e/<spec>.ts` works (the config's
`projectArgs()` reads both forms). C's specs say so in their header comments. Suggestion: the integration step fixes the two
example lines in CLAUDE.md.
