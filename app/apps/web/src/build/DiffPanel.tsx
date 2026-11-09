// The Check step's diff (docs/upload/DESIGN.md U-12.4): this build against the previous build of the draft and against the
// latest version; the counts that changed (per floor), openings added / removed / changed, furniture by kind, rooms added
// and removed; a toggle draws added parts green and removed ones red on the plan. Room names are text.
import type { BuildDiff, DiffBody } from '@/upload/contracts';
import { Checkbox } from '@/components/ui/checkbox';
import { NativeSelect } from './fields';

export const AGAINST_TEXT = { 'previous-run': 'the previous build', version: 'the latest version' } as const;

export interface DiffRow { floor: string; what: string; before: number; after: number }

/** The counts that changed, floor by floor, then the furniture by kind (floor ''). */
export function diffRows(body: DiffBody): DiffRow[] {
  const rows: DiffRow[] = [];
  for (const [floor, counts] of Object.entries(body.counts)) {
    for (const [what, [before, after]] of Object.entries(counts)) if (before !== after) rows.push({ floor, what, before, after });
  }
  for (const [kind, [before, after]] of Object.entries(body.furnitureByKind)) if (before !== after) rows.push({ floor: '', what: `furniture: ${kind}`, before, after });
  return rows;
}

/** Nothing changed against this side. */
export function sameAs(body: DiffBody): boolean {
  return !diffRows(body).length && !body.partsAdded.length && !body.partsRemoved.length && !body.openingsAdded.length
    && !body.openingsRemoved.length && !body.openingsChanged.length && !body.roomsAdded.length && !body.roomsRemoved.length;
}

export interface DiffPanelProps {
  diff: BuildDiff | undefined;
  against: number;
  onAgainst: (i: number) => void;
  draw: boolean;
  onDraw: (v: boolean) => void;
  floor?: string;
}

export function DiffPanel({ diff, against, onAgainst, draw, onDraw, floor }: DiffPanelProps) {
  if (!diff) return <p className="text-sm text-muted-foreground" data-testid="diff-panel">Loading the changes...</p>;
  if (!diff.against.length) return <p className="text-sm text-muted-foreground" data-testid="diff-panel" data-empty="">The first build of a new project: nothing to compare with.</p>;
  const side = diff.against[Math.min(against, diff.against.length - 1)]!;
  const body = side.diff;
  const rows = diffRows(body).filter(r => !floor || !r.floor || r.floor === floor);
  const ops = (list: { floor: string }[]) => list.filter(o => !floor || o.floor === floor).length;
  const same = sameAs(body);
  return (
    <section className="grid gap-2 rounded-lg border bg-background p-3 text-sm" data-testid="diff-panel" data-against={side.kind} data-same={same ? '' : undefined}>
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-semibold">Changes against</span>
        <NativeSelect value={String(against)} onChange={e => onAgainst(Number(e.target.value))} data-testid="diff-against" aria-label="Compare with">
          {diff.against.map((a, i) => <option key={i} value={i}>{`${AGAINST_TEXT[a.kind]} (${a.ref})`}</option>)}
        </NativeSelect>
        <label className="ml-auto flex items-center gap-1.5 text-xs">
          <Checkbox checked={draw} onCheckedChange={v => onDraw(v === true)} data-testid="diff-draw" />
          Draw added and removed parts
        </label>
      </div>
      {same ? (
        <p className="text-muted-foreground" data-testid="diff-none">{`No change against ${AGAINST_TEXT[side.kind]}.`}</p>
      ) : (
        <>
          {rows.length > 0 && (
            <table className="w-full text-xs">
              <thead className="text-left text-muted-foreground"><tr><th className="font-medium">Floor</th><th className="font-medium">What</th><th className="font-medium">Before</th><th className="font-medium">Now</th></tr></thead>
              <tbody>
                {rows.map((r, i) => (
                  <tr key={i} className="border-t" data-testid="diff-row" data-floor={r.floor} data-what={r.what}>
                    <td>{r.floor}</td><td>{r.what}</td><td className="tabular-nums">{r.before}</td><td className="tabular-nums">{r.after}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          <p className="text-xs" data-testid="diff-summary">
            {[
              `${ops(body.partsAdded)} parts added`, `${ops(body.partsRemoved)} removed`,
              `${ops(body.openingsAdded)} openings added`, `${ops(body.openingsRemoved)} removed`, `${ops(body.openingsChanged)} changed`,
            ].join(', ')}
          </p>
          {(body.roomsAdded.length > 0 || body.roomsRemoved.length > 0) && (
            <p className="text-xs" data-testid="diff-rooms">
              {body.roomsAdded.length > 0 && <span>{`Rooms added: ${body.roomsAdded.join(', ')}. `}</span>}
              {body.roomsRemoved.length > 0 && <span>{`Rooms removed: ${body.roomsRemoved.join(', ')}.`}</span>}
            </p>
          )}
        </>
      )}
    </section>
  );
}
