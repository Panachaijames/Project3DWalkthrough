"""API models of the upload milestone (docs/upload/DESIGN.md U-13.2), field for field from
docs/upload/upload-contracts.ts: camelCase JSON (models.py's ApiModel config), the same optionality (`x?: T | null` ->
`T | None = None`; `x: T | null` -> required `T | None`).

* Section 1 (BuildSettings and its parts): validated strictly (`extra='forbid'`), then by `settings_issues()`
  (settings_check.py, U5): key and naming patterns, levels increasing, sources, boxes, ranges and counts are checked
  there, so a bad value gets 422 invalid_settings with `details.issues`, not FastAPI's 422. Patterns are given in the
  field descriptions only.
* Section 5 (API bodies and responses): in the routes and so in `apps/web/openapi.json` and the generated client.
* Sections 3 and 4 (the worker's files: JobSpec, LaunchRecord, RunApiRecord, JobRecord, ConversionReport, DrawingRead,
  PlanGeometry, LayerSuggestions, BuildOverlay, BuildDiff, FurniturePlacements, OpeningsFile) and the store records the
  worker reads (OfficeMapping, VersionInputs): pydantic models used to check the worker's outputs (`check_file`), never
  in a route, so not in OpenAPI. `extra='forbid'` everywhere: a key the contract does not name is an error.
Objects whose keys are optional and never null (`Vocabulary`, `Flag.ref`) are TypedDicts (total=False), so a present
key is never written as null.

Frozen after the scaffold U0 (a change moves openapi.json and the generated client): a defect goes in your own
docs/upload/contract-issues/U<n>.md.

The rooms milestone (docs/rooms/DESIGN.md R-12.4, R-12.5; its scaffold R0, 11 Nov 2026; frozen again after it) added,
every field OPTIONAL with a default, so a settings document of before still validates and comes back with the old
values: FloorSetup.ceilingHeight (None), BuilderOptions.slabs / ceilings / stairs (OLD_RULES), SetAside.floorPast
(False), Fixes.closings / rooms / stairs ([]; ClosingFix, RoomFix, StairFix), the overlay's spaces / holes / stairs /
closings / unfloored (absent with the old rule), eight flag kinds, four Flag.ref keys, three part kinds, and the two
rule sets OLD_RULES and NEW_RULES. Fields with defaults do not split the schemas into -Input and -Output (FastAPI 0.150,
pydantic 2.14; checked on these models by R0).
"""
from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import ConfigDict, Field, model_validator
from typing_extensions import Required, TypedDict

from .models import ApiModel, VersionCounts

# ===================================================================================================== shared scalars
Sha1 = Annotated[str, Field(description='40 hex, lower case.')]
Vec2 = tuple[float, float]
Bbox = Annotated[tuple[float, float, float, float], Field(description='[x0, y0, x1, y1], x0 <= x1, y0 <= y1.')]
FloorKey = Annotated[str, Field(description='Floor key, ^[A-Za-z0-9_]{1,32}$.')]

LayerRole = Literal['wall', 'column', 'glass', 'window', 'door', 'screen', 'stair', 'stair-above', 'railing',
                    'furniture', 'room-name', 'room-outline', 'level', 'grid', 'light', 'other', 'ignore']
Units = Literal['mm', 'cm', 'm', 'in', 'ft']
SourceKind = Literal['dwg', 'dxf']
RunKind = Literal['prepare', 'build']
RunStatus = Literal['queued', 'running', 'done', 'failed', 'cancelled', 'interrupted']
StepStatus = Literal['waiting', 'running', 'done', 'failed', 'skipped']
ConversionVerdict = Literal['ok', 'minor', 'loss', 'failed', 'not-converted']
RunErrorCode = Literal[
    'not_a_drawing', 'unsupported_version', 'convert_failed', 'convert_timeout', 'convert_memory',
    'check_failed', 'read_failed', 'read_timeout', 'read_memory',
    'no_floors', 'bad_settings', 'area_empty', 'align_failed',
    'detect_failed', 'build_failed', 'build_timeout', 'build_memory', 'invalid_output',
    'cancelled', 'interrupted', 'internal',
]
FlagKind = Literal['opening', 'single-line', 'lost', 'outline-wall', 'outline-glass', 'grey-furniture', 'rail-left-out',
                   'room-label', 'plate-dropped', 'alignment', 'units', 'fix-unmatched', 'detector-skipped', 'slow',
                   # the rooms milestone (docs/rooms/DESIGN.md R-6.1)
                   'slab-gap', 'room-open', 'room-names', 'doorway', 'stair', 'stairs-none', 'stair-clash',
                   'hole-skipped']
