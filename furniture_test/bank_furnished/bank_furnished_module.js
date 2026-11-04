// ---------------------------------------------------------------------------
// Furniture test with the bank's own models: added to a copy of the bank page by make_bank_furnished.mjs (the page's own
// script is not changed). The 3D team's 8 models of this bank (banquet/*.glb, embedded byte for byte) stand at the 65 pieces of
// their 8 families: 62 copies, since the banquet is one 3 m bench for its run of four DIOR modules. Each model is normalised
// once (its place and turn in the team's Max scene undone against its own piece) and put at every piece of its family by that
// piece's CAD block: insertion point, turn, and Revit's baked-in mirror (placements.json, from the analysis). Those pieces'
// boxes are not drawn but stay Walk's colliders; the other 120 pieces stay boxes. Ways of drawing:
//   A  boxes, as now
//   B  every model at full detail, as plain copies (each piece its own meshes, sharing the model's geometry)
//   C  every model slimmed to a budget per piece (20,000 / 10,000 / 5,000 / 2,500 triangles), plain copies; a model under the
//      budget is drawn as it is. Slimmed once in Node (slim_models.mjs: three 0.186.1 SimplifyModifier), embedded as GLB files
//   D  level of detail: a model's full detail within 3 m of the camera, its 5,000 version beyond (three's LOD, 10 % hysteresis)
//   E  full detail, but visitor chair01 (241,326 triangles a chair) at 10,000
//   P  (extra check, the projection) all 185 pieces with a model: the 65 with theirs, the other seats with the chair test's
//      chair (Chair.glb), the other tables, coffee tables and sofas with their kind's model, the kinds with no model at all
//      (ATMs, plants, cabinets ...) with the banquet's detail (4,720 triangles, the median of the nine models); full or a budget
// One neutral material per model part (calm greys and warm tones): the exports' own materials are black fallbacks.
// What a way needs is decoded when the way is first picked (the GLBs stay base64 text in the page until then) and put on the
// graphics chip before its first frame. Measure: 120 frames back to back, each finished on the chip (a 1-pixel readPixels).
// Address: ?furniture=A|B|C|D|E|P&budget=full|20000|10000|5000|2500. Test hook: window.__bankFurnished.
// ---------------------------------------------------------------------------
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';

const T_MODULE = performance.now();                     // ms since the navigation started
const DATA = __BF_DATA__;

const host = window.__host, { FL, furniture, camera } = host;
const scene = Object.values(FL)[0].group.parent;
const D2R = Math.PI / 180, UP = new THREE.Vector3(0, 1, 0);
const num = n => Math.round(n).toLocaleString('en-US');
const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const mb = b => (b / 1048576).toFixed(b >= 10485760 ? 1 : 2) + ' MB';
const rows = r => new THREE.Matrix4().set(...r.flat());
const BUDGETS = DATA.budgets;
const kTris = n => n >= 1e6 ? (n / 1e6).toFixed(2) + ' M' : num(n);

// The page keeps its renderer to itself: the scene hands it over at its next render (its first, at start-up).
const renderer = await new Promise(resolve => {
  const own = scene.onBeforeRender;
  scene.onBeforeRender = function (r, ...rest) { scene.onBeforeRender = own; resolve(r); return own.call(this, r, ...rest); };
});
const T_BANK_FRAME = performance.now();
const gl = renderer.getContext();
const dbg = gl.getExtension('WEBGL_debug_renderer_info');
const GPU = String(dbg ? gl.getParameter(dbg.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER));
const px = new Uint8Array(4);
const finish = () => gl.readPixels(0, 0, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, px);

// ---------------------------------------------------------------- materials: one per model part
const MATS = {};
for (const [name, m] of Object.entries(DATA.models)) {
  MATS[name] = m.parts.map((p, i) => {
    const c = m.colours[i % m.colours.length];
    const mat = new THREE.MeshStandardMaterial({ color: c.hex, roughness: c.rough ?? 0.8, metalness: 0 });
    mat.name = `${name}: ${p.name} (${c.name})`;
    return mat;
  });
}

