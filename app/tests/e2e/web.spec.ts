// The staff web app in headless Edge (DESIGN.md 15, 17.4 "web"; WORK_BREAKDOWN F), on the Vite dev server (StrictMode on):
// the project list (4 cards, fields, thumbnails, the house's placeholder); the project page (one viewer under StrictMode:
// created 2, live 1, one canvas; the version picker switching the bank between v1 and v2 and disposing the old viewer);
// heights typed in the viewer saved (PUT seen, `Furniture saved`: step BX, it was `Heights saved`), kept over a reload, in
// the CSV and the offline downloads;
// the Max script byte-equal to the seeded file; the offline download opening from disk; failures and Not found; and
// (@app-only) the viewer's computed styles under the app's Tailwind.
//
// The same file runs at integration (the real API and viewer) and for builder F alone (the mock API and the fake viewer):
// apps/web/test/e2e/web-kit.ts reads which from the environment. Builder F's run (Git Bash, from app/):
//   WT_WEB_PORT=5726 WT_API_PORT=8726 WT_TMP="$TEMP/wt-f" WT_SERVE=web WT_SKIP_STORE_CHECK=1 VITE_FAKE_VIEWER=1 \
//     npx playwright test -c tests/e2e/playwright.config.ts --project=e2e tests/e2e/web.spec.ts
// With the mock, the CSV download is the fixture golden and the offline download a stand-in page that carries the
// payload but no viewer (the viewer check on it runs with the real API only); the computed-style check needs the real
// viewer and is skipped with the fake one.
// Before integration, the real API and viewer on F's ports (the seeded app/data copied under WT_TMP by the API's server
// command; dist/offline not needed; the offline template built into WT_TMP with
// `npx vite build -c packages/viewer/vite.offline.config.ts --outDir "$TEMP/wt-f/offline-template"`):
//   WT_WEB_PORT=5726 WT_API_PORT=8726 WT_TMP="$TEMP/wt-f" WT_SKIP_STORE_CHECK=1 \
//   WALKTHROUGH_OFFLINE_TEMPLATE="$TEMP/wt-f/offline-template/viewer-template.html" \
//     npx playwright test -c tests/e2e/playwright.config.ts --project=e2e tests/e2e/web.spec.ts tests/e2e/web-leak.spec.ts
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { expect, test, type Page } from '@playwright/test';
import type { HeightMap } from '../../packages/viewer/src/contracts';
import {
  formatDate,
  formatFloors,
  formatFurniture,
  formatOpenings,
  formatVersions,
  sourceKindLabel,
  versionLabel,
} from '../../apps/web/src/lib/format';
import {
  backend,
  download,
  facts,
  FAKE_VIEWER,
  heightBox,
  MOCK_API,
  offlinePayload,
  pickVersion,
  PROJECT_IDS,
  typeHeight,
  useApi,
  viewerReady,
} from '../../apps/web/test/e2e/web-kit';
import { FIXTURES_DIR } from '../../apps/web/test/mock-api/fixtures';
import { APP_ONLY, TARGET } from './lib/target';

/** The typed golden's heights (fixtures/csv/bank-v2-typed.csv). */
const TYPED: HeightMap = { table: 600, seat: 300, cabinet: 1000 };

test.skip(TARGET === 'prototype', 'the web specs run against the staff app (E2E_TARGET=app)');
useApi();

