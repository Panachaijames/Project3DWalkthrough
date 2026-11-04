// ---------------------------------------------------------------------------
// Viewer modes: Orbit / Walk / Ghost, plus a Camera tool that takes photos.
// Inlined into each viewer's module script (THREE is in scope there).
//
//   Orbit  - the dollhouse view (OrbitControls).
//   Walk   - first person at eye height; walls and glass block you; you stay on the floor.
//   Ghost  - fly anywhere, through walls and floors.
//   Camera - lens (mm), eye height, tilt, straight verticals, frame, size; P takes a photo.
//   Touch  - phones and tablets: drag to look, a stick to move, buttons for floors (Walk) or up / down (Ghost).
//
// Host passes:
//   { scene, camera, renderer, controls, panel, anchor, hint, project,
//     floors: [{ key, name, level, stack, group, colliders: [Mesh], walkables: [Mesh] }],
//     restoreVisibility: () => void,          // re-applies the host's own floor buttons
//     onChange: ({ mode, floor }) => void }   // optional: the mode or the walked floor changed
// Returns { tick, setMode, goToFloor, takePhoto, applyUrl, lock, mode, state, probe }.
// ---------------------------------------------------------------------------
function installViewerModes(o) {
  const { scene, camera, renderer, controls } = o;
  const canvas = renderer.domElement;
  const floors = o.floors;
  const byKey = {};
  floors.forEach(f => { byKey[f.key] = f; });

  const EYE = 1.6, RADIUS = 0.3, WALK_SPEED = 1.5, RUN_SPEED = 3.4, LOOK = 0.0025, LOOK_TOUCH = 0.004;
  const D2R = Math.PI / 180;
  const lensFov = mm => 2 * Math.atan(12 / mm) / D2R;        // angle across the short side of a 36 x 24 mm frame
  const s = {
    mode: 'orbit', floor: floors[0], pos: new THREE.Vector3(), yaw: 0, pitch: 0, eye: EYE,
    lens: 24, orbitLens: Math.round(12 / Math.tan(camera.fov * D2R / 2)), straight: false,
    ghostSpeed: 6, keys: new Set(), saved: null, drag: null, dragMoved: false,
    frame: '3:2', size: 1920, grid: true, camOpen: false, last: performance.now(),
    touch: matchMedia('(pointer: coarse)').matches, stick: { id: null, x: 0, y: 0 }, vert: 0, locked: false,
  };
  const orbitNear = camera.near;
  camera.rotation.order = 'YXZ';
  const ray = new THREE.Raycaster();
  ray.firstHitOnly = true;
  const DOWN = new THREE.Vector3(0, -1, 0);
  const narrow = () => matchMedia('(max-width:700px)').matches;     // portrait phones: Camera panel across the top

  // ---------------------------------------------------------------- UI
  const css = document.createElement('style');
  css.textContent = `
.vm-panel,.vm-hint{z-index:6}
.vm-label{font-size:11px;letter-spacing:.06em;text-transform:uppercase;color:var(--muted);margin:10px 0 4px}
.vm-row{display:flex;gap:6px;flex-wrap:wrap;align-items:center}
#vm-hud{position:fixed;top:12px;left:50%;transform:translateX(-50%);max-width:calc(100vw - 24px);box-sizing:border-box;background:#1d2329eb;color:#fff;border-radius:999px;padding:6px 8px 6px 14px;font-size:12.5px;display:none;align-items:center;gap:8px;z-index:7}
#vm-hud span{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
#vm-hud button{padding:3px 10px;font-size:12px;flex:none}
#vm-hud .vm-narrow{display:none}
#vm-cross{position:fixed;left:50%;top:50%;width:14px;height:14px;margin:-7px 0 0 -7px;pointer-events:none;display:none;z-index:4}
#vm-cross:before,#vm-cross:after{content:'';position:absolute;background:#fff;box-shadow:0 0 2px #000a}
#vm-cross:before{left:6px;top:0;width:2px;height:14px}
#vm-cross:after{top:6px;left:0;height:2px;width:14px}
#vm-cam{position:fixed;top:12px;right:12px;width:min(270px,calc(100vw - 48px));max-height:calc(100vh - 60px);overflow:auto;background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:12px 14px;box-shadow:0 2px 10px #0001;display:none;z-index:8;font-size:13px}
#vm-cam h2{font-size:14px;margin:0 0 4px;display:flex;justify-content:space-between;align-items:center}
#vm-cam h2 button{padding:0 8px}
#vm-cam .vm-f{margin:9px 0}
#vm-cam .vm-f>div:first-child{display:flex;justify-content:space-between;color:var(--muted);font-size:12px;margin-bottom:2px}
#vm-cam input[type=range]{width:100%;margin:0}
#vm-cam select{font:inherit;font-size:13px;padding:3px 6px;border:1px solid var(--line);border-radius:6px;background:#fff;color:var(--ink)}
#vm-cam .vm-note{color:var(--muted);font-size:11.5px;margin:2px 0 6px}
#vm-shot{width:100%;margin-top:10px;padding:8px;font-weight:600}
#vm-photos{display:flex;gap:6px;flex-wrap:wrap;margin-top:8px}
#vm-photos img{width:72px;height:48px;object-fit:cover;border-radius:4px;border:1px solid var(--line);cursor:pointer}
#vm-frame{position:fixed;pointer-events:none;display:none;z-index:3}
#vm-frame.vm-crop{border:1px solid #fffd;box-shadow:0 0 0 100vmax #0e121666}
#vm-frame i{position:absolute;background:#ffffffa0}
#vm-flash{position:fixed;inset:0;background:#fff;opacity:0;pointer-events:none;z-index:9}
#vm-err{position:fixed;right:12px;bottom:12px;max-width:420px;background:#b42318;color:#fff;font-size:12px;padding:8px 10px;border-radius:8px;display:none;z-index:10;white-space:pre-wrap}
#vm-stick{position:fixed;left:22px;bottom:26px;width:116px;height:116px;border-radius:50%;background:#1d232940;border:2px solid #ffffffb0;display:none;z-index:7;touch-action:none;user-select:none;-webkit-user-select:none}
#vm-stick b{position:absolute;left:50%;top:50%;width:50px;height:50px;margin:-25px 0 0 -25px;border-radius:50%;background:#fffffff0;box-shadow:0 1px 5px #0006;pointer-events:none}
#vm-ud{position:fixed;right:22px;bottom:26px;display:none;flex-direction:column;gap:10px;z-index:7}
#vm-ud button{min-width:104px;padding:12px 10px;border-radius:12px;background:#1d2329c0;border:2px solid #ffffffb0;color:#fff;font-weight:600;touch-action:none;user-select:none;-webkit-user-select:none}
.vm-off{opacity:.45;pointer-events:none}
.vm-crowded .vm-panel{display:none}
/* Phones, upright (narrow) or on their side (short): no side panel while walking or framing a photo. */
@media (max-width:700px),(max-height:500px){
.vm-fp .vm-panel,.vm-fp .vm-hint,.vm-camopen .vm-panel{display:none}
#vm-hud .vm-narrow{display:inline-block}
#vm-hud .vm-more{display:none}
#vm-cam .vm-f{margin:5px 0}
#vm-shot{margin-top:6px;padding:7px}
#vm-photos img{width:54px;height:36px}
#vm-photos img:nth-child(n+5){display:none}
}
@media (max-width:700px){
#vm-cam{top:58px;left:12px;right:12px;width:auto;max-height:42vh;padding:8px 12px}
}
/* Wider screens: in Walk and Ghost the Camera panel starts below the top bar, so Exit stays clickable,
   and with touch controls it ends above the Photo / Upstairs / Downstairs buttons. */
@media (min-width:701px){
.vm-fp #vm-cam{top:58px;max-height:calc(100vh - 70px)}
.vm-touchui #vm-cam{max-height:calc(100vh - 270px);min-height:110px}
}
#vm-snap{background:var(--accent)!important;border-color:#fff!important}
`;
  document.head.appendChild(css);
  o.panel.classList.add('vm-panel');
  if (o.hint) o.hint.classList.add('vm-hint');

  const modeBox = document.createElement('div');
  modeBox.innerHTML = `<div class="vm-label">Look around</div>
<div class="vm-row" id="vm-modes"><button data-m="orbit" class="on">Orbit</button><button data-m="walk">Walk</button><button data-m="ghost">Ghost</button><button id="vm-cam-btn">Camera</button></div>`;
  if (o.anchor && o.anchor.parentNode) o.anchor.parentNode.insertBefore(modeBox, o.anchor.nextSibling);
  else o.panel.appendChild(modeBox);

  const hud = document.createElement('div');
  hud.id = 'vm-hud';
  hud.innerHTML = '<span id="vm-hud-t"></span><button id="vm-hud-cam" class="vm-narrow">Camera</button><button id="vm-exit">Exit</button>';
  const cross = document.createElement('div'); cross.id = 'vm-cross';
  const frameEl = document.createElement('div'); frameEl.id = 'vm-frame';
  frameEl.innerHTML = '<i style="left:33.33%;top:0;bottom:0;width:1px"></i><i style="left:66.66%;top:0;bottom:0;width:1px"></i><i style="top:33.33%;left:0;right:0;height:1px"></i><i style="top:66.66%;left:0;right:0;height:1px"></i>';
  const flashEl = document.createElement('div'); flashEl.id = 'vm-flash';
  const errEl = document.createElement('div'); errEl.id = 'vm-err';
  const stick = document.createElement('div'); stick.id = 'vm-stick'; stick.innerHTML = '<b></b>';
  const ud = document.createElement('div'); ud.id = 'vm-ud';
  ud.innerHTML = '<button id="vm-snap" style="display:none">Photo</button><button id="vm-up"></button><button id="vm-down"></button>';
  const cam = document.createElement('div'); cam.id = 'vm-cam';
  cam.innerHTML = `<h2>Camera <button id="vm-cam-close" title="Close">&times;</button></h2>
<div class="vm-f"><div><span>Lens</span><span id="vm-lens-v"></span></div><input id="vm-lens" type="range" min="12" max="85" step="1">
  <div class="vm-row" style="margin-top:4px"><button data-mm="16">16</button><button data-mm="24">24</button><button data-mm="35">35</button><button data-mm="50">50</button></div></div>
<div id="vm-first">
  <div class="vm-f"><div><span>Eye height</span><span id="vm-eye-v"></span></div><input id="vm-eye" type="range" min="0.8" max="2.2" step="0.05"></div>
  <div class="vm-f"><div><span>Tilt</span><span id="vm-tilt-v"></span></div><input id="vm-tilt" type="range" min="-60" max="60" step="1"></div>
  <label><input type="checkbox" id="vm-straight"> Straight verticals</label>
</div>
<div class="vm-note" id="vm-first-note">Height and tilt work in Walk and Ghost. In Orbit, drag to set the angle.</div>
<div class="vm-f"><div><span>Frame and size</span><span id="vm-px"></span></div><div class="vm-row">
  <select id="vm-frame-sel"><option value="screen">Whole screen</option><option value="16:9">16:9</option><option value="3:2">3:2</option><option value="4:3">4:3</option><option value="1:1">1:1</option><option value="4:5">4:5</option><option value="9:16">9:16</option></select>
  <select id="vm-size"><option value="1920">HD</option><option value="3840">4K</option></select></div></div>
<label><input type="checkbox" id="vm-grid"> Thirds grid</label>
<button id="vm-shot">Take photo (P)</button>
<div id="vm-photos"></div>`;
  document.body.append(hud, cross, frameEl, flashEl, errEl, stick, ud, cam);

  const $ = id => document.getElementById(id);
  const ui = {
    lens: $('vm-lens'), lensV: $('vm-lens-v'), eye: $('vm-eye'), eyeV: $('vm-eye-v'), tilt: $('vm-tilt'), tiltV: $('vm-tilt-v'),
    straight: $('vm-straight'), first: $('vm-first'), firstNote: $('vm-first-note'), frame: $('vm-frame-sel'), size: $('vm-size'),
    grid: $('vm-grid'), photos: $('vm-photos'), hudT: $('vm-hud-t'), px: $('vm-px'), up: $('vm-up'), down: $('vm-down'), snap: $('vm-snap'),
    knob: stick.firstChild,
  };
  ui.frame.value = s.frame; ui.size.value = String(s.size); ui.grid.checked = s.grid;

  // Errors show on the page, so a problem is never silent.
  const showErr = msg => { errEl.textContent = 'Viewer error: ' + msg; errEl.style.display = 'block'; };
  addEventListener('error', e => showErr(e.message || String(e.error)));
  addEventListener('unhandledrejection', e => showErr(String(e.reason && e.reason.message || e.reason)));

  // ---------------------------------------------------------------- geometry helpers
  const visibleColliders = f => f.colliders.filter(m => m.visible);
  function hitAhead(p, dir, dist, f) {        // p = eye position; rays at knee and chest height, across the shoulders
    const cols = visibleColliders(f);
    if (!cols.length) return null;
    const side = new THREE.Vector3(-dir.z, 0, dir.x);
    for (const h of [0.35, 1.2]) {
      // At most 7.5 cm apart, so a partition thicker than that cannot slip between; the outer pair stays 1.5 cm inside
      // the body's edge so that sliding along a wall you touch is not blocked by the wall itself.
      for (const k of [0, -0.25, 0.25, -0.5, 0.5, -0.75, 0.75, -0.95, 0.95]) {
        const origin = new THREE.Vector3(p.x, f.level + h, p.z).addScaledVector(side, k * RADIUS);
        ray.set(origin, dir); ray.far = dist + RADIUS;
        const hit = ray.intersectObjects(cols, false)[0];
        if (hit) return hit;
      }
    }
    return null;
  }
  function onFloor(p, f) {                     // is there floor under this point? (no walkables = no check)
    if (!f.walkables.length) return true;
    ray.set(new THREE.Vector3(p.x, f.level + 1, p.z), DOWN); ray.far = 1.6;
    return ray.intersectObjects(f.walkables, false).length > 0;
  }
  function clearance(p, f) {                   // distance to the nearest wall in 8 directions (up to 3 m)
    const cols = visibleColliders(f);
    if (!cols.length) return Infinity;
    let min = Infinity;
    for (const h of [0.35, 1.2]) {             // knee and chest height, as walking checks: railings are 1 m high
      const origin = new THREE.Vector3(p.x, f.level + h, p.z);
      for (let i = 0; i < 8; i++) {
        const a = i * Math.PI / 4;
        ray.set(origin, new THREE.Vector3(Math.cos(a), 0, Math.sin(a))); ray.far = 3;
        const hit = ray.intersectObjects(cols, false)[0];
        if (hit) min = Math.min(min, hit.distance);
      }
    }
    return min;
  }
  function findFree(p, want = 0.5, again = true) {   // nearest spot with room to stand, spiralling out; tries for `want` m first
    const f = s.floor;
    const passes = want > 0.5 ? [[want, 6], [0.5, 12]] : [[0.5, 12]];
    for (const [need, maxR] of passes) {
      for (let r = 0; r <= maxR; r += 0.5) {
        const n = r === 0 ? 1 : Math.max(8, Math.round(r * 6));
        for (let i = 0; i < n; i++) {
          const a = i / n * Math.PI * 2, q = new THREE.Vector3(p.x + r * Math.cos(a), p.y, p.z + r * Math.sin(a));
          if (clearance(q, f) >= need && onFloor(q, f)) { p.x = q.x; p.z = q.z; return true; }
        }
      }
    }
    // Nothing near (e.g. coming from Ghost far outside): try again from the middle of the floor.
    if (again) {
      const c = startPoint(f, { x: Infinity, z: Infinity });
      if (Number.isFinite(c.x)) { p.x = c.x; p.z = c.z; return findFree(p, want, false); }
    }
    return false;
  }
  function openAhead(yaw, far) {               // free distance straight ahead at chest height
    const f = s.floor, cols = visibleColliders(f);
    if (!cols.length) return far;
    ray.set(new THREE.Vector3(s.pos.x, f.level + 1.2, s.pos.z), new THREE.Vector3(-Math.sin(yaw), 0, -Math.cos(yaw)));
    ray.far = far;
    const hit = ray.intersectObjects(cols, false)[0];
    return hit ? hit.distance : far;
  }
  function faceOpen() {                        // staring at a wall? turn to the most open view near the current heading
    if (openAhead(s.yaw, 4) >= 4) return;
    let best = s.yaw, bestScore = -Infinity;
    for (let i = 1; i < 24; i++) {
      const yaw = s.yaw + i / 24 * Math.PI * 2;
      const score = openAhead(yaw, 15) * (0.7 + 0.3 * Math.cos(yaw - s.yaw));
      if (score > bestScore) { bestScore = score; best = yaw; }
    }
    s.yaw = Math.atan2(Math.sin(best), Math.cos(best));
  }
  function startPoint(f, p) {                  // keep p if it is over this floor, otherwise use the middle of the floor
    if (!f.box) f.box = new THREE.Box3().setFromObject(f.group);
    const b = f.box;
    if (b.isEmpty() || (p.x >= b.min.x && p.x <= b.max.x && p.z >= b.min.z && p.z <= b.max.z)) return p;
    return b.getCenter(new THREE.Vector3());
  }
  function walkMove(d) {                       // d = horizontal step this frame; slide along walls
    const f = s.floor, dist = d.length(), dir = d.clone().divideScalar(dist);
    const hit = hitAhead(s.pos, dir, dist, f);
    let step = d;
    if (hit) {
      const n = hit.face.normal.clone().transformDirection(hit.object.matrixWorld);
      n.y = 0;
      if (n.lengthSq() < 1e-6) return;
      n.normalize();
      if (n.dot(dir) > 0) n.negate();
      step = d.clone().addScaledVector(n, -d.dot(n));   // the part of the step along the wall
      const sl = step.length();
      if (sl < 1e-5 || hitAhead(s.pos, step.clone().divideScalar(sl), sl, f)) return;
    }
    const next = s.pos.clone().add(step);
    if (onFloor(next, f)) { s.pos.copy(next); return; }
    // At a floor edge (a void, the edge of a slab): slide along it by trying the x and z parts of the step, larger first.
    const parts = [new THREE.Vector3(step.x, 0, 0), new THREE.Vector3(0, 0, step.z)].sort((a, b) => b.lengthSq() - a.lengthSq());
    for (const part of parts) {
      const pl = part.length();
      if (pl < 1e-5 || hitAhead(s.pos, part.clone().divideScalar(pl), pl, f)) continue;
      const q = s.pos.clone().add(part);
      if (onFloor(q, f)) { s.pos.copy(q); return; }
    }
  }

  // ---------------------------------------------------------------- camera
  const aspectNow = () => canvas.clientWidth / Math.max(1, canvas.clientHeight);
  function viewFov(mm) {                       // vertical field of view; the lens spans the screen's short side
    const a = aspectNow();
    return a >= 1 ? lensFov(mm) : 2 * Math.atan(Math.tan(lensFov(mm) * D2R / 2) / a) / D2R;
  }
  const wideAngle = mm => 2 * Math.atan(Math.tan(viewFov(mm) * D2R / 2) * aspectNow()) / D2R;
  const ratio = v => { const [a, b] = v.split(':').map(Number); return a / b; };
  function frameRect() {
    const cw = canvas.clientWidth, ch = canvas.clientHeight;
    if (s.frame === 'screen') return { x: 0, y: 0, w: cw, h: ch };
    // Frame the shot in the part of the screen the panels leave free, so the photo is exactly what you can see.
    let left = 0, right = cw, top = 0, bottom = ch;
    if (s.camOpen) {
      const c = cam.getBoundingClientRect();
      if (narrow()) top = c.bottom + 8; else right = c.left - 8;
      const p = o.panel.getBoundingClientRect();
      if (p.width && p.right < cw / 2) left = p.right + 8;
    }
    if (s.mode !== 'orbit') top = Math.max(top, 58);       // below the top bar in Walk and Ghost
    // The touch stick and floor buttons: reserved whenever the device has touch, so switching input never moves the frame.
    if ((s.touch || navigator.maxTouchPoints > 0) && s.mode !== 'orbit') bottom = ch - 156;
    if (right - left < cw * 0.3) { left = 0; right = cw; }
    if (bottom - top < ch * 0.22) { top = 0; bottom = ch; }
    const a = ratio(s.frame), rw = right - left, rh = bottom - top;
    let w = rw * 0.94, h = w / a;
    if (h > rh * 0.9) { h = rh * 0.9; w = h * a; }
    return { x: left + (rw - w) / 2, y: top + (rh - h) / 2, w, h };
  }
  function outSize(r) {                        // photo size in pixels: the long side is HD or 4K
    const long = s.size;
    return r.w >= r.h ? { w: long, h: Math.round(long * r.h / r.w) } : { w: Math.round(long * r.w / r.h), h: long };
  }
  // Straight verticals: keep the camera level and slide the picture up or down instead of tilting (CSS px).
  const shiftPx = () => s.mode !== 'orbit' && s.straight ? -Math.tan(s.pitch) / (2 * Math.tan(camera.fov * D2R / 2)) * canvas.clientHeight : 0;
  function applyProjection() {
    const cw = canvas.clientWidth, ch = canvas.clientHeight;
    camera.aspect = cw / Math.max(1, ch);
    camera.fov = viewFov(s.mode === 'orbit' ? s.orbitLens : s.lens);
    const shift = shiftPx();
    if (shift) camera.setViewOffset(cw, ch, 0, shift, cw, ch);
    else camera.clearViewOffset();
    camera.updateProjectionMatrix();
  }
  function applyCamera() {
    if (s.mode === 'orbit') return;
    camera.position.copy(s.pos);
    camera.rotation.set(s.straight ? 0 : s.pitch, s.yaw, 0, 'YXZ');
    applyProjection();
  }
  function clampPitch() {
    const lim = (s.straight ? 35 : 85) * D2R;
    s.pitch = Math.max(-lim, Math.min(lim, s.pitch));
  }

  // ---------------------------------------------------------------- floors and visibility
  const pickFloor = () => floors.filter(f => f.group.visible).sort((a, b) => a.level - b.level)[0] || floors[0];
  const stackOf = f => floors.filter(g => g.stack === f.stack).sort((a, b) => a.level - b.level);
  function floorAtHeight(y) {                  // the floor at this height, among the floors that are showing
    const base = stackOf(s.floor).some(f => f.group.visible) ? s.floor : pickFloor();
    const all = stackOf(base), shown = all.filter(f => f.group.visible), stack = shown.length ? shown : all;
    const list = stack.filter(f => f.level <= y + 0.1);
    return list.length ? list[list.length - 1] : stack[0];
  }
  // In Ghost you are "on" a floor once your eye is 0.3 m above it (not a full eye height), so a small dip keeps the floor.
  const currentFloor = () => s.mode === 'ghost' ? floorAtHeight(s.pos.y - 0.3) : s.floor;
  function applyVisibility() {
    if (s.mode === 'walk') floors.forEach(f => { f.group.visible = f.stack === s.floor.stack; });
    else o.restoreVisibility();
  }
  function goToFloor(key) {
    const f = byKey[key];
    if (!f || s.mode === 'orbit' || (s.mode === 'walk' && f === s.floor)) return;
    if (s.mode === 'walk') {
      s.floor = f;
      const p = startPoint(f, s.pos);
      s.pos.set(p.x, f.level + s.eye, p.z);
      findFree(s.pos); faceOpen();
    } else {
      s.pos.y += f.level - currentFloor().level; s.floor = f;
    }
    applyVisibility(); applyCamera(); updateHud();
  }
  function changeFloor(step) {
    const cur = currentFloor(), list = stackOf(cur), next = list[list.indexOf(cur) + step];
    if (next) goToFloor(next.key);
  }

  // ---------------------------------------------------------------- modes
  function setMode(m, opt = {}) {
    const from = s.mode;
    if (m === from && !opt.point) return;
    if (from === 'orbit' && m !== 'orbit') {
      s.saved = { pos: camera.position.clone(), target: controls.target.clone() };
      const dir = controls.target.clone().sub(camera.position).normalize();
      s.yaw = Math.atan2(-dir.x, -dir.z);
      controls.enabled = false;
      camera.near = 0.05;
      if (document.activeElement && document.activeElement.blur) document.activeElement.blur();
      s.floor = opt.floor || pickFloor();
      if (m === 'ghost') {
        s.pos.copy(camera.position);
        s.pitch = Math.asin(Math.max(-1, Math.min(1, dir.y)));
      } else {
        const start = startPoint(s.floor, opt.point || controls.target);
        s.pos.set(start.x, s.floor.level + s.eye, start.z);
        findFree(s.pos, opt.point ? 0.5 : 1.0);    // from a button: somewhere with room around you
        s.pitch = 0;
        faceOpen();
      }
    } else if (from === 'ghost' && m === 'walk') {
      // Land on the floor below you; from far outside, start in the middle of that floor.
      s.floor = floorAtHeight(s.pos.y - 0.3);
      const p = startPoint(s.floor, s.pos);
      s.pos.set(p.x, s.floor.level + s.eye, p.z); findFree(s.pos);
    } else if (from === 'walk' && m === 'walk' && opt.point) {
      s.floor = opt.floor || s.floor;
      s.pos.set(opt.point.x, s.floor.level + s.eye, opt.point.z); findFree(s.pos); faceOpen();
    }
    if (m === 'orbit') {
      if (document.pointerLockElement === canvas) document.exitPointerLock();
      camera.near = orbitNear;
      if (s.saved) { camera.position.copy(s.saved.pos); controls.target.copy(s.saved.target); }
      controls.enabled = true;
      s.keys.clear(); s.drag = null; s.vert = 0; resetStick();
    }
    s.mode = m;
    clampPitch();
    applyVisibility();
    applyProjection();
    if (m === 'orbit') controls.update(); else applyCamera();
    document.querySelectorAll('#vm-modes [data-m]').forEach(b => b.classList.toggle('on', b.dataset.m === m));
    updateHud(); syncCamPanel();
  }

  function updateHud() {
    const fp = s.mode !== 'orbit';
    document.body.classList.toggle('vm-fp', fp);
    document.body.classList.toggle('vm-camopen', s.camOpen);
    // Not enough room for the side panel, the Camera panel and a photo frame between them: hide the side panel.
    document.body.classList.toggle('vm-crowded', s.camOpen && !narrow() && innerWidth - 650 < innerWidth * 0.45);
    hud.style.display = fp ? 'flex' : 'none';
    cross.style.display = fp && !s.camOpen ? 'block' : 'none';
    if (s.mode === 'walk') {
      const more = s.touch ? 'drag to look &middot; stick to move'
        : `drag or click to look &middot; W A S D to move, Shift to run &middot; PgUp / PgDn: other floor &middot; wheel: lens ${Math.round(s.lens)} mm &middot; Esc`;
      ui.hudT.innerHTML = `<b>Walk</b> &middot; ${s.floor.name}<span class="vm-more"> &middot; ${more}</span>`;
    } else if (s.mode === 'ghost') {
      const more = s.touch ? 'drag to look &middot; stick to fly'
        : `W A S D &middot; Space up, C down &middot; Shift fast &middot; wheel: speed ${s.ghostSpeed.toFixed(1)} m/s &middot; Esc`;
      ui.hudT.innerHTML = `<b>Ghost</b> &middot; through walls<span class="vm-more"> &middot; ${more}</span>`;
    }
    // Touch controls: a stick to move; Upstairs / Downstairs in Walk, hold Up / Down in Ghost.
    const touchOn = fp && s.touch;
    document.body.classList.toggle('vm-touchui', touchOn);
    stick.style.display = touchOn ? 'block' : 'none';
    ud.style.display = touchOn ? 'flex' : 'none';
    ui.snap.style.display = touchOn && s.camOpen ? 'block' : 'none';     // a shutter button by your thumb while framing
    if (touchOn) {
      const list = stackOf(s.floor), i = list.indexOf(s.floor);
      ui.up.textContent = s.mode === 'walk' ? 'Upstairs' : 'Up';
      ui.down.textContent = s.mode === 'walk' ? 'Downstairs' : 'Down';
      ui.up.classList.toggle('vm-off', s.mode === 'walk' && i >= list.length - 1);
      ui.down.classList.toggle('vm-off', s.mode === 'walk' && i <= 0);
    }
    if (o.hint) {
      o.hint.textContent = !fp
        ? (s.touch ? 'Drag to orbit · pinch to zoom · Walk or Ghost to look around inside'
          : 'Drag to orbit · right-drag to pan · scroll to zoom · double-click a floor to walk there · 1 / 2 / 3: Orbit / Walk / Ghost · P: photo')
        : (s.touch ? 'Drag to look · stick to move · Exit (top) returns to Orbit'
          : 'Click to capture the mouse (Esc frees it, Esc again returns to Orbit) · 1 / 2 / 3: Orbit / Walk / Ghost · P: photo');
    }
    if (o.onChange) o.onChange({ mode: s.mode, floor: s.floor.key });
  }

  // ---------------------------------------------------------------- camera panel
  function syncCamPanel() {
    const first = s.mode !== 'orbit';
    const lens = first ? s.lens : s.orbitLens;
    ui.lens.value = lens;
    ui.lensV.textContent = `${Math.round(lens)} mm · ${Math.round(wideAngle(lens))}° wide`;
    ui.first.classList.toggle('vm-off', !first);
    ui.firstNote.style.display = first ? 'none' : 'block';
    ui.eye.parentElement.classList.toggle('vm-off', s.mode !== 'walk');
    ui.eye.value = s.eye; ui.eyeV.textContent = s.eye.toFixed(2) + ' m';
    ui.tilt.value = Math.round(s.pitch / D2R); ui.tiltV.textContent = Math.round(s.pitch / D2R) + '°';
    ui.straight.checked = s.straight;
    drawFrame();
  }
  function drawFrame() {
    if (!s.camOpen) { frameEl.style.display = 'none'; return; }
    const r = frameRect(), crop = s.frame !== 'screen', px = outSize(r);
    ui.px.textContent = `${px.w} × ${px.h} px`;
    Object.assign(frameEl.style, { display: crop || s.grid ? 'block' : 'none', left: r.x + 'px', top: r.y + 'px', width: r.w + 'px', height: r.h + 'px' });
    frameEl.classList.toggle('vm-crop', crop);
    frameEl.querySelectorAll('i').forEach(i => { i.style.display = s.grid ? 'block' : 'none'; });
  }
  function setLens(mm) {
    mm = Math.max(12, Math.min(85, Number(mm)));
    if (s.mode === 'orbit') s.orbitLens = mm; else s.lens = mm;
    applyProjection(); syncCamPanel(); updateHud();
  }
  function openCam(open) {
    if (open && s.locked) { s.camWanted = true; return; }   // the build replay is on: open it when the replay ends
    s.camOpen = open;
    cam.style.display = open ? 'block' : 'none';
    $('vm-cam-btn').classList.toggle('on', open);
    updateHud(); syncCamPanel();
  }

  // ---------------------------------------------------------------- photos
  const pad = n => String(n).padStart(2, '0');
  function photoName() {
    const t = new Date(), mode = s.mode === 'orbit' ? 'Orbit' : s.mode === 'walk' ? 'Walk' : 'Ghost';
    const where = s.mode === 'orbit' ? 'overview' : currentFloor().name;
    const lens = Math.round(s.mode === 'orbit' ? s.orbitLens : s.lens);
    const stamp = `${t.getFullYear()}-${pad(t.getMonth() + 1)}-${pad(t.getDate())}_${pad(t.getHours())}-${pad(t.getMinutes())}-${pad(t.getSeconds())}`;
    return `${o.project}_${mode}_${where}_${lens}mm_${stamp}.png`.replace(/[^\w.-]+/g, '-');
  }
  function download(url, name) {
    const a = document.createElement('a');
    a.href = url; a.download = name;
    document.body.appendChild(a); a.click(); a.remove();
  }
  function takePhoto() {
    const cw = canvas.clientWidth, ch = canvas.clientHeight;
    if (s.locked || !cw || !ch) return Promise.resolve(null);
    // What you see is what you get: the frame only applies while the Camera panel (and so the frame) is showing.
    const r = s.camOpen ? frameRect() : { x: 0, y: 0, w: cw, h: ch }, size = outSize(r);
    if (s.mode === 'orbit') controls.update(); else applyCamera();
    applyProjection();
    // Draw the photo in screen-sized tiles and stitch them on a 2D canvas, so even a 4K picture needs no more
    // graphics memory than the screen itself (a 4K drawing buffer with antialiasing can take ~300 MB).
    const out = document.createElement('canvas');
    out.width = size.w; out.height = size.h;
    const ctx = out.getContext('2d');
    const k = size.w / r.w, shift = shiftPx(), pr = renderer.getPixelRatio();
    renderer.setPixelRatio(1);                 // the drawing buffer becomes cw x ch: one tile
    for (let ty = 0; ty < size.h; ty += ch) {
      for (let tx = 0; tx < size.w; tx += cw) {
        const w = Math.min(cw, size.w - tx), h = Math.min(ch, size.h - ty);
        camera.setViewOffset(cw * k, ch * k, r.x * k + tx, (r.y + shift) * k + ty, w, h);
        camera.updateProjectionMatrix();
        renderer.setViewport(0, ch - h, w, h);
        renderer.render(scene, camera);
        ctx.drawImage(canvas, 0, 0, w, h, tx, ty, w, h);
      }
    }
    renderer.setPixelRatio(pr);                // back to the screen's own buffer (this also resets the viewport)
    applyProjection();
    renderer.render(scene, camera);
    flashEl.animate([{ opacity: 0.7 }, { opacity: 0 }], { duration: 350, easing: 'ease-out' });
    const name = photoName();
    return new Promise((res, rej) => out.toBlob(b => (b ? res(b) : rej(new Error('the photo could not be saved'))), 'image/png')).then(blob => {
      const u = URL.createObjectURL(blob);
      const img = document.createElement('img');
      img.src = u; img.title = `${name} (${size.w} x ${size.h}) - click to save again`;
      img.onclick = () => download(u, name);
      ui.photos.prepend(img);
      while (ui.photos.children.length > 12) { const old = ui.photos.lastChild; URL.revokeObjectURL(old.src); old.remove(); }
      drawFrame();                             // the panel may have grown
      if (!s.noDownload) download(u, name);
      return { name, width: size.w, height: size.h };
    });
  }

  // ---------------------------------------------------------------- input
  // Keys go to the viewer unless you are typing, or using the arrow keys on a focused slider or list.
  function typing(e) {
    const t = e.target;
    if (!t || !t.matches) return false;
    if (t.matches('textarea, input[type=text], input[type=number], input[type=search], input:not([type])')) return true;
    return t.matches('input[type=range], select') && (e.code || '').startsWith('Arrow');
  }
  addEventListener('keydown', e => {
    if (s.locked || typing(e) || e.ctrlKey || e.metaKey || e.altKey) return;
    // A focused list (Frame, Size) must not also jump to an option when a viewer key is pressed.
    if (e.target && e.target.tagName === 'SELECT' && e.code !== 'Tab') e.preventDefault();
    if (e.code === 'KeyP') { e.preventDefault(); if (!e.repeat) takePhoto(); return; }   // holding P: one photo
    if (e.code === 'Digit1') { setMode('orbit'); return; }
    if (e.code === 'Digit2') { setMode('walk'); return; }
    if (e.code === 'Digit3') { setMode('ghost'); return; }
    if (s.mode === 'orbit') return;
    if (e.code === 'Escape') { if (document.pointerLockElement !== canvas) setMode('orbit'); return; }
    if (e.code === 'PageUp' || e.code === 'PageDown') { changeFloor(e.code === 'PageUp' ? 1 : -1); e.preventDefault(); return; }
    s.keys.add(e.code);
    if (['Space', 'ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(e.code)) e.preventDefault();
  });
  // Space must not also press a focused button or tick a focused checkbox.
  addEventListener('keyup', e => { s.keys.delete(e.code); if (s.mode !== 'orbit' && e.code === 'Space' && !typing(e)) e.preventDefault(); });
  addEventListener('blur', () => { s.keys.clear(); s.vert = 0; resetStick(); });
  // Chrome drops the key-ups that follow the Esc which frees the mouse: forget held keys when the lock ends.
  document.addEventListener('pointerlockchange', () => { if (document.pointerLockElement !== canvas) { s.keys.clear(); s.vert = 0; } });

  function look(dx, dy, touch) {
    // Mouse: turn the way you move. Touch: drag the scene, like a panorama.
    if (touch) { s.yaw += dx * LOOK_TOUCH; s.pitch += dy * LOOK_TOUCH; } else { s.yaw -= dx * LOOK; s.pitch -= dy * LOOK; }
    clampPitch();
    if (s.camOpen) { ui.tilt.value = Math.round(s.pitch / D2R); ui.tiltV.textContent = Math.round(s.pitch / D2R) + '°'; }
  }
  function noteTouch(e) {                      // show the touch controls after a touch, hide them after a mouse
    const t = e.pointerType === 'touch';
    if ((e.pointerType === 'touch' || e.pointerType === 'mouse') && t !== s.touch) { s.touch = t; updateHud(); drawFrame(); }
  }
  addEventListener('pointerdown', noteTouch, true);
  document.addEventListener('mousemove', e => {
    if (s.mode === 'orbit' || document.pointerLockElement !== canvas) return;
    if (Math.abs(e.movementX) > 300 || Math.abs(e.movementY) > 300) return;   // Chrome sometimes reports a jump as the lock starts
    look(e.movementX, e.movementY, false);
  });
  canvas.addEventListener('pointerdown', e => {
    if (s.locked || s.mode === 'orbit' || document.pointerLockElement === canvas || s.drag) return;
    s.drag = { id: e.pointerId, x: e.clientX, y: e.clientY, x0: e.clientX, y0: e.clientY, touch: e.pointerType === 'touch' };
    s.dragMoved = false;
  });
  addEventListener('pointermove', e => {
    if (!s.drag || e.pointerId !== s.drag.id) return;
    const dx = e.clientX - s.drag.x, dy = e.clientY - s.drag.y;
    // A drag is judged by how far it went in all, so a slow, careful drag still counts as one (and does not lock the mouse).
    if (Math.abs(e.clientX - s.drag.x0) + Math.abs(e.clientY - s.drag.y0) > 4) s.dragMoved = true;
    s.drag.x = e.clientX; s.drag.y = e.clientY;
    look(dx, dy, s.drag.touch);
  });
  const endDrag = e => { if (s.drag && e.pointerId === s.drag.id) s.drag = null; };
  addEventListener('pointerup', endDrag);
  addEventListener('pointercancel', endDrag);
  canvas.addEventListener('click', e => {
    if (e.pointerType === 'touch') return;
    if (s.mode !== 'orbit' && !s.dragMoved && document.pointerLockElement !== canvas && canvas.requestPointerLock) {
      try { const p = canvas.requestPointerLock(); if (p && p.catch) p.catch(() => {}); } catch (err) { /* drag to look still works */ }
    }
  });
  canvas.addEventListener('contextmenu', e => { if (s.mode !== 'orbit') e.preventDefault(); });
  // Wheel: Ghost speed or Walk lens, in proportion to how far you scroll (a touchpad sends many small steps).
  // Up or pinch-out = faster / longer lens (zoom in), like the Orbit zoom.
  canvas.addEventListener('wheel', e => {
    if (s.locked || s.mode === 'orbit') return;
    e.preventDefault();
    const px = (e.deltaY || (e.shiftKey ? e.deltaX : 0)) * (e.deltaMode === 1 ? 40 : e.deltaMode === 2 ? 800 : 1);
    if (!px) return;
    if (s.mode === 'ghost') { s.ghostSpeed = Math.max(0.5, Math.min(60, s.ghostSpeed * Math.pow(1.2, -px / 100))); updateHud(); }
    else setLens(s.lens - px / 50);           // 2 mm per mouse notch
  }, { passive: false });
  canvas.addEventListener('dblclick', e => {
    if (s.locked || s.mode !== 'orbit') return;
    const r = canvas.getBoundingClientRect();
    ray.setFromCamera(new THREE.Vector2((e.clientX - r.left) / r.width * 2 - 1, -(e.clientY - r.top) / r.height * 2 + 1), camera);
    ray.far = Infinity;
    const vis = floors.filter(f => f.group.visible);
    const targets = vis.flatMap(f => f.walkables.filter(m => m.visible).concat(visibleColliders(f)));
    const hit = targets.length ? ray.intersectObjects(targets, false)[0] : null;
    let floor = hit ? vis.find(f => f.walkables.includes(hit.object) || f.colliders.includes(hit.object)) : null;
    let point = hit ? hit.point : null;
    if (!point) {
      floor = vis.sort((a, b) => a.level - b.level)[0] || floors[0];
      const p = new THREE.Vector3();
      if (!ray.ray.intersectPlane(new THREE.Plane(new THREE.Vector3(0, 1, 0), -floor.level), p)) return;
      point = p;
    }
    setMode('walk', { floor, point });
  });

  // Touch stick: push to move (Walk) or fly (Ghost); how far you push sets the speed.
  function moveStick(e) {
    const r = stick.getBoundingClientRect(), R = r.width / 2;
    let x = (e.clientX - r.left - R) / R, y = (e.clientY - r.top - R) / R;
    const m = Math.hypot(x, y);
    if (m > 1) { x /= m; y /= m; }
    s.stick.x = x; s.stick.y = y;
    ui.knob.style.transform = `translate(${x * R * 0.6}px, ${y * R * 0.6}px)`;
  }
  function resetStick() { s.stick = { id: null, x: 0, y: 0 }; ui.knob.style.transform = ''; }
  stick.addEventListener('pointerdown', e => {
    s.stick.id = e.pointerId;
    try { stick.setPointerCapture(e.pointerId); } catch (err) { /* moves still arrive while over the stick */ }
    moveStick(e); e.preventDefault();
  });
  stick.addEventListener('pointermove', e => { if (e.pointerId === s.stick.id) moveStick(e); });
  const endStick = e => { if (e.pointerId === s.stick.id) resetStick(); };
  stick.addEventListener('pointerup', endStick);
  stick.addEventListener('pointercancel', endStick);
  // Up / Down buttons: tap for the next floor in Walk, hold to rise or sink in Ghost.
  [[ui.up, 1], [ui.down, -1]].forEach(([b, v]) => {
    b.addEventListener('pointerdown', e => {
      e.preventDefault();
      if (s.mode === 'walk') changeFloor(v);
      else { s.vert = v; try { b.setPointerCapture(e.pointerId); } catch (err) { /* fine */ } }
    });
    const stop = () => { s.vert = 0; };
    b.addEventListener('pointerup', stop); b.addEventListener('pointercancel', stop); b.addEventListener('lostpointercapture', stop);
  });

  document.querySelectorAll('#vm-modes [data-m]').forEach(b => { b.onclick = () => setMode(b.dataset.m); });
  $('vm-exit').onclick = () => setMode('orbit');
  $('vm-cam-btn').onclick = () => openCam(!s.camOpen);
  $('vm-hud-cam').onclick = () => openCam(!s.camOpen);
  $('vm-cam-close').onclick = () => openCam(false);
  ui.lens.oninput = () => setLens(ui.lens.value);
  cam.querySelectorAll('[data-mm]').forEach(b => { b.onclick = () => setLens(b.dataset.mm); });
  ui.eye.oninput = () => { s.eye = Number(ui.eye.value); if (s.mode === 'walk') s.pos.y = s.floor.level + s.eye; applyCamera(); syncCamPanel(); };
  ui.tilt.oninput = () => { s.pitch = Number(ui.tilt.value) * D2R; clampPitch(); applyCamera(); syncCamPanel(); };
  ui.straight.onchange = () => { s.straight = ui.straight.checked; clampPitch(); applyCamera(); syncCamPanel(); };
  // Lists hand the keyboard back to the viewer once a choice is made.
  ui.frame.onchange = () => { s.frame = ui.frame.value; drawFrame(); ui.frame.blur(); };
  ui.size.onchange = () => { s.size = Number(ui.size.value); drawFrame(); ui.size.blur(); };
  ui.grid.onchange = () => { s.grid = ui.grid.checked; drawFrame(); };
  $('vm-shot').onclick = () => takePhoto();
  ui.snap.onclick = () => takePhoto();
  // Resizing, browser zoom and moving to another screen: keep the drawing buffer sharp (pixel ratio capped at 2, as the hosts set it).
  function onResize() {
    renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
    renderer.setSize(innerWidth, innerHeight);
    applyProjection(); updateHud(); syncCamPanel();
  }
  addEventListener('resize', onResize);
  (function watchPixelRatio() {
    const mq = matchMedia(`(resolution: ${devicePixelRatio}dppx)`);
    if (mq.addEventListener) mq.addEventListener('change', () => { onResize(); watchPixelRatio(); }, { once: true });
  })();

  // ---------------------------------------------------------------- frame loop
  function tick() {
    const now = performance.now(), dt = Math.min(0.05, (now - s.last) / 1000);
    s.last = now;
    if (s.mode === 'orbit') { controls.update(); return; }
    const k = s.keys, st = s.stick;
    let fwdIn = (k.has('KeyW') || k.has('ArrowUp') ? 1 : 0) - (k.has('KeyS') || k.has('ArrowDown') ? 1 : 0);
    let sideIn = (k.has('KeyD') || k.has('ArrowRight') ? 1 : 0) - (k.has('KeyA') || k.has('ArrowLeft') ? 1 : 0);
    const sm = Math.hypot(st.x, st.y), dead = 0.15;
    if (sm > dead) { const g = (sm - dead) / (1 - dead) / sm; fwdIn -= st.y * g; sideIn += st.x * g; }
    const fast = k.has('ShiftLeft') || k.has('ShiftRight');
    const right = new THREE.Vector3(Math.cos(s.yaw), 0, -Math.sin(s.yaw));
    if (s.mode === 'walk') {
      const d = new THREE.Vector3(-Math.sin(s.yaw), 0, -Math.cos(s.yaw)).multiplyScalar(fwdIn).addScaledVector(right, sideIn);
      const mag = Math.min(1, d.length());
      if (mag > 0) walkMove(d.setLength(mag * (fast ? RUN_SPEED : WALK_SPEED) * dt));
      s.pos.y = s.floor.level + s.eye;
    } else {
      const upIn = (k.has('Space') || k.has('KeyE') ? 1 : 0) - (k.has('KeyC') || k.has('KeyQ') ? 1 : 0) + s.vert;
      const cp = Math.cos(s.pitch);
      const d = new THREE.Vector3(-Math.sin(s.yaw) * cp, Math.sin(s.pitch), -Math.cos(s.yaw) * cp).multiplyScalar(fwdIn)
        .addScaledVector(right, sideIn).add(new THREE.Vector3(0, Math.max(-1, Math.min(1, upIn)), 0));
      const mag = Math.min(1, d.length());
      if (mag > 0) s.pos.addScaledVector(d.setLength(1), mag * s.ghostSpeed * (fast ? 3 : 1) * dt);
    }
    applyCamera();
  }

  // ---------------------------------------------------------------- start-up options from the address (?mode=walk&floor=...)
  function applyUrl() {
    const q = new URLSearchParams(location.search);
    const num = (k, d) => { const v = parseFloat(q.get(k)); return Number.isFinite(v) ? v : d; };   // ignore typos like 90deg
    if (q.has('lens')) s.lens = Math.max(12, Math.min(85, num('lens', 24)));
    if (q.has('eye')) s.eye = Math.max(0.8, Math.min(2.2, num('eye', EYE)));
    if (q.has('frame') && [...ui.frame.options].some(op => op.value === q.get('frame'))) { s.frame = q.get('frame'); ui.frame.value = s.frame; }
    if (q.get('size') === '4k') { s.size = 3840; ui.size.value = '3840'; }
    if (q.get('straight') === '1') s.straight = true;
    if (q.get('nodownload') === '1') s.noDownload = true;
    if (q.get('touch') === '1') s.touch = true;
    const m = q.get('mode');
    if (m === 'walk' || m === 'ghost') {
      const floor = byKey[q.get('floor')] || undefined;
      const point = q.has('x') ? new THREE.Vector3(num('x', 0), 0, num('z', 0)) : undefined;
      setMode(m, { floor, point });
      if (m === 'ghost' && q.has('x')) s.pos.set(num('x', s.pos.x), num('y', s.pos.y), num('z', s.pos.z));
      if (q.has('yaw')) s.yaw = num('yaw', s.yaw / D2R) * D2R;
      if (q.has('pitch')) { s.pitch = num('pitch', s.pitch / D2R) * D2R; clampPitch(); }
      applyCamera();
    }
    if (q.get('cam') === '1') openCam(true);
    syncCamPanel(); updateHud();
    if (q.get('shot') === '1') setTimeout(() => takePhoto(), 300);
  }

  applyProjection(); updateHud(); syncCamPanel();
  // probe: small read-outs for automated checks and debugging.
  const probe = {
    open: deg => openAhead(deg === undefined ? s.yaw : deg * D2R, 30),
    clearance: () => clearance(s.pos, s.floor),
    onFloor: () => onFloor(s.pos, s.floor),
    crosses: (x0, z0, x1, z1) => {            // is there a wall between two points (chest height, current floor)?
      const f = s.floor, cols = visibleColliders(f), d = new THREE.Vector3(x1 - x0, 0, z1 - z0), len = d.length();
      if (!cols.length || len < 1e-6) return false;
      ray.set(new THREE.Vector3(x0, f.level + 1.2, z0), d.divideScalar(len)); ray.far = len;
      return ray.intersectObjects(cols, false).length > 0;
    },
    walk: (deg, metres) => {                  // walk straight (as W would, 5 cm steps) and return how far you got
      const yaw = deg * D2R, d = new THREE.Vector3(-Math.sin(yaw), 0, -Math.cos(yaw)).multiplyScalar(0.05), start = s.pos.clone();
      for (let t = 0; t < metres; t += 0.05) walkMove(d.clone());
      applyCamera();
      return s.pos.distanceTo(start);
    },
    visible: () => floors.filter(f => f.group.visible).map(f => f.key),
    camera: () => ({ x: camera.position.x, y: camera.position.y, z: camera.position.z, fov: camera.fov, rx: camera.rotation.x,
      offsetY: camera.view && camera.view.enabled ? camera.view.offsetY : null, dir: camera.getWorldDirection(new THREE.Vector3()).toArray() }),
  };
  // lock: while the build replay runs, the viewer takes no keys, clicks or wheel, and stays in Orbit.
  function lock(on) {
    s.locked = !!on;
    if (on) { if (s.mode !== 'orbit') setMode('orbit'); if (s.camOpen) openCam(false); }
    else if (s.camWanted) { s.camWanted = false; openCam(true); }   // e.g. ?cam=1 asked for it while the replay was on
  }
  const api = { tick, setMode, goToFloor, takePhoto, applyUrl, lock, get mode() { return s.mode; }, state: s, probe };
  window.__viewer = api;
  return api;
}
