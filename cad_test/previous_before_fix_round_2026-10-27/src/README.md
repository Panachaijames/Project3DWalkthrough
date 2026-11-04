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

## PDF house (DH3 TYPE L, layered PDF)
    pdfinfo.py, pdflayers.py, pdfplan.py, pdfcheck.py   inspection
    pdf3d.py          walls/openings/stairs from PDF layers + line thickness -> house3d_pdf.json
    make_html_pdf.py <out.html>, preview3d_pdf.py, pdfviews.py
