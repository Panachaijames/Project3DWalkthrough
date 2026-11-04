#!/usr/bin/env node
// Provisional Presentation v1 fixtures (DESIGN.md 8, 17.1; WORK_BREAKDOWN S.8). Scaffold tool:
//   node tools/make-presentation-fixtures.mjs
// fixtures/presentation/<projectId>[-v<n>].json from the captured facts (fixtures/prototype/*.json: title, heading, intro
// HTML split into runs, legend items and layout, floor buttons, tick labels, accent) plus DESIGN.md 8's fixed values
// (camera, creaseAngle, partStyles, groundPlane, toggles). Optional fields are written where D-8's table gives a value;
// a "default" cell is left out (floorButtons.labels only for buttons whose text differs from the model's floor name; tick
// labels only where they differ from the defaults). Builder E's seed/presentation.py output is compared with these.
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import path from 'node:path';
import { APP } from './lib.mjs';

const DEFAULT_LABELS = {
  plates: 'Floor plates', glass: 'Glass', rooms: 'Room names', single: 'Single-line items', picture: 'Plan picture',
  pictureTitle: "Each floor's source picture, laid on its floor plate at the model's scale and position",
};
const HOUSE_STYLES = {
  glass: { color: '#8fd0e0', edge: '#4f9fb3', opacity: 0.35, roughness: 0.85, edgeOpacity: 0.6, renderOrder: 0 },
  pane: { color: '#7fb8e8', edge: '#3f7fb3', opacity: 0.35, roughness: 0.85, edgeOpacity: 0.6, renderOrder: 0 },
  single: { opacity: 0.9 },
};
const FIXED = {
  'bank-sampeng-v1': { model: 'bank-v1', camera: { kind: 'fixed', position: [24, 27, 29], target: [0, 2.5, 0], far: 600 }, creaseAngle: 25, groundPlane: null },
  'bank-sampeng-v2': { model: 'bank-v2', camera: { kind: 'fixed', position: [24, 27, 29], target: [0, 2.5, 0], far: 600 }, creaseAngle: 25, groundPlane: null },
  'presidential-suite': { model: 'suite', camera: { kind: 'fixed', position: [-26, 32, 30], target: [0, 1.2, 0], far: 600 }, creaseAngle: 25, groundPlane: null },
  'sukhumvit-house': { model: 'house', camera: { kind: 'fixed', position: [-28, 30, 34], target: [0, 3, 0], far: 500 }, creaseAngle: 40,
    partStyles: HOUSE_STYLES, groundPlane: { size: [80, 50], colour: '#dfe3e0' } },
  'hotel-lobby': { model: 'hotel', camera: { kind: 'fitSlabs', away: [21.6, 22.05, 26.1], targetY: 2.5, panForPanel: true, far: 600 }, creaseAngle: 25, groundPlane: null },
};

/** The intro HTML (only <b>...</b>, no entities: checked) as text runs. */
function runs(html) {
  const out = [];
  const re = /<b>([\s\S]*?)<\/b>/g;
  let at = 0, m;
  while ((m = re.exec(html))) {
    if (m.index > at) out.push({ text: html.slice(at, m.index) });
    out.push({ text: m[1], bold: true });
    at = m.index + m[0].length;
  }
  if (at < html.length) out.push({ text: html.slice(at) });
  for (const r of out) {
    if (/[<>&]/.test(r.text)) throw new Error(`intro has markup other than <b> or an entity: ${r.text.slice(0, 80)}`);
  }
  return out;
}

const outDir = path.join(APP, 'fixtures', 'presentation');
mkdirSync(outDir, { recursive: true });
for (const [id, fixed] of Object.entries(FIXED)) {
  const facts = JSON.parse(readFileSync(path.join(APP, 'fixtures', 'prototype', `${id}.json`), 'utf8'));
  const model = JSON.parse(readFileSync(path.join(APP, 'fixtures', 'models', `${fixed.model}.model.json`), 'utf8'));
  const p = {
    documentTitle: facts.title,
    heading: facts.heading,
    intro: runs(facts.intro.html),
    accent: facts.accent,
    legend: { layout: facts.legend.layout, items: facts.legend.items },
  };
  if (facts.floorButtons.length) {
    const all = facts.floorButtons.find(b => b.key === 'both');
    const labels = {};
    for (const b of facts.floorButtons) {
      if (b.key === 'both') continue;
      const floor = model.floors.find(f => f.key === b.key);
      if (!floor) throw new Error(`${id}: button ${b.key} names no floor`);
      if (b.text !== floor.name) labels[b.key] = b.text;
    }
    p.floorButtons = Object.keys(labels).length ? { all: all.text, labels } : { all: all.text };
  }
  const labels = {};
  for (const t of facts.ticks) {
    if (t.label !== DEFAULT_LABELS[t.id]) labels[t.id] = t.label;
    if (t.id === 'picture' && t.title && t.title !== DEFAULT_LABELS.pictureTitle) labels.pictureTitle = t.title;
  }
  if (Object.keys(labels).length) p.labels = labels;
  p.camera = fixed.camera;
  if (fixed.partStyles) p.partStyles = fixed.partStyles;
  p.creaseAngle = fixed.creaseAngle;
  p.groundPlane = fixed.groundPlane;
  writeFileSync(path.join(outDir, `${id}.json`), JSON.stringify(p, null, 2) + '\n');
  console.log(`${id}.json: "${p.heading}", ${p.intro.length} intro runs, ${p.legend.items.length} legend items (${p.legend.layout}), `
    + `floorButtons ${JSON.stringify(p.floorButtons ?? null)}, labels ${JSON.stringify(p.labels ?? {})}, camera ${p.camera.kind}`);
}
