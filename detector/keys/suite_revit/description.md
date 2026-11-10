# `presidential suite_layout.dwg`: description for the labellers (held-out run, step 2)

The fifth drawing of the openings detector's held-out test: a Revit export of a hotel presidential suite, made by the
company's 3D team on 9 Nov 2026, one plan per file. Written from the drawing only: the DXF (read with ezdxf) and the
flattened cache `prims.pkl` (paths in `drawing.json`). No detector output and no layer mapping of this drawing was read.
Pictures: `pictures/INDEX.md`. Layer roles as read here: `layer_roles_from_description.json`. Scripts: `scripts/`.

All coordinates are **drawing metres** (DXF millimetres / 1000), the same as the cache and the detector. Openings are not
listed here; where a convention is explained, one example position is given so that it can be found in the pictures.

## 1. File, extent, units, scale

- DWG 2,280,952 bytes (sha1 `9e84e27f…`), converted with LibreDWG to DXF AC1032. The step before this one compared the
  DXF with LibreDWG's own dump of the DWG: every entity type count matches in all spaces and block definitions, hatch
  layers identical (`WORK/suite_revit/check_conversion.txt`). ezdxf's recover mode reads it with 0 errors, 13 fixes.
- Model space only: 22,849 entities; both paper-space layouts are empty; no xrefs; no DIMENSION entities. 34 layers in
  the table, 25 of them with entities. 167 block definitions: 55 inserted in model space (124 inserts, none nested), 65
  unused (section 5), 47 layout and anonymous blocks.
- The cache: 29,886 items (22,848 top level, 7,038 unpacked from the 124 inserts, depth 1 only), all tagged with the
  floor tag **`suite_revit`** (prims.py gives any drawing it has no special case for its cache name). Only one WIPEOUT
  is not in the cache.
- **Extent: x 1.569 to 25.079, y 0.008 to 13.084** (23.5 x 13.1 m). Nothing lies outside. The east edge (x 25.079) and the
  south edge (y 0.008-0.009) are the **crop of the Revit view**: walls stop dead there, two service double doors at
  x 24.02-25.75 lose part of their second leaf, and two unit doors at y 0.81 have their leaves and swings cut at y 0.009.
  The north (bays, y 13.084) and west (bay, x 1.569) edges are real building edges.
- **Units: millimetres.** The header says `$INSUNITS` = 1 (inches) and `$MEASUREMENT` = 0 (imperial): both wrong. Checks:
  - Columns: blocks `COLUMN_CONCRETE RECTANGLE_GEN - 500W 1000D` measure 500 x 1,000 units (e.g. x 2.762-3.262,
    y 10.509-11.509).
  - Door leaves: block `SERVICE_SWING_DOUBLE - D22 1800X2100MM`: two leaves of 865 units, hinges 1,730 apart (frame
    included 1.8 m, as the type name says); `SERVICE_DOOR_SWING_1_SOLID - 850X2400MM_D06`: leaf 780; `UNIT_DOOR_SWING_1_SOLID
    - D01_1000X2250MM`: swing radius 930, frame jambs 0.93 m apart. The exploded doors of the suite have leaves of 0.665-0.70,
    0.865 (a pair), 0.88-0.90 m.
  - Wall thickness: facade wall 100 units (y 11.409-11.509), corridor walls 200 (y 0.209-0.409), partitions 150-unit
    cores with 25-unit linings (x 7.354 / 7.379 / 7.529 / 7.554).
  - With inches every one of these would be 25 times too big (a 12.7 x 25.4 m column). Use `units: mm`; drawing metres are
    real metres.
- Frozen layers (invisible in CAD, present in the DXF and the cache): `Q-SPCQ` (curtains, TVs, lamps, fridge, toilet-roll
  holder) and `A-ANNO-IDEN` (the room names).
- Room-name texts are MTEXT 248 mm high; the only other text is `FHC` (fire-hose cabinet) at (14.116, 1.114).

## 2. Layers: what is drawn on each, and the role read for the detector

Counts: entities at the top level of model space / entities inside the inserts (each insert unpacked). "Block" means the
entities are in block definitions; layer-0 entities inside a block take the insert's layer (that is how the cache and
CAD read them).

