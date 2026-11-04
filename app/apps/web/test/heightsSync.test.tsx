// Fix step (3 Nov review, findings "adversarial" 1, 3, 4): the heights saver never loses a typed height (the outbox in
// this browser until the API has it), sends a save the API did not answer again by itself, names the revision it was typed
// over (If-Match) and merges this tab's changes into heights saved elsewhere, and takes over heights saved elsewhere when
// it has nothing unsaved.
import { QueryClient } from '@tanstack/react-query';
import type { HeightMap } from '@walkthrough/viewer';
import { act } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { getFurnitureHeightsQueryKey } from '@/api/generated/@tanstack/react-query.gen';
import type { HeightOverrides } from '@/api/generated/types.gen';
import { ApiError } from '@/api/client';
import { allUnsent, mergeChanges, readUnsent, writeUnsent, type UnsentEntry } from '@/lib/heightsOutbox';
import { createHeightsSaver, sendUnsent, type PutHeights, type SendInit } from '@/lib/useHeightsSaver';

vi.mock('@walkthrough/viewer', async () => vi.importActual('./fake-viewer'));

interface Call { heights: HeightMap; init: SendInit; resolve(r?: Partial<HeightOverrides>): void; reject(e: unknown): void }

function manualPut() {
  const calls: Call[] = [];
  let revision = 0;
  const put = vi.fn((heights: HeightMap, init: SendInit) => new Promise<HeightOverrides>((resolve, reject) => {
    calls.push({ heights, init, resolve: r => resolve({ heights, revision: ++revision, updatedAt: '2026-11-03T05:00:00Z', ...r }), reject });
  }));
  return { put, calls };
}
const flush = () => act(async () => { await Promise.resolve(); await Promise.resolve(); });
const conflict = (revision: number, heights: HeightMap) =>
  new ApiError(412, 'revision_conflict', 'changed elsewhere', { revision, heights, updatedAt: null });
const NOT_ANSWERING = 'the API did not answer (is it running?)';

