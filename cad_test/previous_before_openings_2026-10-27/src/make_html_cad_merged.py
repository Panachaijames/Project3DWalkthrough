"""Write the DWG test house viewer: merged walls, floor plates, Orbit / Walk / Ghost, the Camera tool and the build replay.
Usage: python make_html_cad_merged.py <out.html>
Reads house3d_merged.json and house3d_stages.json (next to this script) and the shared viewer modules
viewer_modes.js and build_replay.js (../shared/ in the scratch layout, <project>/viewer-modes/ in the project)."""
import json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

def shared(name):
    for d in (HERE.parent / 'shared', HERE.parent.parent / 'viewer-modes', HERE.parent / 'viewer-modes'):
        if (d / name).exists():
            return (d / name).read_text(encoding='utf-8')
    raise SystemExit(f'{name} not found (expected in <project>/viewer-modes/)')

data = (HERE / 'house3d_merged.json').read_text(encoding='utf-8')
modes = shared('viewer_modes.js')
replay = shared('build_replay.js')

# Build replay data: what each build step saw (build_stages.py). Keep the longest ignored lines only, and round
# to the centimetre: it is for watching, not measuring. About 0.5 MB in all.
NOISE_LINES = 6000
S = json.loads((HERE / 'house3d_stages.json').read_text(encoding='utf-8'))
for f in S['floors'].values():
    f['lines'] = {k: [round(v, 2) for v in (a[:NOISE_LINES * 4] if k == 'noise' else a)] for k, a in f['lines'].items()}
    f['pairs'] = {k: [round(v, 2) for v in q] for k, q in f['pairs'].items()}
L = S['stats']['layers']               # the layers found in the two plan areas, by what the build made of them

def layer_list(names):            # 'XR_L44 Plan$0$A-WALL' is a layer from a linked drawing: show it as A-WALL
    plain, linked = [], 0
    for n in names:
        if '$0$' in n:
            linked += 1; n = n.split('$0$')[-1]
        if n not in plain: plain.append(n)
    return ', '.join(plain) + (f' (incl. {linked} from linked drawings)' if linked else '')

S['layers'] = [['Walls', layer_list(L['wall'])], ['Glass', layer_list(L['glass'])],
               ['Windows', layer_list(L['window'])], ['Stairs', layer_list(L['stair'])],
               ['Ignored', f"{len(L['ignored'])} other layers: furniture, floor patterns, doors, grid, dimensions, labels"]]
S['source']['layersUsed'] = S['stats']['planLayers']     # layers with anything in the two plan areas

