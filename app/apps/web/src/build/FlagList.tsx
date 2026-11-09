// The Check step's flag list (docs/upload/DESIGN.md U-12.2, U-12.3): every flag of the floor with its severity, title and
// detail (drawing text: shown as text), and what can be done from it: show it on the plan, select the items it is about,
// edit an opening, accept or refuse an outline suggestion (wall / glass / refuse), give a grey furniture family a kind.
import { Crosshair, MousePointerClick, PencilLine } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import type { Flag, FlagKind, OutlineEdgeFix } from '@/upload/contracts';
import { cn } from '@/lib/utils';

export const FLAG_KIND_TEXT: Record<FlagKind, string> = {
  opening: 'Opening to check',
  'single-line': 'Single line',
  lost: 'Lost in conversion',
  'outline-wall': 'Suggested wall',
  'outline-glass': 'Suggested glass',
  'grey-furniture': 'Furniture of no known kind',
  'rail-left-out': 'Railing left out',
  'room-label': 'Room label',
  'plate-dropped': 'Floor plate dropped',
  alignment: 'Alignment',
  units: 'Units',
  'fix-unmatched': 'A fix that matched nothing',
  'detector-skipped': 'Detector rule skipped',
  slow: 'Slow floor',
};

export interface FlagListProps {
  flags: Flag[];
  /** The outline fix already set for a flag's edge, if any. */
  outlineOf?: (flag: Flag) => OutlineEdgeFix['as'] | null;
  disabled?: boolean;
  activeId?: string | null;
  onShow?: (flag: Flag) => void;
  onSelectKeys?: (keys: string[]) => void;
  onOpening?: (openingId: string) => void;
  onOutline?: (flag: Flag, as: OutlineEdgeFix['as']) => void;
  onFamily?: (family: string) => void;
}

export function FlagList({ flags, outlineOf, disabled, activeId, onShow, onSelectKeys, onOpening, onOutline, onFamily }: FlagListProps) {
  if (!flags.length) return <p className="text-sm text-muted-foreground" data-testid="flag-list-empty">No flags on this floor.</p>;
  const ordered = [...flags].sort((a, b) => (a.severity === b.severity ? 0 : a.severity === 'check' ? -1 : 1));
  return (
    <ul className="grid gap-1.5" data-testid="flag-list">
      {ordered.map(f => {
        const outline = (f.kind === 'outline-wall' || f.kind === 'outline-glass') && f.ref.edge ? outlineOf?.(f) ?? null : null;
        return (
          <li
            key={f.id}
            className={cn('grid gap-1 rounded-md border bg-background p-2 text-sm', activeId === f.id && 'ring-2 ring-primary/40')}
            data-testid="flag"
            data-kind={f.kind}
            data-id={f.id}
            data-severity={f.severity}
          >
            <div className="flex items-start gap-2">
              <Badge variant={f.severity === 'check' ? 'default' : 'secondary'} className="shrink-0">{f.severity === 'check' ? 'check' : 'info'}</Badge>
              <div className="min-w-0 flex-1">
                <p className="text-xs text-muted-foreground">{FLAG_KIND_TEXT[f.kind] ?? f.kind}</p>
                <p className="font-medium" data-testid="flag-title">{f.title}</p>
                {f.detail && <p className="text-xs text-muted-foreground" data-testid="flag-detail">{f.detail}</p>}
              </div>
            </div>
            <div className="flex flex-wrap gap-1">
              {(f.at || f.bbox) && onShow && (
                <Button size="sm" variant="ghost" className="h-7" onClick={() => onShow(f)} data-testid="flag-show"><Crosshair aria-hidden="true" />Show</Button>
              )}
              {f.ref.keys && f.ref.keys.length > 0 && onSelectKeys && (
                <Button size="sm" variant="ghost" className="h-7" onClick={() => onSelectKeys(f.ref.keys!)} data-testid="flag-select">
                  <MousePointerClick aria-hidden="true" />
                  {`Select ${f.ref.keys.length === 1 ? 'the item' : `${f.ref.keys.length} items`}`}
                </Button>
              )}
              {f.ref.openingId && onOpening && (
                <Button size="sm" variant="ghost" className="h-7" onClick={() => onOpening(f.ref.openingId!)} data-testid="flag-opening"><PencilLine aria-hidden="true" />Edit the opening</Button>
              )}
              {(f.kind === 'outline-wall' || f.kind === 'outline-glass') && f.ref.edge && onOutline && (
                <span className="flex flex-wrap items-center gap-1" data-testid="flag-outline" data-as={outline ?? undefined}>
                  {(['wall', 'glass', 'none'] as const).map(as => (
                    <Button key={as} size="sm" className="h-7" variant={outline === as ? 'default' : 'outline'} disabled={disabled}
                      onClick={() => onOutline(f, as)} data-testid={`outline-${as === 'none' ? 'refuse' : as}`}>
                      {as === 'wall' ? 'Wall' : as === 'glass' ? 'Glass' : 'Refuse'}
                    </Button>
                  ))}
                </span>
              )}
              {f.kind === 'grey-furniture' && f.ref.family && onFamily && (
                <Button size="sm" variant="ghost" className="h-7" onClick={() => onFamily(f.ref.family!)} data-testid="flag-family">Give it a kind</Button>
              )}
            </div>
          </li>
        );
      })}
    </ul>
  );
}
