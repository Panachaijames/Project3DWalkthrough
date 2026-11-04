// Slims the 3D team's 8 bank models ONCE, to fixed budgets per piece, for bank_furnished.html (modes C, D, E):
//   node slim_models.mjs            (run after make_placements.mjs; nothing is installed: three 0.186.1 is read from ../../app/node_modules)
// For each model (banquet/*.glb, read only) and each budget of 20,000 / 10,000 / 5,000 / 2,500 triangles that it is over:
//   1. normalised as placements.json says (the GLB scene taken into its piece's block frame), every part baked into that frame
//      (metres, three.js axes; a mirrored part gets its triangles turned round)
//   2. the budget shared out between the model's parts by their triangles (parts of 24 triangles or less, and parts whose share
//      is more than they have, are kept whole); each part welded by position (0.1 mm: its normals dropped, so hard edges do not
//      split it), slimmed with three's SimplifyModifier (meshoptimizer), its normals worked out again (smooth across edges flatter
//      than 40 degrees, sharp across the others; in mm, as the chair test did) and indexed again
//   3. written as a GLB (positions, normals, 16- or 32-bit indices; one mesh and one material per part, in the full model's
//      part order, already normalised) to slim/<model>@<budget>.glb
// Also Chair.glb (the chair test's chair, read only), put at the origin as the chair test did, for the projection to all 185
// pieces. Writes slim/slim_report.json: per model and budget the triangles, vertices, bytes (and gzipped), per part, and ms.
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { gzipSync } from 'node:zlib';
import { createHash } from 'node:crypto';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const PROJECT = path.resolve(HERE, '..', '..');
const THREE_DIR = path.join(PROJECT, 'app', 'node_modules', 'three');
const imp = rel => import(pathToFileURL(path.join(THREE_DIR, rel)).href);
const THREE = await imp('build/three.module.js');
const { GLTFLoader } = await imp('examples/jsm/loaders/GLTFLoader.js');
const { SimplifyModifier } = await imp('examples/jsm/modifiers/SimplifyModifier.js');
const { mergeVertices, toCreasedNormals } = await imp('examples/jsm/utils/BufferGeometryUtils.js');
const threeVersion = JSON.parse(readFileSync(path.join(THREE_DIR, 'package.json'), 'utf8')).version;
const BUDGETS = (process.env.BUDGETS || '20000,10000,5000,2500').split(',').map(Number);
const KEEP_WHOLE = 24, MIN_PART = 12, WELD_M = 1e-4, CREASE_DEG = 40;
const OUT = path.join(HERE, 'slim');
mkdirSync(OUT, { recursive: true });
const pl = JSON.parse(readFileSync(path.join(HERE, 'placements.json'), 'utf8'));
const rowMajor = m => new THREE.Matrix4().set(...m.flat());

// ---------------------------------------------------------------- a model's parts, baked into its normalised frame
async function bakedParts(file, normalise) {
  const buf = readFileSync(file);
  const gltf = await new GLTFLoader().parseAsync(buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength), '');
  const root = gltf.scene;
  normalise(root);
  root.updateMatrixWorld(true);
  const parts = [];
  root.traverse(o => {
    if (!o.isMesh) return;
    const src = o.geometry, n = src.attributes.position.count;
    const pos = new Float32Array(n * 3), nor = new Float32Array(n * 3), v = new THREE.Vector3();
    const nm = new THREE.Matrix3().getNormalMatrix(o.matrixWorld);
    for (let i = 0; i < n; i++) {
      v.fromBufferAttribute(src.attributes.position, i).applyMatrix4(o.matrixWorld); pos.set([v.x, v.y, v.z], i * 3);
      v.fromBufferAttribute(src.attributes.normal, i).applyMatrix3(nm).normalize(); nor.set([v.x, v.y, v.z], i * 3);
    }
    let idx = src.index ? Uint32Array.from(src.index.array) : Uint32Array.from({ length: n }, (_, i) => i);
    const mirrored = o.matrixWorld.determinant() < 0;
    if (mirrored) for (let t = 0; t < idx.length; t += 3) { const a = idx[t + 1]; idx[t + 1] = idx[t + 2]; idx[t + 2] = a; }
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    g.setAttribute('normal', new THREE.BufferAttribute(nor, 3));
    g.setIndex(new THREE.BufferAttribute(idx, 1));
    parts.push({ name: o.name, geometry: g, triangles: idx.length / 3, mirrored });
  });
  return { parts, bytes: buf.length, sha1: createHash('sha1').update(buf).digest('hex').slice(0, 12) };
}

