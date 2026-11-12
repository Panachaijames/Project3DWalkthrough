// Jump (Space in Walk; the owner, 12 Nov): the hop of modes/walk.ts in Node, on the reference building with a chair-sized
// box on its ground floor: over and onto furniture, never through a wall, never over a floor's edge, cut short under a
// low slab; the walker of a model without stairways hops the same way.
import { BoxGeometry, Mesh, MeshBasicMaterial, Vector3 } from 'three';
import { describe, expect, it } from 'vitest';
import type { FloorRecord } from '../../../src/contracts';
import { GRAVITY, JUMP_HEIGHT, JUMP_SPEED, RUN_SPEED, WALK_SPEED } from '../../../src/modes/state';
import { createWalker, type Walker } from '../../../src/modes/walk';
import { r3, referenceRig, type ClimbRig } from './climb-kit';

const DT = 1 / 60;

/** A furniture-like collider: a box of w x d (plan) and h high standing on the floor at plan (x, y). */
function box(f: FloorRecord, x: number, y: number, w = 0.6, d = 0.6, h = 0.45): Mesh {
  const m = new Mesh(new BoxGeometry(w, h, d), new MeshBasicMaterial());
  m.name = `${f.key} test box`;
  m.position.set(x, f.level + h / 2, -y);
  f.group.add(m);
  m.updateMatrixWorld(true);
  f.colliders.push(m);
  return m;
}

/** n frames: walk along plan (dx, dy) at `speed` (when given), then the hop moves on; the highest lift seen. */
function frames(w: Walker, n: number, dir: [number, number] | null, speed = WALK_SPEED): number {
  let top = 0;
  for (let i = 0; i < n; i++) {
    if (dir) { const l = Math.hypot(dir[0], dir[1]); w.walkMove(new Vector3(dir[0] / l * speed * DT, 0, -dir[1] / l * speed * DT)); }
    w.air(DT);
    top = Math.max(top, w.lift());
  }
  return top;
}

function rigWithChair(): ClimbRig {
  const rig = referenceRig();
  box(rig.floor('ground'), -1, 3.0);                   // a chair 0.6 m deep: plan y 2.7 .. 3.3
  return rig;
}

describe('jump: the hop itself', () => {
  it('rises JUMP_HEIGHT and comes down in about 0.7 s', () => {
    expect(JUMP_SPEED).toBeCloseTo(Math.sqrt(2 * GRAVITY * JUMP_HEIGHT), 9);
    const rig = referenceRig(), w = rig.walk;
    rig.put('ground', -1, 2);
    expect([w.lift(), w.hopping()]).toEqual([0, false]);
    expect(w.jump()).toBe(true);
    expect(w.jump()).toBe(false);                        // one hop at a time
    let n = 0, top = 0;
    while (n < 200 && (n === 0 || w.hopping())) { top = Math.max(top, frames(w, 1, null)); n++; }
    expect(top).toBeGreaterThan(JUMP_HEIGHT - 0.02);
    expect(top).toBeLessThan(JUMP_HEIGHT + 0.01);
    expect(n * DT).toBeGreaterThan(0.6);
    expect(n * DT).toBeLessThan(0.8);
    expect([w.lift(), w.hopping(), r3(rig.s.foot)]).toEqual([0, false, 0]);
  });

  it('without a jump nothing changes: no lift, no hop, the same walk', () => {
    const a = referenceRig(), b = referenceRig();
    a.put('ground', -1, 2); b.put('ground', -1, 2);
    frames(a.walk, 60, [0, 1]);
    b.go(0, 1, 1.5);
    expect([a.walk.lift(), a.walk.hopping()]).toEqual([0, false]);
    expect(a.plan().map(r3)).toEqual(b.plan().map(r3));
  });
});

