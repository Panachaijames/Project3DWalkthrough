// Scaffold smoke (project `harness`): headless Edge opens the harness page, three.js draws into WebGL and the read-back
// pixel is the box's red, not blank. Run: WT_WEB_PORT=5700 WT_TMP=... npx playwright test -c tests/e2e/playwright.config.ts --project harness
import { expect, test } from '@playwright/test';

test('three.js from npm draws into a WebGL canvas in headless Edge', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', e => errors.push(String(e)));
  await page.goto('/scaffold/webgl.html');
  await page.waitForFunction(() => window.__smoke !== undefined);
  const smoke = await page.evaluate(() => window.__smoke!);
  expect(errors).toEqual([]);
  expect('error' in smoke ? smoke.error : null).toBeNull();
  if ('error' in smoke) return;
  test.info().annotations.push({ type: 'webgl', description: `three r${smoke.revision}, ${smoke.renderer}` });
  expect(smoke.revision).toBe('186');
  expect(smoke.clear).toEqual([0xee, 0xf0, 0xf2, 255]);
  const [r, g, b, a] = smoke.pixel;
  expect(a).toBe(255);
  expect(r).toBeGreaterThan(200);
  expect(g).toBeLessThan(40);
  expect(b).toBeLessThan(40);
  expect(smoke.bvhHit).toBeCloseTo(4, 5);
  await expect(page.locator('canvas')).toHaveCount(1);
});

test('the shared test context renders the bank v2 fixture with the real WebGL renderer', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', e => errors.push(String(e)));
  await page.goto('/scaffold/context.html');
  await page.waitForFunction(() => window.__kit !== undefined);
  const kit = await page.evaluate(() => window.__kit!);
  expect(errors).toEqual([]);
  expect('error' in kit ? kit.error : null).toBeNull();
  if ('error' in kit) return;
  expect(kit.floors).toEqual(['L1', 'L2']);
  expect(kit.colliders).toBeGreaterThan(10);
  expect(kit.hit).not.toBeNull();
  const [r, g, b] = kit.pixel;
  expect([r, g, b]).not.toEqual([0xee, 0xf0, 0xf2]);
  const left = await page.evaluate(() => {
    (window as unknown as { __ctx: { disposer: { dispose(): void } } }).__ctx.disposer.dispose();
    return { roots: document.querySelectorAll('[data-wt=root]').length, canvases: document.querySelectorAll('canvas').length };
  });
  expect(left).toEqual({ roots: 0, canvases: 0 });
});
