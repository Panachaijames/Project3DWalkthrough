// Where each of the 3D team's 8 models goes on the bank page, worked out ONCE from the analysis (3 Nov 2026):
//   node make_placements.mjs [dxf_pieces.json]
// Reads (read only): analysis.json (this folder), ../../bank_test/src/bank_model.json, ../../bank_test/bank_furniture_list.csv,
// ../../banquet/*.glb, and the analysis step's dxf_pieces.json (every furniture INSERT read back from the DWGs by its handle;
// default: the analysis work folder in the session scratchpad, or pass its path). three 0.186.1 is read from ../../app/node_modules
// (nothing is installed). Writes placements.json here.
//
// Each model is normalised once: the GLB scene as loaded (Y up, where it stood in the team's Max scene) is taken into its own
// piece's BLOCK frame (origin at the block's insertion point on the box underside, the block's own axes: the INSERT's turn undone),
// with the analysis's matrix gltfSceneToBlockFrameThree, or its `suggested` one where the export did not stand on its piece
// (banquet: once for the run of four DIOR modules; sofa: turned and moved onto its drawing; stool, side table: centred on their
// box). Then at every piece P of its family (three.js, in P's level group, as the bank page puts its boxes):
//   place(P) = T(insert x - 1.212, level + base, -(insert y - 0.348)) Ry(insert turn) F(P)        F(P) = diag(1, 1, -1) when P's
//   full model at P = place(P) N   (N = the normalising matrix)                                    block drawing is the matched
//   slimmed model at P = place(P)  (the slimmed GLBs are written already normalised)              piece's mirrored in y
// Checks: at its own piece every unsuggested model lands where it was exported (shifted by the bank offset); at every piece the
// box centre seen from that piece's block frame (mirror undone) is where it is at the matched piece (same drawing, same box).
import { readFileSync, writeFileSync, existsSync } from 'node:fs';
import { createHash } from 'node:crypto';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const PROJECT = path.resolve(HERE, '..', '..');
const THREE_DIR = path.join(PROJECT, 'app', 'node_modules', 'three');
const imp = rel => import(pathToFileURL(path.join(THREE_DIR, rel)).href);
const THREE = await imp('build/three.module.js');
const { GLTFLoader } = await imp('examples/jsm/loaders/GLTFLoader.js');
const threeVersion = JSON.parse(readFileSync(path.join(THREE_DIR, 'package.json'), 'utf8')).version;

const SCRATCH_DXF = 'C:/Users/DWP2/AppData/Local/Temp/claude/c--Users-DWP2-Desktop-Project-walkthrough/e1e2f8a1-5b17-462a-bbe8-01925d989674/scratchpad/work/out/dxf_pieces.json';
const DXF = process.argv[2] || SCRATCH_DXF;
if (!existsSync(DXF)) throw new Error('dxf_pieces.json not found: pass its path (the analysis step writes it with scripts/dxf_pieces.py)');
const A = JSON.parse(readFileSync(path.join(HERE, 'analysis.json'), 'utf8'));
const bank = JSON.parse(readFileSync(path.join(PROJECT, 'bank_test', 'src', 'bank_model.json'), 'utf8'));
const dxf = Object.fromEntries(JSON.parse(readFileSync(DXF, 'utf8')).map(p => [p.id, p]));
const [OX, OY] = bank.offset;
const LEVEL = Object.fromEntries(bank.floors.map(f => [f.key, f.level]));
const byId = Object.fromEntries(bank.furniture.map(p => [p.id, p]));

// base_mm by column name (family / block names may hold commas inside quotes)
function parseRow(s) { const out = []; let cur = '', q = false; for (let i = 0; i < s.length; i++) { const c = s[i]; if (q) { if (c === '"' && s[i + 1] === '"') { cur += '"'; i++; } else if (c === '"') q = false; else cur += c; } else if (c === '"') q = true; else if (c === ',') { out.push(cur); cur = ''; } else cur += c; } out.push(cur); return out; }
const csv = readFileSync(path.join(PROJECT, 'bank_test', 'bank_furniture_list.csv'), 'utf8').replace(/^\uFEFF/, '').split(/\r?\n/).filter(Boolean);
const head = parseRow(csv[0]);
const BASE = {};
for (const line of csv.slice(1)) { const r = parseRow(line); BASE[r[0]] = Number(r[head.indexOf('base_mm')]) / 1000; }

