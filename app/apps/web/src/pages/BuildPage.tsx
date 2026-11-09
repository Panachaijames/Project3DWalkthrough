// /projects/:projectId/builds/:buildId (docs/upload/DESIGN.md U-2 screen 5, U-14.1): a draft's Build page with its step
// bar, Files . Layers . Floors . Build . Check . Save (`?step=`; a step is reachable once its inputs exist). The loader
// reads the build with its settings (getBuild; a 404 shows Not found) and the project; the page then polls the build
// every 1 s while a run is queued or running (useBuild, `withSettings: false`) and saves the settings as staff change
// them (useSettingsSaver: 800 ms debounce, If-Match). A saved draft is read-only ("saved as v<n>" with a link). Leaving and
// coming back resumes where it was: everything is on the server. Title `<name> · draft · Walkthrough`.
import { useQuery, type QueryClient } from '@tanstack/react-query';
import { CircleAlert, RotateCw } from 'lucide-react';
import { useCallback, useMemo } from 'react';
import { Link, useLoaderData, useSearchParams, type LoaderFunctionArgs } from 'react-router';
import { AppBar } from '@/components/AppBar';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { getBuildOptions, getProjectOptions } from '@/api/generated/@tanstack/react-query.gen';
import { BuildContextProvider, type BuildContextValue } from '@/build/context';
import { BuildStep } from '@/build/BuildStep';
import { CheckStep } from '@/build/CheckStep';
import { FilesStep } from '@/build/FilesStep';
import { FloorsStep } from '@/build/FloorsStep';
import { LayersStep } from '@/build/LayersStep';
import { SaveStep } from '@/build/SaveStep';
import { StepBar } from '@/build/StepBar';
import { isStep, reachable, rereadText, STEP_LABELS, type StepId } from '@/build/steps';
import { APP_NAME, errorReason } from '@/lib/format';
import { checkProjectId, fetchOrCached, loadOr404, notFound } from '@/lib/routeData';
import { useDocumentTitle } from '@/lib/useDocumentTitle';
import type { BuildDetail } from '@/upload/contracts';
import { useSettingsSaver, type SettingsSaverState } from '@/upload/settingsSaver';
import { timing } from '@/upload/timing';
import { useBuild } from '@/upload/useBuild';

/** ^[0-9]{8}T[0-9]{6}-[0-9a-f]{6}$ (U-13.1). */
export const BUILD_ID = /^[0-9]{8}T[0-9]{6}-[0-9a-f]{6}$/;
export const draftTitle = (name: string) => `${name} · draft · ${APP_NAME}`;

export interface BuildPageData { projectId: string; buildId: string }

export function buildLoader(queryClient: QueryClient) {
  return async ({ params }: LoaderFunctionArgs): Promise<BuildPageData> => {
    const projectId = checkProjectId(params.projectId);
    const buildId = params.buildId ?? '';
    if (!BUILD_ID.test(buildId)) notFound(`There is no draft called ${JSON.stringify(buildId)}.`);
    const path = { projectId, buildId };
    await loadOr404(() => Promise.all([
      fetchOrCached(queryClient, { ...getBuildOptions({ path }), staleTime: 0 }),
      fetchOrCached(queryClient, getProjectOptions({ path: { projectId } })),
    ]));
    return { projectId, buildId };
  };
}

function SettingsStatus({ state, onRetry }: { state: SettingsSaverState | null; onRetry: () => void }) {
  if (!state) return null;
  const text = state.status === 'saving' || state.status === 'pending' ? 'Saving...' : state.status === 'error' ? `Not saved: ${state.error}` : 'Saved';
  return (
    <div className="flex max-w-md items-center gap-2 text-xs" data-testid="settings-status" data-status={state.status}>
      <span className={state.status === 'error' ? 'truncate text-destructive' : 'text-muted-foreground'} title={text}>{text}</span>
      {state.status === 'error' && (
        <Button size="sm" variant="outline" className="h-7" onClick={onRetry} data-testid="settings-retry">
          <RotateCw aria-hidden="true" />
          Retry
        </Button>
      )}
    </div>
  );
}

function StepBody({ step }: { step: StepId }) {
  switch (step) {
    case 'files': return <FilesStep />;
    case 'layers': return <LayersStep />;
    case 'floors': return <FloorsStep />;
    case 'build': return <BuildStep />;
    case 'check': return <CheckStep />;
    case 'save': return <SaveStep />;
  }
}

