# Bank branch test (26 Oct 2026, revised 27 Oct 2026)

*Bangkok Bank, Sampeng Branch* (project 26-0216; dwp, schematic design, 1:100) run through the CAD-to-3D pipeline: two
Revit-exported DWGs, one per level (*I1201 - LEVEL 1* and *I1202 - LEVEL 2 GENERAL ARRANGEMENT*), the third drawing
style after the Sukhumvit house and the presidential suite.

It is the **first model built with no drawing-specific rules**. The builder knows the drawing only through
`src/bank_project.json`, which holds the layer roles staff confirm once per office, the two levels with their decided
heights, and file paths. It has no coordinates, handles or block names. The doors, windows and passages come from the
openings detector (updated 27 Oct), used exactly as it found them.

**27 Oct:** the detector was re-run on both levels and the model, page and Max script rebuilt from its new output, with
the review's findings fixed by general rules (see "What changed on 27 Oct"). The main ones: the Revit glass wall type
`GLASS WALL 2600H` is now glass 2.60 m high (read from the type name Revit puts on each wall block), the curved piece at
the south-east corner of the terrace is a 1.10 m parapet, the slot the ATM stands in is closed, there is no floor over
the stairs and the lift shaft on Level 2, the flights marked UP / DOWN are solid steps, and the floor plates no longer
bulge outside the facade or cover the north stair.

| File | What it is |
|---|---|
| `bank_3d_preview.html` | The 3D viewer: Build settings and build replay, Orbit / Walk / Ghost, Camera, Level 1 / Level 2 / both, glass, room names |
| `Bangkok_Bank_Sampeng.ms` | The 3ds Max script: the same model as live, editable objects |
| `bank_topview.png` | Top view of both levels as built, with the opening numbers |
| `test_bank.mjs` | Browser checks (22): run `node bank_test/test_bank.mjs` from the project folder |
| `src/` | The scripts, the project file and the data they made (see "Rebuild" below) |

## What was built

| Part | Level 1 | Level 2 | Height | From |
|---|---|---|---|---|
| Wall runs | 9 | 14 | 3.70 m | `A-WALL`, `A-WALL-PATT` and `S-COLS`: 176 cut fills (139 of walls, 37 of columns), face lines paired 4–45 cm apart, and on Level 2 five curved pieces from concentric arcs |
| Columns | 4 | 3 | 3.70 m | `S-COLS` (free-standing ones; the others merge into the facade walls) |
| Glass partitions | 14 panes (8.6 m) | 5 panes (8.4 m) | **2.60 m**, nothing above | Revit wall type `GLASS WALL 2600H 20X100` (11 blocks on Level 1, 5 on Level 2): the 10 mm glass fill of each, with 1 frame post at a corner (Level 1) |
| Glass screens | 2 | – | 3.70 m | The two 10 mm screens either side of the double glass door L1-027 (lift hall) |
| Curtain-wall glass | 9 pieces | – | 3.70 m | `A-GLAZ-CURT`, `A-GLAZ-CWMG`: 7 window panes and 2 pieces of drawn glass outside any opening (the sidelight by door L1-023 and a jamb mullion). Level 2 has no glass layer |
| Door lintels | 10 | 23 | from the door head to 3.70 m | One per door with a wall at a jamb, as deep as the walls beside it |
| Glass transoms | 5 | 1 | from the door head to 2.60 m (L1-027: 3.70 m) | Doors whose jambs are both glass: L1-005, L1-007, L1-008, L1-022, L1-027, L2-010 |
| Closed wall gap | 1 | – | 3.70 m | The 0.58 m slot in the east facade that the through-wall ATM stands in (`A-GENM` *ATM Machine*) |
| Parapet | – | 1 (5.0 m) | **1.10 m** | The curved, unfilled `A-WALL` piece at the south-east corner of the terrace, between the two terrace railings |
| Railings | 2 | 2 | 1.10 m | `A-FLOR-HRAL` lines thickened into bands (the terrace edge is a 100 x 150 balustrade, a 15 cm band). On Level 2, 3 stair rails that would hang over no floor are left out |
| Stairs | flat tread lines (30 below, 76 faint above the cut) | 16 solid steps (2 flights of 8) | one riser 0.176 m each | `S-STRS` / `S-STRS-MBND`. Level 2's flights carry the words UP and DOWN, so they are built as steps rising and falling from Level 2; Level 1's flights carry no words and stay flat lines |
| Floor plate | 237.4 m² | 285.0 m² (terrace 52.7 m² included) | 0.25 m slab under each level | The inside of the walls, glass and openings, plus the terrace (railing-bounded, reached through the louvred doors). Level 2 is open over the stair (9.3 m²) and the lift shaft (3.1 m²) |
| Room names | 7 | 11 | | `A-AREA-IDEN` room tags (with their areas) and `G-ANNO-TEXT` labels; names that would overlap on screen move a row up or down (or hide when no row is free) |

