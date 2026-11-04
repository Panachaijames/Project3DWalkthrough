// apply(T): the replay at global progress T, idempotent (port of build_replay.js "the seven steps": setFloorPlace,
// showSolids, setTransparent, fadeLate, apply). Owner: builder D.
// The floors slide from the sheet onto each other and lift to their levels; the drawing's lines are read (a scan bar),
// sorted (coloured, the ignored ones fade), the wall faces paired into pieces, merged into runs, the walls rise (shader
// patch), and the late objects (floor plates, stairs, furniture boxes) and the ground plane fade in at the end.
// The step list, bar and caption are ui.ts's; index.ts calls both.
import type { LineBasicMaterial, Material, Mesh, MeshBasicMaterial, Object3D, Plane } from 'three';
import type { RiseItem, SettingsMap, StepKey } from '../contracts';
import { cameraPath, lowest, sheetBox, stackBox, type Pose, type Rect, type ViewSize } from './camera';
import type { Made, MadeFloor, ReplayColors, ReplayFloorRt } from './objects';
import { ease, span } from './timeline';

/** The materials of an object (none, one or a multi-material list). */
export function materialsOf(n: Object3D): Material[] {
  const m = (n as Mesh).material as Material | Material[] | undefined;
  return m ? (Array.isArray(m) ? m : [m]) : [];
}

/** Switching transparency needs a shader refresh, so only on a change. */
export function setTransparent(m: Material, on: boolean): void {
  if (m.transparent !== on) { m.transparent = on; m.needsUpdate = true; }
}

/** A rising solid as the replay drives it: its edges' own opacity is what they fade back to. */
export interface RiseRt { item: RiseItem; edgeOpacity: number }

/** The late objects' own look (each material's opacity and transparency), recorded before the replay first hides them. */
export type LateLook = WeakMap<Object3D, { opacity: number[]; transparent: boolean[] }>;

/** Records the look of every material-bearing node under the floors' late objects that has none recorded yet. */
export function recordLate(floors: readonly ReplayFloorRt[], look: LateLook): void {
  for (const f of floors) for (const obj of f.rec.late) obj.traverse(n => {
    const mats = materialsOf(n);
    if (!mats.length || look.has(n)) return;
    look.set(n, { opacity: mats.map(m => m.opacity), transparent: mats.map(m => m.transparent) });
  });
}

/** 0 = on the sheet beside the others, at the lowest level; 1 = at its own place and level. */
export function setFloorPlace(F: MadeFloor, floors: readonly ReplayFloorRt[], settings: SettingsMap, slideT: number, liftT: number): void {
  const f = F.f, s = settings[f.key]!, homeY = s.level - f.level;
  const sx = f.sheet[0] * (1 - slideT), sz = -f.sheet[1] * (1 - slideT);
  const sy = homeY + (lowest(floors, settings) - s.level) * (1 - liftT);
  f.rec.group.position.set(sx, sy, sz);
}

/** The floor's solids at rise (0 = not drawn, 1 = full height) and their outlines at edgeT of their own opacity. */
export function showSolids(f: ReplayFloorRt, rises: readonly RiseRt[], rise: number, edgeT: number): void {
  f.u.uRise.value = rise;
  for (const r of rises) {
    r.item.mesh.visible = rise > 0;
    if (r.item.edges) {
      r.item.edges.visible = edgeT > 0;
      for (const m of materialsOf(r.item.edges)) m.opacity = r.edgeOpacity * edgeT;
    }
  }
}

/** The late objects (and the ground plane) at t of their own opacity; hidden at 0. */
export function fadeLate(floors: readonly ReplayFloorRt[], look: LateLook, ground: Mesh | null, t: number): void {
  for (const f of floors) for (const obj of f.rec.late) obj.traverse(n => {
    const mats = materialsOf(n);
    if (!mats.length) return;
    n.visible = t > 0;
    const own = look.get(n);
    mats.forEach((m, i) => {
      setTransparent(m, t < 1 || !!own?.transparent[i]);
      m.opacity = (own?.opacity[i] ?? 1) * t;
    });
  });
  if (ground) {
    ground.visible = t > 0;
    for (const m of materialsOf(ground)) { setTransparent(m, t < 1); m.opacity = t; }
  }
}

