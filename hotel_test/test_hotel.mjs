// Checks the hotel page (read from two floor-plan PICTURES, no CAD: the walls, doors, glass, stairs, rooms and furniture of
// hotel_model.json) in headless Edge: the page opens without errors, room names (none overlapping), the floor buttons, Walk on
// both floors (it starts on Floor 1 at eye height with room around you, walls stop you, every door and passage lets you through
// its middle both ways - exterior ones from inside -, the glazing stops you, the lift doors are open 1.00 m with walls round
// the shafts, Floor 2 is floor where its plate is and open over the stair and the shafts), the door heads and the steps, Ghost
// through a wall, the Camera's photo name, the 'Plan picture' tick (the pictures are the source files, they lie on their floor
// plates, and the picture's walls are under the model's walls), and the model-data stamp shared with the 3ds Max script.
// What the owner's answers of 2 Nov changed has checks of its own: both stairs (the iconic one from Floor 1 lands on Floor 2, whose
// slab is open over its flight and only there, with no tread lines floating over the opening; the upper one rises from Floor 2
// toward a floor 3 not drawn), the hatches (the serving hatch and the food lift's), the forecourt (floor; the entrance can be walked out and in), the railings
// on the terrace's edges and round the open stair (they stop you), no lamp boxes on the pictures' light symbols, the sculptural
// seating (kind seat), and the check-in seating (no computer box left: the five seat backs stand at the rims of the round sofa
// and the sofa). The furniture boxes (one per piece, coloured by kind) have the bank page's checks: the legend and a height text box per kind (typed
// into with real key events), one box per piece in its floor's group, Walk stopped by real pieces (from 1 m or a little nearer,
// short of the face, never inside), Walk starting clear of them, the show tick, a step-over height, Ghost through a table and a
// counter, the family list against the builder's file, the label under the pointer in Orbit, the side panel at 1366 x 768 and
// 1920 x 1080, 'Keep doorways clear' and the doors and the glass with the boxes in front of them. The structure checks run with
// every kind of furniture hidden (the boxes are colliders); then the doors and the glass are walked again with the boxes shown.
// Usage (from the project folder): node hotel_test/test_hotel.mjs
// HOTEL_URL points it at another build of the page; HOTEL_PORT (default 9421), HOTEL_PROFILE and HOTEL_OUT set the debugging
// port, the browser profile and the screenshot folder (both under %TEMP%\hotel-test unless given); EDGE another browser (see
// viewer-modes/cdp.mjs). The test stops at once if something already answers on the port (another session's browser): the
// shared launcher would attach to that browser and finally close it.
import { mkdirSync, readFileSync, existsSync } from 'node:fs';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { tmpdir } from 'node:os';
import { createHash } from 'node:crypto';
import path from 'node:path';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const CDP = [path.join(HERE, '..', 'viewer-modes', 'cdp.mjs')].find(p => existsSync(p));
const { launch, pageApi, sleep } = await import(pathToFileURL(CDP).href);
const TMP = path.join(tmpdir(), 'hotel-test');
const OUT = process.env.HOTEL_OUT || path.join(TMP, 'out');
mkdirSync(OUT, { recursive: true });
const URL = process.env.HOTEL_URL || pathToFileURL(path.join(HERE, 'hotel_3d_preview.html')).href;
const PORT = Number(process.env.HOTEL_PORT || 9421);
let busy = true;
try { await fetch(`http://127.0.0.1:${PORT}/json/version`, { signal: AbortSignal.timeout(1500) }); } catch { busy = false; }
if (busy) {
  console.error(`Port ${PORT} already answers (another browser is using it). Close it or set HOTEL_PORT to a free port.`);
  process.exit(2);
}
const results = [];
const check = (name, ok, info) => { results.push(!!ok); console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${info !== undefined ? '   ' + JSON.stringify(info) : ''}`); };
const note = (name, info) => console.log(`      ${name}${info !== undefined ? ': ' + JSON.stringify(info) : ''}`);
const r2 = v => Math.round(v * 100) / 100;
const t0 = Date.now();
const { tab, close } = await launch({ port: PORT, profile: process.env.HOTEL_PROFILE || path.join(TMP, 'profile') });
const P = pageApi(tab);
const st = () => P.evaluate(`(() => { const s = __viewer.state; return { mode: s.mode, floor: s.floor.key, level: s.floor.level, x: s.pos.x, y: s.pos.y, z: s.pos.z }; })()`);
const visible = () => P.evaluate('JSON.stringify(__viewer.probe.visible())');
const hasOn = sel => P.evaluate(`!!(document.querySelector(${JSON.stringify(sel)}) || {}).classList?.contains('on')`);
const errs = () => P.logs.filter(l => /exception|error/i.test(l));
const errors = [];                                      // page errors of the pages already left (P.goto clears the log)
const flush = () => { errors.push(...errs()); P.logs.length = 0; };
const boxesOf = `[...document.querySelectorAll('.room')].filter(e => e.style.display === 'block').map(e => { const r = e.getBoundingClientRect(); return [e.textContent, r.left, r.top, r.right, r.bottom]; })`;
const overlaps = bs => { const o = []; for (let i = 0; i < bs.length; i++) for (let j = i + 1; j < bs.length; j++) { const a = bs[i], b = bs[j]; if (a[1] < b[3] - 0.5 && b[1] < a[3] - 0.5 && a[2] < b[4] - 0.5 && b[2] < a[4] - 0.5) o.push([a[0], b[0]]); } return o; };
// the furniture boxes: how many show (their own switch and their floor's), and the switch for all kinds at once (no furniture, no effect)
const boxesShown = `(() => { let n = 0; for (const f of Object.values(__host.FL)) f.group.traverse(o => { if (o.name.startsWith('furn:') && o.visible) n++; }); return n; })()`;
const setFurniture = on => P.evaluate(`(() => { const F = __host.furniture; if (F) F.kinds().forEach(k => F.setVisible(k.key, ${on})); })()`);
const picturesShown = `__host.pictures.objs.filter(m => m.visible).map(m => m.userData.key).sort().join(',')`;

// Walk through every door and passage of the floor you are on: from in front of each (0.9 m, or nearer when the room is small: a
// WC, a lift), walk straight through its middle; you should come out at least 0.3 m on the other side. Exterior ones (one side
// off the floor plate: the forecourt, the car park, a lift shaft above the ground floor, the key-access door at the picture's top
// edge) only have to be reachable from inside: you get to the door line. why: also say what is in the way.
const doorWalks = why => `(() => { const v = __viewer, s = v.state, keep = s.pos.clone(), out = [];
      const num = x => typeof x === 'number';
      for (const d of __host.openings) {
        if (d.floor !== s.floor.key || (d.kind !== 'door' && d.kind !== 'passage')) continue;
        const r = { id: d.id, kind: d.kind, exterior: !!d.exterior };
        for (const sign of [1, -1]) {
          const nx = d.nx * sign, ny = d.ny * sign, deg = Math.atan2(-nx, ny) * 180 / Math.PI;
          let along = null; const tries = [];
          for (const back of [0.9, 0.7, 0.55, 0.45, 0.4]) {          // a start spot on the floor, clear of walls
            s.pos.x = d.x - nx * back; s.pos.z = -(d.y - ny * back);
            const onFloor = v.probe.onFloor(), clr = v.probe.clearance();
            if (!onFloor || clr < 0.25) { tries.push({ back, onFloor, clearance: Math.round(Math.min(9, clr) * 100) / 100, ...(${!!why} ? { near: __t.near(d.floor, s.pos.x, s.pos.z, 0.3) } : {}) }); continue; }
            v.probe.walk(deg, back * 2);
            along = (s.pos.x - d.x) * nx + (-s.pos.z - d.y) * ny;      // metres past the opening's line
            if (${!!why}) tries.push({ back, along: Math.round(along * 100) / 100, stoppedBy: __t.stoppedBy(d.floor, s.pos.x, s.pos.z, deg) });
            break;
          }
          r[sign > 0 ? 'fwd' : 'back'] = along === null ? 'no start' : Math.round(along * 100) / 100;
          if (${!!why} || along === null) r[sign > 0 ? 'fwdTries' : 'backTries'] = tries;
        }
        r.ok = d.exterior ? [r.fwd, r.back].some(x => num(x) && x > -0.15) : num(r.fwd) && num(r.back) && r.fwd > 0.3 && r.back > 0.3;
        out.push(r);
      }
      s.pos.copy(keep); return out; })()`;
// Walk straight at the glass from in front of it (1.0 m, or nearer), as far as you get: how short of the glass you stop, and what is
// straight ahead of you then (the glass, or something in front of it).
const glassWalks = why => `(() => { const v = __viewer, s = v.state, keep = s.pos.clone(), out = [];
      for (const g of __host.probes) {
        if (g.floor !== s.floor.key) continue;
        for (const side of g.inside) {
          const nx = g.nx * side, ny = g.ny * side, deg = Math.atan2(nx, -ny) * 180 / Math.PI;   // facing the glass
          let res = null, ahead = null; const tries = [];
          for (const back of [1.0, 0.8, 0.6]) {
            s.pos.x = g.x + nx * back; s.pos.z = -(g.y + ny * back);
            const onFloor = v.probe.onFloor(), clr = v.probe.clearance();
            if (!onFloor || clr < 0.25) { tries.push({ back, onFloor, clearance: Math.round(Math.min(9, clr) * 100) / 100, ...(${!!why} ? { near: __t.near(g.floor, s.pos.x, s.pos.z, 0.3) } : {}) }); continue; }
            v.probe.walk(deg, 2.0);
            res = Math.round(((s.pos.x - g.x) * nx + (-s.pos.z - g.y) * ny) * 100) / 100;   // metres short of the glass
            const h = __host.rayHit(g.floor, s.pos.x, -s.pos.z, 1.2, -nx, -ny, 1.5);
            ahead = h ? h.name + ' at ' + h.d.toFixed(2) + ' m' : 'nothing';
            if (${!!why}) tries.push({ back, res, stoppedBy: __t.stoppedBy(g.floor, s.pos.x, s.pos.z, deg) });
            break;
          }
          out.push({ id: g.id, what: g.what, side, stoppedAt: res, ahead, ok: res !== null && res > 0.1 && res < 0.6, tries });
        }
      }
      s.pos.copy(keep); return out; })()`;
// Walk into the nearest wall from 40 random spots: never end up on the other side or inside it. outsideBoxes (the boxes shown, as on the
// presidential page): a spot inside a box that stops you is no start - its single-sided faces are not seen from inside, so the spot looks
// free and the walk out of it ends against its outer face (being inside a box is the 'not trapped' checks' business): such spots are
// counted and skipped.
const wallWalks = outsideBoxes => `(() => { const v = __viewer, s = v.state, keep = s.pos.clone(); let seed = 7, n = 0, through = 0, stuck = 0, tries = 0, inBox = 0;
      const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
      let x0 = Infinity, x1 = -Infinity, z0 = Infinity, z1 = -Infinity;
      for (const o of s.floor.group.children) { if (!o.geometry) continue; o.geometry.computeBoundingBox(); const g = o.geometry.boundingBox;
        x0 = Math.min(x0, g.min.x); x1 = Math.max(x1, g.max.x); z0 = Math.min(z0, g.min.z); z1 = Math.max(z1, g.max.z); }
      while (n < 40 && tries++ < 8000) {
        s.pos.x = x0 + rnd() * (x1 - x0); s.pos.z = z0 + rnd() * (z1 - z0);
        if (!v.probe.onFloor() || v.probe.clearance() < 0.6) continue;
        if (${!!outsideBoxes} && __t.holding().length) { inBox++; continue; }
        const d = [...Array(72)].map((_, i) => v.probe.open(i * 5)); let k = 0; d.forEach((x, j) => { if (x < d[k]) k = j; });
        if (d[k] > 2.5) continue;
        const a = s.pos.clone(); v.probe.walk(k * 5, d[k] + 1);
        n++; if (v.probe.crosses(a.x, a.z, s.pos.x, s.pos.z)) through++; if (v.probe.clearance() < 0.15) stuck++;
      }
      s.pos.copy(keep); return Object.assign({ floor: s.floor.key, tried: n, wentThrough: through, endedInsideWall: stuck }, ${!!outsideBoxes} ? { skippedInABox: inBox } : {}); })()`;

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
const stopped = w => w.start && w.gap >= 0.1 && w.gap <= 0.5 && !w.inside && w.moved >= 0.1;       // short of the face (Walk stops at ~0.3 m), never inside, never through
const passed = w => w.start && w.moved >= w.metres - 0.01 && w.gap < -0.2;                          // right across it and out the other side

// In the page: what the checks read out of it. Runs inside the page (its THREE comes from the page's import map).
// A "lane" is a walk straight at a face of a box (side 0 / 1: the ends along the long axis, 2 / 3: the long faces) from a spot
// back metres in front of it: free when there is floor all the way and Walk's own rays (knee and chest height, across the
// shoulders) meet nothing but that box. The plan pictures are read through the sheet itself: a ray straight down onto it gives
// its uv there, and the uv the pixel of the picture (drawn once into a canvas).
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
  // per piece of a kind: a plan spot on its top where looking straight down from 2.5 m meets that piece's own top (nothing stands on it
  // there). Down, not up: a box's faces are single-sided, so a ray from inside it (up from 0.2 m) meets none of them.
  function topSpots(kind) {
    return F.pieces().filter(p => p.kind === kind).map(p => {
      const r = p.rot * Math.PI / 180, ax = [Math.cos(r), Math.sin(r)], az = [-Math.sin(r), Math.cos(r)];
      const spot = [[0, 0], [p.w / 4, 0], [-p.w / 4, 0], [0, p.d / 4], [0, -p.d / 4]].map(([a, b]) => [p.x + ax[0] * a + az[0] * b, p.y + ax[1] * a + az[1] * b])
        .find(([x, y]) => Math.abs((__host.downHit(p.floor, x, y, 2.5) ?? -1) - p.z1) < 0.005);
      return { id: p.id, floor: p.floor, spot: spot || null };
    });
  }
  // a level ray at h above the floor: the first collider it meets (drawnOnly: leave out the invisible walk skins), or null
  function reach(floor, x, y, h, dx, dy, far, drawnOnly) {
    const cols = __host.FL[floor].colliders.filter(m => m.visible && (!drawnOnly || m.material.visible !== false)), n = Math.hypot(dx, dy);
    ray.set(new V3(x, levelOf(floor) + h, -y), new V3(dx / n, 0, -dy / n)); ray.far = far;
    const hit = ray.intersectObjects(cols, false)[0];
    return hit ? { d: Math.round(hit.distance * 1000) / 1000, name: hit.object.name } : null;
  }
  // the free width of an opening along its line at h: the distances to its two jambs (the nearest of five rays spread across the wall's
  // thickness, so a jamb a few cm off the opening's middle line is met too), or null where no ray meets anything in 3 m
  function span(d, h, drawnOnly) {
    const side = (ux, uy) => [-0.4, -0.2, 0, 0.2, 0.4].map(t => reach(d.floor, d.x + d.nx * t * d.wallThickness, d.y + d.ny * t * d.wallThickness, h, ux, uy, 3, drawnOnly))
      .filter(Boolean).sort((p, q) => p.d - q.d)[0] || null;
    const a = side(d.ny, -d.nx), b = side(-d.ny, d.nx);
    return a && b ? { width: Math.round((a.d + b.d) * 1000) / 1000, jambs: [a.d, b.d], what: [a.name, b.name] } : null;
  }
  function hoverSpots(floor, max) {                                  // boxes the Orbit camera sees (nothing in front of their top), as pointer positions, one per kind
    const cam = __host.camera, seen = new Set(), out = [], want = new THREE.Vector2();
    const showing = o => { for (let n = o; n; n = n.parent) if (!n.visible) return false; return true; };
    const hides = Object.values(__host.FL).flatMap(f => f.colliders.concat(f.walkables)).filter(m => showing(m) && !m.name.startsWith('furn:'));
    const boxes = F.pieces().map(b => F.meshOf(b.id)).filter(showing);
    const mine = F.pieces().filter(p => p.floor === floor && p.visible).sort((a, b) => b.w * b.d - a.w * a.d);
    for (const p of mine) {
      if (seen.has(p.kind)) continue;
      const m = F.meshOf(p.id), q = new V3(p.x, levelOf(floor) + p.z1, -p.y).project(cam);
      const x = (q.x + 1) / 2 * innerWidth, y = (1 - q.y) / 2 * innerHeight;
      if (q.z > 1 || x < 400 || x > innerWidth - 20 || y < 50 || y > innerHeight - 70) continue;
      ray.setFromCamera(want.set(q.x, q.y), cam); ray.far = Infinity;
      const hit = ray.intersectObjects(hides.concat(boxes), false)[0];
      if (hit && hit.object === m) { seen.add(p.kind); out.push({ ...brief(p), floor, x, y, size: `${p.w.toFixed(2)} × ${p.d.toFixed(2)} × ${(p.z1 - p.z0).toFixed(2)} m` }); }
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
  // ---- the plan pictures
  const pic = key => __host.pictures.objs.find(o => o.userData.key === key);
  function pixels(m) {                                               // the picture's own pixels (RGBA), drawn once into a canvas
    if (!m.userData.pixels) {
      const img = m.material.map.image, c = document.createElement('canvas');
      c.width = img.naturalWidth; c.height = img.naturalHeight;
      const g = c.getContext('2d'); g.drawImage(img, 0, 0);
      m.userData.pixels = g.getImageData(0, 0, c.width, c.height).data;
    }
    return m.userData.pixels;
  }
  function lumAt(key, x, y) {                                        // the picture's luminance (0 - 255) under plan (x, y), read through the sheet; null off the sheet
    const m = pic(key), [W, H] = m.userData.size;
    ray.set(new V3(x, levelOf(key) + 1, -y), new V3(0, -1, 0)); ray.far = 2;
    const hit = ray.intersectObject(m, false)[0];
    if (!hit || !hit.uv) return null;
    const px = Math.min(W - 1, Math.floor(hit.uv.x * W)), py = Math.min(H - 1, Math.floor((1 - hit.uv.y) * H)), d = pixels(m), i = (py * W + px) * 4;
    return 0.2126 * d[i] + 0.7152 * d[i + 1] + 0.0722 * d[i + 2];
  }
  function wallCorners(key) {                                        // the convex corners of the model's wall outlines (60 - 120 degrees, both edges 0.15 m or more), with the bisector into the wall
    const out = [];
    for (const p of __host.model.parts) {
      if (p.floor !== key || p.kind !== 'wall') continue;
      [p.o, ...p.h].forEach((ring, ri) => {
        const n = ring.length; let area = 0;
        for (let i = 0; i < n; i++) { const a = ring[i], b = ring[(i + 1) % n]; area += a[0] * b[1] - b[0] * a[1]; }
        for (let i = 0; i < n; i++) {
          const a = ring[(i - 1 + n) % n], b = ring[i], c = ring[(i + 1) % n];
          const e1 = [b[0] - a[0], b[1] - a[1]], e2 = [c[0] - b[0], c[1] - b[1]], l1 = Math.hypot(e1[0], e1[1]), l2 = Math.hypot(e2[0], e2[1]);
          if (l1 < 0.15 || l2 < 0.15) continue;
          let convex = (e1[0] * e2[1] - e1[1] * e2[0] > 0) === (area > 0);
          if (ri > 0) convex = !convex;                              // a hole's ring: the wall is outside it
          const ang = Math.acos(Math.max(-1, Math.min(1, -(e1[0] * e2[0] + e1[1] * e2[1]) / (l1 * l2)))) * 180 / Math.PI;
          if (!convex || ang < 60 || ang > 120) continue;
          let bx = -e1[0] / l1 + e2[0] / l2, by = -e1[1] / l1 + e2[1] / l2; const bl = Math.hypot(bx, by);
          out.push({ at: b, into: [bx / bl, by / bl] });
        }
      });
    }
    return out;
  }
  // A corner lines up when the picture 6 cm inside it (along the bisector) is darker by 30 or more (of 255) than 15 cm outside it: the
  // picture's wall is under the model's wall. dx, dy: read the picture that far off (a picture laid that far the other way).
  function lineUp(key, dx = 0, dy = 0) {
    const out = { n: 0, ok: 0, misses: [] };
    for (const c of wallCorners(key)) {
      const [x, y] = c.at, [bx, by] = c.into;
      const a = lumAt(key, x + bx * 0.06 + dx, y + by * 0.06 + dy), b = lumAt(key, x - bx * 0.15 + dx, y - by * 0.15 + dy);
      if (a === null || b === null) continue;
      out.n++;
      if (a <= b - 30) out.ok++; else if (!dx && !dy) out.misses.push({ at: [Math.round(x * 100) / 100, Math.round(y * 100) / 100], wall: Math.round(a), beside: Math.round(b) });
    }
    out.share = out.n ? Math.round(out.ok / out.n * 1000) / 1000 : 0;
    return out;
  }
  // Along every face of the model's walls, a spot every 5 cm (from 5 cm after a corner to 2 cm before the next): the picture 4 cm inside the wall
  // against 12 cm outside it. A spot counts when exactly one side of the face is wall (4 cm off it) and the spot outside is in no wall. dx, dy: read
  // the picture that far off. contrast: the mean of (outside - inside), 0 - 255; share: the spots where the inside is darker by 30 or more.
  const wallCache = {}, spotCache = {};
  const wallsOf = key => wallCache[key] || (wallCache[key] = __host.model.parts.filter(p => p.floor === key && p.kind === 'wall').map(p => {
    const xs = p.o.map(q => q[0]), ys = p.o.map(q => q[1]);
    return { rings: [p.o, ...p.h], box: [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)] }; }));
  function inWall(key, x, y) {                                       // even-odd over the part's outline and holes, any wall of the floor
    for (const w of wallsOf(key)) {
      if (x < w.box[0] || x > w.box[2] || y < w.box[1] || y > w.box[3]) continue;
      let c = false;
      for (const ring of w.rings) for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) { const [xi, yi] = ring[i], [xj, yj] = ring[j]; if ((yi > y) !== (yj > y) && x < xi + (y - yi) * (xj - xi) / (yj - yi)) c = !c; }
      if (c) return true;
    }
    return false;
  }
  function faceSpots(key) {
    if (spotCache[key]) return spotCache[key];
    const out = [];
    for (const w of wallsOf(key)) for (const ring of w.rings) for (let i = 0; i < ring.length; i++) {
      const a = ring[i], b = ring[(i + 1) % ring.length], L = Math.hypot(b[0] - a[0], b[1] - a[1]);
      if (L < 0.1) continue;
      const ux = (b[0] - a[0]) / L, uy = (b[1] - a[1]) / L, nx = -uy, ny = ux;
      for (let k = 1; k * 0.05 < L - 0.02; k++) {
        const t = k * 0.05, qx = a[0] + ux * t, qy = a[1] + uy * t;
        const l = inWall(key, qx + nx * 0.04, qy + ny * 0.04), r = inWall(key, qx - nx * 0.04, qy - ny * 0.04);
        if (l === r) continue;
        const sx = l ? nx : -nx, sy = l ? ny : -ny;                   // into the wall
        if (inWall(key, qx - sx * 0.12, qy - sy * 0.12)) continue;
        out.push([qx + sx * 0.04, qy + sy * 0.04, qx - sx * 0.12, qy - sy * 0.12]);
      }
    }
    return (spotCache[key] = out);
  }
  function faceLineUp(key, dx = 0, dy = 0) {
    let n = 0, sum = 0, dark = 0;
    for (const [ix, iy, ox, oy] of faceSpots(key)) {
      const a = lumAt(key, ix + dx, iy + dy), b = lumAt(key, ox + dx, oy + dy);
      if (a === null || b === null) continue;
      n++; sum += b - a; if (a <= b - 30) dark++;
    }
    return { by: [dx, dy], n, contrast: n ? Math.round(sum / n * 10) / 10 : 0, share: n ? Math.round(dark / n * 1000) / 1000 : 0 };
  }
  window.__t = { THREE, frame, lane, walk, walkTo, targets, crossable, near, stoppedBy, topSpots, reach, span, hoverSpots, along, levelOf, holding, leave, only, verdict, spawn, standIn, lumAt, wallCorners, lineUp, faceSpots, faceLineUp };
  return true;
}

try {
  // ------------------------------------------------------------------ the page opens without errors
  await P.goto(URL + '?nodownload=1');
  // the typed furniture heights of an earlier run are kept in the browser profile: forget them, this run starts from the model's heights
  await P.evaluate(`(() => { try { Object.keys(localStorage).filter(k => k.startsWith('walkthrough-furniture')).forEach(k => localStorage.removeItem(k)); } catch (e) { /* blocked */ } })()`);
  const hasFurniture = await P.evaluate('!!(window.__host && __host.furniture)');
  flush();
  await P.goto(URL + '?nodownload=1');
  const loaded = await P.evaluate(`__host.pictures.ready.then(ok => ({ pictures: ok, title: document.title, h1: document.querySelector('h1').textContent,
    project: __host.model.project, short: __host.model.shortName, photo: __host.model.photoName, floors: __host.floors.map(f => [f.key, f.name, f.level]),
    groups: __host.floors.map(f => f.group.visible), canvas: !!document.querySelector('canvas'), viewerError: (document.getElementById('vm-err') || {}).style?.display === 'block' }))`);
  const firstErrors = errs();
  check(`the page opens without errors: "${loaded.title}", ${loaded.floors.map(f => `${f[1]} at ${f[2].toFixed(2)} m`).join(', ')}, both pictures read`,
    !firstErrors.length && !loaded.viewerError && loaded.canvas && loaded.pictures.every(Boolean) && loaded.title === `${loaded.short} test`
    && JSON.stringify(loaded.floors) === JSON.stringify([['F1', 'Floor 1', 0], ['F2', 'Floor 2', 2.9]]) && loaded.groups.every(Boolean), firstErrors.length ? firstErrors : loaded);
  await P.evaluate(`(${pageHelpers.toString()})()`);
  await sleep(400);
  const shownTop = await P.evaluate(boxesOf);
  const nTop = await P.evaluate(`__host.labels.filter(l => l.floor === 'F2').length`);
  check('room names from the pictures are shown over the top floor (Floor 2), none on top of another', shownTop.length >= Math.min(10, nTop) && !overlaps(shownTop).length,
    { shown: shownTop.length, onFloor2: nTop, overlapping: overlaps(shownTop), names: shownTop.map(b => b[0]) });
  await P.shot(path.join(OUT, 'orbit_both.png'));

  // ------------------------------------------------------------------ floor buttons
  await P.clickEl('#floors [data-f=F1]'); await sleep(400);
  const v1 = await visible();
  const shown1 = await P.evaluate(boxesOf);
  const n1 = await P.evaluate(`__host.labels.filter(l => l.floor === 'F1').length`);
  await P.shot(path.join(OUT, 'orbit_F1.png'));
  await P.clickEl('#floors [data-f=F2]'); await sleep(300);
  const v2 = await visible();
  await P.clickEl('#floors [data-f=both]'); await sleep(300);
  const vb = await visible();
  check('Orbit: the Floor 1 / Floor 2 / Both floors buttons show those floors (Floor 1 names with Floor 1, none overlapping)',
    v1 === '["F1"]' && v2 === '["F2"]' && vb === '["F1","F2"]' && shown1.length >= Math.min(7, n1) && !overlaps(shown1).length && (await hasOn('#floors [data-f=both]')),
    { F1: v1, F2: v2, both: vb, namesOnF1: `${shown1.length} of ${n1}`, overlapping: overlaps(shown1) });
  await P.press('Digit2');
  let s = await st();
  const clr = await P.evaluate('Math.min(99, __viewer.probe.clearance())'), onf = await P.evaluate('__viewer.probe.onFloor()');
  check('Walk starts on Floor 1 at eye height (1.60 m), on the floor, with room around you',
    s.mode === 'walk' && s.floor === 'F1' && Math.abs(s.y - 1.6) < 0.01 && onf && clr >= 0.5, { floor: s.floor, y: r2(s.y), clearance: r2(clr), onFloor: onf });
  await P.clickEl('#floors [data-f=F2]'); s = await st();
  const onf2 = await P.evaluate('__viewer.probe.onFloor()');
  const f2button = { floor: s.floor, y: r2(s.y), onFloor: onf2, on: await hasOn('#floors [data-f=F2]') };
  await P.press('PageDown'); const sd = await st();
  await P.press('PageUp'); const su = await st();
  await P.clickEl('#floors [data-f=both]'); const sb = await st();
  check('Walk: the Floor 2 button takes you up to +2.90 m (eye at 4.50 m) and PgDn / PgUp and the Both button change floor',
    f2button.floor === 'F2' && Math.abs(f2button.y - 4.5) < 0.01 && f2button.onFloor && f2button.on && sd.floor === 'F1' && su.floor === 'F2' && sb.floor === 'F1',
    { floor2: f2button, pgDn: sd.floor, pgUp: su.floor, both: sb.floor });

  // ------------------------------------------------------------------ the structure, with the furniture hidden
  // Walls, doors, glass and stairs are the pictures' own; the boxes are colliders, so these are judged without them. The boxes have
  // their own checks below, and the doors and the glass are walked again with them.
  await setFurniture(false);

  // walls, per floor
  for (const key of ['F1', 'F2']) {
    await P.evaluate(`__viewer.goToFloor(${JSON.stringify(key)})`);
    const walls = await P.evaluate(wallWalks(false));
    check(`${key}: walking into walls at 40 random spots, never through a wall`, walls.floor === key && walls.tried >= 30 && walls.wentThrough === 0 && walls.endedInsideWall === 0, walls);
  }

  // every door and passage, both ways
  const all = [];
  for (const key of ['F1', 'F2']) {
    await P.evaluate(`__viewer.goToFloor(${JSON.stringify(key)})`);
    all.push(...await P.evaluate(doorWalks(false)));
  }
  const blockedAll = all.filter(d => !d.ok);
  const doors = all.filter(d => d.kind === 'door');
  check(`every door and passage can be walked through its middle, both ways (${doors.length} doors and ${all.length - doors.length} passage${all.length - doors.length === 1 ? '' : 's'}; the ${all.filter(d => d.exterior).length} exterior ones from inside)`,
    all.length > 0 && blockedAll.length === 0, blockedAll.length ? blockedAll : { checked: all.map(d => `${d.id} ${d.fwd}/${d.back}`), exterior: all.filter(d => d.exterior).map(d => d.id) });

  // door heads and lintels: looking straight up in each door (in the lintel's line), open up to its head, then the lintel or the glass transom
  const heads = await P.evaluate(`__host.openings.filter(o => o.kind === 'door').map(o => {
    const c = o.lintelDepth ? (o.lintelDepth[0] + o.lintelDepth[1]) / 2 : 0;
    const up = __host.upHit(o.floor, o.x + o.nx * c, o.y + o.ny * c, 1.0);
    return { id: o.id, head: o.head, lintel: o.lintel, top: o.lintelTop, up: up === null ? null : Math.round(up * 1000) / 1000 };
  })`);
  const badHeads = heads.filter(h => h.lintel ? !(h.up !== null && Math.abs(h.up - h.head) < 0.02) : h.up !== null && h.up < 2.5);
  const byHead = {};
  heads.forEach(h => { byHead[h.head.toFixed(2)] = (byHead[h.head.toFixed(2)] || 0) + 1; });
  const transoms = heads.filter(h => h.lintel === 'transom');
  check(`every door is open up to its head with a lintel or glass transom above (heads ${Object.entries(byHead).map(([k, n]) => `${k} m x${n}`).join(', ')}; ${transoms.length} glass transom${transoms.length === 1 ? '' : 's'})`,
    heads.length > 0 && badHeads.length === 0, badHeads.length ? badHeads : { doors: heads.length, transoms: transoms.map(h => `${h.id} to ${h.top}`) });
  // ... and the lintel (or transom) reaches the jambs: looking straight up from 1 m at 1 cm inside each drawn jamb, in the lintel's line, it is met at the
  // head. Where a lintel stops short of a wall, a slit runs from the head up to the floor above (2.10 - 2.90 m), seen from below and from either side.
  const slits = await P.evaluate(`__host.openings.filter(o => o.kind === 'door' && o.lintel).map(o => {
    const sp = __t.span(o, 1.2, true), c = o.lintelDepth ? (o.lintelDepth[0] + o.lintelDepth[1]) / 2 : 0, ux = o.ny, uy = -o.nx, r = { id: o.id, width: o.width, head: o.head };
    if (!sp) return { ...r, ok: false, why: 'no jambs met' };
    r.drawn = sp.width;
    r.ends = [[1, sp.jambs[0]], [-1, sp.jambs[1]]].map(([sg, d]) => {
      const x = o.x + o.nx * c + ux * sg * (d - 0.01), y = o.y + o.ny * c + uy * sg * (d - 0.01), up = __host.upHit(o.floor, x, y, 1.0);
      let gap = 0;                                         // how far in from the jamb the lintel starts (1 cm steps, up to 0.3 m)
      while (gap < 0.3) { const u = __host.upHit(o.floor, x - ux * sg * gap, y - uy * sg * gap, 1.0); if (u !== null && Math.abs(u - o.head) < 0.02) break; gap += 0.005; }
      return { up: up === null ? null : Math.round(up * 1000) / 1000, slit: Math.round((gap + 0.01) * 1000) / 1000 };
    });
    r.ok = r.ends.every(e => e.up !== null && Math.abs(e.up - o.head) < 0.02);
    return r; })`);
  const slitBad = slits.filter(s => !s.ok);
  check(`every door's lintel or transom reaches both drawn jambs (no slit above the head beside it): ${slits.length - slitBad.length} of ${slits.length} doors`,
    slits.length > 0 && !slitBad.length, slitBad.length ? slitBad.map(s => ({ id: s.id, record: s.width, drawn: s.drawn, lintelStartsInFromJamb: s.ends.map(e => e.up === null || Math.abs(e.up - s.head) >= 0.02 ? `${Math.round(e.slit * 1000) / 10} cm (+-0.5)` : 'at the jamb') })) : slits.map(s => s.id));
  // the passages: nothing built across them (no lintel overhead, no glass in their line)
  const passages = await P.evaluate(`__host.openings.filter(d => d.kind === 'passage').map(d => {
    const ux = d.ny, uy = -d.nx, r = { id: d.id, up: [], glass: [] };
    for (const k of [0.25, 0.5, 0.75]) {
      const x = d.x + ux * (k - 0.5) * d.width, y = d.y + uy * (k - 0.5) * d.width, up = __host.upHit(d.floor, x, y, 1.0);
      if (up !== null && up < 2.5) r.up.push(Math.round(up * 100) / 100);
      for (const h of [0.35, 1.2]) { const hit = __host.rayHit(d.floor, x - d.nx * 0.6, y - d.ny * 0.6, h, d.nx, d.ny, 1.2); if (hit && /glass/.test(hit.name) && Math.abs(hit.d - 0.6) <= d.wallThickness / 2 + 0.05) r.glass.push(hit.name); }
    }
    r.parts = __host.model.parts.filter(p => p.label && p.label.split(' ')[0] === d.id).map(p => p.kind);
    return r; })`);
  const touched = passages.filter(p => p.up.length || p.glass.length || p.parts.length);
  check(`the ${passages.length} passage${passages.length === 1 ? ' is' : 's are'} left open: no lintel overhead, no glass across, nothing built for ${passages.length === 1 ? 'it' : 'them'}`,
    passages.length > 0 && !touched.length, touched.length ? touched : passages.map(p => p.id));

  // the lift doors: open 1.00 m between their jambs as drawn (the owner's dimension; the walls, not the invisible walk skins: see the next
  // check), centred on their line, up to the head; the shafts behind them are walled on their other three sides and open only through the door
  const lifts = await P.evaluate(`(() => {
    const M = __host.model, shafts = Object.values(M.voids).flat().filter(v => /^lift/.test(v.what)), out = [];
    for (const d of M.openings.filter(o => o.liftDoor)) {
      const r = { id: d.id, floor: d.floor, label: d.label };
      r.jambs = [0.35, 1.2].map(h => { const sp = __t.span(d, h, true); return sp && sp.jambs; });
      r.width = r.jambs.every(Boolean) ? Math.round((r.jambs[0][0] + r.jambs[0][1]) * 1000) / 1000 : null;
      const up = __host.upHit(d.floor, d.x, d.y, 1.0); r.head = up === null ? null : Math.round(up * 1000) / 1000;
      const sh = shafts.slice().sort((a, b) => Math.hypot(a.x - d.x, a.y - d.y) - Math.hypot(b.x - d.x, b.y - d.y))[0];   // the shaft behind it (the cores stack)
      const tx = d.x - sh.x, ty = d.y - sh.y, toDoor = Math.hypot(tx, ty);
      r.shaft = sh.what;
      r.sides = [[1, 0], [-1, 0], [0, 1], [0, -1]].map(([dx, dy]) => {
        const hit = __host.rayHit(d.floor, sh.x, sh.y, 1.0, dx, dy, 6), door = (dx * tx + dy * ty) / toDoor > 0.9;
        return { dir: [dx, dy], door, d: hit ? Math.round(hit.d * 100) / 100 : null, what: hit ? hit.name : null,
          ok: door ? (!hit || hit.d > toDoor + 0.3) : (!!hit && hit.d < 1.4 && /solid/.test(hit.name)) };
      });
      out.push(r);
    }
    return out; })()`);
  const badLift = lifts.filter(l => l.width === null || Math.abs(l.width - 1.0) > 0.02 || l.jambs.some(j => !j || Math.abs(j[0] - j[1]) > 0.02 || Math.abs(j[0] + j[1] - 1.0) > 0.02)
    || l.head === null || Math.abs(l.head - 2.1) > 0.02 || l.sides.filter(x => x.door).length !== 1 || !l.sides.every(x => x.ok));
  check(`the ${lifts.length} lift doors are open 1.00 m between their drawn jambs (${lifts.map(l => `${l.id} ${l.width}`).join(', ')}), centred, up to the 2.10 m head; each shaft is walled on its other three sides and open only through its door`,
    lifts.length === 4 && !badLift.length, badLift.length ? badLift : lifts.map(l => `${l.id} (${l.shaft}): walls at ${l.sides.filter(x => !x.door).map(x => x.d).join(' / ')} m`));
  // Walk feels the colliders, which add invisible 'walk skins' (the model's colliderSkins: bands round pieces thinner than Walk's ray spacing, so
  // that its rays, 7.5 cm apart, cannot slip past a pane's end) to what is drawn. Between wall jambs there is no thin piece to guard, so no skin may
  // reach into the opening there: the opening Walk lets you through is the one drawn (and built in Max). At a glass jamb the pane's skin narrows
  // the door by design (as on the bank page): listed.
  const skinned = await P.evaluate(`__host.openings.filter(d => d.kind === 'door' || d.kind === 'passage').map(d => {
    const r = { id: d.id, glassJamb: (d.jambs || []).includes('glass'), drawn: [], walk: [] };
    for (const h of [0.35, 1.2]) { const a = __t.span(d, h, true), b = __t.span(d, h, false); r.drawn.push(a && a.width); r.walk.push(b && b.width); if (b) r.what = b.what; }
    r.same = r.drawn.every((w, i) => (w === null && r.walk[i] === null) || (w !== null && r.walk[i] !== null && Math.abs(w - r.walk[i]) <= 0.005));
    return r; })`);
  const narrowed = skinned.filter(r => !r.same && !r.glassJamb), byDesign = skinned.filter(r => !r.same && r.glassJamb);
  if (byDesign.length) note('doors whose glass jambs are guarded by walk skins, narrower for Walk than drawn (by design, as on the bank page)', byDesign.map(r => `${r.id}: ${r.drawn[0] === null ? 'jamb panes not on its middle line' : r.drawn[0] + ' m drawn'}, ${r.walk[0]} m for Walk`));
  check(`Walk's invisible collision skins reach into no opening between wall jambs: at knee and chest height ${skinned.filter(r => !r.glassJamb && r.same).length} of the ${skinned.filter(r => !r.glassJamb).length} doors and passages between wall jambs are as wide for Walk as drawn`,
    skinned.length > 0 && !narrowed.length, narrowed.length ? narrowed.map(r => ({ id: r.id, drawn: r.drawn[0], forWalk: r.walk[0], at: r.what })) : skinned.filter(r => !r.glassJamb).map(r => `${r.id} ${r.drawn[0]}`));

  // glass stops you
  const glass = [];
  for (const key of ['F1', 'F2']) {
    await P.evaluate(`__viewer.goToFloor(${JSON.stringify(key)})`);
    glass.push(...await P.evaluate(glassWalks(false)));
  }
  const through = glass.filter(g => !g.ok);
  check(`the glazing stops you (${glass.length} sides of ${new Set(glass.map(g => g.id)).size} glass spots, both floors)`,
    glass.length > 0 && through.length === 0, through.length ? through : glass.map(g => `${g.id} ${g.stoppedAt}`));

  // Floor 2: floor where its plate is, open over the stair from Floor 1 and the shafts; Walk starts on it from any Orbit view of it
  const f2 = await P.evaluate(`(() => { const v = __viewer, s = v.state, M = __host.model, out = { voids: [], starts: [] };
    const onFloorAt = (k, x, y) => { v.goToFloor(k); const keep = s.pos.clone(); s.pos.x = x; s.pos.z = -y; const r = v.probe.onFloor(); s.pos.copy(keep); return r; };
    for (const vd of M.voids.F2 || []) out.voids.push({ what: vd.what, at: [vd.x, vd.y], onFloor: onFloorAt('F2', vd.x, vd.y) });
    let seed = 3; const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
    v.setMode('orbit'); document.querySelector('#floors [data-f=F2]').click();
    const b = new __t.THREE.Box3().setFromObject(__host.FL.F2.group);
    for (let i = 0; i < 20; i++) {
      v.setMode('orbit'); __host.controls.target.set(b.min.x + rnd() * (b.max.x - b.min.x), 1, b.min.z + rnd() * (b.max.z - b.min.z));
      v.setMode('walk');
      out.starts.push({ floor: s.floor.key, y: Math.round(s.pos.y * 100) / 100, onFloor: v.probe.onFloor(), clearance: Math.round(Math.min(99, v.probe.clearance()) * 100) / 100 });
    }
    v.setMode('orbit'); document.querySelector('#floors [data-f=both]').click();
    return out; })()`);
  const badVoid = f2.voids.filter(x => x.onFloor), badStart2 = f2.starts.filter(x => x.floor !== 'F2' || Math.abs(x.y - 4.5) > 0.01 || !x.onFloor || x.clearance < 0.5);
  check(`Walk on Floor 2 stands on its plate: from 20 Orbit views of Floor 2 it starts at +2.90 m on the floor with room around it, and there is no floor over the ${f2.voids.length} openings in the plate (${f2.voids.map(x => x.what).join(', ')})`,
    f2.voids.length >= 3 && !badVoid.length && f2.starts.length === 20 && !badStart2.length, badVoid.length || badStart2.length ? { voids: badVoid, starts: badStart2 } : { leastRoom: Math.min(...f2.starts.map(x => x.clearance)) });

  // the steps of each stair sit one riser apart (the floor-to-floor height split into risers of at most 0.18 m), as the page has them: looking
  // straight down at the middle of each step. A stair is the first word of its steps' label: F1-S1 from Floor 1, F2-S1 from Floor 2.
  const steps = await P.evaluate(`(() => {
    const M = __host.model, out = [];
    const inside = p => { let x = 0, y = 0; p.o.forEach(q => { x += q[0]; y += q[1]; }); return [x / p.o.length, y / p.o.length]; };
    for (const p of M.parts.filter(p => p.kind === 'step')) { const [x, y] = inside(p), top = __host.downHit(p.floor, x, y, 3.2);
      out.push({ stair: p.label.split(' ')[0], label: p.label, floor: p.floor, at: [Math.round(x * 1000) / 1000, Math.round(y * 1000) / 1000], z0: p.z0, z1: p.z1, top: top === null ? null : Math.round(top * 1000) / 1000 }); }
    const fl = __host.floors, H = fl[1].level - fl[0].level;
    return { steps: out, riser: H / Math.ceil(H / 0.18 - 1e-9), H }; })()`);
  const stairs = {}, badSteps = [];
  for (const p of steps.steps) (stairs[p.stair] = stairs[p.stair] || []).push(p);
  const topsOf = ps => ps.map(p => p.top).sort((a, b) => a - b);
  for (const [id, ps] of Object.entries(stairs)) topsOf(ps).forEach((z, i) => { if (z === null || Math.abs(z - (i + 1) * steps.riser) > 0.01) badSteps.push({ stair: id, step: i + 1, top: z, want: Math.round((i + 1) * steps.riser * 1000) / 1000 }); });
  check(`the steps of each stair sit one riser (${steps.riser.toFixed(3)} m) apart: ${Object.entries(stairs).map(([id, ps]) => `${id} on ${ps[0].floor}, ${ps.length} steps, tops ${topsOf(ps).slice(0, 2).join(', ')} ... ${topsOf(ps)[ps.length - 1]} m`).join('; ')}`,
    steps.steps.length > 0 && !badSteps.length, badSteps.length ? badSteps : Object.fromEntries(Object.entries(stairs).map(([id, ps]) => [id, ps.length])));
  // The stair from Floor 1 is the iconic staircase: it lands on Floor 2 (its top step one riser under Floor 2's level). The upper stair beside the toilets
  // goes UP from Floor 2 toward a floor 3 that is not drawn (the owner, 2 Nov): its steps stand on Floor 2, none below it, each one riser higher and
  // further north than the one before (Floor 2's picture points its UP arrow north), so that it climbs at the rate that reaches +2.90 m above Floor 2.
  const flight1 = steps.steps.filter(p => p.floor === 'F1'), upper = steps.steps.filter(p => p.floor === 'F2').sort((a, b) => a.top - b.top);
  const upBad = [];
  upper.forEach((p, i) => {
    if (p.z0 < -1e-6) upBad.push({ step: p.label, z0: p.z0, why: 'below Floor 2' });
    if (i && !(p.at[1] > upper[i - 1].at[1] + 0.1)) upBad.push({ step: p.label, y: p.at[1], before: upper[i - 1].at[1], why: 'not further north' });
    if (Math.abs(p.top - (i + 1) * steps.riser) > 0.01) upBad.push({ step: p.label, top: p.top, why: 'not one riser above the one before' });
  });
  const lands = flight1.length && Math.abs(Math.max(...flight1.map(p => p.top)) + steps.riser - steps.H) < 0.01;
  const upTop = upper.length ? upper[upper.length - 1].top : null;
  check(`the stairs go where the owner said: Floor 1's ${flight1.length} steps land on Floor 2 (top ${flight1.length ? Math.max(...flight1.map(p => p.top)) : '-'} m + one riser = ${steps.H.toFixed(2)} m); the upper stair's ${upper.length} steps rise from Floor 2 toward floor 3, ${upper.length ? upper[0].top : '-'} to ${upTop} m above it, each one riser higher and further north (${upper.length ? r2(upper[upper.length - 1].at[1] - upper[0].at[1]) : '-'} m in all), none below Floor 2: ${upper.length} of the ${Math.round(steps.H / steps.riser)} risers to +${steps.H.toFixed(2)} m, ending in the air`,
    lands && upper.length >= 3 && !upBad.length && upper.every(p => /floor 3/.test(p.label)), upBad.length ? upBad : upper.map(p => `${p.label.split(' ').slice(0, 3).join(' ')}: top ${p.top} m at y ${p.at[1]}`));

  // The iconic staircase from above: Floor 2 is open over Floor 1's flight and only over it. Looking straight down from 1 m above Floor 2 at a grid of
  // spots on each step of the flight (the top one, 2.73 m high, included), Floor 2's plate is over none of them (no step under the slab); 2 cm outside
  // the flight's four edges the plate is there (no slot beside it). Floor 2's flat tread lines (drawn in the page as thin strips): every corner of
  // them lies on Floor 2's plate, none over the opening or anywhere else in the air.
  const iconic = await P.evaluate(`(() => {
    const THREE = __t.THREE, ray = new THREE.Raycaster(), M = __host.model, F2 = __host.floors.find(f => f.key === 'F2');
    const plateAt = (x, y) => { ray.set(new THREE.Vector3(x, F2.level + 1, -y), new THREE.Vector3(0, -1, 0)); ray.far = 1.5;
      const h = ray.intersectObjects(__host.FL.F2.walkables, false)[0]; return h ? Math.round((1 - h.distance) * 1000) / 1000 : null; };   // the plate's top above Floor 2's level, or null
    const flight = M.parts.filter(p => p.kind === 'step' && p.floor === 'F1'), out = { spots: 0, under: [], edge: 0, slot: [], points: 0, floating: [] };
    for (const p of flight) {
      const xs = p.o.map(q => q[0]), ys = p.o.map(q => q[1]), x0 = Math.min(...xs) + 0.01, x1 = Math.max(...xs) - 0.01, y0 = Math.min(...ys) + 0.01, y1 = Math.max(...ys) - 0.01;
      for (let i = 0; i <= 8; i++) for (let j = 0; j <= 3; j++) { const x = x0 + (x1 - x0) * i / 8, y = y0 + (y1 - y0) * j / 3; out.spots++; if (plateAt(x, y) !== null) out.under.push([p.label, Math.round(x * 100) / 100, Math.round(y * 100) / 100]); }
    }
    const all = flight.flatMap(p => p.o), X0 = Math.min(...all.map(q => q[0])), X1 = Math.max(...all.map(q => q[0])), Y0 = Math.min(...all.map(q => q[1])), Y1 = Math.max(...all.map(q => q[1]));
    out.flight = [X0, Y0, X1, Y1].map(v => Math.round(v * 1000) / 1000);
    for (let k = 0; k <= 12; k++) {
      const y = Y0 + (Y1 - Y0) * k / 12, x = X0 + (X1 - X0) * k / 12;
      for (const [px, py, side] of [[X0 - 0.02, y, 'west'], [X1 + 0.02, y, 'east'], [x, Y0 - 0.02, 'south'], [x, Y1 + 0.02, 'north']]) { out.edge++; if (plateAt(px, py) === null) out.slot.push([side, Math.round(px * 100) / 100, Math.round(py * 100) / 100]); }
    }
    const lines = __host.FL.F2.group.children.find(o => o.name === 'F2 tread lines'), pos = lines && lines.geometry.attributes.position;
    out.lines = pos ? pos.count / 6 : 0;
    out.floor1Lines = !!__host.FL.F1.group.children.find(o => o.name === 'F1 tread lines');
    for (let i = 0; pos && i < pos.count; i++) {
      const x = pos.getX(i), y = -pos.getZ(i), t = plateAt(x, y); out.points++;
      if (t === null || Math.abs(t) > 0.005) out.floating.push([Math.round(x * 100) / 100, Math.round(y * 100) / 100, t]);
      else if (x > X0 - 0.05 && x < X1 + 0.05 && y > Y0 - 0.05 && y < Y1 + 0.05) out.floating.push([Math.round(x * 100) / 100, Math.round(y * 100) / 100, 'over the opening']);
    }
    return out; })()`);
  check(`the iconic staircase: Floor 2 is open over Floor 1's flight (${(iconic.flight[2] - iconic.flight[0]).toFixed(2)} x ${(iconic.flight[3] - iconic.flight[1]).toFixed(2)} m) and only there: looking down at ${iconic.spots} spots on its ${flight1.length} steps, Floor 2's plate is over none (no step under the slab); 2 cm outside its four edges the plate is there at ${iconic.edge - iconic.slot.length} of ${iconic.edge} spots (no slot); Floor 2's ${iconic.lines} flat tread lines lie on its plate at all ${iconic.points} corners, none over the opening${iconic.floor1Lines ? '' : ' (Floor 1 has none)'}`,
    iconic.spots >= 16 * 20 && !iconic.under.length && !iconic.slot.length && iconic.points > 0 && !iconic.floating.length,
    iconic.under.length || iconic.slot.length || iconic.floating.length ? { under: iconic.under.slice(0, 6), slot: iconic.slot.slice(0, 6), floating: iconic.floating.slice(0, 6) } : { flight: iconic.flight, lines: iconic.lines });

  // The hatches (the serving hatch and the food lift's) are open from their sill to their head: a level ray across each at 1.5 m meets nothing in the
  // wall, one at 0.45 m meets the sill; looking down from 1.5 m in the hatch the sill's top is at its recorded sill (0.90 m, or the top of a counter
  // standing in it: 0.85 m), looking up from 1.0 m the lintel at 2.10 m.
  const hatches = await P.evaluate(`__host.openings.filter(o => o.hatch).map(o => {
    const r = { id: o.id, label: o.label, wall: o.wallThickness };
    const across = h => { const hit = __host.rayHit(o.floor, o.x - o.nx * 0.6, o.y - o.ny * 0.6, h, o.nx, o.ny, 1.2); return hit ? Math.round(hit.d * 1000) / 1000 : null; };
    r.at150 = across(1.5); r.at045 = across(0.45);
    const dn = __host.downHit(o.floor, o.x, o.y, 1.5), up = __host.upHit(o.floor, o.x, o.y, 1.0);
    r.sillTop = dn === null ? null : Math.round(dn * 1000) / 1000; r.headAt = up === null ? null : Math.round(up * 1000) / 1000;
    r.ok = (r.at150 === null || r.at150 > 0.6 + o.wallThickness / 2 + 0.02) && r.at045 !== null && Math.abs(r.at045 - (0.6 - o.wallThickness / 2)) < 0.03
      && r.sillTop !== null && Math.abs(r.sillTop - o.sill) < 0.01 && r.headAt !== null && Math.abs(r.headAt - o.head) < 0.01;
    return r; })`);
  check(`the ${hatches.length} hatches (${hatches.map(h => h.id).join(', ')}) are open from the sill to the head: nothing across them at 1.5 m, the sill met at 0.45 m, its top at ${hatches.map(h => h.sillTop).join(' / ')} m, the lintel at ${hatches.map(h => h.headAt).join(' / ')} m`,
    hatches.length > 0 && hatches.every(h => h.ok), hatches.filter(h => !h.ok).length ? hatches.filter(h => !h.ok) : hatches.map(h => `${h.id} ${h.label}: across at 1.5 m ${h.at150 === null ? 'nothing' : h.at150 + ' m'}, at 0.45 m ${h.at045} m`));

  // The forecourt is floor, and the entrance can be walked out (and in): Floor 1's outdoor paving (the slab labelled 'forecourt') is floor at spots
  // all over it; from 0.9 m inside the RED BOX's outer doors (the door whose one side is on the forecourt) Walk takes you out through them onto the
  // forecourt and stops at its edge, as far as it is drawn; from the forecourt, 0.3 m out from the wall, it takes you in through both doors of the
  // RED BOX into the lobby.
  // (Walk, on Floor 1: goToFloor does nothing in Orbit, where the Floor 2 check above left the viewer, and Walk's floor would then still be Floor 2,
  // whose terrace lies under the forecourt.)
  const walkOn = key => P.evaluate(`(() => { const v = __viewer; if (v.mode !== 'walk') v.setMode('walk'); v.goToFloor(${JSON.stringify(key)}); return v.state.floor.key; })()`);
  await walkOn('F1');
  const entrance = await P.evaluate(`(() => {
    const v = __viewer, s = v.state, keep = s.pos.clone(), M = __host.model, out = { mode: v.mode, floor: s.floor.key, spots: 0, notFloor: [] };
    const fc = M.parts.find(p => p.kind === 'slab' && p.floor === 'F1' && /^forecourt/.test(p.label || ''));
    if (!fc) return { none: true };
    const inPoly = (x, y, ring) => { let c = false; for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) { const [xi, yi] = ring[i], [xj, yj] = ring[j]; if ((yi > y) !== (yj > y) && x < xi + (y - yi) * (xj - xi) / (yj - yi)) c = !c; } return c; };
    const xs = fc.o.map(q => q[0]), ys = fc.o.map(q => q[1]);
    for (let x = Math.min(...xs) + 0.1; x < Math.max(...xs); x += 0.5) for (let y = Math.min(...ys) + 0.1; y < Math.max(...ys); y += 0.2) {
      if (![[0, 0], [0.15, 0], [-0.15, 0], [0, 0.15], [0, -0.15]].every(([dx, dy]) => inPoly(x + dx, y + dy, fc.o))) continue;   // 0.15 m or more inside its edge
      s.pos.x = x; s.pos.z = -y; out.spots++; if (!v.probe.onFloor()) out.notFloor.push([Math.round(x * 100) / 100, Math.round(y * 100) / 100]);
    }
    out.area = Math.round(Math.abs(fc.o.reduce((a, p, i) => { const q = fc.o[(i + 1) % fc.o.length]; return a + p[0] * q[1] - q[0] * p[1]; }, 0)) / 2 * 10) / 10;
    // the entrance: the F1 door with its one side on the forecourt (0.3 m beyond its wall face), and the RED BOX's inner door in line with it
    for (const d of M.openings.filter(o => o.floor === 'F1' && o.kind === 'door')) for (const sg of [1, -1]) {
      const t = d.wallThickness / 2 + 0.3;
      if (inPoly(d.x + d.nx * sg * t, d.y + d.ny * sg * t, fc.o)) out.door = { id: d.id, label: d.label, x: d.x, y: d.y, ox: d.nx * sg, oy: d.ny * sg, t: d.wallThickness / 2 };
    }
    if (!out.door) return out;
    const D = out.door, deg = (ux, uy) => Math.atan2(-ux, uy) * 180 / Math.PI;            // Walk's heading for a plan direction
    const inner = M.openings.filter(o => o.floor === 'F1' && o.kind === 'door' && o.id !== D.id && Math.abs((o.x - D.x) * D.oy - (o.y - D.y) * D.ox) < 0.3 && ((o.x - D.x) * D.ox + (o.y - D.y) * D.oy) < 0)
      .sort((a, b) => Math.hypot(a.x - D.x, a.y - D.y) - Math.hypot(b.x - D.x, b.y - D.y))[0];
    out.inner = inner ? inner.id : null;
    // out: from 0.9 m inside, facing the forecourt, walk 3 m
    s.pos.x = D.x - D.ox * 0.9; s.pos.z = -(D.y - D.oy * 0.9);
    out.outStart = { onFloor: v.probe.onFloor(), clearance: Math.round(Math.min(9, v.probe.clearance()) * 100) / 100 };
    out.outMoved = Math.round(v.probe.walk(deg(D.ox, D.oy), 3) * 100) / 100;
    const ex = s.pos.x, ey = -s.pos.z;
    out.outPast = Math.round(((ex - D.x) * D.ox + (ey - D.y) * D.oy - D.t) * 100) / 100;       // metres out from the wall's outer face
    out.outOnForecourt = inPoly(ex, ey, fc.o) && v.probe.onFloor();
    s.pos.x = ex + D.ox * 0.1; s.pos.z = -(ey + D.oy * 0.1); out.edgeAhead = !v.probe.onFloor();   // 0.1 m further: no floor (the forecourt's edge stopped you)
    // in: from the forecourt, 0.3 m out from the wall's face, facing the lobby, walk 4.5 m
    s.pos.x = D.x + D.ox * (D.t + 0.3); s.pos.z = -(D.y + D.oy * (D.t + 0.3));
    out.inStart = { onFloor: v.probe.onFloor(), clearance: Math.round(Math.min(9, v.probe.clearance()) * 100) / 100 };
    out.inMoved = Math.round(v.probe.walk(deg(-D.ox, -D.oy), 4.5) * 100) / 100;
    const ix = s.pos.x, iy = -s.pos.z;
    out.inPastInner = inner ? Math.round(((ix - inner.x) * -D.ox + (iy - inner.y) * -D.oy) * 100) / 100 : null;   // metres past the inner door's line, into the lobby
    s.pos.copy(keep); return out; })()`);
  check(`the forecourt is floor and the entrance can be walked out: Floor 1's forecourt (${entrance.area} m²) is floor at ${entrance.spots - (entrance.notFloor || []).length} of ${entrance.spots} spots; from inside, Walk goes out through ${entrance.door ? `${entrance.door.id} (${entrance.door.label})` : 'no door'} onto it, ${entrance.outPast} m out from the wall, and stops at its edge; from the forecourt it goes in through ${entrance.door ? entrance.door.id : '-'} and ${entrance.inner || '-'} into the lobby (${entrance.inPastInner} m past the inner doors)`,
    !entrance.none && entrance.mode === 'walk' && entrance.floor === 'F1' && entrance.spots >= 20 && !entrance.notFloor.length && !!entrance.door && entrance.outStart.onFloor && entrance.outPast >= 0.15 && entrance.outOnForecourt && entrance.edgeAhead
    && entrance.inStart.onFloor && entrance.inStart.clearance >= 0.25 && !!entrance.inner && entrance.inPastInner >= 0.3, entrance);

  // The railings stop you: walking straight at each railing (the 4 on the terrace's open edges and the 3 round the open stair) from 1 m in front of it, at
  // spots along it (one per 1.5 m, up to 5), you stop 0.1 - 0.6 m short of it (Walk keeps 0.3 m), never across; the railing is straight ahead at knee
  // height, and there is floor between you and it (the railing stops you, not the floor's edge).
  const railFloor = await walkOn('F2');
  const railWalks = await P.evaluate(`(() => {
    const v = __viewer, s = v.state, keep = s.pos.clone(), M = __host.model, out = [];
    for (const p of M.parts.filter(p => p.kind === 'railing')) {
      const xs = p.o.map(q => q[0]), ys = p.o.map(q => q[1]), x0 = Math.min(...xs), x1 = Math.max(...xs), y0 = Math.min(...ys), y1 = Math.max(...ys);
      const alongX = x1 - x0 >= y1 - y0, L = alongX ? x1 - x0 : y1 - y0, n = Math.max(1, Math.min(5, Math.floor(L / 1.5))), half = alongX ? (y1 - y0) / 2 : (x1 - x0) / 2;
      for (let k = 0; k < n; k++) {
        const t = (k + 0.5) / n, cx = alongX ? x0 + (x1 - x0) * t : (x0 + x1) / 2, cy = alongX ? (y0 + y1) / 2 : y0 + (y1 - y0) * t;
        const r = { label: p.label, at: [Math.round(cx * 100) / 100, Math.round(cy * 100) / 100], gap: null };
        for (const sg of [1, -1]) {
          const nx = alongX ? 0 : sg, ny = alongX ? sg : 0;
          s.pos.x = cx + nx * (half + 1.0); s.pos.z = -(cy + ny * (half + 1.0));
          if (!v.probe.onFloor() || v.probe.clearance() < 0.3) continue;
          r.moved = Math.round(v.probe.walk(Math.atan2(nx, -ny) * 180 / Math.PI, 2.0) * 100) / 100;
          const px = s.pos.x, py = -s.pos.z;
          r.gap = Math.round(((px - cx) * nx + (py - cy) * ny - half) * 100) / 100;
          const hit = __t.reach('F2', px, py, 0.35, -nx, -ny, 1.0, true);
          r.ahead = hit ? hit.name + ' at ' + hit.d.toFixed(2) + ' m' : 'nothing';
          s.pos.x = cx + nx * (half + Math.max(0.02, r.gap / 2)); s.pos.z = -(cy + ny * (half + Math.max(0.02, r.gap / 2)));
          r.floorBetween = v.probe.onFloor();
          break;
        }
        r.ok = r.gap !== null && r.gap > 0.1 && r.gap < 0.6 && /railing/.test(r.ahead) && r.floorBetween;
        out.push(r);
      }
    }
    s.pos.copy(keep); return out; })()`);
  const railBad = railWalks.filter(r => !r.ok), terraceWalks = railWalks.filter(r => /terrace/.test(r.label));
  check(`the railings stop you: walking at the ${terraceWalks.length} spots along the terrace's railings and the ${railWalks.length - terraceWalks.length} along the open stair's from 1 m, you stop ${railWalks.length ? r2(Math.min(...railWalks.map(r => r.gap ?? 9))) : '-'} - ${railWalks.length ? r2(Math.max(...railWalks.map(r => r.gap ?? -9))) : '-'} m short of the railing, with floor between you and it, never across`,
    railFloor === 'F2' && terraceWalks.length >= 6 && railWalks.length > terraceWalks.length && !railBad.length, railBad.length ? railBad : railWalks.map(r => `${r.label} ${r.at.join(', ')}: ${r.gap} m`));

  // Ghost goes through a wall that stops Walk: on Floor 1, at the Walk start or else the first of a fixed series of spots with room around it,
  // face the nearest wall square on (the heading of 72 with the least open distance, 0.6 - 2.5 m); Walk stops short of it, Ghost (W held until
  // you are 1 m past its face) comes out on the other side
  await P.press('Digit1'); await P.press('Digit2');
  const g0 = await P.evaluate(`(() => { const v = __viewer, s = v.state; v.goToFloor('F1');
    let seed = 5; const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647, b = new __t.THREE.Box3().setFromObject(__host.FL.F1.group);
    for (let t = 0; t < 400; t++) {
      if (t) { s.pos.x = b.min.x + rnd() * (b.max.x - b.min.x); s.pos.z = b.min.z + rnd() * (b.max.z - b.min.z); }
      if (!v.probe.onFloor() || v.probe.clearance() < 0.6) continue;
      const d = [...Array(72)].map((_, i) => v.probe.open(i * 5)); let k = 0; d.forEach((x, j) => { if (x < d[k]) k = j; });
      if (d[k] > 0.6 && d[k] < 2.5) { s.yaw = k * 5 * Math.PI / 180; s.pitch = 0; return { deg: k * 5, d: d[k], x: s.pos.x, z: s.pos.z, spot: t }; }
    }
    return null; })()`);
  let ghostRes = { found: !!g0 };
  if (g0) {
    const walked = await P.evaluate(`(() => { const v = __viewer, s = v.state, moved = v.probe.walk(${g0.deg}, ${g0.d} + 1.5); const r = { moved, crossed: v.probe.crosses(${g0.x}, ${g0.z}, s.pos.x, s.pos.z) };
      s.pos.x = ${g0.x}; s.pos.z = ${g0.z}; s.yaw = ${g0.deg} * Math.PI / 180; s.pitch = 0; return r; })()`);
    await P.press('Digit3');
    await P.evaluate(`(() => { const s = __viewer.state; s.pos.x = ${g0.x}; s.pos.z = ${g0.z}; s.yaw = ${g0.deg} * Math.PI / 180; s.pitch = 0; })()`);
    const past = `(() => { const s = __viewer.state, a = ${g0.deg} * Math.PI / 180; return (s.pos.x - ${g0.x}) * -Math.sin(a) + (s.pos.z - ${g0.z}) * -Math.cos(a); })()`;
    const tg0 = Date.now();
    await P.keyDown('KeyW');
    let gone = 0;
    for (let i = 0; i < 64 && gone < g0.d + 1.0; i++) { await sleep(125); gone = await P.evaluate(past); }
    await P.keyUp('KeyW');
    const crossed = await P.evaluate(`(() => { const s = __viewer.state; __viewer.state.floor = __host.floors[0]; return __viewer.probe.crosses(${g0.x}, ${g0.z}, s.pos.x, s.pos.z); })()`);
    ghostRes = { wallAhead: r2(g0.d), walkMoved: r2(walked.moved), walkCrossed: walked.crossed, ghostWent: r2(gone), ghostCrossed: crossed, seconds: r2((Date.now() - tg0) / 1000) };
    ghostRes.ok = walked.moved < g0.d && !walked.crossed && gone >= g0.d + 1.0 && crossed;
  }
  check('Ghost goes through a wall that stops Walk (Walk stops short of it; Ghost, W held, comes out 1 m past its face)', !!ghostRes.ok, ghostRes);
  await P.press('Digit1');

  // ------------------------------------------------------------------ the plan pictures (on a fresh page: the usual view, the boxes shown)
  // (a) the tick: off when the page opens; on, a picture shows with each floor that shows (both floors in Walk); off again, none; ?picture=1 opens with it on
  flush();
  await P.goto(URL + '?nodownload=1');
  await P.evaluate('__host.pictures.ready.then(() => true)');
  await P.evaluate(`(${pageHelpers.toString()})()`);
  const pics = {};
  pics.atStart = { ticked: await P.evaluate(`document.getElementById('picture').checked`), shown: await P.evaluate(picturesShown) };
  await clickSel('#picture'); await sleep(300);
  pics.on = await P.evaluate(picturesShown);
  await clickSel('#floors [data-f=F1]'); await sleep(500);
  pics.onF1 = await P.evaluate(picturesShown);
  await P.evaluate(`document.querySelector('.fb-block') && (document.getElementById('panel').scrollTop = 0)`);
  await P.shot(path.join(OUT, 'picture_F1.png'));
  await clickSel('#floors [data-f=F2]'); await sleep(500);
  pics.onF2 = await P.evaluate(picturesShown);
  await P.shot(path.join(OUT, 'picture_F2.png'));
  await clickSel('#floors [data-f=both]'); await sleep(200);
  await P.press('Digit2'); await sleep(200);
  pics.inWalk = await P.evaluate(picturesShown);
  await P.press('Digit1');
  await clickSel('#picture'); await sleep(200);
  pics.off = await P.evaluate(picturesShown);
  check('the Plan picture tick: off when the page opens; on, each floor that shows has its picture (Floor 1 alone: its own; Floor 2 alone: its own; Walk: both); off again, none',
    pics.atStart.ticked === false && pics.atStart.shown === '' && pics.on === 'F1,F2' && pics.onF1 === 'F1' && pics.onF2 === 'F2' && pics.inWalk === 'F1,F2' && pics.off === '', pics);
  // (b) the pictures are the source files, byte for byte, at their own size, and each sheet covers its picture at the model's scale and position
  const src = await P.evaluate(`(() => { const out = {};
    for (const m of __host.pictures.objs) { const k = m.userData.key, pf = __host.model.pictureFrame[k], img = m.material.map.image, g = m.geometry; g.computeBoundingBox();
      const b = g.boundingBox, px = (x, y) => [pf.originPx[0] + pf.pxPerMetreX * (x + __host.model.offset[0]), pf.originPx[1] - pf.pxPerMetreY * (y + __host.model.offset[1])];
      out[k] = { file: pf.file, data: __host.pictures.src[k], natural: [img.naturalWidth, img.naturalHeight], size: pf.size,     // the north-west corner (z = -y) to pixel (0, 0), the south-east to (W, H)
        corners: [px(b.min.x, -b.min.z), px(b.max.x, -b.max.z)].map(q => q.map(v => Math.round(v * 100) / 100)), lift: Math.round((b.min.y - __t.levelOf(k)) * 1000) / 1000 }; }
    return out; })()`);
  const srcBad = [];
  for (const [k, o] of Object.entries(src)) {
    const file = path.resolve(HERE, 'src', o.file), m = /^data:image\/[a-z]+;base64,(.*)$/.exec(o.data || '');
    const same = m && existsSync(file) && Buffer.from(m[1], 'base64').equals(readFileSync(file));
    const placed = Math.abs(o.corners[0][0]) < 0.05 && Math.abs(o.corners[0][1]) < 0.05 && Math.abs(o.corners[1][0] - o.size[0]) < 0.05 && Math.abs(o.corners[1][1] - o.size[1]) < 0.05;
    if (!same || o.natural.join() !== o.size.join() || !placed || !(o.lift > 0 && o.lift <= 0.01)) srcBad.push({ k, file: o.file, same, natural: o.natural, size: o.size, corners: o.corners, lift: o.lift });
    delete o.data;
  }
  check(`the two plan pictures are the source files byte for byte (${Object.values(src).map(o => `${path.basename(o.file)} ${o.size.join(' x ')}`).join(', ')}); each sheet's corners are its picture's corners through the model's pictureFrame, ${Object.values(src).map(o => o.lift * 1000)[0]} mm above its floor`,
    Object.keys(src).length === 2 && !srcBad.length, srcBad.length ? srcBad : src);
  // (c) they line up with the walls: along the faces of the model's walls (a spot every 5 cm) the picture is darker just inside the wall (4 cm) than
  // just outside it (12 cm): its walls are under the model's. Judged against the same picture read off: the mean contrast where the page lays the
  // picture must beat every read 0.1 m off (in four directions) by 1.3 times and every read 0.3 m off by 1.6 times, so the sheet lies where the
  // walls are to within 0.1 m. (Until 2 Nov this was judged at the convex wall corners only, 6 cm inside against 15 cm outside, 85 % of them; since
  // the walls were put on the drawing's outline strokes that rule misses the walls the pictures draw light - the toilets' walls on the teal floor,
  // the outside stair's spine - and a door leaf or swing drawn beside a jamb: its count is shown as information.)
  const lines = await P.evaluate(`(() => { const out = {};
    for (const k of ['F1', 'F2']) {
      const near = [[0.1, 0], [-0.1, 0], [0, 0.1], [0, -0.1]].map(([dx, dy]) => __t.faceLineUp(k, dx, dy)), far = [[0.3, 0], [-0.3, 0], [0, 0.3], [0, -0.3]].map(([dx, dy]) => __t.faceLineUp(k, dx, dy));
      const c = __t.lineUp(k);
      out[k] = { at: __t.faceLineUp(k), near, far, corners: { n: c.n, ok: c.ok, misses: c.misses } };
    }
    return out; })()`);
  const lineBad = Object.entries(lines).filter(([, o]) => o.at.n < 500 || o.near.some(x => x.contrast * 1.3 > o.at.contrast) || o.far.some(x => x.contrast * 1.6 > o.at.contrast));
  const most = xs => Math.max(...xs.map(x => x.contrast)), mostShare = xs => Math.max(...xs.map(x => x.share));
  note('the corner rule of the first build (information since 2 Nov: 6 cm inside a convex wall corner darker by 30 than 15 cm outside)', Object.fromEntries(Object.entries(lines).map(([k, o]) => [k, `${o.corners.ok} of ${o.corners.n} corners; misses ${o.corners.misses.map(m => `(${m.at.join(', ')}) ${m.wall} vs ${m.beside}`).join(', ')}`])));
  check(`the pictures line up with the walls: along the faces of the model's walls the picture is darker 4 cm inside than 12 cm outside by ${Object.entries(lines).map(([k, o]) => `${o.at.contrast} on ${k} (${Math.round(o.at.share * 100)} % of ${o.at.n} spots by 30 or more)`).join(' and ')}; read 0.1 m off at most ${Object.values(lines).map(o => `${most(o.near)} (${Math.round(mostShare(o.near) * 100)} %)`).join(' and ')}, 0.3 m off at most ${Object.values(lines).map(o => `${most(o.far)} (${Math.round(mostShare(o.far) * 100)} %)`).join(' and ')}: the placement beats every read 0.1 m off by 1.3 times and 0.3 m off by 1.6 times`,
    !lineBad.length, lineBad.length ? lines : Object.fromEntries(Object.entries(lines).map(([k, o]) => [k, { at: o.at, near: o.near.map(x => x.contrast), far: o.far.map(x => x.contrast) }])));
  // (d) ?picture=1 in the address opens the page with the pictures on
  flush();
  await P.goto(URL + '?nodownload=1&picture=1');
  await P.evaluate('__host.pictures.ready.then(() => true)'); await sleep(300);
  const viaUrl = { ticked: await P.evaluate(`document.getElementById('picture').checked`), shown: await P.evaluate(picturesShown) };
  check('?picture=1 in the address opens the page with the plan pictures on', viaUrl.ticked && viaUrl.shown === 'F1,F2', viaUrl);
  flush();
  await P.goto(URL + '?nodownload=1');
  await P.evaluate(`(${pageHelpers.toString()})()`);
  await setFurniture(true);

  // ------------------------------------------------------------------ what the pictures' symbols became (2 Nov, after the owner's answers)
  // No lamp boxes: the circles with a cross (2 on Floor 1, 3 on Floor 2 beside seats; the review's issue 10) are the usual symbol of a ceiling or pendant
  // light, and the faint square with a cross in Floor 2's lift lobby (issue 5) is a glyph of the printed background drawing. Their pixels in the source
  // pictures, put through the model's pictureFrame: no box stands on any of them (none holds the spot or has its middle within 0.25 m of it), there is no
  // lamp kind, and no box is called a lamp or a light. The picture read through its sheet shows a dark mark there (the symbol), so the spot is the right one.
  const SYMBOLS = [['F1', 226, 358.5, 'circle with a cross, by the lounge bench'], ['F1', 764, 596, 'circle with a cross, by the desk'], ['F2', 69, 291, 'circle with a cross, by the mural wall'],
    ['F2', 95, 600, 'circle with a cross, by the signature cabinets'], ['F2', 771, 346, 'circle with a cross, on the feature carpet'], ['F2', 658, 604, 'square with a cross, the background glyph in the lift lobby']];
  const lamps = await P.evaluate(`(() => {
    const M = __host.model, F = __host.furniture, out = { kinds: M.furnitureKinds.map(k => k.key), named: F.pieces().filter(p => /lamp|light/i.test(p.family + ' ' + (p.kind || ''))).map(p => p.id), spots: [] };
    for (const [key, px, py, what] of ${JSON.stringify(SYMBOLS)}) {
      const pf = M.pictureFrame[key], x = (px - pf.originPx[0]) / pf.pxPerMetreX - M.offset[0], y = (pf.originPx[1] - py) / pf.pxPerMetreY - M.offset[1];
      const on = F.pieces().filter(p => p.floor === key).map(p => { const r = p.rot * Math.PI / 180, dx = x - p.x, dy = y - p.y, u = dx * Math.cos(r) + dy * Math.sin(r), w = -dx * Math.sin(r) + dy * Math.cos(r);
        return { id: p.id, holds: Math.abs(u) <= p.w / 2 && Math.abs(w) <= p.d / 2, centre: Math.hypot(dx, dy), edge: Math.hypot(Math.max(Math.abs(u) - p.w / 2, 0), Math.max(Math.abs(w) - p.d / 2, 0)) }; })
        .sort((a, b) => a.edge - b.edge);
      let dark = 255;
      for (const ex of [-0.08, -0.04, 0, 0.04, 0.08]) for (const ey of [-0.08, -0.04, 0, 0.04, 0.08]) { const l = __t.lumAt(key, x + ex, y + ey); if (l !== null) dark = Math.min(dark, l); }
      out.spots.push({ key, px: [px, py], what, at: [Math.round(x * 100) / 100, Math.round(y * 100) / 100], dark: Math.round(dark), nearest: on[0] ? on[0].id + ' ' + on[0].edge.toFixed(2) + ' m away' : 'none',
        bad: on.filter(q => q.holds || q.centre < 0.25).map(q => q.id) });
    }
    return out; })()`);
  check(`no lamp boxes: the ${SYMBOLS.length - 1} light symbols (circles with a cross) and the background glyph have no box on them (the nearest ${lamps.spots.map(s => s.nearest.split(' ').slice(1).join(' ')).join(', ')}), there is no lamp kind (${lamps.kinds.length} kinds: ${lamps.kinds.join(', ')}) and no box is called a lamp or a light; the picture shows the symbol at each spot (darkest ${lamps.spots.map(s => s.dark).join(' / ')} of 255)`,
    !lamps.kinds.includes('lamp') && !lamps.named.length && lamps.spots.length === SYMBOLS.length && lamps.spots.every(s => !s.bad.length && s.dark < 120), lamps.spots.filter(s => s.bad.length || s.dark >= 120).length || lamps.named.length ? lamps : lamps.spots.map(s => `${s.key} px ${s.px.join(', ')} -> (${s.at.join(', ')}): ${s.what}; nearest box ${s.nearest}`));
  // The sculptural seating: the large white faceted form in the middle of Floor 2 is a seating (the owner, 2 Nov), traced by boxes of kind seat whose top
  // is at the seat height (450 mm: looking down at the middle of each, the page's downHit finds 0.45 m), each standing on the white form in the picture.
  const sculpt = await P.evaluate(`(() => { const F = __host.furniture, seat = __host.model.furnitureKinds.find(k => k.key === 'seat');
    return { seatHeight: seat && seat.height, pieces: F.pieces().filter(p => /sculptural seating/i.test(p.family)).map(p => { const d = __host.downHit(p.floor, p.x, p.y, 2.5);
      return { id: p.id, kind: p.kind, floor: p.floor, size: [p.w, p.d].map(v => Math.round(v * 100) / 100), top: d === null ? null : Math.round(d * 1000) / 1000, picture: Math.round(__t.lumAt(p.floor, p.x, p.y)) }; }) }; })()`);
  check(`the sculptural seating is kind seat: ${sculpt.pieces.length} boxes (${sculpt.pieces.map(p => `${p.id} ${p.size.join(' x ')} m`).join(', ')}) of kind seat on Floor 2, their tops at ${[...new Set(sculpt.pieces.map(p => p.top))].join(' / ')} m (the seat height, ${sculpt.seatHeight} mm), each on the white form in the picture (${sculpt.pieces.map(p => p.picture).join(' / ')} of 255)`,
    sculpt.pieces.length >= 1 && sculpt.seatHeight === 450 && sculpt.pieces.every(p => p.kind === 'seat' && p.floor === 'F2' && p.top !== null && Math.abs(p.top - 0.45) < 0.005 && p.picture >= 200), sculpt);
  // The check-in seating (the owner, 2 Nov: the purple 'Computer / monitor' boxes are seat backs - "it doesnt even made sense for monitor to be on the
  // sofa"). Floor 1 has no computer box left: no kind 'computer', no box of it, none called a computer, monitor, screen or laptop, and the legend has no
  // 'Computer / monitor' row but a 'Seat back' row (800 mm, its own colour, not the old purple). The five seat backs (kind seat-back) stand on the floor
  // (0 - 0.80 m) at the rims of the check-in's two seats (kind seat, 450 mm): each lies wholly over the round sofa or the sofa, its outer face within
  // 0.25 m of the seat's edge - for the round sofa the circle drawn in its box - and its long side along that edge (within 15 degrees: parallel to the
  // sofa's edge, square to the round sofa's radius); four at the round sofa, one at the sofa. In the page, looking straight down at each back finds
  // its top at 0.80 m, and on the seat 0.25 m inside the back the seat's top at 0.45 m: 350 mm of back shows above the seat. (2 Nov, evening: the
  // sofa's family is 'check-in sofa', so that 'sofa' means only Floor 2's sofas, whose backs are in their box.)
  const checkInSeats = await P.evaluate(`(() => {
    const M = __host.model, F = __host.furniture, pcs = F.pieces(), out = { kinds: M.furnitureKinds.map(k => k.key) };
    const label = k => (M.furnitureKinds.find(q => q.key === k) || {}).label || '';           // what the legend and the hover label say: the kind's label and the family
    out.computers = pcs.filter(p => p.kind === 'computer' || /computer|monitor|screen|laptop/i.test(p.family + ' ' + label(p.kind))).map(p => p.id);
    out.legend = [...document.querySelectorAll('.fb-row[data-k]')].map(r => r.querySelector('.fb-lab').innerText);
    const kb = M.furnitureKinds.find(k => k.key === 'seat-back');
    out.kind = kb ? { label: kb.label, colour: kb.colour, height: kb.height, base: kb.base, count: kb.count, onTop: kb.onTop, support: kb.support, blocks: kb.blocks } : null;
    const seats = pcs.filter(p => p.floor === 'F1' && p.kind === 'seat' && /^(round sofa|check-in sofa)$/.test(p.family));
    out.seats = seats.map(s => ({ id: s.id, family: s.family, size: [s.w, s.d].map(v => Math.round(v * 1000) / 1000), top: Math.round(__host.downHit('F1', s.x, s.y, 2.5) * 1000) / 1000 }));
    const local = (s, x, y) => { const r = s.rot * Math.PI / 180, dx = x - s.x, dy = y - s.y; return [dx * Math.cos(r) + dy * Math.sin(r), -dx * Math.sin(r) + dy * Math.cos(r)]; };
    const corners = p => { const r = p.rot * Math.PI / 180, c = Math.cos(r), s = Math.sin(r); return [[-1, -1], [1, -1], [1, 1], [-1, 1]].map(([a, b]) => [p.x + c * a * p.w / 2 - s * b * p.d / 2, p.y + s * a * p.w / 2 + c * b * p.d / 2]); };
    const mod = (a, m) => ((a % m) + m) % m;
    out.backs = pcs.filter(p => p.kind === 'seat-back').map(b => {
      const r = { id: b.id, floor: b.floor, z: [b.z0, b.z1] }, cs = corners(b);
      const s = seats.find(q => cs.every(([x, y]) => { const [u, w] = local(q, x, y); return Math.abs(u) <= q.w / 2 + 1e-6 && Math.abs(w) <= q.d / 2 + 1e-6; }));
      r.seat = s ? s.family : null;
      if (s && s.family === 'check-in sofa') {            // its nearest edge, and the angle off parallel to it
        const us = cs.map(([x, y]) => local(s, x, y)), gaps = { w: Math.min(...us.map(q => s.w / 2 - Math.abs(q[0]))), d: Math.min(...us.map(q => s.d / 2 - Math.abs(q[1]))) };
        const k = gaps.w < gaps.d ? 'w' : 'd', ang = mod(b.rot - s.rot, 180);
        r.rim = Math.round(gaps[k] * 1000) / 1000; r.off = Math.round((k === 'd' ? Math.min(ang, 180 - ang) : Math.abs(90 - ang)) * 10) / 10;
      } else if (s) {                                     // the circle drawn in its box (radii w / 2 and d / 2): the back's outermost corner, its angle off square to the radius
        const rx = s.w / 2, ry = s.d / 2, outer = Math.max(...cs.map(([x, y]) => { const [u, w] = local(s, x, y); return Math.hypot(u / rx, w / ry); }));
        r.rim = Math.round((1 - outer) * (rx + ry) / 2 * 1000) / 1000;
        r.off = Math.round(Math.abs(90 - mod(b.rot - Math.atan2(b.y - s.y, b.x - s.x) * 180 / Math.PI, 180)) * 10) / 10;
      }
      const top = __host.downHit('F1', b.x, b.y, 2.5);
      r.top = top === null ? null : Math.round(top * 1000) / 1000;
      if (s) {                                            // on the seat, 0.25 m inside the back's inner face (towards the seat's middle)
        const vx = s.x - b.x, vy = s.y - b.y, L = Math.hypot(vx, vy) || 1, g = b.d / 2 + 0.25, sx = b.x + vx / L * g, sy = b.y + vy / L * g, d = __host.downHit('F1', sx, sy, 2.5);
        r.seatTop = d === null ? null : Math.round(d * 1000) / 1000;
      }
      return r;
    });
    return out; })()`);
  const cb = checkInSeats.backs, atRound = cb.filter(b => b.seat === 'round sofa').length, atSofa = cb.filter(b => b.seat === 'check-in sofa').length;
  check(`the check-in seating: Floor 1 has no computer box left (no kind 'computer', ${checkInSeats.computers.length} boxes called a computer, monitor, screen or laptop, the legend lists ${checkInSeats.legend.length} rows without 'Computer / monitor'); its ${cb.length} seat backs (kind seat-back, "${checkInSeats.kind && checkInSeats.kind.label}", ${checkInSeats.kind && checkInSeats.kind.height} mm, ${checkInSeats.kind && checkInSeats.kind.colour}) stand on the floor at the rims of the round sofa (${atRound}) and the check-in sofa (${atSofa}), seats of 450 mm: outer face ${Math.min(...cb.map(b => b.rim))} - ${Math.max(...cb.map(b => b.rim))} m inside the rim, ${Math.max(...cb.map(b => b.off))} degrees at most off its line; tops at ${[...new Set(cb.map(b => b.top))].join(' / ')} m over seats at ${[...new Set(cb.map(b => b.seatTop))].join(' / ')} m`,
    !checkInSeats.kinds.includes('computer') && !checkInSeats.computers.length && !checkInSeats.legend.some(l => /computer|monitor/i.test(l)) && checkInSeats.legend.includes(`Seat back (${cb.length})`)
    && !!checkInSeats.kind && checkInSeats.kind.label === 'Seat back' && checkInSeats.kind.height === 800 && checkInSeats.kind.base === 0 && checkInSeats.kind.colour.toLowerCase() !== '#7b3fb5' && checkInSeats.kind.count === 5 && !checkInSeats.kind.onTop
    && checkInSeats.seats.length === 2 && checkInSeats.seats.every(s => Math.abs(s.top - 0.45) < 0.005)
    && cb.length === 5 && atRound === 4 && atSofa === 1 && cb.every(b => b.floor === 'F1' && b.z[0] === 0 && b.z[1] === 0.8 && b.rim >= 0 && b.rim <= 0.25 && b.off <= 15
      && b.top !== null && Math.abs(b.top - 0.8) < 0.005 && b.seatTop !== null && Math.abs(b.seatTop - 0.45) < 0.005), checkInSeats);

  // ------------------------------------------------------------------ the furniture boxes, shown
  async function furnitureChecks() {
    await setFurniture(true);
    await P.evaluate('__viewer.setMode("orbit")');
    await clickSel('#floors [data-f=both]'); await sleep(200);
    const model = await P.evaluate(`(() => { const M = __host.model; return { kinds: M.furnitureKinds, pieces: M.furniture.map(p => [p.id, p.kind, p.floor, p.on, p.approach || []]), floors: M.floors.map(f => f.key), openings: M.openings.map(o => [o.id, o.floor, o.kind]) }; })()`);
    const nBoxes = model.pieces.length;
    const inApproach = model.pieces.filter(p => p[4].length);               // the pieces the builder put in the approach of a door or a passage

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
    check(`the furniture legend: one row per kind of the model (${model.kinds.length}) in table order, with its count (${model.kinds.reduce((n, k) => n + k.count, 0)} boxes in all), its colour, the default height in mm in a text box, and the show and stops ticks; above them the tick "Keep doorways clear", ticked`,
      legend.title === 'Furniture boxes' && legend.master && legend.rows.length === model.kinds.length && !legendBad.length && legend.buttons.join('|') === 'Reset heights|Save list (CSV)'
      && legend.keep && legend.keep.checked && legend.keep.text === 'Keep doorways clear' && legend.keep.n === 1
      && model.kinds.reduce((n, k) => n + k.count, 0) === nBoxes, legendBad.length ? legendBad : legend.rows.map(r => `${r.label} ${r.h}`));

    // (b) a box per piece, in its floor's group, named furn:<kind>:<id>
    const made = await P.evaluate(`(() => { const FL = __host.FL, F = __host.furniture, pieces = Object.fromEntries(F.pieces().map(p => [p.id, p])), bad = [], names = new Set(), per = {}; let n = 0;
      for (const [key, f] of Object.entries(FL)) f.group.traverse(o => {
        if (!o.name.startsWith('furn:')) return;
        n++; names.add(o.name); per[key] = (per[key] || 0) + 1;
        const [, kind, id] = o.name.split(':'), p = pieces[id];
        if (!p || p.kind !== kind || p.floor !== key || o.parent !== f.group || F.meshOf(id) !== o) bad.push(o.name);
      });
      return { n, distinct: names.size, per, bad: bad.slice(0, 5), nBad: bad.length, perModel: Object.fromEntries(Object.keys(FL).map(k => [k, F.pieces().filter(p => p.floor === k).length])) }; })()`);
    check(`the scene holds ${nBoxes} furniture boxes, each a child of its own floor's group and named furn:<kind>:<id> (${Object.entries(made.per).map(([k, n]) => `${n} on ${k}`).join(', ')})`,
      made.n === nBoxes && made.distinct === nBoxes && made.nBad === 0 && JSON.stringify(made.per) === JSON.stringify(made.perModel), made.nBad ? made.bad : { perFloor: made.per });

    // the page's own controls leave the boxes alone: the ticks (applyChecks), the floor buttons, the legend text
    const own = await P.evaluate(`(async () => {
      const F = __host.furniture, ms = F.pieces().map(p => F.meshOf(p.id)), showing = m => { for (let n = m; n; n = n.parent) if (!n.visible) return false; return true; };
      const count = () => ms.filter(showing).length, click = id => { document.getElementById(id).click(); }, out = {};
      out.start = count();
      for (const id of ['plates', 'glass', 'rooms', 'picture']) click(id);
      out.ticksFlipped = count();
      for (const id of ['plates', 'glass', 'rooms', 'picture']) click(id);
      out.ticksBack = count();
      F.setVisible('plant', false); click('plates'); click('glass'); click('plates'); click('glass');
      out.plantHidden = count();
      F.setVisible('plant', true);
      const perFloor = {};
      for (const key of ['F1', 'F2', 'both']) { document.querySelector('#floors [data-f=' + key + ']').click(); perFloor[key] = ms.filter(showing).length; }
      out.perFloor = perFloor;
      const panel = document.getElementById('panel'), last = panel.lastElementChild, lg = panel.querySelector('.legend');
      out.panel = { fbLast: last.matches('.fb-block') || !!last.querySelector(':scope > .fb-block'), legendSwatches: lg.querySelectorAll('span').length,
        legendHasFurniture: !!lg.querySelector('[class^=fb-]') || /furniture/i.test(lg.textContent),
        legendText: lg.textContent.startsWith('Walls and door lintels') && lg.lastElementChild.textContent.startsWith('Floor plates: the inside of the walls and glass') };
      return out; })()`);
    const perModel = Object.fromEntries(model.floors.map(k => [k, model.pieces.filter(p => p[2] === k).length]));
    check(`the page's own controls leave the boxes alone: Floor plates / Glass / Room names / Plan picture ticks (and a hidden kind stays hidden through them), the floor buttons show ${model.floors.map(k => `${perModel[k]} on ${k}`).join(' / ')}, the legend is as it was and the furniture list is last in the panel`,
      own.start === nBoxes && own.ticksFlipped === nBoxes && own.ticksBack === nBoxes && own.plantHidden === nBoxes - model.kinds.find(k => k.key === 'plant').count
      && model.floors.every(k => own.perFloor[k] === perModel[k]) && own.perFloor.both === nBoxes && own.panel.fbLast && !own.panel.legendHasFurniture
      && own.panel.legendSwatches >= 4 && own.panel.legendText, own);

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
      await P.shot(path.join(OUT, `panel_${w}x${h}.png`));
      await P.evaluate(`document.getElementById('panel').scrollTop = 0`); await sleep(150);
      await P.shot(path.join(OUT, `panel_${w}x${h}_top.png`));
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
    check(`the side panel's bottom edge stays above the hint line at every window height from 640 to 1080 px (${hintGaps.map(([s, g]) => `${s}: ${g} px`).join(', ')})`, hintGaps.every(([, g]) => g >= 4), hintGaps);
    await tab.send('Emulation.clearDeviceMetricsOverride'); await sleep(500);
    await P.evaluate(`document.getElementById('panel').scrollTop = 0`);

    // (c) typing 600 into the table's height box: every table's top is at 0.60 m (as the page's own downHit finds it, looking down from 2.5 m at a spot on the table),
    // what stands on the tables follows, what stands on a counter or a cabinet does not, every other box stays as it was, and Reset brings it all back. Since
    // 2 Nov (the owner: the check-in's purple 'screens' are seat backs) nothing of the hotel stands on a table: the pieces on tables are as many as the model
    // has (none), and the five seat backs, which stood on the round table as screens, are among the boxes that must stay put on the floor.
    const kindById = Object.fromEntries(model.pieces.map(p => [p[0], p[1]]));
    const onTables = model.pieces.filter(p => p[3] && kindById[p[3]] === 'table').map(p => p[0]), onOthers = model.pieces.filter(p => p[3] && kindById[p[3]] !== 'table').map(p => p[0]);
    const rest = model.pieces.filter(p => p[1] !== 'table' && !p[3]).map(p => p[0]), backsIds = model.pieces.filter(p => p[1] === 'seat-back').map(p => p[0]);
    const spots = (await T(`T.topSpots('table')`)).filter(t => t.spot), tableTop = model.kinds.find(k => k.key === 'table').height / 1000, nTables = model.pieces.filter(p => p[1] === 'table').length;
    const nOnTablesModel = await P.evaluate(`__host.model.furniture.filter(p => p.on && __host.model.furniture.find(q => q.id === p.on).kind === 'table').length`);
    const readings = () => P.evaluate(`(() => { const F = __host.furniture, pcs = Object.fromEntries(F.pieces().map(p => [p.id, p])), L = Object.fromEntries(__host.floors.map(f => [f.key, f.level]));
      return { up: ${JSON.stringify(spots)}.map(t => { const u = __host.downHit(t.floor, t.spot[0], t.spot[1], 2.5); return [t.id, u === null ? null : Math.round(u * 1000) / 1000]; }),
        tables: F.pieces().filter(p => p.kind === 'table').map(p => [p.z0, p.z1]), on: ${JSON.stringify(onTables)}.map(id => [pcs[id].kind, pcs[id].z0, Math.round((F.meshOf(id).position.y - L[pcs[id].floor]) * 1000) / 1000]),
        others: ${JSON.stringify(onOthers)}.map(id => pcs[id].z0), rest: ${JSON.stringify(rest)}.map(id => [pcs[id].z0, pcs[id].z1, Math.round((F.meshOf(id).position.y - L[pcs[id].floor]) * 1000) / 1000]),
        backs: ${JSON.stringify(backsIds)}.map(id => [pcs[id].z0, pcs[id].z1]),
        box: document.querySelector('.fb-row[data-k="table"] .fb-h').value, edited: document.querySelectorAll('.fb-h.fb-edited').length,
        stored: (() => { try { return Object.keys(localStorage).filter(k => k.startsWith('walkthrough-furniture')).length; } catch (e) { return 'blocked'; } })() }; })()`);
    const before = await readings();
    await typeHeight('table', 600);
    const at600 = await readings();
    await P.shot(path.join(OUT, 'furniture_table_600.png'));
    await clickSel('.fb-reset');
    const reset = await readings();
    const nearly = (a, b, tol = 0.006) => Math.abs(a - b) <= tol;
    const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);
    check(`typing 600 into the table height box: ${spots.length} of ${nTables} tables have their top at 0.60 m by the page's own downHit (${tableTop.toFixed(2)} m before), the ${onTables.length} pieces standing on tables (as in the model: ${nOnTablesModel}${onTables.length ? ': ' + [...new Set(at600.on.map(o => o[0]))].join(', ') : ''}) follow to 0.60 m, the ${onOthers.length} on a counter or cabinet and the ${rest.length} other boxes (the ${backsIds.length} seat backs among them, ${[...new Set(at600.backs.map(b => b.join(' - ')))].join(', ')} m) stay put; Reset brings it all back`,
      spots.length === nTables && nTables > 0 && onTables.length === nOnTablesModel && backsIds.every(id => rest.includes(id)) && before.up.every(([, z]) => nearly(z, tableTop)) && at600.up.every(([, z]) => nearly(z, 0.6)) && at600.tables.every(([z0, z1]) => z0 === 0 && z1 === 0.6) && at600.box === '600' && at600.edited === 1
      && at600.on.every(([, z0, y]) => z0 === 0.6 && nearly(y, 0.6, 0.002)) && at600.others.every((z, i) => z === before.others[i]) && rest.length > 0 && same(at600.rest, before.rest) && same(reset.rest, before.rest)
      && reset.up.every(([, z]) => nearly(z, tableTop)) && reset.box === String(tableTop * 1000) && reset.edited === 0 && reset.on.every(([, z0]) => z0 === tableTop) && reset.stored === 0,
      { tables: spots.length, upBefore: before.up.map(u => u[1]), upAt600: at600.up.map(u => u[1]), standingOn: at600.on, restMoved: rest.filter((id, i) => !same(at600.rest[i], before.rest[i])), reset: { up: reset.up.map(u => u[1]), box: reset.box, edited: reset.edited, stored: reset.stored } });

    // Walk starts clear of the boxes wherever the Orbit view was looking: from 15 spots over each floor the start is on that floor's floor, has 0.5 m of
    // room around it (the boxes count) and no box holds the player: the faces are single-sided, so the start may be inside a box, and the player walks out of it
    const starts = await P.evaluate(`(() => { const v = __viewer, s = v.state, out = [];
      let seed = 11; const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
      for (const key of ['F1', 'F2']) {
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
    check(`Walk starts clear of the boxes wherever the Orbit view looks: from ${starts.length} spots over the two floors the start is on its own floor, has at least 0.5 m of room around it and is not held by a box (${starts.filter(r => r.inBox.length).length} start inside a box and walk out of it)`,
      starts.length === 30 && !badStart.length, badStart.length ? badStart : { leastRoom: r2(Math.min(...starts.map(r => r.clearance))), insideABox: starts.filter(r => r.inBox.length).map(r => `${r.inBox.join('+')} (${r2(r.best)} m)`) });

    // (d) Walk stops at real boxes: every shown box that stops you and that Walk's rays can meet (knee 0.35 m or chest 1.2 m), approached on a free
    // line straight at one face from 1 m (nearer where something else stands in the way: 0.8, 0.65, 0.5 m): you stop short of the face, never inside, never through
    await P.press('Digit2'); await P.evaluate(`__viewer.goToFloor('F1')`);
    const tg = await T(`T.targets()`);
    const walkable = tg.filter(t => t.side !== null);
    const walks = [];
    for (const t of walkable) walks.push({ ...(await T(`T.walk(__host.furniture.pieces().find(p => p.id === ${JSON.stringify(t.id)}), ${t.side}, ${t.back}, false)`)), kind: t.kind });
    const byKind = {};
    for (const t of tg) { const b = byKind[t.kind] = byKind[t.kind] || { spans: 0, tested: 0, from1m: 0 }; b.spans++; if (t.side !== null) { b.tested++; if (t.back === 1) b.from1m++; } }
    const covered = Object.keys(byKind).filter(k => byKind[k].tested > 0), from1m = Object.keys(byKind).filter(k => byKind[k].from1m > 0), noLine = Object.keys(byKind).filter(k => byKind[k].tested === 0);
    const gaps = walks.filter(w => w.start).map(w => w.gap), notStopped = walks.filter(w => !stopped(w));
    const never = model.kinds.map(k => k.key).filter(k => !byKind[k]);
    check(`Walk stops at real boxes: ${walks.length} of ${tg.length} pieces that Walk's rays can meet had a free line (${walks.filter(w => w.back === 1).length} from 1 m, the rest from 0.8 - 0.5 m), covering ${covered.length} kinds (${from1m.length} of them from 1 m); each stops short of its face (gap ${gaps.length ? r2(Math.min(...gaps)) : '-'} - ${gaps.length ? r2(Math.max(...gaps)) : '-'} m), never inside, never through`,
      walks.length >= 20 && from1m.length >= 4 && notStopped.length === 0, notStopped.length ? notStopped : { perKind: Object.fromEntries(Object.entries(byKind).map(([k, b]) => [k, `${b.tested}/${b.spans} (${b.from1m} from 1 m)`])) });
    note('kinds with no free line to any of their pieces (information)', noLine.map(k => `${k} (${tg.filter(t => t.kind === k).map(t => t.why.replace(/ at [0-9.]+ m/, '')).filter((x, i, a) => a.indexOf(x) === i).join(' / ')})`));
    note('kinds no piece of which spans a Walk ray at its default height (a step-over height or hanging above the chest ray): the box never stops you', never);

    // (c) the boxes in a doorway's approach: with the tick on they are no targets (the walk above left them out); with it off they are targets like
    // the others, and those with a free line stop you short of their face, while with it on the same walk goes on past their face
    const flaggedIds = inApproach.map(p => p[0]);
    check(`Keep doorways clear on: none of the ${flaggedIds.length} box${flaggedIds.length === 1 ? '' : 'es'} in an approach (${flaggedIds.join(', ')}) is among the ${tg.length} pieces Walk stops at, and all of the others that Walk's rays can meet are`,
      flaggedIds.length > 0 && !tg.some(t => flaggedIds.includes(t.id)) && tg.length === (await F(`F.pieces().filter(p => p.blocking && ((p.z0 < 0.33 && p.z1 > 0.37) || (p.z0 < 1.18 && p.z1 > 1.22))).length`)), { listed: tg.length, flagged: flaggedIds });
    await F(`F.setKeepDoorways(false)`);
    const tgOff = await T(`T.targets()`);
    const fTargets = tgOff.filter(t => t.side !== null && flaggedIds.includes(t.id));
    const fOff = [];
    for (const t of fTargets) fOff.push(await T(`T.walk(__host.furniture.pieces().find(p => p.id === ${JSON.stringify(t.id)}), ${t.side}, ${t.back}, false)`));
    await F(`F.setKeepDoorways(true)`);
    const fOn = [];
    for (const t of fTargets) fOn.push(await T(`T.walkTo(__host.furniture.pieces().find(p => p.id === ${JSON.stringify(t.id)}), ${t.side}, ${t.back}, ${t.back + 0.5})`));
    const tgOnAgain = await T(`T.targets()`);
    // the box is no collider: the same walk gets over its face line, or - a small box with a wall or a seat right behind it - comes at least 0.2 m nearer
    // than where the box stopped it, and is then stopped by what stands behind it (Walk keeps 0.3 m from whatever stops it)
    const noStop = (w, off) => w.gap < -0.05 || (off && w.gap <= off.gap - 0.2);
    check(`the walk-stop check for the boxes in an approach: ${fTargets.length} of the ${flaggedIds.length} ha${fTargets.length === 1 ? 's' : 've'} a free line - with Keep doorways clear off it stops you short of its face (gap ${fOff.length ? r2(Math.min(...fOff.map(w => w.gap))) : '-'} m), with it on the same walk does not stop there (gap ${fOn.length ? fOn.map(w => r2(w.gap)).join(' / ') : '-'} m: past the face, or stopped by what stands behind the box)`,
      fTargets.length >= 1 && fOff.every(stopped) && fOn.every((w, i) => noStop(w, fOff[i])) && tgOnAgain.length === tg.length,
      { off: fOff.map(w => ({ id: w.id, gap: r2(w.gap), moved: r2(w.moved) })), on: fOn.map(w => ({ id: w.id, gap: r2(w.gap), moved: r2(w.moved) })), noLine: tgOff.filter(t => t.side === null && flaggedIds.includes(t.id)).map(t => `${t.id}: ${t.why}`) });

    // (e) the show tick: the same walk goes through a piece once its kind is unticked (a real click), and stops again when it is ticked. The chairs first
    // (as on the bank page); a kind of which fewer than two pieces have a free line right across them gives way to the next
    let hk = null, chairs = [];
    for (const kind of ['seat', 'sofa', 'coffee-table', 'cabinet', 'counter']) { chairs = await T(`T.crossable(${JSON.stringify(kind)}, 3)`); if (chairs.length >= 2) { hk = kind; break; } }
    const walkChair = (c, thru) => T(`T.walk(__host.furniture.pieces().find(p => p.id === ${JSON.stringify(c.id)}), ${c.side}, ${c.back}, ${thru}, ${thru ? JSON.stringify(hk) : 'null'})`);
    const tick = [];
    for (const c of hk ? chairs : []) {
      const a = await walkChair(c, false);
      await clickSel(rowSel(hk, 'show'));
      const off = await walkChair(c, true), inCol = await F(`__host.FL[${JSON.stringify(c.floor)}].colliders.includes(F.meshOf(${JSON.stringify(c.id)})) || F.meshOf(${JSON.stringify(c.id)}).visible`);
      await clickSel(rowSel(hk, 'show'));
      const on = await walkChair(c, false);
      tick.push({ id: c.id, stops: stopped(a), through: passed(off), gone: !inCol, stopsAgain: stopped(on), from: c.back });
    }
    check(`a hidden kind does not stop you: unticking show for "${hk}", the same walk (from ${chairs.map(c => c.back).join(' / ')} m) goes right through ${chairs.length} real pieces (${chairs.map(c => c.id).join(', ')}) and they leave the colliders; ticking it again, they stop you again`,
      !!hk && chairs.length >= 2 && tick.every(t => t.stops && t.through && t.gone && t.stopsAgain), tick);

    // (f) the same pieces typed 300 mm high are stepped over (Walk's knee ray at 0.35 m passes above them); at their default height they stop you
    const heights = [], hDefault = hk ? model.kinds.find(k => k.key === hk).height : 0;
    for (const mm of hk ? [300, hDefault] : []) {
      await typeHeight(hk, mm);
      const w = [];
      for (const c of chairs) w.push(mm === 300 ? await walkChair(c, true) : await walkChair(c, false));
      heights.push([mm, w.every(x => (mm === 300 ? passed(x) : stopped(x))), w.map(x => x.start ? `${r2(x.moved)} m, gap ${r2(x.gap)}` : x.why)]);
    }
    await clickSel('.fb-reset');
    check(`a ${hk} height typed as 300 mm is stepped over (the walk goes right across all ${chairs.length}), ${hDefault} mm stops you (short of the face)`, heights.length === 2 && heights.every(h => h[1]), heights);

    // (g) Ghost flies through a real table and a real counter that stop Walk: in front of the face at half the box's height, W held until you are 0.3 m past the far face
    const ghost = [];
    for (const kind of ['table', 'counter']) {
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
    check(`Ghost flies straight through a real table and a real counter (${ghost.map(g => g.id).join(', ')}) at half their height, both pieces that stop Walk short of their face`, ghost.length === 2 && ghost.every(g => g.ok), ghost);
    await P.press('Digit1');

    // the doors and passages again, with the boxes shown and Keep doorways clear on (the default): the boxes the builder put in an opening's approach are
    // no colliders, so every door and passage can be walked through its middle, both ways. An opening that still has some other box near its approach (the
    // walk starts nearer, or is cut short) is counted and listed. Then the same walks with the tick off.
    await P.press('Digit2'); await P.evaluate(`document.activeElement && document.activeElement.blur()`);
    const walkDoors = async () => {
      const out = [];
      for (const key of ['F1', 'F2']) {
        await P.evaluate(`__viewer.goToFloor(${JSON.stringify(key)})`);
        out.push(...await P.evaluate(doorWalks(true)));
      }
      return out;
    };
    const withBoxes = await walkDoors();
    const piecesOf = ts => [...new Set(ts.flatMap(t => (t.near || t.stoppedBy || []).map(p => `${p.id} (${p.kind}, ${String(p.family).slice(0, 34)})`)))];
    const inWayOf = walks2 => {
      const out = [];
      for (const d of walks2) {
        const h = all.find(a => a.id === d.id);
        const sides = ['fwd', 'back'].filter(k => d[k] !== h[k]);
        if (!sides.length) continue;
        out.push({ id: d.id, kind: d.kind, ok: d.ok, structure: { fwd: h.fwd, back: h.back }, withBoxes: { fwd: d.fwd, back: d.back }, pieces: piecesOf(sides.flatMap(k => d[k + 'Tries'])) });
      }
      return out;
    };
    // (what the boxes change: an opening that cannot be walked through without them either is the structure check's, above, and not counted again)
    const openWithout = id => all.find(a => a.id === id).ok, notOpen = all.filter(a => !a.ok).map(a => a.id);
    const inWay = inWayOf(withBoxes), cut = withBoxes.filter(d => !d.ok && openWithout(d.id));
    for (const d of inWay) note(`${d.id}${d.kind === 'passage' ? ' (a passage)' : ''}: a box near the approach that the builder did not flag, ${d.ok ? 'still passable' : 'CANNOT be walked through'} (without boxes ${d.structure.fwd} / ${d.structure.back} m past the line, with ${d.withBoxes.fwd} / ${d.withBoxes.back})`, d.pieces);
    check(`with the boxes on and Keep doorways clear on, every door and passage that is open without the boxes (${withBoxes.length - notOpen.length} of ${withBoxes.length}${notOpen.length ? `; not ${notOpen.join(', ')}, see above` : ''}) can be walked through its middle, both ways (${inWay.length} still have another box near their approach: ${inWay.map(d => d.id).join(', ') || 'none'})`,
      withBoxes.length === all.length && cut.length === 0, cut.length ? cut.map(d => ({ id: d.id, fwd: d.fwd, back: d.back, pieces: piecesOf(['fwd', 'back'].flatMap(k => d[k + 'Tries'])) })) : { nearTheApproach: inWay.map(d => d.id) });

    // the tick's effect, measured: with Keep doorways clear off, every door or passage the boxes then block is one whose approach list names a piece
    await F(`F.setKeepDoorways(false)`);
    const offWalks = await walkDoors();
    await F(`F.setKeepDoorways(true)`);
    const blockedOff = offWalks.filter(d => !d.ok && openWithout(d.id));
    const flaggedFor = id => inApproach.filter(p => p[4].includes(id)).map(p => p[0]);
    for (const d of blockedOff) note(`${d.id}: blocked by boxes with the tick off (without boxes ${all.find(a => a.id === d.id).fwd} / ${all.find(a => a.id === d.id).back} m past the line, with ${d.fwd} / ${d.back})`,
      { pieces: piecesOf(['fwd', 'back'].flatMap(k => d[k + 'Tries'])), inItsApproachList: flaggedFor(d.id) });
    check(`with Keep doorways clear off the boxes block ${blockedOff.length} door${blockedOff.length === 1 ? '' : 's'} or passage${blockedOff.length === 1 ? '' : 's'} (${blockedOff.map(d => d.id).join(', ') || 'none'}), each named by a piece's approach list; the openings with a piece in their approach: ${[...new Set(inApproach.flatMap(p => p[4]))].join(', ')}`,
      blockedOff.every(d => flaggedFor(d.id).length > 0), { blocked: blockedOff.map(d => `${d.id} <- ${flaggedFor(d.id).join(', ')}`) });

    // the colliders against the approach lists, read from the page: with the tick on every piece with a non-empty approach is out of the colliders and every
    // other piece of a blocking kind is in; with it off all of them are in (the page's lists are the model's)
    const rule = await P.evaluate(`(() => { const F = __host.furniture, FL = __host.FL, M = __host.model, kb = Object.fromEntries(M.furnitureKinds.map(k => [k.key, k.blocks !== false])), out = {};
      const inCol = () => new Set(Object.values(FL).flatMap(f => f.colliders.filter(m => m.name.startsWith('furn:')).map(m => m.userData.id)));
      const state = keep => { F.setKeepDoorways(keep); const c = inCol(), ps = F.pieces(); return M.furniture.filter(p => kb[p.kind]).map(p => [p.id, c.has(p.id), (p.approach || []).length > 0, ps.find(q => q.id === p.id).blocking]); };
      out.on = state(true); out.off = state(false); F.setKeepDoorways(true); out.keep = F.keepDoorways();
      out.lists = F.pieces().map(p => p.id + ':' + p.approach.join()).join('|') === M.furniture.map(p => p.id + ':' + (p.approach || []).join()).join('|');
      out.checked = document.querySelector('.fb-keep').checked; return out; })()`);
    const wrongOn = rule.on.filter(([, inCol, flagged, blocking]) => inCol === flagged || blocking !== inCol), wrongOff = rule.off.filter(([, inCol, , blocking]) => !inCol || !blocking);
    check(`the colliders against the approach lists (read from the page): with the tick on the ${inApproach.length} piece${inApproach.length === 1 ? '' : 's'} with an approach ${inApproach.length === 1 ? 'is' : 'are'} out and the other ${rule.on.length - inApproach.length} pieces of blocking kinds are in; with it off all ${rule.off.length} are in; pieces() says the same (blocking); the lists are the model's`,
      inApproach.length > 0 && rule.on.length === nBoxes && !wrongOn.length && !wrongOff.length && rule.lists && rule.keep === true && rule.checked, { wrongOn: wrongOn.slice(0, 4), wrongOff: wrongOff.slice(0, 4) });

    // the glass again with the boxes shown: it still stops you from every side that can be reached, never lets you through; the sides a box stands in front of are listed
    const glassOn = [];
    for (const key of ['F1', 'F2']) { await P.evaluate(`__viewer.goToFloor(${JSON.stringify(key)})`); glassOn.push(...await P.evaluate(glassWalks(true))); }
    const reach = glassOn.filter(g => g.stoppedAt !== null), cutG = glassOn.filter(g => !g.ok);
    const throughOn = reach.filter(g => g.stoppedAt <= 0.1);
    check(`with the boxes on the glass still stops you: ${reach.length} of ${glassOn.length} glass sides can be reached and none lets you through (${glassOn.length - reach.length} have a box right at the start spot, ${reach.filter(g => !g.ok).length} stop you at a box first)`,
      glassOn.length > 0 && throughOn.length === 0, throughOn.length ? throughOn : { sides: glassOn.length });
    note(`glass sides with a box in front, so that the walk to them is cut short (information): ${cutG.length} of ${glassOn.length}`,
      cutG.map(g => `${g.id} (${g.what}, side ${g.side}): ${g.stoppedAt === null ? 'no start' : g.stoppedAt + ' m short'} - ${piecesOf(g.tries).join(', ')}`));

    // with every wall and every box in the way: from 40 random spots outside the boxes, walking at the nearest thing never takes you through it
    const wallsOn = [];
    for (const key of ['F1', 'F2']) { await P.evaluate(`__viewer.goToFloor(${JSON.stringify(key)})`); wallsOn.push(await P.evaluate(wallWalks(true))); }
    check(`with the boxes on: walking into the nearest wall or box from 40 random spots outside the boxes on each floor, never through it and never ending up inside it (${wallsOn.map(w => `${w.floor}: ${w.skippedInABox} spots inside a box skipped`).join(', ')})`,
      wallsOn.map(w => w.floor).join() === 'F1,F2' && wallsOn.every(w => w.tried >= 30 && w.wentThrough === 0 && w.endedInsideWall === 0), wallsOn);

    // (d) not trapped. The faces of a box are single-sided, so Walk's rays from inside a box meet nothing of it: Walk entered at the middle of a box (the
    // double-click path: Orbit, then Walk at the box) puts the player inside a box, and he can always walk out. verdict(): A = walks out (1 m or more in some
    // direction of 8) or is in no box; B = does not, but would with only the boxes around him (a pocket of other boxes: information); C = a box holds him itself.
    const mids = await F(`F.pieces().filter(p => p.blocking).map(p => p.id)`);
    const into = await P.evaluate(`(() => { const out = [];
      for (const id of ${JSON.stringify(mids)}) { __t.spawn(id); out.push({ id, ...__t.verdict() }); }
      __viewer.setMode('orbit'); __viewer.setMode('walk'); return out; })()`);
    const heldBy = into.filter(r => r.class === 'C'), inBox = into.filter(r => r.inside.length), pockets = into.filter(r => r.class === 'B');
    note('Walk entered in a pocket of overlapping boxes (information: nothing holds the player but other boxes)', pockets.map(r => `${r.id} in ${r.inside.join('+')}: ${r2(r.best)} m, ${r2(r.alone)} m with only those boxes`));
    check(`not trapped: Walk entered at the middle of each of the ${mids.length} boxes that stop you lands the player inside a box ${inBox.length} times; ${inBox.filter(r => r.class === 'A').length} walk out at once and ${pockets.length} are in a pocket of other boxes, none is held by a box itself`,
      mids.length === nBoxes - inApproach.length && inBox.length >= 10 && heldBy.length === 0, heldBy.length ? heldBy : { inside: inBox.length, pockets: pockets.map(r => r.id) });
    // ... and from a spot where a box is switched on under the player: its kind's show tick, its stops tick, a taller height (a seat, a table, a cabinet), the
    // doorways tick (each of the boxes in an approach)
    const pickPiece = (kind, flagged) => model.pieces.find(p => p[1] === kind && !!p[4].length === flagged);
    const scenarios = {};
    for (const kind of ['seat', 'table', 'cabinet']) {
      const plain = pickPiece(kind, false)[0];
      scenarios[kind] = await P.evaluate(`(() => { const F = __host.furniture, T = __t, out = {}, id = ${JSON.stringify(plain)}, kind = ${JSON.stringify(kind)};
        const run = (name, prepare, on) => { prepare(); T.standIn(id); const before = T.holding().includes(id); on(); out[name] = { id, before, ...T.verdict() }; };
        run('show', () => F.setVisible(kind, false), () => F.setVisible(kind, true));
        run('stops', () => F.setBlocks(kind, false), () => F.setBlocks(kind, true));
        run('height', () => F.setHeight(kind, 100), () => F.setHeight(kind, 450));
        F.reset(); return out; })()`);
    }
    const doorwaysAll = await P.evaluate(`(() => { const F = __host.furniture, T = __t, out = [];
      for (const p of F.pieces().filter(q => q.approach.length)) { F.setKeepDoorways(true); T.standIn(p.id); const before = T.holding().includes(p.id); F.setKeepDoorways(false); out.push({ id: p.id, before, ...T.verdict() }); }
      F.setKeepDoorways(true); return out; })()`);
    const scAll = Object.entries(scenarios).flatMap(([kind, sc]) => Object.entries(sc).map(([name, r]) => ({ label: `${kind}/${name}`, ...r })));
    const around = r => r.before === false && r.inside.includes(r.id);                         // the box was no obstacle to the player at the middle of it, and it is around him now
    check(`not trapped: a box switched on under the player (the show tick, the stops tick, typed taller: 100 -> 450 mm; a seat, a table, a cabinet: ${scAll.length} cases) does not hold him, nor does any of the ${doorwaysAll.length} box${doorwaysAll.length === 1 ? '' : 'es'} in an approach when the doorways tick is switched off under him`,
      scAll.every(r => around(r) && r.class !== 'C') && doorwaysAll.length === inApproach.length && doorwaysAll.every(r => around(r) && r.class !== 'C'),
      { held: [...scAll, ...doorwaysAll].filter(r => r.class === 'C').map(r => r.label || r.id), notAround: [...scAll, ...doorwaysAll].filter(r => !around(r)).map(r => r.label || r.id), pockets: [...scAll, ...doorwaysAll].filter(r => r.class === 'B').map(r => r.label || r.id) });
    await P.press('Digit1');

    // (h) the family list the page writes is the file the builder wrote (without its byte-order mark), byte for byte
    const csvFile = path.join(HERE, 'hotel_furniture_list.csv');
    if (existsSync(csvFile)) {
      await F(`F.reset()`);
      const page = Buffer.from(await F('F.csv()'), 'utf8'), file = readFileSync(csvFile), bom = file.subarray(0, 3).equals(Buffer.from([0xEF, 0xBB, 0xBF]));
      const same = bom && page.equals(file.subarray(3));
      const noted = page.toString('utf8').split('\r\n').filter(l => l.includes('in the approach of')).length;         // the notes say which opening's approach a box stands in
      check(`the page's csv() is hotel_furniture_list.csv without its byte-order mark, byte for byte (${page.length} bytes, ${(page.toString('utf8').match(/\r\n/g) || []).length - 1} rows), and ${noted} of its rows carr${noted === 1 ? 'ies' : 'y'} "in the approach of ..." (one per box in an approach: ${inApproach.length})`,
        same && noted === inApproach.length, same ? { identical: true, noted } : { page: page.length, file: file.length - 3, bom, firstDifference: [...page].findIndex((b, i) => b !== file[i + 3]) });
    } else check('hotel_furniture_list.csv is next to the test (the family list to compare the page with)', false);

    // (j) the label under the pointer in Orbit, over real boxes: kind, family and size
    await P.press('Digit1');
    await clickSel('#floors [data-f=F1]'); await sleep(500);
    const spotsHover = await T(`T.hoverSpots('F1', 4)`);
    const tipNow = () => P.evaluate(`(() => { const t = document.querySelector('.fb-tip'); return t && t.style.display === 'block' ? t.innerText : null; })()`);
    const hovers = [];
    for (const sp of spotsHover) {
      await P.mouse('mouseMoved', 1250, 40, { button: 'none' });
      for (let i = 0; i < 20 && (await tipNow()) !== null; i++) await sleep(100);
      await P.mouse('mouseMoved', sp.x, sp.y, { button: 'none' });
      let tip = null;
      for (let i = 0; i < 30 && tip === null; i++) { await sleep(100); tip = await tipNow(); }
      const label = model.kinds.find(k => k.key === sp.kind).label;
      const flat = x => String(x).replace(/\s+/g, ' '), text = tip && flat(tip);                // the label's lines are one run of text to compare
      hovers.push({ id: sp.id, kind: sp.kind, ok: !!tip && text.includes(label) && text.includes(flat(sp.family)) && text.includes(sp.size) && text.includes('Floor 1'), tip: text });
      if (sp === spotsHover[0]) await P.shot(path.join(OUT, 'furniture_hover.png'));
    }
    check(`Orbit: the pointer over ${spotsHover.length} real boxes of different kinds (${spotsHover.map(h => h.kind).join(', ')}) shows a label with the kind, the family, the size and the floor`,
      spotsHover.length >= 3 && hovers.every(h => h.ok), hovers.map(h => h.ok ? `${h.kind}: ${h.tip}` : h));
    await P.mouse('mouseMoved', 1250, 40, { button: 'none' });
    await clickSel('#floors [data-f=both]'); await sleep(300);
  }
  if (hasFurniture) await furnitureChecks();
  else note('this page has no furniture boxes: the furniture checks were skipped');
  await setFurniture(true);

  // ------------------------------------------------------------------ Walk at the check-in and at the bar (screenshots), the Camera
  // Facing a piece from a spot on the floor with room around it and no wall between the eye and the piece's top: the first of a few spots
  // round it, nearest the wanted direction first.
  const standFacing = (id, dist, bearing) => P.evaluate(`(() => { const v = __viewer, s = v.state, p = __host.furniture.pieces().find(q => q.id === ${JSON.stringify(id)});
    v.goToFloor(p.floor);
    const V3 = __t.THREE.Vector3, sight = new __t.THREE.Raycaster(), lv = __t.levelOf(p.floor);
    const walls = __host.FL[p.floor].colliders.filter(m => m.visible && !m.name.startsWith('furn:'));
    for (const db of [0, 20, -20, 40, -40, 60, -60, 90, -90]) for (const d of [${dist}, ${dist} - 0.5, ${dist} + 0.5]) {
      const a = (${bearing} + db) * Math.PI / 180, x = p.x + Math.cos(a) * d, y = p.y + Math.sin(a) * d;
      s.pos.x = x; s.pos.z = -y;
      if (!v.probe.onFloor() || v.probe.clearance() < 0.4) continue;
      const eye = new V3(x, lv + 1.6, -y), to = new V3(p.x, lv + p.z1, -p.y).sub(eye), far = to.length();
      sight.set(eye, to.normalize()); sight.far = far - 0.2;
      if (sight.intersectObjects(walls, false).length) continue;
      s.yaw = Math.atan2(-(p.x - x), p.y - y); s.pitch = -0.12;
      return { at: [Math.round(x * 100) / 100, Math.round(y * 100) / 100], facing: p.id, floor: p.floor, clearance: Math.round(v.probe.clearance() * 100) / 100 };
    }
    return null; })()`);
  // Standing near a plan spot (the first of a few spots round it on the floor, with room around it), looking at another spot, pitch in radians.
  const standAt = (key, x, y, tx, ty, pitch) => P.evaluate(`(() => { const v = __viewer, s = v.state; if (v.mode !== 'walk') v.setMode('walk'); v.goToFloor(${JSON.stringify(key)});
    for (const [dx, dy] of [[0, 0], [0.25, 0], [-0.25, 0], [0, 0.25], [0, -0.25], [0.5, 0], [-0.5, 0], [0, 0.5], [0, -0.5]]) {
      const px = ${x} + dx, py = ${y} + dy; s.pos.x = px; s.pos.z = -py;
      if (!v.probe.onFloor() || v.probe.clearance() < 0.35) continue;
      s.yaw = Math.atan2(-(${tx} - px), ${ty} - py); s.pitch = ${pitch};
      return { floor: s.floor.key, at: [Math.round(px * 100) / 100, Math.round(py * 100) / 100], clearance: Math.round(Math.min(9, v.probe.clearance()) * 100) / 100 };
    }
    return null; })()`);
  await P.press('Digit2'); await P.evaluate(`document.activeElement && document.activeElement.blur()`);
  const checkInSpot = await standFacing('F1-seat-004', 4.4, -100);       // the check-in's round sofa with its four seat backs, the sofa beside it, from the lobby to the south
  await sleep(700);
  await P.shot(path.join(OUT, 'walk_checkin.png'));
  note('Walk at the check-in', checkInSpot);
  const bar = await standFacing('F2-counter-004', 3.2, 0);               // the bar's east leg, from the east, looking west along the U
  await sleep(700);
  await P.shot(path.join(OUT, 'walk_bar.png'));
  note('Walk at the bar', bar);
  // Through the entrance from the forecourt: on the paving 0.32 m out from the RED BOX's outer doors, looking in through both doors; then 3.6 m on, in the lobby
  const ent = await P.evaluate(`(() => { const d = __host.openings.find(o => o.floor === 'F1' && /ENTRANCE/.test(o.label)); return d && { x: d.x, y: d.y, t: d.wallThickness / 2 }; })()`);
  if (ent) {
    const outside = await standAt('F1', ent.x, ent.y - ent.t - 0.32, ent.x, ent.y + 4, -0.04);
    await sleep(700);
    await P.shot(path.join(OUT, 'walk_entrance_forecourt.png'));
    const walkedIn = await P.evaluate(`(() => { const v = __viewer, s = v.state, m = v.probe.walk(0, 3.6); s.yaw = 0; s.pitch = -0.04; return { moved: Math.round(m * 100) / 100, at: [Math.round(s.pos.x * 100) / 100, Math.round(-s.pos.z * 100) / 100] }; })()`);
    await sleep(700);
    await P.shot(path.join(OUT, 'walk_entrance_lobby.png'));
    note('Walk through the entrance from the forecourt', { outside, walkedIn });
  }
  // Up to the iconic stair on Floor 2: from the south, looking down into the open stair over Floor 1's flight
  const flight = await P.evaluate(`(() => { const st = __host.model.parts.filter(p => p.kind === 'step' && p.floor === 'F1').flatMap(p => p.o); const xs = st.map(q => q[0]), ys = st.map(q => q[1]); return [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)]; })()`);
  const iconicSpot = await standAt('F2', (flight[0] + flight[2]) / 2, flight[1] - 1.85, (flight[0] + flight[2]) / 2, (flight[1] + flight[3]) / 2, -0.32);
  await sleep(700);
  await P.shot(path.join(OUT, 'walk_iconic_stair.png'));
  note('Walk up to the iconic stair on Floor 2', iconicSpot);
  await P.press('Digit1');
  await clickSel('#vm-cam-btn'); await P.press('KeyP'); await sleep(2500);
  const t = await P.evaluate(`(document.querySelector('#vm-photos img') || {}).title || ''`);
  const photoName = await P.evaluate('__host.model.photoName');
  check(`the Camera takes a 1920 x 1280 photo named after the project (${photoName}_Orbit_overview_...)`, new RegExp(`^${photoName}_Orbit_overview_.*\\(1920 x 1280\\)`).test(t), t.slice(0, 80));
  await clickSel('#vm-cam-btn');

  // ------------------------------------------------------------------ the model-data stamp, errors
  // The page carries the sha1 of the model file next to it, and the 3ds Max script beside the page the same (both generators stamp it).
  const modelFile = path.join(HERE, 'src', 'hotel_model.json');
  if (URL.startsWith('file:') && existsSync(modelFile)) {
    const sha = createHash('sha1').update(readFileSync(modelFile)).digest('hex').slice(0, 12);
    const stamp = await P.evaluate(`document.querySelector('meta[name="model-data"]').content`);
    check('the page carries the model-data stamp of the current hotel_model.json (the sha1 of the file)', stamp === sha, { page: stamp, file: sha });
    const page = fileURLToPath(URL), ms = path.join(path.dirname(page), 'Hotel_Lobby.ms');
    const sb2 = existsSync(ms) ? (readFileSync(ms, 'utf8').match(/model data ([0-9a-f]+)/) || [])[1] : 'no .ms file';
    check('the viewer and the 3ds Max script (Hotel_Lobby.ms) were made from the same model data', stamp === sb2, { viewer: stamp, maxScript: sb2 });
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
