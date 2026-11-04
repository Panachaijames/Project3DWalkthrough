#!/usr/bin/env node
// Facts read from each prototype page in headless Edge (DESIGN.md 17.1; WORK_BREAKDOWN S.7, S.8). Scaffold tool.
//   node tools/capture-prototype-facts.mjs --port 9700        (npm run capture:prototype)
// Writes fixtures/prototype/<projectId>[-v<n>].json for the five prototype pages. Holds the machine-wide Edge lock
// (tools/cdp.mjs). The pages load three.js 0.160 from cdn.jsdelivr.net. Reads only; never writes outside app/ (the
// browser profile and screenshots go to %TEMP%\wt-scaffold).
// How, where a page does not expose a fact (DESIGN.md 17.1): the scene facts are read with ?build=0&nodownload=1 and the
// card facts with the plain address; tick list sizes by toggling each tick and counting the objects under the floor
// groups whose `visible` flips (the plan pictures: __host.pictures.objs); the bank v1 camera from __viewer.probe.camera()
// with target (0, 2.5, 0), near 0.1 and far 600 from its generator; the house's facts from __host.groups, FL, floors,
// rise, plinths, pieces, camera and controls (it exposes no model and has no rooms).
import { createHash } from 'node:crypto';
import { mkdirSync, rmSync, writeFileSync } from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { launch, pageApi, sleep } from './cdp.mjs';
import { APP, PROTOTYPES, parseArgs, requireFreePort } from './lib.mjs';

const args = parseArgs(process.argv.slice(2), { flags: ['port', 'only'] });
const PORT = Number(args.port ?? 9700);
const TMP = path.join(process.env.TEMP || os.tmpdir(), 'wt-scaffold');
const OUT = path.join(APP, 'fixtures', 'prototype');

export const PAGES = [
  { out: 'bank-sampeng-v1', page: 'bank_test/previous_before_fix_round_2026-10-27/bank_3d_preview.html', cameraFromProbe: { target: [0, 2.5, 0], near: 0.1, far: 600 } },
  { out: 'bank-sampeng-v2', page: 'bank_test/bank_3d_preview.html' },
  { out: 'presidential-suite', page: 'presidential_test/presidential_3d_preview.html' },
  { out: 'sukhumvit-house', page: 'cad_test/house_3d_preview.html', house: true },
  { out: 'hotel-lobby', page: 'hotel_test/hotel_3d_preview.html' },
];

