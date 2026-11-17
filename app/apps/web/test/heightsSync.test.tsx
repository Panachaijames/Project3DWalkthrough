// Fix step (3 Nov review, findings "adversarial" 1, 3, 4): the heights saver never loses a typed height (the outbox in
// this browser until the API has it), sends a save the API did not answer again by itself, names the revision it was typed
// over (If-Match) and merges this tab's changes into heights saved elsewhere, and takes over heights saved elsewhere when
// it has nothing unsaved.
import { QueryClient } from '@tanstack/react-query';
import type { HeightMap, PieceEditMap } from '@walkthrough/viewer';
import { act } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { getFurnitureHeightsQueryKey } from '@/api/generated/@tanstack/react-query.gen';
import type { HeightOverrides } from '@/api/generated/types.gen';
import { ApiError } from '@/api/client';
import { allUnsent, editsOf, mergeChanges, mergeEdits, readUnsent, sameEdits, writeUnsent, type UnsentEntry } from '@/lib/heightsOutbox';
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

// ------------------------------------------------------------------------------------------- step BX: the deleted boxes
// docs/boxes/DESIGN.md 6.1: the deleted furniture boxes go through the same core (one PUT, one revision, If-Match), sent
// only while the tab's own change is unsaved (the dirty flag), merged per id on a 412, taken over when idle; onRemoteEdits
// shows a map the viewer did not make.
interface EditsCall { heights: HeightMap; init: SendInit; edits: PieceEditMap | undefined; args: number; resolve(r?: Partial<HeightOverrides>): void; reject(e: unknown): void }

/** A put that records its third argument (the edits) and answers with what it was sent unless told otherwise. */
function editsPut(start = 0) {
  const calls: EditsCall[] = [];
  let revision = start;
  let saved: PieceEditMap = {};
  const put = vi.fn((...a: [HeightMap, SendInit, PieceEditMap?]) => new Promise<HeightOverrides>((resolve, reject) => {
    const [heights, init, edits] = a;
    calls.push({
      heights, init, edits, args: a.length,
      resolve: r => {
        if (edits) saved = edits;
        resolve({ heights, pieceEdits: saved, revision: ++revision, updatedAt: '2026-11-16T05:00:00Z', ...r });
      },
      reject,
    });
  }));
  return { put, calls };
}
const R = { removed: true } as const;
const conflictWith = (revision: number, heights: HeightMap, pieceEdits?: PieceEditMap) =>
  new ApiError(412, 'revision_conflict', 'changed elsewhere', { revision, heights, updatedAt: null, ...(pieceEdits ? { pieceEdits } : {}) });

