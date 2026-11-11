// The climbing tests' kit (rooms step R4; not a test file): a BuiltModel v2 fixture through the real parser, presentation
// and buildScene, with the foot-based walker of modes/walk.ts on a bare state (no DOM), and walks along plan lines.
import { PerspectiveCamera, Vector3 } from 'three';
import type { BuiltModel, BuiltScene, FloorRecord, ModesState, Vec2 } from '../../../src/contracts';
import { buildScene } from '../../../src/core/build';
import { parseBuiltModel } from '../../../src/model/parse';
import { parsePresentation, resolvePresentation } from '../../../src/model/presentation';
import { createState } from '../../../src/modes/state';
import { createWalker, type Walker } from '../../../src/modes/walk';
import { fixtureModel, fixturePresentation } from './synthetic';

export interface ClimbRig {
  model: BuiltModel; built: BuiltScene; floors: FloorRecord[]; s: ModesState; walk: Walker;
  floor(key: string): FloorRecord;
  /** Puts the walker at a plan point on a floor's level (a teleport). */
  put(key: string, x: number, y: number): void;
  /** Puts the walker at a plan point with its foot at a height (on a tread). */
  putAt(key: string, x: number, y: number, foot: number): void;
  /** Walks toward the plan point (x, y) in steps of about 5 cm (as probe.walk does); returns the horizontal distance made. */
  to(x: number, y: number, each?: () => void): number;
  /** Walks along a plan line (the walker is put on its first point's x, y first when `start` is given). */
  along(line: Vec2[], each?: () => void): void;
  /** Walks `metres` along the plan direction (dx, dy). */
  go(dx: number, dy: number, metres: number, each?: () => void): number;
  plan(): [number, number];
}

export const PLAIN = {
  documentTitle: 't', heading: 'h', intro: [], accent: '#2f6f8f', legend: { layout: 'inline', items: [] },
  camera: { kind: 'fixed', position: [24, 27, 29], target: [0, 2.5, 0] },
};

export function parsed(name: string): BuiltModel { return parseBuiltModel(fixtureModel(name)); }

export function climbRig(model: BuiltModel, presentation: unknown = PLAIN): ClimbRig {
  const built = buildScene(model, resolvePresentation(parsePresentation(presentation), model));
  const floors = built.floors;
  for (const f of floors) f.group.updateMatrixWorld(true);
  const s = createState({ camera: new PerspectiveCamera(40, 1.6, 0.1, 500), floors, model });
  const thick = new Map(model.floors.map(f => [f.key, f.slabThickness ?? 0.25]));
  const walk = createWalker(s, { floors, thickness: f => thick.get(f.key) ?? 0.25, height: f => f.wallHeight });
  const floor = (key: string) => floors.find(f => f.key === key)!;
  const rig: ClimbRig = {
    model, built, floors, s, walk, floor,
    put(key, x, y) { rig.putAt(key, x, y, floor(key).level); },
    putAt(key, x, y, foot) {
      s.mode = 'walk'; s.floor = floor(key); s.foot = foot; s.pos.set(x, foot + s.eye, -y); walk.nameFloor(); walk.settle();
    },
    to(x, y, each) {
      const dx = x - s.pos.x, dz = -y - s.pos.z, len = Math.hypot(dx, dz);
      if (len < 1e-9) return 0;
      const n = Math.max(1, Math.round(len / 0.05)), d = new Vector3(dx / n, 0, dz / n), x0 = s.pos.x, z0 = s.pos.z;
      for (let i = 0; i < n; i++) { walk.walkMove(d.clone()); each?.(); }
      return Math.hypot(s.pos.x - x0, s.pos.z - z0);
    },
    along(line, each) { for (const [x, y] of line) rig.to(x, y, each); },
    go(dx, dy, metres, each) {
      const l = Math.hypot(dx, dy);
      return rig.to(s.pos.x + dx / l * metres, -s.pos.z + dy / l * metres, each);
    },
    plan: () => [s.pos.x, -s.pos.z],
  };
  return rig;
}

export const referenceRig = (): ClimbRig => climbRig(parsed('rooms-reference'), fixturePresentation('rooms-reference'));
export const r3 = (v: number) => Math.round(v * 1000) / 1000;