PartKind = Literal['wall', 'column', 'lintel', 'sill', 'parapet', 'glass', 'mullion', 'railing', 'single', 'step', 'slab',
                   'pane', 'balustrade', 'low', 'builtin', 'deck', 'post',
                   'tread', 'landing', 'ceiling']                                     # BuiltModel v2 (rooms R-12.1)

#: The three options of the rooms milestone at their old values: what a missing key means (docs/rooms/DESIGN.md R-1.2).
OLD_RULES: dict[str, str] = {'slabs': 'closed-rooms', 'ceilings': 'off', 'stairs': 'lines'}
#: The three options as every new draft gets them (R-1.3).
NEW_RULES: dict[str, str] = {'slabs': 'network', 'ceilings': 'auto', 'stairs': 'climb'}
LevelLevel = Literal['info', 'warn', 'error']

STRICT = ConfigDict(**ApiModel.model_config, extra='forbid')


class StrictModel(ApiModel):
    """A model that refuses keys the contract does not name."""
    model_config = STRICT


# ===================================================================================== 1. roles, units, build settings
class ProjectNaming(StrictModel):
    photo_name: str = Field(description='^[A-Za-z0-9_.-]{1,64}$ (BuiltModel photoName).')
    max_prefix: str = Field(description='^[A-Z]{2,4}$ (BuiltModel maxPrefix).')
    max_file_name: str = Field(description=r'^[A-Za-z0-9_.-]{1,60}\.ms$ (the stored Max script; the download adds _v<n>).')


class BuildProject(ProjectNaming):
    """BuildSettings.project: ProjectNaming & { name, shortName, projectNo, exportedFrom }."""
    name: str
    short_name: str
    project_no: str | None
    exported_from: str | None = Field(description='e.g. "Revit"; null when unknown. Only ever quoted in texts.')


class SourceSetting(StrictModel):
    sha1: Sha1
    name: str = Field(description="The uploaded file's own name (untrusted; goes into model.source as it is).")
    kind: SourceKind
    units: Units | None = Field(description="The reader's used units, confirmed or changed by staff (U-7.4); null only "
                                            'in revision-0 settings, before the proposal is adopted (U-3.3).')
    units_confirmed: bool = Field(description="false while the reader's verdict was 'votes-win' or 'unknown' and staff "
                                              'have not confirmed: runBuild refuses.')


class FloorAreaWholeFile(StrictModel):
    kind: Literal['wholeFile']


class FloorAreaBox(StrictModel):
    kind: Literal['box']
    bbox: Bbox = Field(description='Sheet metres.')
    pad: float
    match: Literal['all', 'any'] = Field(description="'all': every point of an item inside bbox +- pad; 'any': one "
                                                     'point is enough (U-9.1).')


FloorArea = Annotated[FloorAreaWholeFile | FloorAreaBox, Field(discriminator='kind')]


class FloorAlignAuto(StrictModel):
    method: Literal['auto', 'grid', 'origin'] = Field(description='auto: grid when at least two grid lines are shared '
                                                                  'with floor 0, else origin (U-9.4).')


class FloorAlignPoints(StrictModel):
    method: Literal['points']
    pairs: tuple[tuple[Vec2, Vec2], tuple[Vec2, Vec2]] = Field(
        description="pairs[i] = [a point on floor 0's sheet, the same point on this floor's sheet] (sheet m).")


FloorAlign = Annotated[FloorAlignAuto | FloorAlignPoints, Field(discriminator='method')]


class FloorSetup(StrictModel):
    key: FloorKey
    name: str
    source: Sha1 = Field(description='sha1 of one of settings.sources.')
    area: FloorArea
    level: float = Field(description='m above the datum; floors are listed lowest first, levels strictly increasing.')
    wall_height: float = Field(description='m, > 0.')
    slab_thickness: float | None = Field(description='null: defaults.slabThickness (a plinth floor ignores it).')
    door_head: float | None = Field(description="null: the project defaults. Order per door: its own name, then this, "
                                                "then the drawing's most common named height, then defaults.doorHead.")
    window_sill: float | None
    window_head: float | None
    align: FloorAlign = Field(description='Ignored on floors[0] (the reference).')
    ceiling_height: float | None = Field(default=None, description='m above the level, 0.5 - 20; null: the default '
                                                                   "rule (rooms R-5.1). Read only with ceilings 'auto'.")


class BuildDefaults(StrictModel):
    door_head: float
    window_sill: float
    window_head: float
    railing_height: float
    slab_thickness: float
    single_line_height: float


