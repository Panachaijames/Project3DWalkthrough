# Gaps: the new rule (rooms, slabs, stairs) against the old one, drawing by drawing (11 Nov 2026)

Written by the integration step RI (part RI-B; docs/rooms/WORK_BREAKDOWN.md RI item 4) from the acceptance result
`%TEMP%\wt-ri\acc\rooms-result.json`, which `node tools/rooms/acceptance/run.mjs --tmp %TEMP%\wt-ri\acc` writes (step
`rooms-checks`, from the records of the other steps). **Provisional**: the review step RR runs everything again from a
clean start and may move what is here.

**How the versions were made.** Every new-rule version below went the app's own way: the drawings' DWGs uploaded in parts
to a served API (`node tools/run-api.mjs --port 8748`) over the acceptance store (`%TEMP%\wt-ri\acc\data`, a copy of the
upload milestone's acceptance store, so the 9 Nov versions and the new ones sit side by side), prepared and built by the
real worker, with the settings fixtures `fixtures/upload/settings/<name>-rooms.json` (the new rule: `slabs: network`,
`ceilings: auto`, `stairs: climb`; the house with its ceiling heights 3.00 / 2.90 m; the new suite with layer 0 as wall)
and **no fix**, saved as version 1 of a new project. They are compared with the same drawing's 9 Nov version (the old
rule), from the same store. The tower and the new suite were also built a second time with every item of their
single-line flags set aside, the state staff will leave them in.

**The classes**, as in the upload milestone's gap report: **option now** (staff can answer it on the Check step today),
**option later**, **check-and-fix now** / **later**, **accepted difference** (by design).

