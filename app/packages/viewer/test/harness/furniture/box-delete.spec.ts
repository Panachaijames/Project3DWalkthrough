// Builder C, step BX (docs/boxes/DESIGN.md 2.2 - 2.8; Playwright project `harness`): deleting a furniture box in the REAL
// viewer (createViewer with its real modes, replay and photos; the core harness page /core/viewer.html, mounted here with
// options.editBoxes), in headless Edge with real WebGL, a real mouse and real keys:
//   WT_WEB_PORT=5750 WT_TMP="$TEMP/wt-bx" npx playwright test -c tests/e2e/playwright.config.ts --project=harness packages/viewer/test/harness/furniture/box-delete.spec.ts
// furniture.spec.ts covers the furniture module alone on the shared test context (no modes, no replay); the staff app and
// the saved record are the browser spec's (tests/e2e/box-delete.spec.ts).
import { expect, test, type Page } from '@playwright/test';
import type { PieceEditMap, ViewerEvents, ViewerOptions } from '../../../src/contracts';

declare global { interface Window { __bx?: { boxes: ViewerEvents['boxeschange'][]; shots: Blob[] } } }

const R = { removed: true } as const;

/** Opens the core page without mounting, puts `edits` in the project and mounts with `options` (the test hook is on). */
async function mount(page: Page, project: string, options: ViewerOptions, edits?: PieceEditMap): Promise<string[]> {
  const errors: string[] = [];
  page.on('pageerror', e => errors.push(`[exception] ${e.message}`));
  page.on('console', m => {
    if (m.type() === 'error' && !/favicon/.test(m.text()) && !/favicon\.ico$/.test(m.location().url)) errors.push(`[console.error] ${m.text()}`);
    if (m.type() === 'warning' && /\[viewer\] dispose left/.test(m.text())) errors.push(`[console.warn] ${m.text()}`);
  });
  await page.setViewportSize({ width: 1366, height: 768 });
  await page.goto(`/core/viewer.html?project=${project}&nomount=1`);
  await page.waitForFunction(() => !!window.__core && window.__core.status !== 'loading', undefined, { timeout: 90_000 });
  const failed = await page.evaluate(async ({ options, edits }) => {
    const core = window.__core!;
    if (core.status !== 'loaded') return `the page did not load: ${core.error}`;
    if (edits) core.project!.pieceEdits = edits;
    window.__bx = { boxes: [], shots: [] };
    const bad = window.__wtvMount!.mount({ ...options, download: (blob: Blob) => { window.__bx!.shots.push(blob); } });
    if (bad !== null) return bad;
    const viewer = window.__wtvMount!.viewer!;
    viewer.on('boxeschange', e => window.__bx!.boxes.push(e));
    await viewer.ready;
    return null;
  }, { options, edits });
  expect(failed).toBeNull();
  return errors;
}

