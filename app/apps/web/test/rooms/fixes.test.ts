// R6 (docs/rooms/ACCEPTANCE.md 2.3 R6; DESIGN.md R-6.2 - R-6.4): the Check step's fixes against the reference building's
// overlay (fixtures/rooms/overlay.reference.json): what the flag cards write ("Close it here", "It is outdoors", "Not a
// doorway: one room"), which room, area or stair a fix is about, "waiting for Rebuild" (only while the build is stale,
// and gone once the build shows the fix), the rows of "Fixes on this floor", the canvas's marks, and the mock API's new
// overlay fixtures (the reference building, with the fixes applied the simple way at a "rebuild").
import { describe, expect, it } from 'vitest';
import {
  areaOfFlag, closeHereFix, closingApplied, fixMarks, fixRows, flagFix, notDoorwayFix, outdoorsFix, pointIn, roomApplied, roomFixFor,
  spaceHolding, stairApplied, stairFixFor, stairHolding, unflooredHolding,
} from '@/build/roomsFixes';
import { addClosing, setRoomFix, setStairFix } from '@/build/settingsEdit';
import type { BuildSettings, Flag, OverlayFloor } from '@/upload/contracts';
import { referenceFloorOf, referenceOverlay, referencePlan, referenceSettings, roomsOverlayFor } from '../mock-api/rooms';

const REF = referenceSettings();
const OV = referenceOverlay();
const ground = OV.floors[0]!;
const flagOf = (kind: Flag['kind']) => OV.flags.find(f => f.kind === kind)!;
/** The mock's "rebuild": the reference overlay with the settings' fixes applied (rooms.ts). */
const rebuilt = (s: BuildSettings): OverlayFloor => roomsOverlayFor(s, sha => REF.sources.findIndex(x => x.sha1 === sha)).floors[0]!;

describe('the flag cards\' fixes (R-6.1, R-6.2)', () => {
  it('"Close it here" writes the mouth\'s two ends as a closing line; "Not a doorway" the closing\'s ends with use none', () => {
    expect(closeHereFix(flagOf('slab-gap'))).toEqual({ floor: 'ground', a: [8.9, 8.9], b: [11.8, 8.9], use: 'line' });
    expect(notDoorwayFix(flagOf('doorway'))).toEqual({ floor: 'ground', a: [7, 5.6], b: [7, 6.8], use: 'none' });
    expect(closeHereFix(flagOf('room-open'))).toBeNull();
  });

  it('"It is outdoors" writes a room fix with no floor at a point inside the unfloored area (not on its mouth)', () => {
    const f = flagOf('slab-gap');
    expect(areaOfFlag(f, ground)).toBe(0);
    const fx = outdoorsFix(f, ground)!;
    expect(fx).toMatchObject({ floor: 'ground', name: null, slab: 'none', ceiling: 'auto' });
    expect(unflooredHolding(ground, fx.at)).toBe(0);
    expect(spaceHolding(ground, fx.at)).toBeNull();
    // without the overlay: the flag's own point
    expect(outdoorsFix(f, null)!.at).toEqual(f.at);
  });

  it('a card\'s fix waits for the Rebuild while the build is stale, and not once the build shows it', () => {
    const f = flagOf('slab-gap');
    const s = addClosing(closeHereFix(f)!)(REF);
    expect(flagFix(f, REF, ground, true)).toBeNull();
    expect(flagFix(f, s, ground, true)).toEqual({ what: 'line', waiting: true });
    expect(flagFix(f, s, ground, false)).toEqual({ what: 'line', waiting: false });
    expect(flagFix(f, s, rebuilt(s), true)).toEqual({ what: 'line', waiting: false });
    const d = flagOf('doorway');
    const s2 = addClosing(notDoorwayFix(d)!)(REF);
    expect(flagFix(d, s2, ground, true)).toEqual({ what: 'none', waiting: true });
    expect(flagFix(d, s2, rebuilt(s2), true)).toEqual({ what: 'none', waiting: false });
    const s3 = setRoomFix(outdoorsFix(f, ground)!)(REF);
    expect(flagFix(f, s3, ground, true)).toEqual({ what: 'outdoors', waiting: true });
    expect(flagFix(f, s3, rebuilt(s3), true)).toEqual({ what: 'outdoors', waiting: false });
  });
});

