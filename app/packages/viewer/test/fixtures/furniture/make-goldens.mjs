// Makes the furniture goldens of this folder ONCE (DESIGN.md 17.2; WORK_BREAKDOWN C). Owner: builder C.
//   node packages/viewer/test/fixtures/furniture/make-goldens.mjs            (from app/; system Python 3.14.3 on PATH)
// 1. Reads the prototype's hand-made model furniture/fixtures/mini_model.json (read-only) and writes the variants of
//    furniture/test_boxes.mjs next to this script, built exactly as that test builds them:
//      mini-original.json  the prototype's file, as it is (not v1: no parts, no photoName; the CSV helpers take it as is)
//      awkward.json        commas and quotes in a family, line breaks in a block and a layer, a note with both, empty family
//                          and handle, x_m of -0.0004, exact ties (12.25 -> 12.2, 0.0625 m -> 63 mm), a kind height of
//                          460.5 mm and a base of 10.5 mm, a kind nobody uses (atm), floors Z1, A2 (not alphabetical), the
//                          pieces in reverse order
//      broken.json         a support that is not there, a floor the model does not have, a kind the model does not list
//      mini-typed-heights.json  the heights test_boxes.mjs types in: table 600, coffee-table 300, seat 480, tv 650
// 2. Runs the prototype's own writer of the contract, furniture/fixtures/expected_csv.py (Python's f-strings and csv module),
//    and with --kit furniture_kit.csv_text (the builders' writer, which needs shapely), read-only: the SYSTEM Python with -B
//    and PYTHONDONTWRITEBYTECODE=1, from a temp folder, so nothing is written into the prototype folder (no __pycache__).
//    Writes the text each prints (UTF-8, no byte-order mark: csv() / furnitureCsv() give the bytes after it):
//      mini.csv, mini.kit.csv, mini-typed.csv, mini-typed.kit.csv, awkward.csv, awkward.kit.csv
//    (broken.json has no golden: Python refuses it; the viewer's leniency is checked by the unit tests themselves.)
// 3. Writes goldens.json: file -> sha1 and size, and the python / kit agreement per model.
import { createHash } from 'node:crypto';
import { spawnSync } from 'node:child_process';
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const APP = path.resolve(HERE, '../../../../..');
const PROTO = path.resolve(APP, '..');
const SOURCE = path.join(PROTO, 'furniture', 'fixtures', 'mini_model.json');
const ORACLE = path.join(PROTO, 'furniture', 'fixtures', 'expected_csv.py');
const TMP = process.env.WT_TMP || path.join(os.tmpdir(), 'wt-c');
mkdirSync(TMP, { recursive: true });

const fx = JSON.parse(readFileSync(SOURCE, 'utf8'));
const write = (name, text) => { writeFileSync(path.join(HERE, name), text); return path.join(HERE, name); };
const variant = (name, edit) => { const m = structuredClone(fx); edit(m); return write(name, JSON.stringify(m, null, 1)); };

// ------------------------------------------------------------------ the variants, as furniture/test_boxes.mjs builds them
const original = write('mini-original.json', readFileSync(SOURCE, 'utf8'));
const awkward = variant('awkward.json', m => {
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
variant('broken.json', m => {                                     // data the builder should never write: left out with a warning, or a fall-back, never a crash
  const seat = m.furniture.find(p => p.id === 'L1-seat-001');
  m.furniture.find(p => p.id === 'L1-computer-001').on = 'L1-no-such-table';                 // a support that is not there: the computer stands on its kind's base
  m.furniture.push({ ...seat, id: 'L9-seat-001', floor: 'L9' });                                // a level the page does not have
  m.furniture.push({ ...seat, id: 'L1-sofa-001', kind: 'sofa' });                              // a kind the model does not list
});
const typedHeights = write('mini-typed-heights.json', JSON.stringify({ table: 600, 'coffee-table': 300, seat: 480, tv: 650 }));

// ------------------------------------------------------------------ the prototype's writers, read-only
function python(modelPath, heightsPath, kit) {
  const args = ['-B', ORACLE, modelPath];
  if (heightsPath) args.push(heightsPath);
  if (kit) args.push('--kit');
  const r = spawnSync('python', args, {
    cwd: TMP, encoding: 'buffer',
    env: { ...process.env, PYTHONIOENCODING: 'utf-8', PYTHONUTF8: '1', PYTHONDONTWRITEBYTECODE: '1' },
  });
  if (r.status !== 0) throw new Error(`expected_csv.py ${args.slice(2).join(' ')} failed: ${r.stderr.toString()}`);
  return r.stdout;
}
const sha1 = b => createHash('sha1').update(b).digest('hex');
const out = { made: new Date().toISOString(), by: 'make-goldens.mjs', source: 'furniture/fixtures/mini_model.json', oracle: 'furniture/fixtures/expected_csv.py', files: {}, agree: {} };
for (const [name, model, heights] of [['mini', original, null], ['mini-typed', original, typedHeights], ['awkward', awkward, null]]) {
  const py = python(model, heights, false), kit = python(model, heights, true);
  writeFileSync(path.join(HERE, `${name}.csv`), py);
  writeFileSync(path.join(HERE, `${name}.kit.csv`), kit);
  out.agree[name] = py.equals(kit);
}
for (const f of ['mini-original.json', 'awkward.json', 'broken.json', 'mini-typed-heights.json', 'mini.csv', 'mini.kit.csv', 'mini-typed.csv',
  'mini-typed.kit.csv', 'awkward.csv', 'awkward.kit.csv']) {
  const b = readFileSync(path.join(HERE, f));
  out.files[f] = { sha1: sha1(b), bytes: b.length };
}
writeFileSync(path.join(HERE, 'goldens.json'), JSON.stringify(out, null, 2) + '\n');
const pyc = path.join(PROTO, 'furniture', '__pycache__'), pyc2 = path.join(PROTO, 'furniture', 'fixtures', '__pycache__');
if (existsSync(pyc) || existsSync(pyc2)) { console.error('a __pycache__ appeared in the prototype furniture folder'); process.exit(1); }
console.log(JSON.stringify(out, null, 2));
