// @vitest-environment happy-dom
// The hotel's main stair is climbed (the owner's request of 16 Nov 2026: "I can't just hold W to climb ... it ends at
// the last two stairs and I can't proceed to the next floor"). The hotel (built from two pictures, no `stairways`) is
// loaded as createViewer loads it: parsed, then model/upgrade.ts, which makes its complete F1 flight a stairway; the
// foot-based walker then climbs it. Without the upgrade the same walks stop at the first steps (the last test).
import { Raycaster, Vector3 } from 'three';
import { describe, expect, it } from 'vitest';
import type { BuiltModel } from '../../../src/contracts';
import { upgradeModel } from '../../../src/model/upgrade';
import { FLOOR_HYSTERESIS, STEP_DOWN, STEP_UP } from '../../../src/modes/state';
import { clientOf, modesRig } from './climb-dom-kit';
import { climbRig, parsed, type ClimbRig } from './climb-kit';
import { fixturePresentation } from './synthetic';

const PRES = fixturePresentation('hotel-lobby');
const hotel = (): BuiltModel => upgradeModel(parsed('hotel'));
const DOWN = new Vector3(0, -1, 0);
/** F2's level, and the flight in plan: x -4.665 ... -2.165, the first step from y -1.528, the last to y 2.8. */
const F2 = 2.9, X0 = -4.665, X1 = -2.165, Y0 = -1.528, Y1 = 2.8;

/** What must hold after every move (the watcher of climb.test.ts, R-9.2). */
function watcher(rig: ClimbRig) {
  const s = rig.s, ray = new Raycaster();
  const surfaces = rig.floors.flatMap(f => f.surfaces), colliders = () => rig.floors.flatMap(f => f.colliders.filter(m => m.visible));
  let foot = s.foot, x = s.pos.x, z = s.pos.z;
  const seen = { moves: 0, maxRise: 0, maxDrop: 0, bad: [] as string[] };
  const at = () => `(${s.pos.x.toFixed(2)}, ${(-s.pos.z).toFixed(2)}) foot ${s.foot.toFixed(3)}`;
  const check = () => {
    seen.moves++;
    seen.maxRise = Math.max(seen.maxRise, s.foot - foot); seen.maxDrop = Math.max(seen.maxDrop, foot - s.foot);
    if (s.foot - foot > STEP_UP + 1e-3) seen.bad.push(`rose ${(s.foot - foot).toFixed(3)} at ${at()}`);
    if (foot - s.foot > STEP_DOWN + 1e-3) seen.bad.push(`dropped ${(foot - s.foot).toFixed(3)} at ${at()}`);
    // never inside a step: no tread or slab top between foot + 0.25 and foot + 1.9 over the centre
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
    const nearest = Math.abs(s.foot - F2) < Math.abs(s.foot) ? 'F2' : 'F1';
    if (nearest !== s.floor.key && Math.abs(s.foot - F2 / 2) > FLOOR_HYSTERESIS + 1e-6) seen.bad.push(`named ${s.floor.key} at ${at()}`);
    foot = s.foot; x = s.pos.x; z = s.pos.z;
  };
  return { check, seen, reset: () => { foot = s.foot; x = s.pos.x; z = s.pos.z; } };
}