| Layer | Top level | In blocks | What is drawn (typical shapes, example) | Role |
|---|---|---|---|---|
| `0` | 2,635: LINE 1,640, ARC 787, HATCH 99 (all SOLID), LWPOLYLINE 83, CIRCLE 24, SOLID 1, WIPEOUT 1 | 0 | **All interior partitions of the suite and the wall linings**: face lines and SOLID fills. 106 fill loops: 28 partition fills 0.10-0.205 m thick (e.g. x 7.354-7.544, y 3.334-10.284; x 11.487-11.637, y 4.70-10.51; x 24.812-24.962, y 3.76-11.51), 73 linings 12-35 mm thick along both the partitions and the `A-WALL` shell (e.g. y 11.384-11.409 along the north facade), one 10 mm glass pane (x 9.51-11.50, y 10.229-10.239), two thin L-shaped furniture fills (the back of the living-room sofa, x 15.77-16.07, y 7.00-8.95; the frame of a two-seat sofa in the master bedroom, x 7.04-7.25, y 7.70-8.68), two 5 mm specks. **And all the loose furniture and joinery outlines**: armchairs, sofas, beds, dining and bar tables, bar stools, wardrobes with coat-hanger zigzags, dressing table, TV wall unit, shelving along the angled facade walls; dashed lines inside every bay; dashed pendant-light circles; one riser X; threshold lines; the 10 mm glass-screen lines of the bathrooms. 85 entities carry their own dashed/hidden linetype | **wall** |
| `A-WALL` | 249: LINE 181, HATCH 54 (SOLID), ARC 13, INSERT 1 | 58: LINE 52, HATCH 6 (block `Walls 13 - Walls 1-2656323`) | The building shell only: the 100 mm facade walls between the bays (y 11.409-11.509) and the angled solid facade walls of the bays (e.g. (6.49, 12.948)-(7.379, 11.409), 100 mm), the west facade (x 2.762-2.862), the suite's south wall (y 0.209-0.309, x 3.262-11.512), the corridor and shaft walls in the south-east (100 and 200 mm, x 12.0-25.08, y 0.009-1.209), the jambs of the corridor service doors (x 15.137-15.237, 17.037-17.137), rounded returns of a wall niche (13 arcs, x 20.61-20.79, y 7.54-8.61). In the block: small wedges at the bay corners where the glass facets meet (e.g. x 21.508-21.605, y 12.263-12.349) and at the west bay (x 1.569-1.662, y 4.03-4.10 and 7.62-7.69). 70 fill loops: 54 of 90-210 mm, 14 wedge pieces, 2 specks | **wall** |
| `S-COLS` | 6 INSERT | 30: LINE 24, HATCH 6 | 6 concrete columns 0.5 x 1.0 m (4 lines + SOLID fill each) at x 2.76-3.26, 11.51-12.01, 20.26-20.76 and y 0.21-1.21, 10.51-11.51 | **column** (wall would do the same for the wall solid) |
| `A-GLAZ-CURT` | 18 INSERT | 72 LINE | Curtain-wall glass panels (`System Panel - GLAZED-…`): each pane two lines 10 mm apart with 10 mm end lines; panes 0.707 and 1.417 m long in the north bays, 1.56 and 3.517 m in the west bay (e.g. x ≈ 1.61, y 4.10-7.62) | **glass** |
| `A-GLAZ-CWMG` | 42 INSERT | 140: LINE 131, HATCH 9 | Curtain-wall mullions (`Rectangular Mullion - 100X50-…`): 24 boxes of 50 x 100 mm at the ends and corners of the glass facets, and 18 blocks (`…-V10` to `-V23`, `-2447655/57/65/67`) that run along every pane: two lines 0.10 m apart with the glass midway (one line only in `-2447665`), as long as the pane (0.707-3.517 m); in 9 of them the two 45 mm halves are also SOLID-filled. 12 of the box inserts are mirrored (extrusion -Z) | **glass** |
| `A-DOOR` | 102: LINE 89, ARC 7, INSERT 6 | 41: LINE 32, ARC 9 | Door leaves (two lines 40 mm apart, glass leaves 10 mm), swing arcs (all 16 drawn **dashed**: linetype `- DASH SMALL` set on the arc), slide-direction arrows of the pocket doors (a 0.6 m shaft and two 0.14 m heads, e.g. x 7.324, y 2.48-3.08), the zigzag panels of a bi-fold door (8 lines of 0.564 m, x 9.39-9.95, y 2.45-3.24). The 6 inserts are the corridor door blocks (section 4) | **door** |
| `A-DOOR-FRAM` | 82 LINE | 79 LINE (the 6 door blocks) | Door frames: 40 x 50 mm rebated returns at both jambs and a 0.15 m line across the wall core at the jamb (e.g. x 7.379-7.529 at y 2.284). In the corridor door blocks also three lines **across the whole opening**, 40 and 60 mm apart (e.g. y 3.209 / 3.249 / 3.309, x 15.272-17.002) | **door** |
| `A-DOOR-HDLN` | 4 ARC | 0 | Four dashed 30-degree swings of r 0.70 of the glass doors (e.g. centre (9.512, 5.351), 90-120 deg) | **door** |
| `A-DETL-GENF` | 160: LINE 110, ARC 50 | 32: LINE 20, ARC 12 (the 2 D01 blocks) | Lever door handles only: arcs r 3-5 mm, lines up to 0.112 m, next to the leaf tips (e.g. x 10.67-10.81, y 3.70-3.84). No swings, leaves or jambs | **ignore** |
| `A-DETL` | 6 LINE | 0 | Three dashed (`Centre`) X marks in the service risers behind corridor doors: x 15.237-17.037, y 3.309-3.659 and two at x 23.987-25.079 (y 3.309-3.659, 0.759-1.109) | **ignore** |
| `A-GENM` | 139: LINE 77, ARC 62 | 0 | Generic models: bed linen and cushions on the three beds (x 6.14-7.21, y 4.94-6.77; x 23.52-24.60, y 7.56-11.14), hatched tops of the two mini-bar units (x 2.94-3.76, y 9.04-9.99; x 20.84-21.65, y 10.13-11.08). 16 of its arcs (r 0.30-0.97 m, 20-50 deg) look like door swings | **ignore** |
| `A-GENM-HDLN` | 524: LINE 520, CIRCLE 4 | 0 | Dashed outlines of the long pull handles of the four glass doors, 0.57 m long, along each 30-degree leaf (e.g. x 9.13-9.52, y 5.35-5.96) | **ignore** |
| `Q-CASE` | 17,191: LINE 17,020, ARC 92, SPLINE 32, HATCH 19, LWPOLYLINE 16, INSERT 12 | 5,650: LINE 5,646, LWPOLYLINE 4 (12 blocks `FP_27…FP_59`) | Casework: the two mini-bar units drawn with about 8,400 near-zero-length lines each (x 2.89-3.76, y 9.02-10.01; x 20.8-21.65, y 10.1-11.1), a slatted luggage rack in a wall niche (x 20.65-21.2, y 7.65-8.60), and wall panels behind the beds in the `FP_` blocks (x 7.05-7.35, y 4.13-7.58; x 24.43-24.79, y 6.99-11.74), drawn against the partition faces | **ignore** |
| `Q-CASE-HDLN` | 58: LINE 52, ARC 4, LWPOLYLINE 2 | 0 | Dashed outlines of the mini-bar units (x 2.92-3.73, y 9.06-9.96; x 20.82-21.62, y 10.16-11.06) | **ignore** |
| `Q-SPCQ` (frozen) | 30 INSERT | 892: ARC 729, LINE 135, ELLIPSE 16, LWPOLYLINE 12 | 24 curtain blocks (`CURTAIN_LINEAR_SINGLE`, wavy lines inside each bay, e.g. insert (21.464, 11.611)), two TVs, two table lamps, a fridge in the BOH. (its door swing is an arc of r 0.5) and a toilet-roll holder at (11.627, 1.589) | **ignore** |
| `P-SANR-FIXT` | 806: LINE 385, SPLINE 152, ARC 113, ELLIPSE 102, LWPOLYLINE 54 | 0 | Sanitary fixtures, all in the master bathroom: bath (x 8.82-10.40, y 11.08-12.30), WC (x 10.06-10.70, y 6.26-6.93), two basins (x 7.63-8.09), two shower valves on x 11.29-11.49 | **ignore** |
| `I-FURN` | 206: ARC 116, LINE 68, LWPOLYLINE 22 | 0 | Beds and bed frames, rugs, desk, side tables, the dining-table base (x 4.67-7.24, y 4.32-7.39; x 21.85-24.73, y 7.38-11.33; around (18.55, 8.675)). 10 arcs look like swings (r 0.61-0.75 m, 20-36 deg) | **ignore** |
| `I-FURN-CHAR` | 8 INSERT | 40 LWPOLYLINE | Eight dining chairs (block `Gruppo-19`, scaled x10 and mirrored) round the table at (18.55, 8.675) | **ignore** |
| `M_Arredi` | 13: LWPOLYLINE 8, LINE 4, HATCH 1 | 0 | A small sofa in the master bedroom (x 6.49-7.25, y 8.66-10.07; the exploded block `sofa 2`) | **ignore** |
| `I-WALL-HATT` | 13: LWPOLYLINE 12, LINE 1 | 0 | Despite the name: the cushions on that sofa (x 6.82-7.08, y 8.85-9.45; also from `sofa 2`). No wall hatch | **ignore** |
| `E-LITE-EQPM` | 253: LINE 92, ARC 80, SPLINE 24, ELLIPSE 22, LWPOLYLINE 19, CIRCLE 16 | 0 | Floor, table and wall lamps and pendants (circles with crosses), e.g. x 3.36-3.91, y 10.62-11.17 | **ignore** |
| `M-EQPM` | 271: LINE 270, INSERT 1 | 4 LINE | The rims of the two round tables traced in 2-8 cm segments (dining table r 0.75 at (18.55, 8.675); master-bedroom table r 0.5 at (5.31, 11.58)) and the fire-hose cabinet block `FHC 02 - Type 1` (x 13.89-14.69, y 0.86-1.21) | **ignore** |
| `G-IMPT` | 24: LINE 19, LWPOLYLINE 5 | 0 | Part of the WC (cistern / flush plate) from the exploded WC family (x 10.32-10.70, y 6.68-6.94) | **ignore** |
| `A-ANNO-IDEN` (frozen) | 8 MTEXT | 0 | Room names (section 6) | **ignore** |
| `A-ANNO-NOTE` | 1 MTEXT | 0 | `FHC` | **ignore** |
| `A-WALL-PATT`, `S-STRS`, `S-STRS-MBND`, `A-FLOR`, `A-ANNO-DIMS`, `Defpoints`, `ID-LOOSE`, `ID-LOOSE2`, `G-ANNO-TEXT` | 0 | 0 | Empty. `Defpoints` has 120 POINTs, but only inside orphaned dimension blocks (`*D123`…`*D167`) that model space does not use | wall / stair / stair / ignore ×6 (by name; nothing to read) |

