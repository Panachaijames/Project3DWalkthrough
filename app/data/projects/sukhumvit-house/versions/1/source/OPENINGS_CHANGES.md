# Doors and windows cut into the Sukhumvit house (26 Oct 2026; revised 27 Oct 2026, round 3b; rebuilt 28 Oct 2026)

The opening detector (`detector/openings.py` in the project folder) is a step of the house pipeline. Its output is used as it is:
nothing was added, removed or moved by hand. The merge step cuts the doors and windows into the walls, after the floor
plates. The page shows lintels, sills and window glass. Moved into the project on 27 Oct 2026; the page and
pipeline files it replaced are in `previous_before_openings_2026-10-27/`. Nothing was deployed.

**28 Oct 2026, after the tower test:** the detector was changed (a wall end facing the side of another wall is no longer
a passage, and other rules found with the tower floors L29 / L30; see `../detector/README.md`), re-run on the house, and the
page rebuilt from its output. Every door and window is the same as on 27 Oct (position, width, kind, hinge, heights; the one record that differs besides
its id is a door whose end moved by 1 mm, ground-036, now ground-034, 0.901 m to 0.902 m); **12 passages are gone (ground-023, -034, upper-019, -020, -025, -026, -028, -029, -036, -037, -039,
-040 in the 27 Oct numbering), so the model has 86 openings instead of 98 and 17 passages instead of 29**. Passages are not
cut, so the walls, lintels, panes and floor plates are unchanged; the page is 747,630 bytes on disk (751,129 before). Opening ids after
a removed passage shift down: `previous_before_fix_round_2026-10-27/id_map_27oct_to_28oct.json` maps every old id to its new one.
The text below is the 27 Oct record and uses the 27 Oct ids and counts. The page, merged model and openings of 27 Oct are in
`previous_before_fix_round_2026-10-27/`. `test_house_openings.mjs` passes (13 of 13); `test_house_openings_before.json` was
regenerated for the 17 passages (walked on the page from before any openings). Nothing was deployed.

**Round 3b (27 Oct):** three reviewers' findings were checked against the drawing, the code and the tests, and the
confirmed ones fixed with general rules (no ids, coordinates or per-drawing exceptions; the only per-drawing input is
the layer mapping). The detector score did not drop on any floor and it lost 4 false openings. The house model now
glazes every sliding glass door, closes the glass corner, keeps the grilles and the glass bridge, and its lintels sit
in the walls. The full viewer suite is back to its original 90 % threshold and passes. Details below. (The round-3a
files were not kept; the page from before any openings is in `previous_before_openings_2026-10-27/`.)

What each kind of opening becomes (the 26 Oct decision, now applied to every sliding glazing unit):

- **Door:** open from the floor to its head, with a lintel from the head to the top of the wall. No leaf is drawn.
  Walls, glass and single-line pieces are cut away in its footprint.
- **Window**, and **sliding glazing that may be a door or a window (eitherKind), whatever kind the detector gave
  it**: a 3 cm glass pane from the sill to the head, standing on the drawn glazing. The pane is a collider. A sill
  wall only when the sill is above 0, and a lintel above the head unless the head reaches the top. Round 3a glazed
  only kind 'window', so the three garden sliders (ground-004, -006, -018, 13.4 m) were open holes while the identical
  courtyard slider was glass. Now all four are glass.
- **Passage:** left as it is. No cut and no lintel. The merge now checks this (it stops if anything inside a
  passage changed) and so does the browser test.

## Detector changes (detector/, round 3b)

All rules are physical and apply to any drawing. `openings.py` docstring rules 4-7 describe them; `geomkit.py` gains
the `screen` role.

