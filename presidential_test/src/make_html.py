"""Write the presidential suite test viewer from 'layout presidential test.dwg': walls, columns, glass, low walls and
built-ins, the terrace balustrade, the floor slab, room names, a coloured box per piece of furniture with a legend, a height
per kind and a tick that keeps the doorways clear (Walk is not stopped by the boxes in front of a door), Orbit / Walk / Ghost,
the Camera tool and the build replay.
Usage: python make_html.py <out.html>
Reads pres2_model.json and pres2_stages.json (next to this script, from build_model.py) and the shared viewer modules
viewer_modes.js and build_replay.js (<project>/viewer-modes/) and furniture_boxes.js (<project>/furniture/), pasted in
unchanged. A model without furniture (no furniture list in pres2_model.json) gives the page it always gave, byte for byte."""
import json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def shared(name):
    for d in (HERE.parent.parent / 'viewer-modes', HERE.parent.parent / 'furniture', HERE.parent / 'viewer-modes',
              HERE.parent / 'furniture', HERE.parent / 'shared', Path(r'C:\Users\DWP2\Desktop\Project walkthrough\viewer-modes')):
        if (d / name).exists():
            return (d / name).read_text(encoding='utf-8')
    raise SystemExit(f'{name} not found (expected in <project>/viewer-modes/ or <project>/furniture/)')


import hashlib
RAW = (HERE / 'pres2_model.json').read_bytes()
M = json.loads(RAW.decode('utf-8'))
SHA = hashlib.sha1(RAW).hexdigest()[:12]   # also written into the 3ds Max script
S = json.loads((HERE / 'pres2_stages.json').read_text(encoding='utf-8'))
modes, replay = shared('viewer_modes.js'), shared('build_replay.js')
has_furniture = bool(M.get('furniture'))
furniture_js = shared('furniture_boxes.js') if has_furniture else ''

html = r'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="model-data" content="__SHA__">
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
          border-radius:5px; border:1px solid #d5dade; pointer-events:none; white-space:nowrap; z-index:2; display:none; }__FURNITURE_CSS__
</style>
</head>
<body>
<div id="panel">
  <h1>Presidential suite (test): CAD → 3D</h1>
  <p>__INTRO__</p>
  <div class="row" id="shows">
    <label><input type="checkbox" id="plates" checked> Floor slab</label>
    <label><input type="checkbox" id="glass" checked> Glass</label>
    <label><input type="checkbox" id="rooms" checked> Room names</label>
  </div>
  <div class="legend">__LEGEND__</div>
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

const LV = D.level, H = D.floorToFloor;
// What each kind of part looks like. 'follow' = its top follows the wall height setting (walls, columns, lintels, glass).
const KIND = {
  wall:       { color: 0xe3ddd3, edge: 0x7f786e, follow: true },
  column:     { color: 0xe3ddd3, edge: 0x7f786e, follow: true },
  lintel:     { color: 0xe3ddd3, edge: 0x7f786e, follow: true },
  low:        { color: 0xd2c6b2, edge: 0x8d8170, follow: false },
  builtin:    { color: 0xc9a77f, edge: 0x8a6d4b, follow: false },    // a part can follow the wall height itself (p.follow)
  glass:      { color: 0x9cc3d5, edge: 0x5f8fa6, follow: true, glass: true },
  balustrade: { color: 0x9cc3d5, edge: 0x5f8fa6, follow: false, glass: true },
  deck:       { color: 0xb08a5c, edge: 0x8a6a44, follow: false, walk: true },
  post:       { color: 0x6f6153, edge: 0x4a4038, follow: false },
};
const group = new THREE.Group();
const colliders = [], walkables = [], rise = [], late = [], glassObjs = [], plateObjs = [];

// When each part starts to rise in the build replay: a sweep from west to east (0..1, from the part's centre).
let sx0 = Infinity, sx1 = -Infinity, sy0 = Infinity, sy1 = -Infinity;
for (const p of D.parts) if (p.kind !== 'slab') for (const [x, y] of p.o) {
  sx0 = Math.min(sx0, x); sx1 = Math.max(sx1, x); sy0 = Math.min(sy0, y); sy1 = Math.max(sy1, y);
}
function sweep(p) {
  let cx = 0, cy = 0;
  p.o.forEach(([x, y]) => { cx += x; cy += y; });
  cx /= p.o.length; cy /= p.o.length;
  return Math.max(0, Math.min(1, 0.8 * (cx - sx0) / (sx1 - sx0 || 1) + 0.2 * (sy1 - cy) / (sy1 - sy0 || 1)));
}
// One part (outline + inner loops) extruded from z0 to z1 above the floor level. Plan (x, y) -> three.js (x, z = -y).
function extrudePart(p) {
  const shape = new THREE.Shape(p.o.map(([x, y]) => new THREE.Vector2(x, y)));
  for (const hole of p.h) shape.holes.push(new THREE.Path(hole.map(([x, y]) => new THREE.Vector2(x, y))));
  const g = new THREE.ExtrudeGeometry(shape, { depth: p.z1 - p.z0, bevelEnabled: false, curveSegments: 1 });
  g.rotateX(-Math.PI / 2);
  g.translate(0, LV + p.z0, 0);
  g.setAttribute('aDelay', new THREE.BufferAttribute(new Float32Array(g.attributes.position.count).fill(sweep(p)), 1));
  return g;
}
const byKind = {};
for (const p of D.parts) if (p.kind !== 'slab') (byKind[p.kind] = byKind[p.kind] || []).push(p);
// Walls, columns and lintels share one mesh; every other kind gets its own.
const meshes = [['solid', ['wall', 'column', 'lintel']], ['low', ['low']], ['builtin', ['builtin']], ['glass', ['glass']],
                ['balustrade', ['balustrade']], ['deck', ['deck']], ['post', ['post']]];
