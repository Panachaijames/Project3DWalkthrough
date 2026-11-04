// Builder B's harness spec (project `harness`; WORK_BREAKDOWN B "Tests alone"): installModes on the shared test context
// with the real WebGL renderer in headless Edge, driven with real input: keys, the mouse, pointer lock, the wheel, the
// double-click, touch through lib/page.ts (CDP Input.dispatchTouchEvent, maxTouchPoints 0), photos and their exact sizes
// (each download saved to testInfo.outputPath()), and ?cam=1 on a locked context. The checks are the ones of
// viewer-modes/test_viewers.mjs (house, fixes, fixes2) on this page (/modes/modes.html); tests/e2e/modes.spec.ts runs them
// on the pages. A second page (/modes/viewer.html) mounts the real createViewer, for what only the assembly shows.
//   WT_WEB_PORT=5722 WT_TMP="$TEMP/wt-b" npx playwright test -c tests/e2e/playwright.config.ts --project=harness packages/viewer/test/harness/modes
// "Never through a wall" is judged on the walked path, leg by leg (a sample every 200 - 250 ms while the key is held):
// the prototype's straight line from the start to the end also cuts the corner of a wall you slid along and walked
// round (seen on the bank, 3 Nov), which is not going through it. A check of what a key does holds it until it has done
// it (holdUntil): below 20 fps the 0.05 s time-step cap makes every move slower per second (B.md B-2, B-3).
import { readFileSync } from 'node:fs';
import { expect, test, type Page, type TestInfo } from '@playwright/test';
import { timedDescribe } from '../../../../../tests/e2e/lib/fps';
import { pageApi, sleep, type KeyCode, type PageApi } from '../../../../../tests/e2e/lib/page';

const D2R = Math.PI / 180;
const lensFov = (mm: number) => 2 * Math.atan(12 / mm) / D2R;
const r2 = (v: number) => Math.round(v * 100) / 100;
type St = { mode: string; floor: string; level: number; x: number; y: number; z: number; yaw: number; pitch: number; touch: boolean; lens: number; camOpen: boolean };
const dist2 = (a: St, b: St) => Math.hypot(a.x - b.x, a.z - b.z);
const pngSize = (file: string) => { const b = readFileSync(file); return [b.readUInt32BE(16), b.readUInt32BE(20)]; };

async function open(page: Page, model = 'bank-v2'): Promise<PageApi> {
  const api = await pageApi(page);
  await page.goto(`/modes/modes.html?model=${model}`);
  await page.waitForFunction(() => window.__modes !== undefined, undefined, { timeout: 90_000 });
  const err = await page.evaluate(() => { const k = window.__modes!; return 'error' in k ? k.error : null; });
  expect(err).toBeNull();
  return api;
}
const st = (page: Page): Promise<St> => page.evaluate(() => {
  const s = window.__viewer!.state;
  return { mode: s.mode, floor: s.floor.key, level: s.floor.level, x: s.pos.x, y: s.pos.y, z: s.pos.z, yaw: s.yaw, pitch: s.pitch, touch: s.touch, lens: s.lens, camOpen: s.camOpen };
});
const probe = <T>(page: Page, fn: 'open' | 'clearance' | 'onFloor' | 'visible' | 'camera', arg?: number): Promise<T> =>
  page.evaluate(([f, a]) => { const p = window.__viewer!.probe as unknown as Record<string, (x?: number) => unknown>; return p[f as string]!(a as number | undefined); }, [fn, arg] as const) as Promise<T>;
const setYaw = (page: Page, deg: number) => page.evaluate(d => { const s = window.__viewer!.state; s.yaw = d * Math.PI / 180; s.pitch = 0; }, deg);
const scan = (page: Page) => page.evaluate(() => [...Array(72)].map((_, i) => window.__viewer!.probe.open(i * 5)));
async function nearestWall(page: Page) { const d = await scan(page); let i = 0; d.forEach((v, j) => { if (v < d[i]!) i = j; }); return { yaw: i * 5, dist: d[i]! }; }
async function faceOpenest(page: Page) { const d = await scan(page); let i = 0; d.forEach((v, j) => { if (v > d[i]!) i = j; }); await setYaw(page, i * 5); return d[i]!; }
/** Hold a key until you stop making headway (< 12 cm/s); returns the path, sampled every 250 ms. */
async function holdUntilStill(p: PageApi, code: 'KeyW', maxMs = 15000): Promise<St[]> {
  await p.keyDown(code);
  let prev = await st(p.page), still = 0;
  const path = [prev];
  const t0 = Date.now();
  while (Date.now() - t0 < maxMs) { await sleep(250); const cur = await st(p.page); path.push(cur); still = dist2(prev, cur) < 0.03 ? still + 1 : 0; if (still >= 2) break; prev = cur; }
  await p.keyUp(code); await sleep(80);
  path.push(await st(p.page));
  return path;
}
/** Hold a key until `done(start, now)` or `ms`; returns the path, sampled every 200 ms. */
async function holdTracked(p: PageApi, code: KeyCode, ms: number, done: (a: St, b: St) => boolean = () => false): Promise<St[]> {
  const path = [await st(p.page)];
  await p.keyDown(code);
  const t0 = Date.now();
  while (Date.now() - t0 < ms) {
    await sleep(Math.max(0, Math.min(200, ms - (Date.now() - t0))));
    const cur = await st(p.page);
    path.push(cur);
    if (done(path[0]!, cur)) break;
  }
  await p.keyUp(code); await sleep(80);
  path.push(await st(p.page));
  return path;
}
/**
 * Hold a key until `done(start, now)` (checked every 100 ms) or `maxMs`; returns [start, end]. The modes cap a frame's
 * time step at 0.05 s, so below 20 fps you go slower per second: a check of WHAT a key does (rises, flies through a
 * wall) holds the key until it has done it, not for a fixed time. Speeds are checked by the unit tests (tick).
 */
