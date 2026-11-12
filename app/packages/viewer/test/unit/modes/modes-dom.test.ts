// @vitest-environment happy-dom
// Builder B: installModes in happy-dom on makeTestContext (fake renderer): the markup and its texts word for word, the
// root flags, the HUD and hint texts, aria-pressed, the keys and their target / typing rules, the mouse and touch input,
// the wheel, the double-click, tick, the Camera panel, photos (a stubbed 2D canvas), applyAddress exactly as applyUrl,
// lock, bus `mode`, resize and dispose (DESIGN.md 11.3 - 11.6, 12, 13, 17.2).
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { ModesApi, PhotoResult, ViewerContext } from '../../../src/contracts';
import { lensFov, outSize, viewFov } from '../../../src/modes/camera';
import { MODES_CSS } from '../../../src/modes/css';
import { installModes } from '../../../src/modes/index';
import { D2R, LOOK, LOOK_TOUCH } from '../../../src/modes/state';
import { HINTS } from '../../../src/modes/ui';
import { makeTestContext, type TestContext } from '../../harness/context';
import { fixtureModel, fixturePresentation } from './synthetic';

const PRES: Record<string, string> = { 'bank-v2': 'bank-sampeng-v2', suite: 'presidential-suite', house: 'sukhumvit-house', hotel: 'hotel-lobby' };
const mounted: TestContext[] = [];
function mount(name = 'bank-v2', o: { size?: { width: number; height: number }; options?: Partial<ViewerContext['options']> } = {}) {
  const ctx = makeTestContext({ model: fixtureModel(name), presentation: fixturePresentation(PRES[name]!), ...o });
  mounted.push(ctx);
  const modes = installModes(ctx);
  ctx.modes = modes;
  const q = <T extends Element = HTMLElement>(wt: string) => ctx.ui.root.querySelector(`[data-wt=${wt}]`) as T;
  return { ctx, modes, s: modes.state, q };
}
afterEach(() => { for (const ctx of mounted.splice(0)) ctx.disposer.dispose(); vi.restoreAllMocks(); vi.useRealTimers(); });

const key = (type: 'keydown' | 'keyup', code: string, target: EventTarget = document.body, init: KeyboardEventInit = {}) => {
  const e = new KeyboardEvent(type, { code, bubbles: true, cancelable: true, ...init });
  target.dispatchEvent(e);
  return e;
};
const pointer = (type: string, target: EventTarget, init: PointerEventInit) => {
  const e = new PointerEvent(type, { bubbles: true, cancelable: true, ...init });
  target.dispatchEvent(e);
  return e;
};
const text = (e: Element | null) => e?.textContent ?? null;
const shown = (e: HTMLElement) => e.style.display !== 'none' && e.style.display !== '';
const flags = (ctx: TestContext) => ['fp', 'camopen', 'crowded', 'touchui'].filter(f => ctx.ui.root.hasAttribute(`data-${f}`));

/** A 2D canvas and toBlob for happy-dom (it has neither), so takePhoto runs end to end on the fake renderer. */
function stubCanvas() {
  const drawn: number[][] = [];
  vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockImplementation(function (this: HTMLCanvasElement) {
    return { drawImage: (...a: number[]) => { drawn.push(a.slice(1)); } } as unknown as CanvasRenderingContext2D;
  } as unknown as HTMLCanvasElement['getContext']);
  Object.defineProperty(HTMLCanvasElement.prototype, 'toBlob', {
    configurable: true, writable: true,
    value: function (this: HTMLCanvasElement, cb: (b: Blob | null) => void) { const { width, height } = this; queueMicrotask(() => cb(new Blob([`${width}x${height}`], { type: 'image/png' }))); },
  });
  return drawn;
}
const flush = () => new Promise(r => setTimeout(r, 0));

describe('markup: the modes row, the overlays, the Camera panel (selectors and texts of D-11.6)', { timeout: 60_000 }, () => {
  it('puts the modes row into the slot `modes`, Orbit pressed', () => {
    const { ctx, q } = mount();
    const slot = ctx.panel.slot('modes');
    expect(text(slot.querySelector('.vm-label'))).toBe('Look around');
    const row = q('modes');
    expect(row.parentElement).toBe(slot);
    expect([...row.querySelectorAll('button')].map(b => [b.textContent, b.getAttribute('data-mode'), b.getAttribute('aria-pressed')])).toEqual([
      ['Orbit', 'orbit', 'true'], ['Walk', 'walk', 'false'], ['Ghost', 'ghost', 'false'], ['Camera', null, 'false'],
    ]);
    expect(q('camera-btn').textContent).toBe('Camera');
  });

  it('puts the overlays into the root with the prototype texts', () => {
    const { ctx, q } = mount();
    for (const wt of ['hud', 'cross', 'frame', 'flash', 'stick', 'updown', 'camera-panel']) expect(q(wt).parentElement).toBe(ctx.ui.root);
    expect(text(q('hud-camera'))).toBe('Camera');
    expect(q('hud-camera').classList.contains('vm-narrow')).toBe(true);
    expect(text(q('exit'))).toBe('Exit');
    expect(q('frame').querySelectorAll('i')).toHaveLength(4);
    expect(q('stick').querySelector('b')).not.toBeNull();
    expect([text(q('snap')), q('snap').style.display]).toEqual(['Photo', 'none']);
    expect([...q('updown').children].map(c => c.getAttribute('data-wt'))).toEqual(['snap', 'up', 'down']);
    const cam = q('camera-panel');
    expect(text(cam.querySelector('h2'))).toBe('Camera ×');
    expect([text(q('camera-close')), q('camera-close').title]).toEqual(['×', 'Close']);
    const lens = q<HTMLInputElement>('lens');
    expect([lens.type, lens.min, lens.max, lens.step]).toEqual(['range', '12', '85', '1']);
    expect([...cam.querySelectorAll('[data-wt=lens-preset]')].map(b => [b.textContent, b.getAttribute('data-mm')])).toEqual([['16', '16'], ['24', '24'], ['35', '35'], ['50', '50']]);
    const eye = q<HTMLInputElement>('eye'), tilt = q<HTMLInputElement>('tilt');
    expect([eye.min, eye.max, eye.step, tilt.min, tilt.max, tilt.step]).toEqual(['0.8', '2.2', '0.05', '-60', '60', '1']);
    expect(text(q<HTMLInputElement>('straight').parentElement)).toBe(' Straight verticals');
    expect(text(q('first-note'))).toBe('Height and tilt work in Walk and Ghost. In Orbit, drag to set the angle.');
    expect([...q<HTMLSelectElement>('frame-select').options].map(o => [o.value, o.text])).toEqual([
      ['screen', 'Whole screen'], ['16:9', '16:9'], ['3:2', '3:2'], ['4:3', '4:3'], ['1:1', '1:1'], ['4:5', '4:5'], ['9:16', '9:16'],
    ]);
    expect([...q<HTMLSelectElement>('size-select').options].map(o => [o.value, o.text])).toEqual([['1920', 'HD'], ['3840', '4K']]);
    expect([q<HTMLSelectElement>('frame-select').value, q<HTMLSelectElement>('size-select').value, q<HTMLInputElement>('grid').checked]).toEqual(['3:2', '1920', true]);
    expect(text(q<HTMLInputElement>('grid').parentElement)).toBe(' Thirds grid');
    expect(text(q('shot'))).toBe('Take photo (P)');
    const labels = [...cam.querySelectorAll('.vm-f > div:first-child > span:first-child')].map(e => e.textContent);
    expect(labels).toEqual(['Lens', 'Eye height', 'Tilt', 'Frame and size']);
    expect(ctx.ui.root.querySelector('style')!.textContent).toContain(MODES_CSS.trim());
  });

  it('starts in Orbit: the hint, no flags, the HUD hidden, the 33 mm Orbit lens', () => {
    const { ctx, s, q } = mount();
    expect(ctx.ui.hint.textContent).toBe(HINTS.orbit);
    expect(ctx.ui.hint.textContent).toBe('Drag to orbit · right-drag to pan · scroll to zoom · double-click a floor to walk there · 1 / 2 / 3: Orbit / Walk / Ghost · P: photo');
    expect(flags(ctx)).toEqual([]);
    expect(q('hud').style.display).toBe('none');
    expect([s.mode, s.floor.key, s.orbitLens, s.lens, s.eye, s.frame, s.size, s.grid, s.ghostSpeed]).toEqual(['orbit', 'L1', 33, 24, 1.6, '3:2', 1920, true, 6]);
    expect(ctx.camera.fov).toBeCloseTo(lensFov(33), 9);
    expect(ctx.camera.rotation.order).toBe('YXZ');
    expect(text(q('lens-value'))).toBe(`33 mm · ${Math.round(2 * Math.atan(Math.tan(lensFov(33) * D2R / 2) * 1400 / 880) / D2R)}° wide`);
    expect(q('first').classList.contains('vm-off')).toBe(true);
    expect(q('first-note').style.display).toBe('block');
  });
});

