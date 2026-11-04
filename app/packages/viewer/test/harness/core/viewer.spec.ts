// Builder A (project `harness`): createViewer in headless Edge on the bank, hotel, suite, house and features fixtures with
// their presentations (whatever B, C and D have in their folders: the stubs or their real modules). Run from app/:
//   WT_WEB_PORT=5721 WT_TMP="$TEMP/wt-a" npx playwright test -c tests/e2e/playwright.config.ts --project=harness packages/viewer/test/harness/core
import { expect, test, type Page } from '@playwright/test';

const STAMPS: Record<string, string> = {
  'bank-v1': '4b02dc17f286', 'bank-v2': 'c3a9408304a2', hotel: '6ab030750886', suite: 'f1b95c53eb3d', house: 'e43270cc0c9b', features: '0123456789ab',
};
const FLOORS: Record<string, string[]> = {
  'bank-v1': ['L1', 'L2'], 'bank-v2': ['L1', 'L2'], hotel: ['F1', 'F2'], suite: ['suite'], house: ['ground', 'upper'], features: ['G', 'U'],
};

/** Opens the core harness page; collects page errors, console errors and the viewer's own warnings. */
async function open(page: Page, query: string): Promise<string[]> {
  const errors: string[] = [];
  page.on('pageerror', e => errors.push(`[exception] ${e.message}`));
  page.on('console', m => {
    if (m.type() === 'error' && !/favicon/.test(m.text()) && !/favicon\.ico$/.test(m.location().url)) errors.push(`[console.error] ${m.text()}`);
    if (m.type() === 'warning' && /\[viewer\] dispose left/.test(m.text())) errors.push(`[console.warn] ${m.text()}`);
  });
  await page.goto(`/core/viewer.html${query}`);
  await page.waitForFunction(() => !!window.__core && window.__core.status !== 'loading', undefined, { timeout: 90_000 });
  return errors;
}

for (const key of Object.keys(STAMPS)) {
  test(`${key}: createViewer mounts, draws and is ready; dispose leaves the page as it was`, async ({ page }) => {
    const errors = await open(page, `?project=${key}&build=0&nodownload=1`);
    const status = await page.evaluate(() => ({ status: window.__core!.status, error: window.__core!.error ?? null }));
    expect(status).toEqual({ status: 'ready', error: null });
    const facts = await page.evaluate(() => {
      const app = document.getElementById('app')!, root = app.querySelector('[data-wt=root]') as HTMLElement | null;
      const canvas = root?.querySelector('canvas') ?? null, w = window.__walkthrough!, h = window.__host!;
      return {
        roots: document.querySelectorAll('[data-wt=root]').length, rootInApp: root?.parentElement === app, wtv: root?.classList.contains('wtv'),
        canvases: document.querySelectorAll('canvas').length, canvasInRoot: canvas?.parentElement === root,
        stamp: root?.getAttribute('data-model-stamp') ?? null, panel: !!root?.querySelector('[data-wt=panel]'),
        hint: !!root?.querySelector('[data-wt=hint]'), live: w.live(), mode: w.viewer.mode, disposed: w.viewer.disposed,
        floors: h.floors.map(f => f.key), visible: h.floors.map(f => f.group.visible),
        buffer: canvas ? [canvas.width, canvas.height] : null, root: root ? [root.clientWidth, root.clientHeight] : null, dpr: devicePixelRatio,
        drawn: w.gpu().geometries, build: window.__build ? window.__build.phase : null,
        fl: Object.values(h.FL).map(f => [f.key, f.level]), walk: h.floors.map(f => [f.key, f.level]),
        aspect: h.camera.aspect, far: h.camera.far,
      };
    });
    expect(facts).toMatchObject({ roots: 1, rootInApp: true, wtv: true, canvases: 1, canvasInRoot: true, stamp: STAMPS[key], panel: true, hint: true,
      live: 1, mode: 'orbit', disposed: false, floors: FLOORS[key] });
    expect(facts.visible.every(Boolean)).toBe(true);
    expect(facts.buffer).toEqual(facts.root!.map(v => Math.round(v * Math.min(facts.dpr, 2))));
    expect(facts.aspect).toBeCloseTo(facts.root![0]! / facts.root![1]!, 6);
    expect(facts.drawn).toBeGreaterThan(5);                                   // the first frame uploaded the meshes
    expect(facts.fl).toEqual(facts.walk);                                     // no Build settings change: model = Walk levels
    if (facts.build !== null) expect(facts.build).toBe('done');               // ?build=0: the replay skipped (D's start('skip'))

    const left = await page.evaluate(() => {
      const w = window.__walkthrough!, viewer = w.viewer;
      window.__wtvMount!.unmount();
      return {
        roots: document.querySelectorAll('[data-wt=root], .wtv').length, canvases: document.querySelectorAll('canvas').length,
        app: document.getElementById('app')!.childNodes.length, sheets: document.adoptedStyleSheets.length,
        styles: [...document.querySelectorAll('style')].filter(s => /\.wtv/.test(s.textContent ?? '')).length,
        hooks: ['__viewer', '__host', '__build', '__walkthrough'].filter(k => k in window), live: w.live(), gpu: w.gpu(), disposed: viewer.disposed,
      };
    });
    expect(left).toEqual({ roots: 0, canvases: 0, app: 0, sheets: 0, styles: 0, hooks: [], live: 0, gpu: { geometries: 0, textures: 0, programs: expect.any(Number) }, disposed: true });
    expect(errors).toEqual([]);
  });
}