async function holdUntil(p: PageApi, code: KeyCode, done: (a: St, b: St) => boolean, maxMs: number): Promise<[St, St]> {
  const a = await st(p.page);
  await p.keyDown(code);
  const t0 = Date.now();
  while (Date.now() - t0 < maxMs) { await sleep(100); if (done(a, await st(p.page))) break; }
  await p.keyUp(code); await sleep(80);
  return [a, await st(p.page)];
}
/** The first leg of the path that crosses a wall (chest height, the floor you are on), or null. */
const crossedLeg = (page: Page, path: St[]) => page.evaluate(pts => {
  const pr = window.__viewer!.probe;
  for (let i = 1; i < pts.length; i++) if (pr.crosses(pts[i - 1]!.x, pts[i - 1]!.z, pts[i]!.x, pts[i]!.z)) return { leg: i, from: pts[i - 1], to: pts[i] };
  return null;
}, path.map(q => ({ x: q.x, z: q.z })));
const visible = (page: Page, wt: string) => page.evaluate(w => { const e = document.querySelector(`[data-wt=${w}]`); return !!e && getComputedStyle(e).display !== 'none' && e.getBoundingClientRect().width > 0; }, wt);
const textOf = (page: Page, wt: string) => page.evaluate(w => document.querySelector(`[data-wt=${w}]`)!.textContent, wt);
const setInput = (page: Page, wt: string, v: string | number, ev = 'input') => page.evaluate(([w, value, type]) => {
  const e = document.querySelector(`[data-wt=${w}]`) as HTMLInputElement; e.value = String(value); e.dispatchEvent(new Event(type as string)); return e.value;
}, [wt, v, ev] as const);
const pressed = (page: Page, sel: string) => page.evaluate(s => document.querySelector(s)!.getAttribute('aria-pressed') === 'true', sel);
const nPhotos = (page: Page) => page.evaluate(() => document.querySelectorAll('[data-wt=photos] img').length);
const photoTitle = (page: Page) => page.evaluate(() => (document.querySelector('[data-wt=photos] img') as HTMLImageElement | null)?.title ?? '');
async function waitPhoto(page: Page, n0: number) { for (let i = 0; i < 60 && (await nPhotos(page)) === n0; i++) await sleep(200); }
/** Runs `act`, waits for the photo's download and saves it under the test's output folder; returns its name and size. */
async function download(page: Page, testInfo: TestInfo, act: () => Promise<void>) {
  const [d] = await Promise.all([page.waitForEvent('download', { timeout: 30_000 }), act()]);
  const name = d.suggestedFilename(), file = testInfo.outputPath(name);
  await d.saveAs(file);
  return { name, size: pngSize(file) };
}


test('the modes row, the HUD and the hint on the page (texts, selectors, flags)', async ({ page }) => {
  const p = await open(page);
  expect(await st(page)).toMatchObject({ mode: 'orbit', floor: 'L1' });
  await expect(page.locator('[data-slot=modes] .vm-label')).toHaveText('Look around');
  await expect(page.locator('[data-wt=modes] [data-mode]')).toHaveText(['Orbit', 'Walk', 'Ghost']);
  await expect(page.locator('[data-wt=hint]')).toHaveText('Drag to orbit · right-drag to pan · scroll to zoom · double-click a floor to walk there · 1 / 2 / 3: Orbit / Walk / Ghost · P: photo');
  expect(await visible(page, 'hud')).toBe(false);
  await p.clickEl('[data-wt=modes] [data-mode=walk]');
  expect((await st(page)).mode).toBe('walk');
  expect(await visible(page, 'hud')).toBe(true);
  expect(await textOf(page, 'hud-text')).toBe('Walk · Level 1 · drag or click to look · W A S D to move, Shift to run · PgUp / PgDn: other floor · wheel: lens 24 mm · Esc');
  await expect(page.locator('[data-wt=hint]')).toHaveText('Click to capture the mouse (Esc frees it, Esc again returns to Orbit) · 1 / 2 / 3: Orbit / Walk / Ghost · P: photo');
  expect(await page.evaluate(() => document.querySelector('[data-wt=root]')!.hasAttribute('data-fp'))).toBe(true);
  expect(await pressed(page, '[data-wt=modes] [data-mode=walk]')).toBe(true);
  const hud = await page.evaluate(() => { const r = document.querySelector('[data-wt=hud]')!.getBoundingClientRect(); return { top: r.top, centre: r.left + r.width / 2 }; });
  expect(hud.top).toBeCloseTo(12, 0);
  expect(Math.abs(hud.centre - 700)).toBeLessThan(2);
  await p.clickEl('[data-wt=exit]');
  expect((await st(page)).mode).toBe('orbit');
  expect(p.logs.filter(l => l.startsWith('[exception]'))).toEqual([]);
});

