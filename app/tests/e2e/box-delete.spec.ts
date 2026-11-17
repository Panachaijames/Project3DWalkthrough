// Step BX (docs/boxes/DESIGN.md 8.5; docs/contract-issues/BX.md 3): deleting furniture boxes in the staff app, in
// headless Edge. Raw [data-wt=...] selectors: lib/target.ts is frozen.
//
// The real arm (the real API on a freshly seeded temp store, the real viewer; skipped with the mock API or the fake viewer):
//   * Orbit: a box clicked where the camera sees it (a spot on its top projected through __host.furniture.meshOf), the
//     card, Delete: the box and the one standing on it are gone (hidden, out of the colliders: a knee-high level ray passes
//     where the table stood), saved with the heights (one PUT {heights, pieceEdits}, "Furniture saved"), the app bar's count
//     visible without scrolling at 1366 x 768, still gone after a reload; the CSV without their rows and the 3ds Max script
//     without their lines, with the comment naming their Max objects (each compared with the mock API's copy of the API's
//     filter: apps/web/test/mock-api/core.ts csvWithout, filterMaxScript); the offline file never shows them during its
//     build replay (__build.seek up to 1: risk 4), marks them removed and has no edit control, a click on a box there shows
//     no card; Restore all, its Undo, Restore all again: the CSV and the Max script byte for byte as before, the offline
//     file without pieceEdits (its overrides' revision moved: not byte-equal) and every box drawn.
//   * Walk: entered at an address in front of a box (x, z, yaw, pitch found from the Walk start on L1), the box at the
//     crosshair marked, the click that starts walking, Delete: the line at the bottom, no collider, saved; Ctrl+Z brings it
//     back.
//   * The replay in the staff app: a box selected, Build settings, Generate, Skip; selected again: the marker shows at its
//     own look (the replay's fade never reaches it).
//   * Two tabs: a delete in one and a height typed in the other are both saved, and the other tab shows the deletion; the
//     first tab's next delete keeps the other's height.
// The mock arm (the fake viewer, VITE_FAKE_VIEWER=1, over the mock API or the real one): the fake remove control saves
// {heights, pieceEdits}; the 3ds Max script waits while that save is refused, and stays a link while only a height is.
// Every test starts and ends with the shared reset (web-kit resetHeights: {heights: {}, pieceEdits: {}}), so no deletion is
// left for web.spec.ts's byte-equal Max and CSV checks.
//
// Runs (Git Bash, from app/; the step's row: web 5750, API 8750, %TEMP%\wt-bx). The real arm needs the offline template of
// the viewer as it is now, given to the API; nobody writes dist/ while the batch is open, so it is built into the temp folder:
//   npx vite build -c packages/viewer/vite.offline.config.ts --outDir "$TEMP/wt-bx/offline-template"
//   WT_WEB_PORT=5750 WT_API_PORT=8750 WT_TMP="$TEMP/wt-bx" WT_SKIP_STORE_CHECK=1 \
//   WALKTHROUGH_OFFLINE_TEMPLATE="$TEMP/wt-bx/offline-template/viewer-template.html" \
//     npx playwright test -c tests/e2e/playwright.config.ts --project=e2e tests/e2e/box-delete.spec.ts
// The mock arm:
//   WT_WEB_PORT=5750 WT_API_PORT=8750 WT_TMP="$TEMP/wt-bx" WT_SERVE=web WT_SKIP_STORE_CHECK=1 VITE_FAKE_VIEWER=1 \
//     npx playwright test -c tests/e2e/playwright.config.ts --project=e2e tests/e2e/box-delete.spec.ts
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { expect, test, type Page } from '@playwright/test';
import type { PieceEditMap } from '../../packages/viewer/src/contracts';
import {
  backend,
  download,
  FAKE_VIEWER,
  heightBox,
  MOCK_API,
  offlinePayload,
  typeHeight,
  useApi,
  viewerReady,
} from '../../apps/web/test/e2e/web-kit';
import { csvWithout, filterMaxScript } from '../../apps/web/test/mock-api/core';
import { FIXTURES_DIR } from '../../apps/web/test/mock-api/fixtures';
import { TARGET } from './lib/target';

/* eslint-disable @typescript-eslint/no-explicit-any */

const P = 'bank-sampeng';
const N = 2;
const PAGE = `/projects/${P}/v/${N}`;
const SAVES = `/api/projects/${P}/versions/${N}/furniture-heights`;
/** The bank v2's working table L1-table-005 carries the computer L1-computer-001: deleting the table deletes both. */
const TABLE = 'L1-table-005';
const ON_TABLE = 'L1-computer-001';
const PLANT = 'L1-plant-001';
const R = { removed: true } as const;
/** The closed map of deleting the table (the furniture list's order: the computer's kind comes first). */
const TABLE_EDITS: PieceEditMap = { [ON_TABLE]: R, [TABLE]: R };
/** The real API and the real viewer (the integration run). */
const REAL = !MOCK_API && !FAKE_VIEWER;

