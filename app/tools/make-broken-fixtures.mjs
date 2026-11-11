#!/usr/bin/env node
// The broken-model corpus (DESIGN.md 5.6, 17.1; WORK_BREAKDOWN S.8). Scaffold tool:  node tools/make-broken-fixtures.mjs
// Copies of fixtures/models/bank-v2.model.json with ONE fault each -> fixtures/models/broken/{schema,cross}/*.json and
// fixtures/models/broken/expected.json (file -> the JSON Pointer every checker must report). Before writing, each case is
// checked here: the schema cases fail ajv (Ajv2020, strict) at exactly that path and nothing else; the cross cases pass
// the schema and break exactly one rule of 5.6 (the strict form, as the API applies it) at that path.
// The rooms scaffold R0 (11 Nov 2026) added the BuiltModel v2 cases (v2-*; docs/rooms/DESIGN.md R-12.1): the same model
// with one stairway S1 (L1 to L2), a tread and a landing of it, two spaces and one drawn name in a space, one fault each.
// The v1 cases are made from the unchanged base, so their files stay byte for byte.
import { mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import Ajv2020 from 'ajv/dist/2020.js';
import { APP } from './lib.mjs';

const BASE = 'fixtures/models/bank-v2.model.json';
const base = JSON.parse(readFileSync(path.join(APP, BASE), 'utf8'));
const clone = () => structuredClone(base);
const schema = JSON.parse(readFileSync(path.join(APP, 'docs', 'built-model.schema.json'), 'utf8'));
const ajv = new Ajv2020({ strict: true, allErrors: true });
const validate = ajv.compile(schema);

// The 5.6 cross-reference rules, strict. Paths: the offending value (a duplicate: its later occurrence).
function crossIssues(m) {
  const out = [];
  const keys = m.floors.map(f => f.key), ks = new Set(keys);
  keys.forEach((k, i) => { if (keys.indexOf(k) !== i) out.push(`/floors/${i}/key`); });
  m.floors.forEach((f, i) => { if (i && f.level < m.floors[i - 1].level) out.push(`/floors/${i}/level`); });
  m.parts.forEach((p, i) => {
    if (!ks.has(p.floor)) out.push(`/parts/${i}/floor`);
    if (!(p.z1 > p.z0)) out.push(`/parts/${i}/z1`);
    if (p.plinth && p.kind !== 'slab') out.push(`/parts/${i}/plinth`);
  });
  for (const name of ['stairs', 'voids', 'closures', 'stairOutlines', 'colliderSkins', 'pictureFrame']) {
    for (const k of Object.keys(m[name] ?? {})) if (!ks.has(k)) out.push(`/${name}/${k}`);
  }
  for (const [k, s] of Object.entries(m.stairs)) for (const a of ['below', 'above', 'panels']) if (s[a] && s[a].length % 4) out.push(`/stairs/${k}/${a}`);
  for (const coll of ['rooms', 'openings', 'probes']) m[coll].forEach((x, i) => { if (!ks.has(x.floor)) out.push(`/${coll}/${i}/floor`); });
  const ids = m.openings.map(o => o.id);
  ids.forEach((id, i) => { if (ids.indexOf(id) !== i) out.push(`/openings/${i}/id`); });
  // BuiltModel v2 (rooms/DESIGN.md R-12.1)
  const stackOf = new Map(m.floors.map(f => [f.key, f.stack ?? 'main'])), levelOf = new Map(m.floors.map(f => [f.key, f.level]));
  const stairFrom = new Map();
  (m.stairways ?? []).forEach((s, i) => {
    if (stairFrom.has(s.id)) out.push(`/stairways/${i}/id`); else stairFrom.set(s.id, s.from);
    if (!ks.has(s.from)) out.push(`/stairways/${i}/from`);
    if (!ks.has(s.to)) out.push(`/stairways/${i}/to`);
    else if (ks.has(s.from) && (stackOf.get(s.to) !== stackOf.get(s.from) || !(levelOf.get(s.to) > levelOf.get(s.from)))) out.push(`/stairways/${i}/to`);
  });
  m.parts.forEach((p, i) => {
    if (p.stair === undefined) { if (p.kind === 'tread' || p.kind === 'landing') out.push(`/parts/${i}`); return; }
    if (!stairFrom.has(p.stair) || stairFrom.get(p.stair) !== p.floor) out.push(`/parts/${i}/stair`);
  });
  const spaceFloor = new Map();
  (m.spaces ?? []).forEach((s, i) => {
    if (!ks.has(s.floor)) out.push(`/spaces/${i}/floor`);
    if (spaceFloor.has(s.id)) out.push(`/spaces/${i}/id`); else spaceFloor.set(s.id, s.floor);
  });
  m.rooms.forEach((r, i) => { if (r.space !== undefined && spaceFloor.get(r.space) !== r.floor) out.push(`/rooms/${i}/space`); });
  if (m.furniture) {
    const kinds = new Set(m.furnitureKinds.map(k => k.key)), fid = m.furniture.map(p => p.id), idSet = new Set(fid), oids = new Set(ids);
    fid.forEach((id, i) => { if (fid.indexOf(id) !== i) out.push(`/furniture/${i}/id`); });
    m.furniture.forEach((p, i) => {
      if (!kinds.has(p.kind)) out.push(`/furniture/${i}/kind`);
      if (!ks.has(p.floor)) out.push(`/furniture/${i}/floor`);
      if (p.on !== null && !idSet.has(p.on)) out.push(`/furniture/${i}/on`);
      p.approach.forEach((a, j) => { if (!oids.has(a)) out.push(`/furniture/${i}/approach/${j}`); });
    });
    const n = {};
    for (const p of m.furniture) n[p.kind] = (n[p.kind] ?? 0) + 1;
    m.furnitureKinds.forEach((k, i) => { if ((n[k.key] ?? 0) !== k.count) out.push(`/furnitureKinds/${i}/count`); });
  }
  return out;
}

const firstWith = (pred, what) => { const i = base.furniture.findIndex(pred); if (i < 0) throw new Error(`no piece ${what}`); return i; };
const iOn = firstWith(p => p.on, 'standing on another');
const iApproach = firstWith(p => p.approach.length, 'with an approach list');

// The v2 base: the bank with one stairway, a tread and a landing of it, two spaces and one drawn name in a space.
const iTread = base.parts.length, iLanding = iTread + 1;
const iRoom = base.rooms.findIndex(r => r.floor === 'L1');
if (iRoom < 0) throw new Error('no drawn name on L1');
function v2() {
  const m = clone();
  m.stairways = [{
    id: 'S1', from: 'L1', to: 'L2', kind: 'straight', risers: 21, riser: 0.176, going: 0.28, width: 1.2,
    bottom: [0, -1], top: [0, 6.88], walk: [[0, -1], [0, 6.88]], direction: 'word', treads: 20, landings: 1,
  }];
  m.parts.push({ floor: 'L1', kind: 'tread', z0: 0, z1: 0.176, follow: false, o: [[-0.6, 0], [0.6, 0], [0.6, 0.28], [-0.6, 0.28]], h: [], label: 'stair S1 tread 1', fit: 'storey', stair: 'S1' });
  m.parts.push({ floor: 'L1', kind: 'landing', z0: 1.61, z1: 1.76, follow: false, o: [[-0.6, 2.8], [0.6, 2.8], [0.6, 4], [-0.6, 4]], h: [], label: 'stair S1 landing 10', fit: 'storey', stair: 'S1' });
  m.spaces = [
    { id: 'L1-R1', floor: 'L1', o: [[1, 1], [5, 1], [5, 4], [1, 4]], h: [], area: 12, name: m.rooms[iRoom].name, names: [m.rooms[iRoom].name], source: 'network', ceiling: true },
    { id: 'L2-R1', floor: 'L2', o: [[1, 1], [5, 1], [5, 4], [1, 4]], h: [], area: 12, name: '', names: [], source: 'network', ceiling: true },
  ];
  m.rooms[iRoom].space = 'L1-R1';
  return m;
}

const cases = {
  'schema/wrong-type.json': { path: '/parts/3/z1', viewer: 'throws', fault: 'parts[3].z1 is the string "3.7"', make: m => { m.parts[3].z1 = '3.7'; } },
  'schema/missing-field.json': { path: '/floors/1', viewer: 'throws', fault: 'floors[1] has no wallHeight (a missing property is reported at its parent object)', make: m => { delete m.floors[1].wallHeight; } },
  'schema/bad-pattern.json': { path: '/photoName', viewer: 'throws', fault: 'photoName "Bangkok Bank" has a space', make: m => { m.photoName = 'Bangkok Bank'; } },
  // fix step (3 Nov code review): ECMA-262's $ matches only at the very end; Python's also before a final newline, so the
  // API's jsonschema took this while the viewer refused it
  'schema/pattern-trailing-newline.json': { path: '/photoName', viewer: 'throws', fault: 'photoName ends in a newline ("BangkokBank-Sampeng\\n")', make: m => { m.photoName += '\n'; } },
  'cross/unknown-floor.json': { path: '/parts/10/floor', viewer: 'throws', fault: 'parts[10] is on floor "L9", which the model does not have', make: m => { m.parts[10].floor = 'L9'; } },
  'cross/duplicate-opening-id.json': { path: '/openings/5/id', viewer: 'throws', fault: 'openings[5] repeats the id of openings[4] (the later occurrence is reported)', make: m => { m.openings[5].id = m.openings[4].id; } },
  'cross/z1-not-above-z0.json': { path: '/parts/3/z1', viewer: 'throws', fault: 'parts[3].z1 equals its z0 (0)', make: m => { m.parts[3].z1 = m.parts[3].z0; } },
  'cross/stair-6-numbers.json': { path: '/stairs/L1/below', viewer: 'throws', fault: 'stairs.L1.below has 6 numbers (not a multiple of 4)', make: m => { m.stairs.L1.below = m.stairs.L1.below.slice(0, 6); } },
  'cross/furniture-unknown-kind.json': {
    path: '/furniture/0/kind', viewer: 'warns', fault: 'furniture[0].kind "spaceship" is not in furnitureKinds (its old kind\'s count is lowered by one, so the counts still agree)',
    make: m => { const old = m.furniture[0].kind; m.furniture[0].kind = 'spaceship'; m.furnitureKinds.find(k => k.key === old).count -= 1; },
  },
  'cross/furniture-missing-support.json': {
    path: `/furniture/${iOn}/on`, viewer: 'warns', fault: `furniture[${iOn}].on names no piece`, make: m => { m.furniture[iOn].on = 'no-such-piece'; },
  },
  'cross/furniture-unknown-approach.json': {
    path: `/furniture/${iApproach}/approach/0`, viewer: 'warns', fault: `furniture[${iApproach}].approach[0] names no opening`, make: m => { m.furniture[iApproach].approach[0] = 'NO-SUCH-DOOR'; },
  },
  'cross/furniture-count.json': {
    path: '/furnitureKinds/0/count', viewer: 'warns', fault: 'furnitureKinds[0].count is one more than its pieces', make: m => { m.furnitureKinds[0].count += 1; },
  },
  // BuiltModel v2 (docs/rooms/DESIGN.md R-12.1), one case per rule
  'schema/v2-walk-one-point.json': { v2: true, path: '/stairways/0/walk', viewer: 'throws', fault: 'stairways[0].walk has one point (a walking line has at least 2)', make: m => { m.stairways[0].walk = [[0, -1]]; } },
  'cross/v2-stairway-unknown-floor.json': { v2: true, path: '/stairways/0/to', viewer: 'throws', fault: 'stairways[0].to is "L9", which the model does not have', make: m => { m.stairways[0].to = 'L9'; } },
  'cross/v2-stairway-not-above.json': { v2: true, path: '/stairways/0/to', viewer: 'throws', fault: 'stairways[0].to is its own from floor (to must be above from)', make: m => { m.stairways[0].to = 'L1'; } },
  'cross/v2-stairway-other-stack.json': { v2: true, path: '/stairways/0/to', viewer: 'throws', fault: 'floors[1] is in another stack ("annex"): stairways[0] would leave its stack', make: m => { m.floors[1].stack = 'annex'; } },
  'cross/v2-duplicate-stairway-id.json': { v2: true, path: '/stairways/1/id', viewer: 'throws', fault: 'stairways[1] repeats the id of stairways[0] (the later occurrence is reported)', make: m => { m.stairways.push(structuredClone(m.stairways[0])); } },
  'cross/v2-part-unknown-stairway.json': { v2: true, path: `/parts/${iTread}/stair`, viewer: 'throws', fault: `parts[${iTread}] (a tread) names the stairway "S9", which the model does not have`, make: m => { m.parts[iTread].stair = 'S9'; } },
  'cross/v2-part-stair-on-another-floor.json': { v2: true, path: `/parts/${iTread}/stair`, viewer: 'throws', fault: `parts[${iTread}] (a tread of S1, which rises from L1) is on L2`, make: m => { m.parts[iTread].floor = 'L2'; } },
  'cross/v2-tread-without-stair.json': { v2: true, path: `/parts/${iLanding}`, viewer: 'throws', fault: `parts[${iLanding}] (a landing) names no stairway (a missing property is reported at its parent object)`, make: m => { delete m.parts[iLanding].stair; } },
  'cross/v2-duplicate-space-id.json': { v2: true, path: '/spaces/1/id', viewer: 'throws', fault: 'spaces[1] repeats the id of spaces[0] (the later occurrence is reported)', make: m => { m.spaces[1].id = m.spaces[0].id; } },
  'cross/v2-space-unknown-floor.json': { v2: true, path: '/spaces/1/floor', viewer: 'throws', fault: 'spaces[1] is on floor "L9", which the model does not have', make: m => { m.spaces[1].floor = 'L9'; } },
  'cross/v2-room-unknown-space.json': { v2: true, path: `/rooms/${iRoom}/space`, viewer: 'throws', fault: `rooms[${iRoom}].space names no space`, make: m => { m.rooms[iRoom].space = 'no-such-space'; } },
  'cross/v2-room-space-on-another-floor.json': { v2: true, path: `/rooms/${iRoom}/space`, viewer: 'throws', fault: `rooms[${iRoom}] (a name on L1) names a space of L2`, make: m => { m.rooms[iRoom].space = 'L2-R1'; } },
};

const outDir = path.join(APP, 'fixtures', 'models', 'broken');
rmSync(outDir, { recursive: true, force: true });
const expected = {
  rule: 'Every checker must reject each file with an issue at `path` (JSON Pointer; it may report more): parseBuiltModel '
    + '(viewer: "throws" = ModelError; "warns" = console.warn and the furniture leniency of DESIGN.md 5.6), ajv (schema cases) '
    + 'and walkthrough_api.builtmodel.validate (the API rejects every file, the furniture cases included). A missing property '
    + 'is reported at its parent object (as ajv and jsonschema do); a duplicate at its later occurrence.',
  base: BASE,
  v2Base: 'the same model with stairways [S1: L1 to L2], a tread and a landing of S1 (the last two parts), spaces [L1-R1, L2-R1] and '
    + 'the first drawn name of L1 in L1-R1 (the v2-* cases; docs/rooms/DESIGN.md R-12.1)',
  madeBy: 'node tools/make-broken-fixtures.mjs',
  cases: {},
};
let bad = 0;
for (const [file, c] of Object.entries(cases)) {
  const m = c.v2 ? v2() : clone();
  c.make(m);
  const okSchema = validate(m);
  const schemaPaths = okSchema ? [] : [...new Set(validate.errors.map(e => e.instancePath || '/'))];
  const cross = okSchema ? crossIssues(m) : [];
  const isSchema = file.startsWith('schema/');
  const good = isSchema ? schemaPaths.length === 1 && schemaPaths[0] === c.path : okSchema && cross.length === 1 && cross[0] === c.path;
  console.log(`${good ? 'ok  ' : 'BAD '} ${file}: ${c.path}  (schema: ${schemaPaths.join(', ') || 'valid'}; cross: ${cross.join(', ') || '-'})`);
  if (!good) { bad++; continue; }
  mkdirSync(path.dirname(path.join(outDir, file)), { recursive: true });
  writeFileSync(path.join(outDir, file), JSON.stringify(m) + '\n');
  expected.cases[file] = { path: c.path, kind: isSchema ? 'schema' : 'cross', viewer: c.viewer, fault: c.fault };
}
if (crossIssues(clone()).length || !validate(clone())) { console.error('the base model itself is not clean'); bad++; }
if (crossIssues(v2()).length || !validate(v2())) { console.error('the v2 base model itself is not clean'); bad++; }
if (bad) { console.error(`${bad} case(s) wrong; expected.json not written`); process.exit(1); }
writeFileSync(path.join(outDir, 'expected.json'), JSON.stringify(expected, null, 2) + '\n');
console.log(`wrote ${Object.keys(expected.cases).length} cases and broken/expected.json`);
