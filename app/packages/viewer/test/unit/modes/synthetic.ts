// Builder B's test models (not a test file): small BuiltModel v1 shapes for makeTestContext, in plan metres.
//
// room(): floor L1 at 0 m, a 12 x 10 m slab with a 2 x 2 m void (plan x 2 - 4, y 1 - 3); a 10 x 8 m room (inner faces
// at x = -5 / 5, y = -4 / 4) walled 0.2 m thick, 3 m high; a 7 cm partition at x = -0.035 - 0.035 from the south wall to
// y = 1 (2.5 m high). Floor L2 at 3.5 m: a slab over the west half only.
// corridor(): floor C at 0 m, a closed corridor 1.2 m wide (inner faces y = -0.6 / 0.6) from x = -2 to 3.8.
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import type { BuiltFloor, BuiltModel, Part, Presentation, Ring } from '../../../src/contracts';

export const APP = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../../../..');
export const fixtureModel = (name: string) => JSON.parse(readFileSync(path.join(APP, 'fixtures/models', `${name}.model.json`), 'utf8')) as BuiltModel;
export const fixturePresentation = (name: string) => JSON.parse(readFileSync(path.join(APP, 'fixtures/presentation', `${name}.json`), 'utf8')) as Presentation;

export const rect = (x0: number, y0: number, x1: number, y1: number): Ring => [[x0, y0], [x1, y0], [x1, y1], [x0, y1]];
const wall = (floor: string, o: Ring, z1 = 3): Part => ({ floor, kind: 'wall', z0: 0, z1, follow: true, o, h: [] });
const slab = (floor: string, o: Ring, h: Ring[] = []): Part => ({ floor, kind: 'slab', z0: -0.25, z1: 0, follow: false, o, h });

function model(floors: BuiltFloor[], parts: Part[]): BuiltModel {
  const empty = <T>() => Object.fromEntries(floors.map(f => [f.key, [] as T[]]));
  return {
    project: 'Synthetic', shortName: 'Synthetic', projectNo: null, source: ['synthetic'], units: 'm', offset: [0, 0],
    photoName: 'Synthetic', maxPrefix: 'SY', floors, railingHeight: 1.1, singleLineHeight: 1, doorHeadDefault: 2.1, parts,
    stairs: Object.fromEntries(floors.map(f => [f.key, { below: [], above: [] }])), voids: empty(), closures: empty(),
    stairOutlines: empty(), rooms: [], openings: [], probes: [], colliderSkins: empty(),
  };
}

export function room(): BuiltModel {
  const floors: BuiltFloor[] = [
    { key: 'L1', name: 'Level 1', level: 0, wallHeight: 3, slabThickness: 0.25 },
    { key: 'L2', name: 'Level 2', level: 3.5, wallHeight: 3, slabThickness: 0.25 },
  ];
  return model(floors, [
    slab('L1', rect(-6, -5, 6, 5), [rect(2, 1, 4, 3)]),
    wall('L1', rect(-5.2, -4.2, -5, 4.2)),          // west
    wall('L1', rect(5, -4.2, 5.2, 4.2)),            // east
    wall('L1', rect(-5, -4.2, 5, -4)),              // south
    wall('L1', rect(-5, 4, 5, 4.2)),                // north
    wall('L1', rect(-0.035, -4, 0.035, 1), 2.5),    // the 7 cm partition
    slab('L2', rect(-6, -5, 0, 5)),
    wall('L2', rect(-5.2, -4.2, -5, 4.2)),
  ]);
}

export function corridor(): BuiltModel {
  return model([{ key: 'C', name: 'Corridor', level: 0, wallHeight: 3, slabThickness: 0.25 }], [
    slab('C', rect(-3, -2, 5, 2)),
    wall('C', rect(-2.2, -0.8, 4.0, -0.6)),          // south side
    wall('C', rect(-2.2, 0.6, 4.0, 0.8)),            // north side
    wall('C', rect(-2.2, -0.6, -2, 0.6)),            // west end
    wall('C', rect(3.8, -0.6, 4.0, 0.6)),            // east end
  ]);
}
