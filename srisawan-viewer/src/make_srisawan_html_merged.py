"""Write the Srisawan hospital viewer: merged walls, slabs, Orbit / Walk / Ghost, the Camera tool and the build replay.
Usage: python make_srisawan_html_merged.py <out.html>
Reads srisawan3d_merged.json and srisawan3d.json (next to this script) and the shared viewer modules
viewer_modes.js and build_replay.js (../shared/ in the scratch layout, <project>/viewer-modes/ in the project)."""
import json, math, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

def shared(name):
    for d in (HERE.parent / 'shared', HERE.parent.parent / 'viewer-modes', HERE.parent / 'viewer-modes'):
        if (d / name).exists():
            return (d / name).read_text(encoding='utf-8')
    raise SystemExit(f'{name} not found (expected in <project>/viewer-modes/)')

data = (HERE / 'srisawan3d_merged.json').read_text(encoding='utf-8')
M = json.loads(data)
T = json.loads((HERE / 'srisawan3d.json').read_text(encoding='utf-8'))     # the traced boxes carry each wall's thickness
modes = shared('viewer_modes.js')
replay = shared('build_replay.js')

# Build replay data for floors 1 and 2: the traced lines, each line as a strip of its wall's thickness, and counts.
KINDS = ('wall', 'core', 'glass', 'envelope')
S = {'floors': {}, 'stats': {}}
for fl in ('L1', 'L2'):
    lines, pieces, st = {}, {}, {'lines': {}, 'runs': {}}
    for k in KINDS:
        segs = M['segments'].get(f'{fl}:{k}', [])
        boxes = T['boxes'].get(f'{fl}:{k}', [])
        lines[k] = [round(v, 2) for s in segs for v in s[:4]]
        q = []
        for i, (x1, y1, x2, y2, *_) in enumerate(segs):
            L = math.hypot(x2 - x1, y2 - y1)
            if L < 1e-6: continue
            t = (boxes[i][4] if i < len(boxes) else 0.18) / 2
            nx, ny = -(y2 - y1) / L * t, (x2 - x1) / L * t
            q += [round(v, 2) for v in (x1 + nx, y1 + ny, x2 + nx, y2 + ny, x2 - nx, y2 - ny, x1 - nx, y1 - ny)]
        pieces[k] = q
        st['lines'][k] = len(segs)
        st['runs'][k] = len(M['solids'].get(f'{fl}:{k}', []))
    S['floors'][fl] = {'lines': lines, 'pieces': pieces,
                       'sheet': [0.0, 0.0] if fl == 'L1' else [round(M['size'][0] + 10, 1), 0.0]}   # side by side, as two images
    S['stats'][fl] = st
S['slabHoles'] = {fl: len(M['slabs'][fl]['holes']) for fl in ('L1', 'L2')}