// ---------------------------------------------------------------- the GLBs: decoded on first use, then kept
const loader = new GLTFLoader();
const templates = new Map();                            // asset key -> { root, triangles, bytes (GPU), ms }
const decodeLog = [];
async function bytesOf(el) {
  const b64 = document.getElementById(el).textContent.trim();
  if (Uint8Array.fromBase64) return Uint8Array.fromBase64(b64);
  try { return new Uint8Array(await (await fetch('data:application/octet-stream;base64,' + b64)).arrayBuffer()); } catch (e) { /* below */ }
  const bin = atob(b64), out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
  return out;
}
const freeze = o => o.traverse(n => { n.updateMatrix(); n.matrixAutoUpdate = false; });
function gpuBytes(geometries) {                         // vertex and index buffers, each buffer counted once
  const seen = new Set();
  let bytes = 0;
  for (const g of geometries) {
    for (const a of Object.values(g.attributes)) { const arr = a.isInterleavedBufferAttribute ? a.data.array : a.array; if (!seen.has(arr)) { seen.add(arr); bytes += arr.byteLength; } }
    if (g.index && !seen.has(g.index.array)) { seen.add(g.index.array); bytes += g.index.array.byteLength; }
  }
  return bytes;
}
async function template(key) {
  if (templates.has(key)) return templates.get(key);
  const a = DATA.assets[key], [model] = key.split('@');
  const t0 = performance.now();
  const bytes = await bytesOf(a.el);
  const t1 = performance.now();
  const gltf = await loader.parseAsync(bytes.buffer, '');
  const t2 = performance.now();
  const g = gltf.scene;
  let i = 0;
  const geos = [];
  g.traverse(o => { if (o.isMesh) { o.material = MATS[model][i++]; geos.push(o.geometry); } });
  if (i !== DATA.models[model].parts.length) throw new Error(`${key}: ${i} parts, expected ${DATA.models[model].parts.length}`);
  let root = g;
  if (a.budget === 'full') {                             // the export as it came: normalised by a matrix (the slimmed GLBs are already)
    root = new THREE.Group();
    root.matrix.copy(rows(DATA.models[model].normalise)); root.matrixAutoUpdate = false;
    root.add(g);
  }
  freeze(g);
  root.name = `template ${key}`;
  const tris = geos.reduce((s, x) => s + (x.index ? x.index.count : x.attributes.position.count) / 3, 0);
  if (tris !== a.triangles) throw new Error(`${key}: ${tris} triangles, expected ${a.triangles}`);
  const tp = { key, root, geometries: geos, triangles: tris, gpuBytes: gpuBytes(geos), fileBytes: a.bytes, decodeMs: t1 - t0, parseMs: t2 - t1 };
  templates.set(key, tp);
  decodeLog.push({ key, bytes: a.bytes, base64Ms: +(t1 - t0).toFixed(1), parseMs: +(t2 - t1).toFixed(1) });
  return tp;
}

// ---------------------------------------------------------------- the pieces
const boxOf = id => furniture ? furniture.meshOf(id) : null;
const placements = [];                                  // the 62 copies of the team's models
for (const [name, m] of Object.entries(DATA.models)) {
  if (m.standInOnly) continue;
  for (const p of m.pieces) {
    const box = boxOf(p.key);
    if (!box || !FL[p.floor]) { console.warn('bank_furnished: no box for', p.key); continue; }
    placements.push({ model: name, key: p.key, ids: p.ids, floor: p.floor, y0: p.level + p.base, box, boxes: p.ids.map(boxOf).filter(Boolean),
      place: rows(p.place), centre: new THREE.Vector3(...m.centre).applyMatrix4(rows(p.place)) });
  }
}
const standIns = [];                                    // mode P: the other 120 pieces
for (const s of DATA.standIns) {
  const box = boxOf(s.id), m = DATA.models[s.model];
  if (!box || !FL[s.floor]) continue;
  const place = new THREE.Matrix4().compose(new THREE.Vector3(s.x, s.level + s.base, -s.y), new THREE.Quaternion().setFromAxisAngle(UP, s.rot * D2R), new THREE.Vector3(1, 1, 1))
    .multiply(new THREE.Matrix4().makeTranslation(-m.centre[0], 0, -m.centre[2]));
  standIns.push({ model: s.model, key: s.id, ids: [s.id], floor: s.floor, y0: s.level + s.base, box, boxes: [box], place, centre: new THREE.Vector3(s.x, s.level + s.base + m.centre[1], -s.y) });
}
const furnishedIds = new Set(placements.flatMap(p => p.ids));
const floorKeys = Object.keys(FL);

