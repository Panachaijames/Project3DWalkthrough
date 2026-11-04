// Builder D: the replay's camera framing (build_replay.js freeRect, pose, DOWN / NORTH, dirAt, sheetBox, stackBox,
// lerpPose), root-relative: the free rectangle beside or below the card, a pose that fits a box into it (the 8 corners
// projected with the real camera land inside it, within the 1.08 pad), and the camera path of apply(T).
import { Box3, PerspectiveCamera, Vector3 } from 'three';
import { describe, expect, it } from 'vitest';
import {
  cameraPath, D2R, dirAt, DOWN, freeRect, lerpPose, lowest, NORTH, pose, poseDir, sheetBox, stackBox, type FramedFloor, type Rect,
} from '../../../src/replay/camera';
import { ease, span } from '../../../src/replay/timeline';

const size = { width: 1400, height: 880 };

/** The screen rectangle the box's corners take with a camera at the pose (fov over the height). */
function screenBox(box: Box3, p: { pos: Vector3; target: Vector3 }, fov: number, w = size.width, h = size.height) {
  const cam = new PerspectiveCamera(fov, w / h, 0.1, 100000);
  cam.position.copy(p.pos); cam.lookAt(p.target); cam.updateMatrixWorld(); cam.updateProjectionMatrix();
  let x0 = Infinity, x1 = -Infinity, y0 = Infinity, y1 = -Infinity;
  for (let i = 0; i < 8; i++) {
    const v = new Vector3(i & 1 ? box.max.x : box.min.x, i & 2 ? box.max.y : box.min.y, i & 4 ? box.max.z : box.min.z).project(cam);
    const x = (v.x + 1) / 2 * w, y = (1 - v.y) / 2 * h;
    x0 = Math.min(x0, x); x1 = Math.max(x1, x); y0 = Math.min(y0, y); y1 = Math.max(y1, y);
  }
  return { x0, x1, y0, y1 };
}
const inside = (s: { x0: number; x1: number; y0: number; y1: number }, r: Rect, tol = 1) =>
  s.x0 >= r.x - tol && s.x1 <= r.x + r.w + tol && s.y0 >= r.y - tol && s.y1 <= r.y + r.h + tol;

describe('freeRect', () => {
  it('is the whole root (less the caption room) when the card is hidden or has no size', () => {
    expect(freeRect(size, null, false)).toEqual({ x: 0, y: 0, w: 1400, h: 864 });
    expect(freeRect(size, null, true)).toEqual({ x: 0, y: 0, w: 1400, h: 794 });
    expect(freeRect(size, { right: 0, bottom: 0, width: 0 }, true)).toEqual({ x: 0, y: 0, w: 1400, h: 794 });
  });
  it('is right of the card when the card sits in the left 55 %, else below it', () => {
    expect(freeRect(size, { right: 372, bottom: 700, width: 360 }, false)).toEqual({ x: 380, y: 8, w: 1012, h: 856 });
    expect(freeRect(size, { right: 372, bottom: 700, width: 360 }, true)).toEqual({ x: 380, y: 8, w: 1012, h: 786 });
    expect(freeRect({ width: 600, height: 900 }, { right: 588, bottom: 400, width: 576 }, false)).toEqual({ x: 0, y: 408, w: 600, h: 476 });
    expect(freeRect({ width: 600, height: 500 }, { right: 588, bottom: 480, width: 576 }, true).h).toBe(80);
  });
});

