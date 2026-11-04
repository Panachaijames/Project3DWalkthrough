# Viewer modes and build replay (16 Oct 2026)

Code shared by both prototype viewers, [cad_test/house_3d_preview.html](../cad_test/house_3d_preview.html) and
[srisawan-viewer/Srisawan_3D_viewer.html](../srisawan-viewer/Srisawan_3D_viewer.html). It is prototype code: the product
will port it into the viewer of Phase 1.

| File | What it is |
|---|---|
| `viewer_modes.js` | Orbit / Walk / Ghost, the Camera tool, touch controls and the phone layout |
| `build_replay.js` | The Build settings screen and the build replay (the "loading phase") |
| `test_viewers.mjs`, `cdp.mjs` | Browser tests: drive headless Edge with real key, mouse and touch input (no npm packages) |

Both `.js` files are plain JavaScript that the page generators paste into each viewer page. After changing them, rebuild
both pages from the project folder:

    python cad_test/src/make_html_cad_merged.py cad_test/house_3d_preview.html
    python srisawan-viewer/src/make_srisawan_html_merged.py srisawan-viewer/Srisawan_3D_viewer.html

## Using the viewers

The pages load Three.js from the internet, so they need a connection. They open on **Build settings**: check the levels
and wall heights, pick a replay speed, then **Generate 3D model** (or **Skip**).

| | Computer | Phone or tablet |
|---|---|---|
| Orbit (dollhouse) | Drag to turn, right-drag to pan, wheel to zoom, **1** | Drag, pinch |
| Walk | **2**, or double-click a floor. W A S D, Shift to run, drag or click to look, PgUp / PgDn for floors, wheel = lens, Esc twice = back | Move stick, drag to look, Upstairs / Downstairs |
| Ghost | **3**. W A S D, Space up, C down, Shift fast, wheel = speed | Move stick, hold Up / Down |
| Camera | **Camera** button, **P** for a photo | Camera (top bar), Photo button |
| Build replay | **Replay the build** / **Build settings** in the panel; Esc skips | Same |

## Address options

Handy for demos and tests, e.g. `house_3d_preview.html?build=0&mode=walk&floor=upper`:

| Option | Does |
|---|---|
| `build=0` / `build=play` | Skip the Build settings screen / start the replay at once |
| `speed=quick\|normal\|slow`, `captions=0` | Replay speed (about 9, 20 or 40 s); no captions |
| `mode=walk\|ghost`, `floor=<key>` | Start in Walk or Ghost on a floor (`ground`, `upper`; `L1`, `L2`, `F6`) |
| `x`, `z`, `y`, `yaw`, `pitch` | Start position (m) and direction (degrees) |
| `lens`, `eye` | Lens (mm, 12–85) and eye height (m) |
| `cam=1`, `frame=3:2`, `size=4k`, `straight=1` | Open the Camera panel with these settings |
| `touch=1`, `nodownload=1`, `shot=1` | Force touch controls; photos without download; take a photo on load (tests) |

## Tests

Needs Node 22 or newer and Microsoft Edge (set `EDGE` to a `chrome.exe` path to use Chrome instead):

    node viewer-modes/test_viewers.mjs              # all sections, about 10 minutes
    node viewer-modes/test_viewers.mjs replay       # one or more of: house phone srisawan fixes srisfix landscape replay

Screenshots and the photos the tests take go to `%TEMP%\viewer-modes-test`. The checks run with software rendering
(14–21 frames a second), so timings are generous; they have not been run on a real phone or GPU. On a busy machine (10
frames a second or less) a timed walking check can fail once: run it again before suspecting a change.

Environment variables: `TEST_PORT` (the browser's debugging port, default 9333), `TEST_TMP` (the folder above) and
`TEST_PROFILE` (the browser profile) give a run its own port, folder and profile, so two runs on one machine cannot meet;
`HOUSE_URL` and `SRIS_URL` point the test at other builds of the two pages. The suite has 127 checks (27 Oct 2026: all pass
with the doors and windows cut into the house). The other models have their own tests next to their pages:
`cad_test/test_house_openings.mjs` (13), `cad_test/test_house_furniture.mjs` (29), `presidential_test/test_presidential.mjs` (37)
and `bank_test/test_bank.mjs` (49); the furniture boxes' own module has `furniture/test_boxes.mjs` (87). Since the furniture boxes
(29 Oct) two house checks of this suite sit closer to their limits: "sliding works at random spots along walls" gives 36 of 40
(limit 36; 37 without boxes) and "keys still work after clicking a checkbox" moved 0.17-0.45 m (limit 0.1 m; 0.75 m without
boxes), because faceOpenest looks only at chest height and a knee-high box can cut a walk short.

## How a page uses this

The generators show the whole pattern. In short, after building its meshes a page calls:

- `installViewerModes({ scene, camera, renderer, controls, panel, anchor, hint, project, floors, restoreVisibility, onChange })`,
  where each floor is `{ key, name, level, stack, group, colliders, walkables }`;
- then `installBuildReplay({ ..., modes, intro, layers, floors, steps, applySettings, restore })`, where each floor adds the
  replay data: its drawing lines, wall pieces, merged outlines, the meshes that rise and the ones shown at the end.

Each wall run's geometry carries an `aDelay` attribute (0–1) so the walls rise in a sweep; the generators set it.
The full contracts are in the comments at the top of the two `.js` files.

## Known limits

- Stairs cannot be climbed yet: PgUp / PgDn or the floor buttons change floor.
- The house's floor plates are an approximate outline traced around the walls; hospital floor 6 has no slab.
- The replay data is about 0.5 MB for the house (the longest 6,000 ignored drawing lines per floor are kept).

## Parked: phone and tablet layout (decided 19 Oct: PC first)

Found in the 19 Oct review; to fix when phones come back on the list.

| Screen | Problem |
|---|---|
| Phones on their side, 700 px wide or less (e.g. 667 × 375) | They get the upright layout: the Camera panel covers the Photo button, and the replay model is squeezed into an 80 px strip |
| Phones on their side with the browser bars showing (under about 380 px tall) | The Camera panel's minimum height pushes it over the Photo button |
| Upright phones under about 667 px tall (browser bars showing) | The photo frame falls back to the whole screen and sits mostly behind the Camera panel |
| Tall upright phones | The Photo / Upstairs / Downstairs column covers a corner of the photo frame (the frame reserves 156 px; the column needs about 185) |
| Upright tablets (e.g. 768 × 1024) | The replay uses the narrow strip beside the card instead of the larger area below it |