| Finding | Rule added or changed | Effect on the four drawings |
|---|---|---|
| upper-042, window along the glass bridge | One side of an all-glass corridor (a parallel band opposite, 0.8-3.5 m) is a glass wall also when it stands in a gap that is not between two wall ends of one wall line (cap-end). The no-gap path already did this, which is why the bridge's south side was never a window. | extra removed |
| upper-045, pocket door read from a TREE line | A pocket line must run into the wall and stay in it: at least 80 % of its part past the gap's end lies in wall material. This line ran through the 0.1 m stair wall and 1.2 m beyond it (8 % inside). Presidential D7, a real pocket door drawn on a non-door layer, has 100 % and stays (a door-layer rule would have lost it). | extra removed |
| upper-048 (now upper-043), skewed stair-landing door | A door read from its swing alone turns its chord about its middle onto the nearest wall-face direction around it (wall solid, glazing and jamb shapes within 0.5 m; at most 10 degrees). The arc there is flattened: its circle centre is 0.13 m off the jamb, so the chord ran 8 degrees off. It is now x 116.205 between the jambs (key 116.222), 0.1 m thick. It also straightened ground-037/-038/-039 and bank L2-028 by 0.5-2 degrees. | same score, ends better |
| upper-050, shower door | A door from a swing alone, with no wall, jamb or glazing to bound it, whose leaf closes against a single wall-layer line drawn unbroken through the whole chord (a one-line screen) is not an opening: an opening breaks its wall's lines. | extra removed |
| upper-058, shower screen | Glass that turns a post-less corner is a window corner only when its other end is a wall end in its own line. Glass from the side of a cross wall round a corner is a glass enclosure (shower, glass box), whatever its layer. | extra removed |
| ground-030, window 0.33 m inside the facade | A gap measured from a block shorter than it is thick (a corner block) has no wall line of its own: when its glazing stands outside the block, the window takes the glazing's own line, as deep as the glazing (at least 0.1 m). ground-030 is now on its sashes (x 8.848; key 8.773). | ends error 0.33 -> 0.08 m |
| grilles cut away (A_Grill, W_Grill) | New layer role `screen` (grilles, louvres): never glazing. Screen lines along a gap close it (no opening). The Sukhumvit mapping moves A_Grill and W_Grill from `window` to `screen`. The grille-closed service yard (UE-08/-09/-10, optional in the key) is no longer three windows. | 3 optional finds fewer; no score change |
| panes off the glass | New output field `glazing`: [lo, hi], where the glazing lines lie across the line a->b (metres, + = left), for every window and glazed door; null otherwise. | input for the 3D pane |
| D1, L-corner passage limit on a knife edge | 2.5 m -> 2.75 m (UE-23 is 2.50 m wide); the limits next to the key cases are documented in `passage_ok`. | no change |
| D2, frame_rows grows with the square of small shapes | Neighbours through a 1.65 m grid; rows walked only from pieces within 0.4 m of a wall; wall checks memoised; above 3,000 pieces against walls the step is skipped with a warning; a floor that takes over 60 s names its slow steps. Synthetic 1,600 squares with no walls: 0.1 s (the reviewer measured 16 s with the old code); 1,600 with walls every 6 m: 3 s; 5,000: 18 s. | outputs identical |
| D3, floor split in code | A mapping may give `areas` (where each plan sits on the sheet: a box in drawing metres, or the whole file); the detector then splits the floors itself, so a new drawing needs no code change. Tried on all four mappings: they reproduced the cache's tags exactly (0 of 69,854 items differ) and identical outputs. **The four mappings were left at layer roles only**, as the Phase 0 rule says, so today the split still comes from the cache (`detector/tools/prims.py`; the one change is an `OPENINGS_DATA` option for where the drawing folders are); the area versions are in `detector/mappings_with_areas/` (owner question 5). | outputs identical |
| D6, unknown units | Stops with the list of allowed units. | |
| host | A door from its swing that a wall end or jamb bounds takes its host from the ends (it was `none` when no wall band lay beside the chord): ground-036, upper-043, L2-028. | |

Tried and reverted: splitting glazing at a door-layer jamb that spans the glazing's depth (H-08). It gave the
courtyard slider GW-19 its right width, but it stays a window (no paving outside, so the class is still wrong). The same
rule split UW-16 upstairs, which the key reads as one window over the void, so the upper floor dropped from 40 to 39.

**Score** (`python tools/score.py keys/final/all.json detector/output/all_openings.json`):

| Floor | Before (3a) | Now | Extras before -> now |
|---|---|---|---|
| sukhumvit:ground | 39/41 | **39/41** | 3 -> 3 |
| sukhumvit:upper | 40/40 | **40/40** | 12 -> **8** |
| presidential:suite | 20/21 | **20/21** | 9 -> 9 |
| bank:L1 | 16/16 | **16/16** | 3 -> 3 |
| bank:L2 | 24/25 | **24/25** | 3 -> 3 |
| Total | 139/143 (0.972) | **139/143 (0.972)** | 30 -> **26** |

