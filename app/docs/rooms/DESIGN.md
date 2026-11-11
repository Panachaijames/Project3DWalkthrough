# Rooms and slabs, then stairs you can climb: milestone design (10 Nov 2026; reviewed by three critics and revised on 11 Nov 2026)

The design of the milestone the owner chose on 10 Nov ("rooms & slabs + climbable stairs", branch `milestone-rooms`).
Builders work from this file (sections cited **R-n**), `ACCEPTANCE.md` (what "done" means, criteria **RA-n**, and the
tests) and `WORK_BREAKDOWN.md` (who owns which files, hours). Everything of the foundation's `../DESIGN.md` (cited
**D-n**) and of the upload milestone's `../upload/DESIGN.md` (cited **U-n**) still holds where this file does not change
it. Paths are relative to `app/` unless they start with a project folder (`bank_test/`, `detector/` ...). Line numbers
are at commit `de650bb`; no code under `services/`, `packages/` or `apps/` has changed since `66b4c06`, which stays the
base of the contract checks.

**Reviewed on 10 – 11 Nov** by three independent critics (geometry: 14 findings; the owner's path and the screens: 15;
testability and integration: 21). Every finding and how it was settled is in *Review notes* at the end. Two facts
arrived after the first version and are built in:
* **The door finder was scored on the fifth drawing** (`presidential suite_layout.dwg`, the 3D team's Revit export) as a
  drawing it had never seen: **7 of its 16 doorways right** (`detector/blind_run_suite_revit/README.md`). The held-out
  run is over, so this design cites that drawing's openings (the answer key's ids `SR-nn`,
  `detector/keys/suite_revit/`). The door finder itself is **not** changed in this milestone (R-13, R-18 decision 18).
* **`npm run dev` no longer reloads the API when code changes** (`../upload/contract-issues/UI.md`, UI-5): after an API
  change the app is stopped with Ctrl+C and started again. No step of this milestone relies on a reload
  (WORK_BREAKDOWN 0).

---

## For the owner, in plain words

