// Builder A: createReadouts (DESIGN.md 11.7, 17.2 "readouts"): upHit / downHit / rayHit / cast against known parts, by
// raycasting the real build in Node (three-mesh-bvh per mesh). The bank's glass partitions stand at 2.60 m with nothing
// above, its parapet at the railing height, the ATM gap closed to 3.70 m, the stair steps one riser apart; the features
// model's wall, lintel and the Walk level after a Build settings change.
import { describe, expect, it } from 'vitest';
import { kitContext } from './kit';

const r3 = (v: number | null) => (v === null ? null : Math.round(v * 1000) / 1000);

describe('readouts on features.model.json', () => {
  const ctx = kitContext('features');
  it('rayHit: a level ray meets the east wall from 1 m west of its face, by name', () => {
    const hit = ctx.readouts.rayHit('G', 8.8, 2, 1.2, 1, 0, 3);
    expect(hit && { d: r3(hit.d), name: hit.name }).toEqual({ d: 1, name: 'G solid:follow' });
    expect(ctx.readouts.rayHit('G', 8.8, 2, 1.2, 1, 0, 0.5)).toBeNull();
  });
  it('upHit: in the door the lintel at its head (2.10 m); in the room nothing up to the floor above', () => {
    expect(r3(ctx.readouts.upHit('G', 4.5, 0.1, 1.0))).toBe(2.1);
    expect(ctx.readouts.upHit('G', 3, 3, 1.0)).toBeNull();
  });
  it('downHit: the wall top from above; the deck is no collider, so the upper floor reads nothing there', () => {
    expect(r3(ctx.readouts.downHit('G', 9.9, 2, 3.5))).toBe(3);
    expect(ctx.readouts.downHit('U', 1.5, 2, 2)).toBeNull();
    expect(r3(ctx.readouts.downHit('U', 7, 2.25, 2))).toBe(0.45);          // the low wall
  });
  it('cast: a world-space ray (the house page\'s), unit direction or not', () => {
    const hit = ctx.readouts.cast('G', [8.8, 0.6 + 1.2, -2], [2, 0, 0], 3);
    expect(hit && r3(hit.d)).toBe(1);
  });
  it('only visible colliders count; unknown floors read null', () => {
    const glass = ctx.floorByKey.get('G')!.colliders.find(m => m.name === 'G glass:own')!;
    const skin = ctx.floorByKey.get('G')!.colliders.find(m => m.name === 'G walk skins (glass)')!;
    expect(ctx.readouts.rayHit('G', 6.5, 3, 1.2, 0, 1, 2)?.name).toMatch(/glass/);
    glass.visible = false; skin.visible = false;
    expect(ctx.readouts.rayHit('G', 6.5, 3, 1.2, 0, 1, 2)).toBeNull();
    glass.visible = true; skin.visible = true;
    expect(ctx.readouts.upHit('nowhere', 0, 0)).toBeNull();
    expect(ctx.readouts.cast('nowhere', [0, 0, 0], [1, 0, 0], 1)).toBeNull();
  });
  it('heights above the level Walk uses now (Build settings move the floor)', () => {
    ctx.heights.apply({ G: { level: 1.6, height: 3.0 }, U: { level: 3.6, height: 2.8 } });
    expect(r3(ctx.readouts.upHit('G', 4.5, 0.1, 1.0))).toBe(2.1);
    expect(r3(ctx.readouts.rayHit('G', 8.8, 2, 1.2, 1, 0, 3)?.d ?? null)).toBe(1);
    ctx.heights.apply({ G: { level: 0.6, height: 3.0 }, U: { level: 3.6, height: 2.8 } });
  });
});

describe('readouts on the bank v2 (the structure the bank test reads, in Node)', () => {
  const ctx = kitContext('bank-v2');
  const M = ctx.model;
  it('the glass partitions stand to their type\'s height (2.60 m) with nothing above', () => {
    const parts = M.probes.filter(g => g.what === 'glass partition');
    expect(parts.length).toBeGreaterThan(0);
    for (const g of parts) {
      const side = g.inside[0] ?? 1, nx = g.nx * side, ny = g.ny * side;
      const at = (h: number) => { const hit = ctx.readouts.rayHit(g.floor, g.x + nx * 0.5, g.y + ny * 0.5, h, -nx, -ny, 0.6); return hit && /glass/.test(hit.name) ? hit.d : null; };
      expect(at((g.top ?? 2.6) - 0.1), g.id).not.toBeNull();
      expect(at((g.top ?? 2.6) + 0.15), g.id).toBeNull();
    }
  });
  it('the ATM gap is closed to the top (3.70 m)', () => {
    for (const [k, cs] of Object.entries(M.closures)) for (const c of cs) expect(r3(ctx.readouts.upHit(k, c.x, c.y, 0.5))).toBeCloseTo(3.7, 2);
  });
  it('the stair steps sit one riser apart', () => {
    const steps = M.parts.filter(p => p.kind === 'step');
    expect(steps.length).toBe(16);
    const H = M.floors[1]!.level - M.floors[0]!.level, riser = H / Math.ceil(H / 0.18 - 1e-9);
    const flights = new Map<string, number[]>();
    for (const p of steps) {
      let x = 0, y = 0; p.o.forEach(q => { x += q[0]; y += q[1]; });
      const top = ctx.readouts.downHit(p.floor, x / p.o.length, y / p.o.length, 3.0);
      expect(top, p.label).not.toBeNull();
      expect(Math.abs(top! - p.z1), p.label).toBeLessThan(0.02);
      const flight = (p.label ?? '').replace(/ step [0-9]+ (up|down)$/, '');
      flights.set(flight, [...(flights.get(flight) ?? []), top!]);
    }
    for (const tops of flights.values()) {
      tops.sort((a, b) => Math.abs(a) - Math.abs(b)).forEach((z, i) => expect(Math.abs(Math.abs(z) - (i + 1) * riser)).toBeLessThan(0.01));
    }
  });
});
