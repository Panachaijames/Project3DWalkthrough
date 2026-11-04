"""Write the presidential suite test viewer: merged walls, the terrace parapet, the floor slab, room names,
Orbit / Walk / Ghost, the Camera tool and the build replay.
Usage: python make_html_pres.py <out.html>
Reads pres3d_merged.json and pres3d_stages.json (next to this script, from pres_build.py) and the shared viewer modules
viewer_modes.js and build_replay.js (../shared/ in the scratch layout, <project>/viewer-modes/ in the project)."""
import json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

def shared(name):
    for d in (HERE.parent / 'shared', HERE.parent.parent / 'viewer-modes', HERE.parent / 'viewer-modes'):
        if (d / name).exists():
            return (d / name).read_text(encoding='utf-8')
    raise SystemExit(f'{name} not found (expected in <project>/viewer-modes/)')

data = (HERE / 'pres3d_merged.json').read_text(encoding='utf-8')
S = json.loads((HERE / 'pres3d_stages.json').read_text(encoding='utf-8'))
S['floors']['suite']['lines'] = {k: [round(v, 2) for v in a] for k, a in S['floors']['suite']['lines'].items()}
S['floors']['suite']['pairs'] = {k: [round(v, 2) for v in q] for k, q in S['floors']['suite']['pairs'].items()}
modes, replay = shared('viewer_modes.js'), shared('build_replay.js')

