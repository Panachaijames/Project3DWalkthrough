// U7 (docs/upload/ACCEPTANCE.md A-6, 2.4 U7): the walk checks on every uploaded version, run on its offline HTML file
// opened from disk (the file make-offline.mjs made from the store). Generic: written and first run against the seeded
// dist/offline/bank-sampeng-v2.html; at integration pointed at the uploaded versions' files (bank re-upload, house, suite,
// tower) by WT_UPLOAD_OFFLINE_DIR. Per file:
//   loads   with no error and no network; one canvas; the stamp meta equals version.json's stamp and line 2 of the
//           version's 3ds Max script (read from the store, WT_UPLOAD_DATA_DIR)
//   floors  the floor buttons and PgUp / PgDn change floor (a one-floor version has no buttons and keeps its floor)
//   start   at 1400 x 880 the start view shows every slab corner inside the canvas, clear of the side panel (U-11.2:
//           the fitSlabs camera of an uploaded version; for a version with a fixed camera, as the seeded bank, it is
//           reported, not judged)
//   walls   walls stop you at 40 random spots per floor: never through, never inside
//   doors   every door is walkable through its middle both ways (exterior doors from inside); passages are reported
//   glass   glass stops you at every probe and at 10 random glass parts (seeded) on each floor that has any
// The walls, doors and glass are judged with every furniture kind hidden, as the foundation's structure.spec.ts does.
//
// Environment:
//   WT_UPLOAD_OFFLINE_DIR  folder of <projectId>-v<n>.html files: every .html in it is checked (default: the seeded
//                          dist/offline/bank-sampeng-v2.html alone)
//   WT_UPLOAD_DATA_DIR     the store those files were made from, for the .ms (default app/data)
//   WT_UPLOAD_WALK_SHOULD  comma list of file names without .html, or project ids, whose walk checks are "must run,
//                          should pass" (A-6: the house, the suite, the tower): their failing probes are recorded, the
//                          test passes; the loading and stamp checks still must pass. Every other file must pass all.
// Every probe of every check is written to <WT_TMP>/upload-walk/<file>.json (merged per check) for docs/upload/GAPS.md.
//   WT_WEB_PORT=5737 WT_TMP="$TEMP/wt-u7" WT_SERVE=none WT_SKIP_STORE_CHECK=1 \
//     npx playwright test -c tests/e2e/playwright.config.ts --project=e2e tests/e2e/upload-walk.spec.ts
// (WT_SERVE=none: no server is needed; an empty WT_SERVE works in Git Bash, but PowerShell drops an empty variable and the
// config then starts the API and the web server.)
//
// The rooms milestone (R7, 11 Nov 2026; docs/rooms/ACCEPTANCE.md RA-2, RA-6, 2.4). The eight old uploaded versions run
// as before (their reports compare with docs/rooms/reference/upload-walk-9nov/ check by check). The new-rule versions
// (a model with `stairways`) run the same checks from their own store and offline folder (WT_UPLOAD_DATA_DIR,
// WT_UPLOAD_OFFLINE_DIR) and, with
//   WT_ROOMS_PROBES        1 (fixtures/rooms/keys/probes.json) or the path of a probes key,
// one check more per file: the walk probes that found no floor at their start on 9 Nov, found again by floor and sheet
// point (ids are running counts and may have moved): on each side that had no floor there must now be floor 0.4 - 0.9 m
// in front of the opening (the key's grade: "must" fails the test, "should" records), and the walk from there is
// recorded for docs/rooms/GAPS.md, which classes the ones that still fail for another reason. A probe a decision took
// out of RA-6 is recorded, not judged (the house's ground-034: a garden gate with no floor either side, R1.md D-2). A file
// of an old-rule version, or of a drawing the key does not hold, records why it was not judged. Without WT_ROOMS_PROBES
// that check is not defined, so a plain run is the upload milestone's.
import { existsSync, mkdirSync, readdirSync, readFileSync, writeFileSync } from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { expect, test, type Page, type TestInfo } from '@playwright/test';
import { pageApi, sleep, type PageApi } from './lib/page';
import { APP, noNetwork, sel, waitReady } from './lib/target';
import { doorWalks, glassWalks, wallWalks } from './lib/walks';

