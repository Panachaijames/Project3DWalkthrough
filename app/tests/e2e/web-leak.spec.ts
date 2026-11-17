// Mount / unmount through the staff web app's route changes (DESIGN.md 17.4 "New", the web part; WORK_BREAKDOWN F): the
// list and a project page in turn (StrictMode mounts each page's viewer twice: 10 round trips are 20 mounts), then version
// switches on one page, then mounts that fail. After each, against the baseline taken on the list: live WebGL contexts
// (a getContext counter installed before the app), listener registrations on window, document and the viewer's container
// (a set keyed by target, type, listener and capture, from wrapped add / removeEventListener; removals of registrations
// it never saw are ignored), no `.wtv` element, no viewer stylesheet in document.adoptedStyleSheets, no `<style>` left,
// no window hook left, no `[viewer] dispose left` warning, and the test hook's gpu() at 0 / 0 once a viewer is disposed.
// Same set-ups as web.spec.ts (apps/web/test/e2e/web-kit.ts): the real API and viewer at integration, the mock API and
// the fake viewer for builder F alone.
import { expect, test, type Page } from '@playwright/test';
import { pickVersion, useApi, viewerReady } from '../../apps/web/test/e2e/web-kit';
import { TARGET } from './lib/target';

test.skip(TARGET === 'prototype', 'the web specs run against the staff app (E2E_TARGET=app)');
useApi();

interface WebLeakProbe {
  liveContexts(): number;
  setFailWebgl(on: boolean): void;
  /** Registrations now, as text ('window keydown capture #3'), sorted. */
  registrations(): string[];
  /** The viewer container's registrations now. */
  containerRegistrations(): number;
  mark(): void;
  /** Registrations added / removed since mark(). */
  diff(): { added: string[]; removed: string[] };
  /** gpu() of each instrumented viewer right after its dispose (null when gpu() could not be read then). */
  gpuAfterDispose: ({ geometries: number; textures: number } | null)[];
  /** How many viewers instrument() wrapped. */
  instrumented: number;
  /** Wraps the current viewer's dispose to read gpu() after it; false when the handle cannot be wrapped. */
  instrument(): boolean;
}
declare global {
  interface Window { __webLeak?: WebLeakProbe }
}