describe('modes: Walk, Ghost, Orbit', { timeout: 120_000 }, () => {
  it.each(['bank-v2', 'suite', 'house', 'hotel'])('%s: Walk starts on the first floor at eye height, on the floor, with room around you', name => {
    const { ctx, modes, s } = mount(name);
    modes.setMode('walk');
    const first = ctx.floors[0]!;
    expect([s.mode, s.floor.key]).toEqual(['walk', first.key]);
    expect(s.pos.y).toBeCloseTo(first.level + 1.6, 9);
    expect(modes.probe.onFloor()).toBe(true);
    expect(modes.probe.clearance()).toBeGreaterThanOrEqual(name === 'house' ? 0.99 : 0.5);
    if (name === 'house') expect(modes.probe.open()).toBeGreaterThanOrEqual(3);
    expect(modes.probe.visible()).toEqual(ctx.floors.map(f => f.key));
  });

  it('Walk: the HUD, the flags, the hint, the camera; Ghost; back to Orbit where you left it', () => {
    const { ctx, modes, s, q } = mount();
    const pos0 = ctx.camera.position.clone(), target0 = ctx.controls.target.clone();
    modes.setMode('walk');
    expect(flags(ctx)).toEqual(['fp']);
    expect(q('hud').style.display).toBe('flex');
    expect(q('cross').style.display).toBe('block');
    expect(text(q('hud-text'))).toBe('Walk · Level 1 · drag or click to look · W A S D to move, Shift to run, Space to jump · PgUp / PgDn: other floor · wheel: lens 24 mm · Esc');
    expect(q('hud-text').querySelector('b')!.textContent).toBe('Walk');
    expect(q('hud-text').querySelector('.vm-more')!.textContent).toBe(' · drag or click to look · W A S D to move, Shift to run, Space to jump · PgUp / PgDn: other floor · wheel: lens 24 mm · Esc');
    expect(ctx.ui.hint.textContent).toBe('Click to capture the mouse (Esc frees it, Esc again returns to Orbit) · 1 / 2 / 3: Orbit / Walk / Ghost · P: photo');
    expect(q('modes').querySelector('[data-mode=walk]')!.getAttribute('aria-pressed')).toBe('true');
    expect(q('modes').querySelector('[data-mode=orbit]')!.getAttribute('aria-pressed')).toBe('false');
    expect([ctx.camera.near, ctx.controls.enabled, s.pitch]).toEqual([0.05, false, 0]);
    expect(ctx.camera.position.toArray()).toEqual(s.pos.toArray());
    expect(ctx.camera.fov).toBeCloseTo(lensFov(24), 9);
    expect(s.saved!.pos.toArray()).toEqual(pos0.toArray());
    modes.setMode('ghost');
    expect(text(q('hud-text'))).toBe('Ghost · through walls · W A S D · Space up, C down · Shift fast · wheel: speed 6.0 m/s · Esc');
    expect(q('eye').parentElement!.classList.contains('vm-off')).toBe(true);
    expect(q('first').classList.contains('vm-off')).toBe(false);
    modes.setMode('orbit');
    expect(flags(ctx)).toEqual([]);
    expect([ctx.camera.near, ctx.controls.enabled]).toEqual([0.1, true]);
    expect(ctx.camera.position.distanceTo(pos0)).toBeLessThan(1e-9);
    expect(ctx.controls.target.distanceTo(target0)).toBeLessThan(1e-9);
    expect(ctx.ui.hint.textContent).toBe(HINTS.orbit);
    expect(ctx.camera.fov).toBeCloseTo(lensFov(33), 9);
  });

  it('Orbit to Ghost starts at the camera, looking where it looked', () => {
    const { ctx, modes, s } = mount();
    const dir = ctx.controls.target.clone().sub(ctx.camera.position).normalize();
    const pos0 = ctx.camera.position.clone();
    modes.setMode('ghost');
    expect(s.pos.toArray()).toEqual(pos0.toArray());
    expect(s.yaw).toBeCloseTo(Math.atan2(-dir.x, -dir.z), 12);
    expect(s.pitch).toBeCloseTo(Math.asin(dir.y), 12);
  });

  it('Ghost then Walk lands you on a floor (from far outside: the middle of the floor)', () => {
    const { modes, s } = mount();
    modes.setMode('ghost');
    s.pos.set(300, 40, 300);
    modes.setMode('walk');
    expect(s.mode).toBe('walk');
    expect(s.floor.key).toBe('L2');                       // 40 m up: the floor below you is the top one
    expect(modes.probe.onFloor()).toBe(true);
    expect(s.pos.y).toBeCloseTo(s.floor.level + 1.6, 9);
  });

  it('Walk shows the walked stack; floors and goToFloor / changeFloor; Ghost keeps your height relative to the floor', () => {
    const { ctx, modes, s } = mount();
    const [L1, L2] = ctx.floors;
    ctx.visibility.setFloorMode('L2');
    modes.setMode('walk', { floor: L1 });
    expect(modes.probe.visible()).toEqual(['L1', 'L2']);
    modes.goToFloor('L2');
    expect([s.floor.key, s.pos.y]).toEqual(['L2', L2!.level + 1.6]);
    modes.goToFloor('L2');
    expect(s.floor.key).toBe('L2');
    modes.changeFloor(1);
    expect(s.floor.key).toBe('L2');                       // the top floor stays
    modes.changeFloor(-1);
    expect(s.floor.key).toBe('L1');
    modes.goToFloor('nope');
    expect(s.floor.key).toBe('L1');
    modes.setMode('orbit');
    expect(modes.probe.visible()).toEqual(['L2']);       // restoreVisibility: the floor mode again
    modes.goToFloor('L1');
    expect(s.mode).toBe('orbit');
    ctx.visibility.setFloorMode('all');
    modes.setMode('ghost');
    expect(s.floor.key).toBe('L1');
    s.pos.y = L1!.level + 2;
    modes.goToFloor('L2');                                // Ghost: up by the level difference, the same height above it
    expect(s.pos.y).toBeCloseTo(L2!.level + 2, 9);
    expect(s.floor.key).toBe('L2');
    modes.changeFloor(-1);
    expect(s.pos.y).toBeCloseTo(L1!.level + 2, 9);
  });

  it('double-click in Orbit walks to the spot', () => {
    const { ctx, modes, s } = mount();
    ctx.canvas.getBoundingClientRect = () => ({ left: 0, top: 0, right: 1400, bottom: 880, width: 1400, height: 880, x: 0, y: 0, toJSON: () => ({}) });
    ctx.camera.updateMatrixWorld();
    ctx.canvas.dispatchEvent(new MouseEvent('dblclick', { clientX: 700, clientY: 440, bubbles: true }));
    expect(s.mode).toBe('walk');
    expect(modes.probe.onFloor()).toBe(true);
    modes.setMode('orbit');
    modes.lock(true);
    ctx.canvas.dispatchEvent(new MouseEvent('dblclick', { clientX: 700, clientY: 440, bubbles: true }));
    expect(s.mode).toBe('orbit');
  });
});

