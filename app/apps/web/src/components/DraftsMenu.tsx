// The project page's "New version" button and "Drafts" menu (docs/upload/DESIGN.md U-2 screen 3, U-14.1): New version
// leads to the Upload screen; the Drafts menu lists the project's open drafts (listBuilds) and is shown only when there
// is one. File names are text. Not modal, and closing it hands the keyboard back to the viewer (as the Downloads menu).
import { useQuery } from '@tanstack/react-query';
import { FilePlus2, FolderOpen } from 'lucide-react';
import { Link } from 'react-router';
import { Button } from '@/components/ui/button';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';
import { listBuildsOptions } from '@/api/generated/@tanstack/react-query.gen';
import { draftStatusText, formatDate } from '@/lib/format';

export function NewVersionButton({ projectId }: { projectId: string }) {
  return (
    <Button asChild variant="outline" size="sm">
      <Link to={`/projects/${projectId}/builds/new`} data-testid="new-version">
        <FilePlus2 aria-hidden="true" />
        New version
      </Link>
    </Button>
  );
}

export function DraftsMenu({ projectId }: { projectId: string }) {
  const builds = useQuery({ ...listBuildsOptions({ path: { projectId } }), staleTime: 10_000, retry: false });
  const open = (builds.data?.builds ?? []).filter(b => b.status === 'open');
  if (!open.length) return null;
  return (
    <DropdownMenu modal={false}>
      <DropdownMenuTrigger asChild>
        <Button variant="outline" size="sm" data-testid="drafts-menu">
          <FolderOpen aria-hidden="true" />
          {`Drafts (${open.length})`}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="min-w-64" data-testid="drafts-list" onCloseAutoFocus={e => e.preventDefault()}>
        {open.map(b => (
          <DropdownMenuItem key={b.id} asChild data-testid="draft-item" data-build-id={b.id}>
            <Link to={`/projects/${projectId}/builds/${b.id}`}>
              <span className="grid">
                <span className="max-w-72 truncate">{b.sourceNames.join(', ') || 'No files'}</span>
                <span className="text-xs text-muted-foreground">{`${formatDate(b.createdAt)} · ${draftStatusText(b.runStatus)}`}</span>
              </span>
            </Link>
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