describe("the hotel's main stair (F1-S1, derived when the model is loaded)", () => {
  it('up the walking line from F1 to F2 and back: the rules hold at every move, the floor is named F2 at the top and F1 at the bottom', () => {
    const rig = climbRig(hotel(), PRES), w = watcher(rig), st = rig.model.stairways![0]!;
    rig.put('F1', st.bottom[0], st.bottom[1]); w.reset();
    expect([rig.s.foot, rig.s.floor.key]).toEqual([0, 'F1']);
    rig.to(st.top[0], st.top[1], w.check);
    expect(rig.s.floor.key).toBe('F2');
    expect(Math.abs(rig.s.foot - F2)).toBeLessThan(1e-3);
    expect(rig.plan()[1]).toBeGreaterThan(Y1 + 0.5);                   // well past the last step, on F2's slab
    expect(Math.hypot(rig.plan()[0] - st.top[0], rig.plan()[1] - st.top[1])).toBeLessThan(0.06);
    const up = w.seen.moves;
    rig.to(st.bottom[0], st.bottom[1], w.check);
    expect(rig.s.floor.key).toBe('F1');
    expect(Math.abs(rig.s.foot)).toBeLessThan(1e-3);
    expect(Math.hypot(rig.plan()[0] - st.bottom[0], rig.plan()[1] - st.bottom[1])).toBeLessThan(0.06);
    expect(w.seen.bad).toEqual([]);
    expect(w.seen.maxRise).toBeGreaterThan(0.16);                      // it took the 0.171 m risers, one at a time
    expect(w.seen.maxRise).toBeLessThanOrEqual(STEP_UP);
    expect(w.seen.maxDrop).toBeGreaterThan(0.16);
    expect(w.seen.maxDrop).toBeLessThanOrEqual(STEP_DOWN);
    expect(up).toBeGreaterThan(120);
  });

  it('every one of the 17 risers is taken: the foot stands on each tread top in turn, then on F2', () => {
    const rig = climbRig(hotel(), PRES), st = rig.model.stairways![0]!, feet = new Set<number>();
    rig.put('F1', st.bottom[0], st.bottom[1]);
    rig.to(st.top[0], st.top[1], () => feet.add(Math.round(rig.s.foot * 1000) / 1000));
    const tops = rig.model.parts.filter(p => p.kind === 'tread').map(p => p.z1).sort((a, b) => a - b);
    expect(tops).toHaveLength(16);
    expect([...feet].sort((a, b) => a - b)).toEqual([0, ...tops, F2]);
  });

  it('along the flight near either side (0.45 m from its edges) it climbs too, and no railing or wall is crossed', () => {
    for (const x of [X0 + 0.45, X1 - 0.45]) {
      const rig = climbRig(hotel(), PRES), w = watcher(rig);
      rig.put('F1', x, Y0 - 0.6); w.reset();
      rig.to(x, Y1 + 0.9, w.check);
      expect([x, rig.s.floor.key, Math.abs(rig.s.foot - F2) < 1e-3, rig.plan()[1] > Y1 + 0.8]).toEqual([x, 'F2', true, true]);
      expect(w.seen.bad).toEqual([]);
    }
  });

  it('holding W from the foot of the stair, facing it, reaches Floor 2 (the keys, a made-up 60 Hz clock), and S comes back down', () => {
    const rig = modesRig(hotel(), PRES), { s, modes } = rig;
    try {
      // as the owner does: a double-click at the foot of the stair, then face it
      modes.setMode('walk', { floor: rig.floor('F1'), point: { x: -3.4, z: -(Y0 - 0.9) } });
      expect([s.mode, s.floor.key, s.foot]).toEqual(['walk', 'F1', 0]);
      expect(Math.hypot(s.pos.x - -3.4, -s.pos.z - (Y0 - 0.9))).toBeLessThan(0.01);   // free where it was clicked
      s.yaw = 0; s.pitch = 0;                                           // plan +y: up the flight
      let t = 5000;
      rig.frame(t);
      const hold = (code: string, until: () => boolean, max: number) => {
        s.keys.add(code);
        let frames = 0;
        while (!until() && frames < max) { t += 1000 / 60; rig.frame(t); frames++; }
        s.keys.delete(code);
        return frames;
      };
      const marked: string[] = [];
      const off = rig.ctx.events.on('modechange', e => { marked.push(e.floor); });
      // 1.5 m/s: 0.9 m to the first step, 4.33 m of flight, 1 m on: about 4.2 s
      const up = hold('KeyW', () => -s.pos.z > Y1 + 1.0, 600);
      expect(up).toBeLessThan(320);                                     // it never stood still: under 5.4 s
      expect(s.floor.key).toBe('F2');
      expect(Math.abs(s.foot - F2)).toBeLessThan(1e-3);
      expect(modes.probe.foot()).toBeCloseTo(F2, 3);
      expect(marked).toEqual(['F2']);                                   // the floor buttons and the HUD follow (modechange)
      for (let i = 0; i < 40; i++) { t += 1000 / 60; rig.frame(t); }    // the eye settles
      expect(s.pos.y).toBeCloseTo(F2 + s.eye, 2);
      const down = hold('KeyS', () => -s.pos.z < Y0 - 0.8, 600);
      expect(down).toBeLessThan(320);
      expect(s.floor.key).toBe('F1');
      expect(Math.abs(s.foot)).toBeLessThan(1e-3);
      expect(marked).toEqual(['F2', 'F1']);
      off();
    } finally {
      rig.dispose();
    }
  });

  it('a double-click on a tread stands on it; walking on from there reaches F2', () => {
    const rig = modesRig(hotel(), PRES), { s, modes } = rig;
    try {
      const tread = rig.model.parts.filter(p => p.kind === 'tread').sort((a, b) => a.z1 - b.z1)[5]!;   // the sixth: top 1.024
      const y = (tread.o[0]![1] + tread.o[2]![1]) / 2;
      // from straight above, through the hole in Floor 2's slab over the flight
      rig.ctx.camera.position.set(-3.4 + 0.01, tread.z1 + 15, -y + 0.01);
      rig.ctx.camera.lookAt(new Vector3(-3.4, tread.z1, -y));
      rig.canvas.dispatchEvent(new MouseEvent('dblclick', { ...clientOf(rig.ctx, new Vector3(-3.4, tread.z1, -y)), bubbles: true }));
      expect([s.mode, s.floor.key]).toEqual(['walk', 'F1']);
      expect([s.pos.x, -s.pos.z]).toEqual([expect.closeTo(-3.4, 2), expect.closeTo(y, 2)]);
      expect(s.foot).toBeCloseTo(1.024, 3);
      expect(modes.probe.walk(0, 5)).toBeGreaterThan(4.9);
      expect([s.floor.key, Math.abs(s.foot - F2) < 1e-3]).toEqual(['F2', true]);
    } finally {
      rig.dispose();
    }
  });

  it('the sides of the flight: from the floor beside it, steps 2 to 9 stop the walker (too high a step, or no headroom under them)', () => {
    // (the flight's long sides; where a wall or the stair spine stands beside it the walker stops there instead)
    let ran = 0;
    for (let j = 2; j <= 9; j++) {
      const y = Y0 + (j - 0.5) * 0.2705;
      for (const [from, to] of [[X1 + 0.6, X0 + 0.3], [X0 - 0.6, X1 - 0.3]] as const) {
        const rig = climbRig(hotel(), PRES), w = watcher(rig);
        rig.put('F1', from, y); w.reset();
        if (rig.walk.ground(rig.s.pos) === null || rig.walk.clearance(rig.s.pos, rig.s.floor) < 0.3) continue;
        rig.to(to, y, w.check);
        ran++;
        const [x] = rig.plan();
        expect(w.seen.bad).toEqual([]);
        expect([j, Math.abs(rig.s.foot) < 1e-6, x > X0 + 0.01 && x < X1 - 0.01]).toEqual([j, true, false]);
      }
    }
    expect(ran).toBe(16);                                             // both long sides are open on Floor 1
  });

  it('F2-S1 (to a floor that is not drawn) still stops the walk on Floor 2, where the saved model always stopped it', () => {
    const rig = climbRig(hotel(), PRES), w = watcher(rig);
    rig.put('F2', -3.4, 6.2); w.reset();                                // 1 m before its first step (y 7.175)
    rig.to(-3.4, 9.5, w.check);
    expect(w.seen.bad).toEqual([]);
    expect(rig.s.foot).toBeCloseTo(F2, 3);
    expect(rig.s.floor.key).toBe('F2');
    // its first two steps are lower than the knee ray (0.35 m), the third stops the body 0.3 m before it (y 7.817)
    expect(rig.plan()[1]).toBeGreaterThan(7.4);
    expect(rig.plan()[1]).toBeLessThan(7.817 - 0.25);
    // the level-based walker on the model as saved stops at the same place
    const old = modesRig(parsed('hotel'), PRES);
    try {
      old.modes.setMode('walk', { floor: old.floor('F2'), point: { x: -3.4, z: -6.2 } });
      old.s.pos.x = -3.4; old.s.pos.z = -6.2;
      old.modes.probe.walk(0, 3.3);
      expect(-old.s.pos.z).toBeCloseTo(rig.plan()[1], 6);
      expect(old.s.pos.y).toBeCloseTo(F2 + 1.6, 9);
    } finally {
      old.dispose();
    }
  });

  it('without the upgrade (the saved model as it is) the walk stops at the first steps: this is what the owner saw', () => {
    const rig = modesRig(parsed('hotel'), PRES), { s, modes } = rig;
    try {
      modes.setMode('walk', { floor: rig.floor('F1'), point: { x: -3.4, z: -(Y0 - 0.9) } });
      s.pos.x = -3.4; s.pos.z = -(Y0 - 0.9);
      modes.probe.walk(0, 6.5);
      expect(s.floor.key).toBe('F1');
      expect(s.pos.y).toBeCloseTo(1.6, 9);
      expect(-s.pos.z).toBeLessThan(Y0 + 0.6);                          // a step or two in, no further
    } finally {
      rig.dispose();
    }
  });
});