describe('createHeightsSaver: the deleted boxes (step BX)', () => {
  beforeEach(() => { vi.useFakeTimers(); });
  afterEach(() => { vi.useRealTimers(); });

  it('a delete and a typed height in the same 600 ms go in one PUT, {heights, pieceEdits}', async () => {
    const { put, calls } = editsPut(3);
    const s = createHeightsSaver({ put, base: { revision: 3, heights: { seat: 300 } } });
    s.changeEdits({ 'L1-seat-001': R });
    vi.advanceTimersByTime(300);
    s.change({ seat: 300, table: 600 });
    vi.advanceTimersByTime(599);
    expect(put).not.toHaveBeenCalled();
    vi.advanceTimersByTime(1);
    expect(calls).toHaveLength(1);
    expect([calls[0]!.heights, calls[0]!.init, calls[0]!.edits]).toEqual([{ seat: 300, table: 600 }, { ifRevision: 3 }, { 'L1-seat-001': R }]);
    expect(s.state).toEqual({ status: 'saving', reason: null, editsUnsaved: true });
    calls[0]!.resolve();
    await flush();
    expect(s.state).toEqual({ status: 'saved', reason: null });
    expect(s.base).toEqual({ revision: 4, heights: { seat: 300, table: 600 }, pieceEdits: { 'L1-seat-001': R } });
  });

  it("a delete alone sends the tab's latest heights with it (the last typed map, else the saved one)", async () => {
    const { put, calls } = editsPut(1);
    const s = createHeightsSaver({ put, base: { revision: 1, heights: { seat: 300 } } });
    s.changeEdits({ 'L1-seat-001': R });
    vi.advanceTimersByTime(600);
    expect([calls[0]!.heights, calls[0]!.edits]).toEqual([{ seat: 300 }, { 'L1-seat-001': R }]);
    calls[0]!.resolve();
    await flush();
    s.change({ table: 600 });                                          // typed, still waiting ...
    s.changeEdits({});                                                 // ... when the box is restored
    vi.advanceTimersByTime(600);
    expect([calls[1]!.heights, calls[1]!.edits]).toEqual([{ table: 600 }, {}]);   // {} = every box back
  });

  it('a heights-only PUT has no pieceEdits (two arguments: the body {heights}); no editsUnsaved', async () => {
    const { put, calls } = editsPut();
    const s = createHeightsSaver({ put, base: { revision: 2, heights: {}, pieceEdits: { 'L1-seat-001': R } } });
    s.change({ table: 600 });
    expect(s.state).toEqual({ status: 'saving', reason: null });
    vi.advanceTimersByTime(600);
    expect([calls[0]!.args, calls[0]!.edits]).toEqual([2, undefined]);
    calls[0]!.resolve({ pieceEdits: { 'L1-seat-001': R } });         // the API kept them
    await flush();
    expect(s.base).toEqual({ revision: 1, heights: { table: 600 }, pieceEdits: { 'L1-seat-001': R } });
  });

  it('settled(): what the tab shows when nothing is unsaved (a takeover included); null while anything is (fix of 17 Nov)', async () => {
    const { put, calls } = editsPut(2);
    const s = createHeightsSaver({ put, base: { revision: 1, heights: { seat: 300 } } });
    expect(s.settled()).toEqual({ heights: { seat: 300 }, pieceEdits: {} });
    s.adopt({ revision: 2, heights: { seat: 310 }, pieceEdits: { 'L1-table-005': R } });   // another tab's
    expect(s.settled()).toEqual({ heights: { seat: 310 }, pieceEdits: { 'L1-table-005': R } });
    s.changeEdits({ 'L1-table-005': R, 'L1-atm-001': R });
    expect(s.settled()).toBeNull();                                    // debouncing, dirty
    vi.advanceTimersByTime(600);
    expect(s.settled()).toBeNull();                                    // in flight
    calls[0]!.resolve({ pieceEdits: { 'L1-atm-001': R, 'L1-table-005': R } });
    await flush();
    expect(s.settled()).toEqual({ heights: { seat: 310 }, pieceEdits: { 'L1-atm-001': R, 'L1-table-005': R } });
    s.change({ seat: 320 });
    expect(s.settled()).toBeNull();                                    // a height typed, not sent yet
  });

  it("B takes over A's deletion when idle, then types a height: the body is {heights}, the deletion stays", async () => {
    const { put, calls } = editsPut(2);
    const remoteEdits = vi.fn();
    const s = createHeightsSaver({ put, onRemoteEdits: remoteEdits, base: { revision: 1, heights: {} } });
    s.adopt({ revision: 2, heights: {}, pieceEdits: { 'L1-table-005': R, 'L1-computer-001': R } });   // A deleted a table
    expect(remoteEdits).toHaveBeenCalledWith({ 'L1-table-005': R, 'L1-computer-001': R });
    s.change({ seat: 320 });
    vi.advanceTimersByTime(600);
    expect([calls[0]!.args, calls[0]!.init]).toEqual([2, { ifRevision: 2 }]);
    calls[0]!.resolve({ pieceEdits: { 'L1-computer-001': R, 'L1-table-005': R } });   // kept as they were (another order)
    await flush();
    expect(remoteEdits).toHaveBeenCalledTimes(1);                     // nothing new to show
    expect(s.base.pieceEdits).toEqual({ 'L1-table-005': R, 'L1-computer-001': R });
  });

  it('a revisit replays a heights-only outbox entry on a version with saved deletions, then a height is typed: the deletions stay', async () => {
    const { put, calls } = editsPut(3);
    const remoteEdits = vi.fn();
    const saved = { 'L1-seat-001': R };
    const entry: UnsentEntry = { heights: { seat: 300 }, base: { revision: 1, heights: {} }, at: '' };   // from before the deletion
    const s = createHeightsSaver({ put, onRemoteEdits: remoteEdits, unsent: entry, base: { revision: 3, heights: {}, pieceEdits: saved } });
    expect([calls[0]!.heights, calls[0]!.init, calls[0]!.args]).toEqual([{ seat: 300 }, { ifRevision: 1 }, 2]);   // {heights}
    calls[0]!.reject(conflictWith(3, {}, saved));
    await flush();
    expect([calls[1]!.heights, calls[1]!.init, calls[1]!.args]).toEqual([{ seat: 300 }, { ifRevision: 3 }, 2]);   // still {heights}
    expect(remoteEdits).not.toHaveBeenCalled();                       // the viewer already shows the saved deletions
    calls[1]!.resolve({ pieceEdits: saved });
    await flush();
    s.change({ seat: 300, table: 600 });
    vi.advanceTimersByTime(600);
    expect(calls[2]!.args).toBe(2);
    expect(s.base.pieceEdits).toEqual(saved);
  });

  it("a 412 merges per id: the other tab's deletion and this tab's restore both stay; the merged map is shown and sent", async () => {
    const { put, calls } = editsPut(2);
    const remoteEdits = vi.fn();
    const s = createHeightsSaver({ put, onRemoteEdits: remoteEdits, base: { revision: 1, heights: {}, pieceEdits: { a: R, b: R } } });
    s.changeEdits({ a: R });                                           // this tab restores b
    vi.advanceTimersByTime(600);
    expect(calls[0]!.edits).toEqual({ a: R });
    calls[0]!.reject(conflictWith(2, {}, { a: R, b: R, c: R }));       // meanwhile the other tab deleted c
    await flush();
    expect(remoteEdits).toHaveBeenCalledWith({ a: R, c: R });
    expect([calls[1]!.init, calls[1]!.edits]).toEqual([{ ifRevision: 2 }, { a: R, c: R }]);
    expect(s.state.editsUnsaved).toBe(true);
    calls[1]!.resolve();
    await flush();
    expect(s.state).toEqual({ status: 'saved', reason: null });
    expect(s.base.pieceEdits).toEqual({ a: R, c: R });
    expect(remoteEdits).toHaveBeenCalledTimes(1);
  });

  it('a 412 while the edits are not dirty takes theirs, shows them, and sends {heights} again', async () => {
    const { put, calls } = editsPut(1);
    const remoteEdits = vi.fn();
    const s = createHeightsSaver({ put, onRemoteEdits: remoteEdits, base: { revision: 1, heights: {} } });
    s.change({ table: 600 });
    vi.advanceTimersByTime(600);
    calls[0]!.reject(conflictWith(2, {}, { x: R }));
    await flush();
    expect(remoteEdits).toHaveBeenCalledWith({ x: R });
    expect([calls[1]!.heights, calls[1]!.args]).toEqual([{ table: 600 }, 2]);
    // a 412 without pieceEdits in its details (none saved: read as {}): the tab's empty map stays, nothing to show
    const t = createHeightsSaver({ put, onRemoteEdits: remoteEdits, base: { revision: 5, heights: {} } });
    t.change({ seat: 300 });
    vi.advanceTimersByTime(600);
    calls[2]!.reject(conflictWith(6, { table: 640 }));
    await flush();
    expect(remoteEdits).toHaveBeenCalledTimes(1);
    expect(t.base).toEqual({ revision: 6, heights: { table: 640 } });
  });

  it('a success whose map differs from the one sent (the API closed it) shows the saved map', async () => {
    const { put, calls } = editsPut();
    const remoteEdits = vi.fn();
    const s = createHeightsSaver({ put, onRemoteEdits: remoteEdits });
    s.changeEdits({ 'L1-table-005': R });
    vi.advanceTimersByTime(600);
    calls[0]!.resolve({ pieceEdits: { 'L1-computer-001': R, 'L1-table-005': R } });
    await flush();
    expect(remoteEdits).toHaveBeenCalledWith({ 'L1-computer-001': R, 'L1-table-005': R });
    // the same map back in another order: nothing to show
    s.changeEdits({ 'L1-table-005': R, 'L1-computer-001': R, 'L1-seat-002': R });
    vi.advanceTimersByTime(600);
    calls[1]!.resolve({ pieceEdits: { 'L1-computer-001': R, 'L1-seat-002': R, 'L1-table-005': R } });
    await flush();
    expect(remoteEdits).toHaveBeenCalledTimes(1);
  });

  it('a delete while a save is out stays unsaved (editsUnsaved) and goes next, after its own debounce', async () => {
    const { put, calls } = editsPut();
    const s = createHeightsSaver({ put });
    s.changeEdits({ a: R });
    vi.advanceTimersByTime(600);
    s.changeEdits({ a: R, b: R });
    calls[0]!.resolve();
    await flush();
    expect(s.state).toEqual({ status: 'saving', reason: null, editsUnsaved: true });
    vi.advanceTimersByTime(600);
    expect(calls[1]!.edits).toEqual({ a: R, b: R });
    calls[1]!.resolve();
    await flush();
    expect(s.state).toEqual({ status: 'saved', reason: null });
  });

  it('a failed save of deleted boxes: Not saved with editsUnsaved; the next save carries them with a height typed meanwhile', async () => {
    const { put, calls } = editsPut();
    const s = createHeightsSaver({ put, retryDelaysMs: [] });
    s.changeEdits({ a: R });
    vi.advanceTimersByTime(600);
    calls[0]!.reject(new ApiError(500, 'store_error', 'the store is busy'));
    await flush();
    expect(s.state).toEqual({ status: 'error', reason: 'the store is busy', editsUnsaved: true });
    s.change({ table: 600 });
    vi.advanceTimersByTime(600);
    expect([calls[1]!.heights, calls[1]!.edits]).toEqual([{ table: 600 }, { a: R }]);
  });

  it('the outbox keeps unsaved deleted boxes (and only then); the next visit starts from them and sends them', async () => {
    const { put, calls } = editsPut(2);
    const kept: (UnsentEntry | null)[] = [];
    const s = createHeightsSaver({ put, onUnsent: e => kept.push(e), base: { revision: 2, heights: { seat: 300 }, pieceEdits: { a: R } } });
    s.change({ seat: 320 });
    expect(kept.at(-1)).toMatchObject({ heights: { seat: 320 }, base: { revision: 2, heights: { seat: 300 }, pieceEdits: { a: R } } });
    expect(kept.at(-1)).not.toHaveProperty('pieceEdits');            // a heights-only entry
    s.changeEdits({});                                                 // every box restored
    expect(kept.at(-1)).toMatchObject({ heights: { seat: 320 }, pieceEdits: {} });
    vi.advanceTimersByTime(600);
    calls[0]!.reject(new Error('offline'));
    await flush();
    s.close();
    const entry = kept.at(-1)!;
    expect(entry.pieceEdits).toEqual({});
    const t = createHeightsSaver({ put, onUnsent: e => kept.push(e), unsent: entry, base: { revision: 9, heights: {} } });
    expect([calls[1]!.heights, calls[1]!.init, calls[1]!.edits]).toEqual([{ seat: 320 }, { ifRevision: 2 }, {}]);
    expect(t.state.editsUnsaved).toBe(true);
    calls[1]!.resolve();
    await flush();
    expect(kept.at(-1)).toBeNull();
    expect(t.state).toEqual({ status: 'saved', reason: null });
  });

  it('adopt takes over deleted boxes only when idle and not dirty; the same map again shows nothing', async () => {
    const { put, calls } = editsPut(1);
    const remoteEdits = vi.fn();
    const s = createHeightsSaver({ put, onRemoteEdits: remoteEdits, base: { revision: 1, heights: {} } });
    s.changeEdits({ a: R });
    s.adopt({ revision: 5, heights: {}, pieceEdits: { b: R } });       // dirty: ignored (the PUT meets it, merges)
    expect(remoteEdits).not.toHaveBeenCalled();
    vi.advanceTimersByTime(600);
    s.adopt({ revision: 6, heights: {}, pieceEdits: { b: R } });       // in flight: ignored
    calls[0]!.resolve();                                               // saved as revision 2, {a}
    await flush();
    expect(remoteEdits).not.toHaveBeenCalled();
    s.adopt({ revision: 7, heights: {}, pieceEdits: { a: R } });       // idle, the same map: nothing to show
    expect(remoteEdits).not.toHaveBeenCalled();
    expect(s.base.revision).toBe(7);
    s.adopt({ revision: 8, heights: {}, pieceEdits: { a: R, b: R } });
    expect(remoteEdits).toHaveBeenCalledWith({ a: R, b: R });
    s.adopt({ revision: 9, heights: {} });                             // every box restored elsewhere
    expect(remoteEdits).toHaveBeenLastCalledWith({});
  });

  it('after close (the page went to another version) neither onRemote nor onRemoteEdits is called; the merged save still goes', async () => {
    const { put, calls } = editsPut(1);
    const remote = vi.fn(), remoteEdits = vi.fn();
    const s = createHeightsSaver({ put, onRemote: remote, onRemoteEdits: remoteEdits, base: { revision: 1, heights: {} } });
    s.changeEdits({ a: R });
    s.flush({ keepalive: true });
    s.close();
    calls[0]!.reject(conflictWith(2, { table: 640 }, { b: R }));
    await flush();
    expect([remote.mock.calls.length, remoteEdits.mock.calls.length]).toEqual([0, 0]);
    expect([calls[1]!.init, calls[1]!.edits]).toEqual([{ ifRevision: 2 }, { b: R, a: R }]);   // the page is still there: no keepalive needed
  });
});

