import json, sys
data = json.load(open('house3d_pdf.json'))
html = r'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>PDF to 3D test</title>
<style>
  :root { --bg:#eef0f2; --panel:#ffffffee; --ink:#1d2329; --muted:#5b6670; --accent:#c9773e; --line:#d5dade; }
  html, body { margin:0; height:100%; background:var(--bg); font:14px/1.4 system-ui, -apple-system, "Segoe UI", sans-serif; color:var(--ink); }
  #panel { position:fixed; top:12px; left:12px; max-width:320px; background:var(--panel); border:1px solid var(--line); border-radius:10px; padding:12px 14px; box-shadow:0 2px 10px #0001; }
  h1 { font-size:15px; margin:0 0 4px; }
  p { margin:0 0 10px; color:var(--muted); font-size:12.5px; }
  .row { display:flex; gap:6px; flex-wrap:wrap; margin-bottom:8px; }
  button { border:1px solid var(--line); background:#fff; border-radius:7px; padding:5px 10px; cursor:pointer; font:inherit; }
  button.on { background:var(--accent); border-color:var(--accent); color:#fff; }
  label { font-size:13px; color:var(--ink); display:flex; align-items:center; gap:6px; }
  .legend span { display:inline-block; width:10px; height:10px; border-radius:2px; margin:0 4px 0 10px; vertical-align:-1px; }
  #hint { position:fixed; bottom:10px; left:12px; color:var(--muted); font-size:12px; }
</style>
</head>
<body>
<div id="panel">
  <h1>DH3 Type L show house: PDF → 3D</h1>
  <p>Built automatically from the PDF's layers (walls and columns, doors and windows, stairs), keeping only thick lines as walls. No AI used. The upper floor height (+3.80 m) is assumed: it isn't in the PDF set.</p>
  <div class="row" id="floors">
    <button data-f="both" class="on">Both floors</button><button data-f="ground">Ground</button><button data-f="upper">Upper</button>
  </div>
  <div class="row"><label><input type="checkbox" id="glass" checked> Show glass</label></div>
  <div class="legend"><span style="background:#e3ddd3;margin-left:0"></span>Walls<span style="background:#8fd0e0"></span>Doors / windows<span style="background:#5aa65a"></span>Stairs</div>
</div>
<div id="hint">Drag to orbit · right-drag to pan · scroll to zoom</div>
<script type="importmap">
{ "imports": { "three": "https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js",
               "three/addons/": "https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/" } }
</script>
<script type="module">
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
const DATA = __DATA__;
const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.setSize(innerWidth, innerHeight);
document.body.appendChild(renderer.domElement);
const scene = new THREE.Scene();
scene.background = new THREE.Color(0xeef0f2);
const camera = new THREE.PerspectiveCamera(40, innerWidth / innerHeight, 0.1, 500);
camera.position.set(-22, 24, 26);
const controls = new OrbitControls(camera, renderer.domElement);
controls.target.set(0, 3, 0); controls.enableDamping = true;
scene.add(new THREE.HemisphereLight(0xffffff, 0xb9b4aa, 1.6));
const sun = new THREE.DirectionalLight(0xffffff, 1.6); sun.position.set(-20, 40, 15); scene.add(sun);
const ground = new THREE.Mesh(new THREE.PlaneGeometry(80, 50), new THREE.MeshStandardMaterial({ color: 0xdfe3e0 }));
ground.rotation.x = -Math.PI / 2; scene.add(ground);
const STYLE = {
  wall:   { color: 0xe3ddd3, opacity: 1,    edge: 0x8a8379 },
  glass:  { color: 0x8fd0e0, opacity: 0.35, edge: 0x4f9fb3 },
  window: { color: 0x8fd0e0, opacity: 0.35, edge: 0x4f9fb3 },
  stair:  { color: 0x5aa65a, opacity: 1,    edge: 0x2f6b2f },
};
const groups = { ground: new THREE.Group(), upper: new THREE.Group() };
const glassObjs = [];
for (const [key, segs] of Object.entries(DATA.segments)) {
  const [floor, cat] = key.split(':'); const st = STYLE[cat]; if (!st) continue;
  let z0 = DATA.levels[floor], z1 = DATA.tops[floor];
  if (cat === 'stair') z1 = z0 + 0.15;
  if (cat === 'window') z1 = z1 - 0.6;
  const pos = [], edges = [];
  for (const [x1, y1, x2, y2] of segs) {
    const a = [x1, z0, -y1], b = [x2, z0, -y2], c = [x2, z1, -y2], d = [x1, z1, -y1];
    pos.push(...a, ...b, ...c, ...a, ...c, ...d);
    edges.push(...d, ...c, ...a, ...b);
  }
  const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3)); g.computeVertexNormals();
  const m = new THREE.MeshStandardMaterial({ color: st.color, side: THREE.DoubleSide, transparent: st.opacity < 1, opacity: st.opacity, depthWrite: st.opacity === 1, roughness: 0.85 });
  const mesh = new THREE.Mesh(g, m);
  const eg = new THREE.BufferGeometry(); eg.setAttribute('position', new THREE.Float32BufferAttribute(edges, 3));
  const lines = new THREE.LineSegments(eg, new THREE.LineBasicMaterial({ color: st.edge }));
  groups[floor].add(mesh, lines);
  if (cat === 'glass' || cat === 'window') glassObjs.push(mesh, lines);
}
scene.add(groups.ground, groups.upper);
document.querySelectorAll('#floors button').forEach(btn => btn.onclick = () => {
  document.querySelectorAll('#floors button').forEach(b => b.classList.toggle('on', b === btn));
  const f = btn.dataset.f; groups.ground.visible = f !== 'upper'; groups.upper.visible = f !== 'ground';
});
document.getElementById('glass').onchange = e => glassObjs.forEach(o => o.visible = e.target.checked);
addEventListener('resize', () => { camera.aspect = innerWidth / innerHeight; camera.updateProjectionMatrix(); renderer.setSize(innerWidth, innerHeight); });
renderer.setAnimationLoop(() => { controls.update(); renderer.render(scene, camera); });
</script>
</body>
</html>
'''
open(sys.argv[1], 'w', encoding='utf-8').write(html.replace('__DATA__', json.dumps(data, separators=(',', ':'))))
print('written', sys.argv[1])
