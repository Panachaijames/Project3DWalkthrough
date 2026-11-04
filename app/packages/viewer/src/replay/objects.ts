// Replay geometry: the drawing's lines, the wall pieces, the merged outlines and the scan bar, made fresh for every run
// (port of build_replay.js "replay objects": segGeometry, quadGeometries, ringGeometries, bounds, make, unmake).
// Owner: builder D. Pure three.js (no DOM): Node-testable.
import {
  BufferAttribute, BufferGeometry, Color, DoubleSide, Float32BufferAttribute, Group, LineBasicMaterial, LineSegments, Mesh,
  MeshBasicMaterial, Path, PlaneGeometry, Shape, ShapeGeometry, Vector2, type Plane, type Scene,
} from 'three';
import type { FloorRecord, ReplayData, ReplayRing, Vec2 } from '../contracts';
import { DEFAULT_REPLAY_TEXTS } from '../model/presentation';
import type { RiseUniforms } from './shader';

/** The replay's colours: '#rrggbb' per line category, plus its own ink, faint, piece, pieceEdge, run, runEdge. */
export type ReplayColors = Record<string, string>;
/** The replay's own colours (build_replay.js `C`), which a stages file may override. */
const OWN = ['ink', 'faint', 'piece', 'pieceEdge', 'run', 'runEdge'] as const;

/**
 * The colours of a replay (DESIGN.md 7.2): without `colors` the defaults (the bank page's); with them, exactly what the
 * page passed over the replay's own defaults (build_replay.js `Object.assign({ ink, ... }, o.colors)`), so a category the
 * page did not colour stays ink, as it did there.
 */
export function replayColors(stages: Pick<ReplayData, 'colors'>): ReplayColors {
  const d = DEFAULT_REPLAY_TEXTS.colors;
  if (!stages.colors) return { ...d };
  const own: ReplayColors = {};
  for (const k of OWN) if (typeof d[k] === 'string') own[k] = d[k];
  return { ...own, ...stages.colors };
}

/** Plan bounds of a floor's kept lines (not the noise). */
export interface PlanBox { x0: number; x1: number; y0: number; y1: number }

/** build_replay.js bounds(): over every line category except 'noise'; Infinity / -Infinity when there is none. */
export function lineBounds(lines: Record<string, readonly number[]>): PlanBox {
  let x0 = Infinity, x1 = -Infinity, y0 = Infinity, y1 = -Infinity;
  for (const [cat, a] of Object.entries(lines)) {
    if (cat === 'noise') continue;
    for (let i = 0; i + 1 < a.length; i += 2) {
      const x = a[i]!, y = a[i + 1]!;
      x0 = Math.min(x0, x); x1 = Math.max(x1, x); y0 = Math.min(y0, y); y1 = Math.max(y1, y);
    }
  }
  return { x0, x1, y0, y1 };
}

export const boundsEmpty = (b: PlanBox): boolean => !(Number.isFinite(b.x0) && Number.isFinite(b.x1) && Number.isFinite(b.y0) && Number.isFinite(b.y1));

/**
 * The framing box of a floor whose replay data has no kept lines (the pages always had lines, so they never needed one):
 * the plan bounds of the floor's parts, else the origin. Keeps the camera search finite.
 */
export function partBounds(parts: readonly { floor: string; o: readonly Vec2[] }[], floor: string): PlanBox {
  let x0 = Infinity, x1 = -Infinity, y0 = Infinity, y1 = -Infinity;
  for (const p of parts) {
    if (p.floor !== floor) continue;
    for (const [x, y] of p.o) { x0 = Math.min(x0, x); x1 = Math.max(x1, x); y0 = Math.min(y0, y); y1 = Math.max(y1, y); }
  }
  const b = { x0, x1, y0, y1 };
  return boundsEmpty(b) ? { x0: 0, x1: 0, y0: 0, y1: 0 } : b;
}

