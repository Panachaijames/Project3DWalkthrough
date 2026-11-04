import sys

data = open('srisawan3d.json', encoding='utf-8').read()

html = r'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Srisawan 3D viewer</title>
<style>
  :root { --bg:#eef2f5; --panel:#ffffffee; --ink:#1d2731; --muted:#5a6772; --accent:#2f6f8f; --line:#d3dbe1; }
  html, body { margin:0; height:100%; background:var(--bg); font:14px/1.4 system-ui, -apple-system, "Segoe UI", sans-serif; color:var(--ink); overflow:hidden; }
  #panel { position:fixed; top:12px; left:12px; width:min(340px, calc(100vw - 48px)); background:var(--panel); border:1px solid var(--line); border-radius:10px; padding:12px 14px; box-shadow:0 2px 10px #0001; }
  h1 { font-size:15px; margin:0 0 4px; }
  p { margin:0 0 10px; color:var(--muted); font-size:12.5px; }
  .label { font-size:11px; letter-spacing:.06em; text-transform:uppercase; color:var(--muted); margin:8px 0 4px; }
  .row { display:flex; gap:6px; flex-wrap:wrap; }
  button { border:1px solid var(--line); background:#fff; border-radius:7px; padding:5px 10px; cursor:pointer; font:inherit; font-size:13px; color:var(--ink); }
  button.on { background:var(--accent); border-color:var(--accent); color:#fff; }
  label { font-size:13px; display:flex; align-items:center; gap:6px; }
  .legend { margin-top:10px; font-size:12.5px; line-height:1.9; }
  .legend span { display:inline-block; width:10px; height:10px; border-radius:2px; margin:0 4px 0 8px; vertical-align:-1px; }
  #tip { position:fixed; pointer-events:none; background:#1d2731; color:#fff; font-size:12.5px; padding:4px 8px; border-radius:6px; display:none; white-space:nowrap; }
  #hint { position:fixed; bottom:10px; left:12px; right:12px; color:var(--muted); font-size:12px; }
  #note { margin-top:8px; font-size:12px; color:var(--muted); }
</style>
</head>
<body>
<div id="panel">
  <h1>Srisawan Hospital: 3D from the traced plans</h1>
  <p>Built from <b>srisawan-rebuild/model_geometry.json</b> with the same sizes as the 3ds Max script: walls 4.00 m high, floor 2 at +5.00 m, scale from the 1.20 m lift door (19 px). Traced from plan images, not from DWG.</p>
  <div class="label">Floor</div>
  <div class="row" id="floors">
    <button data-f="both" class="on">Floors 1 + 2</button><button data-f="L1">Floor 1</button><button data-f="L2">Floor 2</button><button data-f="F6">Floor 6</button>
  </div>
  <div class="label">View</div>
  <div class="row" id="views"><button data-v="3d" class="on">3D</button><button data-v="top">Top</button></div>
  <div class="label">Show</div>
  <div class="row">
    <label><input type="checkbox" id="slabs" checked> Slabs</label>
    <label><input type="checkbox" id="shell" checked> Outer walls &amp; glass</label>
  </div>
  <div class="legend">
    <span style="background:#dcd8cf;margin-left:0"></span>Walls<span style="background:#9ea8af"></span>Lift core<span style="background:#7dc2d3"></span>Garden glass<span style="background:#b9c1c6"></span>Slab
  </div>
  <div id="note"></div>
</div>
<div id="tip"></div>
<div id="hint">Drag to orbit · right-drag to pan · scroll to zoom · hover a wall to see its zone</div>
<script type="importmap">
{ "imports": { "three": "https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js",
               "three/addons/": "https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/" } }
</script>
<script type="module">
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
const D = __DATA__;
const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.setSize(innerWidth, innerHeight);
document.body.appendChild(renderer.domElement);
const scene = new THREE.Scene();
scene.background = new THREE.Color(0xeef2f5);
const camera = new THREE.PerspectiveCamera(38, innerWidth / innerHeight, 0.5, 1000);
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
scene.add(new THREE.HemisphereLight(0xffffff, 0xaab4bb, 1.5));
const sun = new THREE.DirectionalLight(0xffffff, 1.7);
sun.position.set(-40, 80, 30);
scene.add(sun);

const COLORS = { wall: 0xdcd8cf, core: 0x9ea8af, envelope: 0xd2cdc3, glass: 0x7dc2d3 };
const KIND_NAME = { wall: 'wall', core: 'lift core', envelope: 'outer wall', glass: 'garden glazing' };
const FLOOR_NAME = { L1: 'Floor 1', L2: 'Floor 2', F6: 'Floor 6' };
const groups = { L1: new THREE.Group(), L2: new THREE.Group(), F6: new THREE.Group() };
const shell = [], slabMeshes = [], pickable = [];

// Plan (x, y) in metres -> three.js (x, z = -y); height -> y.
// Each wall is a box: 6 quad faces = 12 triangles, so faceIndex / 12 gives the wall's index.
function boxes(list) {
  const pos = [], edges = [];
  const V = (x, y, z) => [x, z, -y];
  for (const [x1, y1, x2, y2, t, z0, h] of list) {
    const dx = x2 - x1, dy = y2 - y1, L = Math.hypot(dx, dy);
    const ox = -dy / L * t / 2, oy = dx / L * t / 2;
    const p = [[x1 - ox, y1 - oy], [x2 - ox, y2 - oy], [x2 + ox, y2 + oy], [x1 + ox, y1 + oy]];
    const lo = p.map(([x, y]) => V(x, y, z0)), hi = p.map(([x, y]) => V(x, y, z0 + h));
    const quad = (a, b, c, d) => pos.push(...a, ...b, ...c, ...a, ...c, ...d);
    quad(hi[0], hi[1], hi[2], hi[3]);
    quad(lo[3], lo[2], lo[1], lo[0]);
    for (let i = 0; i < 4; i++) {
      const j = (i + 1) % 4;
      quad(lo[i], lo[j], hi[j], hi[i]);
      edges.push(...hi[i], ...hi[j], ...lo[i], ...hi[i]);
    }
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  g.computeVertexNormals();
  const e = new THREE.BufferGeometry();
  e.setAttribute('position', new THREE.Float32BufferAttribute(edges, 3));
  return [g, e];
}

for (const [key, list] of Object.entries(D.boxes)) {
  const [floor, kind] = key.split(':');
  const [g, e] = boxes(list);
  const glass = kind === 'glass';
  const mesh = new THREE.Mesh(g, new THREE.MeshStandardMaterial({
    color: COLORS[kind], roughness: 0.9, side: THREE.DoubleSide,
    transparent: glass, opacity: glass ? 0.3 : 1, depthWrite: !glass,
  }));
  mesh.userData = { floor, kind, info: D.info[key] };
  const lines = new THREE.LineSegments(e, new THREE.LineBasicMaterial({ color: glass ? 0x4f9fb3 : 0x77716a, transparent: true, opacity: 0.55 }));
  groups[floor].add(mesh, lines);
  pickable.push(mesh);
  if (kind === 'glass' || kind === 'envelope') shell.push(mesh, lines);
}

// Slabs: outline with real holes (floor 2: 2 voids + 6 core openings), 0.25 m thick, as in the 3ds Max script.
for (const [floor, sl] of Object.entries(D.slabs)) {
  const shape = new THREE.Shape(sl.outer.map(([x, y]) => new THREE.Vector2(x, y)));
  for (const h of sl.holes) shape.holes.push(new THREE.Path(h.map(([x, y]) => new THREE.Vector2(x, y))));
  const g = new THREE.ExtrudeGeometry(shape, { depth: 0.25, bevelEnabled: false });
  g.rotateX(-Math.PI / 2);
  g.translate(0, sl.z, 0);
  const m = new THREE.Mesh(g, new THREE.MeshStandardMaterial({ color: 0xb9c1c6, roughness: 0.95 }));
  groups[floor].add(m);
  slabMeshes.push(m);
}
Object.values(groups).forEach(g => scene.add(g));

const NOTES = {
  both: 'Floor 1 at 0.00 m, floor 2 at +5.00 m. Both share the same lift-core position. Floor 2 has 2 voids ("open to below") and 6 core openings in its slab.',
  L1: 'Floor 1 at 0.00 m: North Imaging, East ER/Ortho, South Reception, West Medicine, West/South Pharmacy.',
  L2: 'Floor 2 at +5.00 m: North Clinics, East Checkup/GI, South EENT/PT, West Women, West Pediatric/Pharmacy. The holes in the slab are the 2 voids and 6 core openings.',
  F6: 'Floor 6 (from floor6-dxf), shown on its own: it is measured from a different lift-core point and its height is not given, so it is not stacked. Interior walls only, drawn from wall centre lines, 4 m high.',
};
let floorMode = 'both', viewMode = '3d';

function frame() {
  const size = floorMode === 'F6' ? Math.max(...D.size6) : Math.max(...D.size);
  if (viewMode === 'top') {
    camera.position.set(0, size * 1.35, 0.01);
    controls.target.set(0, 0, 0);
  } else {
    camera.position.set(-size * 0.75, size * 0.72, size * 0.8);
    controls.target.set(0, 3, 0);
  }
  controls.update();
}

function applyFloor() {
  groups.L1.visible = floorMode === 'both' || floorMode === 'L1';
  groups.L2.visible = floorMode === 'both' || floorMode === 'L2';
  groups.F6.visible = floorMode === 'F6';
  document.getElementById('note').textContent = NOTES[floorMode];
}

function bind(id, attr, fn) {
  document.querySelectorAll('#' + id + ' button').forEach(b => {
    b.onclick = () => {
      document.querySelectorAll('#' + id + ' button').forEach(x => x.classList.toggle('on', x === b));
      fn(b.dataset[attr]);
    };
  });
}
bind('floors', 'f', f => {
  const was = floorMode;
  floorMode = f;
  applyFloor();
  if ((was === 'F6') !== (f === 'F6')) frame();
});
bind('views', 'v', v => { viewMode = v; frame(); });
document.getElementById('slabs').onchange = e => slabMeshes.forEach(m => { m.visible = e.target.checked; });
document.getElementById('shell').onchange = e => shell.forEach(o => { o.visible = e.target.checked; });

// Hover: show the floor, zone and type of the wall under the mouse.
const ray = new THREE.Raycaster(), mouse = new THREE.Vector2(), tip = document.getElementById('tip');
addEventListener('pointermove', ev => {
  mouse.set(ev.clientX / innerWidth * 2 - 1, -(ev.clientY / innerHeight) * 2 + 1);
  ray.setFromCamera(mouse, camera);
  const visible = pickable.filter(m => m.visible && m.parent.visible);
  const hit = ray.intersectObjects(visible, false)[0];
  if (hit) {
    const u = hit.object.userData;
    const zone = u.info[Math.floor(hit.faceIndex / 12)] || '';
    tip.textContent = FLOOR_NAME[u.floor] + ' · ' + zone + ' · ' + KIND_NAME[u.kind];
    tip.style.left = (ev.clientX + 14) + 'px';
    tip.style.top = (ev.clientY + 12) + 'px';
    tip.style.display = 'block';
  } else {
    tip.style.display = 'none';
  }
});
addEventListener('resize', () => {
  camera.aspect = innerWidth / innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(innerWidth, innerHeight);
});
applyFloor();
frame();
renderer.setAnimationLoop(() => { controls.update(); renderer.render(scene, camera); });
</script>
</body>
</html>
'''

open(sys.argv[1], 'w', encoding='utf-8').write(html.replace('__DATA__', data))
print('written', sys.argv[1], round((len(html) + len(data)) / 1024), 'KB')
