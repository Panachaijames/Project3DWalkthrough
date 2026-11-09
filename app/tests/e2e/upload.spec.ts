// The staff path in Edge (docs/upload/ACCEPTANCE.md A-7; DESIGN.md U-2, U-14; WORK_BREAKDOWN U6): New project (a new office
// "E2E Revit") -> upload the bank's two DWGs -> leave (the project list's card leads to the draft; the draft is listed on
// the project's page with Continue) -> Files (verdicts ok) -> Layers (three roles changed with the selects, the rest by
// applying the fixture settings through the API) -> Floors (levels typed, 0 and 3.7) -> Build (the checklist clear,
// progress seen, done) -> Check (one item set aside; rebuild; the diff shows the change; restore; rebuild; no change
// against the first build; one whole block set aside with the block pick mode: one ref in the settings) -> Save (a double
// click makes one version) -> the version page shows the viewer with one canvas, live() === 1 -> the CSV download equals
// v2's and the Max script the upload-profile script (generated at test time with the build's date; the mock serves the
// bank's). A second test uploads a synthetic DXF with hostile names and walks every step: nothing injected, no dialog,
// the names shown as text. Projects made here use ids e2e-* (U-15.3).
//
// U6 alone, against the mock API and the fake viewer (Git Bash, from app/):
//   WT_WEB_PORT=5736 WT_API_PORT=8736 WT_TMP="$TEMP/wt-u6" WT_SERVE=web WT_SKIP_STORE_CHECK=1 VITE_FAKE_VIEWER=1 \
//     npx playwright test -c tests/e2e/playwright.config.ts --project=e2e tests/e2e/upload.spec.ts
// At integration: the real API and worker (`npm run test:e2e`; the e2e store is seeded fresh, U-15.3).
import { readFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { expect, test, type Page } from '@playwright/test';
import { formatDate } from '../../apps/web/src/lib/format';
import type { BuildSettings } from '../../apps/web/src/upload/contracts';
import { backend, download, facts, MOCK_API, useApi, viewerReady } from '../../apps/web/test/e2e/web-kit';
import {
  BANK_DWGS, buildIdOf, getBuild, itemInBlock, itemOn, makeHostileDxf, planOf, putBuildSettings, settingsSaved,
  uploadProfileScript, waitForReading, waitForResult,
} from '../../apps/web/test/e2e/upload-kit';
import { BUILD_FILES } from '../../apps/web/test/mock-api/builds';
import { FIXTURES_DIR } from '../../apps/web/test/mock-api/fixtures';
import { TARGET } from './lib/target';

test.skip(TARGET === 'prototype', 'the upload screens are the staff app\'s (E2E_TARGET=app)');
useApi();

const HOSTILE_TEXTS = ['A-WALL<img src=x onerror=alert(1)>', 'A-DOOR</script><script>alert(2)</script>'];

/** Fails the test on any dialog (alert, confirm): drawing text must never run. */
function noDialogs(page: Page): string[] {
  const seen: string[] = [];
  page.on('dialog', d => { seen.push(d.message()); void d.dismiss(); });
  return seen;
}

async function goStep(page: Page, step: string) {
  await page.getByTestId(`step-${step}`).click();
  await expect(page.getByTestId('build-page')).toHaveAttribute('data-step', step);
}

async function newProject(page: Page, name: string, id: string, office: { newName?: string; id?: string }) {
  await page.goto('/projects');
  await page.getByTestId('new-project').click();
  await expect(page).toHaveURL(/\/projects\/new$/);
  await expect(page).toHaveTitle('New project · Walkthrough');
  await page.getByTestId('np-name').fill(name);
  await page.getByTestId('np-id').fill(id);
  if (office.newName) {
    await page.getByTestId('office-select').selectOption('__new__');
    await page.getByTestId('new-office-name').fill(office.newName);
  } else if (office.id) {
    await page.getByTestId('office-select').selectOption(office.id);
  }
  await page.getByTestId('np-create').click();
  await expect(page).toHaveURL(new RegExp(`/projects/${id}/builds/new$`));
  await expect(page.getByTestId('upload-page')).toBeVisible();
}

async function uploadAndContinue(page: Page, files: string[]) {
  await page.getByTestId('file-input').setInputFiles(files);
  await expect(page.locator('[data-testid=upload-row][data-state=done]')).toHaveCount(files.length, { timeout: 120_000 });
  await page.getByTestId('start-build').click();
  await expect(page).toHaveURL(/\/builds\/\d{8}T\d{6}-[0-9a-f]{6}\?step=files$/);
}

test('A-7: the staff path from a new project to a saved version (the bank\'s two DWGs)', async ({ page, request }, testInfo) => {
  // one reading and four builds, each polled for up to 8 min on a busy laptop (8.4 min in all at UR's re-run, 5.2 at
  // integration: UR, V1-7)
  test.setTimeout(20 * 60_000);
  const dialogs = noDialogs(page);
  const projectId = 'e2e-bank';
  await newProject(page, 'E2E Bank', projectId, { newName: 'E2E Revit' });
  await uploadAndContinue(page, BANK_DWGS);
  const buildId = await buildIdOf(page);

  // leave: the project list's card leads to the draft; the project's page lists it with Continue
  await page.getByTestId('back-to-projects').click();
  const card = page.locator(`[data-testid=project-card][data-project-id="${projectId}"]`);
  await expect(card.getByTestId('card-link')).toHaveAttribute('href', `/projects/${projectId}/builds/${buildId}`);
  await page.goto(`/projects/${projectId}`);
  const row = page.locator(`[data-testid=draft-row][data-build-id="${buildId}"]`);
  await expect(row.getByTestId('draft-files')).toHaveText(BANK_DWGS.map(f => path.basename(f)).join(', '));
  await row.getByTestId('draft-continue').click();
  await expect(page).toHaveURL(new RegExp(`/builds/${buildId}$`));

  // Files: both read, verdicts ok (the reading waited for by polling the build: a busy laptop took 159 s, UR V1-7)
  await waitForReading(request, projectId, buildId);
  await expect(page.locator('[data-testid=source-card] [data-testid=source-verdict]')).toHaveCount(2, { timeout: 30_000 });
  await expect(page.locator('[data-testid=source-card] [data-testid=source-verdict][data-verdict=ok]')).toHaveCount(2);
  await expect(page.locator('[data-testid=source-card] [data-testid=units-select]').first()).toBeEnabled({ timeout: 60_000 });

  // Layers: three roles changed with the selects, then the fixture settings through the API (the office kept)
  await goStep(page, 'layers');
  for (const [layer, role] of [['A-DETL', 'ignore'], ['A-FLOR', 'ignore'], ['E-COMM', 'other']] as const) {
    await page.locator(`[data-testid=layer-row][data-layer="${layer}"] [data-testid=role-select]`).selectOption(role);
  }
  await settingsSaved(page);
  const saved = await getBuild(request, projectId, buildId);
  expect(saved.layersReviewedAt).not.toBeNull();
  expect([saved.settings!.layers['A-DETL'], saved.settings!.layers['A-FLOR'], saved.settings!.layers['E-COMM']]).toEqual(['ignore', 'ignore', 'other']);
  const fixture = JSON.parse(readFileSync(path.join(FIXTURES_DIR, 'upload', 'settings', 'bank.json'), 'utf8')) as BuildSettings;
  const byName = new Map(saved.sources.map(s => [s.name, s.sha1]));
  const mapped: BuildSettings = {
    ...fixture,
    office: saved.settings!.office,
    sources: fixture.sources.map(s => ({ ...s, sha1: byName.get(s.name)! })),
    floors: fixture.floors.map(f => ({ ...f, source: byName.get(fixture.sources.find(s => s.sha1 === f.source)!.name)! })),
  };
  expect(mapped.office).toBe('e2e-revit');
  await putBuildSettings(request, projectId, buildId, mapped);
  await page.reload();
  await expect(page.locator('[data-testid=layer-row][data-layer="A-DETL"] [data-testid=role-select]')).toHaveValue('other');

  // Floors: levels typed, 0 and 3.7
  await goStep(page, 'floors');
  await page.locator('[data-testid=floor-card][data-index="0"] [data-testid=floor-level]').fill('0');
  await page.locator('[data-testid=floor-card][data-index="0"] [data-testid=floor-level]').press('Enter');
  await page.locator('[data-testid=floor-card][data-index="1"] [data-testid=floor-level]').fill('3.7');
  await page.locator('[data-testid=floor-card][data-index="1"] [data-testid=floor-level]').press('Enter');
  await expect(page.getByTestId('floor-issues')).toHaveCount(0);
  await settingsSaved(page);

  // Build: the checklist clear, progress seen, done
  await goStep(page, 'build');
  await expect(page.getByTestId('checklist-clear')).toBeVisible();
  await page.getByTestId('run-build').click();
  await expect(page.locator('[data-testid=run-panel][data-kind=build]')).toBeVisible();
  // queued while another run holds the machine's lock: as long as waitForResult allows (UR, V1-7)
  await expect(page.locator('[data-testid=run-panel][data-kind=build][data-status=running]')).toBeVisible({ timeout: 8 * 60_000 });
  const first = await waitForResult(page, request, projectId, buildId, null);
  await expect(page.getByTestId('build-result')).toHaveAttribute('data-run', first.result!.runId, { timeout: 30_000 });

  // Check: one item set aside, rebuild, the diff shows it; restore, rebuild, the same as the first build
  await goStep(page, 'check');
  const plan1 = await planOf(request, first.sources[0]!.urls!.plan);
  const item = itemOn(plan1, 'A-WALL');
  await page.getByTestId('find-items').fill(item);
  await page.locator(`[data-testid=find-result][data-key="${item}"]`).click();
  await expect(page.getByTestId('selection-count')).toHaveText('1 selected');
  await page.getByTestId('set-aside').click();
  await settingsSaved(page);
  expect((await getBuild(request, projectId, buildId)).settings!.fixes.setAside.map(r => r.key)).toEqual([item]);
  await page.getByTestId('rebuild').click();
  const second = await waitForResult(page, request, projectId, buildId, first.result!.runId);
  await expect(page.locator('[data-testid=diff-panel][data-against=previous-run]')).toBeVisible({ timeout: 30_000 });
  await expect(page.locator('[data-testid=diff-panel][data-against=previous-run]')).not.toHaveAttribute('data-same', '');
  await page.locator(`[data-testid=set-aside-row][data-key="${item}"] [data-testid=restore-one]`).click();
  await settingsSaved(page);
  await page.getByTestId('rebuild').click();
  const third = await waitForResult(page, request, projectId, buildId, second.result!.runId);
  expect(third.result!.counts).toEqual(first.result!.counts);
  expect(third.result!.floors).toEqual(first.result!.floors);

  // the whole-block pick mode: one ref, the INSERT's anchor; then restored (the saved model has no fixes)
  const block = itemInBlock(plan1);
  await page.getByTestId('pick-mode').selectOption('block');
  await page.getByTestId('find-items').fill(block.key);
  await page.locator(`[data-testid=find-result][data-key="${block.key}"]`).click();
  await page.getByTestId('set-aside').click();
  await settingsSaved(page);
  expect((await getBuild(request, projectId, buildId)).settings!.fixes.setAside.map(r => r.key)).toEqual([block.anchor]);
  await page.locator(`[data-testid=set-aside-row][data-key="${block.anchor}"] [data-testid=restore-one]`).click();
  await settingsSaved(page);
  expect((await getBuild(request, projectId, buildId)).settings!.fixes.setAside).toEqual([]);
  await page.getByTestId('rebuild').click();
  const last = await waitForResult(page, request, projectId, buildId, third.result!.runId);

  // Save: a double click makes one version
  const saves: string[] = [];
  page.on('request', r => { if (r.method() === 'POST' && r.url().endsWith(`/builds/${buildId}/save`)) saves.push(r.url()); });
  await goStep(page, 'save');
  await expect(page.getByTestId('save-build')).toBeEnabled();
  await page.getByTestId('save-build').dblclick();
  await expect(page).toHaveURL(new RegExp(`/projects/${projectId}/v/1$`), { timeout: 60_000 });
  expect(saves.length).toBe(1);
  const list = await backend(request).list();
  expect(list.find(p => p.id === projectId)?.versionCount).toBe(1);

  // the version page: one viewer, one canvas
  await viewerReady(page, 1);
  expect(await facts(page)).toMatchObject({ live: 1, canvases: 1 });

  // the downloads: the CSV equals v2's; the Max script the upload profile's (the bank's in the mock)
  const csv = await download(page, 'furnitureCsv', testInfo);
  expect(csv.bytes.equals(readFileSync(path.join(FIXTURES_DIR, 'csv', 'bank-v2.csv')))).toBe(true);
  const ms = await download(page, 'maxScript', testInfo);
  if (MOCK_API) {
    expect(ms.bytes.equals(readFileSync(BUILD_FILES.maxScript))).toBe(true);
  } else {
    const model = await request.get(`/api/projects/${projectId}/versions/1/model`);
    const modelFile = testInfo.outputPath('model.json');
    writeFileSync(modelFile, await model.body());
    const expected = uploadProfileScript(modelFile, last.sourceNames, formatDate(last.result!.finishedAt), testInfo.outputPath('.'));
    expect(ms.bytes.equals(expected)).toBe(true);
  }
  expect(dialogs).toEqual([]);
});

test('A-7: a DXF with hostile names through every step: shown as text, nothing injected, no dialog', async ({ page, request }, testInfo) => {
  test.setTimeout(10 * 60_000);
  const dialogs = noDialogs(page);
  const projectId = 'e2e-hostile';
  await newProject(page, 'E2E Hostile <img src=x onerror=alert(9)>', projectId, {});
  const dxf = makeHostileDxf(testInfo.outputPath("E2E $' &amp; hostile.dxf"));
  await uploadAndContinue(page, [dxf]);
  const buildId = await buildIdOf(page);
  const injected = () => page.evaluate(() => ({
    imgs: document.querySelectorAll('img[src="x"], [onerror]').length,
    scripts: [...document.querySelectorAll('script')].filter(s => /alert\(/.test(s.textContent ?? '')).length,
  }));
  await expect(page.locator('[data-testid=source-card] [data-testid=source-name]')).toHaveText("E2E $' &amp; hostile.dxf");
  await waitForReading(request, projectId, buildId);                     // polled, not a fixed wait (UR, V1-7)
  await expect(page.locator('[data-testid=source-card] [data-testid=units-select]')).toBeEnabled({ timeout: 30_000 });
  await expect(page.getByTestId('build-project-name')).toHaveText('E2E Hostile <img src=x onerror=alert(9)>');
  for (const step of ['layers', 'floors', 'build']) {
    await goStep(page, step);
    if (step === 'layers') {
      for (const t of HOSTILE_TEXTS) await expect(page.locator('[data-testid=layer-name]', { hasText: t }).first()).toBeVisible();
    }
    expect(await injected()).toEqual({ imgs: 0, scripts: 0 });
  }
  await settingsSaved(page);
  const before = await getBuild(request, projectId, buildId);
  if (!before.layersReviewedAt) throw new Error('the Layers step was seen: layersReviewed should be set');
  await expect(page.getByTestId('checklist-clear')).toBeVisible();
  await page.getByTestId('run-build').click();
  await waitForResult(page, request, projectId, buildId, null);
  for (const step of ['check', 'save']) {
    await goStep(page, step);
    expect(await injected()).toEqual({ imgs: 0, scripts: 0 });
  }
  // saved, so that the e2e project has a version (web.spec.ts checks every card of the list it reads)
  await expect(page.getByTestId('save-build')).toBeEnabled();
  await page.getByTestId('save-build').click();
  await expect(page).toHaveURL(new RegExp(`/projects/${projectId}/v/1$`), { timeout: 60_000 });
  await expect(page.getByTestId('app-bar-title')).toHaveText('E2E Hostile <img src=x onerror=alert(9)>');
  expect(await injected()).toEqual({ imgs: 0, scripts: 0 });
  expect(dialogs).toEqual([]);
});
