// The 3D preview of a draft (docs/upload/DESIGN.md U-12.5, U-14.4): toViewerProject's sibling taking a BuildDetail and the
// draft's fetched model and stages. Stamp = result.stamp, presentation from result.presentation, no pictures, no saved
// heights, ids { projectId, version: 0 }. Options: the finished model ('skip'), heights kept by the host with no saver
// attached (a height typed in a preview is not saved).
import {
  parseBuiltModel,
  parsePresentation,
  parseReplayData,
  type ViewerOptions,
  type ViewerProject,
} from '@walkthrough/viewer';
import type { BuildDetail } from '@/upload/contracts';

/** Throws what the viewer's parsers throw, or an Error when the draft has no build yet. */
export function toDraftViewerProject(detail: BuildDetail, model: unknown, stages: unknown): ViewerProject {
  const result = detail.result;
  if (!result) throw new Error('This draft has not been built yet.');
  const parsedModel = parseBuiltModel(model);
  return {
    model: parsedModel,
    presentation: parsePresentation(result.presentation),
    stages: stages != null ? parseReplayData(stages, parsedModel) : null,
    pictures: {},
    heights: {},
    stamp: result.stamp,
    ids: { projectId: detail.projectId, version: 0 },
  };
}

const TEST_HOOK = import.meta.env.VITE_WTV_TEST_HOOK === '1';

/** The preview's options (U-12.5): the finished model, heights by the host (none saved). */
export function draftViewerOptions(testHook: boolean = TEST_HOOK): ViewerOptions {
  return { build: 'skip', furnitureHeights: 'host', testHook };
}
