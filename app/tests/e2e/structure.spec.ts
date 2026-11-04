// Builder A (DESIGN.md 17.4 "structure"): what the viewer builds, measured in headless Edge, ported from the prototype
// tests (bank_test/test_bank.mjs, hotel_test/test_hotel.mjs, presidential_test/test_presidential.mjs,
// cad_test/test_house_openings.mjs, the house sections of viewer-modes/test_viewers.mjs). The checks run on both targets
// (lib/target.ts): the offline files (E2E_TARGET=app) and the prototype pages (E2E_TARGET=prototype, with their selectors
// and the shim). As on the prototypes, the walls, doors and glass are judged with every furniture kind hidden (the boxes are
// colliders; furniture.spec.ts walks them). House ray hits are classified by mesh CLASS (lib/target.ts meshIs), never by a
// literal mesh name: the v1 grouping names the house's meshes differently from its page (DESIGN.md 17.2).
// Behaviour this design changes on purpose is tagged @app-only (the suite's labels not overlapping: the declutter is new).
// The untrusted-text check (room, family and layer names with <img onerror> and </script>) is in offline.spec.ts: it needs
// a store of its own and the built template.
//   E2E_TARGET=prototype WT_SERVE= WT_WEB_PORT=5721 WT_TMP="$TEMP/wt-a" npx playwright test -c tests/e2e/playwright.config.ts --project=e2e tests/e2e/structure.spec.ts
// App target against offline files outside dist/offline (builder A's own run on a hand-made store): WT_OFFLINE_DIR=<folder
// of <projectId>-v<n>.html> and WT_DATA_DIR=<its store> (defaults: dist/offline and data).
import { createHash } from 'node:crypto';
import { existsSync, readFileSync } from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { expect, test, type Page } from '@playwright/test';
import { pageApi, sleep, type PageApi } from './lib/page';
import {
  APP, APP_ONLY, isApp, meshIs, noNetwork, pageUrl, plates, PROTOTYPES, sel, VERSIONS, waitReady, type VersionKey,
} from './lib/target';
import { doorWalks, glassWalks, installPageHelpers, judgeHouseWalk, walkThrough, wallWalks } from './lib/walks';

/* eslint-disable @typescript-eslint/no-explicit-any */

const OFFLINE_DIR = process.env.WT_OFFLINE_DIR ?? null;
const DATA_DIR = process.env.WT_DATA_DIR ?? path.join(APP, 'data');

/** The page of a version on this target (the app target may be pointed at another folder of offline files). */
function urlOf(key: VersionKey, query: string): string {
  if (isApp && OFFLINE_DIR) return pathToFileURL(path.join(OFFLINE_DIR, `${VERSIONS[key].projectId}-v${VERSIONS[key].version}.html`)).href + query;
  return pageUrl(key, query);
}

interface Opened { p: PageApi; requests: string[] }
/** Opens a version (?build=0&nodownload=1&test=1 unless given), no network on the app target, and waits until it is ready. */
async function open(page: Page, key: VersionKey, query = '?build=0&nodownload=1&test=1'): Promise<Opened> {
  const p = await pageApi(page);
  const net = await noNetwork(page);
  await page.goto(urlOf(key, query));
  await waitReady(page);
  return { p, requests: net.requests };
}

const problems = (p: PageApi) => p.logs.filter(l => (l.startsWith('[exception]') || l.startsWith('[console.error]')) && !/favicon/i.test(l));

/** The live state of the modes (the prototype's st()). */
const st = (page: Page) => page.evaluate(() => {
  const s = (window as any).__viewer.state;
  return { mode: s.mode as string, floor: s.floor.key as string, level: s.floor.level as number, x: s.pos.x as number, y: s.pos.y as number, z: s.pos.z as number };
});
const visibleFloors = (page: Page) => page.evaluate(() => (window as any).__viewer.probe.visible() as string[]);
/** The room labels shown now: [text, left, top, right, bottom] (the prototypes' boxesOf). */
const shownLabels = (page: Page) => page.evaluate(room => [...document.querySelectorAll(room)]
  .filter(e => (e as HTMLElement).style.display === 'block')
  .map(e => { const r = e.getBoundingClientRect(); return [e.textContent ?? '', r.left, r.top, r.right, r.bottom] as [string, number, number, number, number]; }), sel.room);
function overlaps(bs: [string, number, number, number, number][]): [string, string][] {
  const o: [string, string][] = [];
  for (let i = 0; i < bs.length; i++) for (let j = i + 1; j < bs.length; j++) {
    const a = bs[i]!, b = bs[j]!;
    if (a[1] < b[3] - 0.5 && b[1] < a[3] - 0.5 && a[2] < b[4] - 0.5 && b[2] < a[4] - 0.5) o.push([a[0], b[0]]);
  }
  return o;
}
/** Every furniture kind shown or hidden (the structure is judged without the boxes, as the prototype tests did). */
const setFurniture = (page: Page, on: boolean) => page.evaluate(show => {
  const F = (window as any).__host.furniture;
  if (F) for (const k of F.kinds()) F.setVisible(k.key, show);
}, on);
/** Walk on a floor (goToFloor does nothing in Orbit). */
const walkOn = (page: Page, key: string) => page.evaluate(k => {
  const v = (window as any).__viewer;
  if (v.mode !== 'walk') v.setMode('walk');
  v.goToFloor(k);
  return v.state.floor.key as string;
}, key);
const clickSel = async (page: Page, selector: string) => {
  await page.locator(selector).first().scrollIntoViewIfNeeded();
  await page.locator(selector).first().click();
  await sleep(150);
};

// ===================================================================================================== loading, stamp
const ALL: VersionKey[] = ['bank-v1', 'bank-v2', 'hotel', 'suite', 'house'];
const MAX_SCRIPT: Partial<Record<VersionKey, string>> = {
  'bank-v1': 'bank_test/previous_before_fix_round_2026-10-27/Bangkok_Bank_Sampeng.ms', 'bank-v2': 'bank_test/Bangkok_Bank_Sampeng.ms',
  suite: 'presidential_test/Presidential_Suite.ms', hotel: 'hotel_test/Hotel_Lobby.ms',
};
const msStamp = (file: string) => /\(model data ([0-9a-f]{12})\)/.exec(readFileSync(file, 'utf8').split(/\r?\n/)[1] ?? '')?.[1] ?? null;

for (const key of ALL) {
  test(`${key}: loads without errors${isApp ? ' and without network' : ''}; the stamp meta is the version's and its 3ds Max script's`, async ({ page }) => {
    const { p, requests } = await open(page, key);
    const facts = await page.evaluate(meta => ({
      meta: document.querySelector(meta)?.getAttribute('content') ?? null,
      error: (() => { const e = document.querySelector('[data-wt=error], #vm-err') as HTMLElement | null; return !!e && getComputedStyle(e).display !== 'none' && !e.hidden; })(),
      canvas: document.querySelectorAll('canvas').length,
      floors: ((window as any).__host.floors as { key: string }[]).map(f => f.key),
      payloadStamp: (() => { const d = document.getElementById('wtv-data'); try { return d ? JSON.parse(d.textContent ?? '').version.stamp as string : null; } catch { return null; } })(),
      payloadMax: (() => { const d = document.getElementById('wtv-data'); try { return d ? JSON.parse(d.textContent ?? '').version.downloads.maxScript as string | null : null; } catch { return null; } })(),
    }), sel.stampMeta);
    expect(facts.canvas).toBe(1);
    expect(facts.error).toBe(false);
    expect(facts.floors).toEqual(VERSIONS[key].floors);
    if (isApp) {
      expect(requests).toEqual([]);
      expect(facts.meta).toBe(facts.payloadStamp);
      if (VERSIONS[key].stamp) expect(facts.meta).toBe(VERSIONS[key].stamp);
      const ms = facts.payloadMax ? path.join(DATA_DIR, 'projects', VERSIONS[key].projectId, 'versions', String(VERSIONS[key].version), 'downloads', facts.payloadMax) : null;
      if (ms && existsSync(ms)) expect(msStamp(ms)).toBe(facts.meta);
      else test.info().annotations.push({ type: 'max script', description: ms ? `${ms} is not in the store` : 'this version has no 3ds Max script' });
    } else {
      expect(facts.meta).toBe(VERSIONS[key].stamp);                         // the house page carries none (no Max script)
      const ms = MAX_SCRIPT[key];
      if (ms) expect(msStamp(path.join(PROTOTYPES, ms))).toBe(facts.meta);
    }
    await sleep(300);
    expect(problems(p)).toEqual([]);
  });
}