timedDescribe('Walk (bank v2)', () => {
  test('2 -> Walk at eye height with room; W walks; stops at a wall; slides; still on the floor; PgUp / PgDn', async ({ page }) => {
    const p = await open(page);
    await p.press('Digit2');
    let s = await st(page);
    expect([s.mode, s.floor]).toEqual(['walk', 'L1']);
    expect(Math.abs(s.y - (s.level + 1.6))).toBeLessThan(0.01);
    expect(await probe<number>(page, 'clearance')).toBeGreaterThanOrEqual(0.5);
    expect(await probe<boolean>(page, 'onFloor')).toBe(true);
    expect(await pressed(page, '[data-wt=floors] [data-floor=L1]')).toBe(true);
    expect(await probe<string[]>(page, 'visible')).toEqual(['L1', 'L2']);
    await faceOpenest(page);
    let [a, b] = await holdUntil(p, 'KeyW', (s0, s1) => dist2(s0, s1) > 0.6, 4000);
    expect(dist2(a, b), 'W walks forward').toBeGreaterThan(0.4);
    expect(Math.abs(b.y - a.y)).toBeLessThan(1e-6);
    const w = await nearestWall(page);
    await setYaw(page, w.yaw);
    const walked = await holdUntilStill(p, 'KeyW');
    const near = await probe<number>(page, 'clearance');
    expect(await crossedLeg(page, walked), 'never through a wall on the way').toBeNull();
    expect(near, `stops ${r2(near)} m from the wall`).toBeGreaterThan(0.2);
    expect(near).toBeLessThan(0.6);
    const p0 = await st(page);
    const tryDir = (off: number) => page.evaluate(([yaw, x, y, z]) => { const v = window.__viewer!; const r = v.probe.walk(yaw!, 1.0); v.state.pos.set(x!, y!, z!); return r; }, [w.yaw + off, p0.x, p0.y, p0.z]);
    const plus = await tryDir(40), minus = await tryDir(-40);
    await setYaw(page, w.yaw + (plus >= minus ? 40 : -40));
    const slid = await holdTracked(p, 'KeyW', 5000, (s0, s1) => dist2(s0, s1) > 0.4);
    a = slid[0]!; b = slid[slid.length - 1]!;
    expect(await crossedLeg(page, slid), 'sliding: never through a wall').toBeNull();
    expect(dist2(a, b) > 0.2 || Math.max(plus, minus) < 0.3, `slid ${r2(dist2(a, b))} m`).toBe(true);
    expect(await probe<boolean>(page, 'onFloor')).toBe(true);
    expect(await probe<number>(page, 'clearance')).toBeGreaterThan(0.15);
    await p.press('PageUp'); s = await st(page);
    expect([s.floor, r2(s.y)]).toEqual(['L2', r2(3.7 + 1.6)]);
    expect(await probe<boolean>(page, 'onFloor')).toBe(true);
    expect(await pressed(page, '[data-wt=floors] [data-floor=L2]')).toBe(true);
    await p.press('PageUp'); expect((await st(page)).floor).toBe('L2');
    await p.press('PageDown'); expect((await st(page)).floor).toBe('L1');
    await p.clickEl('[data-wt=floors] [data-floor=L2]'); expect((await st(page)).floor).toBe('L2');
    await p.clickEl('[data-wt=floors] [data-floor=all]'); expect((await st(page)).floor).toBe('L1');
  });

  test('keys still work after clicking a tick; Space does not tick it', async ({ page }) => {
    const p = await open(page);
    await p.press('Digit2');
    await p.clickEl('[data-wt=toggle][data-toggle=glass]');
    expect(await page.evaluate(() => document.activeElement?.getAttribute('data-toggle'))).toBe('glass');
    await faceOpenest(page);
    const [a, b] = await holdUntil(p, 'KeyW', (s0, s1) => dist2(s0, s1) > 0.3, 3000);
    await p.clickEl('[data-wt=toggle][data-toggle=glass]');
    expect(dist2(a, b), 'moved after the click').toBeGreaterThan(0.1);
    await p.keyDown('Space'); await sleep(100); await p.keyUp('Space'); await sleep(100);
    expect(await page.evaluate(() => (document.querySelector('[data-wt=toggle][data-toggle=glass]') as HTMLInputElement).checked)).toBe(true);
  });

  test('3 -> Ghost through walls, Space rises, C sinks; a floor button hides the other floor without moving you; Esc back to Orbit where you left it', async ({ page }) => {
    const p = await open(page);
    const cam0 = await probe<{ x: number; y: number; z: number }>(page, 'camera');
    await p.press('Digit2');
    await p.press('Digit3');
    let s = await st(page);
    expect(s.mode).toBe('ghost');
    expect(await textOf(page, 'hud-text')).toBe('Ghost · through walls · W A S D · Space up, C down · Shift fast · wheel: speed 6.0 m/s · Esc');
    const w = await nearestWall(page);
    await setYaw(page, w.yaw);
    let [a, b] = await holdUntil(p, 'KeyW', (s0, s1) => dist2(s0, s1) > w.dist + 0.5, 8000);
    const crossed = await page.evaluate(([x0, z0, x1, z1]) => window.__viewer!.probe.crosses(x0!, z0!, x1!, z1!), [a.x, a.z, b.x, b.z]);
    expect(crossed && dist2(a, b) > w.dist, `flew ${r2(dist2(a, b))} m, the wall was ${r2(w.dist)} m away`).toBe(true);
    [a, b] = await holdUntil(p, 'Space', (s0, s1) => s1.y - s0.y > 0.6, 5000);
    expect(b.y - a.y, 'Space rises').toBeGreaterThan(0.5);
    [a, b] = await holdUntil(p, 'KeyC', (s0, s1) => s0.y - s1.y > 0.6, 5000);
    expect(a.y - b.y, 'C sinks').toBeGreaterThan(0.5);
    a = await st(page); await p.clickEl('[data-wt=floors] [data-floor=L1]'); b = await st(page);
    expect(dist2(a, b)).toBeLessThan(1e-6);
    expect(a.y).toBe(b.y);
    expect(await probe<string[]>(page, 'visible')).toEqual(['L1']);
    await p.clickEl('[data-wt=floors] [data-floor=all]');
    s = await st(page);
    await p.press('Escape'); await sleep(300);
    const c = await probe<{ x: number; y: number; z: number }>(page, 'camera');
    expect((await st(page)).mode).toBe('orbit');
    expect(Math.hypot(c.x - cam0.x, c.y - cam0.y, c.z - cam0.z)).toBeLessThan(0.5);
    expect(await probe<string[]>(page, 'visible')).toEqual(['L1', 'L2']);
    expect(s.mode).toBe('ghost');
  });

  test('Ghost then Walk from outside lands you on a floor, able to walk', async ({ page }) => {
    const p = await open(page);
    await p.press('Digit3'); await p.press('Digit2');
    const s = await st(page);
    const onf = await probe<boolean>(page, 'onFloor');
    await faceOpenest(page);
    const [a, b] = await holdUntil(p, 'KeyW', (s0, s1) => dist2(s0, s1) > 0.4, 3000);
    expect(s.mode === 'walk' && onf && dist2(a, b) > 0.2, JSON.stringify({ floor: s.floor, onf, moved: r2(dist2(a, b)) })).toBe(true);
  });

  test('touch on a desktop: a tap shows the stick, the stick moves you, a second finger looks, letting go stops, Upstairs / Downstairs, the mouse hides them', async ({ page }) => {
    const p = await open(page);
    await p.press('Digit2');
    await p.tap(1000, 600);
    expect(await page.evaluate(() => navigator.maxTouchPoints)).toBe(0);
    expect((await visible(page, 'stick')) && (await visible(page, 'updown')) && (await st(page)).touch, 'a touch shows the stick and Up / Down').toBe(true);
    expect([await textOf(page, 'up'), await textOf(page, 'down')]).toEqual(['Upstairs', 'Downstairs']);
    expect(await page.evaluate(() => document.querySelector('[data-wt=root]')!.hasAttribute('data-touchui'))).toBe(true);
    await faceOpenest(page);
    const [sx, sy] = (await p.center('[data-wt=stick]'))!;
    const a = await st(page);
    await p.touch('touchStart', [[sx, sy, 1]]); await p.touch('touchMove', [[sx, sy - 55, 1]]);
    for (let t0 = Date.now(); Date.now() - t0 < 4000 && dist2(a, await st(page)) <= 0.5;) await sleep(100);
    const b = await st(page);
    await p.touch('touchStart', [[sx, sy - 55, 1], [900, 400, 2]]); await sleep(50);
    await p.touch('touchMove', [[sx, sy - 55, 1], [960, 400, 2]]); await sleep(150);
    await p.touch('touchMove', [[sx, sy - 55, 1], [1010, 400, 2]]); await sleep(300);
    const c = await st(page);
    await p.touch('touchEnd', []); await sleep(200);
    expect(dist2(a, b), 'the stick moves you forward').toBeGreaterThan(0.3);
    expect(Math.abs(c.yaw - b.yaw), 'a second finger looks around').toBeGreaterThan(0.1);
    expect(dist2(b, c), 'while the stick is held').toBeGreaterThan(0.02);
    const s0 = await st(page); await sleep(400); const s1 = await st(page);
    expect(dist2(s0, s1), 'letting go stops you').toBeLessThan(1e-6);
    await p.tapEl('[data-wt=up]'); expect((await st(page)).floor).toBe('L2');
    await p.tapEl('[data-wt=down]'); expect((await st(page)).floor).toBe('L1');
    await p.click(1000, 600);
    expect(!(await visible(page, 'stick')) && !(await st(page)).touch, 'using the mouse again hides the touch controls').toBe(true);
    await p.press('Digit3');
    await p.tap(1000, 600);
    expect([await textOf(page, 'up'), await textOf(page, 'down')]).toEqual(['Up', 'Down']);
    const [ux, uy] = (await p.center('[data-wt=up]'))!;
    const g0 = await st(page);
    await p.touch('touchStart', [[ux, uy, 3]]);
    for (let t0 = Date.now(); Date.now() - t0 < 4000 && (await st(page)).y - g0.y <= 0.6;) await sleep(100);
    await p.touch('touchEnd', []); await sleep(100);
    const g1 = await st(page);
    expect(g1.y - g0.y, 'holding Up rises').toBeGreaterThan(0.5);
  });
});

