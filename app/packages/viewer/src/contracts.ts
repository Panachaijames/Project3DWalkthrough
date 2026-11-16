// =====================================================================================================================
// app/docs/contracts.ts -- TypeScript DECLARATIONS ONLY (no runtime code) for the walkthrough foundation milestone.
//
// The scaffold copies this file verbatim to app/packages/viewer/src/contracts.ts; every module of packages/viewer imports
// its types from there and implements the function TYPES declared here (each module exports a const or function whose
// type is the named alias, checked by test/contracts.test-d.ts). Builders never edit contracts.ts: a change needs the
// architect (DESIGN.md section 18) and goes to app/docs/contracts.ts first.
//
// Sections: 1 BuiltModel v1 / v2 . 2 ReplayData v1 . 3 Presentation v1 . 4 store files . 5 viewer public API .
//           6 context and core . 7 UI . 8 modes . 9 furniture . 10 replay . 11 offline payload . 12 test hook
// Units: metres; plan (x, y) maps to three.js (x, z = -y); heights z0 / z1 above the floor level unless said otherwise.
// =====================================================================================================================

import type {
  Box3, Color, Euler, Group, LineSegments, MathUtils, Matrix4, Mesh, Object3D, PerspectiveCamera, Plane, Quaternion,
  Raycaster, Scene, Vector2, Vector3, WebGLRenderer,
} from 'three';
import type { OrbitControls } from 'three/addons/controls/OrbitControls.js';

// =====================================================================================================================
// 1. BuiltModel v1 and v2 (app/docs/built-model.schema.json; DESIGN.md section 5; rooms/DESIGN.md R-12.1)
//    v2 (the rooms milestone, 11 Nov 2026) only adds optional things: every v1 model is a valid v2 model. A model is v2
//    when it has the `stairways` key; version.json then says modelFormat 'built-model/2'.
// =====================================================================================================================

/** ^[A-Za-z0-9_]{1,32}$ (captions name floors as {<key>level}). */
export type FloorKey = string;
export type Vec2 = [number, number];
export type Vec3 = [number, number, number];
/** A closed outline, plan metres, last point not repeated. */
export type Ring = Vec2[];
/** x1, y1, x2, y2, ... (length a multiple of 4). */
export type FlatSegments = number[];

export type PartKind =
  | 'wall' | 'column' | 'lintel' | 'sill' | 'parapet' | 'glass' | 'mullion' | 'railing' | 'single' | 'step' | 'slab' // bank / hotel
  | 'pane'                                                                                                          // house (v1 extension)
  | 'balustrade' | 'low' | 'builtin' | 'deck' | 'post'                                                              // suite (v1 extension)
  | 'tread' | 'landing' | 'ceiling';                                                                                // v2: stairs you climb, ceilings

export interface BuiltFloor {
  key: FloorKey;
  name: string;
  /** Level (m) of the floor's top above the datum. */
  level: number;
  /** Wall height (m above the level). */
  wallHeight: number;
  slabThickness: number;
  /** v1 extension; default 'main'. */
  stack?: string;
  /** v1 extension (house), provenance only, not read by the viewer: sheet coordinates = model + offset + sheetShift. */
  sheetShift?: Vec2;
}

/**
 * How a part answers a wall-height change H0 -> H (DESIGN.md 5.5). Derived: fit ?? (follow ? 'scale' : 'fixed').
 * v2 'storey': the part scales with its stairway's storey, S = (L(to) - L(from)) / (L0(to) - L0(from)), when Build settings
 * change a level (treads, landings and the wall pieces cut under a stair; rooms/DESIGN.md R-9.6).
 */
export type FitMode = 'scale' | 'fixed' | 'top' | 'clip' | 'storey';

export interface Part {
  floor: FloorKey;
  kind: PartKind;
  z0: number;
  z1: number;
  /** Its top follows the wall height. */
  follow: boolean;
  o: Ring;
  h: Ring[];
  label?: string;
  /** v1 extension (house): 'top' = z0 stays, z1 becomes the wall top; 'clip' = kept, cut off at the wall top. v2: 'storey'. */
  fit?: 'top' | 'clip' | 'storey';
  /** v1 extension (house ground plate, slabs only): its foot stays at y = 0 when the level changes. */
  plinth?: boolean;
  /** v2: the id of the stairway the part belongs to (treads, landings, cut wall pieces); it lies on that stairway's `from` floor. */
  stair?: string;
}

export interface StairLines {
  /** Tread lines below the cut: strips lying on the floor. */
  below: FlatSegments;
  /** Flights above the cut: faint lines. */
  above: FlatSegments;
  /** v1 extension (house): tread lines as 0.15 m upright panels. */
  panels?: FlatSegments;
}

export interface VoidMark { what: string; x: number; y: number; area: number; [extra: string]: unknown }
export interface Closure { object: string; width: number; x: number; y: number; [extra: string]: unknown }
export interface StairOutline {
  id?: string; x: number; y: number; bbox: [number, number, number, number]; flights: number; withWord: number;
  [extra: string]: unknown;
}
export interface Room {
  floor: FloorKey; name: string;
  /** Drawing text: inserted with textContent only. */
  label: string;
  area: number | null; x: number; y: number; callout?: boolean;
  /** v2: the id of the space (room) this drawn name belongs to, on the same floor; absent when it belongs to none. */
  space?: string;
  [extra: string]: unknown;
}
/** v2: a stair that can be climbed in Walk (rooms/DESIGN.md R-8.5). Coordinates in the model frame. */
export interface Stairway {
  id: string;
  /** The lower floor (the treads and landings are its parts) and a higher floor of the same stack. */
  from: FloorKey; to: FloorKey;
  /** 'straight', 'L', 'U' ... */
  kind: string;
  risers: number;
  /** Riser height (m) = (level(to) - level(from)) / risers. */
  riser: number;
  going: number;
  width: number;
  /** The first and the last point of `walk`. */
  bottom: Vec2; top: Vec2;
  /** The walking line, bottom to top: at least 2 points. */
  walk: Vec2[];
  /** How the bottom end was found: 'word', 'arrow', 'cut', 'floors', 'staff' ... */
  direction: string;
  treads: number;
  landings: number;
  [extra: string]: unknown;
}
/** v2: one room with its outline, named or not (rooms/DESIGN.md R-3.4). Read by nothing in the viewer in this milestone. */
export interface Space {
  id: string; floor: FloorKey; o: Ring; h: Ring[];
  /** m2, to 0.1. */
  area: number;
  /** The room's own name ('' when none) and every drawn name in it. Drawing or staff text: textContent only. */
  name: string; names: string[];
  source: 'network' | 'outline' | 'staff';
  /** false when staff marked the room "no ceiling". */
  ceiling: boolean;
  [extra: string]: unknown;
}
export interface Opening {
  id: string; floor: FloorKey; kind: 'door' | 'window' | 'passage';
  x: number; y: number; nx: number; ny: number; width: number;
  subtype?: string; label?: string; wallThickness?: number; exterior?: boolean; inside?: (1 | -1)[];
  sill?: number; head?: number; lintel?: 'lintel' | 'transom' | null; lintelTop?: number; eitherKind?: boolean;
  /** Builders' evidence fields (glazed, jambs, leaves, a, b, floorSide, lintelDepth ...). */
  [extra: string]: unknown;
}
export interface Probe {
  floor: FloorKey; id: string; what: string; x: number; y: number; nx: number; ny: number; inside: (1 | -1)[];
  top?: number; label?: string | null;
  [extra: string]: unknown;
}
export interface ColliderSkin { o: Ring; h: Ring[]; z0: number; z1: number; glass: boolean }
export interface PictureFrame {
  file: string; size: [number, number]; pxPerMetreX: number; pxPerMetreY: number; originPx: Vec2; yDown: true; _?: string;
}
export interface FurnitureKind {
  key: string; label: string; colour: string; height: number; base: number;
  onTop: boolean; support: boolean; blocks: boolean; count: number;
}
export interface FurniturePiece {
  id: string; floor: FloorKey; kind: string; family: string; block: string; layer: string; handle: string;
  x: number; y: number; w: number; d: number; rot: number; on: string | null; approach: string[]; n: number; note: string;
}

