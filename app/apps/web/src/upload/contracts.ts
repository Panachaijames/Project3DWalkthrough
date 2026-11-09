// =====================================================================================================================
// app/docs/upload/upload-contracts.ts -- TypeScript DECLARATIONS ONLY for the "upload a DWG and build it" milestone
// (app/docs/upload/DESIGN.md, cited U-n). Additive: nothing in app/docs/contracts.ts changes.
//
// The scaffold copies this file verbatim to app/apps/web/src/upload/contracts.ts (a test compares the two). The API's
// pydantic models (services/api/walkthrough_api/models_upload.py) and the builder's JSON writers
// (services/builder/walkthrough_builder) follow it field for field: camelCase JSON, the same optionality. Where this file
// and DESIGN.md disagree, this file wins for shapes and DESIGN.md for behaviour (U-18.0).
//
// Sections: 1 roles, units, settings (BuildSettings = versions/<n>/project-data.json) . 2 store records . 3 worker files
//           (job spec, launch record, the API's run record, job status) . 4 raw files the worker writes and the web app
//           reads (conversion report, drawing read,
//           plan geometry, suggestions, overlay, flags, diff, placements, openings) . 5 API bodies and responses (the
//           generated client is the web app's source for these; listed here so every builder sees one shape)
// Units: metres. "Sheet" coordinates = the drawing's own coordinates in metres (DXF units x the unit factor), per source.
// Drawing text (layer, block, family, file, room and floor names, evidence strings, flag texts) is UNTRUSTED: DOM text
// only (React text nodes, textContent, canvas fillText), never HTML.
// =====================================================================================================================

import type { FloorKey, PartKind, Vec2, VersionCounts } from '@walkthrough/viewer';

/** [x0, y0, x1, y1], x0 <= x1, y0 <= y1. */
export type Bbox = [number, number, number, number];
/** 40 hex, lower case. */
export type Sha1 = string;

// =====================================================================================================================
// 1. Roles, units and the build settings
// =====================================================================================================================

/** The layer-mapping screen's roles (U-8.1). Derived builder and detector roles: U-8.2. */
export type LayerRole =
  | 'wall' | 'column' | 'glass' | 'window' | 'door' | 'screen' | 'stair' | 'stair-above' | 'railing'
  | 'furniture' | 'room-name' | 'room-outline' | 'level' | 'grid' | 'light' | 'other' | 'ignore';

export type Units = 'mm' | 'cm' | 'm' | 'in' | 'ft';

export interface ProjectNaming {
  /** ^[A-Za-z0-9_.-]{1,64}$ (BuiltModel photoName). */
  photoName: string;
  /** ^[A-Z]{2,4}$ (BuiltModel maxPrefix). */
  maxPrefix: string;
  /** ^[A-Za-z0-9_.-]{1,60}\.ms$ (the stored Max script; the download adds _v<n>). */
  maxFileName: string;
}

export interface SourceSetting {
  sha1: Sha1;
  /** The uploaded file's own name (untrusted; goes into model.source as it is). */
  name: string;
  kind: 'dwg' | 'dxf';
  /** Starts as the reader's `used` units (U-7.4); staff confirm or change them on the Files step (a change rescales this
   *  source's boxes and points and re-reads it, U-7.4). null only in revision-0 settings, before the prepare's proposal is
   *  adopted (U-3.3); every later revision has a value. */
  units: Units | null;
  /** false while the reader's verdict was 'votes-win' or 'unknown' and staff have not confirmed: runBuild refuses. */
  unitsConfirmed: boolean;
}

export type FloorArea =
  | { kind: 'wholeFile' }
  /** Sheet metres. match 'all': every point of an item inside bbox +- pad; 'any': one point is enough (U-9.1). */
  | { kind: 'box'; bbox: Bbox; pad: number; match: 'all' | 'any' };

export type FloorAlign =
  /** auto: grid when at least two grid lines are shared with floor 0, else origin (U-9.4). */
  | { method: 'auto' | 'grid' | 'origin' }
  /** pairs[i] = [a point on floor 0's sheet, the same point on this floor's sheet] (sheet m). */
  | { method: 'points'; pairs: [[Vec2, Vec2], [Vec2, Vec2]] };