/** What the page shows now (after two frames): the marked box, the card, the line at the bottom, the edits. */
const state = (page: Page) => page.evaluate(async () => {
  await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(() => r(null))));
  const h = window.__host!, F = h.furniture!, scene = h.floors[0]!.group.parent!;
  const marker = scene.getObjectByName('furniture-selection') ?? null;
  let on: string | null = null;
  if (marker?.visible) {
    const e = marker.matrix.elements;
    for (const p of F.pieces()) {
      const m = F.meshOf(p.id)!;
      m.updateWorldMatrix(true, false);
      const w = m.matrixWorld.elements;
      if (Math.abs(w[12]! - e[12]!) < 1e-6 && Math.abs(w[14]! - e[14]!) < 1e-6 && Math.abs(w[13]! - e[13]!) < 0.05) on = p.id;
    }
    on ??= 'somewhere else';
  }
  const text = (wt: string) => { const el = document.querySelector<HTMLElement>(`[data-wt=${wt}]`); return el && getComputedStyle(el).display !== 'none' && getComputedStyle(el).visibility !== 'hidden' ? el.innerText : null; };
  return {
    hasMarker: !!marker, marker: on, card: text('box-card'), toast: text('box-toast'), line: text('furniture-removed'),
    edits: Object.keys(window.__walkthrough!.viewer.getPieceEdits()), mode: window.__viewer!.mode,
    events: window.__bx!.boxes.map(e => [e.source, Object.keys(e.pieceEdits).length] as [string, number]),
  };
});
/** Client coordinates of a spot on the top of a box, `along` m from its middle along its long axis. */
const topOf = (page: Page, id: string, along = 0) => page.evaluate(({ id, along }) => {
  const h = window.__host!, p = h.furniture!.pieces().find(q => q.id === id)!, r = p.rot * Math.PI / 180;
  const fl = h.floors.find(f => f.key === p.floor)!;
  h.camera.updateMatrixWorld();
  const v = new (window.__walkthrough!.THREE.Vector3)(p.x + along * Math.cos(r), fl.modelLevel + p.z1, -(p.y + along * Math.sin(r))).project(h.camera);
  const b = document.querySelector('[data-wt=root]')!.getBoundingClientRect();
  return [b.left + (v.x + 1) / 2 * b.width, b.top + (1 - v.y) / 2 * b.height] as [number, number];
}, { id, along });
/** The view from above, level 2 alone (as the furniture harness looks at the mini model). */
const fromAbove = (page: Page) => page.evaluate(() => {
  const h = window.__host!;
  window.__walkthrough!.viewer.showFloors('L2');
  h.camera.position.set(0, 40, 8); h.controls.target.set(0, 0, 0); h.controls.update(); h.camera.updateMatrixWorld();
});
/** How many pixels of a PNG (base64) are the marker's magenta. */
const magenta = (page: Page, png: string) => page.evaluate(async png => {
  const bytes = Uint8Array.from(atob(png), c => c.charCodeAt(0));
  const bmp = await createImageBitmap(new Blob([bytes], { type: 'image/png' }));
  const cv = document.createElement('canvas');
  cv.width = bmp.width; cv.height = bmp.height;
  const g = cv.getContext('2d')!;
  g.drawImage(bmp, 0, 0);
  const d = g.getImageData(0, 0, cv.width, cv.height).data;
  let n = 0;
  for (let i = 0; i < d.length; i += 4) if (d[i]! > 215 && d[i + 1]! < 110 && d[i + 2]! > 170) n++;
  return { n, width: cv.width, height: cv.height };
}, png);
const T2 = 'L2-table-001';

test('Orbit: a real click selects, Delete and Ctrl+Z work, boxeschange goes out for the viewer\'s own changes only; a photo never shows the marker', async ({ page }) => {
  const errors = await mount(page, 'mini', { editBoxes: true, furnitureHeights: 'host', build: 'skip' });
  await fromAbove(page);
  expect(await state(page)).toMatchObject({ hasMarker: true, marker: null, card: null, toast: null, line: null, edits: [], mode: 'orbit', events: [] });
  const at = await topOf(page, T2, -0.55);
  await page.mouse.click(...at);
  const sel = await state(page);
  expect(sel.marker).toBe(T2);
  expect(sel.card).toContain('Table / desk');
  expect(sel.card).toContain('Delete box (Del)');
  // the marker is drawn on the screen (around the box, away from the card), and in no photo
  const clip = { x: Math.max(0, at[0] - 120), y: Math.max(0, at[1] - 120), width: 240, height: 240 };
  const screen = await magenta(page, (await page.screenshot({ clip })).toString('base64'));
  expect(screen.n).toBeGreaterThan(30);
  const photo = await page.evaluate(async () => {
    const result = await window.__walkthrough!.viewer.takePhoto();
    const blob = window.__bx!.shots.at(-1)!, bytes = new Uint8Array(await blob.arrayBuffer());
    let s = '';
    for (const b of bytes) s += String.fromCharCode(b);
    return { result, png: btoa(s) };
  });
  expect(photo.result).toMatchObject({ width: 1920 });
  const inPhoto = await magenta(page, photo.png);
  expect(inPhoto).toMatchObject({ n: 0, width: 1920 });
  expect((await state(page)).marker).toBe(T2);                        // and it is back on the screen
  expect((await magenta(page, (await page.screenshot({ clip })).toString('base64'))).n).toBeGreaterThan(30);
  // P (the photo key) too
  await page.keyboard.press('p');
  await page.waitForFunction(() => window.__bx!.shots.length === 2);
  const second = await page.evaluate(async () => { const bytes = new Uint8Array(await window.__bx!.shots[1]!.arrayBuffer()); let s = ''; for (const b of bytes) s += String.fromCharCode(b); return btoa(s); });
  expect((await magenta(page, second)).n).toBe(0);
  // Delete, Ctrl+Z, and the events
  await page.keyboard.press('Delete');
  const gone = await state(page);
  expect(gone).toMatchObject({ marker: null, edits: ['L2-computer-001', T2], events: [['removed', 2]] });
  expect(gone.card).toContain('Deleted: Table / desk (+1 on it)');
  expect(gone.line).toContain('2 boxes deleted');
  await page.keyboard.press('Control+z');
  expect(await state(page)).toMatchObject({ marker: T2, edits: [], events: [['removed', 2], ['restored', 0]], line: null });
  // set from outside (a takeover from another tab): applied, closed, no event; unknown ids ignored
  const set = await page.evaluate(() => {
    const v = window.__walkthrough!.viewer;
    v.setPieceEdits({ 'L1-table-001': { removed: true }, 'L9-nothing': { removed: true } });
    return { edits: v.getPieceEdits(), same: v.getPieceEdits() === v.getPieceEdits() };
  });
  expect(set).toEqual({ edits: { 'L1-computer-001': R, 'L1-printer-001': R, 'L1-table-001': R }, same: false });
  expect((await state(page)).events.length).toBe(2);
  // the Camera panel opening clears the selection; a click with it open selects nothing
  await page.evaluate(() => window.__walkthrough!.viewer.openCamera(true));
  expect(await state(page)).toMatchObject({ marker: null, card: null });
  await page.evaluate(() => window.__walkthrough!.viewer.openCamera(false));
  // after dispose the handle is inert and nothing is left behind
  const after = await page.evaluate(() => {
    const v = window.__walkthrough!.viewer, F = v.furniture!;
    window.__wtvMount!.unmount();
    v.setPieceEdits({});
    return { removed: F.removePiece('L1-seat-001'), restored: F.restorePiece('L1-table-001'), edits: Object.keys(v.getPieceEdits()).length,
      left: document.querySelectorAll('[data-wt=box-card], [data-wt=box-toast], [data-wt=boxes-restore], [data-wt=root]').length };
  });
  expect(after).toEqual({ removed: [], restored: [], edits: 3, left: 0 });
  expect(errors).toEqual([]);
});

