// Times bank_furnished.html in headless Edge (the real graphics chip, ANGLE on Direct3D 11; never a visible window) at 1920 x 1080
// and writes measure_results_<TAG>.json here (screenshots to OUT):
//   node measure_furnished.mjs                 the chip Edge picks (the Intel one on this laptop)
//   ADAPTER=nvidia node measure_furnished.mjs  the NVIDIA one (its adapter LUID is read from edge://gpu first)
// 1. Loading: the page opened afresh in each way of drawing (?furniture=...), LOAD_REPEATS times: when the bank page drew its first
//    frame, and when the first frame with the models was finished on the chip (models decoded from the page's base64 text, parsed
//    by GLTFLoader, put on the chip); and the bank page as it is (bank_3d_preview.html), its first draw call, for comparison.
// 2. Frames: for each view (Orbit, both levels; Walk at each level's busiest furnished spot, walk_spots.json; and, unless
//    WIDEST=0, the widest view of each level) and each way of drawing, the page's own Measure (120 frames back to back, each
//    finished on the chip) REPEATS times, the median kept; the live frames a second; the models' memory on the chip; a screenshot.
// 3. Walking through (unless WALKTHROUGH=0): a straight walk through each level's busiest spot (walk_spots.json path), 240 frames
//    each finished on the chip, in B, C 5,000 and D: frame times, and how often D switched a model between full and slimmed.
// The machine's CPU load (all cores, os.cpus) is sampled every second all along, from 5 s before Edge starts.
// Env: PORT (9770 - 9789, default 9786), BF_TMP (temp folder, default %TEMP%\bank-furnished), OUT, PROFILE, REPEATS (3),
//      LOAD_REPEATS (3), VIEWS (orbit,walkL1,walkL2[,widestL1,widestL2]), CONFIGS (A,B,C20000,C10000,C5000,C2500,D,E,Pfull,P20000,
//      P10000,P5000,P2500), ADAPTER (nvidia | intel | amd), TAG, LOADS=0 (skip 1), WALKTHROUGH=0 (skip 3).
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { acquire, launch, sleep } from './browser.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const PROJECT = path.resolve(HERE, '..', '..');
const TMP = process.env.BF_TMP || path.join(os.tmpdir(), 'bank-furnished');
const OUT = process.env.OUT || path.join(TMP, 'out');
const PROFILE = process.env.PROFILE || path.join(TMP, 'profile');
const PORT = Number(process.env.PORT || 9786);
const REPEATS = Number(process.env.REPEATS || 3), LOAD_REPEATS = Number(process.env.LOAD_REPEATS || 3);
const ADAPTER = (process.env.ADAPTER || '').toLowerCase();
const TAG = process.env.TAG || '';
const EXTRA = process.env.EXTRA ? process.env.EXTRA.split(',') : [];
const makerOf = name => (/swiftshader/i.test(name) ? 'swiftshader' : /nvidia/i.test(name) ? 'nvidia' : /intel/i.test(name) ? 'intel' : /amd|radeon/i.test(name) ? 'amd' : 'gpu');
mkdirSync(OUT, { recursive: true });
const page = pathToFileURL(path.join(HERE, 'bank_furnished.html')).href;
const bankPage = pathToFileURL(path.join(PROJECT, 'bank_test', 'bank_3d_preview.html')).href;
const spots = JSON.parse(readFileSync(path.join(HERE, 'walk_spots.json'), 'utf8')).levels;
const VIEWS = (process.env.VIEWS || ['orbit', 'walkL1', 'walkL2', ...(process.env.WIDEST === '0' ? [] : ['widestL1', 'widestL2'])].join(',')).split(',');
const URLS = { orbit: { url: page + '?build=0', spot: null } };
for (const [lv, s] of Object.entries(spots)) {
  URLS['walk' + lv] = { url: page + `?build=0&${s.busiest.url}`, spot: s.busiest };
  URLS['widest' + lv] = { url: page + `?build=0&${s.widest.url}`, spot: s.widest };
}
const CONFIGS = (process.env.CONFIGS || 'A,B,C20000,C10000,C5000,C2500,D,E,Pfull,P20000,P10000,P5000,P2500').split(',')
  .map(c => ({ name: c, mode: c[0], budget: c.length > 1 ? (c.slice(1) === 'full' ? 'full' : Number(c.slice(1))) : undefined }));
