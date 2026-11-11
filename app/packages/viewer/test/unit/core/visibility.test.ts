// Builder A: createVisibility (DESIGN.md 11.5, 8), createPictures (5.7) and createLoop (11.4) in Node.
import { MeshBasicMaterial, SRGBColorSpace, type Mesh, type Texture } from 'three';
import { describe, expect, it, vi } from 'vitest';
import type { LoopApi } from '../../../src/contracts';
import { createDisposer } from '../../../src/core/disposer';
import { createLoop } from '../../../src/core/loop';
import { needsCors } from '../../../src/core/pictures';
import { kitContext } from './kit';

describe('visibility: floor mode', () => {
  it('shows all floors or one; setFloorMode emits floorMode; an unknown key shows all', () => {
    const ctx = kitContext('bank-v2');
    const seen = vi.fn();
    ctx.bus.on('floorMode', seen);
    const vis = () => ctx.floors.map(f => f.group.visible);
    expect(ctx.visibility.floorMode).toBe('all');
    ctx.visibility.setFloorMode('L1');
    expect(vis()).toEqual([true, false]);
    ctx.visibility.setFloorMode('L2');
    expect(vis()).toEqual([false, true]);
    expect(seen).toHaveBeenLastCalledWith({ floorMode: 'L2' });
    ctx.visibility.setFloorMode('L9');
    expect(ctx.visibility.floorMode).toBe('all');
    expect(vis()).toEqual([true, true]);
    ctx.floors[0]!.group.visible = false;                  // Walk sets the walked stack; applyFloor puts the floor mode back
    ctx.visibility.applyFloor();
    expect(vis()).toEqual([true, true]);
  });
});

// has() builds six scenes with their BVHs (integration: over vitest's 5 s default under load).
describe('visibility: ticks', { timeout: 60_000 }, () => {
  it('start from presentation.toggles (all on, the picture off); setToggle switches the objects and emits toggles', () => {
    const ctx = kitContext('house');
    const seen = vi.fn();
    ctx.bus.on('toggles', seen);
    expect(ctx.visibility.toggles).toEqual({ plates: true, glass: true, rooms: true, single: true, picture: false, ceilings: true });
    ctx.visibility.setToggle('glass', false);
    expect(ctx.built.toggleObjects.glass.every(o => !o.visible)).toBe(true);
    expect(ctx.built.toggleObjects.plates.every(o => o.visible)).toBe(true);
    expect(seen).toHaveBeenLastCalledWith({ toggles: { plates: true, glass: false, rooms: true, single: true, picture: false, ceilings: true } });
    ctx.visibility.setToggle('single', false);
    ctx.visibility.setToggle('plates', false);
    expect([...ctx.built.toggleObjects.single, ...ctx.built.toggleObjects.plates].every(o => !o.visible)).toBe(true);
    for (const o of ctx.built.toggleObjects.plates) o.visible = true;          // the replay shows every late object ...
    ctx.visibility.applyToggles();                                              // ... and its end applies the ticks again
    expect(ctx.built.toggleObjects.plates.every(o => !o.visible)).toBe(true);
  });
  it('has(): Floor plates and Glass always; Room names with rooms; Single-line with single parts; Plan picture with a sheet', () => {
    const has = (name: string, pictures?: Record<string, string>) => {
      const ctx = kitContext(name, { pictures });
      return (['plates', 'glass', 'rooms', 'single', 'picture'] as const).filter(t => ctx.visibility.has(t));
    };
    expect(has('bank-v2')).toEqual(['plates', 'glass', 'rooms']);
    expect(has('house')).toEqual(['plates', 'glass', 'single']);
    expect(has('suite')).toEqual(['plates', 'glass', 'rooms']);
    expect(has('mini')).toEqual(['plates', 'glass']);
    expect(has('hotel')).toEqual(['plates', 'glass', 'rooms']);
    expect(has('hotel', { F1: 'data:,', F2: 'data:,' })).toEqual(['plates', 'glass', 'rooms', 'picture']);
  });
  it('?picture=1 / ?picture=0 set the Plan picture tick at the start', () => {
    expect(kitContext('hotel', { address: { picture: true } }).visibility.toggles.picture).toBe(true);
    expect(kitContext('hotel', { address: {} }).visibility.toggles.picture).toBe(false);
  });
});

