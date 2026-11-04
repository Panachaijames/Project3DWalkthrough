// The slimming judge, step 1 (3 Nov 2026): every model slimmed to the levels asked for, and each level measured against
// the full model. Nothing is installed: three 0.186.1 (its SimplifyModifier, meshoptimizer inside, and GLTFLoader) and
// three-mesh-bvh 0.9.16 are read from <project>/app/node_modules.
//   node slim_levels.mjs <project folder> <out folder> [model keys, comma separated]
//   (about 25 min for all nine, nearly all of it the gap measures; SAMPLES=30000 for a quicker run; KEEP_NORMALS=1 for the
//   variant that carries the exported normals through the slimming, written beside the results: see KEEP_NORMALS below)
// For each model (the 8 GLBs of banquet/ and the chair test's Chair.glb):
//   1. The GLB through GLTFLoader, every mesh put in the model's own frame: turned back by its real turn in the 3D team's
//      scene (analysis.json orientation.realTurnInScene, so that its front faces Max -Y = three.js +z; the round stool and
//      the pouf have no front: 0 and its long side), footprint centred on the origin, base at y = 0, metres. The parts are
//      merged into one geometry (their own matrices applied; a mirrored part's triangles turned round).
//   2. Welded by position at 0.1 mm with the normals dropped (the picture page works them out again), as slim_chair.mjs did.
//   3. Slimmed with SimplifyModifier, each level from the full welded model: 50, 25, 12 and 6 % of the triangles, and the
//      fixed budgets 20,000 / 10,000 / 5,000 / 2,500 where they are below the full count.
//   4. Each level against the full model:
//      - outline overlap (IoU) from the front, the side and the top: both drawn as filled silhouettes on a 2 mm grid
//        (a cell counts when its centre is inside a triangle)
//      - surface area kept
//      - the gap between the two surfaces, both ways: points on one surface (its vertices, at most 100,000, plus 100,000
//        spread by area) to the nearest point of the other surface (three-mesh-bvh), largest / 99th percentile / mean, over
//        all the points and over the points that can be seen from outside (a ray in one of 26 directions gets away
//        without hitting the model they lie on)
// Writes <out>/levels.json (the numbers) and <out>/levels/<key>.json + <key>.bin (the levels' positions and indices, and
// the model's frame, for the picture page). Writes nothing else.
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const [PROJECT, OUT, ONLY] = process.argv.slice(2);
if (!PROJECT || !OUT) { console.error('usage: node slim_levels.mjs <project folder> <out folder> [keys]'); process.exit(2); }
const NM = path.join(PROJECT, 'app', 'node_modules');
const imp = p => import(pathToFileURL(path.join(NM, p)).href);
const THREE = await imp('three/build/three.module.js');
const { GLTFLoader } = await imp('three/examples/jsm/loaders/GLTFLoader.js');
const { SimplifyModifier } = await imp('three/examples/jsm/modifiers/SimplifyModifier.js');
const { mergeVertices } = await imp('three/examples/jsm/utils/BufferGeometryUtils.js');
const { MeshBVH } = await imp('three-mesh-bvh/src/index.js');
const ver = p => JSON.parse(readFileSync(path.join(NM, p, 'package.json'), 'utf8')).version;
const VERSIONS = { three: ver('three'), threeMeshBvh: ver('three-mesh-bvh') };
const A = JSON.parse(readFileSync(path.join(PROJECT, 'furniture_test', 'bank_furnished', 'analysis.json'), 'utf8'));
mkdirSync(path.join(OUT, 'levels'), { recursive: true });

const CELL = 0.002;                       // silhouette grid, m
const WELD = 1e-4;                        // 0.1 mm
// KEEP_NORMALS=1: the variant that carries the exported normals through the slimming (welded by position and normal, so
// SimplifyModifier weighs the normals and keeps hard edges as seams) instead of working them out again; written beside the
// main results as levels/<key>_n.* and levels_keepnormals.json, which it never touches otherwise
const KEEP_NORMALS = process.env.KEEP_NORMALS === '1', SUFFIX = KEEP_NORMALS ? '_n' : '', SUMMARY = KEEP_NORMALS ? 'levels_keepnormals.json' : 'levels.json';
const N_AREA = Number(process.env.SAMPLES || 100000), N_VERT = Number(process.env.SAMPLES || 100000);   // gap samples per surface (SAMPLES=n for a quicker run)
const PERCENT = [0.5, 0.25, 0.12, 0.06];
const BUDGETS = [20000, 10000, 5000, 2500];

