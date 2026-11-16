// Builder C's harness spec (Playwright project `harness`; DESIGN.md 17.4; WORK_BREAKDOWN C "Tests alone"):
//   WT_WEB_PORT=5723 WT_TMP="$TEMP/wt-c" npx playwright test -c tests/e2e/playwright.config.ts --project=harness packages/viewer/test/harness/furniture
// (`--project=harness` with the `=`: Playwright reads `--project harness <path>` as two project names.)
// On furniture.html (the shared test context with C's real root, panel and furniture, real WebGL in headless Edge):
// typing with real keys (select on focus, 640 not 40, Enter / Escape / leave, junk, the range), Reset, the typed heights
// kept under the stamped key, the colliders and the doorways rule, the hover label, the CSV download; the side panel at
// 1366 x 768 / 1920 x 1080 and its bottom edge above the hint line from 640 to 1080 px; and the computed styles with and
// without a host page reset like Tailwind's (the root's all: revert).
import { expect, test, type Page } from '@playwright/test';
import type { FurnHarness } from './furniture-page';

type KindRow = { key: string; height: number; defaultHeight: number; visible: boolean; blocks: boolean };
const sleep = (ms: number) => new Promise(r => setTimeout(r, ms));
const rowSel = (k: string, part: string) => `[data-wt=furniture-row][data-kind="${k}"] [data-wt=${part}]`;

async function open(page: Page, query = 'model=mini') {
  const errors: string[] = [];
  page.on('pageerror', e => errors.push(String(e)));
  await page.goto(`/furniture/furniture.html?${query}`);
  await page.waitForFunction(() => window.__furn !== undefined);
  const err = await page.evaluate(() => (window.__furn && 'error' in window.__furn ? window.__furn.error : null));
  expect(err).toBeNull();
  await page.waitForFunction(() => (window.__furn as FurnHarness).frames > 1);
  return errors;
}
const kinds = (page: Page) => page.evaluate(() => (window.__furn as FurnHarness).F!.kinds() as KindRow[]);
const heightOf = async (page: Page, k: string) => (await kinds(page)).find(x => x.key === k)!.height;
const boxText = (page: Page, k: string) => page.locator(rowSel(k, 'kind-height')).inputValue();
const flagOf = (page: Page, k: string, f: 'edited' | 'bad') => page.locator(rowSel(k, 'kind-height')).evaluate((e, a) => e.hasAttribute(`data-${a}`), f);
const focusBox = (page: Page, k: string) => page.evaluate(s => {
  const e = document.querySelector<HTMLInputElement>(s)!; e.scrollIntoView({ block: 'center' }); e.focus(); e.select(); return document.activeElement === e;
}, rowSel(k, 'kind-height'));
const blur = (page: Page) => page.evaluate(() => { (document.activeElement as HTMLElement | null)?.blur(); });
const reset = (page: Page) => page.evaluate(() => (window.__furn as FurnHarness).F!.reset());
const pieces = (page: Page) => page.evaluate(() => (window.__furn as FurnHarness).F!.pieces().map(p => ({ id: p.id, kind: p.kind, floor: p.floor, z0: p.z0, z1: p.z1, blocking: p.blocking, approach: p.approach })));

