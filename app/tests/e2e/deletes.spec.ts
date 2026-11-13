// Deleting a version and a project through the staff app's screens, in Edge (the owner's request of 12 Nov 2026;
// docs/contract-issues/DEL.md): the project page's "..." menu deletes the version on screen (Cancel in the browser's
// confirm first: nothing happens) and opens the latest remaining one; the only version cannot be deleted; Delete project
// goes to the list; a card's Delete on the list removes that project. Only projects this spec makes (ids e2e-del-*).
//
// Like web.spec.ts it runs against the mock API or the real one (apps/web/test/e2e/web-kit.ts reads which):
//   * mock (WT_SERVE=web): this spec starts its own mock on WT_API_PORT and makes its two projects in it, each version
//     saved from a draft as the mock saves them:
//       WT_WEB_PORT=5749 WT_API_PORT=8749 WT_TMP="$TEMP/wt-del" WT_SERVE=web WT_SKIP_STORE_CHECK=1 VITE_FAKE_VIEWER=1 \
//         npx playwright test -c tests/e2e/playwright.config.ts --project=e2e tests/e2e/deletes.spec.ts
//   * real API (Playwright serves a freshly seeded store in WT_TMP/data): the spec copies the seeded bank (two versions)
//     to its own project ids in that store, then deletes through the screens and checks the API's answers and the
//     store's folders (the tombstone):
//       WT_WEB_PORT=5749 WT_API_PORT=8749 WT_TMP="$TEMP/wt-del" WT_SKIP_STORE_CHECK=1 \
//         npx playwright test -c tests/e2e/playwright.config.ts --project=e2e tests/e2e/deletes.spec.ts
import { cpSync, existsSync, readdirSync, readFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { expect, test, type APIRequestContext, type Page } from '@playwright/test';
import { API_PORT, MOCK_API } from '../../apps/web/test/e2e/web-kit';
import { createMockApi, type MockApi } from '../../apps/web/test/mock-api/core';
import { startMockServer, type MockServer } from '../../apps/web/test/mock-api/server';
import { TARGET, TMP } from './lib/target';

test.skip(TARGET === 'prototype', 'the staff app\'s screens (E2E_TARGET=app)');

const VERSION_PROJECT = 'e2e-del-versions';
const CARD_PROJECT = 'e2e-del-card';
const STORE = path.join(TMP, 'data', 'projects');

let server: MockServer | null = null;
test.beforeAll(async () => {
  if (MOCK_API && !server) server = await startMockServer(API_PORT, createMockApi());
});
test.afterAll(async () => {
  await server?.close();
  server = null;
});

/** A project with two versions (the bank's), under `id`. */
function makeProject(id: string, name: string): void {
  if (server) {
    const mock: MockApi = server.mock;
    const r = mock.handle({ method: 'POST', path: '/api/projects', body: JSON.stringify({ name, shortName: name, id }) });
    expect(r.status, r.body.toString()).toBe(201);
    for (const file of ['first.dwg', 'second.dwg']) {
      const src = mock.uploads.addSource(id, { name: file, bytes: Buffer.from(`AC1032 ${file}`) });
      const b = mock.uploads.createBuildNow(id, [src.sha1], { built: true });
      const s = mock.handle({ method: 'POST', path: `/api/projects/${id}/builds/${b.id}/save`, body: JSON.stringify({ label: file, carryHeights: false, rememberMapping: false }) });
      expect(s.status, s.body.toString()).toBe(201);
    }
    return;
  }
  // the real store: a copy of the seeded bank, renamed (meta.json and each version.json name their project)
  const from = path.join(STORE, 'bank-sampeng');
  const to = path.join(STORE, id);
  expect(existsSync(from), `the seeded store at ${STORE}`).toBe(true);
  cpSync(from, to, { recursive: true });
  const meta = JSON.parse(readFileSync(path.join(to, 'meta.json'), 'utf8'));
  writeFileSync(path.join(to, 'meta.json'), `${JSON.stringify({ ...meta, id, name }, null, 2)}\n`);
  for (const n of readdirSync(path.join(to, 'versions'))) {
    const file = path.join(to, 'versions', n, 'version.json');
    const v = JSON.parse(readFileSync(file, 'utf8'));
    writeFileSync(file, `${JSON.stringify({ ...v, projectId: id }, null, 2)}\n`);
  }
}

async function project(request: APIRequestContext, id: string): Promise<{ status: number; versions: number[]; latest: number }> {
  const r = await request.get(`/api/projects/${id}`);
  if (r.status() !== 200) return { status: r.status(), versions: [], latest: 0 };
  const p = await r.json();
  return { status: 200, versions: p.versions.map((v: { version: number }) => v.version), latest: p.latestVersion };
}

/** Opens the project page's "..." menu. */
async function actions(page: Page): Promise<void> {
  await page.getByTestId('project-actions').click();
  await expect(page.getByTestId('project-actions-list')).toBeVisible();
}

/** Answers the next confirm (accept or dismiss) and returns its text. */
function nextConfirm(page: Page, accept: boolean): Promise<string> {
  return new Promise(resolve => {
    page.once('dialog', d => {
      expect(d.type()).toBe('confirm');
      resolve(d.message());
      void (accept ? d.accept() : d.dismiss());
    });
  });
}

test('delete a version, then the project, through the project page', async ({ page, request }) => {
  makeProject(VERSION_PROJECT, 'E2E delete versions');
  expect(await project(request, VERSION_PROJECT)).toEqual({ status: 200, versions: [1, 2], latest: 2 });
  await page.goto(`/projects/${VERSION_PROJECT}/v/2`);
  await expect(page.getByTestId('project-page')).toHaveAttribute('data-version', '2');

  // Cancel: nothing is sent, nothing changes
  await actions(page);
  await expect(page.getByTestId('delete-version')).toHaveText('Delete this version (v2)');
  let asked = nextConfirm(page, false);
  await page.getByTestId('delete-version').click();
  expect(await asked).toBe('Delete version 2 of E2E delete versions? This cannot be undone. Version numbers are not reused.');
  await page.waitForTimeout(300);
  expect(await project(request, VERSION_PROJECT)).toEqual({ status: 200, versions: [1, 2], latest: 2 });
  await expect(page).toHaveURL(new RegExp(`/projects/${VERSION_PROJECT}/v/2$`));

  // OK: the version goes and the latest remaining one opens, in place of the deleted one's history entry
  await actions(page);
  asked = nextConfirm(page, true);
  await page.getByTestId('delete-version').click();
  await asked;
  await expect(page).toHaveURL(new RegExp(`/projects/${VERSION_PROJECT}/v/1$`));
  await expect(page.getByTestId('project-page')).toHaveAttribute('data-version', '1');
  expect(await project(request, VERSION_PROJECT)).toEqual({ status: 200, versions: [1], latest: 1 });
  const gone = await request.get(`/api/projects/${VERSION_PROJECT}/versions/2`);
  expect(gone.status()).toBe(404);
  expect((await gone.json()).error.message).toBe(`version 2 of '${VERSION_PROJECT}' was deleted`);
  if (!server) {
    // the real store: the folder keeps only its tombstone
    expect(readdirSync(path.join(STORE, VERSION_PROJECT, 'versions', '2'))).toEqual(['deleted.json']);
  }
  await page.getByTestId('version-picker').click();
  await expect(page.getByTestId('version-option')).toHaveCount(1);
  await page.keyboard.press('Escape');

  // the only version: the item is disabled and says to delete the project instead
  await actions(page);
  await expect(page.getByTestId('delete-version')).toHaveAttribute('data-disabled', '');
  await expect(page.getByTestId('delete-version-note')).toHaveText("This is the project's only version: delete the project instead.");

  // Delete project: to the project list, the project gone
  asked = nextConfirm(page, true);
  await page.getByTestId('delete-project').click();
  expect(await asked).toMatch(/^Delete E2E delete versions\? Its 1 version and uploaded drawings are removed from this computer\. This cannot be undone\.$/);
  await expect(page).toHaveURL(/\/projects$/);
  await expect(page.getByTestId('project-grid')).toBeVisible();
  await expect(page.locator(`[data-testid=project-card][data-project-id="${VERSION_PROJECT}"]`)).toHaveCount(0);
  expect((await project(request, VERSION_PROJECT)).status).toBe(404);
  if (!server) expect(existsSync(path.join(STORE, VERSION_PROJECT))).toBe(false);
  // Back does not return to the deleted project's page (its entries were replaced)
  await page.goBack();
  await expect(page).not.toHaveURL(new RegExp(`/projects/${VERSION_PROJECT}/v/2$`));
});

test('delete a project from its card on the project list', async ({ page, request }) => {
  makeProject(CARD_PROJECT, 'E2E delete card');
  await page.goto('/projects');
  const card = page.locator(`[data-testid=project-card][data-project-id="${CARD_PROJECT}"]`);
  await expect(card).toHaveCount(1);
  const others = await page.getByTestId('project-card').count();
  // Cancel first
  let asked = nextConfirm(page, false);
  await card.getByTestId('card-delete').click();
  expect(await asked).toBe('Delete E2E delete card? Its 2 versions and uploaded drawings are removed from this computer. This cannot be undone.');
  await page.waitForTimeout(300);
  await expect(card).toHaveCount(1);
  expect((await project(request, CARD_PROJECT)).status).toBe(200);
  // then OK
  asked = nextConfirm(page, true);
  await card.getByTestId('card-delete').click();
  await asked;
  await expect(card).toHaveCount(0);
  await expect(page.getByTestId('project-card')).toHaveCount(others - 1);
  expect((await project(request, CARD_PROJECT)).status).toBe(404);
  await expect(page).toHaveURL(/\/projects$/);
});