export interface FloorSetup {
  /** ^[A-Za-z0-9_]{1,32}$, unique. */
  key: FloorKey;
  name: string;
  /** sha1 of one of settings.sources. */
  source: Sha1;
  area: FloorArea;
  /** m above the datum; floors are listed lowest first, levels strictly increasing. */
  level: number;
  /** m, > 0. */
  wallHeight: number;
  /** null: defaults.slabThickness (a plinth floor ignores it: its slab reaches the ground, U-9.5). */
  slabThickness: number | null;
  /** null: the project defaults. Order per door: its own name, then this, then the drawing's most common named height,
   *  then defaults.doorHead (U-10.4). */
  doorHead: number | null;
  windowSill: number | null;
  windowHead: number | null;
  /** Ignored on floors[0] (the reference). */
  align: FloorAlign;
}

export interface BuildDefaults {
  doorHead: number;          // 2.1
  windowSill: number;        // 0.9
  windowHead: number;        // 2.1
  railingHeight: number;     // 1.1
  slabThickness: number;     // 0.25
  singleLineHeight: number;  // 1.0
}

export interface FurnitureSettings {
  /** kind -> mm, only kinds this project wants different from furniture_kit.py's office defaults. */
  heights: Record<string, number>;
  bases: Record<string, number>;
  /** kind -> extra words (block / family names) that win over the kit's vocabulary. */
  words: Record<string, string[]>;
  skip: string[];
  /** m: a piece whose long side is shorter is left out (bank 0.08). */
  minSize: number;
  /** m or null (house 0.25). */
  minDepth: number | null;
  /** Layers whose loose lines become boxes (suite); empty: the furniture layers themselves (bank rule). */
  looseLayers: string[];
  /** 'insert' (default, the bank): a piece is an INSERT on a furniture layer and keeps that layer. 'drawn' (the suite):
   *  also an INSERT whose own layer has no furniture role but whose drawing is mostly on furniture layers, taking that
   *  majority layer; never a block that holds furniture inserts (U-10.5). */
  pieceLayer: 'insert' | 'drawn';
}

/** Regular expressions (Python `re` syntax, case-insensitive) as strings; a missing key = the builder's default, which is
 *  the bank builder's own pattern (U-10.3). Not shown on any screen in this milestone. */
export interface Vocabulary {
  stairUp?: string;
  stairDown?: string;
  glassWord?: string;
  liftWord?: string;
  roomTagLine?: string;
  sizeInName?: string;
  typeHeight?: string;
}

export interface BuilderOptions {
  /** Revit glass wall types on the wall layers become glass panes of the type's height (bank). */
  revitWallTypes: 'auto' | 'off';
  /** auto: the parapet rule runs only on floors whose wall layers carry solid fills (U-10.5). */
  parapets: 'auto' | 'off';
  objectClosures: boolean;
  liftShafts: boolean;
  /** auto: a lowest floor above level 0 stands on a plinth slab down to the ground. */
  plinth: 'auto' | 'off';
  /** suggest: free edges of room-outline layers become flagged suggestions (U-10.5); nothing is built until accepted. */
  outlineWalls: 'off' | 'suggest';
  /** auto: the bank rule (centre of all slabs, 3 decimals), unless project-settings.json pins one (U-9.6). */
  offset: 'auto' | Vec2;
}

/** A drawing item, as staff picked it on the plan (U-7.2 for the key and signatures, U-10.6 for matching). Every field is
 *  copied from the plan geometry's entry for the key (PlanGeometry.items: sig, rsig, eid), never derived in the browser. */
export interface ItemRef {
  floor: FloorKey;
  source: Sha1;
  /** Nested handle key, e.g. "BA/2C4/1F3". The key of an INSERT (an anchor, type 5) covers the INSERT and every item whose
   *  key starts with key + '/'. */
  key: string;
  /** 12 hex: the item's geometry signature (type, layer, points rounded to 1 mm, sheet m). */
  sig: string;
  /** 12 hex, or '' when elementId is null: the same hash with the points relative to the element's INSERT (minus its
   *  insertion point, turned back by its world turn). */
  rsig: string;
  /** Revit element id from the innermost block name that carries one, else null. Never matched alone (U-10.6). */
  elementId: string | null;
  layer: string;
}

export interface SetAside extends ItemRef { note: string }

/** Matched to a detected opening by geometry (U-10.6); a and b in sheet m as detected. */
export interface OpeningFix {
  floor: FloorKey;
  a: Vec2;
  b: Vec2;
  /** null: keep the detector's; 'none': not an opening (nothing cut). */
  kind: 'door' | 'window' | 'passage' | 'none' | null;
  head: number | null;
  sill: number | null;
}

/** An outline suggestion staff accepted or refused (sheet m). */
export interface OutlineEdgeFix { floor: FloorKey; a: Vec2; b: Vec2; as: 'wall' | 'glass' | 'none' }

