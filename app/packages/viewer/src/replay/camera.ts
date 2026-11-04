// Camera framing of the replay (port of build_replay.js "camera framing": freeRect, pose, DOWN / NORTH, dirAt,
// sheetBox, stackBox, lowest, lerpPose, setPose). Owner: builder D.
// Root-relative (DESIGN.md 11.5): the sizes are the viewer root's (ctx.size()) and the card's rectangle is relative to the
// root (ctx.rectOf), never the window's, so the replay frames the model the same full-window (offline) and below the
// staff app's bar. Pure three.js maths: Node-testable.
import { Box3, Vector3 } from 'three';
import type { SettingsMap, Vec2 } from '../contracts';
import type { PlanBox } from './objects';

export const D2R = Math.PI / 180;

export interface Pose { pos: Vector3; target: Vector3 }
export interface Rect { x: number; y: number; w: number; h: number }
export interface ViewSize { width: number; height: number }

/** Straight down, north at the top of the screen. */
export const DOWN = new Vector3(0, -1, -0.002).normalize();
/** The heading of that top view. */
export const NORTH = Math.atan2(DOWN.x, DOWN.z);
/** The tilt (degrees down from level) of the oblique view while the floors line up. */
export const TILT = 52;
/** Room kept for the caption at the bottom while it shows, else a small margin (px). */
export const CAPTION_ROOM = 86;
export const NO_CAPTION_ROOM = 16;

/**
 * The part of the root the model is framed in: right of the Build card when the card sits in the left part of the root
 * (its right edge before 55 % of the width), else below it; the bottom leaves room for the caption.
 * `card` is the card's root-relative rectangle, or null when it is hidden.
 */
export function freeRect(size: ViewSize, card: { right: number; bottom: number; width: number } | null, captionShown: boolean): Rect {
  const W = size.width, H = size.height, subH = captionShown ? CAPTION_ROOM : NO_CAPTION_ROOM;
  if (!card || !card.width) return { x: 0, y: 0, w: W, h: H - subH };
  if (card.right < W * 0.55) return { x: card.right + 8, y: 8, w: Math.max(80, W - card.right - 16), h: H - subH - 8 };
  return { x: 0, y: card.bottom + 8, w: W, h: Math.max(80, H - card.bottom - 8 - subH) };
}

/**
 * A camera looking along `dir` at `box` so that the box's picture fills the free rectangle: projects the 8 corners (so
 * perspective is exact), searches the distance (36 steps between 0.5 and 20000 m, geometric) and centres the picture.
 * `fov` is the camera's vertical field of view (degrees) over the root's height.
 */
export function pose(box: Box3, dir: Vector3, view: ViewSize & { fov: number }, fr: Rect, pad = 1.08): Pose & { w: number; h: number } {
  const W = view.width, H = view.height;
  const k = 2 * Math.tan(view.fov * D2R / 2) / H;           // world size of one pixel, per metre of distance
  const c = box.getCenter(new Vector3());
  const right = new Vector3().crossVectors(dir, new Vector3(0, 1, 0)).normalize();
  const up = new Vector3().crossVectors(right, dir).normalize();
  const corners = [...Array(8)].map((_, i) => new Vector3(i & 1 ? box.max.x : box.min.x, i & 2 ? box.max.y : box.min.y, i & 4 ? box.max.z : box.min.z));
  const cx = fr.x + fr.w / 2, cy = fr.y + fr.h / 2;
  function place(dist: number): Pose & { w: number; h: number } {
    const target = c.clone();
    let w = 0, h = 0;
    for (let it = 0; it < 3; it++) {
      const pos = target.clone().addScaledVector(dir, -dist);
      let x0 = Infinity, x1 = -Infinity, y0 = Infinity, y1 = -Infinity;
      for (const p of corners) {
        const v = p.clone().sub(pos), z = Math.max(0.05, v.dot(dir));
        const sx = W / 2 + v.dot(right) / (z * k), sy = H / 2 - v.dot(up) / (z * k);
        x0 = Math.min(x0, sx); x1 = Math.max(x1, sx); y0 = Math.min(y0, sy); y1 = Math.max(y1, sy);
      }
      w = x1 - x0; h = y1 - y0;
      const px = dist * k;
      target.addScaledVector(right, ((x0 + x1) / 2 - cx) * px).addScaledVector(up, -((y0 + y1) / 2 - cy) * px);
    }
    return { pos: target.clone().addScaledVector(dir, -dist), target, w, h };
  }
  let lo = 0.5, hi = 20000;
  for (let i = 0; i < 36; i++) {
    const mid = Math.sqrt(lo * hi), p = place(mid);
    if (p.w * pad <= fr.w && p.h * pad <= fr.h) hi = mid; else lo = mid;
  }
  return place(hi);
}

