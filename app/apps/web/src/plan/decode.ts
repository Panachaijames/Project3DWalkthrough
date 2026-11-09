// Decoding a PlanGeometry (docs/upload/DESIGN.md U-7.5, U-12.1) once into typed arrays. Owner U7.
// Everything here works in the plan's LOCAL frame: integer quanta (1 cm) from PlanGeometry.origin, never absolute sheet
// metres (the suite sits near y = -3,500 m; float32 path coordinates would jitter at close zoom). Sheet metres come back
// only through toSheet() when a point is handed out (a pick, a box, a fix).
// The public DecodedPlan (index.ts) carries this module's PlanData under a private symbol: only decodePlan makes one.
import type { Vec2 } from '@walkthrough/viewer';
import type { Bbox, PlanGeometry } from '@/upload/contracts';
import type { DecodedPlan } from './index';

/** Entry types of PlanGeometry.items.type. */
export const T_OPEN = 0, T_CLOSED = 1, T_SOLID = 2, T_PATTERN = 3, T_TEXT = 4, T_INSERT = 5;
export const TYPE_NAMES = ['line', 'closed line', 'solid fill', 'pattern fill', 'text', 'block'] as const;

/** A box in quanta [x0, y0, x1, y1]. */
export type QBox = [number, number, number, number];

export interface PlanData {
  /** The public object this data belongs to. */
  readonly plan: DecodedPlan;
  readonly n: number;
  readonly origin: Vec2;
  readonly quantum: number;
  readonly layerNames: readonly string[];
  /** x, y, x, y ... in quanta from the origin. */
  readonly pts: Int32Array;
  readonly first: Int32Array;
  readonly count: Int32Array;
  readonly layer: Int32Array;
  readonly type: Uint8Array;
  readonly keys: readonly string[];
  /** Per entry x0, y0, x1, y1 (quanta); an entry without points has x0 > x1. */
  readonly box: Int32Array;
  /** The first entry of each key (a hatch's loops share their hatch's key). */
  readonly byKey: ReadonlyMap<string, number>;
  /** The next entry with the same key, or -1. */
  readonly next: Int32Array;
  /** The distinct keys in code-unit order: the subtree of a key K (K/...) is one contiguous run. */
  readonly sortedKeys: readonly string[];
  /** The box of every point (quanta), or null without points. */
  readonly bounds: QBox | null;
  /** The box to fit the view to: every point, unless a few far-off points make it four times the 1 - 99 % box of all
   *  points (the house sheet: stray items hundreds of metres out); then that box grown by 10 %. */
  readonly fitBox: QBox | null;
  /** Entries per anchor key whose subtree is a quarter of the sheet or more (a view or xref block; U7 decision). */
  readonly bigAnchors: ReadonlySet<string>;
  /** Drawn entries (types 0 - 4). */
  readonly drawn: number;
  /** Sheet metres of a local point. */
  toSheet(qx: number, qy: number): Vec2;
  /** Local quanta (not rounded) of a sheet point. */
  toLocal(x: number, y: number): Vec2;
}

const PLAN = Symbol('walkthrough.plan-data');
type Carrier = { [PLAN]?: PlanData };

/** The PlanData behind a DecodedPlan; throws for an object decodePlan did not make. */
export function planData(plan: DecodedPlan): PlanData {
  const d = (plan as DecodedPlan & Carrier)[PLAN];
  if (!d) throw new Error('plan canvas: the plan was not made by decodePlan()');
  return d;
}

const cmp = (a: string, b: string) => (a < b ? -1 : a > b ? 1 : 0);