// ---------------------------------------------------------------- ways of drawing
const MODES = ['A', 'B', 'C', 'D', 'E', 'P'];
const trisOf = model => DATA.models[model].triangles;
const pick = (model, budget) => (budget === 'full' || trisOf(model) <= budget) ? `${model}@full` : `${model}@${budget}`;
// what each copy draws: a key, or [near key, far key] for a level of detail
function spec(mode, budget) {
  const per = p => {
    if (mode === 'B') return pick(p.model, 'full');
    if (mode === 'C') return pick(p.model, budget);
    if (mode === 'D') { const near = pick(p.model, 'full'), far = pick(p.model, DATA.lodBudget); return near === far ? near : [near, far]; }
    if (mode === 'E') return p.model === DATA.eModel ? pick(p.model, DATA.eBudget) : pick(p.model, 'full');
    if (mode === 'P') return pick(p.model, budget);
    return null;
  };
  const list = mode === 'A' ? [] : placements.concat(mode === 'P' ? standIns : []);
  return list.map(p => ({ p, what: per(p) }));
}
const variantName = (mode, budget) => mode === 'C' || mode === 'P' ? `${mode}${budget}` : mode;
const keysOf = s => [...new Set(s.flatMap(x => [].concat(x.what)))];
const variants = new Map();                             // name -> { name, groups: {floor: Group}, copies, keys }

function copyOf(tp, matrix) {
  const w = new THREE.Group();
  w.matrixAutoUpdate = false; w.matrix.copy(matrix);
  w.add(tp.root.clone(true));
  return w;
}
const T = new THREE.Matrix4();
async function build(mode, budget) {
  const name = variantName(mode, budget);
  if (variants.has(name)) return variants.get(name);
  const s = spec(mode, budget), keys = keysOf(s);
  for (const k of keys) await template(k);
  const groups = Object.fromEntries(floorKeys.map(k => [k, Object.assign(new THREE.Group(), { name: `bank furnished ${name} ${k}` })]));
  const copies = [];
  for (const { p, what } of s) {
    const c = { p, what, dy: 0 };
    if (Array.isArray(what)) {                           // a level of detail: its origin at the model's centre
      const lod = new THREE.LOD();
      lod.name = `lod ${p.key}`; lod.matrixAutoUpdate = false;
      lod.matrix.makeTranslation(p.centre.x, p.centre.y, p.centre.z);
      const rel = new THREE.Matrix4().makeTranslation(-p.centre.x, -p.centre.y, -p.centre.z).multiply(p.place);
      lod.addLevel(copyOf(templates.get(what[0]), rel), 0);
      lod.addLevel(copyOf(templates.get(what[1]), rel), DATA.lodDistance, 0.1);
      c.obj = lod; c.lod = lod;
    } else {
      c.obj = copyOf(templates.get(what), p.place);
    }
    c.obj.name = `${p.model} at ${p.key}`;
    c.base = c.obj.matrix.clone();
    groups[p.floor].add(c.obj);
    copies.push(c);
  }
  const v = { name, mode, budget, groups, copies, keys,
    fileBytes: keys.reduce((a, k) => a + DATA.assets[k].bytes, 0), gzipBytes: keys.reduce((a, k) => a + DATA.assets[k].gzipBytes, 0),
    gpuBytes: gpuBytes(keys.flatMap(k => templates.get(k).geometries)), geometries: keys.reduce((a, k) => a + templates.get(k).geometries.length, 0) };
  variants.set(name, v);
  return v;
}
// Puts a way's geometry on the chip (and compiles its programs, with the scene's own lights) before its first frame: one copy
// of each geometry it uses, not culled, drawn once to the canvas; the frame after it is drawn normally.
function upload(v) {
  const g = new THREE.Group();
  for (const k of v.keys) { const c = templates.get(k).root.clone(true); c.traverse(o => { o.frustumCulled = false; }); g.add(c); }
  scene.add(g);
  const t0 = performance.now();
  renderer.render(scene, camera); finish();
  const ms = performance.now() - t0;
  scene.remove(g);
  return ms;
}

