// Input (DESIGN.md 11.5 "Keys", 12 "Keys, typing rule, pointer lock, drag look, wheel, double-click, stick, Up/Down",
// 13 "Input"): port of viewer_modes.js "input". Every listener goes through ctx.disposer; a handler's error goes to
// ctx.reportError (no page-wide error listeners, 18.14). A keydown counts only when its target is the body / document or
// inside the viewer's root, and not typing, so a host page's own controls keep their keys (18.15). Owner: builder B.
import { Plane, Vector2, Vector3, type Object3D } from 'three';
import type { FloorRecord, ModesState, ViewerContext, ViewMode } from '../contracts';
import {
  D2R, DRAG_PX, GHOST_SPEED_MAX, GHOST_SPEED_MIN, JUMP_PX, LOOK, LOOK_TOUCH, STICK_KNOB, WHEEL_GHOST_BASE, WHEEL_MM_PER_PX,
} from './state';
import type { ModesUi } from './ui';
import type { Walker } from './walk';

/**
 * Keys go to the viewer unless you are typing, or using the arrow keys on a focused slider or list (the prototype's
 * `typing(e)`).
 */
export function typing(e: { target: EventTarget | null; code?: string }): boolean {
  const t = e.target as (EventTarget & { matches?: (sel: string) => boolean }) | null;
  if (!t || typeof t.matches !== 'function') return false;
  if (t.matches('textarea, input[type=text], input[type=number], input[type=search], input:not([type])')) return true;
  return t.matches('input[type=range], select') && (e.code || '').startsWith('Arrow');
}

/** The key event is the viewer's: its target is the window, the document, the body or inside the viewer's root (18.15). */
export function ours(e: { target: EventTarget | null }, root: Node): boolean {
  const t = e.target;
  if (!t) return true;
  if (typeof window !== 'undefined' && t === window) return true;
  if (typeof document !== 'undefined' && (t === document || t === document.body || t === document.documentElement)) return true;
  return typeof Node !== 'undefined' && t instanceof Node && root.contains(t);
}

export interface InputDeps {
  setMode(m: ViewMode, opt?: { floor?: FloorRecord; point?: { x: number; z: number }; foot?: number }): void;
  changeFloor(step: 1 | -1): void;
  /** Takes a photo; a failure is reported (the handlers never leave a rejected promise behind). */
  photo(): void;
  setLens(mm: number | string): void;
  openCam(open: boolean): void;
  updateHud(): void;
  drawFrame(): void;
  syncCamPanel(): void;
  resetStick(): void;
  showTilt(): void;
  clampPitch(): void;
  applyCamera(): void;
}

