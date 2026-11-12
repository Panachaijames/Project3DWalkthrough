// The rooms review's (RR) three viewer fixes, each with the case that failed before it: the eye slider and the head ray
// (CODE-2 / BRK-6), a floor with no slab in a stack that has slabs (CODE-4 / BRK-7), and the stairs' colours (S15).
import type { MeshStandardMaterial } from 'three';
import { describe, expect, it } from 'vitest';
import type { BuiltModel, Part, Vec2 } from '../../../src/contracts';
import { parseBuiltModel } from '../../../src/model/parse';
import { DEFAULT_PART_STYLES } from '../../../src/model/styles';
import { EYE, EYE_MAX, HEAD_ABOVE_EYE, HEAD_REACH } from '../../../src/modes/state';
import { climbRig, parsed, r3, referenceRig, type ClimbRig } from './climb-kit';
import { fixtureModel, fixturePresentation } from './synthetic';

/** Up the stairway's walking line and back down it; the foot and floor at the top and at the bottom. */
function upAndBack(rig: ClimbRig) {
  const st = rig.model.stairways![0]!, line = st.walk as Vec2[];
  rig.put(st.from, line[0]![0], line[0]![1]);
  rig.along(line.slice(1));
  const top = [r3(rig.s.foot), rig.s.floor.key];
  rig.along(line.slice(0, -1).reverse());
  return { top, bottom: [r3(rig.s.foot), rig.s.floor.key] };
}

describe('the eye slider moves the camera only (RR CODE-2 / BRK-6)', () => {
  it('the head reach is the default eye\'s, whatever the slider says', () => {
    expect(HEAD_REACH).toBeCloseTo(EYE + HEAD_ABOVE_EYE, 9);
  });

  it('at the highest eye the reference stair is climbed to the upper floor and back, as at the default eye', () => {
    // the first flight passes under the upper slab's edge (y -1.91) with 2.10 m of headroom over the treads
    for (const eye of [EYE, EYE_MAX]) {
      const rig = referenceRig();
      rig.s.eye = eye;
      expect([eye, upAndBack(rig)]).toEqual([eye, { top: [3, 'upper'], bottom: [0, 'ground'] }]);
    }
  });

  it('in a 2.7 m storey the highest eye walks under the slab above (its underside 2.45 m over the floor)', () => {
    for (const eye of [EYE, EYE_MAX]) {
      const rig = referenceRig(), up = rig.floor('upper').group;
      up.position.y -= 0.3; up.updateMatrixWorld(true);
      rig.s.eye = eye;
      rig.put('ground', -1, 2);
      expect([eye, r3(rig.go(0, 1, 1.5)), r3(rig.s.foot)]).toEqual([eye, 1.5, 0]);
    }
  });
});

describe('a floor with no slab in a stack that has slabs (RR CODE-4 / BRK-7)', () => {
  /** The reference building with the upper floor's slab taken out (its walls never closed): the ground keeps its slab. */
  function slablessUpper(): BuiltModel {
    const raw = fixtureModel('rooms-reference') as BuiltModel & { parts: Part[] };
    raw.parts = raw.parts.filter(p => !(p.kind === 'slab' && p.floor === 'upper'));
    return parseBuiltModel(raw);
  }

  it('the walker moves on the slabless floor as the old walker does (no floor check there)', () => {
    const rig = climbRig(slablessUpper());
    expect(rig.floor('upper').walkables).toHaveLength(0);
    expect(rig.floor('ground').walkables.length).toBeGreaterThan(0);
    rig.put('upper', -1, 2);
    expect(rig.walk.onFloor(rig.s.pos, rig.s.floor)).toBe(true);
    expect([r3(rig.go(0, 1, 1.5)), r3(rig.s.foot), rig.s.floor.key]).toEqual([1.5, 3, 'upper']);
  });

  it('off the side of the flight, over the slabless floor\'s stair well, is still an edge', () => {
    const rig = climbRig(slablessUpper()), line = rig.model.stairways![0]!.walk as Vec2[];
    rig.put('ground', line[0]![0], line[0]![1]);
    rig.along(line.slice(1, 4));                                      // on the landing, foot 1.125
    rig.along(line.slice(4, 5));                                      // up the second flight to its start
    rig.to(-2.9, -0.42);                                               // high on the second flight, named upper
    const foot = rig.s.foot;
    expect(rig.s.floor.key).toBe('upper');
    expect(foot).toBeGreaterThan(1.9);
    expect(foot).toBeLessThan(2.6);
    rig.go(0, -1, 1.0);                                                // south, off the flight's side into the well
    expect(rig.s.foot).toBeCloseTo(foot, 6);
    expect(rig.plan()[1]).toBeGreaterThan(-0.42 - 0.65);              // stopped at the flight's side (0.6 m wide)
  });

  it('the slabbed floor of the same stack still walks, and its stair climbs onto the slabless floor and back', () => {
    const rig = climbRig(slablessUpper());
    rig.put('ground', -1, 2);
    expect([r3(rig.go(0, 1, 1.5)), r3(rig.s.foot)]).toEqual([1.5, 0]);
    const st = rig.model.stairways![0]!, line = st.walk as Vec2[];
    rig.put('ground', line[0]![0], line[0]![1]);
    rig.along(line.slice(1, 3));
    expect(r3(rig.s.foot)).toBe(1.125);                              // the first flight's top: riser 6 of 16
    rig.along(line.slice(3));
    expect([r3(rig.s.foot), rig.s.floor.key]).toEqual([3, 'upper']);
    rig.along(line.slice(0, -1).reverse());
    expect([r3(rig.s.foot), rig.s.floor.key]).toEqual([0, 'ground']);
  });
});

describe('the stairs\' colours (RR S15)', () => {
  it('treads and landings are drawn in the legend\'s stairs colour, as steps are', () => {
    for (const kind of ['tread', 'landing'] as const) {
      expect([kind, DEFAULT_PART_STYLES[kind].color, DEFAULT_PART_STYLES[kind].edge])
        .toEqual([kind, DEFAULT_PART_STYLES.step.color, DEFAULT_PART_STYLES.step.edge]);
    }
    expect(DEFAULT_PART_STYLES.step.color).toBe('#b9c7b4');           // out/presentation.py's 'Stairs' legend item
  });

  it('the reference building\'s treads come out of buildScene in that colour', () => {
    const rig = climbRig(parsed('rooms-reference'), fixturePresentation('rooms-reference'));
    const treads = rig.floor('ground').surfaces.filter(m => /tread|landing/.test(m.name));
    expect(treads.length).toBeGreaterThan(0);
    const colours = new Set(treads.map(m => (m.material as MeshStandardMaterial).color.getHexString()));
    expect([...colours]).toEqual(['b9c7b4']);
  });
});
