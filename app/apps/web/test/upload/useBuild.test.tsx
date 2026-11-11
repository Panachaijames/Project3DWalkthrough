// The build poller (docs/upload/DESIGN.md U-14.2; ACCEPTANCE 2.3 U6): getBuild with withSettings=false every POLL_MS while
// a run is queued or running and not otherwise; the full detail (with settings) fetched again when the poll shows a newer
// settingsRevision (the proposal adopted, or a save elsewhere); answers of the API put into both caches restart the poll.
// And the draft preview's ViewerProject (U-14.4).
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { act } from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import '@/api/client';
import type { BuildDetail } from '@/upload/contracts';
import { draftViewerOptions, toDraftViewerProject } from '@/upload/draftViewerProject';
import { POLL_MS, useBuild, type UseBuild } from '@/upload/useBuild';
import { readJson } from '../mock-api/fixtures';
import { BUILD_FILES } from '../mock-api/builds';
import { render, settle, waitFor } from '../helpers';
import { createMockApi, type MockApi } from '../mock-api/core';
import { mockFetch } from '../mock-api/fetch';

afterEach(() => { vi.unstubAllGlobals(); document.body.replaceChildren(); });

function Probe({ projectId, buildId, out, pollMs }: { projectId: string; buildId: string; out: { current: UseBuild | null }; pollMs: number }) {
  out.current = useBuild(projectId, buildId, { pollMs });
  return <p data-testid="probe">{out.current.detail?.run?.status ?? 'none'}</p>;
}

async function mount(mock: MockApi, buildId: string, pollMs = 100) {
  vi.stubGlobal('fetch', mockFetch(mock));
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const out: { current: UseBuild | null } = { current: null };
  const v = await render(<QueryClientProvider client={queryClient}><Probe projectId="bank-sampeng" buildId={buildId} out={out} pollMs={pollMs} /></QueryClientProvider>, { strict: false });
  return { v, out, queryClient };
}

const gets = (mock: MockApi, buildId: string) => mock.requests.filter(r => r.method === 'GET' && r.path.endsWith(`/builds/${buildId}`));

describe('useBuild', () => {
  it('polls without settings every POLL_MS while the prepare runs, fetches the full detail again when the proposal is adopted, then stops', async () => {
    expect(POLL_MS).toBe(1000);
    const mock = createMockApi();
    const src = mock.uploads.addSource('bank-sampeng', { name: 'I1201.dwg', bytes: Buffer.from('AC1032 one') });
    const b = mock.uploads.createBuildNow('bank-sampeng', [src.sha1]);
    const { v, out } = await mount(mock, b.id);
    await waitFor(() => out.current?.detail?.run?.status === 'done' && out.current.detail.settingsRevision === 1 && out.current.detail.settings !== null);
    const requests = gets(mock, b.id);
    expect(requests[0]!.query ?? '').toBe('');                                  // the full detail first
    const polls = requests.filter(r => r.query === 'withSettings=false');
    expect(polls.length).toBeGreaterThanOrEqual(4);                             // convert, check, read, suggest
    const fulls = requests.filter(r => !r.query);
    expect(fulls.length).toBeGreaterThanOrEqual(2);                             // again for revision 1
    expect(out.current!.detail!.settings!.floors.length).toBe(1);
    expect(out.current!.active).toBe(false);
    const n = gets(mock, b.id).length;
    await settle(400);
    expect(gets(mock, b.id).length).toBe(n);                                    // no poll once the run is done
    await v.unmount();
  });

  it('an answer of the API that starts a run (runBuild) restarts the poll', async () => {
    const mock = createMockApi();
    const src = mock.uploads.addSource('bank-sampeng', { name: 'I1201.dwg', bytes: Buffer.from('AC1032 one') });
    const b = mock.uploads.createBuildNow('bank-sampeng', [src.sha1], { reviewed: true });
    const { v, out } = await mount(mock, b.id);
    await waitFor(() => out.current?.detail?.run?.status === 'done');
    const r = mock.handle({ method: 'POST', path: `/api/projects/bank-sampeng/builds/${b.id}/run`, body: '{}' });
    expect(r.status).toBe(202);
    await act(async () => { out.current!.set(JSON.parse(r.body.toString('utf8')) as BuildDetail); });
    // TanStack Query tells the hook of the new cache data on its own schedule (a timeout), which may land after act():
    // wait for it rather than read it at once (a race that failed 2 runs in 3 on 11 Nov; contract-issues/RI.md)
    await waitFor(() => out.current?.active === true);
    await waitFor(() => out.current?.detail?.result !== null && out.current?.detail?.run?.kind === 'build' && out.current.detail.run.status === 'done');
    expect(out.current!.detail!.result!.runId).toMatch(/-build$/);
    await v.unmount();
  });
});

describe('the draft preview (U-14.4)', () => {
  it('stamp from the result, presentation from the result, no pictures, no saved heights, version 0', () => {
    const model = readJson(BUILD_FILES.model);
    const stages = readJson(BUILD_FILES.stages);
    const presentation = readJson(BUILD_FILES.presentation) as Record<string, unknown>;
    const detail = { projectId: 'e2e-bank', result: { stamp: 'c3a9408304a2', presentation } } as unknown as BuildDetail;
    const p = toDraftViewerProject(detail, model, stages);
    expect(p.stamp).toBe('c3a9408304a2');
    expect(p.ids).toEqual({ projectId: 'e2e-bank', version: 0 });
    expect(p.pictures).toEqual({});
    expect(p.heights).toEqual({});
    expect(p.stages).not.toBeNull();
    expect(draftViewerOptions(false)).toEqual({ build: 'skip', furnitureHeights: 'host', testHook: false });
    expect(() => toDraftViewerProject({ ...detail, result: null } as BuildDetail, model, stages)).toThrow(/not been built/);
  });
});
