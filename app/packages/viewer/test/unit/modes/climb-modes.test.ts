// @vitest-environment happy-dom
// Climbing through the real modes (rooms ACCEPTANCE RA-10's Node part, 2.3 R4; DESIGN R-9.2 - R-9.8): installModes on the
// reference building with the real core (climb-dom-kit.ts): the eye easing with a made-up clock, the probe's foot,
// ground and horizontal walk, the rule that a probe call starts from where the test put the walker, the floor named
// (the HUD, bus `mode`, the public `modechange`), teleports, Ghost -> Walk on a tread, a double-click on the landing,
// Build settings (a raised upper level keeps the stair climbable), and the Ceilings tick.
import { Vector3 } from 'three';
import { afterEach, describe, expect, it } from 'vitest';
import type { Vec2 } from '../../../src/contracts';
import { EYE } from '../../../src/modes/state';
import { createPanel } from '../../../src/ui/panel';
import { clientOf, modesRig, type ModesRig } from './climb-dom-kit';
import { parsed } from './climb-kit';
import { fixturePresentation } from './synthetic';

const rigs: ModesRig[] = [];
function mount(name = 'rooms-reference'): ModesRig {
  const rig = modesRig(parsed(name), name === 'rooms-reference' ? fixturePresentation('rooms-reference') : undefined);
  rigs.push(rig);
  return rig;
}
afterEach(() => { for (const r of rigs.splice(0)) r.dispose(); });

const LINE = (rig: ModesRig) => rig.model.stairways![0]!.walk as Vec2[];
/** Up the walking line by probe.walk, and 1.0 m on. */
function climb(rig: ModesRig) {
  const line = LINE(rig);
  rig.put('ground', line[0]![0], line[0]![1]);
  for (const p of line.slice(1)) rig.to(p[0], p[1]);
  const a = line[line.length - 2]!, b = line[line.length - 1]!;
  rig.to(b[0] + (b[0] - a[0]), b[1] + (b[1] - a[1]));
}
const ceilingsShown = (rig: ModesRig) => rig.ctx.floors.map(f => f.group.children.find(o => o.userData.ceiling)!.visible);