// ---------------------------------------------------------------- the models
const MODELS = [
  ['visitor_chair01', 'visitor chair01'], ['visitor_chair02', 'visitor chair02'], ['stool', 'stool'], ['sofa', 'sofa'],
  ['banquet', 'banquet'], ['working_table', 'working table'], ['side_table', 'side table'], ['monitor', 'monitor'],
].map(([key, name]) => {
  const m = A.models[name], o = m.orientation;
  let turn = o.realTurnInScene, turnFrom = 'its real turn in the scene (analysis.json)';
  if (turn == null && o.symmetry === 'no front') { turn = m.footprint.longSideTurn; turnFrom = 'no front: its long side along x'; }
  if (turn == null) { turn = 0; turnFrom = 'round: no turn'; }
  return { key, name, file: path.join(PROJECT, 'banquet', m.file.name), fileName: 'banquet/' + m.file.name, kind: m.match.kind,
    family: m.match.family, piece: m.match.piece, furnishes: m.furnishes.pieces, turn, turnFrom, standsAt: Math.max(0, Math.round(m.baseZ_m * 1000) / 1000) };
});
MODELS.push({ key: 'chair_test', name: 'Chair.glb (the chair test)', file: path.join(PROJECT, 'Chair.glb'), fileName: 'Chair.glb', kind: 'seat',
  family: 'the chair test\'s round-table chair (not a bank family)', piece: null, furnishes: 75, turn: null, turnFrom: 'the turn of its root nodes undone, as chair_load.js does', standsAt: 0 });
const todo = ONLY ? MODELS.filter(m => ONLY.split(',').includes(m.key)) : MODELS;