// ======================================================================================================= camera start
const FIXED: Partial<Record<VersionKey, { position: number[]; target: number[]; far: number }>> = {
  'bank-v1': { position: [24, 27, 29], target: [0, 2.5, 0], far: 600 }, 'bank-v2': { position: [24, 27, 29], target: [0, 2.5, 0], far: 600 },
  suite: { position: [-26, 32, 30], target: [0, 1.2, 0], far: 600 }, house: { position: [-28, 30, 34], target: [0, 3, 0], far: 500 },
};
for (const key of ALL) {
  test(`${key}: the camera starts as its page did (${FIXED[key] ? 'a fixed view' : 'aimed at the middle of the floor plates, panned by half the side panel'})`, async ({ page }) => {
    await open(page, key);
    await sleep(300);
    const cam = await page.evaluate(sels => {
      const h = (window as any).__host, root = document.querySelector(sels.root) as HTMLElement;
      const box = root === document.body ? { left: 0, top: 0, width: innerWidth, height: innerHeight } : root.getBoundingClientRect();
      const panel = (document.querySelector(sels.panel) as HTMLElement).getBoundingClientRect();
      // the bank v1 page (no furniture) has no __host.camera / controls: its probe has the position (as the facts capture did)
      const probe = (window as any).__viewer.probe.camera();
      return { position: (h.camera ? h.camera.position.toArray() : [probe.x, probe.y, probe.z]) as number[],
        target: (h.controls ? h.controls.target.toArray() : null) as number[] | null, far: (h.camera ? h.camera.far : null) as number | null,
        near: (h.camera ? h.camera.near : null) as number | null,
        W: box.width, H: box.height, panelRight: panel.right - box.left,
        slabs: (h.model ? h.model.parts.filter((p: any) => p.kind === 'slab').flatMap((p: any) => p.o) : []) as number[][] };
    }, { root: sel.root, panel: sel.panel });
    const near = (a: number[] | null, b: number[], tol: number) => !!a && a.every((v, i) => Math.abs(v - b[i]!) < tol);
    if (cam.target === null) test.info().annotations.push({ type: 'camera', description: 'this page exposes no camera or controls: the position only' });
    else expect(cam.near).toBe(0.1);
    const fixed = FIXED[key];
    if (fixed) {
      expect(near(cam.position, fixed.position, 1e-6), JSON.stringify(cam)).toBe(true);
      if (cam.target !== null) {
        expect(near(cam.target, fixed.target, 1e-6), JSON.stringify(cam)).toBe(true);
        expect(cam.far).toBe(fixed.far);
      }
      return;
    }
    // the hotel page's rule (hotel_test/src/make_html.py rule 5), with the window's height and the side panel's right edge,
    // and the camera's starting fov of 40 degrees (the modes then set the Orbit lens)
    expect(cam.far).toBe(600);
    const xs = cam.slabs.map(q => q[0]!), ys = cam.slabs.map(q => q[1]!);
    const away = [24 * 0.9, 24.5 * 0.9, 29 * 0.9], L = Math.hypot(...away), rl = Math.hypot(away[2]!, away[0]!), right = [away[2]! / rl, 0, -away[0]! / rl];
    const mpp = 2 * L * Math.tan(40 * Math.PI / 360) / cam.H, pr = Math.min(cam.panelRight, cam.W / 2);
    const target = [(Math.min(...xs) + Math.max(...xs)) / 2 - right[0]! * pr / 2 * mpp, 2.5, -(Math.min(...ys) + Math.max(...ys)) / 2 - right[2]! * pr / 2 * mpp];
    expect(near(cam.target, target, 1e-3), JSON.stringify({ target: cam.target, want: target, W: cam.W, H: cam.H, pr })).toBe(true);
    expect(near(cam.position, target.map((v, i) => v + away[i]!), 1e-3), JSON.stringify(cam.position)).toBe(true);
  });
}

// =================================================================================================== room names, floors
const ROOMS: { key: VersionKey; top: string; least: number }[] = [
  { key: 'bank-v1', top: 'L2', least: 8 }, { key: 'bank-v2', top: 'L2', least: 8 }, { key: 'hotel', top: 'F2', least: 10 },
];
for (const { key, top, least } of ROOMS) {
  test(`${key}: room names are shown over the top floor (${top}), none on top of another`, async ({ page }) => {
    await open(page, key);
    await sleep(700);
    const shown = await shownLabels(page);
    const r = await page.evaluate(t => {
      const labels = (window as any).__host.labels as { el: HTMLElement; floor: string }[];
      return { onTop: labels.filter(l => l.floor === t).length, shownFloors: [...new Set(labels.filter(l => l.el.style.display === 'block').map(l => l.floor))] };
    }, top);
    expect(shown.length, JSON.stringify(shown.map(b => b[0]))).toBeGreaterThanOrEqual(Math.min(least, r.onTop));
    expect(r.shownFloors).toEqual([top]);
    expect(overlaps(shown)).toEqual([]);
  });
}

test('suite: room names from the drawing are shown over the model', async ({ page }) => {
  await open(page, 'suite');
  await sleep(700);
  const shown = await shownLabels(page);
  const n = await page.evaluate(() => (window as any).__host.labels.length as number);
  expect(shown.length).toBeGreaterThanOrEqual(Math.min(10, n));
});

test(`suite: room names do not overlap (the declutter is new for the suite, DESIGN.md 18.12) ${APP_ONLY}`, async ({ page }) => {
  await open(page, 'suite');
  await sleep(700);
  expect(overlaps(await shownLabels(page))).toEqual([]);
});

const FLOOR_BUTTONS: { key: VersionKey; least?: number }[] = [{ key: 'bank-v1', least: 5 }, { key: 'bank-v2', least: 5 }, { key: 'hotel', least: 7 }, { key: 'house' }];
for (const { key, least } of FLOOR_BUTTONS) {
  test(`${key}: the floor buttons show / hide floors in Orbit and change the floor in Walk; PgUp / PgDn; Both -> the first floor`, async ({ page }) => {
    const { p } = await open(page, key);
    const [f1, f2] = VERSIONS[key].floors as [string, string];
    const levels = await page.evaluate(() => Object.fromEntries(((window as any).__host.floors as { key: string; level: number }[]).map(f => [f.key, f.level])));
    await clickSel(page, sel.floorButton(f1)); await sleep(400);
    const v1 = await visibleFloors(page);
    const shown1 = await shownLabels(page);
    const n1 = await page.evaluate(k => ((window as any).__host.labels ?? []).filter((l: any) => l.floor === k).length as number, f1);
    await clickSel(page, sel.floorButton(f2)); await sleep(300);
    const v2 = await visibleFloors(page);
    await clickSel(page, sel.floorButton('all')); await sleep(300);
    const vb = await visibleFloors(page);
    expect([v1, v2, vb]).toEqual([[f1], [f2], [f1, f2]]);
    expect(await page.locator(sel.floorButton('all')).evaluate((e, app) => (app ? e.getAttribute('aria-pressed') === 'true' : e.classList.contains('on')), isApp)).toBe(true);
    if (least !== undefined) {
      expect(shown1.length, 'room names with the first floor alone').toBeGreaterThanOrEqual(Math.min(least, n1));
      expect(overlaps(shown1)).toEqual([]);
    }

    await p.press('Digit2');
    const s0 = await st(page);
    const room = await page.evaluate(() => ({ clearance: Math.min(99, (window as any).__viewer.probe.clearance()) as number, onFloor: (window as any).__viewer.probe.onFloor() as boolean }));
    expect({ mode: s0.mode, floor: s0.floor }).toEqual({ mode: 'walk', floor: f1 });
    expect(Math.abs(s0.y - (levels[f1]! + 1.6))).toBeLessThan(0.01);
    expect(room.onFloor).toBe(true);
    expect(room.clearance).toBeGreaterThanOrEqual(0.5);
    await clickSel(page, sel.floorButton(f2));
    const s2 = await st(page);
    expect(s2.floor).toBe(f2);
    expect(Math.abs(s2.y - (levels[f2]! + 1.6))).toBeLessThan(0.01);
    expect(await page.evaluate(() => (window as any).__viewer.probe.onFloor())).toBe(true);
    expect(await page.locator(sel.floorButton(f2)).evaluate((e, app) => (app ? e.getAttribute('aria-pressed') === 'true' : e.classList.contains('on')), isApp)).toBe(true);
    await page.locator(sel.floorButton(f2)).blur();
    await p.press('PageDown'); const sd = await st(page);
    await p.press('PageUp'); const su = await st(page);
    await clickSel(page, sel.floorButton('all')); const sb = await st(page);
    expect([sd.floor, su.floor, sb.floor]).toEqual([f1, f2, f1]);
    expect(problems(p)).toEqual([]);
  });
}

// ========================================================================================== walls, doors, passages, heads
const WALLS: { key: VersionKey; seed: number; maxTries: number }[] = [
  { key: 'bank-v1', seed: 7, maxTries: 8000 }, { key: 'bank-v2', seed: 7, maxTries: 8000 }, { key: 'hotel', seed: 7, maxTries: 8000 },
  { key: 'suite', seed: 3, maxTries: 6000 }, { key: 'house', seed: 7, maxTries: 8000 },
];
for (const { key, seed, maxTries } of WALLS) {
  test(`${key}: walls stop you at 40 random spots per floor, never through, never inside`, async ({ page }) => {
    test.setTimeout(300_000);
    await open(page, key);
    await setFurniture(page, false);
    for (const f of VERSIONS[key].floors) {
      expect(await walkOn(page, f)).toBe(f);
      const walls = await wallWalks(page, { seed, maxTries });
      expect(walls, f).toMatchObject({ floor: f, wentThrough: 0, endedInsideWall: 0 });
      expect(walls.tried, f).toBeGreaterThanOrEqual(30);
    }
  });
}

/** Every door (and passage) of every floor walked through its middle, both ways (lib/walks.ts doorWalks). */
async function allDoorWalks(page: Page, key: VersionKey, backs?: number[]) {
  const all = [];
  for (const f of VERSIONS[key].floors) {
    expect(await walkOn(page, f)).toBe(f);
    all.push(...await doorWalks(page, backs ? { backs } : {}));
  }
  return all;
}