describe('the probe on a model that climbs (R-9.8)', () => {
  it('walks up the stair and down again: foot, ground, the floor named, the horizontal distance; never eased', () => {
    const rig = mount(), { s, modes } = rig, probe = modes.probe, line = LINE(rig);
    const named: string[] = [], changes: string[] = [];
    rig.ctx.bus.on('mode', m => { if (named[named.length - 1] !== `${m.mode}:${m.floor}`) named.push(`${m.mode}:${m.floor}`); });
    rig.ctx.events.on('modechange', m => changes.push(`${m.mode}:${m.floor}`));
    rig.put('ground', line[0]![0], line[0]![1]);
    expect([probe.foot(), probe.ground(), probe.onFloor(), s.floor.key]).toEqual([0, 0, true, 'ground']);
    // the first flight: 1.0 m to riser 1 and 1.54 m up its treads (1.125 m higher); the distance returned is horizontal
    const d1 = rig.to(line[1]![0], line[1]![1]), d2 = rig.to(-4.8, -1.16);   // onto tread 6
    expect(d1).toBeCloseTo(1.0, 6);
    expect(d2).toBeGreaterThan(1.539);                               // (probe.walk goes in whole 5 cm moves)
    expect(d2).toBeLessThan(1.551);
    expect(probe.foot()).toBeCloseTo(1.125, 3);
    expect(probe.ground()).toBeCloseTo(1.125, 3);
    expect(s.pos.y).toBe(s.foot + s.eye);                             // not eased
    expect(rig.ctx.camera.position.y).toBe(s.foot + s.eye);
    // crosses is measured from the foot, at chest height where the walker stands: asked at the start of each piece of
    // the line it is never true (asked from the ground floor, the piece over the cut cupboard wall is)
    for (const p of line.slice(2)) {
      expect(probe.crosses(s.pos.x, s.pos.z, p[0], -p[1])).toBe(false);
      rig.to(p[0], p[1]);
    }
    expect(rig.to(0.04, -0.42)).toBeCloseTo(1.0, 6);
    expect([probe.foot(), s.floor.key, probe.onFloor()]).toEqual([3, 'upper', true]);
    expect(probe.visible()).toEqual(['ground', 'upper']);
    for (const p of line.slice(0, -1).reverse()) rig.to(p[0], p[1]);
    expect(Math.abs(probe.foot())).toBeLessThan(1e-9);
    expect(s.floor.key).toBe('ground');
    expect(named).toEqual(['walk:ground', 'walk:upper', 'walk:ground']);
    expect(changes).toEqual(['walk:ground', 'walk:upper', 'walk:ground']);
    expect(rig.root.querySelector('[data-wt=hud]')?.textContent ?? rig.root.textContent).toContain('Ground floor');
    expect(probe.crosses(line[4]![0], -line[4]![1], line[5]![0], -line[5]![1])).toBe(true);
  });

  it('a probe call starts from where the test put the walker: the stale foot of a climb is dropped', () => {
    const rig = mount(), { s, modes } = rig, probe = modes.probe, line = LINE(rig);
    rig.put('ground', line[0]![0], line[0]![1]);
    rig.to(line[1]![0], line[1]![1]); rig.to(-4.8, -2.0);              // ends two treads up
    expect(s.foot).toBeGreaterThan(0.3);
    // the e2e helpers place the walker by writing s.pos.x and s.pos.z (tests/e2e/lib/walks.ts)
    s.pos.x = 0; s.pos.z = 3;                                           // a spot of the ground floor (plan 0, -3)
    expect(probe.onFloor()).toBe(true);
    expect([s.foot, s.pos.y]).toEqual([0, EYE]);
    s.pos.x = -4.8; s.pos.z = 2.0;                                      // over tread 3 from the floor's level: no ground in the window
    expect(probe.onFloor()).toBe(false);
    expect(probe.ground()).toBeNull();
    s.pos.x = 0; s.pos.z = 3;
    const made = probe.walk(90, 1.0);                                   // from the floor's level
    expect(made).toBeGreaterThan(0.2);
    expect(s.foot).toBe(0);
    // the same for each read-out, each after a climb
    for (const read of [() => probe.clearance(), () => probe.open(0), () => probe.crosses(0, 3, 0.5, 3), () => probe.foot(), () => probe.ground()]) {
      rig.put('ground', line[0]![0], line[0]![1]);
      rig.to(line[1]![0], line[1]![1]); rig.to(-4.8, -2.0);
      expect(s.foot).toBeGreaterThan(0.3);
      s.pos.x = 0; s.pos.z = 3;
      read();
      expect(s.foot).toBe(0);
    }
    // a read-out that does not follow a write keeps the foot
    rig.put('ground', line[0]![0], line[0]![1]);
    rig.to(line[1]![0], line[1]![1]); rig.to(-4.8, -2.0);
    const foot = s.foot;
    expect([probe.onFloor(), probe.foot(), probe.ground()]).toEqual([true, foot, foot]);
    expect(probe.clearance()).toBeGreaterThan(0);
    expect(s.foot).toBe(foot);
    // writing the floor too (upstairs after a climb that ended on the ground floor's treads)
    s.floor = rig.floor('upper'); s.pos.x = 0; s.pos.z = -3;
    expect([probe.onFloor(), s.foot]).toEqual([true, 3]);
  });

  it('a frame after a write starts from the floor too (the browser keeps ticking between a write and a probe call)', () => {
    const rig = mount(), { s } = rig, line = LINE(rig);
    rig.put('ground', line[0]![0], line[0]![1]);
    rig.to(line[1]![0], line[1]![1]); rig.to(-4.8, -2.0);
    s.pos.x = 0; s.pos.z = 3;
    rig.frame(1000); rig.frame(1016);
    expect([s.foot, s.pos.y]).toEqual([0, EYE]);
  });
});

