// Furniture boxes and the side panel (builder C; DESIGN.md 17.4 "furniture"): the furniture checks of bank_test/test_bank.mjs,
// presidential_test/test_presidential.mjs, cad_test/test_house_furniture.mjs and hotel_test/test_hotel.mjs, ported once for
// the four furnished versions (bank v2, suite, house, hotel) and both targets (lib/target.ts):
//   E2E_TARGET=prototype  the prototype pages (their selectors, the shim; @app-only skipped)
//   E2E_TARGET=app        the offline files dist/offline/<project>-v<n>.html (?build=0&nodownload=1&test=1), or the same
//                         names in WT_OFFLINE_DIR when it is set (lib/target.ts pagePath: offline files made in a temp
//                         folder from the viewer as it is now, while nobody writes dist/; step BX, 16 Nov 2026)
// Run (builder C's row of DESIGN.md 3, Git Bash):
//   WT_WEB_PORT=5723 WT_TMP="$TEMP/wt-c" E2E_TARGET=prototype npx playwright test -c tests/e2e/playwright.config.ts --project=e2e tests/e2e/furniture.spec.ts
// On a builder's own offline files (the template built into its temp folder, make-offline.mjs over a seeded temp store):
//   WT_SERVE= WT_WEB_PORT=5750 WT_TMP="$TEMP/wt-bx" WT_SKIP_STORE_CHECK=1 WT_OFFLINE_DIR="$TEMP/wt-bx/offline" \
//     npx playwright test -c tests/e2e/playwright.config.ts --project=e2e tests/e2e/furniture.spec.ts
// Per version, on one page: the legend; one box per piece in its floor's group; the page's own ticks and floor buttons
// leave the boxes alone; the side panel at 1366 x 768 and 1920 x 1080 and above the hint line from 640 to 1080 px; typing
// a height with real keys (the tops follow, what stands on them follows); Walk starts clear of the boxes; Walk stops at real
// boxes short of the face; the doorways rule and the colliders against the approach lists; the show and stops ticks; a
// height under the knee ray stepped over; Ghost through two boxes (timed); the doors, the glass and 40 random walks with the
// boxes on; never trapped in a box; csv() equals the prototype CSV byte for byte; the hover label; and (@app-only) the
// storage key with the stamp. The model facts come from fixtures/models (the furniture is the same data on both targets).
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { expect, test, type Browser, type Page } from '@playwright/test';
import type { BuiltModel } from '../../packages/viewer/src/contracts';
import { timedDescribe } from './lib/fps';
import { sleep } from './lib/page';
import { APP, APP_ONLY, isApp, openVersion, sel, VERSIONS, type VersionKey } from './lib/target';
import { doorWalks, installPageHelpers, judgeHouseWalk, walkThrough, wallWalks } from './lib/walks';

/* eslint-disable @typescript-eslint/no-explicit-any */

interface Project {
  key: VersionKey; model: string; csv: string;
  /** typing check: the kind, the mm and the least number of spots on its tops; follows: kinds standing on it follow */
  type: { kind: string; mm: number; minSpots: (n: number) => number };
  /** Walk stops: least walks (of the targets) and covered kinds */
  minWalks: (targets: number) => number; minKinds: number;
  /** the kinds whose show / stops ticks and step-over height are walked (the first with 2 crossable pieces) */
  tickKinds: string[] | 'any';
  /** two kinds Ghost flies through (the first target of each, or of any two of these) */
  ghostKinds: string[];
  /** the kinds of the "switched on under you" scenarios */
  trapKinds: string[];
  minInBox: number;
  hoverFloor: string;
  /** a hover over a box in a doorway's approach is required (the suite's and the house's tests did) */
  doorHover: boolean;
  wallSeed: number;
}

const PROJECTS: Project[] = [
  { key: 'bank-v2', model: 'bank-v2', csv: 'bank-v2.csv', type: { kind: 'table', mm: 600, minSpots: () => 8 }, minWalks: () => 30, minKinds: 8,
    tickKinds: ['seat'], ghostKinds: ['table', 'cabinet'], trapKinds: ['seat', 'table', 'tall-cabinet'], minInBox: 20, hoverFloor: 'L1', doorHover: false, wallSeed: 7 },
  { key: 'suite', model: 'suite', csv: 'suite.csv', type: { kind: 'table', mm: 600, minSpots: n => n }, minWalks: () => 30, minKinds: 5,
    tickKinds: ['seat'], ghostKinds: ['table', 'tall-cabinet'], trapKinds: ['seat', 'table', 'tall-cabinet'], minInBox: 5, hoverFloor: 'suite', doorHover: true, wallSeed: 3 },
  { key: 'house', model: 'house', csv: 'house.csv', type: { kind: 'other', mm: 2100, minSpots: n => n }, minWalks: t => Math.ceil(t / 2), minKinds: 6,
    tickKinds: 'any', ghostKinds: ['counter', 'sofa', 'appliance', 'other'], trapKinds: ['sofa', 'sanitary', 'other'], minInBox: 10, hoverFloor: 'ground', doorHover: true, wallSeed: 7 },
  { key: 'hotel', model: 'hotel', csv: 'hotel.csv', type: { kind: 'table', mm: 600, minSpots: n => n }, minWalks: () => 20, minKinds: 4,
    tickKinds: ['seat', 'sofa', 'coffee-table', 'cabinet', 'counter'], ghostKinds: ['table', 'counter'], trapKinds: ['seat', 'table', 'cabinet'], minInBox: 10, hoverFloor: 'F1', doorHover: false, wallSeed: 7 },
];

const fixtureModel = (name: string) => JSON.parse(readFileSync(path.join(APP, 'fixtures/models', `${name}.model.json`), 'utf8')) as BuiltModel;
const fixtureCsv = (name: string) => readFileSync(path.join(APP, 'fixtures/csv', name));
const fixtureLegend = (ref: { projectId: string; version: number; key: VersionKey }) => {
  const file = ref.key.startsWith('bank') ? `${ref.projectId}-v${ref.version}` : ref.projectId;
  return (JSON.parse(readFileSync(path.join(APP, 'fixtures/presentation', `${file}.json`), 'utf8')) as { legend: { items: { text: string }[] } }).legend.items.map(i => i.text).join('');
};
const r2 = (v: number) => Math.round(v * 100) / 100;
const rowSel = (kind: string, part: 'kindShow' | 'kindHeight' | 'kindStops' | 'kindLabel' | 'kindSwatch') => `${sel.furnitureRow(kind)} ${sel[part]}`;
/** Walk stops at ~0.3 m: short of the face, never inside, never through. */
const stopped = (w: any) => w.start && w.gap >= 0.1 && w.gap <= 0.5 && !w.inside && w.moved >= 0.1;
/** Right across the box and out the other side. */
const passed = (w: any) => w.start && w.moved >= w.metres - 0.01 && w.gap < -0.2;
const num = (x: unknown): x is number => typeof x === 'number';

