# Where the application stands (4 Nov 2026)

The foundation of the real application is built. A final check was run on 4 Nov from a clean start, separate from the
steps that built and fixed it. **Every test passed, and your path through the app worked from start to finish.**

Nothing has been put online or deployed. Everything runs on this laptop only.

## What it does today

**The staff app.** It runs in the browser on this computer.

* **Project list.** The four projects show as cards: the bank branch, the hotel (from two pictures), the Sukhumvit
  house and the presidential suite. Each card has a plan picture, the floors, how many furniture pieces and openings
  there are, the version stamp and the date it was last changed.
* **Project page.** Click a card and the 3D model fills the window under a slim top bar. It works like the prototype
  pages:
  * Orbit, Walk and Ghost
  * the Camera tool and its photos
  * the floor buttons and the ticks (floor plates, glass, room names)
  * the build replay (Replay the build, Build settings)
  * the furniture boxes
* **Versions.** The top bar has a version picker. The bank has two versions: v1 of 27 Oct, without furniture, and v2 of
  29 Oct.
* **Furniture heights are saved.** Type a height for a kind of furniture and the app saves it ("Heights saved" in the
  top bar). It is still there after a reload, on another day and in another tab.
  * Two tabs open on the same project do not wipe out each other's heights.
  * If the app's server is not running when you type a height, the height is kept and sent once the server is back.
* **Downloads menu.** It gives three files:
  * the **3ds Max script**. Each version has its own file name, for example `Bangkok_Bank_Sampeng_v2.ms`.
  * the **furniture list (CSV)**, with the saved heights. It opens in Excel.
  * the **offline viewer**: one HTML file with the saved heights in it. It opens from disk with no internet.

**The offline files.** There is one self-contained HTML file per project version, for clients and meeting rooms. It
opens on the Build settings screen, as the prototype pages did. "Skip: show the finished model" goes straight to the
model. A height a client types in it stays in their own browser only.

**Under the hood.** All four projects use one model format and one viewer. The app keeps its own copy of the projects in
`app/data`, made from the prototype folders by one command. The prototype folders themselves are never changed.

## What it does not do yet

* **No DWG upload.** Projects come only from the four prototype folders (`npm run seed` copies them in). You cannot yet
  add a new drawing in the app.
* **No layer-mapping or check-and-fix screen.** This comes with the upload (next milestone).
* **No rooms and slabs builder, and the stairs cannot be climbed.** These are still the Phase 1 items carried over from
  the gate.
* **No login, share links or cloud storage.** It runs on this computer only.
* **The Max script is the one the prototype made.** The app does not rebuild it with the saved heights; the script's own
  height spinners set them in Max. The house has no Max script, because none was made for it. The house card has no plan
  picture, so it shows a grey placeholder.
* **No box editing yet.** You cannot rename or recolour kinds, move pieces between kinds, or add boxes by hand. The real
  furniture models, finishes and lights are not in yet either.
* **Phone and tablet layout is parked** (PC first). Below about 650 px wide, the top bar loses the project name.

## How to start it (one command)

Open PowerShell in `C:\Users\DWP2\Desktop\Project walkthrough\app` and type:

```
npm run dev
```

Then open **http://127.0.0.1:5710** in Edge or Chrome. Type `127.0.0.1`, not `localhost`. To stop it, press **Ctrl+C**
in the PowerShell window.

The one-time steps are already done on this laptop. You only need them again in two cases:

* `npm run seed`, after a prototype folder changes. Saved heights are kept.
* `npm run build`, after the viewer's code changes. It remakes the offline files and the template that the Downloads menu
  uses.

## Where the offline files are