describe('keys', { timeout: 60_000 }, () => {
  it('1 / 2 / 3 from the body; PgUp / PgDn; Esc back to Orbit', () => {
    const { ctx, s } = mount();
    key('keydown', 'Digit2');
    expect([s.mode, s.floor.key]).toEqual(['walk', 'L1']);
    const pg = key('keydown', 'PageUp');
    expect([s.floor.key, pg.defaultPrevented]).toEqual(['L2', true]);
    key('keydown', 'PageDown');
    expect(s.floor.key).toBe('L1');
    key('keydown', 'Digit3');
    expect(s.mode).toBe('ghost');
    key('keydown', 'Escape');
    expect(s.mode).toBe('orbit');
    key('keydown', 'Digit2', document.documentElement);
    expect(s.mode).toBe('walk');
    key('keydown', 'Digit1', ctx.ui.root);
    expect(s.mode).toBe('orbit');
    key('keydown', 'Digit3', ctx.canvas);
    expect(s.mode).toBe('ghost');
  });

  it("a key whose target is the host's own control (outside the root) is not the viewer's", () => {
    const { s } = mount();
    const host = document.createElement('button');
    document.body.append(host);
    key('keydown', 'Digit2', host);
    expect(s.mode).toBe('orbit');
    host.remove();
  });

  it('typing: text, number and search boxes, and arrows on a slider or a list, keep their keys', () => {
    const { ctx, s, q } = mount();
    const box = document.createElement('input');
    ctx.ui.root.append(box);
    key('keydown', 'Digit2', box);
    expect(s.mode).toBe('orbit');
    for (const type of ['text', 'number', 'search']) { box.type = type; key('keydown', 'Digit2', box); expect(s.mode).toBe('orbit'); }
    const lens = q<HTMLInputElement>('lens');
    key('keydown', 'Digit2', lens);
    expect(s.mode).toBe('walk');
    key('keydown', 'ArrowUp', lens);
    expect(s.keys.has('ArrowUp')).toBe(false);
    const sel = q<HTMLSelectElement>('frame-select');
    const p = key('keydown', 'KeyW', sel);
    expect([s.keys.has('KeyW'), p.defaultPrevented]).toEqual([true, true]);   // a focused list does not jump to an option
    key('keyup', 'KeyW', sel);
    expect(s.keys.has('KeyW')).toBe(false);
    const tab = key('keydown', 'Tab', sel);
    expect(tab.defaultPrevented).toBe(false);
    key('keydown', 'Digit1', document.body, { ctrlKey: true });
    key('keydown', 'Digit1', document.body, { altKey: true });
    key('keydown', 'Digit1', document.body, { metaKey: true });
    expect(s.mode).toBe('walk');
  });

  it('held keys, Space and the arrows do not scroll or press; Space up does not tick a focused checkbox', () => {
    const { ctx, s, q } = mount();
    key('keydown', 'Digit2');
    const down = key('keydown', 'Space');
    expect([s.keys.has('Space'), down.defaultPrevented]).toEqual([true, true]);
    const tick = q<HTMLInputElement>('grid');
    const up = key('keyup', 'Space', tick);
    expect([s.keys.has('Space'), up.defaultPrevented]).toEqual([false, true]);
    const host = document.createElement('button');
    document.body.append(host);
    expect(key('keyup', 'Space', host).defaultPrevented).toBe(false);    // the host's button keeps its Space
    host.remove();
    key('keydown', 'KeyW');
    window.dispatchEvent(new Event('blur'));
    expect(s.keys.size).toBe(0);
    key('keydown', 'Digit1');
    expect(key('keyup', 'Space').defaultPrevented).toBe(false);          // Orbit: Space is not the viewer's
    expect(ctx.ui.root.contains(tick)).toBe(true);
  });

  it('Space in Walk hops on the press itself: the eye rises about 0.6 m and comes back; a held Space is one hop; Ghost keeps Space for up', () => {
    const { modes, s } = mount();
    key('keydown', 'Digit2');
    const y0 = s.pos.y;
    let t = s.last;
    const frames = (n: number) => { let top = -Infinity; for (let i = 0; i < n; i++) { t += 1000 / 60; modes.tick(t); top = Math.max(top, s.pos.y); } return top; };
    key('keydown', 'Space'); key('keyup', 'Space');             // a tap between two frames is not lost
    const top = frames(60);
    expect(top - y0).toBeGreaterThan(0.55);
    expect(top - y0).toBeLessThan(0.61);
    expect(Math.abs(s.pos.y - y0)).toBeLessThan(1e-9);           // back on the floor
    key('keydown', 'Space');
    for (let i = 0; i < 5; i++) key('keydown', 'Space', document.body, { repeat: true });
    frames(60);
    key('keyup', 'Space');
    expect(frames(10)).toBeCloseTo(y0, 9);                     // the held key gave one hop, now over
    key('keydown', 'Digit3');
    const g0 = s.pos.y;
    key('keydown', 'Space'); frames(6); key('keyup', 'Space');
    expect(s.pos.y).toBeGreaterThan(g0);                         // Ghost: Space still rises
    key('keydown', 'Digit2');
    expect(frames(30)).toBeLessThan(s.floor.level + s.eye + 1e-6); // and Walk starts on the floor, no hop carried over
  });

  it('nothing while locked; Esc while the pointer is locked does not leave Walk', () => {
    const { ctx, modes, s } = mount();
    modes.lock(true);
    key('keydown', 'Digit2');
    expect(s.mode).toBe('orbit');
    modes.lock(false);
    key('keydown', 'Digit2');
    Object.defineProperty(document, 'pointerLockElement', { configurable: true, get: () => ctx.canvas });
    key('keydown', 'Escape');
    expect(s.mode).toBe('walk');
    Object.defineProperty(document, 'pointerLockElement', { configurable: true, get: () => null });
    document.dispatchEvent(new Event('pointerlockchange'));
    key('keydown', 'Escape');
    expect(s.mode).toBe('orbit');
  });
});

