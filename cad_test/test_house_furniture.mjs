// Checks the furniture boxes of the Sukhumvit house page (2 Nov 2026) in headless Edge, as bank_test/test_bank.mjs does for
// the bank (the contract is furniture/README.md): one coloured box per piece of the interior designer's furniture, from
// cad_test/src/furniture_house.json (build_furniture.py), coloured by kind. 48 of the 76 are grey 'Other furniture': the
// drawing does not say what they are, and nothing on the page may claim it does.
//   the page carries the builder's kinds and pieces (the file next to it); the legend has a row per kind with its count,
//   colour, default height in a text box, the show and stops ticks, and the tick 'Keep doorways clear'; one box per piece
//   in its own floor's group, standing on the floor's own level (+0.90 / +4.80 m) and moving with it in Build settings;
//   the page's own ticks and floor buttons leave the boxes alone; the side panel at 1366 x 768 and 1920 x 1080;
//   a height typed into a kind's text box (real key events): its boxes are that tall, as a ray looking down finds them;
//   Walk stops at real boxes (short of the face, never inside, never through) and starts clear of them; the show and
//   stops ticks (real clicks) and a height under the knee ray let you through; Ghost flies through;
//   the doors and passages walked again with the boxes: with Keep doorways clear on (the default) every door can be walked
//   through and no passage is cut; with it off what the boxes block is measured and each is named by a box's approach list;
//   the colliders against the approach lists; the windows still stop you; walking at the nearest wall or box never takes
//   you through it; not trapped: Walk entered at the middle of a box, or a box switched on under you, never holds you;
//   the family list the page writes is cad_test/house_furniture_list.csv without its byte-order mark, byte for byte;
//   the label under the pointer in Orbit (kind, family, size, floor; an 'Other furniture' box names no other kind);
//   the build replay brings the boxes in last and the page puts back what you had; no page errors.
// The structure (doors, windows, passages, lintels, fins) is test_house_openings.mjs's: it runs on this page as it is,
// with the boxes shown.
// Usage (from the project folder): node cad_test/test_house_furniture.mjs [page file URL]
//   page: the argument, else HOUSE_URL, else cad_test/house_3d_preview.html. TEST_PORT (default 9419), TEST_PROFILE (the
//   browser profile), TEST_TMP (default %TEMP%\house-furniture-test) and TEST_OUT (screenshots; default TEST_TMP\out) keep it
//   apart from other runs; it stops at once if something already answers on the port (the shared launcher would attach to
//   that browser and finally close it). EDGE as in viewer-modes/cdp.mjs. Exit code 1 when a check fails.
import { mkdirSync, readFileSync, existsSync } from 'node:fs';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { tmpdir } from 'node:os';
import path from 'node:path';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const { launch, pageApi, sleep } = await import(pathToFileURL(path.join(HERE, '..', 'viewer-modes', 'cdp.mjs')).href);
const URL = process.argv[2] || process.env.HOUSE_URL || pathToFileURL(path.join(HERE, 'house_3d_preview.html')).href;
const MODEL = path.join(HERE, 'src', 'furniture_house.json'), LIST = path.join(HERE, 'house_furniture_list.csv');
const TMP = process.env.TEST_TMP || path.join(tmpdir(), 'house-furniture-test'), OUT = process.env.TEST_OUT || path.join(TMP, 'out');
mkdirSync(OUT, { recursive: true });
const PORT = Number(process.env.TEST_PORT || 9419);
let busy = true;
try { await fetch(`http://127.0.0.1:${PORT}/json/version`, { signal: AbortSignal.timeout(1500) }); } catch { busy = false; }
if (busy) {
  console.error(`Port ${PORT} already answers (another browser is using it). Close it or set TEST_PORT to a free port.`);
  process.exit(2);
}
const results = [];
const check = (name, ok, info) => { results.push(!!ok); console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${info !== undefined ? '   ' + JSON.stringify(info) : ''}`); };
const note = (name, info) => console.log(`      ${name}${info !== undefined ? ': ' + JSON.stringify(info) : ''}`);
const r2 = v => Math.round(v * 100) / 100;
const t0 = Date.now();
const { tab, close } = await launch({ port: PORT, profile: process.env.TEST_PROFILE || path.join(TMP, 'profile') });
console.log('page:', URL);
const P = pageApi(tab);
const errs = () => P.logs.filter(l => /exception|error/i.test(l) && !/favicon/i.test(l));
const errors = [];                                      // page errors of the pages already left (P.goto clears the log)
const flush = () => { errors.push(...errs()); P.logs.length = 0; };
const FLOORS = ['ground', 'upper'];
// the boxes that show (their own switch and their floor's), and the switch for all kinds at once
const boxesShown = `(() => { let n = 0; for (const f of Object.values(__host.FL)) f.group.traverse(o => { if (o.name.startsWith('furn:') && o.visible) n++; }); return n; })()`;
const setFurniture = on => P.evaluate(`(() => { const F = __host.furniture; F.kinds().forEach(k => F.setVisible(k.key, ${on})); })()`);

// Typing: real key events (the viewer sees them like any key), so a height typed into a text box is what a person's keys do.
const rawKey = (type, o) => tab.send('Input.dispatchKeyEvent', { type, ...o });
async function typeChars(text) {
  for (const ch of text) {
    const o = { key: ch, code: /\d/.test(ch) ? 'Digit' + ch : 'Key' + ch.toUpperCase(), windowsVirtualKeyCode: ch.toUpperCase().charCodeAt(0) };
    await rawKey('keyDown', { ...o, text: ch }); await rawKey('keyUp', o);
  }
  await sleep(60);
}
const pressKey = async (key, code, vk) => { await rawKey('rawKeyDown', { key, code, windowsVirtualKeyCode: vk }); await rawKey('keyUp', { key, code, windowsVirtualKeyCode: vk }); await sleep(80); };
const F = expr => P.evaluate(`(() => { const F = __host.furniture; return ${expr}; })()`);
const T = expr => P.evaluate(`(() => { const T = window.__t; return ${expr}; })()`);        // the read-outs in the page (pageHelpers)
const rowSel = (k, part) => `.fb-row[data-k="${k}"] .fb-${part}`;
const clickSel = async sel => { await P.evaluate(`document.querySelector(${JSON.stringify(sel)}).scrollIntoView({ block: 'center' })`); await sleep(60); await P.clickEl(sel); await sleep(80); };
// click into a height box (the number is selected), type, Enter: a typed height, with the keyboard handed back to the viewer
const typeHeight = async (k, mm) => { await clickSel(rowSel(k, 'h')); await typeChars(String(mm)); await pressKey('Enter', 'Enter', 13); };
const stopped = w => w.start && w.gap >= 0.1 && w.gap <= 0.5 && !w.inside && w.moved >= 0.1;       // short of the face (Walk stops at ~0.3 m), never inside, never through
const passed = w => w.start && w.moved >= w.metres - 0.01 && w.gap < -0.2;                          // right across it and out the other side
const walkPiece = (id, side, back, through, kind) => T(`T.walk(__host.furniture.pieces().find(p => p.id === ${JSON.stringify(id)}), ${side}, ${back}, ${through}, ${kind ? JSON.stringify(kind) : 'null'})`);

// Walking through the doors and passages of the floor you are on (as test_house_openings.mjs walks them): from in front of the
// line (0.9 m, or nearer when that spot is tight), straight through the middle for twice that far; the metres past the line
// (negative: stopped before it) or why there was no start. A window is walked at from each side with floor: you stop before it.
// why: also say which boxes stopped you or stood at the start spot.
const openingWalks = why => `(() => { const v = __viewer, s = v.state, keep = s.pos.clone(), F = s.floor.key, out = [];
      const floorAt = (d, k) => { s.pos.x = d.x + d.nx * k; s.pos.z = -(d.y + d.ny * k); return v.probe.onFloor(); };
      const cross = (d, sign, tries) => {
        const nx = d.nx * sign, ny = d.ny * sign, deg = Math.atan2(-nx, ny) * 180 / Math.PI;
        let res = 'no start';
        for (const back of [0.9, 0.7, 0.55, 0.45]) {
          s.pos.x = d.x - nx * back; s.pos.z = -(d.y - ny * back);
          if (!v.probe.onFloor()) { res = 'no floor'; continue; }
          if (v.probe.clearance() < 0.25) { res = 'tight'; if (${!!why}) tries.push({ back, near: __t.near(F, s.pos.x, s.pos.z, 0.3) }); continue; }
          v.probe.walk(deg, back * 2);
          const along = Math.round(((s.pos.x - d.x) * nx + (-s.pos.z - d.y) * ny) * 100) / 100;
          if (${!!why}) tries.push({ back, along, stoppedBy: __t.stoppedBy(F, s.pos.x, s.pos.z, deg) });
          return along;
        }
        return res;
      };
      for (const d of __host.openings[F]) {
        const r = { id: d.id, kind: d.glazed ? 'window' : d.kind === 'door' ? 'door' : 'passage', floorPos: floorAt(d, 0.9), floorNeg: floorAt(d, -0.9), fwdTries: [], backTries: [] };
        if (r.floorNeg) r.fwd = cross(d, 1, r.fwdTries);              // from the -n side through to the +n side
        if (r.floorPos) r.back = cross(d, -1, r.backTries);
        out.push(r);
      }
      s.pos.copy(keep); return out; })()`;
const num = x => typeof x === 'number';
const judge = r => {                                    // test_house_openings.mjs's verdict on a door or a passage
  if (r.floorPos && r.floorNeg) return num(r.fwd) && num(r.back) && r.fwd > 0.3 && r.back > 0.3 ? 'both ways' : 'blocked';
  if (r.floorPos || r.floorNeg) return [r.fwd, r.back].some(x => num(x) && x > -0.15) ? 'from the floor side' : 'blocked';
  return 'skipped';
};
const RANK = { blocked: 0, 'from the floor side': 1, 'both ways': 2 };
async function walkOpenings(why) {                      // both floors, in Walk
  const out = [];
  for (const key of FLOORS) { await P.evaluate(`__viewer.goToFloor(${JSON.stringify(key)})`); out.push(...await P.evaluate(openingWalks(why))); }
  return out.map(r => ({ ...r, result: r.kind === 'window' ? null : judge(r) }));
}
const piecesOf = ts => [...new Set(ts.flatMap(t => (t.near || t.stoppedBy || []).map(p => `${p.id} (${p.kind}, ${String(p.family).slice(0, 34)})`)))];

// In the page: what the furniture checks read out of it. Runs inside the page (its THREE comes from the page's import map).
// A "lane" is a walk straight at a face of a box (side 0 / 1: the ends along the long axis, 2 / 3: the long faces) from a spot
// back metres in front of it: free when there is floor all the way and Walk's own rays (knee and chest height, across the
// shoulders) meet nothing but that box.
async function pageHelpers() {
  const THREE = await import('three');
  const F = __host.furniture, v = __viewer, s = v.state, V3 = THREE.Vector3, RADIUS = 0.3, KNEE = 0.35, CHEST = 1.2;
  const ray = new THREE.Raycaster(); ray.firstHitOnly = true;
  const levelOf = key => __host.floors.find(f => f.key === key).level;      // the floor's level now (Build settings can move it)
  const frame = p => { const r = p.rot * Math.PI / 180; return { c: new V3(p.x, 0, -p.y), ax: new V3(Math.cos(r), 0, -Math.sin(r)), az: new V3(Math.sin(r), 0, Math.cos(r)) }; };
  const pieceOf = name => (name && name.startsWith('furn:') ? F.pieces().find(p => p.id === name.split(':')[2]) : null);
  const brief = p => ({ id: p.id, kind: p.kind, family: p.family });
  const spans = p => (p.z0 < KNEE - 0.02 && p.z1 > KNEE + 0.02) || (p.z0 < CHEST - 0.02 && p.z1 > CHEST + 0.02);        // Walk's rays can meet it
  const colliders = (floor, skipKind) => __host.FL[floor].colliders.filter(m => m.visible && !(skipKind && m.name.startsWith('furn:' + skipKind + ':')));
  function ahead(floor, x, z, dir, far, cols) {                      // the first thing each of Walk's rays meets
    const lv = levelOf(floor), side = new V3(-dir.z, 0, dir.x), out = [];
    for (const h of [KNEE, CHEST]) for (const k of [0, -0.25, 0.25, -0.5, 0.5, -0.75, 0.75, -0.95, 0.95]) {
      ray.set(new V3(x, lv + h, z).addScaledVector(side, k * RADIUS), dir); ray.far = far;
      const hit = ray.intersectObjects(cols, false)[0];
      if (hit) out.push({ h, k, d: hit.distance, name: hit.object.name });
    }
    return out;
  }
  const hasFloor = (floor, x, z) => { if (s.floor.key !== floor) v.goToFloor(floor); const keep = s.pos.clone(); s.pos.x = x; s.pos.z = z; const ok = v.probe.onFloor(); s.pos.copy(keep); return ok; };
  function lane(p, side, back, through, kind) {                      // through: right across the box (boxes of `kind` are hidden then, so they do not count)
    const { c, ax, az } = frame(p), n = [ax.clone(), ax.clone().negate(), az.clone(), az.clone().negate()][side], half = side < 2 ? p.w / 2 : p.d / 2;
    const start = c.clone().addScaledVector(n, half + back), dir = n.clone().negate(), metres = through ? back + 2 * half + 0.6 : back + 0.5;
    const target = F.meshOf(p.id), r = { id: p.id, side, back, half, metres, n: n.toArray(), start: [start.x, start.z], free: false, why: '' };
    for (let t = 0; t <= back + (through ? 2 * half + 0.6 : 0); t += 0.25) {
      if (!hasFloor(p.floor, start.x + dir.x * t, start.z + dir.z * t)) { r.why = 'no floor at ' + t.toFixed(2) + ' m'; return r; }
    }
    const cols = colliders(p.floor, kind).filter(m => !through || m !== target);
    const hits = ahead(p.floor, start.x, start.z, dir, (through ? metres : back + 0.4) + RADIUS, cols);
    if (through) { if (hits.length) { r.why = 'meets ' + hits[0].name + ' at ' + hits[0].d.toFixed(2) + ' m'; return r; } r.free = true; return r; }
    const mine = hits.filter(h => h.name === target.name), other = hits.filter(h => h.name !== target.name && h.d < back + 0.2);
    if (other.length) { r.why = 'meets ' + other[0].name + ' at ' + other[0].d.toFixed(2) + ' m'; return r; }
    const mid = mine.find(h => h.k === 0 && h.h === KNEE) || mine.find(h => h.k === 0 && h.h === CHEST);
    if (!mid || Math.abs(mid.d - back) > 0.02) { r.why = 'the box is not met straight ahead at ' + back + ' m'; return r; }
    r.free = true;
    return r;
  }
  function walk(p, side, back, through, kind) {                      // stand at the start of a lane, face the box, walk, and say where you ended up
    const L = lane(p, side, back, through, kind);
    if (!L.free) return { id: p.id, side, start: false, why: L.why };
    if (s.floor.key !== p.floor) v.goToFloor(p.floor);
    s.pos.x = L.start[0]; s.pos.z = L.start[1];
    const n = new V3(...L.n), { c, ax, az } = frame(p);
    s.yaw = Math.atan2(n.x, n.z); s.pitch = -0.1;                    // facing the box, as you would be
    const moved = v.probe.walk(Math.atan2(n.x, n.z) * 180 / Math.PI, L.metres);
    const rel = new V3(s.pos.x - c.x, 0, s.pos.z - c.z);
    return { id: p.id, side, start: true, back, metres: L.metres, moved, gap: rel.dot(n) - L.half, inside: Math.abs(rel.dot(ax)) < p.w / 2 && Math.abs(rel.dot(az)) < p.d / 2 };
  }
  function targets() {                                               // the boxes that stop you (shown, stopping, not in a doorway's approach) and that Walk's rays can meet, each with its first free face
    const out = [];
    for (const p of F.pieces()) {
      if (!p.blocking || !spans(p)) continue;
      let L = null, why = '';
      for (const back of [1.0, 0.8, 0.65, 0.5]) {
        for (const side of [2, 3, 0, 1]) { const t = lane(p, side, back, false); if (t.free) { L = t; break; } if (!why) why = t.why; }
        if (L) break;
      }
      out.push({ ...brief(p), floor: p.floor, kind: p.kind, side: L ? L.side : null, back: L ? L.back : null, why: L ? '' : why });
    }
    return out;
  }
  function crossable(kind, max) {                                    // pieces of a kind with a free approach and a free line right across them, both floors in turn
    const per = {};
    for (const p of F.pieces().filter(q => q.kind === kind && q.blocking)) {
      let pick = null;
      for (const back of [1.0, 0.8, 0.65]) {
        for (const side of [2, 3, 0, 1]) if (!pick && lane(p, side, back, false).free && lane(p, side, back, true, kind).free) pick = { id: p.id, floor: p.floor, side, back };
        if (pick) break;
      }
      if (pick) (per[p.floor] = per[p.floor] || []).push(pick);
    }
    const lists = Object.values(per), out = [];
    for (let i = 0; out.length < max && lists.some(l => l[i]); i++) lists.forEach(l => { if (l[i] && out.length < max) out.push(l[i]); });
    return out;
  }
  function near(floor, x, z, r) {                                    // the pieces that touch a spot (within r m of their footprint) and that Walk's rays can meet
    const out = [];
    for (const p of F.pieces()) {
      if (p.floor !== floor || !p.blocking || !((p.z0 < KNEE && p.z1 > KNEE) || (p.z0 < CHEST && p.z1 > CHEST))) continue;
      const { c, ax, az } = frame(p), rel = new V3(x - c.x, 0, z - c.z), d = Math.hypot(Math.max(Math.abs(rel.dot(ax)) - p.w / 2, 0), Math.max(Math.abs(rel.dot(az)) - p.d / 2, 0));
      if (d < r) out.push({ ...brief(p), d: Math.round(d * 100) / 100 });
    }
    return out.sort((a, b) => a.d - b.d);
  }
  function stoppedBy(floor, x, z, deg, far = 0.45) {                 // the pieces Walk's rays meet straight ahead of a spot: what stopped you
    const dir = new V3(-Math.sin(deg * Math.PI / 180), 0, -Math.cos(deg * Math.PI / 180)), seen = new Map();
    for (const h of ahead(floor, x, z, dir, far, colliders(floor))) { const p = pieceOf(h.name); if (p && !seen.has(p.id)) seen.set(p.id, { ...brief(p), d: Math.round(h.d * 100) / 100 }); }
    return [...seen.values()];
  }
  // Looking straight down from 2.5 m above the floor (the page's own read-out, on the floor's colliders): the height above the
  // floor of the first thing below, and its name; topSpots(kind): per piece, a plan spot where that is the piece's own top.
  function down(floor, x, y) {
    const hit = __host.cast(floor, [x, levelOf(floor) + 2.5, -y], [0, -1, 0], 2.5);
    return hit ? { top: Math.round((2.5 - hit.d) * 1000) / 1000, name: hit.name } : null;
  }
  function topSpots(kind) {
    return F.pieces().filter(p => p.kind === kind).map(p => {
      const r = p.rot * Math.PI / 180, ax = [Math.cos(r), Math.sin(r)], az = [-Math.sin(r), Math.cos(r)], name = F.meshOf(p.id).name;
      const spot = [[0, 0], [p.w / 4, 0], [-p.w / 4, 0], [0, p.d / 4], [0, -p.d / 4]].map(([a, b]) => [p.x + ax[0] * a + az[0] * b, p.y + ax[1] * a + az[1] * b])
        .find(([x, y]) => (down(p.floor, x, y) || {}).name === name);
      return { id: p.id, floor: p.floor, spot: spot || null };
    });
  }
  function hoverSpots(floor, kinds, max = 99) {                      // per kind (or 'id:<id>') asked for, the biggest box the Orbit camera sees (nothing in front of its top), as a pointer position
    const cam = __host.camera, out = [], want = new THREE.Vector2();
    const showing = o => { for (let n = o; n; n = n.parent) if (!n.visible) return false; return true; };
    const hides = Object.values(__host.FL).flatMap(f => f.colliders.concat(f.walkables)).filter(m => showing(m) && !m.name.startsWith('furn:') && !m.material.transparent);
    const boxes = F.pieces().map(b => F.meshOf(b.id)).filter(showing);
    for (const kind of kinds) {
      if (out.length >= max) break;
      const mine = F.pieces().filter(p => p.floor === floor && p.visible && (kind.startsWith('id:') ? p.id === kind.slice(3) : p.kind === kind)).sort((a, b) => b.w * b.d - a.w * a.d);
      for (const p of mine) {
        const m = F.meshOf(p.id), q = new V3(p.x, levelOf(floor) + p.z1, -p.y).project(cam);
        const x = (q.x + 1) / 2 * innerWidth, y = (1 - q.y) / 2 * innerHeight;
        if (q.z > 1 || x < 400 || x > innerWidth - 20 || y < 50 || y > innerHeight - 70) continue;
        ray.setFromCamera(want.set(q.x, q.y), cam); ray.far = Infinity;
        const hit = ray.intersectObjects(hides.concat(boxes), false)[0];
        if (hit && hit.object === m) { out.push({ ...brief(p), floor, approach: p.approach, x, y, size: `${p.w.toFixed(2)} × ${p.d.toFixed(2)} × ${(p.z1 - p.z0).toFixed(2)} m` }); break; }
      }
    }
    return out;
  }
  function along(id, side) {                                         // where you are against a face of a box: rel = metres from its centre along the face's outward normal
    const p = F.pieces().find(q => q.id === id), { c, ax, az } = frame(p), n = [ax.clone(), ax.clone().negate(), az.clone(), az.clone().negate()][side];
    return { rel: (s.pos.x - c.x) * n.x + (s.pos.z - c.z) * n.z, half: side < 2 ? p.w / 2 : p.d / 2, y: s.pos.y - levelOf(p.floor), z0: p.z0, z1: p.z1 };
  }
  function walkTo(p, side, back, metres) {                          // from `back` m in front of a face of the box, facing it: walk `metres` m (the box need not be a collider: it may stand in a doorway's approach)
    const { c, ax, az } = frame(p), n = [ax.clone(), ax.clone().negate(), az.clone(), az.clone().negate()][side], half = side < 2 ? p.w / 2 : p.d / 2, start = c.clone().addScaledVector(n, half + back);
    if (s.floor.key !== p.floor) v.goToFloor(p.floor);
    s.pos.x = start.x; s.pos.z = start.z; s.yaw = Math.atan2(n.x, n.z); s.pitch = -0.1;
    const moved = v.probe.walk(Math.atan2(n.x, n.z) * 180 / Math.PI, metres), rel = new V3(s.pos.x - c.x, 0, s.pos.z - c.z);
    return { id: p.id, side, back, metres, moved, gap: rel.dot(n) - half };
  }
  // The nearest thing Walk's middle rays (knee and chest) meet in a direction, and whether anything stands between two spots at
  // knee or chest height (a wall or a box walked through).
  function nearest(deg, far = 30) {
    const dir = new V3(-Math.sin(deg * Math.PI / 180), 0, -Math.cos(deg * Math.PI / 180)), cols = colliders(s.floor.key);
    let d = far;
    for (const h of [KNEE, CHEST]) { ray.set(new V3(s.pos.x, levelOf(s.floor.key) + h, s.pos.z), dir); ray.far = far; const hit = ray.intersectObjects(cols, false)[0]; if (hit) d = Math.min(d, hit.distance); }
    return d;
  }
  function between(x0, z0, x1, z1) {
    const d = new V3(x1 - x0, 0, z1 - z0), len = d.length(), cols = colliders(s.floor.key);
    if (len < 1e-6) return false;
    d.divideScalar(len);
    return [KNEE, CHEST].some(h => { ray.set(new V3(x0, levelOf(s.floor.key) + h, z0), d); ray.far = len; return ray.intersectObjects(cols, false).length > 0; });
  }
  // Standing inside a box: Walk entered at the middle of a box (the double-click path: Orbit, then Walk at the box), or the player put there.
  // holding(): the boxes that stop you, that Walk's rays can meet and that hold the player's centre. leave(): the furthest you get walking 1.5 m in 8
  // directions. only(ids, fn): fn with no furniture in the way but those boxes (the walls stay). verdict(): A = leaves (or is in no box); B = does not,
  // but would with only the boxes that hold the player in the way (a pocket of other boxes: information); C = a box holds the player by itself, by
  // its own faces - what the single-sided faces rule out.
  const holds = (q, x, z) => { const { c, ax, az } = frame(q), dx = x - c.x, dz = z - c.z; return Math.abs(dx * ax.x + dz * ax.z) < q.w / 2 && Math.abs(dx * az.x + dz * az.z) < q.d / 2; };
  const holding = () => F.pieces().filter(q => q.blocking && q.floor === s.floor.key && spans(q) && holds(q, s.pos.x, s.pos.z)).map(q => q.id);
  function leave() {
    const x0 = s.pos.x, z0 = s.pos.z; let best = 0;
    for (let deg = 0; deg < 360; deg += 45) { s.pos.x = x0; s.pos.z = z0; best = Math.max(best, v.probe.walk(deg, 1.5)); }
    s.pos.x = x0; s.pos.z = z0;
    return best;
  }
  function only(ids, fn) {
    const col = __host.FL[s.floor.key].colliders, keep = col.slice();
    col.length = 0; col.push(...keep.filter(m => !m.name.startsWith('furn:') || ids.includes(m.userData.id)));
    try { return fn(); } finally { col.length = 0; col.push(...keep); }
  }
  function verdict() {
    const inside = holding();
    if (!inside.length) return { class: 'A', inside };
    const best = leave();
    if (best >= 1.0) return { class: 'A', inside, best };
    const base = only([], leave), alone = only(inside, leave);
    return { class: alone + 0.3 < Math.min(1.0, base) ? 'C' : 'B', inside, best, alone, base };
  }
  function spawn(id) {
    const p = F.pieces().find(q => q.id === id), f = __host.floors.find(x => x.key === p.floor);
    v.setMode('orbit'); v.setMode('walk', { floor: f, point: new V3(p.x, 0, -p.y) });
    return p;
  }
  function standIn(id) { const p = spawn(id); s.pos.x = p.x; s.pos.z = -p.y; return p; }       // exactly at the middle, wherever Walk found room
  window.__t = { THREE, frame, lane, walk, walkTo, targets, crossable, near, stoppedBy, down, topSpots, hoverSpots, along, levelOf, nearest, between, holding, leave, only, verdict, spawn, standIn };
  return true;
}
// Walk at the nearest wall or box from 40 random spots of the floor you are on (clear of both): never through it, never inside it.
const wallWalks = `(() => { const v = __viewer, s = v.state, keep = s.pos.clone(); let seed = 7, n = 0, through = 0, stuck = 0, inBox = 0, tries = 0;
      const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
      const b = new __t.THREE.Box3().setFromObject(s.floor.group);
      while (n < 40 && tries++ < 8000) {
        s.pos.x = b.min.x + rnd() * (b.max.x - b.min.x); s.pos.z = b.min.z + rnd() * (b.max.z - b.min.z);
        if (!v.probe.onFloor() || v.probe.clearance() < 0.6 || __t.holding().length) continue;
        const d = [...Array(72)].map((_, i) => __t.nearest(i * 5)); let k = 0; d.forEach((x, j) => { if (x < d[k]) k = j; });
        if (d[k] > 2.5) continue;
        const a = s.pos.clone(); v.probe.walk(k * 5, d[k] + 1);
        n++; if (__t.between(a.x, a.z, s.pos.x, s.pos.z)) through++; if (v.probe.clearance() < 0.15) stuck++; if (__t.holding().length) inBox++;
      }
      s.pos.copy(keep); return { tried: n, wentThrough: through, endedInsideWall: stuck, endedInABox: inBox }; })()`;

try {
  const file = JSON.parse(readFileSync(MODEL, 'utf-8'));
  const nBoxes = file.furniture.length, perFloor = Object.fromEntries(FLOORS.map(k => [k, file.furniture.filter(p => p.floor === k).length]));
  const inApproach = file.furniture.filter(p => (p.approach || []).length);       // the pieces the builder put in the approach of a door or a passage
  const blocksOf = Object.fromEntries(file.furnitureKinds.map(k => [k.key, k.blocks !== false]));

  // ------------------------------------------------------------------ the build replay brings the boxes in last
  await P.goto(URL + '?build=0&nodownload=1');
  // the typed heights (and the doorways tick) of an earlier run are kept in the browser profile: forget them, this run starts from the model's
  await P.evaluate(`(() => { try { Object.keys(localStorage).filter(k => k.startsWith('walkthrough-furniture')).forEach(k => localStorage.removeItem(k)); } catch (e) { /* blocked */ } })()`);
  if (!(await P.evaluate('!!(window.__host && __host.furniture)'))) throw new Error('this page has no furniture boxes (window.__host.furniture)');
  flush();
  await P.goto(URL + '?speed=quick&build=play&nodownload=1');
  await sleep(2500);
  const early = await P.evaluate(`({ T: __build.state.T, phase: __build.phase, boxes: ${boxesShown} })`);
  await P.shot(path.join(OUT, 'house_furniture_replay.png'));
  for (let i = 0; i < 100 && (await P.evaluate('__build.phase')) !== 'done'; i++) await sleep(250);
  const end = await P.evaluate(`(() => { const F = __host.furniture, ms = F.pieces().map(p => F.meshOf(p.id));
    return { phase: __build.phase, n: ms.length, shown: ${boxesShown}, opaque: ms.every(m => m.material.opacity === 1 && !m.material.transparent && m.children.every(c => c.material.opacity === 1 && !c.material.transparent)),
      colliders: Object.values(__host.FL).reduce((n, f) => n + f.colliders.filter(m => m.name.startsWith('furn:')).length, 0),
      caption: __build.steps.find(s => s.key === 'finish').caption(__build.state.settings) }; })()`);
  const blockingN = file.furniture.filter(p => blocksOf[p.kind] && !(p.approach || []).length).length;     // the boxes that stop you: not those in a doorway's approach
  check(`the build replay brings in the ${end.n} furniture boxes last: none while the walls are still to rise (replay at ${Math.round(early.T * 100)} %), all of them, opaque, when it is done, the ${blockingN} that stop you (not the ${inApproach.length} in a doorway's approach) are colliders, and the last caption says so`,
    early.phase === 'play' && early.T > 0.02 && early.T < 0.85 && early.boxes === 0 && end.phase === 'done' && end.n === nBoxes && end.shown === nBoxes && end.opaque && end.colliders === blockingN
    && end.caption.includes(`and last the furniture: ${nBoxes} coloured boxes, one per piece, ${file.furnitureKinds.length} kinds`), { atReplay: early, end });
  flush();

  await P.goto(URL + '?build=0&nodownload=1');
  await P.evaluate(`(${pageHelpers.toString()})()`);
  // the Orbit view the page opens with, to come back to for the label and the pictures (the Walk starts below move the Orbit target)
  const home = await P.evaluate(`({ p: __host.camera.position.toArray(), t: __host.controls.target.toArray() })`);
  const goHome = () => P.evaluate(`(() => { __viewer.setMode('orbit'); __host.camera.position.fromArray(${JSON.stringify(home.p)}); __host.controls.target.fromArray(${JSON.stringify(home.t)}); __host.controls.update(); })()`);

  // ------------------------------------------------------------------ the page carries the builder's kinds and pieces
  const data = await P.evaluate(`(() => { const F = __host.furniture; return { kinds: F.kinds(), pieces: F.pieces() }; })()`);
  const KF = ['key', 'label', 'colour', 'height', 'count', 'blocks'], PF = ['floor', 'kind', 'family', 'block', 'layer', 'handle', 'x', 'y', 'w', 'd', 'rot', 'on', 'n', 'note'];
  const kindsBad = file.furnitureKinds.map((k, i) => [k, data.kinds[i]]).filter(([k, q]) => !q || KF.some(f => f === 'blocks' ? q.blocks !== (k.blocks !== false) : q[f] !== k[f])).map(([k]) => k.key);
  const piecesBad = file.furniture.filter(p => { const q = data.pieces.find(x => x.id === p.id); return !q || PF.some(f => q[f] !== p[f]) || q.approach.join() !== (p.approach || []).join(); }).map(p => p.id);
  check(`the page carries furniture_house.json: its ${file.furnitureKinds.length} kinds in table order (key, label, colour, height, count, stops) and its ${nBoxes} pieces (place, size, turn, family, block, layer, handle, approach, note)`,
    data.kinds.length === file.furnitureKinds.length && data.pieces.length === nBoxes && !kindsBad.length && !piecesBad.length, kindsBad.length || piecesBad.length ? { kindsBad, piecesBad: piecesBad.slice(0, 6) } : undefined);

  // ------------------------------------------------------------------ the legend, and what the page says about the grey boxes
  const legend = await P.evaluate(`(() => ({ title: document.querySelector('.fb-title span').textContent, master: !!document.querySelector('.fb-all'),
    keep: (b => b && { checked: b.checked, text: b.closest('label').textContent.trim(), n: document.querySelectorAll('.fb-keep').length })(document.querySelector('.fb-keep')),
    buttons: [...document.querySelectorAll('.fb-btns button')].map(b => b.innerText),
    rows: [...document.querySelectorAll('.fb-row[data-k]')].map(r => ({ k: r.dataset.k, label: r.querySelector('.fb-lab').innerText, sw: getComputedStyle(r.querySelector('.fb-sw')).backgroundColor,
      h: r.querySelector('.fb-h').value, show: r.querySelector('.fb-show').checked, blk: r.querySelector('.fb-blk').checked })),
    intro: document.querySelector('#panel p').textContent }))()`);
  const rgb = hex => `rgb(${[1, 3, 5].map(i => parseInt(hex.slice(i, i + 2), 16)).join(', ')})`;
  const legendBad = [];
  file.furnitureKinds.forEach((k, i) => {
    const r = legend.rows[i];
    if (!r || r.k !== k.key || r.label !== `${k.label} (${k.count})` || r.sw !== rgb(k.colour) || r.h !== String(k.height) || !r.show || r.blk !== (k.blocks !== false)) legendBad.push([k.key, r]);
  });
  check(`the furniture legend: one row per kind (${file.furnitureKinds.length}) in table order, with its count (${nBoxes} boxes in all), its colour, the default height in mm in a text box, and the show and stops ticks; above them the tick "Keep doorways clear", ticked`,
    legend.title === 'Furniture boxes' && legend.master && legend.rows.length === file.furnitureKinds.length && !legendBad.length && legend.buttons.join('|') === 'Reset heights|Save list (CSV)'
    && legend.keep && legend.keep.checked && legend.keep.text === 'Keep doorways clear' && legend.keep.n === 1, legendBad.length ? legendBad : legend.rows.map(r => `${r.label} ${r.h}`));
  const other = file.furnitureKinds.find(k => k.key === 'other'), named = file.furnitureKinds.filter(k => k.key !== 'other').map(k => k.label);
  const otherRow = legend.rows.find(r => r.k === 'other');
  check(`the grey boxes are called what they are: the legend row "${otherRow && otherRow.label}" in grey, and the panel says that the drawing does not say what ${other ? other.count : 0} of the ${nBoxes} boxes are`,
    !!other && otherRow && otherRow.label === `Other furniture (${other.count})` && otherRow.sw === rgb('#6b6b6b')
    && legend.intro.includes(`Furniture: ${nBoxes} boxes, one per piece, coloured by kind (${file.furnitureKinds.length} kinds); ${other.count} are grey because the drawing does not say what they are.`),
    { row: otherRow, intro: legend.intro.slice(legend.intro.indexOf('Furniture:')) });

  // ------------------------------------------------------------------ a box per piece, in its floor's group, on the floor's own level
  const made = await P.evaluate(`(() => { const FL = __host.FL, F = __host.furniture, pieces = Object.fromEntries(F.pieces().map(p => [p.id, p])), bad = [], names = new Set(), per = {}; let n = 0;
    for (const [key, f] of Object.entries(FL)) f.group.traverse(o => {
      if (!o.name.startsWith('furn:')) return;
      n++; names.add(o.name); per[key] = (per[key] || 0) + 1;
      const [, kind, id] = o.name.split(':'), p = pieces[id];
      if (!p || p.kind !== kind || p.floor !== key || o.parent !== f.group || F.meshOf(id) !== o) bad.push(o.name);
    });
    return { n, distinct: names.size, per, bad: bad.slice(0, 5), nBad: bad.length }; })()`);
  check(`the scene holds ${nBoxes} furniture boxes (${FLOORS.map(k => `${perFloor[k]} on ${k}`).join(', ')}), each a child of its own floor's group and named furn:<kind>:<id>`,
    made.n === nBoxes && made.distinct === nBoxes && made.nBad === 0 && FLOORS.every(k => made.per[k] === perFloor[k]), made.nBad ? made.bad : { perFloor: made.per });
  // where the boxes stand, in the world: the bottom on the floor's level (no piece stands on another here), the top at the kind's height above it;
  // with the upper floor moved to +5.00 m in Build settings the upper boxes go with it, and back
  const stand = () => P.evaluate(`(() => { const F = __host.furniture, out = {};
    for (const g of Object.values(__host.FL)) g.group.updateMatrixWorld(true);
    for (const p of F.pieces()) {
      const b = new __t.THREE.Box3().setFromObject(F.meshOf(p.id)), o = out[p.floor] = out[p.floor] || { bottoms: new Set(), tops: 0, on: 0 };
      o.bottoms.add(Math.round(b.min.y * 1000) / 1000); if (Math.abs(b.max.y - b.min.y - (p.z1 - p.z0)) > 0.001) o.tops++; if (p.on || p.z0 !== 0) o.on++;
    }
    return Object.fromEntries(Object.entries(out).map(([k, o]) => [k, { bottoms: [...o.bottoms], wrongHeight: o.tops, standingOnSomething: o.on }])); })()`);
  const setLevel = async (key, v) => {
    await P.clickEl('#br-open'); await sleep(300);
    await P.evaluate(`(() => { const e = document.querySelector('#br-card input[data-k=${key}][data-p=level]'); e.value = '${v}'; e.dispatchEvent(new Event('change')); })()`);
    await P.clickEl('#br-skip0'); await sleep(400);
  };
  const atLevels = await stand();
  await setLevel('upper', '5.00');
  const at500 = await stand();
  await F(`F.setHeight('bed', 600)`);                                  // a height typed while the floor is moved: the boxes are placed again, on the same level
  const typedAt500 = await stand();
  await F(`F.reset()`);
  await setLevel('upper', '4.80');
  const back = await stand();
  const on = (r, k, lv) => r[k] && r[k].bottoms.length === 1 && Math.abs(r[k].bottoms[0] - lv) < 0.0015 && r[k].wrongHeight === 0 && r[k].standingOnSomething === 0;
  check('the boxes stand on their floor\'s own level (ground +0.90 m, upper +4.80 m; no piece stands on another), as tall as their kind; Build settings moving the upper floor to +5.00 m take its boxes with it (also when a height is typed there), and back',
    on(atLevels, 'ground', 0.9) && on(atLevels, 'upper', 4.8) && on(at500, 'ground', 0.9) && on(at500, 'upper', 5.0) && on(typedAt500, 'upper', 5.0) && on(back, 'upper', 4.8), { atLevels, at500, typedAt500, back });

  // ------------------------------------------------------------------ the page's own controls leave the boxes alone
  const own = await P.evaluate(`(async () => {
    const F = __host.furniture, ms = F.pieces().map(p => F.meshOf(p.id)), showing = m => { for (let n = m; n; n = n.parent) if (!n.visible) return false; return true; };
    const count = () => ms.filter(showing).length, click = id => { document.getElementById(id).click(); }, out = {};
    out.start = count();
    for (const id of ['plates', 'glass', 'single']) click(id);
    out.ticksOff = count();
    for (const id of ['plates', 'glass', 'single']) click(id);
    out.ticksOn = count();
    F.setVisible('sanitary', false); click('plates'); click('glass'); click('plates'); click('glass');
    out.sanitaryHidden = count();
    F.setVisible('sanitary', true);
    const perFloor = {};
    for (const key of ['ground', 'upper', 'both']) { document.querySelector('#floors [data-f=' + key + ']').click(); perFloor[key] = ms.filter(showing).length; }
    out.perFloor = perFloor;
    const panel = document.getElementById('panel'), last = panel.lastElementChild, lg = panel.querySelector('.legend');
    out.panel = { fbLast: last.matches('.fb-block') || !!last.querySelector(':scope > .fb-block'), buildBefore: !!(document.getElementById('br-again').compareDocumentPosition(last) & Node.DOCUMENT_POSITION_FOLLOWING),
      legendSwatches: lg.querySelectorAll('span').length, legendHasFurniture: !!lg.querySelector('[class^=fb-]') || /furniture/i.test(lg.textContent),
      legendText: lg.textContent.startsWith('Walls and lintels') && lg.textContent.endsWith('Floor plate (approximate outline)') };
    return out; })()`);
  const nSan = file.furniture.filter(p => p.kind === 'sanitary').length;
  check(`the page's own controls leave the boxes alone: the Floor plates / Glass / Single-line ticks (and a hidden kind stays hidden through them), the floor buttons show ${FLOORS.map(k => `${perFloor[k]} on ${k}`).join(' / ')}, the legend is as it was and the furniture list is last in the panel`,
    own.start === nBoxes && own.ticksOff === nBoxes && own.ticksOn === nBoxes && own.sanitaryHidden === nBoxes - nSan
    && FLOORS.every(k => own.perFloor[k] === perFloor[k]) && own.perFloor.both === nBoxes && own.panel.fbLast && own.panel.buildBefore && !own.panel.legendHasFurniture
    && own.panel.legendSwatches >= 4 && own.panel.legendText, own);

  // ------------------------------------------------------------------ the side panel at the two screens of a PC / laptop
  for (const [w, h] of [[1366, 768], [1920, 1080]]) {
    await tab.send('Emulation.setDeviceMetricsOverride', { width: w, height: h, deviceScaleFactor: 1, mobile: false });
    await sleep(600);
    const m = await P.evaluate(`(() => { const p = document.getElementById('panel'), r = p.getBoundingClientRect(), cs = getComputedStyle(p);
      const rows = [...document.querySelectorAll('.fb-row[data-k]')], lab = [...document.querySelectorAll('.fb-lab')], inP = e => { const b = e.getBoundingClientRect(), q = p.getBoundingClientRect(); return b.top >= q.top - 0.5 && b.bottom <= q.bottom + 0.5 && b.left >= q.left - 0.5 && b.right <= q.right + 0.5; };
      const out = { vw: innerWidth, vh: innerHeight, panel: [Math.round(r.left), Math.round(r.top), Math.round(r.right), Math.round(r.bottom)], onScreen: r.top >= 0 && r.left >= 0 && r.bottom <= innerHeight && r.right <= innerWidth,
        scrolls: p.scrollHeight > p.clientHeight + 1, overflowY: cs.overflowY, content: p.scrollHeight, shown: p.clientHeight,
        hintGap: Math.round((document.getElementById('hint').getBoundingClientRect().top - r.bottom) * 10) / 10 };      // the panel's bottom edge above the hint line
      p.scrollTop = 0; out.titleVisible = inP(p.querySelector('h1'));
      p.scrollTop = p.scrollHeight; out.lastRowReachable = inP(rows[rows.length - 1]) && inP(document.querySelector('.fb-save')) && inP(document.querySelector('.fb-reset'));
      p.querySelector('.fb-block').scrollIntoView({ block: 'start' });
      out.cut = lab.filter(e => { const t = document.createRange(); t.selectNodeContents(e); return t.getBoundingClientRect().width > e.getBoundingClientRect().width + 0.01; }).map(e => e.textContent);       // the text is wider than its box, even by a fraction of a pixel
      out.panelW = Math.round(r.width);
      out.rowH = Math.round(Math.min(...rows.map(e => e.getBoundingClientRect().height))); out.fontPx = Math.min(...lab.map(e => parseFloat(getComputedStyle(e).fontSize)));
      out.boxesIn = rows.every(e => inP(e.querySelector('.fb-h')) && inP(e.querySelector('.fb-blk')) && inP(e.querySelector('.fb-show')));
      return out; })()`);
    await sleep(250);
    await P.shot(path.join(OUT, `house_furniture_panel_${w}x${h}.png`));
    await P.evaluate(`document.getElementById('panel').scrollTop = 0`); await sleep(150);
    await P.shot(path.join(OUT, `house_furniture_panel_${w}x${h}_top.png`));
    check(`the side panel at ${w} x ${h}: on the screen, ${m.scrolls ? 'it scrolls' : 'it fits'} (${m.content} px of content in ${m.shown}), the title and the last row with the Reset / Save buttons can be reached, ${legend.rows.length} rows at least ${m.rowH} px high and ${m.fontPx} px type, no label cut off, every height box and tick inside it, the bottom edge ${m.hintGap} px above the hint line`,
      m.onScreen && (!m.scrolls || /auto|scroll/.test(m.overflowY)) && m.titleVisible && m.lastRowReachable && m.cut.length === 0 && m.rowH >= 22 && m.fontPx >= 12 && m.boxesIn && m.hintGap >= 4, m);
  }
  const hintGaps = [];
  for (const [w, h] of [[1366, 640], [1366, 700], [1280, 800], [1600, 900], [1920, 1080]]) {
    await tab.send('Emulation.setDeviceMetricsOverride', { width: w, height: h, deviceScaleFactor: 1, mobile: false });
    await sleep(350);
    hintGaps.push([`${w}x${h}`, await P.evaluate(`(() => { const r = document.getElementById('panel').getBoundingClientRect(); return Math.round((document.getElementById('hint').getBoundingClientRect().top - r.bottom) * 10) / 10; })()`)]);
  }
  check(`the side panel's bottom edge stays above the hint line at every window height from 640 to 1080 px (${hintGaps.map(([s, g]) => `${s}: ${g} px`).join(', ')})`, hintGaps.every(([, g]) => g >= 4), hintGaps);
  await tab.send('Emulation.clearDeviceMetricsOverride'); await sleep(500);
  await P.evaluate(`document.getElementById('panel').scrollTop = 0`);

  // ------------------------------------------------------------------ typing a height: 2100 for the grey boxes (wardrobes are among them), then Reset
  // The boxes' tops as the page's own read-out finds them looking down from 2.5 m (on the colliders: the boxes in a doorway's approach are none while the
  // doorways are kept clear), and every box of the kind by its mesh: 2.10 m above its floor; the other kinds stay as they were; Reset brings it all back.
  const spots = (await T(`T.topSpots('other')`)).filter(t => t.spot), otherTop = other.height / 1000;
  const readings = () => P.evaluate(`(() => { const F = __host.furniture;
    for (const g of Object.values(__host.FL)) g.group.updateMatrixWorld(true);
    const lv = k => __t.levelOf(k), top = p => { const b = new __t.THREE.Box3().setFromObject(F.meshOf(p.id)); return Math.round((b.max.y - lv(p.floor)) * 1000) / 1000; };
    return { down: ${JSON.stringify(spots)}.map(t => { const d = __t.down(t.floor, t.spot[0], t.spot[1]); return [t.id, d && d.top]; }),
      tops: [...new Set(F.pieces().filter(p => p.kind === 'other').map(top))], others: F.pieces().filter(p => p.kind !== 'other').map(p => [p.id, top(p)]),
      box: document.querySelector('.fb-row[data-k="other"] .fb-h').value, edited: document.querySelectorAll('.fb-h.fb-edited').length,
      stored: (() => { try { return Object.keys(localStorage).filter(k => k.startsWith('walkthrough-furniture')).length; } catch (e) { return 'blocked'; } })() }; })()`);
  const before = await readings();
  await typeHeight('other', 2100);
  const at2100 = await readings();
  await P.shot(path.join(OUT, 'house_furniture_other_2100.png'));
  await clickSel('.fb-reset');
  const reset = await readings();
  const near = (a, b, tol = 0.006) => Math.abs(a - b) <= tol;
  check(`typing 2100 into the Other furniture height box: ${spots.length} of the ${other.count} grey boxes have their top at 2.10 m by the page's own look down (${otherTop.toFixed(2)} m before; the other ${other.count - spots.length} stand in a doorway's approach, no colliders), all ${other.count} by their mesh, the other kinds stay put; Reset brings it all back`,
    spots.length >= other.count - inApproach.filter(p => p.kind === 'other').length && before.down.every(([, z]) => near(z, otherTop)) && at2100.down.every(([, z]) => near(z, 2.1))
    && at2100.tops.length === 1 && near(at2100.tops[0], 2.1, 0.001) && at2100.box === '2100' && at2100.edited === 1 && at2100.stored === 1 && JSON.stringify(at2100.others) === JSON.stringify(before.others)
    && reset.down.every(([, z]) => near(z, otherTop)) && reset.tops.length === 1 && near(reset.tops[0], otherTop, 0.001) && reset.box === String(other.height) && reset.edited === 0 && reset.stored === 0,
    { spots: spots.length, downBefore: before.down.slice(0, 3).map(u => u[1]), downAt2100: at2100.down.slice(0, 3).map(u => u[1]), meshTops: at2100.tops, reset: { tops: reset.tops, box: reset.box, edited: reset.edited, stored: reset.stored } });

  // ------------------------------------------------------------------ the doors, passages and windows without the boxes (the structure, for the comparisons below)
  await P.press('Digit2');
  await setFurniture(false);
  const bare = await walkOpenings(false);
  await setFurniture(true);

  // Walk starts clear of the boxes wherever the Orbit view was looking: from 15 spots over each floor the start is on that floor, has 0.5 m of room
  // around it (the boxes count) and no box holds the player (the faces are single-sided: the start may be inside a box, and the player walks out of it)
  await P.press('Digit1');
  const starts = await P.evaluate(`(() => { const v = __viewer, s = v.state, out = [];
    let seed = 11; const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
    for (const key of ['ground', 'upper']) {
      v.setMode('orbit'); document.querySelector('#floors [data-f=' + key + ']').click();
      const b = new __t.THREE.Box3().setFromObject(__host.FL[key].group);
      for (let i = 0; i < 15; i++) {
        v.setMode('orbit'); __host.controls.target.set(b.min.x + rnd() * (b.max.x - b.min.x), 1, b.min.z + rnd() * (b.max.z - b.min.z));
        v.setMode('walk');
        const vd = __t.verdict();
        out.push({ want: key, floor: s.floor.key, clearance: Math.min(99, v.probe.clearance()), onFloor: v.probe.onFloor(), inBox: vd.inside, class: vd.class, best: vd.best });
      }
    }
    v.setMode('orbit'); document.querySelector('#floors [data-f=both]').click();
    return out; })()`);
  const badStart = starts.filter(r => r.floor !== r.want || !r.onFloor || r.clearance < 0.5 || r.class !== 'A');
  check(`Walk starts clear of the boxes wherever the Orbit view looks: from ${starts.length} spots over the two floors the start is on its own floor's plate, has at least 0.5 m of room around it and is not held by a box (${starts.filter(r => r.inBox.length).length} start inside a box and walk out of it)`,
    starts.length === 30 && !badStart.length, badStart.length ? badStart : { leastRoom: r2(Math.min(...starts.map(r => r.clearance))), insideABox: starts.filter(r => r.inBox.length).map(r => `${r.inBox.join('+')} (${r2(r.best)} m)`) });

  // ------------------------------------------------------------------ Walk stops at real boxes
  // Every shown box that stops you and that Walk's rays can meet (knee 0.35 m or chest 1.2 m), approached on a free line straight at one face from 1 m
  // (nearer where something else stands in the way: 0.8, 0.65, 0.5 m): you stop short of the face, never inside, never through
  await P.press('Digit2'); await P.evaluate(`__viewer.goToFloor('ground')`);
  const tg = await T(`T.targets()`);
  const walkable = tg.filter(t => t.side !== null);
  const walks = [];
  for (const t of walkable) walks.push({ ...(await walkPiece(t.id, t.side, t.back, false)), kind: t.kind });
  const byKind = {};
  for (const t of tg) { const b = byKind[t.kind] = byKind[t.kind] || { spans: 0, tested: 0, from1m: 0 }; b.spans++; if (t.side !== null) { b.tested++; if (t.back === 1) b.from1m++; } }
  const covered = Object.keys(byKind).filter(k => byKind[k].tested > 0), noLine = Object.keys(byKind).filter(k => byKind[k].tested === 0);
  const gaps = walks.filter(w => w.start).map(w => w.gap), notStopped = walks.filter(w => !stopped(w));
  check(`Walk stops at real boxes: ${walks.length} of the ${tg.length} boxes that stop you and that Walk's rays can meet had a free line (${walks.filter(w => w.back === 1).length} from 1 m, the rest from 0.8 - 0.5 m), covering ${covered.length} of ${file.furnitureKinds.length} kinds; each stops short of its face (gap ${gaps.length ? r2(Math.min(...gaps)) : '-'} - ${gaps.length ? r2(Math.max(...gaps)) : '-'} m), never inside, never through`,
    tg.length === blockingN && walks.length >= tg.length / 2 && covered.length >= file.furnitureKinds.length - 2 && notStopped.length === 0,
    notStopped.length ? notStopped : { perKind: Object.fromEntries(Object.entries(byKind).map(([k, b]) => [k, `${b.tested}/${b.spans}`])) });
  note('boxes with no free line (information)', tg.filter(t => t.side === null).map(t => `${t.id}: ${t.why.replace(/ at [0-9.]+ m/, '')}`));
  const shot = tg.find(t => t.kind === 'counter' && t.side !== null) || walkable[0];
  if (shot) { await walkPiece(shot.id, shot.side, shot.back, false); await sleep(700); }
  await P.shot(path.join(OUT, 'house_furniture_walk_stop.png'));

  // the boxes in a doorway's approach in that walk: with the tick on they are no targets (the walk above left them out) and the same walk goes straight
  // on into them; with it off they are targets like the others and stop you short of their face
  const flaggedIds = inApproach.map(p => p.id);
  await F(`F.setKeepDoorways(false)`);
  const tgOff = await T(`T.targets()`);
  const fTargets = tgOff.filter(t => t.side !== null && flaggedIds.includes(t.id));
  const fOff = [];
  for (const t of fTargets) fOff.push(await walkPiece(t.id, t.side, t.back, false));
  await F(`F.setKeepDoorways(true)`);
  const fOn = [];
  for (const t of fTargets) fOn.push(await T(`T.walkTo(__host.furniture.pieces().find(p => p.id === ${JSON.stringify(t.id)}), ${t.side}, ${t.back}, ${t.back + 0.5})`));
  const pastFace = w => w.gap < -0.05;                                   // the box is no collider: the walk gets over the face line (what is behind it may stop it a little later)
  check(`the ${flaggedIds.length} boxes in a doorway's approach (${flaggedIds.join(', ')}): none is among the boxes Walk stops at while the doorways are kept clear; ${fTargets.length} have a free line - with Keep doorways clear off each stops you short of its face (gap ${fOff.length ? r2(Math.min(...fOff.map(w => w.gap))) : '-'} - ${fOff.length ? r2(Math.max(...fOff.map(w => w.gap))) : '-'} m), with it on the same walk gets past the face (${fOn.length ? r2(Math.min(...fOn.map(w => -w.gap))) : '-'} - ${fOn.length ? r2(Math.max(...fOn.map(w => -w.gap))) : '-'} m in)`,
    flaggedIds.length > 0 && !tg.some(t => flaggedIds.includes(t.id)) && tgOff.length === tg.length + flaggedIds.length && fTargets.length >= 1 && fOff.every(stopped) && fOn.every(pastFace),
    { off: fOff.filter(w => !stopped(w)), on: fOn.filter(w => !pastFace(w)), covered: fTargets.map(t => t.id), noLine: tgOff.filter(t => t.side === null && flaggedIds.includes(t.id)).map(t => `${t.id}: ${t.why}`) });

  // the show and stops ticks (real clicks): the same walk goes through a box once its kind's show tick or stops tick is off (shown, the box stays drawn but
  // lets you through), and stops you again when the tick is on again
  const tickKind = (await T(`[...new Set(T.targets().filter(t => t.side !== null).map(t => t.kind))]`)).map(k => [k, 0]);
  for (const kc of tickKind) kc[1] = (await T(`T.crossable(${JSON.stringify(kc[0])}, 3)`)).length;
  const pickKind = (tickKind.find(([k, n]) => k !== 'other' && n >= 2) || tickKind.sort((a, b) => b[1] - a[1])[0])[0];
  const boxesTick = await T(`T.crossable(${JSON.stringify(pickKind)}, 3)`);
  const tick = [];
  for (const c of boxesTick) {
    const r = { id: c.id, from: c.back };
    for (const part of ['show', 'blk']) {
      r[part] = {};
      r[part].stops = stopped(await walkPiece(c.id, c.side, c.back, false));
      await clickSel(rowSel(pickKind, part));
      r[part].through = passed(await walkPiece(c.id, c.side, c.back, true, pickKind));
      r[part].state = await F(`({ collider: __host.FL[${JSON.stringify(c.floor)}].colliders.includes(F.meshOf(${JSON.stringify(c.id)})), drawn: F.meshOf(${JSON.stringify(c.id)}).visible })`);
      await clickSel(rowSel(pickKind, part));
      r[part].stopsAgain = stopped(await walkPiece(c.id, c.side, c.back, false));
    }
    tick.push(r);
  }
  const label = k => file.furnitureKinds.find(x => x.key === k).label;
  check(`the show and stops ticks (real clicks) for ${label(pickKind)}: the same walk (from ${boxesTick.map(c => c.back).join(' / ')} m) goes right through ${boxesTick.length} real boxes (${boxesTick.map(c => c.id).join(', ')}) once either tick is off - unshown they are gone, not stopping they stay drawn - and they stop you again when it is back on`,
    boxesTick.length >= 2 && tick.every(t => ['show', 'blk'].every(k => t[k].stops && t[k].through && !t[k].state.collider && t[k].stopsAgain)) && tick.every(t => !t.show.state.drawn && t.blk.state.drawn), tick);

  // a height under the knee ray (300 mm) is stepped over: the walk goes right across the same boxes; at the kind's default height they stop you again
  const heights = [];
  const dflt = file.furnitureKinds.find(k => k.key === pickKind).height;
  for (const mm of [300, dflt]) {
    await typeHeight(pickKind, mm);
    const w = [];
    for (const c of boxesTick) w.push(mm === 300 ? await walkPiece(c.id, c.side, c.back, true, pickKind) : await walkPiece(c.id, c.side, c.back, false));
    heights.push([mm, w.every(x => (mm === 300 ? passed(x) : stopped(x))), w.map(x => x.start ? `${r2(x.moved)} m, gap ${r2(x.gap)}` : x.why)]);
  }
  await clickSel('.fb-reset');
  check(`${label(pickKind)} typed as 300 mm is stepped over (the walk goes right across all ${boxesTick.length} boxes), at ${dflt} mm they stop you again (short of the face)`, heights.every(h => h[1]), heights);

  // Ghost flies through two real boxes of different kinds that stop Walk: in front of the face at half the box's height, W held until 0.3 m past the far face
  const ghost = [];
  const ghostPicks = [];
  for (const t of await T(`T.targets()`)) if (t.side !== null && !ghostPicks.some(g => g.kind === t.kind) && ['counter', 'sofa', 'appliance', 'other'].includes(t.kind)) ghostPicks.push(t);
  for (const pick of ghostPicks.slice(0, 2)) {
    await P.press('Digit2'); await P.evaluate(`document.activeElement && document.activeElement.blur()`);
    const pc = `__host.furniture.pieces().find(p => p.id === ${JSON.stringify(pick.id)})`;
    const stop = await walkPiece(pick.id, pick.side, pick.back, false);              // Walk stops short of it ...
    const L = await T(`T.lane(${pc}, ${pick.side}, 1.5, false)`);
    await P.press('Digit3');                                                          // ... Ghost does not
    await P.evaluate(`(() => { const p = ${pc}, s = __viewer.state; s.pos.set(${L.start[0]}, __t.levelOf(p.floor) + (p.z0 + p.z1) / 2, ${L.start[1]}); s.yaw = Math.atan2(${L.n[0]}, ${L.n[2]}); s.pitch = 0; })()`);
    const t1 = Date.now();
    await P.keyDown('KeyW');
    let at = null;
    for (let i = 0; i < 160; i++) {
      await sleep(125);
      at = await T(`T.along(${JSON.stringify(pick.id)}, ${pick.side})`);
      if (at.rel < -(at.half + 0.3)) break;
    }
    await P.keyUp('KeyW');
    ghost.push({ id: pick.id, kind: pick.kind, walkStopsAt: r2(stop.gap), ghostEndsBeyondFace: r2(-at.rel - at.half), height: r2(at.y), seconds: r2((Date.now() - t1) / 1000),
      ok: stopped(stop) && at.rel < -(at.half + 0.3) && at.y > at.z0 && at.y < at.z1 });
  }
  check(`Ghost flies straight through two real boxes that stop Walk short of their face (${ghost.map(g => `${g.id}`).join(', ')}), at half their height`, ghost.length === 2 && ghost.every(g => g.ok), ghost);
  await P.press('Digit1');

  // ------------------------------------------------------------------ the doors and passages with the boxes, Keep doorways clear on and off
  // With the tick on (the default) the boxes the builder put in a door's or a passage's approach are no colliders: every door can be walked through as
  // without the boxes, and no passage is harder to walk through. Then the tick is clicked off: the doors and passages the boxes block are measured and
  // each must be named by a box's approach list (a box the builder did not flag must not block one). The tick is clicked on again.
  await P.press('Digit2'); await P.evaluate(`document.activeElement && document.activeElement.blur()`);
  const withBoxes = await walkOpenings(true);
  const worseThanBare = walks => walks.filter(r => r.kind !== 'window').map(r => ({ r, b: bare.find(x => x.id === r.id) })).filter(({ r, b }) => r.result in RANK && b.result in RANK && RANK[r.result] < RANK[b.result])
    .map(({ r, b }) => ({ id: r.id, kind: r.kind, bare: `${b.result} (${b.fwd ?? '-'} / ${b.back ?? '-'})`, now: `${r.result} (${r.fwd ?? '-'} / ${r.back ?? '-'})`, pieces: piecesOf([...r.fwdTries, ...r.backTries]) }));
  const changed = walks => walks.filter(r => r.kind !== 'window').filter(r => { const b = bare.find(x => x.id === r.id); return r.fwd !== b.fwd || r.back !== b.back; })
    .map(r => { const b = bare.find(x => x.id === r.id); return `${r.id} ${b.fwd ?? '-'} / ${b.back ?? '-'} -> ${r.fwd ?? '-'} / ${r.back ?? '-'} m: ${piecesOf([...r.fwdTries, ...r.backTries]).join(', ') || 'no box named'}`; });
  const doorsOn = withBoxes.filter(r => r.kind === 'door'), worseOn = worseThanBare(withBoxes);
  for (const c of changed(withBoxes)) note('a box near a door or passage, with the doorways kept clear (information)', c);
  check(`with the boxes on and Keep doorways clear on, all ${doorsOn.length} doors can be walked through as without the boxes (${doorsOn.filter(r => r.result === 'both ways').length} both ways, ${doorsOn.filter(r => r.result === 'from the floor side').length} from the only side with floor) and none of the ${withBoxes.filter(r => r.kind === 'passage').length} passages is harder to walk through`,
    doorsOn.length > 0 && !doorsOn.some(r => r.result === 'blocked' && bare.find(b => b.id === r.id).result !== 'blocked') && !worseOn.length, worseOn.length ? worseOn : undefined);
  await clickSel('.fb-keep'); await P.evaluate(`document.activeElement && document.activeElement.blur()`);
  const keptOff = await F(`F.keepDoorways()`);
  await P.press('Digit2');
  const offWalks = await walkOpenings(true);
  await clickSel('.fb-keep'); await P.evaluate(`document.activeElement && document.activeElement.blur()`);
  const keptOn = await F(`F.keepDoorways()`);
  const worseOff = worseThanBare(offWalks), flaggedFor = id => inApproach.filter(p => p.approach.includes(id)).map(p => p.id);
  for (const c of changed(offWalks)) note('with Keep doorways clear off (information)', c);
  // the openings the builder named, as walked without the boxes -> with them and the tick off (a door or passage: its verdict and metres past the
  // line both ways; a window or glazed door: how far short of the glass you stop)
  const listed = [...new Set(inApproach.flatMap(p => p.approach))].sort();
  const walked = r => r ? (r.kind === 'window' ? '' : r.result + ' ') + `${r.fwd ?? '-'} / ${r.back ?? '-'}` : '?';
  const listedNow = listed.map(id => { const o = offWalks.find(r => r.id === id); return `${id} (${o ? o.kind : '?'}) ${walked(bare.find(r => r.id === id))} -> ${walked(o)}`; });
  check(`Keep doorways clear clicked off: the ${inApproach.length} boxes in an approach become colliders, and ${worseOff.length ? `${worseOff.length} doors or passages are harder to walk through their middle (${worseOff.map(d => `${d.id} ${d.bare} -> ${d.now}`).join('; ')}), each named by a box's approach list` : 'no door or passage is harder to walk through its middle'} (the ${listed.length} openings their approach lists name, without the boxes -> with them: ${listedNow.join('; ')}); clicked on again, the rule is back`,
    keptOff === false && keptOn === true && worseOff.every(d => flaggedFor(d.id).length > 0), { worse: worseOff.map(d => ({ ...d, inItsApproachList: flaggedFor(d.id) })) });

  // the colliders against the approach lists, read from the page: with the tick on every piece with a non-empty approach is out of the colliders and every other
  // piece of a blocking kind is in; with it off all of them are in (the page's lists are the file's)
  const rule = await P.evaluate(`(() => { const F = __host.furniture, FL = __host.FL, out = {};
    const inCol = () => new Set(Object.values(FL).flatMap(f => f.colliders.filter(m => m.name.startsWith('furn:')).map(m => m.userData.id)));
    const state = keep => { F.setKeepDoorways(keep); const c = inCol(); return F.pieces().filter(p => p.blocks).map(p => [p.id, c.has(p.id), p.approach.length > 0, p.blocking]); };
    out.on = state(true); out.off = state(false); F.setKeepDoorways(true); out.keep = F.keepDoorways();
    out.checked = document.querySelector('.fb-keep').checked; return out; })()`);
  const wrongOn = rule.on.filter(([, inCol, flagged, blocking]) => inCol === flagged || blocking !== inCol), wrongOff = rule.off.filter(([, inCol, , blocking]) => !inCol || !blocking);
  check(`the colliders against the approach lists (read from the page): with the tick on the ${inApproach.length} pieces with an approach are out and the other ${rule.on.length - inApproach.length} pieces of blocking kinds are in; with it off all ${rule.off.length} are in; pieces() says the same (blocking)`,
    inApproach.length > 0 && rule.on.length === nBoxes && !wrongOn.length && !wrongOff.length && rule.keep === true && rule.checked, { wrongOn: wrongOn.slice(0, 4), wrongOff: wrongOff.slice(0, 4) });

  // the windows with the boxes on: walking at each from each side with floor you still stop before it (never through); a box in front may stop you
  // earlier or stand at the start spot (listed)
  const win = withBoxes.filter(r => r.kind === 'window');
  const winWalks = win.flatMap(r => [['fwd', r.floorNeg], ['back', r.floorPos]].filter(([, has]) => has).map(([k]) => ({ id: r.id, side: k, along: r[k], bare: bare.find(b => b.id === r.id)[k], tries: r[k + 'Tries'] })));
  const winThrough = winWalks.filter(w => num(w.along) && w.along > -0.1), winCut = winWalks.filter(w => w.along !== w.bare);
  check(`with the boxes on the windows still stop you: ${winWalks.filter(w => num(w.along)).length} of ${winWalks.length} walks at the ${win.length} windows and glazed doors from a side with floor stop before the glass, none goes through (${winCut.length} are cut short or have no start because of a box)`,
    winWalks.length > 0 && !winThrough.length, winThrough.length ? winThrough : undefined);
  if (winCut.length) note('windows a box stands in front of (information)', winCut.map(w => `${w.id} ${w.side}: ${w.bare} -> ${w.along} m, ${piecesOf(w.tries).join(', ')}`));

  // walking at the nearest wall or box from 40 random spots on each floor: never through it, never ending up inside a wall or a box
  const wallsOn = [];
  for (const key of FLOORS) { await P.evaluate(`__viewer.goToFloor(${JSON.stringify(key)})`); wallsOn.push({ floor: key, ...await P.evaluate(wallWalks) }); }
  check('with the boxes on: walking at the nearest wall or box (knee or chest height) from 40 random spots on each floor, never through it and never ending up inside a wall or a box',
    wallsOn.every(w => w.tried >= 30 && w.wentThrough === 0 && w.endedInsideWall === 0 && w.endedInABox === 0), wallsOn);

  // ------------------------------------------------------------------ not trapped
  // The faces of a box are single-sided, so Walk's rays from inside a box meet nothing of it: Walk entered at the middle of a box (the double-click path)
  // can put the player inside a box, and he can always walk out. verdict(): A = walks out (1 m or more in some direction of 8) or is in no box; B = does
  // not, but would with only the boxes around him (a pocket of other boxes: information); C = a box holds him itself.
  const mids = await F(`F.pieces().filter(p => p.blocking).map(p => p.id)`);
  const into = await P.evaluate(`(() => { const out = [];
    for (const id of ${JSON.stringify(mids)}) { __t.spawn(id); out.push({ id, ...__t.verdict() }); }
    __viewer.setMode('orbit'); __viewer.setMode('walk'); return out; })()`);
  const heldBy = into.filter(r => r.class === 'C'), inBox = into.filter(r => r.inside.length), pockets = into.filter(r => r.class === 'B');
  if (pockets.length) note('Walk entered in a pocket of overlapping boxes (information: nothing holds the player but other boxes)', pockets.map(r => `${r.id} in ${r.inside.join('+')}: ${r2(r.best)} m, ${r2(r.alone)} m with only those boxes`));
  check(`not trapped: Walk entered at the middle of each of the ${mids.length} boxes that stop you lands the player inside a box ${inBox.length} times; ${inBox.filter(r => r.class === 'A').length} walk out at once and ${pockets.length} are in a pocket of other boxes, none is held by a box itself`,
    mids.length === blockingN && inBox.length >= 10 && heldBy.length === 0, heldBy.length ? heldBy : { inside: inBox.length, pockets: pockets.map(r => r.id) });
  // ... and from a spot where a box is switched on under the player: its kind's show tick, its stops tick, a taller height (three kinds), the doorways tick
  // (each of the boxes in an approach)
  const scenarios = {};
  for (const kind of ['sofa', 'sanitary', 'other']) {
    const plain = file.furniture.find(p => p.kind === kind && !(p.approach || []).length).id;
    scenarios[kind] = await P.evaluate(`(() => { const F = __host.furniture, T = __t, out = {}, id = ${JSON.stringify(plain)}, kind = ${JSON.stringify(kind)}, h = F.kinds().find(k => k.key === kind).height;
      const run = (name, prepare, on) => { prepare(); T.standIn(id); const before = T.holding().includes(id); on(); out[name] = { id, before, ...T.verdict() }; };
      run('show', () => F.setVisible(kind, false), () => F.setVisible(kind, true));
      run('stops', () => F.setBlocks(kind, false), () => F.setBlocks(kind, true));
      run('height', () => F.setHeight(kind, 100), () => F.setHeight(kind, h));
      F.reset(); return out; })()`);
  }
  const doorwaysAll = await P.evaluate(`(() => { const F = __host.furniture, T = __t, out = [];
    for (const p of F.pieces().filter(q => q.approach.length)) { F.setKeepDoorways(true); T.standIn(p.id); const before = T.holding().includes(p.id); F.setKeepDoorways(false); out.push({ id: p.id, before, ...T.verdict() }); }
    F.setKeepDoorways(true); return out; })()`);
  const scAll = Object.entries(scenarios).flatMap(([kind, sc]) => Object.entries(sc).map(([name, r]) => ({ label: `${kind}/${name}`, ...r })));
  const around = r => r.before === false && r.inside.includes(r.id);                         // the box was no obstacle to the player at the middle of it, and it is around him now
  check(`not trapped: a box switched on under the player (the show tick, the stops tick, typed taller: 100 mm -> its height; a sofa, a sanitary fitting, a grey box: ${scAll.length} cases) does not hold him, nor does any of the ${doorwaysAll.length} boxes in an approach when the doorways tick is switched off under him`,
    scAll.every(r => around(r) && r.class !== 'C') && doorwaysAll.length === inApproach.length && doorwaysAll.every(r => around(r) && r.class !== 'C'),
    { held: [...scAll, ...doorwaysAll].filter(r => r.class === 'C').map(r => r.label || r.id), notAround: [...scAll, ...doorwaysAll].filter(r => !around(r)).map(r => r.label || r.id), pockets: [...scAll, ...doorwaysAll].filter(r => r.class === 'B').map(r => r.label || r.id) });
  await P.press('Digit1');

  // ------------------------------------------------------------------ the family list the page writes is the builder's file, byte for byte
  await F(`F.reset()`);
  const page = Buffer.from(await F('F.csv()'), 'utf8'), list = readFileSync(LIST), bom = list.subarray(0, 3).equals(Buffer.from([0xEF, 0xBB, 0xBF]));
  const same = bom && page.equals(list.subarray(3)), lines = page.toString('utf8').split('\r\n');
  const noted = lines.filter(l => l.includes('in the approach of')).length, grey = lines.filter(l => l.split(',')[3] === 'Other furniture').length;
  check(`the page's csv() is house_furniture_list.csv without its byte-order mark, byte for byte (${page.length} bytes, ${lines.length - 2} rows, ${grey} of them 'Other furniture'), and ${noted} of its rows carry "in the approach of ..." (one per box in an approach: ${inApproach.length})`,
    same && noted === inApproach.length && grey === other.count, same ? { identical: true } : { page: page.length, file: list.length - 3, bom, firstDifference: [...page].findIndex((b, i) => b !== list[i + 3]) });

  // ------------------------------------------------------------------ the label under the pointer in Orbit
  // Over real boxes of different kinds on the ground floor: kind, family, size and floor; over a grey box no other kind is named; over a box in a doorway's
  // approach the label says that it does not stop you
  await goHome();
  await clickSel('#floors [data-f=ground]'); await sleep(500);
  const wantKinds = ['other', ...file.furnitureKinds.map(k => k.key).filter(k => k !== 'other')];        // a grey box first, then one of each kind the camera sees
  const spotsHover = await T(`T.hoverSpots('ground', ${JSON.stringify(wantKinds)}, 5)`);
  const flaggedSeen = inApproach.filter(p => p.floor === 'ground' && !spotsHover.some(s => s.id === p.id)).map(p => 'id:' + p.id);
  const spotFlag = spotsHover.some(s => s.approach.length) ? null : (await T(`T.hoverSpots('ground', ${JSON.stringify(flaggedSeen)}, 1)`))[0];
  const tipNow = () => P.evaluate(`(() => { const t = document.querySelector('.fb-tip'); return t && t.style.display === 'block' ? t.innerText : null; })()`);
  const hovers = [];
  for (const sp of [...spotsHover, ...(spotFlag ? [spotFlag] : [])]) {
    await P.mouse('mouseMoved', 1250, 40, { button: 'none' });
    for (let i = 0; i < 20 && (await tipNow()) !== null; i++) await sleep(100);
    await P.mouse('mouseMoved', sp.x, sp.y, { button: 'none' });
    let tip = null;
    for (let i = 0; i < 30 && tip === null; i++) { await sleep(100); tip = await tipNow(); }
    const lab = label(sp.kind), flat = x => String(x).replace(/\s+/g, ' '), text = tip && flat(tip);       // the label's lines are one run of text to compare
    const claims = text ? named.filter(n => n !== lab && text.includes(n)) : [];
    const door = sp.approach.length ? `does not stop you: in the approach of ${sp.approach.join(', ')}` : null;
    hovers.push({ id: sp.id, kind: sp.kind, door: !!door, ok: !!tip && text.includes(lab) && text.includes(flat(sp.family)) && text.includes(sp.size) && text.includes('Ground floor') && !claims.length
      && (door ? text.includes(door) : !text.includes('does not stop you')), tip: text, claims });
    if (sp === spotsHover[0]) await P.shot(path.join(OUT, 'house_furniture_hover_other.png'));
    if (door && hovers.filter(h => h.door).length === 1) await P.shot(path.join(OUT, 'house_furniture_hover_doorway.png'));
  }
  check(`Orbit: the pointer over ${hovers.length} real boxes (${hovers.map(h => h.id + (h.door ? ', in a doorway\'s approach' : '')).join('; ')}) shows a label with the kind, the family, the size and the floor; the grey box's label names no other kind; a box in a doorway's approach says that it does not stop you`,
    spotsHover.length >= 4 && spotsHover[0].kind === 'other' && hovers.some(h => h.door) && hovers.every(h => h.ok), hovers.map(h => h.ok ? `${h.kind}: ${h.tip}` : h));
  await P.mouse('mouseMoved', 1250, 40, { button: 'none' });
  await clickSel('#floors [data-f=both]'); await sleep(300);

  // ------------------------------------------------------------------ the replay's restore hook
  // a kind hidden before a replay is hidden again after it (the replay shows every late object at its end), a kind set not to stop you stays so,
  // and the doorways rule holds: with the tick on the boxes in an approach are no colliders, with it off they are
  const rep = await P.evaluate(`(() => { const F = __host.furniture, ms = F.pieces().map(p => F.meshOf(p.id)), out = {};
    F.setVisible('sanitary', false); F.setBlocks('sofa', false);
    __build.seek(0); out.start = ms.filter(m => m.visible).length;
    __build.seek(1); out.end = ms.filter(m => m.visible).length;
    __build.skip(); out.phase = __build.phase;
    const k = Object.fromEntries(F.kinds().map(x => [x.key, x]));
    out.wrong = F.pieces().filter(p => F.meshOf(p.id).visible !== k[p.kind].visible).length;
    out.cols = [...new Set(Object.values(__host.FL).flatMap(f => f.colliders.filter(m => m.name.startsWith('furn:')).map(m => m.userData.kind)))];
    out.opaque = ms.every(m => m.material.opacity === 1 && !m.material.transparent);
    F.setVisible('sanitary', true); F.setBlocks('sofa', true);
    return out; })()`);
  check('replaying the build and skipping to its end: the boxes are not there at the start and all of them are at the end, then the page puts back what you had (sanitary fittings hidden, sofas not stopping you)',
    rep.start === 0 && rep.end === nBoxes && rep.phase === 'done' && rep.wrong === 0 && rep.opaque && !rep.cols.includes('sanitary') && !rep.cols.includes('sofa') && rep.cols.includes('other'), rep);
  const repDoor = await P.evaluate(`(() => { const F = __host.furniture, FL = __host.FL, fl = F.pieces().filter(p => p.approach.length), plain = F.pieces().filter(p => !p.approach.length && p.blocks),
      inCol = p => FL[p.floor].colliders.includes(F.meshOf(p.id)), out = {};
    __build.seek(0); __build.seek(1); __build.skip(); out.on = fl.map(inCol); out.plainIn = plain.every(inCol);
    F.setKeepDoorways(false); __build.seek(0); __build.seek(1); __build.skip(); out.off = fl.map(inCol); out.n = fl.length; F.setKeepDoorways(true); return out; })()`);
  check(`after a replay the doorways rule still holds: with the tick on the ${repDoor.n} boxes in an approach are no colliders and every other box of a blocking kind is one, with it off the ${repDoor.n} are colliders`,
    repDoor.n === inApproach.length && repDoor.on.every(x => !x) && repDoor.plainIn && repDoor.off.every(Boolean), repDoor);

  // ------------------------------------------------------------------ screenshots: Orbit with the legend, the kitchen close up, Walk at a box
  await goHome();
  await P.evaluate(`document.querySelector('.fb-block').scrollIntoView({ block: 'start' })`); await sleep(300);
  await P.shot(path.join(OUT, 'house_furniture_orbit_both.png'));
  for (const key of FLOORS) { await clickSel(`#floors [data-f=${key}]`); await sleep(500); await P.shot(path.join(OUT, `house_furniture_orbit_${key}.png`)); }
  // each floor from higher up (its walls hide most of its boxes from the usual view): looking down at its middle from the usual side
  for (const key of FLOORS) {
    await clickSel(`#floors [data-f=${key}]`);
    await P.evaluate(`(() => { const b = new __t.THREE.Box3().setFromObject(__host.FL[${JSON.stringify(key)}].group), c = b.getCenter(new __t.THREE.Vector3()), r = Math.max(b.max.x - b.min.x, b.max.z - b.min.z);
      c.y = __t.levelOf(${JSON.stringify(key)}); __host.controls.target.copy(c); __host.camera.position.set(c.x - 0.22 * r, c.y + 0.85 * r, c.z + 0.3 * r); __host.controls.update(); })()`);
    await sleep(600); await P.shot(path.join(OUT, `house_furniture_top_${key}.png`));
  }
  await goHome();
  await clickSel('#floors [data-f=ground]'); await sleep(300);
  const kitchen = await P.evaluate(`(() => { const F = __host.furniture, THREE = __t.THREE, V3 = THREE.Vector3;
    // the kitchen: the counter (the island) and the appliances and cabinets around it on the ground floor
    const c0 = F.pieces().find(p => p.kind === 'counter' && p.floor === 'ground');
    const group = F.pieces().filter(p => p.floor === 'ground' && ['counter', 'appliance', 'cabinet'].includes(p.kind) && Math.hypot(p.x - c0.x, p.y - c0.y) < 4);
    const target = new V3(group.reduce((s, p) => s + p.x, 0) / group.length, __t.levelOf('ground') + 0.9, -group.reduce((s, p) => s + p.y, 0) / group.length);
    const ray = new THREE.Raycaster(), cols = __host.FL.ground.colliders.filter(m => m.visible && !m.name.startsWith('furn:'));
    let best = null;                                  // from the side the usual view looks from if the walls leave it free, else the nearest free side
    for (const [far, up] of [[4.5, 5.5], [3.5, 5.0], [2.6, 4.6], [1.6, 4.2]]) {
      for (const da of [0, 15, -15, 30, -30, 45, -45, 60, -60, 75, -75, 90, -90, 105, -105, 120, -120, 135, -135, 150, -150, 165, -165, 180]) {
        const a = (130 + da) * Math.PI / 180, c = new V3(target.x + Math.cos(a) * far, target.y + up, target.z + Math.sin(a) * far), d = target.clone().sub(c), L = d.length();
        ray.set(c, d.normalize()); ray.far = L - 0.2;
        if (!best && !ray.intersectObjects(cols, false).length) best = c;
      }
      if (best) break;
    }
    __host.controls.target.copy(target); __host.camera.position.copy(best || target.clone().add(new V3(0.5, 6, 0.5))); __host.controls.update();
    return { pieces: group.map(p => p.id), around: [target.x, target.z].map(x => Math.round(x * 10) / 10), camera: (best || target).toArray().map(x => Math.round(x * 10) / 10) }; })()`);
  await sleep(700);
  await P.shot(path.join(OUT, 'house_furniture_kitchen.png'));
  note('close-up of the kitchen (Orbit, ground floor)', kitchen);
  await clickSel('#floors [data-f=both]'); await sleep(200);
  await P.press('Digit2'); await P.evaluate(`document.activeElement && document.activeElement.blur()`);
  const view = await P.evaluate(`(() => { const F = __host.furniture, s = __viewer.state;
    for (const kind of ['counter', 'sofa', 'other']) for (const p of F.pieces().filter(q => q.kind === kind && q.floor === 'ground')) for (const back of [1.8, 1.4, 1.1]) for (const side of [2, 3, 0, 1]) {
      const L = __t.lane(p, side, back, false);
      if (!L.free) continue;
      __viewer.goToFloor('ground'); s.pos.x = L.start[0]; s.pos.z = L.start[1]; s.yaw = Math.atan2(L.n[0], L.n[2]); s.pitch = -0.25;
      return { box: p.id, side, back };
    }
    return null; })()`);
  await sleep(700);
  await P.shot(path.join(OUT, 'house_furniture_walk_box.png'));
  note('Walk at a box', view);
  await P.press('Digit1');

  flush();
  check('no page errors', !errors.length, errors);
} catch (e) {
  check('the test ran to the end', false, String(e && e.stack || e).slice(0, 700));
} finally {
  console.log(`\n${results.filter(Boolean).length} passed, ${results.filter(x => !x).length} failed  (${Math.round((Date.now() - t0) / 1000)} s; screenshots in ${OUT})`);
  await close();
}
process.exit(results.every(Boolean) ? 0 : 1);
