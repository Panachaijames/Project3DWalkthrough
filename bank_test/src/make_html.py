"""Write the bank branch test viewer: both levels with walls, columns, door lintels, curtain-wall glass and window panes,
railings, stairs, floor plates and room names, a coloured box per piece of furniture with a legend, a height per kind and
a tick that keeps the doorways clear (Walk is not stopped by the boxes in front of a door);
Orbit / Walk / Ghost, the Camera tool, the floor buttons and the build replay with this drawing's numbers.
Usage: python make_html.py <out.html>
Reads bank_model.json and bank_stages.json (next to this script, from build_model.py) and the shared viewer modules
viewer_modes.js and build_replay.js (<project>/viewer-modes/) and furniture_boxes.js (<project>/furniture/), pasted in
unchanged. A model without furniture (no furniture list in bank_model.json) gives the page it always gave, byte for byte."""
import hashlib, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def shared(name):
    for d in (HERE.parent.parent / 'viewer-modes', HERE.parent.parent / 'furniture', HERE.parent / 'viewer-modes', HERE.parent / 'furniture'):
        if (d / name).exists():
            return (d / name).read_text(encoding='utf-8')
    raise SystemExit(f'{name} not found (expected in <project>/viewer-modes/ or <project>/furniture/)')


RAW = (HERE / 'bank_model.json').read_bytes()
M = json.loads(RAW.decode('utf-8'))
SHA = hashlib.sha1(RAW).hexdigest()[:12]   # also written into the 3ds Max script
S = json.loads((HERE / 'bank_stages.json').read_text(encoding='utf-8'))
modes, replay = shared('viewer_modes.js'), shared('build_replay.js')
has_furniture = bool(M.get('furniture'))
furniture_js = shared('furniture_boxes.js') if has_furniture else ''

