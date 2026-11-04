// ---------------------------------------------------------------------------
// The slimming judge's picture page (judge_page.html, driven by render_cells.mjs). One model at a time: the full model as
// exported (three.js GLTFLoader, its own normals) and each slimmed level from slim_levels.mjs (normals worked out again,
// smooth across edges flatter than 40 degrees, as the chair test's slimmed chair; or, for the KEEP_NORMALS variant's levels
// (<key>_n), the exported normals carried through the slimming), all in the same neutral material under
// the bank page's light (sky light + one sun), on a plain floor.
// Each cell is a crop of what a 1920 x 1080 screen shows through the Walk camera (24 mm lens: 53.1 degrees tall, eye at
// 1.6 m), so the model is exactly as many pixels as on the client's screen:
//   walk   3 m from the piece's centre (walking past it)
//   close  0.6 m from the piece's edge (a person standing at it; Walk itself stops 0.3 m from a box)
// seen from 30 degrees to the right of its front, looking at the middle of the piece. The crop is the full model's outline
// plus 16 px, the same for every level.
// Test hook: window.__judge = { ready, load(key), cell(key, level, dist) }; level 'full', 'none' (the empty stage, for
// masks) or a level id.
// ---------------------------------------------------------------------------
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { mergeVertices, toCreasedNormals } from 'three/addons/utils/BufferGeometryUtils.js';

const SCREEN = { w: 1920, h: 1080 }, LENS_MM = 24, FOV = 2 * Math.atan(12 / LENS_MM) * 180 / Math.PI;
const EYE = 1.6, AZ = 30 * Math.PI / 180, WALK_M = 3, CLOSE_GAP_M = 0.6, MARGIN_PX = 16, CREASE_DEG = 40;

const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
renderer.setPixelRatio(1);
renderer.setSize(64, 64, false);
document.body.appendChild(renderer.domElement);
const scene = new THREE.Scene();
scene.background = new THREE.Color(0xeef0f2);
scene.add(new THREE.HemisphereLight(0xffffff, 0xe4dfd6, 1.6));          // as the bank page
const sun = new THREE.DirectionalLight(0xffffff, 1.6);
sun.position.set(-20, 40, 15);
scene.add(sun);
const floor = new THREE.Mesh(new THREE.CircleGeometry(8, 128).rotateX(-Math.PI / 2), new THREE.MeshStandardMaterial({ color: 0xd4d8d2, roughness: 0.95 }));
floor.position.y = -0.001;
scene.add(floor);
const MAT = new THREE.MeshStandardMaterial({ color: 0xcdc5b8, roughness: 0.8, metalness: 0 });   // as the chair test
const DESK = new THREE.MeshStandardMaterial({ color: 0xc3c8c1, roughness: 0.9 });
const camera = new THREE.PerspectiveCamera(FOV, SCREEN.w / SCREEN.h, 0.05, 100);

const bytesUrl = p => p.split('/').map(encodeURIComponent).join('/');
function creased(g) {                                   // as chair_load.js slimChairGeometry: in mm for the corner matching
  g.scale(1000, 1000, 1000);
  const flat = toCreasedNormals(g, CREASE_DEG * Math.PI / 180);
  flat.scale(0.001, 0.001, 0.001);
  const out = mergeVertices(flat);
  out.computeBoundingSphere(); out.computeBoundingBox();
  g.dispose(); flat.dispose();
  return out;
}

