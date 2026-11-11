// The line on the Floors, Build and Check steps that says which way the draft is built (docs/rooms/DESIGN.md R-1.3,
// R-12.6), read from the draft's options only (no date, no word "recipe"), with its one button when the draft is built
// the earlier way: "Use the new floor plates, ceilings and stairs" sets the three options in one saved change.
import { Layers } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import type { BuildSettings } from '@/upload/contracts';
import { useBuildContext } from './context';
import { RULES_EARLIER_TEXT, RULES_NEW_TEXT, rulesOf, setRules, USE_NEW_TEXT } from './settingsEdit';
import { TID } from './testids';

export function RulesLine({ settings, editable, className }: { settings: BuildSettings | null; editable: boolean; className?: string }) {
  const { change } = useBuildContext();
  if (!settings) return null;
  const rules = rulesOf(settings);
  return (
    <p className={cn('flex flex-wrap items-center gap-2 rounded-md border px-3 py-2 text-sm', rules === 'earlier' ? 'border-amber-300 bg-amber-50' : 'bg-background', className)}
      data-testid={TID.rulesLine} data-rules={rules}>
      <Layers aria-hidden="true" className="size-4 shrink-0 text-muted-foreground" />
      <span className="min-w-0 flex-1">{rules === 'new' ? RULES_NEW_TEXT : RULES_EARLIER_TEXT}</span>
      {rules === 'earlier' && (
        <Button size="sm" className="h-7" disabled={!editable} onClick={() => change(setRules('new'))} data-testid={TID.rulesUseNew}>
          {USE_NEW_TEXT}
        </Button>
      )}
    </p>
  );
}
