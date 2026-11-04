// Saving the furniture heights typed in the viewer (DESIGN.md 15.5): every `heightschange` map goes to
// PUT .../furniture-heights after 600 ms of quiet, one request at a time, the newest map winning; on success the cached
// furniture heights and the version detail's overrides are updated; on an error the status shows the reason and Retry
// sends the newest map again. A pending save is flushed when the page unmounts, when the version changes (the hook's
// effect is keyed on projectId + version) and when the page is hidden or unloaded (keepalive request).
//
// Fix step (review findings "adversarial" 1, 3 and 4), on top of that:
//  * nothing typed is ever dropped without a word: the newest unsaved map is kept in this browser (lib/heightsOutbox.ts)
//    until the API has it; the next visit of the version starts from it and sends it, and versions not on screen are sent
//    from main.tsx (sendUnsent) when the app starts or the window comes back;
//  * a save that failed because the API did not answer (or failed on its side) is sent again by itself, after 2, 5, 10,
//    20, then every 30 s, and at once when the window comes back online or into focus; Retry still sends it now;
//  * two tabs (or two people) never erase each other's heights: every PUT says which saved revision it was typed over
//    (If-Match); when the heights were saved elsewhere since (412 revision_conflict), this tab's own changes are merged
//    into what is saved now, shown in the viewer (onRemote) and sent again; and heights saved elsewhere while this tab has
//    nothing unsaved are taken over (adopt), so the tab never says "Heights saved" over heights the API no longer has.
//
// createHeightsSaver is the framework-free core (unit-tested with fake timers); useHeightsSaver wires it into React.
import { useQueryClient, type QueryClient } from '@tanstack/react-query';
import type { HeightMap } from '@walkthrough/viewer';
import { useCallback, useEffect, useEffectEvent, useRef, useState } from 'react';
import {
  getFurnitureHeightsQueryKey,
  getVersionQueryKey,
  listProjectsQueryKey,
} from '../api/generated/@tanstack/react-query.gen';
import { putFurnitureHeights } from '../api/generated/sdk.gen';
import type { HeightOverrides, VersionDetail } from '../api/generated/types.gen';
import { conflictOf, isRetryable, isUnreachable } from '../api/client';
import { errorReason } from './format';
import {
  allUnsent, baseOf, mergeChanges, readUnsent, sameHeights, writeUnsent, type SavedBase, type UnsentEntry, type VersionKey,
} from './heightsOutbox';

export const SAVE_DEBOUNCE_MS = 600;
/** When a failed save is sent again by itself (ms after each failure; the last one repeats). */
export const RETRY_DELAYS_MS = [2_000, 5_000, 10_000, 20_000, 30_000];
/** A save that meets heights changed elsewhere this many times in a row stops and says so. */
const MAX_CONFLICTS = 5;

export type SaverStatus = 'saved' | 'saving' | 'error';
export interface SaverState {
  status: SaverStatus;
  /** Why the last save failed (status 'error'), else null. */
  reason: string | null;
  /** Status 'error' because the API did not answer at all (the downloads cannot work either). */
  unreachable?: boolean;
}
export const SAVED_STATE: SaverState = { status: 'saved', reason: null };

export interface SendInit {
  /** fetch keepalive: the request outlives the page (pagehide). */
  keepalive?: boolean;
  /** If-Match: the saved revision the map was typed over (set by the core). */
  ifRevision?: number;
}

export interface SaverDeps {
  put(heights: HeightMap, init: SendInit): Promise<HeightOverrides>;
  /** The saved heights the page started from (the version detail's overrides). Default: none saved (revision 0). */
  base?: SavedBase;
  /** A map typed before and never saved (the outbox): it is the tab's map from the start and goes out at once. */
  unsent?: UnsentEntry | null;
  /** After each successful save, with the API's answer. Also called after close() (the cache outlives the page). */
  onSaved?(result: HeightOverrides, sent: HeightMap): void;
  /** Every state change until close(). */
  onState?(state: SaverState): void;
  /** The tab's heights became these without the viewer typing them (a merge, heights saved elsewhere): show them. */
  onRemote?(heights: HeightMap): void;
  /** The newest unsaved map and its base, or null once the API has it (the outbox). Also called after close(). */
  onUnsent?(entry: UnsentEntry | null): void;
  debounceMs?: number;
  retryDelaysMs?: readonly number[];
}

