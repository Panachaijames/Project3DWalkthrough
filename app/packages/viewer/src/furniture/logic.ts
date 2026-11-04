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
 * The family list (furniture/README.md): CSV_COLUMNS, CRLF after every row (the last too), no byte-order mark (the download
 * adds it). `heights` = {kind: mm} replaces the kinds' heights (what the legend has typed in).
 */
export const furnitureCsv: FurnitureCsv = (model, heights) => {
  const data = furnitureData(model), off = model.offset ?? [0, 0];
  const height = heightFn(data, heights), base = baseFn(data);
  const lines = csvOrder(model, data).map(d => {
    const k = data.kindOf.get(d.kind)!;
    const z0 = undersideOf(d, data.byId, height, base);
    return [d.id, d.floor, d.kind, k.label, d.family, d.block, d.layer, d.handle, fixedDecimals(d.x + off[0], 3),
      fixedDecimals(d.y + off[1], 3), wholeMm(d.w * 1000), wholeMm(d.d * 1000), height(d.kind), z0, fixedDecimals(d.rot, 1), d.on,
      d.n === undefined ? 1 : d.n, d.note].map(csvField).join(',');
  });
  return [CSV_COLUMNS.join(','), ...lines].join('\r\n') + '\r\n';
};

/** The CSV file name: `<photoName>_furniture_list.csv`, anything but word characters, '.' and '-' as '-'. */
export function csvFileName(photoName: string): string {
  return `${photoName}_furniture_list.csv`.replace(/[^\w.-]+/g, '-');
}
