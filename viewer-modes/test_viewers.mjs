// Drives both viewers in headless Edge with real key, mouse and touch input and checks Orbit / Walk / Ghost / Camera
// and the build replay. Usage: node test_viewers.mjs [house|phone|srisawan|fixes|landscape|replay ...]   (default: all)
// HOUSE_URL / SRIS_URL point it at other builds of the two pages. TEST_PORT, TEST_TMP and TEST_PROFILE give it its own
// debugging port, temp folder (screenshots, photos) and browser profile, so two runs cannot meet (defaults as before).
import { launch, pageApi, sleep } from './cdp.mjs';
import { mkdirSync, readdirSync, readFileSync, rmSync } from 'node:fs';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { tmpdir } from 'node:os';
import path from 'node:path';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');     // the project folder
const TMP = process.env.TEST_TMP || path.join(tmpdir(), 'viewer-modes-test');     // screenshots, photos, browser profile
const OUT = path.join(TMP, 'out'), DL = path.join(TMP, 'downloads');
const HOUSE = process.env.HOUSE_URL || pathToFileURL(path.join(ROOT, 'cad_test', 'house_3d_preview.html')).href;
const SRIS = process.env.SRIS_URL || pathToFileURL(path.join(ROOT, 'srisawan-viewer', 'Srisawan_3D_viewer.html')).href;
const only = process.argv.slice(2);
const want = name => !only.length || only.includes(name);
rmSync(DL, { recursive: true, force: true }); mkdirSync(DL, { recursive: true }); mkdirSync(OUT, { recursive: true });