test.describe('pointer lock, the wheel, the double-click', () => {
  test('a slow look-drag does not capture the mouse; a click does', async ({ page }) => {
    const p = await open(page);
    await p.press('Digit2');
    await page.evaluate(() => { (window as unknown as { __locks: number }).__locks = 0; document.querySelector('canvas')!.requestPointerLock = (() => { (window as unknown as { __locks: number }).__locks++; }) as unknown as HTMLCanvasElement['requestPointerLock']; });
    const yaw0 = (await st(page)).yaw;
    await page.mouse.move(900, 500); await page.mouse.down();
    for (let i = 1; i <= 30; i++) await page.mouse.move(900 + i, 500);
    await page.mouse.up(); await sleep(200);
    const afterDrag = await page.evaluate(() => (window as unknown as { __locks: number }).__locks);
    const yaw1 = (await st(page)).yaw;
    await p.click(900, 520);
    const afterClick = await page.evaluate(() => (window as unknown as { __locks: number }).__locks);
    expect({ afterDrag, afterClick }).toEqual({ afterDrag: 0, afterClick: 1 });
    expect(yaw1 - yaw0).toBeCloseTo(-30 * 0.0025, 6);       // the drag turned the view the way the mouse went
  });

  test('a click captures the mouse in Walk; the mouse then looks around; leaving the lock forgets held keys', async ({ page }) => {
    const p = await open(page);
    await p.press('Digit2');
    await p.click(900, 520);
    await sleep(300);
    const locked = await page.evaluate(() => document.pointerLockElement === document.querySelector('canvas'));
    test.skip(!locked, 'headless Edge gave no pointer lock here (the stubbed check above covers the click rule)');
    const yaw0 = (await st(page)).yaw;
    await page.mouse.move(950, 520); await page.mouse.move(1000, 520); await sleep(200);
    expect((await st(page)).yaw).toBeLessThan(yaw0);
    await page.evaluate(() => document.exitPointerLock());
    await sleep(300);
    expect(await page.evaluate(() => document.pointerLockElement)).toBeNull();
    expect((await st(page)).mode).toBe('walk');
  });

  test('wheel follows the scroll distance: 10 small touchpad steps 0.8 mm, one mouse notch 2 mm; Ghost speed', async ({ page }) => {
    const p = await open(page);
    await p.press('Digit2');
    await page.mouse.move(900, 500);
    const lens0 = (await st(page)).lens;
    for (let i = 0; i < 10; i++) await page.mouse.wheel(0, -4);
    await sleep(200);
    const lens1 = (await st(page)).lens;
    await page.mouse.wheel(0, -100);
    await sleep(200);
    const lens2 = (await st(page)).lens;
    expect(Math.abs(lens1 - lens0 - 0.8), JSON.stringify({ lens0, lens1, lens2 })).toBeLessThan(0.05);
    expect(Math.abs(lens2 - lens1 - 2)).toBeLessThan(0.05);
    expect(await textOf(page, 'hud-text')).toContain(`wheel: lens ${Math.round(lens2)} mm`);
    await p.press('Digit3');
    await page.mouse.wheel(0, -100); await sleep(200);
    expect(await page.evaluate(() => window.__viewer!.state.ghostSpeed)).toBeCloseTo(7.2, 6);
    expect(await textOf(page, 'hud-text')).toContain('wheel: speed 7.2 m/s');
  });

  test('double-click in Orbit -> Walk at that spot', async ({ page }) => {
    const p = await open(page);
    await sleep(400);
    await p.dblclick(700, 440); await sleep(400);
    const s = await st(page);
    expect(s.mode, 'double-click walks').toBe('walk');
    expect(await probe<boolean>(page, 'onFloor')).toBe(true);
  });
});