const UP = new THREE.Vector3(0, 1, 0), D2R = Math.PI / 180;
const rowMajor = m => new THREE.Matrix4().set(...m.flat());
const toRows = m => { const e = m.elements; return [0, 1, 2, 3].map(r => [0, 1, 2, 3].map(c => +e[c * 4 + r].toFixed(7) + 0)); };
const MIRROR = { none: [1, 1, 1], 'mirror y': [1, 1, -1], 'mirror x': [-1, 1, 1] };     // three.js: plan y is -z
function placeMatrix(ins, floor, base, mirror) {
  const m = new THREE.Matrix4().compose(new THREE.Vector3(ins.x - OX, LEVEL[floor] + base, -(ins.y - OY)),
    new THREE.Quaternion().setFromAxisAngle(UP, ins.rotation * D2R), new THREE.Vector3(1, 1, 1));
  const s = MIRROR[mirror];
  if (!s) throw new Error('unknown mirror ' + mirror);
  return m.multiply(new THREE.Matrix4().makeScale(...s));
}
const r4 = v => Math.round(v * 1e4) / 1e4 + 0;

const out = { made: new Date().toISOString(), three: threeVersion, offset: bank.offset, levels: LEVEL,
  sources: { analysis: 'analysis.json', inserts: 'dxf_pieces.json of the analysis step (LibreDWG 0.14 conversions of I1201 / I1202, read with ezdxf 1.4.4)', bases: 'bank_test/bank_furniture_list.csv base_mm' },
  formula: 'full model at piece P: place(P) x normalise; slimmed GLBs are already normalised: place(P). place(P) = T(insert x - 1.212, level + base, -(insert y - 0.348)) Ry(insert turn) F(P), F = diag(1, 1, -1) for a block drawing mirrored in y against the matched piece\'s. Matrices row-major (three.js world of the bank page, in the level\'s group).',
  models: {} };
