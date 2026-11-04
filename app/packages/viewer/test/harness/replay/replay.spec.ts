// Builder D harness spec (project `harness`, DESIGN.md 17.4): the replay in headless Edge with the real WebGL renderer on
// the shared test context. The Build card (texts, inputs, the panel and hint hidden), play (steps, captions, the
// hand-over at the start view), skip (Esc, both Skip buttons), replay again and Build settings from the panel, the camera
// path (from above beside the card, tilting without turning, back at the view you left), the rise shader on the GPU
// (pixel by pixel on a synthetic wall), the ground plane's fade, dispose.
//   WT_WEB_PORT=5724 WT_TMP="$TEMP/wt-d" npx playwright test -c tests/e2e/playwright.config.ts --project=harness packages/viewer/test/harness/replay/
// (`--project=harness` with the `=`: Playwright 1.64 reads `--project harness <path>` as two project names.)
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { expect, test, type Page } from '@playwright/test';
import { timedDescribe } from '../../../../../tests/e2e/lib/fps';

const APP = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../../../..');
interface CardFacts {
  inputs: { value: string }[]; introTitle: string; facts: string[]; layersTitle: string; layers: [string, string][];
  steps: { key: string; title: string; caption: string }[]; stepList: string[];
}
const facts = (name: string): CardFacts => (JSON.parse(readFileSync(path.join(APP, 'fixtures/prototype', `${name}.json`), 'utf8')) as { card: CardFacts }).card;

/** Opens the harness page; returns the page errors, console errors and three.js warnings seen from then on. */
async function open(page: Page, query: string): Promise<string[]> {
  const problems: string[] = [];
  page.on('pageerror', e => problems.push(`[exception] ${e.message}`));
  // console errors (but the browser's own favicon request) and three.js warnings; not the driver's performance notes
  page.on('console', m => {
    if (m.type() === 'error' && !/favicon\.ico$/.test(m.location().url)) problems.push(`[console.error] ${m.text()} (${m.location().url})`);
    if (m.type() === 'warning' && /^THREE\./.test(m.text())) problems.push(`[console.warning] ${m.text()}`);
  });
  page.on('response', r => { if (r.status() >= 400 && !/favicon\.ico$/.test(r.url())) problems.push(`[http ${r.status()}] ${r.url()}`); });
  await page.goto(`/replay/replay.html${query}`);
  await page.waitForFunction(() => window.__replayKit !== undefined);
  const kit = await page.evaluate(() => window.__replayKit!);
  expect('error' in kit ? kit.error : null).toBeNull();
  await page.evaluate(() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r))));
  return problems;
}
const phase = (page: Page) => page.evaluate(() => window.__build!.phase);
const display = (page: Page, sel: string) => page.evaluate(s => { const e = document.querySelector(s); return e ? getComputedStyle(e).display : null; }, sel);
const camera = (page: Page) => page.evaluate(() => {
  const ctx = window.__replayCtx!, d = ctx.camera.getWorldDirection(ctx.camera.position.clone());
  return { pos: ctx.camera.position.toArray(), target: ctx.controls.target.toArray(), dir: d.toArray() };
});
const dist = (a: number[], b: number[]) => Math.hypot(...a.map((v, i) => v - b[i]!));

