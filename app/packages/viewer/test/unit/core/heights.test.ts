// Builder A: createHeights (DESIGN.md 5.5, 17.2 "heights"). Build settings: the floor group's home position and Walk level,
// fit scale (walls about the floor level), fit top (the house's door heads stay at 3.50 / 2.00 / 4.50 / 3.90 m wall height,
// the lintels gone at 2.00; panes reaching the top follow it), fit clip (sills and other panes cut at the top), the plinth
// whose foot stays on the ground at level 1.50, a 2.00 m wall height making the walls 2.00 m, the plan picture's y.
import { describe, expect, it, vi } from 'vitest';
import type { Mesh } from 'three';
import { fitDataOf } from '../../../src/core/build';
import { refitGeometry } from '../../../src/core/heights';
import { kitContext, worldY } from './kit';

const r2 = (v: number) => Math.round(v * 100) / 100;

describe('heights.apply on the house (fit top / clip, plinth)', () => {
  const ctx = kitContext('house');
  const ground = ctx.floorByKey.get('ground')!, upper = ctx.floorByKey.get('upper')!;
  const doors = ctx.model.openings.filter(o => o.floor === 'ground' && o.kind === 'door' && !o.glazed && o.lintel === 'lintel');
  const set = (gh: number, gl = 0.9) => ctx.heights.apply({ ground: { level: gl, height: gh }, upper: { level: 4.8, height: 3.5 } });
  /** Looking up from 0.5 m in each door: the height above the floor where the lintel is met (null: nothing). */
  const heads = () => doors.map(d => {
    const hit = ctx.readouts.cast('ground', [d.x, ground.level + 0.5, -d.y], [0, 1, 0], 8);
    return hit && / solid:top$/.test(hit.name) ? r2(hit.d + 0.5) : null;
  });
  const paneTopsAt = (z: number) => ctx.model.openings.filter(o => o.floor === 'ground' && o.glazed && !o.lintel && (o.head as number) >= 3.9 - 0.005)
    .map(d => ctx.readouts.cast('ground', [d.x - d.nx * 0.6, ground.level + z, -(d.y - d.ny * 0.6)], [d.nx, 0, -d.ny], 1.2)?.name ?? null);

  it('starts with the model: levels and heights, every lintel met at its door head', () => {
    expect(ctx.heights.settings).toEqual({ ground: { level: 0.9, height: 3.9 }, upper: { level: 4.8, height: 3.5 } });
    expect(doors.length).toBe(15);                                    // the ground floor's doors with a lintel
    expect(heads()).toEqual(doors.map(d => d.head));
  });
  it('3.50 m: the lintels still at the heads; 2.00 m: none left; 4.50 m: at the heads; back to 3.90 m', () => {
    set(3.5); expect(heads()).toEqual(doors.map(d => d.head));
    set(2.0); expect(heads().every(h => h === null)).toBe(true);
    set(4.5); expect(heads()).toEqual(doors.map(d => d.head));
    const tops = [...paneTopsAt(4.2), ...paneTopsAt(4.45)];
    expect(tops.length).toBeGreaterThan(0);
    expect(tops.every(n => n !== null && / pane:top$/.test(n))).toBe(true);    // panes that reach the top follow it up
    set(3.9); expect(heads()).toEqual(doors.map(d => d.head));
  });
  it('fit top refits per vertex: z0 stays, z1 -> H; at or below z0 the part collapses to its centre at H', () => {
    const lintels = ctx.built.fitted.ground!.find(m => m.name === 'ground solid:top')!;
    set(4.5);
    lintels.geometry.computeBoundingBox();
    expect(r2(lintels.geometry.boundingBox!.max.y - ground.modelLevel)).toBe(4.5);
    expect(r2(lintels.geometry.boundingBox!.min.y - ground.modelLevel)).toBe(3);
    set(2.0);
    const pos = lintels.geometry.getAttribute('position'), d = fitDataOf(lintels.geometry)!;
    for (let i = 0; i < pos.count; i += 97) {
      expect(pos.getY(i) - ground.modelLevel).toBeCloseTo(2.0, 5);
      expect(pos.getX(i)).toBeCloseTo(d.cx[i]!, 5);
      expect(pos.getZ(i)).toBeCloseTo(d.cz[i]!, 5);
    }
    set(3.9);
    const base = d.base;
    for (let i = 0; i < pos.count; i++) expect(pos.getY(i)).toBeCloseTo(base[3 * i + 1]!, 5);
  });
  it('fit clip: kept, cut at the wall top (2.00 m cuts the 3.00 m panes), edges too; the BVH refits', () => {
    const panes = ctx.built.fitted.ground!.find(m => m.name === 'ground pane:clip')!;
    const edges = ground.rise.find(r => r.mesh === panes)!.edges!;
    const refit = vi.spyOn(panes.geometry.boundsTree!, 'refit');
    set(2.0);
    for (const g of [panes.geometry, edges.geometry]) {
      g.computeBoundingBox();
      expect(r2(g.boundingBox!.max.y - ground.modelLevel)).toBe(2);
    }
    expect(refit).toHaveBeenCalled();
    const hit = ctx.readouts.downHit('ground', ...centreOf(panes), 3);
    expect(hit === null || hit <= 2.0 + 1e-6).toBe(true);
    set(3.9);
    panes.geometry.computeBoundingBox();
    expect(r2(panes.geometry.boundingBox!.max.y - ground.modelLevel)).toBe(3);
  });
  it('the plinth keeps its foot on the ground at level 1.50 (0 to 1.50 m), the Walk level follows', () => {
    set(3.9, 1.5);
    expect(ground.level).toBe(1.5);
    expect(ground.group.position.y).toBeCloseTo(0.6, 12);
    for (const m of ctx.built.plinths) {
      const [lo, hi] = worldY(m);
      expect(lo).toBeCloseTo(0, 6);
      expect(hi).toBeCloseTo(1.5, 6);
    }
    expect(ctx.heights.settings.ground).toEqual({ level: 1.5, height: 3.9 });
  });
  it('a 2.00 m wall height makes the walls themselves 2.00 m (fit scale about the floor level)', () => {
    set(2.0, 1.5);
    const walls = ground.rise.find(r => r.scales)!;
    const [lo, hi] = worldY(walls.mesh as Mesh);
    expect(r2(lo)).toBe(1.5);
    expect(r2(hi - lo)).toBe(2);
    expect(walls.mesh.scale.y).toBeCloseTo(2.0 / 3.9, 12);
    expect(walls.edges!.scale.y).toBeCloseTo(2.0 / 3.9, 12);
    expect(walls.mesh.position.y).toBeCloseTo(0.9 * (1 - 2.0 / 3.9), 12);
    const own = ground.rise.find(r => r.fit === 'fixed')!;
    expect([own.mesh.scale.y, own.mesh.position.y]).toEqual([1, 0]);
    set(3.9, 0.9);
    expect(upper.group.position.y).toBe(0);
  });
  it('emits bus "settings" with a copy of the settings', () => {
    const seen = vi.fn();
    ctx.bus.on('settings', seen);
    set(3.6, 1.0);
    expect(seen).toHaveBeenCalledTimes(1);
    expect(seen.mock.calls[0]![0].settings).toEqual({ ground: { level: 1.0, height: 3.6 }, upper: { level: 4.8, height: 3.5 } });
    expect(seen.mock.calls[0]![0].settings).not.toBe(ctx.heights.settings);
    set(3.9, 0.9);
  });
  it('ignores unknown floors and unreadable values (keeps the old ones)', () => {
    ctx.heights.apply({ nowhere: { level: 1, height: 1 }, ground: { level: Number.NaN, height: -2 } });
    expect(ctx.heights.settings.ground).toEqual({ level: 0.9, height: 3.9 });
  });
});

