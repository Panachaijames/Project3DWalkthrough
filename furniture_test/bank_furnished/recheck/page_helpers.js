// Injected into bank_furnished.html by recheck.mjs (an independent check; nothing here changes what the page draws,
// except topView, which draws one extra frame with its own camera for a picture and puts everything back). Defines window.__sk.
(() => {
  const F = window.__bankFurnished, THREE = F.THREE, H = window.__host, fur = H.furniture;
  const D2R = Math.PI / 180;
  const pieceList = fur.pieces();
  const byId = new Map(pieceList.map(p => [p.id, p]));
  const boxOf = id => fur.meshOf(id);
  const allBoxes = pieceList.map(p => boxOf(p.id));
  const angle = (x, y) => ((Math.atan2(y, x) / D2R) % 360 + 360) % 360;
  const adiff = (a, b) => ((a - b + 540) % 360) - 180;
  let placementsFull = {};                                   // model -> key -> { turn, mirror } from placements.json (passed in)

  // the state of every box: material (uuid), its outline's material, visible, in its level's colliders, position, scale
  function boxState() {
    const out = {};
    for (const p of pieceList) {
      const b = boxOf(p.id), line = b.children.find(c => c.isLineSegments);
      out[p.id] = { mat: b.material.uuid, matVisible: b.material.visible, line: line ? line.material.uuid : null, lineVisible: line ? line.material.visible : null,
        visible: b.visible, collider: H.FL[p.floor].colliders.includes(b), pos: b.position.toArray().map(v => +v.toFixed(5)), scale: b.scale.toArray().map(v => +v.toFixed(5)) };
    }
    return out;
  }
  // world points of an object's meshes (every k-th vertex), each with its mesh's index in traversal order
  function points(obj, maxPer = 4000) {
    obj.updateWorldMatrix(true, true);
    const pts = [];
    let mi = 0;
    obj.traverse(o => {
      if (!o.isMesh) return;
      const pos = o.geometry.attributes.position, k = Math.max(1, Math.ceil(pos.count / maxPer)), v = new THREE.Vector3();
      for (let i = 0; i < pos.count; i += k) { v.fromBufferAttribute(pos, i).applyMatrix4(o.matrixWorld); pts.push([v.x, v.y, v.z, mi]); }
      mi++;
    });
    return pts;
  }
  function meshNormal(obj, index) {                          // average world normal of one mesh (by traversal index)
    let mi = 0, res = null;
    obj.traverse(o => {
      if (!o.isMesh || mi++ !== index) return;
      const n = o.geometry.attributes.normal, nm = new THREE.Matrix3().getNormalMatrix(o.matrixWorld), v = new THREE.Vector3(), s = new THREE.Vector3();
      for (let i = 0; i < n.count; i++) s.add(v.fromBufferAttribute(n, i).applyMatrix3(nm).normalize());
      res = s.normalize();
    });
    return res;
  }
  function inBox(b, x, z, tol) {                             // a world point inside a box's plan rectangle (tol metres)?
    const inv = new THREE.Matrix4().copy(b.matrixWorld).invert();
    const v = new THREE.Vector3(x, b.matrixWorld.elements[13] + 0.01, z).applyMatrix4(inv);
    return Math.abs(v.x * b.scale.x) <= b.scale.x / 2 + tol && Math.abs(v.z * b.scale.z) <= b.scale.z / 2 + tol;
  }
  // a model faces its block's -Y (plan 270 deg) turned by inBlock; a 'mirror y' piece faces +Y; then the INSERT's turn
  const expectedFront = (turn, mirror, inBlock = 0) => ((mirror === 'mirror y' ? -(270 + inBlock) : 270 + inBlock) + turn + 720) % 360;
  const current = () => [...F.variants.values()].find(x => Object.values(x.groups).some(g => g.parent)) || null;

  // every copy of the way shown now: where it stands against its box(es), and which way it faces (from its own geometry)
  function copies(tol = 0.05) {
    const v = current();
    if (!v) return { mode: F.mode, copies: [] };
    const rows = [];
    for (const c of v.copies) {
      const p = c.p, model = p.model;
      const obj = c.lod ? c.lod.levels[c.lod.getCurrentLevel()].object : c.obj;
      const pts = points(obj);
      let minY = Infinity, maxY = -Infinity, minX = Infinity, maxX = -Infinity, minZ = Infinity, maxZ = -Infinity;
      for (const q of pts) { minY = Math.min(minY, q[1]); maxY = Math.max(maxY, q[1]); minX = Math.min(minX, q[0]); maxX = Math.max(maxX, q[0]); minZ = Math.min(minZ, q[2]); maxZ = Math.max(maxZ, q[2]); }
      const boxes = p.boxes;
      boxes.forEach(b => b.updateWorldMatrix(true, false));
      const bMinY = Math.min(...boxes.map(b => new THREE.Box3().setFromObject(b).min.y));
      const inside = pts.filter(q => boxes.some(b => inBox(b, q[0], q[2], tol))).length / pts.length;
      const cx = (minX + maxX) / 2, cz = (minZ + maxZ) / 2;
      const bc = boxes.reduce((a, b) => a.add(b.getWorldPosition(new THREE.Vector3())), new THREE.Vector3()).divideScalar(boxes.length);
      const row = { model, key: p.key, floor: p.floor, what: c.what, level: c.lod ? c.lod.getCurrentLevel() : null,
        bottomVsBox_mm: +((minY - bMinY) * 1000).toFixed(1), height_m: +(maxY - minY).toFixed(3),
        insideBox: +inside.toFixed(3), centreFromBox_m: +Math.hypot(cx - bc.x, cz - bc.z).toFixed(3),
        bbox: [minX, minY, minZ, maxX, maxY, maxZ].map(x => +x.toFixed(4)),
        inFloorGroup: !!(c.obj.parent && c.obj.parent.parent === H.FL[p.floor].group), visible: c.obj.visible };
      const pl = (placementsFull[model] || {})[p.key];
      const mean = a => [a.reduce((s, q) => s + q[0], 0) / a.length, a.reduce((s, q) => s + q[2], 0) / a.length];
      if (!pl) { /* a stand-in (way P): no block turn to check */ }
      else if (model === 'visitor chair01') {                     // the backrest: the top fifth of the chair
        const [bx, bz] = mean(pts.filter(q => q[1] > minY + 0.8 * (maxY - minY)));
        row.front = +angle(cx - bx, -(cz - bz)).toFixed(1);
        row.expected = expectedFront(pl.turn, pl.mirror);
      } else if (model === 'working table') {                // the modesty panel's side (the block's -Y, where the visitor sits)
        const [tx, tz] = mean(pts.filter(q => q[3] === 0)), [px, pz] = mean(pts.filter(q => q[3] === 1));
        row.front = +angle(px - tx, -(pz - tz)).toFixed(1);
        row.expected = expectedFront(pl.turn, pl.mirror);
      } else if (model === 'monitor') {                      // the display surface's normal
        const n = meshNormal(obj, 2);
        row.front = +angle(n.x, -n.z).toFixed(1);
        row.expected = +expectedFront(pl.turn, pl.mirror, 0.4).toFixed(1);
        const kb = pts.filter(q => q[3] >= 3), on = byId.get(p.key).on, support = on ? boxOf(on) : null;
        if (support) support.updateWorldMatrix(true, false);
        row.support = on;
        row.keyboardMouseOverSupport = support ? +(kb.filter(q => inBox(support, q[0], q[2], 0)).length / kb.length).toFixed(2) : null;
        row.screenOverSupport = support ? +(pts.filter(q => q[3] <= 2 && inBox(support, q[0], q[2], 0)).length / pts.filter(q => q[3] <= 2).length).toFixed(2) : null;
      } else if (model === 'sofa') {                         // where its back pad is (above 0.6 m) from its centre
        const [bx, bz] = mean(pts.filter(q => q[1] > minY + 0.6));
        row.backPad = { angle: +angle(bx - cx, -(bz - cz)).toFixed(1), m: +Math.hypot(bx - cx, bz - cz).toFixed(3) };
      }
      if (row.front !== undefined) row.frontOff = +adiff(row.front, row.expected).toFixed(1);
      rows.push(row);
    }
    return { mode: F.mode, budget: F.budget, variant: v.name, copies: rows };
  }

  // what the chip should draw now, counted independently of renderer.info, the way three.js decides: shown (with its parents),
  // on the camera's layers, a shown material, in the camera's view unless not culled; LOD: the level in use; a transparent
  // double-sided material is drawn twice (back faces, then front)
  function expectedDraw() {
    const cam = H.camera, scene = F.scene;
    cam.updateMatrixWorld(); scene.updateMatrixWorld();
    const fr = new THREE.Frustum().setFromProjectionMatrix(new THREE.Matrix4().multiplyMatrices(cam.projectionMatrix, cam.matrixWorldInverse));
    let tris = 0, calls = 0, modelTrisInView = 0, modelTrisAll = 0;
    const visit = (o, inModel, inView) => {
      if (!o.visible) return;
      const isModel = inModel || /^bank furnished /.test(o.name);
      if (o.isLOD) { const lv = o.levels[o.getCurrentLevel()]; if (lv) visit(lv.object, true, inView); return; }
      if ((o.isMesh || o.isLine || o.isSprite) && o.material && o.layers.test(cam.layers)) {
        const g = o.geometry, n = o.isSprite ? 6 : (g.index ? g.index.count : g.attributes.position.count);
        const mats = Array.isArray(o.material) ? o.material : [o.material];
        const shown = mats.some(m => m.visible);
        const t = (o.isMesh || o.isSprite) ? n / 3 : 0;
        if (isModel && shown) modelTrisAll += t;
        if (shown && (!o.frustumCulled || (o.isSprite ? fr.intersectsSprite(o) : fr.intersectsObject(o)))) {
          const m = mats[0], twice = !Array.isArray(o.material) && m.transparent && m.side === THREE.DoubleSide && m.forceSinglePass === false ? 2 : 1;
          tris += t * twice; calls += twice;
          if (isModel) modelTrisInView += t;
        }
      }
      for (const c of o.children) visit(c, isModel, inView);
    };
    visit(scene, false, true);
    return { triangles: Math.round(tris), calls, modelTrianglesInView: Math.round(modelTrisInView), modelTrianglesAll: Math.round(modelTrisAll) };
  }
  function panel() {
    const t = s => (document.querySelector('#bf-panel ' + s) || {}).textContent;
    return { modelTris: t('.bf-mtris'), tris: t('.bf-tris'), calls: t('.bf-calls'), fps: t('.bf-fps'), dl: t('.bf-dl'), mem: t('.bf-mem'), load: t('.bf-load'),
      rows: [...document.querySelectorAll('#bf-panel tr[data-m]')].map(r => [r.dataset.m, r.cells[1].textContent, r.cells[2].textContent, r.cells[3].textContent]) };
  }
  async function counts() {
    await new Promise(r => setTimeout(r, 500));
    await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
    const info = { triangles: F.renderer.info.render.triangles, calls: F.renderer.info.render.calls };
    const exp = expectedDraw();
    await new Promise(r => setTimeout(r, 350));
    return { info, expected: exp, panel: panel(), live: F.live() };
  }
  // a plan picture: an orthographic camera looking down at one level, cut at 1.6 m like a plan; the furnished pieces'
  // box outlines drawn in red over the models (their faces stay hidden); the page draws its own frame again afterwards
  function topView(floorKey, cx, cy, halfH, aspect) {
    const f = H.FL[floorKey], level = f.group.position.y + f.level;
    const cam = new THREE.OrthographicCamera(-halfH * aspect, halfH * aspect, halfH, -halfH, 0.01, 1.6 + 1.5);
    cam.position.set(cx, level + 1.6, -cy); cam.up.set(0, 0, -1); cam.lookAt(cx, level, -cy); cam.updateMatrixWorld();
    const hidden = [];
    for (const [k, g] of Object.entries(H.FL)) if (k !== floorKey && g.group.visible) { g.group.visible = false; hidden.push(g.group); }
    const swapped = [];
    for (const b of allBoxes) {
      const line = b.children.find(c => c.isLineSegments);
      if (line && !line.material.visible && b.material && !b.material.visible) { swapped.push([line, line.material]); line.material = new THREE.LineBasicMaterial({ color: 0xe0004d }); }
    }
    F.renderer.render(F.scene, cam);
    const url = F.renderer.domElement.toDataURL('image/png');
    for (const [line, m] of swapped) line.material = m;
    for (const g of hidden) g.visible = true;
    return url;
  }
  // the mollie chairs' facing again, measured in a frame along the expected front (so a turned chair's axis-aligned box does
  // not bias it): the backrest (top fifth) should sit straight behind the centre of the chair's own outline
  function chairFacing() {
    const v = current();
    if (!v) return [];
    return v.copies.filter(c => c.p.model === 'visitor chair01').map(c => {
      const obj = c.lod ? c.lod.levels[c.lod.getCurrentLevel()].object : c.obj;
      const pts = points(obj, 20000), pl = placementsFull[c.p.model][c.p.key];
      const e = expectedFront(pl.turn, pl.mirror) * D2R, ex = Math.cos(e), ey = Math.sin(e);     // plan: x east, y north = -z
      let minY = Infinity, maxY = -Infinity;
      for (const q of pts) { minY = Math.min(minY, q[1]); maxY = Math.max(maxY, q[1]); }
      const uv = pts.map(q => { const px = q[0], py = -q[2]; return [px * ex + py * ey, -px * ey + py * ex, q[1]]; });
      const lo = [Math.min(...uv.map(a => a[0])), Math.min(...uv.map(a => a[1]))], hi = [Math.max(...uv.map(a => a[0])), Math.max(...uv.map(a => a[1]))];
      const cu = (lo[0] + hi[0]) / 2, cv = (lo[1] + hi[1]) / 2;
      const top = uv.filter(a => a[2] > minY + 0.8 * (maxY - minY));
      const bu = top.reduce((s, a) => s + a[0], 0) / top.length - cu, bv = top.reduce((s, a) => s + a[1], 0) / top.length - cv;
      return { key: c.p.key, turn: pl.turn, mirror: pl.mirror, expected: +(e / D2R).toFixed(1), frontOff: +(Math.atan2(-bv, -bu) / D2R).toFixed(1),
        depthAlongFront: +(hi[0] - lo[0]).toFixed(3), widthAcross: +(hi[1] - lo[1]).toFixed(3) };
    });
  }
  window.__sk = { boxState, copies, expectedDraw, counts, panel, topView, chairFacing, setPlacements: p => { placementsFull = p; return Object.keys(p).length; } };
  return true;
})()