export interface Fixes {
  setAside: SetAside[];
  openings: OpeningFix[];
  outlineEdges: OutlineEdgeFix[];
}

/** The build's whole recipe. Stored as builds/<id>/settings.json (inside BuildSettingsFile) while a draft is open and as
 *  versions/<n>/project-data.json when the version is saved; the next build of the project starts from it (U-4.1). */
export interface BuildSettings {
  format: 'build-settings/1';
  /** Office id (^[a-z0-9][a-z0-9-]{1,62}$) whose layer memory is read and, at save, updated; null: none. */
  office: string | null;
  project: ProjectNaming & {
    name: string;
    shortName: string;
    projectNo: string | null;
    /** e.g. "Revit"; null when unknown. Only ever quoted in texts. */
    exportedFrom: string | null;
  };
  sources: SourceSetting[];
  /** Exact layer name (as in the drawing) -> role. A layer of a source that is not listed is 'other'. */
  layers: Record<string, LayerRole>;
  floors: FloorSetup[];
  defaults: BuildDefaults;
  furniture: FurnitureSettings;
  vocabulary: Vocabulary;
  options: BuilderOptions;
  fixes: Fixes;
}

// =====================================================================================================================
// 2. Store records (app/data; U-4.1). JSON UTF-8 without BOM, indent 2 + "\n", written atomically.
// =====================================================================================================================

/** projects/<id>/project-settings.json */
export interface ProjectSettingsFile {
  format: 'walkthrough-project-settings/1';
  office: string | null;
  naming: ProjectNaming;
  /** Pinned model offset (sheet m of floor 0) once a version was saved from an upload; null until then. */
  offset: Vec2 | null;
  updatedAt: string;
}

/** projects/<id>/sources/<sha1>/source.json */
export interface SourceRecord {
  format: 'walkthrough-source/1';
  sha1: Sha1;
  name: string;
  bytes: number;
  kind: 'dwg' | 'dxf';
  /** DWG: the version string of its first 6 bytes (AC1032 ...); DXF: $ACADVER when found, else null. */
  formatVersion: string | null;
  uploadedAt: string;
  /** The stored file's name inside the folder. */
  file: 'original.dwg' | 'original.dxf';
}

/** data/.uploads/<uploadId>/session.json */
export interface UploadSessionFile {
  format: 'walkthrough-upload/1';
  /** ^u[0-9a-f]{24}$ */
  id: string;
  projectId: string;
  fileName: string;
  bytes: number;
  partBytes: number;
  parts: number;
  /** 1-based part numbers received, ascending. */
  received: number[];
  createdAt: string;
  expiresAt: string;
}

/** projects/<id>/builds/<buildId>/build.json (buildId ^[0-9]{8}T[0-9]{6}-[0-9a-f]{6}$). Written by the API only. */
export interface BuildRecord {
  format: 'walkthrough-build/1';
  id: string;
  projectId: string;
  createdAt: string;
  updatedAt: string;
  status: 'open' | 'saved';
  /** sha1s, in upload order. */
  sources: Sha1[];
  /** Where the starting settings came from. */
  from: { kind: 'none' } | { kind: 'version'; version: number } | { kind: 'build'; build: string };
  savedVersion: number | null;
  /** When staff first saved from the Layers step (BuildSettingsUpdate.layersReviewed); runBuild answers 409
   *  layers_not_reviewed while null. A build started from a reviewed build or a version starts with it set (U-8.3). */
  layersReviewedAt: string | null;
}

/** projects/<id>/builds/<buildId>/settings.json. Written by the API only (PUT with If-Match on revision). */
export interface BuildSettingsFile {
  format: 'walkthrough-build-settings/1';
  /** 0 until the prepare run's proposal is adopted (U-3.3); +1 per save. */
  revision: number;
  updatedAt: string;
  settings: BuildSettings;
}

/** data/mappings/<officeId>.json: what an office's layers are (U-8.4). */
export interface OfficeMapping {
  format: 'office-mapping/1';
  id: string;
  name: string;
  createdAt: string;
  updatedAt: string;
  /** Key: the normalised layer name (U-8.4). */
  layers: Record<string, {
    role: LayerRole;
    /** Exact names seen with this normalised name (at most 10). */
    names: string[];
    uses: number;
    lastProject: string;
    lastUsedAt: string;
    /** The role it had before the last change, if it ever changed. */
    was: LayerRole | null;
  }>;
  /** Furniture words staff chose to remember for the office (kind -> words). */
  furnitureWords: Record<string, string[]>;
}

