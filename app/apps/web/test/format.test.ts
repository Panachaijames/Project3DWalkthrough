// Card, picker and status texts (DESIGN.md 15.2, 15.3, 17.2 "card formatting"), and the client's error mapping.
import { describe, expect, it } from 'vitest';
import { ApiError, apiUrl, conflictOf, isUnreachable, toApiError } from '@/api/client';
import {
  boxesDeletedText,
  carriedEditsLines,
  carriedEditsText,
  EDITS_PENDING_TITLE,
  editsNotSavedTitle,
  errorReason,
  formatDate,
  formatFloors,
  formatFurniture,
  formatNumber,
  formatOpenings,
  formatVersions,
  heightsNotSaved,
  heightsNotSavedTitle,
  HEIGHTS_PENDING_TITLE,
  HEIGHTS_SAVED,
  HEIGHTS_SAVING,
  previewDeletedBoxesText,
  NO_PROJECTS,
  projectsTitle,
  sourceKindLabel,
  versionLabel,
  versionTitle,
} from '@/lib/format';

describe('dates', () => {
  it('formats as 29 Oct 2026, the day it was in the given time zone', () => {
    expect(formatDate('2026-10-29T03:24:53Z', 'UTC')).toBe('29 Oct 2026');
    expect(formatDate('2026-10-29T03:24:53Z', 'Asia/Bangkok')).toBe('29 Oct 2026');
    expect(formatDate('2026-10-28T20:00:00Z', 'Asia/Bangkok')).toBe('29 Oct 2026');
    expect(formatDate('2026-10-28T20:00:00Z', 'UTC')).toBe('28 Oct 2026');
    expect(formatDate('2026-09-03T12:00:00Z', 'UTC')).toBe('3 Sep 2026');
    expect(formatDate('2026-11-02T11:56:02Z')).toBe('2 Nov 2026');   // midday: the same day in any zone from -11 to +12
  });
  it('gives nothing for a missing or unreadable time', () => {
    expect(formatDate(null)).toBe('');
    expect(formatDate('')).toBe('');
    expect(formatDate('not a date')).toBe('');
    expect(formatDate(undefined)).toBe('');
  });
});

describe('card texts', () => {
  it('floors', () => {
    expect(formatFloors([{ name: 'Level 1' }, { name: 'Level 2' }])).toBe('2 floors: Level 1, Level 2');
    expect(formatFloors([{ name: 'Suite (FL-01)' }])).toBe('1 floor: Suite (FL-01)');
    expect(formatFloors([])).toBe('No floors');
  });
  it('counts', () => {
    expect(formatFurniture(185)).toBe('185 furniture pieces');
    expect(formatFurniture(1)).toBe('1 furniture piece');
    expect(formatFurniture(0)).toBe('No furniture');
    expect(formatFurniture(12345)).toBe('12,345 furniture pieces');
    expect(formatOpenings(49)).toBe('49 openings');
    expect(formatOpenings(1)).toBe('1 opening');
    expect(formatOpenings(0)).toBe('No openings');
    expect(formatVersions(2)).toBe('2 versions');
    expect(formatVersions(1)).toBe('1 version');
    expect(formatNumber(1234567)).toBe('1,234,567');
    expect(formatNumber(-1000)).toBe('-1,000');
    expect(formatNumber(999)).toBe('999');
  });
  it('the source badge', () => {
    expect(sourceKindLabel('cad')).toBe('CAD');
    expect(sourceKindLabel('pictures')).toBe('Pictures');
  });
});