interface KneeRay { floor: string; x: number; y: number; dx: number; dy: number; d: number; name: string }
interface WalkAim { id: string; label: string; x: number; z: number; yaw: number; pitch: number }
interface MarkerLook { visible: boolean; fill: [number, boolean]; line: [number, boolean] }
/** What the checks read in the page through the viewer's test hook (bxHelpers). */
interface Bxe {
  frames(n?: number): Promise<void>;
  /** Only the box's floor shown, the Orbit camera above the box looking down at it. */
  above(id: string): Promise<void>;
  /** A client point on the box's top where the camera's ray meets that box first, on the canvas itself; or null. */
  spot(id: string): [number, number] | null;
  /** The box the selection marker is on (null: no marker shown). */
  markerOn(): string | null;
  markerLook(): MarkerLook | null;
  /** The box is drawn (its mesh and every parent visible). */
  shown(id: string): boolean;
  /** The box is one of its floor's Walk colliders. */
  collider(id: string): boolean;
  /** A level ray at knee height (0.45 m) from beside the box towards it that meets that box first; or null. */
  knee(id: string): KneeRay | null;
  /** The same ray now. */
  ray(r: KneeRay): { d: number; name: string } | null;
  /** The viewer's deleted boxes, in its order. */
  edits(): string[];
  /** A canvas point (no overlay on it) away from the middle. */
  canvasSpot(): [number, number] | null;
  /** Walk on `floor` at its start: the nearest box (nothing on it, stopping Walk) within 5 m that nothing hides. */
  walkAim(floor: string): Promise<WalkAim | null>;
}
declare global {
  interface Window { __bxe?: Bxe }
}