test.describe('replay harness: the Build card', () => {
  test('opens on the drawing with its levels and heights, the layers and the speed; the panel and hint are hidden', async ({ page }) => {
    const problems = await open(page, '?model=bank-v2');
    const f = facts('bank-sampeng-v2');
    expect(await phase(page)).toBe('settings');
    const card = page.locator('[data-wt=replay-card]');
    await expect(card).toBeVisible();
    expect(await page.locator('[data-wt=replay-card] input[type=number]').evaluateAll(es => es.map(e => (e as HTMLInputElement).value))).toEqual(f.inputs.map(i => i.value));
    await expect(page.locator('[data-wt=replay-file]')).toHaveText(f.introTitle);
    expect(await page.locator('[data-wt=replay-facts] li').allTextContents()).toEqual(f.facts);
    await expect(page.locator('[data-wt=replay-layers-title]')).toHaveText(f.layersTitle);
    expect(await page.locator('[data-wt=replay-steps] li').allTextContents()).toEqual(f.stepList);
    expect(await page.locator('[data-wt=replay-speed] [aria-pressed=true]').getAttribute('data-speed')).toBe('normal');
    await expect(page.locator('[data-wt=replay-captions]')).toBeChecked();
    await expect(page.locator('[data-wt=replay-go]')).toHaveText('Generate 3D model');
    expect([await display(page, '[data-wt=panel]'), await display(page, '[data-wt=hint]'), await display(page, '[data-wt=replay-caption]')]).toEqual(['none', 'none', 'none']);
    // where the page had it: 12 px from the top left, 330 px wide plus padding and border (content-box), below the root's height
    const box = (await card.boundingBox())!;
    expect([box.x, box.y, box.width]).toEqual([12, 12, 360]);
    expect(box.height).toBeLessThanOrEqual(880 - 110 + 24 + 2);
    // the speed buttons and the captions tick
    await page.click('[data-wt=replay-speed] [data-speed=quick]');
    expect(await page.locator('[data-wt=replay-speed] [aria-pressed=true]').getAttribute('data-speed')).toBe('quick');
    expect(await page.evaluate(() => window.__build!.state.speed)).toBe('quick');
    await page.click('[data-wt=replay-captions]');
    expect(await page.evaluate(() => window.__build!.state.captions)).toBe(false);
    // a cleared Level box keeps its value; a typed one is applied when it is left (change), clamped
    const l2 = page.locator('[data-wt=replay-card] input[data-floor="L2"][data-prop=level]');
    await l2.fill(''); await l2.press('Tab');
    await expect(l2).toHaveValue('3.70');
    const h1 = page.locator('[data-wt=replay-card] input[data-floor="L1"][data-prop=height]');
    await h1.fill('15'); await h1.press('Tab');
    await expect(h1).toHaveValue('12.00');
    expect(await page.evaluate(() => window.__build!.state.settings.L1!.height)).toBe(12);
    expect(problems).toEqual([]);
  });
});

timedDescribe('replay harness: play', () => {
  test('Generate plays the seven steps with captions, locked, and hands over to the viewer at the start view', async ({ page }) => {
    const problems = await open(page, '?model=bank-v2&speed=quick');
    const l2 = page.locator('[data-wt=replay-card] input[data-floor="L2"][data-prop=level]');
    await l2.fill('5.00'); await l2.press('Tab');
    await expect(l2).toHaveValue('5.00');
    await page.click('[data-wt=replay-go]');
    expect(await phase(page)).toBe('play');
    await expect(page.locator('[data-wt=replay-caption]')).toBeVisible();
    await expect(page.locator('[data-wt=replay-play]')).toBeVisible();
    await expect(page.locator('[data-wt=replay-settings]')).toBeHidden();
    await page.waitForTimeout(2500);
    const mid = await page.evaluate(() => ({ T: window.__build!.state.T, locked: window.__replayCtx!.modes.state.locked, caption: document.querySelector('[data-wt=replay-caption]')!.textContent ?? '',
      states: [...document.querySelectorAll('[data-wt=replay-steps] li')].map(li => li.getAttribute('data-state')) }));
    expect(mid.T).toBeGreaterThan(0.05);
    expect(mid.T).toBeLessThan(1);
    expect(mid.locked).toBe(true);
    expect(mid.caption).toMatch(/\d/);
    expect(mid.states).toContain('now');
    await page.waitForFunction(() => window.__build!.phase === 'done', undefined, { timeout: 40_000 });
    const end = await page.evaluate(() => {
      const ctx = window.__replayCtx!;
      return {
        locked: ctx.modes.state.locked, controls: ctx.controls.enabled, clipping: ctx.renderer.localClippingEnabled,
        groups: ctx.floors.map(f => [f.group.visible, ...f.group.position.toArray().map(v => v + 0)]),
        solids: ctx.floors.every(f => f.rise.every(r => r.mesh.visible)), late: ctx.floors.every(f => f.late.every(o => o.visible)),
        walkLevel: ctx.floors[1]!.level, flag: ctx.ui.root.hasAttribute('data-replay'),
        replayObjects: ctx.floors.some(f => f.group.children.some(c => c.name === 'build replay')),
      };
    });
    expect(end).toEqual({ locked: false, controls: true, clipping: false, groups: [[true, 0, 0, 0], [true, 0, 5 - 3.7, 0]], solids: true, late: true, walkLevel: 5, flag: false, replayObjects: false });
    await expect(page.locator('[data-wt=replay-card]')).toBeHidden();
    await expect(page.locator('[data-wt=replay-caption]')).toBeHidden();
    await expect(page.locator('[data-wt=panel]')).toBeVisible();
    const c = await camera(page);
    expect(dist(c.pos, [24, 27, 29])).toBeLessThan(0.01);
    expect(dist(c.target, [0, 2.5, 0])).toBeLessThan(0.01);
    expect(problems).toEqual([]);
  });

  test('after a replay you are back at the view you left', async ({ page }) => {
    const problems = await open(page, '?model=bank-v2&build=skip');
    await page.mouse.move(900, 450); await page.mouse.down();
    for (let i = 1; i <= 10; i++) await page.mouse.move(900 + i * 15, 450 + i * 3);
    await page.mouse.up();
    let before = await camera(page);                        // wait until the drag's glide has died away
    for (let i = 0; i < 60; i++) { await page.waitForTimeout(300); const c = await camera(page); const d = dist(c.pos, before.pos); before = c; if (d < 0.002) break; }
    expect(dist(before.pos, [24, 27, 29])).toBeGreaterThan(1);
    await page.click('[data-wt=replay-again]');
    await page.waitForTimeout(600);
    expect(await phase(page)).toBe('play');
    await page.keyboard.press('Escape');
    await page.waitForTimeout(500);
    expect(await phase(page)).toBe('done');
    const after = await camera(page);
    expect(dist(after.pos, before.pos)).toBeLessThan(0.1);
    expect(problems).toEqual([]);
  });
});