// The same crease rule, but each face's normal weighted by its corner's angle at the vertex (three's toCreasedNormals counts
// every face the same, so a fan of thin slivers left by the slimmer pulls the normal its way and shows as a streak). Corners
// are matched at 0.01 mm. Level ids 'a:<id>' in cell() draw this variant.
function creasedByAngle(g) {
  const ng = g.toNonIndexed(), P = ng.attributes.position.array, nF = P.length / 9;
  const fn = new Float64Array(nF * 3), ang = new Float64Array(nF * 3), ids = new Int32Array(nF * 3), keyOf = new Map();
  const e = new Float64Array(6);
  for (let f = 0; f < nF; f++) {
    const o = 9 * f;
    const ux = P[o + 3] - P[o], uy = P[o + 4] - P[o + 1], uz = P[o + 5] - P[o + 2];
    const vx = P[o + 6] - P[o], vy = P[o + 7] - P[o + 1], vz = P[o + 8] - P[o + 2];
    let nx = uy * vz - uz * vy, ny = uz * vx - ux * vz, nz = ux * vy - uy * vx;
    const l = Math.hypot(nx, ny, nz) || 1;
    fn[3 * f] = nx / l; fn[3 * f + 1] = ny / l; fn[3 * f + 2] = nz / l;
    for (let k = 0; k < 3; k++) {                       // the corner angle at vertex k
      const a = o + 3 * k, b = o + 3 * ((k + 1) % 3), c = o + 3 * ((k + 2) % 3);
      for (let q = 0; q < 3; q++) { e[q] = P[b + q] - P[a + q]; e[3 + q] = P[c + q] - P[a + q]; }
      const la = Math.hypot(e[0], e[1], e[2]) || 1, lb = Math.hypot(e[3], e[4], e[5]) || 1;
      ang[3 * f + k] = Math.acos(Math.max(-1, Math.min(1, (e[0] * e[3] + e[1] * e[4] + e[2] * e[5]) / (la * lb))));
      const key = `${Math.round(P[a] * 1e5)},${Math.round(P[a + 1] * 1e5)},${Math.round(P[a + 2] * 1e5)}`;
      let id = keyOf.get(key);
      if (id === undefined) { id = keyOf.size; keyOf.set(key, id); }
      ids[3 * f + k] = id;
    }
  }
  const start = new Int32Array(keyOf.size + 1);
  for (let i = 0; i < ids.length; i++) start[ids[i] + 1]++;
  for (let i = 0; i < keyOf.size; i++) start[i + 1] += start[i];
  const cur = start.slice(0, keyOf.size), corners = new Int32Array(ids.length);
  for (let i = 0; i < ids.length; i++) corners[cur[ids[i]]++] = i;
  const creaseDot = Math.cos(CREASE_DEG * Math.PI / 180), N = new Float32Array(P.length);
  for (let i = 0; i < ids.length; i++) {
    const f = Math.floor(i / 3);
    let sx = 0, sy = 0, sz = 0;
    for (let k = start[ids[i]]; k < start[ids[i] + 1]; k++) {
      const j = corners[k], g2 = Math.floor(j / 3);
      if (fn[3 * f] * fn[3 * g2] + fn[3 * f + 1] * fn[3 * g2 + 1] + fn[3 * f + 2] * fn[3 * g2 + 2] > creaseDot) {
        sx += fn[3 * g2] * ang[j]; sy += fn[3 * g2 + 1] * ang[j]; sz += fn[3 * g2 + 2] * ang[j];
      }
    }
    const l = Math.hypot(sx, sy, sz) || 1;
    N[3 * i] = sx / l; N[3 * i + 1] = sy / l; N[3 * i + 2] = sz / l;
  }
  ng.setAttribute('normal', new THREE.BufferAttribute(N, 3));
  const out = mergeVertices(ng);
  out.computeBoundingSphere(); out.computeBoundingBox();
  ng.dispose();
  return out;
}

const models = {};
async function load(key) {
  if (models[key]) return models[key].summary;
  const info = await (await fetch(`levels/${key}.json`)).json();
  const bin = await (await fetch(`levels/${key}.bin`)).arrayBuffer();
  const glb = await (await fetch('/project/' + bytesUrl(info.file))).arrayBuffer();
  const gltf = await new GLTFLoader().parseAsync(glb, '');
  const holder = new THREE.Group();                     // the stage: lifted onto the desk for the monitor
  holder.position.y = info.standsAt_m;
  const wrap = new THREE.Group();
  wrap.matrixAutoUpdate = false;
  wrap.matrix.fromArray(info.gltfSceneToModelFrame_columnMajor);
  wrap.add(gltf.scene);
  let fullTriangles = 0;
  gltf.scene.traverse(o => { if (o.isMesh) { o.material = MAT; const g = o.geometry; fullTriangles += (g.index ? g.index.count : g.attributes.position.count) / 3; } });
  const full = new THREE.Group(); full.add(wrap);
  const levels = {};
  const plain = L => {
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(bin, L.posOffset, L.posCount).slice(), 3));
    g.setIndex(new THREE.BufferAttribute(new Uint32Array(bin, L.idxOffset, L.idxCount).slice(), 1));
    return g;
  };
  for (const L of info.levels) {
    if (L.nrmOffset != null) {                          // the variant with the exported normals carried through the slimming
      const g = plain(L);
      g.setAttribute('normal', new THREE.BufferAttribute(new Float32Array(bin, L.nrmOffset, L.nrmCount).slice(), 3));
      g.computeBoundingSphere(); g.computeBoundingBox();
      levels[L.id] = new THREE.Mesh(g, MAT);
    } else {
      levels[L.id] = new THREE.Mesh(creased(plain(L)), MAT);
      levels['a:' + L.id] = new THREE.Mesh(creasedByAngle(plain(L)), MAT);
    }
  }
  const extras = new THREE.Group();                     // a plain desk top under the monitor
  if (info.standsAt_m > 0.05) {
    const top = new THREE.Mesh(new THREE.BoxGeometry(info.size_m[0] + 0.3, 0.03, info.size_m[2] + 0.3), DESK);
    top.position.y = info.standsAt_m - 0.015;
    const leg = new THREE.Mesh(new THREE.BoxGeometry(0.05, info.standsAt_m - 0.03, 0.05), DESK);
    leg.position.set(0, (info.standsAt_m - 0.03) / 2, 0);
    extras.add(top, leg);
  }
  scene.add(holder, extras);
  holder.updateMatrixWorld(true);
  models[key] = { info, holder, full, levels, extras, crops: {} };
  models[key].summary = { key, fullTriangles, levels: info.levels.map(L => ({ id: L.id, label: L.label, triangles: L.triangles })) };
  return models[key].summary;
}

