// U7 (docs/upload/ACCEPTANCE.md 2.4 U7; DESIGN.md U-12.1): the plan canvas in Edge, on its harness page
// (apps/web/test/plan/harness.html, served by the web dev server): the bank and house fixture plans draw (pixel probes at
// known wall points: the wall corners of the seeded models, which lie on the drawings' wall lines), a layer highlight
// changes the pixels, click and box selection pick the expected keys (worked out here by brute force from the fixture
// files), the house sheet redraws within the budget (A-10: under 50 ms at 1400 x 880), at device pixel ratio 1 and 2.
// The rooms milestone (R6; docs/rooms/ACCEPTANCE.md 2.4): the overlay's rooms, holes, unfloored areas, stairs and
// closings drawn, the three ticks, and the canvas's test hook (the section "rooms" below).
//   WT_WEB_PORT=5737 WT_API_PORT=8737 WT_TMP="$TEMP/wt-u7" WT_SERVE=web WT_SKIP_STORE_CHECK=1 \
//     npx playwright test -c tests/e2e/playwright.config.ts --project=e2e tests/e2e/plan-canvas.spec.ts
// (Without WT_SERVE the config starts the API as well; this spec needs only the web server.)
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { gunzipSync } from 'node:zlib';
import { expect, test, type Page } from '@playwright/test';
import { insideOf, referenceOverlay, referencePlan } from '../../apps/web/test/mock-api/rooms';
import { timedDescribe } from './lib/fps';
import { APP } from './lib/target';

/* eslint-disable @typescript-eslint/no-explicit-any */

// ------------------------------------------------------------------------------------------------- the fixtures, in Node
interface Plan {
  origin: [number, number]; quantum: number; layers: string[]; pts: number[];
  items: { key: string[]; layer: number[]; type: number[]; first: number[]; count: number[] };
}
const readPlan = (name: string) => JSON.parse(gunzipSync(readFileSync(path.join(APP, 'fixtures/upload/plan', `${name}.plan.json.gz`))).toString('utf8')) as Plan;
const readJson = (rel: string) => JSON.parse(readFileSync(path.join(APP, rel), 'utf8'));

type Seg = [number, number, number, number];
function segmentsOf(p: Plan, i: number): Seg[] {
  const t = p.items.type[i]!, f = p.items.first[i]!, c = p.items.count[i]!;
  const P = (k: number): [number, number] => [p.pts[2 * k]!, p.pts[2 * k + 1]!];
  if (t === 5 || c === 0) return [];
  if (c === 1) { const [x, y] = P(f); return [[x, y, x, y]]; }
  const out: Seg[] = [];
  for (let k = f; k < f + c - 1; k++) out.push([...P(k), ...P(k + 1)]);
  if (t >= 1 && t <= 3 && c >= 3) out.push([...P(f + c - 1), ...P(f)]);
  return out;
}
function d2(px: number, py: number, [ax, ay, bx, by]: Seg): number {
  const dx = bx - ax, dy = by - ay, l2 = dx * dx + dy * dy;
  const t = l2 > 0 ? Math.max(0, Math.min(1, ((px - ax) * dx + (py - ay) * dy) / l2)) : 0;
  return (ax + t * dx - px) ** 2 + (ay + t * dy - py) ** 2;
}
const toQ = (p: Plan, x: number, y: number): [number, number] => [(x - p.origin[0]) / p.quantum, (y - p.origin[1]) / p.quantum];
const toM = (p: Plan, qx: number, qy: number): [number, number] => [p.origin[0] + qx * p.quantum, p.origin[1] + qy * p.quantum];

interface Fixture { plan: Plan; segs: { e: number; s: Seg }[]; roles: Record<string, string> }
const cache = new Map<string, Fixture>();
function fixture(name: 'bank1' | 'sukhumvit'): Fixture {
  if (!cache.has(name)) {
    const plan = readPlan(name);
    const segs: { e: number; s: Seg }[] = [];
    for (let e = 0; e < plan.items.key.length; e++) for (const s of segmentsOf(plan, e)) segs.push({ e, s });
    const roles = readJson(`fixtures/upload/settings/${name === 'bank1' ? 'bank' : 'house'}.json`).layers as Record<string, string>;
    cache.set(name, { plan, segs, roles });
  }
  return cache.get(name)!;
}

