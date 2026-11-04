// Builder A's harness page (npm run harness -- --port 5721; /core/viewer.html): createViewer on a fixture model with its
// fixtures/presentation/*.json (and the bank's stages, the hotel's pictures), the test hook on, the page's own address.
//   ?project=bank-v1 | bank-v2 | hotel | suite | house | features | mini   (default bank-v2)
//   ?nomount=1   load the project but do not mount: the leak checks drive window.__wtvMount themselves
//   ?host=1      furnitureHeights 'host' (the staff app's mode)
// window.__core: what the specs need (the project, the options, createViewer, the status of the first mount).
import type { BuiltModel, Presentation, ReplayData, ViewerOptions, ViewerProject } from '../../../src/contracts';
import { createViewer, ModelError, parseAddressOptions } from '../../../src/index';
import { makeMountApi, type MountApi } from '../../../src/offline/mount';

interface Fixture { model: string; presentation: string | null; stages?: string; pictures?: Record<string, string>; stamp: string; projectId: string; version: number }
const F: Record<string, Fixture> = {
  'bank-v1': { model: new URL('../../../../../fixtures/models/bank-v1.model.json', import.meta.url).href, presentation: new URL('../../../../../fixtures/presentation/bank-sampeng-v1.json', import.meta.url).href,
    stages: new URL('../../../../../fixtures/stages/bank-v1.stages.json', import.meta.url).href, stamp: '4b02dc17f286', projectId: 'bank-sampeng', version: 1 },
  'bank-v2': { model: new URL('../../../../../fixtures/models/bank-v2.model.json', import.meta.url).href, presentation: new URL('../../../../../fixtures/presentation/bank-sampeng-v2.json', import.meta.url).href,
    stages: new URL('../../../../../fixtures/stages/bank-v2.stages.json', import.meta.url).href, stamp: 'c3a9408304a2', projectId: 'bank-sampeng', version: 2 },
  hotel: { model: new URL('../../../../../fixtures/models/hotel.model.json', import.meta.url).href, presentation: new URL('../../../../../fixtures/presentation/hotel-lobby.json', import.meta.url).href,
    pictures: { F1: new URL('../../../../../fixtures/pictures/floor1_plan.png', import.meta.url).href, F2: new URL('../../../../../fixtures/pictures/floor2_plan.png', import.meta.url).href },
    stamp: '6ab030750886', projectId: 'hotel-lobby', version: 1 },
  suite: { model: new URL('../../../../../fixtures/models/suite.model.json', import.meta.url).href, presentation: new URL('../../../../../fixtures/presentation/presidential-suite.json', import.meta.url).href,
    stamp: 'f1b95c53eb3d', projectId: 'presidential-suite', version: 1 },
  house: { model: new URL('../../../../../fixtures/models/house.model.json', import.meta.url).href, presentation: new URL('../../../../../fixtures/presentation/sukhumvit-house.json', import.meta.url).href,
    stamp: 'e43270cc0c9b', projectId: 'sukhumvit-house', version: 1 },
  features: { model: new URL('../../fixtures/features.model.json', import.meta.url).href, presentation: null,
    pictures: { G: new URL('../../../../../fixtures/pictures/floor1_plan.png', import.meta.url).href }, stamp: '0123456789ab', projectId: 'features', version: 1 },
  mini: { model: new URL('../../../../../fixtures/models/mini.model.json', import.meta.url).href, presentation: null, stamp: 'a469ffbe5a93', projectId: 'mini', version: 1 },
};
const PLAIN: Presentation = {
  documentTitle: 'Harness', heading: 'Harness model', intro: [{ text: 'A model of the viewer tests.' }], accent: '#2f6f8f',
  legend: { layout: 'inline', items: [] }, camera: { kind: 'fitSlabs', away: [21.6, 22.05, 26.1], targetY: 1.5, panForPanel: true },
};

export interface CoreHarness {
  status: 'loading' | 'ready' | 'error' | 'loaded';
  error?: string;
  key: string;
  project?: ViewerProject;
  options?: ViewerOptions;
  createViewer: typeof createViewer;
  ModelError: typeof ModelError;
  mounts?: MountApi;
}
declare global { interface Window { __core?: CoreHarness } }

const q = new URLSearchParams(location.search);
const key = q.get('project') ?? 'bank-v2';
const core: CoreHarness = { status: 'loading', key, createViewer, ModelError };
window.__core = core;

async function main(): Promise<void> {
  const fx = F[key];
  if (!fx) throw new Error(`no fixture '${key}'`);
  const get = async <T>(url: string | undefined): Promise<T | null> => (url ? (await (await fetch(url)).json()) as T : null);
  const [model, presentation, stages] = await Promise.all([get<BuiltModel>(fx.model), get<Presentation>(fx.presentation ?? undefined), get<ReplayData>(fx.stages)]);
  const project: ViewerProject = {
    model: model!, presentation: presentation ?? PLAIN, stages, pictures: fx.pictures ?? {}, heights: null, stamp: fx.stamp,
    ids: { projectId: fx.projectId, version: fx.version },
  };
  const address = parseAddressOptions(location.search);
  const options: ViewerOptions = { address, testHook: true, furnitureHeights: q.get('host') === '1' ? 'host' : 'local' };
  core.project = project;
  core.options = options;
  const app = document.getElementById('app')!;
  core.mounts = makeMountApi(app, project, options);
  window.__wtvMount = core.mounts;
  if (q.get('nomount') === '1') { core.status = 'loaded'; return; }
  const failed = core.mounts.mount();
  if (failed !== null) throw new Error(failed);
  await core.mounts.viewer!.ready;
  core.status = 'ready';
}

main().catch(err => {
  core.status = 'error';
  core.error = err instanceof Error ? `${err.name}: ${err.message}` : String(err);
});