export interface BuiltModel {
  project: string;
  shortName: string;
  projectNo?: string | null;
  source: string[];
  units: 'm';
  offset: Vec2;
  photoName: string;
  maxPrefix: string;
  floors: BuiltFloor[];
  railingHeight: number;
  singleLineHeight: number;
  doorHeadDefault: number;
  pictureFrame?: Record<FloorKey, PictureFrame>;
  parts: Part[];
  stairs: Record<FloorKey, StairLines>;
  voids: Record<FloorKey, VoidMark[]>;
  closures: Record<FloorKey, Closure[]>;
  stairOutlines: Record<FloorKey, StairOutline[]>;
  rooms: Room[];
  openings: Opening[];
  probes: Probe[];
  colliderSkins: Record<FloorKey, ColliderSkin[]>;
  furnitureKinds?: FurnitureKind[];
  furniture?: FurniturePiece[];
  /** v2. Present in every model built with the new rule, [] when no stair climbs: its presence switches the foot-based walker on (R-9.1). */
  stairways?: Stairway[];
  /** v2. */
  spaces?: Space[];
}

// =====================================================================================================================
// 2. ReplayData v1 (versions/<n>/stages.json; DESIGN.md section 7). bank_stages.json is valid v1 as it is.
// =====================================================================================================================

/** In replay order: read, sort, align, pair, merge, raise, finish. */
export type StepKey = 'read' | 'sort' | 'align' | 'pair' | 'merge' | 'raise' | 'finish';

export interface ReplayRing { o: Ring; h: Ring[] }
export interface ReplayFloor {
  /** Where this plan sits on the drawing sheet, from its aligned place (plan m). */
  sheet: Vec2;
  /** Drawing lines per category (wall, glass, window, door, stair, railing, noise ...). */
  lines: Record<string, FlatSegments>;
  /** Wall pieces as flat quads x0, y0, ... x3, y3 per piece, per kind (wall, glass). */
  pieces: Record<string, number[]>;
  /** Merged outlines per kind. */
  rings: Record<string, ReplayRing[]>;
}
export interface ReplayData {
  source: { files?: string[]; file?: string; layersInUse?: number[]; layers?: number; units?: string; layersUsed?: number; [extra: string]: unknown };
  /** Legacy: the prototype panel's intro HTML. Not read by the viewer (presentation.intro is). */
  panelIntro?: string;
  /** The Build settings card's facts. */
  intro: string[];
  /** [label, detail] rows of 'How the drawing was read'. */
  layers: [string, string][];
  floors: Record<FloorKey, ReplayFloor>;
  /** Placeholders {<key>level}, {<key>height} (toFixed(2)) and {<key>level+} (signed when >= 0). */
  captions: Record<StepKey, string>;
  stats?: Record<string, unknown>;
  /** Optional; defaults (the bank page's): DEFAULT_REPLAY_TEXTS in DESIGN.md 7.2. */
  introTitle?: string;
  layersTitle?: string;
  stepTitles?: Partial<Record<StepKey, string>>;
  /** '#rrggbb' per line category, plus optional ink, faint, piece, pieceEdge, run, runEdge. */
  colors?: Record<string, string>;
}

// =====================================================================================================================
// 3. Presentation v1 (versions/<n>/version.json -> presentation; DESIGN.md section 8)
// =====================================================================================================================

export interface TextRun { text: string; bold?: boolean }
export interface LegendItem { colour: string; text: string }
export interface Legend { layout: 'inline' | 'lines'; items: LegendItem[] }

export type CameraStart =
  | { kind: 'fixed'; position: Vec3; target: Vec3; far?: number }
  /** The hotel's: target = middle of the slab bounds at targetY, camera = target + away, panned left by half the panel width. */
  | { kind: 'fitSlabs'; away: Vec3; targetY: number; panForPanel: boolean; far?: number };

export interface PartStyle {
  /** '#rrggbb' */
  color: string;
  edge: string;
  /** Merge group name: parts with the same mesh name and fit mode share one mesh per floor. */
  mesh: string;
  /** Transparent glass material, hidden by the Glass tick. */
  glass?: boolean;
  /** Half see-through metal (railings): its opacity. */
  see?: number;
  /** mesh.renderOrder. Defaults: glass, pane, balustrade 3; railing 2; others 0. The house's glass and pane: 0 (its page set none). */
  renderOrder?: number;
  opacity?: number;
  roughness?: number;
  metalness?: number;
  edgeOpacity?: number;
  /** Default true; false: walked on or over, never into (decks). */
  collider?: boolean;
  /** Hidden by the Single-line tick. */
  single?: boolean;
}

/** 'ceilings' (v2, default on): shown only when the model has ceiling parts; ceilings show in Walk and Ghost only (R-9.7). */
export type ToggleName = 'plates' | 'glass' | 'rooms' | 'single' | 'picture' | 'ceilings';

export interface Presentation {
  /** The offline page's <title>. */
  documentTitle: string;
  /** The panel's heading (h1). */
  heading: string;
  intro: TextRun[];
  /** '#rrggbb' (--accent). */
  accent: string;
  legend: Legend;
  floorButtons?: { all?: string; labels?: Partial<Record<FloorKey, string>> };
  labels?: Partial<Record<ToggleName, string>> & { pictureTitle?: string };
  camera: CameraStart;
  partStyles?: Partial<Record<PartKind, Partial<PartStyle>>>;
  /** Degrees; toCreasedNormals and EdgesGeometry threshold. Default 25. */
  creaseAngle?: number;
  groundPlane?: { size: [number, number]; colour: string } | null;
  /** Initial tick states; default all true except picture (false). */
  toggles?: Partial<Record<ToggleName, boolean>>;
}

