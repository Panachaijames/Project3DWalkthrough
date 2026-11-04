// The projection: if all 185 pieces of the bank had models of the same kind of detail as these, how many triangles would the
// scene have, and how long would a frame take, at full detail and at each budget?   node projection.mjs   (after the timings)
// Every piece gets a model: the 65 pieces of the 8 families their own (62 copies; the banquet once for its run), the other seats
// the chair test's chair (Chair.glb, 41,921 triangles), the other tables, coffee tables and sofas their kind's model (working
// table, side table, banquet), and the kinds with no model at all (ATMs, printers, phones, TVs, screens, plants, sanitary
// fittings, cabinets) the banquet's 4,720 triangles, the median of the nine models; as a second case those stay boxes. This is
// mode P of the page, which was also measured. A model under a budget is kept as it is; slimmed triangles are the real ones
// (slim/slim_report.json).
// Frame time: a plane ms = a + b x (million triangles drawn) + c x (hundred draw calls), fitted per chip by least squares to all
// the Orbit Measures (modes A - E and P, measure_results_<chip>.json), read at each case's triangles and draw calls; for the first
// case mode P's own Measures (Orbit and the widest Walk views) are given beside it.
// Writes projection.json here.
import { existsSync, readFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const PROJECT = path.resolve(HERE, '..', '..');
const json = p => JSON.parse(readFileSync(p, 'utf8'));
const pl = json(path.join(HERE, 'placements.json'));
const slim = json(path.join(HERE, 'slim', 'slim_report.json'));
const bank = json(path.join(PROJECT, 'bank_test', 'src', 'bank_model.json'));
const BUDGETS = ['full', ...slim.budgets];
const KIND_MODEL = { seat: 'Chair', table: 'working table', 'coffee-table': 'side table', sofa: 'banquet', computer: 'monitor' };
const NO_MODEL = 'banquet';
const tris = (model, b) => { const m = slim.models[model]; if (b === 'full' || m.triangles <= b) return m.triangles; return m.budgets[b].triangles; };
const parts = model => slim.models[model].parts.length;

const furnished = new Set(Object.values(pl.models).flatMap(m => m.pieces.flatMap(p => p.ids)));
const copies = [];
for (const [name, m] of Object.entries(pl.models)) for (const p of m.pieces) copies.push({ model: name, kind: m.kind, own: true, key: p.key });
for (const d of bank.furniture) if (!furnished.has(d.id)) copies.push({ model: KIND_MODEL[d.kind] || NO_MODEL, kind: d.kind, own: false, key: d.id, noModelKind: !KIND_MODEL[d.kind] });

const sum = (list, f) => list.reduce((a, c) => a + f(c), 0);
const byModel = {};
for (const c of copies) { const k = c.own ? c.model : `${c.model} (stand-in${c.noModelKind ? ', no model of its kind' : ''})`; byModel[k] = (byModel[k] || 0) + 1; }
const cases = {
  standIns: { what: 'every piece a model (kinds with no model at the banquet\'s 4,720 triangles)', list: copies, boxes: 0 },
  kindsWithoutModelAsBoxes: { what: 'kinds with no model of their own stay boxes', list: copies.filter(c => !c.noModelKind), boxes: copies.filter(c => c.noModelKind).length },
  only65: { what: 'only the 65 pieces of the 8 families (as the page\'s modes B - E)', list: copies.filter(c => c.own), boxes: 185 - 65 },
};

// the measured Orbit rows: the scene without furniture, and the line through the Measures
const chips = {};
for (const tag of ['intel', 'nvidia']) {
  const f = path.join(HERE, `measure_results_${tag}.json`);
  if (!existsSync(f)) continue;
  const R = json(f);
  const orbit = R.results.filter(r => r.view === 'orbit' && r.ms);
  const A = orbit.find(r => r.config === 'A');
  // least squares for ms = a + b x Mtri + c x hundred calls (normal equations, 3 x 3)
  const X = orbit.map(r => [1, r.triangles / 1e6, r.calls / 100]), y = orbit.map(r => r.ms);
  const XtX = [0, 1, 2].map(i => [0, 1, 2].map(j => sum(X, x => x[i] * x[j]))), Xty = [0, 1, 2].map(i => X.reduce((s, x, k) => s + x[i] * y[k], 0));
  const solve = (M, v) => { const m = M.map((row, i) => [...row, v[i]]); for (let i = 0; i < 3; i++) { let p = i; for (let k = i + 1; k < 3; k++) if (Math.abs(m[k][i]) > Math.abs(m[p][i])) p = k; [m[i], m[p]] = [m[p], m[i]]; for (let k = 0; k < 3; k++) if (k !== i) { const f = m[k][i] / m[i][i]; for (let j = i; j < 4; j++) m[k][j] -= f * m[i][j]; } } return m.map((row, i) => row[3] / row[i]); };
  const [a, b, c] = solve(XtX, Xty), my = y.reduce((s, v) => s + v, 0) / y.length;
  const fitted = X.map(x => a + b * x[1] + c * x[2]);
  const r2 = 1 - y.reduce((s, v, k) => s + (v - fitted[k]) ** 2, 0) / y.reduce((s, v) => s + (v - my) ** 2, 0);
  const worst = Math.max(...y.map((v, k) => Math.abs(v - fitted[k])));
  const views = [...new Set(R.results.filter(r => r.mode === 'P' && r.ms).map(r => r.view))];
  chips[tag] = { gpu: R.gpu, sceneWithoutFurniture: A ? A.triangles - 185 * 12 : null, wallCalls: A ? A.calls - 185 * 2 : null,
    fit: { a: +a.toFixed(3), bPerMillionTriangles: +b.toFixed(3), cPerHundredCalls: +c.toFixed(3), r2: +r2.toFixed(3), worstMiss_ms: +worst.toFixed(2), points: orbit.map(r => [r.config, r.triangles, r.calls, r.ms]) },
    measuredP: Object.fromEntries(views.map(v => [v, Object.fromEntries(R.results.filter(r => r.view === v && r.mode === 'P' && r.ms).map(r => [String(r.budget), { triangles: r.triangles, calls: r.calls, ms: r.ms }]))])) };
}
const base = Object.values(chips)[0]?.sceneWithoutFurniture ?? null;
const out = { made: new Date().toISOString(), assignment: byModel, cases: {}, chips };
for (const [key, c] of Object.entries(cases)) {
  out.cases[key] = { what: c.what, copies: c.list.length, boxes: c.boxes, budgets: {} };
  for (const B of BUDGETS) {
    const models = sum(c.list, x => tris(x.model, B)), calls = sum(c.list, x => parts(x.model)) + 2 * c.boxes;
    const walls = Object.values(chips)[0]?.wallCalls ?? 0;
    const row = { modelTriangles: models, boxTriangles: 12 * c.boxes, sceneTriangles: base === null ? null : base + models + 12 * c.boxes, modelDrawCalls: calls, sceneDrawCalls: calls + walls };
    for (const [tag, ch] of Object.entries(chips)) row[`${tag}Ms`] = row.sceneTriangles === null ? null : +(ch.fit.a + ch.fit.bPerMillionTriangles * row.sceneTriangles / 1e6 + ch.fit.cPerHundredCalls * row.sceneDrawCalls / 100).toFixed(1);
    out.cases[key].budgets[B] = row;
  }
}
writeFileSync(path.join(HERE, 'projection.json'), JSON.stringify(out, null, 1));
console.log(JSON.stringify(byModel));
for (const [key, c] of Object.entries(out.cases)) {
  console.log(`\n${c.what}: ${c.copies} copies, ${c.boxes} boxes`);
  console.table(Object.fromEntries(['full', '20000', '10000', '5000', '2500'].map(b => [b, c.budgets[b]])));
}
for (const [tag, ch] of Object.entries(chips)) console.log(tag, JSON.stringify(ch.fit), 'measured P', JSON.stringify(ch.measuredP));
