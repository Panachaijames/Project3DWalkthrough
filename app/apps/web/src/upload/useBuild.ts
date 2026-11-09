// A draft's BuildDetail on the Build page (docs/upload/DESIGN.md U-14.2, U-13.1 getBuild):
//  * the poll: getBuild with `withSettings: false` (settings: null, a small answer) every 1 s while a run of the build is
//    queued or running, and not at all otherwise;
//  * the full detail (with settings): read once (the page's loader), and again whenever the poll shows a settingsRevision
//    newer than the one held (saved elsewhere, or the proposal adopted when the prepare run finished).
// It also polls while the first prepare is done and its proposal not yet adopted (revision 0).
// The page reads one merged detail: the newer of the two answers for the run, the result and the sources, the full
// detail's settings. Answers of runBuild / cancelBuildRun / putBuildSettings go into both caches (setBuildDetail), which
// restarts the poll when they start a run.
import { useQuery, useQueryClient, type QueryClient } from '@tanstack/react-query';
import { useCallback, useEffect, useMemo } from 'react';
import { getBuildOptions, getBuildQueryKey } from '@/api/generated/@tanstack/react-query.gen';
import type { BuildDetail, RunInfo } from '@/upload/contracts';

export const POLL_MS = 1_000;

/** A run that still moves (the poll runs while there is one). */
export const isActive = (run: Pick<RunInfo, 'status'> | null | undefined): boolean => run?.status === 'queued' || run?.status === 'running';

/** Poll now: a run moves, or the first prepare is done and its proposal is not adopted yet (the API adopts it at the next
 *  request that sees the run done, U-3.3). */
export function shouldPoll(d: Pick<BuildDetail, 'run' | 'settingsRevision' | 'status'> | null | undefined): boolean {
  if (!d) return false;
  if (isActive(d.run)) return true;
  return d.status === 'open' && d.settingsRevision === 0 && d.run?.kind === 'prepare' && d.run.status === 'done';
}

export interface BuildPath { projectId: string; buildId: string }

export const fullKey = (path: BuildPath) => getBuildQueryKey({ path });
export const pollKey = (path: BuildPath) => getBuildQueryKey({ path, query: { withSettings: false } });

/** Puts a BuildDetail the API answered (with or without settings) into both caches. */
export function setBuildDetail(queryClient: QueryClient, path: BuildPath, detail: BuildDetail): void {
  queryClient.setQueryData(pollKey(path), { ...detail, settings: null });
  const full = queryClient.getQueryData<BuildDetail>(fullKey(path));
  if (detail.settings) {
    queryClient.setQueryData(fullKey(path), detail);
  } else if (full) {
    // keep the settings held (the poll's newer revision, if any, makes the page fetch them again)
    queryClient.setQueryData(fullKey(path), { ...detail, settings: full.settings, settingsRevision: full.settingsRevision });
  }
}

export interface UseBuild {
  /** The merged detail, or undefined before the first answer. */
  detail: BuildDetail | undefined;
  /** The run is queued or running (the poll is on). */
  active: boolean;
  error: unknown;
  /** The last poll failed while a detail is on screen (UR, V2-9: the page showed a frozen 'Building'), else null. */
  pollError: unknown;
  /** Puts an answer of the API (runBuild, cancelBuildRun ...) into the caches. */
  set(detail: BuildDetail): void;
  refetch(): void;
}

export function useBuild(projectId: string, buildId: string, opts: { pollMs?: number } = {}): UseBuild {
  const queryClient = useQueryClient();
  const path = useMemo(() => ({ projectId, buildId }), [projectId, buildId]);
  const pollMs = opts.pollMs ?? POLL_MS;
  const full = useQuery({ ...getBuildOptions({ path }), staleTime: Infinity });
  const poll = useQuery({
    ...getBuildOptions({ path, query: { withSettings: false } }),
    staleTime: 0,
    // the first answer comes from the full detail when the cache has it; polling only while a run moves
    enabled: !!full.data,
    refetchInterval: q => (shouldPoll((q.state.data as BuildDetail | undefined) ?? full.data) ? pollMs : false),
    refetchOnWindowFocus: true,
    // the next poll is the retry: a failed one shows at once (pollError) instead of after a second try
    retry: false,
  });

  // a newer settings revision seen in the poll: the full detail again
  const pollRevision = poll.data?.settingsRevision;
  const fullRevision = full.data?.settingsRevision;
  const refetchFull = full.refetch;
  useEffect(() => {
    if (pollRevision !== undefined && fullRevision !== undefined && pollRevision > fullRevision) void refetchFull();
  }, [pollRevision, fullRevision, refetchFull]);

  const detail = useMemo<BuildDetail | undefined>(() => {
    const f = full.data as BuildDetail | undefined;
    const p = poll.data as BuildDetail | undefined;
    if (!f) return p;
    if (!p || full.dataUpdatedAt >= poll.dataUpdatedAt) return f;
    // the run, the result and the sources from the poll; the settings (and the revision they are) from the full detail
    return { ...p, settings: f.settings, settingsRevision: f.settingsRevision };
  }, [full.data, poll.data, full.dataUpdatedAt, poll.dataUpdatedAt]);

  const set = useCallback((d: BuildDetail) => setBuildDetail(queryClient, path, d), [queryClient, path]);
  const fullRefetch = full.refetch;
  const pollRefetch = poll.refetch;
  const refetch = useCallback(() => { void fullRefetch(); void pollRefetch(); }, [fullRefetch, pollRefetch]);
  // the poll failed while the page holds a detail (the API stopped answering): the page says so, and keeps polling
  const pollError = poll.isError && detail !== undefined ? poll.error : null;
  return { detail, active: isActive(detail?.run), error: full.error ?? poll.error, pollError, set, refetch };
}
