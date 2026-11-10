# Opening detector (Phase 0, 26-28 Oct 2026)

Finds the **doors, windows and passages** (open gaps) in a CAD floor plan, with no one fixing anything by hand. It is the
first item of the Phase 0 gate in `../walkthrough_app_plan.md`: *at least 80 % of door and window openings right with no
manual fixing, and a second author's file needs only a layer-mapping change, across drawings from at least 3 authors.*

It is a prototype for deciding go / no-go, not the product. The product version will be written for the real service,
but the rules and the answer key here carry over.

## Result

Scored by `tools/score.py` against an answer key that was made separately from the detector (see "The answer key").
**RIGHT** = the opening was found, its width is within 10 % (at least 10 cm) and it has the right class (walkable: door or
passage; or window).

### What to expect on a new drawing: the held-out figures

Three drawings were run with the code frozen before their answer key existed. These are the only honest predictions:

| Drawing | Right | |
|---|---|---|
| Bank branch, Revit export (first run, `blind_run/`) | **39 of 41 (95 %)** | |
| **Tower floors L29 and L30**, Revit export (27 Oct, `blind_run_L29_L30/`) | **39 of 54 (72 %)** | **Below the 80 % gate.** 85 % of the openings were found, but the width was right on fewer, and 48 detections were not in the audited key (45 of the 49 extras were judged not to be openings by two blind auditors). The causes were general, see below |
| **Presidential suite, the 3D team's Revit export** (`presidential suite_layout.dwg`, 10 Nov, [`blind_run_suite_revit/README.md`](blind_run_suite_revit/README.md)) | **7 of 16 (44 %)** | **Below the 80 % gate**, with the detector as fixed on 28 Oct. 50 % of the openings were found: every hinged door whose swing is drawn whole, and none of the four pocket doors, the two doors cut by the view's crop, the bi-fold door or the wide doorless opening. Seven of the nine failures have one cause: the wall's lines are drawn on across the door opening, so no gap is found. 8 detections were not in the key (all 8 judged not to be openings by two blind auditors): furniture on the wall layer, two recess mouths, a cabinet niche. Nothing was fixed |

### After the fix round (28 Oct): development-set figures, not held out

The general causes the tower test showed were fixed in the detector (rules in `openings.py`, listed below), checked by
independent reviewers, and every drawing was re-run. **These figures are not predictions.** The tower floors were used to
design the fixes, and each limit was swept on exactly these six floors. A fifth drawing has since shown what the fixed
detector does on a new one: the 3D team's Revit export of a presidential suite, run held out on 10 Nov, came out at 7 of 16
right (44 %), mostly because the wall's lines are drawn on across its door openings (`blind_run_suite_revit/README.md`). It is
the company's own export, so a drawing from another office would still be the stronger test. The held-out figures above are
the answer to "does it meet the gate".

