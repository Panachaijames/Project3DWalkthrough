// model/upgrade.ts (the owner's request of 16 Nov 2026; rooms/DESIGN.md "Amended after the independent review", R-9): a
// model without `stairways` whose `step` parts form an unambiguously complete flight gets, in memory, a derived stairway
// and treads; every other model comes back as the very object it was. On the fixtures: the hotel's F1-S1 qualifies; its
// F2-S1 and the bank's two L2 flights lead to no floor; the house, the suite and mini have no steps. Each condition of
// the rule is refused on a doctored copy of the hotel's flight.
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import Ajv2020 from 'ajv/dist/2020.js';
import { describe, expect, it } from 'vitest';
import type { BuiltModel, Part, Presentation } from '../../../src/contracts';
import { buildScene } from '../../../src/core/build';
import { parseBuiltModel } from '../../../src/model/parse';
import { parsePresentation, resolvePresentation } from '../../../src/model/presentation';
import { upgradeModel, upgradePresentation, upgradeSteps } from '../../../src/model/upgrade';
import { isClimbing } from '../../../src/modes/state';

const APP = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../../../..');
const json = (rel: string): unknown => JSON.parse(readFileSync(path.join(APP, rel), 'utf8'));
const fixture = (name: string) => parseBuiltModel(json(`fixtures/models/${name}.model.json`));
const hotel = () => fixture('hotel');
const ajv = new Ajv2020({ strict: true, allErrors: true }).compile(json('docs/built-model.schema.json') as object);

/** The hotel's main flight (16 steps on F1, tops 0.171 ... 2.729, going +y from -1.528 to 2.8, x -4.665 ... -2.165). */
const flight = (m: BuiltModel): Part[] => m.parts.filter(p => p.kind === 'step' && p.floor === 'F1').sort((a, b) => a.z1 - b.z1);
/** A doctored hotel: `change` edits the freshly parsed model before the upgrade sees it. */
function doctored(change: (m: BuiltModel, steps: Part[]) => void) {
  const m = hotel();
  change(m, flight(m));
  parseBuiltModel(m);                                                // still a valid model
  return { m, r: upgradeSteps(m) };
}
const refusedF1 = (r: ReturnType<typeof upgradeSteps>) => r.refused.find(x => x.floor === 'F1')?.why;

