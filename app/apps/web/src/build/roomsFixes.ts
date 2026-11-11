// The rooms milestone's fixes on the Check step (docs/rooms/DESIGN.md R-6.2, R-6.3, R-6.4; R6), as pure functions of the
// settings and the floor's overlay: which room, area or stair a fix is about, whether the last build shows it applied
// ("waiting for Rebuild" otherwise, and only while the build is stale), the rows of "Fixes on this floor", the fixes the
// flag cards write, and the marks the canvas draws for the fixes that wait. Points are sheet metres. No React here.
import type { Vec2 } from '@walkthrough/viewer';
import type { BuildSettings, ClosingFix, Flag, OverlayFloor, RoomFix, StairFix } from '@/upload/contracts';
import { flat, insidePoint, polyContains, ringContains, d2Polyline } from '@/plan/geom';
import { NO_MARKS, type FixMarks } from '@/plan/marks';
import { closingsOf, removeClosing, removeRoomFix, removeStairFix, roomFixesOf, stairFixesOf, type Change } from './settingsEdit';

type OSpace = NonNullable<OverlayFloor['spaces']>[number];
type OStair = NonNullable<OverlayFloor['stairs']>[number];
type OUnfloored = NonNullable<OverlayFloor['unfloored']>[number];

const dist = (a: Vec2, b: Vec2) => Math.hypot(a[0] - b[0], a[1] - b[1]);
/** The two segments have the same ends within tol (either order). */
export const sameEnds = (a: Vec2, b: Vec2, c: Vec2, d: Vec2, tol: number) =>
  (dist(a, c) <= tol && dist(b, d) <= tol) || (dist(a, d) <= tol && dist(b, c) <= tol);
const mid = (a: Vec2, b: Vec2): Vec2 => [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2];
const r3 = (v: number) => Math.round(v * 1000) / 1000;
export const showPoint = (p: Vec2) => `(${p[0].toFixed(2)}, ${p[1].toFixed(2)})`;

const okRing = (o: unknown): o is Vec2[] => Array.isArray(o) && o.length >= 3;
const spaceHolds = (s: OSpace, p: Vec2) => okRing(s.o) && polyContains(flat(s.o), (s.h ?? []).filter(okRing).map(flat), p[0], p[1]);

/** The room (overlay space) that holds a point. */
export function spaceHolding(of: OverlayFloor | null | undefined, p: Vec2): OSpace | null {
  return (of?.spaces ?? []).find(s => spaceHolds(s, p)) ?? null;
}

/** The stair whose outline holds the point or lies within `tol` m of it (R-6.3). */
export function stairHolding(of: OverlayFloor | null | undefined, p: Vec2, tol = 0.5): OStair | null {
  let best: OStair | null = null, bestD = tol * tol;
  for (const s of of?.stairs ?? []) {
    if (!okRing(s.outline)) continue;
    const ring = flat(s.outline);
    if (ringContains(ring, p[0], p[1])) return s;
    const d = d2Polyline([...ring, ring[0]!, ring[1]!], p[0], p[1]);
    if (d <= bestD) { best = s; bestD = d; }
  }
  return best;
}

/** The index of the unfloored area that holds the point, or -1. */
export function unflooredHolding(of: OverlayFloor | null | undefined, p: Vec2): number {
  return (of?.unfloored ?? []).findIndex(u => okRing(u.o) && ringContains(flat(u.o), p[0], p[1]));
}

const holeHolds = (of: OverlayFloor, p: Vec2) => (of.holes ?? []).some(h => okRing(h.o) && polyContains(flat(h.o), (h.h ?? []).filter(okRing).map(flat), p[0], p[1]));
const slabHolds = (of: OverlayFloor, p: Vec2) => (of.slabs ?? []).some(s => okRing(s.o) && polyContains(flat(s.o), (s.h ?? []).filter(okRing).map(flat), p[0], p[1]));

/** A point well inside an overlay polygon (sheet m), or its first point. */
export function pointIn(o: Vec2[], h: Vec2[][] = []): Vec2 {
  const p = insidePoint(flat(o), h.filter(okRing).map(flat));
  return p ? [r3(p[0]), r3(p[1])] : [o[0]?.[0] ?? 0, o[0]?.[1] ?? 0];
}

// ------------------------------------------------------------------------------------------- applied in the last build
/** The last build shows this closing fix applied: a staff line along it (its ends extended to the walls by up to 0.5 m,
 *  R-2.1), or no app closing left within 0.3 m of a removed one's ends (R-6.2). */
export function closingApplied(fix: ClosingFix, index: number, of: OverlayFloor): boolean {
  const cl = of.closings ?? [];
  if (fix.use === 'line') return cl.some(c => c.kind === 'staff' && (c.fix === undefined || c.fix === index) && sameEnds(c.a, c.b, fix.a, fix.b, 0.6));
  return !cl.some(c => c.kind !== 'staff' && sameEnds(c.a, c.b, fix.a, fix.b, 0.3));
}