test.describe('typing a height with real keys (mini model)', () => {
  test.beforeEach(async ({ page }) => { await open(page); await page.evaluate(() => localStorage.clear()); });

  test('a click into a height box selects the number: typing 480 over 600 gives 480', async ({ page }) => {
    await page.locator(rowSel('plant', 'kind-height')).click();
    await sleep(150);
    const sel = await page.evaluate(() => { const e = document.activeElement as HTMLInputElement; return { wt: e.getAttribute('data-wt'), from: e.selectionStart, to: e.selectionEnd, len: e.value.length }; });
    await page.keyboard.type('480');
    expect(sel).toEqual({ wt: 'kind-height', from: 0, to: 3, len: 3 });
    expect(await boxText(page, 'plant')).toBe('480');
    expect(await heightOf(page, 'plant')).toBe(480);
  });

  test('6 changes nothing and is marked; 60 applies as typed; 600 moves the table tops and what stands on them, on both floors; Enter keeps it', async ({ page }) => {
    expect(await focusBox(page, 'table')).toBe(true);
    await page.keyboard.type('6');
    expect([await heightOf(page, 'table'), await flagOf(page, 'table', 'bad')]).toEqual([750, true]);
    await page.keyboard.type('0');
    expect(await heightOf(page, 'table')).toBe(60);
    await page.keyboard.type('0');
    const z = Object.fromEntries((await pieces(page)).map(p => [p.id, [p.z0, p.z1]]));
    expect(z['L1-table-001']).toEqual([0, 0.6]);
    expect(z['L2-table-001']).toEqual([0, 0.6]);
    expect(z['L1-computer-001']![0]).toBe(0.6);
    expect(z['L1-printer-001']![0]).toBe(0.6);
    expect(z['L2-computer-001']![0]).toBe(0.6);
    const ys = await page.evaluate(() => { const F = (window.__furn as FurnHarness).F!; return [F.meshOf('L1-table-001')!.scale.y, F.meshOf('L1-computer-001')!.position.y]; });
    expect(ys[0]).toBeCloseTo(0.6, 6);
    expect(ys[1]).toBeCloseTo(0.6, 6);
    expect([await boxText(page, 'table'), await flagOf(page, 'table', 'edited'), await flagOf(page, 'table', 'bad')]).toEqual(['600', true, false]);
    await focusBox(page, 'table');
    await page.keyboard.type('700');
    await page.keyboard.press('Enter');
    expect(await heightOf(page, 'table')).toBe(700);
    expect(await page.evaluate(() => document.activeElement?.getAttribute('data-wt') ?? null)).not.toBe('kind-height');
  });

  test('junk is marked while typed and never kept: 9999 passes through 999, abc, 4,5 and nothing go back to the height from before', async ({ page }) => {
    await page.evaluate(() => (window.__furn as FurnHarness).F!.setHeight('table', 700));
    const out: { text: string; marked: boolean; during: number; after: string; height: number }[] = [];
    for (const text of ['9999', 'abc', '4,5', '']) {
      await focusBox(page, 'table');
      if (text) await page.keyboard.type(text); else await page.keyboard.press('Backspace');
      const marked = await flagOf(page, 'table', 'bad'), during = await heightOf(page, 'table');
      await blur(page); await sleep(60);
      out.push({ text, marked, during, after: await boxText(page, 'table'), height: await heightOf(page, 'table') });
    }
    expect(out.map(o => [o.after, o.height])).toEqual([['700', 700], ['700', 700], ['700', 700], ['700', 700]]);
    expect(out.map(o => o.marked)).toEqual([true, true, true, false]);
    expect(out.map(o => o.during)).toEqual([999, 700, 700, 700]);
  });

  test('Escape cancels the edit and leaves the box; the range is 10 - 5000', async ({ page }) => {
    await focusBox(page, 'plant');
    await page.keyboard.type('123');
    expect(await heightOf(page, 'plant')).toBe(123);
    await page.keyboard.press('Escape');
    expect([await boxText(page, 'plant'), await heightOf(page, 'plant')]).toEqual(['600', 600]);
    expect(await page.evaluate(() => document.activeElement?.getAttribute('data-wt') ?? null)).not.toBe('kind-height');
    const tryValue = async (v: string) => { await focusBox(page, 'plant'); await page.keyboard.type(v); await blur(page); return heightOf(page, 'plant'); };
    expect(await tryValue('5000')).toBe(5000);
    expect(await tryValue('5001')).toBe(5000);
    expect(await tryValue('10')).toBe(10);
    expect(await page.evaluate(() => { const F = (window.__furn as FurnHarness).F!; return [F.setHeight('plant', 9), F.setHeight('nothing', 500), F.setHeight('plant', 'abc'), F.setHeight('plant', 600)]; }))
      .toEqual([false, false, false, true]);
  });

  test('640, not 40: the first key right after the focus is not lost (no gap, twice; the page busy 400 ms; after it; 100 ms later)', async ({ page }) => {
    const raceTry = async (busyMs: number, gapMs: number) => {
      await reset(page);
      await page.evaluate(({ s, busyMs }) => {
        const e = document.querySelector<HTMLInputElement>(s)!; e.scrollIntoView({ block: 'center' });
        if (busyMs) setTimeout(() => { const t = Date.now(); while (Date.now() - t < busyMs); }, 0);     // a long task queued ahead of the module's timer
        e.focus(); e.select();
      }, { s: rowSel('table', 'kind-height'), busyMs });
      if (gapMs) await sleep(gapMs);
      await page.keyboard.type('640'); await page.keyboard.press('Enter'); await sleep(200);
      return { height: await heightOf(page, 'table'), text: await boxText(page, 'table') };
    };
    const race = { gap0: await raceTry(0, 0), gap0b: await raceTry(0, 0), busy: await raceTry(400, 0), busyWait: await raceTry(400, 600), gap100: await raceTry(0, 100) };
    for (const r of Object.values(race)) expect(r).toEqual({ height: 640, text: '640' });
  });

  test('Reset heights (a real click) brings every kind, box and text back, clears the marks and the stored heights; the doorways tick stays', async ({ page }) => {
    await page.evaluate(() => { const F = (window.__furn as FurnHarness).F!; F.setHeight('seat', 500); F.setHeight('table', 600); F.setKeepDoorways(false); });
    await page.locator('[data-wt=furniture-reset]').click();
    const ks = await kinds(page);
    expect(ks.every(k => k.height === k.defaultHeight)).toBe(true);
    expect(await page.locator('[data-wt=kind-height][data-edited]').count()).toBe(0);
    const stamp = await page.evaluate(() => (window.__furn as FurnHarness).stamp);
    expect(await page.evaluate(k => localStorage.getItem(k), `walkthrough-furniture-heights:Fixture:${stamp}`)).toBe('{"keepDoorways":false}');
    expect(await page.evaluate(() => (window.__furn as FurnHarness).F!.keepDoorways())).toBe(false);
  });
});

test.describe('kept per browser, under the stamped key (mini model)', () => {
  test('typed heights and the doorways tick survive a reload in local mode; host mode keeps only the tick', async ({ page }) => {
    await open(page);
    await page.evaluate(() => localStorage.clear());
    await focusBox(page, 'table'); await page.keyboard.type('600'); await blur(page);
    await focusBox(page, 'coffee-table'); await page.keyboard.type('420'); await blur(page);
    await page.locator('[data-wt=furniture-keep]').click();
    const stamp = await page.evaluate(() => (window.__furn as FurnHarness).stamp);
    const key = `walkthrough-furniture-heights:Fixture:${stamp}`;
    expect(await page.evaluate(() => Object.keys(localStorage))).toEqual([key]);
    expect(await page.evaluate(k => localStorage.getItem(k), key)).toBe('{"table":600,"coffee-table":420,"keepDoorways":false}');
    await open(page);
    expect(await boxText(page, 'table')).toBe('600');
    expect(await boxText(page, 'coffee-table')).toBe('420');
    expect(await page.locator('[data-wt=furniture-keep]').isChecked()).toBe(false);
    expect((await pieces(page)).find(p => p.id === 'L1-computer-001')!.z0).toBe(0.6);
    await open(page, 'model=mini&mode=host');
    expect(await boxText(page, 'table')).toBe('750');
    expect(await page.locator('[data-wt=furniture-keep]').isChecked()).toBe(false);
    await focusBox(page, 'table'); await page.keyboard.type('640'); await blur(page);
    await page.locator('[data-wt=furniture-keep]').click();
    expect(await page.evaluate(k => localStorage.getItem(k), key)).toBeNull();
    await page.evaluate(() => localStorage.clear());
  });
});