test('the project list: four cards with their fields, thumbnails, and the house placeholder', async ({ page, request }) => {
  const be = backend(request);
  await page.goto('/projects');
  const cards = page.getByTestId('project-card');
  await expect(page.locator(PROJECT_IDS.map(id => `[data-testid=project-card][data-project-id="${id}"]`).join(', '))).toHaveCount(4);   // the four seeded projects' cards (U-15.3: e2e-* projects may be listed too)
  await expect(page).toHaveTitle('Projects · Walkthrough');
  const list = await be.list();
  expect(list.map(p => p.id).filter(id => !id.startsWith('e2e-')).sort()).toEqual(PROJECT_IDS);   // U-15.3: e2e-* projects aside
  expect(await cards.evaluateAll(cs => cs.map(c => c.getAttribute('data-project-id')))).toEqual(list.map(p => p.id));   // newest first
  for (const p of list) {
    const card = page.locator(`[data-testid=project-card][data-project-id="${p.id}"]`);
    await expect(card.getByTestId('card-name')).toHaveText(p.name);
    await expect(card.getByTestId('card-source')).toHaveText(sourceKindLabel(p.sourceKind));
    await expect(card.getByTestId('card-floors')).toHaveText(formatFloors(p.floors));
    await expect(card.getByTestId('card-furniture')).toHaveText(formatFurniture(p.furnitureCount));
    await expect(card.getByTestId('card-openings')).toHaveText(formatOpenings(p.openingsCount));
    await expect(card.getByTestId('card-stamp')).toHaveText(p.stamp);
    await expect(card.getByTestId('card-versions')).toHaveText(formatVersions(p.versionCount));
    await expect(card.getByTestId('card-updated')).toHaveText(formatDate(p.updatedAt));
    await expect(card.getByTestId('card-link')).toHaveAttribute('href', `/projects/${p.id}`);
    if (p.thumbnailUrl) {
      const img = card.getByTestId('card-thumbnail');
      await expect(img).toHaveAttribute('src', p.thumbnailUrl);
      await expect.poll(() => img.evaluate((i: HTMLImageElement) => (i.complete ? i.naturalWidth : 0))).toBeGreaterThan(0);
    } else {
      await expect(card.getByTestId('card-thumbnail')).toHaveCount(0);
      await expect(card.getByTestId('card-placeholder-name')).toHaveText(p.shortName);
    }
  }
  // the seeded facts the cards show
  const card = (id: string) => page.locator(`[data-testid=project-card][data-project-id="${id}"]`);
  await expect(card('bank-sampeng').getByTestId('card-floors')).toHaveText('2 floors: Level 1, Level 2');
  await expect(card('bank-sampeng').getByTestId('card-versions')).toHaveText('2 versions');
  await expect(card('bank-sampeng').getByTestId('card-source')).toHaveText('CAD');
  await expect(card('hotel-lobby').getByTestId('card-source')).toHaveText('Pictures');
  await expect(card('presidential-suite').getByTestId('card-floors')).toHaveText('1 floor: Suite (FL-01)');
  await expect(card('sukhumvit-house').getByTestId('card-placeholder-name')).toHaveText('Sukhumvit house');
  for (const id of ['bank-sampeng', 'hotel-lobby', 'presidential-suite']) await expect(card(id).getByTestId('card-thumbnail')).toHaveCount(1);
});

test('the project page: the latest version, one viewer under StrictMode (created 2, live 1, one canvas)', async ({ page, request }) => {
  const be = backend(request);
  const v2 = await be.version('bank-sampeng', 2);
  await page.goto('/projects');
  await page.locator('[data-testid=project-card][data-project-id="bank-sampeng"] [data-testid=card-link]').click();
  await expect(page).toHaveURL(/\/projects\/bank-sampeng\/v\/2$/);
  await viewerReady(page, 2);
  expect(await facts(page)).toEqual({ created: 2, live: 1, canvases: 1, roots: 1 });
  await expect(page).toHaveTitle('Bangkok Bank, Sampeng Branch · v2 · Walkthrough');
  await expect(page.getByTestId('app-bar-title')).toHaveText('Bangkok Bank, Sampeng Branch');
  await expect(page.getByTestId('version-picker')).toContainText(versionLabel(v2));
  await expect(page.getByTestId('heights-status-text')).toHaveText('Furniture saved');
  await expect(page.locator('[data-wt=root]')).toHaveAttribute('data-model-stamp', v2.stamp);
  // the viewer fills the window below the 48 px bar
  expect(await page.getByTestId('app-bar').boundingBox()).toMatchObject({ x: 0, y: 0, width: 1400, height: 48 });
  expect(await page.getByTestId('viewer-host').boundingBox()).toEqual({ x: 0, y: 48, width: 1400, height: 832 });
  expect(await page.locator('[data-wt=root]').boundingBox()).toEqual({ x: 0, y: 48, width: 1400, height: 832 });
  // the staff app opens on the finished model, the heights kept by the host (nothing in localStorage)
  expect(await page.evaluate(() => window.__walkthrough!.viewer.replay?.phase)).toBe('done');
  expect(await page.evaluate(() => Object.keys(localStorage).filter(k => k.startsWith('walkthrough-furniture-heights:')))).toEqual([]);
  // Back (the redirect replaced its own history entry) and the app bar's link both lead to the list; the viewer goes
  await page.goBack();
  await expect(page).toHaveURL(/\/projects$/);
  await expect(page.locator(PROJECT_IDS.map(id => `[data-testid=project-card][data-project-id="${id}"]`).join(', '))).toHaveCount(4);   // the four seeded projects' cards (U-15.3: e2e-* projects may be listed too)
  expect(await page.evaluate(() => [document.querySelectorAll('[data-wt=root]').length, typeof window.__walkthrough])).toEqual([0, 'undefined']);
  await page.goForward();
  await viewerReady(page, 2);
  await page.getByTestId('back-to-projects').click();
  await expect(page).toHaveURL(/\/projects$/);
  // the URL changes when the navigation commits, React's render of the list a moment later (integration: seen once under
  // load), so wait for the list as the Back check above does, then the canvas must be gone
  await expect(page.locator(PROJECT_IDS.map(id => `[data-testid=project-card][data-project-id="${id}"]`).join(', '))).toHaveCount(4);   // the four seeded projects' cards (U-15.3: e2e-* projects may be listed too)
  await expect.poll(() => page.evaluate(() => document.querySelectorAll('canvas').length)).toBe(0);
});

