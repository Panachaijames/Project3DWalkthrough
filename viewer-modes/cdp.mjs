// Tiny DevTools-protocol driver for headless Edge. No packages: Node 22+ has fetch and WebSocket built in.
import { spawn } from 'node:child_process';
import { writeFileSync } from 'node:fs';

const EDGE = process.env.EDGE || 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe';   // or Chrome
export const sleep = ms => new Promise(r => setTimeout(r, ms));

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
      send: (method, params = {}) => new Promise((res, rej) => {
        const i = ++id; pending.set(i, { res, rej, method });
        ws.send(JSON.stringify({ id: i, method, params }));
      }),
      on: fn => listeners.push(fn),
      close: () => ws.close(),
    });
    ws.onerror = e => reject(new Error('websocket error ' + (e.message || '')));
  });
}

export async function launch({ port = 9333, profile, width = 1400, height = 880 }) {
  const proc = spawn(EDGE, ['--headless=new', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist',
    '--allow-file-access-from-files', `--remote-debugging-port=${port}`, `--user-data-dir=${profile}`,
    `--window-size=${width},${height}`, '--no-first-run', '--no-default-browser-check', 'about:blank'], { stdio: 'ignore' });
  let ver = null;
  for (let i = 0; i < 150 && !ver; i++) {
    try { ver = await (await fetch(`http://127.0.0.1:${port}/json/version`)).json(); } catch { await sleep(100); }
  }
  if (!ver) { proc.kill(); throw new Error('Edge did not start'); }
  const list = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
  const browser = await connect(ver.webSocketDebuggerUrl);
  const tab = await connect(list.find(t => t.type === 'page').webSocketDebuggerUrl);
  await tab.send('Runtime.enable'); await tab.send('Log.enable'); await tab.send('Page.enable');
  const close = async () => { try { await browser.send('Browser.close'); } catch { /* already gone */ } setTimeout(() => proc.kill(), 500); };
  return { proc, browser, tab, close };
}

const KEYS = {
  KeyW: ['w', 87], KeyA: ['a', 65], KeyS: ['s', 83], KeyD: ['d', 68], KeyP: ['p', 80], KeyC: ['c', 67], KeyE: ['e', 69],
  Space: [' ', 32], Digit1: ['1', 49], Digit2: ['2', 50], Digit3: ['3', 51], Digit4: ['4', 52], Escape: ['Escape', 27],
  PageUp: ['PageUp', 33], PageDown: ['PageDown', 34], ShiftLeft: ['Shift', 16], ArrowUp: ['ArrowUp', 38],
};

export function pageApi(tab) {
  const logs = [];
  tab.on(msg => {
    const p = msg.params;
    if (msg.method === 'Runtime.consoleAPICalled') logs.push(`[console.${p.type}] ` + p.args.map(a => a.value ?? a.description ?? '').join(' '));
    if (msg.method === 'Runtime.exceptionThrown') logs.push('[exception] ' + (p.exceptionDetails.exception?.description || p.exceptionDetails.text));
    if (msg.method === 'Log.entryAdded') logs.push(`[log.${p.entry.level}] ${p.entry.text} ${p.entry.url || ''}`);
  });
  const evaluate = async expr => {
    const r = await tab.send('Runtime.evaluate', { expression: expr, awaitPromise: true, returnByValue: true });
    if (r.exceptionDetails) throw new Error('eval failed: ' + (r.exceptionDetails.exception?.description || r.exceptionDetails.text) + '\n  in: ' + expr);
    return r.result.value;
  };
  const keyDown = code => {
    const [key, vk] = KEYS[code];
    return tab.send('Input.dispatchKeyEvent', key.length === 1
      ? { type: 'keyDown', code, key, text: key, windowsVirtualKeyCode: vk }
      : { type: 'rawKeyDown', code, key, windowsVirtualKeyCode: vk });
  };
  const keyUp = code => tab.send('Input.dispatchKeyEvent', { type: 'keyUp', code, key: KEYS[code][0], windowsVirtualKeyCode: KEYS[code][1] });
  const press = async code => { await keyDown(code); await keyUp(code); await sleep(120); };
  const hold = async (code, ms) => { await keyDown(code); await sleep(ms); await keyUp(code); await sleep(80); };
  const mouse = (type, x, y, extra = {}) => tab.send('Input.dispatchMouseEvent', { type, x, y, button: 'left', clickCount: 1, ...extra });
  const click = async (x, y, clickCount = 1) => { await mouse('mouseMoved', x, y, { button: 'none' }); await mouse('mousePressed', x, y, { clickCount }); await mouse('mouseReleased', x, y, { clickCount }); await sleep(150); };
  const dblclick = async (x, y) => { await click(x, y, 1); await click(x, y, 2); };
  const touch = (type, pts) => tab.send('Input.dispatchTouchEvent', { type, touchPoints: pts.map(([x, y, id]) => ({ x, y, id: id ?? 0 })) });
  const tap = async (x, y) => { await touch('touchStart', [[x, y]]); await sleep(60); await touch('touchEnd', []); await sleep(200); };
  const shot = async path => { const r = await tab.send('Page.captureScreenshot', { format: 'png' }); writeFileSync(path, Buffer.from(r.data, 'base64')); };
  const goto = async url => {
    logs.length = 0;
    await tab.send('Page.navigate', { url });
    await sleep(300);
    for (let i = 0; i < 300; i++) {
      try { if (await evaluate('!!window.__viewer')) { await sleep(1200); return; } } catch { /* page still loading */ }
      await sleep(100);
    }
    throw new Error('viewer did not load: ' + url + '\n' + logs.join('\n'));
  };
  const center = sel => evaluate(`(() => { const e = document.querySelector(${JSON.stringify(sel)}); if (!e) return null; const r = e.getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2]; })()`);
  const clickEl = async sel => { const c = await center(sel); if (!c) throw new Error('no element ' + sel); await click(c[0], c[1]); };
  const tapEl = async sel => { const c = await center(sel); if (!c) throw new Error('no element ' + sel); await tap(c[0], c[1]); };
  return { evaluate, keyDown, keyUp, press, hold, mouse, click, dblclick, touch, tap, shot, goto, center, clickEl, tapEl, logs };
}
