# Contract issues: builder A (viewer core, assembly, offline), 3 Nov 2026

Written only by builder A. The integration step settles each with the architect (DESIGN.md 18.0). None of them blocked A:
each is worked around inside A's own files, as said.

## A-1. three 0.186's renderer holds a texture of its own: the dispose self-check of D-11.8 cannot reach 0 by itself

WebGLRenderer 0.186 gives every physically based material (MeshStandardMaterial: every wall, slab and box) a module-wide
DataTexture, the DFG lookup table (`src/renderers/shaders/DFGLUTData.js` `getDFGLUT()`, uniform `dfgLUT`), uploaded once
per renderer and never disposed by `renderer.dispose()` (three 0.160 had none). It is in no scene graph, so after the
traversal of D-11.8 `renderer.info.memory.textures` stays at 1 and the self-check warned `[viewer] dispose left 0
geometries and 1 textures` on every dispose (seen in Edge on all six harness fixtures). Worked around in `core/context.ts`
(`rendererTextures`): before the scene is disposed, the textures the renderer put in the materials' uniforms (read through
`renderer.properties`) are collected and disposed with them. Disposing the shared table frees it in every renderer that
uploaded it; a viewer still drawing on the same page uploads it again at its next frame (three re-uploads a texture whose
GPU copy was freed), so two viewers on one page are unaffected. Suggestion: note it in D-11.8 / risk 19 (three upgrades
may add more renderer-owned textures; the self-check would say so).

## A-2. `Presentation.accent` is required in contracts.ts; D-8 gives it a default

contracts.ts `Presentation.accent: string` (required) against D-8 "accent | Default `#2f6f8f`". `parsePresentation`
follows D-8 (behaviour): a presentation without `accent` parses and gets `#2f6f8f`; a present accent must be `#rrggbb`.
The five fixture presentations all carry one, so nothing differs today. Suggestion: `accent?: string` in contracts.ts, or
D-8 says "required". (A's own tests wrote presentations without it and needed the field to type-check.)

## A-3. Which ticks show: C-1 settled on A's side as D-8 says

`VisibilityApi.has()` returns true for `plates` and `glass` always (D-8 "Floor plates and Glass always"), and for `rooms`
when the model has rooms, `single` when it has single parts (a Single-line tick object), `picture` when a floor has a
plan picture sheet (pictureFrame and a picture URL). This answers C-1's suggestion; C's panel shows exactly `has()`.

## A-4. Room labels (C-4) and the error box (C-5)

`core/labels.ts` creates each label as a child of the root with `data-wt="room"`, text by `textContent`, shown and hidden
through `style.display`, positions root-relative, and adds its own CSS chunk with the same declarations as C's BASE_CSS rule
(plus `left: 0; top: 0`), so the labels look right with either. `ctx.reportError` sets the error box's text to
`'Viewer error: ' + message` (the prototype's showErr), `hidden = false` and `style.display = 'block'`, logs each distinct
message once and emits `error`.

## A-5. Things the contract leaves to A, and what A did (information)

* `ViewerContext` fields are `readonly`; `createContext` returns them as placeholders that throw a clear error when read
  before their init step (`[viewer] ctx.panel.el used before panel was installed`), and `viewer.ts` fills them in the
  order of D-11.4 (A's `CoreContext` type, writable, in `core/context.ts`).
* `LoopApi` has no "first frame" promise; A's loop adds `firstFrame` (not in the contract) for `Viewer.ready`.
* `window.__wtvMount` (`src/offline/mount.ts`): a mount / unmount helper the offline entry installs only with `?test=1`
  (and A's harness page always), used by `tests/e2e/leak.spec.ts` on the app target. Not part of the public API.
* The first `HeightsApi.apply` refits every fitted mesh (fit `top` / `clip`), at the model's own heights too, as the house
  page's `fitPieces` ran at every start-up (through the replay's applySettings); later applies refit only meshes whose
  wall height changed.
* `resolveOptions`: `build` = `options.build ?? address.build ?? (stages ? 'settings' : 'skip')`; without stages no
  replay is installed whatever `build` says (step 8a then runs `visibility.applyFloor()`).

## A-6. The e2e kit can only open the offline files in dist/offline (information)

`tests/e2e/lib/target.ts` (scaffold) builds the app target's URLs from `app/dist/offline`, which only the integration run
fills (`npm run build:offline` from the seeded `data/`). So that A could run its own specs on the app target before then,
`structure.spec.ts`, `offline.spec.ts` and `leak.spec.ts` read `WT_OFFLINE_DIR` and `WT_DATA_DIR` when set (defaults
`dist/offline` and `data`), and `packages/viewer/test/harness/core/make-e2e-offline.mjs` writes a hand-made store of the
five versions from the fixtures into `WT_TMP` and their offline files (no provisional stages exist for the suite and the
house, D-17.1, so there they have no replay; the checks that need the Build settings card say so and run at integration).

## A-7. Prototype pages without `__host.rayHit` (C-7, for the structure checks)

`lib/walks.ts glassWalks` reads `__host.rayHit`, which the suite's prototype page does not have: `structure.spec.ts` walks
at the suite's west glass with its own few lines (the prototype test's walk, generalised over `__host.probes`), which run
on both targets. The house page has `cast` only: the house checks use `cast` on both targets and classify hits with
`meshIs` (lib/target.ts), never by literal mesh names.

## A-8. Node and Python give the same offline file (information, for the integration's byte-equality test)

On 3 Nov (13:20 - 13:40) `scripts/make-offline.mjs` and E's `walkthrough_api.offline.offline_html` (run read-only through
`tools/run-py.mjs` on the same store and the same built template) gave byte-identical files for all six versions of A's
hand-made store (the hostile-names one included: `</script>`, `<!--`, `$'`, `$&`, `` $` ``, `$$` and both marker texts in
the names) and for all five versions of E's seeded `data/` as it stood at 13:04. The template in `dist/offline-template` is
still the scaffold's stub ("The offline viewer is not built yet."): `npm run build:offline:template` replaces it with the
real viewer (about 780 KB). A built its copies into `%TEMP%\wt-a`; one check of the script's command line with its default
arguments (13:21) wrote `dist/offline/*.html` from the seeded store and the stub template, and A removed that folder at once,
so `dist/` is as the scaffold left it.