/** Installed before any page script (page.addInitScript). Plain JS in the page. */
function installLeakProbe(): void {
  type Reg = { target: EventTarget; type: string; fn: unknown; capture: boolean; id: number };
  const contexts = new Set<{ isContextLost(): boolean }>();
  let failWebgl = false;
  const getContext = HTMLCanvasElement.prototype.getContext;
  (HTMLCanvasElement.prototype as unknown as { getContext: (...a: unknown[]) => unknown }).getContext = function (this: HTMLCanvasElement, ...args: unknown[]) {
    const type = String(args[0]);
    if (/webgl/i.test(type) && failWebgl) return null;
    const ctx = (getContext as unknown as (...a: unknown[]) => unknown).apply(this, args);
    if (ctx && /webgl/i.test(type)) contexts.add(ctx as { isContextLost(): boolean });
    return ctx;
  };

  const regs: Reg[] = [];
  let nextId = 1;
  const fnIds = new WeakMap<object, number>();
  const fnId = (fn: unknown) => {
    if (typeof fn !== 'function' && (typeof fn !== 'object' || fn === null)) return 0;
    let id = fnIds.get(fn as object);
    if (!id) { id = nextId++; fnIds.set(fn as object, id); }
    return id;
  };
  const watched = (t: EventTarget) => t === window || t === document
    || (t instanceof Element && t.getAttribute('data-testid') === 'viewer-host');
  const captureOf = (o: unknown) => (typeof o === 'boolean' ? o : !!(o && typeof o === 'object' && (o as { capture?: unknown }).capture));
  const find = (t: EventTarget, type: string, fn: unknown, capture: boolean) =>
    regs.findIndex(r => r.target === t && r.type === type && r.fn === fn && r.capture === capture);
  const drop = (t: EventTarget, type: string, fn: unknown, capture: boolean) => {
    const i = find(t, type, fn, capture);
    if (i >= 0) regs.splice(i, 1);
  };
  const add = EventTarget.prototype.addEventListener;
  const remove = EventTarget.prototype.removeEventListener;
  EventTarget.prototype.addEventListener = function (this: EventTarget, type: string, fn: EventListenerOrEventListenerObject | null, opts?: boolean | AddEventListenerOptions) {
    if (fn && watched(this)) {
      const capture = captureOf(opts);
      const o = typeof opts === 'object' ? opts : undefined;
      if (find(this, type, fn, capture) < 0 && !o?.signal?.aborted) {
        regs.push({ target: this, type, fn, capture, id: fnId(fn) });
        const target = this;
        // listeners removed without removeEventListener: `once` after it fires, `signal` when it aborts
        if (o?.once) add.call(target, type, () => drop(target, type, fn, capture), { once: true, capture });
        o?.signal?.addEventListener('abort', () => drop(target, type, fn, capture), { once: true });
      }
    }
    return add.call(this, type, fn, opts);
  };
  EventTarget.prototype.removeEventListener = function (this: EventTarget, type: string, fn: EventListenerOrEventListenerObject | null, opts?: boolean | EventListenerOptions) {
    if (fn && watched(this)) drop(this, type, fn, captureOf(opts));
    return remove.call(this, type, fn, opts);
  };

  const targetName = (t: EventTarget) => (t === window ? 'window' : t === document ? 'document' : 'container');
  const text = (r: Reg) => `${targetName(r.target)} ${r.type}${r.capture ? ' capture' : ''} #${r.id}`;
  let baseline: Reg[] = [];
  const same = (a: Reg, b: Reg) => a.target === b.target && a.type === b.type && a.fn === b.fn && a.capture === b.capture;
  const gpuAfterDispose: ({ geometries: number; textures: number } | null)[] = [];

  const probe: WebLeakProbe = {
    liveContexts: () => [...contexts].filter(c => !c.isContextLost()).length,
    setFailWebgl: on => { failWebgl = on; },
    registrations: () => regs.filter(r => !(r.target instanceof Element)).map(text).sort(),
    containerRegistrations: () => regs.filter(r => r.target instanceof Element).length,
    mark: () => { baseline = regs.slice(); },
    diff: () => ({
      added: regs.filter(r => !baseline.some(b => same(b, r))).map(text),
      removed: baseline.filter(b => !regs.some(r => same(b, r))).map(text),
    }),
    gpuAfterDispose,
    instrumented: 0,
    instrument: () => {
      const w = window.__walkthrough;
      if (!w?.viewer) return false;
      const viewer = w.viewer as unknown as { dispose(): void; readonly disposed: boolean; __leakWrapped?: boolean };
      if (viewer.__leakWrapped) return true;
      const gpu = w.gpu;
      const dispose = viewer.dispose;
      try {
        viewer.dispose = function wrappedDispose(this: unknown) {
          // dispose() is idempotent and may be called again (the staff app's ViewerHost disposes on unmount in a layout
          // cleanup, then its effect cleanup calls it once more): read gpu() only after the call that disposed
          const first = !viewer.disposed;
          dispose.call(viewer);
          if (!first) return;
          let g: { geometries: number; textures: number } | null = null;
          try { const m = gpu(); g = { geometries: m.geometries, textures: m.textures }; } catch { /* not readable after dispose */ }
          gpuAfterDispose.push(g);
        };
        viewer.__leakWrapped = true;
      } catch {
        return false;   // a frozen handle: the console warning check still covers its dispose
      }
      if (viewer.dispose === dispose) return false;
      probe.instrumented++;
      return true;
    },
  };
  window.__webLeak = probe;
}

interface Baseline { contexts: number; sheets: number; styles: number }

async function baseline(page: Page): Promise<Baseline> {
  await page.evaluate(() => window.__webLeak!.mark());
  return page.evaluate(() => ({
    contexts: window.__webLeak!.liveContexts(),
    sheets: document.adoptedStyleSheets.length,
    styles: document.querySelectorAll('style').length,
  }));
}