describe('the outbox and the merge: the deleted boxes (step BX)', () => {
  beforeEach(() => { localStorage.clear(); });
  afterEach(() => { localStorage.clear(); });

  it('an entry with deleted boxes reads back as written; an old entry parses as before; odd edits are dropped', () => {
    const p = { projectId: 'bank-sampeng', version: 2 };
    const entry: UnsentEntry = { heights: { table: 600 }, pieceEdits: { a: R }, base: { revision: 3, heights: {}, pieceEdits: { b: R } }, at: 'x' };
    writeUnsent(p, entry);
    expect(readUnsent(p)).toEqual(entry);
    const restoredAll: UnsentEntry = { heights: {}, pieceEdits: {}, base: { revision: 1, heights: {}, pieceEdits: { b: R } }, at: '' };
    writeUnsent(p, restoredAll);
    expect(readUnsent(p)).toEqual(restoredAll);                         // {} kept: "every box back" is a change too
    localStorage.setItem('walkthrough-unsaved-heights:bank-sampeng:2', '{"heights":{"seat":300},"base":{"revision":1,"heights":{}},"at":"t"}');
    expect(readUnsent(p)).toEqual({ heights: { seat: 300 }, base: { revision: 1, heights: {} }, at: 't' });
    localStorage.setItem('walkthrough-unsaved-heights:bank-sampeng:2',
      '{"heights":{},"pieceEdits":{"a":{"removed":true},"b":{"removed":"yes"},"c":7,"d":{"removed":false}},"base":{"revision":1,"heights":{},"pieceEdits":[1]},"at":""}');
    expect(readUnsent(p)).toEqual({ heights: {}, pieceEdits: { a: R }, base: { revision: 1, heights: {} }, at: '' });
  });

  it('mergeEdits: mine where this tab changed an id (absent = restored), theirs elsewhere; sameEdits ignores the order', () => {
    expect(mergeEdits({ a: R, b: R }, { a: R }, { a: R, b: R, c: R })).toEqual({ a: R, c: R });
    expect(mergeEdits({}, { a: R }, { b: R })).toEqual({ b: R, a: R });
    expect(mergeEdits({ a: R }, { a: R }, {})).toEqual({});              // restored there, untouched here: theirs
    expect(mergeEdits({ a: R }, {}, { a: R, b: R })).toEqual({ b: R });
    expect(sameEdits({ a: R, b: R }, { b: R, a: R })).toBe(true);
    expect(sameEdits({ a: R }, { a: R, b: R })).toBe(false);
    expect(editsOf({ a: { removed: true }, b: { removed: false }, c: null, d: 'x' })).toEqual({ a: R });
    expect(editsOf([1, 2])).toEqual({});
  });

  it("sendUnsent carries the entry's deleted boxes with the same merge; a heights-only entry sends {heights}", async () => {
    const qc = new QueryClient();
    const path = { projectId: 'bank-sampeng', version: 2 };
    const entry: UnsentEntry = { heights: {}, pieceEdits: { a: R }, base: { revision: 1, heights: {} }, at: '' };
    writeUnsent(path, entry);
    const seen: [SendInit, PieceEditMap | undefined][] = [];
    let first = true;
    const put: PutHeights = async (_p, heights, init, pieceEdits) => {
      seen.push([init, pieceEdits]);
      if (first) { first = false; throw conflictWith(4, {}, { b: R }); }
      return { heights, pieceEdits: pieceEdits ?? {}, revision: 5, updatedAt: null };
    };
    expect(await sendUnsent(path, entry, put, qc)).toBe(true);
    expect(seen).toEqual([[{ ifRevision: 1 }, { a: R }], [{ ifRevision: 4 }, { b: R, a: R }]]);
    expect(readUnsent(path)).toBeNull();
    expect(qc.getQueryData(getFurnitureHeightsQueryKey({ path }))).toEqual({ heights: {}, pieceEdits: { b: R, a: R }, revision: 5, updatedAt: null });
    seen.length = 0;
    expect(await sendUnsent(path, { heights: { seat: 300 }, base: { revision: 5, heights: {} }, at: '' }, put, qc)).toBe(true);
    expect(seen).toEqual([[{ ifRevision: 5 }, undefined]]);
  });
});