/** A view direction from a heading and an elevation (degrees down from level). */
export function dirAt(az: number, elevDeg: number): Vector3 {
  const el = elevDeg * D2R;
  return new Vector3(Math.sin(az) * Math.cos(el), -Math.sin(el), Math.cos(az) * Math.cos(el));
}

export function lerpPose(a: Pose, b: Pose, t: number): Pose {
  return { pos: a.pos.clone().lerp(b.pos, t), target: a.target.clone().lerp(b.target, t) };
}

/** The floors as the camera framing sees them. */
export interface FramedFloor { key: string; b: PlanBox; sheet: Vec2 }

/** The lowest level of the settings. */
export function lowest(floors: readonly FramedFloor[], settings: SettingsMap): number {
  return Math.min(...floors.map(f => settings[f.key]?.level ?? 0));
}

/** Where the drawings are: side by side on the sheet (alignT 0) or lined up (1), at the lowest level. */
export function sheetBox(floors: readonly FramedFloor[], settings: SettingsMap, alignT: number): Box3 {
  const b = new Box3(), y = lowest(floors, settings);
  for (const f of floors) {
    const dx = f.sheet[0] * (1 - alignT), dy = f.sheet[1] * (1 - alignT);
    b.expandByPoint(new Vector3(f.b.x0 + dx, y, -(f.b.y1 + dy)));
    b.expandByPoint(new Vector3(f.b.x1 + dx, y, -(f.b.y0 + dy)));
  }
  return b;
}

/** The lined-up floors, flat (0) up to with their full walls (1). */
export function stackBox(floors: readonly FramedFloor[], settings: SettingsMap, wallsT: number): Box3 {
  const b = new Box3();
  for (const f of floors) {
    const s = settings[f.key] ?? { level: 0, height: 0 };
    b.expandByPoint(new Vector3(f.b.x0, s.level, -f.b.y1));
    b.expandByPoint(new Vector3(f.b.x1, s.level + Math.max(0.1, s.height * wallsT), -f.b.y0));
  }
  return b;
}

/** The view direction of a pose. */
export const poseDir = (p: Pose): Vector3 => p.target.clone().sub(p.pos).normalize();

/**
 * The camera path of apply(T) (build_replay.js): the sheet from above -> the lined-up plan -> tilted towards north (no
 * turn yet) -> turning round to the usual heading while the walls rise -> the usual view. Turning only while tilted
 * avoids a fast spin near the top view. t* are the steps' local progress (0..1); `final` is the view to end on.
 */
export function cameraPath(o: {
  floors: readonly FramedFloor[]; settings: SettingsMap; view: ViewSize & { fov: number }; fr: Rect; final: Pose;
  tAlign: number; tRaise: number; tFin: number; ease: (t: number) => number; span: (t: number, a: number, b: number) => number;
}): Pose {
  const { floors, settings, view, fr, final, tAlign, tRaise, tFin, ease, span } = o;
  const top0 = pose(sheetBox(floors, settings, 0), DOWN, view, fr), top1 = pose(sheetBox(floors, settings, 1), DOWN, view, fr);
  const fd = poseDir(final), azF = Math.atan2(fd.x, fd.z), elF = Math.max(20, Math.min(60, Math.asin(-fd.y) / D2R));
  const turn = Math.atan2(Math.sin(azF - NORTH), Math.cos(azF - NORTH));          // the short way round
  const obl = pose(stackBox(floors, settings, 0), dirAt(NORTH, TILT), view, fr);
  const fin: Pose = { pos: final.pos.clone(), target: final.target.clone() };
  let p: Pose = top0;
  if (tAlign > 0) p = lerpPose(top0, top1, ease(span(tAlign, 0, 0.5)));
  if (tAlign > 0.5) p = lerpPose(top1, obl, ease(span(tAlign, 0.5, 1)));
  if (tRaise > 0) { const e = ease(tRaise); p = pose(stackBox(floors, settings, e), dirAt(NORTH + turn * e, TILT + (elF - TILT) * e), view, fr); }
  if (tFin > 0) p = lerpPose(pose(stackBox(floors, settings, 1), dirAt(NORTH + turn, elF), view, fr), fin, ease(tFin));
  return p;
}
