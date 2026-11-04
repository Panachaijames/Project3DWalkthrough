// The heights saver (DESIGN.md 15.5, 17.2 web): debounce 600 ms, one request in flight, the newest map wins, Retry
// re-sends the newest map, a pending save is flushed on unmount / version change / pagehide, and the caches updated.
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { HeightMap } from '@walkthrough/viewer';
import { act } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { getFurnitureHeightsQueryKey, getVersionQueryKey, listProjectsQueryKey } from '@/api/generated/@tanstack/react-query.gen';
import type { HeightOverrides, VersionDetail } from '@/api/generated/types.gen';
import { ApiError } from '@/api/client';
import {
  createHeightsSaver,
  useHeightsSaver,
  type HeightsSaver,
  type PutHeights,
  type SaverState,
  type SendInit,
  type VersionPath,
} from '@/lib/useHeightsSaver';
import { render, waitFor } from './helpers';

vi.mock('@walkthrough/viewer', async () => vi.importActual('./fake-viewer'));

interface Call { heights: HeightMap; init: SendInit; resolve(r?: Partial<HeightOverrides>): void; reject(e: unknown): void }

function manualPut() {
  const calls: Call[] = [];
  let revision = 0;
  const put = vi.fn((heights: HeightMap, init: SendInit) => new Promise<HeightOverrides>((resolve, reject) => {
    calls.push({
      heights, init,
      resolve: r => resolve({ heights, revision: ++revision, updatedAt: '2026-11-03T05:00:00Z', ...r }),
      reject,
    });
  }));
  return { put, calls };
}

const flush = () => act(async () => { await Promise.resolve(); await Promise.resolve(); });