/** Presentation with every default applied (parsePresentation output used inside the viewer). */
export interface ResolvedPresentation {
  documentTitle: string;
  heading: string;
  intro: TextRun[];
  accent: string;
  legend: Legend;
  floorButtons: { all: string; labels: Partial<Record<FloorKey, string>> };
  labels: Record<ToggleName, string> & { pictureTitle: string };
  camera: CameraStart & { far: number };
  partStyles: Record<PartKind, PartStyle>;
  creaseAngle: number;
  groundPlane: { size: [number, number]; colour: string } | null;
  toggles: Record<ToggleName, boolean>;
}

// =====================================================================================================================
// 4. Store files (app/data; DESIGN.md section 9). The API returns camelCase JSON of the same shapes.
// =====================================================================================================================

export type SourceKind = 'cad' | 'pictures';

/** projects/<id>/meta.json (not 'project.json': that name is kept for the plan's project data, DESIGN.md 9.1). */
export interface ProjectMeta {
  format: 'walkthrough-project/1';
  id: string;
  name: string;
  shortName: string;
  projectNo: string | null;
  sourceKind: SourceKind;
  /** ISO 8601 UTC. */
  createdAt: string;
  updatedAt: string;
  latestVersion: number;
  versions: number[];
}

export interface AssetMeta {
  /** File name under versions/<n>/assets/ (^[A-Za-z0-9._-]+$). */
  name: string;
  role: 'plan-picture' | 'thumbnail';
  floor?: FloorKey;
  mediaType: string;
  bytes: number;
  sha1: string;
  /** For plan pictures: model.pictureFrame[floor].file. */
  modelRef?: string;
}

export interface VersionCounts { floors: number; parts: number; openings: number; furniture: number; furnitureKinds: number; rooms: number }

export interface VersionMeta {
  format: 'walkthrough-version/1';
  projectId: string;
  version: number;
  label: string;
  createdAt: string;
  sourceKind: SourceKind;
  sourceFiles: string[];
  /** 'built-model/2' when the model has the `stairways` key (rooms/DESIGN.md R-12.2). */
  modelFormat: 'built-model/1' | 'built-model/2';
  /** 40 hex: sha1 of versions/<n>/model.json. */
  modelSha1: string;
  /** 12 hex: the model-data stamp shared with the 3ds Max script. */
  stamp: string;
  /** The file (relative to the version folder) whose sha1 gives the stamp: 'model.json' or 'source/<file>'. */
  stampSource: string;
  counts: VersionCounts;
  floors: { key: FloorKey; name: string; level: number }[];
  hasStages: boolean;
  assets: AssetMeta[];
  downloads: { maxScript: string | null; furnitureCsv: boolean };
  presentation: Presentation;
  seed?: { from: string[]; seededAt: string; seedVersion: string };
}

export type HeightMap = Record<string, number>;

/**
 * The edit of one built furniture piece (docs/boxes/DESIGN.md 3.1; step BX, 16 Nov 2026). Today only `removed`: the box
 * is deleted from the version's view, furniture list, 3ds Max script and offline file. Later steps add optional members.
 */
export interface PieceEdit { removed?: true }
/** Furniture piece id -> its edit. Closed: a piece standing on a removed piece is removed too. */
export type PieceEditMap = Record<string, PieceEdit>;

export interface HeightOverridesFile {
  format: 'walkthrough-overrides/1';
  /** kind key -> whole mm (10 - 5000); only kinds whose height differs from the model's. */
  heights: HeightMap;
  /** The deleted boxes (step BX); the key is absent when there are none. */
  pieceEdits?: PieceEditMap;
  revision: number;
  updatedAt: string;
}

// =====================================================================================================================
// 5. Viewer public API (packages/viewer/src/index.ts; DESIGN.md 11.2)
// =====================================================================================================================

export type ViewMode = 'orbit' | 'walk' | 'ghost';
export type ReplayPhase = 'off' | 'settings' | 'play' | 'done';
export type BuildStart = 'settings' | 'play' | 'skip';
export type PhotoFrame = 'screen' | '16:9' | '3:2' | '4:3' | '1:1' | '4:5' | '9:16';
export type ReplaySpeed = 'quick' | 'normal' | 'slow';

/** Address options (the prototypes' ?query options; DESIGN.md 11.3). parseAddressOptions keeps only well-formed values. */
export interface AddressOptions {
  /** Any `mode` key (any value, even empty) -> 'skip', and it wins over build=play; else build=0 -> 'skip', build=play -> 'play'. */
  build?: BuildStart;
  speed?: ReplaySpeed;
  /** captions=0 -> false */
  captions?: boolean;
  /** Only walk / ghost are kept. */
  mode?: 'walk' | 'ghost';
  floor?: FloorKey;
  /**
   * Present whenever the address has an `x` key (three.js metres); each value is parseFloat's number, or null when that key
   * is missing or unreadable. Walk starts at (x ?? 0, z ?? 0); Ghost then sets its position to (x ?? current, y ?? current,
   * z ?? current), as viewer_modes.js applyUrl. Without an `x` key, y and z are not read.
   */
  point?: { x: number | null; y: number | null; z: number | null };
  /** Direction (degrees). parseFloat; unreadable values are dropped (the prototype then kept the current direction). */
  yaw?: number; pitch?: number;
  /** 12 - 85 mm (clamped). */
  lens?: number;
  /** 0.8 - 2.2 m (clamped). */
  eye?: number;
  /** cam=1 */
  cam?: boolean;
  frame?: PhotoFrame;
  /** size=4k -> 3840 (anything else ignored). */
  size?: 1920 | 3840;
  /** straight=1 */
  straight?: boolean;
  /** touch=1 */
  touch?: boolean;
  /** nodownload=1: photos and the CSV are not downloaded. */
  nodownload?: boolean;
  /** shot=1: take a photo 300 ms after start-up. */
  shot?: boolean;
  /** picture=1 / picture=0 */
  picture?: boolean;
  /** test=1 (the offline page maps it to ViewerOptions.testHook). */
  test?: boolean;
}

export interface ViewerProject {
  model: BuiltModel;
  /** Raw or resolved presentation; createViewer resolves defaults. */
  presentation: Presentation;
  stages?: ReplayData | null;
  /** Floor key -> URL (http(s): or data:) of the plan picture. */
  pictures?: Partial<Record<FloorKey, string>>;
  /** Saved heights (overrides.json heights). */
  heights?: HeightMap | null;
  /** Saved piece edits (overrides.json pieceEdits): the deleted boxes. Read leniently (odd values and unknown ids ignored). */
  pieceEdits?: PieceEditMap | null;
  /** 12 hex model-data stamp. */
  stamp: string;
  /** For storage keys and messages. */
  ids?: { projectId: string; version: number };
}

