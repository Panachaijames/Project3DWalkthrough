// /projects/:projectId/v/:n (DESIGN.md 15.1, 15.3): the 48 px app bar (back to the projects, the project's name, New version
// and the Drafts menu of docs/upload/DESIGN.md U-2 screen 3, the version picker, the Downloads menu, the heights status) and
// the viewer filling the window below it.
// The loader reads the project (its versions for the picker), the version detail, then the model and (with a replay) the
// stages. The ViewerProject is memoised on (projectId, version, stamp), the options on the address: a heights save (which
// updates the cached version detail) never re-creates the viewer; a version change does, disposing the old one first.
import { useQuery, type QueryClient } from '@tanstack/react-query';
import type { Viewer, ViewerProject } from '@walkthrough/viewer';
import { CircleAlert, RotateCw } from 'lucide-react';
import { useEffect, useMemo, useRef, useState } from 'react';
import { useLoaderData, useLocation, type LoaderFunctionArgs } from 'react-router';
import { AppBar } from '@/components/AppBar';
import { DownloadsMenu } from '@/components/DownloadsMenu';
import { DraftsMenu, NewVersionButton } from '@/components/DraftsMenu';
import { HeightsStatus } from '@/components/HeightsStatus';
import { VersionPicker } from '@/components/VersionPicker';
import { ViewerHost } from '@/components/ViewerHost';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import {
  getFurnitureHeightsOptions,
  getModelOptions,
  getProjectOptions,
  getStagesOptions,
  getVersionOptions,
} from '@/api/generated/@tanstack/react-query.gen';
import type { ProjectDetail, VersionDetail } from '@/api/generated/types.gen';
import { errorReason, versionTitle } from '@/lib/format';
import { readUnsent } from '@/lib/heightsOutbox';
import { checkProjectId, checkVersion, fetchOrCached, loadOr404 } from '@/lib/routeData';
import { useDocumentTitle } from '@/lib/useDocumentTitle';
import { useHeightsSaver } from '@/lib/useHeightsSaver';
import { buildViewerProject, issueLines, viewerOptions } from '@/lib/viewerProject';

export interface VersionPageData {
  project: ProjectDetail;
  detail: VersionDetail;
  /** model.json as the API sent it (parsed by the viewer's parseBuiltModel on the page). */
  model: unknown;
  /** stages.json, or null when the version has no replay. */
  stages: unknown;
}

export function versionLoader(queryClient: QueryClient) {
  return async ({ params }: LoaderFunctionArgs): Promise<VersionPageData> => {
    const projectId = checkProjectId(params.projectId);
    const version = checkVersion(params.n);
    const path = { projectId, version };
    // the cached data when only a refresh fails because the API does not answer (fetchOrCached): the version stays
    const [project, detail] = await loadOr404(() => Promise.all([
      fetchOrCached(queryClient, getProjectOptions({ path: { projectId } })),
      fetchOrCached(queryClient, getVersionOptions({ path })),
    ]));
    // A version's files never change (a fix is a new version, DESIGN.md 9.5): cached, never stale.
    const [model, stages] = await loadOr404(() => Promise.all([
      queryClient.ensureQueryData({ ...getModelOptions({ path }), staleTime: Infinity }),
      detail.hasStages ? queryClient.ensureQueryData({ ...getStagesOptions({ path }), staleTime: Infinity }) : Promise.resolve(null),
    ]));
    return { project, detail, model, stages };
  };
}

function ViewerFailed({ error, onRetry }: { error: unknown; onRetry: () => void }) {
  return (
    <div className="absolute inset-0 z-10 flex items-center justify-center bg-[#eef0f2]/80 p-6">
      <Alert variant="destructive" className="max-w-lg bg-background" data-testid="viewer-error">
        <CircleAlert aria-hidden="true" />
        <AlertTitle>The viewer could not start</AlertTitle>
        <AlertDescription>
          <p data-testid="viewer-error-reason">{errorReason(error)}</p>
          <Button size="sm" variant="outline" className="mt-2" onClick={onRetry} data-testid="viewer-retry">
            <RotateCw aria-hidden="true" />
            Try again
          </Button>
        </AlertDescription>
      </Alert>
    </div>
  );
}

function ModelFailed({ error }: { error: unknown }) {
  const lines = issueLines(error);
  return (
    <div className="flex size-full items-center justify-center p-6">
      <Alert variant="destructive" className="max-w-2xl bg-background" data-testid="model-error">
        <CircleAlert aria-hidden="true" />
        <AlertTitle>This version's model could not be read</AlertTitle>
        <AlertDescription>
          <p>{errorReason(error)}</p>
          {lines.length > 0 && (
            <ul className="mt-1 list-disc pl-5 font-mono text-xs" data-testid="model-error-issues">
              {lines.map((line, i) => <li key={i}>{line}</li>)}
            </ul>
          )}
        </AlertDescription>
      </Alert>
    </div>
  );
}