class FurnitureSettings(StrictModel):
    heights: dict[str, float] = Field(description="kind -> mm, only kinds this project wants different from "
                                                  "furniture_kit.py's office defaults.")
    bases: dict[str, float]
    words: dict[str, list[str]] = Field(description="kind -> extra words (block / family names) that win over the kit's "
                                                    'vocabulary.')
    skip: list[str]
    min_size: float = Field(description='m: a piece whose long side is shorter is left out (bank 0.08).')
    min_depth: float | None = Field(description='m or null (house 0.25).')
    loose_layers: list[str] = Field(description='Layers whose loose lines become boxes (suite); empty: the furniture '
                                                'layers themselves (bank rule).')
    piece_layer: Literal['insert', 'drawn'] = Field(description="'insert' (default, the bank) or 'drawn' (the suite), "
                                                                'U-10.5.')


class Vocabulary(TypedDict, total=False):
    """Regular expressions (Python `re`, case-insensitive) as strings; a missing key = the builder's default (the bank
    builder's own pattern, U-10.3)."""
    __pydantic_config__ = ConfigDict(extra='forbid')  # type: ignore[misc]
    stairUp: str
    stairDown: str
    glassWord: str
    liftWord: str
    roomTagLine: str
    sizeInName: str
    typeHeight: str


class BuilderOptions(StrictModel):
    revit_wall_types: Literal['auto', 'off']
    parapets: Literal['auto', 'off']
    object_closures: bool
    lift_shafts: bool
    plinth: Literal['auto', 'off']
    outline_walls: Literal['off', 'suggest']
    offset: Literal['auto'] | Vec2 = Field(description='auto: the bank rule (centre of all slabs, 3 decimals), unless '
                                                       'project-settings.json pins one (U-9.6).')
    slabs: Literal['closed-rooms', 'network'] = Field(
        default='closed-rooms', description="Rooms milestone (R-1.2); a missing key is the old rule. 'network': floor "
                                            'plates from the wall network, with rooms, names, holes, flags and fixes.')
    ceilings: Literal['off', 'auto'] = Field(default='off', description="'auto': ceilings (R-5); needs slabs 'network'.")
    stairs: Literal['lines', 'climb'] = Field(default='lines', description="'climb': stairs you can climb (R-7, R-8); "
                                                                           "needs slabs 'network'.")


class ItemRef(StrictModel):
    floor: FloorKey
    source: Sha1
    key: str = Field(description='Nested handle key, e.g. "BA/2C4/1F3"; an INSERT key covers its whole subtree.')
    sig: str = Field(description="12 hex: the item's geometry signature.")
    rsig: str = Field(description="12 hex, or '' when elementId is null.")
    element_id: str | None
    layer: str


class SetAside(ItemRef):
    note: str
    floor_past: bool = Field(default=False, description='Rooms milestone (R-2.1 point 7): true = the floor runs past '
                                                        'the line. Default: a set-aside line still bounds the floor.')


class OpeningFix(StrictModel):
    floor: FloorKey
    a: Vec2
    b: Vec2
    kind: Literal['door', 'window', 'passage', 'none'] | None = Field(description="null: keep the detector's; 'none': "
                                                                                 'not an opening (nothing cut).')
    head: float | None
    sill: float | None


class OutlineEdgeFix(StrictModel):
    floor: FloorKey
    a: Vec2
    b: Vec2
    as_: Literal['wall', 'glass', 'none'] = Field(alias='as')


class ClosingFix(StrictModel):
    """Rooms milestone (R-6.2), sheet m. 'line': a closing line staff drew; 'none': leave out the app's bridge or
    doorway closing whose two ends lie within 0.3 m of a and b."""
    floor: FloorKey
    a: Vec2
    b: Vec2
    use: Literal['line', 'none']


class RoomFix(StrictModel):
    """Rooms milestone (R-6.2): the room, or the unfloored area, that contains `at` (sheet m)."""
    floor: FloorKey
    at: Vec2
    name: str | None = Field(description='At most 200 characters, text only; null: no name given.')
    slab: Literal['auto', 'none', 'floor'] = Field(description="'none': no floor here (or: it is outdoors); 'floor': "
                                                               'floor here.')
    ceiling: Literal['auto', 'none']


class StairFix(StrictModel):
    """Rooms milestone (R-6.2, R-7.6): the stair whose outline contains `at` (sheet m)."""
    floor: FloorKey
    at: Vec2
    bottom: Vec2 | None = Field(description='A point on the bottom tread (it decides the direction), or null.')
    use: Literal['auto', 'lines', 'climb'] = Field(description="'lines': keep it as lines; 'climb': build it although "
                                                               'its riser is outside 0.14 - 0.21 m (up to 0.25 m).')


