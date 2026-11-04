// The build replay in headless Edge (builder D; DESIGN.md 17.4 "replay", ported from viewer-modes/test_viewers.mjs
// sections replay and fixes2, and the replay checks of bank_test/test_bank.mjs, presidential_test/test_presidential.mjs
// and cad_test/test_house_furniture.mjs). Runs on both targets (lib/target.ts):
//   WT_WEB_PORT=5724 WT_TMP="$TEMP/wt-d" E2E_TARGET=prototype npx playwright test -c tests/e2e/playwright.config.ts --project=e2e tests/e2e/replay.spec.ts
// E2E_TARGET=app (integration) opens dist/offline/<project>-v<n>.html. The Build card and the captions at the default
// settings are compared with what the prototype pages showed (fixtures/prototype/*.json): on the app target that checks
// the seed's converted stages (the house's captions are computed by its page, DESIGN.md 7.4) through the real viewer.
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { expect, test, type Page } from '@playwright/test';
import { timedDescribe } from './lib/fps';
import { pageApi, sleep, type PageApi } from './lib/page';
import { APP, noNetwork, pageUrl, sel, VERSIONS, type VersionKey } from './lib/target';

interface CardFacts {
  inputs: { floor: string; prop: 'level' | 'height'; value: string }[];
  introTitle: string; facts: string[]; layersTitle: string; layers: [string, string][];
  settings: Record<string, { level: number; height: number }>;
  steps: { key: string; title: string; caption: string }[]; stepList: string[];
}
const FACTS: Record<string, string> = { 'bank-v1': 'bank-sampeng-v1', 'bank-v2': 'bank-sampeng-v2', suite: 'presidential-suite', house: 'sukhumvit-house' };
const card = (key: VersionKey): CardFacts =>
  (JSON.parse(readFileSync(path.join(APP, 'fixtures/prototype', `${FACTS[key]}.json`), 'utf8')) as { card: CardFacts }).card;

const PLAIN = '?nodownload=1&test=1';
const PLAY = '?speed=quick&build=play&nodownload=1&test=1';
/** The page tests' kinds for the restore check: hidden before a replay, set not to stop you, one that still stops you. */
const RESTORE_KINDS: Partial<Record<VersionKey, [hide: string, loose: string, still: string]>> = {
  'bank-v2': ['plant', 'seat', 'table'], suite: ['plant', 'seat', 'table'], house: ['sanitary', 'sofa', 'other'],
};
/** The Build settings boxes the house page opened with (test_viewers.mjs replay). */
const HOUSE_BOXES = ['0.90', '3.90', '4.80', '3.50'];

async function open(page: Page, key: VersionKey, query: string): Promise<PageApi> {
  await noNetwork(page);
  const p = await pageApi(page);
  await p.goto(pageUrl(key, query));
  return p;
}
const problems = (p: PageApi) => p.logs.filter(l => (l.startsWith('[exception]') || l.startsWith('[console.error]')) && !/favicon/i.test(l));
const phase = (page: Page) => page.evaluate(() => window.__build!.phase);
const waitPhase = (page: Page, want: string, timeout = 40_000) => page.waitForFunction(w => window.__build!.phase === w, want, { timeout });
/** Sets a Build settings box as the prototype tests did (value, then a change event). */
const setBox = (page: Page, floor: string, prop: 'level' | 'height', value: string) => page.evaluate(([s, v]) => {
  const e = document.querySelector<HTMLInputElement>(s!)!;
  e.value = v!; e.dispatchEvent(new Event('change'));
  return e.value;
}, [sel.replayInput(floor, prop), value]);
const visibleSel = (page: Page, s: string) => page.evaluate(q => {
  const e = document.querySelector(q);
  return !!e && getComputedStyle(e).display !== 'none' && e.getBoundingClientRect().width > 0;
}, s);
const st = (page: Page) => page.evaluate(() => { const s = window.__viewer!.state; return { mode: s.mode, floor: s.floor.key, x: s.pos.x, y: s.pos.y, z: s.pos.z, locked: s.locked }; });
const cam = (page: Page) => page.evaluate(() => { const c = window.__viewer!.probe.camera(); return { x: c.x, y: c.y, z: c.z, dir: c.dir }; });
const boxesShown = (page: Page) => page.evaluate(() => {
  let n = 0;
  for (const f of Object.values(window.__host!.FL)) f.group.traverse(o => { if (o.name.startsWith('furn:') && o.visible) n++; });
  return n;
});

