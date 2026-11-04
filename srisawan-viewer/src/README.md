# Srisawan viewer + 3ds Max script sources (6 Oct 2026)

Saved here on 9 Oct 2026 from the Claude Code scratch folder. Inputs: ../srisawan-rebuild/model_geometry.json and ../floor6-dxf/*.dxf.

    pip install --user ezdxf shapely matplotlib
    build_srisawan_merged.py        merge traced wall segments into one solid per wall run, smooth traced curves -> srisawan3d_merged.json
    make_srisawan_html_merged.py <out.html>   write ../Srisawan_3D_viewer.html (reads srisawan3d_merged.json and srisawan3d.json,
                                    both kept here, and the shared viewer code in ../../viewer-modes/)
    generate_maxscript_merged.py    write ../srisawan-rebuild/Srisawan_New_Layouts_Merged.ms from the merged solids
    check3d.py, check_merged.py     PNG checks
    build_srisawan.py, make_srisawan_html.py   first version (one box per segment; superseded)
    test*.mjs                       Node checks that every solid builds in three.js (npm install three@0.160.0)

Since 16 Oct the viewer also has the Build settings screen and build replay, Orbit / Walk / Ghost and the Camera tool,
shared with the house viewer (code, controls and browser tests: ../../viewer-modes/README.md). Rebuild from the project folder:

    python srisawan-viewer/src/make_srisawan_html_merged.py srisawan-viewer/Srisawan_3D_viewer.html