for (const key of ['bank-v1', 'bank-v2'] as VersionKey[]) {
  test(`${key}: every door can be walked through its middle both ways (exterior ones from inside); passages are left as they are`, async ({ page }) => {
    test.setTimeout(300_000);
    await open(page, key);
    await setFurniture(page, false);
    const all = await allDoorWalks(page, key);
    const doors = all.filter(d => d.kind === 'door');
    expect(doors.length).toBeGreaterThan(0);
    expect(doors.filter(d => !d.ok)).toEqual([]);
    const pw = all.filter(d => d.kind === 'passage');
    test.info().annotations.push({ type: 'passages walked (information)', description: `${pw.filter(d => d.ok).length} of ${pw.length} cross` });
    // passages: at 1/4, 1/2, 3/4 nothing overhead below 3 m, no glass across in the wall band, no part named after them
    const passages = await page.evaluate(() => {
      const h = (window as any).__host, out: any[] = [];
      for (const d of h.openings) {
        if (d.kind !== 'passage') continue;
        const ux = d.ny, uy = -d.nx, r: any = { id: d.id, up: [], glass: [] };
        for (const k of [0.25, 0.5, 0.75]) {
          const x = d.x + ux * (k - 0.5) * d.width, y = d.y + uy * (k - 0.5) * d.width;
          const up = h.upHit(d.floor, x, y, 1.0);
          if (up !== null && up < 3) r.up.push(Math.round(up * 100) / 100);
          for (const ht of [0.35, 1.2]) {
            const hit = h.rayHit(d.floor, x - d.nx * 0.6, y - d.ny * 0.6, ht, d.nx, d.ny, 1.2);
            if (hit && Math.abs(hit.d - 0.6) <= d.wallThickness / 2 + 0.05 && /glass/.test(hit.name)) r.glass.push(hit.name);
          }
        }
        r.parts = h.model.parts.filter((p: any) => p.label && p.label.split(' ')[0] === d.id).map((p: any) => p.kind);
        out.push(r);
      }
      return out;
    });
    expect(passages.length).toBeGreaterThan(0);
    expect(passages.filter(p => p.up.length || p.glass.length || p.parts.length)).toEqual([]);
  });

  test(`${key}: every door is open up to its head with a lintel or a glass transom above`, async ({ page }) => {
    await open(page, key);
    await setFurniture(page, false);
    const heads = await page.evaluate(() => (window as any).__host.openings.filter((o: any) => o.kind === 'door').map((o: any) => {
      const c = o.lintelDepth ? (o.lintelDepth[0] + o.lintelDepth[1]) / 2 : 0;
      const up = (window as any).__host.upHit(o.floor, o.x + o.nx * c, o.y + o.ny * c, 1.0);
      return { id: o.id, head: o.head, lintel: o.lintel, up: up === null ? null : Math.round(up * 1000) / 1000 };
    }));
    expect(heads.length).toBeGreaterThan(0);
    expect(heads.filter((h: any) => (h.lintel ? !(h.up !== null && Math.abs(h.up - h.head) < 0.02) : h.up !== null && h.up < 3))).toEqual([]);
  });
}

test('hotel: every door and passage can be walked through its middle both ways; the passages are left open', async ({ page }) => {
  test.setTimeout(300_000);
  await open(page, 'hotel');
  await setFurniture(page, false);
  const all = await allDoorWalks(page, 'hotel');
  expect(all.length).toBeGreaterThan(0);
  expect(all.filter(d => !d.ok)).toEqual([]);
  const passages = await page.evaluate(() => {
    const h = (window as any).__host;
    return h.openings.filter((d: any) => d.kind === 'passage').map((d: any) => {
      const ux = d.ny, uy = -d.nx, r: any = { id: d.id, up: [], glass: [] };
      for (const k of [0.25, 0.5, 0.75]) {
        const x = d.x + ux * (k - 0.5) * d.width, y = d.y + uy * (k - 0.5) * d.width, up = h.upHit(d.floor, x, y, 1.0);
        if (up !== null && up < 2.5) r.up.push(Math.round(up * 100) / 100);
        for (const ht of [0.35, 1.2]) {
          const hit = h.rayHit(d.floor, x - d.nx * 0.6, y - d.ny * 0.6, ht, d.nx, d.ny, 1.2);
          if (hit && /glass/.test(hit.name) && Math.abs(hit.d - 0.6) <= d.wallThickness / 2 + 0.05) r.glass.push(hit.name);
        }
      }
      r.parts = h.model.parts.filter((p: any) => p.label && p.label.split(' ')[0] === d.id).map((p: any) => p.kind);
      return r;
    });
  });
  expect(passages.length).toBeGreaterThan(0);
  expect(passages.filter((p: any) => p.up.length || p.glass.length || p.parts.length)).toEqual([]);
});

test('hotel: every door is open up to its head with a lintel or transom above, reaching both drawn jambs', async ({ page }) => {
  await open(page, 'hotel');
  await setFurniture(page, false);
  expect(await installPageHelpers(page)).toBe(true);
  const heads = await page.evaluate(() => (window as any).__host.openings.filter((o: any) => o.kind === 'door').map((o: any) => {
    const c = o.lintelDepth ? (o.lintelDepth[0] + o.lintelDepth[1]) / 2 : 0;
    const up = (window as any).__host.upHit(o.floor, o.x + o.nx * c, o.y + o.ny * c, 1.0);
    return { id: o.id, head: o.head, lintel: o.lintel, up: up === null ? null : Math.round(up * 1000) / 1000 };
  }));
  expect(heads.length).toBeGreaterThan(0);
  expect(heads.filter((h: any) => (h.lintel ? !(h.up !== null && Math.abs(h.up - h.head) < 0.02) : h.up !== null && h.up < 2.5))).toEqual([]);
  const slits = await page.evaluate(() => {
    const w = window as any, h = w.__host;
    return h.openings.filter((o: any) => o.kind === 'door' && o.lintel).map((o: any) => {
      const sp = w.__t.span(o, 1.2, true), c = o.lintelDepth ? (o.lintelDepth[0] + o.lintelDepth[1]) / 2 : 0, ux = o.ny, uy = -o.nx, r: any = { id: o.id };
      if (!sp) return { ...r, ok: false, why: 'no jambs met' };
      r.ends = [[1, sp.jambs[0]], [-1, sp.jambs[1]]].map(([sg, d]) => {
        const x = o.x + o.nx * c + ux * sg * (d - 0.01), y = o.y + o.ny * c + uy * sg * (d - 0.01), up = h.upHit(o.floor, x, y, 1.0);
        return up === null ? null : Math.round(up * 1000) / 1000;
      });
      r.ok = r.ends.every((u: number | null) => u !== null && Math.abs(u - o.head) < 0.02);
      return r;
    });
  });
  expect(slits.length).toBeGreaterThan(0);
  expect(slits.filter((s: any) => !s.ok)).toEqual([]);
});

test('suite: every door and opening can be walked through both ways (the exterior ones from inside); the west glass stops you', async ({ page }) => {
  test.setTimeout(300_000);
  await open(page, 'suite');
  await setFurniture(page, false);
  const all = await allDoorWalks(page, 'suite', [0.9, 0.7, 0.55]);
  expect(all.length).toBeGreaterThan(0);
  expect(all.filter(d => !d.ok)).toEqual([]);
  // the suite page has no rayHit (lib/walks.ts glassWalks reads it): its own walk, from 1 m inside the glass's room-side face
  const glass = await page.evaluate(() => {
    const w = window as any, v = w.__viewer, s = v.state, keep = s.pos.clone(), out: any[] = [];
    for (const g of w.__host.probes) for (const side of g.inside) {
      const nx = g.nx * side, ny = g.ny * side, deg = Math.atan2(nx, -ny) * 180 / Math.PI;
      s.pos.x = g.x + nx * 1.0; s.pos.z = -(g.y + ny * 1.0);
      v.probe.walk(deg, 2.0);
      out.push({ id: g.id, stoppedAt: Math.round(((s.pos.x - g.x) * nx + (-s.pos.z - g.y) * ny) * 100) / 100 });
    }
    s.pos.copy(keep); return out;
  });
  expect(glass.map((g: any) => g.id)).toEqual(['suite-glass-west']);
  expect(glass.filter((g: any) => !(g.stoppedAt > 0.1 && g.stoppedAt < 0.6))).toEqual([]);
});

// ============================================================================================================ glass
for (const key of ['bank-v1', 'bank-v2', 'hotel'] as VersionKey[]) {
  test(`${key}: glass stops you at every probe`, async ({ page }) => {
    test.setTimeout(300_000);
    await open(page, key);
    await setFurniture(page, false);
    const glass = [];
    for (const f of VERSIONS[key].floors) {
      expect(await walkOn(page, f)).toBe(f);
      glass.push(...await glassWalks(page));
    }
    expect(glass.length).toBeGreaterThan(0);
    expect(glass.filter(g => !g.ok)).toEqual([]);
    if (key !== 'hotel') expect(glass.some(g => g.what === 'glass partition')).toBe(true);
  });
}