test.describe('Walk colliders and the doorways rule (mini and bank v2)', () => {
  test('mini: the colliders hold the boxes that stop you; a real click on Keep doorways clear adds the 2 in an approach; knee rays agree', async ({ page }) => {
    await open(page);
    const state = () => page.evaluate(() => {
      const h = window.__furn as FurnHarness, c = h.ctx;
      const col = Object.fromEntries(c.floors.map(f => [f.key, f.colliders.filter(m => m.name.startsWith('furn:')).map(m => String(m.userData.id)).sort()]));
      const p = h.F!.pieces().find(q => q.id === 'L1-seat-002')!;
      const hit = c.readouts.rayHit('L1', p.x, p.y - 1.2, 0.35, 0, 1, 2);
      return { col, seat2: hit ? hit.name : null, keep: h.F!.keepDoorways(), ticked: document.querySelector<HTMLInputElement>('[data-wt=furniture-keep]')!.checked };
    });
    const on = await state();
    expect(on.keep && on.ticked).toBe(true);
    expect(on.col.L1).not.toContain('L1-seat-002');
    expect(on.col.L2).not.toContain('L2-seat-001');
    expect(on.col.L1).not.toContain('L1-curtain-001');
    expect(on.col.L1).toContain('L1-seat-001');
    expect(on.seat2).not.toBe('furn:seat:L1-seat-002');
    await page.locator('[data-wt=furniture-keep]').click();
    const off = await state();
    expect(off.keep || off.ticked).toBe(false);
    expect(off.col.L1).toContain('L1-seat-002');
    expect(off.col.L2).toContain('L2-seat-001');
    expect(off.seat2).toBe('furn:seat:L1-seat-002');
    await page.locator('[data-wt=furniture-keep]').click();
    expect(await state()).toEqual(on);
    // show off: out of the colliders and not drawn; stops off: drawn, out of the colliders (real clicks)
    await page.locator(rowSel('seat', 'kind-show')).click();
    expect(await page.evaluate(() => { const h = window.__furn as FurnHarness; return [h.F!.meshOf('L1-seat-001')!.visible, h.ctx.floors[0]!.colliders.includes(h.F!.meshOf('L1-seat-001')!)]; })).toEqual([false, false]);
    await page.locator(rowSel('seat', 'kind-show')).click();
    await page.locator(rowSel('seat', 'kind-stops')).click();
    expect(await page.evaluate(() => { const h = window.__furn as FurnHarness; return [h.F!.meshOf('L1-seat-001')!.visible, h.ctx.floors[0]!.colliders.includes(h.F!.meshOf('L1-seat-001')!)]; })).toEqual([true, false]);
    await page.locator(rowSel('seat', 'kind-stops')).click();
  });

  test('bank v2: with the tick on every piece with an approach is out of the colliders and every other piece of a blocking kind is in; off: all in', async ({ page }) => {
    await open(page, 'model=bank-v2');
    const rule = await page.evaluate(() => {
      const h = window.__furn as FurnHarness, F = h.F!, M = h.ctx.model, kb = Object.fromEntries(M.furnitureKinds!.map(k => [k.key, k.blocks]));
      const inCol = () => new Set(h.ctx.floors.flatMap(f => f.colliders.filter(m => m.name.startsWith('furn:')).map(m => String(m.userData.id))));
      const state = (keep: boolean) => { F.setKeepDoorways(keep); const c = inCol(); return M.furniture!.filter(p => kb[p.kind]).map(p => [p.id, c.has(p.id), p.approach.length > 0]); };
      return { on: state(true), off: state(false), n: M.furniture!.length };
    });
    expect(rule.on.length).toBe(185);
    expect(rule.on.filter(([, inCol, flagged]) => inCol === flagged)).toEqual([]);
    expect(rule.off.filter(([, inCol]) => !inCol)).toEqual([]);
    expect(rule.on.filter(([, , flagged]) => flagged).length).toBe(13);
  });
});