`C:\Users\DWP2\Desktop\Project walkthrough\app\dist\offline\`, one file per version:

| File | Size |
|---|---|
| `bank-sampeng-v1.html` | 1.3 MB |
| `bank-sampeng-v2.html` | 1.3 MB |
| `presidential-suite-v1.html` | 1.0 MB |
| `sukhumvit-house-v1.html` | 1.4 MB |
| `hotel-lobby-v1.html` | 2.5 MB (it carries its two plan pictures) |

These files were built on 4 Nov with no saved heights. To give a client a file that has your heights in it, use
**Downloads, then Offline viewer (HTML)** in the staff app.

## Test results (final check, 4 Nov 2026)

| What is checked | Command | Result |
|---|---|---|
| Library versions are exactly the frozen list | `npm run check:pins` | OK (28 npm and 28 Python packages) |
| Strict type check of all the code | `npm run typecheck` | 0 errors |
| Unit tests: the viewer | `npm run test:unit` | 508 passed, 0 failed (40 files) |
| Unit tests: the staff app | `npm run test:unit` | 87 passed, 0 failed (9 files) |
| Store rebuilt from the prototypes | `npm run seed` | 5 versions, same stamps as before (4b02dc17f286, c3a9408304a2, f1b95c53eb3d, e43270cc0c9b, 6ab030750886) |
| API and store tests | `npm run test:api` | 295 passed, 0 failed. Run again in the strict integration mode: 295 passed, nothing skipped |
| API description and generated client unchanged | `npm run gen:api` | No change (18 files identical) |
| Build | `npm run build` | Web app, offline template (783 KB), 5 offline files |
| Browser tests in Edge: everything the four prototype pages do, plus the staff app | `npm run test:e2e` | **214 passed, 0 failed**, none needed a second try (18 min) |
| Prototypes' own tests, unchanged | (one at a time) | All passed (next table) |
| Your path through the app, in Edge | (see below) | 21 of 21 steps passed |

How the 214 browser tests split:

| Area | Passed |
|---|---|
| Furniture | 68 |
| Model structure | 52 |
| Orbit, Walk, Ghost and Camera | 40 |
| Build replay | 19 |
| Staff app | 19 |
| Offline file | 11 |
| Clean-up after closing a viewer | 5 |

The prototypes' own tests, unchanged:

| Test | Passed |
|---|---|
| View modes | 127 of 127 |
| Bank | 49 |
| Presidential suite | 37 |
| House openings | 13 |
| House furniture | 29 |
| Hotel | 56 |
| Furniture boxes | 87 |
| Max script checks: bank | 137 |
| Max script checks: suite | 151 |
| Max script checks: hotel | 196 |

The prototype folders were compared before and after these runs: they have the same 477 files, with the same sizes and
dates.

**Your path**, run in Edge on `npm run dev`:

1. Open the project list.
2. Open each of the four projects from its card.
3. In the bank: Walk, Ghost, and a Camera photo (a 1920 x 1280 PNG named after the project, the mode and the floor).
4. Type 640 mm for the bank's tables. It said "Heights saved", and after a reload it was still 640.
5. Download the Max script. It is the stored file, byte for byte.
6. Download the CSV. All 12 table rows say 640.
7. Download the offline file and open it from disk with all network access blocked. It opened, and showed the tables at
   640.

The test height was removed afterwards, so the store is back as seeded.

## What failed

Nothing in the application.

During the final check, my own check script stopped once, on its last step. It was waiting for the side panel in the
offline file, but the panel sits behind the Build settings card, as on the prototype pages. I corrected the script and
ran the whole path again: 21 of 21 passed.

## Known gaps and small differences

* **Frame rate in the tests.** The newer three.js draws 9 to 22 % fewer frames than the prototype pages in the tests'
  software drawing. On the laptop's own graphics both run at 60 frames a second, so clients will not see it. Changing the
  three.js version is your call.
* **Small looks differences from the prototype pages.** The suite's room labels no longer sit on top of each other. In
  the top views of the bank and hotel, one label and one thin edge are a pixel apart. Nothing else differs.
* **The web app's code is one 1.3 MB file.** The build warns about this. It loads quickly on a PC.
* **Cloud storage, later.** When the files move to cloud storage (next milestone), the download names have to be passed
  to it. This is noted in the code.

## Decisions

Settled by the owner on 4 Nov:

* **What comes first: the DWG upload**, then the box editing.
* **Reset in the offline file stays as it is:** it goes back to the heights saved in that file, not to the model's
  original heights, so a client cannot lose your saved heights.
* **Version control: yes.** The project folder is a git repository on this laptop only (never pushed). The first commit,
  `9eb2d58`, is the state on 4 Nov. Drawings, the video, the PDF and the 3D models stay on disk and are not tracked.

Still open:

* **Excel formulas in the CSV.** In a CSV, Excel could read text that starts with = + - or @ as a formula. None of the
  four projects has such text. It goes in with the box editing, because that is when staff can type names.

## What comes next

**Next milestone: upload a DWG and build it in the app.**

1. A staff member uploads a DWG in the staff app.
2. A separate step turns it into a DXF.
3. The bank's builder, made general, builds the model.
4. The **layer-mapping and check-and-fix screen** lets staff:
   * pick per office which layers are walls, glass, doors and furniture;
   * set heights and line up the floors;
   * fix unknown items;
   * set aside furniture that pairs up like walls.
5. The result is saved as a new version of the project.

The store already has the "add a version" step this needs:

* earlier saved heights can carry over to the new version;
* the Max script will then be made from the model itself.

**After that:** rooms and slabs, stairs you can walk up, and the rest of Phase 1. The openings detector still needs a
fifth office's drawing to confirm the 80 % gate.

Nothing in this milestone needs deploying. When anything goes online later, you run that deploy yourself.