describe('looking around, touch, the wheel', { timeout: 60_000 }, () => {
  it('a mouse drag turns the way you move; touch drags the scene; a drag over 4 px does not lock the pointer', () => {
    const { ctx, modes, s } = mount();
    modes.setMode('walk');
    const locks = vi.fn();
    ctx.canvas.requestPointerLock = locks as unknown as HTMLCanvasElement['requestPointerLock'];
    const yaw0 = s.yaw, pitch0 = s.pitch;
    pointer('pointerdown', ctx.canvas, { pointerId: 1, pointerType: 'mouse', clientX: 100, clientY: 100 });
    pointer('pointermove', window, { pointerId: 1, pointerType: 'mouse', clientX: 102, clientY: 101 });
    expect(s.dragMoved).toBe(false);
    pointer('pointermove', window, { pointerId: 1, pointerType: 'mouse', clientX: 110, clientY: 104 });
    expect(s.dragMoved).toBe(true);
    expect(s.yaw).toBeCloseTo(yaw0 - 10 * LOOK, 12);
    expect(s.pitch).toBeCloseTo(pitch0 - 4 * LOOK, 12);
    pointer('pointerup', window, { pointerId: 1, pointerType: 'mouse' });
    expect(s.drag).toBeNull();
    ctx.canvas.dispatchEvent(new PointerEvent('click', { pointerType: 'mouse', bubbles: true }));
    expect(locks).not.toHaveBeenCalled();
    pointer('pointerdown', ctx.canvas, { pointerId: 2, pointerType: 'mouse', clientX: 100, clientY: 100 });
    pointer('pointerup', window, { pointerId: 2, pointerType: 'mouse' });
    ctx.canvas.dispatchEvent(new PointerEvent('click', { pointerType: 'mouse', bubbles: true }));
    expect(locks).toHaveBeenCalledTimes(1);
    const y1 = s.yaw;
    pointer('pointerdown', ctx.canvas, { pointerId: 3, pointerType: 'touch', clientX: 100, clientY: 100 });
    pointer('pointermove', window, { pointerId: 3, pointerType: 'touch', clientX: 120, clientY: 100 });
    expect(s.yaw).toBeCloseTo(y1 + 20 * LOOK_TOUCH, 12);
    pointer('pointercancel', window, { pointerId: 3, pointerType: 'touch' });
    expect(s.drag).toBeNull();
  });

  it('the pitch stays within 85 degrees (35 with straight verticals); a 300 px mouse jump is ignored', () => {
    const { ctx, modes, s } = mount();
    modes.setMode('walk');
    Object.defineProperty(document, 'pointerLockElement', { configurable: true, get: () => ctx.canvas });
    document.dispatchEvent(new MouseEvent('mousemove', { movementX: 0, movementY: -5000 }));
    expect(s.pitch).toBe(0);
    for (let i = 0; i < 20; i++) document.dispatchEvent(new MouseEvent('mousemove', { movementX: 0, movementY: -200 }));
    expect(s.pitch).toBeCloseTo(85 * D2R, 12);
    Object.defineProperty(document, 'pointerLockElement', { configurable: true, get: () => null });
    s.straight = true;
    modes.setMode('ghost');
    expect(s.pitch).toBeCloseTo(35 * D2R, 12);
  });

  it('a touch shows the stick and the floor buttons, a mouse hides them; their texts in Walk and Ghost', () => {
    const { ctx, modes, s, q } = mount();
    modes.setMode('walk');
    pointer('pointerdown', ctx.ui.root, { pointerType: 'touch', pointerId: 5 });
    expect(s.touch).toBe(true);
    expect(flags(ctx)).toEqual(['fp', 'touchui']);
    expect([shown(q('stick')), q('updown').style.display]).toEqual([true, 'flex']);
    expect([text(q('up')), text(q('down'))]).toEqual(['Upstairs', 'Downstairs']);
    expect([q('up').classList.contains('vm-off'), q('down').classList.contains('vm-off')]).toEqual([false, true]);
    expect(text(q('hud-text'))).toBe('Walk · Level 1 · drag to look · stick to move');
    expect(ctx.ui.hint.textContent).toBe('Drag to look · stick to move · Exit (top) returns to Orbit');
    pointer('pointerdown', q('up'), { pointerType: 'touch', pointerId: 6 });
    expect(s.floor.key).toBe('L2');
    expect([q('up').classList.contains('vm-off'), q('down').classList.contains('vm-off')]).toEqual([true, false]);
    pointer('pointerdown', q('down'), { pointerType: 'touch', pointerId: 7 });
    expect(s.floor.key).toBe('L1');
    modes.setMode('ghost');
    expect([text(q('up')), text(q('down'))]).toEqual(['Up', 'Down']);
    expect(text(q('hud-text'))).toBe('Ghost · through walls · drag to look · stick to fly');
    pointer('pointerdown', q('up'), { pointerType: 'touch', pointerId: 8 });
    expect(s.vert).toBe(1);
    pointer('pointerup', q('up'), { pointerType: 'touch', pointerId: 8 });
    expect(s.vert).toBe(0);
    modes.openCam(true);
    expect(q('snap').style.display).toBe('block');
    modes.setMode('orbit');
    expect(ctx.ui.hint.textContent).toBe('Drag to orbit · pinch to zoom · Walk or Ghost to look around inside');
    pointer('pointerdown', ctx.ui.root, { pointerType: 'mouse', pointerId: 9 });
    expect(s.touch).toBe(false);
    expect(ctx.ui.hint.textContent).toBe(HINTS.orbit);
  });

  it('the stick: how far you push sets the speed (dead zone 0.15); letting go stops', () => {
    const { modes, s, q } = mount();
    modes.setMode('walk');
    const stick = q('stick');
    stick.getBoundingClientRect = () => ({ left: 22, top: 600, right: 142, bottom: 720, width: 120, height: 120, x: 22, y: 600, toJSON: () => ({}) });
    pointer('pointerdown', stick, { pointerId: 4, pointerType: 'touch', clientX: 82, clientY: 600 });
    expect(s.stick.y).toBeCloseTo(-1, 12);
    expect(q('stick').querySelector('b')!.style.transform).toBe('translate(0px, -36px)');
    pointer('pointermove', stick, { pointerId: 4, pointerType: 'touch', clientX: 82, clientY: 655 });
    expect(s.stick.y).toBeCloseTo(-5 / 60, 12);
    s.last = 0;
    const p0 = s.pos.clone();
    modes.tick(1000);                                     // inside the dead zone: no move
    expect(s.pos.distanceTo(p0)).toBe(0);
    pointer('pointerup', stick, { pointerId: 4, pointerType: 'touch' });
    expect(s.stick).toEqual({ id: null, x: 0, y: 0 });
    expect(q('stick').querySelector('b')!.style.transform).toBe('');
  });

  it('wheel: Walk lens 2 mm per 100 px (lines x 40), Ghost speed x 1.2^(-px / 100) within 0.5 - 60', () => {
    const { ctx, modes, s, q } = mount();
    const wheel = (deltaY: number, init: WheelEventInit = {}) => {
      const e = new WheelEvent('wheel', { deltaY, cancelable: true, bubbles: true, ...init });
      if (init.shiftKey) Object.defineProperty(e, 'shiftKey', { value: true });   // happy-dom's WheelEvent drops it
      ctx.canvas.dispatchEvent(e);
      return e;
    };
    wheel(-100);                                          // Orbit: the controls' zoom, not the lens
    expect([s.lens, s.orbitLens]).toEqual([24, 33]);
    modes.setMode('walk');
    for (let i = 0; i < 10; i++) wheel(-4);
    expect(s.lens).toBeCloseTo(24.8, 9);
    expect(wheel(-100).defaultPrevented).toBe(true);
    expect(s.lens).toBeCloseTo(26.8, 9);
    wheel(1, { deltaMode: 1 });
    expect(s.lens).toBeCloseTo(26, 9);
    wheel(0, { deltaX: -50, shiftKey: true });
    expect(s.lens).toBeCloseTo(27, 9);
    expect(text(q('hud-text'))).toContain('wheel: lens 27 mm');
    modes.setMode('ghost');
    wheel(-100);
    expect(s.ghostSpeed).toBeCloseTo(7.2, 9);
    expect(text(q('hud-text'))).toContain('wheel: speed 7.2 m/s');
    for (let i = 0; i < 50; i++) wheel(-1000);
    expect(s.ghostSpeed).toBe(60);
    for (let i = 0; i < 50; i++) wheel(1000);
    expect(s.ghostSpeed).toBe(0.5);
  });

  it('contextmenu: no menu in Walk and Ghost (the controls, off there, take it in Orbit)', () => {
    const { ctx, modes } = mount();
    const menu = () => { const e = new MouseEvent('contextmenu', { cancelable: true, bubbles: true }); ctx.canvas.dispatchEvent(e); return e.defaultPrevented; };
    modes.setMode('walk');
    expect(ctx.controls.enabled).toBe(false);
    expect(menu()).toBe(true);
    modes.setMode('ghost');
    expect(menu()).toBe(true);
  });
});