function placeCamera(m, dist) {
  const [sx, sy, sz] = m.info.size_m;
  const target = new THREE.Vector3(0, m.info.standsAt_m + sy / 2, 0);
  const d = dist === 'walk' ? WALK_M : Math.abs(Math.sin(AZ)) * sx / 2 + Math.abs(Math.cos(AZ)) * sz / 2 + CLOSE_GAP_M;
  camera.position.set(Math.sin(AZ) * d, EYE, Math.cos(AZ) * d);
  camera.clearViewOffset();
  camera.lookAt(target);
  camera.updateMatrixWorld(true);
  camera.updateProjectionMatrix();
  return { distance_m: Math.round(d * 1000) / 1000, eye_m: EYE, target: target.toArray() };
}
function cropFor(m, dist) {                             // the full model's outline on the 1920 x 1080 screen, plus a margin
  if (m.crops[dist]) return m.crops[dist];
  const cam = placeCamera(m, dist);
  m.holder.add(m.full); m.holder.updateMatrixWorld(true);
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  const v = new THREE.Vector3();
  m.full.traverse(o => {
    if (!o.isMesh) return;
    const P = o.geometry.attributes.position, step = Math.max(1, Math.floor(P.count / 40000));
    for (let i = 0; i < P.count; i += step) {
      v.fromBufferAttribute(P, i).applyMatrix4(o.matrixWorld).project(camera);
      const px = (v.x + 1) / 2 * SCREEN.w, py = (1 - v.y) / 2 * SCREEN.h;
      x0 = Math.min(x0, px); x1 = Math.max(x1, px); y0 = Math.min(y0, py); y1 = Math.max(y1, py);
    }
  });
  m.holder.remove(m.full);
  const c = { x: Math.max(0, Math.floor(x0 - MARGIN_PX)), y: Math.max(0, Math.floor(y0 - MARGIN_PX)) };
  c.w = Math.min(SCREEN.w, Math.ceil(x1 + MARGIN_PX)) - c.x; c.h = Math.min(SCREEN.h, Math.ceil(y1 + MARGIN_PX)) - c.y;
  c.clipped = x0 - MARGIN_PX < 0 || y0 - MARGIN_PX < 0 || x1 + MARGIN_PX > SCREEN.w || y1 + MARGIN_PX > SCREEN.h;
  c.camera = cam;
  c.modelPx = { w: Math.round(x1 - x0), h: Math.round(y1 - y0) };
  m.crops[dist] = c;
  return c;
}
function cell(key, level, dist) {
  const m = models[key];
  const crop = cropFor(m, dist);
  placeCamera(m, dist);
  camera.setViewOffset(SCREEN.w, SCREEN.h, crop.x, crop.y, crop.w, crop.h);
  camera.updateProjectionMatrix();
  for (const c of [...m.holder.children]) m.holder.remove(c);
  if (level === 'full') m.holder.add(m.full);
  else if (level !== 'none') m.holder.add(m.levels[level]);
  m.holder.updateMatrixWorld(true);
  renderer.setSize(crop.w, crop.h, false);
  renderer.render(scene, camera);
  const info = renderer.info.render;
  return { dataUrl: renderer.domElement.toDataURL('image/png'), crop, drawnTriangles: info.triangles };
}
function unload(key) {
  const m = models[key];
  if (!m) return;
  scene.remove(m.holder, m.extras);
  for (const L of Object.values(m.levels)) L.geometry.dispose();
  m.full.traverse(o => { if (o.isMesh) o.geometry.dispose(); });
  delete models[key];
}
const gl = renderer.getContext(), dbg = gl.getExtension('WEBGL_debug_renderer_info');
window.__judge = {
  ready: true, load, cell, unload,
  gpu: dbg ? gl.getParameter(dbg.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER),
  three: THREE.REVISION, screen: SCREEN, lensMm: LENS_MM, fovDeg: FOV, eye: EYE, azimuthDeg: 30, walkM: WALK_M, closeGapM: CLOSE_GAP_M, creaseDeg: CREASE_DEG,
};
