// Builder D harness spec on the REAL viewer (project `harness`, DESIGN.md 17.4): /replay/viewer.html mounts createViewer
// (A's assembly, B's modes, C's root, panel and furniture, this replay) with the test hook, as the offline file will, so the
// replay is checked with the modules it works with before the integration step: the card in the real root (its CSS under
// `all: revert`), keys locked, Generate with a changed level, the hand-over, Walk at that level, replay again, Esc, Build
// settings, Skip; the house's ground plane with A's real build; ?cam=1 after the build screen; dispose.
//   WT_WEB_PORT=5724 WT_TMP="$TEMP/wt-d" npx playwright test -c tests/e2e/playwright.config.ts --project=harness packages/viewer/test/harness/replay/
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { expect, test, type Page } from '@playwright/test';
import { timedDescribe } from '../../../../../tests/e2e/lib/fps';

const APP = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../../../..');
const facts = (name: string) => (JSON.parse(readFileSync(path.join(APP, 'fixtures/prototype', `${name}.json`), 'utf8')) as {
  card: { inputs: { value: string }[]; facts: string[]; stepList: string[]; introTitle: string; layersTitle: string };
}).card;

/** Opens the page on a project; returns the page errors, console errors and three.js / viewer warnings seen from then on. */
async function open(page: Page, query: string): Promise<string[]> {
  const problems: string[] = [];
  page.on('pageerror', e => problems.push(`[exception] ${e.message}`));
  page.on('console', m => {
    if (m.type() === 'error' && !/favicon\.ico$/.test(m.location().url)) problems.push(`[console.error] ${m.text()}`);
    if (m.type() === 'warning' && /^(THREE\.|\[viewer\])/.test(m.text())) problems.push(`[console.warning] ${m.text()}`);
  });
  await page.goto(`/replay/viewer.html${query}`);
  await page.waitForFunction(() => window.__replayViewer !== undefined && window.__replayViewer.status !== 'loading', undefined, { timeout: 60_000 });
  const st = await page.evaluate(() => window.__replayViewer!);
  expect(st.error ?? null).toBeNull();
  expect(st.status).toBe('ready');
  return problems;
}
const phase = (page: Page) => page.evaluate(() => window.__build!.phase);
const shown = (page: Page, sel: string) => page.evaluate(s => {
  const e = document.querySelector(s);
  return !!e && getComputedStyle(e).display !== 'none' && e.getBoundingClientRect().width > 0;
}, sel);
const setBox = (page: Page, floor: string, prop: 'level' | 'height', value: string) => page.evaluate(([f, p, v]) => {
  const e = document.querySelector<HTMLInputElement>(`[data-wt=replay-card] input[data-floor="${f}"][data-prop=${p}]`)!;
  e.value = v!; e.dispatchEvent(new Event('change'));
  return e.value;
}, [floor, prop, value]);
const modes = (page: Page) => page.evaluate(() => { const s = window.__viewer!.state; return { mode: s.mode, floor: s.floor.key, y: s.pos.y, locked: s.locked }; });
const press = async (page: Page, code: string) => { await page.keyboard.press(code); await page.waitForTimeout(150); };