// ---------------------------------------------------------------- helpers
function rng(seed) {                      // mulberry32: the same points every run
  return () => { seed = (seed + 0x6D2B79F5) | 0; let t = Math.imul(seed ^ (seed >>> 15), 1 | seed); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
}
const r1 = x => Math.round(x * 10) / 10, r3 = x => Math.round(x * 1000) / 1000, r4 = x => Math.round(x * 1e4) / 1e4;

function bboxOf(pos) {
  const lo = [Infinity, Infinity, Infinity], hi = [-Infinity, -Infinity, -Infinity];
  for (let i = 0; i < pos.length; i += 3) for (let c = 0; c < 3; c++) { const v = pos[i + c]; if (v < lo[c]) lo[c] = v; if (v > hi[c]) hi[c] = v; }
  return { lo, hi };
}
function triAreas(pos, idx) {
  const n = idx.length / 3, out = new Float64Array(n);
  for (let t = 0; t < n; t++) {
    const a = idx[3 * t] * 3, b = idx[3 * t + 1] * 3, c = idx[3 * t + 2] * 3;
    const ux = pos[b] - pos[a], uy = pos[b + 1] - pos[a + 1], uz = pos[b + 2] - pos[a + 2];
    const vx = pos[c] - pos[a], vy = pos[c + 1] - pos[a + 1], vz = pos[c + 2] - pos[a + 2];
    const cx = uy * vz - uz * vy, cy = uz * vx - ux * vz, cz = ux * vy - uy * vx;
    out[t] = 0.5 * Math.sqrt(cx * cx + cy * cy + cz * cz);
  }
  return out;
}
const sum = a => { let s = 0; for (const v of a) s += v; return s; };

// silhouette of (pos, idx) seen along one axis: coordinates (ax, ay) on the grid g; a cell counts when its centre is inside
function raster(pos, idx, ax, ay, g) {
  const img = new Uint8Array(g.nu * g.nv);
  for (let t = 0; t < idx.length; t += 3) {
    const a = idx[t] * 3, b = idx[t + 1] * 3, c = idx[t + 2] * 3;
    const x0 = (pos[a + ax] - g.u0) / CELL, y0 = (pos[a + ay] - g.v0) / CELL;
    const x1 = (pos[b + ax] - g.u0) / CELL, y1 = (pos[b + ay] - g.v0) / CELL;
    const x2 = (pos[c + ax] - g.u0) / CELL, y2 = (pos[c + ay] - g.v0) / CELL;
    const area = (x1 - x0) * (y2 - y0) - (y1 - y0) * (x2 - x0);
    if (area === 0) continue;
    const i0 = Math.max(0, Math.ceil(Math.min(x0, x1, x2) - 0.5)), i1 = Math.min(g.nu - 1, Math.floor(Math.max(x0, x1, x2) - 0.5));
    const j0 = Math.max(0, Math.ceil(Math.min(y0, y1, y2) - 0.5)), j1 = Math.min(g.nv - 1, Math.floor(Math.max(y0, y1, y2) - 0.5));
    for (let j = j0; j <= j1; j++) {
      const py = j + 0.5;
      for (let i = i0; i <= i1; i++) {
        const px = i + 0.5;
        const w0 = (x2 - x1) * (py - y1) - (y2 - y1) * (px - x1);
        const w1 = (x0 - x2) * (py - y2) - (y0 - y2) * (px - x2);
        const w2 = (x1 - x0) * (py - y0) - (y1 - y0) * (px - x0);
        if ((w0 >= 0 && w1 >= 0 && w2 >= 0) || (w0 <= 0 && w1 <= 0 && w2 <= 0)) img[j * g.nu + i] = 1;
      }
    }
  }
  return img;
}
const VIEWS = { front: [0, 1], side: [2, 1], top: [0, 2] };   // front: seen along z (x, y); side: along x (z, y); top: along y (x, z)

// points on a surface: every (welded) vertex, at most nVert of them, and nArea spread by area
function samplePoints(pos, idx, areas, weldedPos, nArea, nVert, seed) {
  const rand = rng(seed), nW = weldedPos.length / 3, takeV = Math.min(nVert, nW);
  const pts = new Float32Array((takeV + nArea) * 3);
  let o = 0;
  if (takeV === nW) { pts.set(weldedPos); o = weldedPos.length; }
  else for (let k = 0; k < takeV; k++) { const i = Math.floor(rand() * nW) * 3; pts[o++] = weldedPos[i]; pts[o++] = weldedPos[i + 1]; pts[o++] = weldedPos[i + 2]; }
  const cum = new Float64Array(areas.length); let s = 0;
  for (let t = 0; t < areas.length; t++) { s += areas[t]; cum[t] = s; }
  for (let k = 0; k < nArea; k++) {
    const r = rand() * s; let lo = 0, hi = cum.length - 1;
    while (lo < hi) { const mid = (lo + hi) >> 1; if (cum[mid] < r) lo = mid + 1; else hi = mid; }
    const a = idx[3 * lo] * 3, b = idx[3 * lo + 1] * 3, c = idx[3 * lo + 2] * 3;
    let u = rand(), v = rand(); if (u + v > 1) { u = 1 - u; v = 1 - v; }
    for (let q = 0; q < 3; q++) pts[o++] = pos[a + q] + u * (pos[b + q] - pos[a + q]) + v * (pos[c + q] - pos[a + q]);
  }
  return { pts, vertexSamples: takeV };
}

const DIRS = [];
for (const x of [-1, 0, 1]) for (const y of [-1, 0, 1]) for (const z of [-1, 0, 1]) if (x || y || z) DIRS.push(new THREE.Vector3(x, y, z).normalize());
// a point can be seen when a ray in one of the 26 directions gets away without hitting the surface it lies on
function visibility(pts, bvh, far) {
  const n = pts.length / 3, out = new Uint8Array(n), ray = new THREE.Ray();
  for (let i = 0; i < n; i++) {
    for (const d of DIRS) {
      ray.origin.set(pts[3 * i], pts[3 * i + 1], pts[3 * i + 2]); ray.direction.copy(d);
      if (!bvh.raycastFirst(ray, THREE.DoubleSide, 3e-4, far)) { out[i] = 1; break; }
    }
  }
  return out;
}
function distances(pts, bvh) {
  const n = pts.length / 3, d = new Float32Array(n), p = new THREE.Vector3(), target = {};
  for (let i = 0; i < n; i++) { p.set(pts[3 * i], pts[3 * i + 1], pts[3 * i + 2]); bvh.closestPointToPoint(p, target); d[i] = target.distance; }
  return d;
}
function stats(d, mask) {
  const v = []; let at = -1, max = -1;
  for (let i = 0; i < d.length; i++) if (!mask || mask[i]) { v.push(d[i]); if (d[i] > max) { max = d[i]; at = i; } }
  if (!v.length) return null;
  const s = Float32Array.from(v).sort(), q = f => s[Math.min(s.length - 1, Math.floor(f * s.length))];
  return { points: v.length, max_mm: r1(max * 1000), p99_mm: r1(q(0.99) * 1000), p95_mm: r1(q(0.95) * 1000), mean_mm: r1(sum(s) / s.length * 1000), atIndex: at };
}

// ---------------------------------------------------------------- one model
async function loadScene(file) {
  const buf = readFileSync(file);
  const gltf = await new GLTFLoader().parseAsync(buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength), '');
  gltf.scene.updateMatrixWorld(true);
  return gltf.scene;
}
function chairTestTurn(scene) {           // as chair_load.js: the turn about the vertical of the root nodes
  const ex = new THREE.Vector3(1, 0, 0).applyQuaternion(scene.children[0].quaternion);
  return Math.atan2(-ex.z, ex.x) * 180 / Math.PI;
}