describe('createHeightsSaver', () => {
  beforeEach(() => { vi.useFakeTimers(); });
  afterEach(() => { vi.useRealTimers(); });

  it('waits for 600 ms of quiet and sends the newest map once', async () => {
    const { put, calls } = manualPut();
    const states: SaverState[] = [];
    const onSaved = vi.fn();
    const s = createHeightsSaver({ put, onSaved, onState: st => states.push(st) });
    s.change({ table: 60 });
    expect(s.state.status).toBe('saving');
    vi.advanceTimersByTime(300);
    s.change({ table: 600 });
    vi.advanceTimersByTime(599);
    expect(put).not.toHaveBeenCalled();
    vi.advanceTimersByTime(1);
    expect(put).toHaveBeenCalledTimes(1);
    expect(calls[0]!.heights).toEqual({ table: 600 });
    expect(s.state.status).toBe('saving');
    calls[0]!.resolve();
    await flush();
    expect(s.state).toEqual({ status: 'saved', reason: null });
    expect(onSaved).toHaveBeenCalledWith({ heights: { table: 600 }, revision: 1, updatedAt: '2026-11-03T05:00:00Z' }, { table: 600 });
    expect(states.map(st => st.status)).toEqual(['saving', 'saved']);
  });

  it('keeps one request in flight; the newest map goes next', async () => {
    const { put, calls } = manualPut();
    const s = createHeightsSaver({ put });
    s.change({ table: 600 });
    vi.advanceTimersByTime(600);
    expect(put).toHaveBeenCalledTimes(1);
    s.change({ table: 600, seat: 30 });
    vi.advanceTimersByTime(600);
    s.change({ table: 600, seat: 300 });
    vi.advanceTimersByTime(600);
    expect(put).toHaveBeenCalledTimes(1);   // still the first in flight
    calls[0]!.resolve();
    await flush();
    expect(put).toHaveBeenCalledTimes(2);
    expect(calls[1]!.heights).toEqual({ table: 600, seat: 300 });   // the older pending map was replaced
    expect(s.state.status).toBe('saving');
    calls[1]!.resolve();
    await flush();
    expect(s.state.status).toBe('saved');
    expect(put).toHaveBeenCalledTimes(2);
  });

  it('a change while in flight waits for its own debounce', async () => {
    const { put, calls } = manualPut();
    const s = createHeightsSaver({ put });
    s.change({ a: 1 });
    vi.advanceTimersByTime(600);
    s.change({ a: 2 });
    calls[0]!.resolve();
    await flush();
    expect(put).toHaveBeenCalledTimes(1);   // the debounce of { a: 2 } is still running
    vi.advanceTimersByTime(600);
    expect(put).toHaveBeenCalledTimes(2);
    expect(calls[1]!.heights).toEqual({ a: 2 });
  });

  it('shows the reason of a failure and Retry sends the newest map again', async () => {
    const { put, calls } = manualPut();
    const s = createHeightsSaver({ put });
    s.change({ table: 600 });
    vi.advanceTimersByTime(600);
    calls[0]!.reject(new ApiError(503, 'unavailable', 'the store is busy'));
    await flush();
    expect(s.state).toEqual({ status: 'error', reason: 'the store is busy' });
    s.retry();
    expect(put).toHaveBeenCalledTimes(2);
    expect(calls[1]!.heights).toEqual({ table: 600 });
    expect(s.state.status).toBe('saving');
    calls[1]!.resolve();
    await flush();
    expect(s.state).toEqual({ status: 'saved', reason: null });
  });

  it('a newer map after a failure replaces the failed one', async () => {
    const { put, calls } = manualPut();
    const s = createHeightsSaver({ put });
    s.change({ table: 600 });
    vi.advanceTimersByTime(600);
    calls[0]!.reject(new Error('offline'));
    await flush();
    expect(s.state.status).toBe('error');
    s.change({ table: 700 });
    expect(s.state.status).toBe('saving');
    vi.advanceTimersByTime(600);
    expect(calls[1]!.heights).toEqual({ table: 700 });
  });

  it('a failure superseded by a newer map in flight sends the newer one', async () => {
    const { put, calls } = manualPut();
    const s = createHeightsSaver({ put });
    s.change({ a: 1 });
    vi.advanceTimersByTime(600);
    s.change({ a: 2 });
    vi.advanceTimersByTime(600);          // its debounce ended while the first was in flight
    calls[0]!.reject(new Error('lost'));
    await flush();
    expect(put).toHaveBeenCalledTimes(2);
    expect(calls[1]!.heights).toEqual({ a: 2 });
    expect(s.state.status).toBe('saving');
  });

  it('a put that throws at once counts as a failure', async () => {
    const put = vi.fn(() => { throw new Error('bad options'); });
    const s = createHeightsSaver({ put });
    s.change({ a: 1 });
    vi.advanceTimersByTime(600);
    await flush();
    expect(s.state).toEqual({ status: 'error', reason: 'bad options' });
  });

  it('flush sends a debounced or failed map now (with keepalive), and nothing else', async () => {
    const { put, calls } = manualPut();
    const s = createHeightsSaver({ put });
    s.flush();
    expect(put).not.toHaveBeenCalled();
    s.change({ table: 600 });
    s.flush({ keepalive: true });
    expect(put).toHaveBeenCalledTimes(1);
    expect(calls[0]!.init).toEqual({ keepalive: true, ifRevision: 0 });
    vi.advanceTimersByTime(1000);
    expect(put).toHaveBeenCalledTimes(1);   // the debounce was cut short, not repeated
    calls[0]!.reject(new Error('offline'));
    await flush();
    s.flush();
    expect(put).toHaveBeenCalledTimes(2);   // the failed map gets one more try
    calls[1]!.resolve();
    await flush();
    s.flush();
    expect(put).toHaveBeenCalledTimes(2);
  });

  it('a flush while a request is in flight sends the queued map right after it, with keepalive', async () => {
    const { put, calls } = manualPut();
    const s = createHeightsSaver({ put });
    s.change({ a: 1 });
    vi.advanceTimersByTime(600);          // { a: 1 } in flight
    s.change({ a: 2 });
    vi.advanceTimersByTime(600);          // its debounce ended while { a: 1 } was in flight: queued behind it
    s.flush({ keepalive: true });         // pagehide
    expect(put).toHaveBeenCalledTimes(1);
    calls[0]!.resolve();
    await flush();
    expect(put).toHaveBeenCalledTimes(2);
    expect(calls[1]!.heights).toEqual({ a: 2 });
    expect(calls[1]!.init).toEqual({ keepalive: true, ifRevision: 1 });
    calls[1]!.resolve();
    await flush();
    expect(s.state.status).toBe('saved');
  });

  it('after close no more states, but the request in flight and the map queued behind it still go out', async () => {
    const { put, calls } = manualPut();
    const onState = vi.fn();
    const onSaved = vi.fn();
    const s = createHeightsSaver({ put, onState, onSaved });
    s.change({ a: 1 });
    vi.advanceTimersByTime(600);
    s.change({ a: 2 });
    s.flush({ keepalive: true });        // an unmount: the newest map is queued behind the one in flight
    s.close();
    const statesBefore = onState.mock.calls.length;
    calls[0]!.resolve();
    await flush();
    expect(put).toHaveBeenCalledTimes(2);
    expect(calls[1]!.heights).toEqual({ a: 2 });
    expect(calls[1]!.init).toEqual({ keepalive: true, ifRevision: 1 });
    calls[1]!.resolve();
    await flush();
    expect(onSaved).toHaveBeenCalledTimes(2);
    expect(onState.mock.calls.length).toBe(statesBefore);
  });
});