// ================================================================================================ the bank's extras
for (const key of ['bank-v1', 'bank-v2'] as VersionKey[]) {
  test(`${key}: glass partitions at their type's height with nothing above; the parapet at 1.10 m; the ATM gap closed to 3.70 m; no floor over the stair and lift voids; steps one riser apart`, async ({ page }) => {
    await open(page, key);
    await setFurniture(page, false);
    await walkOn(page, VERSIONS[key].floors[0]!);
    const tops = await page.evaluate(() => {
      const h = (window as any).__host;
      return h.probes.filter((g: any) => g.what === 'glass partition').map((g: any) => {
        const side = g.inside[0] || 1, nx = g.nx * side, ny = g.ny * side;
        const at = (z: number) => { const hit = h.rayHit(g.floor, g.x + nx * 0.5, g.y + ny * 0.5, z, -nx, -ny, 0.6); return hit && /glass/.test(hit.name) ? Math.round(hit.d * 100) / 100 : null; };
        return { id: g.id, top: g.top, below: at(g.top - 0.1), above: at(g.top + 0.15) };
      });
    });
    expect(tops.length).toBeGreaterThan(0);
    expect([...new Set(tops.map((t: any) => t.top))]).toEqual([2.6]);
    expect(tops.filter((t: any) => t.below === null || t.above !== null)).toEqual([]);

    const extras = await page.evaluate(() => {
      const w = window as any, h = w.__host, M = h.model, out: any = { parapets: [], closures: [], noFloor: [], steps: [] };
      const centre = (p: any) => { let x = 0, y = 0; p.o.forEach((q: number[]) => { x += q[0]!; y += q[1]!; }); return [x / p.o.length, y / p.o.length]; };
      for (const p of M.parts.filter((q: any) => q.kind === 'parapet')) {
        const a = p.o[0], b = p.o[1], m = [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2];
        let best: any = null;
        for (const s of [1, -1]) {
          const L = Math.hypot(b[0] - a[0], b[1] - a[1]), nx = -(b[1] - a[1]) / L * s, ny = (b[0] - a[0]) / L * s;
          const x = m[0]! + nx * 0.03, y = m[1]! + ny * 0.03, top = h.upHit(p.floor, x, y, 0.5);
          if (top !== null && (best === null || Math.abs(top - M.railingHeight) < Math.abs(best.top - M.railingHeight))) best = { x, y, top };
        }
        const over = best && h.upHit(p.floor, best.x, best.y, p.z1 + 0.05);
        out.parapets.push({ floor: p.floor, rail: M.railingHeight, top: best && Math.round(best.top * 1000) / 1000, overhead: over === null || over === undefined ? null : Math.round(over * 100) / 100 });
      }
      for (const [k, cs] of Object.entries(M.closures) as [string, any[]][]) for (const c of cs) {
        const top = h.upHit(k, c.x, c.y, 0.5);
        const pairs = [[1, 0], [0, 1], [0.7071, 0.7071], [0.7071, -0.7071]].map(([dx, dy]) => [h.rayHit(k, c.x - dx! * 0.5, c.y - dy! * 0.5, 1.0, dx, dy, 0.6), h.rayHit(k, c.x + dx! * 0.5, c.y + dy! * 0.5, 1.0, -dx!, -dy!, 0.6)]);
        out.closures.push({ floor: k, object: c.object, top: top === null ? null : Math.round(top * 100) / 100, blocks: pairs.some(([p, q]) => p && q && p.d < 0.55 && q.d < 0.55) });
      }
      const lowest = h.floors[0].key, v = w.__viewer;
      const onFloorAt = (k: string, x: number, y: number) => { const s = v.state, keep = s.pos.clone(); v.goToFloor(k); s.pos.x = x; s.pos.z = -y; const r = v.probe.onFloor(); s.pos.copy(keep); return r; };
      for (const [k, ss] of Object.entries(M.stairOutlines) as [string, any[]][]) for (const s of ss) if (k !== lowest) out.noFloor.push({ floor: k, what: 'stair', onFloor: onFloorAt(k, s.x, s.y) });
      for (const [k, vs] of Object.entries(M.voids) as [string, any[]][]) for (const vd of vs) if (vd.what !== 'stair') out.noFloor.push({ floor: k, what: vd.what, onFloor: onFloorAt(k, vd.x, vd.y) });
      for (const p of M.parts.filter((q: any) => q.kind === 'step')) {
        const [x, y] = centre(p), top = h.downHit(p.floor, x, y, 3.0);
        out.steps.push({ label: p.label, flight: p.label.replace(/ step [0-9]+ (up|down)$/, ''), z1: p.z1, top: top === null ? null : Math.round(top * 1000) / 1000 });
      }
      const fl = h.floors, H = fl.length > 1 ? fl[1].level - fl[0].level : 3.0;
      out.riser = H / Math.ceil(H / 0.18 - 1e-9);
      return out;
    });
    expect(extras.parapets.length).toBeGreaterThan(0);
    expect(extras.parapets.filter((p: any) => p.top === null || Math.abs(p.top - p.rail) > 0.02 || (p.overhead !== null && p.overhead < 3))).toEqual([]);
    expect(extras.parapets.map((p: any) => p.rail)).toContain(1.1);
    expect(extras.closures.length).toBeGreaterThan(0);
    expect(extras.closures.filter((c: any) => c.top === null || Math.abs(c.top - 3.7) > 0.02 || !c.blocks)).toEqual([]);
    expect(extras.noFloor.length).toBeGreaterThanOrEqual(2);
    expect(extras.noFloor.filter((v: any) => v.onFloor)).toEqual([]);
    const bad = extras.steps.filter((p: any) => p.top === null || Math.abs(p.top - p.z1) > 0.02);
    for (const f of [...new Set(extras.steps.map((p: any) => p.flight))]) {
      const ts = extras.steps.filter((p: any) => p.flight === f).map((p: any) => p.top).sort((a: number, b: number) => Math.abs(a) - Math.abs(b));
      ts.forEach((z: number | null, i: number) => { if (z === null || Math.abs(Math.abs(z) - (i + 1) * extras.riser) > 0.01) bad.push({ flight: f, step: i + 1, top: z }); });
    }
    expect(extras.steps.length).toBeGreaterThan(0);
    expect(bad).toEqual([]);
  });
}

// ================================================================================================= the hotel's extras
test('hotel: the lift doors are open 1.00 m between their drawn jambs up to the 2.10 m head, each shaft walled on its other sides', async ({ page }) => {
  await open(page, 'hotel');
  await setFurniture(page, false);
  expect(await installPageHelpers(page)).toBe(true);
  const lifts = await page.evaluate(() => {
    const w = window as any, h = w.__host, M = h.model, shafts = Object.values(M.voids).flat().filter((v: any) => /^lift/.test(v.what)) as any[], out: any[] = [];
    for (const d of M.openings.filter((o: any) => o.liftDoor)) {
      const r: any = { id: d.id };
      r.jambs = [0.35, 1.2].map(ht => { const sp = w.__t.span(d, ht, true); return sp && sp.jambs; });
      r.width = r.jambs.every(Boolean) ? Math.round((r.jambs[0][0] + r.jambs[0][1]) * 1000) / 1000 : null;
      const up = h.upHit(d.floor, d.x, d.y, 1.0); r.head = up === null ? null : Math.round(up * 1000) / 1000;
      const sh = shafts.slice().sort((a, b) => Math.hypot(a.x - d.x, a.y - d.y) - Math.hypot(b.x - d.x, b.y - d.y))[0];
      const tx = d.x - sh.x, ty = d.y - sh.y, toDoor = Math.hypot(tx, ty);
      r.sides = [[1, 0], [-1, 0], [0, 1], [0, -1]].map(([dx, dy]) => {
        const hit = h.rayHit(d.floor, sh.x, sh.y, 1.0, dx, dy, 6), door = (dx! * tx + dy! * ty) / toDoor > 0.9;
        return { door, d: hit ? Math.round(hit.d * 100) / 100 : null, what: hit ? hit.name : null, ok: door ? (!hit || hit.d > toDoor + 0.3) : (!!hit && hit.d < 1.4 && /solid/.test(hit.name)) };
      });
      out.push(r);
    }
    return out;
  });
  expect(lifts).toHaveLength(4);
  const bad = lifts.filter((l: any) => l.width === null || Math.abs(l.width - 1.0) > 0.02 || l.jambs.some((j: any) => !j || Math.abs(j[0] - j[1]) > 0.02 || Math.abs(j[0] + j[1] - 1.0) > 0.02)
    || l.head === null || Math.abs(l.head - 2.1) > 0.02 || l.sides.filter((x: any) => x.door).length !== 1 || !l.sides.every((x: any) => x.ok));
  expect(bad).toEqual([]);
});

test("hotel: Walk's invisible collision skins reach into no opening between wall jambs", async ({ page }) => {
  await open(page, 'hotel');
  await setFurniture(page, false);
  expect(await installPageHelpers(page)).toBe(true);
  const skinned = await page.evaluate(() => {
    const w = window as any;
    return w.__host.openings.filter((d: any) => d.kind === 'door' || d.kind === 'passage').map((d: any) => {
      const r: any = { id: d.id, glassJamb: (d.jambs || []).includes('glass'), drawn: [], walk: [] };
      for (const ht of [0.35, 1.2]) { const a = w.__t.span(d, ht, true), b = w.__t.span(d, ht, false); r.drawn.push(a && a.width); r.walk.push(b && b.width); if (b) r.what = b.what; }
      r.same = r.drawn.every((x: number | null, i: number) => (x === null && r.walk[i] === null) || (x !== null && r.walk[i] !== null && Math.abs(x - r.walk[i]) <= 0.005));
      return r;
    });
  });
  expect(skinned.length).toBeGreaterThan(0);
  expect(skinned.filter((r: any) => !r.same && !r.glassJamb)).toEqual([]);
});

