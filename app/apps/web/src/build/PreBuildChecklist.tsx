// The pre-build checklist (docs/upload/DESIGN.md U-14.3), on the Build step before Build is enabled: each line links to
// the step that fixes it: units not confirmed; the Layers step not seen; a floor with no wall height; a floor with no
// source or an empty area; a source still being read again; a conversion loss (a warning, never a block); the rooms
// milestone's warning line when the draft is built the earlier way (TID.checklistRules, R-12.6).
import { CircleCheck, CircleX, TriangleAlert } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { RULES_ITEM, STEP_LABELS, type ChecklistItem, type StepId } from './steps';
import { TID } from './testids';

export function PreBuildChecklist({ items, onStep }: { items: ChecklistItem[]; onStep: (s: StepId) => void }) {
  const blocking = items.filter(i => i.level === 'block');
  return (
    <section className="grid gap-2 rounded-lg border bg-background p-4" data-testid="prebuild-checklist" data-clear={blocking.length ? undefined : ''}>
      <h3 className="text-sm font-semibold">Before building</h3>
      {!blocking.length && (
        <p className="flex items-center gap-2 text-sm text-emerald-700" data-testid="checklist-clear">
          <CircleCheck aria-hidden="true" className="size-4" />
          Everything needed is set.
        </p>
      )}
      {items.length > 0 && (
        <ul className="grid gap-1">
          {items.map(item => (
            <li key={item.id} className="flex flex-wrap items-center gap-2 text-sm" data-testid={item.id === RULES_ITEM ? TID.checklistRules : 'checklist-item'}
              data-level={item.level} data-id={item.id}>
              {item.level === 'block'
                ? <CircleX aria-hidden="true" className="size-4 text-destructive" />
                : <TriangleAlert aria-hidden="true" className="size-4 text-amber-600" />}
              <span className="min-w-0 flex-1">{item.text}</span>
              <Button size="sm" variant="link" className="h-auto p-0" onClick={() => onStep(item.step)} data-testid="checklist-link">
                {`Go to ${STEP_LABELS[item.step]}`}
              </Button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