test('the hotel: both plan pictures read before ready, the Plan picture tick off; ?picture=1 shows both sheets', async ({ page }) => {
  const errors = await open(page, '?project=hotel&build=0&nodownload=1');
  const off = await page.evaluate(async () => ({ ready: await window.__host!.pictures!.ready, sheets: window.__host!.pictures!.objs.map(m => [m.name, m.visible]),
    toggles: window.__walkthrough!.viewer.getToggles() }));
  expect(off).toEqual({ ready: [true, true], sheets: [['F1 plan picture', false], ['F2 plan picture', false]], toggles: { plates: true, glass: true, rooms: true, single: true, picture: false } });
  await page.goto('/core/viewer.html?project=hotel&build=0&nodownload=1&picture=1');
  await page.waitForFunction(() => window.__core?.status === 'ready');
  await page.waitForFunction(() => window.__host!.pictures!.objs.every(m => m.visible));
  const on = await page.evaluate(() => window.__host!.pictures!.objs.map(m => (m.material as unknown as { map: { image: HTMLImageElement } }).map.image.naturalWidth));
  expect(on).toEqual([1498, 882]);
  expect(errors).toEqual([]);
});

test('the window resizes: the drawing buffer and the camera follow the root (bus resize)', async ({ page }) => {
  await open(page, '?project=bank-v2&build=0&nodownload=1');
  await page.setViewportSize({ width: 1000, height: 640 });
  await page.waitForFunction(() => (document.querySelector('[data-wt=root] canvas') as HTMLCanvasElement).width === Math.round(1000 * Math.min(devicePixelRatio, 2)));
  const after = await page.evaluate(() => ({ aspect: window.__host!.camera.aspect, h: (document.querySelector('[data-wt=root] canvas') as HTMLCanvasElement).height, dpr: devicePixelRatio }));
  expect(after.aspect).toBeCloseTo(1000 / 640, 6);
  expect(after.h).toBe(Math.round(640 * Math.min(after.dpr, 2)));
});

test('an error in a frame hook shows in the error box and the error event, and the loop goes on', async ({ page }) => {
  await open(page, '?project=bank-v2&build=0&nodownload=1');
  const r = await page.evaluate(async () => {
    const v = window.__walkthrough!.viewer, seen: string[] = [];
    v.on('error', e => seen.push(e.message));
    const frames0 = () => new Promise<void>(res => requestAnimationFrame(() => requestAnimationFrame(() => res())));
    await frames0();
    const label = window.__host!.labels.find(l => l.el.style.display === 'block')!;      // a label placed every frame (top floor)
    Object.defineProperty(label.el.style, 'left', { configurable: true, set() { throw new Error('a label could not move'); }, get() { return ''; } });
    const frames = () => new Promise<void>(res => requestAnimationFrame(() => requestAnimationFrame(() => res())));
    await frames(); await frames();
    const box = document.querySelector('[data-wt=error]') as HTMLElement;
    const before = window.__walkthrough!.gpu().geometries;
    await frames();
    return { seen: [...new Set(seen)], text: box.textContent, shown: !box.hidden && getComputedStyle(box).display !== 'none', running: before > 0 };
  });
  expect(r.seen).toEqual(['a label could not move']);
  expect(r.text).toBe('Viewer error: a label could not move');
  expect(r.shown).toBe(true);
  expect(r.running).toBe(true);
});