/* eslint-disable @typescript-eslint/no-explicit-any */

const DIR = process.env.WT_UPLOAD_OFFLINE_DIR ? path.resolve(process.env.WT_UPLOAD_OFFLINE_DIR) : null;
const DATA = path.resolve(process.env.WT_UPLOAD_DATA_DIR ?? path.join(APP, 'data'));
const SHOULD = new Set((process.env.WT_UPLOAD_WALK_SHOULD ?? '').split(',').map(s => s.trim()).filter(Boolean));
const REPORT = path.join(process.env.WT_TMP ?? path.join(os.tmpdir(), 'wt-e2e'), 'upload-walk');
const FILES: string[] = DIR
  ? (existsSync(DIR) ? readdirSync(DIR).filter(f => f.toLowerCase().endsWith('.html')).sort().map(f => path.join(DIR, f)) : [])
  : [path.join(APP, 'dist', 'offline', 'bank-sampeng-v2.html')];
const QUERY = '?build=0&nodownload=1&test=1';

const PROBES_KEY = !process.env.WT_ROOMS_PROBES ? null
  : process.env.WT_ROOMS_PROBES === '1' ? path.join(APP, 'fixtures', 'rooms', 'keys', 'probes.json') : path.resolve(process.env.WT_ROOMS_PROBES);
/** Probes taken out of RA-6 by a decision: recorded, not judged (drawing -> 9 Nov ids). */
const NOT_JUDGED: Record<string, string[]> = { house: ['ground-034'] };

const baseOf = (file: string) => path.basename(file).replace(/\.html$/i, '');
const projectOf = (base: string) => base.replace(/-v\d+$/, '');
const isShould = (file: string) => SHOULD.has(baseOf(file)) || SHOULD.has(projectOf(baseOf(file)));

/** Merges one check's results into the file's report. */
function record(file: string, check: string, result: unknown): void {
  mkdirSync(REPORT, { recursive: true });
  const out = path.join(REPORT, `${baseOf(file)}.json`);
  const prev = existsSync(out) ? JSON.parse(readFileSync(out, 'utf8')) : { file, should: isShould(file) };
  prev[check] = result;
  writeFileSync(out, JSON.stringify(prev, null, 2) + '\n', 'utf8');
}

/** A walk check's verdict: must files fail the test; "should" files record the failures and pass. */
function judge(file: string, info: TestInfo, check: string, failures: unknown[], detail: unknown): void {
  record(file, check, { ok: failures.length === 0, failures, detail });
  if (failures.length && isShould(file)) {
    info.annotations.push({ type: `should: ${check}`, description: `${failures.length} failing: ${JSON.stringify(failures).slice(0, 1500)}` });
    return;
  }
  expect(failures, `${baseOf(file)} ${check}`).toEqual([]);
}

interface Opened { p: PageApi; requests: string[]; problems: () => string[] }
async function open(page: Page, file: string): Promise<Opened> {
  const p = await pageApi(page);
  const net = await noNetwork(page);
  await page.goto(pathToFileURL(file).href + QUERY);
  await waitReady(page);
  const problems = () => p.logs.filter(l => (l.startsWith('[exception]') || l.startsWith('[console.error]')) && !/favicon/i.test(l));
  return { p, requests: net.requests, problems };
}
const floorsOf = (page: Page) => page.evaluate(() => ((window as any).__host.floors as { key: string; level: number }[]).map(f => ({ key: f.key, level: f.level })));
const setFurniture = (page: Page, on: boolean) => page.evaluate(show => {
  const F = (window as any).__host.furniture;
  if (F) for (const k of F.kinds()) F.setVisible(k.key, show);
}, on);
const walkOn = (page: Page, key: string) => page.evaluate(k => {
  const v = (window as any).__viewer;
  if (v.mode !== 'walk') v.setMode('walk');
  v.goToFloor(k);
  return v.state.floor.key as string;
}, key);
const st = (page: Page) => page.evaluate(() => {
  const s = (window as any).__viewer.state;
  return { mode: s.mode as string, floor: s.floor.key as string };
});
const visibleFloors = (page: Page) => page.evaluate(() => (window as any).__viewer.probe.visible() as string[]);
const clickSel = async (page: Page, selector: string) => {
  await page.locator(selector).first().scrollIntoViewIfNeeded();
  await page.locator(selector).first().click();
  await sleep(200);
};

