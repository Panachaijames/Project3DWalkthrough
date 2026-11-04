// Lens and photo-frame maths (DESIGN.md 12 "Projection", 13 "Camera", "Photos"), port of viewer_modes.js "camera".
// The pure helpers (lensFov, viewFov, frameRect, outSize, and their small friends) are Node-testable; createProjection
// binds them to a viewer: root-relative sizes from ctx.size() (never innerWidth / clientWidth), the camera, the state.
// Owner: builder B.
import type { FrameRect, LensFov, ModesState, OutSize, PhotoFrame, ViewerContext, ViewFov, ViewMode } from '../contracts';
import {
  D2R, FRAME_GAP, FRAME_HEIGHT_SHARE, FRAME_MIN_HEIGHT_SHARE, FRAME_MIN_WIDTH_SHARE, FRAME_TOP_FP, FRAME_TOUCH_BOTTOM,
  FRAME_WIDTH_SHARE, NARROW_WIDTH, PITCH_LIMIT, PITCH_LIMIT_STRAIGHT,
} from './state';

/** Angle (degrees) across the short side of a 36 x 24 mm frame. */
export const lensFov: LensFov = mm => 2 * Math.atan(12 / mm) / D2R;

/** Vertical field of view (degrees): the lens spans the screen's short side (portrait: the width). */
export const viewFov: ViewFov = (mm, aspect) =>
  aspect >= 1 ? lensFov(mm) : 2 * Math.atan(Math.tan(lensFov(mm) * D2R / 2) / aspect) / D2R;

/** Horizontal field of view (degrees) of a lens on a screen of this aspect (the Camera panel's "° wide"). */
export const wideAngle = (mm: number, aspect: number): number =>
  2 * Math.atan(Math.tan(viewFov(mm, aspect) * D2R / 2) * aspect) / D2R;

/** '3:2' -> 1.5. */
export const frameRatio = (frame: Exclude<PhotoFrame, 'screen'>): number => {
  const [a, b] = frame.split(':').map(Number);
  return a! / b!;
};

/**
 * The photo frame (root-relative CSS px): the shot is framed in the part of the screen the panels leave free, so the
 * photo is exactly what you can see. `touch` is "the device has touch" (s.touch || navigator.maxTouchPoints > 0): the
 * stick and floor buttons are reserved whenever it does, so switching input never moves the frame.
 */
export const frameRect: FrameRect = i => {
  const cw = i.canvas.width, ch = i.canvas.height;
  if (i.frame === 'screen') return { x: 0, y: 0, w: cw, h: ch };
  let left = 0, right = cw, top = 0, bottom = ch;
  if (i.camOpen) {
    if (i.camPanel) {
      if (i.narrow) top = i.camPanel.bottom + FRAME_GAP;
      else right = i.camPanel.left - FRAME_GAP;
    }
    const p = i.sidePanel;
    if (p && p.width && p.right < cw / 2) left = p.right + FRAME_GAP;
  }
  if (i.mode !== 'orbit') top = Math.max(top, FRAME_TOP_FP);                  // below the top bar in Walk and Ghost
  if (i.touch && i.mode !== 'orbit') bottom = ch - FRAME_TOUCH_BOTTOM;
  if (right - left < cw * FRAME_MIN_WIDTH_SHARE) { left = 0; right = cw; }
  if (bottom - top < ch * FRAME_MIN_HEIGHT_SHARE) { top = 0; bottom = ch; }
  const a = frameRatio(i.frame), rw = right - left, rh = bottom - top;
  let w = rw * FRAME_WIDTH_SHARE, h = w / a;
  if (h > rh * FRAME_HEIGHT_SHARE) { h = rh * FRAME_HEIGHT_SHARE; w = h * a; }
  return { x: left + (rw - w) / 2, y: top + (rh - h) / 2, w, h };
};

/** Photo size in pixels: the long side is HD (1920) or 4K (3840). */
export const outSize: OutSize = (r, long) =>
  r.w >= r.h ? { w: long, h: Math.round(long * r.h / r.w) } : { w: Math.round(long * r.w / r.h), h: long };

/** The pitch kept within +-85 degrees, +-35 with straight verticals (radians). */
export const clampPitch = (pitch: number, straight: boolean): number => {
  const lim = (straight ? PITCH_LIMIT_STRAIGHT : PITCH_LIMIT) * D2R;
  return Math.max(-lim, Math.min(lim, pitch));
};

/**
 * Straight verticals: the camera stays level and the picture slides up or down instead of tilting (CSS px, the view
 * offset's y). 0 in Orbit or without straight verticals.
 */
export const shiftPx = (mode: ViewMode, straight: boolean, pitch: number, fovDeg: number, height: number): number =>
  mode !== 'orbit' && straight ? -Math.tan(pitch) / (2 * Math.tan(fovDeg * D2R / 2)) * height : 0;

/** Narrow screens (portrait phones): the Camera panel goes across the top. Root-relative (DESIGN.md 11.6). */
export const isNarrow = (width: number): boolean => width <= NARROW_WIDTH;

export interface Projection {
  /** Root aspect (width / max(1, height)). */
  aspect(): number;
  /** viewFov for this root. */
  viewFov(mm: number): number;
  /** wideAngle for this root. */
  wideAngle(mm: number): number;
  /** shiftPx for the camera now. */
  shift(): number;
  narrow(): boolean;
  /** aspect, fov from the lens, the straight-verticals view offset, updateProjectionMatrix. */
  applyProjection(): void;
  /** Walk / Ghost: the camera at s.pos looking along yaw / pitch (level with straight verticals), then the projection. */
  applyCamera(): void;
  /** s.pitch within its limits. */
  clampPitch(): void;
}

export function createProjection(ctx: Pick<ViewerContext, 'camera' | 'size'>, s: ModesState): Projection {
  const camera = ctx.camera;
  const aspect = () => { const { width, height } = ctx.size(); return width / Math.max(1, height); };
  const p: Projection = {
    aspect,
    viewFov: mm => viewFov(mm, aspect()),
    wideAngle: mm => wideAngle(mm, aspect()),
    shift: () => shiftPx(s.mode, s.straight, s.pitch, camera.fov, ctx.size().height),
    narrow: () => isNarrow(ctx.size().width),
    applyProjection() {
      const { width: cw, height: ch } = ctx.size();
      camera.aspect = cw / Math.max(1, ch);
      camera.fov = viewFov(s.mode === 'orbit' ? s.orbitLens : s.lens, camera.aspect);
      const shift = p.shift();
      if (shift) camera.setViewOffset(cw, ch, 0, shift, cw, ch);
      else camera.clearViewOffset();
      camera.updateProjectionMatrix();
    },
    applyCamera() {
      if (s.mode === 'orbit') return;
      camera.position.copy(s.pos);
      camera.rotation.set(s.straight ? 0 : s.pitch, s.yaw, 0, 'YXZ');
      p.applyProjection();
    },
    clampPitch() { s.pitch = clampPitch(s.pitch, s.straight); },
  };
  return p;
}
