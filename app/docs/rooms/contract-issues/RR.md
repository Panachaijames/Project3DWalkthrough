# Contract issues: RR, independent review and fix (rooms milestone)

Written only by RR (docs/rooms/WORK_BREAKDOWN.md). 12 Nov 2026, on branch `milestone-rooms` at HEAD `88bdc94` (RI). Every
change below is in the working tree only: nothing was committed, pushed or deployed; `app/data` and the owner's
5710 / 8710 were not touched; ports 5749 / 8749 / 4749 / 9749, temp folder `%TEMP%\wt-rr`.

## 0. In short

* **Four reviewers** (fidelity, code, breaking it, the staff path) reported **34 findings**; triage merged them into **30
  items**: **22 defects** (builder 14, viewer 3, web 5; three builder items had a web part too) and **8 answers**. None was
  rejected. The working notes: `%TEMP%\wt-rr\FINDINGS-{fidelity,code,breaking,staff}.md`, `TRIAGE.md`.
* **Fixed, each with a test**: builder 11 of 14 (and part 1 of a 12th), web 5 of 5 and the web parts of three builder
  items, viewer 3 of 3 (by the main session, after the viewer fix step stopped without changing anything). **Not
  fixed**: two builder items (FID-2, FID-5(a)) and the second part of BRK-3, which needs a contract change. Section 6
  lists them.
* **The re-run caught one regression** in the builder fixes (BRK-1's open side hid a pocket's mouth: RA-18 failed on the
  bank's L1-018); the main session fixed it with a test and ran what it touches again (section 3, BRK-1; section 8).
* **Pins that moved**: the house's and the tower's new-rule pins (model, top view, Max script) and five reference-building
  fixtures; the bank's pinned model, the old rule's pins and the walk-parity golden did not move (section 7).
* **The re-run from a clean start** (WORK_BREAKDOWN RR: RI's steps 3 - 6): section 8.

How each finding was handled: the fixers' notes are `%TEMP%\wt-rr\RR-builder.md` and `RR-web.md`; the viewer fixer wrote
none (it stopped without changing anything); the main session made the three viewer fixes (section 2, 4) and took each
out again to see its tests fail. "Fixed" below means a code change and a test that checks it; the web fixer
also took each fix out and saw its tests fail; the builder fixer did that by measurement for FID-1 only and otherwise
relies on how the tests are built.

## 1. Fidelity (the floors, holes, rooms and stairs against the drawings' plots)

| Finding | Verdict | Outcome |
|---|---|---|
| **FID-1** (+ S5) the new suite, after its single lines are set aside, loses its 52 m² living room: the face becomes an "enclosed shape" and its three names go by distance to slivers of 1.5, 3.0 and 7.6 m², with no flag | confirmed, medium | **Fixed** (builder). `build/rooms.py` `rooms_of_network(..., aside=)`: edge stretches along set-aside lines are left out of both sides of the half test (a face with under 25 % of its edge left to judge stays a shape). Two new `room-open` check flags: "A closed area is not a room" (10 m² or more in no room) and "<name>: placed in a small room nearby" (a name given by distance to a room under 4 m²). Measured on the new suite with the 59 set-asides: before 16 spaces, LIVING & DINING AREA on 1.5 m²; after 18 spaces, L1-R007 LIVING & DINING AREA 59.7 m² with FOYER and BAR; plate 274.3 unchanged. Tests: `test_r1_fixes.py::test_lines_set_aside_along_a_rooms_walls_do_not_unmake_the_room`, `test_r3_overlay.py::test_room_open_for_a_lost_room_and_a_name_given_to_a_small_room`; the acceptance check `rooms-checks` now lists the names an aside build loses (`namesLost`, must be empty) |
| **FID-2** door and casement swings on the window layer close faces: seven 0.5 m² quarter circles (and one 0.6) of plate and ceiling outside the house's north facade; swing sectors cut out of rooms | confirmed, low | **Not fixed** (needs the door finder's leaf and arc items carried from `build/detect.py` into `network_of`; it moves plate0 on the drawings, so it was left for a later round to keep RA-4 safe) |
| **FID-3** (+ FID-5(b)) plate that is in no room (the old suite's 17.5 m² garden sala; the house's 15.3 m² upper east balcony) has floor and a ceiling, and no fix could take them away | the shapes: answer; the missing staff answer: confirmed, low | **Answered** for the shapes: by R-2.5 a detached closed outline over 12 m² is floored and by R-5.2 the ceiling follows the ring; whether the sala and the balcony are roofed is for the owner. **Fixed** for the staff answer: `build/fixes.py` `room_target` matches a room fix with slab or ceiling `'none'` to the face of N' holding its point, else to the piece of plate less network less rooms; the Check step's panel offers "No floor here" and "No ceiling" when the clicked point is on plate in no room. Tests: `test_r1_fixes.py::test_no_floor_and_no_ceiling_on_plate_that_is_in_no_room`; `apps/web/test/rooms/rr-screens.test.tsx` "FID-3 + FID-5b" |
| **FID-4** the bank's L1 `ATM`, written outside the east wall, names the stair lobby | answer | By R-3.2 rule 4 (a name in no room goes to the nearest room within 1.5 m); GAPS 5.1 already accepts `ATM` as a name; the key scores 7 of 7. A room fix renames the lobby |
| **FID-5(a)** rounded plate in the V notches between the new suite's bays (3 x 0.7 m² outside the facade) | confirmed, low | **Not fixed** (the step that keeps the fillet, the ring or a kept bridge, was not traced; it moves plate0) |
| **FID-6** the tower's lift holes are the cars' X rectangles; 13 - 14 m² of floor and ceiling stay inside the 22.7 m² passenger shaft | answer | By R-4.3 (the hole is the X rectangle; the lift-cell rule stops at 12 m²). Option later: allow 12 m² per lift door in the lift-cell rule |
| **FID-7** the old suite's `GYM&YOGA` stays in the study as a second name | answer | GAPS 5.3 (15 of 16, RA-7's should of 13 met; a room fix names the gym) |

