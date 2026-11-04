// Synthetic replay data for the replay's tests (builder D), browser-safe (no node:fs): the unit tests import it through
// test/unit/replay/helpers.ts, the harness pages directly.
//  * syntheticModel / syntheticStages: one floor at level 0 with one 10 m wall, 3 m high, straight in front of a fixed
//    camera, so the rise shader can be checked pixel by pixel on the GPU (replay-page.ts).
//  * stagesFor(model): replay data for any model, for the projects that have no stages fixture (the suite's and the house's
//    are converted by builder E's seed; DESIGN.md 17.1 has none provisional).
import type { BuiltModel, ReplayData } from '../../../src/contracts';

export const WALL_HEIGHT = 3;
const wall: [number, number][] = [[-5, -0.15], [5, -0.15], [5, 0.15], [-5, 0.15]];

export const syntheticModel: BuiltModel = {
  project: 'Replay harness wall', shortName: 'Wall', projectNo: null, source: ['synthetic'], units: 'm', offset: [0, 0],
  photoName: 'Wall', maxPrefix: 'WL',
  floors: [{ key: 'G', name: 'Ground', level: 0, wallHeight: WALL_HEIGHT, slabThickness: 0.25 }],
  railingHeight: 1.1, singleLineHeight: 1, doorHeadDefault: 2.1,
  parts: [
    { floor: 'G', kind: 'wall', z0: 0, z1: WALL_HEIGHT, follow: true, o: wall, h: [] },
    { floor: 'G', kind: 'slab', z0: -0.25, z1: 0, follow: false, o: [[-8, -6], [8, -6], [8, 6], [-8, 6]], h: [] },
  ],
  stairs: {}, voids: {}, closures: {}, stairOutlines: {}, rooms: [], openings: [], probes: [], colliderSkins: {},
};

export const syntheticStages: ReplayData = {
  source: { file: 'wall.dwg', units: 'mm' },
  intro: ['One wall'],
  layers: [['Walls', 'A-WALL']],
  floors: {
    G: {
      sheet: [0, 0],
      lines: { wall: wall.flatMap((p, i) => { const q = wall[(i + 1) % wall.length]!; return [p[0], p[1], q[0], q[1]]; }) },
      pieces: { wall: wall.flat() },
      rings: { wall: [{ o: wall, h: [] }] },
    },
  },
  captions: { read: 'Read.', sort: 'Sort.', align: 'Level {Glevel+} m.', pair: 'Pair.', merge: 'Merge.', raise: 'Walls rise to {Gheight} m.', finish: 'Done.' },
};

/**
 * Replay data for any model (tests only): per floor, every non-slab outline as 'wall' (or 'glass') lines and merged rings,
 * the outlines' first four corners as pieces, a few 'noise' lines far away (left out of the framing), the floors drawn
 * `shift` m apart to the east on the sheet; captions with every placeholder form for the first and last floor keys and an
 * unknown key. Valid ReplayData v1 for its model (parseReplayData: one entry per model floor, flat arrays of 4 and 8).
 */
export function stagesFor(m: BuiltModel, shift = 30): ReplayData {
  const floors: ReplayData['floors'] = {};
  m.floors.forEach((f, i) => {
    const lines: Record<string, number[]> = { wall: [], glass: [], noise: [500, 500, 501, 501] };
    const pieces: Record<string, number[]> = { wall: [], glass: [] };
    const rings: ReplayData['floors'][string]['rings'] = { wall: [], glass: [] };
    for (const p of m.parts) {
      if (p.floor !== f.key || p.kind === 'slab') continue;
      const cat = p.kind === 'glass' || p.kind === 'pane' ? 'glass' : 'wall';
      p.o.forEach((a, j) => { const b = p.o[(j + 1) % p.o.length]!; lines[cat]!.push(a[0], a[1], b[0], b[1]); });
      if (p.o.length >= 4) pieces[cat]!.push(...p.o.slice(0, 4).flat());
      rings[cat]!.push({ o: p.o, h: p.h });
    }
    floors[f.key] = { sheet: [i * shift, 0], lines, pieces, rings };
  });
  const k0 = m.floors[0]!.key, kn = m.floors[m.floors.length - 1]!.key;
  return {
    source: { file: `${m.shortName}.dwg`, units: 'mm' },
    intro: ['One synthetic plan, in metres', `${m.parts.length} parts`],
    layers: [['Walls', 'A-WALL'], ['Left out', 'everything else']],
    floors,
    captions: {
      read: 'Read the drawing.', sort: 'Sort the lines.', align: `Floors at {${k0}level+} m and {${kn}level} m.`, pair: 'Pair the faces.',
      merge: 'Merge them.', raise: `Walls rise to {${k0}height} m; {nokeylevel} stays.`, finish: 'Done.',
    },
  };
}
