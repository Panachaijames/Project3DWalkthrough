// One card of the project list (DESIGN.md 15.2): thumbnail (else a neutral placeholder with the short name), name, a
// CAD / Pictures badge, floors, furniture and openings counts, the stamp, last updated, versions; links to the project.
// A project with no version yet (made in the app, its upload or build unfinished; docs/upload/DESIGN.md U-14.1) links to
// its newest open draft, or to its Upload screen when it has none (listBuilds, read for such cards only).
// Each card has a small Delete over its thumbnail's corner (12 Nov 2026, docs/contract-issues/DEL.md): a sibling of the
// card's link, never inside it.
// Names come from drawings: React renders them as text, never as HTML.
import { useQuery } from '@tanstack/react-query';
import { ImageOff } from 'lucide-react';
import { useState } from 'react';
import { Link } from 'react-router';
import { listBuildsOptions } from '@/api/generated/@tanstack/react-query.gen';
import { DeleteProjectButton } from '@/components/DeleteActions';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { apiUrl } from '@/api/client';
import type { ProjectSummary } from '@/api/generated/types.gen';
import {
  formatDate,
  formatFloors,
  formatFurniture,
  formatOpenings,
  formatVersions,
  NO_VERSIONS,
  sourceKindLabel,
} from '@/lib/format';

function Thumbnail({ project }: { project: ProjectSummary }) {
  const [broken, setBroken] = useState(false);
  const src = project.thumbnailUrl && !broken ? apiUrl(project.thumbnailUrl) : null;
  return (
    <div className="relative aspect-[16/10] w-full overflow-hidden border-b bg-muted">
      {src ? (
        <img
          src={src}
          alt={`Top view of ${project.shortName}`}
          data-testid="card-thumbnail"
          className="size-full object-cover"
          draggable={false}
          onError={() => setBroken(true)}
        />
      ) : (
        <div
          data-testid="card-placeholder"
          className="flex size-full flex-col items-center justify-center gap-2 px-4 text-center text-muted-foreground"
        >
          <ImageOff className="size-6 opacity-60" aria-hidden="true" />
          <span className="text-sm font-medium" data-testid="card-placeholder-name">{project.shortName}</span>
        </div>
      )}
    </div>
  );
}

const Dot = () => <span aria-hidden="true" className="text-muted-foreground/50">·</span>;

/** A project made before its first version (made in the app, while its first version is built). */
export const hasVersions = (project: Pick<ProjectSummary, 'latestVersion' | 'versionCount'>) => project.latestVersion >= 1 && project.versionCount > 0;

/** Where a project with no version leads: its newest open draft, else its Upload screen (U-14.1). */
export function draftTarget(projectId: string, builds: readonly { id: string; status: string; createdAt: string }[] | undefined): string {
  const open = (builds ?? []).filter(b => b.status === 'open').sort((a, b) => (a.createdAt < b.createdAt ? 1 : a.createdAt > b.createdAt ? -1 : 0));
  return open[0] ? `/projects/${projectId}/builds/${open[0].id}` : `/projects/${projectId}/builds/new`;
}

function NoVersionCard({ project }: { project: ProjectSummary }) {
  const builds = useQuery({ ...listBuildsOptions({ path: { projectId: project.id } }), staleTime: 5_000 });
  const to = builds.data ? draftTarget(project.id, builds.data.builds) : `/projects/${project.id}`;
  const hasDraft = !!builds.data?.builds.some(b => b.status === 'open');
  return (
    <Card
      data-testid="project-card"
      data-project-id={project.id}
      data-no-versions=""
      className="relative gap-0 overflow-hidden py-0 transition-shadow focus-within:ring-2 focus-within:ring-ring/50 hover:shadow-md"
    >
      <Link to={to} className="flex h-full flex-col outline-none" aria-label={`Continue ${project.name}`} data-testid="card-link" data-draft={hasDraft ? '' : undefined}>
        <Thumbnail project={project} />
        <CardHeader className="gap-1.5 px-4 pt-4 pb-4">
          <div className="flex items-start justify-between gap-2">
            <CardTitle className="leading-snug" data-testid="card-name">{project.name}</CardTitle>
            <Badge variant="secondary" className="shrink-0" data-testid="card-source">{sourceKindLabel(project.sourceKind)}</Badge>
          </div>
          <CardDescription data-testid="card-no-versions">{NO_VERSIONS}</CardDescription>
          <p className="text-sm text-muted-foreground" data-testid="card-next">{hasDraft ? 'A draft is open: continue it' : 'Upload its drawings'}</p>
        </CardHeader>
      </Link>
      <DeleteProjectButton project={project} />
    </Card>
  );
}

export function ProjectCard({ project }: { project: ProjectSummary }) {
  if (!hasVersions(project)) return <NoVersionCard project={project} />;
  return (
    <Card
      data-testid="project-card"
      data-project-id={project.id}
      className="relative gap-0 overflow-hidden py-0 transition-shadow focus-within:ring-2 focus-within:ring-ring/50 hover:shadow-md"
    >
      <Link
        to={`/projects/${project.id}`}
        className="flex h-full flex-col outline-none"
        aria-label={`Open ${project.name}`}
        data-testid="card-link"
      >
        <Thumbnail project={project} />
        <CardHeader className="gap-1.5 px-4 pt-4">
          <div className="flex items-start justify-between gap-2">
            <CardTitle className="leading-snug" data-testid="card-name">{project.name}</CardTitle>
            <Badge variant="secondary" className="shrink-0" data-testid="card-source">{sourceKindLabel(project.sourceKind)}</Badge>
          </div>
          <CardDescription data-testid="card-floors">{formatFloors(project.floors)}</CardDescription>
        </CardHeader>
        <CardContent className="mt-auto grid gap-1 px-4 pt-3 pb-4 text-sm text-muted-foreground">
          <p className="flex flex-wrap items-baseline gap-x-1.5">
            <span data-testid="card-furniture">{formatFurniture(project.furnitureCount)}</span>
            <Dot />
            <span data-testid="card-openings">{formatOpenings(project.openingsCount)}</span>
          </p>
          <p className="flex flex-wrap items-baseline gap-x-1.5">
            <span data-testid="card-versions">{formatVersions(project.versionCount)}</span>
            <Dot />
            <span>
              {'Updated '}
              <time dateTime={project.updatedAt} data-testid="card-updated">{formatDate(project.updatedAt) || 'unknown'}</time>
            </span>
          </p>
          <p className="mt-1.5 truncate font-mono text-xs text-foreground/75" title="Model-data stamp of the latest version (the 3ds Max script carries the same)">
            <span className="sr-only">Stamp </span>
            <span data-testid="card-stamp">{project.stamp}</span>
          </p>
        </CardContent>
      </Link>
      <DeleteProjectButton project={project} />
    </Card>
  );
}

/** The loading state of the list: cards of the same shape. */
export function ProjectCardSkeleton() {
  return (
    <Card data-testid="project-card-skeleton" className="gap-0 overflow-hidden py-0" aria-hidden="true">
      <Skeleton className="aspect-[16/10] w-full rounded-none" />
      <div className="grid gap-3 p-4">
        <Skeleton className="h-5 w-3/4" />
        <Skeleton className="h-4 w-1/2" />
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-2/3" />
      </div>
    </Card>
  );
}