describe('pictures (5.7)', () => {
  const ctx = kitContext('hotel', { pictures: { F1: 'data:image/png;base64,AAAA', F2: 'data:image/png;base64,BBBB' } });
  const P = ctx.pictures!;
  it('one sheet per floor with a frame and a picture, in a scene-level group, named and with its userData', () => {
    expect(P.sheets.map(s => s.name)).toEqual(['F1 plan picture', 'F2 plan picture']);
    expect(P.sheets.every(s => s.parent?.name === 'plan pictures' && s.parent.parent === ctx.scene)).toBe(true);
    expect(ctx.floors.some(f => f.group.children.some(c => P.sheets.includes(c as Mesh)))).toBe(false);
    expect(P.src).toEqual({ F1: 'data:image/png;base64,AAAA', F2: 'data:image/png;base64,BBBB' });
    const pf = ctx.model.pictureFrame!.F1!;
    expect(P.sheets[0]!.userData).toMatchObject({ key: 'F1', size: pf.size, metres: [pf.size[0] / pf.pxPerMetreX, pf.size[1] / pf.pxPerMetreY] });
  });
  it('each sheet\'s corners are its picture\'s corners through the pictureFrame, 5 mm above its floor', () => {
    const M = ctx.model;
    for (const s of P.sheets) {
      const pf = M.pictureFrame![s.userData.key as string]!, level = ctx.floorByKey.get(s.userData.key as string)!.modelLevel;
      s.geometry.computeBoundingBox();
      const b = s.geometry.boundingBox!;
      const px = (x: number, y: number) => [pf.originPx[0] + pf.pxPerMetreX * (x + M.offset[0]), pf.originPx[1] - pf.pxPerMetreY * (y + M.offset[1])];
      const nw = px(b.min.x, -b.min.z), se = px(b.max.x, -b.max.z);
      expect(nw[0]).toBeCloseTo(0, 4); expect(nw[1]).toBeCloseTo(0, 4);
      expect(se[0]).toBeCloseTo(pf.size[0], 3); expect(se[1]).toBeCloseTo(pf.size[1], 3);
      expect(b.min.y - level).toBeCloseTo(0.005, 6);                      // float32 positions
    }
  });
  it('unlit, in front of the slab, its texture sRGB at the renderer\'s anisotropy; hidden until the tick is on', () => {
    const mat = P.sheets[0]!.material as MeshBasicMaterial;
    expect(mat).toBeInstanceOf(MeshBasicMaterial);
    expect([mat.polygonOffset, mat.polygonOffsetFactor, mat.polygonOffsetUnits]).toEqual([true, -2, -2]);
    const tex = mat.map as Texture;
    expect([tex.colorSpace, tex.anisotropy]).toEqual([SRGBColorSpace, 4]);
    expect(P.sheets.every(s => !s.visible)).toBe(true);
  });
  it('sync: shown with the tick and its floor group; the sheet follows its floor group\'s y', () => {
    ctx.visibility.setToggle('picture', true);
    P.sync();
    expect(P.sheets.map(s => s.visible)).toEqual([true, true]);
    ctx.visibility.setFloorMode('F1');
    P.sync();
    expect(P.sheets.map(s => s.visible)).toEqual([true, false]);
    ctx.visibility.setFloorMode('all');
    ctx.floorByKey.get('F2')!.group.position.y = 0.7;
    P.sync();
    expect(P.sheets[1]!.position.y).toBe(0.7);
    ctx.visibility.setToggle('picture', false);
    expect(P.sheets.every(s => !s.visible)).toBe(true);
  });
  it('ready resolves per floor (false where no image can be read: Node has no Image)', async () => {
    await expect(P.ready).resolves.toEqual([false, false]);
  });
  it('no picture URL or no frame: no sheets (null)', () => {
    expect(kitContext('hotel').pictures).toBeNull();
    expect(kitContext('bank-v2', { pictures: { L1: 'data:,' } }).pictures).toBeNull();
  });
  it('an http(s) picture is loaded in CORS mode, a data: one is not (fix step: WebGL refused a cross-origin picture)', async () => {
    const made: { crossOrigin: string | null; src: string }[] = [];
    class FakeImage {
      crossOrigin: string | null = null;
      onload: (() => void) | null = null;
      onerror: (() => void) | null = null;
      set src(v: string) { made.push(this as unknown as { crossOrigin: string | null; src: string }); (this as { url?: string }).url = v; queueMicrotask(() => this.onload?.()); }
      get src() { return (this as { url?: string }).url ?? ''; }
      removeAttribute() { /* abort */ }
    }
    const own = (globalThis as { Image?: unknown }).Image;
    (globalThis as { Image?: unknown }).Image = FakeImage;
    try {
      const c = kitContext('hotel', { pictures: { F1: 'https://objects.example/floor1_plan.png', F2: 'data:image/png;base64,BBBB' } });
      await expect(c.pictures!.ready).resolves.toEqual([true, true]);
      expect(made.map(i => [i.src.slice(0, 5), i.crossOrigin])).toEqual([['https', 'anonymous'], ['data:', null]]);
      const rel = kitContext('hotel', { pictures: { F1: '/api/projects/hotel-lobby/versions/1/assets/floor1_plan.png' } });
      await rel.pictures!.ready;
      expect(made.at(-1)!.crossOrigin).toBe('anonymous');      // same origin through the proxy: CORS mode is harmless
      c.disposer.dispose(); rel.disposer.dispose();
    } finally {
      (globalThis as { Image?: unknown }).Image = own;
    }
    expect(needsCors('data:image/png;base64,AA')).toBe(false);
    expect(needsCors('blob:http://127.0.0.1/x')).toBe(false);
    expect(needsCors('http://127.0.0.1:8710/a.png')).toBe(true);
  });
});