test('the version picker switches the bank between v2 and v1 and disposes the old viewer', async ({ page, request }) => {
  const v1 = await backend(request).version('bank-sampeng', 1);
  await page.goto('/projects/bank-sampeng/v/2');
  await viewerReady(page, 2);
  await pickVersion(page, 1);
  await viewerReady(page, 3);
  expect(await facts(page)).toEqual({ created: 3, live: 1, canvases: 1, roots: 1 });
  await expect(page).toHaveTitle('Bangkok Bank, Sampeng Branch · v1 · Walkthrough');
  await expect(page.locator('[data-wt=root]')).toHaveAttribute('data-model-stamp', v1.stamp);
  await expect(page.getByTestId('version-picker')).toContainText(versionLabel(v1));
  await expect(page.getByTestId('heights-status')).toHaveCount(0);   // v1 has no furniture
  await pickVersion(page, 2);
  await viewerReady(page, 4);
  expect(await facts(page)).toEqual({ created: 4, live: 1, canvases: 1, roots: 1 });
  await page.goBack();
  await expect(page).toHaveURL(/\/v\/1$/);
  await viewerReady(page, 5);
  expect(await facts(page)).toEqual({ created: 5, live: 1, canvases: 1, roots: 1 });
});

test('downloads: the Max script is byte-equal to the seeded file; no CSV for a version without furniture', async ({ page, request }, testInfo) => {
  const be = backend(request);
  const v2 = await be.version('bank-sampeng', 2);
  await page.goto('/projects/bank-sampeng/v/2');
  await viewerReady(page, 2);
  const ms = await download(page, 'maxScript', testInfo);
  expect(ms.name).toBe('Bangkok_Bank_Sampeng_v2.ms');                      // the version in the name (fix step)
  expect(ms.name).toBe(v2.downloads.maxScript!.fileName);
  expect(ms.bytes.equals(readFileSync(be.maxScriptFile('bank-sampeng', 2, 'Bangkok_Bank_Sampeng.ms')))).toBe(true);   // the stored file
  // the menu: the version detail's URLs, word-for-word texts
  await page.getByTestId('downloads-menu').click();
  const list = page.getByTestId('downloads-list');
  await expect(list.locator('[data-download=maxScript]')).toHaveAttribute('href', v2.downloads.maxScript!.url);
  await expect(list.locator('[data-download=furnitureCsv]')).toHaveAttribute('href', v2.downloads.furnitureCsv!.url);
  await expect(list.locator('[data-download=offlineHtml]')).toHaveAttribute('href', v2.downloads.offlineHtml.url);
  await expect(list.locator('[data-download=maxScript]')).toHaveText('3ds Max script (.ms)');
  await expect(list.locator('[data-download=furnitureCsv]')).toHaveText('Furniture list (CSV)');
  await expect(list.locator('[data-download=offlineHtml]')).toHaveText('Offline viewer (HTML)');
  await page.keyboard.press('Escape');
  await expect(list).toHaveCount(0);
  await pickVersion(page, 1);
  await viewerReady(page, 3);
  await page.getByTestId('downloads-menu').click();
  await expect(list.locator('[data-download=furnitureCsv]')).toHaveAttribute('aria-disabled', 'true');
  expect(await list.locator('[data-download=furnitureCsv]').getAttribute('href')).toBeNull();
  await expect(list.locator('[data-download=maxScript]')).not.toHaveAttribute('aria-disabled', 'true');
  await page.keyboard.press('Escape');
});