test.describe('the hover label (mini model)', () => {
  test('Orbit: kind, family, size and floor at the pointer; the doorway line; none over the sky or while dragging; inside the root', async ({ page }) => {
    await open(page);
    // from above, level 2 alone, then level 1 alone (the floor buttons' floor mode)
    const at = (id: string, along = 0) => page.evaluate(({ id, along }) => {
      const h = window.__furn as FurnHarness, c = h.ctx;
      h.viewFromAbove();
      const p = h.F!.pieces().find(q => q.id === id)!, r = p.rot * Math.PI / 180, fl = c.floorByKey.get(p.floor)!;
      return h.screenAt(p.x + along * Math.cos(r), fl.modelLevel + p.z1, -(p.y + along * Math.sin(r)));
    }, { id, along });
    const tip = () => page.evaluate(() => { const t = document.querySelector<HTMLElement>('[data-wt=furniture-tip]')!; return t.style.display === 'block' ? t.innerText : null; });
    const hover = async (x: number, y: number, shown = true) => {
      await page.mouse.move(1300, 60);
      for (let i = 0; i < 20 && (await tip()) !== null; i++) await sleep(100);
      await page.mouse.move(x, y);
      await sleep(250);
      let t = await tip();
      for (let i = 0; shown && t === null && i < 25; i++) { await sleep(100); t = await tip(); }
      return t;
    };
    const floorBtn = (k: string) => page.locator(`[data-wt=floors] [data-floor="${k}"]`).click();
    await floorBtn('L2');
    const table = await hover(...await at('L2-table-001', -0.55));
    expect(table).toContain('Table / desk');
    expect(table).toContain('IA_J15_WORKING TABLE - 1400W 1000D 750H');
    expect(table).toContain('1.40 × 1.00 × 0.75 m');
    expect(table).toContain('Level 2');
    const comp = await hover(...await at('L2-computer-001'));
    expect(comp).toContain('Computer / monitor');
    expect(comp).toContain('0.74 × 0.43 × 0.45 m, from 0.75 m');
    const inside = await page.evaluate(() => {
      const t = document.querySelector<HTMLElement>('[data-wt=furniture-tip]')!, r = t.getBoundingClientRect(), b = document.querySelector('[data-wt=root]')!.getBoundingClientRect();
      return t.parentElement!.getAttribute('data-wt') === 'root' && getComputedStyle(t).position === 'absolute' && r.left >= b.left && r.right <= b.right && r.top >= b.top && r.bottom <= b.bottom;
    });
    expect(inside).toBe(true);
    await floorBtn('L1');
    const seat2 = await hover(...await at('L1-seat-002'));
    expect(seat2).toContain('Chair / stool');
    expect(seat2).toContain('does not stop you: in the approach of L1-001, L1-002');
    const seat1 = await hover(...await at('L1-seat-001'));
    expect(seat1).toContain('Chair / stool');
    expect(seat1).not.toContain('does not stop you');
    expect(await hover(1250, 30, false)).toBeNull();
    // dragging: no label (the label code leaves OrbitControls alone)
    const [x, y] = await at('L1-table-001');
    await page.mouse.move(x, y); await page.mouse.down();
    for (const d of [10, 30, 60]) { await page.mouse.move(x + d, y + d / 2); await sleep(60); }
    expect(await tip()).toBeNull();
    await page.mouse.up();
  });
});

test.describe('the family list download (mini model)', () => {
  test('Save list (CSV) downloads Fixture_furniture_list.csv: EF BB BF in front of exactly csv(), typed heights included; nodownload: nothing', async ({ page }) => {
    await open(page);
    await focusBox(page, 'table'); await page.keyboard.type('640'); await blur(page);
    await page.locator('[data-wt=furniture-save]').click();
    const dl = await page.evaluate(async () => {
      const h = window.__furn as FurnHarness, d = h.downloads[0];
      if (!d) return null;
      const bytes = new Uint8Array(await d.blob.arrayBuffer());
      return { n: h.downloads.length, name: d.fileName, type: d.blob.type, head: [...bytes.slice(0, 3)], text: new TextDecoder('utf-8', { ignoreBOM: true }).decode(bytes), csv: h.F!.csv() };
    });
    expect(dl).not.toBeNull();
    expect(dl!.n).toBe(1);
    expect(dl!.name).toBe('Fixture_furniture_list.csv');
    expect(dl!.type).toMatch(/text\/csv;charset=utf-8/i);
    expect(dl!.head).toEqual([0xef, 0xbb, 0xbf]);
    expect(dl!.text).toBe('﻿' + dl!.csv);
    expect(dl!.csv).toContain(',640,');
    await page.evaluate(() => localStorage.clear());
    await open(page, 'model=mini&nodownload=1');
    await page.locator('[data-wt=furniture-save]').click();
    expect(await page.evaluate(() => (window.__furn as FurnHarness).downloads.length)).toBe(0);
  });
});

