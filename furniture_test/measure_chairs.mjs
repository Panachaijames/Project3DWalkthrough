// Measures chair_test.html in headless Edge (the real graphics chip, ANGLE on Direct3D 11; never a visible window) at
// 1920 x 1080 and writes measure_results_<TAG>.json here, screenshots to OUT, and (unless NOCOMPARE=1)
// chair_full_vs_slimmed.png from chair_compare.html.
//   node measure_chairs.mjs
// For each view (the orbit start view, both levels; a Walk view in the bank's busiest seating area, level 1) and each way of
// drawing (A boxes, B full chair per seat, C full chair instanced, D slimmed chair instanced, E slimmed chair per seat): the
// page's own Measure (120 frames back to back, each finished on the chip) REPEATS times, the median kept; the live frames a
// second; a screenshot.
// The machine's CPU load is sampled every second (os.cpus) all along: other work on the machine shows in the numbers.
// Env: PORT (9760 - 9769, default 9760), OUT (screenshots, default %TEMP%\chair-test\out), PROFILE, REPEATS (3), VIEWS
// (orbit,walk), MODES (A,B,C,D,E), GPU=0 (SwiftShader instead), ADAPTER=nvidia (the laptop's NVIDIA chip instead of the one
// Edge picks, the Intel one here: its LUID is read from edge://gpu first), EXTRA (more Edge switches, comma separated),
// TAG (the results' name, measure_results_<TAG>.json; by default the chip's maker: intel, nvidia, amd or swiftshader).
import { mkdirSync, writeFileSync } from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { launch, sleep } from './browser.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const TMP = path.join(os.tmpdir(), 'chair-test');
const OUT = process.env.OUT || path.join(TMP, 'out');
const PROFILE = process.env.PROFILE || path.join(TMP, 'profile');
const PORT = Number(process.env.PORT || 9760);
const REPEATS = Number(process.env.REPEATS || 3);
const VIEWS = (process.env.VIEWS || 'orbit,walk').split(',');
const MODES = (process.env.MODES || 'A,B,C,D,E').split(',');
const GPU = process.env.GPU !== '0';
const EXTRA = process.env.EXTRA ? process.env.EXTRA.split(',') : [];
const ADAPTER = (process.env.ADAPTER || '').toLowerCase();
const TAG = process.env.TAG || '';                                      // empty: named after the chip, once it is known
const makerOf = name => (/swiftshader/i.test(name) ? 'swiftshader' : /nvidia/i.test(name) ? 'nvidia' : /intel/i.test(name) ? 'intel' : /amd|radeon/i.test(name) ? 'amd' : 'gpu');
mkdirSync(OUT, { recursive: true });
const page = pathToFileURL(path.join(HERE, 'chair_test.html')).href;

// The Walk view: level 1's lounge (the most seats within 3 m of one seat: 18 around L1-seat-020), seen from its south-west
// side, by the plants, looking north-east over the lounge towards the desks. Plan (x, y) -> three.js (x, z = -y).
const WALK = { floor: 'L1', x: 0.0, y: -5.2, toward: [1.9, -1.4], pitch: -8 };
const yaw = Math.atan2(-(WALK.toward[0] - WALK.x), (WALK.toward[1] - WALK.y)) * 180 / Math.PI;
const URLS = {
  orbit: page + '?build=0',
  walk: page + `?build=0&mode=walk&floor=${WALK.floor}&x=${WALK.x}&z=${-WALK.y}&yaw=${yaw.toFixed(1)}&pitch=${WALK.pitch}`,
};

// ---------------------------------------------------------------- CPU load, all cores, every second
const busy = () => os.cpus().reduce((a, c) => { const t = c.times; a.idle += t.idle; a.all += t.user + t.nice + t.sys + t.idle + t.irq; return a; }, { idle: 0, all: 0 });
const cpu = [];
let prev = busy();
const timer = setInterval(() => { const now = busy(); cpu.push({ t: Date.now(), load: 100 * (1 - (now.idle - prev.idle) / Math.max(1, now.all - prev.all)) }); prev = now; }, 1000);
const loadBetween = (t0, t1) => { const s = cpu.filter(c => c.t >= t0 && c.t <= t1 + 999).map(c => c.load); return s.length ? Math.round(s.reduce((a, b) => a + b, 0) / s.length) : null; };
await sleep(5000);                                                       // 5 s before Edge starts: what the machine is doing anyway
const before = loadBetween(0, Date.now());