test.describe('replay harness: skip, replay again, Build settings', () => {
  test('Esc and both Skip buttons skip; the panel replays it and reopens Build settings with the changed values', async ({ page }) => {
    const problems = await open(page, '?model=bank-v2');
    const l2 = page.locator('[data-wt=replay-card] input[data-floor="L2"][data-prop=level]');
    await l2.fill('5.00'); await l2.press('Tab');
    await page.click('[data-wt=replay-skip-settings]');
    expect(await phase(page)).toBe('done');
    await expect(page.locator('[data-wt=panel]')).toBeVisible();
    expect(await page.evaluate(() => window.__replayCtx!.floors[1]!.level)).toBe(5);
    await page.click('[data-wt=replay-again]');
    expect(await phase(page)).toBe('play');
    await page.keyboard.press('Escape');
    expect(await phase(page)).toBe('done');
    await page.click('[data-wt=replay-open]');
    expect(await phase(page)).toBe('settings');
    await expect(l2).toHaveValue('5.00');
    await page.click('[data-wt=replay-go]');
    expect(await phase(page)).toBe('play');
    await page.click('[data-wt=replay-skip]');
    expect(await phase(page)).toBe('done');
    // Esc on the settings screen does nothing (only while it plays)
    await page.click('[data-wt=replay-open]');
    await page.keyboard.press('Escape');
    expect(await phase(page)).toBe('settings');
    expect(problems).toEqual([]);
  });
});

test.describe('replay harness: the camera path', () => {
  test('from above with the drawings beside the card, tilting without turning while the floors line up, all steps ticked at seek(1)', async ({ page }) => {
    const problems = await open(page, '?model=bank-v2');
    // seek(0): straight down, the drawings (side by side) framed in the part of the root right of the card
    const top = await page.evaluate(() => {
      const ctx = window.__replayCtx!, b = window.__build!;
      b.seek(0);
      const card = ctx.rectOf(document.querySelector('[data-wt=replay-card]')!), size = ctx.size();
      let x0 = Infinity, x1 = -Infinity, y0 = Infinity, y1 = -Infinity;
      const corners: number[][] = [];
      for (const f of ctx.floors) {
        const sf = ctx.stages!.floors[f.key]!;
        for (const [cat, a] of Object.entries(sf.lines)) {
          if (cat === 'noise') continue;
          for (let i = 0; i < a.length; i += 2) { x0 = Math.min(x0, a[i]! + sf.sheet[0]); x1 = Math.max(x1, a[i]! + sf.sheet[0]); y0 = Math.min(y0, a[i + 1]! + sf.sheet[1]); y1 = Math.max(y1, a[i + 1]! + sf.sheet[1]); }
        }
      }
      for (const [x, y] of [[x0, y0], [x1, y0], [x0, y1], [x1, y1]]) {
        const v = ctx.camera.position.clone().set(x!, 0, -y!).project(ctx.camera);
        corners.push([(v.x + 1) / 2 * size.width, (1 - v.y) / 2 * size.height]);
      }
      const d = ctx.camera.getWorldDirection(ctx.camera.position.clone());
      return { dir: d.toArray(), corners, card, size };
    });
    expect(top.dir[1]).toBeLessThan(-0.9999);
    for (const [x, y] of top.corners) {
      expect(x!).toBeGreaterThanOrEqual(top.card.right + 8 - 1);
      expect(x!).toBeLessThanOrEqual(top.size.width - 8 + 1);
      expect(y!).toBeGreaterThanOrEqual(8 - 1);
      expect(y!).toBeLessThanOrEqual(top.size.height - 86 + 1);   // seek() plays: room for the caption
    }
    const az: number[] = [];
    for (const T of [0.32, 0.35, 0.38]) {
      await page.evaluate(t => window.__build!.seek(t), T);
      await page.waitForTimeout(250);
      const c = await camera(page);
      az.push(Math.atan2(c.dir[0]!, c.dir[2]!) * 180 / Math.PI);
    }
    const turn = (a: number, b: number) => Math.abs(((a - b + 540) % 360) - 180);
    expect(turn(az[1]!, az[0]!)).toBeLessThan(2);
    expect(turn(az[2]!, az[1]!)).toBeLessThan(2);
    await page.evaluate(() => window.__build!.seek(1));
    await page.waitForTimeout(300);
    await expect(page.locator('[data-wt=replay-steps] li[data-state=done]')).toHaveCount(7);
    await page.evaluate(() => window.__build!.skip());
    expect(problems).toEqual([]);
  });
});

