# Presidential suite test (19 Oct 2026; furniture boxes 29 Oct 2026)

`layout presidential test.dwg` run through the CAD-to-3D pipeline: a one-floor hotel presidential suite, floor to floor
**3.00 m** as given for the project. It replaces the first try from `layout presidential xx.dwg`, which is kept in
[previous_xx_dwg/](previous_xx_dwg/).

| File | What it is |
|---|---|
| `presidential_3d_preview.html` | The 3D viewer: Build settings and build replay, Orbit / Walk / Ghost, Camera, room names, the furniture boxes with a height box per kind |
| `Presidential_Suite.ms` | The 3ds Max script: the same model as live, editable objects, and the furniture as Box primitives on a layer per kind |
| `presidential_topview.png` | Top view of what was built |
| `presidential_furniture_list.csv` | The family list for the 3D team: one row per furniture box |
| `presidential_furniture_boxes.png` | The suite with every furniture box in its kind colour; grey boxes carry their numbers |
| `test_presidential.mjs` | Browser checks (37): run `node presidential_test/test_presidential.mjs` from the project folder |
| `test_presidential_maxscript.py` | Text checks of the Max script against the model (151): `python -B presidential_test/test_presidential_maxscript.py` |
| `previous_before_furniture_2026-10-29/` | The Max script of 26 Oct, the one the owner ran (no furniture) |
| `src/` | The scripts and the data they made (see "Rebuild" below) |

## What was built

| Part | Count | Height | From |
|---|---|---|---|
| Walls | 12 wall runs + 2 round columns | 3.00 m | The wall layer `A-1.Netcat - tuong`: solid fills, thin outlines, paired double lines |
| Walls on the corridor side | 3 runs, 0.18–0.25 m | 3.00 m | **Not drawn on any layer**; added along the designer's room outlines |
| Lintels over doors | 17 | 2.10 m up | One per door, exactly in the wall's depth; none over the wide open passages |
| Glass | 15 pieces | 3.00 m | Octagonal facade (`A-4. Dim` double line), north and south facades (inferred), a fixed panel by the jacuzzi, the 9 stacked panels of the study / living partition (drawn open) |
| Balustrade | 68.5 m of frameless glass | 1.10 m (assumed) | `KT-Lancan` block, round the terrace and along the north and south facades |
| Terrace | C-wall backrest and bench, cabana backrests and lounge bed, 2 decks, 4 pergola posts | 0.45 / 0.90 / 2.70 m (assumed) | Wall layer and deck hatches |
| Jacuzzi zone | 2 low kerbs | 0.10 m | The unfilled edge lines; the zone is probably sunken (see questions) |
| Floor slab | 648 m², terraces included | 0.25 m thick | Balustrade's outer edge and the outer faces of the corridor-side walls |
| Room names | 16 | | The drawing's labels, in English, placed in the middle of each room |

Doors: 16 doors and 6 open passages, all walkable both ways in the viewer (the entrance and the service door lead to the
corridor, which is not in this drawing). Furniture, bathroom fittings, curtains and trees are coloured boxes since 29 Oct (see "Furniture boxes"); the jacuzzi tub is not built. The doors are the hand-written list in `src/build_model.py`. The openings detector (`../detector/`, 27 Oct; the same on 28 Oct after its fixes, which dropped 4 of its extra passages on this drawing) finds 20 of the 21 openings in this drawing's answer key (it misses the movable glass partition) but is not wired into this model.

## Try the 3ds Max script

1. Open 3ds Max with a **new, empty scene** (the script will not touch a scene that has objects in it).
2. *Scripting → Run Script…* and pick `Presidential_Suite.ms` (or drag it onto a viewport).
3. A small window opens. Leave the defaults and press **BUILD THE SUITE**. Build sets System Units to metres.
4. A message says how many objects were built (198: 62 parts, 16 room names and 120 furniture boxes) and whether any failed
   its check; details in the *MAXScript Listener* (F11). If no window opens at all, the Listener shows a syntax error and its
   line: tell us the line, and use the 26 Oct script in `previous_before_furniture_2026-10-29/` meanwhile.
5. *Save As* to keep it.

Every part is a **live object, not an Editable Poly**: an editable spline (the outline) + an **Extrude** modifier whose
output is a mesh + a Smooth modifier.
- **Change a height:** the Extrude amount on that object, or set *Floor to floor* and press **Update heights** (walls,
  columns, glass, lintel tops and the full-height panel follow; balustrade, terrace pieces and slab keep theirs).
- **Change an outline:** go to the spline level under the modifiers and move vertices.
- **Editable Mesh:** tick *Collapse to Editable Mesh* before Build, or press **Collapse all now** afterwards (the furniture
  boxes stay Box primitives).
- **Furniture heights:** change a kind's number in the window and press **Apply furniture heights**. *Furniture boxes only*
  adds just the boxes to the scene built from the 26 Oct script: it takes the level from the window's *Floor level*, so type
  the level that scene was built at first (0.00 unless you changed it).
