// BuiltModel v2 in the core (rooms ACCEPTANCE 2.3 R4; DESIGN R-9.2, R-9.6, R-9.7, R-9.8): buildScene's surfaces, the
// single-sided tread mesh that is not a collider, the per-floor ceiling mesh and where it shows, Build settings' storey
// scaling of treads and cut walls, ceilings that keep their height, and groundAt.
import { FrontSide, Raycaster, Vector3, type Mesh, type MeshStandardMaterial } from 'three';
import { describe, expect, it } from 'vitest';
import { kitContext, type KitContext } from './kit';

const REF = 'fixtures/models/rooms-reference.model.json';
const names = (list: { name: string }[]) => list.map(m => m.name);
const child = (ctx: KitContext, floor: string, name: string) => ctx.floorByKey.get(floor)!.group.children.find(o => o.name === name) as Mesh;
const span = (m: Mesh): [number, number] => {
  m.updateWorldMatrix(true, false);
  const pos = m.geometry.getAttribute('position'), v = new Vector3();
  let lo = Infinity, hi = -Infinity;
  for (let i = 0; i < pos.count; i++) { v.fromBufferAttribute(pos, i).applyMatrix4(m.matrixWorld); lo = Math.min(lo, v.y); hi = Math.max(hi, v.y); }
  return [Math.round(lo * 1000) / 1000 + 0, Math.round(hi * 1000) / 1000 + 0];
};

describe('buildScene on a model with stairways', () => {
  it('lists the surfaces: the tread mesh and the slabs; walkables stay the slabs only', () => {
    const ctx = kitContext(REF), g = ctx.floorByKey.get('ground')!, u = ctx.floorByKey.get('upper')!;
    expect(names(g.surfaces)).toEqual(['ground tread:storey', 'ground floor plate']);
    expect(names(u.surfaces)).toEqual(['upper floor plate']);
    expect(names(g.walkables)).toEqual(['ground floor plate']);
    expect(names(u.walkables)).toEqual(['upper floor plate']);
  });

  it('a model without stairways has no surfaces, no ceilings mesh and no Ceilings tick', () => {
    for (const name of ['bank-v2', 'hotel', 'house']) {
      const ctx = kitContext(name);
      expect(ctx.floors.every(f => f.surfaces.length === 0)).toBe(true);
      expect(ctx.floors.flatMap(f => f.group.children).filter(o => o.userData.ceiling || o.userData.steps)).toEqual([]);
      expect(ctx.visibility.has('ceilings')).toBe(false);
    }
  });

  it('treads and landings are one single-sided mesh with a BVH and edges, never a collider, fit storey', () => {
    const ctx = kitContext(REF), g = ctx.floorByKey.get('ground')!, mesh = child(ctx, 'ground', 'ground tread:storey');
    expect((mesh.material as MeshStandardMaterial).side).toBe(FrontSide);
    expect((mesh.material as MeshStandardMaterial).polygonOffset).toBe(false);
    expect(mesh.geometry.boundsTree).toBeTruthy();
    expect(mesh.userData).toMatchObject({ steps: true, stairTo: 'upper', floor: 'ground' });
    expect(g.colliders).not.toContain(mesh);
    expect(names(g.colliders).some(n => /tread|landing|ceiling/.test(n))).toBe(false);
    const item = g.rise.find(r => r.mesh === mesh)!;
    expect([item.fit, item.scales, item.edges?.name]).toEqual(['storey', false, 'ground tread:storey edges']);
    expect(names(g.group.children).filter(n => /landing/.test(n))).toEqual([]);       // the landing is in the tread mesh
    expect(span(mesh)).toEqual([0, 2.812]);
    // a ray that starts inside a block passes out of it: from inside tread 4 (0.375 .. 0.75) down, the first hit is not its bottom
    const ray = new Raycaster(new Vector3(-4.8, 0.6, 1.72), new Vector3(0, -1, 0));
    expect(ray.intersectObject(mesh, false)).toEqual([]);
    ray.set(new Vector3(-4.8, 2, 1.72), new Vector3(0, -1, 0));
    expect(ray.intersectObject(mesh, false)[0]!.point.y).toBeCloseTo(0.75, 3);
  });

  it('the wall piece cut under the stair is a collider that scales with the storey', () => {
    const ctx = kitContext(REF), g = ctx.floorByKey.get('ground')!, wall = child(ctx, 'ground', 'ground solid:storey');
    expect(g.colliders).toContain(wall);
    expect(wall.userData.stairTo).toBe('upper');
    expect(g.rise.find(r => r.mesh === wall)!.fit).toBe('storey');
    expect(span(wall)).toEqual([0, 2.062]);
    expect(names(g.rise.map(r => r.mesh))).toEqual(expect.arrayContaining(['ground solid:follow', 'ground solid:storey', 'ground tread:storey']));
  });

  it('ceilings: one merged mesh per floor, facing down, late, no edges, no BVH, not a collider, not a surface', () => {
    const ctx = kitContext(REF);
    for (const f of ctx.floors) {
      const list = f.group.children.filter(o => o.userData.ceiling === true) as Mesh[];
      expect(names(list)).toEqual([`${f.key} ceilings`]);
      const mesh = list[0]!, mat = mesh.material as MeshStandardMaterial;
      expect([mat.side, `#${mat.color.getHexString()}`, mat.roughness]).toEqual([FrontSide, '#f4f3ef', 0.95]);
      expect(mesh.geometry.boundsTree).toBeFalsy();
      expect(f.late).toContain(mesh);
      expect(f.colliders).not.toContain(mesh);
      expect(f.surfaces).not.toContain(mesh);
      expect(f.rise.some(r => r.mesh === mesh)).toBe(false);
      expect(names(f.group.children)).not.toContain(`${f.key} ceilings edges`);
      expect(span(mesh)).toEqual([f.level + 2.68, f.level + 2.68]);
      // every triangle faces down: seen from below, not from above
      const up = new Raycaster(new Vector3(0, f.level + 1, 3), new Vector3(0, 1, 0));
      expect(up.intersectObject(mesh, false).length).toBe(1);
      const down = new Raycaster(new Vector3(0, f.level + 2.9, 3), new Vector3(0, -1, 0));
      expect(down.intersectObject(mesh, false)).toEqual([]);
      const normal = mesh.geometry.getAttribute('normal');
      for (let i = 0; i < normal.count; i++) expect(normal.getY(i)).toBe(-1);
    }
  });
});