Precision 0.825 -> 0.844. Still wrong or missed: GE-17 (vehicle gate), GW-19 (merged with the corner glass; a window),
UW-01 (a window in the key's eitherKind sense: class right, kind differs), presidential D16 (stacking partition), bank
B2-07 (width). The upper floor is renumbered from upper-007 on (upper-008 -> 007 ... upper-048 -> 043, upper-060 ->
053). These figures are on the development set; the only held-out figure is still the blind bank run of `frozen_v1`,
39/41 (0.951). Outputs, PNGs and scores: `detector/output/`.

## House pipeline changes (round 3b)

| File | Change |
|---|---|
| `src/openings3d.py` | (1) **Glazing rule:** windows and eitherKind openings (sliding glass doors included) get a pane; records carry `glazed`. (2) **Pane on the glass:** the pane stands in the middle of the detector's `glazing` band, kept inside the wall depth. (3) **Cut:** the wall depth, the detector's thickness and the glazing band; glass beyond them is left, so the grille in front of UE-11/-12 and along the service yard stays. Openings without glazing information (doors) still take glass and single lines within 0.1 m. (4) **Lintel depth** from the walls beside the jambs (sections 0.05-0.30 m out; a steady wall past nibs, not jamb returns, blocks or cross walls; the faces shared by both jambs, or the deeper when one lies inside the other). Lintels that stick out past the wall beside them: 15 -> 4 ends; that leave a slot: 12 -> 7 (measured with a check script that is not kept; the rest are glass outside a thin wall at UE-05/-06, the pocket side of GE-09, and piers or blocks at a jamb). (5) **Glass corners:** two glazed openings at right angles whose ends meet within 0.15 m: both panes run on to where they cross plus half a pane, the first one's cut and lintel cover the corner square, the second's run up to the first's. (6) **Panes to the top** are marked `top: true`. (7) **Passage check:** the merge stops if the walls, glass or single lines inside a passage changed (other openings' own cuts excepted). |
| `src/find_openings.py` | Glass corners take the same heights: when an elevation row matched one leg only, the other takes its sill and head (the living-room corner is 3.90 m on both legs; the void corner upstairs 2.60 m). No heights.json: the plan defaults (2.10 / 0.90-2.10 m) with a note. The detector is looked for in `$OPENINGS_DETECTOR`, `<project>/detector` (two folders up), `../detector`, then the scratch folder. |
| `src/openings_mapping.json` | A_Grill and W_Grill are `screen`, not `window` (identical to `detector/mappings/sukhumvit.json`). |
| `src/merge_cad.py` | `openings_for()`: stops when openings.json is from another plan.dxf (sha1) or another model frame (centre, shift), and when house3d.json has no frozen frame ("re-run build3d.py"). Without openings.json the output is still byte-identical to the unchanged pipeline (checked). |
| `src/build_stages.py` | The same check; stats gain `glazedDoors`, and window heads and sills count the glazed doors. |
| `src/make_html_cad_merged.py` | A pane that reaches the wall top follows it when the wall height is raised (no open slot over ground-042/-043/-044 at 4.50 m). Intro and captions corrected, numbers from the stats: "32 doors and 37 windows found in the plan are cut in (the 29 passages are gaps that are already open). Doors open to 3.00 m (upper floor 2.60 m) under a lintel; windows, and the 3 sliding glass doors that may be windows, are glazed to their heads (3.00 / 3.90 m; upper floor 2.55 / 2.60 m)." |
| `src/README.md` | The rules above and the new checks. |
| `test_house_openings.mjs` | See Tests. New companion file `test_house_openings_before.json`. |
| `viewer-tests/test_viewers.mjs` | **The 90 % threshold is restored**; the only change left against the project's copy is TEST_PORT / TEST_TMP / TEST_PROFILE from the environment. |

## Files added or changed in the project (27 Oct 2026)

