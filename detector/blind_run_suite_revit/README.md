# Held-out test on the fifth drawing: presidential suite, Revit export by the 3D team (10 Nov 2026)

`presidential suite_layout.dwg` (in the project folder, 2,280,952 bytes) was made by the company's 3D team on 9 Nov 2026. It is
a Revit export (AIA layers; the geometry is in mm although the header says inches) of a hotel presidential suite, one plan per
file, 23.5 x 13.1 m: the suite's rooms, the corridor in front of it with its service risers and the doors of two neighbouring
units, and six curtain-wall bays. The suite's own walls and furniture are on layer `0`; only the building shell is on `A-WALL`.
It is the first drawing run held out since the fix round of 28 Oct, so the detector frozen here is the fixed one. The DWG to
DXF conversion lost nothing that could be checked (every entity type has the same count in the DXF as in LibreDWG's own dump of
the DWG, and no entity is on another layer; no second DWG reader was available).

**Result: 7 of the 16 scored openings are right (44 %) and 8 were found (50 %). The 80 % gate is not met on this drawing.**
The detector found every hinged door whose swing is drawn whole and none of the other eight openings. Seven of the nine
failures have one cause: the wall's lines are drawn on across the door opening. It also reported 8 passages that the key does
not list, and two blind auditors judged all 8 not to be openings. `result_marked.png` shows the result on the plan.

## What was done, in this order

1. **Frozen code.** `frozen_code/` holds `openings.py` (sha1 starts `14a570251f6d`, the detector as it has stood since the fix
   round), `geomkit.py`, the cache tool and the PNG marker, copied before the DWG was converted. The hashes were checked again
   just before and just after the run, and once more at the end of the test: the files in `detector/` are still the same. The
   detector was not changed for this test, and nothing was fixed after it.
2. **Layer mapping from the layer list and from what is drawn on each layer** (`mappings_first_run/`, with notes on all 34
   layers), the way a staff member would confirm it once. The decision that matters: layer `0` is wall, because every interior
   partition is on it. The loose furniture is on it too, and a mapping gives a role to a whole layer.
3. **One run**, output kept untouched (`output_first_mapping/`), and **not looked at** until the answer key existed.
4. **Answer key** (`../keys/suite_revit/`), made without the detector: one agent described the drawing (29 pictures); three
   independent lists were made (one geometry first, one pictures first, one geometry-only inventory); a program compared them
   (44 places: 40 agreed, 4 disputes) and an adjudicator decided the four disputes from the drawing. Result:
   **16 scored openings** (15 doors, 1 passage) and 26 optional ones (the four glass doors of the bathroom glass screens, two
   riser doors cut by the view's crop, two open sides of rooms, the 18 facets of the curtain-wall bays), which are not scored
   either way. There is no scored window: the drawing has no window, only curtain wall. The description read the same role as
   the first mapping for all 34 layers, so there is **no corrected mapping** and no second run.
5. **Score**, then the audit set: 24 anonymous places (the 8 extras, the 8 missed openings, the 1 found but not right, and the
   7 found right as controls), each with a close-up, in shuffled order.
6. **Blind audit** by two independent auditors (below).
7. The audit applied to a copy of the key, the re-score, a check of each cause with the frozen code (`diagnosis/`), this README.

## Result (frozen detector)

| | Scored | Found (right place and kind) | Right (width too, strict) | Right, by kind |
|---|---|---|---|---|
| First mapping, key as made | 16 | 8 (50 %) | 7 (44 %) | doors 7 of 15, passages 0 of 1 |
| **First mapping, audited key** | **16** | **8 (50 %)** | **7 (44 %)** | **doors 7 of 15, passages 0 of 1** |

There is no corrected-mapping row because no corrected mapping was needed (step 4). The audit changed nothing in the key
(below), so the two rows are the same. The gate asks for 80 %: **not met on this drawing**, and not close. The detector also
reports **8 detections that the key does not list**, all passages, and both auditors judged all 8 not to be openings.

| Kind of scored opening | In the key | Right |
|---|---|---|
| Hinged doors with the swing drawn whole (five singles in the suite, the double entrance door, two riser doors) | 8 | 7 |
| Pocket sliding doors | 4 | 0 |
| Unit doors whose leaf and swing are cut by the view's crop | 2 | 0 |
| Bi-fold door | 1 | 0 |
| Doorless opening (passage) | 1 | 0 |

- **One of the nine sits on the scorer's limit.** SR-10 was found at 0.70 m where the key has 0.80 m: off by exactly the 0.10 m
  the scorer allows, and it fails on rounding (the difference comes out 1.4e-15 m over). With it the figure would be 8 of 16
  (50 %). With 16 scored openings each one is 6 points; the gate needs 13.
- **Recess mouths.** Two of the extras are passages across the mouths of the recesses in front of the two missed unit doors.
  The scorer pairs a detection with a key opening up to 0.30 m away; these are 0.30001 m from the doors, so each door counts
  as missed and each mouth as an extra. Paired, they would be two finds of the wrong kind and width and 6 extras: still 7 of 16.
- **One of the seven is right in width but not in place.** SR-13, a double riser door read from its two swings, lies 0.24 m
  off its wall line, in the riser behind it. The scorer's RIGHT asks for width and class, not for the ends.
- **Optional entries**, not counted either way: a detection matches 21 of the 26. The four glass-screen doors were found at
  0.70 m. The two riser doors cut by the crop came out as single doors of 0.87 and 0.90 m (half of each is outside the
  drawing). The 15 facets of the five north bays came out as windows, see the last section.
- **No other reading of the key reaches the gate.** The key's README names the conventions that could be read otherwise (all
  set before the output was seen). Scored each way (`../keys/suite_revit/audit/score_variants.py`): the suite only, with the
  four corridor doors optional, 5 of 12 (42 %); the four glass-screen doors scored, 11 of 20 (55 %); both, 9 of 16 (56 %); the
  bi-fold optional, 7 of 15 (47 %); every curtain-wall facet scored as a window, 22 of 34 (65 %). With the curtain wall left
  out of the key as a glass wall, as in the tower key, it stays 7 of 16 and the 15 facet windows become detections the key
  does not list: 23, not 8.

