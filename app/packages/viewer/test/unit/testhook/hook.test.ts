// @vitest-environment happy-dom
// Builder A: installTestHook (DESIGN.md 11.7): window.__viewer / __host / __build / __walkthrough read the live objects;
// FL carries the MODEL levels, floors the Walk levels; fitted replaces the house page's pieces; THREE is the subset with
// Color; dispose() deletes each property that is still this viewer's. And the offline entry's payload reading.
import * as THREE from 'three';
import { describe, expect, it, vi } from 'vitest';
import type { ModesApi, OfflinePayload, ReplayApi, Viewer } from '../../../src/contracts';
import { createLabels } from '../../../src/core/labels';
import { installTestHook, TEST_THREE } from '../../../src/testhook/hook';
import { kitContext } from '../core/kit';

function setup(name = 'house') {
  const root = document.createElement('div');
  document.body.append(root);
  const ctx = kitContext(name, { root });
  const state = { mode: 'orbit', floor: ctx.floors[0] } as unknown as ModesApi['state'];
  const modes = {
    get mode() { return state.mode; }, state, probe: { visible: () => ['x'] },
    setMode: vi.fn(), goToFloor: vi.fn(), takePhoto: vi.fn(() => Promise.resolve(null)), lock: vi.fn(),
  } as unknown as ModesApi;
  const w = ctx as unknown as Record<string, unknown>;
  w.modes = modes;
  w.labels = createLabels(ctx);
  w.renderer = { info: { memory: { geometries: 3, textures: 1 }, programs: [1, 2] } };
  const viewer = { dispose: () => ctx.disposer.dispose() } as unknown as Viewer;
  return { ctx, modes, state, viewer, root };
}

describe('installTestHook', () => {
  it('sets the four hooks, reading the live objects', () => {
    const { ctx, modes, state, viewer } = setup('house');
    installTestHook(ctx, viewer);
    expect(window.__viewer!.mode).toBe('orbit');
    (state as { mode: string }).mode = 'walk';
    expect(window.__viewer!.mode).toBe('walk');
    expect(window.__viewer!.state).toBe(state);
    expect(window.__viewer!.probe.visible()).toEqual(['x']);
    window.__viewer!.setMode('ghost');
    window.__viewer!.goToFloor('upper');
    window.__viewer!.lock(true);
    expect([vi.mocked(modes.setMode).mock.calls[0], vi.mocked(modes.goToFloor).mock.calls[0], vi.mocked(modes.lock).mock.calls[0]]).toEqual([['ghost', undefined], ['upper'], [true]]);
    const h = window.__host!;
    expect(h.floors).toBe(ctx.floors);
    expect(h.model).toBe(ctx.model);
    expect(h.openings).toBe(ctx.model.openings);
    expect(h.probes).toBe(ctx.model.probes);
    expect(h.fitted).toBe(ctx.built.fitted);
    expect(Object.fromEntries(Object.entries(h.fitted).map(([k, ms]) => [k, ms.length]))).toEqual({ ground: 4, upper: 2 });
    expect(h.plinths).toBe(ctx.built.plinths);
    expect(h.groups.ground).toBe(ctx.floorByKey.get('ground')!.group);
    expect(h.rise.upper).toBe(ctx.floorByKey.get('upper')!.rise);
    expect(h.labels).toBe(ctx.labels.labels);
    expect(h.furniture).toBeNull();
    expect(h.pictures).toBeNull();
    expect(h.camera).toBe(ctx.camera);
    expect(window.__build).toBeNull();
    expect(window.__walkthrough!.gpu()).toEqual({ geometries: 3, textures: 1, programs: 2 });
    expect(window.__walkthrough!.viewer).toBe(viewer);
    expect(typeof window.__walkthrough!.live()).toBe('number');
    expect(window.__walkthrough!.version).toBe('0.1.0');
    viewer.dispose();
    expect([window.__viewer, window.__host, window.__build, window.__walkthrough]).toEqual([undefined, undefined, undefined, undefined]);
    expect('__build' in window).toBe(false);
  });

  it('FL keeps the MODEL levels (the prototypes\' FL), floors the Walk levels; the arrays are the very ones Walk uses', () => {
    const { ctx, viewer } = setup('bank-v2');
    installTestHook(ctx, viewer);
    ctx.heights.apply({ L1: { level: 0, height: 3.7 }, L2: { level: 5, height: 3.7 } });
    expect(window.__host!.FL.L2!.level).toBe(3.7);
    expect(window.__host!.floors[1]!.level).toBe(5);
    expect(window.__host!.FL.L1!.colliders).toBe(ctx.floorByKey.get('L1')!.colliders);
    expect(window.__host!.FL.L1!.late).toBe(ctx.floorByKey.get('L1')!.late);
    const hit = window.__host!.rayHit('L1', 0, 0, 1.2, 1, 0, 0.001);
    expect(hit).toBeNull();
    expect(window.__host!.upHit('nowhere', 0, 0)).toBeNull();
    viewer.dispose();
  });

  it('__build follows the replay; __walkthrough.THREE is the subset, with Color, from the bundled three', () => {
    const { ctx, viewer } = setup('bank-v2');
    const replay = { phase: 'settings', state: { T: 0 }, steps: [], generate: vi.fn(), skip: vi.fn(), openSettings: vi.fn(), seek: vi.fn() } as unknown as ReplayApi;
    (ctx as unknown as { replay: ReplayApi }).replay = replay;
    installTestHook(ctx, viewer);
    expect(window.__build!.phase).toBe('settings');
    (replay as { phase: string }).phase = 'done';
    expect(window.__build!.phase).toBe('done');
    window.__build!.seek(0.5);
    expect(vi.mocked(replay.seek)).toHaveBeenCalledWith(0.5);
    expect(Object.keys(TEST_THREE).sort()).toEqual(['Box3', 'Color', 'Euler', 'MathUtils', 'Matrix4', 'Plane', 'Quaternion', 'Raycaster', 'Vector2', 'Vector3']);
    expect(window.__walkthrough!.THREE.Vector3).toBe(THREE.Vector3);
    expect(window.__walkthrough!.THREE.Color).toBe(THREE.Color);
    viewer.dispose();
    expect(window.__build).toBeUndefined();
  });

  it('dispose leaves another viewer\'s hooks alone', () => {
    const a = setup('mini'), b = setup('mini');
    installTestHook(a.ctx, a.viewer);
    installTestHook(b.ctx, b.viewer);
    const theirs = window.__walkthrough;
    a.viewer.dispose();
    expect(window.__walkthrough).toBe(theirs);
    expect(window.__host).toBeDefined();
    expect(window.__build).toBeNull();
    b.viewer.dispose();
    expect(window.__walkthrough).toBeUndefined();
  });
});

