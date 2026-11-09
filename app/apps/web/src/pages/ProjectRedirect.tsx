// /projects/:projectId (DESIGN.md 15.1): to the project's latest version, /projects/:projectId/v/<latestVersion>, keeping
// the address options. The loader reads the project (getProject; a 404 shows Not found); the page then replaces its own
// history entry with the version's, so Back goes to where the user came from, after a click on a card as after a typed
// address (a loader redirect would PUSH on the first load and REPLACE the list's entry on a click).
// A project with no version yet (made in the app, its upload or build unfinished) stays reachable (docs/upload/DESIGN.md
// U-14.1): its page lists its drafts (listBuilds: the files' names, the status, Continue, Delete) and offers Upload
// drawings (fix step, review finding "code" 10, then U-14.1; it went on to v/0 and Not found).
import { useQuery, useQueryClient, type QueryClient } from '@tanstack/react-query';
import { FileUp, Trash2 } from 'lucide-react';
import { useState } from 'react';
import { Link, Navigate, useLoaderData, type LoaderFunctionArgs } from 'react-router';
import { AppBar } from '@/components/AppBar';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { getProjectOptions, listBuildsOptions, listBuildsQueryKey } from '@/api/generated/@tanstack/react-query.gen';
import { deleteBuild } from '@/api/generated/sdk.gen';
import { draftStatusText, errorReason, formatDate, NO_VERSIONS } from '@/lib/format';
import { checkProjectId, fetchOrCached, loadOr404 } from '@/lib/routeData';
import { useDocumentTitle } from '@/lib/useDocumentTitle';

export interface ProjectRedirectData {
  /** The latest version's page, or null when the project has no version yet. */
  to: string | null;
  name: string;
  projectId: string;
}

export function projectRedirectLoader(queryClient: QueryClient) {
  return async ({ params, request }: LoaderFunctionArgs): Promise<ProjectRedirectData> => {
    const projectId = checkProjectId(params.projectId);
    const project = await loadOr404(() => fetchOrCached(queryClient, getProjectOptions({ path: { projectId } })));
    const latest = project.latestVersion >= 1 && project.versions.some(v => v.version === project.latestVersion) ? project.latestVersion : null;
    return { to: latest ? `/projects/${projectId}/v/${latest}${new URL(request.url).search}` : null, name: project.name, projectId };
  };
}

/** The drafts of a project with no version yet (U-14.1). */
export function DraftList({ projectId }: { projectId: string }) {
  const queryClient = useQueryClient();
  const builds = useQuery(listBuildsOptions({ path: { projectId } }));
  const [deleting, setDeleting] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const open = (builds.data?.builds ?? []).filter(b => b.status === 'open');
  const remove = async (buildId: string) => {
    if (typeof window !== 'undefined' && typeof window.confirm === 'function' && !window.confirm('Delete this draft? Its uploaded files stay with the project.')) return;
    setDeleting(buildId);
    setError(null);
    try {
      await deleteBuild({ path: { projectId, buildId }, throwOnError: true });
      await queryClient.invalidateQueries({ queryKey: listBuildsQueryKey({ path: { projectId } }) });
    } catch (err) {
      setError(errorReason(err));
    } finally {
      setDeleting(null);
    }
  };
  if (builds.isPending) return <p className="text-sm text-muted-foreground">Looking for drafts...</p>;
  if (builds.isError) return <p className="text-sm text-destructive">{`The drafts could not be listed: ${errorReason(builds.error)}`}</p>;
  return (
    <section className="grid gap-2" data-testid="draft-list">
      {open.length ? (
        <ul className="grid gap-2">
          {open.map(b => (
            <li key={b.id} className="flex flex-wrap items-center gap-3 rounded-lg border bg-background p-3" data-testid="draft-row" data-build-id={b.id}>
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium" data-testid="draft-files">{b.sourceNames.join(', ') || 'No files'}</p>
                <p className="text-xs text-muted-foreground" data-testid="draft-status">{`Started ${formatDate(b.createdAt)} · ${draftStatusText(b.runStatus)}`}</p>
              </div>
              <Button asChild size="sm">
                <Link to={`/projects/${projectId}/builds/${b.id}`} data-testid="draft-continue">Continue</Link>
              </Button>
              <Button size="sm" variant="ghost" disabled={deleting !== null || b.runStatus === 'running' || b.runStatus === 'queued'} onClick={() => void remove(b.id)} data-testid="draft-delete">
                <Trash2 aria-hidden="true" />
                Delete
              </Button>
            </li>
          ))}
        </ul>
      ) : <p className="text-sm text-muted-foreground" data-testid="no-drafts">No draft is open.</p>}
      {error && <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>}
    </section>
  );
}

function NoVersions({ name, projectId }: { name: string; projectId: string }) {
  useDocumentTitle(`${name} · Walkthrough`);
  return (
    <div className="min-h-svh bg-muted/30">
      <AppBar back className="sticky top-0" title={name} />
      <main className="mx-auto grid max-w-2xl gap-4 px-6 py-16" data-testid="no-versions">
        <div>
          <h1 className="text-xl font-semibold">{NO_VERSIONS}</h1>
          <p className="mt-2 text-muted-foreground">This project has no version to open yet: continue a draft, or upload its drawings.</p>
        </div>
        <DraftList projectId={projectId} />
        <div className="flex gap-2">
          <Button asChild>
            <Link to={`/projects/${projectId}/builds/new`} data-testid="upload-drawings">
              <FileUp aria-hidden="true" />
              Upload drawings
            </Link>
          </Button>
          <Button asChild variant="outline">
            <Link to="/projects">Back to projects</Link>
          </Button>
        </div>
      </main>
    </div>
  );
}

export function ProjectRedirect() {
  const { to, name, projectId } = useLoaderData<ProjectRedirectData>();
  if (!to) return <NoVersions name={name} projectId={projectId} />;
  return <Navigate to={to} replace />;
}

/** While a project page loads at start-up (HydrateFallback of the project routes). */
export function ProjectPageFallback() {
  return (
    <div className="min-h-svh bg-muted/30" data-testid="project-loading">
      <AppBar back className="fixed inset-x-0 top-0" title={<Skeleton className="h-4 w-48" />} />
      <div className="fixed inset-x-0 top-12 bottom-0 flex items-center justify-center bg-[#eef0f2] text-sm text-muted-foreground">
        Opening the project…
      </div>
    </div>
  );
}