export type FurnitureHeightsMode = 'local' | 'host';

export interface ViewerOptions {
  address?: AddressOptions;
  /** Overrides address.build. Default: 'settings' when stages exist (prototype behaviour), else 'skip'. */
  build?: BuildStart;
  /**
   * 'local' (default): typed heights kept in localStorage under `<storageKeyPrefix><photoName>:<stamp>`, as the differences
   * from the starting heights (DESIGN.md 11.2). 'host': heightschange events only (only the doorways tick is stored).
   */
  furnitureHeights?: FurnitureHeightsMode;
  /** Default 'walkthrough-furniture-heights:'. */
  storageKeyPrefix?: string;
  /** Expose window.__viewer / __host / __build / __walkthrough (section 12). Default false. */
  testHook?: boolean;
  /** Default 2. */
  pixelRatioCap?: number;
  /** Default: an <a download> click inside the root. */
  download?: (blob: Blob, fileName: string) => void;
  /**
   * The staff app's version page only (docs/boxes/DESIGN.md 2.1): furniture boxes can be selected, deleted and restored.
   * Default false: no control appears; saved deletions (project.pieceEdits) are applied all the same.
   */
  editBoxes?: boolean;
  /**
   * Tests only, read only when testHook is true: createViewer throws Error('[viewer] testFailAt <step>') at the start of that
   * init step (DESIGN.md 11.4), after the earlier steps ran, so the leak spec can prove the failure cleanup.
   */
  testFailAt?: 'context' | 'build' | 'panel' | 'modes' | 'furniture' | 'replay' | 'labels' | 'start';
}

export interface PhotoResult { name: string; width: number; height: number }

export interface ViewerEvents {
  /** Emitted by viewer.ts from bus 'mode', only when the mode or the floor differs from the last one emitted. */
  modechange: { mode: ViewMode; floor: FloorKey };
  /**
   * A furniture height was typed or reset in the legend. Emitted by viewer.ts from bus 'furniture' for sources 'typed' and
   * 'reset' only (never 'api' = setHeights, never 'tick' = the doorways tick). heights = kinds differing from the model.
   */
  heightschange: { heights: HeightMap; source: 'typed' | 'reset' };
  /**
   * A furniture box was deleted or restored in the viewer (editBoxes). Emitted by viewer.ts from bus 'pieces' for sources
   * 'removed' and 'restored' only (never 'api' = setPieceEdits). pieceEdits = the whole map each time.
   */
  boxeschange: { pieceEdits: PieceEditMap; source: 'removed' | 'restored' };
  replayphase: { phase: ReplayPhase };
  photo: PhotoResult;
  error: { message: string };
}

export interface Viewer {
  /** Resolves after the plan pictures are read (or failed) and the first frame is drawn. */
  readonly ready: Promise<void>;
  readonly mode: ViewMode;
  readonly disposed: boolean;
  setMode(mode: ViewMode): void;
  goToFloor(key: FloorKey): void;
  /** The floor buttons in Orbit / Ghost: which floors show. */
  showFloors(which: 'all' | FloorKey): void;
  setToggle(name: ToggleName, on: boolean): void;
  getToggles(): Record<ToggleName, boolean>;
  openCamera(open: boolean): void;
  takePhoto(): Promise<PhotoResult | null>;
  /** null when the project has no replay data. */
  readonly replay: { readonly phase: ReplayPhase; generate(): void; skip(): void; openSettings(): void } | null;
  /** null when the model has no furniture. */
  readonly furniture: FurnitureApi | null;
  /** Kinds whose height differs from the model's. */
  getHeights(): HeightMap;
  /** Apply heights from outside (kinds not in the map go back to the model's); unknown kinds and bad values are ignored; no heightschange event. */
  setHeights(heights: HeightMap): void;
  /** The deleted boxes: piece id -> {removed: true}, closed, in the furniture list's order. */
  getPieceEdits(): PieceEditMap;
  /** Apply piece edits from outside (the map replaces the deleted set); unknown ids are ignored, the map is closed; no boxeschange event. */
  setPieceEdits(e: PieceEditMap): void;
  on<E extends keyof ViewerEvents>(event: E, fn: (payload: ViewerEvents[E]) => void): () => void;
  /** Leaves nothing behind: DOM, listeners, timers, GPU memory, the WebGL context, window hooks. Idempotent. */
  dispose(): void;
}

export interface ModelIssue { path: string; message: string }
export interface ModelErrorLike extends Error { readonly issues: ModelIssue[] }

/**
 * Throws ModelError before touching the DOM when the project does not parse, and Error when the container is not in the
 * document. Either returns a handle or throws with nothing left behind: a failure in any later init step runs the viewer's
 * own disposer (root removed, context lost, listeners and timers off, stylesheet and window hooks removed, live counter
 * unchanged) before it rethrows. DESIGN.md 11.2, 11.4.
 */
export type CreateViewer = (container: HTMLElement, project: ViewerProject, options?: ViewerOptions) => Viewer;
export type ParseAddressOptions = (search: string | URLSearchParams) => AddressOptions;
/**
 * Hand-written (no validator library at run time). Throws ModelError (issues with JSON Pointer paths) when the JSON is not
 * BuiltModel v1 or breaks a cross-reference rule outside the furniture; the four furniture rules only console.warn
 * (DESIGN.md 5.6) and the furniture code then behaves as furniture_boxes.js did.
 */
export type ParseBuiltModel = (json: unknown) => BuiltModel;
export type ParseReplayData = (json: unknown, model: BuiltModel) => ReplayData;
export type ParsePresentation = (json: unknown) => Presentation;
export type ResolvePresentationFn = (p: Presentation, model: BuiltModel) => ResolvedPresentation;

// =====================================================================================================================
// 6. Context and core (packages/viewer/src/core; owner: builder A unless said)
// =====================================================================================================================

/** Everything a viewer registers goes through it; dispose() undoes in reverse order. Implemented by the scaffold. */
export interface Disposer {
  /** target.addEventListener now, removeEventListener on dispose. */
  listen<K extends keyof WindowEventMap>(target: Window, type: K, fn: (e: WindowEventMap[K]) => void, opts?: AddEventListenerOptions | boolean): void;
  listen<K extends keyof DocumentEventMap>(target: Document, type: K, fn: (e: DocumentEventMap[K]) => void, opts?: AddEventListenerOptions | boolean): void;
  listen<K extends keyof HTMLElementEventMap>(target: HTMLElement, type: K, fn: (e: HTMLElementEventMap[K]) => void, opts?: AddEventListenerOptions | boolean): void;
  listen(target: EventTarget, type: string, fn: (e: Event) => void, opts?: AddEventListenerOptions | boolean): void;
  timeout(fn: () => void, ms: number): number;
  clearTimeout(id: number): void;
  /** Disposes geometry / material / texture (and three's dispose()-able objects) at the end. */
  track<T extends { dispose(): void }>(thing: T): T;
  /** Any other undo step. */
  add(undo: () => void): void;
  /** URL.revokeObjectURL on dispose. */
  objectUrl(url: string): string;
  readonly disposed: boolean;
  dispose(): void;
}

