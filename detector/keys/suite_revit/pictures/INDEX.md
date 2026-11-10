# Pictures of `presidential suite_layout.dwg` (cache `suite_revit`)

Drawn from the flattened drawing cache only (`prims.pkl` in the run's WORK folder), with
`../scripts/draw_pictures.py`. No detector output was read or drawn.

- **Coordinates are drawing metres** (DXF millimetres / 1000), the same as the cache and the detector. Every picture has
  a labelled grid: 1 m lines labelled on all four sides with 0.5 m minor lines (the `detail_*` close-ups: 0.5 m lines
  labelled, 0.1 m minor lines).
- **Colour = layer** (legend on the right of every picture). Solid fills (SOLID hatches) are shaded in their layer's colour.
  Layer 0 is brown: it carries the interior partitions **and** furniture and casework outlines.
- **Dashed** = the entity itself has a dashed or hidden linetype (door swings, heads over openings, overhead or hidden
  lines) or sits on a dashed layer (`A-DOOR-HDLN`, `A-GENM-HDLN`, `Q-CASE-HDLN`).
- **Block names** are printed at the insert point of blocks drawn around it (doors, columns) and otherwise at the middle
  of each cluster of the block's geometry (curtain-wall panels and mullions, whose insert points lie far away).
  `[mirrored]` marks a mirrored insert. Room names are the drawing's own texts (layer `A-ANNO-IDEN`, frozen in CAD).
- The plan's geometry spans x 1.569 to 25.079, y 0.008 to 13.084. Its east edge (x 25.079) and south edge (y 0.009) are
  the Revit view's crop: line work is cut there.

## Overall plans (box x 1.0 to 26.0, y -0.5 to 13.5)

| File | Shows |
|---|---|
| `overview_all.png` | the whole plan, every layer, room names, door / wall / column block names; the 18 tile boxes dashed magenta |
| `overview_structure.png` | the same with only `A-WALL`, layer 0, `S-COLS`, the curtain-wall layers, the door layers, `A-DETL`, `A-GENM(-HDLN)`. Layer 0 still shows the furniture drawn on it |
| `overview_layer0.png` | layer 0 alone (brown) with `A-WALL` in light grey for reference: what sits on layer 0 |

## Close-up tiles (6 x 6 m, all layers)

Columns A to F run west to east, rows 1 to 3 south to north. Neighbouring tiles overlap by 2.2 m (east-west) and 2.0 m
(north-south), so anything up to 2 m wide lies whole in at least one tile.

| Tile | x from | x to | y from | y to | Mainly (room names of the drawing; others described in `../description.md`) |
|---|---|---|---|---|---|
| `tile_A1.png` | 1.0 | 7.0 | -0.5 | 5.5 | MASTER BEDROOM south part, west bay (lower half), south wall, south-west column |
| `tile_B1.png` | 4.8 | 10.8 | -0.5 | 5.5 | MASTER BEDROOM east part, BEDROOM FOYER, dressing area, walk-in wardrobe (west part) |
| `tile_C1.png` | 8.6 | 14.6 | -0.5 | 5.5 | walk-in wardrobe, small room south of the FOYER, FOYER, corridor (west end), shaft and fire-hose cabinet |
| `tile_D1.png` | 12.4 | 18.4 | -0.5 | 5.5 | FOYER, corridor and its service risers, BAR (south-west) |
| `tile_E1.png` | 16.2 | 22.2 | -0.5 | 5.5 | corridor (with the alcove by the south column), BAR, BOH. |
| `tile_F1.png` | 20.0 | 26.0 | -0.5 | 5.5 | BOH., unlabelled room east of it, corridor east end (crop at x 25.079), risers |
| `tile_A2.png` | 1.0 | 7.0 | 3.5 | 9.5 | MASTER BEDROOM: west bay, bed |
| `tile_B2.png` | 4.8 | 10.8 | 3.5 | 9.5 | MASTER BEDROOM east part, BEDROOM FOYER, MASTER BATHROOM (vanity, WC, glass screen) |
| `tile_C2.png` | 8.6 | 14.6 | 3.5 | 9.5 | MASTER BATHROOM (WC, shower), FOYER, LIVING & DINING AREA (west) |
| `tile_D2.png` | 12.4 | 18.4 | 3.5 | 9.5 | FOYER, LIVING & DINING AREA, BAR |
| `tile_E2.png` | 16.2 | 22.2 | 3.5 | 9.5 | dining table, BAR, BOH., lobby and wardrobe of BEDROOM 2 |
| `tile_F2.png` | 20.0 | 26.0 | 3.5 | 9.5 | BEDROOM 2 (south part), its lobby, the unlabelled room x 22.9-24.8, BOH. |
| `tile_A3.png` | 1.0 | 7.0 | 7.5 | 13.5 | MASTER BEDROOM north part, west bay (upper half), north bay 1, north-west column |
| `tile_B3.png` | 4.8 | 10.8 | 7.5 | 13.5 | MASTER BEDROOM north-east, MASTER BATHROOM, north bays 1 and 2 |
| `tile_C3.png` | 8.6 | 14.6 | 7.5 | 13.5 | MASTER BATHROOM (bath, shower), LIVING & DINING AREA, north bays 2 and 3, column |
| `tile_D3.png` | 12.4 | 18.4 | 7.5 | 13.5 | LIVING & DINING AREA, north bays 3 and 4 |
| `tile_E3.png` | 16.2 | 22.2 | 7.5 | 13.5 | dining area, north bays 4 and 5, BEDROOM 2 west wall, column |
| `tile_F3.png` | 20.0 | 26.0 | 7.5 | 13.5 | BEDROOM 2, north bay 5, east wall |

## Close-ups of drawing conventions (examples of how a kind of thing is drawn; not a list of openings)

| File | x from | x to | y from | y to | Shows |
|---|---|---|---|---|---|
| `detail_pocket_door.png` | 6.9 | 8.0 | 1.9 | 3.7 | a pocket (cavity) sliding door: wall split round the pocket, leaf inside it, slide arrow on `A-DOOR`, two continuous layer-0 core lines across the opening, frames on `A-DOOR-FRAM` |
| `detail_hinged_door.png` | 10.3 | 12.0 | 3.4 | 5.0 | an exploded hinged door: leaf as a 40 mm rectangle drawn open 90 degrees, dashed arc, frames, lever handle on `A-DETL-GENF` |
| `detail_glass_screen_doors.png` | 8.9 | 10.0 | 5.0 | 8.1 | the 10 mm glass screen (two lines 10 mm apart, layer 0) between two continuous lines 0.10 m apart, glass leaves drawn open 30 degrees, dashed swings (`A-DOOR-HDLN`), dashed handle outlines (`A-GENM-HDLN`) |
| `detail_bifold.png` | 9.0 | 10.2 | 0.7 | 3.5 | a four-panel bi-fold door drawn folded (zigzag on `A-DOOR`) with its dashed track (layer 0) |
| `detail_head_lines.png` | 12.6 | 15.8 | 4.4 | 5.8 | a gap without a leaf: the solid fill stops, the two face lines go on across the gap dashed |
| `detail_service_doors.png` | 14.9 | 17.5 | 0.4 | 3.9 | door blocks of the corridor: leaves drawn open 35 degrees, frame lines across the opening (`A-DOOR-FRAM`), X marks of the risers behind (`A-DETL`, layer 0) |
| `detail_unit_doors.png` | 18.8 | 22.2 | -0.2 | 1.4 | two door blocks (D01) whose wall face lines (`A-WALL`) run on across the openings; leaves and arcs cut by the crop at y 0.009 |
| `detail_bay.png` | 3.4 | 7.7 | 11.0 | 13.3 | a curtain-wall bay: glass panels and mullions in blocks, frame lines on both sides of the glass, corner wedges (block `Walls 13`), solid angled facade wall, dashed layer-0 line inside the bay, curtains (frozen `Q-SPCQ`) |

To redraw everything: from `detector/keys/suite_revit/scripts`,
`python -B draw_pictures.py <WORK>/suite_revit/prims.pkl ../pictures` (about 35 s).
