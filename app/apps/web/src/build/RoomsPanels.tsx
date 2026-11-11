// The rooms milestone's panels (docs/rooms/DESIGN.md R-6.2, R-6.4, R-12.6; R6): the Check step's three ticks above the
// plan, its counts in the page, the room panel (a click in a room, or where there is no room, with the tool "Rooms and
// stairs"), the stair panel, the list "Fixes on this floor" with Remove and the "waiting for Rebuild" marks, and the
// Build and Save steps' three counts per floor (counted from the overlay the API serves: R5.md D-3). Room and stair
// names are drawing or staff text: React text only.
import type { Vec2 } from '@walkthrough/viewer';
import { Crosshair, Footprints, Hourglass, X } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { Input } from '@/components/ui/input';
import type { PlanShow } from '@/plan';
import type { BuildResultInfo, BuildSettings, OverlayFloor } from '@/upload/contracts';
import { formatNumber } from '@/lib/format';
import { useBuildContext } from './context';
import { fixRows, pointIn, roomApplied, roomFixFor, showPoint, stairApplied, stairFixFor, type FixRow } from './roomsFixes';
import { removeStairFix, setRoomFix, setStairFix } from './settingsEdit';
import { TID } from './testids';

/** The mark "waiting for Rebuild" (R-6.4), in the list, the panels and the flag cards. */
export function WaitingMark() {
  return (
    <span className="inline-flex items-center gap-1 rounded bg-amber-100 px-1.5 py-0.5 text-xs text-amber-800" data-testid={TID.fixWaiting}>
      <Hourglass aria-hidden="true" className="size-3" />
      waiting for Rebuild
    </span>
  );
}

// ------------------------------------------------------------------------------------------------------ ticks, counts
export function ShowTicks({ show, onShow }: { show: PlanShow; onShow: (s: PlanShow) => void }) {
  const tick = (key: keyof PlanShow, label: string, testId: string) => (
    <label className="flex items-center gap-1.5 text-sm">
      <Checkbox checked={show[key]} onCheckedChange={v => onShow({ ...show, [key]: v === true })} data-testid={testId} />
      {label}
    </label>
  );
  return (
    <div className="flex flex-wrap items-center gap-3" data-testid="show-ticks">
      {tick('rooms', 'Rooms', TID.showRooms)}
      {tick('plate', 'Floor plate', TID.showPlate)}
      {tick('furniture', 'Furniture', TID.showFurniture)}
    </div>
  );
}

/** The counts of the floor on screen (R-12.6: in the page, so a test can read them). Nothing with the old rule. */
export function CheckCounts({ of }: { of: OverlayFloor | null }) {
  if (!of || !Array.isArray(of.spaces)) return null;
  const stairs = of.stairs ?? [];
  const n = (v: number, testId: string, word: string) => (
    <span><span className="font-medium tabular-nums" data-testid={testId}>{formatNumber(v)}</span>{` ${word}`}</span>
  );
  return (
    <p className="flex flex-wrap gap-x-3 gap-y-1 text-xs text-muted-foreground" data-testid="check-counts" data-key={of.key}>
      {n(of.spaces.length, TID.checkRooms, of.spaces.length === 1 ? 'room' : 'rooms')}
      {n((of.holes ?? []).length, TID.checkHoles, (of.holes ?? []).length === 1 ? 'hole' : 'holes')}
      {n(stairs.filter(s => s.state === 'climb').length, TID.checkStairsClimb, 'to climb')}
      {n(stairs.length, TID.checkStairs, stairs.length === 1 ? 'stair in all' : 'stairs in all')}
    </p>
  );
}

/** The Build and Save steps' counts per floor (R-12.6): rooms closed, names placed, stairs you can climb. Shown only
 *  when the overlay has rooms (a build with the new rules). */