| Drawing | Floor | Key | Right | Detections the key does not list |
|---|---|---|---|---|
| Sukhumvit house (`Test Sukhumvit Residence.dwg`) | ground | 41 | 39 | 1 passage. GE-17 (sliding vehicle gate) missed; GW-19 (sliding glass door) merged with the corner glass |
| | upper | 40 | 40 | 1 passage |
| Presidential suite (`layout presidential test.dwg`) | suite | 21 | 20 | 5 passages. D16 (movable glass partition on an overhead track) missed |
| Bank branch, Revit export (`I1201`, `I1202`) | Level 1 | 16 | 16 | 1 passage |
| | Level 2 | 25 | 24 | 0. B2-07 found at 0.875 m where the key says 1.00 m (the key's width is probably wrong: the cross wall is drawn straight through the frame) |
| **Four older drawings** | | **143** | **139 (97.2 %)** | **8** (all passages; 26 before the fix round) |
| Tower, Revit export (`L29.dwg`, `L30.dwg`; key `keys/tower/tower_audited.json`) | floor 29 | 28 | 28 | 2 passages |
| | floor 30 | 26 | 26 | 4 (3 passages, 1 window of 0.6 m) |
| **Tower floors** | | **54** | **54 (100 %)** | **6** (48 before the fix round) |

- Per kind: older drawings: doors 86 of 90, windows 33 of 33, passages 20 of 20; tower floors: doors 44 of 44, passages 10 of 10
  (optional key rows are not counted). The tower key has no scored window: its facade is a curtain wall.
- On the four older drawings **no door or window changed in kind or by more than 1 mm** from the 27 Oct run; 22 passages were removed (12
  Sukhumvit, 4 presidential, 3 + 3 bank) and one bank door is now read from its wall gap (its ends moved 0.05 m). The
  Sukhumvit house and the bank model were rebuilt from the new output (`../cad_test/OPENINGS_CHANGES.md`, `../bank_test/README.md`).
- The 14 detections the key does not list are passages except one 0.6 m window (L30-025). Passages are open floor anyway: they
  change nothing in 3D, but a product would show them to a reviewer.
- **Door width next to fixed glass is a convention.** The key measures a door in a glass partition by its leaf (0.9-1.0 m) and calls
  the glass beside it a glass wall; the detector now does the same. Measured from wall end to wall end instead, four L29 doors are
  1.2-1.4 m: with the detector's rule the tower is 54 of 54 under the leaf convention and 51 of 54 under the wall-end one; without
  the rule 50 of 54 and 53 of 54. Either way it is above 90 %, but which one the 3D team wants should be confirmed.
- Three drawing styles with different layer conventions: the Sukhumvit house (`WALL`, `WIN`, `DOOR`, and xref layers), the
  presidential suite (layers like `A-1.Netcat - tuong`) and Revit exports (AIA layers `A-WALL`, `A-DOOR`, ...; the bank and
  the tower). Each needs only its layer-role file in `mappings/`. A drawing in metres, centimetres, inches or feet gives the same
  result as one in millimetres (the mapping's `units`; checked on three drawings, 28 Oct).

### What the tower test showed, and what was changed

At the held-out run 15 of the 54 key openings were not right (12 for the causes in the table of `blind_run_L29_L30/README.md`,
and three lift doors measured at their clear width of 0.98 m where the key has 1.40 m between the shaft walls) and 48 detections
were not in the key. Each cause is a general one, and each rule below is written in physical sizes (no ids, coordinates or
block names). Rule numbers are those of the docstring at the top of `openings.py` (the short list under "What it reads"
merges some of them).

| Cause | Rule that changed |
|---|---|
| Sliding glass doors in 1-2 cm thin glass screens: the screen is no wall, so no gap was built | 6: a thin screen is no wall for the other rules; a gap at the free end of one is a sliding door when thin leaves on a door layer fill it |
| Lift doors between shaft walls with jamb piers; stair-hall entrances; Revit "Door-Opening" gaps | 2: a jamb return or pier (a stub up to 0.275 m on one face) does not move a wall end. 7: passages beside a stair outline, with a drawn frame, or between two stubs that belong to a wall |
| A cavity slider that cuts a pocket slot in the wall, and a 4.8 m face-mounted slider | 6: leaves drawn as two parallel lines 15-70 mm apart on a door layer, in or beside the wall |
| Doors with fixed glass beside them measured across the whole gap | 4: a door ends at its leaf where fixed glass (0.17 m or more) stands beside it; the glass is recorded in the door's `sidelights` and its evidence |
| Curtain-wall fins, caps and mullions read as windows (22 of the 49 extras) | 5: glass that runs on past a gap's wall ends by more than 0.7 m is the curtain wall's, not the gap's; a glass-only bay needs wall ends in line at both ends; glass beside an uncut wall is no bay |
| Gaps between a wall end and the side of another wall (a partition end across an aisle) read as passages (16 of the 49, and 22 passages on the older drawings) | 7: a passage interrupts a wall line: the wall's faces carry on past it, or a centred wall / pier / column does, or its frame is drawn, or it is a door-wide gap to a flush corner |

Not every cause was fixed the same way: where no geometry tells the cases apart, the rule is written to keep a passage and
leave the question open (see "Limits worth knowing").

### How the fixes were checked

- Six clusters of fixes were made in private copies, each against the six drawings, then merged into one detector.
- Independent reviewers read the merge and tried to break it: two adversarial reviewers on the passage rule and the sidelight rule,
  two blind auditors who judged the passages that the new rule removes (of the 22 passages the rule removes on the older
  drawings, 21 were judged not to be passages by both auditors and one split; of 14 kept passages used as controls, 7 were
  called real by both, 5 not real by both, 2 split), three general reviewers (counterexamples, code and performance,
  fuzzing) and, after their fixes, a last fresh reviewer of the changes made since (it found two regressions in the final
  tolerance edits, both fixed). Their findings are in `fix_round_28oct/reviews/`.
  What they changed: limits moved off the drawn sizes (0.20 m walls, 1.40 m openings, 0.25 m jamb returns) or given a 0.5 mm
  tolerance (a 0.55 m strip, the 0.05 m tip of an arc, the 0.1 m overlap of a leaf line) so that a result no longer depends on where
  the sheet sits, how it is turned, or on a nanometre of noise; a doorway between collinear walls of different thickness; free-standing thin piers;
  windows drawn slightly into a deep reveal; the double door that fell apart when its two arcs came in the other order
  (the openings no longer depend on the order of the items in the file: tested with eight orders of each tower floor and three
  of every drawing, the same openings to within 5 cm on one window's ends); the unit scale applied before de-duplication; two
  crashes (a small self-crossing outline, a failed union of near-degenerate wall pieces); a strip search 4 times faster on 800
  thin screens.
- `run_all.py` re-runs all six drawings from this folder and scores them (41 s with the marked plans). The 27 Oct results are kept
  in `output_original_detector_27oct/`; the new ones are in `output/`.

## What it reads

The drawing is flattened to a cache (`<name>/prims.pkl`, made by `tools/prims.py` from the DXF) with every block unpacked.
The only per-drawing input is the **layer-role file** in `mappings/<name>.json`: which layers are wall, column, glass,
window, screen (grilles and louvres: never glazing), door, stair, and which to ignore. Everything else is read from the
geometry on any layer: no block names, no coordinates, no handles. All lengths in the rules are physical sizes in metres.
The rules are written out at the top of `openings.py`; in short:

1. the wall solid is built from wall-layer fills, thin closed outlines and face lines paired 4-45 cm apart;
2. gaps are found along wall strips from the end of one strip to the next wall material;
3. door swings (arcs on any layer) are matched to gaps; a swing in no gap is a door from the symbol;
4. glazing (parallel lines on window / glass layers) glazes a gap, or makes a bay, a window in a drawn-through wall, or a
   glass wall (not an opening); a door ends at its leaf where fixed glass stands beside it;
5. other contents of a gap: sliding or pocket doors, lift doors, frame-only units, openings over low walls, screens;
6. an empty gap is a passage only when it looks like one, and a passage interrupts a wall line;
7. duplicates are fused (door over window over passage).

Output: `{"openings": [{id, floor, kind, subtype, a, b, width, wallThickness, host, hinge, swing, confidence, evidence,
eitherKind, glazing, sidelights (doors with fixed glass beside them only)}]}` with `a` and `b` on the wall centre line at the
faces of the wall ends, in drawing metres. `eitherKind` marks floor-to-ceiling sliding glazing that the plan cannot tell apart as
door or window (both become glass in 3D). `glazing` is where the glazing lines lie across the opening, so a 3D pane can stand
on the drawn glass. `sidelights` lists the fixed glass cut off beside the leaf (ends and layers): nothing builds it yet.

## Run it

Python with `ezdxf`, `shapely`, `numpy`, `matplotlib`. From this folder:

    # once per drawing: DWG -> DXF with LibreDWG 0.14 (see ../cad_test/src/README.md), then the flattened cache
    mkdir bank1
    dwg2dxf -y -o bank1/plan.dxf "../I1201 - LEVEL 1 GENERAL ARRANGEMENT.dwg"
    python -B tools/prims.py bank1             # sukhumvit | presidential | bank1 | bank2 | l29 | l30 -> bank1/prims.pkl

    python -B openings.py mappings/bank1.json out.json --png outdir      # one drawing, with marked top-view PNGs
    python -B run_all.py [OUT] [--png] [--only sukhumvit bank1 ...]      # all six drawings, merged and scored
    python -B tools/score.py keys/final/all.json last_run/all_older.json
    python -B tools/score.py keys/tower/tower_audited.json last_run/all_tower.json

`tools/prims.py` looks for `<name>/plan.dxf` and writes `<name>/prims.pkl` in this folder, or in the folder named by the
environment variable `OPENINGS_DATA` (use that to keep the large derived files out of the project: the presidential DXF
is 105 MB). The Sukhumvit cache also needs `sukhumvit/regions.json` (kept here; the same file as
`../cad_test/src/regions.json`). The DXFs and caches are not kept in the project. Any other drawing name tags its items with its
own name (one plan per file), which is how `l29` and `l30` work.

Run on all six drawings on 28 Oct 2026 from this folder: 41 s with the marked plans (about 20 s without), and the
output is the same as `output/`. A floor with thousands of walls takes much longer (the cost grows with the square of the
drawing; a reviewer measured 129 s of CPU for 10 copies of L30 side by side); the detector warns when a floor takes over 60 s.

To add a drawing from another office: convert it, write its `mappings/<name>.json` (copy the closest one and change the
layer lists; `mappings/bank1.json` is the shortest), add its area tag in `tools/prims.py` (or give the mapping an `areas`
entry, see below), run it and look at the PNGs. **Map window layers as `window`, and curtain walls and partitions as `glass`:**
glass-role glazing is held to the stricter curtain-wall tests, so a corner window drawn on a glass-role layer is lost.

## The answer key

`keys/final/all.json`: 143 scored openings and 27 optional ones. Optional openings (passage mouths, disputed items) are
not counted either way: finding one is reported, missing one is not a miss. Made independently of the detector:

- Sukhumvit and bank: two labellers worked separately from the drawing alone (each part of a floor, with overlaps), a
  program compared the two lists with the scorer's matching rules, and only the disagreements went to an adjudicator who
  looked at the drawing again. The Sukhumvit door and window heights come from the elevations
  (`keys/sukhumvit_heights.json`).
- Presidential suite: the 22 doors listed by hand when the suite model was built (19 Oct), each checked against the
  drawing and its ends read off the wall faces by a labeller; the passage mouths are optional. This key is the least
  independent of the three.
- Tower floors (`keys/tower/`): two independent labellers per half floor (one geometry first, one pictures first), a third
  geometry-only inventory, a comparison program and an adjudicator for the disagreements only; then a blind audit of the
  detector's extras with known-real openings mixed in as controls, which showed the key was complete (but for one passage, added in
  `tower_audited.json`).
- `keys/disputes/` holds what the comparison program found (agreed openings and disputes) for each part,
  `keys/parts/` and `keys/provisional/` the first version of the key (before adjudication), `keys/final/` the adjudicated
  key (each `parts/*.json` there carries a note on how its disputes were decided). The labellers' own lists and the
  adjudicators' reports are in `history/`.

`tools/score.py` is the referee: one-to-one matching per floor (centre within 30 cm or 30 % of the width, same wall
direction), then width and class. `tools/three_way.py`, `combine_keys.py` and `compare_labels.py` made the key;
`tools/render.py` draws a drawing by category with a metre grid; `tools/analyze_any.py` lists layers, units and blocks of a
new DXF.

## Files

| | |
|---|---|
| `openings.py`, `geomkit.py`, `render_openings.py` | The detector (sha1 of `openings.py` starts `14a570251f6d`; the 27 Oct version, `730a29203309`, is in `blind_run_L29_L30/frozen_code/`), its geometry helpers and the PNG marker |
| `run_all.py` | Runs all six drawings, merges, scores (older four against `keys/final/all.json`, tower against `keys/tower/tower_audited.json`). Writes to `last_run/` unless you name another folder |
| `mappings/` | The layer-role file of each drawing (the only per-drawing input) |
| `mappings_with_areas/` | The same four with an `areas` entry (where each plan sits on the sheet). They give identical results and would remove the per-drawing code in `tools/prims.py`; kept apart because the Phase 0 rule is "layer roles only" (an open question) |
| `tools/` | `prims.py` (drawing reader), `score.py`, the key-making tools, `render.py`, `analyze_any.py` |
| `keys/` | The answer keys, how they were made, the elevation heights; `keys/tower/` is the key of L29 / L30 with the labellers' lists and the blind audit |
| `output/` | Results of 28 Oct 2026 (after the fix round): per drawing, merged, scores, marked PNGs |
| `output_original_detector_27oct/` | The results of the detector as it was on 27 Oct (four older drawings), for comparison |
| `blind_run/` | The frozen code and the output of the blind bank run (39 of 41) |
| `blind_run_L29_L30/` | The held-out test on the fourth drawing (tower floors L29, L30): frozen code, both mappings, outputs, scores, README |
| `fix_round_28oct/` | What the fix round changed and how it was reviewed: the diff of `openings.py` and `geomkit.py` against the frozen code, the six cluster patches, the reviewers' findings, the checks |
| `history/` | Reports of the agents that labelled, adjudicated, reviewed and fixed (JSON). Written while the work was in a temporary folder: the file paths in them (and in the method notes of `keys/final/parts/`) point there and no longer exist |
| `sukhumvit/regions.json` | Where the two Sukhumvit plans sit on the sheet (input of the cache step) |

## Running a new drawing held out (the procedure used for the bank and for L29 / L30)

To keep a figure honest, run a new drawing the way the bank branch and then the tower floors were run:

1. Convert the DWG to DXF and make its cache (see "Run it"). Write its `mappings/<name>.json` from its layer list only:
   which layers are wall, glass, window, door, screen, stair, ignore. Do not change `openings.py`.
   Read what is on the layers, not only their names: on L29 / L30 three layers called `A-DETL-*` held the door swing arcs, leaf
   outlines and jamb lines of the doors in the linked models, and ignoring them from their names cost two doors.
2. Run it and keep the output exactly as it comes out, unseen. That is the held-out figure.
3. Have its doors, windows and passages listed without looking at that output (two labellers working apart, a comparison
   program, an adjudicator for the disagreements only: how `keys/` was made), then score it with `tools/score.py`. Then audit
   the disagreements blind (anonymous candidate places with known-real openings mixed in as controls), which is how L29 / L30
   showed that the key was complete and that 45 of 49 extras were false.
4. Only then look at what was wrong and fix it with general rules (no ids, coordinates or per-drawing exceptions), and check
   that the six floors above still score as before and that no older drawing's detections change (run every drawing and compare
   with the previous outputs). From then on the new drawing is a development-set drawing.

Where each plan sits on a sheet that holds several plans is still set in code (`tools/prims.py`) for the first three
drawings; a drawing with one plan per file, like the bank's, needs nothing. `mappings_with_areas/` shows the alternative (an
`areas` entry in the mapping). The owner had no answer on this (27 Oct), so mappings keep layer roles only.

