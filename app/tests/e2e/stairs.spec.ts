// R7 (rooms milestone; docs/rooms/WORK_BREAKDOWN.md R7, ACCEPTANCE.md RA-10's browser part, RA-8's ceiling checks and
// RA-14's frame rate): climbing in Edge, on the offline files of versions with `stairways` (BuiltModel v2).
//   default               the synthetic versions (the reference building and the straight, L and U stair models), made in
//                         the set-up into <WT_TMP>/rooms with the template of lib/target.ts roomsTemplate()
//   WT_ROOMS_OFFLINE_DIR  every .html in it instead: the real new-rule versions (the house, the bank, the tower)
//   WT_ROOMS_NO_STAIRS    comma list of file names (without .html) allowed to have no climbable stairway (a new-rule
//                         suite has `stairways: []`); any other file must have one
//   WT_FPS_GPU=1          also the frame rate with Edge's GPU: a browser started without the software-drawing flags
//                         (RA-14; DESIGN R-9.9's box-proxy condition, a frame over 33 ms on the tower)
// Per file: up and down every stairway along its walking line (lib/walks.ts stairWalks, docs/rooms/contract-issues/R4.md
// section 5 and D-1), the keyboard start, the probe after a climb (the stale foot), the floor buttons, the ceilings, and
// the frame rate on the stair (recorded, not judged: software-drawn Edge). Once: the old versions show no Ceilings tick
// (lib/target.ts oldPagePath: WT_OFFLINE_DIR or dist/offline). The climbs run with the furniture hidden, as the structure
// checks are judged (structure.spec.ts, upload-walk.spec.ts); the frame rate is taken with it shown. Every result is
// written to <WT_TMP>/stairs/<file>.json (merged per check).
//   WT_WEB_PORT=5747 WT_API_PORT=8747 WT_TMP="$TEMP/wt-r7" WT_SERVE=none WT_SKIP_STORE_CHECK=1 \
//     npx playwright test -c tests/e2e/playwright.config.ts --project=e2e tests/e2e/stairs.spec.ts
// (WT_SERVE=none: nothing to serve. Add WT_OFFLINE_DIR=<old versions' offline files> when dist/offline is not this viewer's.)
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { chromium, expect, test, type Page, type TestInfo } from '@playwright/test';
import { measureFps, timedDescribe } from './lib/fps';
import { pageApi, sleep, type PageApi } from './lib/page';
import {
  APP_ONLY, isOn, makeRoomsOffline, noNetwork, oldPagePath, ROOMS_OFFLINE_DIR, roomsFiles, sel, TMP, VERSIONS, waitReady,
  type VersionKey,
} from './lib/target';
import { stairWalks, type StairWalk } from './lib/walks';

/* eslint-disable @typescript-eslint/no-explicit-any */

const QUERY = '?build=0&nodownload=1&test=1';
const REPORT = path.join(TMP, 'stairs');
const FILES = roomsFiles();
const NO_STAIRS = new Set((process.env.WT_ROOMS_NO_STAIRS ?? '').split(',').map(s => s.trim()).filter(Boolean));
const STEP_UP = 0.25, STEP_DOWN = 0.30, EPS = 1e-4;

const baseOf = (file: string) => path.basename(file).replace(/\.html$/i, '');

