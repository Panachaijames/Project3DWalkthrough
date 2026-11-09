// Step "Files" (docs/upload/DESIGN.md U-2 5a, U-6.3, U-7.4): per source its name, size and kind, the conversion verdict
// (ok green, minor amber, loss red, failed), its notes, the layers whose counts differ, the blocks lost with their inserts
// (and the sheet with the lost inserts marked); the units: declared, the door votes, the verdict, a units select per
// source (enabled once the proposal is in: a change rescales and re-reads that source) and Confirm; "Start again with
// other files"; the advice to export a DXF from AutoCAD when the verdict is loss. Every name is drawing text: text only.
import { CircleAlert, FileWarning, RotateCcw } from 'lucide-react';
import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { PlanCanvas } from '@/plan';
import type { BuildSourceInfo, ConversionVerdict, Flag, Units } from '@/upload/contracts';
import { formatBytes } from '@/upload/upload';
import { cn } from '@/lib/utils';
import { formatNumber } from '@/lib/format';
import { useBuildContext, useConversion, useDrawing, usePlan } from './context';
import { NativeSelect } from './fields';
import { RunPanel } from './RunPanel';
import { confirmUnits, roleOf, setUnits, UNIT_NAMES, UNITS } from './settingsEdit';
import { LOSS_WARNING, proposalIn, readingNow } from './steps';

const VERDICT: Record<ConversionVerdict, { text: string; className: string }> = {
  ok: { text: 'ok', className: 'bg-emerald-600 text-white' },
  minor: { text: 'minor', className: 'bg-amber-500 text-white' },
  loss: { text: 'loss', className: 'bg-red-600 text-white' },
  failed: { text: 'failed', className: 'bg-red-800 text-white' },
  'not-converted': { text: 'DXF: not converted', className: 'bg-slate-500 text-white' },
};

export const CANNOT_SEE = 'The check compares what LibreDWG read with what it wrote: what the converter never read shows only as unknown '
  + 'objects and errors. A DXF exported from AutoCAD is the independent check.';

function VerdictBadge({ verdict }: { verdict: ConversionVerdict }) {
  const v = VERDICT[verdict];
  return <Badge className={cn('shrink-0', v.className)} data-testid="source-verdict" data-verdict={verdict}>{v.text}</Badge>;
}

function LostSheet({ src, flags }: { src: BuildSourceInfo; flags: Flag[] }) {
  const { settings } = useBuildContext();
  const { plan, loading } = usePlan(src);
  if (!plan) return loading ? <p className="text-xs text-muted-foreground">Loading the sheet...</p> : null;
  const roleOfIndex = (i: number) => (settings ? roleOf(settings, plan.layers[i] ?? '') : 'other');
  return (
    <div className="h-72 overflow-hidden rounded-md border bg-white" data-testid="lost-sheet">
      <PlanCanvas plan={plan} roleOf={roleOfIndex} flags={flags} selected={new Set()} setAside={new Set()} tool="pan" />
    </div>
  );
}