- **Position:** at the drawing's own coordinates in metres, so it lines up with the DWG imported in metres. Untick
  *At the drawing's own coordinates* to build it centred on the origin. Each object's pivot is at the middle of its own
  outline.

| Layer | Objects |
|---|---|
| `PS_Walls`, `PS_Columns` | 12 wall runs, 2 columns |
| `PS_Lintels` | 17 door lintels (2.10 m to the ceiling) |
| `PS_Glass` | 15 glass pieces (facades, partition panels, the transom over the terrace door) |
| `PS_BuiltIns` | The full-height panel behind the living-room console |
| `PS_LowWalls` | Terrace C-wall and bench, cabana backrests and lounge bed, jacuzzi kerbs |
| `PS_Balustrade`, `PS_Decks`, `PS_Pergola`, `PS_Slab` | Balustrade, 2 terrace decks, 4 pergola posts, the floor slab |
| `PS_RoomNames` | 16 text shapes |
| `PS_suite_Furn_Bed`, `PS_suite_Furn_Seat`, ... | The 120 furniture boxes, one layer per kind (13), each named `PS_suite_Furn_<kind>_<nnn>_<family>` with its family, block, layer and handle as user properties |
| `PS_Datums` | A hidden point at the DWG origin, with the source and heights in its properties |
| `PS_Check_Failed` | Should be empty: anything here failed the closed-solid, height or position check |

**The owner ran it in real 3ds Max on 26 Oct 2026 and reported it good.** Before that, an independent review checked it
against the MAXScript reference and a second reviewer re-checked each finding; the 10 that held up are fixed (pivots at
each part instead of the drawing origin 3.5 km away, zoom to the suite, sharp 30-degree corners, no scale spinner that
only scaled the plan, Update heights finding the Extrude by type) and 3 were disproved. The viewer and the script carry
the same model-data stamp, and the browser checks compare them. **29 Oct: the furniture boxes are added and not yet run
in 3ds Max** (checked as text, by a lint and a mock interpreter; without the furniture the generator writes the 26 Oct script
byte for byte, and with it the new script only inserts lines).

## Furniture boxes (29 Oct 2026)

