// Checks the doors, windows and passages cut into the Sukhumvit house page (26 Oct 2026; revised 27 Oct 2026 after the
// round-3 review) in headless Edge, with the viewer's own walking probe (as presidential_test/test_presidential.mjs does
// for the suite):
//   the page loads without errors and carries the openings;
//   every detected door can be walked through, both ways (from the side that has floor when only one side has:
//   exterior doors), straight through the middle; sliding glazing that may be a door or a window (eitherKind) is
//   glazed like a window, so it is checked as a window;
//   passages are left as they were (no lintel, sill or pane in or over any of them), and none is harder to walk
//   through than before the openings were cut (the same walk on the page without openings, or its stored results);
//   every window stops you: rays at knee (0.35 m) and chest height (1.2 m) across it hit its pane or sill, and
//   walking at it you stop before it;
//   a lintel sits above every door at its head (a door may go without one only where nothing stands at a jamb),
//   and stays at the head when the wall height is changed (3.50, 2.00 and 4.50 m); a pane that reaches the top of the
//   wall follows it up;
//   no fins: nothing solid stands in a hinged door's or sash's swing (the floor its leaf sweeps), at knee or chest
//   height, and no glass or single-line piece stands in front of a window (sashes drawn open as glass);
//   the floor plates are the ones the model had before the openings were cut (fingerprint).
// Usage: node test_house_openings.mjs [page file URL]
//   page: the argument, else HOUSE_URL, else pages/house_3d_preview.html next to this file if there is one (the build
//   folder), else the project's cad_test/house_3d_preview.html.
//   The page without openings (for the passage comparison): BEFORE_URL, else baseline/pages/house_3d_preview.html next
//   to this file if there is one; its results are stored in test_house_openings_before.json next to this file and read
//   from there when no such page is at hand (the project copy).
//   TEST_PORT (default 9366), TEST_PROFILE (browser profile) and TEST_TMP (screenshots; default %TEMP%\house-openings-test)
//   keep it apart from other test runs. EDGE as in viewer-modes/cdp.mjs. Exit code 1 when a check fails.
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { tmpdir } from 'node:os';
import path from 'node:path';

const HERE = path.dirname(fileURLToPath(import.meta.url));
// The browser driver: ../viewer-modes/cdp.mjs when this file sits in a project folder (cad_test/), else the project's.
const CDP = path.join(HERE, '..', 'viewer-modes', 'cdp.mjs');
const { launch, pageApi, sleep } = await import(pathToFileURL(existsSync(CDP) ? CDP : 'C:/Users/DWP2/Desktop/Project walkthrough/viewer-modes/cdp.mjs').href);
const LOCAL = path.join(HERE, 'pages', 'house_3d_preview.html');
const URL = process.argv[2] || process.env.HOUSE_URL ||
  pathToFileURL(existsSync(LOCAL) ? LOCAL : 'C:/Users/DWP2/Desktop/Project walkthrough/cad_test/house_3d_preview.html').href;
const BEFORE_PAGE = path.join(HERE, 'baseline', 'pages', 'house_3d_preview.html');
const BEFORE_URL = process.env.BEFORE_URL || (existsSync(BEFORE_PAGE) ? pathToFileURL(BEFORE_PAGE).href : null);
const BEFORE_LIST = path.join(HERE, 'test_house_openings_before.json');
const TMP = process.env.TEST_TMP || path.join(tmpdir(), 'house-openings-test'), OUT = path.join(TMP, 'out');
mkdirSync(OUT, { recursive: true });
// The floor plates of the model before any opening was cut (cad_test/src/house3d_merged.json of 19 Oct 2026):
// sha1 of JSON.stringify(plates), 3 ground plates and 1 upper plate.
const PLATES = { sha1: 'ad13064344f9', ground: 3, upper: 1 };