function SourceCard({ src, index }: { src: BuildSourceInfo; index: number }) {
  const { settings, change, editable, detail } = useBuildContext();
  const conversion = useConversion(src);
  const drawing = useDrawing(src);
  const [showSheet, setShowSheet] = useState(false);
  const setting = settings?.sources.find(s => s.sha1 === src.sha1) ?? null;
  const report = conversion.data;
  const votes = drawing.data?.units.votes;
  const lostFlags = useMemo<Flag[]>(() => (report?.lostBlocks ?? []).flatMap((b, bi) => b.inserts.map((ins, ii) => ({
    id: `lost:${index}:${bi}:${ii}`, kind: 'lost' as const, floor: null, severity: 'check' as const,
    title: b.name, detail: `${formatNumber(b.entities)} items lost`, at: [ins.x, ins.y] as [number, number], bbox: null, ref: {},
  }))), [report, index]);
  const reread = readingNow(detail.run)?.only?.includes(src.sha1) ?? false;
  const unitsDisabled = !editable || !proposalIn(detail) || !setting;

  return (
    <article className="grid gap-3 rounded-lg border bg-background p-4" data-testid="source-card" data-sha1={src.sha1}>
      <header className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0">
          <h3 className="truncate text-sm font-semibold" data-testid="source-name">{src.name}</h3>
          <p className="text-xs text-muted-foreground" data-testid="source-meta">
            {formatBytes(src.bytes)} · {src.kind.toUpperCase()}
          </p>
        </div>
        {src.conversion ? <VerdictBadge verdict={src.conversion.verdict} /> : <Badge variant="secondary">{reread || readingNow(detail.run) ? 'Reading...' : 'Not read yet'}</Badge>}
      </header>

      {src.conversion && src.conversion.notes.length > 0 && (
        <ul className="grid gap-1 text-sm" data-testid="source-notes">
          {src.conversion.notes.map((n, i) => <li key={i}>{n}</li>)}
        </ul>
      )}

      {src.conversion?.verdict === 'loss' && (
        <Alert variant="destructive" data-testid="loss-advice">
          <FileWarning aria-hidden="true" />
          <AlertTitle>Parts of the drawing were lost in conversion</AlertTitle>
          <AlertDescription>
            <p>{`${formatNumber(src.conversion.lostInModelSpace)} items did not come through. ${LOSS_WARNING[0]!.toUpperCase()}${LOSS_WARNING.slice(1)}.`}</p>
            <p className="mt-1">You can still build: the lost parts are left out.</p>
          </AlertDescription>
        </Alert>
      )}

      {report && report.byLayer.length > 0 && (
        <details className="text-sm" data-testid="layer-differences">
          <summary className="cursor-pointer text-muted-foreground">{`Layers whose counts differ (${report.byLayer.length})`}</summary>
          <table className="mt-2 w-full text-xs">
            <thead><tr className="text-left text-muted-foreground"><th className="font-medium">Layer</th><th className="font-medium">In the DWG</th><th className="font-medium">In the DXF</th></tr></thead>
            <tbody>
              {report.byLayer.map((l, i) => (
                <tr key={i} data-testid="layer-difference"><td className="pr-2">{l.layer || '(no name)'}</td><td>{formatNumber(l.dwg)}</td><td>{formatNumber(l.dxf)}</td></tr>
              ))}
            </tbody>
          </table>
        </details>
      )}

      {report && report.lostBlocks.length > 0 && (
        <div className="grid gap-2 text-sm" data-testid="lost-blocks">
          <p className="font-medium">{`Blocks lost (${report.lostBlocks.length})`}</p>
          <ul className="grid gap-0.5 text-xs">
            {report.lostBlocks.slice(0, 50).map((b, i) => (
              <li key={i} data-testid="lost-block">
                <span className="font-mono">{b.name}</span>
                {` · ${formatNumber(b.entities)} items · ${b.inserts.length === 0 ? 'not placed on the sheet' : `placed ${b.inserts.length} time${b.inserts.length === 1 ? '' : 's'} on the sheet`}`}
              </li>
            ))}
          </ul>
          {lostFlags.length > 0 && (
            <div>
              <Button size="sm" variant="outline" onClick={() => setShowSheet(v => !v)} data-testid="show-lost-sheet">
                {showSheet ? 'Hide the sheet' : 'Show where they are on the sheet'}
              </Button>
              {showSheet && <div className="mt-2"><LostSheet src={src} flags={lostFlags} /></div>}
            </div>
          )}
        </div>
      )}
      {report && report.verdict !== 'not-converted' && <p className="text-xs text-muted-foreground">{CANNOT_SEE}</p>}

      {src.units && (
        <div className="grid gap-2 rounded-md bg-muted/40 p-3 text-sm" data-testid="units-info">
          <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
            <span>{`Declared: ${src.units.declared ? UNIT_NAMES[src.units.declared] : 'none'}`}</span>
            {votes && (
              <span data-testid="units-votes">
                {'Door votes: '}
                {UNITS.filter(u => votes[u] > 0).map(u => `${u} ${votes[u]}`).join(', ') || 'none'}
              </span>
            )}
            <span data-testid="units-verdict" data-verdict={src.units.verdict}>{`Verdict: ${src.units.verdict}`}</span>
          </div>
          {src.units.note && <p className="text-xs" data-testid="units-note">{src.units.note}</p>}
          <div className="flex flex-wrap items-center gap-2">
            <label className="text-xs font-medium text-muted-foreground" htmlFor={`units-${index}`}>Units</label>
            <NativeSelect
              id={`units-${index}`}
              data-testid="units-select"
              disabled={unitsDisabled}
              value={setting?.units ?? src.units.used}
              onChange={e => change(setUnits(src.sha1, e.target.value as Units))}
            >
              {UNITS.map(u => <option key={u} value={u}>{UNIT_NAMES[u]}</option>)}
            </NativeSelect>
            {setting && !setting.unitsConfirmed && (
              <Button size="sm" disabled={unitsDisabled} onClick={() => change(confirmUnits(src.sha1))} data-testid="units-confirm">
                Confirm {setting.units ? UNIT_NAMES[setting.units] : ''}
              </Button>
            )}
            {setting?.unitsConfirmed && <span className="text-xs text-emerald-700" data-testid="units-confirmed">Confirmed</span>}
            {!proposalIn(detail) && <span className="text-xs text-muted-foreground">Reading the drawings...</span>}
          </div>
          {reread && <p className="text-xs font-medium" data-testid="units-rereading">Reading this drawing again in its new units...</p>}
        </div>
      )}
    </article>
  );
}

export function FilesStep() {
  const { detail, projectId, buildId } = useBuildContext();
  const navigate = useNavigate();
  const run = detail.run;
  const preparing = run && run.kind === 'prepare' ? run : null;
  return (
    <div className="grid gap-4" data-testid="files-step">
      {preparing && (preparing.status !== 'done' || !proposalIn(detail)) && <RunPanel run={preparing} />}
      {!proposalIn(detail) && preparing?.status === 'done' && (
        <p className="text-sm text-muted-foreground">Reading the drawings... the layer roles and floors are being proposed.</p>
      )}
      {detail.sources.map((src, i) => <SourceCard key={src.sha1} src={src} index={i} />)}
      {detail.status === 'open' && (
        <div className="flex flex-wrap items-center gap-3">
          <Button variant="outline" onClick={() => navigate(`/projects/${projectId}/builds/new?from=${encodeURIComponent(buildId)}`)} data-testid="start-again">
            <RotateCcw aria-hidden="true" />
            Start again with other files
          </Button>
          <span className="text-xs text-muted-foreground">A new draft with these settings; this one stays in the Drafts list.</span>
        </div>
      )}
      {preparing?.status === 'failed' && (
        <Alert variant="destructive">
          <CircleAlert aria-hidden="true" />
          <AlertTitle>The drawings could not be read</AlertTitle>
          <AlertDescription>Start again with other files (a DXF exported from AutoCAD reads without conversion).</AlertDescription>
        </Alert>
      )}
    </div>
  );
}
