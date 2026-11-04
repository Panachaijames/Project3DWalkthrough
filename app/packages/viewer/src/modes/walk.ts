// Walk collision (DESIGN.md 12 "Walk collision", 13 "Walk"): hitAhead, onFloor, clearance, findFree, openAhead,
// faceOpen, startPoint, walkMove. Port of viewer_modes.js "geometry helpers", behaviour for behaviour, on the shared
// FloorRecords (the very colliders / walkables arrays the furniture and the replay use). Pure three.js: Node-testable.
// Owner: builder B.
import { Box3, Raycaster, Vector3, type Intersection, type Mesh } from 'three';
import type {} from 'three-mesh-bvh';
import type { FloorRecord, ModesState } from '../contracts';
import {
  CLEARANCE_DIRECTIONS, CLEARANCE_FAR, FACE_FAR, FACE_HEADINGS, FACE_KEEP, FLOOR_RAY_FAR, FLOOR_RAY_FROM, FREE_FAR_RINGS,
  FREE_MIN_ROOM, FREE_NEAR_RINGS, FREE_RING_STEP, OPEN_HEIGHT, RADIUS, RAY_HEIGHTS, RAY_OFFSETS,
} from './state';

/** A plan point in three.js coordinates (x, z). */
export interface XZ { x: number; z: number }

export interface Walker {
  /** The one raycaster of the modes (firstHitOnly), shared with the double-click and the probe, as the prototype's. */
  readonly ray: Raycaster;
  visibleColliders(f: FloorRecord): Mesh[];
  /** p = eye position; rays at knee and chest height, across the shoulders, `dist + RADIUS` far. */
  hitAhead(p: Vector3, dir: Vector3, dist: number, f: FloorRecord): Intersection | null;
  /** Is there floor under this point? (no walkables = no check) */
  onFloor(p: XZ, f: FloorRecord): boolean;
  /** Distance to the nearest wall in 8 directions at knee and chest height (up to 3 m; Infinity when nothing). */
  clearance(p: XZ, f: FloorRecord): number;
  /** Moves p (x, z) to the nearest spot of s.floor with `want` m of room, spiralling out; false when there is none. */
  findFree(p: Vector3, want?: number, again?: boolean): boolean;
  /** Free distance straight ahead at chest height from s.pos (up to `far`). */
  openAhead(yaw: number, far: number): number;
  /** Staring at a wall? Turn to the most open view near the current heading (s.yaw). */
  faceOpen(): void;
  /** p if it is over this floor (its group's box), otherwise the middle of the floor. */
  startPoint<T extends XZ>(f: FloorRecord, p: T): T | Vector3;
  /** d = horizontal step this frame: moves s.pos, sliding along walls and floor edges. */
  walkMove(d: Vector3): void;
}

const DOWN = new Vector3(0, -1, 0);

