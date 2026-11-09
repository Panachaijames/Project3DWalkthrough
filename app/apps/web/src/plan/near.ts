// "Close to walls" (docs/upload/DESIGN.md U-8.1, U-14.3): for each layer that is not a wall layer, how many of its items
// lie within `dist` m of a wall-layer segment. The Layers step puts a warning chip on an `ignore` row that has any
// (ignoring it can change which doors and windows the detector finds: the bank's A-FLOR is its kerb context). Owner U7.
// An item is one key (a hatch's loops count once); drawn items only (an INSERT anchor is not drawn: its lines count on
// their own layers); "within" = some part of the item is at most `dist` from a wall segment. Layers with none are not in
// the map; no wall segment at all gives an empty map.
import { T_INSERT, type PlanData } from './decode';
import { buildGrid, dist2PointSegment, segmentCount, type Grid } from './hit';

/** Squared distance between two segments (0 when they cross). */
export function dist2SegmentSegment(ax: number, ay: number, bx: number, by: number, cx: number, cy: number, dx: number, dy: number): number {
  if (segmentsCross(ax, ay, bx, by, cx, cy, dx, dy)) return 0;
  return Math.min(dist2PointSegment(ax, ay, cx, cy, dx, dy), dist2PointSegment(bx, by, cx, cy, dx, dy),
    dist2PointSegment(cx, cy, ax, ay, bx, by), dist2PointSegment(dx, dy, ax, ay, bx, by));
}

function orient(ax: number, ay: number, bx: number, by: number, cx: number, cy: number): number {
  const v = (bx - ax) * (cy - ay) - (by - ay) * (cx - ax);
  return v > 0 ? 1 : v < 0 ? -1 : 0;
}

function segmentsCross(ax: number, ay: number, bx: number, by: number, cx: number, cy: number, dx: number, dy: number): boolean {
  const o1 = orient(ax, ay, bx, by, cx, cy), o2 = orient(ax, ay, bx, by, dx, dy);
  const o3 = orient(cx, cy, dx, dy, ax, ay), o4 = orient(cx, cy, dx, dy, bx, by);
  return o1 !== o2 && o3 !== o4 && o1 !== 0 && o2 !== 0 && o3 !== 0 && o4 !== 0;
}

export function nearLayersIn(d: PlanData, wallLayers: ReadonlySet<number>, dist: number): Map<number, number> {
  const out = new Map<number, number>();
  if (!(dist >= 0) || !wallLayers.size) return out;
  const r = dist / d.quantum, r2 = r * r;
  const walls: Grid | null = buildGrid(d, e => wallLayers.has(d.layer[e]!), Math.max(200, Math.ceil(r)));
  if (!walls) return out;
  const pts = d.pts;
  const counted = new Uint8Array(d.n);       // per first entry of a key
  const near = (e: number): boolean => {
    const t = d.type[e]!, f = d.first[e]!, c = d.count[e]!, ns = segmentCount(t, c);
    for (let k = 0; k < ns; k++) {
      const a = f + k, b = c === 1 ? f : k + 1 < c ? f + k + 1 : f;
      const ax = pts[2 * a]!, ay = pts[2 * a + 1]!, bx = pts[2 * b]!, by = pts[2 * b + 1]!;
      const c0 = Math.max(0, Math.floor((Math.min(ax, bx) - r - 1 - walls.x0) / walls.cs));
      const r0 = Math.max(0, Math.floor((Math.min(ay, by) - r - 1 - walls.y0) / walls.cs));
      const c1 = Math.min(walls.cols - 1, Math.floor((Math.max(ax, bx) + r + 1 - walls.x0) / walls.cs));
      const r1 = Math.min(walls.rows - 1, Math.floor((Math.max(ay, by) + r + 1 - walls.y0) / walls.cs));
      for (let row = r0; row <= r1; row++) {
        for (let col = c0; col <= c1; col++) {
          const cell = row * walls.cols + col;
          for (let i = walls.start[cell]!; i < walls.start[cell + 1]!; i++) {
            const s = walls.refs[i]!, p = walls.segA[s]!, q = walls.segB[s]!;
            if (dist2SegmentSegment(ax, ay, bx, by, pts[2 * p]!, pts[2 * p + 1]!, pts[2 * q]!, pts[2 * q + 1]!) <= r2) return true;
          }
        }
      }
    }
    return false;
  };
  for (let e = 0; e < d.n; e++) {
    const l = d.layer[e]!;
    if (wallLayers.has(l) || d.type[e] === T_INSERT || d.count[e] === 0) continue;
    const head = d.byKey.get(d.keys[e]!)!;
    if (counted[head]) continue;
    if (near(e)) { counted[head] = 1; out.set(l, (out.get(l) ?? 0) + 1); }
  }
  return out;
}
