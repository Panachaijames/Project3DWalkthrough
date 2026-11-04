// Builder B: the modes checks of DESIGN.md 17.4 (ported from viewer-modes/test_viewers.mjs "house", "fixes", "fixes2" and
// the Walk / Ghost / Camera checks of the bank, suite and hotel tests), on the house, the bank (v2), the suite and the
// hotel, through lib/target.ts: E2E_TARGET=prototype runs them on the prototype pages (their selectors and the shim),
// E2E_TARGET=app (the default, at integration) on dist/offline/*.html.
//   WT_WEB_PORT=5722 WT_TMP="$TEMP/wt-b" E2E_TARGET=prototype npx playwright test -c tests/e2e/playwright.config.ts --project=e2e tests/e2e/modes.spec.ts
// The photo checks open the page without nodownload and save each download under testInfo.outputPath() to read its name
// and size, as test_viewers.mjs did. The wall checks run with the furniture boxes hidden (as the bank, suite and hotel
// tests judge the structure; the boxes have their own checks in furniture.spec.ts). Checks that depend on the frame rate
// are inside timedDescribe (one retry; below 12 fps means "re-run alone").
// Made robust where the prototype checks depended on the machine, not on the viewer (3 Nov, docs/contract-issues/B.md):
// * "never through a wall" is judged on the walked path, leg by leg (a sample every 200 - 250 ms while the key is held):
//   the straight line from the start to the end also cuts the corner of a wall you slid along and walked round;
// * a check of what a key does (W walks, the slide, Ghost flies through the wall, Space rises, C sinks, the stick moves
//   you) holds the key until it has done it (at most a few seconds) instead of a fixed time: the modes cap a frame's time
//   step at 0.05 s, so below 20 fps you go slower per second (the speeds are unit-tested);
// * the 40 random slides draw their spots over the floor plates (the house: the prototype test's own box), so every
//   target draws the same spots, and ask for the share the prototype's own walking reaches on that model.
import { readFileSync } from 'node:fs';
import { expect, test, type Page, type TestInfo } from '@playwright/test';
import { timedDescribe } from './lib/fps';
import { pageApi, sleep, type KeyCode, type PageApi } from './lib/page';
import { isApp, isOn, openVersion, sel, type VersionKey } from './lib/target';

interface Project {
  key: VersionKey;
  photoName: string;
  first: string;
  /** The first floor's name as it appears in a photo name. */
  firstName: string;
  firstLevel: number;
  upper?: { key: string; level: number; name: string };
  /** Room around you when Walk starts (the house's own test asked for 0.99 m, the others 0.5 m). */
  room: number;
  /**
   * The share of the 40 random slides along walls that must work on the first floor. The house: 90 %, its prototype
   * test's (37 of 40 here). The others had no such check: the bank reaches 36 - 37 of 40 (90 % asked), the suite 35 and
   * the hotel's floor 1 30 (small rooms: walking at the nearest wall into an inside corner leaves nowhere to slide), with
   * the prototype's own walking on both targets (B.md B-1).
   */
  slides: number;
}
const PROJECTS: Project[] = [
  { key: 'house', photoName: 'Sukhumvit', first: 'ground', firstName: 'Ground-floor', firstLevel: 0.9, upper: { key: 'upper', level: 4.8, name: 'Upper-floor' }, room: 0.99, slides: 0.9 },
  { key: 'bank-v2', photoName: 'BangkokBank-Sampeng', first: 'L1', firstName: 'Level-1', firstLevel: 0, upper: { key: 'L2', level: 3.7, name: 'Level-2' }, room: 0.5, slides: 0.9 },
  { key: 'suite', photoName: 'Presidential', first: 'suite', firstName: 'Suite-FL-01-', firstLevel: 0, room: 0.5, slides: 0.85 },
  { key: 'hotel', photoName: 'Hotel-pictures', first: 'F1', firstName: 'Floor-1', firstLevel: 0, upper: { key: 'F2', level: 2.9, name: 'Floor-2' }, room: 0.5, slides: 0.7 },
];