test.describe('the Camera tool and photos', () => {
  test('3:2 and 1920 x 1280 px; lens 50; P in Orbit downloads the photo; tilt; straight verticals; eye height; Walk photo; 4K; 9:16; whole screen; panel closed', async ({ page }, testInfo) => {
    const p = await open(page);
    await p.clickEl('[data-wt=camera-btn]');
    expect(await visible(page, 'camera-panel')).toBe(true);
    expect(await pressed(page, '[data-wt=camera-btn]')).toBe(true);
    expect(await visible(page, 'frame')).toBe(true);
    expect(await textOf(page, 'px')).toBe('1920 × 1280 px');
    await setInput(page, 'lens', 50);
    const c50 = await probe<{ fov: number }>(page, 'camera');
    expect(Math.abs(c50.fov - lensFov(50))).toBeLessThan(0.01);
    expect(await textOf(page, 'lens-value')).toMatch(/^50 mm · \d+° wide$/);
    let shot = await download(page, testInfo, () => p.press('KeyP'));
    expect(shot.name).toMatch(/^BangkokBank-Sampeng_Orbit_overview_50mm_\d{4}-\d\d-\d\d_\d\d-\d\d-\d\d\.png$/);
    expect(shot.size).toEqual([1920, 1280]);
    expect(await nPhotos(page)).toBe(1);
    expect(await photoTitle(page)).toBe(`${shot.name} (1920 x 1280) - click to save again`);

    await p.press('Digit2'); await faceOpenest(page);
    await setInput(page, 'tilt', 15);
    const ct = await probe<{ rx: number; offsetY: number | null }>(page, 'camera');
    expect(Math.abs(ct.rx - 15 * D2R)).toBeLessThan(0.01);
    expect(ct.offsetY).toBeNull();
    await p.clickEl('[data-wt=straight]');
    const cs = await probe<{ rx: number; offsetY: number | null }>(page, 'camera');
    expect(Math.abs(cs.rx)).toBeLessThan(1e-9);
    expect(cs.offsetY).not.toBeNull();
    expect(cs.offsetY!).toBeLessThan(0);
    await setInput(page, 'eye', 1.2);
    let s = await st(page);
    expect(Math.abs(s.y - (s.level + 1.2))).toBeLessThan(0.01);
    await setInput(page, 'eye', 1.6);
    shot = await download(page, testInfo, () => p.clickEl('[data-wt=shot]'));
    expect(shot.name).toMatch(/^BangkokBank-Sampeng_Walk_Level-1_24mm_/);
    expect(shot.size).toEqual([1920, 1280]);

    await setInput(page, 'size-select', 3840, 'change');
    expect(await textOf(page, 'px')).toBe('3840 × 2560 px');
    shot = await download(page, testInfo, () => p.press('KeyP'));
    expect(shot.size).toEqual([3840, 2560]);
    await setInput(page, 'frame-select', '9:16', 'change');
    expect(await textOf(page, 'px')).toBe('2160 × 3840 px');
    shot = await download(page, testInfo, () => p.press('KeyP'));
    expect(shot.size).toEqual([2160, 3840]);
    await setInput(page, 'frame-select', 'screen', 'change'); await setInput(page, 'size-select', 1920, 'change');
    shot = await download(page, testInfo, () => p.press('KeyP'));
    const [vw, vh] = await page.evaluate(() => [innerWidth, innerHeight]);
    expect(shot.size[0]).toBe(1920);
    expect(Math.abs(shot.size[1]! - Math.round(1920 * vh! / vw!))).toBeLessThanOrEqual(1);
    const cam = await probe<{ fov: number; offsetY: number | null }>(page, 'camera');
    expect(cam.offsetY, 'straight verticals still shift the view').not.toBeNull();
    expect(Math.abs(cam.fov - lensFov(24)), 'the view is back to normal after photos').toBeLessThan(0.01);
    await p.clickEl('[data-wt=straight]'); await setInput(page, 'frame-select', '3:2', 'change');
    await p.clickEl('[data-wt=camera-close]');
    expect(!(await visible(page, 'camera-panel')) && !(await visible(page, 'frame'))).toBe(true);
    shot = await download(page, testInfo, () => p.press('KeyP'));
    expect(shot.size[0]).toBe(1920);
    expect(Math.abs(shot.size[1]! - Math.round(1920 * vh! / vw!))).toBeLessThanOrEqual(1);
    s = await st(page);
    expect(s.camOpen).toBe(false);
    const errors = await page.evaluate(() => { const k = window.__modes!; return 'errors' in k ? k.errors : []; });
    expect(errors).toEqual([]);
  });

  test('holding P takes one photo; a focused Frame list hands keys back; the frame fits between the panels below the top bar; Exit stays clickable; the flash in Orbit', async ({ page }) => {
    const p = await open(page);
    let n0 = await nPhotos(page);
    await p.keyDown('KeyP'); await p.keyDown('KeyP'); await p.keyDown('KeyP'); await p.keyDown('KeyP');
    await p.keyUp('KeyP');
    await sleep(3000);
    expect((await nPhotos(page)) - n0, 'holding P').toBe(1);

    await p.press('Digit2');
    await p.clickEl('[data-wt=camera-btn]');
    await page.evaluate(() => (document.querySelector('[data-wt=frame-select]') as HTMLSelectElement).focus());
    const f0 = await page.evaluate(() => (document.querySelector('[data-wt=frame-select]') as HTMLSelectElement).value);
    n0 = await nPhotos(page);
    await p.press('KeyP'); await waitPhoto(page, n0);
    await p.press('Digit4');
    expect(await page.evaluate(() => (document.querySelector('[data-wt=frame-select]') as HTMLSelectElement).value)).toBe(f0);
    expect(await nPhotos(page)).toBe(n0 + 1);

    const g = await page.evaluate(() => {
      const r = (w: string) => document.querySelector(`[data-wt=${w}]`)!.getBoundingClientRect();
      const f = r('frame'), c = r('camera-panel'), pn = r('panel'), x = r('exit'), hud = r('hud');
      const hit = document.elementFromPoint(x.left + x.width / 2, x.top + x.height / 2);
      return { frame: [f.left, f.top, f.right, f.bottom].map(Math.round), camLeft: Math.round(c.left), camTop: Math.round(c.top), panelRight: Math.round(pn.right), panelShown: pn.width > 0,
        hudBottom: Math.round(hud.bottom), exitClickable: !!hit && hit.getAttribute('data-wt') === 'exit' };
    });
    expect(g.frame[0]! >= (g.panelShown ? g.panelRight : 0) && g.frame[2]! <= g.camLeft && g.frame[1]! >= g.hudBottom, JSON.stringify(g)).toBe(true);
    expect(g.camTop, 'the Camera panel starts below the top bar in Walk').toBe(58);
    expect(g.exitClickable, JSON.stringify(g)).toBe(true);
    await p.clickEl('[data-wt=camera-close]');

    await p.press('Digit1');
    await p.keyDown('KeyP');
    const anims = await page.evaluate(() => document.querySelector('[data-wt=flash]')!.getAnimations().length);
    await p.keyUp('KeyP'); await sleep(1500);
    expect(anims, 'the shutter flash shows in Orbit too').toBeGreaterThanOrEqual(1);
  });

  test('Ghost 1 m above the upper floor names the photo after it; Ghost above the hidden upper floor names the floor showing', async ({ page }) => {
    const p = await open(page);
    await p.press('Digit3');
    await page.evaluate(() => { window.__viewer!.state.pos.y = 3.7 + 1.0; });
    let n0 = await nPhotos(page);
    await p.press('KeyP'); await waitPhoto(page, n0);
    expect(await photoTitle(page)).toMatch(/_Ghost_Level-2_/);
    await p.press('Digit1');
    await p.clickEl('[data-wt=floors] [data-floor=L1]');
    await p.press('Digit3');
    await page.evaluate(() => { window.__viewer!.state.pos.y = 3.7 + 2.5; });
    n0 = await nPhotos(page);
    await p.press('KeyP'); await waitPhoto(page, n0);
    expect(await photoTitle(page)).toMatch(/_Ghost_Level-1_/);
  });

  test('cam=1 with a locked context: the Camera panel opens when the lock ends, not before', async ({ page }) => {
    await open(page);
    const r = await page.evaluate(() => {
      const k = window.__modes!;
      if ('error' in k) return null;
      k.modes.lock(true);
      k.modes.applyAddress({ cam: true });
      const shownDuring = getComputedStyle(document.querySelector('[data-wt=camera-panel]')!).display !== 'none';
      const wanted = k.modes.state.camWanted;
      k.modes.lock(false);
      return { shownDuring, wanted, shownAfter: getComputedStyle(document.querySelector('[data-wt=camera-panel]')!).display !== 'none' };
    });
    expect(r).toEqual({ shownDuring: false, wanted: true, shownAfter: true });
  });
});