/** Wall corners of the seeded model's floor (model + offset = sheet) that lie within 2 cm of a wall-role line of the plan. */
function wallPoints(name: 'bank1' | 'sukhumvit', max: number): [number, number][] {
  const { plan, segs, roles } = fixture(name);
  const model = readJson(`fixtures/models/${name === 'bank1' ? 'bank-v2' : 'house'}.model.json`);
  const floor = name === 'bank1' ? 'L1' : 'ground';
  const walls = segs.filter(x => roles[plan.layers[plan.items.layer[x.e]!]!] === 'wall');
  const out: [number, number][] = [];
  for (const part of model.parts.filter((q: any) => q.floor === floor && q.kind === 'wall')) {
    for (const [x, y] of part.o as [number, number][]) {
      const sx = x + model.offset[0], sy = y + model.offset[1];
      const [qx, qy] = toQ(plan, sx, sy);
      if (walls.some(w => d2(qx, qy, w.s) <= 4)) out.push([sx, sy]);
    }
  }
  const step = Math.max(1, Math.floor(out.length / max));
  return out.filter((_, i) => i % step === 0).slice(0, max);
}

/** Points at least `clear` m from anything drawn (texts too) and inside no solid fill, inside the sheet's box. */
function emptyPoints(name: 'bank1' | 'sukhumvit', n: number, clear: number, box: [number, number, number, number]): [number, number][] {
  const { plan, segs } = fixture(name);
  let seed = 5;
  const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
  const fills = plan.items.type.map((t, e) => (t === 2 ? segmentsOf(plan, e) : null)).filter((s): s is Seg[] => !!s);
  const inFill = (qx: number, qy: number) => fills.some(ring => {
    let c = false;
    for (const [ax, ay, bx, by] of ring) if ((ay > qy) !== (by > qy) && qx < ax + (qy - ay) * (bx - ax) / (by - ay)) c = !c;
    return c;
  });
  const out: [number, number][] = [], r2 = (clear / plan.quantum) ** 2;
  for (let k = 0; out.length < n && k < 4000; k++) {
    const x = box[0] + rnd() * (box[2] - box[0]), y = box[1] + rnd() * (box[3] - box[1]);
    const [qx, qy] = toQ(plan, x, y);
    if (segs.every(s => d2(qx, qy, s.s) > r2) && !inFill(qx, qy)) out.push([x, y]);
  }
  return out;
}

/** Lines (open or closed) whose longest segment, `minLen` quanta or more, has nothing else within `px` screen pixels of
 *  its middle at scale s (CSS px per quantum); `at` is that middle in sheet metres. */
function isolated(name: 'bank1' | 'sukhumvit', s: number, px: number, accept: (e: number) => boolean, max: number, minLen = 50) {
  const { plan, segs } = fixture(name);
  const r2 = (px / s) ** 2, out: { e: number; key: string; at: [number, number] }[] = [];
  for (let e = 0; e < plan.items.key.length && out.length < max; e++) {
    if ((plan.items.type[e] !== 0 && plan.items.type[e] !== 1) || plan.items.count[e]! < 2 || !accept(e)) continue;
    const [ax, ay, bx, by] = segmentsOf(plan, e).reduce((a, b) => (Math.hypot(b[2] - b[0], b[3] - b[1]) > Math.hypot(a[2] - a[0], a[3] - a[1]) ? b : a));
    if (Math.hypot(bx - ax, by - ay) < minLen) continue;
    const mx = (ax + bx) / 2, my = (ay + by) / 2;
    if (segs.some(x => x.e !== e && plan.items.key[x.e] !== plan.items.key[e] && d2(mx, my, x.s) <= r2)) continue;
    out.push({ e, key: plan.items.key[e]!, at: toM(plan, mx, my) });
  }
  return out;
}

// --------------------------------------------------------------------------------------------------- the page, the harness
const lum = (p: number[]) => 0.2126 * p[0]! + 0.7152 * p[1]! + 0.0722 * p[2]!;
const isWallInk = (p: number[]) => lum(p) < 170 && Math.abs(p[0]! - p[1]!) < 40 && Math.abs(p[1]! - p[2]!) < 40;
const isWhite = (p: number[]) => p[0]! >= 250 && p[1]! >= 250 && p[2]! >= 250;
const isPink = (p: number[]) => p[0]! > 170 && p[0]! - p[1]! > 70 && p[2]! > 80;

interface Info { count: number; layers: number; view: { cx: number; cy: number; s: number }; size: { w: number; h: number }; dpr: number; backing: [number, number]; rect: number[]; frames: number }

