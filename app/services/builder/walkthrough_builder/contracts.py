"""The calls between the builder's parts (docs/upload/DESIGN.md U-10.8; WORK_BREAKDOWN U0 step 3). Scaffold U0; frozen.

U1 (the worker) calls U2 (reader, suggestions), U3 (the model builder) and U4 (outputs) ONLY through the functions below,
and U3 hands U4 exactly the TypedDicts below (total=True: every key present; `NotRequired` only where marked). Both
sides test against the scaffold's fixtures `fixtures/upload/build-result.bank.json` and `replay-input.bank.json`
(a U3 test asserts its bank BuildResult has exactly their key structure and types; U4's tests read only those fixtures;
`tests/test_contracts.py` walks them against these types).

The functions here delegate to the implementing modules, imported when called (so a stub raising NotImplementedError
or a missing module fails the call, never the import of this file). JSON shapes that leave the builder (the run
folder's files) are upload-contracts.ts's; these types are internal.
"""
from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import TypedDict

Vec2 = list[float]                      # [x, y]

Log = Callable[[str], None]
Progress = Callable[[str, float], None]


# ===================================================================================================================== U2
class ReadResult(TypedDict):            # U2 -> U1
    items: str                          # path of items.pkl in out_dir
    drawing: str                        # path of drawing.json in out_dir
    plan: str                           # path of plan.json.gz in out_dir
    units: dict                         # DrawingRead.units (its `used` names the cache folder, U-4.2)
    seconds: float


def read_source(dxf_path: Path, units: str | None, out_dir: Path, *, source: dict, log: Log) -> ReadResult:
    """U2 (U-7): one ezdxf pass over `dxf_path` writing items.pkl, drawing.json and plan.json.gz into `out_dir` (a
    temporary folder: U1 renames it to read-<rv>-<used units> afterwards, U-4.2). `units` None lets the reader decide
    (U-7.4). `source` = {sha1, name} of the upload (DrawingRead.source)."""
    from .read import read_source as impl
    return impl(dxf_path, units, out_dir, source=source, log=log)


def suggest(drawings: list[dict], office: dict | None) -> dict:
    """U2 (U-8.3): DrawingRead of every source of the build + the office memory (OfficeMapping or None) ->
    LayerSuggestions."""
    from .suggest import suggest as impl
    return impl(drawings, office)


def propose_settings(spec: dict, drawings: list[dict], suggestions: dict, conversions: list[dict],
                     latest_version: dict | None) -> dict:
    """U2 (U-3.3): -> BuildSettings (revision 1's). latest_version = { model, msName } of a project with no
    project-data.json (its latest version's model.json as a dict and its stored .ms download's name), else None."""
    from .propose import propose_settings as impl
    return impl(spec, drawings, suggestions, conversions, latest_version)


# ===================================================================================================================== U1
class ConvertResult(TypedDict):         # U1 internal (convert.py)
    dxf: str                            # path of plan.dxf
    log: str                            # path of convert.log
    seconds: float
    peak_mb: float | None
    exit_code: int | None
    memory_hit: bool


# ================================================================================================================ U3 -> U4
class SourceContext(TypedDict):         # one per source, from the prepare and the build's `ensure` step
    sha1: str
    name: str
    kind: str                           # 'dwg' | 'dxf'
    units: str                          # the units the read used
    conversion: str | None              # path of conversion.json (None for a DXF upload)
    drawing: str                        # path of drawing.json (cache)
    items: str                          # path of items.pkl (cache)
    plan: str                           # path of plan.json.gz (cache)
    dxfSha1: str | None


class BuildContext(TypedDict):          # U1 builds it; U3's build and U4's write_outputs both take it
    spec: dict                          # the JobSpec (spec.json) as read
    sources: list[SourceContext]
    converter: dict | None              # { name, version, exeSha1 }
    previousRunModel: str | None        # path of the previous done build run's model.json (diff)
    versionModel: str | None            # path of the latest version's model.json (diff)
    outDir: str
    tmpDir: str


class AlignReport(TypedDict):
    method: str                         # 'none' (floor 0) | 'origin' | 'grid' | 'points'
    shift: Vec2                         # applied to the floor's items (0, 0 when under 0.5 mm)
    spread: float | None                # m, the largest residual
    labels: list[str]                   # grid labels used
    families: int                       # direction families shared (0, 1, 2)


class SingleLine(TypedDict):            # a `single` part and the line work it came from
    part: int
    keys: list[str]
    layer: str
    a: Vec2                             # sheet m
    b: Vec2                             # sheet m


class OutlineSuggestion(TypedDict):
    edge: list[Vec2]
    kind: str                           # 'wall' | 'glass'
    length: float
    state: str                          # 'open' | 'accepted' | 'refused'


class FloorUploadReport(TypedDict):
    source: str
    area: dict
    items: int
    itemsNoPoints: int
    subtreesOutside: int
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
    liftShaft: bool
    stairs: int
    furniturePieces: int
    furnitureKinds: int


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


def build(ctx: BuildContext, log: Log, progress: Progress) -> BuildResult:
    """U3 (U-10): the model and everything the outputs need, from the BuildContext."""
    from .build import build as impl
    return impl(ctx, log, progress)


def write_outputs(result: BuildResult, ctx: BuildContext, log: Log) -> dict[str, Path]:
    """U4 (U-11): writes every output file into ctx['outDir'] -> {output name: path} (model.json, stages.json,
    presentation.json, report.json, overlay.json, diff.json, openings.json, pieces.json, topview.png, <maxFileName>,
    inputs.json)."""
    from .out import write_outputs as impl
    return impl(result, ctx, log)


#: Every TypedDict of this module by name (tests/test_contracts.py walks the fixtures against them).
TYPES: dict[str, type] = {t.__name__: t for t in (
    ReadResult, ConvertResult, SourceContext, BuildContext, AlignReport, SingleLine, OutlineSuggestion,
    FloorUploadReport, FixesReport, BuildReport, DetectorRecordOut, ReplayFacts, ReplayFloor, ReplayInput, BuildResult,
)}