const LOAD_CONFIGS = (process.env.LOAD_CONFIGS || 'A,B,C20000,C10000,C5000,C2500,D,E').split(',');
const setModeExpr = c => `__bankFurnished.setMode('${c.mode}'${c.budget !== undefined ? `, ${JSON.stringify(c.budget)}` : ''})`;
const ready = '!!(window.__bankFurnished && window.__bankFurnished.ready)';

// ---------------------------------------------------------------- CPU load, all cores, every second
const busy = () => os.cpus().reduce((a, c) => { const t = c.times; a.idle += t.idle; a.all += t.user + t.nice + t.sys + t.idle + t.irq; return a; }, { idle: 0, all: 0 });
const cpu = [];
let prev = busy();
const timer = setInterval(() => { const now = busy(); cpu.push({ t: Date.now(), load: 100 * (1 - (now.idle - prev.idle) / Math.max(1, now.all - prev.all)) }); prev = now; }, 1000);
const loadBetween = (t0, t1) => { const s = cpu.filter(c => c.t >= t0 && c.t <= t1 + 999).map(c => c.load); return s.length ? Math.round(s.reduce((a, b) => a + b, 0) / s.length) : null; };
const maxBetween = (t0, t1) => { const s = cpu.filter(c => c.t >= t0 && c.t <= t1 + 999).map(c => c.load); return s.length ? Math.round(Math.max(...s)) : null; };
const median = a => { const s = [...a].sort((x, y) => x - y); return s.length % 2 ? s[(s.length - 1) / 2] : (s[s.length / 2 - 1] + s[s.length / 2]) / 2; };
// The shared Edge lock is taken first and held to the end (launch() below finds it already held), so that 'before Edge' is the
// 5 s just before Edge starts and the run's averages start with Edge: not the time spent waiting for other sessions' browser
// runs, as in the first runs of 3 Nov (their per-row loads, taken during the Measures themselves, were not affected).
const STEP = 'furniture_test bank_furnished measure';
const tLock = Date.now();
await acquire(STEP);
const lockWaitS = Math.round((Date.now() - tLock) / 1000);

// ---------------------------------------------------------------- another graphics chip than the one Edge picks: its adapter LUID
if (ADAPTER) {
  const vendor = { nvidia: '0x10de', intel: '0x8086', amd: '0x1002' }[ADAPTER];
  if (!vendor) throw new Error('ADAPTER: nvidia, intel or amd');
  const p = await launch({ port: PORT, profile: PROFILE, width: 1000, height: 700, step: 'furniture_test bank_furnished gpu list' });
  let text = '';
  try {
    await p.tab.send('Page.navigate', { url: 'edge://gpu' });
    for (let i = 0; i < 30 && !/GPU0/.test(text); i++) { await sleep(300); text = await p.evaluate(`(() => { const v = document.querySelector('info-view'); const r = v && v.shadowRoot ? v.shadowRoot : document.body; return r.innerText || r.textContent || ''; })()`); }
  } finally { await p.close(); await acquire(STEP); }                 // close() lets the lock go: take it straight back
  const m = text.match(new RegExp(String.raw`GPU\d\s*:?\s*VENDOR\s*=\s*${vendor}[^\n]*?LUID=\{(\d+),(\d+)\}`, 'i'));
  if (!m) throw new Error(`no ${ADAPTER} adapter in edge://gpu`);
  EXTRA.push(`--use-adapter-luid=${m[1]},${m[2]}`);
  console.log(`${ADAPTER}: adapter LUID ${m[1]},${m[2]}`);
}