describe('upgradeModel: the hotel (built from two pictures on 2 Nov, no `stairways`)', () => {
  it('gets exactly one derived stairway, F1 to F2, 17 risers of about 0.1706 m', () => {
    const before = hotel(), r = upgradeSteps(before), m = r.model;
    expect(before.stairways).toBeUndefined();
    expect(m.stairways).toHaveLength(1);
    const st = m.stairways![0]!;
    expect(st).toMatchObject({ id: 'F1-S1', from: 'F1', to: 'F2', kind: 'straight', risers: 17, treads: 16, landings: 0, direction: 'floors', derived: 'steps' });
    expect(st.riser).toBeCloseTo(2.9 / 17, 9);
    expect(st.riser).toBeCloseTo(0.1706, 4);
    expect(st.going).toBeCloseTo(0.2705, 2);
    expect(st.width).toBeCloseTo(2.5, 3);
    // the walking line: the flight's centre line, from before the first step (y -1.528) to past the last (y 2.8)
    expect(st.walk).toEqual([st.bottom, st.top]);
    expect(st.bottom[0]).toBeCloseTo(-3.415, 3);
    expect(st.top[0]).toBeCloseTo(-3.415, 3);
    expect(st.bottom[1]).toBeLessThanOrEqual(-1.528 - 0.3 + 1e-9);
    expect(st.top[1]).toBeGreaterThanOrEqual(2.8 + 0.5 - 1e-9);
    expect(isClimbing(m)).toBe(true);
    expect(isClimbing(before)).toBe(false);
  });

  it("re-kinds the 16 steps of F1-S1 to treads of that stairway; F2-S1 (to a floor 3, not drawn) stays steps", () => {
    const before = hotel(), r = upgradeSteps(before), m = r.model;
    const treads = m.parts.filter(p => p.kind === 'tread');
    expect(treads).toHaveLength(16);
    expect(treads.every(p => p.floor === 'F1' && p.stair === 'F1-S1' && p.fit === 'storey' && /^F1-S1 step \d+ up$/.test(p.label ?? ''))).toBe(true);
    const steps = m.parts.filter(p => p.kind === 'step');
    expect(steps).toHaveLength(7);
    expect(steps.every(p => p.floor === 'F2' && p.stair === undefined && (p.label ?? '').startsWith('F2-S1 step'))).toBe(true);
    expect(r.refused).toEqual([{ floor: 'F2', flight: 'F2-S1', why: 'no floor above in the stack' }]);
    // nothing else differs: the same parts in the same order, each tread its step with three fields changed
    expect(m.parts).toHaveLength(before.parts.length);
    m.parts.forEach((p, i) => {
      const was = before.parts[i]!;
      if (p.kind === 'tread') expect(p).toEqual({ ...was, kind: 'tread', fit: 'storey', stair: 'F1-S1' });
      else expect(p).toBe(was);
    });
    const { parts: _p, stairways: _s, ...rest } = m, { parts: _q, ...restBefore } = before;
    expect(rest).toEqual(restBefore);
  });

  it('never changes the model handed in, and the result is a valid BuiltModel v2 (the parser and the schema)', () => {
    const before = hotel(), copy = structuredClone(before);
    const m = upgradeModel(before);
    expect(m).not.toBe(before);
    expect(before).toEqual(copy);
    expect(before).toEqual(json('fixtures/models/hotel.model.json'));
    expect(parseBuiltModel(structuredClone(m))).toEqual(m);
    expect(ajv(m)).toBe(true);
    expect(upgradeModel(m)).toBe(m);                                   // a model with `stairways` is left alone
  });

  it('buildScene sees a v2 stair: one tread mesh on F1 (walked on, never a collider), surfaces listed, F2 steps still colliders', () => {
    const m = upgradeModel(hotel());
    const built = buildScene(m, resolvePresentation(parsePresentation(json('fixtures/presentation/hotel-lobby.json')), m));
    const [f1, f2] = built.floors as [typeof built.floors[0], typeof built.floors[0]];
    const names = (f: typeof f1) => f.group.children.map(o => o.name);
    expect(names(f1)).toContain('F1 tread:storey');
    expect(names(f1)).not.toContain('F1 step:own');
    expect(names(f2)).toContain('F2 step:own');
    const tread = f1.group.children.find(o => o.name === 'F1 tread:storey')!;
    expect(tread.userData).toMatchObject({ steps: true, stairTo: 'F2', floor: 'F1' });
    expect(f1.colliders.map(c => c.name)).not.toContain('F1 tread:storey');
    expect(f1.surfaces.map(c => c.name).sort()).toEqual(['F1 floor plate', 'F1 floor plate', 'F1 tread:storey']);
    expect(f2.colliders.map(c => c.name)).toContain('F2 step:own');
    expect(f1.rise.find(r => r.mesh === tread)?.fit).toBe('storey');
    // without the upgrade: the steps are one collider mesh and nothing is a surface (the level-based walker)
    const old = hotel(), builtOld = buildScene(old, resolvePresentation(parsePresentation(json('fixtures/presentation/hotel-lobby.json')), old));
    expect(builtOld.floors[0]!.colliders.map(c => c.name)).toContain('F1 step:own');
    expect(builtOld.floors.flatMap(f => f.surfaces)).toEqual([]);
  });
});

describe('upgradeModel: every other fixture comes back as it was', () => {
  const OLD = ['bank-v1', 'bank-v2', 'house', 'suite', 'mini'];
  it.each(OLD)('%s: no derived stairway, the very object parsed, deep-equal to its file', name => {
    const before = fixture(name), r = upgradeSteps(before);
    expect(r.derived).toEqual([]);
    expect(r.model).toBe(before);
    expect(upgradeModel(before)).toBe(before);
    expect(before).toEqual(json(`fixtures/models/${name}.model.json`));
    expect(before.stairways).toBeUndefined();
    expect(isClimbing(r.model)).toBe(false);
  });

  it("the bank's two L2 flights lead to a floor that is not in the model; the house, the suite and mini have no steps", () => {
    for (const name of ['bank-v1', 'bank-v2']) {
      const r = upgradeSteps(fixture(name));
      expect(r.refused.map(x => [x.floor, x.why])).toEqual([['L2', 'no floor above in the stack'], ['L2', 'no floor above in the stack']]);
    }
    for (const name of ['house', 'suite', 'mini']) {
      expect(fixture(name).parts.filter(p => p.kind === 'step')).toEqual([]);
      expect(upgradeSteps(fixture(name)).refused).toEqual([]);
    }
  });

  it.each(['rooms-reference', 'stairs-straight', 'stairs-L', 'stairs-U'])('%s (a model with `stairways`) is not looked at', name => {
    const before = fixture(name);
    expect(upgradeSteps(before)).toEqual({ model: before, derived: [], refused: [] });
    expect(upgradeModel(before)).toBe(before);
  });

  it('a model with an empty `stairways` list is left alone too, steps and all', () => {
    const m = { ...hotel(), stairways: [] } as BuiltModel;
    expect(upgradeModel(m)).toBe(m);
  });
});