/** Installed in a page before its scripts (addInitScript): every function reads the test hook when it is called. */
function bxHelpers(): void {
  const w = window as any;
  const showing = (o: any): boolean => { for (let n = o; n; n = n.parent) if (!n.visible) return false; return true; };
  const host = () => w.__host;
  const furn = () => w.__host.furniture;
  const piece = (id: string) => furn().pieces().find((q: any) => q.id === id);
  const canvas = (): HTMLCanvasElement => document.querySelector('[data-wt=root] canvas') as HTMLCanvasElement;
  const frames = (n = 2) => new Promise<void>(resolve => {
    const step = (k: number) => { if (k <= 0) resolve(); else requestAnimationFrame(() => step(k - 1)); };
    step(n);
  });
  // what the viewer's own pick looks through (packages/viewer/src/furniture/pick.ts): the boxes drawn and what hides them
  const targets = () => {
    const boxes = furn().pieces().map((p: any) => furn().meshOf(p.id)).filter((m: any) => m && showing(m));
    const hides = host().floors.filter((f: any) => showing(f.group)).flatMap((f: any) => f.colliders.concat(f.walkables))
      .filter((m: any) => {
        const mat = Array.isArray(m.material) ? m.material[0] : m.material;
        return !String(m.name).startsWith('furn:') && !!mat && mat.visible !== false && !mat.transparent && showing(m);
      });
    return [...boxes, ...hides];
  };
  const marker = () => host().floors[0].group.parent.getObjectByName('furniture-selection') ?? null;
  w.__bxe = {
    frames,
    async above(id: string) {
      const h = host(), m = furn().meshOf(id), V3 = w.__walkthrough.THREE.Vector3;
      w.__walkthrough.viewer.showFloors(piece(id).floor);
      for (let i = 0; i < 10; i++) {                                 // until the camera stays where it was put
        m.updateWorldMatrix(true, false);
        const c = new V3().setFromMatrixPosition(m.matrixWorld), want = new V3(c.x, c.y + 10, c.z + 1.5);
        h.controls.target.copy(c);
        h.camera.position.copy(want);
        h.controls.update();
        h.camera.updateMatrixWorld();
        await frames();
        if (i > 0 && h.camera.position.distanceTo(want) < 1e-3) return;
      }
    },
    spot(id: string): [number, number] | null {
      const THREE = w.__walkthrough.THREE, cam = host().camera, m = furn().meshOf(id), cv = canvas(), r = cv.getBoundingClientRect();
      m.updateWorldMatrix(true, false);
      cam.updateMatrixWorld();
      const ray = new THREE.Raycaster(), list = targets();
      const local = [[0, 0], [0.25, 0], [-0.25, 0], [0, 0.25], [0, -0.25], [0.35, 0.3], [-0.35, 0.3], [0.35, -0.3], [-0.35, -0.3], [0.4, 0], [-0.4, 0]];
      for (const [a, b] of local) {
        const ndc = m.localToWorld(new THREE.Vector3(a, 1, b)).project(cam);   // the unit box's top is y = 1
        if (Math.abs(ndc.x) > 0.95 || Math.abs(ndc.y) > 0.95) continue;
        ray.setFromCamera(new THREE.Vector2(ndc.x, ndc.y), cam);
        if (ray.intersectObjects(list, false)[0]?.object !== m) continue;
        const x = r.left + (ndc.x + 1) / 2 * r.width, y = r.top + (1 - ndc.y) / 2 * r.height;
        if (document.elementFromPoint(x, y) === cv) return [x, y];
      }
      return null;
    },
    markerOn(): string | null {
      const mk = marker();
      if (!mk || !mk.visible) return null;
      const e = mk.matrix.elements;
      for (const p of furn().pieces()) {
        const m = furn().meshOf(p.id);
        m.updateWorldMatrix(true, false);
        const q = m.matrixWorld.elements;
        if (Math.abs(q[12] - e[12]) < 1e-6 && Math.abs(q[14] - e[14]) < 1e-6 && Math.abs(q[13] - e[13]) < 0.05) return p.id;
      }
      return 'somewhere else';
    },
    markerLook() {
      const mk = marker();
      if (!mk) return null;
      const [fill, line] = mk.children;
      return { visible: !!mk.visible, fill: [fill.material.opacity, !!fill.material.transparent], line: [line.material.opacity, !!line.material.transparent] };
    },
    shown: (id: string) => showing(furn().meshOf(id)),
    collider(id: string) {
      const fl = host().floors.find((f: any) => f.key === piece(id).floor);
      return fl.colliders.includes(furn().meshOf(id));
    },
    knee(id: string) {
      const p = piece(id), rot = p.rot * Math.PI / 180, name = furn().meshOf(id).name;
      const along: [number, number] = [Math.cos(rot), Math.sin(rot)], across: [number, number] = [Math.sin(rot), -Math.cos(rot)];
      for (const [ax, half] of [[across, p.d / 2], [along, p.w / 2]] as [[number, number], number][]) {
        for (const sgn of [1, -1]) {
          const x = p.x + sgn * ax[0] * (half + 0.6), y = p.y + sgn * ax[1] * (half + 0.6), dx = -sgn * ax[0], dy = -sgn * ax[1];
          const hit = host().rayHit(p.floor, x, y, 0.45, dx, dy, 3);
          if (hit && hit.name === name) return { floor: p.floor, x, y, dx, dy, d: hit.d, name };
        }
      }
      return null;
    },
    ray: (r: any) => host().rayHit(r.floor, r.x, r.y, 0.45, r.dx, r.dy, 3),
    edits: () => Object.keys(w.__walkthrough.viewer.getPieceEdits()),
    canvasSpot(): [number, number] | null {
      const cv = canvas(), r = cv.getBoundingClientRect();
      for (const [fx, fy] of [[0.8, 0.3], [0.7, 0.25], [0.85, 0.55], [0.6, 0.2], [0.75, 0.7], [0.55, 0.65]]) {
        const x = r.left + fx! * r.width, y = r.top + fy! * r.height;
        if (document.elementFromPoint(x, y) === cv) return [x, y];
      }
      return null;
    },
    async walkAim(floor: string) {
      const THREE = w.__walkthrough.THREE, v = w.__viewer, s = v.state;
      v.setMode('walk', { floor: host().floors.find((f: any) => f.key === floor) });
      await frames();
      const eye = s.pos.clone(), ray = new THREE.Raycaster(), list = targets(), all = furn().pieces();
      const near = all
        .filter((p: any) => p.floor === floor && !p.on && p.blocking && !all.some((q: any) => q.on === p.id))
        .map((p: any) => {
          const m = furn().meshOf(p.id);
          m.updateWorldMatrix(true, false);
          const at = m.localToWorld(new THREE.Vector3(0, 0.6, 0));    // inside the box, a little below its top
          return { p, m, at, dist: at.distanceTo(eye) };
        })
        .filter((c: any) => showing(c.m) && c.dist > 1.5 && c.dist < 5)
        .sort((a: any, b: any) => a.dist - b.dist);
      for (const c of near) {
        const dir = c.at.clone().sub(eye).normalize();
        ray.set(eye, dir);
        ray.far = 6;
        if (ray.intersectObjects(list, false)[0]?.object !== c.m) continue;
        const label = furn().kinds().find((k: any) => k.key === c.p.kind).label;
        return { id: c.p.id, label, x: eye.x, z: eye.z, yaw: Math.atan2(-dir.x, -dir.z) * 180 / Math.PI, pitch: Math.asin(dir.y) * 180 / Math.PI };
      }
      return null;
    },
  } satisfies Bxe;
}

/** The bodies of the furniture saves the page sends, in order. */
function recordPuts(page: Page): unknown[] {
  const puts: unknown[] = [];
  page.on('request', r => {
    if (r.method() === 'PUT' && new URL(r.url()).pathname === SAVES) puts.push(r.postDataJSON());
  });
  return puts;
}