export interface EventBus<E> {
  on<K extends keyof E>(type: K, fn: (payload: E[K]) => void): () => void;
  emit<K extends keyof E>(type: K, payload: E[K]): void;
  clear(): void;
}

export interface FloorSettings { level: number; height: number }
export type SettingsMap = Record<FloorKey, FloorSettings>;

/** Internal events between modules (ctx.bus). */
export interface InternalEvents {
  mode: { mode: ViewMode; floor: FloorKey };
  floorMode: { floorMode: 'all' | FloorKey };
  toggles: { toggles: Record<ToggleName, boolean> };
  settings: { settings: SettingsMap };
  replayPhase: { phase: ReplayPhase };
  /** Every furniture change; viewer.ts turns only 'typed' and 'reset' into the public heightschange. */
  furniture: { heights: HeightMap; source: 'typed' | 'reset' | 'api' | 'tick' };
  /** Every change of the deleted boxes; viewer.ts turns only 'removed' and 'restored' into the public boxeschange. */
  pieces: { pieceEdits: PieceEditMap; source: 'removed' | 'restored' | 'api' };
  resize: { width: number; height: number };
}

/** Order of the per-frame hooks: replay -> modes -> sync -> (render) -> overlay. */
export type TickPhase = 'replay' | 'modes' | 'sync' | 'overlay';
/**
 * Only viewer.ts calls add(), at the end of init (DESIGN.md 11.4 step 8d): replay.tick, modes.tick, pictures.sync,
 * labels.place. Modules never register their own frame hooks (nothing may run twice a frame).
 */
export interface LoopApi {
  add(phase: TickPhase, fn: (now: number) => void): () => void;
  start(): void;
  stop(): void;
  /** One frame now, synchronously (tests). */
  frame(now?: number): void;
  readonly running: boolean;
}

export interface RiseItem {
  mesh: Mesh;
  edges: LineSegments | null;
  /** fit === 'scale': the replay's wall-height setting scales it about the floor level. */
  scales: boolean;
  fit: FitMode;
}

/** One per model floor, in model order. Shared by every module (the very arrays Walk, the furniture and the replay use). */
export interface FloorRecord {
  key: FloorKey;
  name: string;
  /** The level Walk uses now (Build settings may change it). */
  level: number;
  /** The model's level (never changes): where the floor's geometry and boxes were built. */
  modelLevel: number;
  wallHeight: number;
  stack: string;
  group: Group;
  colliders: Mesh[];
  /** The floor plates (slabs) only, for every reader of before the rooms milestone. */
  walkables: Mesh[];
  /**
   * v2 (rooms/DESIGN.md R-9.2): what the foot-based walker stands on: the meshes of the slab, tread and landing parts.
   * Treads and landings are never colliders. Empty for a model without stairways (the old walker reads `walkables`).
   */
  surfaces: Mesh[];
  /** Shown at the end of the replay (floor plates, stairs, furniture boxes). */
  late: Object3D[];
  rise: RiseItem[];
  /** Lazily set by modes (startPoint). */
  box?: Box3;
}

export interface BuiltScene {
  floors: FloorRecord[];
  /** Objects each tick switches (rooms and picture are handled by labels / pictures). */
  toggleObjects: { plates: Object3D[]; glass: Object3D[]; single: Object3D[] };
  /** Slabs with plinth: true. */
  plinths: Mesh[];
  groundPlane: Mesh | null;
  /** Meshes with fit 'top' / 'clip', per floor (core/heights refits their vertices). */
  fitted: Record<FloorKey, Mesh[]>;
}
/** Pure three.js (no DOM, no renderer): Node-testable. */
export type BuildScene = (model: BuiltModel, presentation: ResolvedPresentation) => BuiltScene;

export interface VisibilityApi {
  readonly floorMode: 'all' | FloorKey;
  setFloorMode(mode: 'all' | FloorKey): void;
  /** group.visible from floorMode (modes call it when leaving Walk: the prototypes' restoreVisibility). */
  applyFloor(): void;
  readonly toggles: Readonly<Record<ToggleName, boolean>>;
  setToggle(name: ToggleName, on: boolean): void;
  /** Re-apply the ticks to their objects (after the replay showed every 'late' object). */
  applyToggles(): void;
  /** Whether the project has anything this tick switches (a tick without anything is not shown). */
  has(name: ToggleName): boolean;
}

export interface HeightsApi {
  /** From the replay's settings: Walk levels, plinths, 'top' / 'clip' refits, picture sheets' y; emits bus 'settings'. */
  apply(settings: SettingsMap): void;
  readonly settings: Readonly<SettingsMap>;
}

export interface RoomLabel { el: HTMLDivElement; floor: FloorKey; area: number; p: Vector3; w?: number; h?: number; dy?: number }
export interface LabelsApi {
  readonly labels: RoomLabel[];
  /** Per frame (overlay phase): position, declutter, show / hide. */
  place(): void;
}
export interface LabelBox { l: number; r: number; t: number; b: number }
/** Pure: the declutter rule (rows 0, +1, -1, +2, -2 of h + 2 px); returns dy per label or null (hidden). */
export type LayoutLabels = (items: { x: number; y: number; w: number; h: number }[]) => (number | null)[];

export interface PicturesApi {
  readonly sheets: Mesh[];
  /** Resolves true per floor when its picture was read. */
  readonly ready: Promise<boolean[]>;
  /** Floor key -> the URL it was given. */
  readonly src: Partial<Record<FloorKey, string>>;
  /** sheet.visible = picture tick && its floor group visible (sync phase, every frame). */
  sync(): void;
}

export interface ReadoutsApi {
  /** Looking straight up from h0 above the level: height above the level of the first visible collider, or null. */
  upHit(floor: FloorKey, x: number, y: number, h0?: number): number | null;
  /** Looking straight down from h0 above the level: height above the level of the first thing below, or null. */
  downHit(floor: FloorKey, x: number, y: number, h0?: number): number | null;
  /** A level ray at height h above the level along plan (dx, dy): { d, name } of the first visible collider, or null. */
  rayHit(floor: FloorKey, x: number, y: number, h: number, dx: number, dy: number, far?: number): { d: number; name: string } | null;
  /** World-space ray (the house page's cast): from p along d up to far, visible colliders of the floor. */
  cast(floor: FloorKey, p: Vec3, d: Vec3, far: number): { d: number; name: string } | null;
  /**
   * v2 (rooms/DESIGN.md R-9.8): the height above the floor's level of the highest surface (slab, tread or landing of the
   * floor's stack) under plan (x, y), looking down from h0 (default 3.0) above the level, or null. downHit keeps reading
   * colliders.
   */
  groundAt(floor: FloorKey, x: number, y: number, h0?: number): number | null;
}

