// Picking on the plan (docs/upload/DESIGN.md U-12.1). Owner U7. Pure: no DOM.
// A uniform grid (2 m cells, coarser on a huge sheet so the grid stays under about a million cells) over the segments of
// the drawn entries (types 0 - 4; an INSERT anchor is not drawn and is picked through its subtree). Click = the nearest
// item within a radius; a box selects the items wholly inside, or touched. Pick modes: 'item', 'block' (the innermost
// INSERT holding the item, by key prefix, climbing one level per click), 'layer-in-box'.
import { blockChain, coveredBox, entriesOfKey, T_CLOSED, T_INSERT, T_PATTERN, T_SOLID, type PlanData, type QBox } from './decode';

/** Grid cell in quanta: 2 m. */
export const CELL = 200;
const MAX_CELLS = 1 << 20;

/** The segments of an entry: n - 1 for an open line, n for a closed one (n >= 3), one zero-length segment for a point. */
export function segmentCount(type: number, count: number): number {
  if (count <= 0) return 0;
  if (count === 1) return 1;
  if (type === T_CLOSED || type === T_SOLID || type === T_PATTERN) return count >= 3 ? count : 1;
  return count - 1;
}

export interface Grid {
  x0: number; y0: number; cs: number; cols: number; rows: number;
  /** CSR: cell c holds refs[start[c] .. start[c + 1]). */
  start: Int32Array;
  refs: Int32Array;
  /** Per segment: its entry and its first point's index (absolute, in points). */
  segEntry: Int32Array;
  segA: Int32Array;
  segB: Int32Array;
}

/**
 * The grid over the segments of the entries `accept` takes (default: every drawn entry). Every cell a segment passes
 * through holds it (a supercover walk), so a query need only read the cells its own box touches.
 */
export function buildGrid(d: PlanData, accept: (entry: number) => boolean = e => d.type[e] !== T_INSERT, cellMin = CELL): Grid | null {
  let nseg = 0, x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  for (let e = 0; e < d.n; e++) {
    if (!accept(e) || d.type[e] === T_INSERT) continue;
    const ns = segmentCount(d.type[e]!, d.count[e]!);
    if (!ns) continue;
    nseg += ns;
    const b = 4 * e;
    if (d.box[b]! < x0) x0 = d.box[b]!; if (d.box[b + 1]! < y0) y0 = d.box[b + 1]!;
    if (d.box[b + 2]! > x1) x1 = d.box[b + 2]!; if (d.box[b + 3]! > y1) y1 = d.box[b + 3]!;
  }
  if (!nseg) return null;
  let cs = Math.max(cellMin, 1);
  while (Math.ceil((x1 - x0 + 1) / cs) * Math.ceil((y1 - y0 + 1) / cs) > MAX_CELLS) cs *= 2;
  const cols = Math.max(1, Math.ceil((x1 - x0 + 1) / cs)), rows = Math.max(1, Math.ceil((y1 - y0 + 1) / cs));
  const segEntry = new Int32Array(nseg), segA = new Int32Array(nseg), segB = new Int32Array(nseg);
  let s = 0;
  for (let e = 0; e < d.n; e++) {
    if (!accept(e) || d.type[e] === T_INSERT) continue;
    const t = d.type[e]!, f = d.first[e]!, c = d.count[e]!, ns = segmentCount(t, c);
    for (let k = 0; k < ns; k++) {
      segEntry[s] = e;
      segA[s] = f + k;
      segB[s] = c === 1 ? f : k + 1 < c ? f + k + 1 : f;
      s++;
    }
  }
  const counts = new Int32Array(cols * rows + 1);
  const pts = d.pts;
  const walk = (i: number, visit: (cell: number) => void) => {
    const a = segA[i]!, b = segB[i]!;
    cellsOfSegment(pts[2 * a]! - x0, pts[2 * a + 1]! - y0, pts[2 * b]! - x0, pts[2 * b + 1]! - y0, cs, cols, rows, visit);
  };
  for (let i = 0; i < nseg; i++) walk(i, c => { counts[c]!++; });
  const start = new Int32Array(cols * rows + 1);
  for (let c = 0; c < cols * rows; c++) start[c + 1] = start[c]! + counts[c]!;
  const fill = start.slice(0, cols * rows);
  const refs = new Int32Array(start[cols * rows]!);
  for (let i = 0; i < nseg; i++) walk(i, c => { refs[fill[c]!++] = i; });
  return { x0, y0, cs, cols, rows, start, refs, segEntry, segA, segB };
}