describe('useHeightsSaver', () => {
  const putCalls: { path: VersionPath; heights: HeightMap; init: SendInit }[] = [];
  let answer: (path: VersionPath, heights: HeightMap) => Promise<HeightOverrides>;
  const put: PutHeights = (path, heights, init) => { putCalls.push({ path, heights, init }); return answer(path, heights); };

  beforeEach(() => {
    putCalls.length = 0;
    localStorage.clear();                       // the outbox (an unsaved map of an earlier test would be sent at mount)
    answer = async (_p, heights) => ({ heights, revision: 7, updatedAt: '2026-11-03T05:00:00Z' });
  });
  afterEach(() => { localStorage.clear(); });

  function Probe({ projectId, version, debounceMs, onSaver }: { projectId: string; version: number; debounceMs: number; onSaver: (s: HeightsSaver) => void }) {
    const saver = useHeightsSaver(projectId, version, { put, debounceMs });
    onSaver(saver);
    return <span data-status={saver.state.status}>{saver.state.reason ?? ''}</span>;
  }

  /** debounceMs: 50 for the saves; a minute where a test flushes (so a busy machine cannot let the debounce end first). */
  async function mount(queryClient: QueryClient, projectId: string, version: number, debounceMs = 50) {
    let saver!: HeightsSaver;
    const ui = (id: string, n: number) => (
      <QueryClientProvider client={queryClient}>
        <Probe projectId={id} version={n} debounceMs={debounceMs} onSaver={s => { saver = s; }} />
      </QueryClientProvider>
    );
    const v = await render(ui(projectId, version));
    return { v, saver: () => saver, rerender: (id: string, n: number) => v.rerender(ui(id, n)) };
  }

  const wait = (ms: number) => act(async () => { await new Promise(r => setTimeout(r, ms)); });

  it('saves after the debounce and updates the cached heights and version detail', async () => {
    const qc = new QueryClient();
    const path = { projectId: 'bank-sampeng', version: 2 };
    qc.setQueryData<VersionDetail>(getVersionQueryKey({ path }), { overrides: { heights: {}, revision: 0, updatedAt: null } } as VersionDetail);
    qc.setQueryData(listProjectsQueryKey(), { projects: [] });
    let release!: () => void;
    const gate = new Promise<void>(r => { release = r; });
    answer = async (_p, heights) => { await gate; return { heights, revision: 7, updatedAt: '2026-11-03T05:00:00Z' }; };
    const m = await mount(qc, 'bank-sampeng', 2);
    const status = () => m.v.host.querySelector('span')!.getAttribute('data-status');
    expect(status()).toBe('saved');
    await act(async () => { m.saver().change({ table: 600 }); });
    expect(status()).toBe('saving');                 // waiting for the debounce, or in flight (held by the gate)
    await waitFor(() => putCalls.length === 1);
    expect(putCalls).toEqual([{ path, heights: { table: 600 }, init: { ifRevision: 0 } }]);
    expect(status()).toBe('saving');
    await act(async () => { release(); await gate; });
    await waitFor(() => status() === 'saved');
    expect(qc.getQueryData(getFurnitureHeightsQueryKey({ path }))).toEqual({ heights: { table: 600 }, revision: 7, updatedAt: '2026-11-03T05:00:00Z' });
    expect(qc.getQueryData<VersionDetail>(getVersionQueryKey({ path }))?.overrides).toEqual({ heights: { table: 600 }, revision: 7, updatedAt: '2026-11-03T05:00:00Z' });
    expect(qc.getQueryState(listProjectsQueryKey())?.isInvalidated).toBe(true);
    await m.v.unmount();
  });

  it('shows Not saved with the reason; retry re-sends', async () => {
    const qc = new QueryClient();
    let fail = true;
    answer = async (_p, heights) => {
      if (fail) throw new ApiError(422, 'invalid_heights', 'unknown kind');
      return { heights, revision: 1, updatedAt: null };
    };
    const m = await mount(qc, 'bank-sampeng', 2);
    await act(async () => { m.saver().change({ nope: 600 }); });
    await wait(80);
    const span = m.v.host.querySelector('span')!;
    expect(span.getAttribute('data-status')).toBe('error');
    expect(span.textContent).toBe('unknown kind');
    fail = false;
    await act(async () => { m.saver().retry(); });
    await wait(10);
    expect(span.getAttribute('data-status')).toBe('saved');
    expect(putCalls.map(c => c.heights)).toEqual([{ nope: 600 }, { nope: 600 }]);
    await m.v.unmount();
  });

  it('flushes a pending save when the version changes and when the page unmounts', async () => {
    const qc = new QueryClient();
    const m = await mount(qc, 'bank-sampeng', 2, 60_000);
    await act(async () => { m.saver().change({ table: 600 }); });
    await m.rerender('bank-sampeng', 1);
    expect(putCalls.map(c => [c.path.version, c.heights])).toEqual([[2, { table: 600 }]]);   // flushed at once, for v2
    expect(m.v.host.querySelector('span')!.getAttribute('data-status')).toBe('saved');      // v1 starts clean
    await act(async () => { m.saver().change({ seat: 300 }); });
    await m.v.unmount();
    expect(putCalls.map(c => [c.path.version, c.heights, c.init])).toEqual([[2, { table: 600 }, { keepalive: true, ifRevision: 0 }], [1, { seat: 300 }, { keepalive: true, ifRevision: 0 }]]);
  });

  it('flushes on pagehide with keepalive, and removes its listener on unmount', async () => {
    const qc = new QueryClient();
    const add = vi.spyOn(window, 'addEventListener');
    const remove = vi.spyOn(window, 'removeEventListener');
    const m = await mount(qc, 'hotel-lobby', 1, 60_000);
    await act(async () => { m.saver().change({ table: 600 }); });
    await act(async () => { window.dispatchEvent(new Event('pagehide')); });
    expect(putCalls).toEqual([{ path: { projectId: 'hotel-lobby', version: 1 }, heights: { table: 600 }, init: { keepalive: true, ifRevision: 0 } }]);
    await m.v.unmount();
    const added = add.mock.calls.filter(c => c[0] === 'pagehide').map(c => c[1]);
    const removed = remove.mock.calls.filter(c => c[0] === 'pagehide').map(c => c[1]);
    expect(added.length).toBeGreaterThan(0);
    expect(new Set(removed)).toEqual(new Set(added));   // StrictMode's two mounts, both taken off
    add.mockRestore();
    remove.mockRestore();
  });
});