export interface HeightsSaverCore {
  readonly state: SaverState;
  /** The saved revision and heights the tab's map is based on. */
  readonly base: SavedBase;
  /** A new map from the viewer: replaces any map not yet sent and (re)starts the debounce. */
  change(heights: HeightMap): void;
  /** Send the newest map now (after an error; also cuts a running debounce short). */
  retry(): void;
  /** A failed save that may go again by itself goes now (the window came back online or into focus). */
  retrySoon(): void;
  /**
   * Send the newest unsaved map now (debounced or failed; unmount, version change, pagehide). With a request in flight it
   * goes right after that one, with this init.
   */
  flush(init?: SendInit): void;
  /**
   * The saved heights as the API has them now (a refetch). Taken over (onRemote) when they were saved elsewhere and this
   * tab has nothing unsaved; ignored otherwise (this tab's next save meets them through If-Match and merges).
   */
  adopt(saved: Pick<HeightOverrides, 'revision' | 'heights'>): void;
  /** No more state callbacks or retries; requests already started (and a newest map queued behind them) still go out. */
  close(): void;
}

export function createHeightsSaver(deps: SaverDeps): HeightsSaverCore {
  const debounceMs = deps.debounceMs ?? SAVE_DEBOUNCE_MS;
  const retryDelays = deps.retryDelaysMs ?? RETRY_DELAYS_MS;
  let base: SavedBase = deps.unsent ? { ...deps.unsent.base } : deps.base ? { ...deps.base } : { revision: 0, heights: {} };
  let pending: HeightMap | null = null;  // the newest map not sent yet (or the one whose save failed)
  let unsaved: HeightMap | null = null;  // the newest map the API does not have yet (sent, waiting, or failed)
  let timer: ReturnType<typeof setTimeout> | null = null;
  let retryTimer: ReturnType<typeof setTimeout> | null = null;
  let retries = 0;
  let conflicts = 0;
  let inFlight = false;
  let failed: { reason: string; retryable: boolean; unreachable: boolean } | null = null;
  let closed = false;
  let queuedInit: SendInit = {};                     // for the map queued behind a request in flight (a flush's keepalive)
  let state: SaverState = SAVED_STATE;

  const compute = (): SaverState =>
    timer !== null || inFlight ? { status: 'saving', reason: null }
      : failed !== null ? { status: 'error', reason: failed.reason, ...(failed.unreachable ? { unreachable: true } : {}) }
        : SAVED_STATE;

  function emit() {
    const next = compute();
    if (next.status === state.status && next.reason === state.reason && !!next.unreachable === !!state.unreachable) return;
    state = next;
    if (!closed) deps.onState?.(state);
  }

  /** The outbox follows `unsaved` (also after close: a keepalive that lands removes the entry). */
  function keep() {
    deps.onUnsent?.(unsaved ? { heights: { ...unsaved }, base: { revision: base.revision, heights: { ...base.heights } }, at: new Date().toISOString() } : null);
  }

  function stopTimer() {
    if (timer !== null) { clearTimeout(timer); timer = null; }
  }
  function stopRetry() {
    if (retryTimer !== null) { clearTimeout(retryTimer); retryTimer = null; }
  }
  function scheduleRetry() {
    stopRetry();
    if (closed || !retryDelays.length) return;
    const delay = retryDelays[Math.min(retries, retryDelays.length - 1)]!;
    retries++;
    retryTimer = setTimeout(() => { retryTimer = null; if (failed?.retryable && !closed) send(); }, delay);
  }

  function send(init: SendInit = {}) {
    if (inFlight) {                                  // the completion sends the newest map
      if (init.keepalive) queuedInit = init;
      emit();
      return;
    }
    if (!pending) { emit(); return; }
    const heights = pending;
    pending = null;
    failed = null;
    stopRetry();
    inFlight = true;
    emit();
    let request: Promise<HeightOverrides>;
    try {
      request = deps.put(heights, { ...init, ifRevision: base.revision });
    } catch (err) {
      request = Promise.reject(err);
    }
    const next = () => { const i = queuedInit; queuedInit = {}; send(i); };
    request.then(
      result => {
        inFlight = false;
        base = baseOf(result);
        retries = 0;
        conflicts = 0;
        if (unsaved === heights) unsaved = null;     // a newer map (or a merge) is still unsaved otherwise
        deps.onSaved?.(result, heights);
        keep();
        if (pending && timer === null) next();      // a newer map came while this one was in flight
        else emit();
      },
      err => {
        inFlight = false;
        const now = conflictOf(err);
        if (now && conflicts < MAX_CONFLICTS) {      // saved elsewhere since: this tab's changes over what is saved now
          conflicts++;
          const mine = pending ?? heights;
          const merged = mergeChanges(base.heights, mine, now.heights);
          base = { revision: now.revision, heights: { ...now.heights } };
          pending = merged;
          unsaved = merged;
          stopTimer();
          deps.onRemote?.({ ...merged });
          keep();
          next();
          return;
        }
        if (pending) {                               // a newer map supersedes the one that failed
          if (timer === null) next(); else emit();
          return;
        }
        pending = heights;                           // kept for Retry (and for a flush)
        failed = { reason: errorReason(err), retryable: isRetryable(err), unreachable: isUnreachable(err) };
        keep();
        if (failed.retryable) scheduleRetry();
        emit();
      },
    );
  }

  if (deps.unsent) {                                 // typed before, never saved: the tab's map, sent at once
    pending = { ...deps.unsent.heights };
    unsaved = pending;
    send();
  }

  return {
    get state() { return state; },
    get base() { return { revision: base.revision, heights: { ...base.heights } }; },
    change(heights) {
      pending = { ...heights };
      unsaved = pending;
      failed = null;
      stopRetry();
      stopTimer();
      keep();
      if (closed) { send(); return; }               // after close: no debounce, straight out
      timer = setTimeout(() => { timer = null; send(); }, debounceMs);
      emit();
    },
    retry() {
      stopTimer();
      retries = 0;
      send();
    },
    retrySoon() {
      if (failed?.retryable && !inFlight && timer === null) send();
    },
    flush(init = {}) {
      stopTimer();
      if (pending) send(init);   // in flight: it goes right after the request in flight, with this init (keepalive)
      else emit();
    },
    adopt(saved) {
      // only newer heights: a refetch that started before this tab's own save can land after it with the revision before
      // (revisions only grow; a store reset by the seed's --reset-overrides meets this tab's next save as a 412 instead)
      if (saved.revision <= base.revision) return;
      if (unsaved || pending || inFlight || timer !== null) return;
      const was = base.heights;
      base = baseOf(saved);
      failed = null;
      if (!sameHeights(was, base.heights)) deps.onRemote?.({ ...base.heights });
      emit();
    },
    close() {
      closed = true;
      stopRetry();
    },
  };
}