export function BuildPage() {
  const { projectId, buildId } = useLoaderData<BuildPageData>();
  const [params, setParams] = useSearchParams();
  const build = useBuild(projectId, buildId, { pollMs: timing.pollMs });
  const project = useQuery(getProjectOptions({ path: { projectId } }));
  const detail = build.detail;
  const saverHook = useSettingsSaver(projectId, buildId, detail, { debounceMs: timing.settingsDebounceMs });
  const name = project.data?.name ?? projectId;
  useDocumentTitle(draftTitle(name));

  const wanted = params.get('step');
  const step: StepId = isStep(wanted) ? wanted : 'files';
  const goto = useCallback((s: StepId) => {
    setParams(p => { const n = new URLSearchParams(p); n.set('step', s); return n; });
    window.scrollTo?.({ top: 0 });
  }, [setParams]);

  const settings = saverHook.state?.settings ?? detail?.settings ?? null;
  const lock = detail ? rereadText(detail, settings) : null;
  const editable = !!saverHook.saver && detail?.status === 'open' && !lock;
  const value = useMemo<BuildContextValue | null>(() => (detail ? {
    projectId, buildId, detail, project: project.data ?? null, settings,
    saver: saverHook.saver, saverState: saverHook.state,
    change: (fn, o) => { if (editable) saverHook.change(fn, o); },
    editable,
    setDetail: (d: BuildDetail) => build.set(d),
    refresh: build.refetch,
    goto,
  } : null), [detail, project.data, settings, saverHook.saver, saverHook.state, saverHook.change, editable, build.set, build.refetch, goto, projectId, buildId]);   // eslint-disable-line react-hooks/exhaustive-deps

  if (!detail || !value) {
    return (
      <div className="min-h-svh bg-muted/30">
        <AppBar back title={`${name} · draft`} className="sticky top-0" />
        <main className="mx-auto max-w-2xl px-6 py-16">
          {build.error ? (
            <Alert variant="destructive" data-testid="build-load-error">
              <CircleAlert aria-hidden="true" />
              <AlertTitle>This draft could not be loaded</AlertTitle>
              <AlertDescription>
                <p>{errorReason(build.error)}</p>
                <Button size="sm" variant="outline" className="mt-2" onClick={build.refetch}>Retry</Button>
              </AlertDescription>
            </Alert>
          ) : <p className="text-sm text-muted-foreground">Opening the draft...</p>}
        </main>
      </div>
    );
  }

  const open = reachable(step, detail);
  return (
    <BuildContextProvider value={value}>
      <div className="min-h-svh bg-muted/30" data-testid="build-page" data-build-id={buildId} data-step={step} data-revision={detail.settingsRevision} data-status={detail.status}>
        <AppBar back title={<span><span data-testid="build-project-name">{name}</span>{' · draft'}</span>} className="sticky top-0">
          <SettingsStatus state={saverHook.state} onRetry={() => saverHook.saver?.retry()} />
        </AppBar>
        <main className="mx-auto grid w-full max-w-[1600px] gap-4 px-6 py-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <StepBar detail={detail} current={step} onStep={goto} />
            <p className="truncate text-xs text-muted-foreground" data-testid="build-files">{detail.sourceNames.join(', ')}</p>
          </div>
          {build.pollError !== null && build.pollError !== undefined && (
            <Alert variant="destructive" data-testid="api-not-answering">
              <CircleAlert aria-hidden="true" />
              <AlertDescription>
                {`The API is not answering (${errorReason(build.pollError)}): what you see may be out of date. Trying again every second...`}
              </AlertDescription>
            </Alert>
          )}
          {detail.status === 'saved' && detail.savedVersion !== null && (
            <Alert data-testid="build-saved">
              <AlertDescription>
                <span>{`This draft was saved as v${detail.savedVersion}; it is read-only. `}</span>
                <Link className="underline" to={`/projects/${projectId}/v/${detail.savedVersion}`}>{`Open v${detail.savedVersion}`}</Link>
              </AlertDescription>
            </Alert>
          )}
          {saverHook.state && saverHook.state.issues.length > 0 && (
            <Alert variant="destructive" data-testid="settings-issues">
              <AlertTitle>The settings were not saved</AlertTitle>
              <AlertDescription>
                <ul className="list-disc pl-4">{saverHook.state.issues.map((i, n) => <li key={n}>{`${i.path ? `${i.path}: ` : ''}${i.message}`}</li>)}</ul>
              </AlertDescription>
            </Alert>
          )}
          {open ? <StepBody step={step} /> : (
            <p className="text-sm text-muted-foreground" data-testid="step-not-open">
              {`${STEP_LABELS[step]} opens ${step === 'check' || step === 'save' ? 'once the draft is built' : 'once the drawings are read'}.`}
            </p>
          )}
        </main>
      </div>
    </BuildContextProvider>
  );
}
