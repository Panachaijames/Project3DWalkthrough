// Constants and the mode state (DESIGN.md 12 "Constants", "Mode state s"; 13 Walk / Ghost / Camera / Photos / Input).
// Port of the top of viewer-modes/viewer_modes.js: every number below is the prototype's, unchanged. Owner: builder B.
import { Vector3 } from 'three';
import type { ModesState, PhotoFrame, ViewerContext } from '../contracts';

export const D2R = Math.PI / 180;

// ------------------------------------------------------------------------------------------------------------ Walk
/** Eye height (m above the floor level). */
export const EYE = 1.6;
/** Body radius (m). */
export const RADIUS = 0.3;
/** m/s; Shift: RUN_SPEED. */
export const WALK_SPEED = 1.5;
export const RUN_SPEED = 3.4;
/** rad per px: mouse, touch. */
export const LOOK = 0.0025;
export const LOOK_TOUCH = 0.004;
/** Ray heights above the level: knee and chest (railings are 1 m high). */
export const RAY_HEIGHTS = [0.35, 1.2] as const;
/** Ray offsets across the shoulders, x RADIUS: at most 7.5 cm apart; the outer pair 1.5 cm inside the body's edge. */
export const RAY_OFFSETS = [0, -0.25, 0.25, -0.5, 0.5, -0.75, 0.75, -0.95, 0.95] as const;
/** onFloor: from level + 1 m straight down, 1.6 m far. */
export const FLOOR_RAY_FROM = 1;
export const FLOOR_RAY_FAR = 1.6;
/** clearance: 8 directions at both ray heights, 3 m far. */
export const CLEARANCE_DIRECTIONS = 8;
export const CLEARANCE_FAR = 3;
/** findFree: rings every 0.5 m, n = max(8, round(r * 6)); passes [[want, 6], [0.5, 12]]. */
export const FREE_RING_STEP = 0.5;
export const FREE_MIN_ROOM = 0.5;
export const FREE_NEAR_RINGS = 6;
export const FREE_FAR_RINGS = 12;
/** Room wanted when Walk starts from a button or a key; from a point (double-click, address) FREE_MIN_ROOM. */
export const FREE_FROM_BUTTON = 1.0;
/** openAhead at chest height. */
export const OPEN_HEIGHT = 1.2;
/** faceOpen keeps the heading when this much is open ahead; else it scores 23 other headings, 15 deg apart, 15 m far. */
export const FACE_KEEP = 4;
export const FACE_HEADINGS = 24;
export const FACE_FAR = 15;
/** Frame time cap (s). */
export const DT_CAP = 0.05;
/** probe.walk step (m). */
export const PROBE_STEP = 0.05;
/** probe.open / probe.crosses reach (m) and height. */
export const PROBE_OPEN_FAR = 30;

// -------------------------------------------------------------------------------------------------------- Climbing
// rooms/DESIGN.md R-9.10 (the D-13 "Climbing" row): only for a model with `stairways`; the rows above do not change.
/** The highest step taken up and the deepest taken down (m). */
export const STEP_UP = 0.25;
export const STEP_DOWN = 0.30;
/** The ground ray starts this far above the foot and ends STEP_DOWN below it; the first surface it meets decides. */
export const GROUND_RAY_FROM = 1.0;
/** No ground under the next centre: the ray is tried again this far along the move. */
export const GAP_BRIDGE = 0.08;
/** The head ray: from foot + HEAD_FROM up to foot + eye + HEAD_ABOVE_EYE, against the surfaces. */
export const HEAD_FROM = 0.30;
export const HEAD_ABOVE_EYE = 0.30;
/** The head ray never reaches higher than foot + HEAD_REACH, whatever the eye slider says: the builder leaves 2.10 m of
 *  headroom under a slab, so a reach that grew with the eye (up to 2.2 + 0.30) stopped the walker on stairs and under low
 *  slabs (rooms review RR, CODE-2 / BRK-6). 1.90 is the reach at the default eye. */
export const HEAD_REACH = 1.90;
/** The body rays meet the colliders of every floor whose height range overlaps [foot, foot + BODY_SPAN]. */
export const BODY_SPAN = 2.0;
/** The floor named is the nearest level; it changes once the foot is this far past mid-storey. */
export const FLOOR_HYSTERESIS = 0.20;
/** The eye eases toward foot + eye with this time constant (s); never on a teleport or in a probe call. */
export const EYE_EASE = 0.1;
/** A tolerance of the step window (m): a riser of exactly 0.25 m is climbed. */
export const STEP_EPS = 1e-4;

/** The foot-based walker is on when the model has `stairways`, even an empty list (R-9.1). */
export const isClimbing = (model: { stairways?: unknown } | null | undefined): boolean => !!model && model.stairways !== undefined;

