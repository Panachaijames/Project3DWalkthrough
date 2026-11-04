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
    build3d.py        extract wall / glass / window / stair lines per floor -> house3d.json (continuous lines only, tiny shapes dropped)
    merge_cad.py      pair wall face lines, fill, fuse into one solid per wall run -> house3d_merged.json (also floor plates)
    build_stages.py   what each build step saw, for the build replay -> house3d_stages.json: the drawing's lines by kind,
                      the wall pieces, the layers in the two plan areas and the counts the captions quote (needs plan.dxf,
                      regions.json, grid.json, house3d.json, house3d_merged.json; from a few seconds up to 5 minutes)
    make_html_cad_merged.py <out.html>   write the Three.js viewer (make_html.py = older one-panel-per-line viewer)
    preview3d.py / crops.py / render.py  PNG previews and the colour-by-layer renders

The viewer (16 Oct) also has the Build settings screen and build replay, Orbit / Walk / Ghost and the Camera tool.
That code is shared with the hospital viewer and lives in ../../viewer-modes/ (see its README for controls and tests).
house3d.json, house3d_merged.json and house3d_stages.json are kept here so the viewer can be rebuilt without the DXF:

    python cad_test/src/make_html_cad_merged.py cad_test/house_3d_preview.html

## PDF house (DH3 TYPE L, layered PDF)
    pdfinfo.py, pdflayers.py, pdfplan.py, pdfcheck.py   inspection
    pdf3d.py          walls/openings/stairs from PDF layers + line thickness -> house3d_pdf.json
    make_html_pdf.py <out.html>, preview3d_pdf.py, pdfviews.py