for (const [name, kinds] of meshes) {
  const parts = kinds.flatMap(k => byKind[k] || []);
  if (!parts.length) continue;
  const st = KIND[kinds[0]];
  const geos = parts.map(extrudePart), merged = mergeGeometries(geos, false);
  geos.forEach(x => x.dispose());
  // 25 degrees: round columns and curved walls shade smooth; the suite's 30- and 45-degree corners stay sharp
  const g = toCreasedNormals(merged, THREE.MathUtils.degToRad(25)), e = new THREE.EdgesGeometry(merged, 25);
  merged.dispose();
  g.computeBoundsTree();
  const mat = st.glass
    ? new THREE.MeshStandardMaterial({ color: st.color, roughness: 0.15, metalness: 0, transparent: true, opacity: 0.3, depthWrite: false, side: THREE.DoubleSide })
    : new THREE.MeshStandardMaterial({ color: st.color, roughness: 0.85, side: THREE.DoubleSide });
  const mesh = new THREE.Mesh(g, mat);
  mesh.name = name;
  if (st.glass) mesh.renderOrder = 3;
  const lines = new THREE.LineSegments(e, new THREE.LineBasicMaterial({ color: st.edge, transparent: true, opacity: st.glass ? 0.45 : 0.6 }));
  group.add(mesh, lines);
  if (!st.walk) colliders.push(mesh);                    // decks are walked on, not into
  rise.push({ mesh, edges: lines, scales: st.follow || parts.every(p => p.follow) });   // balustrade, low walls, built-ins, decks and posts keep their own height
  if (st.glass) glassObjs.push(mesh, lines);
}
// The floor slab: 0.25 m under the floor level (terraces included).
for (const p of D.parts.filter(p => p.kind === 'slab')) {
  const g = extrudePart(p);
  g.computeVertexNormals(); g.computeBoundsTree();
  const m = new THREE.Mesh(g, new THREE.MeshStandardMaterial({ color: 0xd4d8d2, roughness: 0.95 }));
  group.add(m); walkables.push(m); late.push(m); plateObjs.push(m);
}
scene.add(group);

const check = id => document.getElementById(id).checked;
function applyChecks() {
  plateObjs.forEach(o => { o.visible = check('plates'); });
  glassObjs.forEach(o => { o.visible = check('glass'); });
}
['plates', 'glass'].forEach(id => { document.getElementById(id).onchange = applyChecks; });

__MODES__
__FURNITURE_JS__
__REPLAY__