/** The last build shows this room fix applied: the room holding its point has its name, no ceiling; "no floor here" or
 *  "it is outdoors" is a hole or an answered area there; "floor here" is plate with no open area left there. */
export function roomApplied(fix: RoomFix, of: OverlayFloor): boolean {
  const sp = spaceHolding(of, fix.at);
  if (fix.name !== null && (!sp || sp.name !== fix.name)) return false;
  if (fix.ceiling === 'none' && (!sp || sp.ceiling !== false)) return false;
  const u = unflooredHolding(of, fix.at);
  const area: OUnfloored | null = u >= 0 ? of.unfloored![u]! : null;
  if (fix.slab === 'none' && !(area?.answered || holeHolds(of, fix.at))) return false;
  if (fix.slab === 'floor' && (area !== null || !slabHolds(of, fix.at))) return false;
  return true;
}

/** The last build shows this stair fix applied: kept as lines, climbable, and climbing from the picked end. */
export function stairApplied(fix: StairFix, of: OverlayFloor): boolean {
  const st = stairHolding(of, fix.at);
  if (!st) return false;
  if (fix.use === 'lines') return st.state === 'lines';
  if (fix.use === 'climb' && st.state !== 'climb') return false;
  if (fix.bottom) {
    if (st.state !== 'climb' || !st.walk || st.walk.length < 2) return false;
    return dist(fix.bottom, st.walk[0]!) <= dist(fix.bottom, st.walk[st.walk.length - 1]!);
  }
  return true;
}

// ------------------------------------------------------------------------------------------- the list "Fixes on this floor"
export type FixKind = 'closing' | 'closing-removed' | 'room' | 'stair';
export interface FixRow {
  kind: FixKind;
  /** Its index in its own fixes list (closings for both closing kinds). */
  index: number;
  text: string;
  waiting: boolean;
  /** Where it is (sheet m), for Show. */
  at: Vec2;
  remove: Change;
}

function roomText(f: RoomFix, of: OverlayFloor | null): string {
  const sp = spaceHolding(of, f.at);
  const parts: string[] = [];
  if (f.name !== null) parts.push(`named “${f.name}”`);
  if (sp || f.slab !== 'none') {
    if (f.slab === 'none') parts.push('no floor here');
    if (f.slab === 'floor') parts.push('floor here');
  } else parts.push('outdoors');
  if (f.ceiling === 'none') parts.push('no ceiling');
  const what = sp ? `Room ${sp.name || sp.id}` : `At ${showPoint(f.at)}`;
  return `${what}: ${parts.join(', ')}`;
}

function stairText(f: StairFix, of: OverlayFloor | null): string {
  const st = stairHolding(of, f.at);
  const parts: string[] = [];
  if (f.bottom) parts.push(`the bottom at ${showPoint(f.bottom)}`);
  if (f.use === 'lines') parts.push('keep as lines');
  if (f.use === 'climb') parts.push('climb it as drawn');
  return `Stair ${st?.id ?? `at ${showPoint(f.at)}`}: ${parts.join(', ')}`;
}

/** The rows of "Fixes on this floor" (R-6.4): closing lines, removed closings, room fixes, stair fixes, each with its
 *  Remove. `stale`: the settings changed since the last build (a fix can wait only then). */
export function fixRows(s: BuildSettings, floor: string, of: OverlayFloor | null, stale: boolean): FixRow[] {
  const rows: FixRow[] = [];
  const waits = (applied: boolean) => stale && !applied;
  closingsOf(s).forEach((f, index) => {
    if (f.floor !== floor) return;
    rows.push({
      kind: f.use === 'line' ? 'closing' : 'closing-removed', index,
      text: f.use === 'line' ? `Closing line ${showPoint(f.a)} – ${showPoint(f.b)}` : `A closing taken out at ${showPoint(mid(f.a, f.b))}: one room`,
      waiting: waits(!!of && closingApplied(f, index, of)), at: mid(f.a, f.b), remove: removeClosing(f),
    });
  });
  roomFixesOf(s).forEach((f, index) => {
    if (f.floor !== floor) return;
    rows.push({ kind: 'room', index, text: roomText(f, of), waiting: waits(!!of && roomApplied(f, of)), at: f.at, remove: removeRoomFix(f) });
  });
  stairFixesOf(s).forEach((f, index) => {
    if (f.floor !== floor) return;
    rows.push({ kind: 'stair', index, text: stairText(f, of), waiting: waits(!!of && stairApplied(f, of)), at: f.at, remove: removeStairFix(f) });
  });
  return rows;
}

