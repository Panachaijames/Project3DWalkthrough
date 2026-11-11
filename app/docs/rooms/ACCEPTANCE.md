# Rooms, slabs and stairs: acceptance criteria and test plan (10 Nov 2026; revised on 11 Nov 2026 after the review by three critics)

What "done" means for `DESIGN.md` (cited R-n), and the tests that show it. **Must** criteria gate the milestone;
**should** criteria are reported with numbers when they are missed. A should becomes a must when its cause would hit
the other drawings too (the rule of the upload milestone's A-12).

**Where the expected figures come from.** The "trial" figures were measured on 10 – 11 Nov by scratch scripts on the
current builder's captured networks (`...\scratchpad\rooms_design\`: `design_step\`, `geo_critique\`, `revise_step\`).
They are not the builder's final code, and three of the revised rules were not run at all (DESIGN, *What this revision
did not verify*). So:
* **R1's first task** runs the network, the closings, the rooms, the plate and the X marks on the five drawings with its
  own code and records the figures of RA-3 – RA-5 and RA-18 in `contract-issues/R1.md`;
* **R2's first task** plots each stair and records the riser counts of RA-9 in `contract-issues/R2.md`;
* a figure that differs from this file by more than 2 % (or by one riser) is a contract issue before anything is built
  on it. RI then checks against the ranges below.

**The fifth drawing.** `presidential suite_layout.dwg` (the new suite) was scored as a drawing the door finder had never
seen on 10 Nov: 7 of 16 doorways right (`detector/blind_run_suite_revit/README.md`). The door finder is not changed in
this milestone. The new suite's rooms and areas rest on its output there, so its rows are **shoulds, given by
position**, and its pinned reference is expected to move with the door finder's round (DESIGN R-13).

**Coordinates** are sheet metres after alignment (U-9.4), unless a row says "model frame". For the house both plans are
given in the ground plan's frame (the upper plan less 74.022 m in x).

**No step relies on a reload.** `npm run dev` and `tools/run-api.mjs` no longer reload the API when code changes
(`../upload/contract-issues/UI.md`, UI-5). Every acceptance run starts its servers after the last code change; after a
fix to API code the server is stopped (Ctrl+C) and started again before the check is repeated. The e2e config starts
its own servers for every run (`reuseExistingServer: false`). Builder code needs no restart: the worker is a new
process for every build.

**One command.** `node tools/rooms/acceptance/run.mjs` runs the acceptance steps and writes
`%TEMP%\wt-ri\acc\result.json`; `docs/rooms/GAPS.md` is written from that file. The scripts start as copies of the
upload milestone's (`%TEMP%\wt-uf\scripts`, `%TEMP%\wt-ur\scripts`: `acc.py`, `check_a1.py`, `a9.py`,
`owner-path.mjs` and the others), brought into the repository by R0 and filled by RI, so the review step and the owner
can run them again.

**Inputs of every acceptance run.**
* **Drawings**: the project folder's DWGs, uploaded through the API.
* **The store**: `%TEMP%\wt-ri\acc`, started as a copy of the upload milestone's acceptance store (R0's copy
  `%TEMP%\wt-r0\acc-9nov`), so one store holds the eight old versions and the five new ones.
* **Settings**:
  * `fixtures/upload/settings/<name>-rooms.json` for the new rule (DESIGN R-1.3): the upload milestone's fixtures plus
    `slabs: 'network'`, `ceilings: 'auto'`, `stairs: 'climb'`;
  * the house's ceiling heights 3.00 / 2.90;
  * for `suite-revit-rooms`, the A-12 recipe with layer 0 as wall (no set-asides: the saved A-12 recipe has none);
  * the unchanged `fixtures/upload/settings/<name>.json` for the old rule.
* **Answer keys**, kept as fixtures in `fixtures/rooms/keys/`: `bank.json` (each room tag's own point), `probes.json`
  (the walk probes of RA-6 by floor, sheet point and side), `house.json` and `suite.json` (points picked once from the
  plots, DESIGN R-7.7 and RA-3, RA-7).
* **Floor keys and levels** as in the upload milestone:
  * bank: `L1` / `L2`, 0 / 3.70;
  * house: `ground` / `upper`, 0.90 / 4.80;
  * old suite: `suite`, 0;
  * tower: `L29` / `L30`, 0 / 4.00, assumed;
  * new suite: `L1`, 0.

## 1. Acceptance criteria

### RA-1 The old rule is untouched, and the right builds get the new one (must)

The bank's re-upload of the upload milestone's A-1, run again both ways (as a new project, and as version 3 of the
seeded `bank-sampeng`) with `fixtures/upload/settings/bank.json` (no new keys) put through the API as a settings
document:

| Output | Must equal |
|---|---|
| `model.json` | sha1 `c3a9408304a240b83c36f5c5c53db56b50a72c64` (stamp `c3a9408304a2`), `version.json` `modelFormat: built-model/1` |
| the report's `summary` | `bank_test/src/bank_summary.json` in content |
| the furniture CSV | `b528bb2320ef...` |
| `assets/topview.png` | `f084b556503c...` (should, as in A-1) |
| `stages.json` | v2's `lines`, `rings`, `sheet`, `source.files`, `source.layersInUse`, `source.units` |
| the Max generator with `bank-27oct` / `hotel-2nov` | `Bangkok_Bank_Sampeng.ms` `615d50137bdb...` / `Hotel_Lobby.ms` `0a30014a84e0...` byte for byte |

* The same bank build from settings with the three options **written out at their old values** (`closed-rooms`, `off`,
  `lines`) gives the same model bytes.
* **Every output file of the five old-rule builds** is unchanged: the bank, and the house, the old suite, the tower and
  the new suite built from their saved versions' recipes (stamps `1c07bfeef580`, `205e9c2c46e8`, `91414f408cb2`,
  `1d90d91ef949`). Model, stages, overlay, flags, diff, top view and Max script (fixed date) are compared with the
  sha1s that R0 recorded from the unchanged code (`test_r_old_rule.py`). With `WT_INTEGRATION=1` a missing reference
  fails; nothing is skipped.