test.describe('the side panel on a PC screen', () => {
  for (const model of ['bank-v2', 'suite', 'house', 'hotel']) {
    test(`${model}: at 1366 x 768 and 1920 x 1080 the panel is on screen, scrolls or fits, title and Reset / Save reachable, rows and type readable, above the hint`, async ({ page }) => {
      await open(page, `model=${model}`);
      for (const [w, h] of [[1366, 768], [1920, 1080]] as const) {
        await page.setViewportSize({ width: w, height: h });
        await sleep(400);
        const m = await page.evaluate(() => {
          const p = document.querySelector<HTMLElement>('[data-wt=panel]')!, r = p.getBoundingClientRect(), cs = getComputedStyle(p);
          const rows = [...document.querySelectorAll<HTMLElement>('[data-wt=furniture-row]')], lab = [...document.querySelectorAll<HTMLElement>('[data-wt=kind-label]')];
          const inP = (e: Element) => { const b = e.getBoundingClientRect(), q = p.getBoundingClientRect(); return b.top >= q.top - 0.5 && b.bottom <= q.bottom + 0.5 && b.left >= q.left - 0.5 && b.right <= q.right + 0.5; };
          const out: Record<string, unknown> = { onScreen: r.top >= 0 && r.left >= 0 && r.bottom <= innerHeight && r.right <= innerWidth,
            scrolls: p.scrollHeight > p.clientHeight + 1, overflowY: cs.overflowY, content: p.scrollHeight, shown: p.clientHeight,
            hintGap: Math.round((document.querySelector('[data-wt=hint]')!.getBoundingClientRect().top - r.bottom) * 10) / 10 };
          p.scrollTop = 0; out.titleVisible = inP(p.querySelector('[data-wt=heading]')!);
          p.scrollTop = p.scrollHeight; out.lastRowReachable = inP(rows[rows.length - 1]!) && inP(document.querySelector('[data-wt=furniture-save]')!) && inP(document.querySelector('[data-wt=furniture-reset]')!);
          p.querySelector('[data-wt=furniture]')!.scrollIntoView({ block: 'start' });
          out.cut = lab.filter(e => { const t = document.createRange(); t.selectNodeContents(e); return t.getBoundingClientRect().width > e.getBoundingClientRect().width + 0.01; }).map(e => e.textContent);
          out.rowH = Math.round(Math.min(...rows.map(e => e.getBoundingClientRect().height)));
          out.fontPx = Math.min(...lab.map(e => parseFloat(getComputedStyle(e).fontSize)));
          out.boxesIn = rows.every(e => inP(e.querySelector('[data-wt=kind-height]')!) && inP(e.querySelector('[data-wt=kind-stops]')!) && inP(e.querySelector('[data-wt=kind-show]')!));
          p.scrollTop = 0;
          return out;
        });
        test.info().annotations.push({ type: `${model} ${w}x${h}`, description: JSON.stringify(m) });
        expect(m.onScreen).toBe(true);
        expect(!m.scrolls || /auto|scroll/.test(String(m.overflowY))).toBe(true);
        expect(m.titleVisible).toBe(true);
        expect(m.lastRowReachable).toBe(true);
        expect(m.cut).toEqual([]);
        expect(m.rowH as number).toBeGreaterThanOrEqual(22);
        expect(m.fontPx as number).toBeGreaterThanOrEqual(12);
        expect(m.boxesIn).toBe(true);
        expect(m.hintGap as number).toBeGreaterThanOrEqual(4);
      }
      const gaps: [string, number][] = [];
      for (const [w, h] of [[1366, 640], [1366, 700], [1280, 800], [1600, 900], [1920, 1080]] as const) {
        await page.setViewportSize({ width: w, height: h });
        await sleep(300);
        gaps.push([`${w}x${h}`, await page.evaluate(() => {
          const r = document.querySelector('[data-wt=panel]')!.getBoundingClientRect();
          return Math.round((document.querySelector('[data-wt=hint]')!.getBoundingClientRect().top - r.bottom) * 10) / 10;
        })]);
      }
      test.info().annotations.push({ type: `${model} hint gaps`, description: JSON.stringify(gaps) });
      expect(gaps.filter(([, g]) => g < 4)).toEqual([]);
    });
  }
});

test.describe('the root: a size container, the error box, the flags (BASE_CSS in a real browser)', () => {
  test('container wtv / size; error box hidden until reported; replay / crowded hide the panel; fp / camopen only in a root at most 700 px wide or 500 px high', async ({ page }) => {
    await page.setViewportSize({ width: 1400, height: 880 });
    await open(page, 'model=bank-v2');
    const look = () => page.evaluate(() => {
      const d = (s: string) => getComputedStyle(document.querySelector(s)!).display;
      return { panel: d('[data-wt=panel]'), hint: d('[data-wt=hint]'), error: d('[data-wt=error]') };
    });
    const flag = (f: 'fp' | 'camopen' | 'crowded' | 'touchui' | 'replay', on: boolean) => page.evaluate(({ f, on }) => (window.__furn as FurnHarness).ctx.ui.setFlag(f, on), { f, on });
    const root = await page.evaluate(() => { const cs = getComputedStyle(document.querySelector('[data-wt=root]')!); return { type: cs.containerType, name: cs.containerName, position: cs.position, overflow: cs.overflow }; });
    expect(root).toEqual({ type: 'size', name: 'wtv', position: 'relative', overflow: 'hidden' });
    expect(await look()).toEqual({ panel: 'block', hint: 'block', error: 'none' });
    await page.evaluate(() => (window.__furn as FurnHarness).ctx.reportError(new Error('a test error')));
    const err = await page.evaluate(() => { const e = document.querySelector<HTMLElement>('[data-wt=error]')!, cs = getComputedStyle(e); return { display: cs.display, position: cs.position, text: e.textContent, inRoot: e.parentElement!.getAttribute('data-wt') }; });
    expect(err).toEqual({ display: 'block', position: 'absolute', text: 'Viewer error: a test error', inRoot: 'root' });
    for (const f of ['replay', 'crowded'] as const) {
      await flag(f, true);
      expect((await look()).panel, f).toBe('none');
      if (f === 'replay') expect((await look()).hint).toBe('none');
      await flag(f, false);
    }
    await flag('fp', true); await flag('camopen', true);
    expect(await look()).toMatchObject({ panel: 'block', hint: 'block' });          // a PC-sized root: the panel stays
    for (const [w, h] of [[690, 880], [1400, 490]] as const) {
      await page.setViewportSize({ width: w, height: h });
      await sleep(300);
      expect(await look(), `${w} x ${h}, fp`).toMatchObject({ panel: 'none', hint: 'none' });
      await flag('fp', false);
      expect((await look()).panel, `${w} x ${h}, camopen`).toBe('none');
      expect((await look()).hint).toBe('block');
      await flag('fp', true);
    }
    await flag('fp', false); await flag('camopen', false);
    expect(await look()).toMatchObject({ panel: 'block', hint: 'block' });
  });
});

