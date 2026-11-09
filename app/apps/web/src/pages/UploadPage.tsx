// /projects/:projectId/builds/new (docs/upload/DESIGN.md U-2 screen 4, U-5, U-14.1): a drop zone and a file picker
// (.dwg, .dxf, several at once); per file its name, size, a progress bar by part, Retry (not for a file the API refuses
// outright) / Remove; for a project whose latest version was built from uploads "Use the files of v<n> again"; then
// createBuild with the uploaded sources (in the order picked) -> the Build page. Files go one at a time, each with two
// parts in flight (upload/upload.ts); leaving the page pauses them, and picking a file again (after a reload, or after
// coming back) resumes its session. `?from=<buildId>` (the Files step's "Start again with other files") starts the new
// draft from that draft's settings. File names are the user's: text only.
import { useQuery, useQueryClient, type QueryClient } from '@tanstack/react-query';
import { CircleAlert, FileUp, RotateCw, Trash2, Upload } from 'lucide-react';
import { useEffect, useRef, useState, type DragEvent } from 'react';
import { Link, useLoaderData, useNavigate, useSearchParams, type LoaderFunctionArgs } from 'react-router';
import { AppBar } from '@/components/AppBar';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { getProjectOptions, listBuildsOptions, listBuildsQueryKey } from '@/api/generated/@tanstack/react-query.gen';
import { createBuild } from '@/api/generated/sdk.gen';
import { APP_NAME, errorReason } from '@/lib/format';
import { checkProjectId, fetchOrCached, loadOr404 } from '@/lib/routeData';
import { useDocumentTitle } from '@/lib/useDocumentTitle';
import { cn } from '@/lib/utils';
import type { BuildDetail, NewBuildRequest, SourceFile } from '@/upload/contracts';
import {
  DRAWING_FILE, formatBytes, PERMANENT_UPLOAD_ERRORS, UploadCancelled, UploadError, uploadFile, type UploadOptions, type UploadProgress,
  type UploadTask,
} from '@/upload/upload';

export const uploadTitle = (name: string) => `${name} · upload · ${APP_NAME}`;
const BUILD_ID = /^[0-9]{8}T[0-9]{6}-[0-9a-f]{6}$/;

export interface UploadPageData { projectId: string }

export function uploadLoader(queryClient: QueryClient) {
  return async ({ params }: LoaderFunctionArgs): Promise<UploadPageData> => {
    const projectId = checkProjectId(params.projectId);
    await loadOr404(() => fetchOrCached(queryClient, getProjectOptions({ path: { projectId } })));
    void queryClient.ensureQueryData(listBuildsOptions({ path: { projectId } })).catch(() => undefined);
    return { projectId };
  };
}

type RowState = 'waiting' | 'uploading' | 'done' | 'failed';
interface Row {
  id: number;
  file: File;
  state: RowState;
  progress: UploadProgress | null;
  source: SourceFile | null;
  error: string | null;
  /** The file itself was refused (too large, not a drawing, too old): Retry cannot help (UR, V2-10). */
  permanent: boolean;
}

/** The project's latest version was built from uploaded drawings, so its files can be used again: a saved draft of the
 *  builds list made it (UR, V3-8: the four seeded projects offered the button and it always failed, 404
 *  version_not_found). A saved draft is cleaned 7 days after its save, and with it the button: the files are uploaded
 *  again then. */
export function latestFromUpload(latest: number, builds: { status: string; savedVersion: number | null }[] | undefined): boolean {
  return latest >= 1 && (builds ?? []).some(b => b.status === 'saved' && b.savedVersion === latest);
}

/** Test seam: the upload options (api, sleep ...) the page passes to every file's upload. */
export let uploadOptionsForTests: Partial<UploadOptions> | null = null;
export function setUploadOptionsForTests(o: Partial<UploadOptions> | null): void { uploadOptionsForTests = o; }

let nextRowId = 1;

