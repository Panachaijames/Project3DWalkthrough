// Part geometry helpers (DESIGN.md 5.4, 13 "Building"), exactly the bank page's extrudePart and sweep. Owner: builder A.
// These signatures are not in contracts.ts (they are A's own).
import { BufferAttribute, BufferGeometry, ExtrudeGeometry, Path, Shape, Vector2 } from 'three';
import type { Ring } from '../contracts';

export interface PlanBounds { x0: number; y0: number; x1: number; y1: number }

/** Anything extruded: a part, a collider skin (outline, holes, bottom and top above the floor level). */
export interface Extrudable { o: Ring; h: Ring[]; z0: number; z1: number }

/** The mean of an outline's points (the prototypes' "centre" of a part: the sweep and the fit collapse use it). */
export function ringCentre(o: Ring): [number, number] {
  let cx = 0, cy = 0;
  for (const [x, y] of o) { cx += x; cy += y; }
  return [cx / o.length, cy / o.length];
}

/** Plan bounds of the parts' outlines (Infinity / -Infinity when there are none). */
export function planBounds(parts: readonly { o: Ring }[]): PlanBounds {
  let x0 = Infinity, x1 = -Infinity, y0 = Infinity, y1 = -Infinity;
  for (const p of parts) for (const [x, y] of p.o) {
    x0 = Math.min(x0, x); x1 = Math.max(x1, x); y0 = Math.min(y0, y); y1 = Math.max(y1, y);
  }
  return { x0, y0, x1, y1 };
}

/** The rise sweep: clamp(0.8 (cx - x0)/(x1 - x0) + 0.2 (y1 - cy)/(y1 - y0)) to 0..1, west to east (the bank page's sweep). */
export function sweepDelay(cx: number, cy: number, b: PlanBounds): number {
  return Math.max(0, Math.min(1, 0.8 * (cx - b.x0) / (b.x1 - b.x0 || 1) + 0.2 * (b.y1 - cy) / (b.y1 - b.y0 || 1)));
}

/**
 * Shape(o) with h as holes, ExtrudeGeometry({ depth: z1 - z0, bevelEnabled: false, curveSegments: 1 }), rotateX(-PI/2),
 * translate(0, modelLevel + z0, 0): plan (x, y) -> three.js (x, z = -y). With `delay`, the attribute aDelay (one value
 * per vertex: the replay's rise sweep) as the pages set it.
 */
export function extrudePart(part: Extrudable, modelLevel: number, delay?: number): BufferGeometry {
  const shape = new Shape(part.o.map(([x, y]) => new Vector2(x, y)));
  for (const hole of part.h) shape.holes.push(new Path(hole.map(([x, y]) => new Vector2(x, y))));
  const g = new ExtrudeGeometry(shape, { depth: part.z1 - part.z0, bevelEnabled: false, curveSegments: 1 });
  g.rotateX(-Math.PI / 2);
  g.translate(0, modelLevel + part.z0, 0);
  if (delay !== undefined) {
    const n = g.getAttribute('position').count;
    g.setAttribute('aDelay', new BufferAttribute(new Float32Array(n).fill(delay), 1));
  }
  return g;
}
