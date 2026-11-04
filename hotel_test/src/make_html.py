"""Write the hotel test viewer (2 Nov 2026), the first model read from two PICTURES instead of CAD: both floors with walls,
door lintels, hatch sills, low walls, the glazing and its frame posts, railings, the stair's steps and the flat tread lines, floor plates and room
names, a coloured box per piece of furniture with a legend, a height per kind and the tick that keeps the doorways clear;
Orbit / Walk / Ghost, the Camera tool and the floor buttons; and a tick 'Plan picture' that lays each floor's source picture
on its floor plate, so the model can be judged against the drawing it was read from. The rules, with sizes in metres:
 1. THE PLAN PICTURE. Each floor's picture (the model's 'pictureFrame': its file, size, pixels per metre along each of the
    picture's axes and the pixel of the model's origin) lies flat PICTURE_LIFT above the floor level (the slab's top), under
    the walls, the whole sheet at the model's scale and position: pixel px = originPx[0] + pxPerMetreX * (x + offset x),
    py = originPx[1] - pxPerMetreY * (y + offset y); the sheet is size[0] / pxPerMetreX by size[1] / pxPerMetreY metres (a
    picture drawn wider than tall is not square in metres). It is unlit (the drawing's own colours), drawn in front of the
    slab, and is neither a collider nor a floor: Walk, the furniture, the double-click and the room names do not see it. It
    shows with its floor (the floor buttons, and both floors in Walk).
 2. OFF BY DEFAULT. The page opens on the model alone; the tick, or ?picture=1 in the address, puts the pictures under it.
 3. EMBEDDED. The two picture files go into the page as they are, byte for byte (a data: address), so the page also works
    when it is opened with a double-click or sent on: a browser does not let a page read a picture beside it from the disc.
 4. NO BUILD REPLAY. The replay of the CAD pages animates a drawing's lines being sorted into layers and paired into wall
    faces; a picture has no lines and no layers, so its steps would be made up. The plan picture shows what was read instead.
 5. THE VIEW. Orbit opens from the south-east, above (the bank page's angle, 0.9 of its distance), aimed at the middle of the
    floor plates and panned by half the side panel's width, so the model sits in the middle of the room the panel leaves.
Usage: python make_html.py <out.html>
Reads hotel_model.json (next to this script, from build_model.py), the pictures its 'pictureFrame' names, and the shared viewer
modules viewer_modes.js (<project>/viewer-modes/) and furniture_boxes.js (<project>/furniture/), pasted in unchanged."""
import base64, hashlib, json, math, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PICTURE_LIFT = 0.005       # rule 1: the sheet's height above the floor level (the slab's top is the level)


def shared(name):
    for d in (HERE.parent.parent / 'viewer-modes', HERE.parent.parent / 'furniture'):
        if (d / name).exists():
            return (d / name).read_text(encoding='utf-8')
    raise SystemExit(f'{name} not found (expected in <project>/viewer-modes/ or <project>/furniture/)')


