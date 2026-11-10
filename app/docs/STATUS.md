# Where the application stands (9 Nov 2026)

The second milestone is built: **you can now upload a DWG in the staff app, check it, and build it into a 3D model that is
saved as a new version of a project.** A final check was run on 9 Nov from a clean start, separate from the steps that
built, reviewed and fixed it.

**Every test suite passed, every acceptance criterion that must pass did, and your path through the app worked from
start to finish, for the bank and for the house.** The bank, uploaded again from its two DWGs through the screens, gives
version 2's model byte for byte. The check found **one fault** that the tests had missed: on the Check step, giving a
furniture family a kind did nothing for some family names. **It was fixed after the check, the same day, with tests**,
and so was the gap found beside it: the furniture size limits now have their boxes on the Floors step (see *What
failed*). A separate reviewer then checked the fix: the house and the bank through the screens again (the house now
saves the acceptance run's model byte for byte, none of its 13 families grey), and every test suite again, all passing.

Nothing has been put online or deployed. Everything runs on this laptop only. Nothing was committed by the check (the last
commit then was `6755e81`, the review's fixes of 9 Nov); the fix, its check and these notes were committed afterwards on
the branch `milestone-upload`, which was then merged into `main` (on this laptop only; nothing is pushed anywhere).

## What the app does now

Everything of 4 Nov still works: the project list, the project page with the 3D viewer (Orbit, Walk, Ghost, the Camera
and its photos, the floor buttons, the build replay, the furniture boxes), versions, saved furniture heights and the
Downloads menu (3ds Max script, furniture list, offline viewer). New in this milestone:

### Uploading a drawing and building it, step by step

1. **New project.** On the project list, **New project**: the name, short name, project number and the office (or "New
   office..."). The office matters: the app remembers each office's layer roles. On a project's page, **New version**
   starts the same steps for a new version of it.
2. **Upload.** Drop the DWG files on the page (several at once; a DXF exported from AutoCAD works too). Each file goes up
   in pieces with its own progress bar. You can leave the page: when you come back and pick the same file, it carries on.
   Files up to about 315 MB are accepted.
3. **Files.** The app turns each DWG into a DXF with LibreDWG (a free converter that runs as a separate program) and
   checks that nothing was lost on the way:
   * green **ok**: nothing lost;
   * amber **minor**: nothing in the plan is missing, a few items only moved to layer 0;
   * red **loss**: parts were lost; the screen lists them and where they sit, and advises exporting a DXF from AutoCAD;
   * **failed**: the file could not be converted, with the reason.

   It also works out the units from the size of the door symbols. When the file's own setting disagrees (the house says
   inches, its doors measure right in millimetres), you press **Confirm**.
4. **Layers.** One row per layer, with what is drawn on it. The app suggests a role for each layer (wall, glass, door,
   window, column, stair, railing, furniture, room name, level tag, grid ... or ignore) from the office's memory, the
   layer's name and its contents. No AI. Doubtful suggestions are marked "check" and can be listed on their own. You
   change a role with its drop-down; everything saves by itself.
5. **Floors.** One card per floor: which file; which part of the sheet (the whole file, or a box you draw round the plan
   when several floors share one sheet); the level (typed, or picked from the drawing's own level tags); the wall height;
   door and window heights; and how the floor lines up with the first one (grid lines, the drawing origin, or two points).
   Below: the names used for photos and for the 3ds Max file, and the build options.
6. **Build.** A short checklist says what is still missing, if anything. The build then runs on this computer (one at a
   time; a second one waits its turn) with a progress bar and **Cancel**. At the end: the counts per floor, a top view
   and a 3D preview.
7. **Check.** Each floor's plan with what was built drawn over it, and a list of flags: things to look at, such as
   doubtful openings, lines on a wall layer with no partner line, lost blocks, large areas inside the walls with no
   floor, and furniture of no known kind. You can set aside items or whole blocks (and restore them), change an opening
   (door, window, passage or not an opening; its head and sill), accept or refuse a suggested wall along a room outline,
   give a furniture family a kind, and change heights; then **Rebuild**, and the screen lists what changed. Fixes are
   kept: they apply at every rebuild, and again when the same drawing is uploaded later.
8. **Save.** The result becomes a new version of the project and opens in the viewer. The furniture heights of the
   previous version carry over, and the office remembers the layer roles. The Downloads menu gives the 3ds Max script
   (now written from the model itself: every part live, never Editable Poly, furniture as boxes), the furniture list and
   the offline viewer.

A draft that is not saved yet stays on the project's page with **Continue**. Uploaded drawings stay on this computer: they
are never given to clients and never go into git. The furniture list now guards against Excel formulas (a name that
starts with = + - or @ is written as plain text), which settles the question left open on 4 Nov.

## How to start it (one command, unchanged)

Open PowerShell in `C:\Users\DWP2\Desktop\Project walkthrough` (the project folder, or its `app` folder: since 10 Nov
both work) and type:

```
npm run dev
```

Then open **http://127.0.0.1:5710** in Edge or Chrome (type `127.0.0.1`, not `localhost`). To stop it, press **Ctrl+C**
in the PowerShell window. Nothing new needs installing: the converter and the builder's own Python are already set up.
Uploads and drafts are kept in `app\data`; the converted DXFs go to a cache folder,
`C:\Users\DWP2\AppData\Local\walkthrough\cache`.

Since 10 Nov, `npm run dev` no longer restarts the app's server by itself when its code changes: on Windows that restart
stopped the whole app in your PowerShell window (your check of 10 Nov, see *What failed*). So after an update, stop the
app with **Ctrl+C** and start it again with `npm run dev`; if it says a port is in use, wait a few seconds and try again.
When you press Ctrl+C, PowerShell shows two "Terminate batch job (Y/N)?" lines and its prompt comes back at once:
nothing needs typing. A build that is running when you stop the app finishes on its own; when the app is back it shows
as done (or, if the builder could not finish, as interrupted: then build again).

## Your path through the app (final check, 9 Nov)

Run in Edge on `npm run dev`, through the screens only (nothing typed into the API), on a copy of the store. The real
`app\data` was never touched: it is still exactly as seeded (54 files, all identical).

**The bank, from its two DWGs: 15 of 15 steps worked.**

1. The project list showed the four projects. **New project**: "Bangkok Bank, Sampeng Branch", project no 26-0216, a new
   office "Owner Revit".
2. **Upload**: the two DWGs from the project folder went up in under a second.
3. **Files**: both read in about 35 s, both green **ok**.
4. **Layers**: 36 layers. With a new office (nothing remembered yet) 28 suggestions were already right; 8 roles were
   changed with their drop-downs to the bank's (for example `G-ANNO-TEXT` to room names, `A-GENM` and `E-COMM` to
   furniture).
5. **Floors**: levels 0 and 3.70 m, walls 3.70 m; the photo name, Max prefix and Max file name typed. No issues.
6. **Build**: the checklist was clear, the progress bar showed, done in 21 s.
7. **Check**: the plans with the parts, openings and flags drawn over them. The family "Fritz-Hansen_SH200 - Default"
   (8 chairs) was grey: given the kind **Chair / stool**; **Rebuild** (22 s); the list of changes showed chairs 67 -> 75.
8. **Save**: version 1, with the label the app proposes ("9 Nov 2026: built from I1201 ... and I1202 ...").
9. The version opened in the viewer (one 3D window, no error). **Walk**: the view moved with W and turned with the arrow
   key.
10. **The model is version 2's, byte for byte** (stamp `c3a9408304a2`), and so is the furniture list (CSV).
11. **The 3ds Max script.** The download, `Bangkok_Bank_Sampeng_v1.ms`, is **not** byte for byte the same as
    `bank_test\Bangkok_Bank_Sampeng.ms`, and is not meant to be: 859 of the 867 lines are identical; the other 8 are
    replaced by 11 lines of text: the comments at the top (they now say "built by the walkthrough app ... 9 Nov 2026" and
    name LibreDWG 0.14), two notes stored on the datum object ("Source", and a new "Built" line) and the window title
    ("Bank branch" instead of "Bank branch (test)"). Everything the script builds in Max is the same. The same saved
    model written with the 27 Oct texts gives `Bangkok_Bank_Sampeng.ms` **byte for byte**.
12. The offline file from the Downloads menu opened from disk with the network switched off.

**The house, from its one DWG, with its floor areas drawn: 11 of 11 steps worked; one fault found.**

1. New project "Test Sukhumvit Residence", no office. Upload: the one DWG.
2. **Files**: amber **minor** (nothing in the plan missing; 1 item moved to layer 0). Units: "the file says inches, its
   doors say millimetres (28 doors measure right in millimetres, 0 in inches): read in millimetres", confirmed with the
   button.
3. **Layers**: 55 layers, 13 roles changed (for example `STRUCTURE` to wall, `TEXT` to room names).
4. **Floors**: the two plans sit side by side on one sheet. For each floor, **Draw a box** and a drag round its plan
   (both boxes came within 1 cm of the ones the acceptance runs use); the levels **picked from the drawing's own level
   tags** (+0.90 and +4.80; the drawing labels them in Thai, shown as written); walls 3.90 / 3.50 m; door and window
   heights 3.00 / 2.60 m.
5. **Build**: done in 22 s: 213 parts, 86 openings, the upper floor lined up with the ground floor by the grid lines.
6. **Check**: 55 flags on the ground floor, 30 upstairs; 13 grey furniture families given the kinds the house's settings
   give them; **Rebuild**.
7. **Save**, the viewer, **Walk** on the ground floor, the Max script (its second line carries the model's stamp) and the
   CSV: all worked.

The walls, glass, openings and floors are exactly those of the acceptance run of the house (the same 213 parts and 86
openings). The furniture is not: **5 of the 13 families stayed grey after the rebuild** (the fault below), and the
screens read 7 small items (thinner than 0.25 m) that the acceptance settings leave out, because that limit has no box on
any screen: 86 pieces against 79. No dialog and no page error in either path. Both are fixed since (see *What failed*):
with its 13 words as the screens saved them the house now gets the acceptance run's furniture, and the 0.25 m limits are
typed on the Floors step.

## What each acceptance criterion showed

| | Criterion | Result | What it showed |
|---|---|---|---|
| A-1 | The bank uploaded again reproduces version 2 (must) | **Met** | Both ways (as a new project, and as version 3 of the bank): the model `c3a9408304a2` byte for byte; the furniture list, the top view and both converted DXFs equal; both drawings **ok**; the 24 + 25 openings equal the detector's; the Max script with the 27 Oct texts equals `Bangkok_Bank_Sampeng.ms` byte for byte; the version's own script equals the one expected for that day |
| A-2 | One 3ds Max script generator (must) | **Met** | The hotel's script byte for byte; two touching holes refused; a model with every kind of part runs in the stand-in for 3ds Max (builder tests) |
| A-3 | Taking in drawings (must) | **Met** | All 8 DWGs in the project folder convert: the bank's two, L29, L30 and the 3D team's new suite **ok**; the house and "layout presidential xx" **minor**; "layout presidential test" **loss** (8,254 of 142,182 items; the 4 lost blocks in the suite listed, with the advice to export a DXF from AutoCAD). Refusals, time and memory limits, Cancel and restarts: covered by the tests, all passed |
| A-4 | Reading and the openings detector (must) | **Met** | The readings equal the prototype's on six drawings, and the detector's openings equal record for record; the house reads in millimetres (28 doors against 4) though it says inches; 26 level tags; grid labels: bank 10, house 63, tower 0 |
| A-5 | The house, suite and tower build from a layer mapping and a floors setup only, with a gap report (must) | **Met** | All three build, are checked, save and open; the house's upper floor lines up by the grid lines (74.022 m, within 0.9 mm). The suite has 127 furniture pieces against the prototype's 120: 6 % more, the wish was within 5 % (a *should*, missed; accepted by you on 10 Nov). The gap report `docs/upload/GAPS.md` explains and classes every difference; this check rebuilt exactly the same models and got the same walk results |
| A-6 | Walk checks on every uploaded version (must for the bank; must run, should pass for the others) | **Met** | The bank, both ways: every wall, door and glass probe passes (80 wall spots, 39 doors, 44 glass probes). The others run, and their failing probes are exactly the ones the gap report lists and explains: house 4 doors and 2 glass, suite 1 door, tower 7 doors and 4 glass, the Revit suite 3 doors |
| A-7 | The staff path in Edge (must) | **Met** | Both browser tests pass: the bank through every screen to a saved version (5.5 min), and a drawing full of hostile names (nothing injected, no pop-up) |
| A-8 | Office memory (must) | **Met** | The office remembered the bank's roles; a new tower project of that office had its 13 shared layers suggested from the office; a new version of the bank kept its floor keys, names and position |
| A-9 | Fixes survive a rebuild and a re-upload (must) | **Met** | A set-aside item, a 108-item block, an opening fix and an accepted outline wall applied again, also after the same DWG was uploaded again (the same model byte for byte) |
| A-10 | Times on this laptop (should) | **Met** (one close) | Reading the bank's two DWGs 27.7 s (target 30 s; about 33 s while the browser and the dev servers also ran); the suite 93 s (150); builds: bank 15 s (45), house 17 s (60), suite 8 s (90); the most memory any step used 675 MB (1.5 GB); the house sheet redraws in 7.5 ms (50) |
| A-11 | Nothing else moved (must) | **Met** | The 4 Nov checks pass; the prototypes' own tests pass (the view-modes test after a re-run, see below); the seed gives the same 5 stamps; no prototype file or drawing changed and no new `__pycache__`; nothing deployed |
| A-12 | The 3D team's new Revit export of the suite (should) | **Met, with gaps** | Converts with nothing lost, reads, builds, saves and opens both ways (as a new project, and as version 2 of the suite); its Max script and furniture list download; its walk checks run (3 of 9 doors fail: no floor, see the gaps) |

## Test results (final check, 9 Nov 2026)

| What is checked | Command | Result |
|---|---|---|
| Library versions are exactly the frozen list | `npm run check:pins` | OK (28 npm and 28 Python packages, the builder's 19, LibreDWG's 63 files) |
| Strict type check of all the code | `npm run typecheck` | 0 errors |
| Unit tests: the viewer and the staff app | `npm run test:unit` | **842 passed**, 0 failed (73 files; 595 on 4 Nov) |
| The builder's tests: converting, reading, building, the Max script | `npm run test:builder` | **705 passed**, 0 failed (10 min) |
| API and store tests | `npm run test:api` | **471 passed**, 0 failed (295 on 4 Nov). Again in the strict mode with the real builder: 471 passed, nothing skipped |
| API description and generated code unchanged | `npm run gen:api` | No change |
| The API only grew: nothing of 4 Nov changed | `node tools/check-openapi-additive.mjs` | OK |
| Build | `npm run build` | OK: web app, offline template (783 KB), 5 offline files |
| Store rebuilt from the prototypes | seed (into a temporary folder) | the same 5 stamps: 4b02dc17f286, c3a9408304a2, f1b95c53eb3d, e43270cc0c9b, 6ab030750886 |
| The acceptance runs: 8 drawings, 14 uploads, 8 saved versions, through the API and the real builder | (A-1 ... A-12) | all done; table above |
| Browser tests in Edge: everything the prototype pages do, the staff app, the upload path and the walk checks | `npm run test:e2e` | **278 passed**, 0 failed, none needed a second try (27 min; 214 on 4 Nov) |
| Prototypes' own tests, unchanged | one at a time | all pass; the view-modes test after a re-run (next table) |
| Your path through the app, in Edge | `npm run dev` | bank 15 of 15 steps, house 11 of 11; one fault found |

**After the fixes of the same day** (the fault and the size limits; `docs/upload/contract-issues/UR.md`, section 8),
run by the fixer and again by a separate reviewer: version check ok (LibreDWG's 64 files with the licence text, below);
type check 0 errors; unit tests **851** passed (9 new); builder tests **722** passed (17 new; the bank's model and
furniture list unchanged); API tests **471** passed, also in the strict mode with the real builder; `gen:api` no change;
the additive check ok; build ok; the whole browser suite in Edge **279** passed (26.6 min, no retries), the final check's
278 plus a new upload test that gives two grey families with such names a kind and checks them after the rebuild (the
upload path now 3). The reviewer also took the house and the bank through the screens again: the house (34 steps) saves
model `1c07bfeef580`, the acceptance run's, byte for byte, with 79 pieces and none of the 13 families grey; the bank (15
steps) saves `c3a9408304a2` with its furniture list `b528bb2320ef`. Outside `app\` nothing changed during the fix and
its check.

How the 278 browser tests split:

| Area | Passed |
|---|---|
| Furniture | 68 |
| Model structure | 52 |
| Walk checks on the uploaded versions (A-6) | 48 |
| Orbit, Walk, Ghost and Camera | 40 |
| Build replay | 19 |
| Staff app | 19 |
| The check screen's plan | 14 |
| Offline file | 11 |
| Clean-up after closing a viewer | 5 |
| The upload path (A-7) | 2 |

The prototypes' own tests, unchanged:

| Test | Passed |
|---|---|
| View modes | 127 of 127 on the third run (126 in the first two: a photo check, see *What failed*) |
| Bank | 49 |
| Presidential suite | 37 |
| House openings | 13 |
| House furniture | 29 |
| Hotel | 56 |
| Furniture boxes | 87 |
| Max script checks: bank / suite / hotel | 137 / 151 / 196 |
| Openings detector | 139 of 143 right on the four older drawings, 54 of 54 on the tower (the gate is 80 %) |

Outside `app\`, the 616 files of the prototype folders and drawings are the same before and after, with the same sizes and
dates, and the same two `__pycache__` folders from October (none new). Two notes in `.claude\handoff` were written at
17:15 by a daily Claude task, not by these checks.

## What failed

1. **A fault on the Check step, found in your path (the house): fixed after the check.** Giving a grey furniture
   family a kind did nothing when the family's name had a capital letter right after a digit or a small letter, such as
   `TF2092P`, `A$C238E5230` or `SmartTable`. The Check step saves the name as the flag shows it (`TF2092P`); the builder
   read the family split at that point (`TF2092 P`), so the two never matched and the pieces stayed grey after the
   rebuild, while the drop-down still showed the kind you chose. In the house, 5 of the 13 families stayed grey: 8
   sanitary fittings, 2 beds and a coffee table. The bank was not affected ("Fritz-Hansen_SH200 - Default" has no such
   letter). **Now** the builder gives a family the kind of a word that names it, compared without spaces and capitals,
   whatever its capitals, digits, underscores or symbols, and the drop-down compares the same way, so it shows the kind
   the next build gives. A family of loose lines ("loose shapes on ...") can now take a kind too, which it never could.
   Settings saved before the fix work as they are. Checked: the house built with its 13 words as the screens saved
   them gives the acceptance run's model byte for byte; the bank, the suite and the tower are unchanged (the bank's
   model `c3a9408304a2` and furniture list `b528bb2320ef`). Tests added for it in the builder, the staff app and the
   browser (`docs/upload/contract-issues/UR.md`, "After the final check").
2. **One photo check of the prototypes' view-modes test** failed in two of three runs, a different one each time
   ("photo in Srisawan named after project, floor and lens", then "phone: photo taken"), and all 127 passed on the third
   run. Each waits a fixed 1.5 s for a 1920 x 1280 photo to appear, which this laptop's software drawing sometimes misses.
   The test is the prototype's own and unchanged; nothing in the app is involved.
3. **Two "should" targets, close:** the suite's furniture count (6 % over the prototype's, the wish was 5 %), and the
   bank's reading time (27.7 s on its own, within 30 s; about 33 s with the browser and the dev servers running too).
4. **A slip in the wording of the gap report:** `docs/upload/GAPS.md` said the version's Max script differs from the 27
   Oct file "in its 13 profile lines"; it is 8 lines replaced by 11 (the counting script skipped removed comment lines).
   The byte-for-byte checks of the scripts were right. Corrected after the check, in GAPS.md and in `UR.md`.
5. **The app stopped by itself during your check of 10 Nov: fixed the same day.** The check gave one of the server's
   code files a new date while the app ran; the server restarted itself to load it, and on Windows that restart also
   stopped the web server and npm, so the whole app stopped and PowerShell's prompt came back. My own checks had run
   without a real terminal window, where this cannot happen. `npm run dev` no longer restarts the server by itself (see
   *How to start it*). Two separate checks in real terminal windows confirmed the fix: the old setup stopped exactly as
   in your window; the new one keeps running when code files change; Ctrl+C stops everything within a second; and a
   build or a reading that is running when you stop the app finishes by itself and shows as done after a restart
   (`docs/upload/contract-issues/UI.md`, UI-5).

## Known gaps

### The bank: none

Uploaded again from its two DWGs, it gives version 2's model byte for byte, with the same furniture list, top view,
openings and 3ds Max script (apart from the script's text lines, above).

### The Sukhumvit house (one DWG, two floors on one sheet)

It builds from its one DWG with the two plans boxed on the sheet; the upper floor lines up with the ground floor by the
grid lines to within a millimetre, and all 86 openings are found where the prototype has them. Against the prototype:

* **No floor under the glass-walled living area.** The app makes a floor only for rooms that its walls close. The living
  area on the ground floor is closed by glass, so about 64 m2 there (and a small glass room upstairs) have no floor; the
  Check step flags it. Three sliding glass doors onto that area and one door in the small east building cannot be walked
  through for that reason. *Comes with rooms and slabs.*
* **Walls a little different.** The prototype had its own cutting rules for the house (fins, glass corners, lintel
  slots); the app uses the bank's rules: about 3 m2 of wall differs on the ground floor and 1 m2 upstairs, and the
  ground floor has 4 more lintels. *Later.*
* **Window glass** goes full height, as glass parts rather than separate panes: *accepted* (decided on 27 Oct).
* **4 window heights** that the prototype took from the elevations (the stair's tall glazing at 3.90 m, one at 2.55 m)
  get the floor's standard heights: *set them on the Check step now* with the opening editor.
* **Stairs** are tread lines and the upper stair void is not cut: *comes with the climbable stairs.*
* **Furniture:** the ground floor matches piece for piece (47); upstairs 32 against 29 (3 rug or zone outlines read as
  furniture). *Later.*

### The presidential suite (`layout presidential test.dwg`)

* **The converter loses part of this drawing** (8,254 of 142,182 items; in the suite, three gym machines and one other
  block, which the prototype did not have either). The Files step says so and advises a DXF exported from AutoCAD.
* **The corridor walls and the facade glass are drawn as room outlines** here, so they are built only when you accept
  the suggested walls on the Check step (switch on "Walls along room outlines" on the Floors step). Accepting all 26
  suggestions overshoots: accept them one by one. The facade glass comes back only as thin panes (0.4 of 5.4 m2).
  *Option now.*
* **Most of the suite has no floor:** only 113 of about 556 m2 inside the walls, because the walls do not close without
  the corridor walls and the facade; the whole living and dining area has none, and one door fails the walk test for
  that reason. Flagged. *Comes with rooms and slabs.*
* **The prototype's hand-made parts** (the C-shaped wall round the sofa, the low kerbs at the jacuzzi, the cabana, a
  movable glass partition, the bath glass) are here full walls or ordinary lines. This milestone can set them aside but
  not lower them or change their kind. *Later.*
* **Openings:** the detector finds 25 against the prototype's 22 hand-checked ones (20 at the same place): *correct
  them on the Check step.*
* **Furniture:** 127 pieces against 120, every kind present. Room names come as drawn ("Bar 7,6m2"): *accepted.*

### The tower (L29 and L30; no prototype to compare with)

* It builds, saves and walks. Levels 0.00 and 4.00 m with 4.00 m walls are assumed: the drawings give none.
* **About half of each floor has no floor.** The curtain wall does not close at its corners, so the rooms between the
  core and the facade get no floor: about 321 m2 on L29 and 190 m2 on L30. Flagged; most of the failing walk probes (5
  of the 7 doors, 3 of the 4 glass probes) come from this. *Comes with rooms and slabs.*
* **Openings** come from the detector, which scored 72 % on this drawing before its fixes (the gate is 80 %), so each
  doubtful one is flagged: 27 to look at. Two doors are blocked by something in the doorway: *fix on the Check step.*
* **39 single lines** on the wall layers (no partner line) are built as 1 m high items: *set aside those that are not
  walls.*

### The 3D team's new Revit export of the suite (9 Nov)

* It converts with nothing lost and builds. But **its interior walls are on layer 0** among other line work, so with
  the office's roles only the facade, the columns and a few walls are built, and the floor is 35 m2. Now: set layer 0 to
  wall and set aside the 42 stray lines on the Check step. Better: ask the 3D team to export with the walls on their own
  layer. *Later:* walls recognised by their shape.
* **Furniture:** Revit family names the app does not know come out grey; give each a kind on the Check step (names like
  `SmartTable` take it since the fix after the final check).
* **As version 2 of the existing suite** it keeps version 1's position, which for this differently drawn file puts it
  3.5 km from the centre (it still works, but the wall walk check finds no spot to start from). For a re-drawn project,
  press **Reset** under "Model position" on the Floors step.
* Its 25 openings (9 doors, 15 windows, 1 passage) are listed in the gap report, for a later fair scoring.

### Other gaps

* **The furniture size limits are now on the Floors step** (after the final check), under *Build options*: "Leave out
  furniture shorter than" (0.08 m unless you change it) and "Leave out furniture thinner than" (empty: no limit). The
  house's settings use 0.25 m for both; type them there and the 7 small lines that came in as grey furniture stay out.
* **"Use the files of v<n> again"** is no longer offered once a saved draft is cleaned up (7 days after saving): upload
  the files again. Keeping it needs a field the frozen contracts do not have: next milestone.
* **LibreDWG's full licence text** (GPL-3.0) is now in place (after the check, 9 Nov): fetched from gnu.org and put
  beside the converter as `vendor\libredwg-0.14-win64\COPYING`, recorded in the manifest
  (`npm run vendor:libredwg -- --add-licence <file>`), so the version check verifies it; nothing is left for you there.
* As on 4 Nov: the phone and tablet layout is parked (PC first); the tests' software drawing runs slower than the
  laptop's graphics; the web app's code is one 1.3 MB file.

## What comes next

1. **Done after the final check:** the furniture-kind fault on the Check step is fixed, and the furniture size limits
   have their boxes on the Floors step (see *What failed*).
2. **Rooms and slabs** (your choice of 10 Nov, started that day): floors made from the wall network, so the house's
   glass living area, the suite's centre and the tower's outer rooms get their floor (most of the failing walk probes go
   with them). Then **stairs you can climb**.
3. **Box editing** after that: rename and recolour furniture kinds, move pieces between kinds, add boxes by hand; then
   the real furniture models, finishes and lights.
4. **A second round of fixes for the door finder.** The 3D team's new suite drawing was tested on 10 Nov as a drawing
   the finder had never seen (its answer key made by separate labellers who never saw the finder's output, then checked
   by two blind auditors): **7 of its 16 doorways came out right (44 %; the goal is 80 %)**, and 8 openings were
   reported that are not there. The main cause is known: this kind of Revit export draws the wall's lines on across the
   doorways (all four pocket doors are hidden that way) and has the furniture on the wall layer. With those lines left
   out, the same finder gets 14 of 16. Nothing is fixed yet. Until then the Check step has two tools for it: select the
   lines drawn across a doorway that has no door and set them aside (Delete), then **Rebuild**, and the door is found;
   and give an opening that is not there the kind "not an opening". (The Check step cannot add a door by hand.) The full
   result, with a marked plan: `detector\blind_run_suite_revit\README.md` and `result_marked.png` beside it. A drawing
   from another office would still be the stronger test.
5. For you: ask the 3D team to export Revit files with the walls on their own layer.

## Decisions

Settled by you on 4 Nov: the DWG upload first, then the box editing; Reset in the offline file stays as built; version
control on this laptop only. The Excel formula question of 4 Nov is settled by the guard described above.

Answered after the final check (9 Nov): the furniture size limits (smallest piece, thinnest piece) got their boxes on
the Floors step now rather than with the box editing, because without them the house built through the screens reads 7
thin items more than its settings; say if you would rather have them moved to the box editing.

Settled by you on 10 Nov: the suite's furniture count (6 % over the prototype's, against a wish of 5 %) is accepted as
it is; rooms and slabs with climbable stairs come next, then the box editing; the new suite drawing is the openings
detector's fifth drawing.

Open: nothing.

Nothing in this milestone needs deploying. When anything goes online later, you run that deploy yourself.