test('hotel: the hatches are open from the sill to the head', async ({ page }) => {
  await open(page, 'hotel');
  await setFurniture(page, false);
  const hatches = await page.evaluate(() => {
    const h = (window as any).__host;
    return h.openings.filter((o: any) => o.hatch).map((o: any) => {
      const r: any = { id: o.id };
      const across = (ht: number) => { const hit = h.rayHit(o.floor, o.x - o.nx * 0.6, o.y - o.ny * 0.6, ht, o.nx, o.ny, 1.2); return hit ? Math.round(hit.d * 1000) / 1000 : null; };
      r.at150 = across(1.5); r.at045 = across(0.45);
      const dn = h.downHit(o.floor, o.x, o.y, 1.5), up = h.upHit(o.floor, o.x, o.y, 1.0);
      r.sillTop = dn === null ? null : Math.round(dn * 1000) / 1000; r.headAt = up === null ? null : Math.round(up * 1000) / 1000;
      r.ok = (r.at150 === null || r.at150 > 0.6 + o.wallThickness / 2 + 0.02) && r.at045 !== null && Math.abs(r.at045 - (0.6 - o.wallThickness / 2)) < 0.03
        && r.sillTop !== null && Math.abs(r.sillTop - o.sill) < 0.01 && r.headAt !== null && Math.abs(r.headAt - o.head) < 0.01;
      return r;
    });
  });
  expect(hatches.length).toBeGreaterThan(0);
  expect(hatches.filter((x: any) => !x.ok)).toEqual([]);
});

test('hotel: the forecourt is floor and the entrance can be walked out and in', async ({ page }) => {
  await open(page, 'hotel');
  await setFurniture(page, false);
  expect(await walkOn(page, 'F1')).toBe('F1');
  const e = await page.evaluate(() => {
    const w = window as any, v = w.__viewer, s = v.state, keep = s.pos.clone(), M = w.__host.model, out: any = { mode: v.mode, floor: s.floor.key, spots: 0, notFloor: [] };
    const fc = M.parts.find((p: any) => p.kind === 'slab' && p.floor === 'F1' && /^forecourt/.test(p.label || ''));
    if (!fc) return { none: true };
    const inPoly = (x: number, y: number, ring: number[][]) => { let c = false; for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) { const [xi, yi] = ring[i]!, [xj, yj] = ring[j]!; if ((yi! > y) !== (yj! > y) && x < xi! + (y - yi!) * (xj! - xi!) / (yj! - yi!)) c = !c; } return c; };
    const xs = fc.o.map((q: number[]) => q[0]), ys = fc.o.map((q: number[]) => q[1]);
    for (let x = Math.min(...xs) + 0.1; x < Math.max(...xs); x += 0.5) for (let y = Math.min(...ys) + 0.1; y < Math.max(...ys); y += 0.2) {
      if (![[0, 0], [0.15, 0], [-0.15, 0], [0, 0.15], [0, -0.15]].every(([dx, dy]) => inPoly(x + dx!, y + dy!, fc.o))) continue;
      s.pos.x = x; s.pos.z = -y; out.spots++; if (!v.probe.onFloor()) out.notFloor.push([Math.round(x * 100) / 100, Math.round(y * 100) / 100]);
    }
    for (const d of M.openings.filter((o: any) => o.floor === 'F1' && o.kind === 'door')) for (const sg of [1, -1]) {
      const t = d.wallThickness / 2 + 0.3;
      if (inPoly(d.x + d.nx * sg * t, d.y + d.ny * sg * t, fc.o)) out.door = { id: d.id, x: d.x, y: d.y, ox: d.nx * sg, oy: d.ny * sg, t: d.wallThickness / 2 };
    }
    if (!out.door) return out;
    const D = out.door, deg = (ux: number, uy: number) => Math.atan2(-ux, uy) * 180 / Math.PI;
    const inner = M.openings.filter((o: any) => o.floor === 'F1' && o.kind === 'door' && o.id !== D.id && Math.abs((o.x - D.x) * D.oy - (o.y - D.y) * D.ox) < 0.3 && ((o.x - D.x) * D.ox + (o.y - D.y) * D.oy) < 0)
      .sort((a: any, b: any) => Math.hypot(a.x - D.x, a.y - D.y) - Math.hypot(b.x - D.x, b.y - D.y))[0];
    out.inner = inner ? inner.id : null;
    s.pos.x = D.x - D.ox * 0.9; s.pos.z = -(D.y - D.oy * 0.9);
    out.outStart = v.probe.onFloor();
    v.probe.walk(deg(D.ox, D.oy), 3);
    const ex = s.pos.x, ey = -s.pos.z;
    out.outPast = Math.round(((ex - D.x) * D.ox + (ey - D.y) * D.oy - D.t) * 100) / 100;
    out.outOnForecourt = inPoly(ex, ey, fc.o) && v.probe.onFloor();
    s.pos.x = ex + D.ox * 0.1; s.pos.z = -(ey + D.oy * 0.1); out.edgeAhead = !v.probe.onFloor();
    s.pos.x = D.x + D.ox * (D.t + 0.3); s.pos.z = -(D.y + D.oy * (D.t + 0.3));
    out.inStart = { onFloor: v.probe.onFloor(), clearance: Math.min(9, v.probe.clearance()) };
    v.probe.walk(deg(-D.ox, -D.oy), 4.5);
    const ix = s.pos.x, iy = -s.pos.z;
    out.inPastInner = inner ? Math.round(((ix - inner.x) * -D.ox + (iy - inner.y) * -D.oy) * 100) / 100 : null;
    s.pos.copy(keep); return out;
  });
  expect(e.none).toBeUndefined();
  expect({ mode: e.mode, floor: e.floor }).toEqual({ mode: 'walk', floor: 'F1' });
  expect(e.spots).toBeGreaterThanOrEqual(20);
  expect(e.notFloor).toEqual([]);
  expect(e.door).toBeTruthy();
  expect(e.outStart).toBe(true);
  expect(e.outPast).toBeGreaterThanOrEqual(0.15);
  expect(e.outOnForecourt).toBe(true);
  expect(e.edgeAhead).toBe(true);
  expect(e.inStart.onFloor).toBe(true);
  expect(e.inStart.clearance).toBeGreaterThanOrEqual(0.25);
  expect(e.inner).toBeTruthy();
  expect(e.inPastInner).toBeGreaterThanOrEqual(0.3);
});

test('hotel: the railings stop you (the terrace and the open stair), with floor between you and them', async ({ page }) => {
  await open(page, 'hotel');
  await setFurniture(page, false);
  expect(await installPageHelpers(page)).toBe(true);
  expect(await walkOn(page, 'F2')).toBe('F2');
  const walks = await page.evaluate(() => {
    const w = window as any, v = w.__viewer, s = v.state, keep = s.pos.clone(), M = w.__host.model, out: any[] = [];
    for (const p of M.parts.filter((q: any) => q.kind === 'railing')) {
      const xs = p.o.map((q: number[]) => q[0]), ys = p.o.map((q: number[]) => q[1]), x0 = Math.min(...xs), x1 = Math.max(...xs), y0 = Math.min(...ys), y1 = Math.max(...ys);
      const alongX = x1 - x0 >= y1 - y0, L = alongX ? x1 - x0 : y1 - y0, n = Math.max(1, Math.min(5, Math.floor(L / 1.5))), half = alongX ? (y1 - y0) / 2 : (x1 - x0) / 2;
      for (let k = 0; k < n; k++) {
        const t = (k + 0.5) / n, cx = alongX ? x0 + (x1 - x0) * t : (x0 + x1) / 2, cy = alongX ? (y0 + y1) / 2 : y0 + (y1 - y0) * t;
        const r: any = { label: p.label, gap: null };
        for (const sg of [1, -1]) {
          const nx = alongX ? 0 : sg, ny = alongX ? sg : 0;
          s.pos.x = cx + nx * (half + 1.0); s.pos.z = -(cy + ny * (half + 1.0));
          if (!v.probe.onFloor() || v.probe.clearance() < 0.3) continue;
          v.probe.walk(Math.atan2(nx, -ny) * 180 / Math.PI, 2.0);
          const px = s.pos.x, py = -s.pos.z;
          r.gap = Math.round(((px - cx) * nx + (py - cy) * ny - half) * 100) / 100;
          const hit = w.__t.reach('F2', px, py, 0.35, -nx, -ny, 1.0, true);
          r.ahead = hit ? hit.name : 'nothing';
          s.pos.x = cx + nx * (half + Math.max(0.02, r.gap / 2)); s.pos.z = -(cy + ny * (half + Math.max(0.02, r.gap / 2)));
          r.floorBetween = v.probe.onFloor();
          break;
        }
        r.ok = r.gap !== null && r.gap > 0.1 && r.gap < 0.6 && /railing/.test(r.ahead) && r.floorBetween;
        out.push(r);
      }
    }
    s.pos.copy(keep); return out;
  });
  const terrace = walks.filter((r: any) => /terrace/.test(r.label));
  expect(terrace.length).toBeGreaterThanOrEqual(6);
  expect(walks.length).toBeGreaterThan(terrace.length);
  expect(walks.filter((r: any) => !r.ok)).toEqual([]);
});

