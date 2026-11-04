// ---------------------------------------------------------------------------
// Chair test: added to a copy of the bank page by make_chair_test.mjs (the page's own script is not changed).
// One real chair from the 3D team (Chair.glb, embedded) stands at every 'seat' piece instead of its box, drawn four ways
// (and a fifth as an extra check):
//   A  boxes, as now
//   B  the full chair, its 5 meshes copied for every seat (what a plain import does: 5 draw calls a seat)
//   C  the full chair, one InstancedMesh per part and level (5 draw calls a level, every chair drawn every frame)
//   D  the slimmed chair (made once in Node by slim_chair.mjs), one InstancedMesh a level
//   E  (an extra check) the slimmed chair as plain copies, one mesh a seat: D without the instancing
// The chair is put at the origin at load (chair_load.js). The export's 3 materials are black fallbacks, so every chair is drawn
// in one warm light grey (MeshStandardMaterial, roughness 0.8). Each chair stands where its box stands (centre, level, the box's
// turn) at its own real size; in B - E the seat boxes are not drawn but stay Walk's colliders, and the chairs follow the boxes'
// show tick, the floor buttons and the build replay. 'Turn chairs 90°' gives every chair a further quarter turn.
// Panel: seats replaced, chair triangles, the scene's triangles and draw calls (renderer.info), live frames a second, and Measure:
// 120 frames back to back, each finished on the GPU (a 1-pixel readPixels), giving ms a frame and fps, with the WebGL renderer.
// Address: ?chairs=A|B|C|D|E (start mode), ?turn=90|180|270. Test hook: window.__chairTest.
// ---------------------------------------------------------------------------
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { mergeVertices, toCreasedNormals } from 'three/addons/utils/BufferGeometryUtils.js';

const GLB_B64 = '__GLB_B64__';
const SLIM = __SLIM_JSON__;

__CHAIR_LOAD__

const host = window.__host, { FL, furniture, camera } = host;
const scene = Object.values(FL)[0].group.parent;
const UP = new THREE.Vector3(0, 1, 0), ONE = new THREE.Vector3(1, 1, 1), D2R = Math.PI / 180;
const num = n => Math.round(n).toLocaleString('en-US');
const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

// The page keeps its renderer to itself: the scene hands it over at its next render.
const renderer = await new Promise(resolve => {
  const own = scene.onBeforeRender;
  scene.onBeforeRender = function (r, ...rest) { scene.onBeforeRender = own; resolve(r); return own.call(this, r, ...rest); };
});
const gl = renderer.getContext();
const dbg = gl.getExtension('WEBGL_debug_renderer_info');
const GPU = String(dbg ? gl.getParameter(dbg.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER));

// ---------------------------------------------------------------- the chair, full and slimmed
const full = await loadFullChair();
const slimGeo = slimChairGeometry(40);
const SLIM_TRIS = slimGeo.index.count / 3;
const MAT = new THREE.MeshStandardMaterial({ color: 0xcdc5b8, roughness: 0.8, metalness: 0 });
MAT.name = 'chair test: neutral warm grey';

// ---------------------------------------------------------------- the seats
const seats = (furniture ? furniture.pieces() : []).filter(p => p.kind === 'seat')
  .map(p => ({ id: p.id, floor: p.floor, box: furniture.meshOf(p.id) })).filter(s => s.box && FL[s.floor]);
const floorKeys = Object.keys(FL).filter(k => seats.some(s => s.floor === k));
const seatsOn = Object.fromEntries(floorKeys.map(k => [k, seats.filter(s => s.floor === k)]));
const params = new URLSearchParams(location.search);
let turn = [90, 180, 270].includes(Number(params.get('turn'))) ? Number(params.get('turn')) : 0;
const MODES = ['A', 'B', 'C', 'D', 'E'];
let mode = 'A';

