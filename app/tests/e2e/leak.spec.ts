// Builder A (DESIGN.md 17.4 "New"; 11.2, 11.8): mount / unmount the viewer 20 times on one page, and mounts that fail;
// after each, the page is back at its baseline: live WebGL contexts (a getContext counter installed before anything ran,
// a context counted live until it is lost), listener REGISTRATIONS on window, document and the container (a set keyed by
// target, type, listener and capture, from wrapped add / removeEventListener; removals of registrations it never saw are
// ignored, as OrbitControls' disconnect() removes listeners it may never have added), no .wtv element, no viewer stylesheet
// (adopted or <style>), no window hook, no '[viewer] dispose left' warning, and gpu() 0 / 0 once disposed. The failing
// mounts: WebGL refused (the renderer throws after the root exists) and testFailAt at each later init step (11.4).
// Where: the core harness page when the harness server runs (WT_SERVE=harness: builder A's own run), else the offline file
// of the bank v2 (E2E_TARGET=app, ?test=1: the offline entry installs the same window.__wtvMount).
//   WT_SERVE=harness WT_WEB_PORT=5721 WT_TMP="$TEMP/wt-a" E2E_TARGET=prototype npx playwright test -c tests/e2e/playwright.config.ts --project=e2e tests/e2e/leak.spec.ts
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { expect, test, type Page } from '@playwright/test';
import { isApp, pageUrl, VERSIONS } from './lib/target';

interface LeakProbe {
  contexts(): number;
  registrations(): string[];
  failWebGL(on: boolean): void;
}
declare global {
  interface Window {
    __wtvMount?: { mount(extra?: Record<string, unknown>): string | null; unmount(): void; readonly viewer: { ready: Promise<void> } | null };
    __leak?: LeakProbe;
    __core?: { status: string; error?: string };
  }
}

const serve = new Set((process.env.WT_SERVE ?? '').split(',').map(s => s.trim()).filter(Boolean));
const OFFLINE_DIR = process.env.WT_OFFLINE_DIR ?? null;            // another folder of offline files than dist/offline
const bankV2 = (query: string) => OFFLINE_DIR
  ? pathToFileURL(path.join(OFFLINE_DIR, `${VERSIONS['bank-v2'].projectId}-v${VERSIONS['bank-v2'].version}.html`)).href + query
  : pageUrl('bank-v2', query);
const onHarness = serve.has('harness');
const MOUNTS = 20;
const STEPS = ['context', 'build', 'panel', 'modes', 'furniture', 'replay', 'labels', 'start'] as const;

test.skip(!onHarness && !isApp, 'needs the core harness page (WT_SERVE=harness) or the offline files (E2E_TARGET=app)');

