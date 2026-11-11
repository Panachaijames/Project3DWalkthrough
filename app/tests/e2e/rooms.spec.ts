// The owner's path through the screens for rooms, slabs and stairs (docs/rooms/ACCEPTANCE.md RA-12; DESIGN.md R-1.3,
// R-6.2, R-6.4, R-12.6; WORK_BREAKDOWN R6). Every project made here has an e2e- id; a fixture is applied by merging only
// its layers, floors and furniture into the settings the draft already has, never its options. Canvas clicks go through
// the plan canvas's test hook window.__plan (toPage, spaces, stairs); the screens' elements by the ids of
// apps/web/src/build/testids.ts.
//   1. RA-12 point 3, the fixes on the reference building (its two DXFs, tools/rooms/make-reference-building.py dxf):
//      "Close it here", "No floor here", the stair's bottom and "Keep as lines", "Not a doorway: one room", a line drawn,
//      Remove. Under the mock API (WT_SERVE=web: the mock knows the reference building, apps/web/test/mock-api/rooms.ts)
//      it checks that the panels and tools write the right fixes and that the waiting marks come and go (the mock's
//      "rebuild" applies the fixes the simple way); with the real worker also what each rebuild built (RA-12 point 3).
//   2. RA-12 point 1, the house as a new project (real worker only).
//   3. RA-12 point 2, a project saved before this milestone, on the reference building (real worker only).
// The earlier way through the screens (RA-12 point 5) is upload.spec.ts's.
//
// R6 alone, against the mock API (Git Bash, from app/):
//   WT_WEB_PORT=5746 WT_API_PORT=8746 WT_TMP="$TEMP/wt-r6" WT_SERVE=web WT_SKIP_STORE_CHECK=1 VITE_FAKE_VIEWER=1 \
//     npx playwright test -c tests/e2e/playwright.config.ts --project=e2e tests/e2e/rooms.spec.ts
// At integration: the real API and worker (`npm run test:e2e`; a fresh store).
import { execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { existsSync, mkdirSync, readdirSync, readFileSync, statSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { expect, test, type APIRequestContext, type Locator, type Page } from '@playwright/test';
import { sel as tidSel, TID, type TestId } from '../../apps/web/src/build/testids';
import { NEW_RULES, OLD_RULES, type BuildDetail, type BuildOverlay, type BuildSettings } from '../../apps/web/src/upload/contracts';
import { download, MOCK_API, useApi, viewerReady } from '../../apps/web/test/e2e/web-kit';
import { buildIdOf, getBuild, putBuildSettings, settingsSaved, waitForReading, waitForResult } from '../../apps/web/test/e2e/upload-kit';
import { APP_DIR, FIXTURES_DIR, PROTOTYPES_DIR } from '../../apps/web/test/mock-api/fixtures';
import { insideOf } from '../../apps/web/test/mock-api/rooms';
import { sel, TARGET, TMP } from './lib/target';
import { stairWalks } from './lib/walks';

/* eslint-disable @typescript-eslint/no-explicit-any */

test.skip(TARGET === 'prototype', 'the rooms screens are the staff app\'s (E2E_TARGET=app)');
useApi();

type P2 = [number, number];
const fixture = (...p: string[]) => JSON.parse(readFileSync(path.join(FIXTURES_DIR, ...p), 'utf8')) as BuildSettings;
const HOUSE_DWG = path.join(PROTOTYPES_DIR, 'Test Sukhumvit Residence.dwg');

/** The reference building's two DXFs, made once into the spec's temp folder by the scaffold's tool (the mock needs only
 *  their names; without the builder Python a mock run writes two empty DXFs of those names). */
function referenceDxfs(): string[] {
  const dir = path.join(TMP, 'rooms-spec', 'dxf');
  const files = ['ground', 'upper'].map(k => path.join(dir, `rooms-reference-${k}.dxf`));
  if (files.every(f => existsSync(f))) return files;
  mkdirSync(dir, { recursive: true });
  try {
    execFileSync(process.execPath, ['tools/run-builder-py.mjs', 'tools/rooms/make-reference-building.py', 'dxf', dir], {
      cwd: APP_DIR, stdio: 'pipe', env: { ...process.env, PYTHONIOENCODING: 'utf-8' },
    });
  } catch (err) {
    if (!MOCK_API) throw err;
    for (const f of files) writeFileSync(f, '  0\r\nSECTION\r\n  2\r\nENTITIES\r\n  0\r\nENDSEC\r\n  0\r\nEOF\r\n', 'latin1');
  }
  return files;
}

/** The draft's settings with only the fixture's layers, floors (sources matched by file name) and furniture merged in:
 *  the draft's options (the new rules) and everything else stay (RA-12). */
function merged(draft: BuildDetail, fx: BuildSettings, opts: { ceilings?: boolean } = {}): BuildSettings {
  const s = draft.settings!;
  const byName = new Map(draft.sources.map(x => [x.name, x.sha1]));
  return {
    ...s,
    sources: s.sources.map(x => ({ ...x, unitsConfirmed: true })),
    layers: { ...s.layers, ...fx.layers },
    furniture: fx.furniture,
    floors: fx.floors.map(f => {
      const name = fx.sources.find(x => x.sha1 === f.source)!.name;
      const source = byName.get(name);
      if (!source) throw new Error(`no source named ${name} in the draft`);
      return opts.ceilings === false ? { ...f, source, ceilingHeight: null } : { ...f, source };
    }),
  };
}

function noDialogs(page: Page): string[] {
  const seen: string[] = [];
  page.on('dialog', d => { seen.push(d.message()); void d.dismiss(); });
  page.on('pageerror', e => seen.push(`[pageerror] ${e.message}`));
  return seen;
}

const T = (page: Page | Locator, id: TestId) => page.locator(tidSel(id));

async function goStep(page: Page, step: string) {
  await page.getByTestId(`step-${step}`).click();
  await expect(page.getByTestId('build-page')).toHaveAttribute('data-step', step);
}

async function newProject(page: Page, name: string, id: string) {
  await page.goto('/projects');
  await page.getByTestId('new-project').click();
  await expect(page).toHaveURL(/\/projects\/new$/);
  await page.getByTestId('np-name').fill(name);
  await page.getByTestId('np-id').fill(id);
  await page.getByTestId('np-create').click();
  await expect(page).toHaveURL(new RegExp(`/projects/${id}/builds/new$`));
}

async function uploadAndContinue(page: Page, files: string[]) {
  await page.getByTestId('file-input').setInputFiles(files);
  await expect(page.locator('[data-testid=upload-row][data-state=done]')).toHaveCount(files.length, { timeout: 120_000 });
  await page.getByTestId('start-build').click();
  await expect(page).toHaveURL(/\/builds\/\d{8}T\d{6}-[0-9a-f]{6}\?step=files$/);
}

async function overlayOf(request: APIRequestContext, d: BuildDetail): Promise<BuildOverlay> {
  const r = await request.get(d.result!.urls.overlay);
  expect(r.status()).toBe(200);
  return (await r.json()) as BuildOverlay;
}

/** A click on the plan at a sheet point, through window.__plan (RA-12: canvas clicks go through the hook). */
async function clickPlan(page: Page, pt: P2) {
  await expect.poll(() => page.evaluate(() => !!(window as any).__plan)).toBe(true);
  const p = await page.evaluate(q => (window as any).__plan.toPage(q), pt);
  if (!p) throw new Error(`${pt} is not on the plan canvas`);
  await page.mouse.click(p[0], p[1]);
}
const hookSpaces = (page: Page) => page.evaluate(() => ((window as any).__plan?.spaces() ?? []) as { id: string; name: string; area: number; at: [number, number] }[]);
const hookStairs = (page: Page) => page.evaluate(() => ((window as any).__plan?.stairs() ?? []) as { id: string; state: 'climb' | 'lines'; at: [number, number] }[]);

async function settingsNow(page: Page, request: APIRequestContext, projectId: string, buildId: string): Promise<BuildSettings> {
  await settingsSaved(page);
  return (await getBuild(request, projectId, buildId)).settings!;
}

async function rebuild(page: Page, request: APIRequestContext, projectId: string, buildId: string, after: BuildDetail): Promise<BuildDetail> {
  await settingsSaved(page);
  await page.getByTestId('rebuild').click();
  return waitForResult(page, request, projectId, buildId, after.result!.runId);
}

/** The counts in the page equal the overlay's (RA-12 point 1: rooms, holes, stairs). */
async function countsMatch(page: Page, ov: BuildOverlay, floor: string) {
  const f = ov.floors.find(x => x.key === floor)!;
  await page.locator(`[data-testid=check-floor][data-key="${floor}"]`).click();
  await expect(T(page, TID.checkRooms)).toHaveText(String(f.spaces?.length ?? 0), { timeout: 30_000 });
  await expect(T(page, TID.checkHoles)).toHaveText(String(f.holes?.length ?? 0));
  await expect(T(page, TID.checkStairs)).toHaveText(String(f.stairs?.length ?? 0));
  await expect(T(page, TID.checkStairsClimb)).toHaveText(String((f.stairs ?? []).filter(s => s.state === 'climb').length));
}

// ================================================================================================================= 1.
test('RA-12 point 3: the fixes on the reference building, each written by its panel or tool (and built, with the real worker)', async ({ page, request }) => {
  test.setTimeout(MOCK_API ? 6 * 60_000 : 40 * 60_000);
  const dialogs = noDialogs(page);
  const projectId = 'e2e-rooms-fixes';
  await newProject(page, 'E2E Rooms fixes', projectId);
  await uploadAndContinue(page, referenceDxfs());
  const buildId = await buildIdOf(page);
  const read = await waitForReading(request, projectId, buildId);
  expect(read.settings!.options, 'a new draft gets the new rules').toMatchObject(NEW_RULES);
  await putBuildSettings(request, projectId, buildId, merged(read, fixture('rooms', 'settings.reference.json')));
  await page.reload();

  // Floors: the line says the new way; Build
  await goStep(page, 'floors');
  await expect(T(page, TID.rulesLine)).toHaveAttribute('data-rules', 'new');
  await goStep(page, 'build');
  await expect(T(page, TID.rulesLine)).toHaveAttribute('data-rules', 'new');
  await expect(page.getByTestId('checklist-clear')).toBeVisible();
  await page.getByTestId('run-build').click();
  let d = await waitForResult(page, request, projectId, buildId, null);
  await expect(page.locator(tidSel(TID.roomCounts))).toHaveCount(2, { timeout: 30_000 });

  // Check: the counts are the overlay's
  await goStep(page, 'check');
  let ov = await overlayOf(request, d);
  const G = ov.floors[0]!.key;
  await countsMatch(page, ov, ov.floors[1]!.key);
  await countsMatch(page, ov, G);
  await expect(T(page, TID.rulesLine)).toHaveAttribute('data-rules', 'new');

  // (a) the 2.9 m opening's slab-gap flag: "Close it here" -> the mouth's two ends as a closing line, waiting
  const gapFlag = ov.flags.find(f => f.kind === 'slab-gap' && f.floor === G && f.ref.a && f.ref.b)!;
  expect(gapFlag, 'a slab-gap flag with its mouth').toBeTruthy();
  const gapCard = page.locator(`[data-testid=flag][data-id="${gapFlag.id}"]`);
  await gapCard.locator(tidSel(TID.flagCloseHere)).click();
  let s = await settingsNow(page, request, projectId, buildId);
  expect(s.fixes.closings).toEqual([{ floor: G, a: gapFlag.ref.a, b: gapFlag.ref.b, use: 'line' }]);
  await expect(gapCard.locator(tidSel(TID.fixWaiting))).toBeVisible();
  await expect(page.locator(`${tidSel(TID.fixRow)}[data-kind=closing][data-waiting]`)).toHaveCount(1);
  d = await rebuild(page, request, projectId, buildId, d);
  ov = await overlayOf(request, d);
  expect(ov.flags.filter(f => f.kind === 'slab-gap' && f.floor === G), 'the gap is closed').toEqual([]);
  await expect(page.locator(`${tidSel(TID.fixRow)}[data-kind=closing]:not([data-waiting])`)).toHaveCount(1, { timeout: 30_000 });
  if (!MOCK_API) {
    // the room behind the gap has its floor: the area's own point now lies in a room or on the plate
    expect(ov.floors[0]!.unfloored ?? []).toEqual([]);
  }

  // (b) "No floor here" on one room (the kitchen), with the tool Rooms and stairs
  await page.getByTestId('check-tool').selectOption('rooms');
  const kitchen = (await hookSpaces(page)).find(x => x.name === 'KITCHEN')!;
  expect(kitchen, 'the kitchen is a room').toBeTruthy();
  await clickPlan(page, kitchen.at);
  await expect(T(page, TID.roomPanel)).toHaveAttribute('data-id', kitchen.id);
  await T(page, TID.roomNoFloor).click();
  s = await settingsNow(page, request, projectId, buildId);
  expect(s.fixes.rooms).toEqual([expect.objectContaining({ floor: G, name: null, slab: 'none', ceiling: 'auto' })]);
  await expect(T(page, TID.roomPanel).locator(tidSel(TID.fixWaiting))).toBeVisible();
  d = await rebuild(page, request, projectId, buildId, d);
  ov = await overlayOf(request, d);
  const roomAt = s.fixes.rooms![0]!.at;
  const holeAt = (o: BuildOverlay) => (o.floors[0]!.holes ?? []).some(h => {
    let c = false;
    for (let i = 0, j = h.o.length - 1; i < h.o.length; j = i++) {
      const [xi, yi] = h.o[i]!, [xj, yj] = h.o[j]!;
      if ((yi > roomAt[1]) !== (yj > roomAt[1]) && roomAt[0] < xj + ((roomAt[1] - yj) * (xi - xj)) / (yi - yj)) c = !c;
    }
    return c;
  });
  expect(holeAt(ov), 'the kitchen is a hole').toBe(true);
  await page.keyboard.press('Escape');

  // (c) the second stair, drawn with no word, arrow or break line: "This is the bottom" and a click on its bottom tread
  const st2 = ov.floors[0]!.stairs!.find(x => x.state === 'lines' && x.why === 'no direction')!;
  expect(st2, 'the stair whose bottom was not found').toBeTruthy();
  expect(ov.flags.some(f => f.kind === 'stair' && f.ref.stair === st2.id && /which end is the bottom was not found/.test(f.detail))).toBe(true);
  const at2 = (await hookStairs(page)).find(x => x.id === st2.id)!.at;
  await clickPlan(page, at2);
  await expect(T(page, TID.stairPanel)).toHaveAttribute('data-id', st2.id);
  await T(page, TID.stairBottom).click();
  await expect(T(page, TID.stairBottom)).toHaveAttribute('data-picking', '');
  // the bottom tread: just past riser 1 at the stair's west end (the drawing: 16 risers from x 1.0 to 5.2 at y 8.0)
  const xs = st2.outline.map(p => p[0]);
  const bottom: P2 = [Math.min(...xs) + 0.14, (Math.min(...st2.outline.map(p => p[1])) + Math.max(...st2.outline.map(p => p[1]))) / 2];
  await clickPlan(page, bottom);
  s = await settingsNow(page, request, projectId, buildId);
  expect(s.fixes.stairs).toEqual([expect.objectContaining({ floor: G, use: 'auto' })]);
  const fb = s.fixes.stairs![0]!.bottom!;
  expect(Math.hypot(fb[0] - bottom[0], fb[1] - bottom[1])).toBeLessThan(0.1);
  await expect(page.locator(`${tidSel(TID.fixRow)}[data-kind=stair][data-waiting]`)).toHaveCount(1);
  d = await rebuild(page, request, projectId, buildId, d);
  ov = await overlayOf(request, d);
  expect(ov.floors[0]!.stairs!.find(x => x.id === st2.id || (x.state === 'climb' && x.id !== 'S1'))?.state, 'the stair is climbable').toBe('climb');
  if (!MOCK_API) {
    const model = await (await request.get(d.result!.urls.model)).json();
    expect(model.stairways.length, 'two stairways now').toBe(2);
  }
  // "Keep as lines" -> no treads, the lines are back
  const climbing = (await hookStairs(page)).find(x => x.state === 'climb' && x.id !== 'S1');
  await clickPlan(page, (climbing ?? (await hookStairs(page)).find(x => x.id === st2.id)!).at);
  await expect(T(page, TID.stairPanel)).toBeVisible();
  await T(page, TID.stairLines).click();
  s = await settingsNow(page, request, projectId, buildId);
  expect(s.fixes.stairs).toEqual([expect.objectContaining({ floor: G, use: 'lines' })]);
  d = await rebuild(page, request, projectId, buildId, d);
  ov = await overlayOf(request, d);
  expect(ov.floors[0]!.stairs!.filter(x => x.state === 'climb').map(x => x.id)).toEqual(['S1']);
  if (!MOCK_API) {
    const model = await (await request.get(d.result!.urls.model)).json();
    expect(model.stairways.length, 'one stairway again').toBe(1);
  }
  await page.keyboard.press('Escape');

  // (d) the door-sized gap: a dashed doorway closing and its flag -> "Not a doorway: one room"
  const door = ov.flags.find(f => f.kind === 'doorway' && f.floor === G)!;
  expect(door, 'a doorway flag').toBeTruthy();
  expect(ov.floors[0]!.closings!.some(c => c.kind === 'doorway')).toBe(true);
  const roomsBefore = ov.floors[0]!.spaces!.length;
  await page.locator(`[data-testid=flag][data-id="${door.id}"]`).locator(tidSel(TID.flagNotDoorway)).click();
  s = await settingsNow(page, request, projectId, buildId);
  expect(s.fixes.closings!.at(-1)).toEqual({ floor: G, a: door.ref.a, b: door.ref.b, use: 'none' });
  d = await rebuild(page, request, projectId, buildId, d);
  ov = await overlayOf(request, d);
  expect(ov.floors[0]!.closings!.filter(c => c.kind === 'doorway')).toEqual([]);
  if (!MOCK_API) expect(ov.floors[0]!.spaces!.length, 'the two rooms are one').toBe(roomsBefore - 1);

  // (e) a line drawn with the tool (two clicks, each end snapped) is a closing line too
  await page.getByTestId('check-tool').selectOption('draw-line');
  await expect(T(page, TID.drawLineHint)).toBeVisible();
  const n0 = s.fixes.closings!.length;
  await clickPlan(page, [8.0, 1.0]);
  await clickPlan(page, [8.0, 2.0]);
  s = await settingsNow(page, request, projectId, buildId);
  expect(s.fixes.closings!.length).toBe(n0 + 1);
  expect(s.fixes.closings!.at(-1)).toMatchObject({ floor: G, use: 'line' });

  // (f) Remove in "Fixes on this floor" takes a fix back: the room's "no floor here", and the drawn line
  await page.locator(`${tidSel(TID.fixRow)}[data-kind=room]`).locator(tidSel(TID.fixRemove)).click();
  s = await settingsNow(page, request, projectId, buildId);
  expect(s.fixes.rooms ?? []).toEqual([]);
  const lastLine = s.fixes.closings!.length - 1;
  await page.locator(`${tidSel(TID.fixRow)}[data-kind=closing][data-index="${lastLine}"]`).locator(tidSel(TID.fixRemove)).click();
  s = await settingsNow(page, request, projectId, buildId);
  expect(s.fixes.closings!.length).toBe(n0);
  await expect(page.locator(tidSel(TID.fixRow))).toHaveCount(n0 + (s.fixes.stairs ?? []).length);

  // saved, so that the e2e project has a version (web.spec.ts reads every card)
  d = await rebuild(page, request, projectId, buildId, d);
  await goStep(page, 'save');
  await expect(page.locator(`[data-testid=save-summary] ${tidSel(TID.roomCounts)}`)).toHaveCount(2);
  await expect(page.getByTestId('save-build')).toBeEnabled();
  await page.getByTestId('save-build').click();
  await expect(page).toHaveURL(new RegExp(`/projects/${projectId}/v/1$`), { timeout: 60_000 });
  expect(dialogs).toEqual([]);
});

// ================================================================================================================= 2.
test('RA-12 point 1: the house as a new project, built the new way, named, saved as built-model/2, climbed', async ({ page, request }, testInfo) => {
  test.skip(MOCK_API, 'the house needs the real reader and worker (the mock reads every DWG as the bank)');
  test.setTimeout(40 * 60_000);
  const dialogs = noDialogs(page);
  const projectId = 'e2e-house-rooms';
  await newProject(page, 'E2E House rooms', projectId);
  await uploadAndContinue(page, [HOUSE_DWG]);
  const buildId = await buildIdOf(page);
  const read = await waitForReading(request, projectId, buildId);
  await expect(page.locator('[data-testid=source-card] [data-testid=source-verdict]')).toHaveCount(1, { timeout: 30_000 });
  // Layers: three roles with the selects, the rest merged from the fixture (layers, floors, furniture only)
  const fx = fixture('upload', 'settings', 'house-rooms.json');
  await goStep(page, 'layers');
  const three = Object.entries(fx.layers).filter(([, r]) => r === 'wall' || r === 'door' || r === 'stair').slice(0, 3);
  for (const [layer, role] of three) {
    await page.locator(`[data-testid=layer-row][data-layer="${layer}"] [data-testid=role-select]`).selectOption(role);
  }
  await settingsSaved(page);
  const afterLayers = await getBuild(request, projectId, buildId);
  expect(afterLayers.settings!.options).toMatchObject(NEW_RULES);
  await putBuildSettings(request, projectId, buildId, merged(afterLayers, fx, { ceilings: false }));
  await page.reload();
  // Floors: the two boxes and levels from the fixture, walls 3.90 / 3.50, the ceiling heights typed 3.00 / 2.90
  await goStep(page, 'floors');
  const cards = page.locator('[data-testid=floor-card]');
  await expect(cards).toHaveCount(2);
  await expect(cards.nth(0).locator('[data-testid=floor-wall-height]')).toHaveValue('3.9');
  await expect(cards.nth(1).locator('[data-testid=floor-wall-height]')).toHaveValue('3.5');
  for (const [i, v] of [[0, '3.00'], [1, '2.90']] as const) {
    await cards.nth(i).locator(tidSel(TID.ceilingHeight)).fill(v);
    await cards.nth(i).locator(tidSel(TID.ceilingHeight)).press('Enter');
  }
  await settingsSaved(page);
  await expect(T(page, TID.rulesLine)).toHaveAttribute('data-rules', 'new');
  const before = (await getBuild(request, projectId, buildId)).settings!;
  expect(before.options.slabs).toBe('network');
  expect(before.floors.map(f => f.ceilingHeight)).toEqual([3, 2.9]);
  // Build -> Check: the page's counts are the overlay's
  await goStep(page, 'build');
  await page.getByTestId('run-build').click();
  let d = await waitForResult(page, request, projectId, buildId, null);
  await goStep(page, 'check');
  let ov = await overlayOf(request, d);
  for (const f of ov.floors) await countsMatch(page, ov, f.key);
  // name the living room (the ground floor's largest room) "Living" with the room panel -> waiting -> Rebuild -> named
  await page.locator('[data-testid=check-floor][data-key="ground"]').click();
  await page.getByTestId('check-tool').selectOption('rooms');
  const living = (await hookSpaces(page)).sort((a, b) => b.area - a.area)[0]!;
  await clickPlan(page, living.at);
  await expect(T(page, TID.roomPanel)).toHaveAttribute('data-id', living.id);
  await T(page, TID.roomName).fill('Living');
  await T(page, TID.roomName).press('Enter');
  await expect(T(page, TID.roomPanel).locator(tidSel(TID.fixWaiting))).toBeVisible({ timeout: 30_000 });
  d = await rebuild(page, request, projectId, buildId, d);
  ov = await overlayOf(request, d);
  const named = ov.floors.find(f => f.key === 'ground')!.spaces!.find(x => x.name === 'Living');
  expect(named, 'the overlay names the living room').toBeTruthy();
  // Save -> version.json says built-model/2 -> the version opens in the viewer
  await goStep(page, 'save');
  await page.getByTestId('save-build').click();
  await expect(page).toHaveURL(new RegExp(`/projects/${projectId}/v/1$`), { timeout: 60_000 });
  const versionJson = JSON.parse(readFileSync(path.join(TMP, 'data', 'projects', projectId, 'versions', '1', 'version.json'), 'utf8'));
  expect(versionJson.modelFormat).toBe('built-model/2');
  await viewerReady(page, 1);
  // Walk: from the main stair's bottom up three risers (the stair probe), then on to the upper floor: "upper" is marked
  const model = await page.evaluate(() => (window as any).__host.model);
  const main = (model.stairways as any[]).find(x => x.from === 'ground' && x.to === 'upper');
  expect(main, 'the main stair climbs from ground to upper').toBeTruthy();
  const riser = (model.floors.find((f: any) => f.key === 'upper').level - model.floors.find((f: any) => f.key === 'ground').level) / main.risers;
  const [three3] = await stairWalks(page, { stair: main.id, rise: 3 * riser });
  expect(three3, 'a walk up three risers').toBeTruthy();
  expect(await page.evaluate(() => (window as any).__viewer.probe.foot()) - model.floors.find((f: any) => f.key === 'ground').level).toBeGreaterThanOrEqual(3 * riser - 0.01);
  await stairWalks(page, { stair: main.id });
  await expect(page.locator(sel.floorButton('upper'))).toHaveAttribute('aria-pressed', 'true', { timeout: 30_000 });
  // the Max download holds the treads
  const ms = await download(page, 'maxScript', testInfo);
  expect(ms.bytes.toString('utf8')).toContain('#tread');
  expect(dialogs).toEqual([]);
});

// ================================================================================================================= 3.
test('RA-12 point 2: a project saved before this milestone gets the new rules with its next version, without the Floors step', async ({ page, request }) => {
  test.skip(MOCK_API, 'the saved recipe is edited in the real store and built by the real worker');
  test.setTimeout(30 * 60_000);
  const dialogs = noDialogs(page);
  const projectId = 'e2e-rooms-before';
  await newProject(page, 'E2E Rooms before', projectId);
  await uploadAndContinue(page, referenceDxfs());
  let buildId = await buildIdOf(page);
  // set-up through the API: built the earlier way, saved as version 1
  const read = await waitForReading(request, projectId, buildId);
  const earlier = merged(read, fixture('rooms', 'settings.reference.json'));
  await putBuildSettings(request, projectId, buildId, { ...earlier, options: { ...earlier.options, ...OLD_RULES } });
  const run = await request.post(`/api/projects/${projectId}/builds/${buildId}/run`, { data: {} });
  expect(run.status()).toBe(202);
  await waitForResult(page, request, projectId, buildId, null);
  const saved = await request.post(`/api/projects/${projectId}/builds/${buildId}/save`, { data: { label: 'before the milestone', carryHeights: false, rememberMapping: false } });
  expect(saved.status(), await saved.text()).toBe(201);
  // a recipe saved before this milestone is exactly a recipe without the three keys
  const v1 = path.join(TMP, 'data', 'projects', projectId, 'versions', '1');
  const recipeFile = path.join(v1, 'project-data.json');
  const recipe = JSON.parse(readFileSync(recipeFile, 'utf8'));
  for (const k of ['slabs', 'ceilings', 'stairs']) delete recipe.options[k];
  writeFileSync(recipeFile, `${JSON.stringify(recipe, null, 2)}\n`, 'utf8');
  const filesOf = (dir: string): Record<string, string> => {
    const out: Record<string, string> = {};
    const walk = (d: string) => {
      for (const n of readdirSync(d)) {
        const p = path.join(d, n);
        if (statSync(p).isDirectory()) walk(p); else out[path.relative(dir, p)] = createHash('sha1').update(readFileSync(p)).digest('hex');
      }
    };
    walk(dir);
    return out;
  };
  const v1Files = filesOf(v1);
  // New version -> the same drawing -> Build, without opening the Floors step
  await page.goto(`/projects/${projectId}/builds/new`);
  await page.getByTestId('reuse-files').click();
  await expect(page).toHaveURL(/\/builds\/\d{8}T\d{6}-[0-9a-f]{6}/);
  buildId = await buildIdOf(page);
  await waitForReading(request, projectId, buildId);
  await goStep(page, 'build');
  await expect(T(page, TID.rulesLine)).toHaveAttribute('data-rules', 'new');
  expect((await getBuild(request, projectId, buildId)).settings!.options).toMatchObject(NEW_RULES);
  await page.getByTestId('run-build').click();
  const d = await waitForResult(page, request, projectId, buildId, null);
  await goStep(page, 'check');
  await expect(T(page, TID.rulesLine)).toHaveAttribute('data-rules', 'new');
  const ov = await overlayOf(request, d);
  expect(ov.floors[0]!.stairs!.some(x => x.state === 'climb'), 'the stair is climbable').toBe(true);
  expect(ov.flags.some(f => f.kind === 'slab-gap' && f.floor === ov.floors[0]!.key), 'the room behind the gap has its flag').toBe(true);
  await goStep(page, 'save');
  await page.getByTestId('save-build').click();
  await expect(page).toHaveURL(new RegExp(`/projects/${projectId}/v/2$`), { timeout: 60_000 });
  const v2 = JSON.parse(readFileSync(path.join(TMP, 'data', 'projects', projectId, 'versions', '2', 'version.json'), 'utf8'));
  expect(v2.modelFormat).toBe('built-model/2');
  expect(filesOf(v1), 'version 1 is unchanged').toEqual(v1Files);
  expect(dialogs).toEqual([]);
});

// keep the helper used (the reference building's areas, for a spec that probes a point inside one)
void insideOf;