test('heights typed in the viewer are saved, survive a reload, and come in the CSV and the offline downloads', async ({ page, request }, testInfo) => {
  test.setTimeout(240_000);
  const be = backend(request);
  await be.resetHeights('bank-sampeng', 2);
  const puts: unknown[] = [];
  page.on('request', r => {
    if (r.method() === 'PUT' && new URL(r.url()).pathname === '/api/projects/bank-sampeng/versions/2/furniture-heights') puts.push(r.postDataJSON());
  });
  await page.goto('/projects/bank-sampeng/v/2');
  await viewerReady(page, 2);
  await expect(heightBox(page, 'table')).toHaveValue('750');
  for (const [kind, mm] of Object.entries(TYPED)) await typeHeight(page, kind, mm);
  await expect(page.getByTestId('heights-status-text')).toHaveText('Furniture saved');
  await expect.poll(() => puts.at(-1)).toEqual({ heights: TYPED });
  expect(await be.saved('bank-sampeng', 2)).toEqual(TYPED);
  expect(await page.evaluate(() => Object.keys(localStorage).filter(k => k.startsWith('walkthrough-furniture-heights:')))).toEqual([]);

  // a reload starts from the saved heights
  await page.reload();
  await viewerReady(page, 2);
  expect(await page.evaluate(() => window.__walkthrough!.viewer.getHeights())).toEqual(TYPED);
  await expect(heightBox(page, 'table')).toHaveValue('600');
  await expect(heightBox(page, 'cabinet')).toHaveValue('1000');

  // the CSV download carries them (byte for byte the typed golden, BOM included)
  const csv = await download(page, 'furnitureCsv', testInfo);
  expect(csv.name).toBe('BangkokBank-Sampeng_furniture_list.csv');
  expect(csv.bytes.equals(readFileSync(path.join(FIXTURES_DIR, 'csv', 'bank-v2-typed.csv')))).toBe(true);

  // and the offline download, which opens from disk with no network
  const off = await download(page, 'offlineHtml', testInfo);
  expect(off.name).toBe('bank-sampeng-v2.html');
  const payload = offlinePayload(off.bytes.toString('utf8'));
  expect(payload.format).toBe('walkthrough-offline/1');
  expect(payload.version).toMatchObject({ projectId: 'bank-sampeng', version: 2, stamp: 'c3a9408304a2' });
  expect(payload.overrides?.heights).toEqual(TYPED);
  const offline = await page.context().newPage();
  const requests: string[] = [];
  offline.on('request', r => { if (!/^(file|data|blob):/i.test(r.url())) requests.push(r.url()); });
  await offline.route(/^(?!file:|data:|blob:)/i, route => route.abort('blockedbyclient'));
  await offline.goto(`${pathToFileURL(off.file).href}?build=0&nodownload=1&test=1`);
  await expect(offline).toHaveTitle('Bank branch test');
  await expect(offline.locator('meta[name=model-data]')).toHaveAttribute('content', 'c3a9408304a2');
  if (!MOCK_API) {
    await offline.waitForFunction(() => !!window.__walkthrough?.viewer, undefined, { timeout: 60_000 });
    await offline.evaluate(() => window.__walkthrough!.viewer.ready);
    expect(await offline.evaluate(() => window.__walkthrough!.viewer.getHeights())).toEqual(TYPED);
  }
  expect(requests).toEqual([]);
  await offline.close();

  // Reset in the viewer: the model's heights again, saved
  await page.locator('[data-wt=furniture-reset]').click();
  await expect.poll(() => puts.at(-1)).toEqual({ heights: {} });
  await expect(page.getByTestId('heights-status-text')).toHaveText('Furniture saved');
  expect(await be.saved('bank-sampeng', 2)).toEqual({});
  await expect(heightBox(page, 'table')).toHaveValue('750');
});

test('a failed save shows Not saved: <reason>, and Retry sends the newest map', async ({ page, request }) => {
  const be = backend(request);
  await be.resetHeights('bank-sampeng', 2);
  await page.goto('/projects/bank-sampeng/v/2');
  await viewerReady(page, 2);
  let failing = true;
  await page.route(url => url.pathname === '/api/projects/bank-sampeng/versions/2/furniture-heights', async route => {
    if (failing && route.request().method() === 'PUT') {
      await route.fulfill({ status: 503, contentType: 'application/json', body: JSON.stringify({ error: { code: 'unavailable', message: 'the store is busy (test)' } }) });
      return;
    }
    await route.fallback();
  });
  await typeHeight(page, 'seat', 300);
  await expect(page.getByTestId('heights-status-text')).toHaveText('Not saved: the store is busy (test)');
  await expect(page.getByTestId('heights-status')).toHaveAttribute('data-state', 'error');
  await typeHeight(page, 'seat', 320);   // a newer map while it fails: still not saved, the newest kept for Retry
  await expect(page.getByTestId('heights-status-text')).toHaveText('Saving…');
  await expect(page.getByTestId('heights-status-text')).toHaveText('Not saved: the store is busy (test)');
  failing = false;
  await page.getByTestId('heights-retry').click();
  await expect(page.getByTestId('heights-status-text')).toHaveText('Furniture saved');
  expect(await be.saved('bank-sampeng', 2)).toEqual({ seat: 320 });
  await be.resetHeights('bank-sampeng', 2);
});