// ------------------------------------------------------------------ the Build settings card
for (const key of ['bank-v1', 'bank-v2', 'suite', 'house'] as VersionKey[]) {
  test.describe(`${key}: the Build settings card`, () => {
    test('opens on Build settings with the drawing\'s levels and heights, its facts, layers and steps; keys do nothing there; a cleared box keeps its value', async ({ page }) => {
      const f = card(key), ref = VERSIONS[key];
      const p = await open(page, key, PLAIN);
      expect(await phase(page)).toBe('settings');
      await expect(page.locator(sel.replayCard)).toBeVisible();
      expect(await visibleSel(page, sel.panel)).toBe(false);
      const boxes = await page.locator(`${sel.replayCard} input[type=number]`).evaluateAll(es => es.map(e => (e as HTMLInputElement).value));
      expect(boxes).toEqual(f.inputs.map(i => i.value));
      if (key === 'house') expect(boxes).toEqual(HOUSE_BOXES);
      await expect(page.locator(sel.replayFile)).toHaveText(f.introTitle);
      expect(await page.locator(`${sel.replayFacts} li`).allTextContents()).toEqual(f.facts);
      await expect(page.locator(sel.replayLayersTitle)).toHaveText(f.layersTitle);
      expect(await page.locator(`${sel.replayLayers} tr`).evaluateAll(rows => rows.map(r => [...r.children].map(c => c.textContent)))).toEqual(f.layers);
      expect(await page.locator(sel.replayStep()).allTextContents()).toEqual(f.stepList);
      // the steps and their captions at the default settings, character for character (DESIGN.md 7.4 oracle)
      const steps = await page.evaluate(() => window.__build!.steps.map(s => ({ key: s.key, title: s.title, caption: s.caption(window.__build!.state.settings) })));
      expect(steps).toEqual(f.steps.map(s => ({ key: s.key, title: s.title, caption: s.caption })));
      // the settings card counts the 38 layers in the house's plan areas (test_viewers.mjs fixes2)
      if (key === 'house') expect(await page.locator(sel.replayFacts).textContent()).toMatch(/on 38 layers/);
      // viewer keys do nothing on the settings screen
      await p.press('Digit2');
      expect((await st(page)).mode).toBe('orbit');
      // a cleared Level box keeps its old value
      const last = ref.floors[ref.floors.length - 1]!, old = f.inputs.find(i => i.floor === last && i.prop === 'level')!.value;
      expect(await setBox(page, last, 'level', '')).toBe(old);
      expect(await page.evaluate(k => window.__build!.state.settings[k]!.level, last)).toBe(Number(old));
      expect(problems(p)).toEqual([]);
    });
  });
}