## What goes wrong (9 of the 16 scored openings are not right)

| Cause | Openings | What happens |
|---|---|---|
| **Wall lines drawn on across the door opening** | **7**: the four pocket sliding doors SR-01, SR-02, SR-04, SR-11 (missed); the two unit doors SR-15, SR-16 (missed); the hinged door SR-10 (found 0.10 m narrow) | The wall's fill stops at the opening, but two of its lines carry on across it between the door frames: the partition's two core lines (layer `0`, 0.15 m apart) at every pocket door and at SR-10, the wall's two face lines (`A-WALL`, 0.10 m apart) at the unit doors. The detector builds wall from two wall-layer lines 4-45 cm apart, so it reads the wall as drawn through and finds no gap. A pocket door then has nothing left to be found by: it has no swing, and its leaf (two lines in the wall pocket) is only read inside a gap. A hinged door is read from its swing alone and comes out at its leaf's width, between the frames: 0.70 m for SR-10's 0.80 m. (SR-06 is closed the same way, by a threshold line and the edge of a lining, and comes out at 0.70 m for 0.75 m, which passes.) The two unit doors have swings too, but the view's crop cuts their leaves and arcs; a cut arc no longer ends at the tip of its leaf, the detector finds no leaf for it, and a swing without a leaf makes no door |
| **A bi-fold door** | **1**: SR-03 (missed) | Two things. Its end wall stands against wardrobe joinery drawn on layer `0` (shelf and rail lines 0.29-0.32 m apart), which is read as wall: the wall end is lost in a 0.75 m block and no gap is looked for. And a bi-fold drawn folded (zigzag panels, a dashed track, no swing arc, no frame) is not a door the detector knows: with the joinery lines left out it finds the 2.225 m gap, reads nothing in it, and does not keep it as a passage (it stands between two short wall ends, 0.09 m and just under 0.30 m, with no frame drawn) |
| **A wide doorless opening that ends at a corner** | **1**: SR-08 (missed) | The gap is found (1.975 m, from the end of a partition to the corner of an L-shaped wall). Its head is drawn as the wall's two face lines carried across dashed, on the wall layer: not wall (dashed), and not an opening frame either (that is read from door-layer lines). So it is judged as an empty gap and fails the rule that a passage interrupts a wall line: a gap that ends at a flush corner is kept up to 1.45 m only, and the wall's face carries on 0.55 m past the corner where the rule asks for 0.6 m. This is the limit already listed in `../README.md` ("a flush-cornered gap wider than 1.45 m") |

