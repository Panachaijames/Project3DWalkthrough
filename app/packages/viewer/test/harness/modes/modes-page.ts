// Builder B's harness page (DESIGN.md 17.4, WORK_BREAKDOWN B "Tests alone"): installModes on the shared test context
// with the real WebGL renderer, so modes.spec.ts drives real keys, the mouse, the wheel, double-clicks, touch (CDP) and
// photos in headless Edge. ?model=bank-v2 (default) | suite | house | hotel.
//
// This page stands in for viewer.ts (A) and the panel (C), which other builders write: it registers modes.tick in the
// loop's `modes` phase as viewer.ts does (11.4 step 8d), downloads photos with an <a download> click inside the root as
// ResolvedOptions.download's default does, and adds, for the harness only, the pages' own CSS under .wtv (the side panel,
// the buttons, the hint, `container: wtv / size`), a heading, the floors row (Walk: go to the floor; otherwise show it;
// aria-pressed as the pages' markFloors) and two ticks (Floor plates, Glass), as the prototype pages had them.
import { Box3, Color, Euler, MathUtils, Matrix4, Plane, Quaternion, Raycaster, Vector2, Vector3 } from 'three';
import type { BuiltModel, FloorKey, ModesApi, Presentation, ToggleName, ViewMode } from '../../../src/contracts';
import { installModes } from '../../../src/modes/index';
import { el } from '../../../src/ui/dom';
import { makeTestContext, type TestContext } from '../context';

type Loader = () => Promise<{ default: unknown }>;
const FIXTURES: Record<string, [Loader, Loader]> = {
  'bank-v2': [() => import('../../../../../fixtures/models/bank-v2.model.json'), () => import('../../../../../fixtures/presentation/bank-sampeng-v2.json')],
  suite: [() => import('../../../../../fixtures/models/suite.model.json'), () => import('../../../../../fixtures/presentation/presidential-suite.json')],
  house: [() => import('../../../../../fixtures/models/house.model.json'), () => import('../../../../../fixtures/presentation/sukhumvit-house.json')],
  hotel: [() => import('../../../../../fixtures/models/hotel.model.json'), () => import('../../../../../fixtures/presentation/hotel-lobby.json')],
};

/** The prototype pages' own CSS (bank_test/src/make_html.py), under .wtv: what C's BASE_CSS ports for the real viewer. */
const PAGE_CSS = `
.wtv { container: wtv / size; font: 14px/1.4 system-ui, -apple-system, "Segoe UI", sans-serif; color: var(--ink); background: var(--bg);
  --bg: #eef0f2; --panel: #ffffffee; --ink: #1d2329; --muted: #5b6670; --line: #d5dade; }
.wtv canvas { display: block; width: 100%; height: 100%; }
.wtv [data-wt=panel] { position: absolute; top: 12px; left: 12px; width: min(330px, calc(100% - 48px)); max-height: calc(100% - 60px);
  overflow: auto; background: var(--panel); border: 1px solid var(--line); border-radius: 10px; padding: 12px 14px; box-shadow: 0 2px 10px #0001; }
.wtv h1 { font-size: 15px; margin: 0 0 4px; }
.wtv .row { display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 8px; }
.wtv button { border: 1px solid var(--line); background: #fff; border-radius: 7px; padding: 5px 10px; cursor: pointer; font: inherit; font-size: 13px; color: var(--ink); }
.wtv button[aria-pressed=true] { background: var(--accent); border-color: var(--accent); color: #fff; }
.wtv label { font-size: 13px; display: flex; align-items: center; gap: 6px; }
.wtv [data-wt=hint] { position: absolute; bottom: 10px; left: 12px; right: 12px; color: var(--muted); font-size: 12px; }
.wtv [data-wt=error] { position: absolute; right: 12px; bottom: 12px; max-width: 420px; background: #b42318; color: #fff; font-size: 12px; padding: 8px 10px; border-radius: 8px; z-index: 10; white-space: pre-wrap; }
.wtv [data-wt=error][hidden] { display: none; }
`;

export interface ModesKit {
  ready: boolean;
  model: string;
  ctx: TestContext;
  modes: ModesApi;
  errors: string[];
  photos: { name: string; width: number; height: number }[];
  downloads: string[];
}
declare global { interface Window { __modes?: ModesKit | { error: string } } }