// ---------------------------------------------------------------------------------------------- page-side readers
// Each runs in the page (CDP Runtime.evaluate of its source) and returns plain JSON.
function readPanel() {
  const panel = document.getElementById('panel');
  const txt = n => (n ? n.textContent.replace(/\s+/g, ' ').trim() : null);
  const hex = span => { const m = /background(?:-color)?\s*:\s*(#[0-9a-fA-F]{3,8})/.exec(span.getAttribute('style') || ''); return m ? m[1].toLowerCase() : null; };
  const legendEl = panel.querySelector('.legend');
  let legend = null;
  if (legendEl) {
    const lines = [...legendEl.children].every(c => c.tagName === 'DIV');
    const items = [];
    const walkInline = parent => {
      let cur = null;
      for (const node of parent.childNodes) {
        if (node.nodeType === 1 && node.tagName === 'SPAN' && !node.textContent.trim()) { cur = { colour: hex(node), text: '' }; items.push(cur); }
        else if (cur) cur.text += node.textContent;
      }
    };
    if (lines) for (const div of legendEl.children) walkInline(div); else walkInline(legendEl);
    items.forEach(i => { i.text = i.text.replace(/\s+/g, ' ').trim(); });
    legend = { layout: lines ? 'lines' : 'inline', items };
  }
  const order = [...panel.children].map(c => (c.id ? `#${c.id}` : c.classList.length ? `.${[...c.classList].join('.')}` : c.tagName.toLowerCase()));
  const intro = panel.querySelector(':scope > p');
  return {
    title: document.title,
    stamp: document.querySelector('meta[name=model-data]')?.getAttribute('content') ?? null,
    heading: txt(panel.querySelector('h1')),
    intro: intro ? { text: intro.textContent, html: intro.innerHTML } : null,
    floorButtons: [...panel.querySelectorAll('#floors [data-f]')].map(b => ({ key: b.dataset.f, text: txt(b), on: b.classList.contains('on') })),
    // the ticks row is #shows on most pages, a plain .row on the house's: find the ticks by their ids
    ticks: ['plates', 'glass', 'rooms', 'single', 'picture'].map(id => document.getElementById(id)).filter(Boolean)
      .map(i => { const l = i.closest('label'); return { id: i.id, label: txt(l), checked: i.checked, title: l?.getAttribute('title') ?? null }; }),
    legend,
    panelOrder: order,
    accent: getComputedStyle(document.documentElement).getPropertyValue('--accent').trim(),
    hint: txt(document.getElementById('hint')),
    rooms: document.querySelectorAll('.room').length,
  };
}

function readScene(opts) {
  const h = window.__host, out = { floors: [] };
  const vcount = m => (m.geometry && m.geometry.attributes.position ? m.geometry.attributes.position.count : 0);
  const isFurn = o => (o.name || '').startsWith('furn:');
  const FL = h.FL;
  const walkFloors = h.floors;
  for (const wf of walkFloors) {
    const f = FL[wf.key];
    const rise = (f.rise || (h.rise && h.rise[wf.key]) || []).map(r => ({ name: r.mesh ? r.mesh.name : r.name, scales: !!r.scales }));
    const colliders = f.colliders.filter(m => !isFurn(m));
    out.floors.push({
      key: wf.key, name: wf.name, level: f.level, walkLevel: wf.level, stack: wf.stack ?? null,
      colliders: colliders.map(m => ({ name: m.name, vertices: vcount(m), visible: m.visible })),
      colliderVertices: colliders.reduce((s, m) => s + vcount(m), 0),
      furnitureColliders: f.colliders.length - colliders.length,
      walkables: f.walkables.map(m => ({ name: m.name, vertices: vcount(m) })),
      walkableVertices: f.walkables.reduce((s, m) => s + vcount(m), 0),
      late: (f.late || []).length,
      lateWithoutFurniture: (f.late || []).filter(o => !isFurn(o)).length,
      rise,
      labels: (h.labels || []).filter(l => l.floor === wf.key).length,
      groupChildren: f.group.children.length,
    });
  }
  if (h.plinths) out.plinths = h.plinths.map(m => ({ name: m.name, vertices: vcount(m) }));
  // the house's pieces: { floor: { look: { mesh, edges } } }
  if (h.pieces) out.pieces = Object.fromEntries(Object.entries(h.pieces).map(([k, byLook]) => [k, Object.entries(byLook).map(([look, p]) => {
    const m = p && p.mesh ? p.mesh : p;
    return { look, mesh: m && m.name, vertices: m ? vcount(m) : 0 };
  })]));
  if (h.plates) out.plates = Object.fromEntries(Object.entries(h.plates).map(([k, list]) => [k, list.length]));
  const cam = h.camera, ctl = h.controls;
  if (cam && ctl) {
    out.camera = { position: cam.position.toArray(), target: ctl.target.toArray(), fov: cam.fov, near: cam.near, far: cam.far, source: '__host.camera, __host.controls' };
  } else {
    const p = window.__viewer.probe.camera();
    out.camera = { position: [p.x, p.y, p.z], target: opts.cameraFromProbe.target, fov: p.fov, near: opts.cameraFromProbe.near, far: opts.cameraFromProbe.far,
      source: '__viewer.probe.camera() (position, fov); target, near, far from the generator' };
  }
  if (h.model) {
    const m = h.model;
    out.model = { project: m.project, shortName: m.shortName, photoName: m.photoName ?? null, floors: (m.floors || []).map(f => f.key),
      parts: (m.parts || []).length, openings: Array.isArray(m.openings) ? m.openings.length : null, rooms: (m.rooms || []).length };
  }
  out.labels = (h.labels || []).length;
  return out;
}

async function tickSizes() {
  const h = window.__host;
  const frames = n => new Promise(r => { const step = () => (n-- <= 0 ? r() : requestAnimationFrame(step)); requestAnimationFrame(step); });
  const objs = [];
  for (const f of Object.values(h.FL)) f.group.traverse(o => { if (o !== f.group && !(o.name || '').startsWith('furn:')) objs.push(o); });
  const pics = (h.pictures && h.pictures.objs) || [];
  if (h.pictures && h.pictures.ready) await h.pictures.ready;
  const out = {};
  for (const input of ['plates', 'glass', 'rooms', 'single', 'picture'].map(id => document.getElementById(id)).filter(Boolean)) {
    const before = objs.map(o => o.visible), pb = pics.map(o => o.visible), roomsBefore = [...document.querySelectorAll('.room')].map(e => e.style.display);
    input.click(); await frames(2);
    const flipped = objs.filter((o, i) => o.visible !== before[i]);
    const picFlips = pics.filter((o, i) => o.visible !== pb[i]).length;
    const roomFlips = [...document.querySelectorAll('.room')].filter((e, i) => e.style.display !== roomsBefore[i]).length;
    input.click(); await frames(2);
    out[input.id] = { objects: flipped.length, names: flipped.map(o => o.name).sort(), pictures: picFlips, roomLabels: roomFlips, startsChecked: input.checked };
  }
  return out;
}

function readCard() {
  const card = document.getElementById('br-card');
  if (!card || !window.__build) return null;
  const txt = n => (n ? n.textContent.replace(/\s+/g, ' ').trim() : null);
  const b = window.__build;
  return {
    phase: b.phase,
    visible: getComputedStyle(card).display !== 'none',
    inputs: [...card.querySelectorAll('input[data-k][data-p]')].map(i => ({ floor: i.dataset.k, prop: i.dataset.p, value: i.value })),
    introTitle: txt(card.querySelector('.br-file')),
    facts: [...card.querySelectorAll('#br-settings ul li')].map(li => li.textContent),
    factsHtml: [...card.querySelectorAll('#br-settings ul li')].map(li => li.innerHTML),
    layersTitle: txt(card.querySelector('details summary')),
    layers: [...card.querySelectorAll('details table tr')].map(tr => [...tr.children].map(td => td.textContent)),
    settings: JSON.parse(JSON.stringify(b.state.settings)),
    steps: b.steps.map(s => ({ key: s.key, title: s.title, caption: s.caption(b.state.settings), t0: s.t0, t1: s.t1 })),
    stepList: [...document.querySelectorAll('#br-steps li')].map(li => li.textContent),
  };
}

function readFurniture() {
  const F = window.__host.furniture;
  if (!F) return null;
  return { kinds: F.kinds(), pieces: F.pieces().length, keepDoorways: F.keepDoorways(), csv: F.csv() };
}

// ---------------------------------------------------------------------------------------------------------- driver
const call = (fn, arg) => `(${fn.toString()})(${arg === undefined ? '' : JSON.stringify(arg)})`;
const sha1 = s => createHash('sha1').update(s, 'utf8').digest('hex');

async function main() {
  await requireFreePort(PORT, 'capture-prototype-facts');
  const profile = path.join(TMP, 'capture-profile');
  rmSync(profile, { recursive: true, force: true });
  mkdirSync(OUT, { recursive: true });
  const { tab, close } = await launch({ port: PORT, profile, step: 'scaffold: capture-prototype-facts' });
  const P = pageApi(tab);
  let failed = 0;
  try {
    for (const pg of PAGES) {
      if (args.only && !pg.out.includes(args.only)) continue;
      const url = pathToFileURL(path.join(PROTOTYPES, pg.page)).href;
      await P.goto(url + '?build=0&nodownload=1');
      await P.evaluate(`(() => { try { Object.keys(localStorage).filter(k => k.startsWith('walkthrough-furniture')).forEach(k => localStorage.removeItem(k)); } catch (e) {} })()`);
      await P.goto(url + '?build=0&nodownload=1');
      const errors = [];
      const panel = await P.evaluate(call(readPanel));
      const scene = await P.evaluate(call(readScene, { cameraFromProbe: pg.cameraFromProbe ?? null }));
      const ticks = await P.evaluate(call(tickSizes));
      const furniture = await P.evaluate(call(readFurniture));
      errors.push(...P.logs.filter(l => /exception|error/i.test(l) && !/favicon/i.test(l)));
      await P.goto(url);
      const card = await P.evaluate(call(readCard));
      const settingsHint = await P.evaluate(`(document.getElementById('hint') || {}).textContent || null`);
      errors.push(...P.logs.filter(l => /exception|error/i.test(l) && !/favicon/i.test(l)));
      if (furniture) { furniture.csvSha1 = sha1(furniture.csv); furniture.csvBytes = Buffer.byteLength(furniture.csv, 'utf8'); delete furniture.csv; }
      const facts = {
        format: 'walkthrough-prototype-facts/1',
        page: pg.page,
        capturedAt: new Date().toISOString(),
        how: 'tools/capture-prototype-facts.mjs (DESIGN.md 17.1): scene with ?build=0&nodownload=1, card with the plain address',
        ...panel,
        scene,
        ticksFlip: ticks,
        card,
        hintOnSettingsScreen: settingsHint,
        furniture,
        errors,
      };
      writeFileSync(path.join(OUT, `${pg.out}.json`), JSON.stringify(facts, null, 2) + '\n');
      const floors = scene.floors.map(f => `${f.key}: ${f.colliders.length} colliders (${f.colliderVertices} v), ${f.walkables.length} walkables (${f.walkableVertices} v), late ${f.late}`).join('; ');
      console.log(`${errors.length ? 'ERRORS' : 'ok    '} ${pg.out}: "${panel.title}", stamp ${panel.stamp}, ${floors}${card ? `, card ${card.steps.length} steps` : ', no replay'}${furniture ? `, ${furniture.kinds.length} kinds csv ${furniture.csvSha1.slice(0, 12)}` : ''}`);
      if (errors.length) { failed++; console.log('       ' + errors.join('\n       ')); }
      await sleep(200);
    }
  } finally {
    await close();
  }
  if (failed) process.exit(1);
}

await main();