/** The furnBox lines of a 3ds Max script: the Max object name and the piece id of each, in the script's order. */
function furnBoxes(script: Buffer, prefix: string): { name: string; id: string }[] {
  const line = new RegExp(`^    ${prefix}_furnBox "[^"]*" "([^"]*)" \\d+ "([^"]*)" `);
  const out: { name: string; id: string }[] = [];
  for (const text of script.toString('latin1').split('\n')) {
    const m = line.exec(text);
    if (m) out.push({ name: m[1]!, id: m[2]! });
  }
  return out;
}

/** A downloaded offline file opened from disk in a new page of the same browser (no network), ready. */
async function openOffline(page: Page, file: string, query: string): Promise<Page> {
  const client = await page.context().newPage();
  await client.addInitScript(bxHelpers);
  await client.route(/^(?!file:|data:|blob:)/i, route => route.abort('blockedbyclient'));
  await client.goto(pathToFileURL(file).href + query);
  await client.waitForFunction(() => !!window.__walkthrough?.viewer, undefined, { timeout: 60_000 });
  await client.evaluate(() => window.__walkthrough!.viewer.ready);
  return client;
}

test.skip(TARGET === 'prototype', 'the staff app (E2E_TARGET=app)');
useApi();

test.beforeEach(async ({ request }) => { await backend(request).resetHeights(P, N); });
test.afterEach(async ({ request }) => { await backend(request).resetHeights(P, N); });

