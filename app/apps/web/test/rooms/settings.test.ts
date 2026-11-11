// R6 (docs/rooms/ACCEPTANCE.md 2.3 R6; DESIGN.md R-1.2, R-1.3, R-5.1, R-6.2, R-12.6): the settings changes of the rooms
// milestone as pure functions: which way a draft is built and the switch, the default ceiling height, the new fixes
// (each matched by its points, never by a list index), "the floor runs past it", the API's refusals said before the save,
// and the checklist's warning line.
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { describe, expect, it } from 'vitest';
import {
  addClosing, ceilingsOn, cleanRoomName, closingsOf, defaultCeilingHeight, floorIssues, otherFixCount, removeClosing, removeRoomFix,
  removeStairFix, roomFixesOf, roomsIssues, RULES_EARLIER_TEXT, RULES_NEED_NETWORK, rulesOf, setCeilings, setFloorPast, setRoomFix,
  setRules, setStairFix, stairFixesOf, updateFloor,
} from '@/build/settingsEdit';
import { checklist, RULES_ITEM } from '@/build/steps';
import { NEW_RULES, OLD_RULES, type BuildDetail, type BuildSettings, type SetAside } from '@/upload/contracts';
import { FIXTURES_DIR } from '../mock-api/fixtures';

const load = (...p: string[]) => JSON.parse(readFileSync(path.join(FIXTURES_DIR, ...p), 'utf8')) as BuildSettings;
const BANK = load('upload', 'settings', 'bank.json');
const BANK_ROOMS = load('upload', 'settings', 'bank-rooms.json');
const HOUSE_ROOMS = load('upload', 'settings', 'house-rooms.json');
const SUITE = load('upload', 'settings', 'suite.json');
const TOWER = load('upload', 'settings', 'tower.json');
const REF = load('rooms', 'settings.reference.json');

const detail = (s: BuildSettings): BuildDetail => ({
  id: '20261111T120000-abcdef', projectId: 'p', createdAt: '', updatedAt: '', status: 'open', savedVersion: null, sourceNames: [],
  runStatus: 'done', url: '', sources: [], settings: s, settingsRevision: 2, layersReviewedAt: '2026-11-11T12:00:00Z', suggestions: {},
  run: null, result: null, urls: { settings: '', run: '', cancel: '', save: '' },
}) as unknown as BuildDetail;

describe('which way a draft is built (R-1.2, R-1.3, R-12.6)', () => {
  it('a settings document without the three keys is the earlier way; the *-rooms fixtures and the reference are new', () => {
    expect(rulesOf(BANK)).toBe('earlier');
    expect(rulesOf(SUITE)).toBe('earlier');
    for (const s of [BANK_ROOMS, HOUSE_ROOMS, REF]) expect(rulesOf(s)).toBe('new');
    expect(rulesOf({ options: { ...BANK.options, slabs: 'network', ceilings: 'off', stairs: 'climb' } })).toBe('new');
    expect(ceilingsOn(BANK_ROOMS)).toBe(true);
    expect(ceilingsOn(setCeilings(false)(BANK_ROOMS))).toBe(false);
    expect(ceilingsOn(BANK)).toBe(false);
  });

  it('setRules writes the three options together, in one change; the same rules again is no change', () => {
    const now = setRules('new')(BANK);
    expect(now.options).toEqual({ ...BANK.options, ...NEW_RULES });
    expect(now.options).toEqual(BANK_ROOMS.options);
    const back = setRules('earlier')(now);
    expect(back.options).toEqual({ ...BANK.options, ...OLD_RULES });
    expect(setRules('new')(now)).toBe(now);
    expect(setRules('earlier')(back)).toBe(back);
    // a legal mix (network, ceilings off) put back to the earlier way takes all three keys
    expect(setRules('earlier')(setCeilings(false)(now)).options).toMatchObject(OLD_RULES);
    expect(setCeilings(true)(now)).toBe(now);
  });

  it('the checklist says the earlier way in its last line, a warning that never blocks', () => {
    const items = checklist(detail(BANK), BANK);
    expect(items.at(-1)).toEqual({ id: RULES_ITEM, step: 'floors', text: RULES_EARLIER_TEXT, level: 'warn' });
    expect(items.filter(i => i.level === 'block')).toEqual([]);
    expect(checklist(detail(BANK_ROOMS), BANK_ROOMS).find(i => i.id === RULES_ITEM)).toBeUndefined();
  });

  it('the old floor plates with ceilings or climbable stairs are refused before the save, in the API\'s words', () => {
    const bad = { ...BANK, options: { ...BANK.options, slabs: 'closed-rooms' as const, ceilings: 'auto' as const, stairs: 'climb' as const } };
    expect(roomsIssues(bad).map(i => i.path)).toEqual(['options/ceilings', 'options/stairs']);
    expect(roomsIssues(bad).every(i => i.message.startsWith(RULES_NEED_NETWORK))).toBe(true);
    expect(roomsIssues(BANK)).toEqual([]);
    expect(roomsIssues(BANK_ROOMS)).toEqual([]);
    expect(checklist(detail(bad), bad).filter(i => i.level === 'block').map(i => i.id)).toEqual(['issue:options/ceilings', 'issue:options/stairs']);
  });
});

