# Upload a DWG and build it in the app: milestone design (4 Nov 2026; revised the same day after two independent reviews,
# see "Review notes" at the end)

The architect's design for the milestone the owner chose on 4 Nov ("next is uploading DWG first"): a staff member makes a
project (or a new version of one), uploads its DWG files (or DXF from AutoCAD), maps the layers, sets up the floors,
builds, checks and fixes, and saves a walkthrough version that opens in the viewer with its downloads. Builders work from
this file (sections cited **U-n**), `upload-contracts.ts` (shapes), `ACCEPTANCE.md` (what "done" means and the tests) and
`WORK_BREAKDOWN.md` (who owns which files). The foundation's `../DESIGN.md` (cited **D-n**), `../contracts.ts`, the
schema and `../contract-issues/I.md` still hold for everything this file does not change.

**In:** the staff workflow (new project or new version, upload, conversion, layer mapping, floors, build, a first
check-and-fix screen, save); the pipeline as server jobs; LibreDWG in a stable place with a loss check; one reading pass;
the per-office layer memory; the bank's builder made general and moved into the app with the openings detector and the
furniture kit; the replay recorded from the build; the Max script generated from the model; the version saved through
`create_version` (D-9.5). **Out, with seams kept (U-16):** rooms and slabs from the wall network, climbable stairs, box
editing, real furniture models, finishes and lights, walls found by shape on a mixed layer, per-piece role changes, login,
anything online. **Never:** deploys, publishes, releases; writes outside `app/`.

