// Deleting a project, a version or a draft (the owner's request of 12 Nov 2026; docs/contract-issues/DEL.md). Every
// delete asks first with the browser's own confirm (as the drafts list of a project with no version does), naming what
// is lost and that it cannot be undone; Cancel sends nothing. A refusal (409 busy while a build runs, 409 only_version)
// shows the API's reason.
// * The project list: a small Delete on each card (DeleteProjectButton, over the thumbnail's corner).
// * The project page: a "..." menu beside the version picker (ProjectActionsMenu) with "Delete this version (v<n>)" (for
//   the only version it is disabled and says to delete the project instead) and "Delete project". After a version is
//   deleted the page goes to the project's latest remaining version; after the project, to the project list. Both
//   replace the history entry of the page that is gone.
// * The Drafts menu's Delete per draft (DraftsMenu.tsx) and the drafts list of a project with no version
//   (ProjectRedirect.tsx) share DRAFT_DELETE_TEXT.
// Names are drawing or staff text: React renders them as text; window.confirm shows plain text.
import { useQueryClient, type QueryClient } from '@tanstack/react-query';
import { CircleAlert, Ellipsis, Trash2 } from 'lucide-react';
import { useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { getProjectOptions, getProjectQueryKey, listBuildsOptions, listProjectsQueryKey } from '@/api/generated/@tanstack/react-query.gen';
import { deleteProject, deleteVersion } from '@/api/generated/sdk.gen';
import type { ProjectList } from '@/api/generated/types.gen';
import { errorReason, plural } from '@/lib/format';
import { allUnsent, writeUnsent } from '@/lib/heightsOutbox';
import { cn } from '@/lib/utils';

export const DRAFT_DELETE_TEXT = 'Delete this draft? Its uploaded files stay with the project.';
export const ONLY_VERSION_TEXT = "This is the project's only version: delete the project instead.";

/** 'Delete TEST_BANK? Its 2 versions, 1 draft and uploaded drawings are removed from this computer. This cannot be
 *  undone.' `drafts` null: not known (the list could not be read). */
export function projectDeleteText(name: string, versions: number, drafts: number | null): string {
  const parts: string[] = [];
  if (versions > 0) parts.push(plural(versions, 'version', 'versions'));
  if (drafts === null) parts.push('drafts');
  else if (drafts > 0) parts.push(plural(drafts, 'draft', 'drafts'));
  parts.push('uploaded drawings');
  const list = parts.length > 1 ? `${parts.slice(0, -1).join(', ')} and ${parts[parts.length - 1]}` : parts[0];
  return `Delete ${name}? Its ${list} are removed from this computer. This cannot be undone.`;
}

/** 'Delete version 1 of TEST_BANK? This cannot be undone. Version numbers are not reused.' */
export function versionDeleteText(name: string, version: number): string {
  return `Delete version ${version} of ${name}? This cannot be undone. Version numbers are not reused.`;
}

/** The browser's confirm; true where there is none (as DraftList). */
export function confirmed(text: string): boolean {
  if (typeof window === 'undefined' || typeof window.confirm !== 'function') return true;
  return window.confirm(text);
}

type KeyHead = { path?: { projectId?: unknown; version?: unknown } };
const headOf = (key: readonly unknown[]): KeyHead | null => (key[0] && typeof key[0] === 'object' ? (key[0] as KeyHead) : null);

/** After a project is deleted: off the cached list at once (then the list is read again), its cached answers and the
 *  heights this browser kept unsent for it dropped. */
export function forgetProject(queryClient: QueryClient, projectId: string): void {
  queryClient.setQueryData<ProjectList>(listProjectsQueryKey(), old => (old ? { ...old, projects: old.projects.filter(p => p.id !== projectId) } : old));
  queryClient.removeQueries({ predicate: q => headOf(q.queryKey)?.path?.projectId === projectId });
  void queryClient.invalidateQueries({ queryKey: listProjectsQueryKey() });
  for (const { path } of allUnsent()) if (path.projectId === projectId) writeUnsent(path, null);
}

/** After a version is deleted: its cached answers and unsent heights dropped; the list is read again. */
export function forgetVersion(queryClient: QueryClient, projectId: string, version: number): void {
  queryClient.removeQueries({ predicate: q => { const p = headOf(q.queryKey)?.path; return p?.projectId === projectId && p.version === version; } });
  writeUnsent({ projectId, version }, null);
  void queryClient.invalidateQueries({ queryKey: listProjectsQueryKey() });
}

export interface DeletableProject { id: string; name: string; versionCount: number }

/** Delete a project: reads its open drafts for the confirm text, asks, deletes, then `after()` (the page goes to the
 *  list) and the caches forget it. */
export function useProjectDelete(project: DeletableProject, after?: () => Promise<void> | void) {
  const queryClient = useQueryClient();
  const going = useRef(false);                     // one delete at a time (a second click while the first asks)
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const start = async () => {
    if (going.current) return;
    going.current = true;
    setError(null);
    try {
      let drafts: number | null = null;
      try {
        const list = await queryClient.fetchQuery({ ...listBuildsOptions({ path: { projectId: project.id } }), staleTime: 0 });
        drafts = list.builds.filter(b => b.status === 'open').length;
      } catch {
        drafts = null;
      }
      if (!confirmed(projectDeleteText(project.name, project.versionCount, drafts))) return;
      setBusy(true);
      try {
        await deleteProject({ path: { projectId: project.id }, throwOnError: true });
      } catch (err) {
        setError(`${project.name} was not deleted: ${errorReason(err)}`);
        return;
      }
      await after?.();
      forgetProject(queryClient, project.id);
    } finally {
      going.current = false;
      setBusy(false);
    }
  };
  return { start, busy, error, dismiss: () => setError(null) };
}

/** The project list's Delete (a small button over the corner of the card's thumbnail). */
export function DeleteProjectButton({ project, className }: { project: DeletableProject; className?: string }) {
  const del = useProjectDelete(project);
  return (
    <>
      <Button
        type="button"
        variant="ghost"
        size="icon"
        className={cn('absolute top-2 right-2 z-10 size-7 bg-background/80 text-muted-foreground shadow-xs hover:bg-background hover:text-destructive', className)}
        aria-label={`Delete ${project.name}`}
        title={`Delete ${project.name}`}
        disabled={del.busy}
        onClick={() => void del.start()}
        data-testid="card-delete"
      >
        <Trash2 aria-hidden="true" />
      </Button>
      {del.error && (
        <p role="alert" className="px-4 pb-3 text-sm text-destructive" data-testid="card-delete-error">{del.error}</p>
      )}
    </>
  );
}

function DeleteError({ text, onClose }: { text: string; onClose: () => void }) {
  return (
    <Alert variant="destructive" className="fixed top-14 right-3 z-30 w-auto max-w-md bg-background shadow-md" data-testid="delete-error">
      <CircleAlert aria-hidden="true" />
      <AlertTitle>Not deleted</AlertTitle>
      <AlertDescription>
        <p data-testid="delete-error-reason">{text}</p>
        <Button size="sm" variant="outline" className="mt-2" onClick={onClose} data-testid="delete-error-close">Close</Button>
      </AlertDescription>
    </Alert>
  );
}

export interface ProjectActionsMenuProps {
  project: DeletableProject & { versions: readonly { version: number }[] };
  /** The version on screen. */
  version: number;
}

/** The project page's "..." menu, beside the version picker: Delete this version, Delete project. */
export function ProjectActionsMenu({ project, version }: ProjectActionsMenuProps) {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const location = useLocation();
  const [versionBusy, setVersionBusy] = useState(false);
  const [versionError, setVersionError] = useState<string | null>(null);
  const projectDelete = useProjectDelete(project, async () => { await navigate('/projects', { replace: true }); });
  const only = project.versions.length <= 1;
  const busy = versionBusy || projectDelete.busy;

  const removeVersion = async () => {
    if (only || busy || !confirmed(versionDeleteText(project.name, version))) return;
    setVersionBusy(true);
    setVersionError(null);
    try {
      await deleteVersion({ path: { projectId: project.id, version }, throwOnError: true });
    } catch (err) {
      setVersionError(`Version ${version} was not deleted: ${errorReason(err)}`);
      setVersionBusy(false);
      return;
    }
    // the project as it is now: its latest remaining version (the redirect page reads it again if this fails)
    const path = { projectId: project.id };
    await queryClient.invalidateQueries({ queryKey: getProjectQueryKey({ path }), refetchType: 'none' });
    let to = `/projects/${project.id}${location.search}`;
    try {
      const fresh = await queryClient.fetchQuery({ ...getProjectOptions({ path }), staleTime: 0 });
      if (fresh.latestVersion >= 1 && fresh.versions.some(v => v.version === fresh.latestVersion)) {
        to = `/projects/${project.id}/v/${fresh.latestVersion}${location.search}`;
      }
    } catch {
      // the redirect page shows what the API says
    }
    await navigate(to, { replace: true });
    forgetVersion(queryClient, project.id, version);
    setVersionBusy(false);
  };
  // the menu closes first, then the browser's confirm opens
  const later = (fn: () => Promise<void>) => { setTimeout(() => void fn(), 0); };

  const error = versionError ?? projectDelete.error;
  return (
    <>
      <DropdownMenu modal={false}>
        <DropdownMenuTrigger asChild>
          <Button
            variant="ghost"
            size="icon"
            className="size-8"
            aria-label="More actions: delete this version or the project"
            title="Delete this version or the project"
            disabled={busy}
            data-testid="project-actions"
          >
            <Ellipsis aria-hidden="true" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-72" data-testid="project-actions-list" onCloseAutoFocus={e => e.preventDefault()}>
          <DropdownMenuItem disabled={only} onSelect={() => later(removeVersion)} data-testid="delete-version" data-version={version}>
            <Trash2 aria-hidden="true" />
            <span className="grid">
              <span>{`Delete this version (v${version})`}</span>
              {only && <span className="text-xs text-muted-foreground" data-testid="delete-version-note">{ONLY_VERSION_TEXT}</span>}
            </span>
          </DropdownMenuItem>
          <DropdownMenuSeparator />
          <DropdownMenuItem variant="destructive" onSelect={() => later(projectDelete.start)} data-testid="delete-project">
            <Trash2 aria-hidden="true" />
            Delete project
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
      {busy && (
        <span role="status" className="text-xs text-muted-foreground" data-testid="delete-busy">
          {versionBusy ? 'Deleting the version…' : 'Deleting the project…'}
        </span>
      )}
      {error && <DeleteError text={error} onClose={() => { setVersionError(null); projectDelete.dismiss(); }} />}
    </>
  );
}
