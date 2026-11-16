# BX: delete one furniture box (16 Nov 2026)

The owner asked on 12 Nov 2026 to delete furniture boxes in the staff app (plan 2.5 "Editing the furniture boxes",
brought forward). The design is `docs/boxes/DESIGN.md` (final, cited BX-n here); its section "Decided by the main
session" settles the owner's four questions and authorises the additive contract changes this step makes. The step is
built on the branch `box-delete` by several builders, one part each, and is not committed (the main session reviews and
commits). Nothing was deployed. One section per part.

---

## 1. The server (`services/api`) and the generated client

Built: BX 3.1, 3.2, 3.4 (server side), 4 (the CSV and 3ds Max download filters; the offline file needs no server change),
5.1 (the carry-over in `create_version`, `source/carried-edits.json`, the seed's re-map, `--reset-overrides`), the main
session's decision 2 (the version detail's `carriedEdits`) and the API tests of 8.3. Ports API 8750, `WT_TMP=%TEMP%\wt-bx`
(`WALKTHROUGH_DATA_DIR`, `WALKTHROUGH_CACHE_DIR` under it); `app/data` only read.

### 1.1 Contract changes (all additive, authorised)

| What | Change |
|---|---|
| `models.py` | new `PieceEdit` (`removed: StrictBool \| None = None`, `extra='forbid'`: an unknown field is a 422, never silently dropped); `HeightOverrides.piece_edits: dict[str, PieceEdit]` (default `{}`; always in the answers, `{}` when none); `HeightsUpdate.piece_edits: dict[str, PieceEdit] \| None = None` (left out or `null`: the saved edits stay); new `CarriedEdits {from: int, notCarried: int}` and `VersionDetail.carried_edits: CarriedEdits \| None` (left out of the answer when None, pydantic's `exclude_if`: see 1.3, decision 1) |
| `store/base.py` | the record `HeightOverridesFile.piece_edits: dict[str, Any] \| None = None`, declared after `heights`, `OPTIONAL = ('pieceEdits',)`; `Store.write_overrides(..., piece_edits=None)`; `Store.download_bytes(project_id, n, name)` |
| `apps/web/openapi.json` | 2 new schemas (`PieceEdit`, `CarriedEdits`); `HeightOverrides`, `HeightsUpdate`, `VersionDetail` each gained one property that is not required; every `required` list unchanged; no `-Input` / `-Output` pair appeared (risk 2 did not happen); no operation changed (39) |
| `apps/web/src/api/generated/**` | regenerated (`npm run gen:api`): `types.gen.ts` gains `PieceEdit`, `CarriedEdits`, `HeightOverrides.pieceEdits?`, `HeightsUpdate.pieceEdits?: {...} \| null`, `VersionDetail.carriedEdits?: CarriedEdits \| null`; `index.ts` exports the two new names; the sdk and the TanStack Query helpers are unchanged |
| New error code | 422 `invalid_piece_edits` on `putFurnitureHeights` (an `ErrorResponse`; `details: {unknownIds: [the first 20, sorted], count}`); a malformed edit stays FastAPI's own 422 (`HTTPValidationError`), which the operation already declares |
| 412 `revision_conflict` | `details` = `{revision, heights, updatedAt}` as before, plus `pieceEdits` (the live map) **only when it is not empty**, so a store without edits answers exactly as before (`test_hardening.py:270` unchanged and green) |
| `contracts.ts` (both copies), `upload-contracts.ts`, `models_upload.py`, the schema, every route decorator | unchanged by this part |

`node tools/check-openapi-additive.mjs`: ok against `66b4c06` (37 old operations and 69 old schemas unchanged; of them
`HeightOverrides`, `HeightsUpdate`, `VersionDetail` gained optional properties, beside the rooms milestone's four) and
`--base 9eb2d58` (13 operations, 18 schemas unchanged; the same three grew); 722 / 299 previously exported symbols of
the client compared.

### 1.2 Behaviour

**The record** (`overrides.json`, the same file, revision, lock and If-Match as the heights):
`"pieceEdits": {"<piece id>": {"removed": true}, ...}` after `heights`. Written by the API in canonical form: model ids,
each value exactly `{"removed": true}` (built by hand in `LocalStore.write_overrides`, so a later optional field is
never written as `null`), closed, in the CSV order (floor in model order, kind in the kinds table's order, id). An empty
map is no key at all: a heights-only file is byte for byte as before (tested against `dumps_pretty` of the four keys).

**PUT** (`routes/furniture.py`, body only): the heights' checks first (422 `invalid_heights` as before), then, when
`pieceEdits` is sent, `piece_edits.canonical` (422 `invalid_piece_edits`; `removed: false` and `{}` dropped; closed;
ordered), then If-Match, then `write_overrides(..., piece_edits=...)`. Left out or `null`: the saved edits stay as they
are in the file. Every save is revision + 1, as before. A version without furniture still answers 404 `no_furniture`
first.

**Every reader takes the live map** (`piece_edits.live(model, saved)`: model ids only, `removed` exactly `true`, other
fields of an entry ignored, closed, ordered): GET, `getVersion`, the 412's details, the CSV, the Max script, the carry and
the seed. A hand-edited, odd or later step's file therefore never answers 500 and never hands the staff app an id its
next PUT would be refused for (tested: an unknown id, `"yes"`, `7`, `null`, `false`, an extra field). The GET reads the
model only when the file has edits. `pieceEdits` that is not a JSON object (a list) still fails the record, like any
other broken store file (500 `store_error`, as `test_routes.py`'s broken-store test expects of a broken `overrides.json`).

**CSV** (`furniture_csv.py`): `csv_text`, `model_csv_text`, `csv_bytes` take `removed` (a set); `ids` (the supports'
lookup) stays the whole list, only the rows are filtered; `None` or empty is the exact old path. Every box deleted: the
header alone (with the BOM).

**3ds Max script** (`routes/downloads.py`, body only): no live edits: the same `FileResponse` as before (bytes, ETag,
Last-Modified, headers; tested before and after a Restore all). Otherwise `Store.download_bytes` feeds
`piece_edits.filter_max_script(script, model.maxPrefix, removed)`, sent with `views.attachment_bytes` under the same
attachment name and media type. The filter works on the bytes: every line `^    <PX>_furnBox "<kind>" "<Max name>" <floor
index> "<id>" ` whose id is removed is dropped; each removed id must have exactly one line (none, two, or another prefix:
500 `store_error` "the 3ds Max script does not match its model: ..."); one comment line goes in as line 3 (line 2, the
stamp, unchanged), ending as line 1 ends (CRLF in every stored script): `-- 4 furniture boxes deleted in the walkthrough
app are left out: BB_L1_Furn_computer_002_..., ...` (the Max object names in the script's order, at most 30, then `, and
N more`; "1 furniture box ... is left out" for one). Every box deleted: `fn HL_furnAll =\r\n(\r\n)\r\n` (an empty body;
never run in real 3ds Max: risk 9). A model without a `maxPrefix` (the schema requires one) would be a 500 `store_error`.

**Offline file**: no change: `offline.py` embeds `overrides.json` as stored, `pieceEdits` included; tested in the
payload and Node = Python with edits (`make-offline.mjs` on the same store, the built template).

**Carry-over** (`LocalStore.create_version`, `piece_edits.carry`): with `carry_overrides_from` (the save's
`carryHeights`), beside `carry_heights` (untouched): the old version's model is read through the store and checked
against its `modelSha1`; only the TOPS of its live map are carried (a removed piece whose support is not removed); a top
P is carried to the new piece Q when floor, kind and family are equal, the drawing-frame centres (x, y + offset) are within
10 mm on each axis, w and d within 10 mm, the turns within 0.5 degrees modulo 180 (modulo 90 when both are square, w - d
under 1 mm), Q is P's only match, P the only old piece (removed or kept) matching Q, and no other carried top claimed Q.
The carried tops are closed in the new model ("cascaded"). `overrides.json` (revision 1) is written when the carried
heights or the carried edits are not empty; `source/carried-edits.json` whenever the old version had live edits:
`{"format": "walkthrough-carried-edits/1", "from": <n>, "carried": {"<old id>": "<new id>"}, "cascaded": ["<new id>"],
"notCarried": [{"id", "floor", "kind", "family", "why"}]}` (the old ids in the old CSV order).

**The version detail's note** (decision 2): `carriedEdits: {from, notCarried}` on `getVersion` (and on `saveBuild`'s
answer, a `VersionDetail` too) when `source/carried-edits.json` lists at least one deleted box that did not carry; absent
otherwise. The staff app's line: "`notCarried` deleted boxes of v`from` are back: not found in the new drawing".

**Seed** (`seed/build.py`): `--force` keeps `overrides.json`, edits included. In the commit phase, under
`store.exclusive()` and before any folder is swapped, every rebuilt version whose `modelSha1` changed and whose kept file
has `pieceEdits` is re-mapped (`remap_piece_edits`): the old live edits carried into the new model as above, written into
the staging folder as `overrides.json` (heights as they were, revision + 1, `updatedAt` now) and
`source/carried-edits.json`; one log line per version ("sukhumvit-house v1: the model changed: deleted furniture boxes
re-mapped, 1 carried, 0 with them, 1 not carried (source/carried-edits.json)"); `SeedResult.remapped` lists them.
`--reset-overrides` drops the edits with the heights (the re-map is skipped). Help text, the module docstring and
`README.md`'s seed line updated.

### 1.3 Decisions made here (differences from, or additions to, the design)

1. **The note's field**: `VersionDetail.carriedEdits: {from: int, notCarried: int}` (`notCarried` = the length of the
   record's `notCarried` list), present only when it is 1 or more. It is left out of the JSON when None through pydantic
   2.14's `Field(exclude_if=...)`, which changes nothing in the schema (still an optional `anyOf [CarriedEdits, null]`)
   and so keeps `test_routes.py`'s `set(d) == DETAIL_KEYS` pin and every mock as they are. It is read from
   `source/carried-edits.json` through the existing `Store.version_file_path` (no new protocol method: the smallest
   change; a URL-backed store must make that file readable through it, as it already must for the worker's version
   model), leniently: a missing or odd record only loses the note.
2. **`pieceEdits: null` in a PUT is "left out"** (keep): the request model cannot tell them apart without more code, and
   the staff app never sends `null`.
3. **422 `invalid_piece_edits`**: `unknownIds` are sorted before the first 20 are taken (as `invalid_heights` sorts
   `unknownKinds`); the message lists them and ends "and N more" past 20. Any key that is not a model piece is refused,
   whatever its edit (`removed: false` included).
4. **Old dependents in the carry**: "an old dependent that the new closure did not add back" is one for which no new
   piece matching it (the fingerprint, without the one-to-one rule) is removed in the new version; that includes a
   dependent with no match at all. Its `why` is always "was on a deleted support", so `notCarried` lists every old
   deleted box whose deletion did not carry. The `why` texts: `no match`, `<k> matches`, `matches <k> old pieces`, `was
   on a deleted support` (k = 2 or more).
5. **carried-edits.json** is written when the old version's LIVE map is not empty (a file holding only odd entries counts
   as no edits), and its name is reserved: `create_version` refuses a draft whose own `source` holds
   `carried-edits.json` (ValueError; no draft does).
6. **The carry reads the old model checked against its `modelSha1`**: a model changed on disk fails the save (500
   `store_error` through `saveBuild`, like every route), rather than mapping deletions against the wrong pieces. A broken
   old `overrides.json` failed the save before this step too.
7. **The seed's re-map** runs as a pre-pass over all rebuilt versions before the first swap, so a re-map that cannot run
   (the old `model.json` unreadable while edits need it) stops the seed with nothing changed (SeedError, "nothing was
   changed"). It runs when the model changed and the kept file has any `pieceEdits` at all (odd entries included), so an
   entry that was not live against the old ids can never become live against the new ones (it is dropped). With the
   model unchanged, an earlier `source/carried-edits.json` is copied into the rebuilt folder (else `--force` would lose
   the record and its note). The `from` of a seed re-map is the version's own number (its previous build). An
   `overrides.json` that does not parse is left to `commit_version` as before.
8. **`write_overrides(piece_edits=None)` keeps the saved map exactly as stored** (odd entries included): the store does
   not know the model; readers filter.
9. **The test of "every model piece has exactly one Max line"** runs on the seeded BB v1 / v2, PS and HL and, read only,
   on the owner's TB and PSL in `app/data` when they are there (else those two are left out). A one-off read-only run of
   the same check over every stored script of `app/data` (6) and of the acc-9nov copy (12: BB, HL, PS, PSRE, SK, TW) passed.
10. **The shared closure cases** (`packages/viewer/test/fixtures/furniture/close-removed.cases.json`, the viewer part's):
    `test_close_removed_against_the_viewers_case_file` reads `{"cases": [...]}` or a bare list; each case needs its
    pieces (`pieces`, `[{id, on}]`), the ids removed (`ids`) and the closed result (`closed`, compared as a set); the
    reader also accepts `removed` / `input` for the ids and `expected` / `want` for the result. Missing file: skipped in a
    plain run, failing under `WT_INTEGRATION=1` (the repository's rule for a missing piece), so the cross-language check
    can never be skipped silently once the parts are together. The Python rule keeps the ids it is given as they are
    (callers pass model ids only).
11. **Odd kept edits and a changed model in the seed**: when the kept `pieceEdits` name no live box of the old model, the
    re-map drops them (revision + 1, no `carried-edits.json`, the log line "... its saved piece edits named no deleted
    box of the old model: dropped").

### 1.4 Frozen texts that now under-describe the behaviour (risk 12)

They cannot change additively; DESIGN 18.7 is the place to say so.

* `putFurnitureHeights`: "Save the furniture heights", "Replaces the saved map. Every key must be a kind of the model
  ..."; its 422 text names `invalid_heights` only (now also `invalid_piece_edits`).
* `getFurnitureHeights`: "The kinds whose saved height differs from the model's"; `getVersion`: "... the saved furniture
  heights".
* `downloadMaxScript`: "The version's .ms script byte for byte as seeded" (true only while no box is deleted).
* `downloadFurnitureCsv`: "With no saved heights it equals the prototype CSV byte for byte" (and no deleted box).
* `downloadOfflineHtml`: "with the saved heights" (and the deleted boxes).
* `SaveBuildRequest.carryHeights` (`models_upload.py`): "Copy the latest version's saved furniture heights ..." (the one
  flag now carries the deleted boxes too).
* The store's `RevisionConflict` message: "the saved heights are at revision ...".
* Built texts that stay as built (BX 2.7, DESIGN 13; the owner accepted the intro, decision 4): `version.json`'s counts,
  the project card's furniture count, the presentation intro, the replay captions, the top view.

### 1.5 Rollback warning (risk 10)

`Record` is `extra='forbid'` at the top level: code from before this step cannot read an `overrides.json` holding
`pieceEdits` (500 `store_error` on that version's furniture heights, `getVersion`, CSV and offline file, and the seed's
`project_meta` stops). Before rolling the code back, Restore all on every version with deleted boxes (that empties the
key) or remove the key by hand.

### 1.6 Files

Changed: `services/api/walkthrough_api/{models,views,furniture_csv}.py`, `store/{base,local}.py`,
`routes/{furniture,downloads}.py` (bodies and module docstrings only), `seed/{build,__main__}.py`,
`services/api/tests/test_routes.py` (the two `overrides` pins: `pieceEdits: {}`), `apps/web/openapi.json` and
`apps/web/src/api/generated/{index,types.gen}.ts` (generated), `README.md` (the seed line).

Added: `services/api/walkthrough_api/piece_edits.py` (pure: `close_removed`, `order`, `live`, `canonical`, `carry`,
`carried_record`, `carry_into`, `carried_note`, `filter_max_script`, `max_script_ids`),
`services/api/tests/test_bx_piece_edits.py` (31 tests), this file.

### 1.7 Checks (16 Nov 2026, alone; `WT_TMP=%TEMP%\wt-bx`)

| Command | Result |
|---|---|
| `npm run test:api` before any change | 576 passed (4 min 41 s) |
| `test_bx_piece_edits.py` alone | 30 passed, 1 skipped (the viewer's case file does not exist yet) |
| `npm run test:api` | **606 passed, 1 skipped** (4 min 20 s; 576 + 31 new; the skip is the case file above) |
| `WT_INTEGRATION=1 npm run test:api` | 605 passed, **1 failed** (5 min 08 s): `test_close_removed_against_the_viewers_case_file`, the case file missing (under the flag a missing piece fails); it was run before the 31st test was added, and the test file alone under the flag then gave 30 passed and the same 1 failed. It passes once the viewer part writes the file in the shape of 1.3, decision 10 |
| `npm run gen:api`, then again | the first changed `openapi.json`, `index.ts`, `types.gen.ts`; the second changed no byte (sha1 of `openapi.json` and the 17 generated files) |
| `node tools/check-openapi-additive.mjs` / `--base 9eb2d58` | ok / ok (also inside `test_ur_api.py`) |
| `npm run typecheck` | 0 errors (the five tsconfigs, with the regenerated client) |
| read-only one-off: every stored `.ms` of `app/data` and of `%TEMP%\wt-r0\acc-9nov` | 18 scripts (BB, HL, PS, PSL, TB; BB, HL, PS, PSRE, SK, TW): one furnBox line per model piece, the filter right on each |

`npm run test:builder` was not run: this part changed nothing it runs.

### 1.8 For the next parts

* The answers: `HeightOverrides.pieceEdits` is always sent (`{}` when none), although the generated type marks it
  optional (a defaulted field is not required): read a missing one as `{}`. The 412's `details.pieceEdits` is there only
  when not empty. `VersionDetail.carriedEdits` is there only when some deleted boxes did not carry over.
* A PUT without `pieceEdits` keeps the saved edits; `{}` clears them; the answer is the canonical (closed, ordered) map,
  which can differ from the map sent (the closure).
* The mock API's CSV with edits is its golden minus the rows; its Max script, if it filters, is the stored script minus
  the lines plus the line-3 comment above.
* `close-removed.cases.json`: the shape in 1.3, decision 10.

### 1.9 Not done here

DESIGN 9.4, 10.2, 13, 15.3, 16, 18.7 and STATUS (the main session's housekeeping, BX 8.8); `app/CLAUDE.md`'s command
table still says "saved heights kept unless `--reset-overrides`" for `npm run seed` (not this part's file); the filtered
script and an empty `furnAll` body have not been run in real 3ds Max (risk 9: the 3D team).

---

## 2. The viewer (`packages/viewer`) and the TypeScript contracts

Built: BX 3.3 (both `contracts.ts` copies, byte-equal), 2.1 - 2.8 on the viewer side, 4's viewer CSV filter and
`offline/entry.ts` `projectOf`, 5.2, and the viewer tests of 8.2. Ports web 5750, `WT_TMP=%TEMP%\wt-bx`. `app/data`,
`src/modes/**`, `apps/web/src/**` and `services/**` were not touched.

### 2.1 Contract changes (additive, authorised; `docs/contracts.ts` = `packages/viewer/src/contracts.ts`)

| What | Change |
|---|---|
| new | `PieceEdit { removed?: true }`, `PieceEditMap = Record<string, PieceEdit>` |
| `HeightOverridesFile` | `pieceEdits?: PieceEditMap` |
| `ViewerProject` | `pieceEdits?: PieceEditMap \| null` |
| `ViewerOptions` | `editBoxes?: boolean` (default false) |
| `ResolvedOptions` | `editBoxes?: boolean`, optional, read as `=== true` (the scaffold's `test/harness/context.ts` is untouched and typechecks) |
| `ViewerEvents` | `boxeschange: { pieceEdits; source: 'removed' \| 'restored' }` |
| `InternalEvents` | `pieces: { pieceEdits; source: 'removed' \| 'restored' \| 'api' }` |
| `Viewer` | `getPieceEdits(): PieceEditMap`, `setPieceEdits(e): void` |
| `FurnitureApi` | `pieceEdits()`, `setPieceEdits(e)`, `removePiece(id): string[]`, `restorePiece(id): string[]`, `restoreAll()` |
| `FurniturePieceView` | `removed?: true` (only on a deleted box) |
| `FurnitureKindView.count` | the comment: the kind's live pieces |
| `FurnitureCsv` | `(model, heights, removed?: ReadonlySet<string>) => string` |

`StoredFurnitureState`, the storage key and every other type are unchanged. `node tools/check-openapi-additive.mjs` still
says the two copies are equal. The three typed literals got their new members: `test/unit/core/viewer-events.test.ts`,
`test/unit/replay/replay.test.ts` (`fakeFurniture`, D's, authorised) and `apps/web/test/fake-viewer.ts` (**stubs only**:
`pieceEdits: () => ({})`, the writes do nothing; the staff-app part completes the fake).

### 2.2 What was built (files)

| File | What |
|---|---|
| `src/furniture/types.ts` | `ItemState.removed`; `UndoEntry`, `EditEvent`; `FurnitureState`: `editBoxes`, `legendKinds`, `liveCount`, `removedIds`, `groups`, `undoTop`, `restoredAll`, `onEdit`, `select`; `LegendActions`: `removePiece`, `restorePiece`, `restoreAll`, `undo` |
| `src/furniture/logic.ts` | `furnitureCsv(model, heights, removed?)`; `closeRemoved`; `groupsOf`; `removedIdsOf` (the lenient read of an edits map) |
| `src/furniture/boxes.ts` | `syncKind` hides a deleted box and keeps it out of the colliders (third parameter: the replay is running); `setRemoved` (the `late` list); `restoreLook` |
| `src/furniture/pick.ts` (new) | the pick taken out of `hover.ts`: `rootPoint`, `atRoot`, `atClient`, `atCentre(reach)`; `showing` |
| `src/furniture/hover.ts` | uses `pick.ts`; with `editBoxes`: the line `[data-wt=furniture-tip-hint]` "Click to select", the pointer cursor, no label while the card is open |
| `src/furniture/select.ts` (new) | the Orbit click, the Walk / Ghost aim, the marker, the card, the line at the bottom, Delete / Ctrl+Z / Esc with the arming, when the selection clears, the photo guard (2.3, decision 2) |
| `src/furniture/restore.ts` (new) | the legend line and the Restore list (the design allowed `legend.ts` or `restore.ts`) |
| `src/furniture/legend.ts` | live counts, `data-empty`, the edit hint, the place of the restore line, the live Keep doorways tooltip, rows from `legendKinds` |
| `src/furniture/css.ts` | card, list, line at the bottom (z 7), the legend lines, `data-empty` |
| `src/furniture/index.ts` | the starting edits, `stops` with `!removed`, the one function every change goes through (`setRemovedIds`: closure, `late`, colliders, legend, undo stack, bus `pieces`, the listeners), the actions and the API, live `kinds().count`, `pieces().removed`, `csv()` with the removed set, the client's legend |
| `src/viewer.ts` | `bridgeEvents` (`pieces` removed / restored -> `boxeschange`, a copy of the map), `guardFurniture` (the five members), `Viewer.getPieceEdits` / `setPieceEdits` |
| `src/core/context.ts` | `resolveOptions`: the `editBoxes` key only when the option is exactly true; the storage key unchanged |
| `src/offline/entry.ts` | `projectOf` adds `pieceEdits` only when the payload's `overrides` has it |

Tests: `test/unit/furniture/remove.test.ts` (new, 28), `select.test.ts` (new, 28), `logic.test.ts` (+7: the CSV filter,
`closeRemoved` against the case file, `groupsOf`, `removedIdsOf`), `install.test.ts` (pins unchanged, +1), `core/
viewer-events.test.ts` (+1 and the guard), `core/context.test.ts` (+1), `testhook/hook.test.ts` (+1; the pin at
`:122-123` unchanged), `test/fixtures/furniture/close-removed.cases.json` (new, 15 cases, the shape of 1.3 decision 10;
its row in that folder's README), `test/harness/furniture/furniture.spec.ts` (+6 cases; the page takes `?edit=1`) and
`test/harness/furniture/box-delete.spec.ts` (new, 3 cases on the real viewer: decision 12).

### 2.3 Decisions made here (differences from, or additions to, the design)

1. **The marker follows its box without a frame hook.** Modules may not register frame hooks (`contracts.ts`, `LoopApi`),
   so "every frame while something is selected" is done by the marker's two parts' own `onBeforeRender` (three calls it
   before it computes the part's model-view matrix), which copies the selected mesh's world matrix; the parts are never
   frustum-culled and never ray-cast. The marker is also placed at once on select, on a typed height (bus `furniture`)
   and on the Build settings (bus `settings`).
2. **No photo shows the marker** (not in the design; found while building). P takes a photo in Orbit and in Walk without
   the Camera panel, so a selected or aimed box would have been in staff's photos with a magenta box around it. A photo
   (`modes/photo.ts`, whatever started it: P, the shutter, `Viewer.takePhoto`, `?shot=1`) draws the scene itself and
   first sets the drawing buffer's pixel ratio; nothing else does but a resize. `select.ts` therefore wraps
   `ctx.renderer.setPixelRatio` on the instance (given back on dispose): the marker hides from that call until the next
   turn of the event loop. Nothing in `src/modes/**` changed. Tested with the real `createPhotos` on the fake renderer
   (every render of the photo sees the marker hidden) and in the browser (a 1920 px photo has 0 magenta pixels while the
   screen has them, for `takePhoto()` and for the P key). If `photo.ts` ever stops setting the pixel ratio first, those
   two tests fail.
3. **The Walk / Ghost aim** is looked for every 100 ms by a timer of the disposer while the mode is Walk or Ghost (started
   from bus `mode`, it ends itself), and **once more on the Delete key press itself**, so the box deleted is the one under
   the crosshair at that moment. It takes the nearest thing on the centre ray within 6 m: a wall in front of a box hides
   it, as in Orbit.
4. **Delete ignores a held key** (`repeat`) and any Ctrl / Cmd / Alt combination, so a key held down in Walk cannot
   delete a row of chairs. **Ctrl+Z** is also Cmd+Z, never Ctrl+Shift+Z, and does nothing while the replay runs. **Esc**
   acts only in Orbit (in Walk and Ghost it is the modes' own "back to Orbit", which clears the aim).
5. **Arming**: one `pointerdown` listener on the window, capture phase, reads the event's first path element: the canvas
   or inside the card arms Delete, anything else (the panel, the Restore list, the host page) disarms it. In Walk the
   arming press is the click that starts walking; a walk started from the panel's Walk button needs one click on the
   canvas before Delete works. Ctrl+Z needs no arming.
6. **Undo** is a stack of `{ids, dir, all}`; an undo is not itself an undo step (no redo). The card's Undo is shown only
   while its own step is the top of the stack (a second delete, an undo by key or a `setPieceEdits` hides it).
   `setPieceEdits` **always** says bus `pieces` source `api` and clears the stack and the "All n boxes are back" line,
   also when the map it was given equals the current one (as `setHeights` always says `api`).
7. **Texts added to the design's**: "1 box deleted · ", "1 box is back · " (the design gives the plural only);
   "1 piece stands on it (Computer / monitor): it is deleted with it." for one; the kinds in that line are the distinct
   kind labels of the live pieces on the box; "Deleted: 5 boxes" for the undo of a Restore all; after an undo the line at
   the bottom has no "· Ctrl+Z to undo" (there is nothing more to undo for it). Restore all shows no line at the bottom
   in Walk: the legend line says it. The card's third line is `w × d × h m · <floor>, from <z0> m` (floor first, as the
   design wrote it; the hover label has the two the other way round and stays as it is).
8. **The client's legend** (`editBoxes` off): the rows and the Keep doorways tick are decided when the file loads. The
   label count is live in both modes (it equals the piece count when nothing is deleted); `data-empty` is set whenever
   it is 0. The master "show" tick follows the kinds that have a row. A file in which every box is deleted shows the
   legend's title, note and buttons with no row.
9. **While the build replay runs** (`ctx.replay.phase` is `settings` or `play`) a change of the deleted set (only
   `setPieceEdits` can happen then) updates the state, the colliders and the `late` lists at once and hides a box that
   is now deleted; a box that is back is left to the replay's fade and its closing `apply()`. `apply()` also gives a
   kind whose every box is deleted its two materials' own look back (`restoreLook`): with no mesh of it left in a `late`
   list, a replay that was fading when the last one went would otherwise leave them half transparent for a later
   restore.
10. **Reads are lenient everywhere in the viewer** (`removedIdsOf`): `project.pieceEdits` and `setPieceEdits` take any
    value; only an entry that is an object with `removed` exactly `true` and whose id is a piece of the model counts.
    `closeRemoved` itself keeps the ids it is given (as the Python rule); the callers filter. `projectOf` passes
    `overrides.pieceEdits` as it is.
11. **Names added** (`data-wt`) beside the design's: on the card `box-kind`, `box-family`, `box-size`, `box-note`,
    `box-id`, `box-cascade`, `box-buttons`, `box-back`, `box-back-kind`; in the list `boxes-restore-head`,
    `boxes-restore-close` (the ×), `boxes-restore-list`, `boxes-restore-row` (with `data-id` = the group's top),
    `boxes-restore-what`, `boxes-restore-foot`. The list closes when the replay starts; the card and the line at the
    bottom are hidden under the root's `data-replay` flag.
12. **A second harness spec on the real viewer** (`test/harness/furniture/box-delete.spec.ts`), beyond the design's list:
    the furniture harness page has no modes, replay or photos, and the unit tests run on the kit's stub modes, so Walk,
    the crosshair, the replay and the photo were otherwise only the staff-app browser spec's to find. It mounts
    `createViewer` on A's core harness page (read only, `?nomount=1`, `__wtvMount.mount({ editBoxes: true })`).
13. **`ResolvedOptions.editBoxes`** is present only when the option is exactly `true` (no `false` key), so nothing that
    compares resolved options changes.

### 2.4 For the staff-app part and the browser spec

* `createViewer(el, project, { editBoxes: true })` with `project.pieceEdits` = the saved (or unsent) map; listen to
  `viewer.on('boxeschange', ({ pieceEdits, source }) => ...)` (the whole map, a copy, in the furniture list's order);
  `viewer.getPieceEdits()` for the count at mount; `viewer.setPieceEdits(map)` for a takeover, a merge or the server's
  answer (no event comes back, the undo stack is cleared).
* A key reaches the viewer only when its target is the body, the document or inside the viewer's root, and never while a
  text box has the focus. Delete needs the last `pointerdown` to have been on the canvas or the card.
* In a browser test: `__host.furniture.removePiece(id)` / `restorePiece(id)` need no arming; a restored box becomes the
  selection in Orbit when it is showing; the marker is `scene.getObjectByName('furniture-selection')` (`.visible`), the
  scene being `__host.floors[0].group.parent`.
* The fake viewer's five `FurnitureApi` members and `getPieceEdits` / `setPieceEdits` are stubs.

### 2.5 Checks (16 Nov 2026; `WT_TMP=%TEMP%\wt-bx`, web 5750)

| Command | Result |
|---|---|
| `npm run typecheck` | 0 errors (the five tsconfigs) |
| `npm run test:unit` | **1111 passed** in 93 files (both projects; the viewer project alone: 712 in 52 files) |
| `walk-parity.test.ts` alone | 10 passed (the golden untouched) |
| harness `furniture/furniture.spec.ts` | **24 passed** (18 of before, 6 new) |
| harness `furniture/box-delete.spec.ts` | **3 passed** |
| the whole `harness` project | **76 passed** (4.7 min: core, modes, replay, scaffold and furniture, on the changed viewer) |
| `WT_INTEGRATION=1 node tools/run-py.mjs -m pytest services/api/tests/test_bx_piece_edits.py -q` | **31 passed** (the failure of 1.7 is gone: `test_close_removed_against_the_viewers_case_file` reads the 15 cases) |
| `node tools/check-openapi-additive.mjs` | ok; the two `contracts.ts` copies equal |
| `npx vite build -c packages/viewer/vite.offline.config.ts --outDir %TEMP%\wt-bx\offline-template` | built (812 kB, one file); nothing written to `dist/` |

### 2.6 Not done here

* Touch (PC first) and a Restore list inside Walk: as the design says.
* The staff app (`apps/web/src`), the mock API, the complete fake viewer, `tests/e2e/box-delete.spec.ts` and the leak
  case of BX 8.5: the other parts'.
* `npm run test:api` in full, `npm run test:builder`, `npm run build`, the e2e specs and the reference checks of BX 8.7
  were not run by this part (it changed nothing they read but the viewer bundle; the offline template was built into
  the temp folder only).
