// The fixes that wait for a Rebuild, drawn over the plan (docs/rooms/DESIGN.md R-6.4 "Shown before Rebuild"). Owner R6.
// PlanCanvasProps (frozen, the rooms scaffold R0) has no place for them, so they ride on the overlay object the Check
// step hands the canvas: withMarks() returns a shallow copy of the floor's overlay and remembers its marks; the canvas
// reads them with marksOf() whenever the overlay prop changes (docs/rooms/contract-issues/R6.md, R6-1). Sheet metres.
import type { Vec2 } from '@walkthrough/viewer';
import type { OverlayFloor } from '@/upload/contracts';

export interface FixMarks {
  /** Closing lines staff drew or asked for, not built yet: dashed orange. */
  lines: { a: Vec2; b: Vec2 }[];
  /** The app's closings staff took out, still in the overlay: struck through. */
  removed: { a: Vec2; b: Vec2 }[];
  /** Rooms (overlay space ids) with a room fix waiting: outlined. */
  rooms: string[];
  /** Points of room fixes: a marker ('floor': floor here, 'outdoors' / 'no-floor', 'room': a name or no ceiling). */
  points: { at: Vec2; kind: 'room' | 'floor' | 'outdoors' }[];
  /** Unfloored areas (indices into overlay.unfloored) answered "it is outdoors", waiting: hatched grey. */
  outdoors: number[];
  /** A stair's picked bottom: an arrow at the point. */
  bottoms: { at: Vec2 }[];
  /** RR (S13): the room (overlay space id) and the stair (overlay stair id) open in the Check step's panel: outlined in a
   *  strong colour, so a small room picked on the plan can be found again. */
  pickedRoom?: string | null;
  pickedStair?: string | null;
}

export const NO_MARKS: FixMarks = { lines: [], removed: [], rooms: [], points: [], outdoors: [], bottoms: [] };

const marks = new WeakMap<OverlayFloor, FixMarks>();

/** A copy of the floor's overlay that carries the marks (the same object for as long as the caller memoises it). */
export function withMarks(overlay: OverlayFloor, m: FixMarks): OverlayFloor {
  const copy: OverlayFloor = { ...overlay };
  marks.set(copy, m);
  return copy;
}

export function marksOf(overlay: OverlayFloor | null | undefined): FixMarks | null {
  return overlay ? marks.get(overlay) ?? null : null;
}

export const hasMarks = (m: FixMarks | null): boolean =>
  !!m && ((m.lines.length + m.removed.length + m.rooms.length + m.points.length + m.outdoors.length + m.bottoms.length) > 0
    || !!m.pickedRoom || !!m.pickedStair);