/** Decodes and checks a PlanGeometry. Throws on a malformed file (parallel arrays of other lengths, points out of range). */
export function decode(json: PlanGeometry): DecodedPlan {
  const it = json.items;
  const n = it.key.length;
  for (const field of ['layer', 'type', 'first', 'count', 'sig', 'rsig', 'eid'] as const) {
    if (it[field].length !== n) throw new Error(`plan geometry: items.${field} has ${it[field].length} entries, items.key ${n}`);
  }
  if (json.pts.length % 2) throw new Error('plan geometry: pts has an odd number of values');
  const q = json.quantum;
  if (!(q > 0) || !Number.isFinite(q)) throw new Error(`plan geometry: quantum ${String(q)} is not a positive number`);
  const [ox, oy] = json.origin;
  if (!Number.isFinite(ox) || !Number.isFinite(oy)) throw new Error('plan geometry: origin is not two numbers');
  const npts = json.pts.length / 2;
  const pts = new Int32Array(json.pts.length);
  for (let i = 0; i < json.pts.length; i++) {
    const v = json.pts[i]!;
    if (!Number.isInteger(v) || v > 2147483647 || v < -2147483648) {
      throw new Error(`plan geometry: pts[${i}] = ${String(v)} is not a whole number of quanta`);
    }
    pts[i] = v;
  }
  const nl = json.layers.length;
  const first = Int32Array.from(it.first), count = Int32Array.from(it.count), layer = Int32Array.from(it.layer);
  const type = new Uint8Array(n);
  const box = new Int32Array(4 * n);
  const next = new Int32Array(n).fill(-1);
  const last = new Map<string, number>();
  const byKey = new Map<string, number>();
  let bx0 = Infinity, by0 = Infinity, bx1 = -Infinity, by1 = -Infinity, drawn = 0;
  for (let i = 0; i < n; i++) {
    const t = it.type[i]!, f = it.first[i]!, c = it.count[i]!, l = it.layer[i]!;
    if (!Number.isInteger(t) || t < 0 || t > 5) throw new Error(`plan geometry: entry ${i} has type ${String(t)} (0 - 5)`);
    if (!Number.isInteger(l) || l < 0 || l >= nl) throw new Error(`plan geometry: entry ${i} has layer ${String(l)} (${nl} layers)`);
    if (!Number.isInteger(f) || !Number.isInteger(c) || f < 0 || c < 0 || f + c > npts) {
      throw new Error(`plan geometry: entry ${i} points ${String(f)} + ${String(c)} lie outside pts (${npts} points)`);
    }
    if (typeof it.key[i] !== 'string') throw new Error(`plan geometry: entry ${i} has no key`);
    type[i] = t;
    if (t !== T_INSERT) drawn++;
    let x0 = 2147483647, y0 = 2147483647, x1 = -2147483648, y1 = -2147483648;
    for (let k = f; k < f + c; k++) {
      const x = pts[2 * k]!, y = pts[2 * k + 1]!;
      if (x < x0) x0 = x; if (x > x1) x1 = x;
      if (y < y0) y0 = y; if (y > y1) y1 = y;
    }
    box[4 * i] = x0; box[4 * i + 1] = y0; box[4 * i + 2] = x1; box[4 * i + 3] = y1;
    if (c) {
      if (x0 < bx0) bx0 = x0; if (x1 > bx1) bx1 = x1;
      if (y0 < by0) by0 = y0; if (y1 > by1) by1 = y1;
    }
    const key = it.key[i]!;
    const prev = last.get(key);
    if (prev === undefined) byKey.set(key, i); else next[prev] = i;
    last.set(key, i);
  }
  const eid = Int32Array.from(it.eid);
  for (let i = 0; i < n; i++) {
    const e = eid[i]!;
    if (e < -1 || e >= json.elementIds.length) throw new Error(`plan geometry: entry ${i} has element id index ${e}`);
  }
  const sortedKeys = [...byKey.keys()].sort(cmp);
  const bounds: QBox | null = Number.isFinite(bx0) ? [bx0, by0, bx1, by1] : null;
  const fitBox = bounds ? robustFit(pts, bounds) : null;
  const extents: Bbox = bounds ? [ox + bounds[0] * q, oy + bounds[1] * q, ox + bounds[2] * q, oy + bounds[3] * q] : [ox, oy, ox, oy];
  const layers = json.layers.slice();
  const keys = it.key.slice();

  const plan: DecodedPlan & Carrier = {
    source: json.source, units: json.units, origin: [ox, oy], quantum: q,
    layers, extents, count: n,
    keyAt: i => keys[i]!,
    layerAt: i => layer[i]!,
    typeAt: i => type[i]!,
    refOf(key) {
      const i = byKey.get(key);
      if (i === undefined) return null;
      const e = eid[i]!;
      return { sig: it.sig[i]!, rsig: it.rsig[i]!, elementId: e >= 0 ? json.elementIds[e] ?? null : null, layer: layers[layer[i]!]! };
    },
  };
  const data: PlanData = {
    plan, n, origin: [ox, oy], quantum: q, layerNames: layers, pts, first, count, layer, type, keys, box, byKey, next,
    sortedKeys, bounds, fitBox, bigAnchors: new Set(), drawn,
    toSheet: (qx, qy) => [round6(ox + qx * q), round6(oy + qy * q)],
    toLocal: (x, y) => [(x - ox) / q, (y - oy) / q],
  };
  (data as { bigAnchors: ReadonlySet<string> }).bigAnchors = findBigAnchors(data);
  Object.defineProperty(plan, PLAN, { value: data, enumerable: true });
  return plan;
}

/** Sheet metres to the micrometre: no 1.2300000000000002 in a fix written back. */
export const round6 = (v: number) => Math.round(v * 1e6) / 1e6;