/** Every cell a segment passes through (Amanatides - Woo), clamped to the grid; coordinates relative to the grid's corner. */
export function cellsOfSegment(ax: number, ay: number, bx: number, by: number, cs: number, cols: number, rows: number,
  visit: (cell: number) => void): void {
  let cx = Math.min(cols - 1, Math.max(0, Math.floor(ax / cs))), cy = Math.min(rows - 1, Math.max(0, Math.floor(ay / cs)));
  const ex = Math.min(cols - 1, Math.max(0, Math.floor(bx / cs))), ey = Math.min(rows - 1, Math.max(0, Math.floor(by / cs)));
  visit(cy * cols + cx);
  if (cx === ex && cy === ey) return;
  const dx = bx - ax, dy = by - ay;
  const sx = dx > 0 ? 1 : dx < 0 ? -1 : 0, sy = dy > 0 ? 1 : dy < 0 ? -1 : 0;
  let tx = sx ? ((sx > 0 ? (cx + 1) * cs : cx * cs) - ax) / dx : Infinity;
  let ty = sy ? ((sy > 0 ? (cy + 1) * cs : cy * cs) - ay) / dy : Infinity;
  const dtx = sx ? cs / Math.abs(dx) : Infinity, dty = sy ? cs / Math.abs(dy) : Infinity;
  for (let n = Math.abs(ex - cx) + Math.abs(ey - cy); n > 0; n--) {
    if (tx < ty) { cx += sx; tx += dtx; } else { cy += sy; ty += dty; }
    if (cx < 0 || cy < 0 || cx >= cols || cy >= rows) break;
    visit(cy * cols + cx);
  }
}

/** The cell range a box (quanta) touches, one quantum wider so points on a cell edge are found. */
function cellRange(g: Grid, b: QBox): [number, number, number, number] | null {
  const c0 = Math.floor((b[0] - 1 - g.x0) / g.cs), r0 = Math.floor((b[1] - 1 - g.y0) / g.cs);
  const c1 = Math.floor((b[2] + 1 - g.x0) / g.cs), r1 = Math.floor((b[3] + 1 - g.y0) / g.cs);
  if (c1 < 0 || r1 < 0 || c0 >= g.cols || r0 >= g.rows) return null;
  return [Math.max(0, c0), Math.max(0, r0), Math.min(g.cols - 1, c1), Math.min(g.rows - 1, r1)];
}

/** Squared distance from (px, py) to the segment (ax, ay) - (bx, by). */
export function dist2PointSegment(px: number, py: number, ax: number, ay: number, bx: number, by: number): number {
  const dx = bx - ax, dy = by - ay, l2 = dx * dx + dy * dy;
  let t = l2 > 0 ? ((px - ax) * dx + (py - ay) * dy) / l2 : 0;
  t = t < 0 ? 0 : t > 1 ? 1 : t;
  const x = ax + t * dx - px, y = ay + t * dy - py;
  return x * x + y * y;
}

/** Does the segment touch the box (closed)? Liang - Barsky. */
export function segmentTouchesBox(ax: number, ay: number, bx: number, by: number, b: QBox): boolean {
  let t0 = 0, t1 = 1;
  const dx = bx - ax, dy = by - ay;
  const clip = (p: number, q: number) => {
    if (p === 0) return q >= 0;
    const r = q / p;
    if (p < 0) { if (r > t1) return false; if (r > t0) t0 = r; } else { if (r < t0) return false; if (r < t1) t1 = r; }
    return true;
  };
  return clip(-dx, ax - b[0]) && clip(dx, b[2] - ax) && clip(-dy, ay - b[1]) && clip(dy, b[3] - ay);
}

/** Ties at the same distance: lines before texts before pattern fills before solid fills, then the later entry. */
const RANK = [0, 0, 3, 2, 1, 9];

export interface Hit { entry: number; d: number }

/** The nearest entry within `r` quanta of (qx, qy) that `accept` takes, or null. */
export function nearest(d: PlanData, g: Grid | null, qx: number, qy: number, r: number, accept?: (entry: number) => boolean): Hit | null {
  if (!g) return null;
  const range = cellRange(g, [qx - r, qy - r, qx + r, qy + r]);
  if (!range) return null;
  const pts = d.pts, r2 = r * r;
  let best = -1, bestD = Infinity;
  for (let row = range[1]; row <= range[3]; row++) {
    for (let col = range[0]; col <= range[2]; col++) {
      const c = row * g.cols + col;
      for (let k = g.start[c]!; k < g.start[c + 1]!; k++) {
        const s = g.refs[k]!, e = g.segEntry[s]!;
        if (accept && !accept(e)) continue;
        const a = g.segA[s]!, b = g.segB[s]!;
        const dd = dist2PointSegment(qx, qy, pts[2 * a]!, pts[2 * a + 1]!, pts[2 * b]!, pts[2 * b + 1]!);
        if (dd > r2) continue;
        if (dd < bestD || (dd === bestD && (RANK[d.type[e]!]! < RANK[d.type[best]!]! || (RANK[d.type[e]!] === RANK[d.type[best]!] && e > best)))) {
          best = e; bestD = dd;
        }
      }
    }
  }
  return best < 0 ? null : { entry: best, d: Math.sqrt(bestD) };
}

