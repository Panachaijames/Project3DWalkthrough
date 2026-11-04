// The tables of RESULTS.md, made from the measured JSON files so that the numbers in the write-up are the measured ones:
//   node results_tables.mjs                 prints every table (Markdown)
//   node results_tables.mjs --fill RESULTS.md   puts each table between its markers <!-- table:NAME --> and <!-- /table:NAME -->
// Reads measure_results_intel.json, measure_results_nvidia.json (and the Orbit repeats measure_results_<chip>_orbit_repeat.json
// when they are there), projection.json, slim/slim_report.json, placements.json.
import { existsSync, readFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const json = p => JSON.parse(readFileSync(path.join(HERE, p), 'utf8'));
const load = f => existsSync(path.join(HERE, f)) ? json(f) : null;
const R = { intel: load('measure_results_intel.json'), nvidia: load('measure_results_nvidia.json') };
const REP = { intel: load('measure_results_intel_orbit_repeat.json'), nvidia: load('measure_results_nvidia_orbit_repeat.json') };
const slim = json('slim/slim_report.json');
const num = n => n === null || n === undefined ? '' : Math.round(n).toLocaleString('en-US');
const ms = r => r ? `${r.ms.toFixed(1)} ms / ${Math.round(r.fps)} fps` : '';
const mb = b => (b / 1048576).toFixed(b >= 10485760 ? 1 : 2) + ' MB';
const LABEL = { A: 'A boxes', B: 'B full, copies', C20000: 'C 20,000', C10000: 'C 10,000', C5000: 'C 5,000', C2500: 'C 2,500', D: 'D level of detail', E: 'E chair01 at 10,000',
  Pfull: 'P all 185, full', P20000: 'P all 185, 20,000', P10000: 'P all 185, 10,000', P5000: 'P all 185, 5,000', P2500: 'P all 185, 2,500' };
const VIEW = { orbit: 'Orbit, both levels', walkL1: 'Walk, L1 busiest', walkL2: 'Walk, L2 busiest', widestL1: 'Walk, L1 widest', widestL2: 'Walk, L2 widest' };
const sections = {};
const first = R.intel || R.nvidia;
const find = (r, v, c) => r ? r.results.find(x => x.view === v && x.config === c && x.ms) : null;

// ---------------------------------------------------------------- frames
function frames(views) {
  const t = ['| View | Way | Models\' triangles | Triangles drawn | Draw calls | Intel Iris Xe | NVIDIA MX570 A | CPU % (Intel / NVIDIA) |', '|---|---|---:|---:|---:|---:|---:|---:|'];
  for (const v of views) {
    const configs = [...new Set(first.results.filter(r => r.view === v && r.ms).map(r => r.config))];
    configs.forEach((c, i) => {
      const ri = find(R.intel, v, c), rn = find(R.nvidia, v, c), base = ri || rn;
      const near = base.nearFull ? ` (${base.nearFull} full)` : '';
      t.push(`| ${i ? '' : VIEW[v] || v} | ${LABEL[c] || c}${near} | ${num(c === 'A' ? 0 : base.modelTriangles)} | ${num(base.triangles)} | ${num(base.calls)} | ${ms(ri)} | ${ms(rn)} | ${ri ? ri.cpuLoad : ''} / ${rn ? rn.cpuLoad : ''} |`);
    });
  }
  return t.join('\n');
}
if (first) {
  sections.frames = frames(['orbit', 'walkL1', 'walkL2']);
  sections.framesWidest = frames(['widestL1', 'widestL2'].filter(v => first.results.some(r => r.view === v)));
  // ---------------------------------------------------------------- Orbit repeated
  if (REP.intel || REP.nvidia) {
    const t = ['| Way | Intel, first run | Intel, again | NVIDIA, first run | NVIDIA, again | CPU % again (Intel / NVIDIA) |', '|---|---:|---:|---:|---:|---:|'];
    for (const c of [...new Set(first.results.filter(r => r.view === 'orbit' && r.ms).map(r => r.config))]) {
      const a = find(R.intel, 'orbit', c), b = find(REP.intel, 'orbit', c), x = find(R.nvidia, 'orbit', c), y = find(REP.nvidia, 'orbit', c);
      t.push(`| ${LABEL[c] || c} | ${a ? a.ms.toFixed(1) + ' ms' : ''} | ${b ? b.ms.toFixed(1) + ' ms' : ''} | ${x ? x.ms.toFixed(1) + ' ms' : ''} | ${y ? y.ms.toFixed(1) + ' ms' : ''} | ${b ? b.cpuLoad : ''} / ${y ? y.cpuLoad : ''} |`);
    }
    const cpu = r => r ? `${r.cpu.beforeEdge} % before Edge, ${r.cpu.meanDuringRun} % on average (${r.cpu.min} - ${r.cpu.max} %)` : 'not run';
    t.push('', `CPU during the repeats: Intel ${cpu(REP.intel)}; NVIDIA ${cpu(REP.nvidia)}.`);
    sections.repeat = t.join('\n');
  }
  // ---------------------------------------------------------------- memory
  {
    const t = ['| Way | Model geometries on the chip | Their vertex and index buffers | renderer.info.memory (the whole page) |', '|---|---:|---:|---:|'];
    for (const c of [...new Set(first.results.filter(r => r.view === 'orbit' && r.ms).map(r => r.config))]) {
      const r = find(first, 'orbit', c);
      t.push(`| ${LABEL[c] || c} | ${r.memory.models.geometries} | ${mb(r.memory.models.bytes)} | ${r.memory.info.geometries} geometries, ${r.memory.info.textures} textures |`);
    }
    sections.memory = t.join('\n');
  }
  // ---------------------------------------------------------------- loads
  {
    const t = ['| Opened in | Intel: bank\'s first frame | Intel: first frame with the models | decode (base64 + GLB parse) | build copies | upload | first frame | NVIDIA: bank\'s first frame | NVIDIA: first frame with the models | decode | upload |',
      '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|'];
    const s = v => v === undefined || v === null ? '' : (v / 1000).toFixed(2) + ' s';
    for (const l of R.intel.loads) {
      const n = R.nvidia ? R.nvidia.loads.find(x => x.config === l.config) : null;
      if (l.config === 'bank page as it is') { t.push(`| bank_3d_preview.html as it is | ${s(l.firstFrame)} | | | | | | ${n ? s(n.firstFrame) : ''} | | | |`); continue; }
      t.push(`| ${LABEL[l.config] || l.config} | ${s(l.bankFirstFrame)} | ${s(l.firstFrameWithModels)} | ${num(l.decodeMs)} ms (${num(l.base64Ms)} + ${num(l.parseMs)}) | ${num(l.buildMs)} ms | ${num(l.uploadMs)} ms | ${num(l.firstFrameMs)} ms | ${n ? s(n.bankFirstFrame) : ''} | ${n ? s(n.firstFrameWithModels) : ''} | ${n ? num(n.decodeMs) + ' ms' : ''} | ${n ? num(n.uploadMs) + ' ms' : ''} |`);
    }
    sections.load = t.join('\n');
  }
  // ---------------------------------------------------------------- walking through
  {
    const t = ['| Level, line | Way | Intel: median | 95 % | worst | over 16.7 / 33 ms | NVIDIA: median | 95 % | worst | over 16.7 / 33 ms | Switches (Intel / NVIDIA) |', '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|'];
    for (const w of R.intel.walks) {
      const o = R.nvidia ? R.nvidia.walks.find(x => x.level === w.level && x.config === w.config) : null;
      const line = `${w.level}: ${w.path.metres} m from (${w.path.from.join(', ')}) to (${w.path.to.join(', ')})`;
      t.push(`| ${w.config === 'B' ? line : ''} | ${LABEL[w.config]} | ${w.medianMs.toFixed(1)} ms | ${w.p95Ms.toFixed(1)} ms | ${w.maxMs.toFixed(1)} ms | ${w.over16} / ${w.over33} | ${o ? o.medianMs.toFixed(1) + ' ms' : ''} | ${o ? o.p95Ms.toFixed(1) + ' ms' : ''} | ${o ? o.maxMs.toFixed(1) + ' ms' : ''} | ${o ? `${o.over16} / ${o.over33}` : ''} | ${w.levelSwitches}${o ? ' / ' + o.levelSwitches : ''} |`);
    }
    sections.walk = t.join('\n');
  }
}
// ---------------------------------------------------------------- slimmed models
{
  const t = ['| Model | Pieces | Full | 20,000 | 10,000 | 5,000 | 2,500 | GLB full | at 10,000 | at 5,000 |', '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|'];
  const pl = json('placements.json');
  for (const [n, m] of Object.entries(slim.models)) {
    const cell = b => m.budgets[b].kept ? 'as it is' : `${num(m.budgets[b].triangles)} (${m.budgets[b].share} %)`;
    const size = b => m.budgets[b].kept ? mb(m.bytes) : mb(m.budgets[b].bytes);
    t.push(`| ${n === 'Chair' ? 'Chair.glb (chair test; projection only)' : n} | ${pl.models[n] ? pl.models[n].piecesFurnished : ''} | ${num(m.triangles)} | ${cell(20000)} | ${cell(10000)} | ${cell(5000)} | ${cell(2500)} | ${mb(m.bytes)} | ${size(10000)} | ${size(5000)} |`);
  }
  sections.slim = t.join('\n');
}
// ---------------------------------------------------------------- projection
if (existsSync(path.join(HERE, 'projection.json'))) {
  const P = json('projection.json');
  const chips = Object.keys(P.chips);
  const mviews = chips.length ? Object.keys(P.chips[chips[0]].measuredP) : [];
  const t = [];
  for (const [key, c] of Object.entries(P.cases)) {
    const measured = key === 'standIns';
    t.push(`**${c.what}** (${c.copies} model copies${c.boxes ? `, ${c.boxes} boxes` : ''})`, '');
    if (measured) {
      const cols = mviews.map(v => VIEW[v] || v);
      t.push(`| Detail | Models' triangles | Draw calls | ${cols.map(v => `${v}: Intel / NVIDIA`).join(' | ')} | Intel, fitted plane |`);
      t.push(`|---|---:|---:|${cols.map(() => '---:').join('|')}|---:|`);
    } else {
      t.push(`| Detail | Models' triangles | Draw calls | Intel, fitted plane |`, '|---|---:|---:|---:|');
    }
    for (const b of ['full', '20000', '10000', '5000', '2500']) {
      const r = c.budgets[b];
      const meas = measured ? mviews.map(v => chips.map(t2 => { const m = P.chips[t2].measuredP[v] && P.chips[t2].measuredP[v][b]; return m ? m.ms.toFixed(1) : '-'; }).join(' / ') + ' ms') : [];
      t.push(`| ${b === 'full' ? 'full' : num(Number(b))} | ${num(r.modelTriangles)} | ${num(r.sceneDrawCalls)} | ${measured ? meas.join(' | ') + ' | ' : ''}${r.intelMs} ms |`);
    }
    t.push('');
  }
  for (const c of chips) {
    const f = P.chips[c].fit;
    t.push(`- ${c}: ms = ${f.a} + ${f.bPerMillionTriangles} x (million triangles drawn) + ${f.cPerHundredCalls} x (hundred draw calls); R² ${f.r2}, worst miss ${f.worstMiss_ms} ms, from the ${f.points.length} Orbit Measures${f.a < 0 ? '. Not used: a frame cannot take less than nothing, so the noise of this run (CPU 50 - 90 % busy) is in the plane' : ''}.`);
  }
  sections.projection = t.join('\n');
}

// ---------------------------------------------------------------- out
const i = process.argv.indexOf('--fill');
if (i > 0) {
  const file = path.resolve(process.argv[i + 1]);
  let text = readFileSync(file, 'utf8');
  for (const [name, body] of Object.entries(sections)) {
    const re = new RegExp(`<!-- table:${name} -->[\\s\\S]*?<!-- /table:${name} -->`);
    if (re.test(text)) text = text.replace(re, () => `<!-- table:${name} -->\n${body}\n<!-- /table:${name} -->`);
  }
  writeFileSync(file, text);
  console.log('filled', Object.keys(sections).filter(n => text.includes(`<!-- table:${n} -->`)).join(', '));
} else {
  for (const [name, body] of Object.entries(sections)) console.log(`\n<!-- ${name} -->\n${body}`);
}