function robustFit(pts: Int32Array, bounds: QBox): QBox {
  const m = pts.length / 2;
  if (m < 50) return bounds;
  const xs = new Int32Array(m), ys = new Int32Array(m);
  for (let i = 0; i < m; i++) { xs[i] = pts[2 * i]!; ys[i] = pts[2 * i + 1]!; }
  xs.sort(); ys.sort();
  const lo = Math.floor(m * 0.01), hi = Math.max(lo, Math.floor(m * 0.99) - 1);
  const r: QBox = [xs[lo]!, ys[lo]!, xs[hi]!, ys[hi]!];
  const area = (b: QBox) => Math.max(1, b[2] - b[0]) * Math.max(1, b[3] - b[1]);
  if (area(bounds) <= 4 * area(r)) return bounds;
  const gx = Math.ceil((r[2] - r[0]) * 0.1), gy = Math.ceil((r[3] - r[1]) * 0.1);
  return [Math.max(bounds[0], r[0] - gx), Math.max(bounds[1], r[1] - gy), Math.min(bounds[2], r[2] + gx), Math.min(bounds[3], r[3] + gy)];
}

// ------------------------------------------------------------------------------------------------------- keys, blocks
/** The keys whose entries form the subtree of `key` (the key itself and every key starting with key + '/'), in order. */
export function subtreeKeys(d: PlanData, key: string): string[] {
  const out: string[] = [];
  if (d.byKey.has(key)) out.push(key);
  const lo = lowerBound(d.sortedKeys, key + '/'), hi = lowerBound(d.sortedKeys, key + '0');   // '0' follows '/'
  for (let i = lo; i < hi; i++) out.push(d.sortedKeys[i]!);
  return out;
}

/** Every entry of a key (a hatch's loops). */
export function entriesOfKey(d: PlanData, key: string, out: number[] = []): number[] {
  for (let i = d.byKey.get(key) ?? -1; i >= 0; i = d.next[i]!) out.push(i);
  return out;
}

/** Every entry an ItemRef with this key covers: an INSERT anchor's whole subtree, else the key's own entries. */
export function coveredEntries(d: PlanData, key: string): number[] {
  const out: number[] = [];
  const i = d.byKey.get(key);
  if (i !== undefined && d.type[i] === T_INSERT) for (const k of subtreeKeys(d, key)) entriesOfKey(d, k, out);
  else entriesOfKey(d, key, out);
  return out;
}

export function isAnchor(d: PlanData, key: string): boolean {
  const i = d.byKey.get(key);
  return i !== undefined && d.type[i] === T_INSERT;
}

/**
 * The INSERT anchors that hold the item `key`, innermost first (U-12.1 "block": by key prefix). An ATTRIB key
 * (<insert key>@<handle>) belongs to its INSERT. Anchors holding a quarter of the sheet or more (a Revit view block, an
 * xref: the bank's BA, the house's upper floor) are left out, so a block pick never selects the whole drawing.
 */
export function blockChain(d: PlanData, key: string): string[] {
  const out: string[] = [];
  const at = key.indexOf('@');
  let k = at >= 0 ? key.slice(0, at) : key;
  if (at >= 0 && isAnchor(d, k) && !d.bigAnchors.has(k)) out.push(k);
  for (let s = k.lastIndexOf('/'); s > 0; s = k.lastIndexOf('/')) {
    k = k.slice(0, s);
    if (isAnchor(d, k) && !d.bigAnchors.has(k)) out.push(k);
  }
  return out;
}

/** The box (quanta) of what a key covers as drawn (an INSERT's insertion point counts only for a block with no drawing),
 *  or null. */
export function coveredBox(d: PlanData, key: string): QBox | null {
  const entries = coveredEntries(d, key);
  for (const drawnOnly of [true, false]) {
    let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
    for (const i of entries) {
      if (d.count[i] === 0 || (drawnOnly && d.type[i] === T_INSERT)) continue;
      const b = 4 * i;
      if (d.box[b]! < x0) x0 = d.box[b]!; if (d.box[b + 1]! < y0) y0 = d.box[b + 1]!;
      if (d.box[b + 2]! > x1) x1 = d.box[b + 2]!; if (d.box[b + 3]! > y1) y1 = d.box[b + 3]!;
    }
    if (Number.isFinite(x0)) return [x0, y0, x1, y1];
  }
  return null;
}

function lowerBound(a: readonly string[], v: string): number {
  let lo = 0, hi = a.length;
  while (lo < hi) {
    const mid = (lo + hi) >>> 1;
    if (a[mid]! < v) lo = mid + 1; else hi = mid;
  }
  return lo;
}

function findBigAnchors(d: PlanData): Set<string> {
  const out = new Set<string>();
  if (d.drawn < 40) return out;
  const limit = d.drawn / 4;
  for (let i = 0; i < d.n; i++) {
    if (d.type[i] !== T_INSERT) continue;
    const key = d.keys[i]!;
    if (d.byKey.get(key) !== i) continue;
    const lo = lowerBound(d.sortedKeys, key + '/'), hi = lowerBound(d.sortedKeys, key + '0');
    let drawn = 0;
    for (let k = lo; k < hi; k++) for (let e = d.byKey.get(d.sortedKeys[k]!)!; e >= 0; e = d.next[e]!) if (d.type[e] !== T_INSERT) drawn++;
    if (drawn >= limit) out.add(key);
  }
  return out;
}
