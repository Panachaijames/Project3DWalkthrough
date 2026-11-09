// The plan's paths (docs/upload/DESIGN.md U-12.1): one path per (layer, type), built once from the decoded entries, in
// the plan's own integer quanta from PlanGeometry.origin (never absolute sheet metres). Owner U7. The path object is
// made by the caller (Path2D in the browser, a recorder in the unit tests), so this module needs no DOM.
import { T_CLOSED, T_INSERT, T_OPEN, T_PATTERN, T_SOLID, T_TEXT, type PlanData } from './decode';

export interface PathSink {
  moveTo(x: number, y: number): void;
  lineTo(x: number, y: number): void;
  closePath(): void;
}

export interface LayerPath<P> {
  layer: number;
  /** 0 open lines, 1 closed lines and circles, 2 solid fill loops, 3 pattern fill loops. */
  type: number;
  path: P;
  /** Entries in it. */
  entries: number;
  /** Its box (quanta): a path outside the view is not drawn. */
  box: [number, number, number, number];
}

/** Adds entry e to the path: a polyline, closed for types 1 - 3. */
export function addEntry(d: PlanData, e: number, p: PathSink): void {
  const f = d.first[e]!, c = d.count[e]!, t = d.type[e]!;
  if (c < 2 || t === T_TEXT || t === T_INSERT) return;
  const pts = d.pts;
  p.moveTo(pts[2 * f]!, pts[2 * f + 1]!);
  for (let k = f + 1; k < f + c; k++) p.lineTo(pts[2 * k]!, pts[2 * k + 1]!);
  if (t === T_CLOSED || t === T_SOLID || t === T_PATTERN) p.closePath();
}

/** One path per (layer, type) that has drawable entries, in layer order then type order. */
export function buildLayerPaths<P extends PathSink>(d: PlanData, make: () => P): LayerPath<P>[] {
  const types = [T_OPEN, T_CLOSED, T_SOLID, T_PATTERN];
  const nl = d.layerNames.length;
  const slots: (LayerPath<P> | null)[] = new Array(nl * 4).fill(null);
  for (let e = 0; e < d.n; e++) {
    const t = d.type[e]!;
    if (t > T_PATTERN || d.count[e]! < 2) continue;
    const at = d.layer[e]! * 4 + t;
    let slot = slots[at];
    if (!slot) slot = slots[at] = { layer: d.layer[e]!, type: types[t]!, path: make(), entries: 0, box: [Infinity, Infinity, -Infinity, -Infinity] };
    addEntry(d, e, slot.path);
    slot.entries++;
    const b = slot.box, o = 4 * e;
    if (d.box[o]! < b[0]) b[0] = d.box[o]!; if (d.box[o + 1]! < b[1]) b[1] = d.box[o + 1]!;
    if (d.box[o + 2]! > b[2]) b[2] = d.box[o + 2]!; if (d.box[o + 3]! > b[3]) b[3] = d.box[o + 3]!;
  }
  return slots.filter((s): s is LayerPath<P> => s !== null);
}

/** One path holding the given entries (a selection, the set-aside items). */
export function pathOfEntries<P extends PathSink>(d: PlanData, entries: Iterable<number>, make: () => P): P {
  const p = make();
  for (const e of entries) addEntry(d, e, p);
  return p;
}

/** The text anchors per layer, as x, y pairs (quanta): drawn as small dots, never as their text (U-12.1). */
export function textAnchors(d: PlanData): Map<number, number[]> {
  const out = new Map<number, number[]>();
  for (let e = 0; e < d.n; e++) {
    if (d.type[e] !== T_TEXT || d.count[e]! < 1) continue;
    const l = d.layer[e]!;
    let a = out.get(l);
    if (!a) out.set(l, (a = []));
    a.push(d.pts[2 * d.first[e]!]!, d.pts[2 * d.first[e]! + 1]!);
  }
  return out;
}