test('failures leave nothing behind: a broken model, a detached container, WebGL refused, testFailAt at every step', async ({ page }) => {
  const errors = await open(page, '?project=bank-v2&nomount=1');
  const r = await page.evaluate(() => {
    const core = window.__core!, project = core.project!, app = document.getElementById('app')!;
    const state = () => ({ app: app.childNodes.length, roots: document.querySelectorAll('.wtv').length, canvases: document.querySelectorAll('canvas').length,
      sheets: document.adoptedStyleSheets.length, hooks: ['__viewer', '__host', '__build', '__walkthrough'].filter(k => k in window) });
    const out: Record<string, unknown> = {};
    try { core.createViewer(app, { ...project, model: { ...project.model, photoName: 'not allowed' } }); out.broken = 'no throw'; }
    catch (e) { out.broken = { name: (e as Error).name, paths: (e as InstanceType<typeof core.ModelError>).issues.map(i => i.path), ...state() }; }
    try { core.createViewer(document.createElement('div'), project); out.detached = 'no throw'; }
    catch (e) { out.detached = { message: (e as Error).message, ...state() }; }
    const get = HTMLCanvasElement.prototype.getContext;
    HTMLCanvasElement.prototype.getContext = function (this: HTMLCanvasElement, type: string, ...a: unknown[]) {
      return /webgl/.test(type) ? null : (get as (...x: unknown[]) => unknown).call(this, type, ...a);
    } as typeof get;
    out.webgl = { message: window.__wtvMount!.mount(), ...state() };
    HTMLCanvasElement.prototype.getContext = get;
    out.steps = (['context', 'build', 'panel', 'modes', 'furniture', 'replay', 'labels', 'start'] as const).map(step => ({ step, message: window.__wtvMount!.mount({ testFailAt: step }), ...state() }));
    out.ok = window.__wtvMount!.mount();
    out.mounted = state();
    window.__wtvMount!.unmount();
    out.after = state();
    return out;
  });
  const empty = { app: 0, roots: 0, canvases: 0, sheets: 0, hooks: [] };
  expect(r.broken).toEqual({ name: 'ModelError', paths: ['/photoName'], ...empty });
  expect(r.detached).toEqual({ message: expect.stringMatching(/not in the document/), ...empty });
  expect(r.webgl).toEqual({ message: expect.stringMatching(/WebGL/), ...empty });
  expect(r.steps).toEqual(['context', 'build', 'panel', 'modes', 'furniture', 'replay', 'labels', 'start'].map(step => ({ step, message: `[viewer] testFailAt ${step}`, ...empty })));
  expect(r.ok).toBeNull();
  expect(r.mounted).toMatchObject({ roots: 1, canvases: 1, sheets: 1 });
  expect(r.after).toEqual(empty);
  expect(errors.filter(e => !/WebGL|THREE\.WebGLRenderer/.test(e))).toEqual([]);
});

test('the Viewer handle: modechange only on a change; heightschange only for typed and reset; setHeights / getHeights, ticks and floors', async ({ page }) => {
  const errors = await open(page, '?project=bank-v2&build=0&nodownload=1');
  const r = await page.evaluate(() => {
    const v = window.__walkthrough!.viewer, h = window.__host!, modes: string[] = [], heights: string[] = [];
    v.on('modechange', e => modes.push(`${e.mode}:${e.floor}`));
    const sorted = (m: Record<string, number>) => JSON.stringify(Object.fromEntries(Object.entries(m).sort(([a], [b]) => (a < b ? -1 : 1))));
    const off = v.on('heightschange', e => heights.push(`${e.source} ${sorted(e.heights)}`));
    v.setMode('walk'); v.setMode('walk'); v.goToFloor('L2'); v.goToFloor('L2'); v.setMode('orbit'); v.openCamera(true); v.openCamera(false);
    const out: Record<string, unknown> = { modes: [...modes], mode: v.mode };
    v.setHeights({ table: 600, nonsense: 5, chair: 'x' as unknown as number });     // unknown kinds and bad values ignored, no event
    out.afterSet = v.getHeights();
    v.furniture!.setHeight('seat', 300);                                            // the legend's typing path: 'typed'
    v.furniture!.setVisible('plant', false);                                        // a tick: no event
    v.furniture!.reset();                                                           // 'reset'
    out.afterReset = v.getHeights();
    off();
    v.furniture!.setHeight('seat', 450);                                            // after off(): not seen
    v.furniture!.reset();
    out.heights = heights;
    v.setToggle('glass', false);
    out.toggles = v.getToggles();
    out.glassShown = h.floors.flatMap(f => f.group.children).filter(o => / glass:/.test(o.name)).some(o => o.visible);
    v.setToggle('glass', true);
    v.showFloors('L1');
    out.visible = h.floors.map(f => f.group.visible);
    v.showFloors('all');
    out.replay = v.replay ? v.replay.phase : null;
    return out;
  });
  expect(r.modes).toEqual(['walk:L1', 'walk:L2', 'orbit:L2']);
  expect(r.mode).toBe('orbit');
  expect(r.afterSet).toEqual({ table: 600 });
  expect(r.heights).toEqual(['typed {"seat":300,"table":600}', 'reset {}']);
  expect(r.afterReset).toEqual({});
  expect(r.toggles).toMatchObject({ glass: false, plates: true });
  expect(r.glassShown).toBe(false);
  expect(r.visible).toEqual([true, false]);
  expect(r.replay).toBe('done');
  expect(errors).toEqual([]);
});

test('the start-up order: with stages the replay starts on its settings screen (D), and room names wait for it', async ({ page }) => {
  await open(page, '?project=bank-v2&nodownload=1');
  const r = await page.evaluate(() => ({ build: window.__build ? window.__build.phase : null, viewer: window.__walkthrough!.viewer.replay?.phase ?? null,
    labels: window.__host!.labels.filter(l => l.el.style.display === 'block').length, toggles: window.__walkthrough!.viewer.getToggles() }));
  if (r.build === null) test.info().annotations.push({ type: 'replay', description: 'installReplay is still the stub (null): no build screen' });
  else {
    expect(r.build).toBe('settings');
    expect(r.viewer).toBe('settings');
    expect(r.labels).toBe(0);                                                  // labels only when the replay is done
  }
  expect(r.toggles).toEqual({ plates: true, glass: true, rooms: true, single: true, picture: false });
});
