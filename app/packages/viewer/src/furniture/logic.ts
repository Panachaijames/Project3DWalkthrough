// Pure furniture helpers (DESIGN.md 11.1, 13 "Furniture"; port of furniture/furniture_boxes.js). Owner: builder C.
// Node-testable, no DOM, no three.js. The CSV is byte-identical to furniture_kit.csv_text for every model whose data keeps
// the contract (furniture/README.md); for hand-made and older files it does what furniture_boxes.js did (DESIGN.md 5.6):
// a piece whose kind or floor is unknown is left out, a piece whose `on` names no piece stands on its kind's base.
import type {
  BuiltModel, CsvField, FixedDecimals, FurnitureCsv, FurnitureKind, FurniturePiece, HeightMap, ParseTypedHeight, StopsWalk,
  UndersideMm, WholeMm,
} from '../contracts';

/** The height box takes 10 - 5000 whole mm (furniture/README.md; the Max spinner has the same range). */
export const MIN_H = 10;
export const MAX_H = 5000;

/** The family list's columns, in this order (furniture/README.md, "The family list"). */
export const CSV_COLUMNS = ['id', 'level', 'kind', 'kind_label', 'family', 'block', 'layer', 'dxf_handle', 'x_m', 'y_m', 'width_mm',
  'depth_mm', 'height_mm', 'base_mm', 'rotation_deg', 'on_top_of', 'merged', 'note'] as const;

/** Whole mm, a half goes up (as furniture_kit.csv_text rounds; JavaScript's Math.round): 62.5 -> 63, 460.5 -> 461. */
export const wholeMm: WholeMm = v => Math.floor(v + 0.5);

/** A height as typed: whole mm, from 10 to 5000, or null ('', '4,5', '-3', 'abc', '6', '9999'). */
export const parseTypedHeight: ParseTypedHeight = s => {
  const v = /^\s*\d+(\.\d*)?\s*$/.test(s) ? wholeMm(Number(s)) : NaN;
  return v >= MIN_H && v <= MAX_H ? v : null;
};

/** A height from data (stored, saved, an API call): whole mm of Number(v) when 10 - 5000, else null (as the prototype read them). */
export function heightFromData(v: unknown): number | null {
  const n = wholeMm(Number(v));
  return n >= MIN_H && n <= MAX_H ? n : null;
}

/**
 * The same digits as Python's f'{v:.{n}f}' (n >= 1), which furniture_kit.csv_text uses: toFixed rounds an exact tie (12.25 to
 * one decimal) up, Python to the even digit. Never '-0.000'.
 */
export const fixedDecimals: FixedDecimals = (v, n) => {
  const a = Math.abs(v), exact = a.toFixed(n + 30), cut = exact.length - 30;
  let s = a.toFixed(n);
  if (/^50*$/.test(exact.slice(cut)) && Number(exact[cut - 1]) % 2 === 0) s = exact.slice(0, cut);
  return v < 0 && /[1-9]/.test(s) ? '-' + s : s;
};