/** The hand-over: every late material back to its own transparency, the ground plane opaque (finish()). */
export function restoreLate(floors: readonly ReplayFloorRt[], look: LateLook, ground: Mesh | null): void {
  for (const f of floors) for (const obj of f.rec.late) obj.traverse(n => {
    const own = look.get(n);
    materialsOf(n).forEach((m, i) => setTransparent(m, !!own?.transparent[i]));
  });
  if (ground) {
    ground.visible = true;
    for (const m of materialsOf(ground)) { setTransparent(m, false); m.opacity = 1; }
  }
}

/** Everything apply(T) reads (index.ts owns it). */
export interface ApplyScene {
  made: Made;
  floors: readonly ReplayFloorRt[];
  rises: ReadonlyMap<ReplayFloorRt, readonly RiseRt[]>;
  settings: SettingsMap;
  colors: ReplayColors;
  /** Each step's [t0, t1]. */
  times: Readonly<Record<StepKey, readonly [number, number]>>;
  scanPlane: Plane;
  sweepPlane: Plane;
  look: LateLook;
  ground: Mesh | null;
  /** The root's size and the camera's vertical fov; the free rectangle beside or below the card. */
  view: ViewSize & { fov: number };
  fr: Rect;
  /** The view the replay ends on. */
  final: Pose;
}

/** apply(T) on the scene and the camera; returns the pose to set. Idempotent: the same T gives the same state. */
export function applyScene(T: number, o: ApplyScene): Pose {
  const at = (k: StepKey) => { const t = o.times[k]; return span(T, t[0], t[1]); };
  const tRead = at('read'), tSort = at('sort'), tAlign = at('align'), tPair = at('pair'), tMerge = at('merge'), tRaise = at('raise'), tFin = at('finish');
  const { made, floors, settings } = o;
  const C = o.colors, ink = C.ink ?? '#3b4148';
  const sb = sheetBox(floors, settings, 0), x0 = sb.min.x - 2, x1 = sb.max.x + 2;
  o.scanPlane.constant = x0 + (x1 - x0) * ease(tRead);
  made.scan.visible = tRead > 0 && tRead < 1;
  made.scan.position.set(o.scanPlane.constant, sb.min.y + 0.05, (sb.min.z + sb.max.z) / 2);
  made.scan.scale.set(1, 1, sb.max.z - sb.min.z + 4);
  const ab = stackBox(floors, settings, 0);
  o.sweepPlane.constant = ab.min.x - 1 + (ab.max.x - ab.min.x + 2) * ease(tPair);
  const sorted = ease(tSort);
  made.floors.forEach((F, i) => {
    setFloorPlace(F, floors, settings, ease(span(tAlign, 0, 0.55)), ease(span(tAlign, 0.45, 1)));
    // Lines: faint until read; then ink; sorting colours them and fades the ignored ones;
    // wall and glass lines give way to the pieces and then the walls; stair lines stay until the stairs appear.
    const order = floors.length > 1 ? i / (floors.length - 1) : 0;
    const riseEnd = 0.62 + order * 0.38, rise = ease(span(tRaise, order * 0.38, riseEnd));
    for (const [cat, L] of Object.entries(F.lines)) {
      L.faint.visible = tRead < 1;
      (L.ink.material as LineBasicMaterial).color.set(ink).lerp(L.color, sorted);
      let op: number;
      if (cat === 'noise') op = (0.9 - 0.8 * sorted) * (1 - ease(tFin));
      else if (cat === 'stair') op = 0.9 * (1 - ease(tFin));
      else op = 0.9 * (1 - 0.7 * ease(tPair)) * (1 - rise);
      (L.ink.material as LineBasicMaterial).opacity = Math.max(0, op);
      L.ink.visible = op > 0.003;
    }
    for (const p of F.pieces) {
      const op = ease(tPair) * (1 - ease(tMerge));
      (p.m.material as MeshBasicMaterial).opacity = (p.glass ? 0.55 : 0.95) * op; (p.e.material as LineBasicMaterial).opacity = 0.9 * op;
      p.m.visible = p.e.visible = op > 0.003;
    }
    for (const r of F.runs) {
      const op = ease(tMerge) * (1 - rise);
      (r.m.material as MeshBasicMaterial).opacity = (r.glass ? 0.6 : 1) * op; (r.e.material as LineBasicMaterial).opacity = op;
      r.m.visible = r.e.visible = op > 0.003;
    }
    showSolids(F.f, o.rises.get(F.f) ?? [], rise, ease(span(tRaise, riseEnd - 0.12, riseEnd)));
  });
  fadeLate(floors, o.look, o.ground, ease(tFin));
  return cameraPath({ floors, settings, view: o.view, fr: o.fr, final: o.final, tAlign, tRaise, tFin, ease, span });
}
