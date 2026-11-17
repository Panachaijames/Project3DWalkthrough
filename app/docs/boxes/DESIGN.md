# Delete one furniture box: design (step BX, 16 Nov 2026, revised after review)

Branch `box-delete`. This step builds the first piece of "Editing the furniture boxes" (plan 2.5), brought forward on the owner's request of 12 Nov. The designer checked every claim against the code without changing any file. Three critics (data, staff, tests) then reviewed it, and their findings were checked against the code and worked in; see "Review notes" at the end. The decisions below are final unless they appear in "For the owner" at the end.

---

## 1. In short (for the owner)

- **In Orbit:** staff click a furniture box in the staff app's 3D view. A bright magenta marker appears on the box, and a card in the top-right corner shows the box's kind, family, size and floor. **Delete box** (or the Delete key) removes it.
- **In Walk and Ghost:** the box under the crosshair gets the same marker. Delete removes it at once, and a line at the bottom reads "Deleted: Chair / stool · Ctrl+Z to undo". This is built by default; see "For the owner", 3.
- **The box goes at once.** Walk no longer bumps into it. It leaves the furniture list (CSV), the 3ds Max script and the offline file, and it is saved with that version like the typed heights.
- **The app bar shows it.** Beside the save status, a line such as "Furniture saved · 3 boxes deleted" stays on screen, so a colleague opening the version sees that boxes were taken out.
- **Pieces standing on it go too.** If something stands on the box (a computer on a table), the card says so before the delete, and those pieces go with it. Nothing is left floating or dropped to the floor.
- **Nothing is lost:**
  - the card's **Undo**, and Ctrl+Z, undo deletes and restores for the whole visit;
  - the line "3 boxes deleted · Restore…" under the furniture legend opens a list of every deleted box, with **Restore** for each and **Restore all**;
  - Restore all can itself be undone.
- **What it does not change:** the drawing, the walls, the rooms, the door finder and the saved version's own files. Clients' offline files show the deletions but have no Delete button.
- **New versions.** When a new version of the drawing is saved with the carry tick on, a deletion carries over only where the new drawing has the same box in the same place (within 1 cm), and only when that match is unambiguous. Any other deleted box shows again in the new version.

---

## 2. Behaviour

### 2.1 Who gets the control