// One container per level and way of drawing (B - E); only the current way's containers are in the levels' groups.
const ways = { B: {}, C: {}, D: {}, E: {} };
for (const k of floorKeys) {
  const list = seatsOn[k];
  const b = new THREE.Group(); b.name = `chair test B ${k}`;
  for (const s of list) {
    s.group = new THREE.Group(); s.group.name = `chair ${s.id}`;
    for (const p of full.parts) {
      const m = new THREE.Mesh(p.geometry, MAT);
      m.name = `chair ${s.id} ${p.name}`;
      p.matrix.decompose(m.position, m.quaternion, m.scale);
      s.group.add(m);
    }
    b.add(s.group);
  }
  const c = new THREE.Group(); c.name = `chair test C ${k}`;
  for (const p of full.parts) {
    const im = new THREE.InstancedMesh(p.geometry, MAT, list.length);
    im.name = `chair test C ${k} ${p.name}`; im.userData.part = p;
    c.add(im);
  }
  const d = new THREE.Group(); d.name = `chair test D ${k}`;
  d.add(Object.assign(new THREE.InstancedMesh(slimGeo, MAT, list.length), { name: `chair test D ${k} slimmed` }));
  const e = new THREE.Group(); e.name = `chair test E ${k}`;
  for (const s of list) { s.slim = new THREE.Mesh(slimGeo, MAT); s.slim.name = `chair ${s.id} slimmed`; e.add(s.slim); }
  ways.B[k] = b; ways.C[k] = c; ways.D[k] = d; ways.E[k] = e;
}

// Every chair on its box: the box's centre and base, the box's own turn plus the extra turn.
const q = new THREE.Quaternion(), mSeat = new THREE.Matrix4(), mPart = new THREE.Matrix4();
function place() {
  for (const k of floorKeys) {
    seatsOn[k].forEach((s, i) => {
      q.setFromAxisAngle(UP, s.box.rotation.y + turn * D2R);
      mSeat.compose(s.box.position, q, ONE);
      s.group.position.copy(s.box.position); s.group.quaternion.copy(q);
      s.slim.position.copy(s.box.position); s.slim.quaternion.copy(q);
      for (const im of ways.C[k].children) im.setMatrixAt(i, mPart.multiplyMatrices(mSeat, im.userData.part.matrix));
      ways.D[k].children[0].setMatrixAt(i, mSeat);
    });
    for (const im of [...ways.C[k].children, ...ways.D[k].children]) { im.instanceMatrix.needsUpdate = true; im.computeBoundingSphere(); }
  }
}

// In B - E a seat box keeps its place in Walk's colliders and its label under the pointer, but is not drawn: it and its outline
// get a material that draws nothing (the build replay sets the boxes' visibility itself, so that is left alone).
const HIDDEN = new THREE.MeshBasicMaterial({ visible: false }), HIDDEN_LINE = new THREE.LineBasicMaterial({ visible: false });
const ownMaterial = new Map();
function setMode(m) {
  if (!MODES.includes(m)) return false;
  mode = m;
  for (const k of floorKeys) for (const w of ['B', 'C', 'D', 'E']) {
    const g = ways[w][k];
    if (w === m) { if (g.parent !== FL[k].group) FL[k].group.add(g); } else if (g.parent) g.parent.remove(g);
  }
  for (const s of seats) for (const o of [s.box, ...s.box.children]) {
    if (!ownMaterial.has(o)) ownMaterial.set(o, o.material);
    o.material = m === 'A' ? ownMaterial.get(o) : o.isLineSegments ? HIDDEN_LINE : HIDDEN;
  }
  ui.querySelectorAll('input[name=ct-mode]').forEach(r => { r.checked = r.value === m; });
  showCounts();
  return true;
}
function setTurn(deg) {
  turn = ((Math.round(deg / 90) * 90) % 360 + 360) % 360;
  place();
  ui.querySelector('.ct-turn').textContent = `Turn chairs 90° (now +${turn}°)`;
  return turn;
}