// ------------------------------------------------------------------------------------------------------------------
// Inside the real viewer (/modes/viewer.html: createViewer with A's core, C's root, panel and furniture, D's replay, as
// they are in the package now), for what only the assembly shows. The checks above stay on the test context.
async function openViewer(page: Page, project = 'bank-v2', query = '&build=0&nodownload=1'): Promise<PageApi> {
  const api = await pageApi(page);
  await page.goto(`/modes/viewer.html?project=${project}${query}`);
  await page.waitForFunction(() => window.__modesViewer !== undefined && window.__modesViewer.status !== 'loading', undefined, { timeout: 90_000 });
  expect(await page.evaluate(() => window.__modesViewer!.error ?? null)).toBeNull();
  api.clearLogs();
  return api;
}
const modeChanges = (page: Page) => page.evaluate(() => window.__modesViewer!.events.filter(e => e.type === 'modechange').map(e => e.payload as { mode: string; floor: string }));
const flagsOf = (page: Page) => page.evaluate(() => ['fp', 'camopen', 'crowded', 'touchui', 'replay'].filter(f => document.querySelector('[data-wt=root]')!.hasAttribute(`data-${f}`)));

test.describe('inside createViewer (the real core, panel, root CSS and replay)', () => {
  test('the modes row in the panel after the floors row; the HUD, the hint, the root flags; the floor buttons follow; one modechange per change', async ({ page }) => {
    const p = await openViewer(page);
    const order = await page.evaluate(() => [...document.querySelectorAll('[data-wt=panel] > [data-slot]')].map(e => e.getAttribute('data-slot')));
    expect(order.slice(0, 5)).toEqual(['title', 'intro', 'floors', 'modes', 'shows']);
    await expect(page.locator('[data-wt=panel] [data-slot=modes] .vm-label')).toHaveText('Look around');
    await expect(page.locator('[data-wt=panel] [data-wt=modes] [data-mode]')).toHaveText(['Orbit', 'Walk', 'Ghost']);
    await expect(page.locator('[data-wt=hint]')).toHaveText('Drag to orbit · right-drag to pan · scroll to zoom · double-click a floor to walk there · 1 / 2 / 3: Orbit / Walk / Ghost · P: photo');
    expect(await flagsOf(page)).toEqual([]);
    await page.evaluate(() => { window.__modesViewer!.events.length = 0; });
    await p.press('Digit2');
    expect(await st(page)).toMatchObject({ mode: 'walk', floor: 'L1' });
    expect(await textOf(page, 'hud-text')).toBe('Walk · Level 1 · drag or click to look · W A S D to move, Shift to run · PgUp / PgDn: other floor · wheel: lens 24 mm · Esc');
    await expect(page.locator('[data-wt=hint]')).toHaveText('Click to capture the mouse (Esc frees it, Esc again returns to Orbit) · 1 / 2 / 3: Orbit / Walk / Ghost · P: photo');
    expect(await flagsOf(page)).toEqual(['fp']);
    expect(await pressed(page, '[data-wt=floors] [data-floor=L1]'), 'the floor buttons show the walked floor').toBe(true);
    expect(await pressed(page, '[data-wt=modes] [data-mode=walk]')).toBe(true);
    await page.mouse.move(900, 500); await page.mouse.wheel(0, -100); await sleep(200);   // a lens change: bus `mode` again, no modechange
    expect(await textOf(page, 'hud-text')).toContain('wheel: lens 26 mm');
    await p.press('PageUp');
    expect((await st(page)).floor).toBe('L2');
    expect(await pressed(page, '[data-wt=floors] [data-floor=L2]')).toBe(true);
    await p.press('Escape');
    expect((await st(page)).mode).toBe('orbit');
    expect(await pressed(page, '[data-wt=floors] [data-floor=all]'), 'Orbit: the floor mode again').toBe(true);
    expect(await modeChanges(page)).toEqual([{ mode: 'walk', floor: 'L1' }, { mode: 'walk', floor: 'L2' }, { mode: 'orbit', floor: 'L2' }]);
    expect(p.logs.filter(l => l.startsWith('[exception]'))).toEqual([]);
  });

  test("the overlays under the root's `all: revert`: the HUD, the Camera panel 300 px wide below the top bar, the frame between the panels, Exit clickable", async ({ page }) => {
    const p = await openViewer(page);
    await p.press('Digit2');
    await p.clickEl('[data-wt=camera-btn]');
    expect(await visible(page, 'camera-panel')).toBe(true);
    expect(await flagsOf(page)).toEqual(['fp', 'camopen']);
    expect(await visible(page, 'cross'), 'no cross while framing').toBe(false);
    const g = await page.evaluate(() => {
      const q = (w: string) => document.querySelector(`[data-wt=${w}]`) as HTMLElement;
      const r = (w: string) => q(w).getBoundingClientRect();
      const hud = getComputedStyle(q('hud')), cam = getComputedStyle(q('camera-panel'));
      const f = r('frame'), c = r('camera-panel'), pn = r('panel'), x = r('exit'), h = r('hud');
      const hit = document.elementFromPoint(x.left + x.width / 2, x.top + x.height / 2);
      return {
        hud: { position: hud.position, display: hud.display, background: hud.backgroundColor, radius: hud.borderTopLeftRadius, top: Math.round(h.top), centre: Math.round(h.left + h.width / 2) },
        cam: { position: cam.position, width: q('camera-panel').offsetWidth, top: Math.round(c.top), right: Math.round(window.innerWidth - c.right), zIndex: cam.zIndex },
        frame: [f.left, f.top, f.right, f.bottom].map(Math.round), camLeft: Math.round(c.left), panelRight: Math.round(pn.right), panelShown: pn.width > 0,
        hudBottom: Math.round(h.bottom), exitClickable: !!hit && hit.getAttribute('data-wt') === 'exit',
        lensLabel: getComputedStyle(q('camera-panel').querySelector('.vm-f > div:first-child')!).display,
      };
    });
    expect(g.hud).toEqual({ position: 'absolute', display: 'flex', background: 'rgba(29, 35, 41, 0.92)', radius: '999px', top: 12, centre: 700 });
    expect(g.cam).toEqual({ position: 'absolute', width: 300, top: 58, right: 12, zIndex: '8' });
    expect(g.lensLabel).toBe('flex');
    expect(g.frame[0]! >= (g.panelShown ? g.panelRight : 0) && g.frame[2]! <= g.camLeft && g.frame[1]! >= g.hudBottom, JSON.stringify(g)).toBe(true);
    expect(g.exitClickable, JSON.stringify(g)).toBe(true);
    expect(await textOf(page, 'px')).toBe('1920 × 1280 px');
    const n0 = await nPhotos(page);
    await p.press('KeyP'); await waitPhoto(page, n0);
    expect(await photoTitle(page)).toMatch(/^BangkokBank-Sampeng_Walk_Level-1_24mm_\d{4}-\d\d-\d\d_\d\d-\d\d-\d\d\.png \(1920 x 1280\) - click to save again$/);
    await p.clickEl('[data-wt=exit]');
    expect((await st(page)).mode).toBe('orbit');
    expect(await flagsOf(page)).toEqual(['camopen']);
    expect(p.logs.filter(l => l.startsWith('[exception]'))).toEqual([]);
  });

  test('P in Orbit downloads the photo through the default download (an <a download> in the root), 1920 x 1280; the photo event', async ({ page }, testInfo) => {
    const p = await openViewer(page, 'bank-v2', '&build=0');
    await p.clickEl('[data-wt=camera-btn]');
    const shot = await download(page, testInfo, () => p.press('KeyP'));
    expect(shot.name).toMatch(/^BangkokBank-Sampeng_Orbit_overview_33mm_\d{4}-\d\d-\d\d_\d\d-\d\d-\d\d\.png$/);
    expect(shot.size).toEqual([1920, 1280]);
    const photos = await page.evaluate(() => window.__modesViewer!.events.filter(e => e.type === 'photo').map(e => e.payload));
    expect(photos).toEqual([{ name: shot.name, width: 1920, height: 1280 }]);
    expect(await page.evaluate(() => document.querySelectorAll('[data-wt=root] a[download]').length), 'the link is gone again').toBe(0);
  });

  test('?cam=1 behind the Build settings screen: the modes are locked, the Camera panel waits and opens when the screen is skipped', async ({ page }) => {
    const p = await openViewer(page, 'bank-v2', '&cam=1&nodownload=1');
    expect(await page.evaluate(() => window.__build?.phase)).toBe('settings');
    expect(await visible(page, 'replay-card')).toBe(true);
    expect(await visible(page, 'camera-panel'), 'not over the build screen').toBe(false);
    expect(await page.evaluate(() => { const s = window.__viewer!.state; return [s.locked, s.camWanted, s.camOpen]; })).toEqual([true, true, false]);
    await p.press('Digit2');
    expect((await st(page)).mode, 'viewer keys do nothing on the settings screen').toBe('orbit');
    await p.clickEl('[data-wt=replay-skip-settings]');
    await sleep(300);
    expect(await page.evaluate(() => window.__build?.phase)).toBe('done');
    expect(await visible(page, 'camera-panel'), 'the Camera panel opens after the build screen').toBe(true);
    expect(await page.evaluate(() => { const s = window.__viewer!.state; return [s.locked, s.camWanted, s.camOpen]; })).toEqual([false, false, true]);
    await p.press('Digit2');
    expect((await st(page)).mode).toBe('walk');
  });

  test('the address on the real start-up: ?mode=walk&floor=upper walks the house upstairs; ?mode=ghost at x, y, z facing yaw on the hotel', async ({ page }) => {
    await openViewer(page, 'house', '&mode=walk&floor=upper&nodownload=1');
    let s = await st(page);
    expect([s.mode, s.floor, r2(s.y)]).toEqual(['walk', 'upper', r2(4.8 + 1.6)]);
    expect(await probe<boolean>(page, 'onFloor')).toBe(true);
    expect(await probe<string[]>(page, 'visible')).toEqual(['ground', 'upper']);
    expect(await pressed(page, '[data-wt=floors] [data-floor=upper]')).toBe(true);
    await openViewer(page, 'hotel', '&mode=ghost&x=1.5&y=12&z=-2&yaw=90&pitch=-20&nodownload=1');
    s = await st(page);
    expect([s.mode, s.x, s.y, s.z]).toEqual(['ghost', 1.5, 12, -2]);
    expect(s.yaw).toBeCloseTo(Math.PI / 2, 9);
    expect(s.pitch).toBeCloseTo(-20 * D2R, 9);
    const c = await probe<{ x: number; y: number; z: number }>(page, 'camera');
    expect([c.x, c.y, c.z]).toEqual([1.5, 12, -2]);
  });

  test('the suite (one floor): the modes row follows the ticks; Walk; dispose takes the overlays and the keys away', async ({ page }) => {
    const p = await openViewer(page, 'suite');
    const order = await page.evaluate(() => [...document.querySelectorAll('[data-wt=panel] > [data-slot]')].map(e => e.getAttribute('data-slot')));
    expect(order.slice(0, 4)).toEqual(['title', 'intro', 'shows', 'modes']);
    await p.press('Digit2');
    expect(await st(page)).toMatchObject({ mode: 'walk', floor: 'suite' });
    expect(await textOf(page, 'hud-text')).toBe('Walk · Suite (FL-01) · drag or click to look · W A S D to move, Shift to run · PgUp / PgDn: other floor · wheel: lens 24 mm · Esc');
    const after = await page.evaluate(() => {
      window.__modesViewer!.viewer!.dispose();
      window.dispatchEvent(new KeyboardEvent('keydown', { code: 'Digit3', bubbles: true }));
      return {
        left: ['hud', 'cross', 'frame', 'flash', 'stick', 'updown', 'camera-panel', 'modes'].filter(w => document.querySelector(`[data-wt=${w}]`)),
        root: !!document.querySelector('.wtv'), hook: window.__viewer === undefined,
      };
    });
    expect(after).toEqual({ left: [], root: false, hook: true });
    expect(p.logs.filter(l => l.startsWith('[exception]'))).toEqual([]);
  });
});

