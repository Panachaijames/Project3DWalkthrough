// Checks furniture_boxes.js in headless Edge, through fixtures/harness.html (the shared viewer modes and build replay, a bare
// scene with two levels) and the hand-made fixtures/mini_model.json: one box per piece in the right level group, placed from
// the model with the resolved heights (a computer on a 750 table stands at 0.75); the legend and its height text boxes, typed
// with real key events (applied as you type, Enter / leaving the box, junk goes back); Walk stopped by shown boxes that stop you
// (from 1 m, short of the face, never inside) and not by hidden ones, ones with the stops tick off, a kind that never stops
// you (the curtain) or a box lower than the knee ray; Ghost passing through; the family list (CSV) against Python's own
// formatting (fixtures/expected_csv.py) and against the builders' writer (furniture_kit.csv_text), its download and
// nodownload=1; the typed heights kept in localStorage (and a page whose storage is blocked); the hover label in Orbit; the
// build replay's late list; a model without furniture; and, when bank_test/src/bank_model.json carries furniture, that model
// (its walls and floor plates as the harness draws them) with the builder's 185 or so pieces.
// The boxes are single-sided, so a player inside one can always walk out: from the middle of every blocking box (and from a
// spot where a box is switched on under the player: the show and stops ticks, a taller height, the doorways tick) Walk is
// never held by the box itself. A first key typed within milliseconds of the click into a height box is not lost (the
// select-on-focus timer used to swallow it: 640 became 40). The tick 'Keep doorways clear' (the model's 'approach' ids): the
// boxes in a door's or passage's approach leave the colliders while it is on and come back with it off, its label, its
// storage next to the typed heights, and, on the bank model, Walk straight through the middle of every door they flank.
// Usage (from the project folder): node furniture/test_boxes.mjs
// FURN_PORT (default 9411) is the browser's debugging port; FURN_TMP (default %TEMP%\furniture-test) holds the browser
// profile (a fresh one per run) and the variant models, FURN_OUT (default <FURN_TMP>\out) the screenshots; EDGE another
// browser (see viewer-modes/cdp.mjs). The test stops at once if something already answers on the port (another session's
// browser): the shared launcher would attach to that browser and finally close it.
import { mkdirSync, readFileSync, writeFileSync, existsSync, rmSync } from 'node:fs';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { tmpdir } from 'node:os';
import { spawnSync } from 'node:child_process';
import path from 'node:path';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const CDP = [path.join(HERE, '..', 'viewer-modes', 'cdp.mjs')].find(p => existsSync(p));
const { launch, pageApi, sleep } = await import(pathToFileURL(CDP).href);
const TMP = process.env.FURN_TMP || path.join(tmpdir(), 'furniture-test');
const OUT = process.env.FURN_OUT || path.join(TMP, 'out');
mkdirSync(TMP, { recursive: true });                               // FURN_OUT may be anywhere: the variant models and the profile go to TMP
mkdirSync(OUT, { recursive: true });
const PAGE = pathToFileURL(path.join(HERE, 'fixtures', 'harness.html')).href;
const FIXTURE = path.join(HERE, 'fixtures', 'mini_model.json');
const ORACLE = path.join(HERE, 'fixtures', 'expected_csv.py');
const PORT = Number(process.env.FURN_PORT || 9411);
let busy = true;
try { await fetch(`http://127.0.0.1:${PORT}/json/version`, { signal: AbortSignal.timeout(1500) }); } catch { busy = false; }
if (busy) {
  console.error(`Port ${PORT} already answers (another browser is using it). Close it or set FURN_PORT to a free port.`);
  process.exit(2);
}
const results = [];
const check = (name, ok, info) => { results.push(!!ok); console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${info !== undefined ? '   ' + JSON.stringify(info) : ''}`); };
const note = (name, info) => console.log(`      ${name}${info !== undefined ? ': ' + JSON.stringify(info) : ''}`);
const r2 = v => Math.round(v * 100) / 100;
const near = (a, b, tol = 1e-6) => Math.abs(a - b) <= tol;
const t0 = Date.now();

// ---------------------------------------------------------------------- what the model says (worked out here, apart from the module)
const fx = JSON.parse(readFileSync(FIXTURE, 'utf8'));
const flagged = fx.furniture.filter(p => p.approach.length);        // the pieces that stand in the approach of a door or a passage (L1-seat-002, L2-seat-001)
function resolve(model, heights = {}) {                           // z0 / z1 in metres per piece, from the kinds table and the supports
  const kinds = Object.fromEntries(model.furnitureKinds.map(k => [k.key, { ...k, height: heights[k.key] ?? k.height }]));
  const byId = Object.fromEntries(model.furniture.map(p => [p.id, p]));
  const under = p => (p.on ? under(byId[p.on]) + kinds[byId[p.on].kind].height : kinds[p.kind].base);
  return model.furniture.map(p => ({ ...p, z0: under(p) / 1000, z1: (under(p) + kinds[p.kind].height) / 1000 }));
}
// the family list as Python writes it: from the contract (expected_csv.py), or by the builders' own writer (furniture_kit.csv_text)
const KIT = existsSync(path.join(HERE, 'furniture_kit.py'));
const python = (modelPath, heights, kit) => {
  const args = ['-B', ORACLE, modelPath];
  if (heights) { const hp = path.join(TMP, 'typed_heights.json'); writeFileSync(hp, JSON.stringify(heights)); args.push(hp); }
  if (kit) args.push('--kit');
  const r = spawnSync('python', args, { encoding: 'buffer', env: { ...process.env, PYTHONIOENCODING: 'utf-8' } });
  if (r.status !== 0) throw new Error('expected_csv.py failed: ' + r.stderr.toString());
  return r.stdout.toString('utf8');
};
// variants of the fixture: awkward text and numbers for the list; a kind nobody uses; a model without furniture
const variant = (name, edit) => { const m = structuredClone(fx); edit(m); const p = path.join(TMP, name); writeFileSync(p, JSON.stringify(m, null, 1)); return p; };
const awkward = variant('awkward_model.json', m => {
  m.furnitureKinds.unshift({ key: 'atm', label: 'ATM / kiosk', colour: '#c0392b', height: 1500, base: 0, onTop: false, support: false, blocks: true, count: 0 });
  const kind = Object.fromEntries(m.furnitureKinds.map(k => [k.key, k]));
  Object.assign(kind.seat, { height: 460.5 });                                                                                // office heights and bases that are not whole mm
  Object.assign(kind.plant, { base: 10.5 });
  const by = Object.fromEntries(m.furniture.map(p => [p.id, p]));
  Object.assign(by['L1-seat-001'], { family: 'Chair, "Lux" model', x: -1.0004, y: 0.0625 - 2.0, rot: 12.25, w: 0.0625 });       // a comma and quotes; -0.000; exact ties
  Object.assign(by['L1-seat-002'], { block: 'Block A\nsecond line', note: 'run of 4, "fronts"', rot: 0.75, w: 0.0635, d: 0.6005 });
  Object.assign(by['L1-seat-003'], { layer: 'I-FURN\rCR', x: 2.4995, y: -2.0004 });
  Object.assign(by['L1-plant-001'], { handle: '', family: '', rot: 179.95, n: 7 });
  // the levels are Z1, A2 in that order (not alphabetical): the list follows the model's floor order
  const key = { L1: 'Z1', L2: 'A2' }, rename = s => (s ? s.replace(/^L[12](?=-)/, x => key[x]) : s);
  m.floors.forEach(f => { f.key = key[f.key]; });
  m.furniture.forEach(p => { p.floor = key[p.floor]; p.id = rename(p.id); p.on = rename(p.on); });
  m.furniture.reverse();                                                                                                    // the list sorts, whatever the order in the file
});
const empty = variant('empty_model.json', m => { m.furnitureKinds = []; m.furniture = []; });
const broken = variant('broken_model.json', m => {               // data the builder should never write: left out with a warning, or a fall-back, never a crash
  const seat = m.furniture.find(p => p.id === 'L1-seat-001');
  m.furniture.find(p => p.id === 'L1-computer-001').on = 'L1-no-such-table';                 // a support that is not there: the computer stands on its kind's base
  m.furniture.push({ ...seat, id: 'L9-seat-001', floor: 'L9' });                                // a level the page does not have
  m.furniture.push({ ...seat, id: 'L1-sofa-001', kind: 'sofa' });                              // a kind the model does not list
});
const older = variant('older_model.json', m => {                 // a model from before 'approach' (or a builder that has no doors to look at): no piece is in an approach
  m.furniture.forEach(p => { delete p.approach; p.note = p.note.replace(/^in the approach of .*$/, ''); });
  m.furniture.find(p => p.id === 'L1-table-002').approach = 'L1-001';                          // not a list: no approach either
});
const modelUrl = p => '&model=' + encodeURIComponent(pathToFileURL(p).href);

// ---------------------------------------------------------------------- the browser
const profile = path.join(TMP, `profile-${process.pid}-${t0}`);
mkdirSync(profile, { recursive: true });
const { tab, browser, close } = await launch({ port: PORT, profile });
const P = pageApi(tab);
await browser.send('Browser.setDownloadBehavior', { behavior: 'deny' }).catch(() => {});      // a stray download must never land in the user's folder
const errors = [];
const flush = () => { errors.push(...P.logs.filter(l => /exception|error/i.test(l))); P.logs.length = 0; };
const open = async (query = '', page = PAGE) => { flush(); await P.goto(`${page}?build=0&nodownload=1${query}`); };
const F = expr => P.evaluate(`(() => { const F = __host.furniture; return ${expr}; })()`);
const scrollTo = sel => P.evaluate(`document.querySelector(${JSON.stringify(sel)}).scrollIntoView({ block: 'center' })`);
const clickSel = async sel => { await scrollTo(sel); await sleep(60); await P.clickEl(sel); await sleep(80); };
const rowSel = (k, part) => `.fb-row[data-k="${k}"] .fb-${part}`;
const boxText = k => P.evaluate(`document.querySelector(${JSON.stringify(rowSel(k, 'h'))}).value`);
const kindsNow = () => F('F.kinds()');
const rawKey = (type, o) => tab.send('Input.dispatchKeyEvent', { type, ...o });
async function typeChars(text) {                                   // real key events: keydown (the viewer sees it), the character, keyup
  for (const ch of text) {
    const o = { key: ch, code: /\d/.test(ch) ? 'Digit' + ch : 'Key' + ch.toUpperCase(), windowsVirtualKeyCode: ch.toUpperCase().charCodeAt(0) };
    await rawKey('keyDown', { ...o, text: ch }); await rawKey('keyUp', o);
  }
  await sleep(60);
}
const pressKey = async (key, code, vk) => { await rawKey('rawKeyDown', { key, code, windowsVirtualKeyCode: vk }); await rawKey('keyUp', { key, code, windowsVirtualKeyCode: vk }); await sleep(80); };
const focusBox = k => P.evaluate(`(() => { const e = document.querySelector(${JSON.stringify(rowSel(k, 'h'))}); e.scrollIntoView({ block: 'center' }); e.focus(); e.select(); return document.activeElement === e; })()`);
const typeInto = async (k, text) => { await focusBox(k); await typeChars(text); };
const blurBox = () => P.evaluate('document.activeElement && document.activeElement.blur()');
const modeNow = () => P.evaluate('__viewer.mode');
const hasClass = (sel, c) => P.evaluate(`document.querySelector(${JSON.stringify(sel)}).classList.contains(${JSON.stringify(c)})`);
const tipNow = () => P.evaluate(`(() => { const t = document.querySelector('.fb-tip'); return t && t.style.display === 'block' ? t.innerText : null; })()`);
const screenAt = (x, y, z) => P.evaluate(`(() => { const v = new THREE.Vector3(${x}, ${y}, ${z}).project(__host.camera); return [(v.x + 1) / 2 * innerWidth, (1 - v.y) / 2 * innerHeight]; })()`);
// Move the pointer to (x, y) from a clean start (the label cleared by a visit to an empty corner) and read the label there.
// shown: a label is expected, so wait for it (a slow machine draws a frame in 200 ms or more); else wait a little and read.
const hoverAt = async (x, y, shown = true) => {
  await P.mouse('mouseMoved', 1300, 60, { button: 'none' });
  for (let i = 0; i < 20 && (await tipNow()) !== null; i++) await sleep(100);
  await P.mouse('mouseMoved', x, y, { button: 'none' });
  await sleep(250);
  let t = await tipNow();
  for (let i = 0; shown && t === null && i < 25; i++) { await sleep(100); t = await tipNow(); }
  return t;
};

// In the page: stand in front of a face of a box, face it, walk, and report where you ended up.
function pageHelpers() {
  const F = __host.furniture, v = __viewer, s = v.state, V3 = THREE.Vector3;
  const frame = id => {
    const p = F.pieces().find(q => q.id === id), r = p.rot * Math.PI / 180;
    return { p, c: new V3(p.x, 0, -p.y), ax: new V3(Math.cos(r), 0, -Math.sin(r)), az: new V3(Math.sin(r), 0, Math.cos(r)) };
  };
  // side 0 / 1: the ends along its long axis, 2 / 3: the long faces. through: walk right across it (else 0.5 m more than the distance to the face)
  function walkAt(id, side, back, through) {
    const { p, c, ax, az } = frame(id);
    const n = [ax.clone(), ax.clone().negate(), az.clone(), az.clone().negate()][side], half = side < 2 ? p.w / 2 : p.d / 2;
    if (s.floor.key !== p.floor) v.goToFloor(p.floor);
    s.pos.x = c.x + n.x * (half + back); s.pos.z = c.z + n.z * (half + back);
    if (!v.probe.onFloor() || v.probe.clearance() < 0.6) return { id, side, start: false };
    const metres = through ? back + 2 * half + 0.6 : back + 0.5;
    const moved = v.probe.walk(Math.atan2(n.x, n.z) * 180 / Math.PI, metres);
    const rel = new V3(s.pos.x - c.x, 0, s.pos.z - c.z);
    return { id, side, start: true, metres, moved, gap: rel.dot(n) - half, inside: Math.abs(rel.dot(ax)) < p.w / 2 && Math.abs(rel.dot(az)) < p.d / 2 };
  }
  // Standing inside a box: Walk is entered at the middle of a box the way a double-click on it does (a level, a point), or the
  // player is put there. Can the player leave? Walk 1.5 m in 8 directions: the furthest you get. holding(): the blocking boxes
  // (taller than the knee ray) that hold the player's centre. only(ids, fn): fn with no furniture in the way but those boxes (the
  // walls stay). verdict(): A = leaves; B = does not, but would with only the boxes that hold the player in the way (a pocket of
  // other boxes: information); C = a box holds the player by itself (its own faces), which the single-sided faces rule out.
  const inFootprint = (q, x, z) => { const { c, ax, az } = frame(q.id), dx = x - c.x, dz = z - c.z; return Math.abs(dx * ax.x + dz * ax.z) < q.w / 2 && Math.abs(dx * az.x + dz * az.z) < q.d / 2; };
  const spans = q => (q.z0 < 0.35 && q.z1 > 0.35) || (q.z0 < 1.2 && q.z1 > 1.2);        // Walk's rays (knee, chest) can meet it
  const holding = () => F.pieces().filter(q => q.blocking && q.floor === s.floor.key && spans(q) && inFootprint(q, s.pos.x, s.pos.z)).map(q => q.id);
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
    if (!inside.length) return { class: 'A', inside };                // in no box: nothing holds the player
    const best = leave();
    if (best >= 1.0) return { class: 'A', inside, best };
    const base = only([], leave), alone = only(inside, leave);
    return { class: alone + 0.3 < Math.min(1.0, base) ? 'C' : 'B', inside, best, alone, base };
  }
  function spawn(id) {                                               // the double-click path: Orbit, then Walk at the middle of the box
    const p = F.pieces().find(q => q.id === id), f = __host.floors.find(x => x.key === p.floor);
    v.setMode('orbit'); v.setMode('walk', { floor: f, point: new V3(p.x, 0, -p.y) });
    return p;
  }
  function standIn(id) { const p = spawn(id); s.pos.x = p.x; s.pos.z = -p.y; return p; }       // exactly at the middle, wherever Walk found room
  // Walk straight through the middle of a door or passage of the model, both ways (as bank_test/test_bank.mjs does): metres past its line.
  function doorWalk(d) {
    const keep = s.pos.clone(), out = { id: d.id, kind: d.kind };
    if (s.floor.key !== d.floor) v.goToFloor(d.floor);
    for (const sign of [1, -1]) {
      const nx = d.nx * sign, ny = d.ny * sign, deg = Math.atan2(-nx, ny) * 180 / Math.PI;
      let along = null;
      for (const back of [0.9, 0.7, 0.55, 0.45, 0.4]) {
        s.pos.x = d.x - nx * back; s.pos.z = -(d.y - ny * back);
        if (!v.probe.onFloor() || v.probe.clearance() < 0.25) continue;
        v.probe.walk(deg, back * 2);
        along = (s.pos.x - d.x) * nx + (-s.pos.z - d.y) * ny;
        break;
      }
      out[sign > 0 ? 'fwd' : 'back'] = along === null ? null : Math.round(along * 100) / 100;
    }
    s.pos.copy(keep);
    out.ok = typeof out.fwd === 'number' && typeof out.back === 'number' && out.fwd > 0.3 && out.back > 0.3;
    return out;
  }
  window.__t = { frame, walkAt, holding, leave, only, verdict, spawn, standIn, doorWalk };
}
// In the page: a box is switched on under the player (its kind's show tick, its stops tick, a taller height, the doorways tick): the
// player stands at the middle of the box while it does not stop you, then it starts to. Each verdict says whether the player can leave.
function pageScenarios(plain, inApproach, kind) {                    // a box of that kind, and one of that kind that stands in an approach
  const F = __host.furniture, T = __t, out = {};
  const run = (name, id, prepare, on) => { prepare(); T.standIn(id); const before = T.holding().length; on(); out[name] = { id, before, ...T.verdict() }; };
  run('show', plain, () => F.setVisible(kind, false), () => F.setVisible(kind, true));
  run('stops', plain, () => F.setBlocks(kind, false), () => F.setBlocks(kind, true));
  run('height', plain, () => F.setHeight(kind, 100), () => F.setHeight(kind, 450));
  run('doorways', inApproach, () => F.setKeepDoorways(true), () => F.setKeepDoorways(false));
  F.reset(); F.setKeepDoorways(true);
  return out;
}
const SIDES = { 'L1-tall-cabinet-001': [0, 1, 2, 3], 'L1-coffee-table-001': [0, 1, 2, 3], 'L1-cabinet-001': [0, 1, 2, 3], 'L1-plant-001': [0, 1, 2, 3],
  'L1-table-002': [0, 1, 2, 3], 'L1-tv-001': [2, 3], 'L1-seat-003': [0, 1, 2, 3] };
const kindOfId = id => fx.furniture.find(p => p.id === id).kind;
const walks = (ids, through, sides = SIDES) => P.evaluate(`(() => { const out = [];
  for (const [id, ss] of Object.entries(${JSON.stringify(sides)})) { if (!${JSON.stringify(ids)}.includes(id)) continue; for (const s of ss) out.push(__t.walkAt(id, s, 1.0, ${through})); }
  return out; })()`);
const stopped = w => w.start && w.gap >= 0.25 && w.gap <= 0.42 && !w.inside && w.moved > 0.5 && w.moved < 0.8;     // short of the face, not inside, 0.6 - 0.7 m from the start
const passed = w => w.start && w.moved >= w.metres - 0.01 && w.gap < -0.2;                                          // right across it, out the other side
const walkedIn = w => w.start && w.moved >= w.metres - 0.01;                                                        // nothing stopped the walk, whether or not it got across
const brief = ws => ws.filter(w => w.start).map(w => `${w.id.replace('L1-', '')}/${w.side}: ${r2(w.moved)} m, gap ${r2(w.gap)}`);
const collidersOf = () => P.evaluate(`Object.fromEntries(Object.entries(__host.FL).map(([k, f]) => [k, f.colliders.filter(m => m.name.startsWith('furn:')).map(m => m.userData.id).sort()]))`);

try {
  // ------------------------------------------------------------------ the module in the page: one box per piece
  await open();
  const nPieces = fx.furniture.length, floors = fx.floors.map(f => f.key);
  const made = await P.evaluate(`(() => { const F = __host.furniture, FL = __host.FL, bad = [], ids = new Set();
    const per = {};
    for (const p of F.pieces()) {
      const m = F.meshOf(p.id);
      if (!m) { bad.push(p.id + ': no mesh'); continue; }
      ids.add(m.uuid);
      per[p.floor] = (per[p.floor] || 0) + 1;
      if (m.parent !== FL[p.floor].group) bad.push(p.id + ': not in the group of ' + p.floor);
      if (m.name !== 'furn:' + p.kind + ':' + p.id || /glass/i.test(m.name)) bad.push(p.id + ': name ' + m.name);
      if (!FL[p.floor].late.includes(m)) bad.push(p.id + ': not in late');
      const u = m.userData;
      if (u.id !== p.id || u.kind !== p.kind || u.family !== p.family || !Array.isArray(u.size) || u.size.length !== 3) bad.push(p.id + ': userData ' + JSON.stringify(u));
      if (!m.children.some(c => c.isLineSegments)) bad.push(p.id + ': no outline');
      if (m.geometry.boundsTree) bad.push(p.id + ': has a bounds tree');
    }
    const all = [];
    for (const f of Object.values(FL)) f.group.traverse(o => { if (o.name && o.name.startsWith('furn:')) all.push(o); });
    return { bad, distinct: ids.size, inGroups: all.length, per, late: Object.fromEntries(Object.entries(FL).map(([k, f]) => [k, f.late.filter(o => o.name.startsWith('furn:')).length])) }; })()`);
  check(`one mesh per piece (${nPieces}), each a child of its level's group and in its 'late' list, named furn:<kind>:<id> (no 'glass'), with userData and an outline`,
    made.bad.length === 0 && made.distinct === nPieces && made.inGroups === nPieces && fx.floors.every(f => made.per[f.key] === fx.furniture.filter(p => p.floor === f.key).length)
    && fx.floors.every(f => made.late[f.key] === made.per[f.key]), made.bad.length ? made.bad : { perLevel: made.per, late: made.late });

  // ------------------------------------------------------------------ placed from the model, with the resolved heights
  const expect = resolve(fx);
  const placed = await P.evaluate(`(() => { const exp = ${JSON.stringify(expect)}, F = __host.furniture, FL = __host.FL, kinds = Object.fromEntries(F.kinds().map(k => [k.key, k])), bad = [];
    const near = (a, b) => Math.abs(a - b) < 1e-6;
    for (const e of exp) {
      const m = F.meshOf(e.id), lv = FL[e.floor].level, c = new THREE.Color(kinds[e.kind].colour), mc = m.material.color;
      if (!near(m.position.x, e.x) || !near(m.position.y, lv + e.z0) || !near(m.position.z, -e.y)) bad.push(e.id + ' position ' + m.position.toArray());
      if (!near(m.scale.x, e.w) || !near(m.scale.y, e.z1 - e.z0) || !near(m.scale.z, e.d)) bad.push(e.id + ' scale ' + m.scale.toArray());
      if (!near(m.rotation.y, e.rot * Math.PI / 180) || !near(m.rotation.x, 0) || !near(m.rotation.z, 0)) bad.push(e.id + ' rotation ' + m.rotation.toArray());
      if (Math.abs(mc.r - c.r) + Math.abs(mc.g - c.g) + Math.abs(mc.b - c.b) > 1e-6) bad.push(e.id + ' colour');
      const top = new THREE.Box3().setFromObject(m.children[0]);                      // the outline: the box's own corners, in the world
      if (!near(top.min.y, FL[e.floor].group.position.y + lv + e.z0) || !near(top.max.y, lv + e.z1)) bad.push(e.id + ' extent ' + top.min.y + ' ' + top.max.y);
    }
    const got = F.pieces(), idx = Object.fromEntries(got.map(g => [g.id, g]));
    for (const e of exp) if (!near(idx[e.id].z0, e.z0) || !near(idx[e.id].z1, e.z1)) bad.push(e.id + ' pieces() ' + idx[e.id].z0 + ' ' + idx[e.id].z1);
    return { bad, n: exp.length, z: Object.fromEntries(['L1-computer-001', 'L1-printer-001', 'L1-table-001', 'L1-tv-001', 'L1-seat-001', 'L2-computer-001', 'L2-table-001'].map(i => [i, [idx[i].z0, idx[i].z1]])) }; })()`);
  check('every box stands at (x, level + z0, -y), is w x height x d, turned by rot and coloured by its kind; pieces() agrees with the model',
    placed.bad.length === 0 && placed.n === nPieces, placed.bad.length ? placed.bad : 'ok');
  check('resolved heights: a computer on a table stands at 0.75 (top 1.20), a printer on it 0.75 - 1.05, the table is 0 - 0.75, the wall TV hangs at 0.90 - 1.50, a chair is 0 - 0.45',
    near(placed.z['L1-computer-001'][0], 0.75) && near(placed.z['L1-computer-001'][1], 1.2) && near(placed.z['L1-printer-001'][0], 0.75) && near(placed.z['L1-printer-001'][1], 1.05)
    && near(placed.z['L1-table-001'][0], 0) && near(placed.z['L1-table-001'][1], 0.75) && near(placed.z['L1-tv-001'][0], 0.9) && near(placed.z['L1-tv-001'][1], 1.5)
    && near(placed.z['L1-seat-001'][1], 0.45) && near(placed.z['L2-computer-001'][0], 0.75), placed.z);

  // ------------------------------------------------------------------ the legend
  const legend = await P.evaluate(`(() => { const rows = [...document.querySelectorAll('.fb-row[data-k]')];
    return { title: document.querySelector('.fb-title span').textContent, note: document.querySelector('.fb-note').textContent, master: !!document.querySelector('.fb-all'),
      buttons: [...document.querySelectorAll('.fb-btns button')].map(b => b.innerText),
      rows: rows.map(r => ({ k: r.dataset.k, label: r.querySelector('.fb-lab').innerText, sw: getComputedStyle(r.querySelector('.fb-sw')).backgroundColor, h: r.querySelector('.fb-h').value,
        show: r.querySelector('.fb-show').checked, blk: r.querySelector('.fb-blk').checked, type: r.querySelector('.fb-h').type })) }; })()`);
  const hex = h => `rgb(${[1, 3, 5].map(i => parseInt(h.slice(i, i + 2), 16)).join(', ')})`;
  const legendBad = [];
  fx.furnitureKinds.forEach((k, i) => {
    const r = legend.rows[i];
    if (!r || r.k !== k.key || r.label !== `${k.label} (${k.count})` || r.sw !== hex(k.colour) || r.h !== String(k.height) || !r.show || r.blk !== k.blocks || r.type !== 'text') legendBad.push([k.key, r]);
  });
  check(`the legend: "Furniture boxes", its note, a master tick, one row per kind in table order (${fx.furnitureKinds.length}) with swatch colour, label (count), a height text box and the stops tick (curtain off), Reset heights and Save list (CSV)`,
    legend.title === 'Furniture boxes' && legend.note === 'Type a height in mm for each kind. Walk: boxes stop you; Ghost passes through.' && legend.master
    && legend.rows.length === fx.furnitureKinds.length && !legendBad.length && legend.buttons.join('|') === 'Reset heights|Save list (CSV)', legendBad.length ? legendBad : legend.rows.map(r => `${r.label} ${r.h}`));
  const kn = await kindsNow();
  check('kinds(): key, label, colour, height, defaultHeight, count (as in the model), shown and stopping',
    kn.length === fx.furnitureKinds.length && fx.furnitureKinds.every((k, i) => kn[i].key === k.key && kn[i].label === k.label && kn[i].colour === k.colour && kn[i].height === k.height
      && kn[i].defaultHeight === k.height && kn[i].count === k.count && kn[i].visible === true && kn[i].blocks === k.blocks), kn.map(k => `${k.key} ${k.count}`));
  // the doorways tick: one, ticked, between the note and the rows, named as the contract says
  const keepUi = await P.evaluate(`(() => { const b = document.querySelector('.fb-keep'), l = b && b.closest('label'), kids = [...document.querySelector('.fb-block').children];
    return { there: !!b, checked: b && b.checked, text: l && l.textContent.trim(), title: l ? l.title : '', n: document.querySelectorAll('.fb-keep').length,
      order: kids.indexOf(document.querySelector('.fb-note')) < kids.indexOf(l) && kids.indexOf(l) < kids.indexOf(document.querySelector('.fb-row.fb-head')) }; })()`);
  check(`the block has one tick "Keep doorways clear", ticked, between the note and the rows, whose tooltip says how many boxes it is about (${flagged.length})`,
    keepUi.there && keepUi.checked && keepUi.text === 'Keep doorways clear' && keepUi.n === 1 && keepUi.order && keepUi.title.startsWith(`${flagged.length} of the boxes`), keepUi);
  // pieces() carries approach (a copy) and blocking (what Walk does now); kinds() does not change with the tick
  const api = await P.evaluate(`(() => { const F = __host.furniture, out = {}, pc = () => F.pieces().map(p => [p.id, p.blocking, p.blocks, p.visible]);
    out.kinds0 = JSON.stringify(F.kinds()); out.keep0 = F.keepDoorways(); out.on = pc(); out.approach = F.pieces().filter(p => p.approach.length).map(p => [p.id, p.approach]);
    F.pieces().find(p => p.id === 'L1-seat-002').approach.push('L1-099'); out.copy = F.pieces().find(p => p.id === 'L1-seat-002').approach.join();
    out.set = [F.setKeepDoorways(false), F.keepDoorways()]; out.off = pc(); out.kindsOff = JSON.stringify(F.kinds());
    out.back = [F.setKeepDoorways(true), F.keepDoorways()]; out.kinds1 = JSON.stringify(F.kinds()); return out; })()`);
  const wantApi = keep => fx.furniture.map(p => { const blocks = fx.furnitureKinds.find(k => k.key === p.kind).blocks; return [p.id, blocks && !(keep && p.approach.length), blocks, true]; });
  check('pieces() lists each piece with its approach (a copy of the model\'s ids) and blocking, the box\'s effective state: on, the 2 pieces in an approach do not block; off, every box of a blocking kind does; setKeepDoorways / keepDoorways read and write the tick',
    api.keep0 === true && JSON.stringify(api.on) === JSON.stringify(wantApi(true)) && JSON.stringify(api.off) === JSON.stringify(wantApi(false))
    && JSON.stringify(api.approach) === JSON.stringify(flagged.map(p => [p.id, p.approach])) && api.copy === 'L1-001,L1-002' && api.set.join() === 'true,false' && api.back.join() === 'true,true',
    { keep: api.keep0, set: api.set, back: api.back, copy: api.copy });
  check('kinds() is the same with the tick on and off (a kind\'s stops tick is still the kind\'s default, whatever the doorways tick says)', api.kinds0 === api.kindsOff && api.kinds0 === api.kinds1);
  await P.shot(path.join(OUT, '01_orbit_both.png'));
  await P.clickEl('#floors [data-f=L1]'); await sleep(500);
  await P.shot(path.join(OUT, '02_orbit_L1.png'));
  await P.clickEl('#floors [data-f=both]'); await sleep(200);

  // ------------------------------------------------------------------ typing a height
  const n0 = await P.evaluate('__host.changes');
  await clickSel(rowSel('plant', 'h'));                                          // a real click in the middle of "600" ...
  await sleep(150);
  const sel = await P.evaluate('(() => { const e = document.activeElement; return { box: e.className, from: e.selectionStart, to: e.selectionEnd, len: e.value.length }; })()');
  await typeChars('480');                                                         // ... and typing replaces the number
  const afterClick = await boxText('plant');
  await blurBox();
  await F(`F.reset()`);
  check('clicking into a height box puts the keyboard there with the number selected: typing 480 over 600 gives 480 (not 600480 or 6480)',
    sel.box === 'fb-h' && sel.from === 0 && sel.to === sel.len && afterClick === '480', { sel, afterClick });
  await focusBox('table');
  check('the keyboard is in the box (the viewer ignores keys typed in it)', (await P.evaluate('document.activeElement.className')) === 'fb-h');
  await typeChars('6');
  let t6 = await F(`({ h: F.kinds().find(k => k.key === 'table').height, bad: document.querySelector(${JSON.stringify(rowSel('table', 'h'))}).classList.contains('fb-bad') })`);
  await typeChars('0');
  const t60 = (await F(`F.kinds().find(k => k.key === 'table').height`));
  await typeChars('0');
  const z600 = await F(`F.pieces().filter(p => p.kind === 'table' || p.kind === 'computer' || p.kind === 'printer').map(p => [p.id, p.z0, p.z1])`);
  const meshes600 = await P.evaluate(`(() => { const F = __host.furniture, g = id => F.meshOf(id), L2 = __host.FL.L2.level;
    return { tableScale: g('L1-table-001').scale.y, table2Scale: g('L2-table-001').scale.y, compY: g('L1-computer-001').position.y, comp2Y: g('L2-computer-001').position.y - L2, printY: g('L1-printer-001').position.y }; })()`);
  check('typing 6 (below 10 mm) changes nothing and marks the box; 60 applies as you type; 600 moves the computer and the printer to 0.60 and the table top to 0.60, on both levels',
    t6.h === 750 && t6.bad && t60 === 60 && z600.every(([id, z0, z1]) => id.includes('table') ? near(z0, 0) && near(z1, 0.6) : near(z0, 0.6))
    && near(meshes600.tableScale, 0.6) && near(meshes600.table2Scale, 0.6) && near(meshes600.compY, 0.6) && near(meshes600.comp2Y, 0.6) && near(meshes600.printY, 0.6),
    { after6: t6, after60: t60, meshes: meshes600 });
  check('the text box keeps what was typed, shows it as edited, and the change reached the host (onChange)',
    (await boxText('table')) === '600' && (await hasClass(rowSel('table', 'h'), 'fb-edited')) && !(await hasClass(rowSel('table', 'h'), 'fb-bad')) && (await P.evaluate('__host.changes')) > n0, { changes: (await P.evaluate('__host.changes')) - n0 });
  await P.shot(path.join(OUT, '03_table_600.png'));
  await focusBox('table'); await typeChars('700'); await pressKey('Enter', 'Enter', 13);
  check('Enter applies the number and gives the keyboard back to the viewer (700 mm, box no longer focused)',
    (await F(`F.kinds().find(k => k.key === 'table').height`)) === 700 && (await P.evaluate('document.activeElement === document.body || !document.activeElement.classList.contains("fb-h")')), await boxText('table'));
  const junk = [], tableH = () => F(`F.kinds().find(k => k.key === 'table').height`);
  for (const text of ['9999', 'abc', '4,5', '']) {
    await focusBox('table');
    if (text) await typeChars(text); else await pressKey('Backspace', 'Backspace', 8);
    const bad = await hasClass(rowSel('table', 'h'), 'fb-bad'), during = await tableH();
    await blurBox(); await sleep(60);
    junk.push({ text, marked: bad, during, after: await boxText('table'), height: await tableH(), edited: await hasClass(rowSel('table', 'h'), 'fb-edited') });
  }
  check('junk (9999, abc, 4,5, nothing) is marked while typed and never kept: leaving the box puts back the height from before you typed (700)',
    junk.every(j => j.after === '700' && j.height === 700) && junk.slice(0, 3).every(j => j.marked) && !junk[3].marked, junk);
  check('what is applied on the way is undone: typing 9999 passes through 999 (a valid number, applied as you type), leaving the box brings back 700',
    junk[0].during === 999 && junk[0].height === 700 && junk[1].during === 700 && junk[2].during === 700 && junk[3].during === 700, junk.map(j => [j.text, j.during]));
  await focusBox('plant'); await typeChars('123');
  check('digits typed in a height box do not switch the viewer mode (1 / 2 / 3 are mode keys)', (await modeNow()) === 'orbit' && (await F(`F.kinds().find(k => k.key === 'plant').height`)) === 123, await modeNow());
  await pressKey('Escape', 'Escape', 27);
  check('Escape cancels the edit (the plant is back to 600), leaves the box and does not change the viewer mode',
    (await modeNow()) === 'orbit' && (await P.evaluate('document.activeElement.className !== "fb-h"')) && (await boxText('plant')) === '600' && (await F(`F.kinds().find(k => k.key === 'plant').height`)) === 600);
  await focusBox('plant'); await typeChars('600'); await blurBox();
  await focusBox('plant'); await typeChars('5000'); await blurBox();
  const edge = await F(`F.kinds().find(k => k.key === 'plant').height`);
  await focusBox('plant'); await typeChars('5001'); await blurBox();
  const over = await F(`F.kinds().find(k => k.key === 'plant').height`);
  await focusBox('plant'); await typeChars('10'); await blurBox();
  const low = await F(`F.kinds().find(k => k.key === 'plant').height`);
  check('the range is 10 - 5000 mm (5000 and 10 are taken, 5001 is not)', edge === 5000 && over === 5000 && low === 10, { five000: edge, five001: over, ten: low });
  check('the API refuses what the box refuses: setHeight(x, 9) and unknown kinds return false, a good one true',
    (await F(`[F.setHeight('plant', 9), F.setHeight('nothing', 500), F.setHeight('plant', 'abc'), F.setHeight('plant', 600)]`)).join() === 'false,false,false,true');

  // The first key typed right after the click must not be lost: the module selects the number a moment after the focus (so that
  // typing replaces it), and that timer used to select the first digit just typed, so that the next one replaced it (640 -> 40).
  // The keys come at once after the focus (no gap), or while the page is busy for 400 ms right after the focus (a slow frame).
  async function raceTry(busyMs, gapMs) {
    await F(`F.reset()`);
    await P.evaluate(`(() => { const e = document.querySelector(${JSON.stringify(rowSel('table', 'h'))}); e.scrollIntoView({ block: 'center' });
      if (${busyMs}) setTimeout(() => { const t = Date.now(); while (Date.now() - t < ${busyMs}); }, 0);       // a long task queued ahead of the module's timer
      e.focus(); e.select(); })()`);
    if (gapMs) await sleep(gapMs);
    await typeChars('640'); await pressKey('Enter', 'Enter', 13); await sleep(200);
    return { height: await F(`F.kinds().find(k => k.key === 'table').height`), text: await boxText('table') };
  }
  const race = { gap0: await raceTry(0, 0), gap0b: await raceTry(0, 0), busy: await raceTry(400, 0), busyWait: await raceTry(400, 600), gap100: await raceTry(0, 100) };
  await F(`F.reset()`);
  check('typing 640 into a height box right after the focus gives 640, not 40: keys with no gap (twice), keys while the page is busy for 400 ms, keys after the busy spell, keys 100 ms later',
    Object.values(race).every(r => r.height === 640 && r.text === '640'), race);

  // ------------------------------------------------------------------ Reset heights
  await F(`F.setHeight('seat', 500)`);
  await clickSel('.fb-reset');
  const afterReset = await P.evaluate(`(() => { const F = __host.furniture; return { kinds: F.kinds().map(k => [k.key, k.height, k.defaultHeight]), boxes: [...document.querySelectorAll('.fb-row[data-k] .fb-h')].map(e => e.value),
    edited: document.querySelectorAll('.fb-h.fb-edited').length, stored: (() => { try { return Object.keys(localStorage).filter(k => k.startsWith('walkthrough-furniture')).map(k => [k, localStorage.getItem(k)]); } catch (e) { return 'blocked'; } })() }; })()`);
  check('Reset heights brings every kind, text box and box back to the model heights, clears the edited marks and the stored heights',
    afterReset.kinds.every(([, h, d]) => h === d) && afterReset.boxes.join() === fx.furnitureKinds.map(k => k.height).join() && afterReset.edited === 0 && Array.isArray(afterReset.stored) && afterReset.stored.length === 0
    && near((await F(`F.pieces().find(p => p.id === 'L1-computer-001').z0`)), 0.75), afterReset.stored);

  // ------------------------------------------------------------------ remembered across a reload
  await typeInto('table', '600'); await typeInto('coffee-table', '420'); await blurBox();
  const key = await P.evaluate(`Object.keys(localStorage).find(k => k.startsWith('walkthrough-furniture'))`);
  const saved = await P.evaluate(`localStorage.getItem(${JSON.stringify(key || 'nothing stored')})`);
  const savedJson = (() => { try { return JSON.parse(saved) || {}; } catch { return {}; } })();
  check(`typed heights are stored under a key with the project name ("${key}"), only the changed ones`, !!key && key.includes('Fixture') && savedJson.table === 600 && savedJson['coffee-table'] === 420 && Object.keys(savedJson).length === 2, saved);
  await open();
  const reloaded = await P.evaluate(`(() => { const F = __host.furniture; return { box: document.querySelector(${JSON.stringify(rowSel('table', 'h'))}).value, coffee: document.querySelector(${JSON.stringify(rowSel('coffee-table', 'h'))}).value,
    k: F.kinds().filter(k => k.height !== k.defaultHeight).map(k => [k.key, k.height]), z: F.pieces().find(p => p.id === 'L1-computer-001').z0, y: F.meshOf('L1-computer-001').position.y }; })()`);
  check('after a reload the typed heights are back: the boxes show them, the table and everything on it follow', reloaded.box === '600' && reloaded.coffee === '420' && near(reloaded.z, 0.6) && near(reloaded.y, 0.6)
    && JSON.stringify(reloaded.k) === JSON.stringify([['table', 600], ['coffee-table', 420]]), reloaded);
  await clickSel('.fb-reset');
  await open();
  check('Reset heights before a reload: the page comes back with the model heights', (await boxText('table')) === '750' && (await P.evaluate(`Object.keys(localStorage).filter(k => k.startsWith('walkthrough-furniture')).length`)) === 0);
  // garbage in storage is ignored (a value out of range, a wrong type), good ones around it are kept
  await P.evaluate(`localStorage.setItem(${JSON.stringify(key)}, JSON.stringify({ table: 'tall', seat: 12, plant: 99999, sofa: 800, 'tall-cabinet': 1900 }))`);
  await open();
  const garbage = await kindsNow();
  check('stored values that are not numbers in range (or kinds this model does not have) are ignored; the rest is applied',
    garbage.find(k => k.key === 'table').height === 750 && garbage.find(k => k.key === 'seat').height === 12 && garbage.find(k => k.key === 'plant').height === 600 && garbage.find(k => k['key'] === 'tall-cabinet').height === 1900,
    garbage.filter(k => k.height !== k.defaultHeight).map(k => [k.key, k.height]));
  await P.evaluate(`localStorage.setItem(${JSON.stringify(key)}, 'not json {')`);
  await open();
  check('stored text that is not JSON is ignored too (the page opens with the model heights)', (await boxText('table')) === '750');
  await P.evaluate(`localStorage.clear()`);
  // storage blocked (a private window, site data off): the page still works and the heights last for the visit
  const blocked = await tab.send('Page.addScriptToEvaluateOnNewDocument', { source: `Object.defineProperty(window, 'localStorage', { configurable: true, get() { throw new DOMException('blocked for the test', 'SecurityError'); } });` });
  await open();
  await typeInto('table', '640'); await pressKey('Enter', 'Enter', 13);
  const noStore = await F(`({ h: F.kinds().find(k => k.key === 'table').height, z: F.pieces().find(p => p.id === 'L1-computer-001').z0, n: F.pieces().length })`);
  await clickSel('.fb-reset');
  check('with storage blocked the boxes, the typing and Reset heights all still work', noStore.n === nPieces && noStore.h === 640 && near(noStore.z, 0.64) && (await boxText('table')) === '750', noStore);
  await clickSel('.fb-keep');
  const noStore2 = await F(`({ keep: F.keepDoorways(), ticked: document.querySelector('.fb-keep').checked, col: ['L1-seat-002', 'L2-seat-001'].map(id => __host.FL[F.pieces().find(p => p.id === id).floor].colliders.includes(F.meshOf(id))) })`);
  check('... and so does the doorways tick (off: the 2 boxes are colliders; nothing is stored, nothing throws)', noStore2.keep === false && !noStore2.ticked && noStore2.col.every(Boolean), noStore2);
  await tab.send('Page.removeScriptToEvaluateOnNewDocument', { identifier: blocked.identifier });
  await open();

  // the doorways tick is kept with the typed heights: the same key, only when it is off, and read back with the same care
  const keepKey = await P.evaluate(`'walkthrough-furniture-heights:' + __host.model.shortName`);
  const stored = () => P.evaluate(`localStorage.getItem(${JSON.stringify(keepKey)})`);
  check('the doorways tick on (the default) stores nothing', (await stored()) === null);
  await clickSel('.fb-keep');
  const s1 = await stored();
  await typeInto('table', '600'); await blurBox();
  const s2 = await stored();
  check('unticking "Keep doorways clear" stores {"keepDoorways":false} under the heights key; with a typed table height the key holds both', s1 === '{"keepDoorways":false}' && s2 === '{"table":600,"keepDoorways":false}', { s1, s2 });
  await open();
  const back = await F(`({ keep: F.keepDoorways(), ticked: document.querySelector('.fb-keep').checked, table: F.kinds().find(k => k.key === 'table').height,
    col: ['L1-seat-002', 'L2-seat-001', 'L1-seat-001'].map(id => __host.FL[F.pieces().find(p => p.id === id).floor].colliders.includes(F.meshOf(id))) })`);
  check('after a reload the tick is off again (the page shows it, the 2 boxes are colliders) and the table height is back too', back.keep === false && !back.ticked && back.col.every(Boolean) && back.table === 600, back);
  await clickSel('.fb-reset');
  const s3 = await stored(), tickAfterReset = await F(`F.keepDoorways()`);
  check('Reset heights clears the typed heights and leaves the doorways tick as it is (off)', s3 === '{"keepDoorways":false}' && tickAfterReset === false, { s3 });
  await clickSel('.fb-keep');
  check('ticking it on again removes the stored key altogether (no typed heights, nothing but the defaults)', (await stored()) === null && (await F(`F.keepDoorways()`)) === true);
  let keepRead = true;
  for (const bad of ['{"keepDoorways":"no","table":800}', '{"keepDoorways":0}', '{"keepDoorways":null}', '{"keepDoorways":true}']) {          // only a stored false switches it off
    await P.evaluate(`localStorage.setItem(${JSON.stringify(keepKey)}, ${JSON.stringify(bad)})`);
    await open();
    const g = await F(`({ keep: F.keepDoorways(), table: F.kinds().find(k => k.key === 'table').height })`);
    if (g.keep !== true || g.table !== (bad.includes('"table"') ? 800 : 750)) { note('stored text read wrongly', { bad, g }); keepRead = false; }
  }
  check('anything but a stored false leaves the tick on ("no", 0, null, true), and the heights next to it are still read', keepRead);
  await P.evaluate(`localStorage.clear()`);
  await open();

  // ------------------------------------------------------------------ Walk: shown boxes that stop you
  await P.evaluate(`__viewer.setMode('walk')`);
  await P.evaluate(`(${pageHelpers.toString()})()`);
  const ids = Object.keys(SIDES);
  const col0 = await collidersOf();
  // the boxes of the kinds that stop you; with the doorways tick on (the default) not those in the approach of a door or a passage
  const expectedCol = (fl, keep = true) => fx.furniture.filter(p => p.floor === fl && fx.furnitureKinds.find(k => k.key === p.kind).blocks && !(keep && p.approach.length)).map(p => p.id).sort();
  check('the level colliders hold the boxes of kinds that stop you (all but the curtain and the 2 boxes in a doorway\'s approach), on their own level only',
    floors.every(fl => JSON.stringify(col0[fl]) === JSON.stringify(expectedCol(fl))) && !col0.L1.includes('L1-curtain-001') && !col0.L1.includes('L1-seat-002') && !col0.L2.includes('L2-seat-001')
    && col0.L1.includes('L1-seat-001'), { L1: col0.L1.length, L2: col0.L2.length });
  const w0 = await walks(ids, false);
  const w0ok = w0.filter(stopped);
  check(`Walk from 1 m, straight at ${w0.filter(w => w.start).length} faces of ${ids.length} boxes: it stops short of each face (gap 0.25 - 0.42 m), never inside, never through`,
    w0.filter(w => w.start).length >= 20 && w0ok.length === w0.filter(w => w.start).length && ids.every(id => w0.filter(w => w.id === id && w.start).length >= 2), w0ok.length === w0.filter(w => w.start).length ? brief(w0).slice(0, 8) : w0.filter(w => w.start && !stopped(w)));
  const startable = Object.fromEntries(ids.map(id => [id, w0.filter(w => w.id === id && w.start).map(w => w.side)]));
  const through0 = await walks(ids, true, startable);
  const wl = await P.evaluate(`(() => { const L = __host.FL.L1.colliders.find(m => m.name === 'L1 wall'), b = new THREE.Box3().setFromObject(L), out = [];
    for (const back of [1.0, 0.8]) { __viewer.goToFloor('L1'); const s = __viewer.state; s.pos.x = b.min.x - back; s.pos.z = 0; const m = __viewer.probe.walk(-90, 3); out.push({ back, gap: b.min.x - s.pos.x, moved: m }); }
    return out; })()`);
  check('the wall of the scene still stops you (boxes did not disturb the other colliders)', wl.every(w => w.gap >= 0.25 && w.gap <= 0.42), wl);
  await P.shot(path.join(OUT, '04_walk.png'));

  // each kind in turn: untick show (a real click) -> the same walks go right through; tick it again -> they stop you again
  const showLog = [];
  for (const k of [...new Set(ids.map(kindOfId))]) {
    const mine = ids.filter(id => kindOfId(id) === k);
    await clickSel(rowSel(k, 'show'));
    const inCol = await collidersOf(), shown = await F(`F.meshOf(${JSON.stringify(mine[0])}).visible`);
    const t = await walks(mine, true, startable);
    await clickSel(rowSel(k, 'show'));
    const back = await walks(mine, false, startable);
    const ok = t.length > 0 && t.every(passed) && back.every(stopped) && !shown && mine.every(id => !inCol.L1.includes(id));
    showLog.push([k, ok]);
    if (!ok) note(`show tick, ${k}`, { hidden: shown, through: t.filter(w => !passed(w)), again: back.filter(w => !stopped(w)), colliders: inCol.L1.filter(i => mine.includes(i)) });
  }
  check(`unticking show: the same walks pass right through the boxes of that kind, they leave the colliders, and ticking it again makes them stop you again (${showLog.length} kinds)`, showLog.every(([, ok]) => ok), showLog);
  const blkLog = [];
  for (const k of [...new Set(ids.map(kindOfId))]) {
    const mine = ids.filter(id => kindOfId(id) === k);
    await clickSel(rowSel(k, 'blk'));
    const inCol = await collidersOf(), shown = await F(`F.meshOf(${JSON.stringify(mine[0])}).visible`);
    const t = await walks(mine, true, startable);
    await clickSel(rowSel(k, 'blk'));
    const back = await walks(mine, false, startable);
    const ok = t.length > 0 && t.every(passed) && back.every(stopped) && shown && mine.every(id => !inCol.L1.includes(id));
    blkLog.push([k, ok]);
    if (!ok) note(`stops tick, ${k}`, { shown, through: t.filter(w => !passed(w)), again: back.filter(w => !stopped(w)) });
  }
  check(`unticking "stops": the boxes stay on screen but you walk right through them (and out of the colliders); ticking it again stops you again (${blkLog.length} kinds)`, blkLog.every(([, ok]) => ok), blkLog);
  const tickState = await P.evaluate(`(() => { const F = __host.furniture; return F.kinds().every(k => k.visible) && F.kinds().filter(k => k.blocks).length === ${fx.furnitureKinds.filter(k => k.blocks).length}; })()`);
  check('after those clicks every kind is shown again and the stops ticks are as the model has them', tickState);

  // the curtain: blocks false in the model, so it does not stop you while shown; its stops tick makes it
  const cSides = { 'L1-curtain-001': [2, 3] };
  const cur0 = await walks(['L1-curtain-001'], true, cSides);
  const curShown = await F(`F.meshOf('L1-curtain-001').visible`);
  await clickSel(rowSel('curtain', 'blk'));
  const cur1 = await walks(['L1-curtain-001'], false, cSides);
  await clickSel(rowSel('curtain', 'blk'));
  const cur2 = await walks(['L1-curtain-001'], true, cSides);
  check('the curtain (blocks: false in the model) is shown and does not stop you; ticking stops makes it a wall, unticking lets you through again',
    curShown && cur0.length === 2 && cur0.every(passed) && cur1.every(stopped) && cur2.every(passed), { before: brief(cur0), ticked: brief(cur1), after: brief(cur2) });

  // a box lower than Walk's knee ray (0.35 m) is stepped over
  const cs = { 'L1-coffee-table-001': [0, 1, 2, 3] };
  const low300 = [];
  for (const mm of [300, 340, 360, 450]) {
    await typeInto('coffee-table', String(mm)); await pressKey('Enter', 'Enter', 13);
    low300.push([mm, await walks(['L1-coffee-table-001'], mm < 350, cs)]);
  }
  check('a coffee table typed as 300 mm does not stop you (the knee ray at 0.35 m passes over it), 340 neither; at 360 and at its own 450 it does',
    low300[0][1].every(passed) && low300[1][1].every(passed) && low300[2][1].every(stopped) && low300[3][1].every(stopped), low300.map(([mm, w]) => [mm, brief(w)]));
  // no frame in between: the box a height was just set on must already be where Walk's rays look (matrices are updated at once)
  const sameTick = await P.evaluate(`(() => { const F = __host.furniture, out = [];
    for (const mm of [300, 450, 300, 450]) { F.setHeight('coffee-table', mm); out.push([mm, __t.walkAt('L1-coffee-table-001', 2, 1.0, mm < 350)]); }
    F.reset(); return out; })()`);
  check('a height set a moment ago is seen by Walk in the same tick, before any frame is drawn (300 passes, 450 stops, 300, 450: the matrices are updated at once)',
    passed(sameTick[0][1]) && stopped(sameTick[1][1]) && passed(sameTick[2][1]) && stopped(sameTick[3][1]), sameTick.map(([mm, w]) => [mm, brief([w])[0]]));
  await clickSel('.fb-reset');

  // the other level: boxes only stop you on their own level
  const l2 = await P.evaluate(`(() => { const out = {};
    out.table = __t.walkAt('L2-table-001', 2, 1.0, false); out.cabinet = __t.walkAt('L2-cabinet-001', 3, 1.0, false); out.chair = __t.walkAt('L2-seat-001', 1, 1.0, false);
    // the same walk as at the level-2 cabinet (from plan (-2, -0.4) towards -y), on level 1, where its box does not exist
    __viewer.goToFloor('L1'); const s = __viewer.state; s.pos.x = -2.0; s.pos.z = 0.4; out.l1 = __viewer.probe.walk(180, 2.2);
    return out; })()`);
  check('on level 2 the level-2 boxes stop you (table, cabinet), the chair in a doorway\'s approach does not (the tick is on); the same walk at the cabinet\'s place on level 1 goes straight on',
    stopped(l2.table) && stopped(l2.cabinet) && walkedIn(l2.chair) && l2.l1 >= 2.1, { table: brief([l2.table]), cabinet: brief([l2.cabinet]), chair: brief([l2.chair]), onLevel1: r2(l2.l1) });

  // the master tick and the colliders
  await clickSel('.fb-all');
  const masterOff = await P.evaluate(`(() => ({ vis: __host.furniture.kinds().every(k => !k.visible), meshes: __host.furniture.pieces().every(p => !__host.furniture.meshOf(p.id).visible), ticks: [...document.querySelectorAll('.fb-show')].every(c => !c.checked),
    col: Object.values(__host.FL).every(f => f.colliders.every(m => !m.name.startsWith('furn:'))) }))()`);
  await clickSel(rowSel('seat', 'show'));
  const mixed = await P.evaluate(`(() => { const m = document.querySelector('.fb-all'); return { checked: m.checked, indeterminate: m.indeterminate }; })()`);
  await clickSel('.fb-all');
  const masterOn = await P.evaluate(`(() => ({ vis: __host.furniture.kinds().every(k => k.visible), ticks: [...document.querySelectorAll('.fb-show')].every(c => c.checked), master: document.querySelector('.fb-all').checked,
    n: Object.values(__host.FL).reduce((n, f) => n + f.colliders.filter(m => m.name.startsWith('furn:')).length, 0) }))()`);
  check('the master tick hides / shows every kind at once (hidden boxes leave the colliders) and shows a mixed state when only some are on',
    masterOff.vis && masterOff.meshes && masterOff.ticks && masterOff.col && mixed.indeterminate && !mixed.checked && masterOn.vis && masterOn.ticks && masterOn.master && masterOn.n === floors.reduce((n, fl) => n + expectedCol(fl).length, 0), { masterOff, mixed, masterOn });

  // ------------------------------------------------------------------ doorways: the boxes in the approach of a door or a passage
  // Keep doorways clear on (the default): the two flagged pieces are drawn but are no colliders, the seat beside one of them still is.
  const SEAT2 = { 'L1-seat-002': [2, 3] }, SEAT1 = { 'L1-seat-001': [0] };
  const doorState = async () => ({
    col: await collidersOf(), drawn: await F(`['L1-seat-002', 'L2-seat-001'].every(id => F.meshOf(id).visible)`),
    across: await walks(['L1-seat-002'], true, SEAT2), at: await walks(['L1-seat-002'], false, SEAT2), seat1: await walks(['L1-seat-001'], false, SEAT1),
    chair: await P.evaluate(`__t.walkAt('L2-seat-001', 1, 1.0, false)`) });
  const colsAre = (st, keep) => floors.every(fl => JSON.stringify(st.col[fl]) === JSON.stringify(expectedCol(fl, keep)));
  const dOn = await doorState();
  check('Keep doorways clear is on: the 2 boxes in an approach are drawn but no colliders - Walk goes right across the seat on level 1 and into the chair on level 2 - while the seat beside it still stops you',
    dOn.drawn && colsAre(dOn, true) && dOn.across.length === 2 && dOn.across.every(passed) && dOn.at.length === 2 && dOn.at.every(walkedIn) && dOn.seat1.length === 1 && dOn.seat1.every(stopped) && walkedIn(dOn.chair),
    { across: brief(dOn.across), at: brief(dOn.at), seat1: brief(dOn.seat1), chair: brief([dOn.chair]) });
  await clickSel('.fb-keep');                                                  // a real click: the doorways are no longer kept clear
  const dOff = await doorState(), tickOff = await P.evaluate(`({ checked: document.querySelector('.fb-keep').checked, keep: __host.furniture.keepDoorways() })`);
  check('a real click on the tick (off): the 2 boxes are colliders again and stop you like any other (short of the face, gap 0.25 - 0.42 m, never across), and are still drawn',
    !tickOff.checked && tickOff.keep === false && dOff.drawn && colsAre(dOff, false) && dOff.at.length === 2 && dOff.at.every(stopped) && !dOff.across.some(passed) && dOff.seat1.every(stopped) && stopped(dOff.chair),
    { at: brief(dOff.at), across: brief(dOff.across), chair: brief([dOff.chair]) });
  await clickSel('.fb-keep');
  const dBack = await doorState(), tickBack = await P.evaluate(`({ checked: document.querySelector('.fb-keep').checked, keep: __host.furniture.keepDoorways() })`);
  check('ticking it again: you walk through them again and the colliders are as they were', tickBack.checked && tickBack.keep && colsAre(dBack, true) && dBack.across.every(passed) && dBack.at.every(walkedIn) && walkedIn(dBack.chair)
    && JSON.stringify(dBack.col) === JSON.stringify(dOn.col));
  // the show and stops ticks keep their meaning for such a piece: with the doorways tick on it is never a collider (drawn or not), with it off it is one while its kind is shown and stops you
  const snapOf = () => P.evaluate(`(() => { const F = __host.furniture; return ['L1-seat-002', 'L2-seat-001', 'L1-seat-001'].map(id => { const m = F.meshOf(id), p = F.pieces().find(q => q.id === id);
    return [m.visible, __host.FL[p.floor].colliders.includes(m), p.blocking]; }); })()`);
  const ticks = {};
  for (const keep of [true, false]) {
    await F(`F.setKeepDoorways(${keep})`);
    ticks[keep] = { plain: await snapOf() };
    await F(`F.setVisible('seat', false)`); ticks[keep].hidden = await snapOf(); await F(`F.setVisible('seat', true)`);
    await F(`F.setBlocks('seat', false)`); ticks[keep].nostop = await snapOf(); await F(`F.setBlocks('seat', true)`);
  }
  await F(`F.setKeepDoorways(true)`);
  const trio = (...a) => JSON.stringify(a), same3 = (v, c, b) => trio([v, c, b], [v, c, b], [v, c, b]);
  check('the kind\'s ticks mean the same for such a piece: show off hides it and takes it out of the colliders, stops off leaves it drawn and out of them; with the doorways tick on it is out of them anyway (the plain seat beside it is in)',
    JSON.stringify(ticks.true.plain) === trio([true, false, false], [true, false, false], [true, true, true]) && JSON.stringify(ticks.true.hidden) === same3(false, false, false)
    && JSON.stringify(ticks.true.nostop) === same3(true, false, false) && JSON.stringify(ticks.false.plain) === same3(true, true, true)
    && JSON.stringify(ticks.false.hidden) === same3(false, false, false) && JSON.stringify(ticks.false.nostop) === same3(true, false, false), ticks);

  // ------------------------------------------------------------------ the boxes are single-sided: a player inside one can walk out
  // From the middle of every box that stops you (the double-click path: Orbit, then Walk at the box), and from a spot where a box is
  // switched on under the player. Double-sided faces trapped the player in the big boxes (every ray from inside met the inner faces).
  await F(`F.setKeepDoorways(false)`);                                              // every box of a blocking kind is a collider now
  const mids = await F(`F.pieces().filter(p => p.blocking).map(p => p.id)`);
  const into = await P.evaluate(`(() => { const out = [];
    for (const id of ${JSON.stringify(mids)}) { __t.spawn(id); out.push({ id, ...__t.verdict() }); }
    __viewer.setMode('orbit'); __viewer.setMode('walk'); return out; })()`);
  await F(`F.setKeepDoorways(true)`);
  const heldBy = into.filter(r => r.class === 'C'), inBox = into.filter(r => r.inside.length);
  check(`Walk entered at the middle of each of the ${mids.length} boxes that stop you: ${inBox.length} land the player inside a box, and every one of them can walk out (none is held by a box itself)`,
    mids.length >= 14 && inBox.length >= 3 && heldBy.length === 0, heldBy.length ? heldBy : { inside: inBox.map(r => `${r.id} in ${r.inside.join('+')} (${r2(r.best)} m)`) });
  const sc = await P.evaluate(`(${pageScenarios.toString()})('L1-seat-001', 'L1-seat-002', 'seat')`);
  check('a box switched on under the player (the show tick, the stops tick, typed taller: 100 -> 450 mm, the doorways tick) does not hold the player: the box is around him, and he walks out',
    Object.values(sc).every(r => r.before === 0 && r.inside.length >= 1 && r.class !== 'C' && r.best >= 1.0), sc);
  await P.evaluate(`__viewer.setMode('walk')`);

  // ------------------------------------------------------------------ Ghost passes through
  await P.evaluate(`__viewer.setMode('ghost')`);
  await P.evaluate(`(() => { const s = __viewer.state; s.pos.set(3.0, 1.0, 3.0); s.yaw = -Math.PI / 2; s.pitch = 0; })()`);
  const cabinet = await P.evaluate(`__t.frame('L1-tall-cabinet-001').c.toArray()`);
  const stillBlocking = await F(`F.kinds().find(k => k.key === 'tall-cabinet').blocks && __host.FL.L1.colliders.includes(F.meshOf('L1-tall-cabinet-001'))`);
  await P.keyDown('KeyW');
  let gx = 0;
  for (let i = 0; i < 120 && gx < 6.4; i++) { await sleep(100); gx = await P.evaluate('__viewer.state.pos.x'); }
  await P.keyUp('KeyW');
  const gs = await P.evaluate(`({ x: __viewer.state.pos.x, y: __viewer.state.pos.y, z: __viewer.state.pos.z })`);
  check('Ghost flies straight through a tall cabinet that does stop you in Walk (it is a collider, and you come out the other side)',
    stillBlocking && cabinet[0] === 5 && gs.x > 5.6 && near(gs.z, 3.0, 0.05) && near(gs.y, 1.0, 0.05), { from: 3.0, to: r2(gs.x), cabinetAt: cabinet[0], y: r2(gs.y) });
  await P.evaluate(`__viewer.setMode('orbit')`);

  // ------------------------------------------------------------------ the family list (CSV)
  await open();
  const text = await F('F.csv()');
  const lines = text.split('\r\n');
  const header = 'id,level,kind,kind_label,family,block,layer,dxf_handle,x_m,y_m,width_mm,depth_mm,height_mm,base_mm,rotation_deg,on_top_of,merged,note';
  const wantIds = ['L1-computer-001', 'L1-printer-001', 'L1-tv-001', 'L1-curtain-001', 'L1-plant-001', 'L1-seat-001', 'L1-seat-002', 'L1-seat-003', 'L1-table-001', 'L1-table-002', 'L1-coffee-table-001',
    'L1-cabinet-001', 'L1-tall-cabinet-001', 'L2-computer-001', 'L2-seat-001', 'L2-table-001', 'L2-cabinet-001'];
  check(`csv(): the header, ${nPieces} rows sorted by level, kind (table order) and id, CRLF line ends with one after the last row, no byte-order mark`,
    lines[0] === header && lines.length === nPieces + 2 && lines[lines.length - 1] === '' && lines.slice(1, -1).map(l => l.split(',')[0]).join() === wantIds.join()
    && !/(^|[^\r])\n/.test(text) && text.charCodeAt(0) !== 0xFEFF, { rows: lines.length - 2, first: lines[0].slice(0, 30), firstIds: lines.slice(1, 4).map(l => l.split(',')[0]) });
  const byId = Object.fromEntries(lines.slice(1, -1).map(l => [l.split(',')[0], l]));
  check('csv(): rows byte for byte as the contract says (drawing coordinates = model + offset, whole mm, base_mm of a computer on a 750 table = 750, one decimal for the rotation, empty cells)',
    byId['L1-computer-001'] === 'L1-computer-001,L1,computer,Computer / monitor,Enscape AssetDefinition - Computer 003,Enscape AssetDefinition - Computer 003 - Enscape AssetDefinition - Computer 003,I-FURN,A1,1.300,2.100,740,430,450,750,0.0,L1-table-001,1,'
    && byId['L1-tv-001'] === 'L1-tv-001,L1,tv,TV / wall screen,APPLIANCE_TV_WALL MOUNT WITH BRACKET - 75_,APPLIANCE_TV_WALL MOUNT WITH BRACKET - 75_,Q-SPCQ,A3,8.000,5.000,1680,50,600,900,90.0,,1,'
    && byId['L2-cabinet-001'] === 'L2-cabinet-001,L2,cabinet,Cabinet / casework,PANEL_ADJ_GEN - ADJUSTABLE CUPBOARD DOOR,PANEL_ADJ_GEN - ADJUSTABLE CUPBOARD DOOR,Q-CASE,,-1.000,0.000,3600,1200,900,0,0.0,,4,merged 4 cupboard-door fronts'
    && byId['L1-table-002'].endsWith(',AA,5.000,4.000,1400,1000,750,0,150.0,,1,'), [byId['L1-computer-001'], byId['L1-tv-001'].slice(-40), byId['L2-cabinet-001'].slice(-50)]);
  check('csv() equals the contract as Python writes it (expected_csv.py: its own f-string formatting and csv writer) for the model heights', text === python(FIXTURE), text === python(FIXTURE) ? 'identical' : { js: text.slice(0, 200), py: python(FIXTURE).slice(0, 200) });
  if (KIT) check('csv() equals furniture_kit.csv_text, the builders\' writer, for the model heights', text === python(FIXTURE, null, true), text === python(FIXTURE, null, true) ? 'identical' : { js: text.slice(0, 200), kit: python(FIXTURE, null, true).slice(0, 200) });
  else note('furniture/furniture_kit.py not found: the list was not compared with the builders\' writer');
  const typedH = { table: 600, 'coffee-table': 300, seat: 480, tv: 650 };
  for (const [k, mm] of Object.entries(typedH)) await typeInto(k, String(mm));
  await blurBox();
  const text2 = await F('F.csv()');
  const r2l = Object.fromEntries(text2.split('\r\n').slice(1, -1).map(l => [l.split(',')[0], l.split(',')]));
  check('csv() carries the typed heights (height_mm), and the pieces standing on a table take the new underside (base_mm 600); it equals Python for these heights',
    text2 === python(FIXTURE, typedH) && r2l['L1-table-001'][12] === '600' && r2l['L1-computer-001'][13] === '600' && r2l['L1-seat-001'][12] === '480' && r2l['L1-tv-001'][12] === '650' && r2l['L2-computer-001'][13] === '600',
    { computerBase: r2l['L1-computer-001'][13], table: r2l['L1-table-001'][12] });
  if (KIT) check('... and equals furniture_kit.csv_text for those heights (what the viewer types in, the builders\' writer accepts as {kind: mm})', text2 === python(FIXTURE, typedH, true));
  await clickSel('.fb-reset');

  // ------------------------------------------------------------------ the download
  await P.evaluate(`window.__dl = []; const mk = URL.createObjectURL; URL.createObjectURL = b => { window.__dl.push({ blob: b, name: null }); return mk.call(URL, b); };
    HTMLAnchorElement.prototype.click = function () { if (this.download) window.__dl[window.__dl.length - 1].name = this.download; };`);
  await clickSel('.fb-save'); await sleep(200);
  const quiet = await P.evaluate('window.__dl.length');
  check('with nodownload=1 "Save list (CSV)" downloads nothing (csv() still works)', quiet === 0 && (await F('F.csv().length')) > 1000, quiet);
  await flush();
  await P.goto(`${PAGE}?build=0`);                                              // downloads allowed
  await P.evaluate(`window.__dl = []; const mk = URL.createObjectURL; URL.createObjectURL = b => { window.__dl.push({ blob: b, name: null }); return mk.call(URL, b); };
    HTMLAnchorElement.prototype.click = function () { if (this.download) window.__dl[window.__dl.length - 1].name = this.download; };`);
  await typeInto('table', '640'); await blurBox();
  await clickSel('.fb-save'); await sleep(300);
  const dl = await P.evaluate(`(async () => { const d = window.__dl[0]; if (!d) return null; const bytes = new Uint8Array(await d.blob.arrayBuffer());
    return { name: d.name, type: d.blob.type, head: [...bytes.slice(0, 4)], text: new TextDecoder('utf-8', { ignoreBOM: true }).decode(bytes), csv: __host.furniture.csv(), n: window.__dl.length }; })()`);
  check('"Save list (CSV)" downloads Fixture_furniture_list.csv, UTF-8 with the EF BB BF mark in front of exactly csv() (typed heights included)',
    dl && dl.name === 'Fixture_furniture_list.csv' && dl.head.slice(0, 3).join() === '239,187,191' && dl.text === String.fromCharCode(0xFEFF) + dl.csv && dl.csv.includes(',640,') && dl.n === 1 && /utf-8/i.test(dl.type), dl && { name: dl.name, type: dl.type, head: dl.head, n: dl.n });
  await clickSel('.fb-reset');

  // ------------------------------------------------------------------ the awkward model: quoting, ties, -0.000, a kind nobody uses, unsorted input
  flush(); await P.goto(`${PAGE}?build=0&nodownload=1${modelUrl(awkward)}`);
  const aw = await P.evaluate(`(() => ({ csv: __host.furniture.csv(), rows: [...document.querySelectorAll('.fb-row[data-k]')].map(r => r.dataset.k) }))()`);
  const awPy = python(awkward), awKit = KIT ? python(awkward, null, true) : null;
  check('a kind with no pieces (ATM) gets no row in the legend', !aw.rows.includes('atm') && aw.rows.length === fx.furnitureKinds.length, aw.rows);
  check('csv() with a comma and quotes in a family, line breaks in a block and a layer, a note with both, empty family / handle, x_m of -0.0004, exact ties (12.25 -> 12.2, 0.0625 m -> 63 mm), office heights of 460.5 and a base of 10.5 mm, levels not in alphabetical order, unsorted input: identical to Python',
    aw.csv === awPy, aw.csv === awPy ? aw.csv.split('\r\n').filter(l => /Lux|Block A|-0\.000|0\.000/.test(l)).slice(0, 3) : { js: aw.csv.slice(0, 600), py: awPy.slice(0, 600) });
  if (KIT) check('... and identical to furniture_kit.csv_text for the same awkward model', aw.csv === awKit, aw.csv === awKit ? 'identical' : { js: aw.csv.slice(0, 600), kit: awKit.slice(0, 600) });
  check('csv(): quoted where a field has a comma, quote, CR or LF (inner quotes doubled); no -0.000; whole mm rounded half up (62.5 -> 63, 460.5 -> 461, 10.5 -> 11); levels in the model\'s order (Z1 before A2)',
    aw.csv.includes('"Chair, ""Lux"" model"') && aw.csv.includes('"Block A\nsecond line"') && aw.csv.includes('"run of 4, ""fronts"""') && aw.csv.includes('"I-FURN\rCR"') && !aw.csv.includes('-0.000')
    && aw.csv.includes(',0.000,0.062,63,570,461,0,12.2,') && aw.csv.includes(',7.000,2.000,500,500,600,11,179.9,,7,') && aw.csv.indexOf('\r\nZ1-') < aw.csv.indexOf('\r\nA2-'),
    aw.csv.split('\r\n').filter(l => l.startsWith('Z1-seat-001') || l.startsWith('Z1-plant-001')));
  await P.shot(path.join(OUT, '05_awkward_legend.png'));

  // ------------------------------------------------------------------ data the builder should never write
  flush(); await P.goto(`${PAGE}?build=0&nodownload=1${modelUrl(broken)}`);
  const warned = P.logs.filter(l => l.includes('left out'));
  const bro = await F(`({ n: F.pieces().length, z0: F.pieces().find(p => p.id === 'L1-computer-001').z0, ids: F.pieces().map(p => p.id).filter(i => i.startsWith('L9') || i.includes('sofa')), rows: document.querySelectorAll('.fb-row[data-k]').length })`);
  check('pieces on a level the page lacks or of a kind the model does not list are left out with a warning (no row, no box, no page error); a support that is not there leaves the piece on its kind\'s base',
    bro.n === nPieces && bro.ids.length === 0 && near(bro.z0, 0) && bro.rows === fx.furnitureKinds.length && warned.length === 2 && warned.some(l => l.includes('L9-seat-001')) && warned.some(l => l.includes('L1-sofa-001')), { n: bro.n, z0: bro.z0, warned });

  // a model without any approach (older, or a drawing without doors): no tick to show, every box of a blocking kind stops you, the API still answers
  flush(); await P.goto(`${PAGE}?build=0&nodownload=1${modelUrl(older)}`);
  const old = await F(`({ tick: !!document.querySelector('.fb-keep'), keep: F.keepDoorways(), set: F.setKeepDoorways(false), after: F.keepDoorways(), approach: F.pieces().every(p => Array.isArray(p.approach) && p.approach.length === 0),
    blocking: F.pieces().every(p => p.blocking === p.blocks), cols: Object.values(__host.FL).reduce((n, f) => n + f.colliders.filter(m => m.name.startsWith('furn:')).length, 0), n: F.pieces().length, rows: document.querySelectorAll('.fb-row[data-k]').length })`);
  check('a model without approach lists (or with one that is not a list): no "Keep doorways clear" tick, every piece has approach [] and blocks as its kind says, the API still reads and writes the flag',
    !old.tick && old.keep === true && old.set === true && old.after === false && old.approach && old.blocking && old.cols === 16 && old.n === nPieces && old.rows === fx.furnitureKinds.length, old);
  await F(`F.setKeepDoorways(true)`);                                  // the flag is stored under the project's key: leave nothing behind for the pages that follow

  // ------------------------------------------------------------------ the label under the pointer (Orbit only)
  await open();
  const spot = await P.evaluate(`(() => { const F = __host.furniture, L2 = __host.FL.L2.level, t = F.pieces().find(p => p.id === 'L2-table-001'), r = t.rot * Math.PI / 180, c = F.pieces().find(p => p.id === 'L2-computer-001'),
    d = 0.55; return { table: [t.x + d * Math.cos(r), L2 + t.z1, -(t.y + d * Math.sin(r))], computer: [c.x, L2 + c.z1, -c.y],
      coffee: (p => [p.x, p.z1, -p.y])(F.pieces().find(p => p.id === 'L1-coffee-table-001')) }; })()`);
  const sTable = await screenAt(...spot.table), sComp = await screenAt(...spot.computer), sCoffee = await screenAt(...spot.coffee);
  const tipTable = await hoverAt(...sTable);
  await P.shot(path.join(OUT, '06_hover.png'));
  const tipComp = await hoverAt(...sComp);
  const tipCoffeeHidden = await hoverAt(...sCoffee, false);                              // level 1, under the level-2 floor plate
  const tipSky = await hoverAt(1250, 160, false);
  check('Orbit: the pointer over a box shows a label with the kind, family, size in m (w × d × height) and level - the table\'s edge: Table / desk, 1.40 × 1.00 × 0.75 m, Level 2',
    tipTable && tipTable.includes('Table / desk') && tipTable.includes('IA_J15_WORKING TABLE - 1400W 1000D 750H') && tipTable.includes('1.40 × 1.00 × 0.75 m') && tipTable.includes('Level 2'), tipTable);
  check('the nearest box wins: over the computer on that table the label is the computer (0.74 × 0.43 × 0.45 m, from 0.75 m)',
    tipComp && tipComp.includes('Computer / monitor') && tipComp.includes('0.74 × 0.43 × 0.45 m') && tipComp.includes('from 0.75 m') && !tipComp.includes('Table / desk'), tipComp);
  check('no label over empty space, nor over a box that is hidden behind the level-2 floor plate', tipSky === null && tipCoffeeHidden === null, { sky: tipSky, coffee: tipCoffeeHidden, at: sCoffee.map(Math.round) });
  await P.clickEl('#floors [data-f=L1]'); await sleep(300);
  const tipCoffee = await hoverAt(...sCoffee);
  check('with level 1 alone showing the coffee table is labelled (Coffee / side table, 1.00 × 0.50 × 0.45 m, Level 1)', tipCoffee && tipCoffee.includes('Coffee / side table') && tipCoffee.includes('1.00 × 0.50 × 0.45 m') && tipCoffee.includes('Level 1'), tipCoffee);
  await F(`F.setVisible('coffee-table', false)`);
  const tipGone = await hoverAt(sCoffee[0] + 1, sCoffee[1], false);
  await F(`F.setVisible('coffee-table', true)`);
  check('a hidden kind has no label', tipGone === null, tipGone);
  // the label of a box in a doorway's approach says that it does not stop you (while the tick is on); the plain seat beside it says nothing
  const sSeat2 = await screenAt(2.0, 0.45, -1.0), sSeat1 = await screenAt(1.0, 0.45, -1.0);
  const tipSeat2 = await hoverAt(...sSeat2), tipSeat1 = await hoverAt(...sSeat1);
  await F(`F.setKeepDoorways(false)`);
  const tipSeat2Off = await hoverAt(...sSeat2);
  await F(`F.setKeepDoorways(true)`);
  await P.shot(path.join(OUT, '06b_hover_doorway.png'));
  check('the label of a box in a doorway\'s approach has the line "does not stop you: in the approach of L1-001, L1-002" (the ids joined by commas), the plain seat next to it none, and with the tick off it has none either',
    tipSeat2 && tipSeat2.includes('Chair / stool') && tipSeat2.includes('does not stop you: in the approach of L1-001, L1-002') && tipSeat1 && tipSeat1.includes('Chair / stool') && !tipSeat1.includes('does not stop you')
    && tipSeat2Off && tipSeat2Off.includes('Chair / stool') && !tipSeat2Off.includes('does not stop you'), { flagged: tipSeat2, plain: tipSeat1, off: tipSeat2Off, at: [sSeat2, sSeat1].map(a => a.map(Math.round)) });
  await P.clickEl('#floors [data-f=both]'); await sleep(200);
  // 2 / 3 under a still pointer: the label goes at once; then, looking straight at the tall cabinet with the pointer on it, none comes back
  await hoverAt(sTable[0] + 1, sTable[1]);
  const upBefore = await tipNow(); await P.press('Digit2'); await sleep(150);
  const upAfter = await tipNow();
  await P.evaluate(`(() => { const s = __viewer.state; s.pos.set(5.205 + 2.0, 1.6, 3.0); s.yaw = Math.PI / 2; s.pitch = 0; })()`);
  await sleep(300);
  const tipWalk = await hoverAt(700, 440, false), tipWalk2 = await hoverAt(702, 441, false);
  await P.press('Digit1'); await sleep(100);
  await hoverAt(sTable[0] + 1, sTable[1]);
  const upBefore3 = await tipNow(); await P.press('Digit3'); await sleep(150);
  const upAfter3 = await tipNow();
  await P.evaluate(`(() => { const s = __viewer.state; s.pos.set(5.205 + 2.0, 1.6, 3.0); s.yaw = Math.PI / 2; s.pitch = 0; })()`);
  await sleep(300);
  const tipGhost = await hoverAt(700, 440, false), tipGhost2 = await hoverAt(702, 441, false);
  await P.press('Digit1'); await sleep(100);
  check('pressing 2 or 3 under a still pointer takes the label away at once, and in Walk or Ghost none shows even with the pointer on a box',
    upBefore !== null && upAfter === null && upBefore3 !== null && upAfter3 === null && tipWalk === null && tipWalk2 === null && tipGhost === null && tipGhost2 === null,
    { walk: [upBefore && upBefore.slice(0, 12), upAfter, tipWalk, tipWalk2], ghost: [upBefore3 && upBefore3.slice(0, 12), upAfter3, tipGhost, tipGhost2] });
  await P.shot(path.join(OUT, '07_orbit_again.png'));
  const cam0 = await P.evaluate('__host.camera.position.toArray()');
  await P.mouse('mouseMoved', 700, 450, { button: 'none' });
  await P.mouse('mousePressed', 700, 450, { buttons: 1 });
  for (const [x, y] of [[740, 460], [800, 480], [860, 500]]) { await P.mouse('mouseMoved', x, y, { buttons: 1 }); await sleep(60); }
  const tipDrag = await tipNow();
  await P.mouse('mouseReleased', 860, 500, { buttons: 0 }); await sleep(300);
  const cam1 = await P.evaluate('__host.camera.position.toArray()');
  check('dragging still orbits the view (the label code leaves OrbitControls alone) and no label shows while dragging', Math.hypot(...cam1.map((v, i) => v - cam0[i])) > 0.5 && tipDrag === null, { moved: r2(Math.hypot(...cam1.map((v, i) => v - cam0[i]))) });

  // ------------------------------------------------------------------ the build replay shows the boxes at its end, and the ticks hold
  await open();
  await F(`F.setVisible('plant', false)`);
  await F(`F.setBlocks('seat', false)`);
  const rep = await P.evaluate(`(() => { const F = __host.furniture, ms = F.pieces().map(p => F.meshOf(p.id)), out = {};
    __build.seek(0);  out.start = ms.filter(m => m.visible).length;
    __build.seek(1);  out.end = ms.filter(m => m.visible).length; out.endOpaque = ms.every(m => m.material.opacity === 1);
    __build.skip();   out.phase = __build.phase;
    const k = Object.fromEntries(F.kinds().map(x => [x.key, x]));
    out.shown = F.pieces().filter(p => F.meshOf(p.id).visible !== k[p.kind].visible).map(p => p.id);
    out.opaque = ms.every(m => m.material.opacity === 1 && !m.material.transparent) && ms.every(m => m.children.every(c => c.material.opacity === 1 && !c.material.transparent));
    out.cols = Object.fromEntries(Object.entries(__host.FL).map(([key, f]) => [key, f.colliders.filter(m => m.name.startsWith('furn:')).map(m => m.userData.kind)]));
    out.plantHidden = !F.meshOf('L1-plant-001').visible;
    return out; })()`);
  check('build replay: the boxes are hidden at its start and shown at its end; afterwards a kind that was hidden is hidden again (restore calls apply()) and every box is opaque',
    rep.start === 0 && rep.end === nPieces && rep.phase === 'done' && rep.shown.length === 0 && rep.opaque && rep.plantHidden, rep);
  check('after the replay the colliders are still right: no plant (hidden), no chairs (stops off), no curtain, the rest there',
    !rep.cols.L1.includes('plant') && !rep.cols.L1.includes('seat') && !rep.cols.L1.includes('curtain') && rep.cols.L1.includes('table') && rep.cols.L1.includes('tall-cabinet') && rep.cols.L2.includes('table'), { L1: [...new Set(rep.cols.L1)], L2: [...new Set(rep.cols.L2)] });
  // the replay shows every late box at its end: the page's restore hook puts the doorways rule back too (on: the 2 boxes in an approach are no colliders; off: they are)
  await open();
  const repDoor = await P.evaluate(`(() => { const F = __host.furniture, out = {}, ids = ['L1-seat-002', 'L2-seat-001', 'L1-seat-001'],
      inCol = id => __host.FL[F.pieces().find(p => p.id === id).floor].colliders.includes(F.meshOf(id));
    __build.seek(0); __build.seek(1); __build.skip(); out.on = ids.map(inCol); out.onShown = ids.map(id => F.meshOf(id).visible);
    F.setKeepDoorways(false); __build.seek(0); __build.seek(1); __build.skip(); out.off = ids.map(inCol); F.setKeepDoorways(true); return out; })()`);
  check('after the build replay the doorways rule holds: with the tick on the 2 boxes in an approach are drawn but no colliders (the plain seat is one), with it off all 3 are colliders',
    repDoor.on.join() === 'false,false,true' && repDoor.onShown.every(Boolean) && repDoor.off.every(Boolean), repDoor);

  // ------------------------------------------------------------------ a model without furniture
  flush(); await P.goto(`${PAGE}?build=0&nodownload=1${modelUrl(empty)}`);
  const none = await P.evaluate(`(() => ({ api: __host.furniture, block: !!document.querySelector('.fb-block'), tip: !!document.querySelector('.fb-tip'), css: [...document.querySelectorAll('style')].some(s => s.textContent.includes('.fb-')),
    late: Object.values(__host.FL).reduce((n, f) => n + f.late.length, 0), kids: Object.values(__host.FL).reduce((n, f) => n + f.group.children.filter(o => o.name.startsWith('furn:')).length, 0), mode: __viewer.mode }))()`);
  check('a model without furniture: installFurnitureBoxes returns null and adds nothing (no block, no label, no style, nothing in the groups); the viewer works', none.api === null && !none.block && !none.tip && !none.css && none.kids === 0 && none.mode === 'orbit', none);
  await P.press('Digit2');
  check('... and Walk starts as usual', (await modeNow()) === 'walk');

  // ------------------------------------------------------------------ the bank's own furniture, once the builder has written it into bank_model.json
  const bankFile = path.join(HERE, '..', 'bank_test', 'src', 'bank_model.json');
  const bankRaw = existsSync(bankFile) ? readFileSync(bankFile) : null;          // one read: the builder may be rewriting the file
  let bank = null;
  try { bank = bankRaw && JSON.parse(bankRaw.toString('utf8')); } catch { /* half written: skip the bank run */ }
  if (bank && (bank.furniture || []).length) {
    const snap = path.join(TMP, 'bank_snapshot.json');                           // the same bytes for the page and for Python
    writeFileSync(snap, bankRaw);
    flush(); await P.goto(`${PAGE}?build=0&nodownload=1${modelUrl(snap)}`);
    const real = await P.evaluate(`(() => { const F = __host.furniture, FL = __host.FL, bad = [];
      for (const p of F.pieces()) { const m = F.meshOf(p.id); if (!m || m.parent !== FL[p.floor].group || !FL[p.floor].late.includes(m)) bad.push(p.id); }
      return { n: F.pieces().length, rows: document.querySelectorAll('.fb-row[data-k]').length, bad, csv: F.csv() }; })()`);
    check(`the bank model (${bank.furniture.length} pieces, ${bank.furnitureKinds.length} kinds, on ${bank.floors.length} levels): one box per piece in its level's group and 'late' list, one legend row per kind`,
      real.n === bank.furniture.length && real.rows === bank.furnitureKinds.length && real.bad.length === 0, real.bad.slice(0, 5));
    const bankPy = python(snap), bankKit = KIT ? python(snap, null, true) : null;
    check('the bank model: csv() equals the contract as Python writes it (expected_csv.py), byte for byte', real.csv === bankPy, real.csv === bankPy ? `${real.csv.split('\r\n').length - 2} rows` : 'differs');
    if (KIT) check('the bank model: csv() equals furniture_kit.csv_text, the builders\' own writer, byte for byte', real.csv === bankKit, real.csv === bankKit ? 'identical' : 'differs');

    // The doorways rule on the real model: the pieces the builder put in an approach (ids of doors and passages of their own level, named in the note),
    // the colliders with the tick on and off, and Walk straight through the middle of each of those doors and passages, both ways, on the bare model
    // (every kind hidden), with the boxes and the tick on, and with the tick off.
    const kindBlocks = Object.fromEntries(bank.furnitureKinds.map(k => [k.key, k.blocks !== false])), opens = Object.fromEntries((bank.openings || []).map(o => [o.id, o]));
    const inApproach = bank.furniture.filter(p => (p.approach || []).length), doorIds = [...new Set(inApproach.flatMap(p => p.approach))].sort();
    const dataOk = inApproach.every(p => p.approach.every(id => opens[id] && opens[id].floor === p.floor && ['door', 'passage'].includes(opens[id].kind)) && p.note.includes('in the approach of ' + p.approach.join(', ')));
    await P.evaluate(`(${pageHelpers.toString()})()`);
    await P.evaluate(`__viewer.setMode('walk')`);
    const rule = await P.evaluate(`(() => { const F = __host.furniture, FL = __host.FL, out = {};
      const col = () => Object.fromEntries(Object.entries(FL).map(([k, f]) => [k, f.colliders.filter(m => m.name.startsWith('furn:')).map(m => m.userData.id).sort()]));
      out.keep = F.keepDoorways(); out.on = col(); out.blocking = F.pieces().filter(p => p.blocking).map(p => p.id).sort(); F.setKeepDoorways(false); out.off = col(); F.setKeepDoorways(true); return out; })()`);
    const wantCol = keep => Object.fromEntries(bank.floors.map(f => [f.key, bank.furniture.filter(p => p.floor === f.key && kindBlocks[p.kind] && !(keep && (p.approach || []).length)).map(p => p.id).sort()]));
    check(`the bank model: ${inApproach.length} pieces stand in the approach of ${doorIds.length} doors and passages of their own level (their notes say so); with the tick on they are drawn but no colliders and every other box of a blocking kind is one; with it off all of them are`,
      inApproach.length > 0 && dataOk && rule.keep === true && JSON.stringify(rule.on) === JSON.stringify(wantCol(true)) && JSON.stringify(rule.off) === JSON.stringify(wantCol(false))
      && JSON.stringify(rule.blocking) === JSON.stringify(Object.values(wantCol(true)).flat().sort()), { inApproach: inApproach.map(p => p.id), colliders: [rule.on, rule.off].map(c => Object.values(c).flat().length) });
    const doors = await P.evaluate(`(() => { const F = __host.furniture, ops = Object.fromEntries(__host.model.openings.map(o => [o.id, o])), out = {}, all = () => ${JSON.stringify(doorIds)}.map(id => __t.doorWalk(ops[id]));
      F.kinds().forEach(k => F.setVisible(k.key, false)); out.bare = all();
      F.kinds().forEach(k => F.setVisible(k.key, true)); out.on = all();
      F.setKeepDoorways(false); out.off = all(); F.setKeepDoorways(true); return out; })()`);
    const bad = list => list.filter(d => !d.ok).map(d => d.id), bareBad = bad(doors.bare), onBad = bad(doors.on), offBad = bad(doors.off).filter(id => !bareBad.includes(id));
    note('doors and passages a box stands in front of: metres past the door line (both ways) on the bare model / tick on / tick off', doors.on.map((d, i) => `${d.id} ${[doors.bare[i], d, doors.off[i]].map(x => `${x.fwd}/${x.back}`).join(' | ')}`));
    check(`Walk straight through the middle of each of the ${doorIds.length} doors and passages with a box in front, both ways: with the tick on none is cut by a box (${doors.on.filter(d => d.kind === 'door').length} doors all open), with it off the boxes block ${offBad.length} (${offBad.join(', ')})`,
      doors.on.length === doorIds.length && onBad.every(id => bareBad.includes(id)) && doors.on.filter(d => d.kind === 'door').every(d => d.ok) && offBad.length >= 1, { bare: bareBad, on: onBad, offOnlyByBoxes: offBad });

    // Entered at the middle of each of the boxes that stop you (the double-click path), and from a spot where a box is switched on under the player
    await P.evaluate(`__viewer.setMode('walk')`);
    await F(`F.setKeepDoorways(false)`);                                            // every box of a blocking kind is a collider now
    const mids = await F(`F.pieces().filter(p => p.blocking).map(p => p.id)`);
    const into = await P.evaluate(`(() => { const out = [];
      for (const id of ${JSON.stringify(mids)}) { __t.spawn(id); out.push({ id, ...__t.verdict() }); }
      __viewer.setMode('orbit'); __viewer.setMode('walk'); return out; })()`);
    await F(`F.setKeepDoorways(true)`);
    const heldBy = into.filter(r => r.class === 'C'), inBox = into.filter(r => r.inside.length), pockets = into.filter(r => r.class === 'B');
    note('spawns in a pocket of overlapping boxes (information: nothing holds the player but other boxes)', pockets.map(r => `${r.id} in ${r.inside.join('+')}: ${r2(r.best)} m, ${r2(r.alone)} m with only those boxes`));
    check(`the bank: Walk entered at the middle of each of the ${mids.length} boxes that stop you lands the player inside a box ${inBox.length} times, and none of them is held by a box itself (the audit found 16 of 169 trapped with double-sided faces)`,
      mids.length >= 100 && inBox.length >= 20 && heldBy.length === 0, heldBy.length ? heldBy : { inside: inBox.length, leave: inBox.filter(r => r.class === 'A').length, pockets: pockets.map(r => r.id) });
    const pick = (kind, flaggedOne) => bank.furniture.find(p => p.floor === 'L1' && p.kind === kind && !!(p.approach || []).length === flaggedOne);
    const plainSeat = pick('seat', false), flaggedSeat = pick('seat', true);
    const scs = {};
    for (const [plain, flaggedId, kind] of [[plainSeat.id, flaggedSeat.id, 'seat'], [pick('table', false).id, flaggedSeat.id, 'table'], [pick('tall-cabinet', false).id, flaggedSeat.id, 'tall-cabinet']]) {
      scs[kind] = await P.evaluate(`(${pageScenarios.toString()})(${JSON.stringify(plain)}, ${JSON.stringify(flaggedId)}, ${JSON.stringify(kind)})`);
    }
    const doorwaysAll = await P.evaluate(`(() => { const F = __host.furniture, T = __t, out = [];
      for (const p of F.pieces().filter(q => q.approach.length)) { F.setKeepDoorways(true); T.standIn(p.id); const before = T.holding().includes(p.id); F.setKeepDoorways(false); out.push({ id: p.id, before, ...T.verdict() }); }
      F.setKeepDoorways(true); __viewer.setMode('orbit'); __viewer.setMode('walk'); return out; })()`);
    const scOk = Object.values(scs).every(sc => Object.values(sc).every(r => r.before === 0 && r.inside.length >= 1 && r.class !== 'C'));
    check(`the bank: a box switched on under the player (the show tick, the stops tick, typed taller: 100 -> 450 mm, a seat, a table and a tall cabinet) does not hold the player, nor does one of the ${doorwaysAll.length} boxes in an approach when the doorways tick is switched off under him`,
      scOk && doorwaysAll.length === inApproach.length && doorwaysAll.every(r => !r.before && r.class !== 'C'), { held: Object.entries(scs).flatMap(([k, sc]) => Object.entries(sc).filter(([, r]) => r.class === 'C').map(([n]) => `${k}/${n}`)), doorways: doorwaysAll.filter(r => r.class !== 'A').map(r => `${r.id} ${r.class}`) });
    await P.evaluate(`__viewer.setMode('orbit')`);
    await P.shot(path.join(OUT, '08_bank_both.png'));
    await P.clickEl('#floors [data-f=L1]'); await sleep(500);
    await P.shot(path.join(OUT, '09_bank_L1.png'));
  } else note('bank_test/src/bank_model.json has no furniture (or is being rewritten): the bank run was skipped');

  flush();
  check('no page errors (all pages, all runs)', errors.length === 0, errors.slice(0, 6));
} catch (e) {
  check('the test ran to the end', false, String(e && e.stack || e).slice(0, 900));
  flush(); if (errors.length) note('page errors so far', errors.slice(0, 6));
} finally {
  console.log(`\n${results.filter(Boolean).length} passed, ${results.filter(x => !x).length} failed  (${Math.round((Date.now() - t0) / 1000)} s; screenshots in ${OUT})`);
  await close();
  await sleep(800);
  try { rmSync(profile, { recursive: true, force: true }); } catch { /* the browser may still hold a file; the folder is under the test's temp folder anyway */ }
}
process.exit(results.every(Boolean) ? 0 : 1);
