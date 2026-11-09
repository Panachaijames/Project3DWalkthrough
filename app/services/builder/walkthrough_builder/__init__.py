"""The walkthrough builder (docs/upload/DESIGN.md U-3, U-6, U-7, U-10, U-11): a separate worker process in its own pinned
Python (services/builder/.venv, U-10.1) that converts, reads and builds uploaded drawings and writes a version's outputs.

It never imports walkthrough_api (pydantic) and the API never imports it: they meet only through the run folder's JSON
files (U-18.1). Run it with `python -B -P -m walkthrough_builder.job --run <run dir>` (U-3.2); tests with
`npm run test:builder`.

Owners (docs/upload/WORK_BREAKDOWN.md): the scaffold U0 wrote this file, roles.py, names.py, keys.py, contracts.py and
vendor/; U1 the intake and jobs (job, step, isolate, convert, losscheck, cache, runio, and after the scaffold jsonfile,
oslock); U2 the reader and suggestions (read, drawing, plangeom, units, levels, grid, areas, suggest, propose); U3 the
model builder (build/); U4 the outputs (out/).
"""

#: The builder's version: recorded in VersionInputs.builder.version (upload-contracts.ts section 2).
BUILDER_VERSION = '1'
#: The reader's version: names the cache folder read-<READER_VERSION>-<units> (U-4.2) and DrawingRead.reader.version.
READER_VERSION = '1'
