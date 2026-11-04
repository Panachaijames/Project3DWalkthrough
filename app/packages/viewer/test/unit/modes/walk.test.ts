// Builder B: Walk collision in plain Node (DESIGN.md 17.2 modes): modes/walk.ts and the probe on makeTestContext, on a
// synthetic room (a wall, a 7 cm partition, a void in the slab, a second floor) and a closed corridor, and on the bank v2
// fixture: stops 0.2 - 0.6 m from a wall, slides at 40 degrees along it, never through the partition, never closer than
// the body's edge to its end, onFloor at a void edge, findFree from far outside, the Ghost floor rule, faceOpen.
import { Box3, Vector3 } from 'three';
import { describe, expect, it } from 'vitest';
import type { BuiltModel, FloorRecord, ModesProbe, ModesState } from '../../../src/contracts';
import { createProjection } from '../../../src/modes/camera';
import { currentFloor, floorAtHeight, pickFloor, stackOf } from '../../../src/modes/index';
import { createProbe } from '../../../src/modes/probe';
import { createState, D2R, RADIUS } from '../../../src/modes/state';
import { createWalker, type Walker } from '../../../src/modes/walk';
import { makeTestContext, type TestContext } from '../../harness/context';
import { corridor, fixtureModel, fixturePresentation, room } from './synthetic';

interface Rig { ctx: TestContext; s: ModesState; walk: Walker; probe: ModesProbe; floor(key: string): FloorRecord }
function rig(model: BuiltModel, presentation?: string): Rig {
  const ctx = makeTestContext({ model, presentation: presentation ? fixturePresentation(presentation) : undefined });
  const s = createState(ctx);
  const walk = createWalker(s);
  const probe = createProbe(ctx, s, walk, createProjection(ctx, s).applyCamera);
  s.mode = 'walk';
  return { ctx, s, walk, probe, floor: key => ctx.floorByKey.get(key)! };
}
/** Stand at plan (x, y) on a floor, eye height. */
const stand = (r: Rig, key: string, x: number, y: number) => { const f = r.floor(key); r.s.floor = f; r.s.pos.set(x, f.level + r.s.eye, -y); };
/** The probe's walking direction (degrees) for a plan direction. */
const deg = (dx: number, dy: number) => Math.atan2(-dx, dy) / D2R;
const planX = (s: ModesState) => s.pos.x, planY = (s: ModesState) => -s.pos.z;
const turn = (a: number, b: number) => Math.abs(Math.atan2(Math.sin(a - b), Math.cos(a - b)));

