// Final check (UF): the owner's path in headless Edge on `npm run dev` (web 5710, API 8710), through the screens only
// (no settings sent through the API): the bank from its two DWGs (new project, upload, Files, Layers, Floors, Build,
// Check with a grey family given its kind and a rebuild, Save, the viewer, Walk, the downloads; the Max script compared
// byte for byte with bank_test/Bangkok_Bank_Sampeng.ms), then the house from its one DWG with its two floor areas
// drawn as boxes on the sheet. The API is read only to wait for runs and to compare. Holds the Edge lock.
//   node owner-path.mjs [bank|house|all]
import { createRequire } from 'node:module';
import { execFileSync } from 'node:child_process';
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import crypto from 'node:crypto';
import path from 'node:path';
import zlib from 'node:zlib';
import { pathToFileURL } from 'node:url';

const APP = 'C:/Users/DWP2/Desktop/Project walkthrough/app';
const PROJECT = path.resolve(APP, '..');
const W = path.join(process.env.TEMP, 'wt-uf');
const OUT = path.join(W, 'dev', 'path');
mkdirSync(OUT, { recursive: true });
const require = createRequire(`${APP}/package.json`);
const { chromium } = require('@playwright/test');
const { acquire, release } = await import(pathToFileURL(`${APP}/tools/edge-lock.mjs`).href);

const BASE = 'http://127.0.0.1:5710';
const WHICH = process.argv[2] ?? 'all';
const SYS_PY = 'C:/Python314/python.exe';
const log = [];
const facts = {};
const note = (step, ok, detail = '') => { log.push({ step, ok, detail, at: new Date().toISOString() }); console.log(`${ok ? 'ok  ' : 'FAIL'} ${step}${detail ? ': ' + detail : ''}`); };
const sha1 = b => crypto.createHash('sha1').update(b).digest('hex');
const sleep = ms => new Promise(r => setTimeout(r, ms));
const esc = s => String(s).replace(/\\/g, '\\\\').replace(/"/g, '\\"');
const role = (layers, name) => layers[name] ?? 'other';
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const formatDate = iso => { const d = new Date(iso); return `${d.getDate()} ${MONTHS[d.getMonth()]} ${d.getFullYear()}`; };

async function until(what, fn, timeout = 120_000, every = 500) {
  const t0 = Date.now();
  for (;;) {
    const v = await fn().catch(() => null);
    if (v) return v;
    if (Date.now() - t0 > timeout) throw new Error(`timed out after ${timeout / 1000} s: ${what}`);
    await sleep(every);
  }
}

function builderPy(args) {
  return execFileSync(process.execPath, ['tools/run-builder-py.mjs', ...args], { cwd: APP, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] });
}
function msdiff(a, b) {
  return JSON.parse(execFileSync(SYS_PY, ['-B', path.join(W, 'scripts', 'msdiff.py'), a, b], { encoding: 'utf8', env: { ...process.env, PYTHONIOENCODING: 'utf-8' } }));
}