test.describe.configure({ mode: 'default' });

if (!FILES.length) {
  test('upload-walk: offline files to check', () => {
    throw new Error(`no .html files in WT_UPLOAD_OFFLINE_DIR=${DIR ?? ''} (make them with make-offline.mjs from the acceptance store)`);
  });
}

for (const file of FILES) {
  const name = baseOf(file);
  const tag = isShould(file) ? ' (should pass)' : '';

  test.describe(`${name}${tag}`, () => {
    test(`${name}: loads from disk with no error and no network; the stamp meta is the version's and its 3ds Max script's`, async ({ page }) => {
      expect(existsSync(file), `${file} exists`).toBe(true);
      const { requests, problems } = await open(page, file);
      const facts = await page.evaluate(meta => {
        const data = document.getElementById('wtv-data');
        let version: any = null;
        try { version = data ? JSON.parse(data.textContent ?? '').version : null; } catch { version = null; }
        const e = document.querySelector('[data-wt=error]') as HTMLElement | null;
        return {
          meta: document.querySelector(meta)?.getAttribute('content') ?? null, canvas: document.querySelectorAll('canvas').length,
          error: !!e && getComputedStyle(e).display !== 'none' && !e.hidden,
          projectId: version?.projectId ?? null, version: version?.version ?? null, stamp: version?.stamp ?? null,
          maxScript: version?.downloads?.maxScript ?? null,
        };
      }, sel.stampMeta);
      await sleep(300);
      const ms = facts.maxScript && facts.projectId
        ? path.join(DATA, 'projects', facts.projectId, 'versions', String(facts.version), 'downloads', facts.maxScript) : null;
      const line2 = ms && existsSync(ms) ? readFileSync(ms, 'utf8').split(/\r?\n/)[1] ?? '' : null;
      const msStamp = line2 === null ? null : /\(model data ([0-9a-f]{12})\)/.exec(line2)?.[1] ?? null;
      record(file, 'loads', { ...facts, requests, problems: problems(), maxScriptFile: ms, maxScriptStamp: msStamp });
      expect(facts.canvas).toBe(1);
      expect(facts.error).toBe(false);
      expect(requests).toEqual([]);
      expect(problems()).toEqual([]);
      expect(facts.stamp).toMatch(/^[0-9a-f]{12}$/);
      expect(facts.meta).toBe(facts.stamp);
      expect(facts.maxScript, 'the version has a 3ds Max script').toBeTruthy();
      expect(line2, `${ms} is in the store (set WT_UPLOAD_DATA_DIR to the store the offline files came from)`).not.toBeNull();
      expect(msStamp).toBe(facts.stamp);
    });

    test(`${name}: at 1400 x 880 the start view shows every slab corner inside the canvas, clear of the panel`, async ({ page }, info) => {
      await open(page, file);
      await sleep(300);
      const r = await page.evaluate(sels => {
        const w = window as any, h = w.__host, T = w.__walkthrough.THREE;
        const canvas = document.querySelector('canvas') as HTMLCanvasElement, c = canvas.getBoundingClientRect();
        const panel = (document.querySelector(sels.panel) as HTMLElement | null)?.getBoundingClientRect() ?? null;
        const levels = Object.fromEntries((h.model.floors as { key: string; level: number }[]).map(f => [f.key, f.level]));
        const pres = (() => { try { return JSON.parse(document.getElementById('wtv-data')!.textContent ?? '').version.presentation; } catch { return null; } })();
        h.camera.updateMatrixWorld();
        const corners: { floor: string; x: number; y: number; px: number; py: number }[] = [];
        for (const p of h.model.parts) {
          if (p.kind !== 'slab') continue;
          for (const z of [p.z0, p.z1]) for (const [x, y] of p.o) {
            const q = new T.Vector3(x, levels[p.floor] + z, -y).project(h.camera);
            corners.push({ floor: p.floor, x, y, px: c.left + (q.x + 1) / 2 * c.width, py: c.top + (1 - q.y) / 2 * c.height });
          }
        }
        return { canvas: [c.left, c.top, c.right, c.bottom], panel: panel ? [panel.left, panel.top, panel.right, panel.bottom] : null,
          camera: pres?.camera?.kind ?? 'unknown', corners, size: [innerWidth, innerHeight] };
      }, { panel: sel.panel });
      expect(r.size).toEqual([1400, 880]);
      expect(r.corners.length).toBeGreaterThan(0);
      const [cl, ct, cr, cb] = r.canvas as [number, number, number, number];
      const pn = r.panel as [number, number, number, number] | null;
      // the panel sits at one side; the corners must be in the canvas and on the free side of it
      const [x0, x1] = !pn ? [cl, cr] : pn[0] - cl < cr - pn[2] ? [Math.max(cl, pn[2]), cr] : [cl, Math.min(cr, pn[0])];
      const outside = r.corners.filter(k => !(k.px >= x0 && k.px <= x1 && k.py >= ct && k.py <= cb))
        .map(k => ({ floor: k.floor, at: [k.x, k.y], px: [Math.round(k.px), Math.round(k.py)] }));
      const detail = { camera: r.camera, canvas: r.canvas, panel: r.panel, free: [x0, ct, x1, cb], corners: r.corners.length };
      if (r.camera !== 'fitSlabs') {
        record(file, 'start', { ok: outside.length === 0, judged: false, failures: outside, detail });
        info.annotations.push({ type: 'start view (information)', description: `${r.camera} camera, not judged: ${outside.length} of ${r.corners.length} corners outside ${JSON.stringify(detail)}` });
        return;
      }
      judge(file, info, 'start', outside, detail);
    });

    test(`${name}: the floor buttons and PgUp / PgDn change floor`, async ({ page }, info) => {
      const { p, problems } = await open(page, file);
      const floors = await floorsOf(page);
      const failures: unknown[] = [];
      const buttons = await page.locator(sel.floorButtons).count();
      if (floors.length < 2) {
        await p.press('Digit2');
        const s0 = await st(page);
        await p.press('PageUp'); const su = await st(page);
        await p.press('PageDown'); const sd = await st(page);
        if (s0.floor !== floors[0]!.key || su.floor !== floors[0]!.key || sd.floor !== floors[0]!.key) failures.push({ oneFloor: [s0, su, sd] });
        judge(file, info, 'floors', failures, { floors, buttons });
        return;
      }
      const [f1, f2] = [floors[0]!.key, floors[1]!.key];
      await clickSel(page, sel.floorButton(f1));
      const v1 = await visibleFloors(page);
      await clickSel(page, sel.floorButton(f2));
      const v2 = await visibleFloors(page);
      await clickSel(page, sel.floorButton('all'));
      const vb = await visibleFloors(page);
      if (JSON.stringify(v1) !== JSON.stringify([f1])) failures.push({ orbit: f1, visible: v1 });
      if (JSON.stringify(v2) !== JSON.stringify([f2])) failures.push({ orbit: f2, visible: v2 });
      if (vb.length !== floors.length) failures.push({ orbit: 'all', visible: vb });
      await p.press('Digit2');
      const s0 = await st(page);
      if (s0.mode !== 'walk' || s0.floor !== f1) failures.push({ walk: s0 });
      await clickSel(page, sel.floorButton(f2));
      const s2 = await st(page);
      if (s2.floor !== f2) failures.push({ button: f2, now: s2 });
      await page.locator(sel.floorButton(f2)).blur();
      await p.press('PageDown'); const sd = await st(page);
      await p.press('PageUp'); const su = await st(page);
      if (sd.floor !== f1) failures.push({ pageDown: sd });
      if (su.floor !== f2) failures.push({ pageUp: su });
      judge(file, info, 'floors', failures, { floors, buttons });
      expect(problems()).toEqual([]);
    });

    test(`${name}: walls stop you at 40 random spots per floor, never through, never inside`, async ({ page }, info) => {
      test.setTimeout(300_000);
      await open(page, file);
      await setFurniture(page, false);
      const failures: unknown[] = [], results: unknown[] = [];
      for (const f of await floorsOf(page)) {
        expect(await walkOn(page, f.key)).toBe(f.key);
        const w = await wallWalks(page, { seed: 7, maxTries: 8000 });
        results.push(w);
        if (w.wentThrough || w.endedInsideWall || w.tried < 30) failures.push(w);
      }
      judge(file, info, 'walls', failures, results);
    });

    test(`${name}: every door can be walked through its middle both ways (exterior doors from inside)`, async ({ page }, info) => {
      test.setTimeout(300_000);
      await open(page, file);
      await setFurniture(page, false);
      const all = [];
      for (const f of await floorsOf(page)) {
        expect(await walkOn(page, f.key)).toBe(f.key);
        all.push(...await doorWalks(page, { why: false }));
      }
      const doors = all.filter(d => d.kind === 'door'), passages = all.filter(d => d.kind === 'passage');
      info.annotations.push({ type: 'doors', description: `${doors.filter(d => d.ok).length} of ${doors.length} doors walked; passages (information) ${passages.filter(d => d.ok).length} of ${passages.length}` });
      judge(file, info, 'doors', doors.filter(d => !d.ok), { doors: doors.length, passages: passages.map(d => ({ id: d.id, ok: d.ok, fwd: d.fwd, back: d.back })) });
    });

    test(`${name}: glass stops you at every probe and at 10 random glass parts`, async ({ page }, info) => {
      test.setTimeout(300_000);
      await open(page, file);
      await setFurniture(page, false);
      const probes: any[] = [], parts: any[] = [];
      for (const f of await floorsOf(page)) {
        expect(await walkOn(page, f.key)).toBe(f.key);
        probes.push(...await glassWalks(page));
        parts.push(...await randomGlassWalks(page, f.key, 10, 11));
      }
      const failures = [...probes.filter(g => !g.ok).map(g => ({ probe: g.id, side: g.side, stoppedAt: g.stoppedAt, ahead: g.ahead })),
        ...parts.filter(g => !g.ok)];
      info.annotations.push({ type: 'glass', description: `${probes.length} probe walks, ${parts.length} random glass parts walked (${parts.filter(g => g.ok).length} stop you)` });
      judge(file, info, 'glass', failures, { probes: probes.length, parts });
    });

    if (PROBES_KEY) {
      test(`${name}: RA-6: the probes that found no floor on 9 Nov stand on floor now (a new-rule version of a drawing in the key)`, async ({ page }, info) => {
        test.setTimeout(300_000);
        expect(existsSync(PROBES_KEY), `${PROBES_KEY} (WT_ROOMS_PROBES)`).toBe(true);
        const key = JSON.parse(readFileSync(PROBES_KEY, 'utf8'));
        await open(page, file);
        await setFurniture(page, false);
        const facts = await page.evaluate(() => {
          const h = (window as any).__host;
          let projectId: string | null = null;
          try { projectId = JSON.parse(document.getElementById('wtv-data')!.textContent ?? '').version.projectId; } catch { projectId = null; }
          return { newRule: 'stairways' in h.model, source: (h.model.source ?? []) as string[], offset: (h.model.offset ?? [0, 0]) as [number, number], projectId };
        });
        // the drawing: the key's project id, or the same source file names as its *-rooms settings fixture
        const drawing = Object.keys(key.drawings).find(d => {
          if (key.drawings[d].project === facts.projectId) return true;
          const fx = path.join(APP, 'fixtures', 'upload', 'settings', `${d}-rooms.json`);
          if (!existsSync(fx)) return false;
          const names = (JSON.parse(readFileSync(fx, 'utf8')).sources as { name: string }[]).map(s => s.name).sort();
          return JSON.stringify(names) === JSON.stringify([...facts.source].sort());
        }) ?? null;
        if (!facts.newRule || !drawing) {
          const why = !facts.newRule ? 'an old-rule version (no stairways): not judged' : 'no drawing of the key: not judged';
          record(file, 'ra6', { judged: false, why, ...facts });
          info.annotations.push({ type: 'RA-6', description: why });
          return;
        }
        const d = key.drawings[drawing], skip = new Set(NOT_JUDGED[drawing] ?? []);
        const results: any[] = [];
        for (const f of await floorsOf(page)) {
          const mine = (d.probes as any[]).filter(q => q.floor === f.key);
          if (!mine.length) continue;
          expect(await walkOn(page, f.key)).toBe(f.key);
          results.push(...await keyProbes(page, mine, facts.offset));
        }
        const failures = results.filter(r => !skip.has(r.id9Nov) && !r.standsOnFloor).map(r => ({ probe: r.id9Nov, found: r.found, sides: r.sides }));
        const detail = { drawing, grade: d.grade, notJudged: [...skip], results };
        record(file, 'ra6', { judged: true, ok: failures.length === 0, failures, detail });
        info.annotations.push({ type: 'RA-6', description: `${drawing} (${d.grade}): ${results.length - failures.length} of ${results.length} probes stand on floor; ${JSON.stringify(results.map(r => [r.id9Nov, r.found?.id ?? null, r.sides.map((s: any) => s.walk)]))}`.slice(0, 1500) });
        if (d.grade === 'must') expect(failures, `${name} RA-6`).toEqual([]);
      });
    }
  });
}

