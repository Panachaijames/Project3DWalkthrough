# CAD / PDF test pipeline (6 Oct 2026)

Scripts that produced `cad_test/house_3d_preview.html`, `cad_test/pdf_house_3d_preview.html` and the PNGs.
Saved here on 9 Oct 2026 from the Claude Code scratch folder. They are test scripts, not the product.

## Setup
    pip install --user ezdxf shapely pymupdf matplotlib numpy
    # DWG -> DXF: LibreDWG 0.14 (GPL-3.0), https://github.com/LibreDWG/libredwg/releases (libredwg-0.14-win64.zip)
    dwg2dxf -y -o plan.dxf "Test Sukhumvit Residence.dwg"      # see dwg2dxf_convert_log.txt for the warnings it printed

## DWG house (run in order, in a folder containing plan.dxf)
    analyze.py        layers, units, blocks, text, dimensions
    regions2.py       find the four drawings on the sheet (two plans, two elevations) -> regions.json (regions.py was a first try)
    regions3.py       tighten the two plan regions in regions.json
    align.py          grid labels in both plans -> floor shift (74.021 m); writes grid.json
    levels_grid.py    floor levels from the elevation level tags -> levels_grid.json
    build3d.py        extract wall / glass / window / stair lines per floor -> house3d.json (continuous lines only, tiny shapes dropped;
                      also the model's frozen origin "centre" and the floor "shift", 26 Oct)
    find_openings.py  (26 Oct) run the Phase 0 opening detector (openings.py, used as it is) on plan.dxf with the drawing's layer
                      mapping (openings_mapping.json), add the door / window heights from the elevations (heights.json)
                      -> openings.json (drawing metres), openings_detected.json (the detector's own output), prims.pkl (its cache).
                      Needs the detector folder: --detector DIR or OPENINGS_DETECTOR, else <project>/detector (two folders up),
                      or ../detector. Without heights.json: the plan defaults (2.10 / 0.90-2.10 m)
    merge_cad.py      pair wall face lines, fill, fuse into one solid per wall run -> house3d_merged.json (also floor plates);
                      then, with openings.json, cut the doors and windows in (openings3d.py): lintels, sills, window panes,
                      leaves drawn as glass removed; the floor plates are computed before the cut and stay as they were.
                      Stops when openings.json is from another plan.dxf or model frame (re-run find_openings.py)
    build_stages.py   what each build step saw, for the build replay -> house3d_stages.json: the drawing's lines by kind
                      (door symbols too), the wall pieces, the layers in the two plan areas and the counts the captions quote,
                      openings per floor included (needs plan.dxf, regions.json, grid.json, house3d.json, house3d_merged.json,
                      openings.json; from a few seconds up to 5 minutes)
    make_html_cad_merged.py <out.html>   write the Three.js viewer (make_html.py = older one-panel-per-line viewer)
    preview3d.py / crops.py / render.py  PNG previews and the colour-by-layer renders

The viewer (16 Oct) also has the Build settings screen and build replay, Orbit / Walk / Ghost and the Camera tool.
That code is shared with the hospital viewer and lives in ../../viewer-modes/ (see its README for controls and tests).
house3d.json, house3d_merged.json and house3d_stages.json are kept here so the viewer can be rebuilt without the DXF:

    python cad_test/src/make_html_cad_merged.py cad_test/house_3d_preview.html

Openings (26 Oct): rebuild from the DXF in this folder with

    python -B build3d.py && python -B find_openings.py && python -B merge_cad.py && python -B build_stages.py && python -B make_html_cad_merged.py ../house_3d_preview.html

Doors are open from the floor to their head with a lintel to the top of the wall, windows are a glass pane from the sill
to the head (a sill wall only above 0, a lintel unless the head reaches the top), passages are left as they are. Sliding
glazing that may be a door or a window (eitherKind) is glazed like a window, the sliding glass doors onto the terraces
included (27 Oct). Panes stand on the drawn glazing; lintels are as deep as the walls beside the jambs; grilles (A_Grill,
W_Grill: 'screen' layers) are not glazing and are not cut. Heights: heights.json, read from the elevations (ground doors and
windows to 3.00 m, upper to 2.60 m, windows from the floor; rows for particular openings, e.g. the double-height glazing to
3.90 m); both legs of a post-less glass corner take the same heights; a window over a low wall gets a 0.90 m sill. The viewer
keeps door and window heads where they are when the wall height is changed in Build settings, and a pane that reaches the top
of the wall follows it. Browser check of the openings: test_house_openings.mjs (doors walked through, passages left as they
were and no harder to walk than before the cut, windows stop you, lintels at the heads, no leaves in door swings);
test_house_openings_before.json holds the passage walk on the page from before the openings.

Furniture boxes (29 Oct): one coloured box per piece of furniture, kind = colour; the contract is ../../furniture/README.md (shared
with the bank). Run it last, in this folder, once the openings are built (a box in a door's approach is marked):

    python -B build_furniture.py [--config furniture.json] [--cache prims.pkl]

    build_furniture.py   reads prims.pkl (the flatten cache find_openings.py writes; plan.dxf beside it is only used to check
                         openings.json), regions.json, house3d.json, house3d_merged.json, openings.json and furniture.json
                         -> furniture_house.json (furnitureKinds + furniture in the model frame, plus offset = the model's centre,
                         floors and a furnitureReport of everything left out), ../house_furniture_list.csv (the family list for
                         the 3D team) and ../house_furniture_boxes.png. house3d*.json and openings.json are not changed.
    furniture.json       what the builder knows about this drawing: the furniture layers, the office's words per block name (the
                         names are cryptic: 'kjjkjkkkk' is a sofa), minSize / minDepth, and notes on what each layer and block draws.

The furniture of the plans is the interior designer's linked drawing (layer XR_L44$0$I-FURN): blocks with cryptic names (toilets,
chairs, sofas, beds, gym equipment, a whole kitchen) and thousands of loose lines where blocks were exploded. A block is one piece
(the rectangle around what it draws, a door swing included); a block with no name for a kind that holds two or more known blocks
(the kitchen) is an assembly and its parts are the pieces. Loose lines that touch form clusters and a cluster that fills its
rectangle is a box (chairs, a sofa, outlines of tables, benches and wardrobes): nothing names them, so their kind is 'other'.
Left out, with the numbers and every cluster in furnitureReport: dashed lines (above the cut plane), rows and L / U shapes of
touching outlines, strips under 25 cm, rugs and zones, WC fitting details under 25 cm. Not furniture here: TREE (long straight
lines and stair treads, no trees), FLOOR-PATTERN (pebbles), layer 0 (rugs, hanging rails, the TV). The upper plan is moved onto the
ground plan, as for the walls, so x_m of an upper-floor row in the list is on the ground plan's grid (add 74.021 m for the place on
the sheet). The cache and the DXF are not kept in the project: run it in a scratch copy of this folder with plan.dxf and prims.pkl
copied in, then copy the three outputs back.