Levels: **Level 1 at 0.00 m, Level 2 at +3.70 m**. The floor-to-floor height comes from the stair: 21 risers of about
0.176 m. Walls are 3.70 m on each level, up to the next floor. The 30 grid lines, and the 10 grid labels the builder
compares, are identical on both levels, so no shift was needed.

**Openings, all from the detector (55):**

| | Level 1 | Level 2 | How it is built |
|---|---|---|---|
| Doors | 15 | 24 | Open from the floor to the head. The wall, glass and single-line pieces in its footprint are cut away. Above: a lintel to the top of the wall (33), or a glass transom when both jambs are glass (6). No leaf is drawn |
| Windows | 7 | 0 | Curtain-wall panels in the facade gaps: a glass pane from 0 to 3.70 m (a collider) on the detector's glazing band, so there is no sill and no lintel |
| Passages | 5 | 4 | Left as they are: nothing cut, no lintel |

All 39 doors can be walked through their middle both ways. The street doors L1-019 (the pivot double door) and
L1-023 (the curtain-wall door) and the Level 2 lift door L2-006 (the shaft is open) are walked from inside. The
Level 2 facade doors open onto the terrace, which is floor, so they are walked both ways.

**Door heads, read from the door block names** (the size after the width: `...1000X2400` gives 2.40 m). A door whose
name has no height gets the most common height in this drawing's door names: 2.40 m, which 21 of the 31 names with a
size carry.

| Door family (block name) | Doors | Head | From |
|---|---|---|---|
| SINGLE SWING DOOR-GENERIC - 1000X2400 / 700X2400 | 6 + 1 | 2.40 m | name |
| DOOR_GEN_SWING_1 PANEL_FLUSH - 1200x2400 / 900x2400 / 700x2400 | 1 / 1 / 2 | 2.40 m | name |
| DOOR_SWING_1_SOLID - D00-720X2400 / 900X2400, DOOR_SWING_1_louver - 600X2400 | 5 / 1 / 2 | 2.40 m | name |
| _GEN_LIFT_DOOR - DOOR1100x2400 | 2 | 2.40 m | name |
| DOOR_SWING_2_SOLID - 800x2000 (double) | 2 | 2.00 m | name |
| DOOR_SWING_louver - 650x2000 / 800x2000 / 900x2000 (double, Level 2 facade) | 6 / 1 / 1 | 2.00 m | name |
| SINGLE GLASS SWING DOOR-GENERIC - TYPE 1 | 5 | 2.40 m | most common (no size in the name) |
| DOUBLE GLASS SWING DOOR-GENERIC - TYPE 1 | 2 | 2.40 m | most common |
| DOOR-CW_PIVOT_1 PANEL_FLUSH4 - D3 - PL03 (pivot pair) | 1 | 2.40 m | most common |

Not built: furniture, casework, fixtures, plants (the ATM included: only its slot is closed), the stair landings, and
Level 1's flights as solids.

## Glass partitions: the Revit wall type name (a general rule for Revit exports)