**The first cause was checked with the frozen code** (`diagnosis/whatif.py`): with the 15 lines that cross eight door openings
left out of a copy of the drawing, the same detector reads the four pocket doors as pocket sliding doors of 1.10 m, SR-10 at
0.80 m, SR-06 at 0.75 m and both unit doors at 1.00 m, each from its wall gap: 14 of 16. That is a check of the cause, not a
result. Nothing was fixed, and the held-out figure is 7 of 16. The unit doors needed both things to be lost: without the lines
their gaps are found (checked), and a whole swing would have given a door from its symbol, as it did for SR-06 and SR-10 (not
checked: the leaves end outside the drawing).

All three causes are general. The lines across the openings come with the door family (all four pocket doors and both unit
doors have them, and one of the five hinged singles), not with this one plan, so they should be expected in the team's other
Revit exports.

## The 8 detections the key does not list

All eight are passages, and both auditors judged every one not to be an opening. No door or window was reported that is not there.

| Cause | Detections | What the auditors said |
|---|---|---|
| **Furniture and a rug on the wall layer** | **5**: `suite_revit-005`, `-011`, `-012` (0.70, 0.71 and 1.07 m, at two ottomans on the edge of the living-room rug), `-003` (2.76 m, across the mouth of north bay 3), `-014` (1.69 m, along the facade to an armchair) | Layer `0` carries the partitions and the loose furniture, so furniture is wall material to the detector. The outline of one rug is behind all five: its south edge lies 8 cm from the sides of two ottomans and its north edge 0.375 m from the facade's lining, and two wall-layer lines 4-45 cm apart make a wall. These "walls" end where the furniture ends, and the gaps between them are reported as passages. Auditors: furniture and open floor (inside an ottoman; between an ottoman and the sofa; between the TV wall unit and an ottoman); open floor beside a facade wall that runs past unbroken; the mouth of a curtain-wall bay where the room simply continues (one auditor was least sure of this one, 0.75: a key that counted bay mouths would put it on the facade line, 3.5 m wide, not here) |
| **Mouths of door recesses** | **2**: `-016`, `-017` (1.175 m each) | The corridor wall steps back 0.30 m in front of each unit door, between a wall return and a column. The wall line is interrupted, so the detector reports a passage. Both auditors: the mouth of a door recess, not an opening; the opening is the door at its back (SR-15, SR-16, which the detector missed). They were less sure here than elsewhere (0.8 and "medium-high"). The key had rejected both places before any output was seen |
| **An equipment niche** | **1**: `-008` (0.80 m) | A fire-hose cabinet stands in a gap of the 0.20 m corridor wall, with a closed shaft behind it. The cabinet is on an equipment layer (`M-EQPM`, mapped ignore), so the gap looks empty between two wall ends. Both auditors: a recessed fire-hose cabinet, not a door, window or passage. The key had rejected this place too |

## The blind audit (`../keys/suite_revit/audit/`)

24 anonymous places (the 8 extras, the 9 key openings the detector missed or got wrong, and 7 key openings it found right as
controls) were judged by two independent auditors who were not told which place came from where.

- **Controls:** both auditors called all 7 real openings with the key's kind, and with the key's width to the millimetre.
- **Key openings the detector missed or got wrong:** both called all 9 real, again with the key's kind and width. The misses are
  the detector's, not the key's.
- **Extras:** both rejected all 8. No verdict was split.
- **Is the key complete?** Each auditor listed what else they noticed beside the places: the same 8 openings, all of them in
  the key already (as optional entries). One auditor also counted every door symbol of the drawing (16 swings on `A-DOOR`, 4
  pocket doors, 1 bi-fold, 4 glass doors) and found each one covered.

So no key opening was called not an opening by both auditors, and no extra was accepted by both.
**The audited key has the same openings as the key as made** (`../keys/suite_revit/suite_revit_audited.json`: a copy with a
record of the audit added). `audit/analyze_audit.py` makes it, and `audit/audit_result.json` holds every place with both
verdicts.

## How long each part took

No step logged its own time; these are the file times of 10 Nov 2026, apart from the three measured figures.

| Part | Clock | About |
|---|---|---|
| Freeze the code, DWG to DXF (1.5 s), drawing cache (10.8 s) | 08:38 | 1 min |
| Layer census, conversion check, a look at every layer, the mapping | 08:39-08:53 | 14 min |
| The one run and its record (the detection itself took 2-6 s when re-run in step 7) | 08:55-08:56 | 1 min |
| Description of the drawing, 29 pictures | 08:59-09:37 | 38 min |
| Three independent lists (at the same time) | 09:39-10:03 | 24 min |
| Comparison, the four disputes, the key | 10:06-10:22 | 16 min |
| Score and the audit set | 10:24-10:31 | 7 min |
| Two blind auditors (at the same time) | 10:31-10:53 | 22 min |
| Audit result, re-score, cause checks, this README | 13:02-13:35 | 33 min |