await acquire('uf-owner-path');
const browser = await chromium.launch({ channel: 'msedge', headless: true,
  args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
const context = await browser.newContext({ viewport: { width: 1400, height: 880 }, acceptDownloads: true, baseURL: BASE });
const page = await context.newPage();
const dialogs = [], errors = [], consoleErrors = [];
page.on('dialog', d => { dialogs.push(d.message()); void d.dismiss(); });
page.on('pageerror', e => errors.push(String(e).slice(0, 400)));
page.on('console', m => { if (m.type() === 'error') consoleErrors.push(m.text().slice(0, 300)); });
let n = 0;
const shot = async name => { n += 1; const f = path.join(OUT, `${String(n).padStart(2, '0')}-${name}.png`); await page.screenshot({ path: f }); return f; };
const tid = id => page.getByTestId(id);
const api = context.request;
const getJson = async url => { const r = await api.get(url); if (!r.ok()) throw new Error(`GET ${url} -> ${r.status()}`); return r.json(); };
const getBuild = (pid, bid, withSettings = true) => getJson(`/api/projects/${pid}/builds/${bid}${withSettings ? '' : '?withSettings=false'}`);

async function waitReading(pid, bid) {
  return until('the reading (prepare) adopted', async () => {
    const d = await getBuild(pid, bid);
    const r = d.run;
    if (!r || r.status === 'queued' || r.status === 'running') return null;
    if (r.status !== 'done') throw new Error(`prepare ${r.status}: ${JSON.stringify(r.error)}`);
    return d.settingsRevision >= 1 && d.settings ? d : null;
  }, 15 * 60_000, 1000);
}
async function waitResult(pid, bid, afterRun) {
  return until('the build run done', async () => {
    const d = await getBuild(pid, bid, false);
    const r = d.run;
    if (!r || r.kind !== 'build' || r.status === 'queued' || r.status === 'running') return null;
    if (r.status !== 'done') throw new Error(`build ${r.status}: ${JSON.stringify(r.error)}`);
    return d.result && d.result.runId !== afterRun ? d : null;
  }, 15 * 60_000, 1000);
}
/** Polls the API until pred(settings) holds (what the screens typed has been saved). */
async function savedWhen(pid, bid, what, pred) {
  return until(`saved: ${what}`, async () => { const d = await getBuild(pid, bid); return pred(d.settings, d) ? d : null; }, 60_000, 700);
}
async function typeIn(loc, value) {
  await loc.scrollIntoViewIfNeeded();
  await loc.fill(String(value));
  await loc.press('Enter');
}
async function goStep(step) {
  await tid(`step-${step}`).click();
  await until(`step ${step}`, async () => (await tid('build-page').getAttribute('data-step')) === step, 30_000);
}

async function newProject({ name, shortName, projectNo, officeName, id }) {
  await page.goto('/projects');
  await tid('new-project').waitFor({ timeout: 60_000 });
  await tid('new-project').click();
  await tid('np-name').fill(name);
  if (shortName) await tid('np-short-name').fill(shortName);
  if (projectNo) await tid('np-project-no').fill(projectNo);
  if (officeName) {
    await tid('office-select').selectOption('__new__');
    await tid('new-office-name').fill(officeName);
  }
  await tid('np-id').fill(id);
}

async function upload(files, tag) {
  const t = Date.now();
  await tid('file-input').setInputFiles(files);
  await until('uploads done', async () => (await page.locator('[data-testid=upload-row][data-state=done]').count()) === files.length, 300_000);
  const up = (Date.now() - t) / 1000;
  await shot(`${tag}-upload`);
  await tid('start-build').click();
  await page.waitForURL(/\?step=files$/, { timeout: 60_000 });
  const buildId = await tid('build-page').getAttribute('data-build-id');
  return { buildId, seconds: up };
}

/** The layer roles the screens must change to reach `target` (a role missing from a map is `other`). */
function layerChanges(current, target) {
  const names = [...new Set([...Object.keys(current), ...Object.keys(target)])].sort();
  return names.filter(nm => role(current, nm) !== role(target, nm) && nm in current).map(nm => [nm, role(target, nm)]);
}
async function setLayers(pid, bid, target, tag) {
  await goStep('layers');
  await page.locator('[data-testid=layer-row]').first().waitFor({ timeout: 60_000 });
  const rows = await page.locator('[data-testid=layer-row]').count();
  const d0 = await getBuild(pid, bid);
  const changes = layerChanges(d0.settings.layers, target);
  for (const [layer, r] of changes) {
    const sel = page.locator(`[data-testid=layer-row][data-layer="${esc(layer)}"] [data-testid=role-select]`);
    await sel.scrollIntoViewIfNeeded();
    await sel.selectOption(r);
  }
  const d = await savedWhen(pid, bid, 'layer roles', (s, b) => changes.every(([l, r]) => s.layers[l] === r) && !!b.layersReviewedAt);
  const notInDrawing = Object.keys(target).filter(l => !(l in d.settings.layers));
  const wrong = Object.keys(d.settings.layers).filter(l => role(d.settings.layers, l) !== role(target, l));
  await shot(`${tag}-layers`);
  return { rows, changes, wrong, notInDrawing, layersReviewedAt: d.layersReviewedAt };
}

const PROJECT_FIELDS = { name: 'project-name', shortName: 'project-short-name', projectNo: 'project-no', exportedFrom: 'exported-from',
  photoName: 'photo-name', maxPrefix: 'max-prefix', maxFileName: 'max-file-name' };
async function setProjectDetails(pid, bid, want) {
  const d = await getBuild(pid, bid);
  const typed = [];
  for (const [k, testId] of Object.entries(PROJECT_FIELDS)) {
    if ((d.settings.project[k] ?? null) !== (want[k] ?? null)) { await typeIn(tid(testId), want[k] ?? ''); typed.push(k); }
  }
  await savedWhen(pid, bid, 'project details', s => Object.keys(PROJECT_FIELDS).every(k => (s.project[k] ?? null) === (want[k] ?? null)));
  return typed;
}

/** The live plan view of a canvas: the controller through the dev server's own module (the same instance the page uses). */
async function liveView(canvasSel) {
  return page.evaluate(async sel => {
    const c = document.querySelector(sel);
    if (!c) return { error: 'no canvas' };
    try {
      const m = await import('/src/plan/controller.ts');
      const ctl = m.controllerOf.get(c);
      if (!ctl || !ctl.view) return { error: 'no controller for the canvas' };
      const r = c.getBoundingClientRect();
      return { view: ctl.view, size: ctl.size, origin: ctl.data.origin, quantum: ctl.data.quantum, rect: { x: r.left, y: r.top, w: r.width, h: r.height } };
    } catch (e) { return { error: String(e) }; }
  }, canvasSel);
}
/** Fallback: the view F gives (plan/view.ts fitView of decode.ts's robust fit box), worked out from the plan geometry. */
async function fittedView(canvasSel, planUrl) {
  const res = await api.get(planUrl);
  let buf = await res.body();
  if (buf[0] === 0x1f && buf[1] === 0x8b) buf = zlib.gunzipSync(buf);
  const plan = JSON.parse(buf.toString('utf8'));
  const pts = plan.pts, m = pts.length / 2;
  let bx0 = Infinity, by0 = Infinity, bx1 = -Infinity, by1 = -Infinity;
  const it = plan.items;
  for (let i = 0; i < it.key.length; i++) {
    for (let k = it.first[i]; k < it.first[i] + it.count[i]; k++) {
      const x = pts[2 * k], y = pts[2 * k + 1];
      if (x < bx0) bx0 = x; if (x > bx1) bx1 = x; if (y < by0) by0 = y; if (y > by1) by1 = y;
    }
  }
  let box = [bx0, by0, bx1, by1];
  if (m >= 50) {
    const xs = Int32Array.from({ length: m }, (_, i) => pts[2 * i]).sort(), ys = Int32Array.from({ length: m }, (_, i) => pts[2 * i + 1]).sort();
    const lo = Math.floor(m * 0.01), hi = Math.max(lo, Math.floor(m * 0.99) - 1);
    const r = [xs[lo], ys[lo], xs[hi], ys[hi]];
    const area = b => Math.max(1, b[2] - b[0]) * Math.max(1, b[3] - b[1]);
    if (area(box) > 4 * area(r)) {
      const gx = Math.ceil((r[2] - r[0]) * 0.1), gy = Math.ceil((r[3] - r[1]) * 0.1);
      box = [Math.max(box[0], r[0] - gx), Math.max(box[1], r[1] - gy), Math.min(box[2], r[2] + gx), Math.min(box[3], r[3] + gy)];
    }
  }
  const rect = await page.locator(canvasSel).evaluate(c => { const r = c.getBoundingClientRect(); return { x: r.left, y: r.top, w: r.width, h: r.height }; });
  const size = { w: rect.w, h: rect.h };
  const s = Math.min(40, Math.max(1, size.w - 48) / Math.max(1, box[2] - box[0]), Math.max(1, size.h - 48) / Math.max(1, box[3] - box[1]));
  return { view: { cx: (box[0] + box[2]) / 2, cy: (box[1] + box[3]) / 2, s }, size, origin: plan.origin, quantum: plan.quantum, rect, fallback: true };
}
const toScreen = (lv, x, y) => {
  const qx = (x - lv.origin[0]) / lv.quantum, qy = (y - lv.origin[1]) / lv.quantum;
  return [lv.rect.x + (qx - lv.view.cx) * lv.view.s + lv.size.w / 2, lv.rect.y + (lv.view.cy - qy) * lv.view.s + lv.size.h / 2];
};
/** Draws a floor's area: "Draw a box", F to fit the sheet, then a mouse drag from one corner of `bbox` to the other. */
async function drawBox(i, bbox, planUrl) {
  const card = page.locator(`[data-testid=floor-card][data-index="${i}"]`);
  await card.getByTestId('area-draw').click();
  await until('box tool on', async () => (await tid('floors-tool').count()) > 0, 10_000);
  const canvasSel = '[data-testid=floors-canvas] canvas';
  await page.locator(canvasSel).evaluate(el => el.scrollIntoView({ block: 'center' }));
  await sleep(300);
  await page.locator(canvasSel).evaluate(el => el.focus({ preventScroll: true }));
  await page.keyboard.press('f');
  await sleep(600);
  let lv = await liveView(canvasSel);
  if (lv.error) {
    const why = lv.error;
    lv = await fittedView(canvasSel, planUrl);
    lv.why = why;
  }
  const vp = page.viewportSize();
  if (lv.rect.y < 0 || lv.rect.y + lv.rect.h > vp.height || lv.rect.x < 0 || lv.rect.x + lv.rect.w > vp.width) {
    throw new Error(`the sheet is not wholly on screen: ${JSON.stringify(lv.rect)}`);
  }
  const [ax, ay] = toScreen(lv, bbox[0], bbox[3]);
  const [bx, by] = toScreen(lv, bbox[2], bbox[1]);
  await page.mouse.move(ax, ay);
  await page.mouse.down();
  for (let k = 1; k <= 10; k++) await page.mouse.move(ax + (bx - ax) * k / 10, ay + (by - ay) * k / 10);
  await page.mouse.up();
  await until('the box tool ends', async () => (await tid('floors-tool').count()) === 0, 10_000);
  const got = [];
  for (const k of ['x0', 'y0', 'x1', 'y1']) got.push(Number(await card.getByTestId(`box-${k}`).inputValue()));
  return { drawn: got, screen: [[ax, ay], [bx, by]], scale: lv.view.s, metresPerPixel: lv.quantum / lv.view.s, viewFrom: lv.fallback ? `worked out (${lv.why})` : 'the live canvas' };
}
async function pickLevelTag(i, value) {
  const card = page.locator(`[data-testid=floor-card][data-index="${i}"]`);
  const det = card.getByTestId('level-tags');
  if (!(await det.evaluate(e => e.open))) await det.locator('summary').click();
  const tags = card.getByTestId('level-tag');
  const values = await tags.evaluateAll(els => els.map(e => Number(e.getAttribute('data-value'))));
  const k = values.findIndex(v => Math.abs(v - value) < 0.0005);
  if (k < 0) throw new Error(`no level tag ${value} in ${values.join(', ')}`);
  const text = await tags.nth(k).textContent();
  await tags.nth(k).click();
  await det.locator('summary').click();
  return { picked: text, tags: values.length };
}
async function setFloors(pid, bid, floors) {
  await goStep('floors');
  await page.locator('[data-testid=floor-card]').first().waitFor({ timeout: 30_000 });
  await until('the sheet', async () => (await page.locator('[data-testid=floors-canvas] canvas').count()) === 1, 60_000);
  const out = [];
  const det = await getBuild(pid, bid);
  for (const [i, f] of floors.entries()) {
    const card = page.locator(`[data-testid=floor-card][data-index="${i}"]`);
    const r = { key: f.key };
    if (f.keyName) { await typeIn(card.getByTestId('floor-key'), f.key); await typeIn(card.getByTestId('floor-name'), f.name); }
    if (f.box) r.box = await drawBox(i, f.box, det.sources.find(x => x.sha1 === det.settings.floors[i].source).urls.plan);
    if (f.levelTag !== undefined) r.level = await pickLevelTag(i, f.levelTag);
    else await typeIn(card.getByTestId('floor-level'), f.level);
    for (const [field, testId] of [['wallHeight', 'floor-wall-height'], ['doorHead', 'floor-door-head'], ['windowSill', 'floor-window-sill'], ['windowHead', 'floor-window-head']]) {
      if (f[field] !== undefined && f[field] !== null) await typeIn(card.getByTestId(testId), f[field]);
    }
    out.push(r);
  }
  return out;
}

async function build(pid, bid, tag, afterRun) {
  await goStep('build');
  const checklist = await tid('prebuild-checklist').textContent({ timeout: 30_000 }).catch(() => '');
  const clear = (await tid('checklist-clear').count()) > 0;
  await shot(`${tag}-build-checklist`);
  const t = Date.now();
  await tid('run-build').click();
  await page.locator('[data-testid=run-panel][data-kind=build]').waitFor({ timeout: 60_000 });
  const sawRunning = await until('running shown', async () => (await page.locator('[data-testid=run-panel][data-kind=build][data-status=running]').count()) > 0, 300_000, 200).catch(() => false);
  if (sawRunning) await shot(`${tag}-build-running`);
  const d = await waitResult(pid, bid, afterRun);
  await tid('build-result').waitFor({ timeout: 60_000 });
  await sleep(1500);
  await shot(`${tag}-build-done`);
  return { d, seconds: (Date.now() - t) / 1000, clear, checklist: checklist.slice(0, 400), sawRunning: !!sawRunning };
}

/** Check step: each floor's plan, flags and grey families; families named in `words` get their kind; then Rebuild. */
async function check(pid, bid, tag, words, first) {
  await goStep('check');
  await page.locator('[data-testid=check-canvas] canvas').waitFor({ timeout: 60_000 });
  await sleep(2000);
  await shot(`${tag}-check`);
  const floors = await page.locator('[data-testid=check-floor]').evaluateAll(els => els.map(e => e.getAttribute('data-key')));
  const seen = {}, given = [], flagsPerFloor = {};
  // a grey family gets the kind of the first settings word that names it, matched as the furniture kit matches its office
  // words (furniture_kit._rx: whole words, a space between tokens matching spaces, '_' or '-', an optional plural s, any
  // case; the kinds in sorted order; the family split at camel case): what staff do when they read "Maker_X - Default"
  const kitRx = w => new RegExp(`(?<![a-z])(?:${w.split(/\s+/).filter(Boolean).map(t => t.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('[\\s_\\-]*')})s?(?![a-z])`, 'i');
  const camel = s => s.replace(/(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])/g, ' ');
  const want = Object.keys(words).sort().flatMap(kind => words[kind].map(w => ({ word: w, kind, rx: kitRx(w) })));
  const used = new Set();
  for (const k of floors) {
    await page.locator(`[data-testid=check-floor][data-key="${esc(k)}"]`).click();
    await sleep(1200);
    flagsPerFloor[k] = await page.locator('[data-testid=flag]').count();
    const fams = await page.locator('[data-testid=furniture-family]').evaluateAll(els => els.map(e => e.getAttribute('data-family')));
    seen[k] = fams;
    for (const fam of fams) {
      if (given.some(g => g[0] === fam)) continue;
      const hit = want.find(w => w.rx.test(camel(fam)));
      if (!hit) continue;
      await page.locator(`[data-testid=furniture-family][data-family="${esc(fam)}"] [data-testid=furniture-word-kind]`).selectOption(hit.kind);
      given.push([fam, hit.kind, hit.word]);
      used.add(hit.word);
      await sleep(300);
    }
  }
  const missing = want.filter(w => !used.has(w.word)).map(w => w.word);
  if (given.length) await savedWhen(pid, bid, 'furniture words', s => given.every(([fam, kind]) => (s.furniture.words[kind] ?? []).includes(fam)));
  await shot(`${tag}-check-words`);
  let rebuilt = null;
  if (given.length) {
    await tid('rebuild').click();
    const t = Date.now();
    const d = await waitResult(pid, bid, first.result.runId);
    await sleep(2000);
    const panel = page.locator('[data-testid=diff-panel][data-against=previous-run]');
    await panel.waitFor({ timeout: 60_000 }).catch(() => {});
    const same = (await panel.count()) ? (await panel.getAttribute('data-same')) !== null : null;
    const summary = (await tid('diff-summary').count()) ? await tid('diff-summary').first().textContent() : '';
    await shot(`${tag}-check-rebuilt`);
    rebuilt = { d, seconds: (Date.now() - t) / 1000, diffSame: same, diffSummary: summary };
  }
  return { floors, flagsPerFloor, families: seen, given, missing, rebuilt };
}

async function save(pid, tag) {
  await goStep('save');
  await tid('save-build').waitFor({ timeout: 30_000 });
  const summary = ((await tid('save-summary').textContent().catch(() => '')) ?? '').replace(/\s+/g, ' ').slice(0, 400);
  const label = await tid('save-label').inputValue().catch(() => '');
  const carry = (await tid('carry-heights').count()) ? await tid('carry-heights').getAttribute('data-state') : null;
  const remember = (await tid('remember-mapping').count()) ? await tid('remember-mapping').getAttribute('data-state') : null;
  await shot(`${tag}-save`);
  await tid('save-build').click();
  await page.waitForURL(new RegExp(`/projects/${pid}/v/1$`), { timeout: 120_000 });
  return { summary, label, carry, remember, url: page.url() };
}

async function viewerAndWalk(tag) {
  const area = page.locator('[data-testid=viewer-area] canvas');
  await until('one viewer canvas', async () => (await area.count()) === 1, 90_000);
  const walkBtn = page.locator('[data-wt=modes] [data-mode=walk]');
  await walkBtn.waitFor({ timeout: 90_000 });
  await sleep(4000);
  const viewerErr = await tid('viewer-error').count() + await tid('model-error').count();
  await shot(`${tag}-viewer`);
  const before = await area.screenshot();
  await walkBtn.click();
  await until('Walk pressed', async () => (await walkBtn.getAttribute('aria-pressed')) === 'true', 15_000);
  await sleep(2000);
  const start = await area.screenshot();
  const hud = ((await page.locator('[data-wt=hud-text]').textContent().catch(() => '')) ?? '').replace(/\s+/g, ' ').trim();
  await page.keyboard.down('KeyW'); await sleep(1500); await page.keyboard.up('KeyW');
  await sleep(700);
  const moved = await area.screenshot();
  await page.keyboard.down('ArrowLeft'); await sleep(900); await page.keyboard.up('ArrowLeft');
  await sleep(700);
  const turned = await area.screenshot();
  await shot(`${tag}-walk`);
  await page.locator('[data-wt=modes] [data-mode=orbit]').click();
  await sleep(1000);
  return { canvases: await page.locator('canvas').count(), viewerErr, hud, enteredWalk: !before.equals(start), movedForward: !start.equals(moved), turned: !moved.equals(turned) };
}

async function downloads(tag, keys) {
  const got = {};
  for (const key of keys) {
    await tid('downloads-menu').click();
    const item = page.locator(`[data-testid=downloads-list] [data-download=${key}]`);
    await item.waitFor({ timeout: 30_000 });
    const [d] = await Promise.all([page.waitForEvent('download', { timeout: 180_000 }), item.click()]);
    const file = path.join(OUT, `${tag}-${d.suggestedFilename()}`);
    await d.saveAs(file);
    got[key] = { name: d.suggestedFilename(), file, bytes: readFileSync(file).length, sha1: sha1(readFileSync(file)) };
    await page.keyboard.press('Escape');
    await sleep(500);
  }
  return got;
}

async function offlineOpens(file, tag) {
  const ctx = await browser.newContext({ viewport: { width: 1400, height: 880 }, offline: true });
  const off = await ctx.newPage();
  const reqs = [], errs = [];
  off.on('request', r => { const u = r.url(); if (!/^(file|data|blob):/.test(u)) reqs.push(u); });
  off.on('pageerror', e => errs.push(String(e).slice(0, 300)));
  await off.goto(pathToFileURL(file).href);
  await off.waitForFunction(() => document.querySelectorAll('canvas').length > 0, null, { timeout: 90_000 });
  await sleep(4000);
  await off.screenshot({ path: path.join(OUT, `${String(++n).padStart(2, '0')}-${tag}-offline-file.png`) });
  const canvases = await off.locator('canvas').count();
  await ctx.close();
  return { requests: reqs, errors: errs, canvases };
}

function settingsDiff(s, fx, ignore = []) {
  const out = [];
  const cmp = (p, a, b) => { if (JSON.stringify(a) !== JSON.stringify(b)) out.push(`${p}: ${JSON.stringify(a)?.slice(0, 160)} (fixture ${JSON.stringify(b)?.slice(0, 160)})`); };
  const lay = [...new Set([...Object.keys(s.layers), ...Object.keys(fx.layers)])].sort();
  for (const l of lay) if (role(s.layers, l) !== role(fx.layers, l)) out.push(`layers.${l}: ${role(s.layers, l)} (fixture ${role(fx.layers, l)})`);
  for (const k of ['project', 'defaults', 'options', 'vocabulary', 'fixes']) if (!ignore.includes(k)) cmp(k, s[k], fx[k]);
  cmp('furniture (all but words)', { ...s.furniture, words: null }, { ...fx.furniture, words: null });
  cmp('sources', s.sources.map(x => ({ ...x })), fx.sources);
  s.floors.forEach((f, i) => { const g = fx.floors[i] ?? {}; for (const k of Object.keys({ ...f, ...g })) if (!ignore.includes(`floors.${k}`)) cmp(`floors[${i}].${k}`, f[k], g[k]); });
  if (s.office !== fx.office) out.push(`office: ${s.office} (fixture ${fx.office})`);
  return out;
}

// ------------------------------------------------------------------------------------------------------------ the bank
async function bankPath() {
  const PID = 'owner-bank';
  const fx = JSON.parse(readFileSync(`${APP}/fixtures/upload/settings/bank.json`, 'utf8'));
  const R = facts.bank = {};
  await page.goto('/projects');
  await tid('new-project').waitFor({ timeout: 60_000 });
  const cards = await page.locator('[data-testid=project-card]').count();
  await shot('bank-project-list');
  note('1 project list', cards === 4, `${cards} project cards (the four seeded projects)`);

  await newProject({ name: fx.project.name, shortName: fx.project.shortName, projectNo: fx.project.projectNo, officeName: 'Owner Revit', id: PID });
  await shot('bank-new-project');
  await tid('np-create').click();
  await tid('upload-page').waitFor({ timeout: 30_000 });
  note('2 new project', page.url().endsWith(`/projects/${PID}/builds/new`), `${page.url()} (office "Owner Revit", new)`);

  const dwgs = ['I1201 - LEVEL 1 GENERAL ARRANGEMENT.dwg', 'I1202 - LEVEL 2 GENERAL ARRANGEMENT.dwg'].map(f => path.join(PROJECT, f));
  const up = await upload(dwgs, 'bank');
  R.upload = up;
  note('3 upload', true, `2 DWGs from the project root uploaded in ${up.seconds} s; build ${up.buildId}`);

  const tPrep = Date.now();
  await shot('bank-files-reading');
  await until('verdicts', async () => (await page.locator('[data-testid=source-card] [data-testid=source-verdict]').count()) === 2 &&
    (await page.locator('[data-testid=source-card] [data-testid=source-verdict][data-verdict=ok]').count()) === 2, 15 * 60_000, 1000);
  const prep = await waitReading(PID, up.buildId);
  await until('units enabled', async () => page.locator('[data-testid=source-card] [data-testid=units-select]').first().isEnabled(), 120_000);
  const verdicts = await page.locator('[data-testid=source-card]').evaluateAll(els => els.map(e => `${e.querySelector('[data-testid=source-name]')?.textContent}: ${e.querySelector('[data-testid=source-verdict]')?.getAttribute('data-verdict')}`));
  R.prepare = { seconds: (Date.now() - tPrep) / 1000, steps: prep.run.steps?.map(s => `${s.name} ${s.seconds}`), verdicts };
  await shot('bank-files');
  note('4 Files', verdicts.length === 2 && verdicts.every(v => v.endsWith(': ok')), `${verdicts.join('; ')}; read in ${R.prepare.seconds.toFixed(1)} s`);

  R.layers = await setLayers(PID, up.buildId, fx.layers, 'bank');
  note('5 Layers', R.layers.wrong.length === 0, `${R.layers.rows} rows; ${R.layers.changes.length} roles changed with their selects: ${R.layers.changes.map(([l, r]) => `${l} -> ${r}`).join(', ')}; all roles now the bank's${R.layers.wrong.length ? ' EXCEPT ' + R.layers.wrong.join(', ') : ''}`);

  R.floors = await setFloors(PID, up.buildId, fx.floors.map(f => ({ key: f.key, level: f.level, wallHeight: f.wallHeight })));
  R.projectTyped = await setProjectDetails(PID, up.buildId, fx.project);
  const fl = await savedWhen(PID, up.buildId, 'floors', s => s.floors.every((f, i) => f.level === fx.floors[i].level && f.wallHeight === fx.floors[i].wallHeight));
  const floorIssues = await tid('floor-issues').count();
  await shot('bank-floors');
  note('6 Floors', floorIssues === 0, `levels ${fl.settings.floors.map(f => f.level).join(' / ')}, wall heights ${fl.settings.floors.map(f => f.wallHeight).join(' / ')}; typed in Project details: ${R.projectTyped.join(', ')}; no floor issues`);

  const b1 = await build(PID, up.buildId, 'bank', null);
  R.build1 = { seconds: b1.seconds, stamp: b1.d.result.stamp, counts: b1.d.result.counts, clear: b1.clear, sawRunning: b1.sawRunning };
  note('7 Build', b1.d.run.status === 'done' && b1.clear, `checklist clear: ${b1.clear}; progress seen: ${b1.sawRunning}; done in ${b1.seconds.toFixed(1)} s; stamp ${b1.d.result.stamp}`);

  const ck = await check(PID, up.buildId, 'bank', fx.furniture.words, b1.d);
  R.check = { floors: ck.floors, flags: ck.flagsPerFloor, families: ck.families, given: ck.given, missing: ck.missing,
    rebuild: ck.rebuilt && { seconds: ck.rebuilt.seconds, stamp: ck.rebuilt.d.result.stamp, diffSame: ck.rebuilt.diffSame, diffSummary: ck.rebuilt.diffSummary } };
  note('8 Check', !!ck.rebuilt && ck.missing.length === 0 && ck.rebuilt.diffSame === false,
    `plan and flags on ${ck.floors.join(', ')} (${Object.entries(ck.flagsPerFloor).map(([k, v]) => `${k} ${v} flags`).join(', ')}); grey families ${JSON.stringify(ck.families)}; given a kind: ${ck.given.map(g => g.join(' -> ')).join(', ')}; rebuilt in ${ck.rebuilt?.seconds.toFixed(1)} s, stamp ${ck.rebuilt?.d.result.stamp}, the diff against the first build shows the change: ${ck.rebuilt?.diffSame === false} (${(ck.rebuilt?.diffSummary ?? '').replace(/\s+/g, ' ').slice(0, 160)})`);

  const sNow = (await getBuild(PID, up.buildId)).settings;
  R.settingsAgainstFixture = settingsDiff(sNow, fx);
  R.words = sNow.furniture.words;
  note('8b settings made on the screens = the bank fixture', R.settingsAgainstFixture.every(d => d.startsWith('office:')),
    `${R.settingsAgainstFixture.join(' | ') || 'identical'}; furniture words on the screens ${JSON.stringify(sNow.furniture.words)} (the fixture's ${JSON.stringify(fx.furniture.words)})`);

  R.save = await save(PID, 'bank');
  note('9 Save', true, `${R.save.url}; label "${R.save.label}"; remember roles ${R.save.remember}; ${R.save.summary}`);

  R.viewer = await viewerAndWalk('bank');
  note('10 viewer', R.viewer.canvases === 1 && R.viewer.viewerErr === 0, `${R.viewer.canvases} canvas, no viewer error`);
  note('11 Walk', R.viewer.enteredWalk && R.viewer.movedForward && R.viewer.turned, `Walk on: the view changed ${R.viewer.enteredWalk}; W moved the view ${R.viewer.movedForward}; Left turned it ${R.viewer.turned}; HUD "${R.viewer.hud.slice(0, 120)}"`);

  const got = await downloads('bank', ['maxScript', 'furnitureCsv', 'offlineHtml']);
  R.downloads = got;
  const proto = path.join(PROJECT, 'bank_test', 'Bangkok_Bank_Sampeng.ms');
  const cmpProto = msdiff(proto, got.maxScript.file);
  R.msAgainstPrototype = cmpProto;
  // the saved model, the bank-27oct profile on it, the upload profile with the build's date
  const modelRes = await api.get(`/api/projects/${PID}/versions/1/model`);
  const modelFile = path.join(OUT, 'bank-model.json');
  writeFileSync(modelFile, await modelRes.body());
  const modelSha1 = sha1(readFileSync(modelFile));
  const ms27 = path.join(OUT, 'bank-27oct-from-saved-model.ms');
  builderPy(['-m', 'walkthrough_builder.out', modelFile, '--profile', 'bank-27oct', '--out', ms27]);
  const cmp27 = msdiff(proto, ms27);
  const last = ck.rebuilt?.d ?? b1.d;
  const date = formatDate(last.result.finishedAt);
  const expUp = path.join(OUT, 'bank-expected-upload.ms');
  builderPy(['-m', 'walkthrough_builder.out', modelFile, '--profile', 'upload', '--date', date, '--sources', 'dwg:mm,dwg:mm', '--converter-version', '0.14', '--out', expUp]);
  const cmpUp = msdiff(expUp, got.maxScript.file);
  const csvEq = readFileSync(got.furnitureCsv.file).equals(readFileSync(path.join(APP, 'fixtures', 'csv', 'bank-v2.csv')));
  R.model = { sha1: modelSha1, equalsV2: modelSha1 === 'c3a9408304a240b83c36f5c5c53db56b50a72c64' };
  R.ms27 = cmp27; R.msUpload = { equal: cmpUp.equal, date, diff: cmpUp.diff.slice(0, 20) };
  note('12 model', R.model.equalsV2, `the saved model is v2's byte for byte: sha1 ${modelSha1}`);
  note('13 Max script downloaded vs bank_test/Bangkok_Bank_Sampeng.ms', cmpProto.equal,
    `${got.maxScript.name}: byte-equal ${cmpProto.equal}; ${cmpProto.lines[1]} CRLF lines against ${cmpProto.lines[0]}; ${cmpProto.removed} prototype lines differ (${cmpProto.added} in the download)`);
  note('13b the same model through the 27 Oct text profile', cmp27.equal, `byte for byte equal to Bangkok_Bank_Sampeng.ms: ${cmp27.equal} (sha1 ${cmp27.sha1[1]}, ${cmp27.lines[1]} lines)`);
  note('13c the download = the upload profile made for this build', cmpUp.equal, `generated with the build's date ${date}: equal ${cmpUp.equal}`);
  note('14 CSV', csvEq, `${got.furnitureCsv.name} equals v2's CSV (fixtures/csv/bank-v2.csv): ${csvEq}`);
  const off = await offlineOpens(got.offlineHtml.file, 'bank');
  R.offline = off;
  note('15 offline file', off.requests.length === 0 && off.errors.length === 0 && off.canvases >= 1, `${got.offlineHtml.name} (${got.offlineHtml.bytes} B) opened from disk with the network off: ${off.canvases} canvas, ${off.requests.length} network requests, ${off.errors.length} errors`);
}

// ----------------------------------------------------------------------------------------------------------- the house
async function housePath() {
  const PID = 'owner-house';
  const fx = JSON.parse(readFileSync(`${APP}/fixtures/upload/settings/house.json`, 'utf8'));
  const R = facts.house = {};
  await newProject({ name: fx.project.name, shortName: fx.project.shortName, id: PID });
  await shot('house-new-project');
  await tid('np-create').click();
  await tid('upload-page').waitFor({ timeout: 30_000 });
  note('H1 new project', page.url().endsWith(`/projects/${PID}/builds/new`), `${page.url()} (no office)`);

  const up = await upload([path.join(PROJECT, 'Test Sukhumvit Residence.dwg')], 'house');
  R.upload = up;
  note('H2 upload', true, `the one DWG uploaded in ${up.seconds} s; build ${up.buildId}`);

  const tPrep = Date.now();
  await until('verdict', async () => (await page.locator('[data-testid=source-card] [data-testid=source-verdict]').count()) === 1 &&
    (await page.locator('[data-testid=source-card] [data-testid=source-verdict][data-verdict=minor]').count()) === 1, 15 * 60_000, 1000);
  const prep = await waitReading(PID, up.buildId);
  await until('units enabled', async () => page.locator('[data-testid=source-card] [data-testid=units-select]').first().isEnabled(), 120_000);
  const unitsNote = ((await tid('units-note').first().textContent().catch(() => '')) ?? '').replace(/\s+/g, ' ');
  const notes = ((await tid('source-notes').first().textContent().catch(() => '')) ?? '').replace(/\s+/g, ' ');
  await shot('house-files');
  let confirmed = false;
  if (await tid('units-confirm').count()) {
    await tid('units-confirm').click();
    await savedWhen(PID, up.buildId, 'units confirmed', s => s.sources.every(x => x.unitsConfirmed));
    confirmed = true;
  }
  R.prepare = { seconds: (Date.now() - tPrep) / 1000, steps: prep.run.steps?.map(s => `${s.name} ${s.seconds}`), unitsNote, notes, confirmed };
  note('H3 Files', true, `verdict minor; read in ${R.prepare.seconds.toFixed(1)} s; units: "${unitsNote.slice(0, 200)}"; confirmed with the button: ${confirmed}; notes "${notes.slice(0, 200)}"`);

  R.layers = await setLayers(PID, up.buildId, fx.layers, 'house');
  note('H4 Layers', R.layers.wrong.length === 0, `${R.layers.rows} rows; ${R.layers.changes.length} roles changed with their selects: ${R.layers.changes.map(([l, r]) => `${l} -> ${r}`).join(', ')}${R.layers.wrong.length ? '; STILL DIFFERENT ' + R.layers.wrong.join(', ') : ''}`);

  const pre = (await getBuild(PID, up.buildId)).settings;
  R.proposedFloors = pre.floors.map(f => ({ key: f.key, area: f.area, level: f.level, wallHeight: f.wallHeight }));
  R.floors = await setFloors(PID, up.buildId, fx.floors.map(f => ({ key: f.key, name: f.name, keyName: true, box: f.area.bbox, levelTag: f.level,
    wallHeight: f.wallHeight, doorHead: f.doorHead, windowSill: f.windowSill, windowHead: f.windowHead })));
  R.projectTyped = await setProjectDetails(PID, up.buildId, fx.project);
  const fl = await savedWhen(PID, up.buildId, 'floors', s => s.floors.length === 2 && s.floors.every((f, i) => f.key === fx.floors[i].key &&
    f.level === fx.floors[i].level && f.wallHeight === fx.floors[i].wallHeight && f.windowHead === fx.floors[i].windowHead && f.area.kind === 'box'));
  const floorIssues = await tid('floor-issues').count();
  await shot('house-floors');
  const boxes = fl.settings.floors.map((f, i) => `${f.key} [${f.area.bbox.map(v => v.toFixed(2)).join(', ')}] (fixture [${fx.floors[i].area.bbox.map(v => v.toFixed(2)).join(', ')}], at ${R.floors[i].box.metresPerPixel.toFixed(3)} m a pixel)`);
  note('H5 Floors: the two areas drawn on the sheet', floorIssues === 0 && fl.settings.floors.every((f, i) => f.area.bbox.every((v, k) => Math.abs(v - fx.floors[i].area.bbox[k]) < 0.5)),
    `${boxes.join('; ')}; levels picked from the level tags ${R.floors.map(f => f.level?.picked?.replace(/\s+/g, ' ').trim()).join(' | ')}; wall heights ${fl.settings.floors.map(f => f.wallHeight).join(' / ')}; door / window heads typed; Project details typed: ${R.projectTyped.join(', ')}; no floor issues: ${floorIssues === 0}`);

  const b1 = await build(PID, up.buildId, 'house', null);
  R.build1 = { seconds: b1.seconds, stamp: b1.d.result.stamp, counts: b1.d.result.counts, clear: b1.clear, checklist: b1.checklist };
  note('H6 Build', b1.d.run.status === 'done', `checklist clear: ${b1.clear}${b1.clear ? '' : ` ("${b1.checklist.slice(0, 200)}")`}; done in ${b1.seconds.toFixed(1)} s; stamp ${b1.d.result.stamp}; ${JSON.stringify(b1.d.result.counts)}`);

  const ck = await check(PID, up.buildId, 'house', fx.furniture.words, b1.d);
  R.check = { floors: ck.floors, flags: ck.flagsPerFloor, families: ck.families, given: ck.given, missing: ck.missing,
    rebuild: ck.rebuilt && { seconds: ck.rebuilt.seconds, stamp: ck.rebuilt.d.result.stamp, diffSame: ck.rebuilt.diffSame } };
  note('H7 Check', !!ck.rebuilt, `flags ${JSON.stringify(ck.flagsPerFloor)}; grey families given the fixture's kinds: ${ck.given.map(g => g.join(' -> ')).join(', ')}; not listed as grey: ${ck.missing.join(', ') || 'none'}; rebuilt in ${ck.rebuilt?.seconds.toFixed(1)} s, stamp ${ck.rebuilt?.d.result.stamp}`);
  const sNow = (await getBuild(PID, up.buildId)).settings;
  R.settingsAgainstFixture = settingsDiff(sNow, fx, ['floors.area']);
  note('H7b settings made on the screens against the house fixture', true, R.settingsAgainstFixture.join(' | ') || 'identical apart from the drawn areas');

  R.save = await save(PID, 'house');
  note('H8 Save', true, `${R.save.url}; ${R.save.summary}`);
  R.viewer = await viewerAndWalk('house');
  note('H9 viewer', R.viewer.canvases === 1 && R.viewer.viewerErr === 0, `${R.viewer.canvases} canvas`);
  note('H10 Walk', R.viewer.enteredWalk && R.viewer.movedForward && R.viewer.turned, `Walk on ${R.viewer.enteredWalk}; moved ${R.viewer.movedForward}; turned ${R.viewer.turned}; HUD "${R.viewer.hud.slice(0, 120)}"`);
  const got = await downloads('house', ['maxScript', 'furnitureCsv']);
  R.downloads = got;
  const ms = readFileSync(got.maxScript.file);
  const line2 = ms.toString('latin1').split('\r\n')[1];
  const modelRes = await api.get(`/api/projects/${PID}/versions/1/model`);
  const modelFile = path.join(OUT, 'house-model.json');
  writeFileSync(modelFile, await modelRes.body());
  const model = JSON.parse(readFileSync(modelFile, 'utf8'));
  const ver = await getJson(`/api/projects/${PID}/versions/1`);
  R.model = { sha1: sha1(readFileSync(modelFile)), stamp: ver.stamp, parts: model.parts.length, openings: model.openings.length,
    furniture: (model.furniture ?? []).length, rooms: (model.rooms ?? []).length, floors: model.floors.map(f => [f.key, f.level, f.sheetShift ?? null]) };
  note('H11 downloads', line2 === `(model data ${ver.stamp})` && ms.length > 0,`${got.maxScript.name} line 2 "${line2}"; ${got.furnitureCsv.name} ${got.furnitureCsv.bytes} B; model ${JSON.stringify(R.model)}`);
}

try {
  if (WHICH === 'all' || WHICH === 'bank') await bankPath();
  if (WHICH === 'all' || WHICH === 'house') await housePath();
  note('no dialog, no page error', dialogs.length === 0 && errors.length === 0, JSON.stringify({ dialogs, errors, consoleErrors: consoleErrors.slice(0, 8) }).slice(0, 900));
} catch (e) {
  note('error', false, String(e?.stack ?? e).slice(0, 2000));
  await shot('error').catch(() => {});
} finally {
  writeFileSync(path.join(OUT, 'path.json'), JSON.stringify({ log, facts, dialogs, errors, consoleErrors }, null, 1));
  await browser.close();
  release();
}
process.exit(log.every(l => l.ok) ? 0 : 1);
