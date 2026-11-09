// The Build page's six steps (docs/upload/DESIGN.md U-2 screen 5, U-14.3): which are reachable, and the pre-build
// checklist. Pure functions of the BuildDetail and the settings on screen.
import type { BuildDetail, BuildSettings, RunInfo, Units } from '@/upload/contracts';
import { floorIssues, furnitureIssues, namingIssues, UNIT_NAMES, UNITS } from './settingsEdit';

export const STEPS = ['files', 'layers', 'floors', 'build', 'check', 'save'] as const;
export type StepId = (typeof STEPS)[number];
export const STEP_LABELS: Record<StepId, string> = {
  files: 'Files', layers: 'Layers', floors: 'Floors', build: 'Build', check: 'Check', save: 'Save',
};
export const isStep = (v: string | null | undefined): v is StepId => !!v && (STEPS as readonly string[]).includes(v);

/** The proposal is in (revision >= 1, U-3.3): the settings can be saved. */
export const proposalIn = (d: Pick<BuildDetail, 'settingsRevision'>) => d.settingsRevision >= 1;

/** A prepare run going now: the first reading, or a one-source re-read after a units change (U-7.4). */
export function readingNow(run: RunInfo | null | undefined): RunInfo | null {
  return run && run.kind === 'prepare' && (run.status === 'queued' || run.status === 'running') ? run : null;
}

/** Any run going now (the units select and other settings that start a run wait for it: UR, V2-11). */
export const runGoing = (run: RunInfo | null | undefined): boolean => run?.status === 'queued' || run?.status === 'running';

/** The draft's first reading ended without a proposal (failed, cancelled or interrupted): "Read the drawings again"
 *  (runBuild then reads them again, UR V3-4) or delete the draft. */
export function firstReadingEnded(d: Pick<BuildDetail, 'run' | 'settingsRevision' | 'status'>): boolean {
  const r = d.run;
  return d.status === 'open' && d.settingsRevision === 0 && !!r && r.kind === 'prepare' && !r.only
    && (r.status === 'failed' || r.status === 'cancelled' || r.status === 'interrupted');
}

/** The units chosen for a source against its door votes (U-7.4): a warning when the chosen units have no door votes
 *  while another unit has at least 3 (metres on a millimetre drawing showed 'agree' and 'Confirmed': UR, V2-11). */
export function unitsAgainstVotes(chosen: Units | null | undefined, votes: Partial<Record<Units, number>> | null | undefined): string | null {
  if (!chosen || !votes) return null;
  let best: Units | null = null;
  for (const u of UNITS) if ((votes[u] ?? 0) > (best ? votes[best] ?? 0 : 0)) best = u;
  if (!best || best === chosen || (votes[best] ?? 0) < 3 || (votes[chosen] ?? 0) > 0) return null;
  return `its door symbols measure right in ${UNIT_NAMES[best]} (${votes[best]} doors), none in ${UNIT_NAMES[chosen]}: check the units`;
}

/** A step is reachable once its inputs exist (U-2 screen 5). */
export function reachable(step: StepId, d: BuildDetail): boolean {
  switch (step) {
    case 'files': return true;
    case 'layers':
    case 'floors':
    case 'build': return proposalIn(d);
    case 'check':
    case 'save': return d.result !== null;
  }
}

/** "Reading <file> again in <units>..." while a one-source prepare runs (U-7.4), else null. */
export function rereadText(d: BuildDetail, settings: BuildSettings | null): string | null {
  const run = readingNow(d.run);
  if (!run || !run.only || !run.only.length) return null;
  const names = run.only.map(sha1 => {
    const src = settings?.sources.find(s => s.sha1 === sha1);
    const name = src?.name ?? d.sources.find(s => s.sha1 === sha1)?.name ?? sha1.slice(0, 12);
    return src?.units ? `${name} again in ${UNIT_NAMES[src.units]}` : `${name} again`;
  });
  return `Reading ${names.join(', ')}...`;
}

export interface ChecklistItem {
  id: string;
  /** The step that fixes it. */
  step: StepId;
  text: string;
  /** 'block': Build stays disabled; 'warn': said, never blocks (a conversion loss, U-3.4). */
  level: 'block' | 'warn';
}

export const LOSS_WARNING = 'parts of the drawing were lost in conversion; export a DXF from AutoCAD for a complete build';

/** The pre-build checklist (U-14.3), each line naming the step that fixes it. `votes`: each source's door votes (its
 *  drawing read), for the units warning. */