// ---------------------------------------------------------------- switching
const HIDDEN = new THREE.MeshBasicMaterial({ visible: false }), HIDDEN_LINE = new THREE.LineBasicMaterial({ visible: false });
const ownMaterial = new Map();
const allBoxes = furniture ? furniture.pieces().map(p => furniture.meshOf(p.id)).filter(Boolean) : [];
let mode = 'A', budget = 5000, current = null, busy = 0, lastSwitch = null, queue = Promise.resolve();
function hideBoxes(which) {                             // the boxes of furnished pieces: not drawn, still colliders
  for (const b of allBoxes) for (const o of [b, ...b.children]) {
    if (!ownMaterial.has(o)) ownMaterial.set(o, o.material);
    const hide = which === 'all' || (which === 'furnished' && furnishedIds.has(b.userData.id));
    o.material = hide ? (o.isLineSegments ? HIDDEN_LINE : HIDDEN) : ownMaterial.get(o);
  }
}
function setMode(m, b) {                                // switches one at a time, in the order asked
  if (!MODES.includes(m)) return Promise.resolve(false);
  busy++;
  const run = queue.then(() => switchTo(m, b));
  queue = run.catch(e => { console.error('bank_furnished:', e); });
  return run.finally(() => { busy--; });
}
async function switchTo(m, b) {
  if (b !== undefined) budget = b === 'full' ? 'full' : Number(b);
  if (m === 'C' && !BUDGETS.includes(budget)) budget = 5000;
  if (m === 'P' && budget !== 'full' && !BUDGETS.includes(budget)) budget = 'full';
  const t0 = performance.now();
  {
    showBusy(m === 'A' ? '' : 'Loading the models…');
    const decodedBefore = decodeLog.length;
    let v = null, t1 = t0, t2 = t0, uploadMs = 0;
    if (m !== 'A') {
      const s = spec(m, budget), keys = keysOf(s);
      for (const k of keys) await template(k);
      t1 = performance.now();
      v = await build(m, budget);
      t2 = performance.now();
    }
    if (current) for (const k of floorKeys) current.groups[k].removeFromParent();
    current = v;
    if (v) { for (const k of floorKeys) FL[k].group.add(v.groups[k]); follow(true); uploadMs = upload(v); }
    hideBoxes(m === 'A' ? 'none' : m === 'P' ? 'all' : 'furnished');
    mode = m;
    const t3 = performance.now();
    renderer.render(scene, camera); finish();            // the first frame with them, finished on the chip
    const t4 = performance.now();
    const fresh = decodeLog.slice(decodedBefore);
    lastSwitch = { mode: m, budget: m === 'C' || m === 'P' ? budget : null, at: +t0.toFixed(1), decodedNow: fresh.length,
      base64Ms: +fresh.reduce((a, d) => a + d.base64Ms, 0).toFixed(1), parseMs: +fresh.reduce((a, d) => a + d.parseMs, 0).toFixed(1),
      decodeMs: +(t1 - t0).toFixed(1), buildMs: +(t2 - t1).toFixed(1), uploadMs: +uploadMs.toFixed(1), firstFrameMs: +(t4 - t3).toFixed(1),
      totalMs: +(t4 - t0).toFixed(1), firstFrameDoneAt: +t4.toFixed(1) };
    showBusy('');
    syncUi();
    return lastSwitch;
  }
}

// ---------------------------------------------------------------- every frame: follow the boxes (heights, ticks) and the build replay
let fps = 0, frames = 0, since = performance.now(), shown = 0;
function follow(force) {
  if (!current) return;
  const done = !window.__build || window.__build.phase === 'done';
  for (const c of current.copies) {
    c.obj.visible = done && c.p.box.visible;             // the kind's show tick
    const dy = c.p.box.position.y - c.p.y0;               // a typed height moves what stands on it
    if (force || Math.abs(dy - c.dy) > 1e-6) { c.dy = dy; c.obj.matrix.copy(T.makeTranslation(0, dy, 0).multiply(c.base)); c.obj.matrixWorldNeedsUpdate = true; }
  }
}
function tick(now) {
  frames++;
  if (now - since >= 1000) { fps = frames * 1000 / (now - since); frames = 0; since = now; }
  follow(false);
  if (now - shown > 250) { shown = now; showLive(); }
  requestAnimationFrame(tick);
}

