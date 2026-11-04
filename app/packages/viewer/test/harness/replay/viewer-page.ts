// Replay harness page on the REAL viewer (builder D): createViewer, A's assembly with B's modes, C's root, panel and
// furniture and this replay, on a fixture model with its fixtures/presentation/*.json, the test hook on and the page's own
// address (as the offline file does), so the replay is checked with everything it works with before the integration step
// runs the e2e specs on the offline files. Served by `npm run harness -- --port 5724`:
//   /replay/viewer.html?project=bank-v2|bank-v1|suite|house[&build=play&speed=quick&cam=1 ...]
// The banks use their stages fixtures; the suite and the house have none before E's seed (DESIGN.md 17.1), so they get
// synthetic replay data made from their own parts (synthetic.ts stagesFor). window.__replayViewer says how it went.
import type { BuiltModel, Presentation, ReplayData, ViewerProject } from '../../../src/contracts';
import { createViewer, parseAddressOptions } from '../../../src/index';
import bankV1 from '../../../../../fixtures/models/bank-v1.model.json';
import bankV2 from '../../../../../fixtures/models/bank-v2.model.json';
import house from '../../../../../fixtures/models/house.model.json';
import suite from '../../../../../fixtures/models/suite.model.json';
import bankV1Pres from '../../../../../fixtures/presentation/bank-sampeng-v1.json';
import bankV2Pres from '../../../../../fixtures/presentation/bank-sampeng-v2.json';
import suitePres from '../../../../../fixtures/presentation/presidential-suite.json';
import housePres from '../../../../../fixtures/presentation/sukhumvit-house.json';
import bankV1Stages from '../../../../../fixtures/stages/bank-v1.stages.json';
import bankV2Stages from '../../../../../fixtures/stages/bank-v2.stages.json';
import { stagesFor } from './synthetic';

export interface ReplayViewerHarness { status: 'loading' | 'ready' | 'error'; project: string; error?: string }
declare global { interface Window { __replayViewer?: ReplayViewerHarness } }

const m = <T>(x: unknown) => x as T;
const SETS: Record<string, () => { model: BuiltModel; presentation: Presentation; stages: ReplayData; stamp: string; projectId: string; version: number }> = {
  'bank-v1': () => ({ model: m(bankV1), presentation: m(bankV1Pres), stages: m(bankV1Stages), stamp: '4b02dc17f286', projectId: 'bank-sampeng', version: 1 }),
  'bank-v2': () => ({ model: m(bankV2), presentation: m(bankV2Pres), stages: m(bankV2Stages), stamp: 'c3a9408304a2', projectId: 'bank-sampeng', version: 2 }),
  suite: () => ({ model: m(suite), presentation: m(suitePres), stages: stagesFor(m(suite)), stamp: 'f1b95c53eb3d', projectId: 'presidential-suite', version: 1 }),
  house: () => ({ model: m(house), presentation: m(housePres), stages: stagesFor(m(house)), stamp: 'e43270cc0c9b', projectId: 'sukhumvit-house', version: 1 }),
};

const key = new URLSearchParams(location.search).get('project') ?? 'bank-v2';
const state: ReplayViewerHarness = { status: 'loading', project: key };
window.__replayViewer = state;

async function main(): Promise<void> {
  const set = SETS[key];
  if (!set) throw new Error(`no project '${key}'`);
  const s = set();
  // the heights of an earlier run stay in this browser profile under the stamped key: start from the model's
  try { for (const k of Object.keys(localStorage)) if (k.startsWith('walkthrough-furniture')) localStorage.removeItem(k); } catch { /* blocked */ }
  const project: ViewerProject = {
    model: s.model, presentation: s.presentation, stages: s.stages, pictures: {}, heights: null, stamp: s.stamp,
    ids: { projectId: s.projectId, version: s.version },
  };
  document.title = s.presentation.documentTitle;
  const address = parseAddressOptions(location.search);
  const viewer = createViewer(document.getElementById('app')!, project, { address, furnitureHeights: 'local', testHook: true });
  await viewer.ready;
  state.status = 'ready';
}

main().catch(err => {
  state.status = 'error';
  state.error = err instanceof Error ? `${err.name}: ${err.message}\n${err.stack ?? ''}` : String(err);
});