test.describe('replay on the real viewer: the Build card', () => {
  test('bank v2 opens on Build settings in the real root: its texts, its CSS, the panel and hint hidden, the keys locked, the Build row in its slot', async ({ page }) => {
    const problems = await open(page, '?project=bank-v2');
    const f = facts('bank-sampeng-v2');
    expect(await phase(page)).toBe('settings');
    expect(await shown(page, '[data-wt=replay-card]')).toBe(true);
    expect([await shown(page, '[data-wt=panel]'), await shown(page, '[data-wt=hint]'), await shown(page, '[data-wt=replay-caption]')]).toEqual([false, false, false]);
    expect(await page.locator('[data-wt=replay-card] input[type=number]').evaluateAll(es => es.map(e => (e as HTMLInputElement).value))).toEqual(f.inputs.map(i => i.value));
    await expect(page.locator('[data-wt=replay-file]')).toHaveText(f.introTitle);
    expect(await page.locator('[data-wt=replay-facts] li').allTextContents()).toEqual(f.facts);
    await expect(page.locator('[data-wt=replay-layers-title]')).toHaveText(f.layersTitle);
    expect(await page.locator('[data-wt=replay-steps] li').allTextContents()).toEqual(f.stepList);
    // the page's look under the root's `all: revert` (content-box: 330 + 28 + 2; bullets; a bold heading; the accent button)
    const look = await page.evaluate(() => {
      const card = document.querySelector<HTMLElement>('[data-wt=replay-card]')!, cs = (s: string) => getComputedStyle(card.querySelector(s)!);
      return { width: card.offsetWidth, left: card.getBoundingClientRect().left, top: card.getBoundingClientRect().top, bullets: cs('[data-wt=replay-facts]').listStyleType,
        h1: cs('h1').fontWeight, go: cs('[data-wt=replay-go]').backgroundColor, speed: getComputedStyle(card.querySelector('[data-speed=normal]')!).backgroundColor };
    });
    expect(look).toEqual({ width: 360, left: 12, top: 12, bullets: 'disc', h1: '700', go: 'rgb(47, 111, 143)', speed: 'rgb(47, 111, 143)' });
    // the Build row in the panel's build slot, the furniture after it
    const row = await page.evaluate(() => {
      const r = document.querySelector('[data-wt=replay-row]'), slot = r?.closest('[data-slot]'), furn = document.querySelector('[data-slot=furniture]');
      return { slot: slot?.getAttribute('data-slot') ?? null, furnitureAfter: !!(furn && r && (r.compareDocumentPosition(furn) & Node.DOCUMENT_POSITION_FOLLOWING)), text: r?.textContent ?? null };
    });
    expect(row).toEqual({ slot: 'build', furnitureAfter: true, text: 'BuildReplay the buildBuild settings' });
    // viewer keys do nothing on the settings screen
    await press(page, 'Digit2');
    expect(await modes(page)).toMatchObject({ mode: 'orbit', locked: true });
    expect(problems).toEqual([]);
  });
});

timedDescribe('replay on the real viewer: Generate', () => {
  test('bank v2: the level set before Generate is the one walked; Replay plays again; Esc skips; Build settings reopen with it; Skip on the card', async ({ page }) => {
    const problems = await open(page, '?project=bank-v2');
    expect(await setBox(page, 'L2', 'level', '5.00')).toBe('5.00');
    await page.click('[data-wt=replay-speed] [data-speed=quick]');
    await page.click('[data-wt=replay-go]');
    expect(await phase(page)).toBe('play');
    expect(await shown(page, '[data-wt=replay-caption]')).toBe(true);
    await page.waitForTimeout(2500);
    const mid = await page.evaluate(() => ({ T: window.__build!.state.T, caption: document.querySelector('[data-wt=replay-caption]')!.textContent ?? '' }));
    expect(mid.T).toBeGreaterThan(0.05);
    expect(mid.T).toBeLessThan(1);
    expect(mid.caption).toMatch(/\d/);
    await press(page, 'Digit3');
    expect(await modes(page)).toMatchObject({ mode: 'orbit', locked: true });
    await page.waitForFunction(() => window.__build!.phase === 'done', undefined, { timeout: 40_000 });
    const end = await page.evaluate(() => ({
      locked: window.__viewer!.state.locked, visible: window.__viewer!.probe.visible(),
      groups: window.__host!.floors.map(f => [f.key, f.group.visible, ...f.group.position.toArray().map(v => Math.round(v * 1e6) / 1e6 + 0)]),
      replayObjects: window.__host!.floors.some(f => f.group.children.some(c => c.name === 'build replay')),
    }));
    expect(end).toEqual({ locked: false, visible: ['L1', 'L2'], groups: [['L1', true, 0, 0, 0], ['L2', true, 0, 1.3, 0]], replayObjects: false });
    expect(await shown(page, '[data-wt=panel]')).toBe(true);
    expect(await shown(page, '[data-wt=replay-card]')).toBe(false);
    await press(page, 'Digit2'); await press(page, 'PageUp');
    const walk = await modes(page);
    expect(walk.mode).toBe('walk');
    expect(walk.floor).toBe('L2');
    expect(Math.abs(walk.y - 6.6)).toBeLessThan(0.01);
    expect(await page.evaluate(() => window.__viewer!.probe.onFloor())).toBe(true);
    await press(page, 'Escape');
    expect((await modes(page)).mode).toBe('orbit');
    await page.click('[data-wt=replay-again]'); await page.waitForTimeout(600);
    expect(await phase(page)).toBe('play');
    await press(page, 'Escape');
    expect(await phase(page)).toBe('done');
    await page.click('[data-wt=replay-open]'); await page.waitForTimeout(300);
    expect(await phase(page)).toBe('settings');
    await expect(page.locator('[data-wt=replay-card] input[data-floor="L2"][data-prop=level]')).toHaveValue('5.00');
    await page.click('[data-wt=replay-skip-settings]'); await page.waitForTimeout(300);
    expect(await phase(page)).toBe('done');
    expect(problems).toEqual([]);
  });
});