## Limits worth knowing

- **The fifth drawing was run held out on 10 Nov and came out below the gate: 7 of 16 right** (the 3D team's Revit export of
  a presidential suite, `blind_run_suite_revit/README.md`). What it showed, none of it fixed: wall lines drawn on across a door
  opening (every pocket door, both unit doors, one hinged door) leave no gap, so the door is missed, or read from its swing at
  the width of its leaf; a door whose swing is cut by the view's crop is not read from its symbol; a bi-fold door is not a
  door the detector knows; a doorless opening of 1.975 m that ends at a flush corner is dropped (the limit under "Passages
  next to walls"); furniture on a layer that has to be mapped as wall makes false passages; the mouths of door recesses and
  an equipment niche are reported as passages. Every figure after the fix round is still a development-set figure, and that
  drawing is the company's own: a drawing from another office would still be the stronger test.
- The 14 detections the key does not list are passages (one window). They cost nothing in 3D (passages are left as they are), but a
  product would show them to a reviewer. Whether passages should be reported at all is a question for the owner: a passage adds no
  object in 3D.
- **Passages next to walls.** The rule that a passage interrupts a wall line drops: a doorway beside a cross wall thicker than 0.225 m
  with the wall carrying on beyond it (no geometry tells it from a corridor crossing), a flush-cornered gap wider than 1.45 m, and
  a far wall turned more than 2 degrees off the line (a kinked facade). It keeps thick-cornered, ragged-end and framed mouths. All
  of the limits are in the comments of `openings.py` with the case that fixed them and the range over which the six floors do not
  mind.
- **Layer roles matter.** Glass-role glazing is read with the curtain-wall tests: a window drawn on a glass-role layer that runs
  on past its wall ends by more than 0.7 m, or a corner window with a post-less glass corner, is dropped (Sukhumvit's two corner
  windows are lost when its window layer is mapped as glass: 137 of 143). Fixed glass beside a door is only recognised on window
  and glass layers, and only when drawn as lines of 8 cm or more (not hatch).
- Door and sliding-door evidence: two parallel lines on a door layer 15-70 mm apart that fill a gap read as a sliding leaf, so
  a threshold or track drawn the same way would too. A leaf longer than 2 m beside a thin glass screen is not read.
- Movable partitions on a track (D16) and site gates (GE-17) are not found; a sliding glass door that is drawn as one run with
  fixed glass beside it comes out as one wide window (GW-19).
- **Noise and placement** (stress tests of 28 Oct, `fix_round_28oct/reviews/round3_fuzzing.json` and the notes in
  `fix_round_28oct/README.md`). Moving every vertex at random by 1 nm to 1 micrometre changes 8 of the 2,260 openings read in ten
  runs of the six drawings (one Sukhumvit pocket door whose ends move by 5 cm); the 27 Oct detector changed 32-41. With 1 mm of
  noise 81 openings change (119 before), and noise of 1.5-10 mm never stopped a drawing (72 runs). Moving a drawing by 100 km, by
  1,000 km or to 5,000 km north changes at most that pocket door; rotating it by 17, 45, 135 (mirrored) or 301 degrees
  changes only the presidential suite's double door (1.60 m or 1.52 m). Both are doors read from a swing or leaf symbol
  on a rounding knife-edge that was not tracked down.
- **Fragile by design, found by the reviewers and left as they are:** a gap's direction is taken from one short wall-end face, so
  1-3 mm of noise on a 3.5-17 cm wall end tilts the gap by up to 2 degrees and the new squareness tests can fail (five tower
  passages, among them the Door-Opening L29W-06, are the first to fall out, with 1.5-5 mm of noise); the 3 cm strip floor sits 5 mm under two 3.5 cm reveals that two keys rest on;
  the facade-glass test needs the glass to stay one long band (7 of 16 runs at 3 mm add a false window on the tower); leaves, glass
  panes and screens are read from single line segments, so lines an exporter cuts in two cost the merged detector 4 tower and 4
  older openings in a reviewer's test that split every line at a random point; several limits (door-wide 1.45 m, jamb return, 3 cm strips) each rest on one or two drawings.
  A uniform 10 % resize of the drawing kept the tower at 54 of 54 in a reviewer's test of the 27 Oct merge, 20 % did not: the limits are
  physical sizes, so a drawing in the wrong units is not read.
- Scanned or PDF-only drawings are out of scope (no geometry to read).
- Windows: windows in the older drawings were all found, but the tower key has no scored window, so window recall on a curtain
  wall building has not been measured.
