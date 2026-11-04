// Builder A's unit-test kit: A's REAL core modules (buildScene, createPictures, createVisibility, createHeights,
// createReadouts, createLabels) on a context without WebGL (Node, or happy-dom for the DOM parts). The scaffold's
// test/harness/context.ts builds naively (one mesh per part, no fit data), so the core's own behaviour is tested here.
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { PerspectiveCamera, Scene } from 'three';
import type {
  BuiltModel, FloorRecord, InternalEvents, ModesApi, Presentation, ReplayApi, ResolvedOptions, ViewerContext, ViewerEvents,
} from '../../../src/contracts';
import { buildScene } from '../../../src/core/build';
import { createDisposer } from '../../../src/core/disposer';
import { createEventBus } from '../../../src/core/events';
import { createHeights } from '../../../src/core/heights';
import { createPictures } from '../../../src/core/pictures';
import { createReadouts } from '../../../src/core/readouts';
import { createVisibility } from '../../../src/core/visibility';
import { parseBuiltModel } from '../../../src/model/parse';
import { parsePresentation, resolvePresentation } from '../../../src/model/presentation';

export const APP = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../../../..');
export const json = (rel: string): any => JSON.parse(readFileSync(path.join(APP, rel), 'utf8'));
export const FEATURES = 'packages/viewer/test/fixtures/features.model.json';
export const MODEL: Record<string, string> = {
  'bank-v1': 'fixtures/models/bank-v1.model.json', 'bank-v2': 'fixtures/models/bank-v2.model.json', hotel: 'fixtures/models/hotel.model.json',
  suite: 'fixtures/models/suite.model.json', house: 'fixtures/models/house.model.json', mini: 'fixtures/models/mini.model.json', features: FEATURES,
};
export const PRESENTATION: Record<string, string | null> = {
  'bank-v1': 'bank-sampeng-v1', 'bank-v2': 'bank-sampeng-v2', hotel: 'hotel-lobby', suite: 'presidential-suite', house: 'sukhumvit-house',
  mini: null, features: null,
};
const PLAIN: Presentation = { documentTitle: 't', heading: 'h', intro: [], accent: '#2f6f8f', legend: { layout: 'inline', items: [] }, camera: { kind: 'fixed', position: [24, 27, 29], target: [0, 2.5, 0] } };

export type KitContext = ViewerContext & { modes: ModesApi & { mode: 'orbit' | 'walk' | 'ghost' } };

/** A context with A's real core on `name` (a key of MODEL), the renderer a stub, modes a mode holder, no replay. */
export function kitContext(name: string, opts: { pictures?: Record<string, string>; address?: ResolvedOptions['address']; size?: { width: number; height: number }; root?: HTMLDivElement } = {}): KitContext {
  const model: BuiltModel = parseBuiltModel(json(MODEL[name] ?? name));
  const p = PRESENTATION[name];
  const presentation = resolvePresentation(parsePresentation(p ? json(`fixtures/presentation/${p}.json`) : PLAIN), model);
  const built = buildScene(model, presentation);
  const scene = new Scene();
  for (const f of built.floors) scene.add(f.group);
  if (built.groundPlane) scene.add(built.groundPlane);
  const size = opts.size ?? { width: 1400, height: 880 };
  const camera = new PerspectiveCamera(40, size.width / size.height, 0.1, presentation.camera.far);
  if (presentation.camera.kind === 'fixed') { camera.position.set(...presentation.camera.position); camera.lookAt(...presentation.camera.target); }
  camera.updateMatrixWorld();
  const styles: string[] = [];
  const root = opts.root ?? ({} as HTMLDivElement);
  const modes = { mode: 'orbit' } as KitContext['modes'];
  const ctx = {
    id: 'kit', container: root, renderer: { capabilities: { getMaxAnisotropy: () => 4 } }, canvas: null, scene, camera, controls: null,
    model, presentation, stages: null,
    project: { model, presentation, stages: null, pictures: opts.pictures ?? {}, heights: null, stamp: 'kitkitkitkit' },
    options: { address: opts.address ?? {}, build: 'skip', furnitureHeights: 'local', storageKey: 'k', testHook: false, pixelRatioCap: 2,
      download: () => {}, noDownload: true, testFailAt: null },
    floors: built.floors, floorByKey: new Map<string, FloorRecord>(built.floors.map(f => [f.key, f])), built,
    disposer: createDisposer(), events: createEventBus<ViewerEvents>(), bus: createEventBus<InternalEvents>(),
    ui: { root, hint: null, errorBox: null, addStyle: (css: string) => { styles.push(css); }, setFlag: () => {} },
    size: () => ({ ...size }),
    rectOf: () => ({ left: 0, top: 0, right: 0, bottom: 0, width: 0, height: 0 }),
    reportError: (err: unknown) => { throw err; },
    pictures: null, modes, furniture: null, replay: null as ReplayApi | null, panel: null, labels: null, loop: null,
    kitStyles: styles,
  } as unknown as KitContext & { pictures: ViewerContext['pictures'] };
  const w = ctx as unknown as Record<string, unknown>;
  w.pictures = createPictures(ctx);
  w.visibility = createVisibility(ctx);
  w.heights = createHeights(ctx);
  w.readouts = createReadouts(ctx);
  return ctx;
}

/** World-space vertical extent of a mesh (its matrices updated). */
export function worldY(mesh: { updateWorldMatrix(a: boolean, b: boolean): void; geometry: any; matrixWorld: any }): [number, number] {
  mesh.updateWorldMatrix(true, false);
  mesh.geometry.computeBoundingBox();
  const b = mesh.geometry.boundingBox.clone().applyMatrix4(mesh.matrixWorld);
  return [b.min.y, b.max.y];
}