/** Flat [x1, y1, x2, y2, ...] in plan metres -> line segments at height y. */
export function segGeometry(a: readonly number[], y: number): BufferGeometry {
  const n = Math.floor(a.length / 4), pos = new Float32Array(n * 6);
  for (let i = 0; i < n; i++) {
    pos[6 * i] = a[4 * i]!; pos[6 * i + 1] = y; pos[6 * i + 2] = -a[4 * i + 1]!;
    pos[6 * i + 3] = a[4 * i + 2]!; pos[6 * i + 4] = y; pos[6 * i + 5] = -a[4 * i + 3]!;
  }
  const g = new BufferGeometry();
  g.setAttribute('position', new BufferAttribute(pos, 3));
  return g;
}

/** Flat quads (x0, y0, ... x3, y3 per piece) -> filled triangles + their outlines (the seams). */
export function quadGeometries(q: readonly number[], y: number): [BufferGeometry, BufferGeometry] {
  const n = Math.floor(q.length / 8), tri = new Float32Array(n * 18), edge = new Float32Array(n * 24);
  for (let i = 0; i < n; i++) {
    const P = (k: number): [number, number, number] => [q[8 * i + 2 * k]!, y, -q[8 * i + 2 * k + 1]!];
    tri.set([...P(0), ...P(1), ...P(2), ...P(0), ...P(2), ...P(3)], 18 * i);
    edge.set([...P(0), ...P(1), ...P(1), ...P(2), ...P(2), ...P(3), ...P(3), ...P(0)], 24 * i);
  }
  const a = new BufferGeometry(); a.setAttribute('position', new BufferAttribute(tri, 3));
  const b = new BufferGeometry(); b.setAttribute('position', new BufferAttribute(edge, 3));
  return [a, b];
}

/** Merged outlines -> a flat fill + the outline, at height y. */
export function ringGeometries(rings: readonly ReplayRing[], y: number): [BufferGeometry, BufferGeometry] {
  const shapes: Shape[] = [], edge: number[] = [];
  for (const r of rings) {
    const s = new Shape(r.o.map(([x, z]) => new Vector2(x, z)));
    for (const h of r.h) s.holes.push(new Path(h.map(([x, z]) => new Vector2(x, z))));
    shapes.push(s);
    for (const loop of [r.o, ...r.h] as Vec2[][]) {
      loop.forEach((p, i) => { const q = loop[(i + 1) % loop.length]!; edge.push(p[0], y, -p[1], q[0], y, -q[1]); });
    }
  }
  const fill = new ShapeGeometry(shapes, 1); fill.rotateX(-Math.PI / 2); fill.translate(0, y, 0);
  const line = new BufferGeometry(); line.setAttribute('position', new Float32BufferAttribute(edge, 3));
  return [fill, line];
}

export const lineMat = (color: string, opacity: number, clip?: Plane[]): LineBasicMaterial =>
  new LineBasicMaterial({ color, transparent: true, opacity, depthWrite: false, clippingPlanes: clip ?? null });
export const fillMat = (color: string, opacity: number, clip?: Plane[]): MeshBasicMaterial =>
  new MeshBasicMaterial({ color, transparent: true, opacity, depthWrite: false, side: DoubleSide, clippingPlanes: clip ?? null });

/** What the replay knows about each model floor (in model order). */
export interface ReplayFloorRt {
  /** The shared floor record (group, rise, late ...). */
  rec: FloorRecord;
  key: string;
  name: string;
  /** The model's level L0 (build_replay.js f.level: where the geometry was built). */
  level: number;
  /** The model's wall height H0 (build_replay.js f.height). */
  height: number;
  /** Where this plan sits on the drawing sheet, from its aligned place (plan m). */
  sheet: Vec2;
  lines: Record<string, number[]>;
  pieces: Record<string, number[]>;
  rings: Record<string, ReplayRing[]>;
  /** Plan bounds of the kept lines (or of the floor's parts when it has none). */
  b: PlanBox;
  /** The floor's rise uniforms (its solids' shader patch). */
  u: RiseUniforms;
}

export interface MadeLine { faint: LineSegments; ink: LineSegments; color: Color }
export interface MadeFill { m: Mesh; e: LineSegments; glass: boolean }
export interface MadeFloor { f: ReplayFloorRt; g: Group; lines: Record<string, MadeLine>; pieces: MadeFill[]; runs: MadeFill[] }
export interface Made { floors: MadeFloor[]; scan: Mesh }