describe('the version picker, titles and statuses', () => {
  it('v2 · 29 Oct 2026 · c3a9408304a2', () => {
    expect(versionLabel({ version: 2, createdAt: '2026-10-29T03:24:53Z', stamp: 'c3a9408304a2' }, 'UTC')).toBe('v2 · 29 Oct 2026 · c3a9408304a2');
    expect(versionLabel({ version: 1, createdAt: 'bad', stamp: '4b02dc17f286' })).toBe('v1 · 4b02dc17f286');
  });
  it('document titles', () => {
    expect(projectsTitle()).toBe('Projects · Walkthrough');
    expect(versionTitle('Bangkok Bank, Sampeng Branch', 2)).toBe('Bangkok Bank, Sampeng Branch · v2 · Walkthrough');
  });
  it('status and empty texts word for word', () => {
    expect(HEIGHTS_SAVED).toBe('Furniture saved');   // was 'Heights saved' (step BX: the status covers the deleted boxes too)
    expect(HEIGHTS_SAVING).toBe('Saving…');
    expect(heightsNotSaved('the API did not answer')).toBe('Not saved: the API did not answer');
    expect(NO_PROJECTS).toBe('No projects yet: make one with New project');   // changed on purpose (docs/upload/DESIGN.md U-14.1)
  });
});

describe('step BX: the deleted boxes', () => {
  it('the app bar count, the carried-over note and the download tooltips, word for word', () => {
    expect(boxesDeletedText(3)).toBe('· 3 boxes deleted');
    expect(boxesDeletedText(1)).toBe('· 1 box deleted');
    expect(boxesDeletedText(1234)).toBe('· 1,234 boxes deleted');
    expect(carriedEditsText(2, 2)).toBe('2 deleted boxes of v2 are back');
    expect(carriedEditsText(1, 4)).toBe('1 deleted box of v4 is back');
    expect(HEIGHTS_PENDING_TITLE).toBe('Waiting for the furniture changes (heights, deleted boxes) to be saved');
    expect(heightsNotSavedTitle('x')).toBe('The furniture changes on screen are not saved (x): the file would not carry them');
    expect(EDITS_PENDING_TITLE).toBe('Waiting for the deleted boxes to be saved');
    expect(editsNotSavedTitle('x')).toBe('The deleted boxes on screen are not saved (x): the script would still build them');
  });

  // fixes after the review (17 Nov 2026): the note names the boxes and why; the draft's preview says what a save applies
  it('the carried-over note names each box (kind, family, floor, reason): one line, or at most 5 then "and N more"', () => {
    const box = (i: number, reason = 'not found in the new drawing') =>
      ({ kind: 'Other furniture', family: `Fritz-Hansen_SH20${i}`, floor: 'Level 2', reason });
    expect(carriedEditsLines({ from: 2, notCarried: 1, boxes: [box(0)] })).toEqual([
      '1 deleted box of v2 is back: Other furniture (Fritz-Hansen_SH200) on Level 2: not found in the new drawing']);
    expect(carriedEditsLines({ from: 2, notCarried: 2, boxes: [box(0), box(1, 'its floor changed')] })).toEqual([
      '2 deleted boxes of v2 are back:',
      'Other furniture (Fritz-Hansen_SH200) on Level 2: not found in the new drawing',
      'Other furniture (Fritz-Hansen_SH201) on Level 2: its floor changed']);
    const seven = Array.from({ length: 7 }, (_, i) => box(i));
    expect(carriedEditsLines({ from: 3, notCarried: 7, boxes: seven })).toEqual([
      '7 deleted boxes of v3 are back:', ...seven.slice(0, 5).map(b => `Other furniture (${b.family}) on Level 2: not found in the new drawing`),
      'and 2 more']);
    expect(carriedEditsLines({ from: 3, notCarried: 2 })).toEqual(['2 deleted boxes of v3 are back']);   // no list
    expect(carriedEditsLines({ from: 3, notCarried: 1, boxes: [{ ...box(0), family: '' }] })).toEqual([
      '1 deleted box of v3 is back: Other furniture on Level 2: not found in the new drawing']);
    expect(previewDeletedBoxesText(3, 2)).toBe("v2's 3 deleted boxes are applied when you save, where the same box is in the same place.");
    expect(previewDeletedBoxesText(1, 4)).toBe("v4's 1 deleted box is applied when you save, where the same box is in the same place.");
  });
});

