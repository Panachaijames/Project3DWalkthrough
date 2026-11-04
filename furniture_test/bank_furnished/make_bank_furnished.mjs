// Builds bank_furnished.html (run from anywhere, after make_placements.mjs, find_walk_spots.py and slim_models.mjs):
//   node make_bank_furnished.mjs
// A copy of ../../bank_test/bank_3d_preview.html (read only, unchanged) with its title changed and, before </body>, the models
// as base64 text blocks (<script type="application/octet-stream">: never run, decoded by the page when a way first needs them)
// and one module script (bank_furnished_module.js with its data). three still comes from the CDN through the page's own import
// map. Everything else is the bank page byte for byte. Embedded: the 8 GLBs of banquet/ as they came, Chair.glb (the chair test's
// chair, for mode P), and the slimmed GLBs of slim/.
import { readFileSync, writeFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { gzipSync } from 'node:zlib';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const PROJECT = path.resolve(HERE, '..', '..');
const THREE_DIR = path.join(PROJECT, 'app', 'node_modules', 'three');
const imp = rel => import(pathToFileURL(path.join(THREE_DIR, rel)).href);
const THREE = await imp('build/three.module.js');
const { GLTFLoader } = await imp('examples/jsm/loaders/GLTFLoader.js');
const read = p => readFileSync(p, 'utf8');
const json = p => JSON.parse(read(p));
const BANK = path.join(PROJECT, 'bank_test', 'bank_3d_preview.html');
const bank = read(BANK);
const pl = json(path.join(HERE, 'placements.json'));
const slim = json(path.join(HERE, 'slim', 'slim_report.json'));
const spots = json(path.join(HERE, 'walk_spots.json'));
const analysis = json(path.join(HERE, 'analysis.json'));
const model = json(path.join(PROJECT, 'bank_test', 'src', 'bank_model.json'));
const LEVEL = Object.fromEntries(model.floors.map(f => [f.key, f.level]));

// base_mm by column name
function parseRow(s) { const out = []; let cur = '', q = false; for (let i = 0; i < s.length; i++) { const c = s[i]; if (q) { if (c === '"' && s[i + 1] === '"') { cur += '"'; i++; } else if (c === '"') q = false; else cur += c; } else if (c === '"') q = true; else if (c === ',') { out.push(cur); cur = ''; } else cur += c; } out.push(cur); return out; }
const csv = read(path.join(PROJECT, 'bank_test', 'bank_furniture_list.csv')).replace(/^﻿/, '').split(/\r?\n/).filter(Boolean);
const head = parseRow(csv[0]);
const BASE = {};
for (const line of csv.slice(1)) { const r = parseRow(line); BASE[r[0]] = Number(r[head.indexOf('base_mm')]) / 1000; }

// ---------------------------------------------------------------- colours: one neutral material per part (calm greys and warm tones)
const C = {
  charcoal: '#4b4f54', graphite: '#3c4046', midGrey: '#8e9297', lightGrey: '#c9cbcc', warmGrey: '#b3aa9e', linen: '#ddd3c3',
  sand: '#cdb795', oak: '#c4a072', walnut: '#8a6a4f', taupe: '#a39383', offWhite: '#e9e5dd', screen: '#1f2429', warmLight: '#cdc5b8',
};
const sw = (name, rough) => ({ name: name.replace(/([A-Z])/g, ' $1').toLowerCase(), hex: C[name], ...(rough ? { rough } : {}) });
const COLOURS = {
  banquet: [sw('charcoal'), sw('linen'), sw('walnut')],                                         // plinth, two cushions, frame
  monitor: [sw('graphite'), sw('midGrey'), sw('screen', 0.35), sw('lightGrey'), sw('midGrey'), sw('offWhite'), sw('lightGrey'), sw('graphite')],   // screen (3), keyboard (3: keys last), mouse (2)
  'side table': [sw('charcoal'), sw('charcoal'), sw('midGrey'), sw('oak')],                      // two legs, frame, top
  sofa: [sw('warmGrey'), sw('charcoal')],                                                       // bench and back, plinth
  stool: [sw('sand'), sw('charcoal')],                                                          // cushion, base
  'visitor chair01': [sw('walnut'), sw('linen'), sw('warmGrey'), sw('charcoal')],               // arm pads, seat cushion, shell, legs
  'visitor chair02': [sw('charcoal'), sw('taupe')],                                             // base, cushion
  'working table': [sw('oak'), sw('lightGrey'), sw('charcoal')],                                // top, modesty panel, frame and legs
  Chair: [sw('warmLight'), sw('warmGrey'), sw('taupe'), sw('midGrey'), sw('linen')],
};

// ---------------------------------------------------------------- Chair.glb at the origin, as the chair test put it (one matrix on the scene)
const chairBuf = readFileSync(path.join(PROJECT, 'Chair.glb'));
const chairGltf = await new GLTFLoader().parseAsync(chairBuf.buffer.slice(chairBuf.byteOffset, chairBuf.byteOffset + chairBuf.byteLength), '');
const roots = chairGltf.scene.children;
const r0 = roots[0];
if (!roots.every(r => r.matrix.elements.every((v, i) => Math.abs(v - r0.matrix.elements[i]) < 1e-5))) throw new Error('Chair.glb: the roots do not share one matrix');
const ex = new THREE.Vector3(1, 0, 0).applyQuaternion(r0.quaternion), yaw = Math.atan2(-ex.z, ex.x);
const N1 = new THREE.Matrix4().makeRotationY(-yaw).multiply(new THREE.Matrix4().makeTranslation(-r0.position.x, -r0.position.y, -r0.position.z));
const g1 = new THREE.Group(); g1.matrixAutoUpdate = false; g1.matrix.copy(N1); g1.add(chairGltf.scene); g1.updateMatrixWorld(true);
const cb = new THREE.Box3().setFromObject(g1, true);
const NC = new THREE.Matrix4().makeTranslation(-(cb.min.x + cb.max.x) / 2, -cb.min.y, -(cb.min.z + cb.max.z) / 2).multiply(N1);
const chairSize = cb.getSize(new THREE.Vector3());
const toRows = m => { const e = m.elements; return [0, 1, 2, 3].map(r => [0, 1, 2, 3].map(c => +e[c * 4 + r].toFixed(7) + 0)); };
const chairParts = []; chairGltf.scene.traverse(o => { if (o.isMesh) chairParts.push({ name: o.name, triangles: o.geometry.index.count / 3 }); });

// ---------------------------------------------------------------- the assets
const assets = {}, blocks = [];
let n = 0;
function asset(key, file, info) {
  const buf = readFileSync(file);
  const el = `bf-a${n++}`;
  assets[key] = { el, file: path.relative(PROJECT, file).replace(/\\/g, '/'), bytes: buf.length, gzipBytes: gzipSync(buf).length, sha1: createHash('sha1').update(buf).digest('hex').slice(0, 12), ...info };
  blocks.push(`<script type="application/octet-stream" id="${el}" data-asset="${key}">${buf.toString('base64')}</script>`);
}
const models = {};
for (const [name, m] of Object.entries(pl.models)) {
  const s = slim.models[name];
  asset(`${name}@full`, path.join(PROJECT, m.file), { model: name, budget: 'full', triangles: m.triangles, vertices: m.vertices });
  for (const [b, e] of Object.entries(s.budgets)) if (!e.kept) asset(`${name}@${b}`, path.join(HERE, e.file), { model: name, budget: Number(b), triangles: e.triangles, vertices: e.vertices });
  models[name] = { family: m.family, kind: m.kind, triangles: m.triangles, parts: m.parts.map(p => ({ name: p.name, triangles: p.triangles })), colours: COLOURS[name],
    normalise: m.normalise, centre: m.centreNormalised, suggested: m.suggested, piecesFurnished: m.piecesFurnished,
    pieces: m.pieces.map(p => ({ key: p.key, ids: p.ids, floor: p.floor, level: p.level, base: p.base, place: p.place })) };
}
{
  const s = slim.models.Chair;
  asset('Chair@full', path.join(PROJECT, 'Chair.glb'), { model: 'Chair', budget: 'full', triangles: s.triangles, vertices: s.vertices });
  for (const [b, e] of Object.entries(s.budgets)) if (!e.kept) asset(`Chair@${b}`, path.join(HERE, e.file), { model: 'Chair', budget: Number(b), triangles: e.triangles, vertices: e.vertices });
  models.Chair = { family: "the chair test's chair (Chair.glb)", kind: 'seat', triangles: s.triangles, parts: chairParts, colours: COLOURS.Chair, standInOnly: true,
    normalise: toRows(NC), centre: [0, +(chairSize.y / 2).toFixed(4), 0], size: chairSize.toArray().map(v => +v.toFixed(4)) };
}
for (const [name, m] of Object.entries(models)) if (m.colours.length !== m.parts.length) throw new Error(`${name}: ${m.colours.length} colours for ${m.parts.length} parts`);

// ---------------------------------------------------------------- mode P: a stand-in for every piece without a model
const furnished = new Set(Object.values(pl.models).flatMap(m => m.pieces.flatMap(p => p.ids)));
const KIND_MODEL = { seat: 'Chair', table: 'working table', 'coffee-table': 'side table', sofa: 'banquet', computer: 'monitor' };
const NO_MODEL = 'banquet';                    // 4,720 triangles: the median of the nine models (the 8 and Chair.glb)
const nine = Object.values(models).map(m => m.triangles).sort((a, b) => a - b);
if (nine[4] !== models[NO_MODEL].triangles) throw new Error('the median model is not the banquet any more');
const standIns = model.furniture.filter(d => !furnished.has(d.id)).map(d => ({ id: d.id, floor: d.floor, kind: d.kind, model: KIND_MODEL[d.kind] || NO_MODEL,
  level: LEVEL[d.floor], base: BASE[d.id], x: d.x, y: d.y, rot: d.rot }));

const DATA = {
  made: new Date().toISOString(), three: slim.three, budgets: slim.budgets, lodDistance: 3, lodBudget: 5000, eBudget: 10000, eModel: 'visitor chair01',
  exportMaterials: Object.values(analysis.models).reduce((a, m) => a + m.materials.length, 0),
  assets, models, standIns, walk: spots.levels,
};

// ---------------------------------------------------------------- the page
const TITLE = '<title>Bank branch test</title>';
if (!bank.includes(TITLE) || bank.lastIndexOf('</body>') < 0) throw new Error('the bank page is not the one this was written for (title or </body> not found)');
const eol = bank.includes('\r\n') ? '\r\n' : '\n';
const lines = s => s.replace(/\r?\n/g, eol);
const module = read(path.join(HERE, 'bank_furnished_module.js')).replace('__BF_DATA__', () => JSON.stringify(DATA));
const added = lines(`<!-- ===== Furniture test with the bank's own models (added by furniture_test/bank_furnished/make_bank_furnished.mjs; everything above is the bank page as it is) ===== -->\n`)
  + blocks.join(eol) + eol + lines(`<script type="module">\n${module}</script>\n`);
const at = bank.lastIndexOf('</body>');
const page = bank.slice(0, at).replace(TITLE, '<title>Furniture test (bank models)</title>') + added + bank.slice(at);
writeFileSync(path.join(HERE, 'bank_furnished.html'), page);
const kb = s => Math.round(Buffer.byteLength(s) / 1024);
console.log(`bank_furnished.html ${kb(page)} KB (bank page ${kb(bank)} KB, sha1 ${createHash('sha1').update(bank).digest('hex').slice(0, 12)}); ${n} assets, ${Math.round(Object.values(assets).reduce((a, x) => a + x.bytes, 0) / 1024)} KB of GLB; ${standIns.length} stand-ins; chair ${chairSize.toArray().map(v => v.toFixed(3)).join(' x ')} m`);