The page (unchanged command: python -B cad_test/src/make_html_cad_merged.py cad_test/house_3d_preview.html) also reads
furniture_house.json and pastes in ../../furniture/furniture_boxes.js: 76 boxes (47 ground, 29 upper) in 9 kinds, 48 of them grey
'other' because the drawing does not say what they are, with a height box per kind, show / stops ticks, Keep doorways clear (5
boxes stand in an approach), the hover label and Save list (CSV); they come in at the end of the replay. Without
furniture_house.json (or with no pieces in it) the page is the old one byte for byte. Browser check of the furniture (29 checks,
port 9419): node cad_test/test_house_furniture.mjs; test_house_openings.mjs still passes 13 of 13 with the boxes shown.
What the boxes are not (29 Oct): one height per kind cannot suit the grey boxes (the six dining chairs are as tall as their table
at 750 mm); the L-shaped sofa is two overlapping 3.48 x 2.32 m boxes; each bed's box includes its bedside tables and rug (3.59 x
2.92 m); five wardrobes, the kitchen's cabinet runs and two basins are not boxed. There is no Max script for the house yet.

## PDF house (DH3 TYPE L, layered PDF)
    pdfinfo.py, pdflayers.py, pdfplan.py, pdfcheck.py   inspection
    pdf3d.py          walls/openings/stairs from PDF layers + line thickness -> house3d_pdf.json
    make_html_pdf.py <out.html>, preview3d_pdf.py, pdfviews.py