async function open(page: Page, name: 'bank1' | 'sukhumvit'): Promise<{ info: Info; problems: () => string[] }> {
  const problems: string[] = [];
  page.on('pageerror', e => problems.push(`[exception] ${e.message}`));
  page.on('console', m => { if (m.type() === 'error' && !/favicon/i.test(m.text())) problems.push(`[console.error] ${m.text()}`); });
  page.on('response', r => { if (r.status() >= 400 && !/favicon\.ico/i.test(r.url())) problems.push(`[http ${r.status()}] ${r.url()}`); });
  await page.goto('/test/plan/harness.html');
  await page.waitForFunction(() => (window as any).__planHarness?.ready === true, undefined, { timeout: 60_000 });
  const info = await page.evaluate(n => (window as any).__planHarness.load(n), name) as Info;
  return { info, problems: () => problems.filter(p => !/404.*favicon|favicon/i.test(p)) };
}
const H = {
  set: (page: Page, c: Record<string, unknown>) => page.evaluate(x => (window as any).__planHarness.set(x), c) as Promise<Info>,
  pixels: (page: Page, x: number, y: number, r = 2) => page.evaluate(([a, b, c]) => (window as any).__planHarness.pixels(a, b, c), [x, y, r] as const) as Promise<number[][] | null>,
  toPage: (page: Page, x: number, y: number) => page.evaluate(([a, b]) => (window as any).__planHarness.toPage(a, b), [x, y] as const) as Promise<[number, number]>,
  toSheet: (page: Page, x: number, y: number) => page.evaluate(([a, b]) => (window as any).__planHarness.toSheet(a, b), [x, y] as const) as Promise<[number, number]>,
  selected: (page: Page) => page.evaluate(() => (window as any).__planHarness.selected()) as Promise<string[]>,
  events: (page: Page) => page.evaluate(() => (window as any).__planHarness.events.slice()) as Promise<any[]>,
  clear: (page: Page) => page.evaluate(() => (window as any).__planHarness.clearEvents()),
  timeRedraw: (page: Page, n: number) => page.evaluate(k => (window as any).__planHarness.timeRedraw(k), n) as Promise<number[]>,
};
async function clickSheet(page: Page, x: number, y: number, modifiers: ('Shift' | 'Alt' | 'Control')[] = []) {
  const [px, py] = await H.toPage(page, x, y);
  for (const m of modifiers) await page.keyboard.down(m);
  await page.mouse.click(px, py);
  for (const m of modifiers) await page.keyboard.up(m);
}
async function dragPage(page: Page, a: [number, number], b: [number, number], modifiers: ('Shift' | 'Alt' | 'Control')[] = []) {
  for (const m of modifiers) await page.keyboard.down(m);
  await page.mouse.move(a[0], a[1]);
  await page.mouse.down();
  await page.mouse.move((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, { steps: 4 });
  await page.mouse.move(b[0], b[1], { steps: 4 });
  await page.mouse.up();
  for (const m of modifiers) await page.keyboard.up(m);
}
const median = (a: number[]) => [...a].sort((x, y) => x - y)[Math.floor(a.length / 2)]!;

// ======================================================================================================== drawing
const PROBES: { name: 'bank1' | 'sukhumvit'; focus: [number, number, number, number] | null }[] = [
  { name: 'bank1', focus: null },
  { name: 'sukhumvit', focus: [7.74826, 5.601038, 53.870897, 25.854851] },        // the ground floor's area (settings)
];
for (const dpr of [1, 2]) {
  test.describe(`device pixel ratio ${dpr}`, () => {
    test.use({ deviceScaleFactor: dpr });

    for (const { name, focus } of PROBES) {
      test(`${name}: draws its wall lines at the wall corners of the seeded model, and nothing on empty floor`, async ({ page }) => {
        const { info, problems } = await open(page, name);
        expect(info.dpr).toBe(dpr);
        expect(info.backing).toEqual([info.size.w * dpr, info.size.h * dpr]);
        expect(info.size).toEqual({ w: 1400, h: 880 });
        if (focus) await H.set(page, { focus });
        const walls = wallPoints(name, 30);
        expect(walls.length).toBeGreaterThanOrEqual(20);
        const missed: unknown[] = [];
        for (const [x, y] of walls) {
          const px = await H.pixels(page, x, y, dpr === 1 ? 2 : 3);
          expect(px, `${x}, ${y} is on the canvas`).not.toBeNull();
          if (!px!.some(isWallInk)) missed.push({ at: [x, y], darkest: px!.reduce((a, b) => (lum(b) < lum(a) ? b : a)) });
        }
        expect(missed, JSON.stringify(missed)).toEqual([]);
        const box = name === 'bank1' ? [-4, -8, 5, 10] as [number, number, number, number] : focus!;
        const empty = emptyPoints(name, 10, 0.6, box);
        expect(empty.length).toBeGreaterThanOrEqual(5);
        for (const [x, y] of empty) {
          const px = await H.pixels(page, x, y, 2);
          expect(px!.every(isWhite), `${x}, ${y}: ${JSON.stringify(px)}`).toBe(true);
        }
        expect(problems()).toEqual([]);
      });
    }

    test('bank1: a layer highlight paints that layer over a veil, and taking it off restores the pixels', async ({ page }) => {
      const { problems } = await open(page, 'bank1');
      await H.timeRedraw(page, 4);       // read-backs move the canvas to the CPU once: compare pixels after that
      const walls = wallPoints('bank1', 12);
      const before = await Promise.all(walls.map(([x, y]) => H.pixels(page, x, y, 2)));
      const furn = isolated('bank1', (await H.set(page, {})).view.s, 8, e => fixture('bank1').plan.layers[fixture('bank1').plan.items.layer[e]!] === 'I-FURN', 3);
      expect(furn.length).toBeGreaterThan(0);
      const furnBefore = await H.pixels(page, ...furn[0]!.at, 1);
      await H.set(page, { highlight: 'A-WALL-PATT' });
      await H.set(page, { highlight: 'A-WALL' });
      const lit = await Promise.all(walls.map(([x, y]) => H.pixels(page, x, y, 2)));
      expect(lit.filter(px => px!.some(isPink)).length).toBeGreaterThanOrEqual(Math.ceil(walls.length * 0.8));
      const furnLit = await H.pixels(page, ...furn[0]!.at, 1);
      expect(Math.min(...furnLit!.map(lum))).toBeGreaterThan(Math.min(...furnBefore!.map(lum)));   // paler under the veil
      await H.set(page, { highlight: null });
      const after = await Promise.all(walls.map(([x, y]) => H.pixels(page, x, y, 2)));
      expect(after).toEqual(before);
      expect(problems()).toEqual([]);
    });

    test('bank1: a click picks the item under the pointer (shift adds); block mode climbs one level a click', async ({ page }) => {
      const { info, problems } = await open(page, 'bank1');
      const F = fixture('bank1');
      const targets = isolated('bank1', info.view.s, 12, () => true, 6);
      expect(targets.length).toBeGreaterThanOrEqual(4);
      for (const t of targets) {
        await H.clear(page);
        await clickSheet(page, ...t.at);
        const ev = (await H.events(page)).filter(e => e.type === 'select');
        expect(ev.at(-1), t.key).toEqual({ type: 'select', keys: [t.key], mode: 'replace' });
      }
      await clickSheet(page, ...targets[0]!.at);
      await clickSheet(page, ...targets[1]!.at, ['Shift']);
      expect((await H.selected(page)).sort()).toEqual([targets[0]!.key, targets[1]!.key].sort());

      // block mode: a line of a block (a piece of furniture) inside the view block BA, zoomed in on that block
      const P = F.plan;
      const anchors = new Set(P.items.key.filter((_, i) => P.items.type[i] === 5));
      let deep: { e: number; key: string; at: [number, number] } | undefined;
      for (const a of [...anchors].filter(k => k.split('/').length === 2 && anchors.has(k.split('/')[0]!))) {
        const es = P.items.key.map((k, i) => (k.startsWith(a + '/') && P.items.type[i] !== 5 ? i : -1)).filter(i => i >= 0);
        if (es.length < 4) continue;
        const xs = es.flatMap(i => segmentsOf(P, i).flatMap(s => [s[0], s[2]])), ys = es.flatMap(i => segmentsOf(P, i).flatMap(s => [s[1], s[3]]));
        const b = [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)];
        if (b[2]! - b[0]! < 40 || b[3]! - b[1]! < 40 || b[2]! - b[0]! > 300) continue;
        const v = await H.set(page, { focus: [...toM(P, b[0]! - 150, b[1]! - 150), ...toM(P, b[2]! + 150, b[3]! + 150)] });
        deep = isolated('bank1', v.view.s, 6, e => P.items.key[e]!.split('/').length === 3 && P.items.key[e]!.startsWith(a + '/'), 1, 10)[0];
        if (deep) break;
      }
      expect(deep, 'a line of a block inside the view block').toBeTruthy();
      const [outer, inner] = [deep!.key.split('/')[0]!, deep!.key.split('/').slice(0, 2).join('/')];
      await H.set(page, { pick: 'block', selected: [] });
      await clickSheet(page, ...deep!.at);
      expect(await H.selected(page)).toEqual([inner]);
      await clickSheet(page, ...deep!.at);
      expect(await H.selected(page)).toEqual([outer]);
      await clickSheet(page, ...deep!.at);
      expect(await H.selected(page)).toEqual([outer]);
      expect(problems()).toEqual([]);
    });

    test('bank1: a drag box selects the items wholly inside, or touched with alt; block and layer-in-box modes', async ({ page }) => {
      const { problems } = await open(page, 'bank1');
      const F = fixture('bank1'), P = F.plan;
      // a block of a few metres (a desk with its chair) and the box round it, a little larger
      const anchors = P.items.key.map((k, i) => (P.items.type[i] === 5 && k.split('/').length === 2 ? k : null)).filter((k): k is string => !!k);
      let pick: { anchor: string; box: [number, number, number, number] } | null = null;
      for (const a of anchors) {
        const es = P.items.key.map((k, i) => (k.startsWith(a + '/') && P.items.type[i] !== 5 ? i : -1)).filter(i => i >= 0);
        if (es.length < 6) continue;
        const xs = es.flatMap(i => segmentsOf(P, i).flatMap(s => [s[0], s[2]])), ys = es.flatMap(i => segmentsOf(P, i).flatMap(s => [s[1], s[3]]));
        const b: [number, number, number, number] = [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)];
        if (b[2] - b[0] > 60 && b[2] - b[0] < 250 && b[3] - b[1] > 60 && b[3] - b[1] < 250) { pick = { anchor: a, box: b }; break; }
      }
      expect(pick, 'a block of a few metres').toBeTruthy();
      await H.set(page, { focus: [...toM(P, pick!.box[0] - 400, pick!.box[1] - 300), ...toM(P, pick!.box[2] + 400, pick!.box[3] + 300)] });
      const a = await H.toPage(page, ...toM(P, pick!.box[0] - 8, pick!.box[3] + 8));
      const b = await H.toPage(page, ...toM(P, pick!.box[2] + 8, pick!.box[1] - 8));
      const [sx0, sy1] = await H.toSheet(page, ...a), [sx1, sy0] = await H.toSheet(page, ...b);
      const [qx0, qy0] = toQ(P, sx0, sy0), [qx1, qy1] = toQ(P, sx1, sy1);
      const inBox = (s: Seg) => s[0] >= qx0 && s[2] >= qx0 && s[0] <= qx1 && s[2] <= qx1 && s[1] >= qy0 && s[3] >= qy0 && s[1] <= qy1 && s[3] <= qy1;
      const touches = (s: Seg) => {
        const t = (x: number, y: number) => x >= qx0 && x <= qx1 && y >= qy0 && y <= qy1;
        if (t(s[0], s[1]) || t(s[2], s[3])) return true;
        for (let k = 1; k < 64; k++) { const u = k / 64; if (t(s[0] + (s[2] - s[0]) * u, s[1] + (s[3] - s[1]) * u)) return true; }
        return false;
      };
      const loopsOf = new Map<string, number[]>();
      P.items.key.forEach((k, i) => loopsOf.set(k, [...(loopsOf.get(k) ?? []), i]));
      const keysWhere = (ok: (e: number) => boolean, all: boolean) => {
        const out: string[] = [], seen = new Set<string>();
        for (let e = 0; e < P.items.key.length; e++) {
          const k = P.items.key[e]!;
          if (P.items.type[e] === 5 || seen.has(k) || !ok(e)) continue;
          const loops = loopsOf.get(k)!;
          const hit = all ? loops.every(i => segmentsOf(P, i).every(inBox)) : loops.some(i => segmentsOf(P, i).some(touches));
          if (hit) { seen.add(k); out.push(k); }
        }
        return out;
      };
      const wantInside = keysWhere(() => true, true);
      expect(wantInside.length).toBeGreaterThanOrEqual(6);
      await dragPage(page, a, b);
      expect((await H.events(page)).filter(e => e.type === 'select').at(-1)).toEqual({ type: 'select', keys: wantInside, mode: 'replace' });
      await dragPage(page, a, b, ['Alt']);
      const wantTouch = keysWhere(() => true, false);
      expect(wantTouch.length).toBeGreaterThanOrEqual(wantInside.length);
      expect(await H.selected(page)).toEqual(wantTouch);
      await H.set(page, { pick: 'block', selected: [] });
      await dragPage(page, a, b);
      const blockKeys = await H.selected(page);
      expect(blockKeys).toContain(pick!.anchor);
      expect(blockKeys.some(k => k.startsWith(pick!.anchor + '/'))).toBe(false);
      // layer-in-box: click one I-FURN line, then box: only that layer's items inside
      await H.set(page, { pick: 'layer-in-box', selected: [] });
      const lineOf = (layer: string) => wantInside.find(k => P.layers[P.items.layer[P.items.key.indexOf(k)]!] === layer && P.items.type[P.items.key.indexOf(k)] === 0);
      const layer = P.layers[P.items.layer[P.items.key.indexOf(wantInside[0]!)]!]!;
      const one = lineOf(layer) ?? wantInside[0]!;
      const e1 = P.items.key.indexOf(one), [s1] = segmentsOf(P, e1) as [Seg];
      await clickSheet(page, ...toM(P, (s1[0] + s1[2]) / 2, (s1[1] + s1[3]) / 2));
      await dragPage(page, a, b);
      const L = P.items.layer[e1]!;
      expect(await H.selected(page)).toEqual(keysWhere(e => P.items.layer[e] === L, true));
      expect(problems()).toEqual([]);
    });

    test('bank1: hovering names the item in the tooltip (layer, type, key) and reports it', async ({ page }) => {
      const { info, problems } = await open(page, 'bank1');
      const t = isolated('bank1', info.view.s, 12, () => true, 1)[0]!;
      const [px, py] = await H.toPage(page, ...t.at);
      await page.mouse.move(px, py);
      const tip = page.locator('[data-plan-tip]');
      await expect(tip).toBeVisible();
      const layer = fixture('bank1').plan.layers[fixture('bank1').plan.items.layer[t.e]!]!;
      await expect(tip).toHaveText(`${layer}\nline · ${t.key}`);
      const hov = (await H.events(page)).filter(e => e.type === 'hover').at(-1);
      expect(hov.info).toEqual({ layer, type: 0, key: t.key });
      expect(problems()).toEqual([]);
    });
  });
}