// ---------------------------------------------------------------- counts
const modelTris = () => !current ? 0 : current.copies.reduce((a, c) => a + templates.get(c.lod ? c.what[c.lod.getCurrentLevel()] : c.what).triangles, 0);
const nearCopies = () => !current ? 0 : current.copies.filter(c => c.lod && c.lod.getCurrentLevel() === 0).length;
function memory() {
  const live = current ? { geometries: current.geometries, bytes: current.gpuBytes, assets: current.keys.length } : { geometries: 0, bytes: 0, assets: 0 };
  return { info: { ...renderer.info.memory }, models: live, allDecoded: { assets: templates.size, bytes: gpuBytes([...templates.values()].flatMap(t => t.geometries)) } };
}

// ---------------------------------------------------------------- Measure: 120 frames, each finished before the next
let last = null;
function measure(n = 120) {
  const draw = () => { renderer.render(scene, camera); finish(); };
  for (let i = 0; i < 5; i++) draw();                   // warm-up: programs compiled, buffers on the chip
  const { calls, triangles } = renderer.info.render;
  const t0 = performance.now();
  for (let i = 0; i < n; i++) draw();
  const ms = (performance.now() - t0) / n, size = renderer.getDrawingBufferSize(new THREE.Vector2());
  last = { mode, budget: mode === 'C' || mode === 'P' ? budget : null, frames: n, ms: Math.round(ms * 100) / 100, fps: Math.round(10000 / ms) / 10,
    triangles, calls, modelTriangles: modelTris(), nearFull: nearCopies(), gpu: GPU, width: size.x, height: size.y,
    view: window.__viewer ? window.__viewer.mode : 'orbit', at: new Date().toISOString() };
  out.innerHTML = `<b>${last.ms.toFixed(1)} ms a frame = ${last.fps.toFixed(0)} fps</b><br>${label(mode, budget)}: ${num(triangles)} triangles drawn, ${num(calls)} draw calls, ${size.x} × ${size.y} px`;
  return last;
}
// A walk straight through (for D: does the switch between full and slimmed show as a jolt?): the camera at eye height from
// `from` to `to` (plan x, y) in `frames` steps, looking along the way, each frame finished on the chip. The viewer's own camera
// comes back at its next frame.
function walkThrough({ floor, from, to, frames: n = 240, eye = 1.6, pitchDeg = -8 }) {
  const f = FL[floor], lv = f.group.position.y + f.level, yaw = Math.atan2(-(to[0] - from[0]), to[1] - from[1]);
  const times = [], levels = () => current ? current.copies.map(c => c.lod ? c.lod.getCurrentLevel() : -1) : [];
  let switches = 0, prev = null;
  const rot = camera.rotation.clone(), pos = camera.position.clone();
  for (let i = 0; i <= n; i++) {
    const t = i / n;
    camera.position.set(from[0] + (to[0] - from[0]) * t, lv + eye, -(from[1] + (to[1] - from[1]) * t));
    camera.rotation.set(pitchDeg * D2R, yaw, 0, 'YXZ'); camera.updateMatrixWorld();
    const t0 = performance.now();
    renderer.render(scene, camera); finish();
    times.push(performance.now() - t0);
    const l = levels();
    if (prev) switches += l.reduce((a, x, k) => a + (x !== prev[k] ? 1 : 0), 0);
    prev = l;
  }
  camera.position.copy(pos); camera.rotation.copy(rot); camera.updateMatrixWorld();
  const s = [...times].sort((a, b) => a - b), q = p => s[Math.min(s.length - 1, Math.floor(p * s.length))];
  return { mode, budget: mode === 'C' || mode === 'P' ? budget : null, frames: times.length, metres: Math.hypot(to[0] - from[0], to[1] - from[1]),
    medianMs: +q(0.5).toFixed(2), p95Ms: +q(0.95).toFixed(2), maxMs: +s[s.length - 1].toFixed(2), over33: times.filter(x => x > 33.3).length,
    over16: times.filter(x => x > 16.7).length, levelSwitches: switches };
}