// ------------------------------------------------------------------------------------------------------------ React hook

export type VersionPath = VersionKey;
export type PutHeights = (path: VersionPath, heights: HeightMap, init: SendInit) => Promise<HeightOverrides>;

/** The generated client's PUT (DESIGN.md 10.2), with If-Match: "<revision>" when the core gives one. */
export const putHeights: PutHeights = async (path, heights, init) => {
  const headers = init.ifRevision !== undefined ? { 'If-Match': `"${init.ifRevision}"` } : undefined;
  const { data } = await putFurnitureHeights({ path, body: { heights }, throwOnError: true, keepalive: init.keepalive, headers });
  return data;
};

/** After a save: the cached furniture heights and the version detail's overrides; the project list is now stale. */
export function updateHeightCaches(queryClient: QueryClient, path: VersionPath, result: HeightOverrides): void {
  queryClient.setQueryData<HeightOverrides>(getFurnitureHeightsQueryKey({ path }), result);
  queryClient.setQueryData<VersionDetail>(getVersionQueryKey({ path }), old => (old ? { ...old, overrides: result } : old));
  void queryClient.invalidateQueries({ queryKey: listProjectsQueryKey() });
}

/** The versions a mounted saver looks after (sendUnsent leaves them to it). */
const claimed = new Map<string, number>();
const claimKey = (p: VersionKey) => `${p.projectId}:${p.version}`;
export const isClaimed = (p: VersionKey) => (claimed.get(claimKey(p)) ?? 0) > 0;

export interface HeightsSaver {
  state: SaverState;
  /** Give it the viewer's heightschange maps (stable identity). */
  change: (heights: HeightMap) => void;
  /** Re-send the newest map (stable identity). */
  retry: () => void;
  /** Send a debounced map now, e.g. before a download that carries the saved heights (stable identity). */
  flush: () => void;
  /** The saved heights as the API has them now (a refetch): see HeightsSaverCore.adopt (stable identity). */
  adopt: (saved: Pick<HeightOverrides, 'revision' | 'heights'>) => void;
}

export interface HeightsSaverOptions {
  /** Tests: a stable put (a new one each render would restart the saver every render). */
  put?: PutHeights;
  debounceMs?: number;
  retryDelaysMs?: readonly number[];
  /** The saved heights the page shows (version detail overrides), read when the version's saver starts. */
  base?: Pick<HeightOverrides, 'revision' | 'heights'>;
  /** The tab's heights changed without the viewer typing them: the page shows them (viewer.setHeights). */
  onRemote?: (heights: HeightMap) => void;
}