/** Everything back to the baseline taken on the list (call on the list, after the page left). */
async function expectBaseline(page: Page, base: Baseline, warnings: string[], label: string): Promise<void> {
  // Radix may still be animating a menu closed: its listeners and scroll-lock style go when it unmounts
  await expect.poll(() => page.evaluate(() => document.querySelectorAll('[data-slot=select-content], [data-slot=dropdown-menu-content]').length)).toBe(0);
  const now = await page.evaluate(() => ({
    contexts: window.__webLeak!.liveContexts(),
    sheets: document.adoptedStyleSheets.length,
    styles: document.querySelectorAll('style').length,
    wtv: document.querySelectorAll('.wtv').length,
    hooks: ['__walkthrough', '__viewer', '__host', '__build'].filter(k => k in window),
    diff: window.__webLeak!.diff(),
  }));
  expect(now, label).toEqual({ ...base, wtv: 0, hooks: [], diff: { added: [], removed: [] } });
  expect(warnings, label).toEqual([]);
}

async function openLeakPage(page: Page): Promise<{ base: Baseline; warnings: string[] }> {
  const warnings: string[] = [];
  page.on('console', m => { if (m.text().includes('[viewer] dispose left')) warnings.push(m.text()); });
  await page.addInitScript(installLeakProbe);
  await page.goto('/projects');
  await expect(page.locator(['bank-sampeng', 'hotel-lobby', 'presidential-suite', 'sukhumvit-house'].map(id => `[data-testid=project-card][data-project-id="${id}"]`).join(', '))).toHaveCount(4);   // the four seeded projects' cards (U-15.3: e2e-* projects may be listed too)
  // Playwright's own helper script in the page's main world (made by the first page.waitForFunction, which viewerReady
  // uses) puts capture listeners and `__playwright_global_listeners_check__` on window for the life of the page: make it
  // now, so they are part of the baseline and not counted as the app's.
  await page.waitForFunction(() => true);
  await page.waitForTimeout(300);   // the app settles (queries, router) before the baseline
  return { base: await baseline(page), warnings };
}

async function openFromList(page: Page, projectId: string): Promise<void> {
  const created = await page.evaluate(() => window.__walkthrough?.created() ?? 0);
  await page.locator(`[data-testid=project-card][data-project-id="${projectId}"] [data-testid=card-link]`).click();
  await expect(page).toHaveURL(new RegExp(`/projects/${projectId}/v/\\d+$`));
  await viewerReady(page, created + 1);
  expect(await page.evaluate(() => [window.__walkthrough!.live(), document.querySelectorAll('canvas').length, window.__webLeak!.liveContexts()])).toEqual([1, 1, 1]);
  await page.evaluate(() => window.__webLeak!.instrument());
}

/** gpu() read right after each instrumented dispose: 0 geometries and 0 textures (one entry per instrumented viewer). */
async function expectGpuFreed(page: Page): Promise<void> {
  const { instrumented, after } = await page.evaluate(() => ({ instrumented: window.__webLeak!.instrumented, after: window.__webLeak!.gpuAfterDispose }));
  expect(after.length).toBe(instrumented);
  expect(after.filter(g => g !== null && (g.geometries !== 0 || g.textures !== 0))).toEqual([]);
}

async function backToList(page: Page): Promise<void> {
  await page.getByTestId('back-to-projects').click();
  await expect(page).toHaveURL(/\/projects$/);
  await expect(page.locator(['bank-sampeng', 'hotel-lobby', 'presidential-suite', 'sukhumvit-house'].map(id => `[data-testid=project-card][data-project-id="${id}"]`).join(', '))).toHaveCount(4);   // the four seeded projects' cards (U-15.3: e2e-* projects may be listed too)
}

test('20 mounts through route changes (list and project pages in turn) leave nothing behind', async ({ page }) => {
  test.setTimeout(300_000);
  const { base, warnings } = await openLeakPage(page);
  expect(base.contexts).toBe(0);
  for (let i = 0; i < 10; i++) {
    await openFromList(page, i % 2 ? 'hotel-lobby' : 'bank-sampeng');   // the hotel's plan pictures are textures
    await backToList(page);
    await expectBaseline(page, base, warnings, `round trip ${i + 1}`);
  }
  expect(await page.evaluate(() => window.__walkthrough?.created() ?? -1)).toBe(-1);   // no hook left on the list
  await expectGpuFreed(page);
});

