// The routes and screens (DESIGN.md 15.1 - 15.5) in a memory router over the mock API (test/mock-api), with the fake
// viewer in place of @walkthrough/viewer: the list's states and cards, the redirects, Not found, the project page's app bar
// and viewer, version changes (the old viewer disposed first), saving heights, the error paths, and (step BX) the deleted
// furniture boxes on the version page.
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { act } from 'react';
import { createMemoryRouter } from 'react-router';
import { RouterProvider } from 'react-router/dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import '@/api/client';
import { getFurnitureHeightsQueryKey, listProjectsQueryKey } from '@/api/generated/@tanstack/react-query.gen';
import { createQueryClient } from '@/lib/queryClient';
import { formatDate } from '@/lib/format';
import { createRoutes } from '@/router';
import { fakeViewerLog, resetFakeViewer } from './fake-viewer';
import { all, click, render, settle, stubWebGL, text, waitFor } from './helpers';
import { createMockApi, type MockApi } from './mock-api/core';
import { mockFetch, type MockFetchOptions } from './mock-api/fetch';

vi.mock('@walkthrough/viewer', async () => vi.importActual('./fake-viewer'));

let restoreWebGL: () => void = () => undefined;
let webglFails = false;
beforeEach(() => {
  resetFakeViewer();
  webglFails = false;
  restoreWebGL = stubWebGL({ fail: () => webglFails });
  document.title = '';
});
afterEach(async () => {
  restoreWebGL();
  vi.unstubAllGlobals();
  document.body.replaceChildren();
});

const opened: { unmount(): Promise<void> }[] = [];
afterEach(async () => {
  while (opened.length) await opened.pop()!.unmount();
});

async function openApp(path: string, opts: { mock?: MockApi; fetch?: MockFetchOptions; strict?: boolean } = {}) {
  const mock = opts.mock ?? createMockApi();
  vi.stubGlobal('fetch', mockFetch(mock, opts.fetch));
  // retry off here (errors show at once); the app's own client retries once (checked below)
  const queryClient = new QueryClient({ defaultOptions: { queries: { staleTime: 30_000, retry: false } } });
  const router = createMemoryRouter(createRoutes(queryClient), { initialEntries: [path] });
  const v = await render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
    { strict: opts.strict ?? true },
  );
  opened.push(v);
  return { v, router, mock, queryClient, body: document.body };
}

const cards = () => all(document.body, '[data-testid=project-card]');
const live = () => window.__fakeViewer!.live();

describe('the app client', () => {
  it('createQueryClient: staleTime 30 s, one retry', () => {
    const q = createQueryClient().getDefaultOptions().queries;
    expect(q?.staleTime).toBe(30_000);
    expect(q?.retry).toBe(1);
  });
});