describe('ceiling heights (R-5.1)', () => {
  it('the default: min(3.00, wall height - 0.30), under the floor above less 2 cm; the test projects\' values', () => {
    expect([0, 1].map(i => defaultCeilingHeight(BANK, i))).toEqual([3, 3]);
    expect([0, 1].map(i => defaultCeilingHeight(HOUSE_ROOMS, i))).toEqual([3, 3]);
    expect(HOUSE_ROOMS.floors.map(f => f.ceilingHeight)).toEqual([3, 2.9]);
    expect(TOWER.floors.map((_, i) => defaultCeilingHeight(TOWER, i))).toEqual([3, 3]);
    expect(defaultCeilingHeight(SUITE, 0)).toBe(2.7);
    // a low storey: the floor above's underside less 2 cm wins
    const low = updateFloor(1, { level: 2.9 })(updateFloor(0, { wallHeight: 3.5 })(BANK));
    expect(defaultCeilingHeight(low, 0)).toBe(2.63);
    expect(defaultCeilingHeight(updateFloor(0, { wallHeight: 0 })(BANK), 0)).toBeNull();
    expect(defaultCeilingHeight(BANK, 5)).toBeNull();
  });

  it('a typed height is 0.5 - 20 m; empty (null) is the default', () => {
    expect(floorIssues(updateFloor(0, { ceilingHeight: 2.6 })(BANK_ROOMS))).toEqual([]);
    expect(floorIssues(updateFloor(0, { ceilingHeight: null })(BANK_ROOMS))).toEqual([]);
    for (const v of [0.4, 21, -1]) {
      expect(floorIssues(updateFloor(1, { ceilingHeight: v })(BANK_ROOMS)).map(i => i.path)).toEqual(['floors/1/ceilingHeight']);
    }
  });
});

