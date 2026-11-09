"""The upload milestone's service layer (docs/upload/DESIGN.md U-3 - U-5, U-8.4, U-11.1, U-13; step U5): what the 24 new
routes do, over the Store and the JobRunner. Routes stay thin (they parse, call one function here and answer).

    naming.py      createProject's ids, the project naming and office ids (U-13.3)
    sourcefile.py  an upload's first bytes: DWG of R13 or newer, ASCII or binary DXF (U-5.1)
    projects.py    createProject, listOffices
    uploads.py     upload sessions in raw parts (U-5)
    runs.py        reading a run folder: the effective status (a gone worker is interrupted), RunInfo, writing job.json
                   in the API's three cases (U-3.2, U-3.4)
    validate.py    the run-done validation of the worker's outputs (U-3.2)
    adopt.py       revision-0 settings, the settings proposal adopted once (U-3.3), the units change (U-7.4)
    builds.py      createBuild ... deleteBuild, the draft's raw files
    save.py        saveBuild (U-11.1) and the office memory (U-8.4)
    cleanup.py     start-up and before-run clean-up (U-4.1) and the interrupted marking (U-3.4)
"""