// ----------------------------------------------------------------------------------------------------------- Ghost
export const GHOST_SPEED = 6;
export const GHOST_SPEED_MIN = 0.5;
export const GHOST_SPEED_MAX = 60;
export const GHOST_FAST = 3;
/** In Ghost you are on a floor once your eye is 0.3 m above it. */
export const GHOST_ON_FLOOR = 0.3;
/** floorAtHeight: a floor counts up to 0.1 m above the height asked. */
export const FLOOR_TOLERANCE = 0.1;

// ---------------------------------------------------------------------------------------------------------- Camera
export const LENS_MIN = 12;
export const LENS_MAX = 85;
export const WALK_LENS = 24;
export const LENS_PRESETS = [16, 24, 35, 50] as const;
/** Wheel in Walk: mm per px of scroll (2 mm per 100 px, a mouse notch). */
export const WHEEL_MM_PER_PX = 1 / 50;
/** Wheel in Ghost: speed x 1.2^(-px / 100). */
export const WHEEL_GHOST_BASE = 1.2;
export const EYE_MIN = 0.8;
export const EYE_MAX = 2.2;
export const PITCH_LIMIT = 85;
export const PITCH_LIMIT_STRAIGHT = 35;
/** Camera near plane in Walk and Ghost (Orbit keeps the camera's own, 0.1). */
export const NEAR_FIRST_PERSON = 0.05;

// ---------------------------------------------------------------------------------------------------------- Photos
export const PHOTO_SIZES = [1920, 3840] as const;
export const FRAMES: readonly PhotoFrame[] = ['screen', '16:9', '3:2', '4:3', '1:1', '4:5', '9:16'];
export const FRAME_DEFAULT: PhotoFrame = '3:2';
/** Frame: 94 % of the free width, at most 90 % of its height, 8 px from the panels, below the 58 px top bar in Walk /
 *  Ghost, 156 px kept at the bottom on touch devices; the whole screen when the free part is under 30 % / 22 %. */
export const FRAME_WIDTH_SHARE = 0.94;
export const FRAME_HEIGHT_SHARE = 0.9;
export const FRAME_GAP = 8;
export const FRAME_TOP_FP = 58;
export const FRAME_TOUCH_BOTTOM = 156;
export const FRAME_MIN_WIDTH_SHARE = 0.3;
export const FRAME_MIN_HEIGHT_SHARE = 0.22;
/** Narrow screens (portrait phones): the Camera panel across the top. */
export const NARROW_WIDTH = 700;
/** Crowded: the side panel, the Camera panel and a frame do not fit side by side (innerWidth - 650 < 45 %). */
export const CROWDED_PANELS = 650;
export const CROWDED_SHARE = 0.45;
export const FLASH_MS = 350;
export const FLASH_FROM = 0.7;
export const THUMBNAILS = 12;
/** Delay of ?shot=1 (ms). */
export const SHOT_DELAY = 300;

// ----------------------------------------------------------------------------------------------------------- Input
/** A drag counts as one after 4 px (|dx| + |dy| from where it started). */
export const DRAG_PX = 4;
/** Mouse movements over 300 px are ignored (Chrome reports a jump as the pointer lock starts). */
export const JUMP_PX = 300;
/** Touch stick: knob travel 60 % of the radius; dead zone 0.15. */
export const STICK_KNOB = 0.6;
export const STICK_DEAD = 0.15;

/** The prototype's `s` (ModesState), with its starting values. `touch` from the device's pointer. */
export function createState(ctx: Pick<ViewerContext, 'camera' | 'floors'> & { model?: { stairways?: unknown } | null }): ModesState {
  const coarse = typeof matchMedia === 'function' && matchMedia('(pointer: coarse)').matches;
  // The foot (rooms/DESIGN.md R-9.2): the walker's own state when the model climbs; otherwise always the current floor's
  // level, whatever is written (the old walker never reads it, and `s.foot + s.eye` is then today's `level + eye`).
  const climbing = isClimbing(ctx.model);
  let foot = ctx.floors[0]!.level;
  return {
    mode: 'orbit',
    floor: ctx.floors[0]!,
    pos: new Vector3(),
    get foot() { return climbing ? foot : this.floor.level; },
    set foot(value: number) { if (climbing && Number.isFinite(value)) foot = value; },
    yaw: 0,
    pitch: 0,
    eye: EYE,
    lens: WALK_LENS,
    orbitLens: Math.round(12 / Math.tan(ctx.camera.fov * D2R / 2)),
    straight: false,
    ghostSpeed: GHOST_SPEED,
    keys: new Set(),
    saved: null,
    drag: null,
    dragMoved: false,
    frame: FRAME_DEFAULT,
    size: 1920,
    grid: true,
    camOpen: false,
    last: typeof performance !== 'undefined' ? performance.now() : Date.now(),
    touch: coarse,
    stick: { id: null, x: 0, y: 0 },
    vert: 0,
    locked: false,
  };
}

/** Number.isFinite as a type guard. */
export const finite = (v: unknown): v is number => typeof v === 'number' && Number.isFinite(v);
export const clamp = (v: number, lo: number, hi: number) => Math.max(lo, Math.min(hi, v));