const tBefore = Date.now();
await sleep(5000);
const before = loadBetween(tBefore, Date.now());
const results = [], loads = [], walks = [], errors = [];
let gpuName = null, winSize = null;
const tStart = Date.now();
const b = await launch({ port: PORT, profile: PROFILE, extra: EXTRA, width: 1920, height: 1080 });
const collect = tag => errors.push(...b.logs.filter(l => /exception|error/i.test(l)).map(l => `${tag}: ${l}`));
try {
  // ---------------------------------------------------------------- 1. loading
  if (process.env.LOADS !== '0') {
    // the bank page as it is: its first draw call (a probe on WebGL's draw calls, for these loads only)
    const probe = await b.tab.send('Page.addScriptToEvaluateOnNewDocument', { source: `(() => { window.__firstDraw = null; for (const C of [window.WebGL2RenderingContext, window.WebGLRenderingContext]) { if (!C) continue; const P = C.prototype; for (const f of ['drawElements', 'drawArrays']) { const o = P[f]; P[f] = function (...a) { if (window.__firstDraw === null) window.__firstDraw = performance.now(); return o.apply(this, a); }; } } })();` });
    const bankRuns = [];
    for (let i = 0; i < LOAD_REPEATS; i++) {
      await b.goto(bankPage + '?build=0', '!!(window.__host && window.__firstDraw)', 120000);
      bankRuns.push(await b.evaluate(`(() => { const n = performance.getEntriesByType('navigation')[0]; return { firstDraw: +window.__firstDraw.toFixed(1), domContentLoaded: +n.domContentLoadedEventEnd.toFixed(1) }; })()`));
      await sleep(800);
    }
    await b.tab.send('Page.removeScriptToEvaluateOnNewDocument', { identifier: probe.identifier });
    loads.push({ config: 'bank page as it is', runs: bankRuns, firstFrame: median(bankRuns.map(r => r.firstDraw)), domContentLoaded: median(bankRuns.map(r => r.domContentLoaded)) });
    console.log(JSON.stringify(loads[loads.length - 1]));
    for (const name of LOAD_CONFIGS) {
      const c = { mode: name[0], budget: name.length > 1 ? Number(name.slice(1)) : undefined };
      const runs = [];
      const t0 = Date.now();
      for (let i = 0; i < LOAD_REPEATS; i++) {
        await b.goto(page + `?build=0&furniture=${c.mode}${c.budget ? `&budget=${c.budget}` : ''}`, ready, 180000);
        const s = await b.evaluate('__bankFurnished.startup');
        runs.push({ domContentLoaded: s.domContentLoaded, bankFirstFrame: s.bankFirstFrame, firstFrameWithModels: s.firstFrameWithModels, decodeMs: s.switch.decodeMs,
          base64Ms: s.switch.base64Ms, parseMs: s.switch.parseMs, buildMs: s.switch.buildMs, uploadMs: s.switch.uploadMs, firstFrameMs: s.switch.firstFrameMs, assets: s.decoded.length });
        gpuName = gpuName || await b.evaluate('__bankFurnished.gpu');
        collect(`load ${name}`);
        await sleep(800);
      }
      const med = k => median(runs.map(r => r[k]));
      const row = { config: name, runs, domContentLoaded: med('domContentLoaded'), bankFirstFrame: med('bankFirstFrame'), firstFrameWithModels: med('firstFrameWithModels'),
        decodeMs: med('decodeMs'), base64Ms: med('base64Ms'), parseMs: med('parseMs'), buildMs: med('buildMs'), uploadMs: med('uploadMs'), firstFrameMs: med('firstFrameMs'),
        cpuLoad: loadBetween(t0, Date.now()), cpuMax: maxBetween(t0, Date.now()) };
      loads.push(row);
      console.log(JSON.stringify({ ...row, runs: undefined }));
    }
  }
  // ---------------------------------------------------------------- 2. frames
  for (const view of VIEWS) {
    const V = URLS[view];
    if (!V) throw new Error('unknown view ' + view);
    await b.goto(V.url, ready, 180000);
    await sleep(2500);
    gpuName = await b.evaluate('__bankFurnished.gpu');
    winSize = await b.evaluate('[innerWidth, innerHeight, devicePixelRatio]');
    const at = V.spot ? await b.evaluate(`(() => { const s = __viewer.state; return { mode: s.mode, floor: s.floor.key, x: +s.pos.x.toFixed(2), planY: +(-s.pos.z).toFixed(2), eye: +(s.pos.y - s.floor.level).toFixed(2), yawDeg: +(s.yaw * 180 / Math.PI).toFixed(1), pitchDeg: +(s.pitch * 180 / Math.PI).toFixed(1) }; })()`) : null;
    if (at) console.log(view, 'asked', V.spot.x, V.spot.y, V.spot.yawDeg, '-> at', JSON.stringify(at));
    for (const c of CONFIGS) {
      const sw = await b.evaluate(setModeExpr(c));
      await sleep(2500);                                              // a couple of seconds of the page's own frames
      const live = await b.evaluate('__bankFurnished.live()');
      const runs = [];
      const t0 = Date.now();
      for (let i = 0; i < REPEATS; i++) { runs.push(await b.evaluate('__bankFurnished.measure(120)')); await sleep(300); }
      const t1 = Date.now();
      const ms = median(runs.map(r => r.ms));
      const mem = await b.evaluate('__bankFurnished.memory()');
      const row = { view, config: c.name, mode: c.mode, budget: c.budget ?? null, triangles: runs[0].triangles, calls: runs[0].calls, modelTriangles: runs[0].modelTriangles,
        nearFull: runs[0].nearFull, ms, fps: Math.round(10000 / ms) / 10, msRuns: runs.map(r => r.ms), liveFps: Math.round(live.fps),
        width: runs[0].width, height: runs[0].height, memory: mem, switchMs: sw.totalMs, cpuLoad: loadBetween(t0, t1), cpuMax: maxBetween(t0, t1), seconds: Math.round((t1 - t0) / 100) / 10 };
      results.push(row);
      console.log(JSON.stringify({ ...row, memory: { models: mem.models, info: mem.info } }));
      await sleep(1200);
      await b.shot(path.join(OUT, `${TAG || makerOf(gpuName)}_${view}_${c.name}.png`));
    }
    await b.evaluate(`__bankFurnished.setMode('A')`);
    if (view === 'orbit') results.push({ view, check: 'boxes drawn again in A', value: await b.evaluate('__bankFurnished.boxesDrawn() === __bankFurnished.counts.boxes') });
    collect(view);
  }
  // ---------------------------------------------------------------- 3. walking through
  if (process.env.WALKTHROUGH !== '0') {
    for (const [lv, s] of Object.entries(spots)) {
      const p = s.busiest.path;
      if (!p) continue;
      await b.goto(page + `?build=0&${s.busiest.url}`, ready, 180000);
      await sleep(2000);
      for (const c of [{ name: 'B', mode: 'B' }, { name: 'C5000', mode: 'C', budget: 5000 }, { name: 'D', mode: 'D' }]) {
        await b.evaluate(setModeExpr(c));
        await sleep(1500);
        const t0 = Date.now();
        const runs = [];
        for (let i = 0; i < REPEATS; i++) {      // there and back: the far end of one run is the start of the next
          const [from, to] = i % 2 ? [p.to, p.from] : [p.from, p.to];
          runs.push(await b.evaluate(`__bankFurnished.walkThrough(${JSON.stringify({ floor: lv, from, to, frames: 240 })})`));
          await sleep(300);
        }
        const row = { level: lv, config: c.name, path: p, runs, medianMs: median(runs.map(r => r.medianMs)), p95Ms: median(runs.map(r => r.p95Ms)), maxMs: Math.max(...runs.map(r => r.maxMs)),
          over33: runs.reduce((a, r) => a + r.over33, 0), over16: runs.reduce((a, r) => a + r.over16, 0), frames: runs.reduce((a, r) => a + r.frames, 0), levelSwitches: runs.reduce((a, r) => a + r.levelSwitches, 0),
          cpuLoad: loadBetween(t0, Date.now()) };
        walks.push(row);
        console.log(JSON.stringify({ ...row, runs: undefined }));
      }
      collect(`walk-through ${lv}`);
    }
  }
  if (errors.length) console.log('page errors:\n' + errors.join('\n'));
} finally {
  await b.close();
  clearInterval(timer);
}
const all = cpu.filter(c => c.t >= tStart).map(c => c.load);
const summary = {
  at: new Date().toISOString(), tag: TAG || makerOf(gpuName || ''), gpu: gpuName, edgeSwitches: EXTRA, window: winSize, repeats: REPEATS, loadRepeats: LOAD_REPEATS, lockWaitS,
  views: Object.fromEntries(VIEWS.map(v => [v, { url: URLS[v].url.replace(page, 'bank_furnished.html'), spot: URLS[v].spot ? { x: URLS[v].spot.x, y: URLS[v].spot.y, yawDeg: URLS[v].spot.yawDeg, facing: URLS[v].spot.facing, nearestRooms: URLS[v].spot.nearestRooms } : null }])),
  pageErrors: errors,
  cpu: { cores: os.cpus().length, model: os.cpus()[0].model, beforeEdge: before, meanDuringRun: Math.round(all.reduce((a, b) => a + b, 0) / all.length), max: Math.round(Math.max(...all)), min: Math.round(Math.min(...all)) },
  loads, results, walks,
};
writeFileSync(path.join(HERE, `measure_results_${summary.tag}.json`), JSON.stringify(summary, null, 1));
console.log(JSON.stringify({ ...summary, loads: undefined, results: undefined, walks: undefined }, null, 1));