export interface ResolvedOptions {
  address: AddressOptions;
  build: BuildStart;
  furnitureHeights: FurnitureHeightsMode;
  /** `<storageKeyPrefix><photoName>:<stamp>`. */
  storageKey: string;
  testHook: boolean;
  pixelRatioCap: number;
  download: (blob: Blob, fileName: string) => void;
  noDownload: boolean;
  /** options.editBoxes === true; optional, read as `=== true` (a missing key is false). */
  editBoxes?: boolean;
  /** options.testFailAt when testHook is true, else null. */
  testFailAt: NonNullable<ViewerOptions['testFailAt']> | null;
}

export interface ViewerContext {
  readonly id: string;
  readonly container: HTMLElement;
  readonly ui: RootApi;
  readonly renderer: WebGLRenderer;
  readonly canvas: HTMLCanvasElement;
  readonly scene: Scene;
  readonly camera: PerspectiveCamera;
  readonly controls: OrbitControls;
  readonly model: BuiltModel;
  readonly presentation: ResolvedPresentation;
  readonly stages: ReplayData | null;
  readonly project: ViewerProject;
  readonly options: ResolvedOptions;
  readonly floors: FloorRecord[];
  readonly floorByKey: ReadonlyMap<FloorKey, FloorRecord>;
  readonly built: BuiltScene;
  readonly disposer: Disposer;
  readonly events: EventBus<ViewerEvents>;
  readonly bus: EventBus<InternalEvents>;
  readonly loop: LoopApi;
  readonly visibility: VisibilityApi;
  readonly heights: HeightsApi;
  readonly readouts: ReadoutsApi;
  /** Root size in CSS px (canvas size). */
  size(): { width: number; height: number };
  /** Root-relative rectangle of an element (all screen maths is root-relative). */
  rectOf(el: Element): { left: number; top: number; right: number; bottom: number; width: number; height: number };
  /** Shows the error box and emits 'error' (never page-wide listeners). */
  reportError(err: unknown): void;
  // Set during createViewer, in init order (DESIGN.md 11.4). A module reads the fields set after its own install step only
  // inside handlers and tick functions, never while it installs (they are not there yet).
  panel: PanelApi;
  pictures: PicturesApi | null;
  modes: ModesApi;
  furniture: FurnitureApi | null;
  replay: ReplayApi | null;
  labels: LabelsApi;
}

/** core/context.ts: renderer, scene, lights, camera, controls, root, resize; floors come from BuildScene. */
export type CreateContext = (container: HTMLElement, project: ViewerProject, options: ViewerOptions | undefined) => ViewerContext;
export type CreateVisibility = (ctx: ViewerContext) => VisibilityApi;
export type CreateHeights = (ctx: ViewerContext) => HeightsApi;
export type CreateLabels = (ctx: ViewerContext) => LabelsApi;
export type CreatePictures = (ctx: ViewerContext) => PicturesApi | null;
export type CreateReadouts = (ctx: ViewerContext) => ReadoutsApi;
export type CreateLoop = (ctx: Pick<ViewerContext, 'renderer' | 'scene' | 'camera' | 'disposer' | 'reportError'>) => LoopApi;
export type CreateDisposer = () => Disposer;
export type CreateEventBus = <E>() => EventBus<E>;
/** Per-mesh three-mesh-bvh: geometry.boundsTree = new MeshBVH(geometry); mesh.raycast = acceleratedRaycast. No prototype patching. */
export type WithBvh = (mesh: Mesh) => Mesh;
export type InstallTestHook = (ctx: ViewerContext, viewer: Viewer) => void;

// =====================================================================================================================
// 7. UI (packages/viewer/src/ui; owner: builder C). Plain DOM inside the container; CSS scoped under `.wtv`.
// =====================================================================================================================

export interface RootApi {
  /** <div class="wtv" data-wt="root" data-model-stamp="..."> inside the container; removed on dispose. */
  readonly root: HTMLDivElement;
  /** Bottom hint line ([data-wt=hint]). */
  readonly hint: HTMLDivElement;
  /** Error box ([data-wt=error]). */
  readonly errorBox: HTMLDivElement;
  /**
   * Appends CSS text to the viewer's one constructed CSSStyleSheet (document.adoptedStyleSheets, removed on dispose; a <style>
   * inside the root where constructed sheets are missing). Each module adds its chunk once. DESIGN.md 11.6.
   */
  addStyle(css: string): void;
  /** Root flags for CSS: fp, camopen, crowded, touchui, replay (data-<flag> attributes). */
  setFlag(flag: 'fp' | 'camopen' | 'crowded' | 'touchui' | 'replay', on: boolean): void;
}
export type CreateRoot = (container: HTMLElement, accent: string, stamp: string, disposer: Disposer) => RootApi;

/** Panel slots, in order; 'floors' only with more than one floor; 'modes' follows 'floors', or 'shows' when there is none. */
export type PanelSlot = 'title' | 'intro' | 'floors' | 'modes' | 'shows' | 'legend' | 'build' | 'furniture';
export interface PanelApi {
  /** [data-wt=panel] */
  readonly el: HTMLDivElement;
  slot(name: PanelSlot): HTMLDivElement;
  /** Floor buttons follow the walked floor in Walk, else the floor mode. */
  markFloors(state: { mode: ViewMode; floor: FloorKey }): void;
}
export type CreatePanel = (ctx: ViewerContext) => PanelApi;

/** ui/dom.ts (scaffold): elements with text only; never innerHTML with data. */
export type El = <K extends keyof HTMLElementTagNameMap>(
  tag: K,
  props?: { cls?: string; wt?: string; attrs?: Record<string, string>; text?: string; title?: string; style?: Partial<CSSStyleDeclaration> },
  children?: (Node | string | null | undefined)[],
) => HTMLElementTagNameMap[K];

// =====================================================================================================================
// 8. Modes (port of viewer-modes/viewer_modes.js; packages/viewer/src/modes; owner: builder B)
// =====================================================================================================================