describe('/ and /projects', () => {
  it('/ goes to /projects', async () => {
    const app = await openApp('/');
    await waitFor(() => app.router.state.location.pathname === '/projects');
    await waitFor(() => cards().length === 4);
  });

  it('shows skeleton cards while loading, then one card per project, newest first, with their fields', async () => {
    let release!: () => void;
    const gate = new Promise<void>(r => { release = r; });
    const app = await openApp('/projects', { fetch: { intercept: async (m, p) => { if (p === '/api/projects') await gate; return undefined; } } });
    expect(all(app.body, '[data-testid=project-card-skeleton]').length).toBeGreaterThan(0);   // the list is held at the gate
    expect(cards().length).toBe(0);
    release();
    await waitFor(() => cards().length === 4);
    expect(document.title).toBe('Projects · Walkthrough');
    expect(all(app.body, '[data-testid=project-card-skeleton]').length).toBe(0);
    expect(cards().map(c => c.getAttribute('data-project-id'))).toEqual(['hotel-lobby', 'sukhumvit-house', 'presidential-suite', 'bank-sampeng']);
    const field = (id: string, f: string) => text(app.body.querySelector(`[data-project-id=${id}] [data-testid=card-${f}]`));
    expect(field('bank-sampeng', 'name')).toBe('Bangkok Bank, Sampeng Branch');
    expect(field('bank-sampeng', 'source')).toBe('CAD');
    expect(field('bank-sampeng', 'floors')).toBe('2 floors: Level 1, Level 2');
    expect(field('bank-sampeng', 'furniture')).toBe('185 furniture pieces');
    expect(field('bank-sampeng', 'openings')).toBe('49 openings');
    expect(field('bank-sampeng', 'stamp')).toBe('c3a9408304a2');
    expect(field('bank-sampeng', 'versions')).toBe('2 versions');
    expect(field('bank-sampeng', 'updated')).toBe(formatDate('2026-10-29T03:24:53Z'));
    expect(app.body.querySelector('[data-project-id=bank-sampeng] time[data-testid=card-updated]')?.getAttribute('datetime')).toBe('2026-10-29T03:24:53Z');
    expect(field('hotel-lobby', 'source')).toBe('Pictures');
    expect(field('hotel-lobby', 'floors')).toBe('2 floors: Floor 1, Floor 2');
    expect(field('presidential-suite', 'floors')).toBe('1 floor: Suite (FL-01)');
    expect(field('presidential-suite', 'versions')).toBe('1 version');
    // thumbnails from thumbnailUrl; the house has none: the placeholder with its short name
    const img = (id: string) => app.body.querySelector(`[data-project-id=${id}] img[data-testid=card-thumbnail]`);
    expect(img('bank-sampeng')?.getAttribute('src')).toBe('/api/projects/bank-sampeng/thumbnail');
    expect(img('hotel-lobby')?.getAttribute('src')).toBe('/api/projects/hotel-lobby/thumbnail');
    expect(img('sukhumvit-house')).toBeNull();
    expect(field('sukhumvit-house', 'placeholder-name')).toBe('Sukhumvit house');
    // each card links to its project
    expect(app.body.querySelector('[data-project-id=bank-sampeng] a[data-testid=card-link]')?.getAttribute('href')).toBe('/projects/bank-sampeng');
  });

  it('an error shows an Alert with the reason and Retry', async () => {
    let fail = true;
    const app = await openApp('/projects', {
      fetch: {
        intercept: (m, p) => (fail && p === '/api/projects'
          ? new Response(JSON.stringify({ error: { code: 'store_down', message: 'the store is not readable' } }), { status: 500, headers: { 'content-type': 'application/json' } })
          : undefined),
      },
    });
    const alert = await waitFor(() => app.body.querySelector('[data-testid=projects-error]'));
    expect(text(alert.querySelector('[data-testid=projects-error-reason]'))).toBe('the store is not readable');
    fail = false;
    await click(app.body.querySelector('[data-testid=projects-retry]'));
    await waitFor(() => cards().length === 4);
    expect(app.body.querySelector('[data-testid=projects-error]')).toBeNull();
  });

  it('a dead API: the reason says so', async () => {
    const app = await openApp('/projects', { fetch: { intercept: () => { throw new TypeError('Failed to fetch'); } } });
    const alert = await waitFor(() => app.body.querySelector('[data-testid=projects-error]'));
    expect(text(alert.querySelector('[data-testid=projects-error-reason]'))).toBe('the API did not answer (is it running?)');
  });

  it('a failed refresh keeps the cards it has and shows the reason above them', async () => {
    let fail = false;
    const app = await openApp('/projects', {
      fetch: {
        intercept: (m, p) => (fail && p === '/api/projects'
          ? new Response(JSON.stringify({ error: { code: 'store_down', message: 'the store went away' } }), { status: 500, headers: { 'content-type': 'application/json' } })
          : undefined),
      },
    });
    await waitFor(() => cards().length === 4);
    fail = true;
    await act(async () => { await app.queryClient.refetchQueries({ queryKey: listProjectsQueryKey() }); });
    const alert = await waitFor(() => app.body.querySelector('[data-testid=projects-error]'));
    expect(text(alert.querySelector('[data-testid=projects-error-reason]'))).toBe('the store went away');
    expect(cards().length).toBe(4);
    fail = false;
    await click(app.body.querySelector('[data-testid=projects-retry]'));
    await waitFor(() => !app.body.querySelector('[data-testid=projects-error]'));
    expect(cards().length).toBe(4);
  });

  it('no projects: No projects yet: make one with New project (changed on purpose, docs/upload/DESIGN.md U-14.1)', async () => {
    const app = await openApp('/projects', {
      fetch: { intercept: (m, p) => (p === '/api/projects' ? new Response('{"projects":[]}', { headers: { 'content-type': 'application/json' } }) : undefined) },
    });
    const empty = await waitFor(() => app.body.querySelector('[data-testid=projects-empty]'));
    expect(text(empty)).toBe('No projects yet: make one with New project');
    expect(app.body.querySelector('a[data-testid=new-project]')?.getAttribute('href')).toBe('/projects/new');
  });

  it('drawing text in names stays text', async () => {
    const mock = createMockApi();
    const evil = '<img src=x onerror="window.__pwned=1">';
    const app = await openApp('/projects', {
      mock,
      fetch: {
        intercept: (m, p) => {
          if (p !== '/api/projects') return undefined;
          const list = { projects: mock.list().map(x => ({ ...x, name: evil, shortName: evil, thumbnailUrl: null })) };
          return new Response(JSON.stringify(list), { headers: { 'content-type': 'application/json' } });
        },
      },
    });
    await waitFor(() => cards().length === 4);
    expect(text(app.body.querySelector('[data-testid=card-name]'))).toBe(evil);
    expect(app.body.querySelector('[data-testid=project-grid] img')).toBeNull();
    expect((window as { __pwned?: number }).__pwned).toBeUndefined();
  });
});

describe('/projects/:projectId and Not found', () => {
  it('goes to the latest version, keeping the address options, replacing its own history entry', async () => {
    const app = await openApp('/projects/bank-sampeng?build=play');
    await waitFor(() => app.router.state.location.pathname === '/projects/bank-sampeng/v/2');
    expect(app.router.state.location.search).toBe('?build=play');
    expect(app.router.state.historyAction).toBe('REPLACE');
    await waitFor(() => fakeViewerLog.some(r => r.event === 'create'));
    expect(fakeViewerLog.at(-1)?.options?.build).toBe('play');
  });

  it('an unknown project, an unknown version, a bad version number, a bad id, an unknown page: Not found', async () => {
    for (const [path, message] of [
      ['/projects/no-such-project', 'There is no project no-such-project.'],
      ['/projects/no-such-project/v/1', 'There is no project no-such-project.'],
      ['/projects/bank-sampeng/v/9', 'Project bank-sampeng has no version 9.'],
      ['/projects/bank-sampeng/v/0', 'There is no version "0".'],
      ['/projects/bank-sampeng/v/2x', 'There is no version "2x".'],
      ['/projects/Bad_Id', 'There is no project called "Bad_Id".'],
      ['/nowhere/at/all', 'There is no page at this address.'],
    ] as const) {
      const app = await openApp(path);
      const nf = await waitFor(() => app.body.querySelector('[data-testid=not-found]'));
      expect(text(nf.querySelector('[data-testid=not-found-message]')), path).toBe(message);
      expect(document.title).toBe('Not found · Walkthrough');
      await opened.pop()!.unmount();
    }
  });

  it('a server error while opening a project: an Alert with Retry that loads it', async () => {
    let fail = true;
    const app = await openApp('/projects/hotel-lobby/v/1', {
      fetch: { intercept: (m, p) => (fail && p === '/api/projects/hotel-lobby/versions/1' ? new Response('boom', { status: 500 }) : undefined) },
    });
    const alert = await waitFor(() => app.body.querySelector('[data-testid=route-error]'));
    expect(text(alert.querySelector('[data-testid=route-error-reason]'))).toBe('boom');
    fail = false;
    await click(app.body.querySelector('[data-testid=route-error-retry]'));
    await waitFor(() => app.body.querySelector('[data-testid=project-page]'));
  });
});

