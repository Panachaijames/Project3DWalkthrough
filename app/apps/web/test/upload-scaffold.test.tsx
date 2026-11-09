// The upload milestone's three routes answer with their screens (written by the scaffold U0 for its placeholders; U6
// replaced the placeholders, docs/upload/WORK_BREAKDOWN.md U6), and the plan module's decodePlan decodes the fixture plans
// (U7 keeps its signature and behaviour; its own tests are in test/plan/).
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { gunzipSync } from 'node:zlib';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { createMemoryRouter } from 'react-router';
import { RouterProvider } from 'react-router/dom';
import { afterEach, describe, expect, it, vi } from 'vitest';
import '@/api/client';
import { decodePlan, nearLayers, PlanCanvas, proposeAreas } from '@/plan';
import { createRoutes } from '@/router';
import type { PlanGeometry } from '@/upload/contracts';
import { render, waitFor, type Mounted } from './helpers';
import { createMockApi } from './mock-api/core';
import { mockFetch } from './mock-api/fetch';

const plan = (name: string) =>
  JSON.parse(gunzipSync(readFileSync(path.resolve(__dirname, '../../../fixtures/upload/plan', `${name}.plan.json.gz`))).toString('utf8')) as PlanGeometry;

const opened: Mounted[] = [];
afterEach(async () => {
  while (opened.length) await opened.pop()!.unmount();
  vi.unstubAllGlobals();
  document.body.replaceChildren();
});

describe('upload routes (static routes before :projectId, U-14.1)', () => {
  const mock = createMockApi();
  const src = mock.uploads.addSource('bank-sampeng', { name: 'I1201.dwg', bytes: Buffer.from('AC1032 bank') });
  const build = mock.uploads.createBuildNow('bank-sampeng', [src.sha1], { finish: true });
  const cases = [
    ['/projects/new', 'new-project-page', 'New project · Walkthrough'],
    ['/projects/bank-sampeng/builds/new', 'upload-page', 'Bangkok Bank, Sampeng Branch · upload · Walkthrough'],
    [`/projects/bank-sampeng/builds/${build.id}`, 'build-page', 'Bangkok Bank, Sampeng Branch · draft · Walkthrough'],
  ] as const;
  for (const [route, testId, title] of cases) {
    it(`${route} shows its screen`, async () => {
      vi.stubGlobal('fetch', mockFetch(mock));
      const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
      const router = createMemoryRouter(createRoutes(queryClient), { initialEntries: [route] });
      opened.push(await render(<QueryClientProvider client={queryClient}><RouterProvider router={router} /></QueryClientProvider>));
      await waitFor(() => document.querySelector(`[data-testid=${testId}]`));
      await waitFor(() => document.title === title);
      expect(router.state.location.pathname).toBe(route);
    });
  }
});

describe('decodePlan', () => {
  it('decodes the bank fixture plan', () => {
    const json = plan('bank1');
    const p = decodePlan(json);
    expect(p.count).toBe(json.items.key.length);
    expect(p.layers).toEqual(json.layers);
    expect(p.keyAt(0)).toBe(json.items.key[0]);
    expect(p.layerAt(5)).toBe(json.items.layer[5]);
    expect(p.typeAt(5)).toBe(json.items.type[5]);
    const [x0, y0, x1, y1] = p.extents;
    expect(x1 - x0).toBeGreaterThan(10);
    expect(y1 - y0).toBeGreaterThan(10);
    const withElement = json.items.eid.findIndex(e => e >= 0);
    expect(withElement).toBeGreaterThanOrEqual(0);
    expect(p.refOf(json.items.key[withElement]!)).toEqual({
      sig: json.items.sig[withElement], rsig: json.items.rsig[withElement],
      elementId: json.elementIds[json.items.eid[withElement]!], layer: json.layers[json.items.layer[withElement]!],
    });
    expect(p.refOf('no such key')).toBeNull();
    // the signatures U6 calls (U7 fills the bodies): an array of boxes, a map of counts
    expect(Array.isArray(proposeAreas(p, new Set([0])))).toBe(true);
    expect(nearLayers(p, new Set([0]), 1)).toBeInstanceOf(Map);
  });

  it('refuses parallel arrays of different lengths', () => {
    const json = plan('bank1');
    expect(() => decodePlan({ ...json, items: { ...json.items, sig: json.items.sig.slice(1) } })).toThrow(/items.sig/);
  });

  it('the canvas renders for a decoded plan', async () => {
    const p = decodePlan(plan('bank1'));
    const host = await render(<PlanCanvas plan={p} roleOf={() => 'other'} selected={new Set()} setAside={new Set()} tool="pan" />);
    opened.push(host);
    expect(host.host.firstElementChild).not.toBeNull();
  });
});