/** Merges one check's result into the file's report. */
function record(file: string, check: string, result: unknown): void {
  mkdirSync(REPORT, { recursive: true });
  const out = path.join(REPORT, `${baseOf(file)}.json`);
  const prev = existsSync(out) ? JSON.parse(readFileSync(out, 'utf8')) : { file };
  prev[check] = result;
  writeFileSync(out, JSON.stringify(prev, null, 2) + '\n', 'utf8');
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

interface Stairway { id: string; from: string; to: string; risers: number; riser: number; walk: [number, number][] }
const stairwaysOf = (page: Page): Promise<Stairway[]> => page.evaluate(() =>
  (((window as any).__host.model.stairways ?? []) as any[]).map(s => ({ id: s.id, from: s.from, to: s.to, risers: s.risers, riser: s.riser, walk: s.walk })));
const floorsOf = (page: Page) => page.evaluate(() => ((window as any).__host.floors as { key: string; level: number }[]).map(f => ({ key: f.key, level: f.level })));
const setFurniture = (page: Page, on: boolean) => page.evaluate(show => {
  const F = (window as any).__host.furniture;
  if (F) for (const k of F.kinds()) F.setVisible(k.key, show);
}, on);
const st = (page: Page) => page.evaluate(() => {
  const s = (window as any).__viewer.state;
  return { mode: s.mode as string, floor: s.floor.key as string, foot: s.foot as number, x: s.pos.x as number, y: -s.pos.z as number };
});
const footNow = (page: Page) => page.evaluate(() => (window as any).__viewer.probe.foot() as number);
const r3 = (v: number) => Math.round(v * 1000) / 1000;

/** The stairways a file must climb: none is a failure unless the file is in WT_ROOMS_NO_STAIRS. */
async function climbable(page: Page, file: string, info: TestInfo): Promise<Stairway[]> {
  const list = await stairwaysOf(page);
  if (!list.length) {
    record(file, 'stairways', []);
    if (NO_STAIRS.has(baseOf(file))) { info.annotations.push({ type: 'stairs', description: 'no climbable stairway (allowed by WT_ROOMS_NO_STAIRS)' }); return []; }
    expect(list, `${baseOf(file)} has no climbable stairway (WT_ROOMS_NO_STAIRS allows that)`).not.toEqual([]);
  }
  return list;
}

/** What RA-10 asks of one climb (up or down), as a list of failures (empty: it passed). */
function judgeClimb(r: StairWalk): string[] {
  const bad: string[] = [];
  const [startLevel, endLevel, startFloor, endFloor] = r.dir === 'up' ? [r.lower, r.upper, r.from, r.to] : [r.upper, r.lower, r.to, r.from];
  if (Math.abs(r.start.foot - startLevel) > 0.01) bad.push(`start foot ${r.start.foot}, not ${startLevel} ± 0.01`);
  if (r.start.floor !== startFloor) bad.push(`started on ${r.start.floor}, not ${startFloor}`);
  if (Math.abs(r.end.foot - endLevel) > 0.02) bad.push(`end foot ${r.end.foot}, not ${endLevel} ± 0.02`);
  if (r.end.floor !== endFloor) bad.push(`ended named ${r.end.floor}, not ${endFloor}`);
  const last = r.modechange[r.modechange.length - 1];
  if (!last || last.floor !== endFloor) bad.push(`the last modechange named ${last ? last.floor : 'nothing'}, not ${endFloor}`);
  if (r.past < 0.5) bad.push(`only ${r.past} m past the last riser`);
  const crossed = r.pieces.filter(q => q.crosses);
  if (crossed.length) bad.push(`probe.crosses true on ${crossed.length} piece(s): ${JSON.stringify(crossed.map(q => q.to))}`);
  if (r.maxRise > STEP_UP + EPS) bad.push(`a 5 cm move rose ${r.maxRise} m`);
  if (r.maxDrop > STEP_DOWN + EPS) bad.push(`a 5 cm move dropped ${r.maxDrop} m`);
  return bad;
}

/** One door's walk both ways from its start spots, as doorWalks does it (lib/walks.ts), also the first spot's foot. */
const doorProbes = (page: Page, ids: string[]) => page.evaluate(list => {
  const w = window as any, v = w.__viewer, s = v.state, out: any[] = [];
  for (const id of list) {
    const d = w.__host.openings.find((o: any) => o.id === id);
    const r: any = { id };
    for (const sign of [1, -1]) {
      const nx = d.nx * sign, ny = d.ny * sign, deg = Math.atan2(-nx, ny) * 180 / Math.PI;
      let along: number | string = 'no start';
      for (const back of [0.9, 0.7, 0.55, 0.45, 0.4]) {
        s.pos.x = d.x - nx * back; s.pos.z = -(d.y - ny * back);
        const onFloor = v.probe.onFloor(), foot = v.probe.foot(), clr = v.probe.clearance();
        if (r.firstFoot === undefined) { r.firstFoot = Math.round(foot * 1e6) / 1e6; r.firstOnFloor = onFloor; }
        if (!onFloor || clr < 0.25) continue;
        v.probe.walk(deg, back * 2);
        along = Math.round(((s.pos.x - d.x) * nx + (-s.pos.z - d.y) * ny) * 1000) / 1000;
        break;
      }
      r[sign > 0 ? 'fwd' : 'back'] = along;
    }
    out.push(r);
  }
  return out;
}, ids);

/** The doors (and passages) of a floor, nearest to a plan point first. */
const doorsByDistance = (page: Page, floor: string, x: number, y: number) => page.evaluate(({ floor, x, y }) =>
  ((window as any).__host.openings as any[]).filter(o => o.floor === floor && (o.kind === 'door' || o.kind === 'passage'))
    .map(o => ({ id: o.id as string, d: Math.hypot(o.x - x, o.y - y) })).sort((a, b) => a.d - b.d).map(o => o.id), { floor, x, y });

/** Every ceiling mesh of the scene: name, floor, whether it and its parents are visible. */
const ceilings = (page: Page) => page.evaluate(() => {
  const w = window as any, out: any[] = [];
  const showing = (o: any) => { for (let n = o; n; n = n.parent) if (!n.visible) return false; return true; };
  for (const [key, f] of Object.entries(w.__host.FL) as [string, any][]) {
    f.group.traverse((o: any) => { if (o.isMesh && o.userData && o.userData.ceiling) out.push({ name: o.name, floor: key, visible: o.visible, showing: showing(o) }); });
  }
  return out as { name: string; floor: string; visible: boolean; showing: boolean }[];
});

/**
 * On floor `key` (walked there first): a point in the middle of a room under a ceiling part (a closed space with
 * `ceiling`, else any point of a ceiling part), and the first ceiling mesh a ray straight up from it meets.
 */
const ceilingRay = (page: Page, key: string) => page.evaluate(k => {
  const w = window as any, v = w.__viewer, T = w.__walkthrough.THREE, model = w.__host.model;
  if (v.mode !== 'walk') v.setMode('walk');
  v.goToFloor(k);
  const level = w.__host.floors.find((f: any) => f.key === k).level as number;
  const inRing = (ring: number[][], x: number, y: number) => {
    let c = false;
    for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
      const [xi, yi] = ring[i]!, [xj, yj] = ring[j]!;
      if ((yi! > y) !== (yj! > y) && x < xi! + (y - yi!) * (xj! - xi!) / (yj! - yi!)) c = !c;
    }
    return c;
  };
  const inPoly = (p: any, x: number, y: number) => inRing(p.o, x, y) && !(p.h ?? []).some((h: number[][]) => inRing(h, x, y));
  const parts = (model.parts as any[]).filter(p => p.floor === k && p.kind === 'ceiling');
  const under = (x: number, y: number) => parts.find(p => inPoly(p, x, y)) ?? null;
  const candidates = (poly: any) => {
    const xs = poly.o.map((q: number[]) => q[0]), ys = poly.o.map((q: number[]) => q[1]);
    const pts: number[][] = [[xs.reduce((a: number, b: number) => a + b, 0) / xs.length, ys.reduce((a: number, b: number) => a + b, 0) / ys.length]];
    const [x0, x1, y0, y1] = [Math.min(...xs), Math.max(...xs), Math.min(...ys), Math.max(...ys)];
    for (let i = 1; i < 8; i++) for (let j = 1; j < 8; j++) pts.push([x0 + (x1 - x0) * i / 8, y0 + (y1 - y0) * j / 8]);
    return pts;
  };
  let pick: any = null;
  for (const sp of ((model.spaces ?? []) as any[]).filter(q => q.floor === k && q.ceiling)) {
    for (const [x, y] of candidates(sp)) { const c = under(x!, y!); if (c && inPoly(sp, x!, y!)) { pick = { x, y, space: sp.id, z0: c.z0 }; break; } }
    if (pick) break;
  }
  if (!pick) for (const c of parts) { for (const [x, y] of candidates(c)) if (inPoly(c, x!, y!)) { pick = { x, y, space: null, z0: c.z0 }; break; } if (pick) break; }
  if (!pick) return { floor: k, level, parts: parts.length, pick: null, hit: null };
  const meshes: any[] = [];
  for (const f of Object.values(w.__host.FL) as any[]) f.group.traverse((o: any) => { if (o.isMesh && o.userData && o.userData.ceiling) meshes.push(o); });
  for (const m of meshes) m.updateWorldMatrix(true, false);
  const ray = new T.Raycaster(new T.Vector3(pick.x, level + 1.2, -pick.y), new T.Vector3(0, 1, 0));
  ray.far = 20;
  const h = ray.intersectObjects(meshes, false)[0];
  const showing = (o: any) => { for (let n = o; n; n = n.parent) if (!n.visible) return false; return true; };
  return {
    floor: k, level, parts: parts.length, pick: { ...pick, x: Math.round(pick.x * 1000) / 1000, y: Math.round(pick.y * 1000) / 1000 },
    hit: h ? { name: h.object.name, y: Math.round(h.point.y * 1000) / 1000, showing: showing(h.object) } : null,
  };
}, key);