- A new viewer option `editBoxes` (default false). Only the staff app's version page sets it: `viewerOptions(search, testHook, editBoxes = false)` in `apps/web/src/lib/viewerProject.ts` adds the key only when it is true, and only the version page passes true. Today's `toEqual` pins in `viewerProject.test.ts:73,78-81` therefore stay as they are.
- The draft preview (`BuildStep.tsx`, `draftViewerOptions()`) does not set it, because it has no saver. The offline file does not set it either (plan 2.4: clients change nothing).
- With `editBoxes` off, no control appears and saved deletions are still applied (2.7 describes the client's legend).

### 2.2 Picking a box in Orbit

New module `packages/viewer/src/furniture/select.ts`. Everything is registered through `ctx.disposer` and listens on `ctx.canvas`.

- **Shared pick.** The pick code moves out of `hover.ts` (lines 39-50: the ray from the pointer, the visible box meshes plus the occluders, the nearest hit) into `furniture/pick.ts`, which takes a screen point. Hover, select and Walk aim (2.2b) all use it.
  - Deleted boxes have `mesh.visible = false`, so `showing()` already leaves them out.
  - Hidden kinds and hidden floors are never picked.
- **When a click selects.** All of these must hold:
  - left button, not touch (PC first);
  - `ctx.modes.mode === 'orbit'`;
  - `!ctx.modes.state.locked` (the replay is not running);
  - `!ctx.modes.state.camOpen`;
  - the pointer moved less than 4 px between `pointerdown` and `pointerup`. The module records this itself, because OrbitControls captures the pointer and `modes/input.ts` does not track drags in Orbit.
- **The double-click to walk is untouched.** A `click` with `detail === 1` selects. A `click` with `detail >= 2` clears the selection, and the existing double-click then switches to Walk, which clears it anyway. The first click of a double-click briefly shows the marker; this is accepted.
- **What a click does.**
  - A click on a box selects it.
  - A click on empty space or on a wall clears the selection.
  - A click on another box moves the selection to it.
- **The cursor.** With `editBoxes` on, `hover.ts` sets `canvas.style.cursor = 'pointer'` while the pointer rests on a selectable box. It clears the cursor on leave and when a drag starts. OrbitControls sets a cursor only when `cursorStyle` is `'grab'`, which the viewer does not use.

### 2.2b Deleting from Walk and Ghost, at the crosshair

The crosshair already exists in Walk and Ghost: `[data-wt=cross]` (`modes/ui.ts:88`) is shown whenever the Camera panel is closed (`ui.ts:191`). Under pointer lock, keys reach a window listener: the modes' keydown only adds unknown keys to `s.keys` (`modes/input.ts:73`), and the target is the body, so `ours()` is true. The furniture module therefore needs nothing inside `modes/**`.

- **The aimed box.** With `editBoxes` on, in Walk or Ghost, with the Camera panel closed and the replay not running, the shared pick runs at the screen centre at most 10 times a second. It takes the nearest showing box within 6 m of the eye, so a box across a hall is not aimed at by accident. That box carries the selection marker (2.3).
- **Delete.** The Delete key removes the aimed box with its cascade (2.5), under the same key guards as in Orbit (2.3). There is no card, because the mouse is captured, and no confirm.
- **The toast.** `[data-wt=box-toast]` sits at the bottom centre, above the hint line, with `z-index: 7` and `pointer-events: none`. It reads "Deleted: Chair / stool (+2 on it) · Ctrl+Z to undo". It stays until the next delete, restore or undo, or for 6 s. The kind label goes in through `el()`.
- **Undo.** Ctrl+Z undoes, as in Orbit.
- **Colliders** update at once, so the walker can step into the place.
- **Not built:** touch (PC first), and a Walk-side Restore list. The panel's Restore list stays usable in Walk, and 2.6 describes how a restore behaves there.

### 2.3 What is shown

- **Selection marker.** One shared `Group`, `furniture-selection`, added to `ctx.scene` and never to a floor group or a `late` list:
  - an enlarged box (the unit box scaled to the selected box plus 2 cm on each side) with a translucent fill (opacity 0.35);
  - an outline `LineSegments` on the unit `EdgesGeometry`, with its own `LineBasicMaterial` (`depthTest: false`, `renderOrder` 10);
  - the colour is magenta `#ff2bd6`, which no kind uses. A unit test checks it against the kinds table.

  On select, and every frame while something is selected (a typed height changes the mesh's scale), the group copies the selected mesh's `matrixWorld`. It is visible only while that mesh is showing. Because the marker is outside every `late` subtree, the replay's `fadeLate` and `restoreLate` never touch it, so a marker can never be left invisible after a replay. Its geometries and materials are disposed through `ctx.disposer`. `intersectObjects` never sees the marker, because the pick lists only box meshes and occluders.
- **Card.** `[data-wt=box-card]` is placed at a fixed spot, the top right of `ctx.ui.root` (`top: 12px; right: 12px`, the Camera panel's place). The Camera panel cannot be open while a box is selected. It has `width: min(280px, calc(100% - 48px))`, `z-index: 7` and `pointer-events: auto`.
  - Layers: above the side panel and hint (6) and the hover tip (5); below the Camera panel and replay (8), the flash (9) and the error box (10). The Walk HUD (7) is never shown with a card.
  - The card never covers the scene's middle or the next chair in a row. It does not move while the view orbits.
  - Every drawing text goes in through `el()`.

  Lines:
  1. **Kind label** (bold)
  2. family
  3. `w × d × h m · <floor name>` (plus `, from z0 m` when it stands on something, as the tip does)
  4. the piece's builder note, muted, when it has one (for example "fronts merged: 12 x …", "drawn loose, not as a block")
  5. the id, small and muted
  6. only when other pieces stand on it: "2 pieces stand on it (Computer, Printer): they are deleted with it."
  7. buttons `[data-wt=box-delete]` **Delete box (Del)** and `[data-wt=box-close]` ×

  The old line "n pieces drawn side by side" is dropped. `n` counts drawn shapes or absorbed fronts, not pieces: the house has boxes with n = 92 (`vendor/furniture_kit.py:238,296`). The furniture list has one row per box either way.
- **No browser confirm.** The card is the confirmation step, and Undo, Ctrl+Z and Restore always exist. The confirms used for deleting a project or version (DEL) are for things that cannot be undone, which this is not.
- **Hover tip.** With `editBoxes` on, the tip gains one last line, `[data-wt=furniture-tip-hint]` "Click to select". The tip is not shown while a card is open. With `editBoxes` off the tip is byte-for-byte as today, so the hover tests in `install.test.ts` (497-584) stay green.
- **How staff find the feature.** With `editBoxes` on, a line `[data-wt=furniture-edit-hint]` sits under the legend note, in its own element: "Orbit: click a box to delete it · Walk: aim at it and press Delete". The pinned legend note (`legend.ts:59`, `install.test.ts:193`, e2e `furniture.spec.ts:234`) stays byte-equal. The Orbit hint line is pinned to the prototypes and stays.
- **Keys.** One window `keydown` listener handles the keys. It ignores a key when `typing(e)` is true or `ours(e, root)` is false (both exported from `modes/input.ts`), so a height box keeps its own Delete.
  - **Delete** with a box selected (Orbit) or aimed (Walk, Ghost) deletes it. Delete is armed only while the last `pointerdown` was on the canvas or on the card, and a `pointerdown` in the panel disarms it. So a Delete pressed after typing a height (Enter blurs to the body, `legend.ts:119`) does nothing.
  - **Ctrl+Z** undoes the last delete or restore of this visit (2.4). `modes/input.ts:61` leaves Ctrl combinations free.
  - **Esc** closes the card and clears the selection.
  - **Backspace** is not used, to keep a delete deliberate.
- **When the selection clears.**
  - bus `mode` with mode not Orbit, or with the camera open (`openCam` → `updateHud` emits `mode`);
  - bus `floorMode` or `toggles`, or bus `furniture` with source `tick`, when the selected mesh is no longer showing;
  - bus `pieces` (any source), when the selected piece's removed state changes. This covers a deletion taken over from another tab;
  - bus `replayPhase` (the replay starting; `modes.lock(true)` emits nothing). The marker is outside `late`, so the few frames between `enter()` and `phaseChanged()` do no harm;
  - Esc;
  - dispose.

### 2.4 Deleting: soft, so restore is trivial

- `ItemState` gains `removed: boolean`. The mesh, the item, `itemOf` and `pieceById` all stay.
- `removePiece(id)` marks the piece and every piece standing on it as removed. This cascade is the closure in 2.5. Then it calls `kinds.forEach(sync)` and the legend refresh, and emits.
- After a delete, the card reads "Deleted: Table (+2 on it)" with `[data-wt=box-undo]` **Undo** and ×. It stays until the next click or Esc. There is no timer.
- **Undo is a visit-long stack.** Each delete, restore or Restore all pushes its ids and its direction. Undo (the card button or Ctrl+Z) applies the inverse of the top entry and then closes the map.
  - An undone delete restores exactly that delete's group, a top and what stood on it, so the closure always holds.
  - The stack is cleared when the host sets edits from elsewhere (bus `pieces` with source `api`: a takeover from another tab or a 412 merge), because remote changes make the inverses ambiguous. A card whose Undo is no longer on the stack hides its Undo.

### 2.5 Pieces standing on a deleted piece: cascade, not the old leniency

Decision: when a support goes, the pieces standing on it go with it, and the card says so beforehand. The "drop to the kind's base" leniency of DESIGN 5.6 stays for odd model files only. Reasons:

1. **The 3ds Max script.** Each piece is one line whose height and z0 come from its kind and its `"supKind"` token (`vendor/furniture_max.py:448`). A computer kept after its table was dropped would still sit at table height in Max, but at its own base in the viewer and the CSV. Keeping them equal would mean rewriting other pieces' lines and the CSV's `base_mm` and `on_top_of`.
2. **Validators refuse a dangling `on`.** The API's model rule (`builtmodel.py:224`) and the Max generator (`furniture_max.py:438-441`) both refuse one. The edits record must stay "bakeable" into a valid model later (section 7).
3. **Staff intent.** A computer left on the floor is never what staff mean.
4. **Less code.** With cascade no surviving piece ever stands on a removed one. `undersideOf` (`logic.ts:84-88`), `pieceById` and the CSV's `ids` lookup (`furniture_csv.py:66`) need no change, and no `KeyError` is possible.

**The closure rule.** There is one pure function in TypeScript, `furniture/logic.ts` `closeRemoved(ids, pieces)`, and one in Python, `piece_edits.py` `close_removed`. Both are tested against the same case file, `packages/viewer/test/fixtures/furniture/close-removed.cases.json` (C-owned), which the Python test reads by its app path.

- If a piece is removed, every piece whose `on` names it is removed too.
- The rule is applied transitively. Supports never stand on anything today, but the loop is cheap.
- The viewer, the API and the carry-over all apply it, so a list that arrives open (an old tab, a hand-edited file, a merge) is closed the same way everywhere.

**Restore** keeps the record valid:

- `restorePiece(id)` restores the piece's group: its top (its support, if that is removed, else itself) and every removed piece standing on that top.
- Restoring a computer whose table was deleted brings the table back too.
- Restoring a table from the list brings back everything removed on it, including a computer that staff had deleted on its own before deleting the table. The record keeps no history. This is accepted and is the documented behaviour. Undo within the visit is exact.
- `restoreAll()` clears everything (and is undoable, 2.6).

### 2.6 Where the list of deleted boxes is shown

- **The app bar** (staff app, 6.2) always shows the count while anything is deleted. The panel line below is the way into the Restore list.
- **The legend line.** A new element `[data-wt=furniture-removed]` sits between the kind rows and `furniture-buttons`. It is not inside the buttons row and not a new head column, because both are pinned by tests.
  - It exists only while `editBoxes` is on and at least one box is deleted, or just after a Restore all (below). With nothing deleted the legend is unchanged.
  - Text: "3 boxes deleted · " followed by a link-style button `[data-wt=boxes-restore-open]` "Restore…".
- **The popover.** `[data-wt=boxes-restore]` is an absolute child of `ctx.ui.root` beside the panel, `z-index: 7`, with × in its top-right corner.
  - Its bottom edge is clamped above the hint line's top, measured with `ctx.rectOf(ctx.ui.hint)`. Its height is at most 50 % of the root, and it scrolls.
  - **One line per group** (a deleted piece whose support is not deleted, with its deleted dependents folded in): `Table / desk · <family> · Level 1 (+2 on it)`, the id small and muted after it, and `[data-wt=box-restore]` **Restore**. All drawing text goes in through `el()`.
  - **Footer, left:** `[data-wt=boxes-restore-all]` **Restore all**, away from ×.
- **Restore all is undoable.** After it, the legend line reads "All 12 boxes are back · " with `[data-wt=boxes-restore-undo]` **Undo**, which puts back the exact previous map (one PUT each way). It stays until the next delete or restore, or until the version is left. Ctrl+Z does the same.
- **What a restore shows:**
  - In Orbit, with the box's floor showing and its kind visible, the restored box becomes the selection (marker and card). The camera does not move.
  - When its floor is not showing, the card reads "Back on Level 1 (not shown: press Level 1)".
  - When its kind is hidden, the card adds "(Table / desk is hidden: tick it to see it)".
  - In Walk or Ghost there is no selection. The toast reads "Back: Table / desk on Level 1".
- **Panel size.** The popover is an overlay, so the panel's size tests (harness `furniture.spec.ts` 284-330, e2e 306-345) are unaffected. The extra legend lines must still fit at 1366×768, and a new e2e check proves it.

### 2.7 Walk colliders, replay, counts, Keep doorways clear

- **Colliders.**
  - `stops(p)` (`index.ts:67`) becomes `!p.removed && stopsWalk(p.kind, p.approach, keepDoorways)`. The frozen `StopsWalk` type is untouched.
  - `syncKind` (`boxes.ts:63-70`) sets `mesh.visible = k.visible && !p.removed` and pushes or splices the collider as `stops(p)` says.
  - Walk, its jump landing (`stepHop`) and the readouts already use only visible colliders. Ghost ignores colliders.
  - Walls and glass are not touched, and the walk-parity rig installs no furniture (`record-walk-parity.ts:8`), so the walk-parity golden stays green.
- **Replay.**
  - The problem: the replay fades in every object in `FloorRecord.late` at the end (`replay/apply.ts` `fadeLate`), and only `furniture.apply()` restores per-box visibility. A removed box would flash in during the build replay, including in a client's offline file.
  - The fix: a removed mesh also leaves its floor's `late` list, and a restored one is pushed back. Both happen in a small `boxes.ts` helper, `setRemoved(p, on)`. The removed state lives in `syncKind`, so `apply()` after the replay (`replay/index.ts:188`) keeps it.
  - A `setPieceEdits` from the host during a running replay updates state and `late` but leaves `mesh.visible` to the replay's closing `apply()`.
- **Counts in the staff app (`editBoxes` on).**
  - The legend label becomes live: `${label} (${live})`, where live counts the kind's pieces that are not removed. The format is pinned, the number is not. `legend.ts` keeps the label span in its `Row`, and `showRow` refreshes it.
  - A kind whose boxes are all deleted keeps its row, so the layout does not jump while staff work and the kind's typed height stays reachable. The row shows `(0)` and is dimmed through `data-empty`.
- **Counts in the client's file (`editBoxes` off).** The deletions are fixed when the file loads, so the legend is built from the live pieces only:
  - a kind with no live piece gets no row, as an unused kind gets none today (`index.ts:40`);
  - the Keep doorways tick is shown only when a live box stands in a doorway approach.

  With no deletions this is today's legend exactly.
- **The API reads.**
  - `api.kinds()` lists every built kind in both modes, with `count` = the live count. This equals today's value when nothing is deleted.
  - `api.pieces()` still lists every piece. A removed piece carries `removed: true`, and its `visible` and `blocking` are false. The field is present only on removed pieces, so existing `toEqual` checks stay green.
- **Keep doorways clear.** The tick stays (staff app). Its tooltip's count ("N of the boxes stand in front of a door…") becomes live through `showKeep()`. A removed box is never a collider, whatever the tick says.
- **Counts built into the version stay as built:**
  - `version.json` counts and the project card's furniture count;
  - the panel's presentation intro (`ui/panel.ts:34`, for example bank v2's "Furniture: 185 coloured boxes in 14 kinds…"), which is also the first text a client reads in the offline file;
  - the replay captions "N furniture boxes in M kinds" (`stages.json`);
  - the top-view picture.

  These are immutable build outputs, and the legend is the live count. This is recorded in `docs/contract-issues/BX.md` and DESIGN 13. The intro mismatch in clients' files is "For the owner", 4.
- **Reset heights** stays heights only. Its 'local' / 'host' meaning is pinned (`index.ts:103-109`, tests 382-401). It never restores boxes; Restore has its own controls.

### 2.8 Events: viewer to host

- New bus key `pieces: { pieceEdits, source: 'removed' | 'restored' | 'api' }`. It is a separate key, so the pinned `furniture` event list (`install.test.ts:326-336`) does not change. Undoing a delete emits `restored`, and undoing a restore emits `removed`.
- `viewer.ts` `bridgeEvents` turns `removed` and `restored` (never `api`) into the public `boxeschange: { pieceEdits, source }`. This mirrors `heightschange`: the whole map each time, and no event for `setPieceEdits`, so the host cannot loop.

---

## 3. Where it is saved

### 3.1 The record: `overrides.json`, beside the heights

Same file, same revision, same lock, same If-Match, same seed and offline paths. There is no new route and no second saver.

The field is a map keyed by piece id, not a bare list. Re-kind, rename and move will later be more fields of the same piece edit (section 7). The name `pieceEdits` / `removed` avoids `deleted`, which the DEL step already uses for tombstones.

```json
{
  "format": "walkthrough-overrides/1",
  "heights": { "seat": 820 },
  "pieceEdits": {
    "L1-computer-001": { "removed": true },
    "L1-table-005": { "removed": true }
  },
  "revision": 7,
  "updatedAt": "2026-11-16T09:12:03Z"
}
```

- **Canonical form, written by the API:**
  - every key is a piece id of that version's model;
  - the value is exactly `{"removed": true}` (an edit with nothing set is dropped);
  - the map is closed (2.5);
  - keys are in the CSV order (floor in model order, kind in the kinds table's order, id), so the bytes are deterministic;
  - at most one entry per model piece.
- **An empty map is stored as an absent key, never `{}` or `null`.** A heights-only file stays byte-for-byte as today (`test_store.py:75-88`, `test_offline.py:118`). The format stays `walkthrough-overrides/1`, because the field is optional and old files remain valid.
- **Store record** (`store/base.py`, an authorised record change):
  - `HeightOverridesFile` gains `piece_edits: dict[str, Any] | None = None`, declared after `heights`, with `OPTIONAL = ('pieceEdits',)`. `Record.to_json` drops `None` only at the top level (`base.py:123-125`), which is exactly this key.
  - There is no nested `Record` for an edit. `write_overrides` builds each value by hand as `{"removed": True}`, so a later optional field is never written as `null`.
  - The file level accepts any JSON object as an edit. `piece_edits.live` (3.2) keeps only entries whose id is a model piece and whose `removed` is exactly `true`, and ignores other fields and non-object values. A hand-edited, odd or newer-step file therefore never makes `read_overrides` raise, so `getVersion` (`views.py:127`) and the version page never answer 500 because of it.
- **Rollback warning.** `Record` uses `extra='forbid'` at the top level, so code from before this step cannot read a file holding `pieceEdits`. This goes in BX.md.
- **`write_overrides(project_id, n, heights, if_revision=None, piece_edits=None)`** (`store/local.py:333-348`, and the `Store` protocol in `base.py:361`):
  - `None` keeps the saved map;
  - a dict replaces it (empty = absent);
  - the revision goes up by 1 for either change, under the same `exclusive()` lock and the same `RevisionConflict`.

### 3.2 API: additive fields on the existing routes, no new route or operationId

All of this is in `models.py`, which is frozen; the main session authorises the change as it did for DEL.

- **New schema `PieceEdit(ApiModel)`:**
  - `removed: StrictBool | None = None`, description "true: the box is deleted from this version's view, furniture list, 3ds Max script and offline file";
  - `model_config` adds `extra='forbid'`, so a later client sending `{kind: …}` to this server gets a 422 rather than being silently ignored.
- **`HeightOverrides`** (the response, also inside `VersionDetail.overrides`) gains `piece_edits: dict[str, PieceEdit] = Field(default_factory=dict, description='Furniture piece id -> its edit; today only {removed: true}. Empty when none.')`.
  - Responses always carry it (`{}` when none).
  - Pins that change: `test_routes.py:145` (`test_version_detail`'s `overrides` over every version), `test_routes.py:272ff` (GET and PUT JSON), and the mock API.
- **`HeightsUpdate`** (the request) gains `piece_edits: dict[str, PieceEdit] | None = Field(default=None, description='Piece id -> edit; replaces the saved edits when sent; left out, the saved edits stay.')`.
  - `heights` stays required (changing that would not be additive).
  - Absent means keep. An old tab, and the saver whenever the edits are not dirty (6.1), can never erase deletions.
  - The heights-only PUT body stays exactly `{heights}` (`web.spec.ts:195`).
- **PUT** (`routes/furniture.py`, body only; decorators, summary, description and responses unchanged):
  - after `canonical_heights` (422 `invalid_heights` as today), it calls `piece_edits.canonical(model, body.piece_edits)` when the field is sent;
  - an id that is not a model piece gives **422 `invalid_piece_edits`** with `details: {unknownIds: [first 20], count}`;
  - non-object values and unknown inner keys are refused by pydantic (FastAPI's `HTTPValidationError`, already in the 422 schema);
  - `removed: false` or `{}` is dropped;
  - the map is closed and ordered;
  - then `write_overrides(..., piece_edits=...)`.
- **412 `revision_conflict`** details stay `{revision, heights, updatedAt}`, plus `pieceEdits` (the live map) **only when it is non-empty**. `test_hardening.py:270`, an exact dict equality on a store without edits, stays green. `conflictOf` reads a missing `pieceEdits` as `{}` (`heightsSync.test.tsx:29` already builds details without it).
- **GET, `getVersion` and the 412 details return the live map** (`piece_edits.live(model, saved)`: model ids only, entries exactly `{removed: true}`, closed) through `views.overrides_of` (`views.py:85-88`), using the cached model. An id the model lacks therefore never reaches the staff app, where a 412 merge would copy it into the next PUT and fail every retry with 422.
- **Read time is lenient.** Every consumer (GET, CSV, Max, carry, offline) uses `live`, so an odd file never causes a 500.
- **Generation and checks:**
  - `npm run gen:api` regenerates `apps/web/openapi.json` and `src/api/generated/**`; a second run must change no byte (`test_openapi.py:25`).
  - `node tools/check-openapi-additive.mjs` must pass against both bases (`66b4c06` default and `--base 9eb2d58`): existing operations deep-equal, `HeightOverrides` and `HeightsUpdate` only gain optional properties, `PieceEdit` is a new schema, and the generated types only gain optional members.
  - Today's `openapi.json` has no `-Input` / `-Output` schema pairs, and a defaulted field is not marked required (`ErrorBody.details`), so a split or a required `pieceEdits` is unlikely. The builder still checks the output. If either happens, `HeightOverrides.piece_edits` becomes `dict[str, PieceEdit] | None = None` (null when none), and the pins follow.
- **The contract file.** The step writes `docs/contract-issues/BX.md` on the DEL.md pattern: what changed, the additive check against both bases, files, checks, and the guard results of 8.7. It records:
  - the new error code;
  - that the frozen route texts ("Replaces the saved map…", the Max script's "byte for byte as seeded", the frozen `carryHeights` description) now under-describe the behaviour;
  - the stale built texts (2.7);
  - the amendments to DESIGN 9.4, 10.2, 13, 15.3, 16 and 18.7.

### 3.3 TypeScript contracts

These go in both `docs/contracts.ts` and `packages/viewer/src/contracts.ts`, byte-equal, as an authorised additive change:

- `export interface PieceEdit { removed?: true }` and `export type PieceEditMap = Record<string, PieceEdit>`.
- `HeightOverridesFile.pieceEdits?: PieceEditMap`.
- `ViewerProject.pieceEdits?: PieceEditMap | null`.
- `ViewerOptions.editBoxes?: boolean` (default false), and in `ResolvedOptions` (about line 693) an **optional** `editBoxes?: boolean`, read as `=== true`. With it optional, the scaffold's shared test context (`test/harness/context.ts:487-492`, "nobody edits") still typechecks untouched.
- `ViewerEvents.boxeschange: { pieceEdits: PieceEditMap; source: 'removed' | 'restored' }`.
- `InternalEvents.pieces: { pieceEdits: PieceEditMap; source: 'removed' | 'restored' | 'api' }`.
- `Viewer.getPieceEdits(): PieceEditMap` and `Viewer.setPieceEdits(e: PieceEditMap): void`. These mirror `getHeights` / `setHeights`: unknown ids are ignored, the map is closed, and no public event fires.
- `FurnitureApi` gains:
  - `pieceEdits(): PieceEditMap`
  - `setPieceEdits(e: PieceEditMap): void`
  - `removePiece(id: string): string[]` (the ids removed, cascade included; `[]` when unknown or already removed)
  - `restorePiece(id: string): string[]`
  - `restoreAll(): void`

  The typed literals that must gain stubs are `core/viewer-events.test.ts:45`, `test/unit/replay/replay.test.ts:45` (`fakeFurniture`, D-owned) and `apps/web/test/fake-viewer.ts:386`.
- `FurniturePieceView.removed?: true`. The doc comment of `FurnitureKindView.count` changes to "live".
- `FurnitureCsv = (model, heights, removed?: ReadonlySet<string>) => string`.
- `StoredFurnitureState` and the storage key are unchanged (3.5 explains why).

### 3.4 Limits

- The edits map holds at most the model's piece count. Ids must be model ids.
- The 2 MiB body guard is far away: the biggest model has 185 pieces, about 8 KB.
- **Keepalive cap.** Browsers refuse a `keepalive` request once the bodies in flight pass 64 KiB. That is about 1,600 entries at 40 bytes, which no model reaches today. The saver sends `pieceEdits` only while edits are dirty (6.1). When a keepalive body would pass about 60 KiB, it is sent without keepalive and the outbox keeps the change.

### 3.5 (note) Browser storage

- The staff app ('host') keeps nothing locally beyond today's doorways tick. The saver's outbox (6.1) carries unsent edits.
- The offline file has no Delete control, so it stores no deletions. The localStorage key's `savedHeightsTag` (`core/context.ts:99-123`) therefore needs no change, and the pins in `install.test.ts:348-415` and e2e `furniture.spec.ts:672-683` stay as they are.

---

## 4. The downloads

All three leave deleted boxes out, and each is byte-identical to today when nothing is deleted.

| Download | Where | With deletions | Byte-identical when nothing is deleted |
|---|---|---|---|
| Furniture list CSV (staff app) | `furniture_csv.py`: `csv_text`, `model_csv_text` and `csv_bytes` gain `removed: AbstractSet[str] \| None = None`. `ids` stays the whole list; only the rows are filtered. `routes/downloads.py:63-65` passes `piece_edits.live(model, saved)`. | Rows of removed ids are left out. Thanks to the cascade, every other row's `base_mm` and `on_top_of` is unchanged. | `None` or empty takes the exact old path. Goldens `fixtures/csv/{bank-v2,suite,house,hotel}{,-typed}.csv` (`test_furniture_csv.py:26,31`, `test_routes.py:222,234`, `web.spec.ts:213`) stay green. |
| Furniture list CSV (the viewer's own **Save list (CSV)**, staff app and offline file) | `logic.ts` `furnitureCsv(model, heights, removed?)` filters `csvOrder` rows. `index.ts` `csv()` passes the live removed set. | The same bytes as the API's, tested against each other. | No argument or an empty set gives today's text (`install.test.ts:457`, e2e 617). |
| 3ds Max script | `routes/downloads.py` `download_max_script` (body only). If `live` is empty, today's `FileResponse` is returned untouched. Otherwise a new `Store.download_bytes(project_id, n, name)` (`LocalStore` reads `downloads/<name>` beside `download()` at `local.py:312`; a URL store can implement it) feeds the pure `piece_edits.filter_max_script(text, prefix, removed)`. The result is served by `views.attachment_bytes` with the same attachment name and media type. **The prefix is the version's `model.maxPrefix`** (required by the schema; it matches every stored script's `fn <PX>_furnAll`). It never comes from `project-settings.json`, which may be missing or name a newer prefix. | Every line matching `^    <PX>_furnBox "[^"]*" "[^"]*" \d+ "<id>" ` with `<id>` in the removed set is dropped. The line format is kind, Max object name, floor index, id (`furniture_max.py:446`). `ascii_name` turns `"` into `'`, so names never hold a quote. The filter counts the lines it drops: when the count differs from the number of live removed ids, it refuses with 500 `store_error` ("the 3ds Max script does not match its model"), so the comment can never name a box that is still built. One comment line is inserted as the new **line 3**, line 2 (the stamp) unchanged, ending as the file's own lines do (CRLF). It names the **Max object names** the 3D team searches by: `-- 3 furniture boxes deleted in the walkthrough app are left out: BB_L1_Furn_computer_001_…, BB_L1_Furn_printer_001_…, BB_L1_Furn_table_005_…` (up to 30 names, then `, and N more`). Kinds, spinners and materials stay. The script is filtered, never regenerated: the API never imports the builder, and the generator is vendor-pinned. | Same `FileResponse`, same bytes and headers (`test_routes.py:200-210`). |
| Offline HTML | No change in `offline.py` or `make-offline.mjs`: the raw `overrides.json` text is already embedded (`offline.py:124-126`). `packages/viewer/src/offline/entry.ts` `projectOf` adds `pieceEdits` **only when** `p.overrides?.pieceEdits` is present (no `?? null`), so `hook.test.ts:122-123` stays as pinned. The viewer reads it leniently (non-object values and unknown ids ignored). | Deleted boxes are absent in the file (no replay flash, 2.7), and the client's legend is live-only (2.7). Its Save list (CSV) leaves them out. There is no Delete or Restore control. | The file has no `pieceEdits` key, so the payload is identical and Node equals Python (`test_offline.py:224-228`, `offline.spec.ts:99`). |

- **The Downloads menu** (`DownloadsMenu.tsx:29`).
  - `WITH_HEIGHTS` keeps `furnitureCsv` and `offlineHtml`, which carry heights and deletions and wait as today, whenever the saver is "Saving…" or "Not saved".
  - The **Max script waits only while deleted-box edits are unsaved** (the saver's `editsDirty`, 6.1). The script carries no saved heights, so a heights-only save, pending or failed, leaves it a link as today. `web.spec.ts:447-475` (`:468`), `pages.test.tsx:358` and `DownloadsMenu.test.tsx:78-89,105` stay as pinned.
  - **Tooltips** (`lib/format.ts:63-67`):
    - the CSV and offline items: "Waiting for the furniture changes (heights, deleted boxes) to be saved" and "The furniture changes on screen are not saved (…): the file would not carry them";
    - the Max item: "Waiting for the deleted boxes to be saved" and "The deleted boxes on screen are not saved (…): the script would still build them".
    - Pins that change: `DownloadsMenu.test.tsx:86,103`, `web.spec.ts:466`.
- **Saved heights in the Max script.** The script's spinners still start at the model's heights, not the saved ones. That is unchanged and out of scope (DESIGN 18.7).
- **The 3D team's side.** The script refuses a scene that already has boxes (`furniture_max.py:310-313`). A team that built the boxes earlier deletes the named objects by hand, which is why the comment lists Max object names. The step adds this to the product doc and STATUS.
- **Every box deleted.**
  - The CSV is the header only.
  - The Max script's `fn <PX>_furnAll = ( … )` ends up with an empty body. That is valid MaxScript but has not been run in real Max (risk 9).
  - `hasFurniture` and the download flags stay as built.
  - This is allowed and not refused.

---

## 5. A new version, and the offline file's 'local' mode

### 5.1 Carry-over: yes, by fingerprint, one-to-one, never by bare id

*Amended after the review (17 Nov, `contract-issues/BX.md`):* floors are paired between the two models by stack and
level (within 10 mm, one to one), never by key, because a new draft hands out floor keys by position; a piece whose
floor has no pair is not carried ("its floor changed"). The kind is no longer part of the match, so giving a grey
family a kind keeps its deleted boxes deleted. The note on the new version's page names each box that came back (kind,
family, floor, reason).

Ids are ranks (`<floor>-<kind>-<nnn>`, sorted by x then y: `vendor/furniture_kit.py` `finish()` 364-393). One piece added or removed on that floor and kind renumbers every later piece, so v2's `L1-seat-017` can be a different chair in v3. Copying ids blindly would delete the wrong box.

Requiring "same id" (the brief's example) would also drop every correct carry after an unrelated piece shifted the numbering. So the rule matches by what the box is and where it stands, then maps to the new id.

**`piece_edits.carry(old_model, old_edits, new_model) -> (carried, cascaded, not_carried)`** is called in `LocalStore.create_version` beside `carry_heights` (`local.py:512-517`), which itself stays untouched (`test_store.py:207-213`).

- **When it runs.** Only when `carry_overrides_from` is set, i.e. `SaveBuildRequest.carryHeights` is true. The web app sends true by default. Its frozen description talks only about heights; BX.md records that the one flag now covers both.
- **What is carried.** Only the **tops** of the old live map: a removed piece whose support is not removed. Pieces that went only with their support are not carried as deletions in their own right. A computer that went with its table, and that the new drawing puts on another, kept table, therefore stays.
- **The match.** An old piece P matches a new piece Q when all of these hold:
  - same floor key, kind and family;
  - drawing-frame centres (x + offset, y + offset) within **10 mm** on each axis;
  - `w` and `d` within 10 mm;
  - turns equal within 0.5°, compared modulo 180°, or modulo 90° when both pieces are square (w − d under 1 mm), as `finish()` normalises them (`furniture_kit.py:377-379`).

  The handle, block and layer are not compared, because a Revit re-export renumbers handles and can rename blocks. The one-to-one rule below covers the duplicates this lets in.
- **One-to-one.** A removed top P is carried to Q only when all of these hold:
  - Q is P's only match in the new model;
  - **P is the only old piece, removed or kept, that matches Q**;
  - no other carried edit has claimed Q.

  Otherwise P is not carried. A box shows again, but the wrong box is never deleted (the U-10.6 principle). This covers a block inserted twice a few mm apart, or on two layers (the builder merges only exact duplicates, `build/furniture.py:236-246`): when the next drawing drops the duplicate, nothing is carried.
- **Result.** The carried tops, keyed by their new ids, are closed in the new model. Whatever the closure adds is "cascaded".
- **Writing.** `overrides.json` is written (revision 1) when the carried heights **or** the carried edits are non-empty.
- **The record.** `versions/<n>/source/carried-edits.json` is written whenever the old version had edits. It is immutable and makes "why did my chair come back?" answerable:

  ```json
  {"format": "walkthrough-carried-edits/1", "from": 2,
   "carried": {"<old id>": "<new id>"}, "cascaded": ["<new id>"],
   "notCarried": [{"id", "floor", "kind", "family", "why"}]}
  ```

  `why` is one of `"no match"`, `"2 matches"`, `"matches 2 old pieces"` or `"was on a deleted support"`, the last for an old dependent that the new closure did not add back.
- **What staff see.**
  - `SaveStep.tsx:111-112` reads "Carry the furniture heights of v<n>, and its deleted boxes where the new drawing has the same box in the same place". The label is not pinned by any test.
  - A deletion that was not carried shows up as a visible box in the new version, fixed with one more delete.
  - An on-screen note is "For the owner", 2 (recommended).
- **The same drawing** ("Use the files of v<n> again", or a rebuild after an unrelated fix): positions are identical, so everything carries.
- **Seed.**
  - `--force` keeps `overrides.json` (it is in `KEPT_ON_REBUILD`, copied in the commit phase, `seed/build.py:287-295`).
  - In that commit phase, still under `store.exclusive()`, the seed now compares the old and new `modelSha1` of each version. When they differ and the kept file has `pieceEdits`, the edits are re-mapped with `piece_edits.carry` (revision + 1), `source/carried-edits.json` is written, and the seed logs one line per version. Even the suite's stamp does not change with its model (`seed/sources.py:85`), so `modelSha1` is the test.
  - `--reset-overrides` drops the edits with the heights.
  - The help text in `seed/__main__.py:23` and the README are updated.
- **Deleted versions (DEL).** The carry reads the latest remaining version, as heights do.

### 5.2 The offline file's 'local' mode

- A client or staff member opening the file sees the saved deletions applied: the boxes are absent, the colliders gone, the legend built from the live pieces (2.7), and the CSV without them.
- There is no Delete, no Restore, no aim marker and no "boxes deleted" line, because `editBoxes` is off.
- Typed heights work per browser as today, and Reset heights is as today.
- `__host.furniture.removePiece` exists only behind `?test=1`, lasts for the visit and is never stored.
- This matches plan 2.4: clients only look.

---

## 6. The staff app

### 6.1 One saver for heights and deleted boxes: the same core, generalised

`lib/useHeightsSaver.ts` and `lib/heightsOutbox.ts` keep their names and pinned behaviour. The core tracks the edits with an explicit dirty flag. It never decides by comparing its own copy with `base`, because that copy goes stale after a takeover or an outbox replay.

- **State.**
  - `base` becomes `{revision, heights, pieceEdits?}`. The getter exposes `pieceEdits` only when it is non-empty, so the pinned `toEqual({revision, heights})` in `heightsSync.test.tsx` 148, 164 and 167 stays green.
  - The core holds `edits` (the tab's map) and `editsDirty`.
  - `change(heights)` is unchanged.
  - A new `changeEdits(edits)` sets `edits` and `editsDirty = true`, sets pending and unsaved, and restarts the **same** 600 ms debounce, so a delete and a typed height coalesce into one PUT. An edits-only change sends the tab's latest heights (the last `change`, else `base.heights`).
  - `SaverState` gains `editsUnsaved: true`, present only while `editsDirty`, for the Downloads menu.
- **PUT.**
  - `putHeights(path, heights, init, pieceEdits?)` sends `{heights}` unless `editsDirty`, and `{heights, pieceEdits: edits}` while it is set.
  - The pinned `putCalls` records (`useHeightsSaver.test.tsx:261,306,320`) only see the first three arguments.
  - `If-Match` is unchanged.
  - Keepalive bodies over about 60 KiB go without keepalive (3.4).
- **Success.**
  - `base` becomes the API's answer, which includes the canonical live edits.
  - If no `changeEdits` came while the request was in flight, `edits` becomes the answer's map and `editsDirty` is cleared.
  - If the answer's map differs from the map sent (the server closed it or dropped an id), the core calls the new `onRemoteEdits(map)`, so the viewer shows what was saved.
  - `updateHeightCaches` (`:272-276`) writes `pieceEdits` into the `getFurnitureHeights` cache and the `getVersion` cache's `overrides`. Without that, a later address change that re-creates the viewer from a stale `detail.overrides` would bring deleted boxes back.
- **412.**
  - `conflictOf` (`api/client.ts:82-89`) also reads `details.pieceEdits`, with missing read as `{}`.
  - Heights keep `mergeChanges`.
  - When `editsDirty`, the edits are merged by `mergeEdits(base, mine, theirs)`, a per-id three-way merge on the same pattern: an id whose edit differs between `base` and `mine` takes `mine`'s (absent = restored), and every other id keeps `theirs`. Restores need a three-way merge; a set union would undo them. `editsDirty` stays set, and the merged map goes to the viewer through `onRemoteEdits`, where the viewer closes it. The server closes it again.
  - When `editsDirty` is not set, `edits` becomes `theirs`, `onRemoteEdits(theirs)` runs, and the re-sent body stays `{heights}`.
  - It re-sends up to `MAX_CONFLICTS` times, as today.
- **`adopt()`.** It takes over a newer revision only when nothing is unsaved, pending, in flight or debouncing and `editsDirty` is not set (as today, plus the flag). Then `base` becomes the saved answer and `edits` becomes its map. `onRemote(heights)` runs when the heights changed, as today, and the separate `onRemoteEdits(map)` runs when the edits changed. Both reach `viewer.setHeights` / `viewer.setPieceEdits`, which emit no public event and so cause no save loop. `onRemote` keeps its one argument, so the pins in `heightsSync.test.tsx:58,147,169` stay green.
- **Outbox.**
  - An entry always carries `base.pieceEdits` when the base has any.
  - It carries `pieceEdits` only while `editsDirty`; restoring the entry sets `editsDirty` exactly when that field is present.
  - A heights-only entry replayed on a revisit therefore sends `{heights}` and can never erase saved deletions; a 412 then takes theirs.
  - `parseUnsent` accepts old entries without these fields, and the round trip `toEqual(entry)` (`:178-180`) stays green.
  - `sendUnsent` and `startUnsentSender` carry them with the same merge.
  - `forgetVersion` / `forgetProject` (DEL) already drop the whole entry.

### 6.2 Page and host wiring

- **`ViewerHost.tsx`:** a second callback prop, `onPieceEditsChange`, and a second `viewer.on('boxeschange', …)` in the same effect (next to `:49`), with the same Effect Event pattern. The StrictMode double mount must still leave one viewer.
- **`ProjectVersionPage.tsx`:**
  - the memo (`:112-116`) passes `unsent?.pieceEdits ?? detail.overrides.pieceEdits` to `buildViewerProject` / `toViewerProject`, which sets `ViewerProject.pieceEdits` (`viewerProject.ts:39`);
  - the memo key is unchanged, so a save never re-creates the viewer;
  - `options` passes `editBoxes: true` through the version page's own `viewerOptions(…, true)` call (2.1);
  - the core's `onRemote` calls `setHeights` and `onRemoteEdits` calls `setPieceEdits`;
  - `saver.changeEdits` goes to `onPieceEditsChange`;
  - the takeover on focus and every 30 s (`:130-139`) is unchanged.
- **Status texts** (`lib/format.ts:59-61`): `'Heights saved'` becomes **`'Furniture saved'`**, because the status now covers deleted boxes too.
  - `'Saving…'` and `'Not saved: <reason>'` are unchanged, as are the test ids `heights-status`, `heights-status-text` and `heights-retry`.
  - The `beforeunload` prompt while 'error' now covers edits for free.
  - Pins that change in this step: `format.test.ts:75` (and the import at `:13` if it names the constant), `pages.test.tsx` 233, 292, 305, 329, 361, 373 and 488, and `web.spec.ts` 109, 194, 236, 262, 416, 442, 472, 506, 509, 514 and 516. DESIGN 15.3 is amended.
- **Deleted-box count in the app bar.** `[data-testid=boxes-deleted]` is its own element beside `heights-status`, so `heights-status-text` stays as pinned. It reads "· 3 boxes deleted" and is hidden at 0. The count is taken from `getPieceEdits()` at mount, `boxeschange` and `onRemoteEdits`.
- **Version switch.** It works as today. The old viewer is disposed, and the saver effect's cleanup does `flush({keepalive: true})` to the **old** version's path, so a delete in the last 600 ms lands on the old version. The new core starts from the new `detail.overrides`, including its `pieceEdits`, and that version's outbox entry.
- **Conflicts across tabs:**
  - Tab A deletes and tab B types a height: B's body is `{heights}` (its edits are not dirty), so A's deletion stays. On a 412, B takes A's edits and shows them.
  - Idle tab B adopts A's deletion and then types a height: still `{heights}`.
  - A restore in A and a delete in B of different boxes both survive (per-id merge).
- **Test doubles.**
  - `apps/web/test/fake-viewer.ts` gains `getPieceEdits`, `setPieceEdits`, `boxeschange`, stubs for the five new `FurnitureApi` methods (`:386`), and a fake control `[data-wt=fake-remove-box]` (removes the first piece) for mock runs.
  - `apps/web/test/mock-api/core.ts` `putHeights` keeps or replaces `pieceEdits` and closes them. Its CSV with edits is its golden with those rows removed, so there is no `mock_no_golden` 500. The offline stand-in embeds the edits.
  - The shared e2e reset helper, `apps/web/test/e2e/web-kit.ts:60-62` `resetHeights`, sends `{heights: {}, pieceEdits: {}}`, so no spec leaves deletions behind for `web.spec.ts`'s byte-equal Max (161) and CSV (209) checks.

---

## 7. Consistency with the rest of box editing and the 3ds Max round trip

**What this sets up**, reused by the rest of box editing:

1. **The record.** `overrides.json` → `pieceEdits[<id>]` is the per-piece edit of a built piece. Later fields are additive optional members of `PieceEdit`, written by hand without nulls (3.1), and carried by the same revision, saver (dirty flag), merge and carry:
   - `kind` (re-kind)
   - `name` (name a piece)
   - `place {x, y, rot, w, d}` (move, turn, resize; drawing-frame numbers like the CSV)

   Kind-level edits become a sibling `kindEdits {<key>: {label?, colour?}}`, plus new kinds. Hand-added boxes become a sibling `addedBoxes: [...]`. Everything stays an overlay beside an immutable model: model.json, its stamp and the storage key never change. Because the store reads edits as plain objects, code from this step ignores a later field instead of failing.
2. **The selection and card.** "Select a box (Orbit click or Walk aim), act on it in a card" is the entry point for re-kind, name, move and turn. The marker outside `late` and the fixed card place are reused.
3. **Download transforms.** The CSV row filter and the Max line filter (prefix from `model.maxPrefix`, a counted match) become row and line rewriters for the other edits, keyed the same way.
4. **The carry matcher.** The one-to-one fingerprint match is the same identity the Max round trip needs to apply a Send file to a later drawing revision. U-10.6 stays the principle: a unique match or a flag, never a silent wrong match.
5. **The Max round trip.**
   - The Send file's "deleted boxes" means ids the script built that have no box left. The API turns each into `{removed: true}` in the edits of the version whose stamp the Send file names (line 2 of the script; `modelSha1` where the stamp is not enough, 5.1).
   - "Moved, turned, resized" becomes `place`.
   - Whether applying a Send file also cuts a new version (plan 9 Nov) is that milestone's choice. The overlay does not preclude it: "bake model + edits into a new version" stays possible, because the closure rule keeps the record valid against the API's model rules (unique ids, every `on` naming a piece, no renumbering).

**What this must not preclude**, as rules for later steps:

- **The closure rule gets one exception later.** A dependent that has its own `place` edit (moved in Max or in the app) no longer cascades with its support; it stands where it was put. The rule lives in one function per language, sharing one case file, so it can change in one place.
- **Ids are never rewritten or renumbered by edits.** Added boxes will need ids the vendored generator accepts (`<floor>-<kind>-<digits>`, unique), for example numbers above the kind's highest (`L1-seat-901`). That is decided with adding boxes, not here.
- **Drawing-level set-aside stays separate.** The Check step's set-aside (`build/fixes.py`) removes drawing items for everything (walls, door finder) and needs a rebuild. Box deletion never touches walls, rooms, the door finder or stairs (plan 2.5: "walls and slabs stay the drawing's").
- **No `BuildSettings.fixes`.** The record is deliberately not in `BuildSettings.fixes`, which the door-finder round (next action 16, decision L) is changing and which has the 5,000-fix cap.

---

## 8. Files to change, and the tests

### 8.1 How the step works

- One step, **BX**, on branch `box-delete`. Its own temp folder is `%TEMP%\wt-bx`, and its ports are web 5750, API 8750, preview 4750 and CDP 9750, all free in every table of `app/CLAUDE.md`.
- `WALKTHROUGH_DATA_DIR` and `WALKTHROUGH_CACHE_DIR` go under `WT_TMP`. The step never writes `app/data`, never uses 5710 or 8710, never commits (the main session does) and never deploys.
- It touches files owned by C, D (one test literal), A/R4, E/R5 and F/R6, listed below. It also touches the scaffold's contracts and `models.py`, under the main session's written authorisation, as DEL did. `test/harness/context.ts` stays untouched (3.3).

### 8.2 Viewer: `packages/viewer`

| File | Change |
|---|---|
| `src/contracts.ts` + `docs/contracts.ts` | 3.3 (authorised, byte-equal) |
| `src/furniture/types.ts` | `ItemState.removed`; `FurnitureState` gains `removedIds()`, `editBoxes`, the selection hooks and the undo stack; `LegendActions` gains `removePiece`, `restorePiece`, `restoreAll`, `undo` |
| `src/furniture/index.ts` | starting edits from `ctx.project.pieceEdits` (next to `:48`, closed); `stops` with `!removed`; actions and api methods; `changedPieces(source)` on bus `pieces`; live `kinds().count`; `pieces().removed`; `csv()` passes the removed set; live-only legend when `editBoxes` is off |
| `src/furniture/boxes.ts` | `syncKind` visibility with `!removed`; `setRemoved(p, on)` maintains `fl.late` |
| `src/furniture/logic.ts` | `furnitureCsv(model, heights, removed?)`; `closeRemoved`; `groupsOf` (restore lines); `undersideOf` untouched |
| `src/furniture/pick.ts` (new) | the pick taken out of `hover.ts:39-50`, at any screen point |
| `src/furniture/hover.ts` | uses `pick.ts`; the "Click to select" line and the pointer cursor when `editBoxes` is on; no tip while the card is open |
| `src/furniture/select.ts` (new) | Orbit click selection, Walk/Ghost aim, the marker (outside `late`), the card at the top right, the toast, Delete / Ctrl+Z / Esc with arming, the undo stack |
| `src/furniture/legend.ts` | live counts in the label span; `data-empty`; the edit-hint line; the `furniture-removed` line, the Restore all undo and the restore popover (or `restore.ts`, new) |
| `src/furniture/css.ts` | card, popover, toast (z 7), `data-empty` |
| `src/viewer.ts` | `bridgeEvents`: bus `pieces` (removed/restored) → `boxeschange`; `guardFurniture` lists the five new methods (inert after dispose: writes false or `[]`, reads answer the last state); `Viewer.getPieceEdits` / `setPieceEdits` next to `:179-180` |
| `src/core/context.ts` | resolves `editBoxes` (optional, `=== true`; storage key unchanged) |
| `src/offline/entry.ts` | `projectOf` passes `pieceEdits` only when present |
| `test/unit/replay/replay.test.ts:45` (D) | `fakeFurniture` gains five stubs |

**Viewer tests.**

- `test/unit/furniture/remove.test.ts` (new):
  - remove, restore and restore-all, and Restore all then Undo giving back the exact map;
  - the cascade on the mini fixture (`L1-table-001` carries `L1-computer-001` and `L1-printer-001`) and the group restore;
  - colliders out and back; mesh hidden and out of `late`; `apply()` keeps it hidden;
  - live counts and `data-empty`; with `editBoxes` off, no row for an emptied kind and no Keep doorways tick without a live approach box;
  - `pieces()`'s `removed` field present only when removed;
  - `setPieceEdits` closes the map, ignores unknown ids, emits nothing public and clears the undo stack;
  - bus `pieces` sources (undo of a delete emits `restored`); Reset heights leaves edits alone;
  - the popover: `boxes-restore-open`, `box-restore`, `boxes-restore-all`, `boxes-restore-undo`, grouping dependents under their support, the line absent with `editBoxes` off or nothing deleted;
  - the restore cases of 2.6 (floor not showing, kind hidden, Walk);
  - a hostile `<img onerror>` kind label, family and floor name stay text in the popover;
  - the live Keep doorways tooltip count.
- `test/unit/furniture/select.test.ts` (new):
  - a click selects; a drag of 4 px or more does not; `detail` 2 clears;
  - not in Orbit while locked or with the camera open; touch is ignored;
  - Walk/Ghost aim at the screen centre within 6 m, and Delete with the toast;
  - the Delete key with the `typing()` / `ours()` guard and the arming (a `pointerdown` in the panel disarms it); Ctrl+Z; Esc;
  - the card's lines: a hostile kind label, family and floor name stay text; the builder note on a loose-shapes piece and on a cabinet with fronts; no "side by side" line; the cascade warning text;
  - the tip's "Click to select" line on and off; the cursor;
  - Undo; clearing on mode, floor, tick, bus `pieces`, `replayPhase` and dispose;
  - the marker colour is in no kind's colour;
  - the marker is reached by neither `fadeLate` nor `restoreLate` (the real functions from `replay/apply.ts` on a fake `late` list). After `fadeLate(…, 0)`, a clear and a new select, the marker is visible with material opacity 1.
- `logic.test.ts`:
  - `furnitureCsv` with no third argument equals today's text byte for byte;
  - with removed ids it equals the golden minus those rows;
  - `closeRemoved` against `test/fixtures/furniture/close-removed.cases.json`.
- `install.test.ts`: **unchanged pins.** It gains one assertion that the legend is identical with `editBoxes: false` and no edits.
- `core/viewer-events.test.ts`: the literal `FurnitureApi` at `:45` gains the methods; the bridge passes removed/restored but not api; the guard is inert after dispose.
- `testhook/hook.test.ts`: `projectOf` passes `pieceEdits` when present and adds no key when absent (the existing pin at `:122-123` unchanged).
- `test/harness/furniture/furniture.spec.ts` (real WebGL; this page has no modes and no replay, `furniture-page.ts:1-4`):
  - click a projected box, then the marker and card;
  - Delete, then the box is not drawn and a knee-height `rayHit` passes its place (as the existing collider test does);
  - restore;
  - with the popover open near the bottom, `elementFromPoint` at the centre and the lower quarter of Restore all is the button itself;
  - the panel still fits at 1366×768 with the extra lines.

### 8.3 API: `services/api`

| File | Change |
|---|---|
| `walkthrough_api/models.py` | `PieceEdit`, `HeightOverrides.piece_edits`, `HeightsUpdate.piece_edits` (authorised) |
| `store/base.py` | `HeightOverridesFile.piece_edits: dict[str, Any] \| None`; `Store.write_overrides(..., piece_edits=None)`; `Store.download_bytes` (authorised record change) |
| `store/local.py` | `write_overrides` keep, replace or absent (values built by hand); `download_bytes`; the `create_version` carry block plus `source/carried-edits.json` |
| `piece_edits.py` (new, pure) | `canonical`, `close_removed`, `live`, `order`, `carry`, `filter_max_script` |
| `views.py` | `overrides_of` returns the live `pieceEdits` |
| `routes/furniture.py` | body only: validate, write, 412 details (`pieceEdits` only when non-empty) |
| `routes/downloads.py` | body only: CSV `removed`; Max bypass or filter (prefix from `model.maxPrefix`) |
| `furniture_csv.py` | `removed=` |
| `seed/build.py`, `seed/__main__.py` | re-map kept edits when `modelSha1` changed; help text |

`apps/web/openapi.json` and `apps/web/src/api/generated/**` are regenerated by `npm run gen:api`, never edited by hand.

**API tests.**

- `tests/test_bx_piece_edits.py` (new):
  - a PUT with edits, then GET and `getVersion` show them;
  - left out = kept (a heights-only PUT after a delete);
  - `{}` clears them, and the file is byte-equal to a heights-only file;
  - 422 `invalid_piece_edits` with `unknownIds`; a pydantic 422 for `{"removed": "yes"}` and for an unknown inner key;
  - closure and canonical order; `removed: false` dropped;
  - If-Match with a stale revision gives 412 with `pieceEdits` in the details when there are edits, and without it when there are none;
  - CSV with edits = golden minus rows (bank v2, suite);
  - Max: first, on all five stored scripts (BB, PS, HL, TB, PSL), every model piece has exactly one line. Then, with edits: the stored script minus those lines plus the line-3 comment naming the Max object names; line 2 equal to the stamp; the attachment name unchanged; a wrong prefix or a missing line gives 500 `store_error`;
  - Max without edits is the identical `FileResponse`;
  - the offline payload embeds the key, and Node equals Python;
  - carry:
    - the same model carries everything;
    - a moved piece (more than 10 mm) is not carried;
    - a duplicate twin in the new drawing is not carried;
    - **two old duplicates, one deleted, one left in the new drawing: nothing is carried** ("matches 2 old pieces");
    - a turn of 179.8° against 0.1° matches;
    - a renumbered id maps to its new id;
    - only tops are carried: a computer that went with its table and now stands on a kept table stays ("was on a deleted support");
    - a new piece on a carried table is cascaded;
    - the content of `carried-edits.json`;
  - a heights-only carry still writes as today;
  - seed: `--force` keeps the edits with an unchanged model, re-maps them (with `carried-edits.json`) with a changed `modelSha1`, and `--reset-overrides` drops them;
  - a corrupt value, an unknown id or an extra field in the file is ignored by GET, `getVersion`, CSV and Max (no 500).
- Updated pins: `test_routes.py:145` and `:272ff` (`pieceEdits: {}`), `test_openapi.py` (regenerated bytes).
- Unchanged and must pass: the `fixtures/csv` goldens, `test_routes.py:200-210`, `test_offline.py:118,224-228`, `test_store.py:75-88,207-213` and `test_hardening.py:268-285` (including the exact `:270`).

### 8.4 Staff app: `apps/web`

| File | Change |
|---|---|
| `src/lib/useHeightsSaver.ts` | `edits`, `editsDirty`, `changeEdits`, PUT body, success, 412, adopt, `onRemoteEdits`, `editsUnsaved`, keepalive size, `updateHeightCaches`, `sendUnsent` |
| `src/lib/heightsOutbox.ts` | optional `pieceEdits` and `base.pieceEdits`; `mergeEdits`; `sameEdits` |
| `src/api/client.ts` | `conflictOf` reads `pieceEdits` (missing = `{}`) |
| `src/lib/viewerProject.ts` | `pieceEdits` into the project; `editBoxes` third parameter, default false, key added only when true |
| `src/components/ViewerHost.tsx` | `onPieceEditsChange` and a second `viewer.on` |
| `src/components/HeightsStatus.tsx` (or a sibling) | the `boxes-deleted` count |
| `src/pages/ProjectVersionPage.tsx` | wiring as in 6.2 |
| `src/lib/format.ts` | 'Furniture saved'; the four download tooltips |
| `src/components/DownloadsMenu.tsx` | the Max item waits only on `editsUnsaved` |
| `src/build/SaveStep.tsx` | the label |
| `test/fake-viewer.ts`, `test/mock-api/core.ts`, `test/e2e/web-kit.ts` | 6.2 |

**Web tests.**

- `useHeightsSaver.test.tsx` and `heightsSync.test.tsx` (new cases; the existing pins unchanged):
  - a delete and a height coalesce into one PUT;
  - a heights-only PUT has no `pieceEdits`;
  - **B adopts A's deletion and then types a height: the body is `{heights}`, and the deletion is kept**;
  - **a revisit replays a heights-only outbox entry on a version with saved deletions, then a height is typed: the deletions are kept**;
  - a 412 per-id merge keeps the other tab's deletion and this tab's restore;
  - a 412 with clean edits takes theirs and calls `onRemoteEdits`;
  - a success whose map differs from the one sent calls `onRemoteEdits`;
  - the outbox round trip with edits; an old entry parses;
  - adopt takes edits only when idle and not dirty;
  - a version switch flushes edits to the old path;
  - a keepalive body over 60 KiB goes without keepalive.
- `DownloadsMenu.test.tsx`:
  - heights-only saving or failed leaves Max a link (the existing pins);
  - pending or failed edits make Max wait with its own tooltip;
  - the retitled CSV and offline tooltips (`:86,103`).
- `format.test.ts:75`: the new status text.
- `pages.test.tsx`: `boxeschange` reaches the saver; `onRemoteEdits` calls `setPieceEdits`; the status text pins listed in 6.2; the `boxes-deleted` count.
- `ViewerHost.test.tsx`: `boxeschange` reaches the latest callback.
- `viewerProject.test.ts`: `pieceEdits`; `editBoxes` only when true (`:73,78-81` unchanged).

### 8.5 Browser: `tests/e2e/box-delete.spec.ts` (new)

The new spec uses raw `[data-wt=…]` selectors, because `tests/e2e/lib/target.ts` is frozen. It has two arms.

**Real API on a freshly seeded temp store, with the real viewer:**

- Click a box projected through `__host.furniture.meshOf(id)`, see the card, press Delete.
- The box is gone, there is no collider, and Walk passes.
- The status reads "Furniture saved", and `boxes-deleted` is visible **without scrolling** at 1366×768.
- Reload: still gone.
- The CSV download lacks the row. The Max download lacks the line and has the comment with the object name.
- **Walk:** enter Walk at an address in front of a known box, press Delete at the crosshair, and see the toast. Ctrl+Z brings it back.
- **The offline download:**
  - the deleted box's mesh is not visible at any of several `__build.seek(T)` values up to 1, under `?build=play&test=1` (the only browser check for risk 4);
  - after `skip`, `__host.furniture.pieces()` marks the id removed;
  - clicking a projected box shows no `box-card`, `box-delete`, `furniture-removed` or marker.
- **The replay in the staff app:** select a box, open Replay, skip, select again, and the marker shows.
- **Restore all, then Undo, then Restore all again:** everything is back. The CSV and the Max script are byte-equal to before. In the offline file the payload's `overrides` has no `pieceEdits` key and every box is drawn (its revision and `updatedAt` have moved, so it is not byte-equal).
- **Two tabs,** a delete in one and a height in the other: both are saved (real API only).
- Clean-up in `afterEach` and through the shared `resetHeights` helper, which now sends `{heights: {}, pieceEdits: {}}`.

**Mock arm** (`WT_SERVE=web`, `VITE_FAKE_VIEWER=1`):

- the fake remove control → the PUT body is `{heights, pieceEdits}`;
- the Max item waits while that save is refused and stays a link during a heights-only refusal.

`web.spec.ts`: the text pins move to "Furniture saved" (6.2) and the tooltip regex at `:466` moves to the new text. `:447-475`'s Max behaviour stays.

**Leak.** One case in `leak.spec.ts` style mounts through `__wtvMount.mount({ editBoxes: true })`, selects a box, deletes it, opens the popover and unmounts. It then expects gpu 0/0 and no registrations.

### 8.6 Regression guards (all must stay green, unedited)

- `walk-parity.test.ts` / `walk-parity.json` (furniture is not in its rig; walls and glass untouched).
- `test_r_old_rule.py` and `test_vendor.py` (run by `npm run test:builder`; the builder is not touched).
- The CSV goldens; the stored Max script equals the prototype file; offline Node equals Python; heights-only `overrides.json` bytes; the heights-only PUT body `{heights}`.
- `install.test.ts` legend, bus and storage pins; e2e `furniture.spec.ts` 218-241, 306-345, 617 and 672-683; `web.spec.ts:447-475`'s Max behaviour; `test_hardening.py:270`.
- The eight uploaded versions (acc-9nov) walk value for value as on 9 Nov (`docs/rooms/reference/upload-walk-9nov/`).
- `outside.txt` and `versions.sha1` unchanged.
- Old versions and every `app/data` version behave identically (none has `pieceEdits`).

### 8.7 Checks to run

| Check | Note |
|---|---|
| `npm run check:pins` | |
| `npm run typecheck` | the five tsconfigs, including the scaffold's `test/harness/context.ts`, untouched |
| `npm run test:unit` | |
| `npm run test:api` | and `WT_INTEGRATION=1` |
| `npm run test:builder` | runs `test_r_old_rule.py` and `test_vendor.py` |
| `npm run gen:api` | twice; the second run changes no byte |
| `node tools/check-openapi-additive.mjs` and `--base 9eb2d58` | |
| `npm run build` | reads `app/data` only |
| `node tools/rooms/reference.mjs versions --check` and `outside --check` | |
| `node tools/rooms/acceptance/run.mjs --only offline` | the eight acc-9nov offline files with the new template, under the step's `WT_TMP` |
| `upload-walk.spec.ts` on those files (`WT_UPLOAD_OFFLINE_DIR`, `WT_UPLOAD_DATA_DIR`) | the report compared with `upload-walk-9nov/`, as RI did (`RI.md:305-308`) |
| harness `furniture.spec.ts` | |
| e2e `furniture.spec.ts`, `offline.spec.ts`, `web.spec.ts`, `deletes.spec.ts`, `box-delete.spec.ts` | both arms |
| `leak.spec.ts`, `web-leak.spec.ts` | the app bar text changed; the new leak case |

Timed fps checks are re-run alone before any diagnosis. The results go in BX.md.

### 8.8 Housekeeping (the main session, after review)

- `docs/contract-issues/BX.md` (the step writes it).
- DESIGN 9.4, 10.2, 11.2, 13, 15.3, 16 and 18.7.
- `STATUS.md`, with the one-line instruction "Orbit: click a box, Delete · Walk: aim, Delete · Ctrl+Z undoes"; plan next actions 12 and 18 and the hours note.
- The product doc (memory: keep the plan, doc and viewers in sync), with the same instruction and the 3D team's note on deleting already-built boxes by object name. The prototype viewers are read-only since the app began, so they are not updated.

---

## 9. Risks and hours

### 9.1 Risks

| # | Risk | Mitigation |
|---|---|---|
| 1 | The contract change needs the main session's authorisation (`models.py`, the store records, both `contracts.ts` copies, one D test literal) | Additive only; written up in BX.md; the additive check against both bases; `context.ts` untouched |
| 2 | FastAPI marks the defaulted `pieceEdits` as required, or splits `PieceEdit` into `-Input` / `-Output`, and the additive check fails | Unlikely (no pairs today; `ErrorBody.details` precedent); check `openapi.json` first; the fallback is `dict \| None = None` (3.2) |
| 3 | Deletions are lost or come back (a stale copy in the saver, an outbox replay, a cache not updated, a re-create from a stale `detail.overrides`) | The `editsDirty` flag (send only real edit changes); `updateHeightCaches` carries the edits; a per-id three-way merge; `onRemoteEdits` on takeover, merge and server closure; tests in 8.4 for both flows |
| 4 | A box flashes during the build replay (`late`) | `late` membership follows removal; the e2e seek check on the offline file |
| 5 | Click versus orbit drag, or the double-click to walk, misfires | Own 4 px check; `detail === 1` only; unit and harness tests |
| 6 | Panel overflow at 1366×768 with the extra lines | Lines shown only with `editBoxes` (the hint) or when something is deleted; the list is an overlay; the app-bar count is the always-visible sign; an e2e size check |
| 7 | Carry-over matches wrongly | Tight tolerance (10 mm, 0.5° modulo 180/90), one-to-one against old and new pieces, tops only, never by bare id; the `carried-edits.json` record |
| 8 | Carry-over misses (boxes come back) | Visible; the tick's label says so; "For the owner", 2 |
| 9 | Max: the filtered script and an empty `furnAll` body have never been run in real 3ds Max | Ask the 3D team to run the bank script with three boxes deleted (one table with a computer on it) before calling it done; the box proxies were not yet run in Max either (memory) |
| 10 | Rolling the code back makes saved files with `pieceEdits` unreadable (`extra='forbid'` at the top level) | Recorded in BX.md; "Restore all" before a rollback empties the key |
| 11 | Stale built counts (project card, version counts, the panel intro, replay captions, top view) | Accepted as build-time text, documented in DESIGN 13; the legend and app bar are live; "For the owner", 4 |
| 12 | The frozen route texts ("byte for byte as seeded", the `carryHeights` text) under-describe the behaviour | Recorded in BX.md and DESIGN 18.7; the texts cannot change additively |
| 13 | A Delete in Walk removes a box staff did not mean | The marker shows the aimed box first; 6 m reach; the toast with Ctrl+Z; the Restore list |
| 14 | A seed with a changed converter deletes other boxes by rank id | `modelSha1` compare and re-map in the seed's commit phase; GET answers only live ids |
| 15 | A keepalive save over 64 KiB is refused | Edits sent only when dirty; over 60 KiB without keepalive; the outbox keeps it |

### 9.2 Hours (hands-on developer)

| Part | Hours |
|---|---|
| Viewer state, closure, colliders, `late`, counts (live and client legend), API, events, guard, contracts | 2.5 |
| Picking, marker, card, Delete / Ctrl+Z / Esc with arming, undo stack, cursor and hint line | 3.5 |
| Delete from Walk and Ghost at the crosshair, aim marker, toast ("For the owner", 3) | 1.5 |
| Legend line, Restore list, Restore all undo, restore cases | 2 |
| CSV filter (TS and Python), offline entry | 1 |
| API record, models, PUT validation and closure, live reads, 412, `gen:api`, additive check | 2 |
| Max download filter, counted match, object-name comment | 1 |
| Carry-over (one-to-one, tops, turns), record file, seed re-map, Save label | 2 |
| Staff app saver (dirty flag), outbox, merge, adopt, caches, host, page, status and count, downloads, test doubles | 3.5 |
| Tests: viewer unit and harness, API, web, e2e, leak | 5 |
| Guard runs (acceptance offline, upload-walk compare, reference checks) | 1 |
| BX.md and doc amendments | 0.5 |
| **Total** | **~26 h (range 20–34 h)** |

What this means for the plan:

- The plan's "Editing the furniture boxes" row is ~20 h: kinds about 8 h and boxes about 12 h, delete included.
- This delete alone takes ~26 h (24.5 h without the Walk part).
- About 10 h of it is foundation the rest of the row reuses:
  - the selection, marker and card;
  - the saved record with its saver (dirty flag), merge and carry;
  - the download filters.
- The rest of the row (rename and recolour a kind, re-kind, name a piece, add, move, turn and size a box, and their CSV and Max output) should then take about 12 h on that foundation.
- So the row becomes **about 38 h (+18 h)**. The Max round trip row (~20 h) reuses the same record and matcher and stays as planned.

---

## For the owner

1. **Hours.** Should the plan's "Editing the furniture boxes" row go from ~20 h to ~38 h (+18 h), and core hours with it? **Recommended: yes, record it.** The delete takes ~26 h, including foundation the rest of the row needs. A cheaper alternative would have no Restore list and no carry-over into new drawing versions, and would save about 4 h. But a deletion noticed after the visit could then not be undone one box at a time, and every deletion would be lost when a new drawing version arrives.
2. **A note when deleted boxes did not carry into a new version.** **Recommended: yes, in its cheapest form**, about 1.5 h, not in the ~26 h. It would be one line on the new version's page, for example "2 deleted boxes of v2 are back: not found in the new drawing", counted from `carried-edits.json`. It needs one more additive API field, so it is built only on your yes. Without it, a returned box is found only by someone who looks.
3. **Deleting from inside Walk** (aim the crosshair at the box, press Delete). **Built in this step by default** (about 1.5 h, included above), because the crosshair already exists and most of the parts are built here anyway. The Orbit-only way costs more than it looks:
   - pressing 1 returns to the overview camera;
   - a lower floor's boxes cannot be clicked until that floor is chosen;
   - staff must zoom in to find the box;
   - double-clicking back drops the walker at the clicked spot, not where they stood.

   Say no if you want deleting in Orbit only; that saves about 1.5 h.
4. **The client's offline file still says "185 coloured boxes".** The panel's intro is written at build time, so after deletions it states the built count. **Recommended: accept it** (documented). The alternative is a neutral line in the client's legend, such as "3 boxes taken out by the design team" (about 0.5 h).

### Decided by the main session (16 Nov 2026)

The owner's standing instruction is to pick sensible defaults rather than ask; each recommendation above is taken.

1. **Hours: yes.** The plan's "Editing the furniture boxes" row becomes about 38 h (+18 h); the plan, STATUS and the
   product doc are updated with the measured result after the step.
2. **The note on deletions that did not carry over: yes, built in this step** (about 1.5 h more, so the step is about
   27.5 h). The new version's page shows one line, for example "2 deleted boxes of v2 are back: not found in the new
   drawing", counted from `source/carried-edits.json`. The API gains one more additive, optional field for it (on the
   version detail, absent when nothing came back); the builder of the API part names it and records it in BX.md.
3. **Deleting from inside Walk and Ghost: yes**, as designed (2.2b).
4. **The client's offline file keeps the built count in its intro: accepted**, documented in DESIGN 13 and BX.md.

**Contract changes authorised** for this step, additive only, as for DEL: `services/api/walkthrough_api/models.py`
(`PieceEdit`, `HeightOverrides.piece_edits`, `HeightsUpdate.piece_edits`, the field of point 2), the store records in
`store/base.py` (`HeightOverridesFile.piece_edits`, `Store.write_overrides(..., piece_edits=None)`,
`Store.download_bytes`), both `contracts.ts` copies (3.3, byte-equal), and the D-owned test literal
`test/unit/replay/replay.test.ts:45`. `test/harness/context.ts` stays untouched. Everything goes in
`docs/contract-issues/BX.md`; `check-openapi-additive` must pass on both bases.

---

## Review notes

Every finding was checked against the code. All of them were correct on the points checked, among them:

- `test_hardening.py:270` is an exact dict equality;
- `test_routes.py:145` pins `overrides`;
- `Record.to_json` drops `None` only at the top level;
- the hint line is z 6 with pointer events;
- `[data-wt=cross]` exists;
- `n` counts shapes;
- `rot` is normalised modulo 180/90;
- `context.ts` builds `ResolvedOptions` from a Partial;
- the furniture harness page has no modes or replay;
- `fadeLate` runs before `phaseChanged`;
- `web.spec.ts:468` pins the Max item;
- the Max line format is kind, name, floor index, id.

Where a finding was worked in differently from its suggestion:

| Finding | Decision | Why |
|---|---|---|
| Data 4 (412 details) | Took the first option: `pieceEdits` in the 412 details only when non-empty, missing read as `{}`; `test_routes.py:145` added to the updated pins | Keeps `test_hardening.py:270` exact and matches "empty = absent" in the file |
| Data 8 (nested record) | Read leniently (plain objects, `live` filters), not a strict 500 | The design promises an odd file never breaks the version page; it also lets this code ignore a later step's fields |
| Data 10 (Restore list brings back a separately deleted computer) | Accepted in writing (2.5); Undo made exact through the visit stack, cleared on remote changes | The record keeps no history, and adding one is not worth it for this edge |
| Data 6, Tests 2, Staff 8 (Max item waits) | The Max item waits only on unsaved edits, so `pages.test.tsx:358`, `web.spec.ts:468` and `DownloadsMenu.test.tsx:78-89,105` stay unchanged rather than being listed as changing; only the tooltip pins change | The script carries no heights |
| Staff 2 (z-order) | Card moved to a fixed top-right spot (z 7) rather than clamped near the click; the popover is z 7 and clamped above the hint | The fixed spot also answers Staff 10 (the card covering the next chair) |
| Staff 6 (restore lines) | "near <room name>" not added | It needs a rooms lookup per floor; the family, the floor and the marker on restore identify the box |
| Staff 10 (highlight) | No face-material swap; a separate marker group outside `late` instead | Swapping a mesh's material would be captured by the replay's `recordLate` look; the separate marker also fixes Tests 4 |
| Staff 11 (Ctrl+Z) | Widened from "the last action" to a visit-long stack of inverses, cleared on `pieces` source `api` | The same cost, and it stays exact |
| Staff 5 (Walk delete) | Built by default rather than only re-estimated | The premise of the deferral was wrong, and the owner's requests come from walking; the owner can still say no |
| Staff 12 (carry note) | Kept as an owner question, with the recommendation changed to yes | It needs another additive API field, so the owner decides |
| Staff 7 (client legend and intro) | Live-only legend applied only with `editBoxes` off; the staff app keeps `(0)` rows | The staff app needs a stable layout and access to typed heights while deleting; the intro is owner question 4 |
| Tests 1 (typecheck) | Took the optional `ResolvedOptions.editBoxes` | It leaves the scaffold's `context.ts` untouched; the three typed `FurnitureApi` literals are listed |
| Tests 6 (pins) | Code shaped so the `projectOf`, `viewerOptions` and `onRemote` pins hold (no null key, `editBoxes` only when true, a separate `onRemoteEdits`); the "Heights saved" pins do change and are all listed | Fewer pins touched |
| Tests 3 (harness checks) | The replay-flash check moved to `box-delete.spec` on the offline file with `__build.seek`; the harness keeps a `rayHit` check | The offline file is the client's real case, and the harness page has neither a replay nor Walk |