describe('heights.apply on the bank (scale, levels) and on features (the picture follows its floor)', () => {
  it('bank: the upper level moves its group; the lintels scale with the walls (follow, no fit)', () => {
    const ctx = kitContext('bank-v2');
    const L2 = ctx.floorByKey.get('L2')!;
    ctx.heights.apply({ L1: { level: 0, height: 3.7 }, L2: { level: 5.0, height: 4.0 } });
    expect(L2.level).toBe(5.0);
    expect(L2.group.position.y).toBeCloseTo(1.3, 12);
    const solid = L2.rise.find(r => r.mesh.name === 'L2 solid:follow')!;
    expect(solid.mesh.scale.y).toBeCloseTo(4 / 3.7, 12);
    expect(solid.mesh.position.y).toBeCloseTo(3.7 * (1 - 4 / 3.7), 12);
    expect(ctx.built.fitted.L2).toEqual([]);
  });
  it('features: the ground floor picture sheet lies at the floor level setting', () => {
    const ctx = kitContext('features', { pictures: { G: 'data:image/png;base64,AA==' } });
    const sheet = ctx.pictures!.sheets[0]!;
    expect(sheet.name).toBe('G plan picture');
    ctx.heights.apply({ G: { level: 1.0, height: 3.0 }, U: { level: 3.6, height: 2.8 } });
    expect(sheet.position.y).toBeCloseTo(0.4, 12);
    const [lo] = worldY(sheet);
    expect(lo).toBeCloseTo(1.005, 6);
  });
});

describe('refitGeometry', () => {
  it('leaves a geometry without fit data alone', () => {
    const ctx = kitContext('mini');
    const wall = ctx.floors[0]!.rise[0]!.mesh;
    expect(refitGeometry(wall.geometry, 1)).toBe(false);
  });
});

function centreOf(m: Mesh): [number, number] {
  m.geometry.computeBoundingBox();
  const b = m.geometry.boundingBox!;
  return [(b.min.x + b.max.x) / 2, -(b.min.z + b.max.z) / 2];
}