describe('ceilings show in Walk and Ghost only, with the Ceilings tick (R-9.7)', () => {
  it('never in Orbit; the tick hides them; a model with ceilings has the tick, on by default', () => {
    const ctx = kitContext(REF);
    const shown = () => ctx.floors.map(f => child(ctx, f.key, `${f.key} ceilings`).visible);
    const mode = (m: 'orbit' | 'walk' | 'ghost') => { ctx.modes.mode = m; ctx.bus.emit('mode', { mode: m, floor: 'ground' }); };
    expect(ctx.visibility.has('ceilings')).toBe(true);
    expect(ctx.visibility.toggles.ceilings).toBe(true);
    expect(shown()).toEqual([false, false]);                          // as built
    ctx.visibility.applyToggles();
    expect(shown()).toEqual([false, false]);                          // Orbit
    mode('walk');
    expect(shown()).toEqual([true, true]);
    ctx.visibility.setToggle('ceilings', false);
    expect(shown()).toEqual([false, false]);
    mode('ghost');
    expect(shown()).toEqual([false, false]);
    ctx.visibility.setToggle('ceilings', true);
    expect(shown()).toEqual([true, true]);
    // the replay's end (fadeLate shows every late object, then applyToggles): hidden again in Orbit
    mode('orbit');
    for (const f of ctx.floors) for (const o of f.late) o.visible = true;
    ctx.visibility.applyToggles();
    expect(shown()).toEqual([false, false]);
    // the other ticks are as before
    ctx.visibility.setToggle('plates', false);
    expect(child(ctx, 'ground', 'ground floor plate').visible).toBe(false);
  });
});

