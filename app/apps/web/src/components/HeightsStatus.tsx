// The heights status in the app bar (DESIGN.md 15.3, 15.5): `Furniture saved` (step BX: it was `Heights saved`; the save
// carries the deleted boxes too), `Saving…`, or `Not saved: <reason>` with Retry. The page hides it when the model has no
// furniture. Beside it, its own element (step BX, docs/boxes/DESIGN.md 6.2): the count of the deleted furniture boxes,
// '· 3 boxes deleted', nothing at 0, so a colleague opening the version sees that boxes were taken out.
import { Check, LoaderCircle, TriangleAlert } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { boxesDeletedText, boxesDeletedTitle, HEIGHTS_SAVED, HEIGHTS_SAVING, heightsNotSaved } from '@/lib/format';
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

/** The count of the deleted furniture boxes of the version on screen (step BX): '· 3 boxes deleted'; nothing at 0. */
export function BoxesDeleted({ count }: { count: number }) {
  if (count <= 0) return null;
  return (
    <span data-testid="boxes-deleted" title={boxesDeletedTitle(count)} className="shrink-0 whitespace-nowrap text-sm text-muted-foreground">
      {boxesDeletedText(count)}
    </span>
  );
}