| File | What |
|---|---|
| `cad_test/src/build3d.py` | Changed in 3a: freezes the model origin and writes `centre` [30.8095, 16.3425] and `shift` {ground 0, upper -74.021} into house3d.json. The segments are unchanged, byte for byte. |
| `cad_test/src/find_openings.py` | **New** pipeline step (3a; revised 3b). Runs the detector unchanged (imported as a module) on this folder's plan.dxf with `openings_mapping.json`, rebuilds the detector's cache `prims.pkl` when plan.dxf or regions.json is newer, adds heights and writes `openings.json` and `openings_detected.json`. Finds the detector in `<project>/detector`. |
| `cad_test/src/openings3d.py` | **New.** The cutting (rules in its docstring). |
| `cad_test/src/merge_cad.py` | Changed `main()` and the new `openings_for()`. `strips()` and `solidify()` are untouched. |
| `cad_test/src/build_stages.py` | Changed (door-symbol lines, opening stats, the openings check). |
| `cad_test/src/make_html_cad_merged.py` | Changed. |
| `cad_test/src/README.md` | Pipeline order and the openings. |
| `cad_test/src/openings_mapping.json` | **New input.** Layer roles for the detector (the same as `detector/mappings/sukhumvit.json`). |
| `cad_test/src/heights.json` | **New input.** Door and window heights read from the elevations (copy of `detector/keys/sukhumvit_heights.json`). |
| `cad_test/src/regions.json`, `grid.json` | Inputs the pipeline scripts made earlier (where the two plans sit on the sheet; the floor shift), now kept so the openings step can be re-run from the DXF. |
| `cad_test/src/house3d.json`, `house3d_merged.json`, `house3d_stages.json` | Regenerated data. |
| `cad_test/src/openings.json`, `openings_detected.json` | **New data.** |
| `cad_test/house_3d_preview.html` | The rebuilt page (751,129 bytes; 629,344 before any openings). |
| `cad_test/test_house_openings.mjs`, `test_house_openings_before.json` | **New** browser test and the passage walk on the page before the openings (the test reads the stored list; with `BEFORE_URL` set to `previous_before_openings_2026-10-27/house_3d_preview.html` it walks that page itself). |
| `cad_test/previous_before_openings_2026-10-27/` | The page, pipeline files and data as they were on 19 Oct (backup). |
| `viewer-modes/test_viewers.mjs` | Only TEST_PORT, TEST_TMP and TEST_PROFILE from the environment (defaults as before). The old copy is in `viewer-modes/previous_2026-10-27/`. |
| `detector/` | **New.** The opening detector (openings.py sha1 `730a29203309`, recorded in openings.json), its mappings, the answer keys, the scorer and the results. See `detector/README.md`. |

Not kept in the project (derived, or analysis files): the DXF (`dwg2dxf` makes it) and the drawing caches `prims.pkl`,
`src/openings_png/` (the same PNGs are in `detector/output/`), the unchanged copies of the shared viewer code and of
the Srisawan page, the analysis scripts, logs and negative controls of the reviews, and the browser profiles and test
output folders.

**Shared viewer code: not changed.** `viewer_modes.js` and `build_replay.js` are untouched, so the presidential and
Srisawan pages need no rebuild.

## The openings in 3D

| | Ground | Upper | Total (3a) |
|---|---|---|---|
| Doors / windows / passages found | 19 / 16 / 10 | 13 / 21 / 19 | 32 / 37 / 29 (34 / 42 / 29) |
| Glazed (windows + eitherKind sliding glass doors) | 19 (16 + 3) | 21 | 40 (42 windows) |
| Lintels | 31 | 34 | 65 (71) |
| Window panes | 19 | 21 | 40 (42) |
| Sill walls | 1 (ground-010, 0.90 m) | 0 | 1 |
| Fins removed | 2 single-line pieces of ground-038's swing | 11 glass leaves and sashes: the casements on the north facade (upper-030, -042), the leaves of upper-008, -010, -043 (UE-18) and -006 (UE-13), the sash of upper-044 | 13 (11) |
| Doors without a lintel | ground-036 (site gate: nothing at one jamb) | none | 1 (2) |
| Windows without a lintel (head = top) | ground-042, -043, -044 (3.90 m) | none | 3 |

Gone from the model with the four false detections: the 4.85 m pane and lintel along the glass bridge, the 1.55 m
lintel across the stair hall, the 0.7 m cut in the shower screen line, the 1 m pane in the master-bath shower. Gone
with the screen role: the three grille "windows" round the service yard and their lintels; the grille is back along the
whole staff-block facade. The stair-landing door's cut and lintel are a straight 1.0 x 0.1 m block between the jambs.

**Heights** (heights.json, the elevations): ground doors and windows to 3.00 m, upper to 2.60 m, windows from the floor.
16 openings take values from the elevation rows and 2 more from their glass-corner partner. The ones that change
something: ground-042, -043 and -044 run to 3.90 m (double-height glazing, no lintel); upper-051 (UE-01, tag AW17) to 2.55 m.
15 of the 16 rows matched; the ground AD1 row (x 38.698, y 16.86-20.91) matched nothing, and the key has no opening there.

## Numbers that changed