html = r'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Srisawan 3D viewer</title>
<style>
  :root { --bg:#eef2f5; --panel:#ffffffee; --ink:#1d2731; --muted:#5a6772; --accent:#2f6f8f; --line:#d3dbe1; }
  html, body { margin:0; height:100%; background:var(--bg); font:14px/1.4 system-ui, -apple-system, "Segoe UI", sans-serif; color:var(--ink); overflow:hidden; }
  #panel { position:fixed; top:12px; left:12px; width:min(340px, calc(100vw - 48px)); max-height:calc(100vh - 60px); overflow:auto; background:var(--panel); border:1px solid var(--line); border-radius:10px; padding:12px 14px; box-shadow:0 2px 10px #0001; }
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
scene.background = new THREE.Color(0xeef2f5);
const camera = new THREE.PerspectiveCamera(38, innerWidth / innerHeight, 0.5, 1000);
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
scene.add(new THREE.HemisphereLight(0xffffff, 0xdbe0e4, 1.5));
const sun = new THREE.DirectionalLight(0xffffff, 1.7);
sun.position.set(-40, 80, 30);
scene.add(sun);

const COLORS = { wall: 0xdcd8cf, core: 0x9ea8af, envelope: 0xd2cdc3, glass: 0x7dc2d3 };
const KIND_NAME = { wall: 'wall', core: 'lift core', envelope: 'outer wall', glass: 'garden glazing' };
const FLOOR_NAME = { L1: 'Floor 1', L2: 'Floor 2', F6: 'Floor 6' };
const groups = { L1: new THREE.Group(), L2: new THREE.Group(), F6: new THREE.Group() };
const shell = [], slabMeshes = [], pickable = [];
const colliders = { L1: [], L2: [], F6: [] }, walkables = { L1: [], L2: [], F6: [] };
const rise = { L1: [], L2: [], F6: [] }, late = { L1: [], L2: [], F6: [] };     // for the build replay

// When each wall run starts to rise in the build replay: a sweep from west to east (0..1, from the run's centre).
const [W0, W1] = [-D.size[0] / 2, D.size[0] / 2], [N0, N1] = [-D.size[1] / 2, D.size[1] / 2];
function sweep(r) {
  let cx = 0, cy = 0;
  r.o.forEach(([x, y]) => { cx += x; cy += y; });
  cx /= r.o.length; cy /= r.o.length;
  return Math.max(0, Math.min(1, 0.8 * (cx - W0) / (W1 - W0) + 0.2 * (N1 - cy) / (N1 - N0)));
}

// Walls arrive already merged: each item is one solid outline (with holes) per wall run,
// so there are no seams between traced segments and corners are clean.
// Plan (x, y) in metres -> three.js (x, z = -y); height -> y.
function solids(rings, z0, h) {
  const parts = [];
  for (const r of rings) {
    const shape = new THREE.Shape(r.o.map(([x, y]) => new THREE.Vector2(x, y)));
    for (const hole of r.h) shape.holes.push(new THREE.Path(hole.map(([x, y]) => new THREE.Vector2(x, y))));
    const g = new THREE.ExtrudeGeometry(shape, { depth: h, bevelEnabled: false, curveSegments: 1 });
    g.rotateX(-Math.PI / 2);
    g.translate(0, z0, 0);
    g.setAttribute('aDelay', new THREE.BufferAttribute(new Float32Array(g.attributes.position.count).fill(sweep(r)), 1));
    parts.push(g);
  }
  const merged = mergeGeometries(parts, false);
  parts.forEach(p => p.dispose());
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
  const [g, e] = solids(rings, D.levels[floor], D.heights[floor]);
  const glass = kind === 'glass';
  const mesh = new THREE.Mesh(g, new THREE.MeshStandardMaterial({
    color: COLORS[kind], roughness: 0.9, side: THREE.DoubleSide,
    transparent: glass, opacity: glass ? 0.3 : 1, depthWrite: !glass,
  }));
  mesh.userData = { floor, kind, segs: D.segments[key] || [] };
  g.computeBoundsTree();
  colliders[floor].push(mesh);
  const lines = new THREE.LineSegments(e, new THREE.LineBasicMaterial({ color: glass ? 0x4f9fb3 : 0x6a655e, transparent: true, opacity: 0.6 }));
  groups[floor].add(mesh, lines);
  pickable.push(mesh);
  rise[floor].push({ mesh, edges: lines, scales: true });
  if (kind === 'glass' || kind === 'envelope') shell.push(mesh, lines);
}

// Zone of the traced segment nearest to a plan point (for the hover label).
function nearestZone(segs, x, y) {
  let best = Infinity, zone = '';
  for (const [x1, y1, x2, y2, z] of segs) {
    const dx = x2 - x1, dy = y2 - y1, L2 = dx * dx + dy * dy;
    const t = L2 ? Math.max(0, Math.min(1, ((x - x1) * dx + (y - y1) * dy) / L2)) : 0;
    const d = Math.hypot(x - (x1 + t * dx), y - (y1 + t * dy));
    if (d < best) { best = d; zone = D.zones[z]; }
  }
  return zone;
}

// Slabs: outline with real holes (floor 2: 2 voids + 6 core openings), 0.25 m thick, as in the 3ds Max script.
for (const [floor, sl] of Object.entries(D.slabs)) {
  const shape = new THREE.Shape(sl.outer.map(([x, y]) => new THREE.Vector2(x, y)));
  for (const h of sl.holes) shape.holes.push(new THREE.Path(h.map(([x, y]) => new THREE.Vector2(x, y))));
  const g = new THREE.ExtrudeGeometry(shape, { depth: 0.25, bevelEnabled: false });
  g.rotateX(-Math.PI / 2);
  g.translate(0, sl.z, 0);
  const m = new THREE.Mesh(g, new THREE.MeshStandardMaterial({ color: 0xb9c1c6, roughness: 0.95 }));
  g.computeBoundsTree();
  groups[floor].add(m);
  slabMeshes.push(m);
  walkables[floor].push(m);
  late[floor].push(m);
}
Object.values(groups).forEach(g => scene.add(g));

// Floor notes quote the levels in use, which Build settings can change.
const LV = { L1: D.levels.L1, L2: D.levels.L2 };
const lvTxt = x => x === 0 ? '0.00 m' : (x > 0 ? '+' : '') + x.toFixed(2) + ' m';
const NOTES = {
  both: () => `Floor 1 at ${lvTxt(LV.L1)}, floor 2 at ${lvTxt(LV.L2)}. Both share the same lift-core position. Floor 2 has 2 voids ("open to below") and 6 core openings in its slab.`,
  L1: () => `Floor 1 at ${lvTxt(LV.L1)}: North Imaging, East ER/Ortho, South Reception, West Medicine, West/South Pharmacy.`,
  L2: () => `Floor 2 at ${lvTxt(LV.L2)}: North Clinics, East Checkup/GI, South EENT/PT, West Women, West Pediatric/Pharmacy. The holes in the slab are the 2 voids and 6 core openings.`,
  F6: () => 'Floor 6 (from floor6-dxf), shown on its own: it is measured from a different lift-core point and its height is not given, so it is not stacked. Interior walls only, drawn from wall centre lines, 4 m high.',
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
  document.getElementById('note').textContent = NOTES[floorMode]();
}
const check = id => document.getElementById(id).checked;
function applyChecks() {
  slabMeshes.forEach(m => { m.visible = check('slabs'); });
  shell.forEach(o => { o.visible = check('shell'); });
}

// Floor buttons: in Walk they show (and change) the floor you are on, and the note follows it; otherwise they show or hide floors.
function markFloors(st) {
  if (st.mode === 'walk') {
    // Leaving Walk (to Ghost or Orbit) keeps showing the building you walked in: floor 6, or floors 1 + 2.
    if (st.floor === 'F6') floorMode = 'F6'; else if (floorMode === 'F6') floorMode = 'both';
  }
  const key = st.mode === 'walk' ? st.floor : floorMode;
  document.querySelectorAll('#floors button').forEach(b => b.classList.toggle('on', b.dataset.f === key));
  if (st.mode === 'walk') document.getElementById('note').textContent = NOTES[st.floor]();
}

__MODES__

__REPLAY__

const FLOORS = [
  { key: 'L1', name: 'Floor 1', level: D.levels.L1, stack: 'hospital', group: groups.L1, colliders: colliders.L1, walkables: walkables.L1 },
  { key: 'L2', name: 'Floor 2', level: D.levels.L2, stack: 'hospital', group: groups.L2, colliders: colliders.L2, walkables: walkables.L2 },
  { key: 'F6', name: 'Floor 6', level: D.levels.F6, stack: 'floor6', group: groups.F6, colliders: colliders.F6, walkables: walkables.F6 },
];
const modes = installViewerModes({
  scene, camera, renderer, controls, project: 'Srisawan',
  panel: document.getElementById('panel'), anchor: document.getElementById('views'), hint: document.getElementById('hint'),
  restoreVisibility: applyFloor, onChange: markFloors, floors: FLOORS,
});

function bind(id, attr, fn) {
  document.querySelectorAll('#' + id + ' button').forEach(b => {
    b.onclick = () => {
      document.querySelectorAll('#' + id + ' button').forEach(x => x.classList.toggle('on', x === b));
      fn(b.dataset[attr]);
    };
  });
}
document.querySelectorAll('#floors button').forEach(b => {
  b.onclick = () => {
    const f = b.dataset.f;
    if (modes.mode === 'walk') { modes.goToFloor(f === 'both' ? 'L1' : f); return; }
    const was = floorMode;
    floorMode = f;
    applyFloor();
    if (modes.mode === 'orbit' && (was === 'F6') !== (f === 'F6')) frame();
    markFloors({ mode: modes.mode });
  };
});
bind('views', 'v', v => { modes.setMode('orbit'); viewMode = v; frame(); });
['slabs', 'shell'].forEach(id => { document.getElementById(id).onchange = applyChecks; });

// Hover (mouse only): show the floor, zone and type of the wall under the pointer.
const ray = new THREE.Raycaster(), mouse = new THREE.Vector2(), tip = document.getElementById('tip');
addEventListener('pointermove', ev => {
  if (ev.pointerType !== 'mouse' || modes.mode !== 'orbit' || replay.phase === 'settings' || replay.phase === 'play') { tip.style.display = 'none'; return; }
  mouse.set(ev.clientX / innerWidth * 2 - 1, -(ev.clientY / innerHeight) * 2 + 1);
  ray.setFromCamera(mouse, camera);
  const visible = pickable.filter(m => m.visible && m.parent.visible);
  const hit = ray.intersectObjects(visible, false)[0];
  if (hit) {
    const u = hit.object.userData;
    const zone = nearestZone(u.segs, hit.point.x, -hit.point.z);
    tip.textContent = FLOOR_NAME[u.floor] + ' · ' + zone + ' · ' + KIND_NAME[u.kind];
    tip.style.left = (ev.clientX + 14) + 'px';
    tip.style.top = (ev.clientY + 12) + 'px';
    tip.style.display = 'block';
  } else {
    tip.style.display = 'none';
  }
});
addEventListener('pointerdown', ev => { if (ev.pointerType !== 'mouse') tip.style.display = 'none'; });
applyFloor();
frame();

// ---------------------------------------------------------------- the build replay, with this model's numbers
const st1 = S.stats.L1, st2 = S.stats.L2;
const n = (st, k) => Object.values(st[k]).reduce((a, b) => a + b, 0);
const kind = k => st1.lines[k] + st2.lines[k];
const lv = x => (x >= 0 ? '+' : '') + x.toFixed(2) + ' m';
const replay = installBuildReplay({
  scene, camera, renderer, controls, modes, panel: document.getElementById('panel'), project: 'Srisawan',
  intro: { title: 'Srisawan Hospital, floors 1 and 2', facts: [
    'Traced from the plan images x01.jpg and x02.jpg (not CAD)',
    'Scale from the 1.20 m lift door (19 px)',
    'Floor 6 is a separate drawing and is not part of this replay',
  ] },
  layersTitle: 'What the tracing found',
  layers: [['Walls', `${kind('wall')} lines`], ['Lift core', `${kind('core')} lines`], ['Garden glass', `${kind('glass')} lines`], ['Outer walls', `${kind('envelope')} lines`]],
  floors: ['L1', 'L2'].map(k => ({
    key: k, name: FLOOR_NAME[k], level: D.levels[k], height: D.heights[k], sheet: S.floors[k].sheet, group: groups[k],
    lines: S.floors[k].lines, pieces: S.floors[k].pieces,
    rings: Object.fromEntries(['wall', 'core', 'envelope', 'glass'].map(t => [t, D.solids[k + ':' + t] || []])),
    rise: rise[k], late: late[k],
  })),
  others: [groups.F6],
  colors: { wall: 0x7a6650, core: 0x55606a, glass: 0x2f86a8, envelope: 0x8a6f52 },
  steps: {
    read: { title: 'Read the traced plans', caption: () => `${n(st1, 'lines')} traced lines on floor 1 and ${n(st2, 'lines')} on floor 2, from the plan images, scaled by the 1.20 m lift door.` },
    sort: { title: 'Sort the lines', caption: () => `Walls ${kind('wall')} lines, lift core ${kind('core')}, garden glass ${kind('glass')}, outer walls ${kind('envelope')}.` },
    align: { title: 'Line up the floors', caption: st => `Floor 2 was traced from its own image. Lining up the lift cores puts it over floor 1, and it rises to ${lv(st.L2.level)}.` },
    pair: { title: 'Make wall pieces', caption: () => `Each traced line becomes a strip as thick as its wall: ${n(st1, 'lines')} pieces on floor 1 and ${n(st2, 'lines')} on floor 2.` },
    merge: { title: 'Merge into wall runs', caption: () => `${n(st1, 'lines') + n(st2, 'lines')} pieces merge into ${n(st1, 'runs') + n(st2, 'runs')} wall runs (${n(st1, 'runs')} on floor 1, ${n(st2, 'runs')} on floor 2): one solid each, no seams.` },
    raise: { title: 'Raise the walls', caption: st => `The walls rise to ${st.L1.height.toFixed(2)} m on floor 1 and ${st.L2.height.toFixed(2)} m on floor 2.` },
    finish: { title: 'Slabs, done', caption: () => `The slabs go in, with floor 2's ${S.slabHoles.L2} openings (2 voids and 6 core openings). Done: ${n(st1, 'runs') + n(st2, 'runs')} wall runs on 2 floors. Floor 6 is under its own button.` },
  },
  applySettings: st => {
    FLOORS.forEach(f => { if (st[f.key]) f.level = st[f.key].level; });
    LV.L1 = st.L1.level; LV.L2 = st.L2.level;
  },
  restore: () => { applyFloor(); applyChecks(); },
});
window.__host = { groups, rise };          // read-outs for the browser tests
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