async function doModel(M) {
  const tStart = performance.now();
  const scene = await loadScene(M.file);
  if (M.turn == null) M.turn = Math.round(chairTestTurn(scene) * 1000) / 1000;
  const R = new THREE.Matrix4().makeRotationY(-M.turn * Math.PI / 180);
  // merged, turned back
  const meshes = [];
  scene.traverse(o => { if (o.isMesh) meshes.push(o); });
  let nv = 0, nt = 0;
  for (const o of meshes) { const g = o.geometry; nv += g.attributes.position.count; nt += (g.index ? g.index.count : g.attributes.position.count) / 3; }
  const pos = new Float32Array(nv * 3), nrm = KEEP_NORMALS ? new Float32Array(nv * 3) : null, idx = new Uint32Array(nt * 3), triPart = new Uint16Array(nt), parts = [];
  const v = new THREE.Vector3();
  let vo = 0, io = 0, to = 0;
  meshes.forEach((o, k) => {
    const g = o.geometry, P = g.attributes.position, I = g.index, Mx = R.clone().multiply(o.matrixWorld), flip = Mx.determinant() < 0, first = vo / 3;
    if (nrm) {
      const N = g.attributes.normal, nm = new THREE.Matrix3().getNormalMatrix(Mx);
      for (let i = 0, o = vo; i < P.count; i++) { v.fromBufferAttribute(N, i).applyMatrix3(nm).normalize(); nrm[o++] = v.x; nrm[o++] = v.y; nrm[o++] = v.z; }
    }
    for (let i = 0; i < P.count; i++) { v.fromBufferAttribute(P, i).applyMatrix4(Mx); pos[vo++] = v.x; pos[vo++] = v.y; pos[vo++] = v.z; }
    const n = I ? I.count : P.count;
    for (let i = 0; i < n; i += 3) {
      const a = I ? I.getX(i) : i, b = I ? I.getX(i + 1) : i + 1, c = I ? I.getX(i + 2) : i + 2;
      idx[io++] = first + a; idx[io++] = first + (flip ? c : b); idx[io++] = first + (flip ? b : c); triPart[to++] = k;
    }
    parts.push({ name: o.name, triangles: n / 3, vertices: P.count, mirrored: flip });
  });
  // footprint centred, base at 0
  const bb0 = bboxOf(pos), centre = [(bb0.lo[0] + bb0.hi[0]) / 2, bb0.lo[1], (bb0.lo[2] + bb0.hi[2]) / 2];
  for (let i = 0; i < pos.length; i += 3) { pos[i] -= centre[0]; pos[i + 1] -= centre[1]; pos[i + 2] -= centre[2]; }
  const C = new THREE.Matrix4().makeTranslation(-centre[0], -centre[1], -centre[2]).multiply(R);   // glTF scene -> the model's frame
  const bb = bboxOf(pos), size = [0, 1, 2].map(c => bb.hi[c] - bb.lo[c]);
  const T = nt;
  const full = new THREE.BufferGeometry();
  full.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  full.setIndex(new THREE.BufferAttribute(idx, 1));
  let welded;
  if (nrm) { const fn = full.clone(); fn.setAttribute('normal', new THREE.BufferAttribute(nrm, 3)); welded = mergeVertices(fn, WELD); }
  else welded = mergeVertices(full, WELD);
  const wPos = welded.attributes.position.array, wIdx = welded.index.array, wv = wPos.length / 3;
  const fullAreas = triAreas(pos, idx), fullArea = sum(fullAreas);

  // the levels
  const wanted = [];
  for (const r of PERCENT) wanted.push({ id: `${Math.round(r * 100)}%`, label: `${Math.round(r * 100)} %`, target: Math.max(1, Math.floor(T * r)) });
  for (const b of BUDGETS) if (b < T) wanted.push({ id: `${b}`, label: `${b.toLocaleString('en-US')} budget`, target: b });
  wanted.sort((a, b) => b.target - a.target || (a.id.endsWith('%') ? -1 : 1));
  const levels = [];
  for (const L of wanted) {
    const t0 = performance.now();
    const s = await new SimplifyModifier().modify(welded, wv * (1 - L.target / T));
    const ms = performance.now() - t0;
    const sp = Float32Array.from(s.attributes.position.array), si = Uint32Array.from(s.index.array);
    const sn = s.attributes.normal ? Float32Array.from(s.attributes.normal.array) : null;
    levels.push({ ...L, pos: sp, nrm: sn, idx: si, triangles: si.length / 3, vertices: sp.length / 3, ms: Math.round(ms) });
  }

  // silhouettes: one grid per view over the full model and every level, 10 cells to spare
  let ulo = [...bb.lo], uhi = [...bb.hi];
  for (const L of levels) { const b = bboxOf(L.pos); for (let c = 0; c < 3; c++) { ulo[c] = Math.min(ulo[c], b.lo[c]); uhi[c] = Math.max(uhi[c], b.hi[c]); } }
  const grids = {}, fullSil = {};
  for (const [view, [ax, ay]] of Object.entries(VIEWS)) {
    const g = { u0: ulo[ax] - 10 * CELL, v0: ulo[ay] - 10 * CELL };
    g.nu = Math.ceil((uhi[ax] - g.u0) / CELL) + 10; g.nv = Math.ceil((uhi[ay] - g.v0) / CELL) + 10;
    grids[view] = g; fullSil[view] = raster(pos, idx, ax, ay, g);
  }
  const fullSilCells = Object.fromEntries(Object.entries(fullSil).map(([k, s]) => [k, sum(s)]));

  // gaps: the full model's points, and which of them can be seen
  const far = Math.hypot(...size) * 2 + 1;
  const fullBVH = new MeshBVH(full, { indirect: true });
  const fs = samplePoints(pos, idx, fullAreas, wPos, N_AREA, N_VERT, 1234);
  const tv = performance.now();
  const fullVis = visibility(fs.pts, fullBVH, far);
  const visMs = performance.now() - tv;
  const fullVisibleShare = sum(fullVis) / fullVis.length;

  const out = [];
  for (const L of levels) {
    const sil = {};
    for (const [view, [ax, ay]] of Object.entries(VIEWS)) {
      const a = fullSil[view], b = raster(L.pos, L.idx, ax, ay, grids[view]);
      let inter = 0, uni = 0, onlyFull = 0, onlySlim = 0;
      for (let i = 0; i < a.length; i++) { const x = a[i], y = b[i]; if (x & y) inter++; if (x | y) uni++; if (x && !y) onlyFull++; if (y && !x) onlySlim++; }
      sil[view] = { iou: r4(inter / uni), lost_cm2: r1(onlyFull * CELL * CELL * 1e4), added_cm2: r1(onlySlim * CELL * CELL * 1e4) };
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(L.pos, 3));
    g.setIndex(new THREE.BufferAttribute(L.idx, 1));
    const sAreas = triAreas(L.pos, L.idx), sArea = sum(sAreas);
    const bvh = new MeshBVH(g, { indirect: true });
    // full -> slim: what the slimmed surface misses; slim -> full: where it stands away from the full one
    const dF = distances(fs.pts, bvh);
    const ss = samplePoints(L.pos, L.idx, sAreas, L.pos, N_AREA, N_VERT, 4321);
    const sVis = visibility(ss.pts, bvh, far);
    const dS = distances(ss.pts, fullBVH);
    const fAll = stats(dF), fVis = stats(dF, fullVis), sAll = stats(dS), sVisS = stats(dS, sVis);
    const where = (st, pts) => {
      if (!st) return null;
      const i = st.atIndex, p = new THREE.Vector3(pts[3 * i], pts[3 * i + 1], pts[3 * i + 2]), hit = fullBVH.closestPointToPoint(p, {});
      const part = hit ? parts[triPart[hit.faceIndex]]?.name : null;
      delete st.atIndex;
      return { at_m: [r3(p.x), r3(p.y), r3(p.z)], nearestFullPart: part };
    };
    const gap = {
      fullToSlim: { all: fAll, visible: fVis, visibleMaxAt: where(fVis, fs.pts) },
      slimToFull: { all: sAll, visible: sVisS, visibleMaxAt: where(sVisS, ss.pts) },
    };
    delete fAll.atIndex; delete sAll.atIndex;
    const visMax = Math.max(fVis?.max_mm ?? 0, sVisS?.max_mm ?? 0), allMax = Math.max(fAll.max_mm, sAll.max_mm);
    const bytes = L.pos.byteLength + L.idx.length * (L.vertices <= 65535 ? 2 : 4);
    out.push({
      id: L.id, label: L.label, target: L.target, triangles: L.triangles, vertices: L.vertices, shareOfFull: r4(L.triangles / T),
      ms: L.ms, bytes, outline: sil, outlineIoUMin: Math.min(...Object.values(sil).map(s => s.iou)),
      areaKept: r4(sArea / fullArea), gap, largestGapSeen_mm: visMax, largestGapAnywhere_mm: allMax,
      p99GapSeen_mm: Math.max(fVis?.p99_mm ?? 0, sVisS?.p99_mm ?? 0),
    });
    console.log(`  ${M.key} ${L.id.padStart(5)} ${String(L.triangles).padStart(7)} tris  IoU f/s/t ${sil.front.iou}/${sil.side.iou}/${sil.top.iou}  area ${r3(sArea / fullArea)}  gap seen ${visMax} mm (p99 ${Math.max(fVis?.p99_mm ?? 0, sVisS?.p99_mm ?? 0)}), anywhere ${allMax} mm`);
  }

  // the levels for the picture page: positions (Float32) then indices (Uint32), one after another
  const chunks = [], manifest = [];
  let off = 0;
  for (const L of levels) {
    const pb = Buffer.from(L.pos.buffer, L.pos.byteOffset, L.pos.byteLength), ib = Buffer.from(L.idx.buffer, L.idx.byteOffset, L.idx.byteLength);
    const entry = { id: L.id, label: L.label, triangles: L.triangles, vertices: L.vertices, posOffset: off, posCount: L.pos.length, idxOffset: off + pb.length, idxCount: L.idx.length };
    chunks.push(pb, ib); off += pb.length + ib.length;
    if (L.nrm) { const nb = Buffer.from(L.nrm.buffer, L.nrm.byteOffset, L.nrm.byteLength); entry.nrmOffset = off; entry.nrmCount = L.nrm.length; chunks.push(nb); off += nb.length; }
    manifest.push(entry);
  }
  writeFileSync(path.join(OUT, 'levels', `${M.key}${SUFFIX}.bin`), Buffer.concat(chunks));
  const info = {
    key: M.key + SUFFIX, name: M.name + (KEEP_NORMALS ? ' (normals kept)' : ''), file: M.fileName, kind: M.kind, family: M.family, piece: M.piece, furnishes: M.furnishes,
    normals: KEEP_NORMALS ? 'the exported normals, carried through the slimming' : 'worked out again in the page (40 degree crease)',
    turnUndone_deg: M.turn, turnFrom: M.turnFrom, standsAt_m: M.standsAt, size_m: size.map(r4),
    gltfSceneToModelFrame_columnMajor: C.toArray().map(x => Math.round(x * 1e7) / 1e7),
    full: { triangles: T, vertices: nv, weldedVertices: wv, parts, area_m2: r4(fullArea) },
    levels: manifest,
  };
  writeFileSync(path.join(OUT, 'levels', `${M.key}${SUFFIX}.json`), JSON.stringify(info, null, 1));
  console.log(`${M.key}: ${T} triangles, ${levels.length} levels, ${Math.round((performance.now() - tStart) / 1000)} s (visibility of the full model's ${fs.pts.length / 3} points ${Math.round(visMs / 1000)} s, ${r3(fullVisibleShare)} seen)`);
  return {
    key: M.key + SUFFIX, name: M.name + (KEEP_NORMALS ? ' (normals kept)' : ''), file: M.fileName, kind: M.kind, family: M.family, piece: M.piece, furnishes: M.furnishes,
    normals: KEEP_NORMALS ? 'the exported normals, carried through the slimming' : 'worked out again in the page (40 degree crease)',
    turnUndone_deg: M.turn, turnFrom: M.turnFrom, size_m: size.map(r3),
    full: { triangles: T, vertices: nv, weldedVertices: wv, area_m2: r4(fullArea), outlineCells: fullSilCells, parts },
    gapSamples: { fullModel: { points: fs.pts.length / 3, vertices: fs.vertexSamples, seenShare: r3(fullVisibleShare) } },
    levels: out,
  };
}

