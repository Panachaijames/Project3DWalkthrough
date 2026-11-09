// Saving a draft's settings (docs/upload/DESIGN.md U-14.2, U-8.3, U-12.3, U-13.1): every change from the steps goes to
// PUT .../builds/<id>/settings after 800 ms of quiet, one request at a time, with `If-Match: "<revision>"` (the revision
// the change was made over).
//  * A change is a FUNCTION of the settings (set this layer's role, add this set-aside ...), kept until the API has it, so
//    that a 412 revision_conflict (the settings were saved elsewhere since: the answer carries the saved revision and
//    settings) is met by taking the saved settings and applying this tab's changes again on top, then sending again.
//  * The Layers step's saves carry `layersReviewed: true` (U-8.3): once set, the flag rides on the next PUT, also as an
//    otherwise unchanged save (markReviewed), until the API has taken it.
//  * 413 (body_too_large: too many items set aside at once) can never be sent as it is: those changes are dropped and the
//    status says "too many items set aside at once: set aside whole blocks instead" (U-12.3).
//  * 422 invalid_settings: the status shows the API's issues; the changes stay on screen and go again with the next change.
//  * Anything else (the API down, 409 not_prepared / run_in_progress / build_saved): the status says why; the changes
//    stay and Retry sends them.
// createSettingsSaver is the framework-free core (unit-tested with fake timers); useSettingsSaver wires it into React
// and into the build's query cache.
import { useQueryClient } from '@tanstack/react-query';
import { useCallback, useEffect, useRef, useState, useSyncExternalStore } from 'react';
import { ApiError } from '@/api/client';
import { getBuildQueryKey } from '@/api/generated/@tanstack/react-query.gen';
import { putBuildSettings } from '@/api/generated/sdk.gen';
import type { BuildDetail, BuildSettings } from '@/upload/contracts';
import { errorReason } from '@/lib/format';

export const SETTINGS_DEBOUNCE_MS = 800;
/** A save that meets settings changed elsewhere this many times in a row stops and says so. */
const MAX_CONFLICTS = 5;
export const TOO_MANY_SET_ASIDE = 'too many items set aside at once: set aside whole blocks instead';

export type SettingsChange = (s: BuildSettings) => BuildSettings;
export type SettingsSaverStatus = 'saved' | 'pending' | 'saving' | 'error';

export interface SettingsIssue { path: string; message: string }

export interface SettingsSaverState {
  /** The settings as this tab has them: the saved ones with the changes not yet saved applied. */
  settings: BuildSettings;
  /** The saved revision they rest on. */
  revision: number;
  status: SettingsSaverStatus;
  /** Why the last save failed (status 'error'). */
  error: string | null;
  /** invalid_settings: the API's issues. */
  issues: SettingsIssue[];
  /** A Layers-step review that the API has not taken yet. */
  reviewPending: boolean;
}

export interface SettingsSaverDeps {
  /** The PUT (If-Match: revision). */
  put(settings: BuildSettings, revision: number, layersReviewed: boolean): Promise<BuildDetail>;
  base: { settings: BuildSettings; revision: number };
  debounceMs?: number;
  /** After each successful save, with the API's answer. */
  onSaved?(detail: BuildDetail): void;
}

export interface SettingsSaver {
  readonly state: SettingsSaverState;
  /** Applies a change now (on screen) and saves it after the debounce. */
  change(fn: SettingsChange, opts?: { layersReviewed?: boolean }): void;
  /** The Layers step was seen: send `layersReviewed: true`, with no change if there is none. */
  markReviewed(): void;
  /** Sends what waits now (no debounce). */
  flush(): void;
  /** After an error: sends the changes again. */
  retry(): void;
  /** Settings saved elsewhere (a newer revision read from the API): the base, with this tab's changes on top. */
  rebase(settings: BuildSettings, revision: number): void;
  subscribe(listener: () => void): () => void;
  /** Stops the timers; a change still waiting is sent first (flush). */
  close(): void;
}

const apply = (fns: readonly SettingsChange[], s: BuildSettings) => fns.reduce((acc, fn) => fn(acc), s);