/** Installed before any page script: the WebGL context counter and the listener registration set. */
function installProbe(containerId: string) {
  const contexts: WebGLRenderingContext[] = [];
  let refuse = false;
  const getContext = HTMLCanvasElement.prototype.getContext;
  HTMLCanvasElement.prototype.getContext = function (this: HTMLCanvasElement, type: string, ...rest: unknown[]) {
    if (/webgl/i.test(type) && refuse) return null;
    const gl = (getContext as (...a: unknown[]) => unknown).call(this, type, ...rest) as WebGLRenderingContext | null;
    if (gl && /webgl/i.test(type) && !contexts.includes(gl)) contexts.push(gl);
    return gl;
  } as typeof getContext;
  const regs = new Set<string>();
  const ids = new WeakMap<object, number>();
  let next = 1;
  const idOf = (o: object) => { let id = ids.get(o); if (!id) ids.set(o, (id = next++)); return id; };
  const where = (t: EventTarget) => (t === window ? 'window' : t === document ? 'document' : (t as Element).id === containerId ? 'container' : null);
  const key = (t: EventTarget, type: string, fn: unknown, opts: unknown) => {
    const w = where(t);
    if (!w || !fn || (typeof fn !== 'function' && typeof fn !== 'object')) return null;
    const capture = typeof opts === 'boolean' ? opts : !!(opts && (opts as { capture?: boolean }).capture);
    return `${w} ${type} #${idOf(fn as object)} ${capture ? 'capture' : 'bubble'}`;
  };
  const add = EventTarget.prototype.addEventListener, remove = EventTarget.prototype.removeEventListener;
  EventTarget.prototype.addEventListener = function (this: EventTarget, type: string, fn: EventListenerOrEventListenerObject | null, opts?: boolean | AddEventListenerOptions) {
    const k = key(this, type, fn, opts);
    if (k) regs.add(k);
    return add.call(this, type, fn, opts);
  };
  EventTarget.prototype.removeEventListener = function (this: EventTarget, type: string, fn: EventListenerOrEventListenerObject | null, opts?: boolean | EventListenerOptions) {
    const k = key(this, type, fn, opts);
    if (k) regs.delete(k);                          // a registration never seen: nothing to delete (ignored)
    return remove.call(this, type, fn, opts);
  };
  (window as unknown as { __leak: LeakProbe }).__leak = {
    contexts: () => contexts.filter(gl => !gl.isContextLost()).length,
    registrations: () => [...regs].sort(),
    failWebGL: on => { refuse = on; },
  };
}

interface PageState { contexts: number; registrations: string[]; wtv: number; roots: number; adopted: number; styles: number; hooks: string[]; container: number }
const state = (page: Page, containerId: string) => page.evaluate(id => ({
  contexts: window.__leak!.contexts(),
  registrations: window.__leak!.registrations(),
  wtv: document.querySelectorAll('.wtv').length,
  roots: document.querySelectorAll('[data-wt=root]').length,
  adopted: document.adoptedStyleSheets.length,
  styles: [...document.querySelectorAll('style')].filter(s => /\.wtv\b/.test(s.textContent ?? '')).length,
  hooks: ['__viewer', '__host', '__build', '__walkthrough'].filter(k => k in window),
  container: document.getElementById(id)!.childNodes.length,
}) as PageState, containerId);

