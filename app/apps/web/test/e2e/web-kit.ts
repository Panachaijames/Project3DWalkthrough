// Shared helpers of tests/e2e/web.spec.ts and web-leak.spec.ts (builder F; DESIGN.md 17.4 "web").
//
// The set-up is read from the environment, so the specs run unchanged in both:
//   * integration (WT_SERVE unset, or listing `api`): the real API (Playwright starts it over a temp copy of the seeded
//     store) and the real viewer;
//   * builder F alone (WT_SERVE=web, WT_SKIP_STORE_CHECK=1): no API server from Playwright; the specs start the mock API
//     (apps/web/test/mock-api/server.ts) on WT_API_PORT, behind the Vite proxy as the real one is, and VITE_FAKE_VIEWER=1
//     puts the fake viewer (apps/web/test/fake-viewer.ts) in place of @walkthrough/viewer.
// Every request the specs make goes to the web origin (127.0.0.1:WT_WEB_PORT) and its /api proxy: one path for both.
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { expect, test, type APIRequestContext, type Page, type TestInfo } from '@playwright/test';
import type { HeightMap } from '../../../../packages/viewer/src/contracts';
import type { ProjectSummary, VersionDetail } from '../../src/api/generated/types.gen';
import { APP_DIR } from '../mock-api/fixtures';
import { startMockServer, type MockServer } from '../mock-api/server';

export const SERVE = (process.env.WT_SERVE ?? 'api,web').split(',').map(s => s.trim()).filter(Boolean);
/** No API server from Playwright: the specs run the mock API themselves. */
export const MOCK_API = !SERVE.includes('api');
/** The web app was started with VITE_FAKE_VIEWER=1 (the fake viewer in place of @walkthrough/viewer). */
export const FAKE_VIEWER = process.env.VITE_FAKE_VIEWER === '1';
export const API_PORT = Number(process.env.WT_API_PORT ?? 8711);
export const PROJECT_IDS = ['bank-sampeng', 'hotel-lobby', 'presidential-suite', 'sukhumvit-house'];

// ------------------------------------------------------------------------------------------------------------ the API
let server: MockServer | null = null;

/** Registers the mock API server's start / stop around the spec file (only when MOCK_API). Call at the top level. */
export function useApi(): void {
  test.beforeAll(async () => {
    if (MOCK_API && !server) server = await startMockServer(API_PORT);
  });
  test.afterAll(async () => {
    await server?.close();
    server = null;
  });
}

export interface Backend {
  list(): Promise<ProjectSummary[]>;
  version(projectId: string, n: number): Promise<VersionDetail>;
  saved(projectId: string, n: number): Promise<HeightMap>;
  resetHeights(projectId: string, n: number): Promise<void>;
  /** The seeded copy of a version's download (real store), or the file the mock serves. */
  maxScriptFile(projectId: string, n: number, name: string): string;
}

/** The API as the page sees it, through the web origin's /api proxy (real or mock alike). */
export function backend(request: APIRequestContext): Backend {
  const getJson = async <T>(url: string): Promise<T> => {
    const r = await request.get(url);
    expect(r.status(), url).toBe(200);
    return (await r.json()) as T;
  };
  return {
    list: async () => (await getJson<{ projects: ProjectSummary[] }>('/api/projects')).projects,
    version: (id, n) => getJson<VersionDetail>(`/api/projects/${id}/versions/${n}`),
    saved: async (id, n) => (await getJson<{ heights: HeightMap }>(`/api/projects/${id}/versions/${n}/furniture-heights`)).heights,
    resetHeights: async (id, n) => {
      const r = await request.put(`/api/projects/${id}/versions/${n}/furniture-heights`, { data: { heights: {} } });
      expect(r.status(), `reset the heights of ${id} v${n}`).toBe(200);
    },
    maxScriptFile: (id, n, name) => {
      if (server) return server.mock.source(id, n)!.maxScript!.file;
      return path.join(APP_DIR, 'data', 'projects', id, 'versions', String(n), 'downloads', name);
    },
  };
}

// --------------------------------------------------------------------------------------------------------- the viewer
/** Waits until at least `created` viewers were made in this page and the current one is ready (test hook). */
export async function viewerReady(page: Page, created: number): Promise<void> {
  await page.waitForFunction(n => !!window.__walkthrough?.viewer && window.__walkthrough.created() >= n, created, { timeout: 60_000 });
  await page.evaluate(() => window.__walkthrough!.viewer.ready);
}

/** Viewers made and alive (test hook), canvases and viewer roots in the document. */
export async function facts(page: Page): Promise<{ created: number; live: number; canvases: number; roots: number }> {
  return page.evaluate(() => ({
    created: window.__walkthrough!.created(),
    live: window.__walkthrough!.live(),
    canvases: document.querySelectorAll('canvas').length,
    roots: document.querySelectorAll('[data-wt=root]').length,
  }));
}

export const heightBox = (page: Page, kind: string) => page.locator(`[data-wt=furniture-row][data-kind="${kind}"] [data-wt=kind-height]`);

/** Types a height into the viewer's legend (the box's text replaced, then Enter), as a user does. */
export async function typeHeight(page: Page, kind: string, mm: number): Promise<void> {
  const box = heightBox(page, kind);
  await box.fill(String(mm));
  await box.press('Enter');
}

/** Chooses a version in the app bar's picker and waits for its address. */
export async function pickVersion(page: Page, n: number): Promise<void> {
  await page.getByTestId('version-picker').click();
  await page.locator(`[data-testid=version-option][data-version="${n}"]`).click();
  await expect(page).toHaveURL(new RegExp(`/v/${n}(\\?|$)`));
}

export interface Saved { name: string; file: string; bytes: Buffer }

/** A file from the Downloads menu, saved under the test's output folder. */
export async function download(page: Page, key: 'maxScript' | 'furnitureCsv' | 'offlineHtml', testInfo: TestInfo): Promise<Saved> {
  await page.getByTestId('downloads-menu').click();
  const item = page.locator(`[data-testid=downloads-list] [data-download=${key}]`);
  await expect(item).toBeVisible();
  const [d] = await Promise.all([page.waitForEvent('download'), item.click()]);
  const name = d.suggestedFilename();
  const file = testInfo.outputPath(name);
  await d.saveAs(file);
  return { name, file, bytes: readFileSync(file) };
}

export interface OfflinePayloadLike {
  format: string;
  version: { stamp: string; projectId: string; version: number };
  overrides: { heights: HeightMap } | null;
}
/** The offline file's #wtv-data payload (DESIGN.md 16). */
export function offlinePayload(html: string): OfflinePayloadLike {
  const m = /<script type="application\/json" id="wtv-data">([\s\S]*?)<\/script>/.exec(html);
  if (!m) throw new Error('no #wtv-data in the offline file');
  return JSON.parse(m[1]!) as OfflinePayloadLike;
}