function conflictDetails(err: unknown): { revision: number; settings: BuildSettings } | null {
  if (!(err instanceof ApiError) || err.status !== 412 || !err.details) return null;
  const { revision, settings } = err.details as { revision?: unknown; settings?: unknown };
  if (typeof revision !== 'number' || !settings || typeof settings !== 'object') return null;
  return { revision, settings: settings as BuildSettings };
}

function issuesOf(err: unknown): SettingsIssue[] {
  if (!(err instanceof ApiError) || !err.details) return [];
  const issues = (err.details as { issues?: unknown }).issues;
  if (!Array.isArray(issues)) return [];
  return issues.map(i => {
    const it = i as { path?: unknown; message?: unknown };
    return { path: typeof it.path === 'string' ? it.path : '', message: typeof it.message === 'string' ? it.message : String(i) };
  });
}

export function createSettingsSaver(deps: SettingsSaverDeps): SettingsSaver {
  const debounceMs = deps.debounceMs ?? SETTINGS_DEBOUNCE_MS;
  let base = { ...deps.base };
  let pending: SettingsChange[] = [];
  let inflight: SettingsChange[] | null = null;
  let reviewWanted = false;
  let reviewInFlight = false;
  let timer: ReturnType<typeof setTimeout> | null = null;
  let error: string | null = null;
  let issues: SettingsIssue[] = [];
  let conflicts = 0;
  let closed = false;
  const listeners = new Set<() => void>();
  let state: SettingsSaverState = snapshot();

  function snapshot(): SettingsSaverState {
    const status: SettingsSaverStatus = inflight ? 'saving' : error ? 'error' : pending.length || timer || reviewWanted ? 'pending' : 'saved';
    return {
      settings: apply([...(inflight ?? []), ...pending], base.settings),
      revision: base.revision,
      status,
      error: inflight ? null : error,
      issues: inflight ? [] : issues,
      reviewPending: reviewWanted || reviewInFlight,
    };
  }
  function emit() {
    state = snapshot();
    for (const l of [...listeners]) l();
  }
  function schedule() {
    if (closed) return;
    if (timer) clearTimeout(timer);
    timer = setTimeout(() => { timer = null; send(); }, debounceMs);
  }

  function send(): void {
    if (inflight) return;                                   // one at a time: the next goes when this one is answered
    if (timer) { clearTimeout(timer); timer = null; }
    if (!pending.length && !reviewWanted) { emit(); return; }
    inflight = pending;
    pending = [];
    reviewInFlight = reviewWanted;
    reviewWanted = false;
    const sending = apply(inflight, base.settings);
    const carried = reviewInFlight;
    error = null;
    issues = [];
    emit();
    deps.put(sending, base.revision, carried).then(
      detail => {
        base = { settings: detail.settings ?? sending, revision: detail.settingsRevision };
        inflight = null;
        reviewInFlight = false;
        conflicts = 0;
        deps.onSaved?.(detail);
        if (pending.length || reviewWanted) schedule();
        emit();
      },
      err => {
        const changes = inflight ?? [];
        inflight = null;
        const conflict = conflictDetails(err);
        if (conflict && conflicts < MAX_CONFLICTS) {
          conflicts++;
          base = conflict;
          pending = [...changes, ...pending];
          reviewWanted = reviewWanted || reviewInFlight;
          reviewInFlight = false;
          send();                                           // at once: the change was waited for already
          return;
        }
        conflicts = 0;
        if (err instanceof ApiError && err.status === 413) {
          // never sendable as it is: dropped (the screen goes back to what is saved)
          error = TOO_MANY_SET_ASIDE;
          issues = [];
          reviewWanted = reviewWanted || reviewInFlight;
        } else {
          pending = [...changes, ...pending];
          reviewWanted = reviewWanted || reviewInFlight;
          error = conflict ? 'the settings keep changing elsewhere: reload the page' : errorReason(err);
          issues = issuesOf(err);
        }
        reviewInFlight = false;
        emit();
      },
    );
  }

  return {
    get state() { return state; },
    change(fn, opts) {
      if (closed) return;
      pending.push(fn);
      if (opts?.layersReviewed) reviewWanted = true;
      schedule();
      emit();
    },
    markReviewed() {
      if (closed || reviewWanted || reviewInFlight) return;
      reviewWanted = true;
      schedule();
      emit();
    },
    flush() { send(); },
    retry() { error = null; send(); },
    rebase(settings, revision) {
      if (revision <= base.revision) return;
      base = { settings, revision };
      emit();
    },
    subscribe(listener) {
      listeners.add(listener);
      return () => { listeners.delete(listener); };
    },
    close() {
      if (closed) return;
      if (timer || pending.length || reviewWanted) send();
      closed = true;
      if (timer) { clearTimeout(timer); timer = null; }
      listeners.clear();
    },
  };
}