const results = [];
const check = (name, ok, info) => { results.push(!!ok); console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${info !== undefined ? '   ' + JSON.stringify(info) : ''}`); };
const t0 = Date.now();
const { tab, close } = await launch({ port: Number(process.env.TEST_PORT) || 9366, profile: process.env.TEST_PROFILE || path.join(TMP, 'profile') });
console.log('page:', URL);
const P = pageApi(tab);
const errs = () => P.logs.filter(l => /exception|error/i.test(l) && !/favicon/i.test(l));

// In the page: the walking helpers (model metres; d = an opening record or {x, y, nx, ny, a, b, width}).
const HELPERS = `const v = __viewer, s = v.state;
    const floorAt = (d, k) => { s.pos.x = d.x + d.nx * k; s.pos.z = -(d.y + d.ny * k); return v.probe.onFloor(); };
    // From in front of the line (0.9 m, or nearer when that spot is tight), walk straight at it for twice that far;
    // -> metres past the line (negative: stopped before it), or why there was no start.
    const cross = (d, sign) => {
      const nx = d.nx * sign, ny = d.ny * sign, deg = Math.atan2(-nx, ny) * 180 / Math.PI;
      let why = 'no start';
      for (const back of [0.9, 0.7, 0.55, 0.45]) {
        s.pos.x = d.x - nx * back; s.pos.z = -(d.y - ny * back);
        if (!v.probe.onFloor()) { why = 'no floor'; continue; }
        if (v.probe.clearance() < 0.25) { why = 'tight'; continue; }
        v.probe.walk(deg, back * 2);
        return Math.round(((s.pos.x - d.x) * nx + (-s.pos.z - d.y) * ny) * 100) / 100;
      }
      return why;
    };
    const walkThrough = d => { const r = { floorPos: floorAt(d, 0.9), floorNeg: floorAt(d, -0.9) };
      if (r.floorNeg) r.fwd = cross(d, 1);                    // from the -n side through to the +n side
      if (r.floorPos) r.back = cross(d, -1);
      return r; };`;
const num = x => typeof x === 'number';
const judge = r => {
  if (r.floorPos && r.floorNeg) return num(r.fwd) && num(r.back) && r.fwd > 0.3 && r.back > 0.3 ? 'both ways' : 'blocked';
  if (r.floorPos || r.floorNeg) return [r.fwd, r.back].some(x => num(x) && x > -0.15) ? 'from the floor side' : 'blocked';
  return 'skipped';
};
const RANK = { blocked: 0, 'from the floor side': 1, 'both ways': 2 };

try {
  await P.goto(URL + '?build=0&nodownload=1');
  const info = await P.evaluate(`(() => { const h = __host, n = f => h.openings[f] || [];
    const count = f => ({ door: n(f).filter(o => o.kind === 'door' && !o.glazed).length, glazed: n(f).filter(o => o.glazed).length,
                          passage: n(f).filter(o => o.kind === 'passage').length });
    return { ground: count('ground'), upper: count('upper'), meshes: Object.fromEntries(['ground', 'upper'].map(f => [f, Object.keys(h.pieces[f] || {})])),
             err: getComputedStyle(document.getElementById('vm-err')).display !== 'none' }; })()`);
  check('page loads without errors and carries the openings', !errs().length && !info.err && info.ground.door + info.upper.door > 0 &&
        info.meshes.ground.length === 2 && info.meshes.upper.length === 2, { openings: { ground: info.ground, upper: info.upper }, meshes: info.meshes, errors: errs() });

  // Floor plates: exactly the ones the model had before the openings.
  const plates = await P.evaluate('JSON.stringify(__host.plates)');
  const sha = createHash('sha1').update(plates).digest('hex').slice(0, 12), pl = JSON.parse(plates);
  check('the floor plates are unchanged (same outlines as before the openings were cut)', sha === PLATES.sha1 && pl.ground.length === PLATES.ground && pl.upper.length === PLATES.upper,
        { sha1: sha, expected: PLATES.sha1, plates: { ground: pl.ground.length, upper: pl.upper.length } });

  // ---------------------------------------------------------------- walking: doors, passages and windows, per floor
  await P.press('Digit2');                                     // Walk, ground floor
  const walkFloor = () => P.evaluate(`(() => { ${HELPERS}
    const keep = s.pos.clone(), F = s.floor.key, out = { doors: [], windows: [], passages: [] }, lv = s.floor.level;
    for (const d of __host.openings[F]) {
      if (d.glazed) {                                          // windows, and the sliding glass doors glazed like them
        const r = { id: d.id, kind: d.kind, floorPos: floorAt(d, 0.9), floorNeg: floorAt(d, -0.9), rays: [], walk: [] };
        for (const [sign, has] of [[1, r.floorNeg], [-1, r.floorPos]]) {     // from each side that has floor
          if (!has) continue;
          const nx = d.nx * sign, ny = d.ny * sign, ux = (d.b[0] - d.a[0]) / d.width, uy = (d.b[1] - d.a[1]) / d.width;
          // the pane stands on the glazing, d.pane across the line (+n): 0.6 + sign * pane ahead, less half its 3 cm
          const paneAt = Math.round((0.6 + sign * (d.pane || 0) - 0.015) * 1000) / 1000;
          for (const h of [0.35, 1.2]) for (const t of [0.1, 0.3, 0.5, 0.7, 0.9]) {
            const px = d.a[0] + ux * d.width * t - nx * 0.6, py = d.a[1] + uy * d.width * t - ny * 0.6;
            const hit = __host.cast(F, [px, lv + h, -py], [nx, 0, -ny], 1.2);
            r.rays.push(hit ? { d: Math.round(hit.d * 1000) / 1000, mesh: hit.name, pane: paneAt } : { pane: paneAt });
          }
          r.walk.push(cross(d, sign));
        }
        out.windows.push(r);
      } else if (d.kind === 'door') {
        const r = { id: d.id, kind: d.kind, width: d.width, ...walkThrough(d) };
        // what stands in the way, if anything: knee and chest rays across the line at the middle, 0.6 m each side
        const block = [];
        for (const h of [0.35, 1.2]) {
          const hit = __host.cast(F, [d.x - d.nx * 0.6, lv + h, -(d.y - d.ny * 0.6)], [d.nx, 0, -d.ny], 1.2);
          if (hit) block.push(hit.name + ' at ' + (Math.round((hit.d - 0.6) * 100) / 100) + ' m');
        }
        if (block.length) r.inTheWay = block;
        out.doors.push(r);
      } else {                                                 // a passage: walked, and nothing of the cut in or over it
        const r = { id: d.id, floor: F, x: d.x, y: d.y, nx: d.nx, ny: d.ny, a: d.a, b: d.b, width: d.width, ...walkThrough(d), pieces: [], skipped: 0 };
        const ux = (d.b[0] - d.a[0]) / d.width, uy = (d.b[1] - d.a[1]) / d.width;
        // a door or window of its own may cross or touch a detected passage (its lintel is then over the passage line):
        // sample points within 0.3 m of another opening's line are left out
        const segDist = (p, q) => { const L2 = (q.b[0] - q.a[0]) ** 2 + (q.b[1] - q.a[1]) ** 2,
          t = L2 ? Math.max(0, Math.min(1, ((p[0] - q.a[0]) * (q.b[0] - q.a[0]) + (p[1] - q.a[1]) * (q.b[1] - q.a[1])) / L2)) : 0;
          return Math.hypot(p[0] - q.a[0] - t * (q.b[0] - q.a[0]), p[1] - q.a[1] - t * (q.b[1] - q.a[1])); };
        const others = __host.openings[F].filter(q => q.kind !== 'passage');
        for (const t of [0.25, 0.5, 0.75]) {
          const px = d.a[0] + ux * d.width * t, py = d.a[1] + uy * d.width * t;
          if (others.some(q => segDist([px, py], q) < 0.3)) { r.skipped++; continue; }
          for (const h of [0.35, 1.2]) {
            const hit = __host.cast(F, [px - d.nx * 0.6, lv + h, -(py - d.ny * 0.6)], [d.nx, 0, -d.ny], 1.2);
            if (hit && /lintels and sills|window panes/.test(hit.name)) r.pieces.push(hit.name + ' across at ' + h + ' m');
          }
          const up = __host.cast(F, [px, lv + 1.0, -py], [0, 1, 0], 8);
          if (up && /lintels and sills|window panes/.test(up.name)) r.pieces.push(up.name + ' overhead at ' + (Math.round((up.d + 1) * 100) / 100) + ' m');
        }
        out.passages.push(r);
      }
    }
    s.pos.copy(keep); return out; })()`);
  const ground = await walkFloor();
  await P.shot(path.join(OUT, 'walk_ground.png'));
  await P.press('PageUp');
  const onUpper = (await P.evaluate('__viewer.state.floor.key')) === 'upper';
  const upper = onUpper ? await walkFloor() : { doors: [], windows: [], passages: [] };
  check('PgUp reaches the upper floor for its checks', onUpper);
  {
    const list = [...ground.doors, ...upper.doors].map(r => ({ ...r, result: judge(r) }));
    const ids = k => list.filter(r => r.result === k).map(r => r.id);
    const bad = list.filter(r => r.result === 'blocked');
    check(`every door can be walked through (${list.length}: ${ids('both ways').length} both ways, ${ids('from the floor side').length} from the only side with floor, ${ids('skipped').length} skipped: no floor on either side)`,
          list.length > 0 && !bad.length, bad.length ? bad : undefined);
    if (ids('from the floor side').length) console.log(`      doors with floor on one side only (walked from it): ${ids('from the floor side').join(', ')}`);
    if (ids('skipped').length) console.log(`      doors skipped (no floor plate 0.9 m out on either side): ${ids('skipped').join(', ')}`);
  }
  // ---------------------------------------------------------------- passages: left as they were
  const passages = [...ground.passages, ...upper.passages].map(r => ({ ...r, result: judge(r) }));
  const touched = passages.filter(r => r.pieces.length);
  const skippedPts = passages.filter(r => r.skipped).map(r => `${r.id} (${r.skipped})`);
  check(`passages are left as they were: no lintel, sill or pane across or over any of them (${passages.length} passages; knee and chest rays across at 1/4, 1/2 and 3/4, a ray up from 1 m)`,
        passages.length > 0 && !touched.length, touched.length ? touched.map(r => ({ id: r.id, pieces: r.pieces })) : undefined);
  if (skippedPts.length) console.log(`      sample points left out where a door or window crosses or touches the passage: ${skippedPts.join(', ')}`);
  // The same walk on the page without openings (or its stored results): no passage may be harder to walk through now.
  let before = null, beforeFrom = '';
  if (BEFORE_URL) {
    await P.goto(BEFORE_URL + '?build=0&nodownload=1'); await sleep(500);
    await P.press('Digit2');
    const walkBefore = list => P.evaluate(`(() => { ${HELPERS}
      const keep = s.pos.clone(), out = (${JSON.stringify(list)}).map(d => ({ ...d, ...walkThrough(d) }));
      s.pos.copy(keep); return out; })()`);
    const strip = r => ({ id: r.id, floor: r.floor, x: r.x, y: r.y, nx: r.nx, ny: r.ny, a: r.a, b: r.b, width: r.width });
    const bg = await walkBefore(passages.filter(r => r.floor === 'ground').map(strip));
    await P.press('PageUp');
    const bu = (await P.evaluate('__viewer.state.floor.key')) === 'upper' ? await walkBefore(passages.filter(r => r.floor === 'upper').map(strip)) : [];
    before = [...bg, ...bu].map(r => ({ ...r, result: judge(r) }));
    beforeFrom = BEFORE_URL;
    writeFileSync(BEFORE_LIST, JSON.stringify({ page: BEFORE_URL.split('/').slice(-3).join('/'), made: new Date().toISOString().slice(0, 10),
      note: 'Passages walked on the house page before the openings were cut (test_house_openings.mjs); matched by position.',
      passages: before.map(({ id, floor, x, y, a, b, width, floorPos, floorNeg, fwd, back, result }) => ({ id, floor, x, y, a, b, width, floorPos, floorNeg, fwd, back, result })) }, null, 1));
  } else if (existsSync(BEFORE_LIST)) {
    before = JSON.parse(readFileSync(BEFORE_LIST, 'utf-8')).passages; beforeFrom = path.basename(BEFORE_LIST);
  }
  if (before) {
    const match = r => before.find(q => q.floor === r.floor && Math.hypot(q.x - r.x, q.y - r.y) < 0.05);
    const rows = passages.map(r => ({ id: r.id, now: r.result, before: match(r) ? match(r).result : 'not walked before' }));
    const worse = rows.filter(x => x.before in RANK && RANK[x.now] < RANK[x.before]);
    const blocked = rows.filter(x => x.now === 'blocked');
    check(`no passage is harder to walk through than before the openings were cut (${rows.length} passages, compared with ${beforeFrom})`,
          !worse.length && rows.every(x => x.before !== 'not walked before'), worse.length ? worse : rows.filter(x => x.before === 'not walked before'));
    if (blocked.length) console.log(`      blocked now and before (left as they are; the passage rule does not cut): ${blocked.map(x => {
      const r = passages.find(p => p.id === x.id);
      return `${x.id} (fwd ${r.fwd ?? '-'}, back ${r.back ?? '-'})`; }).join(', ')}`);
  } else {
    check('no passage is harder to walk through than before the openings were cut', false, 'no page without openings (BEFORE_URL) and no test_house_openings_before.json');
  }
  if (BEFORE_URL) { await P.goto(URL + '?build=0&nodownload=1'); await sleep(300); }

  // ---------------------------------------------------------------- windows stop you
  const windows = [...ground.windows, ...upper.windows];
  const wTested = windows.filter(w => w.rays.length), wSkipped = windows.filter(w => !w.rays.length).map(w => w.id);
  // A ray stopped by the window: a hit on its pane (where its glazing is) or its sill (from 0.3 m ahead), on the window
  // meshes; or on a wall that meets the window (a partition or a wall stub standing against its end), never on a glass
  // or single-line piece. At least 60 % of the rays must hit the window's own pane or sill.
  const own = x => x && num(x.d) && x.d >= 0.3 && x.d <= x.pane + 0.02 && /window panes|lintels and sills/.test(x.mesh);
  const stopped = x => own(x) || (x && num(x.d) && x.d >= 0.3 && x.d <= x.pane + 0.02 && /:wall$/.test(x.mesh));
  const wBad = wTested.filter(w => !w.rays.every(stopped) || w.rays.filter(own).length < 0.6 * w.rays.length || w.walk.some(x => !num(x) || x > -0.1));
  const byWall = wTested.filter(w => w.rays.some(x => stopped(x) && !own(x))).map(w => `${w.id} (${w.rays.filter(x => stopped(x) && !own(x)).length})`);
  const nGlazedDoors = windows.filter(w => w.kind === 'door').length;
  check(`every window stops you: knee and chest rays hit its pane or sill and walking at it you stop before it (${wTested.length} tested, ${nGlazedDoors} of them sliding glass doors glazed like windows; ${wSkipped.length} skipped: no floor on either side)`,
        wTested.length > 0 && !wBad.length, wBad.length ? wBad.map(w => ({ id: w.id, raysStopped: `${w.rays.filter(stopped).length}/${w.rays.length}`,
          missed: w.rays.filter(x => !stopped(x)).slice(0, 3), walk: w.walk })) : undefined);
  if (wSkipped.length) console.log(`      windows skipped: ${wSkipped.join(', ')}`);
  if (byWall.length) console.log(`      rays stopped by a wall that meets the window: ${byWall.join(', ')}`);
  await P.press('Escape'); await sleep(300);

  // ---------------------------------------------------------------- lintels at the door heads; fins
  const lintels = () => P.evaluate(`(() => { const out = [];
    for (const F of ['ground', 'upper']) {
      const lv = __build.state.settings[F].level, H = __build.state.settings[F].height;
      for (const d of __host.openings[F].filter(o => o.kind === 'door' && !o.glazed)) {
        // A door goes without a lintel only where nothing stands at a jamb for it to sit on (jambGap null).
        const free = d.jambGap.some(g => g === null);
        const want = !free && d.head < H;
        const hit = __host.cast(F, [d.x, lv + 0.5, -d.y], [0, 1, 0], 8);
        const at = hit ? Math.round((hit.d + 0.5) * 1000) / 1000 : null;
        out.push({ id: d.id, head: d.head, lintel: d.lintel, free, want, at, mesh: hit && hit.name,
                   ok: d.lintel === (!free && d.head < __host.openings.__H0[F] - 0.005) &&
                       (want ? !!hit && /lintels/.test(hit.name) && Math.abs(at - d.head) < 0.02 : !hit || !/lintels/.test(hit.name) || at >= H - 0.02) });
      }
    }
    return out; })()`);
  await P.evaluate(`__host.openings.__H0 = { ground: __build.state.settings.ground.height, upper: __build.state.settings.upper.height }`);
  const L0 = await lintels();
  const withL = L0.filter(r => r.want), noL = L0.filter(r => !r.lintel && r.free);
  check(`a lintel sits above every door at its head (${withL.length} doors; without one, as nothing stands at a jamb: ${noL.map(r => r.id).join(', ') || 'none'})`,
        withL.length > 0 && L0.every(r => r.ok), L0.filter(r => !r.ok));
  // Panes that reach the top of the wall (no lintel) must follow it: rays across their line just under the wall top.
  const topPanes = H => P.evaluate(`(() => { const out = [], F = 'ground', lv = __build.state.settings[F].level;
    for (const d of __host.openings[F].filter(o => o.glazed && !o.lintel && o.head >= __host.openings.__H0[F] - 0.005)) {
      for (const z of [${H} - 0.3, ${H} - 0.05]) {
        const hit = __host.cast(F, [d.x - d.nx * 0.6, lv + z, -(d.y - d.ny * 0.6)], [d.nx, 0, -d.ny], 1.2);
        out.push({ id: d.id, z: Math.round(z * 100) / 100, mesh: hit && hit.name });
      }
    }
    return out; })()`);
  // Change the ground floor's wall height in Build settings: heads stay where they are (3.50 m: lintels from the
  // head up to 3.50; 2.00 m: lower than the heads, no lintels left; 4.50 m: higher than the drawing's 3.90 m, lintels
  // from the heads up to 4.50 and the panes that reach the top run up with it).
  const setHeight = async h => {
    await P.clickEl('#br-open'); await sleep(300);
    await P.evaluate(`(() => { const e = document.querySelector('#br-card input[data-k=ground][data-p=height]'); e.value = '${h}'; e.dispatchEvent(new Event('change')); })()`);
    await P.clickEl('#br-skip0'); await sleep(300);
  };
  await setHeight('3.50');
  const L1 = (await lintels()).filter(r => r.id.startsWith('ground'));
  await setHeight('2.00');
  const L2 = (await lintels()).filter(r => r.id.startsWith('ground'));
  await setHeight('4.50');
  const L4 = (await lintels()).filter(r => r.id.startsWith('ground'));
  const T4 = await topPanes(4.5);
  await setHeight('3.90');
  const L3 = (await lintels()).filter(r => r.id.startsWith('ground'));
  const okHead = r => r.ok;
  check('door heads stay put when the wall height changes (ground walls 3.50 m: lintels still at the heads; 2.00 m: none left; 4.50 m: at the heads; back to 3.90 m)',
        L1.every(okHead) && L1.some(r => r.want) && L2.every(r => !r.want && r.ok) && L4.every(okHead) && L4.some(r => r.want) && L3.every(okHead),
        { at350: L1.filter(r => !r.ok).map(r => r.id), at200: L2.filter(r => !r.ok).map(r => r.id), at450: L4.filter(r => !r.ok).map(r => r.id), back: L3.filter(r => !r.ok).map(r => r.id) });
  const topBad = T4.filter(r => !r.mesh || !/window panes/.test(r.mesh));
  check(`panes that reach the top of the wall follow it up (ground walls raised to 4.50 m: ${[...new Set(T4.map(r => r.id))].join(', ') || 'none'} still glazed at 4.20 and 4.45 m)`,
        T4.length > 0 && !topBad.length, topBad.length ? topBad : undefined);

  const fins = await P.evaluate(`(() => { const out = { tested: 0, leaves: 0, skipped: [], hits: [] };
    for (const F of ['ground', 'upper']) {
      const lv = __build.state.settings[F].level;
      for (const d of __host.openings[F].filter(o => o.kind !== 'passage')) {
        if (!d.leaves.length) { if (d.kind === 'door') out.skipped.push(d.id); continue; }
        out.tested++;
        for (const L of d.leaves) {
          out.leaves++;
          // chords along arcs inside the swept quarter disc, 8 to 82 degrees from the closed leaf, at knee and chest height
          const at = (r, t) => [L.hinge[0] + r * (L.closed[0] * Math.cos(t) + L.open[0] * Math.sin(t)), L.hinge[1] + r * (L.closed[1] * Math.cos(t) + L.open[1] * Math.sin(t))];
          for (const h of [0.35, 1.2]) for (const k of [0.3, 0.55, 0.8, 0.95]) {
            const r = L.r * k;
            for (let i = 0; i < 8; i++) {
              const t0 = (8 + 74 * i / 8) * Math.PI / 180, t1 = (8 + 74 * (i + 1) / 8) * Math.PI / 180;
              const p = at(r, t0), q = at(r, t1), len = Math.hypot(q[0] - p[0], q[1] - p[1]);
              const hit = __host.cast(F, [p[0], lv + h, -p[1]], [q[0] - p[0], 0, -(q[1] - p[1])], len);
              if (hit) { out.hits.push({ id: d.id, height: h, radius: Math.round(r * 100) / 100, mesh: hit.name }); }
            }
          }
        }
      }
    }
    return out; })()`);
  const finIds = [...new Set(fins.hits.map(h => h.id))];
  check(`no fins: nothing solid in any hinged door's (or sash's) swing (${fins.tested} doors and casements, ${fins.leaves} leaves tested; ${fins.skipped.length} sliding or pocket doors have no swing)`,
        fins.tested > 0 && !fins.hits.length, fins.hits.length ? { openings: finIds, hits: fins.hits.slice(0, 12) } : undefined);
  // Casement sashes whose hinges the drawing does not give (several sashes in one window) were also drawn open as glass
  // leaves: no glass or single-line piece may stand in front of a window, 0.3 and 0.6 m out on either side, across
  // 10-90 % of its width (a wall there is a partition meeting the window at a mullion, which is fine).
  const front = await P.evaluate(`(() => { const out = { tested: 0, hits: [] };
    for (const F of ['ground', 'upper']) {
      const lv = __build.state.settings[F].level;
      for (const d of __host.openings[F].filter(o => o.glazed)) {
        out.tested++;
        const ux = (d.b[0] - d.a[0]) / d.width, uy = (d.b[1] - d.a[1]) / d.width;
        for (const side of [1, -1]) for (const c of [0.3, 0.6]) for (const h of [0.35, 1.2]) {
          const off = side * (c + Math.max(Math.abs(d.depth[0]), Math.abs(d.depth[1])));
          const p = [d.a[0] + ux * d.width * 0.1 + d.nx * off, d.a[1] + uy * d.width * 0.1 + d.ny * off];
          const hit = __host.cast(F, [p[0], lv + h, -p[1]], [ux, 0, -uy], d.width * 0.8);
          if (hit && /:(glass|single)$/.test(hit.name)) out.hits.push({ id: d.id, side, out: c, height: h, mesh: hit.name, at: Math.round(hit.d * 100) / 100 });
        }
      }
    }
    return out; })()`);
  const frontIds = [...new Set(front.hits.map(h => h.id))];
  check(`no leaves left in front of the windows (${front.tested} windows and glazed doors: no glass or single-line piece 0.3 or 0.6 m out on either side)`,
        front.tested > 0 && !front.hits.length, front.hits.length ? { windows: frontIds, hits: front.hits.slice(0, 12) } : undefined);

  check('no page errors during these checks', !errs().length, errs());
  // A look through a door, for the record: Walk on the ground floor, facing the living room's double door from the link.
  await P.goto(URL + '?build=0&nodownload=1&mode=walk&floor=ground&x=-12.9&z=-3.95&yaw=-90');
  await sleep(800); await P.shot(path.join(OUT, 'walk_door_living.png'));
} catch (e) {
  check('ran to the end', false, e.message.split('\n').slice(0, 3).join(' | '));
}
console.log(`\n${results.filter(Boolean).length} passed, ${results.filter(x => !x).length} failed  (${Math.round((Date.now() - t0) / 1000)} s)`);
await close();
process.exit(results.every(Boolean) ? 0 : 1);