Areas are m². "Plate0" is the floor plate before its holes (report `slab.plate`, ACCEPTANCE RA-4's figure); "slab" is
what the model finally holds (the slab parts, after the holes and the 3 cm edge). The old rule's figure is its slab parts.

## 1. In short

* **The floors that were missing are there.** The plates grew where the old rule left whole parts of a floor bare: the
  tower 445 / 504 -> 843 / 705 m² of slab, the old suite 113 -> 476 m², the new suite 35 -> 277 m², the house's ground
  floor 428 -> 513 m². Every plate0 is inside its must bounds and its should range (RA-4).
* **The holes are the drawn ones**: the lift shafts, the house's two marked voids, the stair wells; small marks and the
  grid cut nothing (RA-5).
* **Stairs climb** on the bank (21 risers of 0.176 m), the house (21 of 0.186 m) and the tower's stair A (20 of 0.200 m).
  The stairs that stay as lines say why, and most can be answered by staff on the Check step (sections 2.2, 4, 5).
* **The walks.** Every walk probe that found "no floor" on 9 Nov now starts on floor, but the house's garden gate
  (accepted: outdoors) and one side of one door of the new suite (section 3). The bank's new version passes every wall,
  door and glass probe, as its old one does. The doors and glass probes that still fail failed on 9 Nov too, or could
  not be tried then for want of floor: none of them is caused by the new floor (sections 3.2, 5).
* **What staff still have to answer** (section 5): the house's two areas with no floor (16.8 and 28.8 m²) and its service
  stair; the old suite's garden side inside the balustrade (161 m²); the tower's stair B and its assumed storey; the bank's
  north stair. None of them is a fault of the rule; each has a button.
* **One thing to check and fix now** (section 5.6): on the house's L-shaped main stair, a stair fix put at a point inside
  the stair's drawn outline found no stair, because the outline cuts across the inside corner of the L. The point the
  Check step itself writes still matches, but only by about a centimetre.

## 2. Per drawing, the new rule against the old

Stamps: new rule (version 1 of the project named) against the 9 Nov version.

| Drawing | New rule | Old rule (9 Nov) |
|---|---|---|
| bank | `bank-rooms` v1, `54ef1ac240bb`, built-model/2 | `bank-sampeng` v3, `c3a9408304a2` |
| house | `house-rooms` v1, `c7824bca6008`, built-model/2 | `house-upload` v1, `1c07bfeef580` |
| old suite | `suite-rooms` v1, `ed7774c64b9b`, built-model/2 | `suite-upload` v1, `205e9c2c46e8` |
| tower | `tower-rooms` v1, `3d25cdf722fb`, built-model/2 | `tower-upload` v1, `91414f408cb2` |
| new suite | `suite-revit-rooms` v1, `424cc8cabd45`, built-model/2 | `suite-revit` v1, `1d90d91ef949` |

### 2.1 Floors, holes, rooms, names, ceilings

| Floor | Slab, old -> new | Plate0 (RA-4 should) | Holes cut (new) | Rooms (new) | Names old -> new | Ceilings (new) |
|---|---|---|---|---|---|---|
| bank L1 | 237.4 -> 234.5 | 235.8 (234 - 241) | lift shaft 3.17 | 15 | 7 -> 12 | 1 piece, 223.5, 2.98 m up |
| bank L2 | 285.0 -> 285.2 | 295.7 (293 - 303) | stair well 7.13, the next stair's footprint 2.28, lift shaft 3.13 (old: stair 9.28, lift shaft 3.13) | 14 | 11 -> 11 | 1, 239.7, 2.98 |
| house ground | 428.0 -> 513.3 | 507.7 (495 - 530) | none (3 small X marks reported) | 22 | 0 -> 0 | 2, 418.3, 2.98 |
| house upper | 421.1 -> 409.1 | 450.9 (435 - 460) | void 26.12, stair hall 16.62, stair well 4.39, the service stair's opening 3.93 | 24 | 0 -> 0 | 1, 446.2, 2.88 |
| old suite | 112.8 -> 475.5 | 471.1 (460 - 480), with 53.2 of terrace | none (5 small marks reported) | 18 | 16 -> 16 | 3, 412.5, 2.68 |
| tower L29 | 444.7 -> 842.7 | 848.7 (840 - 875) | 4 shafts: 2.81, 3.06, 3.06, 3.06 | 32 | 0 -> 0 | 1, 806.2, 2.98 |
| tower L30 | 504.4 -> 705.1 | 739.8 (725 - 765) | stair A's well 11.52, stair B's opening 17.24, 4 shafts 2.81, 2.78, 2.78, 2.78 | 34 | 0 -> 0 | 1, 728.6, 2.98 |
| new suite L1 | 35.1 -> 276.7 | 274.2 (262 - 280) | none (1 small mark) | 17 (+3 enclosed shapes) | 6 -> 8 | 1, 254.1, 2.68 |

The ceiling heights are the ceiling's underside (the height less the 2 cm plate): 3.00 m on the bank and the tower,
3.00 / 2.90 m typed on the house, the default 2.70 m on the two suites.

### 2.2 Stairs

| Drawing | Climbable (new) | Kept as lines (new), and why | Old rule |
|---|---|---|---|
| bank | `S1` L1 -> L2, kind L, 21 risers of 0.176 m, 17 treads, 3 landings (direction from Level 1's cut) | the north stair on both levels: "its top does not stand on a floor plate" (check); Level 2's next stair up: "leads to a floor that is not in the model" (info) | 16 two-riser `step` parts on L2; no climb |
| house | `S1` ground -> upper, kind L, 21 risers of 0.186 m, 19 treads, 1 landing (direction from the walking line's arrow) | ST-05: "its 7 steps would rise about 1.0 - 1.5 m: no floor of the model is at that height" (info); the service stair ST-02 on both plans: "16 steps for 3.90 m give 0.24 m each ... A storey of 2.94 - 3.36 m would fit every stair between these floors" (check); 4 groups of three lines: "turning or curved steps: not built yet" (info) | lines only |
| tower | `S1` (stair A) L29 -> L30, kind U, 20 risers of 0.200 m, 18 treads, 1 landing (direction from the cut) | stair B on both plans: "18 steps for 4.00 m give 0.22 m each ... A storey of 2.80 - 3.78 m would fit every stair between these floors" (check); today's opening over it stays (17.24 m²) | lines only |
| old suite, new suite | none (one floor) | none | none |

No new-rule model has a two-riser `step` part. The bank's toilet walls under flights 3 and 4 are cut to the stair's
underside (5 `stair-clash` cuts, one flag).

### 2.3 Flags, before and after

| Drawing | Old rule (9 Nov) | New rule |
|---|---|---|
| bank | opening 8, room-label 7, plate-dropped 2, rail-left-out 3 | opening 8, room-label 2, room-names 3, rail-left-out 2, stair 3, stair-clash 1 |
| house | opening 35, single-line 13, room-label 3, plate-dropped 5, grey-furniture 8, units 1 | opening 35, single-line 13, room-label 3, grey-furniture 8, units 1, slab-gap 2, doorway 2, stair 7 |
| old suite | opening 13, single-line 7, lost 4, rail-left-out 2, plate-dropped 9, grey-furniture 13 | the same less plate-dropped, plus slab-gap 2, room-names 2, doorway 1 |
| tower | opening 27, single-line 39, plate-dropped 23, grey-furniture 11 | opening 27, single-line 39, grey-furniture 11, doorway 3, stair 2 |
| new suite | opening 21, room-label 2, plate-dropped 6, grey-furniture 4, units 1 | opening 26, single-line 42, grey-furniture 4, units 1, room-names 1, doorway 6 |

The old rule's `plate-dropped` flags (a large area with no floor) are gone on every drawing: the areas they named are
floored or now flagged as `slab-gap` with an answer to give. The new suite's 42 single-line flags come from layer 0 being
built as wall (`suite-revit-rooms.json` adds it to the A-12 recipe of 9 Nov, which had none); its 5 more openings are
what the door finder finds with those walls.

## 3. The walk checks (RA-6)

### 3.1 In the builder: is there floor in front of the probes that had none on 9 Nov?

The probes of `fixtures/rooms/keys/probes.json`, each side that had no floor on 9 Nov: floor at some point 0.4 - 0.9 m in
front, and a room within 2.5 m (the overlay's plates and rooms, sheet m).

| Drawing | Probes and sides | Floor 0.4 - 0.9 m in front | Not on floor |
|---|---|---|---|
| house (must) | `ground-004`, `-006`, `-018` (the side with no floor on 9 Nov: the living room), `upper glass 44` | 4 of 4 | `ground-034` (both sides): the garden gate in a free-standing wall, out of the must list since 11 Nov (R1.md D-2): **accepted** |
| old suite (must) | `suite-025`, both sides | 2 of 2 | - |
| tower (must) | `L29-001`, `-016`, `-025`, `-028`, `L30-033` (both sides), `L30-032`, `L30 glass 24`, `L30 glass 26` | 13 of 13 | - |
| new suite (should) | `L1-004`, `L1-008`, `L1-010`, both sides | 5 of 6 | `L1-004`'s south side (24.4, 0.5): see 5.5 |

With the single-line flags set aside (the tower: 39 flags, 133 items; the new suite: 42 flags, 59 items): the same
answers (tower 13 of 13; new suite 5 of 6), and every plate0 still inside its range: tower 848.5 / 739.6, new suite 274.3.

### 3.2 In the browser (upload-walk.spec.ts, `WT_ROOMS_PROBES=1`, the new-rule offline files)

`upload-walk.spec.ts` on the seven new-rule offline files (made with `dist/offline-template`), headless Edge, the bank a
must file and the others should files: **49 passed** (2.2 min). Every file loads with its stamp, starts, shows its floors,
and no random wall walk goes through a wall.

| File | RA-6's probes (floor 0.4 - 0.9 m in front, then the walk) | Doors | Glass |
|---|---|---|---|
| bank-rooms v1 (must) | not a probe drawing | **39 of 39** | **30 probes + 14 random parts, all pass** (as the old version: 80 wall spots, 39 doors, 44 glass) |
| house-rooms v1 | **4 of 4 stand on floor** (`ground-034` recorded: no floor either side); from the living room's new floor, `ground-004`, `-006`, `-018` then stop 0.30 m short of the door line; `upper glass 44` has floor but no start spot with 0.25 m of room | 4 failing of 32 | 3 failing of 63 probes (+ 20 random parts) |
| suite-rooms v1 | **`suite-025` stands on floor**, walked through 0.90 m both ways | **15 of 15** | no glass |
| tower-rooms v1 | **8 of 8 stand on floor**: the five doors walked through 0.90 m both ways; `L30-032` and `L30 glass 24` stop 0.35 m short, as glass should; `L30 glass 26` has floor 0.5 - 0.9 m in front but no start spot | 2 failing of 44 | 6 failing of 41 probes (+ 20) |
| tower-aside v1 (single lines set aside) | the same 8 of 8 | 2 failing of 44 | 6 failing of 41 (+ 20) |
| suite-revit-rooms v1 (should) | `L1-008`, `L1-010` walked through 0.90 m both ways; **`L1-004`'s south side has no floor** (no start) | 1 failing of 14 | 8 failing of 29 probes (+ 10) |
| suite-revit-aside v1 | the same | 1 failing of 14 | 8 failing of 29 (+ 10) |

Against the 9 Nov walks of the same drawings (`docs/rooms/reference/upload-walk-9nov/`):
* **Gone**: every "no start: no floor" of RA-6's probes but `ground-034` (accepted) and the new suite's `L1-004` south side.
  The tower's doors went from 7 failing to 2, the old suite's from 1 to 0, the new suite's from 3 to 1.
* **The same as on 9 Nov** (failures the new floor did not cause): the house's `ground-004`, `-006`, `-018` stopped 0.45 m
  short from their other side on 9 Nov and still do (now they also start from the living room and stop 0.30 m short); its `ground
  glass 18` and `upper glass 44`; the tower's doors `L29-026`, `L30-034` and its glass `L30-032`, `L30 glass 19`, `24`,
  `26`.
* **New, because more probes now have floor to start from**: the house's `ground-040` (from the newly floored side the
  walker stops 1.0 m out, at another glass part 0.95 m away); the tower's `L29 glass 9` and `L30 glass 17`; the new
  suite's door and eight glass probes (none of them could start on 9 Nov).

## 4. The tower's storey window, and stair B's counts

* **Stair B** is read on both plans as a U stair: L29 10 + 8 risers (flights 1.22 and 1.35 m wide), L30 8 + 8 (+1).
  Its 18 risers over the assumed 4.00 m storey give 0.222 m each, over the 0.21 m a stair is built with, so it stays as
  lines with a `stair` flag (check) on each plan: "18 steps for 4.00 m give 0.22 m each. The drawing may not show every
  step, or the levels may be off. A storey of 2.80 - 3.78 m would fit every stair between these floors." Today's opening
  over it stays in L30's floor (17.24 m², RA-5's 17 ± 1).
* **The storey window 2.80 - 3.78 m** is the storey every stair between L29 and L30 would fit with risers of 0.14 -
  0.21 m: stair A's 20 risers fit 2.80 - 4.20 m, stair B's 18 fit 2.52 - 3.78 m. The tower's 4.00 m is an assumption
  (ACCEPTANCE: "L29 / L30, 0 / 4.00, assumed"): at 4.00 m only stair A fits; at any storey of 2.80 - 3.78 m both would.
* **Stair A** climbs at 4.00 m: 20 risers of 0.200 m (RA-9's should).
* **Class: option now.** Staff can type the real storey on the Floors step (the window says which heights fit both), or
  answer stair B with "Climb" (a riser up to 0.25 m is allowed then: 0.222 m fits). Check the storey with the drawings'
  sections when the owner has them: **check-and-fix later** for the assumed level itself.

## 5. Every difference, classed

### 5.1 Bank

| Difference | Class |
|---|---|
| Level 1 now has its lift shaft cut (3.17 m²); the old rule floored it | accepted difference (RA-5) |
| Level 2's stair opening is now the stair well (7.13 m²) plus the next stair's own footprint (2.28 m²), 9.41 in all, against the old 9.28 | accepted difference (RA-5: 6 - 12 m²) |
| 23 names, not 18: `ATM` three times, `BA`, `BE` are names now (no letter limit) | accepted difference (R1.md D-1, RA-7) |
| 4 of the 12 written areas are more than 15 % off their room: MEEETING 4 PAX 8.2 against 10.0 m², PANTRY 3.9 / 3.2, MALE TOILET 4.7 / 3.3, FEMALE TOILET 6.4 / 3.4 (8 of 12 within 15 %, the trial's count) | accepted difference (a written area that spans two cells, as on the drawing) |
| The north stair stays as lines: its top lies outside Level 2's plate | option now as R2.md D-2 says ("Floor here" on the area at its top, then it climbs; not tried here: that area is listed as "mostly stair", not flagged, so whether the fix finds it is for the owner's path to see) |
| Level 2's next stair up stays as lines: it leads to a floor that is not in the model | accepted difference |
| Against the prototype's slab (bank v2): L1 0.4 m² more and 3.2 m² less (the lift shaft), L2 0.6 / 0.5 | accepted difference (under 15 %) |

### 5.2 House

| Difference | Class |
|---|---|
| The ground floor gains 86 m² of plate (507.7 against today's 421.6): the glass-walled living room (81.6 m², it holds (26.2, 11.1)) and the floor around it | accepted difference (the purpose of the milestone) |
| An area of 16.8 m² on the ground floor (the terrace strip south of the living room, x 18.6 - 32.7) has no floor: the walls do not close there and no single mouth was found; `slab-gap` flag | option now ("Floor here" or "It is outdoors" on the Check step) |
| The upper floor's loop in front of the living room (28.8 m²; (26.7, 13.0) is not on the plate) has no floor; `slab-gap` flag | option now (as above; RA-4 asks for no floor there) |
| The upper floor's two X voids are cut (26.12 and 16.62 m²) and the stair well (4.39 m²) lies in the stair hall; the service stair keeps today's opening (3.93 m²); the duct and the three roof slots are listed, not cut | accepted difference (RA-5) |
| Against the prototype's slab: ground 41.7 m² more and 22.3 less (13 %); upper 18.4 more and 48.4 less (15.2 %, over 15 %): the 48 m² are the two X voids and the stair well, which the new rule cuts and the prototype's slab floors | accepted difference (RA-5's holes) |
| The service stair ST-02 stays as lines: 16 steps for 3.90 m are 0.24 m each; "A storey of 2.94 - 3.36 m would fit" | option now ("Climb" allows up to 0.25 m: RA-13's run shows it then climbs, 16 risers) |
| ST-05 stays as lines: no floor at its height | accepted difference |
| Four groups of three stair lines get an info flag "turning or curved steps: not built yet" | option later (R2.md D-3: no flag for a group with no flight and under six lines, if staff find them noise) |
| Two doorway closings (0.25 and 1.00 m) and four bridges on the ground floor, three bridges upstairs, each a dashed line on the Check step | accepted difference (info flags; "Not a doorway: one room" if one is wrong) |
| The living room's doors `ground-004`, `-006` (5.25 m wide) and `-018` (2.90 m): the walker now starts on the living room's new floor and stops 0.30 m short of the door line; from the other side it stopped 0.45 m short on 9 Nov already, and still does | check-and-fix later (something stands in those openings; not caused by the floor) |
| `upper glass 44`: floor in front now, but no spot with 0.25 m of room to start the walk | check-and-fix later |
| `ground-040`: from the newly floored side the walker stops 1.0 m out, at another glass part 0.95 m away; `ground glass 18` fails as on 9 Nov | check-and-fix later |

### 5.3 Old suite

| Difference | Class |
|---|---|
| The plate is 471.1 m², against 108.6 under the old rule: the villa's rooms inside the balustrade and 53.2 m² of terrace (two terraces with a door) | accepted difference (R1.md D-3: pinned 53.2 within 3 m²) |
| The garden side inside the balustrade (161.2 m²) and a strip of 7.2 m² have no floor: `slab-gap` flags; two fenced areas of 14.3 and 5.1 m² with no door found are listed, not floored | option now ("Floor here") |
| Against the prototype's hand-drawn slab (647.6 m²): 172.2 m² of it is not in the new plate (27 %, over 15 %): the garden side above, which the prototype floored by hand up to the balustrade | option now (the same "Floor here"); accepted difference for the rule (R-4.2 floors fenced areas with a door only) |
| **15 of 16 names** stand in the room the drawing means (the key points of `fixtures/rooms/keys/suite.json`, picked from the drawing's own room outlines on Defpoints and the areas the names write). The one that does not: `GYM&YOGA 33m2` is written inside the study's outline, 1.8 m west of the gym (the 31.3 m² room east of the wall, where `YOGA` stands), and goes with the study | option now (a room fix names the gym; RA-7's should, at least 13 of 16, is met) |
| Two rooms carry two names (`GYM&YOGA` with `Study & Meeting Room`; `Jacuzi` with `Master Bedroom`): `room-names` flags (info) | option now (a room fix names the room) |

### 5.4 Tower

| Difference | Class |
|---|---|
| The plates are 848.7 / 739.8 m² against 431 / 539 today: the rooms between the core and the curtain wall have floor | accepted difference (the purpose) |
| Four shafts cut per floor (2.78 - 3.06 m²); stair A's well 11.52 m²; stair B's opening 17.24 m² | accepted difference (RA-5) |
| Stair B stays as lines; the storey is assumed (section 4) | option now / check-and-fix later |
| Doorway closings 2 / 1 (1.31, 0.63; 0.46 m): RA-18's should (at most 2 per floor) | accepted difference |
| With every single-line flag set aside (133 items), the plates move by 0.2 m² and every probe stays on floor | accepted difference |
| The doors `L29-026`, `L30-034` stop 0.15 / 0.50 m short, as on 9 Nov (0.10 / 0.55) | check-and-fix later (not caused by the floor) |
| Glass: `L29 glass 9` and `L30 glass 17` fail now that they have floor to start from; `L30-032`, `L30 glass 19`, `24`, `26` fail as on 9 Nov (`L30 glass 26`: floor in front, no start spot) | check-and-fix later |

### 5.5 New suite (a should drawing: the door finder never saw it)

| Difference | Class |
|---|---|
| The plate is 274.2 m² against 192.6 today (35.1 of slab under the old rule) | accepted difference |
| Six doorway closings, five of them 0.15 - 0.78 m between armchairs drawn on layer 0, and the 1.99 m doorless opening closed | check-and-fix later (R1.md D-4: the door finder's round, plan next action 16) |
| 42 single-line flags (layer 0 built as wall); with their 59 items set aside: 3 passages instead of 8 found, 16 rooms instead of 17, the plate 274.3 m² | option now (set aside), and check-and-fix later (furniture on layer 0) |
| `L1-004` (a 0.90 m door at (24.4, 0.9)): its south side still has no floor 0.4 - 0.9 m in front (RA-6's should for this drawing is missed for this one side). The plate stops 0.08 m south of the door's middle: the strip beyond it, at the drawing's south edge, is not enclosed, and no area is flagged there, so staff have nothing to answer | check-and-fix later (a door with floor on one side only could raise a `slab-gap` flag, or get a landing; with the door finder's round, this being a drawing it never saw) |
| One door (`L1-019`, the door the walker stops 0.9 m short of from one side) and 8 of 29 glass probes fail the walk; on 9 Nov no probe of this drawing could start | check-and-fix later (should drawing; layer 0 built as wall puts furniture in the walker's way) |
| `BAR`, `BOH.` are names; the bed and the sofa corner are no rooms of their own | accepted difference (RA-3, RA-7) |
| `LIVING & DINING AREA`, `FOYER`, `BAR` in one room: `room-names` flag | option now |

### 5.6 Found by the acceptance runs

| Finding | Class |
|---|---|
| **A stair fix put at a point inside the house's main stair outline found no stair** (RA-13's first run): the outline the report and the overlay give for an L stair (`S1`: (21.64, 21.16), (19.67, 21.16), ..., (24.99, 24.25), (24.99, 23.15)) has no vertex at the L's inner corner, so its last edge cuts across the corner, and a point in that triangle, (21.96, 22.71), is inside the outline drawn on the Check step but 0.9 m from any tread, and the fix was unmatched ("A stair fix finds no stair": the builder matches a stair fix to the union of the stair's flights and landings, or within 0.3 m of it). The Check step's stair panel writes its fix at `pointIn(st.outline)` (`apps/web/src/build/CheckStep.tsx:271`); worked out by hand on this outline with the same algorithm (`plan/geom.ts` `insidePoint`), that point is (21.34, 22.71), about 0.29 m from the lower flight: inside the 0.3 m, so the staff's "Keep as lines" on this stair should match, but by about a centimetre. With the fix on riser 1's middle every stair fix matched | check-and-fix now (RR: the stair outline the report and the overlay give for an L stair should follow its treads; or the stair panel should write a point on a tread) |

## 6. The rest of the acceptance run, in short

* **The old rule is untouched (RA-1).** The upload milestone's eleven cases ran again through the API on a freshly seeded
  store: every saved model has its 9 Nov stamp (the bank both ways `c3a9408304a2`, the house `1c07bfeef580`, the old suite
  `205e9c2c46e8`, with outlines `2c85c67fe80f`, the tower `91414f408cb2`, the new suite `1d90d91ef949` and
  `467d3f8444c0`); the bank's CSV, top view, stages and its 27 Oct Max script are byte for byte the old ones. Every new
  project's draft got the new rule.
* **Fixes survive (RA-13)**: on the house, a set-aside with "the floor runs past it", two closing fixes, six room fixes
  and three stair fixes were each matched on the rebuild (the one put in no room raised "A room fix finds no room"); the
  same DWG uploaded again carried all six fix lists and built the same model, byte for byte; the API refused a 201-character
  room name and 5,001 fixes. "Climb" on the service stair made it climb (16 risers).
* **Times (RA-14)**: the new-rule builds took 5 - 24 s of work (the bank 9.3, the house 13.7, the old suite 5.2, the tower
  24.2, the new suite 13.9), at most 8.8 s more than the old rule's; no child process used more than 221 MB. In Edge with
  the laptop's GPU, walking on the stair with the ceilings on: 60 frames a second on the bank, the house and the tower (the
  screen's cap), the longest frame 17.2 ms. In Node: the first view 17 - 76 ms, a step on a stair 0.04 - 0.05 ms.
* **The same bytes twice (RA-15)**: each of the five new-rule builds, made in two separate processes, gave the same model,
  CSV, stages, top view and 3ds Max script; these are the pinned references (`services/builder/tests/test_r_rooms_golden.py`,
  provisional).
* **A missed door does not cost the floor (RA-18)**: every door of the bank and the house taken out in turn, the test of
  R1 passes on all four floors.

## 7. Not measured here

* RA-17 (the staff's fix time on the tower and the new suite): measured by RI-C through the screens, section 8.
* Pictures per floor against the prototypes' slabs (RA-4's should): the areas are above; no pictures were made.
* RA-14's first view of the OLD versions against the viewer of before the milestone (R4.md section 7): not measured.

## 8. The staff's fix time (RA-17), measured through the screens (RI-C, 12 Nov 2026)

**How.** The owner's path in Edge on 5748 / 8748 over a copy of this store (`%TEMP%\wt-ri\ric\path-data`), driven by a
script through the screens only (`%TEMP%\wt-ri\ric\scripts\owner-path-rooms.mjs tower|suite`: clicks, typing, the file
picker; the API read only to wait for runs and to read the overlay): new project, the DWGs uploaded, Files, Layers (the
fixture's roles with their selects), Floors (keys, names, levels, walls typed), Build, then **the timed part, from the
first Check view**: every flag of the kinds that concern rooms, floors and stairs (`single-line`, `slab-gap`, `doorway`,
`stair`, `room-names`) looked at with its **Show** button; each `single-line` flag's items set aside (**Select the
items**, **Set aside**), as GAPS 5.4 / 5.5 class them ("option now"); `doorway`, `stair` and `room-names` flags left as
built; Rebuild; until no area is left without floor or answer. Then Save, **New version** with **Use the files of v1
again**, Build, Check, Save. The opening and grey-furniture flags (the upload milestone's) were not worked.

**A script is faster than a person**: the scripted minutes are the clicks and the builds. The staff estimate adds
20 s to read each flag looked at and 3 s a click to the measured rebuild waits; it is an estimate, not a measurement.

| | Tower (`L29.dwg`, `L30.dwg`) | New suite (`presidential suite_layout.dwg`, office `dwp-revit`) |
|---|---|---|
| Set-up before the Check step (upload, reading, Layers, Floors, first build) | 0.9 min (reading 17 s, build 29 s) | 1.0 min (reading 31 s, build 19 s) |
| Flags before | opening 27, single-line 39, grey-furniture 11, doorway 3, stair 2; rooms 32 / 34 | opening 26, single-line 42, grey-furniture 4, units 1, room-names 1, doorway 6; 17 rooms |
| Rooms not closed or answered after the first build | **none** (no `slab-gap` flag, no unfloored area) | **none** |
| Fixes made | 39 flags set aside (133 items); 44 flags looked at; 122 clicks; 1 rebuild (56 s) | 33 flags set aside (59 items: some flags share items); 49 flags looked at; 124 clicks; 1 rebuild (19 s) |
| Flags after | opening 26, single-line 1, grey-furniture 11, doorway 3, stair 2; rooms 32 / 34 | opening 21, single-line 6, grey-furniture 4, units 1, doorway 6; 16 rooms |
| Minutes until every room is closed or answered (target 30) | 0 (closed at the first build); the flag review: **1.6 min scripted, about 22 min estimated** | 0; the flag review: **1.7 min scripted, about 23 min estimated** |
| Model | `600a29f95972` (RI-B's `tower-aside` `f6e6fcdf4725` but for the project's `photoName` and `maxPrefix`, not typed here) | `424cc8cabd45` before (= the pinned new suite), `6a0c916176a3` after (= RI-B's `suite-revit-aside`, byte for byte) |
| Second version, the fixes carried over (target 15) | 133 set-asides carried; built in 39 s; the same model; nothing to answer: **0.8 min scripted** (about 2 min for a person) | 59 carried; 18 s; the same model; nothing to answer: **0.4 min scripted** (about 2 min) |

**Left after one pass** (option now, not worked here): 1 (tower) and 6 (new suite) `single-line` flags that were not in
the first build's list: lines whose partner face was among the items set aside flag on the next build, so a person makes a
second pass (2 or 12 more clicks and one more rebuild). The doorway closings (3 and 6) stay, as GAPS 5.4 and 5.5 class
them. Records: `%TEMP%\wt-ri\path\{tower,suite}.json` and their screenshots.