test('the hotel: its plan pictures reach the viewer as the version asset URLs', async ({ page, request }) => {
  const be = backend(request);
  const hotel = await be.version('hotel-lobby', 1);
  const want = Object.fromEntries(hotel.assets.filter(a => a.role === 'plan-picture').map(a => [a.floor!, a.url]));
  expect(Object.keys(want).sort()).toEqual(['F1', 'F2']);
  await page.goto('/projects/hotel-lobby/v/1');
  await viewerReady(page, 2);
  expect(await page.evaluate(() => window.__host?.pictures?.src)).toEqual(want);
  expect(await page.evaluate(() => window.__host!.pictures!.ready)).toEqual([true, true]);
  expect(await page.evaluate(() => window.__walkthrough!.viewer.replay)).toBeNull();   // no stages
  const name = (await be.list()).find(p => p.id === 'hotel-lobby')!.name;
  await expect(page).toHaveTitle(`${name} · v1 · Walkthrough`);
});

test('the address options reach the viewer, and the picker keeps them (?build=play starts the replay)', async ({ page }) => {
  await page.goto('/projects/bank-sampeng/v/2?build=play');
  await viewerReady(page, 2);
  expect(await page.evaluate(() => window.__walkthrough!.viewer.replay?.phase)).toBe('play');
  await pickVersion(page, 1);
  await expect(page).toHaveURL(/\/v\/1\?build=play$/);
});

test('Not found and errors: an unknown project or version, a bad address; a failing list with Retry', async ({ page }) => {
  for (const p of ['/projects/no-such-project', '/projects/bank-sampeng/v/99', '/projects/bank-sampeng/v/0', '/somewhere/else']) {
    await page.goto(p);
    await expect(page.getByTestId('not-found'), p).toBeVisible();
    await expect(page).toHaveTitle('Not found · Walkthrough');
  }
  let failing = true;
  await page.route(url => url.pathname === '/api/projects', async route => {
    if (failing) {
      await route.fulfill({ status: 500, contentType: 'application/json', body: JSON.stringify({ error: { code: 'boom', message: 'the list is broken (test)' } }) });
      return;
    }
    await route.fallback();
  });
  await page.goto('/projects');
  await expect(page.getByTestId('projects-error-reason')).toHaveText('the list is broken (test)', { timeout: 20_000 });
  failing = false;
  await page.getByTestId('projects-retry').click();
  await expect(page.locator(PROJECT_IDS.map(id => `[data-testid=project-card][data-project-id="${id}"]`).join(', '))).toHaveCount(4);   // the four seeded projects' cards (U-15.3: e2e-* projects may be listed too)
});

test('a model the viewer cannot read shows its issues instead of a viewer', async ({ page }) => {
  await page.route(url => url.pathname === '/api/projects/bank-sampeng/versions/1/model', route =>
    route.fulfill({ status: 200, contentType: 'application/json', body: '"not a model"' }));
  await page.goto('/projects/bank-sampeng/v/1');
  await expect(page.getByTestId('model-error')).toBeVisible();
  await expect(page.getByTestId('model-error')).toContainText("This version's model could not be read");
  expect(await page.evaluate(() => [document.querySelectorAll('[data-wt=root]').length, document.querySelectorAll('canvas').length])).toEqual([0, 0]);
  await expect(page.getByTestId('downloads-menu')).toBeVisible();   // the app bar still works
});