// ------------------------------------------------------------------ play to the end
for (const key of ['bank-v2', 'suite', 'house'] as VersionKey[]) {
  timedDescribe(`${key}: Generate`, () => {
    test('plays with captions quoting the drawing, keys locked, the boxes last; ends in the normal viewer, unlocked, groups at home', async ({ page }) => {
      const ref = VERSIONS[key];
      const p = await open(page, key, PLAY);
      expect(await phase(page)).toBe('play');
      const caps = await page.evaluate(() => window.__build!.steps.map(s => s.caption(window.__build!.state.settings)));
      if (key === 'bank-v2') {
        // the replay captions quote this drawing: levels, doors, lintels, glass partitions (bank_test/test_bank.mjs)
        const nDoors = await page.evaluate(() => window.__host!.openings.filter(o => o.kind === 'door').length);
        expect(nDoors).toBe(39);
        expect(caps.some(c => c.includes(`${nDoors} doors`)) && caps.some(c => c.includes('rises to 3.70 m')) && caps.some(c => /lintels/.test(c))
          && caps.some(c => /glass partition/.test(c))).toBe(true);
      }
      await sleep(2500);
      const early = await page.evaluate(() => ({ T: window.__build!.state.T, phase: window.__build!.phase }));
      const earlyBoxes = ref.hasFurniture ? await boxesShown(page) : 0;
      const caption = await page.locator(sel.replayCaption).textContent();
      expect(await visibleSel(page, sel.replayCaption)).toBe(true);
      expect(caption).toMatch(/\d/);
      await p.press('Digit3');
      expect(await st(page)).toMatchObject({ mode: 'orbit', locked: true });
      expect(early.phase).toBe('play');
      expect(early.T).toBeGreaterThan(0.02);
      expect(early.T).toBeLessThan(0.85);
      expect(earlyBoxes).toBe(0);                          // none while the walls are still to rise
      await waitPhase(page, 'done');
      const handed = await page.evaluate(() => ({ locked: window.__viewer!.state.locked, mode: window.__viewer!.state.mode,
        groups: window.__host!.floors.map(f => [f.key, f.group.visible, ...f.group.position.toArray().map(v => Math.round(v * 1e6) / 1e6 + 0)]),
        visible: window.__viewer!.probe.visible() }));
      expect(handed).toEqual({ locked: false, mode: 'orbit', groups: ref.floors.map(k => [k, true, 0, 0, 0]), visible: ref.floors });
      expect(await visibleSel(page, sel.panel)).toBe(true);
      expect(await visibleSel(page, sel.replayCard)).toBe(false);
      expect(await visibleSel(page, sel.replayCaption)).toBe(false);
      if (ref.hasFurniture) {
        // the boxes are late objects: all of them at the end, opaque, and those that stop you (not in a doorway's approach) colliders
        const end = await page.evaluate(() => {
          const F = window.__host!.furniture!, FL = window.__host!.FL, ms = F.pieces().map(q => F.meshOf(q.id)!);
          const blocks = Object.fromEntries(F.kinds().map(k => [k.key, k.blocks]));
          const opaque = (m: { material: unknown }) => { const x = m.material as { opacity: number; transparent: boolean }; return x.opacity === 1 && !x.transparent; };
          return { n: ms.length, opaque: ms.every(m => opaque(m) && m.children.every(c => opaque(c as never))),
            colliders: Object.values(FL).reduce((n, f) => n + f.colliders.filter(m => m.name.startsWith('furn:')).length, 0),
            blocking: F.pieces().filter(q => blocks[q.kind] && !q.approach.length).length };
        });
        expect(await boxesShown(page)).toBe(end.n);
        expect(end.opaque).toBe(true);
        expect(end.colliders).toBe(end.blocking);
        if (key === 'house') {
          // ... and the last caption says so (cad_test/test_house_furniture.mjs)
          const kinds = await page.evaluate(() => window.__host!.furniture!.kinds().length);
          const last = await page.evaluate(() => window.__build!.steps.find(s => s.key === 'finish')!.caption(window.__build!.state.settings));
          expect(last).toContain(`and last the furniture: ${end.n} coloured boxes, one per piece, ${kinds} kinds`);
        }
      }
      expect(problems(p)).toEqual([]);
    });
  });
}

// ------------------------------------------------------------------ the whole flow (test_viewers.mjs replay section)
for (const key of ['house', 'bank-v2'] as VersionKey[]) {
  timedDescribe(`${key}: Build settings, replay again, Esc, Skip`, () => {
    test('the upper level set before Generate is the one walked; Replay plays again; Esc skips; Build settings reopen with the changed values; Skip on the card', async ({ page }) => {
      const ref = VERSIONS[key], upper = ref.floors[ref.floors.length - 1]!;
      const p = await open(page, key, PLAIN);
      expect(await setBox(page, upper, 'level', '5.00')).toBe('5.00');
      expect(await setBox(page, upper, 'height', '3.00')).toBe('3.00');
      await p.clickEl(sel.replaySpeed('quick'));
      await p.clickEl(sel.replayGo);
      expect(await phase(page)).toBe('play');
      expect(await visibleSel(page, sel.replayCaption)).toBe(true);
      await sleep(2500);
      const mid = await page.evaluate(() => ({ T: window.__build!.state.T, caption: document.querySelector('[data-wt=replay-caption], #br-sub')!.textContent ?? '' }));
      expect(mid.T).toBeGreaterThan(0.05);
      expect(mid.T).toBeLessThan(1);
      expect(mid.caption).toMatch(/\d/);
      await p.press('Digit3');
      expect((await st(page)).mode).toBe('orbit');
      await waitPhase(page, 'done');
      expect(await page.evaluate(() => window.__viewer!.probe.visible())).toEqual(ref.floors);
      await p.press('Digit2'); await p.press('PageUp');
      const s = await st(page);
      expect(s.floor).toBe(upper);
      expect(Math.abs(s.y - 6.6)).toBeLessThan(0.01);
      expect(await page.evaluate(() => window.__viewer!.probe.onFloor())).toBe(true);
      await p.press('Escape');
      await p.clickEl(sel.replayAgain); await sleep(600);
      expect(await phase(page)).toBe('play');
      await p.press('Escape'); await sleep(300);
      expect(await phase(page)).toBe('done');
      expect(await visibleSel(page, sel.panel)).toBe(true);
      await p.clickEl(sel.replayOpen); await sleep(300);
      expect(await phase(page)).toBe('settings');
      expect(await page.locator(sel.replayInput(upper, 'level')).inputValue()).toBe('5.00');
      await p.clickEl(sel.replaySkipSettings); await sleep(300);
      expect(await phase(page)).toBe('done');
      expect(problems(p)).toEqual([]);
    });
  });
}