describe('loop (11.4): replay -> modes -> sync -> render -> overlay', () => {
  const make = () => {
    const calls: string[] = [];
    let anim: ((t: number) => void) | null = null;
    const renderer = { render: () => calls.push('render'), setAnimationLoop: (fn: ((t: number) => void) | null) => { anim = fn; } };
    const errors: unknown[] = [];
    const disposer = createDisposer();
    const loop = createLoop({ renderer: renderer as never, scene: {} as never, camera: {} as never, disposer, reportError: e => errors.push(e) }) as LoopApi & { firstFrame: Promise<void> };
    return { loop, calls, errors, disposer, anim: () => anim };
  };
  it('runs the phases in order, whatever the order they were added in', () => {
    const { loop, calls } = make();
    for (const phase of ['overlay', 'sync', 'modes', 'replay'] as const) loop.add(phase, () => calls.push(phase));
    loop.frame(5);
    expect(calls).toEqual(['replay', 'modes', 'sync', 'render', 'overlay']);
  });
  it('an error in a hook goes to reportError and the frame goes on', () => {
    const { loop, calls, errors } = make();
    loop.add('modes', () => { throw new Error('boom'); });
    loop.add('overlay', () => calls.push('overlay'));
    loop.frame(1);
    expect(errors.map(e => (e as Error).message)).toEqual(['boom']);
    expect(calls).toEqual(['render', 'overlay']);
  });
  it('add() returns its own remover; start / stop drive setAnimationLoop; firstFrame after the first frame', async () => {
    const { loop, calls, anim, disposer } = make();
    const off = loop.add('sync', now => calls.push(`sync ${now}`));
    loop.start();
    expect(loop.running).toBe(true);
    anim()!(16);
    off();
    anim()!(32);
    expect(calls).toEqual(['sync 16', 'render', 'render']);
    await loop.firstFrame;
    loop.stop();
    expect(loop.running).toBe(false);
    expect(anim()).toBeNull();
    loop.start();
    disposer.dispose();
    expect(loop.running).toBe(false);
    loop.start();
    expect(loop.running).toBe(false);                     // no restart after dispose
  });
  it('firstFrame also resolves when the loop is disposed before any frame', async () => {
    const { loop, disposer } = make();
    disposer.dispose();
    await expect(loop.firstFrame).resolves.toBeUndefined();
  });
});
