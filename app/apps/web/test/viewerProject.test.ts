// Building the ViewerProject and the options (DESIGN.md 15.3): parse* on the API's JSON, pictures by floor -> asset URLs,
// heights = the saved overrides, stamp, ids; options from the address with build 'skip', furnitureHeights 'host'.
import { describe, expect, it, vi } from 'vitest';
import { buildViewerProject, issueLines, picturesByFloor, toViewerProject, viewerOptions } from '@/lib/viewerProject';
import { createMockApi } from './mock-api/core';
import { readJson } from './mock-api/fixtures';

vi.mock('@walkthrough/viewer', async () => vi.importActual('./fake-viewer'));

const mock = createMockApi();

describe('toViewerProject', () => {
  it('the hotel: pictures by floor, no stages, heights from the saved overrides', () => {
    mock.setSaved('hotel-lobby', 1, { table: 600 });
    const detail = mock.version('hotel-lobby', 1)!;
    const model = readJson(mock.source('hotel-lobby', 1)!.model);
    const p = toViewerProject(detail, model, null);
    expect(p.model).toBe(model);
    expect(p.presentation).toEqual(detail.presentation);
    expect(p.stages).toBeNull();
    expect(p.pictures).toEqual({
      F1: '/api/projects/hotel-lobby/versions/1/assets/floor1_plan.png',
      F2: '/api/projects/hotel-lobby/versions/1/assets/floor2_plan.png',
    });
    expect(p.heights).toEqual({ table: 600 });
    expect(p.heights).not.toBe(detail.overrides.heights);
    expect(p.stamp).toBe('6ab030750886');
    expect(p.ids).toEqual({ projectId: 'hotel-lobby', version: 1 });
  });

  it('the bank v2: stages when the version has them, no pictures (the thumbnail is not a plan picture)', () => {
    const detail = mock.version('bank-sampeng', 2)!;
    const src = mock.source('bank-sampeng', 2)!;
    const stages = readJson(src.stages!);
    const p = toViewerProject(detail, readJson(src.model), stages);
    expect(p.stages).toBe(stages);
    expect(p.pictures).toEqual({});
    expect(p.heights).toEqual({});
    expect(p.stamp).toBe('c3a9408304a2');
    // stages are ignored when the version says it has none
    expect(toViewerProject({ ...detail, hasStages: false }, readJson(src.model), stages).stages).toBeNull();
  });

  it('a model that does not parse: buildViewerProject reports the ModelError', () => {
    const detail = mock.version('bank-sampeng', 1)!;
    const built = buildViewerProject(detail, [1, 2, 3], null);
    expect(built.ok).toBe(false);
    if (built.ok) return;
    expect((built.error as Error).name).toBe('ModelError');
    expect(issueLines(built.error)).toEqual(['/: must be an object']);
  });

  it('the first plan picture of a floor wins; thumbnails are not pictures', () => {
    expect(picturesByFloor([
      { name: 'a.png', role: 'plan-picture', floor: 'F1', mediaType: 'image/png', bytes: 1, sha1: 'x', url: '/api/a.png' },
      { name: 'b.png', role: 'plan-picture', floor: 'F1', mediaType: 'image/png', bytes: 1, sha1: 'x', url: '/api/b.png' },
      { name: 'topview.png', role: 'thumbnail', floor: null, mediaType: 'image/png', bytes: 1, sha1: 'x', url: '/api/t.png' },
    ])).toEqual({ F1: '/api/a.png' });
  });

  it('issue lines: at most five, then a count', () => {
    const issues = Array.from({ length: 7 }, (_, i) => ({ path: `/parts/${i}/z1`, message: 'must be > z0' }));
    expect(issueLines({ issues })).toEqual([
      '/parts/0/z1: must be > z0', '/parts/1/z1: must be > z0', '/parts/2/z1: must be > z0', '/parts/3/z1: must be > z0',
      '/parts/4/z1: must be > z0', '… and 2 more',
    ]);
    expect(issueLines(new Error('x'))).toEqual([]);
  });
});

describe('viewerOptions', () => {
  it('opens on the finished model, heights kept by the host', () => {
    expect(viewerOptions('', false)).toEqual({ address: {}, build: 'skip', furnitureHeights: 'host', testHook: false });
  });
  it('the address still decides the replay start-up (any mode key skips, even with build=play)', () => {
    expect(viewerOptions('?build=play', false).build).toBe('play');
    expect(viewerOptions('?build=play&mode=walk', false).build).toBe('skip');
    expect(viewerOptions('?mode=walk&floor=L2&x=1&z=2', true)).toEqual({
      address: { build: 'skip', mode: 'walk', floor: 'L2', point: { x: 1, y: null, z: 2 } },
      build: 'skip', furnitureHeights: 'host', testHook: true,
    });
  });
  it('the test hook follows VITE_WTV_TEST_HOOK by default', () => {
    expect(viewerOptions('').testHook).toBe(import.meta.env.VITE_WTV_TEST_HOOK === '1');
  });
});
