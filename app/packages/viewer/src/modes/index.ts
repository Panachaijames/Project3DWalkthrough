// installModes: Orbit / Walk / Ghost, the Camera tool, photos, touch controls (DESIGN.md 11, 12, 13): a TypeScript port of
// viewer-modes/viewer_modes.js, behaviour for behaviour, inside the viewer's root. Owner: builder B.
//
// What changed from the prototype, by design: the markup is built with ui/dom.ts el() (drawing text as text), the overlays
// are absolute children of the root and all screen maths is root-relative (ctx.size(), ctx.rectOf()); body classes are
// root flags (ctx.ui.setFlag); listeners go through ctx.disposer; errors go to ctx.reportError (no window error
// listeners); restoreVisibility is ctx.visibility.applyFloor(); onChange is bus `mode` (every HUD update; viewer.ts
// filters); resize comes from bus `resize` (core/context.ts watches the size and the pixel ratio); photo downloads go
// through ctx.options.download unless nodownload, and each photo emits `photo`; the start-up options come as parsed
// AddressOptions (applyAddress); the frame hook is registered by viewer.ts (tick), never here; window.__viewer is set by
// the test hook (A), not here.
import { Vector3 } from 'three';
import type { AddressOptions, FloorRecord, InstallModes, ModesApi, ViewerContext, ViewMode } from '../contracts';
import { createProjection } from './camera';
import { installInput } from './input';
import { createPhotos } from './photo';
import { createProbe } from './probe';
import {
  clamp, createState, D2R, DT_CAP, EYE_MAX, EYE_MIN, FLOOR_TOLERANCE, FRAMES, FREE_FROM_BUTTON, FREE_MIN_ROOM, finite, GHOST_FAST,
  GHOST_ON_FLOOR, LENS_MAX, LENS_MIN, NEAR_FIRST_PERSON, RUN_SPEED, SHOT_DELAY, STICK_DEAD, WALK_SPEED,
} from './state';
import { buildUi, createHud } from './ui';
import { createWalker } from './walk';

// ---------------------------------------------------------------------------------------- floors (pure, Node-testable)
/** The lowest floor that is showing, else the first. */
export const pickFloor = (floors: FloorRecord[]): FloorRecord =>
  floors.filter(f => f.group.visible).sort((a, b) => a.level - b.level)[0] || floors[0]!;

/** The floors of f's stack, bottom up. */
export const stackOf = (floors: FloorRecord[], f: FloorRecord): FloorRecord[] =>
  floors.filter(g => g.stack === f.stack).sort((a, b) => a.level - b.level);

/** The floor at this height, among the floors that are showing (of the stack of `current`, or of the picked floor). */
export function floorAtHeight(floors: FloorRecord[], current: FloorRecord, y: number): FloorRecord {
  const base = stackOf(floors, current).some(f => f.group.visible) ? current : pickFloor(floors);
  const all = stackOf(floors, base), shown = all.filter(f => f.group.visible), stack = shown.length ? shown : all;
  const list = stack.filter(f => f.level <= y + FLOOR_TOLERANCE);
  return list.length ? list[list.length - 1]! : stack[0]!;
}

/** In Ghost you are "on" a floor once your eye is 0.3 m above it (not a full eye height), so a small dip keeps the floor. */
export const currentFloor = (floors: FloorRecord[], s: { mode: ViewMode; floor: FloorRecord; pos: Vector3 }): FloorRecord =>
  s.mode === 'ghost' ? floorAtHeight(floors, s.floor, s.pos.y - GHOST_ON_FLOOR) : s.floor;