test.describe('replay harness: on the GPU', () => {
  test('the walls rise in the shader: nothing before the raise, the lower half at mid-rise, the whole wall at the end', async ({ page }) => {
    const problems = await open(page, '?model=synthetic');
    const steps = await page.evaluate(() => window.__build!.steps.map(s => ({ key: s.key, t0: s.t0, t1: s.t1 })));
    const merge = steps.find(s => s.key === 'merge')!, raise = steps.find(s => s.key === 'raise')!;
    const H = [0.75, 1.25, 1.75, 2.25, 3.8];
    const px = (T: number | null) => page.evaluate(([t, h]) => (window.__replayKit as { pixels(T: number | null, h: number[]): number[][] }).pixels(t, h), [T, H] as const);
    const before = await px((merge.t0 + merge.t1) / 2);
    const mid = await px(raise.t0 + (raise.t1 - raise.t0) * 0.31);      // the floor's uRise 0.5: the wall's top at 1.5 m
    const done = await px(null);
    const bg = done[4]!;                                    // nothing above the wall
    const same = (a: number[], b: number[]) => a.every((v, i) => Math.abs(v - b[i]!) <= 3);
    test.info().annotations.push({ type: 'pixels', description: JSON.stringify({ before, mid, done }) });
    expect(same(done[0]!, bg)).toBe(false);
    expect(same(done[3]!, bg)).toBe(false);
    expect(before.every(p => same(p, bg))).toBe(true);
    expect(same(mid[0]!, done[0]!)).toBe(true);
    expect(same(mid[1]!, done[1]!)).toBe(true);
    expect(same(mid[2]!, bg)).toBe(true);
    expect(same(mid[3]!, bg)).toBe(true);
    expect(problems).toEqual([]);
  });

  test('the ground plane fades in with the floor plates at the end, and dispose leaves nothing behind', async ({ page }) => {
    const problems = await open(page, '?model=bank-v2&ground=1');
    const look = (T: number | null) => page.evaluate(t => {
      const ctx = window.__replayCtx!, b = window.__build!;
      if (t === null) b.skip(); else b.seek(t);
      const g = ctx.built.groundPlane!, m = g.material as { opacity: number; transparent: boolean };
      const plate = ctx.floors[0]!.walkables[0]!, pm = plate.material as { opacity: number };
      return { visible: g.visible, opacity: m.opacity, transparent: m.transparent, plate: plate.visible, plateOpacity: pm.opacity };
    }, T);
    const fin = await page.evaluate(() => { const s = window.__build!.steps.find(x => x.key === 'finish')!; return [s.t0, s.t1]; });
    expect(await display(page, '[data-wt=replay-card]')).toBe('block');
    expect((await look(0.5)).visible).toBe(false);
    const half = await look((fin[0]! + fin[1]!) / 2);
    expect(half.visible && half.plate && half.transparent).toBe(true);
    expect(half.opacity).toBeGreaterThan(0.2); expect(half.opacity).toBeLessThan(0.8);
    expect(half.plateOpacity).toBeCloseTo(half.opacity, 9);
    expect(await look(null)).toEqual({ visible: true, opacity: 1, transparent: false, plate: true, plateOpacity: 1 });
    await page.waitForTimeout(300);
    const left = await page.evaluate(() => {
      window.__replayCtx!.disposer.dispose();
      return { replay: document.querySelectorAll('[data-wt^=replay-]').length, roots: document.querySelectorAll('[data-wt=root]').length, canvases: document.querySelectorAll('canvas').length };
    });
    expect(left).toEqual({ replay: 0, roots: 0, canvases: 0 });
    expect(problems).toEqual([]);
  });
});