describe('what a fix is about, and whether the last build applied it (R-6.3, R-6.4)', () => {
  it('rooms, stairs and unfloored areas by point; a stair also within 0.5 m of its outline', () => {
    const living = ground.spaces![0]!;
    const at = pointIn(living.o, living.h);
    expect(spaceHolding(ground, at)?.id).toBe('ground-R001');
    const st2 = ground.stairs![1]!;
    expect(stairHolding(ground, pointIn(st2.outline))?.id).toBe('ground-ST2');
    const out = [Math.max(...st2.outline.map(p => p[0])) + 0.3, pointIn(st2.outline)[1]] as [number, number];
    expect(stairHolding(ground, out)?.id).toBe('ground-ST2');
    expect(stairHolding(ground, [out[0] + 1, out[1]])).toBeNull();
  });

  it('a name, no ceiling, no floor here; a stair kept as lines, climbed from its bottom: applied after the rebuild only', () => {
    const living = ground.spaces![0]!;
    const at = pointIn(living.o, living.h);
    const room = { floor: 'ground', at, name: 'Living', slab: 'none' as const, ceiling: 'none' as const };
    const s1 = setRoomFix(room)(REF);
    expect(roomApplied(room, ground)).toBe(false);
    expect(roomApplied(room, rebuilt(s1))).toBe(true);
    expect(roomFixFor(s1, 'ground', ground, { space: living, at: [0, 0] })).toEqual(room);
    const st2 = ground.stairs![1]!;
    const bottom = st2.outline[0]!;
    const stair = { floor: 'ground', at: pointIn(st2.outline), bottom, use: 'auto' as const };
    const s2 = setStairFix(stair)(REF);
    expect(stairApplied(stair, ground)).toBe(false);
    expect(stairApplied(stair, rebuilt(s2))).toBe(true);
    expect(stairFixFor(s2, 'ground', ground, 'ground-ST2')).toEqual(stair);
    const lines = { floor: 'ground', at: pointIn(ground.stairs![0]!.outline), bottom: null, use: 'lines' as const };
    expect(stairApplied(lines, ground)).toBe(false);
    expect(stairApplied(lines, rebuilt(setStairFix(lines)(REF)))).toBe(true);
    // a closing line: its ends may be extended by up to 0.5 m in the build
    const line = { floor: 'ground', a: [8.9, 8.9] as [number, number], b: [11.8, 8.9] as [number, number], use: 'line' as const };
    const built = { ...ground, closings: [...ground.closings!, { kind: 'staff' as const, a: [8.6, 8.9] as [number, number], b: [12.2, 8.9] as [number, number], fix: 0 }] };
    expect(closingApplied(line, 0, built)).toBe(true);
    expect(closingApplied(line, 0, ground)).toBe(false);
  });

  it('"Fixes on this floor": every kind with its index and its Remove; waiting only while stale', () => {
    let s = addClosing(closeHereFix(flagOf('slab-gap'))!)(REF);
    s = addClosing(notDoorwayFix(flagOf('doorway'))!)(s);
    const living = ground.spaces![0]!;
    s = setRoomFix({ floor: 'ground', at: pointIn(living.o, living.h), name: 'Living', slab: 'auto', ceiling: 'auto' })(s);
    s = setStairFix({ floor: 'ground', at: pointIn(ground.stairs![1]!.outline), bottom: [2.6, 6.4], use: 'auto' })(s);
    s = setRoomFix({ floor: 'upper', at: [5, 5], name: null, slab: 'floor', ceiling: 'auto' })(s);
    const rows = fixRows(s, 'ground', ground, true);
    expect(rows.map(r => [r.kind, r.index, r.waiting])).toEqual([
      ['closing', 0, true], ['closing-removed', 1, true], ['room', 0, true], ['stair', 0, true],
    ]);
    expect(rows.map(r => r.text)).toEqual([
      'Closing line (8.90, 8.90) – (11.80, 8.90)',
      'A closing taken out at (7.00, 6.20): one room',
      'Room LIVING: named “Living”',
      'Stair ground-ST2: the bottom at (2.60, 6.40)',
    ]);
    expect(fixRows(s, 'ground', ground, false).every(r => !r.waiting)).toBe(true);
    expect(fixRows(s, 'ground', rebuilt(s), true).map(r => r.waiting)).toEqual([false, false, false, false]);
    // Remove takes exactly that fix back
    const after = rows[1]!.remove(s);
    expect(fixRows(after, 'ground', ground, true).map(r => r.kind)).toEqual(['closing', 'room', 'stair']);
    expect(fixRows(s, 'upper', OV.floors[1]!, true).map(r => [r.kind, r.text])).toEqual([['room', 'Room LOUNGE: floor here']]);
  });

  it('the marks the canvas draws for the fixes that wait (R-6.4 "Shown before Rebuild")', () => {
    let s = addClosing(closeHereFix(flagOf('slab-gap'))!)(REF);
    s = addClosing(notDoorwayFix(flagOf('doorway'))!)(s);
    s = setRoomFix(outdoorsFix(flagOf('slab-gap'), ground)!)(s);
    const living = ground.spaces![0]!;
    s = setRoomFix({ floor: 'ground', at: pointIn(living.o, living.h), name: null, slab: 'auto', ceiling: 'none' })(s);
    s = setStairFix({ floor: 'ground', at: pointIn(ground.stairs![1]!.outline), bottom: [2.6, 6.4], use: 'auto' })(s);
    const m = fixMarks(s, 'ground', ground, true);
    expect(m.lines).toEqual([{ a: [8.9, 8.9], b: [11.8, 8.9] }]);
    expect(m.removed).toEqual([{ a: [7, 5.6], b: [7, 6.8] }]);
    expect(m.rooms).toEqual(['ground-R001']);
    expect(m.points.map(p => p.kind)).toEqual(['outdoors', 'room']);
    expect(m.outdoors).toEqual([0]);
    expect(m.bottoms).toEqual([{ at: [2.6, 6.4] }]);
    expect(fixMarks(s, 'ground', ground, false)).toEqual({ lines: [], removed: [], rooms: [], points: [], outdoors: [], bottoms: [] });
  });
});