// the budget shared out by triangles; small parts and parts under their share kept whole
function shareOut(parts, budget) {
  const target = parts.map(() => null);
  let left = budget;
  for (;;) {
    const open = parts.map((p, i) => i).filter(i => target[i] === null);
    const openTris = open.reduce((a, i) => a + parts[i].triangles, 0);
    let changed = false;
    for (const i of open) {
      const share = left * parts[i].triangles / openTris;
      if (parts[i].triangles <= KEEP_WHOLE || share >= parts[i].triangles) { target[i] = parts[i].triangles; left -= parts[i].triangles; changed = true; }
    }
    if (!changed) { for (const i of open) target[i] = Math.max(MIN_PART, Math.floor(left * parts[i].triangles / openTris)); return target; }
  }
}

// one part slimmed to about `want` triangles: welded by position, SimplifyModifier, creased normals, indexed again
async function slimPart(geometry, want) {
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', geometry.attributes.position);
  g.setIndex(geometry.index);
  const welded = mergeVertices(g, WELD_M);
  const V = welded.attributes.position.count, T = welded.index.count / 3;
  const slim = await new SimplifyModifier().modify(welded, Math.max(0, Math.round(V * (1 - want / T))));
  slim.scale(1000, 1000, 1000);
  const creased = toCreasedNormals(slim, CREASE_DEG * Math.PI / 180);
  creased.scale(0.001, 0.001, 0.001);
  const out = mergeVertices(creased);
  return out;
}

// ---------------------------------------------------------------- GLB writer: positions, normals, indices; a mesh and a material a part
function glb(parts, generator) {
  const views = [], accessors = [], meshes = [], nodes = [], chunks = [];
  let offset = 0;
  const add = (typed, target) => {
    views.push({ buffer: 0, byteOffset: offset, byteLength: typed.byteLength, target });
    chunks.push(Buffer.from(typed.buffer, typed.byteOffset, typed.byteLength));
    offset += typed.byteLength;
    const pad = (4 - offset % 4) % 4; if (pad) { chunks.push(Buffer.alloc(pad)); offset += pad; }
    return views.length - 1;
  };
  parts.forEach((p, i) => {
    const P = p.geometry.attributes.position, N = p.geometry.attributes.normal, I = p.geometry.index;
    const pos = Float32Array.from(P.array), nor = Float32Array.from(N.array);
    const idx = P.count <= 65535 ? Uint16Array.from(I.array) : Uint32Array.from(I.array);
    const min = [Infinity, Infinity, Infinity], max = [-Infinity, -Infinity, -Infinity];
    for (let k = 0; k < pos.length; k += 3) for (let c = 0; c < 3; c++) { min[c] = Math.min(min[c], pos[k + c]); max[c] = Math.max(max[c], pos[k + c]); }
    const a = accessors.length;
    accessors.push({ bufferView: add(pos, 34962), componentType: 5126, count: P.count, type: 'VEC3', min, max });
    accessors.push({ bufferView: add(nor, 34962), componentType: 5126, count: P.count, type: 'VEC3' });
    accessors.push({ bufferView: add(idx, 34963), componentType: idx instanceof Uint16Array ? 5123 : 5125, count: idx.length, type: 'SCALAR' });
    meshes.push({ name: p.name, primitives: [{ attributes: { POSITION: a, NORMAL: a + 1 }, indices: a + 2, material: i, mode: 4 }] });
    nodes.push({ name: p.name, mesh: i });
  });
  const json = { asset: { version: '2.0', generator }, scene: 0, scenes: [{ nodes: nodes.map((_, i) => i) }], nodes, meshes,
    materials: parts.map((p, i) => ({ name: `part ${i}`, pbrMetallicRoughness: { baseColorFactor: [0.8, 0.8, 0.8, 1], metallicFactor: 0, roughnessFactor: 0.8 } })),
    accessors, bufferViews: views, buffers: [{ byteLength: offset }] };
  let js = Buffer.from(JSON.stringify(json), 'utf8');
  js = Buffer.concat([js, Buffer.alloc((4 - js.length % 4) % 4, 0x20)]);
  const bin = Buffer.concat(chunks);
  const head = Buffer.alloc(12), jh = Buffer.alloc(8), bh = Buffer.alloc(8);
  head.writeUInt32LE(0x46546c67, 0); head.writeUInt32LE(2, 4); head.writeUInt32LE(12 + 8 + js.length + 8 + bin.length, 8);
  jh.writeUInt32LE(js.length, 0); jh.writeUInt32LE(0x4e4f534a, 4);
  bh.writeUInt32LE(bin.length, 0); bh.writeUInt32LE(0x004e4942, 4);
  return Buffer.concat([head, jh, js, bh, bin]);
}