const D2R = Math.PI / 180;
const lensFov = (mm: number) => 2 * Math.atan(12 / mm) / D2R;
const r2 = (v: number) => Math.round(v * 100) / 100;
const QUIET = `?build=0&nodownload=1${isApp ? '&test=1' : ''}`;
const LOUD = `?build=0${isApp ? '&test=1' : ''}`;
type St = { mode: string; floor: string; level: number; x: number; y: number; z: number; yaw: number; pitch: number; touch: boolean; lens: number };
const dist2 = (a: St, b: St) => Math.hypot(a.x - b.x, a.z - b.z);
const pngSize = (file: string) => { const b = readFileSync(file); return [b.readUInt32BE(16), b.readUInt32BE(20)]; };

/* eslint-disable @typescript-eslint/no-explicit-any */
const st = (page: Page): Promise<St> => page.evaluate(() => {
  const s = (window as any).__viewer.state;
  return { mode: s.mode, floor: s.floor.key, level: s.floor.level, x: s.pos.x, y: s.pos.y, z: s.pos.z, yaw: s.yaw, pitch: s.pitch, touch: s.touch, lens: s.lens };
});
const probe = <T>(page: Page, fn: string, ...args: number[]): Promise<T> => page.evaluate(([f, a]) => (window as any).__viewer.probe[f as string](...(a as number[])), [fn, args] as const) as Promise<T>;
const crosses = (page: Page, a: St, b: St) => probe<boolean>(page, 'crosses', a.x, a.z, b.x, b.z);
const setYaw = (page: Page, deg: number) => page.evaluate(d => { const s = (window as any).__viewer.state; s.yaw = d * Math.PI / 180; s.pitch = 0; }, deg);
const scan = (page: Page): Promise<number[]> => page.evaluate(() => [...Array(72)].map((_, i) => (window as any).__viewer.probe.open(i * 5)));
async function nearestWall(page: Page) { const d = await scan(page); let i = 0; d.forEach((v, j) => { if (v < d[i]!) i = j; }); return { yaw: i * 5, dist: d[i]! }; }
async function faceOpenest(page: Page) { const d = await scan(page); let i = 0; d.forEach((v, j) => { if (v > d[i]!) i = j; }); await setYaw(page, i * 5); return d[i]!; }
/** Hold W until you stop making headway (< 12 cm/s); returns the path, sampled every 250 ms. */
async function holdUntilStill(p: PageApi, maxMs = 15000): Promise<St[]> {
  await p.keyDown('KeyW');
  let prev = await st(p.page), still = 0;
  const path = [prev];
  const t0 = Date.now();
  while (Date.now() - t0 < maxMs) { await sleep(250); const cur = await st(p.page); path.push(cur); still = dist2(prev, cur) < 0.03 ? still + 1 : 0; if (still >= 2) break; prev = cur; }
  await p.keyUp('KeyW'); await sleep(80);
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
/** Hold a key until `done(start, now)` (checked every 100 ms) or `maxMs`; returns [start, end]. */
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
  const pr = (window as any).__viewer.probe;
  for (let i = 1; i < pts.length; i++) if (pr.crosses(pts[i - 1]!.x, pts[i - 1]!.z, pts[i]!.x, pts[i]!.z)) return { leg: i, from: pts[i - 1], to: pts[i] };
  return null;
}, path.map(q => ({ x: q.x, z: q.z })));
const visible = (page: Page, selector: string) => page.evaluate(s => { const e = document.querySelector(s); return !!e && getComputedStyle(e).display !== 'none' && e.getBoundingClientRect().width > 0; }, selector);
const textOf = (page: Page, selector: string) => page.evaluate(s => document.querySelector(s)!.textContent, selector);
const setInput = (page: Page, selector: string, v: string | number, ev = 'input') => page.evaluate(([s, value, type]) => {
  const e = document.querySelector(s as string) as HTMLInputElement; e.value = String(value); e.dispatchEvent(new Event(type as string)); return e.value;
}, [selector, v, ev] as const);
const nPhotos = (page: Page) => page.evaluate(s => document.querySelectorAll(`${s} img`).length, sel.photos);
const photoTitle = (page: Page) => page.evaluate(s => (document.querySelector(`${s} img`) as HTMLImageElement | null)?.title ?? '', sel.photos);
async function waitPhoto(page: Page, n0: number) { for (let i = 0; i < 60 && (await nPhotos(page)) === n0; i++) await sleep(200); }
const setFurniture = (page: Page, on: boolean) => page.evaluate(v => { const F = (window as any).__host.furniture; if (F) F.kinds().forEach((k: { key: string }) => F.setVisible(k.key, v)); }, on);
async function download(page: Page, testInfo: TestInfo, act: () => Promise<void>) {
  const [d] = await Promise.all([page.waitForEvent('download', { timeout: 30_000 }), act()]);
  const name = d.suggestedFilename(), file = testInfo.outputPath(name);
  await d.saveAs(file);
  return { name, size: pngSize(file) };
}
async function open(page: Page, v: VersionKey, query = QUIET): Promise<PageApi> {
  const p = await pageApi(page);
  await openVersion(page, v, query);
  p.clearLogs();
  return p;
}
const exceptions = (p: PageApi) => p.logs.filter(l => l.startsWith('[exception]'));

