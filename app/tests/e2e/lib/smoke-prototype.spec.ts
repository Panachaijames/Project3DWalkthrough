// Scaffold smoke of the test kit (project `scaffold`), on the prototype target only:
//   E2E_TARGET=prototype npx playwright test -c tests/e2e/playwright.config.ts tests/e2e/lib/smoke-prototype.spec.ts
// Opens the prototype pages through lib/target.ts (file URLs, waitReady, the shim) under the Edge lock, and checks that
// the kit's pieces work there: the selector map, isOn, __walkthrough.THREE, the v1 openings / probes / FL, plates and
// fitted (house), and one page-side walk helper. The pages need cdn.jsdelivr.net (three.js 0.160 from their import map).
import { expect, test } from '@playwright/test';
import { pageApi } from './page';
import { fittedNames, isApp, isOn, openVersion, plates, sel, VERSIONS, type VersionKey } from './target';
import { doorWalks, installPageHelpers, judgeHouseWalk, walkThrough } from './walks';

test.skip(isApp, 'the scaffold smoke runs on the prototype target (E2E_TARGET=prototype)');

const KEYS: VersionKey[] = ['bank-v1', 'bank-v2', 'suite', 'house', 'hotel'];

for (const key of KEYS) {
  test(`${key}: the prototype page opens through the target lib`, async ({ page }) => {
    const ref = VERSIONS[key];
    const p = await pageApi(page);
    await openVersion(page, key);

    const facts = await page.evaluate(() => {
      const w = window as any;
      const h = w.__host;
      const T = w.__walkthrough.THREE;
      const v = new T.Vector3(1, 2, 3);
      return {
        three: v.length() > 3.7 && typeof T.Raycaster === 'function' && typeof T.Color === 'function',
        openings: h.openings.length,
        v1: h.openings.every((o: any) => typeof o.id === 'string' && typeof o.floor === 'string' && ['door', 'window', 'passage'].includes(o.kind)
          && [o.x, o.y, o.nx, o.ny, o.width].every(n => typeof n === 'number')),
        probes: Array.isArray(h.probes) ? h.probes.length : -1,
        fl: Object.keys(h.FL),
        floors: h.floors.map((f: any) => f.key),
        mode: w.__viewer.state.mode,
        stamp: document.querySelector('meta[name=model-data]')?.getAttribute('content') ?? null,
      };
    });
    expect(facts.three).toBe(true);
    expect(facts.openings).toBeGreaterThan(0);
    expect(facts.v1).toBe(true);
    expect(facts.probes).toBeGreaterThanOrEqual(0);
    expect(facts.fl).toEqual(ref.floors);
    expect(facts.floors).toEqual(ref.floors);
    expect(facts.mode).toBe('orbit');
    expect(facts.stamp).toBe(ref.stamp);

    await expect(page.locator(sel.panel)).toBeVisible();
    await expect(page.locator(sel.heading)).not.toHaveText('');
    if (ref.floors.length > 1) {
      expect(await isOn(page.locator(sel.floorButton('all')))).toBe(true);
      expect(await isOn(page.locator(sel.floorButton(ref.floors[1]!)))).toBe(false);
    }
    await expect(page.locator(sel.toggle('plates'))).toBeChecked();

    if (key === 'house') {
      const fitted = await fittedNames(page);
      expect(Object.keys(fitted).sort()).toEqual(['ground', 'upper']);
      const pl = await plates(page);
      expect(pl.ground?.length).toBe(3);
      expect(pl.upper?.length).toBe(1);
      // the house's own door rule (cad_test/test_house_openings.mjs): no door of the ground floor is blocked
      const doors = await page.evaluate(() => (window as any).__host.openings.filter((o: any) => o.floor === 'ground' && o.kind === 'door' && !o.glazed));
      const results = (await walkThrough(page, doors)).map(judgeHouseWalk);
      expect(results.length).toBeGreaterThan(0);
      expect(results.filter(r => r === 'blocked')).toEqual([]);
      test.info().annotations.push({ type: 'house doors', description: `${results.length} ground doors: ${results.filter(r => r === 'both ways').length} both ways` });
    }
    if (ref.hasFurniture) expect(await installPageHelpers(page)).toBe(true);

    const walks = await doorWalks(page);
    expect(walks.length).toBeGreaterThan(0);
    test.info().annotations.push({ type: 'doors', description: `${walks.filter(w => w.ok).length} of ${walks.length} walkable on ${facts.floors[0]}` });
    expect(p.logs.filter(l => l.startsWith('[exception]'))).toEqual([]);
  });
}