/**
 * The probes of the RA-6 key on the floor you are on: each found again by its sheet point (the model point is the sheet
 * point less the model's offset and less its floor's `sheetShift`, the floor's own place on a sheet that holds several
 * plans; an opening of its floor, or a glass probe, within 0.1 m), then, for every side that had
 * no floor on 9 Nov, the floor 0.4 - 0.9 m in front of it (every 0.1 m) and the walk from the first start spot with room
 * (as doorWalks: 0.9, 0.7, 0.55, 0.45, 0.4 m back, clearance 0.25 m): a door is walked through (metres past its line), a
 * glass probe walked at (metres short of the glass).
 */
function keyProbes(page: Page, probes: any[], offset: [number, number]): Promise<any[]> {
  return page.evaluate(({ probes, offset }) => {
    const w = window as any, v = w.__viewer, s = v.state, keep = s.pos.clone(), out: any[] = [];
    const r2 = (x: number) => Math.round(x * 100) / 100;
    for (const q of probes) {
      const shift = ((w.__host.model.floors as any[]).find(f => f.key === q.floor)?.sheetShift ?? [0, 0]) as number[];
      const mx = q.at[0] - offset[0] - shift[0]!, my = q.at[1] - offset[1] - shift[1]!;
      const pool = q.kind === 'glass' ? (w.__host.probes as any[]) : (w.__host.openings as any[]);
      let found: any = null, best = 0.1;
      for (const o of pool) {
        if (o.floor !== q.floor) continue;
        const dd = Math.hypot(o.x - mx, o.y - my);
        if (dd <= best) { best = dd; found = o; }
      }
      const sides: any[] = [];
      for (const side of q.sides as number[]) {
        const nx = q.n[0] * side, ny = q.n[1] * side, floorAt: number[] = [];
        for (let k = 4; k <= 9; k++) {
          s.pos.x = mx + nx * k / 10; s.pos.z = -(my + ny * k / 10);
          if (v.probe.onFloor()) floorAt.push(k / 10);
        }
        let walk: number | string = 'no start';
        for (const back of [0.9, 0.7, 0.55, 0.45, 0.4]) {
          s.pos.x = mx + nx * back; s.pos.z = -(my + ny * back);
          if (!v.probe.onFloor() || v.probe.clearance() < 0.25) continue;
          const deg = Math.atan2(nx, -ny) * 180 / Math.PI;                    // toward the opening (-side * n)
          v.probe.walk(deg, q.kind === 'glass' ? 2.0 : back * 2);
          const past = (s.pos.x - mx) * -nx + (-s.pos.z - my) * -ny;          // past the opening's line (glass: < 0, short of it)
          walk = r2(q.kind === 'glass' ? -past : past);
          break;
        }
        sides.push({ side, floorAt, walk, ...(q.kind === 'glass' ? { glassOk: typeof walk === 'number' && walk > 0.1 && walk < 0.6 } : { through: typeof walk === 'number' && walk > 0.3 }) });
      }
      out.push({ id9Nov: q.id9Nov, kind: q.kind, floor: q.floor, model: [r2(mx), r2(my)], found: found ? { id: found.id ?? null, d: r2(best) } : null,
        sides, standsOnFloor: sides.every(x => x.floorAt.length > 0) });
    }
    s.pos.copy(keep);
    return out;
  }, { probes, offset });
}

