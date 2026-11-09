"""`python -m walkthrough_builder.out <model.json> --profile upload --date "4 Nov 2026" --sources dwg:mm --out <file.ms>`:
the 3ds Max generator from the command line (out/maxscript.py main(); docs/upload/DESIGN.md U-11.5). Owner U4."""
from .maxscript import main

raise SystemExit(main())
