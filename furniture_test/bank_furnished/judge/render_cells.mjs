// The slimming judge, step 2: every level of every model drawn in headless Edge (judge_page.html), at walking distance and
// close up, each cell saved as a PNG for compose_sheets.py.
//   node render_cells.mjs <project folder> <cells folder> [model keys, comma separated]
// Serves judge/ (the page and slim_levels.mjs's levels/), the model files (banquet/*.glb, Chair.glb) and three.js from
// app/node_modules on http://127.0.0.1:9771 (GET only, nothing else reachable), and drives Edge over the DevTools protocol on
// port 9770 (this job keeps to 9770 - 9789). Edge runs headless with the graphics chip it picks (ANGLE on Direct3D 11), never a
// visible window, inside the machine's one-Edge-at-a-time lock (%TEMP%\wt-edge.lock, taken with ../../browser.mjs's acquire /
// release, the same lock as app/tools/edge-lock.mjs) from launch to close. The CPU load is sampled every second all along
// (not a timing run: the pictures do not depend on it, but it is recorded). Writes <cells>/<key>/<dist>_<level>.png (the
// empty stage 'none', the full model, every level with its normals worked out as the chair test did, and every level again
// as 'a_<level>' with them weighted by corner angle; a <key>_n model from slim_levels.mjs's KEEP_NORMALS variant carries its
// own) and <cells>/cells.json, and judge/render_run.json (chip, CPU load, times).
import { spawn } from 'node:child_process';
import { createReadStream, existsSync, mkdirSync, readFileSync, statSync, writeFileSync } from 'node:fs';
import http from 'node:http';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { acquire, release } from '../../browser.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const [PROJECT, CELLS, ONLY] = process.argv.slice(2);
if (!PROJECT || !CELLS) { console.error('usage: node render_cells.mjs <project folder> <cells folder> [keys]'); process.exit(2); }
const EDGE = process.env.EDGE || 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe';
const CDP_PORT = 9770, HTTP_PORT = 9771;
const PROFILE = path.join(os.tmpdir(), 'wt-slim-judge-profile');
const sleep = ms => new Promise(r => setTimeout(r, ms));
const keys = ONLY ? ONLY.split(',') : JSON.parse(readFileSync(path.join(HERE, 'levels.json'), 'utf8')).models.map(m => m.key);
for (const k of keys) if (!existsSync(path.join(HERE, 'levels', `${k}.json`))) throw new Error(`no levels/${k}.json: run slim_levels.mjs first`);
mkdirSync(CELLS, { recursive: true });

// ---------------------------------------------------------------- CPU load, all cores, every second
const busy = () => os.cpus().reduce((a, c) => { const t = c.times; a.idle += t.idle; a.all += t.user + t.nice + t.sys + t.idle + t.irq; return a; }, { idle: 0, all: 0 });
const cpu = [];
let prev = busy();
const timer = setInterval(() => { const now = busy(); cpu.push({ t: Date.now(), load: 100 * (1 - (now.idle - prev.idle) / Math.max(1, now.all - prev.all)) }); prev = now; }, 1000);
await sleep(3000);
const before = Math.round(cpu.reduce((a, c) => a + c.load, 0) / Math.max(1, cpu.length));

// ---------------------------------------------------------------- the files, read only
const TYPES = { '.html': 'text/html', '.js': 'text/javascript', '.mjs': 'text/javascript', '.json': 'application/json', '.bin': 'application/octet-stream', '.glb': 'model/gltf-binary', '.wasm': 'application/wasm' };
const ROOTS = [
  ['/three/', path.join(PROJECT, 'app', 'node_modules', 'three')],
  ['/project/banquet/', path.join(PROJECT, 'banquet')],
  ['/project/Chair.glb', path.join(PROJECT, 'Chair.glb')],
  ['/', HERE],
];
const server = http.createServer((req, res) => {
  try {
    if (req.method !== 'GET') { res.writeHead(405); res.end(); return; }
    const url = decodeURIComponent(new URL(req.url, 'http://x').pathname);
    for (const [prefix, dir] of ROOTS) {
      if (!url.startsWith(prefix)) continue;
      const file = prefix.endsWith('/') ? path.resolve(dir, '.' + path.sep + url.slice(prefix.length)) : dir;
      if (prefix.endsWith('/') && !file.startsWith(path.resolve(dir) + path.sep)) break;
      if (!existsSync(file) || !statSync(file).isFile()) break;
      res.writeHead(200, { 'Content-Type': TYPES[path.extname(file).toLowerCase()] || 'application/octet-stream', 'Cache-Control': 'no-store' });
      createReadStream(file).pipe(res);
      return;
    }
    res.writeHead(404); res.end();
  } catch { res.writeHead(400); res.end(); }
});
await new Promise((res, rej) => { server.once('error', rej); server.listen(HTTP_PORT, '127.0.0.1', res); });