test.describe('the same look in any host page (all: revert)', () => {
  for (const reset of ['', 'tailwind']) {
    test(`at 1400 px${reset ? ', under a Tailwind-like reset' : ''}: panel 360 px wide (content-box), heading bold, a tick keeps the default checkbox margin`, async ({ page }) => {
      await page.setViewportSize({ width: 1400, height: 880 });
      await open(page, `model=bank-v2${reset ? '&reset=' + reset : ''}`);
      const s = await page.evaluate(() => {
        const p = document.querySelector<HTMLElement>('[data-wt=panel]')!, h1 = document.querySelector('[data-wt=heading]')!, tick = document.querySelector('input[data-wt=toggle]')!;
        const cs = getComputedStyle(tick), ps = getComputedStyle(p), btn = document.querySelector('[data-wt=floors] [data-floor="all"]')!;
        return { width: p.offsetWidth, boxSizing: ps.boxSizing, weight: getComputedStyle(h1).fontWeight, h1Size: getComputedStyle(h1).fontSize,
          margin: [cs.marginTop, cs.marginRight, cs.marginBottom, cs.marginLeft].join(' '), pressedBg: getComputedStyle(btn).backgroundColor,
          sheets: document.adoptedStyleSheets.length, styles: document.querySelectorAll('[data-wt=root] style').length };
      });
      test.info().annotations.push({ type: 'computed', description: JSON.stringify(s) });
      expect(s.width).toBe(360);
      expect(s.boxSizing).toBe('content-box');
      expect(s.weight).toBe('700');
      expect(s.h1Size).toBe('15px');
      expect(s.margin).toBe('3px 3px 3px 4px');
      expect(s.pressedBg).toBe('rgb(47, 111, 143)');
      expect(s.sheets).toBe(1);
      expect(s.styles).toBe(0);
    });
  }
});