/** The live state object (exposed as window.__viewer.state with testHook). Field names as the prototype's `s`. */
export interface ModesState {
  mode: ViewMode;
  floor: FloorRecord;
  pos: Vector3;
  /**
   * v2 (rooms/DESIGN.md R-9.2): the height of the walker's feet above the datum (m); the eye is foot + eye. On a model
   * without stairways it is always the current floor's level (the old walker never reads it).
   */
  foot: number;
  yaw: number;
  pitch: number;
  eye: number;
  lens: number;
  orbitLens: number;
  straight: boolean;
  ghostSpeed: number;
  keys: Set<string>;
  saved: { pos: Vector3; target: Vector3 } | null;
  drag: { id: number; x: number; y: number; x0: number; y0: number; touch: boolean } | null;
  dragMoved: boolean;
  frame: PhotoFrame;
  size: 1920 | 3840;
  grid: boolean;
  camOpen: boolean;
  last: number;
  touch: boolean;
  stick: { id: number | null; x: number; y: number };
  vert: number;
  locked: boolean;
  noDownload?: boolean;
  camWanted?: boolean;
}

/**
 * Read-outs for tests (window.__viewer.probe), exactly the prototype's, plus foot and ground (v2).
 * With climbing on (a model with stairways; rooms/DESIGN.md R-9.8): a probe call starts from where the test put the
 * walker. When state.pos.x / z differ from where the walker last put them, onFloor, clearance, open, crosses and walk first
 * put the foot back on the current floor's level (a teleport). Probe calls never ease the eye. `onFloor` means ground
 * within the step window; `walk` returns the horizontal distance walked (the same as before on flat floors). Models without
 * stairways are not touched.
 */
export interface ModesProbe {
  open(deg?: number): number;
  clearance(): number;
  onFloor(): boolean;
  crosses(x0: number, z0: number, x1: number, z1: number): boolean;
  walk(deg: number, metres: number): number;
  /** v2: the height of the walker's feet above the datum (m). */
  foot(): number;
  /** v2: the height above the datum of the surface under the walker (within the step window), or null. */
  ground(): number | null;
  visible(): FloorKey[];
  camera(): { x: number; y: number; z: number; fov: number; rx: number; offsetY: number | null; dir: Vec3 };
}

export interface ModesApi {
  readonly mode: ViewMode;
  readonly state: ModesState;
  readonly probe: ModesProbe;
  setMode(mode: ViewMode, opt?: { floor?: FloorRecord; point?: { x: number; z: number } }): void;
  goToFloor(key: FloorKey): void;
  changeFloor(step: 1 | -1): void;
  takePhoto(): Promise<PhotoResult | null>;
  openCam(open: boolean): void;
  /** The build replay is on: no keys, clicks or wheel; Orbit only (the prototype's lock). */
  lock(on: boolean): void;
  /**
   * Start-up address options (mode, floor, point, yaw, pitch, lens, eye, cam, frame, size, straight, touch, nodownload, shot),
   * exactly as viewer_modes.js applyUrl. Called once, after replay.start (DESIGN.md 11.4 step 8c): while the replay's settings
   * screen is up modes are locked, so cam=1 only sets camWanted and the panel opens at lock(false).
   */
  applyAddress(a: AddressOptions): void;
  /** Called by the loop in the 'modes' phase (registered by viewer.ts only). */
  tick(now: number): void;
}
export type InstallModes = (ctx: ViewerContext) => ModesApi;

/** Pure helpers (modes/camera.ts), Node-testable. */
export type LensFov = (mm: number) => number;
export type ViewFov = (mm: number, aspect: number) => number;
export interface FrameRectInput {
  frame: PhotoFrame; camOpen: boolean; mode: ViewMode; touch: boolean; narrow: boolean;
  canvas: { width: number; height: number };
  camPanel: { left: number; bottom: number } | null;
  sidePanel: { right: number; width: number } | null;
}
export type FrameRect = (i: FrameRectInput) => { x: number; y: number; w: number; h: number };
export type OutSize = (r: { w: number; h: number }, long: 1920 | 3840) => { w: number; h: number };
export type PhotoName = (photoName: string, mode: ViewMode, where: string, lensMm: number, now: Date) => string;

// =====================================================================================================================
// 9. Furniture (port of furniture/furniture_boxes.js; packages/viewer/src/furniture; owner: builder C)
// =====================================================================================================================

export interface FurniturePieceView extends FurniturePiece {
  z0: number; z1: number;
  visible: boolean;
  blocks: boolean;
  /** Stops Walk now (in its floor's colliders). */
  blocking: boolean;
  /** Present only on a deleted box (its visible and blocking are then false). */
  removed?: true;
}
export interface FurnitureKindView {
  /** count: the kind's live pieces (the deleted boxes are not counted). */
  key: string; label: string; colour: string; height: number; defaultHeight: number; count: number; visible: boolean; blocks: boolean;
}
/** window.__host.furniture and Viewer.furniture; the prototype's API. */
export interface FurnitureApi {
  pieces(): FurniturePieceView[];
  kinds(): FurnitureKindView[];
  setHeight(key: string, mm: number | string): boolean;
  setVisible(key: string, on: boolean): boolean;
  setBlocks(key: string, on: boolean): boolean;
  setKeepDoorways(on: boolean): boolean;
  keepDoorways(): boolean;
  reset(): void;
  /** The family list without a byte-order mark. */
  csv(): string;
  /** Downloads it (BOM + csv()) unless nodownload; returns csv(). */
  saveCsv(): string;
  meshOf(id: string): Mesh | null;
  /** Re-sync colliders and visibility from the ticks (after the replay). */
  apply(): void;
  /** Kinds whose height differs from the model's. */
  heights(): HeightMap;
  /** Apply heights from outside (bus 'furniture' source 'api'): the map replaces the typed set; missing kinds go back to the model's. */
  setHeights(h: HeightMap): void;
  /** The deleted boxes: piece id -> {removed: true}, closed, in the furniture list's order. */
  pieceEdits(): PieceEditMap;
  /** Apply piece edits from outside (bus 'pieces' source 'api'): the map replaces the deleted set; unknown ids ignored; closed. */
  setPieceEdits(e: PieceEditMap): void;
  /** Deletes the box and every piece standing on it; the ids removed (the cascade included), [] when unknown or already removed. */
  removePiece(id: string): string[];
  /** Restores the box's group (its support when that is deleted, and every deleted piece on it); the ids restored. */
  restorePiece(id: string): string[];
  restoreAll(): void;
}
export type InstallFurniture = (ctx: ViewerContext) => FurnitureApi | null;