// ======================================================================================================== rooms (R6)
// The rooms milestone (docs/rooms/ACCEPTANCE.md 2.4 R6, RA-12 point 1's pixel checks): pixel probes on the house-rooms
// overlay over the house's plan (a room tint, a hatched hole, the furniture boxes; each tick switches its layer off),
// and on the reference building's overlay over the mock's plan of it (the dashed doorway closing and the climbable
// stair's walking line, drawn whatever the ticks say); the canvas's test hook window.__plan turns sheet points into
// clicks for the tools Rooms and stairs and Draw a line. The overlays are read here, in Node, and handed to the harness.
const HOUSE_ROOMS = readJson('fixtures/upload/overlay/house-rooms.overlay.json');
const SHOW = (rooms: boolean, plate: boolean, furniture: boolean) => ({ rooms, plate, furniture });
const tinted = (p: number[]) => p[2]! - p[0]! >= 10 && p[2]! >= 225 && p[0]! < 248;
const hatchy = (p: number[]) => Math.abs(p[0]! - p[1]!) < 25 && Math.abs(p[1]! - p[2]!) < 25 && lum(p) >= 95 && lum(p) <= 228;
const yellowish = (p: number[]) => p[0]! - p[2]! >= 20 && p[1]! - p[2]! >= 12 && lum(p) > 170;
const closingInk = (p: number[]) => p[0]! - p[2]! > 70 && p[1]! - p[2]! > 30 && p[0]! > 100;
const stairInk = (p: number[]) => p[1]! - p[0]! > 35 && p[1]! - p[2]! > 15;
const count = (px: number[][] | null, f: (p: number[]) => boolean) => (px ?? []).filter(f).length;
const hook = <T>(page: Page, fn: string, arg?: unknown) => page.evaluate(([f, a]) => {
  const h = (window as any).__plan;
  return h ? h[f as string](a) : null;
}, [fn, arg] as const) as Promise<T>;