| | Before openings | Round 3a | Round 3b |
|---|---|---|---|
| Wall runs (ground / upper) | 30 / 23 = 53 | 32 / 27 = 59 | 32 / 27 = **59** |
| Glass runs | 23 / 26 = 49 | 4 / 8 = 12 | 4 / 7 = **11** |
| Single-line runs | 15 / 7 = 22 | 10 / 8 = 18 | 10 / 7 = **17** |
| Wall area | 30.92 / 37.36 m² | 30.45 / 36.86 m² | 30.45 / 36.87 m² |
| Floor plates | 3 (494 m²) / 1 (439 m²) | unchanged | **unchanged** (sha1 `ad13064344f9`) |
| Lines ignored (sort caption) | 42,316 | 39,463 | 39,463 |
| house3d_merged.json / stages | 30.9 / 677 KB | 80.0 / 754 KB | 78.9 / 754 KB |
| Page | 629,344 bytes | 751,450 bytes | 751,129 bytes |

The plan and the product doc quote some of these numbers; both were brought in line on 27 Oct 2026 (plan section 2.3:
"about 42,000 ... lines ignored" is now 39,463, "53 wall runs" is 59; the glass runs are now 11).

## How to rebuild (Git Bash from the project folder; about 40 s in all)

Needs `plan.dxf` in `cad_test/src/` (from `dwg2dxf -y -o plan.dxf "Test Sukhumvit Residence.dwg"`, see `cad_test/src/README.md`).

    cd cad_test/src && export PYTHONIOENCODING=utf-8
    python -B build3d.py && python -B find_openings.py && python -B merge_cad.py && python -B build_stages.py && python -B make_html_cad_merged.py ../house_3d_preview.html

Measured on 27 Oct from the project folder: 41 s for the five steps (a fresh drawing cache included), and the page and the
three data files came out byte for byte the same as the ones in the project. `openings.json` differs only in the detector
folder it records. No `__pycache__` is written. Delete `plan.dxf` and `prims.pkl` afterwards if you want the folder as it was.

The detector on all four drawings and the score (see `detector/README.md` for the drawing caches it needs):

    python -B detector/run_all.py

Tests (each in its own headless Edge; set TEST_PORT / TEST_TMP / TEST_PROFILE to keep two runs apart):

    node viewer-modes/test_viewers.mjs              # the whole viewer suite, about 10 minutes
    node cad_test/test_house_openings.mjs           # the openings checks, about 25 s

## Test results (round 3b)

**Existing suite, all sections, 127 checks, 90 % threshold restored.**

| Run | Result | House fps | Note |
|---|---|---|---|
| run 1 | **127 passed, 0 failed** | 19 | "sliding works at random spots along walls": **37 of 40** (the same 37 as on the page before the openings) |
| run 2 | 126 passed, 1 failed | 13 | "Walk slides along a wall when you walk into it at an angle": slid 0.16 m. That check walks from wherever the earlier timed walking left you (here a corner: one side 0 m), and the machine was loaded (18 Edge processes of other runs, 13 fps) |
| run 3 | **127 passed, 0 failed** | 11 | the same page, run on its own |

**Why the random-spot check is back to 90 %:** the reviewer's probe showed every miss on the round-3a page was a
pier, column or convex corner; four of them were the piers between the garden sliders that round 3a had opened.
With the sliders glazed again (H-01) those spots end on glass, as before the openings: 37 of 40. No exclusion rule
was needed, so the procedure is unchanged. A probe that lists the spots that miss (a wall-face filter would be
the principled exclusion) was used in the review; it is not kept.

**test_house_openings.mjs: 13 passed, 0 failed** (23 s).

- PASS: the page loads without errors; 16 + 13 doors, 19 + 21 glazed openings, 10 + 19 passages; 4 piece meshes.
- PASS: the floor plates are unchanged (fingerprint).
- PASS: every door can be walked through: 29 doors (the glazed sliders are now checked as windows), 20 both ways,
  8 from the only side with floor, 1 skipped (ground-036, the site gate).
- PASS (**new**): passages are left as they were: knee and chest rays across each passage at 1/4, 1/2 and 3/4 and a
  ray up from 1 m hit no lintel, sill or pane (29 passages; one sample point of upper-028 left out, where the real
  door upper-009 crosses that false passage).
