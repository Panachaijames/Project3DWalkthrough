// The foot-based walker in Node (rooms ACCEPTANCE RA-10's Node part, 2.3 R4; DESIGN R-9.2, R-9.3): on the reference
// building and the synthetic straight, L and U stairs, through the real parser and buildScene.
import { readFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { Raycaster, Vector3, type Mesh } from 'three';
import { describe, expect, it } from 'vitest';
import type { BuiltModel, Part, Vec2 } from '../../../src/contracts';
import { parseBuiltModel } from '../../../src/model/parse';
import { BODY_SPAN, FLOOR_HYSTERESIS, STEP_DOWN, STEP_UP, createState } from '../../../src/modes/state';
import { createWalker } from '../../../src/modes/walk';
import { climbRig, parsed, referenceRig, type ClimbRig } from './climb-kit';
import { fixtureModel } from './synthetic';

const MODELS = ['rooms-reference', 'stairs-straight', 'stairs-L', 'stairs-U'] as const;
const DOWN = new Vector3(0, -1, 0);

/** What must always hold (R-9.2), checked after every 5 cm move; returns the checker and what it saw. */
function watcher(rig: ClimbRig) {
  const s = rig.s, ray = new Raycaster();
  const surfaces = rig.floors.flatMap(f => f.surfaces), colliders = () => rig.floors.flatMap(f => f.colliders.filter(m => m.visible));
  let foot = s.foot, x = s.pos.x, z = s.pos.z;
  const seen = { moves: 0, maxRise: 0, maxDrop: 0, floors: new Set<string>([s.floor.key]), top: s.foot, bad: [] as string[] };
  const at = () => `(${s.pos.x.toFixed(2)}, ${(-s.pos.z).toFixed(2)}) foot ${s.foot.toFixed(3)}`;
  const check = () => {
    seen.moves++;
    seen.maxRise = Math.max(seen.maxRise, s.foot - foot); seen.maxDrop = Math.max(seen.maxDrop, foot - s.foot);
    seen.floors.add(s.floor.key); seen.top = Math.max(seen.top, s.foot);
    if (s.foot - foot > STEP_UP + 1e-3) seen.bad.push(`rose ${(s.foot - foot).toFixed(3)} at ${at()}`);
    if (foot - s.foot > STEP_DOWN + 1e-3) seen.bad.push(`dropped ${(foot - s.foot).toFixed(3)} at ${at()}`);
    // never inside a step: no tread, landing or slab top between foot + 0.25 and foot + 1.9 over the centre
    ray.set(new Vector3(s.pos.x, s.foot + 1.9, s.pos.z), DOWN); ray.near = 0; ray.far = 1.9 - STEP_UP - 1e-3;
    const over = ray.intersectObjects(surfaces, false)[0];
    if (over) seen.bad.push(`inside a step: a top at ${over.point.y.toFixed(3)} over ${at()}`);
    // no move crosses a collider (knee and chest height of the foot the move started from)
    const d = new Vector3(s.pos.x - x, 0, s.pos.z - z), len = d.length();
    if (len > 1e-9) {
      d.divideScalar(len);
      for (const h of [0.35, 1.2]) {
        ray.set(new Vector3(x, foot + h, z), d); ray.far = len;
        const hit = ray.intersectObjects(colliders(), false)[0];
        if (hit) seen.bad.push(`crossed ${hit.object.name} at ${at()}`);
      }
    }
    // the floor named matches the foot: the nearest level, or either one within the hysteresis band of mid-storey
    const stack = rig.floors.filter(f => f.stack === s.floor.stack).sort((a, b) => a.level - b.level);
    const nearest = stack.slice().sort((a, b) => Math.abs(a.level - s.foot) - Math.abs(b.level - s.foot))[0]!;
    if (nearest !== s.floor) {
      const i = stack.indexOf(s.floor), j = stack.indexOf(nearest);
      const mid = (s.floor.level + nearest.level) / 2;
      if (Math.abs(i - j) !== 1 || Math.abs(s.foot - mid) > FLOOR_HYSTERESIS + 1e-6) seen.bad.push(`named ${s.floor.key} at ${at()}`);
    }
    foot = s.foot; x = s.pos.x; z = s.pos.z;
  };
  return { check, seen, reset: () => { foot = s.foot; x = s.pos.x; z = s.pos.z; } };
}

/** Up the stairway's walking line and 1.0 m on, then back. */
function upAndDown(rig: ClimbRig, each?: () => void) {
  const st = rig.model.stairways![0]!, line = st.walk as Vec2[];
  rig.put(st.from, line[0]![0], line[0]![1]);
  rig.along(line.slice(1), each);
  const a = line[line.length - 2]!, b = line[line.length - 1]!;
  rig.go(b[0] - a[0], b[1] - a[1], 1.0, each);
  const top = { foot: rig.s.foot, floor: rig.s.floor.key, plan: rig.plan() };
  rig.along(line.slice(0, -1).reverse(), each);
  return { st, top, bottom: { foot: rig.s.foot, floor: rig.s.floor.key, plan: rig.plan() } };
}

/** The last flight's direction (unit, plan) and the middle of the top riser. */
function topOf(model: BuiltModel) {
  const line = model.stairways![0]!.walk as Vec2[], a = line[line.length - 2]!, b = line[line.length - 1]!;
  const l = Math.hypot(b[0] - a[0], b[1] - a[1]);
  return { riser: a, dir: [(b[0] - a[0]) / l, (b[1] - a[1]) / l] as Vec2 };
}

describe('climbing: up and down the walking line', () => {
  it.each(MODELS)('%s: the foot ends at the upper level, then back at the lower one, and the rules hold at every move', name => {
    const rig = climbRig(parsed(name)), w = watcher(rig);
    const lower = rig.floor(rig.model.stairways![0]!.from).level, upper = rig.floor(rig.model.stairways![0]!.to).level;
    const st0 = rig.model.stairways![0]!;
    rig.put(st0.from, st0.walk[0]![0], st0.walk[0]![1]); w.reset();
    const { st, top, bottom } = upAndDown(rig, w.check);
    expect(Math.abs(top.foot - upper)).toBeLessThan(0.02);
    expect(top.floor).toBe(st.to);
    // 0.5 m or more past the last riser
    const t = topOf(rig.model);
    expect((top.plan[0] - t.riser[0]) * t.dir[0] + (top.plan[1] - t.riser[1]) * t.dir[1]).toBeGreaterThan(0.5);
    expect(Math.abs(bottom.foot - lower)).toBeLessThan(0.02);
    expect(bottom.floor).toBe(st.from);
    expect(Math.hypot(bottom.plan[0] - st.walk[0]![0], bottom.plan[1] - st.walk[0]![1])).toBeLessThan(0.06);
    expect(w.seen.bad).toEqual([]);
    expect(w.seen.maxRise).toBeGreaterThan(0.15);                   // it did take risers
    expect(w.seen.maxRise).toBeLessThanOrEqual(STEP_UP + 1e-3);
    expect(w.seen.maxDrop).toBeLessThanOrEqual(STEP_DOWN + 1e-3);
    expect(w.seen.moves).toBeGreaterThan(150);
  });

  it.each(MODELS)('%s: the top edge is crossed walking at 45 and at 70 degrees to the flight, from either side', name => {
    for (const deg of [45, -45, 70, -70]) {
      const rig = climbRig(parsed(name)), w = watcher(rig), t = topOf(rig.model), st = rig.model.stairways![0]!;
      const upper = rig.floor(st.to).level;
      // from the walking line 0.7 m (two and a half treads) below the top riser, on its tread
      rig.put(st.from, st.walk[0]![0], st.walk[0]![1]);
      rig.along((st.walk as Vec2[]).slice(1, -2));
      rig.to(t.riser[0] - t.dir[0] * 0.7, t.riser[1] - t.dir[1] * 0.7);
      expect(rig.s.foot).toBeGreaterThan(upper - 0.8);
      expect(rig.s.foot).toBeLessThan(upper - 0.3);
      w.reset();
      const a = deg * Math.PI / 180, dx = t.dir[0] * Math.cos(a) - t.dir[1] * Math.sin(a), dy = t.dir[0] * Math.sin(a) + t.dir[1] * Math.cos(a);
      rig.go(dx, dy, 4.0, w.check);
      expect([deg, Math.abs(rig.s.foot - upper) < 0.02, rig.s.floor.key]).toEqual([deg, true, st.to]);
      expect(w.seen.bad).toEqual([]);
    }
  });
});

describe('climbing: the sides of a flight', () => {
  // the first flight of the straight stair: x -4.0 .. -2.8, treads from y -2.5, 0.28 m each; the reference building's: x
  // -5.4 .. -4.2 from y -2.7
  const FLIGHTS: [string, number, number, number][] = [['stairs-straight', -4.0, -2.8, -2.5], ['rooms-reference', -5.4, -4.2, -2.7]];
  it.each(FLIGHTS)('%s: entering treads 1 - 6 from the floor beside the flight stops the walker or puts it on tread 1 only', (name, x0, x1, y0) => {
    const seen: string[] = [];
    for (let j = 1; j <= 6; j++) {
      for (const offset of [0.07, 0.14, 0.21]) {
        const y = y0 + (j - 1) * 0.28 + offset;
        for (const [from, to] of [[x1 + 0.45, x0 + 0.1], [x0 - 0.33, x1 - 0.1]] as const) {
          const rig = climbRig(parsed(name)), w = watcher(rig);
          rig.put('ground', from, y); w.reset();
          if (rig.walk.ground(rig.s.pos) === null) continue;       // (no floor beside the flight on that side)
          rig.to(to, y, w.check);
          const [x] = rig.plan(), inside = x > x0 && x < x1;
          expect(w.seen.bad).toEqual([]);
          if (j === 1) {
            expect(rig.s.foot).toBeLessThan(0.19);
            if (inside) { expect(rig.s.foot).toBeCloseTo(0.188, 2); seen.push('on tread 1'); }
          } else {
            expect([j, rig.s.foot, inside]).toEqual([j, 0, false]);
            seen.push('stopped');
          }
        }
      }
    }
    expect(seen).toContain('on tread 1');
    expect(seen.filter(v => v === 'stopped').length).toBeGreaterThanOrEqual(15);
  });

  it.each(FLIGHTS)('%s: from the middle of the flight a walk to either side moves at most half its width + 0.1 m', (name, x0, x1, y0) => {
    for (let j = 2; j <= 6; j++) {
      for (const side of [-1, 1]) {
        const rig = climbRig(parsed(name)), w = watcher(rig), mid = (x0 + x1) / 2, y = y0 + (j - 0.5) * 0.28;
        const top = j * 0.1875;
        rig.putAt('ground', mid, y, top);
        expect(rig.walk.ground(rig.s.pos)).toBeCloseTo(top, 2);
        w.reset();
        const moved = rig.to(mid + side * 2.0, y, w.check);
        expect(moved).toBeLessThanOrEqual((x1 - x0) / 2 + 0.1);
        expect(rig.s.foot).toBeCloseTo(top, 2);                      // no fall, no step
        expect(w.seen.bad).toEqual([]);
      }
    }
  });

  it('beside the first tread a step down sideways is allowed (one riser, no railing)', () => {
    const rig = climbRig(parsed('stairs-straight'));
    rig.putAt('ground', -3.4, -2.36, 0.188);
    const moved = rig.to(-1.4, -2.36);
    expect(moved).toBeGreaterThan(1.5);
    expect(rig.s.foot).toBeCloseTo(0, 6);
  });

  it('walking into the stair well from above stops at its edge: never a fall', () => {
    const rig = climbRig(parsed('stairs-straight')), w = watcher(rig);
    // the well of the straight stair: x -4.05 .. -2.75, y -1.71 .. 1.70; from the east at y 0, walking west
    rig.put('upper', -1.5, 0); w.reset();
    rig.to(-3.4, 0, w.check);
    expect(rig.s.foot).toBeCloseTo(3, 6);
    expect(rig.plan()[0]).toBeGreaterThan(-2.75 - 0.081);            // the centre stays on the slab (or the bridge's 0.08 m)
    expect(w.seen.bad).toEqual([]);
  });
});

describe('climbing: the head ray and the gap bridge', () => {
  it('under a low part of the flight the head ray stops the walker; under its high end it passes', () => {
    // the straight flight seen from the east: tread 6 (y -1.10 .. -0.82) is a block 0.75 .. 1.125 m, tread 14 (y 1.14 ..
    // 1.42) 2.25 .. 2.625 m
    const low = climbRig(parsed('stairs-straight')), w = watcher(low);
    low.put('ground', -1.8, -0.96); w.reset();
    low.to(-3.4, -0.96, w.check);
    expect(low.s.foot).toBe(0);
    expect(low.plan()[0]).toBeGreaterThan(-2.8);                     // stopped at the flight's side
    expect(low.plan()[0]).toBeLessThan(-2.7);
    expect(w.seen.bad).toEqual([]);
    const high = climbRig(parsed('stairs-straight')), w2 = watcher(high);
    high.put('ground', -1.8, 1.28); w2.reset();
    high.to(-3.4, 1.28, w2.check);
    expect(high.s.foot).toBe(0);
    expect(high.plan()[0]).toBeCloseTo(-3.4, 2);                     // walked under it
    expect(w2.seen.bad).toEqual([]);
  });

  /** The straight stair with its last tread cut back (no lap), leaving `gap` m before the slab's edge at y 1.70. */
  function gapped(gap: number): BuiltModel {
    const raw = fixtureModel('stairs-straight') as BuiltModel & { parts: Part[] };
    const last = raw.parts.filter(p => p.kind === 'tread').at(-1)!;
    last.o = last.o.map(([x, y]) => [x, y > 1.7 ? 1.7 - gap : y]);
    raw.parts.filter(p => p.kind === 'slab' && p.floor === 'upper').forEach(p => { p.h = p.h.map(h => h.map(([x, y]) => [x, y > 1.6 ? 1.7 : y])); });
    return raw;
  }
  it('a 0.07 m gap at the top of a flight is crossed, square and at 45 and 70 degrees; a 0.20 m gap is an edge', () => {
    for (const deg of [0, 45, -45, 70, -70]) {
      const rig = climbRig(gapped(0.07)), w = watcher(rig), st = rig.model.stairways![0]!;
      rig.put('ground', st.walk[0]![0], st.walk[0]![1]);
      rig.to(-3.4, 1.0); w.reset();
      const a = deg * Math.PI / 180;
      rig.go(-Math.sin(a), Math.cos(a), 4.0, w.check);
      expect([deg, rig.s.foot, rig.s.floor.key]).toEqual([deg, 3, 'upper']);
      expect(w.seen.bad).toEqual([]);
    }
    const rig = climbRig(gapped(0.2)), st = rig.model.stairways![0]!;
    rig.put('ground', st.walk[0]![0], st.walk[0]![1]);
    rig.along((st.walk as Vec2[]).slice(1));
    expect(rig.s.foot).toBeCloseTo(2.812, 2);                        // on the last tread
    expect(rig.plan()[1]).toBeLessThan(1.5);
  });
});

describe('climbing: the floor named', () => {
  it('changes once each way, 0.20 m past mid-storey, and tells the modes', () => {
    const model = parsed('rooms-reference');
    const rig = referenceRig(), s = rig.s;
    let told = 0;
    // a walker with the modes' callback
    const walk = createWalker(s, { floors: rig.floors, thickness: () => 0.25, height: f => f.wallHeight, floorChanged: () => { told++; } });
    const line = model.stairways![0]!.walk as Vec2[];
    s.mode = 'walk'; s.floor = rig.floor('ground'); s.foot = 0; s.pos.set(line[0]![0], 1.6, -line[0]![1]); walk.settle();
    const changes: [string, number][] = [];
    let named = s.floor.key;
    const step = (x: number, y: number) => {
      const dx = x - s.pos.x, dz = -y - s.pos.z, n = Math.max(1, Math.round(Math.hypot(dx, dz) / 0.05));
      for (let i = 0; i < n; i++) {
        walk.walkMove(new Vector3(dx / n, 0, dz / n));
        if (s.floor.key !== named) { named = s.floor.key; changes.push([named, Math.round(s.foot * 1000) / 1000]); }
      }
    };
    for (const p of line.slice(1)) step(p[0], p[1]);
    for (const p of line.slice(0, -1).reverse()) step(p[0], p[1]);
    // mid-storey is 1.5 m: up, the first tread over 1.70 m is the 10th riser (1.875); down, the first under 1.30 m the 6th (1.125)
    expect(changes).toEqual([['upper', 1.875], ['ground', 1.125]]);
    expect(told).toBe(2);
  });

  it('nameFloor is the nearest level with the hysteresis, over three floors', () => {
    const rig = referenceRig(), s = rig.s;
    const third = { ...rig.floor('upper'), key: 'roof', level: 6 };
    const floors = [...rig.floors, third];
    const walk = createWalker(s, { floors, thickness: () => 0.25, height: () => 3 });
    s.floor = rig.floor('ground');
    const name = (foot: number) => { s.foot = foot; walk.nameFloor(); return s.floor.key; };
    expect([0, 1.5, 1.7, 1.71, 1.5, 1.3, 1.29, 4.71, 4.4, 4.29, 0.2].map(name))
      .toEqual(['ground', 'ground', 'ground', 'upper', 'upper', 'upper', 'ground', 'roof', 'roof', 'upper', 'ground']);
  });
});

describe('climbing: the body rays and findFree', () => {
  it('one floor on a floor plate, two on the stair', () => {
    const rig = referenceRig(), names = () => new Set(rig.walk.bodies().map(m => m.name.split(' ')[0]));
    rig.put('ground', -4.8, -3.7);
    expect([...names()]).toEqual(['ground']);
    rig.putAt('ground', -3.5, -0.42, 1.688);
    expect([...names()].sort()).toEqual(['ground', 'upper']);
    rig.put('upper', 0, -0.42);
    expect([...names()]).toEqual(['upper']);
    expect(BODY_SPAN).toBe(2);
  });

  it('findFree looks for room on the floor plate, never on a tread or under a low flight', () => {
    const rig = climbRig(parsed('stairs-straight')), s = rig.s;
    for (const [x, y] of [[-3.4, -2.3], [-3.4, -1.0], [-3.4, 0.5], [-3.4, 1.5]] as Vec2[]) {
      rig.put('ground', x, y);
      expect(rig.walk.findFree(s.pos)).toBe(true);
      const [px, py] = rig.plan();
      const onFlight = px > -4.0 && px < -2.8 && py > -2.5 && py < 1.75;
      // under the high end of the flight (2.06 m or more clear) the plate is free; anywhere else it is beside the flight
      if (onFlight) expect(py).toBeGreaterThan(0.86);
      s.foot = 0;
      expect(rig.walk.ground(s.pos)).toBeCloseTo(0, 6);
    }
  });

  it('a model without stairways keeps the old walker: no foot of its own, no surfaces', () => {
    const model = parsed('bank-v2'), rig = climbRig(model);
    expect(rig.floors.every(f => f.surfaces.length === 0)).toBe(true);
    const s = createState({ camera: { fov: 40 } as never, floors: rig.floors, model });
    const old = createWalker(s);
    expect(old.climbing).toBe(false);
    s.foot = 9;
    expect(s.foot).toBe(s.floor.level);
    s.floor = rig.floors[1]!;
    expect(s.foot).toBe(rig.floors[1]!.level);
    expect([old.restart(), old.displaced(), old.nameFloor(), old.surfaceUnder(s.pos, 9, s.floor)]).toEqual([false, false, false, null]);
    expect(old.base()).toBe(s.floor.level);
  });
});

describe('climbing: seeded random walks over both floors', () => {
  it.each(MODELS)('%s: the rules hold at every move of 6 x 1500 moves', name => {
    let seed = 20261111;
    const rnd = () => { seed = (seed * 1664525 + 1013904223) >>> 0; return seed / 4294967296; };
    const model = parsed(name), st = model.stairways![0]!, line = st.walk as Vec2[];
    let climbed = 0;
    for (let k = 0; k < 6; k++) {
      const rig = climbRig(model), w = watcher(rig), s = rig.s;
      // start at the stair's bottom or top, or part of the way up it, so that the walks meet the flight from every side
      if (k % 3 === 0) rig.put(st.from, line[0]![0], line[0]![1]);
      else if (k % 3 === 1) rig.put(st.to, line[line.length - 1]![0], line[line.length - 1]![1]);
      else { rig.put(st.from, line[0]![0], line[0]![1]); rig.along(line.slice(1, 3)); }
      w.reset();
      let heading = rnd() * Math.PI * 2;
      for (let i = 0; i < 1500; i++) {
        if (i % 12 === 0) {
          // mostly wander; sometimes head for a point of the walking line
          if (rnd() < 0.5) heading += (rnd() - 0.5) * 2.4;
          else { const p = line[Math.floor(rnd() * line.length)]!; heading = Math.atan2(p[1] + s.pos.z, p[0] - s.pos.x); }
        }
        rig.walk.walkMove(new Vector3(Math.cos(heading) * 0.05, 0, -Math.sin(heading) * 0.05));
        w.check();
      }
      expect(w.seen.bad).toEqual([]);
      if (w.seen.floors.size === 2) climbed++;
    }
    expect(climbed).toBeGreaterThan(0);                              // some of them changed floor by the stair
  });
});

describe('climbing: surfaces under a point', () => {
  it('surfaceUnder gives the highest surface below a height, its floor, and whether it is a step', () => {
    const rig = referenceRig(), g = rig.floor('ground');
    const at = (x: number, y: number, from: number) => { const h = rig.walk.surfaceUnder({ x, z: -y }, from, g); return h && [Math.round(h.y * 1000) / 1000, h.floor.key, h.steps]; };
    expect(at(-4.8, -1.72, 5)).toEqual([0.75, 'ground', true]);       // tread 4, through the well
    expect(at(-4.8, -0.42, 5)).toEqual([1.312, 'ground', true]);      // the landing
    expect(at(0, -0.42, 5)).toEqual([3, 'upper', false]);             // the upper slab
    expect(at(0, -0.42, 2.9)).toEqual([0, 'ground', false]);          // from under it: the ground slab
    expect(at(40, 40, 5)).toBeNull();
    const meshes: Mesh[] = rig.floors.flatMap(f => f.surfaces);
    expect(meshes.map(m => m.name)).toEqual(['ground tread:storey', 'ground floor plate', 'upper floor plate']);
  });
});

// At integration (RA-10: "and at integration on the real house and bank models"): defined only when WT_ROOMS_MODELS names
// a folder holding <name>.model.json files built with the new rules (a plain run has no skipped test).
const REAL = process.env.WT_ROOMS_MODELS;
if (REAL) {
  const names = (process.env.WT_ROOMS_NAMES ?? 'house,bank').split(',');
  const real = (name: string) => parseBuiltModel(JSON.parse(readFileSync(path.join(REAL, `${name}.model.json`), 'utf8')));
  describe('climbing: the real new-rule models', () => {
    it.each(names)('%s: every stairway is climbed up and down along its walking line, and the rules hold', name => {
      const model = real(name);
      expect(model.stairways!.length).toBeGreaterThan(0);
      const out: unknown[] = [];
      for (const st of model.stairways!) {
        const rig = climbRig(model), w = watcher(rig), line = st.walk as Vec2[], s = rig.s;
        const lower = rig.floor(st.from).level, upper = rig.floor(st.to).level;
        rig.put(st.from, line[0]![0], line[0]![1]); w.reset();
        const trace: unknown[] = [];
        const row = () => trace.push([+s.pos.x.toFixed(2), +(-s.pos.z).toFixed(2), +s.foot.toFixed(3), s.floor.key]);
        row();
        // probe.crosses' ray (chest height above the foot, against the bodies the walker can meet) along each piece of
        // the line, asked from the piece's start: recorded, not asserted (a wall cut under the far end of a flight)
        const crosses: boolean[] = [], cray = new Raycaster();
        for (const p of line.slice(1)) {
          const d = new Vector3(p[0] - s.pos.x, 0, -p[1] - s.pos.z), len = d.length();
          cray.set(new Vector3(s.pos.x, s.foot + 1.2, s.pos.z), d.divideScalar(len)); cray.far = len;
          crosses.push(cray.intersectObjects(rig.walk.bodies(), false).length > 0);
          rig.to(p[0], p[1], w.check); row();
        }
        const a = line[line.length - 2]!, b = line[line.length - 1]!;
        rig.go(b[0] - a[0], b[1] - a[1], 1.0, w.check); row();
        const top = { foot: s.foot, floor: s.floor.key };
        for (const p of line.slice(0, -1).reverse()) { rig.to(p[0], p[1], w.check); row(); }
        out.push({ name, stair: st.id, risers: st.risers, lower, upper, top, bottom: { foot: s.foot, floor: s.floor.key }, bad: w.seen.bad.slice(0, 5), crosses, trace });
        expect([st.id, Math.abs(top.foot - upper) < 0.02, top.floor]).toEqual([st.id, true, st.to]);
        expect([st.id, Math.abs(s.foot - lower) < 0.02, s.floor.key]).toEqual([st.id, true, st.from]);
        expect(w.seen.bad).toEqual([]);
      }
      if (process.env.WT_TMP) writeFileSync(path.join(process.env.WT_TMP, `real-climb-${name}.json`), JSON.stringify(out));
    });

    // R-9.9's budget, measured in Node (recorded in WT_TMP/real-timing-<name>.json, not asserted: the Edge figure is R7's)
    if (process.env.WT_R4_TIMING === '1') {
      it.each(names)('%s: the time of the first view (parse, checks, buildScene) and of a move on the stair', name => {
        const text = readFileSync(path.join(REAL, `${name}.model.json`), 'utf8');
        const first: number[] = [];
        for (let i = 0; i < 7; i++) { const t0 = performance.now(); climbRig(parseBuiltModel(JSON.parse(text))); first.push(performance.now() - t0); }
        const rig = climbRig(real(name)), st = rig.model.stairways![0]!, line = st.walk as Vec2[];
        let moves = 0;
        const count = () => { moves++; };
        rig.put(st.from, line[0]![0], line[0]![1]);
        const t0 = performance.now();
        for (let k = 0; k < 20; k++) { rig.along(line.slice(1), count); rig.along(line.slice(0, -1).reverse(), count); }
        const micros = (performance.now() - t0) / moves * 1000;
        const out = { name, firstViewMs: first.map(v => Math.round(v)).sort((a, b) => a - b), moves, microsPerMove: Math.round(micros) };
        writeFileSync(path.join(process.env.WT_TMP ?? '.', `real-timing-${name}.json`), JSON.stringify(out));
        expect(moves).toBeGreaterThan(1000);
      });
    }

    it.each(names)('%s: seeded random walks from the stair keep the rules', name => {
      const model = real(name), st = model.stairways![0]!, line = st.walk as Vec2[];
      let seed = 7;
      const rnd = () => { seed = (seed * 1664525 + 1013904223) >>> 0; return seed / 4294967296; };
      for (let k = 0; k < 6; k++) {
        const rig = climbRig(model), w = watcher(rig), s = rig.s;
        if (k % 2 === 0) rig.put(st.from, line[0]![0], line[0]![1]);
        else rig.put(st.to, line[line.length - 1]![0], line[line.length - 1]![1]);
        w.reset();
        let heading = rnd() * Math.PI * 2;
        for (let i = 0; i < 2500; i++) {
          if (i % 12 === 0) {
            if (rnd() < 0.5) heading += (rnd() - 0.5) * 2.4;
            else { const p = line[Math.floor(rnd() * line.length)]!; heading = Math.atan2(p[1] + s.pos.z, p[0] - s.pos.x); }
          }
          rig.walk.walkMove(new Vector3(Math.cos(heading) * 0.05, 0, -Math.sin(heading) * 0.05));
          w.check();
        }
        expect(w.seen.bad).toEqual([]);
      }
    });
  });
}