export function createWalker(s: ModesState): Walker {
  const ray = new Raycaster() as Raycaster & { firstHitOnly?: boolean };
  ray.firstHitOnly = true;

  const visibleColliders = (f: FloorRecord) => f.colliders.filter(m => m.visible);

  function hitAhead(p: Vector3, dir: Vector3, dist: number, f: FloorRecord): Intersection | null {
    const cols = visibleColliders(f);
    if (!cols.length) return null;
    const side = new Vector3(-dir.z, 0, dir.x);
    for (const h of RAY_HEIGHTS) {
      // At most 7.5 cm apart, so a partition thicker than that cannot slip between; the outer pair stays 1.5 cm inside
      // the body's edge so that sliding along a wall you touch is not blocked by the wall itself.
      for (const k of RAY_OFFSETS) {
        const origin = new Vector3(p.x, f.level + h, p.z).addScaledVector(side, k * RADIUS);
        ray.set(origin, dir);
        ray.far = dist + RADIUS;
        const hit = ray.intersectObjects(cols, false)[0];
        if (hit) return hit;
      }
    }
    return null;
  }

  function onFloor(p: XZ, f: FloorRecord): boolean {
    if (!f.walkables.length) return true;
    ray.set(new Vector3(p.x, f.level + FLOOR_RAY_FROM, p.z), DOWN);
    ray.far = FLOOR_RAY_FAR;
    return ray.intersectObjects(f.walkables, false).length > 0;
  }

  function clearance(p: XZ, f: FloorRecord): number {
    const cols = visibleColliders(f);
    if (!cols.length) return Infinity;
    let min = Infinity;
    for (const h of RAY_HEIGHTS) {                  // knee and chest height, as walking checks: railings are 1 m high
      const origin = new Vector3(p.x, f.level + h, p.z);
      for (let i = 0; i < CLEARANCE_DIRECTIONS; i++) {
        const a = i * Math.PI / 4;
        ray.set(origin, new Vector3(Math.cos(a), 0, Math.sin(a)));
        ray.far = CLEARANCE_FAR;
        const hit = ray.intersectObjects(cols, false)[0];
        if (hit) min = Math.min(min, hit.distance);
      }
    }
    return min;
  }

  function findFree(p: Vector3, want = FREE_MIN_ROOM, again = true): boolean {
    const f = s.floor;
    const passes: [number, number][] = want > FREE_MIN_ROOM ? [[want, FREE_NEAR_RINGS], [FREE_MIN_ROOM, FREE_FAR_RINGS]] : [[FREE_MIN_ROOM, FREE_FAR_RINGS]];
    for (const [need, maxR] of passes) {
      for (let r = 0; r <= maxR; r += FREE_RING_STEP) {
        const n = r === 0 ? 1 : Math.max(8, Math.round(r * 6));
        for (let i = 0; i < n; i++) {
          const a = i / n * Math.PI * 2, q = new Vector3(p.x + r * Math.cos(a), p.y, p.z + r * Math.sin(a));
          if (clearance(q, f) >= need && onFloor(q, f)) { p.x = q.x; p.z = q.z; return true; }
        }
      }
    }
    // Nothing near (e.g. coming from Ghost far outside): try again from the middle of the floor.
    if (again) {
      const c = startPoint(f, { x: Infinity, z: Infinity });
      if (Number.isFinite(c.x)) { p.x = c.x; p.z = c.z; return findFree(p, want, false); }
    }
    return false;
  }

  function openAhead(yaw: number, far: number): number {
    const f = s.floor, cols = visibleColliders(f);
    if (!cols.length) return far;
    ray.set(new Vector3(s.pos.x, f.level + OPEN_HEIGHT, s.pos.z), new Vector3(-Math.sin(yaw), 0, -Math.cos(yaw)));
    ray.far = far;
    const hit = ray.intersectObjects(cols, false)[0];
    return hit ? hit.distance : far;
  }

  function faceOpen(): void {
    if (openAhead(s.yaw, FACE_KEEP) >= FACE_KEEP) return;
    // The 23 other headings, 15 degrees apart (the current one is never a candidate, so it always turns); the first
    // best (strictly greater) wins.
    let best = s.yaw, bestScore = -Infinity;
    for (let i = 1; i < FACE_HEADINGS; i++) {
      const yaw = s.yaw + i / FACE_HEADINGS * Math.PI * 2;
      const score = openAhead(yaw, FACE_FAR) * (0.7 + 0.3 * Math.cos(yaw - s.yaw));
      if (score > bestScore) { bestScore = score; best = yaw; }
    }
    s.yaw = Math.atan2(Math.sin(best), Math.cos(best));
  }

  function startPoint<T extends XZ>(f: FloorRecord, p: T): T | Vector3 {
    if (!f.box) f.box = new Box3().setFromObject(f.group);
    const b = f.box;
    if (b.isEmpty() || (p.x >= b.min.x && p.x <= b.max.x && p.z >= b.min.z && p.z <= b.max.z)) return p;
    return b.getCenter(new Vector3());
  }

  function walkMove(d: Vector3): void {
    const f = s.floor, dist = d.length();
    if (!(dist > 0)) return;                            // a zero step (dt 0) moves nothing (the prototype cast NaN rays to the same end)
    const dir = d.clone().divideScalar(dist);
    const hit = hitAhead(s.pos, dir, dist, f);
    let step = d;
    if (hit) {
      if (!hit.face) return;
      const n = hit.face.normal.clone().transformDirection(hit.object.matrixWorld);
      n.y = 0;
      if (n.lengthSq() < 1e-6) return;
      n.normalize();
      if (n.dot(dir) > 0) n.negate();
      step = d.clone().addScaledVector(n, -d.dot(n));   // the part of the step along the wall
      const sl = step.length();
      if (sl < 1e-5 || hitAhead(s.pos, step.clone().divideScalar(sl), sl, f)) return;
    }
    const next = s.pos.clone().add(step);
    if (onFloor(next, f)) { s.pos.copy(next); return; }
    // At a floor edge (a void, the edge of a slab): slide along it by trying the x and z parts of the step, larger first.
    const parts = [new Vector3(step.x, 0, 0), new Vector3(0, 0, step.z)].sort((a, b) => b.lengthSq() - a.lengthSq());
    for (const part of parts) {
      const pl = part.length();
      if (pl < 1e-5 || hitAhead(s.pos, part.clone().divideScalar(pl), pl, f)) continue;
      const q = s.pos.clone().add(part);
      if (onFloor(q, f)) { s.pos.copy(q); return; }
    }
  }

  return { ray, visibleColliders, hitAhead, onFloor, clearance, findFree, openAhead, faceOpen, startPoint, walkMove };
}