test('hotel: Floor 2 is floor where its plate is and open over its voids; the steps of each stair sit one riser apart', async ({ page }) => {
  await open(page, 'hotel');
  await setFurniture(page, false);
  await walkOn(page, 'F1');
  const f2 = await page.evaluate(() => {
    const w = window as any, v = w.__viewer, s = v.state, M = w.__host.model, out: any[] = [];
    for (const vd of M.voids.F2 || []) { v.goToFloor('F2'); const keep = s.pos.clone(); s.pos.x = vd.x; s.pos.z = -vd.y; out.push({ what: vd.what, onFloor: v.probe.onFloor() }); s.pos.copy(keep); }
    return out;
  });
  expect(f2.length).toBeGreaterThanOrEqual(3);
  expect(f2.filter((x: any) => x.onFloor)).toEqual([]);
  const steps = await page.evaluate(() => {
    const h = (window as any).__host, M = h.model, out: any[] = [];
    const centre = (p: any) => { let x = 0, y = 0; p.o.forEach((q: number[]) => { x += q[0]!; y += q[1]!; }); return [x / p.o.length, y / p.o.length]; };
    for (const p of M.parts.filter((q: any) => q.kind === 'step')) {
      const [x, y] = centre(p), top = h.downHit(p.floor, x, y, 3.2);
      out.push({ stair: p.label.split(' ')[0], floor: p.floor, y, z0: p.z0, top: top === null ? null : Math.round(top * 1000) / 1000, label: p.label });
    }
    const fl = h.floors, H = fl[1].level - fl[0].level;
    return { steps: out, riser: H / Math.ceil(H / 0.18 - 1e-9), H };
  });
  const stairs: Record<string, any[]> = {}, bad: any[] = [];
  for (const p of steps.steps) (stairs[p.stair] ??= []).push(p);
  for (const [id, ps] of Object.entries(stairs)) {
    ps.map(p => p.top).sort((a, b) => a - b).forEach((z: number | null, i: number) => { if (z === null || Math.abs(z - (i + 1) * steps.riser) > 0.01) bad.push({ stair: id, step: i + 1, top: z }); });
  }
  expect(steps.steps.length).toBeGreaterThan(0);
  expect(bad).toEqual([]);
  // the flight from Floor 1 lands on Floor 2; the upper stair rises from Floor 2, each step further north, none below it
  const flight1 = steps.steps.filter((p: any) => p.floor === 'F1'), upper = steps.steps.filter((p: any) => p.floor === 'F2').sort((a: any, b: any) => a.top - b.top);
  expect(flight1.length).toBeGreaterThan(0);
  expect(Math.abs(Math.max(...flight1.map((p: any) => p.top)) + steps.riser - steps.H)).toBeLessThan(0.01);
  expect(upper.length).toBeGreaterThanOrEqual(3);
  upper.forEach((p: any, i: number) => {
    expect(p.z0).toBeGreaterThan(-1e-6);
    if (i) expect(p.y).toBeGreaterThan(upper[i - 1].y + 0.1);
  });
});

test('hotel: the Plan picture tick (off at start, each shown floor its sheet, both in Walk, off again); ?picture=1', async ({ page }) => {
  const shown = () => page.evaluate(() => ((window as any).__host.pictures.objs as any[]).filter(m => m.visible).map(m => m.userData.key).sort().join(','));
  const { p } = await open(page, 'hotel', '?nodownload=1&test=1');
  await page.evaluate(() => (window as any).__host.pictures.ready);
  const r: Record<string, unknown> = {};
  r.atStart = { ticked: await page.locator(sel.toggle('picture')).isChecked(), shown: await shown() };
  await clickSel(page, sel.toggle('picture')); await sleep(300);
  r.on = await shown();
  await clickSel(page, sel.floorButton('F1')); await sleep(400);
  r.onF1 = await shown();
  await clickSel(page, sel.floorButton('F2')); await sleep(400);
  r.onF2 = await shown();
  await clickSel(page, sel.floorButton('all')); await sleep(200);
  await page.locator(sel.floorButton('all')).blur();
  await p.press('Digit2'); await sleep(300);
  r.inWalk = await shown();
  await p.press('Digit1'); await sleep(200);
  await clickSel(page, sel.toggle('picture')); await sleep(300);
  r.off = await shown();
  expect(r).toEqual({ atStart: { ticked: false, shown: '' }, on: 'F1,F2', onF1: 'F1', onF2: 'F2', inWalk: 'F1,F2', off: '' });

  await page.goto(urlOf('hotel', '?nodownload=1&test=1&picture=1'));
  await waitReady(page);
  await page.evaluate(() => (window as any).__host.pictures.ready);
  await sleep(300);
  expect({ ticked: await page.locator(sel.toggle('picture')).isChecked(), shown: await shown() }).toEqual({ ticked: true, shown: 'F1,F2' });
});

test("hotel: the plan pictures are the source files byte for byte; each sheet's corners through the pictureFrame, 5 mm above its floor; they line up with the walls", async ({ page }) => {
  test.setTimeout(300_000);
  await open(page, 'hotel');
  await page.evaluate(() => (window as any).__host.pictures.ready);
  expect(await installPageHelpers(page)).toBe(true);
  const src = await page.evaluate(() => {
    const w = window as any, out: Record<string, any> = {};
    for (const m of w.__host.pictures.objs) {
      const k = m.userData.key, pf = w.__host.model.pictureFrame[k], img = m.material.map.image, g = m.geometry;
      g.computeBoundingBox();
      const b = g.boundingBox, px = (x: number, y: number) => [pf.originPx[0] + pf.pxPerMetreX * (x + w.__host.model.offset[0]), pf.originPx[1] - pf.pxPerMetreY * (y + w.__host.model.offset[1])];
      out[k] = { file: pf.file, data: w.__host.pictures.src[k], natural: [img.naturalWidth, img.naturalHeight], size: pf.size,
        corners: [px(b.min.x, -b.min.z), px(b.max.x, -b.max.z)].map(q => q.map(v => Math.round(v * 100) / 100)),
        lift: Math.round((b.min.y + m.position.y - w.__t.levelOf(k)) * 1000) / 1000 };
    }
    return out;
  });
  expect(Object.keys(src).sort()).toEqual(['F1', 'F2']);
  for (const [k, o] of Object.entries(src)) {
    const file = isApp ? path.join(APP, 'fixtures', 'pictures', path.basename(o.file)) : path.resolve(PROTOTYPES, 'hotel_test', 'src', o.file);
    const m = /^data:image\/[a-z]+;base64,(.*)$/.exec(o.data || '');
    expect(m, `${k}: a data: URL`).toBeTruthy();
    expect(Buffer.from(m![1]!, 'base64').equals(readFileSync(file)), `${k}: the bytes of ${file}`).toBe(true);
    expect(o.natural).toEqual(o.size);
    expect(Math.abs(o.corners[0][0]) < 0.05 && Math.abs(o.corners[0][1]) < 0.05 && Math.abs(o.corners[1][0] - o.size[0]) < 0.05 && Math.abs(o.corners[1][1] - o.size[1]) < 0.05, JSON.stringify(o.corners)).toBe(true);
    expect(o.lift).toBeCloseTo(0.005, 3);
  }
  const lines = await page.evaluate(() => {
    const t = (window as any).__t, out: Record<string, any> = {};
    for (const k of ['F1', 'F2']) {
      out[k] = { at: t.faceLineUp(k), near: [[0.1, 0], [-0.1, 0], [0, 0.1], [0, -0.1]].map(([dx, dy]) => t.faceLineUp(k, dx, dy)),
        far: [[0.3, 0], [-0.3, 0], [0, 0.3], [0, -0.3]].map(([dx, dy]) => t.faceLineUp(k, dx, dy)) };
    }
    return out;
  });
  for (const [k, o] of Object.entries(lines)) {
    expect(o.at.n, k).toBeGreaterThanOrEqual(500);
    expect(o.near.filter((x: any) => x.contrast * 1.3 > o.at.contrast), `${k} near`).toEqual([]);
    expect(o.far.filter((x: any) => x.contrast * 1.6 > o.at.contrast), `${k} far`).toEqual([]);
  }
});

// ================================================================================================= the house's openings
const PLATES_SHA1 = 'ad13064344f9';            // cad_test/test_house_openings.mjs: the floor plates before the openings were cut
const RANK: Record<string, number> = { blocked: 0, 'from the floor side': 1, 'both ways': 2 };

/** The house's Build settings now ({ level, height } per floor): the replay's, else the Walk levels and the model's wall heights. */
const houseSettings = (page: Page) => page.evaluate(() => {
  const w = window as any;
  if (w.__build && w.__build.state && w.__build.state.settings) return JSON.parse(JSON.stringify(w.__build.state.settings)) as Record<string, { level: number; height: number }>;
  const m = w.__host.model;
  return Object.fromEntries(w.__host.floors.map((f: any) => [f.key, { level: f.level, height: m.floors.find((x: any) => x.key === f.key).wallHeight }])) as Record<string, { level: number; height: number }>;
});

test('house: the floor plates are the ones the model had before the openings (fingerprint)', async ({ page }) => {
  await open(page, 'house');
  const pl = await plates(page);
  expect({ ground: pl.ground?.length, upper: pl.upper?.length }).toEqual({ ground: 3, upper: 1 });
  expect(createHash('sha1').update(JSON.stringify(pl)).digest('hex').slice(0, 12)).toBe(PLATES_SHA1);
});

