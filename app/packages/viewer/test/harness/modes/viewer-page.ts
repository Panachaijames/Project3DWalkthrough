// Builder B's second harness page (/modes/viewer.html): the modes inside the REAL viewer, createViewer from src/index.ts
// with every module as it is in the package now (A's context, loop, visibility, heights and test hook; C's root, panel
// and BASE_CSS; D's replay; C's furniture), mounted the way the offline page mounts it: the page's own address
// (parseAddressOptions(location.search)), furnitureHeights 'local', the test hook on, the default download (an <a download>
// click inside the root). modes.spec.ts uses it to check what only the assembly shows: the modes row in C's panel, the
// CSS under C's `all: revert`, A's modechange filter, ?cam=1 behind D's Build settings screen.
//   ?project=bank-v2 (default) | suite | house | hotel, plus any viewer address option (build=0, mode=walk, cam=1 ...)
import type { BuiltModel, Presentation, ReplayData, Viewer, ViewerEvents, ViewerProject } from '../../../src/contracts';
import { createViewer, parseAddressOptions } from '../../../src/index';

type Loader = () => Promise<{ default: unknown }>;
interface Fixture { model: Loader; presentation: Loader; stages?: Loader; pictures?: Record<string, string>; stamp: string; projectId: string }
const FIXTURES: Record<string, Fixture> = {
  'bank-v2': {
    model: () => import('../../../../../fixtures/models/bank-v2.model.json'),
    presentation: () => import('../../../../../fixtures/presentation/bank-sampeng-v2.json'),
    stages: () => import('../../../../../fixtures/stages/bank-v2.stages.json'),
    stamp: 'c3a9408304a2', projectId: 'bank-sampeng',
  },
  suite: {
    model: () => import('../../../../../fixtures/models/suite.model.json'),
    presentation: () => import('../../../../../fixtures/presentation/presidential-suite.json'),
    stamp: 'f1b95c53eb3d', projectId: 'presidential-suite',
  },
  house: {
    model: () => import('../../../../../fixtures/models/house.model.json'),
    presentation: () => import('../../../../../fixtures/presentation/sukhumvit-house.json'),
    stamp: 'e43270cc0c9b', projectId: 'sukhumvit-house',
  },
  hotel: {
    model: () => import('../../../../../fixtures/models/hotel.model.json'),
    presentation: () => import('../../../../../fixtures/presentation/hotel-lobby.json'),
    pictures: {
      F1: new URL('../../../../../fixtures/pictures/floor1_plan.png', import.meta.url).href,
      F2: new URL('../../../../../fixtures/pictures/floor2_plan.png', import.meta.url).href,
    },
    stamp: '6ab030750886', projectId: 'hotel-lobby',
  },
};

export interface ModesViewerKit {
  status: 'loading' | 'ready' | 'error';
  error?: string;
  key: string;
  viewer?: Viewer;
  /** Every public event since createViewer returned, in order. */
  events: { type: keyof ViewerEvents; payload: unknown }[];
}
declare global { interface Window { __modesViewer?: ModesViewerKit } }

const key = new URLSearchParams(location.search).get('project') ?? 'bank-v2';
const kit: ModesViewerKit = { status: 'loading', key, events: [] };
window.__modesViewer = kit;

async function main(): Promise<void> {
  const fx = FIXTURES[key];
  if (!fx) throw new Error(`no fixture '${key}'`);
  const [m, p, s] = await Promise.all([fx.model(), fx.presentation(), fx.stages ? fx.stages() : Promise.resolve(null)]);
  const project: ViewerProject = {
    model: m.default as BuiltModel, presentation: p.default as Presentation, stages: s ? (s.default as ReplayData) : null,
    pictures: fx.pictures ?? {}, heights: null, stamp: fx.stamp, ids: { projectId: fx.projectId, version: 1 },
  };
  const viewer = createViewer(document.getElementById('app')!, project, {
    address: parseAddressOptions(location.search), furnitureHeights: 'local', testHook: true,
  });
  for (const type of ['modechange', 'heightschange', 'replayphase', 'photo', 'error'] as const) {
    viewer.on(type, payload => { kit.events.push({ type, payload }); });
  }
  kit.viewer = viewer;
  await viewer.ready;
  kit.status = 'ready';
}

main().catch(err => { kit.status = 'error'; kit.error = String((err as Error)?.stack ?? err); });
