// /projects/:projectId (DESIGN.md 15.1): to the project's latest version, /projects/:projectId/v/<latestVersion>, keeping
// the address options. The loader reads the project (getProject; a 404 shows Not found); the page then replaces its own
// history entry with the version's, so Back goes to where the user came from, after a click on a card as after a typed
// address (a loader redirect would PUSH on the first load and REPLACE the list's entry on a click).
// A project with no version yet (made by the next milestone's upload before its first version is built) has nowhere to go:
// the page says so (fix step, review finding "code" 10; it went on to v/0 and Not found).
import type { QueryClient } from '@tanstack/react-query';
import { Link, Navigate, useLoaderData, type LoaderFunctionArgs } from 'react-router';
import { AppBar } from '@/components/AppBar';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { getProjectOptions } from '@/api/generated/@tanstack/react-query.gen';
import { NO_VERSIONS } from '@/lib/format';
import { checkProjectId, fetchOrCached, loadOr404 } from '@/lib/routeData';
import { useDocumentTitle } from '@/lib/useDocumentTitle';

export interface ProjectRedirectData {
  /** The latest version's page, or null when the project has no version yet. */
  to: string | null;
  name: string;
}

export function projectRedirectLoader(queryClient: QueryClient) {
  return async ({ params, request }: LoaderFunctionArgs): Promise<ProjectRedirectData> => {
    const projectId = checkProjectId(params.projectId);
    const project = await loadOr404(() => fetchOrCached(queryClient, getProjectOptions({ path: { projectId } })));
    const latest = project.latestVersion >= 1 && project.versions.some(v => v.version === project.latestVersion) ? project.latestVersion : null;
    return { to: latest ? `/projects/${projectId}/v/${latest}${new URL(request.url).search}` : null, name: project.name };
  };
}

function NoVersions({ name }: { name: string }) {
  useDocumentTitle(`${name} · Walkthrough`);
  return (
    <div className="min-h-svh bg-muted/30">
      <AppBar back className="sticky top-0" title={name} />
      <main className="mx-auto max-w-2xl px-6 py-16" data-testid="no-versions">
        <h1 className="text-xl font-semibold">{NO_VERSIONS}</h1>
        <p className="mt-2 text-muted-foreground">This project has no version to open yet.</p>
        <Button asChild variant="outline" className="mt-6">
          <Link to="/projects">Back to projects</Link>
        </Button>
      </main>
    </div>
  );
}

export function ProjectRedirect() {
  const { to, name } = useLoaderData<ProjectRedirectData>();
  if (!to) return <NoVersions name={name} />;
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