describe('pose', () => {
  const box = new Box3(new Vector3(-12, 0, -9), new Vector3(15, 7.4, 8));
  const fr = freeRect(size, { right: 372, bottom: 700, width: 360 }, false);

  it('fits the box into the free rectangle from above (DOWN) and obliquely, centred in it', () => {
    for (const dir of [DOWN, dirAt(NORTH, 52), dirAt(NORTH + 2, 30)]) {
      const p = pose(box, dir, { ...size, fov: 40 }, fr);
      const s = screenBox(box, p, 40);
      expect(inside(s, fr)).toBe(true);
      // tight: it would not fit with 3 % more (the search stops within the 1.08 pad)
      expect(Math.max((s.x1 - s.x0) / fr.w, (s.y1 - s.y0) / fr.h)).toBeGreaterThan(1 / 1.08 - 0.03);
      // centred (three passes of the prototype: within 2 % of the free rectangle on oblique views)
      expect(Math.abs((s.x0 + s.x1) / 2 - (fr.x + fr.w / 2))).toBeLessThan(fr.w * 0.02);
      expect(Math.abs((s.y0 + s.y1) / 2 - (fr.y + fr.h / 2))).toBeLessThan(fr.h * 0.02);
      expect(poseDir(p).angleTo(dir)).toBeLessThan(1e-6);
    }
  });

  it('looks straight down with north at the top (DOWN, NORTH)', () => {
    expect(DOWN.length()).toBeCloseTo(1, 12);
    expect(DOWN.y).toBeLessThan(-0.99999);
    expect(NORTH).toBeCloseTo(Math.PI, 12);
    const d = dirAt(NORTH, 52);
    expect(Math.asin(-d.y) / D2R).toBeCloseTo(52, 9);
    expect(Math.atan2(d.x, d.z)).toBeCloseTo(Math.atan2(Math.sin(NORTH), Math.cos(NORTH)), 9);
    const a = { pos: new Vector3(0, 0, 0), target: new Vector3(0, 0, -1) }, b = { pos: new Vector3(10, 0, 0), target: new Vector3(10, 0, -1) };
    expect(lerpPose(a, b, 0.25).pos.x).toBeCloseTo(2.5, 12);
  });
});

describe('sheetBox / stackBox', () => {
  const floors: FramedFloor[] = [
    { key: 'ground', b: { x0: -10, x1: 10, y0: -5, y1: 5 }, sheet: [0, 0] },
    { key: 'upper', b: { x0: -8, x1: 9, y0: -4, y1: 4 }, sheet: [74.021, 0] },
  ];
  const settings = { ground: { level: 0.9, height: 3.9 }, upper: { level: 4.8, height: 3.5 } };

  it('has the drawings side by side on the sheet (0) or lined up (1), at the lowest level', () => {
    expect(lowest(floors, settings)).toBe(0.9);
    const s0 = sheetBox(floors, settings, 0), s1 = sheetBox(floors, settings, 1);
    expect(s0.min.toArray()).toEqual([-10, 0.9, -5]);
    expect(s0.max.x).toBeCloseTo(9 + 74.021, 9);
    expect(s1.max.x).toBe(10);
    expect(s1.min.y).toBe(0.9);
  });

  it('stacks the floors flat (0, 0.1 m) or with their walls (1)', () => {
    const k0 = stackBox(floors, settings, 0), k1 = stackBox(floors, settings, 1);
    expect(k0.max.y).toBeCloseTo(4.9, 9);
    expect(k1.max.y).toBeCloseTo(8.3, 9);
    expect(k1.min.toArray()).toEqual([-10, 0.9, -5]);
  });

  it('camera path: from above at 0, tilted towards north without turning while the floors line up, on the final view at 1', () => {
    const final = { pos: new Vector3(-28, 30, 34), target: new Vector3(0, 3, 0) };
    const fr = freeRect(size, { right: 372, bottom: 700, width: 360 }, true);
    const view = { ...size, fov: 40 };
    const at = (tAlign: number, tRaise: number, tFin: number) => cameraPath({ floors, settings, view, fr, final, tAlign, tRaise, tFin, ease, span });
    expect(poseDir(at(0, 0, 0)).angleTo(DOWN)).toBeLessThan(1e-6);
    const az = (p: { pos: Vector3; target: Vector3 }) => { const d = poseDir(p); return Math.atan2(d.x, d.z); };
    const turn = (a: number, b: number) => Math.abs(Math.atan2(Math.sin(a - b), Math.cos(a - b))) / D2R;
    // while the floors line up (the second half of the align step) the heading stays north
    expect(turn(az(at(0.6, 0, 0)), NORTH)).toBeLessThan(0.5);
    expect(turn(az(at(0.8, 0, 0)), NORTH)).toBeLessThan(0.5);
    expect(turn(az(at(1, 0, 0)), NORTH)).toBeLessThan(0.5);
    const end = at(1, 1, 1);
    expect(end.pos.distanceTo(final.pos)).toBeLessThan(1e-9);
    expect(end.target.distanceTo(final.target)).toBeLessThan(1e-9);
    // half way through the rise it has turned part of the way to the final heading
    const azF = az(final);
    expect(turn(az(at(1, 0.5, 0)), azF)).toBeLessThan(turn(NORTH, azF));
  });
});