describe('Walk collision on a synthetic room', { timeout: 120_000 }, () => {
  it('stops 0.2 - 0.6 m from a wall and never passes through it', () => {
    const r = rig(room());
    for (const [x, y, dx, dy] of [[-3, 0, -1, 0], [3, -1, 1, 0], [-2, -2, 0, -1], [-2.5, 2, 0, 1], [-3, -1.5, -1, -0.6]] as const) {
      stand(r, 'L1', x, y);
      const a = r.s.pos.clone();
      const moved = r.probe.walk(deg(dx, dy), 6);
      expect(moved).toBeGreaterThan(0.5);
      expect(r.probe.crosses(a.x, a.z, r.s.pos.x, r.s.pos.z)).toBe(false);
      const clr = r.probe.clearance();
      expect(clr).toBeGreaterThan(0.2);
      expect(clr).toBeLessThan(0.6);
      expect(r.probe.onFloor()).toBe(true);
    }
    expect(Math.abs(planX(r.s))).toBeLessThan(5);
    r.ctx.disposer.dispose();
  });

  it('slides along a wall when walked into at 40 degrees', () => {
    const r = rig(room());
    stand(r, 'L1', -3, 0);
    r.probe.walk(deg(-1, 0), 4);                           // up to the west wall
    const p0 = r.s.pos.clone();
    for (const off of [40, -40]) {
      r.s.pos.copy(p0);
      const moved = r.probe.walk(deg(-1, 0) + off, 1);
      expect(moved).toBeGreaterThan(0.6);                  // most of the step goes along the wall
      expect(planX(r.s)).toBeGreaterThan(-5 + 0.2);
      expect(r.probe.crosses(p0.x, p0.z, r.s.pos.x, r.s.pos.z)).toBe(false);
      expect(Math.abs(planX(r.s) - planX({ pos: p0 } as ModesState))).toBeLessThan(0.05);
    }
    r.ctx.disposer.dispose();
  });

  it('never goes through a 7 cm partition, from either side and at any angle', () => {
    const r = rig(room());
    let walks = 0;
    for (const side of [-1, 1]) {
      for (const y of [-3.5, -2.5, -1.5, -0.5]) {
        for (let a = -60; a <= 60; a += 10) {
          stand(r, 'L1', 1.5 * side, y);
          const toward = deg(-side, 0) + a;
          for (let i = 0; i < 50; i++) {
            const p = r.s.pos.clone();
            r.probe.walk(toward, 0.05);
            expect(r.probe.crosses(p.x, p.z, r.s.pos.x, r.s.pos.z)).toBe(false);
          }
          if (planY(r.s) < 1 - RADIUS) expect(Math.sign(planX(r.s))).toBe(side);
          walks++;
        }
      }
    }
    expect(walks).toBe(2 * 4 * 13);
    r.ctx.disposer.dispose();
  });

  it("never comes closer than the body's edge to the partition's end", () => {
    const r = rig(room());
    let worst = Infinity;
    for (const [x, y, d] of [[0.6, 2.2, 153], [0.6, 2.2, 148], [0.6, 2.2, 158], [0.55, 2.2, 153], [0.65, 2.2, 153], [-0.6, 2.2, -153]] as const) {
      stand(r, 'L1', x, y);
      let min = r.probe.clearance();
      for (let i = 0; i < 60; i++) { r.probe.walk(d, 0.05); min = Math.min(min, r.probe.clearance()); }
      worst = Math.min(worst, min);
    }
    expect(worst).toBeGreaterThan(0.25);
    r.ctx.disposer.dispose();
  });

  it('stays on the floor at a void edge, and slides along it when walked into at an angle', () => {
    const r = rig(room());
    stand(r, 'L1', 1, 2);
    r.probe.walk(deg(1, 0), 3);                            // straight at the void (x 2 - 4)
    expect(planX(r.s)).toBeLessThanOrEqual(2 + 1e-6);
    expect(planX(r.s)).toBeGreaterThan(1.9);
    expect(r.probe.onFloor()).toBe(true);
    stand(r, 'L1', 1.8, 1.5);
    const moved = r.probe.walk(deg(1, 0.6), 1.5);           // at an angle: along the edge (the larger axis first)
    expect(moved).toBeGreaterThan(0.3);
    expect(r.probe.onFloor()).toBe(true);
    r.ctx.disposer.dispose();
  });

  it('findFree finds room from far outside the floor (the middle of the floor, then the spiral)', () => {
    const r = rig(room());
    stand(r, 'L1', 40, 30);
    expect(r.walk.findFree(r.s.pos, 1.0)).toBe(true);
    expect(r.probe.onFloor()).toBe(true);
    expect(r.probe.clearance()).toBeGreaterThanOrEqual(1.0);
    expect(Math.hypot(planX(r.s), planY(r.s))).toBeLessThan(6);
    stand(r, 'L1', 4.8, 0);                                // 0.2 m from the east wall: findFree moves you out
    expect(r.walk.findFree(r.s.pos)).toBe(true);
    expect(r.probe.clearance()).toBeGreaterThanOrEqual(0.5);
    r.ctx.disposer.dispose();
  });

  it('startPoint keeps a point over the floor and takes the middle otherwise; onFloor without walkables is true', () => {
    const r = rig(room());
    const f = r.floor('L1');
    const inside = { x: 1, z: -2 };
    expect(r.walk.startPoint(f, inside)).toBe(inside);
    const c = r.walk.startPoint(f, { x: 100, z: 0 });
    expect(c.x).toBeCloseTo(0, 9);
    expect(c.z).toBeCloseTo(0, 9);
    expect(f.box).toBeInstanceOf(Box3);
    const bare = { ...f, walkables: [] };
    expect(r.walk.onFloor({ x: 100, z: 100 }, bare)).toBe(true);
    expect(r.walk.clearance({ x: 0, z: 0 }, { ...f, colliders: [] })).toBe(Infinity);
    r.ctx.disposer.dispose();
  });
});