test(`the viewer looks the same as in the offline file whatever the app's Tailwind does ${APP_ONLY}`, async ({ page }) => {
  test.skip(FAKE_VIEWER, "the computed styles are the real viewer's (VITE_FAKE_VIEWER=1 runs the fake)");
  await page.goto('/projects/bank-sampeng/v/2');
  await viewerReady(page, 2);
  const browserDefaultMargin = await page.evaluate(() => {
    const host = document.createElement('div');
    const cb = document.createElement('input');
    cb.type = 'checkbox';
    host.attachShadow({ mode: 'open' }).append(cb);   // no page styles reach into a shadow root: the browser's own default
    document.body.append(host);
    const m = getComputedStyle(cb).margin;
    host.remove();
    return m;
  });
  const look = await page.evaluate(() => {
    const q = (s: string) => document.querySelector(s) as HTMLElement;
    return {
      headingWeight: getComputedStyle(q('[data-wt=heading]')).fontWeight,
      panelWidth: q('[data-wt=panel]').offsetWidth,
      tickMargin: getComputedStyle(q('input[data-wt=toggle]')).margin,
    };
  });
  expect(look).toEqual({ headingWeight: '700', panelWidth: 360, tickMargin: browserDefaultMargin });
  await page.locator('[data-wt=camera-btn]').click();
  await expect(page.locator('[data-wt=camera-panel]')).toBeVisible();
  expect(await page.locator('[data-wt=camera-panel]').evaluate(e => (e as HTMLElement).offsetWidth)).toBe(300);
  await page.locator('[data-wt=camera-close]').click();
  await expect(page.locator('[data-wt=camera-panel]')).toBeHidden();
  // the staff app opens on the finished model: Build settings (the Build row's button) opens the card with its facts
  await page.locator('[data-wt=replay-open]').click();
  await expect(page.locator('[data-wt=replay-facts]')).toBeVisible();
  expect(await page.locator('[data-wt=replay-facts]').evaluate(e => getComputedStyle(e).listStyleType)).toBe('disc');
  expect(await page.evaluate(() => window.__walkthrough!.viewer.replay?.phase)).toBe('settings');
});

// ------------------------------------------------------------------------------------------------- fix step (3-4 Nov review)
// The staff app's own findings: a typed height is never dropped (adversarial 1), the last version picked wins (2), two tabs
// never erase each other's heights (3), an API that does not answer is said so and the save goes again by itself (4), the
// files that carry the saved heights wait while those are not saved (6), the keys go back to the viewer when a menu closes
// (9), and a clean console: an icon (no /favicon.ico 404) and no ResizeObserver loop error while switching versions.
const SAVES = '/api/projects/bank-sampeng/versions/2/furniture-heights';
const statusText = (page: Page) => page.getByTestId('heights-status-text');

test('a clean console: an icon in the page (no /favicon.ico), no errors while switching versions', async ({ page }) => {
  const errors: string[] = [], favicon: string[] = [];
  page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
  page.on('pageerror', e => errors.push(`[pageerror] ${e.message}`));
  page.on('request', r => { if (new URL(r.url()).pathname === '/favicon.ico') favicon.push(r.url()); });
  await page.goto('/projects');
  await expect(page.locator(PROJECT_IDS.map(id => `[data-testid=project-card][data-project-id="${id}"]`).join(', '))).toHaveCount(4);   // the four seeded projects' cards (U-15.3: e2e-* projects may be listed too)
  expect(await page.locator('link[rel=icon]').count()).toBe(1);
  await page.goto('/projects/bank-sampeng/v/2');
  await viewerReady(page, 2);
  for (const [n, created] of [[1, 3], [2, 4], [1, 5], [2, 6]] as const) {
    await pickVersion(page, n);
    await viewerReady(page, created);
  }
  await page.waitForTimeout(500);
  expect(favicon).toEqual([]);
  expect(errors).toEqual([]);
});

test('the browser\'s ResizeObserver-loop notification reaches no other error listener (Vite\'s forwarded it to the terminal); other errors do', async ({ page }) => {
  await page.goto('/projects');
  await expect(page.locator(PROJECT_IDS.map(id => `[data-testid=project-card][data-project-id="${id}"]`).join(', '))).toHaveCount(4);   // the four seeded projects' cards (U-15.3: e2e-* projects may be listed too)
  const seen = await page.evaluate(() => {
    // a window error listener added by a module script, as Vite's dev client's is (index.html's inline filter runs first)
    const w = window as unknown as { __seenErrors: string[] };
    w.__seenErrors = [];
    window.addEventListener('error', e => w.__seenErrors.push(e.message));
    window.dispatchEvent(new ErrorEvent('error', { message: 'ResizeObserver loop completed with undelivered notifications.' }));
    window.dispatchEvent(new ErrorEvent('error', { message: 'a real error (test)' }));
    return (window as unknown as { __seenErrors: string[] }).__seenErrors;
  });
  expect(seen).toEqual(['a real error (test)']);
});

