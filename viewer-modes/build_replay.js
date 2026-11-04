// ---------------------------------------------------------------------------
// Build replay (the "loading phase"): watch the model being built from the plan, step by step.
// Inlined into each viewer's module script after viewer_modes.js (THREE is in scope there).
//
//   Build settings  the uploaded plan in top view; floor levels and wall heights; the layers found; replay speed
//   Generate        seven steps with the real numbers: read the drawing, sort the layers, line up the floors,
//                   pair the wall faces, merge into wall runs, raise the walls, finish; then the normal viewer
// The build itself takes seconds; the replay shows the steps the builder recorded, slowed down to watch.
//
// Host passes:
//   { scene, camera, renderer, controls, modes, panel, hint, project,
//     intro: { title, facts: [string] },        // what the settings card says about the upload
//     layers: [[label, detail]],                // the layer mapping that was found (read-only here)
//     floors: [{ key, name, level, height,      // level and wall height from the data (m)
//                sheet: [dx, dy],               // where this plan sits on the drawing, from its aligned place (plan m)
//                group,                         // the host's floor group; replay objects go inside it
//                lines: { <cat>: [x1, y1, x2, y2, ...] },        // plan metres; cat names match colors
//                pieces: { <kind>: [x0, y0, x1, y1, x2, y2, x3, y3, ...] },
//                rings: { <kind>: [{ o, h }] },  // the merged outlines
//                rise: [{ mesh, edges, scales }],  // solids that grow; edges = their outline; scales = follow wall height
//                late: [Object3D] }],           // shown at the end: floor plates, stairs, slabs
//     hide: [Object3D],                         // hidden while building, shown at the end (ground plane)
//     colors: { <cat>: 0xrrggbb, ink, faint, piece, pieceEdge, run, runEdge },
//     steps: { read|sort|align|pair|merge|raise|finish: { title, caption: settings => string } },
//     applySettings: settings => void,          // the host updates what it owns (walk levels) after a change
//     restore: () => void }                     // re-apply the host's own visibility rules at the end
// Returns { tick, generate, skip, openSettings, get phase, state }.
// ---------------------------------------------------------------------------
function installBuildReplay(o) {
  const { scene, camera, renderer, controls, modes } = o;
  const floors = o.floors;
  const D2R = Math.PI / 180;
  const KEYS = ['read', 'sort', 'align', 'pair', 'merge', 'raise', 'finish'];
  const WEIGHT = { read: 1.2, sort: 1.1, align: 1.5, pair: 1.3, merge: 1.0, raise: 2.3, finish: 1.4 };
  const SPEEDS = { quick: 9, normal: 20, slow: 40 };          // seconds for the whole replay
  const totalW = KEYS.reduce((a, k) => a + WEIGHT[k], 0);
  let acc = 0;
  const steps = KEYS.map(k => {
    const s = { key: k, title: o.steps[k].title, caption: o.steps[k].caption, t0: acc / totalW };
    acc += WEIGHT[k]; s.t1 = acc / totalW;
    return s;
  });
  const C = Object.assign({ ink: 0x3b4148, faint: 0xa4acb4, piece: 0xcfc2b0, pieceEdge: 0x8a7a66, run: 0xe3ddd3, runEdge: 0x6f675d }, o.colors);
  const st = {
    phase: 'off', T: 0, speed: 'normal', captions: true, last: 0, endAt: 0, step: null,
    settings: Object.fromEntries(floors.map(f => [f.key, { level: f.level, height: f.height }])),
  };
  const final = { pos: camera.position.clone(), target: controls.target.clone() };
  const scanPlane = new THREE.Plane(new THREE.Vector3(-1, 0, 0), 0);    // keeps x <= constant
  const sweepPlane = new THREE.Plane(new THREE.Vector3(-1, 0, 0), 0);
  const ease = t => t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
  const clamp01 = t => Math.max(0, Math.min(1, t));
  const span = (t, a, b) => clamp01((t - a) / (b - a));                   // local progress of t inside [a, b]

  // ---------------------------------------------------------------- the walls grow: a small shader patch
  // Each solid has an aDelay attribute (0..1, set by the host per wall run); uRise 0 -> 1 raises them in a sweep.
  // A run that has not started yet is not drawn at all (so it cannot flicker against the outlines below it).
  // The wall-height setting scales the mesh itself (applySettings), so hover, double-click and walking see it too.
  floors.forEach(f => f.rise.forEach(r => {
    const u = { uRise: { value: 1 }, uBase: { value: f.level } };
    const m = r.mesh.material;
    m.onBeforeCompile = sh => {
      Object.assign(sh.uniforms, u);
      sh.vertexShader = sh.vertexShader
        .replace('#include <common>', '#include <common>\nattribute float aDelay;\nuniform float uRise;\nuniform float uBase;\nvarying float vBrK;')
        .replace('#include <begin_vertex>', '#include <begin_vertex>\n' +
          '  float brK = clamp((uRise - aDelay * 0.6) / 0.4, 0.0, 1.0);\n' +
          '  brK = brK * brK * (3.0 - 2.0 * brK);\n' +
          '  vBrK = brK;\n' +
          '  transformed.y = uBase + (transformed.y - uBase) * max(brK, 0.004);');
      sh.fragmentShader = sh.fragmentShader
        .replace('#include <common>', '#include <common>\nvarying float vBrK;')
        .replace('#include <clipping_planes_fragment>', '#include <clipping_planes_fragment>\n  if (vBrK <= 0.0005) discard;');
    };
    m.needsUpdate = true;
    r.mesh.frustumCulled = false;                      // the drawn shape can differ from the stored one
    r.u = u;
    if (r.edges) r.edgeOpacity = r.edges.material.opacity;
  }));
  floors.forEach(f => f.late.forEach(obj => obj.traverse(n => {
    if (n.material && n.userData.brOpacity === undefined) { n.userData.brOpacity = n.material.opacity; n.userData.brTransparent = n.material.transparent; }
  })));

  // ---------------------------------------------------------------- UI
  const css = document.createElement('style');
  css.textContent = `
#br-card{position:fixed;top:12px;left:12px;width:min(330px,calc(100vw - 48px));max-height:calc(100vh - 110px);overflow:auto;background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:12px 14px;box-shadow:0 2px 10px #0001;z-index:8;display:none}
#br-card h1{font-size:15px;margin:0 0 4px}
#br-card .br-file{font-weight:600;margin:0 0 2px;color:var(--ink);font-size:13px}
#br-card ul{margin:0 0 8px;padding-left:18px;color:var(--muted);font-size:12.5px}
#br-card table{border-collapse:collapse;width:100%;font-size:12.5px}
#br-card td,#br-card th{padding:3px 4px;text-align:left;vertical-align:middle}
#br-card th{color:var(--muted);font-weight:500;font-size:11.5px}
#br-card input[type=number]{width:62px;font:inherit;font-size:12.5px;padding:2px 4px;border:1px solid var(--line);border-radius:5px;background:#fff;color:var(--ink);color-scheme:light}
#br-card details{margin:8px 0;font-size:12.5px}
#br-card summary{cursor:pointer;color:var(--ink)}
#br-card details td:first-child{white-space:nowrap;padding-right:8px}
#br-card details td{color:var(--muted)}
#br-card .br-note{color:var(--muted);font-size:11.5px;margin:4px 0 0}
#br-go{width:100%;margin-top:10px;padding:9px;font-weight:600;background:var(--accent);border-color:var(--accent);color:#fff;position:sticky;bottom:0;box-shadow:0 -6px 8px var(--panel)}
#br-skip0{width:100%;margin-top:6px;border:none;background:none;color:var(--muted);text-decoration:underline;font-size:12.5px}
#br-steps{list-style:none;margin:6px 0 8px;padding:0;font-size:13px}
#br-steps li{display:flex;align-items:center;gap:8px;padding:3px 0;color:var(--muted)}
#br-steps li i{flex:none;width:16px;height:16px;border-radius:50%;border:1.5px solid var(--line);display:inline-flex;align-items:center;justify-content:center;font-style:normal;font-size:10px;box-sizing:border-box}
#br-steps li.br-now{color:var(--ink);font-weight:600}
#br-steps li.br-now i{border-color:var(--accent);background:var(--accent)}
#br-steps li.br-done{color:var(--ink)}
#br-steps li.br-done i{border-color:var(--accent);color:var(--accent)}
#br-bar{height:4px;background:var(--line);border-radius:2px;overflow:hidden;margin:4px 0 10px}
#br-bar i{display:block;height:100%;width:0;background:var(--accent)}
#br-sub{position:fixed;left:50%;bottom:22px;transform:translateX(-50%);width:min(680px,calc(100vw - 24px));box-sizing:border-box;background:#1d2329e6;color:#fff;border-radius:10px;padding:10px 14px;font-size:13.5px;line-height:1.45;z-index:8;display:none;transition:opacity .25s}
#br-sub b{color:#fff}
.br-on .vm-hint,.br-on .vm-panel{display:none}
@media (max-width:700px){
#br-card{width:auto;right:12px;max-height:46vh}
#br-steps{display:grid;grid-template-columns:1fr 1fr;column-gap:8px}
#br-steps li{font-size:12px}
#br-sub{bottom:12px;font-size:12.5px}
}
`;
  document.head.appendChild(css);
  const card = document.createElement('div'); card.id = 'br-card';
  const floorRows = floors.map(f => `<tr><td>${f.name}</td><td><input type="number" step="0.05" data-k="${f.key}" data-p="level"></td><td><input type="number" step="0.05" min="1" max="12" data-k="${f.key}" data-p="height"></td></tr>`).join('');
  card.innerHTML = `
<div id="br-settings">
  <h1>Build the 3D model</h1>
  <p class="br-file">${o.intro.title}</p>
  <ul>${o.intro.facts.map(x => `<li>${x}</li>`).join('')}</ul>
  <table><tr><th>Floor</th><th>Level (m)</th><th>Wall height (m)</th></tr>${floorRows}</table>
  <p class="br-note">Read from the drawing. Change them if the drawing is wrong or not given.</p>
  <details><summary>${o.layersTitle || 'Layers found'}</summary><table>${o.layers.map(([a, b]) => `<tr><td>${a}</td><td>${b}</td></tr>`).join('')}</table></details>
  <div class="vm-label">Replay speed</div>
  <div class="vm-row" id="br-speed"><button data-s="quick">Quick</button><button data-s="normal">Normal</button><button data-s="slow">Slow</button></div>
  <label style="margin-top:8px"><input type="checkbox" id="br-cap" checked> Explain each step</label>
  <button id="br-go">Generate 3D model</button>
  <button id="br-skip0">Skip: show the finished model</button>
</div>
<div id="br-play" style="display:none">
  <h1>Building the model</h1>
  <ol id="br-steps">${steps.map((s, i) => `<li data-k="${s.key}"><i>${i + 1}</i>${s.title}</li>`).join('')}</ol>
  <div id="br-bar"><i></i></div>
  <div class="vm-row"><button id="br-skip">Skip to the model</button></div>
</div>`;
  const sub = document.createElement('div'); sub.id = 'br-sub';
  document.body.append(card, sub);
  // A row in the host panel to come back to this later.
  const row = document.createElement('div');
  row.innerHTML = `<div class="vm-label">Build</div><div class="vm-row"><button id="br-again">Replay the build</button><button id="br-open">Build settings</button></div>`;
  o.panel.appendChild(row);

  const $ = id => document.getElementById(id);
  const inputs = [...card.querySelectorAll('input[type=number]')];
  function syncInputs() { inputs.forEach(i => { i.value = st.settings[i.dataset.k][i.dataset.p].toFixed(2); }); }
  function markSpeed() { card.querySelectorAll('#br-speed button').forEach(b => b.classList.toggle('on', b.dataset.s === st.speed)); }
  card.querySelectorAll('#br-speed button').forEach(b => { b.onclick = () => { st.speed = b.dataset.s; markSpeed(); }; });
  inputs.forEach(i => {
    i.onchange = () => {
      // An empty or unreadable box keeps the old value (a browser reports both as '', and Number('') would be 0).
      const raw = i.value.trim(), v = raw === '' ? NaN : Number(raw), cur = st.settings[i.dataset.k];
      if (Number.isFinite(v)) cur[i.dataset.p] = i.dataset.p === 'height' ? Math.max(1, Math.min(12, v)) : Math.max(-10, Math.min(200, v));
      syncInputs(); applySettings();
    };
  });
  $('br-cap').onchange = e => { st.captions = e.target.checked; };
  $('br-go').onclick = () => generate();
  $('br-skip0').onclick = () => skip();
  $('br-skip').onclick = () => skip();
  $('br-again').onclick = () => { openSettings(); generate(); };
  $('br-open').onclick = () => openSettings();

  // ---------------------------------------------------------------- replay objects (made fresh for every run)
  const lineMat = (color, opacity, clip) => new THREE.LineBasicMaterial({ color, transparent: true, opacity, depthWrite: false, clippingPlanes: clip || null });
  const fillMat = (color, opacity, clip) => new THREE.MeshBasicMaterial({ color, transparent: true, opacity, depthWrite: false, side: THREE.DoubleSide, clippingPlanes: clip || null });
  function segGeometry(a, y) {                 // flat [x1, y1, x2, y2, ...] in plan metres -> line segments at height y
    const n = Math.floor(a.length / 4), pos = new Float32Array(n * 6);
    for (let i = 0; i < n; i++) {
      pos[6 * i] = a[4 * i]; pos[6 * i + 1] = y; pos[6 * i + 2] = -a[4 * i + 1];
      pos[6 * i + 3] = a[4 * i + 2]; pos[6 * i + 4] = y; pos[6 * i + 5] = -a[4 * i + 3];
    }
    const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    return g;
  }
  function quadGeometries(q, y) {              // flat quads -> filled triangles + their outlines (the seams)
    const n = Math.floor(q.length / 8), tri = new Float32Array(n * 18), edge = new Float32Array(n * 24);
    for (let i = 0; i < n; i++) {
      const P = k => [q[8 * i + 2 * k], y, -q[8 * i + 2 * k + 1]];
      tri.set([...P(0), ...P(1), ...P(2), ...P(0), ...P(2), ...P(3)], 18 * i);
      edge.set([...P(0), ...P(1), ...P(1), ...P(2), ...P(2), ...P(3), ...P(3), ...P(0)], 24 * i);
    }
    const a = new THREE.BufferGeometry(); a.setAttribute('position', new THREE.BufferAttribute(tri, 3));
    const b = new THREE.BufferGeometry(); b.setAttribute('position', new THREE.BufferAttribute(edge, 3));
    return [a, b];
  }
  function ringGeometries(rings, y) {          // merged outlines -> a flat fill + the outline
    const shapes = [], edge = [];
    for (const r of rings) {
      const s = new THREE.Shape(r.o.map(([x, z]) => new THREE.Vector2(x, z)));
      for (const h of r.h) s.holes.push(new THREE.Path(h.map(([x, z]) => new THREE.Vector2(x, z))));
      shapes.push(s);
      for (const loop of [r.o, ...r.h]) loop.forEach((p, i) => { const q = loop[(i + 1) % loop.length]; edge.push(p[0], y, -p[1], q[0], y, -q[1]); });
    }
    const fill = new THREE.ShapeGeometry(shapes, 1); fill.rotateX(-Math.PI / 2); fill.translate(0, y, 0);
    const line = new THREE.BufferGeometry(); line.setAttribute('position', new THREE.Float32BufferAttribute(edge, 3));
    return [fill, line];
  }
  function bounds(f) {                         // plan bounds of a floor's kept lines (not the noise)
    let x0 = Infinity, x1 = -Infinity, y0 = Infinity, y1 = -Infinity;
    for (const [cat, a] of Object.entries(f.lines)) {
      if (cat === 'noise') continue;
      for (let i = 0; i < a.length; i += 2) { x0 = Math.min(x0, a[i]); x1 = Math.max(x1, a[i]); y0 = Math.min(y0, a[i + 1]); y1 = Math.max(y1, a[i + 1]); }
    }
    return { x0, x1, y0, y1 };
  }
  floors.forEach(f => { f.b = bounds(f); });

  let made = null;                              // the objects of the current run
  function make() {
    unmake();
    const accent = (getComputedStyle(document.documentElement).getPropertyValue('--accent') || '#c9773e').trim();
    const scan = new THREE.Mesh(new THREE.PlaneGeometry(0.35, 1).rotateX(-Math.PI / 2),
      new THREE.MeshBasicMaterial({ color: new THREE.Color(accent), transparent: true, opacity: 0.85, depthWrite: false }));
    scan.renderOrder = 7; scan.visible = false;
    scene.add(scan);
    made = { floors: [], scan };
    for (const f of floors) {
      const g = new THREE.Group(); g.name = 'build replay';
      const y = f.level, F = { f, g, lines: {}, pieces: [], runs: [] };
      for (const [cat, a] of Object.entries(f.lines)) {
        if (!a.length) continue;
        const geo = segGeometry(a, y + 0.03);
        const faint = new THREE.LineSegments(geo, lineMat(C.faint, cat === 'noise' ? 0.35 : 0.5));
        const ink = new THREE.LineSegments(geo, lineMat(C.ink, 0.9, [scanPlane]));
        faint.renderOrder = 1; ink.renderOrder = 2;
        g.add(faint, ink);
        F.lines[cat] = { faint, ink, color: new THREE.Color(cat === 'noise' ? C.faint : (C[cat] || C.ink)) };
      }
      for (const [kind, q] of Object.entries(f.pieces)) {
        if (!q.length) continue;
        const [tri, edge] = quadGeometries(q, y + 0.01);
        const glass = kind === 'glass';
        const m = new THREE.Mesh(tri, fillMat(glass ? C.glass : C.piece, 0, [sweepPlane]));
        const e = new THREE.LineSegments(edge, lineMat(glass ? C.glass : C.pieceEdge, 0, [sweepPlane]));
        m.renderOrder = 3; e.renderOrder = 4;
        g.add(m, e);
        F.pieces.push({ m, e, glass });
      }
      for (const [kind, rings] of Object.entries(f.rings)) {
        if (!rings.length) continue;
        const [fill, line] = ringGeometries(rings, y + 0.015);
        const glass = kind === 'glass';
        const m = new THREE.Mesh(fill, fillMat(glass ? C.glass : C.run, 0));
        const e = new THREE.LineSegments(line, lineMat(glass ? C.glass : C.runEdge, 0));
        m.renderOrder = 5; e.renderOrder = 6;
        g.add(m, e);
        F.runs.push({ m, e, glass });
      }
      f.group.add(g);
      made.floors.push(F);
    }
  }
  function unmake() {
    if (!made) return;
    scene.remove(made.scan); made.scan.geometry.dispose(); made.scan.material.dispose();
    for (const F of made.floors) {
      F.g.traverse(n => { if (n.geometry) n.geometry.dispose(); if (n.material) n.material.dispose(); });
      F.f.group.remove(F.g);
    }
    made = null;
  }

  // ---------------------------------------------------------------- settings -> the model
  function applySettings() {
    for (const f of floors) {
      const s = st.settings[f.key];
      f.group.position.set(0, s.level - f.level, 0);       // home position: the level chosen in the settings
      const k = s.height / f.height;
      f.rise.forEach(r => {               // scale about the floor level, wall and outline alike
        const sc = r.scales ? k : 1;
        for (const obj of [r.mesh, r.edges]) if (obj) { obj.scale.y = sc; obj.position.y = f.level * (1 - sc); }
      });
    }
    if (o.applySettings) o.applySettings(JSON.parse(JSON.stringify(st.settings)));
  }

  // ---------------------------------------------------------------- camera framing (fits the free part of the screen)
  function freeRect() {
    const W = innerWidth, H = innerHeight, subH = st.captions && st.phase === 'play' ? 86 : 16;
    const r = card.style.display === 'none' ? null : card.getBoundingClientRect();
    if (!r || !r.width) return { x: 0, y: 0, w: W, h: H - subH };
    if (r.right < W * 0.55) return { x: r.right + 8, y: 8, w: Math.max(80, W - r.right - 16), h: H - subH - 8 };
    return { x: 0, y: r.bottom + 8, w: W, h: Math.max(80, H - r.bottom - 8 - subH) };
  }
  // Camera looking along dir at a box so the box's picture fills the free rectangle; returns { pos, target }.
  // Projects the 8 corners (so perspective is exact), searches the distance, and centres the picture.
  function pose(box, dir, pad = 1.08) {
    const fr = freeRect(), W = innerWidth, H = innerHeight;
    const k = 2 * Math.tan(camera.fov * D2R / 2) / H;      // world size of one pixel, per metre of distance
    const c = box.getCenter(new THREE.Vector3());
    const right = new THREE.Vector3().crossVectors(dir, new THREE.Vector3(0, 1, 0)).normalize();
    const up = new THREE.Vector3().crossVectors(right, dir).normalize();
    const corners = [...Array(8)].map((_, i) => new THREE.Vector3(i & 1 ? box.max.x : box.min.x, i & 2 ? box.max.y : box.min.y, i & 4 ? box.max.z : box.min.z));
    const cx = fr.x + fr.w / 2, cy = fr.y + fr.h / 2;
    function place(dist) {
      const target = c.clone();
      let w = 0, h = 0;
      for (let it = 0; it < 3; it++) {
        const pos = target.clone().addScaledVector(dir, -dist);
        let x0 = Infinity, x1 = -Infinity, y0 = Infinity, y1 = -Infinity;
        for (const p of corners) {
          const v = p.clone().sub(pos), z = Math.max(0.05, v.dot(dir));
          const sx = W / 2 + v.dot(right) / (z * k), sy = H / 2 - v.dot(up) / (z * k);
          x0 = Math.min(x0, sx); x1 = Math.max(x1, sx); y0 = Math.min(y0, sy); y1 = Math.max(y1, sy);
        }
        w = x1 - x0; h = y1 - y0;
        const px = dist * k;
        target.addScaledVector(right, ((x0 + x1) / 2 - cx) * px).addScaledVector(up, -((y0 + y1) / 2 - cy) * px);
      }
      return { pos: target.clone().addScaledVector(dir, -dist), target, w, h };
    }
    let lo = 0.5, hi = 20000;
    for (let i = 0; i < 36; i++) {
      const mid = Math.sqrt(lo * hi), p = place(mid);
      if (p.w * pad <= fr.w && p.h * pad <= fr.h) hi = mid; else lo = mid;
    }
    return place(hi);
  }
  const DOWN = new THREE.Vector3(0, -1, -0.002).normalize();   // straight down, north at the top of the screen
  const NORTH = Math.atan2(DOWN.x, DOWN.z);                   // the heading of that top view
  const finalDir = () => final.target.clone().sub(final.pos).normalize();
  function dirAt(az, elevDeg) {                  // a view direction from a heading and an elevation (degrees down from level)
    const el = elevDeg * D2R;
    return new THREE.Vector3(Math.sin(az) * Math.cos(el), -Math.sin(el), Math.cos(az) * Math.cos(el));
  }
  function sheetBox(alignT) {                    // where the drawings are: side by side on the sheet (alignT 0) or lined up (1)
    const b = new THREE.Box3(), y = lowest();
    for (const f of floors) {
      const dx = f.sheet[0] * (1 - alignT), dy = f.sheet[1] * (1 - alignT);
      b.expandByPoint(new THREE.Vector3(f.b.x0 + dx, y, -(f.b.y1 + dy)));
      b.expandByPoint(new THREE.Vector3(f.b.x1 + dx, y, -(f.b.y0 + dy)));
    }
    return b;
  }
  function stackBox(wallsT) {                    // the lined-up floors, flat (0) up to with their full walls (1)
    const b = new THREE.Box3();
    for (const f of floors) {
      const s = st.settings[f.key];
      b.expandByPoint(new THREE.Vector3(f.b.x0, s.level, -f.b.y1));
      b.expandByPoint(new THREE.Vector3(f.b.x1, s.level + Math.max(0.1, s.height * wallsT), -f.b.y0));
    }
    return b;
  }
  const lowest = () => Math.min(...floors.map(f => st.settings[f.key].level));
  function lerpPose(a, b, t) {
    return { pos: a.pos.clone().lerp(b.pos, t), target: a.target.clone().lerp(b.target, t) };
  }
  function setPose(p) { camera.position.copy(p.pos); controls.target.copy(p.target); camera.lookAt(p.target); }

  // ---------------------------------------------------------------- the seven steps
  function setFloorPlace(F, slideT, liftT) {     // 0 = on the sheet beside the others, 1 = at its own place and level
    const f = F.f, s = st.settings[f.key], homeY = s.level - f.level;
    const sx = f.sheet[0] * (1 - slideT), sz = -f.sheet[1] * (1 - slideT);
    const sy = homeY + (lowest() - s.level) * (1 - liftT);
    f.group.position.set(sx, sy, sz);
  }
  function showSolids(F, rise, edgeT) {
    F.f.rise.forEach(r => {
      r.mesh.visible = rise > 0;
      r.u.uRise.value = rise;
      if (r.edges) { r.edges.visible = edgeT > 0; r.edges.material.opacity = (r.edgeOpacity ?? 0.6) * edgeT; }
    });
  }
  function setTransparent(m, on) {               // switching needs a shader refresh, so only on a change
    if (m.transparent !== on) { m.transparent = on; m.needsUpdate = true; }
  }
  function fadeLate(t) {
    for (const f of floors) for (const obj of f.late) obj.traverse(n => {
      if (!n.material) return;
      n.visible = t > 0;
      setTransparent(n.material, t < 1 || !!n.userData.brTransparent);
      n.material.opacity = (n.userData.brOpacity ?? 1) * t;
    });
    (o.hide || []).forEach(n => { n.visible = t > 0; if (n.material) { setTransparent(n.material, t < 1); n.material.opacity = t; } });
  }
  function apply(T) {                            // set everything for global progress T (0..1); idempotent
    const at = k => { const s = steps.find(x => x.key === k); return span(T, s.t0, s.t1); };
    const tRead = at('read'), tSort = at('sort'), tAlign = at('align'), tPair = at('pair'), tMerge = at('merge'), tRaise = at('raise'), tFin = at('finish');
    const sb = sheetBox(0), x0 = sb.min.x - 2, x1 = sb.max.x + 2;
    scanPlane.constant = x0 + (x1 - x0) * ease(tRead);
    made.scan.visible = tRead > 0 && tRead < 1;
    made.scan.position.set(scanPlane.constant, sb.min.y + 0.05, (sb.min.z + sb.max.z) / 2);
    made.scan.scale.set(1, 1, sb.max.z - sb.min.z + 4);
    const ab = stackBox(false);
    sweepPlane.constant = ab.min.x - 1 + (ab.max.x - ab.min.x + 2) * ease(tPair);
    const sorted = ease(tSort);
    made.floors.forEach((F, i) => {
      setFloorPlace(F, ease(span(tAlign, 0, 0.55)), ease(span(tAlign, 0.45, 1)));
      // Lines: faint until read; then ink; sorting colours them and fades the ignored ones;
      // wall and glass lines give way to the pieces and then the walls; stair lines stay until the stairs appear.
      const order = floors.length > 1 ? i / (floors.length - 1) : 0;
      const riseEnd = 0.62 + order * 0.38, rise = ease(span(tRaise, order * 0.38, riseEnd));
      for (const [cat, L] of Object.entries(F.lines)) {
        L.faint.visible = tRead < 1;
        L.ink.material.color.set(C.ink).lerp(L.color, sorted);
        let op;
        if (cat === 'noise') op = (0.9 - 0.8 * sorted) * (1 - ease(tFin));
        else if (cat === 'stair') op = 0.9 * (1 - ease(tFin));
        else op = 0.9 * (1 - 0.7 * ease(tPair)) * (1 - rise);
        L.ink.material.opacity = Math.max(0, op);
        L.ink.visible = op > 0.003;
      }
      F.pieces.forEach(p => {
        const op = ease(tPair) * (1 - ease(tMerge));
        p.m.material.opacity = (p.glass ? 0.55 : 0.95) * op; p.e.material.opacity = 0.9 * op;
        p.m.visible = p.e.visible = op > 0.003;
      });
      F.runs.forEach(r => {
        const op = ease(tMerge) * (1 - rise);
        r.m.material.opacity = (r.glass ? 0.6 : 1) * op; r.e.material.opacity = op;
        r.m.visible = r.e.visible = op > 0.003;
      });
      showSolids(F, rise, ease(span(tRaise, riseEnd - 0.12, riseEnd)));
    });
    fadeLate(ease(tFin));
    // Camera: the sheet from above -> the lined-up plan -> tilted towards north (no turn yet) -> turning round to the
    // usual heading while the walls rise -> the usual view. Turning only while tilted avoids a fast spin near the top view.
    const top0 = pose(sheetBox(0), DOWN), top1 = pose(sheetBox(1), DOWN);
    const fd = finalDir(), azF = Math.atan2(fd.x, fd.z), elF = Math.max(20, Math.min(60, Math.asin(-fd.y) / D2R));
    const turn = Math.atan2(Math.sin(azF - NORTH), Math.cos(azF - NORTH));          // the short way round
    const obl = pose(stackBox(0), dirAt(NORTH, 52));
    const fin = { pos: final.pos.clone(), target: final.target.clone() };
    let p = top0;
    if (tAlign > 0) p = lerpPose(top0, top1, ease(span(tAlign, 0, 0.5)));
    if (tAlign > 0.5) p = lerpPose(top1, obl, ease(span(tAlign, 0.5, 1)));
    if (tRaise > 0) { const e = ease(tRaise); p = pose(stackBox(e), dirAt(NORTH + turn * e, 52 + (elF - 52) * e)); }
    if (tFin > 0) p = lerpPose(pose(stackBox(1), dirAt(NORTH + turn, elF)), fin, ease(tFin));
    setPose(p);
    // Step list, bar and caption.
    const now = steps.find(s => T < s.t1) || steps[steps.length - 1], ended = T >= 1;
    if (st.step !== now.key || st.captionDirty || st.ended !== ended) {      // at the very end, tick the last step too
      st.step = now.key; st.captionDirty = false; st.ended = ended;
      card.querySelectorAll('#br-steps li').forEach(li => {
        const s = steps.find(x => x.key === li.dataset.k);
        li.classList.toggle('br-done', T >= s.t1); li.classList.toggle('br-now', s === now && T < 1);
        li.querySelector('i').textContent = T >= s.t1 ? '✓' : String(steps.indexOf(s) + 1);
      });
      sub.innerHTML = `<b>${now.title}.</b> ${now.caption(st.settings)}`;
    }
    card.querySelector('#br-bar i').style.width = (T * 100).toFixed(1) + '%';
    sub.style.display = st.captions && st.phase === 'play' ? 'block' : 'none';
  }

  // ---------------------------------------------------------------- phases: settings -> play -> done
  function enter() {                             // hide the finished model, show the drawing
    if (modes) { if (modes.mode !== 'orbit') modes.setMode('orbit'); modes.lock(true); }
    // Finish any glide left from the last mouse drag now, so it does not keep turning the view during or after the replay.
    const damping = controls.enableDamping;
    controls.enableDamping = false; controls.update(); controls.enableDamping = damping;
    document.body.classList.add('br-on');
    controls.enabled = false;
    renderer.localClippingEnabled = true;
    floors.forEach(f => { f.group.visible = true; });
    (o.others || []).forEach(g => { g.visible = false; });
    make();
    card.style.display = 'block';
  }
  function openSettings() {
    const fromViewer = st.phase === 'done';
    enter();
    // Started from the viewer (Replay / Build settings): end on the view you left, not the start-up view.
    if (fromViewer) { final.pos.copy(camera.position); final.target.copy(controls.target); }
    st.phase = 'settings'; st.T = 0;
    $('br-settings').style.display = 'block'; $('br-play').style.display = 'none';
    syncInputs(); markSpeed(); applySettings();
    apply(0);
    sub.style.display = 'none';
  }
  function generate() {
    if (st.phase !== 'settings') openSettings();
    applySettings();
    st.phase = 'play'; st.T = 0; st.step = null; st.paused = false; st.endAt = 0; st.last = performance.now();
    $('br-settings').style.display = 'none'; $('br-play').style.display = 'block';
    apply(0);
  }
  function finish() {                            // the normal viewer, exactly as without the replay
    st.T = 1;
    if (made) apply(1);
    unmake();
    floors.forEach(f => {
      f.group.position.set(0, st.settings[f.key].level - f.level, 0);
      showSolids({ f }, 1, 1);
    });
    fadeLate(1);
    floors.forEach(f => f.late.forEach(obj => obj.traverse(n => { if (n.material) setTransparent(n.material, !!n.userData.brTransparent); })));
    (o.hide || []).forEach(n => { n.visible = true; if (n.material) { setTransparent(n.material, false); n.material.opacity = 1; } });
    setPose({ pos: final.pos.clone(), target: final.target.clone() });
    renderer.localClippingEnabled = false;
    controls.enabled = true;
    card.style.display = 'none'; sub.style.display = 'none';
    document.body.classList.remove('br-on');
    st.phase = 'done';
    if (o.restore) o.restore();
    if (modes) modes.lock(false);
  }
  function skip() {
    if (st.phase === 'off' || st.phase === 'done') return;
    finish();
  }
  function seek(T) {                             // jump to a moment of the replay and hold it there (tests, screenshots)
    if (st.phase !== 'play') generate();
    st.paused = true; st.T = clamp01(T); st.step = null;
    apply(st.T);
  }
  function tick() {
    if (st.phase === 'settings') { apply(0); return; }
    if (st.phase !== 'play') return;
    if (st.paused) { apply(st.T); return; }
    const now = performance.now(), dt = Math.min(0.1, (now - st.last) / 1000);
    st.last = now;
    st.T = Math.min(1, st.T + dt / SPEEDS[st.speed]);
    apply(st.T);
    if (st.T >= 1) { if (!st.endAt) st.endAt = now + 700; else if (now >= st.endAt) { st.endAt = 0; finish(); } }
  }
  addEventListener('keydown', e => {
    if (e.code === 'Escape' && st.phase === 'play') { skip(); e.preventDefault(); }
  });

  // Start-up: ?build=0 (or any ?mode=) skips straight to the model; ?build=play starts the replay at once.
  const q = new URLSearchParams(location.search);
  if (q.get('speed') && SPEEDS[q.get('speed')]) st.speed = q.get('speed');
  if (q.get('captions') === '0') { st.captions = false; $('br-cap').checked = false; }
  const api = { tick, generate, skip, openSettings, seek, get phase() { return st.phase; }, state: st, steps };
  window.__build = api;
  if (q.get('build') === '0' || q.has('mode')) { st.phase = 'done'; applySettings(); }
  else { openSettings(); if (q.get('build') === 'play') generate(); }
  return api;
}
