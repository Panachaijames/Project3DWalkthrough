// @vitest-environment happy-dom
// The walk-parity golden (docs/rooms/DESIGN.md R-13, ACCEPTANCE RA-2; scaffold R0; frozen): the six models of before the
// rooms milestone walk in this viewer exactly as they did in the viewer of commit 66b4c06, within 1e-9 m. The recipes
// and the recorder are in test/tools/record-walk-parity.ts; the golden's own sha1 is pinned here, so nobody "fixes" a
// difference by recording again.
//
// 16 Nov 2026 (the owner's request; rooms/DESIGN.md "Amended after the independent review", R-9): the hotel's F1 flight is
// 16 `step` blocks that stopped the walk; the viewer now makes such a complete flight a stairway when it loads the model
// (src/model/upgrade.ts), so the hotel walks on its feet and climbs to F2. The hotel's entry ALONE was recorded again
// (recordHotelParity); the other five entries are R0's, byte for byte: ENTRY_SHA1 pins each of them as it was in the
// golden of 11 Nov (sha1 13f96bcb5cb709e9249846a7bd712bd0e2c33d50).
import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { BASE, GOLDEN, MODELS, parityDiffs, recordHotelParity, recordWalkParity, runWalkParity, sha1, type WalkParity } from '../../tools/record-walk-parity';

/** sha1 of test/fixtures/walk-parity.json: R0's recording of 11 Nov 2026 with the hotel's entry recorded again on 16 Nov. */
const GOLDEN_SHA1 = 'ffac9168ecb2fa826ec8702646b3c21f715c81ec';
/**
 * sha1 of JSON.stringify(entry) of the five entries nobody recorded again, taken from R0's golden of 11 Nov 2026 (there
 * the hotel's was 7cf9e4311b0db827bd53292327ee4d33cc1ca15f).
 */
const ENTRY_SHA1: Record<string, string> = {
  'bank-v1': '579729b4eeaef9c613b19bab04805e8203f761a6', 'bank-v2': '7141c2ac79f92652a1281720f709c717215eaae2',
  house: 'f52e95474d083193a2cac53ea26849eabc01409b', mini: 'e41c54915ad29e775bccd1491f4527745b4a862c',
  suite: 'f941dc859f0d0b66bb01b63245c9995ef8ac6d87',
};
const RECORD = process.env.WT_RECORD_WALK_PARITY === '1';
const RECORD_HOTEL = process.env.WT_RECORD_WALK_PARITY === 'hotel';
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

  if (RECORD_HOTEL) {
    it("records the hotel's entry alone (16 Nov 2026: its F1 flight climbs)", () => {
      const g = recordHotelParity();
      expect(Object.keys(g.models)).toEqual(MODELS.map(m => m[0]));
    });
  }

  it("the five entries nobody recorded again are R0's, byte for byte", () => {
    const g = golden();
    const now = Object.fromEntries(Object.entries(g.models).filter(([k]) => k !== 'hotel').map(([k, v]) => [k, sha1(JSON.stringify(v))]));
    expect(now).toEqual(ENTRY_SHA1);
    // and the file is as the recorder writes it, so those entries' bytes in it are R0's too
    expect(JSON.stringify(g, null, 1) + '\n').toBe(readFileSync(GOLDEN, 'utf8'));
  });

  it('the golden is the one R0 recorded, with the hotel recorded again: its sha1, the viewer tree it names, the six models', () => {
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

  it("the hotel's F1 flight now climbs to F2 and comes down again (the owner's request, 16 Nov 2026)", () => {
    const flight = (golden().models.hotel!.results as Row).flight as Row[];
    expect(flight.length).toBe(3);
    for (const row of flight) {
      expect(row.start.onFloor).toBe(true);
      // up: nothing stops the 6.5 m walk; the floor named is F2, the foot on its level (2.90), the eye 1.6 m above it
      expect(row.up.moved).toBeGreaterThan(6.45);
      expect(row.up.floor).toBe('F2');
      expect(row.up.foot).toBeCloseTo(2.9, 5);
      expect(row.up.y).toBeCloseTo(2.9 + 1.6, 5);
      expect(row.up.intoFlight).toBeGreaterThan(4.33 + 1.0);         // past the 4.33 m of the flight, on F2's slab
      // and down again to where it started, on F1
      expect(row.down.moved).toBeGreaterThan(6.45);
      expect(row.down.floor).toBe('F1');
      expect(row.down.foot).toBeCloseTo(0, 5);
      expect(row.down.y).toBeCloseTo(1.6, 5);
      expect(row.down.z).toBeCloseTo(2.6, 5);
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