## 2. Code

| Finding | Verdict | Outcome |
|---|---|---|
| **CODE-1** (+ BRK-2) a 0.3 m tile grid is read as an X void (4.5 m²) and cut; furniture drawn as a rectangle with two diagonals is cut as a shaft; a cut X hole raises no flag and no fix can undo it | confirmed, medium | **Fixed** (builder and web). `build/xmarks.py`: an outline stretch counts as drawn only along lines within 5 degrees of that side; a box is refused when two or more other long lines run parallel to a diagonal 5 cm or more beside it (the first form of this rule, "crossed through its middle", lost the tower's four shafts and the house's stair-hall void, so it was narrowed). `build/slabs.py` leaves an X hole uncut when a slab `'floor'` room fix lies in it (`why: 'kept as floor by staff'`). `out/overlay.py` raises an info flag "An X mark was cut as a shaft / void" for every cut X hole (kind `hole-skipped`, a bbox, `ref {}`: the kinds and ref keys are frozen). The flag gets an **It is floor** button that writes `{ floor, at, name: null, slab: 'floor', ceiling: 'auto' }`. The rectangle-with-diagonals on a layer that is not furniture is still cut, as R-4.3 says, but is now flagged and can be undone. Tests: `test_r1_slabs.py::test_a_tile_grid_is_no_x_mark`, `::test_staff_keep_the_floor_in_an_x_hole`; `test_r3_overlay.py::test_hole_skipped_only_for_the_lowest_floor_and_the_large_marks`; `rr-screens.test.tsx` "CODE-1 + BRK-2" (2) |
| **CODE-2** (+ BRK-6) the head ray grows with the eye slider: at eye 1.9 m the walker stops on stairs, at 2.2 m it cannot move in a 2.7 m storey | confirmed, medium | **Fixed** (viewer, main session): `modes/state.ts` `HEAD_REACH = 1.90`; `modes/walk.ts` `headHit` reaches `min(eye + 0.30, HEAD_REACH)`, so the eye slider moves the camera only. DESIGN R-9 and R-9.10 and the main DESIGN's D-13 "Climbing" row amended. Tests: `packages/viewer/test/unit/modes/climb-review.test.ts` (the reference stair up and back at eye 2.2; a 2.7 m storey walked at eye 2.2; the reach equals the default eye's); each fails with the fix taken out |
| **CODE-3** (+ known item 1) stair fixes: the builder reaches 0.3 m where R-6.3 says 0.5 m, and the web judges on the convex hull of the treads, so the whole 0.3 - 0.5 m band (7.06 of 21.6 m² on the house's `S1`) matched no stair | confirmed, medium | **Fixed** (builder). `build/stairs_read.py` `FIX_NEAR = 0.5`; `build/bank.py` gives the stairways row the outside of the joined treads and landings (no longer the hull), so the web and the builder judge one shape. Tests: `test_r2_build.py::test_a_stair_fix_reaches_half_a_metre_as_the_design_and_the_web`, `::test_the_stairways_row_carries_the_real_outline_not_the_hull` |
| **CODE-4** (+ BRK-7) a floor with no slab part in a stack that has slabs: Walk teleports there, then cannot move | confirmed, low | **Fixed** (viewer, main session): `modes/walk.ts` `groundRay`: no hit on a floor with no walkables is ground at that floor's level when the level is within the step window of the foot (as the old walker walks such a floor); off the side of a flight it stays an edge. The triage's proposal ("no hit -> the foot's own height") was tried first: the walker then left the stair's top tread onto the slabless floor at 2.81 m and floated there, so the level is used. DESIGN R-9 amended. Tests: `climb-review.test.ts` (the reference building with its upper slab taken out: the upper floor walked; the stair climbed onto it and back; off the flight's side over the well still an edge); the first two fail with the fix taken out. No real build has shown such a floor |
| **CODE-5** `doorway_candidates` can pair one wall end twice | confirmed, low | **Fixed**: `build/network.py` skips ends already used. Test: `test_r1_network.py::test_two_doorway_closings_never_share_a_wall_end` |
| **CODE-6** with `stairs: 'lines'` on a shifted floor, the "kept as lines" text gives build-frame coordinates | confirmed, low | **Fixed**: `build/stairs_build.py` takes off the floor's shift. Test: `test_r2_build.py::test_the_lines_option_text_is_in_the_floors_own_frame` |
| **CODE-7** `_mouth` accepts a free stretch of 5 m where R-2.5 says 3 m | confirmed, low | **Fixed in code, behaviour kept**: `MOUTH_STRETCH = 5.0` named (a mouth may follow a round closing's curve; its chord stays 3 m or less). Test: `test_r1_network.py::test_a_mouth_is_a_chord_of_3_m_and_a_stretch_of_5_m`. **Not done**: DESIGN R-2.5 should read "one stretch of 5 m or less whose ends are 3 m or less apart" |

## 3. Breaking it

| Finding | Verdict | Outcome |
|---|---|---|
| **BRK-1** a gap over 3 m in an outside wall loses floor with no flag (a 10 x 8 m hall with a 5 m gap: 6.7 of 80 m² floored; a 160 m² wing: 74 m² lost silently) | confirmed, medium-high | **Fixed** (builder). `build/network.py` `_unfloored` adds an "open side": a piece of (hull of N' less plate less N') of 10 m² or more with 80 % or more of its edge on the network or the plate; the existing `slab-gap` flag asks about it (no mouth: "draw a line across the gap, or say it is outdoors"). Why 80 % and not the 2/3 triage proposed: at 2/3 four real places would flag (tower L30 0.78, old suite 0.75, house upper 0.74, house ground 0.69); at 80 % none does, and the reviewer's hall is 0.85. **Caveat**: the margin to the tower's 0.78 is thin, and a gap wide enough to bring the share under 80 % is still silent. Tests: `test_r1_network.py::test_a_wide_gap_in_an_outside_wall_is_asked_about`, `::test_a_notch_and_a_court_are_not_open_sides`. **A regression it caused, found by the re-run and fixed (main session):** RA-18 (must) failed on the bank's L1-018: with that door undone, the 10.6 m² room behind it was found both as a pocket (10.5 m², its mouth across the doorway) and as an open side (10.79 m²: it also takes in the doorway's strip in the wall), and "one row per place" kept the larger, the open side, which has no mouth, so the flag lost its **Close it here**. `_unfloored` now takes the open sides last, as the fallback they are: one that the other rules' pieces cover by more than half is skipped; one that is kept takes in the smaller pieces inside it. With no open side (every normal build of the five drawings) nothing changes. Test: `test_r1_network.py::test_an_open_side_never_hides_a_pockets_mouth` (three side rooms; all three fail with the fix taken out) |
| **BRK-2** furniture drawn as a rectangle with two diagonals is cut as a shaft / void | confirmed, medium | With CODE-1 (above): flagged, and **It is floor** undoes it |
| **BRK-3** after a re-upload of a drawing that moved, fixes land in the wrong place silently (moved 5 m: a "no floor" fix cuts the next room; a closing line is applied in empty space, "matched") | confirmed, medium | **Part 1 fixed**: a staff closing line with neither end on or within 0.5 m of the network is reported unmatched ("A closing line meets no wall: has the drawing moved?"); it is still applied as drawn (R-6.3). Tests: `test_r1_network.py::test_a_staff_closing_line_that_meets_no_wall_is_unmatched`, `test_r3_overlay.py::test_fix_unmatched_for_the_new_fixes`. **Part 2 not done; the owner said yes on 12 Nov, to be built with plan next action 16** (a room fix that remembers its room's area and names, flagged when they differ): `RoomFix` is in the frozen contracts (`apps/web/src/upload/contracts.ts`, the StrictModel in `services/api/walkthrough_api/models_upload.py`, `walkthrough_builder/contracts.py`): a contract change for the owner |
| **BRK-4** "Climb it as drawn" refused over 0.25 m without saying so; risers printed with two decimals (0.1375 reads 0.14) | confirmed, low | **Fixed**: `build/stairs_build.py` says '"Climb it as drawn" is not possible: each step would be 0.263 m (the limit is 0.25 m)', and prints risers with three decimals. Tests: `test_r2_build.py::test_the_riser_check_and_climb_it_as_drawn`, `::test_the_riser_text_has_three_decimals` |
| **BRK-5** a stair that starts just inside an entrance door gets its bottom point 0.3 m outside, on no slab | confirmed, low | **Fixed**: `clear()` checks the 0.3 m fallback, then the 0.1 m point, then the nearest plate point; never an off-plate point. Test: `test_r2_build.py::test_the_bottom_point_never_leaves_the_plate` |
| **BRK-6** = CODE-2 (confirmed by running, worse than its numbers) | | fixed (section 2) |
| **BRK-7** = CODE-4 (confirmed on an edited model) | | fixed (section 2) |
| **BRK-8** a level change of more than 1 m while on a stair leaves the walker hung; the replay card accepts an upper level at or below the lower one | answer | Not reachable through the screens: the Build settings card locks the modes to Orbit (`replay/index.ts:193`) and Walk re-enters on a level; the builder refuses floors out of order. Only a direct `heights.apply` call shows it; the card's order check belongs to the replay card's own round (the card is the 4 Nov baseline's) |

Tried by the breaking reviewer with no finding: open networks on one floor, corner gaps, crossing lines that are not X
marks, stairs with no direction or `UP` at both ends, risers that do not fit, stairs over doors and walls, drawings far
from the origin or turned, three floors, a 1200-room floor (build 183 s, 295 MB); in Node, 63,000 random steps on seven
real and synthetic stairs with no rise, drop or headroom violation.

## 4. The staff path (a non-programmer's view; RA-17 timed on the tower and the new suite)

| Finding | Verdict | Outcome |
|---|---|---|
| **S1** Show on a flag far down the list moves a plan that is scrolled off screen (the last of 32 flags: the canvas 3309 px above the window) | confirmed, medium | **Fixed** (web): the plan column is sticky under the app bar on a wide screen (`CheckStep.tsx` `PLAN_COLUMN`), and Show (on a flag or a fix row) and "Open this stair" scroll the canvas into view after the render. Tests: `rr-screens.test.tsx` "S1" (3); `tests/e2e/rr-web.spec.ts` (at 1400 x 880 and 1366 x 680; with the fix out the canvas top was at -154 / -314 px) |
| **S2** (+ **S3**) the stair card has only Show; its kind label repeats the title | confirmed, low-medium | **Fixed** (web): **Open this stair** on a stair card that asks for a check and names its stair (the tool Rooms and stairs, that stair's panel, outlined on the plan); the kind label reads "Stair". Tests: `rr-screens.test.tsx` "S2 + S3" (2); `rr-web.spec.ts` |
| **S4** "A gap of 0.15 m ... closed as a doorway" | answer | The text and the button are R-6.1 / R-2.6's own (0.10 - 2.0 m gaps on purpose); the small gaps between armchairs are known item 3 (the door finder's round). Later, optionally: say "gap" under 0.6 m |
| **S5** = FID-1 | | fixed (section 1) |
| **S6** "3 names in one room" does not list the names | confirmed, low | **Fixed** (builder, `out/overlay.py`): "3 names in one room (LIVING & DINING AREA, FOYER, BAR): ...". Test: `test_r3_overlay.py::test_the_reference_flags_carry_the_design_texts` |
| **S7** (+ **S14**) the Check plan opens small and off-centre; on the house it fits the whole sheet (elevations and both plans) | confirmed, low-medium | **Fixed** (web, `plan/controller.ts`): the first view, F / 0 / Home and Fit fit the chosen floor's plate, parts and stairs (or its area box), with a margin of 0.5 m or 4 %; it fits again when the floor changes, not after a Rebuild of the same floor. Tests: `apps/web/test/rooms/rr-canvas.test.tsx` "S7" (4). The house's DWG itself was not re-run |
| **S8** stair ids `S1` against `L29-ST1`; the upper floor says "0 to climb, 1 stair in all" | answer | By R-7 / R-12: `S<n>` is a climbable stairway of the model, `<floor>-ST<n>` a stair drawn on one floor; the count is of stairs that start on that floor. Optional wording: "1 stair arrives from Ground floor" |
| **S9** the set-aside rows mean nothing | answer (mostly not as described) | Each row shows the handle and the layer: the "0" is the new suite's layer named `0`, and the tick has a tooltip. A length and a Show button per row are a later improvement to the upload milestone's list |
| **S10** "rooms" means two things on the Save step and the changes list ("9 rooms" is the number of names) | confirmed, low | **Fixed** (web): "9 room names"; the changes list's row reads "Room names". Tests: `rr-screens.test.tsx` "S10" (2) |
| **S11** "Floor here" far outside the building is taken without a word; fix rows speak in coordinates | answer | By R-6.3 the rebuild raises "A room fix finds no room"; a check before the build needs the faces of N' in the overlay. Fix rows have a Show button. Later |
| **S12** hovering a room shows nothing | answer | Not in DESIGN R-6.4; the room is found with Rooms and stairs and a click (now outlined: S13) |
| **S13** the Floor plate tick seems to do nothing; a picked room is not marked | confirmed in part, low | **Fixed** (web, `plan/draw.ts`, `marks.ts`, `overlay.ts`, `colours.ts`): the plate has a faint tint under its dashed outline; the room or stair open in the panel is outlined in a strong colour whatever the ticks. Tests: `rr-canvas.test.tsx` "S13" (3), `rr-screens.test.tsx` "S13" (1) |
| **S15** stair treads are drawn in the wall colour; the legend's Stairs swatch is a pale green | confirmed, low | **Fixed** (viewer, main session): `packages/viewer/src/model/styles.ts` treads and landings `#b9c7b4`, edge `#6f8a6a`, as `step` and the legend's Stairs. Tests: `climb-review.test.ts` (the default styles; the reference building's treads out of `buildScene`); both fail with the fix taken out. A project's own `partStyles` still overrides them |

RA-17 by the staff reviewer (scripted through the screens, a person's time estimated): the tower 2.1 min scripted, about
24.5 min for a person (two passes of set-asides: 39 flags, then 1); the new suite 2.3 min, about 28.4 min (33, then 6);
the second versions with the fixes carried over 0.7 / 0.4 min. Target 30 min: met, by an estimate, closely on the suite.

## 5. The integration's known items

| Item | Outcome |
|---|---|
| 1. A stair fix inside the house's L outline found no stair (RI-B section 4) | confirmed and worse than described; **fixed** with CODE-3 |
| 2. After one pass of set-asides, 1 (tower) and 6 (new suite) more single lines are flagged | **answer**: a line is "single" only once its partner face is set aside; a second short pass (2 - 12 clicks) and one rebuild are expected, and RA-17's 30 min is still met |
| 3. Small doorway closings between furniture on the new suite | unchanged: the door finder's round (plan next action 16) |
| 4. A name on a terrace (R0 item 4) | **decided by the owner on 12 Nov: yes, as proposed** (built with plan next action 16). Was **for the owner to decide**: no drawing has one (the five overlays checked). Today such a name goes to the nearest room within 1.5 m or raises `room-open`. Proposed: a name on a terrace piece or on an area answered "outdoors" stays as that area's label, is not given by distance and is not flagged (a small builder change) |

## 6. What is not fixed, and what other files still need

* **Viewer**: none left (the three were fixed by the main session after the viewer fix step stopped without changing
  anything: it read the relayed request as a status question).
* **Builder (2 and a half)**: FID-2 (swings on the window layer), FID-5(a) (V notches between bays), BRK-3 part 2 (a
  contract change: `RoomFix` remembers its room).
* **DESIGN.md**: done by the main session. R-9's head ray and ground ray are amended in place (and R-9.10, and the main
  DESIGN's D-13 "Climbing" row); every other rule the fixers changed is listed in a new last section of
  `docs/rooms/DESIGN.md`, "Amended after the independent review (12 Nov 2026)", which takes precedence over the text
  above it.
* **Readers of `rooms.open`**: rows with `why` carry no `space` (the room is in `room`). Nothing in the web app, the API or
  the viewer reads `rooms.open` today (searched); `out/overlay.py` handles both shapes.

## 7. Pins that moved

**The new-rule pins (`services/builder/tests/test_r_rooms_golden.py`, RI's, provisional), the house and the tower only:**

| Drawing | File | Before (RI) | After (RR) |
|---|---|---|---|
| house | model.json | `c7824bca60086c43d010eebc5c1f3aaa654fdcf5` | `d90ccc3c6e5db0eb703b648b68d9400b46de8785` |
| house | topview.png | `9fb483f70903364e6e4a2038f3dbf2c925473559` | `f0d77602836a289101824063b67db154c7c74a52` |
| house | Max script | `10148e2364460d7b95403c62217adcc89772d614` | `66794ff4df6982d8af3906c41cae717c609f0f97` |
| tower | model.json | `3d25cdf722fb699a1aaa83203205834c445620ca` | `9f95de8a365c6a5cf9bcd953690d241f0291c053` |
| tower | topview.png | `d7d95040ca1c05030178e18dfcca5e42078cb623` | `2cfdccca0c676f1f4cd1ffad36582f6f67e8ace4` |
| tower | Max script | `cd5e439dfc7ca943e851f579b0f27b99935ef52a` | `8659ebdcb593d8c6a5f09c98ad81404328772650` |

Why: the X-mark finder (CODE-1) no longer reads the "+" where two lines cross as the diagonals of a diamond. The diamonds
it found before (1.5 m² in each tower lift, 3.85 m² in the house's stair-hall void) lay inside real holes, so only the
holes' outline points changed: the part counts, every floor row and `holesArea` are the same (the builder fixer compared
the models). The Max script carries the model's stamp, and the top view draws the holes. **Did not move**: the bank
(`BANK_NEW_RULE_SHA1` `54ef1ac240bb...`, so the bank's path through the screens still gives the pinned bytes), both
suites, every `stages.json` and CSV, `test_r_old_rule.py` (the old rule byte for byte) and the walk-parity golden.

**The reference building's fixtures** (frozen; re-made with the scaffold's tool `make-reference-building.py fixtures`,
as RI did): `fixtures/rooms/build-result.reference.json` (`c94e2f66...` -> `ee304f37...`), `overlay.reference.json`
(`83471734...` -> `b0949a81...`), `flags.every-kind.json` (`88bf1aa2...` -> `636a6a42...`),
`runs/reference-build/out/report.json` (`36024e0b...` -> `4cce60d0...`) and `runs/reference-build/job.json`
(`ecd256d0...` -> `1e9679fd...`, the report's size and sha1). Why: the stairways row's outline and point (CODE-3), the
names in the room-names text (S6), and one new info flag for the upper floor's cut X void (CODE-1). The models,
presentation, stages, settings and the three stairs models did not move (`--check`), so the stamp `bfcd621e0a22` and the
walk-parity inputs stand. `fixtures/README.md`'s five sha1 rows were still the old ones after the fixers; RR updated them
and added a note on the new row shapes.

**Test expectations that follow the fixes**: `test_r1_drawings.py` (the old suite's "not a room" row of 16.6 m², the garden
sala; the house's upper floor one of 13.9 m², the east balcony; the house's ground X marks listed 3 -> 2: a 0.78 m² mark
that was never cut is no longer a mark), `test_r2_drawings.py` (riser texts 0.24 -> 0.244, 0.22 -> 0.222),
`test_r3_outputs.py` (the `hole-skipped` count now includes the cut X holes), `apps/web/test/rooms/fixes.test.ts` (the
reference overlay now has five flag kinds; the test reads "the fixture's flags less slab-gap, doorway and stair"), and
`apps/web/test/mock-api/rooms.ts` (the mock's rebuild keeps an X hole as floor when a `floor` fix lies in it, as the
builder now does).

**Frozen things worked around, not changed**: `FlagKind` and `FlagRef` (the cut-X flag reuses `hole-skipped` with an
empty ref; the "placed by distance" flag's ref is `{ room }`), `apps/web/src/build/testids.ts` (the two new test ids
`flag-open-stair` and `flag-it-is-floor` are defined in `FlagList.tsx`).

## 8. The re-run from a clean start (RI's steps 3 - 6)

Run by the main session on 12 Nov, 10:23 - 12:12, after the three viewer fixes, one step at a time (so the API tests ran
alone), on ports 5749 / 8749 with its own stores: scripts and logs in `%TEMP%\wt-rr\rerun` (`all.sh`, `logs\summary.txt`), the
acceptance in `%TEMP%\wt-rr\acc` (`result.json`, `rooms-result.json`). Then, after the RA-18 fix (section 3, BRK-1), the runs
that fix touches and three that the first part could not settle (`after.sh`, 12:14 - 12:59). Nothing deployed,
pushed or committed during the runs; `app/data` and 5710 / 8710 untouched.

| Step | Command | Result |
|---|---|---|
| versions | `npm run check:pins` | ok (28 npm, 28 API pip, 19 builder; LibreDWG 64 files) |
| types | `npm run typecheck` | 0 errors |
| unit | `npm run test:unit` | **1023 passed** (89 files; RI 997: + 18 RR web, + 8 viewer `climb-review.test.ts`) |
| builder | `npm run test:builder` | first part: 1063 passed, 1 failed: `test_vendor.py::test_load_imports_by_path_in_a_fresh_process`, because three `__pycache__` folders had been written into `services/builder/walkthrough_builder` at 08:48 by a reviewer's ad-hoc run (git-ignored bytecode; the test forbids it); removed, that file 18 passed alone. After the RA-18 fix, the whole suite again: **1067 passed** (+ 3 new), 9 deselected (`acceptance`), 14 min 49 s |
| seed | into `%TEMP%\wt-rr\rerun\seed` | the five stamps (`4b02dc17f286`, `c3a9408304a2`, `f1b95c53eb3d`, `e43270cc0c9b`, `6ab030750886`) |
| API | `npm run test:api` | **560 passed**, 1 skipped (the real-worker one) |
| API, real worker | `WT_INTEGRATION=1 npm run test:api` | first part: 56 failed with `path_too_long` (the run's store `%TEMP%\wt-rr\rerun\api-int` made project paths of 261 - 263 characters; the store refuses them, as it should); again under `%TEMP%\wt-ai`: **561 passed** |
| API description | `npm run gen:api` twice | no change to `openapi.json` or the generated client |
| additive | `check-openapi-additive.mjs`, bases 66b4c06 and 9eb2d58 | ok, ok |
| build | `npm run build` | ok |
| acceptance (old cases) | `run.mjs` `acceptance`, `acceptance-a12`, `checks` | every old stamp as on 9 Nov (the bank both ways `c3a9408304a2`, CSV `b528bb2320ef`; the new suite `1d90d91ef949`, `467d3f8444c0`); `suite-revit` needs the office of `acceptance-a12`, as in RI |
| new-rule builds | `rooms-builds` (7 cases and RA-13) | ok; stamps bank `54ef1ac240bb`, house `d90ccc3c6e5d`, old suite `ed7774c64b9b`, tower `9f95de8a365c`, new suite `424cc8cabd45`, tower set aside `0cb0a89452b8`, new suite set aside `ed76d1441480`; RA-13 every fix matched. After the RA-18 fix, built again in a fresh store (`%TEMP%\wt-rb`): every stamp the same |
| walks in Edge | `rooms-offline`, `rooms-walks` | upload-walk 49 passed, stairs 57 passed (GPU 60 fps) |
| Node climbs | `rooms-node` | 9 passed, the climbs' traces equal RI's; run again alone at 12:59: a move on a stair 55 / 54 / 93 µs (bank / house / tower; RI 42 / 42 / 52), the first view at most 27 / 43 / 117 ms; slower than RI's night-time run on the bank and the tower, far inside RA-14's 2 ms and 0.35 s |
| two processes, RA-18 | `rooms-golden` | first part: 20 passed, 1 failed (RA-18 on the bank's L1-018: the regression of section 3, BRK-1); after the fix: **21 passed** (the five pins unchanged) |
| figures | `rooms-checks` | `rooms-result.json`: GAPS.md section 9 |
| references | `reference-checks` | `versions.sha1` unchanged, `outside.txt` 0 differences, no new `__pycache__` outside `app/` |
| prototypes | `proto-tests` | 10 of 11 passed (bank 49, suite, house openings, house furniture, hotel, boxes, Max scripts 137 / 151 / hotel, detector 54 / 54); view modes 126 of 127 under load ("Walk slides along a wall when you walk into it at an angle", slid 0.18 m; a timed check, as RI saw); alone: **127 of 127** |
| browser | `npm run test:e2e` (RI-C's set-up) | **393 passed, 0 failed**, 3 skipped (the layout checks of `rr-web.spec.ts`, mock API only), 43.5 min; after the RA-18 fix `rooms.spec.ts` and `upload.spec.ts` with the real worker again: **6 passed** (11.3 min); `rr-web.spec.ts` under the mock API: **3 passed**. In all, **396 browser checks pass** |