/** The generated client's PUT, with If-Match: "<revision>" (U-13.1). */
export async function putSettings(projectId: string, buildId: string, settings: BuildSettings, revision: number,
  layersReviewed: boolean): Promise<BuildDetail> {
  const { data } = await putBuildSettings({
    path: { projectId, buildId },
    body: layersReviewed ? { settings, layersReviewed: true } : { settings },
    headers: { 'If-Match': `"${revision}"` },
    throwOnError: true,
  });
  return data as BuildDetail;
}

export interface UseSettingsSaver {
  /** null until the proposal is in (revision 0 settings cannot be saved, U-3.3). */
  saver: SettingsSaver | null;
  state: SettingsSaverState | null;
  change: (fn: SettingsChange, opts?: { layersReviewed?: boolean }) => void;
}

const NO_STATE = () => null;
const noSubscribe = () => () => undefined;

/**
 * The saver of one draft, made once the full detail (with settings at revision >= 1) is known. Saved answers go into the
 * build's query cache (the full detail and the 1 s poll alike), a newer revision read from the API is taken over
 * (rebase), and leaving the page sends a change still waiting.
 */
export function useSettingsSaver(projectId: string, buildId: string, detail: BuildDetail | null | undefined,
  opts: { put?: SettingsSaverDeps['put']; debounceMs?: number } = {}): UseSettingsSaver {
  const queryClient = useQueryClient();
  const ref = useRef<SettingsSaver | null>(null);
  const [saver, setSaver] = useState<SettingsSaver | null>(null);
  const ready = !!detail?.settings && detail.settingsRevision >= 1 && detail.status === 'open';
  const putRef = useRef(opts.put);
  putRef.current = opts.put;

  useEffect(() => {
    if (!ready || ref.current || !detail?.settings) return;
    const path = { projectId, buildId };
    const s = createSettingsSaver({
      base: { settings: detail.settings, revision: detail.settingsRevision },
      debounceMs: opts.debounceMs,
      put: (settings, revision, reviewed) => (putRef.current ?? ((a, b, c) => putSettings(projectId, buildId, a, b, c)))(settings, revision, reviewed),
      onSaved: saved => {
        queryClient.setQueryData(getBuildQueryKey({ path }), saved);
        queryClient.setQueryData(getBuildQueryKey({ path, query: { withSettings: false } }), { ...saved, settings: null });
      },
    });
    ref.current = s;
    setSaver(s);
  }, [ready, projectId, buildId]);   // eslint-style deps kept small on purpose: one saver per draft

  // settings saved elsewhere (another tab): taken over, this tab's changes on top
  useEffect(() => {
    if (saver && detail?.settings) saver.rebase(detail.settings, detail.settingsRevision);
  }, [saver, detail?.settings, detail?.settingsRevision]);

  useEffect(() => () => { ref.current?.close(); ref.current = null; }, []);

  const state = useSyncExternalStore(
    saver ? saver.subscribe : noSubscribe,
    saver ? () => saver.state : NO_STATE,
    saver ? () => saver.state : NO_STATE,
  );
  const change = useCallback((fn: SettingsChange, o?: { layersReviewed?: boolean }) => { saver?.change(fn, o); }, [saver]);
  return { saver, state, change };
}