describe('the project page', () => {
  it('the app bar, the title and one viewer made with the version (StrictMode: made twice, one left)', async () => {
    const app = await openApp('/projects/bank-sampeng/v/2');
    await waitFor(() => app.body.querySelector('[data-testid=project-page]'));
    await waitFor(() => fakeViewerLog.filter(r => r.event === 'create').length === 2);
    expect(document.title).toBe('Bangkok Bank, Sampeng Branch · v2 · Walkthrough');
    expect(text(app.body.querySelector('[data-testid=app-bar-title]'))).toBe('Bangkok Bank, Sampeng Branch');
    expect(app.body.querySelector('[data-testid=back-to-projects]')?.getAttribute('href')).toBe('/projects');
    expect(text(app.body.querySelector('[data-testid=version-picker]'))).toContain(`v2 · ${formatDate('2026-10-29T03:24:53Z')} · c3a9408304a2`);
    expect(text(app.body.querySelector('[data-testid=downloads-menu]'))).toBe('Downloads');
    expect(text(app.body.querySelector('[data-testid=heights-status-text]'))).toBe('Furniture saved');
    expect(fakeViewerLog.map(r => r.event)).toEqual(['create', 'dispose', 'create']);
    expect(live()).toBe(1);
    const rec = fakeViewerLog.at(-1)!;
    expect(rec).toMatchObject({ projectId: 'bank-sampeng', version: 2, stamp: 'c3a9408304a2', heights: {}, pictures: {}, hasStages: true });
    expect(rec.options).toMatchObject({ build: 'skip', furnitureHeights: 'host', address: {} });
    // the viewer's root inside the host div, below the 48 px bar
    const host = app.body.querySelector('[data-testid=viewer-area] [data-testid=viewer-host]');
    expect(host?.querySelectorAll('[data-wt=root]').length).toBe(1);
  });

  it('the saved heights are the starting heights; v1 (no furniture) has no heights status', async () => {
    const mock = createMockApi();
    mock.setSaved('bank-sampeng', 2, { table: 600 });
    const app = await openApp('/projects/bank-sampeng/v/2', { mock });
    await waitFor(() => fakeViewerLog.some(r => r.event === 'create'));
    expect(fakeViewerLog.at(-1)?.heights).toEqual({ table: 600 });
    await act(async () => { await app.router.navigate('/projects/bank-sampeng/v/1'); });
    await waitFor(() => fakeViewerLog.at(-1)?.version === 1);
    expect(app.body.querySelector('[data-testid=heights-status]')).toBeNull();
    expect(document.title).toBe('Bangkok Bank, Sampeng Branch · v1 · Walkthrough');
  });

  it('a version change disposes the old viewer before making the new one, on the same div', async () => {
    const app = await openApp('/projects/bank-sampeng/v/2');
    await waitFor(() => fakeViewerLog.filter(r => r.event === 'create').length === 2);
    const host = app.body.querySelector('[data-testid=viewer-host]');
    fakeViewerLog.length = 0;
    await act(async () => { await app.router.navigate('/projects/bank-sampeng/v/1'); });
    await waitFor(() => fakeViewerLog.length === 2);
    expect(fakeViewerLog.map(r => [r.event, r.version])).toEqual([['dispose', 2], ['create', 1]]);
    expect(app.body.querySelector('[data-testid=viewer-host]')).toBe(host);
    expect(all(app.body, '[data-wt=root]').length).toBe(1);
    expect(live()).toBe(1);
    // and back: a fresh viewer for v2 again
    await act(async () => { await app.router.navigate('/projects/bank-sampeng/v/2'); });
    await waitFor(() => fakeViewerLog.length === 4);
    expect(fakeViewerLog.map(r => [r.event, r.version])).toEqual([['dispose', 2], ['create', 1], ['dispose', 1], ['create', 2]]);
    // leaving the page disposes it
    await act(async () => { await app.router.navigate('/projects'); });
    await waitFor(() => cards().length === 4);
    expect(live()).toBe(0);
    expect(all(app.body, '[data-wt=root]').length).toBe(0);
  });

  it('the hotel: its plan pictures go to the viewer as asset URLs, no stages are read', async () => {
    const app = await openApp('/projects/hotel-lobby/v/1');
    await waitFor(() => fakeViewerLog.some(r => r.event === 'create'));
    expect(fakeViewerLog.at(-1)).toMatchObject({
      pictures: {
        F1: '/api/projects/hotel-lobby/versions/1/assets/floor1_plan.png',
        F2: '/api/projects/hotel-lobby/versions/1/assets/floor2_plan.png',
      },
      hasStages: false,
      stamp: '6ab030750886',
    });
    expect(app.mock.requests.some(r => r.path.endsWith('/stages'))).toBe(false);
  });

  it('heights typed in the viewer are saved: Saving…, PUT with the map, Furniture saved', async () => {
    let release!: () => void;
    const gate = new Promise<void>(r => { release = r; });
    const app = await openApp('/projects/bank-sampeng/v/2', { fetch: { intercept: async m => { if (m === 'PUT') await gate; return undefined; } } });
    const input = await waitFor(() => app.body.querySelector<HTMLInputElement>('[data-wt=furniture-row][data-kind=table] [data-wt=kind-height]'));
    expect(input.value).toBe('750');
    await act(async () => {
      input.focus();
      input.value = '600';
      input.dispatchEvent(new Event('input', { bubbles: true }));
    });
    expect(text(app.body.querySelector('[data-testid=heights-status-text]'))).toBe('Saving…');   // debouncing, then held at the gate
    release();
    await waitFor(() => text(app.body.querySelector('[data-testid=heights-status-text]')) === 'Furniture saved');
    const puts = app.mock.requests.filter(r => r.method === 'PUT');
    expect(puts.map(r => [r.path, JSON.parse(r.body ?? '')])).toEqual([['/api/projects/bank-sampeng/versions/2/furniture-heights', { heights: { table: 600 } }]]);
    expect(app.mock.saved('bank-sampeng', 2).heights).toEqual({ table: 600 });
    // the cached version detail has the saved heights: no new viewer was made for it
    expect(fakeViewerLog.filter(r => r.event === 'create').length).toBe(2);
  });

  it('a failed save: Not saved: <reason>, and Retry sends the newest map', async () => {
    let fail = true;
    const app = await openApp('/projects/bank-sampeng/v/2', {
      fetch: {
        intercept: (m) => (fail && m === 'PUT'
          ? new Response(JSON.stringify({ error: { code: 'unavailable', message: 'the store is read-only' } }), { status: 503, headers: { 'content-type': 'application/json' } })
          : undefined),
      },
    });
    await waitFor(() => fakeViewerLog.some(r => r.event === 'create'));
    const viewers = window.__fakeViewer!.viewers;
    await act(async () => { viewers.at(-1)!.emit('heightschange', { heights: { seat: 300 }, source: 'typed' }); });
    await waitFor(() => app.body.querySelector('[data-testid=heights-status]')?.getAttribute('data-state') === 'error');
    expect(text(app.body.querySelector('[data-testid=heights-status-text]'))).toBe('Not saved: the store is read-only');
    fail = false;
    await click(app.body.querySelector('[data-testid=heights-retry]'));
    await waitFor(() => text(app.body.querySelector('[data-testid=heights-status-text]')) === 'Furniture saved');
    expect(app.mock.saved('bank-sampeng', 2).heights).toEqual({ seat: 300 });
  });

  it('opening the Downloads menu sends a waiting save at once; the CSV and the offline file wait for it', async () => {
    let release!: () => void;
    const gate = new Promise<void>(r => { release = r; });
    let putAt = 0;
    const app = await openApp('/projects/bank-sampeng/v/2', {
      fetch: {
        onRequest: m => { if (m === 'PUT' && !putAt) putAt = performance.now(); },
        intercept: async m => { if (m === 'PUT') await gate; return undefined; },
      },
    });
    await waitFor(() => fakeViewerLog.some(r => r.event === 'create'));
    const item = (key: string) => document.body.querySelector(`[data-testid=downloads-list] [data-download=${key}]`);
    const t0 = performance.now();
    await act(async () => { window.__fakeViewer!.viewers.at(-1)!.emit('heightschange', { heights: { table: 600 }, source: 'typed' }); });
    expect(text(app.body.querySelector('[data-testid=heights-status-text]'))).toBe('Saving…');
    const trigger = app.body.querySelector('[data-testid=downloads-menu]')!;
    await act(async () => { trigger.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true, cancelable: true })); });
    const openedAt = performance.now();
    await waitFor(() => item('offlineHtml'));
    await waitFor(() => putAt > 0);
    // sent by the menu, not by the 600 ms debounce (checked when this machine opened the menu well inside the debounce)
    if (openedAt - t0 < 300) expect(putAt - t0).toBeLessThan(550);
    for (const key of ['furnitureCsv', 'offlineHtml']) {
      expect(item(key)?.hasAttribute('data-waiting'), key).toBe(true);
      expect(item(key)?.getAttribute('href'), key).toBeNull();
    }
    expect(item('maxScript')?.getAttribute('href')).toBe('/api/projects/bank-sampeng/versions/2/downloads/max-script');
    release();
    await waitFor(() => text(app.body.querySelector('[data-testid=heights-status-text]')) === 'Furniture saved');
    await waitFor(() => item('furnitureCsv')?.getAttribute('href') === '/api/projects/bank-sampeng/versions/2/downloads/furniture-csv');
    expect(item('offlineHtml')?.getAttribute('href')).toBe('/api/projects/bank-sampeng/versions/2/downloads/offline-html');
    expect(app.mock.saved('bank-sampeng', 2).heights).toEqual({ table: 600 });
    expect(app.mock.requests.filter(r => r.method === 'PUT').length).toBe(1);
  });

  it('a new address query re-creates the viewer, starting from the heights saved since the page opened', async () => {
    const app = await openApp('/projects/bank-sampeng/v/2');
    await waitFor(() => fakeViewerLog.filter(r => r.event === 'create').length === 2);
    await act(async () => { window.__fakeViewer!.viewers.at(-1)!.emit('heightschange', { heights: { table: 600 }, source: 'typed' }); });
    await waitFor(() => app.mock.saved('bank-sampeng', 2).revision === 1
      && text(app.body.querySelector('[data-testid=heights-status-text]')) === 'Furniture saved');
    fakeViewerLog.length = 0;
    await act(async () => { await app.router.navigate('/projects/bank-sampeng/v/2?mode=walk'); });
    await waitFor(() => fakeViewerLog.some(r => r.event === 'create'));
    expect(fakeViewerLog.map(r => r.event)).toEqual(['dispose', 'create']);
    expect(fakeViewerLog.at(-1)).toMatchObject({ heights: { table: 600 }, options: { address: { build: 'skip', mode: 'walk' }, build: 'skip' } });
    expect(live()).toBe(1);
  });

  it('a pending save is sent when the user leaves the page', async () => {
    const app = await openApp('/projects/bank-sampeng/v/2');
    await waitFor(() => fakeViewerLog.some(r => r.event === 'create'));
    await act(async () => { window.__fakeViewer!.viewers.at(-1)!.emit('heightschange', { heights: { cabinet: 1000 }, source: 'typed' }); });
    await act(async () => { await app.router.navigate('/projects'); });
    await waitFor(() => app.mock.requests.some(r => r.method === 'PUT'));
    await settle(20);
    expect(app.mock.saved('bank-sampeng', 2).heights).toEqual({ cabinet: 1000 });
  });

  it('a model that does not parse: its issues instead of a viewer', async () => {
    const app = await openApp('/projects/bank-sampeng/v/1', {
      fetch: { intercept: (m, p) => (p.endsWith('/v/1') || !p.endsWith('/versions/1/model') ? undefined : new Response('"not a model"', { headers: { 'content-type': 'application/json' } })) },
    });
    const err = await waitFor(() => app.body.querySelector('[data-testid=model-error]'));
    expect(text(err)).toContain("This version's model could not be read");
    expect(text(err.querySelector('[data-testid=model-error-issues]'))).toBe('/: must be an object');
    expect(app.body.querySelector('[data-testid=viewer-host]')).toBeNull();
    expect(fakeViewerLog).toEqual([]);
  });

  it('a viewer that cannot start: the reason and Try again', async () => {
    webglFails = true;
    const app = await openApp('/projects/bank-sampeng/v/2');
    const err = await waitFor(() => app.body.querySelector('[data-testid=viewer-error]'));
    expect(text(err.querySelector('[data-testid=viewer-error-reason]'))).toContain('WebGL is not available');
    expect(fakeViewerLog.map(r => r.event)).toEqual(['fail', 'fail']);   // StrictMode: both mounts failed
    expect(all(app.body, '[data-wt=root]').length).toBe(0);              // nothing left behind
    webglFails = false;
    await click(app.body.querySelector('[data-testid=viewer-retry]'));
    await waitFor(() => app.body.querySelector('[data-wt=root]'));
    expect(app.body.querySelector('[data-testid=viewer-error]')).toBeNull();
    expect(live()).toBe(1);
  });
});