// ------------------------------------------------------------------ the camera (test_viewers.mjs fixes2)
timedDescribe('house: the camera', () => {
  test('after a replay you are back at the view you left', async ({ page }) => {
    const p = await open(page, 'house', '?nodownload=1&build=0&test=1');
    await page.mouse.move(900, 450); await page.mouse.down();
    for (let i = 1; i <= 10; i++) await page.mouse.move(900 + i * 15, 450);
    await page.mouse.up();
    let before = await cam(page);                           // wait until the drag's glide has died away
    for (let i = 0; i < 60; i++) { await sleep(300); const c = await cam(page); const d = Math.hypot(c.x - before.x, c.y - before.y, c.z - before.z); before = c; if (d < 0.002) break; }
    await p.clickEl(sel.replayAgain); await sleep(600);
    await p.press('Escape'); await sleep(1500);
    const after = await cam(page);
    expect(Math.hypot(after.x - before.x, after.y - before.y, after.z - before.z)).toBeLessThan(0.1);
    expect(problems(p)).toEqual([]);
  });
});

for (const key of ['house', 'bank-v2', 'suite'] as VersionKey[]) {
  test.describe(`${key}: seek`, () => {
    test('all seven steps are ticked at seek(1); while the floors line up the camera tilts without turning', async ({ page }) => {
      const p = await open(page, key, PLAIN);
      await page.evaluate(() => window.__build!.seek(1)); await sleep(300);
      await expect(page.locator(sel.replayStep('done'))).toHaveCount(7);
      const az: number[] = [];
      for (const T of [0.32, 0.35, 0.38]) {
        await page.evaluate(t => window.__build!.seek(t), T); await sleep(250);
        const c = await cam(page);
        az.push(Math.atan2(c.dir[0], c.dir[2]) * 180 / Math.PI);
      }
      const turn = (a: number, b: number) => Math.abs(((a - b + 540) % 360) - 180);
      expect(turn(az[1]!, az[0]!)).toBeLessThan(2);
      expect(turn(az[2]!, az[1]!)).toBeLessThan(2);
      await page.evaluate(() => window.__build!.skip());
      expect(problems(p)).toEqual([]);
    });
  });
}

test.describe('house: ?cam=1', () => {
  test('?cam=1 opens the Camera panel after the build screen, not over it', async ({ page }) => {
    const p = await open(page, 'house', '?cam=1&nodownload=1&test=1');
    const during = await visibleSel(page, sel.cameraPanel);
    await p.clickEl(sel.replaySkipSettings); await sleep(400);
    expect(during).toBe(false);
    expect(await visibleSel(page, sel.cameraPanel)).toBe(true);
    expect(problems(p)).toEqual([]);
  });
});

test.describe('house: the ground plane', () => {
  test('is hidden on the settings screen and while the walls rise, fades in during the last step, opaque after', async ({ page }) => {
    const p = await open(page, 'house', PLAIN);
    const look = (T: number | 'skip' | 'none') => page.evaluate(t => {
      if (t === 'skip') window.__build!.skip(); else if (t !== 'none') window.__build!.seek(t);
      const scene = window.__host!.floors[0]!.group.parent!;
      const g = scene.children.find(o => {
        const geo = (o as { geometry?: { type?: string; parameters?: { width?: number; height?: number } } }).geometry;
        return geo?.type === 'PlaneGeometry' && geo.parameters?.width === 80 && geo.parameters?.height === 50;
      }) as unknown as { visible: boolean; material: { opacity: number; transparent: boolean } } | undefined;
      return g ? { visible: g.visible, opacity: g.material.opacity, transparent: g.material.transparent } : null;
    }, T);
    const fin = await page.evaluate(() => { const s = window.__build!.steps.find(x => x.key === 'finish')!; return [s.t0, s.t1] as const; });
    expect((await look('none'))?.visible).toBe(false);
    expect((await look(0.7))?.visible).toBe(false);
    const half = (await look((fin[0] + fin[1]) / 2))!;
    expect(half.visible && half.transparent).toBe(true);
    expect(half.opacity).toBeGreaterThan(0.2);
    expect(half.opacity).toBeLessThan(0.8);
    expect(await look('skip')).toEqual({ visible: true, opacity: 1, transparent: false });
    expect(problems(p)).toEqual([]);
  });
});

