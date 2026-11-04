// Builder A (DESIGN.md 16, 17.4): the offline single HTML per version. Each version's file opens from disk with
// ?build=0&nodownload=1&test=1, needs no network (the app target aborts and records anything that is not file:, data: or
// blob:), carries its version's stamp (the model-data meta and the root's data-model-stamp, the 3ds Max script's line 2)
// and its document title, and draws. On the prototype target the same checks run on the prototype pages, which load
// three.js from the CDN (no network rule there), have no root attribute and no payload (@app-only).
// @app-only: the payload is the store's files as they are; the viewer looks the same whatever the host page resets (the
// computed-style numbers F checks in the staff app); drawing text that is hostile renders as text, never as HTML.
//   E2E_TARGET=prototype WT_SERVE= WT_WEB_PORT=5721 WT_TMP="$TEMP/wt-a" npx playwright test -c tests/e2e/playwright.config.ts --project=e2e tests/e2e/offline.spec.ts
// The app target reads dist/offline and the store in data/ (the integration run); WT_OFFLINE_DIR and WT_DATA_DIR point it at
// other ones (builder A's own run on the hand-made store: packages/viewer/test/harness/core/make-e2e-offline.mjs).
import { spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { cpSync, existsSync, mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { expect, test, type Page } from '@playwright/test';
import { pageApi } from './lib/page';
import type { Viewer } from '../../packages/viewer/src/contracts';
import { APP, APP_ONLY, isApp, noNetwork, pageUrl, PROTOTYPES, sel, VERSIONS, waitReady, type VersionKey } from './lib/target';

const KEYS: VersionKey[] = ['bank-v1', 'bank-v2', 'suite', 'house', 'hotel'];
const PROTOTYPE_MAX: Partial<Record<VersionKey, string>> = {
  'bank-v1': 'bank_test/previous_before_fix_round_2026-10-27/Bangkok_Bank_Sampeng.ms', 'bank-v2': 'bank_test/Bangkok_Bank_Sampeng.ms',
  suite: 'presidential_test/Presidential_Suite.ms', hotel: 'hotel_test/Hotel_Lobby.ms',
};
const PROTOTYPE_MODEL: Partial<Record<VersionKey, string>> = {
  'bank-v1': 'bank_test/previous_before_fix_round_2026-10-27/src/bank_model.json', 'bank-v2': 'bank_test/src/bank_model.json',
  suite: 'presidential_test/src/pres2_model.json', hotel: 'hotel_test/src/hotel_model.json',
};
const TMP = process.env.WT_TMP ?? path.join(os.tmpdir(), 'wt-e2e');
const OFFLINE_DIR = process.env.WT_OFFLINE_DIR ?? null;
const DATA_DIR = process.env.WT_DATA_DIR ?? path.join(APP, 'data');
const versionDir = (k: VersionKey) => path.join(DATA_DIR, 'projects', VERSIONS[k].projectId, 'versions', String(VERSIONS[k].version));
/** The page of a version on this target (the app target may be pointed at another folder of offline files). */
function urlOf(key: VersionKey, query: string): string {
  if (isApp && OFFLINE_DIR) return pathToFileURL(path.join(OFFLINE_DIR, `${VERSIONS[key].projectId}-v${VERSIONS[key].version}.html`)).href + query;
  return pageUrl(key, query);
}
async function openVersion(page: Page, key: VersionKey, query = '?build=0&nodownload=1&test=1'): Promise<void> {
  await page.goto(urlOf(key, query));
  await waitReady(page);
}
const maxStamp = (file: string) => /\(model data ([0-9a-f]{12})\)/.exec(readFileSync(file, 'utf8').split(/\r?\n/)[1] ?? '')?.[1] ?? null;

async function payloadOf(page: Page): Promise<any> {
  return page.evaluate(() => JSON.parse(document.getElementById('wtv-data')!.textContent!));
}

for (const key of KEYS) {
  test(`${key}: the file opens from disk, without network, with its stamp and title, and draws`, async ({ page }) => {
    const p = await pageApi(page);
    const net = await noNetwork(page);
    await openVersion(page, key);
    const facts = await page.evaluate(sel => ({
      title: document.title,
      meta: document.querySelector('meta[name=model-data]')?.getAttribute('content') ?? null,
      root: document.querySelector('[data-wt=root]')?.getAttribute('data-model-stamp') ?? null,
      canvases: document.querySelectorAll('canvas').length,
      panel: !!document.querySelector(sel.panel),
      heading: document.querySelector(sel.heading)?.textContent ?? null,
      floors: (window.__host as unknown as { floors: { key: string }[] }).floors.map(f => f.key),
    }), { panel: sel.panel, heading: sel.heading });
    expect(facts.canvases).toBe(1);
    expect(facts.panel).toBe(true);
    expect(facts.floors).toEqual(VERSIONS[key].floors);
    if (isApp) {
      const payload = await payloadOf(page);
      const stamp = payload.version.stamp as string;
      expect(facts.title).toBe(payload.version.presentation.documentTitle);
      expect(facts.heading).toBe(payload.version.presentation.heading);
      expect(facts.meta).toBe(stamp);
      expect(facts.root).toBe(stamp);
      if (VERSIONS[key].stamp) expect(stamp).toBe(VERSIONS[key].stamp);
      const ms = payload.version.downloads.maxScript as string | null;
      if (ms) expect(maxStamp(path.join(versionDir(key), 'downloads', ms))).toBe(stamp);
      expect(net.requests).toEqual([]);
      expect(await page.evaluate(() => window.__walkthrough!.gpu().geometries)).toBeGreaterThan(5);
    } else {
      expect(facts.meta).toBe(VERSIONS[key].stamp);                       // the house page has none
      const model = PROTOTYPE_MODEL[key], max = PROTOTYPE_MAX[key];
      if (model) expect(createHash('sha1').update(readFileSync(path.join(PROTOTYPES, model))).digest('hex').slice(0, 12)).toBe(VERSIONS[key].stamp);
      if (max) expect(maxStamp(path.join(PROTOTYPES, max))).toBe(VERSIONS[key].stamp);
    }
    expect(p.logs.filter(l => l.startsWith('[exception]') || l.startsWith('[console.error]'))).toEqual([]);
  });
}

test(`the payload is the store's files as they are ${APP_ONLY}`, async ({ page }) => {
  for (const key of KEYS) {
    await openVersion(page, key);
    const payload = await payloadOf(page);
    const dir = versionDir(key), json = (f: string) => JSON.parse(readFileSync(path.join(dir, f), 'utf8'));
    expect(payload.format).toBe('walkthrough-offline/1');
    expect(payload.project).toEqual(JSON.parse(readFileSync(path.join(dir, '../../meta.json'), 'utf8')));
    expect(payload.version).toEqual(json('version.json'));
    expect(payload.model).toEqual(json('model.json'));
    expect(payload.stages).toEqual(existsSync(path.join(dir, 'stages.json')) ? json('stages.json') : null);
    expect(payload.overrides).toEqual(existsSync(path.join(dir, 'overrides.json')) ? json('overrides.json') : null);
    const pictures = (payload.version.assets as { role: string; floor?: string; name: string }[]).filter(a => a.role === 'plan-picture');
    expect(Object.keys(payload.pictures)).toEqual(pictures.map(a => a.floor));
    for (const a of pictures) {
      const b64 = /^data:[^;]+;base64,(.*)$/.exec(payload.pictures[a.floor!])![1]!;
      expect(Buffer.from(b64, 'base64').equals(readFileSync(path.join(dir, 'assets', a.name)))).toBe(true);
    }
  }
});

test(`the viewer looks the same whatever the host resets: the computed-style numbers at 1400 px ${APP_ONLY}`, async ({ page }) => {
  await page.setViewportSize({ width: 1400, height: 880 });
  await page.goto(urlOf('bank-v2', '?nodownload=1&test=1'));                 // the plain address: Build settings first
  await page.waitForFunction(() => !!window.__walkthrough?.viewer);
  await page.evaluate(() => window.__walkthrough!.viewer.ready);
  const facts = await page.evaluate(() => {
    const q = (s: string) => document.querySelector(s) as HTMLElement | null;
    const facts = q('[data-wt=replay-facts]');
    return { facts: facts ? getComputedStyle(facts).listStyleType : null };
  });
  expect(facts.facts).toBe('disc');
  await page.evaluate(() => (window as unknown as { __build: { skip(): void } }).__build.skip());
  const r = await page.evaluate(() => {
    const q = (s: string) => document.querySelector(s) as HTMLElement | null;
    const heading = q('[data-wt=heading]'), panel = q('[data-wt=panel]'), tick = q('input[data-wt=toggle]');
    q('[data-wt=camera-btn]')?.click();
    const cam = q('[data-wt=camera-panel]');
    return { heading: heading && getComputedStyle(heading).fontWeight, panel: panel?.offsetWidth ?? null, camera: cam?.offsetWidth ?? null,
      margin: tick && getComputedStyle(tick).margin };
  });
  expect(r).toEqual({ heading: '700', panel: 360, camera: 300, margin: '3px 3px 3px 4px' });
});

test(`hostile drawing text renders as text, never as HTML (a store made here with the built template) ${APP_ONLY}`, async ({ page }) => {
  const template = process.env.WT_OFFLINE_TEMPLATE ?? path.join(APP, 'dist', 'offline-template', 'viewer-template.html');
  test.skip(!existsSync(template), `no template at ${template} (npm run build:offline:template)`);
  const evil = ['</script><script>window.__pwned = 1</script>', "$' $& $` $$", '__WTV_DATA__ __WTV_STAMP__', '<!--', '<img src=x onerror="window.__pwned = 1">'];
  const root = path.join(TMP, 'offline-hostile', 'data'), out = path.join(TMP, 'offline-hostile', 'out');
  const model = JSON.parse(readFileSync(path.join(APP, 'fixtures/models/mini.model.json'), 'utf8'));
  model.project = `Hostile ${evil.join(' ')}`;
  model.rooms = evil.map((label, i) => ({ floor: 'L2', name: label, label, area: 40 - i, x: -2 + i * 2, y: 0 }));
  model.furniture.forEach((piece: Record<string, string>, i: number) => { piece.family = evil[i % evil.length]!; piece.layer = evil[(i + 1) % evil.length]!; });
  const modelText = `${JSON.stringify(model)}\n`;
  const modelSha1 = createHash('sha1').update(modelText).digest('hex'), stamp = modelSha1.slice(0, 12);   // the real sha1: make-offline checks it
  const dir = path.join(root, 'projects', 'hostile-names', 'versions', '1');
  mkdirSync(dir, { recursive: true });
  writeFileSync(path.join(dir, 'model.json'), modelText);
  writeFileSync(path.join(root, 'projects', 'hostile-names', 'meta.json'), `${JSON.stringify({ format: 'walkthrough-project/1', id: 'hostile-names', name: model.project,
    shortName: 'Hostile', projectNo: null, sourceKind: 'cad', createdAt: '2026-11-03T00:00:00Z', updatedAt: '2026-11-03T00:00:00Z', latestVersion: 1, versions: [1] }, null, 2)}\n`);
  writeFileSync(path.join(dir, 'version.json'), `${JSON.stringify({ format: 'walkthrough-version/1', projectId: 'hostile-names', version: 1, label: evil.join(' '),
    createdAt: '2026-11-03T00:00:00Z', sourceKind: 'cad', sourceFiles: evil, modelFormat: 'built-model/1', modelSha1, stamp, stampSource: 'model.json',
    counts: { floors: 2, parts: model.parts.length, openings: model.openings.length, furniture: model.furniture.length, furnitureKinds: model.furnitureKinds.length, rooms: model.rooms.length },
    floors: model.floors.map((f: { key: string; name: string; level: number }) => ({ key: f.key, name: f.name, level: f.level })), hasStages: false, assets: [],
    downloads: { maxScript: null, furnitureCsv: true },
    presentation: { documentTitle: `Hostile ${evil[0]}`, heading: `Hostile ${evil[0]}`, intro: evil.map(text => ({ text, bold: true })), accent: '#2f6f8f',
      legend: { layout: 'lines', items: evil.map(text => ({ colour: '#e3ddd3', text })) }, camera: { kind: 'fixed', position: [12, 14, 16], target: [0, 1.5, 0] } } }, null, 2)}\n`);
  const r = spawnSync(process.execPath, [path.join(APP, 'packages/viewer/scripts/make-offline.mjs'), '--data', root, '--template', template, '--out', out], { encoding: 'utf8' });
  expect(r.status, r.stderr).toBe(0);
  const p = await pageApi(page);
  await noNetwork(page);
  await page.goto(`${pathToFileURL(path.join(out, 'hostile-names-v1.html')).href}?build=0&nodownload=1&test=1`);
  await page.waitForFunction(() => !!window.__walkthrough?.viewer);
  await page.evaluate(() => window.__walkthrough!.viewer.ready);
  await page.waitForTimeout(500);
  const seen = await page.evaluate(() => ({
    pwned: (window as unknown as { __pwned?: number }).__pwned ?? null,
    scripts: document.querySelectorAll('script').length,
    imgs: document.querySelectorAll('[data-wt=root] img').length,
    title: document.title,
    heading: document.querySelector('[data-wt=heading]')?.textContent ?? null,
    rooms: [...document.querySelectorAll('[data-wt=room]')].map(e => e.textContent),
    legend: document.querySelector('[data-wt=legend]')?.textContent ?? '',
    furniture: (window.__host as unknown as { furniture: { pieces(): { family: string }[] } | null }).furniture?.pieces().map(x => x.family).slice(0, 5) ?? [],
  }));
  expect(seen.pwned).toBeNull();
  expect(seen.imgs).toBe(0);
  expect(seen.scripts).toBe(3);                    // the template's three (the incomplete-file check, the module, the data)
  expect(seen.title).toBe(`Hostile ${evil[0]}`);
  expect(seen.heading).toBe(`Hostile ${evil[0]}`);
  expect(seen.rooms).toEqual(evil);
  for (const e of evil) expect(seen.legend).toContain(e);
  if (seen.furniture.length) expect(seen.furniture).toEqual(evil.concat(evil).slice(0, seen.furniture.length));
  expect(p.logs.filter(l => l.startsWith('[exception]'))).toEqual([]);
});

// ------------------------------------------------------------------------------------------------- fix step (3 Nov review)
/** dist/offline (or WT_OFFLINE_DIR) file of a version on the app target. */
const offlineFile = (key: VersionKey) =>
  path.join(OFFLINE_DIR ?? path.join(APP, 'dist', 'offline'), `${VERSIONS[key].projectId}-v${VERSIONS[key].version}.html`);

test(`a file cut short says so: inside the viewer's script (the template's check) and inside the data (the entry's) ${APP_ONLY}`, async ({ page }) => {
  const whole = readFileSync(offlineFile('bank-v2'));
  const dataAt = whole.indexOf('<script type="application/json" id="wtv-data">');
  expect(dataAt).toBeGreaterThan(300_000);                                   // the viewer's script comes first
  const dir = path.join(TMP, 'offline-truncated');
  mkdirSync(dir, { recursive: true });
  const cases = [
    { name: 'in-the-script.html', bytes: whole.subarray(0, 300_000), says: 'This file is incomplete or damaged' },
    { name: 'in-the-data.html', bytes: whole.subarray(0, dataAt + Math.floor((whole.length - dataAt) / 2)), says: 'the file may be incomplete' },
  ];
  for (const c of cases) {
    writeFileSync(path.join(dir, c.name), c.bytes);
    await page.goto(pathToFileURL(path.join(dir, c.name)).href);
    const box = page.locator('[data-wt=offline-error]');
    await expect(box, c.name).toHaveCount(1);
    await expect(box, c.name).toContainText('The walkthrough could not start.');
    await expect(box, c.name).toContainText(c.says);
    expect(await page.locator('canvas').count(), c.name).toBe(0);
  }
  await openVersion(page, 'bank-v2');                                         // the whole file: no message
  expect(await page.locator('[data-wt=offline-error]').count()).toBe(0);
});

test(`the handle of a disposed viewer types no heights and stores nothing ${APP_ONLY}`, async ({ page }) => {
  await openVersion(page, 'bank-v2');
  const r = await page.evaluate(() => {
    localStorage.clear();
    const mount = window.__wtvMount as unknown as { viewer: Viewer; unmount(): void };
    const viewer = mount.viewer;
    mount.unmount();
    return {
      disposed: viewer.disposed,
      setHeight: viewer.furniture!.setHeight('table', 640),
      setKeep: viewer.furniture!.setKeepDoorways(false),
      heights: viewer.getHeights(),
      keys: Object.keys(localStorage).filter(k => k.startsWith('walkthrough-furniture-heights:')),
    };
  });
  expect(r).toEqual({ disposed: true, setHeight: false, setKeep: false, heights: {}, keys: [] });
});

test(`two downloads of a version with other saved heights: each opens with its own, and Reset goes back to the file's ${APP_ONLY}`, async ({ page }) => {
  const template = process.env.WT_OFFLINE_TEMPLATE ?? path.join(APP, 'dist', 'offline-template', 'viewer-template.html');
  test.skip(!existsSync(template), `no template at ${template} (npm run build:offline:template)`);
  const make = (name: string, heights: Record<string, number>) => {
    const root = path.join(TMP, 'offline-saved', name, 'data'), out = path.join(TMP, 'offline-saved', name, 'out');
    const src = path.join(DATA_DIR, 'projects', 'bank-sampeng'), dst = path.join(root, 'projects', 'bank-sampeng');
    rmSync(path.join(TMP, 'offline-saved', name), { recursive: true, force: true });
    cpSync(src, dst, { recursive: true });
    writeFileSync(path.join(dst, 'versions', '2', 'overrides.json'),
      `${JSON.stringify({ format: 'walkthrough-overrides/1', heights, revision: 1, updatedAt: '2026-11-03T00:00:00Z' }, null, 2)}\n`);
    const r = spawnSync(process.execPath, [path.join(APP, 'packages/viewer/scripts/make-offline.mjs'), '--data', root, '--template', template, '--out', out], { encoding: 'utf8' });
    expect(r.status, r.stderr).toBe(0);
    return `${pathToFileURL(path.join(out, 'bank-sampeng-v2.html')).href}?build=0&nodownload=1&test=1`;
  };
  const first = make('first', { table: 600 }), second = make('second', { table: 700, seat: 300 });
  const open = async (url: string) => {
    await page.goto(url);
    await page.waitForFunction(() => !!window.__walkthrough?.viewer);
    await page.evaluate(() => window.__walkthrough!.viewer.ready);
  };
  await open(first);
  await page.evaluate(() => { for (const k of Object.keys(localStorage)) if (k.startsWith('walkthrough-furniture-heights:')) localStorage.removeItem(k); });
  await open(first);
  expect(await page.evaluate(() => window.__walkthrough!.viewer.getHeights())).toEqual({ table: 600 });
  await page.evaluate(() => { window.__host!.furniture!.setHeight('table', 500); window.__host!.furniture!.setHeight('cabinet', 1000); });
  await open(second);                                                        // the owner's next download, same browser
  expect(await page.evaluate(() => window.__walkthrough!.viewer.getHeights())).toEqual({ table: 700, seat: 300 });
  await open(first);                                                         // the first file keeps what was typed in it
  expect(await page.evaluate(() => window.__walkthrough!.viewer.getHeights())).toEqual({ table: 500, cabinet: 1000 });
  await page.locator('[data-wt=furniture-reset]').click();                   // Reset: the file's heights, not the model's
  expect(await page.evaluate(() => window.__walkthrough!.viewer.getHeights())).toEqual({ table: 600 });
  await open(first);
  expect(await page.evaluate(() => window.__walkthrough!.viewer.getHeights())).toEqual({ table: 600 });
});