export function installInput(ctx: ViewerContext, s: ModesState, ui: ModesUi, walk: Walker, d: InputDeps): void {
  const canvas = ctx.canvas, root = ctx.ui.root, disposer = ctx.disposer;
  /** Listens through the disposer; an error in the handler goes to the error box. */
  function on<E extends Event>(target: EventTarget, type: string, fn: (e: E) => void, opts?: AddEventListenerOptions | boolean): void {
    disposer.listen(target, type, (e: Event) => {
      try { fn(e as E); } catch (err) { ctx.reportError(err); }
    }, opts);
  }
  const locked = () => typeof document !== 'undefined' && document.pointerLockElement === canvas;

  // ---------------------------------------------------------------- keys
  on<KeyboardEvent>(window, 'keydown', e => {
    if (s.locked || !ours(e, root) || typing(e) || e.ctrlKey || e.metaKey || e.altKey) return;
    // A focused list (Frame, Size) must not also jump to an option when a viewer key is pressed.
    if (e.target instanceof Element && e.target.tagName === 'SELECT' && e.code !== 'Tab') e.preventDefault();
    if (e.code === 'KeyP') { e.preventDefault(); if (!e.repeat) d.photo(); return; }   // holding P: one photo
    if (e.code === 'Digit1') { d.setMode('orbit'); return; }
    if (e.code === 'Digit2') { d.setMode('walk'); return; }
    if (e.code === 'Digit3') { d.setMode('ghost'); return; }
    if (s.mode === 'orbit') return;
    if (e.code === 'Escape') { if (!locked()) d.setMode('orbit'); return; }
    if (e.code === 'PageUp' || e.code === 'PageDown') { d.changeFloor(e.code === 'PageUp' ? 1 : -1); e.preventDefault(); return; }
    s.keys.add(e.code);
    if (['Space', 'ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(e.code)) e.preventDefault();
  });
  // Space must not also press a focused button or tick a focused checkbox (of the viewer: a host's controls keep it).
  on<KeyboardEvent>(window, 'keyup', e => {
    s.keys.delete(e.code);
    if (s.mode !== 'orbit' && e.code === 'Space' && ours(e, root) && !typing(e)) e.preventDefault();
  });
  on(window, 'blur', () => { s.keys.clear(); s.vert = 0; d.resetStick(); });
  // Chrome drops the key-ups that follow the Esc which frees the mouse: forget held keys when the lock ends.
  on(document, 'pointerlockchange', () => { if (!locked()) { s.keys.clear(); s.vert = 0; } });

  // ---------------------------------------------------------------- looking around
  function look(dx: number, dy: number, touch: boolean) {
    // Mouse: turn the way you move. Touch: drag the scene, like a panorama.
    if (touch) { s.yaw += dx * LOOK_TOUCH; s.pitch += dy * LOOK_TOUCH; } else { s.yaw -= dx * LOOK; s.pitch -= dy * LOOK; }
    d.clampPitch();
    d.showTilt();
  }
  // Show the touch controls after a touch, hide them after a mouse.
  on<PointerEvent>(window, 'pointerdown', e => {
    const t = e.pointerType === 'touch';
    if ((e.pointerType === 'touch' || e.pointerType === 'mouse') && t !== s.touch) { s.touch = t; d.updateHud(); d.drawFrame(); }
  }, true);
  on<MouseEvent>(document, 'mousemove', e => {
    if (s.mode === 'orbit' || !locked()) return;
    if (Math.abs(e.movementX) > JUMP_PX || Math.abs(e.movementY) > JUMP_PX) return;   // Chrome sometimes reports a jump as the lock starts
    look(e.movementX, e.movementY, false);
  });
  on<PointerEvent>(canvas, 'pointerdown', e => {
    if (s.locked || s.mode === 'orbit' || locked() || s.drag) return;
    s.drag = { id: e.pointerId, x: e.clientX, y: e.clientY, x0: e.clientX, y0: e.clientY, touch: e.pointerType === 'touch' };
    s.dragMoved = false;
  });
  on<PointerEvent>(window, 'pointermove', e => {
    const drag = s.drag;
    if (!drag || e.pointerId !== drag.id) return;
    const dx = e.clientX - drag.x, dy = e.clientY - drag.y;
    // A drag is judged by how far it went in all, so a slow, careful drag still counts as one (and does not lock the mouse).
    if (Math.abs(e.clientX - drag.x0) + Math.abs(e.clientY - drag.y0) > DRAG_PX) s.dragMoved = true;
    drag.x = e.clientX; drag.y = e.clientY;
    look(dx, dy, drag.touch);
  });
  const endDrag = (e: PointerEvent) => { if (s.drag && e.pointerId === s.drag.id) s.drag = null; };
  on(window, 'pointerup', endDrag);
  on(window, 'pointercancel', endDrag);
  on<PointerEvent>(canvas, 'click', e => {
    if (e.pointerType === 'touch') return;
    if (s.mode !== 'orbit' && !s.dragMoved && !locked() && typeof canvas.requestPointerLock === 'function') {
      try {
        const p: unknown = canvas.requestPointerLock();
        if (p instanceof Promise) p.catch(() => { /* drag to look still works */ });
      } catch { /* drag to look still works */ }
    }
  });
  on<MouseEvent>(canvas, 'contextmenu', e => { if (s.mode !== 'orbit') e.preventDefault(); });
  // Wheel: Ghost speed or Walk lens, in proportion to how far you scroll (a touchpad sends many small steps).
  // Up or pinch-out = faster / longer lens (zoom in), like the Orbit zoom.
  on<WheelEvent>(canvas, 'wheel', e => {
    if (s.locked || s.mode === 'orbit') return;
    e.preventDefault();
    const px = (e.deltaY || (e.shiftKey ? e.deltaX : 0)) * (e.deltaMode === 1 ? 40 : e.deltaMode === 2 ? 800 : 1);
    if (!px) return;
    if (s.mode === 'ghost') { s.ghostSpeed = Math.max(GHOST_SPEED_MIN, Math.min(GHOST_SPEED_MAX, s.ghostSpeed * Math.pow(WHEEL_GHOST_BASE, -px / 100))); d.updateHud(); }
    else d.setLens(s.lens - px * WHEEL_MM_PER_PX);           // 2 mm per mouse notch
  }, { passive: false });
  // Double-click a floor in Orbit: Walk there.
  on<MouseEvent>(canvas, 'dblclick', e => {
    if (s.locked || s.mode !== 'orbit') return;
    const r = canvas.getBoundingClientRect();                // event coordinates are client coordinates: so is this rect
    const ray = walk.ray;
    ray.setFromCamera(new Vector2((e.clientX - r.left) / r.width * 2 - 1, -(e.clientY - r.top) / r.height * 2 + 1), ctx.camera);
    ray.far = Infinity;
    const vis = ctx.floors.filter(f => f.group.visible);
    // Climbing: the treads and landings too (surfaces that are not floor plates; none on a model without stairways).
    const stepsOf = (f: FloorRecord): Object3D[] => f.surfaces.filter(m => m.userData.steps === true && m.visible);
    const targets: Object3D[] = vis.flatMap(f => (f.walkables.filter(m => m.visible) as Object3D[]).concat(walk.visibleColliders(f), stepsOf(f)));
    const hit = targets.length ? ray.intersectObjects(targets, false)[0] : null;
    let floor = hit ? vis.find(f => (f.walkables as Object3D[]).includes(hit.object) || (f.colliders as Object3D[]).includes(hit.object)
      || (f.surfaces as Object3D[]).includes(hit.object)) : undefined;
    let point: { x: number; z: number } | null = hit ? hit.point : null;
    if (hit && floor && hit.object.userData.steps === true) {
      // A double-click on a tread or landing puts the foot on it (R-9.5): the surface under the point that was hit.
      const land = walk.surfaceUnder(hit.point, hit.point.y + 0.05, floor);
      d.setMode('walk', { floor, point: hit.point, foot: land ? land.y : hit.point.y });
      return;
    }
    if (!point) {
      floor = vis.sort((a, b) => a.level - b.level)[0] || ctx.floors[0];
      const p = new Vector3();
      if (!floor || !ray.ray.intersectPlane(new Plane(new Vector3(0, 1, 0), -floor.level), p)) return;
      point = p;
    }
    d.setMode('walk', { floor, point });
  });

  // ---------------------------------------------------------------- touch stick: push to move (Walk) or fly (Ghost)
  // How far you push sets the speed. Event coordinates and the stick's rect are both client coordinates.
  function moveStick(e: PointerEvent) {
    const r = ui.stick.getBoundingClientRect(), R = r.width / 2;
    let x = (e.clientX - r.left - R) / R, y = (e.clientY - r.top - R) / R;
    const m = Math.hypot(x, y);
    if (m > 1) { x /= m; y /= m; }
    s.stick.x = x; s.stick.y = y;
    ui.knob.style.transform = `translate(${x * R * STICK_KNOB}px, ${y * R * STICK_KNOB}px)`;
  }
  on<PointerEvent>(ui.stick, 'pointerdown', e => {
    s.stick.id = e.pointerId;
    try { ui.stick.setPointerCapture(e.pointerId); } catch { /* moves still arrive while over the stick */ }
    moveStick(e); e.preventDefault();
  });
  on<PointerEvent>(ui.stick, 'pointermove', e => { if (e.pointerId === s.stick.id) moveStick(e); });
  const endStick = (e: PointerEvent) => { if (e.pointerId === s.stick.id) d.resetStick(); };
  on(ui.stick, 'pointerup', endStick);
  on(ui.stick, 'pointercancel', endStick);
  // Up / Down buttons: tap for the next floor in Walk, hold to rise or sink in Ghost.
  for (const [b, v] of [[ui.up, 1], [ui.down, -1]] as const) {
    on<PointerEvent>(b, 'pointerdown', e => {
      e.preventDefault();
      if (s.mode === 'walk') d.changeFloor(v);
      else { s.vert = v; try { b.setPointerCapture(e.pointerId); } catch { /* fine */ } }
    });
    const stop = () => { s.vert = 0; };
    on(b, 'pointerup', stop); on(b, 'pointercancel', stop); on(b, 'lostpointercapture', stop);
  }

  // ---------------------------------------------------------------- buttons and the Camera panel
  for (const m of ['orbit', 'walk', 'ghost'] as const) on(ui.modeButtons[m], 'click', () => d.setMode(m));
  on(ui.exit, 'click', () => d.setMode('orbit'));
  on(ui.camBtn, 'click', () => d.openCam(!s.camOpen));
  on(ui.hudCam, 'click', () => d.openCam(!s.camOpen));
  on(ui.camClose, 'click', () => d.openCam(false));
  on(ui.lens, 'input', () => d.setLens(ui.lens.value));
  for (const b of ui.presets) on(b, 'click', () => d.setLens(b.getAttribute('data-mm') ?? ''));
  on(ui.eye, 'input', () => { s.eye = Number(ui.eye.value); if (s.mode === 'walk') s.pos.y = s.foot + s.eye; d.applyCamera(); d.syncCamPanel(); });
  on(ui.tilt, 'input', () => { s.pitch = Number(ui.tilt.value) * D2R; d.clampPitch(); d.applyCamera(); d.syncCamPanel(); });
  on(ui.straight, 'change', () => { s.straight = ui.straight.checked; d.clampPitch(); d.applyCamera(); d.syncCamPanel(); });
  // Lists hand the keyboard back to the viewer once a choice is made.
  on(ui.frameSel, 'change', () => { s.frame = ui.frameSel.value as ModesState['frame']; d.drawFrame(); ui.frameSel.blur(); });
  on(ui.size, 'change', () => { s.size = Number(ui.size.value) === 3840 ? 3840 : 1920; d.drawFrame(); ui.size.blur(); });
  on(ui.grid, 'change', () => { s.grid = ui.grid.checked; d.drawFrame(); });
  on(ui.shot, 'click', () => d.photo());
  on(ui.snap, 'click', () => d.photo());
}