/**
 * build_replay.js make(): the scan bar (in the scene) and, per floor, a 'build replay' group inside the floor's group
 * with the faint and ink lines of every category, the wall pieces and the merged outlines.
 */
export function makeReplayObjects(o: {
  scene: Scene; floors: readonly ReplayFloorRt[]; colors: ReplayColors; accent: string; scanPlane: Plane; sweepPlane: Plane;
}): Made {
  const C = o.colors;
  const ink = C.ink ?? DEFAULT_REPLAY_TEXTS.colors.ink ?? '#3b4148';
  const faint = C.faint ?? DEFAULT_REPLAY_TEXTS.colors.faint ?? '#a4acb4';
  const col = (k: string, fallback: string) => C[k] ?? DEFAULT_REPLAY_TEXTS.colors[k] ?? fallback;
  const scan = new Mesh(new PlaneGeometry(0.35, 1).rotateX(-Math.PI / 2),
    new MeshBasicMaterial({ color: new Color(o.accent || '#c9773e'), transparent: true, opacity: 0.85, depthWrite: false }));
  scan.name = 'build replay scan';
  scan.renderOrder = 7; scan.visible = false;
  o.scene.add(scan);
  const made: Made = { floors: [], scan };
  for (const f of o.floors) {
    const g = new Group(); g.name = 'build replay';
    const y = f.level, F: MadeFloor = { f, g, lines: {}, pieces: [], runs: [] };
    for (const [cat, a] of Object.entries(f.lines)) {
      if (!a.length) continue;
      const geo = segGeometry(a, y + 0.03);
      const faintLines = new LineSegments(geo, lineMat(faint, cat === 'noise' ? 0.35 : 0.5));
      const inkLines = new LineSegments(geo, lineMat(ink, 0.9, [o.scanPlane]));
      faintLines.renderOrder = 1; inkLines.renderOrder = 2;
      g.add(faintLines, inkLines);
      F.lines[cat] = { faint: faintLines, ink: inkLines, color: new Color(cat === 'noise' ? faint : (C[cat] || ink)) };
    }
    for (const [kind, q] of Object.entries(f.pieces)) {
      if (!q.length) continue;
      const [tri, edge] = quadGeometries(q, y + 0.01);
      const glass = kind === 'glass';
      const m = new Mesh(tri, fillMat(glass ? col('glass', '#2f86a8') : col('piece', '#cfc2b0'), 0, [o.sweepPlane]));
      const e = new LineSegments(edge, lineMat(glass ? col('glass', '#2f86a8') : col('pieceEdge', '#8a7a66'), 0, [o.sweepPlane]));
      m.renderOrder = 3; e.renderOrder = 4;
      g.add(m, e);
      F.pieces.push({ m, e, glass });
    }
    for (const [kind, rings] of Object.entries(f.rings)) {
      if (!rings.length) continue;
      const [fill, line] = ringGeometries(rings, y + 0.015);
      const glass = kind === 'glass';
      const m = new Mesh(fill, fillMat(glass ? col('glass', '#2f86a8') : col('run', '#e3ddd3'), 0));
      const e = new LineSegments(line, lineMat(glass ? col('glass', '#2f86a8') : col('runEdge', '#6f675d'), 0));
      m.renderOrder = 5; e.renderOrder = 6;
      g.add(m, e);
      F.runs.push({ m, e, glass });
    }
    f.rec.group.add(g);
    made.floors.push(F);
  }
  return made;
}

/** build_replay.js unmake(): takes the run's objects out of the scene and frees their GPU memory. */
export function unmakeReplayObjects(made: Made, scene: Scene): void {
  scene.remove(made.scan);
  made.scan.geometry.dispose();
  (made.scan.material as MeshBasicMaterial).dispose();
  for (const F of made.floors) {
    F.g.traverse(n => {
      const m = n as Mesh;
      if (m.geometry) m.geometry.dispose();
      const mats = m.material ? (Array.isArray(m.material) ? m.material : [m.material]) : [];
      for (const mat of mats) mat.dispose();
    });
    F.f.rec.group.remove(F.g);
  }
}