describe('the eye easing (R-9.4), with a made-up clock', () => {
  it('eases toward foot + eye while W climbs, settles within 0.5 s, and is skipped on a teleport', () => {
    const rig = mount(), { s, modes } = rig, line = LINE(rig);
    rig.put('ground', line[1]![0], line[1]![1] - 0.3);
    modes.probe.onFloor();
    s.yaw = 0; s.pitch = 0;                                           // facing plan +y: up the first flight
    let t = 5000;
    rig.frame(t);
    s.keys.add('KeyW');
    let maxStep = 0, maxLag = 0, frames = 0, lastY = s.pos.y, lastFoot = s.foot, maxFootJump = 0;
    while (s.foot < 0.56 && frames < 400) {
      t += 1000 / 60; rig.frame(t); frames++;
      maxStep = Math.max(maxStep, Math.abs(s.pos.y - lastY)); lastY = s.pos.y;
      maxFootJump = Math.max(maxFootJump, s.foot - lastFoot); lastFoot = s.foot;
      maxLag = Math.max(maxLag, s.foot + s.eye - s.pos.y);
    }
    s.keys.delete('KeyW');
    expect(s.foot).toBeCloseTo(0.562, 2);                             // three risers up
    expect(maxFootJump).toBeCloseTo(0.188, 2);                        // the physics steps by a riser
    expect(maxStep).toBeLessThan(0.04);                               // the eye never jumps (at most about 3.2 cm a frame)
    expect(maxLag).toBeGreaterThan(0.05);                             // it did lag behind the foot
    expect(rig.ctx.camera.position.y).toBe(s.pos.y);
    for (let i = 0; i < 30; i++) { t += 1000 / 60; rig.frame(t); }    // 0.5 s
    expect(Math.abs(s.pos.y - (s.foot + s.eye))).toBeLessThan(0.002);
    for (let i = 0; i < 30; i++) { t += 1000 / 60; rig.frame(t); }
    expect(s.pos.y).toBe(s.foot + s.eye);
    // teleports: the floor buttons / PgUp / PgDn, and the eye slider
    modes.goToFloor('upper');
    expect([s.foot, s.pos.y, s.floor.key]).toEqual([3, 3 + s.eye, 'upper']);
    modes.changeFloor(-1);
    expect([s.foot, s.pos.y, s.floor.key]).toEqual([0, s.eye, 'ground']);
    const eye = rig.root.querySelector<HTMLInputElement>('[data-wt=eye]')!;
    eye.value = '1.2';
    eye.dispatchEvent(new Event('input', { bubbles: true }));
    expect([s.eye, s.pos.y]).toEqual([1.2, 1.2]);
  });

  it('the eye height moves the head ray: 2.2 m does not fit under what 1.6 m walks under', () => {
    // the straight flight seen from the east: tread 12 (y 0.58 .. 0.86) is a block from 1.875 m
    const tall = mount('stairs-straight'), short = mount('stairs-straight');
    for (const [rig, eye] of [[short, 1.4], [tall, 2.2]] as const) {
      rig.put('ground', -1.8, 0.72);
      rig.s.eye = eye;
      rig.to(-3.4, 0.72);
    }
    expect(short.s.pos.x).toBeLessThan(-3.3);                          // 1.4 + 0.3 = 1.70 m under 1.875 m: passes
    expect(tall.s.pos.x).toBeGreaterThan(-2.8);                        // 2.2 + 0.3 = 2.50 m: stopped at the flight's side
    expect([short.s.foot, tall.s.foot]).toEqual([0, 0]);
  });
});

describe('landing on steps (R-9.5)', () => {
  it('Ghost -> Walk lands on the highest surface under the eye - 0.30 m: a tread, the landing, a plate', () => {
    const rig = mount(), { s, modes } = rig;
    const land = (x: number, y: number, eyeY: number) => {
      modes.setMode('ghost');
      s.pos.set(x, eyeY, -y);
      modes.setMode('walk');
      return [Math.round(s.foot * 1000) / 1000, s.floor.key, Math.round(s.pos.x * 1000) / 1000, Math.round(-s.pos.z * 1000) / 1000, s.pos.y === s.foot + s.eye];
    };
    expect(land(-4.8, -1.72, 2.5)).toEqual([0.75, 'ground', -4.8, -1.72, true]);          // tread 4
    expect(land(-4.8, -0.42, 2.5)).toEqual([1.312, 'ground', -4.8, -0.42, true]);         // the landing
    expect(land(-2.38, -0.42, 4.5)).toEqual([2.625, 'upper', -2.38, -0.42, true]);        // tread 14, through the well: named upper
    expect(land(-4.8, -1.72, 0.9)).toEqual([0, 'ground', expect.any(Number), expect.any(Number), true]);   // under the tread's top: the plate (findFree moves off the flight)
    const up = land(0, 3, 4.6);                                                            // over the upper slab
    expect(up.slice(0, 2)).toEqual([3, 'upper']);
    const down = land(0, 3, 2.9);                                                          // under it: the ground floor
    expect(down.slice(0, 2)).toEqual([0, 'ground']);
    expect(modes.probe.onFloor()).toBe(true);
  });

  it('a double-click on the landing puts the foot on it; on a plate it is today\'s Walk-there', () => {
    const rig = mount(), { s, modes, ctx } = rig;
    ctx.visibility.setFloorMode('ground');                             // (the upper floor is not in the way)
    const aim = (x: number, y: number, h: number) => {
      modes.setMode('orbit');
      ctx.camera.position.set(x + 0.01, h + 15, -y + 0.01);
      ctx.camera.lookAt(new Vector3(x, h, -y));
      const at = clientOf(ctx, new Vector3(x, h, -y));
      rig.canvas.dispatchEvent(new MouseEvent('dblclick', { ...at, bubbles: true }));
    };
    aim(-4.8, -0.42, 1.312);
    expect(s.mode).toBe('walk');
    expect(s.foot).toBeCloseTo(1.312, 3);
    expect([s.pos.x, -s.pos.z]).toEqual([expect.closeTo(-4.8, 2), expect.closeTo(-0.42, 2)]);
    expect([s.floor.key, s.pos.y === s.foot + s.eye, modes.probe.onFloor()]).toEqual(['ground', true, true]);
    aim(-4.8, -1.72, 0.75);                                            // tread 4
    expect(s.foot).toBeCloseTo(0.75, 3);
    aim(0, 3, 0);                                                      // the ground plate
    expect([s.mode, s.foot, s.floor.key]).toEqual(['walk', 0, 'ground']);
  });
});

