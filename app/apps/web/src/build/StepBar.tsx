// The Build page's step bar (docs/upload/DESIGN.md U-2 screen 5): Files . Layers . Floors . Build . Check . Save, the
// current one marked; a step is reachable once its inputs exist (the others are shown, disabled, with the reason).
import { Check, ChevronRight } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { BuildDetail } from '@/upload/contracts';
import { reachable, STEP_LABELS, STEPS, type StepId } from './steps';

const WAIT_REASON: Record<StepId, string> = {
  files: '',
  layers: 'once the drawings are read',
  floors: 'once the drawings are read',
  build: 'once the drawings are read',
  check: 'once the draft is built',
  save: 'once the draft is built',
};

export function StepBar({ detail, current, onStep }: { detail: BuildDetail; current: StepId; onStep: (s: StepId) => void }) {
  return (
    <nav aria-label="Steps" data-testid="step-bar" className="flex flex-wrap items-center gap-1">
      {STEPS.map((step, i) => {
        const ok = reachable(step, detail);
        const here = step === current;
        const done = STEPS.indexOf(current) > i && ok;
        return (
          <div key={step} className="flex items-center gap-1">
            {i > 0 && <ChevronRight aria-hidden="true" className="size-3.5 text-muted-foreground/60" />}
            <button
              type="button"
              disabled={!ok}
              aria-current={here ? 'step' : undefined}
              data-testid={`step-${step}`}
              data-current={here ? '' : undefined}
              title={ok ? undefined : `Opens ${WAIT_REASON[step]}`}
              onClick={() => onStep(step)}
              className={cn(
                'inline-flex h-8 items-center gap-1.5 rounded-md px-3 text-sm font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-40',
                here ? 'bg-primary text-primary-foreground' : 'hover:bg-accent',
              )}
            >
              <span className="text-xs tabular-nums opacity-70">{i + 1}</span>
              {STEP_LABELS[step]}
              {done && <Check aria-hidden="true" className="size-3.5" />}
            </button>
          </div>
        );
      })}
    </nav>
  );
}