class Fixes(StrictModel):
    set_aside: list[SetAside]
    openings: list[OpeningFix]
    outline_edges: list[OutlineEdgeFix]
    closings: list[ClosingFix] = Field(default_factory=list, description='Rooms milestone; a missing key is no fix. The '
                                                                         'cap of 5,000 other fixes counts these too.')
    rooms: list[RoomFix] = Field(default_factory=list)
    stairs: list[StairFix] = Field(default_factory=list)


class BuildSettings(StrictModel):
    """The build's whole recipe (builds/<id>/settings.json; versions/<n>/project-data.json)."""
    format: Literal['build-settings/1']
    office: str | None = Field(description='Office id (^[a-z0-9][a-z0-9-]{1,62}$), or null.')
    project: BuildProject
    sources: list[SourceSetting]
    layers: dict[str, LayerRole] = Field(description="Exact layer name -> role; a layer not listed is 'other'.")
    floors: list[FloorSetup]
    defaults: BuildDefaults
    furniture: FurnitureSettings
    vocabulary: Vocabulary
    options: BuilderOptions
    fixes: Fixes


# ===================================================================== 2. store records the worker reads (not in routes)
class OfficeLayer(StrictModel):
    role: LayerRole
    names: list[str]
    uses: int
    last_project: str
    last_used_at: str
    was: LayerRole | None


class OfficeMapping(StrictModel):
    format: Literal['office-mapping/1']
    id: str
    name: str
    created_at: str
    updated_at: str
    layers: dict[str, OfficeLayer]
    furniture_words: dict[str, list[str]]


class ConverterInfo(StrictModel):
    name: Literal['libredwg']
    version: str
    exe_sha1: Sha1


class VersionInputSource(StrictModel):
    sha1: Sha1
    name: str
    bytes: int
    kind: SourceKind
    units: Units
    verdict: ConversionVerdict
    dxf_sha1: Sha1 | None


class BuilderInfo(StrictModel):
    version: str
    python: str
    packages: dict[str, str]
    vendor: dict[str, str]


class VersionInputs(StrictModel):
    format: Literal['version-inputs/1']
    build_id: str
    run_id: str
    settings_revision: int
    built_at: str
    sources: list[VersionInputSource]
    converter: ConverterInfo | None
    builder: BuilderInfo
    seconds: dict[str, float]


# =================================================================================================== 3. worker files
class JobSpecSource(StrictModel):
    sha1: Sha1
    name: str
    kind: SourceKind
    path: str
    units: Units | None


class JobSpecPaths(StrictModel):
    out: str
    cache: str
    libredwg: str
    previous_run: str | None
    version_model: str | None


class Limit(StrictModel):
    seconds: float
    memory_mb: int = Field(alias='memoryMB')


class JobSpecLimits(StrictModel):
    convert: Limit
    check: Limit
    read: Limit
    build: Limit


class JobSpec(StrictModel):
    format: Literal['job-spec/1']
    kind: RunKind
    run_id: str
    build_id: str
    project_id: str
    settings: BuildSettings
    settings_revision: int
    sources: list[JobSpecSource]
    only: list[Sha1] | None
    office: OfficeMapping | None
    paths: JobSpecPaths
    limits: JobSpecLimits
    wall_clock_seconds: float


class LaunchRecord(StrictModel):
    format: Literal['launch/1']
    pid: int
    proc_start: str
    launched_at: str


class RunApiRecord(StrictModel):
    format: Literal['run-api/1']
    validated: bool | None
    issues: list[str]
    adopted_revision: int | None
    at: str


class JobStep(StrictModel):
    name: str
    label: str
    status: StepStatus
    seconds: float | None
    note: str


class JobMessage(StrictModel):
    at: str
    level: LevelLevel
    text: str


class JobError(StrictModel):
    code: RunErrorCode
    message: str
    step: str | None


class JobOutput(StrictModel):
    bytes: int
    sha1: Sha1


class JobRecord(StrictModel):
    format: Literal['job/1']
    kind: RunKind
    run_id: str
    status: RunStatus
    pid: int | None
    proc_start: str | None
    queued_at: str
    started_at: str | None
    finished_at: str | None
    step: str | None
    progress: float
    steps: list[JobStep]
    messages: list[JobMessage]
    error: JobError | None
    outputs: dict[str, JobOutput]


# ================================================================================================ 4. raw worker files
class ConversionSource(StrictModel):
    sha1: Sha1
    name: str
    bytes: int
    kind: SourceKind
    format_version: str | None