const report = [];
for (const [name, M] of Object.entries(A.models)) {
  const fam = A.families[name];
  const rb = M.relativeToBlock, sug = rb.suggested;
  const N = rowMajor((sug || rb).gltfSceneToBlockFrameThree_rowMajor);
  const NB = rowMajor((M.relativeToBox.suggested || M.relativeToBox).gltfSceneToBoxFrameThree_rowMajor);
  const buf = readFileSync(path.join(PROJECT, 'banquet', M.file.name));
  const gltf = await new GLTFLoader().parseAsync(buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength), '');
  const scene = gltf.scene; scene.updateMatrixWorld(true);
  const parts = [];
  scene.traverse(o => { if (o.isMesh) parts.push({ name: o.name, triangles: (o.geometry.index ? o.geometry.index.count : o.geometry.attributes.position.count) / 3, det: Math.sign(o.matrixWorld.determinant()) }); });
  // the parts in the order the loader gives them must be the analysis's parts (same triangles, same order)
  const want = M.parts.map(p => p.triangles);
  if (JSON.stringify(parts.map(p => p.triangles)) !== JSON.stringify(want)) throw new Error(`${name}: parts ${parts.map(p => p.triangles)} against the analysis's ${want}`);
  const bb = new THREE.Box3().setFromObject(scene, true);
  // the normalised model: its box in the block frame
  const nb = bb.clone(); { const g = new THREE.Group(); g.matrixAutoUpdate = false; g.matrix.copy(N); g.add(scene); g.updateMatrixWorld(true); nb.setFromObject(g, true); g.remove(scene); scene.updateMatrixWorld(true); }
  const centreN = nb.getCenter(new THREE.Vector3());

  // check 1: unsuggested, at its own piece: lands where it was exported (shifted by the offset)
  const own = M.match.piece, insOwn = rb.insert;
  if (Math.abs(insOwn.x - dxf[own].insert.x) > 1e-6 || Math.abs(insOwn.y - dxf[own].insert.y) > 1e-6) throw new Error(`${name}: insert of ${own} differs between the analysis and dxf_pieces.json`);
  let backAtOwn = null;
  if (!sug) {
    const placed = new THREE.Box3().setFromObject(scene, true).applyMatrix4(placeMatrix(insOwn, dxf[own].floor, BASE[own], 'none').multiply(N));
    const shifted = bb.clone().translate(new THREE.Vector3(-OX, 0, OY));
    backAtOwn = Math.max(placed.min.distanceTo(shifted.min), placed.max.distanceTo(shifted.max));
    if (backAtOwn > 1e-3) throw new Error(`${name}: placed back at ${own} it is ${backAtOwn} m off`);
  }
  // the box centre in the matched piece's block frame
  const blockOf = (id, mirror) => { const p = dxf[id]; return placeMatrix(p.insert, p.floor, BASE[id], mirror); };
  const boxIn = (id, mirror) => { const b = byId[id]; return new THREE.Vector3(b.x, LEVEL[b.floor] + BASE[id], -b.y).applyMatrix4(blockOf(id, mirror).invert()); };
  const ref = boxIn(own, 'none');
  const pieces = [];
  const groups = name === 'banquet' ? [{ key: own, ids: fam.ids }] : fam.ids.map(id => ({ key: id, ids: [id] }));    // the banquet: once for its run
  for (const g of groups) {
    const pp = fam.perPiece.find(q => q.id === g.key), d = dxf[g.key], b = byId[g.key];
    if (!pp || !d || !b) throw new Error(`${name}: ${g.key} missing`);
    if (Math.abs(d.insert.rotation - pp.insertTurn) > 1e-3) throw new Error(`${g.key}: insert turn ${d.insert.rotation} against ${pp.insertTurn}`);
    if (d.insert.mirrored || d.insert.xscale !== 1 || d.insert.yscale !== 1) throw new Error(`${g.key}: a scaled or mirrored INSERT`);
    const mirror = pp.mirrorToMatchedPiece;
    const place = placeMatrix(d.insert, d.floor, BASE[g.key], mirror);
    const gap = boxIn(g.key, mirror).distanceTo(ref);                  // same box in the same place of the block: ~0
    const at = centreN.clone().applyMatrix4(place);                    // the normalised model's box centre, placed
    const centreGap = Math.hypot(at.x - b.x, at.z + b.y);             // from the piece's box centre (plan)
    const boxPlace = new THREE.Matrix4().compose(new THREE.Vector3(b.x, LEVEL[b.floor] + BASE[g.key], -b.y), new THREE.Quaternion().setFromAxisAngle(UP, b.rot * D2R), new THREE.Vector3(1, 1, 1));
    pieces.push({ key: g.key, ids: g.ids, floor: d.floor, level: LEVEL[d.floor], base: BASE[g.key],
      insert: { x: r4(d.insert.x - OX), y: r4(d.insert.y - OY), turn: d.insert.rotation }, mirror, box: { x: b.x, y: b.y, rot: b.rot },
      boxInBlockGap_m: r4(gap), modelCentreFromBoxCentre_m: r4(centreGap), place: toRows(place), boxPlace: toRows(boxPlace) });
  }
  out.models[name] = {
    file: 'banquet/' + M.file.name, bytes: buf.length, sha256: createHash('sha256').update(buf).digest('hex'),
    family: fam.family, kind: fam.kind, triangles: M.triangles, vertices: M.vertices,
    parts: parts.map((p, i) => ({ index: i, name: p.name, triangles: p.triangles, mirrored: p.det < 0, exportMaterial: M.parts[i].material })),
    matchedPiece: own, normalise: toRows(N), normaliseBox: toRows(NB), suggested: sug ? sug.why : null,
    sizeNormalised_m: nb.getSize(new THREE.Vector3()).toArray().map(r4), centreNormalised: centreN.toArray().map(r4),
    placedBackAtOwnPiece_m: backAtOwn === null ? null : +backAtOwn.toExponential(2),
    piecesFurnished: fam.ids.length, copies: pieces.length, pieces,
  };
  report.push({ name, parts: parts.length, copies: pieces.length, hides: fam.ids.length, backAtOwn_mm: backAtOwn === null ? 'suggested' : +(backAtOwn * 1000).toFixed(4),
    maxBoxInBlockGap_mm: Math.round(Math.max(...pieces.map(p => p.boxInBlockGap_m)) * 1000), centreFromBox_mm: [Math.round(Math.min(...pieces.map(p => p.modelCentreFromBoxCentre_m)) * 1000), Math.round(Math.max(...pieces.map(p => p.modelCentreFromBoxCentre_m)) * 1000)].join(' - '),
    size: out.models[name].sizeNormalised_m.join(' x ') });
}
const hidden = Object.values(out.models).flatMap(m => m.pieces.flatMap(p => p.ids));
if (new Set(hidden).size !== hidden.length) throw new Error('a piece is furnished twice');
out.piecesFurnished = hidden.length;
writeFileSync(path.join(HERE, 'placements.json'), JSON.stringify(out, null, 1));
console.table(report);
console.log(`${hidden.length} pieces furnished by ${Object.values(out.models).reduce((a, m) => a + m.copies, 0)} copies; placements.json written (three ${threeVersion})`);
