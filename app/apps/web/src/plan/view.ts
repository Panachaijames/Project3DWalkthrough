// The canvas view (docs/upload/DESIGN.md U-12.1): pan, zoom at the pointer, fit. Owner U7. Pure maths, no DOM.
// A view is the local point (quanta from the plan's origin) at the middle of the canvas and the scale in CSS pixels per
// quantum. Screen y points down, sheet y up. The canvas transform maps quanta straight to device pixels, so paths stay
// in small integers (U-12.1 "local frame") and line widths are given in screen pixels divided by the scale.
import type { QBox } from './decode';

export interface View {
  /** The local point (quanta) at the middle of the canvas. */
  cx: number;
  cy: number;
  /** CSS pixels per quantum (1 cm). */
  s: number;
}

export interface Size { w: number; h: number }

/** The closest zoom: 40 px per centimetre. */
export const MAX_SCALE = 40;
/** Pixels kept free round a fitted box. */
export const FIT_MARGIN = 24;

/** The view that shows `box` whole and centred, `margin` px free on every side. */
export function fitView(box: QBox, size: Size, margin = FIT_MARGIN): View {
  const bw = Math.max(1, box[2] - box[0]), bh = Math.max(1, box[3] - box[1]);
  const w = Math.max(1, size.w - 2 * margin), h = Math.max(1, size.h - 2 * margin);
  const s = Math.min(MAX_SCALE, w / bw, h / bh);
  return { cx: (box[0] + box[2]) / 2, cy: (box[1] + box[3]) / 2, s };
}

/** The zoom range for a plan: from a quarter of what fits the whole plan (at least 1 px per 10 km) to MAX_SCALE. */
export function scaleLimits(bounds: QBox | null, size: Size): { min: number; max: number } {
  const fit = bounds ? fitView(bounds, size).s : 1;
  return { min: Math.max(1e-6, Math.min(fit / 4, MAX_SCALE / 8)), max: MAX_SCALE };
}

export const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v));

/** Zooms by `factor` keeping the local point under the screen point (px, py) where it is. */
export function zoomAt(v: View, size: Size, px: number, py: number, factor: number, limits?: { min: number; max: number }): View {
  const s = limits ? clamp(v.s * factor, limits.min, limits.max) : v.s * factor;
  const [qx, qy] = toLocal(v, size, px, py);
  // keep (qx, qy) at (px, py): px = (qx - cx) s + w / 2
  return { cx: qx - (px - size.w / 2) / s, cy: qy + (py - size.h / 2) / s, s };
}

/** Moves the drawing by (dx, dy) screen pixels (a drag to the right moves the drawing to the right). */
export function panBy(v: View, dx: number, dy: number): View {
  return { cx: v.cx - dx / v.s, cy: v.cy + dy / v.s, s: v.s };
}

/** Screen pixels (CSS, from the canvas's top-left corner) of a local point. */
export function toScreen(v: View, size: Size, qx: number, qy: number): [number, number] {
  return [(qx - v.cx) * v.s + size.w / 2, (v.cy - qy) * v.s + size.h / 2];
}

/** The local point (quanta) under a screen point. */
export function toLocal(v: View, size: Size, px: number, py: number): [number, number] {
  return [v.cx + (px - size.w / 2) / v.s, v.cy - (py - size.h / 2) / v.s];
}

/** The canvas transform (setTransform a, b, c, d, e, f) from quanta to device pixels. */
export function canvasTransform(v: View, size: Size, dpr: number): [number, number, number, number, number, number] {
  const k = v.s * dpr;
  return [k, 0, 0, -k, (size.w / 2 - v.cx * v.s) * dpr, (size.h / 2 + v.cy * v.s) * dpr];
}

/** The local box the canvas shows. */
export function visibleBox(v: View, size: Size): QBox {
  const hw = size.w / 2 / v.s, hh = size.h / 2 / v.s;
  return [v.cx - hw, v.cy - hh, v.cx + hw, v.cy + hh];
}

/** A box (quanta) from two screen corners in any order. */
export function boxFromScreen(v: View, size: Size, ax: number, ay: number, bx: number, by: number): QBox {
  const [x0, y0] = toLocal(v, size, Math.min(ax, bx), Math.max(ay, by));
  const [x1, y1] = toLocal(v, size, Math.max(ax, bx), Math.min(ay, by));
  return [x0, y0, x1, y1];
}

/** The zoom factor of one wheel event: a notch (100 px) zooms by about 1.16. */
export function wheelFactor(deltaY: number, deltaMode: number, pageHeight: number): number {
  const px = deltaMode === 1 ? deltaY * 16 : deltaMode === 2 ? deltaY * pageHeight : deltaY;
  return Math.exp(-clamp(px, -600, 600) * 0.0015);
}

export function sameView(a: View, b: View): boolean {
  return a.cx === b.cx && a.cy === b.cy && a.s === b.s;
}