// ------------------------------------------------------------------ the furniture after a replay (the page tests' restore hook)
// bank_test/test_bank.mjs, presidential_test/test_presidential.mjs, cad_test/test_house_furniture.mjs: a kind hidden before
// a replay is hidden again after it (the replay shows every late object at its end), a kind set not to stop you stays so,
// another kind still stops you; and the doorways rule holds after a replay: the boxes in an approach that would stop you
// (the suite's curtains never do) are no colliders with the tick on, colliders with it off.
for (const key of ['bank-v2', 'suite', 'house'] as VersionKey[]) {
  test.describe(`${key}: furniture and the replay`, () => {
    test('replaying the build puts back what you had (a hidden kind, a kind that does not stop you); the doorways rule still holds', async ({ page }) => {
      const [hide, loose, still] = RESTORE_KINDS[key]!;
      const p = await open(page, key, '?nodownload=1&build=0&test=1');
      const rep = await page.evaluate(([hideKind, looseKind]) => {
        const F = window.__host!.furniture!, FL = window.__host!.FL, out: Record<string, unknown> = {};
        const ms = F.pieces().map(q => F.meshOf(q.id)!);
        const kindOf = (m: { name: string }) => m.name.split(':')[1];              // furn:<kind>:<id>
        F.setVisible(hideKind, false); F.setBlocks(looseKind, false);
        window.__build!.seek(0); out.start = ms.filter(m => m.visible).length;
        window.__build!.seek(1); out.end = ms.filter(m => m.visible).length; out.n = ms.length;
        window.__build!.skip(); out.phase = window.__build!.phase;
        const k = Object.fromEntries(F.kinds().map(x => [x.key, x]));
        out.wrong = F.pieces().filter(q => F.meshOf(q.id)!.visible !== k[q.kind]!.visible).length;
        out.cols = [...new Set(Object.values(FL).flatMap(f => f.colliders.filter(m => m.name.startsWith('furn:')).map(kindOf)))];
        out.opaque = ms.every(m => { const x = m.material as unknown as { opacity: number; transparent: boolean }; return x.opacity === 1 && !x.transparent; });
        F.setVisible(hideKind, true); F.setBlocks(looseKind, true);
        const inApproach = F.pieces().filter(q => q.approach.length && q.blocks), plain = F.pieces().filter(q => !q.approach.length && q.blocks);
        const inCol = (q: { floor: string; id: string }) => FL[q.floor]!.colliders.includes(F.meshOf(q.id)!);
        window.__build!.seek(0); window.__build!.seek(1); window.__build!.skip();
        out.on = inApproach.map(inCol); out.plainIn = plain.every(inCol);
        F.setKeepDoorways(false); window.__build!.seek(0); window.__build!.seek(1); window.__build!.skip();
        out.off = inApproach.map(inCol); out.nApproach = inApproach.length;
        F.setKeepDoorways(true);
        return out;
      }, [hide, loose] as const);
      expect(rep.start).toBe(0);
      expect(rep.end).toBe(rep.n);
      expect(rep.phase).toBe('done');
      expect(rep.wrong).toBe(0);
      expect(rep.opaque).toBe(true);
      const cols = rep.cols as string[];
      expect([cols.includes(hide), cols.includes(loose), cols.includes(still)]).toEqual([false, false, true]);
      expect(rep.nApproach).toBeGreaterThan(0);
      expect((rep.on as boolean[]).every(x => !x)).toBe(true);
      expect(rep.plainIn).toBe(true);
      expect((rep.off as boolean[]).every(Boolean)).toBe(true);
      expect(problems(p)).toEqual([]);
    });
  });
}

// ------------------------------------------------------------------ no replay data, no replay (the hotel: stages.json absent)
test.describe('hotel: no build replay', () => {
  test('opens on the finished model: no Build card, no Build row, no __build', async ({ page }) => {
    const p = await open(page, 'hotel', PLAIN);
    expect(await page.evaluate(() => window.__build ?? null)).toBeNull();
    expect(await page.locator(sel.replayCard).count()).toBe(0);
    expect(await page.locator(sel.replayAgain).count()).toBe(0);
    expect(await visibleSel(page, sel.panel)).toBe(true);
    expect(problems(p)).toEqual([]);
  });
});
