// Checks the presidential suite page (built from 'layout presidential test.dwg') in headless Edge: the build replay,
// room names, walking (walls stop you, every door and opening lets you through, the glass stops you), Ghost, the Camera.
// The furniture boxes (one per piece, coloured by kind) have their own checks: the legend and a height text box per kind (typed
// into with real key events), one box per piece in the suite's group, the page's own ticks leaving them alone, the side panel at
// 1366 x 768 and 1920 x 1080 and above the hint line at every window height from 640 to 1080 px, a table typed lower with what
// stands on it, Walk starting clear of them, Walk stopped by real pieces of every kind that stops you (from 1 m or a little
// nearer, short of the face, never inside, never through), the show and stops ticks, a seat of 300 mm (stepped over) against
// 450 mm (a stop), Ghost through real pieces, the family list against the builder's file, the label under the pointer in Orbit
// and the build replay. The structure checks (walls, doors, glass) run with every kind of furniture hidden: the boxes are colliders, so
// what the drawing's own walls, doors and glass do is judged without them; then the doors, the glass and the walls are walked
// again with the boxes shown, and what a box changes is counted and listed.
// The tick 'Keep doorways clear' (on by default): the boxes the builder put in the approach of a door or an opening (the
// 'approach' ids of the model are the door codes D1 ... O6, 'in the approach of ...' in the family list) are drawn but are no
// colliders, so every door and opening can be walked through with the boxes on; with the tick off the doors the boxes block are
// measured and listed. The colliders are read from the page against those lists, the walk-stop check is run for the boxes in an
// approach with the tick off and on, and, the faces being single-sided, a player entered at the middle of any box (or with a box
// switched on under him) is never held by it. Curtains never stop Walk (their kind's default), in an approach or not.
// Usage (from the project folder): node presidential_test/test_presidential.mjs
// PRES_URL points it at another build of the page; PRES_PORT (default 9344), PRES_PROFILE and PRES_OUT set the debugging
// port, the browser profile and the screenshot folder (both under %TEMP%\presidential-test unless given); EDGE another
// browser (see viewer-modes/cdp.mjs). The test stops at once if something already answers on the port (another session's
// browser): the shared launcher would attach to that browser and finally close it.
import { launch, pageApi, sleep } from '../viewer-modes/cdp.mjs';
import { mkdirSync, readFileSync, existsSync } from 'node:fs';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { tmpdir } from 'node:os';
import { createHash } from 'node:crypto';
import path from 'node:path';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');     // the project folder
const HERE = path.join(ROOT, 'presidential_test');
const TMP = path.join(tmpdir(), 'presidential-test'), OUT = process.env.PRES_OUT || path.join(TMP, 'out');   // screenshots and browser profile
mkdirSync(OUT, { recursive: true });
const URL = process.env.PRES_URL || pathToFileURL(path.join(ROOT, 'presidential_test', 'presidential_3d_preview.html')).href;
const PORT = Number(process.env.PRES_PORT || 9344);
let busy = true;
try { await fetch(`http://127.0.0.1:${PORT}/json/version`, { signal: AbortSignal.timeout(1500) }); } catch { busy = false; }
if (busy) {
  console.error(`Port ${PORT} already answers (another browser is using it). Close it or set PRES_PORT to a free port.`);
  process.exit(2);
}
const results = [];
const check = (name, ok, info) => { results.push(!!ok); console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${info !== undefined ? '   ' + JSON.stringify(info) : ''}`); };
const note = (name, info) => console.log(`      ${name}${info !== undefined ? ': ' + JSON.stringify(info) : ''}`);
const r2 = v => Math.round(v * 100) / 100;
const t0 = Date.now();
const { tab, close } = await launch({ port: PORT, profile: process.env.PRES_PROFILE || path.join(TMP, 'profile') });
const P = pageApi(tab);
const st = () => P.evaluate(`(() => { const s = __viewer.state; return { mode: s.mode, floor: s.floor.key, level: s.floor.level, x: s.pos.x, y: s.pos.y, z: s.pos.z }; })()`);
const errs = () => P.logs.filter(l => /exception|error/i.test(l));
const errors = [];                                      // page errors of the pages already left (P.goto clears the log)
const flush = () => { errors.push(...errs()); P.logs.length = 0; };
// the furniture boxes: how many show (their own switch), and the switch for all kinds at once (no furniture, no effect)
const boxesShown = `(() => { let n = 0; for (const f of Object.values(__host.FL)) f.group.traverse(o => { if (o.name.startsWith('furn:') && o.visible) n++; }); return n; })()`;
const setFurniture = on => P.evaluate(`(() => { const F = __host.furniture; if (F) F.kinds().forEach(k => F.setVisible(k.key, ${on})); })()`);

// Walls: walk into the nearest wall from 40 random spots; never end up on the other side or inside it. outsideBoxes (the boxes
// shown): a spot inside a box that stops you is no start (its single-sided faces are not seen from inside, so the spot looks
// free, and the walk out of it ends against its outer face): such spots are counted and skipped.
const wallWalks = outsideBoxes => `(() => { const v = __viewer, s = v.state, keep = s.pos.clone(); let seed = 3, n = 0, through = 0, stuck = 0, tries = 0, inBox = 0;
  const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
  const box = { x0: Infinity, x1: -Infinity, z0: Infinity, z1: -Infinity };
  for (const o of __host.group.children) {
    if (!o.geometry) continue;
    o.geometry.computeBoundingBox(); const g = o.geometry.boundingBox;
    box.x0 = Math.min(box.x0, g.min.x); box.x1 = Math.max(box.x1, g.max.x); box.z0 = Math.min(box.z0, g.min.z); box.z1 = Math.max(box.z1, g.max.z);
  }
  while (n < 40 && tries++ < 6000) {
    s.pos.x = box.x0 + rnd() * (box.x1 - box.x0); s.pos.z = box.z0 + rnd() * (box.z1 - box.z0);
    if (!v.probe.onFloor() || v.probe.clearance() < 0.6) continue;
    if (${!!outsideBoxes} && __t.holding().length) { inBox++; continue; }
    const d = [...Array(72)].map((_, i) => v.probe.open(i * 5)); let k = 0; d.forEach((x, j) => { if (x < d[k]) k = j; });
    if (d[k] > 2.5) continue;
    const a = s.pos.clone(); v.probe.walk(k * 5, d[k] + 1);
    n++; if (v.probe.crosses(a.x, a.z, s.pos.x, s.pos.z)) through++; if (v.probe.clearance() < 0.15) stuck++;
  }
  s.pos.copy(keep); return Object.assign({ tried: n, wentThrough: through, endedInsideWall: stuck }, ${!!outsideBoxes} ? { skippedInABox: inBox } : {}); })()`;
// Doors: from in front of each door (0.9 m, or nearer if that spot is not on the floor or not clear), walk straight through
// it; you should come out at least 0.3 m on the other side. Exterior doors (to the corridor, which is not in the drawing) only
// have to be reachable from inside: you get to the door line. why: also say what is in the way (the boxes near a start spot,
// the boxes that stopped the walk).
const doorWalks = why => `(() => { const v = __viewer, s = v.state, keep = s.pos.clone(), out = [];
  for (const d of __host.doors) {
    const res = { id: d.id, name: d.name, exterior: !!d.exterior };
    for (const sign of [1, -1]) {
      const nx = d.nx * sign, ny = d.ny * sign, deg = Math.atan2(-nx, ny) * 180 / Math.PI;
      let along = null; const tries = [];
      for (const back of [0.9, 0.7, 0.55]) {         // a start spot on the floor, clear of walls
        s.pos.x = d.x - nx * back; s.pos.z = -(d.y - ny * back);
        if (!v.probe.onFloor() || v.probe.clearance() < 0.25) { if (${!!why}) tries.push({ back, onFloor: v.probe.onFloor(), near: __t.near('suite', s.pos.x, s.pos.z, 0.3) }); continue; }
        v.probe.walk(deg, back * 2);
        along = (s.pos.x - d.x) * nx + (-s.pos.z - d.y) * ny;     // metres past the door line
        if (${!!why}) tries.push({ back, along: Math.round(along * 100) / 100, stoppedBy: __t.stoppedBy('suite', s.pos.x, s.pos.z, deg) });
        break;
      }
      res[sign > 0 ? 'fwd' : 'back'] = along === null ? 'no start' : Math.round(along * 100) / 100;
      if (${!!why}) res[sign > 0 ? 'fwdTries' : 'backTries'] = tries;
    }
    const num = x => typeof x === 'number';
    res.ok = d.exterior ? [res.fwd, res.back].some(x => num(x) && x > -0.15)
                        : num(res.fwd) && num(res.back) && res.fwd > 0.3 && res.back > 0.3;
    out.push(res);
  }
  s.pos.copy(keep); return out; })()`;
// Glass stops you: from 1 m inside the living room's west glass, walk west 2 m; you stay inside. why: what stopped the walk.
const glassWalk = why => `(() => { const v = __viewer, s = v.state, keep = s.pos.clone();
  const gx = __host.glassWestX;                      // x of the glass's room-side face (model metres)
  s.pos.x = gx + 1.0; s.pos.z = -__host.glassWestY; const moved = v.probe.walk(90, 2.0);
  const x = s.pos.x, by = ${!!why} ? __t.stoppedBy('suite', s.pos.x, s.pos.z, 90) : undefined;
  s.pos.copy(keep); return { stoppedAt: Math.round((x - gx) * 100) / 100, moved: Math.round(moved * 100) / 100, stoppedBy: by }; })()`;

// ---------------------------------------------------------------------------- the furniture, as the checks below use it
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
// Walk's rays look ahead the body's radius (0.30 m) plus the next 5 cm step, so walking straight at a face you stop with it 0.30 -
// 0.35 m ahead (1 cm either way for rounding): short of the face, never inside the box, after a walk of 10 cm at least
const stopped = w => w.start && w.gap >= 0.29 && w.gap <= 0.36 && !w.inside && w.moved >= 0.1;
const passed = w => w.start && w.moved >= w.metres - 0.01 && w.gap < -0.2;                          // right across it and out the other side

// In the page: what the furniture checks read out of it. Runs inside the page (its THREE comes from the page's import map).
// A "lane" is a walk straight at a face of a box (side 0 / 1: the ends along the long axis, 2 / 3: the long faces) from a spot
// back metres in front of it: free when there is floor all the way and Walk's own rays (knee and chest height, across the
// shoulders) meet nothing but that box.
async function pageHelpers() {
  const THREE = await import('three');
  const F = __host.furniture, v = __viewer, s = v.state, V3 = THREE.Vector3, RADIUS = 0.3, KNEE = 0.35, CHEST = 1.2;
  const ray = new THREE.Raycaster(); ray.firstHitOnly = true;
  const levelOf = key => __host.floors.find(f => f.key === key).level;
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
  // looking straight down from h0 above the level at a plan spot: the first thing below that stops you (its height above the level, its name), or null
  function downAt(floor, x, y, h0 = 3.0) {
    ray.set(new V3(x, levelOf(floor) + h0, -y), new V3(0, -1, 0)); ray.far = 8;
    const hit = ray.intersectObjects(colliders(floor), false)[0];
    return hit ? { h: h0 - hit.distance, name: hit.object.name } : null;
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
  function freeLine(p) {                                             // the first free face of a box, from 1 m or nearer (0.8, 0.65, 0.5 m), or why there is none
    let why = '';
    for (const back of [1.0, 0.8, 0.65, 0.5]) for (const side of [2, 3, 0, 1]) { const t = lane(p, side, back, false); if (t.free) return t; if (!why) why = t.why; }
    return { free: false, why };
  }
  function targets() {                                               // the boxes that stop you (shown, stopping, not in a doorway's approach) and that Walk's rays can meet, each with its first free face
    const out = [];
    for (const p of F.pieces()) {
      if (!p.blocking || !spans(p)) continue;
      const L = freeLine(p);
      out.push({ ...brief(p), floor: p.floor, kind: p.kind, side: L.free ? L.side : null, back: L.free ? L.back : null, why: L.free ? '' : L.why });
    }
    return out;
  }
  function crossable(kind, max) {                                    // pieces of a kind with a free approach and a free line right across them
    const out = [];
    for (const p of F.pieces().filter(q => q.kind === kind && q.blocking)) {
      let pick = null;
      for (const back of [1.0, 0.8, 0.65]) {
        for (const side of [2, 3, 0, 1]) if (!pick && lane(p, side, back, false).free && lane(p, side, back, true, kind).free) pick = { id: p.id, floor: p.floor, side, back };
        if (pick) break;
      }
      if (pick && out.length < max) out.push(pick);
    }
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
  function topSpots(kind) {                                          // per piece of a kind: a plan spot on it where looking down from 3 m meets that piece's own top first
    return F.pieces().filter(p => p.kind === kind).map(p => {
      const r = p.rot * Math.PI / 180, ax = [Math.cos(r), Math.sin(r)], az = [-Math.sin(r), Math.cos(r)], name = F.meshOf(p.id).name;
      const spot = [[0, 0], [p.w / 4, 0], [-p.w / 4, 0], [0, p.d / 4], [0, -p.d / 4]].map(([a, b]) => [p.x + ax[0] * a + az[0] * b, p.y + ax[1] * a + az[1] * b])
        .find(([x, y]) => { const h = downAt(p.floor, x, y); return h && h.name === name && Math.abs(h.h - p.z1) < 0.005; });
      return { id: p.id, floor: p.floor, spot: spot || null };
    });
  }
  function hoverSpots(floor, max, only) {                            // boxes the Orbit camera sees (nothing in front of their top), as pointer positions, one per kind (only: among these ids)
    const cam = __host.camera, seen = new Set(), out = [], want = new THREE.Vector2();
    const showing = o => { for (let n = o; n; n = n.parent) if (!n.visible) return false; return true; };
    const hides = Object.values(__host.FL).flatMap(f => f.colliders.concat(f.walkables)).filter(m => showing(m) && !m.name.startsWith('furn:'));
    const boxes = F.pieces().map(b => F.meshOf(b.id)).filter(showing);
    const mine = F.pieces().filter(p => p.floor === floor && p.visible && (!only || only.includes(p.id))).sort((a, b) => b.w * b.d - a.w * a.d);
    for (const p of mine) {
      if (seen.has(p.kind)) continue;
      const m = F.meshOf(p.id), q = new V3(p.x, levelOf(floor) + p.z1, -p.y).project(cam);
      const x = (q.x + 1) / 2 * innerWidth, y = (1 - q.y) / 2 * innerHeight;
      if (q.z > 1 || x < 400 || x > innerWidth - 20 || y < 50 || y > innerHeight - 70) continue;
      ray.setFromCamera(want.set(q.x, q.y), cam); ray.far = Infinity;
      const hit = ray.intersectObjects(hides.concat(boxes), false)[0];
      if (hit && hit.object === m) { seen.add(p.kind); out.push({ ...brief(p), floor, x, y, approach: p.approach, size: `${p.w.toFixed(2)} × ${p.d.toFixed(2)} × ${(p.z1 - p.z0).toFixed(2)} m` }); }
      if (out.length >= max) break;
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
  // a view of a spot from above (far m away, up m higher): from the side `heading` says (degrees, three.js x towards z; 135 = the side the usual
  // view looks from) if the walls leave the line free, else the nearest free side
  function lookAt(target, poses = [[4.5, 6.5], [3.5, 5.6], [2.6, 4.8], [1.6, 4.4]], heading = 135) {
    const r = new THREE.Raycaster(), cols = __host.FL.suite.colliders.filter(m => m.visible && !m.name.startsWith('furn:'));
    let best = null;
    for (const [far, up] of poses) {
      for (const da of [0, 15, -15, 30, -30, 45, -45, 60, -60, 75, -75, 90, -90, 105, -105, 120, -120, 135, -135, 150, -150, 165, -165, 180]) {
        const a = (heading + da) * Math.PI / 180, c = new V3(target.x + Math.cos(a) * far, target.y + up, target.z + Math.sin(a) * far), d = target.clone().sub(c), L = d.length();
        r.set(c, d.normalize()); r.far = L - 0.2;
        if (!best && !r.intersectObjects(cols, false).length) best = c;
      }
      if (best) break;
    }
    __host.controls.target.copy(target); __host.camera.position.copy(best || target.clone().add(new V3(0.5, 6, 0.5))); __host.controls.update();
    return (best || target).toArray().map(x => Math.round(x * 10) / 10);
  }
  window.__t = { THREE, frame, lane, walk, walkTo, freeLine, targets, crossable, near, stoppedBy, downAt, topSpots, hoverSpots, along, levelOf, holding, leave, only, verdict, spawn, standIn, lookAt };
  return true;
}

try {
  // ------------------------------------------------------------------ the build replay
  await P.goto(URL + '?build=0&nodownload=1');
  // the typed furniture heights of an earlier run are kept in the browser profile: forget them, this run starts from the model's heights
  await P.evaluate(`(() => { try { Object.keys(localStorage).filter(k => k.startsWith('walkthrough-furniture')).forEach(k => localStorage.removeItem(k)); } catch (e) { /* blocked */ } })()`);
  const hasFurniture = await P.evaluate('!!(window.__host && __host.furniture)');
  flush();
  await P.goto(URL + '?speed=quick&build=play&nodownload=1');
  let early = null;
  if (hasFurniture) {
    await sleep(2500);
    early = await P.evaluate(`({ T: __build.state.T, phase: __build.phase, boxes: ${boxesShown} })`);
    await P.shot(path.join(OUT, 'suite_replay.png'));
  }
  for (let i = 0; i < 80 && (await P.evaluate('__build.phase')) !== 'done'; i++) await sleep(250);
  check('the build replay plays to the end and hands over to the viewer', (await P.evaluate('__build.phase')) === 'done');
  if (hasFurniture) {
    // the boxes are 'late' objects, like the floor slab: none while the drawing is read and the walls rise, all of them (opaque, those that stop you colliders) at the end
    const end = await P.evaluate(`(() => { const F = __host.furniture, ms = F.pieces().map(p => F.meshOf(p.id));
      return { n: ms.length, shown: ${boxesShown}, opaque: ms.every(m => m.material.opacity === 1 && !m.material.transparent && m.children.every(c => c.material.opacity === 1 && !c.material.transparent)),
        colliders: Object.values(__host.FL).reduce((n, f) => n + f.colliders.filter(m => m.name.startsWith('furn:')).length, 0),
        blocking: (M => M.furniture.filter(p => M.furnitureKinds.find(k => k.key === p.kind).blocks !== false && !(p.approach || []).length).length)(__host.model) }; })()`);   // the boxes that stop you: not the curtains, not those in a doorway's approach
    check(`the build replay brings in the ${end.n} furniture boxes last: none while the walls are still to rise (replay at ${Math.round(early.T * 100)} %), all of them, opaque, when it is done, and the ${end.blocking} that stop you (not the curtains, not the ones in a doorway's approach) are colliders`,
      early.phase === 'play' && early.T > 0.02 && early.T < 0.85 && early.boxes === 0 && end.shown === end.n && end.opaque && end.colliders === end.blocking, { atReplay: early, end });
  }
  await sleep(500);
  const shown = await P.evaluate(`[...document.querySelectorAll('.room')].filter(e => e.style.display === 'block').length`);
  const nRooms = await P.evaluate('__host.labels.length');
  check('room names from the drawing are shown over the model', shown >= Math.min(10, nRooms), { shown, rooms: nRooms });
  await P.shot(path.join(OUT, 'suite_orbit.png'));
  await P.press('Digit2');
  let s = await st();
  const clr = await P.evaluate('Math.min(99, __viewer.probe.clearance())'), onf = await P.evaluate('__viewer.probe.onFloor()');
  check('Walk starts on the floor at eye height, with room around you', s.mode === 'walk' && Math.abs(s.y - 1.6) < 0.01 && onf && clr >= 0.5, { y: r2(s.y), clearance: r2(clr), onFloor: onf });
  await P.shot(path.join(OUT, 'suite_walk.png'));

  // ------------------------------------------------------------------ the structure, with the furniture hidden
  // Walls, doors and glass are the drawing's own; the boxes are colliders, so these are judged without them. The boxes have their
  // own checks below, and the doors, the glass and the walls are walked again with them.
  if (hasFurniture) await P.evaluate(`(${pageHelpers.toString()})()`);
  await setFurniture(false);
  const walls = await P.evaluate(wallWalks(false));
  check('walking into walls at 40 random spots: never through a wall', walls.tried >= 30 && walls.wentThrough === 0 && walls.endedInsideWall === 0, walls);
  const doors = await P.evaluate(doorWalks(false));
  const blocked = doors.filter(d => !d.ok);
  check(`every door and opening can be walked through, both ways (${doors.length}; the 2 exterior doors from inside)`, doors.length > 0 && blocked.length === 0, blocked.length ? blocked : { doors: doors.length });
  const glass = await P.evaluate(glassWalk(false));
  delete glass.stoppedBy;
  check("the glass facade stops you (walking at the living room's west glass)", glass.stoppedAt > 0.1 && glass.stoppedAt < 0.6, glass);

  // ------------------------------------------------------------------ the furniture boxes, shown
  async function furnitureChecks() {
    await setFurniture(true);
    await P.evaluate('__viewer.setMode("orbit")'); await sleep(200);
    const home = await P.evaluate(`[__host.camera.position.toArray(), __host.controls.target.toArray()]`);       // the start-up view, for the screenshot with the legend
    const model = await P.evaluate(`(() => { const M = __host.model; return { kinds: M.furnitureKinds, pieces: M.furniture.map(p => [p.id, p.kind, p.floor, p.on, p.approach || []]), doors: M.doors.map(d => d.id) }; })()`);
    const nBoxes = model.pieces.length;
    const blocksKind = Object.fromEntries(model.kinds.map(k => [k.key, k.blocks !== false]));
    const inApproach = model.pieces.filter(p => p[4].length);                // the pieces the builder put in the approach of a door or an opening
    const inApproachStop = inApproach.filter(p => blocksKind[p[1]]);         // ... of the kinds that stop you (a curtain never does)
    const nStop = model.pieces.filter(p => blocksKind[p[1]]).length;         // the pieces of the kinds that stop you

    // the page was made from the model file that is next to it (the stamp is the sha1 of the file's bytes, as the 3ds Max script's is)
    const modelFile = path.join(HERE, 'src', 'pres2_model.json');
    if (URL.startsWith('file:') && existsSync(modelFile)) {
      const sha = createHash('sha1').update(readFileSync(modelFile)).digest('hex').slice(0, 12);
      const stamp = await P.evaluate(`document.querySelector('meta[name="model-data"]').content`);
      check('the page carries the model-data stamp of the current pres2_model.json (the sha1 of the file)', stamp === sha, { page: stamp, file: sha });
    }

    // (a) the legend: a row per kind of the model, with its count, its colour and the default height in the text box
    const legend = await P.evaluate(`(() => ({ title: document.querySelector('.fb-title span').textContent, master: !!document.querySelector('.fb-all'),
      keep: (b => b && { checked: b.checked, text: b.closest('label').textContent.trim(), n: document.querySelectorAll('.fb-keep').length })(document.querySelector('.fb-keep')),
      buttons: [...document.querySelectorAll('.fb-btns button')].map(b => b.innerText),
      rows: [...document.querySelectorAll('.fb-row[data-k]')].map(r => ({ k: r.dataset.k, label: r.querySelector('.fb-lab').innerText, sw: getComputedStyle(r.querySelector('.fb-sw')).backgroundColor,
        h: r.querySelector('.fb-h').value, show: r.querySelector('.fb-show').checked, blk: r.querySelector('.fb-blk').checked })) }))()`);
    const rgb = hex => `rgb(${[1, 3, 5].map(i => parseInt(hex.slice(i, i + 2), 16)).join(', ')})`;
    const legendBad = [];
    model.kinds.forEach((k, i) => {
      const r = legend.rows[i];
      if (!r || r.k !== k.key || r.label !== `${k.label} (${k.count})` || r.sw !== rgb(k.colour) || r.h !== String(k.height) || !r.show || r.blk !== k.blocks) legendBad.push([k.key, r]);
    });
    check(`the furniture legend: one row per kind of the model (${model.kinds.length}) in table order, with its count (${model.kinds.reduce((n, k) => n + k.count, 0)} boxes in all), its colour, the default height in mm in a text box, and the show and stops ticks (stops unticked for ${model.kinds.filter(k => !k.blocks).map(k => k.key).join(', ') || 'none'}); above them the tick "Keep doorways clear", ticked`,
      legend.title === 'Furniture boxes' && legend.master && legend.rows.length === model.kinds.length && !legendBad.length && legend.buttons.join('|') === 'Reset heights|Save list (CSV)'
      && legend.keep && legend.keep.checked && legend.keep.text === 'Keep doorways clear' && legend.keep.n === 1
      && model.kinds.reduce((n, k) => n + k.count, 0) === nBoxes, legendBad.length ? legendBad : legend.rows.map(r => `${r.label} ${r.h}${r.blk ? '' : ' (does not stop)'}`));

    // (b) a box per piece, in the suite's group, named furn:<kind>:<id>
    const made = await P.evaluate(`(() => { const FL = __host.FL, F = __host.furniture, pieces = Object.fromEntries(F.pieces().map(p => [p.id, p])), bad = [], names = new Set(), per = {}; let n = 0;
      for (const [key, f] of Object.entries(FL)) f.group.traverse(o => {
        if (!o.name.startsWith('furn:')) return;
        n++; names.add(o.name); per[key] = (per[key] || 0) + 1;
        const [, kind, id] = o.name.split(':'), p = pieces[id];
        if (!p || p.kind !== kind || p.floor !== key || o.parent !== f.group || F.meshOf(id) !== o) bad.push(o.name);
      });
      return { n, distinct: names.size, per, bad: bad.slice(0, 5), nBad: bad.length, sameGroup: FL.suite.group === __host.group && FL.suite.colliders === __host.floors[0].colliders,
        perModel: Object.fromEntries(Object.keys(FL).map(k => [k, F.pieces().filter(p => p.floor === k).length])) }; })()`);
    check(`the scene holds ${nBoxes} furniture boxes, each a child of the suite's group (the one Walk and the replay use) and named furn:<kind>:<id>`,
      made.n === nBoxes && made.distinct === nBoxes && made.nBad === 0 && made.sameGroup && JSON.stringify(made.per) === JSON.stringify(made.perModel), made.nBad ? made.bad : { perLevel: made.per, sameGroup: made.sameGroup });

    // the page's own controls leave the boxes alone: the ticks (applyChecks), the legend text, the Build row
    const own = await P.evaluate(`(async () => {
      const F = __host.furniture, ms = F.pieces().map(p => F.meshOf(p.id)), showing = m => { for (let n = m; n; n = n.parent) if (!n.visible) return false; return true; };
      const count = () => ms.filter(showing).length, click = id => { document.getElementById(id).click(); }, out = {};
      out.start = count();
      for (const id of ['plates', 'glass', 'rooms']) click(id);
      out.ticksOff = count();
      for (const id of ['plates', 'glass', 'rooms']) click(id);
      out.ticksOn = count();
      F.setVisible('plant', false); click('plates'); click('glass'); click('plates'); click('glass');
      out.plantHidden = count();
      F.setVisible('plant', true);
      const panel = document.getElementById('panel'), last = panel.lastElementChild, lg = panel.querySelector('.legend');
      out.panel = { fbLast: last.matches('.fb-block') || !!last.querySelector(':scope > .fb-block'), buildBefore: !!(document.getElementById('br-again').compareDocumentPosition(last) & Node.DOCUMENT_POSITION_FOLLOWING),
        legendSwatches: lg.querySelectorAll('span').length, legendHasFurniture: !!lg.querySelector('[class^=fb-]') || /furniture/i.test(lg.textContent),
        legendText: lg.textContent.startsWith('Walls and columns') && lg.textContent.endsWith('Floor slab') };
      out.ticks = ['plates', 'glass', 'rooms'].map(id => document.getElementById(id).checked);
      return out; })()`);
    check(`the page's own controls leave the boxes alone: the Floor slab / Glass / Room names ticks (and a hidden kind stays hidden through them), the legend is as it was and the furniture list is last in the panel`,
      own.start === nBoxes && own.ticksOff === nBoxes && own.ticksOn === nBoxes && own.plantHidden === nBoxes - model.kinds.find(k => k.key === 'plant').count
      && own.ticks.every(Boolean) && own.panel.fbLast && own.panel.buildBefore && !own.panel.legendHasFurniture && own.panel.legendSwatches >= 4 && own.panel.legendText, own);

    // the side panel at the two screens of a PC / laptop: it is on the screen, it scrolls (nothing runs off), the whole list can be reached and read
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
        out.cut = lab.filter(e => { const t = document.createRange(); t.selectNodeContents(e); return t.getBoundingClientRect().width > e.getBoundingClientRect().width + 0.01; }).map(e => e.textContent);       // the text is wider than its box, even by a fraction of a pixel (an ellipsis shows)
        out.panelW = Math.round(r.width);
        out.rowH = Math.round(Math.min(...rows.map(e => e.getBoundingClientRect().height))); out.fontPx = Math.min(...lab.map(e => parseFloat(getComputedStyle(e).fontSize)));
        out.boxesIn = rows.every(e => inP(e.querySelector('.fb-h')) && inP(e.querySelector('.fb-blk')) && inP(e.querySelector('.fb-show')));
        return out; })()`);
      await sleep(250);
      await P.shot(path.join(OUT, `suite_panel_${w}x${h}.png`));
      await P.evaluate(`document.getElementById('panel').scrollTop = 0`); await sleep(150);
      await P.shot(path.join(OUT, `suite_panel_${w}x${h}_top.png`));
      check(`the side panel at ${w} x ${h}: on the screen, ${m.scrolls ? 'it scrolls' : 'it fits'} (${m.content} px of content in ${m.shown}), the title and the last row with the Reset / Save buttons can be reached, ${model.kinds.length} rows at least ${m.rowH} px high and ${m.fontPx} px type, no label cut off, every height box and tick inside it, the bottom edge ${m.hintGap} px above the hint line`,
        m.onScreen && (!m.scrolls || /auto|scroll/.test(m.overflowY)) && m.titleVisible && m.lastRowReachable && m.cut.length === 0 && m.rowH >= 22 && m.fontPx >= 12 && m.boxesIn && m.hintGap >= 4, m);
    }
    // the panel never reaches under the hint line, at the heights of a laptop and a desktop screen (700 - 1080 px) and a window a little lower
    const hintGaps = [];
    for (const [w, h] of [[1366, 640], [1366, 700], [1280, 800], [1600, 900], [1920, 1080]]) {
      await tab.send('Emulation.setDeviceMetricsOverride', { width: w, height: h, deviceScaleFactor: 1, mobile: false });
      await sleep(350);
      hintGaps.push([`${w}x${h}`, await P.evaluate(`(() => { const r = document.getElementById('panel').getBoundingClientRect(); return Math.round((document.getElementById('hint').getBoundingClientRect().top - r.bottom) * 10) / 10; })()`)]);
    }
    check(`the side panel's bottom edge stays above the hint line at every window height from 640 to 1080 px (${hintGaps.map(([g, d]) => `${g}: ${d} px`).join(', ')})`, hintGaps.every(([, d]) => d >= 4), hintGaps);
    await tab.send('Emulation.clearDeviceMetricsOverride'); await sleep(500);
    await P.evaluate(`document.getElementById('panel').scrollTop = 0`);

    // (c) typing 600 into the table's height box: every table's top is at 0.60 m (looking down from 3 m at a spot on the table, the first thing met is
    // that table's top), what stands on the tables follows (the lamps on the console), what stands on the coffee tables does not, and Reset brings it all back
    const kindById = Object.fromEntries(model.pieces.map(p => [p[0], p[1]]));
    const onTables = model.pieces.filter(p => p[3] && kindById[p[3]] === 'table').map(p => p[0]), onOthers = model.pieces.filter(p => p[3] && kindById[p[3]] !== 'table').map(p => p[0]);
    const nTables = model.pieces.filter(p => p[1] === 'table').length;
    const spots = (await T(`T.topSpots('table')`)).filter(t => t.spot), tableTop = model.kinds.find(k => k.key === 'table').height / 1000;
    const readings = () => P.evaluate(`(() => { const F = __host.furniture, T = __t, pcs = Object.fromEntries(F.pieces().map(p => [p.id, p])), L = Object.fromEntries(__host.floors.map(f => [f.key, f.level]));
      return { down: ${JSON.stringify(spots)}.map(t => { const d = T.downAt(t.floor, t.spot[0], t.spot[1]); return [t.id, d && d.name === F.meshOf(t.id).name ? Math.round(d.h * 1000) / 1000 : null]; }),
        tables: F.pieces().filter(p => p.kind === 'table').map(p => [p.z0, p.z1]), on: ${JSON.stringify(onTables)}.map(id => [pcs[id].kind, pcs[id].z0, Math.round((F.meshOf(id).position.y - L[pcs[id].floor]) * 1000) / 1000]),
        others: ${JSON.stringify(onOthers)}.map(id => pcs[id].z0), box: document.querySelector('.fb-row[data-k="table"] .fb-h').value, edited: document.querySelectorAll('.fb-h.fb-edited').length,
        stored: (() => { try { return Object.keys(localStorage).filter(k => k.startsWith('walkthrough-furniture')).length; } catch (e) { return 'blocked'; } })() }; })()`);
    const before = await readings();
    await typeHeight('table', 600);
    const at600 = await readings();
    await P.shot(path.join(OUT, 'suite_furniture_table_600.png'));
    await clickSel('.fb-reset');
    const reset = await readings();
    const near = (a, b, tol = 0.006) => a !== null && Math.abs(a - b) <= tol;
    check(`typing 600 into the table height box: ${spots.length} of ${nTables} tables have their top at 0.60 m looking down on them (${tableTop.toFixed(2)} m before), the ${onTables.length} pieces standing on tables (${[...new Set(at600.on.map(o => o[0]))].join(', ')}) follow to 0.60 m, the ${onOthers.length} on coffee tables stay put; Reset brings it all back`,
      spots.length === nTables && onTables.length > 0 && onOthers.length > 0 && before.down.every(([, z]) => near(z, tableTop)) && at600.down.every(([, z]) => near(z, 0.6)) && at600.tables.every(([z0, z1]) => z0 === 0 && z1 === 0.6) && at600.box === '600' && at600.edited === 1
      && at600.on.every(([, z0, y]) => z0 === 0.6 && near(y, 0.6, 0.002)) && at600.others.every((z, i) => z === before.others[i])
      && reset.down.every(([, z]) => near(z, tableTop)) && reset.box === String(tableTop * 1000) && reset.edited === 0 && reset.on.every(([, z0]) => z0 === tableTop) && reset.stored === 0,
      { tables: spots.length, downBefore: before.down.map(u => u[1]), downAt600: at600.down.map(u => u[1]), standingOn: at600.on, onCoffeeTables: at600.others, reset: { down: reset.down.map(u => u[1]), box: reset.box, edited: reset.edited, stored: reset.stored } });

    // Walk starts clear of the boxes wherever the Orbit view was looking: from 30 spots over the suite (its whole width) the start is on the floor, has
    // 0.5 m of room around it (the boxes count) and no box holds the player: the faces are single-sided, so the start may be inside a box (the eye is above
    // it or in it, Walk's rays from inside meet nothing of it), and the player walks out of it (verdict A)
    const starts = await P.evaluate(`(() => { const v = __viewer, s = v.state, out = [];
      let seed = 11; const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
      const b = new __t.THREE.Box3().setFromObject(__host.FL.suite.group);
      for (let i = 0; i < 30; i++) {
        v.setMode('orbit'); __host.controls.target.set(b.min.x + rnd() * (b.max.x - b.min.x), 1, b.min.z + rnd() * (b.max.z - b.min.z));
        v.setMode('walk');
        const vd = __t.verdict();
        out.push({ floor: s.floor.key, clearance: Math.min(99, v.probe.clearance()), onFloor: v.probe.onFloor(), inBox: vd.inside, class: vd.class, best: vd.best });
      }
      v.setMode('orbit');
      return out; })()`);
    const badStart = starts.filter(r => r.floor !== 'suite' || !r.onFloor || r.clearance < 0.5 || r.class !== 'A');
    check(`Walk starts clear of the boxes wherever the Orbit view looks: from ${starts.length} spots over the suite the start is on the floor, has at least 0.5 m of room around it and is not held by a box (${starts.filter(r => r.inBox.length).length} start inside a box and walk out of it)`,
      starts.length === 30 && !badStart.length, badStart.length ? badStart : { leastRoom: r2(Math.min(...starts.map(r => r.clearance))), insideABox: starts.filter(r => r.inBox.length).map(r => `${r.inBox.join('+')} (${r2(r.best)} m)`) });

    // (d) Walk stops at real boxes: every shown box that stops you and that Walk's rays can meet (knee 0.35 m or chest 1.2 m), approached on a free
    // line straight at one face from 1 m (nearer where something else stands in the way: 0.8, 0.65, 0.5 m): you stop short of the face, never inside, never through
    await P.press('Digit2');
    const tg = await T(`T.targets()`);
    const walkable = tg.filter(t => t.side !== null);
    const walks = [];
    for (const t of walkable) walks.push({ ...(await T(`T.walk(__host.furniture.pieces().find(p => p.id === ${JSON.stringify(t.id)}), ${t.side}, ${t.back}, false)`)), kind: t.kind });
    const byKind = {};
    for (const t of tg) { const b = byKind[t.kind] = byKind[t.kind] || { spans: 0, tested: 0, from1m: 0 }; b.spans++; if (t.side !== null) { b.tested++; if (t.back === 1) b.from1m++; } }
    const covered = Object.keys(byKind).filter(k => byKind[k].tested > 0), noLine = Object.keys(byKind).filter(k => byKind[k].tested === 0);
    note('kinds with no free line to any of their pieces (information)', noLine.map(k => `${k} (${tg.filter(t => t.kind === k).map(t => t.why.replace(/ at [0-9.]+ m/, '')).filter((x, i, a) => a.indexOf(x) === i).join(' / ')})`));
    // A kind none of whose pieces has a free line stands behind other boxes wherever it is (the TV hangs over the sideboard under it): its first
    // piece is walked at again with the kind of the box in front of it hidden (that kind's show tick), so that its own box is seen to stop you.
    const behind = [];
    for (const k of noLine) {
      const t = tg.find(x => x.kind === k), inFront = /^meets furn:([^:]+):(\S+)/.exec(t.why) || [];
      if (!inFront[1]) { behind.push({ id: t.id, kind: k, start: false, why: t.why }); continue; }
      await F(`F.setVisible(${JSON.stringify(inFront[1])}, false)`);
      const w = await T(`(p => { const L = T.freeLine(p); return L.free ? T.walk(p, L.side, L.back, false) : { id: p.id, start: false, why: L.why }; })(__host.furniture.pieces().find(p => p.id === ${JSON.stringify(t.id)}))`);
      await F(`F.setVisible(${JSON.stringify(inFront[1])}, true)`);
      behind.push({ ...w, kind: k, inFront: inFront[2] });
    }
    const all = [...walks, ...behind], gaps = all.filter(w => w.start).map(w => w.gap), notStopped = all.filter(w => !stopped(w));
    const stopKinds = model.kinds.filter(k => k.blocks).map(k => k.key), never = stopKinds.filter(k => !byKind[k]);
    check(`Walk stops at real boxes: ${walks.length} of ${tg.length} pieces that Walk's rays can meet had a free line (${walks.filter(w => w.back === 1).length} from 1 m, the rest from 0.8 - 0.5 m), covering ${covered.length} of the ${stopKinds.length} kinds that stop you${behind.length ? '; ' + behind.map(b => `the ${b.kind} ${b.id} once the box in front of it (${b.inFront || '?'}) is hidden${b.start ? ' (from ' + b.back + ' m)' : ''}`).join(', ') : ''}; each stops short of its face (gap ${gaps.length ? r2(Math.min(...gaps)) : '-'} - ${gaps.length ? r2(Math.max(...gaps)) : '-'} m), never inside, never through`,
      walks.length >= 30 && covered.length + behind.length === stopKinds.length - never.length && notStopped.length === 0,
      notStopped.length ? notStopped : { perKind: Object.fromEntries(Object.entries(byKind).map(([k, b]) => [k, `${b.tested}/${b.spans}, ${b.from1m} from 1 m`])), behind: behind.map(b => `${b.id}: gap ${r2(b.gap)} m`) });
    note('kinds that stop you of which no piece spans a Walk ray at its default height (a step-over height or hanging above the chest ray): the box never stops you', never);
    const shot = tg.find(t => t.kind === 'table' && t.side !== null && t.back === 1) || tg.find(t => t.kind === 'table' && t.side !== null);
    if (shot) { await T(`T.walk(__host.furniture.pieces().find(p => p.id === ${JSON.stringify(shot.id)}), ${shot.side}, ${shot.back}, false)`); await sleep(700); }
    await P.shot(path.join(OUT, 'suite_furniture_walk_stop.png'));

    // the boxes in a doorway's approach in that walk: with the tick on they are no targets (the walk above left them out) and the same walk goes straight
    // on into them; with it off they are targets like the others and stop you short of their face
    const flaggedIds = inApproach.map(p => p[0]);
    check(`Keep doorways clear on: none of the ${flaggedIds.length} boxes in an approach is among the ${tg.length} pieces Walk stops at, and all of the others that Walk's rays can meet are (${tg.length} in all)`,
      flaggedIds.length > 0 && !tg.some(t => flaggedIds.includes(t.id)) && tg.length === (await F(`F.pieces().filter(p => p.blocking && ((p.z0 < 0.33 && p.z1 > 0.37) || (p.z0 < 1.18 && p.z1 > 1.22))).length`)), { listed: tg.length, flagged: flaggedIds.length });
    await F(`F.setKeepDoorways(false)`);
    const tgOff = await T(`T.targets()`);
    const fTargets = tgOff.filter(t => t.side !== null && flaggedIds.includes(t.id)), fNoLine = tgOff.filter(t => t.side === null && flaggedIds.includes(t.id));
    const fOff = [];
    for (const t of fTargets) fOff.push(await T(`T.walk(__host.furniture.pieces().find(p => p.id === ${JSON.stringify(t.id)}), ${t.side}, ${t.back}, false)`));
    await F(`F.setKeepDoorways(true)`);
    const fOn = [];
    for (const t of fTargets) fOn.push(await T(`T.walkTo(__host.furniture.pieces().find(p => p.id === ${JSON.stringify(t.id)}), ${t.side}, ${t.back}, ${t.back + 0.5})`));
    const tgOnAgain = await T(`T.targets()`);
    const pastFace = w => w.gap < -0.05;                                   // the box is no collider: the walk gets over the face line (what is behind it, a wall, may stop it a little later)
    check(`the walk-stop check for the boxes in an approach: ${fTargets.length} of the ${inApproachStop.length} that would stop you have a free line (${fTargets.map(t => t.id).join(', ')}) - with Keep doorways clear off each stops you short of its face (gap ${fOff.length ? r2(Math.min(...fOff.map(w => w.gap))) : '-'} - ${fOff.length ? r2(Math.max(...fOff.map(w => w.gap))) : '-'} m), with it on the same walk gets past the face (${fOn.length ? r2(Math.min(...fOn.map(w => -w.gap))) : '-'} - ${fOn.length ? r2(Math.max(...fOn.map(w => -w.gap))) : '-'} m inside)`,
      fTargets.length * 2 >= inApproachStop.length && fTargets.length > 0 && fOff.every(stopped) && fOn.every(pastFace) && tgOnAgain.length === tg.length,
      { off: fOff.filter(w => !stopped(w)), on: fOn.filter(w => !pastFace(w)), noFreeLine: fNoLine.map(t => `${t.id}: ${t.why}`) });

    // (e) the show tick: the same walk goes through a chair once its kind is unticked (a real click), and stops again when it is ticked
    const chairs = await T(`T.crossable('seat', 3)`);
    const walkChair = (c, through) => T(`T.walk(__host.furniture.pieces().find(p => p.id === ${JSON.stringify(c.id)}), ${c.side}, ${c.back}, ${through}, ${through ? "'seat'" : 'null'})`);
    const tick = [];
    for (const c of chairs) {
      const a = await walkChair(c, false);
      await clickSel(rowSel('seat', 'show'));
      const off = await walkChair(c, true), inCol = await F(`__host.FL[${JSON.stringify(c.floor)}].colliders.includes(F.meshOf(${JSON.stringify(c.id)})) || F.meshOf(${JSON.stringify(c.id)}).visible`);
      await clickSel(rowSel('seat', 'show'));
      const on = await walkChair(c, false);
      tick.push({ id: c.id, stops: stopped(a), through: passed(off), gone: !inCol, stopsAgain: stopped(on), from: c.back });
    }
    check(`unticking show for the chairs: the same walk (from ${chairs.map(c => c.back).join(' / ')} m) goes right through ${chairs.length} real chairs (${chairs.map(c => c.id).join(', ')}) and they leave the colliders; ticking it again, they stop you again`,
      chairs.length >= 2 && tick.every(t => t.stops && t.through && t.gone && t.stopsAgain), tick);
    // ... and the stops tick (a real click): unticked, the same walk goes right through the chairs while they stay drawn; ticked again, they stop you again
    const stopsTick = [];
    for (const c of chairs) {
      await clickSel(rowSel('seat', 'blk'));
      const off = await walkChair(c, true), now = await F(`({ inCol: __host.FL[${JSON.stringify(c.floor)}].colliders.includes(F.meshOf(${JSON.stringify(c.id)})), drawn: F.meshOf(${JSON.stringify(c.id)}).visible })`);
      await clickSel(rowSel('seat', 'blk'));
      const on = await walkChair(c, false);
      stopsTick.push({ id: c.id, through: passed(off), drawn: now.drawn, gone: !now.inCol, stopsAgain: stopped(on) });
    }
    check(`unticking stops for the chairs: the same walk goes right through the ${chairs.length} chairs while they stay drawn, and they leave the colliders; ticking it again, they stop you again`,
      chairs.length >= 2 && stopsTick.every(t => t.through && t.drawn && t.gone && t.stopsAgain), stopsTick);

    // (f) a seat typed as 300 mm is stepped over (Walk's knee ray at 0.35 m passes above it), 450 mm stops you
    const heights = [];
    for (const mm of [300, 450]) {
      await typeHeight('seat', mm);
      const w = [];
      for (const c of chairs) w.push(mm === 300 ? await walkChair(c, true) : await walkChair(c, false));
      heights.push([mm, w.every(x => (mm === 300 ? passed(x) : stopped(x))), w.map(x => x.start ? `${r2(x.moved)} m, gap ${r2(x.gap)}` : x.why)]);
    }
    await clickSel('.fb-reset');
    check(`a seat height typed as 300 mm is stepped over (the walk goes right across all ${chairs.length} chairs), 450 mm stops you (short of the face)`, heights.every(h => h[1]), heights);

    // (g) Ghost flies through real boxes that stop Walk (a table, a tall cabinet): in front of the face at half the box's height, W held until you are 0.3 m past the far face
    const ghost = [];
    for (const kind of ['table', 'tall-cabinet']) {
      await P.press('Digit2'); await P.evaluate(`document.activeElement && document.activeElement.blur()`);
      const pick = (await T(`T.targets()`)).find(t => t.kind === kind && t.side !== null);
      if (!pick) { ghost.push({ kind, ok: false, why: `no free line to a ${kind}` }); continue; }
      const pc = `__host.furniture.pieces().find(p => p.id === ${JSON.stringify(pick.id)})`;
      const stop = await T(`T.walk(${pc}, ${pick.side}, ${pick.back}, false)`);                // Walk stops short of it ...
      const L = await T(`T.lane(${pc}, ${pick.side}, 1.5, false)`);
      await P.press('Digit3');                                                                 // ... Ghost does not
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
      ghost.push({ id: pick.id, kind, walkStopsAt: r2(stop.gap), ghostEndsBeyondFace: r2(-at.rel - at.half), height: r2(at.y), inside: at.y > at.z0 && at.y < at.z1, seconds: r2((Date.now() - t1) / 1000),
        ok: stopped(stop) && at.rel < -(at.half + 0.3) && at.y > at.z0 && at.y < at.z1 });
    }
    check(`Ghost flies straight through a real table and a real tall cabinet (${ghost.map(g => g.id || g.kind).join(', ')}) at half their height, both pieces that stop Walk short of their face`, ghost.length === 2 && ghost.every(g => g.ok), ghost);
    await P.press('Digit1');

    // the doors again, with the boxes shown and Keep doorways clear on (the default): the boxes the builder put in a door's or an opening's approach are
    // no colliders, so every door and opening can be walked through its middle, both ways (the 2 exterior doors from inside), as without the boxes. A door
    // that still has some other box near its approach (the walk starts nearer, or is cut short) is counted and listed. Then the same walks with the tick off.
    await P.press('Digit2'); await P.evaluate(`document.activeElement && document.activeElement.blur()`);
    const withBoxes = await P.evaluate(doorWalks(true));
    const piecesOf = ts => [...new Set(ts.flatMap(t => (t.near || t.stoppedBy || []).map(p => `${p.id} (${p.kind}, ${String(p.family).replace(/ - .*$/, '').slice(0, 34)})`)))];
    const inWayOf = runs => {
      const out = [];
      for (const d of runs) {
        const h = doors.find(a => a.id === d.id);
        const sides = ['fwd', 'back'].filter(k => d[k] !== h[k]);
        if (!sides.length) continue;
        out.push({ id: d.id, name: d.name, ok: d.ok, structure: { fwd: h.fwd, back: h.back }, withBoxes: { fwd: d.fwd, back: d.back }, pieces: piecesOf(sides.flatMap(k => d[k + 'Tries'])) });
      }
      return out;
    };
    const inWay = inWayOf(withBoxes), cutOn = withBoxes.filter(d => !d.ok);
    for (const d of inWay) note(`${d.id} (${d.name}): a box near the approach that the builder did not flag, ${d.ok ? 'still passable' : 'CANNOT be walked through'} (without boxes ${d.structure.fwd} / ${d.structure.back} m past the door, with ${d.withBoxes.fwd} / ${d.withBoxes.back})`, d.pieces);
    check(`with the boxes on and Keep doorways clear on, every door and opening can still be walked through, both ways (${withBoxes.length}; the 2 exterior doors from inside); ${inWay.length} still have another box near their approach (${inWay.map(d => d.id).join(', ') || 'none'})`,
      withBoxes.length === doors.length && cutOn.length === 0, cutOn.length ? inWayOf(cutOn).concat(cutOn.filter(d => !inWay.some(x => x.id === d.id))) : { nearTheApproach: inWay.map(d => `${d.id} ${d.withBoxes.fwd} / ${d.withBoxes.back}`) });

    // the tick's effect, measured (information): with Keep doorways clear off the same walks are blocked at the doors the boxes block
    await F(`F.setKeepDoorways(false)`);
    const offWalks = await P.evaluate(doorWalks(true));
    await F(`F.setKeepDoorways(true)`);
    const blockedOff = offWalks.filter(d => !d.ok), shortOff = inWayOf(offWalks).filter(d => d.ok);
    const flaggedFor = id => inApproach.filter(p => p[4].includes(id)).map(p => p[0]);
    for (const d of blockedOff) note(`${d.id} (${d.name}): blocked by boxes with the tick off (without boxes ${doors.find(a => a.id === d.id).fwd} / ${doors.find(a => a.id === d.id).back} m past the line, with ${d.fwd} / ${d.back})`,
      { pieces: piecesOf(['fwd', 'back'].flatMap(k => d[k + 'Tries'])), inItsApproachList: flaggedFor(d.id) });
    for (const d of shortOff) note(`${d.id} (${d.name}): still passable with the tick off, but a box is in the way (without boxes ${d.structure.fwd} / ${d.structure.back}, with ${d.withBoxes.fwd} / ${d.withBoxes.back})`, d.pieces);
    note(`with Keep doorways clear off the boxes block ${blockedOff.length} of the ${offWalks.length} doors and openings (information)`, blockedOff.map(d => `${d.id} <- ${flaggedFor(d.id).join(', ') || 'no box flagged for it'}`));

    // (b) the colliders against the approach lists, read from the page: with the tick on every piece of a kind that stops you with a non-empty approach is
    // out of the colliders and every other one is in; with it off all of them are in (the page's lists are the model's); a curtain is never in
    const rule = await P.evaluate(`(() => { const F = __host.furniture, FL = __host.FL, M = __host.model, kb = Object.fromEntries(M.furnitureKinds.map(k => [k.key, k.blocks !== false])), out = {};
      const inCol = () => new Set(Object.values(FL).flatMap(f => f.colliders.filter(m => m.name.startsWith('furn:')).map(m => m.userData.id)));
      const state = keep => { F.setKeepDoorways(keep); const c = inCol(), ps = F.pieces(); return M.furniture.map(p => [p.id, c.has(p.id), (p.approach || []).length > 0, ps.find(q => q.id === p.id).blocking, kb[p.kind]]); };
      out.on = state(true); out.off = state(false); F.setKeepDoorways(true); out.keep = F.keepDoorways();
      out.lists = F.pieces().map(p => p.id + ':' + p.approach.join()).join('|') === M.furniture.map(p => p.id + ':' + (p.approach || []).join()).join('|');
      out.checked = document.querySelector('.fb-keep').checked; return out; })()`);
    const wrongOn = rule.on.filter(([, inCol, flagged, blocking, kb]) => inCol !== (kb && !flagged) || blocking !== inCol), wrongOff = rule.off.filter(([, inCol, , blocking, kb]) => inCol !== kb || blocking !== inCol);
    check(`the colliders against the approach lists (read from the page): with the tick on the ${inApproachStop.length} pieces with an approach of the kinds that stop you are out and the other ${nStop - inApproachStop.length} pieces of those kinds are in; with it off all ${nStop} are in; the ${nBoxes - nStop} of the kinds that do not stop you never are; pieces() says the same (blocking); the lists are the model's`,
      inApproachStop.length > 0 && rule.on.length === nBoxes && !wrongOn.length && !wrongOff.length && rule.lists && rule.keep === true && rule.checked, { wrongOn: wrongOn.slice(0, 4), wrongOff: wrongOff.slice(0, 4) });

    // the glass again with the boxes shown: it still stops you, never lets you through (a box in front of it may stop you first)
    const glassOn = await P.evaluate(glassWalk(true));
    check(`with the boxes on the glass facade still stops you (walking at the living room's west glass: ${glassOn.stoppedAt} m short of it${glassOn.stoppedBy.length ? ', at ' + glassOn.stoppedBy.map(p => p.id).join(', ') : ''})`,
      glassOn.stoppedAt > 0.1, glassOn);

    // with every wall and every box in the way: from 40 random spots outside the boxes, walking at the nearest thing never takes you through it
    const wallsOn = await P.evaluate(wallWalks(true));
    check(`with the boxes on: walking into the nearest wall or box from 40 random spots outside the boxes, never through it and never ending up inside it (${wallsOn.skippedInABox} spots inside a box skipped)`,
      wallsOn.tried >= 30 && wallsOn.wentThrough === 0 && wallsOn.endedInsideWall === 0, wallsOn);

    // (d) not trapped. The faces of a box are single-sided, so Walk's rays from inside a box meet nothing of it: Walk entered at the middle of a box (the
    // double-click path: Orbit, then Walk at the box) puts the player inside a box about every other time, and he can always walk out. verdict(): A = walks
    // out (1 m or more in some direction of 8) or is in no box; B = does not, but would with only the boxes around him (a pocket of other boxes:
    // information); C = a box holds him itself.
    const mids = await F(`F.pieces().filter(p => p.blocking).map(p => p.id)`);
    const into = await P.evaluate(`(() => { const out = [];
      for (const id of ${JSON.stringify(mids)}) { __t.spawn(id); out.push({ id, ...__t.verdict() }); }
      __viewer.setMode('orbit'); __viewer.setMode('walk'); return out; })()`);
    const heldBy = into.filter(r => r.class === 'C'), inBox = into.filter(r => r.inside.length), pockets = into.filter(r => r.class === 'B');
    note('Walk entered in a pocket of overlapping boxes (information: nothing holds the player but other boxes)', pockets.map(r => `${r.id} in ${r.inside.join('+')}: ${r2(r.best)} m, ${r2(r.alone)} m with only those boxes`));
    check(`not trapped: Walk entered at the middle of each of the ${mids.length} boxes that stop you lands the player inside a box ${inBox.length} times; ${inBox.filter(r => r.class === 'A').length} walk out at once and ${pockets.length} are in a pocket of other boxes, none is held by a box itself`,
      mids.length === nStop - inApproachStop.length && inBox.length >= 10 && heldBy.length === 0, heldBy.length ? heldBy : { inside: inBox.length, pockets: pockets.map(r => r.id) });
    // ... and from a spot where a box is switched on under the player: its kind's show tick, its stops tick, a taller height (a seat, a table, a tall
    // cabinet), the doorways tick (each of the boxes in an approach of a kind that stops you)
    const pick = (kind, flagged) => model.pieces.find(p => p[1] === kind && !!p[4].length === flagged);
    const scenarios = {};
    for (const kind of ['seat', 'table', 'tall-cabinet']) {
      const plain = pick(kind, false)[0];
      scenarios[kind] = await P.evaluate(`(() => { const F = __host.furniture, T = __t, out = {}, id = ${JSON.stringify(plain)}, kind = ${JSON.stringify(kind)};
        const run = (name, prepare, on) => { prepare(); T.standIn(id); const before = T.holding().includes(id); on(); out[name] = { id, before, ...T.verdict() }; };
        run('show', () => F.setVisible(kind, false), () => F.setVisible(kind, true));
        run('stops', () => F.setBlocks(kind, false), () => F.setBlocks(kind, true));
        run('height', () => F.setHeight(kind, 100), () => F.setHeight(kind, 450));
        F.reset(); return out; })()`);
    }
    const doorwaysAll = await P.evaluate(`(() => { const F = __host.furniture, T = __t, out = [];
      for (const p of F.pieces().filter(q => q.approach.length && q.blocks)) { F.setKeepDoorways(true); T.standIn(p.id); const before = T.holding().includes(p.id); F.setKeepDoorways(false); out.push({ id: p.id, before, ...T.verdict() }); }
      F.setKeepDoorways(true); return out; })()`);
    const scAll = Object.entries(scenarios).flatMap(([kind, sc]) => Object.entries(sc).map(([name, r]) => ({ label: `${kind}/${name}`, ...r })));
    const around = r => r.before === false && r.inside.includes(r.id);                         // the box was no obstacle to the player at the middle of it, and it is around him now
    check(`not trapped: a box switched on under the player (the show tick, the stops tick, typed taller: 100 -> 450 mm; a seat, a table, a tall cabinet: ${scAll.length} cases) does not hold him, nor does any of the ${doorwaysAll.length} boxes in an approach that would stop you when the doorways tick is switched off under him`,
      scAll.every(r => around(r) && r.class !== 'C') && doorwaysAll.length === inApproachStop.length && doorwaysAll.every(r => around(r) && r.class !== 'C'),
      { held: [...scAll, ...doorwaysAll].filter(r => r.class === 'C').map(r => r.label || r.id), notAround: [...scAll, ...doorwaysAll].filter(r => !around(r)).map(r => r.label || r.id), pockets: [...scAll, ...doorwaysAll].filter(r => r.class === 'B').map(r => r.label || r.id) });
    await P.press('Digit1');

    // (h) the family list the page writes is the file the builder wrote (without its byte-order mark), byte for byte
    const csvFile = path.join(HERE, 'presidential_furniture_list.csv');
    if (existsSync(csvFile)) {
      await F(`F.reset()`);
      const page = Buffer.from(await F('F.csv()'), 'utf8'), file = readFileSync(csvFile), bom = file.subarray(0, 3).equals(Buffer.from([0xEF, 0xBB, 0xBF]));
      const same = bom && page.equals(file.subarray(3));
      const noted = page.toString('utf8').split('\r\n').filter(l => l.includes('in the approach of')).length;         // the notes say which door's approach a box stands in
      check(`the page's csv() is presidential_furniture_list.csv without its byte-order mark, byte for byte (${page.length} bytes, ${(page.toString('utf8').match(/\r\n/g) || []).length - 1} rows), and ${noted} of its rows carry "in the approach of ..." (one per box in an approach: ${inApproach.length})`,
        same && noted === inApproach.length, same ? { identical: true, noted } : { page: page.length, file: file.length - 3, bom, firstDifference: [...page].findIndex((b, i) => b !== file[i + 3]) });
    } else note('presidential_furniture_list.csv is not next to the test: the family list was not compared');

    // (j) the label under the pointer in Orbit, over real boxes: kind, family, size and the level; over a box in a doorway's approach also why it does not stop you
    await P.press('Digit1'); await sleep(500);
    const spotsHover = await T(`T.hoverSpots('suite', 4)`);
    const spotsDoor = await T(`T.hoverSpots('suite', 1, ${JSON.stringify(inApproachStop.map(p => p[0]))})`);
    const tipNow = () => P.evaluate(`(() => { const t = document.querySelector('.fb-tip'); return t && t.style.display === 'block' ? t.innerText : null; })()`);
    const floorName = await P.evaluate('__host.floors[0].name');
    const hovers = [];
    for (const sp of [...spotsHover, ...spotsDoor]) {
      await P.mouse('mouseMoved', 1250, 40, { button: 'none' });
      for (let i = 0; i < 20 && (await tipNow()) !== null; i++) await sleep(100);
      await P.mouse('mouseMoved', sp.x, sp.y, { button: 'none' });
      let tip = null;
      for (let i = 0; i < 30 && tip === null; i++) { await sleep(100); tip = await tipNow(); }
      const label = model.kinds.find(k => k.key === sp.kind).label, door = spotsDoor.includes(sp);
      const flat = x => String(x).replace(/\s+/g, ' '), text = tip && flat(tip);                // the label's lines are one run of text to compare
      const why = `does not stop you: in the approach of ${sp.approach.join(', ')}`;
      hovers.push({ id: sp.id, kind: sp.kind, door, ok: !!tip && text.includes(label) && text.includes(flat(sp.family)) && text.includes(sp.size) && text.includes(floorName) && text.includes(why) === door, tip: text });
      if (sp === spotsHover[0]) await P.shot(path.join(OUT, 'suite_furniture_hover.png'));
      if (door) await P.shot(path.join(OUT, 'suite_furniture_hover_doorway.png'));
    }
    check(`Orbit: the pointer over ${spotsHover.length} real boxes of different kinds (${spotsHover.map(h => h.kind).join(', ')}) shows a label with the kind, the family, the size and the level; over ${spotsDoor.length} box in a doorway's approach (${spotsDoor.map(h => h.id).join(', ')}) it also says it does not stop you and why`,
      spotsHover.length >= 3 && spotsDoor.length === 1 && hovers.every(h => h.ok), hovers.map(h => h.ok ? `${h.kind}: ${h.tip}` : h));
    await P.mouse('mouseMoved', 1250, 40, { button: 'none' });

    // the replay's restore hook: a kind hidden before a replay is hidden again after it (the replay shows every late object at its end)
    const rep = await P.evaluate(`(() => { const F = __host.furniture, ms = F.pieces().map(p => F.meshOf(p.id)), out = {};
      F.setVisible('plant', false); F.setBlocks('seat', false);
      __build.seek(0); out.start = ms.filter(m => m.visible).length;
      __build.seek(1); out.end = ms.filter(m => m.visible).length;
      __build.skip(); out.phase = __build.phase;
      const k = Object.fromEntries(F.kinds().map(x => [x.key, x]));
      out.wrong = F.pieces().filter(p => F.meshOf(p.id).visible !== k[p.kind].visible).length;
      out.cols = [...new Set(Object.values(__host.FL).flatMap(f => f.colliders.filter(m => m.name.startsWith('furn:')).map(m => m.userData.kind)))];
      out.opaque = ms.every(m => m.material.opacity === 1 && !m.material.transparent);
      F.setVisible('plant', true); F.setBlocks('seat', true);
      return out; })()`);
    check('replaying the build and skipping to its end: the boxes are not there at the start and all of them are at the end, then the page puts back what you had (plants hidden, chairs not stopping you)',
      rep.start === 0 && rep.end === nBoxes && rep.phase === 'done' && rep.wrong === 0 && rep.opaque && !rep.cols.includes('plant') && !rep.cols.includes('seat') && rep.cols.includes('table'), rep);
    // ... and the doorways rule: after a replay the boxes in an approach (of the kinds that stop you) are still no colliders (tick on) or colliders again (tick off)
    const repDoor = await P.evaluate(`(() => { const F = __host.furniture, FL = __host.FL, fl = F.pieces().filter(p => p.approach.length && p.blocks), plain = F.pieces().filter(p => !p.approach.length && p.blocks),
        inCol = p => FL[p.floor].colliders.includes(F.meshOf(p.id)), out = {};
      __build.seek(0); __build.seek(1); __build.skip(); out.on = fl.map(inCol); out.plainIn = plain.every(inCol);
      F.setKeepDoorways(false); __build.seek(0); __build.seek(1); __build.skip(); out.off = fl.map(inCol); out.n = fl.length; F.setKeepDoorways(true); return out; })()`);
    check(`after a replay the doorways rule still holds: with the tick on the ${repDoor.n} boxes in an approach that would stop you are no colliders and every other box of a kind that stops you is one, with it off the ${repDoor.n} are colliders`,
      repDoor.n === inApproachStop.length && repDoor.on.every(x => !x) && repDoor.plainIn && repDoor.off.every(Boolean), repDoor);

    // screenshots: Orbit with the legend, a close-up of the bedroom, Walk at the bed (or the dining table)
    await P.evaluate(`__viewer.setMode('orbit')`);
    await P.evaluate(`(() => { __host.camera.position.fromArray(${JSON.stringify(home[0])}); __host.controls.target.fromArray(${JSON.stringify(home[1])}); __host.controls.update(); })()`);
    await P.evaluate(`document.querySelector('.fb-block').scrollIntoView({ block: 'start' })`); await sleep(500);
    await P.shot(path.join(OUT, 'suite_furniture_orbit.png'));
    const bedroom = await P.evaluate(`(() => { const bed = __host.furniture.pieces().find(p => p.kind === 'bed');
      // the room the bed is in: the room name nearest to it; seen from high above its north-east side (the usual view's side has a column in front of the bed)
      const room = [...__host.labels].sort((a, b) => Math.hypot(a.p.x - bed.x, a.p.z + bed.y) - Math.hypot(b.p.x - bed.x, b.p.z + bed.y))[0];
      return { bed: bed.id, room: room.el.textContent, camera: __t.lookAt(new __t.THREE.Vector3(room.p.x, 0.5, room.p.z), [[3.5, 10], [3, 9]], -60) }; })()`);
    await sleep(700);
    await P.shot(path.join(OUT, 'suite_furniture_bedroom.png'));
    note('close-up of the bedroom (Orbit)', bedroom);
    await P.evaluate(`__viewer.setMode('orbit')`);
    await P.press('Digit2'); await P.evaluate(`document.activeElement && document.activeElement.blur()`);
    const view = await P.evaluate(`(() => { const F = __host.furniture, pcs = F.pieces(), s = __viewer.state;
      // the bed, else the table the most chairs stand round (the dining table is drawn loose, so its kind is 'other')
      const chairsBy = t => pcs.filter(p => p.kind === 'seat' && Math.hypot(p.x - t.x, p.y - t.y) < Math.max(t.w, t.d) / 2 + 0.8).length;
      const tables = pcs.filter(p => (p.kind === 'other' || p.kind === 'table') && p.blocking).sort((a, b) => chairsBy(b) - chairsBy(a));
      for (const t of [pcs.find(p => p.kind === 'bed'), ...tables.slice(0, 2)]) for (const back of [1.8, 1.4, 1.1, 0.9]) for (const side of [2, 3, 0, 1]) {
        const L = __t.lane(t, side, back, false);
        if (!L.free) continue;
        s.pos.x = L.start[0]; s.pos.z = L.start[1]; s.yaw = Math.atan2(L.n[0], L.n[2]); s.pitch = -0.2;
        return { piece: t.id, family: t.family, side, back };
      }
      return null; })()`);
    await sleep(700);
    await P.shot(path.join(OUT, 'suite_furniture_walk.png'));
    note('Walk at the bed (or the dining table)', view);
    await P.press('Digit1');
  }
  if (hasFurniture) await furnitureChecks();
  else note('this page has no furniture boxes: the furniture checks were skipped');
  await setFurniture(true);

  // ------------------------------------------------------------------ Ghost, Camera, stamp, errors
  await P.press('Digit2'); await P.press('Digit3');
  const a = await st(); await P.hold('KeyW', 1500); const b = await st();
  check('Ghost flies (through walls)', Math.hypot(a.x - b.x, a.z - b.z) > 1.5, { moved: r2(Math.hypot(a.x - b.x, a.z - b.z)) });
  await P.press('Digit1');
  await clickSel('#vm-cam-btn'); await P.press('KeyP'); await sleep(2500);
  const t = await P.evaluate(`(document.querySelector('#vm-photos img') || {}).title || ''`);
  check('the Camera takes a 1920 x 1280 photo named after the project', /^Presidential_Orbit_overview_.*\(1920 x 1280\)/.test(t), t.slice(0, 80));
  // The viewer and the 3ds Max script beside it must come from the same model data (the generators stamp its sha1 in both).
  if (URL.startsWith('file:')) {
    const page = fileURLToPath(URL), ms = path.join(path.dirname(page), 'Presidential_Suite.ms');
    const sa = (readFileSync(page, 'utf8').match(/name="model-data" content="([0-9a-f]+)"/) || [])[1];
    const sb = existsSync(ms) ? (readFileSync(ms, 'utf8').match(/model data ([0-9a-f]+)/) || [])[1] : 'no .ms file';
    check('the viewer and the 3ds Max script were made from the same model data', sa && sa === sb, { viewer: sa, maxScript: sb });
  }
  flush();
  check('no page errors', !errors.length, errors);
} catch (e) {
  check('the test ran to the end', false, String(e && e.stack || e).slice(0, 700));
} finally {
  console.log(`\n${results.filter(Boolean).length} passed, ${results.filter(x => !x).length} failed  (${Math.round((Date.now() - t0) / 1000)} s; screenshots in ${OUT})`);
  await close();
}
process.exit(results.every(Boolean) ? 0 : 1);