* **Which rules a new draft gets** (DESIGN R-1.3), one integration test with the real worker:
  1. a new project's adopted settings carry the new values;
  2. a new version of a project whose saved recipe has none of the three keys (the house as saved on 9 Nov: the test
     puts `fixtures/upload/settings/recipes/house.json` into its temp store as version 1's recipe) carries the new
     values and builds a `built-model/2` model whose plate contains (26.2, 11.1) and whose `stairways` holds the main
     stair;
  3. the same draft switched to "the earlier way" builds the old stamp `1c07bfeef580`;
  4. a recipe that carries the keys, old or new, is kept as it is.

### RA-2 Saved versions never change; old versions look and walk as before (must)

* **`app/data`**: every file listed in `docs/rooms/reference/versions.sha1` (the 49 files under
  `app/data/projects/*/versions/`, recorded by R0) has the same sha1 at the end. New files are allowed: the owner uses
  the app. Uploads and drafts in the store are not counted and never touched; nothing is "restored".
* **`npm run seed`** into a temp folder gives the five stamps (`4b02dc17f286`, `c3a9408304a2`, `f1b95c53eb3d`,
  `e43270cc0c9b`, `6ab030750886`) and files equal to the committed `app/data` version files (`git show`).
* **The upload milestone's eight saved versions** (in the acceptance store's copy): their files are unchanged, and
  every one still opens in the viewer with no error.
* **The walk-parity golden** (DESIGN R-13), recorded by R0 from the unchanged viewer:
  * models: the six model files that `fixtures/models` holds today (`bank-v1`, `bank-v2`, `hotel`, `house`, `mini`,
    `suite`), their sha1 in the golden;
  * walks: the wall, door and glass recipes and floor edges with their `clearance`, `open` and `findFree` results;
    key-driven walks through `tick(now)` with a made-up clock; PgUp, a double-click landing, a Ghost → Walk landing, one
    eye-height change; the walk into the hotel's F1 flight;
  * check: the new viewer's end positions and floors equal the golden within 1e-9 m; the golden's own sha1 is pinned,
    and it names the viewer tree it was recorded from.
* The bank's and hotel's `step` parts are still colliders: the hotel's F1 flight still stops today's walk 1.3 m in.
* **`upload-walk` on the eight old uploaded versions** with the new viewer template gives the same result probe by
  probe as the reports of 9 Nov (`%TEMP%\wt-uf\e2e\upload-walk`, copied by R0).
* The structure, modes, furniture, replay, offline and upload-walk browser specs pass unchanged on a freshly seeded
  store (`WT_DATA_DIR`, `WT_OFFLINE_DIR`), never on `app/data`.

### RA-3 Rooms (must, should where said)

On the eight floors (bank L1, L2; house ground, upper; old suite; tower L29, L30; new suite L1), built with the new
rule:

| Floor | Must | Trial (10 – 11 Nov) |
|---|---|---|
| bank L1 / L2 | each of the 7 + 11 names' own point lies in a room, and that room carries the name (`keys/bank.json`, 18 of 18, checked by the test) | 15 / 14 faces |
| house ground | the glass-walled living room is one room: it contains (26.2, 11.1) and is 60–90 m²; every room of the small east building is a room (one point each, fixed by R1's first task in `keys/house.json` and checked against the plot by the review) | 24 faces |
| house upper | no named point; the rooms of RA-6's probes | 25 faces |
| old suite | at least 13 of its 16 names belong to a room; the others are flagged `room-open` | 13 of 16 inside the closed outlines |
| tower L29 / L30 | the rooms between the core and the curtain wall are rooms: RA-6's probe points stand in rooms | 32 / 34 faces |
| new suite (should, by position) | `BAR` and `BOH.` are kept as names; the bed at (5.38, 5.84) and the sofa corner at (13.61, 8.34) are not rooms of their own (the report counts them as enclosed shapes) | 18 faces, two of them furniture |

* **A room that does not close is floored or flagged** (unit, must): a 10 × 10 m room with one opening of 0.8, 1.6 or
  2.9 m in its outside wall, in 0.10 m and in 0.20 m walls, with no door found. Each case gives the room its floor (a
  doorway closing) or a `slab-gap` flag whose mouth lies on the opening.
* **Furniture is not a room** (unit, must): a bed, a table and a sofa corner drawn as lines on a wall layer inside a
  room leave it one room.
* **The report** gives, per floor: the rooms, the named ones, the enclosed shapes left out, the names in no room, the
  rooms with several names.
* **The plan's gate line is reported as it stands**: "every room closed on both floors with no staff fix", for the bank
  and for the house.

### RA-4 Slab areas against the drawings (must for the bounds, should for the ranges)

Plate0 per floor (before holes and before the 3 cm edge, closed outlines filled; report `slab.plate`), in m²:

| Floor | Today (old rule) | Trial: ring | Trial: plate0 (ring ∪ today's) | Must: at least | Must: at most | Should: within |
|---|---|---|---|---|---|---|
| bank L1 | 235.3 | 235.8 | 235.8 | today's | 243 | 234 – 241 |
| bank L2 | 295.4 | 242.8 | 295.7 | today's | 307 | 293 – 303 |
| house ground | 421.6 | 466.3 | 508.0 | 483 | 545 | 495 – 530 |
| house upper | 423.0 | 453.3 | 454.3 | 431 | 497 | 435 – 460 |
| tower L29 | 430.9 | 856.8 | 856.8 | 814 | 885 | 840 – 875 |
| tower L30 | 536.4 | 740.9 | 740.9 | 704 | 772 | 725 – 765 |
| old suite | 108.6 | 416.4 | 421.7, plus 53.2 of terrace (within 3 m², decided 11 Nov: R1.md D-3) | 400 | 660 | 460 – 480 |
| new suite (layer 0 as wall; should) | 170.9 | 247.0 | 274.0 | 260 | 284 | 262 – 280 |

* **"At least"** is 95 % of the trial's plate0 on the floors this milestone exists for (the trial's figure, so the bound
  does not move with the code it judges). For the bank it is today's plate.
* **Never smaller than today's**, on all eight floors: the area of today's plate (old rule, same drawing) outside
  plate0 is under 0.5 m². This holds by construction (DESIGN R-4.1) and guards the union only.
* **"At most"** is a round closing of 1.5 m of the same network with its railings, plus 2 %: a guard against a closing
  or terrace rule that runs away.
* **The house's upper loop gets no floor**: the point (26.7, 13.0) is not on the plate, and a `slab-gap` flag covers it.
* **The old suite's terrace** is measured by R1's first task with the rule of DESIGN R-4.2 and then holds within 3 m².
* **Against the prototypes' slabs** (should, reported with a picture per floor): the area that is in the new plate and
  not in the prototype's slab, and the other way, for the bank (`fixtures/models/bank-v2.model.json`), the house and the
  old suite (its hand-drawn slab is 648 m²). A difference over 15 % of the prototype's slab is explained in `GAPS.md`.
* **Against the written areas** (should): of the bank's 12 rooms with a written area, at least 8 are within 15 % of it
  (the trial's count); the old suite's are reported.
* **Every slab part passes the Max checks**: no hole within 0.5 mm of its outline or of another hole.
* **No piece of 4 m² or less is lost silently**: each is in the report's `slab.dropped` with its reason.

### RA-5 Holes against the drawings (must)

| Floor | Hole | Must |
|---|---|---|
| house upper | double-height living room (X, x 19.45 – 24.95, y 14.51 – 19.26) | cut, 26.1 ± 1.0 m² |
| house upper | stair hall (an X with three ends at corners; x 19.50 – 24.95, y 21.41 – 24.46), which holds the main stair's well | cut, 16.6 ± 1.0 m²; it covers every tread of the main stair whose top is above 1.55 m (= 3.90 − 0.25 − 2.10); its east edge is the top riser (x 24.93 – 24.95), so the slab laps the last tread |
| house upper | service stair ST-02 (kept as lines) | today's void stays: 3.9 ± 0.5 m² |
| house upper | the 0.84 m² duct X; three roof slots 0.3 m wide; wall lines crossing `TREE` lines | **not** cut; the duct and the slots are listed in the report |
| house ground | – | no hole (the lowest floor; its plinth slab as today); its three small X's (under 0.7 m²) are reported |
| bank L1, L2 | lift shaft (the X of 1.4 × 1.4 m inside the lift door block, 1.96 m², and the lift-door cell, merged) | cut on both floors, 1.9 – 3.4 m², within x −3.43 – −1.63, y −8.58 – −6.83. **The grid lines cut nothing** |
| bank L2 | stair well | covers flight 4, the landing over the toilet, flight 3, the north-west landing, the top of flight 2, the band between the two flights fenced by handrails (DESIGN R-8.2), and the footprint of the next stair's `UP` flight; does **not** cover flight 1 or the north-east landing; 6 – 12 m² (R2's first task records the figure) |
| tower L29 | four shafts: three lifts (the lift-door X of 2.24 m² and the `A-DETL` X of 2.78 m², merged) and one `A-DETL` X of 2.81 m² | four holes of 2.7 – 3.6 m² |
| tower L30 | four shafts (`A-DETL` X's of 2.78, 2.78, 2.78 and 2.81 m²) | four holes of 2.7 – 3.6 m² |
| tower L30 | stair A's well | cut where headroom needs it; the floor-level landings at the east end (x 11.2 – 13.0) stay floor |
| tower L30 | stair B (kept as lines) | today's void stays: 17 ± 1 m² |
| old suite, new suite | – | no X hole. **The old suite's 3.0 × 1.5 m rectangle with a divider cuts nothing** |
| every floor | – | each hole is a `voids[floor]` record with its `what`; holes under 0.5 m² are reported, not cut; no hole of over 60 m² or over 30 % of the plate is cut by itself |

The holes are asserted in a heavy builder test, by the hole's `what`, place and area.

### RA-6 The floors that were missing (must)

The walk probes that failed for "no start: no floor" in `../upload/GAPS.md` now find floor at their start points. The
probes are named here by their ids of 9 Nov, but the ids are running counts and can move (a glass probe's id counts all
probes, `build/model.py:147`). So R0 records each one's **floor, sheet point and side** in `keys/probes.json` from the
reports of 9 Nov, and the checks use those.

| Drawing | Probes |
|---|---|
| house | `ground-004`, `ground-006`, `ground-018`, `upper glass 44` (`ground-034`, a garden gate in a free-standing wall with no floor on either side, was taken out on 11 Nov: R1.md D-2; it stays in the walk report as "outdoors, no floor") |
| old suite | `suite-025` |
| tower | `L29-001`, `L29-016`, `L29-025`, `L29-028`, `L30-033`, `L30-032`, `L30 glass 24`, `L30 glass 26` |
| new suite (should) | no door probe ends with "no start: no floor" |

* **In the builder first** (heavy, seconds): the plate contains the point 0.4 – 0.9 m in front of the opening, on the
  side that had no floor.
* **In the browser**: the walk itself. Each probe then passes or fails for another reason, which `docs/rooms/GAPS.md`
  lists and classes.
* **With the stray lines set aside** (the state staff will leave): the tower and the new suite built again with every
  item of their single-line flags set aside. The areas stay inside RA-4's ranges and the probes above still stand on
  floor.
* The bank's new-rule version passes every wall, door and glass probe of `upload-walk.spec.ts`, as the old one does (80
  wall spots, 39 doors, 44 glass probes; the counts may grow with the new floors, never shrink).

### RA-7 Room names (must, should where said)

* **Every name belongs to the room the drawing means**, against the answer keys: must for the bank (18 of 18,
  `keys/bank.json`, automatic); should for the old suite (at least 13 of 16, against 16 key points picked once at RI
  into `keys/suite.json`).
* **The named pairs of the trial** (unit and heavy): the bank's `TOILET 3.2` stays in the 3.1 m² room it stands in;
  `FEMALE TOILET 6.4` stays in its 3.3 m² face and the F/C room keeps one name; the old suite's `Steam 3m2` stays in
  its 2.8 m² room; `Foyer 10m2` and `Massage Room 9m2` do not both go to one room.
* **Every drawn name keeps its label where the designer wrote it.** The bank's new-rule version shows 23 labels at the
  drawing's positions, in the viewer and as 3ds Max text objects, and its version counts 23 rooms: today's 18 plus
  `ATM` (three times), `BA` and `BE`, which R-3.2 keeps as names where today's 4-letter limit dropped them (decided 11
  Nov, R1.md D-1: no letter limit keeps `BAR` and drops `ATM`). The 18 of today stand where they stand today. The hall
  with `CSO 5PAX`, `WAITING AREA` and `FOR 1 PAX` shows three labels and one `room-names` flag (info).