/** versions/<n>/source/inputs.json: what a version was built from (provenance; never served). */
export interface VersionInputs {
  format: 'version-inputs/1';
  buildId: string;
  runId: string;
  settingsRevision: number;
  builtAt: string;
  sources: { sha1: Sha1; name: string; bytes: number; kind: 'dwg' | 'dxf'; units: Units; verdict: ConversionVerdict; dxfSha1: Sha1 | null }[];
  converter: { name: 'libredwg'; version: string; exeSha1: Sha1 } | null;
  builder: { version: string; python: string; packages: Record<string, string>; vendor: Record<string, Sha1> };
  seconds: Record<string, number>;
}

// =====================================================================================================================
// 3. Worker files: builds/<buildId>/runs/<runId>/ (runId ^[0-9]{4}-(prepare|build)$; U-3)
// =====================================================================================================================

export type RunKind = 'prepare' | 'build';
export type RunStatus = 'queued' | 'running' | 'done' | 'failed' | 'cancelled' | 'interrupted';

/** spec.json: written once by the API before it starts the worker; the worker only reads it. */
export interface JobSpec {
  format: 'job-spec/1';
  kind: RunKind;
  runId: string;
  buildId: string;
  projectId: string;
  /** The settings snapshot the run uses (a later PUT does not change a running build). */
  settings: BuildSettings;
  settingsRevision: number;
  /** Absolute paths of the stored originals. */
  sources: { sha1: Sha1; name: string; kind: 'dwg' | 'dxf'; path: string; units: Units | null }[];
  /** prepare only: the sources to (re-)read after a units change (U-3.1, U-7.4); null: every source, then `suggest`. */
  only: Sha1[] | null;
  /** The office's memory at the time (prepare only; null otherwise). */
  office: OfficeMapping | null;
  /** Absolute paths. */
  paths: { out: string; cache: string; libredwg: string; previousRun: string | null; versionModel: string | null };
  limits: Record<'convert' | 'check' | 'read' | 'build', { seconds: number; memoryMB: number }>;
  /** Whole run, queue time included (U-3.4): the worker stops itself past it. */
  wallClockSeconds: number;
}

/** launch.json: written by the API right after it started the worker (U-3.4). */
export interface LaunchRecord {
  format: 'launch/1';
  pid: number;
  /** Same definition as JobRecord.procStart. */
  procStart: string;
  launchedAt: string;
}

/** api.json: the API's own record of what it did with a finished run (U-3.2), written under the per-build lock. */
export interface RunApiRecord {
  format: 'run-api/1';
  /** null: not yet checked; true: the outputs passed; false: the run was marked invalid_output. */
  validated: boolean | null;
  issues: string[];
  /** The settings revision this prepare's proposal became (U-3.3), or null. */
  adoptedRevision: number | null;
  at: string;
}

/** job.json: written only by the worker (atomically with retries on sharing violations, after every status or step
 *  change; progress at most twice a second), except that the API marks a run 'interrupted' when its worker is gone, or
 *  'cancelled' after it had to kill it and the pid has exited (U-3.4). After writing 'cancelled' the worker writes
 *  nothing more. */
export interface JobRecord {
  format: 'job/1';
  kind: RunKind;
  runId: string;
  status: RunStatus;
  pid: number | null;
  /** The worker's process creation time: the raw FILETIME from GetProcessTimes (100 ns ticks since 1601-01-01 UTC) as a
   *  decimal string, compared exactly, to tell a reused pid from the worker. */
  procStart: string | null;
  queuedAt: string;
  startedAt: string | null;
  finishedAt: string | null;
  /** The step running now, or the last one. */
  step: string | null;
  /** 0 - 1. */
  progress: number;
  steps: { name: string; label: string; status: 'waiting' | 'running' | 'done' | 'failed' | 'skipped'; seconds: number | null; note: string }[];
  /** The last 200, oldest first. Plain sentences, no server paths. */
  messages: { at: string; level: 'info' | 'warn' | 'error'; text: string }[];
  error: { code: RunErrorCode; message: string; step: string | null } | null;
  /** Output file name (relative to out/) -> size and sha1, written when the run is done. */
  outputs: Record<string, { bytes: number; sha1: Sha1 }>;
}