Revit exports some wall elements as blocks named after the element, `<family> _ <type> - …-<element id>-<view>`
(Revit's `:` becomes `_`): here `Basic Wall _ GLASS WALL 2600H 20X100 - ___-2613114-LEVEL 1 GENERAL ARRANGEMENT`.
The builder reads that type name the way it reads door heads from door names, with a fixed vocabulary and no data about
this drawing:

- a block on a **wall layer** is a wall element, and its type name is the text between `_` and ` - `;
- a type that says **GLASS, GLAZED, GLAZING or CURTAIN** is a glass wall, and **`<n>H`** in it is its height in drawing
  units (`2600H` = 2.60 m in a millimetre drawing). With no `<n>H` the glass runs the full wall height;
- Revit draws the glass layer's cut fill (the 10 mm pane) outside the block, and the block holds only some of the wall's
  face lines. So the glass is the thin fill (3 cm or less) within 10 cm of the block's own lines, plus any thin fill
  joined to it (a T or L joint where one pane runs through another). Each pane is widened to the type's faces (the
  block's lines parallel to it, 5 cm each side here) and that band is no longer wall; a corner square left between two
  bands is a frame post of the same height;
- the pane is built as glass from the floor to the type's height, with nothing above it, and each pane is its own Max
  object on `BB_<level>_Glass` (named after its type), so the 3D team can select it and change its material or height;
- a door whose jambs are both glass gets a glass transom from its head to the lower glass top (2.60 m), not a wall
  lintel;
- a thin fill (3 cm or less) on a wall layer at the jamb of a door whose block name says GLASS is a frameless glass
  screen: glass, full height (the lift-hall screens either side of L1-027).

The other wall-type block in the drawings (`Basic Wall _ IA_PT01_FINISH LAMINATE - 10mm`, Level 2) says nothing about
glass and stays a wall. The 10 mm screen in the FOR 1 PAX nook (Level 2) has no block and no glass door, so it stays a
wall too.

## Try the 3ds Max script

1. Open 3ds Max with a **new, empty scene** (the script will not touch a scene that has objects in it).
2. *Scripting → Run Script…* and pick `Bangkok_Bank_Sampeng.ms` (or drag it onto a viewport).
3. A small window opens with each level's floor level and wall height (0.00 / 3.70 m and 3.70 / 3.70 m). Leave them and
   press **BUILD THE MODEL**. Build sets System Units to metres.
4. A message says how many objects were built (146: 124 parts, 4 stair shapes, 18 room names) and whether any failed its
   check; details are in the *MAXScript Listener* (F11).
5. *Save As* to keep it.

It follows the presidential-suite script, which the owner ran in real 3ds Max on 26 Oct. Every part is a **live object,
never an Editable Poly**: an editable spline (the outline) with an **Extrude** modifier (output: mesh) and a Smooth
modifier.
- **Change a height:** change the Extrude amount on that object. Or change a level's floor level or wall height in the
  window and press **Update levels and heights**. Every part moves to its level; walls, columns, full-height glass and
  lintel tops take the new wall height. The glass partitions (2.60 m), transoms, the parapet, the steps, railings, slabs
  and room names keep their own heights.
- **Change an outline:** go to the spline level under the modifiers and move vertices.
- **Editable Mesh:** tick *Collapse to Editable Mesh* before Build, or press **Collapse all now** afterwards.
- **Position:** the model sits at the drawing's own coordinates in metres, so it lines up with the DWGs imported in
  metres. Untick *At the drawing's own coordinates* to centre it on the origin. Each object's pivot is at the middle of
  its own outline, on its base, and Zoom Extents frames the model.

| Layer (per level: `L1`, `L2`) | Objects |
|---|---|
| `BB_L1_Walls`, `BB_L1_Columns` | Wall runs (the closed ATM slot is its own object, `BB_L1_Wall_010_closure (ATM Machine …)`), columns |
| `BB_L1_Lintels` | Door lintels (from each door's head to the top of the wall) |
| `BB_L1_Glass` | Glass partitions (`…_GLASS WALL 2600H 20X100`), glass screens, glass transoms (`…_L1-005 transom`), curtain-wall glass and window panes |
| `BB_L1_GlassFrames` | The frame post at a glass-partition corner |
| `BB_L2_Parapets` | The terrace parapet (1.10 m) |
| `BB_L1_Railings`, `BB_L1_Slab` | Railings (1.10 m), the floor slab (0.25 m) |
| `BB_L2_Steps` | The 16 steps of the two flights marked UP / DOWN (each one riser, named after its flight) |
| `BB_L1_Stairs`, `BB_L1_StairsAbove` | Stair lines as plain splines: below the cut, and above it |
| `BB_L1_RoomNames` | Text shapes |
| `BB_Datums` | A hidden point at the DWG origin, with the source and levels in its properties |
| `BB_Check_Failed` | Should be empty: anything here failed the closed-solid, height or position check |

No run of the script in 3ds Max is recorded (the owner thinks the 3D team has already tried it on their own computer; what they found is not known). It was checked as text: brackets balanced, ASCII only, and no part with a
hole touching its outline. The viewer and the script carry the same model-data stamp, and the browser checks compare
them.

## How the drawing was read

| Item | This drawing | Automatic? |
|---|---|---|
| DWG → DXF | LibreDWG 0.14, both files; entity counts checked equal to the DWGs (L1 4,473, L2 21,581) | Yes |
| Layer roles | 30 / 27 layers in use. Walls, columns, glass, doors, stairs (below and above the cut), railings, room names and grid each have a role; furniture, casework, fixtures, plants, services, dimensions and floor edges have none | Staff confirm once (the same roles as the detector's mappings) |
| Walls | Revit draws each cut wall as a solid fill plus its outline. Fills, paired face lines and concentric arcs give the wall runs and 7 free-standing columns; no wall-layer line was left over (0 single-line items) | Yes |
| Glass partitions | The Revit wall type name on each wall block (16 blocks): GLASS and `2600H` | Yes (vocabulary rule, see above) |
| Glass | Curtain-wall panels (10 mm fills) and mullions on the two glazing layers, Level 1 only; frameless screens at a glass door | Yes |
| Doors, windows, passages | 55 openings from the detector, used as found. A door is cut 15 cm past each wall face, but only within its width, so frames drawn a little off its line go too. A self-check finds nothing solid across any door or passage | Yes |
| Door heads | From the door block names; 2.40 m (the most common) where a name has no size | Yes |
| Lintels | As deep as the walls beside the jambs (sections 5–30 cm beyond each jamb), except that a column or block at a jamb does not make a lintel deeper than the door's own wall. This puts L1-023's lintel in the facade line | Yes |
| Wall gaps | Two wall ends facing each other along one wall line, at most 1.2 m apart, with no opening between them and an object block standing in the gap and reaching out of both wall faces, are closed. One found: the ATM slot | Yes |
| Parapets | An unfilled wall piece whose ends both meet railings is part of the balustrade: railing height. One found | Yes |
| Stairs | Stair lines grouped into stairs, riser lines (3+ parallel lines 0.19–0.37 m apart) into flights. A stair word at a flight's end gives its direction; a riser hidden by the break line is put back | Yes |
| Levels | Floor to floor 3.70 m, from the stair's 21 risers (decided) | Given |
| Level alignment | The grid labels match on both levels to 0.0 mm: no shift | Yes |
| Room names | 18 of the 25 labels. Left out: ATM ×3, BA, BE (labels of 3 letters or fewer with no area under them), UP and DOWN (stair words). The drawing's spelling "MEEETING 4 PAX" is kept | Yes |
| Floor plates | See the assumptions below | Yes |

**What the detector's output looked like in 3D** (its job is checked in its own report; these are only the points that
showed up while building):
- The detector's score on these two levels is 16/16 (Level 1) and 24/25 (Level 2) against the answer key; these are
  development-set figures (the bank was used to tune it). The only blind figure is the frozen_v1 run on the bank: 39/41.
- The re-run detector gives the same 27 + 28 openings with the same ids. New: each window carries its glazing band (the
  panes sit on it), and L2-028 (female toilet door) is straightened onto the wall line and now has host 'wall'.
- **L1-023**, the curtain-wall door B1-09 at (5.93, 5.43): its centre line still sits about 0.1 m west of the door slot in
  the curtain wall (a detector matter, unchanged). The cut reaches the slot, and the builder's lintel rule now puts the
  lintel in the facade line (x 5.97–6.07) instead of 10 cm behind it.
- **6 extra passages** (in the detector's score): L1-024, L1-025, L1-026, L2-019, L2-020, L2-021. They are open floor
  anyway, so they change nothing in 3D. L2-019 cannot be crossed at its middle (a toilet partition corner is 0.28 m away);
  the test lists that as information.
- **7 curtain-wall windows**, all typed *sliding* and 5 of them flagged *either kind*. The panels are fixed, but they are
  built as full-height panes either way. The 0.98 m sidelight beside L1-023 is not reported as a window, so its drawn
  glass stays.
- **L2-016** (B2-07) is 0.875 m wide where the door family says 1.00 m: the cross wall runs straight through the frame.
  It is built as found.

## Assumptions (sensible defaults taken from the drawing)

- **Glass partitions** stand to the height their type name gives (2.60 m) with **nothing above them** up to the slab; a
  ceiling or bulkhead is not drawn, so none is built. The doors in them get glass transoms to 2.60 m. The 10 mm fill is the
  glass; the rest of the type's 100 mm band (frame tracks) is not built, except a corner post.
- **The frameless screens** by the lift-hall door L1-027 are glass and full height (no height in any name), so L1-027's
  transom also runs to 3.70 m.
- **The south-east terrace element is a parapet at the railing height (1.10 m).** It is the only wall piece on Level 2 with
  no cut fill (Revit fills every wall it cuts, so it is below the cut plane), and the terrace railings run into both its
  ends. The reviewer also found it drawn entirely in projection line style (colour 8, no line weight), which the drawing
  cache does not carry, so the rule uses the fill and the railings.
- **The ATM slot is closed with full-height wall**, flush in the facade line. The ATM itself is equipment and is not built.
- **Floor plates** are the inside of the walls, glass and openings (every detected opening spans its gap). An area that only
  a railing bounds is floor when you can stand in it (a 0.8 m disc fits), a detected door or passage opens onto it and it is
  not mostly stair: the terrace is floor (its louvred doors open onto it); the area over the north stair (no door, all
  stair) and the rounded corners a closing would add outside the facade are not. Each plate is a 0.25 m slab under its
  level, its edge 3 cm proud of the outline.
- **Above the ground floor there is no floor over a stair** (the outline of its flights and landings: 9.3 m² on Level 2,
  matching the floor-edge line the drawing shows on `A-FLOR`) **nor over a lift shaft** (a room whose only opening is a lift
  door, `_GEN_LIFT_DOOR`: 3.1 m²). On Level 1 the shaft keeps its floor (the pit is not modelled).
- **Steps:** a flight with a stair word at one end rises (UP) or falls (DOWN) from that end, one riser per tread; the riser
  is the floor-to-floor height split into steps of at most 0.18 m (3.70 / 21 = 0.176 m). Each step is a block two risers
  deep (the stair looks stepped from above and below). Landings are not built. Flights without a word (all of Level 1's)
  are drawn as flat tread lines on the floor, since the drawing does not say which way they go; on Level 2, stair lines and
  stair rails over no floor (the north stair, the stairwell) are not drawn: they are below the floor.
- **Room names** that would overlap on screen: the bigger room keeps its place, a smaller one moves one or two rows up or
  down, and is hidden only when no free row is near (in the default view one of the 11 Level 2 names is hidden).
- Door heads from the names (2.40 m where a name has no size), floor to floor 3.70 m and railings 1.10 m are unchanged
  from 26 Oct.
- The detector, its mappings and the drawing reader (`tools/prims.py`) are in `detector/` in the project folder, and
  `bank_project.json` points at them with relative paths. The two drawing caches (`detector/bank1/prims.pkl`,
  `detector/bank2/prims.pkl`) are derived files and are not kept: step 1 of "Rebuild" makes them.

## Questions for the owner

**27 Oct:** the owner had no answers to these, so every one stands as built. They stay listed so that anyone who knows can change them.

- **Glass partitions:** 2.60 m with nothing above them is how the type is named. Should there be a solid bulkhead (or a
  ceiling) from 2.60 m up to the slab?
- **The terrace parapet** is built at the railing height, 1.10 m. Is that its height?
- **The two stair drawings do not line up.** Level 2 shows two flights side by side (DOWN to the south, UP to the north,
  9 risers each, landing to the west). Level 1 shows a flight running north, a quarter landing and a flight running west,
  over the Level 1 toilet. The model follows each drawing on its own level, so looking down the Level 2 stairwell you see
  the Level 1 toilet's walls. Which is right?
- **Floor to floor 3.70 m** (21 risers of about 0.176 m): please confirm. With Revit's default stair type it could be
  3.80–3.99 m.
- **Glass and pivot doors at 2.40 m** (no size in their names, so the most common height): please confirm.
- **The north stair** outside the north wall: drawn on Level 1 as tread lines with its rail; on Level 2 it is no longer
  floor (no door reaches it and all its risers are below the cut). Keep it, or leave it out altogether?
- **The lift-hall screens** by L1-027: glass to the full height, as built?

## What changed on 27 Oct (review findings)

| Finding | Verdict | What changed |
|---|---|---|
| SE terrace element built 3.70 m | Confirmed | Parapet rule: 1.10 m, kept at its height by Update (also fixes the Max follow reset) |
| Glass partitions built as solid walls | Confirmed | Revit wall-type rule: 19 glass panes 2.60 m, own Max objects, 6 glass transoms, lift-hall screens glass |
| ATM slot open | Confirmed | Object-in-gap rule: closed full height (its own object) |
| Stairs as fins, floor over the stairwell and lift shaft | Confirmed | No floor over stairs and lift shafts above the ground floor; UP / DOWN flights as 16 solid steps; other tread lines flat |
| Floor over the north stair | Confirmed | Railing-bounded areas only with a door and standing room and not mostly stair: 4.7 m² (L2) and 1.3 m² (L1) dropped |
| Room names overlap | Confirmed | Names move a row apart (or hide), bigger rooms first; the test checks no overlap |
| Slab bulges at concave facade corners | Confirmed | Plates follow the walls: 0.0 m² of slab lies more than 10 cm outside the walls, glass and railings (the terrace aside) |
| L1-023 lintel 10 cm behind the facade | Confirmed (detector line) | Detector unchanged; lintel depth from the walls beside the jambs puts it in the facade line |
| Test port collision | Confirmed | The test stops if the port already answers |
| Passage lanes bent to fit L2-019 | Confirmed | Doors through the middle only; passages checked as untouched (no lintel, no pane, nothing built), walking them is information |

## Rebuild

The detector and the drawing reader (`tools/prims.py`) are in `detector/` in the project folder (see its README).
`src/bank_project.json` points at the drawing caches (`detector/bank1/prims.pkl`, `detector/bank2/prims.pkl`: derived
files, not kept in the project) and at the detector mappings, all with paths relative to `src/`. Use Python with ezdxf,
shapely and matplotlib. The builder takes `strips` / `solidify` from `cad_test/src/merge_cad.py` and the outline helpers
from `presidential_test/src/geom.py`. The viewer embeds `viewer-modes/` unchanged. Run everything from the project folder.

    # 1. DWG -> DXF (LibreDWG 0.14), then the flattened drawing cache the detector and the builder both read
    mkdir detector/bank1 detector/bank2
    dwg2dxf -y -o detector/bank1/plan.dxf "I1201 - LEVEL 1 GENERAL ARRANGEMENT.dwg"
    dwg2dxf -y -o detector/bank2/plan.dxf "I1202 - LEVEL 2 GENERAL ARRANGEMENT.dwg"
    python -B detector/tools/prims.py bank1
    python -B detector/tools/prims.py bank2
    # 2. The openings (the detector, unchanged; about 1 s per level)
    python -B detector/openings.py detector/mappings/bank1.json bank_test/src/detector_out/openings_L1.json --png bank_test/src/detector_out
    python -B detector/openings.py detector/mappings/bank2.json bank_test/src/detector_out/openings_L2.json --png bank_test/src/detector_out
    # 3. The model -> src/bank_model.json, bank_stages.json, bank_summary.json, bank_topview.png (about 2 s)
    python -B bank_test/src/build_model.py
    # 4. The viewer and the Max script (both stamped with the same model data)
    python -B bank_test/src/make_html.py bank_test/bank_3d_preview.html
    python -B bank_test/src/generate_maxscript.py bank_test/Bangkok_Bank_Sampeng.ms
    # 5. Checks (headless Edge on port 9377; BANK_PORT / BANK_PROFILE / BANK_OUT to change)
    node bank_test/test_bank.mjs

The two DXFs and caches can be deleted after step 4; nothing else needs them. (To keep them out of the project, set
`OPENINGS_DATA` to another folder that holds `bank1/` and `bank2/` before steps 1 and 2, and point `cache` in
`bank_project.json` at the same place.)

The checks (22, about 25 s) cover:
- the replay's captions use this drawing's numbers, and the replay plays to the end and hands over;
- room names show, and none sits on another (both levels, and Level 1 alone);
- the Level 1 / Level 2 / both buttons work in Orbit and Walk, as do PgUp and PgDn;
- walls stop you at 40 random spots per level;
- every detected door can be walked through its middle both ways (exterior doors from inside);
- the 9 passages are left as they are: nothing overhead below 3 m at 1/4, 1/2 and 3/4, no glass across their line, no
  piece built for them (walking them is reported as information);
- every door is open up to its head with a lintel or glass transom above;
- the curtain-wall glass, the window panes and the glass partitions stop you, and the partitions stop at 2.60 m;
- the parapet stands at the railing height with nothing above; the ATM slot is closed to the top;
- on Level 2 there is no floor over the two stairs and the lift shaft; the 16 steps sit one riser apart;
- Ghost, the Camera photo name, the shared model-data stamp, and no page errors.

The test stops at once if something already answers on its debugging port (the shared launcher would attach to that
other browser and finally close it). A negative control (a copy of the model with the parapet at 3.70 m, the partitions at
3.70 m, a transom moved up, a step 10 cm off, the closure removed, the Level 2 floor holes filled and a lintel over a
passage) fails exactly those 7 checks, plus the stamp check (no Max script beside it).

The walk code (shared, not changed) casts its shoulder rays 7.5 cm apart, so the free end of a 10 mm screen could slip
between them. The page therefore adds invisible 8 cm collision skins round the thin pieces: the glass partitions and
screens, the panes and the rail ends. They are viewer-only and not in the Max script.
