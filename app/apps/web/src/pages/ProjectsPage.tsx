// /projects (DESIGN.md 15.1, 15.2): a grid of project cards, newest first. Loading: skeleton cards; error: an Alert with
// Retry; empty: `No projects yet: make one with New project` (docs/upload/DESIGN.md U-14.1, with the New project button).
// The loader starts the list query (ensureQueryData) without waiting for it, so the page itself shows the loading and
// error states.
import { useQuery, type QueryClient } from '@tanstack/react-query';
import { CircleAlert, Plus, RotateCw } from 'lucide-react';
import type { ReactNode } from 'react';
import { Link } from 'react-router';
import { AppBar } from '@/components/AppBar';
import { ProjectCard, ProjectCardSkeleton } from '@/components/ProjectCard';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { listProjectsOptions } from '@/api/generated/@tanstack/react-query.gen';
import type { ProjectSummary } from '@/api/generated/types.gen';
import { errorReason, formatNumber, NO_PROJECTS, projectsTitle } from '@/lib/format';
import { useDocumentTitle } from '@/lib/useDocumentTitle';

export function projectsLoader(queryClient: QueryClient) {
  return () => {
    void queryClient.ensureQueryData(listProjectsOptions()).catch(() => undefined);   // the page shows the error
    return null;
  };
}

/** Newest first by updatedAt (the API's order; kept stable for equal times). */
export function newestFirst(projects: readonly ProjectSummary[]): ProjectSummary[] {
  return projects
    .map((p, i) => ({ p, i, t: Date.parse(p.updatedAt) || 0 }))
    .sort((a, b) => b.t - a.t || a.i - b.i)
    .map(x => x.p);
}

function Grid({ children }: { children: ReactNode }) {
  return <div className="grid grid-cols-[repeat(auto-fill,minmax(260px,1fr))] gap-4" data-testid="project-grid">{children}</div>;
}

function Shell({ children, count }: { children: ReactNode; count?: number }) {
  return (
    <div className="min-h-svh bg-muted/30">
      <AppBar className="sticky top-0" />
      <main className="mx-auto w-full max-w-7xl px-6 py-6">
        <div className="mb-4 flex items-baseline gap-3">
          <h1 className="text-xl font-semibold tracking-tight">Projects</h1>
          {count !== undefined && <span className="text-sm text-muted-foreground" data-testid="project-count">{formatNumber(count)}</span>}
          <Button asChild size="sm" className="ml-auto self-center">
            <Link to="/projects/new" data-testid="new-project">
              <Plus aria-hidden="true" />
              New project
            </Link>
          </Button>
        </div>
        {children}
      </main>
    </div>
  );
}

export function ProjectsSkeleton() {
  return (
    <Grid>
      {[0, 1, 2, 3].map(i => <ProjectCardSkeleton key={i} />)}
    </Grid>
  );
}

/** The page while the router starts (HydrateFallback). */
export function ProjectsPageFallback() {
  useDocumentTitle(projectsTitle());
  return <Shell><ProjectsSkeleton /></Shell>;
}

function ListError({ error, busy, onRetry, title }: { error: unknown; busy: boolean; onRetry: () => void; title: string }) {
  return (
    <Alert variant="destructive" data-testid="projects-error" className="mb-4">
      <CircleAlert aria-hidden="true" />
      <AlertTitle>{title}</AlertTitle>
      <AlertDescription>
        <p data-testid="projects-error-reason">{errorReason(error)}</p>
        <Button size="sm" variant="outline" className="mt-2" disabled={busy} onClick={onRetry} data-testid="projects-retry">
          <RotateCw aria-hidden="true" className={busy ? 'animate-spin' : undefined} />
          Retry
        </Button>
      </AlertDescription>
    </Alert>
  );
}

export function ProjectsPage() {
  useDocumentTitle(projectsTitle());
  const query = useQuery(listProjectsOptions());
  const retry = () => void query.refetch();

  if (query.isPending) return <Shell><ProjectsSkeleton /></Shell>;

  // No list at all: the error alone. A failed background refresh keeps the cards it has and says so above them.
  if (!query.data) {
    return (
      <Shell>
        <ListError error={query.error} busy={query.isFetching} onRetry={retry} title="The projects could not be loaded" />
      </Shell>
    );
  }
  const refreshFailed = query.isError
    ? <ListError error={query.error} busy={query.isFetching} onRetry={retry} title="The list could not be refreshed" />
    : null;

  const projects = newestFirst(query.data.projects);
  if (!projects.length) {
    return (
      <Shell count={0}>
        {refreshFailed}
        <p className="rounded-lg border border-dashed bg-background p-8 text-center text-muted-foreground" data-testid="projects-empty">
          {NO_PROJECTS}
        </p>
      </Shell>
    );
  }
  return (
    <Shell count={projects.length}>
      {refreshFailed}
      <Grid>
        {projects.map(p => <ProjectCard key={p.id} project={p} />)}
      </Grid>
    </Shell>
  );
}