describe('faceOpen', { timeout: 60_000 }, () => {
  it('keeps the heading when 4 m are open', () => {
    const r = rig(corridor());
    stand(r, 'C', -1, 0);
    r.s.yaw = deg(1, 0) * D2R;                             // 4.8 m to the east end
    const yaw0 = r.s.yaw;
    r.walk.faceOpen();
    expect(r.s.yaw).toBe(yaw0);
    r.ctx.disposer.dispose();
  });

  it('turns away from a wall even when the current heading would score best (it is never a candidate)', () => {
    const r = rig(corridor());
    stand(r, 'C', 0, 0);
    r.s.yaw = deg(1, 0) * D2R;                             // 3.8 m to the east end: under 4 m
    const yaw0 = r.s.yaw, own = r.walk.openAhead(yaw0, 15);
    expect(own).toBeCloseTo(3.8, 6);
    // Every other heading of the 24 scores less than the current one would (open * (0.7 + 0.3 cos 0) = 3.8).
    const scores = [...Array(23)].map((_, i) => { const y = yaw0 + (i + 1) / 24 * Math.PI * 2; return r.walk.openAhead(y, 15) * (0.7 + 0.3 * Math.cos(y - yaw0)); });
    expect(Math.max(...scores)).toBeLessThan(own);
    r.walk.faceOpen();
    expect(turn(r.s.yaw, yaw0)).toBeCloseTo(15 * D2R, 6);
    expect(Math.abs(r.s.yaw)).toBeLessThanOrEqual(Math.PI);
    r.ctx.disposer.dispose();
  });

  it('turns to the most open view: in the room, facing the wall 1 m away, it turns away from it', () => {
    const r = rig(room());
    stand(r, 'L1', -4, -1);
    r.s.yaw = deg(-1, 0) * D2R;                            // 1 m to the west wall
    r.walk.faceOpen();
    expect(r.walk.openAhead(r.s.yaw, 15)).toBeGreaterThan(4);
    r.ctx.disposer.dispose();
  });
});

describe('floors: the Ghost floor rule, stacks, picking', { timeout: 60_000 }, () => {
  it('in Ghost you are on a floor once your eye is 0.3 m above it (floorAtHeight tolerance 0.1 m)', () => {
    const r = rig(room());
    const [L1, L2] = r.ctx.floors as [FloorRecord, FloorRecord];
    r.s.mode = 'ghost';
    r.s.floor = L1;
    r.s.pos.y = 3.5 + 0.21;
    expect(currentFloor(r.ctx.floors, r.s)).toBe(L2);
    r.s.pos.y = 3.5 + 0.19;
    expect(currentFloor(r.ctx.floors, r.s)).toBe(L1);
    r.s.pos.y = -20;
    expect(currentFloor(r.ctx.floors, r.s)).toBe(L1);       // under every floor: the lowest
    r.s.mode = 'walk';
    r.s.pos.y = 50;
    expect(currentFloor(r.ctx.floors, r.s)).toBe(L1);       // Walk: the floor you walk on
    r.ctx.disposer.dispose();
  });

  it('among the floors that are showing: above a hidden floor you are on the one showing', () => {
    const r = rig(room());
    const [L1, L2] = r.ctx.floors as [FloorRecord, FloorRecord];
    L2.group.visible = false;
    expect(floorAtHeight(r.ctx.floors, L1, 3.5 + 1.0)).toBe(L1);
    expect(floorAtHeight(r.ctx.floors, L2, 3.5 + 1.0)).toBe(L1);
    L1.group.visible = false; L2.group.visible = true;
    expect(floorAtHeight(r.ctx.floors, L1, 0.5)).toBe(L2);   // nothing low showing: the lowest shown
    L1.group.visible = false; L2.group.visible = false;
    expect(floorAtHeight(r.ctx.floors, L1, 4)).toBe(L2);     // nothing showing: all floors count
    r.ctx.disposer.dispose();
  });

  it('pickFloor: the lowest floor showing; stackOf: the floors of a stack, bottom up', () => {
    const r = rig(room());
    const [L1, L2] = r.ctx.floors as [FloorRecord, FloorRecord];
    expect(pickFloor(r.ctx.floors)).toBe(L1);
    L1.group.visible = false;
    expect(pickFloor(r.ctx.floors)).toBe(L2);
    L2.group.visible = false;
    expect(pickFloor(r.ctx.floors)).toBe(L1);
    expect(stackOf(r.ctx.floors, L2)).toEqual([L1, L2]);
    L2.stack = 'other';
    expect(stackOf(r.ctx.floors, L2)).toEqual([L2]);
    r.ctx.disposer.dispose();
  });
});

