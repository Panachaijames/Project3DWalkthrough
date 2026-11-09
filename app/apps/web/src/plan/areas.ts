// Area proposals in the browser (docs/upload/DESIGN.md U-14.3: "propose areas again on the wall layers"): the clustering
// of U-7.3 (docs/upload/reference/areas_propose.py, as the reader's drawing.json `areas`) with a layer filter, on the
// decoded plan. Owner U7.
// Occupied 1 m cells of the items' points (every max(1, n // 20)-th point of an item; texts and inserts left out), cells
// within 2 cells of each other connected, each group's box [min x, min y, max x + 1, max y + 1] in sheet metres, boxes
// over 25 m2 kept, sorted top edge first, then left edge (reading order, as the reader's a1, a2 ...).
// One difference from the reader, by design: it reads the plan's points (simplified at 5 mm and quantised to 1 cm), not
// the drawing's own, so a box can differ by a cell where an item sits on a cell edge.
import type { Bbox } from '@/upload/contracts';
import { T_INSERT, T_PATTERN, T_SOLID, T_TEXT, type PlanData } from './decode';

const GAP = 2;
const MIN_AREA = 25;
const OFF = 1 << 20;          // cell coordinates in -1,048,576 .. 1,048,575 m pack into one safe integer
const pack = (x: number, y: number) => (x + OFF) * 2 * OFF + (y + OFF);

export function proposeAreasIn(d: PlanData, layers: ReadonlySet<number>): Bbox[] {
  const [ox, oy] = d.origin;
  const perMetre = 1 / d.quantum;
  const whole = Math.abs(perMetre - Math.round(perMetre)) < 1e-9 && Number.isInteger(ox) && Number.isInteger(oy);
  const n = Math.round(perMetre);
  const cellOf = (q: number, o: number) => (whole ? o + Math.floor(q / n) : Math.floor(o + q * d.quantum + 1e-9));
  const cells = new Map<number, [number, number]>();
  const pts = d.pts;
  const sample = (list: number[]) => {
    const step = Math.max(1, Math.floor(list.length / 2 / 20));
    for (let k = 0; k < list.length / 2; k += step) {
      const x = cellOf(list[2 * k]!, ox), y = cellOf(list[2 * k + 1]!, oy);
      const c = pack(x, y);
      if (!cells.has(c)) cells.set(c, [x, y]);
    }
  };
  let e = 0;
  while (e < d.n) {
    const t = d.type[e]!;
    if (t === T_TEXT || t === T_INSERT || !layers.has(d.layer[e]!)) { e++; continue; }
    // a hatch's loops (consecutive entries of one key) are one item, as in the reader
    const list: number[] = [];
    let k = e;
    do {
      const f = d.first[k]!, c = d.count[k]!;
      for (let p = f; p < f + c; p++) list.push(pts[2 * p]!, pts[2 * p + 1]!);
      k++;
    } while ((t === T_SOLID || t === T_PATTERN) && k < d.n && d.keys[k] === d.keys[e] && d.type[k] === t);
    if (list.length) sample(list);
    e = k;
  }
  const seen = new Set<number>();
  const boxes: Bbox[] = [];
  const order = [...cells.values()].sort((a, b) => a[0] - b[0] || a[1] - b[1]);
  for (const [sx, sy] of order) {
    const start = pack(sx, sy);
    if (seen.has(start)) continue;
    seen.add(start);
    const stack: [number, number][] = [[sx, sy]];
    let x0 = sx, y0 = sy, x1 = sx, y1 = sy;
    while (stack.length) {
      const [x, y] = stack.pop()!;
      if (x < x0) x0 = x; if (x > x1) x1 = x;
      if (y < y0) y0 = y; if (y > y1) y1 = y;
      for (let dx = -GAP; dx <= GAP; dx++) {
        for (let dy = -GAP; dy <= GAP; dy++) {
          const q = pack(x + dx, y + dy);
          if (cells.has(q) && !seen.has(q)) { seen.add(q); stack.push([x + dx, y + dy]); }
        }
      }
    }
    const box: Bbox = [x0, y0, x1 + 1, y1 + 1];
    if ((box[2] - box[0]) * (box[3] - box[1]) > MIN_AREA) boxes.push(box);
  }
  return boxes.sort((a, b) => b[3] - a[3] || a[0] - b[0]);
}