/** What the canvas draws for the fixes that wait (R-6.4 "Shown before Rebuild"). */
export function fixMarks(s: BuildSettings, floor: string, of: OverlayFloor, stale: boolean): FixMarks {
  if (!stale) return NO_MARKS;
  const m: FixMarks = { lines: [], removed: [], rooms: [], points: [], outdoors: [], bottoms: [] };
  closingsOf(s).forEach((f, i) => {
    if (f.floor !== floor || closingApplied(f, i, of)) return;
    (f.use === 'line' ? m.lines : m.removed).push({ a: f.a, b: f.b });
  });
  for (const f of roomFixesOf(s)) {
    if (f.floor !== floor || roomApplied(f, of)) continue;
    const sp = spaceHolding(of, f.at);
    if (sp) m.rooms.push(sp.id);
    m.points.push({ at: f.at, kind: f.slab === 'floor' ? 'floor' : f.slab === 'none' ? 'outdoors' : 'room' });
    const u = unflooredHolding(of, f.at);
    if (f.slab === 'none' && u >= 0) m.outdoors.push(u);
  }
  for (const f of stairFixesOf(s)) {
    if (f.floor !== floor || stairApplied(f, of)) continue;
    if (f.bottom) m.bottoms.push({ at: f.bottom });
  }
  return m;
}

// ------------------------------------------------------------------------------------------- the flag cards' fixes
/** "Close it here" on a slab-gap flag with a mouth: a closing line from the mouth's two ends (R-6.2; the builder extends
 *  each end to the walls within 0.5 m, R1.md section 5). */
export function closeHereFix(f: Flag): ClosingFix | null {
  return f.floor && f.ref.a && f.ref.b ? { floor: f.floor, a: f.ref.a, b: f.ref.b, use: 'line' } : null;
}

/** "Not a doorway: one room" on a doorway flag: the app's closing left out (its two ends as the report gives them). */
export function notDoorwayFix(f: Flag): ClosingFix | null {
  return f.floor && f.ref.a && f.ref.b ? { floor: f.floor, a: f.ref.a, b: f.ref.b, use: 'none' } : null;
}

/** The unfloored area a slab-gap flag is about: its mouth is the flag's (5 cm), else it holds the flag's point. */
export function areaOfFlag(f: Flag, of: OverlayFloor | null): number {
  const list = of?.unfloored ?? [];
  const a = f.ref.a, b = f.ref.b;
  if (a && b) {
    const i = list.findIndex(u => u.mouth && sameEnds(u.mouth[0], u.mouth[1], a, b, 0.05));
    if (i >= 0) return i;
  }
  return f.at ? unflooredHolding(of, f.at) : -1;
}

/** "It is outdoors" on a slab-gap flag: a room fix with slab 'none' at a point inside the area (R-6.2). */
export function outdoorsFix(f: Flag, of: OverlayFloor | null): RoomFix | null {
  if (!f.floor) return null;
  const i = areaOfFlag(f, of);
  const at = i >= 0 ? pointIn(of!.unfloored![i]!.o) : f.at;
  return at ? { floor: f.floor, at: [r3(at[0]), r3(at[1])], name: null, slab: 'none', ceiling: 'auto' } : null;
}

/** The fix a flag card already wrote, if any, and whether it waits for a Rebuild. */
export function flagFix(f: Flag, s: BuildSettings | null, of: OverlayFloor | null, stale: boolean): { what: 'line' | 'none' | 'outdoors'; waiting: boolean } | null {
  if (!s || !f.floor) return null;
  if ((f.kind === 'slab-gap' || f.kind === 'doorway') && f.ref.a && f.ref.b) {
    const want = f.kind === 'slab-gap' ? 'line' : 'none';
    const i = closingsOf(s).findIndex(c => c.floor === f.floor && c.use === want && sameEnds(c.a, c.b, f.ref.a!, f.ref.b!, 0.05));
    if (i >= 0) return { what: want, waiting: stale && !(of && closingApplied(closingsOf(s)[i]!, i, of)) };
  }
  if (f.kind === 'slab-gap') {
    const area = areaOfFlag(f, of);
    const fx = roomFixesOf(s).find(r => r.floor === f.floor && r.slab === 'none'
      && (area >= 0 ? unflooredHolding(of, r.at) === area : !!f.at && dist(r.at, f.at) <= 0.5));
    if (fx) return { what: 'outdoors', waiting: stale && !(of && roomApplied(fx, of)) };
  }
  return null;
}

/** The room fix of a room (its point inside the room), or of a place with no room (within 0.5 m, or in the same
 *  unfloored area), with its point. */
export function roomFixFor(s: BuildSettings, floor: string, of: OverlayFloor | null, target: { space: OSpace | null; at: Vec2 }): RoomFix | null {
  const list = roomFixesOf(s).filter(r => r.floor === floor);
  if (target.space) return list.find(r => spaceHolds(target.space!, r.at)) ?? null;
  const area = unflooredHolding(of, target.at);
  return list.find(r => !spaceHolding(of, r.at) && (dist(r.at, target.at) <= 0.5 || (area >= 0 && unflooredHolding(of, r.at) === area))) ?? null;
}

/** The stair fix of an overlay stair (its point on or within 0.5 m of that stair). */
export function stairFixFor(s: BuildSettings, floor: string, of: OverlayFloor | null, stairId: string): StairFix | null {
  return stairFixesOf(s).find(f => f.floor === floor && stairHolding(of, f.at)?.id === stairId) ?? null;
}