describe('Walk collision on the bank v2 fixture', { timeout: 300_000 }, () => {
  const rnd = (seed: number) => () => (seed = (seed * 16807) % 2147483647) / 2147483647;
  const nearest = (probe: ModesProbe) => { const d = [...Array(72)].map((_, i) => probe.open(i * 5)); let k = 0; d.forEach((x, j) => { if (x < d[k]!) k = j; }); return { k, d: d[k]! }; };

  it('walls stop you at 40 random spots per floor: never through, never inside', () => {
    const r = rig(fixtureModel('bank-v2'), 'bank-sampeng-v2');
    for (const f of r.ctx.floors) {
      r.s.floor = f;
      const box = new Box3().setFromObject(f.group), next = rnd(7);
      let n = 0, through = 0, inside = 0, tries = 0;
      while (n < 40 && tries++ < 8000) {
        r.s.pos.set(box.min.x + next() * (box.max.x - box.min.x), f.level + r.s.eye, box.min.z + next() * (box.max.z - box.min.z));
        if (!r.probe.onFloor() || r.probe.clearance() < 0.6) continue;
        const w = nearest(r.probe);
        if (w.d > 2.5) continue;
        const a = r.s.pos.clone();
        r.probe.walk(w.k * 5, w.d + 1);
        n++;
        if (r.probe.crosses(a.x, a.z, r.s.pos.x, r.s.pos.z)) through++;
        if (r.probe.clearance() < 0.15) inside++;
      }
      expect({ floor: f.key, n, through, inside }).toEqual({ floor: f.key, n: 40, through: 0, inside: 0 });
    }
    r.ctx.disposer.dispose();
  });

  it('sliding works at random spots along walls (40 tries, at least 90 %)', () => {
    const r = rig(fixtureModel('bank-v2'), 'bank-sampeng-v2');
    const f = r.floor('L1');
    r.s.floor = f;
    const box = new Box3().setFromObject(f.group), next = rnd(11);
    let n = 0, ok = 0, tries = 0;
    while (n < 40 && tries++ < 3000) {
      r.s.pos.set(box.min.x + next() * (box.max.x - box.min.x), f.level + r.s.eye, box.min.z + next() * (box.max.z - box.min.z));
      if (!r.probe.onFloor() || r.probe.clearance() < 0.6) continue;
      const w = nearest(r.probe);
      if (w.d > 2.5) continue;
      r.probe.walk(w.k * 5, w.d + 1);
      const p = r.s.pos.clone();
      const a = r.probe.walk(w.k * 5 + 40, 1);
      r.s.pos.copy(p);
      const b = r.probe.walk(w.k * 5 - 40, 1);
      n++; if (Math.max(a, b) > 0.3) ok++;
    }
    expect(n).toBeGreaterThanOrEqual(30);
    expect(ok).toBeGreaterThanOrEqual(n * 0.9);
    r.ctx.disposer.dispose();
  });

  it('a Build settings level is the level Walk uses (the group moves with it)', () => {
    const r = rig(fixtureModel('bank-v2'), 'bank-sampeng-v2');
    const L2 = r.floor('L2');
    r.ctx.heights.apply({ L2: { level: 5, height: 3.7 } });
    r.ctx.scene.updateMatrixWorld(true);
    expect(L2.level).toBe(5);
    r.s.floor = L2;
    r.s.pos.set(0, 0, 0);
    expect(r.walk.findFree(r.s.pos, 1.0)).toBe(true);
    r.s.pos.y = L2.level + r.s.eye;
    expect(r.probe.onFloor()).toBe(true);
    expect(r.walk.onFloor(new Vector3(r.s.pos.x, 0, r.s.pos.z), { ...L2, level: 3.7 })).toBe(false);   // the old level has no floor now
    r.ctx.disposer.dispose();
  });
});