// ------------------------------------------------------------------------------------------------- the real API and viewer
test.describe('the real API and viewer', () => {
  test.skip(!REAL, 'the real API and the real viewer (WT_SERVE with api, VITE_FAKE_VIEWER unset)');
  test.use({ viewport: { width: 1366, height: 768 } });

  test('Orbit: a box clicked and deleted is gone and saved, after a reload too; the downloads leave it out; Restore all, Undo, Restore all: as before', async ({ page, request }, testInfo) => {
    test.setTimeout(480_000);
    const be = backend(request);
    const puts = recordPuts(page);
    await page.addInitScript(bxHelpers);
    await page.goto(PAGE);
    await viewerReady(page, 2);
    const prefix = await page.evaluate(() => window.__host!.model.maxPrefix);

    // the files as they are with nothing deleted
    const csv0 = (await download(page, 'furnitureCsv', testInfo)).bytes;
    expect(csv0.equals(readFileSync(path.join(FIXTURES_DIR, 'csv', 'bank-v2.csv'))), 'the CSV with nothing saved is the golden').toBe(true);
    const max0 = (await download(page, 'maxScript', testInfo)).bytes;
    const maxWithout = filterMaxScript(max0, prefix, [ON_TABLE, TABLE]);
    expect(maxWithout, 'one furnBox line each for the table and the computer').not.toBeNull();
    const names = furnBoxes(max0, prefix).filter(b => b.id === TABLE || b.id === ON_TABLE).map(b => b.name);
    expect(names).toHaveLength(2);

    // the table, seen from above on its floor alone, clicked where the camera sees it
    await page.evaluate(id => window.__bxe!.above(id), TABLE);
    const knee = await page.evaluate(id => window.__bxe!.knee(id), TABLE);
    expect(knee, 'a knee-high level ray that meets the table first').not.toBeNull();
    expect(await page.evaluate(id => window.__bxe!.collider(id), TABLE)).toBe(true);
    const at = await page.evaluate(id => window.__bxe!.spot(id), TABLE);
    expect(at, 'a spot on the table that the camera sees').not.toBeNull();
    await page.mouse.click(at![0], at![1]);
    const card = page.locator('[data-wt=box-card]');
    await expect(card).toBeVisible();
    await expect(card.locator('[data-wt=box-kind]')).toHaveText('Table / desk');
    await expect(card.locator('[data-wt=box-id]')).toHaveText(TABLE);
    await expect(card.locator('[data-wt=box-cascade]')).toHaveText('1 piece stands on it (Computer / monitor): it is deleted with it.');
    await expect(card.locator('[data-wt=box-delete]')).toHaveText('Delete box (Del)');
    expect(await page.evaluate(() => window.__bxe!.markerOn())).toBe(TABLE);

    // Delete: the table and the computer on it go at once: not drawn, no collider, the knee-high ray passes their place
    await page.keyboard.press('Delete');
    await expect(card.locator('[data-wt=box-kind]')).toHaveText('Deleted: Table / desk (+1 on it)');
    expect(await page.evaluate(() => window.__bxe!.edits())).toEqual([ON_TABLE, TABLE]);
    expect(await page.evaluate(ids => ids.map(id => [window.__bxe!.shown(id), window.__bxe!.collider(id)]), [TABLE, ON_TABLE]))
      .toEqual([[false, false], [false, false]]);
    expect(await page.evaluate(() => window.__bxe!.markerOn())).toBeNull();
    const through = await page.evaluate(r => window.__bxe!.ray(r), knee!);
    expect(through?.name ?? null).not.toBe(knee!.name);
    if (through) expect(through.d).toBeGreaterThan(knee!.d);

    // saved with the heights: one PUT, Furniture saved, and the count, which needs no scrolling at 1366 x 768
    await expect.poll(() => puts.length).toBe(1);
    expect(puts[0]).toEqual({ heights: {}, pieceEdits: TABLE_EDITS });
    await expect(page.getByTestId('heights-status-text')).toHaveText('Furniture saved');
    await expect(page.getByTestId('boxes-deleted')).toHaveText('· 2 boxes deleted');
    expect(await page.evaluate(() => {
      const el = document.querySelector('[data-testid=boxes-deleted]')!, r = el.getBoundingClientRect();
      const top = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
      return {
        inside: r.width > 0 && r.left >= 0 && r.top >= 0 && r.right <= innerWidth && r.bottom <= innerHeight,
        onTop: !!top && el.contains(top), scrolled: [scrollX, scrollY], wide: document.documentElement.scrollWidth <= innerWidth,
        size: [innerWidth, innerHeight],
      };
    })).toEqual({ inside: true, onTop: true, scrolled: [0, 0], wide: true, size: [1366, 768] });
    expect(await be.savedEdits(P, N)).toEqual(TABLE_EDITS);
    expect(await be.saved(P, N)).toEqual({});
    await expect(page.locator('[data-wt=furniture-removed]')).toContainText('2 boxes deleted');

    // a reload starts from the saved deletions
    await page.reload();
    await viewerReady(page, 2);
    expect(await page.evaluate(() => window.__bxe!.edits())).toEqual([ON_TABLE, TABLE]);
    expect(await page.evaluate(ids => ids.map(id => window.__bxe!.shown(id) || window.__bxe!.collider(id)), [TABLE, ON_TABLE])).toEqual([false, false]);
    await expect(page.getByTestId('boxes-deleted')).toHaveText('· 2 boxes deleted');

    // the CSV without their rows (every other row as before), the Max script without their lines and with the comment
    const csv1 = (await download(page, 'furnitureCsv', testInfo)).bytes;
    expect(csv1.equals(csvWithout(csv0, [ON_TABLE, TABLE])), 'the CSV is the one before without the two rows').toBe(true);
    expect(csv1.toString('utf8')).not.toContain(`\r\n${TABLE},`);
    const max1 = (await download(page, 'maxScript', testInfo)).bytes;
    expect(max1.equals(maxWithout!), 'the Max script is the stored one without the two lines, with the comment').toBe(true);
    const lines0 = max0.toString('latin1').split('\n'), lines1 = max1.toString('latin1').split('\n');
    expect(lines1[1]).toBe(lines0[1]);                                // line 2, the stamp, unchanged
    expect(lines1[2]).toMatch(/^-- 2 furniture boxes deleted in the walkthrough app are left out: /);
    for (const name of names) expect(lines1[2]).toContain(name);
    expect(furnBoxes(max1, prefix).filter(b => b.id === TABLE || b.id === ON_TABLE)).toEqual([]);
    expect(furnBoxes(max1, prefix)).toHaveLength(furnBoxes(max0, prefix).length - 2);

    // the offline file: the deletions in its payload, never drawn during its build replay, no edit control
    const off1 = await download(page, 'offlineHtml', testInfo);
    expect(offlinePayload(off1.bytes.toString('utf8')).overrides?.pieceEdits).toEqual(TABLE_EDITS);
    const client = await openOffline(page, off1.file, '?build=play&test=1&nodownload=1');
    const run = await client.evaluate(async ids => {
      const h = window.__host!, F = h.furniture!, B = window.__build!, frames = window.__bxe!.frames;
      const seen: [number, boolean][] = [];
      for (const T of [0, 0.2, 0.4, 0.6, 0.8, 0.9, 0.95, 0.98, 0.995, 1]) {
        B.seek(T);
        await frames(1);
        seen.push([T, ids.some(id => F.meshOf(id)!.visible)]);
      }
      B.skip();
      await frames();
      return {
        shownAt: seen.filter(([, shown]) => shown).map(([T]) => T),
        phase: B.phase,
        removed: F.pieces().filter(p => p.removed).map(p => p.id),
        drawn: ids.filter(id => F.meshOf(id)!.visible),
        controls: document.querySelectorAll('[data-wt=box-card], [data-wt=box-delete], [data-wt=box-toast], [data-wt=furniture-removed], [data-wt=furniture-edit-hint], [data-wt=boxes-restore]').length,
        marker: !!h.floors[0]!.group.parent!.getObjectByName('furniture-selection'),
      };
    }, [TABLE, ON_TABLE]);
    expect(run).toEqual({ shownAt: [], phase: 'done', removed: [ON_TABLE, TABLE], drawn: [], controls: 0, marker: false });
    // a click on a box in the client's file selects nothing
    await client.evaluate(id => window.__bxe!.above(id), 'L1-table-001');
    const there = await client.evaluate(id => window.__bxe!.spot(id), 'L1-table-001');
    expect(there, 'a spot on another table in the offline file').not.toBeNull();
    await client.mouse.click(there![0], there![1]);
    await client.waitForTimeout(300);
    expect(await client.locator('[data-wt=box-card], [data-wt=box-delete], [data-wt=furniture-removed]').count()).toBe(0);
    expect(await client.evaluate(() => window.__bxe!.markerOn())).toBeNull();
    await client.close();

    // Restore all, its Undo (the exact map back), Restore all again: one PUT each
    const line = page.locator('[data-wt=furniture-removed]');
    const list = page.locator('[data-wt=boxes-restore]');
    await page.locator('[data-wt=boxes-restore-open]').click();
    await expect(list).toBeVisible();
    await expect(list.locator('[data-wt=boxes-restore-row]')).toHaveCount(1);   // one line per group: the table, the computer folded in
    const row = list.locator(`[data-wt=boxes-restore-row][data-id="${TABLE}"]`);
    await expect(row).toContainText('Table / desk');
    await expect(row).toContainText('(+1 on it)');
    await list.locator('[data-wt=boxes-restore-all]').click();
    await expect(list).toBeHidden();
    await expect(line).toContainText('All 2 boxes are back');
    await expect.poll(() => puts.length).toBe(2);
    expect(puts[1]).toEqual({ heights: {}, pieceEdits: {} });
    await expect(page.getByTestId('boxes-deleted')).toHaveCount(0);
    await page.locator('[data-wt=boxes-restore-undo]').click();
    await expect(line).toContainText('2 boxes deleted');
    await expect.poll(() => puts.length).toBe(3);
    expect(puts[2]).toEqual({ heights: {}, pieceEdits: TABLE_EDITS });
    await expect(page.getByTestId('boxes-deleted')).toHaveText('· 2 boxes deleted');
    await page.locator('[data-wt=boxes-restore-open]').click();
    await list.locator('[data-wt=boxes-restore-all]').click();
    await expect.poll(() => puts.length).toBe(4);
    expect(puts[3]).toEqual({ heights: {}, pieceEdits: {} });
    await expect(page.getByTestId('heights-status-text')).toHaveText('Furniture saved');
    expect(await be.savedEdits(P, N)).toEqual({});
    expect(await page.evaluate(() => window.__bxe!.edits())).toEqual([]);
    expect(await page.evaluate(ids => ids.map(id => window.__bxe!.shown(id) && window.__bxe!.collider(id)), [TABLE, ON_TABLE])).toEqual([true, true]);

    // everything is back: the CSV and the Max script byte for byte as before; the offline file without pieceEdits, every box drawn
    expect((await download(page, 'furnitureCsv', testInfo)).bytes.equals(csv0), 'the CSV as before').toBe(true);
    expect((await download(page, 'maxScript', testInfo)).bytes.equals(max0), 'the Max script as before').toBe(true);
    const off2 = await download(page, 'offlineHtml', testInfo);
    const payload = offlinePayload(off2.bytes.toString('utf8'));
    expect(payload.overrides).not.toBeNull();
    expect(Object.keys(payload.overrides!)).not.toContain('pieceEdits');
    expect(payload.overrides!.revision).toBeGreaterThan(0);        // saved since the seed: not byte-equal to the file before
    const again = await openOffline(page, off2.file, '?build=0&nodownload=1&test=1');
    expect(await again.evaluate(ids => {
      const F = window.__host!.furniture!;
      return {
        removed: F.pieces().filter(p => p.removed).length,
        edits: Object.keys(window.__walkthrough!.viewer.getPieceEdits()).length,
        drawn: ids.map(id => F.meshOf(id)!.visible),
        live: F.kinds().reduce((n, k) => n + k.count, 0) === F.pieces().length,
      };
    }, [TABLE, ON_TABLE])).toEqual({ removed: 0, edits: 0, drawn: [true, true], live: true });
    await again.close();
  });

  test('Walk: entered at an address in front of a box, Delete at the crosshair, the line at the bottom; Ctrl+Z brings it back', async ({ page }) => {
    test.setTimeout(240_000);
    const puts = recordPuts(page);
    await page.addInitScript(bxHelpers);
    await page.goto(PAGE);
    await viewerReady(page, 2);
    const aim = await page.evaluate(() => window.__bxe!.walkAim('L1'));
    expect(aim, 'a box within 5 m of the Walk start on L1 that nothing hides').not.toBeNull();
    const a = aim!;
    const num = (v: number) => String(Math.round(v * 1e4) / 1e4);
    await page.goto(`${PAGE}?mode=walk&floor=L1&x=${num(a.x)}&z=${num(a.z)}&yaw=${num(a.yaw)}&pitch=${num(a.pitch)}`);
    await viewerReady(page, 2);
    expect(await page.evaluate(() => window.__walkthrough!.viewer.mode)).toBe('walk');
    await expect.poll(() => page.evaluate(() => window.__bxe!.markerOn())).toBe(a.id);   // the box at the crosshair is marked
    expect(await page.evaluate(id => window.__bxe!.collider(id), a.id)).toBe(true);
    // the click that starts walking (it arms Delete), then Delete at the crosshair
    const spot = await page.evaluate(() => window.__bxe!.canvasSpot());
    expect(spot, 'a canvas spot with nothing over it').not.toBeNull();
    await page.mouse.click(spot![0], spot![1]);
    await expect.poll(() => page.evaluate(() => window.__bxe!.markerOn())).toBe(a.id);   // the view did not move
    await page.keyboard.press('Delete');
    const toast = page.locator('[data-wt=box-toast]');
    await expect(toast).toHaveText(`Deleted: ${a.label} · Ctrl+Z to undo`);
    expect(await page.evaluate(() => window.__bxe!.edits())).toEqual([a.id]);
    expect(await page.evaluate(id => [window.__bxe!.shown(id), window.__bxe!.collider(id)], a.id)).toEqual([false, false]);
    expect(await page.evaluate(() => window.__walkthrough!.viewer.mode)).toBe('walk');
    await expect.poll(() => puts.length).toBe(1);
    expect(puts[0]).toEqual({ heights: {}, pieceEdits: { [a.id]: R } });
    await expect(page.getByTestId('boxes-deleted')).toHaveText('· 1 box deleted');
    // Ctrl+Z: back, a collider again, saved
    await page.keyboard.press('Control+z');
    await expect(toast).toHaveText(`Back: ${a.label} on Level 1`);
    expect(await page.evaluate(() => window.__bxe!.edits())).toEqual([]);
    expect(await page.evaluate(id => window.__bxe!.collider(id), a.id)).toBe(true);
    await expect.poll(() => puts.length).toBe(2);
    expect(puts[1]).toEqual({ heights: {}, pieceEdits: {} });
    await expect(page.getByTestId('heights-status-text')).toHaveText('Furniture saved');
    await expect(page.getByTestId('boxes-deleted')).toHaveCount(0);
  });

  test('the replay in the staff app: a box selected, Build settings, Generate, Skip; selected again, the marker shows at its own look', async ({ page }) => {
    test.setTimeout(240_000);
    await page.addInitScript(bxHelpers);
    await page.goto(PAGE);
    await viewerReady(page, 2);
    const phase = () => page.evaluate(() => window.__walkthrough!.viewer.replay!.phase);
    const select = async () => {
      await page.evaluate(id => window.__bxe!.above(id), TABLE);
      const at = await page.evaluate(id => window.__bxe!.spot(id), TABLE);
      expect(at, 'a spot on the table that the camera sees').not.toBeNull();
      await page.mouse.click(at![0], at![1]);
      await expect.poll(() => page.evaluate(() => window.__bxe!.markerOn())).toBe(TABLE);
      await expect(page.locator('[data-wt=box-card]')).toBeVisible();
    };
    await select();
    const look = await page.evaluate(() => window.__bxe!.markerLook());
    expect(look).toEqual({ visible: true, fill: [0.35, true], line: [1, false] });
    await page.locator('[data-wt=replay-open]').click();
    await expect.poll(phase).toBe('settings');
    expect(await page.evaluate(() => window.__bxe!.markerOn())).toBeNull();          // the replay clears the selection
    await expect(page.locator('[data-wt=box-card]')).toBeHidden();
    await page.locator('[data-wt=replay-go]').click();
    await expect.poll(phase).toBe('play');
    await page.waitForTimeout(1500);                                                 // the fade under way
    await page.locator('[data-wt=replay-skip]').click();
    await expect.poll(phase).toBe('done');
    await select();
    expect(await page.evaluate(() => window.__bxe!.markerLook())).toEqual(look);
    expect(await page.evaluate(() => window.__bxe!.edits())).toEqual([]);
  });

  test('two tabs: a delete in one and a height typed in the other are both saved, and each keeps the other\'s', async ({ page, request }) => {
    test.setTimeout(240_000);
    const be = backend(request);
    const a = page, b = await page.context().newPage();
    await a.goto(PAGE);
    await viewerReady(a, 2);
    await b.goto(PAGE);
    await viewerReady(b, 2);
    await a.evaluate(id => window.__walkthrough!.viewer.furniture!.removePiece(id), TABLE);
    await expect(a.getByTestId('boxes-deleted')).toHaveText('· 2 boxes deleted');
    await expect.poll(() => be.savedEdits(P, N)).toEqual(TABLE_EDITS);
    await typeHeight(b, 'seat', 300);                                 // B opened before A's delete: its {heights} keeps it
    await expect.poll(() => be.saved(P, N)).toEqual({ seat: 300 });
    expect(await be.savedEdits(P, N)).toEqual(TABLE_EDITS);
    await expect.poll(() => b.evaluate(() => Object.keys(window.__walkthrough!.viewer.getPieceEdits()))).toEqual([ON_TABLE, TABLE]);
    await expect(b.getByTestId('boxes-deleted')).toHaveText('· 2 boxes deleted');
    await expect(b.getByTestId('heights-status-text')).toHaveText('Furniture saved');
    await a.evaluate(id => window.__walkthrough!.viewer.furniture!.removePiece(id), PLANT);   // A's next delete keeps B's height
    await expect.poll(() => be.savedEdits(P, N)).toEqual({ ...TABLE_EDITS, [PLANT]: R });
    expect(await be.saved(P, N)).toEqual({ seat: 300 });
    await expect(heightBox(a, 'seat')).toHaveValue('300');            // A shows B's height (the merge, or the takeover)
    await expect(a.getByTestId('heights-status-text')).toHaveText('Furniture saved');
    await b.close();
  });
});