// ---------------------------------------------------------------------------------------------- page helpers (both targets)
async function F<T>(page: Page, fn: string): Promise<T> { return page.evaluate(`(() => { const F = window.__host.furniture; return ${fn}; })()`) as Promise<T>; }
async function T<T>(page: Page, fn: string): Promise<T> { return page.evaluate(`(() => { const T = window.__t; return ${fn}; })()`) as Promise<T>; }
async function clickSel(page: Page, selector: string) {
  await page.evaluate(s => document.querySelector(s)!.scrollIntoView({ block: 'center' }), selector);
  await sleep(60);
  await page.locator(selector).first().click();
  await sleep(80);
}
/** Click into a height box (the number is selected), type with real keys, Enter: the keyboard goes back to the viewer. */
async function typeHeight(page: Page, kind: string, mm: number) {
  await clickSel(page, rowSel(kind, 'kindHeight'));
  await page.keyboard.type(String(mm));
  await page.keyboard.press('Enter');
  await sleep(80);
}
const blur = (page: Page) => page.evaluate(() => { (document.activeElement as HTMLElement | null)?.blur?.(); });
const press = async (page: Page, key: string) => { await blur(page); await page.keyboard.press(key); await sleep(120); };
const setAllShown = (page: Page, on: boolean) => F(page, `F.kinds().forEach(k => F.setVisible(k.key, ${on}))`);

/** window.__fh: what the checks below read that lib/walks.ts does not have, on both targets (no __host.upHit / downHit on the
 *  suite and house prototype pages): a look down at a spot, the spots on a kind's tops, a glass walk, a box's screen spot. */
function installFurnitureHelpers(page: Page): Promise<boolean> {
  return page.evaluate(() => {
    const w = window as any, THREE = w.__walkthrough.THREE, F = w.__host.furniture, v = w.__viewer, s = v.state, V3 = THREE.Vector3;
    const ray = new THREE.Raycaster();
    const levelOf = (key: string) => w.__host.floors.find((f: any) => f.key === key).level;
    const showing = (o: any) => { for (let n = o; n; n = n.parent) if (!n.visible) return false; return true; };
    // looking straight down from 2.5 m above the floor at a plan spot: the first visible collider (the boxes that stop you among them)
    function downAt(floor: string, x: number, y: number) {
      const cols = w.__host.FL[floor].colliders.filter((m: any) => m.visible);
      ray.set(new V3(x, levelOf(floor) + 2.5, -y), new V3(0, -1, 0)); ray.far = 4;
      const hit = ray.intersectObjects(cols, false)[0];
      return hit ? { h: Math.round((2.5 - hit.distance) * 1000) / 1000, name: hit.object.name } : null;
    }
    // per piece of a kind: a spot on its top where the look down meets that piece's own top first
    function topSpots(kind: string) {
      return F.pieces().filter((p: any) => p.kind === kind).map((p: any) => {
        const r = p.rot * Math.PI / 180, ax = [Math.cos(r), Math.sin(r)], az = [-Math.sin(r), Math.cos(r)], name = F.meshOf(p.id).name;
        const spot = [[0, 0], [p.w / 4, 0], [-p.w / 4, 0], [0, p.d / 4], [0, -p.d / 4]].map(([a, b]) => [p.x + ax[0]! * a! + az[0]! * b!, p.y + ax[1]! * a! + az[1]! * b!])
          .find(([x, y]) => { const d = downAt(p.floor, x!, y!); return d && d.name === name && Math.abs(d.h - p.z1) < 0.005; });
        return { id: p.id, floor: p.floor, name, spot: spot || null };
      });
    }
    // walk straight at each glass probe of the floor you are on, from 1.0 m (or nearer): how short of the glass you stop
    function glassWalks() {
      const keep = s.pos.clone(), out: any[] = [];
      for (const g of w.__host.probes) {
        if (g.floor !== s.floor.key) continue;
        for (const side of g.inside) {
          const nx = g.nx * side, ny = g.ny * side, deg = Math.atan2(nx, -ny) * 180 / Math.PI;
          let res: number | null = null; const tries: any[] = [];
          for (const back of [1.0, 0.8, 0.6]) {
            s.pos.x = g.x + nx * back; s.pos.z = -(g.y + ny * back);
            if (!v.probe.onFloor() || v.probe.clearance() < 0.25) { tries.push({ back, near: w.__t.near(g.floor, s.pos.x, s.pos.z, 0.3) }); continue; }
            v.probe.walk(deg, 2.0);
            res = Math.round(((s.pos.x - g.x) * nx + (-s.pos.z - g.y) * ny) * 100) / 100;
            tries.push({ back, res, stoppedBy: w.__t.stoppedBy(g.floor, s.pos.x, s.pos.z, deg) });
            break;
          }
          out.push({ id: g.id, what: g.what, side, stoppedAt: res, ok: res !== null && res > 0.1 && res < 0.6, tries });
        }
      }
      s.pos.copy(keep); return out;
    }
    // the Orbit view the page opens with (read here, right after the load), to come back to for the label: the Walk starts of
    // the checks below move the Orbit target (cad_test/test_house_furniture.mjs goHome)
    const home = { p: w.__host.camera.position.toArray(), t: w.__host.controls.target.toArray() };
    function goHome() {
      v.setMode('orbit');
      w.__host.camera.position.fromArray(home.p); w.__host.controls.target.fromArray(home.t); w.__host.controls.update();
    }
    // the house test's hoverSpots: per kind asked for (in that order), the biggest box of the floor the Orbit camera sees, nothing
    // opaque in front of its top middle (glass and other half see-through things do not hide it), as a pointer position
    function kindSpots(floor: string, kinds: string[], max: number) {
      const cam = w.__host.camera, out: any[] = [], want = new THREE.Vector2();
      const hides = Object.values(w.__host.FL).flatMap((f: any) => f.colliders.concat(f.walkables)).filter((m: any) => showing(m) && !m.name.startsWith('furn:') && !m.material.transparent);
      const boxes = F.pieces().map((b: any) => F.meshOf(b.id)).filter(showing);
      for (const kind of kinds) {
        if (out.length >= max) break;
        const mine = F.pieces().filter((p: any) => p.floor === floor && p.visible && p.kind === kind).sort((a: any, b: any) => b.w * b.d - a.w * a.d);
        for (const p of mine) {
          const m = F.meshOf(p.id), q = new V3(p.x, levelOf(floor) + p.z1, -p.y).project(cam);
          const x = (q.x + 1) / 2 * innerWidth, y = (1 - q.y) / 2 * innerHeight;
          if (q.z > 1 || x < 400 || x > innerWidth - 20 || y < 50 || y > innerHeight - 70) continue;
          ray.setFromCamera(want.set(q.x, q.y), cam); ray.far = Infinity;
          const hit = ray.intersectObjects(hides.concat(boxes), false)[0];
          if (hit && hit.object === m) { out.push({ id: p.id, kind: p.kind, family: p.family, floor, approach: p.approach, x, y, size: `${p.w.toFixed(2)} × ${p.d.toFixed(2)} × ${(p.z1 - p.z0).toFixed(2)} m` }); break; }
        }
      }
      return out;
    }
    // the screen spot of a box's top middle when the Orbit camera sees it there (nothing in front of it), else null
    function spotOf(id: string) {
      const cam = w.__host.camera, p = F.pieces().find((q: any) => q.id === id), m = F.meshOf(id);
      if (!p || !showing(m)) return null;
      const hides = Object.values(w.__host.FL).flatMap((f: any) => f.colliders.concat(f.walkables)).filter((x: any) => showing(x) && !x.name.startsWith('furn:') && !x.material.transparent && x.material.visible !== false);
      const boxes = F.pieces().map((b: any) => F.meshOf(b.id)).filter(showing);
      const q = new V3(p.x, levelOf(p.floor) + p.z1, -p.y).project(cam), x = (q.x + 1) / 2 * innerWidth, y = (1 - q.y) / 2 * innerHeight;
      if (q.z > 1 || x < 400 || x > innerWidth - 20 || y < 50 || y > innerHeight - 70) return null;
      ray.setFromCamera(new THREE.Vector2(q.x, q.y), cam); ray.far = Infinity;
      const hits = ray.intersectObjects(hides.concat(boxes), false), hit = hits[0];
      // A box whose top lies in one plane with another box's (the house's L-shaped sofa is two overlapping blocks, both
      // 0.80 m high): which of the two the ray meets first is floating-point noise, so a box among the nearest hits of
      // furniture counts as seen (integration: three 0.186 broke that tie the other way from the page's 0.160).
      const seen = !!hit && (hit.object === m || (hit.object.name.startsWith('furn:') && hits.some((h: any) => h.object === m && h.distance - hit.distance < 1e-4)));
      return seen ? { id: p.id, kind: p.kind, family: p.family, approach: p.approach, x, y, size: `${p.w.toFixed(2)} × ${p.d.toFixed(2)} × ${(p.z1 - p.z0).toFixed(2)} m` } : null;
    }
    w.__fh = { downAt, topSpots, glassWalks, spotOf, levelOf, goHome, kindSpots };
    return true;
  });
}