// ------------------------------------------------------------------------------------------------------------ install
export const installModes: InstallModes = (ctx: ViewerContext) => {
  const { camera, controls, floors } = ctx;
  const s = createState(ctx);
  const orbitNear = camera.near;
  camera.rotation.order = 'YXZ';
  const walk = createWalker(s);
  const proj = createProjection(ctx, s);
  const ui = buildUi(ctx, s);
  const stack = (f: FloorRecord) => stackOf(floors, f);
  const here = () => currentFloor(floors, s);
  const hud = createHud(ctx, s, ui, proj, { stackOf: stack });
  const photos = createPhotos(ctx, s, {
    frameRect: hud.frameRect, shift: proj.shift, applyProjection: proj.applyProjection, applyCamera: proj.applyCamera,
    where: () => (s.mode === 'orbit' ? 'overview' : here().name), drawFrame: hud.drawFrame, flash: ui.flash, photos: ui.photos,
  });
  const report = (err: unknown) => ctx.reportError(err);

  // -------------------------------------------------------------- floors and visibility
  function applyVisibility() {
    if (s.mode === 'walk') for (const f of floors) f.group.visible = f.stack === s.floor.stack;
    else ctx.visibility.applyFloor();                     // the prototypes' restoreVisibility
  }
  function goToFloor(key: string) {
    const f = ctx.floorByKey.get(key);
    if (!f || s.mode === 'orbit' || (s.mode === 'walk' && f === s.floor)) return;
    if (s.mode === 'walk') {
      s.floor = f;
      const p = walk.startPoint(f, s.pos);
      s.pos.set(p.x, f.level + s.eye, p.z);
      walk.findFree(s.pos); walk.faceOpen();
    } else {
      s.pos.y += f.level - here().level; s.floor = f;
    }
    applyVisibility(); proj.applyCamera(); hud.updateHud();
  }
  function changeFloor(step: 1 | -1) {
    const cur = here(), list = stack(cur), next = list[list.indexOf(cur) + step];
    if (next) goToFloor(next.key);
  }

  // -------------------------------------------------------------- modes
  function setMode(m: ViewMode, opt: { floor?: FloorRecord; point?: { x: number; z: number } } = {}) {
    const from = s.mode;
    if (m === from && !opt.point) return;
    // Locked (the build replay is on): Orbit only. The prototype's UI could not get here (the panel is hidden, the keys,
    // the wheel and the double-click check the lock); the public Viewer.setMode and the address can (B.md B-4).
    if (s.locked && m !== 'orbit') return;
    if (from === 'orbit' && m !== 'orbit') {
      s.saved = { pos: camera.position.clone(), target: controls.target.clone() };
      const dir = controls.target.clone().sub(camera.position).normalize();
      s.yaw = Math.atan2(-dir.x, -dir.z);
      controls.enabled = false;
      camera.near = NEAR_FIRST_PERSON;
      // Hand the keys back to the viewer (a focused button would take Space); only the viewer's own controls lose focus.
      const active = typeof document !== 'undefined' ? document.activeElement : null;
      if (active instanceof HTMLElement && ctx.ui.root.contains(active)) active.blur();
      s.floor = opt.floor || pickFloor(floors);
      if (m === 'ghost') {
        s.pos.copy(camera.position);
        s.pitch = Math.asin(Math.max(-1, Math.min(1, dir.y)));
      } else {
        const start = walk.startPoint(s.floor, opt.point || controls.target);
        s.pos.set(start.x, s.floor.level + s.eye, start.z);
        walk.findFree(s.pos, opt.point ? FREE_MIN_ROOM : FREE_FROM_BUTTON);    // from a button: somewhere with room around you
        s.pitch = 0;
        walk.faceOpen();
      }
    } else if (from === 'ghost' && m === 'walk') {
      // Land on the floor below you; from far outside, start in the middle of that floor.
      s.floor = floorAtHeight(floors, s.floor, s.pos.y - GHOST_ON_FLOOR);
      const p = walk.startPoint(s.floor, s.pos);
      s.pos.set(p.x, s.floor.level + s.eye, p.z); walk.findFree(s.pos);
    } else if (from === 'walk' && m === 'walk' && opt.point) {
      s.floor = opt.floor || s.floor;
      s.pos.set(opt.point.x, s.floor.level + s.eye, opt.point.z); walk.findFree(s.pos); walk.faceOpen();
    }
    if (m === 'orbit') {
      if (typeof document !== 'undefined' && document.pointerLockElement === ctx.canvas) document.exitPointerLock();
      camera.near = orbitNear;
      if (s.saved) { camera.position.copy(s.saved.pos); controls.target.copy(s.saved.target); }
      controls.enabled = true;
      s.keys.clear(); s.drag = null; s.vert = 0; hud.resetStick();
    }
    s.mode = m;
    proj.clampPitch();
    applyVisibility();
    proj.applyProjection();
    if (m === 'orbit') controls.update(); else proj.applyCamera();
    hud.markModes();
    hud.updateHud(); hud.syncCamPanel();
  }

  // -------------------------------------------------------------- frame tick (Walk / Ghost movement)
  function tick(now: number) {
    const t = finite(now) ? now : performance.now();
    const dt = Math.max(0, Math.min(DT_CAP, (t - s.last) / 1000));
    s.last = t;
    if (s.mode === 'orbit') { controls.update(); return; }
    const k = s.keys, st = s.stick;
    let fwdIn = (k.has('KeyW') || k.has('ArrowUp') ? 1 : 0) - (k.has('KeyS') || k.has('ArrowDown') ? 1 : 0);
    let sideIn = (k.has('KeyD') || k.has('ArrowRight') ? 1 : 0) - (k.has('KeyA') || k.has('ArrowLeft') ? 1 : 0);
    const sm = Math.hypot(st.x, st.y);
    if (sm > STICK_DEAD) { const g = (sm - STICK_DEAD) / (1 - STICK_DEAD) / sm; fwdIn -= st.y * g; sideIn += st.x * g; }
    const fast = k.has('ShiftLeft') || k.has('ShiftRight');
    const right = new Vector3(Math.cos(s.yaw), 0, -Math.sin(s.yaw));
    if (s.mode === 'walk') {
      const d = new Vector3(-Math.sin(s.yaw), 0, -Math.cos(s.yaw)).multiplyScalar(fwdIn).addScaledVector(right, sideIn);
      const mag = Math.min(1, d.length());
      if (mag > 0) walk.walkMove(d.setLength(mag * (fast ? RUN_SPEED : WALK_SPEED) * dt));
      s.pos.y = s.floor.level + s.eye;
    } else {
      const upIn = (k.has('Space') || k.has('KeyE') ? 1 : 0) - (k.has('KeyC') || k.has('KeyQ') ? 1 : 0) + s.vert;
      const cp = Math.cos(s.pitch);
      const d = new Vector3(-Math.sin(s.yaw) * cp, Math.sin(s.pitch), -Math.cos(s.yaw) * cp).multiplyScalar(fwdIn)
        .addScaledVector(right, sideIn).add(new Vector3(0, Math.max(-1, Math.min(1, upIn)), 0));
      const mag = Math.min(1, d.length());
      if (mag > 0) s.pos.addScaledVector(d.setLength(1), mag * s.ghostSpeed * (fast ? GHOST_FAST : 1) * dt);
    }
    proj.applyCamera();
  }

  // -------------------------------------------------------------- start-up options (viewer_modes.js applyUrl)
  function applyAddress(a: AddressOptions) {
    if (finite(a.lens)) s.lens = clamp(a.lens, LENS_MIN, LENS_MAX);
    if (finite(a.eye)) s.eye = clamp(a.eye, EYE_MIN, EYE_MAX);
    if (a.frame !== undefined && FRAMES.includes(a.frame)) { s.frame = a.frame; ui.frameSel.value = s.frame; }
    if (a.size === 3840) { s.size = 3840; ui.size.value = '3840'; }
    if (a.straight === true) s.straight = true;
    if (a.nodownload === true) s.noDownload = true;
    if (a.touch === true) s.touch = true;
    const m = a.mode;
    // While the modes are locked (a Build settings screen asked for by options.build) the viewer stays in Orbit (B.md B-4).
    if ((m === 'walk' || m === 'ghost') && !s.locked) {
      const floor = a.floor !== undefined ? ctx.floorByKey.get(a.floor) : undefined;
      const pt = a.point;
      const point = pt ? { x: finite(pt.x) ? pt.x : 0, z: finite(pt.z) ? pt.z : 0 } : undefined;
      setMode(m, { floor, point });
      if (m === 'ghost' && pt) s.pos.set(finite(pt.x) ? pt.x : s.pos.x, finite(pt.y) ? pt.y : s.pos.y, finite(pt.z) ? pt.z : s.pos.z);
      if (finite(a.yaw)) s.yaw = a.yaw * D2R;
      if (finite(a.pitch)) { s.pitch = a.pitch * D2R; proj.clampPitch(); }
      proj.applyCamera();
    }
    if (a.cam === true) hud.openCam(true);
    hud.syncCamPanel(); hud.updateHud();
    if (a.shot === true) ctx.disposer.timeout(() => { photos.takePhoto().catch(report); }, SHOT_DELAY);
  }

  // -------------------------------------------------------------- lock: while the build replay runs, Orbit only
  function lock(on: boolean) {
    s.locked = !!on;
    if (on) { if (s.mode !== 'orbit') setMode('orbit'); if (s.camOpen) hud.openCam(false); }
    else if (s.camWanted) { s.camWanted = false; hud.openCam(true); }   // e.g. ?cam=1 asked for it while the replay was on
  }

  installInput(ctx, s, ui, walk, {
    setMode, changeFloor, photo: () => { photos.takePhoto().catch(report); }, setLens: hud.setLens, openCam: hud.openCam,
    updateHud: hud.updateHud, drawFrame: hud.drawFrame, syncCamPanel: hud.syncCamPanel, resetStick: hud.resetStick,
    showTilt: hud.showTilt, clampPitch: proj.clampPitch, applyCamera: proj.applyCamera,
  });
  // Resizing, browser zoom and another screen (core/context.ts resizes the renderer): the projection, the HUD, the frame.
  ctx.disposer.add(ctx.bus.on('resize', () => {
    try { proj.applyProjection(); hud.updateHud(); hud.syncCamPanel(); } catch (err) { report(err); }
  }));

  proj.applyProjection(); hud.updateHud(); hud.syncCamPanel();
  const probe = createProbe(ctx, s, walk, proj.applyCamera);
  const api: ModesApi = {
    get mode() { return s.mode; },
    state: s,
    probe,
    setMode,
    goToFloor,
    changeFloor,
    takePhoto: () => photos.takePhoto(),
    openCam: open => hud.openCam(open),
    lock,
    applyAddress,
    tick,
  };
  return api;
};