// ---------------------------------------------------------------- the panel
const css = document.createElement('style');
css.textContent = `
#bf-panel{position:fixed;right:12px;bottom:34px;width:min(360px,calc(100vw - 48px));max-height:calc(100vh - 60px);overflow:auto;box-sizing:border-box;background:var(--panel,#ffffffee);border:1px solid var(--line,#d5dade);border-radius:10px;padding:10px 13px;box-shadow:0 2px 10px #0001;z-index:5;font-size:12.5px;color:var(--ink,#1d2329)}
#bf-panel h2{font-size:14px;margin:0 0 3px}
#bf-panel .bf-sub{color:var(--muted,#5b6670);font-size:12px;margin:0 0 7px}
#bf-panel .bf-modes label{display:flex;align-items:flex-start;gap:7px;font-size:12.5px;margin:3px 0;cursor:pointer}
#bf-panel .bf-modes input{margin:2px 0 0}
#bf-panel .bf-modes b{display:inline-block;width:14px}
#bf-panel .bf-extra{color:var(--muted,#5b6670)}
#bf-panel .bf-row{display:flex;gap:5px;flex-wrap:wrap;margin:6px 0 6px 21px;align-items:center}
#bf-panel .bf-row button{padding:3px 8px;font-size:12px}
#bf-panel .bf-row button.on{background:var(--accent,#2f6f8f);border-color:var(--accent,#2f6f8f);color:#fff}
#bf-panel table{border-collapse:collapse;width:100%;margin:6px 0;font-variant-numeric:tabular-nums;font-size:12px}
#bf-panel th{color:var(--muted,#5b6670);font-weight:normal;text-align:right;padding:1px 3px;border-bottom:1px solid var(--line,#d5dade)}
#bf-panel td{text-align:right;padding:1px 3px;white-space:nowrap}
#bf-panel th:first-child,#bf-panel td:first-child{text-align:left}
#bf-panel td i{display:inline-block;width:9px;height:9px;border-radius:2px;margin-right:2px;vertical-align:-1px;border:1px solid #0002}
#bf-panel dl{display:grid;grid-template-columns:auto 1fr;gap:1px 10px;margin:6px 0;font-variant-numeric:tabular-nums}
#bf-panel dt{color:var(--muted,#5b6670)}
#bf-panel dd{margin:0;text-align:right}
#bf-panel .bf-out{background:#f4f6f7;border:1px solid var(--line,#d5dade);border-radius:7px;padding:6px 8px;margin-top:6px;font-variant-numeric:tabular-nums;min-height:1.4em}
#bf-panel .bf-out b{font-size:13.5px}
#bf-panel .bf-busy{color:var(--accent,#2f6f8f);font-weight:600;min-height:1.2em}
#bf-panel .bf-small{color:var(--muted,#5b6670);font-size:11.5px;margin-top:6px;overflow-wrap:anywhere}
#bf-panel details summary{cursor:pointer;color:var(--muted,#5b6670);font-size:12px;margin-top:6px}
`;
document.head.appendChild(css);
const ui = document.createElement('div');
ui.id = 'bf-panel';
const modelNames = Object.keys(DATA.models).filter(n => !DATA.models[n].standInOnly);
const fullTris = placements.reduce((a, p) => a + trisOf(p.model), 0);
const label = (m, b) => m === 'C' ? `C ${num(b)} a piece` : m === 'P' ? `P ${b === 'full' ? 'full detail' : num(b) + ' a piece'}` : m;
const swatches = n => DATA.models[n].colours.slice(0, DATA.models[n].parts.length).map(c => `<i style="background:${c.hex}" title="${esc(c.name)}"></i>`).join('');
const downloads = [['B', 'full'], ...BUDGETS.map(b => ['C', b]), ['D'], ['E'], ['P', 'full'], ...BUDGETS.map(b => ['P', b])].map(([m, b]) => {
  const keys = keysOf(spec(m, b));
  return { m, b, label: label(m, b), bytes: keys.reduce((a, k) => a + DATA.assets[k].bytes, 0), gzip: keys.reduce((a, k) => a + DATA.assets[k].gzipBytes, 0) };
});
ui.innerHTML = `<h2>Furniture test: the bank's own models</h2>
<div class="bf-sub">The 3D team's 8 models at the <b>${furnishedIds.size}</b> pieces of their families (${placements.length} copies: the banquet is one bench for its run of 4), placed by each piece's CAD block (insertion point, turn, mirror). The other ${allBoxes.length - furnishedIds.size} pieces stay boxes.</div>
<div class="bf-modes">
  <label><input type="radio" name="bf-mode" value="A"><span><b>A</b> Boxes, as now</span></label>
  <label><input type="radio" name="bf-mode" value="B"><span><b>B</b> Full detail, plain copies</span></label>
  <label><input type="radio" name="bf-mode" value="C"><span><b>C</b> Slimmed to a budget a piece, plain copies (a model under it stays as it is)</span></label>
  <div class="bf-row bf-budgets">${BUDGETS.map(b => `<button data-b="${b}">${num(b)}</button>`).join('')}</div>
  <label><input type="radio" name="bf-mode" value="D"><span><b>D</b> Level of detail: full within ${DATA.lodDistance} m, ${num(DATA.lodBudget)} beyond</span></label>
  <label><input type="radio" name="bf-mode" value="E"><span><b>E</b> Full detail, but visitor chair01 at ${num(DATA.eBudget)}</span></label>
  <label class="bf-extra"><input type="radio" name="bf-mode" value="P"><span><b>P</b> Extra check: all ${allBoxes.length} pieces with a model (stand-ins for the ${allBoxes.length - furnishedIds.size} without one)</span></label>
  <div class="bf-row bf-pbudgets"><button data-b="full">full</button>${BUDGETS.map(b => `<button data-b="${b}">${num(b)}</button>`).join('')}</div>
</div>
<div class="bf-busy"></div>
<table class="bf-models"><thead><tr><th>Model</th><th>pieces</th><th>full</th><th>now</th></tr></thead><tbody>
${modelNames.map(n => `<tr data-m="${esc(n)}"><td title="${esc(DATA.models[n].family)}">${swatches(n)} ${esc(n)}</td><td>${DATA.models[n].piecesFurnished}</td><td>${num(trisOf(n))}</td><td class="bf-now"></td></tr>`).join('')}
</tbody></table>
<dl>
  <dt>Models' triangles</dt><dd class="bf-mtris"></dd>
  <dt>Scene triangles drawn</dt><dd class="bf-tris"></dd>
  <dt>Draw calls</dt><dd class="bf-calls"></dd>
  <dt>Frames a second</dt><dd class="bf-fps"></dd>
  <dt>Download, this way</dt><dd class="bf-dl"></dd>
  <dt>Models on the chip</dt><dd class="bf-mem"></dd>
  <dt>Models loaded</dt><dd class="bf-load"></dd>
</dl>
<div class="bf-row" style="margin-left:0"><button class="bf-measure">Measure (120 frames)</button></div>
<div class="bf-out">Press Measure: 120 frames drawn back to back, each one finished on the graphics chip.</div>
<div class="bf-small">Graphics: ${esc(GPU)}</div>
<details><summary>Download for the models, per way</summary>
<table><thead><tr><th>Way</th><th>GLB files</th><th>gzipped</th></tr></thead><tbody>
${downloads.map(d => `<tr><td>${esc(d.label)}</td><td>${mb(d.bytes)}</td><td>${mb(d.gzip)}</td></tr>`).join('')}
</tbody></table></details>
<div class="bf-small">Materials: the exports' ${DATA.exportMaterials} materials are all black 'fallback' ones (the real V-Ray / Corona ones did not come across), so each model part is drawn in one neutral colour of its own here (the swatches). Slimmed once in Node with three ${esc(DATA.three)}'s SimplifyModifier, per part.</div>`;
document.body.appendChild(ui);
const out = ui.querySelector('.bf-out');
ui.querySelectorAll('input[name=bf-mode]').forEach(r => r.addEventListener('change', e => { e.target.blur(); setMode(e.target.value); }));
ui.querySelectorAll('.bf-budgets button').forEach(btn => { btn.onclick = e => { e.currentTarget.blur(); setMode('C', Number(btn.dataset.b)); }; });
ui.querySelectorAll('.bf-pbudgets button').forEach(btn => { btn.onclick = e => { e.currentTarget.blur(); setMode('P', btn.dataset.b === 'full' ? 'full' : Number(btn.dataset.b)); }; });
ui.querySelector('.bf-measure').onclick = e => { e.currentTarget.blur(); out.textContent = 'Measuring…'; setTimeout(() => measure(120), 40); };
function showBusy(t) { ui.querySelector('.bf-busy').textContent = t; }
function syncUi() {
  ui.querySelectorAll('input[name=bf-mode]').forEach(r => { r.checked = r.value === mode; });
  ui.querySelectorAll('.bf-budgets button').forEach(b => b.classList.toggle('on', mode === 'C' && Number(b.dataset.b) === budget));
  ui.querySelectorAll('.bf-pbudgets button').forEach(b => b.classList.toggle('on', mode === 'P' && String(budget) === b.dataset.b));
  for (const n of modelNames) {
    const cell = ui.querySelector(`tr[data-m="${CSS.escape(n)}"] .bf-now`);
    let t = '';
    if (mode === 'A') t = 'box';
    else if (mode === 'D') { const far = pick(n, DATA.lodBudget); t = far.endsWith('@full') ? num(trisOf(n)) : `${num(trisOf(n))} / ${num(DATA.assets[far].triangles)}`; }
    else { const s = spec(mode, budget).find(x => x.p.model === n); t = s ? num(DATA.assets[s.what].triangles) : ''; }
    cell.textContent = t;
  }
  const v = current;
  const dl = downloads.find(d => d.m === mode && ((mode !== 'C' && mode !== 'P') || String(d.b) === String(budget)));
  ui.querySelector('.bf-dl').textContent = dl ? `${mb(dl.bytes)} of GLB (${mb(dl.gzip)} gzipped)` : 'none (boxes)';
  ui.querySelector('.bf-mem').textContent = v ? `${mb(v.gpuBytes)} (${v.geometries} geometries)` : 'none';
  const L = lastSwitch && lastSwitch.mode !== 'A' ? lastSwitch : null;
  ui.querySelector('.bf-load').textContent = L ? `${(L.totalMs / 1000).toFixed(2)} s for ${label(L.mode, L.budget ?? budget)} (decode ${(L.decodeMs / 1000).toFixed(2)}, upload ${(L.uploadMs / 1000).toFixed(2)})` : '–';
}
function showLive() {
  const r = renderer.info.render;
  const mt = modelTris();
  ui.querySelector('.bf-mtris').textContent = mode === 'A' ? '0 (boxes)' : `${kTris(mt)}${mode === 'D' ? ` (${nearCopies()} full)` : ''}`;
  ui.querySelector('.bf-tris').textContent = num(r.triangles);
  ui.querySelector('.bf-calls').textContent = num(r.calls);
  ui.querySelector('.bf-fps').textContent = fps ? fps.toFixed(0) + ' (live)' : '…';
}