class ConversionDxf(StrictModel):
    sha1: Sha1
    bytes: int
    acad_version: str | None
    ins_units: int | None
    audit_errors: int
    audit_fixes: int


class ConversionMessage(StrictModel):
    class_: str = Field(alias='class')
    count: int
    example: str


class ConversionTotals(StrictModel):
    dwg_entities: int | None
    dxf_entities: int | None
    missing: int
    extra: int
    layer_changed: int
    empty_layer: int


class LayerCount(StrictModel):
    layer: str
    dwg: int
    dxf: int


class LostInsert(StrictModel):
    x: float
    y: float
    layer: str


class LostBlock(StrictModel):
    name: str
    entities: int
    by_layer: dict[str, int]
    inserts: list[LostInsert]


class RenamedBlock(StrictModel):
    dwg: str
    dxf: str


class ConversionReport(StrictModel):
    format: Literal['conversion-report/1']
    source: ConversionSource
    converter: ConverterInfo | None
    dxf: ConversionDxf | None
    seconds: float
    peak_memory_mb: float | None = Field(alias='peakMemoryMB')
    exit_code: int | None
    messages: list[ConversionMessage]
    totals: ConversionTotals
    by_layer: list[LayerCount]
    lost_blocks: list[LostBlock]
    renamed_blocks: list[RenamedBlock]
    unknown_objects: int
    verdict: ConversionVerdict
    notes: list[str]


class DrawingSource(StrictModel):
    sha1: Sha1
    name: str


class ReaderInfo(StrictModel):
    version: str
    seconds: float
    peak_memory_mb: float | None = Field(alias='peakMemoryMB')


class DrawingDxf(StrictModel):
    acad_version: str | None
    ins_units: int | None
    audit_errors: int
    audit_fixes: int


class UnitVotes(StrictModel):
    """Record<Units, number>: every unit present."""
    mm: float
    cm: float
    m: float
    in_: float = Field(alias='in')
    ft: float


class DrawingUnits(StrictModel):
    declared: Units | None
    votes: UnitVotes
    dimension_median: float | None
    used: Units
    verdict: Literal['agree', 'votes-win', 'declared-only', 'unknown']
    note: str


class DrawingCounts(StrictModel):
    items: int
    by_type: dict[str, int]
    dimensions: int


class LayerState(StrictModel):
    on: bool
    frozen: bool
    locked: bool
    plot: bool


class FamilyCount(StrictModel):
    family: str
    count: int


class PairCounts(StrictModel):
    glass_like: int
    wall_like: int


class LayerRead(StrictModel):
    name: str
    normalised: str
    state: LayerState
    linetype: str
    colour: int | None
    items: int
    by_type: dict[str, int]
    in_blocks: int
    closed_shapes: int
    solid_hatches: int
    hatch_patterns: dict[str, int]
    length: float
    door_arcs: int
    door_arcs_with_leaf: int
    texts: int
    inserts: int
    top_blocks: list[FamilyCount]
    linetypes: dict[str, int]
    pairs: PairCounts
    extents: Bbox | None


class BlockRead(StrictModel):
    name: str
    family: str
    inserts: int
    by_layer: dict[str, int]
    mirrored: int
    max_depth: int
    attrib_tags: list[str]


class TextRead(StrictModel):
    layer: str
    x: float
    y: float
    height: float | None
    text: str
    kind: Literal['TEXT', 'MTEXT', 'ATTRIB']
    tag: str | None
    block: str | None


class LevelTag(StrictModel):
    x: float
    y: float
    value: float
    text: str
    layer: str
    source: Literal['attrib', 'text']
    label: str | None


class GridLabel(StrictModel):
    text: str
    x: float
    y: float
    layer: str
    block: str | None
    direction: Vec2 | None
    line: tuple[Vec2, Vec2] | None


class AreaProposal(StrictModel):
    id: str
    bbox: Bbox
    items: int
    wall_items: int
    looks: Literal['plan', 'elevation', 'other']


class DrawingRead(StrictModel):
    format: Literal['drawing-read/1']
    source: DrawingSource
    reader: ReaderInfo
    dxf: DrawingDxf
    units: DrawingUnits
    extents: Bbox | None
    counts: DrawingCounts
    layers: list[LayerRead]
    blocks: list[BlockRead]
    texts: list[TextRead]
    level_tags: list[LevelTag]
    grid_labels: list[GridLabel]
    areas: list[AreaProposal]