describe('the fixes (R-6.2)', () => {
  const a: [number, number] = [8.9, 8.9], b: [number, number] = [11.8, 8.9];

  it('a closing line or a removed closing, by its segment (either order, 5 mm); kept to the millimetre; Remove by segment', () => {
    const s1 = addClosing({ floor: 'ground', a, b, use: 'line' })(REF);
    expect(closingsOf(s1)).toEqual([{ floor: 'ground', a, b, use: 'line' }]);
    expect(addClosing({ floor: 'ground', a: b, b: a, use: 'line' })(s1)).toBe(s1);
    const s2 = addClosing({ floor: 'ground', a: [7.00012, 5.6], b: [7, 6.8004], use: 'none' })(s1);
    expect(closingsOf(s2)[1]).toEqual({ floor: 'ground', a: [7, 5.6], b: [7, 6.8], use: 'none' });
    // the same segment with the other use replaces the fix in its place
    const s3 = addClosing({ floor: 'ground', a: b, b: a, use: 'none' })(s2);
    expect(closingsOf(s3).map(c => c.use)).toEqual(['none', 'none']);
    expect(addClosing({ floor: 'ground', a, b: a, use: 'line' })(REF)).toBe(REF);           // no length
    expect(closingsOf(removeClosing({ floor: 'ground', a: b, b: a, use: 'line' })(s2))).toEqual([closingsOf(s2)[1]]);
    expect(removeClosing({ floor: 'upper', a, b, use: 'line' })(s2)).toBe(s2);
    expect(otherFixCount(s2)).toBe(2);
  });

  it('a room fix: one per room point; the panel\'s change replaces it; nothing asked takes it out', () => {
    const at: [number, number] = [3.5851, 5.0];
    const s1 = setRoomFix({ floor: 'ground', at, name: '  Living\n', slab: 'auto', ceiling: 'auto' })(REF);
    expect(roomFixesOf(s1)).toEqual([{ floor: 'ground', at: [3.585, 5], name: 'Living', slab: 'auto', ceiling: 'auto' }]);
    const s2 = setRoomFix({ floor: 'ground', at: [3.585, 5], name: 'Living', slab: 'none', ceiling: 'none' }, [3.585, 5])(s1);
    expect(roomFixesOf(s2)).toEqual([{ floor: 'ground', at: [3.585, 5], name: 'Living', slab: 'none', ceiling: 'none' }]);
    expect(setRoomFix(roomFixesOf(s2)[0]!)(s2)).toBe(s2);
    const s3 = setRoomFix({ floor: 'upper', at: [5, 5], name: null, slab: 'floor', ceiling: 'auto' })(s2);
    expect(roomFixesOf(s3).length).toBe(2);
    expect(roomFixesOf(setRoomFix({ floor: 'ground', at: [3.585, 5], name: ' ', slab: 'auto', ceiling: 'auto' })(s3))).toEqual([roomFixesOf(s3)[1]]);
    expect(roomFixesOf(removeRoomFix({ floor: 'upper', at: [5, 5] })(s3))).toEqual(roomFixesOf(s2));
    expect(removeRoomFix({ floor: 'upper', at: [9, 9] })(s3)).toBe(s3);
  });

  it('a room name: one line of at most 200 characters, text only (markup is just text); a longer one is refused', () => {
    expect(cleanRoomName('<img src=x onerror=alert(1)>')).toBe('<img src=x onerror=alert(1)>');
    expect(cleanRoomName('a\tb\u0085c')).toBe('a b c');
    expect(cleanRoomName('x'.repeat(250))).toBe('x'.repeat(200));
    expect(cleanRoomName('   ')).toBeNull();
    expect(cleanRoomName(null)).toBeNull();
    const long = { ...REF, fixes: { ...REF.fixes, rooms: [{ floor: 'ground', at: [1, 1] as [number, number], name: 'y'.repeat(201), slab: 'auto' as const, ceiling: 'auto' as const }] } };
    expect(roomsIssues(long).map(i => i.path)).toEqual(['fixes/rooms/0/name']);
  });

  it('a stair fix: the bottom, keep as lines, climb as drawn; "Decide automatically" takes it out', () => {
    const at: [number, number] = [3.1, 8.0];
    const s1 = setStairFix({ floor: 'ground', at, bottom: [2.6, 6.4], use: 'auto' })(REF);
    expect(stairFixesOf(s1)).toEqual([{ floor: 'ground', at, bottom: [2.6, 6.4], use: 'auto' }]);
    const s2 = setStairFix({ floor: 'ground', at, bottom: [2.6, 6.4], use: 'lines' }, at)(s1);
    expect(stairFixesOf(s2)).toEqual([{ floor: 'ground', at, bottom: [2.6, 6.4], use: 'lines' }]);
    expect(stairFixesOf(setStairFix({ floor: 'ground', at, bottom: null, use: 'auto' }, at)(s2))).toEqual([]);
    expect(stairFixesOf(removeStairFix({ floor: 'ground', at })(s2))).toEqual([]);
  });

  it('the set-aside tick "The floor runs past it": written only when ticked', () => {
    const ref: SetAside = { floor: 'ground', source: REF.sources[0]!.sha1, key: '1A', sig: 'a'.repeat(12), rsig: '', elementId: null, layer: 'A-WALL', note: '' };
    const s0 = { ...REF, fixes: { ...REF.fixes, setAside: [ref] } };
    const s1 = setFloorPast('ground', '1A', true)(s0);
    expect(s1.fixes.setAside).toEqual([{ ...ref, floorPast: true }]);
    expect(setFloorPast('ground', '1A', true)(s1)).toBe(s1);
    const s2 = setFloorPast('ground', '1A', false)(s1);
    expect(s2.fixes.setAside).toEqual([ref]);
    expect('floorPast' in s2.fixes.setAside[0]!).toBe(false);
    expect(setFloorPast('upper', '1A', true)(s0)).toBe(s0);
  });

  it('the 5,000 "other fixes" count the new lists too', () => {
    const many = Array.from({ length: 2501 }, (_, i) => ({ floor: 'ground', a: [i, 0] as [number, number], b: [i, 1] as [number, number], use: 'line' as const }));
    const rooms = Array.from({ length: 2500 }, (_, i) => ({ floor: 'ground', at: [i, 5] as [number, number], name: null, slab: 'floor' as const, ceiling: 'auto' as const }));
    const s = { ...REF, fixes: { ...REF.fixes, closings: many, rooms } };
    expect(otherFixCount(s)).toBe(5001);
    expect(roomsIssues(s).map(i => i.path)).toEqual(['fixes']);
  });
});