// ---------------------------------------------------------------------------------------------------------------------
// Step BX (docs/boxes/DESIGN.md 2.2 - 2.6, 8.2): deleting a furniture box, real WebGL, real mouse and keys (?edit=1).
// This page has no modes and no replay: Walk, the crosshair and the replay are the browser spec's (tests/e2e).
// ---------------------------------------------------------------------------------------------------------------------
test.describe('deleting a furniture box (?edit=1)', () => {
  const at = (page: Page, id: string, along = 0) => page.evaluate(({ id, along }) => {
    const h = window.__furn as FurnHarness, c = h.ctx;
    h.viewFromAbove();
    const p = h.F!.pieces().find(q => q.id === id)!, r = p.rot * Math.PI / 180, fl = c.floorByKey.get(p.floor)!;
    return h.screenAt(p.x + along * Math.cos(r), fl.modelLevel + p.z1, -(p.y + along * Math.sin(r)));
  }, { id, along });
  /** What the page shows of one box: the marker, the card, the mesh, the collider, a knee-height ray through its place, its pixel. */
  const look = (page: Page, id: string, px: [number, number]) => page.evaluate(async ({ id, px }) => {
    const h = window.__furn as FurnHarness, c = h.ctx, F = h.F!;
    const frames = h.frames;
    await new Promise<void>(done => { const tick = () => (h.frames > frames + 1 ? done() : requestAnimationFrame(tick)); tick(); });
    const p = F.pieces().find(q => q.id === id)!, mesh = F.meshOf(id)!, fl = c.floorByKey.get(p.floor)!;
    const marker = c.scene.getObjectByName('furniture-selection');
    const card = document.querySelector<HTMLElement>('[data-wt=box-card]');
    const hit = c.readouts.rayHit(p.floor, p.x, p.y - 1.5, 0.35, 0, 1, 3);
    // the pixel the box is drawn at (the drawing buffer is kept: preserveDrawingBuffer)
    const cv = c.canvas, r = cv.getBoundingClientRect(), copy = document.createElement('canvas');
    copy.width = cv.width; copy.height = cv.height;
    const g = copy.getContext('2d')!;
    g.drawImage(cv, 0, 0);
    const d = g.getImageData(Math.round((px[0] - r.left) * cv.width / r.width), Math.round((px[1] - r.top) * cv.height / r.height), 1, 1).data;
    return {
      marker: !!marker && marker.visible, markerInScene: !!marker && marker.parent === c.scene,
      card: card && getComputedStyle(card).display !== 'none' ? card.innerText : null,
      visible: mesh.visible, collider: fl.colliders.includes(mesh), late: fl.late.includes(mesh), ray: hit ? hit.name : null,
      pixel: [d[0]!, d[1]!, d[2]!], removed: p.removed === true, edits: Object.keys(F.pieceEdits()),
      line: document.querySelector<HTMLElement>('[data-wt=furniture-removed]')?.innerText ?? null,
    };
  }, { id, px });
  const far = (a: number[], b: number[]) => Math.abs(a[0]! - b[0]!) + Math.abs(a[1]! - b[1]!) + Math.abs(a[2]! - b[2]!);

  test('mini: a real click selects a box (marker, card at the top right); Delete: not drawn, no collider, a knee ray passes its place; Undo brings it back', async ({ page }) => {
    await page.setViewportSize({ width: 1366, height: 768 });
    const errors = await open(page, 'model=mini&edit=1');
    await page.locator('[data-wt=floors] [data-floor="L2"]').click();
    const T = 'L2-table-001', px = await at(page, T, -0.55);
    await page.mouse.move(1300, 700);
    const before = await look(page, T, px);
    expect(before).toMatchObject({ marker: false, markerInScene: true, card: null, visible: true, collider: true, late: true, ray: `furn:table:${T}`, removed: false, line: null });
    // the hover label says a click selects, and the cursor is the pointer
    await page.mouse.move(...px);
    await expect(page.locator('[data-wt=furniture-tip-hint]')).toHaveText('Click to select');
    expect(await page.evaluate(() => (window.__furn as FurnHarness).ctx.canvas.style.cursor)).toBe('pointer');
    await page.mouse.click(...px);
    const sel = await look(page, T, px);
    expect(sel.marker).toBe(true);
    expect(sel.card).toContain('Table / desk');
    expect(sel.card).toContain('IA_J15_WORKING TABLE - 1400W 1000D 750H');
    expect(sel.card).toContain('1.40 × 1.00 × 0.75 m · Level 2');
    expect(sel.card).toContain(T);
    expect(sel.card).toContain('1 piece stands on it (Computer / monitor): it is deleted with it.');
    expect(sel.card).toContain('Delete box (Del)');
    expect(far(sel.pixel, before.pixel)).toBeGreaterThan(40);                         // the magenta marker is drawn over the box
    expect(await page.locator('[data-wt=furniture-tip]').evaluate(e => getComputedStyle(e).display)).toBe('none');   // no label under a card
    // the card: at the top right of the root, above the side panel's layer, never over the box
    const cardBox = await page.evaluate(() => {
      const c = document.querySelector<HTMLElement>('[data-wt=box-card]')!, r = c.getBoundingClientRect(), b = document.querySelector('[data-wt=root]')!.getBoundingClientRect();
      const mid = document.elementFromPoint(r.left + r.width / 2, r.top + 10);
      return { top: Math.round(r.top - b.top), right: Math.round(b.right - r.right), width: Math.round(r.width), z: getComputedStyle(c).zIndex, onTop: !!mid && c.contains(mid) };
    });
    expect(cardBox).toEqual({ top: 12, right: 12, width: 280, z: '7', onTop: true });
    // a drag (orbiting) keeps the selection
    await page.mouse.move(700, 600); await page.mouse.down(); await page.mouse.move(730, 600, { steps: 3 }); await page.mouse.move(700, 600, { steps: 3 }); await page.mouse.up();
    expect((await look(page, T, px)).marker).toBe(true);
    await page.mouse.click(...await at(page, T, -0.55));
    await page.keyboard.press('Delete');
    const gone = await look(page, T, px);
    expect(gone).toMatchObject({ marker: false, visible: false, collider: false, late: false, removed: true, edits: ['L2-computer-001', T] });
    expect(gone.ray).not.toBe(`furn:table:${T}`);                                      // the walker can step into the place
    expect(gone.card).toContain('Deleted: Table / desk (+1 on it)');
    expect(gone.card).toContain('Undo');
    expect(gone.line).toContain('2 boxes deleted');
    expect(far(gone.pixel, before.pixel)).toBeGreaterThan(40);                        // the box is not drawn any more
    expect(far(gone.pixel, sel.pixel)).toBeGreaterThan(40);
    expect(await page.locator(rowSel('table', 'kind-label')).innerText()).toBe('Table / desk (2)');
    // Ctrl+Z brings it back, selected; Delete again; then the card's Undo (a real click)
    await page.keyboard.press('Control+z');
    expect(await look(page, T, px)).toMatchObject({ marker: true, visible: true, collider: true, late: true, ray: `furn:table:${T}`, removed: false, edits: [], line: null });
    await page.keyboard.press('Delete');
    expect((await look(page, T, px)).edits).toEqual(['L2-computer-001', T]);
    await page.locator('[data-wt=box-undo]').click();
    const back = await look(page, T, px);
    expect(back).toMatchObject({ marker: true, visible: true, collider: true, ray: `furn:table:${T}`, edits: [] });
    await page.keyboard.press('Escape');
    await page.mouse.move(1300, 700);
    const end = await look(page, T, px);
    expect(end).toMatchObject({ marker: false, card: null });
    expect(far(end.pixel, before.pixel)).toBeLessThan(12);                            // drawn as before
    // a height typed and kept with Enter, then Delete: the armed key belongs to the canvas, not to the panel
    await page.mouse.click(...await at(page, T, -0.55));
    await page.locator(rowSel('seat', 'kind-height')).click();
    await page.keyboard.type('500');
    await page.keyboard.press('Enter');
    await page.keyboard.press('Delete');
    expect((await look(page, T, px)).edits).toEqual([]);
    expect(errors).toEqual([]);
  });

  test('bank v2: the Restore list near the bottom: above the hint line, at most half the root, Restore all is itself under the pointer; Restore all and its Undo', async ({ page }) => {
    await page.setViewportSize({ width: 1366, height: 768 });
    const errors = await open(page, 'model=bank-v2&edit=1');
    const n = await page.evaluate(() => {
      const F = (window.__furn as FurnHarness).F!;
      for (const p of F.pieces().filter((_, i) => i % 3 === 0)) F.removePiece(p.id);
      return Object.keys(F.pieceEdits()).length;
    });
    expect(n).toBeGreaterThan(60);
    const opener = page.locator('[data-wt=boxes-restore-open]');
    await opener.scrollIntoViewIfNeeded();
    await expect(page.locator('[data-wt=furniture-removed]')).toContainText(`${n} boxes deleted`);
    await opener.click();
    const m = await page.evaluate(() => {
      const root = document.querySelector('[data-wt=root]')!.getBoundingClientRect();
      const pop = document.querySelector<HTMLElement>('[data-wt=boxes-restore]')!, r = pop.getBoundingClientRect();
      const hint = document.querySelector('[data-wt=hint]')!.getBoundingClientRect(), panel = document.querySelector('[data-wt=panel]')!.getBoundingClientRect();
      const list = pop.querySelector<HTMLElement>('[data-wt=boxes-restore-list]')!;
      const all = pop.querySelector<HTMLElement>('[data-wt=boxes-restore-all]')!, a = all.getBoundingClientRect();
      const x = pop.querySelector<HTMLElement>('[data-wt=boxes-restore-close]')!, xr = x.getBoundingClientRect();
      const first = pop.querySelector<HTMLElement>('[data-wt=box-restore]')!, fr = first.getBoundingClientRect();
      return {
        parent: pop.parentElement!.getAttribute('data-wt'), z: getComputedStyle(pop).zIndex,
        aboveHint: hint.top - r.bottom, half: r.height <= root.height / 2 + 0.5, inRoot: r.top >= root.top && r.right <= root.right,
        besidePanel: r.left - panel.right, scrolls: list.scrollHeight > list.clientHeight + 1,
        rows: pop.querySelectorAll('[data-wt=boxes-restore-row]').length,
        allCentre: document.elementFromPoint(a.left + a.width / 2, a.top + a.height / 2) === all,
        allLowQuarter: document.elementFromPoint(a.left + a.width / 2, a.top + a.height * 0.875) === all,
        closeItself: document.elementFromPoint(xr.left + xr.width / 2, xr.top + xr.height / 2) === x,
        restoreItself: document.elementFromPoint(fr.left + fr.width / 2, fr.top + fr.height / 2) === first,
        allLeft: a.left - r.left < r.width / 2, closeRight: r.right - xr.right < r.width / 4, closeTop: xr.top - r.top < 40,
      };
    });
    test.info().annotations.push({ type: 'restore list', description: JSON.stringify(m) });
    expect(m).toMatchObject({ parent: 'root', z: '7', half: true, inRoot: true, scrolls: true, allCentre: true, allLowQuarter: true, closeItself: true,
      restoreItself: true, allLeft: true, closeRight: true, closeTop: true });
    expect(m.aboveHint).toBeGreaterThanOrEqual(4);
    expect(m.besidePanel).toBeGreaterThanOrEqual(4);
    expect(m.rows).toBeGreaterThan(40);
    expect(m.rows).toBeLessThanOrEqual(n);
    // one Restore (a real click), then Restore all, then its Undo
    await page.locator('[data-wt=box-restore]').first().click();
    const left = await page.evaluate(() => Object.keys((window.__furn as FurnHarness).F!.pieceEdits()).length);
    expect(left).toBeLessThan(n);
    await page.locator('[data-wt=boxes-restore-all]').click();
    expect(await page.evaluate(() => Object.keys((window.__furn as FurnHarness).F!.pieceEdits()).length)).toBe(0);
    await expect(page.locator('[data-wt=boxes-restore]')).toBeHidden();
    await expect(page.locator('[data-wt=furniture-removed]')).toContainText(`All ${left} boxes are back`);
    await page.locator('[data-wt=boxes-restore-undo]').click();
    expect(await page.evaluate(() => Object.keys((window.__furn as FurnHarness).F!.pieceEdits()).length)).toBe(left);
    await expect(page.locator('[data-wt=furniture-removed]')).toContainText(`${left} boxes deleted`);
    expect(errors).toEqual([]);
  });

  for (const model of ['bank-v2', 'suite', 'house', 'hotel']) {
    test(`${model}: at 1366 x 768 the panel still fits with the edit hint and the line of the deleted boxes (on screen, everything reachable, above the hint)`, async ({ page }) => {
      await page.setViewportSize({ width: 1366, height: 768 });
      await open(page, `model=${model}&edit=1`);
      await page.evaluate(() => { const F = (window.__furn as FurnHarness).F!; F.removePiece(F.pieces()[0]!.id); F.removePiece(F.pieces().at(-1)!.id); });
      await sleep(300);
      const m = await page.evaluate(() => {
        const p = document.querySelector<HTMLElement>('[data-wt=panel]')!, r = p.getBoundingClientRect(), cs = getComputedStyle(p);
        const inP = (e: Element) => { const b = e.getBoundingClientRect(), q = p.getBoundingClientRect(); return b.height > 0 && b.top >= q.top - 0.5 && b.bottom <= q.bottom + 0.5 && b.left >= q.left - 0.5 && b.right <= q.right + 0.5; };
        const one = (wt: string) => document.querySelector<HTMLElement>(`[data-wt=${wt}]`)!;
        const out: Record<string, unknown> = { onScreen: r.top >= 0 && r.left >= 0 && r.bottom <= innerHeight && r.right <= innerWidth,
          scrolls: p.scrollHeight > p.clientHeight + 1, overflowY: cs.overflowY, wide: p.scrollWidth > p.clientWidth + 1,
          hintGap: Math.round((one('hint').getBoundingClientRect().top - r.bottom) * 10) / 10 };
        p.scrollTop = 0; out.titleVisible = inP(one('heading'));
        p.scrollTop = p.scrollHeight;
        out.endReachable = inP(one('furniture-removed')) && inP(one('boxes-restore-open')) && inP(one('furniture-save')) && inP(one('furniture-reset'));
        one('furniture').scrollIntoView({ block: 'start' });
        out.hintReachable = inP(one('furniture-edit-hint'));
        const cut = (e: HTMLElement) => { const t = document.createRange(); t.selectNodeContents(e); return t.getBoundingClientRect().width > e.getBoundingClientRect().width + 0.5; };
        out.cut = [...document.querySelectorAll<HTMLElement>('[data-wt=kind-label]')].filter(cut).map(e => e.textContent);
        out.lineText = one('furniture-removed').innerText;
        p.scrollTop = 0;
        return out;
      });
      test.info().annotations.push({ type: `${model} 1366x768 edit`, description: JSON.stringify(m) });
      expect(m).toMatchObject({ onScreen: true, wide: false, titleVisible: true, endReachable: true, hintReachable: true, cut: [] });
      expect(!m.scrolls || /auto|scroll/.test(String(m.overflowY))).toBe(true);
      expect(m.hintGap as number).toBeGreaterThanOrEqual(4);
      expect(m.lineText).toContain('deleted');
    });
  }
});
