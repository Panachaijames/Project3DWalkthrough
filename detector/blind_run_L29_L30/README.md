# Held-out test on the fourth drawing: tower floors L29 and L30 (27 Oct 2026)

`L29.dwg` and `L30.dwg` (in the project folder) were added by the owner after the detector was finished. They are Revit
exports (AIA layers, mm) of two floors of an office tower: floor 29 an office floor, floor 30 a banquet floor. The shell,
core, stairs and many doors come from linked Revit models; the facade is one continuous curtain wall. The two floors share
one origin (offset 0.000 mm). The DWG to DXF conversion lost nothing that could be checked (every entity and every hatch is in the DXF
with the same layer, compared with LibreDWG's own dump of the DWG; no second DWG reader was available). It is the same export style as the bank branch, so it tests "another building" more
than "another office's drawing habits".

## What was done, in this order

1. **Frozen code.** `frozen_code/` holds `openings.py` (sha1 starts `730a29203309`), `geomkit.py` and the cache tool as they
   were. The detector was not changed for this test.
2. **Layer mapping from the layer list alone** (`mappings_first_run/`), the way a staff member would confirm it once.
3. **One run**, output kept untouched (`output_first_mapping/`), and **not looked at** until the answer key existed.
4. **Answer key** (`../keys/tower/`), made without the detector: one agent described the drawings; two independent labellers
   listed every opening of each half floor (one geometry first, one pictures first); a third, geometry-only inventory was made for each
   floor; a program compared the three lists and only the disagreements (16 of 75 entries) went to an adjudicator who decided them from the
   drawing. Result: 53 scored openings (23 doors and 4 passages on floor 29, 21 doors and 5 passages on floor 30) and 22 optional ones
   (toilet cubicle doors, lift landings with no door drawn), which are not scored either way.
5. **Score**, then a **blind audit** of what the score showed (below).

## Result (frozen detector)

| | Key | Found (right place and kind) | Right (width too, strict) | Right, also accepting the clear width |
|---|---|---|---|---|
| First mapping, as run | 53 | 43 (81 %) | 36 (68 %) | 39 (74 %) |
| First mapping, audited key | 54 | 44 (81 %) | 37 (69 %) | 40 (74 %) |
| Mapping corrected (see below), key as made | 53 | 45 (85 %) | 38 (72 %) | 41 (77 %) |
| **Mapping corrected, audited key** | **54** | **46 (85 %)** | **39 (72 %)** | **42 (78 %)** |

With the corrected mapping and the key as made, floor 29 alone is 16 of 27 right (59 %) and floor 30 is 22 of 26 (85 %). The gate asks for 80 %:
**not met on this drawing** under the strict reading, close under the clear-width reading (78 %), and the detector does find 85 % of the
openings. It also reports **48 detections that the audited key does not list** (21 windows, 28 passages less one that is now in the key,
no doors), 45 of which two auditors independently judged not to be openings; the four older drawings have 26 such extras, all passages.

- **Mapping.** My first mapping marked three "detail" layers as ignore from their names. They hold the swing arcs, leaf outlines
  and jamb lines of the doors that sit inside the linked models. The independent description of the drawings read them correctly, and
  `mappings_corrected/` (now the active `../mappings/l29.json`, `l30.json`) follows it. Same frozen code: one more door per floor.
- **Strict vs clear width.** The key was made with "the faces of the wall ends that bound the opening". Three lift doors are 1.40 m
  between the shaft-wall ends but only 0.98 m between the liner returns and 0.90 m between the door frame legs; the detector's
  0.98 m matches the clear width. The "clear width" column accepts an independently measured clear width (19 key entries have one:
  `altWidth` in `../keys/tower/tower_audited.json`); it changes only these three lifts. Applying that convention to every entry
  literally would have made standard doors 0.90 m instead of the 1.02 m between wall ends, which both the key and the detector use; that
  was not adopted.

## What goes wrong (12 of 54 key openings are not right; mapping corrected)

| Kind of problem | Openings | What happens |
|---|---|---|
| Sliding glass doors in thin glass screens | 2 (floor 29) | The screen is 1-2 cm thick; the detector only builds a gap in walls of 4 cm or more |
| Passages | 4 | Two Revit "Door-Opening" gaps, and two stair-hall entrances (one beside a stair outline line, one with a designer's line across the gap) are not reported |
| Large sliders | 2 (floor 30) | A bi-parting cavity slider (it cuts a pocket slot in the wall) and a 4.8 m face-mounted slider are not found |
| Doors in glass partitions with sidelights | 4 (floor 29) | Found, but measured across the whole gap between the wall ends (1.2-1.4 m) instead of the door (0.9-1.0 m) |

And the 45 extras that both auditors rejected: 22 are fins, caps and mullion boxes of the curtain-wall facade or long glass partitions
(read as windows, plus one passage), 16 are gaps between a wall end and open space or the side of another wall, 6 are area or room-boundary
lines, and 1 is a printer standing in a wall recess.

## The blind audit (`../keys/tower/audit/`)

73 anonymous places (the 49 extras mixed with 24 key openings as controls) were judged by two independent auditors per floor,
who were not told which place came from where: all four called all 12 controls on their floor real openings with the right kind. They
rejected 45 of the 49 extras, accepted 1 (a doorway the key had missed, now in `tower_audited.json`; the detector had found it) and split on 3. All
of the roughly 90 openings they noticed near the places they judged were already in the key: **the key is complete.** One reviewer per floor also
re-measured every key opening against an explicit clear-opening convention (the table above uses only the lifts from it).

## After the fix round (28 Oct 2026): development-set figures

The misses and extras above were general problems, and the detector was changed for them (`../fix_round_28oct/`; the rules are in
`../openings.py` and summarised in `../README.md`). **This drawing stopped being held out when the detector was changed for it**:
the figures in "Result" above are the held-out ones; everything below is development-set, like the older drawings.

| Same key (`tower_audited.json`) | Right | Not in the key |
|---|---|---|
| Held-out run (frozen code, corrected mapping) | 39 of 54 (72 %) | 48 |
| Floor 29 after the fixes | 28 of 28 | 2 passages |
| Floor 30 after the fixes | 26 of 26 | 4 (3 passages, 1 window of 0.6 m) |
| **Both floors after the fixes** | **54 of 54** | **6** |

- All 12 problems of the table above are gone: the two sliding glass doors in thin screens, the four passages, the two large
  sliders, the four sidelit doors (and the three lift doors are now measured between the shaft walls, as the key has them).
- Four older drawings: 139 of 143 as before, the 26 passages not in their key are now 9, and no door or window changed.
- **The door convention matters for the four doors with fixed glass beside them.** The key measures a door in a glass partition by its leaf and lists the glass beside it
  as a glass wall; the detector now cuts the door at its leaf and records the glass as `sidelights`. Under a wall-end to wall-end
  convention instead, the same output scores 51 of 54; with the sidelight rule switched off, 50 of 54 under the leaf convention and
  53 of 54 under the wall-end one. The 3D team should say which they want.
- A fifth drawing is the first test of any of this.

## Files

| | |
|---|---|
| `frozen_code/`, `frozen_code_hashes.txt` | The detector as it was run |
| `mappings_first_run/`, `mappings_corrected/` | The two layer-role files |
| `output_first_mapping/`, `output_corrected_mapping/` | Detections, marked plans and score files of the two runs |
| `../fix_round_28oct/` | The detector changes made because of this test, and how they were checked |
| `../keys/tower/` | The answer key (`tower.json` as made, `tower_audited.json`), the labellers' and inventory lists (`labels/`), the comparison and adjudicated parts, the audit |
