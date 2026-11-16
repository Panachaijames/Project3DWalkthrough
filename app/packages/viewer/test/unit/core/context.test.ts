// Builder A: the parts of core/context.ts that run without WebGL (DESIGN.md 11.2 - 11.4, 11.8): the resolved options, the
// camera start (fixed, and the hotel page's fitSlabs with the side panel's right edge), and what dispose frees besides the
// scene graph (three 0.186's renderer-owned DFG lookup table, docs/contract-issues/A.md A-1).
import {
  BoxGeometry, DataTexture, Group, Mesh, MeshBasicMaterial, MeshStandardMaterial, OrthographicCamera, PerspectiveCamera, Scene, Texture, Vector3,
  type WebGLRenderer,
} from 'three';
import { describe, expect, it, vi } from 'vitest';
import type { ViewerContext, ViewerProject } from '../../../src/contracts';
import { applyCameraStart, disposeTree, rendererTextures, resolveOptions, savedHeightsTag, STORAGE_KEY_PREFIX } from '../../../src/core/context';
import { kitContext } from './kit';

const project = (stages: boolean): ViewerProject => ({
  model: { photoName: 'BangkokBank-Sampeng' } as ViewerProject['model'], presentation: {} as ViewerProject['presentation'],
  stages: stages ? ({} as NonNullable<ViewerProject['stages']>) : null, stamp: 'c3a9408304a2',
});

describe('resolveOptions (11.3, contracts ResolvedOptions)', () => {
  const dl = () => {};
  it('build: options.build wins, then the address, then settings with stages / skip without', () => {
    expect(resolveOptions(project(true), undefined, dl).build).toBe('settings');
    expect(resolveOptions(project(false), undefined, dl).build).toBe('skip');
    expect(resolveOptions(project(true), { address: { build: 'skip' } }, dl).build).toBe('skip');
    expect(resolveOptions(project(true), { address: { build: 'skip' }, build: 'play' }, dl).build).toBe('play');
  });
  it('the storage key, the heights mode, the pixel ratio cap, nodownload, the download function', () => {
    const r = resolveOptions(project(false), { address: { nodownload: true } }, dl);
    expect(r.storageKey).toBe(`${STORAGE_KEY_PREFIX}BangkokBank-Sampeng:c3a9408304a2`);
    expect(STORAGE_KEY_PREFIX).toBe('walkthrough-furniture-heights:');
    expect([r.furnitureHeights, r.pixelRatioCap, r.noDownload, r.download]).toEqual(['local', 2, true, dl]);
    const own = vi.fn();
    const h = resolveOptions(project(false), { furnitureHeights: 'host', storageKeyPrefix: 'x:', pixelRatioCap: 1, download: own }, dl);
    expect([h.furnitureHeights, h.storageKey, h.pixelRatioCap, h.download, h.noDownload]).toEqual(['host', 'x:BangkokBank-Sampeng:c3a9408304a2', 1, own, false]);
  });
  it('the offline storage key carries the saved heights the file has (fix step): another download with other saved heights has its own key', () => {
    const plain = `${STORAGE_KEY_PREFIX}BangkokBank-Sampeng:c3a9408304a2`;
    const withHeights = (heights: Record<string, number> | null, mode?: 'local' | 'host') =>
      resolveOptions({ ...project(false), heights }, mode ? { furnitureHeights: mode } : undefined, dl).storageKey;
    expect(withHeights(null)).toBe(plain);
    expect(withHeights({})).toBe(plain);
    const a = withHeights({ table: 600 }), b = withHeights({ table: 700, seat: 300 });
    expect(a).toMatch(new RegExp(`^${plain}:[0-9a-f]{8}$`));
    expect(b).toMatch(new RegExp(`^${plain}:[0-9a-f]{8}$`));
    expect(a).not.toBe(b);
    expect(withHeights({ seat: 300, table: 700 })).toBe(b);                   // the order of the keys does not matter
    expect(withHeights({ table: 600 }, 'host')).toBe(plain);                  // the staff app stores no heights
    expect(savedHeightsTag({ table: 600 })).toBe(a.slice(plain.length + 1));
    expect(savedHeightsTag({ table: Number.NaN })).toBe('');
  });
  it('editBoxes (step BX): the key is there only when the option is exactly true; the storage key does not change with it', () => {
    expect('editBoxes' in resolveOptions(project(false), undefined, dl)).toBe(false);
    expect('editBoxes' in resolveOptions(project(false), { editBoxes: false }, dl)).toBe(false);
    expect('editBoxes' in resolveOptions(project(false), { editBoxes: 1 as unknown as boolean }, dl)).toBe(false);
    const on = resolveOptions(project(false), { editBoxes: true, furnitureHeights: 'host' }, dl);
    expect(on.editBoxes).toBe(true);
    expect(on.storageKey).toBe(resolveOptions(project(false), { furnitureHeights: 'host' }, dl).storageKey);
    // saved deleted boxes do not change the offline file's key either (docs/boxes/DESIGN.md 3.5)
    const withEdits = { ...project(false), heights: { table: 600 }, pieceEdits: { 'L1-table-001': { removed: true as const } } };
    expect(resolveOptions(withEdits, undefined, dl).storageKey).toBe(resolveOptions({ ...project(false), heights: { table: 600 } }, undefined, dl).storageKey);
  });
  it('testFailAt only together with testHook', () => {
    expect(resolveOptions(project(false), { testFailAt: 'modes' }, dl).testFailAt).toBeNull();
    expect(resolveOptions(project(false), { testFailAt: 'modes', testHook: true }, dl)).toMatchObject({ testFailAt: 'modes', testHook: true });
  });
});