test('house: every door can be walked through; the passages are left as they were and no harder to walk through than before the openings', async ({ page }) => {
  test.setTimeout(300_000);
  await open(page, 'house');
  await setFurniture(page, false);
  const doors: any[] = [], passages: any[] = [];
  for (const f of VERSIONS.house.floors) {
    expect(await walkOn(page, f)).toBe(f);
    const list = await page.evaluate(k => (window as any).__host.openings.filter((o: any) => o.floor === k), f);
    doors.push(...(await walkThrough(page, list.filter((o: any) => o.kind === 'door' && !o.glazed))));
    const ps = list.filter((o: any) => o.kind === 'passage');
    const walked = await walkThrough(page, ps.map((d: any) => ({ id: d.id, floor: d.floor, x: d.x, y: d.y, nx: d.nx, ny: d.ny, a: d.a, b: d.b, width: d.width })));
    // what of the cut is in or over each passage: knee and chest casts across at 1/4, 1/2, 3/4 and one up from 1 m (names, classified below)
    const hits = await page.evaluate(({ k, ids }) => {
      const h = (window as any).__host, lv = h.floors.find((x: any) => x.key === k).level, all = h.openings.filter((o: any) => o.floor === k);
      const others = all.filter((q: any) => q.kind !== 'passage');
      const segDist = (p: number[], q: any) => { const L2 = (q.b[0] - q.a[0]) ** 2 + (q.b[1] - q.a[1]) ** 2,
        t = L2 ? Math.max(0, Math.min(1, ((p[0]! - q.a[0]) * (q.b[0] - q.a[0]) + (p[1]! - q.a[1]) * (q.b[1] - q.a[1])) / L2)) : 0;
        return Math.hypot(p[0]! - q.a[0] - t * (q.b[0] - q.a[0]), p[1]! - q.a[1] - t * (q.b[1] - q.a[1])); };
      return ids.map((id: string) => {
        const d = all.find((o: any) => o.id === id), ux = (d.b[0] - d.a[0]) / d.width, uy = (d.b[1] - d.a[1]) / d.width, names: string[] = [];
        let skipped = 0;
        for (const t of [0.25, 0.5, 0.75]) {
          const px = d.a[0] + ux * d.width * t, py = d.a[1] + uy * d.width * t;
          if (others.some((q: any) => segDist([px, py], q) < 0.3)) { skipped++; continue; }
          for (const ht of [0.35, 1.2]) { const hit = h.cast(k, [px - d.nx * 0.6, lv + ht, -(py - d.ny * 0.6)], [d.nx, 0, -d.ny], 1.2); if (hit) names.push(hit.name); }
          const up = h.cast(k, [px, lv + 1.0, -py], [0, 1, 0], 8);
          if (up) names.push(up.name);
        }
        return { id, names, skipped };
      });
    }, { k: f, ids: ps.map((d: any) => d.id) });
    passages.push(...walked.map(r => ({ ...r, floor: f, pieces: (hits.find((x: any) => x.id === r.id)?.names ?? []).filter((n: string) => meshIs(n, 'piece')) })));
  }
  const judged = doors.map(r => ({ id: r.id, result: judgeHouseWalk(r) }));
  expect(judged.length).toBeGreaterThan(0);
  expect(judged.filter(r => r.result === 'blocked')).toEqual([]);
  expect(passages.length).toBeGreaterThan(0);
  expect(passages.filter(p => p.pieces.length).map(p => ({ id: p.id, pieces: p.pieces }))).toEqual([]);
  const before = JSON.parse(readFileSync(path.join(APP, 'fixtures', 'prototype', 'house_openings_before.json'), 'utf8')).passages as any[];
  const rows = passages.map(r => {
    const m = before.find(q => q.floor === r.floor && Math.hypot(q.x - r.x, q.y - r.y) < 0.05);
    return { id: r.id, now: judgeHouseWalk(r), before: m ? m.result : 'not walked before' };
  });
  expect(rows.filter(x => x.before === 'not walked before')).toEqual([]);
  expect(rows.filter(x => x.before in RANK && RANK[x.now]! < RANK[x.before]!)).toEqual([]);
});

test('house: every window stops you (knee and chest rays hit its pane or sill; walking at it you stop before it)', async ({ page }) => {
  test.setTimeout(300_000);
  await open(page, 'house');
  await setFurniture(page, false);
  const windows: any[] = [];
  for (const f of VERSIONS.house.floors) {
    expect(await walkOn(page, f)).toBe(f);
    windows.push(...await page.evaluate(k => {
      const w = window as any, v = w.__viewer, s = v.state, keep = s.pos.clone(), lv = s.floor.level, out: any[] = [];
      const floorAt = (d: any, kk: number) => { s.pos.x = d.x + d.nx * kk; s.pos.z = -(d.y + d.ny * kk); return v.probe.onFloor(); };
      const cross = (d: any, sign: number) => {
        const nx = d.nx * sign, ny = d.ny * sign, deg = Math.atan2(-nx, ny) * 180 / Math.PI;
        let why: number | string = 'no start';
        for (const back of [0.9, 0.7, 0.55, 0.45]) {
          s.pos.x = d.x - nx * back; s.pos.z = -(d.y - ny * back);
          if (!v.probe.onFloor()) { why = 'no floor'; continue; }
          if (v.probe.clearance() < 0.25) { why = 'tight'; continue; }
          v.probe.walk(deg, back * 2);
          return Math.round(((s.pos.x - d.x) * nx + (-s.pos.z - d.y) * ny) * 100) / 100;
        }
        return why;
      };
      for (const d of w.__host.openings.filter((o: any) => o.floor === k && o.glazed)) {
        const r: any = { id: d.id, kind: d.kind, floorPos: floorAt(d, 0.9), floorNeg: floorAt(d, -0.9), rays: [], walk: [] };
        for (const [sign, has] of [[1, r.floorNeg], [-1, r.floorPos]] as [number, boolean][]) {
          if (!has) continue;
          const nx = d.nx * sign, ny = d.ny * sign, ux = (d.b[0] - d.a[0]) / d.width, uy = (d.b[1] - d.a[1]) / d.width;
          const paneAt = Math.round((0.6 + sign * (d.pane || 0) - 0.015) * 1000) / 1000;
          for (const ht of [0.35, 1.2]) for (const t of [0.1, 0.3, 0.5, 0.7, 0.9]) {
            const px = d.a[0] + ux * d.width * t - nx * 0.6, py = d.a[1] + uy * d.width * t - ny * 0.6;
            const hit = w.__host.cast(k, [px, lv + ht, -py], [nx, 0, -ny], 1.2);
            r.rays.push(hit ? { d: Math.round(hit.d * 1000) / 1000, mesh: hit.name, pane: paneAt } : { pane: paneAt });
          }
          r.walk.push(cross(d, sign));
        }
        out.push(r);
      }
      s.pos.copy(keep); return out;
    }, f));
  }
  const num = (x: unknown): x is number => typeof x === 'number';
  const own = (x: any) => !!x && num(x.d) && x.d >= 0.3 && x.d <= x.pane + 0.02 && meshIs(x.mesh, 'piece');
  const stopped = (x: any) => own(x) || (!!x && num(x.d) && x.d >= 0.3 && x.d <= x.pane + 0.02 && meshIs(x.mesh, 'wall'));
  const tested = windows.filter(w => w.rays.length);
  expect(tested.length).toBeGreaterThan(0);
  const bad = tested.filter(w => !w.rays.every(stopped) || w.rays.filter(own).length < 0.6 * w.rays.length || w.walk.some((x: unknown) => !num(x) || x > -0.1));
  expect(bad.map(w => ({ id: w.id, stopped: `${w.rays.filter(stopped).length}/${w.rays.length}`, missed: w.rays.filter((x: any) => !stopped(x)).slice(0, 3), walk: w.walk }))).toEqual([]);
});

test('house: no fins in a door\'s or sash\'s swing, no leaves in front of the windows', async ({ page }) => {
  await open(page, 'house');
  await setFurniture(page, false);
  const levels = await page.evaluate(() => Object.fromEntries((window as any).__host.floors.map((f: any) => [f.key, f.level])));
  const r = await page.evaluate(lv => {
    const h = (window as any).__host, out: any = { tested: 0, leaves: 0, fins: [], front: [], glazed: 0 };
    for (const F of ['ground', 'upper']) {
      for (const d of h.openings.filter((o: any) => o.floor === F && o.kind !== 'passage')) {
        if (!d.leaves || !d.leaves.length) continue;
        out.tested++;
        for (const L of d.leaves) {
          out.leaves++;
          const at = (rr: number, t: number) => [L.hinge[0] + rr * (L.closed[0] * Math.cos(t) + L.open[0] * Math.sin(t)), L.hinge[1] + rr * (L.closed[1] * Math.cos(t) + L.open[1] * Math.sin(t))];
          for (const ht of [0.35, 1.2]) for (const k of [0.3, 0.55, 0.8, 0.95]) {
            const rr = L.r * k;
            for (let i = 0; i < 8; i++) {
              const t0 = (8 + 74 * i / 8) * Math.PI / 180, t1 = (8 + 74 * (i + 1) / 8) * Math.PI / 180;
              const p = at(rr, t0), q = at(rr, t1), len = Math.hypot(q[0]! - p[0]!, q[1]! - p[1]!);
              const hit = h.cast(F, [p[0], lv[F] + ht, -p[1]!], [q[0]! - p[0]!, 0, -(q[1]! - p[1]!)], len);
              if (hit) out.fins.push({ id: d.id, height: ht, mesh: hit.name });
            }
          }
        }
      }
      for (const d of h.openings.filter((o: any) => o.floor === F && o.glazed)) {
        out.glazed++;
        const ux = (d.b[0] - d.a[0]) / d.width, uy = (d.b[1] - d.a[1]) / d.width;
        for (const side of [1, -1]) for (const c of [0.3, 0.6]) for (const ht of [0.35, 1.2]) {
          const off = side * (c + Math.max(Math.abs(d.depth[0]), Math.abs(d.depth[1])));
          const p = [d.a[0] + ux * d.width * 0.1 + d.nx * off, d.a[1] + uy * d.width * 0.1 + d.ny * off];
          const hit = h.cast(F, [p[0], lv[F] + ht, -p[1]!], [ux, 0, -uy], d.width * 0.8);
          if (hit) out.front.push({ id: d.id, side, out: c, height: ht, mesh: hit.name });
        }
      }
    }
    return out;
  }, levels);
  expect(r.tested).toBeGreaterThan(0);
  expect(r.fins).toEqual([]);
  expect(r.glazed).toBeGreaterThan(0);
  expect(r.front.filter((x: any) => meshIs(x.mesh, 'glass') || meshIs(x.mesh, 'single'))).toEqual([]);
});