test.describe('rooms milestone (R6): the overlay\'s rooms, plate, stairs and closings', () => {
  test('house-rooms, upper floor: rooms tinted, furniture boxes (and the holes inside its area hatched); each tick switches its layer off', async ({ page }) => {
    const { problems } = await open(page, 'sukhumvit');
    const upper = HOUSE_ROOMS.floors.find((f: any) => f.key === 'upper');
    await H.set(page, { overlayFloor: upper, focus: upper.area.bbox });
    await H.timeRedraw(page, 2);
    const spaces = await hook<{ id: string; area: number; at: [number, number] }[]>(page, 'spaces');
    expect(spaces, 'window.__plan (the web server sets VITE_WTV_TEST_HOOK=1)').not.toBeNull();
    expect(spaces.map(s => s.id)).toEqual(upper.spaces.map((s: any) => s.id));
    const big = spaces.filter(s => s.area >= 8);
    expect(big.length).toBeGreaterThanOrEqual(8);
    // the provisional (tracer) fixture wrote the upper floor's holes and stairs in the build frame, 74 m off the sheet
    // (R1.md N-11; contract-issues/R6.md D-3): only holes inside the floor's area are probed here. RI re-made the fixture
    // with the real rules, every field in the floor's sheet metres (RI.md), so every hole of the upper floor is probed
    const [ax0, ay0, ax1, ay1] = upper.area.bbox as number[];
    const holes = upper.holes.map((h: any) => insideOf(h.o, h.h)).filter(([x, y]: [number, number]) => x >= ax0! && x <= ax1! && y >= ay0! && y <= ay1!);
    expect(holes.length, 'every hole lies inside the floor\'s area').toBe(upper.holes.length);
    expect(holes.length).toBeGreaterThanOrEqual(1);
    const pieces = upper.furniture.filter((f: any) => f.w >= 0.6 && f.d >= 0.6).slice(0, 12);
    expect(pieces.length).toBeGreaterThanOrEqual(5);
    const measure = async () => ({
      rooms: await Promise.all(big.map(async s => count(await H.pixels(page, s.at[0], s.at[1], 3), tinted))),
      holes: await Promise.all(holes.map(async ([x, y]: [number, number]) => count(await H.pixels(page, x, y, 6), hatchy))),
      furniture: await Promise.all(pieces.map(async (f: any) => count(await H.pixels(page, f.x, f.y, 2), yellowish))),
    });
    const all = await measure();
    const note = JSON.stringify(all);
    expect(all.rooms.filter(n => n >= 20).length, note).toBeGreaterThanOrEqual(Math.ceil(big.length * 0.6));
    expect(all.furniture.filter(n => n >= 12).length, note).toBeGreaterThanOrEqual(Math.ceil(pieces.length * 0.6));

    await H.set(page, { show: SHOW(false, true, true) });
    const noRooms = await measure();
    expect(noRooms.rooms.filter(n => n >= 20).length, JSON.stringify(noRooms)).toBeLessThanOrEqual(Math.floor(big.length * 0.1));
    await H.set(page, { show: SHOW(true, false, true) });
    const noPlate = await measure();
    noPlate.holes.forEach((n, i) => expect(n, JSON.stringify(noPlate)).toBeLessThanOrEqual(all.holes[i]! - 8));
    await H.set(page, { show: SHOW(true, true, false) });
    const noFurniture = await measure();
    expect(noFurniture.furniture.filter(n => n >= 12).length, JSON.stringify(noFurniture)).toBeLessThanOrEqual(Math.floor(pieces.length * 0.1));
    await H.set(page, { show: SHOW(true, true, true) });
    expect((await measure()).rooms).toEqual(all.rooms);
    expect(problems()).toEqual([]);
  });

  test('the reference building, upper floor: the stair well and the void are hatched; the Floor plate tick takes them away', async ({ page }) => {
    const { problems } = await open(page, 'bank1');
    const upper = referenceOverlay().floors[1]!;
    const roles = (readJson('fixtures/rooms/settings.reference.json') as { layers: Record<string, string> }).layers;
    await page.evaluate(([j, r]) => (window as any).__planHarness.loadJson(j, r), [referencePlan('d'.repeat(40), 1), roles] as const);
    await H.set(page, { overlayFloor: upper });
    await H.timeRedraw(page, 2);
    const holes = upper.holes!.map(h => insideOf(h.o, h.h));
    expect(holes.length).toBe(2);
    const hatch = async () => Promise.all(holes.map(async ([x, y]) => count(await H.pixels(page, x, y, 6), hatchy)));
    const on = await hatch();
    await H.set(page, { show: SHOW(true, false, true) });
    const off = await hatch();
    on.forEach((n, i) => expect(n, `on ${on} off ${off}`).toBeGreaterThanOrEqual(off[i]! + 8));
    await H.set(page, { show: SHOW(true, true, true) });
    expect(await hatch()).toEqual(on);
    expect(problems()).toEqual([]);
  });

  test('the reference building: the doorway closing is dashed, the climbable stair has its walking line, whatever the ticks', async ({ page }) => {
    const { problems } = await open(page, 'bank1');
    const ground = referenceOverlay().floors[0]!;
    const roles = (readJson('fixtures/rooms/settings.reference.json') as { layers: Record<string, string> }).layers;
    await page.evaluate(([j, r]) => (window as any).__planHarness.loadJson(j, r), [referencePlan('c'.repeat(40), 0), roles] as const);
    await H.set(page, { overlayFloor: ground });
    await H.timeRedraw(page, 2);
    const c = ground.closings![0]!;
    const samples: number[] = [];
    for (let k = 0; k <= 40; k++) {
      const t = 0.1 + (0.8 * k) / 40;
      const px = await H.pixels(page, c.a[0] + (c.b[0] - c.a[0]) * t, c.a[1] + (c.b[1] - c.a[1]) * t, 0);
      samples.push(count(px, closingInk));
    }
    const inked = samples.filter(n => n > 0).length;
    expect(inked, samples.join('')).toBeGreaterThanOrEqual(8);                     // drawn
    expect(inked, samples.join('')).toBeLessThanOrEqual(36);                       // with gaps: dashed
    const walk = ground.stairs!.find(s => s.state === 'climb')!.walk!;
    const mids = walk.slice(1).map((p, i) => [(p[0] + walk[i]![0]) / 2, (p[1] + walk[i]![1]) / 2] as [number, number]);
    const onLine = async () => (await Promise.all(mids.map(async ([x, y]) => count(await H.pixels(page, x, y, 1), stairInk)))).filter(n => n > 0).length;
    expect(await onLine()).toBeGreaterThanOrEqual(Math.ceil(mids.length * 0.6));
    await H.set(page, { show: SHOW(false, false, false) });
    expect(await onLine()).toBeGreaterThanOrEqual(Math.ceil(mids.length * 0.6));
    const again: number[] = [];
    for (let k = 0; k <= 40; k++) {
      const t = 0.1 + (0.8 * k) / 40;
      again.push(count(await H.pixels(page, c.a[0] + (c.b[0] - c.a[0]) * t, c.a[1] + (c.b[1] - c.a[1]) * t, 0), closingInk));
    }
    expect(again.filter(n => n > 0).length).toBeGreaterThanOrEqual(8);
    expect(problems()).toEqual([]);
  });

  test('window.__plan turns sheet points into clicks: Rooms and stairs reports the room, the stair, the closing, the point; Draw a line its two ends', async ({ page }) => {
    const { problems } = await open(page, 'bank1');
    const ground = referenceOverlay().floors[0]!;
    const roles = (readJson('fixtures/rooms/settings.reference.json') as { layers: Record<string, string> }).layers;
    await page.evaluate(([j, r]) => (window as any).__planHarness.loadJson(j, r), [referencePlan('c'.repeat(40), 0), roles] as const);
    await H.set(page, { overlayFloor: ground, tool: 'rooms' });
    const spaces = await hook<{ id: string; at: [number, number] }[]>(page, 'spaces');
    const stairs = await hook<{ id: string; state: string; at: [number, number] }[]>(page, 'stairs');
    expect(stairs.map(s => [s.id, s.state])).toEqual([['S1', 'climb'], ['ground-ST2', 'lines']]);
    const clickAt = async (pt: [number, number]) => {
      const p = await hook<[number, number] | null>(page, 'toPage', pt);
      expect(p, `${pt} is on the canvas`).not.toBeNull();
      await page.mouse.click(p![0], p![1]);
    };
    await H.clear(page);
    await clickAt(spaces.find(s => s.id === 'ground-R002')!.at);
    await clickAt(stairs[1]!.at);
    const c = ground.closings![0]!;
    await clickAt([(c.a[0] + c.b[0]) / 2, (c.a[1] + c.b[1]) / 2]);
    await clickAt(insideOf(ground.unfloored![0]!.o));
    const ev = (await H.events(page)).filter(e => ['space', 'stair', 'closing', 'point'].includes(e.type));
    expect(ev.slice(0, 3)).toEqual([{ type: 'space', id: 'ground-R002' }, { type: 'stair', id: 'ground-ST2' }, { type: 'closing', index: 0 }]);
    expect(ev[3]?.type).toBe('point');
    await H.set(page, { tool: 'draw-line' });
    await H.clear(page);
    const m = ground.unfloored![0]!.mouth!;
    await clickAt(m[0]);
    await clickAt(m[1]);
    const line = (await H.events(page)).filter(e => e.type === 'line');
    expect(line.length).toBe(1);
    expect(Math.hypot(line[0].a[0] - m[0][0], line[0].a[1] - m[0][1])).toBeLessThan(0.15);
    expect(Math.hypot(line[0].b[0] - m[1][0], line[0].b[1] - m[1][1])).toBeLessThan(0.15);
    expect(problems()).toEqual([]);
  });
});

