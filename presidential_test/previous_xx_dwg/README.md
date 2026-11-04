# Presidential suite: a second office's drawing (test, 19 Oct 2026)

`layout presidential xx.dwg` run through the same pipeline as the DWG house, to see how it copes with a drawing from a
different office. One floor (FL-01), floor to floor **3.00 m** as given for the project.

| File | What it is |
|---|---|
| `presidential_3d_preview.html` | The 3D viewer: Build settings and build replay, Orbit / Walk / Ghost, Camera, the room names from the drawing |
| `Presidential_Suite.ms` | The 3ds Max script: the same model as editable geometry |
| `presidential_topview.png` | Top view of what was built: walls (brown), terrace parapet (orange), floor slab (grey) |
| `src/` | The scripts and the data they made (see "Rebuild" below) |

## Try the 3ds Max script

1. Open 3ds Max with a **new, empty scene** (the script will not touch a scene that has objects in it).
2. *Scripting → Run Script…* and pick `Presidential_Suite.ms` (or drag it onto a viewport).
3. A small window opens. Leave the defaults (wall height 3.00 m, parapet 1.10 m, floor level 0.00, scale 1.0) and press **BUILD THE SUITE**.
4. A message says how many objects were built and whether any wall failed its check. Details are in the *MAXScript Listener* (F11).
5. Have a look, then *Save As* if you want to keep it.

What you should get, in metres, at the DWG's own coordinates (so it lines up if you import the DWG in metres):

| Layer | Objects | What to check |
|---|---|---|
| `PS_Walls` | 24 Editable Polys, one per wall run, 3.00 m high | Select one: it is one closed solid you can edit (move vertices, extrude, cut). Curved walls should look smooth |
| `PS_Parapet` | 2 Editable Polys, 1.10 m | The terrace edge under the balcony railing |
| `PS_Slab` | 1 spline + Extrude modifier, 0.25 m under the floor | Change the Extrude amount to change the thickness |
| `PS_RoomNames` | 17 text shapes | Room names from the drawing (Vietnamese accents become plain letters) |
| `PS_Datums` | A point at the DWG origin | Its properties record the source and heights |
| `PS_Check_Failed` | Should be empty | Any wall here failed the closed-solid, height or position check |

Please note whether it ran, how long the build took, and anything that looks wrong; that is next action 1 in the plan.

## How the drawing was read

| Step | This drawing | Automatic? |
|---|---|---|
| DWG → DXF | LibreDWG 0.14; 24 layers in both files; 140 error lines of the same harmless kinds as the house (text formatting, colours) | Yes |
| Walls | Drawn on **layer 0** together with loose furniture, so the layer name cannot pick them out. Found instead by shape: straight lines drawn directly on layer 0 (not inside blocks), paired with a parallel line 60–330 mm away (walls and partitions) or 450–520 mm away (the thick edge band) | Yes |
| Furniture that pairs up like walls | Five areas set aside: the central dining table and the ring around it, the terrace dining table and chairs, the terrace bar, a bath tub, the stair treads in the core | **By hand** (the check-and-fix screen's job in the product) |
| Terrace edge | The wall band under the balcony railing (layer KT-Lancan) became a 1.10 m parapet, so the terrace stays open | Yes, by rule |
| Doors and windows | Layer KT-Cua: shown in the replay; door openings are the gaps between wall runs | Yes |
| Room names | 17 from the drawing's own labels (the house drawing had none) | Yes |
| Heights | Not in the drawing: floor to floor 3.00 m from the project | Given |

**What this means for Phase 0:** the plan's gate says a second author's file should need only a layer-mapping change. That did
not hold here, because this office does not put walls on a wall layer. Finding walls by shape worked, but furniture drawn the
same way still needs a person to set it aside. The check-and-fix screen therefore needs a "this is furniture, not a wall"
tool, not only a layer list.

## Rebuild

From the project folder (needs Python with ezdxf and shapely; uses `cad_test/src/merge_cad.py` for the pairing):

    # 1. DWG -> DXF (LibreDWG 0.14 for Windows, run from its own folder so it finds its DLL)
    dwg2dxf -y -o presidential_test/src/plan.dxf "layout presidential xx.dwg"
    # 2. Walls, parapet, slab, room names and the replay data -> src/pres3d_merged.json, src/pres3d_stages.json
    python presidential_test/src/pres_build.py
    # 3. The viewer and the Max script
    python presidential_test/src/make_html_pres.py presidential_test/presidential_3d_preview.html
    python presidential_test/src/generate_maxscript_pres.py presidential_test/Presidential_Suite.ms

The furniture areas set aside by hand are the `EXCLUDE` list at the top of `src/pres_build.py`.
