// The tracer climb (rooms WORK_BREAKDOWN R4 "first task"; ACCEPTANCE 2.3): in Node, on the reference building's model, up
// the stair S1 along its walking line onto the upper slab and down again, with the constants of DESIGN R-9.10. Its trace
// is written to WT_TMP/tracer-climb.json when WT_TMP is set (the figures at the top of docs/rooms/contract-issues/R4.md).
import { mkdirSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { describe, expect, it } from 'vitest';
import type { Vec2 } from '../../../src/contracts';
import { r3, referenceRig } from './climb-kit';

describe('the tracer climb on the reference building', () => {
  it('walks up S1 onto the upper slab and down again', () => {
    const rig = referenceRig(), s = rig.s, st = rig.model.stairways![0]!;
    const line = st.walk as Vec2[];
    const row = () => ({ plan: rig.plan().map(r3), foot: r3(s.foot), floor: s.floor.key });
    const trace: Record<string, unknown> = { stair: st.id, risers: st.risers, riser: st.riser, constants: 'R-9.10' };

    rig.put(st.from, line[0]![0], line[0]![1]);
    const up: unknown[] = [row()];
    let maxRise = 0, maxDrop = 0, last = s.foot;
    const each = () => { maxRise = Math.max(maxRise, s.foot - last); maxDrop = Math.max(maxDrop, last - s.foot); last = s.foot; };
    for (const p of line.slice(1)) { rig.to(p[0], p[1], each); up.push(row()); }
    const a = line[line.length - 2]!, b = line[line.length - 1]!;
    rig.go(b[0] - a[0], b[1] - a[1], 1.0, each);
    up.push(row());
    trace.up = up;
    expect(s.foot).toBeCloseTo(rig.floor(st.to).level, 2);
    expect(s.floor.key).toBe(st.to);

    const down: unknown[] = [row()];
    for (const p of line.slice(0, -1).reverse()) { rig.to(p[0], p[1], each); down.push(row()); }
    trace.down = down;
    trace.maxRisePer5cm = r3(maxRise); trace.maxDropPer5cm = r3(maxDrop);
    expect(s.foot).toBeCloseTo(rig.floor(st.from).level, 2);
    expect(s.floor.key).toBe(st.from);
    expect(Math.hypot(s.pos.x - line[0]![0], -s.pos.z - line[0]![1])).toBeLessThan(0.05);
    expect(maxRise).toBeLessThanOrEqual(0.25 + 1e-6);
    expect(maxDrop).toBeLessThanOrEqual(0.30 + 1e-6);

    if (process.env.WT_TMP) {
      mkdirSync(process.env.WT_TMP, { recursive: true });
      writeFileSync(path.join(process.env.WT_TMP, 'tracer-climb.json'), JSON.stringify(trace, null, 1));
    }
  });
});