Why these roles, in short:

- **Layer 0 must be `wall`**: it holds every interior partition (28 cores and their linings); `A-WALL` has only the shell,
  so without layer 0 the suite has no interior walls at all. The price: everything else on layer 0 (furniture, wardrobes,
  shelves, dashed bay lines, thresholds, the riser X, the bathroom screen lines, two furniture fills) is read as possible
  wall material too. Its 787 arcs are all small or flat: none has r 0.28-2 m with a 20-125 degree sweep, so none looks
  like a door swing.
- `A-GLAZ-CURT` and `A-GLAZ-CWMG` are the curtain wall of the bays (Revit categories curtain panel and curtain mullion),
  read as `glass` as in the bank branch's Revit export. Mapped as `wall`, the mullion layer's two lines along each pane
  (0.10 m apart, nine of them filled) would make a 0.10 m wall over every bay.
- `A-DETL-GENF` holds nothing but door handles (on the tower floors the `A-DETL-*` layers held swings and leaves; here
  they do not); `A-DETL` holds only the riser X marks.
- `A-GENM`, `I-FURN`, `Q-SPCQ` hold arcs shaped like door swings (bed throws, table rims, the fridge door): ignore them.
- There is **no window layer and no window family**: all facade glazing is curtain wall. Nothing is a screen (no grille
  or louvre). Nothing is a stair.