describe('tick', { timeout: 60_000 }, () => {
  it('Walk: 1.5 m/s, Shift 3.4 m/s, dt capped at 0.05 s; a time going backwards moves nothing', () => {
    const { modes, s } = mount('house');
    modes.setMode('walk');
    const ahead = modes.probe.open();
    expect(ahead).toBeGreaterThan(1);
    s.keys.add('KeyW');
    let p = s.pos.clone();
    s.last = 1000; modes.tick(1020);
    expect(s.pos.distanceTo(p)).toBeCloseTo(1.5 * 0.02, 6);
    p = s.pos.clone();
    modes.tick(5000);
    expect(s.pos.distanceTo(p)).toBeCloseTo(1.5 * 0.05, 6);
    s.keys.add('ShiftLeft');
    p = s.pos.clone();
    modes.tick(5040);
    expect(s.pos.distanceTo(p)).toBeCloseTo(3.4 * 0.04, 6);
    p = s.pos.clone();
    modes.tick(4000);
    expect(s.pos.distanceTo(p)).toBe(0);
    expect(s.pos.y).toBeCloseTo(s.floor.level + s.eye, 9);
  });

  it('Ghost: 6 m/s, Shift x 3; Space / E up, C / Q down; the camera follows', () => {
    const { ctx, modes, s } = mount();
    modes.setMode('ghost');
    s.last = 0;
    const y0 = s.pos.y;
    s.keys.add('Space'); modes.tick(50);
    expect(s.pos.y - y0).toBeCloseTo(6 * 0.05, 9);
    s.keys.clear(); s.keys.add('KeyQ'); s.keys.add('ShiftRight'); modes.tick(100);
    expect(s.pos.y - y0).toBeCloseTo(0.3 - 18 * 0.05, 9);
    s.keys.clear(); s.keys.add('KeyE'); s.keys.add('KeyC'); const y1 = s.pos.y; modes.tick(150);
    expect(s.pos.y).toBe(y1);
    expect(ctx.camera.position.toArray()).toEqual(s.pos.toArray());
  });

  it('Orbit: the controls update (damping)', () => {
    const { ctx, modes } = mount();
    const update = vi.spyOn(ctx.controls, 'update');
    modes.tick(16);
    expect(update).toHaveBeenCalledTimes(1);
  });
});

