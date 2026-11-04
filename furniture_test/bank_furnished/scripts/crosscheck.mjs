// Cross-check of the Python reading with three.js 0.186.1's own GLTFLoader (read from ../app/node_modules, nothing installed):
// per model the triangles, vertices, attributes and the scene's world box (y up), and the box / block matrices of the analysis
// put back at the model's own piece (they must give the model where it was exported, shifted by the bank's offset).
//   node crosscheck.mjs <project folder> <analysis json>
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const [PROJECT, ANALYSIS] = process.argv.slice(2);
const THREE_DIR = path.join(PROJECT, 'app', 'node_modules', 'three');
const imp = rel => import(pathToFileURL(path.join(THREE_DIR, rel)).href);
const THREE = await imp('build/three.module.js');
const { GLTFLoader } = await imp('examples/jsm/loaders/GLTFLoader.js');
const version = JSON.parse(readFileSync(path.join(THREE_DIR, 'package.json'), 'utf8')).version;
const A = JSON.parse(readFileSync(ANALYSIS, 'utf8'));
const bank = JSON.parse(readFileSync(path.join(PROJECT, 'bank_test', 'src', 'bank_model.json'), 'utf8'));
const level = Object.fromEntries(bank.floors.map(f => [f.key, f.level]));
const byId = Object.fromEntries(bank.furniture.map(p => [p.id, p]));
const csv = readFileSync(path.join(PROJECT, 'bank_test', 'bank_furniture_list.csv'), 'utf8').replace(/^﻿/, '').split(/\r?\n/).filter(Boolean);
const head = csv[0].split(',');
const baseMm = {};
// base_mm by its column name, from rows whose family / block may hold commas inside quotes
function parseRow(s) { const out = []; let cur = '', q = false; for (let i = 0; i < s.length; i++) { const c = s[i]; if (q) { if (c === '"' && s[i + 1] === '"') { cur += '"'; i++; } else if (c === '"') q = false; else cur += c; } else if (c === '"') q = true; else if (c === ',') { out.push(cur); cur = ''; } else cur += c; } out.push(cur); return out; }
for (const line of csv.slice(1)) { const r = parseRow(line); baseMm[r[0]] = Number(r[head.indexOf('base_mm')]); }

const rowMajor = m => new THREE.Matrix4().set(...m.flat());
let bad = 0;
const report = [];
for (const [name, M] of Object.entries(A.models)) {
  const buf = readFileSync(path.join(PROJECT, 'banquet', M.file.name));
  const ab = buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength);
  const gltf = await new GLTFLoader().parseAsync(ab, '');
  const scene = gltf.scene;
  scene.updateMatrixWorld(true);
  let tris = 0, verts = 0; const attrs = new Set();
  scene.traverse(o => { if (o.isMesh) { const g = o.geometry; tris += (g.index ? g.index.count : g.attributes.position.count) / 3; verts += g.attributes.position.count; Object.keys(g.attributes).forEach(a => attrs.add(a)); } });
  const box = new THREE.Box3().setFromObject(scene, true);
  // Python's Max box -> glTF: (x, z, -y)
  const pm = M.worldBox.maxZup;
  const want = { min: [pm.min[0], pm.min[2], -pm.max[1]], max: [pm.max[0], pm.max[2], -pm.min[1]] };
  const dBox = Math.max(...[0, 1, 2].map(i => Math.abs(box.min.getComponent(i) - want.min[i])), ...[0, 1, 2].map(i => Math.abs(box.max.getComponent(i) - want.max[i])));
  // the box matrix back at the model's own piece, on the bank page: T(x, level + z0, -y) Ry(rot) @ gltfSceneToBoxFrameThree
  const p = byId[M.match.piece];
  const B = new THREE.Matrix4().compose(new THREE.Vector3(p.x, level[p.floor] + baseMm[p.id] / 1000, -p.y), new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 1, 0), p.rot * Math.PI / 180), new THREE.Vector3(1, 1, 1));
  const L = rowMajor(M.relativeToBox.gltfSceneToBoxFrameThree_rowMajor);
  const placed = new THREE.Box3().setFromObject(scene, true).applyMatrix4(new THREE.Matrix4().multiplyMatrices(B, L));
  const shifted = box.clone().translate(new THREE.Vector3(-bank.offset[0], 0, bank.offset[1]));
  const dPlaced = Math.max(placed.min.distanceTo(shifted.min), placed.max.distanceTo(shifted.max));
  // the block matrix back at the model's own piece: T(ix - ox, level + z0, -(iy - oy)) Ry(insert turn) @ gltfSceneToBlockFrameThree
  const ins = M.relativeToBlock.insert;
  const I = new THREE.Matrix4().compose(new THREE.Vector3(ins.x - bank.offset[0], level[p.floor] + baseMm[p.id] / 1000, -(ins.y - bank.offset[1])), new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 1, 0), ins.rotation * Math.PI / 180), new THREE.Vector3(1, 1, 1));
  const K = rowMajor(M.relativeToBlock.gltfSceneToBlockFrameThree_rowMajor);
  const placed2 = new THREE.Box3().setFromObject(scene, true).applyMatrix4(new THREE.Matrix4().multiplyMatrices(I, K));
  const dPlaced2 = Math.max(placed2.min.distanceTo(shifted.min), placed2.max.distanceTo(shifted.max));
  const ok = tris === M.triangles && verts === M.vertices && dBox < 1e-3 && dPlaced < 1e-3 && dPlaced2 < 1e-3;
  if (!ok) bad++;
  report.push({ name, tris, verts, pyTris: M.triangles, pyVerts: M.vertices, attrs: [...attrs].sort().join('+'), boxDiff: +dBox.toExponential(2), boxPlacedBack: +dPlaced.toExponential(2), blockPlacedBack: +dPlaced2.toExponential(2), ok });
}
console.log(`three ${version}`);
console.table(report);
console.log(bad ? `${bad} MISMATCH` : 'all 8 agree');
process.exit(bad ? 1 : 0);
