// Headless Edge for the bank furniture test (a copy of ../browser.mjs with its own ports, 9770 - 9789), driven over the DevTools protocol (no packages: Node 22+ has fetch and WebSocket).
// Holds the machine-wide one-Edge-at-a-time lock that the app's tools use (app/tools/edge-lock.mjs: the file %TEMP%\wt-edge.lock,
// created with the 'wx' flag, holding { step, pid, startedAt }; a lock whose pid is gone is stale and taken over) from launch()
// until close(). Same file and format, so this waits for the app's browser runs and they wait for this one.
// Edge is started with the real graphics chip (ANGLE on Direct3D 11) unless `gpu: false`; never a visible window.
import { spawn } from 'node:child_process';
import { closeSync, openSync, readFileSync, unlinkSync, writeFileSync, writeSync } from 'node:fs';
import os from 'node:os';
import path from 'node:path';

export const EDGE = process.env.EDGE || 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe';
export const LOCK_FILE = path.join(process.env.TEMP || os.tmpdir(), 'wt-edge.lock');
export const sleep = ms => new Promise(r => setTimeout(r, ms));

// ---------------------------------------------------------------- the lock
let held = false;
const alive = pid => { if (!Number.isInteger(pid) || pid <= 0) return false; try { process.kill(pid, 0); return true; } catch (e) { return e.code === 'EPERM'; } };
const holder = () => { try { return JSON.parse(readFileSync(LOCK_FILE, 'utf8')); } catch { return null; } };
export async function acquire(step, waitMs = 45 * 60 * 1000) {
  const t0 = Date.now();
  let told = 0;
  for (;;) {
    try {
      const fd = openSync(LOCK_FILE, 'wx');
      try { writeSync(fd, JSON.stringify({ step, pid: process.pid, startedAt: new Date().toISOString() })); } finally { closeSync(fd); }
      held = true;
      process.once('exit', release);
      return;
    } catch (e) { if (e.code !== 'EEXIST') throw e; }
    const h = holder();
    if (h && h.pid === process.pid) { held = true; return; }
    if (h && !alive(h.pid)) {
      const again = holder();
      if (again && again.pid === h.pid && again.startedAt === h.startedAt) {
        try { unlinkSync(LOCK_FILE); } catch { /* taken over by someone else */ }
        console.log(`edge lock: took over a stale lock of '${h.step}' (pid ${h.pid} is gone)`);
      }
      continue;
    }
    if (Date.now() - t0 > waitMs) throw new Error(`edge lock: waited ${Math.round(waitMs / 60000)} min for '${h?.step}' (pid ${h?.pid}); giving up`);
    if (Date.now() - told > 60000) { console.log(`edge lock: waiting for '${h?.step ?? '?'}' (pid ${h?.pid ?? '?'}, since ${h?.startedAt ?? '?'})`); told = Date.now(); }
    await sleep(250);                                                    // (the shared helper polls every 2 s; this one a little more often)
  }
}
export function release() {
  if (!held) return;
  held = false;
  const h = holder();
  if (h && h.pid === process.pid) { try { unlinkSync(LOCK_FILE); } catch { /* gone */ } }
}

// ---------------------------------------------------------------- DevTools protocol
function connect(url) {
  return new Promise((resolve, reject) => {
    const ws = new WebSocket(url);
    let id = 0;
    const pending = new Map(), listeners = [];
    ws.onmessage = ev => {
      const msg = JSON.parse(ev.data);
      if (msg.id && pending.has(msg.id)) {
        const { res, rej, method } = pending.get(msg.id);
        pending.delete(msg.id);
        if (msg.error) rej(new Error(method + ': ' + msg.error.message)); else res(msg.result);
      } else if (msg.method) listeners.forEach(fn => fn(msg));
    };
    ws.onopen = () => resolve({
      send: (method, params = {}) => new Promise((res, rej) => { const i = ++id; pending.set(i, { res, rej, method }); ws.send(JSON.stringify({ id: i, method, params })); }),
      on: fn => listeners.push(fn),
      close: () => ws.close(),
    });
    ws.onerror = e => reject(new Error('websocket error ' + (e.message || '')));
  });
}