const results = [];
function check(name, ok, info) {
  results.push({ name, ok: !!ok });
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${info !== undefined ? '   ' + JSON.stringify(info) : ''}`);
}
const r2 = v => Math.round(v * 100) / 100;
const D2R = Math.PI / 180;
const pngSize = file => { const b = readFileSync(file); return [b.readUInt32BE(16), b.readUInt32BE(20)]; };
const dist2 = (a, b) => Math.hypot(a.x - b.x, a.z - b.z);

const { browser, tab, close } = await launch({ port: Number(process.env.TEST_PORT) || 9333, profile: process.env.TEST_PROFILE || path.join(TMP, 'profile') });
const P = pageApi(tab);
await browser.send('Browser.setDownloadBehavior', { behavior: 'allow', downloadPath: DL.replace(/\//g, '\\'), eventsEnabled: true });

const st = () => P.evaluate(`(() => { const s = __viewer.state; return { mode: s.mode, floor: s.floor.key, level: s.floor.level, x: s.pos.x, y: s.pos.y, z: s.pos.z, yaw: s.yaw, pitch: s.pitch, touch: s.touch }; })()`);
const probe = (fn, ...args) => P.evaluate(`__viewer.probe.${fn}(${args.join(',')})`);
const setYaw = deg => P.evaluate(`(__viewer.state.yaw = ${deg} * Math.PI / 180, __viewer.state.pitch = 0, true)`);
const visible = sel => P.evaluate(`(() => { const e = document.querySelector(${JSON.stringify(sel)}); return !!e && getComputedStyle(e).display !== 'none' && e.getBoundingClientRect().width > 0; })()`);
const text = sel => P.evaluate(`document.querySelector(${JSON.stringify(sel)}).textContent`);
const hasOn = sel => P.evaluate(`document.querySelector(${JSON.stringify(sel)}).classList.contains('on')`);
const setInput = (sel, v, ev = 'input') => P.evaluate(`(() => { const e = document.querySelector(${JSON.stringify(sel)}); e.value = ${JSON.stringify(String(v))}; e.dispatchEvent(new Event('${ev}')); return e.value; })()`);
async function scan() { return P.evaluate(`[...Array(72)].map((_, i) => __viewer.probe.open(i * 5))`); }
async function nearestWall() { const d = await scan(); let i = 0; d.forEach((v, j) => { if (v < d[i]) i = j; }); return { yaw: i * 5, dist: d[i] }; }
async function holdUntilStill(code, maxMs = 15000) {   // hold a key until you stop making headway (< 12 cm/s)
  await P.keyDown(code); let prev = await st(), still = 0; const t0 = Date.now();
  while (Date.now() - t0 < maxMs) { await sleep(250); const cur = await st(); still = dist2(prev, cur) < 0.03 ? still + 1 : 0; if (still >= 2) break; prev = cur; }
  await P.keyUp(code); await sleep(80);
}
async function faceOpenest() { const d = await scan(); let i = 0; d.forEach((v, j) => { if (v > d[i]) i = j; }); await setYaw(i * 5); return d[i]; }
const fps = () => P.evaluate(`new Promise(r => { let n = 0; const t0 = performance.now(); const f = () => { n++; if (performance.now() - t0 < 1000) requestAnimationFrame(f); else r(n); }; requestAnimationFrame(f); })`);
const errorsIn = logs => logs.filter(l => /exception|error/i.test(l) && !/favicon/i.test(l));
async function newDownload(before, ms = 6000) {
  for (let t = 0; t < ms; t += 200) {
    const now = readdirSync(DL).filter(f => f.endsWith('.png') && !before.includes(f));
    if (now.length) { await sleep(300); return now[0]; }
    await sleep(200);
  }
  return null;
}
const thumbSize = () => P.evaluate(`(async () => { const i = document.querySelector('#vm-photos img'); if (!i) return null; await i.decode(); return [i.naturalWidth, i.naturalHeight]; })()`);

async function section(name, fn) {
  if (!want(name)) return;
  console.log(`\n=== ${name} ===`);
  try { await fn(); } catch (e) { check(`${name}: ran to the end`, false, e.message.split('\n').slice(0, 3).join(' | ')); }
  const errs = errorsIn(P.logs);
  if (errs.length) console.log('page errors:\n  ' + errs.join('\n  '));
}

// ------------------------------------------------------------------ DWG house, desktop
await section('house', async () => {
  await P.goto(HOUSE + '?build=0');
  check('loads without errors', !errorsIn(P.logs).length && !(await visible('#vm-err')), errorsIn(P.logs));
  check('starts in Orbit', (await st()).mode === 'orbit');
  console.log('      frames per second here (software GPU):', await fps());

  await P.press('Digit2');
  let s = await st();
  check('2 → Walk on the ground floor at eye height', s.mode === 'walk' && s.floor === 'ground' && Math.abs(s.y - (s.level + 1.6)) < 0.01, { floor: s.floor, level: s.level, y: r2(s.y) });
  const clr = await probe('clearance'), open = await probe('open'), onf = await probe('onFloor');
  check('Walk starts with room around you and a view ahead', clr >= 0.99 && open >= 3 && onf, { clearance: r2(clr), openAhead: r2(open), onFloor: onf });
  check('floor buttons show the walked floor', (await hasOn('#floors [data-f=ground]')) && !(await hasOn('#floors [data-f=both]')));
  check('Walk shows the whole house (upper floor as ceiling)', JSON.stringify(await probe('visible')) === '["ground","upper"]', await probe('visible'));
  await P.shot(OUT + '/house_walk_start.png');

  await faceOpenest();
  let a = await st(); await P.hold('KeyW', 1500); let b = await st();
  check('W walks forward', dist2(a, b) > 0.4 && Math.abs(b.y - a.y) < 1e-6, { moved: r2(dist2(a, b)) });

  let w = await nearestWall(); await setYaw(w.yaw);
  a = await st(); await holdUntilStill('KeyW'); b = await st();
  const left = await probe('open', w.yaw), crossed = await probe('crosses', a.x, a.z, b.x, b.z), nearW = await probe('clearance');
  check('Walk stops at a wall and does not pass through', !crossed && nearW > 0.2 && nearW < 0.6, { wallWas: r2(w.dist), moved: r2(dist2(a, b)), gapAhead: r2(left), nearestWall: r2(nearW) });
  // Sliding: try both sides without moving (the probe), then hold W towards the side the wall runs to.
  const p0 = await st();
  const tryDir = async off => { const r = await probe('walk', w.yaw + off, 1.0); await P.evaluate(`__viewer.state.pos.set(${p0.x}, ${p0.y}, ${p0.z})`); return r; };
  const plus = await tryDir(40), minus = await tryDir(-40);
  await setYaw(w.yaw + (plus >= minus ? 40 : -40)); a = await st(); await P.hold('KeyW', 1200); b = await st();
  const slidCross = await probe('crosses', a.x, a.z, b.x, b.z);
  check('Walk slides along a wall when you walk into it at an angle', !slidCross && (dist2(a, b) > 0.2 || Math.max(plus, minus) < 0.3),
    { slid: r2(dist2(a, b)), probeSides: [r2(plus), r2(minus)], note: Math.max(plus, minus) < 0.3 ? 'corner: nowhere to slide' : undefined });
  const many = await P.evaluate(`(() => {
    const v = __viewer, s = v.state, keep = s.pos.clone(); let seed = 11, n = 0, ok = 0, tries = 0;
    const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
    while (n < 40 && tries++ < 3000) {
      s.pos.x = -22 + rnd() * 44; s.pos.z = -14 + rnd() * 28;
      if (!v.probe.onFloor() || v.probe.clearance() < 0.6) continue;
      const d = [...Array(72)].map((_, i) => v.probe.open(i * 5)); let k = 0; d.forEach((x, j) => { if (x < d[k]) k = j; });
      if (d[k] > 2.5) continue;
      v.probe.walk(k * 5, d[k] + 1); const p = s.pos.clone();
      const a = v.probe.walk(k * 5 + 40, 1); s.pos.copy(p); const b = v.probe.walk(k * 5 - 40, 1);
      n++; if (Math.max(a, b) > 0.3) ok++;
    }
    s.pos.copy(keep); return [ok, n];
  })()`);
  check('sliding works at random spots along walls (40 tries)', many[1] >= 30 && many[0] >= many[1] * 0.9, { slid: many[0], of: many[1] });
  check('still on the floor and clear of walls', (await probe('onFloor')) && (await probe('clearance')) > 0.15, { clearance: r2(await probe('clearance')) });

  await P.press('PageUp'); s = await st();
  check('PgUp → upper floor at eye height, on the floor plate', s.floor === 'upper' && Math.abs(s.y - (s.level + 1.6)) < 0.01 && (await probe('onFloor')), { level: s.level, y: r2(s.y) });
  check('floor button follows (Upper)', await hasOn('#floors [data-f=upper]'));
  await P.shot(OUT + '/house_walk_upper.png');
  await P.press('PageUp'); check('PgUp on the top floor stays there', (await st()).floor === 'upper');
  await P.press('PageDown'); check('PgDn → ground floor', (await st()).floor === 'ground');
  await P.clickEl('#floors [data-f=upper]'); check('Upper button while walking → upper floor', (await st()).floor === 'upper');
  await P.clickEl('#floors [data-f=both]'); check('Both-floors button while walking → ground floor', (await st()).floor === 'ground');

  await P.clickEl('#glass');                    // checkbox now has focus; glass hidden
  await faceOpenest(); a = await st(); await P.hold('KeyW', 800); b = await st();
  await P.clickEl('#glass');
  check('keys still work after clicking a checkbox', dist2(a, b) > 0.1, { moved: r2(dist2(a, b)) });
  a = await st(); await P.keyDown('Space'); await sleep(100); await P.keyUp('Space'); await sleep(100);
  check('Space does not tick the focused checkbox', await P.evaluate(`document.getElementById('glass').checked`));

  await P.press('Digit3'); s = await st();
  check('3 → Ghost', s.mode === 'ghost');
  w = await nearestWall(); await setYaw(w.yaw);
  a = await st(); await P.hold('KeyW', 1500); b = await st();
  check('Ghost flies through walls', (await probe('crosses', a.x, a.z, b.x, b.z)) && dist2(a, b) > w.dist, { wallWas: r2(w.dist), moved: r2(dist2(a, b)) });
  a = await st(); await P.hold('Space', 700); b = await st(); check('Space rises', b.y - a.y > 0.5, { rise: r2(b.y - a.y) });
  a = await st(); await P.hold('KeyC', 700); b = await st(); check('C sinks', a.y - b.y > 0.5, { drop: r2(a.y - b.y) });
  a = await st(); await P.clickEl('#floors [data-f=ground]'); b = await st();
  check('Ghost: a floor button hides the other floor and does not move you', dist2(a, b) < 1e-6 && a.y === b.y && JSON.stringify(await probe('visible')) === '["ground"]', await probe('visible'));
  await P.clickEl('#floors [data-f=both]');
  await P.shot(OUT + '/house_ghost.png');

  const saved = await P.evaluate('({ x: __viewer.state.saved.pos.x, y: __viewer.state.saved.pos.y, z: __viewer.state.saved.pos.z })');
  await P.press('Escape'); await sleep(300);
  const c0 = await probe('camera');
  check('Esc → back to Orbit where you left it', (await st()).mode === 'orbit' && Math.hypot(c0.x - saved.x, c0.y - saved.y, c0.z - saved.z) < 0.5);
  check('Orbit after Walk: both floors visible again', JSON.stringify(await probe('visible')) === '["ground","upper"]');

  // Camera panel
  await P.clickEl('#vm-cam-btn');
  check('Camera panel opens', await visible('#vm-cam'));
  check('3:2 frame drawn, HD size shown', (await visible('#vm-frame')) && (await text('#vm-px')) === '1920 × 1280 px', await text('#vm-px'));
  await setInput('#vm-lens', 50);
  const c50 = await probe('camera');
  check('Lens 50 mm sets the view angle', Math.abs(c50.fov - 2 * Math.atan(12 / 50) / D2R) < 0.01, { fov: r2(c50.fov), label: await text('#vm-lens-v') });
  let before = readdirSync(DL);
  await P.press('KeyP');
  let file = await newDownload(before);
  check('P in Orbit takes a photo and downloads it', file && /^Sukhumvit_Orbit_overview_50mm_\d{4}-\d\d-\d\d_\d\d-\d\d-\d\d\.png$/.test(file), file);
  if (file) check('photo is 1920 × 1280 (3:2, HD)', JSON.stringify(pngSize(DL + '/' + file)) === '[1920,1280]', pngSize(DL + '/' + file));
  check('thumbnail added to the panel', (await P.evaluate(`document.querySelectorAll('#vm-photos img').length`)) === 1);

  await P.press('Digit2'); await faceOpenest();
  await setInput('#vm-tilt', 15);
  const ct = await probe('camera');
  check('Tilt slider tilts the camera', Math.abs(ct.rx - 15 * D2R) < 0.01 && ct.offsetY === null, { rx: r2(ct.rx / D2R) });
  await P.clickEl('#vm-straight');
  const cs = await probe('camera');
  check('Straight verticals: camera stays level, picture slides up', Math.abs(cs.rx) < 1e-9 && cs.offsetY !== null && cs.offsetY < 0, { rx: cs.rx, offsetY: cs.offsetY && r2(cs.offsetY) });
  await setInput('#vm-eye', 1.2);
  s = await st(); check('Eye height slider lowers the camera', Math.abs(s.y - (s.level + 1.2)) < 0.01, { y: r2(s.y) });
  await setInput('#vm-eye', 1.6);
  await P.shot(OUT + '/house_cam_panel.png');
  before = readdirSync(DL);
  await P.clickEl('#vm-shot');
  file = await newDownload(before);
  check('Take photo button in Walk → Walk photo named after the floor and lens', file && /^Sukhumvit_Walk_Ground-floor_24mm_/.test(file), file);
  if (file) check('Walk photo is 1920 × 1280', JSON.stringify(pngSize(DL + '/' + file)) === '[1920,1280]', pngSize(DL + '/' + file));
  if (file) console.log('      walk photo saved: ' + DL + '/' + file);

  await setInput('#vm-size', 3840, 'change');
  check('4K shows 3840 × 2560', (await text('#vm-px')) === '3840 × 2560 px', await text('#vm-px'));
  before = readdirSync(DL); await P.press('KeyP'); file = await newDownload(before, 12000);
  check('4K photo is 3840 × 2560', file && JSON.stringify(pngSize(DL + '/' + file)) === '[3840,2560]', file && pngSize(DL + '/' + file));
  await setInput('#vm-frame-sel', '9:16', 'change');
  check('9:16 at 4K shows 2160 × 3840', (await text('#vm-px')) === '2160 × 3840 px', await text('#vm-px'));
  before = readdirSync(DL); await P.press('KeyP'); file = await newDownload(before, 12000);
  check('9:16 photo is upright 2160 × 3840', file && JSON.stringify(pngSize(DL + '/' + file)) === '[2160,3840]', file && pngSize(DL + '/' + file));
  await setInput('#vm-frame-sel', 'screen', 'change'); await setInput('#vm-size', 1920, 'change');
  before = readdirSync(DL); await P.press('KeyP'); file = await newDownload(before);
  const [vw, vh] = await P.evaluate('[innerWidth, innerHeight]');
  check('Whole-screen photo keeps the window shape', file && (() => { const [w, h] = pngSize(DL + '/' + file); return w === 1920 && Math.abs(h - Math.round(1920 * vh / vw)) <= 1; })(), { photo: file && pngSize(DL + '/' + file), window: [vw, vh] });
  check('view is back to normal after photos (no leftover crop)', (await probe('camera')).offsetY !== null && Math.abs((await probe('camera')).fov - 2 * Math.atan(12 / 24) / D2R) < 0.01);
  await P.clickEl('#vm-straight'); await setInput('#vm-frame-sel', '3:2', 'change');
  await P.clickEl('#vm-cam-close');
  check('Camera panel closes', !(await visible('#vm-cam')) && !(await visible('#vm-frame')));
  before = readdirSync(DL); await P.press('KeyP'); file = await newDownload(before);
  check('P with the panel closed takes the whole screen (no hidden crop)', file && (() => { const [w, h] = pngSize(DL + '/' + file); return w === 1920 && Math.abs(h - Math.round(1920 * vh / vw)) <= 1; })(), file && pngSize(DL + '/' + file));

  await P.press('Digit1'); await sleep(400);
  await P.dblclick(760, 470); await sleep(400);
  s = await st();
  check('double-click in Orbit → Walk at that spot', s.mode === 'walk' && (await probe('onFloor')), { mode: s.mode, floor: s.floor, x: r2(s.x), z: r2(s.z) });

  // Touch on the same page: a touch shows the stick; the stick moves you; a second finger looks around.
  await tab.send('Emulation.setTouchEmulationEnabled', { enabled: true, maxTouchPoints: 5 });
  await P.tap(1000, 600);
  check('a touch shows the move stick and floor buttons', (await visible('#vm-stick')) && (await visible('#vm-ud')) && (await st()).touch);
  await faceOpenest();
  const [sx, sy] = await P.center('#vm-stick');
  a = await st();
  await P.touch('touchStart', [[sx, sy, 1]]); await P.touch('touchMove', [[sx, sy - 55, 1]]);
  await sleep(1500); b = await st();
  await P.touch('touchStart', [[sx, sy - 55, 1], [900, 400, 2]]); await sleep(50);
  await P.touch('touchMove', [[sx, sy - 55, 1], [960, 400, 2]]); await sleep(150);
  await P.touch('touchMove', [[sx, sy - 55, 1], [1010, 400, 2]]); await sleep(300);
  const c = await st();
  await P.touch('touchEnd', []); await sleep(200);
  check('stick moves you forward', dist2(a, b) > 0.3, { moved: r2(dist2(a, b)) });
  check('a second finger looks around while the stick is held', Math.abs(c.yaw - b.yaw) > 0.1 && dist2(b, c) > 0.02, { turned: r2((c.yaw - b.yaw) / D2R), movedMeanwhile: r2(dist2(b, c)) });
  const s0 = await st(); await sleep(400); const s1 = await st();
  check('letting go stops you', dist2(s0, s1) < 1e-6);
  await P.tapEl('#vm-up'); check('Upstairs button → upper floor', (await st()).floor === 'upper');
  await P.tapEl('#vm-down'); check('Downstairs button → ground floor', (await st()).floor === 'ground');
  await tab.send('Emulation.setTouchEmulationEnabled', { enabled: false });
  await P.click(1000, 600);
  check('using the mouse again hides the touch controls', !(await visible('#vm-stick')) && !(await st()).touch);
  await P.press('Escape');
});

// ------------------------------------------------------------------ DWG house, phone size
await section('phone', async () => {
  await tab.send('Emulation.setDeviceMetricsOverride', { width: 390, height: 844, deviceScaleFactor: 2, mobile: true });
  await tab.send('Emulation.setTouchEmulationEnabled', { enabled: true, maxTouchPoints: 5 });
  await P.goto(HOUSE + '?nodownload=1&build=0');
  const coarse = await P.evaluate(`matchMedia('(pointer: coarse)').matches`);
  console.log('      phone emulation reports a coarse pointer:', coarse);
  await P.shot(OUT + '/phone_orbit.png');
  await P.tapEl('#vm-modes [data-m=walk]');
  let s = await st();
  check('phone: Walk button works by touch', s.mode === 'walk');
  check('phone: touch controls showing', (await visible('#vm-stick')) && (await visible('#vm-ud')));
  check('phone: side panel and hint hidden while walking', !(await visible('#panel')) && !(await visible('#hint')));
  const hudW = await P.evaluate(`document.getElementById('vm-hud').getBoundingClientRect().width`);
  check('phone: top bar fits the screen', hudW <= 390 - 20, { width: r2(hudW) });
  check('phone: portrait view is not cropped narrow (24 mm spans the width)', Math.abs((await probe('camera')).fov - 2 * Math.atan(Math.tan(Math.atan(12 / 24)) * 844 / 390) / D2R) < 0.05, { fov: r2((await probe('camera')).fov) });
  await P.shot(OUT + '/phone_walk.png');
  await P.tapEl('#vm-hud-cam');
  check('phone: Camera button in the top bar opens the camera panel', await visible('#vm-cam'));
  const fr = await P.evaluate(`(() => { const f = document.getElementById('vm-frame').getBoundingClientRect(), c = document.getElementById('vm-cam').getBoundingClientRect(), k = document.getElementById('vm-stick').getBoundingClientRect(); return { frameTop: f.top, frameBottom: f.bottom, frameW: f.width, panelBottom: c.bottom, stickTop: k.top }; })()`);
  check('phone: the photo frame sits between the panel and the touch controls', fr.frameTop >= fr.panelBottom && fr.frameBottom <= fr.stickTop && fr.frameW > 200, fr);
  await P.shot(OUT + '/phone_cam.png');
  await P.tapEl('#vm-shot'); await sleep(1500);
  check('phone: photo taken (thumbnail)', (await P.evaluate(`document.querySelectorAll('#vm-photos img').length`)) === 1, await thumbSize());
  await P.tapEl('#vm-cam-close');
  await P.tapEl('#vm-exit');
  check('phone: Exit returns to Orbit and the panel comes back', (await st()).mode === 'orbit' && (await visible('#panel')));
  await P.goto(HOUSE + '?mode=ghost&touch=1&nodownload=1');
  check('phone: Ghost shows Up / Down', (await text('#vm-up')) === 'Up' && (await visible('#vm-ud')));
  const [ux, uy] = await P.center('#vm-up');
  let a = await st(); await P.touch('touchStart', [[ux, uy, 1]]); await sleep(800); await P.touch('touchEnd', []); await sleep(100); let b = await st();
  check('phone: holding Up rises', b.y - a.y > 0.5, { rise: r2(b.y - a.y) });
  await P.shot(OUT + '/phone_ghost.png');
  await tab.send('Emulation.clearDeviceMetricsOverride');
  await tab.send('Emulation.setTouchEmulationEnabled', { enabled: false });
});

// ------------------------------------------------------------------ Srisawan
await section('srisawan', async () => {
  await P.goto(SRIS + '?nodownload=1&build=0');
  check('loads without errors', !errorsIn(P.logs).length && !(await visible('#vm-err')), errorsIn(P.logs));
  console.log('      frames per second here (software GPU):', await fps());
  await P.press('Digit2');
  let s = await st();
  check('2 → Walk on floor 1 at eye height', s.mode === 'walk' && s.floor === 'L1' && Math.abs(s.y - 1.6) < 0.01, { floor: s.floor, y: r2(s.y) });
  check('Walk starts with room around you', (await probe('clearance')) >= 0.99 && (await probe('onFloor')), { clearance: r2(await probe('clearance')), openAhead: r2(await probe('open')) });
  check('Walk shows floors 1 and 2 (not floor 6)', JSON.stringify(await probe('visible')) === '["L1","L2"]', await probe('visible'));
  await P.shot(OUT + '/sris_walk_L1.png');
  await faceOpenest();
  let a = await st(); await P.hold('KeyW', 1500); let b = await st();
  check('W walks forward', dist2(a, b) > 0.4, { moved: r2(dist2(a, b)) });
  const w = await nearestWall(); await setYaw(w.yaw);
  a = await st(); await holdUntilStill('KeyW'); b = await st();
  const nearS = await probe('clearance');
  const floorAhead = await P.evaluate(`(() => { const s = __viewer.state, p = s.pos.clone(), y = ${w.yaw} * Math.PI / 180, out = [];
    for (const t of [0.1, 0.3, 0.5]) { s.pos.set(p.x - Math.sin(y) * t, p.y, p.z - Math.cos(y) * t); out.push(__viewer.probe.onFloor() ? 1 : 0); } s.pos.copy(p); return out.join(''); })()`);
  check('walls stop you (never through, ends up beside a wall)', !(await probe('crosses', a.x, a.z, b.x, b.z)) && nearS > 0.2 && nearS < 0.6, { gapAhead: r2(await probe('open', w.yaw)), nearestWall: r2(nearS), floorAhead, wallWas: r2(w.dist), moved: r2(dist2(a, b)) });
  await P.press('PageUp'); s = await st();
  check('PgUp → floor 2 at +5.00 m, standing on the slab', s.floor === 'L2' && Math.abs(s.y - 6.6) < 0.01 && (await probe('onFloor')), { y: r2(s.y) });
  await P.shot(OUT + '/sris_walk_L2.png');
  await P.press('PageUp'); check('PgUp on floor 2 stays (floor 6 is a separate drawing)', (await st()).floor === 'L2');
  await P.clickEl('#floors [data-f=F6]'); s = await st();
  check('Floor 6 button while walking → floor 6, shown on its own', s.floor === 'F6' && JSON.stringify(await probe('visible')) === '["F6"]' && (await hasOn('#floors [data-f=F6]')), await probe('visible'));
  check('floor 6 start has room around you', (await probe('clearance')) >= 0.5, { clearance: r2(await probe('clearance')) });
  await P.shot(OUT + '/sris_walk_F6.png');
  await P.clickEl('#floors [data-f=both]'); check('Floors 1 + 2 button while walking → floor 1', (await st()).floor === 'L1');
  await P.press('Digit3');
  a = await st(); await P.clickEl('#floors [data-f=L2]'); b = await st();
  check('Ghost: Floor 2 button shows floor 2 only and does not move you', dist2(a, b) < 1e-6 && JSON.stringify(await probe('visible')) === '["L2"]', await probe('visible'));
  await P.hold('Space', 1500);
  await P.shot(OUT + '/sris_ghost.png');
  await P.press('Escape'); await sleep(300);
  check('Esc → Orbit keeps the Floor 2 choice', (await st()).mode === 'orbit' && (await hasOn('#floors [data-f=L2]')) && JSON.stringify(await probe('visible')) === '["L2"]');
  await P.clickEl('#views [data-v=\"top\"]'); await sleep(300);
  check('Top view still works', (await st()).mode === 'orbit' && (await probe('camera')).y > 50, { camY: r2((await probe('camera')).y) });
  await P.clickEl('#floors [data-f=both]'); await P.clickEl('#views [data-v=\"3d\"]');
  await P.press('Digit2'); await P.clickEl('#vm-cam-btn'); await P.press('KeyP'); await sleep(1500);
  const t = await P.evaluate(`document.querySelector('#vm-photos img') && document.querySelector('#vm-photos img').title`);
  check('photo in Srisawan named after project, floor and lens', t && /^Srisawan_Walk_Floor-1_24mm_/.test(t), t);
  check('no errors during the run', !errorsIn(P.logs).length, errorsIn(P.logs));
});

// ------------------------------------------------------------------ fixes from the 16 Oct code review (house, desktop)
await section('fixes', async () => {
  await P.goto(HOUSE + '?nodownload=1&build=0');
  const nPhotos = () => P.evaluate(`document.querySelectorAll('#vm-photos img').length`);
  const waitPhoto = async n0 => { for (let i = 0; i < 40 && (await nPhotos()) === n0; i++) await sleep(200); };
  // Ghost, then Walk straight away: Ghost starts far outside the house; Walk must still land you on a floor.
  await P.press('Digit3'); await P.press('Digit2');
  let s = await st();
  const onf = await probe('onFloor');
  await faceOpenest(); let a = await st(); await P.hold('KeyW', 1000); let b = await st();
  check('Ghost then Walk from outside lands you on a floor, able to walk', s.mode === 'walk' && onf && dist2(a, b) > 0.2, { floor: s.floor, onFloor: onf, moved: r2(dist2(a, b)) });
  // In Ghost 1 m above the upper floor you are on the upper floor (photo name), not the floor below.
  await P.press('Digit3');
  await P.evaluate(`(__viewer.state.pos.y = 4.8 + 1.0, true)`);
  let n0 = await nPhotos();
  await P.press('KeyP'); await waitPhoto(n0);
  const title = await P.evaluate(`document.querySelector('#vm-photos img') && document.querySelector('#vm-photos img').title`);
  check('in Ghost 1 m above the upper floor, the photo is named after the upper floor', /_Ghost_Upper-floor_/.test(title || ''), title);
  // Holding P: auto-repeated key-downs take no extra photos.
  n0 = await nPhotos();
  const pk = extra => tab.send('Input.dispatchKeyEvent', { type: 'keyDown', code: 'KeyP', key: 'p', text: 'p', windowsVirtualKeyCode: 80, ...extra });
  await pk({}); for (let i = 0; i < 3; i++) await pk({ autoRepeat: true });
  await tab.send('Input.dispatchKeyEvent', { type: 'keyUp', code: 'KeyP', key: 'p', windowsVirtualKeyCode: 80 });
  await sleep(3000);
  check('holding P takes one photo, not a burst', (await nPhotos()) - n0 === 1, { taken: (await nPhotos()) - n0 });
  // Wheel: follows the scroll distance; wheel up = longer lens (zoom in), like the Orbit zoom.
  await P.press('Digit2');
  const lens0 = await P.evaluate('__viewer.state.lens');
  for (let i = 0; i < 10; i++) await tab.send('Input.dispatchMouseEvent', { type: 'mouseWheel', x: 900, y: 500, deltaX: 0, deltaY: -4 });
  await sleep(200);
  const lens1 = await P.evaluate('__viewer.state.lens');
  await tab.send('Input.dispatchMouseEvent', { type: 'mouseWheel', x: 900, y: 500, deltaX: 0, deltaY: -100 });
  await sleep(200);
  const lens2 = await P.evaluate('__viewer.state.lens');
  check('wheel follows the scroll distance: 10 small touchpad steps 0.8 mm, one mouse notch 2 mm', Math.abs(lens1 - lens0 - 0.8) < 0.05 && Math.abs(lens2 - lens1 - 2) < 0.05, { start: lens0, afterSmallSteps: r2(lens1), afterNotch: r2(lens2) });
  // A focused Frame list hands keys back to the viewer, and its type-ahead does not change the frame.
  await P.clickEl('#vm-cam-btn');
  await P.evaluate(`document.getElementById('vm-frame-sel').focus()`);
  const f0 = await P.evaluate(`document.getElementById('vm-frame-sel').value`);
  n0 = await nPhotos();
  await P.press('KeyP'); await waitPhoto(n0);
  await P.press('Digit4');
  check('with the Frame list focused, P still takes a photo and typing does not change the frame', (await P.evaluate(`document.getElementById('vm-frame-sel').value`)) === f0 && (await nPhotos()) === n0 + 1, { frame: await P.evaluate(`document.getElementById('vm-frame-sel').value`) });
  // Wide screen, Walk, Camera open: the frame sits between the side panel and the Camera panel, below the top bar; Exit stays clickable.
  const g = await P.evaluate(`(() => { const r = id => document.getElementById(id).getBoundingClientRect(); const f = r('vm-frame'), c = r('vm-cam'), p = r('panel'), x = r('vm-exit'), hud = r('vm-hud');
    const hit = document.elementFromPoint(x.left + x.width / 2, x.top + x.height / 2);
    return { frame: [f.left, f.top, f.right, f.bottom].map(Math.round), camLeft: Math.round(c.left), panelRight: Math.round(p.right), panelShown: p.width > 0, hudBottom: Math.round(hud.bottom), exitClickable: !!hit && hit.id === 'vm-exit' }; })()`);
  check('photo frame fits between the side panel and the Camera panel, below the top bar', g.frame[0] >= (g.panelShown ? g.panelRight : 0) && g.frame[2] <= g.camLeft && g.frame[1] >= g.hudBottom, g);
  check('Exit stays clickable with the Camera panel open', g.exitClickable, g);
  // A slow, careful look-drag does not capture the mouse; a plain click does.
  await P.clickEl('#vm-cam-close');
  await P.evaluate(`(() => { window.__locks = 0; document.querySelector('canvas').requestPointerLock = () => { window.__locks++; }; })()`);
  await P.mouse('mouseMoved', 900, 500, { button: 'none' }); await P.mouse('mousePressed', 900, 500);
  for (let i = 1; i <= 30; i++) await P.mouse('mouseMoved', 900 + i, 500, { button: 'left', buttons: 1 });
  await P.mouse('mouseReleased', 930, 500); await sleep(200);
  const afterDrag = await P.evaluate('window.__locks');
  await P.click(900, 520);
  const afterClick = await P.evaluate('window.__locks');
  check('a slow look-drag does not capture the mouse; a click does', afterDrag === 0 && afterClick === 1, { afterDrag, afterClick });
  // The shutter flash shows in Orbit with the Camera panel closed.
  await P.press('Digit1');
  await P.keyDown('KeyP');
  const anims = await P.evaluate(`document.getElementById('vm-flash').getAnimations().length`);
  await P.keyUp('KeyP'); await sleep(1500);
  check('the shutter flash shows in Orbit too', anims >= 1, { animations: anims });
  // Typos in the address are ignored instead of giving a blank view.
  await P.goto(HOUSE + '?mode=walk&yaw=north&pitch=up&nodownload=1');
  s = await st();
  check('typos in the address (yaw=north, pitch=up) are ignored', Number.isFinite(s.yaw) && Number.isFinite(s.pitch) && (await probe('onFloor')), { yaw: s.yaw, pitch: s.pitch });
  // A pixel-ratio change (browser zoom, another screen) keeps the 3D view sharp.
  await tab.send('Emulation.setDeviceMetricsOverride', { width: 1200, height: 760, deviceScaleFactor: 2, mobile: false });
  await sleep(1200);
  const buf = await P.evaluate(`[document.querySelector('canvas').width, innerWidth, devicePixelRatio]`);
  check('after a pixel-ratio change the drawing buffer follows (2 pixels per CSS pixel)', buf[0] === buf[1] * Math.min(buf[2], 2), buf);
  await tab.send('Emulation.clearDeviceMetricsOverride'); await sleep(500);
});

// ------------------------------------------------------------------ fixes from the 16 Oct code review (hospital)
await section('srisfix', async () => {
  await P.goto(SRIS + '?nodownload=1&build=0');
  // Walking on floor 1, Ghost, show Floor 6, then Walk: you walk on floor 6, the building on screen.
  await P.press('Digit2'); await P.press('Digit3'); await P.clickEl('#floors [data-f=F6]'); await P.press('Digit2');
  const s = await st();
  check('hospital: Floor 6 shown in Ghost, then Walk: you walk on floor 6', s.floor === 'F6' && JSON.stringify(await probe('visible')) === '["F6"]', { floor: s.floor, visible: await probe('visible') });
  // The panel note follows the floor you walk to with PgUp.
  await P.press('Digit1'); await P.clickEl('#floors [data-f=both]'); await P.press('Digit2'); await P.press('PageUp');
  const note = await text('#note');
  check('hospital: the floor note follows PgUp to floor 2', (await st()).floor === 'L2' && note.startsWith('Floor 2 at +5.00 m'), note.slice(0, 50));
});

// ------------------------------------------------------------------ landscape phone
await section('landscape', async () => {
  await tab.send('Emulation.setDeviceMetricsOverride', { width: 844, height: 390, deviceScaleFactor: 2, mobile: true });
  await tab.send('Emulation.setTouchEmulationEnabled', { enabled: true, maxTouchPoints: 5 });
  await P.goto(HOUSE + '?mode=walk&touch=1&nodownload=1');
  check('landscape phone: side panel hidden while walking', !(await visible('#panel')));
  await P.tapEl('#vm-hud-cam');
  const g = await P.evaluate(`(() => { const r = id => document.getElementById(id).getBoundingClientRect(); const f = r('vm-frame'), c = r('vm-cam'), k = r('vm-stick'), hud = r('vm-hud');
    const at = id => { const el = document.getElementById(id), b = el.getBoundingClientRect(); const h = document.elementFromPoint(b.left + b.width / 2, b.top + b.height / 2); return !!h && (h === el || el.contains(h)); };
    return { frame: [f.left, f.top, f.right, f.bottom].map(Math.round), cam: [c.left, c.top, c.right, c.bottom].map(Math.round), stickTop: Math.round(k.top), hudBottom: Math.round(hud.bottom),
      exit: at('vm-exit'), up: at('vm-up'), snap: at('vm-snap') }; })()`);
  check('landscape phone: the photo frame is clear of the top bar, the Camera panel and the touch controls',
    g.frame[1] >= g.hudBottom && g.frame[2] <= g.cam[0] && g.frame[3] <= g.stickTop && g.frame[2] - g.frame[0] > 150, g);
  check('landscape phone: Exit, Upstairs and the Photo button stay tappable with the Camera open', g.exit && g.up && g.snap, g);
  const n0 = await P.evaluate(`document.querySelectorAll('#vm-photos img').length`);
  await P.tapEl('#vm-snap'); await sleep(2500);
  check('landscape phone: the Photo button takes a photo', (await P.evaluate(`document.querySelectorAll('#vm-photos img').length`)) === n0 + 1);
  await P.shot(OUT + '/landscape_cam.png');
  await tab.send('Emulation.clearDeviceMetricsOverride');
  await tab.send('Emulation.setTouchEmulationEnabled', { enabled: false });
});

// ------------------------------------------------------------------ build replay (the "loading phase")
await section('replay', async () => {
  await P.goto(HOUSE + '?nodownload=1');
  check('page opens on the Build settings screen with the drawing', (await P.evaluate('__build.phase')) === 'settings' && (await visible('#br-card')) && !(await visible('#panel')));
  check('settings show each floor\'s level and wall height from the drawing', JSON.stringify(await P.evaluate(`[...document.querySelectorAll('#br-card input[type=number]')].map(i => i.value)`)) === '["0.90","3.90","4.80","3.50"]');
  await P.press('Digit2');
  check('viewer keys do nothing on the settings screen', (await st()).mode === 'orbit');
  await setInput('#br-card input[data-k=upper][data-p=level]', '5.00', 'change');
  await setInput('#br-card input[data-k=upper][data-p=height]', '3.00', 'change');
  await P.clickEl('#br-speed [data-s=quick]');
  await P.clickEl('#br-go');
  check('Generate starts the replay, with captions', (await P.evaluate('__build.phase')) === 'play' && (await visible('#br-sub')));
  await sleep(2500);
  const mid = await P.evaluate(`({ T: __build.state.T, step: __build.state.step, caption: document.getElementById('br-sub').textContent })`);
  check('the replay moves through the steps, quoting the real numbers', mid.T > 0.05 && mid.T < 1 && /\d/.test(mid.caption), mid);
  await P.press('Digit3');
  check('viewer keys are locked while it plays', (await st()).mode === 'orbit');
  for (let i = 0; i < 80 && (await P.evaluate('__build.phase')) !== 'done'; i++) await sleep(250);
  check('the replay ends in the normal viewer', (await P.evaluate('__build.phase')) === 'done' && (await visible('#panel')) && !(await visible('#br-card')) && JSON.stringify(await probe('visible')) === '["ground","upper"]');
  await P.press('Digit2'); await P.press('PageUp');
  const s = await st();
  check('walking on the upper floor uses the level set before Generate (5.00 m)', s.floor === 'upper' && Math.abs(s.y - 6.6) < 0.01 && (await probe('onFloor')), { y: r2(s.y), onFloor: await probe('onFloor') });
  await P.press('Escape');
  await P.clickEl('#br-again'); await sleep(600);
  check('Replay the build plays it again', (await P.evaluate('__build.phase')) === 'play');
  await P.press('Escape'); await sleep(300);
  check('Esc skips to the finished model', (await P.evaluate('__build.phase')) === 'done' && (await visible('#panel')));
  await P.clickEl('#br-open'); await sleep(300);
  check('Build settings reopens with the changed values', (await P.evaluate('__build.phase')) === 'settings' && (await P.evaluate(`document.querySelector('#br-card input[data-k=upper][data-p=level]').value`)) === '5.00');
  await P.clickEl('#br-skip0'); await sleep(300);
  check('Skip on the settings screen shows the finished model', (await P.evaluate('__build.phase')) === 'done');
  check('no page errors during the house replay', !errorsIn(P.logs).length, errorsIn(P.logs));
  await P.goto(SRIS + '?speed=quick&build=play');
  for (let i = 0; i < 80 && (await P.evaluate('__build.phase')) !== 'done'; i++) await sleep(250);
  check('hospital: the replay runs to the end, floors 1 + 2 shown, floor 6 hidden', (await P.evaluate('__build.phase')) === 'done' && JSON.stringify(await probe('visible')) === '["L1","L2"]');
  check('hospital: no page errors', !errorsIn(P.logs).length, errorsIn(P.logs));
  await tab.send('Emulation.setDeviceMetricsOverride', { width: 390, height: 844, deviceScaleFactor: 2, mobile: true });
  await P.goto(HOUSE + '?nodownload=1');
  const btn = await P.evaluate(`(() => { const b = document.getElementById('br-go').getBoundingClientRect(); const h = document.elementFromPoint(b.left + b.width / 2, b.top + b.height / 2); return { top: Math.round(b.top), bottom: Math.round(b.bottom), clickable: !!h && h.id === 'br-go' }; })()`);
  check('phone: the Generate button is fully visible and tappable', btn.clickable && btn.bottom <= 844, btn);
  await P.shot(OUT + '/phone_settings.png');
  await tab.send('Emulation.clearDeviceMetricsOverride');
});

// ------------------------------------------------------------------ fixes from the 19 Oct review (PC)
await section('fixes2', async () => {
  const nPhotos = () => P.evaluate(`document.querySelectorAll('#vm-photos img').length`);
  const worldY = expr => P.evaluate(`(() => { const m = ${expr}; m.updateWorldMatrix(true, false); m.geometry.computeBoundingBox(); const b = m.geometry.boundingBox.clone().applyMatrix4(m.matrixWorld); return [b.min.y, b.max.y]; })()`);
  await P.goto(HOUSE + '?nodownload=1');
  await setInput('#br-card input[data-k=upper][data-p=level]', '', 'change');
  check('a cleared Level box keeps its old value', (await P.evaluate(`document.querySelector('#br-card input[data-k=upper][data-p=level]').value`)) === '4.80' && (await P.evaluate('__build.state.settings.upper.level')) === 4.8);
  await setInput('#br-card input[data-k=ground][data-p=level]', '1.50', 'change');
  await P.clickEl('#br-skip0'); await sleep(400);
  const pl = await worldY('__host.plinths[0]');
  check('raising the ground level keeps the plinth on the ground (0 to 1.50 m)', Math.abs(pl[0]) < 0.01 && Math.abs(pl[1] - 1.5) < 0.01, pl.map(r2));
  await P.clickEl('#br-open'); await sleep(300);
  await setInput('#br-card input[data-k=ground][data-p=height]', '2.00', 'change');
  await P.clickEl('#br-skip0'); await sleep(400);
  const wall = await worldY('__host.rise.ground.find(r => r.scales).mesh');
  check('a 2.00 m wall height makes the walls themselves 2.00 m (so hover, double-click and walking agree)', Math.abs(wall[1] - wall[0] - 2.0) < 0.02 && Math.abs(wall[0] - 1.5) < 0.02, wall.map(r2));
  // Replay from your own view: you come back to it.
  await P.mouse('mouseMoved', 900, 450, { button: 'none' }); await P.mouse('mousePressed', 900, 450);
  for (let i = 1; i <= 10; i++) await P.mouse('mouseMoved', 900 + i * 15, 450, { button: 'left', buttons: 1 });
  await P.mouse('mouseReleased', 1050, 450);
  let before = await probe('camera');                 // wait until the drag's glide has died away
  for (let i = 0; i < 60; i++) { await sleep(300); const c = await probe('camera'); const d = Math.hypot(c.x - before.x, c.y - before.y, c.z - before.z); before = c; if (d < 0.002) break; }
  await P.clickEl('#br-again'); await sleep(600); await P.press('Escape'); await sleep(1500);
  const after = await probe('camera');
  check('after a replay you are back at the view you left', Math.hypot(after.x - before.x, after.y - before.y, after.z - before.z) < 0.1, { before: [before.x, before.y, before.z].map(r2), after: [after.x, after.y, after.z].map(r2) });
  // ?cam=1 waits for the build screen: the Camera panel opens after it, not over it.
  await P.goto(HOUSE + '?cam=1&nodownload=1');
  const camDuring = await visible('#vm-cam');
  await P.clickEl('#br-skip0'); await sleep(400);
  check('?cam=1 opens the Camera panel after the build screen, not over it', !camDuring && (await visible('#vm-cam')), { during: camDuring });
  await P.goto(HOUSE + '?nodownload=1');
  const facts = await text('#br-card ul');
  check('the settings card counts the 38 layers in the plan areas', /on 38 layers/.test(facts), facts);
  // Ghost names the floor among the floors that are showing.
  await P.goto(HOUSE + '?nodownload=1&build=0');
  await P.clickEl('#floors [data-f=ground]'); await P.press('Digit3');
  await P.evaluate(`(__viewer.state.pos.y = 6.2, true)`);
  const n0 = await nPhotos();
  await P.press('KeyP');
  for (let i = 0; i < 40 && (await nPhotos()) === n0; i++) await sleep(200);
  const t2 = await P.evaluate(`document.querySelector('#vm-photos img').title`);
  check('Ghost above the hidden upper floor names the photo after the floor showing', /_Ghost_Ground-floor_/.test(t2), t2);
  // The end of a thin partition (the review's spot) stops you at the body's edge, not 2-3 cm away.
  await P.press('Digit2');
  // Closest approach to any wall along the way, from five starts near the spot (the old rays let you get within 3 cm).
  const gap = await P.evaluate(`(() => { const v = __viewer, s = v.state; let worst = Infinity;
    for (const [x, z, yaw] of [[21.80, -5.64, 175], [21.80, -5.64, 170], [21.80, -5.64, 180], [21.75, -5.64, 175], [21.85, -5.64, 175]]) {
      s.pos.set(x, s.pos.y, z); let min = v.probe.clearance();
      for (let i = 0; i < 60; i++) { v.probe.walk(yaw, 0.05); min = Math.min(min, v.probe.clearance()); }
      worst = Math.min(worst, min);
    } return worst; })()`);
  check('walking at the end of a thin partition never brings you closer than the body\'s edge', gap > 0.25, { closestApproach: r2(gap) });
  // Hospital.
  await P.goto(SRIS + '?nodownload=1&build=0');
  await P.press('Digit2'); await P.clickEl('#floors [data-f=F6]'); await P.press('Digit3');
  check('hospital: Walk on floor 6, then Ghost: floor 6 stays on screen', JSON.stringify(await probe('visible')) === '["F6"]', await probe('visible'));
  await P.press('Digit1'); await P.clickEl('#floors [data-f=both]');
  await P.clickEl('#views [data-v="top"]'); await sleep(500);
  await P.clickEl('#br-open'); await sleep(300);
  await setInput('#br-card input[data-k=L2][data-p=level]', '5.60', 'change');
  await P.clickEl('#br-skip0'); await sleep(500);
  const cam = await probe('camera');
  check('hospital: after Build settings the Top view is still the view (button and camera agree)', (await hasOn('#views [data-v="top"]')) && cam.y > 50, { camY: r2(cam.y) });
  check('hospital: the floor note quotes the level set in Build settings', (await text('#note')).includes('+5.60 m'), (await text('#note')).slice(0, 60));
  await P.evaluate('__build.seek(1)'); await sleep(300);
  check('all seven steps are ticked at the end of the replay', (await P.evaluate(`document.querySelectorAll('#br-steps li.br-done').length`)) === 7);
  // While the floors line up, the camera tilts without turning.
  const az = [];
  for (const T of [0.32, 0.35, 0.38]) { await P.evaluate(`__build.seek(${T})`); await sleep(250); const c = await probe('camera'); az.push(Math.atan2(c.dir[0], c.dir[2]) * 180 / Math.PI); }
  const turn = (a, b) => Math.abs(((a - b + 540) % 360) - 180);
  check('while the floors line up the camera tilts without turning', turn(az[1], az[0]) < 2 && turn(az[2], az[1]) < 2, az.map(r2));
  await P.evaluate('__build.skip()');
  check('no page errors in these checks', !errorsIn(P.logs).length, errorsIn(P.logs));
});

const failed = results.filter(r => !r.ok).length;
console.log(`\n${results.length - failed} passed, ${failed} failed`);
await close();
process.exit(failed ? 1 : 0);