test('house: a lintel at every door head, staying there when the ground walls go to 3.50 / 2.00 / 4.50 / 3.90 m; panes reaching the top follow', async ({ page }) => {
  test.setTimeout(300_000);
  await open(page, 'house');
  const hasReplay = await page.evaluate(() => !!(window as any).__build);
  const H0 = await houseSettings(page);
  const lintels = async () => {
    const S = await houseSettings(page);
    const rows = await page.evaluate(({ S, H0 }) => {
      const h = (window as any).__host, out: any[] = [];
      for (const F of ['ground', 'upper']) {
        const lv = S[F]!.level, H = S[F]!.height;
        for (const d of h.openings.filter((o: any) => o.floor === F && o.kind === 'door' && !o.glazed)) {
          const free = d.jambGap.some((g: unknown) => g === null), want = !free && d.head < H;
          const hit = h.cast(F, [d.x, lv + 0.5, -d.y], [0, 1, 0], 8);
          out.push({ id: d.id, floor: F, head: d.head, lintel: !!d.lintel, free, want, H, H0: H0[F]!.height, at: hit ? Math.round((hit.d + 0.5) * 1000) / 1000 : null, mesh: hit ? hit.name : null });
        }
      }
      return out;
    }, { S, H0 });
    return rows.map(r => ({ ...r, ok: r.lintel === (!r.free && r.head < r.H0 - 0.005)
      && (r.want ? meshIs(r.mesh, 'lintel') && Math.abs(r.at - r.head) < 0.02 : !r.mesh || !meshIs(r.mesh, 'lintel') || r.at >= r.H - 0.02) }));
  };
  const L0 = await lintels();
  expect(L0.filter(r => r.want).length).toBeGreaterThan(0);
  expect(L0.filter(r => !r.ok)).toEqual([]);
  if (!hasReplay) {
    test.info().annotations.push({ type: 'skipped', description: 'this house version has no replay data: no Build settings card to change the wall height (checked at the seeded store)' });
    return;
  }
  const setHeight = async (h: string) => {
    await page.locator(sel.replayOpen).click(); await sleep(300);
    await page.evaluate(({ s, v }) => { const e = document.querySelector(s) as HTMLInputElement; e.value = v; e.dispatchEvent(new Event('change')); }, { s: sel.replayInput('ground', 'height'), v: h });
    await page.locator(sel.replaySkipSettings).click(); await sleep(300);
  };
  const ground = async () => (await lintels()).filter(r => r.floor === 'ground');
  await setHeight('3.50');
  const L1 = await ground();
  await setHeight('2.00');
  const L2 = await ground();
  await setHeight('4.50');
  const L4 = await ground();
  const T4 = await page.evaluate(({ H, H0 }) => {
    const w = window as any, h = w.__host, lv = h.floors.find((f: any) => f.key === 'ground').level, out: any[] = [];
    for (const d of h.openings.filter((o: any) => o.floor === 'ground' && o.glazed && !o.lintel && o.head >= H0 - 0.005)) {
      for (const z of [H - 0.3, H - 0.05]) {
        const hit = h.cast('ground', [d.x - d.nx * 0.6, lv + z, -(d.y - d.ny * 0.6)], [d.nx, 0, -d.ny], 1.2);
        out.push({ id: d.id, z: Math.round(z * 100) / 100, mesh: hit ? hit.name : null });
      }
    }
    return out;
  }, { H: 4.5, H0: H0.ground!.height });
  await setHeight('3.90');
  const L3 = await ground();
  expect(L1.some(r => r.want) && L4.some(r => r.want)).toBe(true);
  expect({ at350: L1.filter(r => !r.ok).map(r => r.id), at200: L2.filter(r => r.want || !r.ok).map(r => r.id), at450: L4.filter(r => !r.ok).map(r => r.id), back: L3.filter(r => !r.ok).map(r => r.id) })
    .toEqual({ at350: [], at200: [], at450: [], back: [] });
  expect(T4.length).toBeGreaterThan(0);
  expect(T4.filter(r => !meshIs(r.mesh, 'pane'))).toEqual([]);
});

test('house: raising the ground level to 1.50 m keeps the plinth on the ground; a 2.00 m wall height makes the walls 2.00 m', async ({ page }) => {
  await open(page, 'house', '?nodownload=1&test=1');
  const hasReplay = await page.evaluate(() => !!(window as any).__build);
  test.skip(!hasReplay, 'this house version has no replay data: no Build settings card (checked at the seeded store)');
  const worldY = (expr: 'plinth' | 'wall') => page.evaluate(which => {
    const h = (window as any).__host;
    const m = which === 'plinth' ? h.plinths[0] : h.rise.ground.find((r: any) => r.scales).mesh;
    m.updateWorldMatrix(true, false); m.geometry.computeBoundingBox();
    const b = m.geometry.boundingBox.clone().applyMatrix4(m.matrixWorld);
    return [b.min.y as number, b.max.y as number];
  }, expr);
  const set = (s: string, v: string) => page.evaluate(({ s, v }) => { const e = document.querySelector(s) as HTMLInputElement; e.value = v; e.dispatchEvent(new Event('change')); }, { s, v });
  await set(sel.replayInput('ground', 'level'), '1.50');
  await page.locator(sel.replaySkipSettings).click(); await sleep(400);
  const [foot, plinthTop] = await worldY('plinth') as [number, number];
  expect(Math.abs(foot), `the plinth's foot at ${foot}`).toBeLessThan(0.01);
  expect(Math.abs(plinthTop - 1.5), `the plinth's top at ${plinthTop}`).toBeLessThan(0.01);
  await page.locator(sel.replayOpen).click(); await sleep(300);
  await set(sel.replayInput('ground', 'height'), '2.00');
  await page.locator(sel.replaySkipSettings).click(); await sleep(400);
  const wall = await worldY('wall');
  const [bottom, top] = wall as [number, number];
  expect(Math.abs(top - bottom - 2.0)).toBeLessThan(0.02);
  expect(Math.abs(bottom - 1.5)).toBeLessThan(0.02);
});

// ------------------------------------------------------------------------------------------------- fix step (3-4 Nov review)
// three 0.186 differs from the prototypes' three 0.160 in two places the viewer now evens out (core/sort.ts, controls.ts).

test(`house: in the first Walk view the single-line piece seen through a window pane is drawn after the pane, as on its page (three 0.160's transparent order) ${APP_ONLY}`, async ({ page }) => {
  const { p } = await open(page, 'house');
  await p.press('Digit2');
  await sleep(800);
  const r = await page.evaluate(async () => {
    const h = (window as any).__host, s = (window as any).__viewer.state;
    const scene = (Object.values(h.groups)[0] as any).parent;
    const order: string[] = [];
    const watched: { o: any; own: boolean; before: any }[] = [];
    scene.traverse((o: any) => { if (o.isMesh && o.visible && o.material?.transparent) watched.push({ o, own: Object.prototype.hasOwnProperty.call(o, 'onBeforeRender'), before: o.onBeforeRender }); });
    for (const { o, before } of watched) o.onBeforeRender = function (...a: unknown[]) { order.push(o.name); return before.apply(this, a); };
    await new Promise(res => requestAnimationFrame(() => requestAnimationFrame(res)));
    for (const { o, own, before } of watched) { if (own) o.onBeforeRender = before; else delete o.onBeforeRender; }   // as it was
    return { mode: s.mode, floor: s.floor.key, order: [...new Set(order)] };
  });
  expect([r.mode, r.floor]).toEqual(['walk', 'ground']);
  const pane = r.order.indexOf('ground pane:clip'), piece = r.order.indexOf('ground single:own');
  expect(pane >= 0 && piece >= 0, JSON.stringify(r.order)).toBe(true);
  // the pane's merged centre lies behind the eye here: three 0.160 drew it first (NDC depth > 1), 0.186 last (over the piece)
  expect(pane, JSON.stringify(r.order)).toBeLessThan(piece);
});

test(`suite: a touchpad pinch (ctrl + wheel, Ctrl not held) zooms Orbit as far as on its page, a mouse notch too ${APP_ONLY}`, async ({ page }) => {
  await open(page, 'suite');
  await sleep(600);
  const dist = () => page.evaluate(() => { const h = (window as any).__host; return h.camera.position.distanceTo(h.controls.target) as number; });
  const settle = async () => { let a = await dist(); for (let i = 0; i < 40; i++) { await sleep(150); const b = await dist(); if (Math.abs(a - b) < 1e-4) return b; a = b; } return a; };
  const cdp = await page.context().newCDPSession(page);
  const wheel = (deltaY: number, modifiers: number) => cdp.send('Input.dispatchMouseEvent', { type: 'mouseWheel', x: 800, y: 450, deltaX: 0, deltaY, modifiers });
  const ratio = await page.evaluate(() => devicePixelRatio);
  expect(ratio).toBe(1);
  const d0 = await settle();
  for (let i = 0; i < 10; i++) await wheel(-5, 2);                         // Edge sends a pinch as wheel + ctrlKey
  const d1 = await settle();
  // three 0.160: 0.95 ^ (|deltaY| / 100) per event, so x 0.95 ^ 0.5 for ten of -5 (three 0.186 gave x 0.774)
  expect(d1 / d0).toBeCloseTo(Math.pow(0.95, 0.5), 3);
  await wheel(100, 0);                                                     // one mouse notch out: x 1 / 0.95
  const d2 = await settle();
  expect(d2 / d1).toBeCloseTo(1 / 0.95, 3);
});