**What clients will see.**
* **Every room has a floor**, including the places that had none:
  * the house's glass-walled living room and the small east building;
  * the middle of both presidential suites (the 3D team's new one once its layer 0 is set to wall, as on 9 Nov);
  * the outer offices of the tower, between the lift core and the glass facade.

  A doorway that could not be walked through because the floor behind it was missing now can. A doorway that the
  drawing closes with a wall line is a different matter: see *Doors* below.
* **Rooms have ceilings when you walk through them.** In Orbit the building stays open from above, as now. Double-height
  spaces (the house's living room, the stair halls) stay open up to the floor above.
* **Stairs are real steps with landings.** In Walk you climb them by walking:
  * the view rises step by step and you arrive on the next floor;
  * walking down takes you back;
  * you cannot fall off the side of a stair or into a stair well, and you cannot walk into the side of the steps.

  The floor buttons and PgUp / PgDn still jump between floors.
* **Which stairs climb on the test drawings.**
  * The house's main stair and the bank's main stair climb. They are the test this milestone must pass.
  * The tower's stair A climbs if its storey really is about 4.00 m (the drawings do not give the tower's levels, so
    the app assumes them).
  * These stay as lines, each with a note that says why: the house's service stair and the short stair in its living
    room, the flight that goes on up from the bank's top floor, the tower's west stair, and perhaps the bank's north
    stair. Curved and spiral stairs are for later.
* **Old versions look and walk exactly as before.** That covers the bank's two versions, the hotel, the suite and the
  house as they are saved today.

**How you will see it.** Nothing changes on the project list by itself: the four projects there keep their saved
versions. Upload a project's DWG again (**New version**) and that new version has the new floors, ceilings and stairs.
Open it and press Walk.

**What changes for staff in the app.**
* **Floors step.**
  * Each floor gets a **ceiling height**. Leave it empty for 3.00 m, or less when the storey is low.
  * **Every new version is built the new way**, also for a project that was uploaded before this milestone. Saved
    versions never change. One line on the Floors, Build and Check steps says which way a draft is built, with one
    button to go back to the earlier way (kept for comparison, in a fold called **Earlier build rules**).
* **Build and Save steps** show three new counts: rooms closed, names placed, stairs you can climb.
* **Check step.**
  * The plan shows the rooms (outlined, with the area when you point at one), the floor plate with its holes, and each
    stair with its walking line. Three ticks switch the rooms, the floor plate and the furniture on and off.
  * Short dashed lines show where the app closed a gap by itself.
  * New flags point at four things:
    * where the outside walls do not close, with the opening marked: **Close it here** (one click) or **It is
      outdoors**;
    * which room names sit in no closed room;
    * which stairs could not be made climbable, and why;
    * two floors with no stair between them that can be climbed.
  * New fixes:
    * draw a line across a gap to close a room;
    * click a room to name it, or to mark it "no floor here" (a double-height space, a courtyard), "floor here" or "no
      ceiling" (open to the sky);
    * click a stair to show which end is the bottom, to keep it as lines, or to climb it as drawn;
    * a list of the fixes on the floor, each with **Remove**.
  * **Set aside** no longer costs floor: a line that is set aside is not built, but it still closes the floor, unless
    you tick "the floor runs past it".

  Rebuild applies the fixes, and the next upload of the same drawing keeps them.

**What the 3D team gets in 3ds Max.**
* Stairs as live step objects: a shape with an Extrude (Editable Mesh when collapsed, never Editable Poly).
* Ceilings on their own layers, **hidden** when the script has run: switch them on for interior views.
* Larger slabs with their holes, and walls under a stair cut down to the stair's underside.
* "Update levels and heights" keeps the stairs whole when a level changes.
* Furniture is unchanged: Box primitives on their kind layers.

**Doors: do the designers have to mark them first? No. But the door finder is not finished.**
* On four of the five test drawings the app finds the doors on its own. Plain hinged doors drawn with their swing are
  found.
* On the 3D team's Revit export, tested on 10 Nov as a drawing the finder had never seen, it got **7 of 16 doorways
  right**. This kind of export draws the wall's lines on across the doorway, which hides pocket doors and some others.
* Its second round of fixes comes **after** this milestone (your order of 10 Nov: rooms, slabs and stairs; then the door
  finder; then the box editing).
* **What a missed doorway does under this design:**
  * *The wall is drawn across the doorway* (the pocket doors). Both rooms keep their floors and ceilings, but the wall
    stands in the doorway and Walk cannot pass. Staff set aside the lines across it on the Check step, as today; on this
    drawing 14 of the 16 doorways then come out right, and the others are open.
  * *Nothing is drawn across it, inside the building* (the folding door, the wide opening). Walk passes. The app closes
    door-sized gaps between two wall ends by itself, so the two rooms stay two rooms. Where it cannot, the two rooms
    count as one room with two names. Floors and ceilings are complete either way.
  * *Nothing is drawn across it, in an outside wall.* In the first version of this design one such door could cost a
    large part of a floor (106 m² on the bank's upper level in a trial). Now the app closes such gaps by itself, up to
    2.0 m wide, where two wall ends face each other; in a trial that kept the whole floor for every door of the bank's
    upper level. A gap it does not close gets a flag with one click to close it.
  * *A door found that is not there* can split a room in two. No floor is lost. Staff give it "Not an opening", as
    today.
* The floors were missing for three reasons that have nothing to do with doors, and this design deals with each:
  * outside walls with small gaps at their corners;
  * walls drawn only as room outlines;
  * walls drawn on layer 0.

**Not in this milestone.** These are kept for later, each with a place prepared for it (R-16):
* curved and spiral stairs, and stairs with turning steps;
* stairs that lead to a floor that is not in the model (they stay as lines);
* steps from the garden up to a raised ground floor;
* handrails built along the steps;
* adding a door by hand on the Check step (it comes with the door finder's round);
* the room's name in the Walk read-out;
* reading ceiling heights from the elevations;
* finishes per room;
* hiding the walls;
* phones and tablets (the touch Upstairs / Downstairs buttons stay as they are);
* rebuilding the hotel, which was traced by hand from two pictures, so its stair stays as it is.

**What it costs.** About **237 hours** of hands-on developer time (174 – 323), in the plan's terms (WORK_BREAKDOWN 9):
* the plan holds about 75 hours for this work, so the milestone adds about **160 hours** to the plan's totals (the first
  working version moves from about 616 to about 776 hours);
* the review raised the figure from 194 hours: the door-sized gaps, the clearer flags, the set-aside change and the
  repeatable acceptance checks are new work;
* **agent working time is a different measure.** The last milestone was estimated at about 205 hours and took about 15
  hours of agent working time. This one is forecast at 25 – 40 hours of agent working time, because more of it is new
  rules judged by measurements, not copies of proven prototypes.

The plan (section 5) and the product document's Cost table carry these hours since 11 Nov.

**What needs you: nothing.** Every value the drawings do not give has a default. Each default is listed with its
reason in R-15, so you can say if one is wrong. The ones worth knowing:
* new versions of every project use the new floors, ceilings and stairs (one button goes back);
* ceilings at 3.00 m, or 0.30 m under the wall height when that is lower;
* door-sized gaps up to 2.0 m between two wall ends are closed as doorways;
* a stair is built when its steps come out 0.14 – 0.21 m high; staff can say "climb it as drawn" up to 0.25 m;
* the tower's storey is taken as 4.00 m;
* the fenced strip in front of the house's upper living room gets no floor (it reads as a screen, not a balcony), and a
  flag asks;
* ceilings are on hidden layers in 3ds Max.

---

**In:**
* the wall network and the rooms it closes;
* room outlines when the drawing has them, closed or as single lines;
* the app's own closings: bridges over small gaps and door-sized gaps between wall ends, each shown on the Check step;
* room names placed in their rooms, and staff names;
* the floor plate as the outside outline of each floor, with holes for:
  * stair wells;
  * the openings over stairs that stay as lines (as today);
  * lift shafts and other shafts;
  * voids marked with an X;
* terraces edged by railings;
* ceilings;
* the flags and fixes for rooms that do not close, with the opening marked;
* stairs read from the drawings:
  * straight, L and U stairs with landings;
  * matched across two floors;
  * direction from words, walking-line arrows, the cut plan or staff;
* step and landing solids;
* the slab hole of the floor above, and lower-floor parts cut under a flight;
* climbing in Walk;
* the Ceilings tick;
* the 3ds Max script, the top view, the replay and the offline file for all of the above;
* BuiltModel v2;
* the API and staff-app changes, with the new rules as the default for every new version;
* acceptance checks that can be run again with one command.

**Out, with seams kept (R-16):**
* curved, spiral and winder stairs, ramps and escalators;
* stairs to floors that are not in the model;
* garden steps to a plinth floor;
* generated handrails;
* a door added by hand; any change to the door finder;
* the room's name in the Walk read-out;
* ceiling heights from elevations or reflected ceiling plans;
* a ceiling height per room;
* finishes;
* AI room naming;
* hiding walls;
* walls found by shape on a mixed layer;
* a ramp collider (not needed, R-18 decision 9);
* a v2 of the hotel.

**Never:**
* deploys, publishes or releases;
* writes outside `app/`;
* a change to a saved version.

**Reference material** (scratch, session scratchpad `...\scratchpad\rooms_design\`, can be cleared; read-only measurements,
never app code):
* `builder_map/` (the builder reader's rebuild and capture scripts);
* `viewer_walk/` (the viewer reader's walk simulations, including `climb.ts`, the climbing prototype);
* `drawings_inventory/`:
  * the converted DXFs and the builder captures;
  * the plots `png/house_g_stair.png`, `house_u_stair.png`, `bank1_stair.png`, `bank2_stair.png` and `ov_l29.png`;
  * the scripts;
* `contracts_map/`;
* `design_step/` (the first version's slab trials): `slab_try.py`, `slab_try2.py`, `bridges.py`, `suite_outl.py`,
  `suite_terr.py`, pictures in `design_step/png/`;
* `geo_critique/` (the geometry critic's scripts, their outputs in `run2/*.txt`, plots in `png/`),
  `critique_owner_staff/`, `critique_testability/`, and `critic_findings_owner_and_tests.md`;
* `revise_step/` (this revision's two trials): `doorgap2.py` and `doorgap3.py` (the doorway closings of R-2.6),
  `x3.py` (the X marks of R-4.3).

Builders re-make what they need from the drawings, never from these folders.

Contents:
* 0 facts this rests on . 1 terms . R-1 inputs and options . R-2 the wall network . R-3 rooms . R-4 the slab
* R-5 ceilings . R-6 rooms that do not close . R-7 stairs: reading . R-8 stairs: building . R-9 the viewer
* R-10 the 3ds Max script . R-11 offline file, pictures, presentation, replay . R-12 contracts . R-13 determinism
* R-14 tests . R-15 defaults and the owner . R-16 seams . R-17 risks . R-18 decisions . review notes

---

## 0. Facts this design rests on (measured 10 – 11 Nov 2026 by four readers, the design step, the three critics and this revision; scratch copies only)

| Fact | Consequence |
|---|---|
| Rebuilt in-process from the acceptance store's caches and each version's `project-data.json`, five uploads give their saved models **byte for byte** in 2–9 s each: the bank re-upload `c3a9408304a2`, the house `1c07bfeef580`, the suite `205e9c2c46e8`, the tower `91414f408cb2` and the Revit suite `1d90d91ef949` (builder reader; the testability critic rebuilt them again, also from `WT_REF`) | old recipes stay reproducible; the new rules are developed against the same inputs (R-13) |
| Today a floor plate exists only where walls close a room (`build/bank.py:835-856`: walls, glass and every opening span, cracks under 10 cm closed, holes filled), plus strips under ~3 m wide along railings that a door reaches. Each drawing loses floor in its own way: **the house** through one 0.17 m gap between two glass pieces; **the tower** through gaps of 0.37–2.5 m where the curtain wall meets columns and single-line pieces; **the old suite** because its corridor walls exist only as `Defpoints` room outlines; **the new suite** because its partitions are on layer 0 | the network needs more than walls and spans: drawn lines, single-line parts, outline edges, bridged gaps, doorway closings and staff closing lines (R-2) |
| The trial (`design_step/bridges.py`, `slab_try2.py`; re-run faster by the geometry critic with the same rings, `geo_critique/run2/fast.txt`): walls, glass and spans **plus the single-line parts and every continuous line on a wall, column, glass, window or screen layer (2 cm wide)**, plus bridges found by a 1.0 m disc, gives these outside rings: bank L1 236 m², L2 243, house ground 466, house upper 453, tower L29 857, L30 741, old suite 416 (its outline edges in the network), new suite (layer 0 as wall) 247. With today's plate joined to it (`ring ∪ old`, measured with the app's own `plates_of`): 235.8 / 295.7 / 508.0 / 454.3 / 856.8 / 740.9 / 421.7 / 274.0 m². Today's plates are 235.3 / 295.4 / 421.6 / 423.0 / 430.9 / 536.4 / 108.6 / 170.9 m². A 1.5 m round closing of the same network, which overfills, gives an upper bound: 238 / 301 / 534 / 487 / 868 / 757 / 434 / 278 m² | the rule of R-2 / R-4 closes the house, the tower and the new suite without staff; the expected areas of ACCEPTANCE RA-4 |
| **The 1.0 m is the disc's width, not the gap it closes.** A gap in line closes up to 0.21 m between 2 cm strips, 0.44 m in a 0.10 m wall, 0.60 m in a 0.20 m wall, 0.80 m in a 0.40 m wall; a wall end facing a wall, 0.60–0.80 m (`geo_critique/run2/gapwidth2.txt`; the owner-path critic measured the same on a 10 × 10 m room, `critique_owner_staff/wide_gap2.py`). The first version's flag for a room that does not close had the same limit: with 0.20 m walls a room got its floor up to a 0.55 m opening, a flag up to 1.10 m, and from 1.15 m neither | bridges are for corner gaps, not doorways; doorways need their own rule (R-2.6) and the flag a second rule that does not depend on wall thickness (R-2.5) |
| **A missed doorway.** With each detected door taken out in turn (`geo_critique/missdoor2_log.txt`): rooms merge for 28 of 31 doors on tower L29 and 14 of 17 on bank L1; where the door is in the outside wall of a room the floor leaks: on bank L2 any one of six doors (0.68–1.88 m) costs 106 m², 36 % of the plate, two more 25.5 m² each; bank L1 10.6 m² (one door); house ground 39.1, 8.3 and 4.1 m². Today's rule loses the same floor, so `old` in the union does not help | door-sized gaps are closed explicitly (R-2.6); what still leaks is flagged with its opening (R-2.5, R-6.1) |
| **The doorway rule, tried by this revision** (`revise_step/doorgap3.py`, on the same captures, a script, not builder code): two wall ends that face each other up to 2.0 m apart always get a closing; a wall end that faces a wall's side only where the outside ring would lose 1 m² or more without it. With every detected door in place it adds 0 closings on the bank, 2 and 0 on the house, 2 and 1 on the tower, 1 on the old suite, and changes no ring and no room count. With each door taken out in turn: bank L2 loses more than 2 m² for **0 of 25** (8 before), bank L1 for 1 of 17 (the 1.60 m door `L1-018`, unchanged), house ground for 1 of 27 (3 before), house upper 0; rooms merge for 5 of 25 on bank L2 (22 before). The critic's wording ("same thickness within 5 cm") left 3 of the 8 open, because the bank's doors sit between 0.10 m and 0.20 m walls. Not run on the new suite (the trial script failed there) | R-2.6 as tried; RA-18's numbers |
| Mitre-joined closings of these networks are **not monotonic** in the radius (tower L29: 429 → 672 → 540 → 822 m² for 0.05 → 0.15 → 0.25 → 0.5 m). Round joins are monotonic, but a plain round closing also fills concave corners (hundreds of fillets per floor). The first version told a bridge from a fillet by counting contact stretches. That hangs on millimetres: on the house's upper floor one piece of 0.004 m² decides whether a 10 × 2.3 m loop closes (+26.7 m², the 453 / 482 m² difference of the two trial methods), and the loop flips with the radius: open at 0.4–0.6 m, closed at 0.65, open at 0.75, closed at 1.0 (`run2/miscA.txt`). What is sound: the ring is the same for radii 0.30–0.60 m on the tower, the house's ground floor and the new suite | no mitre closing above today's 10 cm crack rule; a bridge is decided by what it separates, not by counting stretches (R-2.2) |
| A bridge of the first version was a whole piece of the closing, not a line: 11.0 m² on the new suite, 13 m² on tower L29, taken out of the rooms. Bridges also hop over small free-standing pieces: without the pieces under 0.1 m² the house's rings fall from 466 to 458 and from 453 to 438 m² (all 16 bridges of the ground floor and 26 of the 28 upstairs use them); on the tower the stepping stones are columns (`run2/islands.txt`) | a bridge is a 2 cm strip; free-standing specks take no part (R-2.2) |
| The slow part of the bridge rule is the closing of the raw network (10.7 s on the new suite: 32,727 vertices, 1,594 small holes). On a copy with the holes too small for the disc filled, simplified by 1 cm, the whole rule takes under 0.5 s a floor and gives the same ring and faces on the four floors tried (`run2/time3.txt`, `fast.txt`) | the recipe of R-2.2; RA-14's budget |
| Furniture and symbols on a wall layer become "rooms": on the new suite the bed is a 7.5 m² face (98 % single-line parts), a round table 1.7 m², the sofa corner 10.0 m² (cut off by bridges between armchairs); on the house's ground floor a 7.5 m² face is 47 % loose lines and 30 % bridges (`run2/facebound.txt`) | a face is a room only when half its edge is structure (R-3.1) |
| The old suite: 10 closed `Defpoints` outlines (334 m²) hold 13 of its 16 labels; 5 labels fall inside the one 153 m² outline, and labels sit beside their rooms. Every name carries its area in its own text ("Bar 7,6m2") and the model's `area` is null for all 16. The `KT-Lancan` balustrade encloses 69–93 m² more of terrace (the two trial methods differ). Tower L29 has six single lines of 1.7–4.0 m on a room-outline layer and no closed outline: Revit's room separation lines | outlines join the network, closed or open (R-2.4); trailing areas with comma decimals parsed |
| Placing names "by written area first" takes names out of the rooms they stand in (`run2/names.txt`): the bank's `TOILET 3.2` goes to the 3.1 m² room next door, `FEMALE TOILET 6.4` (standing in a 3.3 m² face: the cubicles split the room) goes to the F/C room, and 8 of the old suite's 15 labels with an area are moved. Revit's room tags sit inside their rooms by definition. Open-plan rooms carry several names on purpose: the bank's 112 m² hall holds `CSO 5PAX`, `WAITING AREA` and `FOR 1 PAX` | containment first, area second and one-to-one (R-3.2); every drawn name keeps its own label (R-3.4) |
| A ceiling built up from the room faces with a 0.30 m closing leaves holes over everything wider than 0.6 m and over cells under 1 m²: 6 holes on the new suite (33.7 m² of 247 with no ceiling), 9 on tower L29, 22 separate pieces on the house's upper floor (`run2/miscC.txt`) | the ceiling is cut from the plate's outline, top down (R-5.2) |
| Every drawing draws its doors (door blocks and/or arcs on door layers); the detector found 39 doors on the bank, 32 on the house, 44 on the tower and 15 on the old suite. **On the fifth drawing, held out on 10 Nov, 7 of 16 doorways were right:** wall lines drawn across the opening hide the four 1.10 m pocket doors and the two unit doors cut by the view's crop; the 2.23 m bi-fold and the 1.98 m doorless opening are missed; 8 passages were reported that are not there. With the 15 crossing lines set aside on the Check step, 14 of 16 come out right (`../STATUS.md`, 11 Nov) | nothing for the designers to mark; what a missed doorway does is designed for (R-2.6, R-6); the detector is not changed here (R-13) |
| Staff are told to set aside single lines that are not walls and the lines across a missed doorway. In the first version a set-aside line left the network too: on tower L30 one single-line part about 1.10 m long closes 43 m² (the room behind door `L30-033`), so setting it aside took that floor away again (`critique_owner_staff/singles_which.py`) | a set-aside line still bounds the floor (R-2.1 point 7, R-6.2) |
| Today every stair drawn on an upper floor cuts a stair void in that floor's plate (`bank.py:896-907`): 3.93 m² over the house's service stair, 17.24 m² over the tower's west stair on L30 (`critique_owner_staff/stair_floor.py`) | a stair that stays as lines keeps today's opening (R-4.3) |
| The house's main stair is an **L**: 7 + 14 = 21 risers, 0.30 m going, 3.90 / 21 = 0.186 m (checked on `house_g_stair.png` and `house_u_stair.png` by this revision). Lower flight: riser lines at y 21.15, 21.55, 21.85 … 23.05; the bottom step is flared and 0.40 m deep; the line at 23.05 is the landing's edge. Upper flight: 6 risers on `STAIR` up to a break line (x 21.05 … 22.55), 8 on `TREE` in a hidden linetype (x 22.85 … 24.95). The upper plan shows the top 9 risers on `STAIR`, within 0.02 m after the 74.022 m shift. A walking line with a dot and an arrowhead is drawn on both floors; there is no word. Today it gives 0 steps and `TREE` is not read | the gate stair; a deeper first step; lines on any layer that continue a flight's rhythm; direction from the walking line (R-7) |
| The bank's main stair is a square spiral of four flights, 4 + 5 + 3 + 9 = 21 risers, 3.70 / 21 = 0.176 m (the split checked on `bank1_stair.png`). On Level 1: 4 nosing pairs at the east, 5 risers at the north (one cut in two by the zig-zag break line, three on the beyond-the-cut layer `S-STRS-MBND`), 3 at the west. Flight 4 (with `DOWN` and an arrow) is on Level 2, beside the `UP` flight of the next stair: two parallel 9-riser flights at the same offsets, 0.76 m apart. Level 1's last line (x 2.53) is Level 2's first riser. Flight 4 passes over the Level 1 toilet and over flight 1. Today: 16 two-riser blocks hang from Level 2, 8 of them down to −1.41 m, and the walker is stopped by an L1 wall standing under the flight | a stair is matched across two floors; flights of different senses are never chained (R-7.3, R-7.5); lower-floor parts under a flight are cut (R-8.3) |
| The tower's U stairs put both flights' risers (25 mm nosing pairs) in one lane, and `bank.py:733-736` throws the chain away when the common span turns negative: 0 flights on both floors. Stair A has 10 + 10 risers (0.200 m at the assumed 4.00 m storey; any storey of 2.80–4.20 m fits); stair B 8 + 8 (+1) on L30 and 10 + 8 on L29's own drawing, 0.235–0.25 m | a riser-height check (R-7.5); the level assumption is shown in the gap report |
| Run as written on the real stair layers, the first version's flight rules (`geo_critique/g2_flights.py`, `run2/flights.txt`) gave widths of 0.45 m for 1.3 m risers (the break line shortens some risers and "the common span" collapses), a phantom third flight on tower L30, and counts of 19 and 20 where the drawings show 21: riser pieces cut by the break line fell out, and risers skipped under the one-missing allowance were not counted. Each wrong count still lay inside 0.14–0.21 m | riser pieces are joined first; the width is the median; a skipped riser is counted; the counts are pinned per flight (R-7.1, R-7.2, R-7.7) |
| Steps today are `step` parts two risers deep, built only for flights with an UP / DN word. They are ordinary colliders, so the hotel's 16 F1 steps stop today's walker 1.3 m into the flight (`F1 step:own`). Bank v2 and the hotel carry `step` parts | climbing comes only with new data, never from `step` (R-9.1) |
| A walker measured from the feet, with a 0.25 m step-up and the steps taken out of the body rays, climbs the hotel's flight on the real scene in Node (`viewer_walk/climb.ts`). Without a gap bridge it sticks at 2.729 m on a sliver before F2's slab edge; with a bridge of 3 cm or more it reaches F2 at 2.900 m and comes back down to 0 (`geo_critique/run2/climb_gap_*.txt`). **With the walls beside the flight taken out, the same walker crosses steps 2 and 3 from the side with its feet on the floor** (0.34 and 0.51 m below the step tops): the ground ray started inside the step (`geo_critique/side.ts`) | step solids with a step-up, no ramp collider; the ground ray starts above the walker's knees (R-9.2); the gap bridge and the tread overlap (R-8.2) |
| Walk costs per move: the structure 26–39 µs; with the furniture boxes 0.2–0.9 ms; with both floors' boxes, as on a stair, up to 1.2 ms (tower) | inside a 33 ms frame; a box proxy stays optional (R-9.9) |
| X marks. Read as "any two crossing lines", the rule cut real floor: the bank's grid lines made one 270 m² "void" on Level 2, a rectangle with a divider on the old suite became a shaft, wall lines crossing `TREE` lines a 9.7 m² void on the house, and the tower's four shafts were missed because their X is on a layer set to `ignore`. **Read as the two diagonals of one box** (`revise_step/x3.py`, all five drawings): the bank's lift (1.96 m², both levels); the house's double-height living room (26.1 m²) and its stair hall (16.6 m², one diagonal stops at the flight, so three of its four ends are at corners); the tower's three lift-door X's (L29) and four `A-DETL` X's (both floors); nothing on either suite; nothing else. The house's 0.84 m² duct and three 0.3 m wide roof slots are too narrow to count | X marks become holes by the rule of R-4.3; RA-5's pinned holes |
| On the bank's Level 2 the rounded rectangle in the middle of the plan is the "MINI BAR / WEALTH ROOM", with walls drawn as `A-WALL` arcs | curved walls are part of the network as drawn; not a void |
| BuiltModel v1 has no version field (`version.json` says `built-model/1`, `services/api/walkthrough_api/store/base.py:41, 188`); the schema closes the top level, `floor`, `part` and `stairLines`; `rooms[]` entries are open; the part kinds are an enum | **BuiltModel v2**: optional additions, `modelFormat: built-model/2` (R-12.1) |
| Pinned byte for byte today: the bank model `c3a9408304a2` (`services/builder/tests/test_u3_bank.py:59-60`), its summary (`bank_summary.json`), CSV `b528bb2320ef`, top view `f084b556503c`, the `bank-27oct` and `hotel-2nov` Max scripts, the replay's lines, rings and sheet, and the seed's five stamps. The house, suite and tower stamps are recorded only in `../upload/GAPS.md` and `../STATUS.md` | new behaviour only through options whose missing value is the old rule (R-1, R-13) |
| `BuildSettings` is strict with every field required (`models_upload.py:118-225`). The builder merges missing options with its defaults (`build/settings.py:19-20, 60`). Three dicts named `OPTIONS` are equal today (`build/settings.py:19`, `propose.py:38`, `drafts/adopt.py:35`). `tools/check-openapi-additive.mjs` deep-compares against `9eb2d58`. A new version starts from the latest version's saved settings (`drafts/builds.py:370-391`) | new settings fields are optional with defaults; the additive check learns "an optional property was added" (R-12.5); which rules a new draft gets is decided in one place (R-1.3) |
| In `walkthrough_builder/contracts.py`, `NotRequired` does nothing at run time (`from __future__ import annotations`, `:13`; tried on the builder's Python 3.14.3), and `tests/test_contracts.py:102-110` wants every key of the design's block required | new report keys go in `total=False` subclasses (R-12.3) |
| `app/data` holds 58 files since the owner uploaded the bank's two DWGs on 10 Nov; 49 of them are under `versions/`. Outside `app/` the detector's fifth-drawing folders were added the same day | "nothing else moved" is checked against manifests of saved versions, not file counts (R-13) |
| Only the house gives ceiling heights (its elevations: 3.00 m on the ground floor, 2.90 m upstairs, as `cad_test/src/heights.json`) | a default rule, typed values for the house (R-5.1) |

---

## 1. Terms

* **Network**: per floor, everything that bounds a space in plan (R-2.1), as polygons in sheet metres after alignment.
* **Gap**: a place where two parts of the network come close without touching. A **crack** is a gap under 10 cm (closed
  as today). A **bridge** is a 2 cm strip the app adds across a gap that a 1.0 m disc cannot pass (R-2.2: up to 0.2–0.8 m
  wide, depending on the wall thickness). A **doorway closing** is a 2 cm strip the app adds across a door-sized gap
  between wall ends, up to 2.0 m (R-2.6). A **closing line** is a strip staff draw (R-6.2). None of the three builds
  anything or blocks walking.
* **Face**: a bounded area of the plan that the network closes on all sides. A **room** (in the model: a **space**) is a
  face of at least 1 m² whose edge is at least half structure (R-3.1). The model's `rooms[]` stays what it is in v1: the
  drawn room names, one label each.
* **Ring**: the outside outline of a floor's network, filled.
* **Slab** (floor plate): the ring plus terraces, minus holes. In the model it is the `slab` part, top at the floor
  level. **Plate0** is the plate before the holes are cut.
* **Hole**: an opening in a slab. A **stair well** is the hole a climbable stair passes through. A **kept stair void**
  is today's opening over a stair that stays as lines. A **shaft** is a lift or service shaft. A **void** is an opening
  of 4 m² or more marked in the drawing (a double-height space).
* **Unfloored area**: a place beside the walls that has no floor and is nearly closed; its **mouth** is the opening
  through which it is open (R-2.5).
* **Stair**: one way up from a floor to a higher floor of the same stack. A stair has:
  * **flights**: runs of parallel risers;
  * **landings**: flat parts between flights.
* **Riser line**: the drawn line of a step's front edge. A **tread** is the step between two riser lines. The **going**
  is the depth of a tread. The **rise** is the level difference of the two floors, and the **riser** height is the rise
  divided by the number of risers.
* **Sense** of a flight on one plan: it **leaves** (goes up from this plan's floor) or **arrives** (comes up to this
  plan's floor from below).
* **Walking line**: the line along the middle of the flights and landings, from the bottom to the top. Its end on the
  lower floor is the **bottom**, and its end on the upper floor is the **arrival**.
* **Foot**: the height of the walker's feet above the datum. The eye is the foot plus the eye height.
* **Old rule / new rule**: today's builder behaviour (`bank_test`'s rule 10 and the bank's stairs) / this milestone's,
  switched by the options of R-1.2. On the screens they are "the earlier way" and "as built now".

---

## R-1. Inputs and the three new options

### R-1.1 What the new rules read

| Input | From | Used for |
|---|---|---|
| walls, glass and every built part after the openings are cut (`E_walls` of `bank.py:896-897`), the detector's opening spans, the single-line parts | the build, as today | the network (R-2.1) |
| continuous lines on layers with the roles wall, column, glass, window and screen, **set-aside ones included** | the floor's per-item reading (U-9.1) | the network (R-2.1) |
| polylines and lines on `room-outline` layers, closed or open | the same | rooms and the network (R-2.4, R-3) |
| railings and parapets (built parts) and the lines on railing layers | the build | terraces (R-4.2) |
| texts on `room-name` layers | the same | names (R-3.2) |
| pairs of straight lines that are the two diagonals of one box (X marks), on every layer except furniture, grid and dimension layers; `ignore` layers are read too | the same | holes (R-4.3) |
| lines on `stair` and `stair-above` layers; lines on any other layer that continue a found flight; stair words; arrows and walking lines on any layer except ignore | the same | stairs (R-7) |
| levels, wall heights, slab thicknesses, the new ceiling heights | `settings.floors` | stairs (rise), slabs, ceilings |
| staff fixes: closing lines, room points, stair points, set-asides (R-6.2, R-7.6) | `settings.fixes` | everything above |

### R-1.2 The options (`BuildSettings.options`) and their defaults

Every new rule switches on through an option. **In a settings document a missing key means the old rule**, so every
recipe saved before this milestone, and every settings fixture of the upload milestone, still builds exactly as before
when it is handed to the builder as it is.

| Option | Missing key = old rule | New rule | What it switches |
|---|---|---|---|
| `slabs` | `'closed-rooms'` (`bank.py:835-911` as it is) | `'network'` | the network, rooms, names, slabs, holes, flags and fixes of R-2 – R-4 and R-6 |
| `ceilings` | `'off'` | `'auto'` | ceilings (R-5); needs `slabs: 'network'` |
| `stairs` | `'lines'` (`bank.py:756-799` as it is: words, two-riser blocks) | `'climb'` | R-7 and R-8; needs `slabs: 'network'` |

* **The two sets are named once**, in the contracts: `OLD_RULES = { slabs: 'closed-rooms', ceilings: 'off', stairs:
  'lines' }` and `NEW_RULES = { slabs: 'network', ceilings: 'auto', stairs: 'climb' }` (both TypeScript copies,
  `models_upload.py`, `walkthrough_builder/contracts.py`). The three `OPTIONS` dicts that are equal today
  (`build/settings.py:19`, `propose.py:38`, `drafts/adopt.py:35`) differ on purpose afterwards: the builder's fills
  `OLD_RULES` for missing keys; the proposal and `adopt` write `NEW_RULES`.
* `FloorSetup.ceilingHeight` (new, `number | null`, default null = the rule of R-5.1) is read only with
  `ceilings: 'auto'`.
* With `slabs: 'closed-rooms'` the other two must be at their old values: `settings_issues` answers 422
  `invalid_settings` ("ceilings and climbable stairs need floor plates from the wall network").
* **The screens show one choice, not three** (R-12.6): "Floor plates, ceilings and stairs: as built now / the earlier
  way", and "Ceilings: on / off". The three keys stay in the settings for the tests and the API.

### R-1.3 Which builds get the new rules

* **Every new draft gets the new rules.** `adopt()` writes `NEW_RULES` into the draft's settings when the draft starts
  from:
  * the proposal (a new project, or a new version of a project with no recipe: the four seeded ones);
  * a saved version's settings, or another build's settings, **whose file was written before this milestone**: its
    raw JSON has none of the three keys. `drafts/builds.py:378` holds the raw file before the defaults are filled in,
    and that is the one place that looks.

  So a project uploaded on 9 Nov gets its floors, ceilings and stairs with its next version, without staff opening the
  Floors step (a draft made from a saved version skips that step: its Layers step counts as reviewed,
  `builds.py:391`).
* **A recipe that carries the keys is kept as it is.** A project that staff put back to the earlier way stays there
  until they switch, and re-uploading a drawing onto a version built after this milestone reproduces it (upload A-9).
* **Saved versions never change.** The new rules reach a project only in a new version.
* **One line says which way a draft is built**, on the Floors, Build and Check steps, with one button to switch
  (R-12.6). The button sets the three options in one saved change.
* **An open draft from before this milestone** (its `settings.json` has no keys) reads as the earlier way, by the
  rule of R-1.2, and shows the line with its button. The owner's store holds no such draft today (two uploaded
  drawings, no build).
* **Request bodies and the builder** follow R-1.2: a settings document without the keys means the old rule. The API
  fills a missing key with the old value when it validates a settings document, and writes it out at the next save.
* **The acceptance fixtures** `fixtures/upload/settings/{bank,house,suite,tower,small}.json` stay as they are, with the
  old rules. New fixtures `fixtures/upload/settings/{bank,house,suite,tower,suite-revit}-rooms.json` carry the new
  rules:
  * all of them: the three options;
  * the house: also its ceiling heights 3.00 / 2.90;
  * `suite-revit-rooms`: the A-12 recipe (`suite-revit` v1) with layer 0 set to wall, where the new suite's
    partitions are, and nothing set aside (the saved A-12 recipe sets nothing aside).
* **Tests that build a new version from a pre-milestone recipe and compare bytes** write the old values first
  (ACCEPTANCE 3 lists them).

---

## R-2. The wall network (with `slabs: 'network'`)

### R-2.1 What bounds a space

The network `N` of a floor is the union of the following.

1. Today's `E_walls`:
   * walls and glass after the cut;
   * lintels, sills, window panes and transoms;
   * Revit glass-wall panes, glass screens and frame posts;
   * closures (`bank.py:896-897`).
2. Every detected opening's span: doors, windows and passages, the wall thickness + 4 cm across (`bank.py:836`, as
   today). A detected opening still closes its doorway, so rooms divide at doors. An opening that staff gave the kind
   "Not an opening" has no span (and its wall is not cut, as today).
3. **The single-line parts** (`single`, built 1.0 m high). The tower's corner gaps stand next to them.
4. **Drawn boundary lines**: every continuous line (the wall reader's linetype rule, `items.py:257`) on a layer whose
   role is wall, column, glass, window or screen, as a strip 2 cm wide.
   * This covers the curtain walls' two face lines with the mullions between them (the tower), thin facade lines that
     pair with nothing (the tower's slanted west facade), and the house's lone 1.1 m `WALL-GL` line.
   * These strips are never built and never cut anything. They only bound spaces.
   * Hidden, dashed and centre lines are left out (overhead beams, the outline of the floor above).
5. **Room outlines** (R-2.4): the edges of closed ones and the open lines, 2 cm wide.
6. **Staff closing lines** (R-6.2), 2 cm wide. Each end is extended to the nearest part of the network within 0.5 m,
   so a line that stops a little short of a thin facade line still closes.
7. **Set-aside lines.** A line that staff set aside on a wall, column, glass, window or screen layer is not built and
   is not read by the door finder, as today, but it **stays in the network** as a 2 cm strip: point 4 reads it like
   any other line. It leaves the network only when its set-aside record says `floorPast: true` ("the floor runs past
   it", R-6.2). Reason: staff set aside single lines that are not walls and the lines across a missed doorway
   (`../STATUS.md`); on tower L30 one such line closes 43 m² (§0).

Railings and parapets are **not** in `N`: they bound terraces (R-4.2), not rooms.

### R-2.2 Gaps: cracks and bridges

* **Cracks** under 10 cm are closed as today: a mitre closing of 0.05 m (`bank.py:837`). No other mitre closing is used
  (§0: mitre closings are not monotonic).
* **Bridges** are for the small gaps at corners and between a facade and a column. What they reach is set by a disc
  1.0 m wide: a gap in line closes up to **0.21 m** between two drawn lines, **0.44 m** in a 0.10 m wall, **0.60 m** in
  a 0.20 m wall and 0.80 m in a 0.40 m wall; a wall end facing a wall, 0.60–0.80 m (§0). They are not for doorways
  (R-2.6).
  1. **A working copy** `M` of the network, for the closing only:
     * free-standing specks are left out: a piece that touches nothing else and is under 0.05 m² when filled, and a
       lone drawn line shorter than 0.3 m. Built walls, columns, glass, mullions, frame posts and single-line parts of
       0.05 m² or more, and lines of 0.3 m or more, can be the ends of a bridge;
     * holes too small to hold the disc are filled;
     * the outline is simplified by 1 cm.
  2. **The round closing** `C = M.buffer(0.5, round).buffer(-0.5, round)` (8 segments a quarter circle).
  3. **Each connected piece of `C − M` is judged by what it does.** It is a bridge when it lies between two different
     open areas: the areas outside `C` that touch its edge (rooms of 1 m² or more, and the outside) are two or more.
     A piece with one open area round it is dropped: the fillet of a concave corner, the gap between a wall and a
     column standing free in a room, a slot between two walls that is open to the outside at both ends. Nothing is
     counted in millimetres.
  4. **A bridge is a straight strip**, 2 cm wide: the shortest segment between the two parts of `M` that the piece
     joins (ties: the lower midpoint by x, then y). When the piece joins more than two parts, one strip joins each
     pair of neighbouring parts, and a strip that the test of step 3 does not need is dropped again. So room corners
     stay square and no area is taken out of a room.
  5. The strips are added to `N` for the rest of R-2 – R-5, listed in the report and drawn on the Check step (dashed).
* A bridge does **not** build anything and does **not** block walking.
* **Measured** (§0), with the first version's rule (whole pieces, contact stretches): the bank needs no bridges; the
  house 16 on the ground floor and 28 upstairs, the tower 10 on L29 and 6 on L30, the new suite 13. The ring is the
  same for disc radii of 0.30–0.60 m on the tower, the house's ground floor and the new suite, so 0.5 m sits on a
  plateau. With 0.75 m the house's ground floor reaches outside the walls (497 m² against 466).
* **Not yet run as one rule:** the strips, the speck rule and the "two open areas" test. The speck rule is expected to
  cost the house about 8 m² on the ground floor (one face of loose lines) and 15 m² upstairs (the critic measured
  that with a 0.1 m² limit), and to keep the loop in front of the upper living room open (R-4.2). **R1's first task**
  runs the rule on the eight floors and records rings, rooms and strips against RA-3 and RA-4 before building on it;
  a difference from this section is a contract issue, not a silent choice.

### R-2.3 Glass partitions and curtain walls

Glass partitions are built glass parts, so they are in `E_walls`. Curtain walls are in the network three times over:
* their built glass and mullions (`E_walls`);
* their drawn face lines (R-2.1 point 4);
* the bridges at their ends.

No new pairing rule is added for the 0.5 m curtain-wall band. Its two faces bound the space either way.

### R-2.4 Room outlines (when the drawing has them)

* **A closed polyline** on a `room-outline` layer, of 1 m² or more after `buffer(0)`, is used two ways:
  * its edges join `N`, so the faces follow the designer's rooms where no wall is drawn (the old suite's corridor side);
  * its area and position help place names (R-3.2).

  A polyline whose two ends are within 0.10 m of each other counts as closed.
* **Open lines and polylines** on those layers join `N` as 2 cm strips too. They are the designer's own room
  boundaries where no wall is drawn: Revit's room separation lines (six of 1.7–4.0 m on tower L29).

The upload's `outlineWalls: 'suggest'` option (U-10.5) is unchanged and independent: it **builds** walls along free
outline edges when staff accept them. This rule only uses the outlines to bound spaces.

### R-2.5 What the network gives

**The order**, per floor:
1. `N` (R-2.1), cracks closed;
2. the doorway closings (R-2.6);
3. the bridges (R-2.2);
4. minus the app's closings that staff removed (R-6.2); the result is `N'`.

**From `N'`:**
* **Faces**: the holes of `close_mitre(N', 0.05)` of 1 m² or more.
* **The ring**: the filled outside outlines of the same geometry, each piece whose **filled** area is over 4 m².
  (Today's `inner`, `bank.py:838`, tests the area of the walls themselves; a detached 5 × 6 m building with 0.10 m
  walls has 2.16 m² of wall and would get no floor.) A detached piece of under 12 m² counts only when an opening span
  or a doorway closing lies on it: a pavilion has a door, a planter or a parked car drawn on a wall layer has none.
* **Unfloored areas**, found after plate0 is known (R-4.1). Two rules, pieces of 4 m² or more with standing room (a
  0.8 m disc):
  * **beside a gap**: the parts of a 1.5 m round closing of `N'` plus railings, closed outlines filled, that are not in
    plate0. This finds areas under 3 m across;
  * **pockets**: take the space with no floor (a frame 5 m round the floor, minus plate0, minus `N'`), shrink it by
    1.5 m and grow it back by 1.5 m. What comes back is open outside. What does not come back is a pocket: its way out
    is under 3 m wide, whatever the wall thickness. (The owner-path critic's trial, `critique_owner_staff/pockets.py`,
    flags every opening from 0.8 to 2.9 m in 0.1 and 0.2 m walls; on the captured floors it finds one more area, the
    house's 61 m² court between its wings.)
* **The mouth** of an unfloored area is the stretch of its edge that is neither network nor plate. When it is one
  stretch of 3 m or less, its two ends go into the flag (R-6.1).
* **Walls that never close**: when plate0 is under half of the walls' convex hull and 100 m² or more short of it
  (today's fallback, `out/overlay.py:300-306`), the floor gets one flag for the whole floor. It stays with the new
  rule.
* An area that staff answered ("It is outdoors", R-6.2) is not reported again.

### R-2.6 Doorway closings (door-sized gaps that have no door)

A doorway the door finder missed, with nothing drawn across it, is a gap of 0.7–2 m between two wall ends. No bridge
reaches it (R-2.2). In the outside wall of a room it lets the whole floor leak (§0). So door-sized gaps are closed
explicitly, whatever the wall thickness.

* **A wall end** is a short edge (0.04–0.5 m: the wall's thickness) of a built wall or glass piece, with wall behind it
  for 0.3 m and nothing of the network in the 0.10 m in front of it.
* **End to end.** Two wall ends that face each other (opposite within 5°), 0.10–2.0 m apart, the thinner lying at least
  60 % in front of the other, with nothing of the network between them, get a 2 cm strip straight across from the
  thinner end's middle. The thicknesses may differ: the bank's doors sit between 0.10 m and 0.20 m walls.
* **End to face.** A wall end that squarely faces any other part of the network 0.10–2.0 m ahead (a wall's side, a
  column) is a candidate. It is kept only where the outside ring would lose 1 m² or more without it, each candidate
  tested alone against all the others. Reason: taken always, this case adds 6 and 11 closings on the bank's two levels
  with every door found and splits rooms (15 faces become 16, 14 become 18); taken only where the floor needs it, it
  adds none.
* **2.0 m** covers the bank's widest door (1.88 m). The new suite's 1.98 m doorless opening ends at a corner and its
  2.23 m bi-fold is wider: those two rooms merge (R-3.2) and no floor is lost, since both are inside the building.
* **What a doorway closing does.** It bounds spaces, like a bridge: it builds nothing and blocks nothing, so Walk
  passes. It is handed to today's plate rule and to the terrace rule as a passage span, so "a door reaches it" tests
  see it. It counts as structure for the room test (R-3.1).
* **Shown and answerable.** Each one is in the report and the overlay, drawn dashed on the Check step, with a `doorway`
  flag (info): "A gap of 1.20 m between two wall ends was closed as a doorway: no door was found here." Staff can
  remove it ("Not a doorway: one room", R-6.2). This is also the first sign on the screen that a door is missing
  there.
* **Tried** (§0, `revise_step/doorgap3.py`): no closing on the bank with every door found, 0–2 per floor elsewhere,
  no ring or room count changed; with each door taken out in turn the bank's Level 2 loses floor for 0 of 25 doors
  (8 before). The thresholds above are the trial's; R1's first task repeats it in builder code (RA-18).
* **A wall drawn across a doorway** is not a gap, so nothing here opens it: the rooms close, both have floor, and the
  wall stands in the doorway until staff set aside the lines across it. The door finder then usually finds the door;
  where it still does not, the set-aside lines keep the two rooms apart (R-2.1 point 7) and the doorway is open.

---

## R-3. Rooms

### R-3.1 Which faces are rooms

* **A face is a room (a space)** when it is 1 m² or more and **at least half of its edge** runs along structure: built
  parts (`E_walls`), opening spans, doorway closings, outline edges or staff lines. Single-line parts, loose drawn
  lines and bridges do not count toward the half.
* **A face that fails the test is an enclosed shape**: a bed, a table, a sofa corner drawn on a wall layer. It is joined
  to the room across its longest stretch of edge that is not structure, and the report counts it ("3 enclosed shapes
  left out as furniture"). The floor is not affected: the ring is the outside outline.
* **A free-standing group of lines** (a piece of the network that touches nothing else) of under 12 m² with no opening
  span or doorway closing on it is an object: its faces are not rooms.
* **Ids**: `<floor key>-R<nnn>`, numbered by the room's label point:
  * rows from the top of the plan (y falling, 0.5 m rows);
  * left to right within a row (x rising).

  The label point is the room's pole of inaccessibility (shapely's `polylabel`, tolerance 0.05 m); a point within 0.3 m
  of a wall moves to the room's representative point. It is used for the ids, the overlay and staff fixes, not for the
  drawn names.

### R-3.2 Names

* **Which texts are names.** Texts on `room-name` layers, as today (`bank.py:815-832`), with three changes.
  1. **Short names are kept.** A text is a name when it has 2 or more letters, is not a stair word (the vocabulary's
     `stairUp` / `stairDown`), and is not a tag. A tag has 3 letters or fewer and at least one digit: `D1`, `W12`,
     `ST-05`, `R-01`. So `BAR`, `BOH.`, `WC` and `F/C` are names. The old rule's 4-letter limit (`bank.py:826`) stays
     only with the old rule.
  2. **An area written in the name** ("Bar 7,6m2", "Master Bedroom: 47m2") is split off. The name keeps the words before
     it (trailing `:` removed), and the area is read with a comma or a point as the decimal mark. The separate tag line
     below a name (Revit's "12 m²", "Not Enclosed") is paired as today.
  3. The written area stays in the `label` as written (as today: "Bar · 7,6m2"), so what the designer wrote still
     shows.
* **Which room a name belongs to**, the first rule that applies:
  1. **Where it stands**, when the name has no written area, or when the room it stands in fits the written area
     (within 15 %, or 0.5 m²).
  2. **By written area**, for a name that stands in no room or in a room that does not fit: among the rooms within
     3.0 m of its insertion point in which no name stands by rule 1 and whose area fits (15 %, or 0.5 m²). These are
     placed **one-to-one for the whole floor**: the pair with the smallest area error first, then the nearest. This
     places the old suite's labels that sit beside their rooms.
  3. **Where it stands**, even though the area does not fit (the bank's `FEMALE TOILET 6.4` in its 3.3 m² face).
  4. **By distance**: the nearest room within 1.5 m.
  5. Else the name belongs to no room and is flagged `room-open` (R-6.1).
* **Several names in one room** are all kept, each at its own point (R-3.4). The room lists them. The room's own name,
  for the report, the overlay and later for finishes, is the staff name (R-3.3), else the name whose written area fits
  the room, else the first in reading order. A `room-names` flag (info) says: "3 names in one room: an open-plan room,
  or a wall between them is missing."
* **Room names on the wrong layer**: the upload's `room-label` flag (`out/overlay.py:331-366`) stays. It now also looks
  outside the slab, since names can now fall on floors that had none.

### R-3.3 Staff names

A room fix (R-6.2) with a name names the room that contains its point. It becomes the room's own name; the drawing's
names in that room keep their labels. In a room with no drawn name, the staff name also becomes a label at the room's
label point.

### R-3.4 What the model and the sidecars carry

* **`rooms[]` keeps its v1 meaning: one record per drawn name, at the point where the designer wrote it.** `name`,
  `label`, `x` and `y` are made as today (with the three changes of R-3.2). `area` is the written area, else the
  room's area when the name is alone in its room, else null. New, optional: `space` (the id of the room it belongs to;
  absent when it belongs to none). A staff name for an unnamed room adds one record.
  * So the viewer's labels, the Max text objects, the top view's texts and the version's room count read `rooms[]`
    exactly as they do today: the bank's new-rule version shows its 18 labels where the drawing has them, and counts
    18 rooms.
* **`spaces[]` is new (R-12.1): one record per room**, named or not: `id`, `floor`, `o` and `h` (outline and holes,
  model frame), `area` (0.1 m²), `name` (the room's own name, `''` when it has none), `names` (every drawn name in it),
  `source` (`'network' | 'outline' | 'staff'`), `ceiling` (false when marked "no ceiling").
* **The overlay** (R-12.4): the spaces with their ids, names and areas.
* **The report**: per floor the spaces, the named ones, the enclosed shapes left out, the names in no room, the rooms
  with several names.
* **The diff** compares names as today and adds the number of spaces, the plate area and the climbable stairs per floor.

---

## R-4. The slab

### R-4.1 The ring and the plate

Per floor, with `slabs: 'network'`:

```
ring      = filled outside outlines of close_mitre(N', 0.05), pieces of over 4 m2 filled area   (R-2.5)
terraces  = R-4.2
old       = today's plate (plates_of, bank.py:835-856: closed rooms and the kept strips), with the doorway
            closings handed to it as passage spans
staff     = areas marked "floor here" (R-6.2)
plate0    = (ring | terraces | old | staff-floor) - areas marked "no floor here"       # plate_of, pass 1 (R-12.3)
slab      = plate0 - holes (R-4.3), then finished (R-4.4)                              # cut_slab, pass 3
```

* **Plate0 is never smaller than today's plate.** `old` is in the union. A test checks it on the five drawings: the area
  of today's plate outside the new one is under 0.5 m² per floor.
* **That is not the test of the milestone**, since it holds by construction. The floors this milestone exists for have
  lower bounds of their own, measured against the trial (ACCEPTANCE RA-4), and probe points that must lie on the plate
  (RA-6).
* **Over-filling is bounded by the network.** Only areas enclosed by drawn structure are added.
* **Courtyards and atriums** enclosed by the network (none in the test drawings) would be floored. Staff mark them "no
  floor here" (R-6.2).
* A room of over 150 m² with no opening span or doorway closing on its edge is flagged `room-open`: "closed area with
  no door: is it floor?"

### R-4.2 Terraces and balconies

Two sources:
1. **Today's kept strips** (`old` above): strips under ~3 m wide along railings and parapets, with standing room, reached
   by a door and not mostly stair. These keep the bank's 52.7 m² Level 2 strip.
2. **Enclosed terraces**: the faces of `N'` plus railings and parapets (railing lines as 2 cm strips) that lie outside
   the ring, have standing room (a 0.8 m disc), and have a door span, a passage span or a doorway closing within 5 cm
   of them. The same crack, doorway and bridge rules close this larger network; here free-standing specks do take part,
   because a balustrade drawn as posts is a railing. The old suite's terrace inside its `KT-Lancan` balustrade is one
   (69–93 m² in the trial's two methods; R1's first task measures it with this rule and it is pinned within 3 m²).

* Terraces get a floor but no ceiling (R-5.2).
* **A fenced area with no door found** gets no floor. It is listed in the report ("no door or passage opens onto it",
  as today's dropped strips) and, at 4 m² or more, flagged as an unfloored area (R-6.1), where staff answer "Floor here"
  or "It is outdoors".
* **The house's upper floor has one**: a 10 × 2.3 m loop in front of the living room (x 21.5–31.9, y 11.6–14.3 on the
  sheet), drawn as 171 small pieces on `WALL` with gaps of 4–45 cm. It reads as a screen of fins in front of the
  double-height glass, no door opens onto it, and the ground floor below it is the terrace strip outside the living
  room. **Default: no floor**, and a flag asks (R-15).

### R-4.3 Holes

Holes are cut, in this order, from plate0 of each floor:

| Hole | Rule | On the lowest floor of the stack |
|---|---|---|
| **stair well** | for each climbable stair that rises through or to this floor: the stair's footprint where it needs headroom, and the band fenced by handrails (R-8.2) | none (no stair from below) |
| **kept stair void** | for a stair group drawn on this floor in which no climbable stair arrives: today's rule (`bank.py:899-901`), the hull of its stair lines inside the plate, less walls and glass. In a group where a climbable stair arrives, the other flights that stay as lines (the next stair up) cut the hull of their own risers. Never the arrival of a climbable stair (the 1.2 m past its top riser) | none (as today) |
| **shaft (lift)** | today's rule (`bank.py:859-870`): a cell of 12 m² or less touching a lift door and no other opening | yes (cut on every floor: the lowest floor of a model is not always the bottom of the building, e.g. the tower's L29) |
| **X mark** | the rule below | shafts yes; voids are not cut there and are flagged (info) |
| **staff "no floor here"** | the room or the unfloored area of the room fix (R-6.2) | yes |

**An X mark is the two diagonals of one closed shape**:
* two straight lines, each 1.0 m or longer, their lengths within 15 % of each other;
* crossing at 30°–150°, in the middle half of both (25–75 % along each);
* their four ends mark a rectangle: four ends at its corners, or three at its corners and the fourth on one of its
  sides (the house's stair hall, where one diagonal stops at the flight). Tolerance: 0.15 m, or 10 % of the
  rectangle's longer side;
* the rectangle's outline is drawn: at least 60 % of it runs along the network or along drawn lines (any layer except
  furniture, grid and dimension layers) within 0.15 m;
* the rectangle is 0.6 m wide or more, and is not 80 % covered by wall or column parts (a column symbol);
* the lines may be on any layer except furniture, grid and dimension layers. Layers set to `ignore` are read: an X is
  an annotation, and the tower's shafts carry theirs on `A-DETL`.

**The hole is that rectangle**, not the hull of the four ends: 4 m² and more is a `void`, 1.0–4 m² a `shaft`, under
1.0 m² is reported and not cut.
* **Two X marks are never joined into a larger shape.** Holes that overlap or touch are cut as one hole, their union
  (the tower's lift-door X and the `A-DETL` X of the same lift; an X shaft and the lift-door cell).
* **Never cut automatically**: a hole of over 60 m², or of over 30 % of plate0. It gets a `hole-skipped` flag (check:
  "An X marks N m² as a void: is it one?"), and staff mark it "no floor here" if it is.
* **Tried** on the five drawings (§0, `revise_step/x3.py`; a script on bounding boxes, without the drawn-outline
  test): exactly the holes of ACCEPTANCE RA-5 and nothing else. The bank's grid, the old suite's rectangle with a
  divider and the house's wall lines crossing `TREE` lines are not X marks by this rule. R1's first task runs the
  whole rule and settles the tolerances against RA-5.

**Also:**
* **Holes of 0.5 m² or more are cut.** Smaller ones are reported, not cut (as today, `bank.py:908`).
* **Each hole is a `voids[floor]` record** (`what`: `stair`, `lift shaft`, `void`, `shaft`, `no floor`), as today.
* **The house's upper plate** gets two X-marked holes: the double-height living room (26.1 m²) and the stair hall
  (16.6 m², which holds the main stair's well). Its service stair keeps today's void (3.9 m²). The 0.84 m² duct and the
  roof slots are reported, not cut.
* **On the tower**, L29 and L30 each get four shafts. L30 also gets the stair well of stair A where headroom needs it,
  so the floor-level landings at the east stay floor, and today's void over stair B (17 m²), which is not climbable.
* **Slab-edge lines** (`A-FLOR`, `FLOOR`) are not used: none of them is closed in any test drawing (seam, R-16).

### R-4.4 Finishing

As today (`bank.py:908-911`, `model.py:23, 45-70, 89-104`):
1. simplify by 2 cm;
2. grow by `SLAB_EDGE` 0.03 m;
3. cut the holes again;
4. keep the pieces over 4 m²;
5. `clean()`;
6. `max_safe` (a hole touching the outline or another hole cuts the part in two for 3ds Max).

**Pieces of 4 m² or less are no longer lost silently**: each one goes into the report's `slab.dropped` (`why`: "under 4
m2"). Today they disappear without a word (builder reader).

The plinth (U-9.5), the slab thickness per floor and `slabThickness` in the model are unchanged.

### R-4.5 The offset of a new project

`options.offset: 'auto'` is still the centre of the slabs (`model.py:81-83`), so a new project built with the new rule
sits at a slightly different centre than it would have before. Projects with a pinned offset (U-9.6) keep their frame.
Nothing else moves.

---

## R-5. Ceilings (with `ceilings: 'auto'`)

### R-5.1 Height

* **Per floor**, `FloorSetup.ceilingHeight` (m above the floor level). It is typed on the Floors step and in the Check
  step's Heights panel.
* **Empty means the default**: `min(3.00, wallHeight − 0.30)`, and never above the underside of the floor above less
  2 cm (`next level − level − next slabThickness − 0.02`). With the test projects' settings that gives:

| Project | Floor | Default | Typed in the `*-rooms` fixtures |
|---|---|---|---|
| bank | L1, L2 | 3.00 | – |
| house | ground, upper | 3.00, 3.00 | 3.00, 2.90 (the elevations, `cad_test/src/heights.json`) |
| tower | L29, L30 | 3.00 | – |
| old suite | suite | 2.70 | – |
| new suite | L1 | 2.70 | – |

* **Reason**: 3.00 m is the house's measured ground-floor ceiling and a common suspended-ceiling height. The 0.30 m
  plenum keeps the ceiling under the next slab in low storeys. Reading the elevations' ceiling lines is left for later
  (R-16).

### R-5.2 Shape

The ceiling is cut from the top down, out of the plate's outline. One `ceiling` part per connected piece of:

```
the filled outline of (ring | areas marked "floor here")          # this floor's own holes filled: a void is open
                                                                  # from the floor below up to this ceiling
- terraces and kept strips (R-4.2)
- rooms marked "no ceiling"
- this floor's own shafts (lift, X shafts)
- the holes of the floor above (stair wells, kept stair voids, voids, shafts, "no floor" areas)
- the stair-headroom region of every climbable stair rising from this floor: its treads and landings whose top is
  higher than ceilingHeight - 2.10 m
```

* **No closing is used**, so nothing is left out by a radius: walls and columns pass through the ceiling, which hides
  the plate where it runs through them. Pieces under 0.5 m² are dropped.
* **Heights and labels**: `z0 = ceilingHeight − 0.02`, `z1 = ceilingHeight`, `follow: false`, label `ceiling`.
* **No ceiling** over terraces, over a room marked "no ceiling", or where the floor above has a hole (a double-height
  space is open to the upper floor's ceiling).
* **The top floor**: its ceiling is the roof seen from inside.
* **One part per piece, not per room.** Ceilings per room would overlap at passages and flicker. Finishes per room,
  later, split them by room (R-16).
* **Checked**: no hole in a ceiling over a part that is lower than the ceiling height (a single-line part, a low
  partition, furniture drawn on a wall layer, a shower cell).

### R-5.3 Shown where

* **Viewer**: in Walk and Ghost only (R-9.7). The material is single-sided, facing down, so from above, in Orbit or in
  Ghost over the roof, ceilings are not drawn.
* **The Ceilings tick** hides them.
* **Max**: `Ceilings` layers, **hidden** when the script has run (R-10).
* **Top view**: not drawn.

---

## R-6. When a room or the slab cannot be closed: flags and staff fixes

### R-6.1 Flags (in `overlay.json`, U-12.2; all kinds but the last two are new)

| Kind | When | Severity | Text (plain, drawing text as text) |
|---|---|---|---|
| `slab-gap` | an unfloored area (R-2.5) of 4 m² or more; or the walls of a floor never close | check | "About N m² beside the walls has no floor: the walls do not close here." With a mouth: `a`, `b` and the buttons **Close it here** and **It is outdoors**. Without one: "Draw a line across the gap if it is inside the building, or say it is outdoors." For the whole floor: "The floor plate is N m² of the about M m² the walls span: check the wall and glass layers on the Layers step." (`at`: the middle of the mouth, else the area's label point; `bbox`) |
| `room-open` | a name that belongs to no room (R-3.2 rule 5); a room over 150 m² with no opening on its edge | check | "Bar: its room is not closed (a gap in its walls). Close the gap or place the name." / "A closed area of N m² with no door: is it floor?" |
| `room-names` | two or more names in one room | info | "3 names in one room: an open-plan room, or a wall between them is missing." |
| `doorway` | each doorway closing (R-2.6) | info | "A gap of 1.20 m between two wall ends was closed as a doorway: no door was found here." Button: **Not a doorway: one room** |
| `stair` | a stair group that is not built climbable with `stairs: 'climb'` (R-7.6), with its reason | check when staff can act on it, else info | the texts of R-7.6 |
| `stairs-none` | two floors of a stack next to each other with no climbable stair between them | check | "No stair between L29 and L30 can be climbed." Then the stairs found, each with its reason; or "No stair lines were found: is the stair's layer set to Stair on the Layers step?" |
| `stair-clash` | lower-floor parts cut under a flight (R-8.3) | info | "N wall pieces of Level 1 under the stair were cut to the stair's underside." |
| `hole-skipped` | an X void on the lowest floor; an X shape too large to cut by itself (R-4.3) | info / check | "An X marks a void on the lowest floor: not cut." / "An X marks N m² as a void: is it one?" |
| `plate-dropped` | unchanged, with the old rule only (`out/overlay.py:255-306`); its stored text does not change | check / info | as today; the staff app adds under it: "This draft is built the earlier way. **Use the new floor plates, ceilings and stairs**" |
| `fix-unmatched` | also for the new fix kinds (R-6.3) | check | as today |

A flag that staff cannot act on is `info`: a stair to a floor that is not in the model, a stair with turning steps.

### R-6.2 The fixes on the Check step (new `settings.fixes` lists, R-12.4)

| Fix | Written as | The builder does |
|---|---|---|
| **Close a gap**: **Close it here** on a `slab-gap` flag with a mouth (one click), or the canvas tool **Draw a line** (two clicks; each end snaps to a drawn vertex within 6 px, as `pick-point` does, `plan/controller.ts:264-288`) | `fixes.closings[] { floor, a, b, use: 'line' }` (sheet m) | adds a 2 cm strip from `a` to `b` to `N`, each end extended to the network within 0.5 m (R-2.1 point 6); builds nothing |
| **Remove one of the app's closings**: **Not a doorway: one room** on a `doorway` flag, or a click on a dashed bridge with the Rooms and stairs tool | `fixes.closings[] { floor, a, b, use: 'none' }` | leaves out the app's bridge or doorway closing whose two ends lie within 0.3 m of `a` and `b` |
| **A room**: with the tool **Rooms and stairs**, click inside a room, then name it and / or set **No floor here** or **No ceiling** | `fixes.rooms[] { floor, at, name: string \| null, slab: 'auto' \| 'none' \| 'floor', ceiling: 'auto' \| 'none' }` | the room that contains `at` (R-6.3) is named, cut out of the plate (a `no floor` hole), or left out of the ceiling |
| **An area with no floor**: **It is outdoors** on a `slab-gap` flag; or with the tool, a click on a place with no room, then **Floor here** or **It is outdoors** | the same record, `slab: 'none'` or `'floor'` | `'none'`: the unfloored area that contains `at` is answered and not flagged again. `'floor'`: that area (closed across its mouth), or else the face of `N'` plus railings that contains `at`, is added to the plate |
| **A stair**: with the tool, click a stair (its outline is drawn), then **This is the bottom** (a pick on the bottom tread), **Keep as lines** or **Climb it as drawn** | `fixes.stairs[] { floor, at, bottom: Vec2 \| null, use: 'auto' \| 'lines' \| 'climb' }` | `bottom` decides the direction (R-7.4 rule 5); `lines` keeps the stair as lines; `climb` builds it although its riser is outside 0.14–0.21 m, as long as it is 0.25 m or less (R-7.6) |
| **Set aside** (existing), with the new tick **The floor runs past it** | `SetAside.floorPast?: boolean` (default false) | the line is not built and not read by the door finder; it still bounds the floor unless `floorPast` (R-2.1 point 7) |

The other existing tools stay: opening kinds and heights, outline suggestions, furniture kinds, and heights (with the
ceiling height added).

### R-6.3 Matching the fixes again

These fixes are points and lines, not item keys, so they survive a re-export with other handles.
* **A closing line** is applied as drawn, every build. A `use: 'none'` closing that matches none of the app's closings
  is unmatched (`fix-unmatched`: "the removed closing at ... is no longer there").
* **A room fix** applies to the room containing `at`; else to the unfloored area containing `at`; else to the room
  within 0.5 m; else, with `slab: 'floor'`, to the face of `N'` plus railings containing `at`; else it is unmatched
  ("the room fix at ... finds no room").
* **A stair fix** applies to the stair whose outline contains `at` or lies within 0.5 m; else it is unmatched.
* **A units change** rescales the points (`adopt.rescale`, U-7.4), as for the opening fixes.

The report gains `fixes.closings / rooms / stairs` rows `{ fix, matched }`.

### R-6.4 The staff's path through the three fixes

| Fix | What is clicked | Shown before Rebuild | Shown after Rebuild | Taken back with |
|---|---|---|---|---|
| close a gap from its flag | **Close it here** on the flag card | the line, dashed orange, marked "waiting for Rebuild" | the room filled, the flag gone, the line solid | **Remove** in *Fixes on this floor* |
| close a gap by hand | tool **Draw a line**, two clicks | the same | the same | the same |
| an area is outdoors | **It is outdoors** on the flag card | the area hatched grey, "waiting" | the flag gone, the area hatched "outdoors" | **Remove** in the list (the flag comes back) |
| name a room, no floor, no ceiling | tool **Rooms and stairs**, a click in the room, the room panel | the room outlined, the panel's values, "waiting" | the name in the room; a hatched hole; "no ceiling" in the room's hover text | the panel (set back), or **Remove** in the list |
| floor here | the tool, a click where there is no room, **Floor here** | a marker at the point, "waiting" | the area filled as floor | **Remove** in the list |
| a stair's bottom | the tool, a click on the stair, **This is the bottom**, a click on its bottom tread | an arrow at the picked end, "waiting" | the stair drawn with its walking line; the `stair` flag gone | the stair panel, or **Remove** in the list |
| keep a stair as lines / climb it as drawn | the stair panel | the choice in the panel, "waiting" | lines, or the walking line | the same |
| not a doorway | **Not a doorway: one room** on the `doorway` flag | the dashed line struck through, "waiting" | the two rooms are one | **Remove** in the list (the closing comes back) |
| the floor runs past a set-aside line | the tick in the set-aside list | the tick | the floor no longer stops at the line | untick |

* **Fixes on this floor** is a list on the Check step, beside the set-aside list (`build/CheckStep.tsx:372-375`): the
  closing lines, the removed closings, the room fixes and the stair fixes, each with **Remove**.
* **The tool Rooms and stairs** sends a click to a stair, then to one of the app's closings, then to a room, else it
  reports the point. In the existing Select tool a click still goes to a flag, an opening, then the nearest drawn item
  (`plan/controller.ts:291-301`), so items inside rooms can still be set aside.
* **A lost floor comes first**: when a Rebuild makes a floor's plate smaller by 2 m² or more, that is the first row of
  the Check step's list of what changed.

---

## R-7. Stairs: reading them (with `stairs: 'climb'`)

### R-7.1 Lines

1. **Lines on `stair` and `stair-above` layers**, every linetype. Hidden and beyond-the-cut lines are part of the stair.
2. **Nosing pairs.** Lines within 0.01–0.05 m of each other, parallel within 2°, and overlapping by 60 % or more are one
   riser line, at their middle. Revit draws each nosing as two lines: 15 mm apart on the bank, 25 mm on the tower.
3. **Pieces of one riser.** Before anything is chained, riser pieces that lie on one line (the same offset within 1 cm,
   in the same lane) are joined into one riser with their whole span. A break line cuts risers in two: the bank's
   riser at x 3.01 is half on the stair layer and half on the beyond-the-cut layer.
4. **The continuation on any layer.** After the flights are found (R-7.2), lines on any layer except furniture and
   ignore extend a flight when all of these hold:
   * parallel to its risers within 2°;
   * spaced at its going within 2 cm, counted from the last riser found;
   * overlapping its span by 60 % or more;
   * within two goings beyond its last riser.

   **Where one going is skipped, the missing riser is inserted and counted**, as `bank.py:744-747` does inside a chain
   today. This finds the house's `TREE` treads beyond the break line, all eight of them. The flight then grows, and the
   rule repeats until nothing is added.
5. **End steps.** The first or the last riser of a flight may stand 0.19–0.45 m from its neighbour and may be wider than
   the others: a deeper, flared bottom step (the house's is 0.40 m deep).
6. **Landing edges.** The line where a flight meets a landing is that flight's end riser when it stands one going from
   the next riser and covers the flight's width, even when it runs on along the landing (the house's line at y 23.05).
7. **A curved first step** (an arc, or a polyline of three or more segments, whose chord is parallel to the risers
   within 5°) counts as one riser at its chord; the tread keeps its drawn shape.
8. **Each riser line keeps its own ends.** Flared first steps and steps of unequal width keep their shape.

### R-7.2 Flights

As `bank.py:696-753` (lines of 0.5 m or more after the joining of point 3; 2° direction bands; spacing 0.19–0.37 m; at
least 3 risers), with four changes:
1. **Lanes are formed by mutual overlap.** A riser joins a lane when it overlaps 60 % of the lane's span, not only the
   lane's first line.
2. **A chain is split only where the next riser stands clear of the flight**: a gap of 0.10 m or more between its span
   and the flight's span (the tower's two flights in one lane). It is never split, and never dropped, because the
   common span shrank: a break line shortens some risers.
3. **The width is the median riser length** of the flight. The tread polygons use each riser's own ends (R-7.1
   point 8).
4. **A skipped going inserts a riser, and it is counted** (today's rule inside a chain, now also in the count).

The riser count of every flight on the test drawings is pinned (R-7.7) and tested on the reader alone, before any
solid is built.

### R-7.3 Senses, landings and turns

1. **The sense of each flight, per plan** (§1): it leaves this plan's floor, or it arrives at it. A word gives it: "UP"
   means leaves, "DOWN" means arrives (the word's place as in R-7.4 rule 1). Without a word the sense is unknown here
   and is settled across floors (R-7.5).
2. **Flights of one stair group** (lines within 0.3 m of each other, as `bank.py:764-768`) are chained into one stair
   when an end riser of one and an end riser of the next lie within 1.5 × the wider flight's width, and:
   * both have the same known sense; or
   * one or both senses are unknown, and the two flights are joined at one end only: their end risers meet at a corner
     (an L turn), or landing lines (stair-layer lines that are not risers) join them there (a U turn, a straight run),
     while their other ends stand free.
3. **A flight that arrives and a flight that leaves are never chained.** The turn between them lies on the floor
   itself: it is not a landing. The bank's Level 2 has this pair: the `DOWN` flight of the main stair and the `UP`
   flight of the next stair, side by side 0.76 m apart. Chained, they gave the main stair 28–30 risers of 0.12–0.13 m
   and the gate stair was refused.
4. **The turn decides the landing:**

| Turn | Landing |
|---|---|
| straight (same direction, in line) | the rectangle between the two risers, over the flights' width |
| L (perpendicular) | the rectangle spanning the first flight's width and the second's (the house: x 19.67–21.05, y 23.05–24.25) |
| U (opposite directions, side by side) | the area over both flights' ends and the well between them, out to the drawn landing lines, else to the edge of the stair hall's face, else as deep as the flights' median width (the tower: the half landing at the west) |
| anything else (turning steps, curves) | not chained: each flight is tried as a stair of its own, and the group is flagged "turning or curved steps" (R-7.6) |

The bank's spiral is three L turns: flights 1–3 on Level 1, flight 4 on Level 2, joined across the floors by R-7.5.

### R-7.4 Direction (which end is the bottom)

The first rule that gives an answer:
1. **A word** (the vocabulary's `stairUp` / `stairDown`) within 0.3 m across and −0.3 to 0.8 m along a flight end, as
   `bank.py:775-781`. "UP" marks the bottom on this floor's plan; "DOWN" marks the top.
2. **A walking line**: a polyline or line running along the flights' middle, within 0.3 m of the walking line, covering
   half the flights' length or more, with an arrowhead at one end (two strokes of 0.1–0.4 m meeting at it, or a solid
   triangle). The other end may carry a dot or a circle. **The end without the arrowhead is at this plan's floor.**
3. **The cut plan**: the flight's lines are continuous (below the cut) at one end and hidden, `stair-above` or beyond a
   zig-zag break line at the other. The continuous end is at this plan's floor (the bank's Level 1, the tower).
4. **The other floor**: a stair matched across floors (R-7.5) takes the direction from either floor.
5. **Staff**: the stair fix's `bottom` point (R-6.2) wins over every rule above.

Rules 2 and 3 give the end that is at this plan's floor. That end is the bottom when the stair leaves this floor and
the top when it arrives. Where no word says which: a stair on the lowest floor of its stack leaves; elsewhere the match
across floors decides (R-7.5); a stair that stays undecided is flagged "no direction found".

### R-7.5 One stair over two floors

* **Matching.** After alignment (U-9.4), the stairs of floor N and floor N+1 of one stack are one stair when either:
  * their footprints overlap by 30 % or more; or
  * a riser line of one lies within 5 cm of a riser or landing edge of the other (the bank: x 2.53).
* **What the upper plan's drawing of a matched stair is**, the first row that applies:

| The upper plan's stair | It is | What happens |
|---|---|---|
| carries a DOWN word or arrow, or its flights arrive | the top of the stair from below | its risers extend the stair (the bank's flight 4) |
| every one of its risers lies within 5 cm of a riser of the stair from below, **and the model has no floor above this one** | the same stair seen from above (the house; the tower's L30 core, drawn like L29's) | no stair of its own: its lines are removed with the stair's (R-8.4), no flag |
| the stair from below is complete, and this one carries an UP word, has risers of its own, or the model has a floor above this one (a stacked core) | another stair, leaving the upper floor | it is tried as a stair of its own (the bank's next stair up) |
| none of these | undecided | the stair from below is built from its own plan if it is complete; this one stays as lines, flagged |

  **Complete** means: the stair's own riser count gives a riser of 0.14–0.21 m for the rise to its floor.
* **Risers.** The risers of both drawings are put in order along the walking line, those within 5 cm of each other
  merged. Their number `n` gives the riser height `r = (level(to) − level(from)) / n`. This replaces `bank.py:762`.
  * House: 21 risers, 0.186 m.
  * Bank: 21 risers, 0.176 m.
  * Tower stair A: 20 risers, 0.200 m.
* **Which floor it rises to.** The floors above N in the same stack are tried in order, N+1 first. The stair rises to
  the first one on whose plate0 its arrival lies (within 0.25 m) and whose rise gives a riser of 0.14–0.21 m. So a
  split level or a mezzanine that staff add as a floor does not break the stairs that pass it.
* **Plausible risers are 0.14–0.21 m.** A stair whose count fits no floor stays as lines, flagged with the number
  (R-7.6). The tower's stair B, at 0.235–0.25 m, is one. A ramp drawn with cross lines on a stair layer is another: no
  floor gives it a plausible riser.

### R-7.6 Which stairs are built, and what the others say

A stair is built climbable (R-8) only when all of these hold:
* its direction is known;
* it joins floor N to a higher floor of the same stack (R-7.5);
* its riser height is plausible, or staff chose **Climb it as drawn** and the riser is 0.25 m or less (the walker's
  step, R-9.2);
* its bottom lies on floor N's plate0, and its arrival on the upper floor's plate0 (within 0.25 m);
* staff did not keep it as lines.

**Every other stair group stays as lines** (`stairs[floor].below / above`, as today) and gets a `stair` flag: a group
with flights, and also a group of stair lines that forms no flight. Today's two-riser `step` blocks are never made
with the new rule. The reasons and their texts:

| Reason | Text | Severity; what staff can do |
|---|---|---|
| no direction | "Stair at ...: kept as lines: which end is the bottom was not found." | check; **This is the bottom** |
| the riser does not fit | "Stair at ...: 16 steps for 3.90 m give 0.24 m each. The drawing may not show every step, or the levels may be off." When the levels were typed or assumed, it adds: "A storey of 2.80–3.57 m would fit every stair between these floors." | check; **Climb it as drawn** (up to 0.25 m), or the levels on the Floors step |
| no floor at its top | "Stair at ...: its 7 steps would rise about 1.0–1.5 m: no floor of the model is at that height." | info |
| it leaves the top floor | "Stair at ...: it leads to a floor that is not in the model." | info |
| the floors do not line up | "Stair at ...: its two floors' drawings do not line up. Line the floors up with two points on the Floors step." | check |
| off the plate | "Stair at ...: its top (or its bottom) does not stand on a floor plate." | check; close the room, or **Floor here** |
| turning or curved steps | "Stair at ...: turning or curved steps: not built yet." Also for stair lines that form no straight flight | info |
| kept by staff | "Stair at ...: kept as lines." | info |

**One flag per pair of floors that no stair joins** (`stairs-none`, R-6.1), listing the stairs found with their
reasons, so a two-floor project never ends without a word about its stairs.

### R-7.7 Expected on the test drawings

The riser counts per flight are tested on the reader alone (ACCEPTANCE RA-9). R2's first task plots each stair and
confirms them; a count that the drawing does not bear out is a contract issue before any solid is built.

| Drawing | Stair | Risers per flight, as drawn | Expected |
|---|---|---|---|
| house | main stair (L) | ground plan: 7 (the first 0.40 m deep and flared), then 14 (6 on `STAIR`, 8 on `TREE`); upper plan: the top 9 of the 14 on `STAIR`, the rest on `TREE` | climbable ground → upper: 21 risers of 0.186 m, 1 landing, bottom at about (20.40, 21.15), direction from the walking line (both floors); the upper plan's drawing is the same stair seen from above |
| house | ST-05 (7 risers inside the living room) | 7 | lines, "no floor of the model is at that height" (no floor at +2.20 m) |
| house | service stair ST-02 | 6 on the ground plan; 6 + 3 upstairs | lines, the riser does not fit (15 or 16 risers would give 0.24–0.26 m); today's void stays over it on the upper floor |
| bank | main stair (square spiral) | Level 1: 4 (east), 5 (north), 3 (west); Level 2: 9 (the `DOWN` flight) | climbable L1 → L2: 21 risers of 0.176 m, 3 landings, matched across the two files, direction from L2's word and arrow and L1's cut |
| bank | north stair (straight) | 18 riser lines | built or flagged, with the reason recorded (0.206 m if it rises the full storey; its top must lie on L2's plate) |
| bank | L2's next stair up (`UP`) | 9 | lines, "leads to a floor that is not in the model"; never chained with the main stair's flight 4 |
| tower | stair A (U) | 10 + 10 on both floors | climbable L29 → L30 with the assumed levels (should); L30's own drawing coincides with it: the same stair seen from above |
| tower | stair B (U) | L29: 10 + 8; L30: 8 + 8 (+1) | lines, the riser does not fit (0.235–0.25 m); today's void stays over it on L30 |
| suites | none | – | – |

---

## R-8. Stairs: what is built

### R-8.1 Treads and landings (new part kinds, all on the lower floor `from`, `follow: false`)

* **Treads.** Number the risers along the walking line 1..n. **Tread j** (j = 1..n−1) is the polygon between riser line
  j and riser line j+1, each line with its own ends (flares and unequal steps keep their shape). It is clipped to the
  stair group's outline buffered by 0.05 m.
  * Heights: `z1 = j × r` and `z0 = max(0, (j − 2) × r)`, two risers deep as the bank's steps, so the underside follows
    the pitch.
  * Kind `tread`, label `stair <S> tread <j>`.
* **The last tread** (j = n−1) is extended 0.05 m past riser n, under the upper floor's slab.
* **Landings.** A landing after riser k has `z1 = k × r` and `z0 = max(0, z1 − 0.15)`.
  * A 15 cm landing keeps the bank's toilet under its landing at 1.96 m clear, above the walker's 1.90 m head check
    (R-9.2).
  * Kind `landing`, label `stair <S> landing <k>`.
* **The floor-level ends** are the floors' own slabs.

### R-8.2 Meeting the floors above

* **The stair well** is cut in every floor M above `from`, up to and including `to`: the footprint of the treads and
  landings whose top is higher than `level(M) − level(from) − slabThickness(M) − 2.10 m`, rounded out to whole treads.
  * **2.10 m** is the usual building headroom, more than the viewer's 1.90 m head check, so the default walker always
    fits.
  * The well is grown by 0.05 m on every side **except the arrival side**.
  * **At the arrival the hole's edge is riser n.** Every hole of floor `to` (the well, an X hole, a kept stair void) is
    trimmed along riser n's line across the arrival, so the slab laps the last tread by 0.05 m in plan and no sliver
    is left between them (the viewer reader's stuck case, §0).
  * Where an X on the upper floor covers the stair (the house's stair hall), the X's hole is cut as well (R-4.3).
  * **The fenced band**: an area of the upper floor inside the stair group's outline that railings drawn there fence
    off (a face of the railing lines, the stair's outline and the well) is added to the well. The bank's Level 2 band
    between its down and up flights, fenced by its handrails, is one.
* **Where headroom allows**, the plate of the upper floor stays over the low treads (the bank's flight 1 and its first
  landing; the tower's lower flight). That is where a stacked core carries the next storey's flight. When that flight
  is not built, the stair hall shows a piece of floor where the building has the next flight (R-17).
* **Railings drawn on the upper floor around the well** are kept as today. Railings mostly off the plate are dropped on
  upper floors (`bank.py:913-916`).

### R-8.3 The floor below: parts in the way

A part of floor `from` (wall, column, glass, mullion, single, railing, parapet, lintel, sill) is cut when its footprint
overlaps the footprint of a tread or landing whose underside is lower than the part's top, **by at least 2 cm in depth
and 0.01 m² in area**. (Riser lines end on the wall's face, so a side wall touches the treads along the whole flight;
an overlap of millimetres cuts nothing and raises no flag.)
* the part is split along the stair's footprint;
* the piece under the stair gets `z1` = the lowest underside over it (`(j − 2) × r` of the treads above it, or the
  landing's `z0`), with `follow: false` and `fit: 'storey'` (R-9.6), so it keeps under the stair when a level changes;
* pieces whose new top would be 0.05 m or less are dropped;
* the rest of the part is unchanged.

The bank's toilet walls under flights 3 and 4 are the case (§0). Each cut is listed in the report, and a `stair-clash`
flag (info) gives the count. The collider skins follow, since they are made from the parts (`model.py:177-185`).

### R-8.4 Lines left

* **The lines that became treads** are removed from `stairs[floor].below / above` (as `bank.py:794-797` does for stepped
  flights), on the lower plan and on the upper plan's drawing of the same stair (R-7.5). Other stair lines stay.
* **`stairOutlines` and the summary's `stairs` block** (`model.py:229-232, 260-262`) keep their keys. With the new rule
  `stairOutlines` holds the outline of every stair group, built or kept, and the block's counts come from the new
  reader. R1's `model.py` writes both from R2's result (R-12.3).
* **The hotel** keeps its `step` parts, and the bank's old versions keep theirs (v1).

### R-8.5 The stairway record (`model.stairways[]`, R-12.1)

```ts
{ id: 'S1', from: 'ground', to: 'upper', kind: 'L', risers: 21, riser: 0.186, going: 0.30, width: 1.20,
  bottom: [x, y], top: [x, y], walk: [[x, y], ...], direction: 'arrow', treads: 20, landings: 1 }
```

* **Coordinates** are in the model frame. `to` is a higher floor of the same stack, usually the next.
* **`width`** is the median riser length of the narrowest flight.
* **`walk`** runs from a point 1.0 m before riser 1, on the lower floor, through the middle of each flight and landing
  (the middle of each riser's own span), to a point 1.0 m past riser n, on the upper floor. A start or end point that
  falls inside a wall, or off the plate, is moved toward the stair until it is 0.3 m clear.
* **`bottom` and `top`** are the first and last points.
* **With `slabs: 'network'` the model always has `stairways`**, an empty list when no stair climbs. Its presence is the
  one mark of a v2 model (R-12.2).
* **What reads it**: the viewer's climbing switch (R-9.1), the stair probe (ACCEPTANCE RA-10) and the replay's facts.

---

## R-9. The viewer: walking on slabs and stairs

### R-9.1 Climbing only with new data

* **The foot-based walker is on when the model has `stairways`** (the key, even with an empty list: every new-rule
  model has it, R-8.5).
* **Otherwise Walk keeps exactly today's rules**, the "constants to keep exactly" of D-13 (`../DESIGN.md:1046`): the
  foot at the floor's level, the floor test against the current floor's plates, the rays from the level.

So the bank's two versions, the hotel (whose `step` parts stay colliders), the suite, the house and every uploaded
version so far walk as before. A walk-parity golden proves it (R-13).

### R-9.2 The walker when climbing (`modes/walk.ts`, `modes/state.ts`)

* **State**: `ModesState.foot` (m above the datum); the eye is `foot + eye`.
  * Every place that sets the height today now sets the foot:
    * the per-frame pin (`modes/index.ts:156`);
    * mode entry (`:109, 118, 121`);
    * floor changes (`:75`);
    * the eye slider (`modes/input.ts:196`).
  * A teleport sets the foot to the target floor's level. A double-click or a Ghost landing sets it to the surface hit
    (R-9.5).
* **Surfaces**: the meshes of `slab`, `tread` and `landing` parts. They are listed as `FloorRecord.surfaces` (new);
  `walkables` stays the slabs only, for every existing reader.
  * Treads and landings are **not** colliders.
  * Their material is single-sided (outward faces), so a ray starting inside a block passes out of it.
* **The ground ray** goes down at the walker's next centre, **from `foot + 1.0 m`** to `foot − 0.30 m`, against the
  surfaces of every floor of the walked stack. **The first surface it meets decides:**
  * between `foot − 0.30` and `foot + 0.25`: the move is allowed and the foot becomes the hit's height;
  * higher than `foot + 0.25`: a step too high, the move is refused. This stops the walker at the side of a flight:
    with a ray that started at `foot + 0.25` it passed through steps 2 and 3 from the side (§0);
  * none: an edge, the move is refused, as at today's floor edge. Never a fall.

  Climbing from the front is unchanged: the next tread is the first surface met. Above 1.0 m the head ray takes over.
  * **Step-up** is up to 0.25 m; **step-down** is up to 0.30 m.
  * The slide along an edge (`walk.ts:154-163`) stays as it is.
* **The gap bridge**: when the centre finds no ground, the ray is tried again 0.08 m further along the move. The
  builder's 0.05 m lap of slab and last tread (R-8.2) already leaves no sliver; the bridge covers what rounding leaves.
  Measured on the hotel's steps, which have no lap: 3 cm is enough for a square approach (§0). The approach at 45° and
  at 70° to the top edge is a test (RA-10).
* **The head ray** goes up from `foot + 0.30` to `foot + eye + 0.30` (1.90 m at the default eye height) against the
  surfaces (not ceilings, not colliders); a hit refuses the move. It stops the walker under a low flight or landing. The
  same 1.90 m keeps the bank's toilet under its landing (1.96 m clear) walkable.
* **The body rays**: the 9 shoulder rays at `foot + 0.35` and `foot + 1.20` (`state.ts:20-22`, offsets unchanged). They
  run against the visible colliders of each floor whose height range `[level − slabThickness, level + wallHeight]`
  overlaps `[foot, foot + 2.0]`: one floor on a floor plate, two on a stair.
  * `clearance`, `openAhead`, `crosses` and `findFree` are measured from the foot as well.
  * `findFree` also needs ground under the spot.
* **Edges, holes and shafts**: walking into a stair well or a shaft from above stops at its edge (a drop over 0.30 m).
  Beside the last tread, which is one riser below the floor, a step down sideways is allowed, as it would be on a real
  stair with no railing. Walking off the open side of a higher tread stops: there is no railing, and no fall.
* **What must always hold** (the test of RA-10, sampled every 5 cm of any walk): the foot never rises more than 0.25 m
  nor drops more than 0.30 m; no tread, landing or slab top lies between `foot + 0.25` and `foot + 1.9` over the
  walker's centre (the walker is never inside a step); no 5 cm move crosses a collider; the floor named matches the
  foot.

### R-9.3 The floor you are on

* **The current floor** (`s.floor`) is the floor of the stack whose level is nearest the foot. It changes once the foot
  passes mid-storey by 0.20 m (hysteresis), so a landing at mid-storey does not flicker.
* **When it changes**:
  * `updateHud` runs;
  * the floor buttons follow (bus `mode`, `ui/panel.ts:50-54`);
  * the public `modechange` event fires with the new floor (`viewer.ts:113-123`).
* **The floor buttons, PgUp / PgDn and the touch Upstairs / Downstairs buttons** stay teleports (`index.ts:69-85`), as
  today.
* **Visibility**: every floor of the walked stack is shown in Walk, as today (`index.ts:65-68`).

### R-9.4 Camera

* **The eye eases** toward `foot + eye` with a 0.1 s time constant: at most 3.2 cm a frame at 60 fps, instead of a
  17 cm jump per step.
* **The physics uses the foot.** The easing is skipped on a teleport and in every probe call (R-9.8).
* **Walking speed** is unchanged on stairs.

### R-9.5 Teleports and landings

* **Ghost → Walk** lands on the highest surface under the eye − 0.30 m (any floor's plate, tread or landing of the
  stack). The floor becomes that surface's floor.
* **A double-click** on a tread or landing puts the foot on it.
* **`?floor=` and the floor buttons** put the foot at the level.
* **`findFree`** never puts the walker on a tread: it looks for room on the floor's plate, as today.

### R-9.6 Build settings (the replay card, D-5.5)

* **Treads, landings and the wall pieces cut under a stair** carry `fit: 'storey'` and their stairway's id (`stair`,
  R-12.1). When the level of the stairway's `from` or `to` floor changes, their meshes get `scale.y = S`,
  `position.y = L0 × (1 − S)`, with `S = (L(to) − L(from)) / (L0(to) − L0(from))`. That is floor `from`'s group
  transform and the `scale` rule (`core/heights.ts`), with the storey ratio instead of the wall-height ratio. A changed
  level therefore keeps the stair climbable, and the cut wall pieces stay under it.
* **Ceilings keep their height above their floor's level** (`follow: false`, the `fixed` rule), in the viewer as in
  3ds Max (R-10): one rule for both tools.
* `fitOf` (`core/build.ts:23`) stays as it is; `FitMode` and the part's `fit` gain `'storey'`.

### R-9.7 Ceilings in the viewer

* **Meshes**: one merged mesh per floor (`<key> ceilings`). `MeshStandardMaterial`, colour `#f4f3ef`, roughness 0.95,
  `FrontSide`, facing down. No edges, no BVH, not a collider.
* **The replay**: in the floor group's `late` list, so the replay shows them at the end like the slabs.
* **Visible** when the new Ceilings tick (`ToggleName` `'ceilings'`, default on, shown only when the model has ceilings)
  is on **and** the mode is Walk or Ghost.
* **Never in Orbit.** Orbit is the dollhouse view, and ceilings face down anyway.

### R-9.8 Labels, read-outs, probe

* **Room labels** are made from `rooms[]` exactly as today (`core/labels.ts`): one per drawn name, at its point.
  `spaces[]` is read by nothing in the viewer in this milestone (the Walk read-out's room name is a seam, R-16).
* **`readouts.downHit`** keeps reading colliders (the bank's and hotel's structure checks). A new `groundAt(floor, x, y)`
  reads the surfaces.
* **The probe** (`modes/probe.ts`, test hook only):
  * `probe.foot()` (new);
  * `probe.ground()` (new: the surface height under the walker, or null);
  * `probe.walk` returns the **horizontal** distance walked (the same as today on flat floors);
  * `onFloor` means ground within the window.
* **A probe call starts from where the test put the walker.** The existing helpers place the walker by writing
  `s.pos.x` and `s.pos.z` (`tests/e2e/lib/walks.ts:34, 65, 98`). So, with climbing on: when `s.pos.x / z` differ from
  where the walker last put them, `onFloor`, `clearance`, `open`, `crosses` and `walk` first put the foot back on the
  current floor's level (a teleport). Probe calls never ease the eye. Without this, a probe walk that ends two treads
  up a stair would leave a stale foot, and every later spot on that floor would answer "no floor". Old models have no
  foot and are not touched.

### R-9.9 Performance (budget, measured by the viewer reader; R-17)

* **Plates**: one mesh per slab part, as today, about 4 triangles per outline vertex. The tower's new plates are about 6k
  triangles and a 60 KB BVH, built in under 20 ms.
* **Treads and landings**: merged per floor into one mesh with a BVH. A 21-riser stair is about 250 triangles.
* **Ceilings**: one mesh per floor, no BVH.
* **Walk**: about +5 µs a move for the ground and head rays. On a stair, the body rays check two floors' furniture boxes:
  up to 1.2 ms a move on the tower, inside a 33 ms frame. The box proxy (one merged BVH mesh per floor's blocking boxes)
  is a should of the viewer package, used only if the frame time in Edge on this laptop goes over 33 ms on the tower.
* **First view**: the CPU part (parse, checks, `buildScene`) of an old version stays within 10 % of today's; the tower's
  is 0.13–0.24 s today, and its new-rule model, with larger plates and ceilings, may take at most 0.35 s (ACCEPTANCE
  RA-14).
* **The offline file**: tens of KB more per version.

### R-9.10 New constants (added to D-13 as a "Climbing" row; the existing rows do not change)

| | Value |
|---|---|
| step up / step down | 0.25 m / 0.30 m |
| ground ray | from foot + 1.0 m down to foot − 0.30 m; the first surface decides |
| gap bridge | 0.08 m along the move |
| head ray | from foot + 0.30 m up to foot + eye + 0.30 m |
| body rays | at foot + 0.35 / + 1.20 m, against the floors overlapping [foot, foot + 2.0 m] |
| floor change | nearest level, ± 0.20 m past mid-storey |
| eye easing | time constant 0.1 s; never in a probe call |
| ceilings | `#f4f3ef`, roughness 0.95, FrontSide, Walk and Ghost only |

---

## R-10. The 3ds Max script (`out/maxscript.py`; the owner's rule of 19 Oct)

* **Every new part goes through the existing part function** (`maxscript.py:210-265`): an editable spline (outline and
  holes) + **Extrude** (mesh output) + Smooth; **Collapse** gives Editable Mesh, **never Editable Poly**. Slabs with
  their holes already work this way (`#slab`, holes as splines). Furniture is untouched: Box primitives on their kind
  layers, so the furniture round trip can still tell furniture by its Box.
* **New kinds in `EXTRA_KINDS`** (`maxscript.py:58-65`), each written only when the model uses it, so the `bank-27oct`
  and `hotel-2nov` goldens cannot move:

| Kind | Layer suffix | Material |
|---|---|---|
| `tread` | `Treads` | `Tread`: `diffuse:(color 185 199 180)` (the stairs' colour, D-5.4) |
| `landing` | `Landings` | `Landing`: the same colour |
| `ceiling` | `Ceilings` | `Ceiling`: `diffuse:(color 244 243 239)` |

* **The Ceilings layers are hidden when the script has run.** The layer function makes every layer visible
  (`maxscript.py:163-168`); with ceilings on ordinary layers the top floor of every scene, and the whole of a one-floor
  suite, would open with a lid over the rooms, in the scene where the 3D team arranges furniture. So, only when the
  model has ceilings, one statement after the ceiling parts switches each `..._Ceilings` layer off, and the script's
  notes and its window say: "Ceilings are on hidden layers ..._Ceilings: switch them on for interior views."
* **The storey of a stair's parts.** After each tread, landing and cut-wall part call the script writes one statement
  that sets the user property `__PX___storey` on that object (the index of its stairway's `to` floor). It is **not**
  set inside `__PX___part`, so the part function stays byte for byte in both goldens and the mock interpreter runs the
  statement.
* **"Update levels and heights"** (`maxscript.py:298-317`). A new block placeholder, `__STOREYFIT__`, sits inside
  `__PX___updateLevels`. It is written only when the model has treads or landings, and vanishes with its line otherwise
  (`BLOCKS`, `maxscript.py:412`). Its code: for a part with `__PX___storey`, `base` and the Extrude `amount` are scaled
  by `(newLevels[up] − newLevels[fi]) / (oldLevels[up] − oldLevels[fi])` before the move, and the stored base is
  updated with it. A level change in Max therefore keeps the stair whole and the cut walls under it.
* **Ceilings** keep their height above their level (`follow: false`), as in the viewer (R-9.6).
* **The header's computed sentences** (U-11.5) count tread parts in `__STAIRTXT__` ("Stairs: 21 risers of 0.186 m")
  for the `upload` profile. The two golden profiles have no treads, so they are unchanged.
* **Room names**: text objects from `rooms[]`, as today.
* **Max safety** is checked as today:
  * no hole within 0.5 mm of an outline or of another hole;
  * the "two holes touch" refusal;
  * `max_safe` cuts in the builder.

  The new slabs, with more holes, go through the same rules.
* **The upload profile's notes** gain two conditions: `stairs` (the treads keep their storey when the levels change) and
  `ceilings` (the hidden layers).

---

## R-11. The offline file, the pictures, the presentation and the replay

* **The offline file** (D-16) is the current viewer template plus the version's stored files. The v2 data travels inside
  `model.json`, so nothing in the payload format changes. An old version's offline file walks as before (R-9.1). The
  `upload-walk` checks run on the new versions' files too (ACCEPTANCE RA-6, RA-10).
* **The top view** (`out/pictures.py`). The bank's styles and order stay, and the new kinds are slotted in:
  * `tread` as `step` (filled green, `#7cc48a`);
  * `landing` lighter (`#b8dcbc`);
  * `ceiling` is not drawn;
  * the `voids` texts already say "open: ..." and gain the new `what` values;
  * room texts come from `rooms[]`, as today.

  The bank's bytes cannot move: the old rule draws none of these.
* **The presentation** (`out/presentation.py:30-38`):
  * the legend row "Stairs" covers `step`, `tread` and `landing`;
  * no legend row for ceilings (not seen in Orbit);
  * the Ceilings tick's label is "Ceilings";
  * the `fitSlabs` camera and the plinth's ground plane come from the new, larger slabs.

  The start-view check (every slab corner in view, U-11.2) applies as before.
* **The replay** (`out/replay.py`):
  * the facts gain `rooms` (closed and named per floor), `climbable` (stairs) and `ceilings` (bool), in a `total=False`
    subclass (R-12.3);
  * the finish caption adds "N rooms closed" and "M stairs you can climb" only when they hold;
  * lines, pieces and rings are unchanged.
* **The thumbnail** is the top view, as today.

---

## R-12. Contracts

### R-12.1 BuiltModel v2 (`docs/built-model.schema.json` and its API copy; `docs/contracts.ts` and its viewer copy)

Every v1 model is a valid v2 model: v2 only adds optional things, and no v1 field changes meaning (the rule of
D-5.1).

| v2 addition | Type | Meaning |
|---|---|---|
| part kinds `tread`, `landing` | enum | a stair's step and landing solids; surfaces in the viewer (R-9.2) |
| part kind `ceiling` | enum | a ceiling plate (R-5); Walk and Ghost only; keeps its height above its floor's level |
| part `fit: 'storey'`, part `stair` | enum value; optional string | the part scales with its stairway's storey (R-9.6); `stair` is the stairway's id (treads, landings, cut wall pieces) |
| `stairways` (top level) | `Stairway[]` | R-8.5; present in every new-rule model, empty when no stair climbs; its presence marks v2 and switches the foot-based walker on |
| `spaces` (top level) | `Space[]` | the rooms with their outlines (R-3.4) |
| `rooms[].space` | optional string | the id of the room a drawn name belongs to (the `room` object is already open in the schema; v2 types the field) |
| `voids[].what` values `void`, `shaft`, `no floor` | strings | R-4.3 (already free text) |

* **Cross-reference rules** (D-5.6), added to the three checkers:
  * `stairways[].from` and `.to` name floors of one stack, with `to` above `from`;
  * a part with `stair` names a stairway, and lies on that stairway's `from` floor; every tread and landing has one;
  * stairway ids and space ids are unique; `rooms[].space` names a space of the same floor;
  * `walk` has at least 2 points.
* **The three checkers** (the schema, `packages/viewer/src/model/parse.ts`, `walkthrough_api/builtmodel.py`) change
  together, **in the scaffold step, by one owner** (R0), and agree on a new broken-model corpus case for each rule.

### R-12.2 The version number, and saved versions

* **`version.json` `modelFormat`** becomes `'built-model/1' | 'built-model/2'` (`store/base.py:188`, viewer
  `contracts.ts:300`). `create_version` writes `built-model/2` when the model has the `stairways` key, else
  `built-model/1`. That one key is the v2 mark for the builder, `create_version` and the viewer. So every old version,
  every old-rule rebuild and the bank's A-1 run stay `/1`.
* **The model itself still carries no version field** (D-5.1).
* **Saved versions never change.** `create_version` stages a whole folder and renames it
  (`store/local.py:410-440`), and nothing in this milestone writes into `versions/<n>/`. What does reach old versions
  is the **current viewer**, in the app and in each offline download; R-9.1 and the walk-parity golden keep their look
  and walk identical.

### R-12.3 The builder's internal contracts (`walkthrough_builder/contracts.py`, scaffold R0)

The seam between the network (R1) and the stairs (R2) carries the gate, and the two builders do not talk. So the calls
are typed, the plate exists before the stairs are built, and a working tracer of the whole chain is green before either
builder starts (WORK_BREAKDOWN R0).

```python
class PartGeo(TypedDict):            # one part before the model frame (today's parts_geo row, named)
    floor: str; kind: str; poly: Any; z0: float; z1: float; follow: bool; label: str; extra: dict
class FloorBuilt(TypedDict):         # one floor after openings and walls: floor_walls(), extracted by R0
    key: str; index: int; level: float; top: float; lowest: bool; items: list
    parts: list; e_walls: list; recs: list; rails: list; parapets: list; singles: list
    old_plate: Any; old_report: dict; old_stairs: dict
class Closing(TypedDict):            # a 2 cm strip added to the network
    kind: str; a: tuple; b: tuple; width: float      # kind: 'bridge' | 'doorway' | 'staff'
class Unfloored(TypedDict):
    poly: Any; area: float; at: tuple; mouth: Any; answered: bool
class SpaceGeo(TypedDict):
    id: str; poly: Any; area: float; at: tuple; source: str; name: str; names: list; ceiling: bool
class NetworkResult(TypedDict):      # R1, pass 1 (shapely geometry, sheet m, after alignment)
    N: Any; closings: list; faces: list; spaces: list; shapes: int; ring: Any
class FlightFound(TypedDict):
    risers: list; going: float; width: float; sense: str; lines: list      # sense: 'leaves' | 'arrives' | ''
class StairFound(TypedDict):         # R2, pass 1, per floor
    id: str; floor: str; flights: list; landings: list; outline: Any; hull: Any; floorEnd: Any; lines: list
class StairCut(TypedDict):
    floor: str; part: int; footprint: Any; z1: float
class StairBuilt(TypedDict):         # R2, pass 2: a climbable stair
    stairway: dict; treads: list; landings: list; wellOf: dict; headroom: Any; arrival: Any; cuts: list; linesUsed: dict
class StairLeft(TypedDict):          # R2, pass 2: a stair group kept as lines
    id: str; floor: str; why: str; text: str; severity: str; at: tuple; outline: Any; keptVoid: Any; risers: int
class StairsResult(TypedDict):
    built: list; left: list; pairs: list; fixes: list
class FloorRoomsReport(TypedDict):
    spaces: int; named: int; shapes: int; open: list; several: list
class FloorSlabReport(TypedDict):
    ring: float; terraces: float; old: float; plate: float; holes: list; unfloored: list; closings: list; dropped: list
class FloorUploadReportRooms(FloorUploadReport, total=False):   # the keys the new rule adds; absent with the old rule
    rooms: FloorRoomsReport; slab: FloorSlabReport; stairways: list; stairClash: list
class FixesReportRooms(FixesReport, total=False):
    closings: list; rooms: list; stairs: list
class ReplayFactsRooms(ReplayFacts, total=False):
    rooms: dict; climbable: int; ceilings: bool
```

```python
def prepare_floors(ctx) -> list                                        # R0: out of build(), no change in behaviour
def floor_walls(F, X) -> FloorBuilt                                    # R0: out of the loop bank.py:874-958, no change
def network_of(fb, fixes, X) -> NetworkResult                          # R1, pass 1
def plate_of(fb, net, fixes, X) -> tuple                               # R1, pass 1: (plate0, unfloored list, report)
def find_stairs(fb, net, fixes, X) -> list                             # R2, pass 1: [StairFound]
def build_stairs(floors, found, nets, plate0, fixes, X) -> StairsResult    # R2, pass 2; plate0: {floor key: geometry}
def cut_slab(fb, net, plate0, stairs, fixes, X) -> tuple               # R1, pass 3: (slab parts, voids, report)
def ceilings_of(fb, net, plate0, holes_above, headroom, X) -> list     # R1, pass 3: [PartGeo]
```

* **New report keys live in `total=False` subclasses**, which work at run time (`NotRequired` does not, §0). So the
  old-rule bank's report keeps exactly the keys of `fixtures/upload/build-result.bank.json`.
  `tests/test_contracts.py::test_typeddicts_equal_the_design` also reads the first block above (R0 extends it: classes
  declared with `(TypedDict)` have every key required; the three subclasses are checked on their optional keys).
* **The passes**, behind `slabs: 'network'`, in `build_floors` (R1 owns the branch and `build/__init__.py`):
  1. per floor: `floor_walls` (openings and walls, as today), then `network_of`, `plate_of`, `find_stairs`;
  2. across floors: `build_stairs`. It gets every floor's plate0 (to test "bottom and arrival on the plate" and to move
     `walk` ends that are off it), the lower floors' parts (the clash cuts) and the upper floors' railings (the fenced
     band), all in `FloorBuilt`;
  3. per floor: the clash cuts applied to the parts, `cut_slab` (the wells, the kept stair voids, shafts, X marks,
     staff holes), `ceilings_of`.

  With `'closed-rooms'` the loop calls the same `floor_walls` and then does exactly what it does today.
* **Who writes what in the model**: `build/model.py` (R1) writes `spaces`, `rooms[].space`, the slab and ceiling
  parts, `stairways`, the tread and landing parts, `stairOutlines` and the summary's `stairs` block, the last four
  from `StairsResult`. R2 never edits `model.py`.
* **`build/__init__.py`** passes the three new fix lists through (today `build/settings.py:90-91` drops every list but
  three, and `__init__.py:263` writes exactly three keys into `report['fixes']`).
* **The tracer.** R0's `network.py`, `stairs_read.py` and `stairs_build.py` are thin but working, not
  `NotImplementedError` stubs: the network is today's walls and spans, the stairs are one straight flight with a word.
  One end-to-end test builds a two-floor drawing with one straight stair (`tools/rooms/make-stair-dxf.py straight`)
  through `build()` with the new options and gets a v2 model with one stairway. It is green before R1 and R2 start,
  and stays green while they replace the tracer's bodies. The reference building (ACCEPTANCE 2.5) needs the real
  rules: it is R2's contract test.

### R-12.4 Settings, fixes, the overlay and flags (`docs/upload/upload-contracts.ts` and its web copy; `models_upload.py`)

Every new member is **optional in both TypeScript copies** and has a default in the API: a missing key is the old rule
or an empty list. (Written as required, the five unchanged settings fixtures and the generated types would fail
`apps/web/test/upload-fixtures.test-d.ts:44-49` and `upload-generated-types.test-d.ts:11`.)

| Shape | Change |
|---|---|
| `FloorSetup` | + `ceilingHeight?: number \| null` (API default None; 0.5–20 m in `settings_check`) |
| `BuilderOptions` | + `slabs?`, `ceilings?`, `stairs?` (R-1.2; API defaults = `OLD_RULES`); the constants `OLD_RULES` and `NEW_RULES` |
| `SetAside` | + `floorPast?: boolean` (default false; R-2.1 point 7) |
| `Fixes` | + `closings?: ClosingFix[]`, `rooms?: RoomFix[]`, `stairs?: StairFix[]` (API default `[]`; shapes in R-6.2); the cap of 5,000 "other fixes" (U-13.2) counts them too; a room name is at most 200 characters, text only |
| `OverlayFloor` | + `spaces: { id, name, names, area, o, h, ceiling, source }[]`, `holes: { what, o, h }[]`, `stairs: { id, state, why, text, outline, walk, bottom, to, risers, riser }[]`, `closings: { kind, a, b, fix? }[]` (`kind`: `staff`, `bridge`, `doorway`), `unfloored: { area, o, mouth, answered }[]` (sheet m; all optional, absent with the old rule) |
| `FlagKind` | + `slab-gap`, `room-open`, `room-names`, `doorway`, `stair`, `stairs-none`, `stair-clash`, `hole-skipped`; `FlagRef` + `room?: string`, `stair?: string`, `a?: Vec2`, `b?: Vec2` |
| `PartKind` (the upload copy, `models_upload.py:52`) | + `tread`, `landing`, `ceiling` |
| the build result's floor report | the optional keys of R-12.3 (`rooms`, `slab`, `stairways`, `stairClash`), read by the Build and Save steps' counts |

The overlay and the flags are raw files, not in OpenAPI (U-13.2). The settings are in OpenAPI (R-12.5).

### R-12.5 API

* **Routes are unchanged.** Their component schemas grow, all optional:
  * `FloorSetup.ceilingHeight`;
  * the three `BuilderOptions` keys;
  * `SetAside.floorPast`;
  * the three `Fixes` lists and their item schemas `ClosingFix`, `RoomFix`, `StairFix`.

  `openapi.json` and the generated client are regenerated once by the scaffold. On the API's FastAPI 0.150 and pydantic
  2.14, fields with defaults do not split the schemas into `-Input` and `-Output` (the testability critic tried it on
  a small copy; R0 confirms it on the real models in its first hour).
* **`tools/check-openapi-additive.mjs`** gets `--base 66b4c06` as the default for this milestone. It also learns one
  more additive case: **an existing component schema may gain a property that is not required.** All its other
  properties, its `required` list and every operation must stay deep-equal. For the generated client, an interface or
  type may gain optional members, and every other member's text must stay identical. The rule is tested on a hand-made
  pair: a required property added, and a property's type changed, must both fail.
* **The API's code changes:**
  * `settings_check` (the combinations of R-1.2, ceiling heights, fix counts, name lengths);
  * `drafts/builds.py` and `adopt` (R-1.3: `NEW_RULES` for the proposal and for a recipe whose raw file has no keys;
    a recipe with keys kept);
  * `adopt.rescale` (the new fixes' points);
  * `create_version` (`modelFormat` from the `stairways` key);
  * `check_file` (the new overlay fields).

  The version's counts are unchanged: `rooms[]` still means drawn names.
* **`builtmodel.py`** takes the v2 schema and rules (written by R0, R-12.1).

### R-12.6 The staff app (`apps/web`)

* **One line on the Floors, Build and Check steps** says which way the draft is built:
  * "Floor plates, ceilings and stairs are built the new way.", or
  * "This draft is built the earlier way: only rooms the walls close get a floor, and stairs stay lines. **Use the new
    floor plates, ceilings and stairs**".

  It is shown from the draft's options, so it needs no date and no word "recipe". The pre-build checklist
  (`build/steps.ts:79-118`) gets the same sentence as a warning line when the draft is built the earlier way.
* **Floors step** (`build/FloorsStep.tsx`):
  * per floor, "Ceiling height", placeholder = the default (R-5.1);
  * a fold **Earlier build rules**, closed by default, with two controls:
    * "Floor plates, ceilings and stairs: as built now / the earlier way" (sets the three options together);
    * "Ceilings: on / off" (only with "as built now").
* **Build step and Save step**: the counts per floor gain "rooms closed", "names placed" and "stairs you can climb",
  from the build result (R-12.4).
* **Check step** (`build/CheckStep.tsx`):
  * three ticks above the plan: **Rooms**, **Floor plate**, **Furniture**;
  * the rooms outlined and tinted, each with its area in the hover text; the plate's outline with its holes hatched;
    the stairs with their walking line and an arrow at the bottom; the app's closings as short dashed lines; unfloored
    areas hatched orange with their mouth dashed;
  * the counts in the page (rooms, holes, stairs), so a test can read them;
  * the flag texts and buttons of R-6.1 (`FlagList.tsx`'s `Record<FlagKind, string>` forces one text per kind);
  * the tools **Draw a line** and **Rooms and stairs**; the room panel, the stair panel, the list **Fixes on this
    floor** and the "waiting for Rebuild" marks of R-6.4;
  * the tick "The floor runs past it" in the set-aside list;
  * the ceiling height in the Heights panel;
  * a lost floor as the first row of the list of changes (R-6.4).
* **The plan canvas** (`apps/web/src/plan/index.ts:46-65`, the scaffold's signatures):
  * `tool` gains `'draw-line'` and `'rooms'`;
  * new callbacks `onLine?(a, b)`, `onSpace?(id)`, `onStair?(id)`, `onClosing?(index)`, `onPoint?(pt)`;
  * `show?: { rooms, plate, furniture }`;
  * `pick-point` is reused for the bottom tread;
  * a test hook `window.__plan` (only with `VITE_WTV_TEST_HOOK`): `toPage(sheetPoint)`, `spaces()`, `stairs()`, so a
    spec can turn a sheet point into a click.
* **Test ids** live in one module, `apps/web/src/build/testids.ts`, written by R0 and imported by the components and by
  the specs.
* **`build/settingsEdit.ts`** gains `addClosing`, `removeClosing`, `setRoomFix`, `setStairFix`, `setFloorPast`,
  `setRules`; ceiling heights go through the existing `updateFloor`.
* **The mock API** gains overlay fixtures with rooms and stairs.
* **The draft preview** (U-14.4) needs nothing new: the viewer reads v2.

### R-12.7 The change table (applied by the scaffold R0 in one step, then frozen again; a defect goes in the finder's own `docs/rooms/contract-issues/R<n>.md`)

| Frozen item | Change |
|---|---|
| `docs/built-model.schema.json`, `services/api/walkthrough_api/schema/built-model.schema.json` | v2 (R-12.1), `$id` `.../built-model-2.json`, title "BuiltModel v2" |
| `docs/contracts.ts`, `packages/viewer/src/contracts.ts` | `PartKind` + 3; `Stairway`; `Space`; `Room.space?`; `Part.stair?`; `BuiltModel.stairways?`, `.spaces?`; `FitMode` + `'storey'`; `ToggleName` + `'ceilings'`; `FloorRecord.surfaces`; `ModesState.foot`; `ModesProbe.foot / ground` and the rule of R-9.8; `ReadoutsApi.groundAt`; `VersionMeta.modelFormat` |
| `packages/viewer/src/model/parse.ts`, `services/api/walkthrough_api/builtmodel.py` | the v2 cross rules (R-12.1), written by R0 with the schema |
| `docs/upload/upload-contracts.ts`, `apps/web/src/upload/contracts.ts` | R-12.4, every new member optional |
| `services/api/walkthrough_api/models_upload.py` | R-12.4 (pydantic) |
| `services/api/walkthrough_api/store/base.py` | `model_format` Literal + `'built-model/2'` |
| `services/builder/walkthrough_builder/contracts.py` | R-12.3 |
| `services/builder/walkthrough_builder/build/bank.py`, `build/__init__.py` | `floor_walls` and `prepare_floors` extracted with no change in behaviour (the five old stamps guard it) |
| `apps/web/openapi.json`, `apps/web/src/api/generated/**` | regenerated (`npm run gen:api`) |
| `apps/web/src/plan/index.ts`, `apps/web/src/build/testids.ts` | R-12.6 signatures, the test hook, the test ids |
| files that list every kind, toggle or flag | a placeholder entry each, so the workspace type-checks and its exact-set tests pass: `apps/web/src/build/FlagList.tsx:10`, `apps/web/src/plan/colours.ts:57`, `packages/viewer/src/model/styles.ts:9`, `model/presentation.ts:52, 64`, `core/build.ts:127`, `apps/web/test/fake-viewer.ts:263`, `packages/viewer/test/harness/context.ts:192, 359`, and the objects that implement `ModesState`, `ModesProbe` and `ReadoutsApi` (WORK_BREAKDOWN R0 lists the tests) |
| `tools/check-openapi-additive.mjs` | R-12.5 |
| `fixtures/` | R-1.3 settings; the reference building and everything derived from it (ACCEPTANCE 2.5); the broken-model cases; the answer keys |
| pinned counts in tests | the API's schema list; `test_openapi.py` component count; the flag-kind lists; the toggle and part-kind sets |

---

## R-13. Determinism: what stays byte for byte, what may change, how it is checked

| Must stay byte for byte | How it is checked |
|---|---|
| the bank built with `fixtures/upload/settings/bank.json` (no new keys): model `c3a9408304a2`, summary = `bank_summary.json`, CSV `b528bb2320ef`, top view `f084b556503c`, replay lines, rings and sheet | `test_u3_bank.py`, unchanged; plus the same build from the settings with the three options **written out at their old values** (`test_r_old_rule.py`) |
| the `bank-27oct` and `hotel-2nov` Max scripts | `test_u4_maxscript.py`, unchanged |
| **every output file** of the five old-rule builds (the bank, and the house, suite, tower and Revit suite built from their saved versions' recipes, copied by R0 into `fixtures/upload/settings/recipes/`): `model.json` (the stamps `c3a9408304a2`, `1c07bfeef580`, `205e9c2c46e8`, `91414f408cb2`, `1d90d91ef949`), stages, overlay, flags, diff, top view, Max script (fixed date) | `test_r_old_rule.py`, **written by R0 from the unchanged code and green before any builder starts**. The sha1 of each file is in one fixture. R1 and R3 change the code it guards and may not edit it. With `WT_INTEGRATION=1` a missing reference fails; it does not skip |
| `npm run seed`: the five stamps | a seed into a temp folder gives the committed `app/data` version files (compared with `git show`) |
| every saved version on disk | `docs/rooms/reference/versions.sha1`, recorded by R0: the sha1 of the 49 files under `app/data/projects/*/versions/`. Every listed file is unchanged at the end. New files are allowed (the owner uses the app: two drawings were uploaded on 10 Nov); uploads and drafts in the store are not counted and never touched. The same for the upload acceptance store's eight versions |
| how old versions look and walk | **the walk-parity golden**, recorded by R0 **before any viewer change**. Models: the six model files that `fixtures/models` holds today (`bank-v1`, `bank-v2`, `hotel`, `house`, `mini`, `suite`; five are byte-identical to the seeded versions), their sha1 inside the golden. It drives only the frozen `ModesApi` and the probe, never the walker's internals: the existing wall, door and glass recipes plus floor edges, with the `clearance`, `open` and `findFree` results; key-driven walks through `tick(now)` with a made-up clock (the frame path); PgUp, a double-click, Ghost → Walk, one eye-height change; the walk into the hotel's F1 flight, which old `step` parts must still block. The recorder refuses to run unless `git diff 66b4c06 -- packages/viewer/src` is empty and writes that tree's hash into the golden; the test pins the golden's own sha1. The new viewer must give the same within 1e-9 m. At integration, `upload-walk` runs again on the eight old uploaded versions with the new template and is compared probe by probe with the reports of 9 Nov |
| the door finder | not changed in this milestone: `services/builder/tests/test_vendor.py` pins the vendored detector. Its second fix round is the next milestone (the owner's order of 10 Nov). It will bring the new detector in as a build option of its own and re-record the `-rooms` references in one commit |
| the prototypes and the drawings | `docs/rooms/reference/outside.txt`, a listing R0 takes at its start (without `detector/blind_run_suite_revit/`, `detector/keys/suite_revit/`, `.claude/` and the documents the main session edits): no listed file changes |

**Allowed to change, on purpose:**
* the models built with the new rule: the bank, house, suite, tower and new suite with the `*-rooms` fixtures, and every
  new draft;
* their offsets when `'auto'`;
* their top views, Max scripts (the upload profile's stair sentence), replays and presentations (camera, ground plane);
* `upload.spec.ts` (A-7): it reads the draft's options (the new values, from the proposal), switches the fold's choice
  to "the earlier way" on the Floors step, reads the options again (the old values), then builds. It merges only
  layers, floors and furniture from its fixture into the settings the draft already has, so the fixture can no longer
  turn the options old behind the screens' back;
* every test that builds a new version from a pre-milestone recipe and compares bytes: it writes the old values first
  (ACCEPTANCE 3);
* the new owner's-path spec, which builds with the defaults (R-14).

**New references.** RI pins them in `services/builder/tests/test_r_rooms_golden.py` as soon as its acceptance runs pass,
as provisional: the five new-rule models' sha1s, their summaries' room, slab and stair rows, the bank's new-rule CSV.
Every move of a pinned value during the review is explained in `contract-issues/RR.md`; after the review they are
final, and a later change is a decision recorded in `docs/rooms/GAPS.md`.
* **Built twice means in two processes**: each of the five drawings is built in two child processes with different
  `PYTHONHASHSEED` values (`kit.python_child`) and must give the same bytes. One process cannot see ordering by string
  hashes, the one cause already met in this code (`tools/upload/make-test-dxf.py:25, 171-172`).
* **The new suite's reference rests on the door finder's output** (R-2.1 point 2 divides rooms at detected openings),
  which is known to miss 9 doorways and add 8 there. It is expected to move with the door finder's round.

---

## R-14. Tests (the detail and the owners are in ACCEPTANCE 2 and WORK_BREAKDOWN)

* **Builder** (pytest; the `heavy` and `worker` markers of U-3.5).
  * The network on synthetic plans:
    * a corner gap bridged, a corner fillet and a free column not;
    * a slot between two walls not bridged;
    * a chain of specks left open; in-line gaps of 0.3 / 0.6 / 0.9 m at thicknesses 0.02 / 0.10 / 0.20 m;
    * a lone glass line; a curtain-wall band; an outline edge; an open outline line; a closing line stopping 0.4 m
      short of a thin line;
    * a set-aside line, with and without "the floor runs past it".
  * The same ring at disc radii 0.4 and 0.6 on the house's ground floor, the tower and the new suite (heavy).
  * Doorway closings: end to end with unequal thicknesses; end to face only where the ring needs it; openings of 0.8,
    1.6 and 2.9 m in 0.1 and 0.2 m outside walls give floor or a flag with its mouth; each door of the bank and the
    house undone in turn (heavy, RA-18).
  * A detached 3 × 4 m room with 0.10 m walls gets its floor (its walls are 1.4 m², its outline 12 m²); a detached
    2 × 3 m shape with no door on it does not; with a door it does.
  * Rooms: the half-structure test (a bed, a table, a sofa corner are not rooms); ids.
  * Names: where it stands, written area one-to-one, distance, several names, short names, "Bar 7,6m2", `ST-05`
    dropped; the three floors' answer keys (heavy).
  * Terraces; the fenced area with no door.
  * X marks: four corners; three corners and a side; narrow shapes; a column X; a void on the lowest floor; a shape over
    60 m²; and three that must not cut: the bank's grid, the old suite's rectangle with a divider, the house's wall
    lines crossing `TREE` lines (heavy).
  * Holes and Max safety; the kept stair voids.
  * Plate0 ⊇ today's plate, and the lower bounds, on the five drawings (heavy).
  * Ceilings (default rule, typed, double height, headroom, no hole over a low part).
  * Stairs:
    * riser pieces joined; nosing pairs; lanes by mutual overlap; no phantom flight; the width as the median;
    * a skipped riser counted; the continuation on another layer; a deeper first step; a landing edge as a riser;
    * **the riser count of every flight of the house, the bank and the tower** (heavy), on the reader alone;
    * senses: a `DOWN` flight and an `UP` flight side by side are two stairs (synthetic; the bank's Level 2, heavy);
    * L, U and straight landings; the U landing's depth;
    * direction by word, by arrow, by cut, by the other floor, by staff;
    * matching across two floors and the four rows of R-7.5 (synthetic; the bank and the house, heavy);
    * the riser check; the floor a stair rises to (a split level in the stack); "climb it as drawn";
    * treads and landings (heights, the lap at the top); the well (headroom, not grown at the arrival, trimmed at
      riser n); the clash cuts and their minimum overlap; the stairway record;
    * every stair group built or flagged; the flag per pair of floors.
  * The reference building: built from its DXFs, the treads, landings, well and stairway equal the model fixture within
    1 mm (the contract test that ties the builder's stairs to the walker's fixtures).
  * Old-rule byte identity, every output (R-13).
  * Determinism in two processes (R-13).
  * Fixes matched, rescaled and unmatched.
  * Outputs:
    * Max: kinds, the Ceilings layers hidden, the storey statement after each part call, `__STOREYFIT__` in the mock
      interpreter with real Extrude amounts, no `convertToPoly`, `Edit_Poly` or `editable_poly` anywhere;
    * top view styles; the legend; the replay facts and captions;
    * the overlay records against `check_file`; the new flags; the diff.
* **API**:
  * old settings files without the new keys validate and come back with the old values;
  * which rules a new draft gets (R-1.3), with the real worker;
  * the new fields' ranges; the illegal combinations get 422;
  * rescale of the new fixes;
  * `modelFormat` `/1` against `/2`;
  * the OpenAPI additive check with its new rule (and its two failing cases);
  * the strict integration run with the real builder.
* **Viewer** (vitest, Node):
  * the parser on v2 and on the broken corpus;
  * `buildScene` with surfaces, ceilings and FrontSide treads;
  * the walker on the reference building and on synthetic straight, L and U stairs:
    * up and down; the approach at 45° and 70° to the top edge;
    * into the side of treads 1–6 from both sides (stopped, or onto tread 1 only);
    * the invariants of R-9.2 on scripted and seeded random walks;
    * the gap bridge; the head ray under a low flight; body rays against two floors;
    * floor naming with hysteresis; the easing with a made-up clock;
    * a probe call after a climb (R-9.8);
  * Build settings: storey scaling of treads and cut walls; ceilings fixed;
  * the walk-parity golden;
  * the probe's horizontal distance.
* **Web** (vitest): the line and its button on three steps; the fold; ceiling heights; the Check step's tools writing
  the right fixes; the fixes list and Remove; the flag texts and buttons; the ticks; the counts; the mock overlay; the
  canvas's tools and snapping.
* **Browser** (Playwright, Edge, the Edge lock):
  * `tests/e2e/stairs.spec.ts`, the climb of ACCEPTANCE RA-10 and the ceilings' visibility per mode;
  * `upload-walk.spec.ts` on the new-rule versions;
  * `rooms.spec.ts`, the owner's path of RA-12;
  * `plan-canvas.spec.ts`, pixel probes on the Check plan;
  * `upload.spec.ts` with the fold's choice (R-13).

---

## R-15. Defaults chosen, with their reasons, and what needs the owner

| Default | Value | Reason |
|---|---|---|
| which builds get the new rules | every new draft; a recipe that carries the keys is kept (R-1.3) | the owner chose this milestone to get floors: a project uploaded before it should get them with its next version; nothing saved changes; one button goes back |
| the network's drawn lines | continuous lines of wall, column, glass, window and screen layers, 2 cm | they close the tower and the house in the trial (§0); hidden lines are overhead or below |
| a set-aside line | still bounds the floor, unless "the floor runs past it" | setting a line aside must not take a floor away (tower L30: 43 m²) |
| bridges | a 1.0 m disc, which closes gaps of 0.2–0.8 m depending on the wall thickness; a bridge is what separates two open areas; a 2 cm strip; specks under 0.05 m² take no part | closes L30 (a 0.5 m disc leaves 147 m² open); the ring is stable for discs of 0.6–1.2 m; a strip takes no area from rooms; specks made a loop of fins into a room |
| doorway closings | wall ends facing each other, up to 2.0 m; a wall end facing a wall only where the floor needs it | one missed door cost 106 m² on the bank; 2.0 m covers its widest door (1.88 m); tried: no closing where every door is found |
| cracks | 10 cm (today's) | unchanged |
| rooms | faces of 1 m² or more whose edge is at least half structure | today's hole threshold; beds and tables on a wall layer are not rooms |
| ring pieces | over 4 m² filled; a detached piece under 12 m² needs a door | today's limit, measured on the outline, not on the walls |
| names | 2 letters, not a stair word, not a tag (3 letters or fewer with a digit) | keeps BAR, BOH, WC; drops D1, ST-05, R-01 |
| name placement | where the name stands; by written area (15 %, 3 m, one-to-one) when it stands in no room or in one that does not fit; then 1.5 m | Revit's tags stand in their rooms; the old suite's labels sit beside theirs |
| several names in one room | all kept, each at its own point | open-plan rooms carry several names on purpose |
| terraces | standing room 0.8 m and a door within 5 cm | today's strip rule, extended to enclosed terraces |
| a fenced area with no door (the house's upper loop) | no floor, a flag asks | it reads as a screen in front of the glass; no door opens onto it; the ground below is outdoors |
| unfloored areas | flagged from 4 m²; a way out under 3 m wide | today's `UNFLOORED_PIECE`; independent of wall thickness |
| X marks | the two diagonals of one drawn rectangle (three corners are enough); 1 m² and up a shaft, 4 m² and up a void; over 60 m² or 30 % of the floor asked, not cut | tried on the five drawings: the expected holes and nothing else |
| voids on the lowest floor | not cut, flagged | there is nothing below to see |
| shafts on the lowest floor | cut | the lowest floor of a model may be mid-building (L29) |
| a stair that stays as lines | keeps today's opening in the floor above | nothing that is right today gets worse |
| ceiling height | min(3.00, wall height − 0.30), under the next slab | the house's measured ground-floor ceiling; a 0.30 m plenum |
| ceiling headroom over a stair | 2.10 m | building headroom |
| ceilings when heights change | keep their height above the floor's level | one rule for the viewer and 3ds Max |
| plausible risers | 0.14–0.21 m; "climb it as drawn" up to 0.25 m | covers the house (0.186), bank (0.176), tower A (0.200); refuses tower B (0.235–0.25) unless staff say so; 0.25 m is the walker's step |
| the floor a stair rises to | the first floor above whose rise fits and on whose plate it arrives | a split level in the stack does not break the stairs that pass it |
| the first step of a flight | may be 0.19–0.45 m deep | the house's is 0.40 m |
| tread depth | two risers (as the bank's steps) | the underside follows the pitch |
| landing thickness | 0.15 m | keeps the bank's toilet under its landing walkable (1.96 m) |
| slab over the last tread | 0.05 m lap | the sliver measured on the hotel |
| stair well | headroom 2.10 m over the treads; the X when drawn; the band fenced by handrails | keeps floor over low treads in stacked cores; drawn openings and handrails win |
| step up / down | 0.25 / 0.30 m | the viewer reader's prototype; one riser up to 0.21 m fits |
| ground check | from 1.0 m above the feet; the first surface decides | stops the walker at the side of the steps |
| head check | eye + 0.30 m (1.90 m) | stops under low flights, lets the bank's toilet (1.96 m) be walked |
| eye easing | 0.1 s | 3.2 cm a frame at 60 fps |
| floor naming | nearest level, ± 0.20 m hysteresis | no flicker on a mid-storey landing |
| Ceilings tick | on; Walk and Ghost only | ceilings are what a client expects inside; Orbit is the dollhouse |
| ceilings in 3ds Max | on layers of their own, hidden after Build | a lid over the rooms would be in the way of arranging furniture |
| ceilings per floor piece | one part per connected piece | no flicker at passages; per room later |

**What needs the owner: nothing.** The tower's levels (0.00 / 4.00 m) stay the upload milestone's assumption; its stair
A climbs only under it (a should), and the gap report shows which storey heights would fit its stairs. The house's
ceiling heights come from its elevations. Everything else is a default of this table, and the owner can overrule any
of them.

---

## R-16. Seams kept for later

| Later | Seam here |
|---|---|
| curved, spiral and winder stairs; ramps (the house's R-01); escalators | `Stairway.kind: 'other'`; the flights' own riser ends; the "turning or curved steps" reason keeps them as lines with a flag |
| stairs to a floor not in the model | `stair` flag reasons; `Stairway.from / to` |
| steps from the garden up to a plinth floor (the house's ST-05, if that is what it is) | the plinth slab and `StairFix` (a later `to: 'ground'`) |
| handrails along flights | the flights' open sides are known (R-7.3) |
| **a door added by hand** on the Check step | a doorway closing's `a` and `b` give its place; `ClosingFix.use` can gain `'door'` with the door finder's round |
| **the new door finder as a build option** (the next milestone) | the additive rule of R-12.5 lets it add its option key the same way; none is reserved here |
| **the room's name in the Walk read-out** (plan 2.2) | `spaces[]`: one point-in-outline test |
| ceiling heights from elevations or reflected ceiling plans; a ceiling height per room | `FloorSetup.ceilingHeight`; `RoomFix.ceiling` (a number later) |
| finishes per room | `spaces[].id / o / h / name`; ceilings split by room |
| AI room naming (plan 3.4) | `spaces[].source` gains `'ai'` |
| hiding walls (plan Phase 0 list) | the ticks (`ToggleName`) |
| slab-edge lines as hints | R-4.3 |
| a box proxy for Walk on stairs | R-9.9 |
| the hotel climbable | a hotel v2 converted with a `stairways` record (`seed/convert_*`) |
| walls found by shape on layer 0 | U-16, unchanged |

## R-17. Risks

| Risk | Handling |
|---|---|
| The door finder misses a doorway (7 of 16 right on the fifth drawing) | a wall drawn across it: rooms and floors are right, Walk is blocked until staff set the lines aside, as today. Nothing drawn across it: the doorway closing (R-2.6) keeps the floor and the rooms; what it does not reach is flagged with its mouth and closed with one click. A false opening can split a room; no floor is lost. RA-18 tests it by undoing each door |
| A closing rule closes a real outdoor recess or courtyard (over-filling) | bridges only where two open areas are separated; doorway closings only between wall ends; specks take no part; "no floor here" and "Not a doorway"; the 150 m² no-door flag; RA-4's upper bounds |
| The revised bridge rule (strips, specks, two open areas) was designed from measurements of the first rule, not run | R1's first task runs it on the eight floors before building on it; RA-4's lower bounds and RA-6's points are measured against the trial, not against the rule's own output |
| The bridge rule is slow (the trial script took up to 117 s on one floor) | the measured recipe: the closing runs on a copy with small holes filled, simplified by 1 cm (under 0.5 s a floor as a script); RA-14's budget (each test drawing at most 30 s more than today) |
| A room does not close and nothing says so | two flag rules that do not depend on the wall thickness (R-2.5), the fallback for walls that never close, the `room-open` flag for names |
| Names misplaced | where the name stands first; one-to-one by area; every drawn name keeps its label; answer keys as fixtures (RA-7) |
| X marks found where there are none | the diagonals of one drawn rectangle; furniture, grid and dimension layers excluded; never over 60 m² or 30 % of the floor by itself; three must-not-cut tests |
| A stair misread (direction, count, match) | the riser counts pinned per flight and tested on the reader alone; senses before chaining; five direction rules, staff last; the riser check; the `stair` flag with its reason; the stair probe on the house and the bank |
| What R2 builds and what R4 walks do not meet (lap, bridge, step-up are spread over two builders) | one reference building, made by one script, feeds both; a contract test within 1 mm; R4's tracer climb first; a smoke step with the real house and bank as soon as R1 and R2 report (WORK_BREAKDOWN RI-0) |
| Lower-floor walls in the stair's way (the bank) | the clash cut (R-8.3) with its flag; the stair probe's "crosses never" check |
| The walker gets into a step, or sticks at the top of a flight | the ground ray from 1.0 m; the 0.05 m lap and the 0.08 m bridge; the invariants of R-9.2 on random walks |
| In a stacked stair core, the floor above stays over the lower stair's low treads (headroom allows it), where the building really has the next storey's flight (the bank's Level 2 north lane, the tower's L30 core) | accepted for this milestone: the walker is never blocked by it; the fenced-band rule (R-8.2) removes the part fenced by handrails; the Check step shows the well, and staff can remove the rest ("no floor here" after a closing line) |
| Old versions walk differently with the new viewer | the foot-based walker only with `stairways`; the walk-parity golden recorded before the change, through the frame path too; `upload-walk` on the eight old versions compared with 9 Nov |
| The old rule's outputs move (R3 changes every writer) | every output file of the five old-rule builds is pinned by R0 before the builders start |
| A project uploaded before the milestone keeps the old floors unnoticed | every new draft gets the new rules (R-1.3); the line on three steps |
| The OpenAPI check cannot tell additive from breaking for optional fields | the new rule with its two failing cases |
| Max refuses the new slabs (holes touching) | `max_safe` as today; the mock interpreter; RA-11 |
| Ceilings flicker against slabs or each other | one plate per piece, 2 cm under the height, single-sided; never coplanar with a slab (at least 2 cm under the next slab) |
| Bigger slabs bring new walk-probe failures (more doors and glass now judged) | expected: each is classified in `docs/rooms/GAPS.md` (ACCEPTANCE RA-6) |
| The tower's levels are assumed | its stair is a should; the gap report gives stair A's storey window (2.80–4.20 m) and stair B's counts |
| The new suite's rooms rest on a door finder that is wrong there | its rows in RA-3 and RA-4 are shoulds, by position; its reference is expected to move with the door finder's round (R-13) |
| The full check takes over an hour (builder tests about 20 min, browser about 40 min) | budgets in RA-14; one new-rule build per drawing shared by the tests of a session; the costly runs only under the acceptance flag |
| Hours: the plan has no line for this work | WORK_BREAKDOWN 9.2, reported to the owner |

## R-18. Decisions made here

0. **Contract changes** follow D-18.0 and U-18.0: frozen at the scaffold R0. A defect goes in the finder's own
   `docs/rooms/contract-issues/R<n>.md`, settled by the integration step.
1. **New behaviour only through options, and in a settings document a missing option means the old rule.** Reason: the
   bank's byte-for-byte goldens and every saved recipe stay valid.
2. **Every new draft gets the new rules; a saved version never changes** (R-1.3). A recipe written before this
   milestone gets them too; a recipe that carries the keys is kept. (The first version kept old recipes on the old
   rules until staff pressed a button; the review showed staff would not see that button.)
3. **The slab is the outside outline of the network, with terraces and holes, and never less than today's plate.**
   Reason: floors under the whole plan, without losing what the bank's rule built.
4. **The network includes every continuous line of the structural layers, set aside or not, and the single-line
   parts. Small gaps are bridged where a bridge separates two open areas; door-sized gaps between wall ends are closed
   as doorways. Every closing the app makes is a 2 cm strip, shown on the Check step, and staff can remove it.**
   Reason: measured on the five drawings (§0); mitre closings are not monotonic, round closings round the room
   corners, and counting contact stretches hangs on millimetres.
5. **Rooms are the network's faces whose edge is at least half structure. A name belongs to the room it stands in;
   written areas place the names that stand in none. `rooms[]` stays the drawn names, and the rooms' outlines are a
   new `spaces[]`.**
6. **Ceilings are cut from the plate's outline, one plate per floor piece at a default height of min(3.00, wall height
   − 0.30), shown in Walk and Ghost only, hidden layers in 3ds Max.**
7. **Stairs come from the stair layers plus their continuation on any layer, are matched across two floors, and take
   their riser from the levels. Flights that arrive and flights that leave are never chained.**
8. **Treads and landings are new part kinds; `step` keeps its v1 meaning.** Reason: bank v2 and the hotel carry `step`
   parts that must keep walking as before.
9. **No ramp collider**: step solids with a 0.25 m step-up (the plan's 3.3 named a ramp collider). Reason: measured
   climbing on the hotel's real steps; a ramp would need its own geometry and an exact meeting with the landings.
10. **The foot-based walker is switched on by the `stairways` key only;** without it the walker is today's, exactly.
11. **The floor you are on follows your feet;** the floor buttons and PgUp / PgDn stay teleports.
12. **Lower-floor parts under a flight are cut to the flight's underside;** the stair well is cut where headroom (2.10 m)
    needs it; a stair that stays as lines keeps today's opening.
13. **BuiltModel v2 is v1 plus optional additions,** recorded in `version.json` as `built-model/2`; the model keeps no
    version field.
14. **Settings fields are optional with defaults in the API and in both TypeScript copies,** and the OpenAPI check
    accepts an added optional property and nothing more.
15. **Fixes for rooms and stairs are points and lines,** not item keys, so they survive re-exports.
16. **The upload milestone's acceptance fixtures are not changed;** the new rules have their own `*-rooms` fixtures.
17. **A-7 (the bank through the screens) keeps its byte-for-byte checks** by choosing "the earlier way" in the fold;
    the new owner's path is a test of its own.
18. **This milestone comes first; the door finder is frozen until it is done** (the owner's order of 10 Nov). The fifth
    drawing's openings may be cited; its acceptance rows are shoulds, by position.
19. **The acceptance checks are scripts in the repository** (`tools/rooms/acceptance/`), one command, a JSON result,
    `GAPS.md` written from it. Reason: the last milestone's lived in temp folders and could not be run again.
20. **The scaffold leaves a working tracer, not stubs:** the chain from a drawing to a model with a stairway is green on
    a two-floor test drawing before the builders start, and one reference building, made by one script, feeds every
    package's fixtures.

---

## Review notes (11 Nov 2026)

Three independent critics read the first version on 10 – 11 Nov. Each finding was checked in the code, in the critics'
scripts and outputs, or on the drawings' plots before it was acted on. **G** is the geometry critic, **O** the owner's
path and screens, **T** testability and integration. Rejected parts are marked.

| Finding | Settled in | Where it differs from the proposal, and why |
|---|---|---|
| G1 the X rule cuts real floor and misses the tower's shafts | R-4.3, R-1.1, R-15, R-17; RA-5 | Adopted. Two differences. Three ends at corners and the fourth on a side also count: the same-box test misses the house's stair hall, whose drawn void (16.6 m²) is larger than the headroom well; tried on the five drawings (`revise_step/x3.py`): the expected holes and nothing else. The shape is the rectangle the ends mark, with its outline drawn, instead of "a network face, closed polyline or box of lines": one test in place of three |
| G2 flights chained before their direction is known | R-7.3, R-7.4, R-7.5, R-7.7; RA-9 | Adopted. The sense comes from words only: an arrow or the cut pattern gives the end that is at this floor, not up or down, so they feed the direction. The table has a fourth row (undecided), and a stacked core's next storey goes to "another stair" when the model has a floor above |
| G3 wrong widths, a phantom flight, wrong counts | R-7.1, R-7.2, R-7.7; RA-9 | Adopted. The counts 7 + 14 and 4 + 5 + 3 + 9 were checked on the plots by this revision. The lines the first rules missed: the house's 0.40 m bottom step, the bank's riser cut by the break line, the skipped `TREE` risers |
| G4 what a missed doorway does | R-2.6, R-3.1, R-6.1, R-6.2, the owner's text; RA-18 | Adopted, with three differences. (1) "Same thickness within 5 cm" left 3 of the bank's 8 leaking doors open (0.10 m walls meet 0.20 m walls): the ends may differ, and a wall end facing a wall's side counts where the floor needs it (tried, `revise_step/doorgap3.py`). (2) The must is the trial's result: 0 of 25 on bank L2; the one door each on bank L1 and the house's ground floor that still leaks must carry a flag. (3) **Rejected:** the choice "it is a door or an opening" that writes an opening fix. Where the app closes a gap the wall is already open, and a door added by hand needs the door finder's record, which belongs to its fix round (R-16) |
| G5 the bridge rule is fragile | §1, R-2.2, R-4.2, R-15; RA-4 | Adopted: the real limits, a bridge decided by what it separates, strips, specks left out, the same rule for terraces. Decided: the house's loop gets no floor. It is pinned by a point in RA-4, not by area within 3 m², because the revised rule was not run; R1's first task records the area. The speck limit (0.05 m²) is the critic's proposal; the critic measured with 0.1 m² |
| G6 the walker can walk into the side of the low steps | R-9.2, R-9.10; RA-10 | Adopted |
| G7 the ceiling by closing leaves holes | R-5.2; RA-8 | Adopted |
| G8 "by written area" takes names out of their rooms | R-3.2; RA-7 | Adopted |
| G9 furniture and symbols become rooms | R-3.1, R-2.5; RA-3 | Adopted. Doorway closings count as structure, bridges do not |
| G10 today's 4 m² is the walls' area | R-2.5, R-4.1 | Adopted. A detached piece under 12 m² also needs a door on it (G9's object rule, applied to the ring) |
| G11 open lines on room-outline layers | R-2.4 | Adopted |
| G12 the well grown at the arrival; sliver cuts | R-8.2, R-8.3 | Adopted. Every hole is also trimmed at the top riser, since an X hole can reach it too |
| G13 always floor N+1; turning steps; ramps | R-7.5, R-7.6, R-8.2, R-12.1 | Adopted |
| G14 the "not verified" list | R-2.2, R-17; RA-14; the gap report | Adopted |
| O1 when a room does not close the flag often says nothing | R-2.5, R-6.1, R-6.2; RA-3, RA-12 | Adopted. Both rules flag from 4 m² |
| O2 a project uploaded before keeps the old floors | R-1.3, R-12.6, R-18 decision 2; RA-1, RA-12 | Adopted. An open draft from before the milestone keeps the earlier way and shows the line (the owner's store has none). The old flag's stored text is not changed, so the old rule's outputs stay byte for byte: the staff app adds the hint |
| O3 "Set aside" can take the new floor away | R-2.1 point 7, R-6.2; RA-13, RA-17 | Adopted |
| O4 the three fixes' clicks are not designed | R-6.2, R-6.4, R-12.6 | Adopted |
| O5 a stair that stays as lines loses its opening | R-4.3, R-5.2; RA-5 | Adopted for stair groups in which no climbable stair arrives. Where one arrives, only the other flights' own footprints are cut, and never the arrival: today's hull would cut the way from the top step to the floor |
| O6 stair flags staff can do nothing about; no flag when no stair is found | R-6.1, R-6.2, R-7.6 | Adopted |
| O7 one name per room merges the designer's labels | R-3.2, R-3.4, R-12.1; RA-7 | Adopted: `rooms[]` stays the drawn names; the rooms go in `spaces[]`. No consumer of `rooms[]` changes |
| O8 the owner's summary is out of date in one place and silent in four | For the owner | Adopted |
| O9 three surprises in 3ds Max | R-10, R-9.6, R-8.3; RA-11 | Adopted |
| O10 three "nothing else moved" statements overtaken | R-13; RA-2, RA-6, RA-16 | Adopted |
| O11 no criterion measures the staff's fix time | RA-17; WORK_BREAKDOWN RI, RR | Adopted, as a should |
| O12 three selects nobody should choose | R-1.2, R-12.6 | Adopted |
| O13 nothing to switch off on the Check plan; bridges unseen | R-12.4, R-12.6 | Adopted |
| O14 the room's name in Walk; counts on Build and Save | R-12.6; R-16 | Counts adopted. **Rejected for this milestone:** the room's name in the Walk read-out. Nothing in the gate needs it; `spaces[]` is its seam |
| O15 checked, no change needed | – | – |
| T1 the seam between R1 and R2 | R-12.3; WORK_BREAKDOWN R0, R1, R2 | Adopted |
| T2 nothing ties what R2 builds to what R4 walks | ACCEPTANCE 2.5; WORK_BREAKDOWN R0, R2, R4, RI-0 | Adopted |
| T3 musts that cannot fail; checks that cannot be run again | RA-3, RA-4, RA-7, RA-9; `tools/rooms/acceptance/` | Adopted. The lower bounds are 95 % of the trial's measured plates (§0), not of R1's own figure, so they do not move with the code they judge |
| T4 the probe's stale foot | R-9.8; RA-10 | Adopted |
| T5 R0 cannot leave the workspace green as written | R-12.3, R-12.4, R-12.7; WORK_BREAKDOWN R0; ACCEPTANCE 3 | Adopted. R0 writes the v2 rules in all three checkers |
| T6 the design was overtaken; the order with the detector | the top note, R-13, R-18 decision 18; RA-3, RA-6 | Adopted: this milestone first, the detector frozen. **Rejected:** reserving an `openings` option key now. The additive rule added here lets the next milestone add its key the same way, and a name reserved before that design exists would freeze a guess |
| T7 the screens and their spec are built apart | WORK_BREAKDOWN R6, R7; R-12.6 | Adopted: R6 owns `rooms.spec.ts`, the `upload.spec.ts` change and `plan-canvas.spec.ts`. The test-id module and the `window.__plan` hook are added as well |
| T8 the old rule is guarded for the model only | R-13; RA-1; WORK_BREAKDOWN R0 | Adopted |
| T9 stale baselines | R-13; RA-2, RA-16; ACCEPTANCE 3 | Adopted |
| T10 the walk-parity golden is under-defined | R-13; RA-2; WORK_BREAKDOWN R0 | Adopted |
| T11 probe ids are not stable | RA-6; ACCEPTANCE 2.5 | Adopted |
| T12 the well check; entering a stair from the side; frame-rate dependence | R-9.2; RA-10 | Adopted. The ground ray starts at foot + 1.0 m (the geometry critic's figure), not + 1.9 m: above 1.0 m the head ray already refuses the move, and both critics' cases come out the same |
| T13 the selects' test cannot fail | R-13; RA-12; ACCEPTANCE 2.4 | Adopted |
| T14 one rule built in three places | R-1.2, R-1.3; RA-1; ACCEPTANCE 2.2 | Adopted, with its part (b) turned round by O2: a new version from a pre-milestone recipe gets the new rules; the old stamp comes from the old values written out |
| T15 files with no owner; one shared `dist/` | WORK_BREAKDOWN 0 and the Owns lists | Adopted |
| T16 determinism in one process; `stairways` empty or absent | R-8.5, R-12.2, R-13; RA-15 | Adopted |
| T17 run times | RA-14; ACCEPTANCE 2; RA-12 | Adopted. The bank's second path runs through the API |
| T18 the split of hours and the agent-time forecast | WORK_BREAKDOWN 8, 9 | Adopted in direction. The total is about 237 h, not near 200 h: the other two critics' findings add rules and screens |
| T19 the Max mock | R-10; RA-11 | Adopted |
| T20 small gaps in measurability | RA-3, RA-5, RA-8, RA-14 | Adopted. The east building's points are fixed by R1's first task: this revision has no plot of it |
| T21 limits of the review | WORK_BREAKDOWN R0 | Adopted. The gap-bridge run was done by the geometry critic (3 cm is enough) |

**What this revision did not verify.**
* The revised bridge rule (strips, specks, "two open areas") and the pocket rule were not run by this revision; the
  bridge figures are the first rule's, the pocket figures the owner-path critic's.
* The doorway rule and the X rule were run as scripts on the captured floors: the doorway rule not on the new suite, the
  X rule on bounding boxes and without the drawn-outline test. Neither exists as builder code.
* The stair reader's revised rules were not run. The riser counts were read off four plots.
* The walker's ground ray from 1.0 m was not run.
* The house's loop was judged from one plot.
* The hours are estimates.