// ---------------------------------------------------------------- the models
const models = Object.entries(pl.models).map(([name, m]) => ({
  name, file: path.join(PROJECT, m.file), triangles: m.triangles,
  normalise: root => { const N = rowMajor(m.normalise); root.matrixAutoUpdate = false; root.matrix.copy(N); },
}));
// Chair.glb as the chair test put it at the origin: each root's turn about the vertical and position undone, footprint centred, base at 0
models.push({
  name: 'Chair', file: path.join(PROJECT, 'Chair.glb'), triangles: 41921, projectionOnly: true,
  normalise: root => {
    const UP = new THREE.Vector3(0, 1, 0);
    for (const node of root.children) {
      const ex = new THREE.Vector3(1, 0, 0).applyQuaternion(node.quaternion);
      node.quaternion.premultiply(new THREE.Quaternion().setFromAxisAngle(UP, -Math.atan2(-ex.z, ex.x)));
      node.position.set(0, 0, 0);
    }
    root.updateMatrixWorld(true);
    const bb = new THREE.Box3().setFromObject(root, true);
    root.position.set(-(bb.min.x + bb.max.x) / 2, -bb.min.y, -(bb.min.z + bb.max.z) / 2);
  },
});

const report = { made: new Date().toISOString(), three: threeVersion, budgets: BUDGETS,
  method: `per part: welded by position at ${WELD_M * 1000} mm, SimplifyModifier (three ${threeVersion}, meshoptimizer), normals creased at ${CREASE_DEG} degrees; the budget shared out by triangles (parts of ${KEEP_WHOLE} triangles or less kept whole)`,
  models: {} };
for (const M of models) {
  const { parts, bytes, sha1 } = await bakedParts(M.file, M.normalise);
  const full = parts.reduce((a, p) => a + p.triangles, 0);
  if (full !== M.triangles) throw new Error(`${M.name}: ${full} triangles, expected ${M.triangles}`);
  const fileBytes = readFileSync(M.file);
  const entry = { file: path.relative(PROJECT, M.file).replace(/\\/g, '/'), sha1, triangles: full, bytes, gzipBytes: gzipSync(fileBytes).length,
    vertices: parts.reduce((a, p) => a + p.geometry.attributes.position.count, 0), parts: parts.map(p => ({ name: p.name, triangles: p.triangles, mirrored: p.mirrored })),
    projectionOnly: !!M.projectionOnly, budgets: {} };
  for (const B of BUDGETS) {
    if (full <= B) { entry.budgets[B] = { kept: true, triangles: full }; continue; }
    const t0 = performance.now();
    let target = shareOut(parts, B), made = [];
    for (let round = 0; round < 4; round++) {
      made = [];
      for (let i = 0; i < parts.length; i++) {
        if (target[i] >= parts[i].triangles) { made.push(parts[i].geometry); continue; }
        made.push(await slimPart(parts[i].geometry, target[i]));
      }
      const got = made.map(g => g.index.count / 3), total = got.reduce((a, b) => a + b, 0);
      if (total <= B * 1.01) break;
      // over budget (a part could not go as low as asked): ask the slimmed parts for proportionally less
      const fixed = got.reduce((a, g, i) => a + (target[i] >= parts[i].triangles ? g : 0), 0), slimmed = total - fixed;
      target = target.map((t, i) => t >= parts[i].triangles ? t : Math.max(MIN_PART, Math.floor(t * (B - fixed) / slimmed)));
    }
    const ms = performance.now() - t0;
    const outParts = parts.map((p, i) => ({ name: p.name, geometry: made[i] }));
    const data = glb(outParts, `furniture_test/bank_furnished/slim_models.mjs: ${M.name} slimmed to ${B} triangles (three ${threeVersion} SimplifyModifier)`);
    const fname = `${M.name}@${B}.glb`;
    writeFileSync(path.join(OUT, fname), data);
    const tris = made.map(g => g.index.count / 3);
    entry.budgets[B] = { kept: false, file: 'slim/' + fname, triangles: tris.reduce((a, b) => a + b, 0), vertices: made.reduce((a, g) => a + g.attributes.position.count, 0),
      bytes: data.length, gzipBytes: gzipSync(data).length, share: +(tris.reduce((a, b) => a + b, 0) / full * 100).toFixed(2), ms: Math.round(ms),
      parts: parts.map((p, i) => ({ name: p.name, from: p.triangles, asked: target[i], got: tris[i] })) };
    console.log(`${M.name} @${B}: ${entry.budgets[B].triangles} triangles (${entry.budgets[B].share} %), ${entry.budgets[B].vertices} vertices, ${Math.round(data.length / 1024)} KB, ${Math.round(ms)} ms; parts ${tris.join(' + ')}`);
  }
  report.models[M.name] = entry;
}
writeFileSync(path.join(OUT, 'slim_report.json'), JSON.stringify(report, null, 1));
console.log('slim/slim_report.json written');