From freezing the code to the auditors' verdicts: 2 h 15 min by the clock.

## What this drawing tests, and what it does not

- **The fixed detector on a drawing it had never seen.** This is the first held-out run since the fix round, and the rules
  written for the tower did not carry it over the gate. Two of the three causes above are not ones the tower showed (wall
  lines across the opening, a bi-fold door). The third is the other side of a fix-round rule: the test that removed the
  tower's false passages at partition ends is what drops SR-08, a limit that was written down at the time. What did hold:
  once a pocket door has a gap, the rules that read a leaf in a wall pocket (one of them written for the tower's cavity
  slider) read it as a pocket sliding door of the right width (the check above).
- **A Revit export by the company's own 3D team.** The same kind of export as the bank branch and the tower (`A-WALL`,
  `A-DOOR`, `A-GLAZ-CURT`, ...). The mapping took a quarter of an hour, and an independent reading of the layers gave the same
  role to all 34: the layer mapping was not what went wrong.
- **A different and smaller layout than the older suite drawing** (`layout presidential test.dwg`, 21 scored openings, drawn
  in another style with layers like `A-1.Netcat - tuong`): another suite, drawn by Revit, with 16 scored openings. A small key
  makes a coarse figure (one opening is 6 points), but 7 of 16 is far from the 13 the gate needs.
- **Interior walls on layer `0`.** The partitions themselves were read as walls without trouble: the four doors found from a
  gap in them have their ends right within 1.3 cm. The price of the layer is what else is on it: the furniture (five false
  passages, the lost wall end of the bi-fold door) and the core lines across five door openings.
- **Doors other than a plain hinged door:** pocket doors with the wall lines carried across (0 of 4), a bi-fold (0 of 1),
  doors cut by the view's crop (0 of 2 scored; the two optional riser doors came out half as wide as they are).
- **Curtain-wall bays.** Six bays of three facets each. The detector reported the 15 facets of the five north bays as windows
  of the right width (it calls them sliding; they are fixed glazing, and either way they are glass in 3D) and none of the three
  facets of the west bay, where it finds no wall end in line with the glass at the bay's corners. The key lists the facets as
  optional, so none of this is scored. No mullion, wedge or cap of the curtain wall became a false window or passage, which
  was the tower's main source of extras before the fix round.

What it does not test:

- **Another office's drawing habits.** This is the company's own team and Revit's own export, the third Revit export among the
  five drawings. A drawing from another office (other layer names, another CAD program, other door symbols) would still be the
  stronger test, above all of the half of the gate that says a second author's file needs only a layer-mapping change.
- **Windows** (the key has no scored window, as on the tower, so window recall on a curtain-wall building is still not
  measured), **stairs and lifts** (none drawn), several plans in one file, units read from the header (it says inches; the
  mapping sets mm by hand).

## Files

| | |
|---|---|
| `frozen_code/`, `frozen_code_hashes.txt` | The detector as it was run |
| `mappings_first_run/`, `mapping_helpers/` | The layer-role file, its notes on all 34 layers, the layer census, the conversion check, and the scripts behind them |
| `output_first_mapping/` | The one run, untouched: the detections (`suite_revit.json`), the marked plan (`png/`), the run record |
| `score_first_mapping.txt`, `.json` | The score against the key as made (step 5) |
| `score_first_mapping_audited.txt`, `.json` | The score against the audited key (step 7): the same figures |
| `result_marked.png` | The result on the plan: scored openings green (right), orange (found, width not right) and red (missed), the 8 extras purple, optional entries thin blue or grey |
| `diagnosis/` | `diagnose.py`: what the frozen detector's own intermediate results say at every miss and extra (printed in `diagnose_output.txt`). `whatif.py`: the checks of the causes on a copy of the drawing (`whatif_output.txt`). `mark_result.py`: the picture. They change nothing and need the drawing cache, which is not kept in the project (make it as in "Run it" of `../README.md`) |
| `../keys/suite_revit/` | The answer key (`suite_revit.json` as made, `suite_revit_audited.json`), its README (how it was made, the four disputes, the uncertain points), the description and pictures, the three lists, and the audit (`audit/`: the places, the secret map, both auditors' verdicts, `analyze_audit.py`, `audit_result.json`, `score_variants.py`) |

To score it again, from `detector/`:
`python -B tools/score.py keys/suite_revit/suite_revit_audited.json blind_run_suite_revit/output_first_mapping/suite_revit.json`
