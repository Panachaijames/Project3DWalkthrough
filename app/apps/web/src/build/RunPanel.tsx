// A run of the build as it goes (docs/upload/DESIGN.md U-2 5d, U-3.4): its steps with their status and seconds, a
// progress bar, the last messages, "Stopping..." while a cancel is asked (Cancel disabled meanwhile), and a failed run's
// error with what to change. Messages are plain sentences from the worker: shown as text.
import { CircleAlert, CircleCheck, CircleDashed, CircleX, LoaderCircle, Square } from 'lucide-react';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import type { RunInfo } from '@/upload/contracts';
import { errorAdvice } from './steps';

const STATUS_TEXT: Record<RunInfo['status'], string> = {
  queued: 'Waiting for another build to finish',
  running: 'Running',
  done: 'Done',
  failed: 'Failed',
  cancelled: 'Cancelled',
  interrupted: 'Stopped (interrupted)',
};

function StepIcon({ status }: { status: RunInfo['steps'][number]['status'] }) {
  switch (status) {
    case 'running': return <LoaderCircle aria-hidden="true" className="size-4 animate-spin text-primary" />;
    case 'done': return <CircleCheck aria-hidden="true" className="size-4 text-emerald-600" />;
    case 'failed': return <CircleX aria-hidden="true" className="size-4 text-destructive" />;
    default: return <CircleDashed aria-hidden="true" className="size-4 text-muted-foreground/60" />;
  }
}

export interface RunPanelProps {
  run: RunInfo;
  /** Cancel is offered (the Build step, and the Files step's reading: UR, V2-4); null hides it. */
  onCancel?: (() => void) | null;
  cancelling?: boolean;
  title?: string;
}

export function RunPanel({ run, onCancel = null, cancelling = false, title }: RunPanelProps) {
  const active = run.status === 'queued' || run.status === 'running';
  const stopping = active && run.cancelRequested;
  const messages = run.messages.slice(-8);
  return (
    <section className="grid gap-3 rounded-lg border bg-background p-4" data-testid="run-panel" data-status={run.status} data-kind={run.kind}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h3 className="text-sm font-semibold">{title ?? (run.kind === 'prepare' ? 'Reading the drawings' : 'Building')}</h3>
          <p className="text-xs text-muted-foreground" data-testid="run-status">
            {stopping ? 'Stopping...' : STATUS_TEXT[run.status]}
          </p>
        </div>
        {onCancel && active && (
          <Button size="sm" variant="outline" disabled={stopping || cancelling} onClick={onCancel} data-testid="cancel-run">
            <Square aria-hidden="true" />
            {stopping ? 'Stopping...' : 'Cancel'}
          </Button>
        )}
      </div>
      {stopping && <p className="text-sm font-medium" data-testid="run-stopping">Stopping...</p>}
      <Progress value={Math.round(Math.max(0, Math.min(1, run.progress)) * 100)} data-testid="run-progress" aria-label="Progress" />
      <ol className="grid gap-1 text-sm">
        {run.steps.map(s => (
          <li key={s.name} className="flex items-center gap-2" data-testid="run-step" data-step={s.name} data-status={s.status}>
            <StepIcon status={s.status} />
            <span className="min-w-0 flex-1 truncate">{s.label}</span>
            {s.seconds !== null && <span className="text-xs tabular-nums text-muted-foreground">{s.seconds.toFixed(1)} s</span>}
            {s.note && <span className="text-xs text-muted-foreground">{s.note}</span>}
          </li>
        ))}
      </ol>
      {messages.length > 0 && (
        <ul className="grid gap-0.5 rounded-md bg-muted/50 p-2 font-mono text-xs" data-testid="run-messages">
          {messages.map((m, i) => (
            <li key={`${m.at}-${i}`} className={m.level === 'error' ? 'text-destructive' : m.level === 'warn' ? 'text-amber-700' : undefined}>{m.text}</li>
          ))}
        </ul>
      )}
      {run.error && run.status !== 'done' && (
        <Alert variant="destructive" data-testid="run-error" data-code={run.error.code}>
          <CircleAlert aria-hidden="true" />
          <AlertTitle>{run.status === 'cancelled' ? 'Cancelled' : 'The run did not finish'}</AlertTitle>
          <AlertDescription>
            <p data-testid="run-error-message">{run.error.message}</p>
            <p className="mt-1" data-testid="run-advice">{errorAdvice(run.error.code, run.kind)}</p>
          </AlertDescription>
        </Alert>
      )}
    </section>
  );
}