/** The WebGL renderer the page draws with (the unmasked name when the browser gives it). */
const rendererOf = (page: Page) => page.evaluate(() => {
  const c = document.querySelector('canvas') as HTMLCanvasElement | null;
  const gl = (c?.getContext('webgl2') ?? c?.getContext('webgl')) as WebGL2RenderingContext | null;
  if (!gl) return 'unknown';
  const ext = gl.getExtension('WEBGL_debug_renderer_info');
  return String(ext ? gl.getParameter(ext.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER));
});

/** The intervals between frames over `ms` (requestAnimationFrame): mean fps, the 95th percentile and the longest, in ms. */
const frameTimes = (page: Page, ms: number) => page.evaluate(duration => new Promise<{ fps: number; p95Ms: number; maxMs: number; over33: number; frames: number }>(resolve => {
  const ts: number[] = [];
  const step = (t: number) => {
    ts.push(t);
    if (t - ts[0]! >= duration) {
      const d = ts.slice(1).map((x, i) => x - ts[i]!).sort((a, b) => a - b);
      const r1 = (x: number) => Math.round(x * 10) / 10;
      resolve({ fps: r1(d.length * 1000 / (t - ts[0]!)), p95Ms: r1(d[Math.floor(d.length * 0.95)] ?? 0), maxMs: r1(d[d.length - 1] ?? 0), over33: d.filter(x => x > 33.4).length, frames: d.length });
    } else requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
}), ms);

/**
 * The frame rate in Walk on the stair, ceilings on, furniture as the model has it: standing on riser 1 facing up the
 * flight, then holding W (the walker climbs; the body rays meet both floors): the mean of lib/fps.ts measureFps, and
 * the frame intervals (95th percentile, longest, how many over 33 ms) while W is held. Returns the figures (also
 * recorded).
 */
async function stairFps(page: Page, p: PageApi, file: string, check: string, ms: number): Promise<Record<string, unknown>> {
  const list = await stairwaysOf(page);
  if (!list.length) return { stair: null };
  const s0 = list[0]!;
  await stairWalks(page, { stair: s0.id, dir: 'up', pieces: 1 });              // stand on riser 1's middle
  await page.evaluate(pt => {
    const s = (window as any).__viewer.state, dx = pt[0] - s.pos.x, dy = pt[1] + s.pos.z;
    s.yaw = Math.atan2(-dx, dy); s.pitch = 0;
  }, s0.walk[2] ?? s0.walk[s0.walk.length - 1]!);
  const toggles = await page.evaluate(() => (window as any).__walkthrough.viewer.getToggles());
  await sleep(500);
  const standing = await measureFps(page, ms);
  const a = await st(page);
  await p.keyDown('KeyW');
  const walking = await measureFps(page, ms);
  const walkingFrames = await frameTimes(page, ms);
  await p.keyUp('KeyW'); await sleep(100);
  const b = await st(page);
  const renderer = await rendererOf(page);
  const res = {
    stair: s0.id, renderer, ceilingsTick: toggles.ceilings ?? null, standingFps: standing, walkingFps: walking,
    standingFrameMs: standing > 0 ? r3(1000 / standing) : null, walkingFrameMs: walking > 0 ? r3(1000 / walking) : null,
    walkingFrames, footBeforeW: r3(a.foot), footAfterW: r3(b.foot), floorAfterW: b.floor, movedWithW: r3(Math.hypot(b.x - a.x, b.y - a.y)), ms,
  };
  record(file, check, res);
  return res;
}

test.describe('stairs', { tag: APP_ONLY }, () => {
  test.describe.configure({ mode: 'default' });

  // The synthetic files are made afresh by the first test's worker (and again by a worker restarted after a failure).
  test.beforeAll(() => {
    if (!ROOMS_OFFLINE_DIR) makeRoomsOffline();
  });

  if (!FILES.length) {
    test('stairs: offline files to check', () => {
      throw new Error(`no .html files in WT_ROOMS_OFFLINE_DIR=${ROOMS_OFFLINE_DIR ?? ''}`);
    });
  }

  for (const file of FILES) {
    const name = baseOf(file);

    test.describe(name, () => {
      test(`${name}: up every stairway along its walking line and 1.0 m on: the upper floor's level, named, no crossing (RA-10 Up)`, async ({ page }, info) => {
        const { problems, requests } = await open(page, file);
        await setFurniture(page, false);
        const results: StairWalk[] = [], failures: unknown[] = [];
        for (const s of await climbable(page, file, info)) {
          const [r] = await stairWalks(page, { stair: s.id, dir: 'up' });
          const bad = judgeClimb(r!);
          if (!(await isOn(page.locator(sel.floorButton(r!.to))))) bad.push(`the floor button ${r!.to} is not pressed`);
          results.push(r!);
          if (bad.length) failures.push({ stair: s.id, bad });
          info.annotations.push({ type: `up ${s.id}`, description: `foot ${r!.start.foot} -> ${r!.end.foot} m (rose ${r3(r!.end.foot - r!.start.foot)}), named ${r!.named.join(' -> ')}, ${r!.past} m past the last riser, ${r!.moves} moves` });
        }
        record(file, 'up', { ok: !failures.length, failures, results });
        expect(failures).toEqual([]);
        expect(requests).toEqual([]);
        expect(problems()).toEqual([]);
      });

      test(`${name}: down every stairway, the reverse path: the lower floor's level, named, no crossing (RA-10 Down)`, async ({ page }, info) => {
        const { problems } = await open(page, file);
        await setFurniture(page, false);
        const results: StairWalk[] = [], failures: unknown[] = [];
        for (const s of await climbable(page, file, info)) {
          const [r] = await stairWalks(page, { stair: s.id, dir: 'down' });
          const bad = judgeClimb(r!);
          if (!(await isOn(page.locator(sel.floorButton(r!.from))))) bad.push(`the floor button ${r!.from} is not pressed`);
          results.push(r!);
          if (bad.length) failures.push({ stair: s.id, bad });
          info.annotations.push({ type: `down ${s.id}`, description: `foot ${r!.start.foot} -> ${r!.end.foot} m, named ${r!.named.join(' -> ')}, ${r!.moves} moves` });
        }
        record(file, 'down', { ok: !failures.length, failures, results });
        expect(failures).toEqual([]);
        expect(problems()).toEqual([]);
      });

      test(`${name}: a door probe beside the stair, then a far one, answer as on a flat floor after a walk that ended up the stair (RA-10)`, async ({ page }, info) => {
        const { problems } = await open(page, file);
        await setFurniture(page, false);
        const out: unknown[] = [];
        for (const s of await climbable(page, file, info)) {
          await page.evaluate(k => { const v = (window as any).__viewer; if (v.mode !== 'walk') v.setMode('walk'); v.goToFloor(k); }, s.from);
          // the door nearest to the stair's foot and the farthest one, among the doors with a start spot on the floor
          // (no climb yet: a door with floor on neither side, as the house's garden gate, tells nothing)
          const all = await doorProbes(page, await doorsByDistance(page, s.from, s.walk[0]![0], s.walk[0]![1]));
          const usable = all.filter(d => typeof d.fwd === 'number' || typeof d.back === 'number');
          expect(usable.length, `${s.from} has a door to probe`).toBeGreaterThan(0);
          const ids = [...new Set([usable[0]!.id, usable[usable.length - 1]!.id])] as string[];
          const flat = all.filter(d => ids.includes(d.id)).sort((a, b) => ids.indexOf(a.id) - ids.indexOf(b.id));
          // a walk that ends three risers up the stair (R-9.8: "two treads up a stair would leave a stale foot")
          const [part] = await stairWalks(page, { stair: s.id, dir: 'up', rise: 3 * s.riser - 0.005 });
          const lower = part!.lower;
          const after = await doorProbes(page, ids);                             // the one beside the stair first
          out.push({ stair: s.id, doors: ids, upTo: part!.end, flat, after });
          record(file, 'staleFoot', out);
          expect(part!.end.foot, 'the walk ended up the stair').toBeGreaterThan(lower + 0.3);
          expect(part!.end.floor, 'still named the lower floor').toBe(s.from);
          for (const d of after) {
            // the first spot written after the climb: the foot back on the floor's level; each door has a start spot
            expect(Math.abs(d.firstFoot - lower), `${d.id}: the probe starts from the floor's level`).toBeLessThan(1e-6);
            expect(typeof d.fwd === 'number' || typeof d.back === 'number', `${d.id}: a start spot on the floor`).toBe(true);
          }
          expect(after, 'the same answers as before the climb').toEqual(flat);
        }
        expect(problems()).toEqual([]);
      });

      test(`${name}: PgUp / PgDn and the floor buttons still change floor (teleports); the touch Upstairs / Downstairs buttons show in Walk`, async ({ page }) => {
        const { p, problems } = await open(page, file);
        const floors = await floorsOf(page);
        const failures: unknown[] = [];
        if (floors.length < 2) { record(file, 'floors', { ok: true, floors, note: 'one floor' }); return; }
        const [f1, f2] = [floors[0]!, floors[1]!];
        await p.press('Digit2');
        const at = async (what: string, want: { key: string; level: number }) => {
          const s = await st(page), foot = await footNow(page);
          if (s.mode !== 'walk' || s.floor !== want.key || Math.abs(foot - want.level) > 1e-6) failures.push({ what, want: want.key, mode: s.mode, floor: s.floor, foot });
        };
        await at('Walk', f1);
        await p.press('PageUp'); await at('PageUp', f2);
        await p.press('PageDown'); await at('PageDown', f1);
        await page.locator(sel.floorButton(f2.key)).click(); await sleep(200); await at(`button ${f2.key}`, f2);
        await page.locator(sel.floorButton(f1.key)).click(); await sleep(200); await at(`button ${f1.key}`, f1);
        await page.locator(sel.floorButton(f1.key)).blur();
        await p.tap(1000, 600);
        const shown = await page.evaluate(s => { const e = document.querySelector(s); return !!e && getComputedStyle(e).display !== 'none' && e.getBoundingClientRect().width > 0; }, sel.updown);
        if (!shown) failures.push({ what: 'the touch Upstairs / Downstairs buttons do not show' });
        else {
          await p.tapEl(sel.up); await at('Upstairs', f2);
          await p.tapEl(sel.down); await at('Downstairs', f1);
        }
        record(file, 'floors', { ok: !failures.length, failures, floors });
        expect(failures).toEqual([]);
        expect(problems()).toEqual([]);
      });

      test(`${name}: ceilings: in Walk a ray up from the middle of a room meets the ceiling at its height; hidden in Orbit; shown in Ghost; the Ceilings tick hides them (RA-8)`, async ({ page }) => {
        const { problems } = await open(page, file);
        const tick = page.locator(sel.toggle('ceilings'));
        const hasCeilings = await page.evaluate(() => ((window as any).__host.model.parts as any[]).some(p => p.kind === 'ceiling'));
        const failures: unknown[] = [], rays: unknown[] = [];
        if (!hasCeilings) {
          if (await tick.count()) failures.push('a Ceilings tick on a version with no ceiling');
          record(file, 'ceilings', { ok: !failures.length, failures, note: 'no ceiling parts' });
          expect(failures).toEqual([]);
          return;
        }
        expect(await tick.count(), 'the Ceilings tick').toBe(1);
        const label = await page.evaluate(s => (document.querySelector(s) as HTMLInputElement).closest('label')?.textContent?.trim() ?? null, sel.toggle('ceilings'));
        expect(await tick.isChecked(), 'the tick is on at first').toBe(true);
        // Walk: every floor with ceilings
        const floors = await page.evaluate(() => [...new Set(((window as any).__host.model.parts as any[]).filter(p => p.kind === 'ceiling').map(p => p.floor as string))]);
        for (const k of floors) {
          const r = await ceilingRay(page, k);
          rays.push(r);
          if (!r.pick || !r.hit) { failures.push({ floor: k, why: r.pick ? 'the ray up met no ceiling' : 'no point under a ceiling part', r }); continue; }
          const want = r3(r.level + r.pick.z0);
          if (r.hit.name !== `${k} ceilings` || Math.abs(r.hit.y - want) > 0.01 || !r.hit.showing) failures.push({ floor: k, want, r });
        }
        const inWalk = await ceilings(page);
        if (inWalk.some(c => !c.visible)) failures.push({ mode: 'walk', hidden: inWalk.filter(c => !c.visible).map(c => c.name) });
        await page.evaluate(() => (window as any).__viewer.setMode('orbit')); await sleep(200);
        const inOrbit = await ceilings(page);
        if (inOrbit.some(c => c.visible)) failures.push({ mode: 'orbit', visible: inOrbit.filter(c => c.visible).map(c => c.name) });
        await page.evaluate(() => (window as any).__viewer.setMode('ghost')); await sleep(200);
        const inGhost = await ceilings(page);
        if (inGhost.some(c => !c.visible)) failures.push({ mode: 'ghost', hidden: inGhost.filter(c => !c.visible).map(c => c.name) });
        await page.evaluate(() => (window as any).__viewer.setMode('walk')); await sleep(200);
        await tick.scrollIntoViewIfNeeded(); await tick.click(); await sleep(200);
        const off = await ceilings(page), offToggle = await page.evaluate(() => (window as any).__walkthrough.viewer.getToggles().ceilings);
        if (off.some(c => c.visible) || offToggle !== false || await tick.isChecked()) failures.push({ tick: 'off', visible: off.filter(c => c.visible).map(c => c.name), toggle: offToggle });
        await tick.click(); await sleep(200);
        const on = await ceilings(page);
        if (on.some(c => !c.visible)) failures.push({ tick: 'on again', hidden: on.filter(c => !c.visible).map(c => c.name) });
        record(file, 'ceilings', { ok: !failures.length, failures, label, rays, meshes: inWalk.map(c => c.name) });
        expect(label).toBe('Ceilings');
        expect(failures).toEqual([]);
        expect(problems()).toEqual([]);
      });

      timedDescribe(`${name}: by keyboard`, () => {
        test(`${name}: W held until the foot has risen three risers, then the probe finishes the climb (RA-10)`, async ({ page }, info) => {
          test.setTimeout(240_000);
          const { p, problems } = await open(page, file);
          await setFurniture(page, false);
          const out: unknown[] = [];
          for (const s of await climbable(page, file, info)) {
            await p.press('Digit2');
            const lower = await page.evaluate(({ from, a, b }) => {
              const v = (window as any).__viewer, sv = v.state;
              v.goToFloor(from);
              sv.pos.x = a[0]; sv.pos.z = -a[1];
              v.probe.foot();                                          // the foot on the floor's level (a written position)
              sv.yaw = Math.atan2(-(b[0] - a[0]), b[1] - a[1]); sv.pitch = 0;
              return sv.floor.level as number;
            }, { from: s.from, a: s.walk[0]!, b: s.walk[1]! });
            const want = lower + 3 * s.riser - 0.005, t0 = Date.now();
            let foot = lower;
            await p.keyDown('KeyW');
            while (Date.now() - t0 < 90_000) {
              await sleep(50);
              foot = await page.evaluate(() => (window as any).__viewer.state.foot as number);
              if (foot >= want) break;
            }
            await p.keyUp('KeyW'); await sleep(150);
            const byKeys = await st(page), heldMs = Date.now() - t0;
            const [r] = await stairWalks(page, { stair: s.id, dir: 'up', start: 'here' });
            out.push({ stair: s.id, lower, want: r3(want), byKeys: { foot: r3(byKeys.foot), floor: byKeys.floor, at: [r3(byKeys.x), r3(byKeys.y)] }, heldMs, finish: r });
            record(file, 'keyboard', out);
            info.annotations.push({ type: `keys ${s.id}`, description: `W held ${heldMs} ms: foot ${r3(lower)} -> ${r3(byKeys.foot)} m; the probe finished at ${r!.end.foot} m on ${r!.end.floor}` });
            expect(byKeys.foot, 'W climbed three risers').toBeGreaterThanOrEqual(want);
            expect(Math.abs(r!.end.foot - r!.upper), 'the probe finished the climb').toBeLessThanOrEqual(0.02);
            expect(r!.end.floor).toBe(s.to);
            expect(r!.maxRise).toBeLessThanOrEqual(STEP_UP + EPS);
          }
          expect(problems()).toEqual([]);
        });

        test(`${name}: frame rate in Walk on the stair, ceilings on (recorded, software-drawn Edge)`, async ({ page }, info) => {
          const { p } = await open(page, file);
          await p.press('Digit2');
          const r = await stairFps(page, p, file, 'fps', 3000);
          info.annotations.push({ type: 'stair fps', description: JSON.stringify(r) });
        });
      });

      if (process.env.WT_FPS_GPU === '1') {
        // RA-14: Edge started without the software-drawing flags (the config's --use-angle=swiftshader and
        // --enable-unsafe-swiftshader); R-9.9: the box proxy is needed only if a frame takes over 33 ms on the tower.
        // Playwright refuses launchOptions in a describe group (a new worker), so this test starts its own headless Edge
        // (WT_FPS_GPU_ARGS: its flags) while the run's own one waits, idle, under the same Edge lock.
        test(`${name}: frame rate in Walk on the stair, ceilings on, with the GPU (RA-14 >= 30 fps; R-9.9 <= 33 ms)`, async ({ browserName }, info) => {
          test.setTimeout(180_000);
          expect(browserName).toBe('chromium');
          const args = (process.env.WT_FPS_GPU_ARGS ?? '--allow-file-access-from-files --ignore-gpu-blocklist').split(' ').filter(Boolean);
          const browser = await chromium.launch({ channel: 'msedge', headless: true, args });
          try {
            const page = await (await browser.newContext({ viewport: { width: 1400, height: 880 } })).newPage();
            const { p } = await open(page, file);
            await p.press('Digit2');
            const r = await stairFps(page, p, file, 'fpsGpu', 5000);
            record(file, 'fpsGpu', { ...r, args });
            info.annotations.push({ type: 'stair fps (GPU)', description: JSON.stringify({ ...r, args }) });
          } finally {
            await browser.close();
          }
        });
      }
    });
  }

  test('the old versions show no Ceilings tick and no ceiling mesh (RA-8)', async ({ page }) => {
    test.setTimeout(300_000);
    const out: unknown[] = [];
    for (const k of Object.keys(VERSIONS) as VersionKey[]) {
      const file = oldPagePath(k);
      expect(existsSync(file), `${file} (set WT_OFFLINE_DIR to the old versions' offline files made with this viewer)`).toBe(true);
      const { problems } = await open(page, file);
      const ticks = await page.locator(sel.toggle('ceilings')).count();
      const meshes = (await ceilings(page)).length;
      // the model as the viewer loaded it: `stairways` only where it derived one from a complete flight of old steps
      // (16 Nov 2026, model/upgrade.ts: the hotel's F1-S1; hotel-stairs.spec.ts climbs it). The saved data has none.
      const v2 = await page.evaluate(() => (((window as any).__host.model.stairways ?? null) as any[] | null)?.map(s => `${s.id} ${s.derived}`) ?? null);
      const saved = await page.evaluate(() => (document.getElementById('wtv-data')?.textContent ?? '').includes('"stairways"'));
      out.push({ version: k, file, ticks, meshes, stairways: v2, savedStairways: saved });
      expect([k, ticks, meshes, v2, saved]).toEqual([k, 0, 0, k === 'hotel' ? ['F1-S1 steps'] : null, false]);
      expect(problems()).toEqual([]);
    }
    mkdirSync(REPORT, { recursive: true });
    writeFileSync(path.join(REPORT, 'old-versions.json'), JSON.stringify(out, null, 2) + '\n', 'utf8');
  });
});
