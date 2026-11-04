// Independent check of furniture_test/bank_furnished/bank_furnished.html (3 Nov 2026), in headless Edge on the chip Edge picks
// (the Intel one), holding the shared one-Edge-at-a-time lock (through the folder's own browser.mjs), port 9787:
//   node recheck.mjs <project folder> <out folder> [phases: checks, facing, measure, measure2; default checks,measure]
//   Env: PORT (9770 - 9789, default 9787), VIEWS (orbit,walkL1,widestL1), CONFIGS (A,B,C5000) for the measure phase.
//   Writes <out folder>/recheck_<phases>.json and, in checks, plan pictures plan_<level>_<part>_B.png; the Edge profile in
//   <out folder>/profile (keep the out folder out of the project).
// 1. checks: placement of every copy against its box (bottom, plan, facing), the boxes (hidden / untouched / still colliders),
//    the panel's counts against renderer.info and against an independent count, Walk / Ghost / Orbit, plan pictures.
// 2. measure: the page's own Measure (120 frames, each finished on the chip), 3 times, A / B / C 5,000, in Orbit and the two
//    level 1 Walk views, exactly as measure_furnished.mjs does it; the CPU load sampled every second.
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { pathToFileURL, fileURLToPath } from 'node:url';

const PROJECT = process.argv[2], OUT = process.argv[3];
const PHASES = (process.argv[4] || 'checks,measure').split(',');
const HERE = path.join(PROJECT, 'furniture_test', 'bank_furnished');
const { launch, acquire, sleep } = await import(pathToFileURL(path.join(HERE, 'browser.mjs')).href);
mkdirSync(OUT, { recursive: true });
const PORT = Number(process.env.PORT || 9787);
const page = pathToFileURL(path.join(HERE, 'bank_furnished.html')).href;
const helpers = readFileSync(path.join(path.dirname(fileURLToPath(import.meta.url)), 'page_helpers.js'), 'utf8');
const pl = JSON.parse(readFileSync(path.join(HERE, 'placements.json'), 'utf8'));
const spots = JSON.parse(readFileSync(path.join(HERE, 'walk_spots.json'), 'utf8')).levels;
const ready = '!!(window.__bankFurnished && window.__bankFurnished.ready)';
const placementsFull = Object.fromEntries(Object.entries(pl.models).map(([n, m]) => [n, Object.fromEntries(m.pieces.map(p => [p.key, { turn: p.insert.turn, mirror: p.mirror }]))]));
const log = (...a) => console.log(new Date().toISOString().slice(11, 19), ...a);
const res = { at: new Date().toISOString(), port: PORT, phases: PHASES };

// ---------------------------------------------------------------- CPU load, all cores, every second
const busy = () => os.cpus().reduce((a, c) => { const t = c.times; a.idle += t.idle; a.all += t.user + t.nice + t.sys + t.idle + t.irq; return a; }, { idle: 0, all: 0 });
const cpu = [];
let prev = busy();
const timer = setInterval(() => { const now = busy(); cpu.push({ t: Date.now(), load: 100 * (1 - (now.idle - prev.idle) / Math.max(1, now.all - prev.all)) }); prev = now; }, 1000);
const between = (t0, t1) => cpu.filter(c => c.t >= t0 && c.t <= t1 + 999).map(c => c.load);
const mean = a => a.length ? Math.round(a.reduce((x, y) => x + y, 0) / a.length) : null;
const median = a => { const s = [...a].sort((x, y) => x - y); return s.length % 2 ? s[(s.length - 1) / 2] : (s[s.length / 2 - 1] + s[s.length / 2]) / 2; };