describe('the Camera panel', { timeout: 60_000 }, () => {
  it('opens and closes from its buttons; aria-pressed; the frame and its size; crowded flag', () => {
    const { ctx, modes, s, q } = mount();
    q('camera-btn').click();
    expect([s.camOpen, q('camera-panel').style.display, q('camera-btn').getAttribute('aria-pressed')]).toEqual([true, 'block', 'true']);
    expect(flags(ctx)).toEqual(['camopen']);
    expect(text(q('px'))).toBe('1920 × 1280 px');
    expect(q('frame').classList.contains('vm-crop')).toBe(true);
    expect(q('frame').style.display).toBe('block');
    q<HTMLSelectElement>('size-select').value = '3840';
    q('size-select').dispatchEvent(new Event('change'));
    expect([s.size, text(q('px'))]).toEqual([3840, '3840 × 2560 px']);
    q<HTMLSelectElement>('frame-select').value = '9:16';
    q('frame-select').dispatchEvent(new Event('change'));
    expect([s.frame, text(q('px'))]).toEqual(['9:16', '2160 × 3840 px']);
    q<HTMLSelectElement>('frame-select').value = 'screen';
    q('frame-select').dispatchEvent(new Event('change'));
    expect([q('frame').classList.contains('vm-crop'), q('frame').style.display]).toEqual([false, 'block']);   // the grid alone
    q<HTMLInputElement>('grid').checked = false;
    q('grid').dispatchEvent(new Event('change'));
    expect([s.grid, q('frame').style.display]).toEqual([false, 'none']);
    q('camera-close').click();
    expect([s.camOpen, q('camera-panel').style.display, q('frame').style.display, q('camera-btn').getAttribute('aria-pressed')]).toEqual([false, 'none', 'none', 'false']);
    modes.setMode('walk');
    q('hud-camera').click();
    expect(s.camOpen).toBe(true);
    expect(q('cross').style.display).toBe('none');
    q('hud-camera').click();
    expect(s.camOpen).toBe(false);
    const narrowish = mount('bank-v2', { size: { width: 1100, height: 700 } });
    narrowish.modes.openCam(true);
    expect(flags(narrowish.ctx)).toEqual(['camopen', 'crowded']);
  });

  it('lens: the slider, the presets, the bounds; Orbit and Walk have their own lens', () => {
    const { ctx, modes, s, q } = mount();
    q<HTMLButtonElement>('lens-preset').click();
    expect(s.orbitLens).toBe(16);
    expect(ctx.camera.fov).toBeCloseTo(lensFov(16), 9);
    modes.setMode('walk');
    expect(s.lens).toBe(24);
    const fifty = q('camera-panel').querySelector('[data-mm="50"]') as HTMLButtonElement;
    fifty.click();
    expect([s.lens, s.orbitLens]).toEqual([50, 16]);
    expect(ctx.camera.fov).toBeCloseTo(lensFov(50), 9);
    expect(text(q('lens-value'))).toMatch(/^50 mm · \d+° wide$/);
    const lens = q<HTMLInputElement>('lens');
    lens.value = '35'; lens.dispatchEvent(new Event('input'));
    expect(s.lens).toBe(35);
    expect(text(q('hud-text'))).toContain('wheel: lens 35 mm');
    modes.setMode('orbit');
    expect(ctx.camera.fov).toBeCloseTo(lensFov(16), 9);
    expect(lens.value).toBe('16');
  });

  it('eye height, tilt and straight verticals (a level camera and a shifted picture)', () => {
    const { ctx, modes, s, q } = mount();
    modes.setMode('walk');
    modes.openCam(true);
    const eye = q<HTMLInputElement>('eye');
    eye.value = '1.2'; eye.dispatchEvent(new Event('input'));
    expect(s.pos.y).toBeCloseTo(s.floor.level + 1.2, 9);
    expect(text(q('eye-value'))).toBe('1.20 m');
    const tilt = q<HTMLInputElement>('tilt');
    tilt.value = '15'; tilt.dispatchEvent(new Event('input'));
    expect(ctx.camera.rotation.x).toBeCloseTo(15 * D2R, 12);
    expect(ctx.camera.view?.enabled ?? false).toBe(false);
    expect(text(q('tilt-value'))).toBe('15°');
    const straight = q<HTMLInputElement>('straight');
    straight.checked = true; straight.dispatchEvent(new Event('change'));
    expect(ctx.camera.rotation.x).toBe(0);
    expect(ctx.camera.view!.enabled).toBe(true);
    expect(ctx.camera.view!.offsetY).toBeLessThan(0);
    expect(modes.probe.camera().offsetY).toBeLessThan(0);
    tilt.value = '60'; tilt.dispatchEvent(new Event('input'));
    expect(s.pitch).toBeCloseTo(35 * D2R, 12);
    expect(text(q('tilt-value'))).toBe('35°');
    straight.checked = false; straight.dispatchEvent(new Event('change'));
    expect(modes.probe.camera().offsetY).toBeNull();
  });

  it('opening waits for the replay: while locked it only records camWanted; lock(false) opens it', () => {
    const { modes, s, q } = mount();
    modes.setMode('walk');
    modes.openCam(true);
    modes.lock(true);
    expect([s.locked, s.mode, s.camOpen]).toEqual([true, 'orbit', false]);
    modes.openCam(true);
    expect([s.camOpen, s.camWanted, q('camera-panel').style.display]).toEqual([false, true, 'none']);
    modes.lock(false);
    expect([s.locked, s.camOpen, s.camWanted, q('camera-panel').style.display]).toEqual([false, true, false, 'block']);
  });
});