/**
 * Walk at `n` random glass parts of the floor you are on (seeded; panes that reach the floor and stand over 1.8 m, at
 * least 0.6 m long, drawn as thin strips): from 1.0 m (or 0.8, 0.6) in front of the middle of the pane, on each side
 * that has floor and room to start, straight at it: you must stop between 0.1 and 0.6 m short of its face (0.1 or less:
 * into or through it). A side with no start spot (the outside of a facade), or where something else stops you 0.6 m or
 * more short of the pane, does not count; a part with no side that counts is replaced by another.
 */
function randomGlassWalks(page: Page, floor: string, n: number, seed: number): Promise<any[]> {
  return page.evaluate(({ floor, n, seed0 }) => {
    const w = window as any, v = w.__viewer, s = v.state, keep = s.pos.clone(), out: any[] = [];
    let seed = seed0;
    const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
    const panes = (w.__host.model.parts as any[]).map((p, i) => ({ p, i })).filter(({ p }) => {
      if (p.floor !== floor || p.kind !== 'glass' || p.z0 > 0.3 || p.z1 < 1.8 || p.o.length < 3) return false;
      return true;
    }).map(({ p, i }) => {
      let best = [0, 0, 0, 0], L = 0;
      for (let k = 0; k < p.o.length; k++) {
        const a = p.o[k], b = p.o[(k + 1) % p.o.length], l = Math.hypot(b[0] - a[0], b[1] - a[1]);
        if (l > L) { L = l; best = [a[0], a[1], b[0], b[1]]; }
      }
      const ux = (best[2]! - best[0]!) / (L || 1), uy = (best[3]! - best[1]!) / (L || 1), nx = -uy, ny = ux;
      const across = p.o.map((q: number[]) => (q[0]! - best[0]!) * nx + (q[1]! - best[1]!) * ny);
      const t0 = Math.min(...across), t1 = Math.max(...across);
      const mx = (best[0]! + best[2]!) / 2 + nx * (t0 + t1) / 2, my = (best[1]! + best[3]!) / 2 + ny * (t0 + t1) / 2;
      return { i, id: `part ${i}`, x: mx, y: my, nx, ny, half: (t1 - t0) / 2, length: L, thick: t1 - t0 };
    }).filter(g => g.length >= 0.6 && g.thick <= 0.12);
    const order = panes.map(g => ({ g, k: rnd() })).sort((a, b) => a.k - b.k).map(x => x.g);
    for (const g of order) {
      if (out.length >= n) break;
      const sides: any[] = [];
      for (const side of [1, -1]) {
        const nx = g.nx * side, ny = g.ny * side, deg = Math.atan2(nx, -ny) * 180 / Math.PI;
        let res: number | null = null;
        for (const back of [1.0, 0.8, 0.6]) {
          s.pos.x = g.x + nx * (g.half + back); s.pos.z = -(g.y + ny * (g.half + back));
          if (!v.probe.onFloor() || v.probe.clearance() < 0.25) continue;
          v.probe.walk(deg, 2.0);
          res = Math.round((((s.pos.x - g.x) * nx + (-s.pos.z - g.y) * ny) - g.half) * 100) / 100;
          break;
        }
        // stopped 0.6 m or more short: something else (a mullion, a jamb, a column) stopped you first: not a test of the pane
        if (res !== null) sides.push({ side, stoppedAt: res, ok: res > 0.1 && res < 0.6, judged: res < 0.6 });
      }
      if (!sides.some(x => x.judged)) continue;
      out.push({ part: g.id, floor, at: [Math.round(g.x * 1000) / 1000, Math.round(g.y * 1000) / 1000], sides,
        ok: sides.filter(x => x.judged).every(x => x.ok) });
    }
    s.pos.copy(keep);
    return out;
  }, { floor, n, seed0: seed });
}