// --------------------------------------------------------------------------------------------------------- the fake viewer
test.describe('the fake viewer', () => {
  test.skip(!FAKE_VIEWER, "the fake viewer's remove control (VITE_FAKE_VIEWER=1)");

  test('the fake remove control: the PUT body is {heights, pieceEdits}; a height typed next goes as {heights}', async ({ page, request }) => {
    const be = backend(request);
    const puts = recordPuts(page);
    await page.goto(PAGE);
    await viewerReady(page, 2);
    await page.locator('[data-wt=fake-remove-box]').click();          // the first box not deleted yet: an ATM, nothing on it
    await expect(page.getByTestId('boxes-deleted')).toHaveText('· 1 box deleted');
    await expect.poll(() => puts.length).toBe(1);
    expect(puts[0]).toEqual({ heights: {}, pieceEdits: { 'L1-atm-001': R } });
    await expect(page.getByTestId('heights-status-text')).toHaveText('Furniture saved');
    expect(await be.savedEdits(P, N)).toEqual({ 'L1-atm-001': R });
    await typeHeight(page, 'seat', 300);
    await expect.poll(() => puts.length).toBe(2);
    expect(puts[1]).toEqual({ heights: { seat: 300 } });
    await expect(page.getByTestId('heights-status-text')).toHaveText('Furniture saved');
    expect(await be.savedEdits(P, N)).toEqual({ 'L1-atm-001': R });
    expect(await be.saved(P, N)).toEqual({ seat: 300 });
  });

  test('the 3ds Max script waits while a delete is refused, and stays a link while only a height is', async ({ page, request }) => {
    const be = backend(request);
    await page.goto(PAGE);
    await viewerReady(page, 2);
    let refusing = true;
    await page.route(url => url.pathname === SAVES, async route => {
      if (refusing && route.request().method() === 'PUT') {
        await route.fulfill({ status: 500, contentType: 'application/json', body: JSON.stringify({ error: { code: 'store_error', message: 'overrides.json could not be written (test)' } }) });
        return;
      }
      await route.fallback();
    });
    const status = page.getByTestId('heights-status-text');
    const list = page.getByTestId('downloads-list');
    const NOT_SAVED = 'Not saved: overrides.json could not be written (test)';
    // a height alone refused: the CSV and the offline file wait, the Max script stays a link (it carries no heights)
    await typeHeight(page, 'seat', 300);
    await expect(status).toHaveText(NOT_SAVED);
    await page.getByTestId('downloads-menu').click();
    await expect(list.locator('[data-download=furnitureCsv]')).toHaveAttribute('data-disabled', '');
    await expect(list.locator('[data-download=maxScript]')).not.toHaveAttribute('data-disabled', '');
    await expect(list.locator('[data-download=maxScript]')).toHaveAttribute('href', /\/downloads\/max-script$/);
    await page.keyboard.press('Escape');
    await expect(list).toHaveCount(0);
    // a delete refused too: now the Max script waits, with its own reason
    await page.locator('[data-wt=fake-remove-box]').click();
    await expect(status).toHaveText('Saving…');
    await expect(status).toHaveText(NOT_SAVED);
    await page.getByTestId('downloads-menu').click();
    await expect(list.locator('[data-download=maxScript]')).toHaveAttribute('data-disabled', '');
    await expect(list.locator('[data-download=maxScript]')).toHaveAttribute('title',
      'The deleted boxes on screen are not saved (overrides.json could not be written (test)): the script would still build them');
    await expect(list.locator('[data-download=furnitureCsv]')).toHaveAttribute('title',
      'The furniture changes on screen are not saved (overrides.json could not be written (test)): the file would not carry them');
    await page.keyboard.press('Escape');
    await expect(list).toHaveCount(0);
    // saved: a link again
    refusing = false;
    await page.getByTestId('heights-retry').click();
    await expect(status).toHaveText('Furniture saved');
    expect(await be.saved(P, N)).toEqual({ seat: 300 });
    expect(await be.savedEdits(P, N)).toEqual({ 'L1-atm-001': R });
    await page.getByTestId('downloads-menu').click();
    await expect(list.locator('[data-download=maxScript]')).not.toHaveAttribute('data-disabled', '');
    await page.keyboard.press('Escape');
  });
});