// ---------------------------------------------------------------- all of them
const results = [];
let prev = {};
try { prev = JSON.parse(readFileSync(path.join(OUT, SUMMARY), 'utf8')); } catch { /* first run */ }
for (const M of todo) results.push(await doModel(M));
const merged = Object.fromEntries((prev.models || []).map(m => [m.key, m]));
for (const r of results) merged[r.key] = r;
const order = MODELS.map(m => m.key + SUFFIX).filter(k => merged[k]);
writeFileSync(path.join(OUT, SUMMARY), JSON.stringify({
  variant: KEEP_NORMALS ? 'normals kept: welded by position and normal, the exported normals carried through SimplifyModifier (which then weighs them)' : 'as the chair test: welded by position, normals dropped and worked out again in the page',
  what: 'Each model slimmed to 50 / 25 / 12 / 6 % of its triangles and to the fixed budgets 20,000 / 10,000 / 5,000 / 2,500 below its full count, and each level measured against the full model (slim_levels.mjs).',
  made: new Date().toISOString(), versions: VERSIONS,
  method: {
    frame: 'each model turned back by its real turn in the 3D team\'s scene (front = three.js +z = Max -Y), footprint centred, base at y = 0, metres; the parts merged into one geometry',
    slimming: `SimplifyModifier (three ${VERSIONS.three}; meshoptimizer's simplify, target error 1, no locked borders) on the merged model welded by position at ${WELD * 1000} mm with its normals dropped; each level made from the full model; the count passed is the vertices to remove that gives the target share of the triangles`,
    outline: `filled silhouettes on a ${CELL * 1000} mm grid seen from the front (along z), the side (along x) and the top (along y); a cell counts when its centre is inside a triangle; IoU = cells in both / cells in either; lost / added = cells only in the full / only in the slimmed model`,
    area: 'surface area of the slimmed model / of the full model (all triangles, hidden ones too)',
    gap: `points on each surface (its welded vertices, at most ${N_VERT.toLocaleString('en-US')}, plus ${N_AREA.toLocaleString('en-US')} spread by area, fixed seed) to the nearest point of the other surface (three-mesh-bvh ${VERSIONS.threeMeshBvh} closestPointToPoint): fullToSlim = what the slimmed model misses, slimToFull = where it stands away from the full one; 'visible' = the points from which a ray in one of 26 directions (the cube's faces, edges and corners) gets away without hitting the surface they lie on; largestGapSeen_mm = the larger of the two visible maxima`,
  },
  models: order.map(k => merged[k]),
}, null, 1));
console.log('wrote', path.join(OUT, SUMMARY));
