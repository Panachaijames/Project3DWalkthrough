// Scaffold: the shared test context (test/harness/context.ts) works in plain Node with the fake renderer on every
// fixture model: floors, colliders, walkables, rise, fitted, read-outs, heights, visibility, the loop and dispose.
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it, vi } from 'vitest';
import type { BuiltModel, Presentation } from '../../../src/contracts';
import { DEFAULT_PART_STYLES } from '../../../src/model/styles';
import { makeTestContext } from '../../harness/context';

const APP = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../../../..');
const model = (name: string) => JSON.parse(readFileSync(path.join(APP, 'fixtures/models', `${name}.model.json`), 'utf8')) as BuiltModel;
const presentation = (name: string) => JSON.parse(readFileSync(path.join(APP, 'fixtures/presentation', `${name}.json`), 'utf8')) as Presentation;

describe('makeTestContext (Node, fake renderer)', () => {
  it.each(['bank-v1', 'bank-v2', 'hotel', 'suite', 'house', 'mini'])('builds %s', name => {
    const m = model(name);
    const ctx = makeTestContext({ model: m });
    expect(ctx.kit.fake).toBe(true);
    expect(ctx.floors.map(f => f.key)).toEqual(m.floors.map(f => f.key));
    for (const f of ctx.floors) {
      const parts = m.parts.filter(p => p.floor === f.key);
      const slabs = parts.filter(p => p.kind === 'slab');
      const solid = parts.filter(p => p.kind !== 'slab');
      const skins = new Set((m.colliderSkins[f.key] ?? []).map(s => !!s.glass)).size;
      expect(f.walkables).toHaveLength(slabs.length);
      expect(f.rise).toHaveLength(solid.length);
      expect(f.colliders).toHaveLength(solid.filter(p => DEFAULT_PART_STYLES[p.kind].collider !== false).length + skins);
      expect(f.colliders.every(c => c.geometry.boundsTree !== undefined)).toBe(true);
      expect(ctx.built.fitted[f.key]).toHaveLength(solid.filter(p => p.fit).length);
    }
    expect(ctx.built.plinths).toHaveLength(m.parts.filter(p => p.plinth).length);
    ctx.disposer.dispose();
    expect(ctx.disposer.disposed).toBe(true);
  });

  it('reads heights and hits on the mini model (a 0.2 m wall)', () => {
    const m = model('mini');
    const ctx = makeTestContext({ model: m });
    const floor = m.floors[0]!;
    const wall = m.parts.find(p => p.floor === floor.key && p.kind === 'wall')!;
    const xs = wall.o.map(q => q[0]), ys = wall.o.map(q => q[1]);
    const cx = (Math.min(...xs) + Math.max(...xs)) / 2, cy = (Math.min(...ys) + Math.max(...ys)) / 2;
    expect(ctx.readouts.downHit(floor.key, cx, cy, 5)).toBeCloseTo(wall.z1, 5);
    const hit = ctx.readouts.rayHit(floor.key, Math.min(...xs) - 2, cy, 1.2, 1, 0, 3);
    expect(hit?.d).toBeCloseTo(2, 5);
    expect(hit?.name).toBe(`${floor.key} solid:follow`);
    expect(ctx.readouts.cast(floor.key, [Math.min(...xs) - 2, floor.level + 1.2, -cy], [1, 0, 0], 3)?.d).toBeCloseTo(2, 5);
    expect(ctx.readouts.upHit(floor.key, cx + 5, cy, 1)).toBeNull();
    ctx.disposer.dispose();
  });

  it('applies Build settings: group position, Walk level, wall scale', () => {
    const m = model('bank-v2');
    const ctx = makeTestContext({ model: m, presentation: presentation('bank-sampeng-v2') });
    const seen = vi.fn();
    ctx.bus.on('settings', seen);
    const upper = ctx.floors[1]!;
    ctx.heights.apply({ [upper.key]: { level: upper.modelLevel + 1, height: upper.wallHeight * 2 } });
    expect(upper.group.position.y).toBeCloseTo(1, 9);
    expect(upper.level).toBeCloseTo(upper.modelLevel + 1, 9);
    const scaled = upper.rise.find(r => r.scales)!;
    expect(scaled.mesh.scale.y).toBeCloseTo(2, 9);
    expect(scaled.mesh.position.y).toBeCloseTo(upper.modelLevel * (1 - 2), 9);
    expect(seen).toHaveBeenCalledTimes(1);
    ctx.disposer.dispose();
  });

  it('switches floors and ticks', () => {
    const ctx = makeTestContext({ model: model('bank-v2') });
    const [lower, upper] = ctx.floors;
    ctx.visibility.setFloorMode(lower!.key);
    expect([lower!.group.visible, upper!.group.visible]).toEqual([true, false]);
    ctx.visibility.setFloorMode('all');
    expect(ctx.visibility.has('glass')).toBe(true);
    ctx.visibility.setToggle('glass', false);
    expect(ctx.built.toggleObjects.glass.every(o => !o.visible)).toBe(true);
    expect(ctx.visibility.has('rooms')).toBe(true);
    expect(ctx.visibility.has('picture')).toBe(false);
    ctx.disposer.dispose();
  });

  it('runs the loop phases in order and reports a failing hook', () => {
    const ctx = makeTestContext({ model: model('mini') });
    const order: string[] = [];
    for (const phase of ['overlay', 'sync', 'modes', 'replay'] as const) ctx.loop.add(phase, () => order.push(phase));
    const errors = vi.fn();
    ctx.events.on('error', errors);
    ctx.loop.add('modes', () => { throw new Error('boom'); });
    ctx.loop.frame(0);
    expect(order).toEqual(['replay', 'modes', 'sync', 'overlay']);
    expect(errors).toHaveBeenCalledWith({ message: 'boom' });
    ctx.disposer.dispose();
  });

  it('builds the house with its presentation: ground plane, stairs panels, plinths', () => {
    const ctx = makeTestContext({ model: model('house'), presentation: presentation('sukhumvit-house') });
    expect(ctx.built.groundPlane?.name).toBe('ground plane');
    expect(ctx.presentation.creaseAngle).toBe(40);
    expect(ctx.floors[0]!.late.some(o => o.name === 'ground stair panels')).toBe(true);
    expect(ctx.built.plinths.length).toBeGreaterThan(0);
    ctx.disposer.dispose();
  });
});
