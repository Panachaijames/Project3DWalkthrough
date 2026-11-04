// The prototypes' Orbit zoom (three 0.160 OrbitControls) on three 0.186's OrbitControls. Owner: A (fix step, review
// finding "parity-cad" 2).
//
// three 0.160: one wheel event zooms by 0.95 ^ (zoomSpeed * |deltaY| / (100 * (devicePixelRatio | 0))), the same for a
// mouse notch, a two-finger scroll and a touchpad pinch (which Edge sends as a wheel event with ctrlKey set), and the
// middle-button drag uses the same scale. three 0.186 divides by 100 whatever the pixel ratio (twice as far on a 2x
// screen) and multiplies a ctrl+wheel by 10 when Ctrl is not physically held (a pinch: about ten times as far, in log
// terms, on the owner's touchpad). Both differences are taken out here, per instance (no prototype patching): the wheel
// event keeps only 0.186's line / page mode scaling (Firefox's line-mode wheels; Edge always sends pixels), and the zoom
// scale is 0.160's, with the pixel ratio below 1 (a zoomed-out page) read as 1 (0.160 divided by zero there).
import type { OrbitControls } from 'three/addons/controls/OrbitControls.js';

/** The private OrbitControls methods this replaces (three 0.186.1: examples/jsm/controls/OrbitControls.js). */
interface ZoomInternals {
  zoomSpeed: number;
  _customWheelEvent?: (event: WheelEvent) => { clientX: number; clientY: number; deltaY: number };
  _getZoomScale?: (delta: number) => number;
}

const pixelRatio = () => (typeof devicePixelRatio === 'number' && devicePixelRatio > 0 ? devicePixelRatio : 1);

/** three 0.160's zoom scale of one wheel step (or one middle-drag move) of `delta` pixels. */
export function prototypeZoomScale(delta: number, zoomSpeed: number, dpr: number): number {
  return Math.pow(0.95, zoomSpeed * Math.abs(delta) / (100 * Math.max(1, Math.floor(dpr))));
}

/** The wheel event OrbitControls zooms by: the deltaY in pixels (line and page modes scaled as three 0.186 does), no
 * pinch factor. */
export function prototypeWheel(event: Pick<WheelEvent, 'clientX' | 'clientY' | 'deltaY' | 'deltaMode'>): { clientX: number; clientY: number; deltaY: number } {
  const k = event.deltaMode === 1 ? 16 : event.deltaMode === 2 ? 100 : 1;
  return { clientX: event.clientX, clientY: event.clientY, deltaY: event.deltaY * k };
}

/** Gives `controls` the prototypes' zoom per wheel, pinch and middle-drag step. Returns false when this three's
 * OrbitControls does not have the two methods it replaces (a three upgrade: the unit test then fails too). */
export function usePrototypeZoom(controls: OrbitControls, dpr: () => number = pixelRatio): boolean {
  const c = controls as unknown as ZoomInternals;
  if (typeof c._customWheelEvent !== 'function' || typeof c._getZoomScale !== 'function') return false;
  c._customWheelEvent = prototypeWheel;
  c._getZoomScale = (delta: number) => prototypeZoomScale(delta, c.zoomSpeed, dpr());
  return true;
}
