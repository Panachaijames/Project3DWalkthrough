# Layer mapping, first run: presidential suite, Revit export (10 Nov 2026)

`suite_revit.json` in this folder is the layer-role file for `presidential suite_layout.dwg` (project folder; 2,280,952 bytes,
sha1 `9e84e27fef67773b73ec8ef42bc25f65a5f1c52c`), a Revit export of a hotel presidential suite made by the 3D team on 9 Nov 2026,
one plan per file. It was written from the layer list and from what is drawn on each layer, before the detector was run on this
drawing. Nothing from the detector's output was seen.

- **Conversion.** LibreDWG 0.14 `dwg2dxf` (DXF AC1032), exit 0, 1.5 s. It printed 264 "Skip HATCH common handles due to short
  handle stream", about 130 "Object handle not found" and a few unstable-class notices (MATERIAL, MLEADERSTYLE, TABLESTYLE).
  Checked against LibreDWG's own JSON dump of the DWG (`dwgread -O JSON`): every entity type has the same count in the dump and in
  the DXF (ARC 1,976, CIRCLE 55, ELLIPSE 268, HATCH 264, INSERT 311, LINE 36,663, LWPOLYLINE 434, MTEXT 50, POINT 120, SOLID 1,
  SPLINE 539, WIPEOUT 2), and no entity, matched by handle, is on another layer. In particular the 99 solid hatches on layer 0 are
  on layer 0 in the DWG too. As for L29 / L30, no second DWG reader was available. Output: `conversion_check.txt`.
- **Cache.** `tools/prims.py suite_revit`: 29,886 items in 10.8 s, every one tagged `suite_revit` (prims.py tags all items of a
  drawing name it does not know with that name: one plan per file, as for `l29` / `l30`).
- **Floor.** The mapping names that floor `suite_revit`, the same string as the cache tag. Every output record has
  `"floor": "suite_revit"`, so the answer key must use that floor name too.
- **Evidence.** `layer_census.txt` (entity types per layer at the top level and inside blocks, with sizes) and pictures of
  each layer over the plan. Helper scripts are in `../mapping_helpers/`; the pictures were left in the work folder, not the project.

## Units: millimetres, although the header says inches

The header has `$INSUNITS` = 1 (inches), `$LUNITS` 2, `$MEASUREMENT` 0. The geometry is in millimetres:

- The plan covers 23,510 × 13,076 units: 23.5 m × 13.1 m in mm (a suite), 597 m × 332 m in inches.
- Door swing arcs on A-DOOR have radii 700-930: leaves of 0.70-0.93 m. The door blocks are named `D01_1000X2250MM`,
  `D22 1800X2100MM` and `850X2400MM_D06`.
- S-COLS columns are drawn 500 × 1000, and their block is named `500W 1000D` (the solid fill is 500,000 units², 0.5 m²).
- Mullions are 100 × 50 (block `Rectangular Mullion - 100X50`). Partition cores are 100-200 thick and linings 15-25.

So `"units": "mm"`; prims.py divides by 1,000, and the cache is in metres.

## Roles, layer by layer (all 34 layers of the layer table)