describe('the offline entry: reading the payload', async () => {
  const { readPayload, projectOf } = await import('../../../src/offline/entry');
  const payload: OfflinePayload = {
    format: 'walkthrough-offline/1',
    project: { id: 'bank-sampeng' } as OfflinePayload['project'],
    version: { version: 2, stamp: 'c3a9408304a2', presentation: { documentTitle: 'T' } } as unknown as OfflinePayload['version'],
    model: { photoName: 'x' } as unknown as OfflinePayload['model'],
    stages: null, pictures: { F1: 'data:image/png;base64,AA==' }, overrides: { format: 'walkthrough-overrides/1', heights: { table: 600 }, revision: 1, updatedAt: '' },
  };
  it('parses a payload and makes the ViewerProject of DESIGN.md 16', () => {
    const p = readPayload(JSON.stringify(payload).split('<').join('\\u003c'));
    expect(projectOf(p)).toEqual({ model: payload.model, presentation: payload.version.presentation, stages: null, pictures: payload.pictures,
      heights: { table: 600 }, stamp: 'c3a9408304a2', ids: { projectId: 'bank-sampeng', version: 2 } });
    expect(projectOf({ ...p, overrides: null }).heights).toBeNull();
  });
  it('passes the deleted boxes only when the file carries them: no pieceEdits key otherwise (step BX)', () => {
    expect('pieceEdits' in projectOf(payload)).toBe(false);
    expect('pieceEdits' in projectOf({ ...payload, overrides: null })).toBe(false);
    const edits = { 'L1-table-001': { removed: true as const }, 'L1-computer-001': { removed: true as const } };
    const withEdits: OfflinePayload = { ...payload, overrides: { ...payload.overrides!, pieceEdits: edits } };
    const p = projectOf(readPayload(JSON.stringify(withEdits)));
    expect(p.pieceEdits).toEqual(edits);
    expect(p.heights).toEqual({ table: 600 });
    expect(Object.keys(p).sort()).toEqual([...Object.keys(projectOf(payload)), 'pieceEdits'].sort());
    // whatever the file holds there is passed as it is: the viewer reads it leniently (furniture/logic.ts removedIdsOf)
    const odd = { ...payload, overrides: { ...payload.overrides!, pieceEdits: { x: 'yes' } } } as unknown as OfflinePayload;
    expect(projectOf(odd).pieceEdits).toEqual({ x: 'yes' });
  });
  it('says plainly what is wrong with a missing or broken payload', () => {
    expect(() => readPayload(null)).toThrow('could not be read');
    expect(() => readPayload('not json')).toThrow('could not be read');
    expect(() => readPayload('{"format":"other"}')).toThrow('walkthrough-offline/1');
    expect(() => readPayload(JSON.stringify({ ...payload, model: null }))).toThrow('incomplete');
    expect(() => readPayload(JSON.stringify({ ...payload, version: { presentation: {} } }))).toThrow('incomplete');
  });
});
