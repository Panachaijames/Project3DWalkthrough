// The walk-parity golden (docs/rooms/DESIGN.md R-13, ACCEPTANCE RA-2; WORK_BREAKDOWN R0 item 1). Scaffold R0; frozen.
//
// How the models of before the rooms milestone walk, recorded from the viewer as it was at commit 66b4c06, so that the
// viewer with slabs you climb (R-9) can be shown to walk them exactly as before. It drives ONLY the frozen ModesApi
// (setMode, goToFloor, changeFloor, tick, state, probe), the read-outs (ReadoutsApi.rayHit) and the page's own input
// (keys, the eye slider, a double-click), never the walker's internals:
//   * the real parseBuiltModel, resolvePresentation, buildScene, createVisibility, createReadouts and installModes, on a
//     context without WebGL (happy-dom; the renderer is a stub, the furniture is not installed: structure only);
//   * per floor: the wall, door and glass recipes of tests/e2e/lib/walks.ts (unrounded), walks across the floor plates'
//     edges, and a grid of spots with onFloor, clearance, open and the landing of a double-click there (findFree,
//     faceOpen);
//   * per model: Walk from the button, then W / Shift+W / W+D through tick(now) with a made-up clock (the frame path);
//     PgUp and PgDn; double-clicks on the canvas; Ghost -> Walk landings; one eye-height change;
//   * the hotel: the walk north into its F1 flight, which the old `step` parts must still stop.
//
//   runWalkParity()      -> the results of the viewer as it is now (walk-parity.test.ts compares them with the golden
//                           within 1e-9 m)
//   recordWalkParity()   -> writes test/fixtures/walk-parity.json. It refuses unless `git diff 66b4c06 --
//                           packages/viewer/src` is empty (and nothing there is untracked), and writes that tree's hash
//                           into the golden. Run it with
//                             WT_RECORD_WALK_PARITY=1 npx vitest run --project viewer test/unit/modes/walk-parity.test.ts
//                           The test pins the golden's own sha1: a new recording is a decision, not a routine.
import { execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { readFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { Box3, PerspectiveCamera, Scene, Vector2, Vector3, type WebGLRenderer } from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import type {
  BuiltModel, FloorRecord, InternalEvents, ModesApi, ModesState, PanelSlot, Presentation, ViewerContext, ViewerEvents,
} from '../../src/contracts';
import { buildScene } from '../../src/core/build';
import { createDisposer } from '../../src/core/disposer';
import { createEventBus } from '../../src/core/events';
import { createReadouts } from '../../src/core/readouts';
import { createVisibility } from '../../src/core/visibility';
import { parseBuiltModel } from '../../src/model/parse';
import { parsePresentation, resolvePresentation } from '../../src/model/presentation';
import { installModes } from '../../src/modes/index';

export const APP = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../../..');
export const GOLDEN = path.join(APP, 'packages/viewer/test/fixtures/walk-parity.json');
/** The commit the golden is recorded from: the viewer before the rooms milestone. */
export const BASE = '66b4c06';
export const VIEWER_SRC = 'packages/viewer/src';

/** The six model files fixtures/models held on 11 Nov 2026, with their presentation fixture (null: a plain one). */
export const MODELS: [string, string | null][] = [
  ['bank-v1', 'bank-sampeng-v1'], ['bank-v2', 'bank-sampeng-v2'], ['hotel', 'hotel-lobby'], ['house', 'sukhumvit-house'],
  ['mini', null], ['suite', 'presidential-suite'],
];
const PLAIN: Presentation = {
  documentTitle: 't', heading: 'h', intro: [], accent: '#2f6f8f', legend: { layout: 'inline', items: [] },
  camera: { kind: 'fixed', position: [24, 27, 29], target: [0, 2.5, 0] },
};
const SIZE = { width: 1400, height: 880 };
const D2R = Math.PI / 180;

type Json = null | boolean | number | string | Json[] | { [k: string]: Json };
/** A number as JSON keeps it: Infinity and NaN as their names. */
const n = (v: number): number | string => (Number.isFinite(v) ? v : String(v));
const file = (rel: string) => readFileSync(path.join(APP, rel));
const json = (rel: string): unknown => JSON.parse(file(rel).toString('utf8'));
export const sha1 = (b: Buffer | string) => createHash('sha1').update(b).digest('hex');

// ------------------------------------------------------------------------------------------------------------ the rig
interface Rig { ctx: ViewerContext; model: BuiltModel; modes: ModesApi; s: ModesState; canvas: HTMLCanvasElement; dispose(): void }

function mount(name: string, pres: string | null): Rig {
  const model = parseBuiltModel(json(`fixtures/models/${name}.model.json`));
  const presentation = resolvePresentation(parsePresentation(pres ? json(`fixtures/presentation/${pres}.json`) : PLAIN), model);
  const built = buildScene(model, presentation);
  const scene = new Scene();
  for (const f of built.floors) scene.add(f.group);
  if (built.groundPlane) scene.add(built.groundPlane);
  const disposer = createDisposer();

  const container = document.createElement('div');
  document.body.append(container);
  const root = document.createElement('div');
  root.className = 'wtv';
  root.setAttribute('data-wt', 'root');
  const div = (wt: string) => { const e = document.createElement('div'); e.setAttribute('data-wt', wt); return e; };
  const hint = div('hint'), errorBox = div('error'), panelEl = div('panel');
  const style = document.createElement('style');
  const canvas = document.createElement('canvas');
  canvas.getBoundingClientRect = () => ({ left: 0, top: 0, right: SIZE.width, bottom: SIZE.height, width: SIZE.width, height: SIZE.height, x: 0, y: 0, toJSON: () => ({}) });
  root.append(canvas, style, hint, errorBox, panelEl);
  container.append(root);
  const slots = new Map<PanelSlot, HTMLDivElement>();
  for (const slot of ['title', 'intro', 'floors', 'modes', 'shows', 'legend', 'build', 'furniture'] as PanelSlot[]) {
    const e = div(`slot-${slot}`);
    slots.set(slot, e);
    panelEl.append(e);
  }

  const camera = new PerspectiveCamera(40, SIZE.width / SIZE.height, 0.1, presentation.camera.far);
  const controls = new OrbitControls(camera, canvas);
  controls.enableDamping = true;
  const cam = presentation.camera;
  if (cam.kind === 'fixed') {
    camera.position.set(...cam.position);
    controls.target.set(...cam.target);
  } else {
    const box = new Box3();
    for (const f of built.floors) for (const m of f.walkables) box.expandByObject(m);
    const c = box.isEmpty() ? new Vector3() : box.getCenter(new Vector3());
    controls.target.set(c.x, cam.targetY, c.z);
    camera.position.set(c.x + cam.away[0], cam.targetY + cam.away[1], c.z + cam.away[2]);
  }
  camera.lookAt(controls.target);
  controls.update();
  camera.updateMatrixWorld();

  const renderer = {
    domElement: canvas, getPixelRatio: () => 1, setPixelRatio: () => {}, setSize: () => {}, getSize: (t: Vector2) => t.set(SIZE.width, SIZE.height),
    getDrawingBufferSize: (t: Vector2) => t.set(SIZE.width, SIZE.height), render: () => {}, setRenderTarget: () => {}, getRenderTarget: () => null,
    capabilities: { getMaxAnisotropy: () => 1 }, dispose: () => {},
  } as unknown as WebGLRenderer;
  const errors: string[] = [];
  const ctx = {
    id: `parity-${name}`, container, renderer, canvas, scene, camera, controls, model, presentation, stages: null,
    project: { model, presentation, stages: null, pictures: {}, heights: null, stamp: 'walkparity00' },
    options: {
      address: {}, build: 'skip', furnitureHeights: 'local', storageKey: 'walk-parity', testHook: false, pixelRatioCap: 2,
      download: () => {}, noDownload: true, testFailAt: null,
    },
    floors: built.floors, floorByKey: new Map<string, FloorRecord>(built.floors.map(f => [f.key, f])), built,
    disposer, events: createEventBus<ViewerEvents>(), bus: createEventBus<InternalEvents>(),
    ui: {
      root, hint, errorBox,
      addStyle: (css: string) => { style.textContent += `\n${css}`; },
      setFlag: (flag: string, on: boolean) => { if (on) root.setAttribute(`data-${flag}`, ''); else root.removeAttribute(`data-${flag}`); },
    },
    size: () => ({ ...SIZE }),
    rectOf: (e: Element) => { const r = e.getBoundingClientRect(); return { left: r.left, top: r.top, right: r.right, bottom: r.bottom, width: r.width, height: r.height }; },
    reportError: (err: unknown) => { errors.push(err instanceof Error ? err.message : String(err)); throw err; },
    panel: { el: panelEl, slot: (slot: PanelSlot) => slots.get(slot)!, markFloors: () => {} },
    pictures: null, furniture: null, replay: null, labels: { labels: [], place: () => {} }, loop: null, heights: null,
  } as unknown as ViewerContext;
  const w = ctx as unknown as Record<string, unknown>;
  w.visibility = createVisibility(ctx);
  w.readouts = createReadouts(ctx);
  ctx.visibility.applyFloor();
  ctx.visibility.applyToggles();
  const modes = installModes(ctx);
  w.modes = modes;
  return {
    ctx, model, modes, s: modes.state, canvas,
    dispose: () => { disposer.dispose(); controls.dispose(); container.remove(); },
  };
}

// ------------------------------------------------------------------------------------------------------ the recipes
const key = (type: 'keydown' | 'keyup', code: string) => {
  document.body.dispatchEvent(new KeyboardEvent(type, { code, bubbles: true, cancelable: true }));
};
const where = (s: ModesState): Json => ({ floor: s.floor.key, x: s.pos.x, y: s.pos.y, z: s.pos.z, yaw: s.yaw });
/** The slab bounds of a floor in plan (x0, y0, x1, y1), else the bounds of all its parts. */
function planBounds(model: BuiltModel, floor: string): [number, number, number, number] {
  const of = (kinds: (k: string) => boolean) => {
    let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
    for (const p of model.parts) {
      if (p.floor !== floor || !kinds(p.kind)) continue;
      for (const [x, y] of p.o) { x0 = Math.min(x0, x); x1 = Math.max(x1, x); y0 = Math.min(y0, y); y1 = Math.max(y1, y); }
    }
    return [x0, y0, x1, y1] as [number, number, number, number];
  };
  const slabs = of(k => k === 'slab');
  return Number.isFinite(slabs[0]) ? slabs : of(() => true);
}

/** tests/e2e/lib/walks.ts wallWalks (seed 7, 8000 tries, 40 spots): walk into the nearest wall from random spots. */
function wallRecipe(r: Rig): Json {
  const { s } = r, v = r.modes;
  let seed = 7, tries = 0;
  const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
  let x0 = Infinity, x1 = -Infinity, z0 = Infinity, z1 = -Infinity;
  for (const o of s.floor.group.children) {
    const g = (o as { geometry?: { computeBoundingBox(): void; boundingBox: Box3 | null } }).geometry;
    if (!g) continue;
    g.computeBoundingBox();
    const b = g.boundingBox!;
    x0 = Math.min(x0, b.min.x); x1 = Math.max(x1, b.max.x); z0 = Math.min(z0, b.min.z); z1 = Math.max(z1, b.max.z);
  }
  const out: Json[] = [];
  while (out.length < 40 && tries++ < 8000) {
    s.pos.x = x0 + rnd() * (x1 - x0); s.pos.z = z0 + rnd() * (z1 - z0);
    if (!v.probe.onFloor() || v.probe.clearance() < 0.6) continue;
    const d = [...Array(72)].map((_, i) => v.probe.open(i * 5));
    let k = 0;
    d.forEach((x, j) => { if (x < d[k]!) k = j; });
    if (d[k]! > 2.5) continue;
    const a = s.pos.clone();
    const moved = v.probe.walk(k * 5, d[k]! + 1);
    out.push({ x: a.x, z: a.z, deg: k * 5, open: d[k]!, moved, ex: s.pos.x, ez: s.pos.z, crosses: v.probe.crosses(a.x, a.z, s.pos.x, s.pos.z), clearance: n(v.probe.clearance()) });
  }
  return { tries, spots: out };
}

/** tests/e2e/lib/walks.ts doorWalks: straight through the middle of every door and passage, both ways. */
function doorRecipe(r: Rig): Json {
  const { s } = r, v = r.modes, out: Json[] = [];
  for (const d of r.model.openings) {
    if (d.floor !== s.floor.key || (d.kind !== 'door' && d.kind !== 'passage')) continue;
    for (const sign of [1, -1]) {
      const nx = d.nx * sign, ny = d.ny * sign, deg = Math.atan2(-nx, ny) / D2R;
      const row: { [k: string]: Json } = { id: d.id, sign, back: null, along: 'no start' };
      for (const back of [0.9, 0.7, 0.55, 0.45, 0.4]) {
        s.pos.x = d.x - nx * back; s.pos.z = -(d.y - ny * back);
        const onFloor = v.probe.onFloor(), clr = v.probe.clearance();
        if (!onFloor || clr < 0.25) continue;
        const moved = v.probe.walk(deg, back * 2);
        Object.assign(row, { back, clearance: n(clr), moved, along: (s.pos.x - d.x) * nx + (-s.pos.z - d.y) * ny, ex: s.pos.x, ez: s.pos.z });
        break;
      }
      out.push(row);
    }
  }
  return out;
}

/** tests/e2e/lib/walks.ts glassWalks: straight at every glass probe from in front of it. */
function glassRecipe(r: Rig): Json {
  const { s } = r, v = r.modes, out: Json[] = [];
  for (const g of r.model.probes) {
    if (g.floor !== s.floor.key) continue;
    for (const side of g.inside) {
      const nx = g.nx * side, ny = g.ny * side, deg = Math.atan2(nx, -ny) / D2R;
      const row: { [k: string]: Json } = { id: g.id, side, back: null, short: null, ahead: null };
      for (const back of [1.0, 0.8, 0.6]) {
        s.pos.x = g.x + nx * back; s.pos.z = -(g.y + ny * back);
        const onFloor = v.probe.onFloor(), clr = v.probe.clearance();
        if (!onFloor || clr < 0.25) continue;
        const moved = v.probe.walk(deg, 2.0);
        const h = r.ctx.readouts.rayHit(g.floor, s.pos.x, -s.pos.z, 1.2, -nx, -ny, 1.5);
        Object.assign(row, { back, moved, short: (s.pos.x - g.x) * nx + (-s.pos.z - g.y) * ny, ex: s.pos.x, ez: s.pos.z, ahead: h ? { name: h.name, d: h.d } : 'nothing' });
        break;
      }
      out.push(row);
    }
  }
  return out;
}

/** Floor edges: from 0.6 m inside the plate, walk across the middle of an edge (straight, and 30 degrees off). */
function edgeRecipe(r: Rig): Json {
  const { s } = r, v = r.modes;
  const cands: { x: number; z: number; deg: number }[] = [];
  for (const p of r.model.parts) {
    if (p.floor !== s.floor.key || p.kind !== 'slab') continue;
    for (const ring of [p.o, ...p.h]) {
      for (let i = 0; i < ring.length; i++) {
        const a = ring[i]!, b = ring[(i + 1) % ring.length]!, len = Math.hypot(b[0] - a[0], b[1] - a[1]);
        if (len < 1.0) continue;
        const mx = (a[0] + b[0]) / 2, my = (a[1] + b[1]) / 2, ux = -(b[1] - a[1]) / len, uy = (b[0] - a[0]) / len;
        for (const side of [1, -1]) {
          const x = mx + ux * side * 0.6, y = my + uy * side * 0.6;
          s.pos.x = x; s.pos.z = -y;
          if (!v.probe.onFloor() || v.probe.clearance() < 0.25) continue;
          cands.push({ x, z: -y, deg: Math.atan2(ux * side, -uy * side) / D2R });      // walking back toward the edge
          break;
        }
      }
    }
  }
  const step = Math.max(1, Math.ceil(cands.length / 12));
  const out: Json[] = [];
  for (let i = 0; i < cands.length; i += step) {
    const c = cands[i]!;
    for (const off of [0, 30]) {
      s.pos.x = c.x; s.pos.z = c.z;
      const moved = v.probe.walk(c.deg + off, 1.5);
      out.push({ x: c.x, z: c.z, deg: c.deg + off, moved, ex: s.pos.x, ez: s.pos.z, onFloor: v.probe.onFloor(), clearance: n(v.probe.clearance()) });
    }
  }
  return { candidates: cands.length, walks: out };
}

/** A 5 x 5 grid over the floor: onFloor, clearance, open in four directions, and where a double-click there lands. */
function spotRecipe(r: Rig, f: FloorRecord): Json {
  const { s } = r, v = r.modes, [x0, y0, x1, y1] = planBounds(r.model, f.key), out: Json[] = [];
  for (let i = 0; i < 5; i++) {
    for (let j = 0; j < 5; j++) {
      const x = x0 + (x1 - x0) * (i + 0.5) / 5, y = y0 + (y1 - y0) * (j + 0.5) / 5;
      if (s.mode !== 'walk' || s.floor !== f) { v.setMode('orbit'); v.setMode('walk', { floor: f, point: { x, z: -y } }); }
      s.pos.x = x; s.pos.z = -y;
      const row: { [k: string]: Json } = { x, z: -y, onFloor: v.probe.onFloor(), clearance: n(v.probe.clearance()), open: [0, 90, 180, 270].map(a => v.probe.open(a)) };
      v.setMode('orbit');
      v.setMode('walk', { floor: f, point: { x, z: -y } });                     // what a double-click on this spot does
      row.landing = where(s);
      row.landed = { onFloor: v.probe.onFloor(), clearance: n(v.probe.clearance()) };
      out.push(row);
    }
  }
  return out;
}

/** Walk from the button, then held keys through tick(now) with a made-up clock (60 frames a second). */
function keyRecipe(r: Rig): Json {
  const { s } = r, v = r.modes, frames: Json[] = [];
  v.setMode('orbit');
  v.setMode('walk');
  const start = where(s);
  let t = 1000, f = 0;
  v.tick(t);
  const run = (count: number, codes: string[]) => {
    for (const c of codes) key('keydown', c);
    for (let i = 0; i < count; i++) {
      t += 1000 / 60; f++;
      v.tick(t);
      if (f % 30 === 0) frames.push({ frame: f, ...(where(s) as { [k: string]: Json }) });
    }
    for (const c of codes) key('keyup', c);
  };
  run(120, ['KeyW']);
  s.yaw += Math.PI / 2;
  run(60, ['KeyW', 'ShiftLeft']);
  run(60, ['KeyW', 'KeyD']);
  s.yaw += Math.PI * 0.75;
  run(90, ['ArrowUp']);
  run(30, ['KeyS', 'KeyA']);
  return { start, frames, end: where(s), camera: v.probe.camera().y };
}

/** PgUp and PgDn in Walk (teleports). */
function floorRecipe(r: Rig): Json {
  const { s } = r, v = r.modes, out: Json[] = [];
  v.setMode('orbit');
  v.setMode('walk');
  out.push({ step: 'walk', ...(where(s) as { [k: string]: Json }) });
  for (const code of ['PageUp', 'PageUp', 'PageDown', 'PageDown']) {
    key('keydown', code); key('keyup', code);
    out.push({ step: code, ...(where(s) as { [k: string]: Json }), onFloor: v.probe.onFloor(), clearance: n(v.probe.clearance()), visible: v.probe.visible() });
  }
  return out;
}

/** Double-clicks on the canvas in Orbit (the camera where the page starts). */
function dblclickRecipe(r: Rig): Json {
  const { s } = r, v = r.modes, out: Json[] = [];
  for (const [px, py] of [[700, 440], [500, 400], [900, 500], [700, 600], [350, 300], [1100, 250]] as const) {
    v.setMode('orbit');
    r.ctx.camera.updateMatrixWorld();
    r.canvas.dispatchEvent(new MouseEvent('dblclick', { clientX: px, clientY: py, bubbles: true }));
    out.push({ px, py, mode: s.mode, ...(where(s) as { [k: string]: Json }), onFloor: s.mode === 'walk' ? v.probe.onFloor() : null });
  }
  v.setMode('orbit');
  return out;
}

/** Ghost -> Walk: from 5 m above each floor's middle, from 0.2 m above its level, and from far outside. */
function ghostRecipe(r: Rig): Json {
  const { s } = r, v = r.modes, out: Json[] = [];
  for (const f of r.ctx.floors) {
    const [x0, y0, x1, y1] = planBounds(r.model, f.key), cx = (x0 + x1) / 2, cz = -(y0 + y1) / 2;
    for (const [what, x, y, z] of [['above', cx, f.level + 5, cz], ['just above', cx, f.level + 0.2, cz], ['eye', cx + 1.5, f.level + 1.6, cz - 1.5], ['outside', cx + 200, f.level + 2, cz]] as const) {
      v.setMode('orbit');
      v.setMode('ghost');
      s.pos.set(x, y, z);
      v.setMode('walk');
      out.push({ from: f.key, what, ...(where(s) as { [k: string]: Json }), onFloor: v.probe.onFloor(), clearance: n(v.probe.clearance()) });
    }
  }
  v.setMode('orbit');
  return out;
}

/** One eye-height change with the Camera panel's slider, then a frame and a 1 m walk. */
function eyeRecipe(r: Rig): Json {
  const { s } = r, v = r.modes;
  v.setMode('orbit');
  v.setMode('walk');
  const before = { eye: s.eye, y: s.pos.y, camera: v.probe.camera().y };
  const slider = r.ctx.ui.root.querySelector('[data-wt=eye]') as HTMLInputElement;
  slider.value = '1.2';
  slider.dispatchEvent(new Event('input'));
  const typed = { eye: s.eye, y: s.pos.y, camera: v.probe.camera().y };
  v.tick(5000); v.tick(5000 + 1000 / 60);
  const moved = v.probe.walk(s.yaw / D2R, 1.0);
  const after = { eye: s.eye, moved, ...(where(s) as { [k: string]: Json }), camera: v.probe.camera().y, onFloor: v.probe.onFloor() };
  slider.value = '1.6';
  slider.dispatchEvent(new Event('input'));
  return { before, typed, after, back: { eye: s.eye, y: s.pos.y } };
}

/** The hotel: the walk north into its F1 flight (x -4.67 ... -2.17, steps from y -1.53): the old steps stop it. */
function hotelFlight(r: Rig): Json {
  const { s } = r, v = r.modes, f = r.ctx.floorByKey.get('F1')!, out: Json[] = [];
  for (const x of [-3.42, -4.2, -2.6]) {
    v.setMode('orbit');
    v.setMode('walk', { floor: f, point: { x, z: 2.6 } });
    s.pos.x = x; s.pos.z = 2.6;                                        // plan (x, -2.6): 1.07 m before the first step
    const start = { onFloor: v.probe.onFloor(), clearance: n(v.probe.clearance()) };
    const moved = v.probe.walk(0, 5);                                   // 0 degrees = north (three.js -z)
    const knee = r.ctx.readouts.rayHit('F1', s.pos.x, -s.pos.z, 0.35, 0, 1, 1.0), chest = r.ctx.readouts.rayHit('F1', s.pos.x, -s.pos.z, 1.2, 0, 1, 1.0);
    out.push({ x, start, moved, ...(where(s) as { [k: string]: Json }), intoFlight: -s.pos.z - -1.53, knee: knee ? { name: knee.name, d: knee.d } : null, chest: chest ? { name: chest.name, d: chest.d } : null });
  }
  return out;
}

// ------------------------------------------------------------------------------------------------------------ the run
export interface WalkParity {
  format: 'walk-parity/1';
  base: string;
  /** git tree of packages/viewer/src at `base` (the viewer the golden was recorded from). */
  viewerTree: string;
  models: Record<string, { sha1: string; results: Json }>;
}

/** The results of the viewer as it is now, for one model (a key of MODELS) or all six. */
export function runWalkParity(only?: string): Record<string, { sha1: string; results: Json }> {
  const out: Record<string, { sha1: string; results: Json }> = {};
  for (const [name, pres] of MODELS) {
    if (only && only !== name) continue;
    const r = mount(name, pres);
    try {
      const floors: { [k: string]: Json } = {};
      for (const f of r.ctx.floors) {
        const [x0, y0, x1, y1] = planBounds(r.model, f.key);
        r.modes.setMode('orbit');
        r.modes.setMode('walk', { floor: f, point: { x: (x0 + x1) / 2, z: -(y0 + y1) / 2 } });
        const entry = where(r.s);
        floors[f.key] = { entry, walls: wallRecipe(r), doors: doorRecipe(r), glass: glassRecipe(r), edges: edgeRecipe(r), spots: spotRecipe(r, f) };
      }
      const results: { [k: string]: Json } = { floors, keys: keyRecipe(r), pages: floorRecipe(r), dblclick: dblclickRecipe(r), ghost: ghostRecipe(r), eye: eyeRecipe(r) };
      if (name === 'hotel') results.flight = hotelFlight(r);
      out[name] = { sha1: sha1(file(`fixtures/models/${name}.model.json`)), results };
    } finally {
      r.dispose();
    }
  }
  return out;
}

const git = (...args: string[]) => execFileSync('git', args, { cwd: APP, encoding: 'utf8' }).trim();

/** Writes the golden from the viewer at BASE; throws when packages/viewer/src differs from that commit. */
export function recordWalkParity(): WalkParity {
  try {
    execFileSync('git', ['diff', '--quiet', BASE, '--', VIEWER_SRC], { cwd: APP });
  } catch {
    throw new Error(`record-walk-parity: ${VIEWER_SRC} differs from ${BASE} (git diff ${BASE} -- ${VIEWER_SRC}): the golden is recorded from the unchanged viewer only`);
  }
  const untracked = git('status', '--porcelain', '--', VIEWER_SRC);
  if (untracked) throw new Error(`record-walk-parity: ${VIEWER_SRC} has changed or untracked files:\n${untracked}`);
  const viewerTree = git('rev-parse', `${BASE}:app/${VIEWER_SRC}`);
  const golden: WalkParity = { format: 'walk-parity/1', base: BASE, viewerTree, models: runWalkParity() };
  writeFileSync(GOLDEN, JSON.stringify(golden, null, 1) + '\n');
  return golden;
}

/** Every place where `now` differs from `golden`: numbers by more than `tol`, everything else exactly. */
export function parityDiffs(golden: Json, now: Json, tol = 1e-9, at = '', out: string[] = []): string[] {
  if (out.length > 40) return out;
  if (typeof golden === 'number' && typeof now === 'number') {
    if (Math.abs(golden - now) > tol) out.push(`${at}: ${now} (golden ${golden})`);
  } else if (Array.isArray(golden) && Array.isArray(now)) {
    if (golden.length !== now.length) out.push(`${at}: ${now.length} entries (golden ${golden.length})`);
    else golden.forEach((g, i) => parityDiffs(g, now[i]!, tol, `${at}/${i}`, out));
  } else if (golden && now && typeof golden === 'object' && typeof now === 'object' && !Array.isArray(golden) && !Array.isArray(now)) {
    const keys = new Set([...Object.keys(golden), ...Object.keys(now)]);
    for (const k of keys) {
      if (!(k in golden) || !(k in now)) out.push(`${at}/${k}: ${k in now ? 'not in the golden' : 'missing'}`);
      else parityDiffs(golden[k]!, now[k]!, tol, `${at}/${k}`, out);
    }
  } else if (golden !== now) {
    out.push(`${at}: ${JSON.stringify(now)} (golden ${JSON.stringify(golden)})`);
  }
  return out;
}