Item counts are effective layers as prims.py reads them (layer 0 inside a block takes the INSERT's layer): top level / inside blocks.

| Layer | Items | What is on it | Role |
|---|---|---|---|
| `0` | 2,635 / 0 | **All interior partitions of the suite** (see below), the inner linings of the shell walls, and also loose furniture, an outline inside the glazing of each bay, and short lines across some doorways. No door-size arc (0 arcs of r 0.28-2 m and 20-125°) | **wall** |
| `A-WALL` | 249 / 58 | The shell only: the solid facets of the six facade bays, the corridor walls, the end walls. 60 solid fills, lines, one wall block | wall |
| `A-WALL-PATT` | 0 / 0 | Empty | wall (as bank1, L29) |
| `S-COLS` | 6 inserts (24 lines, 6 solid fills) | Concrete columns 500 × 1000 | column |
| `A-GLAZ-CURT` | 18 inserts (72 lines) | The glass panes (`System Panel - GLAZED`) of the curtain walls in the five bays at the top and the bay on the left | glass |
| `A-GLAZ-CWMG` | 42 inserts (131 lines, 9 pattern hatches) | The curtain-wall mullions (`Rectangular Mullion - 100X50`): the 0.1 m frame drawn along each glazed facet and the corner mullions | glass (as bank1) |
| `A-DOOR` | 102 / 41 (6 door blocks) | Door leaves (lines, thin rectangles), 16 swing arcs of r 0.70-0.93 m, sliding leaves with their arrows | door |
| `A-DOOR-FRAM` | 82 / 79 | Jamb frames at the door ends and frame lines across the openings (up to 1.73 m) | door |
| `A-DOOR-HDLN` | 4 arcs (dashed) | The swings (r 0.70 m, drawn 30° open) of the three glass doors of the shower and WC at x ≈ 9.5 m and of one more door with the same pull handle (x ≈ 23.0-23.7 m, y ≈ 4.8-5.2 m). Their leaves are on A-DOOR, and these arcs are their only swings | door |
| `S-STRS`, `S-STRS-MBND` | 0 / 0 | Only in block definitions that are not inserted: no stair in the plan | stair (harmless) |
| `A-DETL-GENF` | 160 / 32 | Lever handles drawn on door leaves (lines up to 0.112 m, arcs of r 3-5 mm). No swing, leaf or jamb, unlike the A-DETL-* layers of L29 | ignore (as bank1) |
| `A-GENM-HDLN` | 524 lines, 4 circles (dashed) | Hidden-line pull handles on the leaves of those four doors (a U-bar on stand-offs 3-5 cm off the leaf, with a knob). No arcs | ignore |
| `A-GENM` | 77 lines, 62 arcs | Bed throws and pillows on the three beds (16 door-sized arcs: r 0.30-0.97 m, sweeps 20-50°) and two hatched boxes against walls | ignore |
| `A-DETL` | 6 lines, `Centre` linetype | X-crosses in three shallow boxes behind double service doors (probably riser shafts): an annotation symbol | ignore (as bank1, L29) |
| `I-FURN` | 206 | Beds, pillows, bedside tables, rugs, and the edge of the round dining table (10 door-sized arcs) | ignore |
| `I-FURN-CHAR` | 8 inserts | Dining chairs | ignore |
| `M_Arredi` | 13 | A sofa | ignore |
| `I-WALL-HATT` | 13 | The cushions of that sofa (despite the name, no wall) | ignore |
| `G-IMPT` | 24 | A small fitting at the WC (0.37 × 0.25 m) | ignore |
| `P-SANR-FIXT` | 806 | Bath, basins, WC, shower mixers | ignore |
| `Q-CASE` | 17,191 / 5,650 | Casework (headboards, cabinets, a fluted panel), with about 17,000 tiny lines of wood-grain fill patterns | ignore |
| `Q-CASE-HDLN` | 58, dashed | Hidden casework lines | ignore |
| `Q-SPCQ` (frozen) | 30 inserts | Curtains along the glazing, TVs, a fridge (its block holds a 0.5 m door swing), lamps, a toilet-paper holder | ignore |
| `M-EQPM` | 271 | Two circles of short lines over the tables (probably ceiling equipment) and a fire-hose cabinet in the corridor wall | ignore |
| `E-LITE-EQPM` | 253 | Lamps and light fittings | ignore |
| `A-ANNO-IDEN` (frozen), `A-ANNO-NOTE` | 8 + 1 texts | Room names | ignore |
| `A-ANNO-DIMS`, `A-FLOR`, `Defpoints`, `G-ANNO-TEXT`, `ID-LOOSE`, `ID-LOOSE2` | 0 / 0 | Empty in model space | ignore |

No layer is left without a role.

## The decisions that matter

**1. Layer 0 is wall.** In this export, the interior partitions are on layer 0, not on A-WALL. A-WALL holds only the building
shell. On layer 0 they are drawn as solid-hatch cores with their face lines. Examples: 0.19 × 6.95 m at x 7.35 m,
0.15 × 5.81 m at x 11.5 m, 0.15 × 7.75 m at x 24.8 m, 0.205 × 3.33 m at x 20.4 m, and a 0.10 m core with 15 mm linings on both faces
at y 6.95-7.05 m. 15-25 mm lining fills run along the inside of the A-WALL shell. Without layer 0 the suite would have no interior
walls at all. The layer looks like an interior designer's drawing brought into the Revit model and exported on layer 0 with its
furniture. M_Arredi, I-WALL-HATT and G-IMPT are probably from the same import. That is a different habit from the bank and the
tower, whose partitions are on A-WALL.

The mapping gives roles to whole layers, so what else is on layer 0 comes along as wall material. The detector's own rules decide
what each piece becomes:

- **Furniture.** Thin closed outlines (armchair cushions with a mean width of 0.07-0.24 m; bar-stool circles of r 0.18-0.20 m,
  mean width 0.18-0.20 m) and parallel lines 4-45 cm apart (sofa, bar counter, headboard panels, bench, wardrobe fittings) join
  the wall solid. Wider outlines (the rug, the round tables of r 0.75 m and 0.5 m, a 0.45 × 2.0 m bench with mean width 0.379 m)
  do not.
- **Lines across doorways.** 5 of the 20 door-size swing arcs on A-DOOR and A-DOOR-HDLN have a layer-0 line along the whole
  closed-leaf position, within 4 cm (`door_lines_on_0.py`). Their hinges are at (11.71, 3.23), (13.32, 3.31) and (15.05, 3.31)
  (one double door), (20.57, 5.16) and (20.76, 3.39). For example, a 0.700 m line at y 3.409 runs from x 20.762 to 21.462,
  exactly across that door. With layer 0 as wall, these become wall-layer lines drawn across the doorways.
- **Bay outlines.** An outline drawn about 0.3-0.5 m inside the glazing of each bay (a window seat, a curtain pelmet or a
  floor-finish edge; the plan does not say which) becomes single wall-layer lines.

**2. Glazing.** There is no window layer. The facade glazing is curtain wall: panes on A-GLAZ-CURT, mullions and frames on
A-GLAZ-CWMG. Following the README ("curtain walls and glass partitions as glass") and the bank mapping (A-GLAZ-CWMG in glass),
both are glass. Only the curtain-wall panes and mullions are on glass layers. No glazing or glass screen inside the suite is
drawn on a glass or window layer, and no door is drawn in the curtain wall.

**3. Door layers.** A-DOOR, A-DOOR-FRAM and A-DOOR-HDLN are door, as for the bank and the tower. A-DOOR-HDLN matters here: it
holds the only swings of the four glass doors. The two hardware layers were looked at, not judged from their names (the L29
lesson). A-DETL-GENF holds lever handles and A-GENM-HDLN holds pull handles; neither has a swing, a leaf or a jamb. Both are
ignored. On a door layer, the pull handle's two long parallel lines, about 25-30 mm apart, could pass for a sliding leaf.

**4. Arcs off the door layers.** Arcs are read as door swings on every layer that is not ignored. The door-sized arcs outside
the door layers are all furniture or equipment: bed throws and pillows (A-GENM, I-FURN), the round dining table (I-FURN) and the
fridge door (Q-SPCQ). All three layers are ignored. Layer 0 has no door-sized arc.

**5. Frozen layers.** Q-SPCQ and A-ANNO-IDEN are frozen in the file (not shown to the author). prims.py does not read layer
states, so they are in the cache. Both are ignored, which matches what the author sees.
