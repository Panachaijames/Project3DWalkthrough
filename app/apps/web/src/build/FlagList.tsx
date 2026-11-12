// The Check step's flag list (docs/upload/DESIGN.md U-12.2, U-12.3): every flag of the floor with its severity, title and
// detail (drawing text: shown as text), and what can be done from it: show it on the plan, select the items it is about,
// edit an opening, accept or refuse an outline suggestion (wall / glass / refuse), give a grey furniture family a kind.
// The rooms milestone (docs/rooms/DESIGN.md R-6.1, R-6.4; R6): "Close it here" and "It is outdoors" on a slab-gap flag
// (the first only with a mouth), "Not a doorway: one room" on a doorway flag, the "waiting for Rebuild" mark of a fix a
// card wrote, and the hint under an old-rule plate-dropped flag while the draft is built the earlier way.
import { Crosshair, Footprints, MousePointerClick, PencilLine } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import type { Flag, FlagKind, OutlineEdgeFix } from '@/upload/contracts';
import { cn } from '@/lib/utils';
import { WaitingMark } from './RoomsPanels';
import { isCutXHole } from './roomsFixes';
import { RULES_EARLIER_TEXT, USE_NEW_TEXT } from './settingsEdit';
import { TID } from './testids';

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
  // The rooms milestone's kinds (docs/rooms/DESIGN.md R-6.1; the scaffold's words, kept by R6: the cards show the
  // builder's own title and sentence under them)
  'slab-gap': 'No floor beside the walls',
  'room-open': 'Room not closed',
  'room-names': 'Several names in one room',
  doorway: 'Gap closed as a doorway',
  stair: 'Stair',                                     // RR (S3): the builder's own title already says "Stair kept as lines"
  'stairs-none': 'No stair can be climbed',
  'stair-clash': 'Walls cut under a stair',
  'hole-skipped': 'Void mark not cut',
};

/** RR (S2): the stair card's button (testids.ts is frozen: the id lives here). */
export const FLAG_OPEN_STAIR = 'flag-open-stair';
/** RR (CODE-1 + BRK-2): the cut X hole card's button. */
export const FLAG_IT_IS_FLOOR = 'flag-it-is-floor';

/** The rooms milestone's buttons and marks on the flag cards (R-6.1, R-6.4). */
export interface FlagRoomsActions {
  /** The fix a card already wrote, and whether it waits for a Rebuild. */
  fixOf: (flag: Flag) => { what: 'line' | 'none' | 'outdoors' | 'floor'; waiting: boolean } | null;
  onCloseHere: (flag: Flag) => void;
  /** RR (CODE-1 + BRK-2): "It is floor" on the flag of an X mark cut as a shaft or a void. */
  onItIsFloor?: (flag: Flag) => void;
  onOutdoors: (flag: Flag) => void;
  onNotDoorway: (flag: Flag) => void;
  /** The draft is built the earlier way: the hint under an old-rule plate-dropped flag, with its button. */
  earlier: boolean;
  onUseNew: () => void;
}

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
  rooms?: FlagRoomsActions;
  /** RR (S2): a stair card that asks for a check: open that stair's panel (the tool Rooms and stairs). */
  onOpenStair?: (flag: Flag) => void;
}

export function FlagList({ flags, outlineOf, disabled, activeId, onShow, onSelectKeys, onOpening, onOutline, onFamily, rooms, onOpenStair }: FlagListProps) {
  if (!flags.length) return <p className="text-sm text-muted-foreground" data-testid="flag-list-empty">No flags on this floor.</p>;
  const ordered = [...flags].sort((a, b) => (a.severity === b.severity ? 0 : a.severity === 'check' ? -1 : 1));
  return (
    <ul className="grid gap-1.5" data-testid="flag-list">
      {ordered.map(f => {
        const outline = (f.kind === 'outline-wall' || f.kind === 'outline-glass') && f.ref.edge ? outlineOf?.(f) ?? null : null;
        const cutX = isCutXHole(f);
        const fix = rooms && (f.kind === 'slab-gap' || f.kind === 'doorway' || cutX) ? rooms.fixOf(f) : null;
        const mouth = !!f.ref.a && !!f.ref.b;
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
              {rooms && f.kind === 'slab-gap' && mouth && (
                <Button size="sm" className="h-7" variant={fix?.what === 'line' ? 'default' : 'outline'} disabled={disabled || !!fix}
                  onClick={() => rooms.onCloseHere(f)} data-testid={TID.flagCloseHere}>Close it here</Button>
              )}
              {rooms && f.kind === 'slab-gap' && (
                <Button size="sm" className="h-7" variant={fix?.what === 'outdoors' ? 'default' : 'outline'} disabled={disabled || !!fix}
                  onClick={() => rooms.onOutdoors(f)} data-testid={TID.flagOutdoors}>It is outdoors</Button>
              )}
              {rooms && f.kind === 'doorway' && mouth && (
                <Button size="sm" className="h-7" variant={fix?.what === 'none' ? 'default' : 'outline'} disabled={disabled || !!fix}
                  onClick={() => rooms.onNotDoorway(f)} data-testid={TID.flagNotDoorway}>Not a doorway: one room</Button>
              )}
              {rooms?.onItIsFloor && cutX && (
                <Button size="sm" className="h-7" variant={fix?.what === 'floor' ? 'default' : 'outline'} disabled={disabled || !!fix}
                  onClick={() => rooms.onItIsFloor!(f)} data-testid={FLAG_IT_IS_FLOOR}>It is floor</Button>
              )}
              {f.kind === 'stair' && f.severity === 'check' && f.ref.stair && onOpenStair && (
                <Button size="sm" variant="outline" className="h-7" onClick={() => onOpenStair(f)} data-testid={FLAG_OPEN_STAIR}>
                  <Footprints aria-hidden="true" />
                  Open this stair
                </Button>
              )}
              {fix?.waiting && <WaitingMark />}
            </div>
            {rooms?.earlier && f.kind === 'plate-dropped' && (
              <div className="flex flex-wrap items-center gap-2 rounded bg-amber-50 p-2 text-xs" data-testid={TID.flagEarlierHint}>
                <span className="min-w-0 flex-1">{RULES_EARLIER_TEXT}</span>
                <Button size="sm" className="h-7" disabled={disabled} onClick={rooms.onUseNew}>{USE_NEW_TEXT}</Button>
              </div>
            )}
          </li>
        );
      })}
    </ul>
  );
}