describe('errors', () => {
  const res = (status: number, statusText = '') => new Response(null, { status, statusText });
  it("the API's ErrorResponse body", () => {
    const e = toApiError({ error: { code: 'project_not_found', message: 'There is no project x.', details: { id: 'x' } } }, res(404));
    expect(e).toBeInstanceOf(ApiError);
    expect([e.status, e.code, e.message, e.details]).toEqual([404, 'project_not_found', 'There is no project x.', { id: 'x' }]);
  });
  it("FastAPI's 422, other answers and no answer", () => {
    const v = toApiError({ detail: [{ loc: ['path', 'version'], msg: 'Input should be greater than or equal to 1', type: 'x' }] }, res(422));
    expect([v.status, v.code, v.message]).toEqual([422, 'validation_error', 'Input should be greater than or equal to 1']);
    const t = toApiError('Internal Server Error', res(500));
    expect([t.status, t.code, t.message]).toEqual([500, 'http_500', 'Internal Server Error']);
    // the dev / preview proxy's empty 502 / 504 (and a bare 503) when the API is not running: "did not answer" (fix step)
    for (const status of [502, 503, 504]) {
      const empty = toApiError(status === 503 ? '' : {}, res(status, 'Bad Gateway'));
      expect([empty.status, empty.code, empty.message], String(status)).toEqual([status, 'network_error', 'the API did not answer (is it running?)']);
      expect(isUnreachable(empty)).toBe(true);
    }
    const busy = toApiError({ error: { code: 'offline_template_missing', message: 'run npm run build:offline:template' } }, res(503));
    expect([busy.code, isUnreachable(busy)]).toEqual(['offline_template_missing', false]);   // the API's own 503 stays its own
    const other = toApiError({}, res(501, 'Not Implemented'));
    expect([other.code, other.message]).toEqual(['http_501', 'Not Implemented']);
    const n = toApiError(new TypeError('Failed to fetch'), undefined);
    expect([n.status, n.code, n.message]).toEqual([0, 'network_error', 'the API did not answer (is it running?)']);
    const same = new ApiError(418, 'teapot', 'short and stout');
    expect(toApiError(same, res(500))).toBe(same);
  });
  it('step BX: conflictOf reads the deleted boxes of a 412 leniently (missing: none); other errors are no conflict', () => {
    const c = (details: Record<string, unknown>) => new ApiError(412, 'revision_conflict', 'changed elsewhere', details);
    expect(conflictOf(c({ revision: 3, heights: { table: 600 }, updatedAt: null }))).toEqual({ revision: 3, heights: { table: 600 }, pieceEdits: {} });
    expect(conflictOf(c({ revision: 4, heights: {}, updatedAt: null, pieceEdits: { a: { removed: true }, b: { removed: 'yes' }, c: 1 } })))
      .toEqual({ revision: 4, heights: {}, pieceEdits: { a: { removed: true } } });
    expect(conflictOf(new ApiError(422, 'invalid_piece_edits', 'not a furniture piece of the model: q', { unknownIds: ['q'], count: 1 }))).toBeNull();
  });
  it('a reason for any error', () => {
    expect(errorReason(new ApiError(422, 'invalid_heights', 'bad kinds'))).toBe('bad kinds');
    expect(errorReason({ error: { message: 'from a body' } })).toBe('from a body');
    expect(errorReason('plain')).toBe('plain');
    expect(errorReason(null)).toBe('unknown error');
    expect(errorReason({})).toBe('unknown error');
  });
  it('apiUrl keeps root-relative URLs on this origin and absolute ones as they are', () => {
    expect(apiUrl('/api/projects/x/thumbnail')).toBe('/api/projects/x/thumbnail');
    expect(apiUrl('https://example.test/a.png')).toBe('https://example.test/a.png');
    expect(apiUrl('data:image/png;base64,AA==')).toBe('data:image/png;base64,AA==');
  });
});