// ---------------------------------------------------------------- the panel
const css = document.createElement('style');
css.textContent = `
#ct-panel{position:fixed;right:12px;bottom:34px;width:min(318px,calc(100vw - 48px));max-height:calc(100vh - 60px);overflow:auto;box-sizing:border-box;background:var(--panel,#ffffffee);border:1px solid var(--line,#d5dade);border-radius:10px;padding:10px 13px;box-shadow:0 2px 10px #0001;z-index:5;font-size:12.5px;color:var(--ink,#1d2329)}
#ct-panel h2{font-size:14px;margin:0 0 3px}
#ct-panel .ct-sub{color:var(--muted,#5b6670);font-size:12px;margin:0 0 7px}
#ct-panel .ct-modes label{display:flex;align-items:flex-start;gap:7px;font-size:12.5px;margin:3px 0;cursor:pointer}
#ct-panel .ct-modes input{margin:2px 0 0}
#ct-panel .ct-modes b{display:inline-block;width:14px}
#ct-panel .ct-modes .ct-extra{color:var(--muted,#5b6670)}
#ct-panel .ct-row{display:flex;gap:6px;flex-wrap:wrap;margin:8px 0 6px}
#ct-panel dl{display:grid;grid-template-columns:auto 1fr;gap:1px 10px;margin:6px 0;font-variant-numeric:tabular-nums}
#ct-panel dt{color:var(--muted,#5b6670)}
#ct-panel dd{margin:0;text-align:right}
#ct-panel .ct-out{background:#f4f6f7;border:1px solid var(--line,#d5dade);border-radius:7px;padding:6px 8px;margin-top:6px;font-variant-numeric:tabular-nums;min-height:1.4em}
#ct-panel .ct-out b{font-size:13.5px}
#ct-panel .ct-gpu{color:var(--muted,#5b6670);font-size:11.5px;margin-top:6px;overflow-wrap:anywhere}
#ct-panel .ct-note{color:var(--muted,#5b6670);font-size:11.5px;margin-top:6px}
`;
document.head.appendChild(css);
const ui = document.createElement('div');
ui.id = 'ct-panel';
const perFloor = floorKeys.map(k => `${esc(FL[k].name || k)} ${seatsOn[k].length}`).join(' · ');
ui.innerHTML = `<h2>Chair test</h2>
<div class="ct-sub">One real chair (Chair.glb) at every 'seat' box: <b>${seats.length}</b> seats (${perFloor}).</div>
<div class="ct-modes">
  <label><input type="radio" name="ct-mode" value="A"><span><b>A</b> Boxes, as now</span></label>
  <label><input type="radio" name="ct-mode" value="B"><span><b>B</b> Full chair, its own meshes at every seat</span></label>
  <label><input type="radio" name="ct-mode" value="C"><span><b>C</b> Full chair, drawn once per part (instanced)</span></label>
  <label><input type="radio" name="ct-mode" value="D"><span><b>D</b> Slimmed chair, instanced</span></label>
  <label class="ct-extra"><input type="radio" name="ct-mode" value="E"><span><b>E</b> Slimmed chair, its own mesh at every seat (extra check: D without instancing)</span></label>
</div>
<div class="ct-row"><button class="ct-turn"></button></div>
<dl>
  <dt>Chair, full</dt><dd>${num(full.triangles)} triangles, ${full.parts.length} parts</dd>
  <dt>Chair, slimmed</dt><dd>${num(SLIM_TRIS)} triangles (${(SLIM_TRIS / full.triangles * 100).toFixed(1)} %)</dd>
  <dt>Seats replaced</dt><dd class="ct-seats"></dd>
  <dt>Chairs' triangles</dt><dd class="ct-chairs"></dd>
  <dt>Scene triangles</dt><dd class="ct-tris"></dd>
  <dt>Draw calls</dt><dd class="ct-calls"></dd>
  <dt>Frames a second</dt><dd class="ct-fps"></dd>
</dl>
<div class="ct-row"><button class="ct-measure">Measure (120 frames)</button></div>
<div class="ct-out">Press Measure: 120 frames drawn back to back, each one finished on the graphics chip.</div>
<div class="ct-gpu">Graphics: ${esc(GPU)}</div>
<div class="ct-note">The export's 3 materials are black 'fallback' materials (the real ones did not come across), so every chair is drawn in one neutral warm grey here. Size ${full.size.x.toFixed(2)} × ${full.size.z.toFixed(2)} m, ${full.size.y.toFixed(2)} m tall, as exported.</div>`;
document.body.appendChild(ui);
ui.querySelectorAll('input[name=ct-mode]').forEach(r => r.addEventListener('change', e => { setMode(e.target.value); e.target.blur(); }));
ui.querySelector('.ct-turn').onclick = e => { setTurn(turn + 90); e.currentTarget.blur(); };
const out = ui.querySelector('.ct-out');