describe('the mock API\'s new overlay fixtures (WORK_BREAKDOWN R6)', () => {
  it('the reference building\'s two DXFs are known by their names or sha1; their plans hold the overlay\'s outlines', () => {
    expect(referenceFloorOf({ sha1: 'x', name: 'rooms-reference-ground.dxf' })).toBe(0);
    expect(referenceFloorOf({ sha1: 'x', name: 'C:/tmp/Rooms-Reference-UPPER.DXF' })).toBe(1);
    expect(referenceFloorOf({ sha1: REF.sources[1]!.sha1, name: 'other.dxf' })).toBe(1);
    expect(referenceFloorOf({ sha1: 'x', name: 'house.dwg' })).toBe(-1);
    const plan = referencePlan('a'.repeat(40), 0);
    expect(plan.layers).toContain('A-WALL');
    const walls = ground.parts.filter(p => p.kind === 'wall').length;
    expect(plan.items.layer.filter(l => plan.layers[l] === 'A-WALL').length).toBeGreaterThanOrEqual(walls);
    expect(plan.items.type.filter(t => t === 4).length).toBe(ground.rooms.length);
  });

  it('the overlay is re-keyed to the build\'s floors and sources; the flags with it; with no fix it is the fixture\'s', () => {
    const s: BuildSettings = {
      ...REF,
      sources: REF.sources.map((x, i) => ({ ...x, sha1: String(i).repeat(40) })),
      floors: REF.floors.map((f, i) => ({ ...f, key: i ? 'L2' : 'L1', source: String(i).repeat(40) })),
    };
    const o = roomsOverlayFor(s, sha => Number(sha[0]));
    expect(o.floors.map(f => [f.key, f.source.slice(0, 2)])).toEqual([['L1', '00'], ['L2', '11']]);
    expect(o.floors[0]!.spaces).toEqual(ground.spaces);
    expect(o.flags.map(f => [f.kind, f.floor])).toEqual(OV.flags.map(f => [f.kind, f.floor === 'ground' ? 'L1' : 'L2']));
    expect(o.flags.every(f => f.id.includes(`:${f.floor}:`))).toBe(true);
  });

  it('a "rebuild" with the fixes: the staff line drawn, the doorway gone, the area answered, the room named, the stair climbs', () => {
    let s = addClosing(notDoorwayFix(flagOf('doorway'))!)(REF);
    s = setRoomFix(outdoorsFix(flagOf('slab-gap'), ground)!)(s);
    const living = ground.spaces![0]!;
    s = setRoomFix({ floor: 'ground', at: pointIn(living.o, living.h), name: 'Living', slab: 'auto', ceiling: 'none' })(s);
    s = setStairFix({ floor: 'ground', at: pointIn(ground.stairs![1]!.outline), bottom: ground.stairs![1]!.outline[0]!, use: 'auto' })(s);
    const o = roomsOverlayFor(s, sha => REF.sources.findIndex(x => x.sha1 === sha));
    const g = o.floors[0]!;
    expect(g.closings).toEqual([]);
    expect(g.unfloored![0]!.answered).toBe(true);
    expect(g.spaces![0]).toMatchObject({ name: 'Living', ceiling: false });
    expect(g.stairs!.map(x => x.state)).toEqual(['climb', 'climb']);
    // the slab-gap, the doorway and the stair flags are answered; the others stay (RR: whatever the fixture holds besides,
    // e.g. the upper floor's cut X void since the builder flags every cut X hole)
    expect(o.flags.map(f => f.kind)).toEqual(OV.flags.map(f => f.kind).filter(k => !['slab-gap', 'doorway', 'stair'].includes(k)));
    expect(o.flags.map(f => f.kind).slice(0, 4)).toEqual(['room-open', 'room-names', 'stair-clash', 'hole-skipped']);
    const s2 = addClosing(closeHereFix(flagOf('slab-gap'))!)(REF);
    const g2 = roomsOverlayFor(s2, sha => REF.sources.findIndex(x => x.sha1 === sha)).floors[0]!;
    expect(g2.closings!.map(c => [c.kind, c.fix])).toEqual([['doorway', undefined], ['staff', 0]]);
    expect(g2.unfloored).toEqual([]);
  });
});
