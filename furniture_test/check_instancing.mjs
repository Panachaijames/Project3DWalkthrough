// Why mode C (the full chair, instanced) is slow on the Intel chip: the orbit view (or Walk with VIEW=walk) drawn more ways
// than the panel offers, in headless Edge on the real graphics chip, each timed with the page's own Measure (3 x 120 frames).
//   node check_instancing.mjs     (another chip: LUID=<its adapter LUID from edge://gpu>, e.g. LUID=0,61888 for the NVIDIA one)
//   A - E   the panel's ways
//   B2, C2  B and C with the export's packed vertex data (position + normal + 8 spare bytes per vertex) unpacked
//   G, F    the chair's 5 parts merged into one geometry: a copy at every seat (G) or instanced (F)
// Besides Measure it prints two other timings: 'queued' (60 frames sent without waiting, then one wait: the chip's own pace,
// as in normal use) and 'js' (the JavaScript part of a frame alone). Port 9761; holds the one-Edge-at-a-time lock.
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { launch, sleep } from './browser.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const page = pathToFileURL(path.join(HERE, 'chair_test.html')).href;
const VIEW = process.env.VIEW || 'orbit';
const url = VIEW === 'walk' ? page + '?build=0&mode=walk&floor=L1&x=0&z=5.2&yaw=-26.6&pitch=-8' : page + '?build=0';
const WAYS = (process.env.WAYS || 'A,B,B2,G,C,C2,F,D,E').split(',');
const extra = process.env.LUID ? [`--use-adapter-luid=${process.env.LUID}`] : [];

// Pasted into the page: builds the extra ways from the chair test's own parts (window.__chairTest).
const PAGE_CODE = String.raw`window.__ways = (() => {
  const T = __chairTest, THREE = T.THREE, MAT = T.material, PAGE = ['A', 'B', 'C', 'D', 'E'];
  const unpack = g => {
    const n = new THREE.BufferGeometry();
    for (const [k, a] of Object.entries(g.attributes)) {
      const arr = new Float32Array(a.count * 3);
      for (let i = 0; i < a.count; i++) { arr[i * 3] = a.getX(i); arr[i * 3 + 1] = a.getY(i); arr[i * 3 + 2] = a.getZ(i); }
      n.setAttribute(k, new THREE.BufferAttribute(arr, 3));
    }
    n.setIndex(new THREE.BufferAttribute(g.index.array.slice(), 1)); n.computeBoundingSphere(); return n;
  };
  const parts = T.parts.map(p => ({ ...p, geometry: unpack(p.geometry) }));
  const merged = (() => {
    let nv = 0, ni = 0; for (const p of parts) { nv += p.geometry.attributes.position.count; ni += p.geometry.index.count; }
    const pos = new Float32Array(nv * 3), nor = new Float32Array(nv * 3), idx = new Uint32Array(ni);
    let vo = 0, io = 0; const v = new THREE.Vector3(), nm = new THREE.Matrix3();
    for (const p of parts) {
      nm.getNormalMatrix(p.matrix); const P = p.geometry.attributes.position, N = p.geometry.attributes.normal, first = vo;
      for (let i = 0; i < P.count; i++) { v.fromBufferAttribute(P, i).applyMatrix4(p.matrix); pos.set([v.x, v.y, v.z], vo * 3); v.fromBufferAttribute(N, i).applyMatrix3(nm).normalize(); nor.set([v.x, v.y, v.z], vo * 3); vo++; }
      for (const i of p.geometry.index.array) idx[io++] = first + i;
    }
    const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.BufferAttribute(pos, 3)); g.setAttribute('normal', new THREE.BufferAttribute(nor, 3)); g.setIndex(new THREE.BufferAttribute(idx, 1)); g.computeBoundingSphere(); return g;
  })();
  const seatMatrix = s => { s.group.updateMatrix(); return s.group.matrix; };
  const build = {
    B2: k => { const c = new THREE.Group(); for (const s of T.seatsOn[k]) { const g = new THREE.Group(); s.group.matrix.decompose(g.position, g.quaternion, g.scale); for (const p of parts) { const m = new THREE.Mesh(p.geometry, MAT); p.matrix.decompose(m.position, m.quaternion, m.scale); g.add(m); } c.add(g); } return c; },
    C2: k => { const c = new THREE.Group(), list = T.seatsOn[k]; for (const p of parts) { const im = new THREE.InstancedMesh(p.geometry, MAT, list.length); list.forEach((s, i) => im.setMatrixAt(i, new THREE.Matrix4().multiplyMatrices(seatMatrix(s), p.matrix))); im.computeBoundingSphere(); c.add(im); } return c; },
    F: k => { const list = T.seatsOn[k], im = new THREE.InstancedMesh(merged, MAT, list.length); list.forEach((s, i) => im.setMatrixAt(i, seatMatrix(s))); im.computeBoundingSphere(); const c = new THREE.Group(); c.add(im); return c; },
    G: k => { const c = new THREE.Group(); for (const s of T.seatsOn[k]) { const m = new THREE.Mesh(merged, MAT); s.group.matrix.decompose(m.position, m.quaternion, m.scale); c.add(m); } return c; },
  };
  const made = {};
  function use(name) {
    for (const k of T.floorKeys) for (const v of Object.values(made)) if (v[k].parent) v[k].parent.remove(v[k]);
    if (PAGE.includes(name)) { T.setMode(name); return name; }
    T.setMode('B');                                               // seat boxes hidden, then the page's own chairs taken out
    for (const k of T.floorKeys) for (const w of ['B', 'C', 'D', 'E']) { const g = T.ways[w][k]; if (g.parent) g.parent.remove(g); }
    if (!made[name]) { made[name] = {}; for (const k of T.floorKeys) made[name][k] = build[name](k); }
    for (const k of T.floorKeys) T.FL[k].group.add(made[name][k]);
    return name;
  }
  const gl = T.renderer.getContext(), px = new Uint8Array(4), draw = () => T.renderer.render(T.scene, __host.camera);
  function queued(n = 60) {
    draw(); gl.readPixels(0, 0, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, px);
    const t0 = performance.now();
    for (let i = 0; i < n; i++) draw();
    const t1 = performance.now();
    gl.readPixels(0, 0, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, px);
    return { js: +((t1 - t0) / n).toFixed(2), queued: +((performance.now() - t0) / n).toFixed(2) };
  }
  return { use, queued };
})(); true;`;

const b = await launch({ port: Number(process.env.PORT || 9761), profile: path.join(os.tmpdir(), 'chair-test', 'profile-check'), extra, step: 'furniture_test instancing check' });
try {
  await b.goto(url, '!!(window.__chairTest && window.__chairTest.ready)');
  await sleep(2000);
  await b.evaluate(PAGE_CODE);
  console.log(`${VIEW} view, ${await b.evaluate('__chairTest.gpu')}`);
  for (const w of WAYS) {
    await b.evaluate(`__ways.use('${w}')`);
    await sleep(1200);
    const ms = [];
    for (let i = 0; i < 3; i++) ms.push((await b.evaluate('__chairTest.measure(120)')).ms);
    const q = await b.evaluate('__ways.queued(60)'), live = await b.evaluate('__chairTest.live()');
    console.log(`${w.padEnd(3)} Measure ${ms.map(x => x.toFixed(1)).join(' / ')} ms | queued ${q.queued} ms | js ${q.js} ms | ${live.triangles.toLocaleString('en-US')} triangles, ${live.calls} draw calls`);
  }
  const errors = b.logs.filter(l => /exception|error/i.test(l));
  if (errors.length) console.log('page errors:\n' + errors.join('\n'));
} finally { await b.close(); }