describe('Build settings while the model climbs (R-9.6)', () => {
  it('a raised upper level keeps the stair climbable, and the walker on a tread follows it', () => {
    const rig = mount(), { s, ctx } = rig;
    ctx.heights.apply({ upper: { level: 3.6, height: 3 } });           // risers of 0.225 m
    rig.refresh();
    climb(rig);
    expect(s.foot).toBeCloseTo(3.6, 2);
    expect(s.floor.key).toBe('upper');
    // back down to tread 4 of the first flight, then the level is put back: the foot stays on the tread
    const line = LINE(rig);
    for (const p of line.slice(2, -1).reverse()) rig.to(p[0], p[1]);
    rig.to(-4.8, -1.72);
    expect(s.foot).toBeCloseTo(0.9, 2);                                // 0.75 x 1.2
    ctx.heights.apply({ upper: { level: 3, height: 3 } });
    expect(s.foot).toBeCloseTo(0.75, 2);
    expect(s.pos.y).toBe(s.foot + s.eye);
    rig.refresh();
    ctx.heights.apply({ ground: { level: 0.4, height: 3 }, upper: { level: 3.4, height: 3 } });   // both floors 0.4 m up
    expect(s.foot).toBeCloseTo(1.15, 2);
    rig.refresh();
    expect(rig.modes.probe.ground()).toBeCloseTo(1.15, 2);
    // too steep to climb: a storey of 4.2 m makes risers of 0.2625 m, over the 0.25 m step
    ctx.heights.apply({ ground: { level: 0, height: 3 }, upper: { level: 4.2, height: 3 } });
    rig.refresh();
    climb(rig);
    expect(s.foot).toBe(0);
  });

  it('on the upper floor the walker follows its level', () => {
    const rig = mount(), { s, ctx } = rig;
    rig.put('upper', 0, 3);
    rig.modes.probe.onFloor();
    ctx.heights.apply({ upper: { level: 3.5, height: 3 } });
    expect([s.foot, s.pos.y, s.floor.key]).toEqual([3.5, 3.5 + s.eye, 'upper']);
  });
});

describe('the Ceilings tick and the modes (R-9.7)', () => {
  it('ceilings show in Walk and Ghost, never in Orbit; the panel has the tick', () => {
    const rig = mount(), { modes, ctx } = rig;
    const panel = createPanel(ctx);
    const tick = panel.el.querySelector<HTMLInputElement>('input[data-wt=toggle][data-toggle=ceilings]')!;
    expect([tick.checked, tick.closest('label')!.textContent]).toEqual([true, ' Ceilings']);
    expect(ceilingsShown(rig)).toEqual([false, false]);
    modes.setMode('walk');
    expect(ceilingsShown(rig)).toEqual([true, true]);
    modes.setMode('ghost');
    expect(ceilingsShown(rig)).toEqual([true, true]);
    tick.checked = false;
    tick.dispatchEvent(new Event('change', { bubbles: true }));
    expect(ceilingsShown(rig)).toEqual([false, false]);
    modes.setMode('walk');
    expect(ceilingsShown(rig)).toEqual([false, false]);
    ctx.visibility.setToggle('ceilings', true);
    expect([tick.checked, ...ceilingsShown(rig)]).toEqual([true, true, true]);
    modes.setMode('orbit');
    expect(ceilingsShown(rig)).toEqual([false, false]);
  });

  it('a model without ceilings has no tick', () => {
    const rig = modesRig(parsed('bank-v2'), fixturePresentation('bank-sampeng-v2'));
    rigs.push(rig);
    const panel = createPanel(rig.ctx);
    expect(panel.el.querySelector('input[data-toggle=ceilings]')).toBeNull();
    expect(panel.el.querySelector('input[data-toggle=plates]')).not.toBeNull();
  });
});