/** The entries (of `accept`) wholly inside the box ('inside') or touching it ('touch'), ascending. */
export function entriesInBox(d: PlanData, g: Grid | null, b: QBox, mode: 'inside' | 'touch', accept?: (entry: number) => boolean): number[] {
  if (!g) return [];
  const range = cellRange(g, b);
  if (!range) return [];
  const seen = new Uint8Array(d.n);
  const out: number[] = [];
  const pts = d.pts;
  for (let row = range[1]; row <= range[3]; row++) {
    for (let col = range[0]; col <= range[2]; col++) {
      const c = row * g.cols + col;
      for (let k = g.start[c]!; k < g.start[c + 1]!; k++) {
        const s = g.refs[k]!, e = g.segEntry[s]!;
        if (seen[e]) continue;
        if (mode === 'inside') {
          seen[e] = 1;
          if (accept && !accept(e)) continue;
          const o = 4 * e;
          if (d.box[o]! >= b[0] && d.box[o + 1]! >= b[1] && d.box[o + 2]! <= b[2] && d.box[o + 3]! <= b[3]) out.push(e);
        } else {
          if (accept && !accept(e)) { seen[e] = 1; continue; }
          const a = g.segA[s]!, z = g.segB[s]!;
          if (segmentTouchesBox(pts[2 * a]!, pts[2 * a + 1]!, pts[2 * z]!, pts[2 * z + 1]!, b)) { seen[e] = 1; out.push(e); }
        }
      }
    }
  }
  return out.sort((x, y) => x - y);
}

// ----------------------------------------------------------------------------------------------------- pick modes
export type Mode = 'replace' | 'add' | 'toggle';
export type Pick = 'item' | 'block' | 'layer-in-box';

/**
 * The key a click on `entry` selects in the pick mode. 'block': the innermost INSERT anchor holding the item; when that
 * block (or one inside the chain) is already selected and the click replaces the selection, one level up (at the top it
 * stays). An item in no block selects itself.
 */
export function clickKey(d: PlanData, entry: number, pick: Pick, selected: ReadonlySet<string>, mode: Mode): string {
  const key = d.keys[entry]!;
  if (pick !== 'block') return key;
  const chain = blockChain(d, key);
  if (!chain.length) return key;
  if (mode === 'replace') {
    for (let j = chain.length - 1; j >= 0; j--) if (selected.has(chain[j]!)) return chain[Math.min(j + 1, chain.length - 1)]!;
  }
  return chain[0]!;
}

/**
 * The keys a box selects in the pick mode (U-12.1): 'item' every item wholly inside ('inside') or touched ('touch');
 * 'block' the innermost INSERT of each such item (the item itself when it is in no block), an INSERT only when its whole
 * subtree is inside (or, touching, any of it); 'layer-in-box' the items of `layer` only. Keys in entry order, once each;
 * a hatch is inside only when all its loops are.
 */
export function boxKeys(d: PlanData, g: Grid | null, b: QBox, mode: 'inside' | 'touch', pick: Pick, layer: number | null): string[] {
  if (pick === 'layer-in-box' && layer === null) return [];
  const accept = pick === 'layer-in-box' ? (e: number) => d.layer[e] === layer : undefined;
  const found = entriesInBox(d, g, b, mode, accept);
  const out: string[] = [];
  const done = new Set<string>();
  const inside = (e: number) => {
    const o = 4 * e;
    return d.count[e] === 0 || (d.box[o]! >= b[0] && d.box[o + 1]! >= b[1] && d.box[o + 2]! <= b[2] && d.box[o + 3]! <= b[3]);
  };
  for (const e of found) {
    const key = d.keys[e]!;
    let pickKey = key;
    if (pick === 'block') {
      const chain = blockChain(d, key);
      if (chain.length) pickKey = chain[0]!;
    }
    if (done.has(pickKey)) continue;
    done.add(pickKey);
    if (mode === 'inside') {
      if (pickKey !== key) {
        const cb = coveredBox(d, pickKey);
        if (!cb || cb[0] < b[0] || cb[1] < b[1] || cb[2] > b[2] || cb[3] > b[3]) continue;
      } else if (!entriesOfKey(d, key).every(inside)) continue;
    }
    out.push(pickKey);
  }
  return out;
}