* A name carrying its area ("Bar 7,6m2") gives the name "Bar" and keeps "Bar · 7,6m2" as its label. Comma decimals are
  read; no name keeps a trailing area.
* `BAR`, `BOH.`, `WC` are names; `D1`, `ST-05`, `R-01` are not (unit test and the house's and new suite's builds).
* Old versions' counts are unchanged.
* A room fix names a room (RA-13).

### RA-8 Ceilings (must)

* Every room has a `ceiling` part over it, except where the floor above has a hole and where a stair needs headroom
  (DESIGN R-5.2). The ceiling heights:
  * the house: 3.00 m above +0.90 and 2.90 m above +4.80 (typed);
  * the other drawings: the default rule (3.00 m, the old suite and the new suite 2.70 m).
* **No hole in a ceiling over a part that is lower than the ceiling height** (single-line parts, low partitions,
  furniture drawn on a wall layer, small cells). One ceiling piece per piece of plate, less the holes above: the house's
  upper floor has no more ceiling pieces than plate pieces.
* No ceiling:
  * over the house's ground-floor living room where the upper floor's X void is;
  * over the terraces;
  * over a room marked "no ceiling".
* Every ceiling lies at least 2 cm under the slab above, and no two ceiling parts overlap.
* In Edge (`tests/e2e/stairs.spec.ts`), with the house's new-rule offline file:
  * in Walk, a ray up from the middle of a room hits a ceiling mesh at the ceiling height;
  * in Orbit, the ceiling meshes are not visible;
  * the Ceilings tick hides them in Walk;
  * the old versions' panels show no Ceilings tick.

### RA-9 Stairs read from the drawings (must for the house and the bank, should elsewhere)

**The reader alone, before any solid is built** (heavy tests on the drawings' caches):

| Drawing | Stair | Must / should | Risers per flight |
|---|---|---|---|
| house, ground plan | main stair | must | 7 (the first 0.40 m before the second, flared), then 14 (6 on `STAIR`, 8 on `TREE`) |
| house, upper plan | main stair | must | the top 9 on `STAIR`; every riser within 5 cm of the ground plan's |
| bank, Level 1 | main stair | must | 4 (east), 5 (north), 3 (west) |
| bank, Level 2 | main stair; the next stair | must | 9 (`DOWN`); 9 (`UP`): two stairs, never one chain |
| tower, both floors | stair A | should | 10 + 10; flight widths 1.65 m (not 0.46 m); no third flight |
| tower | stair B | should | L29: 10 + 8; L30: 8 + 8 (+1); flight widths 1.2 – 1.3 m |

**The stairs:**

| Drawing | Stair | Must / should | Expected |
|---|---|---|---|
| house | main stair | must | climbable `ground` → `upper`, 21 risers, riser 0.186 ± 0.002 m, kind `L`, 1 landing, the bottom within 0.3 m of (20.40, 21.15), direction from the walking line; the upper plan's drawing adds no stair and no flag |
| bank | main stair | must | climbable `L1` → `L2`, 21 risers, riser 0.176 ± 0.002 m, 3 landings, matched across the two files, direction from L2's word and arrow (and L1's cut) |
| tower | stair A | should | climbable `L29` → `L30`, 20 risers, 0.200 ± 0.002 m, kind `U`; the gap report gives the storey heights that would fit (2.80 – 4.20 m) |
| tower | stair B | must | lines, a `stair` flag naming the riser height and the storey that would fit |
| house | ST-05, ST-02 | must | lines, `stair` flags with their reasons (no floor at that height; the riser does not fit) |
| bank | Level 2's next stair up | must | lines, `stair` flag "leads to a floor that is not in the model" (info) |
| bank | north stair | should | built or flagged, the reason recorded |
| every drawing | every stair group, with or without flights | must | climbable or flagged with a reason; no two-riser `step` part in a new-rule model; a `stairs-none` flag for a pair of floors with no climbable stair |

* Every tread lies between its two riser lines, within 0.02 m of their own ends.
* The slab of the upper floor laps the last tread by 0.05 m in plan.
* Every lower-floor part that overlaps the stair's walking volume by 2 cm and 0.01 m² or more is cut to the stair's
  underside and listed (`stair-clash`). On the bank this includes the Level 1 toilet's walls under flights 3 and 4. A
  side wall that only touches the treads is not cut.
* Each climbable stair is a `stairways[]` record whose `walk` starts on the lower floor's plate and ends on the upper
  floor's plate, 0.3 m clear of walls.
* **The reference building** (2.5): built from its DXFs, the treads, landings, well and stairway equal the model fixture
  within 1 mm.

### RA-10 Climbing in Walk (must on the house and the bank, should on the tower)

