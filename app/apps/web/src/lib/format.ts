// Texts of the staff app's cards, version picker and statuses (DESIGN.md 15.2, 15.3, 15.5). Pure functions: no DOM, no
// React, no `@/` imports, so the Playwright specs import them too and compare the page with the API's own JSON.

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

/** 1234 -> '1,234' (fixed, whatever the browser's locale). */
export function formatNumber(n: number): string {
  const s = String(Math.trunc(Math.abs(n)));
  const grouped = s.replace(/\B(?=(\d{3})+(?!\d))/g, ',');
  return n < 0 ? `-${grouped}` : grouped;
}

/** '29 Oct 2026' for an ISO 8601 time, as the day it was in `timeZone` (default: this computer's). '' when unreadable. */
export function formatDate(iso: string | null | undefined, timeZone?: string): string {
  if (!iso) return '';
  const t = Date.parse(iso);
  if (Number.isNaN(t)) return '';
  const parts = new Intl.DateTimeFormat('en-US', { timeZone, year: 'numeric', month: 'numeric', day: 'numeric' })
    .formatToParts(new Date(t));
  const get = (type: string) => Number(parts.find(p => p.type === type)?.value);
  const month = MONTHS[get('month') - 1];
  return month ? `${get('day')} ${month} ${get('year')}` : '';
}

/** '185 furniture pieces', '1 furniture piece'; `none` when zero (default: '0 <plural>'). */
export function plural(n: number, one: string, many: string, none?: string): string {
  if (n === 0 && none !== undefined) return none;
  return `${formatNumber(n)} ${n === 1 ? one : many}`;
}

/** '2 floors: Level 1, Level 2', '1 floor: Suite (FL-01)', 'No floors'. */
export function formatFloors(floors: readonly { name: string }[]): string {
  if (!floors.length) return 'No floors';
  return `${plural(floors.length, 'floor', 'floors')}: ${floors.map(f => f.name).join(', ')}`;
}

export const formatFurniture = (n: number) => plural(n, 'furniture piece', 'furniture pieces', 'No furniture');
export const formatOpenings = (n: number) => plural(n, 'opening', 'openings', 'No openings');
export const formatVersions = (n: number) => plural(n, 'version', 'versions');

/** The badge of a project's source: 'CAD' or 'Pictures'. */
export function sourceKindLabel(kind: 'cad' | 'pictures'): string {
  return kind === 'pictures' ? 'Pictures' : 'CAD';
}

/** The version picker's text: 'v2 · 29 Oct 2026 · c3a9408304a2'. */
export function versionLabel(v: { version: number; createdAt: string; stamp: string }, timeZone?: string): string {
  return [`v${v.version}`, formatDate(v.createdAt, timeZone), v.stamp].filter(Boolean).join(' · ');
}

/** Document titles (DESIGN.md 15.1). */
export const APP_NAME = 'Walkthrough';
export const projectsTitle = () => `Projects · ${APP_NAME}`;
export const versionTitle = (name: string, version: number) => `${name} · v${version} · ${APP_NAME}`;
export const notFoundTitle = () => `Not found · ${APP_NAME}`;
export const errorTitle = () => `Error · ${APP_NAME}`;

/**
 * The furniture status line (DESIGN.md 15.3). Step BX (docs/boxes/DESIGN.md 6.2): 'Heights saved' became
 * 'Furniture saved', the status covering the deleted boxes too (the constant keeps its name).
 */
export const HEIGHTS_SAVED = 'Furniture saved';
export const HEIGHTS_SAVING = 'Saving…';
export const heightsNotSaved = (reason: string) => `Not saved: ${reason}`;

/** The app bar's count of the deleted furniture boxes (step BX), beside the status: '· 3 boxes deleted'. */
export const boxesDeletedText = (n: number) => `· ${plural(n, 'box deleted', 'boxes deleted')}`;
/** Its tooltip. */
export const boxesDeletedTitle = (n: number) =>
  `${plural(n, 'furniture box is', 'furniture boxes are')} deleted in this version: the furniture legend's Restore… brings them back`;

/**
 * The new version's note when deleted boxes of the version it was carried from did not carry over (step BX, the main
 * session's decision 2; VersionDetail.carriedEdits): '2 deleted boxes of v2 are back: not found in the new drawing'.
 */
export const carriedEditsText = (notCarried: number, from: number) =>
  `${plural(notCarried, 'deleted box', 'deleted boxes')} of v${from} ${notCarried === 1 ? 'is' : 'are'} back: not found in the new drawing`;

/**
 * The tooltip of the CSV and offline downloads while a save is going (they carry the saved heights and deleted boxes).
 * Step BX: the furniture changes, heights and deleted boxes alike (the constants keep their names).
 */
export const HEIGHTS_PENDING_TITLE = 'Waiting for the furniture changes (heights, deleted boxes) to be saved';
/** ... and while the changes on screen are not saved: the file would carry other furniture than the viewer shows. */
export const heightsNotSavedTitle = (reason: string) =>
  `The furniture changes on screen are not saved (${reason}): the file would not carry them`;
/** The 3ds Max script's tooltip while deleted boxes are being saved (it carries no saved heights: only these wait). */
export const EDITS_PENDING_TITLE = 'Waiting for the deleted boxes to be saved';
/** ... and while the deleted boxes on screen are not saved: the script would still build them. */
export const editsNotSavedTitle = (reason: string) =>
  `The deleted boxes on screen are not saved (${reason}): the script would still build them`;
/** The tooltip of every download while the API does not answer. */
export const API_DOWN_TITLE = 'The API is not answering (is it running?): nothing can be downloaded now';

/** The Downloads menu's items (DESIGN.md 15.3), in order. */
export const DOWNLOAD_ITEMS = [
  { key: 'maxScript', text: '3ds Max script (.ms)' },
  { key: 'furnitureCsv', text: 'Furniture list (CSV)' },
  { key: 'offlineHtml', text: 'Offline viewer (HTML)' },
] as const;

/** The empty project list (DESIGN.md 15.2; docs/upload/DESIGN.md U-14.1 changed it: projects are made in the app now). */
export const NO_PROJECTS = 'No projects yet: make one with New project';

/** A short reason for an error, for 'Not saved: <reason>' and the error alerts. */
export function errorReason(err: unknown): string {
  if (err instanceof Error && err.message) return err.message;
  if (typeof err === 'string' && err) return err;
  if (err && typeof err === 'object') {
    const e = err as { error?: { message?: unknown }; message?: unknown };
    if (e.error && typeof e.error.message === 'string' && e.error.message) return e.error.message;
    if (typeof e.message === 'string' && e.message) return e.message;
  }
  return 'unknown error';
}

/** A project with no version yet (its card, its page). */
export const NO_VERSIONS = 'No versions yet';

/** A draft's run status in the drafts lists (docs/upload/DESIGN.md U-14.1). */
export function draftStatusText(status: string | null): string {
  switch (status) {
    case null: return 'not started';
    case 'queued': return 'waiting to run';
    case 'running': return 'running';
    case 'done': return 'ready';
    case 'failed': return 'failed';
    case 'cancelled': return 'cancelled';
    case 'interrupted': return 'interrupted';
    default: return status;
  }
}
