// Makes the slimmed chair ONCE, for chair_test.html (mode D).
//   node slim_chair.mjs            (run from this folder; nothing is installed: three 0.186.1 is read from ../app/node_modules)
// Reads ../Chair.glb (glTF 2.0 binary, parsed here by hand: 5 meshes, POSITION + NORMAL, 32-bit indices), puts the chair
// where the page puts it (the export's scene turn about the vertical and its position undone, the Z-up -> Y-up turn and the
// 0.38 scale kept, footprint centred on the origin, base at y = 0, metres), welds the five parts into one geometry by position
// (normals dropped: the page works them out again), slims it with three's SimplifyModifier (meshoptimizer inside) to about
// 12 % of the triangles, and writes chair_slim.json: positions (Float32) and indices (Uint16 when the vertices fit, else
// Uint32), base64, with the numbers the README quotes.
import { createHash } from 'node:crypto';
import { readFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const PROJECT = path.resolve(HERE, '..');
const GLB = path.join(PROJECT, 'Chair.glb');
const OUT = path.join(HERE, 'chair_slim.json');
const THREE_DIR = path.join(PROJECT, 'app', 'node_modules', 'three');
const imp = rel => import(pathToFileURL(path.join(THREE_DIR, rel)).href);
const THREE = await imp('build/three.module.js');
const { SimplifyModifier } = await imp('examples/jsm/modifiers/SimplifyModifier.js');
const { mergeVertices } = await imp('examples/jsm/utils/BufferGeometryUtils.js');
const threeVersion = JSON.parse(readFileSync(path.join(THREE_DIR, 'package.json'), 'utf8')).version;
const TARGET = Number(process.env.TARGET_RATIO || 0.12);          // share of the triangles to keep

// ---------------------------------------------------------------- the GLB, by hand
const buf = readFileSync(GLB);
if (buf.readUInt32LE(0) !== 0x46546c67) throw new Error('not a GLB file');
const jsonLen = buf.readUInt32LE(12);
const gltf = JSON.parse(buf.subarray(20, 20 + jsonLen).toString('utf8'));
const binStart = 20 + jsonLen + 8;                                // the BIN chunk's data
const COMPONENTS = { SCALAR: 1, VEC2: 2, VEC3: 3, VEC4: 4 };
const ARRAYS = { 5121: Uint8Array, 5123: Uint16Array, 5125: Uint32Array, 5126: Float32Array };
function accessor(i) {                                            // a tightly packed copy of an accessor
  const a = gltf.accessors[i], bv = gltf.bufferViews[a.bufferView], Arr = ARRAYS[a.componentType], n = COMPONENTS[a.type];
  const stride = bv.byteStride || n * Arr.BYTES_PER_ELEMENT, base = binStart + (bv.byteOffset || 0) + (a.byteOffset || 0);
  const out = new Arr(a.count * n), view = new DataView(buf.buffer, buf.byteOffset);
  const read = { 5121: o => view.getUint8(o), 5123: o => view.getUint16(o, true), 5125: o => view.getUint32(o, true), 5126: o => view.getFloat32(o, true) }[a.componentType];
  for (let k = 0; k < a.count; k++) for (let c = 0; c < n; c++) out[k * n + c] = read(base + k * stride + c * Arr.BYTES_PER_ELEMENT);
  return out;
}
const matrixOf = node => node.matrix ? new THREE.Matrix4().fromArray(node.matrix)
  : new THREE.Matrix4().compose(new THREE.Vector3(...(node.translation || [0, 0, 0])), new THREE.Quaternion(...(node.rotation || [0, 0, 0, 1])), new THREE.Vector3(...(node.scale || [1, 1, 1])));

// The export's placement, read from a root node: the turn about the vertical (yaw) that the chair had in its Max scene, and its
// position. Undoing both keeps the rest of the root's matrix: the Z-up -> Y-up turn and the uniform scale.
const UP = new THREE.Vector3(0, 1, 0);
function normalisedRoot(m) {
  const pos = new THREE.Vector3(), q = new THREE.Quaternion(), sc = new THREE.Vector3();
  m.decompose(pos, q, sc);
  const ex = new THREE.Vector3(1, 0, 0).applyQuaternion(q);       // the model's own x axis, in the world: level after Z-up -> Y-up
  const yaw = Math.atan2(-ex.z, ex.x);
  const qn = new THREE.Quaternion().setFromAxisAngle(UP, -yaw).multiply(q);
  return { matrix: new THREE.Matrix4().compose(new THREE.Vector3(), qn, sc), yawDeg: yaw * 180 / Math.PI, position: pos.toArray(), scale: sc.toArray() };
}

// Every mesh under the scene's roots, with its matrix in the normalised chair (before centring).
const parts = [];
let fullTriangles = 0, fullVertices = 0;
const placement = [];
const scene = gltf.scenes[gltf.scene || 0];
function walk(nodeIndex, parentMatrix, ownMatrix) {                 // ownMatrix: a root's normalised matrix
  const node = gltf.nodes[nodeIndex];
  const m = parentMatrix.clone().multiply(ownMatrix || matrixOf(node));
  if (node.mesh !== undefined) for (const prim of gltf.meshes[node.mesh].primitives) {
    if ((prim.mode ?? 4) !== 4) throw new Error('only triangle lists are handled');
    const pos = accessor(prim.attributes.POSITION), idx = prim.indices !== undefined ? accessor(prim.indices) : null;
    const tris = (idx ? idx.length : pos.length / 3) / 3;
    fullTriangles += tris; fullVertices += pos.length / 3;
    parts.push({ name: gltf.meshes[node.mesh].name || node.name || `mesh ${node.mesh}`, matrix: m, pos, idx, tris, material: prim.material });
  }
  for (const c of node.children || []) walk(c, m);
}
for (const r of scene.nodes) {
  const n = normalisedRoot(matrixOf(gltf.nodes[r]));
  placement.push({ node: r, yawDeg: n.yawDeg, position: n.position, scale: n.scale });
  walk(r, new THREE.Matrix4(), n.matrix);
}

// ---------------------------------------------------------------- one geometry, centred (footprint on the origin, base at 0)
const positions = new Float32Array(fullVertices * 3), indices = new Uint32Array(fullTriangles * 3);
const v = new THREE.Vector3();
let vo = 0, io = 0;
for (const p of parts) {
  const first = vo / 3;
  for (let k = 0; k < p.pos.length; k += 3) {
    v.set(p.pos[k], p.pos[k + 1], p.pos[k + 2]).applyMatrix4(p.matrix);
    positions[vo++] = v.x; positions[vo++] = v.y; positions[vo++] = v.z;
  }
  if (p.idx) for (const i of p.idx) indices[io++] = first + i;
  else for (let k = 0; k < p.pos.length / 3; k++) indices[io++] = first + k;
}
const box = new THREE.Box3().setFromArray(positions);
const centre = [(box.min.x + box.max.x) / 2, box.min.y, (box.min.z + box.max.z) / 2];
for (let k = 0; k < positions.length; k += 3) { positions[k] -= centre[0]; positions[k + 1] -= centre[1]; positions[k + 2] -= centre[2]; }
const full = new THREE.BufferGeometry();
full.setAttribute('position', new THREE.BufferAttribute(positions, 3));
full.setIndex(new THREE.BufferAttribute(indices, 1));
full.computeBoundingBox();
const size = full.boundingBox.getSize(new THREE.Vector3());

// Welded by position (0.1 mm): the parts' hard edges split their vertices, and the slimmer can only fold across a weld.
const welded = mergeVertices(full, 1e-4);
const weldedVertices = welded.getAttribute('position').count;

// ---------------------------------------------------------------- slimmed, once
const t0 = performance.now();
const removeCount = Math.round(weldedVertices * (1 - TARGET));    // SimplifyModifier takes the number of vertices to remove
const slim = await new SimplifyModifier().modify(welded, removeCount);
const ms = performance.now() - t0;
const sPos = slim.getAttribute('position').array, sIdxRaw = slim.getIndex().array;
const sVerts = sPos.length / 3, sTris = sIdxRaw.length / 3;
const sIdx = sVerts <= 65535 ? Uint16Array.from(sIdxRaw) : Uint32Array.from(sIdxRaw);
slim.computeBoundingBox();
const sSize = slim.boundingBox.getSize(new THREE.Vector3());
const b64 = a => Buffer.from(a.buffer, a.byteOffset, a.byteLength).toString('base64');
const r4 = x => Math.round(x * 1e4) / 1e4;
const out = {
  source: { file: 'Chair.glb', bytes: buf.length, sha1: createHash('sha1').update(buf).digest('hex').slice(0, 12) },
  made: new Date().toISOString(), three: threeVersion, method: `SimplifyModifier (three ${threeVersion}, meshoptimizer), welded by position at 0.1 mm, target ${TARGET * 100} % of the triangles`,
  placementUndone: placement.map(p => ({ node: p.node, yawDeg: Math.round(p.yawDeg * 100) / 100, position: p.position.map(r4), scale: p.scale.map(r4) })),
  centre: centre.map(r4),
  full: { triangles: fullTriangles, vertices: fullVertices, weldedVertices, parts: parts.map(p => ({ name: p.name, triangles: p.tris, material: p.material })), size: size.toArray().map(r4) },
  slim: {
    triangles: sTris, vertices: sVerts, share: Math.round(sTris / fullTriangles * 1000) / 10, ms: Math.round(ms),
    size: sSize.toArray().map(r4), indexType: sIdx instanceof Uint16Array ? 'uint16' : 'uint32',
    bytes: sPos.byteLength + sIdx.byteLength,
    positions: b64(Float32Array.from(sPos)), indices: b64(sIdx),
  },
};
writeFileSync(OUT, JSON.stringify(out));
console.log(JSON.stringify({ ...out, slim: { ...out.slim, positions: `<${out.slim.positions.length} chars>`, indices: `<${out.slim.indices.length} chars>` } }, null, 1));