export type RunErrorCode =
  | 'not_a_drawing' | 'unsupported_version' | 'convert_failed' | 'convert_timeout' | 'convert_memory'
  | 'check_failed' | 'read_failed' | 'read_timeout' | 'read_memory'
  | 'no_floors' | 'bad_settings' | 'area_empty' | 'align_failed'
  | 'detect_failed' | 'build_failed' | 'build_timeout' | 'build_memory' | 'invalid_output'
  | 'cancelled' | 'interrupted' | 'internal';

// =====================================================================================================================
// 4. Raw files the worker writes (run out/ folder) and the API serves as stored (ETag = sha1)
// =====================================================================================================================

export type ConversionVerdict = 'ok' | 'minor' | 'loss' | 'failed' | 'not-converted';

/** out/sources/<sha1>/conversion.json (prepare). U-6.3. */
export interface ConversionReport {
  format: 'conversion-report/1';
  source: { sha1: Sha1; name: string; bytes: number; kind: 'dwg' | 'dxf'; formatVersion: string | null };
  /** null for a DXF upload (verdict 'not-converted'). */
  converter: { name: 'libredwg'; version: string; exeSha1: Sha1 } | null;
  dxf: { sha1: Sha1; bytes: number; acadVersion: string | null; insUnits: number | null; auditErrors: number; auditFixes: number } | null;
  seconds: number;
  peakMemoryMB: number | null;
  exitCode: number | null;
  /** The converter's messages by class (U-6.3), with one example line each (paths removed). */
  messages: { class: string; count: number; example: string }[];
  totals: { dwgEntities: number | null; dxfEntities: number | null; missing: number; extra: number; layerChanged: number; emptyLayer: number };
  /** Only layers whose counts differ. */
  byLayer: { layer: string; dwg: number; dxf: number }[];
  /** Blocks whose definition came out empty or short while the DWG has content. */
  lostBlocks: {
    name: string;
    entities: number;
    byLayer: Record<string, number>;
    /** Model-space inserts of it (sheet m, composed through nested inserts), at most 200. */
    inserts: { x: number; y: number; layer: string }[];
  }[];
  renamedBlocks: { dwg: string; dxf: string }[];
  unknownObjects: number;
  verdict: ConversionVerdict;
  /** Plain sentences for the Files step. */
  notes: string[];
}

/** out/sources/<sha1>/drawing.json (prepare): what the layer-mapping and floors screens show. U-7.3. */
export interface DrawingRead {
  format: 'drawing-read/1';
  source: { sha1: Sha1; name: string };
  reader: { version: string; seconds: number; peakMemoryMB: number | null };
  dxf: { acadVersion: string | null; insUnits: number | null; auditErrors: number; auditFixes: number };
  units: {
    declared: Units | null;
    /** Door votes per unit hypothesis (quarter arcs with a leaf, 0.6 - 1.25 m in that unit). */
    votes: Record<Units, number>;
    /** Median DIMENSION measurement in the declared unit, or null. */
    dimensionMedian: number | null;
    /** What the reader used (declared unless the votes clearly disagree). */
    used: Units;
    verdict: 'agree' | 'votes-win' | 'declared-only' | 'unknown';
    note: string;
  };
  /** Sheet m: the 1 - 99 % box of all item points. */
  extents: Bbox | null;
  counts: { items: number; byType: Record<string, number>; dimensions: number };
  layers: LayerRead[];
  /** By insert count, at most 2000. */
  blocks: BlockRead[];
  /** At most 5000, longest first; text untrusted. */
  texts: TextRead[];
  levelTags: LevelTag[];
  gridLabels: GridLabel[];
  areas: AreaProposal[];
}

export interface LayerRead {
  name: string;
  /** Upper case, xref prefix up to the last '$0$' removed, spaces collapsed (U-8.4). */
  normalised: string;
  state: { on: boolean; frozen: boolean; locked: boolean; plot: boolean };
  linetype: string;
  colour: number | null;
  /** Items on the layer (after unpacking blocks). */
  items: number;
  byType: Record<string, number>;
  inBlocks: number;
  closedShapes: number;
  solidHatches: number;
  hatchPatterns: Record<string, number>;
  /** m of line work. */
  length: number;
  /** Arcs 0.28 - 2 m radius, 20 - 125 deg; and those with a leaf line from the centre. */
  doorArcs: number;
  doorArcsWithLeaf: number;
  texts: number;
  inserts: number;
  /** Most inserted block families on the layer, at most 10. */
  topBlocks: { family: string; count: number }[];
  linetypes: Record<string, number>;
  /** Parallel-line spacing classes: glass-like 0.5 - 7 cm, wall-like 7 - 45 cm (hints only). */
  pairs: { glassLike: number; wallLike: number };
  extents: Bbox | null;
}