const slimMode = () => mode === 'D' || mode === 'E';
const chairTris = () => mode === 'A' ? 0 : seats.length * (slimMode() ? SLIM_TRIS : full.triangles);
function showCounts() {
  ui.querySelector('.ct-seats').textContent = mode === 'A' ? `none (boxes; ${seats.length} in B - E)` : `${seats.length} of ${seats.length}`;
  ui.querySelector('.ct-chairs').textContent = mode === 'A' ? '0' : `${num(chairTris())} (${seats.length} × ${num(slimMode() ? SLIM_TRIS : full.triangles)})`;
}
let fps = 0;
function showLive() {
  const r = renderer.info.render;
  ui.querySelector('.ct-tris').textContent = num(r.triangles);
  ui.querySelector('.ct-calls').textContent = num(r.calls);
  ui.querySelector('.ct-fps').textContent = fps ? fps.toFixed(0) + ' (live)' : '…';
}

// ---------------------------------------------------------------- Measure: 120 frames, each finished before the next
let last = null;
function measure(frames = 120) {
  const px = new Uint8Array(4);
  const draw = () => { renderer.render(scene, camera); gl.readPixels(0, 0, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, px); };
  for (let i = 0; i < 5; i++) draw();                                         // warm-up: programs compiled, buffers on the chip
  const { calls, triangles } = renderer.info.render;
  const t0 = performance.now();
  for (let i = 0; i < frames; i++) draw();
  const ms = (performance.now() - t0) / frames, size = renderer.getDrawingBufferSize(new THREE.Vector2());
  last = { mode, turn, frames, ms: Math.round(ms * 100) / 100, fps: Math.round(10000 / ms) / 10, triangles, calls, gpu: GPU,
    width: size.x, height: size.y, view: window.__viewer ? window.__viewer.mode : 'orbit', at: new Date().toISOString() };
  out.innerHTML = `<b>${last.ms.toFixed(1)} ms a frame = ${last.fps.toFixed(0)} fps</b><br>mode ${mode}, ${num(triangles)} triangles, ${num(calls)} draw calls, ${size.x} × ${size.y} px`;
  return last;
}
ui.querySelector('.ct-measure').onclick = e => {
  e.currentTarget.blur();
  out.textContent = 'Measuring…';
  setTimeout(() => measure(120), 40);                                         // let the 'Measuring' text show first
};

// ---------------------------------------------------------------- every frame: follow the boxes and the replay, count frames
let frames = 0, since = performance.now(), shown = 0;
function tick(now) {
  frames++;
  if (now - since >= 1000) { fps = frames * 1000 / (now - since); frames = 0; since = now; }
  const done = !window.__build || window.__build.phase === 'done';
  for (const k of floorKeys) {
    const on = done && seatsOn[k].some(s => s.box.visible);                   // the seat kind's show tick (Chair / stool)
    ways.B[k].visible = ways.C[k].visible = ways.D[k].visible = ways.E[k].visible = on;
  }
  if (now - shown > 250) { shown = now; showLive(); }
  requestAnimationFrame(tick);
}

place();
setTurn(turn);
setMode(MODES.includes(params.get('chairs')) ? params.get('chairs') : 'A');
requestAnimationFrame(tick);
window.__chairTest = {
  ready: true, setMode, setTurn, measure, get mode() { return mode; }, get turn() { return turn; }, get last() { return last; },
  gpu: GPU, seats: seats.length, perFloor: Object.fromEntries(floorKeys.map(k => [k, seatsOn[k].length])),
  fullTriangles: full.triangles, fullVertices: full.vertices, slimTriangles: SLIM_TRIS, slimVertices: slimGeo.attributes.position.count,
  chairSize: full.size.toArray(), undone: full.undone, attributes: full.attributes, exportMaterials: full.materials,
  live: () => ({ fps, triangles: renderer.info.render.triangles, calls: renderer.info.render.calls, chairTriangles: chairTris() }),
  renderer, scene, THREE, parts: full.parts, slimGeo, material: MAT, ways, seatsOn, floorKeys, FL,      // for checks beyond A - D
};
