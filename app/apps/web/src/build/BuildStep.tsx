// Step "Build" (docs/upload/DESIGN.md U-2 5d, U-3.4, U-12.5, U-14.3): the pre-build checklist; Build (runBuild) once it is
// clear; the run's steps with their status and seconds, a progress bar, the last messages ("Stopping..." after Cancel);
// when done: counts per floor, the flags, the top view and a 3D preview (the viewer on the draft, disposed when closed);
// a failed run shows its error and what to change.
import { useQueries, useQuery } from '@tanstack/react-query';
import type { Viewer } from '@walkthrough/viewer';
import { Box, Download, Hammer, X } from 'lucide-react';
import { useMemo, useState } from 'react';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { ViewerHost } from '@/components/ViewerHost';
import { ApiError, apiUrl } from '@/api/client';
import { cancelBuildRun, runBuild } from '@/api/generated/sdk.gen';
import type { BuildDetail, BuildResultInfo, DrawingRead } from '@/upload/contracts';
import { draftViewerOptions, toDraftViewerProject } from '@/upload/draftViewerProject';
import { rawQueryOptions } from '@/upload/raw';
import { errorReason, formatNumber } from '@/lib/format';
import { sourceToken, useBuildContext } from './context';
import { PreBuildChecklist } from './PreBuildChecklist';
import { RunPanel } from './RunPanel';
import { checklist } from './steps';