**Reference material** in `docs/upload/reference/` (copied on 4 Nov from the session scratchpad, which can be cleared;
scratch prototypes to port, not app code): `run_isolated.py` (a Job Object runner), `nothing_lost_stream.py` (the loss
check), `read_drawing.py` (the reading step), `areas_propose.py` (sheet islands), `expand_probe.py` and `missing_plot.py`
(empty inserts, a picture of lost items), `geom_check.py` (DWG against DXF geometry), `house_align.py` (the house's grid
labels), `pres_rules.py` (the suite's outline measurements), `bank_chain.ps1` (the timed bank chain) and
`derived_detector_mapping_bank1.json` (the derived mapping that reproduced the bank's openings).

Contents: 0 facts this rests on . 1 terms . 2 staff workflow . 3 pipeline and jobs . 4 where files live . 5 upload .
6 converter . 7 reading the drawing . 8 layer mapping . 9 floors . 10 the general builder . 11 a version's outputs .
12 check-and-fix . 13 API . 14 web app . 15 frozen contracts . 16 seams . 17 risks . 18 decisions

---

## 0. Facts this design rests on (measured 4 Nov 2026 by four readers, scratch copies only)

| Fact | Consequence |
|---|---|
| The bank chain rerun from the two DWGs (LibreDWG -> `prims.py` -> detector -> `build_model.py` -> `generate_maxscript.py`) gives **byte-identical** `model.json` (sha1 `c3a9408304a240b83c36f5c5c53db56b50a72c64`), `stages.json` (`c7c01b67...`), the CSV (`b528bb2320ef...`), `topview.png` (`f084b556503c...`) and `Bangkok_Bank_Sampeng.ms` (`615d50137bdb...`) in 25.6 s | the bank re-upload can reproduce v2 exactly; it is the golden test of the port (U-10.3) |
| LibreDWG 0.14 is deterministic: both bank DXFs equal the 26 Oct ones (`9167d084...` 2,817,940 B; `c88491df...` 7,923,920 B) | store the DWG and the DXF's sha1, not the DXF (U-4) |
| The LibreDWG folder the brief names (`...fedf5601.../scratchpad/libredwg/`) has no DLLs and cannot run (exit 127). The release zip (`libredwg-0.14-win64.zip`, sha1 `edb5c01152c3ea9bcb46175aa3403fd18b941ff3`, 75 entries incl. `libredwg-0.dll` 31.2 MB, `libiconv-2.dll`, `libpcre2-8-0.dll`, `libpcre2-16-0.dll`, `README.txt`, `dwgfilter`, `share/man`) is in this session's scratchpad `.../e1e2f8a1-.../scratchpad/p0/tools/`, beside an extracted folder that lacks `README.txt`, `dwgfilter` and the `share/` contents. The zip has no COPYING file; its `README.txt` states GPL-3.0 | the scaffold extracts `app/vendor/` from the zip (the zip is the authority) with a sha1 manifest (U-6.1) |
| Converter exit code is 0 even with ERROR lines; every HATCH logs "Skip HATCH common handles due to short handle stream" (148 of 148 in I1201) | success is judged by a count check, never the exit code (U-6.3) |
| The presidential DWG loses 8,254 of 142,182 entities (5.8 %) in conversion: 11 block definitions come out empty, 4 of them inserted inside the suite (three gym machines, `A$C59a32014`); the prototype suite was built without them. Bank and tower: 0 lost; house: 1 hatch put on layer 0 | verdicts `ok` / `minor` / `loss`, the AutoCAD DXF fallback offered (U-6.3) |
| The detector fed by a mapping **derived** from the builder's roles (`other` still read, `ignore` dropped) gives openings identical to the hand mappings; ignoring `other` changes 3 bank records (A-FLOR is the kerb context) | one staff mapping, two derived role tables (U-8.2); unknown layers default to `other`, not `ignore` |
| `detector/output/<name>_openings.json` (bank1, bank2, sukhumvit, presidential, l29, l30) were written on 28 Oct by the detector this design vendors (`openings.py` `14a570251f6d...`); a rerun from L29.dwg with `detector/mappings/l29.json` equals `l29_openings.json` exactly. `detector/blind_run_L29_L30/output_corrected_mapping/` was written on 27 Oct by the frozen older code (`730a29203309`) and differs (L29: 42 records against 31) | the oracles are `detector/output/` only; the blind-run outputs are history (U-8.2) |
| Detector records carry `floor` = the name the caller gives (`bank:L1`, `sukhumvit:ground`, `presidential:suite`, `tower:L29`) and ids `<floor key>-NNN` | oracle comparisons drop `floor`; the acceptance settings use the prototypes' floor keys (U-8.2) |
| In `prims` the item handle `h` is the top-level entity's: 1,019 of bank1's 6,106 items share `BA` (Revit's view block); the house's upper floor is one xref block. ezdxf 1.4.4 virtual entities carry `source_of_copy` (checked) | a nested handle key per item (U-7.2) |
| The bank's grid alignment (median of label shifts) puts the house's upper floor 0.304 m off (73.717 against 74.021 m) | per-gridline offsets (U-9.4) |
| `prims` divides by 1000 and flattens at 10 DXF units: right for mm only; the house header says inches on a mm drawing; door votes catch it | unit-aware flattening, a unit check (U-7.4) |
| The builder needs ezdxf 1.4.4, shapely 2.1.2 (GEOS 3.13.1), numpy 2.4.4, matplotlib 3.11.2, pillow 12.2.0; the API venv has none; the system Python 3.14.3 has them only in the user site (`%APPDATA%\Python\Python314\site-packages`), and no pytest | a separate builder process and its own pinned venv, approved by the owner on 4 Nov (U-10.1) |
| Per step (warm): dwg2dxf 1-7.5 s; read 2.4-57 s (presidential: 43 s of it ezdxf parsing 105 MB); detector 1-2.7 s; build 7 s (bank). Peak memory up to 764 MB (presidential read); every Python with default OpenBLAS threads commits ~350 MB more | limits and `OPENBLAS_NUM_THREADS=1` (U-3.5) |
| Multipart forms need `python-multipart` (not pinned); a raw `application/octet-stream` body works on a plain `def` route; Hey API 0.99.0 generates `putUploadPart({ body: Blob })` | uploads in raw 8 MiB parts (U-5) |
| `seed --force` replaces any table version; the e2e config copies `app/data` and asserts 4 cards | seed protections, a freshly seeded e2e store (U-15.3) |
| `seed/presentation.page_text` raises on `&` + letter or `<` in a name; the Max `ascii_name` reduces Thai names to empty | new presentations are built from text runs, never HTML; Max names fall back to ids (U-11) |

## 1. Terms

* **Source**: one uploaded file (DWG or DXF), stored once per project, named by its sha1.
* **Build** (a draft): the staff member's work towards one new version: its sources, its **settings** (`BuildSettings`,
  the recipe: layer roles, floors, defaults, options, fixes) and its **runs**. A build is saved once, as one version.
* **Run**: one job of the worker on a build: `prepare` (convert, check, read each source; suggest roles) or `build`
  (detect openings, build the model, write every output).
* **Sheet coordinates**: a source's own coordinates in metres. **Model coordinates**: sheet minus `offset` minus the
  floor's `sheetShift` (D-5.2).
* **Office**: whoever drew the drawings (a design office, or our own team with a given exporter); its layer names are
  consistent, so its roles are remembered (plan decision 6 Oct).

---

## 2. Staff workflow, screen by screen

All screens are in the staff app (`apps/web`), PC first. Every name that comes from a drawing or a file is shown as text
(React text nodes, canvas `fillText`), never as HTML.

| # | Route | Screen | Shows | Does |
|---|---|---|---|---|
| 1 | `/projects` | project list (exists) | + a **New project** button | -> `/projects/new` |
| 2 | `/projects/new` | **New project** | name, short name, project no, office (select of known offices + "New office..."), id (derived, editable) | `createProject` -> screen 4. Errors inline (id taken: 409 offers the next free id) |
| 3 | `/projects/:id/v/:n` | project page (exists) | + **New version** in the app bar; + a **Drafts** menu when the project has open builds | -> screen 4, or to an open draft |
| 4 | `/projects/:id/builds/new` | **Upload** | drop zone and file picker (`.dwg`, `.dxf`, several at once); per file: name, size, a progress bar by part, Retry / Remove; for a project with versions: "Use the files of v<n> again" | `createUpload`, `PUT` each part, `completeUpload` per file (U-5), then `createBuild` -> screen 5 |
| 5 | `/projects/:id/builds/:buildId` | **Build** page with a step bar: Files . Layers . Floors . Build . Check . Save (`?step=`); a step is reachable once its inputs exist | the build's `BuildDetail`, polled every 1 s while a run is queued or running | the six panels below |
| 5a | step **Files** | per source: name, size, kind, the conversion verdict (`ok` green, `minor` amber, `loss` red, `failed`), its notes, the layers whose counts differ, the blocks lost with how many of their inserts lie on the sheet (and a sheet view with the lost inserts marked); the units: declared, the door votes, the verdict | units select per source, enabled once the proposal is in (a change rescales that source's boxes and points and re-reads it at once, U-7.4); **Start again with other files** (new build, settings copied: `createBuild { from: { kind: 'build' } }`), the advice to export a DXF from AutoCAD when the verdict is `loss` |
| 5b | step **Layers** | one row per layer name across the sources (100 - 400 rows): name, on/off/frozen, items by type, fills, door arcs, texts, inserts, top block families, the suggested role with where it came from and its evidence; filters (unmapped, by role, search); the sheet on the canvas (U-12.1) with the hovered or selected layer highlighted and every layer coloured by its role | a native `<select>` per row (17 roles shown by their labels with one line of help, U-8.1; a warning chip on an `ignore` row close to walls); "apply to all rows shown" for a filtered set; changes save as settings (`putBuildSettings`, debounced 800 ms, If-Match; the first save from this step carries `layersReviewed: true`, U-8.3) |
| 5c | step **Floors** | each source's sheet with the area proposals (dashed) and the level tags and grid labels marked; the floor list | add, remove, reorder floors; per floor: key, name, source, area (whole file, or a box: click a proposal or drag one; pad and match under "Advanced", U-9.1), level (typed, or picked from the list of all the source's level tags with their labels, U-9.2), wall height (default: next level - this level; the top floor typed), slab thickness, door head / window sill / head defaults, alignment (auto, grid, origin, two points picked on both sheets); project details: office (U-8.4), photo name, Max prefix, Max file name, exported from; the build options (UR: outline-wall suggestions, how furniture pieces are read, the model position's Reset; after the final check of 9 Nov: the furniture size limits `minSize` and `minDepth`, U-10.4) |
| 5d | step **Build** | the pre-build checklist (U-14.3); the run's steps with their status and seconds, a progress bar, the last messages ("Stopping..." after Cancel); when done: counts per floor, the flags count, the top view, a **3D preview** (the viewer on the draft, U-14.4) | **Build** (`runBuild`), **Cancel** (`cancelBuildRun`); a failed run shows its error and what to change |
| 5e | step **Check** | per floor: the plan with the built walls, glass, openings, furniture boxes and flags over it (U-12); the flag list; the diff against the previous build and against the latest version | select items (click, shift-click, box; pick modes item / whole block / layer in a box, U-12.1) -> **Set aside** / **Restore**; an opening -> kind (door, window, passage, not an opening), head, sill; an outline suggestion -> wall, glass, refuse; grey furniture families -> pick a kind; floor heights; **Rebuild** (a build run) |
| 5f | step **Save** | the label (default `<d Mon yyyy>: built from <file names>`), what will be saved (counts, flags left, the stamp), "carry the furniture heights of v<n>" (ticked), "remember these layer roles for <office>" (ticked; hidden with no office, and an office select offered, U-8.4) | `saveBuild` (the button disabled while the request is in flight) -> the new version's page `/projects/:id/v/:n` |

A build saved is read-only (its page shows "saved as v<n>" with a link). Leaving and coming back resumes a draft where it
was: the settings are on the server; an upload in progress resumes by file name, size and date (U-5.3).

---

## 3. The pipeline as server jobs

### 3.1 Runs and steps

| Run | Started by | Steps (JobRecord.steps names) | Writes (`runs/<runId>/out/`) |
|---|---|---|---|
| `prepare` | `createBuild` (every source); a units change saved for one source (`spec.only = [sha1]`: that source's `read:i` only, the conversion a cache hit, no `suggest`, U-7.4) | per source i: `convert:i` (DWG only), `check:i` (DWG only), `read:i`; then `suggest` | `sources/<sha1>/conversion.json`, `drawing.json`, `plan.json.gz`; `suggestions.json`; `proposed-settings.json` |
| `build` | `runBuild` | `ensure` (re-read any source whose units changed; cache hits are instant), `align`, `detect:<floor>`, `walls`, `openings`, `furniture`, `outputs`, `validate` | `model.json`, `stages.json`, `presentation.json`, `report.json`, `overlay.json`, `diff.json`, `openings.json`, `pieces.json`, `topview.png`, `<maxFileName>`, `inputs.json` |

### 3.2 Who does what

* **The API never builds and never holds the store lock during a run.** It writes `spec.json` (JobSpec) and starts the
  worker; it reads `job.json` (JobRecord) to answer; at save it reads the outputs and calls `create_version`, which takes
  the store lock briefly (D-9.3).
* **The worker** (`python -B -m walkthrough_builder.job --run <run dir>`, the builder Python, U-10.1) is the orchestrator:
  it takes the machine lock (U-3.5), runs each heavy step as a **child process in a Windows Job Object** (time and memory
  capped, kill on close, one process: `isolate.py`, after `docs/upload/reference/run_isolated.py`), and writes
  `job.json` atomically after every status or step change (progress-only changes at most twice a second). Children:
  `dwg2dxf.exe`, `dwgread.exe`, and `python -B -P -m walkthrough_builder.step <read|suggest|build> <args.json>`.
* **Writing `job.json` on Windows:** `os.replace` fails with `PermissionError` (WinError 5) while another process has the
  target open, and the API reads it on every poll. `jsonfile.write` therefore retries the replace with back-off (10 ms
  doubling, for at least 5 s), as the API's `jsonio.atomic_write_bytes` does with `retry_on_sharing`; a status write
  that still fails is logged and written again at the next change, and never stops the worker. The API opens
  `job.json` only to read it whole and closes it at once.
* **The API validates the worker's outputs** when a run is done (`builtmodel.validate_bytes`, `checks.validate_replay`,
  `checks.validate_presentation`, the pydantic records of the raw files, the `.ms` line-2 stamp) and marks the run
  `failed` with `invalid_output` if any check fails (it writes `job.json` only in this case and in U-3.4's). The API
  has no background task, so this happens in the first request that sees the run `done` (`getBuild`, `runBuild`,
  `saveBuild`), under a **per-build lock** (an OS file lock on `builds/<buildId>/.api.lock`, held for the check only),
  and the result is recorded in `runs/<runId>/api.json` (`RunApiRecord { validated, issues, adoptedRevision }`) so two
  polling tabs never validate twice. It checks again at save: the worker reads untrusted drawings.

### 3.3 Settings proposal

When the first `prepare` run is done, the API adopts `proposed-settings.json` as revision 1 (under the per-build lock of
U-3.2, recorded as `adoptedRevision` in that run's `api.json`, so it happens once): layer roles from the suggestions;
one floor per source (whole file) when there are several sources; one floor per area proposal that `looks: 'plan'`
when one source holds several (keys `L1`, `L2` ..., names `Level 1` ..., levels 0, +3.00 ..., wall heights 3.00, a
plain-sentence note that these are guesses); units as the reader used them; project naming from
`project-settings.json`; defaults, furniture and options as in U-10.4. **Until then the settings cannot be saved:**
`putBuildSettings` answers 409 `not_prepared` while the settings are at revision 0, and the web app disables every
control that saves (the Files step's units select included) with "Reading the drawings..." until the proposal is in.
Revision-0 settings exist only on the server; their sources have `units: null`.

A build that starts `from` a version or another build takes that recipe instead (adopted at the same moment, as
revision 1; a source whose file is new gets the units its read used) and only re-points floors at sources by file name
(same name -> same floor; otherwise the Floors step says which floor has no source). **A project with no
`project-settings.json` and no `project-data.json`** (the four seeded projects) takes from its latest version: the
naming (`photoName`, `maxPrefix` from its `model.json`; `maxFileName` = its stored `.ms` download's name), the floor keys
and names in model order (so a new bank version keeps `L1` / `L2` and a new house version `ground` / `upper`), and the
offset (U-9.6); the office is unset until staff pick one (U-8.4). The acceptance runs (ACCEPTANCE A-1, A-5) use the
fixture settings, whose floor keys are the prototypes' (`L1`/`L2`, `ground`/`upper`, `suite`, `L29`/`L30`).

### 3.4 Status, cancel, restart

* `runBuild` answers 409 `run_in_progress` while any run of the build (prepare or build) is `queued` or `running`, 409
  `not_prepared` before the first prepare is done (**UR:** when that first prepare ended `failed`, `cancelled` or
  `interrupted`, so no proposal can ever come, `runBuild` starts a new prepare of the draft's files instead: the Files
  step's "Read the drawings again"; and the reading's run panel has Cancel, so a wrong or huge drawing can be stopped and
  its draft deleted), 409 `layers_not_reviewed` until staff have seen the Layers step once
  (U-8.3), 503 `builder_missing` when the builder Python or LibreDWG is not where the settings say. A `loss` conversion
  verdict warns (on the Files step and the pre-build checklist, U-14.3) and never blocks.
* **Process identity:** `procStart` is the process creation time as returned by `GetProcessTimes`, the raw FILETIME
  (100 ns ticks since 1601, UTC) written as a decimal string, and compared exactly. Right after `Popen` the API writes
  `runs/<runId>/launch.json` (`LaunchRecord { pid, procStart }`, the same definition, read through `OpenProcess` on the
  new pid); the worker writes the same pair into `job.json`. One function computes it in each package (builder
  `runio.proc_start(pid)`, API `jobs/local.py`), both tested against the other on a live child.
* **Cancel:** the API creates `runs/<runId>/cancel` and `RunInfo.cancelRequested` turns true (the UI shows
  "Stopping..."); the worker looks for it between steps and every second while a child runs, terminates the child's
  Job, writes `cancelled` as its **last** write and exits. `LocalJobRunner` starts a timer thread at the cancel: if the
  status has not changed 15 s later, it kills the worker tree (`taskkill /T /F /PID <pid>`, only after checking the
  pid's creation time equals `procStart`), waits until the pid has exited, and only then writes `cancelled` itself.
* **The worker stops by itself** when its `spec.json` or its run folder disappears (checked with the cancel file, every
  second, while queued too), and when the whole run, queue time included, passes `JobSpec.wallClockSeconds` (3600: 30
  min running plus up to 30 min queued): it kills its child and exits, writing `interrupted` if the folder still exists. A fresh e2e seed
  that replaces the data folder therefore never leaves a worker holding the machine lock; the e2e global teardown also
  cancels open runs through the API.
* **API restart** (`npm run dev` has no uvicorn `--reload` since 10 Nov: on Windows its restart is a `CTRL_C_EVENT` to
  every program in the terminal, and it stopped the whole app, UI-5; after an API change the owner presses Ctrl+C and
  runs `npm run dev` again): the worker is a separate process (`CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW`) and owns
  its state, so a running build carries on. On start-up the API marks `interrupted` every `queued` / `running` run whose
  worker is gone (pid dead, or a different creation time), and every run that has a `spec.json`, no `job.json`, is
  older than 60 s and whose `launch.json` pid is not alive (or that has no `launch.json`); Build runs it again. A run
  whose worker still lives is followed and ends as the worker writes it. **After Ctrl+C on `npm run dev`** the worker
  never sees the Ctrl+C (CREATE_NO_WINDOW gives it a console of its own); `run-api.mjs` ends uvicorn at once (Node's
  `child.kill` is TerminateProcess on Windows), so concurrently's `taskkill /T /F`, which comes after, no longer finds
  the worker below it and the build normally finishes (checked in real consoles on 10 Nov, UI-5). A tree kill while the
  API still runs does end it (concurrently `-k` ends the API side that way when the web server stops first), so this is
  not promised: the run ends `done`, `cancelled` or `interrupted`, and the next start-up shows which.
* Errors: `JobRecord.error { code, message, step }` with the codes of `upload-contracts.ts` `RunErrorCode`; messages are
  plain sentences naming files by their upload names, never a server path.

### 3.5 Limits and concurrency (this laptop: i7-1255U, 16 GB)

| Child | Time | Memory | Largest measured |
|---|---|---|---|
| `dwg2dxf.exe` | 120 s | 2 GB | 7.5 s, 369 MB (presidential) |
| `dwgread.exe -O JSON` + the scan (U-6.3) | 180 s | 1 GB | 15 s, 207 MB |
| read (ezdxf, U-7) | 300 s | 4 GB | 57 s, 764 MB |
| build (detector + builder + outputs) | 900 s | 4 GB | 15 s cold, 158 MB (bank); the detector warns above 60 s a floor |
| a whole run | 30 min running; 60 min with its queue time (`JobSpec.wallClockSeconds` = 3600, U-3.4) | - | - |
| DXF written by the converter | - | 1.5 GB on disk (killed beyond) | 105 MB |

* **One run at a time on the machine**: the worker takes an OS lock on `%TEMP%\walkthrough-run.lock` (msvcrt locking,
  released by the OS if the worker dies) before its first step, and shows `queued` ("another build is running") while it
  waits. Tests and parallel builders share it, so two heavy drawings never run at once. The lock belongs to a process:
  a test that holds it must never spawn a worker (ACCEPTANCE 2.1: the `heavy` and `worker` markers).
* **Memory caps:** `JOB_OBJECT_LIMIT_PROCESS_MEMORY` makes allocations past the cap fail; it does not kill. So (1) the
  port of the reading walk re-raises `MemoryError` and `RecursionError` from its per-entity handlers (every other
  exception is still swallowed and counted, U-7.1), and a step child that ends on `MemoryError` exits with code 75;
  (2) `isolate.py` associates a completion port with the Job and classifies a child as `*_memory` when it received
  `JOB_OBJECT_MSG_PROCESS_MEMORY_LIMIT`, exited with 75, or ended with `PeakProcessMemoryUsed` at 95 % of the cap or
  more; otherwise a failure is `*_failed`. A converter that dies at its cap is therefore `convert_memory`, not
  `convert_failed`.
* Every worker and child runs with `OPENBLAS_NUM_THREADS=1`, `OMP_NUM_THREADS=1`, `MPLBACKEND=Agg`,
  `PYTHONIOENCODING=utf-8`, `PYTHONUTF8=1`, `-B`, and Python children with `-P` (no working folder on `sys.path`); never
  `-I`, `-E` or `-s` (the builder relies on `PYTHONPATH`); `stdin` = DEVNULL; argument lists, never a shell; working
  folder = a fresh empty folder under the run's `out/tmp/` (deleted at the end).

---

## 4. Where files live

### 4.1 The store (`app/data`, or `WALKTHROUGH_DATA_DIR`; D-9.1 plus)

```
data/
  projects/<id>/
    meta.json                         unchanged (ProjectMeta)
    project-settings.json             ProjectSettingsFile: office, naming, pinned offset            (new, small)
    sources/<sha1>/source.json        SourceRecord                                                  (new)
    sources/<sha1>/original.dwg|.dxf  the upload, byte for byte; never served                       (new)
    builds/<buildId>/build.json       BuildRecord (API)                                             (new, drafts)
    builds/<buildId>/settings.json    BuildSettingsFile (API, If-Match)
    builds/<buildId>/.api.lock        the per-build lock (adoption, validation, save; U-3.2)
    builds/<buildId>/runs/<runId>/    spec.json, launch.json, api.json (API), job.json (worker), cancel, log.txt, out/
    versions/<n>/...                  unchanged, plus:
      project-data.json               the BuildSettings the version was built with (the reserved name of D-9.1)
      source/inputs.json              VersionInputs (provenance)
      source/conversion-<sha12>.json  each source's ConversionReport
      source/build-report.json        the builder's report (U-10.8)
      source/openings.json            OpeningsFile: the detector's full records
      source/pieces.json              FurniturePlacements: each piece's block turn and mirror (U-11.7)
      source/flags.json               the flags left at save
  mappings/<officeId>.json            OfficeMapping (new)
  .uploads/<uploadId>/                session.json + part-00001 ... (new; deleted on complete, cancel or after 24 h)
```

* **Never served:** `sources/`, `builds/*/.api.lock`, `builds/*/runs/*/spec.json|launch.json|api.json|job.json|log.txt|cancel`,
  `out/tmp/`, `versions/*/source/`,
  `.uploads/`, the cache. Routes serve only the named outputs of U-13 (draft model, stages, overlay, diff, drawing read,
  plan geometry, conversion report, top view, draft Max script) and, as before, a version's assets and downloads.
* **Git** (`app/.gitignore`): add `data/projects/*/sources/`, `data/projects/*/builds/`, `data/.uploads/`,
  `data/.staging/`. `data/mappings/` and the version folders stay tracked (small JSON; a version is what a client sees).
  The root `.gitignore` already ignores `*.dwg`, `*.dxf`, `prims.pkl`.
* Folders are made when first used, so a freshly seeded store is still `['.lock', 'projects']` (`test_seed`).
* **Clean-up** (API start-up and before each new run): upload sessions older than 24 h; build runs older than the two
  newest `done` build runs and the newest `done` prepare run of their build; builds saved more than 7 days ago (the
  version keeps what matters); builds untouched for 30 days and not saved, after logging their ids. The cache has its
  own clean-up (U-4.2).
* **Path length:** long paths are off on this laptop (`LongPathsEnabled = 0`), so every path stays under 260
  characters. With `app/data` at its present depth a 63-character project id gives 240 characters for
  `...\runs\0001-prepare\out\sources\<sha1>\conversion.json` and 250 with a temp suffix, so **new project ids are at
  most 40 characters** (U-13.3; existing ids keep the old 63 limit when read), and every store and worker write checks
  the full path first and fails with a plain message ("the project folder is too deep for Windows: move it or shorten
  its path") instead of a `FileNotFoundError`. A test runs a prepare under a 40-character id at `app/data`'s depth.

### 4.2 The cache (`WALKTHROUGH_CACHE_DIR`, default `%LOCALAPPDATA%\walkthrough\cache`)

Derived, regenerable files, kept out of the project (the presidential DXF is 105 MB):

```
<cache>/<source sha1>/libredwg-0.14/plan.dxf       + convert.log + conversion.json + .done (sha1s of the three)
<cache>/<source sha1>/read-<readerVersion>-<units>/items.pkl  + drawing.json + plan.json.gz + .done
```

An entry counts only when its `.done` lists the files with their sha1s; anything else is recomputed. A pickle is only
ever one the worker wrote (never a file from an upload). Clearing the cache costs only time. Tests and builders set
`WALKTHROUGH_CACHE_DIR=<WT_TMP>/cache`.

* **Naming a read before it has run:** the units a read uses are known only after it (`units: null` lets the reader
  decide, U-7.4). The reader writes into `<sha1>/read-<rv>-tmp-<runId>/`; the worker renames it to
  `read-<rv>-<used units>/` when its `.done` is written, and writes `read-<rv>-auto.json` (`{ units }`) beside it, so a
  later lookup with `units: null` follows the pointer. A rename that finds the target already complete keeps the
  existing entry.
* **Eviction:** the worker, holding the machine lock at the start of each run, removes whole `<sha1>/` entries, least
  recently used first (by the newest `.done` mtime; a cache hit touches it), until the cache is under
  `WALKTHROUGH_CACHE_MAX_GB` (default 5). Entries of the sources of the run itself are never removed.

### 4.3 Sizes (the six drawings)

| | DWG (stored) | DXF (cache) | items.pkl (cache) | drawing.json | plan.json.gz | run outputs |
|---|---|---|---|---|---|---|
| bank L1 + L2 | 0.50 + 1.21 MB | 2.8 + 7.9 MB | ~2 + ~7 MB | 41-61 KB each | 32 + 48 KB | ~2.5 MB (model 0.6, stages 0.47, top view 0.6) |
| house | 1.75 MB | 12.3 MB | ~12 MB | ~60 KB | 130 KB | ~3 MB |
| suite | 17.8 MB | 104.9 MB | ~30 MB | ~60 KB | 65 KB | ~2 MB |
| tower L29 + L30 | 0.77 + 0.73 MB | 4.3 + 4.7 MB | ~5 + ~5 MB | ~50 KB each | 75 + 70 KB | ~2.5 MB |

The plan sizes were measured without the per-item signatures that U-7.5 now adds (`sig`, `rsig`, `eid`): 12-hex strings
compress poorly, so expect about three times these sizes (the house about 0.4 - 0.5 MB gzipped), loaded once per step.

---

## 5. Upload (raw parts, no new library)

### 5.1 Protocol

1. `POST /api/uploads { projectId, fileName, bytes }` -> 201 `UploadSession { id, partBytes: 8388608, parts, received: [],
   partUrls, completeUrl, url, expiresAt }`. Refused: 404 `project_not_found`; 413 `too_large` above
   `WALKTHROUGH_UPLOAD_MAX_BYTES` (300 MiB); 422 `bad_kind` unless the name ends in `.dwg` / `.dxf` (any case), is 1 - 255
   characters and has no control character.
2. `PUT <partUrls[i]>` with `Content-Type: application/octet-stream`, the bytes of part i + 1: every part but the last is
   exactly `partBytes`, the last the rest. Idempotent (a part sent again replaces itself: written to `part-NNNNN.tmp`, then
   renamed). 422 `bad_part` for a wrong number or size; 413 `part_too_large` and 411 `length_required` come from the body
   guard before the body is read (U-13.5). Answer `UploadPartResult { part, bytes }`.
3. `POST <completeUrl> {}` -> 201 `SourceFile`: the parts streamed together into a temp file with its sha1; the first bytes
   checked: a DWG starts `AC10` + 2 digits and must be AC1012 (R13) or newer; `AC1001` - `AC1011`, and the pre-R10
   prefixes `AC1.` and `AC2.` (`AC1.40`, `AC1.50`, `AC2.10` ...), get 422 `unsupported_version` ("save it as a newer DWG,
   or export a DXF"); an ASCII DXF starts (after optional whitespace and `999` comments) with group code `0`
   and `SECTION`; a binary DXF with `AutoCAD Binary DXF\r\n\x1a\x00`; anything else 422 `bad_kind`. Then moved to
   `sources/<sha1>/original.<ext>` + `source.json`. A sha1 the project already has keeps the stored file (the same DWG
   uploaded twice is one source). 409 `incomplete` with `details.missing` while parts are missing.
4. `GET <url>` returns the session (resume); `DELETE <url>` cancels it (204).

Locally the part URLs point at the API; an object store later hands out presigned multipart URLs (R2's 5 MiB minimum part
fits) and the client does not change (D-10.3: it never builds a path).

### 5.2 Cross-site rule

Every state-changing route is `PUT` or `DELETE`, or a `POST` with a JSON body (even `{}`): none is a "simple" request, so
another origin cannot send one without a CORS preflight, which it fails (probed 4 Nov). CORS gains `POST` and `DELETE`;
the allowed headers stay `content-type` and `if-match`.

### 5.3 The browser side (`apps/web/src/upload/upload.ts`)

`Blob.slice` per part, `fetch(partUrl, { method: 'PUT', body })`, two parts in flight, progress per finished part (an
XHR is not needed at 8 MiB), retries per part after 1, 2, 5, 10 and 20 s, then the file shows Retry. The session id is
kept in `localStorage` under `walkthrough-upload:<projectId>:<name>:<size>:<lastModified>` (try/catch around every
access); re-picking the same file resumes with the parts the session lacks. Leaving the Upload screen pauses the uploads
(session and key kept, UR); only Remove cancels one. A refusal of the file itself (too large, not a drawing, too old) has
no Retry, and the size refusal is said in MB.

---

## 6. The converter

### 6.1 Where LibreDWG lives from now on

* **The zip is the authority.** The scaffold copies the release zip (`scratchpad/p0/tools/libredwg-0.14-win64.zip`, sha1
  `edb5c011...`) to `app/vendor/libredwg-0.14-win64.zip`, checks its sha1, and **extracts** all 75 entries into
  **`app/vendor/libredwg-0.14-win64/`** (the exes, the four DLLs, `dwgfilter`, `README.txt`, `share/`) with
  `tools/vendor-libredwg.py` (the same script re-extracts and verifies later). The extracted scratch folder beside the
  zip is not used (it lacks `README.txt`, `dwgfilter` and the `share/` contents). If the zip is gone it stops and asks
  for it (the owner re-downloads the GitHub release; network). The binaries are gitignored;
  `app/vendor/libredwg.manifest.json` (tracked) lists each file's path, bytes and sha1 (`dwg2dxf.exe` `07f9c8d95dc0...`,
  `dwgread.exe` `bd2a2745827a...`, `libredwg-0.dll` `4146008520ec...`), and `npm run check:pins` verifies them.
* **Licence:** the zip carries no COPYING file; its `README.txt` (shipped) states GPL-3.0-or-later. The full GPL-3.0
  text goes beside it as `app/vendor/libredwg-0.14-win64/COPYING` (fetched from gnu.org and recorded, with its sha1, in
  the manifest on 9 Nov 2026). `app/vendor/LIBREDWG-LICENCE.txt` (tracked) names the licence, the release and where the
  text is.
* Setting `WALKTHROUGH_LIBREDWG_DIR` (default `vendor/libredwg-0.14-win64`, relative to `app/`). Cloud Run later needs a
  Linux build behind the same setting.
* **GPL boundary:** LibreDWG runs only as a separate program; nothing links it; its licence ships beside it; the staff
  app and the offline files never contain it.

### 6.2 Running it

Per DWG, in a fresh folder `out/tmp/convert-<i>/`: the upload copied in as `input.dwg` (the original name never reaches
the command line; the converter echoes paths), then `dwg2dxf.exe -y -o plan.dxf input.dwg` in a Job Object (U-3.5),
stdout and stderr to files. Success = exit 0 **and** `plan.dxf` exists and is not empty **and** `ezdxf.recover` opens it
(its auditor's fixes and errors recorded). The DXF and the log go to the cache (U-4.2).

### 6.3 The "nothing lost" check (port of `reference/nothing_lost_stream.py`)

1. **DWG side:** `dwgread.exe -O JSON input.dwg` with stdout piped into a line scanner (never written to disk: about 20x
   the DWG). Keep the `OBJECTS` section: per handle the type (DWG names mapped to DXF names: `DIMENSION_*` -> DIMENSION,
   `VERTEX_*` -> VERTEX, `POLYLINE_*` -> POLYLINE, `_3DFACE` -> 3DFACE ...), the layer and the owner (by `entmode`: 2 model
   space, 1 paper space, else through the parent: VERTEX -> POLYLINE, ATTRIB -> INSERT, up to the block header); layer
   names, block names, the `UNKNOWN_OBJ` / `UNKNOWN_ENT` / proxy counts.
2. **DXF side:** a raw group-code scan (no ezdxf): `TABLES` (LAYER; BLOCK_RECORD handle -> name), `BLOCKS`, `ENTITIES`;
   per entity code 5 (handle), 8 (layer) and the first 330 outside `{ACAD_REACTORS}` (owner).
3. **Compare:** missing and extra handles; type, layer and owner changes; layers; blocks (DWG anonymous names `*D`, `*U`,
   `*X` are unnumbered, the DXF numbers them); blocks whose definition came out empty or short; for each, its model-space
   inserts with their composed positions (sheet m) and layers.
4. **Messages** of the converter by class: `hatch-short-handles` (one per HATCH), `handle-not-found`,
   `unstable-class`, `unhandled-class`, `unknown-flag`, `unknown-object`, `wrong-layer` (`Wrong POLYLINE.layer` ...),
   `error:<kind>` (`Invalid ATTRIB.keep_duplicate_records`, `bit_read_*`, `Invalid CMC`, `buffer overflow` ...), `other`;
   one example line each with paths removed. Measured: bank L1 148 hatch, 28 handle-not-found, 9 unstable-class
   (MATERIAL x6, TABLESTYLE, MLEADERSTYLE x2; UR measured 9, the integration too); the
   house 1,004 handle-not-found, 385 wrong-layer, 81 `error:Invalid ATTRIB.keep_duplicate_records`, 46 hatch.
5. **Verdict, from the comparison only** (messages never decide it): `ok` (nothing missing, no type, layer or owner
   change), `minor` (nothing missing; only items whose layer or owner the DWG decode did not know, written to layer 0,
   or empty layer names on ATTRIB/ATTDEF), `loss` (an entity of model space or of a block inserted in model space is
   missing), `failed` (the conversion failed). The classes `hatch-short-handles`, `handle-not-found`, `unstable-class`,
   `unhandled-class`, `unknown-flag` and `wrong-layer` never affect the verdict and add no note; `error:*`,
   `unknown-object` and `other` add a note ("the converter reported 81 errors of one kind; nothing is missing") unless
   something is missing, when the `loss` notes say it. Measured: bank and tower `ok`, house `minor` (1 hatch put on
   layer 0, 1 owner change), suite `loss` (8,254; 4 blocks inserted in the suite's area).
6. **What it cannot see:** both sides come from LibreDWG's decoder, so it proves the writer kept what the decoder read;
   what the decoder never read shows only as `UNKNOWN_*` counts and ERROR classes. The Files step says so. The
   independent checks are a DXF exported from AutoCAD (decision F's fallback) or a second converter (ODA, U-18.12).

**The DWG side must be whole (UR):** dwgread exits 0 and ends its JSON with `  }}` on all eight project drawings; a
non-zero exit, a JSON whose `OBJECTS` array or whole document never closed (a crash, a kill or a failed allocation while
it wrote), or more than 64 MB of dwgread messages give `check_failed`, never a verdict (a prefix of the drawing made
every later entity `extra`, which never counted: verdict `ok`). Extra handles now make the verdict at least `minor` with a
note (none on the eight drawings). The converter's own messages are capped at 64 MB (the largest is 440 KB), and a
child's output goes into the run's `log.txt` as its first and last 256 KB.

A DXF upload gets `verdict: 'not-converted'`, its audit counts, and the note "Exported by the drawing's own program: no
conversion to check".

---

## 7. Reading the drawing (one pass per source and unit)

### 7.1 One ezdxf pass, three outputs (`walkthrough_builder/read.py`, `drawing.py`, `plangeom.py`)

`ezdxf.recover.readfile(plan.dxf)`, then the walk of `detector/tools/prims.py` `_flatten` **unchanged in what it keeps
and in its arithmetic** (model space only; INSERTs unpacked with `virtual_entities()` to depth 8; layer `0` inside a block
takes the INSERT's layer; DIMENSION and the `SKIP` types not kept as items; every exception per entity swallowed and
counted, except `MemoryError` and `RecursionError`, which are re-raised: U-3.5), with three changes: (1) curves
flattened at **10 mm expressed in DXF units** (`10 / UNIT_MM[units]`: exactly `10` for mm, so mm drawings give the same
points); (2) each item gets `k`, its nested key (U-7.2); (3) the same pass counts what `drawing.json` needs (dimensions
included). Coordinates stay in the prims frame (**DXF units / 1000**, the same float operation `v.x / 1000`), so the
detector's and the builder's own `scaled(d, UNITS[units])` turn them into metres exactly as today. INSERT items are
kept as `prims` keeps them, each directly before its subtree (the bank builder's furniture reader relies on that order).

* **(a) items cache** `items.pkl`: `{ items: [...], layers: {name: linetype}, units }`, items as prims plus `k`; no
  `area` (areas are build settings, tagged at build time, U-9.1).
* **(b) `drawing.json`** (DrawingRead, U-7.3).
* **(c) `plan.json.gz`** (PlanGeometry, U-7.5).

**Oracle:** for each of the six drawings (bank1, bank2, sukhumvit, presidential, l29, l30), the cache's items equal the
prototype `prims.py` items (made by `tools/upload/make-reference.py` into `WT_TMP`) field for field, ignoring `k` and
`area`, in the same order.

### 7.2 The nested key

`k` = the top-level entity's handle, then, for each level of block nesting, the handle of the source entity inside the
block definition (`virtual_entity.source_of_copy.dxf.handle`), joined by `/`: `BA/2C4/1F3`. A level whose entity has no
source handle gives `~<index in virtual_entities order>`. An ATTRIB is `<insert key>@<attrib handle>`. Hatch loops share
their hatch's key. LibreDWG keeps DWG handles exactly (checked on every handle), so the key is stable across
re-conversions of the same DWG and across AutoCAD edits that keep the entity; Revit re-exports renumber handles, hence
the fallbacks of U-10.6:
* `elementId` = the last `-(\d{5,})-` run of the innermost block name in the path that has one. It names a whole family
  instance (every line of one door block shares it), so it is never matched alone;
* `sig` = sha1[:12] of type, layer and points rounded to 1 mm in metres, the `plan_items._signature` rule;
* `rsig` (items with an `elementId` only, else empty) = the same hash with the points taken relative to that element's
  INSERT: minus its insertion point, turned back by its world turn, rounded to 1 mm. It survives a re-export that moves
  or renumbers the element and tells its lines apart.

The reader computes all three per item; PlanGeometry carries them to the browser (U-7.5), which copies them into each
`ItemRef` it writes.

### 7.3 `drawing.json` (DrawingRead; port of `reference/read_drawing.py`)

The fields of `upload-contracts.ts` section 4. Rules worth stating:
* **extents**: the 1 - 99 % box of all item points (the house's header `$EXTMAX` is 13,528,690 units, 13.5 km in its
  millimetres, far outside the drawing);
* **layer stats**: counted over the unpacked items, by effective layer; `pairs` counts parallel line pairs (within 3
  degrees, overlapping half the shorter) by spacing class: hints only (stairs and trees pair too);
* **blocks**: family = the name without an xref prefix (up to the last `$0$`) and without a Revit
  `-<5+ digits or V#>-<view>` suffix (both rules: `XR_L44$0$SINK-720-400` -> `SINK-720-400`; bank chairs drop their id);
* **texts**: TEXT, MTEXT (`plain_text()`), ATTRIB (tag, block); at most 5,000, longest first;
* **levelTags**: an ATTRIB tagged `LEVEL`, `ELEV`, `EL`, `LV` or `FFL`, or a text matching `reference/read_drawing.py`'s
  `LEVEL_RE`, copied verbatim (Python `re`, no flags):
  `^\s*(?:(?:F\.?F\.?L|S\.?S\.?L|T\.?O\.?S|FL|EL|LEVEL|LVL|LV)\.?\s*[:=]?\s*)?([+\-±]?\s*\d{1,3}(?:[.,]\d{2,3}))\s*(?:M|m)?\s*$`
  (the sign class is `[+\-±]`, escaped: an unescaped `[+-±]` is a range from `+` to `±` that takes digits and letters);
  value in metres (a value above 100 read as mm); `label` = the nearest other text within 3 m (the house: `+0.90` beside
  "ระดับพื้นชั้นที่ 1"). Door and window tags never match: `W1.20`, `D2.10`, `A1.00`, `R1.50`, `x0.900` are U2's negative
  cases. House: 28 tags, 18 on `SPEC` and 10 on layer `0` (`+0.70 +0.90 +4.80 +7.95 +9.05 ...`), every one in the
  elevations (y 28.3 - 61.0 m; the plans end at y 25.85); bank, suite, tower: none;
* **gridLabels**: a text matching `read_drawing.py`'s `GRID_RE`, copied verbatim:
  `^[A-Z]{1,2}['′]?$|^\d{1,2}['′]?$|^[A-Z]{1,2}[.\-]?\d{1,2}$|^\d{1,2}[.\-/]\d{1,2}$` (`1`, `A`, `A'`, `A1`, `A.1`, `1/2`,
  `H2`), on a layer whose name contains GRID or AXIS, or inside a block on such a layer; `line` = the longest grid-layer
  line with an end within 1.0 m of the label's insert point (or passing within 0.3 m), `direction` its unit vector; bank
  10 (`S-GRID-IDEN`, MTEXT in "Grid - CIRCLE"), house 63 (`GRID-01`; bubbles outside the plan boxes, and the elevations
  carry labels with the same letters: which floor a label belongs to is decided at build time, U-9.4), tower 0;
* **areas** (port of `reference/areas_propose.py`): occupied 1 m cells of all items, grown by 2 m, connected, boxes over
  25 m2 kept; `looks` by contents (door arcs and wall-like pairs: plan; level tags and long horizontals: elevation). They
  are starting points: the house's are near `regions.json` but not equal; the suite sits in a 163 x 70 m cluster with its
  neighbours, so the Floors step clusters again on the wall-role layers once roles exist (the same rule with a layer
  filter, run in the browser on the plan geometry, U-14.3).

### 7.4 Units

`declared` from `$INSUNITS` (1 in, 2 ft, 4 mm, 5 cm, 6 m; else null). **Door votes**: per hypothesis k (m per unit),
quarter arcs (80 - 100 degrees) with a straight leaf from the centre to an arc end, the leaf as long as the radius within
10 %, counted where 0.6 <= r k <= 1.25. `used` = declared when its votes are the most or no hypothesis has 3 votes;
otherwise the hypothesis with the most votes (`votes-win`, note "the file says inches, its doors say millimetres"). Bank1
16 votes mm, bank2 31, L29 19, L30 17, house 22 mm (4 m) with `$INSUNITS = 1`, suite 7. Staff confirm on the Files step.
The detector must not run on a drawing in the wrong units (its limits are physical sizes, a 20 % resize already breaks
it), so `runBuild` answers 409 `units_unconfirmed` while a source has `unitsConfirmed: false`. The proposal of U-3.3 sets
it true when the verdict is `agree` or `declared-only` and false for `votes-win` or `unknown`; the Files step's units
control sets it true (a settings save).

**A units change** (a save whose `sources[i].units` differs from the stored one) re-reads that source at once: in the
same request the API (1) rescales everything of that source that is in sheet metres by `newFactor / oldFactor` about
the sheet origin (its floors' box areas and pads, alignment points on its sheet, `fixes.openings` and
`fixes.outlineEdges` of its floors; set-aside keys need nothing), (2) saves the settings, and (3) starts a `prepare` run
for that source only (U-3.1), which writes a new `drawing.json` and `plan.json.gz` (the flattening distance and every
coordinate depend on the units). The Floors and Check steps are locked ("Reading <file> again in <units>...") until it is
done; the build run's `ensure` step is then only a cache check.

### 7.5 Plan geometry for the browser

Every item (no area filter), in sheet metres, curves already flattened, polylines simplified at 5 mm (shapely
`simplify(0.005, preserve_topology=False)`), quantised to 1 cm from `origin` (the extents' lower-left corner, floored to
1 m). Parallel arrays (`upload-contracts.ts` PlanGeometry), gzip level 6. Every INSERT, at every depth, gives one
anchor entry (type 5) with its own key, so the canvas can pick a whole block. Per entry the file also carries the item's
`sig`, `rsig` and element id (an index into `elementIds`; hatch loops repeat their hatch's values), computed by the
reader from the cache item (U-7.2), so the browser writes complete `ItemRef`s without re-deriving anything from the
lossy points. Measured sizes before the signatures: 32 - 130 KB gzipped (about three times that with them, U-4.3).
Served with `Content-Encoding: gzip` when the request accepts it (every browser does), decompressed in the route
otherwise.

---

## 8. The layer mapping

### 8.1 Roles (what staff choose)

| Role | Built as | Read for | Label and one-line help on the Layers step |
|---|---|---|---|
| `wall`, `column` | walls (fills, thin outlines, paired faces, arcs) | the detector's wall solid | Walls: "built as walls; doors and windows are cut into them" / Columns: "built as solid columns" |
| `glass` | glass (paired lines 5 mm - 30 cm), Revit glass wall types | glazing bands | Glass walls: "curtain walls and glass partitions, built full height" |
| `window` | glass panes in the openings | glazing bands, tie-break | Windows: "windows in walls; a sill and a head are built round them" |
| `door` | (door blocks: head heights from names) | swings, leaves, tie-break | Doors: "door swings and leaves: where doors are cut" |
| `screen` | **new**: built as `glass` parts labelled `screen` (grilles, louvres), never cut by an opening | the detector's screens (never glazing) | Screens: "grilles and louvres: see-through, never cut" |
| `stair`, `stair-above` | treads, steps, voids (bank rule 8) | stair flights kept out of passages | Stairs / Stairs above: "stair treads on this floor" / "the stair of the floor above, drawn dashed" |
| `railing` | railings 1.10 m (bank rule 7), parapets where the rule runs | - | Railings: "balustrades and handrails, built 1.10 m high" |
| `furniture` | one box per piece (furniture kit) | - | Furniture: "one coloured box per piece" |
| `room-name` | room names (bank rule 9) | - | Room names: "texts that name rooms" |
| `room-outline` | **new**: with `outlineWalls: 'suggest'`, flagged wall / glass suggestions along free edges (U-10.5) | (read as context) | Room outlines: "room boundaries; can suggest missing walls" |
| `level` | - | level tags | Levels: "level marks such as +0.90" |
| `grid` | - | alignment | Grid: "grid lines and their bubbles: used to line floors up" |
| `light` | **seam**: counted, not built (light fittings come with the lights work, plan 2.5) | - | Lights: "light fittings: kept for later, not built now" |
| `other` | not built; shown faint in the replay | read by the detector as context (default for an unknown layer) | Not built (kept as context): "not built, but still read when finding doors and windows" |
| `ignore` | dropped everywhere | dropped | Ignore: "dropped everywhere, also from finding doors and windows" |

The select shows the labels (the role names stay in the settings). A layer set to `ignore` that has items within 1 m of
wall-role lines gets a warning chip: "close to walls: ignoring it can change which doors and windows are found" (the
bank's `A-FLOR` is the detector's kerb context: ignoring it changes 3 records). The check runs in the browser on the
plan (`nearLayers`, U-14.3).

### 8.2 Derived role tables (pure functions in `walkthrough_builder/roles.py`, tested)

* **Builder** (the bank builder's `plan_items` roles): `wall column glass window door stair stair-above railing room-name
  grid furniture other ignore` map to themselves; `screen` -> `screen` (a builder role added to the port's ROLES);
  `room-outline` -> `room-outline` (added); `level`, `light` -> `other`.
* **Detector** (`geomkit.ROLES`): `wall column glass window screen door stair` -> themselves; `stair-above` -> `stair`;
  `railing furniture room-name level grid light ignore` -> `ignore`; `room-outline` and `other` -> no role (read).
* The bank builder's consistency check (its four roles against the detector's) is kept as a self-test of the two tables.
* **Oracle:** with the acceptance settings (`fixtures/upload/settings/*.json`), the derived detector mapping gives
  openings equal to `detector/output/{bank1,bank2,sukhumvit,presidential,l29,l30}_openings.json` (`openings` list),
  record for record, **with the `floor` field removed** from both sides (the app names floors `<projectId>:<key>`, the
  files `bank:L1`, `sukhumvit:ground`, `presidential:suite`, `tower:L29`). Ids are `<key>-NNN`, so the settings use the
  prototypes' floor keys: `L1`/`L2`, `ground`/`upper`, `suite`, `L29`/`L30`. The bank pair equals
  `bank_test/src/detector_out/openings_L{1,2}.json` (checked). `detector/blind_run_L29_L30/output_corrected_mapping/` is
  history (written on 27 Oct by the older frozen detector, `730a29203309`) and is not an oracle. Where a drawing's frozen
  output needs a layer the builder calls `other` dropped (the tower's `A-DETL`, `A-FLOR`, as in
  `detector/mappings/l29.json`), its settings give that layer `ignore`. The test is that the derived mapping
  **reproduces the output**, not that it lists the same layers: the bank's derived table reads `A-DETL`, `A-DETL-GENF`,
  `A-FLOR-HRAL-MBND` (`other`) and drops `A-ANNO-DIMS`, `A-ANNO-DIMS-100`, `A-GENM`, the opposite of
  `detector/mappings/bank1.json`, and both give identical records (checked on both floors).

### 8.3 Suggestions (no AI: decision D; `suggest.py`)

Per layer name, first match wins, with its evidence:
1. **office** - the office memory has this exact name;
2. **office-similar** - the office memory has its normalised name (U-8.4);
3. **name** - a pattern table (case-insensitive globs, in this order): `A-DOOR-IDEN`, `A-GLAZ-IDEN`, `A-WIND-IDEN`
   (door and window tags) other; `*STRS*MBND*`, `*STAIR*ABOVE*` stair-above;
   `A-WALL*`, `*-WALL`, `WALL`, `*TUONG*` wall; `S-COLS*`, `COL`, `*-COL`, `A.COT*`, `*COT *` column; `A-GLAZ` (exactly:
   Revit's AIA export puts the Windows category there, and the detector holds glass-role layers to the stricter
   curtain-wall tests, so a window on a glass-role layer is lost: detector README) window; `A-GLAZ-CURT*`,
   `A-GLAZ-CWMG*`, `*-GL`, `*GLASS*`, `*KINH*` glass; `A-WIND*`, `WIN`, `*WINDOW*` window; `A-DOOR*`, `DOOR`, `*-DOOR`,
   `D-JAMB`, `DSYM`,
   `*DOOR-WIND*` door; `*GRILL*`, `*LOUV*` screen; `S-STRS*`, `*STAIR*`, `*THANG*` stair; `*HRAL*`, `*RAIL*`, `*LANCAN*`,
   `*BALUS*` railing; `I-FURN*`, `*FURN*`, `FUR`, `Q-CASE*`, `Q-SPCQ*`, `P-SANR*`, `*SANR*`, `FIXT`, `L-PLNT*`, `*NOI THAT*`,
   `*CAY*` furniture; `A-AREA-IDEN`, `*ROOM*NAME*`, `*RNAME*`, `A-TEXT`, `*-IDEN` room-name; `A-AREA`, `DEFPOINTS` (only
   with 3+ closed outlines over 2 m2) room-outline; `S-GRID*`, `*GRID*`, `*AXIS*` grid; `*LEVEL*` (with level tags) level;
   `E-LITE*`, `*LIGHT*` light; `*DIM*`, `*ANNO*`, `*HATCH*`, `*PATT*` (not `A-WALL-PATT`), `*TITLE*`, `VIEWPORT*` ignore;
4. **contents** - solid hatches plus wall-like pairs -> wall; door arcs with leaves -> door; glass-like pairs and no
   fills -> glass; 10+ inserts whose families the furniture kit classifies -> furniture; only texts -> room-name when
   most texts are not tags (`D1`, `W2`), else other; only DIMENSION -> ignore; circles with short labels -> grid; level
   tags -> level;
5. **default** - `other`.

A name hit that the contents contradict gets the contents' evidence added ("named like a room-name layer, but its 41
texts are door tags D1 ... D23": the house's `RNAME`), and the name still wins: staff decide. Never trust names blindly:
every suggestion is shown with its evidence and nothing is built until staff have seen the Layers step once: the step
sends `layersReviewed: true` with its first save (or, with no change, an otherwise unchanged save), the API records
`BuildRecord.layersReviewedAt`, and `runBuild` answers 409 `layers_not_reviewed` until it is set. A build started
`from` a version or a build that was reviewed starts reviewed. The acceptance scripts send the flag with their settings.

### 8.4 Office memory (`data/mappings/<officeId>.json`, OfficeMapping)

* **Normalised name** = upper case, xref prefix up to the last `$0$` removed, runs of spaces as one, trimmed
  (`Xr_SDC_DD_ID-PRS-ID wall$0$DA-DOOR-WIND` -> `DA-DOOR-WIND`).
* Written at **save** when "remember" is ticked: every layer of the build's sources with a role other than `other`
  (and `other` too when it was set by hand, i.e. differs from the suggestion) is upserted: role, the exact name added to
  `names` (at most 10), `uses + 1`, `lastProject`, `lastUsedAt`; a changed role keeps the old one in `was` (latest wins).
  Furniture words go to the office only when staff tick "remember for the office" next to a word.
* Created empty by `createProject` with `newOfficeName`; `listOffices` lists the files. An office id is a slug of its
  name (`^[a-z0-9][a-z0-9-]{1,62}$`).
* **Acceptance:** after the bank is saved for office `dwp-revit`, a new project of that office uploading L29 gets
  `A-WALL`, `A-WALL-PATT`, `S-COLS`, `A-GLAZ-CURT`, `A-DOOR`, `A-DOOR-FRAM`, `A-DOOR-HDLN`, `S-STRS`, `S-STRS-MBND`,
  `I-FURN`, `Q-CASE`, `P-SANR-FIXT`, `A-GENM` from the office (L29 has 23 layers and no `L-PLNT`; L30 has it), and any
  other L29 layer that the bank's memory holds (an `ignore` or a hand-set `other`) from the office too.
* **Projects with no office** (the seeded four, or a project made without one): the Floors step's project details and
  the Save step offer an office select (known offices + "New office..."); the choice is saved into the settings
  (`office`) and, at save, into `project-settings.json`. With no office, "remember these layer roles" is hidden.

---

## 9. The floors

### 9.1 Which file, which area

`FloorSetup.source` names a source; `area` is `wholeFile` (one plan per file: the bank, the tower) or a `box` on that
source's sheet with `pad` and `match` (the detector's `area_tagger` semantics: the house's plans `pad 0.5, match 'all'`,
which keeps grid lines running into the elevations out; the suite `match 'any'`). Items are tagged at build time **after
scaling to metres** (the detector's tagger compared unscaled coordinates: right for mm only). An item belongs to the
first floor whose area matches it, in floor order, per source. **An item with no points belongs to no floor**, under
`wholeFile` too (`prims.py` `tag if _pts(d) else None` and `openings.area_tagger`: "items with no points belong to no
area"; the bank has none, the house 2,267), so item counts, `layersInUse` and the dedupe match the prototype caches. A
floor whose area holds no wall-role item fails the run (`area_empty`, naming the floor).

**Two readings of the same tags.** This per-item tagging is what the detector and the line-based readers (walls, glass,
stairs, railings, room names) get. The readers that walk an INSERT together with its subtree (the furniture pieces, the
door blocks, `block_kids`, `drawn_inside`) instead read **the whole source in cache order** and give each INSERT, with
its whole subtree, to the floor whose area box (+ pad) holds the majority of its subtree's drawn points; a subtree is
never split, and one in no floor's area is left out (counted in the report). Reason: per-item tagging splits a block
from its contents whenever the insertion point lies outside the box (the suite: 47 INSERTs outside the box with their
contents inside, among them the balustrade block (529 items), the lounge (1,124) and all 12 plant blocks; read per item
the suite gets 57 pieces and 46 loose boxes against the prototype's 120 pieces), and both prototypes read blocks this
way (the suite gathered blocks from the whole sheet by top-level handle; the house placed pieces by box centre). Under
`wholeFile` the two readings are the same set in the same order, so the bank cannot move.

**The Floors step's box:** drawn or picked from a proposal; `pad` 0.5 m and `match: 'all'` by default, both under
"Advanced" with one line of help each ("how far outside the box a line may reach"; "all: a line must lie wholly inside;
any: one point inside is enough, for a plan that touches its neighbours").

### 9.2 Levels and heights

`level` and `wallHeight` per floor are typed or picked; the Floors step lists **all** of the source's level tags with their
labels, sorted by value, each marked on the sheet when hovered (they normally sit in the elevations, away from the
plans: all 28 of the house's do), so staff pick by label (the house: `+0.90` ground, `+4.80` upper, `+8.30` roof beam;
the tool suggests nothing it cannot read: bank, suite and tower are typed). Default wall height = next floor's level - this level; the top floor's
must be typed (proposal: the floor below's). Per-floor `doorHead`, `windowSill`, `windowHead` override the project
defaults for that floor's openings (the house's elevations: ground 3.00 / 0.00, upper 2.60 / 0.00). Floors are listed
lowest first with strictly increasing levels (the model's rule, D-5.6).

### 9.3 `sheetShift` and the frame

After alignment, floor i's items are moved by its shift s_i onto floor 0's frame (translation only, as the bank builder
does in memory, and the detector's openings with them). The model records `floors[i].sheetShift = -s_i` (rounded to the
mm) **only when it is not zero**, so the bank's floors stay exactly as they were (D-5.1: provenance; the viewer does not
read it). The house's upper floor: `[74.021, 0]`.

### 9.4 Alignment methods (`build/align.py`)

* **origin** - no shift (the tower: three linked Revit models inserted at 0,0 on both floors; separate files of one
  project).
* **grid** (per gridline, replacing the bank's median of label shifts). **Which labels belong to a floor:** the
  source's `drawing.json` `gridLabels`; a label belongs to floor i when its `line` crosses floor i's area (the box +
  pad; under `wholeFile`, every label with a `line`), **its line continued 10 m away from its bubble** (`align.py`
  `EXTEND`: the house's grid lines are 1.5 m ticks, which reach no plan on their own: 3 / 0 labels without the
  continuation, 19 / 16 with it, 16 shared; U2.md, U3.md, UR). A label with no `line`, or whose continued line enters
  no floor's area, is
  dropped (elevation labels: the house's elevations repeat the letters A - M at y 34.3 - 34.7). The bubbles themselves
  may lie outside the box (the house's all do: numbers at y 30.4 above boxes ending at 25.85, letters at x 0.3 - 0.4
  and 73.7 - 73.8 left of boxes starting at 7.75 and 81.77). Labels of floors i and 0 are paired by the same text and
  the same direction family. For each pair, the offset along the line's normal, n . (p_i - p_0), p any point of each
  line. Lines are grouped into direction families (within 2 degrees). Two families: the shift is the least-squares
  solution of all normal offsets; one family: the shift along its normal only, with the flag "only one direction of grid
  lines is shared: the other axis is not checked". Spread = the largest residual. Bank: 10 labels, shift 0 within 0.0
  mm. House: 19 labels on the ground floor and 16 on the upper (16 shared; measured by UR: the design's first reading
  said 12 numbered and 12 lettered on each); the numbered lines agree on 74.021 - 74.023 m, the
  lettered ones on dy = 0, so the shift is (-74.021, 0) with a spread under 2 mm (a U3 test). **A shift under 0.5 mm in
  both axes is no shift** (no transform is applied at all), so floating-point noise never moves the bank's coordinates.
  (The figure 74.021 was first measured with `reference/house_align.py`, which splits the sheet by hand-set quadrant
  lines; the rule above replaces those lines.)
* **points** - two point pairs picked on both sheets: the shift is the mean of the two differences; pairs disagreeing by
  more than 5 cm are flagged (`alignment`): rotation is not supported.
* **auto** - grid when at least two labels with lines are shared, else origin when floor i is in another file than floor
  0, else the run fails (`align_failed`: "Level 2 and Level 1 are on one sheet: pick grid or two points").
* The result (method, shift, spread, labels used) goes into the report, the replay's align caption and the check
  screen; a spread over 5 mm is flagged.

### 9.5 Plinth

`options.plinth: 'auto'`: when the lowest floor's level is above 0, its slab part is `z0 = -level`, `z1 = 0`,
`plinth: true` (D-5.4, 5.5: the house's 0.90 m plinth), and `slabThickness` of that floor is its level. A level of 0
(bank, suite, tower) changes nothing.

### 9.6 Offset, pinned per project

`options.offset: 'auto'` = the bank rule (centre of the bounding box of all slabs, rounded to 3 decimals) for the first
version saved from an upload; `saveBuild` then writes it into `project-settings.json` and every later build of the
project uses it (unless staff reset it on the Floors step), so versions keep one frame (saved views, model placement and
the diff need it). **A project with no `project-settings.json`** (the four seeded ones) pins the offset of its latest
version's `model.offset` instead of computing one: the bank still gets `[1.212, 0.348]` (v2's, which the bank rule also
gives), the house `[30.8095, 16.3425]` (its prototype's frozen ground-floor centre, not the slab-centre rule), the suite
its own. A new house version therefore stays in v1's frame, and saved views keep working (U3 checks that the
house's uploaded ground-floor walls land on v1's within 2 cm with that offset; if they do not, the gap report says so).
The diff against a version
(U-12.4) is computed in sheet coordinates (model + offset + `sheetShift`), so it holds even across a frame change.

---

## 10. The general builder

### 10.1 Package, environment, process

* **`app/services/builder/`**: `walkthrough_builder/` (the package), `tests/`, `pyproject.toml` (pytest config),
  `requirements.lock.txt`, `.venv/` (gitignored). It never imports `walkthrough_api` (pydantic) and the API never imports
  it: they meet only through the run folder's JSON files.
* **Environment (approved by the owner on 4 Nov, plan decision row of that day):** its own venv on Python 3.14.3 with
  exactly the versions the prototypes were built with: ezdxf 1.4.4, shapely 2.1.2, numpy 2.4.4, matplotlib 3.11.2,
  pillow 12.2.0, and their closure (contourpy 1.4.0, cycler 0.12.1, fonttools 4.62.1, kiwisolver 1.5.1, packaging 26.3,
  pyparsing 3.3.3, python-dateutil 2.9.0.post0, six 1.17.0, typing_extensions 4.15.0), plus pytest 9.1.1 with iniconfig
  2.3.1, pluggy 1.7.0, pygments 2.21.0, colorama 0.4.6 (the scaffold checks the closure with `pip check` and pins what pip
  adds). Byte-identity with the prototypes depends on these versions (GEOS 3.13.1 inside shapely, freetype inside
  matplotlib). Creating it needs network access to PyPI, once, in the scaffold. **The venv is the only supported
  path.** The system Python (`C:\Python314\python.exe`) can stand in for a diagnosis only, by setting
  `WALKTHROUGH_BUILDER_PYTHON`, with two limits: its libraries are in the user site (`%APPDATA%\Python\Python314\
  site-packages`), so nothing may start it with `-I`, `-E`, `-s` or `PYTHONNOUSERSITE`; and it has no pytest, so
  `test:builder` cannot run on it. `check:pins` imports each pinned module in the set interpreter, resolves its
  `__file__` and version, and fails on any difference from the lock.
* Setting `WALKTHROUGH_BUILDER_PYTHON` (default `services/builder/.venv/Scripts/python.exe`). `tools/run-builder-py.mjs`
  runs it with `-B -P`, `PYTHONPATH=services/builder` and the environment of U-3.5; `npm run test:builder` =
  `node tools/run-builder-py.mjs -m pytest services/builder/tests -q`.

### 10.2 Vendored prototype code (unchanged, hash-checked)

`walkthrough_builder/vendor/` holds byte-identical copies, listed in `vendor/VENDOR.json` (`{ path, from, sha1 }`):
`detector/openings.py` (sha1 `14a570251f6d...`), `detector/geomkit.py` (`6d4f8178...`), `detector/tools/prims.py`
(`0e5566a0...`; only because `openings.py` imports it on load: it finds `tools/prims.py` beside itself), `merge_cad.py`
(`cad_test/src`), `geom.py` (`presidential_test/src`), `furniture_kit.py`, `furniture_max.py` (`furniture/`). A test
checks each copy against `VENDOR.json` and, while the prototype folder exists, against the prototype file. They are
imported by path with `sys.dont_write_bytecode` set; `OPENINGS_DATA` is set to the run's `out/tmp/` before
`openings.py` is imported (its `prims` import reads it once and never uses it here). A change to a prototype after this
milestone is copied in on purpose, with the goldens re-run.

### 10.3 The port of `bank_test/src/build_model.py` (U3's main job)

The bank builder is one script that runs at import (globals `CFG`, `DEF`, `floors`, `DOMINANT`). It becomes functions
in `walkthrough_builder/build/` **without changing any arithmetic or order**, in this order, each step gated by the
golden (the bank's `model.json` sha1 `c3a9408304a2...`, and the report's `summary` equal in content to
`bank_test/src/bank_summary.json`, U-10.8):

1. **Lift** the module code into functions with explicit inputs (`build_model(cfg, floors_items, source_items,
   openings, fixes) -> BuildResult`, `source_items` being the whole-source reading of U-9.1 for the INSERT readers),
   keeping: door heads computed across all floors; the order of `parts_geo`; the offset from all slabs;
   the probe counter running across floors; the furniture sort order; `plan_items.load_floor`'s dedupe (`_signature`) and
   scaling. Inputs: items come from the cache (U-7.1) instead of `prims.pkl`; openings from `detect()` (U-10.7) instead of
   `detector_out/*.json`.
2. **Generalise what is tied to two floors or to the bank** with no change for the bank: any number of floors (the
   one-floor crash in the pictures; `F1, F2 = floors[0], floors[-1]` in the texts, U-11.3); the stair rise per floor =
   next level - this level, the top floor its wall height (as now); `maxPrefix` and `photoName` from the settings; the
   `screen` and `room-outline` roles; unit-aware everything (already metres after scaling).
3. **Options** of U-10.5, each resolving to the bank's behaviour for the bank's drawing.
4. **Fixes** of U-10.6.

What stays bank-flavoured but harmless elsewhere (it switches on only when the data matches) is kept as it is and made
configurable through `settings.vocabulary` with the bank's patterns as defaults: `family()` (`-(\d{5,}|V\d+)-`),
`type_name()`, `GLASS_WORD`, `TYPE_HEIGHT` (`2600H`), `LIFT_WORD`, `SIZE_IN_NAME` (`1000X2400`), `TAG_LINE`
("Not Enclosed / Not Placed / Redundant Room", plus comma decimals such as `1,8m2`), `STAIR_UP` / `STAIR_DOWN`.
`head_in_name` takes the **last** number of a W x W x H run (`920x920x3100` -> 3.10 m; the tower's cavity sliders); no
bank name has three numbers, so the bank cannot move.

### 10.4 Settings -> behaviour (defaults)

`defaults` as `bank_project.json` (door head 2.1, sill 0.9, head 2.1, railing 1.1, slab 0.25, single line 1.0); door
heads, per door: its own name first, then the floor's `doorHead` when staff set one, then the most common height among
the names across the drawing (the bank's `DOMINANT`), then the default (the bank sets no floor door head, so its order
is unchanged; on a Revit drawing a typed floor door head is no longer overridden by other doors' names).
`furniture`: `{ heights: {}, bases: {}, words: {}, skip: [], minSize: 0.08, minDepth: null, looseLayers: [],
pieceLayer: 'insert' }`.

**Numbers from the settings:** the builder applies `float()` to every metre value it reads from the settings (levels,
wall heights, slab thickness, the defaults, door and window heights, offsets, pads, fix points) and `int()` to the mm
furniture heights and bases, before any arithmetic. The browser sends `0` for a typed `0.00` (`JSON.stringify(0)` is
`"0"`), the bank's model bytes carry `0.0`, `3.7` and `1.0`, and `R3` keeps an int an int: without the coercion the
golden breaks. A U3 test builds the bank from its settings rewritten with integer-valued JSON numbers and still gets
`c3a9408304a2`.
`options`: `revitWallTypes 'auto'`, `parapets 'auto'`, `objectClosures true`, `liftShafts true`, `plinth 'auto'`,
`outlineWalls 'off'`, `offset 'auto'`. The bank's settings fixture differs only in `furniture.words = { seat:
['Fritz-Hansen'] }` and the project names.

### 10.5 Builder options for the other drawing styles (this milestone)

| Option / rule | For | Must / should | Bank | Notes |
|---|---|---|---|---|
| `screen` role: glass parts labelled `screen`, never cut, never glazing | house grilles | must | no such layer | the house prototype built them as glass |
| areas per floor (U-9.1), unit-aware reading (U-7) | house, suite | must | wholeFile, mm | |
| per-gridline alignment (U-9.4) | house | must | 0 shift | the 0.304 m error goes |
| plinth auto (U-9.5) | house | must | level 0 | |
| per-floor door / window defaults (a floor's typed window head also caps its curtain windows, which get a lintel above: UR) | house | must | none set | the house's 28 curtain windows reached the wall top (3.90 / 3.50 m) with no lintel |
| `parapets: 'auto'` = only where the floor's wall layers carry solid fills | house (no fills: no false parapets) | must | fills: on | Revit fills every wall it cuts |
| eitherKind openings glazed like windows (decision 27 Oct) | house (11) | must | its 5 are windows already | |
| window "opening over a low wall" gets a 0.90 m sill wall (`LOW_WALL_SILL`) | house (1) | must | none | |
| W x W x H in door names | tower | must | none | U-10.3 |
| `outlineWalls: 'suggest'`: free edges (>= 0.5 m, no wall within 0.35 m) of `room-outline` polylines become flagged suggestions: a 0.20 m wall on the side away from the room, or glass when a railing lies within 0.5 m outside; built only when accepted (`fixes.outlineEdges`) and added before the openings are cut | suite corridor walls and facade glass | should | off | the suite's three hand-added runs lie 63 % on outline edges; 67.8 of 225.8 m of edges are free |
| whole-subtree reading for the INSERT readers (U-9.1) | suite, house | must | wholeFile: the same items in the same order | the suite: 47 inserts lie outside its box with their contents inside |
| furniture reader rules from the house and the suite, inert on the bank (measured: 0 assemblies, 0 dashed loose lines, 0 duplicate boxes, the single loose box not on a part): an `other` block holding 2+ known floor-standing blocks counts as its parts; dashed loose lines left out; duplicates of an xref bound twice; `minDepth`; `looseLayers`; loose boxes lying on a built part dropped | house, suite | should | unchanged model and CSV | the kit itself is unchanged |
| `furniture.pieceLayer: 'drawn'` (default `'insert'`): an INSERT whose **own layer has no furniture role** becomes a candidate piece when the majority of what is drawn in it is on furniture layers, and the piece's `layer` is that majority layer. Never a block that contains furniture-candidate INSERTs (that one is walked into, as the bank's Revit view block on layer `0` is). With `'insert'` a piece keeps its INSERT's layer | suite (its pieces are layer-`0` inserts drawn on `A-2.Noi That`) | should | `'insert'`: unchanged. Not inert if applied blindly: 3 wall-hung basins are inserted on `P-SANR-FIXT` and drawn on `A-GENM`, and the view block `26-0216-AR-...` on layer `0` is drawn mostly on `P-SANR-FIXT` | U3 test: the bank with every furniture option at its default gives model `c3a9408304a2` and CSV `b528bb2320ef` (must); with `pieceLayer: 'drawn'` and the other suite rules on, the same (should; a difference is listed) |
| room names placed by containment in a `room-outline` polygon | suite | later | - | 4 suite labels lie outside every outline |
| house cutter rules: glass corners, fins, jamb-section depth, lintel slots, lintel only when both jambs bear | house | later (gaps measured) | - | the bank's cutter is the base; the bearing rule conflicts |
| walls by shape on a mixed layer (layer-0 offices) | suite xx | later (U-16) | - | needs per-piece set-aside, which this milestone builds |
| glass to wall height - 0.6 m; closing 0.12 m; glass pairs from 2 cm | house | not adopted (gaps measured) | - | arbitrary prototype choices |

### 10.6 Fixes (applied by the builder, every run)

1. **Set aside** (`fixes.setAside`): items whose key matches are removed from the floor's items **before everything**,
   the detector included (an item set aside is not in the drawing). **A ref whose key is an INSERT's** sets aside the
   INSERT and every item whose key starts with `key + '/'` (its whole subtree; the canvas's "whole block" mode writes
   one such ref instead of one per line). Matching, first that applies: (a) exact `key` on the same source; (b) the
   source changed: the same `elementId` **together with** the same layer, type and `rsig` (an element id alone names a
   whole family instance); (c) the same `sig` on the same layer; else the fix is unmatched (flag `fix-unmatched`, kept in
   the settings until staff drop it). When (b) or (c) matches more than one item (a second identical line, a block drawn
   twice), nothing is removed and the flag `fix-unmatched` says "matches 3 items: pick again".
2. **Openings** (`fixes.openings`): matched to a detector record of the floor when both ends lie within 0.15 m of the
   fix's `a`, `b` (either order), else when they overlap 50 % on the same line within 0.1 m; `kind` replaces the
   detector's (`none` drops it: nothing is cut), `head` / `sill` replace the computed ones. Unmatched: flagged.
3. **Outline edges** (`fixes.outlineEdges`): an accepted suggestion (same edge within 0.05 m) becomes a wall or glass
   segment before the cut.
4. **Furniture words and heights** come in through `settings.furniture`. A word that names a family exactly gives it
   that kind, the two compared with every run of white space removed and in lower case (`build/furniture.py`
   `family_form`; the web app's `familyForm` is the same rule), after the kit's skip words and before its vocabulary;
   it also wins over another kind's word that the kit finds inside the family's longer name (the family's own word is
   what staff picked for it). Every word also reaches the kit in the kit's own camel-case form, so it still matches
   whole inside longer names. A
   loose-shape family (`loose shapes on <layer>`) takes its word too. (After the final check of 9 Nov: the Check step
   saves a family as its flag shows it, `TF2092P`, and the kit compared it as written with the split name `TF2092 P`.)

### 10.7 The detector wrapper (`build/detect.py`)

Per floor: items of the floor (after set-aside, scaled to metres with `openings.scaled`, deduped with
`geomkit.dedupe`), `geomkit.role_matcher(derived detector roles)`, `openings.Floor(f"{projectId}:{key}", items,
layer_linetypes, roles, 1.0)`, `openings.detect_floor`, `openings.finish(fl, ops, floor_name)` -> records with ids
`<key>-NNN` (as today). The records go to the builder in drawing metres before the alignment shift (as the bank builder
reads them). Kept for the check screen: `fl.singles` (wall-layer lines left out of the solid) and the swings that went to
no opening. The detector prints its two warnings to **stderr** (`openings.py` lines 866 and 1130): the wrapper captures
both stdout and stderr into the run log (`contextlib.redirect_stdout` / `redirect_stderr` around the call). The `slow`
flag comes from `fl.T['total'] > openings.SLOW_FLOOR` (not from the text). The `FRAME_ROWS_MAX` warning ("N small
shapes stand against walls ...; frame-only sliding units are not looked for") means a whole detection rule was skipped
on that floor: the wrapper recognises it by its fixed wording, records `frameRowsSkipped: N` in the floor's report and
raises a `detector-skipped` flag (severity check) naming the floor and asking staff to map the tile, hatch or symbol
layer to `ignore`.

### 10.8 What the build returns (`walkthrough_builder/contracts.py`, scaffold; U3 -> U4 is pinned here, not in prose)

U3 and U4 are built in parallel, so every key U4 reads is typed by U0 in `contracts.py` (TypedDicts, `total=True`;
`NotRequired` only where marked) and both sides test against the scaffold's fixtures `build-result.bank.json` and
`replay-input.bank.json` (a U3 test asserts that its bank `BuildResult` has exactly their key structure and types; U4's
tests read only those fixtures).

```python
Vec2 = list[float]                      # [x, y]

class SourceContext(TypedDict):         # one per source, from the prepare and the build's `ensure` step
    sha1: str; name: str; kind: str     # 'dwg' | 'dxf'
    units: str                          # the units the read used
    conversion: str | None              # path of conversion.json (None for a DXF upload)
    drawing: str; items: str; plan: str # paths of drawing.json, items.pkl, plan.json.gz (cache)
    dxfSha1: str | None

class BuildContext(TypedDict):          # U1 builds it; U3's build and U4's write_outputs both take it
    spec: dict                          # the JobSpec (spec.json) as read
    sources: list[SourceContext]
    converter: dict | None              # { name, version, exeSha1 }
    previousRunModel: str | None        # path of the previous done build run's model.json (diff)
    versionModel: str | None            # path of the latest version's model.json (diff)
    outDir: str; tmpDir: str

class AlignReport(TypedDict):
    method: str                         # 'none' (floor 0) | 'origin' | 'grid' | 'points'
    shift: Vec2                         # applied to the floor's items (0, 0 when under 0.5 mm)
    spread: float | None                # m, the largest residual
    labels: list[str]                   # grid labels used
    families: int                       # direction families shared (0, 1, 2)

class SingleLine(TypedDict):            # a `single` part and the line work it came from
    part: int; keys: list[str]; layer: str; a: Vec2; b: Vec2       # sheet m

class OutlineSuggestion(TypedDict):
    edge: list[Vec2]; kind: str; length: float; state: str         # kind 'wall' | 'glass'; state 'open' | 'accepted' | 'refused'

class FloorUploadReport(TypedDict):
    source: str; area: dict; items: int; itemsNoPoints: int; subtreesOutside: int
    alignment: AlignReport
    singles: list[SingleLine]
    outlineSuggestions: list[OutlineSuggestion]
    swingsUnmatched: list[dict]         # { keys: list[str], at: Vec2 }
    railsLeftOut: list[dict]            # { keys: list[str], at: Vec2 }
    roomLabels: list[dict]              # labels that are not names: { text, at }
    platesDropped: list[dict]           # { area, at }
    detector: dict                      # { seconds: float, slow: bool, frameRowsSkipped: int | None, records: int }
    lost: list[dict]                    # lost-block inserts inside the area: { block, at, layer }

class FixesReport(TypedDict):
    setAside: list[dict]                # { fix: int, matchedBy: 'key' | 'element' | 'sig' | None, items: int, ambiguous: int }
    openings: list[dict]                # { fix: int, matched: str | None }   (model opening id)
    outlineEdges: list[dict]            # { fix: int, matched: bool }

class BuildReport(TypedDict):
    summary: dict                       # exactly the keys and nesting of bank_test/src/bank_summary.json (floors{key:
                                        # 25 keys}, doorHeads, offset, dominantHead, blocked, namedHeads, furniture); the
                                        # bank's equals that file in content
    floors: dict[str, FloorUploadReport]
    fixes: FixesReport
    doorHeadsFrom: dict[str, str]       # model opening id -> 'name' | 'floor' | 'drawing' | 'default'

class DetectorRecordOut(TypedDict):
    record: dict                        # the detector's record as returned (its `floor` = '<projectId>:<key>')
    modelId: str | None                 # the model opening it became; None: refused or fixed to 'none'
    fix: int | None                     # index into fixes.openings

class ReplayFacts(TypedDict):           # every number a caption quotes (U-11.3); nothing else
    floors: list[dict]                  # { key, name, level, wallHeight, source, align: AlignReport }
    sources: list[dict]                 # { name, units, kind }
    exportedFrom: str | None
    counts: dict[str, dict[str, int]]   # floor -> line category -> lines
    parts: dict[str, dict[str, int]]    # floor -> part kind -> parts
    openings: dict[str, dict[str, int]] # floor -> door | window | passage -> count
    layersByRole: dict[str, list[str]]
    liftShaft: bool; stairs: int; furniturePieces: int; furnitureKinds: int

class ReplayFloor(TypedDict):           # model coordinates (sheet - toSheet), unrounded
    lines: dict[str, list[list[float]]] # cat -> [[x0, y0, x1, y1], ...]
    pieces: dict[str, list[list[Vec2]]] # 'wall' | 'glass' -> quads
    rings: dict[str, list[dict]]        # 'wall' | 'glass' -> [{ o, h }]
    sheet: Vec2

class ReplayInput(TypedDict):
    floors: dict[str, ReplayFloor]
    facts: ReplayFacts

class BuildResult(TypedDict):
    model: dict                         # BuiltModel v1, keys in the bank's order
    report: BuildReport
    replay: ReplayInput                 # U-11.3
    detector: dict[str, list[DetectorRecordOut]]
    placements: list[dict]              # FurniturePlacements.pieces (U-11.7)
    floors_frame: dict[str, dict]       # floor -> { source, toSheet: Vec2, area }
    seconds: dict[str, float]

def build(ctx: BuildContext, log: Callable[[str], None], progress: Callable[[str, float], None]) -> BuildResult  # U3
def write_outputs(result: BuildResult, ctx: BuildContext, log: Callable[[str], None]) -> dict[str, Path]          # U4
```

U4 takes the `units` flags, `inputs.json` (verdicts, `dxfSha1`, converter) and the diff's inputs from `BuildContext`,
and the `lost` flags from the report (U3 reads each conversion report through `BuildContext` and places the lost
inserts in floors); neither ever builds a cache path of its own.

`lines` are the bank's (`cat_of` over the items: wall, glass (glass, window, screen), door, stair, railing, noise; noise
the longest 6,000 per floor); **pieces are the rectangles the build actually paired** (`strips(F['segs'], 0.04, 0.45)`
and the glass pairs at the build's 0.005 - 0.30), not recomputed for the picture as the bank page did (0.60 and fill
edges); rings are the built wall and glass parts at `z0 < 0.01`, as the bank's.

### 10.9 Bytes

`model.json` = `json.dumps(model, separators=(',', ':'), ensure_ascii=False).encode('utf-8')`, **no trailing newline**
(the prototype's bytes; the store keeps them as they are: `create_version` never re-serialises). Every settings number
reaches it through U-10.4's coercion (`0.0`, never `0`). Optional v1 fields only
where used (`sheetShift` when non-zero, `plinth` on plinth slabs; never `fit` or `stairs.panels` in this milestone).
`project`, `shortName`, `projectNo`, `photoName`, `maxPrefix` come from `settings.project`; `source` = the upload names
of the floors' sources in floor order, each once (the bank: `["I1201 - LEVEL 1 GENERAL ARRANGEMENT.dwg", "I1202 - LEVEL
2 GENERAL ARRANGEMENT.dwg"]`; only the storage key is ever made safe, never the name).

---

## 11. A version's outputs

### 11.1 What `saveBuild` hands `create_version` (D-9.5)

`VersionDraft { label, source_kind: 'cad', source_files: model.source, model_json: <bytes as built>, stages_json,
presentation, assets: { 'topview.png' }, downloads: { <maxFileName>: <bytes> }, source: { inputs.json,
conversion-<sha12>.json per source, build-report.json, openings.json, pieces.json, flags.json }, carry_overrides_from:
latest version if carryHeights, project_data: <settings JSON> }` (`project_data` is new: written as
`versions/<n>/project-data.json`). `create_version` also refuses a `.ms` whose line-2 stamp is not
`sha1(model.json)[:12]` (`seed.build.ms_stamp`), checked **after** its file-name checks (so
`test_create_version_refuses_odd_file_names` still sees the name error; `test_store.py`'s draft with the stamp
`000000000000` gets the real stamp, a change on purpose, ACCEPTANCE 3). version.json: `stamp = sha1(model)[:12]`,
`stampSource 'model.json'`, no `seed` record (that is how the seed tells an uploaded version, U-15.3). **Stale (UR):** the
settings changed since the run in more than `office` (the office only names the layer memory read at the prepare and
written at save; no build step reads it), so picking the office on the Save step keeps the build saveable, and
`project_data`, `project-settings.json` and the office memory take the office as the settings have it at save. Then
`saveBuild` writes `project-settings.json` (office, naming, the pinned offset), updates the office memory (U-8.4) and marks the
build saved. **Save is idempotent:** the "still open" check, `create_version` and marking the build saved all happen
under the per-build lock (U-3.2), so a double click or a client retry gets 409 `build_saved` (with the version number
in `details`) instead of a second version; the Save button is disabled while the request is in flight. The furniture
CSV is not stored: the API makes it from the model (D-18.8), as for every version.

### 11.2 Presentation for an uploaded version (`out/presentation.py`, pure Python, no HTML anywhere)

| Field | Value |
|---|---|
| documentTitle | `shortName` |
| heading | `project` (no "(test)", no "CAD -> 3D") |
| intro | text runs, never parsed from markup: `Built from <n> drawing(s) (<file names>): walls from the wall layers, glass from the glass layers, and <d> doors, <w> windows and <p> passages from the openings detector.` + (furniture) ` <k> furniture boxes in <j> kinds.` + ` Levels <levels> m.` + ` No AI used.`; the project name, when quoted, is one plain run (`&`, `<` and Thai stay as they are) |
| accent | `#2f6f8f` |
| legend | inline; for the part kinds present, in this order and these colours (D-5.4): Walls and lintels `#e3ddd3`, Glass `#9cc3d5`, Glass frames `#5d6b74`, Railings `#6f6a75`, Stairs `#b9c7b4`, Single-line items `#e0a458`, Floor plates `#d4d8d2` |
| floorButtons | none for one floor; `{ all: 'Both floors' }` for two; `'All floors'` for three or more; labels = floor names |
| camera | `{ kind: 'fitSlabs', away: [0.52 d, 0.53 d, 0.63 d], targetY: 2.5, panForPanel: true, far: max(600, 6 d) }`, d = the slabs' bounding-box diagonal (at least 20 m). Check: at 1400 x 880 every slab corner projects inside the canvas left of the panel |
| creaseAngle, partStyles, toggles | defaults |
| groundPlane | for a plinth project `{ size: [w + 20, d + 20] rounded up to 10 m, colour: '#dfe3e0' }`, else null |

The bank re-upload's presentation therefore differs from `fixtures/presentation/bank-sampeng-v2.json` (heading, intro,
camera): listed in the bank's gap report, by design.

### 11.3 Replay data recorded from the build (`out/replay.py`)

ReplayData v1 (D-7) from `ReplayInput`, for any number of floors:
* `floors[k]`: `lines` rounded as the bank did (3 decimals, noise 2), `pieces` (3 decimals, from the real pairing),
  `rings`; `sheet`: floors from separate files side by side in reading order (`i * (width + 3 m)`, the bank rule);
  floors sharing a sheet at their `sheetShift`.
* `source { files, layersInUse, units }`; `intro`, `layers` rows, `captions` from **fact-driven templates**: a sentence
  is said only when its fact holds ("with no shift" only when there is none, "exported from Revit" only when
  `exportedFrom` says so, "and the lift shaft" only when one exists, "Done: <n> levels"); every floor is named (two:
  "on Level 1 and Level 2"; more: "on 3 floors"); placeholders `{<key>level}` and `{<key>height}` for every floor (D-7.3).
  No `panelIntro`. `stepTitles`, `colors`, `layersTitle` omitted (defaults, D-7.2).
* For the bank, `lines`, `rings`, `sheet` and `source.files` equal v2's `stages.json`; `pieces` (real pairing) and the
  texts differ, listed (ACCEPTANCE A-1).

### 11.4 Pictures (`out/pictures.py`)

`topview.png`: the bank builder's top view drawn from the model alone (parts by kind, stairs, voids, openings with their
numbers, room names, a title per floor), matplotlib Agg, one panel per floor (a single Axes for one floor: the crash
fixed). For the bank's model the bytes equal v2's `assets/topview.png` (should; recorded if not). The furniture picture
is not made (no use in the app).

### 11.5 The 3ds Max script (`out/maxscript.py`; plan 3.6, the owner's rule of 19 Oct)

One generator for every model: the bank's `generate_maxscript.py` and the hotel's merged, reading **only the model bytes
and a `MaxTexts` profile**; furniture through the vendored `furniture_max.fragments` / `splice`. The hotel's differs
from the bank's in more than words (`diff --strip-trailing-cr` of the two; `hotel_test/test_hotel_maxscript.py` line
734 lists the lines that differ on purpose): a header computed from the model (which kinds follow the wall height and
which keep their own, from the parts' `follow`; the stair width from the first floor's step parts; the lift doors'
`drawnWidth`), datum Picture lines computed from `model.pictureFrame`, the placement tick box's tooltip, the `Placed at
... (__FRAME__)` lines, and one more refusal ("two holes touch": two holes of one outline within 0.0005 m). Every part stays live (spline
+ Extrude with mesh output + Smooth; Collapse gives Editable Mesh, never Editable Poly); furniture as Box primitives.
* **Bytes:** CRLF written explicitly (`'\r\n'.join(lines) + '\r\n'` as bytes, never the platform's text mode); line 2
  `(model data <sha1(model)[:12]>)`; `num` / `pt` with 4 decimals and negatives in brackets; `ascii_name` with both
  spellings; a "no placeholder left" check.
* **Kinds:** the bank's 11 `KINDS` lines and its 7 materials stay fixed; a case line and a material are written only for
  a kind outside them that the model uses (pane, balustrade, low, builtin, deck, post), so the bank's bytes cannot move.
  `plinth` slabs build from `z0 = -level`. `fit`, `stairs.panels`, `sheetShift` are not read; `pictureFrame` is read
  only by a profile that asks for picture lines (the hotel's; an uploaded model never has one).
* **Refusals:** the bank's checks plus the hotel's "two holes touch" (every model goes through it; the bank's model
  passes it, which its golden proves).
* **Texts:** a `MaxTexts` profile (JSON in `fixtures/upload/max-texts/`, owned by U4) carries `header` (verbatim lines
  with placeholders, CRLF added by the generator), `tooltip` (the placement tick box's), `placedAt` (the "Placed at"
  lines), `datumSource` (the datum's Source property), `datumExtra` (verbatim extra datum lines with placeholders),
  `titleSuffix`, `builtBy`, `page`, `rolloutSuffix`, `notes[]`, and `pictures: boolean` (write one datum Picture line per
  floor from `model.pictureFrame`). The generator computes for every profile the placeholders the hotel's header uses:
  `__FOLLOWTXT__` / `__KEEPTXT__` from the parts' `follow` flags (better for uploads too: the header then says what
  "Update levels and heights" does to this model), `__STAIRTXT__` (from step parts), `__DOORTXT__` (from lift doors'
  `drawnWidth`), `__FRAME__` (from the profile). Profiles: `bank-27oct` and `hotel-2nov` (fixtures, for the goldens
  only) reproduce the two scripts byte for byte; `upload` (the default) says `built by the walkthrough app from <files>,
  <d Mon yyyy>`, page `the walkthrough app`, no "(test)", `converted with LibreDWG 0.14; drawing units <units>` (or `DXF
  exported by its own program`), the follow / keep sentence, and a glass note only when the model has Revit glass wall
  types. The date is the build's date, so a test that compares an upload-profile script generates its expected bytes
  with the same date.
* **Names:** an object name that `ascii_name` reduces to nothing (Thai) falls back to its id (`BB_L1_Wall_012`).
* The suite's prototype script used an older template (`PS_level`, a `FOLLOW` table; 716 lines differ): an uploaded
  suite's script differs from `Presidential_Suite.ms` by design (gap report).

### 11.6 Offline HTML and the CSV

The offline file needs nothing new: the API's `downloadOfflineHtml` and `npm run make:offline` work for any version
(D-16). **The CSV formula guard comes in now** (uploads bring other offices' block names): in the text columns (`id`,
`level`, `kind`, `kind_label`, `family`, `block`, `layer`, `dxf_handle`, `on_top_of`, `note`) a value starting with `=`,
`+`, `-`, `@`, TAB or CR gets a leading `'`, before RFC 4180 quoting; number columns never change. Same rule in the API
(`furniture_csv.py`) and the viewer (`furniture/logic.ts` csv). The four seeded CSVs are unchanged (no text field starts
that way; checked against the goldens).

### 11.7 Each piece's block turn and mirror (for real models later)

`pieces.json` (FurniturePlacements) keeps, per furniture piece, the INSERT's nested key, block, family, element id,
insertion point (sheet m), world turn and scale factors with their sign from the cache's INSERT item, beside the box's
own `rot`, and two mirror fields:
* `insertMirrored` = sx sy < 0 on the INSERT. In a Revit export it is always false (all 174 readable bank INSERTs have
  scale (1, 1, 1)): Revit draws a flipped family instance **into the block definition**;
* `drawnVariant` (`'same' | 'mirrorX' | 'mirrorY' | 'turned180' | null`): the piece's drawing compared with its
  family's first piece, a port of `furniture_test/bank_furnished/scripts/block_variants.py` (104 lines) on the cache
  items: each piece's subtree points brought back into the block's frame (minus the insertion point, turned back by the
  INSERT's turn, divided by its scale), sampled at 5 mm, and compared with the family's first piece as it is, mirrored
  in x, mirrored in y and turned 180 degrees by the mean nearest-point distance both ways; the closest wins. `null` for
  a loose-line piece or a family of one. The bank has 26 pieces in 9 families drawn as mirror images (9 of the 19 mollie
  chairs, 6 of 16 Aeron, 4 of 8 Fritz Hansen, 2 of 4 Haworth, 1 of 3 SE107 benches, a console cabinet, a vase, an Etta
  armchair, a work cabinet), all front to back; U3's test expects exactly those 26 as not `same` (should; if the port
  is not done in this milestone the field is written `null` everywhere and the test is listed as later).

The model is not changed (its bytes), and nothing reads the file yet: it is the seam for placing the team's models by
their block (plan 2.5: "a check for Revit's mirror, which is drawn into the block itself"; the block's turn was right in
4 of 4 checkable cases).

---

## 12. The check-and-fix screen, first version

### 12.1 The plan canvas (`apps/web/src/plan/`, owner U7)

* **Local frame:** paths are built in the plan's own integer quanta relative to `PlanGeometry.origin` (never in
  absolute sheet metres: the suite sits near y = -3,500 m, and Skia's float32 path coordinates jitter at close zoom
  when a zoomed absolute path reaches millions of pixels). The overlay, the flags, the fixes and picked points are
  converted into the same local frame once when they arrive, and back to sheet metres only when a fix is written.
  Line widths are set in screen pixels (divided by the current scale).
* One `<canvas>` (device-pixel-ratio aware), never one element per line (20,000 - 40,000 lines a floor). The plan
  geometry is decoded once into typed arrays; one `Path2D` per (layer, type) is built once and cached; a frame draws the
  cached paths with the role's colour (`other` and `ignore` faint, the floor's area lit, the rest dimmed), then the
  overlay (parts filled by kind, slabs outlined, openings as thick segments coloured by kind with their numbers, furniture
  rectangles, set-aside items crossed, flags as rings), then the selection. Pan (drag, arrows), zoom (wheel at the
  pointer, +/-), fit; redraw on `requestAnimationFrame` only when something changed.
* Picking: a uniform grid index (2 m cells) over the items' segments; click = the nearest item within 6 px, shift adds,
  a drag box selects the items wholly inside (`select-inside`) or touched (alt). **Pick modes** (`pick`): `item` (one
  drawn item), `block` (the innermost INSERT whose subtree holds the clicked item, by key prefix; clicking again
  climbs one level; selects the INSERT's anchor key, so a set-aside writes one subtree ref, U-10.6), `layer-in-box`
  (a box selects every item of the clicked item's layer inside it). Tools: `pan`, `select`, `pick-point` (alignment),
  `draw-box` (areas). Keyboard: Esc clears, Delete = set aside the selection.
* Text: only room names and opening numbers, with `fillText`. Hover shows layer, type and key in a DOM tooltip (text).
* Budget: the house sheet (39,000 items) redraws in under 50 ms in Edge on this laptop at 1400 x 880 (measured in U7's
  harness and in the e2e run).

### 12.2 Flags

From the report and the detector, in `overlay.json` (`Flag`):

| Kind | When | Severity |
|---|---|---|
| opening | a passage; confidence <= 0.55; `eitherKind`; host `none` or `line work`; evidence "ends from the swing"; a door with `sidelights` | check |
| single-line | each `single` part (the line work it came from, by key) | check |
| lost | a lost block's insert (U-6.3) inside the floor's area | check |
| outline-wall, outline-glass | each suggestion (U-10.5) not yet accepted or refused | check |
| grey-furniture | each family the kit classified `other`, with its count | info |
| rail-left-out, room-label, plate-dropped | from the report (a dropped plate area: an area next to the walls, outside the rooms they close, with why) | info |
| plate-dropped (UR) | about N m2 inside the walls has no floor plate (the walls closed by 1.5 m, pieces of 4 m2 or more with standing room, 20 m2 in all), or the walls never close and the plate is under half their convex hull (and 100 m2 short): the bank's room rule needs a closed wall network | check |
| room-label (UR) | 3 or more texts that look like room names inside the plate on a layer set to `ignore` or `other` (not block attributes or texts of blocks) | check |
| alignment | spread over 5 mm, one grid direction only, points disagreeing | check |
| units | declared units overruled by the votes | check |
| fix-unmatched | a remembered fix that matched nothing in this drawing, or more than one item (U-10.6) | check |
| detector-skipped | the detector skipped its frame-only sliding units on a floor (`FRAME_ROWS_MAX`, U-10.7): map the tile or symbol layer to `ignore` | check |
| slow | the detector took over 60 s on a floor (`fl.T['total']`) | info |

### 12.3 Tools and what each writes (all into `settings.fixes` or the settings, through `putBuildSettings`)

* **Set aside / Restore** the selected items -> `fixes.setAside` (ItemRef: floor, source, key, sig, rsig, elementId,
  layer, all read from the plan geometry's entry for that key, U-7.5; an INSERT anchor's ref covers its subtree). The
  canvas offers the `block` and `layer-in-box` pick modes so that a piece of furniture drawn as loose lines inside a
  block (one Revit chair is dozens of lines) is one ref, not dozens. At most 20,000 set-asides per build (U-13.2); the
  settings saver shows "too many items set aside at once: set aside whole blocks instead" on a 413.
* **Opening**: click an opening -> kind, head, sill -> `fixes.openings` (a, b as detected, sheet m).
* **Outline suggestion**: wall / glass / refuse -> `fixes.outlineEdges`.
* **Grey furniture**: per family, a kind -> `settings.furniture.words[kind]` gains the family exactly as its flag shows
  it, and any word of the same family (U-10.6 point 4's form) leaves every other kind; the select shows the kind the
  next build gives ("remember for the office" is not offered: no contract field, U6-3).
* **Heights**: the floors' levels and wall heights, the project's door head, railing and single-line heights (the same
  fields as the Floors step).
* **Rebuild** -> `runBuild`; while it runs, the screen keeps the last result.

### 12.4 Diff

`diff.json` from the worker (`out/diff.py`): against the previous `done` build run of the draft and against the latest
version's model (when the project has one). Both sides are compared **in sheet coordinates** (model + offset +
`sheetShift`), so a version in another frame (a seeded project's) still matches part for part. Parts matched by
(floor, kind, outline rounded to 1 cm); openings by (floor, kind, centre within 0.1 m); furniture compared by kind
counts; rooms by name. The check screen lists the counts that
changed and draws added parts green and removed ones red (toggle).

### 12.5 The 3D preview

The Build and Check steps can open the viewer on the draft (`ViewerHost` with `createViewer`, the draft's model, stages
and presentation from the result's URLs, `ids: { projectId, version: 0 }`, `build: 'skip'`, `furnitureHeights:
'host'` with no saver attached: a height typed in a preview is not saved). Closing it disposes the viewer (D-15.4).

---

## 13. API

### 13.1 Routes (new; 24 operations, 37 with the 13 of D-10.2)

Plain `def`, store from `Depends(get_store)`, jobs from `Depends(get_jobs)`, explicit `summary`, `description`,
`response_description` (D-10.1), errors as `ErrorResponse` with the codes below.

| Method, path | operationId | Body -> response | Errors |
|---|---|---|---|
| POST `/api/projects` | createProject | NewProjectRequest -> 201 ProjectDetail | 409 project_exists (`details.suggested`), 422 bad_project |
| GET `/api/offices` | listOffices | -> OfficeList | - |
| POST `/api/uploads` | createUpload | UploadRequest -> 201 UploadSession | 404 project_not_found; 413 too_large; 422 bad_kind |
| GET `/api/uploads/{uploadId}` | getUpload | -> UploadSession | 404 upload_not_found |
| PUT `/api/uploads/{uploadId}/parts/{part}` | putUploadPart | octet-stream -> UploadPartResult | 404 upload_not_found; 411 length_required; 413 part_too_large; 422 bad_part |
| POST `/api/uploads/{uploadId}/complete` | completeUpload | `{}` -> 201 SourceFile | 404; 409 incomplete; 422 bad_kind, unsupported_version |
| DELETE `/api/uploads/{uploadId}` | cancelUpload | -> 204 | 404 |
| POST `/api/projects/{projectId}/builds` | createBuild | NewBuildRequest -> 201 BuildDetail | 404 project_not_found, source_not_found, version_not_found, build_not_found; 422 bad_sources; 503 builder_missing |
| GET `/api/projects/{projectId}/builds` | listBuilds | -> BuildList (newest first) | 404 |
| GET `/api/projects/{projectId}/builds/{buildId}` | getBuild | query `withSettings` (bool, default true) -> BuildDetail (`settings: null` when false: the 1 s poll asks without them and refetches with them when `settingsRevision` changes) | 404 build_not_found |
| PUT `.../builds/{buildId}/settings` | putBuildSettings | BuildSettingsUpdate (+ `If-Match: "<revision>"`; body up to 8 MiB) -> BuildDetail | 404; 409 build_saved, not_prepared (revision 0: the proposal is not in yet), run_in_progress (a one-source prepare after a units change is running); 412 revision_conflict (`details: { revision, settings }`); 413 body_too_large; 422 invalid_settings (`details.issues: [{ path, message }]`) |
| POST `.../builds/{buildId}/run` | runBuild | `{}` -> 202 BuildDetail | 404; 409 run_in_progress, not_prepared, build_saved, units_unconfirmed, layers_not_reviewed; 503 builder_missing |
| POST `.../builds/{buildId}/cancel` | cancelBuildRun | `{}` -> BuildDetail | 404; 409 no_run |
| GET `.../builds/{buildId}/sources/{sha1}/conversion` | getBuildConversion | -> ConversionReport (raw) | 404 not_ready |
| GET `.../builds/{buildId}/sources/{sha1}/drawing` | getBuildDrawing | -> DrawingRead (raw) | 404 not_ready |
| GET `.../builds/{buildId}/sources/{sha1}/plan` | getBuildPlan | -> PlanGeometry (raw, gzip) | 404 not_ready |
| GET `.../builds/{buildId}/overlay` | getBuildOverlay | -> BuildOverlay (raw) | 404 not_built |
| GET `.../builds/{buildId}/diff` | getBuildDiff | -> BuildDiff (raw) | 404 not_built |
| GET `.../builds/{buildId}/model` | getBuildModel | -> model.json (raw, `X-Model-Stamp`) | 404 not_built |
| GET `.../builds/{buildId}/stages` | getBuildStages | -> stages.json (raw) | 404 not_built |
| GET `.../builds/{buildId}/topview` | getBuildTopview | -> image/png | 404 not_built |
| GET `.../builds/{buildId}/max-script` | downloadBuildMaxScript | -> the draft `.ms`, attachment `<stem>_draft.ms` | 404 not_built |
| POST `.../builds/{buildId}/save` | saveBuild | SaveBuildRequest -> 201 VersionDetail | 404; 409 not_built, stale, run_in_progress, build_saved (`details.version`); 422 invalid_output |
| DELETE `.../builds/{buildId}` | deleteBuild | -> 204 | 404; 409 run_in_progress, build_saved |

Raw routes answer as D-10.1's raw files do: the stored bytes, `ETag: "<sha1>"`, `Cache-Control: no-cache`,
`If-None-Match` -> 304, `X-Content-Type-Options: nosniff`; their 200 schema in OpenAPI is `{ type: object }` (the shapes
are `upload-contracts.ts`'s, as BuiltModel's are the viewer's). Path params: `uploadId` `^u[0-9a-f]{24}$`, `part` int
1 - 10000, `buildId` `^[0-9]{8}T[0-9]{6}-[0-9a-f]{6}$`, `sha1` `^[0-9a-f]{40}$`, `projectId` as before.

### 13.2 Models

`services/api/walkthrough_api/models_upload.py` (new, frozen after the scaffold): every type of `upload-contracts.ts`
section 5, plus `BuildSettings` and its parts (section 1), with the same camelCase names (`ApiModel` config of
`models.py`). `BuildSettings` is validated strictly (`extra='forbid'`) and then by `settings_issues()` (U5's code):
floor keys unique and `^[A-Za-z0-9_]{1,32}$`; levels strictly increasing; every floor's source among the sources; boxes
with `x0 < x1`, `y0 < y1`; heights 0.05 - 50 m; naming patterns; roles in the enum; at most 5,000 layers, 20,000
set-asides and 5,000 other fixes (20,000 set-asides of about 300 bytes each is about 6 MB, inside the 8 MiB body
limit of `putBuildSettings`); strings at most 500 characters; every source's `units` set (not `null`) once adopted. The raw files' records are pydantic models too (`DrawingRead`, `PlanGeometry`,
`ConversionReport`, `BuildOverlay`, `BuildDiff`, `FurniturePlacements`, `OpeningsFile`, `JobRecord`), used to check the
worker's outputs, **not** in OpenAPI. `models.py` does not change.

### 13.3 createProject

Id (UR: a slug with no letter is no id: a Thai name with a number gave `31`; a given id may not end in `-` or hold
`--`): the given one, or a slug of the name (NFKD, ASCII letters and digits, spaces and punctuation to `-`, 2 - **40**
characters for a new project, U-4.1's path length; a longer slug is cut at a `-` and the given id is refused with 422
`bad_project`); empty (Thai names) -> `project-<6 hex>`. Taken -> 409 `project_exists` with `details.suggested` (the next
`-2`, `-3` ...). Reserved: `new` and the seed table's ids (`bank-sampeng`, `presidential-suite`, `sukhumvit-house`,
`hotel-lobby`) whether or not they exist. Writes `meta.json` (`sourceKind 'cad'`, latestVersion 0) and
`project-settings.json` (office; naming derived: `photoName` = the short name's ASCII with other runs as `-`, at most 64,
else `Project`; `maxPrefix` = the initials of the first two to four ASCII words, upper case, padded with `X` to 2;
`maxFileName` = the ASCII words joined by `_` + `.ms`, at most 60). Staff edit them on the Floors step.

### 13.4 Store and jobs (code, not frozen)

`store/base.py` gains the records of `upload-contracts.ts` section 2 (`Record` subclasses, as `ProjectMeta`), the methods
for uploads, sources, builds, settings files, offices and project settings, and `VersionDraft.project_data: BlobSource |
None`; `LocalStore` implements them (atomic writes, `retry_on_sharing`, the
store lock only around `meta.json` / version writes, never around a run; the per-build lock of U-3.2 around adoption,
validation and save). `jobs/base.py`: `JobRunner` protocol (`start(run dir)`, `cancel(run dir)`, `alive(launch or job
record)`), `jobs/local.py`: `LocalJobRunner` (U-3.2, U-3.4: `launch.json` after `Popen`, the 15 s kill on a timer
thread, the FILETIME `procStart`), `deps.get_jobs`.
Routes never see `app.state` (`test_routes`' rule). Cloud Run Jobs replace `LocalJobRunner` later without a route change.

### 13.5 Middleware, CORS, settings

* A pure-ASGI **body guard** before routing: `PUT /api/uploads/*/parts/*` needs `Content-Length` (411) not above
  `partBytes` (413); `PUT .../builds/*/settings` above 8 MiB and any other `POST` / `PUT` body above 2 MiB is refused
  (413 `body_too_large`), so FastAPI never reads a large body into memory.
* CORS: methods `GET, PUT, POST, DELETE`; headers `content-type, if-match`; exposed `etag, x-model-stamp,
  content-disposition`.
* `settings.py` gains `WALKTHROUGH_BUILDER_PYTHON`, `WALKTHROUGH_LIBREDWG_DIR`, `WALKTHROUGH_CACHE_DIR`,
  `WALKTHROUGH_CACHE_MAX_GB`, `WALKTHROUGH_UPLOAD_MAX_BYTES`, `WALKTHROUGH_RUN_LOCK` (default
  `%TEMP%\walkthrough-run.lock`); `run-api.mjs` passes them through. `/api/health` adds nothing (its schema is frozen); `createBuild` and `runBuild` answer 503
  `builder_missing` with what is missing.
* On start-up: the clean-up of U-4.1 and the `interrupted` marking of U-3.4.

---

## 14. Web app

### 14.1 Routes (React Router 8 data mode; static routes before `:projectId`)

| Path | Screen | Loader |
|---|---|---|
| `/projects/new` | NewProjectPage | `listOffices` |
| `/projects/:projectId/builds/new` | UploadPage | `getProject`, `listBuilds` |
| `/projects/:projectId/builds/:buildId` | BuildPage (steps via `?step=files|layers|floors|build|check|save`) | `getBuild` |

Plus: the **New project** button on the list, **New version** and **Drafts** in the project page's app bar, the empty
state's text `No projects yet: make one with New project` (was "run npm run seed"). Document titles `New project ·
Walkthrough`, `<name> · draft · Walkthrough`.

**A project with no version yet** (made by `createProject`, its upload or prepare perhaps unfinished) must stay
reachable: its card (`components/ProjectCard.tsx`, today a card with no link when `hasVersions()` is false) links to
its newest open draft, or to `/projects/:id/builds/new` when it has none; its page (`pages/ProjectRedirect.tsx`
`NoVersions`, today only "Back to projects") lists its drafts (`listBuilds`: name of the files, status, Continue,
Delete) and offers **Upload drawings**. ACCEPTANCE A-7 walks this path (leave the draft, come back from the list).

### 14.2 Files (owner U6 unless said)

`pages/{NewProjectPage, UploadPage, BuildPage}.tsx` (and the changes to `ProjectCard.tsx`, `ProjectRedirect.tsx` of
U-14.1); `build/{FilesStep, LayersStep, FloorsStep, BuildStep, CheckStep, SaveStep, StepBar, FlagList, DiffPanel,
OpeningEditor, FurnitureWords, PreBuildChecklist, OfficeSelect}.tsx`; `upload/{upload.ts, contracts.ts (the scaffold's
copy, not U6's), useBuild.ts (polling `getBuild` with `withSettings: false`: `refetchInterval` 1000 while a run is
queued or running, else off; the full detail is fetched again when `settingsRevision` changes), settingsSaver.ts
(debounce 800 ms, one in flight, If-Match, a 412 reloads and re-applies this tab's change, a 413 shows a plain message),
draftViewerProject.ts}`; `plan/**` (U7: `index.ts` (the scaffold's signatures, U7 fills the bodies), `PlanCanvas.tsx`,
`decode.ts`, `paths.ts`, `view.ts`, `hit.ts`, `colours.ts`, `areas.ts`, `near.ts`); new `components/ui/` files written by
hand on `radix-ui` 1.8.1 (no shadcn CLI run): `input`, `label`, `dialog`, `tabs`, `checkbox`, `progress`,
`radio-group`, `scroll-area`, `table`, `textarea`.

### 14.3 Rules

* Generated client for every JSON route (`createProjectMutation`, `getBuildOptions` ...); raw files fetched by their
  URLs from the API's responses and typed by `upload/contracts.ts`; upload parts with `fetch` to `partUrls` (U-5.3).
  The section 5 shapes therefore exist twice (generated and hand-written): a scaffold type test
  (`apps/web/test/upload-generated-types.test-d.ts`) asserts that the generated `BuildSettings`, `BuildDetail`,
  `UploadSession` and `SourceFile` and the `contracts.ts` ones are mutually assignable, so an optional-versus-nullable
  difference shows at the scaffold, not at integration.
* The Layers table: native `<select>` per row showing the role labels of U-8.1, rows virtualised above 200 (a fixed row
  height and a windowed slice: no library); the "close to walls" chip on `ignore` rows from `nearLayers(plan,
  wallLayers, 1.0)` (U7's `plan/near.ts`).
* The Floors step's "propose areas again on the wall layers" runs in the browser on the decoded plan (the clustering of
  U-7.3 with a layer filter, in `plan/areas.ts`). Boxes default to pad 0.5 and match `all`, under "Advanced" (U-9.1);
  level tags are listed whole (U-9.2); the project details hold the office select (U-8.4).
* **Pre-build checklist** on the Build step, before **Build** is enabled, each line linking to its step: units not
  confirmed; Layers step not reviewed; a floor with no wall height; a floor with no source or an empty area; a source
  whose verdict is `loss` (a warning: "parts of the drawing were lost in conversion; export a DXF from AutoCAD for a
  complete build", never a block); a source still being read again.
* While `RunInfo.cancelRequested` is true the run shows "Stopping..." and Cancel is disabled.
* Drawing text in React text nodes only (no `dangerouslySetInnerHTML` anywhere: a test greps `apps/web/src`).
* `apps/web/test/mock-api/core.ts` gains the new routes (in-memory uploads and builds whose runs complete from fixtures).

### 14.4 Draft preview

`upload/draftViewerProject.ts`: `toViewerProject`'s sibling taking a `BuildDetail` (+ fetched model, stages): stamp =
`result.stamp`, presentation from `result.presentation`, no pictures, no saved heights.

---

## 15. Frozen contracts: what changes and how

### 15.1 Changes (all applied by the scaffold U0, in one step, then frozen again)

| Frozen item | Change |
|---|---|
| `docs/contracts.ts` and its viewer copy | **none** (the upload types live in `docs/upload/upload-contracts.ts`, copied to `apps/web/src/upload/contracts.ts`) |
| `built-model.schema.json` (both copies) | **none** (flags, handles, confidences, placements go in sidecars) |
| `models.py` | **none**; new `models_upload.py` |
| routes | new modules `routes/uploads.py`, `routes/builds.py`, `routes/offices.py`; `createProject` added to `routes/projects.py`; bodies `raise ApiError(501, 'not_implemented', ...)` until U5 |
| `main.py`, `settings.py`, `deps.py` | routers; CORS methods; the body guard; the settings; `get_jobs` |
| `apps/web/openapi.json`, `src/api/generated/**` | regenerated (`npm run gen:api`) |
| root `package.json` | scripts `test:builder`, `make:reference`, `vendor:libredwg`; `check:pins` covers the builder lock and `vendor/libredwg.manifest.json` |
| `tests/e2e/playwright.config.ts` | the API server seeds a fresh store (`--seed-fresh`) instead of copying `app/data`; it passes `WALKTHROUGH_CACHE_DIR=<WT_TMP>/cache` and the builder settings; a global teardown that cancels open runs through the API (U-3.4) |
| `apps/web/src/plan/index.ts` (new, written by the scaffold) | the final exported signatures of U7's module (`PlanCanvasProps`, `DecodedPlan`, `decodePlan`, `proposeAreas`, `nearLayers`, a placeholder `PlanCanvas`), so U6 imports from `@/plan` from the first day; U7 replaces the bodies, not the signatures |
| `tools/run-api.mjs` | `--seed-fresh` (runs the seed into `--data` first); passes the builder settings |
| `.gitignore`, `CLAUDE.md`, `README.md` | U-4.1's entries and `services/builder/.venv/`, `vendor/libredwg-*/`, `vendor/*.zip`; the builder pins, LibreDWG, ports, owners, commands |
| pinned counts in tests | `test_openapi.py` (`OPERATION_IDS` + 24, `len(ops) == 37`), `test_routes.py` (37 routes over 7 modules), `test_error_responses_are_typed` (409 / 411 / 412 / 413 / 422-domain also `ErrorResponse`) |
| tests changed on purpose by later steps | `services/api/tests/test_store.py` (U5: the `notes.ms` draft gets the real stamp, U-11.1); `tests/e2e/web.spec.ts` line 65 (U6: the id list filters out `e2e-*` ids) besides the 8 count lines (U-15.3) |

### 15.2 Proving the change is additive

`tools/check-openapi-additive.mjs` (scaffold): reads the committed `apps/web/openapi.json` with `git show
HEAD:app/apps/web/openapi.json` (read-only) and asserts every old path, method, parameter and component schema is
deep-equal in the new one; for `src/api/generated/**` it compares **by exported symbol**: each file's old version
(`git show HEAD:...`) and new version are parsed with the TypeScript compiler API (already a dev dependency), import
declarations are ignored (Hey API writes each import list on one long line, which any new operation rewrites), and
every previously exported function, const and type must be present with identical text; `npm run typecheck`; `cmp` of the two `contracts.ts` copies and of the two `upload-contracts.ts` copies; `npm run
seed` gives the same 5 stamps. The result goes into `docs/contract-issues/U0.md`.

### 15.3 The seed and the e2e store

* The seed refuses to replace a version folder whose `version.json` has no `seed` record (an uploaded version), naming
  it, even with `--force`; `project_meta()` keeps counting uploaded versions (D-9.2).
* The e2e API serves a freshly seeded store, so the four seeded projects are always the starting point; specs that add
  projects use ids `e2e-*`, and `web.spec.ts` / `web-leak.spec.ts` check "the four seeded projects' cards are there"
  instead of "4 cards", and `web.spec.ts` line 65 compares the ids with `e2e-*` filtered out (U6 changes those nine
  lines). Specs run in file order with one worker, so `upload.spec.ts` runs before `web.spec.ts`; both changes are
  needed. `upload.spec.ts` sets `test.setTimeout(10 * 60_000)`: three builds, the uploads and a save take minutes, more
  than the config's 120 s per test.

### 15.4 Recording

Each step writes its own `docs/contract-issues/<U0..U7, UI>.md`; the integration step settles each (D-18.0's rule).

---

## 16. Seams kept for later

| Later | Seam here |
|---|---|
| rooms and slabs from the wall network | `BuildSettings.options` takes new keys; `project-data.json` is the recipe beside which wall segments (plan 3.2) can live; `room-outline` role and outline suggestions; `ReplayInput` per floor |
| climbable stairs | the bank's stair flights and risers in the report; `stair`/`stair-above` roles |
| box editing (rename / recolour kinds, re-kind pieces, add boxes) | furniture words per project and office; `pieces.json` keys; the CSV guard already in |
| real furniture models | `pieces.json` (INSERT key, turn, `insertMirrored`, `drawnVariant` for Revit's mirror drawn into the block, family, element id) |
| lights | the `light` role (remembered, counted) |
| walls by shape, per-piece roles and heights | `ItemRef` keys and the fix matcher (U-10.6) |
| AI-suggested mapping (decision D, opt-in) | `suggest.py` takes a provider; `LayerSuggestion.from` gains a value |
| object storage, Cloud Run Jobs, login | `UploadSession.partUrls` (presigned later), `JobRunner`, `Store`; no route change |
| ODA or AutoCAD as a second converter | `ConversionReport.converter`, the cache's converter folder name |
| layered PDF (tier 2) | a source `kind` and the reader behind the same DrawingRead |

## 17. Risks

| Risk | Handling |
|---|---|
| LibreDWG exists only in temp folders, the brief's copy is broken | copied once into `app/vendor/` with a manifest, re-extractable from the zip; scaffold stops if both copies are gone |
| Conversion loses content (the suite: 5.8 %, 4 blocks inside it) and the count check cannot see what the decoder never read | verdicts and lost inserts on the sheet; the AutoCAD DXF fallback; ODA left to the owner (U-18.12) |
| The builder's environment adds libraries; byte-identity depends on exact versions (GEOS, freetype) | a pinned venv equal to the prototypes' versions (approved 4 Nov; needs PyPI once), `check:pins` resolving each module's file and version, the goldens; the system Python only for a diagnosis (user-site libraries, no pytest) |
| Porting a 1,487-line module-level script changes an order or a float | step-by-step port gated by the bank's sha1s; one change at a time |
| Hostile or huge drawings (C parser, ezdxf, quadratic detector) | child processes in Job Objects with time and memory caps, one run at a time, output size cap, pickles only ours, text as text |
| Handles change on a Revit re-export: remembered fixes miss | element id, then geometry signature; unmatched fixes flagged, never silently dropped |
| The detector's held-out score is 72 % on the tower | every doubtful opening flagged; the opening editor; the fifth drawing still decides the gate |
| Ctrl+C on `npm run dev`, or the API ending, during a run | the worker owns its state and has its own console: it normally finishes (`done`); when a tree kill reaches it (concurrently `-k` after the web server stopped, Playwright's teardown), `interrupted` and run again. No `--reload` in `npm run dev` since 10 Nov (UI-5) |
| 16 GB with the dev servers, Edge and a build | one run at a time machine-wide, OpenBLAS threads 1, 4 GB caps; builders' heavy tests share the lock |
| Uploaded versions break the e2e counts or are overwritten by the seed | fresh seeded e2e store; the seed refuses uploaded versions |
| Wrong units, wrong alignment | door votes and staff confirmation; per-gridline method with a spread; two points |
| The 3D team has not run an uploaded project's Max script | the goldens prove the generator equals the scripts run in Max (bank) or checked (hotel); ask the team to run the first uploaded one |
| Thai names in Max object names | id fallback |
| The canvas is slow on large sheets | cached Path2D per layer, redraw on demand, a measured budget |
| The plan's Phase 1 hours are low for what is left (WORK_BREAKDOWN 9) | reported to the owner with the estimate |
| Windows details that break a run at random: `os.replace` on a file another process reads, a memory cap that fails allocations instead of killing, paths over 260 characters, a lock a test holds while its worker waits on it | retries with back-off, re-raised `MemoryError` and a completion port, 40-character ids and a path check, the `heavy` / `worker` test markers (U-3.2, U-3.5, U-4.1) |
| Set-asides by the line make the settings huge (one Revit chair is dozens of lines) | subtree refs and whole-block picking, an 8 MiB settings body, a cap of 20,000 |

## 18. Decisions made here

0. **Contract changes** follow D-18.0: frozen at the scaffold, defects in each step's own `contract-issues/U<n>.md`,
   settled by the integration step. Where this file and `upload-contracts.ts` disagree, the contract wins for shapes.
1. **The worker is a separate process in its own Python**, talking to the API only through files in the run folder; the
   API never imports the builder and the builder never imports pydantic.
2. **A pinned builder venv** with the prototypes' exact library versions, **approved by the owner on 4 Nov** (plan
   decision row of 4 Nov); it is the only supported path (the system Python keeps its libraries in the user site and
   has no pytest). Reason: byte-identity with the prototypes and a frozen list, as for the API.
3. **LibreDWG lives in `app/vendor/`**, extracted from the release zip (the authority), gitignored binaries plus a
   tracked manifest, GPL kept as a separate program, its README (GPL-3.0) shipped and the licence text fetched by the
   owner.
4. **Store the DWG, not the DXF**; derived files in a cache outside the project (`%LOCALAPPDATA%`), keyed by sha1 and
   reader version. Reason: the conversion is deterministic; the DXF is 6-8x the DWG.
5. **Raw 8 MiB parts over PUT**, no multipart library; every state change is PUT, DELETE or a JSON POST.
6. **One run at a time on the machine**, a lock in `%TEMP%`; heavy steps as Job Object children with caps.
7. **One staff mapping, two derived role tables**; an unknown layer is `other` (read by the detector), `ignore` drops
   it everywhere. Reason: measured on the bank (A-FLOR is the detector's kerb context).
8. **The reader keeps `prims`' frame and arithmetic** (DXF units / 1000, the same division) and only makes flattening
   unit-aware, so every frozen detector output and the bank model reproduce.
9. **A nested handle key per item**, with element id and geometry signature as fallbacks for set-asides.
10. **Areas, levels, alignment and plinth are build settings**, never code: the house's quadrants, `DX_UPPER`,
    `LEVELS/TOP` become a Floors step.
11. **Per-gridline alignment** replaces the median of label shifts; a shift under 0.5 mm is none.
12. **ODA File Converter is not added in this milestone.** Decision F says revisit on losses: the owner's call (licence
    terms unknown); the AutoCAD DXF fallback covers the suite now.
13. **The bank builder is ported, not rewritten**, step by step against its golden; drawing-style rules from the house
    and the suite come in as options that do nothing when their trigger is absent.
14. **The replay records the real build** (pieces from the actual pairing, fact-driven texts), so an uploaded bank's
    `stages.json` differs from v2's in `pieces` and texts; `lines`, `rings`, `sheet` match.
15. **New presentations from facts and text runs** (no "(test)", fitSlabs camera); the bank re-upload's presentation
    differs from v2's by design.
16. **One Max generator** from the model and a text profile; the bank and hotel profiles exist only to prove the
    generator byte for byte.
17. **Sidecars, not model fields**, for confidences, evidence, handles, flags and placements: `model.json` stays the bank
    format and the bank's bytes.
18. **The offset is pinned per project** after its first uploaded version.
19. **The CSV formula guard comes forward** to this milestone (STATUS.md had put it with the box editing): uploads bring
    other offices' block names now. The four seeded CSVs do not change.
20. **The check-and-fix screen's first version**: set aside, opening kind and heights, outline suggestions, grey
    furniture words, floor heights, rebuild, diff. Per-piece role and height changes wait (U-16).
21. **Office memory is written at save**, latest wins with the old role kept; per-project furniture words, per-office
    only when ticked.
22. **The e2e store is seeded fresh** for every run; the seed never overwrites an uploaded version.
23. **Reserved project ids**: `new` and the seed table's.
24. **No new viewer types and no viewer changes** except the CSV guard in `furniture/logic.ts`.
25. **Draft outputs are served only by name** (raw routes); sources, specs, logs and caches never.
26. **A saved build is read-only**; a fix after saving is a new build and a new version (versions are never edited, D-9.5).
27. **The detector oracles are `detector/output/*_openings.json`**, compared without the `floor` field; the acceptance
    settings use the prototypes' floor keys. The blind-run outputs of 27 Oct are history.
28. **Two readings of the floor tags** (U-9.1): per item for the detector and the line readers, whole subtrees by
    majority for the INSERT readers.
29. **Grid labels belong to the floor whose area their line crosses** (U-9.4); labels whose line enters no area are
    elevation labels.
30. **The U3 -> U4 interface is typed** (`BuildContext`, `BuildReport`, `ReplayFacts`, `DetectorRecordOut`; U-10.8), and
    the plan module's signatures are written by the scaffold (U-15.1).
31. **Set-aside refs carry what re-matching needs** (`sig`, `rsig`, `elementId` from the plan geometry); an INSERT ref
    covers its subtree; an element id is never matched alone.
32. **Walk checks are a must for the bank re-upload** and must-run, should-pass for the house, suite and tower, whose
    failures are classified in the gap report (ACCEPTANCE A-6).

---

## Review notes (4 Nov 2026)

Two independent reviewers (fidelity: 22 findings; engineering: 25) read the first version of these documents. Each
finding was checked against the files before it was acted on (the detector outputs and their dates, the frozen code
hashes, the house's area boxes against its grid bubbles, the suite's hand rules, the bank's and hotel's Max
generators, `analysis.md`'s mirror paragraph, the detector's `print(..., file=sys.stderr)`, the user-site location of
the builder libraries, the missing pytest, the plan's 4 Nov approval of the venv, the zip's 75 entries and its missing
COPYING, `web.spec.ts` line 65, `test_store.py` line 151, the 120 s Playwright timeout, the single-line import lists of
the generated client). **Every finding held up; none is rejected outright.** Where the fix adopted differs from the one
proposed, the reason is below.

| Finding | Fixed in | Where the fix differs from the proposal, and why |
|---|---|---|
| F1 oracles name the wrong files | U-0, U-8.2, ACCEPTANCE A-1, A-4, WORK_BREAKDOWN U0 / U3 | - |
| F2 grid labels never reach a floor | U-7.3, U-9.4, ACCEPTANCE A-4, A-5 | - |
| F3 per-item tagging splits blocks | U-9.1, U-10.3, U-10.5 | Whole-subtree reading is used for the **INSERT readers only** (furniture, door blocks, `block_kids`, `drawn_inside`), not for every builder input: the house's upper floor is one xref INSERT, and assigning whole subtrees to the line readers could pull its elevation lines into a plan. Walls, glass, stairs, railings and room names keep the detector's per-item tags |
| F4 majority layer not inert on the bank | U-10.4, U-10.5 | Both guards: an option (`pieceLayer`, default `'insert'`) **and**, when on, only for INSERTs whose own layer has no furniture role and never for a block holding furniture inserts |
| F5 `mirrored` cannot see Revit's mirror | U-11.7, contracts | The port of `block_variants.py` is a **should** for this milestone (nothing reads `pieces.json` yet); if it slips, `drawnVariant` is written `null` and the test is listed as later |
| F6 record floor names | U-0, U-3.3, U-8.2, ACCEPTANCE A-1, A-4, A-5 | - |
| F7 level-tag regex range | U-7.3, ACCEPTANCE A-4 | - |
| F8 level tags on SPEC, extents, tags in the elevations | U-7.3, U-9.2, ACCEPTANCE A-4 | - |
| F9 / E18 L29 has no L-PLNT | U-8.4, ACCEPTANCE A-8 | `A-GENM` replaces `L-PLNT` (thirteen layers stay) |
| F10 verdict classes, pre-R13 prefixes | U-5.1, U-6.3 | - |
| F11 incomplete LibreDWG copy, no COPYING | U-0, U-6.1, U-18.3, WORK_BREAKDOWN U0 | - |
| F12 user-site libraries | U-0, U-3.5, U-10.1, U-18.2 | Python children also get `-P` (no working folder on `sys.path`), the hardening that `-I` would have given without breaking `PYTHONPATH` |
| F13 detector warnings on stderr | U-10.7, U-12.2, contracts (`detector-skipped`) | - |
| F14 hotel script needs more than six text fields | U-11.5, ACCEPTANCE A-2 | Both: the profile carries verbatim lines, and the generator computes follow / keep for every profile |
| F15 derived mapping check fails for the bank | U-8.2, WORK_BREAKDOWN U0 step 8 | - |
| F16 `A-GLAZ*` -> glass | U-8.3 | Also added `A-DOOR-IDEN`, `A-GLAZ-IDEN`, `A-WIND-IDEN` -> other, so tag layers do not fall into `*-IDEN` room names |
| F17 gaps missing from A-5 | ACCEPTANCE A-5 | - |
| F18 integer JSON numbers break the golden | U-10.4, U-10.9 | - |
| F19 items with no points | U-9.1 | - |
| F20 element id names a whole instance | U-7.2, U-10.6, contracts (`rsig`) | - |
| F21 seeded projects change frame | U-3.3, U-9.6, U-12.4 | A U3 check that the house's ground-floor walls land on v1's with the pinned offset, since v1's frame came from a frozen centre |
| F22 door-head order | U-10.4 | - |
| E1 ItemRef fields the browser cannot fill | U-7.5, U-12.1, U-12.3, contracts | The signatures ride in **PlanGeometry** (one file, no new route) rather than a separate index; the size cost (about 3x, ~0.5 MB for the house) is stated in U-4.3 |
| E2 U3 -> U4 interface in prose | U-10.8, WORK_BREAKDOWN U0 | `BuildReport.summary` holds the bank summary's exact structure and the upload keys sit beside it, so the golden comparison stays one equality |
| E3 `DecodedPlan` undefined | U-15.1, WORK_BREAKDOWN U0 / U6 / U7 | - |
| E4 `os.replace` sharing violations | U-3.2, WORK_BREAKDOWN U0 / U1 | - |
| E5 `procStart` format, launch gap, cancel races | U-3.4, contracts | The raw FILETIME as a decimal string (no rounding question at all) |
| E6 run lock held by the test that spawns the worker | U-3.5, ACCEPTANCE 2.1, WORK_BREAKDOWN U0 | - |
| E7 adoption race, units change | U-3.1, U-3.3, U-7.4, U-13.1 | `putBuildSettings` answers 409 `not_prepared` until adoption (the simpler of the two proposals: no field merging) |
| E8 projects with no version unreachable | U-14.1, ACCEPTANCE A-7 | - |
| E9 memory cap does not kill | U-3.5, U-7.1 | - |
| E10 settings grow past the body guard | U-12.1, U-12.3, U-13.1, U-13.2, U-13.5 | Subtree refs, pick modes, an 8 MiB limit for the settings PUT and a poll without settings; fixes are **not** regrouped by source (the shape stays one ref per pick) |
| E11 usability of the Layers and Floors steps | U-2, U-8.1, U-8.3, U-9.1, U-14.3, contracts | The "seen once" gate is a `BuildRecord.layersReviewedAt` set through `BuildSettingsUpdate.layersReviewed`, not a settings field (it is not part of the recipe a version keeps) |
| E12 A-6 must on out-of-scope rules | ACCEPTANCE A-6, U-18.32 | - |
| E13 hours | WORK_BREAKDOWN 9 | Re-estimated part by part with this revision's additions: ~205 h likely (155 - 275), ~140 h elapsed at the foundation's ratio including the usage-limit waits; `upload-walk.spec.ts` moved to U7 |
| E14 path length | U-4.1, U-13.3 | - |
| E15 e2e id list, timeout, dated script | U-15.1, U-15.3, U-11.5, ACCEPTANCE 3 / A-7 | - |
| E16 `test_store.py` stamp | U-11.1, U-15.1, ACCEPTANCE 3 | - |
| E17 numstat cannot prove additivity | U-15.2 | - |
| E19 Ctrl+C and teardown | U-3.4, U-15.1, contracts (`cancelRequested`) | A `cancelRequested` flag on the run instead of a new `cancelling` status (the status enum stays what the worker writes) |
| E20 save not idempotent | U-11.1, U-13.1 | - |
| E21 every builder re-running `make:reference` | ACCEPTANCE 2.1, WORK_BREAKDOWN U0 | - |
| E22 seeded projects have no settings, venv approved | U-3.3, U-8.4, U-10.1, U-18.2 | - |
| E23 the cache grows forever | U-4.2 | Eviction runs in the worker, which holds the machine lock, rather than in the API (the cache is the worker's) |
| E24 float32 jitter on the canvas | U-12.1 | - |
| E25 cache name before the read, two TS copies | U-4.2, U-14.3, WORK_BREAKDOWN U0 | - |