export interface BlockRead {
  name: string;
  /** Xref prefix and the Revit "-<element id or V#>-<view>" suffix removed. */
  family: string;
  inserts: number;
  byLayer: Record<string, number>;
  mirrored: number;
  maxDepth: number;
  attribTags: string[];
}

export interface TextRead {
  layer: string;
  x: number;
  y: number;
  height: number | null;
  text: string;
  kind: 'TEXT' | 'MTEXT' | 'ATTRIB';
  tag: string | null;
  block: string | null;
}

export interface LevelTag {
  x: number;
  y: number;
  /** m. */
  value: number;
  text: string;
  layer: string;
  source: 'attrib' | 'text';
  /** The nearest other text within 3 m (e.g. a floor's name in the elevation), or null. */
  label: string | null;
}

export interface GridLabel {
  text: string;
  x: number;
  y: number;
  layer: string;
  block: string | null;
  /** Unit direction of the grid line ending at this bubble, or null when none was found. */
  direction: Vec2 | null;
  /** Sheet m: the grid line itself (two end points), or null. */
  line: [Vec2, Vec2] | null;
}

export interface AreaProposal {
  /** a1, a2 ... in reading order (top-left first). */
  id: string;
  bbox: Bbox;
  items: number;
  /** Items on layers that look like walls (fills or wall-like pairs). */
  wallItems: number;
  /** A guess for the Floors step: plans hold door arcs and wall pairs, elevations level tags and long horizontals. */
  looks: 'plan' | 'elevation' | 'other';
}

/** out/sources/<sha1>/plan.json.gz (prepare): the whole sheet for the canvas (U-7.5). Gzip of the UTF-8 JSON. */
export interface PlanGeometry {
  format: 'plan-geometry/1';
  source: Sha1;
  units: Units;
  /** Sheet m; every coordinate is an integer number of quanta from here. */
  origin: Vec2;
  /** 0.01: centimetres. */
  quantum: number;
  layers: string[];
  /** One entry per polyline (a hatch gives one per loop; a text or an insert one point; every INSERT, at every depth,
   *  one anchor). Parallel arrays. */
  items: {
    key: string[];
    layer: number[];
    /** 0 open line or polyline, 1 closed polyline or circle, 2 solid hatch loop, 3 pattern hatch loop, 4 text anchor,
     *  5 insert anchor. */
    type: number[];
    /** Index of the first point in pts (in points, not numbers). */
    first: number[];
    count: number[];
    /** The item's ItemRef.sig (12 hex), computed by the reader from the cache item (hatch loops repeat their hatch's). */
    sig: string[];
    /** The item's ItemRef.rsig (12 hex, '' without an element id). */
    rsig: string[];
    /** Index into elementIds, -1 for none. */
    eid: number[];
  };
  /** Revit element ids met in this source (U-7.2). */
  elementIds: string[];
  /** x, y, x, y ... integers. Curves flattened at 10 mm, then simplified at 5 mm. */
  pts: number[];
}

/** out/suggestions.json (prepare): one suggestion per layer name across the build's sources (U-8.3). */
export interface LayerSuggestions {
  format: 'layer-suggestions/1';
  office: string | null;
  layers: Record<string, LayerSuggestion>;
}
export interface LayerSuggestion {
  role: LayerRole;
  from: 'office' | 'office-similar' | 'name' | 'contents' | 'default';
  /** Plain sentences (they quote layer and block names: untrusted). */
  evidence: string[];
}

/** out/overlay.json (build): what the check screen draws over each floor's plan, in that floor's sheet coordinates. */
export interface BuildOverlay {
  format: 'build-overlay/1';
  floors: OverlayFloor[];
  flags: Flag[];
}
export interface OverlayFloor {
  key: FloorKey;
  source: Sha1;
  /** sheet = model + toSheet (= model offset + sheetShift). */
  toSheet: Vec2;
  area: FloorArea;
  /** Footprints of the floor's parts (no slabs), sheet m. */
  parts: { i: number; kind: PartKind; label: string | null; o: Vec2[]; h: Vec2[][] }[];
  slabs: { o: Vec2[]; h: Vec2[][] }[];
  openings: { id: string; kind: 'door' | 'window' | 'passage'; a: Vec2; b: Vec2; flagged: boolean; fixed: boolean }[];
  furniture: { id: string; kind: string; x: number; y: number; w: number; d: number; rot: number }[];
  rooms: { name: string; x: number; y: number }[];
  /** Items the build set aside (matched fixes). */
  setAside: string[];
}