test('20 mounts and unmounts on one page, and mounts that fail, leave nothing behind', async ({ page }) => {
  test.setTimeout(600_000);
  const containerId = onHarness ? 'app' : 'wtv-app';
  const warnings: string[] = [];
  const errors: string[] = [];
  page.on('console', m => {
    if (m.type() === 'warning' && /\[viewer\] dispose left/.test(m.text())) warnings.push(m.text());
    if (m.type() === 'error' && !/WebGL|favicon/.test(m.text()) && !/favicon\.ico$/.test(m.location().url)) errors.push(m.text());
  });
  page.on('pageerror', e => errors.push(`[exception] ${e.message}`));
  await page.addInitScript(installProbe, containerId);
  if (onHarness) {
    await page.goto('/core/viewer.html?project=bank-v2&build=0&nodownload=1&nomount=1');
    await page.waitForFunction(() => window.__core?.status === 'loaded' || window.__core?.status === 'error');
    expect(await page.evaluate(() => window.__core!.error ?? null)).toBeNull();
  } else {
    await page.goto(bankV2('?test=1&build=0&nodownload=1'));
    await page.waitForFunction(() => !!window.__wtvMount?.viewer);
    await page.evaluate(() => window.__wtvMount!.viewer!.ready);
    await page.evaluate(() => window.__wtvMount!.unmount());             // the file mounts at load: take the baseline after it
  }
  const baseline = await state(page, containerId);
  expect(baseline).toMatchObject({ contexts: 0, wtv: 0, roots: 0, styles: 0, hooks: [], container: 0 });

  for (let i = 0; i < MOUNTS; i++) {
    const mounted = await page.evaluate(async () => {
      const failed = window.__wtvMount!.mount();
      if (failed !== null) return { failed };
      await window.__wtvMount!.viewer!.ready;
      await new Promise<void>(r => requestAnimationFrame(() => requestAnimationFrame(() => r())));
      return { failed: null, contexts: window.__leak!.contexts(), gpu: window.__walkthrough!.gpu(), live: window.__walkthrough!.live() };
    });
    expect(mounted, `mount ${i + 1}`).toMatchObject({ failed: null, contexts: baseline.contexts + 1, live: 1 });
    const gone = await page.evaluate(() => {
      const w = window.__walkthrough!;
      window.__wtvMount!.unmount();
      return { gpu: w.gpu(), live: w.live() };
    });
    expect(gone, `unmount ${i + 1}`).toMatchObject({ gpu: { geometries: 0, textures: 0 }, live: 0 });
    expect(await state(page, containerId), `after unmount ${i + 1}`).toEqual(baseline);
  }

  // the failing mounts: WebGL refused (after the root exists), then testFailAt at the start of each init step
  await page.evaluate(() => window.__leak!.failWebGL(true));
  const refused = await page.evaluate(() => window.__wtvMount!.mount());
  await page.evaluate(() => window.__leak!.failWebGL(false));
  expect(refused).toMatch(/WebGL/);
  expect(await state(page, containerId), 'after WebGL was refused').toEqual(baseline);
  for (const step of STEPS) {
    const message = await page.evaluate(s => window.__wtvMount!.mount({ testFailAt: s }), step);
    expect(message).toBe(`[viewer] testFailAt ${step}`);
    expect(await state(page, containerId), `after testFailAt ${step}`).toEqual(baseline);
  }
  // and it still mounts after all that
  expect(await page.evaluate(async () => { const f = window.__wtvMount!.mount(); if (!f) await window.__wtvMount!.viewer!.ready; return f; })).toBeNull();
  await page.evaluate(() => window.__wtvMount!.unmount());
  expect(await state(page, containerId)).toEqual(baseline);
  expect(warnings).toEqual([]);
  expect(errors).toEqual([]);
});

// Integration (F-5): a host may take the container out of the document BEFORE it calls dispose() (React removes a page's
// DOM before its effect cleanups run). OrbitControls' capturing keydown listener sits on the document; dispose must still
// find it. The container goes back afterwards only so that the page state can be compared with the baseline.
test('dispose after the host detached the container leaves nothing behind', async ({ page }) => {
  test.setTimeout(300_000);
  const containerId = onHarness ? 'app' : 'wtv-app';
  const warnings: string[] = [];
  page.on('console', m => { if (m.type() === 'warning' && /\[viewer\] dispose left/.test(m.text())) warnings.push(m.text()); });
  await page.addInitScript(installProbe, containerId);
  if (onHarness) {
    await page.goto('/core/viewer.html?project=bank-v2&build=0&nodownload=1&nomount=1');
    await page.waitForFunction(() => window.__core?.status === 'loaded' || window.__core?.status === 'error');
  } else {
    await page.goto(bankV2('?test=1&build=0&nodownload=1'));
    await page.waitForFunction(() => !!window.__wtvMount?.viewer);
    await page.evaluate(() => window.__wtvMount!.viewer!.ready);
    await page.evaluate(() => window.__wtvMount!.unmount());
  }
  const baseline = await state(page, containerId);
  for (let i = 0; i < 3; i++) {
    expect(await page.evaluate(async () => { const f = window.__wtvMount!.mount(); if (!f) await window.__wtvMount!.viewer!.ready; return f; })).toBeNull();
    await page.evaluate(id => {
      const c = document.getElementById(id)!, parent = c.parentNode!, next = c.nextSibling;
      c.remove();                                                   // the host detaches first ...
      window.__wtvMount!.unmount();                                 // ... then disposes
      parent.insertBefore(c, next);
    }, containerId);
    expect(await state(page, containerId), `after detached unmount ${i + 1}`).toEqual(baseline);
  }
  expect(warnings).toEqual([]);
});