/** Pure helpers (furniture/logic.ts), Node-testable, the CSV byte-identical to furniture_kit.csv_text. */
export type WholeMm = (v: number) => number;                                  // Math.floor(v + 0.5)
export type ParseTypedHeight = (s: string) => number | null;                  // /^\s*\d+(\.\d*)?\s*$/, whole, 10..5000
export type FixedDecimals = (v: number, n: number) => string;                 // Python f'{v:.nf}' digits, never -0.000
export type CsvField = (v: unknown) => string;                                // RFC 4180 quoting
/** CSV text, CRLF, no BOM; the rows of the `removed` ids (the deleted boxes) are left out. */
export type FurnitureCsv = (model: BuiltModel, heights: HeightMap, removed?: ReadonlySet<string>) => string;
export type UndersideMm = (piece: FurniturePiece, model: BuiltModel, heights: HeightMap) => number;
export type StopsWalk = (k: { visible: boolean; blocks: boolean }, approach: string[], keepDoorways: boolean) => boolean;
/** Stored under `<storageKeyPrefix><photoName>:<stamp>` (DESIGN.md 11.2; the prototypes' key had no stamp: 18.31). */
export interface StoredFurnitureState { heights: HeightMap; keepDoorways: boolean }
/** Junk ignored; heights whole mm 10 - 5000 for known kinds only; only `keepDoorways: false` keeps the tick off. */
export type ReadStoredState = (raw: string | null, kinds: FurnitureKind[]) => StoredFurnitureState;
/**
 * 'local': the kinds whose height differs from `baseline` (the starting heights: the model's, with project.heights over
 * them), plus keepDoorways: false when off; 'host': only keepDoorways: false. null: nothing to keep, remove the key.
 */
export type WriteStoredState = (s: StoredFurnitureState, mode: FurnitureHeightsMode, baseline: HeightMap) => string | null;

// =====================================================================================================================
// 10. Replay (port of viewer-modes/build_replay.js; packages/viewer/src/replay; owner: builder D)
// =====================================================================================================================

export interface ReplayStep { key: StepKey; title: string; caption: (settings: SettingsMap) => string; t0: number; t1: number }
export interface ReplayState {
  phase: ReplayPhase;
  T: number;
  speed: ReplaySpeed;
  captions: boolean;
  last: number;
  endAt: number;
  step: StepKey | null;
  paused?: boolean;
  settings: SettingsMap;
  captionDirty?: boolean;
  ended?: boolean;
}
/** window.__build; the prototype's API. */
export interface ReplayApi {
  readonly phase: ReplayPhase;
  readonly state: ReplayState;
  readonly steps: ReplayStep[];
  generate(): void;
  skip(): void;
  openSettings(): void;
  seek(T: number): void;
  /** 'replay' phase of the loop (registered by viewer.ts only). */
  tick(now: number): void;
  /**
   * Start-up (DESIGN.md 11.4), called before modes.applyAddress. Reads address speed / captions, then: 'settings' ->
   * openSettings(); 'play' -> openSettings() and generate(); 'skip' -> phase 'done' and ctx.heights.apply(the model's
   * settings), nothing else (no enter / finish, no camera pose, no controls change, no lock, no applyFloor / applyToggles /
   * furniture.apply), as build_replay.js's build=0 path.
   */
  start(build: BuildStart, address: AddressOptions): void;
}
export type InstallReplay = (ctx: ViewerContext) => ReplayApi | null;

/** Pure helpers (replay/timeline.ts). */
export type StepTimes = (titles: Record<StepKey, string>) => { key: StepKey; title: string; t0: number; t1: number }[];
export type FillCaption = (template: string, settings: SettingsMap) => string;
export type Ease = (t: number) => number;

// =====================================================================================================================
// 11. Offline payload (the template's <script type="application/json" id="wtv-data">; DESIGN.md section 16)
// =====================================================================================================================

export interface OfflinePayload {
  format: 'walkthrough-offline/1';
  /** The project's meta.json. */
  project: ProjectMeta;
  version: VersionMeta;
  model: BuiltModel;
  stages: ReplayData | null;
  /** Floor key -> data:image/...;base64 URL. */
  pictures: Record<FloorKey, string>;
  overrides: HeightOverridesFile | null;
}

// =====================================================================================================================
// 12. Test hook (only with ViewerOptions.testHook; DESIGN.md 11.7). Names kept from the prototypes.
// =====================================================================================================================

export interface TestHookViewer {
  readonly mode: ViewMode;
  readonly state: ModesState;
  readonly probe: ModesProbe;
  setMode: ModesApi['setMode'];
  goToFloor: ModesApi['goToFloor'];
  takePhoto: ModesApi['takePhoto'];
  lock: ModesApi['lock'];
}
export interface TestHookFloor {
  key: FloorKey; name: string;
  /** The MODEL level (the prototypes' FL records). */
  level: number;
  group: Group; colliders: Mesh[]; walkables: Mesh[]; late: Object3D[]; rise: RiseItem[];
  /** v2: FloorRecord.surfaces (optional here: a page of before the rooms milestone has none). */
  surfaces?: Mesh[];
}
export interface TestHookHost {
  FL: Record<FloorKey, TestHookFloor>;
  /** The FloorRecords (walk levels), the prototypes' FLOORS. */
  floors: FloorRecord[];
  model: BuiltModel;
  openings: Opening[];
  probes: Probe[];
  labels: RoomLabel[];
  upHit: ReadoutsApi['upHit'];
  downHit: ReadoutsApi['downHit'];
  rayHit: ReadoutsApi['rayHit'];
  cast: ReadoutsApi['cast'];
  furniture: FurnitureApi | null;
  camera: PerspectiveCamera;
  controls: OrbitControls;
  pictures: { objs: Mesh[]; ready: Promise<boolean[]>; src: Partial<Record<FloorKey, string>>; show: () => void } | null;
  rise: Record<FloorKey, RiseItem[]>;
  plinths: Mesh[];
  groups: Record<FloorKey, Group>;
  /** BuiltScene.fitted (meshes with fit 'top' / 'clip' per floor); replaces the house page's __host.pieces. */
  fitted: Record<FloorKey, Mesh[]>;
}
export interface TestHookBuild {
  readonly phase: ReplayPhase;
  readonly state: ReplayState;
  readonly steps: ReplayStep[];
  generate(): void; skip(): void; openSettings(): void; seek(T: number): void;
}
export interface TestHookThree {
  Vector2: typeof Vector2; Vector3: typeof Vector3; Raycaster: typeof Raycaster; Box3: typeof Box3; Plane: typeof Plane;
  Matrix4: typeof Matrix4; Quaternion: typeof Quaternion; Euler: typeof Euler; MathUtils: typeof MathUtils; Color: typeof Color;
}
export interface TestHookWalkthrough {
  THREE: TestHookThree;
  viewer: Viewer;
  version: string;
  /** Live viewers in this page (module counter) and viewers created so far. */
  live(): number;
  created(): number;
  /** renderer.info.memory and programs, now. */
  gpu(): { geometries: number; textures: number; programs: number };
}

declare global {
  interface Window {
    __viewer?: TestHookViewer;
    __host?: TestHookHost;
    __build?: TestHookBuild | null;
    __walkthrough?: TestHookWalkthrough;
  }
}