test('Walk and Ghost: the box at the crosshair carries the marker; Delete removes it (a line at the bottom, no collider); Ctrl+Z brings it back', async ({ page }) => {
  const errors = await mount(page, 'mini', { editBoxes: true, furnitureHeights: 'host', build: 'skip' });
  await page.mouse.click(1250, 700);                                  // a click on the canvas (in a session: the one that starts walking)
  // stand 2 m south of the chair L1-seat-001 and look at its top
  const aim = (id: string, from: [number, number]) => page.evaluate(async ({ id, from }) => {
    const v = window.__viewer!, h = window.__host!, s = v.state, p = h.furniture!.pieces().find(q => q.id === id)!;
    const x = p.x + from[0], z = -(p.y + from[1]);
    if (v.mode === 'orbit') v.setMode('walk', { floor: h.floors.find(f => f.key === p.floor)!, point: { x, z } });
    s.pos.x = x; s.pos.z = z;
    await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(() => r(null))));
    const dx = p.x - s.pos.x, dz = -p.y - s.pos.z, dy = h.floors.find(f => f.key === p.floor)!.level + p.z1 - s.pos.y;
    s.yaw = Math.atan2(-dx, -dz);
    s.pitch = Math.atan2(dy, Math.hypot(dx, dz));
    await new Promise(r => setTimeout(r, 400));                       // the aim is looked for 10 times a second
    const cross = document.querySelector<HTMLElement>('[data-wt=cross]');
    return { mode: v.mode, cross: !!cross && getComputedStyle(cross).display !== 'none', dist: Math.hypot(dx, dy, dz) };
  }, { id, from });
  const seat = 'L1-seat-001';
  const a = await aim(seat, [0, -2]);
  expect(a).toMatchObject({ mode: 'walk', cross: true });
  expect(a.dist).toBeLessThan(6);
  const aimed = await state(page);
  expect(aimed).toMatchObject({ marker: seat, card: null, toast: null, mode: 'walk' });
  const collider = () => page.evaluate(id => { const h = window.__host!; return h.floors[0]!.colliders.includes(h.furniture!.meshOf(id)!); }, seat);
  expect(await collider()).toBe(true);
  await page.keyboard.press('Delete');
  const gone = await state(page);
  expect(gone).toMatchObject({ edits: [seat], toast: 'Deleted: Chair / stool · Ctrl+Z to undo', card: null, mode: 'walk', events: [['removed', 1]] });
  expect(gone.marker).not.toBe(seat);
  expect(await collider()).toBe(false);                                // the walker can step into the place
  expect(await page.evaluate(() => { const t = document.querySelector<HTMLElement>('[data-wt=box-toast]')!, r = t.getBoundingClientRect(), hint = document.querySelector('[data-wt=hint]')!.getBoundingClientRect();
    return { z: getComputedStyle(t).zIndex, events: getComputedStyle(t).pointerEvents, aboveHint: hint.height === 0 || r.bottom <= hint.top + 0.5, centred: Math.abs((r.left + r.right) / 2 - innerWidth / 2) < 2 }; }))
    .toEqual({ z: '7', events: 'none', aboveHint: true, centred: true });
  await page.keyboard.press('Control+z');
  const back = await state(page);
  expect(back).toMatchObject({ edits: [], toast: 'Back: Chair / stool on Level 1', events: [['removed', 1], ['restored', 0]] });
  expect(await collider()).toBe(true);
  expect((await state(page)).marker).toBe(seat);                      // aimed at again
  // a box further than 6 m is not aimed at: Delete does nothing
  const farAway = await aim(seat, [0, -6.6]);
  if (farAway.dist > 6) {
    await page.keyboard.press('Delete');
    expect((await state(page)).edits).toEqual([]);
  }
  // Ghost the same
  await aim(seat, [0, -2]);
  await page.keyboard.press('3');
  await aim(seat, [0, -2]);
  expect(await state(page)).toMatchObject({ marker: seat, mode: 'ghost' });
  await page.keyboard.press('Delete');
  expect(await state(page)).toMatchObject({ edits: [seat], toast: 'Deleted: Chair / stool · Ctrl+Z to undo' });
  // back in Orbit: no aim marker. In Both floors the chair stands under Level 2's floor plate: the Restore list's Restore
  // brings it back without a marker (none drawn through the plate) and the card says where it is (review of 17 Nov)
  await page.keyboard.press('1');
  expect(await state(page)).toMatchObject({ marker: null, mode: 'orbit' });
  await page.evaluate(() => window.__walkthrough!.viewer.showFloors('all'));
  await page.locator('[data-wt=boxes-restore-open]').click();
  await page.locator('[data-wt=box-restore]').click();
  const under = await state(page);
  expect(under).toMatchObject({ marker: null, edits: [], line: null });
  expect(under.card).toContain('Back on Level 1 (under Level 2: press Level 1 to see it)');
  // Level 1 alone: the Restore list's Restore selects it; the card's button has no "(Del)": the press in the list disarmed the key
  await page.keyboard.press('Control+z');
  expect((await state(page)).edits).toEqual([seat]);
  await page.evaluate(() => window.__walkthrough!.viewer.showFloors('L1'));
  await page.locator('[data-wt=boxes-restore-open]').click();
  await page.locator('[data-wt=box-restore]').click();
  const restored = await state(page);
  expect(restored).toMatchObject({ marker: seat, edits: [], line: null });
  expect(restored.card).toContain('Chair / stool');
  expect(await page.locator('[data-wt=box-delete]').innerText()).toBe('Delete box');
  expect(errors).toEqual([]);
});