export function RoomCounts({ overlay, result }: { overlay: { floors: OverlayFloor[] } | undefined; result: BuildResultInfo }) {
  const floors = overlay?.floors ?? [];
  if (!floors.some(f => Array.isArray(f.spaces))) return null;
  return (
    <table className="w-full text-sm" data-testid="room-counts-table">
      <thead className="text-left text-xs text-muted-foreground">
        <tr><th className="font-medium">Floor</th><th className="font-medium">Rooms closed</th><th className="font-medium">Names placed</th><th className="font-medium">Stairs you can climb</th></tr>
      </thead>
      <tbody>
        {floors.map(f => (
          <tr key={f.key} className="border-t" data-testid={TID.roomCounts} data-key={f.key}>
            <td>{result.floors.find(x => x.key === f.key)?.name ?? f.key}</td>
            <td className="tabular-nums" data-testid={TID.countRooms}>{formatNumber((f.spaces ?? []).length)}</td>
            <td className="tabular-nums" data-testid={TID.countNames}>{formatNumber((f.rooms ?? []).length)}</td>
            <td className="tabular-nums" data-testid={TID.countStairs}>{formatNumber((f.stairs ?? []).filter(s => s.state === 'climb').length)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

// ------------------------------------------------------------------------------------------------------ room panel
export interface RoomTarget { id: string; at: Vec2 }

export function RoomPanel({ floor, target, settings, of, stale, editable, onClose }: {
  floor: string; target: RoomTarget; settings: BuildSettings; of: OverlayFloor | null; stale: boolean; editable: boolean; onClose: () => void;
}) {
  const { change } = useBuildContext();
  const space = target.id ? (of?.spaces ?? []).find(s => s.id === target.id) ?? null : null;
  const fix = roomFixFor(settings, floor, of, { space, at: target.at });
  const at: Vec2 = fix?.at ?? (space ? pointIn(space.o, space.h) : target.at);
  const name = fix?.name ?? null;
  const slab = fix?.slab ?? 'auto';
  const ceiling = fix?.ceiling ?? 'auto';
  const waiting = !!fix && stale && !(of && roomApplied(fix, of));
  const [text, setText] = useState(name ?? '');
  const focused = useRef(false);
  useEffect(() => { if (!focused.current) setText(name ?? ''); }, [name, target.id]);
  const write = (patch: Partial<{ name: string | null; slab: 'auto' | 'none' | 'floor'; ceiling: 'auto' | 'none' }>) =>
    change(setRoomFix({ floor, at, name, slab, ceiling, ...patch }, fix?.at ?? null));
  const commitName = () => { const v = text.trim(); if ((v || null) !== name) write({ name: v || null }); };
  return (
    <section className="grid gap-2 rounded-lg border bg-background p-3 text-sm" data-testid={TID.roomPanel} data-id={target.id}
      data-at={`${at[0]},${at[1]}`}>
      <header className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <h4 className="font-semibold">{space ? `Room ${space.name || space.id}` : 'No room here'}</h4>
          <p className="text-xs text-muted-foreground">
            {space ? `${(Math.round(space.area * 10) / 10).toFixed(1)} m²${space.names.length > 1 ? ` · names: ${space.names.join(', ')}` : ''}` : `At ${showPoint(target.at)}`}
          </p>
        </div>
        <Button size="icon" variant="ghost" className="size-7" onClick={onClose} aria-label="Close the room panel" data-testid={TID.roomPanelClose}><X aria-hidden="true" /></Button>
      </header>
      {space ? (
        <>
          <label className="grid gap-1 text-xs text-muted-foreground">
            Name
            <Input className="h-8" value={text} maxLength={200} disabled={!editable} placeholder={space.name || 'no name'} data-testid={TID.roomName}
              onChange={e => setText(e.target.value)} onFocus={() => { focused.current = true; }}
              onBlur={() => { focused.current = false; commitName(); }} onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); commitName(); } }} />
          </label>
          <label className="flex items-center gap-2">
            <Checkbox checked={slab === 'none'} disabled={!editable} onCheckedChange={v => write({ slab: v === true ? 'none' : 'auto' })} data-testid={TID.roomNoFloor} />
            No floor here
          </label>
          <label className="flex items-center gap-2">
            <Checkbox checked={ceiling === 'none'} disabled={!editable} onCheckedChange={v => write({ ceiling: v === true ? 'none' : 'auto' })} data-testid={TID.roomNoCeiling} />
            No ceiling
          </label>
        </>
      ) : (
        <div className="flex flex-wrap items-center gap-2">
          <Button size="sm" variant={slab === 'floor' ? 'default' : 'outline'} disabled={!editable} data-testid={TID.roomFloorHere}
            aria-pressed={slab === 'floor'} onClick={() => write({ slab: slab === 'floor' ? 'auto' : 'floor' })}>Floor here</Button>
          <Button size="sm" variant={slab === 'none' ? 'default' : 'outline'} disabled={!editable} data-testid={TID.roomOutdoors}
            aria-pressed={slab === 'none'} onClick={() => write({ slab: slab === 'none' ? 'auto' : 'none' })}>It is outdoors</Button>
        </div>
      )}
      {waiting && <p><WaitingMark /></p>}
    </section>
  );
}

// ------------------------------------------------------------------------------------------------------ stair panel
export function StairPanel({ floor, stairId, settings, of, stale, editable, picking, onPickBottom, onClose }: {
  floor: string; stairId: string; settings: BuildSettings; of: OverlayFloor | null; stale: boolean; editable: boolean;
  picking: boolean; onPickBottom: () => void; onClose: () => void;
}) {
  const { change } = useBuildContext();
  const st = (of?.stairs ?? []).find(s => s.id === stairId) ?? null;
  if (!st) return null;
  const fix = stairFixFor(settings, floor, of, stairId);
  const at: Vec2 = fix?.at ?? pointIn(st.outline);
  const use = fix?.use ?? 'auto';
  const waiting = !!fix && stale && !(of && stairApplied(fix, of));
  const setUse = (u: 'lines' | 'climb') => change(setStairFix({ floor, at, bottom: fix?.bottom ?? null, use: use === u ? 'auto' : u }, fix?.at ?? null));
  return (
    <section className="grid gap-2 rounded-lg border bg-background p-3 text-sm" data-testid={TID.stairPanel} data-id={st.id} data-state={st.state}>
      <header className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <h4 className="font-semibold">{`Stair ${st.id}`}</h4>
          <p className="text-xs text-muted-foreground">
            {st.state === 'climb'
              ? `You can climb it${st.risers ? `: ${st.risers} risers` : ''}${st.riser ? ` of ${st.riser.toFixed(3)} m` : ''}${st.to ? `, up to ${st.to}` : ''}.`
              : `Kept as lines${st.why ? `: ${st.why}` : ''}.`}
          </p>
          {st.text && <p className="text-xs text-muted-foreground">{st.text}</p>}
        </div>
        <Button size="icon" variant="ghost" className="size-7" onClick={onClose} aria-label="Close the stair panel" data-testid={TID.stairPanelClose}><X aria-hidden="true" /></Button>
      </header>
      <div className="flex flex-wrap gap-1">
        <Button size="sm" variant={picking ? 'default' : 'outline'} disabled={!editable} onClick={onPickBottom} data-testid={TID.stairBottom}
          data-picking={picking ? '' : undefined}>
          <Footprints aria-hidden="true" />
          {picking ? 'Click its bottom tread...' : 'This is the bottom'}
        </Button>
        <Button size="sm" variant={use === 'lines' ? 'default' : 'outline'} disabled={!editable} aria-pressed={use === 'lines'} onClick={() => setUse('lines')}
          data-testid={TID.stairLines}>Keep as lines</Button>
        <Button size="sm" variant={use === 'climb' ? 'default' : 'outline'} disabled={!editable} aria-pressed={use === 'climb'} onClick={() => setUse('climb')}
          data-testid={TID.stairClimb}>Climb it as drawn</Button>
        <Button size="sm" variant="ghost" disabled={!editable || !fix} onClick={() => { if (fix) change(removeStairFix(fix)); }} data-testid={TID.stairAuto}>
          Decide automatically
        </Button>
      </div>
      {fix?.bottom && <p className="text-xs">{`The bottom: ${showPoint(fix.bottom)}`}</p>}
      {waiting && <p><WaitingMark /></p>}
    </section>
  );
}

// ------------------------------------------------------------------------------------------------------ the fixes list
export const FIX_KIND_TEXT: Record<FixRow['kind'], string> = {
  closing: 'Closing line', 'closing-removed': 'Closing taken out', room: 'Room', stair: 'Stair',
};

export function FixesList({ settings, floor, of, stale, editable, onShow }: {
  settings: BuildSettings; floor: string; of: OverlayFloor | null; stale: boolean; editable: boolean; onShow?: (at: Vec2) => void;
}) {
  const { change } = useBuildContext();
  const rows = fixRows(settings, floor, of, stale);
  return (
    <section className="grid gap-2" data-testid={TID.fixesList}>
      <h4 className="text-sm font-semibold">{`Fixes on this floor (${formatNumber(rows.length)})`}</h4>
      {rows.length > 0 && (
        <ul className="grid gap-1 text-xs">
          {rows.map(r => (
            <li key={`${r.kind}:${r.index}`} className="flex flex-wrap items-center gap-2" data-testid={TID.fixRow} data-kind={r.kind} data-index={r.index}
              data-waiting={r.waiting ? '' : undefined}>
              <span className="min-w-0 flex-1">{r.text}</span>
              {r.waiting && <WaitingMark />}
              {onShow && (
                <Button size="sm" variant="ghost" className="h-6" onClick={() => onShow(r.at)} aria-label={`Show ${FIX_KIND_TEXT[r.kind]}`}><Crosshair aria-hidden="true" /></Button>
              )}
              <Button size="sm" variant="ghost" className="h-6" disabled={!editable} onClick={() => change(r.remove)} data-testid={TID.fixRemove}>Remove</Button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