describe('photos (a stubbed 2D canvas on the fake renderer)', { timeout: 60_000 }, () => {
  it('P takes one photo (held P: still one), named and sized, downloaded, with a thumbnail and the photo event', async () => {
    const drawn = stubCanvas();
    const { ctx, modes, q } = mount();
    const events: PhotoResult[] = [];
    ctx.events.on('photo', p => events.push(p));
    const frames0 = ctx.renderer.info.render.frame;
    key('keydown', 'KeyP');
    key('keydown', 'KeyP', document.body, { repeat: true });
    await flush();
    expect(events).toHaveLength(1);
    const want = outSize({ w: 1400, h: 880 }, 1920);
    expect(events[0]).toMatchObject({ width: want.w, height: want.h });
    expect(events[0]!.name).toMatch(/^BangkokBank-Sampeng_Orbit_overview_33mm_\d{4}-\d\d-\d\d_\d\d-\d\d-\d\d\.png$/);
    expect(ctx.kit.downloads.map(d => d.fileName)).toEqual([events[0]!.name]);
    // 1920 x 1207 in screen-sized tiles (1400 x 880), each read from the top left of the drawing buffer; then the screen again
    expect(ctx.renderer.info.render.frame - frames0).toBe(4 + 1);
    expect(drawn).toEqual([[0, 0, 1400, 880, 0, 0, 1400, 880], [0, 0, 520, 880, 1400, 0, 520, 880], [0, 0, 1400, 327, 0, 880, 1400, 327], [0, 0, 520, 327, 1400, 880, 520, 327]]);
    const img = q('photos').querySelector('img')!;
    expect(img.title).toBe(`${events[0]!.name} (${want.w} x ${want.h}) - click to save again`);
    img.click();
    expect(ctx.kit.downloads).toHaveLength(2);
    expect(ctx.camera.view?.enabled ?? false).toBe(false);        // no leftover crop
    expect(ctx.renderer.getPixelRatio()).toBe(1);
    expect(modes.state.locked).toBe(false);
  });

  it('the frame only applies with the Camera panel open: 3:2 HD 1920 x 1280, 4K 3840 x 2560, 9:16 2160 x 3840; Walk names the floor', async () => {
    stubCanvas();
    const { modes, s } = mount();
    modes.openCam(true);
    expect(await modes.takePhoto()).toMatchObject({ width: 1920, height: 1280 });
    s.size = 3840;
    expect(await modes.takePhoto()).toMatchObject({ width: 3840, height: 2560 });
    s.frame = '9:16';
    expect(await modes.takePhoto()).toMatchObject({ width: 2160, height: 3840 });
    s.frame = '3:2'; s.size = 1920;
    modes.setMode('walk');
    const w = await modes.takePhoto();
    expect(w!.name).toMatch(/^BangkokBank-Sampeng_Walk_Level-1_24mm_/);
    modes.setMode('ghost');
    s.pos.y = 3.7 + 1.0;
    expect((await modes.takePhoto())!.name).toMatch(/^BangkokBank-Sampeng_Ghost_Level-2_24mm_/);
    modes.openCam(false);
    expect(await modes.takePhoto()).toMatchObject({ width: 1920, height: Math.round(1920 * 880 / 1400) });
  });

  it('nodownload keeps the photo in the panel only; 12 thumbnails at most; nothing while locked', async () => {
    stubCanvas();
    const { ctx, modes, q } = mount('bank-v2', { options: { noDownload: true } });
    for (let i = 0; i < 13; i++) await modes.takePhoto();
    expect(ctx.kit.downloads).toHaveLength(0);
    expect(q('photos').querySelectorAll('img')).toHaveLength(12);
    modes.lock(true);
    expect(await modes.takePhoto()).toBeNull();
    const other = mount();
    other.modes.applyAddress({ nodownload: true });
    await other.modes.takePhoto();
    expect(other.ctx.kit.downloads).toHaveLength(0);
    expect(other.modes.state.noDownload).toBe(true);
  });

  it('a failing photo is reported in the error box, not thrown', async () => {
    const { ctx } = mount();
    vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockImplementation(() => null);
    const errors: string[] = [];
    ctx.events.on('error', e => errors.push(e.message));
    key('keydown', 'KeyP');
    await flush();
    expect(errors).toEqual(['the photo could not be made (no 2D canvas)']);
    expect(ctx.ui.errorBox.hidden).toBe(false);
  });
});

describe('applyAddress (viewer_modes.js applyUrl, D-11.3)', { timeout: 60_000 }, () => {
  it('lens and eye clamped; frame, size, straight, touch, nodownload', () => {
    const { modes, s, q } = mount();
    modes.applyAddress({ lens: 100, eye: 0.2, frame: '4:5', size: 3840, straight: true, touch: true, nodownload: true });
    expect([s.lens, s.eye, s.frame, s.size, s.straight, s.touch, s.noDownload, s.mode]).toEqual([85, 0.8, '4:5', 3840, true, true, true, 'orbit']);
    expect([q<HTMLSelectElement>('frame-select').value, q<HTMLSelectElement>('size-select').value]).toEqual(['4:5', '3840']);
    const b = mount();
    b.modes.applyAddress({ lens: 5, eye: 9, size: 1920 });
    expect([b.s.lens, b.s.eye, b.s.size]).toEqual([12, 2.2, 1920]);
    const c = mount();
    c.modes.applyAddress({ lens: Number.NaN, yaw: Number.NaN, mode: 'walk' });
    expect(c.s.lens).toBe(24);
    expect(Number.isFinite(c.s.yaw)).toBe(true);
  });

  it('mode walk on a floor, at a point (x ?? 0, z ?? 0), facing yaw / pitch (degrees, clamped)', () => {
    const { ctx, modes, s } = mount();
    modes.applyAddress({ mode: 'walk', floor: 'L2', point: { x: 2, y: null, z: -3 }, yaw: 90, pitch: 120 });
    expect([s.mode, s.floor.key]).toEqual(['walk', 'L2']);
    expect(Math.hypot(s.pos.x - 2, s.pos.z + 3)).toBeLessThan(2);
    expect(s.yaw).toBeCloseTo(Math.PI / 2, 12);
    expect(s.pitch).toBeCloseTo(85 * D2R, 12);
    expect(ctx.camera.rotation.y).toBeCloseTo(Math.PI / 2, 12);
    const b = mount();
    b.modes.applyAddress({ mode: 'walk', floor: 'nope', point: { x: null, y: null, z: null } });
    expect([b.s.mode, b.s.floor.key]).toEqual(['walk', 'L1']);
    expect(b.modes.probe.onFloor()).toBe(true);
  });

  it('mode ghost at x, y, z (each ?? the current)', () => {
    const { modes, s } = mount();
    modes.applyAddress({ mode: 'ghost', point: { x: 5, y: 12, z: -3 } });
    expect([s.mode, ...s.pos.toArray()]).toEqual(['ghost', 5, 12, -3]);
    const b = mount();
    const cam = b.ctx.camera.position.clone();
    b.modes.applyAddress({ mode: 'ghost', point: { x: 5, y: null, z: null } });
    expect(b.s.pos.toArray()).toEqual([5, cam.y, cam.z]);
    const c = mount();
    c.modes.applyAddress({ mode: 'ghost' });
    expect(c.s.pos.toArray()).toEqual(c.ctx.camera.position.toArray());
  });

  it('cam=1 opens the Camera panel; during the replay (locked) it waits for lock(false); a locked start stays in Orbit', () => {
    const { modes, s } = mount();
    modes.applyAddress({ cam: true });
    expect(s.camOpen).toBe(true);
    const b = mount();
    b.modes.lock(true);
    b.modes.applyAddress({ cam: true, mode: 'walk' });
    expect([b.s.camOpen, b.s.camWanted, b.s.mode]).toEqual([false, true, 'orbit']);
    b.modes.lock(false);
    expect([b.s.camOpen, b.s.camWanted]).toEqual([true, false]);
  });

  it('shot=1 takes a photo 300 ms after start-up', async () => {
    stubCanvas();
    vi.useFakeTimers();
    const { ctx, modes } = mount();
    const events: PhotoResult[] = [];
    ctx.events.on('photo', p => events.push(p));
    modes.applyAddress({ shot: true });
    await vi.advanceTimersByTimeAsync(299);
    expect(events).toHaveLength(0);
    await vi.advanceTimersByTimeAsync(2);
    expect(events).toHaveLength(1);
  });
});

