// Builder B: the pure lens, frame, photo-size and photo-name maths of modes/camera.ts and modes/photo.ts (DESIGN.md 13
// "Camera", "Photos"; 17.2 modes), against the prototype's numbers (viewer-modes/viewer_modes.js, test_viewers.mjs).
import { describe, expect, it } from 'vitest';
import type { FrameRectInput, PhotoFrame } from '../../../src/contracts';
import { clampPitch, frameRatio, frameRect, isNarrow, lensFov, outSize, shiftPx, viewFov, wideAngle } from '../../../src/modes/camera';
import { photoName } from '../../../src/modes/photo';
import { D2R } from '../../../src/modes/state';

const desk = { width: 1400, height: 880 };
const input = (o: Partial<FrameRectInput>): FrameRectInput => ({
  frame: '3:2', camOpen: false, mode: 'orbit', touch: false, narrow: false, canvas: desk, camPanel: null, sidePanel: null, ...o,
});
// The panels as the pages lay them out at 1400 x 880: the side panel 12 + 360 px wide (330 + 28 + 2, content-box), the
// Camera panel 300 px wide (270 + 28 + 2) 12 px from the right.
const camPanel = { left: 1400 - 12 - 300, bottom: 600 };
const sidePanel = { right: 12 + 360, width: 360 };

describe('lensFov / viewFov / wideAngle', () => {
  it('lensFov(mm) = 2 atan(12 / mm), the short side of a 36 x 24 mm frame', () => {
    expect(lensFov(24)).toBeCloseTo(2 * Math.atan(0.5) / D2R, 12);
    expect(lensFov(50)).toBeCloseTo(26.991466561591, 9);
    expect(lensFov(12)).toBeCloseTo(90, 12);
    expect(lensFov(33)).toBeCloseTo(39.96621304379996, 9);   // Orbit: the camera's 40 degrees as a lens (33 mm), as captured
  });

  it('viewFov: landscape keeps the lens on the height; portrait spans the width (the phone check)', () => {
    expect(viewFov(24, 1400 / 880)).toBe(lensFov(24));
    expect(viewFov(24, 1)).toBe(lensFov(24));
    const a = 390 / 844;
    expect(viewFov(24, a)).toBeCloseTo(2 * Math.atan(Math.tan(Math.atan(12 / 24)) * 844 / 390) / D2R, 9);
  });

  it('wideAngle is the horizontal angle of the screen', () => {
    const a = 1400 / 880;
    expect(wideAngle(24, a)).toBeCloseTo(2 * Math.atan(Math.tan(lensFov(24) * D2R / 2) * a) / D2R, 12);
    expect(Math.round(wideAngle(24, a))).toBe(77);
    expect(Math.round(wideAngle(24, 1))).toBe(Math.round(lensFov(24)));
  });
});