test.describe('replay on the real viewer: the house and the suite', () => {
  test('house: its levels and heights, the walls rise, the ground plane fades in with the plates, opaque after', async ({ page }) => {
    const problems = await open(page, '?project=house');
    expect(await page.locator('[data-wt=replay-card] input[type=number]').evaluateAll(es => es.map(e => (e as HTMLInputElement).value))).toEqual(['0.90', '3.90', '4.80', '3.50']);
    const look = (T: number | 'skip' | 'none') => page.evaluate(t => {
      if (t === 'skip') window.__build!.skip(); else if (t !== 'none') window.__build!.seek(t);
      const scene = window.__host!.floors[0]!.group.parent!;
      const g = scene.children.find(o => o.name === 'ground plane') as unknown as { visible: boolean; material: { opacity: number; transparent: boolean } };
      const plate = window.__host!.floors[0]!.walkables[0]!, pm = plate.material as unknown as { opacity: number };
      return { ground: [g.visible, g.material.opacity, g.material.transparent], plate: [plate.visible, pm.opacity],
        walls: window.__host!.floors.map(f => f.rise.filter(r => r.mesh.visible).length) };
    }, T);
    const steps = await page.evaluate(() => Object.fromEntries(window.__build!.steps.map(s => [s.key, [s.t0, s.t1]])) as Record<string, [number, number]>);
    const n = await page.evaluate(() => window.__host!.floors.map(f => f.rise.length));
    const atStart = await look('none');
    expect(atStart.ground[0]).toBe(false);
    expect(atStart.plate[0]).toBe(false);
    expect(atStart.walls).toEqual([0, 0]);
    const merge = await look((steps.merge![0] + steps.merge![1]) / 2);
    expect(merge.walls).toEqual([0, 0]);
    expect(merge.ground[0]).toBe(false);
    const half = await look((steps.finish![0] + steps.finish![1]) / 2);
    expect(half.walls).toEqual(n);
    expect(half.ground[0]).toBe(true);
    expect(half.ground[2]).toBe(true);
    expect(half.ground[1] as number).toBeGreaterThan(0.2);
    expect(half.ground[1] as number).toBeLessThan(0.8);
    expect(half.plate[1] as number).toBeCloseTo(half.ground[1] as number, 9);
    expect(await look('skip')).toEqual({ ground: [true, 1, false], plate: [true, 1], walls: n });
    expect(problems).toEqual([]);
  });

  test('house: ?cam=1 opens the Camera panel after the build screen, not over it', async ({ page }) => {
    const problems = await open(page, '?project=house&cam=1');
    const during = await shown(page, '[data-wt=camera-panel]');
    await page.click('[data-wt=replay-skip-settings]'); await page.waitForTimeout(400);
    expect(during).toBe(false);
    expect(await shown(page, '[data-wt=camera-panel]')).toBe(true);
    expect(problems).toEqual([]);
  });

  test('suite (one floor): all seven steps at seek(1), the hand-over shows its one floor; dispose leaves nothing of the replay', async ({ page }) => {
    const problems = await open(page, '?project=suite');
    expect(await phase(page)).toBe('settings');
    await page.evaluate(() => window.__build!.seek(1)); await page.waitForTimeout(300);
    await expect(page.locator('[data-wt=replay-steps] li[data-state=done]')).toHaveCount(7);
    await page.evaluate(() => window.__build!.skip());
    expect(await phase(page)).toBe('done');
    expect(await page.evaluate(() => window.__viewer!.probe.visible())).toEqual(['suite']);
    expect(await shown(page, '[data-wt=panel]')).toBe(true);
    const left = await page.evaluate(() => {
      window.__walkthrough!.viewer.dispose();
      return { replay: document.querySelectorAll('[data-wt^=replay-]').length, roots: document.querySelectorAll('.wtv').length, build: '__build' in window };
    });
    expect(left).toEqual({ replay: 0, roots: 0, build: false });
    expect(problems).toEqual([]);
  });
});
