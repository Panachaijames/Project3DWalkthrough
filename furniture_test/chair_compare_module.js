// ---------------------------------------------------------------------------
// The full and the slimmed chair side by side (chair_compare.html, made by make_chair_test.mjs; chair_full_vs_slimmed.png is
// a screenshot of it). Same light as the bank page (sky light + one sun), same neutral material, same camera for all four
// views: top row shaded, bottom row with the triangles drawn over. Drag to turn all four, wheel to come closer.
// Test hook: window.__compare.
// ---------------------------------------------------------------------------
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { mergeVertices, toCreasedNormals } from 'three/addons/utils/BufferGeometryUtils.js';

const GLB_B64 = '__GLB_B64__';
const SLIM = __SLIM_JSON__;

__CHAIR_LOAD__

const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.setSize(innerWidth, innerHeight);
renderer.setScissorTest(true);
document.body.appendChild(renderer.domElement);
const camera = new THREE.PerspectiveCamera(30, 1, 0.05, 50);
camera.position.set(1.15, 1.05, 1.55);                        // a person's view of the chair: from the front, a little to the right
const controls = new OrbitControls(camera, renderer.domElement);
controls.target.set(0, 0.36, 0);
controls.enableDamping = true;

const MAT = new THREE.MeshStandardMaterial({ color: 0xcdc5b8, roughness: 0.8, metalness: 0 });
const WIRE = new THREE.MeshBasicMaterial({ color: 0x2b3036, wireframe: true, transparent: true, opacity: 0.28, depthWrite: false,
  polygonOffset: true, polygonOffsetFactor: -1, polygonOffsetUnits: -1 });
function stage() {
  const s = new THREE.Scene();
  s.background = new THREE.Color(0xeef0f2);
  s.add(new THREE.HemisphereLight(0xffffff, 0xe4dfd6, 1.6));
  const sun = new THREE.DirectionalLight(0xffffff, 1.6);
  sun.position.set(-20, 40, 15);
  s.add(sun);
  const floor = new THREE.Mesh(new THREE.CircleGeometry(0.75, 64).rotateX(-Math.PI / 2), new THREE.MeshStandardMaterial({ color: 0xd4d8d2, roughness: 0.95 }));
  floor.position.y = -0.001;
  s.add(floor);
  s.userData.wire = [];
  return s;
}
const full = await loadFullChair();
const slimGeo = slimChairGeometry(40);
const fullScene = stage(), slimScene = stage();
for (const p of full.parts) {
  for (const [mat, wire] of [[MAT, false], [WIRE, true]]) {
    const m = new THREE.Mesh(p.geometry, mat);
    p.matrix.decompose(m.position, m.quaternion, m.scale);
    fullScene.add(m);
    if (wire) fullScene.userData.wire.push(m);
  }
}
slimScene.add(new THREE.Mesh(slimGeo, MAT));
const slimWire = new THREE.Mesh(slimGeo, WIRE);
slimScene.add(slimWire); slimScene.userData.wire.push(slimWire);

const slimTris = slimGeo.index.count / 3;
const num = n => n.toLocaleString('en-US');
document.getElementById('l-full').innerHTML = `<b>Full chair, as exported</b><br>${num(full.triangles)} triangles, ${full.parts.length} parts`;
document.getElementById('l-slim').innerHTML = `<b>Slimmed once (SimplifyModifier)</b><br>${num(slimTris)} triangles: ${(slimTris / full.triangles * 100).toFixed(1)} % of the full one`;
document.getElementById('note').textContent = `Same light, same neutral material (the export's own 3 materials are black fallbacks). ` +
  `${full.size.x.toFixed(2)} × ${full.size.z.toFixed(2)} m, ${full.size.y.toFixed(2)} m tall. Top: as you would see it. Bottom: the triangles drawn over it. Drag to turn all four.`;

function render() {
  controls.update();
  const W = innerWidth, H = innerHeight, top = Math.round(H * 0.6);
  const cells = [                                              // [scene, wire?, x, y (from the bottom), w, h]
    [fullScene, false, 0, H - top, W / 2, top], [slimScene, false, W / 2, H - top, W / 2, top],
    [fullScene, true, 0, 0, W / 2, H - top], [slimScene, true, W / 2, 0, W / 2, H - top],
  ];
  for (const [s, wire, x, y, w, h] of cells) {
    s.userData.wire.forEach(m => { m.visible = wire; });
    camera.aspect = w / h; camera.updateProjectionMatrix();
    renderer.setViewport(x, y, w, h); renderer.setScissor(x, y, w, h);
    renderer.render(s, camera);
  }
}
addEventListener('resize', () => renderer.setSize(innerWidth, innerHeight));
renderer.setAnimationLoop(render);
window.__compare = { ready: true, fullTriangles: full.triangles, slimTriangles: slimTris, size: full.size.toArray(), camera, controls };