describe('upgradeModel: the strict rule, each condition refused on a doctored copy of the hotel flight', () => {
  const unchanged = (m: BuiltModel, r: ReturnType<typeof upgradeSteps>) => {
    expect(r.derived).toEqual([]);
    expect(r.model).toBe(m);
    expect(m.stairways).toBeUndefined();
    expect(m.parts.filter(p => p.kind === 'tread')).toEqual([]);
  };

  it('the undoctored copy qualifies (the control)', () => {
    const { r } = doctored(() => {});
    expect(r.derived).toHaveLength(1);
  });

  it('an uneven riser (one top 3 cm high)', () => {
    const { m, r } = doctored((_m, s) => { s[7]!.z1 += 0.03; });
    unchanged(m, r);
    expect(refusedF1(r)).toBe('the risers are uneven');
  });

  it('a top within 1 cm of its place still qualifies (the tolerance)', () => {
    const { r } = doctored((_m, s) => { s[7]!.z1 += 0.004; });
    expect(r.derived).toHaveLength(1);
  });

  it('a missing step in the middle', () => {
    const { m, r } = doctored((mm, s) => { mm.parts.splice(mm.parts.indexOf(s[8]!), 1); });
    unchanged(m, r);
    expect(refusedF1(r)).toMatch(/risers are uneven|do not share an edge/);
  });

  it('a missing step with the tops closed up (the plan gap alone)', () => {
    const { m, r } = doctored((mm, s) => {
      mm.parts.splice(mm.parts.indexOf(s[8]!), 1);
      const h = (mm.floors[1]!.level - mm.floors[0]!.level) / 16;
      s.filter((_p, i) => i !== 8).forEach((p, k) => { p.z1 = h * (k + 1); p.z0 = p.z1 - 2 * h; });
    });
    unchanged(m, r);
    expect(refusedF1(r)).toBe('two steps do not share an edge (a step is missing, or they overlap)');
  });

  it('the top one riser short of F2 (the last step gone)', () => {
    const { m, r } = doctored((mm, s) => { mm.parts.splice(mm.parts.indexOf(s[15]!), 1); });
    unchanged(m, r);
    expect(refusedF1(r)).toBe("the last step's top is not one riser below F2");
  });

  it('a riser over 0.25 m (the whole flight and F2 stretched to 0.26 m risers)', () => {
    const { m, r } = doctored((mm, s) => {
      const k = 0.26 / (2.9 / 17);
      for (const p of s) { p.z0 *= k; p.z1 *= k; }
      mm.floors[1]!.level = 0.26 * 17;
    });
    unchanged(m, r);
    expect(refusedF1(r)).toMatch(/^a riser of 0\.26/);
  });

  it('a riser under 0.12 m', () => {
    const { m, r } = doctored((mm, s) => {
      const k = 0.11 / (2.9 / 17);
      for (const p of s) { p.z0 = p.z0 * k; p.z1 *= k; }
      mm.floors[1]!.level = 0.11 * 17;
    });
    unchanged(m, r);
    expect(refusedF1(r)).toMatch(/^a riser of 0\.11/);
  });

  it("the arrival not on F2's slab (a hole in the slab past the last step)", () => {
    const { m, r } = doctored(mm => {
      const slab = mm.parts.find(p => p.kind === 'slab' && p.floor === 'F2')!;
      slab.h.push([[-4.4, 2.9], [-4.4, 3.7], [-2.4, 3.7], [-2.4, 2.9]]);
    });
    unchanged(m, r);
    expect(refusedF1(r)).toBe("the arrival is not on F2's slab");
  });

  it('no F2 slab at all', () => {
    const { m, r } = doctored(mm => { mm.parts = mm.parts.filter(p => !(p.kind === 'slab' && p.floor === 'F2')); });
    unchanged(m, r);
    expect(refusedF1(r)).toBe("the arrival is not on F2's slab");
  });

  it('no F1 slab before the first step', () => {
    const { m, r } = doctored(mm => { mm.parts = mm.parts.filter(p => !(p.kind === 'slab' && p.floor === 'F1')); });
    unchanged(m, r);
    expect(refusedF1(r)).toBe('no F1 slab before the first step');
  });

  it('a step that is not a rectangle, a step with a hole, a step of another width, a step of another going', () => {
    const cases: [string, (s: Part[]) => void][] = [
      ['a step is not a rectangle along the flight', s => { s[4]!.o[0] = [s[4]!.o[0]![0] + 0.3, s[4]!.o[0]![1] + 0.1]; }],
      ['a step is not a rectangle along the flight', s => { s[4]!.o.push([-3.4, s[4]!.o[3]![1] + 0.1]); }],
      ['a step has a hole', s => { s[4]!.h.push([[-4, -0.4], [-4, -0.3], [-3, -0.3]]); }],
      ['the steps are not of one width', s => { s[4]!.o[0]![0] += 0.4; s[4]!.o[3]![0] += 0.4; }],
      ['the goings differ', s => { s[15]!.o[2]![1] += 0.05; s[15]!.o[3]![1] += 0.05; }],
    ];
    for (const [why, change] of cases) {
      const { m, r } = doctored((_m, s) => change(s));
      unchanged(m, r);
      expect(refusedF1(r)).toBe(why);
    }
  });

  it('a step that follows the wall height or has a fit; a flight of two steps; a floor above in another stack only', () => {
    let d = doctored((_m, s) => { s[3]!.follow = true; });
    unchanged(d.m, d.r);
    expect(refusedF1(d.r)).toBe('a step follows the wall height or has a fit');
    d = doctored((mm, s) => { for (const p of s.slice(2)) mm.parts.splice(mm.parts.indexOf(p), 1); });
    unchanged(d.m, d.r);
    expect(refusedF1(d.r)).toBe('only 2 step(s)');
    d = doctored(mm => { mm.floors[1]!.stack = 'annex'; });
    unchanged(d.m, d.r);
    expect(refusedF1(d.r)).toBe('no floor above in the stack');
  });

  it('steps with no flight in their label are grouped by the one stair outline that holds them; with none, they stay steps', () => {
    let d = doctored((_m, s) => { for (const p of s) delete p.label; });
    expect(d.r.derived.map(st => [st.id, st.risers])).toEqual([['F1-S1', 17]]);
    d = doctored((mm, s) => { for (const p of s) delete p.label; mm.stairOutlines.F1 = []; });
    unchanged(d.m, d.r);
    expect(d.r.refused.filter(x => x.floor === 'F1')).toEqual([]);     // in no flight at all
  });
});

describe('upgradePresentation', () => {
  const base = parsePresentation(json('fixtures/presentation/hotel-lobby.json'));
  it('leaves the presentation alone when nothing was derived, when `step` is not styled, or when `tread` is', () => {
    expect(upgradePresentation(base, true)).toBe(base);
    const styled = { ...base, partStyles: { step: { color: '#112233', edge: '#445566', mesh: 'step' } } };
    expect(upgradePresentation(styled, false)).toBe(styled);
    const both = { ...base, partStyles: { ...styled.partStyles, tread: { color: '#000000' } } };
    expect(upgradePresentation(both, true)).toBe(both);
  });
  it("gives the derived treads the step's own colours, not its mesh name or collider", () => {
    const styled: Presentation = { ...base, partStyles: { step: { color: '#112233', edge: '#445566', mesh: 'step', collider: true } } };
    const p = upgradePresentation(styled, true), m = upgradeModel(hotel());
    expect(p.partStyles!.tread).toEqual({ color: '#112233', edge: '#445566' });
    expect(resolvePresentation(p, m).partStyles.tread).toMatchObject({ color: '#112233', edge: '#445566', mesh: 'tread', collider: false });
    expect(styled.partStyles).not.toHaveProperty('tread');
  });
});