class PlanItems(StrictModel):
    key: list[str]
    layer: list[int]
    type: list[int]
    first: list[int]
    count: list[int]
    sig: list[str]
    rsig: list[str]
    eid: list[int]

    @model_validator(mode='after')
    def _parallel(self) -> PlanItems:
        n = len(self.key)
        for name in ('layer', 'type', 'first', 'count', 'sig', 'rsig', 'eid'):
            if len(getattr(self, name)) != n:
                raise ValueError(f'items.{name} has {len(getattr(self, name))} entries, items.key {n}')
        return self


class PlanGeometry(StrictModel):
    format: Literal['plan-geometry/1']
    source: Sha1
    units: Units
    origin: Vec2
    quantum: float
    layers: list[str]
    items: PlanItems
    element_ids: list[str]
    pts: list[int]


class LayerSuggestion(StrictModel):
    role: LayerRole
    from_: Literal['office', 'office-similar', 'name', 'contents', 'default'] = Field(alias='from')
    evidence: list[str] = Field(description='Plain sentences (they quote layer and block names: untrusted).')


class LayerSuggestions(StrictModel):
    format: Literal['layer-suggestions/1']
    office: str | None
    layers: dict[str, LayerSuggestion]


class OverlayPart(StrictModel):
    i: int
    kind: PartKind
    label: str | None
    o: list[Vec2]
    h: list[list[Vec2]]


class OverlaySlab(StrictModel):
    o: list[Vec2]
    h: list[list[Vec2]]


class OverlayOpening(StrictModel):
    id: str
    kind: Literal['door', 'window', 'passage']
    a: Vec2
    b: Vec2
    flagged: bool
    fixed: bool


class OverlayFurniture(StrictModel):
    id: str
    kind: str
    x: float
    y: float
    w: float
    d: float
    rot: float


class OverlayRoom(StrictModel):
    name: str
    x: float
    y: float


class OverlaySpace(StrictModel):
    id: str
    name: str
    names: list[str]
    area: float
    o: list[Vec2]
    h: list[list[Vec2]]
    ceiling: bool
    source: Literal['network', 'outline', 'staff']


class OverlayHole(StrictModel):
    what: str
    o: list[Vec2]
    h: list[list[Vec2]]


class OverlayStair(StrictModel):
    id: str
    state: Literal['climb', 'lines']
    why: str | None
    text: str | None
    outline: list[Vec2]
    walk: list[Vec2] | None
    bottom: Vec2 | None
    to: FloorKey | None
    risers: int | None
    riser: float | None


class OverlayClosing(TypedDict, total=False):
    """{ kind, a, b, fix? }: `fix` (the index into fixes.closings of a staff line) is optional and never null."""
    __pydantic_config__ = ConfigDict(extra='forbid')  # type: ignore[misc]
    kind: Required[Literal['staff', 'bridge', 'doorway']]
    a: Required[Vec2]
    b: Required[Vec2]
    fix: int


class OverlayUnfloored(StrictModel):
    area: float
    o: list[Vec2]
    mouth: tuple[Vec2, Vec2] | None
    answered: bool


class OverlayFloor(StrictModel):
    key: FloorKey
    source: Sha1
    to_sheet: Vec2
    area: FloorArea
    parts: list[OverlayPart]
    slabs: list[OverlaySlab]
    openings: list[OverlayOpening]
    furniture: list[OverlayFurniture]
    rooms: list[OverlayRoom]
    set_aside: list[str]
    # The rooms milestone (R-12.4), sheet m: each key optional and never null; absent with the old rule. (A field typed
    # as a list with the default None: a missing key passes, an explicit null does not.)
    spaces: list[OverlaySpace] = None            # type: ignore[assignment]
    holes: list[OverlayHole] = None              # type: ignore[assignment]
    stairs: list[OverlayStair] = None            # type: ignore[assignment]
    closings: list[OverlayClosing] = None        # type: ignore[assignment]
    unfloored: list[OverlayUnfloored] = None     # type: ignore[assignment]


class FlagRef(TypedDict, total=False):
    __pydantic_config__ = ConfigDict(extra='forbid')  # type: ignore[misc]
    openingId: str
    keys: list[str]
    family: str
    fix: int
    edge: tuple[Vec2, Vec2]
    # the rooms milestone: a space id; a stair id; the two ends of a mouth or of a doorway closing (sheet m)
    room: str
    stair: str
    a: Vec2
    b: Vec2


class Flag(StrictModel):
    id: str = Field(description='<kind>:<floor>:<12 hex of what it is about>.')
    kind: FlagKind
    floor: FloorKey | None
    severity: Literal['check', 'info']
    title: str
    detail: str
    at: Vec2 | None
    bbox: Bbox | None
    ref: FlagRef