**In Node** (vitest), on the reference building, the synthetic straight, L and U stairs, and at integration on the real
house and bank models:
* **Up and down** along `walk`: the foot ends at the upper floor's level ± 0.02 m, then back at the lower floor's.
* **The top edge at an angle**: the upper floor is reached walking at 45° and at 70° to the top riser.
* **The sides**: entering treads 1 – 6 from each side, from the floor beside the flight, either stops the walker or puts
  it on tread 1 only. From the middle of a flight, a walk to either side moves at most half the flight's width + 0.1 m.
* **What must always hold**, sampled every 5 cm on scripted walks and on seeded random walks over both floors:
  * the foot never rises more than 0.25 m nor drops more than 0.30 m;
  * no tread, landing or slab top lies between foot + 0.25 m and foot + 1.9 m over the walker's centre;
  * no 5 cm move crosses a collider;
  * the floor named matches the foot.
* **Under a low flight** the head ray stops the walker; the 0.08 m gap at the top of a flight is crossed.
* **The easing**, with a made-up clock: the eye settles within 0.5 s; a probe call never eases.
* **A probe after a climb**: the walker is put on a spot of the lower floor by writing its position, after a walk that
  ended up a stair; `onFloor` is true and `walk` starts from the floor's level.

**In Edge**, `tests/e2e/stairs.spec.ts` with the helper `stairWalks(page)` (`tests/e2e/lib/walks.ts`), on the offline
files of the house's and the bank's new-rule versions (and the tower's, should). For each climbable stair:
* **Up**: start on the lower floor at `walk[0]`, foot at that floor's level ± 0.01 m; walk each segment of `walk` with
  `probe.walk` (5 cm steps), then 1.0 m on. Pass when the foot is at the upper floor's level ± 0.02 m (it rose by 3.90 m
  on the house, 3.70 m on the bank), the floor buttons and `modechange` name the upper floor, the walker is 0.5 m or
  more past the last riser, and `probe.crosses` along each segment is never true.
* **Down**: the reverse path, ending on the lower floor's level ± 0.02 m and naming it.
* **By keyboard**: W is held only until the foot has risen three risers (the frame rate of software-drawn Edge is not
  part of the test); the probe finishes the climb.
* **A door probe beside the stair, then a far one**, both answer as on a flat floor (the stale-foot case).
* **Floor buttons**: PgUp / PgDn and the floor buttons still change floor (teleports), and the touch Upstairs /
  Downstairs buttons still show in Walk.

### RA-11 The 3ds Max script (must)

For the house's and the bank's new-rule versions (the `upload` profile):
* **Parts**: the slabs are `#slab` parts with their holes; the treads, landings and ceilings are `#tread`, `#landing`
  and `#ceiling` parts. Every one goes through the part function: an editable spline, then Extrude (mesh output), then
  Smooth.
* **No Editable Poly**: the text contains no `convertToPoly`, `Edit_Poly`, `editable_poly` or `Editable_Poly`, and
  Collapse gives Editable Mesh.
* **Furniture is still Box primitives** on its kind layers.
* **The Ceilings layers are hidden after Build**, and the script's notes say so.
* **The mock interpreter**: the script runs with no error and the expected object count **per kind**. The test's
  stand-in parts carry an Extrude with `amount` (as `bank_test/test_bank_maxscript.py:653`), and the real
  `updateLevels` is called:
  * with the upper level raised 0.30 m, every tread's and landing's base and height are scaled by the storey ratio:
    the top tread's top equals the new upper level − one new riser, ± 1 mm;
  * with the upper level lowered 0.50 m, no cut wall piece is higher than the stair's underside over it;
  * ceilings keep their height above their floor's level.

  R3 may add a test-only extension of the mock in its own test files; the prototype's mock is not changed.
* **No refusals**: none for "a hole touches the outline" or "two holes touch".
* **The two goldens** are unchanged (RA-1).
* **The header** says the stair's risers ("21 risers of 0.186 m") on the house, and notes that the treads keep their
  storey when levels change.

### RA-12 The owner's path through the screens (must)