## 3. Things on unexpected layers (plainly)

- **Interior walls on layer 0**, not on `A-WALL`: every partition of the suite, with its 12-35 mm finish linings drawn
  as separate fills and lines on both sides; also the linings of the `A-WALL` facade, corridor and column faces.
- **Furniture on the wall layer**: the same layer 0 carries armchairs, sofas, beds, bar counter and stools, wardrobes,
  dressing table, shelving, two solid furniture fills, a pendant light (dashed circles) and threshold lines.
- **Glass on layer 0**: the 10 mm glass screens of the bathrooms (two lines 10 mm apart, one 10 mm SOLID fill at
  y 10.229-10.239), not on a glass layer.
- **Wall pieces inside a block**: the corner wedges of the six bays are block `Walls 13 - Walls 1-2656323` on `A-WALL`,
  inserted at (-5.738, 11.009) with a 6.7-degree rotation; its geometry lands at the bays (insert point far away).
- **Door swings on `A-DOOR` are dashed** (linetype on the entity), and the glass-door swings are on `A-DOOR-HDLN`.
- **Door handles on a detail layer** (`A-DETL-GENF`), riser X marks on `A-DETL` and one on layer 0.
- **Misleading names**: `I-WALL-HATT` = cushions; `M-EQPM` = table rims and a fire-hose cabinet; `G-IMPT` = part of the WC.
- **Room names and curtains on frozen layers**.

## 4. How this drawing draws things

**Walls.** Shell walls (`A-WALL`): two face lines plus a SOLID fill, 100 mm (facade, west wall, south wall, unit-door
wall) or 200 mm (corridor and shaft walls). Partitions (layer 0): a SOLID fill for the core (100, 150 or 175-205 mm)
with face lines, plus finish linings of 12-35 mm on one or both sides drawn as their own thin fills and lines, so one
partition shows four or five parallel lines (e.g. x 7.354, 7.379, 7.529, 7.554; overall 0.20 m). Wall ends at openings
are squared off, usually with door-frame returns on `A-DOOR-FRAM`. The fill always stops at an opening; **the face
lines do not always stop** (see "lines across openings" below).