const median = a => { const s = [...a].sort((x, y) => x - y); return s.length % 2 ? s[(s.length - 1) / 2] : (s[s.length / 2 - 1] + s[s.length / 2]) / 2; };
const results = [];
let gpuName = null, winSize = null, walkAt = null, boxesBack = null;
const errors = [];
// Another graphics chip than the one Edge picks: Edge is told its adapter LUID (edge://gpu lists GPU0, GPU1 with theirs).
if (ADAPTER) {
  const vendor = { nvidia: '0x10de', intel: '0x8086', amd: '0x1002' }[ADAPTER];
  if (!vendor) throw new Error('ADAPTER: nvidia, intel or amd');
  const p = await launch({ port: PORT, profile: PROFILE, gpu: GPU, width: 1000, height: 700, step: 'furniture_test gpu list' });
  let text = '';
  try {
    await p.tab.send('Page.navigate', { url: 'edge://gpu' });
    for (let i = 0; i < 30 && !/GPU0/.test(text); i++) { await sleep(300); text = await p.evaluate(`(() => { const v = document.querySelector('info-view'); const r = v && v.shadowRoot ? v.shadowRoot : document.body; return r.innerText || r.textContent || ''; })()`); }
  } finally { await p.close(); }
  const m = text.match(new RegExp(String.raw`GPU\d\s*:?\s*VENDOR\s*=\s*${vendor}[^\n]*?LUID=\{(\d+),(\d+)\}`, 'i'));
  if (!m) throw new Error(`no ${ADAPTER} adapter in edge://gpu`);
  EXTRA.push(`--use-adapter-luid=${m[1]},${m[2]}`);
  console.log(`${ADAPTER}: adapter LUID ${m[1]},${m[2]}`);
}
const b = await launch({ port: PORT, profile: PROFILE, gpu: GPU, extra: EXTRA, width: 1920, height: 1080 });
try {
  for (const view of VIEWS) {
    await b.goto(URLS[view], '!!(window.__chairTest && window.__chairTest.ready)');
    await sleep(2500);
    gpuName = await b.evaluate('__chairTest.gpu');
    winSize = await b.evaluate('[innerWidth, innerHeight, devicePixelRatio]');
    if (view === 'walk') walkAt = await b.evaluate(`(() => { const s = __viewer.state; return { mode: s.mode, floor: s.floor.key, x: +s.pos.x.toFixed(2), planY: +(-s.pos.z).toFixed(2), eye: +(s.pos.y - s.floor.level).toFixed(2), yawDeg: +(s.yaw * 180 / Math.PI).toFixed(1), pitchDeg: +(s.pitch * 180 / Math.PI).toFixed(1) }; })()`);
    for (const mode of MODES) {
      await b.evaluate(`__chairTest.setMode('${mode}')`);
      await sleep(2500);                                                 // a couple of seconds of the page's own frames
      const live = await b.evaluate('__chairTest.live()');
      const runs = [];
      const t0 = Date.now();
      for (let i = 0; i < REPEATS; i++) { runs.push(await b.evaluate('__chairTest.measure(120)')); await sleep(300); }
      const t1 = Date.now();
      const ms = median(runs.map(r => r.ms));
      const row = { view, mode, triangles: runs[0].triangles, calls: runs[0].calls, ms, fps: Math.round(10000 / ms) / 10,
        msRuns: runs.map(r => r.ms), liveFps: Math.round(live.fps), chairTriangles: live.chairTriangles, width: runs[0].width, height: runs[0].height,
        cpuLoad: loadBetween(t0, t1), seconds: Math.round((t1 - t0) / 100) / 10 };
      results.push(row);
      console.log(JSON.stringify(row));
      await sleep(1600);                                                 // the live counter over a second of normal frames again
      await b.shot(path.join(OUT, `${TAG || makerOf(gpuName)}_${view}_${mode}.png`));
    }
    await b.evaluate(`__chairTest.setMode('A')`);                     // back to boxes: every seat box drawn again
    boxesBack = await b.evaluate(`__host.furniture.pieces().filter(p => p.kind === 'seat').every(p => { const m = __host.furniture.meshOf(p.id); return m.material.visible && m.children.every(c => c.material.visible); })`);
    errors.push(...b.logs.filter(l => /exception|error/i.test(l)).map(l => `${view}: ${l}`));     // the next page clears the log
  }
  if (process.env.NOCOMPARE !== '1') {
    await b.tab.send('Emulation.setDeviceMetricsOverride', { width: 1800, height: 1200, deviceScaleFactor: 1, mobile: false });
    await b.goto(pathToFileURL(path.join(HERE, 'chair_compare.html')).href, '!!(window.__compare && window.__compare.ready)');
    await sleep(2000);
    await b.shot(path.join(HERE, 'chair_full_vs_slimmed.png'));
    errors.push(...b.logs.filter(l => /exception|error/i.test(l)).map(l => `compare: ${l}`));
  }
  if (errors.length) console.log('page errors:\n' + errors.join('\n'));
} finally {
  await b.close();
  clearInterval(timer);
}
const loads = cpu.map(c => c.load);
const summary = {
  at: new Date().toISOString(), tag: TAG || makerOf(gpuName || ''), gpu: gpuName, edgeSwitches: EXTRA, window: winSize, repeats: REPEATS, walkView: walkAt, walkUrl: URLS.walk,
  seatBoxesDrawnAgainInA: boxesBack, pageErrors: errors,
  cpu: { cores: os.cpus().length, model: os.cpus()[0].model, beforeEdge: before, meanDuringRun: Math.round(loads.reduce((a, b) => a + b, 0) / loads.length),
    max: Math.round(Math.max(...loads)), min: Math.round(Math.min(...loads)) },
  results,
};
writeFileSync(path.join(HERE, `measure_results_${summary.tag}.json`), JSON.stringify(summary, null, 1));
console.log(JSON.stringify({ ...summary, results: undefined }, null, 1));