test('the build replay never shows a deleted box (saved in the project, or deleted while it runs); after it a selection shows the marker again', async ({ page }) => {
  // the client's file: the saved deletions, no editBoxes
  const errors = await mount(page, 'bank-v2', { build: 'play' }, { 'L1-table-001': R });
  const run = await page.evaluate(async () => {
    const h = window.__host!, F = h.furniture!, B = window.__build!;
    const gone = F.pieces().filter(p => p.removed).map(p => p.id), kept = F.pieces().find(p => !p.removed && p.kind === 'table')!.id;
    const seen: [number, boolean, boolean][] = [];
    for (const T of [0, 0.1, 0.3, 0.5, 0.7, 0.85, 0.93, 0.97, 0.99, 0.999, 1]) {
      B.seek(T);
      await new Promise(r => requestAnimationFrame(() => r(null)));
      seen.push([T, gone.some(id => F.meshOf(id)!.visible), F.meshOf(kept)!.visible]);
    }
    B.skip();
    await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(() => r(null))));
    return { gone, seen, phase: B.phase, after: [gone.some(id => F.meshOf(id)!.visible), F.meshOf(kept)!.visible],
      rows: document.querySelectorAll('[data-wt=furniture-row]').length, kinds: F.kinds().length,
      controls: document.querySelectorAll('[data-wt=box-card], [data-wt=box-toast], [data-wt=furniture-removed], [data-wt=furniture-edit-hint], [data-wt=boxes-restore]').length,
      marker: !!h.floors[0]!.group.parent!.getObjectByName('furniture-selection'), edits: Object.keys(window.__walkthrough!.viewer.getPieceEdits()) };
  });
  expect(run.gone.length).toBeGreaterThan(1);                         // the table and what stands on it
  expect(run.gone).toContain('L1-table-001');
  expect(run.seen.filter(([, goneShown]) => goneShown)).toEqual([]);  // never, at any moment of the replay
  expect(run.seen.at(-1)![2]).toBe(true);                             // the others fade in
  expect(run.seen[0]![2]).toBe(false);
  expect(run).toMatchObject({ phase: 'done', after: [false, true], controls: 0, marker: false });
  expect(run.edits).toEqual(run.gone.slice().sort((a, b) => run.edits.indexOf(a) - run.edits.indexOf(b)));
  expect(run.rows).toBeLessThanOrEqual(run.kinds);
  // a click on a box does nothing in the client's file
  await page.mouse.click(700, 420);
  expect(await page.locator('[data-wt=box-card]').count()).toBe(0);
  await page.evaluate(() => window.__wtvMount!.unmount());

  // the staff app: a box deleted from outside while the replay runs, then a selection after it
  const failed = await page.evaluate(async () => {
    delete window.__core!.project!.pieceEdits;                        // this version has no saved deletions
    const bad = window.__wtvMount!.mount({ editBoxes: true, furnitureHeights: 'host', build: 'skip', download: () => {} });
    if (bad === null) await window.__wtvMount!.viewer!.ready;
    return bad;
  });
  expect(failed).toBeNull();
  const staff = await page.evaluate(async () => {
    const h = window.__host!, F = h.furniture!, B = window.__build!, v = window.__walkthrough!.viewer;
    const frame = () => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(() => r(null))));
    const scene = h.floors[0]!.group.parent!, marker = scene.getObjectByName('furniture-selection')!;
    const card = () => { const c = document.querySelector<HTMLElement>('[data-wt=box-card]')!; return getComputedStyle(c).display !== 'none' && getComputedStyle(c).visibility !== 'hidden'; };
    const seat = F.pieces().find(p => p.kind === 'seat')!.id, plant = F.pieces().find(p => p.kind === 'plant')?.id ?? F.pieces().find(p => p.kind !== 'seat' && p.kind !== 'table' && !p.on)!.id;
    const out: Record<string, unknown> = { before: Object.keys(v.getPieceEdits()) };
    v.showFloors(F.pieces().find(p => p.id === seat)!.floor);         // its floor alone: in Both floors Level 2's plate hides it
    F.removePiece(seat); F.restorePiece(seat);                        // the restored box is the selection
    await frame();
    out.selected = [marker.visible, card()];
    v.replay!.openSettings();
    await frame();
    out.inSettings = [marker.visible, card(), B.phase];
    B.generate();
    B.seek(0.5);
    await frame();
    v.setPieceEdits({ [plant]: { removed: true }, 'L1-table-001': { removed: true } });   // a takeover mid-replay
    const shown: boolean[] = [];
    for (const T of [0.6, 0.9, 0.97, 0.995, 1]) { B.seek(T); await frame(); shown.push(F.meshOf(plant)!.visible || F.meshOf('L1-table-001')!.visible); }
    B.skip();
    await frame();
    out.shown = shown;
    out.afterReplay = [F.meshOf(plant)!.visible, F.meshOf(seat)!.visible, B.phase, marker.visible];
    v.setPieceEdits({});                                              // and back: drawn at their own look
    await frame();
    const mats = (id: string) => { const m = F.meshOf(id)!.material as { opacity: number; transparent: boolean }; return [F.meshOf(id)!.visible, m.opacity, m.transparent]; };
    out.back = [mats(plant), mats('L1-table-001')];
    F.removePiece(seat); F.restorePiece(seat);
    await frame();
    const line = (marker.children[1] as unknown as { material: { opacity: number; transparent: boolean } }).material;
    out.again = [marker.visible, card(), line.opacity, line.transparent];
    return out;
  });
  expect(staff).toEqual({
    before: [], selected: [true, true], inSettings: [false, false, 'settings'], shown: [false, false, false, false, false],
    afterReplay: [false, true, 'done', false], back: [[true, 1, false], [true, 1, false]], again: [true, true, 1, false],
  });
  expect(errors).toEqual([]);
});