RAW = (HERE / 'hotel_model.json').read_bytes()
M = json.loads(RAW.decode('utf-8'))
SHA = hashlib.sha1(RAW).hexdigest()[:12]   # also written into the 3ds Max script
modes = shared('viewer_modes.js')
has_furniture = bool(M.get('furniture'))
furniture_js = shared('furniture_boxes.js') if has_furniture else ''
pictures = {}                              # rule 3: floor key -> data: address of its picture, the file's own bytes
for key, pf in M.get('pictureFrame', {}).items():
    path = (HERE / pf['file']).resolve()
    if not path.exists(): raise SystemExit(f"{key}: picture {pf['file']} not found (from {HERE})")
    data = path.read_bytes()
    kind = 'png' if data[:8] == b'\x89PNG\r\n\x1a\n' else 'jpeg'
    pictures[key] = f'data:image/{kind};base64,' + base64.b64encode(data).decode('ascii')

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
  .legend { font-size:12.5px; line-height:1.45; margin-top:8px; }
  .legend div { margin:3px 0; padding-left:16px; text-indent:-16px; }                  /* one item a line, its swatch hanging in front */
  .legend span { display:inline-block; width:10px; height:10px; border-radius:2px; margin:0 6px 0 0; vertical-align:-1px; text-indent:0; }
  #hint { position:fixed; bottom:10px; left:12px; right:12px; color:var(--muted); font-size:12px; }
  .room { position:fixed; transform:translate(-50%, -50%); font-size:11.5px; background:#ffffffd9; color:#1d2329; padding:1px 6px;
          border-radius:5px; border:1px solid #d5dade; pointer-events:none; white-space:nowrap; z-index:2; display:none; }__FURNITURE_CSS__
</style>
</head>
<body>
<div id="panel">
  <h1>__SHORT__ (test): two pictures → 3D</h1>
  <p>__INTRO__</p>
  <div class="row" id="floors">
    <button data-f="both" class="on">Both floors</button>__FLOORBUTTONS__
  </div>
  <div class="row" id="shows">
    <label><input type="checkbox" id="plates" checked> Floor plates</label>
    <label><input type="checkbox" id="glass" checked> Glass</label>
    <label><input type="checkbox" id="rooms" checked> Room names</label>
    <label title="Each floor's source picture, laid on its floor plate at the model's scale and position"><input type="checkbox" id="picture"> Plan picture</label>
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
const PICTURES = __PICTURES__;             // floor key -> the picture file, as a data: address (its own bytes)
const PICTURE_LIFT = __LIFT__;             // the plan picture's height above the floor level (m)
const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.setSize(innerWidth, innerHeight);
document.body.appendChild(renderer.domElement);
const scene = new THREE.Scene();
scene.background = new THREE.Color(0xeef0f2);
const camera = new THREE.PerspectiveCamera(40, innerWidth / innerHeight, 0.1, 600);
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
scene.add(new THREE.HemisphereLight(0xffffff, 0xe4dfd6, 1.6));
const sun = new THREE.DirectionalLight(0xffffff, 1.6);
sun.position.set(-20, 40, 15);
scene.add(sun);
// The usual view: from the south-east, above (the bank page's angle, 0.9 of its distance), aimed at the middle of the floor
// plates and panned so that they sit in the middle of the room the side panel leaves on the right.
{
  let x0 = Infinity, x1 = -Infinity, y0 = Infinity, y1 = -Infinity;
  for (const p of D.parts) if (p.kind === 'slab') for (const [x, y] of p.o) { x0 = Math.min(x0, x); x1 = Math.max(x1, x); y0 = Math.min(y0, y); y1 = Math.max(y1, y); }
  const away = new THREE.Vector3(24, 24.5, 29).multiplyScalar(0.9), right = new THREE.Vector3(away.z, 0, -away.x).normalize();   // the screen's right, on the ground
  const metresPerPx = 2 * away.length() * Math.tan(camera.fov * Math.PI / 360) / innerHeight;
  const panelRight = Math.min(document.getElementById('panel').getBoundingClientRect().right, innerWidth / 2);
  const target = new THREE.Vector3((x0 + x1) / 2, 2.5, -(y0 + y1) / 2).addScaledVector(right, -panelRight / 2 * metresPerPx);
  controls.target.copy(target);
  camera.position.copy(target).add(away);
}

// What each kind of part looks like. A part whose top follows the wall height (p.follow: walls, full-height glass, frame
// posts, lintel tops) goes in its own mesh; the rest keep their own height (as on the CAD pages).
const KIND = {
  wall:    { color: 0xe3ddd3, edge: 0x7f786e, mesh: 'solid' },
  column:  { color: 0xe3ddd3, edge: 0x7f786e, mesh: 'solid' },
  lintel:  { color: 0xe3ddd3, edge: 0x7f786e, mesh: 'solid' },
  sill:    { color: 0xe3ddd3, edge: 0x7f786e, mesh: 'sill' },
  parapet: { color: 0xe3ddd3, edge: 0x7f786e, mesh: 'parapet' },               // a low wall at railing height
  glass:   { color: 0x9cc3d5, edge: 0x5f8fa6, mesh: 'glass', glass: true },
  mullion: { color: 0x5d6b74, edge: 0x3d474e, mesh: 'mullion' },               // a glazing line's frame post
  railing: { color: 0x6f6a75, edge: 0x4a4550, mesh: 'railing', see: 0.5 },     // an open metal rail: half see-through
  single:  { color: 0xe0a458, edge: 0xa86f2c, mesh: 'single' },
  step:    { color: 0xb9c7b4, edge: 0x6f8a6a, mesh: 'step' },                  // solid stair steps
};
const FL = {};                    // per floor: group, colliders, walkables, late (the furniture module adds its boxes to them)
for (const f of D.floors) FL[f.key] = { ...f, group: new THREE.Group(), colliders: [], walkables: [], late: [] };
const glassObjs = [], plateObjs = [], singleObjs = [];

// One part (outline + inner loops) extruded from z0 to z1 above its floor. Plan (x, y) -> three.js (x, z = -y).
function extrudePart(p, level) {
  const shape = new THREE.Shape(p.o.map(([x, y]) => new THREE.Vector2(x, y)));
  for (const hole of p.h) shape.holes.push(new THREE.Path(hole.map(([x, y]) => new THREE.Vector2(x, y))));
  const g = new THREE.ExtrudeGeometry(shape, { depth: p.z1 - p.z0, bevelEnabled: false, curveSegments: 1 });
  g.rotateX(-Math.PI / 2);
  g.translate(0, level + p.z0, 0);
  return g;
}
// Merged per floor and kind (one draw call each), split by whether the top follows the wall height.
for (const f of Object.values(FL)) {
  const groups = {};
  for (const p of D.parts) {
    if (p.floor !== f.key || p.kind === 'slab') continue;
    const k = KIND[p.kind].mesh + (p.follow ? ':follow' : ':own');
    (groups[k] = groups[k] || []).push(p);
  }
  for (const [name, parts] of Object.entries(groups)) {
    const st = KIND[parts[0].kind];
    const geos = parts.map(p => extrudePart(p, f.level)), merged = mergeGeometries(geos, false);
    geos.forEach(x => x.dispose());
    // 25 degrees: the small kinks of an outline traced from a picture shade smooth; real corners stay sharp
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
    f.colliders.push(mesh);                            // walls, lintels, glass, frame posts, railings, steps
    if (st.glass) glassObjs.push(mesh, lines);
    if (st.mesh === 'single') singleObjs.push(mesh, lines);
  }
  // Walk-collision skins: invisible colliders round the pieces thinner than Walk's ray spacing (panes, frame posts, rails).
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
  // The floor plate: a slab under the floor. Drawn slightly in front where it meets the tops of the walls of the floor
  // below (same height), so it never flickers.
  for (const p of D.parts.filter(p => p.floor === f.key && p.kind === 'slab')) {
    const g = extrudePart(p, f.level);
    g.computeVertexNormals(); g.computeBoundsTree();
    const m = new THREE.Mesh(g, new THREE.MeshStandardMaterial({ color: 0xd4d8d2, roughness: 0.95, polygonOffset: true, polygonOffsetFactor: -1, polygonOffsetUnits: -1 }));
    m.name = f.key + ' floor plate';
    f.group.add(m); f.walkables.push(m); f.late.push(m); plateObjs.push(m);
  }
  // Stairs: the flight from Floor 1 is solid steps (parts, above); the flights that lead to a floor not in the pictures lie
  // flat on the floor as thin strips (the stair as the picture draws it).
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

// ---------------------------------------------------------------- the plan pictures (rules 1 to 3 of make_html.py)
// Each floor's picture as one flat sheet, PICTURE_LIFT above its floor level, at the model's scale and position. Its own group
// (not the floor's, whose colliders, floors and extent are the model's): it shows while the tick is on and its floor shows.
const pictureObjs = [], pictureLayer = new THREE.Group();
pictureLayer.name = 'plan pictures';
scene.add(pictureLayer);
const picturesReady = Promise.all(Object.entries(D.pictureFrame || {}).filter(([key]) => FL[key] && PICTURES[key]).map(([key, pf]) => {
  const [W, H] = pf.size, kx = pf.pxPerMetreX, ky = pf.pxPerMetreY, [ox, oy] = pf.originPx;
  // the sheet's middle in plan: pixel (W / 2, H / 2) through the frame; its size: the picture's pixels at the floor's scale, per axis
  const w = W / kx, h = H / ky, cx = (W / 2 - ox) / kx - D.offset[0], cy = -(H / 2 - oy) / ky - D.offset[1];
  const g = new THREE.PlaneGeometry(w, h);              // uv (0, 1) = the picture's top left, which lies to the north-west
  g.rotateX(-Math.PI / 2);
  g.translate(cx, FL[key].level + PICTURE_LIFT, -cy);
  const tex = new THREE.Texture();
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.anisotropy = renderer.capabilities.getMaxAnisotropy();
  // unlit, the drawing's own colours; pulled in front of the slab (which itself is pulled in front of the walls below)
  const m = new THREE.Mesh(g, new THREE.MeshBasicMaterial({ map: tex, polygonOffset: true, polygonOffsetFactor: -2, polygonOffsetUnits: -2 }));
  m.name = key + ' plan picture';
  m.userData = { key, size: [W, H], metres: [w, h], centre: [cx, cy] };
  m.visible = false;
  pictureLayer.add(m); pictureObjs.push(m);
  return new Promise(resolve => {
    const img = new Image();
    img.onload = () => { tex.image = img; tex.needsUpdate = true; resolve(true); };
    img.onerror = () => { console.error('plan picture ' + key + ' could not be read'); resolve(false); };
    img.src = PICTURES[key];
  });
}));
// The tick, and ?picture=1 / 0 in the address (rule 2: off unless asked for).
const pictureParam = new URLSearchParams(location.search).get('picture');
if (pictureParam === '1' || pictureParam === '0') document.getElementById('picture').checked = pictureParam === '1';
const showPictures = () => { const on = check('picture'); pictureObjs.forEach(m => { m.visible = on && FL[m.userData.key].group.visible; }); };

let floorMode = 'both';
function applyFloor() { for (const f of Object.values(FL)) f.group.visible = floorMode === 'both' || floorMode === f.key; }
function check(id) { const el = document.getElementById(id); return !el || el.checked; }
function applyChecks() {
  plateObjs.forEach(o => { o.visible = check('plates'); });
  glassObjs.forEach(o => { o.visible = check('glass'); });
  singleObjs.forEach(o => { o.visible = check('single'); });
  showPictures();
}
// Floor buttons: in Walk they show (and change) the floor you are on; otherwise they show or hide floors.
function markFloors(st) {
  const key = st.mode === 'walk' ? st.floor : floorMode;
  document.querySelectorAll('#floors button').forEach(b => b.classList.toggle('on', b.dataset.f === key));
}

__MODES__
__FURNITURE_JS__

const FLOORS = D.floors.map(f => ({ key: f.key, name: f.name, level: f.level, stack: 'hotel', group: FL[f.key].group,
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
['plates', 'glass', 'rooms', 'single', 'picture'].forEach(id => { const el = document.getElementById(id); if (el) el.onchange = applyChecks; });
applyFloor();
__FURNITURE_INSTALL__
// Room names from the pictures, shown over the model in Orbit (on the floors that are showing).
const labels = D.rooms.map(r => {
  const el = document.createElement('div'); el.className = 'room'; el.textContent = r.label; document.body.appendChild(el);
  return { el, floor: r.floor, area: r.area || 0, p: new THREE.Vector3(r.x, 0, -r.y) };
});
const labelsByArea = [...labels].sort((a, b) => b.area - a.area);      // bigger rooms first (the pictures give no areas: as listed)
const levelOf = k => FLOORS.find(f => f.key === k).level;
const v = new THREE.Vector3();
// Names that would overlap on screen are moved apart: the first keeps its spot, a later one moves just above or below it
// (up to two rows away), and is hidden only when no free row is near.
function placeLabels() {
  const show = check('rooms') && modes.mode === 'orbit';
  // only the top floor that is showing: the ones below are under its floor plate
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
// read-outs for tests: the floors, the openings, the glass spots to walk into, and what is overhead at a spot
// (the height above the floor of the first thing that stops you, looking straight up from h0; null = open)
const upRay = new THREE.Raycaster(); upRay.firstHitOnly = true;
function upHit(key, x, y, h0 = 1.0) {
  const f = FLOORS.find(g => g.key === key);
  upRay.set(new THREE.Vector3(x, f.level + h0, -y), new THREE.Vector3(0, 1, 0)); upRay.far = 20;
  const hit = upRay.intersectObjects(FL[key].colliders.filter(m => m.visible), false)[0];
  return hit ? hit.distance + h0 : null;
}
// a level ray in any direction at height h above the floor: the first thing it stops on (distance, mesh name), or null
const flatRay = new THREE.Raycaster(); flatRay.firstHitOnly = true;
function rayHit(key, x, y, h, dx, dy, far = 3) {
  const f = FLOORS.find(g => g.key === key), n = Math.hypot(dx, dy) || 1;
  flatRay.set(new THREE.Vector3(x, f.level + h, -y), new THREE.Vector3(dx / n, 0, -dy / n)); flatRay.far = far;
  const hit = flatRay.intersectObjects(FL[key].colliders.filter(m => m.visible), false)[0];
  return hit ? { d: hit.distance, name: hit.object.name } : null;
}
// looking straight down from h0 above the floor: the height above the floor of the first thing below (null = nothing)
function downHit(key, x, y, h0 = 3.0) {
  const f = FLOORS.find(g => g.key === key);
  upRay.set(new THREE.Vector3(x, f.level + h0, -y), new THREE.Vector3(0, -1, 0)); upRay.far = 8;
  const hit = upRay.intersectObjects(FL[key].colliders.filter(m => m.visible), false)[0];
  return hit ? h0 - hit.distance : null;
}
window.__host = { FL, labels, openings: D.openings, probes: D.probes, floors: FLOORS, upHit, downHit, rayHit, model: D,
                  pictures: { objs: pictureObjs, ready: picturesReady, src: PICTURES, show: showPictures }__FURNITURE_HOST__ };
applyChecks();
modes.applyUrl();
renderer.setAnimationLoop(() => { modes.tick(); showPictures(); renderer.render(scene, camera); placeLabels(); });
</script>
</body>
</html>
'''

# ------------------------------------------------------------------------------------------------- the panel's words, from the model
kinds = {p['kind'] for p in M['parts']}
heights = sorted({f['wallHeight'] for f in M['floors']})
levels = ' and '.join(f"{f['name']} at {f['level']:+.2f} m".replace('+0.00', '0.00') for f in M['floors'])
frames = M.get('pictureFrame', {})
FLOOR = {f['key']: f for f in M['floors']}
NAME = {f['key']: f['name'] for f in M['floors']}


def inside(pt, ring):                      # even-odd rule: is the plan point inside the ring?
    x, y = pt
    c = False
    for (x1, y1), (x2, y2) in zip(ring, ring[1:] + ring[:1]):
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1): c = not c
    return c


def slabs(key, label=None):                # a floor's floor plates (with a label that starts so, if given)
    return [p for p in M['parts'] if p['kind'] == 'slab' and p['floor'] == key and (label is None or (p.get('label') or '').startswith(label))]


def on_plate(plates, x, y): return any(inside((x, y), p['o']) and not any(inside((x, y), h) for h in p['h']) for p in plates)


def steps_of(key): return [p for p in M['parts'] if p['kind'] == 'step' and p['floor'] == key]


# The scale: the owner's one real dimension is the width of the main stair (the flight from the lowest floor up to the next
# one); the model builds it that wide between its side walls, so the width of its steps says it. Pixels per metre per axis.
def scale_words(key, first):
    pf = frames[key]
    kx, ky = pf['pxPerMetreX'], pf['pxPerMetreY']
    if abs(kx - ky) < 0.005: return f"{NAME[key]}'s {kx:.2f}" + (' px per metre' if first else '')
    return f"{NAME[key]}'s picture has {kx:.2f} px per metre across and {ky:.2f} down"


first = M['floors'][0]['key']
flight = steps_of(first)
stair_w = max(max(max(x for x, _ in p['o']) - min(x for x, _ in p['o']), max(y for _, y in p['o']) - min(y for _, y in p['o'])) for p in flight) if flight else None   # each step's longer side
scale_txt = ', '.join(scale_words(f['key'], i == 0) for i, f in enumerate(f for f in M['floors'] if f['key'] in frames))
lift_w = sorted({o['width'] for o in M['openings'] if o.get('liftDoor')})
intro = (f"No CAD: read from two presentation pictures, {levels}, scaled from the one real size the owner gave, the main "
         f"stair's width between its side walls, {stair_w:.2f} m: {scale_txt}."
         + (f" Lift doors built {lift_w[0]:.2f} m wide (the owner's)." if len(lift_w) == 1 else '')
         + (" The circles with a cross are lights, not furniture." if not any(k['key'] == 'lamp' for k in M.get('furnitureKinds') or []) else '')
         + " Tick Plan picture to see each picture under the model.")
hatches = [o for o in M['openings'] if o.get('hatch')]
sills = sorted({o['sill'] for o in hatches})
legend_items = [('#e3ddd3', 'Walls and door lintels, ' + ' / '.join(f'{h:.2f}' for h in heights) + ' m (up to the next floor)'
                 + (f"; {len(hatches)} hatch{'es' if len(hatches) > 1 else ''} ({', '.join(o['subtype'] for o in hatches)}), open from "
                    f"{' / '.join(f'{s:.2f}' for s in sills)} to {max(o['head'] for o in hatches):.2f} m" if hatches else ''))]
if 'parapet' in kinds:                     # low walls (a parapet at railing height: the outside stair's spine)
    lows = [p for p in M['parts'] if p['kind'] == 'parapet']
    low_h = ' / '.join(sorted({'%.2f' % (p['z1'] - p['z0']) for p in lows}))
    low_what = ', '.join(sorted({(p.get('label') or 'low wall').replace(' (low wall)', '') for p in lows}))
    legend_items.append(('#e3ddd3', f'Low walls, {low_h} m: {low_what}'))
if 'glass' in kinds:
    legend_items.append(('#9cc3d5', 'Glass read from the pictures, full height' + (', and its frame posts' if 'mullion' in kinds else '')))
if 'railing' in kinds:
    rails = [(p.get('label') or '') for p in M['parts'] if p['kind'] == 'railing']
    where = [w for w, n in (('round the open stair', sum('open stair' in r for r in rails)), ("on the terrace's open edges", sum('terrace' in r for r in rails))) if n]
    legend_items.append(('#77727c', f"Railings, {M['railingHeight']:.2f} m" + (', ' + ' and '.join(where) if where else '')))
flat = [(f['key'], M['stairs'][f['key']]['below']) for f in M['floors'] if f['key'] in M['stairs'] and M['stairs'][f['key']]['below']]
if any(steps_of(f['key']) for f in M['floors']) or flat:
    said = []
    for i, f in enumerate(M['floors']):
        st = steps_of(f['key'])
        if not st: continue
        top = max(p['z1'] for p in st)
        nxt = M['floors'][i + 1] if i + 1 < len(M['floors']) else None
        if nxt and abs(f['level'] + top + (top / len(st)) - nxt['level']) < 0.01:      # the last riser lands on the next floor
            said.append(f"{len(st)} steps from {f['name']} up to {nxt['name']}" + ("'s open stair" if any(v['what'] == 'stair' for v in M['voids'].get(nxt['key'], [])) else ''))
        else:
            said.append(f"{len(st)} steps from {f['name']} up toward the floor above (not in the pictures), ending at {top:+.2f} m")
    for key, a in flat:                    # flat tread lines: name the stair by the nearest room name (within 3 m of their middle)
        xs, ys = a[0::2], a[1::2]
        cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
        near = sorted((math.hypot(r['x'] - cx, r['y'] - cy), r['label']) for r in M['rooms'] if r['floor'] == key)
        what = f"the {near[0][1].lower()}" if near and near[0][0] < 3 else f"{NAME[key]}'s other stair"
        said.append(f"{what} as flat tread lines (up or down not known)")
    legend_items.append(('#b9c7b4', 'Stairs: ' + '; '.join(said)))
# The floor plates, and the outdoor ones at the same level: a slab labelled 'forecourt' (how deep it is in front of the doors
# that open onto it, from the wall's outer face, as drawn), and a terrace (railings labelled 'terrace' on its edges).
plate_txt = 'Floor plates: the inside of the walls and glass'
outdoor = []
for f in M['floors']:
    fc = slabs(f['key'], 'forecourt')
    if not fc: continue
    allp, depth = slabs(f['key']), []
    for o in M['openings']:
        if o['floor'] != f['key'] or o['kind'] not in ('door', 'passage'): continue
        for sgn in (1, -1):                # the side whose spot 0.3 m beyond the wall face is on the forecourt
            nx, ny, t = o['nx'] * sgn, o['ny'] * sgn, o['wallThickness'] / 2
            if on_plate(fc, o['x'] + nx * (t + 0.3), o['y'] + ny * (t + 0.3)):
                d = 0.0
                while d < 20 and on_plate(allp, o['x'] + nx * (t + d + 0.005), o['y'] + ny * (t + d + 0.005)): d += 0.01
                depth.append(d)
    outdoor.append(f"{f['name']}'s forecourt" + (f" ({min(depth):.2f} m deep in front of the entrance doors, as drawn)" if depth else ''))
if any('terrace' in (p.get('label') or '') for p in M['parts'] if p['kind'] == 'railing'):
    outdoor.append(f"{NAME[next(p['floor'] for p in M['parts'] if p['kind'] == 'railing' and 'terrace' in (p.get('label') or ''))]}'s terrace")
if outdoor: plate_txt += '; outdoors at the same level, ' + ' and '.join(outdoor)
legend_items.append(('#d4d8d2', plate_txt))
legend = ''.join(f'<div><span style="background:{c}"></span>{t}</div>' for c, t in legend_items)
floor_buttons = ''.join(f'<button data-f="{f["key"]}">{f["name"]}</button>' for f in M['floors'])
# The furniture boxes, as the bank page has them: the module, its call (the list goes last in the side panel), the read-outs for
# tests (the furniture, the camera and the orbit controls) and the panel rule: the list makes the panel scroll, and its bottom
# edge must then stay above the hint line (12 px type, one line of 17 px or two when the window is narrow, 10 px from the
# bottom): the panel's whole box is at most 64 px short of the window's height, which is 90 px for its content box.
# Without a furniture list in the model all five vanish.
furniture_parts = {
    '__FURNITURE_CSS__': '''
  #panel { max-height:calc(100vh - 90px); }''',
    '__FURNITURE_JS__': '\n' + furniture_js,
    '__FURNITURE_INSTALL__': '''
// ---------------------------------------------------------------- furniture boxes: one per piece, a legend with a height per kind
const furnitureList = document.createElement('div');
const furniture = installFurnitureBoxes({ THREE, model: D, FL, panel: furnitureList, canvas: renderer.domElement, camera,
                                          getMode: () => modes.mode, params: new URLSearchParams(location.search), project: D.photoName });
// the furniture list goes last in the side panel
document.getElementById('panel').appendChild(furnitureList);
''',
    '__FURNITURE_HOST__': ', furniture, camera, controls',
}

out = (html.replace('__DATA__', json.dumps(M, separators=(',', ':'), ensure_ascii=False))
           .replace('__PICTURES__', json.dumps(pictures, separators=(',', ':')))
           .replace('__LIFT__', repr(PICTURE_LIFT))
           .replace('__SHA__', SHA).replace('__INTRO__', intro).replace('__LEGEND__', legend)
           .replace('__FLOORBUTTONS__', floor_buttons)
           .replace('__SHORT__', M.get('shortName', M['project']))
           .replace('__MODES__', modes))
for marker, text in furniture_parts.items():
    out = out.replace(marker, text if has_furniture else '')
Path(sys.argv[1]).write_text(out, encoding='utf-8')
print('written', sys.argv[1], round(len(out) / 1024), 'KB | model data', SHA, '| pictures', ', '.join(f'{k} {round(len(v) * 3 / 4 / 1024)} KB' for k, v in pictures.items()))