// ------------------------------------------------------------------------------------------------- fix step (3-4 Nov review)
describe('fix step: the page keeps what it has, says what it cannot do', () => {
  const NONE = new Response('', { status: 502 });
  const down502 = () => NONE.clone();

  it('a version already seen stays on screen when only its refresh fails because the API does not answer (proxy 502)', async () => {
    let down = false;
    const app = await openApp('/projects/bank-sampeng/v/2', { fetch: { intercept: (_m, p) => (down && p.startsWith('/api/') ? down502() : undefined) } });
    await waitFor(() => fakeViewerLog.filter(r => r.event === 'create').length === 2);
    await act(async () => { await app.router.navigate('/projects/bank-sampeng/v/1'); });
    await waitFor(() => fakeViewerLog.at(-1)?.version === 1 && fakeViewerLog.at(-1)?.event === 'create');
    down = true;
    await act(async () => { await app.queryClient.invalidateQueries(); });   // everything stale: a refresh is due
    await act(async () => { await app.router.navigate('/projects/bank-sampeng/v/2'); });
    await waitFor(() => fakeViewerLog.at(-1)?.version === 2 && fakeViewerLog.at(-1)?.event === 'create');
    expect(app.router.state.location.pathname).toBe('/projects/bank-sampeng/v/2');
    expect(app.body.querySelector('[data-testid=project-page]')?.getAttribute('data-version')).toBe('2');
    expect(live()).toBe(1);
    // a version never loaded has nothing to show: that one is an error page, with the client's own words
    await act(async () => { await app.router.navigate('/projects/presidential-suite/v/1'); });
    await waitFor(() => app.body.querySelector('[data-testid=project-page]') === null);
    expect(text(app.body)).toContain('the API did not answer (is it running?)');
    expect(text(app.body)).not.toContain('Bad Gateway');
  });

  it('a project with no version yet: its card leads to its Upload screen, then to its newest draft; its page lists the drafts (U-14.1)', async () => {
    const mock = createMockApi();
    const made = mock.handle({ method: 'POST', path: '/api/projects', body: JSON.stringify({ name: 'New upload', id: 'new-upload' }) });
    expect(made.status).toBe(201);
    const app = await openApp('/projects', { mock });
    await waitFor(() => cards().length === 5);
    const card = () => app.body.querySelector('[data-testid=project-card][data-project-id=new-upload]')!;
    expect(card().hasAttribute('data-no-versions')).toBe(true);
    expect(text(card())).toContain('No versions yet');
    await waitFor(() => card().querySelector('a[data-testid=card-link]')?.getAttribute('href') === '/projects/new-upload/builds/new');
    // a draft: the card leads to it
    const src = mock.uploads.addSource('new-upload', { name: 'plan.dwg', bytes: Buffer.from('AC1032 a drawing') });
    const b = mock.uploads.createBuildNow('new-upload', [src.sha1], { finish: true });
    await act(async () => { await app.queryClient.invalidateQueries(); });
    await waitFor(() => card().querySelector('a[data-testid=card-link]')?.getAttribute('href') === `/projects/new-upload/builds/${b.id}`);
    expect(card().querySelector('a[data-testid=card-link]')?.hasAttribute('data-draft')).toBe(true);
    // its address: the drafts with Continue, and Upload drawings (not on to /v/0 and Not found)
    await act(async () => { await app.router.navigate('/projects/new-upload'); });
    await waitFor(() => app.body.querySelector('[data-testid=no-versions]'));
    expect(app.router.state.location.pathname).toBe('/projects/new-upload');
    expect(text(app.body.querySelector('[data-testid=no-versions]'))).toContain('No versions yet');
    const row = await waitFor(() => app.body.querySelector(`[data-testid=draft-row][data-build-id="${b.id}"]`));
    expect(text(row.querySelector('[data-testid=draft-files]'))).toBe('plan.dwg');
    expect(row.querySelector('a[data-testid=draft-continue]')?.getAttribute('href')).toBe(`/projects/new-upload/builds/${b.id}`);
    expect(app.body.querySelector('a[data-testid=upload-drawings]')?.getAttribute('href')).toBe('/projects/new-upload/builds/new');
    // Delete (confirmed): the draft goes
    vi.stubGlobal('confirm', () => true);
    await click(row.querySelector('[data-testid=draft-delete]'));
    await waitFor(() => app.body.querySelector('[data-testid=no-drafts]'));
    expect(mock.uploads.builds('new-upload')).toEqual([]);
  });

  it('while a save has failed the browser asks before the tab is closed or reloaded; once saved it does not', async () => {
    let fail = true;
    const app = await openApp('/projects/bank-sampeng/v/2', {
      fetch: { intercept: m => (fail && m === 'PUT' ? new Response(JSON.stringify({ error: { code: 'store_error', message: 'busy (test)' } }), { status: 500, headers: { 'content-type': 'application/json' } }) : undefined) },
    });
    await waitFor(() => fakeViewerLog.some(r => r.event === 'create'));
    const leave = () => { const e = new Event('beforeunload', { cancelable: true }); window.dispatchEvent(e); return e.defaultPrevented; };
    expect(leave()).toBe(false);
    await act(async () => { window.__fakeViewer!.viewers.at(-1)!.emit('heightschange', { heights: { seat: 300 }, source: 'typed' }); });
    await waitFor(() => app.body.querySelector('[data-testid=heights-status]')?.getAttribute('data-state') === 'error');
    expect(leave()).toBe(true);
    fail = false;
    await click(app.body.querySelector('[data-testid=heights-retry]'));
    await waitFor(() => text(app.body.querySelector('[data-testid=heights-status-text]')) === 'Furniture saved');
    expect(leave()).toBe(false);
    expect(app.mock.saved('bank-sampeng', 2).heights).toEqual({ seat: 300 });
  });
});