class BuildOverlay(StrictModel):
    format: Literal['build-overlay/1']
    floors: list[OverlayFloor]
    flags: list[Flag]


class DiffPart(StrictModel):
    floor: FloorKey
    kind: PartKind
    o: list[Vec2]


class DiffOpening(StrictModel):
    floor: FloorKey
    id: str
    kind: str
    a: Vec2
    b: Vec2


class DiffOpeningChange(StrictModel):
    floor: FloorKey
    id: str
    field: str
    before: Any
    after: Any


class DiffBody(StrictModel):
    counts: dict[str, dict[str, tuple[float, float]]]
    parts_added: list[DiffPart]
    parts_removed: list[DiffPart]
    openings_added: list[DiffOpening]
    openings_removed: list[DiffOpening]
    openings_changed: list[DiffOpeningChange]
    furniture_by_kind: dict[str, tuple[float, float]]
    rooms_added: list[str]
    rooms_removed: list[str]


class DiffAgainst(StrictModel):
    kind: Literal['previous-run', 'version']
    ref: str
    diff: DiffBody


class BuildDiff(StrictModel):
    format: Literal['build-diff/1']
    against: list[DiffAgainst]


class FurniturePiece(StrictModel):
    id: str
    floor: FloorKey
    source: Sha1
    key: str | None
    block: str | None
    family: str | None
    element_id: str | None
    ins: Vec2 | None
    rot: float | None
    sx: float | None
    sy: float | None
    insert_mirrored: bool | None
    drawn_variant: Literal['same', 'mirrorX', 'mirrorY', 'turned180'] | None
    box_rot: float


class FurniturePlacements(StrictModel):
    format: Literal['furniture-placements/1']
    pieces: list[FurniturePiece]


class OpeningRecordOut(StrictModel):
    record: dict[str, Any]
    model_id: str | None
    fix: int | None


class OpeningsFile(StrictModel):
    format: Literal['openings/1']
    floors: dict[str, list[OpeningRecordOut]]


# ====================================================================================== 5. API bodies and responses
class NewProjectRequest(ApiModel):
    name: str
    short_name: str | None = None
    project_no: str | None = None
    office: str | None = Field(default=None, description='An existing office id, or null.')
    new_office_name: str | None = Field(default=None, description="A new office's name (creates it); ignored when office "
                                                                  'is given.')
    id: str | None = Field(default=None, description='Wanted id, 2 - 40 characters (Windows path length, U-4.1); derived '
                                                     'from the name when absent (U-13.3).')


class OfficeInfo(ApiModel):
    id: str
    name: str
    layers: int
    updated_at: str


class OfficeList(ApiModel):
    offices: list[OfficeInfo]


class UploadRequest(ApiModel):
    project_id: str
    file_name: str
    bytes: int


class UploadSession(ApiModel):
    id: str = Field(description='^u[0-9a-f]{24}$')
    project_id: str
    file_name: str
    bytes: int
    part_bytes: int
    parts: int
    received: list[int] = Field(description='1-based part numbers received, ascending.')
    expires_at: str
    part_urls: list[str] = Field(description='partUrls[i] is part i + 1.')
    complete_url: str
    url: str


class UploadPartResult(ApiModel):
    part: int
    bytes: int


class SourceFile(ApiModel):
    sha1: Sha1
    name: str
    bytes: int
    kind: SourceKind
    format_version: str | None
    uploaded_at: str


class BuildFromNone(StrictModel):
    kind: Literal['none']


class BuildFromLatest(StrictModel):
    kind: Literal['latest']


class BuildFromVersion(StrictModel):
    kind: Literal['version']
    version: int


class BuildFromBuild(StrictModel):
    kind: Literal['build']
    build: str


BuildFrom = Annotated[BuildFromNone | BuildFromLatest | BuildFromVersion | BuildFromBuild, Field(discriminator='kind')]


class NewBuildRequest(ApiModel):
    sources: list[Sha1] | None = Field(description='null: the sources of the version or build named by `from` (a '
                                                   'rebuild of the same files).')
    from_: BuildFrom | None = Field(default=None, alias='from',
                                    description='Where the starting settings come from; default: the latest version '
                                                '(when it has project-data.json), else none.')


class RunStepInfo(ApiModel):
    name: str
    label: str
    status: StepStatus
    seconds: float | None
    note: str


class RunMessage(ApiModel):
    at: str
    level: LevelLevel
    text: str


class RunError(ApiModel):
    code: str
    message: str
    step: str | None