async function main() {
  const name = new URLSearchParams(location.search).get('model') ?? 'bank-v2';
  const pair = FIXTURES[name];
  if (!pair) throw new Error(`no fixture ${name}`);
  const [m, p] = await Promise.all([pair[0](), pair[1]()]);
  const model = m.default as BuiltModel, presentation = p.default as Presentation;
  const downloads: string[] = [];
  let ctx!: TestContext;
  ctx = makeTestContext({
    model, presentation, renderer: 'webgl', container: document.getElementById('app')!,
    stamp: 'modes0harness',
    options: {
      // as ResolvedOptions.download's default: an <a download> click inside the root
      download: (blob, fileName) => {
        downloads.push(fileName);
        const a = el('a', { attrs: { href: URL.createObjectURL(blob), download: fileName } });
        ctx.ui.root.append(a);
        a.click();
        a.remove();
        setTimeout(() => URL.revokeObjectURL(a.href), 60_000);
      },
    },
  });
  ctx.ui.root.style.setProperty('--accent', ctx.presentation.accent);
  ctx.ui.addStyle(PAGE_CSS);

  // ---------------------------------------------------------------- stand-ins for C's panel: heading, floors row, ticks
  ctx.panel.slot('title').append(el('h1', { wt: 'heading', text: ctx.presentation.heading }));
  const floorButtons: HTMLButtonElement[] = [];
  let modes!: ModesApi;
  if (ctx.floors.length > 1) {
    const keys: ('all' | FloorKey)[] = ['all', ...ctx.floors.map(f => f.key)];
    for (const key of keys) {
      const text = key === 'all' ? ctx.presentation.floorButtons.all : ctx.presentation.floorButtons.labels[key] ?? ctx.floorByKey.get(key)!.name;
      const b = el('button', { text, attrs: { type: 'button', 'data-floor': key, 'aria-pressed': String(key === 'all') } });
      b.addEventListener('click', () => {
        if (modes.mode === 'walk') { modes.goToFloor(key === 'all' ? ctx.floors[0]!.key : key); return; }
        ctx.visibility.setFloorMode(key);
      });
      floorButtons.push(b);
    }
    ctx.panel.slot('floors').append(el('div', { cls: 'row', wt: 'floors' }, floorButtons));
  }
  let last: { mode: ViewMode; floor: FloorKey } = { mode: 'orbit', floor: ctx.floors[0]!.key };
  const markFloors = () => {
    const key = last.mode === 'walk' ? last.floor : ctx.visibility.floorMode;
    for (const b of floorButtons) b.setAttribute('aria-pressed', String(b.getAttribute('data-floor') === key));
  };
  ctx.bus.on('mode', e => { last = e; markFloors(); });
  ctx.bus.on('floorMode', () => markFloors());
  const ticks = (['plates', 'glass'] as ToggleName[]).map(t => {
    const box = el('input', { wt: 'toggle', attrs: { type: 'checkbox', 'data-toggle': t } });
    box.checked = ctx.visibility.toggles[t];
    box.addEventListener('change', () => ctx.visibility.setToggle(t, box.checked));
    return el('label', {}, [box, ` ${ctx.presentation.labels[t]}`]);
  });
  ctx.panel.slot('shows').append(el('div', { cls: 'row', wt: 'shows' }, ticks));

  // ---------------------------------------------------------------- the modes, as viewer.ts installs them
  modes = installModes(ctx);
  ctx.modes = modes;
  ctx.loop.add('modes', t => modes.tick(t));
  ctx.loop.start();

  const errors: string[] = [];
  const photos: ModesKit['photos'] = [];
  ctx.events.on('error', e => errors.push(e.message));
  ctx.events.on('photo', e => photos.push(e));
  window.__viewer = {
    get mode() { return modes.mode; }, state: modes.state, probe: modes.probe, setMode: modes.setMode, goToFloor: modes.goToFloor,
    takePhoto: modes.takePhoto, lock: modes.lock,
  };
  window.__host = {
    FL: Object.fromEntries(ctx.floors.map(f => [f.key, { key: f.key, name: f.name, level: f.modelLevel, group: f.group, colliders: f.colliders, walkables: f.walkables, late: f.late, rise: f.rise }])),
    floors: ctx.floors, model, openings: model.openings, probes: model.probes, labels: [], upHit: ctx.readouts.upHit, downHit: ctx.readouts.downHit,
    rayHit: ctx.readouts.rayHit, cast: ctx.readouts.cast, furniture: null, camera: ctx.camera, controls: ctx.controls, pictures: null,
    rise: Object.fromEntries(ctx.floors.map(f => [f.key, f.rise])), plinths: ctx.built.plinths,
    groups: Object.fromEntries(ctx.floors.map(f => [f.key, f.group])), fitted: ctx.built.fitted,
  };
  (window as unknown as { __walkthrough: unknown }).__walkthrough = {
    THREE: { Vector2, Vector3, Raycaster, Box3, Plane, Matrix4, Quaternion, Euler, MathUtils, Color },
  };
  ctx.loop.frame();
  await new Promise(r => requestAnimationFrame(() => r(null)));
  window.__modes = { ready: true, model: name, ctx, modes, errors, photos, downloads };
}

main().catch(err => { window.__modes = { error: String(err && (err as Error).stack || err) }; });