/** The result's counts per floor (U-2 5d). */
export function ResultTable({ result }: { result: BuildResultInfo }) {
  return (
    <table className="w-full text-sm" data-testid="result-floors">
      <thead className="text-left text-xs text-muted-foreground">
        <tr><th className="font-medium">Floor</th><th className="font-medium">Level</th><th className="font-medium">Parts</th><th className="font-medium">Doors</th><th className="font-medium">Windows</th><th className="font-medium">Passages</th><th className="font-medium">Furniture</th><th className="font-medium">Rooms</th></tr>
      </thead>
      <tbody>
        {result.floors.map(f => (
          <tr key={f.key} className="border-t" data-testid="result-floor" data-key={f.key}>
            <td>{f.name}</td>
            <td className="tabular-nums">{f.level.toFixed(2)}</td>
            <td className="tabular-nums" data-testid="result-parts">{formatNumber(f.parts)}</td>
            <td className="tabular-nums">{f.openings.door}</td>
            <td className="tabular-nums">{f.openings.window}</td>
            <td className="tabular-nums">{f.openings.passage}</td>
            <td className="tabular-nums">{f.furniture}</td>
            <td className="tabular-nums">{f.rooms}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

/** The 3D preview of the draft (U-12.5): the viewer on the draft's model, stages and presentation; heights not saved. */
export function DraftPreview({ detail, onClose }: { detail: BuildDetail; onClose: () => void }) {
  const result = detail.result!;
  const model = useQuery(rawQueryOptions<unknown>(result.urls.model, result.runId));
  const stages = useQuery(rawQueryOptions<unknown>(result.urls.stages, result.runId));
  const options = useMemo(() => draftViewerOptions(), []);
  const [failure, setFailure] = useState<unknown>(null);
  const built = useMemo(() => {
    if (model.data === undefined || stages.isPending) return null;
    try {
      return { ok: true as const, project: toDraftViewerProject(detail, model.data, stages.data ?? null) };
    } catch (error) {
      return { ok: false as const, error };
    }
    // the project is made once per run (the draft's result)
  }, [model.data, stages.data, stages.isPending, result.runId]);   // eslint-disable-line react-hooks/exhaustive-deps
  return (
    <div className="fixed inset-x-0 top-12 bottom-0 z-30 bg-[#eef0f2]" data-testid="draft-preview">
      <div className="absolute top-2 left-2 z-40 flex items-center gap-2 rounded-md bg-background/90 px-2 py-1 text-sm shadow">
        <span className="font-medium">3D preview of the draft</span>
        <span className="text-xs text-muted-foreground">Heights typed here are not saved.</span>
        <Button size="sm" variant="outline" onClick={onClose} data-testid="close-preview">
          <X aria-hidden="true" />
          Close
        </Button>
      </div>
      {built?.ok && !failure && (
        <ViewerHost project={built.project} options={options} onError={setFailure} onCreated={(_v: Viewer) => setFailure(null)} />
      )}
      {(model.isError || (built !== null && !built.ok) || !!failure) && (
        <div className="flex size-full items-center justify-center p-6">
          <Alert variant="destructive" className="max-w-lg bg-background" data-testid="preview-error">
            <AlertTitle>The preview could not start</AlertTitle>
            <AlertDescription>{errorReason(model.error ?? (built && !built.ok ? built.error : failure))}</AlertDescription>
          </Alert>
        </div>
      )}
      {!built && !model.isError && <p className="p-6 text-sm text-muted-foreground">Loading the draft model...</p>}
    </div>
  );
}

/** A run another tab (or the API's own restart marking) started: the answer to runBuild's 409 run_in_progress. The page
 *  reads the build again so the running build shows and is polled (UR, V2-14: the tab kept its old 'done' panel). */
export const STARTED_ELSEWHERE = 'A run of this draft is going already (started in another tab or window): it is shown below.';

export function isRunInProgress(err: unknown): boolean {
  return err instanceof ApiError && err.status === 409 && err.code === 'run_in_progress';
}

export function BuildStep() {
  const { detail, settings, saverState, setDetail, refresh, goto, projectId, buildId } = useBuildContext();
  const [busy, setBusy] = useState<'run' | 'cancel' | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [preview, setPreview] = useState(false);
  const drawings = useQueries({ queries: detail.sources.map(s => rawQueryOptions<DrawingRead>(s.urls?.drawing, sourceToken(s))) });
  const votes = Object.fromEntries(detail.sources.map((s, i) => [s.sha1, drawings[i]?.data?.units.votes]));
  const items = checklist(detail, settings, { reviewPending: saverState?.reviewPending, votes });
  const blocked = items.some(i => i.level === 'block');
  const run = detail.run;
  const active = run && (run.status === 'queued' || run.status === 'running');
  const result = detail.result;
  const saved = detail.status === 'saved';
  const savingSettings = saverState?.status === 'saving' || saverState?.status === 'pending';

  const start = async () => {
    setBusy('run');
    setError(null);
    try {
      const { data } = await runBuild({ path: { projectId, buildId }, body: {}, throwOnError: true });
      setDetail(data as BuildDetail);
    } catch (err) {
      if (isRunInProgress(err)) {
        refresh();
        setError(STARTED_ELSEWHERE);
      } else {
        setError(errorReason(err));
      }
    } finally {
      setBusy(null);
    }
  };
  const cancel = async () => {
    setBusy('cancel');
    try {
      const { data } = await cancelBuildRun({ path: { projectId, buildId }, body: {}, throwOnError: true });
      setDetail(data as BuildDetail);
    } catch (err) {
      setError(errorReason(err));
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="grid gap-4 xl:grid-cols-[minmax(0,2fr)_minmax(0,3fr)]" data-testid="build-step">
      <section className="grid content-start gap-3">
        {!saved && <PreBuildChecklist items={items} onStep={goto} />}
        {!saved && (
          <div className="flex flex-wrap items-center gap-3">
            <Button disabled={blocked || !!active || busy !== null || savingSettings} onClick={() => void start()} data-testid="run-build">
              <Hammer aria-hidden="true" />
              {result ? 'Build again' : 'Build'}
            </Button>
            {savingSettings && <span className="text-xs text-muted-foreground">Saving the settings first...</span>}
          </div>
        )}
        {error && (
          <Alert variant="destructive" data-testid="build-error"><AlertDescription>{error}</AlertDescription></Alert>
        )}
        {run && <RunPanel run={run} onCancel={run.kind === 'build' && !saved ? () => void cancel() : null} cancelling={busy === 'cancel'} />}
      </section>

      <section className="grid content-start gap-3">
        {result ? (
          <div className="grid gap-3 rounded-lg border bg-background p-4" data-testid="build-result" data-run={result.runId}>
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h3 className="text-sm font-semibold">The draft as last built</h3>
              <div className="flex flex-wrap gap-2">
                <Button size="sm" variant="outline" onClick={() => setPreview(true)} data-testid="open-preview">
                  <Box aria-hidden="true" />
                  3D preview
                </Button>
                <Button size="sm" variant="outline" asChild>
                  <a href={apiUrl(result.urls.maxScript)} download data-testid="draft-max-script">
                    <Download aria-hidden="true" />
                    Draft 3ds Max script
                  </a>
                </Button>
              </div>
            </div>
            {result.stale && (
              <p className="text-sm text-amber-700" data-testid="result-stale">The settings changed since this build: build again before saving.</p>
            )}
            <p className="text-sm" data-testid="result-counts">
              {`${formatNumber(result.counts.parts)} parts, ${formatNumber(result.counts.openings)} openings, ${formatNumber(result.counts.furniture)} furniture pieces, ${formatNumber(result.counts.rooms)} rooms`}
            </p>
            <p className="text-sm" data-testid="result-flags" data-total={result.flags.total} data-check={result.flags.check}>
              {result.flags.total ? `${formatNumber(result.flags.total)} flags, ${formatNumber(result.flags.check)} to check on the Check step` : 'No flags'}
            </p>
            <ResultTable result={result} />
            <img src={apiUrl(result.urls.topview)} alt="Top view of the draft" className="w-full rounded border bg-white" data-testid="result-topview" key={result.runId} />
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">Nothing built yet.</p>
        )}
      </section>
      {preview && result && <DraftPreview detail={detail} onClose={() => setPreview(false)} />}
    </div>
  );
}
