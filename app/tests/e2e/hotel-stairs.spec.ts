// The hotel's main stair is climbed in Edge (the owner's request of 16 Nov 2026; rooms/DESIGN.md "Amended after the
// independent review", R-9): the hotel (seeded on 2 Nov from two plan pictures; BuiltModel v1, no `stairways`) used to stop
// the walk at its first steps. The viewer now makes its complete F1 flight a stairway when it loads the model
// (packages/viewer/src/model/upgrade.ts), in memory only: the file's data and its stamp stay as they are.
//
// On the hotel's offline file made from the template of the viewer as it is now: WT_OFFLINE_DIR (lib/target.ts
// oldPagePath), else dist/offline. App target only (the prototype page has no climbing).
//   node node_modules/vite/bin/vite.js build -c packages/viewer/vite.offline.config.ts --outDir "$TEMP/wt-hs/offline-template" --emptyOutDir
//   node tools/run-py.mjs -m walkthrough_api.seed --prototypes .. --data "$TEMP/wt-hs/seed" --force
//   node packages/viewer/scripts/make-offline.mjs --data "$TEMP/wt-hs/seed" --template "$TEMP/wt-hs/offline-template/viewer-template.html" --out "$TEMP/wt-hs/offline"
//   WT_WEB_PORT=5751 WT_API_PORT=8751 WT_TMP="$TEMP/wt-hs/run" WT_SERVE=none WT_SKIP_STORE_CHECK=1 WT_OFFLINE_DIR="$TEMP/wt-hs/offline" \
//     npx playwright test -c tests/e2e/playwright.config.ts --project=e2e tests/e2e/hotel-stairs.spec.ts
import { existsSync } from 'node:fs';
import { pathToFileURL } from 'node:url';
import { expect, test, type Page } from '@playwright/test';
import { timedDescribe } from './lib/fps';
import { pageApi, sleep, type KeyCode, type PageApi } from './lib/page';
import { APP_ONLY, isOn, noNetwork, oldPagePath, sel, VERSIONS, waitReady } from './lib/target';
import { stairWalks } from './lib/walks';

/* eslint-disable @typescript-eslint/no-explicit-any */

const FILE = oldPagePath('hotel');
const QUERY = '?build=0&nodownload=1&test=1';
/** Floor 2's level, and the flight in plan: the first step from y -1.528, the last to y 2.8, the centre line x -3.415. */
const F2 = 2.9, Y0 = -1.528, Y1 = 2.8, XC = -3.415;
const STEP_UP = 0.25, STEP_DOWN = 0.30, EPS = 1e-4;

async function open(page: Page): Promise<{ p: PageApi; requests: string[]; problems: () => string[] }> {
  const p = await pageApi(page);
  const net = await noNetwork(page);
  await page.goto(pathToFileURL(FILE).href + QUERY);
  await waitReady(page);
  const problems = () => p.logs.filter(l => (l.startsWith('[exception]') || l.startsWith('[console.error]')) && !/favicon/i.test(l));
  return { p, requests: net.requests, problems };
}

const st = (page: Page) => page.evaluate(() => {
  const s = (window as any).__viewer.state;
  return { mode: s.mode as string, floor: s.floor.key as string, foot: s.foot as number, x: s.pos.x as number, y: -s.pos.z as number, eye: s.pos.y as number };
});

/** Holds a key until `done` says so (or `maxMs`), sampling the walker every 50 ms; returns the samples. */
async function hold(page: Page, p: PageApi, code: KeyCode, done: (s: Awaited<ReturnType<typeof st>>) => boolean, maxMs = 90_000) {
  const seen: Awaited<ReturnType<typeof st>>[] = [await st(page)], t0 = Date.now();
  await p.keyDown(code);
  try {
    while (Date.now() - t0 < maxMs) {
      await sleep(50);
      const now = await st(page);
      seen.push(now);
      if (done(now)) break;
    }
  } finally {
    await p.keyUp(code);
  }
  await sleep(200);
  seen.push(await st(page));
  return { seen, ms: Date.now() - t0 };
}