// ======================================================================================================== the budget
timedDescribe('redraw budget (A-10)', () => {
  test('the house sheet redraws in under 50 ms at 1400 x 880 (whole sheet; the ground floor, a highlight and dpr 2 reported)', async ({ page }, info) => {
    const { info: hi, problems } = await open(page, 'sukhumvit');
    expect(hi.size).toEqual({ w: 1400, h: 880 });
    expect(hi.count).toBeGreaterThan(30_000);
    await H.timeRedraw(page, 4);                                            // warm-up (the first read-back moves the canvas)
    const whole = await H.timeRedraw(page, 10);
    await H.set(page, { focus: [7.74826, 5.601038, 53.870897, 25.854851], area: 'ground' });
    await H.timeRedraw(page, 2);
    const ground = await H.timeRedraw(page, 10);
    await H.set(page, { highlight: 'XR_L44$0$I-FURN' });
    await H.timeRedraw(page, 2);
    const lit = await H.timeRedraw(page, 10);
    const note = `whole sheet median ${median(whole)} ms (max ${Math.max(...whole)}); ground floor ${median(ground)} ms; with the largest layer highlighted ${median(lit)} ms`;
    info.annotations.push({ type: 'redraw', description: note });
    console.log(`plan-canvas redraw: ${note}`);
    expect(median(whole), note).toBeLessThan(50);
    expect(median(ground), note).toBeLessThan(50);
    expect(problems()).toEqual([]);
  });

  test.describe('at device pixel ratio 2', () => {
    test.use({ deviceScaleFactor: 2 });
    test('the house sheet at dpr 2 (reported; the drawing stays 1 device-pixel hairlines)', async ({ page }, info) => {
      const { problems } = await open(page, 'sukhumvit');
      await H.timeRedraw(page, 4);
      const whole = await H.timeRedraw(page, 10);
      const note = `dpr 2 whole sheet median ${median(whole)} ms (max ${Math.max(...whole)})`;
      info.annotations.push({ type: 'redraw', description: note });
      console.log(`plan-canvas redraw: ${note}`);
      expect(median(whole), note).toBeLessThan(100);
      expect(problems()).toEqual([]);
    });
  });
});
