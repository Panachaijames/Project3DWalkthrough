// RR (the rooms milestone's independent review and fix, area "web"; %TEMP%\wt-rr\TRIAGE.md S1, S2, S7) in Edge, on the
// reference building's Check step under the mock API: the layout fixes that only a real browser shows.
//   S1: with the window scrolled to the end of the flag list, Show on the last flag leaves the plan in view (the plan
//       column is sticky under the app bar, and Show brings the plan into view); on a laptop-sized window too.
//   S2: "Open this stair" on the stair card opens that stair's panel with the tool Rooms and stairs, the plan in view.
//   S7: the floor on screen is drawn whole inside the canvas (the floor's own fit; the unit tests check the sheet case).
// Mock API only (the layout does not depend on the worker; the real build of the reference building is rooms.spec.ts's):
//   WT_WEB_PORT=5749 WT_API_PORT=8749 WT_TMP="$TEMP/wt-rr/e2e" WT_SERVE=web WT_SKIP_STORE_CHECK=1 VITE_FAKE_VIEWER=1 \
//     npx playwright test -c tests/e2e/playwright.config.ts --project=e2e tests/e2e/rr-web.spec.ts
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { expect, test, type Page } from '@playwright/test';
import type { BuildDetail, BuildOverlay, BuildSettings } from '../../apps/web/src/upload/contracts';
import { MOCK_API, useApi } from '../../apps/web/test/e2e/web-kit';
import { buildIdOf, putBuildSettings, waitForReading, waitForResult } from '../../apps/web/test/e2e/upload-kit';
import { FIXTURES_DIR } from '../../apps/web/test/mock-api/fixtures';
import { TARGET, TMP } from './lib/target';

/* eslint-disable @typescript-eslint/no-explicit-any */
test.skip(TARGET === 'prototype', 'the staff app\'s screens (E2E_TARGET=app)');
test.skip(!MOCK_API, 'under the mock API only (WT_SERVE=web): a layout check');
useApi();

/** The mock knows the reference building by the two files' names; their contents do not matter to it (but must differ). */
function referenceNames(): string[] {
  const dir = path.join(TMP, 'rr-web-spec', 'dxf');
  mkdirSync(dir, { recursive: true });
  return ['ground', 'upper'].map(k => {
    const f = path.join(dir, `rooms-reference-${k}.dxf`);
    // two different files (the same bytes would be one source): a DXF comment names the floor
    if (!existsSync(f)) writeFileSync(f, `999\r\n${k}\r\n  0\r\nSECTION\r\n  2\r\nENTITIES\r\n  0\r\nENDSEC\r\n  0\r\nEOF\r\n`, 'latin1');
    return f;
  });
}

function merged(draft: BuildDetail, fx: BuildSettings): BuildSettings {
  const s = draft.settings!;
  const byName = new Map(draft.sources.map(x => [x.name, x.sha1]));
  return {
    ...s,
    sources: s.sources.map(x => ({ ...x, unitsConfirmed: true })),
    layers: { ...s.layers, ...fx.layers },
    furniture: fx.furniture,
    floors: fx.floors.map(f => ({ ...f, source: byName.get(fx.sources.find(x => x.sha1 === f.source)!.name)! })),
  };
}

/** The element's box is wholly inside the window. */
async function inView(page: Page, testId: string): Promise<{ top: number; bottom: number; height: number; whole: boolean }> {
  return page.getByTestId(testId).evaluate(el => {
    const r = el.getBoundingClientRect();
    return { top: r.top, bottom: r.bottom, height: window.innerHeight, whole: r.top >= 0 && r.bottom <= window.innerHeight + 0.5 };
  });
}

