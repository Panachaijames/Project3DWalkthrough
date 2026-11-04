// Card, picker and status texts (DESIGN.md 15.2, 15.3, 17.2 "card formatting"), and the client's error mapping.
import { describe, expect, it } from 'vitest';
import { ApiError, apiUrl, isUnreachable, toApiError } from '@/api/client';
import {
  errorReason,
  formatDate,
  formatFloors,
  formatFurniture,
  formatNumber,
  formatOpenings,
  formatVersions,
  heightsNotSaved,
  HEIGHTS_SAVED,
  HEIGHTS_SAVING,
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
    expect(HEIGHTS_SAVED).toBe('Heights saved');
    expect(HEIGHTS_SAVING).toBe('Saving…');
    expect(heightsNotSaved('the API did not answer')).toBe('Not saved: the API did not answer');
    expect(NO_PROJECTS).toBe('No projects yet: run npm run seed');
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