**Hinged doors (the suite's own: exploded, top level).** Leaf = a thin rectangle, two lines 40 mm apart, drawn open at
90 degrees; swing = a dashed arc on `A-DOOR` from the open leaf's tip back to the closed position (sweep 90.5 deg);
frames on `A-DOOR-FRAM` at both jambs; a lever handle on `A-DETL-GENF` at the leaf tip. Example: centre (11.507, 3.747),
r 0.90, in the partition x 11.487-11.637 (`pictures/detail_hinged_door.png`). The suite's double door is drawn the same
way: two such leaves of 0.865 m whose closed tips meet (centres 1.73 m apart on one wall line, e.g. y 3.309).

**Doors in blocks (the corridor outside the suite).** Six Revit door families are still blocks on `A-DOOR`:
`UNIT_DOOR_SWING_1_SOLID - D01_1000X2250MM` (2, a pair at rotations 0 and 180, not mirrored),
`SERVICE_SWING_DOUBLE - D22 1800X2100MM` (3), `SERVICE_DOOR_SWING_1_SOLID - 850X2400MM_D06` (1). Their sub-entities are on
`A-DOOR` (leaves, dashed arcs), `A-DOOR-FRAM` (frames) and, for D01, `A-DETL-GENF` (handles). The service doors are drawn
**open 35 degrees** (swing sweep 35.5 deg), with three frame lines running across the whole opening; behind each is a
shallow riser (0.35 m) marked with an X (`pictures/detail_service_doors.png`). The two D01 doors stand in a 100 mm
`A-WALL` wall at y 0.809-0.909 whose two face lines run on unbroken across both openings; their leaves (0.93 m) and
swings point south and are cut by the crop at y 0.009 (`pictures/detail_unit_doors.png`). The insert point of each
door block is on the door (on the wall line at the opening).

**Pocket (cavity) sliding doors (exploded).** The wall is split into two skins round a pocket beside the opening; the
leaf (two lines 40 mm apart, 1.0 m) is drawn inside the pocket, mostly out of the opening; a red arrow on `A-DOOR` in the
room beside the opening gives the slide direction; frames on `A-DOOR-FRAM` at both ends; and **the partition's two core
lines (150 mm apart, layer 0, continuous) run across the opening**. Example: x 7.354-7.554, opening y 2.284-3.334,
pocket (between x 7.419 and 7.489) up to y 4.267 (`pictures/detail_pocket_door.png`). The unused block
`DOOR_SLIDING_CAVITY_1_SOLID - D13` (9 frame lines, 7 door lines) matches this drawing of it.

**Glass doors in glass screens (exploded).** In the master bathroom a screen runs along x 9.467-9.567: two continuous
lines 0.10 m apart (layer 0, no fill; probably a kerb or base channel) with the 10 mm glass between them (lines at
x 9.512 and 9.522, layer 0). The glass stops at each door; the door leaf (`A-DOOR`, two lines 10 mm apart, 0.70 m) is
drawn **open 30 degrees**, with a dashed 30-degree swing on `A-DOOR-HDLN` and a dashed handle outline on `A-GENM-HDLN`;
no frames. The 0.10 m lines run on past every door. The same screen type runs along y 4.724-4.824 (glass at
y 4.770-4.780) in the unlabelled room x 22.89-24.79 (`pictures/detail_glass_screen_doors.png`). The unused block
`IN_SHOWER DOOR1 - Shower door_700X2160MM` is this family: its 130 lines and 1 circle on `A-GENM-HDLN` and 1 arc on
`A-DOOR-HDLN`, four times over, are exactly the 520 lines, 4 circles and 4 arcs on those layers.

**Bi-fold door.** Four panels (8 lines of 0.564 m on `A-DOOR`) drawn folded as a zigzag against one end of a 2.2 m
opening, with a dashed track line (layer 0) along the opening's centre (x 9.46, y 0.96-3.18;
`pictures/detail_bifold.png`). Unused block `Doors 1 - Doors 1`.

**Openings without a leaf.** Two looks: (a) the fill stops and the two face lines go on across the gap **dashed**
(head over the opening), e.g. x 13.137-15.112 at y 5.061-5.211 (`pictures/detail_head_lines.png`; the only dashed head
of this kind on layer 0); (b) open sides with nothing drawn, where a partition simply ends and a room opens into the next
(e.g. the dressing area x 7.55-9.39 is open along y 3.18-3.33). The open plan between the bar and the living and dining
area, and between the lobby of bedroom 2 and the bedroom, has no walls at all.

