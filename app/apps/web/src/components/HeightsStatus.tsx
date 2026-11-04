// The heights status in the app bar (DESIGN.md 15.3, 15.5): `Heights saved`, `Saving…`, or `Not saved: <reason>` with
// Retry. The page hides it when the model has no furniture.
import { Check, LoaderCircle, TriangleAlert } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { HEIGHTS_SAVED, HEIGHTS_SAVING, heightsNotSaved } from '@/lib/format';
import type { SaverState } from '@/lib/useHeightsSaver';

export function HeightsStatus({ state, onRetry }: { state: SaverState; onRetry: () => void }) {
  const text = state.status === 'saved' ? HEIGHTS_SAVED
    : state.status === 'saving' ? HEIGHTS_SAVING
      : heightsNotSaved(state.reason ?? 'unknown error');
  return (
    <div
      role="status"
      aria-live="polite"
      data-testid="heights-status"
      data-state={state.status}
      className="flex max-w-80 items-center gap-1.5 text-sm"
    >
      {state.status === 'saved' && <Check className="size-4 shrink-0 text-emerald-600" aria-hidden="true" />}
      {state.status === 'saving' && <LoaderCircle className="size-4 shrink-0 animate-spin text-muted-foreground" aria-hidden="true" />}
      {state.status === 'error' && <TriangleAlert className="size-4 shrink-0 text-destructive" aria-hidden="true" />}
      <span
        data-testid="heights-status-text"
        title={text}
        className={state.status === 'error' ? 'truncate text-destructive' : 'truncate text-muted-foreground'}
      >
        {text}
      </span>
      {state.status === 'error' && (
        <Button size="xs" variant="outline" onClick={onRetry} data-testid="heights-retry">
          Retry
        </Button>
      )}
    </div>
  );
}