describe('bus, resize, lock, dispose', { timeout: 60_000 }, () => {
  it('bus `mode` on every HUD update (the viewer filters), with the walked floor', () => {
    const { ctx, modes } = mount();
    const seen: string[] = [];
    ctx.bus.on('mode', e => seen.push(`${e.mode}:${e.floor}`));
    modes.setMode('walk');
    modes.goToFloor('L2');
    (ctx.ui.root.querySelector('[data-mm="35"]') as HTMLButtonElement).click();
    modes.setMode('orbit');
    expect(seen).toEqual(['walk:L1', 'walk:L2', 'walk:L2', 'orbit:L2']);
  });

  it('a listener of bus `mode` that throws is reported and the modes go on', () => {
    const { ctx, modes, s } = mount();
    ctx.bus.on('mode', () => { throw new Error('panel broke'); });
    const errors: string[] = [];
    ctx.events.on('error', e => errors.push(e.message));
    modes.setMode('walk');
    expect(s.mode).toBe('walk');
    expect(errors).toEqual(['panel broke']);
  });

  it('bus `resize` re-applies the projection', () => {
    const { ctx, modes } = mount();
    modes.setMode('walk');
    ctx.camera.aspect = 1; ctx.camera.fov = 70;
    ctx.bus.emit('resize', { width: 1400, height: 880 });
    expect(ctx.camera.aspect).toBeCloseTo(1400 / 880, 12);
    expect(ctx.camera.fov).toBeCloseTo(viewFov(24, 1400 / 880), 12);
  });

  it('lock: Orbit only, the Camera panel closed; no keys, no drag; unlocked again', () => {
    const { ctx, modes, s, q } = mount();
    modes.setMode('walk');
    modes.openCam(true);
    modes.lock(true);
    expect([s.mode, s.camOpen, s.locked]).toEqual(['orbit', false, true]);
    key('keydown', 'Digit3');
    key('keydown', 'KeyP');
    expect(s.mode).toBe('orbit');
    pointer('pointerdown', ctx.canvas, { pointerId: 1, pointerType: 'mouse', clientX: 1, clientY: 1 });
    expect(s.drag).toBeNull();
    modes.setMode('walk');                               // the public setMode too: Orbit only while locked
    modes.setMode('ghost');
    q('modes').querySelector<HTMLButtonElement>('[data-mode=walk]')!.click();
    expect(s.mode).toBe('orbit');
    modes.lock(false);
    expect([s.locked, s.camOpen]).toEqual([false, false]);
    key('keydown', 'Digit3');
    expect(s.mode).toBe('ghost');
  });

  it('dispose takes every listener away (keys do nothing after it)', () => {
    const { ctx, s } = mount();
    const add = vi.spyOn(window, 'addEventListener');
    const remove = vi.spyOn(window, 'removeEventListener');
    const b = mount();
    const added = add.mock.calls.length;
    expect(added).toBeGreaterThan(0);
    b.ctx.disposer.dispose();
    expect(remove.mock.calls.length).toBeGreaterThanOrEqual(added);
    key('keydown', 'Digit2');
    expect([s.mode, b.s.mode]).toEqual(['walk', 'orbit']);
    expect(ctx.ui.root.isConnected).toBe(true);
    expect(b.ctx.ui.root.isConnected).toBe(false);
  });
});

describe('ModesApi shape', { timeout: 60_000 }, () => {
  it('registers no frame hook of its own (viewer.ts registers tick) and no page-wide error listener', () => {
    const ctx = makeTestContext({ model: fixtureModel('bank-v2'), presentation: fixturePresentation('bank-sampeng-v2') });
    mounted.push(ctx);
    const add = vi.spyOn(ctx.loop, 'add');
    const listen = vi.spyOn(window, 'addEventListener');
    ctx.modes = installModes(ctx);
    expect(add).not.toHaveBeenCalled();
    const types = listen.mock.calls.map(c => c[0]);
    expect(types).not.toContain('error');
    expect(types).not.toContain('unhandledrejection');
    expect(new Set(types)).toEqual(new Set(['keydown', 'keyup', 'blur', 'pointerdown', 'pointermove', 'pointerup', 'pointercancel']));
  });

  it('has the contract members', () => {
    const { modes } = mount();
    const api: ModesApi = modes;
    expect(Object.keys(api).sort()).toEqual(['applyAddress', 'changeFloor', 'goToFloor', 'lock', 'mode', 'openCam', 'probe', 'setMode', 'state', 'takePhoto', 'tick'].sort());
    expect(api.mode).toBe('orbit');
    expect(Object.keys(api.probe).sort()).toEqual(['camera', 'clearance', 'crosses', 'foot', 'ground', 'onFloor', 'open', 'visible', 'walk']);
    expect(api.probe.camera().dir).toHaveLength(3);
  });
});