describe('createHeightsSaver: two tabs, the API coming back, nothing dropped', () => {
  beforeEach(() => { vi.useFakeTimers(); });
  afterEach(() => { vi.useRealTimers(); });

  it('every PUT names the revision it was typed over (If-Match): the base first, then each answer', async () => {
    const { put, calls } = manualPut();
    const s = createHeightsSaver({ put, base: { revision: 4, heights: { seat: 300 } } });
    s.change({ seat: 300, table: 600 });
    vi.advanceTimersByTime(600);
    expect(calls[0]!.init).toEqual({ ifRevision: 4 });
    calls[0]!.resolve({ revision: 5 });
    await flush();
    expect(s.base.revision).toBe(5);
    s.change({ table: 600 });
    vi.advanceTimersByTime(600);
    expect(calls[1]!.init).toEqual({ ifRevision: 5 });
  });

  it("heights saved elsewhere since (412): this tab's changes are merged into them, shown, and sent again", async () => {
    const { put, calls } = manualPut();
    const remote = vi.fn();
    const s = createHeightsSaver({ put, onRemote: remote, base: { revision: 1, heights: { table: 600 } } });
    s.change({ table: 600, seat: 300 });                              // this tab: seat typed (table as saved)
    vi.advanceTimersByTime(600);
    calls[0]!.reject(conflict(2, { table: 640, cabinet: 1000 }));     // meanwhile another tab saved table 640, cabinet 1000
    await flush();
    expect(remote).toHaveBeenCalledWith({ table: 640, cabinet: 1000, seat: 300 });
    expect(calls).toHaveLength(2);
    expect([calls[1]!.heights, calls[1]!.init]).toEqual([{ table: 640, cabinet: 1000, seat: 300 }, { ifRevision: 2 }]);
    calls[1]!.resolve({ revision: 3 });
    await flush();
    expect(s.state.status).toBe('saved');
  });

  it("a reset in this tab survives the merge (the kind goes back to the model's); the other kinds are theirs", async () => {
    const { put, calls } = manualPut();
    const s = createHeightsSaver({ put, base: { revision: 1, heights: { table: 600, seat: 300 } } });
    s.change({ seat: 300 });                                           // table reset to the model's
    vi.advanceTimersByTime(600);
    calls[0]!.reject(conflict(2, { table: 600, seat: 320 }));
    await flush();
    expect(calls[1]!.heights).toEqual({ seat: 320 });
    expect(s.state.status).toBe('saving');
  });

  it('a save the API did not answer is sent again by itself, sooner when the window comes back', async () => {
    const { put, calls } = manualPut();
    const s = createHeightsSaver({ put, retryDelaysMs: [2_000, 5_000] });
    s.change({ table: 600 });
    vi.advanceTimersByTime(600);
    calls[0]!.reject(new ApiError(502, 'network_error', NOT_ANSWERING));
    await flush();
    expect(s.state).toEqual({ status: 'error', reason: NOT_ANSWERING, unreachable: true });
    vi.advanceTimersByTime(1_999);
    expect(calls).toHaveLength(1);
    vi.advanceTimersByTime(1);
    expect(calls).toHaveLength(2);                                     // by itself, after 2 s
    calls[1]!.reject(new ApiError(0, 'network_error', NOT_ANSWERING));
    await flush();
    vi.advanceTimersByTime(4_000);
    expect(calls).toHaveLength(2);                                     // the next wait is 5 s ...
    s.retrySoon();                                                     // ... but the window came back online
    expect(calls).toHaveLength(3);
    calls[2]!.resolve();
    await flush();
    expect(s.state).toEqual({ status: 'saved', reason: null });
    vi.advanceTimersByTime(60_000);
    expect(calls).toHaveLength(3);                                     // nothing more
  });

  it('a save the API refused (422) is not sent again by itself; Retry still sends it', async () => {
    const { put, calls } = manualPut();
    const s = createHeightsSaver({ put });
    s.change({ nope: 600 });
    vi.advanceTimersByTime(600);
    calls[0]!.reject(new ApiError(422, 'invalid_heights', 'unknown kind'));
    await flush();
    vi.advanceTimersByTime(120_000);
    s.retrySoon();
    expect(calls).toHaveLength(1);
    s.retry();
    expect(calls).toHaveLength(2);
  });

  it('the newest unsaved map is kept (the outbox) until the API has it; the next visit starts from it and sends it', async () => {
    const { put, calls } = manualPut();
    const kept: (UnsentEntry | null)[] = [];
    const s = createHeightsSaver({ put, onUnsent: e => kept.push(e), base: { revision: 2, heights: {} } });
    s.change({ table: 600 });
    expect(kept.at(-1)).toMatchObject({ heights: { table: 600 }, base: { revision: 2, heights: {} } });
    vi.advanceTimersByTime(600);
    calls[0]!.reject(new Error('offline'));
    await flush();
    expect(kept.at(-1)).toMatchObject({ heights: { table: 600 } });
    s.close();                                                         // the page goes (its keepalive failed too)
    vi.advanceTimersByTime(120_000);
    expect(calls).toHaveLength(1);                                     // no retry after close: the outbox keeps it
    expect(kept.at(-1)).not.toBeNull();
    const t = createHeightsSaver({ put, onUnsent: e => kept.push(e), unsent: kept.at(-1)!, base: { revision: 9, heights: {} } });
    expect(calls).toHaveLength(2);                                     // at once, over the base it was typed on
    expect([calls[1]!.heights, calls[1]!.init]).toEqual([{ table: 600 }, { ifRevision: 2 }]);
    expect(t.state.status).toBe('saving');
    calls[1]!.resolve();
    await flush();
    expect(kept.at(-1)).toBeNull();
    expect(t.state.status).toBe('saved');
  });

  it('heights saved elsewhere are taken over when this tab has nothing unsaved, and left to the merge while it has', async () => {
    const { put, calls } = manualPut();
    const remote = vi.fn();
    const s = createHeightsSaver({ put, onRemote: remote, base: { revision: 1, heights: { table: 600 } } });
    s.adopt({ revision: 1, heights: { table: 600 } });
    expect(remote).not.toHaveBeenCalled();
    s.adopt({ revision: 2, heights: { seat: 300 } });
    expect(remote).toHaveBeenCalledWith({ seat: 300 });
    expect(s.base).toEqual({ revision: 2, heights: { seat: 300 } });
    s.change({ seat: 300, cabinet: 1000 });
    s.adopt({ revision: 3, heights: { table: 700 } });                // unsaved here: ignored (the PUT meets it, merges)
    expect(remote).toHaveBeenCalledTimes(1);
    vi.advanceTimersByTime(600);
    expect(calls[0]!.init).toEqual({ ifRevision: 2 });
  });

  it('a refetch older than what this tab saved (it started before the save) is not taken over', async () => {
    const { put, calls } = manualPut();
    const remote = vi.fn();
    const s = createHeightsSaver({ put, onRemote: remote, base: { revision: 4, heights: { table: 600 } } });
    s.change({ table: 640 });
    vi.advanceTimersByTime(600);
    calls[0]!.resolve({ revision: 5 });
    await flush();
    expect(s.base).toEqual({ revision: 5, heights: { table: 640 } });
    s.adopt({ revision: 4, heights: { table: 600 } });                // the refetch of before the save, landing after it
    expect(remote).not.toHaveBeenCalled();
    expect(s.base).toEqual({ revision: 5, heights: { table: 640 } });
    s.adopt({ revision: 6, heights: { table: 700 } });                // newer: taken over
    expect(remote).toHaveBeenCalledWith({ table: 700 });
  });
});