export function checklist(d: BuildDetail, s: BuildSettings | null,
  opts: { reviewPending?: boolean; votes?: Record<string, Partial<Record<Units, number>> | undefined> } = {}): ChecklistItem[] {
  const out: ChecklistItem[] = [];
  if (!proposalIn(d) || !s) {
    out.push({ id: 'reading', step: 'files', text: 'Reading the drawings...', level: 'block' });
    return out;
  }
  const reread = rereadText(d, s);
  if (reread) out.push({ id: 'reread', step: 'files', text: reread, level: 'block' });
  for (const src of s.sources) {
    if (!src.unitsConfirmed) out.push({ id: `units:${src.sha1}`, step: 'files', text: `Confirm the units of ${src.name}`, level: 'block' });
    const against = unitsAgainstVotes(src.units, opts.votes?.[src.sha1]);
    if (against) out.push({ id: `units-votes:${src.sha1}`, step: 'files', text: `${src.name}: ${against}`, level: 'warn' });
  }
  if (!d.layersReviewedAt && !opts.reviewPending) {
    out.push({ id: 'layers', step: 'layers', text: 'Look through the Layers step once (nothing is built before)', level: 'block' });
  }
  if (!s.floors.length) out.push({ id: 'floors', step: 'floors', text: 'Add a floor', level: 'block' });
  const sources = new Set(s.sources.map(x => x.sha1));
  s.floors.forEach((f, i) => {
    const name = f.name || f.key;
    if (!(f.wallHeight > 0)) out.push({ id: `height:${i}`, step: 'floors', text: `${name} has no wall height`, level: 'block' });
    if (!sources.has(f.source)) out.push({ id: `source:${i}`, step: 'floors', text: `${name} has no source file`, level: 'block' });
    if (f.area.kind === 'box') {
      const [x0, y0, x1, y1] = f.area.bbox;
      if (!(x0 < x1 && y0 < y1)) out.push({ id: `area:${i}`, step: 'floors', text: `${name}'s area is empty`, level: 'block' });
    }
  });
  const seen = new Set(out.map(i => i.text));
  for (const issue of [...floorIssues(s), ...namingIssues(s), ...furnitureIssues(s)]) {
    if (seen.has(issue.message)) continue;
    seen.add(issue.message);
    out.push({ id: `issue:${issue.path}`, step: 'floors', text: issue.message, level: 'block' });
  }
  for (const src of d.sources) {
    if (src.conversion?.verdict === 'loss') out.push({ id: `loss:${src.sha1}`, step: 'files', text: `${src.name}: ${LOSS_WARNING}`, level: 'warn' });
    if (src.conversion?.verdict === 'failed') out.push({ id: `failed:${src.sha1}`, step: 'files', text: `${src.name} could not be converted`, level: 'block' });
  }
  return out;
}

/** What to change after a failed run (RunErrorCode, U-3.4 / contracts section 3), in a plain sentence. A reading run
 *  (prepare) that stopped is read again from the Files step, not built (UR, V3-4). */
export function errorAdvice(code: string, kind: RunInfo['kind'] = 'build'): string {
  if (kind === 'prepare') {
    switch (code) {
      case 'cancelled': return 'The reading was cancelled: read the drawings again, or delete this draft.';
      case 'interrupted': return 'The reading stopped (the API or the computer restarted): read the drawings again.';
      case 'invalid_output':
      case 'internal': return 'Read the drawings again; if it fails again, report it with the message above.';
      default: break;
    }
  }
  switch (code) {
    case 'not_a_drawing':
    case 'unsupported_version': return 'Save the drawing as a newer DWG, or export a DXF, and start again with that file.';
    case 'convert_failed':
    case 'convert_timeout':
    case 'convert_memory':
    case 'check_failed': return 'The converter could not read this DWG: export a DXF from AutoCAD and start again with it.';
    case 'read_failed':
    case 'read_timeout':
    case 'read_memory': return 'The drawing could not be read: check it opens in AutoCAD, or export a smaller DXF.';
    case 'no_floors': return 'Add a floor on the Floors step.';
    case 'bad_settings': return 'Check the Floors step: a value is out of range.';
    case 'area_empty': return 'A floor has no walls in its area: check its area on the Floors step, or the wall layers on the Layers step.';
    case 'align_failed': return 'Pick grid or two points for the alignment on the Floors step.';
    case 'detect_failed':
    case 'build_failed':
    case 'build_timeout':
    case 'build_memory': return 'Check the Layers step (a hatch or symbol layer set to walls can do this), then build again.';
    case 'invalid_output': return 'The build made a model that did not pass its checks: build again, and report it if it happens again.';
    case 'cancelled': return 'The run was cancelled: build again when ready.';
    case 'interrupted': return 'The run stopped (the API or the computer restarted): build again.';
    default: return 'Build again; if it fails again, report it with the message above.';
  }
}