export function UploadPage() {
  const { projectId } = useLoaderData<UploadPageData>();
  const [params] = useSearchParams();
  const fromBuild = params.get('from');
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const project = useQuery(getProjectOptions({ path: { projectId } }));
  const builds = useQuery(listBuildsOptions({ path: { projectId } }));
  const name = project.data?.name ?? projectId;
  useDocumentTitle(uploadTitle(name));
  const [rows, setRows] = useState<Row[]>([]);
  const [refused, setRefused] = useState<string[]>([]);
  const [drag, setDrag] = useState(false);
  const [starting, setStarting] = useState<'build' | 'reuse' | null>(null);
  const [startError, setStartError] = useState<string | null>(null);
  const tasks = useRef(new Map<number, UploadTask>());
  const input = useRef<HTMLInputElement>(null);
  const latest = project.data?.latestVersion ?? 0;
  const openDrafts = (builds.data?.builds ?? []).filter(b => b.status === 'open');

  const update = (id: number, patch: Partial<Row>) => setRows(rs => rs.map(r => (r.id === id ? { ...r, ...patch } : r)));

  // one file at a time (each with two parts in flight): the next waiting row starts when none is uploading
  useEffect(() => {
    if (rows.some(r => r.state === 'uploading')) return;
    const next = rows.find(r => r.state === 'waiting');
    if (!next) return;
    update(next.id, { state: 'uploading', error: null });
    const task = uploadFile(projectId, next.file, {
      ...uploadOptionsForTests,
      onProgress: p => update(next.id, { progress: p }),
    });
    tasks.current.set(next.id, task);
    task.promise.then(
      source => update(next.id, { state: 'done', source }),
      err => {
        if (err instanceof UploadCancelled) return;
        const code = err instanceof UploadError ? err.code : '';
        update(next.id, { state: 'failed', error: errorReason(err), permanent: PERMANENT_UPLOAD_ERRORS.has(code) });
      },
    ).finally(() => tasks.current.delete(next.id));
  }, [rows, projectId]);

  // leaving the page pauses the uploads: their sessions and resume keys stay, so picking the same files again resumes
  // them (U-5.3; UR, V2-8). Remove cancels one for good.
  useEffect(() => () => { for (const t of tasks.current.values()) t.pause(); }, []);

  const add = (files: FileList | File[] | null) => {
    if (!files) return;
    const list = [...files];
    const ok = list.filter(f => DRAWING_FILE.test(f.name));
    setRefused(list.filter(f => !DRAWING_FILE.test(f.name)).map(f => f.name));
    setRows(rs => [
      ...rs,
      ...ok.filter(f => !rs.some(r => r.file.name === f.name && r.file.size === f.size && r.file.lastModified === f.lastModified))
        .map(f => ({ id: nextRowId++, file: f, state: 'waiting' as const, progress: null, source: null, error: null, permanent: false })),
    ]);
  };
  const remove = (row: Row) => {
    const t = tasks.current.get(row.id);
    if (t) void t.cancel();
    setRows(rs => rs.filter(r => r.id !== row.id));
  };
  const retry = (row: Row) => update(row.id, { state: 'waiting', error: null });
  const onDrop = (e: DragEvent) => { e.preventDefault(); setDrag(false); add(e.dataTransfer?.files ?? null); };

  const done = rows.filter(r => r.state === 'done' && r.source);
  const ready = done.length > 0 && done.length === rows.length;
  const failed = rows.filter(r => r.state === 'failed');
  const reusable = latestFromUpload(latest, builds.data?.builds);
  const begin = async (body: NewBuildRequest, kind: 'build' | 'reuse') => {
    setStarting(kind);
    setStartError(null);
    try {
      const { data } = await createBuild({ path: { projectId }, body, throwOnError: true });
      void queryClient.invalidateQueries({ queryKey: listBuildsQueryKey({ path: { projectId } }) });
      navigate(`/projects/${projectId}/builds/${(data as BuildDetail).id}?step=files`);
    } catch (err) {
      setStartError(errorReason(err));
      setStarting(null);
    }
  };
  const sources = [...new Set(done.map(r => r.source!.sha1))];
  const from = fromBuild && BUILD_ID.test(fromBuild) ? { kind: 'build' as const, build: fromBuild } : undefined;

  return (
    <div className="min-h-svh bg-muted/30">
      <AppBar back className="sticky top-0" title={`${name} · upload drawings`} />
      <main className="mx-auto grid max-w-3xl gap-5 px-6 py-8" data-testid="upload-page">
        <div>
          <h1 className="text-xl font-semibold">Upload drawings</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {fromBuild ? 'Other files for the draft: its settings are taken over.' : 'DWG files, or DXF exported from AutoCAD; several at once (one per floor, or one sheet with every floor).'}
          </p>
        </div>

        <div
          className={cn('grid place-items-center gap-2 rounded-lg border-2 border-dashed bg-background px-6 py-10 text-center', drag && 'border-primary bg-primary/5')}
          onDragOver={e => { e.preventDefault(); setDrag(true); }}
          onDragLeave={() => setDrag(false)}
          onDrop={onDrop}
          data-testid="drop-zone"
        >
          <FileUp aria-hidden="true" className="size-8 text-muted-foreground" />
          <p className="text-sm">Drop .dwg or .dxf files here, or</p>
          <Button type="button" variant="outline" onClick={() => input.current?.click()}>Choose files</Button>
          <input
            ref={input}
            type="file"
            accept=".dwg,.dxf"
            multiple
            className="sr-only"
            data-testid="file-input"
            onChange={e => { add(e.target.files); e.target.value = ''; }}
          />
        </div>
        {refused.length > 0 && (
          <Alert variant="destructive" data-testid="upload-refused">
            <CircleAlert aria-hidden="true" />
            <AlertDescription>{`Only .dwg and .dxf files can be uploaded: ${refused.join(', ')}`}</AlertDescription>
          </Alert>
        )}

        {rows.length > 0 && (
          <ul className="grid gap-2" data-testid="upload-rows">
            {rows.map(r => {
              const pct = r.progress ? Math.round((r.progress.bytesDone / Math.max(1, r.progress.bytes)) * 100) : r.state === 'done' ? 100 : 0;
              return (
                <li key={r.id} className="grid gap-1.5 rounded-lg border bg-background p-3" data-testid="upload-row" data-name={r.file.name} data-state={r.state}>
                  <div className="flex items-center gap-2">
                    <span className="min-w-0 flex-1 truncate text-sm font-medium" data-testid="upload-name">{r.file.name}</span>
                    <span className="text-xs text-muted-foreground">{formatBytes(r.file.size)}</span>
                    {r.state === 'failed' && !r.permanent && (
                      <Button size="sm" variant="outline" className="h-7" onClick={() => retry(r)} data-testid="upload-retry"><RotateCw aria-hidden="true" />Retry</Button>
                    )}
                    <Button size="icon" variant="ghost" className="size-7" aria-label={`Remove ${r.file.name}`} onClick={() => remove(r)} data-testid="upload-remove"><Trash2 /></Button>
                  </div>
                  <Progress value={pct} data-testid="upload-progress" aria-label={`Upload of ${r.file.name}`} />
                  <p className="text-xs text-muted-foreground" data-testid="upload-status">
                    {r.state === 'waiting' && 'Waiting'}
                    {r.state === 'uploading' && (r.progress ? `Part ${r.progress.partsDone} of ${r.progress.parts} sent` : 'Starting...')}
                    {r.state === 'done' && 'Uploaded'}
                    {r.state === 'failed' && <span className="text-destructive" data-testid="upload-error">{`Not uploaded: ${r.error}`}</span>}
                  </p>
                </li>
              );
            })}
          </ul>
        )}

        {startError && (
          <Alert variant="destructive" data-testid="start-error"><CircleAlert aria-hidden="true" /><AlertDescription>{startError}</AlertDescription></Alert>
        )}
        <div className="flex flex-wrap items-center gap-3">
          <Button disabled={!ready || starting !== null} onClick={() => void begin({ sources, ...(from ? { from } : {}) }, 'build')} data-testid="start-build">
            <Upload aria-hidden="true" />
            {starting === 'build' ? 'Starting...' : sources.length ? `Continue with ${sources.length} file${sources.length === 1 ? '' : 's'}` : 'Continue'}
          </Button>
          {reusable && !fromBuild && (
            <Button variant="outline" disabled={starting !== null} onClick={() => void begin({ sources: null, from: { kind: 'version', version: latest } }, 'reuse')} data-testid="reuse-files">
              {`Use the files of v${latest} again`}
            </Button>
          )}
        </div>
        {failed.length > 0 && done.length > 0 && (
          <p className="text-sm text-muted-foreground" data-testid="remove-failed-hint">
            {`Remove the file${failed.length === 1 ? '' : 's'} that ${failed.length === 1 ? 'was' : 'were'} not uploaded to continue with the others.`}
          </p>
        )}

        {openDrafts.length > 0 && (
          <section className="grid gap-2" data-testid="open-drafts">
            <h2 className="text-sm font-semibold">Drafts not saved yet</h2>
            <ul className="grid gap-1 text-sm">
              {openDrafts.map(b => (
                <li key={b.id} className="flex items-center gap-2">
                  <span className="min-w-0 flex-1 truncate">{b.sourceNames.join(', ') || b.id}</span>
                  <Link className="underline" to={`/projects/${projectId}/builds/${b.id}`}>Continue</Link>
                </li>
              ))}
            </ul>
          </section>
        )}
      </main>
    </div>
  );
}
