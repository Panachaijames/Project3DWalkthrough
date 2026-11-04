// @vitest-environment happy-dom
// Fix step (review finding "parity-cad" 2): the Orbit zoom per wheel, pinch and middle-drag step of three 0.160's
// OrbitControls (the prototype pages) on three 0.186's: 0.95 ^ (|deltaY| / (100 * (devicePixelRatio | 0))), no pinch factor.
import { PerspectiveCamera } from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { afterEach, describe, expect, it } from 'vitest';
import { prototypeWheel, prototypeZoomScale, usePrototypeZoom } from '../../../src/core/controls';

const live: OrbitControls[] = [];
afterEach(() => { for (const c of live.splice(0)) c.dispose(); document.body.innerHTML = ''; });

function orbit(dpr = 1, prototype = true) {
  const canvas = document.createElement('canvas');
  document.body.append(canvas);
  const camera = new PerspectiveCamera(40, 1.5, 0.1, 1000);
  camera.position.set(0, 0, 50);
  const controls = new OrbitControls(camera, canvas);
  live.push(controls);
  if (prototype) expect(usePrototypeZoom(controls, () => dpr)).toBe(true);
  controls.update();
  const distance = () => camera.position.distanceTo(controls.target);
  const wheel = (deltaY: number, init: WheelEventInit = {}) => {
    const e = new WheelEvent('wheel', { deltaY, clientX: 400, clientY: 300, bubbles: true, cancelable: true, ...init });
    // happy-dom 21's WheelEvent leaves the modifier keys out of its init (ctrlKey undefined): set it as Edge does
    if (init.ctrlKey && !e.ctrlKey) Object.defineProperty(e, 'ctrlKey', { value: true });
    return canvas.dispatchEvent(e);
  };
  return { controls, distance, wheel };
}

describe('the Orbit zoom of the prototype pages (three 0.160 OrbitControls)', () => {
  it('a touchpad pinch (wheel with ctrlKey, Ctrl not held): 10 steps of -5 zoom x0.975, not x0.774', () => {
    const o = orbit();
    const d0 = o.distance();
    for (let i = 0; i < 10; i++) o.wheel(-5, { ctrlKey: true });
    expect(o.distance() / d0).toBeCloseTo(Math.pow(0.95, 0.5), 6);           // 0.9747, the page's
    const three = orbit(1, false);                                             // three 0.186 as it is
    for (let i = 0; i < 10; i++) three.wheel(-5, { ctrlKey: true });
    expect(three.distance() / d0).toBeCloseTo(Math.pow(0.95, 5), 6);           // 0.7738: the faster pinch
  });

  it('a mouse notch: x0.95 at devicePixelRatio 1 and 1.25 (as three 0.186), x0.975 at 2 (three 0.186: x0.95)', () => {
    for (const [dpr, want] of [[1, 0.95], [1.25, 0.95], [2, Math.pow(0.95, 0.5)], [0.9, 0.95]] as const) {
      const o = orbit(dpr);
      const d0 = o.distance();
      o.wheel(-100);
      expect(o.distance() / d0, `dpr ${dpr}`).toBeCloseTo(want, 6);
      o.wheel(100);                                                            // and back out by the same factor
      expect(o.distance() / d0, `dpr ${dpr}`).toBeCloseTo(1, 6);
    }
  });

  it('line and page wheels keep three 0.186 scaling (16 and 100 pixels a step)', () => {
    expect(prototypeWheel({ clientX: 1, clientY: 2, deltaY: 3, deltaMode: 1 })).toEqual({ clientX: 1, clientY: 2, deltaY: 48 });
    expect(prototypeWheel({ clientX: 0, clientY: 0, deltaY: -1, deltaMode: 2 }).deltaY).toBe(-100);
    expect(prototypeWheel({ clientX: 0, clientY: 0, deltaY: -5, deltaMode: 0 }).deltaY).toBe(-5);
    expect(prototypeZoomScale(-100, 1, 2)).toBeCloseTo(Math.pow(0.95, 0.5), 9);
    expect(prototypeZoomScale(100, 2, 1)).toBeCloseTo(Math.pow(0.95, 2), 9);
  });
});
