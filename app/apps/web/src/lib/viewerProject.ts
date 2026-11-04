// From the API's version detail + model + stages to the viewer's ViewerProject and ViewerOptions (DESIGN.md 15.3, 11.2).
// The page memoises the project on (projectId, version, stamp): a heights save that updates the cached version detail
// must not re-create the viewer (it already shows those heights).
import {
  parseAddressOptions,
  parseBuiltModel,
  parsePresentation,
  parseReplayData,
  type FloorKey,
  type HeightMap,
  type ViewerOptions,
  type ViewerProject,
} from '@walkthrough/viewer';
import { apiUrl } from '../api/client';
import type { AssetInfo, VersionDetail } from '../api/generated/types.gen';

/** Plan-picture assets by floor -> their URLs (the viewer loads each as its floor's sheet; DESIGN.md 5.7). */
export function picturesByFloor(assets: readonly AssetInfo[]): Partial<Record<FloorKey, string>> {
  const out: Partial<Record<FloorKey, string>> = {};
  for (const a of assets) {
    if (a.role === 'plan-picture' && a.floor && !(a.floor in out)) out[a.floor] = apiUrl(a.url);
  }
  return out;
}

/**
 * The ViewerProject of a version. Throws what the viewer's parsers throw (ModelError for a model that is not BuiltModel
 * v1): the page shows it instead of a viewer.
 */
export function toViewerProject(detail: VersionDetail, model: unknown, stages: unknown, heights?: HeightMap | null): ViewerProject {
  const parsedModel = parseBuiltModel(model);
  const presentation = parsePresentation(detail.presentation);
  const parsedStages = detail.hasStages && stages != null ? parseReplayData(stages, parsedModel) : null;
  return {
    model: parsedModel,
    presentation,
    stages: parsedStages,
    pictures: picturesByFloor(detail.assets),
    heights: { ...(heights ?? detail.overrides.heights) },   // heights typed earlier and not saved yet win (heightsOutbox.ts)
    stamp: detail.stamp,
    ids: { projectId: detail.projectId, version: detail.version },
  };
}

export type BuiltViewerProject = { ok: true; project: ViewerProject } | { ok: false; error: unknown };

/** toViewerProject without throwing. */
export function buildViewerProject(detail: VersionDetail, model: unknown, stages: unknown, heights?: HeightMap | null): BuiltViewerProject {
  try {
    return { ok: true, project: toViewerProject(detail, model, stages, heights) };
  } catch (error) {
    return { ok: false, error };
  }
}

const TEST_HOOK = import.meta.env.VITE_WTV_TEST_HOOK === '1';

/**
 * The staff app's viewer options (DESIGN.md 15.3): the page's own address options, the finished model unless the address
 * says otherwise (build 'skip', 18.10), heights kept by the host (the API), the test hook when VITE_WTV_TEST_HOOK=1.
 */
export function viewerOptions(search: string, testHook: boolean = TEST_HOOK): ViewerOptions {
  const address = parseAddressOptions(search);
  return { address, build: address.build ?? 'skip', furnitureHeights: 'host', testHook };
}

/** Lines of a parse failure for the page ('/parts/12/z1: must be a number'), at most `max`. */
export function issueLines(err: unknown, max = 5): string[] {
  const issues = (err as { issues?: unknown } | null)?.issues;
  if (!Array.isArray(issues)) return [];
  const lines = issues.slice(0, max).map(i => {
    const it = i as { path?: unknown; message?: unknown };
    return `${typeof it.path === 'string' && it.path ? it.path : '/'}: ${typeof it.message === 'string' ? it.message : 'invalid'}`;
  });
  if (issues.length > max) lines.push(`… and ${issues.length - max} more`);
  return lines;
}