test.describe('per model', () => {
  test("house: Walk starts with room around you and a view ahead; never closer than the body's edge to the thin partition's end", async ({ page }) => {
    const p = await open(page, 'house');
    await p.press('Digit2');
    const s = await st(page);
    expect([s.mode, s.floor]).toEqual(['walk', 'ground']);
    expect(Math.abs(s.y - (s.level + 1.6))).toBeLessThan(0.01);
    expect(await probe<number>(page, 'clearance')).toBeGreaterThanOrEqual(0.99);
    expect(await probe<number>(page, 'open')).toBeGreaterThanOrEqual(3);
    expect(await probe<boolean>(page, 'onFloor')).toBe(true);
    const gap = await page.evaluate(() => {
      const v = window.__viewer!, st0 = v.state; let worst = Infinity;
      for (const [x, z, yaw] of [[21.80, -5.64, 175], [21.80, -5.64, 170], [21.80, -5.64, 180], [21.75, -5.64, 175], [21.85, -5.64, 175]] as const) {
        st0.pos.set(x, st0.pos.y, z); let min = v.probe.clearance();
        for (let i = 0; i < 60; i++) { v.probe.walk(yaw, 0.05); min = Math.min(min, v.probe.clearance()); }
        worst = Math.min(worst, min);
      }
      return worst;
    });
    expect(gap).toBeGreaterThan(0.25);
  });

  test('suite (one floor): the modes row follows the ticks; Walk on the suite floor', async ({ page }) => {
    const p = await open(page, 'suite');
    const order = await page.evaluate(() => [...document.querySelectorAll('[data-wt=panel] [data-slot]')].map(e => e.getAttribute('data-slot')));
    expect(order.slice(0, 4)).toEqual(['title', 'intro', 'shows', 'modes']);
    expect(await page.evaluate(() => !!document.querySelector('[data-slot=modes] [data-wt=modes]'))).toBe(true);
    await p.press('Digit2');
    const s = await st(page);
    expect([s.mode, s.floor]).toEqual(['walk', 'suite']);
    expect(Math.abs(s.y - 1.6)).toBeLessThan(0.01);
    expect(await probe<number>(page, 'clearance')).toBeGreaterThanOrEqual(0.5);
    expect(await textOf(page, 'hud-text')).toBe('Walk · Suite (FL-01) · drag or click to look · W A S D to move, Shift to run · PgUp / PgDn: other floor · wheel: lens 24 mm · Esc');
  });

  test('hotel: Walk on Floor 1 at 1.60 m; the Floor 2 button takes you to 4.50 m', async ({ page }) => {
    const p = await open(page, 'hotel');
    await p.press('Digit2');
    let s = await st(page);
    expect([s.mode, s.floor, r2(s.y)]).toEqual(['walk', 'F1', 1.6]);
    expect(await probe<number>(page, 'clearance')).toBeGreaterThanOrEqual(0.5);
    await p.clickEl('[data-wt=floors] [data-floor=F2]');
    s = await st(page);
    expect([s.floor, r2(s.y)]).toEqual(['F2', 4.5]);
    expect(await probe<boolean>(page, 'onFloor')).toBe(true);
  });
});