for (const P of PROJECTS) {
  test.describe(`${P.key}`, () => {
    timedDescribe(`${P.key}: Walk`, () => {
      test('Orbit at start; 2 -> Walk at eye height on the first floor with room around you; W walks; stops at a wall; slides at an angle; 40 random slides; still on the floor', async ({ page }, testInfo) => {
        const p = await open(page, P.key);
        expect((await st(page)).mode).toBe('orbit');
        await setFurniture(page, false);
        await p.press('Digit2');
        let s = await st(page);
        expect([s.mode, s.floor]).toEqual(['walk', P.first]);
        expect(Math.abs(s.y - (P.firstLevel + 1.6)), `eye at ${r2(s.y)} m`).toBeLessThan(0.01);
        const clr = await probe<number>(page, 'clearance'), onf = await probe<boolean>(page, 'onFloor');
        expect(onf).toBe(true);
        expect(Math.min(99, clr), 'room around you').toBeGreaterThanOrEqual(P.room);
        if (P.key === 'house') expect(await probe<number>(page, 'open'), 'a view ahead').toBeGreaterThanOrEqual(3);
        if (P.upper) {
          expect(await isOn(page.locator(sel.floorButton(P.first))), 'the floor button shows the walked floor').toBe(true);
          expect(await isOn(page.locator(sel.floorButton('all')))).toBe(false);
        }
        await faceOpenest(page);
        let [a, b] = await holdUntil(p, 'KeyW', (s0, s1) => dist2(s0, s1) > 0.6, 4000);
        expect(dist2(a, b), 'W walks forward').toBeGreaterThan(0.4);
        expect(Math.abs(b.y - a.y)).toBeLessThan(1e-6);
        const w = await nearestWall(page);
        await setYaw(page, w.yaw);
        const walked = await holdUntilStill(p);
        const near = await probe<number>(page, 'clearance');
        expect(await crossedLeg(page, walked), 'not through the wall on the way').toBeNull();
        expect(near, `stopped ${r2(near)} m from the wall`).toBeGreaterThan(0.2);
        expect(near).toBeLessThan(0.6);
        const p0 = await st(page);
        const tryDir = (off: number) => page.evaluate(([yaw, x, y, z]) => { const v = (window as any).__viewer; const r = v.probe.walk(yaw, 1.0); v.state.pos.set(x, y, z); return r as number; }, [w.yaw + off, p0.x, p0.y, p0.z]);
        const plus = await tryDir(40), minus = await tryDir(-40);
        await setYaw(page, w.yaw + (plus >= minus ? 40 : -40));
        const slid = await holdTracked(p, 'KeyW', 5000, (s0, s1) => dist2(s0, s1) > 0.4);
        a = slid[0]!; b = slid[slid.length - 1]!;
        expect(await crossedLeg(page, slid), 'sliding: not through a wall').toBeNull();
        expect(dist2(a, b) > 0.2 || Math.max(plus, minus) < 0.3, `slid ${r2(dist2(a, b))} m (probe sides ${r2(plus)}, ${r2(minus)})`).toBe(true);
        const many = await page.evaluate(house => {
          const w = window as any, v = w.__viewer, s = v.state, keep = s.pos.clone(), T = w.__walkthrough.THREE;
          // the house: test_viewers.mjs's own box; the others: over the floor plates (the same spots on every target)
          const box = house ? new T.Box3(new T.Vector3(-22, 0, -14), new T.Vector3(22, 0, 14)) : new T.Box3();
          if (!house) for (const m of s.floor.walkables) box.expandByObject(m);
          let seed = 11, n = 0, ok = 0, tries = 0;
          const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
          while (n < 40 && tries++ < 3000) {
            s.pos.x = box.min.x + rnd() * (box.max.x - box.min.x); s.pos.z = box.min.z + rnd() * (box.max.z - box.min.z);
            if (!v.probe.onFloor() || v.probe.clearance() < 0.6) continue;
            const d = [...Array(72)].map((_, i) => v.probe.open(i * 5)); let k = 0; d.forEach((x: number, j: number) => { if (x < d[k]) k = j; });
            if (d[k] > 2.5) continue;
            v.probe.walk(k * 5, d[k] + 1); const q = s.pos.clone();
            const da = v.probe.walk(k * 5 + 40, 1); s.pos.copy(q); const db = v.probe.walk(k * 5 - 40, 1);
            n++; if (Math.max(da, db) > 0.3) ok++;
          }
          s.pos.copy(keep); return [ok, n] as [number, number];
        }, P.key === 'house');
        testInfo.annotations.push({ type: 'slides', description: `${many[0]} of ${many[1]} random slides along walls worked (${P.key}, ${P.first})` });
        expect(many[1], 'random spots along walls').toBeGreaterThanOrEqual(30);
        expect(many[0], `slid at ${many[0]} of ${many[1]} spots (at least ${P.slides * 100} % asked)`).toBeGreaterThanOrEqual(many[1] * P.slides);
        expect(await probe<boolean>(page, 'onFloor')).toBe(true);
        expect(await probe<number>(page, 'clearance'), 'still clear of walls').toBeGreaterThan(0.15);
        s = await st(page);
        expect(s.mode).toBe('walk');
        if (P.upper) {
          await p.press('PageUp'); s = await st(page);
          expect([s.floor, r2(s.y)], 'PgUp: the upper floor at eye height').toEqual([P.upper.key, r2(P.upper.level + 1.6)]);
          expect(await probe<boolean>(page, 'onFloor')).toBe(true);
          expect(await isOn(page.locator(sel.floorButton(P.upper.key)))).toBe(true);
          await p.press('PageUp'); expect((await st(page)).floor).toBe(P.upper.key);
          await p.press('PageDown'); expect((await st(page)).floor).toBe(P.first);
          await p.clickEl(sel.floorButton(P.upper.key)); s = await st(page);
          expect([s.floor, r2(s.y)], 'the upper floor button while walking: up there at eye height').toEqual([P.upper.key, r2(P.upper.level + 1.6)]);
          expect(await probe<boolean>(page, 'onFloor'), 'standing on the slab').toBe(true);
          await p.clickEl(sel.floorButton('all')); expect((await st(page)).floor).toBe(P.first);
        }
        expect(exceptions(p)).toEqual([]);
      });

      test('keys still work after clicking a tick; Space does not tick it', async ({ page }) => {
        const p = await open(page, P.key);
        await setFurniture(page, false);
        await p.press('Digit2');
        await p.clickEl(sel.toggle('glass'));                 // the checkbox now has focus; the glass is hidden
        await faceOpenest(page);
        const [a, b] = await holdUntil(p, 'KeyW', (s0, s1) => dist2(s0, s1) > 0.3, 3000);
        await p.clickEl(sel.toggle('glass'));
        expect(dist2(a, b), 'moved after clicking the tick').toBeGreaterThan(0.1);
        await p.keyDown('Space'); await sleep(100); await p.keyUp('Space'); await sleep(100);
        expect(await page.evaluate(s => (document.querySelector(s) as HTMLInputElement).checked, sel.toggle('glass'))).toBe(true);
      });

      test('3 -> Ghost through walls, Space rises, C sinks; a floor button hides the other floor without moving you; Esc back to Orbit where you left it', async ({ page }) => {
        const p = await open(page, P.key);
        await setFurniture(page, false);
        await p.press('Digit2');
        await p.press('Digit3');
        expect((await st(page)).mode).toBe('ghost');
        const w = await nearestWall(page);
        await setYaw(page, w.yaw);
        let [a, b] = await holdUntil(p, 'KeyW', (s0, s1) => dist2(s0, s1) > w.dist + 0.5, 8000);
        expect((await crosses(page, a, b)) && dist2(a, b) > w.dist, `flew ${r2(dist2(a, b))} m through the wall ${r2(w.dist)} m away`).toBe(true);
        [a, b] = await holdUntil(p, 'Space', (s0, s1) => s1.y - s0.y > 0.6, 5000);
        expect(b.y - a.y, 'Space rises').toBeGreaterThan(0.5);
        [a, b] = await holdUntil(p, 'KeyC', (s0, s1) => s0.y - s1.y > 0.6, 5000);
        expect(a.y - b.y, 'C sinks').toBeGreaterThan(0.5);
        if (P.upper) {
          a = await st(page); await p.clickEl(sel.floorButton(P.first)); b = await st(page);
          expect(dist2(a, b) < 1e-6 && a.y === b.y, 'the floor button does not move you').toBe(true);
          expect(await probe<string[]>(page, 'visible')).toEqual([P.first]);
          await p.clickEl(sel.floorButton('all'));
        }
        const saved = await page.evaluate(() => { const v = (window as any).__viewer.state.saved.pos; return { x: v.x, y: v.y, z: v.z }; });
        await p.press('Escape'); await sleep(300);
        const c0 = await probe<{ x: number; y: number; z: number }>(page, 'camera');
        expect((await st(page)).mode).toBe('orbit');
        expect(Math.hypot(c0.x - saved.x, c0.y - saved.y, c0.z - saved.z), 'back where you left Orbit').toBeLessThan(0.5);
        expect(await probe<string[]>(page, 'visible'), 'every floor visible again').toEqual(P.upper ? [P.first, P.upper.key] : [P.first]);
      });

      test('Ghost then Walk from outside lands you on a floor, able to walk', async ({ page }) => {
        const p = await open(page, P.key);
        await setFurniture(page, false);
        await p.press('Digit3'); await p.press('Digit2');
        const s = await st(page);
        const onf = await probe<boolean>(page, 'onFloor');
        await faceOpenest(page);
        const [a, b] = await holdUntil(p, 'KeyW', (s0, s1) => dist2(s0, s1) > 0.4, 3000);
        expect(s.mode === 'walk' && onf && dist2(a, b) > 0.2, JSON.stringify({ floor: s.floor, onFloor: onf, moved: r2(dist2(a, b)) })).toBe(true);
      });

      test('touch on a desktop: a tap shows the stick, the stick moves you, a second finger looks, letting go stops, Upstairs / Downstairs, the mouse hides them', async ({ page }) => {
        const p = await open(page, P.key);
        await setFurniture(page, false);
        await p.press('Digit2');
        await p.tap(1000, 600);
        expect((await visible(page, sel.stick)) && (await visible(page, sel.updown)) && (await st(page)).touch, 'a touch shows the stick and the floor buttons').toBe(true);
        await faceOpenest(page);
        const [sx, sy] = (await p.center(sel.stick))!;
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
        if (P.upper) {
          await p.tapEl(sel.up); expect((await st(page)).floor, 'Upstairs').toBe(P.upper.key);
          await p.tapEl(sel.down); expect((await st(page)).floor, 'Downstairs').toBe(P.first);
        } else {
          expect(await textOf(page, sel.up)).toBe('Upstairs');
        }
        await p.click(1000, 600);
        expect(!(await visible(page, sel.stick)) && !(await st(page)).touch, 'using the mouse again hides the touch controls').toBe(true);
      });
    });

    test('the Camera panel: 3:2 and 1920 x 1280 px; lens 50; P in Orbit downloads the photo; tilt; straight verticals; eye height; the Walk photo; 4K; 9:16; whole screen; panel closed', async ({ page }, testInfo) => {
      const p = await open(page, P.key, LOUD);
      await p.clickEl(sel.cameraBtn);
      expect(await visible(page, sel.cameraPanel), 'the Camera panel opens').toBe(true);
      expect((await visible(page, sel.frame)) && (await textOf(page, sel.px)) === '1920 × 1280 px', '3:2 frame drawn, HD size shown').toBe(true);
      await setInput(page, sel.lens, 50);
      const c50 = await probe<{ fov: number }>(page, 'camera');
      expect(Math.abs(c50.fov - lensFov(50)), 'lens 50 mm sets the view angle').toBeLessThan(0.01);
      let shot = await download(page, testInfo, () => p.press('KeyP'));
      expect(shot.name).toMatch(new RegExp(`^${P.photoName}_Orbit_overview_50mm_\\d{4}-\\d\\d-\\d\\d_\\d\\d-\\d\\d-\\d\\d\\.png$`));
      expect(shot.size).toEqual([1920, 1280]);
      expect(await nPhotos(page), 'thumbnail added').toBe(1);
      expect(await photoTitle(page)).toBe(`${shot.name} (1920 x 1280) - click to save again`);

      await p.press('Digit2'); await faceOpenest(page);
      await setInput(page, sel.tilt, 15);
      const ct = await probe<{ rx: number; offsetY: number | null }>(page, 'camera');
      expect(Math.abs(ct.rx - 15 * D2R) < 0.01 && ct.offsetY === null, 'the tilt slider tilts the camera').toBe(true);
      await p.clickEl(sel.straight);
      const cs = await probe<{ rx: number; offsetY: number | null }>(page, 'camera');
      expect(Math.abs(cs.rx) < 1e-9 && cs.offsetY !== null && cs.offsetY < 0, 'straight verticals: level camera, picture slides up').toBe(true);
      await setInput(page, sel.eye, 1.2);
      let s = await st(page);
      expect(Math.abs(s.y - (s.level + 1.2)), 'the eye height slider lowers the camera').toBeLessThan(0.01);
      await setInput(page, sel.eye, 1.6);
      shot = await download(page, testInfo, () => p.clickEl(sel.shot));
      expect(shot.name).toMatch(new RegExp(`^${P.photoName}_Walk_${P.firstName.replace(/[()]/g, '\\$&')}_24mm_`));
      expect(shot.size).toEqual([1920, 1280]);

      await setInput(page, sel.sizeSelect, 3840, 'change');
      expect(await textOf(page, sel.px)).toBe('3840 × 2560 px');
      shot = await download(page, testInfo, () => p.press('KeyP'));
      expect(shot.size, '4K').toEqual([3840, 2560]);
      await setInput(page, sel.frameSelect, '9:16', 'change');
      expect(await textOf(page, sel.px)).toBe('2160 × 3840 px');
      shot = await download(page, testInfo, () => p.press('KeyP'));
      expect(shot.size, '9:16 upright').toEqual([2160, 3840]);
      await setInput(page, sel.frameSelect, 'screen', 'change'); await setInput(page, sel.sizeSelect, 1920, 'change');
      shot = await download(page, testInfo, () => p.press('KeyP'));
      const [vw, vh] = await page.evaluate(() => [innerWidth, innerHeight]);
      expect(shot.size[0] === 1920 && Math.abs(shot.size[1]! - Math.round(1920 * vh! / vw!)) <= 1, `whole screen keeps the window shape ${shot.size}`).toBe(true);
      const cam = await probe<{ fov: number; offsetY: number | null }>(page, 'camera');
      expect(cam.offsetY !== null && Math.abs(cam.fov - lensFov(24)) < 0.01, 'the view is back to normal after photos (no leftover crop)').toBe(true);
      await p.clickEl(sel.straight); await setInput(page, sel.frameSelect, '3:2', 'change');
      await p.clickEl(sel.cameraClose);
      expect(!(await visible(page, sel.cameraPanel)) && !(await visible(page, sel.frame)), 'the Camera panel closes').toBe(true);
      shot = await download(page, testInfo, () => p.press('KeyP'));
      expect(shot.size[0] === 1920 && Math.abs(shot.size[1]! - Math.round(1920 * vh! / vw!)) <= 1, `P with the panel closed takes the whole screen ${shot.size}`).toBe(true);
      s = await st(page);
      expect(s.mode).toBe('walk');
      expect(exceptions(p)).toEqual([]);
    });

    test('double-click in Orbit -> Walk at that spot', async ({ page }) => {
      const p = await open(page, P.key);
      await sleep(400);
      await p.dblclick(760, 470); await sleep(400);
      const s = await st(page);
      expect(s.mode, JSON.stringify(s)).toBe('walk');
      expect(await probe<boolean>(page, 'onFloor')).toBe(true);
    });

    test('16 Oct fixes: holding P takes one photo; wheel follows the scroll distance; a focused Frame list hands keys back; the frame fits between the panels below the top bar; Exit clickable; a slow drag does not lock the pointer, a click does; the flash in Orbit', async ({ page }) => {
      const p = await open(page, P.key);
      let n0 = await nPhotos(page);
      await p.keyDown('KeyP'); await p.keyDown('KeyP'); await p.keyDown('KeyP'); await p.keyDown('KeyP');
      await p.keyUp('KeyP');
      await sleep(3000);
      expect((await nPhotos(page)) - n0, 'holding P takes one photo, not a burst').toBe(1);
      if (P.upper) {
        await p.press('Digit3');
        await page.evaluate(y => { (window as any).__viewer.state.pos.y = y; }, P.upper.level + 1.0);
        n0 = await nPhotos(page);
        await p.press('KeyP'); await waitPhoto(page, n0);
        expect(await photoTitle(page), 'in Ghost 1 m above the upper floor, the photo is named after it').toMatch(new RegExp(`_Ghost_${P.upper.name}_`));
      }
      await p.press('Digit2');
      const lens0 = (await st(page)).lens;
      await page.mouse.move(900, 500);
      for (let i = 0; i < 10; i++) await page.mouse.wheel(0, -4);
      await sleep(200);
      const lens1 = (await st(page)).lens;
      await page.mouse.wheel(0, -100);
      await sleep(200);
      const lens2 = (await st(page)).lens;
      expect(Math.abs(lens1 - lens0 - 0.8) < 0.05 && Math.abs(lens2 - lens1 - 2) < 0.05, `wheel: 10 small steps 0.8 mm, one notch 2 mm (${lens0}, ${r2(lens1)}, ${r2(lens2)})`).toBe(true);
      await p.clickEl(sel.cameraBtn);
      await page.evaluate(s => (document.querySelector(s) as HTMLSelectElement).focus(), sel.frameSelect);
      const f0 = await page.evaluate(s => (document.querySelector(s) as HTMLSelectElement).value, sel.frameSelect);
      n0 = await nPhotos(page);
      await p.press('KeyP'); await waitPhoto(page, n0);
      await p.press('Digit4');
      expect(await page.evaluate(s => (document.querySelector(s) as HTMLSelectElement).value, sel.frameSelect), 'typing does not change the frame').toBe(f0);
      expect(await nPhotos(page), 'with the Frame list focused, P still takes a photo').toBe(n0 + 1);
      const g = await page.evaluate(q => {
        const r = (s: string) => document.querySelector(s)!.getBoundingClientRect();
        const f = r(q.frame), c = r(q.cameraPanel), pn = r(q.panel), x = r(q.exit), hud = r(q.hud);
        const hit = document.elementFromPoint(x.left + x.width / 2, x.top + x.height / 2);
        return { frame: [f.left, f.top, f.right, f.bottom].map(Math.round), camLeft: Math.round(c.left), panelRight: Math.round(pn.right), panelShown: pn.width > 0,
          hudBottom: Math.round(hud.bottom), exitClickable: !!hit && hit === document.querySelector(q.exit) };
      }, { frame: sel.frame, cameraPanel: sel.cameraPanel, panel: sel.panel, exit: sel.exit, hud: sel.hud });
      expect(g.frame[0]! >= (g.panelShown ? g.panelRight : 0) && g.frame[2]! <= g.camLeft && g.frame[1]! >= g.hudBottom, `the frame fits between the side panel and the Camera panel, below the top bar ${JSON.stringify(g)}`).toBe(true);
      expect(g.exitClickable, 'Exit stays clickable with the Camera panel open').toBe(true);
      await p.clickEl(sel.cameraClose);
      await page.evaluate(() => { (window as any).__locks = 0; document.querySelector('canvas')!.requestPointerLock = (() => { (window as any).__locks++; }) as any; });
      await page.mouse.move(900, 500); await page.mouse.down();
      for (let i = 1; i <= 30; i++) await page.mouse.move(900 + i, 500);
      await page.mouse.up(); await sleep(200);
      const afterDrag = await page.evaluate(() => (window as any).__locks);
      await p.click(900, 520);
      const afterClick = await page.evaluate(() => (window as any).__locks);
      expect({ afterDrag, afterClick }, 'a slow look-drag does not capture the mouse; a click does').toEqual({ afterDrag: 0, afterClick: 1 });
      await p.press('Digit1');
      await p.keyDown('KeyP');
      const anims = await page.evaluate(s => document.querySelector(s)!.getAnimations().length, sel.flash);
      await p.keyUp('KeyP'); await sleep(1500);
      expect(anims, 'the shutter flash shows in Orbit too').toBeGreaterThanOrEqual(1);
      expect(exceptions(p)).toEqual([]);
    });

    test('typos in the address are ignored; the drawing buffer follows a pixel-ratio change', async ({ page }) => {
      const p = await open(page, P.key, `?mode=walk&yaw=north&pitch=up&nodownload=1${isApp ? '&test=1' : ''}`);
      const s = await st(page);
      expect(s.mode).toBe('walk');
      expect(Number.isFinite(s.yaw) && Number.isFinite(s.pitch) && (await probe<boolean>(page, 'onFloor')), `yaw=north, pitch=up: ${s.yaw}, ${s.pitch}`).toBe(true);
      const cdp = await page.context().newCDPSession(page);
      await cdp.send('Emulation.setDeviceMetricsOverride', { width: 1200, height: 760, deviceScaleFactor: 2, mobile: false });
      await sleep(1200);
      const buf = await page.evaluate(() => [document.querySelector('canvas')!.width, innerWidth, devicePixelRatio]);
      await cdp.send('Emulation.clearDeviceMetricsOverride');
      expect(buf[0], `after a pixel-ratio change the drawing buffer follows (2 pixels per CSS pixel): ${buf}`).toBe(buf[1]! * Math.min(buf[2]!, 2));
      expect(exceptions(p)).toEqual([]);
    });

    if (P.upper) {
      test('Ghost above the hidden upper floor names the photo after the floor showing', async ({ page }) => {
        const p = await open(page, P.key);
        const upper = P.upper!;
        await p.clickEl(sel.floorButton(P.first));
        await p.press('Digit3');
        await page.evaluate(y => { (window as any).__viewer.state.pos.y = y; }, upper.level + 1.4);
        const n0 = await nPhotos(page);
        await p.press('KeyP'); await waitPhoto(page, n0);
        expect(await photoTitle(page)).toMatch(new RegExp(`_Ghost_${P.firstName}_`));
      });
    }

    if (P.key === 'house') {
      test("walking at the end of a thin partition never brings you closer than the body's edge", async ({ page }) => {
        const p = await open(page, P.key);
        await setFurniture(page, false);
        await p.press('Digit2');
        const gap = await page.evaluate(() => {
          const v = (window as any).__viewer, s = v.state; let worst = Infinity;
          for (const [x, z, yaw] of [[21.80, -5.64, 175], [21.80, -5.64, 170], [21.80, -5.64, 180], [21.75, -5.64, 175], [21.85, -5.64, 175]]) {
            s.pos.set(x, s.pos.y, z); let min = v.probe.clearance();
            for (let i = 0; i < 60; i++) { v.probe.walk(yaw, 0.05); min = Math.min(min, v.probe.clearance()); }
            worst = Math.min(worst, min);
          }
          return worst as number;
        });
        expect(gap, `closest approach ${r2(gap)} m`).toBeGreaterThan(0.25);
      });
    }
  });
}