/** The heights saver of one version. */
export function useHeightsSaver(projectId: string, version: number, opts: HeightsSaverOptions = {}): HeightsSaver {
  const queryClient = useQueryClient();
  const [state, setState] = useState<SaverState>(SAVED_STATE);
  const coreRef = useRef<HeightsSaverCore | null>(null);
  const put = opts.put ?? putHeights;
  const debounceMs = opts.debounceMs ?? SAVE_DEBOUNCE_MS;
  const retryDelaysMs = opts.retryDelaysMs ?? RETRY_DELAYS_MS;
  const remote = useEffectEvent((heights: HeightMap) => opts.onRemote?.(heights));
  const startBase = useEffectEvent((): SavedBase => (opts.base ? baseOf(opts.base) : { revision: 0, heights: {} }));

  useEffect(() => {
    const path: VersionPath = { projectId, version };
    const key = claimKey(path);
    claimed.set(key, (claimed.get(key) ?? 0) + 1);
    const core = createHeightsSaver({
      debounceMs,
      retryDelaysMs,
      base: startBase(),
      unsent: readUnsent(path),
      put: (heights, init) => put(path, heights, init),
      onSaved: result => updateHeightCaches(queryClient, path, result),
      onState: setState,
      onRemote: heights => remote(heights),
      onUnsent: entry => writeUnsent(path, entry),
    });
    coreRef.current = core;
    setState(core.state);
    const onPageHide = () => core.flush({ keepalive: true });
    const onBack = () => core.retrySoon();
    window.addEventListener('pagehide', onPageHide);
    window.addEventListener('online', onBack);
    window.addEventListener('focus', onBack);
    return () => {
      window.removeEventListener('pagehide', onPageHide);
      window.removeEventListener('online', onBack);
      window.removeEventListener('focus', onBack);
      core.flush({ keepalive: true });
      core.close();
      const n = (claimed.get(key) ?? 1) - 1;
      if (n > 0) claimed.set(key, n); else claimed.delete(key);
      if (coreRef.current === core) coreRef.current = null;
    };
  }, [projectId, version, queryClient, put, debounceMs, retryDelaysMs]);

  const change = useCallback((heights: HeightMap) => { coreRef.current?.change(heights); }, []);
  const retry = useCallback(() => { coreRef.current?.retry(); }, []);
  const flush = useCallback(() => { coreRef.current?.flush(); }, []);
  const adopt = useCallback((saved: Pick<HeightOverrides, 'revision' | 'heights'>) => { coreRef.current?.adopt(saved); }, []);
  return { state, change, retry, flush, adopt };
}

// ------------------------------------------------------------------------------------------------------- other versions

/**
 * Sends the unsaved map of a version that is not on screen (the outbox entry of a tab that left it, closed or reloaded
 * while the API did not answer), with If-Match and the same merge as the saver. Resolves true once the API has it (the
 * entry is then removed), false while it cannot (the entry stays for the next try).
 */
export async function sendUnsent(path: VersionKey, entry: UnsentEntry, put: PutHeights, queryClient: QueryClient): Promise<boolean> {
  let base = entry.base, heights = entry.heights;
  for (let i = 0; i < MAX_CONFLICTS; i++) {
    try {
      const result = await put(path, heights, { ifRevision: base.revision });
      if (!isClaimed(path)) writeUnsent(path, null);      // a saver that opened meanwhile keeps its own entry
      updateHeightCaches(queryClient, path, result);
      return true;
    } catch (err) {
      const now = conflictOf(err);
      if (!now) return false;
      heights = mergeChanges(base.heights, heights, now.heights);
      base = { revision: now.revision, heights: now.heights };
      if (!isClaimed(path)) writeUnsent(path, { heights, base, at: new Date().toISOString() });
    }
  }
  return false;
}

/**
 * Sends every unsaved map of a version not on screen (main.tsx): a little after start-up, whenever the window comes back
 * online or into focus, and every 30 s while there is one. Returns the stop function.
 */
export function startUnsentSender(queryClient: QueryClient, put: PutHeights = putHeights): () => void {
  let running = false;
  const run = async () => {
    if (running) return;
    running = true;
    try {
      for (const { path, entry } of allUnsent()) if (!isClaimed(path)) await sendUnsent(path, entry, put, queryClient);
    } finally {
      running = false;
    }
  };
  const go = () => { void run(); };
  const first = setTimeout(go, 1_000);
  const every = setInterval(go, 30_000);
  window.addEventListener('online', go);
  window.addEventListener('focus', go);
  return () => {
    clearTimeout(first);
    clearInterval(every);
    window.removeEventListener('online', go);
    window.removeEventListener('focus', go);
  };
}
