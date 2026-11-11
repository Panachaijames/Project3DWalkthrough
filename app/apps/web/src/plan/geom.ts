// Small polygon helpers of the plan canvas for the rooms milestone (docs/rooms/DESIGN.md R-6.4, R-12.6): a point in a
// ring or a polygon with holes (even-odd), a point well inside a polygon (the room panel's and the test hook's point),
// the distance from a point to a ring's edges. Rings are flat [x, y, x, y ...] in any one frame (the canvas uses local
// quanta; the Check step sheet metres). Owner R6. Pure: no DOM.

export type Ring = ArrayLike<number>;

/** The ring as a flat array from points. */
export function flat(points: readonly (readonly [number, number])[]): number[] {
  const out: number[] = [];
  for (const p of points) out.push(p[0], p[1]);
  return out;
}

/** Even-odd: the point is inside the ring (a point on an edge may answer either way). */
export function ringContains(r: Ring, x: number, y: number): boolean {
  const n = r.length >> 1;
  if (n < 3) return false;
  let c = false;
  for (let i = 0, j = n - 1; i < n; j = i++) {
    const xi = r[2 * i]!, yi = r[2 * i + 1]!, xj = r[2 * j]!, yj = r[2 * j + 1]!;
    if ((yi > y) !== (yj > y) && x < xj + ((y - yj) * (xi - xj)) / (yi - yj)) c = !c;
  }
  return c;
}

/** Inside the outline and in none of its holes. */
export function polyContains(o: Ring, holes: readonly Ring[], x: number, y: number): boolean {
  if (!ringContains(o, x, y)) return false;
  for (const h of holes) if (ringContains(h, x, y)) return false;
  return true;
}

/** Squared distance from a point to a segment. */
export function d2Segment(px: number, py: number, ax: number, ay: number, bx: number, by: number): number {
  const dx = bx - ax, dy = by - ay, l2 = dx * dx + dy * dy;
  const t = l2 > 0 ? Math.max(0, Math.min(1, ((px - ax) * dx + (py - ay) * dy) / l2)) : 0;
  return (ax + t * dx - px) ** 2 + (ay + t * dy - py) ** 2;
}

/** The smallest distance from a point to the edges of the rings (closed). */
export function distToRings(rings: readonly Ring[], x: number, y: number): number {
  let best = Infinity;
  for (const r of rings) {
    const n = r.length >> 1;
    for (let i = 0, j = n - 1; i < n; j = i++) {
      const d = d2Segment(x, y, r[2 * j]!, r[2 * j + 1]!, r[2 * i]!, r[2 * i + 1]!);
      if (d < best) best = d;
    }
  }
  return Math.sqrt(best);
}

/** Squared distance from a point to an open polyline. */
export function d2Polyline(r: Ring, x: number, y: number): number {
  let best = Infinity;
  const n = r.length >> 1;
  for (let i = 1; i < n; i++) {
    const d = d2Segment(x, y, r[2 * i - 2]!, r[2 * i - 1]!, r[2 * i]!, r[2 * i + 1]!);
    if (d < best) best = d;
  }
  if (n === 1) best = (r[0]! - x) ** 2 + (r[1]! - y) ** 2;
  return best;
}

/** The ring's box [x0, y0, x1, y1], or null when it has no point. */
export function ringBox(r: Ring): [number, number, number, number] | null {
  if (r.length < 2) return null;
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  for (let i = 0; i + 1 < r.length; i += 2) {
    const x = r[i]!, y = r[i + 1]!;
    if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y;
  }
  return [x0, y0, x1, y1];
}

/** A point well inside the polygon (outline minus holes): of the middles of the inside spans of 15 horizontal and 15
 *  vertical scan lines, the one farthest from every edge. Deterministic; null for a polygon with no inside. */
export function insidePoint(o: Ring, holes: readonly Ring[] = []): [number, number] | null {
  const box = ringBox(o);
  if (!box) return null;
  const rings = [o, ...holes];
  let best: [number, number] | null = null, bestD = -1;
  const consider = (x: number, y: number) => {
    if (!polyContains(o, holes, x, y)) return;
    const d = distToRings(rings, x, y);
    if (d > bestD) { bestD = d; best = [x, y]; }
  };
  for (const axis of [0, 1] as const) {
    const lo = axis === 0 ? box[1] : box[0], hi = axis === 0 ? box[3] : box[2];
    for (let k = 1; k <= 15; k++) {
      const v = lo + ((hi - lo) * k) / 16;
      // crossings of the scan line (y = v for axis 0, x = v for axis 1) with every edge
      const xs: number[] = [];
      for (const r of rings) {
        const n = r.length >> 1;
        for (let i = 0, j = n - 1; i < n; j = i++) {
          const ax = r[2 * j]!, ay = r[2 * j + 1]!, bx = r[2 * i]!, by = r[2 * i + 1]!;
          const [pa, qa, pb, qb] = axis === 0 ? [ay, ax, by, bx] : [ax, ay, bx, by];
          if ((pa > v) !== (pb > v)) xs.push(qa + ((v - pa) * (qb - qa)) / (pb - pa));
        }
      }
      xs.sort((a, b) => a - b);
      for (let i = 0; i + 1 < xs.length; i += 2) {
        const m = (xs[i]! + xs[i + 1]!) / 2;
        if (axis === 0) consider(m, v); else consider(v, m);
      }
    }
  }
  return best;
}

/** The ring's area (absolute, shoelace). */
export function ringArea(r: Ring): number {
  const n = r.length >> 1;
  let a = 0;
  for (let i = 0, j = n - 1; i < n; j = i++) a += r[2 * j]! * r[2 * i + 1]! - r[2 * i]! * r[2 * j + 1]!;
  return Math.abs(a) / 2;
}