// ---------------------------------------------------------------- DevTools protocol (as ../../browser.mjs)
function connect(url) {
  return new Promise((resolve, reject) => {
    const ws = new WebSocket(url);
    let id = 0;
    const pending = new Map(), listeners = [];
    ws.onmessage = ev => {
      const msg = JSON.parse(ev.data);
      if (msg.id && pending.has(msg.id)) { const { res, rej, method } = pending.get(msg.id); pending.delete(msg.id); if (msg.error) rej(new Error(method + ': ' + msg.error.message)); else res(msg.result); }
      else if (msg.method) listeners.forEach(fn => fn(msg));
    };
    ws.onopen = () => resolve({ send: (method, params = {}) => new Promise((res, rej) => { const i = ++id; pending.set(i, { res, rej, method }); ws.send(JSON.stringify({ id: i, method, params })); }), on: fn => listeners.push(fn), close: () => ws.close() });
    ws.onerror = e => reject(new Error('websocket error ' + (e.message || '')));
  });
}
const portAnswers = async port => { try { await fetch(`http://127.0.0.1:${port}/json/version`, { signal: AbortSignal.timeout(1200) }); return true; } catch { return false; } };

if (await portAnswers(CDP_PORT)) throw new Error(`port ${CDP_PORT} already answers: another browser is using it`);
await acquire('furniture_test bank_furnished slimming judge', Number(process.env.LOCK_WAIT_MIN || 45) * 60 * 1000);   // LOCK_WAIT_MIN: how long to wait for other runs
const tLock = Date.now();
let proc, browser, tab;
const logs = [];
const run = { gpu: null, cells: 0, models: {} };
try {
  proc = spawn(EDGE, ['--headless=new', '--use-angle=d3d11', '--enable-gpu', '--ignore-gpu-blocklist', `--remote-debugging-port=${CDP_PORT}`,
    `--user-data-dir=${PROFILE}`, '--window-size=1920,1080', '--hide-scrollbars', '--no-first-run', '--no-default-browser-check', 'about:blank'], { stdio: 'ignore' });
  let ver = null;
  for (let i = 0; i < 150 && !ver; i++) { try { ver = await (await fetch(`http://127.0.0.1:${CDP_PORT}/json/version`)).json(); } catch { await sleep(100); } }
  if (!ver) throw new Error('Edge did not start');
  const list = await (await fetch(`http://127.0.0.1:${CDP_PORT}/json/list`)).json();
  browser = await connect(ver.webSocketDebuggerUrl);
  tab = await connect(list.find(t => t.type === 'page').webSocketDebuggerUrl);
  await tab.send('Runtime.enable'); await tab.send('Page.enable');
  tab.on(msg => {
    const p = msg.params;
    if (msg.method === 'Runtime.consoleAPICalled') logs.push(`[console.${p.type}] ` + p.args.map(a => a.value ?? a.description ?? '').join(' '));
    if (msg.method === 'Runtime.exceptionThrown') logs.push('[exception] ' + (p.exceptionDetails.exception?.description || p.exceptionDetails.text));
  });
  await tab.send('Emulation.setDeviceMetricsOverride', { width: 1920, height: 1080, deviceScaleFactor: 1, mobile: false });
  const evaluate = async expr => {
    const r = await tab.send('Runtime.evaluate', { expression: expr, awaitPromise: true, returnByValue: true });
    if (r.exceptionDetails) throw new Error('eval failed: ' + (r.exceptionDetails.exception?.description || r.exceptionDetails.text) + '\n' + logs.join('\n'));
    return r.result.value;
  };
  await tab.send('Page.navigate', { url: `http://127.0.0.1:${HTTP_PORT}/judge_page.html` });
  for (let t0 = Date.now(); ; await sleep(200)) {
    try { if (await evaluate('!!(window.__judge && window.__judge.ready)')) break; } catch { /* loading */ }
    if (Date.now() - t0 > 60000) throw new Error('page did not get ready\n' + logs.join('\n'));
  }
  run.gpu = await evaluate('__judge.gpu');
  run.page = await evaluate('({ three: __judge.three, screen: __judge.screen, lensMm: __judge.lensMm, fovDeg: __judge.fovDeg, eye: __judge.eye, azimuthDeg: __judge.azimuthDeg, walkM: __judge.walkM, closeGapM: __judge.closeGapM, creaseDeg: __judge.creaseDeg })');
  console.log('graphics:', run.gpu);
  const index = {};
  for (const key of keys) {
    const t0 = Date.now();
    const s = await evaluate(`__judge.load(${JSON.stringify(key)})`);
    mkdirSync(path.join(CELLS, key), { recursive: true });
    index[key] = { fullTriangles: s.fullTriangles, levels: s.levels, dists: {} };
    for (const dist of ['walk', 'close']) {
      // every level with its normals worked out as the chair test did, and again weighted by corner angle ('a:<id>'); the
      // KEEP_NORMALS variant's levels (<key>_n) carry their own normals
      const lv = s.levels.map(l => l.id), ids = ['none', 'full', ...lv, ...(key.endsWith('_n') ? [] : lv.map(i => 'a:' + i))];
      for (const id of ids) {
        const r = await evaluate(`__judge.cell(${JSON.stringify(key)}, ${JSON.stringify(id)}, ${JSON.stringify(dist)})`);
        writeFileSync(path.join(CELLS, key, `${dist}_${id.replace('%', 'pct').replace(':', '_')}.png`), Buffer.from(r.dataUrl.split(',')[1], 'base64'));
        index[key].dists[dist] ??= { crop: r.crop, drawn: {} };
        index[key].dists[dist].drawn[id] = r.drawnTriangles;
        run.cells++;
      }
    }
    await evaluate(`__judge.unload(${JSON.stringify(key)})`);
    run.models[key] = { seconds: Math.round((Date.now() - t0) / 100) / 10 };
    console.log(`${key}: ${Object.keys(index[key].dists.walk.drawn).length * 2} cells, ${run.models[key].seconds} s`);
  }
  let prevIndex = {};
  try { prevIndex = JSON.parse(readFileSync(path.join(CELLS, 'cells.json'), 'utf8')); } catch { /* first run */ }
  writeFileSync(path.join(CELLS, 'cells.json'), JSON.stringify({ ...prevIndex, ...index }, null, 1));
} finally {
  try { await browser?.send('Browser.close'); } catch { /* gone */ }
  await sleep(600);
  try { proc?.kill(); } catch { /* gone */ }
  release();
  server.close();
  clearInterval(timer);
}
const during = cpu.filter(c => c.t >= tLock).map(c => c.load);
run.cpu = { cores: os.cpus().length, model: os.cpus()[0].model, beforeEdge: before, meanDuringRun: Math.round(during.reduce((a, b) => a + b, 0) / Math.max(1, during.length)), maxDuringRun: Math.round(Math.max(...during)) };
run.seconds = Math.round((Date.now() - tLock) / 1000);
run.made = new Date().toISOString();
run.note = 'pictures only, nothing timed: the CPU load is recorded for the record';
if (logs.length) run.pageLog = logs.slice(0, 40);
let prevRun = {};
try { prevRun = JSON.parse(readFileSync(path.join(HERE, 'render_run.json'), 'utf8')); } catch { /* first run */ }
writeFileSync(path.join(HERE, 'render_run.json'), JSON.stringify({ ...run, models: { ...(prevRun.models || {}), ...run.models } }, null, 1));
console.log(JSON.stringify({ gpu: run.gpu, cells: run.cells, cpu: run.cpu, seconds: run.seconds }));
process.exit(0);