// Step BX (docs/boxes/DESIGN.md 8.5 "Leak"): a viewer that edits the furniture boxes (options.editBoxes, as the staff app's
// version page makes it) goes with nothing left behind either, also with a box selected (the marker and the card), one
// deleted from the card and the Restore list open when it goes: the marker's geometries and materials, the card, the line
// at the bottom, the list and their listeners (the window pointerdown and keydown of select.ts among them). The box is
// selected the way the viewer selects a restored box (a restore in Orbit selects it when it is showing), so the check does
// not depend on where the camera looks; the delete and the list are real clicks.
test('a viewer that edits the boxes: a box selected, deleted from its card and the Restore list open, then unmounted, leaves nothing behind', async ({ page }) => {
  test.setTimeout(300_000);
  const containerId = onHarness ? 'app' : 'wtv-app';
  const warnings: string[] = [];
  const errors: string[] = [];
  page.on('console', m => {
    if (m.type() === 'warning' && /\[viewer\] dispose left/.test(m.text())) warnings.push(m.text());
    if (m.type() === 'error' && !/WebGL|favicon/.test(m.text()) && !/favicon\.ico$/.test(m.location().url)) errors.push(m.text());
  });
  page.on('pageerror', e => errors.push(`[exception] ${e.message}`));
  await page.addInitScript(installProbe, containerId);
  if (onHarness) {
    await page.goto('/core/viewer.html?project=bank-v2&build=0&nodownload=1&nomount=1');
    await page.waitForFunction(() => window.__core?.status === 'loaded' || window.__core?.status === 'error');
    expect(await page.evaluate(() => window.__core!.error ?? null)).toBeNull();
  } else {
    await page.goto(bankV2('?test=1&build=0&nodownload=1'));
    await page.waitForFunction(() => !!window.__wtvMount?.viewer);
    await page.evaluate(() => window.__wtvMount!.viewer!.ready);
    await page.evaluate(() => window.__wtvMount!.unmount());
  }
  const baseline = await state(page, containerId);
  for (let i = 0; i < 2; i++) {
    expect(await page.evaluate(async () => {
      const failed = window.__wtvMount!.mount({ editBoxes: true });
      if (failed === null) await window.__wtvMount!.viewer!.ready;
      return failed;
    }), `mount ${i + 1}`).toBeNull();
    const selected = await page.evaluate(async () => {
      const h = window.__host!, F = h.furniture!, all = F.pieces();
      const p = all.find(q => !q.on && !all.some(r => r.on === q.id) && q.visible)!;
      F.removePiece(p.id);
      F.restorePiece(p.id);                                          // back, and the selection in Orbit
      await new Promise<void>(r => requestAnimationFrame(() => requestAnimationFrame(() => r())));
      return { id: p.id, marker: !!h.floors[0]!.group.parent!.getObjectByName('furniture-selection')?.visible };
    });
    expect(selected.marker, `the marker on ${selected.id}`).toBe(true);
    await expect(page.locator('[data-wt=box-card]')).toBeVisible();
    await page.locator('[data-wt=box-delete]').click();
    await expect(page.locator('[data-wt=box-card] [data-wt=box-kind]')).toContainText('Deleted:');
    await page.locator('[data-wt=boxes-restore-open]').click();
    await expect(page.locator('[data-wt=boxes-restore]')).toBeVisible();
    expect(await page.evaluate(() => Object.keys(window.__walkthrough!.viewer.getPieceEdits()).length)).toBe(1);
    const gone = await page.evaluate(() => {
      const w = window.__walkthrough!;
      window.__wtvMount!.unmount();
      return { gpu: w.gpu(), live: w.live() };
    });
    expect(gone, `unmount ${i + 1}`).toMatchObject({ gpu: { geometries: 0, textures: 0 }, live: 0 });
    expect(await state(page, containerId), `after unmount ${i + 1}`).toEqual(baseline);
  }
  expect(warnings).toEqual([]);
  expect(errors).toEqual([]);
});
