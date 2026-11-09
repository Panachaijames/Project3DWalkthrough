// U7: view.ts (docs/upload/DESIGN.md U-12.1; ACCEPTANCE 2.3 U7 "view.ts (pan / zoom maths, fit)").
import { describe, expect, it } from 'vitest';
import {
  boxFromScreen, canvasTransform, fitView, MAX_SCALE, panBy, scaleLimits, toLocal, toScreen, visibleBox, wheelFactor, zoomAt,
} from '@/plan/view';

const size = { w: 1400, h: 880 };
const close = (a: number[], b: number[], digits = 9) => a.forEach((v, i) => expect(v).toBeCloseTo(b[i]!, digits));

describe('fit', () => {
  it('centres the box and fits its longer side (relative to the canvas) inside a 24 px margin', () => {
    const v = fitView([0, 0, 2000, 1000], size);            // 20 x 10 m in quanta
    expect(v.cx).toBe(1000); expect(v.cy).toBe(500);
    expect(v.s).toBeCloseTo((1400 - 48) / 2000, 12);       // width limits: 1352 / 2000 < 832 / 1000
    const [x0, y1] = toScreen(v, size, 0, 0), [x1, y0] = toScreen(v, size, 2000, 1000);
    expect(x0).toBeCloseTo(24, 9); expect(x1).toBeCloseTo(1376, 9);
    expect(y0).toBeGreaterThanOrEqual(24); expect(y1).toBeLessThanOrEqual(856);
    expect((y0 + y1) / 2).toBeCloseTo(440, 9);
  });

  it('a tall box fits its height; a box with no area does not divide by zero and never zooms past the closest zoom', () => {
    const v = fitView([0, 0, 100, 5000], size);
    expect(v.s).toBeCloseTo(832 / 5000, 12);
    const p = fitView([7, 7, 7, 7], size);
    expect(p.s).toBe(MAX_SCALE);
    expect([p.cx, p.cy]).toEqual([7, 7]);
  });
});

describe('screen <-> local', () => {
  const v = { cx: 12345.5, cy: -678.25, s: 0.37 };
  it('toScreen and toLocal are inverses; screen y points down, sheet y up', () => {
    for (const [qx, qy] of [[0, 0], [12345.5, -678.25], [-50000, 90000], [1e6, -1e6]] as const) {
      const [px, py] = toScreen(v, size, qx, qy);
      close(toLocal(v, size, px, py), [qx, qy], 6);
    }
    expect(toScreen(v, size, v.cx, v.cy)).toEqual([700, 440]);
    const [, yUp] = toScreen(v, size, v.cx, v.cy + 100);
    expect(yUp).toBeLessThan(440);
  });

  it('the canvas transform maps quanta to device pixels like toScreen x the pixel ratio', () => {
    for (const dpr of [1, 1.5, 2]) {
      const [a, b, c, dd, e, f] = canvasTransform(v, size, dpr);
      expect([b, c]).toEqual([0, 0]);
      for (const [qx, qy] of [[0, 0], [12000, -500], [13000, -900]] as const) {
        const [px, py] = toScreen(v, size, qx, qy);
        expect(a * qx + c * qy + e).toBeCloseTo(px * dpr, 6);
        expect(b * qx + dd * qy + f).toBeCloseTo(py * dpr, 6);
      }
    }
  });

  it('the visible box is what the canvas shows; a screen box comes back ordered', () => {
    const vb = visibleBox(v, size);
    close(toScreen(v, size, vb[0], vb[1]), [0, 880], 6);
    close(toScreen(v, size, vb[2], vb[3]), [1400, 0], 6);
    const b = boxFromScreen(v, size, 900, 100, 300, 700);
    expect(b[0]).toBeLessThan(b[2]); expect(b[1]).toBeLessThan(b[3]);
    close(toScreen(v, size, b[0], b[1]), [300, 700], 6);
    close(toScreen(v, size, b[2], b[3]), [900, 100], 6);
  });
});

describe('pan and zoom', () => {
  const v = { cx: 500, cy: 500, s: 0.5 };
  it('a drag moves the drawing with the pointer', () => {
    const p = panBy(v, 100, -40);
    const [x, y] = toScreen(p, size, 500, 500);
    expect([x, y]).toEqual([800, 400]);
    expect(p.s).toBe(v.s);
  });

  it('zooming keeps the local point under the pointer where it is', () => {
    for (const [px, py, f] of [[100, 100, 2], [1300, 850, 0.5], [700, 440, 1.7], [0, 880, 1 / 3]] as const) {
      const before = toLocal(v, size, px, py);
      const z = zoomAt(v, size, px, py, f);
      expect(z.s).toBeCloseTo(v.s * f, 12);
      close(toLocal(z, size, px, py), before, 6);
    }
  });

  it('zoom is held to its limits, and the point under the pointer still stays put', () => {
    const lim = { min: 0.1, max: 2 };
    const z = zoomAt(v, size, 200, 300, 100, lim);
    expect(z.s).toBe(2);
    close(toLocal(z, size, 200, 300), toLocal(v, size, 200, 300), 6);
    expect(zoomAt(v, size, 200, 300, 0.0001, lim).s).toBe(0.1);
  });

  it('limits: from a quarter of what fits the plan to 40 px per centimetre', () => {
    const lim = scaleLimits([0, 0, 2000, 1000], size);
    expect(lim.max).toBe(MAX_SCALE);
    expect(lim.min).toBeCloseTo(fitView([0, 0, 2000, 1000], size).s / 4, 12);
    expect(scaleLimits(null, size).min).toBeGreaterThan(0);
  });

  it('the wheel: down zooms out, up zooms in, by about 1.16 a notch; lines and pages count as pixels; a burst is capped', () => {
    expect(wheelFactor(100, 0, 880)).toBeCloseTo(Math.exp(-0.15), 12);
    expect(wheelFactor(-100, 0, 880)).toBeGreaterThan(1);
    expect(wheelFactor(3, 1, 880)).toBeCloseTo(Math.exp(-48 * 0.0015), 12);
    expect(wheelFactor(1, 2, 880)).toBeCloseTo(Math.exp(-600 * 0.0015), 12);
    expect(wheelFactor(1e6, 0, 880)).toBeCloseTo(Math.exp(-0.9), 12);
  });
});