// ------------------------------------------------------------------------------------------- step BX: the deleted boxes
// docs/boxes/DESIGN.md 6.2: the version page lets the viewer edit the boxes (options.editBoxes) and starts it from the saved
// (or unsent) deleted boxes; its boxeschange goes to the heights saver (one PUT, Furniture saved); deleted boxes taken over
// from elsewhere reach the viewer through setPieceEdits (no event back, nothing sent); the app bar counts the deleted boxes
// beside the status; the 3ds Max script waits while deleted boxes are not saved; a version whose previous version's deleted
// boxes did not all carry over says so in one line under the app bar (VersionDetail.carriedEdits).
describe('step BX: the deleted furniture boxes on the version page', () => {
  const R = { removed: true } as const;
  /** The bank v2's table L1-table-005 and the computer standing on it (the closure: deleting the table deletes both). */
  const TABLE = { 'L1-computer-001': R, 'L1-table-005': R };
  const statusText = () => text(document.body.querySelector('[data-testid=heights-status-text]'));
  const count = () => document.body.querySelector('[data-testid=boxes-deleted]');
  const puts = (mock: MockApi) => mock.requests.filter(r => r.method === 'PUT').map(r => JSON.parse(r.body ?? '') as unknown);
  const viewer = () => window.__fakeViewer!.viewers.at(-1)!;
  beforeEach(() => { localStorage.clear(); });                        // no unsaved entry of another test is the start
  afterEach(() => { localStorage.clear(); });

  it('a box deleted in the viewer goes to the heights saver: one PUT {heights, pieceEdits}, Furniture saved, the count in the app bar', async () => {
    const app = await openApp('/projects/bank-sampeng/v/2');
    await waitFor(() => fakeViewerLog.filter(r => r.event === 'create').length === 2);
    const rec = fakeViewerLog.at(-1)!;
    expect(rec.options?.editBoxes).toBe(true);                        // only the version page lets the viewer edit the boxes
    expect(rec.pieceEdits).toBeNull();                                // nothing deleted: the project has no pieceEdits key
    expect(count()).toBeNull();
    expect(app.body.querySelector('[data-testid=carried-edits-note]')).toBeNull();
    await act(async () => { viewer().furniture!.removePiece('L1-table-005'); });
    expect(text(count())).toBe('· 2 boxes deleted');
    expect(statusText()).toBe('Saving…');
    await waitFor(() => statusText() === 'Furniture saved');
    expect(puts(app.mock)).toEqual([{ heights: {}, pieceEdits: TABLE }]);
    expect(app.mock.saved('bank-sampeng', 2).pieceEdits).toEqual(TABLE);
    // a height typed next goes as {heights}: the saved deletions stay as they are
    await act(async () => { viewer().emit('heightschange', { heights: { seat: 300 }, source: 'typed' }); });
    await waitFor(() => puts(app.mock).length === 2 && statusText() === 'Furniture saved');
    expect(puts(app.mock)[1]).toEqual({ heights: { seat: 300 } });
    expect(app.mock.saved('bank-sampeng', 2)).toMatchObject({ heights: { seat: 300 }, pieceEdits: TABLE });
    // the mock runs' control deletes the first box not deleted yet (an ATM, nothing on it); the tab's heights go with it
    await click(app.body.querySelector('[data-wt=fake-remove-box]'));
    expect(text(count())).toBe('· 3 boxes deleted');
    await waitFor(() => puts(app.mock).length === 3 && statusText() === 'Furniture saved');
    expect(puts(app.mock)[2]).toEqual({ heights: { seat: 300 }, pieceEdits: { 'L1-atm-001': R, ...TABLE } });
    expect(fakeViewerLog.filter(r => r.event === 'create').length).toBe(2);   // a save never re-creates the viewer
  });

  it('the saved deleted boxes are where the viewer starts, counted at once; Restore all saves {} and the count goes', async () => {
    const mock = createMockApi();
    mock.setSaved('bank-sampeng', 2, {}, { 'L1-table-005': R });      // closed by the mock, as the API does
    const app = await openApp('/projects/bank-sampeng/v/2', { mock });
    await waitFor(() => fakeViewerLog.filter(r => r.event === 'create').length === 2);
    expect(fakeViewerLog.at(-1)!.pieceEdits).toEqual(TABLE);
    await waitFor(() => text(count()) === '· 2 boxes deleted');
    expect(count()!.getAttribute('title')).toBe("2 furniture boxes are deleted in this version: the furniture legend's Restore… brings them back");
    expect(viewer().getPieceEdits()).toEqual(TABLE);
    await act(async () => { viewer().furniture!.restoreAll(); });
    expect(count()).toBeNull();
    await waitFor(() => puts(mock).length === 1 && statusText() === 'Furniture saved');
    expect(puts(mock)).toEqual([{ heights: {}, pieceEdits: {} }]);   // {} = every box back (a change of this tab: sent)
    expect(mock.saved('bank-sampeng', 2).pieceEdits).toEqual({});
    await act(async () => { viewer().furniture!.removePiece('L1-table-005'); });
    expect(text(count())).toBe('· 2 boxes deleted');
    // another project's page never shows the bank's count
    await act(async () => { await app.router.navigate('/projects/hotel-lobby/v/1'); });
    await waitFor(() => fakeViewerLog.at(-1)?.projectId === 'hotel-lobby' && fakeViewerLog.at(-1)?.event === 'create');
    expect(app.body.querySelector('[data-testid=heights-status]')).not.toBeNull();
    expect(count()).toBeNull();
  });

  it('deleted boxes saved elsewhere are taken over while the tab is idle: shown with setPieceEdits and counted, nothing sent back', async () => {
    const app = await openApp('/projects/bank-sampeng/v/2');
    await waitFor(() => fakeViewerLog.filter(r => r.event === 'create').length === 2);
    await waitFor(() => app.mock.requests.some(r => r.method === 'GET' && r.path.endsWith('/versions/2/furniture-heights')));
    app.mock.setSaved('bank-sampeng', 2, {}, { 'L1-table-005': R }); // another tab deleted the table
    await act(async () => {
      await app.queryClient.invalidateQueries({ queryKey: getFurnitureHeightsQueryKey({ path: { projectId: 'bank-sampeng', version: 2 } }) });
    });
    await waitFor(() => Object.keys(viewer().getPieceEdits()).length === 2);
    expect(viewer().getPieceEdits()).toEqual(TABLE);
    await waitFor(() => text(count()) === '· 2 boxes deleted');
    await settle(700);                                                // past the debounce: setPieceEdits sends no boxeschange
    expect(puts(app.mock)).toEqual([]);
    expect(statusText()).toBe('Furniture saved');
  });

  it('a viewer re-created on the version after a takeover starts from what the saver has, so its next delete keeps the other tab\'s', async () => {
    // fix of 17 Nov 2026: the address changes within the 30 s cache, so the loader hands back the detail read before the
    // takeover and the new viewer starts from no deleted boxes; with nothing unsaved the page brings it to the saver's map
    const app = await openApp('/projects/bank-sampeng/v/2');
    await waitFor(() => fakeViewerLog.filter(r => r.event === 'create').length === 2);
    await waitFor(() => app.mock.requests.some(r => r.method === 'GET' && r.path.endsWith('/versions/2/furniture-heights')));
    app.mock.setSaved('bank-sampeng', 2, { seat: 300 }, { 'L1-table-005': R }); // another tab: a height and the table
    await act(async () => {
      await app.queryClient.invalidateQueries({ queryKey: getFurnitureHeightsQueryKey({ path: { projectId: 'bank-sampeng', version: 2 } }) });
    });
    await waitFor(() => Object.keys(viewer().getPieceEdits()).length === 2);
    await act(async () => { await app.router.navigate('/projects/bank-sampeng/v/2?floor=L1'); });
    await waitFor(() => fakeViewerLog.filter(r => r.event === 'create').length === 3);
    expect(fakeViewerLog.at(-1)!.pieceEdits).toBeNull();               // made from the detail as it was read at first
    expect(viewer().getPieceEdits()).toEqual(TABLE);                   // ... then brought to the saver's
    expect(viewer().getHeights()).toEqual({ seat: 300 });
    await waitFor(() => text(count()) === '· 2 boxes deleted');
    await act(async () => { viewer().furniture!.removePiece('L1-atm-001'); });
    await waitFor(() => puts(app.mock).length === 1 && statusText() === 'Furniture saved');
    expect(puts(app.mock)).toEqual([{ heights: { seat: 300 }, pieceEdits: { 'L1-atm-001': R, ...TABLE } }]);
    expect(app.mock.saved('bank-sampeng', 2).pieceEdits).toEqual({ 'L1-atm-001': R, ...TABLE });
  });

  it('while a delete is not saved the 3ds Max script waits too, with its own reason; saved, it is a link again', async () => {
    let refuse = true, putsMade = 0;
    const app = await openApp('/projects/bank-sampeng/v/2', {
      fetch: {
        onRequest: m => { if (m === 'PUT') putsMade++; },
        intercept: m => (refuse && m === 'PUT'
          ? new Response(JSON.stringify({ error: { code: 'store_error', message: 'busy (test)' } }), { status: 500, headers: { 'content-type': 'application/json' } })
          : undefined),
      },
    });
    const failedNow = () => app.body.querySelector('[data-testid=heights-status]')?.getAttribute('data-state') === 'error';
    await waitFor(() => fakeViewerLog.filter(r => r.event === 'create').length === 2);
    await click(app.body.querySelector('[data-wt=fake-remove-box]'));
    await waitFor(() => putsMade === 1 && failedNow());
    expect(statusText()).toBe('Not saved: busy (test)');
    const item = (key: string) => document.body.querySelector(`[data-testid=downloads-list] [data-download=${key}]`);
    const trigger = app.body.querySelector('[data-testid=downloads-menu]')!;
    await act(async () => { trigger.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true, cancelable: true })); });
    // opening the menu sends the failed save again (refused again): then the Max script says why it waits
    await waitFor(() => putsMade >= 2 && failedNow()
      && item('maxScript')?.getAttribute('title') === 'The deleted boxes on screen are not saved (busy (test)): the script would still build them');
    expect(item('maxScript')?.getAttribute('href')).toBeNull();
    expect(item('maxScript')?.hasAttribute('data-waiting')).toBe(true);
    expect(item('furnitureCsv')?.getAttribute('title')).toBe('The furniture changes on screen are not saved (busy (test)): the file would not carry them');
    refuse = false;
    await click(app.body.querySelector('[data-testid=heights-retry]'));
    await waitFor(() => item('maxScript')?.getAttribute('href') === '/api/projects/bank-sampeng/versions/2/downloads/max-script');
    expect(app.mock.saved('bank-sampeng', 2).pieceEdits).toEqual({ 'L1-atm-001': R });
  });

  it("a version whose previous version's deleted boxes did not all carry over says so under the app bar, until closed", async () => {
    const mock = createMockApi();
    const detail = {
      ...mock.version('bank-sampeng', 2)!,
      carriedEdits: {
        from: 1, notCarried: 2, boxes: [
          { kind: 'Chair / stool', family: 'Fritz-Hansen_SH200', floor: 'Level 2', reason: 'not found in the new drawing' },
          { kind: 'Table / desk', family: '<b>Desk</b>', floor: 'Level 1', reason: 'its floor changed', newId: 'L1-table-009' },
        ],
      },
    };
    const app = await openApp('/projects/bank-sampeng/v/2', {
      mock,
      fetch: {
        intercept: (m, p) => (m === 'GET' && p === '/api/projects/bank-sampeng/versions/2'
          ? new Response(JSON.stringify(detail), { status: 200, headers: { 'content-type': 'application/json' } })
          : undefined),
      },
    });
    const note = await waitFor(() => app.body.querySelector('[data-testid=carried-edits-note]'));
    expect(note.getAttribute('role')).toBe('note');
    // which boxes and why (fix of 17 Nov 2026): the head, then one line each
    expect([...note.querySelectorAll('[data-testid=carried-edits-line]')].map(l => text(l))).toEqual([
      '2 deleted boxes of v1 are back:',
      'Chair / stool (Fritz-Hansen_SH200) on Level 2: not found in the new drawing',
      'Table / desk (<b>Desk</b>) on Level 1: its floor changed',
    ]);
    expect(note.querySelector('b')).toBeNull();                        // drawing text stays text
    const area = () => app.body.querySelector<HTMLElement>('[data-testid=viewer-area]')!;
    expect((note as HTMLElement).style.height).toBe('80px');           // 3 lines of 24 px and 8 px
    expect(area().style.top).toBe('128px');                            // the viewer starts below the note
    expect(area().classList.contains('top-12')).toBe(false);
    await waitFor(() => fakeViewerLog.filter(r => r.event === 'create').length === 2);
    await click(note.querySelector('[data-testid=carried-edits-close]'));
    expect(app.body.querySelector('[data-testid=carried-edits-note]')).toBeNull();
    expect(area().classList.contains('top-12')).toBe(true);
    expect(area().style.top).toBe('');
    expect(fakeViewerLog.filter(r => r.event === 'create').length).toBe(2);   // closing the note re-creates nothing
  });
});