const tWait = Date.now();
await acquire('furniture_test bank_furnished recheck');
res.lockWaitS = Math.round((Date.now() - tWait) / 1000);
log(`lock taken after ${res.lockWaitS} s`);
const tBefore = Date.now();
await sleep(5000);
res.cpuBeforeEdge = mean(between(tBefore, Date.now()));
const tEdge = Date.now();
const b = await launch({ port: PORT, profile: path.join(OUT, 'profile'), width: 1920, height: 1080, step: 'furniture_test bank_furnished recheck' });
const errors = [];
const collect = tag => errors.push(...b.logs.filter(l => /exception|error/i.test(l)).map(l => `${tag}: ${l}`));
const ev = expr => b.evaluate(expr);
const inject = async () => { await ev(helpers); await ev(`__sk.setPlacements(${JSON.stringify(placementsFull)})`); };
const setMode = (m, bud) => ev(`__bankFurnished.setMode('${m}'${bud !== undefined ? `, ${JSON.stringify(bud)}` : ''})`);
try {
  if (PHASES.includes('checks')) {
    const C = res.checks = {};
    await b.goto(page + '?build=0', ready, 180000);
    await sleep(2500);
    await inject();
    C.gpu = await ev('__bankFurnished.gpu');
    C.canvas = await ev('[innerWidth, innerHeight, devicePixelRatio, __bankFurnished.renderer.getPixelRatio(), __bankFurnished.renderer.domElement.width, __bankFurnished.renderer.domElement.height]');
    C.counts0 = await ev('__bankFurnished.counts');
    C.boxesA = await ev('__sk.boxState()');
    C.countsA = await ev('__sk.counts()');
    log('A', JSON.stringify(C.countsA));
    for (const [m, bud] of [['B'], ['C', 20000], ['C', 10000], ['C', 5000], ['C', 2500], ['D'], ['E'], ['P', 'full'], ['P', 5000]]) {
      const name = m + (bud ?? '');
      C['switch' + name] = await setMode(m, bud);
      await sleep(1200);
      C['boxes' + name] = await ev('__sk.boxState()');
      C['copies' + name] = await ev('__sk.copies()');
      C['counts' + name] = await ev('__sk.counts()');
      log(name, JSON.stringify(C['counts' + name]).slice(0, 400));
    }
    await setMode('A');
    await sleep(800);
    C.boxesA2 = await ev('__sk.boxState()');
    C.countsA2 = await ev('__sk.counts()');
    // plan pictures in B, the furnished pieces' box outlines in red
    await setMode('B');
    await sleep(1000);
    const views = [['L1', 0.87, 2.2, 2.5, 'L1_north'], ['L1', 0.87, -2.75, 2.5, 'L1_south'], ['L2', -0.6, 3.2, 2.55, 'L2_north'], ['L2', -0.6, -1.8, 2.55, 'L2_middle'], ['L2', -0.6, -6.9, 2.55, 'L2_south']];
    for (const [fl, x, y, h, name] of views) {
      const url = await ev(`__sk.topView('${fl}', ${x}, ${y}, ${h}, 16 / 9)`);
      writeFileSync(path.join(OUT, `plan_${name}_B.png`), Buffer.from(url.split(',')[1], 'base64'));
    }
    collect('checks orbit');
    // Walk: a furnished (hidden) box still stops you, exactly as the drawn box does; Ghost flies through; Orbit still turns
    const W = C.walk = {};
    const start = { x: -0.39, z: 2.426 };                 // 1.4 m east of the mollie chair L1-seat-012, walking west towards it and its desk
    await b.goto(page + `?build=0&furniture=B&mode=walk&floor=L1&x=${start.x}&z=${start.z}&yaw=90&pitch=-8`, ready, 180000);
    await sleep(2000);
    await inject();
    const walkFrom = async () => ev(`(() => { const v = __viewer, s = v.state; s.pos.set(${start.x}, s.floor.level + s.eye, ${start.z}); s.yaw = Math.PI / 2;
      const crosses = v.probe.crosses(${start.x}, ${start.z}, ${start.x} - 2, ${start.z}); const got = v.probe.walk(90, 2.0);
      return { mode: v.mode, floor: s.floor.key, walked: +got.toFixed(3), endX: +s.pos.x.toFixed(3), wallBetween: crosses }; })()`);
    W.B = await walkFrom();
    await setMode('A'); await sleep(500);
    W.A = await walkFrom();
    await setMode('B'); await sleep(500);
    await ev(`__host.furniture.setBlocks('seat', false)`);
    W.B_seatsDoNotStop = await walkFrom();
    await ev(`__host.furniture.setBlocks('seat', true)`);
    W.B_again = await walkFrom();
    // keys: 3 = Ghost, W held 0.8 s; 2 = Walk; 1 = Orbit, then a mouse drag
    const key = async (code, k, vk, type) => b.tab.send('Input.dispatchKeyEvent', { type, code, key: k, windowsVirtualKeyCode: vk, nativeVirtualKeyCode: vk });
    const press = async (code, k, vk, ms = 60) => { await key(code, k, vk, 'keyDown'); await sleep(ms); await key(code, k, vk, 'keyUp'); };
    const pos = () => ev(`(() => { const c = __host.camera.position; return { mode: __viewer.mode, x: +c.x.toFixed(3), y: +c.y.toFixed(3), z: +c.z.toFixed(3) }; })()`);
    await ev(`(() => { const s = __viewer.state; s.pos.set(${start.x}, s.floor.level + s.eye, ${start.z}); s.yaw = Math.PI / 2; s.pitch = 0; return 1; })()`);
    await press('Digit3', '3', 51);
    await sleep(300);
    W.ghostBefore = await pos();
    await press('KeyW', 'w', 87, 800);
    await sleep(300);
    W.ghostAfter = await pos();
    await press('Digit2', '2', 50);
    await sleep(300);
    W.walkKeyBefore = await pos();
    await press('KeyW', 'w', 87, 800);
    await sleep(300);
    W.walkKeyAfter = await pos();
    await press('Digit1', '1', 49);
    await sleep(500);
    W.orbitBefore = await pos();
    await b.tab.send('Input.dispatchMouseEvent', { type: 'mouseMoved', x: 700, y: 540 });
    await b.tab.send('Input.dispatchMouseEvent', { type: 'mousePressed', x: 700, y: 540, button: 'left', buttons: 1, clickCount: 1 });
    for (let i = 1; i <= 10; i++) { await b.tab.send('Input.dispatchMouseEvent', { type: 'mouseMoved', x: 700 + i * 25, y: 540, button: 'left', buttons: 1 }); await sleep(30); }
    await b.tab.send('Input.dispatchMouseEvent', { type: 'mouseReleased', x: 950, y: 540, button: 'left', buttons: 0, clickCount: 1 });
    await sleep(800);
    W.orbitAfter = await pos();
    W.errorsOnPage = await ev(`(() => { const e = [...document.querySelectorAll('div')].find(d => /^Viewer error/.test(d.textContent || '')); return e && e.style.display !== 'none' ? e.textContent : null; })()`);
    collect('walk / ghost / orbit');
    log('walk', JSON.stringify(W));
  }
  if (PHASES.includes('facing')) {
    await b.goto(page + '?build=0', ready, 180000);
    await sleep(2000);
    await inject();
    const F = res.facing = {};
    for (const [m, bud] of [['B'], ['C', 10000], ['C', 5000]]) {
      await setMode(m, bud);
      await sleep(800);
      F[m + (bud ?? '')] = await ev('__sk.chairFacing()');
    }
    log('facing', JSON.stringify(F).slice(0, 300));
    collect('facing');
  }
  if (PHASES.includes('measure2')) {
    // the same Measures in the opposite order, and the chair test's page in A (boxes) beside this page's A, in one Edge
    const M = res.measure2 = { rows: [] };
    const chairPage = pathToFileURL(path.join(PROJECT, 'furniture_test', 'chair_test.html')).href;
    const t0run = Date.now();
    const row = async (view, config, expr, extra = {}) => {
      const runs = [];
      const t0 = Date.now();
      for (let i = 0; i < 3; i++) { runs.push(await ev(expr)); await sleep(300); }
      const t1 = Date.now();
      const r = { view, config, ms: median(runs.map(x => x.ms)), msRuns: runs.map(x => x.ms), triangles: runs[0].triangles, calls: runs[0].calls, gpu: runs[0].gpu,
        width: runs[0].width, height: runs[0].height, cpuLoad: mean(between(t0, t1)), cpuMax: Math.round(Math.max(...between(t0, t1))), ...extra };
      M.rows.push(r);
      log(JSON.stringify(r));
    };
    for (const round of [1, 2]) {
      await b.goto(chairPage + '?build=0', '!!(window.__chairTest && window.__chairTest.ready)', 180000);
      await sleep(2500);
      await ev(`__chairTest.setMode('A')`); await sleep(2500);
      await row('orbit', 'chair_test.html A', '__chairTest.measure(120)', { round });
      await b.goto(page + '?build=0', ready, 180000);
      await sleep(2500);
      for (const [m, bud] of [['C', 5000], ['B'], ['A']]) {
        await setMode(m, bud); await sleep(2500);
        await row('orbit', m + (bud ?? ''), '__bankFurnished.measure(120)', { round });
      }
    }
    await b.goto(page + `?build=0&${spots.L1.widest.url}`, ready, 180000);
    await sleep(2500);
    for (const [m, bud] of [['C', 5000], ['B'], ['A'], ['C', 5000]]) {
      await setMode(m, bud); await sleep(2500);
      await row('widestL1', m + (bud ?? ''), '__bankFurnished.measure(120)');
    }
    collect('measure2');
    const all = between(t0run, Date.now());
    M.cpu = { meanDuringMeasures: mean(all), min: Math.round(Math.min(...all)), max: Math.round(Math.max(...all)) };
  }
  if (PHASES.includes('measure')) {
    const M = res.measure = { rows: [] };
    const ALLVIEWS = { orbit: page + '?build=0', walkL1: page + `?build=0&${spots.L1.busiest.url}`, widestL1: page + `?build=0&${spots.L1.widest.url}` };
    const VIEWS = Object.fromEntries((process.env.VIEWS || 'orbit,walkL1,widestL1').split(',').map(v => [v, ALLVIEWS[v]]));
    const CONFIGS = (process.env.CONFIGS || 'A,B,C5000').split(',').map(c => ({ name: c, mode: c[0], budget: c.length > 1 ? (c.slice(1) === 'full' ? 'full' : Number(c.slice(1))) : undefined }));
    const t0run = Date.now();
    for (const [view, url] of Object.entries(VIEWS)) {
      await b.goto(url, ready, 180000);
      await sleep(2500);
      for (const c of CONFIGS) {
        await setMode(c.mode, c.budget);
        await sleep(2500);
        const live = await ev('__bankFurnished.live()');
        const runs = [];
        const t0 = Date.now();
        for (let i = 0; i < 3; i++) { runs.push(await ev('__bankFurnished.measure(120)')); await sleep(300); }
        const t1 = Date.now();
        const row = { view, config: c.name, ms: median(runs.map(r => r.ms)), msRuns: runs.map(r => r.ms), triangles: runs[0].triangles, calls: runs[0].calls,
          modelTriangles: runs[0].modelTriangles, liveFps: Math.round(live.fps), width: runs[0].width, height: runs[0].height, gpu: runs[0].gpu,
          cpuLoad: mean(between(t0, t1)), cpuMax: Math.round(Math.max(...between(t0, t1))), seconds: (t1 - t0) / 1000 };
        M.rows.push(row);
        log(JSON.stringify(row));
      }
      collect('measure ' + view);
    }
    const all = between(t0run, Date.now());
    M.cpu = { meanDuringMeasures: mean(all), min: Math.round(Math.min(...all)), max: Math.round(Math.max(...all)) };
  }
} finally {
  await b.close();
  clearInterval(timer);
}
const all = between(tEdge, Date.now());
res.cpu = { cores: os.cpus().length, model: os.cpus()[0].model, beforeEdge: res.cpuBeforeEdge, meanWhileEdgeRan: mean(all), min: Math.round(Math.min(...all)), max: Math.round(Math.max(...all)) };
res.pageErrors = errors;
writeFileSync(path.join(OUT, `recheck_${PHASES.join('_')}.json`), JSON.stringify(res, null, 1));
log('done', JSON.stringify({ lockWaitS: res.lockWaitS, cpu: res.cpu, errors: errors.length }));