**Lines across openings** (what is drawn inside door openings varies):

| What crosses the opening | Seen at, for example |
|---|---|
| nothing | the hinged door at x 11.487-11.637, y 3.70-4.70 |
| one continuous layer-0 line (a threshold) | y 3.309 across the suite's double door, x 13.322-15.052; also at two 0.7 m doors |
| the partition's two core lines, continuous, layer 0 | every pocket door (e.g. x 7.379 and 7.529, y 2.284-3.342); also one hinged door (x 20.437 and 20.587, y 4.459-5.159) |
| the wall's two face lines, continuous, `A-WALL` | the two D01 unit doors (y 0.809 and 0.909) |
| the screen's two 0.10 m lines, continuous, layer 0 | every glass door of the screens |
| three frame lines on `A-DOOR-FRAM` | the corridor service doors |
| the two face lines, dashed | the gap at x 13.137-15.112, y 5.061-5.211 |

**Windows and curtain walls.** No windows: there is no window layer and no window family. The facade glazing is six
**curtain-wall bays** (Revit curtain walls, all in blocks): five on the north facade, 4.375 m apart (glass and
mullions at x 3.80-6.14, 8.17-10.51, 12.55-14.89, 16.92-19.26, 21.30-23.64; y 11.48-13.07), each three facets of
0.707, 1.417 and 0.707 m panes at 75, 30 and -15 degrees, and one on the west (x 1.57-2.83, y 2.86-8.86) of 1.556,
3.517 and 1.556 m panes at 45, 90 and 135 degrees. Each facet: the pane's two lines 10 mm apart (`A-GLAZ-CURT`), two
mullion lines 0.10 m apart with the glass midway, partly filled (`A-GLAZ-CWMG`), mullion boxes 50 x 100 mm at the facet
ends, and a small wall wedge where two facets meet (block `Walls 13`). Each bay starts and ends
at solid wall: on the north facade a 100 mm straight wall on one side and a 1.66-1.78 m solid angled wall on the other,
on the west the 100 mm west wall. Inside every bay a dashed layer-0 polyline runs roughly parallel to the glass (overhead or
floor edge of the bay), and curtains (`Q-SPCQ`, frozen) hang in it (`pictures/detail_bay.png`).

**Glass partitions.** Only the two bathroom screens above (10 mm glass on layer 0 between 0.10 m lines), plus the 10 mm
glass fill at x 9.51-11.50, y 10.229-10.239 closing the shower on its north side. No `A-GLAZ` partition layer.

**Lifts and stairs.** None drawn. `S-STRS` and `S-STRS-MBND` exist but are empty. The service risers behind the corridor
doors are X-marked shafts 0.35 m deep; the enclosed shaft at x 12.01-14.69, y 0.41-1.01 has no door.

**Columns.** Six 0.5 x 1.0 m concrete columns (blocks, `S-COLS`) on a grid of 8.75 m (x) by 10.3 m (y), standing in the
facade and corridor walls.

## 5. How blocks are used

- Block names are Revit `<family> - <type>-<element id or Vnn>-<view name>`, e.g.
  `SERVICE_SWING_DOUBLE - D22 1800X2100MM-2804302-GENERAL ARRANGEMENT PLAN`: one definition per placed element, all with
  base point (0, 0). Some families are drawn round their insert point (doors, columns: insert point on the door or at
  the column centre); others carry world coordinates and are inserted far away (the `Walls 13` block and 18 mullion blocks
  at (-5.738, 11.009); the bay pieces land at the facade). Labels in the pictures are placed at the geometry.
- Used in model space (124 inserts): 6 door blocks (`A-DOOR`), 18 curtain panels (`A-GLAZ-CURT`), 42 mullions
  (`A-GLAZ-CWMG`), 6 columns (`S-COLS`), 1 `Walls 13` (`A-WALL`), 12 casework panels `FP_xx` (`Q-CASE`), 30 loose items
  (`Q-SPCQ`), 8 chairs `Gruppo-19` (`I-FURN-CHAR`), 1 fire-hose cabinet (`M-EQPM`). **No nesting** (depth 1 only).
- **Mirrored inserts:** 12 mullion boxes (`Rectangular Mullion - 100X50-2447682`, extrusion -Z) and the 8 chairs (scale
  10, -10). No door block is mirrored.
