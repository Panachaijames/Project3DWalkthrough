// /projects/new (docs/upload/DESIGN.md U-2 screen 2, U-13.3, U-14.1): name, short name, project no, office (the known
// offices + "New office..."), id (derived from the name as the API would, editable; at most 40 characters for a new
// project, U-4.1). createProject, then the Upload screen. Errors inline: an id taken (409 project_exists) offers the
// next free id the API suggests; a refused id or name (422 bad_project) shows the API's reason.
import { useQueryClient, type QueryClient } from '@tanstack/react-query';
import { CircleAlert } from 'lucide-react';
import { useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router';
import { AppBar } from '@/components/AppBar';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { ApiError } from '@/api/client';
import { listOfficesOptions, listProjectsQueryKey } from '@/api/generated/@tanstack/react-query.gen';
import { createProject } from '@/api/generated/sdk.gen';
import { OfficeSelect, type OfficeChoice } from '@/build/OfficeSelect';
import { APP_NAME, errorReason } from '@/lib/format';
import { projectIdProblem, slugify } from '@/lib/slug';
import { useDocumentTitle } from '@/lib/useDocumentTitle';

export const newProjectTitle = () => `New project · ${APP_NAME}`;

export function newProjectLoader(queryClient: QueryClient) {
  return () => {
    void queryClient.ensureQueryData(listOfficesOptions()).catch(() => undefined);   // the select shows its own error
    return null;
  };
}

export function NewProjectPage() {
  useDocumentTitle(newProjectTitle());
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [name, setName] = useState('');
  const [shortName, setShortName] = useState('');
  const [projectNo, setProjectNo] = useState('');
  const [office, setOffice] = useState<OfficeChoice>({ office: null, newOfficeName: null });
  const [id, setId] = useState('');
  const [idTouched, setIdTouched] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [suggested, setSuggested] = useState<string | null>(null);
  const [tried, setTried] = useState(false);

  const shownId = idTouched ? id : slugify(name);
  const idProblem = projectIdProblem(shownId);
  const nameProblem = !name.trim() ? 'a project needs a name' : name.length > 200 ? 'at most 200 characters' : null;
  const officeProblem = office.office === null && office.newOfficeName !== null && !office.newOfficeName.trim() ? 'type the new office\'s name' : null;

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setTried(true);
    if (nameProblem || idProblem || officeProblem || busy) return;
    setBusy(true);
    setError(null);
    setSuggested(null);
    try {
      const { data } = await createProject({
        body: {
          name: name.trim(),
          shortName: shortName.trim() || null,
          projectNo: projectNo.trim() || null,
          office: office.office,
          newOfficeName: office.office ? null : office.newOfficeName?.trim() || null,
          id: shownId || null,
        },
        throwOnError: true,
      });
      void queryClient.invalidateQueries({ queryKey: listProjectsQueryKey() });
      navigate(`/projects/${data.id}/builds/new`);
    } catch (err) {
      if (err instanceof ApiError && err.status === 409 && err.code === 'project_exists') {
        const s = (err.details as { suggested?: unknown } | null)?.suggested;
        setSuggested(typeof s === 'string' ? s : null);
      }
      setError(errorReason(err));
      setBusy(false);
    }
  };

  return (
    <div className="min-h-svh bg-muted/30">
      <AppBar back className="sticky top-0" title="New project" />
      <main className="mx-auto max-w-xl px-6 py-10" data-testid="new-project-page">
        <h1 className="text-xl font-semibold">New project</h1>
        <p className="mt-1 text-sm text-muted-foreground">Name the project, then upload its drawings.</p>
        <form className="mt-6 grid gap-4" onSubmit={e => void submit(e)} noValidate>
          <div className="grid gap-1.5">
            <Label htmlFor="np-name">Name</Label>
            <Input id="np-name" value={name} onChange={e => setName(e.target.value)} aria-invalid={tried && !!nameProblem || undefined} data-testid="np-name" autoFocus />
            {tried && nameProblem && <p className="text-xs text-destructive" data-testid="np-name-error">{nameProblem}</p>}
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="grid gap-1.5">
              <Label htmlFor="np-short">Short name</Label>
              <Input id="np-short" value={shortName} placeholder={name || 'as the name'} onChange={e => setShortName(e.target.value)} data-testid="np-short-name" />
            </div>
            <div className="grid gap-1.5">
              <Label htmlFor="np-no">Project no</Label>
              <Input id="np-no" value={projectNo} onChange={e => setProjectNo(e.target.value)} data-testid="np-project-no" />
            </div>
          </div>
          <OfficeSelect value={office} onChange={setOffice} />
          {tried && officeProblem && <p className="-mt-3 text-xs text-destructive">{officeProblem}</p>}
          <div className="grid gap-1.5">
            <Label htmlFor="np-id">Id</Label>
            <Input
              id="np-id"
              value={shownId}
              onChange={e => { setIdTouched(true); setId(e.target.value); setSuggested(null); }}
              aria-invalid={!!idProblem || undefined}
              className="font-mono"
              data-testid="np-id"
            />
            {idProblem
              ? <p className="text-xs text-destructive" data-testid="np-id-error">{`The id: ${idProblem}.`}</p>
              : <p className="text-xs text-muted-foreground">{shownId ? `The project's address: /projects/${shownId}` : 'Made from the name; for a name with no Latin letters the API chooses one.'}</p>}
          </div>
          {error && (
            <Alert variant="destructive" data-testid="np-error">
              <CircleAlert aria-hidden="true" />
              <AlertDescription>
                <p>{error}</p>
                {suggested && (
                  <Button type="button" size="sm" variant="outline" className="mt-2" onClick={() => { setIdTouched(true); setId(suggested); setError(null); setSuggested(null); }} data-testid="np-use-suggested">
                    {`Use ${suggested}`}
                  </Button>
                )}
              </AlertDescription>
            </Alert>
          )}
          <div className="flex gap-2">
            <Button type="submit" disabled={busy || (tried && !!(nameProblem || officeProblem)) || !!idProblem} data-testid="np-create">
              {busy ? 'Creating...' : 'Create and upload drawings'}
            </Button>
            <Button type="button" variant="ghost" onClick={() => navigate('/projects')}>Cancel</Button>
          </div>
        </form>
      </main>
    </div>
  );
}