Every piece of furniture, the bathroom fittings, the curtains and the trees are now **one coloured box each, colour = kind**,
with a **height in mm per kind** that can be typed in the viewer and in the Max script's window; boxes stop you in Walk and not
in Ghost (the owner's decisions of 28 Oct; the shared code and its contract are in `../furniture/`). **120 boxes in 13 kinds:**

| Kind | Boxes | Height (mm) | Notes |
|---|---|---|---|
| TV / wall screen | 1 | 600, hanging at 900 | the recessed 55-inch TV |
| Curtain | 21 | 2700 (assumed: the slab above leaves 2.75 m) | do not stop you |
| Lamp | 9 | 500 | 4 stand on the bedside / coffee tables, 2 on the dining console (their tables' tops), 3 on the floor (a floor lamp and two at the window bench) |
| Plant | 12 | 2500 (assumed) | the trees on the terraces: boxes the size of their canopies, which stop you (untick "stops" for Plant to walk under them) |
| Sanitary fitting | 5 | 850 | toilet, basins |
| Appliance | 2 | 900 | minibar, hob |
| Bed | 1 | 500 | the king bed |
| Chair / stool | 14 | 450 | 12 dining chairs, the tufted bench, a chair |
| Sofa / armchair | 7 | 800 | the curved sectionals, the 6 m banquette, lounge chairs |
| Table / desk | 2 | 750 | the console table and the study's meeting table |
| Coffee / side table | 2 | 450 | the bedside tables |
| Tall cabinet / wardrobe | 3 | 2100 | the closet's wardrobes |
| Other furniture | 41 | 750 | 11 blocks with no name in the drawing and 30 groups of loose lines: grey, numbered in the picture and the list |

**How they are made** (section 6 of `src/build_model.py`, with the layers and words in the new `src/furniture.json`): a piece is a
block on one of the 9 furniture layers (`A-2.Noi That`, the furniture layer, `A-4. Cay` for the trees, the `Xr_SDC...` layers of the
linked furniture drawing: loose furniture, curtains, lamps, sanitary fittings, and three blocks on `A-4. Dim`), its box the smallest
rotated rectangle round what is drawn in it. The kind comes from the block's name (80 pieces: dining chairs, bed, TV, minibar ...),
or from a word in `furniture.json` where the block's name is a scribble but its picture leaves no doubt (`jdlkasdjkla` = tree,
`sdhsdfhsdfh` = curved sofa, `*U1636` = wardrobe ...: 20 blocks, to be confirmed by staff). Left out on purpose: the dimension blocks,
the 9 movable glass panels (already built as glass), the door symbols, the balustrade block, the terrace daybed (built as low walls),
a floor drain, and **the whole north-west terrace lounge, drawn as one 6.7 x 4.2 m block** (sectional, armchairs, tables, rug: one box
would wall off the terrace). 30 groups of loose lines on the furniture layer became boxes too; nothing names them, so they are grey.

**Doorways:** 7 boxes stand in the approach of 7 of the 22 doors and openings (one of them is a curtain); with *Keep doorways clear*
ticked (the default) all 22 can be walked through; with it off the kitchen run blocks D8 and boxes block the passages O1 and O2.

**For the 3D team:** `presidential_furniture_list.csv` (120 rows, UTF-8 with BOM) and `presidential_furniture_boxes.png`, where every grey
box carries its number (`suite-other-012` ...) so the owner can say what it is; a word in `src/furniture.json` then names that block for
good. In 3ds Max the boxes are Box primitives on the layers `PS_suite_Furn_<Kind>` (13), with the height spinners and *Apply furniture
heights*; **not yet run in 3ds Max.** The script of 26 Oct, the one the owner ran, is kept in `previous_before_furniture_2026-10-29/`.

## How the drawing was read

| Item | This drawing | Automatic? |
|---|---|---|
| DWG → DXF | LibreDWG 0.14; 200 layers in the file; 5,951 drawing items in the suite area, on 36 of them | Yes |
| Walls | On their own layer, mostly with solid fills: no furniture had to be set aside (the old drawing needed five areas set aside by hand) | Yes |
| Corridor-side walls | Missing on every layer: only the designer's room outlines (Defpoints) mark them. Added 0.25 m (party wall, kitchen side) and 0.18 m (gym notch), as in the office's earlier drawing of this floor | Rule + three given lines |
| Glass facade | Not on a glass layer. The octagon is a 0.18 m double line on `A-4. Dim` with two solid piers and a terrace door; the north and south glazing is inferred from the room outlines and the curtains behind the balustrade | Rule + given layers |
| Doors | 5 door blocks, 9 doors drawn as arcs on the visible-line layers, a pocket door, a movable partition; door heights not in the drawing (2.10 m) | Rule + door list |
| Terrace | Balustrade, decks (hatches), C-wall and cabana on the wall layer; heights not in the drawing | Rule + assumed heights |
| Room names | 16 labels (`A-Text`), placed in each room's middle (the labels sit beside their rooms in the drawing) | Yes |

**What was wrong in the previous model** (from `layout presidential xx.dwg`): walls were found by pairing lines on
layer 0, so the octagon's glass facade became a 0.43 m solid wall, a gym bench became a wall, rooms on the far east
side that are not in the suite were built, and several real walls were missing (the study's south wall, the wall between
the gym and the yoga area, most of the bedroom's diagonal wall).

## Questions for the owner

**Answered 26 Oct 2026: keep the heights as built.** Doors 2.10 m everywhere (entrance included), balustrade 1.10 m,
terrace seating backrests 0.90 m, pergola posts 2.70 m with no beams, a 0.10 m kerb between the bath and the jacuzzi.

Still open:
- Should the north balustrade continue the last 1.6 m to the gym's corner?
- Jacuzzi zone: it reads as sunken 0.45 m with steps from the bath; the tub's depth.
- Corridor-side walls: 0.25 m and 0.18 m taken from the earlier drawing of this floor; confirm.
- **Furniture (29 Oct):** what are the 11 grey blocks with no name (numbered in `presidential_furniture_boxes.png`: a
  sideboard under the TV, a pouf, round stools, two wall capsules, a gym bench, sauna benches, a massage table ...)? Are the
  20 scribbled block names read right (trees, sofas, wardrobes, basins, hob, bench, meeting table, floor lamp)? Trees 2.5 m
  and curtains 2.7 m high? Should the terrace lounge (one block for a whole seating group) be split into its pieces by hand?

## Rebuild

From the project folder (needs Python with ezdxf, shapely and matplotlib; uses `cad_test/src/merge_cad.py` for the
pairing and `viewer-modes/` for the viewer):

    # 1. DWG -> DXF (LibreDWG 0.14 for Windows, run from its own folder so it finds its DLL; ~100 MB, not kept here)
    dwg2dxf -y -o presidential_test/src/plan.dxf "layout presidential test.dwg"
    # 2. The model -> src/pres2_model.json, src/pres2_stages.json, src/pres2_topview.png (first run ~30 s, then cached)
    python presidential_test/src/build_model.py presidential_test/src/plan.dxf
    #    (it also writes presidential_furniture_list.csv and presidential_furniture_boxes.png; layers and words: src/furniture.json)
    # 3. The viewer and the Max script
    python presidential_test/src/make_html.py presidential_test/presidential_3d_preview.html
    python presidential_test/src/generate_maxscript.py presidential_test/Presidential_Suite.ms
    # 4. Checks
    node presidential_test/test_presidential.mjs                 # 37 browser checks (PRES_PORT to change the port 9344)
    python -B presidential_test/test_presidential_maxscript.py   # 151 text checks of the Max script

`src/floor_spec.json` holds the slab outline, the balustrade line and the terrace pieces worked out from the drawing.
The rules and the few hand-given items (corridor-side walls, door list, room names) are at the top of `src/build_model.py`.