html = r'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Presidential suite test</title>
<style>
  :root { --bg:#eef0f2; --panel:#ffffffee; --ink:#1d2329; --muted:#5b6670; --accent:#8a6d3b; --line:#d5dade; }
  html, body { margin:0; height:100%; background:var(--bg); font:14px/1.4 system-ui, -apple-system, "Segoe UI", sans-serif; color:var(--ink); overflow:hidden; }
  #panel { position:fixed; top:12px; left:12px; width:min(330px, calc(100vw - 48px)); max-height:calc(100vh - 60px); overflow:auto; background:var(--panel); border:1px solid var(--line); border-radius:10px; padding:12px 14px; box-shadow:0 2px 10px #0001; }
  h1 { font-size:15px; margin:0 0 4px; }
  p { margin:0 0 10px; color:var(--muted); font-size:12.5px; }
  .row { display:flex; gap:6px; flex-wrap:wrap; margin-bottom:8px; }
  button { border:1px solid var(--line); background:#fff; border-radius:7px; padding:5px 10px; cursor:pointer; font:inherit; font-size:13px; color:var(--ink); }
  button.on { background:var(--accent); border-color:var(--accent); color:#fff; }
  label { font-size:13px; display:flex; align-items:center; gap:6px; }
  .legend { font-size:12.5px; line-height:1.9; margin-top:8px; }
  .legend span { display:inline-block; width:10px; height:10px; border-radius:2px; margin:0 4px 0 8px; vertical-align:-1px; }
  #hint { position:fixed; bottom:10px; left:12px; right:12px; color:var(--muted); font-size:12px; }
  .room { position:fixed; transform:translate(-50%, -50%); font-size:11.5px; background:#ffffffd9; color:#1d2329; padding:1px 6px;
          border-radius:5px; border:1px solid #d5dade; pointer-events:none; white-space:nowrap; z-index:2; display:none; }
</style>
</head>
<body>
<div id="panel">
  <h1>Presidential suite (test): CAD → 3D</h1>
  <p>Built automatically from <b>layout presidential xx.dwg</b>, a drawing by another office: walls drawn on layer 0 with the furniture, layer names in Vietnamese. Walls are found by pairing parallel lines, not by layer; five furniture areas were set aside by hand. Floor to floor 3.00 m, as given for the project. No AI used.</p>
  <div class="row" id="shows">
    <label><input type="checkbox" id="plates" checked> Floor slab</label>
    <label><input type="checkbox" id="parapet" checked> Terrace parapet</label>
    <label><input type="checkbox" id="rooms" checked> Room names</label>
  </div>
  <div class="legend"><span style="background:#e3ddd3;margin-left:0"></span>Walls (3.00 m)<span style="background:#d9b98a"></span>Parapet under the railing (1.10 m)<span style="background:#d4d8d2"></span>Floor slab</div>
</div>
<div id="hint"></div>
<script type="importmap">
{ "imports": { "three": "https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js",
               "three/addons/": "https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/",
               "three-mesh-bvh": "https://cdn.jsdelivr.net/npm/three-mesh-bvh@0.8.3/build/index.module.js" } }
</script>
<script type="module">
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { mergeGeometries, toCreasedNormals } from 'three/addons/utils/BufferGeometryUtils.js';
import { computeBoundsTree, acceleratedRaycast } from 'three-mesh-bvh';
THREE.BufferGeometry.prototype.computeBoundsTree = computeBoundsTree;
THREE.Mesh.prototype.raycast = acceleratedRaycast;
const D = __DATA__;
const S = __STAGES__;
const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.setSize(innerWidth, innerHeight);
document.body.appendChild(renderer.domElement);
const scene = new THREE.Scene();
scene.background = new THREE.Color(0xeef0f2);
const camera = new THREE.PerspectiveCamera(40, innerWidth / innerHeight, 0.1, 600);
camera.position.set(-26, 32, 30);
const controls = new OrbitControls(camera, renderer.domElement);
controls.target.set(0, 1.2, 0);
controls.enableDamping = true;
scene.add(new THREE.HemisphereLight(0xffffff, 0xe4dfd6, 1.6));
const sun = new THREE.DirectionalLight(0xffffff, 1.6);
sun.position.set(-20, 40, 15);
scene.add(sun);

const LV = D.levels.suite, H = D.tops.suite - D.levels.suite, HP = D.parapetHeight;
const STYLE = { wall: { color: 0xe3ddd3, edge: 0x7f786e }, parapet: { color: 0xd9b98a, edge: 0x9a7a4a } };
const group = new THREE.Group();
const colliders = [], walkables = [], rise = [], late = [], parapetObjs = [], plateObjs = [];

// When each wall run starts to rise in the build replay: a sweep from west to east (0..1, from the run's centre).
let sx0 = Infinity, sx1 = -Infinity, sy0 = Infinity, sy1 = -Infinity;
for (const rings of Object.values(D.solids)) for (const r of rings) for (const [x, y] of r.o) {
  sx0 = Math.min(sx0, x); sx1 = Math.max(sx1, x); sy0 = Math.min(sy0, y); sy1 = Math.max(sy1, y);
}
function sweep(r) {
  let cx = 0, cy = 0;
  r.o.forEach(([x, y]) => { cx += x; cy += y; });
  cx /= r.o.length; cy /= r.o.length;
  return Math.max(0, Math.min(1, 0.8 * (cx - sx0) / (sx1 - sx0 || 1) + 0.2 * (sy1 - cy) / (sy1 - sy0 || 1)));
}
// Outline (+ inner loops) extruded. Plan (x, y) -> three.js (x, z = -y); height -> y.
function extrude(rings, z0, h) {
  const parts = rings.map(r => {
    const shape = new THREE.Shape(r.o.map(([x, y]) => new THREE.Vector2(x, y)));
    for (const hole of r.h) shape.holes.push(new THREE.Path(hole.map(([x, y]) => new THREE.Vector2(x, y))));
    const g = new THREE.ExtrudeGeometry(shape, { depth: h, bevelEnabled: false, curveSegments: 1 });
    g.rotateX(-Math.PI / 2);
    g.translate(0, z0, 0);
    g.setAttribute('aDelay', new THREE.BufferAttribute(new Float32Array(g.attributes.position.count).fill(sweep(r)), 1));
    return g;
  });
  const merged = mergeGeometries(parts, false);
  parts.forEach(p => p.dispose());
  return merged;
}
for (const kind of ['wall', 'parapet']) {
  const rings = D.solids['suite:' + kind] || [];
  if (!rings.length) continue;
  const merged = extrude(rings, LV, kind === 'wall' ? H : HP);
  const g = toCreasedNormals(merged, THREE.MathUtils.degToRad(40)), e = new THREE.EdgesGeometry(merged, 40);
  merged.dispose();
  g.computeBoundsTree();
  const mesh = new THREE.Mesh(g, new THREE.MeshStandardMaterial({ color: STYLE[kind].color, roughness: 0.85, side: THREE.DoubleSide }));
  const lines = new THREE.LineSegments(e, new THREE.LineBasicMaterial({ color: STYLE[kind].edge, transparent: true, opacity: 0.6 }));
  group.add(mesh, lines);
  colliders.push(mesh);
  rise.push({ mesh, edges: lines, scales: kind === 'wall' });          // the parapet stays 1.10 m whatever the wall height
  if (kind === 'parapet') parapetObjs.push(mesh, lines);
}
// The floor slab: 0.25 m under the floor level.
for (const r of D.plates.suite) {
  const g = extrude([r], LV - 0.25, 0.25);
  g.computeVertexNormals(); g.computeBoundsTree();
  const m = new THREE.Mesh(g, new THREE.MeshStandardMaterial({ color: 0xd4d8d2, roughness: 0.95 }));
  group.add(m); walkables.push(m); late.push(m); plateObjs.push(m);
}
scene.add(group);

const check = id => document.getElementById(id).checked;
function applyChecks() {
  plateObjs.forEach(o => { o.visible = check('plates'); });
  parapetObjs.forEach(o => { o.visible = check('parapet'); });
}
['plates', 'parapet'].forEach(id => { document.getElementById(id).onchange = applyChecks; });

__MODES__

__REPLAY__

const FLOORS = [{ key: 'suite', name: 'Suite (FL-01)', level: LV, stack: 'suite', group, colliders, walkables }];
const modes = installViewerModes({
  scene, camera, renderer, controls, project: 'Presidential',
  panel: document.getElementById('panel'), anchor: document.getElementById('shows'), hint: document.getElementById('hint'),
  restoreVisibility: () => { group.visible = true; }, floors: FLOORS,
});

// ---------------------------------------------------------------- the build replay, with this drawing's numbers
const fmt = n => Math.round(n).toLocaleString('en-US');
const st = S.stats;
const replay = installBuildReplay({
  scene, camera, renderer, controls, modes, panel: document.getElementById('panel'), project: 'Presidential',
  intro: { title: S.source.file, facts: [
    'One floor plan (FL-01), in millimetres; the corridor lines to the right are cut off',
    `${fmt(st.read)} drawing items in the suite area, on ${st.planLayers} layers`,
    `Walls are on layer 0 with the furniture: found by pairing parallel lines, not by layer`,
    `Floor to floor 3.00 m, as given for the project`,
  ] },
  layersTitle: 'How the drawing was read',
  layers: [['Walls', 'layer 0, straight lines drawn directly (not inside blocks), paired 60–330 mm and 450–520 mm apart'],
           ['Doors and windows', 'KT-Cua'], ['Balcony railing', 'KT-Lancan (the wall band under it becomes the 1.10 m parapet)'],
           ['Set aside by hand', st.excludedAreas.join('; ')],
           ['Ignored', `${st.layers.noise.length} layers: furniture, fixtures, plants, dimensions, symbols`]],
  floors: [{ key: 'suite', name: 'Suite (FL-01)', level: LV, height: H, sheet: S.floors.suite.sheet, group,
             lines: S.floors.suite.lines, pieces: S.floors.suite.pairs,
             rings: { wall: D.solids['suite:wall'] || [], parapet: D.solids['suite:parapet'] || [] }, rise, late }],
  colors: { wall: 0x7a6650, door: 0xc0702a, railing: 0x2f86a8 },
  steps: {
    read: { title: 'Read the drawing', caption: () => `${fmt(st.read)} drawing items in the suite area, on ${st.planLayers} layers, in millimetres.` },
    sort: { title: 'Sort the line work', caption: () => `This office keeps walls on layer 0 with the furniture, so walls are found by shape: ${fmt(st.kept.wall)} straight lines drawn on layer 0 are wall candidates. Doors on KT-Cua (${fmt(st.kept.door)} lines), the balcony railing on KT-Lancan (${fmt(st.kept.railing)}). ${fmt(st.ignoredLines)} lines of furniture, fixtures, plants and dimensions are ignored.` },
    align: { title: 'Check the floor', caption: s => `One floor in this drawing (FL-01). Floor to floor 3.00 m, as given for the project; the floor is at ${s.suite.level.toFixed(2)} m.` },
    pair: { title: 'Pair the wall faces', caption: () => `Parallel lines a wall's thickness apart are paired: ${fmt(st.pieces.wall)} wall pieces (60–330 mm) and ${fmt(st.pieces.parapet)} edge-band pieces (500 mm). ${fmt(st.excluded)} pieces in five furniture areas were set aside by hand (tables, the bar, a bath, stair treads).` },
    merge: { title: 'Merge into wall runs', caption: () => `The pieces merge into ${st.runs.wall} wall runs. The band under the balcony railing becomes the terrace parapet (${st.runs.parapet} pieces).` },
    raise: { title: 'Raise the walls', caption: s => `Walls rise to ${s.suite.height.toFixed(2)} m (floor to floor); the parapet to ${HP.toFixed(2)} m.` },
    finish: { title: 'Slab and room names', caption: () => `The floor slab goes in. Done: ${st.runs.wall} wall runs and the terrace parapet; ${st.rooms} room names from the drawing are shown.` },
  },
  applySettings: s => { FLOORS[0].level = s.suite.level; },
  restore: () => { group.visible = true; applyChecks(); },
});

// Room names from the drawing, shown over the model in Orbit.
const labels = D.rooms.map(r => {
  const el = document.createElement('div'); el.className = 'room'; el.textContent = r.name; document.body.appendChild(el);
  return { el, p: new THREE.Vector3(r.x, 1.4, -r.y) };
});
const v = new THREE.Vector3();
function placeLabels() {
  const show = check('rooms') && modes.mode === 'orbit' && replay.phase === 'done';
  for (const L of labels) {
    v.copy(L.p); v.y = FLOORS[0].level + 1.4; v.project(camera);
    const on = show && v.z < 1 && Math.abs(v.x) < 1.1 && Math.abs(v.y) < 1.1;
    L.el.style.display = on ? 'block' : 'none';
    if (on) { L.el.style.left = ((v.x + 1) / 2 * innerWidth) + 'px'; L.el.style.top = ((1 - v.y) / 2 * innerHeight) + 'px'; }
  }
}
window.__host = { group, rise, labels };      // read-outs for tests
applyChecks();
modes.applyUrl();
renderer.setAnimationLoop(() => { replay.tick(); modes.tick(); renderer.render(scene, camera); placeLabels(); });
</script>
</body>
</html>
'''

out = (html.replace('__DATA__', data).replace('__STAGES__', json.dumps(S, separators=(',', ':'), ensure_ascii=False))
           .replace('__MODES__', modes).replace('__REPLAY__', replay))
Path(sys.argv[1]).write_text(out, encoding='utf-8')
print('written', sys.argv[1], round(len(out) / 1024), 'KB')