html = r'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="model-data" content="__SHA__">
<title>__SHORT__ test</title>
<style>
  :root { --bg:#eef0f2; --panel:#ffffffee; --ink:#1d2329; --muted:#5b6670; --accent:#2f6f8f; --line:#d5dade; }
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
  <h1>__PROJECT__ (test): CAD → 3D</h1>
  <p>__INTRO__</p>
  <div class="row" id="floors">
    <button data-f="both" class="on">Both levels</button>__FLOORBUTTONS__
  </div>
  <div class="row" id="shows">
    <label><input type="checkbox" id="plates" checked> Floor plates</label>
    <label><input type="checkbox" id="glass" checked> Glass</label>
    <label><input type="checkbox" id="rooms" checked> Room names</label>__SINGLEBOX__
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
camera.position.set(24, 27, 29);          // the usual view: from the south-east, above
const controls = new OrbitControls(camera, renderer.domElement);
controls.target.set(0, 2.5, 0);
controls.enableDamping = true;
scene.add(new THREE.HemisphereLight(0xffffff, 0xe4dfd6, 1.6));
const sun = new THREE.DirectionalLight(0xffffff, 1.6);
sun.position.set(-20, 40, 15);
scene.add(sun);

// What each kind of part looks like. A part whose top follows the wall height (p.follow: walls, columns, full-height
// glass, lintel tops) goes in a mesh that the wall-height setting scales; the rest keep their own height.
const KIND = {
  wall:    { color: 0xe3ddd3, edge: 0x7f786e, mesh: 'solid' },
  column:  { color: 0xe3ddd3, edge: 0x7f786e, mesh: 'solid' },
  lintel:  { color: 0xe3ddd3, edge: 0x7f786e, mesh: 'solid' },
  sill:    { color: 0xe3ddd3, edge: 0x7f786e, mesh: 'sill' },
  parapet: { color: 0xe3ddd3, edge: 0x7f786e, mesh: 'parapet' },               // a low wall at railing height
  glass:   { color: 0x9cc3d5, edge: 0x5f8fa6, mesh: 'glass', glass: true },
  mullion: { color: 0x5d6b74, edge: 0x3d474e, mesh: 'mullion' },               // a glass wall's frame post
  railing: { color: 0x6f6a75, edge: 0x4a4550, mesh: 'railing', see: 0.5 },     // an open metal rail: half see-through
  single:  { color: 0xe0a458, edge: 0xa86f2c, mesh: 'single' },
  step:    { color: 0xb9c7b4, edge: 0x6f8a6a, mesh: 'step' },                  // solid stair steps
};
const FL = {};                    // per level: group, colliders, walkables, rise, late
for (const f of D.floors) FL[f.key] = { ...f, group: new THREE.Group(), colliders: [], walkables: [], rise: [], late: [] };
const glassObjs = [], plateObjs = [], singleObjs = [];

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
// One part (outline + inner loops) extruded from z0 to z1 above its level. Plan (x, y) -> three.js (x, z = -y).
function extrudePart(p, level) {
  const shape = new THREE.Shape(p.o.map(([x, y]) => new THREE.Vector2(x, y)));
  for (const hole of p.h) shape.holes.push(new THREE.Path(hole.map(([x, y]) => new THREE.Vector2(x, y))));
  const g = new THREE.ExtrudeGeometry(shape, { depth: p.z1 - p.z0, bevelEnabled: false, curveSegments: 1 });
  g.rotateX(-Math.PI / 2);
  g.translate(0, level + p.z0, 0);
  g.setAttribute('aDelay', new THREE.BufferAttribute(new Float32Array(g.attributes.position.count).fill(sweep(p)), 1));
  return g;
}
// Merged per level and kind (one draw call each), split by whether the top follows the wall height.
for (const f of Object.values(FL)) {
  const groups = {};
  for (const p of D.parts) {
    if (p.floor !== f.key || p.kind === 'slab') continue;
    const k = KIND[p.kind].mesh + (p.follow ? ':follow' : ':own');
    (groups[k] = groups[k] || []).push(p);
  }
  for (const [name, parts] of Object.entries(groups)) {
    const st = KIND[parts[0].kind], follow = name.endsWith(':follow');
    const geos = parts.map(p => extrudePart(p, f.level)), merged = mergeGeometries(geos, false);
    geos.forEach(x => x.dispose());
    // 25 degrees: the curved terrace wall and the wealth-room corners shade smooth; 30-45 degree corners stay sharp
    const g = toCreasedNormals(merged, THREE.MathUtils.degToRad(25)), e = new THREE.EdgesGeometry(merged, 25);
    merged.dispose();
    g.computeBoundsTree();
    const mat = st.glass
      ? new THREE.MeshStandardMaterial({ color: st.color, roughness: 0.15, metalness: 0, transparent: true, opacity: 0.3, depthWrite: false, side: THREE.DoubleSide })
      : st.see ? new THREE.MeshStandardMaterial({ color: st.color, roughness: 0.6, metalness: 0.2, transparent: true, opacity: st.see, depthWrite: false, side: THREE.DoubleSide })
      : new THREE.MeshStandardMaterial({ color: st.color, roughness: 0.85, side: THREE.DoubleSide });
    const mesh = new THREE.Mesh(g, mat);
    mesh.name = f.key + ' ' + name;
    if (st.glass) mesh.renderOrder = 3;
    else if (st.see) mesh.renderOrder = 2;
    const lines = new THREE.LineSegments(e, new THREE.LineBasicMaterial({ color: st.edge, transparent: true, opacity: st.glass ? 0.45 : 0.6 }));
    f.group.add(mesh, lines);
    f.colliders.push(mesh);                            // walls, columns, lintels, sills, glass, railings, single lines
    f.rise.push({ mesh, edges: lines, scales: follow });
    if (st.glass) glassObjs.push(mesh, lines);
    if (st.mesh === 'single') singleObjs.push(mesh, lines);
  }
  // Walk-collision skins: invisible 8 cm colliders around pieces thinner than Walk's ray spacing (screens, panes, rails).
  for (const isGlass of [false, true]) {
    const sk = (D.colliderSkins[f.key] || []).filter(p => !!p.glass === isGlass);
    if (!sk.length) continue;
    const geos = sk.map(p => extrudePart(p, f.level)), merged = mergeGeometries(geos, false);
    geos.forEach(x => x.dispose());
    merged.computeBoundsTree();
    const m = new THREE.Mesh(merged, new THREE.MeshBasicMaterial({ visible: false }));
    m.name = f.key + ' walk skins' + (isGlass ? ' (glass)' : '');
    f.group.add(m); f.colliders.push(m);
    if (isGlass) glassObjs.push(m);            // the Glass box switches them with the glass they wrap
  }
  // The floor plate: a slab under the level (approximate outline of the walls, glass and railings). Drawn slightly in
  // front where it meets the tops of the walls of the level below (same height), so it never flickers.
  for (const p of D.parts.filter(p => p.floor === f.key && p.kind === 'slab')) {
    const g = extrudePart(p, f.level);
    g.computeVertexNormals(); g.computeBoundsTree();
    const m = new THREE.Mesh(g, new THREE.MeshStandardMaterial({ color: 0xd4d8d2, roughness: 0.95, polygonOffset: true, polygonOffsetFactor: -1, polygonOffsetUnits: -1 }));
    f.group.add(m); f.walkables.push(m); f.late.push(m); plateObjs.push(m);
  }
  // Stairs: flights with an UP / DOWN word are solid steps (parts, above); the other tread lines below the cut lie flat
  // on the floor as thin strips (the stair as the plan draws it); flights above the cut (the next storey's) as faint lines.
  const st = D.stairs[f.key] || { below: [], above: [] };
  if (st.below.length) {
    const pos = [], a = st.below, z0 = f.level + 0.012, hw = 0.015;
    for (let i = 0; i < a.length; i += 4) {
      const dx = a[i + 2] - a[i], dy = a[i + 3] - a[i + 1], L = Math.hypot(dx, dy) || 1, nx = -dy / L * hw, ny = dx / L * hw;
      const p = [a[i] + nx, z0, -(a[i + 1] + ny)], q = [a[i + 2] + nx, z0, -(a[i + 3] + ny)];
      const r = [a[i + 2] - nx, z0, -(a[i + 3] - ny)], s = [a[i] - nx, z0, -(a[i + 1] - ny)];
      pos.push(...p, ...q, ...r, ...p, ...r, ...s);
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
    g.computeVertexNormals();
    const m = new THREE.Mesh(g, new THREE.MeshStandardMaterial({ color: 0x3f8f4f, side: THREE.DoubleSide }));
    m.name = f.key + ' tread lines';
    f.group.add(m); f.late.push(m);
  }
  if (st.above.length) {
    const pos = [], a = st.above, y = f.level + 0.02;
    for (let i = 0; i < a.length; i += 4) pos.push(a[i], y, -a[i + 1], a[i + 2], y, -a[i + 3]);
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
    const m = new THREE.LineSegments(g, new THREE.LineBasicMaterial({ color: 0x5aa65a, transparent: true, opacity: 0.35 }));
    f.group.add(m); f.late.push(m);
  }
  scene.add(f.group);
}

let floorMode = 'both';
function applyFloor() { for (const f of Object.values(FL)) f.group.visible = floorMode === 'both' || floorMode === f.key; }
const check = id => { const el = document.getElementById(id); return !el || el.checked; };
function applyChecks() {
  plateObjs.forEach(o => { o.visible = check('plates'); });
  glassObjs.forEach(o => { o.visible = check('glass'); });
  singleObjs.forEach(o => { o.visible = check('single'); });
}
// Floor buttons: in Walk they show (and change) the level you are on; otherwise they show or hide levels.
function markFloors(st) {
  const key = st.mode === 'walk' ? st.floor : floorMode;
  document.querySelectorAll('#floors button').forEach(b => b.classList.toggle('on', b.dataset.f === key));
}

__MODES__
__FURNITURE_JS__
__REPLAY__

const FLOORS = D.floors.map(f => ({ key: f.key, name: f.name, level: f.level, stack: 'bank', group: FL[f.key].group,
                                    colliders: FL[f.key].colliders, walkables: FL[f.key].walkables }));
const modes = installViewerModes({
  scene, camera, renderer, controls, project: D.photoName,
  panel: document.getElementById('panel'), anchor: document.getElementById('floors'), hint: document.getElementById('hint'),
  restoreVisibility: applyFloor, onChange: markFloors, floors: FLOORS,
});
document.querySelectorAll('#floors button').forEach(btn => {
  btn.onclick = () => {
    const f = btn.dataset.f;
    if (modes.mode === 'walk') { modes.goToFloor(f === 'both' ? FLOORS[0].key : f); return; }
    floorMode = f;
    applyFloor();
    markFloors({ mode: modes.mode });
  };
});
['plates', 'glass', 'rooms', 'single'].forEach(id => { const el = document.getElementById(id); if (el) el.onchange = applyChecks; });
applyFloor();
__FURNITURE_INSTALL__
// ---------------------------------------------------------------- the build replay, with this drawing's numbers
const fill = (txt, s) => txt.replace(/\{(\w+?)(level|height)\}/g, (m, k, p) => (s[k] ? s[k][p].toFixed(2) : m));
const replay = installBuildReplay({
  scene, camera, renderer, controls, modes, panel: document.getElementById('panel'), project: D.photoName,
  intro: { title: S.source.files.join(' + '), facts: S.intro },
  layersTitle: 'How the drawing was read',
  layers: S.layers,
  floors: D.floors.map(f => ({ key: f.key, name: f.name, level: f.level, height: f.wallHeight, sheet: S.floors[f.key].sheet,
    group: FL[f.key].group, lines: S.floors[f.key].lines, pieces: S.floors[f.key].pieces, rings: S.floors[f.key].rings,
    rise: FL[f.key].rise, late: FL[f.key].late })),
  colors: { wall: 0x7a6650, glass: 0x2f86a8, door: 0xc0702a, stair: 0x2e8b47, railing: 0x9b3fa0 },
  steps: {
    read: { title: 'Read the drawing', caption: () => S.captions.read },
    sort: { title: 'Sort the layers', caption: () => S.captions.sort },
    align: { title: 'Line up the levels', caption: s => fill(S.captions.align, s) },
    pair: { title: 'Find the wall faces', caption: () => S.captions.pair },
    merge: { title: 'Merge, cut the openings', caption: () => S.captions.merge },
    raise: { title: 'Raise the walls', caption: s => fill(S.captions.raise, s) },
    finish: { title: 'Floors, stairs, room names', caption: () => S.captions.finish },
  },
  applySettings: st => { FLOORS.forEach(f => { f.level = st[f.key].level; }); },
  restore: () => { applyFloor(); applyChecks();__FURNITURE_RESTORE__ },
});
__FURNITURE_PANEL__
// Room names from the drawing, shown over the model in Orbit (on the levels that are showing).
const labels = D.rooms.map(r => {
  const el = document.createElement('div'); el.className = 'room'; el.textContent = r.label; document.body.appendChild(el);
  return { el, floor: r.floor, area: r.area || 0, p: new THREE.Vector3(r.x, 0, -r.y) };
});
const labelsByArea = [...labels].sort((a, b) => b.area - a.area);      // bigger rooms first (they keep their spot)
const levelOf = k => FLOORS.find(f => f.key === k).level;
const v = new THREE.Vector3();
// Names that would overlap on screen are moved apart: the bigger room keeps its spot, a smaller one moves just above
// or below it (up to two rows away), and is hidden only when no free row is near.
function placeLabels() {
  const show = check('rooms') && modes.mode === 'orbit' && replay.phase === 'done';
  // only the top level that is showing: the ones below are under its floor plate
  const top = FLOORS.filter(f => f.group.visible).sort((a, b) => b.level - a.level)[0];
  const placed = [];
  for (const L of labelsByArea) {
    const on0 = show && top && L.floor === top.key;
    if (on0) { v.copy(L.p); v.y = levelOf(L.floor) + 1.4; v.project(camera); }
    let on = on0 && v.z < 1 && Math.abs(v.x) < 1.1 && Math.abs(v.y) < 1.1;
    if (on) {
      const x = (v.x + 1) / 2 * innerWidth, y = (1 - v.y) / 2 * innerHeight;
      if (!L.w) { L.el.style.display = 'block'; L.w = L.el.offsetWidth; L.h = L.el.offsetHeight; }
      const box = dy => ({ l: x - L.w / 2, r: x + L.w / 2, t: y + dy - L.h / 2, b: y + dy + L.h / 2 });
      const free = b => placed.every(q => b.r + 2 <= q.l || b.l >= q.r + 2 || b.b + 1 <= q.t || b.t >= q.b + 1);
      const dy = [0, 1, -1, 2, -2].map(k => k * (L.h + 2)).find(d => free(box(d)));
      if (dy === undefined) on = false;
      else { placed.push(box(dy)); L.el.style.left = x + 'px'; L.el.style.top = (y + dy) + 'px'; L.dy = dy; }
    }
    L.el.style.display = on ? 'block' : 'none';
  }
}
// read-outs for tests: the levels, the detected openings, the glass spots to walk into, and what is overhead at a spot
// (the height above the level of the first thing that stops you, looking straight up from h0; null = open)
const upRay = new THREE.Raycaster(); upRay.firstHitOnly = true;
function upHit(key, x, y, h0 = 1.0) {
  const f = FLOORS.find(g => g.key === key);
  upRay.set(new THREE.Vector3(x, f.level + h0, -y), new THREE.Vector3(0, 1, 0)); upRay.far = 20;
  const hit = upRay.intersectObjects(FL[key].colliders.filter(m => m.visible), false)[0];
  return hit ? hit.distance + h0 : null;
}
// a level ray in any direction at height h above the level: the first thing it stops on (distance, mesh name), or null
const flatRay = new THREE.Raycaster(); flatRay.firstHitOnly = true;
function rayHit(key, x, y, h, dx, dy, far = 3) {
  const f = FLOORS.find(g => g.key === key), n = Math.hypot(dx, dy) || 1;
  flatRay.set(new THREE.Vector3(x, f.level + h, -y), new THREE.Vector3(dx / n, 0, -dy / n)); flatRay.far = far;
  const hit = flatRay.intersectObjects(FL[key].colliders.filter(m => m.visible), false)[0];
  return hit ? { d: hit.distance, name: hit.object.name } : null;
}
// looking straight down from h0 above the level: the height above the level of the first thing below (null = nothing)
function downHit(key, x, y, h0 = 3.0) {
  const f = FLOORS.find(g => g.key === key);
  upRay.set(new THREE.Vector3(x, f.level + h0, -y), new THREE.Vector3(0, -1, 0)); upRay.far = 8;
  const hit = upRay.intersectObjects(FL[key].colliders.filter(m => m.visible), false)[0];
  return hit ? h0 - hit.distance : null;
}
window.__host = { FL, labels, openings: D.openings, probes: D.probes, floors: FLOORS, upHit, downHit, rayHit, model: D__FURNITURE_HOST__ };
applyChecks();
modes.applyUrl();
renderer.setAnimationLoop(() => { replay.tick(); modes.tick(); renderer.render(scene, camera); placeLabels(); });
</script>
</body>
</html>
'''

kinds = {p['kind'] for p in M['parts']}
heights = sorted({f['wallHeight'] for f in M['floors']})
legend_items = [('#e3ddd3', 'Walls, columns and door lintels (' + ' / '.join(f'{h:.2f}' for h in heights) + ' m per level)')]
gw_heights = sorted({p['z1'] for p in M['parts'] if p['kind'] == 'glass' and p.get('label') and not p['label'].endswith((' pane', ' transom', 'glass screen'))})
if 'glass' in kinds: legend_items.append(('#9cc3d5', 'Glass: curtain wall, window panes' + (', glass partitions (' + ' / '.join(f'{h:.2f}' for h in gw_heights) + ' m, from the Revit wall types)' if gw_heights else '')))
if 'railing' in kinds: legend_items.append(('#77727c', f"Railings ({M['railingHeight']:.2f} m)" + (' and the parapet' if 'parapet' in kinds else '')))
legend_items.append(('#b9c7b4' if 'step' in kinds else '#5aa65a', ('Stairs: steps where the drawing says UP / DOWN, flat tread lines elsewhere' if 'step' in kinds else 'Stairs') + ' (faint: flights above the cut)'))
if 'single' in kinds: legend_items.append(('#e0a458', 'Single line: wall, railing or edge?'))
legend_items.append(('#d4d8d2', 'Floor plate (approximate outline)'))
legend = ''.join(f'<span style="background:{c}{";margin-left:0" if i == 0 else ""}"></span>{t}' for i, (c, t) in enumerate(legend_items))
floor_buttons = ''.join(f'<button data-f="{f["key"]}">{f["name"]}</button>' for f in M['floors'])
single_box = '\n    <label><input type="checkbox" id="single" checked> Single-line items</label>' if 'single' in kinds else ''
# The furniture boxes: the module, its call before the build replay (which reads each level's 'late' list as it starts) with
# the list under the Build row (the page's own controls stay where they were), the replay's restore hook and the read-outs for
# tests (the furniture, the camera and the orbit controls, to look at a spot), and a panel rule: the list makes the panel
# scroll, and its bottom edge must then stay above the hint line (12 px type, one line of 17 px or two when the window is
# narrow, 10 px from the bottom): the panel's whole box (its content box, its 12 + 12 px of padding and its borders) is at most
# 64 px short of the window's height, which is 90 px for the content box (the box model, and so the width, stay as they were).
# Without a furniture list in the model all six vanish.
furniture_parts = {
    '__FURNITURE_CSS__': '''
  #panel { max-height:calc(100vh - 90px); }''',
    '__FURNITURE_JS__': '\n' + furniture_js,
    '__FURNITURE_INSTALL__': '''
// ---------------------------------------------------------------- furniture boxes: one per piece, a legend with a height per kind
const furnitureList = document.createElement('div');
const furniture = installFurnitureBoxes({ THREE, model: D, FL, panel: furnitureList, canvas: renderer.domElement, camera,
                                          getMode: () => modes.mode, params: new URLSearchParams(location.search), project: D.photoName });
''',
    '__FURNITURE_PANEL__': '''
// the furniture list goes last in the side panel, under the Build row
document.getElementById('panel').appendChild(furnitureList);
''',
    '__FURNITURE_RESTORE__': ' if (furniture) furniture.apply();',
    '__FURNITURE_HOST__': ', furniture, camera, controls',
}

out = (html.replace('__DATA__', json.dumps(M, separators=(',', ':'), ensure_ascii=False))
           .replace('__STAGES__', json.dumps(S, separators=(',', ':'), ensure_ascii=False))
           .replace('__SHA__', SHA).replace('__INTRO__', S['panelIntro']).replace('__LEGEND__', legend)
           .replace('__FLOORBUTTONS__', floor_buttons).replace('__SINGLEBOX__', single_box)
           .replace('__PROJECT__', M['project']).replace('__SHORT__', M.get('shortName', M['project']))
           .replace('__MODES__', modes).replace('__REPLAY__', replay))
for marker, text in furniture_parts.items():
    out = out.replace(marker, text if has_furniture else '')
Path(sys.argv[1]).write_text(out, encoding='utf-8')
print('written', sys.argv[1], round(len(out) / 1024), 'KB | model data', SHA)