describe('the outbox', () => {
  beforeEach(() => { localStorage.clear(); });
  afterEach(() => { localStorage.clear(); });

  it('reads back what it wrote, drops junk, lists every version', () => {
    const entry: UnsentEntry = { heights: { table: 600 }, base: { revision: 3, heights: { seat: 300 } }, at: '2026-11-03T05:00:00Z' };
    writeUnsent({ projectId: 'bank-sampeng', version: 2 }, entry);
    expect(readUnsent({ projectId: 'bank-sampeng', version: 2 })).toEqual(entry);
    localStorage.setItem('walkthrough-unsaved-heights:hotel-lobby:1', '{"heights":{"a":"x"},"base":{"revision":-1,"heights":{}}}');
    expect(readUnsent({ projectId: 'hotel-lobby', version: 1 })).toBeNull();
    expect(allUnsent().map(x => x.path)).toEqual([{ projectId: 'bank-sampeng', version: 2 }]);
    writeUnsent({ projectId: 'bank-sampeng', version: 2 }, null);
    expect(readUnsent({ projectId: 'bank-sampeng', version: 2 })).toBeNull();
  });

  it("mergeChanges: this tab's value where it changed a kind, theirs elsewhere", () => {
    expect(mergeChanges({ table: 600 }, { table: 600, seat: 300 }, { table: 640 })).toEqual({ table: 640, seat: 300 });
    expect(mergeChanges({ table: 600 }, {}, { table: 640, seat: 1 })).toEqual({ seat: 1 });
    expect(mergeChanges({}, { table: 500 }, { table: 640 })).toEqual({ table: 500 });
  });

  it('sendUnsent (another version than the one on screen): If-Match, a merge, then the entry is gone', async () => {
    const qc = new QueryClient();
    const path = { projectId: 'bank-sampeng', version: 2 };
    const entry: UnsentEntry = { heights: { table: 600 }, base: { revision: 1, heights: {} }, at: '' };
    writeUnsent(path, entry);
    const seen: SendInit[] = [];
    let first = true;
    const put: PutHeights = async (_p, heights, init) => {
      seen.push(init);
      if (first) { first = false; throw conflict(4, { seat: 300 }); }
      return { heights, revision: 5, updatedAt: null };
    };
    expect(await sendUnsent(path, entry, put, qc)).toBe(true);
    expect(seen).toEqual([{ ifRevision: 1 }, { ifRevision: 4 }]);
    expect(readUnsent(path)).toBeNull();
    expect(qc.getQueryData(getFurnitureHeightsQueryKey({ path }))).toEqual({ heights: { seat: 300, table: 600 }, revision: 5, updatedAt: null });
    writeUnsent(path, entry);
    expect(await sendUnsent(path, entry, async () => { throw new ApiError(0, 'network_error', NOT_ANSWERING); }, qc)).toBe(false);
    expect(readUnsent(path)).toEqual(entry);                          // kept for the next try
  });
});