`tests/e2e/rooms.spec.ts`, in the e2e suite (the Playwright config's own servers, never 5710 / 8710) with a fresh store
and the real worker. Every project a spec makes is saved under an `e2e-` id. A spec that applies a fixture merges only
its layers, floors and furniture into the settings the draft already has, never its options.
1. **The house, as a new project**:
   * New project → upload `Test Sukhumvit Residence.dwg` → Files (`minor`, units confirmed) → Layers (the house's
     roles: the selects for three of them, the rest merged from the fixture).
   * Floors: the two boxes, the levels picked from the level tags, walls 3.90 / 3.50, ceiling heights typed 3.00 / 2.90.
     The line says the draft is built the new way; the draft's options have `slabs: 'network'` before Build.
   * Build → Check: the page's counts (rooms, holes, stairs) equal the overlay's; pixel probes show a room tint, a
     hatched hole and the stair's walking line (`plan-canvas.spec.ts` holds the pixel checks).
   * Name the living room "Living" with the room panel → the fix is drawn as waiting → Rebuild → the overlay names it.
   * Save → `version.json` says `built-model/2` → the version opens in the viewer.
   * Walk: from the main stair's bottom, W until the foot has risen three risers, then the stair probe; the floor
     button "upper" is marked.
   * The Max download contains `#tread`.
2. **A project saved before this milestone**, on the reference building (2.5):
   * the set-up builds it the earlier way through the API, saves version 1, and takes the three option keys out of
     that version's recipe in the spec's own temp store. A recipe saved before this milestone is exactly a recipe
     without those keys;
   * New version → the same drawing → Build, **without opening the Floors step**;
   * the Build and Check steps show the line "built the new way"; the stair is climbable and the room behind the gap
     has its flag; Save → `built-model/2`; version 1's files are unchanged.

   At RI the same path is walked by hand on the real `house-upload` of 9 Nov in the acceptance store's copy: the plate
   contains (26.2, 11.1) and the main stair climbs (RA-1 checks that case with the real worker).
3. **The fixes, on the reference building** (one test, one drawing, 2.5):
   * its 2.9 m opening in an outside wall gives a `slab-gap` flag with its mouth → **Close it here** → Rebuild → the
     flag is gone and the room has its floor;
   * "No floor here" on one room → Rebuild → it is a hole;
   * its second stair, drawn with no word, arrow or break line, has the `stair` flag "which end is the bottom was not
     found" → **This is the bottom** and a click on the bottom tread → Rebuild → the stair is climbable → **Keep as
     lines** → Rebuild → no treads, the lines are back;
   * its door-sized gap shows a dashed doorway closing and a `doorway` flag → **Not a doorway: one room** → Rebuild →
     the two rooms are one;
   * **Remove** in *Fixes on this floor* takes a fix back.
4. **The bank with the defaults**, through the API (an integration test, not the screens a second time): it saves a model
   byte for byte equal to the bank's new-rule reference (RA-15).
5. **The earlier way through the screens**: `upload.spec.ts` (the upload's A-7) reads the draft's options (new), chooses
   "the earlier way" in the fold on the Floors step, reads the options again (old), builds, and keeps every
   byte-for-byte check against version 2.
6. **Text only**: no dialog and no page error in any of these; drawing texts and room names show as text (the hostile
   DXF of A-7 also gets a room name with `<img ...>` through the room panel).

Under the mock API (`WT_SERVE=web`) the spec covers only that the panels and tools write the right fixes into the
settings. Points 1 – 3 and 5 need the real worker.

### RA-13 Fixes survive a rebuild and a re-upload (must)

* **Rebuild**: a closing line, a removed closing, a room fix (a name, "no floor", "floor here", "no ceiling", "it is
  outdoors"), a stair fix (`bottom`; `use: 'lines'`; `use: 'climb'`) and a set-aside with "the floor runs past it" are
  applied in the next run, and the report lists each as matched.
* **Set aside keeps the floor**: a single line that closes a room, set aside, leaves the plate as it was; with "the
  floor runs past it" the room opens.
* **Re-upload**:
  * the same DWG uploaded again matches all of them;
  * a synthetic re-export with other handles and 2 cm of drift matches all of them (they are points);
  * a fix whose point lies in no room, area or stair gives `fix-unmatched` and changes nothing.
* **Units**: a units change rescales their points (`adopt.rescale`).
* **API checks**: the API refuses a room name over 200 characters and more than 5,000 "other fixes" in all (422).

### RA-14 Times (should)

| Measure | Target |
|---|---|
| build run with the new rule (`job.json`) | bank ≤ 45 s, house ≤ 60 s, old suite ≤ 90 s, tower ≤ 90 s, new suite ≤ 90 s, and each no more than 30 s over its old-rule build |
| peak memory of any child | ≤ 1.5 GB |
| first view (the CPU part, Node: parse, checks, `buildScene`) | within 10 % of today's on the old versions; ≤ 0.35 s on the tower's new-rule model |
| a walk move on a stair with both floors' furniture boxes (Node) | ≤ 2 ms |
| frame rate in Edge on this laptop with its GPU, Walk on the house's and the tower's new-rule versions, ceilings on | ≥ 30 fps, measured by a script: Edge started without the software-drawing flags, timed with `tests/e2e/lib/fps.ts`, the number written to the acceptance result |
| `npm run test:builder` | ≤ 15 min (one new-rule build per drawing, shared by the session's tests) |
| the new browser specs | ≤ 10 min |

### RA-15 Determinism and the new references (must)

* **Built in two processes, the same bytes**: each new-rule build (bank, house, old suite, tower, new suite) gives the
  same `model.json`, CSV, `stages.json`, top view and Max script (fixed date) in two child processes with different
  `PYTHONHASHSEED` values. Its `version.json` says `built-model/2`.
* **Every new-rule model has `stairways`**, an empty list when no stair climbs.
* **The references are pinned** in `services/builder/tests/test_r_rooms_golden.py`: the five models' sha1s, the bank's
  new-rule CSV, and per floor the summary rows (rooms, named rooms, plate area, holes, climbable stairs). RI pins them
  as provisional when its runs pass; every move during the review is explained in `contract-issues/RR.md`.
* **The old-rule references** stay pinned (RA-1).

### RA-16 Every test suite passes; nothing else moved (must)

* **Section 3's commands** pass, with only the changes it lists, and none skipped.
* **The prototypes' own tests** pass unchanged.
* **Outside `app/`** no file listed in `docs/rooms/reference/outside.txt` changes (the listing R0 takes at its start,
  without the detector's two fifth-drawing folders, `.claude/` and the documents the main session edits), and there is
  no new `__pycache__`.
* **Nothing is deployed.**

### RA-17 The staff's fix time (should)

The plan's gate asks for a fix time of 30 minutes a project. Measured by hand through the screens at RI, and again by
the review's staff-path reviewer, on the two drawings where fixes decide the result (the tower and the new suite):
* the flags to check before and after;
* the fixes made (clicks and rebuilds);
* the minutes until every room is closed or answered: target **30 minutes**;
* the same for a second version of each with the fixes carried over: target **15 minutes**.

The numbers go into `GAPS.md`.

### RA-18 A missed doorway does not cost the floor (must)

* **Synthetic** (unit): a doorway of 0.8, 1.2 or 1.88 m with no door found, between wall ends of equal thickness and of
  0.10 m against 0.20 m, is closed and the room keeps its floor. A gap of 2.5 m is not closed by this rule and gets a
  `slab-gap` flag with its mouth.
* **Each door of the bank and the house undone in turn** (heavy; the door's span is taken out of the records and what is
  built in its footprint out of the walls):
  * bank L2: plate0 loses less than 2 m² for every one of its 25 doors and passages (8 lost 25 – 107 m² under the
    first version; the trial of the rule: 0);
  * bank L1 and the house's ground floor: at most one door each loses more (the trial: `L1-018`, `ground-032`), and
    each one that does carries a `slab-gap` flag whose mouth lies within 0.3 m of the undone doorway;
  * the house's upper floor: none loses more than 2 m².
* **With every door found** (should): no doorway closing on the bank; at most 2 per floor on the house, the tower and
  the old suite (the trial: 2 / 0, 2 / 1, 1); no ring and no room count differs from a build without the rule.
* **A wall drawn across a doorway, set aside** (unit): the two rooms stay two, the plate is unchanged, and no wall part
  stands in the doorway.
* **The new suite** (should, reported): with the 15 lines across its doorways set aside, as on 11 Nov: the doorways
  found, the rooms and the plate.

## 2. Test plan

### 2.1 Builder (`npm run test:builder`; markers `heavy` and `worker` as U-3.5; `WT_REF` read-only; `WT_ACCEPTANCE=1` for the costly runs)

| Owner | Tests |
|---|---|
| R0 | `test_r_old_rule.py` (every output of the five old-rule builds; green before the builders start; nobody else edits it); the contract fixtures against `contracts.py`, with the rooms block of DESIGN R-12.3 (`test_contracts.py` extended); the old fixtures' bank build still matches `build-result.bank.json`'s key structure; the tracer: a two-floor drawing with one straight stair end to end through `build()`; `tools/rooms/make-reference-building.py` makes deterministic DXFs; session-wide fixtures in `conftest.py` (one new-rule build per drawing) |
| R1 | the network, the bridges, the doorway closings, the unfloored areas, rooms, names, terraces, X marks, holes, kept stair voids, plate bounds, ceilings and the fixes, as listed in DESIGN R-14; RA-3, RA-4, RA-5 and RA-18 asserted on the five drawings (heavy); the shoulds reported |
| R2 | the stair reader and builder as listed in DESIGN R-14; RA-9's two tables (heavy); the reference building's contract test |
| R3 | Max: the three kinds, the hidden Ceilings layers, the storey statement, `__STOREYFIT__` (present with treads, absent without: both goldens unchanged), the mock with real amounts, no Poly anywhere; the top view with the new kinds (the bank's bytes unchanged); the legend; the replay facts and captions (1, 2, 3 floors; with and without stairs); the overlay's new fields through `check_file`; every new flag kind from the reference building's build result; `fix-unmatched` for the new fixes; the diff; `gap-report.py` with the new rows |
| RI | the five drawings end to end with the `*-rooms` fixtures; determinism in two processes; `test_r_rooms_golden.py` |

### 2.2 API (`npm run test:api`, also with `WT_INTEGRATION=1`; R5)

* **Old settings**: an old `project-data.json` without the new keys validates and comes back with the old values.
* **Which rules a draft gets**: RA-1's four cases, with the real worker.
* **New fields**: their ranges (ceiling height 0.5 – 20 m); `SetAside.floorPast`.
* **Combinations**: the illegal ones (`closed-rooms` with `auto` or `climb`) answer 422 with a plain message.
* **Fix limits**: the count cap and the name length.
* **Rescale**: of the new fixes' points.
* **`create_version`**: writes `built-model/2` for a model with `stairways` and `/1` otherwise. The seeded versions'
  counts are unchanged.
* **Checks**: the v2 schema and rules in `builtmodel.validate` agree with the viewer on the broken-model corpus
  (written by R0); `check_file overlay` checks the new fields.
* **OpenAPI**: re-exported byte-identical. `tools/check-openapi-additive.mjs --base 66b4c06` passes, and fails on its two
  hand-made breaking cases (a required property added; a property's type changed).
* **Integration**: with the real worker, a new-rule build of the reference building; the bank with the defaults (RA-12
  point 4).

### 2.3 Viewer and web unit tests (`npm run test:unit`, vitest)

* **R0**: the walk-parity golden test (RA-2); the v2 parser rules on the broken corpus.
* **R4 (viewer)**:
  * first, the tracer climb: in Node on the reference building's model, up onto the slab and down again, reported
    before anything else;
  * `buildScene` (surfaces; treads single-sided and not colliders; ceilings merged per floor, late, visible only in Walk
    and Ghost);
  * the walker (RA-10's Node part);
  * the floor naming and its hysteresis; the easing;
  * Build settings' storey scaling of treads and cut walls (a raised upper level keeps the stair climbable); ceilings
    keep their height;
  * Ghost → Walk landing on a tread; double-click on a landing;
  * the probe's `foot`, `ground`, horizontal `walk`, and the rule of DESIGN R-9.8;
  * the walk-parity golden passes at every point.
* **R6 (web)**:
  * the line and its button on the Floors, Build and Check steps; the checklist's warning line;
  * the Floors step: ceiling heights (placeholder = the default), the fold and its two controls;
  * the Build and Save steps' three counts;
  * the Check step: rooms, holes, stairs, closings and unfloored areas drawn from the overlay fixtures; the three
    ticks; "Close it here", "It is outdoors", "Not a doorway" and "Draw a line" write the right fixes; the room panel
    and the stair panel; the fixes list and Remove; "waiting for Rebuild"; each new flag kind has its text; the
    Heights panel's ceiling height; the set-aside tick;
  * the canvas: the draw-line tool with snapping, the Rooms and stairs tool (stair, closing, room, point), the local
    frame (a plan at y = −3,500 m picks the same);
  * the mock API's new overlay fixtures.

### 2.4 Browser (Playwright, installed Edge, one at a time through the Edge lock)

* **R6**:
  * `tests/e2e/rooms.spec.ts` (RA-12), with the test ids of `apps/web/src/build/testids.ts` and the `window.__plan`
    hook for canvas clicks; first under the mock (`WT_SERVE=web`: the fixes written), then with the real worker;
  * `tests/e2e/plan-canvas.spec.ts`: pixel probes on the house-rooms overlay (a room tint, a hatched hole, a dashed
    closing, the stair's line; each tick switches its layer off);
  * the change in `tests/e2e/upload.spec.ts` (RA-12 point 5).
* **R7**:
  * `tests/e2e/stairs.spec.ts` (RA-10's browser part and RA-8's ceiling checks), written against the reference
    building's offline file, made in the spec's set-up into its own temp folder, and run at integration on the
    house's and bank's new-rule offline files (`WT_ROOMS_OFFLINE_DIR`);
  * the `stairWalks` helper; `tests/e2e/lib/target.ts` and `upload-walk.spec.ts` for the new versions; `lib/fps.ts`'s
    scripted measure.
* **RI**:
  * `upload-walk.spec.ts` on the new-rule versions (RA-6) and on the eight old ones (RA-2);
  * every existing spec unchanged on a freshly seeded store (RA-2).

### 2.5 Fixtures (scaffold R0; owners after it in WORK_BREAKDOWN)

* **Settings**: `fixtures/upload/settings/{bank,house,suite,tower,suite-revit}-rooms.json` (R1 owns them after R0);
  `fixtures/upload/settings/recipes/{house,suite,tower,suite-revit}.json` (the saved versions' recipes).
* **The reference building**: one synthetic building made by one script, `tools/rooms/make-reference-building.py`. Two
  floors; an L stair with nosing pairs and a riser shared by the two plans; a second, straight stair drawn with no
  word, arrow or break line; a 2.9 m opening with no door in an outside wall; a door-sized gap between two wall ends; an
  X void; a terrace; two names in one room. Everything provisional is derived from it:
  * its DXFs (made at test time: the root `.gitignore` ignores `*.dxf`);
  * the v2 model `fixtures/models/rooms-reference.model.json`, with its presentation, and a tiny store made by
    `tools/rooms/make-fixture-store.mjs`;
  * a build result with every new report key and every new flag kind;
  * the overlay, and a FakeJobRunner run folder.

  The contract test (RA-9) keeps the builder's output and the model fixture within 1 mm.
* **Synthetic v2 models** for the walker: `fixtures/models/stairs-{straight,L,U}.model.json`.
* **Stair drawings for the reader's tests**, made at test time:
  `tools/rooms/make-stair-dxf.py straight|L|U|two-floor|no-direction|down-up-pair|split-level` (nosing pairs, a word, an
  arrow with a dot, a break line that cuts a riser in two, hidden continuations with one riser missing, a deeper first
  step, a `DOWN` and an `UP` flight side by side, a floor between the stair's two floors). `straight` is also the
  tracer's drawing.
* **The v2 broken-model corpus**: `fixtures/models/broken/` (one case per new rule, written by R0 with the three
  checkers).
* **The house-rooms overlay**: `fixtures/upload/overlay/house-rooms.overlay.json`, provisional from the trial, replaced
  at the smoke step (WORK_BREAKDOWN RI-0).
* **The old-rule outputs**: `fixtures/rooms/old-rule.sha1.json`.
* **The answer keys**: `fixtures/rooms/keys/{bank,probes,house,suite}.json`.
* **The walk-parity golden**: `packages/viewer/test/fixtures/walk-parity.json`, with the script that made it
  (`packages/viewer/test/tools/record-walk-parity.ts`).
* **The references**: `docs/rooms/reference/versions.sha1`, `outside.txt`.

## 3. Keeping the earlier checks passing

Every count is stated with its environment. Nobody writes `dist/` while the builders run in parallel: a builder that
needs the viewer template builds it into its own temp folder (`--outDir`, as
`packages/viewer/test/harness/core/make-e2e-offline.mjs:5-9`).

| Command | Baseline (9 Nov, after the final check's fixes) | After this milestone |
|---|---|---|
| `npm run check:pins` | 28 npm, 28 API pip, builder 19, LibreDWG 64 files | the same (no new library) |
| `npm run typecheck` | 0 errors, 5 configs | 0 errors, the same 5 |
| `npm run test:unit` | 851 | 851 + new. Changed on purpose, by R0, because they list every kind or toggle: `packages/viewer/test/unit/core/visibility.test.ts:37, 41`, `test/unit/model/presentation.test.ts:103`, `apps/web/test/plan/colours.test.ts:12, 50` |
| `npm run test:builder` (with `WT_REF`) | 722 | 722 + new; none skipped. Changed on purpose, by R0: `test_contracts.py` (it also reads the rooms block), `conftest.py`, `kit.py`, `test_u3_helpers.py` (the new suite's cache). The bank golden, summary and key-structure tests are unchanged |
| `npm run test:api` (+ `WT_INTEGRATION=1`) | 471 | 471 + new. Changed on purpose: `test_openapi.py`'s component schema count (the three new fix schemas); `test_builtmodel.py`'s corpus (the v2 cases); every test that builds a new version from a pre-milestone recipe and compares bytes writes the old values first (R5 lists them in its report) |
| `npm run gen:api` | no change | regenerated once by R0 (additive), then no change |
| `node tools/check-openapi-additive.mjs` | ok against `9eb2d58` | ok against `66b4c06` with the new optional-property rule, and still ok against `9eb2d58` |
| `npm run build` | template 783 KB, 5 offline files from `app/data` | the same 5 offline files; the template grows by the climbing code (tens of KB). The reference building's offline file is made in the spec's set-up, not here |
| `npm run seed` | 5 stamps | the same 5 stamps |
| `npm run test:e2e` | 279, with `WT_UPLOAD_OFFLINE_DIR` holding the eight old uploaded versions' offline files (48 of the tests) | 279 + new specs, run with `WT_DATA_DIR` and `WT_OFFLINE_DIR` on a freshly seeded temp store. Changed on purpose: `upload.spec.ts` (the fold's choice, options read before and after), `packages/viewer/test/harness/core/viewer.spec.ts:74, 200` (the toggle and kind sets) |
| the prototypes' own tests (view modes 127, bank 49, suite 37, house openings 13, house furniture 29, hotel 56, boxes 87; Max checks 137 / 151 / 196; the detector 139 / 143 and 54 / 54) | all pass | unchanged, one at a time under the Edge lock; `furniture/test_furniture_max.py` still not run (it rewrites prototype files) |