describe('applyCameraStart (11.4 steps 2 and 4)', () => {
  const withCamera = (name: string, panelRight: number, size = { width: 1400, height: 880 }) => {
    const ctx = kitContext(name, { size }) as unknown as Record<string, unknown> & ViewerContext;
    const camera = new PerspectiveCamera(40, size.width / size.height, 0.1, 600);
    const target = new Vector3();
    Object.assign(ctx, {
      camera, controls: { target, update: vi.fn(() => camera.lookAt(target)) },
      panel: { el: {} as HTMLDivElement }, rectOf: () => ({ left: 12, top: 12, right: panelRight, bottom: 500, width: panelRight - 12, height: 488 }),
    });
    return ctx;
  };
  it('fixed (the bank): the position and target of the presentation, then controls.update()', () => {
    const ctx = withCamera('bank-v2', 372);
    applyCameraStart(ctx);
    expect(ctx.camera.position.toArray()).toEqual([24, 27, 29]);
    expect(ctx.controls.target.toArray()).toEqual([0, 2.5, 0]);
    expect(ctx.controls.update).toHaveBeenCalled();
  });
  it('fitSlabs (the hotel): the middle of the slabs at y 2.5, from (24, 24.5, 29) x 0.9, panned left by half of min(panel right, width / 2)', () => {
    for (const [right, size] of [[372, { width: 1400, height: 880 }], [372, { width: 1400, height: 800 }], [372, { width: 600, height: 800 }]] as const) {
      const ctx = withCamera('hotel', right, size);
      applyCameraStart(ctx);
      let x0 = Infinity, x1 = -Infinity, y0 = Infinity, y1 = -Infinity;
      for (const p of ctx.model.parts) if (p.kind === 'slab') for (const [x, y] of p.o) { x0 = Math.min(x0, x); x1 = Math.max(x1, x); y0 = Math.min(y0, y); y1 = Math.max(y1, y); }
      const away = new Vector3(24, 24.5, 29).multiplyScalar(0.9), sideways = new Vector3(away.z, 0, -away.x).normalize();
      const mpp = 2 * away.length() * Math.tan(40 * Math.PI / 360) / size.height;
      const want = new Vector3((x0 + x1) / 2, 2.5, -(y0 + y1) / 2).addScaledVector(sideways, -Math.min(right, size.width / 2) / 2 * mpp);
      expect(ctx.controls.target.distanceTo(want)).toBeLessThan(1e-9);
      expect(ctx.camera.position.distanceTo(want.clone().add(away))).toBeLessThan(1e-9);
    }
  });
});

describe('what dispose frees (11.8)', () => {
  it('disposeTree: every geometry (its BVH dropped), material and material texture once', () => {
    const scene = new Scene(), group = new Group(), map = new Texture();
    const geo = new BoxGeometry(), mat = new MeshBasicMaterial({ map }), shared = new MeshStandardMaterial();
    group.add(new Mesh(geo, mat), new Mesh(geo, shared), new Mesh(new BoxGeometry(), [shared, mat]));
    scene.add(group);
    (geo as unknown as { boundsTree: unknown }).boundsTree = {};
    const seen: string[] = [];
    for (const [name, thing] of [['geo', geo], ['mat', mat], ['shared', shared], ['map', map]] as const) thing.addEventListener('dispose', () => seen.push(name));
    disposeTree(scene);
    expect(seen.sort()).toEqual(['geo', 'map', 'mat', 'shared']);
    expect((geo as unknown as { boundsTree: unknown }).boundsTree).toBeUndefined();
  });
  it("rendererTextures: the textures the renderer put in the materials' uniforms (three 0.186's dfgLUT), found once", () => {
    const lut = new DataTexture(new Uint16Array(16 * 16 * 2), 16, 16);
    const scene = new Scene(), a = new MeshStandardMaterial(), b = new MeshStandardMaterial(), basic = new MeshBasicMaterial();
    scene.add(new Mesh(new BoxGeometry(), a), new Mesh(new BoxGeometry(), [b, basic]), new OrthographicCamera());
    const uniforms = new Map<object, unknown>([[a, { dfgLUT: { value: lut } }], [b, { dfgLUT: { value: lut } }], [basic, {}]]);
    const renderer = { properties: { get: (o: object) => ({ uniforms: uniforms.get(o) }) } } as unknown as WebGLRenderer;
    expect([...rendererTextures(renderer, scene)]).toEqual([lut]);
    expect([...rendererTextures({} as WebGLRenderer, scene)]).toEqual([]);                    // a stub renderer has none
  });
});