export type FlagKind =
  | 'opening' | 'single-line' | 'lost' | 'outline-wall' | 'outline-glass' | 'grey-furniture' | 'rail-left-out'
  | 'room-label' | 'plate-dropped' | 'alignment' | 'units' | 'fix-unmatched' | 'detector-skipped' | 'slow';

export interface Flag {
  /** Stable for the same drawing and settings: <kind>:<floor>:<12 hex of what it is about>. */
  id: string;
  kind: FlagKind;
  floor: FloorKey | null;
  severity: 'check' | 'info';
  /** Untrusted text: may quote drawing names. */
  title: string;
  detail: string;
  /** Sheet m of the flag's floor (null: not a place). */
  at: Vec2 | null;
  bbox: Bbox | null;
  ref: {
    openingId?: string;
    keys?: string[];
    family?: string;
    fix?: number;
    edge?: [Vec2, Vec2];
  };
}

/** out/diff.json (build): this build against the previous build of the draft and against the latest version (U-12.4),
 *  compared in sheet coordinates (model + offset + sheetShift); outlines below are in the floor's sheet metres. */
export interface BuildDiff {
  format: 'build-diff/1';
  against: { kind: 'previous-run' | 'version'; ref: string; diff: DiffBody }[];
}
export interface DiffBody {
  counts: Record<FloorKey, Record<string, [number, number]>>;
  partsAdded: { floor: FloorKey; kind: PartKind; o: Vec2[] }[];
  partsRemoved: { floor: FloorKey; kind: PartKind; o: Vec2[] }[];
  openingsAdded: { floor: FloorKey; id: string; kind: string; a: Vec2; b: Vec2 }[];
  openingsRemoved: { floor: FloorKey; id: string; kind: string; a: Vec2; b: Vec2 }[];
  openingsChanged: { floor: FloorKey; id: string; field: string; before: unknown; after: unknown }[];
  furnitureByKind: Record<string, [number, number]>;
  roomsAdded: string[];
  roomsRemoved: string[];
}

/** out/pieces.json (build) -> versions/<n>/source/pieces.json: each furniture piece's own block placement, kept for
 *  placing real models later (plan 2.5; furniture_test/bank_furnished/analysis.md). Not read by the viewer. */
export interface FurniturePlacements {
  format: 'furniture-placements/1';
  pieces: {
    /** The model's furniture id. */
    id: string;
    floor: FloorKey;
    source: Sha1;
    /** Nested key of the INSERT; null for a piece made of loose lines. */
    key: string | null;
    block: string | null;
    family: string | null;
    elementId: string | null;
    /** Sheet m of the INSERT's insertion point; null for loose lines. */
    ins: Vec2 | null;
    /** The INSERT's world turn (deg) and world scale factors incl. sign. */
    rot: number | null;
    sx: number | null;
    sy: number | null;
    /** sx * sy < 0 on the INSERT itself. Always false in a Revit export: Revit draws a flipped instance into the block
     *  definition, which only drawnVariant shows. null for loose lines. */
    insertMirrored: boolean | null;
    /** The piece's drawing against its family's first piece (U-11.7, a port of block_variants.py): 'same', mirrored in x
     *  or y, or turned 180 degrees. null: loose lines, a family of one, or not computed in this milestone. */
    drawnVariant: 'same' | 'mirrorX' | 'mirrorY' | 'turned180' | null;
    /** The box's own turn in the model (0 - 180). */
    boxRot: number;
  }[];
}

/** out/openings.json (build) -> versions/<n>/source/openings.json: the detector's full records per floor, with the
 *  model's opening id each became (null: refused or fixed to 'none'). */
export interface OpeningsFile {
  format: 'openings/1';
  floors: Record<FloorKey, { record: Record<string, unknown>; modelId: string | null; fix: number | null }[]>;
}

// =====================================================================================================================
// 5. API bodies and responses (models_upload.py; the generated client in apps/web/src/api/generated is the web app's
//    source for these). Every URL is root-relative and comes from the API: the web app never builds an API path.
// =====================================================================================================================

export interface NewProjectRequest {
  name: string;
  shortName?: string | null;
  projectNo?: string | null;
  /** An existing office id, or null. */
  office?: string | null;
  /** A new office's name (creates it); ignored when office is given. */
  newOfficeName?: string | null;
  /** Wanted id, 2 - 40 characters (Windows path length, U-4.1); derived from the name when absent (U-13.3). */
  id?: string | null;
}