export async function portAnswers(port) {
  try { await fetch(`http://127.0.0.1:${port}/json/version`, { signal: AbortSignal.timeout(1200) }); return true; } catch { return false; }
}

// gpu: true -> ANGLE on Direct3D 11 with the graphics chip; false -> SwiftShader (software), as the prototypes' tests run.
export async function launch({ port, profile, width = 1920, height = 1080, gpu = true, extra = [], step = 'furniture_test bank_furnished' }) {
  if (port < 9770 || port > 9789) throw new Error('the bank furniture test keeps to ports 9770 - 9789');
  if (await portAnswers(port)) throw new Error(`port ${port} already answers: another browser is using it`);
  await acquire(step);
  let proc;
  try {
    const g = gpu ? ['--use-angle=d3d11', '--enable-gpu', '--ignore-gpu-blocklist'] : ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'];
    proc = spawn(EDGE, ['--headless=new', ...g, ...extra, '--allow-file-access-from-files', `--remote-debugging-port=${port}`, `--user-data-dir=${profile}`,
      `--window-size=${width},${height}`, '--hide-scrollbars', '--no-first-run', '--no-default-browser-check', 'about:blank'], { stdio: ['ignore', 'ignore', openSync(profile + '-stderr.log', 'a')] });     // Edge's own messages, for when it does not start
    let ver = null;
    for (let i = 0; i < 600 && !ver; i++) { try { ver = await (await fetch(`http://127.0.0.1:${port}/json/version`)).json(); } catch { await sleep(100); } }
    if (!ver) throw new Error('Edge did not open its DevTools port within a minute');
    const list = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
    const browser = await connect(ver.webSocketDebuggerUrl);
    const tab = await connect(list.find(t => t.type === 'page').webSocketDebuggerUrl);
    await tab.send('Runtime.enable'); await tab.send('Page.enable'); await tab.send('Log.enable');
    await tab.send('Emulation.setDeviceMetricsOverride', { width, height, deviceScaleFactor: 1, mobile: false });
    const logs = [];
    tab.on(msg => {
      const p = msg.params;
      if (msg.method === 'Runtime.consoleAPICalled') logs.push(`[console.${p.type}] ` + p.args.map(a => a.value ?? a.description ?? '').join(' '));
      if (msg.method === 'Runtime.exceptionThrown') logs.push('[exception] ' + (p.exceptionDetails.exception?.description || p.exceptionDetails.text));
      if (msg.method === 'Log.entryAdded') logs.push(`[log.${p.entry.level}] ${p.entry.text} ${p.entry.url || ''}`);
    });
    const evaluate = async expr => {
      const r = await tab.send('Runtime.evaluate', { expression: expr, awaitPromise: true, returnByValue: true });
      if (r.exceptionDetails) throw new Error('eval failed: ' + (r.exceptionDetails.exception?.description || r.exceptionDetails.text) + '\n  in: ' + expr.slice(0, 300));
      return r.result.value;
    };
    const goto = async (url, readyExpr, timeoutMs = 90000) => {
      logs.length = 0;
      await tab.send('Page.navigate', { url });
      const t0 = Date.now();
      for (;;) {
        try { if (await evaluate(readyExpr)) return; } catch { /* still loading */ }
        if (Date.now() - t0 > timeoutMs) throw new Error('page did not get ready: ' + url + '\n' + logs.join('\n'));
        await sleep(200);
      }
    };
    const shot = async file => { const r = await tab.send('Page.captureScreenshot', { format: 'png' }); writeFileSync(file, Buffer.from(r.data, 'base64')); };
    const close = async () => {
      try { await browser.send('Browser.close'); } catch { /* gone */ }
      await sleep(600);
      try { proc.kill(); } catch { /* gone */ }
      release();
    };
    return { proc, browser, tab, logs, evaluate, goto, shot, close };
  } catch (e) {
    try { proc?.kill(); } catch { /* gone */ }
    release();
    throw e;
  }
}
