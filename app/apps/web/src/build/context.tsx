// What the Build page's six steps share (docs/upload/DESIGN.md U-2 screen 5, U-14.2): the merged BuildDetail (useBuild),
// the settings as this tab has them (the saver's), the change function, the project, and the raw files of each source
// (conversion report, drawing read, decoded plan geometry) fetched once by the URLs the API gave.
import { useQuery, type UseQueryResult } from '@tanstack/react-query';
import { createContext, useContext, useMemo } from 'react';
import type { ProjectDetail } from '@/api/generated/types.gen';
import { decodePlan, type DecodedPlan } from '@/plan';
import type { BuildDetail, BuildSettings, BuildSourceInfo, ConversionReport, DrawingRead, PlanGeometry } from '@/upload/contracts';
import { rawQueryOptions } from '@/upload/raw';
import type { SettingsChange, SettingsSaver, SettingsSaverState } from '@/upload/settingsSaver';
import type { StepId } from './steps';
import { rereadText } from './steps';

export interface BuildContextValue {
  projectId: string;
  buildId: string;
  detail: BuildDetail;
  project: ProjectDetail | null;
  /** The settings on screen (the saver's when it exists, else the detail's); null before the proposal. */
  settings: BuildSettings | null;
  saver: SettingsSaver | null;
  saverState: SettingsSaverState | null;
  /** Saves a change (debounced). A no-op while the settings cannot be saved (`editable` false). */
  change: (fn: SettingsChange, opts?: { layersReviewed?: boolean }) => void;
  /** The settings can be changed now: the proposal is in, the build is open, no source is being read again. */
  editable: boolean;
  /** Puts an answer of the API (runBuild, cancel ...) into the caches. */
  setDetail: (d: BuildDetail) => void;
  /** Reads the build again (a run another tab started: UR, V2-14). */
  refresh: () => void;
  goto: (step: StepId) => void;
}

const Ctx = createContext<BuildContextValue | null>(null);
export const BuildContextProvider = Ctx.Provider;

export function useBuildContext(): BuildContextValue {
  const v = useContext(Ctx);
  if (!v) throw new Error('useBuildContext outside the Build page');
  return v;
}

/** The token a source's raw files are keyed by: they change only when the source is read again (other units). */
export const sourceToken = (src: BuildSourceInfo) => `${src.units?.used ?? ''}:${src.conversion?.verdict ?? ''}`;

export function useConversion(src: BuildSourceInfo | undefined): UseQueryResult<ConversionReport> {
  return useQuery(rawQueryOptions<ConversionReport>(src?.urls?.conversion, src ? sourceToken(src) : ''));
}

export function useDrawing(src: BuildSourceInfo | undefined): UseQueryResult<DrawingRead> {
  return useQuery(rawQueryOptions<DrawingRead>(src?.urls?.drawing, src ? sourceToken(src) : ''));
}

export interface PlanState { plan: DecodedPlan | null; loading: boolean; error: unknown }

/** A source's plan geometry, decoded once (U-7.5, U-12.1): the decoded plan is the same object for as long as the
 *  plan's file is (its query keeps one answer per URL and source token). UR, V2-3: it was decoded again whenever the page
 *  got a new BuildDetail (every settings save gives a new `urls` object), and the canvas took that as a new plan and
 *  fitted it, throwing away the staff member's zoom after every Set aside, Restore or fix. */
export function usePlan(src: BuildSourceInfo | undefined): PlanState {
  const q = useQuery(rawQueryOptions<PlanGeometry>(src?.urls?.plan, src ? sourceToken(src) : ''));
  const hasUrls = !!src?.urls;
  const decoded = useMemo<{ plan: DecodedPlan | null; error: unknown }>(() => {
    if (!q.data) return { plan: null, error: null };
    try {
      return { plan: decodePlan(q.data), error: null };
    } catch (err) {
      return { plan: null, error: err };
    }
  }, [q.data]);
  return useMemo<PlanState>(() => (q.data
    ? { plan: decoded.plan, loading: false, error: decoded.error }
    : { plan: null, loading: q.isPending && hasUrls, error: q.error }), [q.data, decoded, q.isPending, q.error, hasUrls]);
}

/** The text that locks the Floors and Check steps while a source is read again (U-7.4), or null. */
export function useLockText(): string | null {
  const { detail, settings } = useBuildContext();
  return rereadText(detail, settings);
}