- **Exploded families.** 65 definitions are not inserted anywhere. Among them are the suite's own door families
  `DOOR_SWING_1_SOLID - 800` (3) and `- D09`, `DOOR_SWING_DOUBLE_TYPE 2 - L16_D07`, `DOOR_SLIDING_CAVITY_1_SOLID - D13`
  (2), `IN_SHOWER DOOR1 - Shower door_700X2160MM` (2), `Doors 1`, the niche `Walls 4 - Walls 3`, beds, headboards,
  sanitary ware, a `MINI BAR` of 8,462 lines, and a base-building link block
  `25-0314 MARRIOTT RIVERSIDE HOTEL_ARC_R24_rvt-1-GENERAL ARRANGEMENT PLAN` (shell walls and curtain wall in other
  coordinates). Their geometry is in model space as loose entities, and where it can be counted it matches exactly:
  each of the two mini-bar units is 8,462 `Q-CASE` lines + 12 splines + 34 `A-GENM` lines + 26 `Q-CASE-HDLN` lines, the
  `MINI BAR` block's content; `A-GENM-HDLN` (520 lines, 4 circles) and `A-DOOR-HDLN` (4 arcs) are four copies of
  `IN_SHOWER DOOR1`; `A-DETL-GENF` at the top level (110 lines, 50 arcs) is five copies of the 22 lines + 10 arcs of
  the handle in `DOOR_SWING_1_SOLID`; `M_Arredi` + `I-WALL-HATT` are `sofa 2`. So the suite's doors and furniture were
  exploded, and very probably its partitions too. That is likely why the partitions are on layer 0: entities on layer 0
  inside a block take the insert's layer and lose it when the block is exploded. The suite's doors, walls and furniture
  therefore have no block names to go by; only the corridor doors, the curtain wall, the columns and a few loose items
  are still blocks.

## 6. Rooms (names from the drawing; boxes rough, in drawing metres)

| Room | Label at | Rough box (x; y) | Notes |
|---|---|---|---|
| MASTER BEDROOM | (3.80, 3.51) | 2.89-7.35; 0.33-11.38 | plus the west bay (x 1.57-2.86, y 2.86-8.86) and north bay 1 (to y 13.07); bed, sitting area in the north, wardrobe along the south wall |
| BEDROOM FOYER | (8.03, 4.52) | 7.55-11.49; 3.33-5.06 | |
| (no name) dressing area | | 7.55-9.39; 0.33-3.18 | dressing table, two stools; open to the bedroom foyer on the north |
| (no name) walk-in wardrobe | | 9.54-11.49; 0.33-3.18 | hanging rails; bi-fold door on its west side |
| MASTER BATHROOM | (8.08, 10.78) | 7.55-11.49; 5.25-11.38 | plus north bay 2 (bath); WC x 9.57-11.49, y 5.25-6.95 and shower x 9.57-11.49, y 7.07-10.23 behind the glass screen |
| FOYER | (13.60, 4.64) | 11.64-15.11; 3.33-5.06 | the suite's entrance is on its south side |
| (no name) small room, probably a WC | | 11.64-13.12; 1.22-3.19 | toilet-roll holder block on its west wall, no fixtures drawn |
| LIVING & DINING AREA | (12.22, 6.02) | 11.64-20.41; 5.21-11.38 | plus north bays 3 and 4; round dining table at (18.55, 8.675) |
| BAR | (17.77, 4.90) | 15.66-20.41; 3.78-6.0 | open to the dining area; back counter y 3.78-4.41, bar counter x 16.75-19.33, y 5.20-6.00 |
| BOH. | (21.08, 4.57) | 20.61-22.71; 3.43-5.28 | service pantry, fridge; reached from the bar side and from the corridor |
| (no name) lobby of bedroom 2 | | 20.61-22.71; 5.43-6.99 | wardrobe on its south side; open to bedroom 2 on the north |
| (no name) room east of BOH. | | 22.89-24.79; 3.42-6.85 | glass screen with a glass door at y 4.73-4.83; no fixtures drawn (probably bedroom 2's bathroom) |
| BEDROOM 2 | (22.07, 9.48) | 20.61-24.79; 6.99-11.51 | plus north bay 5; two single beds |
| outside the suite: corridor | | 13.24-25.08; 1.21-3.31 (to 3.66 at x 17.1-20.4) | fire-hose cabinet (x 13.89-14.69, y 0.86-1.21), four service risers, an alcove x 19.09-21.94, y 0.81-1.21 with the column and two unit doors leading south out of the drawing |
| outside the suite: shaft | | 12.01-14.69; 0.41-1.01 | closed, 200 mm walls |

## 7. What will make the openings hard to list

1. **Layer 0 mixes walls and furniture.** Partitions, linings, glass, furniture, wardrobes, shelving, thresholds and
   dashed bay lines all sit on the one layer the walls need; no layer rule can separate them. Parallel furniture lines
   (sofa and bed outlines, wardrobe fronts and shelves 0.3-0.6 m deep, the bar counter, shelving along the angled
   facade walls) can look like wall faces, and two thin furniture fills look like wall pieces.
2. **Face lines carried across openings.** The pocket doors, one hinged door, the two D01 doors and the glass doors all
   have two continuous wall-layer lines 0.10-0.15 m apart running right across the opening (table in section 4): the
   wall looks drawn through. Only the missing fill and the frames, leaves or arrows show the opening.
3. **Pocket doors look empty or closed**: the leaf sits in the wall pocket, the opening holds only the two core lines and
   two frame returns, and the slide arrow is drawn in the room just off the wall face (shaft 0.03-0.04 m from it).
4. **Leaves at odd angles**: glass doors open 30 degrees, corridor service doors 35 degrees, the bi-fold folded. Most
   leaves of the suite are at 90 degrees.
5. **Crop**: walls, the leaves and swings of the two D01 doors (y 0.009) and the second leaf of the two service double
   doors at x 24.02-25.75 (x 25.079) are cut by the view's crop.
6. **Doors outside the suite**: the corridor holds the suite's entrance, service doors to four risers (doors onto 0.35 m
   shafts) and two doors of neighbouring units whose rooms are not drawn. Whether these count is for the labelling rules.