describe('jump: furniture', () => {
  it('walking into a chair stops the walker; a hop carries it onto the chair, and walking on it steps off the far side', () => {
    const blocked = rigWithChair();
    blocked.put('ground', -1, 2.1);
    frames(blocked.walk, 90, [0, 1]);
    expect(blocked.plan()[1]).toBeLessThan(2.45);        // stopped short of the chair's face (2.7) by about the body

    const rig = rigWithChair(), w = rig.walk;
    rig.put('ground', -1, 2.1);
    w.jump();
    frames(w, 40, [0, 1]);                               // about 1 m forward while in the air
    expect(rig.plan()[1]).toBeGreaterThan(2.7);
    expect(rig.plan()[1]).toBeLessThan(3.3);
    expect([r3(w.lift()), w.hopping(), r3(rig.s.foot)]).toEqual([0.45, false, 0]);   // standing on the chair's top
    frames(w, 60, [0, 1]);                               // walks off its far edge and drops to the floor
    expect(rig.plan()[1]).toBeGreaterThan(3.3);
    expect([w.lift(), w.hopping(), r3(rig.s.foot)]).toEqual([0, false, 0]);
  });

  it('a hop from the top of a chair is a hop again, up to the slab overhead', () => {
    const rig = rigWithChair(), w = rig.walk;
    rig.put('ground', -1, 2.1);
    w.jump(); frames(w, 40, [0, 1]);
    expect(r3(w.lift())).toBe(0.45);
    expect(w.jump()).toBe(true);
    const top = frames(w, 20, null);
    // 0.45 + 0.6 would put the head (lift + 1.90) through the upper slab's underside at 2.75: it stops just under it
    expect(top).toBeGreaterThan(0.75);
    expect(top).toBeLessThanOrEqual(2.75 - 1.9 + 1e-6);
  });

  it('the hop is the same at 20 and at 144 frames a second', () => {
    const peak = (fps: number) => {
      const rig = referenceRig(), w = rig.walk;
      rig.put('ground', -1, 2);
      w.jump();
      let top = 0;
      for (let i = 0; i < fps; i++) { w.air(1 / fps); top = Math.max(top, w.lift()); }
      return top;
    };
    expect(Math.abs(peak(20) - peak(144))).toBeLessThan(0.01);
  });
});

describe('jump: what does not change', () => {
  it('a hop never goes through a wall (the room\'s north wall, 3 m high)', () => {
    const rig = referenceRig(), w = rig.walk;
    rig.put('ground', -1, 3.6);
    w.jump();
    frames(w, 60, [0, 1], RUN_SPEED);
    expect(rig.plan()[1]).toBeLessThan(4.3 - 0.25);      // the wall's inner face is at y 4.3
    expect(rig.plan()[1]).toBeGreaterThan(3.6);
  });

  it('a hop never carries the walker over the edge of the stair well (never a fall)', () => {
    const rig = referenceRig(), w = rig.walk;
    rig.put('upper', -3.0, -1.6);                       // on the upper slab, 0.53 m south of the well's edge (y -1.07)
    w.jump();
    frames(w, 60, [0, 1], RUN_SPEED);
    frames(w, 30, null);
    expect(rig.plan()[1]).toBeLessThan(-1.07 + 0.1);
    expect([r3(rig.s.foot), rig.s.floor.key, w.lift()]).toEqual([3, 'upper', 0]);
  });

  it('a slab overhead cuts the hop short', () => {
    const rig = referenceRig(), w = rig.walk, up = rig.floor('upper').group;
    up.position.y -= 0.4; up.updateMatrixWorld(true);  // its underside 2.35 m over the ground floor
    rig.put('ground', -1, 2);
    w.jump();
    const top = frames(w, 60, null);
    expect(top).toBeLessThan(2.35 - 1.9 + 0.06);        // the head (foot + 1.90) stops under it
    expect(top).toBeGreaterThan(0.2);
    expect(w.lift()).toBe(0);
  });
});

describe('jump: a model without stairways (the walker of before)', () => {
  it('hops over the same chair and lands beyond it; walls still stop it', () => {
    const rig = rigWithChair(), s = rig.s;
    const old = createWalker(s);                        // no climb deps: the old walker on the same floors
    expect(old.climbing).toBe(false);
    s.mode = 'walk'; s.floor = rig.floor('ground'); s.pos.set(-1, 1.6, -2.1);
    old.jump();
    frames(old, 40, [0, 1]);
    frames(old, 60, [0, 1]);
    expect(-s.pos.z).toBeGreaterThan(3.3);
    expect(old.lift()).toBe(0);
    s.pos.set(-1, 1.6, -3.6); old.land();
    old.jump();
    frames(old, 60, [0, 1], RUN_SPEED);
    expect(-s.pos.z).toBeLessThan(4.3 - 0.25);
  });
});