test('10 version switches on one page keep one viewer and one context, and leave nothing behind', async ({ page }) => {
  test.setTimeout(300_000);
  const { base, warnings } = await openLeakPage(page);
  await openFromList(page, 'bank-sampeng');
  // the registrations of one live viewer (window, document by type; the container by count): the same after every switch
  const kinds = (regs: string[]) => regs.map(r => r.replace(/ #\d+$/, '')).sort();
  const one = await page.evaluate(() => ({ container: window.__webLeak!.containerRegistrations(), registrations: window.__webLeak!.registrations() }));
  // Step BX: the version page edits the furniture boxes (options.editBoxes), and the box selection (viewer
  // furniture/select.ts) adds two window listeners where a version has boxes (keydown: Delete, Ctrl+Z, Escape;
  // pointerdown, capture: arms Delete). The bank's version 2 has 185 boxes, version 1 none (no furniture module there):
  // version 1 is expected with exactly those two fewer, version 2 as opened.
  const BOX_SELECT = ['window keydown', 'window pointerdown capture'];
  const without = (regs: string[], drop: string[]) => {
    const out = [...regs];
    for (const d of drop) { const at = out.indexOf(d); if (at >= 0) out.splice(at, 1); }
    return out;
  };
  for (let i = 0; i < 10; i++) {
    const created = await page.evaluate(() => window.__walkthrough!.created());
    const v = i % 2 ? 2 : 1;
    await pickVersion(page, v);
    await viewerReady(page, created + 1);
    await expect.poll(() => page.evaluate(() => document.querySelectorAll('[data-slot=select-content]').length)).toBe(0);
    const now = await page.evaluate(() => ({
      live: window.__walkthrough!.live(),
      canvases: document.querySelectorAll('canvas').length,
      contexts: window.__webLeak!.liveContexts(),
      roots: document.querySelectorAll('.wtv').length,
      container: window.__webLeak!.containerRegistrations(),
      registrations: window.__webLeak!.registrations(),
    }));
    const label = `switch ${i + 1} (version ${v})`;
    const want = v === 2 ? kinds(one.registrations) : without(kinds(one.registrations), BOX_SELECT);
    expect({ ...now, registrations: kinds(now.registrations) }, label)
      .toEqual({ live: 1, canvases: 1, contexts: 1, roots: 1, container: one.container, registrations: want });
    await page.evaluate(() => window.__webLeak!.instrument());
  }
  await backToList(page);
  await expectBaseline(page, base, warnings, 'after the switches');
  await expectGpuFreed(page);
});

test('a viewer that fails to start (no WebGL) leaves nothing behind; Try again then works', async ({ page }) => {
  test.setTimeout(180_000);
  const { base, warnings } = await openLeakPage(page);
  await page.evaluate(() => window.__webLeak!.setFailWebgl(true));
  await page.locator('[data-testid=project-card][data-project-id="bank-sampeng"] [data-testid=card-link]').click();
  await expect(page.getByTestId('viewer-error')).toBeVisible({ timeout: 60_000 });
  const failed = await page.evaluate(() => ({
    contexts: window.__webLeak!.liveContexts(),
    sheets: document.adoptedStyleSheets.length,
    wtv: document.querySelectorAll('.wtv').length,
    canvases: document.querySelectorAll('canvas').length,
    hooks: ['__walkthrough', '__viewer', '__host', '__build'].filter(k => k in window),
  }));
  expect(failed).toEqual({ contexts: 0, sheets: base.sheets, wtv: 0, canvases: 0, hooks: [] });
  await backToList(page);
  await expectBaseline(page, base, warnings, 'after the failed mount');
  // the same page again with WebGL back: Try again makes the viewer
  await page.locator('[data-testid=project-card][data-project-id="bank-sampeng"] [data-testid=card-link]').click();
  await expect(page.getByTestId('viewer-error')).toBeVisible({ timeout: 60_000 });
  await page.evaluate(() => window.__webLeak!.setFailWebgl(false));
  await page.getByTestId('viewer-retry').click();
  await viewerReady(page, 1);
  await expect(page.getByTestId('viewer-error')).toHaveCount(0);
  expect(await page.evaluate(() => [window.__walkthrough!.live(), window.__webLeak!.liveContexts()])).toEqual([1, 1]);
  await backToList(page);
  await expectBaseline(page, base, warnings, 'after Try again');
});