/** Opens a version, forgets stored furniture state, and installs the page helpers. */
async function openFurnished(page: Page, key: VersionKey) {
  await openVersion(page, key);
  await page.evaluate(() => { try { Object.keys(localStorage).filter(k => k.startsWith('walkthrough-furniture')).forEach(k => localStorage.removeItem(k)); } catch { /* blocked */ } });
  await openVersion(page, key);
  expect(await installPageHelpers(page)).toBe(true);
  expect(await installFurnitureHelpers(page)).toBe(true);
}
const errorsOf = (page: Page) => { const e: string[] = []; page.on('pageerror', x => e.push(String(x))); return e; };

for (const pr of PROJECTS) {
  const ref = VERSIONS[pr.key];
  const M = fixtureModel(pr.model);
  const kinds = M.furnitureKinds!, pieces = M.furniture!;
  const inApproach = pieces.filter(p => p.approach.length);
  const blocksKind = Object.fromEntries(kinds.map(k => [k.key, k.blocks]));
  const nBlocking = pieces.filter(p => blocksKind[p.kind]).length;

  test.describe(`furniture: ${pr.key}`, () => {
    let page: Page;
    let errors: string[] = [];
    test.beforeAll(async ({ browser }: { browser: Browser }) => {
      page = await browser.newPage();
      errors = errorsOf(page);
      await openFurnished(page, pr.key);
    });
    test.afterAll(async () => { await page?.close(); });
    test.beforeEach(async () => {
      await page.setViewportSize({ width: 1400, height: 880 });
      await page.evaluate(() => { (window as any).__viewer.setMode('orbit'); });
      if (ref.floors.length > 1) await clickSel(page, sel.floorButton('all'));
      await F(page, 'F.setKeepDoorways(true)');
      await setAllShown(page, true);
    });

    test('the legend: one row per kind in table order with label (count), colour, default height, show and stops ticks; Keep doorways clear ticked', async () => {
      const legend = await page.evaluate(s => {
        const rows = [...document.querySelectorAll(s.row)];
        const keep = document.querySelector<HTMLInputElement>(s.keep);
        return {
          title: document.querySelector(s.title)!.textContent, master: !!document.querySelector(s.all), note: document.querySelector(s.note)!.textContent,
          keep: keep && { checked: keep.checked, text: keep.closest('label')!.textContent!.trim(), title: keep.closest('label')!.title, n: document.querySelectorAll(s.keep).length },
          buttons: [...document.querySelectorAll(s.buttons + ' button')].map(b => (b as HTMLElement).innerText),
          rows: rows.map(r => ({ label: (r.querySelector(s.label) as HTMLElement).innerText, sw: getComputedStyle(r.querySelector(s.sw)!).backgroundColor,
            h: (r.querySelector(s.h) as HTMLInputElement).value, type: (r.querySelector(s.h) as HTMLInputElement).type, show: (r.querySelector(s.show) as HTMLInputElement).checked,
            blk: (r.querySelector(s.blk) as HTMLInputElement).checked })),
        };
      }, { row: sel.furnitureRow('').replace('=""', ''), keep: sel.furnitureKeep, title: sel.furnitureTitle, all: sel.furnitureAll, note: sel.furnitureNote, buttons: sel.furnitureButtons,
        label: sel.kindLabel, sw: sel.kindSwatch, h: sel.kindHeight, show: sel.kindShow, blk: sel.kindStops });
      const rgb = (hex: string) => `rgb(${[1, 3, 5].map(i => parseInt(hex.slice(i, i + 2), 16)).join(', ')})`;
      expect(legend.title).toBe('Furniture boxes');
      expect(legend.note).toBe('Type a height in mm for each kind. Walk: boxes stop you; Ghost passes through.');
      expect(legend.master).toBe(true);
      expect(legend.buttons).toEqual(['Reset heights', 'Save list (CSV)']);
      expect(legend.keep).toEqual({ checked: true, text: 'Keep doorways clear', n: 1,
        title: `${inApproach.length} of the boxes stand in front of a door or a passage. Ticked: Walk is not stopped by them (they stay drawn), so every doorway can be walked through. Unticked: they stop you like any other box.` });
      expect(legend.rows).toEqual(kinds.map(k => ({ label: `${k.label} (${k.count})`, sw: rgb(k.colour), h: String(k.height), type: 'text', show: true, blk: k.blocks })));
      expect(kinds.reduce((n, k) => n + k.count, 0)).toBe(pieces.length);
    });

    test('one box per piece, a child of its own floor group, named furn:<kind>:<id>', async () => {
      const made = await page.evaluate(() => {
        const w = window as any, FL = w.__host.FL, Fu = w.__host.furniture, byId = Object.fromEntries(Fu.pieces().map((p: any) => [p.id, p])), bad: string[] = [], names = new Set<string>(), per: Record<string, number> = {};
        let n = 0;
        for (const [key, f] of Object.entries<any>(FL)) f.group.traverse((o: any) => {
          if (!o.name.startsWith('furn:')) return;
          n++; names.add(o.name); per[key] = (per[key] || 0) + 1;
          const [, kind, id] = o.name.split(':'), p = byId[id];
          if (!p || p.kind !== kind || p.floor !== key || o.parent !== f.group || Fu.meshOf(id) !== o || !f.late.includes(o)) bad.push(o.name);
        });
        return { n, distinct: names.size, per, bad };
      });
      expect(made.bad).toEqual([]);
      expect(made.n).toBe(pieces.length);
      expect(made.distinct).toBe(pieces.length);
      expect(made.per).toEqual(Object.fromEntries(ref.floors.map(k => [k, pieces.filter(p => p.floor === k).length])));
    });

    test("the page's own ticks and floor buttons leave the boxes alone; the legend is as it was; the furniture list is last in the panel", async () => {
      const toggles = await page.evaluate(s => s.names.filter(n => !!document.querySelector(s.toggle.replace('@', n))), { names: ['plates', 'glass', 'rooms', 'single', 'picture'], toggle: sel.toggle('@' as any) });
      const own = await page.evaluate(({ s, toggles, floors }) => {
        const w = window as any, Fu = w.__host.furniture, ms = Fu.pieces().map((p: any) => Fu.meshOf(p.id));
        const showing = (m: any) => { for (let n = m; n; n = n.parent) if (!n.visible) return false; return true; };
        const count = () => ms.filter(showing).length, click = (n: string) => (document.querySelector(s.toggle.replace('@', n)) as HTMLElement).click(), out: any = {};
        const ticks = () => toggles.map(n => (document.querySelector(s.toggle.replace('@', n)) as HTMLInputElement).checked);
        out.ticks0 = ticks();
        out.start = count();
        for (const n of toggles) click(n);
        out.ticksOff = count();
        for (const n of toggles) click(n);
        out.ticksOn = count();
        const plant = Fu.kinds().find((k: any) => k.key === 'plant') ? 'plant' : Fu.kinds()[0].key;
        Fu.setVisible(plant, false); click('plates'); click('glass'); click('plates'); click('glass');
        out.hidden = { kind: plant, n: count() };
        Fu.setVisible(plant, true);
        out.perFloor = {};
        for (const [key, fs] of Object.entries<string>(floors)) { (document.querySelector(fs) as HTMLElement).click(); out.perFloor[key] = ms.filter(showing).length; }
        const panel = document.querySelector(s.panel)!, last = panel.lastElementChild!, lg = panel.querySelector(s.legend)!;
        out.fbLast = last.matches(s.block) || !!last.querySelector(':scope > ' + s.block);
        const again = document.querySelector(s.again);
        out.buildBefore = again ? !!(again.compareDocumentPosition(last) & Node.DOCUMENT_POSITION_FOLLOWING) : null;
        out.legendHasFurniture = !!lg.querySelector(s.block) || /furniture/i.test(lg.textContent!);
        out.legendText = lg.textContent;
        out.ticks = ticks();
        return out;
      }, { s: { toggle: sel.toggle('@' as any), panel: sel.panel, legend: sel.legend, block: sel.furniture, again: sel.replayAgain }, toggles,
        floors: ref.floors.length > 1 ? Object.fromEntries([...ref.floors, 'all'].map(k => [k, sel.floorButton(k)])) : {} });
      expect(own.start).toBe(pieces.length);
      expect(own.ticksOff).toBe(pieces.length);
      expect(own.ticksOn).toBe(pieces.length);
      expect(own.hidden.n).toBe(pieces.length - pieces.filter(p => p.kind === own.hidden.kind).length);
      if (ref.floors.length > 1) {
        for (const k of ref.floors) expect(own.perFloor[k]).toBe(pieces.filter(p => p.floor === k).length);
        expect(own.perFloor.all).toBe(pieces.length);
      }
      expect(own.fbLast).toBe(true);
      if (ref.hasReplay) expect(own.buildBefore).toBe(true);
      expect(own.legendHasFurniture).toBe(false);
      expect(own.legendText).toBe(fixtureLegend(ref));
      expect(own.ticks).toEqual(own.ticks0);
      expect(own.ticks0).toEqual(toggles.map(n => n !== 'picture'));
    });

    test('the side panel at 1366 x 768 and 1920 x 1080, and its bottom edge above the hint line from 640 to 1080 px', async () => {
      const s = { panel: sel.panel, row: sel.furnitureRow('').replace('=""', ''), label: sel.kindLabel, h: sel.kindHeight, show: sel.kindShow, blk: sel.kindStops,
        save: sel.furnitureSave, reset: sel.furnitureReset, hint: sel.hint, heading: sel.heading, block: sel.furniture };
      for (const [w, h] of [[1366, 768], [1920, 1080]] as const) {
        await page.setViewportSize({ width: w, height: h });
        await sleep(600);
        const m = await page.evaluate(s => {
          const p = document.querySelector<HTMLElement>(s.panel)!, r = p.getBoundingClientRect(), cs = getComputedStyle(p);
          const rows = [...document.querySelectorAll<HTMLElement>(s.row)], lab = [...document.querySelectorAll<HTMLElement>(s.label)];
          const inP = (e: Element) => { const b = e.getBoundingClientRect(), q = p.getBoundingClientRect(); return b.top >= q.top - 0.5 && b.bottom <= q.bottom + 0.5 && b.left >= q.left - 0.5 && b.right <= q.right + 0.5; };
          const out: any = { onScreen: r.top >= 0 && r.left >= 0 && r.bottom <= innerHeight && r.right <= innerWidth, scrolls: p.scrollHeight > p.clientHeight + 1, overflowY: cs.overflowY,
            content: p.scrollHeight, shown: p.clientHeight, hintGap: Math.round((document.querySelector(s.hint)!.getBoundingClientRect().top - r.bottom) * 10) / 10 };
          p.scrollTop = 0; out.titleVisible = inP(p.querySelector(s.heading)!);
          p.scrollTop = p.scrollHeight; out.lastRowReachable = inP(rows[rows.length - 1]!) && inP(document.querySelector(s.save)!) && inP(document.querySelector(s.reset)!);
          p.querySelector(s.block)!.scrollIntoView({ block: 'start' });
          out.cut = lab.filter(e => { const t = document.createRange(); t.selectNodeContents(e); return t.getBoundingClientRect().width > e.getBoundingClientRect().width + 0.01; }).map(e => e.textContent);
          out.rowH = Math.round(Math.min(...rows.map(e => e.getBoundingClientRect().height)));
          out.fontPx = Math.min(...lab.map(e => parseFloat(getComputedStyle(e).fontSize)));
          out.boxesIn = rows.every(e => inP(e.querySelector(s.h)!) && inP(e.querySelector(s.blk)!) && inP(e.querySelector(s.show)!));
          p.scrollTop = 0;
          return out;
        }, s);
        test.info().annotations.push({ type: `panel ${w}x${h}`, description: JSON.stringify(m) });
        expect(m.onScreen).toBe(true);
        expect(!m.scrolls || /auto|scroll/.test(m.overflowY)).toBe(true);
        expect(m.titleVisible).toBe(true);
        expect(m.lastRowReachable).toBe(true);
        expect(m.cut).toEqual([]);
        expect(m.rowH).toBeGreaterThanOrEqual(22);
        expect(m.fontPx).toBeGreaterThanOrEqual(12);
        expect(m.boxesIn).toBe(true);
        expect(m.hintGap).toBeGreaterThanOrEqual(4);
      }
      const gaps: [string, number][] = [];
      for (const [w, h] of [[1366, 640], [1366, 700], [1280, 800], [1600, 900], [1920, 1080]] as const) {
        await page.setViewportSize({ width: w, height: h });
        await sleep(350);
        gaps.push([`${w}x${h}`, await page.evaluate(s => Math.round((document.querySelector(s.hint)!.getBoundingClientRect().top - document.querySelector(s.panel)!.getBoundingClientRect().bottom) * 10) / 10, s)]);
      }
      test.info().annotations.push({ type: 'hint gaps', description: JSON.stringify(gaps) });
      expect(gaps.filter(([, g]) => g < 4)).toEqual([]);
    });

    test(`typing ${pr.type.mm} into the ${pr.type.kind} box with real keys moves its tops (and what stands on them); Reset brings it all back`, async () => {
      const { kind, mm } = pr.type;
      const dflt = kinds.find(k => k.key === kind)!.height;
      const kindById = Object.fromEntries(pieces.map(p => [p.id, p.kind]));
      const onIt = pieces.filter(p => p.on && kindById[p.on] === kind).map(p => p.id);
      const rest = pieces.filter(p => p.kind !== kind && !(p.on && kindById[p.on] === kind)).map(p => p.id);
      const spots = (await page.evaluate(k => (window as any).__fh.topSpots(k), kind)).filter((t: any) => t.spot);
      interface Readings { down: (number | null)[]; own: number[][]; on: number[][]; rest: number[][]; box: string; edited: number }
      const readings = (): Promise<Readings> => page.evaluate(({ spots, onIt, rest, s, kind }) => {
        const w = window as any, Fu = w.__host.furniture, fh = w.__fh, pcs = Object.fromEntries(Fu.pieces().map((p: any) => [p.id, p]));
        return {
          down: spots.map((t: any) => { const d = fh.downAt(t.floor, t.spot[0], t.spot[1]); return d && d.name === t.name ? d.h : null; }),
          own: Fu.pieces().filter((p: any) => p.kind === kind).map((p: any) => [p.z0, p.z1]),
          on: onIt.map((id: string) => [pcs[id].z0, Math.round((Fu.meshOf(id).position.y - fh.levelOf(pcs[id].floor)) * 1000) / 1000]),
          rest: rest.map((id: string) => [pcs[id].z0, pcs[id].z1]),
          box: (document.querySelector(s.h) as HTMLInputElement).value, edited: [...document.querySelectorAll(s.anyH)].filter(e => s.app ? e.hasAttribute('data-edited') : e.classList.contains('fb-edited')).length,
        };
      }, { spots, onIt, rest, kind, s: { h: rowSel(kind, 'kindHeight'), anyH: sel.kindHeight, app: isApp } });
      const before = await readings();
      await typeHeight(page, kind, mm);
      const after = await readings();
      await clickSel(page, sel.furnitureReset);
      const reset = await readings();
      const near = (a: number | null | undefined, b: number, tol = 0.006) => typeof a === 'number' && Math.abs(a - b) <= tol;
      test.info().annotations.push({ type: 'tops', description: JSON.stringify({ spots: spots.length, of: pieces.filter(p => p.kind === kind).length, onIt: onIt.length, after: after.down.slice(0, 4) }) });
      expect(spots.length).toBeGreaterThanOrEqual(pr.type.minSpots(pieces.filter(p => p.kind === kind && !p.approach.length).length));
      expect(before.down.every(z => near(z, dflt / 1000))).toBe(true);
      expect(after.down.every(z => near(z, mm / 1000))).toBe(true);
      expect(after.own.every(([z0, z1]: number[]) => z0 === 0 && near(z1, mm / 1000, 1e-9))).toBe(true);
      expect(after.on.every(([z0, y]: number[]) => near(z0, mm / 1000, 1e-9) && near(y, mm / 1000, 0.002))).toBe(true);
      expect(after.rest).toEqual(before.rest);
      expect([after.box, after.edited]).toEqual([String(mm), 1]);
      expect(reset.down.every(z => near(z, dflt / 1000))).toBe(true);
      expect([reset.box, reset.edited]).toEqual([String(dflt), 0]);
      expect(reset.on.every(([z0]: number[]) => near(z0, dflt / 1000, 1e-9))).toBe(true);
      expect(await page.evaluate(() => { try { return Object.keys(localStorage).filter(k => k.startsWith('walkthrough-furniture')).length; } catch { return -1; } })).toBe(0);
    });

    test('Walk starts clear of the boxes wherever the Orbit view looks (30 spots): on its floor, 0.5 m of room, never held by a box', async () => {
      const per = Math.round(30 / ref.floors.length);
      const starts = await page.evaluate(({ floors, per, floorSels }) => {
        const w = window as any, v = w.__viewer, s = v.state, out: any[] = [];
        let seed = 11; const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
        for (const key of floors) {
          v.setMode('orbit');
          if (floors.length > 1) (document.querySelector(floorSels[key]!) as HTMLElement).click();
          const b = new w.__walkthrough.THREE.Box3().setFromObject(w.__host.FL[key].group);
          for (let i = 0; i < per; i++) {
            v.setMode('orbit'); w.__host.controls.target.set(b.min.x + rnd() * (b.max.x - b.min.x), 1, b.min.z + rnd() * (b.max.z - b.min.z));
            v.setMode('walk');
            const vd = w.__t.verdict();
            out.push({ want: key, floor: s.floor.key, clearance: Math.min(99, v.probe.clearance()), onFloor: v.probe.onFloor(), inBox: vd.inside, class: vd.class, best: vd.best });
          }
        }
        v.setMode('orbit');
        if (floors.length > 1) (document.querySelector(floorSels.all!) as HTMLElement).click();
        return out;
      }, { floors: ref.floors, per, floorSels: Object.fromEntries([...ref.floors, 'all'].map(k => [k, sel.floorButton(k)])) });
      test.info().annotations.push({ type: 'starts', description: `${starts.length} spots, ${starts.filter((r: any) => r.inBox.length).length} inside a box` });
      expect(starts.length).toBe(per * ref.floors.length);
      expect(starts.filter((r: any) => r.floor !== r.want || !r.onFloor || r.clearance < 0.5 || r.class !== 'A')).toEqual([]);
    });

    test("Walk stops at real boxes short of the face, never inside; the doorways rule (on: the boxes in an approach do not stop you, off: they do)", async () => {
      test.setTimeout(300_000);
      await press(page, 'Digit2');
      await page.evaluate(k => (window as any).__viewer.goToFloor(k), ref.floors[0]!);
      const tg: any[] = await T(page, 'T.targets()');
      const walks: any[] = [];
      for (const t of tg.filter(x => x.side !== null)) walks.push({ ...(await T<any>(page, `T.walk(window.__host.furniture.pieces().find(p => p.id === ${JSON.stringify(t.id)}), ${t.side}, ${t.back}, false)`)), kind: t.kind });
      const covered = [...new Set(walks.map(w => w.kind))];
      test.info().annotations.push({ type: 'walks', description: `${walks.length} of ${tg.length} targets, ${covered.length} kinds; gaps ${r2(Math.min(...walks.map(w => w.gap)))} - ${r2(Math.max(...walks.map(w => w.gap)))} m` });
      expect(walks.length).toBeGreaterThanOrEqual(pr.minWalks(tg.length));
      expect(covered.length).toBeGreaterThanOrEqual(pr.minKinds);
      expect(walks.filter(w => !stopped(w))).toEqual([]);
      // the boxes in an approach are no targets while the doorways are kept clear; all the others Walk's rays can meet are
      const flagged = inApproach.map(p => p.id);
      expect(tg.filter(t => flagged.includes(t.id))).toEqual([]);
      expect(tg.length).toBe(await F<number>(page, `F.pieces().filter(p => p.blocking && ((p.z0 < 0.33 && p.z1 > 0.37) || (p.z0 < 1.18 && p.z1 > 1.22))).length`));
      await F(page, 'F.setKeepDoorways(false)');
      const tgOff: any[] = await T(page, 'T.targets()');
      const fTargets = tgOff.filter(t => t.side !== null && flagged.includes(t.id));
      const fOff: any[] = [];
      for (const t of fTargets) fOff.push(await T(page, `T.walk(window.__host.furniture.pieces().find(p => p.id === ${JSON.stringify(t.id)}), ${t.side}, ${t.back}, false)`));
      await F(page, 'F.setKeepDoorways(true)');
      const fOn: any[] = [];
      for (const t of fTargets) fOn.push(await T(page, `T.walkTo(window.__host.furniture.pieces().find(p => p.id === ${JSON.stringify(t.id)}), ${t.side}, ${t.back}, ${t.back + 0.5})`));
      // the box is no collider: the walk gets over its face line, or comes at least 0.2 m nearer than where the box stopped it (a wall right behind)
      const noStop = (w: any, off: any) => w.gap < -0.05 || (off && w.gap <= off.gap - 0.2);
      test.info().annotations.push({ type: 'doorway boxes', description: JSON.stringify({ flagged: flagged.length, freeLine: fTargets.length, off: fOff.map(w => r2(w.gap)), on: fOn.map(w => r2(w.gap)) }) });
      expect(fTargets.length).toBeGreaterThanOrEqual(1);
      expect(fOff.filter(w => !stopped(w))).toEqual([]);
      expect(fOn.filter((w, i) => !noStop(w, fOff[i]))).toEqual([]);
      await press(page, 'Digit1');
    });

    test('the colliders against the approach lists: tick on, the pieces with an approach are out and the others of blocking kinds in; off, all in', async () => {
      const rule = await page.evaluate(({ kb, s }) => {
        const w = window as any, Fu = w.__host.furniture, FL = w.__host.FL;
        const inCol = () => new Set(Object.values<any>(FL).flatMap(f => f.colliders.filter((m: any) => m.name.startsWith('furn:')).map((m: any) => m.userData.id)));
        const state = (keep: boolean) => { Fu.setKeepDoorways(keep); const c = inCol(), ps = Fu.pieces(); return ps.filter((p: any) => kb[p.kind]).map((p: any) => [p.id, c.has(p.id), p.approach.length > 0, p.blocking]); };
        const out: any = { on: state(true), off: state(false) };
        Fu.setKeepDoorways(true);
        out.keep = Fu.keepDoorways(); out.checked = document.querySelector<HTMLInputElement>(s)!.checked;
        out.lists = Fu.pieces().map((p: any) => p.id + ':' + p.approach.join());
        return out;
      }, { kb: blocksKind, s: sel.furnitureKeep });
      expect(rule.on.length).toBe(nBlocking);
      expect(rule.on.filter(([, inCol, flagged, blocking]: any[]) => inCol === flagged || blocking !== inCol)).toEqual([]);
      expect(rule.off.filter(([, inCol, , blocking]: any[]) => !inCol || !blocking)).toEqual([]);
      expect([rule.keep, rule.checked]).toEqual([true, true]);
      expect(rule.lists).toEqual(pieces.map(p => p.id + ':' + p.approach.join()));
    });

    test('show off and stops off (real clicks): the same walks go right through, drawn or not; a height under the knee ray is stepped over', async () => {
      test.setTimeout(240_000);
      await press(page, 'Digit2');
      let kind: string | null = null, boxes: any[] = [];
      const candidates = pr.tickKinds === 'any'
        ? (await T<string[]>(page, `[...new Set(T.targets().filter(t => t.side !== null).map(t => t.kind))]`)).filter(k => k !== 'other')
        : pr.tickKinds;
      for (const k of candidates) { boxes = await T(page, `T.crossable(${JSON.stringify(k)}, 3)`); if (boxes.length >= 2) { kind = k; break; } }
      expect(kind, `a kind with 2 boxes to walk across among ${candidates.join(', ')}`).not.toBeNull();
      const walkBox = (c: any, through: boolean) => T<any>(page, `T.walk(window.__host.furniture.pieces().find(p => p.id === ${JSON.stringify(c.id)}), ${c.side}, ${c.back}, ${through}, ${through ? JSON.stringify(kind) : 'null'})`);
      const out: any[] = [];
      for (const c of boxes) {
        const r: any = { id: c.id };
        for (const part of ['kindShow', 'kindStops'] as const) {
          r[part] = { stops: stopped(await walkBox(c, false)) };
          await clickSel(page, rowSel(kind!, part));
          r[part].through = passed(await walkBox(c, true));
          r[part].state = await F(page, `({ collider: window.__host.FL[${JSON.stringify(c.floor)}].colliders.includes(F.meshOf(${JSON.stringify(c.id)})), drawn: F.meshOf(${JSON.stringify(c.id)}).visible })`);
          await clickSel(page, rowSel(kind!, part));
          r[part].stopsAgain = stopped(await walkBox(c, false));
        }
        out.push(r);
      }
      test.info().annotations.push({ type: 'ticks', description: JSON.stringify({ kind, out }) });
      for (const r of out) {
        for (const part of ['kindShow', 'kindStops']) expect([r[part].stops, r[part].through, r[part].state.collider, r[part].stopsAgain]).toEqual([true, true, false, true]);
        expect([r.kindShow.state.drawn, r.kindStops.state.drawn]).toEqual([false, true]);
      }
      // 300 mm: the knee ray at 0.35 m passes over it; the kind's own height stops you again
      const dflt = kinds.find(k => k.key === kind)!.height;
      const heights: any[] = [];
      for (const mm of [300, dflt]) {
        await typeHeight(page, kind!, mm);
        const w: any[] = [];
        for (const c of boxes) w.push(mm === 300 ? await walkBox(c, true) : await walkBox(c, false));
        heights.push([mm, w.every(x => (mm === 300 ? passed(x) : stopped(x)))]);
      }
      await clickSel(page, sel.furnitureReset);
      expect(heights).toEqual([[300, true], [dflt, true]]);
      await press(page, 'Digit1');
    });

    test('with the boxes on: the doors as without them (the doorways kept clear), and off only the doors an approach list names are blocked', async () => {
      test.setTimeout(300_000);
      await press(page, 'Digit2');
      const house = pr.key === 'house';
      const walkFloor = async (key: string) => {
        await page.evaluate(k => (window as any).__viewer.goToFloor(k), key);
        if (!house) return doorWalks(page, { why: true, ...(pr.key === 'suite' ? { backs: [0.9, 0.7, 0.55] } : {}) });
        const list = await page.evaluate(k => (window as any).__host.openings.filter((o: any) => o.floor === k && (o.kind === 'door' || o.kind === 'passage') && !o.glazed), key);
        return (await walkThrough(page, list)).map(r => ({ id: r.id as string, kind: r.kind as string, ok: judgeHouseWalk(r) !== 'blocked', verdict: judgeHouseWalk(r), fwd: r.fwd, back: r.back }));
      };
      const walkAll = async () => { const out: any[] = []; for (const k of ref.floors) out.push(...await walkFloor(k)); return out; };
      await setAllShown(page, false);
      const bare = await walkAll();
      await setAllShown(page, true);
      const withBoxes = await walkAll();
      await F(page, 'F.setKeepDoorways(false)');
      const off = await walkAll();
      await F(page, 'F.setKeepDoorways(true)');
      const okBare = (id: string) => bare.find(b => b.id === id)!.ok;
      const cut = withBoxes.filter(d => !d.ok && okBare(d.id));
      const blockedOff = off.filter(d => !d.ok && okBare(d.id));
      const flaggedFor = (id: string) => inApproach.filter(p => p.approach.includes(id)).map(p => p.id);
      test.info().annotations.push({ type: 'doors', description: JSON.stringify({ openings: bare.length, openBare: bare.filter(b => b.ok).length, cutWithBoxes: cut.map(d => d.id), blockedOff: blockedOff.map(d => `${d.id} <- ${flaggedFor(d.id).join(', ')}`) }) });
      expect(withBoxes.length).toBe(bare.length);
      expect(bare.length).toBeGreaterThan(0);
      expect(cut.map(d => d.id)).toEqual([]);
      expect(blockedOff.filter(d => flaggedFor(d.id).length === 0).map(d => d.id)).toEqual([]);
      if (house) {                                     // no door or passage harder to walk through than without the boxes (both ways > from the floor side > blocked)
        const RANK: Record<string, number> = { blocked: 0, 'from the floor side': 1, 'both ways': 2 };
        const worse = (walks: any[]) => walks.filter(r => { const b = bare.find(x => x.id === r.id)!; return r.verdict in RANK && b.verdict in RANK && RANK[r.verdict]! < RANK[b.verdict]!; });
        expect(worse(withBoxes).map(r => r.id)).toEqual([]);
        expect(worse(off).filter(r => flaggedFor(r.id).length === 0).map(r => r.id)).toEqual([]);
      }
      if (pr.key === 'bank-v2') expect(blockedOff.filter(d => d.kind === 'door').length).toBeGreaterThanOrEqual(1);
      await press(page, 'Digit1');
    });

    test('with the boxes on: the glass (or the windows) still stops you, and 40 random walks at the nearest wall or box never go through', async () => {
      test.setTimeout(240_000);
      await press(page, 'Digit2');
      if (pr.key === 'house') {
        const out: any[] = [];
        for (const k of ref.floors) {
          await page.evaluate(key => (window as any).__viewer.goToFloor(key), k);
          const win = await page.evaluate(key => (window as any).__host.openings.filter((o: any) => o.floor === key && (o.kind === 'window' || o.glazed)), k);
          out.push(...(await walkThrough(page, win)).flatMap(r => [['fwd', r.floorNeg], ['back', r.floorPos]].filter(([, has]) => has).map(([side]) => ({ id: r.id, side, along: r[side as 'fwd' | 'back'] }))));
        }
        test.info().annotations.push({ type: 'windows', description: `${out.length} walks, ${out.filter(w => num(w.along)).length} from a free start` });
        expect(out.length).toBeGreaterThan(0);
        expect(out.filter(w => num(w.along) && (w.along as number) > -0.1)).toEqual([]);
      } else {
        const glass: any[] = [];
        for (const k of ref.floors) { await page.evaluate(key => (window as any).__viewer.goToFloor(key), k); glass.push(...await page.evaluate(() => (window as any).__fh.glassWalks())); }
        const reach = glass.filter(g => g.stoppedAt !== null);
        test.info().annotations.push({ type: 'glass', description: `${reach.length} of ${glass.length} glass sides reached; ${glass.filter(g => !g.ok).map(g => `${g.id}/${g.side}: ${g.stoppedAt}`).join(', ')}` });
        expect(glass.length).toBeGreaterThan(0);
        expect(reach.length).toBeGreaterThan(0);
        expect(reach.filter(g => g.stoppedAt <= 0.1)).toEqual([]);
      }
      const walls: any[] = [];
      for (const k of ref.floors) {
        await page.evaluate(key => (window as any).__viewer.goToFloor(key), k);
        walls.push(await wallWalks(page, { seed: pr.wallSeed, outsideBoxes: true, maxTries: pr.key === 'suite' ? 6000 : 8000 }));
      }
      test.info().annotations.push({ type: 'random walks', description: JSON.stringify(walls) });
      expect(walls.map(w => w.floor)).toEqual(ref.floors);
      expect(walls.filter(w => w.tried < 30 || w.wentThrough || w.endedInsideWall)).toEqual([]);
      await press(page, 'Digit1');
    });

    test('never trapped: Walk entered at the middle of every box that stops you, or a box switched on under you, and you walk out', async () => {
      test.setTimeout(300_000);
      await press(page, 'Digit2');
      await F(page, 'F.setKeepDoorways(false)');
      const mids: string[] = await F(page, 'F.pieces().filter(p => p.blocking).map(p => p.id)');
      const into: any[] = await page.evaluate(ids => {
        const w = window as any, out: any[] = [];
        for (const id of ids) { w.__t.spawn(id); out.push({ id, ...w.__t.verdict() }); }
        w.__viewer.setMode('orbit'); w.__viewer.setMode('walk'); return out;
      }, mids);
      await F(page, 'F.setKeepDoorways(true)');
      const inBox = into.filter(r => r.inside.length), held = into.filter(r => r.class === 'C');
      test.info().annotations.push({ type: 'spawned', description: `${mids.length} boxes, ${inBox.length} inside a box, pockets ${into.filter(r => r.class === 'B').map(r => r.id).join(', ') || 'none'}` });
      expect(mids.length).toBe(nBlocking);
      expect(inBox.length).toBeGreaterThanOrEqual(pr.minInBox);
      expect(held).toEqual([]);
      const scenarios: any[] = [];
      for (const kind of pr.trapKinds) {
        const plain = pieces.find(p => p.kind === kind && !p.approach.length && (pr.key !== 'bank-v2' || p.floor === 'L1'));
        if (!plain) continue;
        scenarios.push(...await page.evaluate(({ id, kind }) => {
          const w = window as any, Fu = w.__host.furniture, T = w.__t, out: any[] = [], h = Fu.kinds().find((k: any) => k.key === kind).height;
          const run = (name: string, prepare: () => void, on: () => void) => { prepare(); T.standIn(id); const before = T.holding().includes(id); on(); out.push({ label: `${kind}/${name}`, id, before, ...T.verdict() }); };
          run('show', () => Fu.setVisible(kind, false), () => Fu.setVisible(kind, true));
          run('stops', () => Fu.setBlocks(kind, false), () => Fu.setBlocks(kind, true));
          run('height', () => Fu.setHeight(kind, 100), () => Fu.setHeight(kind, Math.max(450, h)));
          Fu.reset(); return out;
        }, { id: plain.id, kind }));
      }
      const doorways: any[] = await page.evaluate(() => {
        const w = window as any, Fu = w.__host.furniture, T = w.__t, out: any[] = [];
        const spans = (q: any) => (q.z0 < 0.33 && q.z1 > 0.37) || (q.z0 < 1.18 && q.z1 > 1.22);          // Walk's rays can meet it
        for (const p of Fu.pieces().filter((q: any) => q.approach.length && q.blocks && spans(q))) { Fu.setKeepDoorways(true); T.standIn(p.id); const before = T.holding().includes(p.id); Fu.setKeepDoorways(false); out.push({ label: p.id, id: p.id, before, ...T.verdict() }); }
        Fu.setKeepDoorways(true); return out;
      });
      const around = (r: any) => r.before === false && r.inside.includes(r.id);
      expect(scenarios.length).toBeGreaterThanOrEqual(6);
      expect([...scenarios, ...doorways].filter(r => !around(r) || r.class === 'C').map(r => r.label)).toEqual([]);
      expect(doorways.length).toBeGreaterThanOrEqual(1);
      await press(page, 'Digit1');
    });

    test("csv() equals the prototype's family list byte for byte (no byte-order mark), and its approach notes", async () => {
      await F(page, 'F.reset()');
      const text = await F<string>(page, 'F.csv()');
      const file = fixtureCsv(pr.csv);
      expect([...file.subarray(0, 3)]).toEqual([0xef, 0xbb, 0xbf]);
      expect(Buffer.from(text, 'utf8').equals(file.subarray(3))).toBe(true);
      expect(text.split('\r\n').filter(l => l.includes('in the approach of')).length).toBe(inApproach.length);
      expect(await F<boolean>(page, 'F.saveCsv() === F.csv()')).toBe(true);          // nodownload=1: nothing downloaded, the text returned
    });

    test('the hover label in Orbit: kind, family, size and floor; a box in a doorway\'s approach says it does not stop you, and why', async () => {
      await press(page, 'Digit1');
      await page.evaluate(() => (window as any).__fh.goHome());           // the view the page opened with (the Walk starts above moved the Orbit target)
      if (ref.floors.length > 1) await clickSel(page, sel.floorButton(pr.hoverFloor));
      await sleep(500);
      const floorName = await page.evaluate(k => (window as any).__host.floors.find((f: any) => f.key === k).name, pr.hoverFloor);
      // the house test: a grey box first, then one of each kind the camera sees, glass hiding nothing (test_house_furniture.mjs);
      // the bank, suite and hotel tests: one box per kind, the biggest first (lib/walks.ts hoverSpots, as their pageHelpers)
      const house = pr.key === 'house';
      const spots: any[] = house
        ? await page.evaluate(({ floor, order }) => (window as any).__fh.kindSpots(floor, order, 5), { floor: pr.hoverFloor, order: ['other', ...kinds.map(k => k.key).filter(k => k !== 'other')] })
        : await T(page, `T.hoverSpots(${JSON.stringify(pr.hoverFloor)}, 4)`);
      // and one box in a doorway's approach (the suite's test always; the house's when none of the spots above is one)
      const seenDoor = spots.some(s => (pieces.find(p => p.id === s.id)?.approach.length ?? 0) > 0 && blocksKind[s.kind]);
      const door: any = house && seenDoor ? null : await page.evaluate(ids => { for (const id of ids) { const s = (window as any).__fh.spotOf(id); if (s) return s; } return null; },
        inApproach.filter(p => p.floor === pr.hoverFloor && blocksKind[p.kind] && !spots.some(s => s.id === p.id)).map(p => p.id));
      const tipNow = () => page.evaluate(s => { const t = document.querySelector<HTMLElement>(s); return t && t.style.display === 'block' ? t.innerText : null; }, sel.furnitureTip);
      const named = kinds.filter(k => k.key !== 'other').map(k => k.label);
      const hovers: any[] = [];
      for (const sp of [...spots.map(s => ({ ...s, door: false })), ...(door ? [{ ...door, door: true }] : [])]) {
        await page.mouse.move(1250, 40);
        for (let i = 0; i < 20 && (await tipNow()) !== null; i++) await sleep(100);
        await page.mouse.move(sp.x, sp.y);
        let tip: string | null = null;
        for (let i = 0; i < 30 && tip === null; i++) { await sleep(100); tip = await tipNow(); }
        const flat = (x: unknown) => String(x).replace(/\s+/g, ' '), t = tip && flat(tip), label = kinds.find(k => k.key === sp.kind)!.label;
        // the doorway line shows for a box in an approach whose kind stops you (the doorways are kept clear), and only then
        const piece = pieces.find(p => p.id === sp.id)!, kept = blocksKind[piece.kind]! && piece.approach.length > 0;
        const why = `does not stop you: in the approach of ${piece.approach.join(', ')}`;
        // the house test: a label names no kind but its own (so a grey box's names no other kind)
        const claims = t && house ? named.filter(n => n !== label && t.includes(n)) : [];
        hovers.push({ id: sp.id, kind: sp.kind, door: sp.door, kept, tip: t, claims, ok: !!t && t.includes(label) && t.includes(flat(sp.family)) && t.includes(sp.size) && t.includes(floorName)
          && t.includes(why) === kept && (kept || !t.includes('does not stop you')) && (!sp.door || kept) && !claims.length });
      }
      await page.mouse.move(1250, 40);
      if (ref.floors.length > 1) await clickSel(page, sel.floorButton('all'));
      test.info().annotations.push({ type: 'hovers', description: JSON.stringify(hovers) });
      if (house) {
        expect(spots.length, 'the house test: a grey box and three more kinds').toBeGreaterThanOrEqual(4);
        expect(spots[0]!.kind).toBe('other');
      } else expect(spots.length).toBeGreaterThanOrEqual(3);
      if (pr.doorHover) expect(hovers.some(h => h.kept), 'a box in a doorway\'s approach the Orbit camera sees').toBe(true);
      expect(hovers.filter(h => !h.ok)).toEqual([]);
    });

    test('the storage key carries the stamp: <prefix><photoName>:<stamp>, only the changed heights, removed after Reset', { tag: APP_ONLY }, async () => {
      const stamp = await page.evaluate(() => document.querySelector('[data-wt=root]')!.getAttribute('data-model-stamp'));
      const key = `walkthrough-furniture-heights:${M.photoName}:${stamp}`;
      const kind = kinds.find(k => k.key === 'table')?.key ?? kinds[0]!.key;
      await typeHeight(page, kind, 640);
      const stored = await page.evaluate(() => Object.fromEntries(Object.keys(localStorage).filter(k => k.startsWith('walkthrough-furniture')).map(k => [k, localStorage.getItem(k)])));
      await clickSel(page, sel.furnitureReset);
      const after = await page.evaluate(() => Object.keys(localStorage).filter(k => k.startsWith('walkthrough-furniture')));
      expect(stamp).toMatch(/^[0-9a-f]{12}$/);
      expect(stored).toEqual({ [key]: JSON.stringify({ [kind]: 640 }) });
      expect(after).toEqual([]);
    });

    test('no page errors', async () => {
      expect(errors).toEqual([]);
    });
  });

  timedDescribe(`furniture (timed): ${pr.key}`, () => {
    test('Ghost flies straight through two real boxes that stop Walk short of their face, at half their height', async ({ page }) => {
      test.setTimeout(180_000);
      await openFurnished(page, pr.key);
      await press(page, 'Digit2');
      const tg: any[] = await T(page, 'T.targets()');
      const picks: any[] = [];
      for (const k of pr.ghostKinds) { const t = tg.find(x => x.kind === k && x.side !== null); if (t && picks.length < 2) picks.push(t); }
      expect(picks.length, `free lines to two of ${pr.ghostKinds.join(', ')}`).toBe(2);
      const ghost: any[] = [];
      for (const pick of picks) {
        await press(page, 'Digit2');
        const pc = `window.__host.furniture.pieces().find(p => p.id === ${JSON.stringify(pick.id)})`;
        const stop = await T<any>(page, `T.walk(${pc}, ${pick.side}, ${pick.back}, false)`);
        const L = await T<any>(page, `T.lane(${pc}, ${pick.side}, 1.5, false)`);
        await press(page, 'Digit3');
        await page.evaluate(`(() => { const p = ${pc}, s = window.__viewer.state; s.pos.set(${L.start[0]}, window.__t.levelOf(p.floor) + (p.z0 + p.z1) / 2, ${L.start[1]}); s.yaw = Math.atan2(${L.n[0]}, ${L.n[2]}); s.pitch = 0; })()`);
        await page.keyboard.down('KeyW');
        let at: any = null;
        for (let i = 0; i < 160; i++) {
          await sleep(125);
          at = await T(page, `T.along(${JSON.stringify(pick.id)}, ${pick.side})`);
          if (at.rel < -(at.half + 0.3)) break;
        }
        await page.keyboard.up('KeyW');
        ghost.push({ id: pick.id, kind: pick.kind, walkStops: stopped(stop), beyond: r2(-at.rel - at.half), inside: at.y > at.z0 && at.y < at.z1 });
      }
      await press(page, 'Digit1');
      test.info().annotations.push({ type: 'ghost', description: JSON.stringify(ghost) });
      expect(ghost.filter(g => !g.walkStops || g.beyond < 0.3 || !g.inside)).toEqual([]);
    });
  });
}
