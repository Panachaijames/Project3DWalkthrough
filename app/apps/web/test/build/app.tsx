// Mounting the staff app's routes over the mock API for the upload milestone's screen tests: a memory router, React
// Query with no retries, StrictMode, the build page's clocks shortened (debounce 20 ms, poll 40 ms; the defaults are
// asserted in test/upload), and helpers that read the mock's requests.
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { createMemoryRouter } from 'react-router';
import { RouterProvider } from 'react-router/dom';
import { vi } from 'vitest';
import '@/api/client';
import { createRoutes } from '@/router';
import type { BuildSettings, BuildSettingsUpdate } from '@/upload/contracts';
import { timing } from '@/upload/timing';
import { render, waitFor } from '../helpers';
import { createMockApi, type MockApi, type MockRequest } from '../mock-api/core';
import { mockFetch, type MockFetchOptions } from '../mock-api/fetch';

export const opened: { unmount(): Promise<void> }[] = [];

export async function closeAll(): Promise<void> {
  while (opened.length) await opened.pop()!.unmount();
  vi.unstubAllGlobals();
  document.body.replaceChildren();
}

export function fastClocks(): () => void {
  const was = { ...timing };
  timing.settingsDebounceMs = 20;
  timing.pollMs = 40;
  return () => { Object.assign(timing, was); };
}

export async function openApp(path: string, opts: { mock?: MockApi; fetch?: MockFetchOptions; strict?: boolean } = {}) {
  const mock = opts.mock ?? createMockApi();
  vi.stubGlobal('fetch', mockFetch(mock, opts.fetch));
  const queryClient = new QueryClient({ defaultOptions: { queries: { staleTime: 30_000, retry: false } } });
  const router = createMemoryRouter(createRoutes(queryClient), { initialEntries: [path] });
  const v = await render(
    <QueryClientProvider client={queryClient}><RouterProvider router={router} /></QueryClientProvider>,
    { strict: opts.strict ?? true },
  );
  opened.push(v);
  return { v, router, mock, queryClient, body: document.body };
}

/** The settings PUTs the app made, parsed, oldest first. */
export function settingsPuts(mock: MockApi, buildId?: string): (BuildSettingsUpdate & { ifMatch: string | undefined; req: MockRequest })[] {
  return mock.requests
    .filter(r => r.method === 'PUT' && r.path.endsWith('/settings') && (!buildId || r.path.includes(`/builds/${buildId}/`)))
    .map(r => ({ ...(JSON.parse(r.body ?? '{}') as BuildSettingsUpdate), ifMatch: r.headers?.['if-match'], req: r }));
}

/** Waits for a settings PUT that satisfies `check` and the API's answer (200). */
export async function waitForPut(mock: MockApi, check: (s: BuildSettings, u: BuildSettingsUpdate) => boolean): Promise<ReturnType<typeof settingsPuts>[number]> {
  return waitFor(() => settingsPuts(mock).find(p => check(p.settings, p)));
}

/** A project with a draft of the given files (fixtures by position), optionally read, reviewed and built. */
export function draftOf(mock: MockApi, projectId: string, names: string[], opts: { finish?: boolean; reviewed?: boolean; built?: boolean } = {}) {
  const sources = names.map((n, i) => mock.uploads.addSource(projectId, { name: n, bytes: Buffer.from(`${n.toLowerCase().endsWith('.dxf') ? '  0\nSECTION\n' : 'AC1032'} ${i} ${n}`) }));
  return { sources, build: mock.uploads.createBuildNow(projectId, sources.map(s => s.sha1), opts) };
}

export const q = (sel: string) => document.body.querySelector<HTMLElement>(sel);
export const qa = (sel: string) => [...document.body.querySelectorAll<HTMLElement>(sel)];
