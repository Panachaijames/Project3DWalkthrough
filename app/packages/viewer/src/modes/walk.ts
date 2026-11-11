// Walk collision (DESIGN.md 12 "Walk collision", 13 "Walk"): hitAhead, onFloor, clearance, findFree, openAhead,
// faceOpen, startPoint, walkMove. Port of viewer_modes.js "geometry helpers", behaviour for behaviour, on the shared
// FloorRecords (the very colliders / walkables arrays the furniture and the replay use). Pure three.js: Node-testable.
// Owner: builder B.
//
// Climbing (rooms/DESIGN.md R-9.2 - R-9.5; rooms step R4): createWalker(s, climb) with `climb` given is the foot-based
// walker of a model with `stairways`. Everything is measured from s.foot instead of the floor's level: the ground ray
// (from foot + 1.0 m down to foot - 0.30 m, the first surface decides: a step up to 0.25 m, a step down to 0.30 m, never
// a fall), the gap bridge (0.08 m further along the move), the head ray (foot + 0.30 up to foot + eye + 0.30, against the
// surfaces), the body rays (against the colliders of every floor of the stack whose height range overlaps
// [foot, foot + 2.0]), and the floor named (the nearest level, with 0.20 m of hysteresis past mid-storey). Without
// `climb` the walker is today's, line for line (the walk-parity golden, R-13).
import { Box3, Raycaster, Vector3, type Intersection, type Mesh } from 'three';
import type {} from 'three-mesh-bvh';
import type { FloorRecord, ModesState } from '../contracts';
import {
  BODY_SPAN, CLEARANCE_DIRECTIONS, CLEARANCE_FAR, FACE_FAR, FACE_HEADINGS, FACE_KEEP, FLOOR_HYSTERESIS, FLOOR_RAY_FAR,
  FLOOR_RAY_FROM, FREE_FAR_RINGS, FREE_MIN_ROOM, FREE_NEAR_RINGS, FREE_RING_STEP, GAP_BRIDGE, GROUND_RAY_FROM,
  HEAD_ABOVE_EYE, HEAD_FROM, OPEN_HEIGHT, RADIUS, RAY_HEIGHTS, RAY_OFFSETS, STEP_DOWN, STEP_EPS, STEP_UP,
} from './state';

/** What the foot-based walker needs beyond the state (modes/index.ts gives it when the model has `stairways`). */
export interface ClimbDeps {
  floors: FloorRecord[];
  /** The floor's slab thickness (m). */
  thickness(f: FloorRecord): number;
  /** The floor's wall height now (m; Build settings may change it). */
  height(f: FloorRecord): number;
  /** The floor named changed during a move (the HUD, the floor buttons, `modechange`). */
  floorChanged?(): void;
}

/** A surface under a point: its height (m above the datum), the floor whose part it is, and whether it is a tread or landing. */
export interface SurfaceHit { y: number; floor: FloorRecord; steps: boolean }

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
  /** The foot-based walker (the model has `stairways`). */
  readonly climbing: boolean;
  /** The height the rays are measured from: s.foot when climbing, else the current floor's level. */
  base(): number;
  /** The visible colliders the walker can meet where it stands (one floor's, two on a stair). */
  bodies(): Mesh[];
  /** The height of the ground under p within the step window (climbing: of s.foot), or null. */
  ground(p: XZ): number | null;
  /** Climbing: the highest surface of the stack of `f` below the height `from` at p; null when none (or not climbing). */
  surfaceUnder(p: XZ, from: number, f: FloorRecord): SurfaceHit | null;
  /** Climbing: names the floor from the foot (nearest level, with hysteresis); true when s.floor changed. */
  nameFloor(): boolean;
  /** Remembers where the walker stands (after a teleport, a frame's move, a probe call): see displaced(). */
  settle(): void;
  /** Climbing: s.pos.x / z or s.floor are not where the walker last put them (a test wrote them, R-9.8). */
  displaced(): boolean;
  /** Climbing: after a Build settings change, puts the foot back on the surface it stood on (levels moved). */
  reground(): void;
  /**
   * Climbing: when displaced(), the walker starts again from where it was put: the foot on the current floor's level, a
   * teleport (R-9.8). True when it did.
   */
  restart(): boolean;
}

const DOWN = new Vector3(0, -1, 0);

