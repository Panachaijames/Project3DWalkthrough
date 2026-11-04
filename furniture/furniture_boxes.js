// ---------------------------------------------------------------------------
// Furniture boxes: one coloured box per piece of furniture, a legend with a height text box per kind,
// Walk stops you at the boxes (Ghost does not), and the family list as a CSV file.
// Inlined into each viewer's module script after viewer_modes.js; the page's THREE is passed in.
// The model JSON (furnitureKinds, furniture), the kinds table and the CSV columns are in furniture/README.md.
//
//   Boxes   - a unit box per piece, scaled to w x height x d and turned by rot; it stands on z0 (the top of the piece
//             it sits on, else the kind's base) and is named 'furn:<kind>:<id>'
//   Heights - a text box per kind (mm, 10 - 5000): typing moves that kind's boxes and the pieces standing on them
//   Walk    - a box is in its level's colliders while its kind is shown and set to stop you, and, while 'Keep doorways clear'
//             is ticked (the default), only if the model's 'approach' of the piece is empty (no door or passage to keep clear);
//             Walk's rays at 0.35 m and 1.2 m do the rest (a box lower than the knee ray is stepped over). The faces are
//             single-sided, so a player whose eye is inside a box (entered Walk on it) walks out. Ghost ignores colliders.
//   Orbit   - a label under the pointer: kind, family, size and level
//   CSV     - the family list with the heights typed in (nodownload=1 in the address: nothing is downloaded)
//
// Host passes:
//   { THREE, model, FL, panel, canvas, camera, getMode, onChange, params, project }
//     model:   the model JSON (furnitureKinds, furniture, floors, offset)
//     FL:      per level { key, name, level, group, colliders, walkables, late }: the boxes join group, colliders and late
//     getMode: () => 'orbit' | 'walk' | 'ghost'      onChange: () => void, after a height, a tick or a reset
//     params:  URLSearchParams of the address (default: this page's)     project: names the storage key and the CSV file
// Returns null when the model has no furniture, else
//   { pieces, kinds, setHeight, setVisible, setBlocks, setKeepDoorways, keepDoorways, reset, csv, saveCsv, meshOf, apply }
// pieces() lists each piece with its approach (ids of the doors and passages it stands in front of) and blocking (stops Walk now).
// apply() puts the ticks back on the boxes: the build replay shows every 'late' object when it ends, so call it from the
// page's restore hook. In a page, after installViewerModes and before installBuildReplay (which reads each level's 'late' list
// as it starts):
//   const furniture = installFurnitureBoxes({ THREE, model: D, FL, panel: document.getElementById('panel'), canvas: renderer.domElement,
//                                             camera, getMode: () => modes.mode, params: new URLSearchParams(location.search), project: D.photoName });
//   ... installBuildReplay({ ..., restore: () => { applyFloor(); applyChecks(); if (furniture) furniture.apply(); } });
//   window.__host = { ..., furniture };
// ---------------------------------------------------------------------------
function installFurnitureBoxes(o) {
  const { THREE, model, FL, panel, canvas, camera, onChange } = o;
  const getMode = o.getMode || (() => 'orbit');
  const D2R = Math.PI / 180, MIN_H = 10, MAX_H = 5000;
  const params = o.params || new URLSearchParams(location.search);
  const project = o.project || model.photoName || model.shortName || model.project || 'model';
  const off = model.offset || [0, 0];
  const whole = v => Math.floor(v + 0.5);                        // whole mm, a half goes up (as furniture_kit.csv_text rounds)

  // ---------------------------------------------------------------- kinds and pieces
  const allKinds = (model.furnitureKinds || []).map(k => ({ ...k, height: whole(k.height), base: whole(k.base), defaultHeight: whole(k.height),
    visible: true, blocks: k.blocks !== false, items: [] }));
  const kindOf = new Map(allKinds.map(k => [k.key, k])), itemOf = new Map(), items = [];
  for (const d of model.furniture || []) {
    const kind = kindOf.get(d.kind), fl = FL[d.floor];
    if (!kind || !fl) { console.warn('furniture box left out (unknown kind or level):', d.id); continue; }
    const p = { d, kind, fl, mesh: null, z0mm: 0, approach: Array.isArray(d.approach) ? d.approach.map(String) : [] };
    kind.items.push(p); itemOf.set(d.id, p); items.push(p);
  }
  if (!items.length) return null;
  const kinds = allKinds.filter(k => k.items.length);            // a kind nobody uses gets no row
  const inApproach = items.filter(p => p.approach.length);       // the pieces that stand where a door or a passage is walked through
  let keepDoorways = true;                                       // the 'Keep doorways clear' tick: those pieces do not stop Walk

  // The underside above the level in mm: the top of the piece it stands on (that piece's own base plus its height),
  // else the kind's base. Whole mm all the way, so the metres below are exact.
  const under = (p, depth = 0) => {
    const s = p.d.on && depth < 3 ? itemOf.get(p.d.on) : null;
    return s ? under(s, depth + 1) + s.kind.height : p.kind.base;
  };
  function place(p) {                                            // position, size and matrices of one box
    const { d, mesh } = p, h = p.kind.height / 1000;
    p.z0mm = under(p);
    mesh.position.set(d.x, p.fl.level + p.z0mm / 1000, -d.y);    // plan (x, y) -> three.js (x, z = -y)
    mesh.scale.set(d.w, h, d.d);
    mesh.userData.size = [d.w, d.d, h];
    mesh.updateWorldMatrix(true, true);                          // raycasts (Walk, hover) may come before the next frame
  }
  const placeAll = () => items.forEach(place);
  // Shown and stopping: a box is a collider of its level only while its kind is shown AND set to stop you, and not (while the
  // doorways are kept clear) when it stands in the approach of a door or a passage. Such a box stays drawn.
  const stops = p => p.kind.visible && p.kind.blocks && !(keepDoorways && p.approach.length);
  function sync(kind) {
    for (const p of kind.items) {
      const col = p.fl.colliders, i = col.indexOf(p.mesh), want = stops(p);
      p.mesh.visible = kind.visible;
      if (want && i < 0) col.push(p.mesh);
      else if (!want && i >= 0) col.splice(i, 1);
    }
  }

  // ---------------------------------------------------------------- the boxes
  const unit = new THREE.BoxGeometry(1, 1, 1).translate(0, 0.5, 0);      // 1 m each way, base at y = 0 (no bounds tree: 12 triangles)
  const outline = new THREE.EdgesGeometry(unit);
  for (const k of kinds) {
    // The faces sit a little behind their outline, so the thin darker edges are never eaten by them. They are single-sided:
    // Walk's rays from inside a box meet none of its faces (double-sided ones would make the inside look like open space
    // one metre deep, and then wall you in), so a player whose eye is inside a box can always walk out.
    k.face = new THREE.MeshStandardMaterial({ color: k.colour, roughness: 0.85, side: THREE.FrontSide, polygonOffset: true, polygonOffsetFactor: 1, polygonOffsetUnits: 1 });
    k.edge = new THREE.LineBasicMaterial({ color: new THREE.Color(k.colour).multiplyScalar(0.4) });
    for (const p of k.items) {
      const m = new THREE.Mesh(unit, k.face);
      m.name = `furn:${k.key}:${p.d.id}`;
      m.rotation.y = p.d.rot * D2R;
      m.add(new THREE.LineSegments(outline, k.edge));
      m.userData = { id: p.d.id, kind: k.key, family: p.d.family, floor: p.d.floor, size: [] };
      p.mesh = m;
      p.fl.group.add(m);
      if (p.fl.late) p.fl.late.push(m);                          // like the floor plates: they appear at the end of the build replay
    }
  }

  // ---------------------------------------------------------------- typed heights (and the doorways tick) are remembered per project
  const storeKey = 'walkthrough-furniture-heights:' + project;
  function persist() {
    try {
      const typed = {};                                          // only what differs from the model: the typed heights, and the doorways tick when it is off
      for (const k of kinds) if (k.height !== k.defaultHeight) typed[k.key] = k.height;
      if (!keepDoorways) typed.keepDoorways = false;
      if (Object.keys(typed).length) localStorage.setItem(storeKey, JSON.stringify(typed));
      else localStorage.removeItem(storeKey);
    } catch (e) { /* storage blocked: the heights and the tick last for this visit only */ }
  }
  try {
    const typed = JSON.parse(localStorage.getItem(storeKey) || '{}');
    for (const k of kinds) { const v = whole(Number(typed[k.key])); if (v >= MIN_H && v <= MAX_H) k.height = v; }
    if (typed.keepDoorways === false) keepDoorways = false;
  } catch (e) { /* nothing saved, or storage blocked */ }

  // ---------------------------------------------------------------- the legend, with a height text box per kind
  const css = document.createElement('style');
  css.textContent = `
.fb-block{margin-top:10px;border-top:1px solid var(--line,#d5dade);padding-top:8px;font-size:12.5px}
.fb-title{display:flex;justify-content:space-between;align-items:center;font-size:11px;letter-spacing:.06em;text-transform:uppercase;color:var(--muted,#5b6670)}
.fb-title label{font-size:12px;letter-spacing:0;text-transform:none;color:var(--ink,#1d2329)}
.fb-note{color:var(--muted,#5b6670);font-size:11.5px;margin:4px 0 6px}
.fb-door{display:flex;align-items:center;gap:6px;margin:0 0 6px;font-size:12px;color:var(--ink,#1d2329)}
.fb-door input{margin:0}
.fb-row{display:grid;grid-template-columns:16px 12px minmax(0,1fr) 52px 38px;gap:6px;align-items:center;padding:1px 0}
.fb-row input[type=checkbox]{margin:0;justify-self:center}
.fb-head{font-size:10px;color:var(--muted,#5b6670);text-align:center}
.fb-head span:nth-child(3){text-align:left}
.fb-sw{width:12px;height:12px;border-radius:3px;border:1px solid #0003;box-sizing:border-box}
.fb-lab{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.fb-h{width:100%;box-sizing:border-box;font:inherit;font-size:12.5px;text-align:right;padding:2px 5px;border:1px solid var(--line,#d5dade);border-radius:5px;background:#fff;color:var(--ink,#1d2329);color-scheme:light}
.fb-h.fb-edited{border-color:var(--accent,#2f6f8f)}
.fb-h.fb-bad{border-color:#b42318;background:#fdecea}
.fb-btns{display:flex;gap:6px;flex-wrap:wrap;margin-top:8px}
.fb-tip{position:fixed;display:none;pointer-events:none;z-index:5;max-width:min(340px,calc(100vw - 24px));overflow-wrap:anywhere;background:#1d2329eb;color:#fff;border-radius:8px;padding:6px 10px;font-size:12px;line-height:1.4}
.fb-tip span{color:#c9d1d8}
`;
  document.head.appendChild(css);
  const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const box = document.createElement('div');
  box.className = 'fb-block';
  box.innerHTML = `<div class="fb-title"><span>Furniture boxes</span><label><input type="checkbox" class="fb-all" checked> show</label></div>
<div class="fb-note">Type a height in mm for each kind. Walk: boxes stop you; Ghost passes through.</div>${inApproach.length ? `
<label class="fb-door" title="${inApproach.length} of the boxes stand in front of a door or a passage. Ticked: Walk is not stopped by them (they stay drawn), so every doorway can be walked through. Unticked: they stop you like any other box."><input type="checkbox" class="fb-keep" checked> Keep doorways clear</label>` : ''}
<div class="fb-row fb-head"><span></span><span></span><span>Kind</span><span>mm</span><span title="Walk stops you at these boxes">stops</span></div>
${kinds.map(k => `<div class="fb-row" data-k="${esc(k.key)}">
  <input type="checkbox" class="fb-show" title="Show these boxes" aria-label="Show ${esc(k.label)}">
  <i class="fb-sw" style="background:${esc(k.colour)}"></i>
  <span class="fb-lab" title="${esc(k.label)}">${esc(k.label)} (${k.items.length})</span>
  <input type="text" class="fb-h" inputmode="numeric" autocomplete="off" spellcheck="false" title="Height in mm, ${MIN_H} to ${MAX_H}" aria-label="${esc(k.label)}: height in mm">
  <input type="checkbox" class="fb-blk" title="Walk stops you at these boxes" aria-label="${esc(k.label)}: Walk stops you">
</div>`).join('')}
<div class="fb-btns"><button class="fb-reset">Reset heights</button><button class="fb-save">Save list (CSV)</button></div>`;
  panel.appendChild(box);
  const rows = new Map([...box.querySelectorAll('.fb-row[data-k]')].map(r => [r.dataset.k, r]));
  const masterBox = box.querySelector('.fb-all'), keepBox = box.querySelector('.fb-keep');      // keepBox: none when no piece is in an approach
  function showRow(k, keepText) {                                // the row follows the kind; the box being typed in keeps its text
    const r = rows.get(k.key), h = r.querySelector('.fb-h');
    r.querySelector('.fb-show').checked = k.visible;
    r.querySelector('.fb-blk').checked = k.blocks;
    if (!keepText) { h.value = k.height; h.classList.remove('fb-bad'); }
    h.classList.toggle('fb-edited', k.height !== k.defaultHeight);
    masterBox.checked = kinds.every(x => x.visible);
    masterBox.indeterminate = !masterBox.checked && kinds.some(x => x.visible);
  }
  const changed = () => { if (onChange) onChange(); };

  function setHeight(key, mm, keepText) {
    const k = kindOf.get(key), v = whole(Number(mm));
    if (!k || !(v >= MIN_H && v <= MAX_H)) return false;
    k.height = v;
    placeAll(); persist(); showRow(k, keepText); changed();
    return true;
  }
  function setVisible(key, on) {
    const k = kindOf.get(key);
    if (!k) return false;
    k.visible = !!on; sync(k); showRow(k, true); changed();
    return true;
  }
  function setBlocks(key, on) {
    const k = kindOf.get(key);
    if (!k) return false;
    k.blocks = !!on; sync(k); showRow(k, true); changed();
    return true;
  }
  const showKeep = () => { if (keepBox) keepBox.checked = keepDoorways; };
  function setKeepDoorways(on) {
    keepDoorways = !!on; kinds.forEach(sync); showKeep(); persist(); changed();
    return true;
  }
  function reset() {                                             // the heights only: the ticks stay as they are
    kinds.forEach(k => { k.height = k.defaultHeight; });
    placeAll(); persist(); kinds.forEach(k => showRow(k)); changed();
  }
  const apply = () => kinds.forEach(sync);

  // A height as typed: whole mm, from 10 to 5000, or null ('', '4,5', '-3', 'abc', 6, 9999).
  const typed = s => {
    const v = /^\s*\d+(\.\d*)?\s*$/.test(s) ? whole(Number(s)) : NaN;
    return v >= MIN_H && v <= MAX_H ? v : null;
  };
  const rowOf = e => e.target.closest('.fb-row[data-k]'), before = new Map();     // before: a kind's height when you clicked into its box
  box.addEventListener('focusin', e => {
    if (!e.target.matches('.fb-h')) return;
    const k = kindOf.get(rowOf(e).dataset.k), el = e.target;
    before.set(k.key, k.height);
    const v0 = el.value;                                         // the number is selected, so typing replaces it (after the click's own caret) - unless a key got in first
    setTimeout(() => { if (document.activeElement === el && el.value === v0) el.select(); }, 0);
  });
  box.addEventListener('input', e => {
    if (!e.target.matches('.fb-h')) return;
    const k = kindOf.get(rowOf(e).dataset.k), v = typed(e.target.value);
    e.target.classList.toggle('fb-bad', v === null && e.target.value.trim() !== '');
    if (v !== null && v !== k.height) setHeight(k.key, v, true);       // applies as you type a valid number
  });
  // Enter or leaving the box keeps a good number; anything else (and Escape) goes back to the height from before you typed,
  // which also undoes the half-typed numbers that were applied on the way (the 999 of 9999).
  function commit(el, cancel) {
    const k = kindOf.get(el.closest('.fb-row').dataset.k), v = cancel ? null : typed(el.value), to = v !== null ? v : before.has(k.key) ? before.get(k.key) : k.height;
    if (to !== k.height) setHeight(k.key, to); else showRow(k);
  }
  box.addEventListener('focusout', e => { if (e.target.matches('.fb-h')) commit(e.target); });
  box.addEventListener('keydown', e => {
    if (!e.target.matches('.fb-h')) return;
    if (e.key === 'Enter') { commit(e.target); e.target.blur(); }
    else if (e.key === 'Escape') { commit(e.target, true); e.target.blur(); }
  });
  box.addEventListener('change', e => {
    if (e.target.matches('.fb-all')) { const on = e.target.checked; kinds.forEach(k => { k.visible = on; sync(k); showRow(k, true); }); changed(); }
    else if (e.target.matches('.fb-show')) setVisible(rowOf(e).dataset.k, e.target.checked);
    else if (e.target.matches('.fb-blk')) setBlocks(rowOf(e).dataset.k, e.target.checked);
    else if (e.target.matches('.fb-keep')) setKeepDoorways(e.target.checked);
  });
  box.querySelector('.fb-reset').onclick = reset;
  box.querySelector('.fb-save').onclick = () => saveCsv();

  // ---------------------------------------------------------------- the family list (CSV, as furniture/README.md says)
  const COLUMNS = ['id', 'level', 'kind', 'kind_label', 'family', 'block', 'layer', 'dxf_handle', 'x_m', 'y_m', 'width_mm', 'depth_mm',
    'height_mm', 'base_mm', 'rotation_deg', 'on_top_of', 'merged', 'note'];
  // The same digits as Python's f'{v:.{n}f}' (n >= 1), which furniture_kit.csv_text uses: toFixed rounds an exact tie (12.25
  // to one decimal) up, Python to the even digit. Never '-0.000'.
  function fixed(v, n) {
    const a = Math.abs(v), exact = a.toFixed(n + 30), cut = exact.length - 30;
    let s = a.toFixed(n);
    if (/^50*$/.test(exact.slice(cut)) && Number(exact[cut - 1]) % 2 === 0) s = exact.slice(0, cut);
    return v < 0 && /[1-9]/.test(s) ? '-' + s : s;
  }
  const field = v => { const s = v === null || v === undefined ? '' : String(v); return /[",\r\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s; };
  function csv() {                                               // no byte-order mark: the download adds it
    const level = new Map(model.floors.map((f, i) => [f.key, i])), order = new Map(kinds.map((k, i) => [k.key, i]));
    const sorted = [...items].sort((a, b) => level.get(a.d.floor) - level.get(b.d.floor) || order.get(a.d.kind) - order.get(b.d.kind)
      || (a.d.id < b.d.id ? -1 : a.d.id > b.d.id ? 1 : 0));
    const lines = sorted.map(p => {
      const d = p.d;
      return [d.id, d.floor, d.kind, p.kind.label, d.family, d.block, d.layer, d.handle, fixed(d.x + off[0], 3), fixed(d.y + off[1], 3),
        whole(d.w * 1000), whole(d.d * 1000), p.kind.height, p.z0mm, fixed(d.rot, 1), d.on, d.n === undefined ? 1 : d.n, d.note].map(field).join(',');
    });
    return [COLUMNS.join(','), ...lines].join('\r\n') + '\r\n';
  }
  function saveCsv() {
    const text = csv();
    if (params.get('nodownload') === '1') return text;
    const url = URL.createObjectURL(new Blob([new Uint8Array([0xEF, 0xBB, 0xBF]), text], { type: 'text/csv;charset=utf-8' }));    // UTF-8 with a byte-order mark: Excel then reads Thai text right
    const a = document.createElement('a');
    a.href = url; a.download = `${project}_furniture_list.csv`.replace(/[^\w.-]+/g, '-');
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 4000);
    return text;
  }

  // ---------------------------------------------------------------- the label under the pointer (Orbit only)
  const tip = document.createElement('div');
  tip.className = 'fb-tip';
  document.body.appendChild(tip);
  const ray = new THREE.Raycaster(), ndc = new THREE.Vector2();
  ray.firstHitOnly = true;
  let pending = null, timer = 0;
  const pieceOf = m => { const p = itemOf.get(m.userData.id); return p && p.mesh === m ? p : null; };
  const showing = obj => { for (let n = obj; n; n = n.parent) if (!n.visible) return false; return true; };
  const hide = () => { pending = null; tip.style.display = 'none'; };
  function hover() {
    timer = 0;
    const at = pending;
    if (!at || getMode() !== 'orbit') { hide(); return; }
    const r = canvas.getBoundingClientRect();
    ray.setFromCamera(ndc.set((at.x - r.left) / r.width * 2 - 1, -(at.y - r.top) / r.height * 2 + 1), camera);
    // The nearest thing under the pointer among the boxes and what hides them (walls, floor plates; glass and the
    // invisible Walk skins do not hide anything).
    const hides = Object.values(FL).filter(f => showing(f.group)).flatMap(f => f.colliders.concat(f.walkables || []))
      .filter(m => !pieceOf(m) && m.material && m.material.visible !== false && !m.material.transparent && showing(m));
    const hit = ray.intersectObjects(items.map(p => p.mesh).filter(showing).concat(hides), false)[0];
    const p = hit && pieceOf(hit.object);
    if (!p) { tip.style.display = 'none'; return; }
    const d = p.d, h = p.kind.height / 1000, z0 = p.z0mm / 1000;
    const kept = keepDoorways && p.kind.blocks && p.approach.length;        // it would stop you, but the doorway it stands in front of is kept clear
    tip.innerHTML = `<b>${esc(p.kind.label)}</b><br>${esc(d.family)}<br><span>${d.w.toFixed(2)} × ${d.d.toFixed(2)} × ${h.toFixed(2)} m` +
      `${z0 > 0 ? ', from ' + z0.toFixed(2) + ' m' : ''} · ${esc(p.fl.name || d.floor)}</span>` +
      `${kept ? `<br><span>does not stop you: in the approach of ${esc(p.approach.join(', '))}</span>` : ''}`;
    tip.style.display = 'block';
    tip.style.left = Math.max(4, Math.min(at.x + 14, innerWidth - tip.offsetWidth - 8)) + 'px';
    tip.style.top = Math.max(4, Math.min(at.y + 18, innerHeight - tip.offsetHeight - 8)) + 'px';
  }
  canvas.addEventListener('pointermove', e => {
    if (e.pointerType === 'touch' || e.buttons || getMode() !== 'orbit') { hide(); return; }     // not while dragging, nor in Walk / Ghost
    pending = { x: e.clientX, y: e.clientY };
    if (!timer) timer = setTimeout(hover, 50);                   // at most 20 times a second; the last position always gets its turn
  });
  canvas.addEventListener('pointerleave', hide);
  canvas.addEventListener('pointerdown', hide);
  canvas.addEventListener('wheel', hide, { passive: true });
  addEventListener('keydown', () => setTimeout(() => { if (getMode() !== 'orbit') hide(); }, 0));     // 2 / 3 switch the mode under a still pointer

  placeAll(); apply(); kinds.forEach(k => showRow(k)); showKeep();
  return {
    // visible / blocks are the kind's ticks; blocking is what Walk does now (the box is in its level's colliders)
    pieces: () => items.map(p => ({ ...p.d, approach: p.approach.slice(), z0: p.z0mm / 1000, z1: (p.z0mm + p.kind.height) / 1000, visible: p.kind.visible,
      blocks: p.kind.blocks, blocking: stops(p) })),
    kinds: () => kinds.map(k => ({ key: k.key, label: k.label, colour: k.colour, height: k.height, defaultHeight: k.defaultHeight, count: k.items.length,
      visible: k.visible, blocks: k.blocks })),
    setHeight, setVisible, setBlocks, setKeepDoorways, keepDoorways: () => keepDoorways, reset, csv, saveCsv, apply,
    meshOf: id => (itemOf.get(id) || {}).mesh || null,
  };
}
