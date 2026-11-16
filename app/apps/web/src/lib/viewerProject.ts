// From the API's version detail + model + stages to the viewer's ViewerProject and ViewerOptions (DESIGN.md 15.3, 11.2).
// The page memoises the project on (projectId, version, stamp): a heights save that updates the cached version detail
// must not re-create the viewer (it already shows those heights). Step BX (docs/boxes/DESIGN.md 2.1, 6.2): the project
// carries the deleted furniture boxes (the unsent map of this browser, else the saved one), and only the version page's
// options switch the viewer's box editing on.
import {
  parseAddressOptions,
  parseBuiltModel,
  parsePresentation,
  parseReplayData,
  type FloorKey,
  type HeightMap,
  type PieceEditMap,
  type ViewerOptions,
  type ViewerProject,
} from '@walkthrough/viewer';
import { apiUrl } from '../api/client';
import type { AssetInfo, HeightOverrides, VersionDetail } from '../api/generated/types.gen';
import { editsOf } from './heightsOutbox';

/** The deleted boxes a project starts from: the viewer's map (the outbox) or the API's (read leniently). */
type StartEdits = PieceEditMap | HeightOverrides['pieceEdits'] | null;

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
 * v1): the page shows it instead of a viewer. `heights` / `pieceEdits`: typed or deleted earlier in this browser and
 * not saved yet (heightsOutbox.ts), else the version detail's saved ones; `pieceEdits` is set only when a box is deleted.
 */
export function toViewerProject(
  detail: VersionDetail, model: unknown, stages: unknown, heights?: HeightMap | null, pieceEdits?: StartEdits,
): ViewerProject {
  const parsedModel = parseBuiltModel(model);
  const presentation = parsePresentation(detail.presentation);
  const parsedStages = detail.hasStages && stages != null ? parseReplayData(stages, parsedModel) : null;
  const edits = editsOf(pieceEdits ?? detail.overrides.pieceEdits);
  return {
    model: parsedModel,
    presentation,
    stages: parsedStages,
    pictures: picturesByFloor(detail.assets),
    heights: { ...(heights ?? detail.overrides.heights) },   // heights typed earlier and not saved yet win (heightsOutbox.ts)
    ...(Object.keys(edits).length ? { pieceEdits: edits } : {}),
    stamp: detail.stamp,
    ids: { projectId: detail.projectId, version: detail.version },
  };
}

export type BuiltViewerProject = { ok: true; project: ViewerProject } | { ok: false; error: unknown };

/** toViewerProject without throwing. */
export function buildViewerProject(
  detail: VersionDetail, model: unknown, stages: unknown, heights?: HeightMap | null, pieceEdits?: StartEdits,
): BuiltViewerProject {
  try {
    return { ok: true, project: toViewerProject(detail, model, stages, heights, pieceEdits) };
  } catch (error) {
    return { ok: false, error };
  }
}

const TEST_HOOK = import.meta.env.VITE_WTV_TEST_HOOK === '1';

/**
 * The staff app's viewer options (DESIGN.md 15.3): the page's own address options, the finished model unless the address
 * says otherwise (build 'skip', 18.10), heights kept by the host (the API), the test hook when VITE_WTV_TEST_HOOK=1.
 * `editBoxes` (step BX): furniture boxes can be selected, deleted and restored; only the version page passes true (the
 * draft preview has no saver), and the key is there only then.
 */
export function viewerOptions(search: string, testHook: boolean = TEST_HOOK, editBoxes = false): ViewerOptions {
  const address = parseAddressOptions(search);
  return { address, build: address.build ?? 'skip', furnitureHeights: 'host', testHook, ...(editBoxes ? { editBoxes: true } : {}) };
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