test('a height typed while saves fail is kept: leaving the version and coming back, it is sent and saved', async ({ page, request }) => {
  const be = backend(request);
  await be.resetHeights('bank-sampeng', 2);
  await page.goto('/projects/bank-sampeng/v/2');
  await viewerReady(page, 2);
  let down = true;
  await page.route(url => url.pathname === SAVES, async route => {
    if (down && route.request().method() === 'PUT') { await route.abort('connectionrefused'); return; }
    await route.fallback();
  });
  await typeHeight(page, 'seat', 300);
  await expect(statusText(page)).toHaveText('Not saved: the API did not answer (is it running?)');
  await pickVersion(page, 1);                                  // leave the version (the save on leaving fails too)
  await viewerReady(page, 3);
  expect(await be.saved('bank-sampeng', 2)).toEqual({});
  down = false;
  await pickVersion(page, 2);                                  // back: the typed height, not the old saved one
  await viewerReady(page, 4);
  await expect(heightBox(page, 'seat')).toHaveValue('300');
  await expect(statusText(page)).toHaveText('Furniture saved');
  await expect.poll(() => be.saved('bank-sampeng', 2)).toEqual({ seat: 300 });
  await be.resetHeights('bank-sampeng', 2);
});

test('an API that does not answer (the proxy\'s empty 502): said so, downloads off, and the save goes again by itself', async ({ page, request }) => {
  const be = backend(request);
  await be.resetHeights('bank-sampeng', 2);
  await page.goto('/projects/bank-sampeng/v/2');
  await viewerReady(page, 2);
  let down = true;
  await page.route(url => url.pathname.startsWith('/api/'), async route => {
    if (down) { await route.fulfill({ status: 502, body: '' }); return; }
    await route.fallback();
  });
  await typeHeight(page, 'cabinet', 1000);
  await expect(statusText(page)).toHaveText('Not saved: the API did not answer (is it running?)');
  await page.getByTestId('downloads-menu').click();
  const list = page.getByTestId('downloads-list');
  await expect(list).toHaveAttribute('data-api-down', '');
  for (const key of ['maxScript', 'furnitureCsv', 'offlineHtml']) {
    await expect(list.locator(`[data-download=${key}]`)).toHaveAttribute('data-disabled', '');
    await expect(list.locator(`[data-download=${key}]`)).toHaveAttribute('title', 'The API is not answering (is it running?): nothing can be downloaded now');
  }
  await page.keyboard.press('Escape');
  down = false;                                                // the API is back: no Retry click
  await expect(statusText(page)).toHaveText('Furniture saved', { timeout: 20_000 });
  expect(await be.saved('bank-sampeng', 2)).toEqual({ cabinet: 1000 });
  await be.resetHeights('bank-sampeng', 2);
});

test('while a save was refused, the CSV and the offline file wait (they would carry other heights); the Max script does not', async ({ page, request }) => {
  const be = backend(request);
  await be.resetHeights('bank-sampeng', 2);
  await page.goto('/projects/bank-sampeng/v/2');
  await viewerReady(page, 2);
  let refusing = true;
  await page.route(url => url.pathname === SAVES, async route => {
    if (refusing && route.request().method() === 'PUT') {
      await route.fulfill({ status: 500, contentType: 'application/json', body: JSON.stringify({ error: { code: 'store_error', message: 'overrides.json could not be written (test)' } }) });
      return;
    }
    await route.fallback();
  });
  await typeHeight(page, 'table', 600);
  await expect(statusText(page)).toHaveText('Not saved: overrides.json could not be written (test)');
  await page.getByTestId('downloads-menu').click();
  const list = page.getByTestId('downloads-list');
  for (const key of ['furnitureCsv', 'offlineHtml']) {
    await expect(list.locator(`[data-download=${key}]`)).toHaveAttribute('data-disabled', '');
    await expect(list.locator(`[data-download=${key}]`)).toHaveAttribute('title', /The furniture changes on screen are not saved \(overrides\.json could not be written \(test\)\)/);
  }
  await expect(list.locator('[data-download=maxScript]')).not.toHaveAttribute('data-disabled', '');
  await page.keyboard.press('Escape');
  refusing = false;
  await page.getByTestId('heights-retry').click();
  await expect(statusText(page)).toHaveText('Furniture saved');
  expect(await be.saved('bank-sampeng', 2)).toEqual({ table: 600 });
  await be.resetHeights('bank-sampeng', 2);
});

