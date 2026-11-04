"""The seed (DESIGN.md 9.2): rebuilds data/ from the prototype folders, which it only reads (no prototype code imported).

    sources.py        the seed table: which prototype files make which project version
    convert_suite.py  presidential_test/src/pres2_model.json -> BuiltModel v1 (6.3)
    convert_house.py  cad_test/src/house3d_merged.json + furniture_house.json -> BuiltModel v1 (6.4)
    stages.py         replay data: bank copied, suite renamed, house built from the page's caption functions (7.4)
    presentation.py   Presentation v1 per version, ported from each generator's Python (8)
    build.py          the version folders, version.json and meta.json, all checked before anything is committed
    __main__.py       python -m walkthrough_api.seed --prototypes <folder> --data <dir> [--force] [--reset-overrides]
"""