describe('frameRect', () => {
  it('the whole screen for the Whole screen frame', () => {
    expect(frameRect(input({ frame: 'screen', camOpen: true, mode: 'walk', camPanel, sidePanel }))).toEqual({ x: 0, y: 0, w: 1400, h: 880 });
  });

  it('3:2 in Orbit with the panel closed: 90 % of the height, centred', () => {
    const r = frameRect(input({}));
    expect(r.h).toBeCloseTo(880 * 0.9, 9);
    expect(r.w).toBeCloseTo(792 * 1.5, 9);
    expect(r.x).toBeCloseTo((1400 - 1188) / 2, 9);
    expect(r.y).toBeCloseTo(44, 9);
  });

  it('with the Camera panel open: between the side panel and the Camera panel, 8 px from each, 94 % of the gap', () => {
    const r = frameRect(input({ camOpen: true, camPanel, sidePanel }));
    const left = sidePanel.right + 8, right = camPanel.left - 8;
    expect(r.w).toBeCloseTo((right - left) * 0.94, 9);
    expect(r.h).toBeCloseTo(r.w / 1.5, 9);
    expect(r.x).toBeCloseTo(left + ((right - left) - r.w) / 2, 9);
    expect(r.x).toBeGreaterThanOrEqual(left);
    expect(r.x + r.w).toBeLessThanOrEqual(right);
  });

  it('a side panel on the right half, or hidden (width 0), leaves the left free', () => {
    const r1 = frameRect(input({ camOpen: true, camPanel, sidePanel: { right: 800, width: 360 } }));
    const r2 = frameRect(input({ camOpen: true, camPanel, sidePanel: { right: 372, width: 0 } }));
    for (const r of [r1, r2]) expect(r.x).toBeCloseTo(((camPanel.left - 8) - (camPanel.left - 8) * 0.94) / 2, 9);
  });

  it('Walk and Ghost: below the 58 px top bar', () => {
    for (const mode of ['walk', 'ghost'] as const) {
      const r = frameRect(input({ mode, camOpen: true, camPanel, sidePanel }));
      expect(r.y).toBeGreaterThanOrEqual(58);
      const free = frameRect(input({ mode, frame: '1:1' }));
      expect(free.h).toBeCloseTo((880 - 58) * 0.9, 9);
      expect(free.y).toBeCloseTo(58 + (880 - 58 - free.h) / 2, 9);
    }
  });

  it('touch devices keep 156 px at the bottom in Walk and Ghost (not in Orbit)', () => {
    const r = frameRect(input({ mode: 'walk', touch: true, frame: '1:1' }));
    expect(r.h).toBeCloseTo((880 - 156 - 58) * 0.9, 9);
    expect(r.y + r.h).toBeLessThanOrEqual(880 - 156);
    expect(frameRect(input({ mode: 'orbit', touch: true, frame: '1:1' })).h).toBeCloseTo(880 * 0.9, 9);
  });

  it('narrow screens: the Camera panel across the top, the frame below it', () => {
    const phone = { width: 390, height: 844 };
    const r = frameRect(input({ canvas: phone, narrow: true, mode: 'walk', camOpen: true, camPanel: { left: 12, bottom: 400 }, sidePanel: null }));
    expect(r.y).toBeGreaterThanOrEqual(408);
    expect(r.w).toBeCloseTo(390 * 0.94, 9);
  });

  it('falls back to the whole screen when the free part is under 30 % wide or 22 % high', () => {
    const narrowGap = frameRect(input({ camOpen: true, camPanel: { left: 700, bottom: 600 }, sidePanel: { right: 400, width: 388 } }));
    expect(narrowGap.w).toBeCloseTo(Math.min(1400 * 0.94, 880 * 0.9 * 1.5), 9);
    const lowGap = frameRect(input({ canvas: { width: 390, height: 844 }, narrow: true, camOpen: true, camPanel: { left: 12, bottom: 700 }, frame: '1:1' }));
    expect(lowGap.y).toBeCloseTo((844 - 390 * 0.94) / 2, 9);
  });

  it('frameRatio of every frame', () => {
    const ratios: [Exclude<PhotoFrame, 'screen'>, number][] = [['16:9', 16 / 9], ['3:2', 1.5], ['4:3', 4 / 3], ['1:1', 1], ['4:5', 0.8], ['9:16', 9 / 16]];
    for (const [f, v] of ratios) expect(frameRatio(f)).toBeCloseTo(v, 12);
  });
});