/** RFC 4180: a field with a comma, a double quote, CR or LF goes in double quotes, inner quotes doubled; null / undefined -> ''. */
export const csvField: CsvField = v => {
  const s = v === null || v === undefined ? '' : String(v);
  return /[",\r\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
};

/** Whether a box stops Walk now: its kind is shown and stops you, and (while the doorways are kept clear) it is in no approach. */
export const stopsWalk: StopsWalk = (k, approach, keepDoorways) => k.visible && k.blocks && !(keepDoorways && approach.length > 0);

const hasOwn = (o: object, key: string) => Object.prototype.hasOwnProperty.call(o, key);

/** The model's furniture as the viewer uses it: kinds (all, model order), the pieces kept and the ones left out. */
export interface FurnitureData {
  kinds: FurnitureKind[];
  kindOf: Map<string, FurnitureKind>;
  /** Pieces with a known kind and a known floor, in model order. */
  pieces: FurniturePiece[];
  /** id -> kept piece (supports are looked up here). */
  byId: Map<string, FurniturePiece>;
  /** Pieces whose kind or floor is unknown (furniture_boxes.js left them out with a warning). */
  leftOut: FurniturePiece[];
}

export function furnitureData(model: BuiltModel, floorKeys: Iterable<string> = model.floors.map(f => f.key)): FurnitureData {
  const floors = new Set(floorKeys);
  const kinds = model.furnitureKinds ?? [];
  const kindOf = new Map(kinds.map(k => [k.key, k]));
  const pieces: FurniturePiece[] = [], leftOut: FurniturePiece[] = [], byId = new Map<string, FurniturePiece>();
  for (const d of model.furniture ?? []) {
    if (!kindOf.has(d.kind) || !floors.has(d.floor)) { leftOut.push(d); continue; }
    pieces.push(d);
    byId.set(d.id, d);
  }
  return { kinds, kindOf, pieces, byId, leftOut };
}

/**
 * The underside above the floor level in mm: the top of the piece it stands on (that piece's own underside plus its kind's
 * height), else the kind's base; at most 3 steps (supports never sit on anything: no chains). Whole mm all the way.
 */
export function undersideOf(p: FurniturePiece, byId: ReadonlyMap<string, FurniturePiece>, heightOf: (kind: string) => number,
  baseOf: (kind: string) => number, depth = 0): number {
  const s = p.on && depth < 3 ? byId.get(p.on) : undefined;
  return s ? undersideOf(s, byId, heightOf, baseOf, depth + 1) + heightOf(s.kind) : baseOf(p.kind);
}

/** A kind's height in mm with the typed heights over the model's (whole mm, as the kit: whole(heights.get(kind, height))). */
function heightFn(data: FurnitureData, heights: HeightMap): (kind: string) => number {
  return kind => wholeMm(hasOwn(heights, kind) ? Number(heights[kind]) : data.kindOf.get(kind)!.height);
}
const baseFn = (data: FurnitureData) => (kind: string) => wholeMm(data.kindOf.get(kind)!.base);

/** The underside (mm) of a piece with the given typed heights: a computer on a 750 table says 750, the wall TV 900. */
export const undersideMm: UndersideMm = (piece, model, heights) => {
  const data = furnitureData(model);
  if (!data.kindOf.has(piece.kind)) return 0;
  return undersideOf(piece, data.byId, heightFn(data, heights), baseFn(data));
};

/** The order of the family list: floor (model order), kind (the kinds table's order), id. */
export function csvOrder(model: BuiltModel, data: FurnitureData): FurniturePiece[] {
  // A key listed twice takes its last place, as kindOf takes its last record (the kit's dicts and the prototype's Maps do the same).
  const level = new Map(model.floors.map((f, i) => [f.key, i])), order = new Map(data.kinds.map((k, i) => [k.key, i]));
  return [...data.pieces].sort((a, b) => level.get(a.floor)! - level.get(b.floor)! || order.get(a.kind)! - order.get(b.kind)!
    || (a.id < b.id ? -1 : a.id > b.id ? 1 : 0));
}

/**
 * The formula guard of a text column (docs/upload/DESIGN.md U-11.6, the same rule as the API's furniture_csv.py): a value
 * starting with =, +, -, @, TAB or CR gets a leading ' so that a spreadsheet reads it as text, never as a formula (uploads
 * bring other offices' block, family and layer names). Applied before the RFC 4180 quoting; null / undefined stay empty.
 */
const csvText = (v: unknown): unknown => {
  if (v === null || v === undefined) return v;
  const s = String(v);
  return /^[=+\-@\t\r]/.test(s) ? `'${s}` : s;
};

/**
 * The family list (furniture/README.md): CSV_COLUMNS, CRLF after every row (the last too), no byte-order mark (the download
 * adds it). `heights` = {kind: mm} replaces the kinds' heights (what the legend has typed in). The text columns (id, level,
 * kind, kind_label, family, block, layer, dxf_handle, on_top_of, note) pass the formula guard (csvText); the number
 * columns never change. `removed` (docs/boxes/DESIGN.md 4): the rows of those ids, the deleted boxes, are left out; the
 * supports' lookup stays the whole list, and the closure (closeRemoved) means no other row changes. None or an empty set:
 * the text is byte for byte as without it.
 */
export const furnitureCsv: FurnitureCsv = (model, heights, removed) => {
  const data = furnitureData(model), off = model.offset ?? [0, 0];
  const height = heightFn(data, heights), base = baseFn(data);
  const lines = csvOrder(model, data).filter(d => !removed?.has(d.id)).map(d => {
    const k = data.kindOf.get(d.kind)!;
    const z0 = undersideOf(d, data.byId, height, base);
    return [csvText(d.id), csvText(d.floor), csvText(d.kind), csvText(k.label), csvText(d.family), csvText(d.block),
      csvText(d.layer), csvText(d.handle), fixedDecimals(d.x + off[0], 3), fixedDecimals(d.y + off[1], 3), wholeMm(d.w * 1000),
      wholeMm(d.d * 1000), height(d.kind), z0, fixedDecimals(d.rot, 1), csvText(d.on), d.n === undefined ? 1 : d.n,
      csvText(d.note)].map(csvField).join(',');
  });
  return [CSV_COLUMNS.join(','), ...lines].join('\r\n') + '\r\n';
};

/** The CSV file name: `<photoName>_furniture_list.csv`, anything but word characters, '.' and '-' as '-'. */
export function csvFileName(photoName: string): string {
  return `${photoName}_furniture_list.csv`.replace(/[^\w.-]+/g, '-');
}

// ------------------------------------------------------------------------------------------------------------------
// Deleted boxes (docs/boxes/DESIGN.md 2.5, 2.6; step BX)
// ------------------------------------------------------------------------------------------------------------------

/** What the closure rule reads of a piece. */
export interface StandsOn { id: string; on?: string | null }

/**
 * The closure rule (docs/boxes/DESIGN.md 2.5): `ids` and every piece standing on one of them, transitively (a piece whose
 * `on` names a removed piece is removed too). The ids given are kept as they are. The same rule as the API's
 * piece_edits.close_removed; both are tested against test/fixtures/furniture/close-removed.cases.json.
 */
export function closeRemoved(ids: Iterable<string>, pieces: Iterable<StandsOn>): Set<string> {
  const standing = new Map<string, string[]>();
  for (const p of pieces) {
    if (typeof p.on !== 'string' || typeof p.id !== 'string') continue;
    const list = standing.get(p.on);
    if (list) list.push(p.id); else standing.set(p.on, [p.id]);
  }
  const removed = new Set(ids), todo = [...removed];
  while (todo.length) {
    for (const child of standing.get(todo.pop()!) ?? []) {
      if (!removed.has(child)) { removed.add(child); todo.push(child); }
    }
  }
  return removed;
}

/** One line of the Restore list: a deleted piece whose support is not deleted, with the deleted pieces standing on it. */
export interface RemovedGroup { top: string; on: string[] }

/**
 * The deleted boxes as groups (docs/boxes/DESIGN.md 2.6), in the order of `pieces`: each deleted piece whose support is
 * not deleted is a top; the deleted pieces standing on it are folded in (`on`, in the order of `pieces`).
 */
export function groupsOf(removed: ReadonlySet<string>, pieces: Iterable<StandsOn>): RemovedGroup[] {
  const groups = new Map<string, RemovedGroup>(), list = [...pieces].filter(p => removed.has(p.id));
  const isTop = (p: StandsOn) => typeof p.on !== 'string' || !removed.has(p.on);
  for (const p of list) if (isTop(p)) groups.set(p.id, { top: p.id, on: [] });
  for (const p of list) if (!isTop(p)) groups.get(topOf(p, list, removed))?.on.push(p.id);
  return [...groups.values()];
}

/** The top of a deleted piece's group: its support while that is deleted too (at most 3 steps, as undersideOf), else itself. */
function topOf(p: StandsOn, list: readonly StandsOn[], removed: ReadonlySet<string>): string {
  let at = p;
  for (let i = 0; i < 3 && typeof at.on === 'string' && removed.has(at.on); i++) {
    const s = list.find(x => x.id === at.on);
    if (!s) break;
    at = s;
  }
  return at.id;
}

/** A saved or given edits map read leniently: the ids whose edit is an object with `removed` exactly true (anything else ignored). */
export function removedIdsOf(edits: unknown): string[] {
  if (edits === null || typeof edits !== 'object' || Array.isArray(edits)) return [];
  return Object.entries(edits as Record<string, unknown>)
    .filter(([, v]) => v !== null && typeof v === 'object' && !Array.isArray(v) && (v as { removed?: unknown }).removed === true)
    .map(([id]) => id);
}