const FLOORS = [{ key: 'suite', name: 'Suite (FL-01)', level: LV, stack: 'suite', group, colliders, walkables }];
const modes = installViewerModes({
  scene, camera, renderer, controls, project: 'Presidential',
  panel: document.getElementById('panel'), anchor: document.getElementById('shows'), hint: document.getElementById('hint'),
  restoreVisibility: () => { group.visible = true; }, floors: FLOORS,
});
__FURNITURE_INSTALL__
// ---------------------------------------------------------------- the build replay, with this drawing's numbers
const fmt = n => Math.round(n).toLocaleString('en-US');
const st = S.stats;
const replay = installBuildReplay({
  scene, camera, renderer, controls, modes, panel: document.getElementById('panel'), project: 'Presidential',
  intro: { title: S.source.file, facts: S.intro },
  layersTitle: 'How the drawing was read',
  layers: S.layers,
  floors: [{ key: 'suite', name: 'Suite (FL-01)', level: LV, height: H, sheet: S.floor.sheet, group,
             lines: S.floor.lines, pieces: S.floor.pieces, rings: S.floor.rings, rise, late }],
  colors: { wall: 0x7a6650, glass: 0x3f8fb0, door: 0xc0702a, railing: 0x9b3fa0 },
  steps: {
    read: { title: 'Read the drawing', caption: () => S.captions.read },
    sort: { title: 'Sort the line work', caption: () => S.captions.sort },
    align: { title: 'Check the floor', caption: s => S.captions.align.replace('{level}', s.suite.level.toFixed(2)) },
    pair: { title: 'Find the wall faces', caption: () => S.captions.pair },
    merge: { title: 'Merge into wall runs', caption: () => S.captions.merge },
    raise: { title: 'Raise the walls', caption: s => S.captions.raise.replace('{height}', s.suite.height.toFixed(2)) },
    finish: { title: 'Slab and room names', caption: () => S.captions.finish },
  },
  applySettings: s => { FLOORS[0].level = s.suite.level; },
  restore: () => { group.visible = true; applyChecks();__FURNITURE_RESTORE__ },
});
__FURNITURE_PANEL__
// Room names from the drawing, shown over the model in Orbit.
const labels = D.rooms.map(r => {
  const el = document.createElement('div'); el.className = 'room'; el.textContent = r.label; document.body.appendChild(el);
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
// read-outs for tests: the doors, and a spot on the living room's west glass (its room-side face)
window.__host = { group, rise, labels, doors: D.doors, glassWestX: D.probe.glassWestX, glassWestY: D.probe.glassWestY__FURNITURE_HOST__ };
applyChecks();
modes.applyUrl();
renderer.setAnimationLoop(() => { replay.tick(); modes.tick(); renderer.render(scene, camera); placeLabels(); });
</script>
</body>
</html>
'''

legend_items = [('#e3ddd3', f"Walls and columns ({M['floorToFloor']:.2f} m)")]
kinds = {p['kind'] for p in M['parts']}
if 'glass' in kinds: legend_items.append(('#9cc3d5', 'Glass'))
if 'low' in kinds: legend_items.append(('#d2c6b2', 'Low walls, built-in seats, kerbs'))
if 'builtin' in kinds: legend_items.append(('#c9a77f', 'Built-ins'))
if 'balustrade' in kinds: legend_items.append(('#9cc3d5', f"Balustrade ({M.get('balustradeHeight', 1.1):.2f} m)"))
if 'deck' in kinds: legend_items.append(('#b08a5c', 'Terrace decks'))
if 'post' in kinds: legend_items.append(('#6f6153', 'Pergola posts'))
legend_items.append(('#d4d8d2', 'Floor slab'))
legend = ''.join(f'<span style="background:{c}{";margin-left:0" if i == 0 else ""}"></span>{t}' for i, (c, t) in enumerate(legend_items))
# The furniture boxes: the module, its call between Walk and the build replay (which reads the level's 'late' list as it starts)
# with the list under the Build row (the page's own controls stay where they were), the replay's restore hook, the read-outs for
# tests (the level as the module has it, the walk levels, the model, the furniture, the camera and the orbit controls) and a panel
# rule: the list makes the panel scroll, and its bottom edge must then stay above the hint line (12 px type, one line of 17 px or
# two when the window is narrow, 10 px from the bottom). The panel's whole box (its content box, 12 + 12 px of padding and the
# borders) is then 64 px shorter than the window and ends 52 px above its bottom (the box model, and so the width, stay as they
# were). The suite is one level and its model has no 'floors' list: the page hands the module that level itself, the way the
# bank's model and page have theirs. Without a furniture list in the model all six vanish.
furniture_parts = {
    '__FURNITURE_CSS__': '''
  #panel { max-height:calc(100vh - 90px); }''',
    '__FURNITURE_JS__': '\n' + furniture_js,
    '__FURNITURE_INSTALL__': '''
// ---------------------------------------------------------------- furniture boxes: one per piece, a legend with a height per kind
// The module takes the levels as the bank's model has them (FL: per level its group and lists; model.floors: their order). The
// suite's model has no 'floors': this is its one level, at the model's level (the build settings move the group, not this
// record), with the very lists Walk and the build replay use.
const FL = { suite: { key: 'suite', name: FLOORS[0].name, level: LV, group, colliders, walkables, late } };
const furnitureList = document.createElement('div');
const furniture = installFurnitureBoxes({ THREE, model: { ...D, floors: [FL.suite] }, FL, panel: furnitureList, canvas: renderer.domElement,
                                          camera, getMode: () => modes.mode, params: new URLSearchParams(location.search), project: 'Presidential' });
''',
    '__FURNITURE_PANEL__': '''
// the furniture list goes last in the side panel, under the Build row
document.getElementById('panel').appendChild(furnitureList);
''',
    '__FURNITURE_RESTORE__': ' if (furniture) furniture.apply();',
    '__FURNITURE_HOST__': ', FL, floors: FLOORS, model: D, furniture, camera, controls',
}

out = (html.replace('__DATA__', json.dumps(M, separators=(',', ':'), ensure_ascii=False))
           .replace('__STAGES__', json.dumps(S, separators=(',', ':'), ensure_ascii=False))
           .replace('__SHA__', SHA).replace('__INTRO__', S['panelIntro']).replace('__LEGEND__', legend)
           .replace('__MODES__', modes).replace('__REPLAY__', replay))
for marker, text in furniture_parts.items():
    out = out.replace(marker, text if has_furniture else '')
Path(sys.argv[1]).write_text(out, encoding='utf-8')
print('written', sys.argv[1], round(len(out) / 1024), 'KB')
