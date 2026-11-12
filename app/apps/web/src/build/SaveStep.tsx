// Step "Save" (docs/upload/DESIGN.md U-2 5f, U-11.1, U-8.4): the label (default `<d Mon yyyy>: built from <file names>`),
// what will be saved (counts, flags left, the stamp), "carry the furniture heights of v<n>" (ticked), "remember these
// layer roles for <office>" (ticked; hidden with no office, and an office select offered). Save (saveBuild) is disabled
// while the request is in flight (a double click makes one version; the API answers 409 build_saved to a second) and
// leads to the new version's page.
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Save } from 'lucide-react';
import { useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { Input } from '@/components/ui/input';
import { ApiError } from '@/api/client';
import { getProjectQueryKey, listBuildsQueryKey, listOfficesOptions, listProjectsQueryKey } from '@/api/generated/@tanstack/react-query.gen';
import { saveBuild } from '@/api/generated/sdk.gen';
import type { BuildOverlay } from '@/upload/contracts';
import { rawQueryOptions } from '@/upload/raw';
import { errorReason, formatDate, formatNumber } from '@/lib/format';
import { useBuildContext } from './context';
import { OfficeSelect } from './OfficeSelect';
import { RoomCounts } from './RoomsPanels';
import { setOffice } from './settingsEdit';

/** The default label (U-2 5f): '4 Nov 2026: built from I1201.dwg, I1202.dwg'. */
export function defaultLabel(names: readonly string[], when: Date = new Date()): string {
  return `${formatDate(when.toISOString())}: built from ${names.join(', ')}`.slice(0, 200);
}

/** RR (S10): counts.rooms is the model's room names (the upload milestone's count), not the rooms closed of the table
 *  below it: '9 room names'. */
export const roomNamesText = (n: number) => `${formatNumber(n)} room name${n === 1 ? '' : 's'}`;

export function SaveStep() {
  const { detail, settings, project, projectId, buildId, change, editable, saverState } = useBuildContext();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const offices = useQuery(listOfficesOptions());
  // rooms milestone: the three counts per floor, from the overlay (R5.md D-3)
  const overlay = useQuery(rawQueryOptions<BuildOverlay>(detail.result?.urls.overlay, detail.result?.runId ?? ''));
  const [label, setLabel] = useState(() => defaultLabel(detail.sourceNames));
  const [carry, setCarry] = useState(true);
  const [remember, setRemember] = useState(true);
  const [inFlight, setInFlight] = useState(false);
  /** Set at once (a second click in the same frame sees it): one request per Save. */
  const sending = useRef(false);
  const [error, setError] = useState<string | null>(null);
  const result = detail.result;
  const latest = project?.latestVersion ?? 0;
  const office = settings?.office ?? null;
  const officeName = offices.data?.offices.find(o => o.id === office)?.name ?? office;
  const active = detail.run && (detail.run.status === 'queued' || detail.run.status === 'running');
  const pendingSettings = saverState?.status === 'saving' || saverState?.status === 'pending';

  if (detail.status === 'saved') {
    return (
      <div className="grid gap-2" data-testid="save-step" data-saved="">
        <p className="text-sm">{`This draft was saved as v${detail.savedVersion}.`}</p>
        <Link className="text-sm underline" to={`/projects/${projectId}/v/${detail.savedVersion}`} data-testid="saved-version-link">{`Open v${detail.savedVersion}`}</Link>
      </div>
    );
  }
  if (!result) return <p className="text-sm text-muted-foreground" data-testid="save-step">Build the draft first.</p>;

  const blocked = result.stale || !!active || pendingSettings || !label.trim() || label.length > 200;
  const save = async () => {
    if (sending.current) return;
    sending.current = true;
    setInFlight(true);
    setError(null);
    try {
      const { data } = await saveBuild({
        path: { projectId, buildId },
        body: { label: label.trim(), carryHeights: latest >= 1 ? carry : false, rememberMapping: office ? remember : false },
        throwOnError: true,
      });
      void queryClient.invalidateQueries({ queryKey: listProjectsQueryKey() });
      void queryClient.invalidateQueries({ queryKey: getProjectQueryKey({ path: { projectId } }) });
      void queryClient.invalidateQueries({ queryKey: listBuildsQueryKey({ path: { projectId } }) });
      navigate(`/projects/${projectId}/v/${data.version}`);
    } catch (err) {
      if (err instanceof ApiError && err.status === 409 && err.code === 'build_saved') {
        const v = (err.details as { version?: unknown } | null)?.version;
        if (typeof v === 'number') {
          void queryClient.invalidateQueries({ queryKey: getProjectQueryKey({ path: { projectId } }) });
          navigate(`/projects/${projectId}/v/${v}`);
          return;
        }
      }
      setError(errorReason(err));
      sending.current = false;
      setInFlight(false);
    }
  };

  return (
    <div className="grid max-w-2xl gap-4" data-testid="save-step">
      <div className="grid gap-1">
        <label htmlFor="save-label" className="text-xs font-medium text-muted-foreground">Label</label>
        <Input id="save-label" value={label} maxLength={200} onChange={e => setLabel(e.target.value)} data-testid="save-label" />
      </div>
      <section className="grid gap-1 rounded-lg border bg-background p-4 text-sm" data-testid="save-summary">
        <p className="font-semibold">What will be saved</p>
        <p data-testid="save-counts">{`${formatNumber(result.counts.floors)} floor${result.counts.floors === 1 ? '' : 's'}, ${formatNumber(result.counts.parts)} parts, ${formatNumber(result.counts.openings)} openings, ${formatNumber(result.counts.furniture)} furniture pieces, ${roomNamesText(result.counts.rooms)}`}</p>
        <p data-testid="save-flags">{result.flags.check ? `${formatNumber(result.flags.check)} flags left to check (of ${formatNumber(result.flags.total)})` : 'No flags left to check'}</p>
        <p>Model-data stamp <span className="font-mono" data-testid="save-stamp">{result.stamp}</span></p>
        <RoomCounts overlay={overlay.data} result={result} />
      </section>
      {latest >= 1 && (
        <label className="flex items-center gap-2 text-sm">
          <Checkbox checked={carry} onCheckedChange={v => setCarry(v === true)} data-testid="carry-heights" />
          {`Carry the furniture heights of v${latest}`}
        </label>
      )}
      {office ? (
        <label className="flex items-center gap-2 text-sm" data-testid="remember-field">
          <Checkbox checked={remember} onCheckedChange={v => setRemember(v === true)} data-testid="remember-mapping" />
          {`Remember these layer roles for ${officeName}`}
        </label>
      ) : (
        <div className="grid gap-1" data-testid="save-office">
          <OfficeSelect mode="settings" disabled={!editable} value={{ office: null, newOfficeName: null }} onChange={v => change(setOffice(v.office))} />
          <p className="text-xs text-muted-foreground">With an office, its layer roles are remembered for its next drawings.</p>
        </div>
      )}
      {result.stale && (
        <Alert data-testid="save-stale"><AlertDescription>The settings changed since the last build: build again before saving.</AlertDescription></Alert>
      )}
      {error && <Alert variant="destructive" data-testid="save-error"><AlertDescription>{error}</AlertDescription></Alert>}
      <div>
        <Button disabled={blocked || inFlight} onClick={() => void save()} data-testid="save-build" data-in-flight={inFlight ? '' : undefined}>
          <Save aria-hidden="true" />
          {inFlight ? 'Saving...' : 'Save as a new version'}
        </Button>
      </div>
    </div>
  );
}