export interface OfficeInfo { id: string; name: string; layers: number; updatedAt: string }
export interface OfficeList { offices: OfficeInfo[] }

export interface UploadRequest { projectId: string; fileName: string; bytes: number }
export interface UploadSession {
  id: string;
  projectId: string;
  fileName: string;
  bytes: number;
  partBytes: number;
  parts: number;
  received: number[];
  expiresAt: string;
  /** partUrls[i] is part i + 1. */
  partUrls: string[];
  completeUrl: string;
  url: string;
}
export interface UploadPartResult { part: number; bytes: number }
export interface SourceFile { sha1: Sha1; name: string; bytes: number; kind: 'dwg' | 'dxf'; formatVersion: string | null; uploadedAt: string }

export interface NewBuildRequest {
  /** null: the sources of the version or build named by `from` (a rebuild of the same files). */
  sources: Sha1[] | null;
  /** Where the starting settings come from; default: the latest version (when it has project-data.json), else none. */
  from?: { kind: 'none' } | { kind: 'latest' } | { kind: 'version'; version: number } | { kind: 'build'; build: string } | null;
}

export interface RunStepInfo { name: string; label: string; status: 'waiting' | 'running' | 'done' | 'failed' | 'skipped'; seconds: number | null; note: string }
export interface RunInfo {
  id: string;
  kind: RunKind;
  status: RunStatus;
  step: string | null;
  progress: number;
  steps: RunStepInfo[];
  /** The last 50. */
  messages: { at: string; level: 'info' | 'warn' | 'error'; text: string }[];
  error: { code: string; message: string; step: string | null } | null;
  queuedAt: string;
  startedAt: string | null;
  finishedAt: string | null;
  /** Cancel was asked and the run has not stopped yet: the UI shows "Stopping..." (U-3.4). */
  cancelRequested: boolean;
  /** prepare only: the sources it reads (null: all). */
  only: Sha1[] | null;
}

export interface BuildSourceInfo {
  sha1: Sha1;
  name: string;
  bytes: number;
  kind: 'dwg' | 'dxf';
  /** null until the prepare run has read it. */
  conversion: { verdict: ConversionVerdict; notes: string[]; lostInModelSpace: number } | null;
  units: { declared: Units | null; used: Units; verdict: string; note: string } | null;
  urls: { conversion: string; drawing: string; plan: string } | null;
}

export interface BuildResultInfo {
  runId: string;
  finishedAt: string;
  /** The settings changed since this run: Save is refused until it runs again. */
  stale: boolean;
  settingsRevision: number;
  counts: VersionCounts;
  floors: { key: FloorKey; name: string; level: number; parts: number; openings: Record<'door' | 'window' | 'passage', number>; furniture: number; rooms: number }[];
  flags: { total: number; check: number; byKind: Record<string, number> };
  stamp: string;
  presentation: Record<string, unknown>;
  urls: { model: string; stages: string; overlay: string; diff: string; topview: string; maxScript: string };
  seconds: Record<string, number>;
}

export interface BuildSummary {
  id: string;
  projectId: string;
  createdAt: string;
  updatedAt: string;
  status: 'open' | 'saved';
  savedVersion: number | null;
  sourceNames: string[];
  runStatus: RunStatus | null;
  url: string;
}
export interface BuildList { builds: BuildSummary[] }

export interface BuildDetail extends BuildSummary {
  sources: BuildSourceInfo[];
  /** null only when asked with withSettings=false (the 1 s poll, U-14.2). */
  settings: BuildSettings | null;
  settingsRevision: number;
  /** BuildRecord.layersReviewedAt. */
  layersReviewedAt: string | null;
  /** Empty until the prepare run is done. */
  suggestions: Record<string, LayerSuggestion>;
  /** The run going now, else the last one. */
  run: RunInfo | null;
  /** The last finished build run, or null. */
  result: BuildResultInfo | null;
  urls: { settings: string; run: string; cancel: string; save: string };
}

export interface BuildSettingsUpdate {
  settings: BuildSettings;
  /** true from the Layers step's saves: sets BuildRecord.layersReviewedAt once (U-8.3). */
  layersReviewed?: boolean | null;
}
export interface RunBuildRequest { }
export interface CancelBuildRequest { }
export interface SaveBuildRequest {
  /** 1 - 200 characters. */
  label: string;
  /** Copy the latest version's saved furniture heights for the kinds that still exist (default true). */
  carryHeights: boolean;
  /** Remember the layer roles for the build's office (default true). */
  rememberMapping: boolean;
}