// ---------------------------------------------------------------- start
const params = new URLSearchParams(location.search);
const startMode = MODES.includes(params.get('furniture')) ? params.get('furniture') : 'A';
const pb = params.get('budget');
const startBudget = pb === 'full' ? 'full' : BUDGETS.includes(Number(pb)) ? Number(pb) : (startMode === 'P' ? 'full' : 5000);
requestAnimationFrame(tick);
const startSwitch = await setMode(startMode, startBudget);
const nav = performance.getEntriesByType('navigation')[0];
const startup = { mode: startMode, budget: startMode === 'C' || startMode === 'P' ? startBudget : null,
  responseEnd: nav ? +nav.responseEnd.toFixed(1) : null, domContentLoaded: nav ? +nav.domContentLoadedEventEnd.toFixed(1) : null,
  moduleStart: +T_MODULE.toFixed(1), bankFirstFrame: +T_BANK_FRAME.toFixed(1), firstFrameWithModels: startSwitch.firstFrameDoneAt,
  switch: startSwitch, decoded: decodeLog.slice() };
window.__bankFurnished = {
  ready: true, setMode, measure, walkThrough, memory, get mode() { return mode; }, get budget() { return budget; }, get last() { return last; },
  get lastSwitch() { return lastSwitch; }, get busy() { return !!busy; }, startup, decodeLog, downloads, gpu: GPU,
  live: () => ({ fps, triangles: renderer.info.render.triangles, calls: renderer.info.render.calls, modelTriangles: modelTris(), nearFull: nearCopies() }),
  counts: { furnished: furnishedIds.size, copies: placements.length, standIns: standIns.length, boxes: allBoxes.length, fullTriangles: fullTris },
  boxesDrawn: () => allBoxes.filter(b => b.material.visible).length,
  copies: () => current ? current.copies.map(c => ({ model: c.p.model, key: c.p.key, floor: c.p.floor, what: c.what, level: c.lod ? c.lod.getCurrentLevel() : null })) : [],
  renderer, scene, THREE, templates, variants, placements, standIns, DATA,
};