test.describe('the hotel: the main stair is climbed', { tag: APP_ONLY }, () => {
  test.skip(process.env.E2E_TARGET === 'prototype', 'the app viewer only');

  test('the offline file is there', () => {
    expect(existsSync(FILE), `${FILE} (make it as the header says, or npm run build)`).toBe(true);
  });

  test('the loaded model has one derived stairway, F1 to F2, 17 risers; the treads are walked on; F2-S1 stays steps; the file and its stamp are as saved', async ({ page }) => {
    const { requests, problems } = await open(page);
    const facts = await page.evaluate(() => {
      const h = (window as any).__host, M = h.model, count = (k: string, f: string) => M.parts.filter((q: any) => q.kind === k && q.floor === f).length;
      const names = (f: string) => (h.groups[f].children as any[]).map(o => o.name as string);
      const data = document.getElementById('wtv-data');
      return {
        stairways: (M.stairways ?? []).map((s: any) => ({ id: s.id, from: s.from, to: s.to, risers: s.risers, riser: s.riser, treads: s.treads, derived: s.derived })),
        treadsF1: count('tread', 'F1'), stepsF1: count('step', 'F1'), stepsF2: count('step', 'F2'), treadsF2: count('tread', 'F2'),
        f1: names('F1'), f2: names('F2'),
        surfacesF1: (h.FL.F1.surfaces as any[]).map(m => m.name as string).sort(),
        collidersF1: (h.FL.F1.colliders as any[]).map(m => m.name as string),
        stamp: document.querySelector('meta[name=model-data]')?.getAttribute('content') ?? null,
        // the data in the page is the saved model: no `stairways` key in it
        saved: data ? (data.textContent ?? '').includes('"stairways"') : null,
      };
    });
    expect(facts.stairways).toHaveLength(1);
    expect(facts.stairways[0]).toMatchObject({ id: 'F1-S1', from: 'F1', to: 'F2', risers: 17, treads: 16, derived: 'steps' });
    expect(facts.stairways[0].riser).toBeCloseTo(0.1706, 4);
    expect([facts.treadsF1, facts.stepsF1, facts.treadsF2, facts.stepsF2]).toEqual([16, 0, 0, 7]);
    expect(facts.f1).toContain('F1 tread:storey');
    expect(facts.f1).not.toContain('F1 step:own');
    expect(facts.f2).toContain('F2 step:own');
    expect(facts.surfacesF1).toContain('F1 tread:storey');
    expect(facts.collidersF1).not.toContain('F1 tread:storey');
    expect(facts.stamp).toContain(VERSIONS.hotel.stamp!);
    expect(facts.saved).toBe(false);
    expect(requests).toEqual([]);
    expect(problems()).toEqual([]);
  });

  test('the probe walks the stairway up to Floor 2 and down again along its walking line (5 cm moves, no crossing)', async ({ page }) => {
    const { p, problems } = await open(page);
    await p.press('Digit2');
    for (const dir of ['up', 'down'] as const) {
      const [r] = await stairWalks(page, { stair: 'F1-S1', dir });
      expect(r, `the ${dir} walk`).toBeTruthy();
      const [endLevel, endFloor] = dir === 'up' ? [r!.upper, 'F2'] : [r!.lower, 'F1'];
      expect([r!.lower, r!.upper]).toEqual([0, F2]);
      expect(Math.abs(r!.end.foot - endLevel), `${dir}: the end foot ${r!.end.foot}`).toBeLessThanOrEqual(0.02);
      expect(r!.end.floor).toBe(endFloor);
      expect(r!.modechange[r!.modechange.length - 1]?.floor).toBe(endFloor);
      expect(r!.pieces.filter(q => q.crosses)).toEqual([]);
      expect(r!.maxRise).toBeLessThanOrEqual(STEP_UP + EPS);
      expect(r!.maxDrop).toBeLessThanOrEqual(STEP_DOWN + EPS);
      expect(await isOn(page.locator(sel.floorButton(endFloor)))).toBe(true);
    }
    expect(problems()).toEqual([]);
  });

  timedDescribe('the hotel: by keyboard, as the owner walks it', () => {
    test("Walk from a double-click at the foot of the main stair, facing it: holding W reaches Floor 2's level (2.90 m) and lights the Floor 2 button; S comes back down", async ({ page }, info) => {
      test.setTimeout(300_000);
      const { p, problems } = await open(page);
      // Floor 1 alone, seen from straight above the foot of the stair; a double-click there starts Walk on that spot
      await page.locator(sel.floorButton('F1')).click();
      await page.locator(sel.floorButton('F1')).blur();
      const at = await page.evaluate(({ x, y }) => {
        const w = window as any, h = w.__host, T = w.__walkthrough.THREE;
        h.camera.position.set(x + 0.01, 14, -y + 0.01);
        h.controls.target.set(x, 0, -y);
        h.controls.update();
        h.camera.updateMatrixWorld();
        const v = new T.Vector3(x, 0, -y).project(h.camera), r = document.querySelector('canvas')!.getBoundingClientRect();
        return { cx: r.left + (v.x + 1) / 2 * r.width, cy: r.top + (1 - v.y) / 2 * r.height };
      }, { x: XC, y: Y0 - 0.9 });
      await sleep(300);
      await p.dblclick(at.cx, at.cy);
      await sleep(400);
      const start = await st(page);
      expect([start.mode, start.floor]).toEqual(['walk', 'F1']);
      expect(Math.abs(start.foot)).toBeLessThan(1e-3);
      expect(Math.hypot(start.x - XC, start.y - (Y0 - 0.9)), `Walk started at (${start.x.toFixed(2)}, ${start.y.toFixed(2)})`).toBeLessThan(0.6);
      expect(await isOn(page.locator(sel.floorButton('F1')))).toBe(true);
      // face the stair (plan +y), as the owner turns to it
      await page.evaluate(() => { const s = (window as any).__viewer.state; s.yaw = 0; s.pitch = 0; });

      const up = await hold(page, p, 'KeyW', s => s.y > Y1 + 0.8);
      const top = up.seen[up.seen.length - 1]!;
      info.annotations.push({ type: 'W', description: `held ${up.ms} ms: foot ${start.foot.toFixed(3)} -> ${top.foot.toFixed(3)} m, y ${start.y.toFixed(2)} -> ${top.y.toFixed(2)}, floor ${top.floor}` });
      expect(top.y, 'W went past the last step (y 2.8)').toBeGreaterThan(Y1 + 0.5);
      expect(top.foot).toBeCloseTo(F2, 2);
      expect(top.floor).toBe('F2');
      expect(await page.evaluate(() => (window as any).__viewer.probe.foot() as number)).toBeCloseTo(F2, 2);
      expect(await isOn(page.locator(sel.floorButton('F2')))).toBe(true);
      expect(await isOn(page.locator(sel.floorButton('F1')))).toBe(false);
      expect(await page.locator(sel.hudText).textContent()).toContain('Floor 2');
      // the foot only ever went up, a riser (or a few, between two samples) at a time, and the eye followed it
      for (let i = 1; i < up.seen.length; i++) expect(up.seen[i]!.foot).toBeGreaterThanOrEqual(up.seen[i - 1]!.foot - 1e-6);
      expect(new Set(up.seen.map(s => Math.round(s.foot * 100))).size, 'several treads were seen under the foot').toBeGreaterThan(5);
      await sleep(600);
      expect((await st(page)).eye).toBeCloseTo(F2 + 1.6, 1);

      const down = await hold(page, p, 'KeyS', s => s.y < Y0 - 0.6);
      const foot = down.seen[down.seen.length - 1]!;
      info.annotations.push({ type: 'S', description: `held ${down.ms} ms: foot ${top.foot.toFixed(3)} -> ${foot.foot.toFixed(3)} m, y ${top.y.toFixed(2)} -> ${foot.y.toFixed(2)}, floor ${foot.floor}` });
      expect(foot.y).toBeLessThan(Y0 - 0.3);
      expect(Math.abs(foot.foot)).toBeLessThan(0.01);
      expect(foot.floor).toBe('F1');
      expect(await isOn(page.locator(sel.floorButton('F1')))).toBe(true);
      expect(await isOn(page.locator(sel.floorButton('F2')))).toBe(false);
      expect(problems()).toEqual([]);
    });
  });
});