- PASS (**new**, replaces "every passage can be walked through"): no passage is harder to walk through than before
  the openings were cut: the same walk on the page from before the openings, stored in
  `test_house_openings_before.json`. Blocked both before and now (information): ground-021 (the
  gym's open side, a real passage blocked by a 1 m single line in the drawing), ground-031, upper-026, -028, -029
  (false passages).
- PASS: every window stops you: 39 tested (3 of them the glazed sliders), 1 skipped (ground-040, no floor). **Stricter:**
  the ray must hit the window's own pane or sill mesh, where its glazing is, and 60 % of the rays must; a wall that
  meets the window may stop the rest (upper-053, UW-02: 2 rays end on the wall stub against its north end).
- PASS: a lintel sits above every door at its head. **Stricter:** a door may go without one only where nothing stands
  at a jamb (jambGap null): only ground-036.
- PASS: the heads stay put at 3.50, 2.00 and (**new**) 4.50 m wall heights.
- PASS (**new**): panes that reach the top of the wall follow it: at 4.50 m, ground-042, -043 and -044 are still glass
  at 4.20 and 4.45 m.
- PASS: no fins in any hinged door's or sash's swing (26 doors and casements, 30 leaves); no glass or single-line piece
  in front of any of the 40 glazed openings; no page errors.

**Negative control** (a copy of the page with faults put in, run through the test): a page with one door's lintel
removed (ground-003), two windows' panes removed (upper-001, -003), a lintel put over a passage (upper-015) and the
panes' `top` flag dropped fails exactly the five checks that should fail (passages, windows, lintels, heads, top
panes) and passes the other eight. The round-3a negative control (fins) still applies.

## Detector issues left (drawing metres)

- **GE-17** (53.763, 7.90-11.85): the vehicle gate, a site element; missed. The model keeps its closed leaf.
- **ground-043** (19.373, 14.51-18.65): the 2.90 m courtyard slider GW-19 merged with the fixed corner glass (4.15 m),
  read as an eitherKind window. In 3D it is glass like the other three sliders, and the corner now closes.
- **upper-033** (UW-01, 82.869, 8.01-12.51): sliding glass door to the west balcony in the key (eitherKind), a sliding
  window here; **round 3a's report was wrong to call it eitherKind: the detector's flag is false** (a planter edge runs
  outside it). Under the decision it is glass either way.
- **Extra passages** that cannot be walked through: ground-031, upper-026, -028, -029 (the old upper-028/-030/-031).
  Nothing is cut for passages, so they are harmless in 3D.
- **Bank L1-023**: the curtain-wall door's line sits 0.1 m inside the facade slot (a 10 cm recess above it). A rule
  that snaps a door to the slot in its frame lines is left for the bank round (done in the bank round: see `bank_test/README.md`).

## Assumptions (defaults picked and stated)

- **Low-wall window.** ground-010 is "an opening over a low wall (no glass drawn)"; no elevation shows it, so it keeps
  the plan's default sill (§3.2): 0.90 m, and the decided window rule gives it a pane.
- **Grilles.** The base model still draws A_Grill / W_Grill as glass at the glass-wall height (top minus 0.6 m), as
  before any opening; they are just no longer cut.
- **Glass walls.** Glass that is not in any opening (WALL-GL screens, the bridge sides) keeps its old height, the top
  minus 0.6 m.
- **Passages.** Their heads are recorded in openings.json but not used.

## Open questions for the owner

**27 Oct:** the owner had no answers to these, so every one stands as built (the pane and sill stay, the passage stays
untouched, mappings keep layer roles only). They stay listed so that anyone who knows can change them.

1. Should an "opening over a low wall (no glass drawn)" (ground-010, the kitchen pass-through) get no pane, only the
   sill wall and the lintel? The decided rule glazes every window, so it has one now. And is the 0.90 m sill wanted?
2. Should a passage clear a 1 m single line that runs along it? ground-021, the gym's open side, is blocked by one; the
   decided passage rule leaves it.
3. `viewer-modes/test_viewers.mjs`: the TEST_PORT / TEST_TMP / TEST_PROFILE change is now in the shared test (defaults as
   before). It is the only change (the threshold is back to 90 %); the old copy is in `viewer-modes/previous_2026-10-27/`.
4. ~~Where will the detector live in the project?~~ Done: `<project>/detector/`, which find_openings.py looks in first.
5. Floor areas: may a mapping carry `areas` (where each floor's plan sits on the sheet), so that a new drawing needs no
   code in `tools/prims.py`? That is input data, not detection tuning, but it is more than layer roles; the four
   mappings were left without it (ready-made versions in `detector/mappings_with_areas/`).
6. The house has no 3ds Max export, and none was added. The owner's Max conventions (live spline + Extrude to mesh +
   Smooth) would apply if one is made.