describe('Build settings on a model with stairways (R-9.6)', () => {
  it('treads, landings and the cut wall scale with the storey; ceilings keep their height above their floor', () => {
    const ctx = kitContext(REF);
    const tread = child(ctx, 'ground', 'ground tread:storey'), wall = child(ctx, 'ground', 'ground solid:storey');
    const other = child(ctx, 'ground', 'ground solid:follow');
    const ceil = (k: string) => span(child(ctx, k, `${k} ceilings`))[0];
    ctx.heights.apply({ upper: { level: 3.6, height: 3 } });           // the upper floor 0.6 m higher: S = 1.2
    expect(tread.scale.y).toBeCloseTo(1.2, 9);
    expect(span(tread)).toEqual([0, 3.374]);                           // 2.812 x 1.2: one riser under 3.6
    expect(span(wall)).toEqual([0, 2.474]);
    expect(span(other)).toEqual([0, 3]);                               // the other walls: the wall height, unchanged
    expect([ceil('ground'), ceil('upper')]).toEqual([2.68, 6.28]);
    const edges = ctx.floorByKey.get('ground')!.rise.find(r => r.mesh === tread)!.edges!;
    expect([edges.scale.y, edges.position.y]).toEqual([tread.scale.y, tread.position.y]);

    ctx.heights.apply({ ground: { level: 0.5, height: 3.5 }, upper: { level: 3.5, height: 3 } });   // both moved: S = 1 again
    expect(span(tread)).toEqual([0.5, 3.312]);
    expect(span(wall)).toEqual([0.5, 2.562]);                          // not the wall-height ratio
    expect(span(other)).toEqual([0.5, 4]);
    expect([ceil('ground'), ceil('upper')]).toEqual([3.18, 6.18]);

    ctx.heights.apply({ ground: { level: 1, height: 3 }, upper: { level: 3, height: 3 } });         // S = 2 / 3
    expect(tread.scale.y).toBeCloseTo(2 / 3, 9);
    expect(span(tread)).toEqual([1, 2.875]);
    ctx.heights.apply({ ground: { level: 0, height: 3 }, upper: { level: 3, height: 3 } });
    expect([tread.scale.y, tread.position.y, span(tread)]).toEqual([1, 0, [0, 2.812]]);
  });
});

describe('readouts.groundAt (R-9.8)', () => {
  it('reads the surfaces of the stack: a tread, the landing, the slabs; null off them and on an old model', () => {
    const ctx = kitContext(REF), at = (k: string, x: number, y: number, h0?: number) => { const v = ctx.readouts.groundAt(k, x, y, h0); return v === null ? null : Math.round(v * 1000) / 1000; };
    expect(at('ground', -4.8, -1.72)).toBe(0.75);                      // tread 4
    expect(at('ground', -4.8, -0.42)).toBe(1.312);                     // the landing
    expect(at('ground', 0, 3, 2.5)).toBe(0);                          // the ground slab, from under the upper one
    expect(at('ground', 0, 3, 4)).toBe(3);                            // from above the upper slab
    expect(at('upper', 0, 3)).toBe(0);
    expect(at('upper', -4.8, -1.72)).toBe(-2.25);                      // through the well, the tread below
    expect(at('ground', 40, 40)).toBeNull();
    expect(at('nope', 0, 0)).toBeNull();
    ctx.visibility.setToggle('plates', false);                         // what Walk stands on, shown or not
    expect(at('upper', 0, 3)).toBe(0);
    ctx.heights.apply({ upper: { level: 3.6, height: 3 } });
    expect(at('ground', -4.8, -1.72)).toBe(0.9);                       // the tread scaled with the storey
    const old = kitContext('bank-v2');
    expect(old.readouts.groundAt(old.floors[0]!.key, 0, 0)).toBeNull();
    expect(old.readouts.downHit(old.floors[0]!.key, 0, 0)).toBe(kitContext('bank-v2').readouts.downHit(old.floors[0]!.key, 0, 0));
  });
});