html = r'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>CAD to 3D test</title>
<style>
  :root { --bg:#eef0f2; --panel:#ffffffee; --ink:#1d2329; --muted:#5b6670; --accent:#c9773e; --line:#d5dade; }
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
</style>
</head>
<body>
<div id="panel">
  <h1>Test Sukhumvit Residence: CAD → 3D</h1>
  <p>Built automatically from the DWG. Each wall's two face lines are paired, filled and merged into one solid per wall run, so there are no seams. Floor heights come from the elevations (+0.90 m, +4.80 m). No AI used.</p>
  <div class="row" id="floors">
    <button data-f="both" class="on">Both floors</button><button data-f="ground">Ground</button><button data-f="upper">Upper</button>
  </div>
  <div class="row">
    <label><input type="checkbox" id="plates" checked> Floor plates</label>
    <label><input type="checkbox" id="glass" checked> Glass</label>
    <label><input type="checkbox" id="single" checked> Single-line items</label>
  </div>
  <div class="legend"><span style="background:#e3ddd3;margin-left:0"></span>Walls<span style="background:#8fd0e0"></span>Windows / glass<span style="background:#5aa65a"></span>Stairs<span style="background:#e0a458"></span>Single line: wall, railing or edge?<span style="background:#d4d8d2"></span>Floor plate (approximate outline)</div>
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
const camera = new THREE.PerspectiveCamera(40, innerWidth / innerHeight, 0.1, 500);
camera.position.set(-28, 30, 34);
const controls = new OrbitControls(camera, renderer.domElement);
controls.target.set(0, 3, 0);
controls.enableDamping = true;
scene.add(new THREE.HemisphereLight(0xffffff, 0xe4dfd6, 1.6));
const sun = new THREE.DirectionalLight(0xffffff, 1.6);
sun.position.set(-20, 40, 15);
scene.add(sun);
const ground = new THREE.Mesh(new THREE.PlaneGeometry(80, 50), new THREE.MeshStandardMaterial({ color: 0xdfe3e0 }));
ground.rotation.x = -Math.PI / 2;
scene.add(ground);

const STYLE = {
  wall:   { color: 0xe3ddd3, edge: 0x7f786e, opacity: 1 },
  glass:  { color: 0x8fd0e0, edge: 0x4f9fb3, opacity: 0.35 },
  single: { color: 0xe0a458, edge: 0xa86f2c, opacity: 0.9 },
};
const groups = { ground: new THREE.Group(), upper: new THREE.Group() };
const colliders = { ground: [], upper: [] }, walkables = { ground: [], upper: [] };
const glassObjs = [], singleObjs = [], plateObjs = [], plinths = [];
const rise = { ground: [], upper: [] }, late = { ground: [], upper: [] };      // for the build replay

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
function solids(rings, z0, h) {
  const merged = extrude(rings, z0, h);
  // Smooth shading across gentle bends (curved walls look like one surface); sharp corners stay crisp.
  const smooth = toCreasedNormals(merged, THREE.MathUtils.degToRad(40));
  // Outline only real corners (> 40 deg), not the small steps along a curve.
  const edges = new THREE.EdgesGeometry(merged, 40);
  merged.dispose();
  return [smooth, edges];
}

for (const [key, rings] of Object.entries(D.solids)) {
  if (!rings.length) continue;
  const [floor, kind] = key.split(':');
  const st = STYLE[kind];
  const z0 = D.levels[floor], top = D.tops[floor];
  const h = kind === 'single' ? 1.0 : kind === 'glass' ? (top - z0) - 0.6 : (top - z0);
  const [g, e] = solids(rings, z0, h);
  g.computeBoundsTree();
  const mesh = new THREE.Mesh(g, new THREE.MeshStandardMaterial({ color: st.color, roughness: 0.85, side: THREE.DoubleSide,
    transparent: st.opacity < 1, opacity: st.opacity, depthWrite: st.opacity === 1 }));
  const lines = new THREE.LineSegments(e, new THREE.LineBasicMaterial({ color: st.edge, transparent: true, opacity: 0.6 }));
  groups[floor].add(mesh, lines);
  colliders[floor].push(mesh);
  rise[floor].push({ mesh, edges: lines, scales: kind !== 'single' });   // railings stay 1 m whatever the wall height
  if (kind === 'glass') glassObjs.push(mesh, lines);
  if (kind === 'single') singleObjs.push(mesh, lines);
}

// Floor plates: the ground plate runs from the ground up to the floor level (a plinth), upper plates are 0.25 m.
for (const [floor, rings] of Object.entries(D.plates || {})) {
  if (!rings.length) continue;
  const lvl = D.levels[floor], thick = floor === 'ground' ? lvl : 0.25;
  const g = extrude(rings, lvl - thick, thick);
  g.computeVertexNormals();
  g.computeBoundsTree();
  const m = new THREE.Mesh(g, new THREE.MeshStandardMaterial({ color: 0xd4d8d2, roughness: 0.95 }));
  groups[floor].add(m);
  walkables[floor].push(m);
  plateObjs.push(m);
  late[floor].push(m);
  if (floor === 'ground') plinths.push(m);
}

// Stairs stay as low line panels (tread outlines).
for (const [floor, segs] of Object.entries(D.stairs)) {
  const z0 = D.levels[floor], pos = [];
  for (const [x1, y1, x2, y2] of segs) {
    const a = [x1, z0, -y1], b = [x2, z0, -y2], c = [x2, z0 + 0.15, -y2], d = [x1, z0 + 0.15, -y1];
    pos.push(...a, ...b, ...c, ...a, ...c, ...d);
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  g.computeVertexNormals();
  const m = new THREE.Mesh(g, new THREE.MeshStandardMaterial({ color: 0x5aa65a, side: THREE.DoubleSide }));
  groups[floor].add(m);
  late[floor].push(m);
}
scene.add(groups.ground, groups.upper);

let floorMode = 'both';
function applyFloor() {
  groups.ground.visible = floorMode !== 'upper';
  groups.upper.visible = floorMode !== 'ground';
}
const check = id => document.getElementById(id).checked;
function applyChecks() {
  plateObjs.forEach(o => { o.visible = check('plates'); });
  glassObjs.forEach(o => { o.visible = check('glass'); });
  singleObjs.forEach(o => { o.visible = check('single'); });
}

// Floor buttons: in Walk they show (and change) the floor you are on; otherwise they show or hide floors.
function markFloors(st) {
  const key = st.mode === 'walk' ? st.floor : floorMode;
  document.querySelectorAll('#floors button').forEach(b => b.classList.toggle('on', b.dataset.f === key));
}

__MODES__

__REPLAY__

const FLOORS = [
  { key: 'ground', name: 'Ground floor', level: D.levels.ground, stack: 'house', group: groups.ground, colliders: colliders.ground, walkables: walkables.ground },
  { key: 'upper', name: 'Upper floor', level: D.levels.upper, stack: 'house', group: groups.upper, colliders: colliders.upper, walkables: walkables.upper },
];
const modes = installViewerModes({
  scene, camera, renderer, controls, project: 'Sukhumvit',
  panel: document.getElementById('panel'), anchor: document.getElementById('floors'), hint: document.getElementById('hint'),
  restoreVisibility: applyFloor, onChange: markFloors, floors: FLOORS,
});

document.querySelectorAll('#floors button').forEach(btn => {
  btn.onclick = () => {
    const f = btn.dataset.f;
    if (modes.mode === 'walk') { modes.goToFloor(f === 'both' ? 'ground' : f); return; }
    floorMode = f;
    applyFloor();
    markFloors({ mode: modes.mode });
  };
});
['plates', 'glass', 'single'].forEach(id => { document.getElementById(id).onchange = applyChecks; });
applyFloor();

// ---------------------------------------------------------------- the build replay, with this drawing's numbers
const fmt = n => Math.round(n).toLocaleString('en-US');
const lv = x => (x >= 0 ? '+' : '') + x.toFixed(2) + ' m';
const pct = x => Math.round(x * 100) + '%';
const FS = S.stats.floors, both = fn => fn(FS.ground) + fn(FS.upper);
const kept = c => both(f => f.kept[c]);
const replay = installBuildReplay({
  scene, camera, renderer, controls, modes, panel: document.getElementById('panel'), project: 'Sukhumvit',
  intro: { title: S.source.file, facts: [
    'Two floor plans side by side on one sheet, in millimetres',
    `${fmt(both(f => f.read))} drawing items in the plan areas, on ${S.source.layersUsed} layers in use`,
    `Floors lined up by ${S.stats.gridLabels} grid labels; levels from the elevation tags`,
  ] },
  layers: S.layers,
  floors: ['ground', 'upper'].map(k => ({
    key: k, name: k === 'ground' ? 'Ground floor' : 'Upper floor', level: D.levels[k], height: D.tops[k] - D.levels[k],
    sheet: S.floors[k].sheet, group: groups[k], lines: S.floors[k].lines, pieces: S.floors[k].pairs,
    rings: { wall: D.solids[k + ':wall'] || [], glass: D.solids[k + ':glass'] || [] }, rise: rise[k], late: late[k],
  })),
  hide: [ground],
  colors: { wall: 0x7a6650, glass: 0x2f86a8, window: 0x4a9cc0, stair: 0x2e8b47 },
  steps: {
    read: { title: 'Read the drawing', caption: () => `${fmt(both(f => f.read))} drawing items in the two plan areas, on ${S.source.layersUsed} layers, in millimetres.` },
    sort: { title: 'Sort the layers', caption: () => `Walls ${fmt(kept('wall'))} lines, windows and glass ${fmt(kept('window') + kept('glass'))}, stairs ${fmt(kept('stair'))}. ${fmt(both(f => f.ignoredLines))} lines ignored: furniture, floor patterns, doors, grid and dimensions.` },
    align: { title: 'Line up the floors', caption: st => `The upper plan sits beside the ground plan on the sheet. ${S.stats.gridLabels} grid labels match on both, so it moves ${S.floors.upper.sheet[0].toFixed(2)} m onto the ground plan and rises to its level: ground ${lv(st.ground.level)}, upper ${lv(st.upper.level)}.` },
    pair: { title: 'Pair the wall faces', caption: () => `Each wall is drawn as two lines. Pairing them gives ${fmt(both(f => f.pieces.wall))} wall pieces and ${fmt(both(f => f.pieces.glass))} glass pieces; ${pct(FS.ground.pairedShare)} of the ground-floor wall lines and ${pct(FS.upper.pairedShare)} of the upper ones found their partner.` },
    merge: { title: 'Merge into wall runs', caption: () => `${fmt(both(f => f.pieces.wall + f.pieces.glass))} pieces merge into ${both(f => f.runs.wall)} wall runs and ${both(f => f.runs.glass)} glass runs: one solid each, no seams.` },
    raise: { title: 'Raise the walls', caption: st => `The walls rise to their height: ground floor ${st.ground.height.toFixed(2)} m, upper floor ${st.upper.height.toFixed(2)} m.` },
    finish: { title: 'Floors, stairs, done', caption: () => `Floor plates and stairs go in. Done: 2 floors, ${both(f => f.runs.wall)} wall runs, ${both(f => f.runs.glass)} glass runs. The real build takes seconds; this replay slows it down so you can follow it.` },
  },
  applySettings: st => {
    FLOORS.forEach(f => { f.level = st[f.key].level; });
    // The ground plate is a plinth from the ground up to the floor: keep its foot on the ground at any floor level.
    const lv0 = D.levels.ground, lv = st.ground.level;
    if (lv0 > 0) plinths.forEach(m => { m.scale.y = Math.max(0.01, lv / lv0); m.position.y = lv0 - lv; });
  },
  restore: () => { applyFloor(); applyChecks(); },
});
window.__host = { groups, rise, plinths };      // read-outs for the browser tests
modes.applyUrl();
renderer.setAnimationLoop(() => { replay.tick(); modes.tick(); renderer.render(scene, camera); });
</script>
</body>
</html>
'''

out = (html.replace('__DATA__', data).replace('__STAGES__', json.dumps(S, separators=(',', ':')))
           .replace('__MODES__', modes).replace('__REPLAY__', replay))
Path(sys.argv[1]).write_text(out, encoding='utf-8')
print('written', sys.argv[1], round(len(out) / 1024), 'KB')