export function ProjectVersionPage() {
  const { project, detail, model, stages } = useLoaderData<VersionPageData>();
  const location = useLocation();
  useDocumentTitle(versionTitle(project.name, detail.version));

  // Memoised on (projectId, version, stamp), not on the detail object: a save updates the cached detail's overrides and
  // must not re-create the viewer (it shows those heights already). A new address query re-creates it anyway (new
  // options), so the project is rebuilt with it, from the detail the loader read again: the heights saved since then.
  // Heights typed on an earlier visit and never saved (the API did not answer) are the start, and the saver sends them.
  const projectKey = `${detail.projectId}\n${detail.version}\n${detail.stamp}`;
  const built = useMemo(
    () => buildViewerProject(detail, model, stages, readUnsent({ projectId: detail.projectId, version: detail.version })?.heights),
    [projectKey, location.search],
  );
  const options = useMemo(() => viewerOptions(location.search), [location.search]);

  // The live viewer (set in ViewerHost's effect, never during render): heights merged with, or taken over from, heights
  // saved elsewhere are shown through it (setHeights: no heightschange, so no save loop).
  const viewerRef = useRef<Viewer | null>(null);
  const saver = useHeightsSaver(detail.projectId, detail.version, {
    base: detail.overrides,
    onRemote: heights => { const v = viewerRef.current; if (v && !v.disposed) v.setHeights(heights); },
  });

  // Heights saved elsewhere (another tab, another person) while this tab has nothing unsaved: taken over on focus, and
  // every 30 s while the page is visible (fix step, review finding "adversarial" 3).
  const path = { projectId: detail.projectId, version: detail.version };
  const savedNow = useQuery({
    ...getFurnitureHeightsOptions({ path }),
    enabled: detail.hasFurniture,
    staleTime: 0,
    refetchOnWindowFocus: 'always',
    refetchInterval: 30_000,
    retry: false,
  });
  const { adopt } = saver;
  useEffect(() => { if (savedNow.data) adopt(savedNow.data); }, [savedNow.data, adopt]);

  // A save that failed is kept in this browser and sent again, but closing the tab now could leave it unsaved for long:
  // the browser asks first (fix step, review finding "adversarial" 1).
  const unsavedFailure = saver.state.status === 'error';
  useEffect(() => {
    if (!unsavedFailure) return;
    const ask = (e: BeforeUnloadEvent) => { e.preventDefault(); e.returnValue = ''; };
    window.addEventListener('beforeunload', ask);
    return () => window.removeEventListener('beforeunload', ask);
  }, [unsavedFailure]);

  // A failed create belongs to the project it was for; Try again mounts a new host (a fresh div and a new create).
  const [attempt, setAttempt] = useState(0);
  const [failure, setFailure] = useState<{ project: ViewerProject; error: unknown } | null>(null);
  const viewerProject = built.ok ? built.project : null;
  const onError = (error: unknown) => { if (viewerProject) setFailure({ project: viewerProject, error }); };
  const onCreated = (viewer: Viewer) => {
    viewerRef.current = viewer;
    setFailure(f => (f && f.project === viewerProject ? null : f));
  };

  return (
    <div className="h-svh overflow-hidden bg-[#eef0f2]" data-testid="project-page" data-project-id={detail.projectId} data-version={detail.version}>
      <AppBar back title={project.name} className="fixed inset-x-0 top-0">
        <NewVersionButton projectId={detail.projectId} />
        <DraftsMenu projectId={detail.projectId} />
        <VersionPicker projectId={detail.projectId} versions={project.versions} current={detail.version} />
        <DownloadsMenu downloads={detail.downloads} heights={detail.hasFurniture ? saver.state : null} onOpen={saver.flush} />
        {detail.hasFurniture && <HeightsStatus state={saver.state} onRetry={saver.retry} />}
      </AppBar>
      <div className="fixed inset-x-0 top-12 bottom-0" data-testid="viewer-area">
        {viewerProject ? (
          <>
            <ViewerHost
              key={attempt}
              project={viewerProject}
              options={options}
              onHeightsChange={saver.change}
              onError={onError}
              onCreated={onCreated}
            />
            {failure && failure.project === viewerProject && (
              <ViewerFailed error={failure.error} onRetry={() => { setFailure(null); setAttempt(a => a + 1); }} />
            )}
          </>
        ) : (
          <ModelFailed error={built.ok ? null : built.error} />
        )}
      </div>
    </div>
  );
}