test('picking the version on screen again while another one loads stays on it: the last pick wins', async ({ page }) => {
  await page.goto('/projects/bank-sampeng/v/2');
  await viewerReady(page, 2);
  let release!: () => void;
  const gate = new Promise<void>(r => { release = r; });
  await page.route(url => url.pathname.startsWith('/api/projects/bank-sampeng/versions/1'), async route => { await gate; await route.fallback(); });
  await page.getByTestId('version-picker').click();
  await page.locator('[data-testid=version-option][data-version="1"]').click();
  await expect(page.getByTestId('version-picker')).toHaveAttribute('data-pending', '');      // v1 is loading
  await page.getByTestId('version-picker').click();
  await page.locator('[data-testid=version-option][data-version="2"]').click();             // back to v2 before it lands
  release();
  await expect(page.getByTestId('version-picker')).not.toHaveAttribute('data-pending', '');
  await page.waitForTimeout(1500);                                                           // v1's answers come in meanwhile
  await expect(page).toHaveURL(/\/projects\/bank-sampeng\/v\/2$/);
  await expect(page.getByTestId('project-page')).toHaveAttribute('data-version', '2');
  expect(await facts(page)).toEqual({ created: 2, live: 1, canvases: 1, roots: 1 });       // v2's viewer, never replaced
});

test(`two tabs on one version: a save in one never erases the other's heights, and each shows what is saved ${APP_ONLY}`, async ({ page, request }) => {
  test.skip(MOCK_API, 'If-Match (412 revision_conflict) is the real API\'s');
  const be = backend(request);
  await be.resetHeights('bank-sampeng', 2);
  const a = page, b = await page.context().newPage();
  await a.goto('/projects/bank-sampeng/v/2');
  await viewerReady(a, 2);
  await b.goto('/projects/bank-sampeng/v/2');
  await viewerReady(b, 2);
  await typeHeight(a, 'table', 600);
  await expect(statusText(a)).toHaveText('Furniture saved');
  expect(await be.saved('bank-sampeng', 2)).toEqual({ table: 600 });
  await typeHeight(b, 'seat', 300);                            // B was opened before A's save: its PUT meets it, merges
  await expect(statusText(b)).toHaveText('Furniture saved');
  await expect.poll(() => be.saved('bank-sampeng', 2)).toEqual({ table: 600, seat: 300 });
  await expect(heightBox(b, 'table')).toHaveValue('600');      // B shows A's height too
  await a.evaluate(() => window.dispatchEvent(new Event('visibilitychange')));   // A looks again (focus; also every 30 s)
  await expect(heightBox(a, 'seat')).toHaveValue('300');
  await expect(statusText(a)).toHaveText('Furniture saved');
  await typeHeight(a, 'cabinet', 1000);                        // and A's next save keeps B's
  await expect(statusText(a)).toHaveText('Furniture saved');
  await expect.poll(() => be.saved('bank-sampeng', 2)).toEqual({ table: 600, seat: 300, cabinet: 1000 });
  await b.close();
  await be.resetHeights('bank-sampeng', 2);
});

test(`after the Downloads menu or the version picker closes, the keys go to the viewer again (Walk, W, Space) ${APP_ONLY}`, async ({ page }) => {
  test.skip(FAKE_VIEWER, 'the real viewer\'s Walk');
  await page.goto('/projects/bank-sampeng/v/2');
  await viewerReady(page, 2);
  await page.keyboard.press('Digit2');
  await expect.poll(() => page.evaluate(() => window.__walkthrough!.viewer.mode)).toBe('walk');
  const held = () => page.evaluate(() => (window as unknown as { __viewer: { state: { keys: Set<string> } } }).__viewer.state.keys.has('KeyW'));
  for (const [opener, opened] of [['downloads-menu', '[data-testid=downloads-list]'], ['version-picker', '[data-testid=version-option]']] as const) {
    await page.getByTestId(opener).click();
    await expect(page.locator(opened).first()).toBeVisible();     // open (the focus is in it)
    await page.keyboard.press('Escape');
    await expect(page.locator(opened)).toHaveCount(0);
    await expect.poll(() => page.evaluate(() => document.activeElement?.closest('[data-testid=app-bar]') ? 'app bar' : 'not')).toBe('not');
    await page.keyboard.down('KeyW');
    await expect.poll(held, opener).toBe(true);                // Walk has the key
    await page.keyboard.up('KeyW');
    await page.keyboard.press('Space');                        // Walk's jump / Ghost's up, not the menu again
    await expect(page.getByTestId('downloads-list')).toHaveCount(0);
  }
});