class RunInfo(ApiModel):
    id: str
    kind: RunKind
    status: RunStatus
    step: str | None
    progress: float
    steps: list[RunStepInfo]
    messages: list[RunMessage] = Field(description='The last 50.')
    error: RunError | None
    queued_at: str
    started_at: str | None
    finished_at: str | None
    cancel_requested: bool = Field(description='Cancel was asked and the run has not stopped yet: the UI shows '
                                               '"Stopping..." (U-3.4).')
    only: list[Sha1] | None = Field(description='prepare only: the sources it reads (null: all).')


class BuildSourceConversion(ApiModel):
    verdict: ConversionVerdict
    notes: list[str]
    lost_in_model_space: int


class BuildSourceUnits(ApiModel):
    declared: Units | None
    used: Units
    verdict: str
    note: str


class BuildSourceUrls(ApiModel):
    conversion: str
    drawing: str
    plan: str


class BuildSourceInfo(ApiModel):
    sha1: Sha1
    name: str
    bytes: int
    kind: SourceKind
    conversion: BuildSourceConversion | None = Field(description='null until the prepare run has read it.')
    units: BuildSourceUnits | None
    urls: BuildSourceUrls | None


class OpeningCounts(ApiModel):
    door: int
    window: int
    passage: int


class BuildFloorResult(ApiModel):
    key: FloorKey
    name: str
    level: float
    parts: int
    openings: OpeningCounts
    furniture: int
    rooms: int


class BuildFlagCounts(ApiModel):
    total: int
    check: int
    by_kind: dict[str, int]


class BuildResultUrls(ApiModel):
    model: str
    stages: str
    overlay: str
    diff: str
    topview: str
    max_script: str


class BuildResultInfo(ApiModel):
    run_id: str
    finished_at: str
    stale: bool = Field(description='The settings changed since this run: Save is refused until it runs again.')
    settings_revision: int
    counts: VersionCounts
    floors: list[BuildFloorResult]
    flags: BuildFlagCounts
    stamp: str
    presentation: dict[str, Any]
    urls: BuildResultUrls
    seconds: dict[str, float]


class BuildSummary(ApiModel):
    id: str = Field(description='^[0-9]{8}T[0-9]{6}-[0-9a-f]{6}$')
    project_id: str
    created_at: str
    updated_at: str
    status: Literal['open', 'saved']
    saved_version: int | None
    source_names: list[str]
    run_status: RunStatus | None
    url: str


class BuildList(ApiModel):
    builds: list[BuildSummary] = Field(description='Newest first.')


class BuildUrls(ApiModel):
    settings: str
    run: str
    cancel: str
    save: str


class BuildDetail(BuildSummary):
    sources: list[BuildSourceInfo]
    settings: BuildSettings | None = Field(description='null only when asked with withSettings=false (the 1 s poll).')
    settings_revision: int
    layers_reviewed_at: str | None = Field(description='BuildRecord.layersReviewedAt.')
    suggestions: dict[str, LayerSuggestion] = Field(description='Empty until the prepare run is done.')
    run: RunInfo | None = Field(description='The run going now, else the last one.')
    result: BuildResultInfo | None = Field(description='The last finished build run, or null.')
    urls: BuildUrls


class BuildSettingsUpdate(ApiModel):
    settings: BuildSettings
    layers_reviewed: bool | None = Field(default=None, description="true from the Layers step's saves: sets "
                                                                   'BuildRecord.layersReviewedAt once (U-8.3).')


class RunBuildRequest(StrictModel):
    """An empty JSON object: a state change is never a simple cross-site request (U-5.2)."""


class CancelBuildRequest(StrictModel):
    """An empty JSON object (U-5.2)."""


class CompleteUploadRequest(StrictModel):
    """An empty JSON object (U-5.2)."""


class SaveBuildRequest(ApiModel):
    label: str = Field(description='1 - 200 characters.')
    carry_heights: bool = Field(description="Copy the latest version's saved furniture heights for the kinds that still "
                                            'exist (the web app sends true by default).')
    remember_mapping: bool = Field(description="Remember the layer roles for the build's office (the web app sends true "
                                               'by default).')


#: The raw files' record models by check_file kind (U-13.2).
RECORDS: dict[str, type[ApiModel]] = {
    'settings': BuildSettings,
    'drawing': DrawingRead,
    'plan': PlanGeometry,
    'conversion': ConversionReport,
    'suggestions': LayerSuggestions,
    'overlay': BuildOverlay,
    'diff': BuildDiff,
    'pieces': FurniturePlacements,
    'openings': OpeningsFile,
    'job': JobRecord,
    'spec': JobSpec,
    'launch': LaunchRecord,
    'api': RunApiRecord,
    'office': OfficeMapping,
    'inputs': VersionInputs,
}
