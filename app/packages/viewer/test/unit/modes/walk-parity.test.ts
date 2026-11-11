// @vitest-environment happy-dom
// The walk-parity golden (docs/rooms/DESIGN.md R-13, ACCEPTANCE RA-2; scaffold R0; frozen): the six models of before the
// rooms milestone walk in this viewer exactly as they did in the viewer of commit 66b4c06, within 1e-9 m. The recipes
// and the recorder are in test/tools/record-walk-parity.ts; the golden's own sha1 is pinned here, so nobody "fixes" a
// difference by recording again.
import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { BASE, GOLDEN, MODELS, parityDiffs, recordWalkParity, runWalkParity, sha1, type WalkParity } from '../../tools/record-walk-parity';

/** sha1 of test/fixtures/walk-parity.json as R0 recorded it on 11 Nov 2026 from the unchanged viewer. */
const GOLDEN_SHA1 = '13f96bcb5cb709e9249846a7bd712bd0e2c33d50';
const RECORD = process.env.WT_RECORD_WALK_PARITY === '1';
const MODEL_SHA1: Record<string, string> = {
  'bank-v1': '4b02dc17f286db688a55f0784d0b2fbb5642cb79', 'bank-v2': 'c3a9408304a240b83c36f5c5c53db56b50a72c64',
  hotel: '6ab03075088689f7b694f71c422927a289a7005e', house: 'e43270cc0c9be5c00025881f09762325cfc5f92f',
  mini: 'a469ffbe5a934e0d05a5ef7be6bd3dd83fbec45c', suite: '34a02b1f6a28d8dce7ce660f720ea418f45b8f36',
};

const golden = (): WalkParity => JSON.parse(readFileSync(GOLDEN, 'utf8')) as WalkParity;
type Row = Record<string, any>;                                     // eslint-disable-line @typescript-eslint/no-explicit-any

describe('walk parity: old models walk as they did before the rooms milestone', { timeout: 600_000 }, () => {
  // defined only when recording, so that a plain run has no skipped test (WORK_BREAKDOWN R0 "Done when")
  if (RECORD) {
    it('records the golden (only from the viewer of 66b4c06)', () => {
      const g = recordWalkParity();
      expect(Object.keys(g.models)).toEqual(MODELS.map(m => m[0]));
    });
  }

  it('the golden is the one R0 recorded: its sha1, the viewer tree it names, the six models', () => {
    expect(sha1(readFileSync(GOLDEN))).toBe(GOLDEN_SHA1);
    const g = golden();
    expect([g.format, g.base]).toEqual(['walk-parity/1', BASE]);
    expect(g.viewerTree).toMatch(/^[0-9a-f]{40}$/);
    expect(Object.fromEntries(Object.entries(g.models).map(([k, v]) => [k, v.sha1]))).toEqual(MODEL_SHA1);
  });

  it('the golden holds every recipe with real walks in it', () => {
    const g = golden();
    let walls = 0, doors = 0, glass = 0, edges = 0, spots = 0, through = 0, stuck = 0;
    for (const [name] of MODELS) {
      const res = g.models[name]!.results as Row;
      expect(Object.keys(res).filter(k => k !== 'flight')).toEqual(['floors', 'keys', 'pages', 'dblclick', 'ghost', 'eye']);
      for (const f of Object.values(res.floors) as Row[]) {
        walls += f.walls.spots.length; doors += f.doors.length; glass += f.glass.length; edges += f.edges.walks.length; spots += f.spots.length;
        through += f.walls.spots.filter((s: Row) => s.crosses).length;
        stuck += f.walls.spots.filter((s: Row) => typeof s.clearance === 'number' && s.clearance < 0.15).length;
      }
      expect(res.keys.frames.length).toBe(12);
      expect(res.dblclick.length).toBe(6);
    }
    expect({ through, stuck }).toEqual({ through: 0, stuck: 0 });   // the old walker never went through a wall
    expect(walls).toBeGreaterThan(150);
    expect(doors).toBeGreaterThan(200);
    expect(glass).toBeGreaterThan(40);
    expect(edges).toBeGreaterThan(60);
    expect(spots).toBe(25 * 11);                                     // 11 floors in the six models
  });

  it("the hotel's F1 flight stops the walk about 1.3 m in, at its step parts", () => {
    const flight = (golden().models.hotel!.results as Row).flight as Row[];
    expect(flight.length).toBe(3);
    for (const row of flight) {
      expect(row.start.onFloor).toBe(true);
      expect(row.floor).toBe('F1');
      expect(row.y).toBeCloseTo(1.6, 9);                             // the eye stays at the floor's level + 1.6 m: no climbing
      expect(row.intoFlight).toBeGreaterThan(0.1);
      expect(row.intoFlight).toBeLessThan(0.5);
      expect(row.moved).toBeGreaterThan(1.2);
      expect(row.moved).toBeLessThan(1.5);
      expect(row.knee.name).toBe('F1 step:own');
    }
  });

  it.each(MODELS.map(m => m[0]))('%s walks as recorded (every end position within 1e-9 m)', name => {
    const g = golden().models[name]!, now = runWalkParity(name)[name]!;
    expect(now.sha1).toBe(g.sha1);
    expect(parityDiffs(g.results, now.results)).toEqual([]);
  });

  it('the comparison sees 1e-8 m and lets 1e-10 m pass', () => {
    const a = { floors: { L1: { walls: [{ ex: 1.25, crosses: false }] } } };
    expect(parityDiffs(a, { floors: { L1: { walls: [{ ex: 1.25 + 1e-10, crosses: false }] } } })).toEqual([]);
    expect(parityDiffs(a, { floors: { L1: { walls: [{ ex: 1.25 + 1e-8, crosses: false }] } } })).toHaveLength(1);
    expect(parityDiffs(a, { floors: { L1: { walls: [{ ex: 1.25, crosses: true }] } } })).toHaveLength(1);
    expect(parityDiffs(a, { floors: { L1: { walls: [] } } })).toHaveLength(1);
    expect(parityDiffs(a, { floors: {} })).toHaveLength(1);
  });
});