describe('outSize: the exact photo sizes', () => {
  const sizeOf = (frame: PhotoFrame, long: 1920 | 3840, o: Partial<FrameRectInput> = {}) => outSize(frameRect(input({ frame, ...o })), long);
  it('3:2 HD 1920 x 1280, 4K 3840 x 2560 (Orbit, Walk, with the panel open)', () => {
    for (const o of [{}, { mode: 'walk' as const }, { camOpen: true, camPanel, sidePanel }, { camOpen: true, camPanel, sidePanel, mode: 'walk' as const }]) {
      expect(sizeOf('3:2', 1920, o)).toEqual({ w: 1920, h: 1280 });
      expect(sizeOf('3:2', 3840, o)).toEqual({ w: 3840, h: 2560 });
    }
  });

  it('9:16 at 4K is upright 2160 x 3840', () => {
    for (const o of [{}, { mode: 'walk' as const, camOpen: true, camPanel, sidePanel }]) expect(sizeOf('9:16', 3840, o)).toEqual({ w: 2160, h: 3840 });
  });

  it('every frame at both sizes keeps the frame shape on the long side', () => {
    const shapes: Record<Exclude<PhotoFrame, 'screen'>, [number, number]> = {
      '16:9': [1920, 1080], '3:2': [1920, 1280], '4:3': [1920, 1440], '1:1': [1920, 1920], '4:5': [1536, 1920], '9:16': [1080, 1920],
    };
    for (const [frame, [w, h]] of Object.entries(shapes) as [Exclude<PhotoFrame, 'screen'>, [number, number]][]) {
      expect(sizeOf(frame, 1920, { mode: 'walk', camOpen: true, camPanel, sidePanel })).toEqual({ w, h });
      expect(sizeOf(frame, 3840)).toEqual({ w: w * 2, h: h * 2 });
    }
  });

  it('the whole screen keeps the window shape', () => {
    expect(outSize({ w: 1400, h: 880 }, 1920)).toEqual({ w: 1920, h: Math.round(1920 * 880 / 1400) });
    expect(outSize({ w: 390, h: 844 }, 1920)).toEqual({ w: Math.round(1920 * 390 / 844), h: 1920 });
  });
});

describe('pitch, straight verticals, narrow', () => {
  it('clampPitch: +-85 degrees, +-35 with straight verticals', () => {
    expect(clampPitch(2, false)).toBeCloseTo(85 * D2R, 12);
    expect(clampPitch(-2, false)).toBeCloseTo(-85 * D2R, 12);
    expect(clampPitch(1, true)).toBeCloseTo(35 * D2R, 12);
    expect(clampPitch(0.3, true)).toBe(0.3);
  });

  it('shiftPx: only in Walk / Ghost with straight verticals; looking up slides the picture up (negative offset)', () => {
    const fov = lensFov(24);
    expect(shiftPx('orbit', true, 0.3, fov, 880)).toBe(0);
    expect(shiftPx('walk', false, 0.3, fov, 880)).toBe(0);
    const up = shiftPx('walk', true, 15 * D2R, fov, 880);
    expect(up).toBeCloseTo(-Math.tan(15 * D2R) / (2 * Math.tan(fov * D2R / 2)) * 880, 9);
    expect(up).toBeLessThan(0);
  });

  it('narrow() is the root width <= 700', () => {
    expect(isNarrow(700)).toBe(true);
    expect(isNarrow(701)).toBe(false);
  });
});

describe('photoName', () => {
  const t = new Date(2026, 10, 3, 9, 5, 7);
  it('<photoName>_<mode>_<where>_<lens>mm_<YYYY-MM-DD_HH-MM-SS>.png', () => {
    expect(photoName('Sukhumvit', 'orbit', 'overview', 50, t)).toBe('Sukhumvit_Orbit_overview_50mm_2026-11-03_09-05-07.png');
    expect(photoName('BangkokBank-Sampeng', 'walk', 'Level 1', 24, t)).toBe('BangkokBank-Sampeng_Walk_Level-1_24mm_2026-11-03_09-05-07.png');
    expect(photoName('Hotel-pictures', 'ghost', 'Floor 2', 24.6, t)).toBe('Hotel-pictures_Ghost_Floor-2_25mm_2026-11-03_09-05-07.png');
  });

  it('every run of characters outside [A-Za-z0-9_.-] becomes one dash', () => {
    expect(photoName('Presidential', 'walk', 'Suite (FL-01)', 24, t)).toBe('Presidential_Walk_Suite-FL-01-_24mm_2026-11-03_09-05-07.png');
    expect(photoName('Sukhumvit', 'walk', 'Ground floor', 24, t)).toMatch(/^Sukhumvit_Walk_Ground-floor_24mm_\d{4}-\d\d-\d\d_\d\d-\d\d-\d\d\.png$/);
    expect(photoName('X', 'walk', '<img src=x onerror=alert(1)>', 35, t)).toBe('X_Walk_-img-src-x-onerror-alert-1-_35mm_2026-11-03_09-05-07.png');
    expect(photoName('X', 'walk', 'ชั้น 1', 35, t)).toBe('X_Walk_-1_35mm_2026-11-03_09-05-07.png');
  });
});