7. **Curtain-wall bays** instead of windows: glazing only in blocks, three facets per bay turning by 45 degrees, with
   mullion lines on both sides of the glass (pane + two mullion lines + mullion boxes = parallel lines 10 mm and about
   45 mm apart, partly filled), bounded by solid walls at both ends. Whether a bay is one window, three, or a glass wall (the tower key scored no curtain-wall
   window) needs the key's convention.
8. **Thin glass and kerbs**: the 10 mm glass of the bathroom screens is on layer 0, between continuous 0.10 m lines that
   do not stop at the doors.
9. **Duplicated line work**: the round tables are drawn on layer 0 and again on `M-EQPM`; beds on `I-FURN`, `A-GENM` and
   layer 0; wall panels (`FP_` blocks) lie against the partition faces; the mini-bars are 8,400 tiny lines each.
10. **Swing-like arcs on non-door layers** (`I-FURN`, `A-GENM`, the fridge in `Q-SPCQ`).
11. **Header units wrong** (inches): use millimetres.

## 8. Uncertain points (said plainly)

- The two continuous 0.10 m lines along the glass screens (x 9.467 / 9.567 and y 4.73 / 4.83) are read as a kerb or base
  channel; they could be the screen's frame. Either way they run through the glass doors.
- The room at x 22.89-24.79, y 3.42-6.85 and the small room south of the foyer have no sanitary fixtures drawn; their use
  is guessed from a screen with a glass door and from a toilet-roll holder.
- The single layer-0 lines across some door openings are read as thresholds (floor-finish changes); the continuous
  `A-WALL` lines across the D01 doors may be thresholds or the wall above the door drawn as cut.
- The dashed layer-0 line inside each bay may be a bulkhead, a curtain pelmet or the edge of a raised floor.
- That the doors and furniture were exploded rests on exact entity counts (section 5); that the partitions were too, and
  that this is why they are on layer 0, is an inference.
- The tower floors had swings and leaves on `A-DETL-*` layers; here every `A-DETL-GENF` and `A-DETL` entity was looked at
  (handles and X marks only), so ignoring both costs no door symbol as far as the drawing shows.

## 9. Files and how they were made

| File | |
|---|---|
| `drawing.json` | extent, units, floor tag, WORK paths of the DXF and the cache, header and counts |
| `layer_roles_from_description.json` | `{layer: role}` as read here, all 34 layers |
| `pictures/` | 3 overall plans, 18 tiles of 6 x 6 m, 8 convention close-ups; list and boxes in `pictures/INDEX.md` |
| `scripts/census.py` | layer census of the DXF (top level, unpacked inserts, extents, line lengths, arc radii, blocks, inserts) |
| `scripts/probe.py` | points / wipeouts, unused blocks, texts, door-layer arcs, swing-like arcs on other layers, linetypes |
| `scripts/draw_pictures.py`, `scripts/zoom.py` | the pictures (zoom.py: any box) |

Commands (Git Bash, from `detector/keys/suite_revit/scripts`, `WORK` as in `drawing.json`):
`python -B census.py $WORK/suite_revit/plan.dxf`, `python -B probe.py $WORK/suite_revit/plan.dxf`,
`python -B draw_pictures.py $WORK/suite_revit/prims.pkl ../pictures`. The cache was made by `tools/prims.py suite_revit`
with `OPENINGS_DATA=$WORK` in the step before this one; the detector code was not touched.