async function openCheck(page: Page, request: any, projectId: string): Promise<BuildOverlay> {
  await page.goto('/projects');
  await page.getByTestId('new-project').click();
  await page.getByTestId('np-name').fill(`E2E ${projectId}`);
  await page.getByTestId('np-id').fill(projectId);
  await page.getByTestId('np-create').click();
  await expect(page).toHaveURL(new RegExp(`/projects/${projectId}/builds/new$`));
  await page.getByTestId('file-input').setInputFiles(referenceNames());
  await expect(page.locator('[data-testid=upload-row][data-state=done]')).toHaveCount(2, { timeout: 120_000 });
  await page.getByTestId('start-build').click();
  await expect(page).toHaveURL(/\/builds\/\d{8}T\d{6}-[0-9a-f]{6}\?step=files$/);
  const buildId = await buildIdOf(page);
  const read = await waitForReading(request, projectId, buildId);
  const fx = JSON.parse(readFileSync(path.join(FIXTURES_DIR, 'rooms', 'settings.reference.json'), 'utf8')) as BuildSettings;
  await putBuildSettings(request, projectId, buildId, merged(read, fx));
  await page.reload();
  await page.getByTestId('step-build').click();
  await page.getByTestId('run-build').click();
  const d = await waitForResult(page, request, projectId, buildId, null);
  await page.getByTestId('step-check').click();
  await expect(page.getByTestId('build-page')).toHaveAttribute('data-step', 'check');
  await expect(page.locator('[data-testid=flag]').first()).toBeVisible({ timeout: 30_000 });
  await expect.poll(() => page.evaluate(() => !!(window as any).__plan)).toBe(true);
  const r = await request.get(d.result!.urls.overlay);
  expect(r.status()).toBe(200);
  return (await r.json()) as BuildOverlay;
}

for (const [label, size] of [['the default window', null], ['a laptop-sized window', { width: 1366, height: 680 }]] as const) {
  test(`S1, S7 (${label}): Show on the last flag with the page scrolled to its end leaves the plan in view; the floor is whole on the canvas`, async ({ page, request }) => {
    test.setTimeout(4 * 60_000);
    if (size) await page.setViewportSize(size);
    const ov = await openCheck(page, request, size ? 'e2e-rr-web-s1-small' : 'e2e-rr-web-s1');
    // S7: every corner of the floor's plate is on the canvas
    const g = ov.floors[0]!;
    const xs = g.slabs.flatMap(s => s.o.map(p => p[0])), ys = g.slabs.flatMap(s => s.o.map(p => p[1]));
    const corners = [[Math.min(...xs), Math.min(...ys)], [Math.max(...xs), Math.max(...ys)]];
    for (const c of corners) expect(await page.evaluate(q => (window as any).__plan.toPage(q), c), `plate corner ${c}`).not.toBeNull();
    // S1: the window at the end of the page, then Show on the last flag
    await page.evaluate(() => window.scrollTo(0, document.documentElement.scrollHeight));
    const scrolled = await page.evaluate(() => window.scrollY);
    const last = page.locator('[data-testid=flag]').last();
    await last.getByTestId('flag-show').click();
    await expect(last).toHaveClass(/ring-2/);
    const box = await inView(page, 'check-canvas');
    expect(box.whole, `the plan's box ${JSON.stringify(box)} after Show (window scrolled by ${scrolled} px)`).toBe(true);
  });
}

test('S2: "Open this stair" on the stair card to check opens that stair, with the tool Rooms and stairs, the plan in view', async ({ page, request }) => {
  test.setTimeout(4 * 60_000);
  await page.setViewportSize({ width: 1366, height: 680 });
  const ov = await openCheck(page, request, 'e2e-rr-web-s2');
  const flag = ov.flags.find(x => x.kind === 'stair' && x.severity === 'check' && x.ref.stair)!;
  expect(flag, 'a stair flag to check').toBeTruthy();
  const card = page.locator(`[data-testid=flag][data-id="${flag.id}"]`);
  await expect(card.locator('p').first()).toHaveText('Stair');
  await page.evaluate(() => window.scrollTo(0, document.documentElement.scrollHeight));
  await card.getByTestId('flag-open-stair').click();
  await expect(page.getByTestId('stair-panel')).toHaveAttribute('data-id', flag.ref.stair!);
  await expect(page.getByTestId('check-tool')).toHaveValue('rooms');
  expect((await inView(page, 'check-canvas')).whole).toBe(true);
  // the stair is on the canvas (its point through the test hook)
  const st = (await page.evaluate(() => (window as any).__plan.stairs())) as { id: string; at: [number, number] }[];
  const at = st.find(x => x.id === flag.ref.stair)!.at;
  expect(await page.evaluate(q => (window as any).__plan.toPage(q), at)).not.toBeNull();
});