export function createWalker(s: ModesState, climb?: ClimbDeps): Walker {
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

  const today: Walker = {
    ray, visibleColliders, hitAhead, onFloor, clearance, findFree, openAhead, faceOpen, startPoint, walkMove,
    climbing: false,
    base: () => s.floor.level,
    bodies: () => visibleColliders(s.floor),
    ground: p => (onFloor(p, s.floor) ? s.floor.level : null),
    surfaceUnder: () => null,
    nameFloor: () => false,
    settle: () => { /* the old walker has no foot */ },
    displaced: () => false,
    reground: () => { /* the per-frame pin follows the level */ },
    restart: () => false,
  };
  if (!climb) return today;

  // ------------------------------------------------------------------------------------------------ the foot-based walker
  const deps = climb;
  const UP = new Vector3(0, 1, 0);
  const stack = (f: FloorRecord) => deps.floors.filter(g => g.stack === f.stack).sort((a, b) => a.level - b.level);
  const surfaceLists = new Map<string, Mesh[]>();
  /** The slabs, treads and landings of every floor of f's stack (whether shown or not, as today's floor test). */
  const surfaces = (f: FloorRecord): Mesh[] => {
    let list = surfaceLists.get(f.stack);
    if (!list) surfaceLists.set(f.stack, (list = deps.floors.filter(g => g.stack === f.stack).flatMap(g => g.surfaces)));
    return list;
  };
  /** Where the walker last put itself (settle), and its foot above its floor's level then. */
  const placed = { x: NaN, z: NaN, floor: null as FloorRecord | null, rel: 0 };

  /** The visible colliders of every floor of the stack whose range [level - slab, level + wall] overlaps [base, base + 2.0]. */
  function bodiesAt(base: number, f: FloorRecord): Mesh[] {
    const out: Mesh[] = [];
    for (const g of deps.floors) {
      if (g.stack !== f.stack) continue;
      const lo = g.level - deps.thickness(g), hi = g.level + deps.height(g);
      if (lo < base + BODY_SPAN - STEP_EPS && hi > base + STEP_EPS) for (const m of g.colliders) if (m.visible) out.push(m);
    }
    return out;
  }

  /**
   * The ground ray at (x, z) for a walker whose foot is at `foot`: from foot + 1.0 m down to foot - 0.30 m; the first
   * surface it meets decides. A height = ground within the step window; 'high' = a step too high (the side of a
   * flight); null = no ground (an edge, a well). A stack with no surface at all is not checked (as today's floor test).
   */
  function groundRay(x: number, z: number, foot: number, f: FloorRecord): { y: number; object: Mesh | null } | 'high' | null {
    const list = surfaces(f);
    if (!list.length) return { y: foot, object: null };
    ray.set(new Vector3(x, foot + GROUND_RAY_FROM, z), DOWN);
    ray.far = GROUND_RAY_FROM + STEP_DOWN + STEP_EPS;
    const hit = ray.intersectObjects(list, false)[0];
    if (!hit) return null;
    return hit.point.y > foot + STEP_UP + STEP_EPS ? 'high' : { y: hit.point.y, object: hit.object as Mesh };
  }

  /** The head ray: is there a slab, tread or landing over (x, z) between foot + 0.30 and foot + eye + 0.30? */
  function headHit(x: number, z: number, foot: number, f: FloorRecord): boolean {
    const list = surfaces(f);
    if (!list.length) return false;
    ray.set(new Vector3(x, foot + HEAD_FROM, z), UP);
    ray.far = s.eye + HEAD_ABOVE_EYE - HEAD_FROM;
    return ray.intersectObjects(list, false).length > 0;
  }

  function hitAheadAt(p: XZ, dir: Vector3, dist: number, base: number, f: FloorRecord): Intersection | null {
    const cols = bodiesAt(base, f);
    if (!cols.length) return null;
    const side = new Vector3(-dir.z, 0, dir.x);
    for (const h of RAY_HEIGHTS) {
      for (const k of RAY_OFFSETS) {
        const origin = new Vector3(p.x, base + h, p.z).addScaledVector(side, k * RADIUS);
        ray.set(origin, dir);
        ray.far = dist + RADIUS;
        const hit = ray.intersectObjects(cols, false)[0];
        if (hit) return hit;
      }
    }
    return null;
  }

  function clearanceAt(p: XZ, base: number, f: FloorRecord): number {
    const cols = bodiesAt(base, f);
    if (!cols.length) return Infinity;
    let min = Infinity;
    for (const h of RAY_HEIGHTS) {
      const origin = new Vector3(p.x, base + h, p.z);
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

  function nameFloor(): boolean {
    const list = stack(s.floor), from = list.indexOf(s.floor);
    let i = from;
    while (i + 1 < list.length && s.foot > (list[i]!.level + list[i + 1]!.level) / 2 + FLOOR_HYSTERESIS) i++;
    while (i > 0 && s.foot < (list[i - 1]!.level + list[i]!.level) / 2 - FLOOR_HYSTERESIS) i--;
    if (i === from) return false;
    s.floor = list[i]!;
    return true;
  }

  function settle(): void {
    placed.x = s.pos.x; placed.z = s.pos.z; placed.floor = s.floor; placed.rel = s.foot - s.floor.level;
  }
  const displaced = () => s.pos.x !== placed.x || s.pos.z !== placed.z || s.floor !== placed.floor;

  /** The move to `next` (a step along `dir`): allowed when there is ground within the window and room for the head. */
  function tryAt(next: XZ, dir: Vector3): boolean {
    const f = s.floor;
    let g = groundRay(next.x, next.z, s.foot, f);
    if (g === null) g = groundRay(next.x + dir.x * GAP_BRIDGE, next.z + dir.z * GAP_BRIDGE, s.foot, f);   // the gap bridge
    if (g === null || g === 'high') return false;
    if (headHit(next.x, next.z, g.y, f)) return false;
    s.pos.x = next.x; s.pos.z = next.z; s.foot = g.y;
    const renamed = nameFloor();
    settle();
    if (renamed) deps.floorChanged?.();
    return true;
  }

  function climbMove(d: Vector3): void {
    const f = s.floor, dist = d.length();
    if (!(dist > 0)) return;
    const dir = d.clone().divideScalar(dist);
    const hit = hitAheadAt(s.pos, dir, dist, s.foot, f);
    let step = d, stepDir = dir;
    if (hit) {
      if (!hit.face) return;
      const n = hit.face.normal.clone().transformDirection(hit.object.matrixWorld);
      n.y = 0;
      if (n.lengthSq() < 1e-6) return;
      n.normalize();
      if (n.dot(dir) > 0) n.negate();
      step = d.clone().addScaledVector(n, -d.dot(n));   // the part of the step along the wall
      const sl = step.length();
      if (sl < 1e-5) return;
      stepDir = step.clone().divideScalar(sl);
      if (hitAheadAt(s.pos, stepDir, sl, s.foot, f)) return;
    }
    if (tryAt({ x: s.pos.x + step.x, z: s.pos.z + step.z }, stepDir)) return;
    // At an edge (a well, the open side of a flight, a step too high): slide along it, as today's floor edge.
    const parts = [new Vector3(step.x, 0, 0), new Vector3(0, 0, step.z)].sort((a, b) => b.lengthSq() - a.lengthSq());
    for (const part of parts) {
      const pl = part.length();
      if (pl < 1e-5) continue;
      const partDir = part.clone().divideScalar(pl);
      if (hitAheadAt(s.pos, partDir, pl, s.foot, f)) continue;
      if (tryAt({ x: s.pos.x + part.x, z: s.pos.z + part.z }, partDir)) return;
    }
  }

  /** Room on the floor's own plate at its level (never on a tread, R-9.5), with ground under the spot and room overhead. */
  function findFreeOnPlate(p: Vector3, want = FREE_MIN_ROOM, again = true): boolean {
    const f = s.floor, base = f.level;
    const plate = (q: XZ): boolean => {
      if (!f.walkables.length) return true;
      const g = groundRay(q.x, q.z, base, f);
      return g !== null && g !== 'high' && (g.object === null || f.walkables.includes(g.object)) && !headHit(q.x, q.z, g.y, f);
    };
    const passes: [number, number][] = want > FREE_MIN_ROOM ? [[want, FREE_NEAR_RINGS], [FREE_MIN_ROOM, FREE_FAR_RINGS]] : [[FREE_MIN_ROOM, FREE_FAR_RINGS]];
    for (const [need, maxR] of passes) {
      for (let r = 0; r <= maxR; r += FREE_RING_STEP) {
        const n = r === 0 ? 1 : Math.max(8, Math.round(r * 6));
        for (let i = 0; i < n; i++) {
          const a = i / n * Math.PI * 2, q = new Vector3(p.x + r * Math.cos(a), p.y, p.z + r * Math.sin(a));
          if (clearanceAt(q, base, f) >= need && plate(q)) { p.x = q.x; p.z = q.z; return true; }
        }
      }
    }
    if (again) {
      const c = startPoint(f, { x: Infinity, z: Infinity });
      if (Number.isFinite(c.x)) { p.x = c.x; p.z = c.z; return findFreeOnPlate(p, want, false); }
    }
    return false;
  }

  function openAheadFromFoot(yaw: number, far: number): number {
    const cols = bodiesAt(s.foot, s.floor);
    if (!cols.length) return far;
    ray.set(new Vector3(s.pos.x, s.foot + OPEN_HEIGHT, s.pos.z), new Vector3(-Math.sin(yaw), 0, -Math.cos(yaw)));
    ray.far = far;
    const hit = ray.intersectObjects(cols, false)[0];
    return hit ? hit.distance : far;
  }

  function faceOpenFromFoot(): void {
    if (openAheadFromFoot(s.yaw, FACE_KEEP) >= FACE_KEEP) return;
    let best = s.yaw, bestScore = -Infinity;
    for (let i = 1; i < FACE_HEADINGS; i++) {
      const yaw = s.yaw + i / FACE_HEADINGS * Math.PI * 2;
      const score = openAheadFromFoot(yaw, FACE_FAR) * (0.7 + 0.3 * Math.cos(yaw - s.yaw));
      if (score > bestScore) { bestScore = score; best = yaw; }
    }
    s.yaw = Math.atan2(Math.sin(best), Math.cos(best));
  }

  function surfaceUnder(p: XZ, from: number, f: FloorRecord): SurfaceHit | null {
    const list = surfaces(f);
    if (!list.length) return null;
    ray.set(new Vector3(p.x, from, p.z), DOWN);
    ray.far = Infinity;
    const hit = ray.intersectObjects(list, false)[0];
    if (!hit) return null;
    const floor = deps.floors.find(g => g.surfaces.includes(hit.object as Mesh)) ?? f;
    return { y: hit.point.y, floor, steps: hit.object.userData.steps === true };
  }

  /** Build settings moved the levels: the foot goes to the surface nearest to where it was above its floor. */
  function reground(): void {
    const target = s.floor.level + placed.rel, list = surfaces(s.floor);
    let best = target, gap = Infinity;
    if (list.length) {
      for (const m of list) m.updateWorldMatrix(true, false);
      ray.firstHitOnly = false;
      ray.set(new Vector3(s.pos.x, target + GROUND_RAY_FROM, s.pos.z), DOWN);
      ray.far = GROUND_RAY_FROM * 2;
      for (const hit of ray.intersectObjects(list, false)) {
        const g = Math.abs(hit.point.y - target);
        if (g < gap) { gap = g; best = hit.point.y; }
      }
      ray.firstHitOnly = true;
    }
    s.foot = best;
    nameFloor();
    settle();
  }

  return {
    ray, visibleColliders, startPoint,
    climbing: true,
    hitAhead: (p, dir, dist, f) => hitAheadAt(p, dir, dist, s.foot, f),
    onFloor: (p, f) => { const g = groundRay(p.x, p.z, s.foot, f); return g !== null && g !== 'high'; },
    clearance: (p, f) => clearanceAt(p, s.foot, f),
    findFree: findFreeOnPlate,
    openAhead: openAheadFromFoot,
    faceOpen: faceOpenFromFoot,
    walkMove: climbMove,
    base: () => s.foot,
    bodies: () => bodiesAt(s.foot, s.floor),
    ground: p => { const g = groundRay(p.x, p.z, s.foot, s.floor); return g !== null && g !== 'high' ? g.y : null; },
    surfaceUnder, nameFloor, settle, displaced, reground,
    restart() {
      if (!displaced()) return false;
      s.foot = s.floor.level;
      if (s.mode === 'walk') s.pos.y = s.foot + s.eye;
      settle();
      return true;
    },
  };
}

