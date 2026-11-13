// The project page's "New version" button and "Drafts" menu (docs/upload/DESIGN.md U-2 screen 3, U-14.1): New version
// leads to the Upload screen; the Drafts menu lists the project's open drafts (listBuilds) and is shown only when there
// is one. File names are text. Not modal, and closing it hands the keyboard back to the viewer (as the Downloads menu).
// Each draft has a Delete beside it (12 Nov 2026, docs/contract-issues/DEL.md): the existing deleteBuild, after the same
// confirm as the drafts list of a project with no version; the menu stays open, so a refusal shows its reason in it, and
// a draft whose run is going cannot be deleted (the API says run_in_progress).
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { FilePlus2, FolderOpen, Trash2 } from 'lucide-react';
import { useState } from 'react';
import { Link } from 'react-router';
import { Button } from '@/components/ui/button';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';
import { listBuildsOptions, listBuildsQueryKey } from '@/api/generated/@tanstack/react-query.gen';
import { deleteBuild } from '@/api/generated/sdk.gen';
import { confirmed, DRAFT_DELETE_TEXT } from '@/components/DeleteActions';
import { draftStatusText, errorReason, formatDate } from '@/lib/format';

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

const running = (status: string | null) => status === 'running' || status === 'queued';

export function DraftsMenu({ projectId }: { projectId: string }) {
  const queryClient = useQueryClient();
  const builds = useQuery({ ...listBuildsOptions({ path: { projectId } }), staleTime: 10_000, retry: false });
  const [deleting, setDeleting] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const open = (builds.data?.builds ?? []).filter(b => b.status === 'open');
  if (!open.length) return null;
  const remove = async (buildId: string) => {
    if (deleting !== null || !confirmed(DRAFT_DELETE_TEXT)) return;
    setDeleting(buildId);
    setError(null);
    try {
      await deleteBuild({ path: { projectId, buildId }, throwOnError: true });
      await queryClient.invalidateQueries({ queryKey: listBuildsQueryKey({ path: { projectId } }) });
    } catch (err) {
      setError(`The draft was not deleted: ${errorReason(err)}`);
    } finally {
      setDeleting(null);
    }
  };
  return (
    <DropdownMenu modal={false} onOpenChange={o => { if (!o) setError(null); }}>
      <DropdownMenuTrigger asChild>
        <Button variant="outline" size="sm" data-testid="drafts-menu">
          <FolderOpen aria-hidden="true" />
          {`Drafts (${open.length})`}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="min-w-64" data-testid="drafts-list" onCloseAutoFocus={e => e.preventDefault()}>
        {open.map(b => (
          <div key={b.id} className="flex items-center gap-1" data-testid="draft-entry" data-build-id={b.id}>
            <DropdownMenuItem asChild className="min-w-0 flex-1" data-testid="draft-item" data-build-id={b.id}>
              <Link to={`/projects/${projectId}/builds/${b.id}`}>
                <span className="grid">
                  <span className="max-w-72 truncate">{b.sourceNames.join(', ') || 'No files'}</span>
                  <span className="text-xs text-muted-foreground">{`${formatDate(b.createdAt)} · ${draftStatusText(b.runStatus)}`}</span>
                </span>
              </Link>
            </DropdownMenuItem>
            <DropdownMenuItem
              variant="destructive"
              className="shrink-0"
              disabled={deleting !== null || running(b.runStatus)}
              title={running(b.runStatus) ? 'A run of this draft is going: cancel it first' : 'Delete this draft'}
              aria-label={`Delete the draft of ${b.sourceNames.join(', ') || 'no files'}`}
              onSelect={e => { e.preventDefault(); void remove(b.id); }}
              data-testid="draft-item-delete"
              data-build-id={b.id}
            >
              <Trash2 aria-hidden="true" />
              {deleting === b.id ? 'Deleting…' : 'Delete'}
            </DropdownMenuItem>
          </div>
        ))}
        {error && <p role="alert" className="max-w-80 px-2 py-1.5 text-xs text-destructive" data-testid="draft-delete-error">{error}</p>}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
