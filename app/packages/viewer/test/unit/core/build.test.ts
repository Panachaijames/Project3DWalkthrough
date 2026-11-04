// Builder A: buildScene (DESIGN.md 5.4, 17.2 "build"), pure three.js in Node. Every fixture model against the facts read
// from its prototype page (fixtures/prototype/*.json): per floor the colliders (names and vertices), walkables, late
// objects without the boxes, rise (names, scales) and the group's children; the tick lists; for the house its v1 values
// (17.2: the bank's grouping rule groups it differently from its page). features.model.json covers every kind, fit,
// plinth, panels, the ground plane and a deck that is not a collider.
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { DoubleSide, FrontSide, LineSegments, Mesh, MeshStandardMaterial, type BufferAttribute, type Material, type Object3D } from 'three';
import { describe, expect, it } from 'vitest';
import type { BuiltModel, BuiltScene, Presentation } from '../../../src/contracts';
import { buildScene, fitDataOf, fitName, fitOf } from '../../../src/core/build';
import { parsePresentation, resolvePresentation } from '../../../src/model/presentation';

const APP = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../../../..');
const json = (rel: string): any => JSON.parse(readFileSync(path.join(APP, rel), 'utf8'));
const model = (name: string): BuiltModel => json(name.endsWith('.json') ? name : `fixtures/models/${name}.model.json`);
const presentationOf = (name: string | null, m: BuiltModel) => resolvePresentation(parsePresentation(name ? json(`fixtures/presentation/${name}.json`)
  : { documentTitle: 't', heading: 'h', intro: [], accent: '#2f6f8f', legend: { layout: 'inline', items: [] }, camera: { kind: 'fixed', position: [1, 1, 1], target: [0, 0, 0] } } satisfies Presentation), m);
const build = (m: string, p: string | null): { model: BuiltModel; built: BuiltScene } => {
  const mm = model(m);
  return { model: mm, built: buildScene(mm, presentationOf(p, mm)) };
};
const vcount = (o: Object3D) => ((o as Mesh).geometry?.getAttribute('position') as BufferAttribute | undefined)?.count ?? 0;
const sum = (xs: number[]) => xs.reduce((a, b) => a + b, 0);

interface FloorFacts {
  key: string; colliders: { name: string; vertices: number }[]; colliderVertices: number; walkables: { vertices: number }[];
  walkableVertices: number; late: number; lateWithoutFurniture: number; rise: { name: string; scales: boolean }[]; groupChildren: number;
}

describe.each([
  { m: 'bank-v1', facts: 'bank-sampeng-v1', names: 'exact' },
  { m: 'bank-v2', facts: 'bank-sampeng-v2', names: 'exact' },
  { m: 'hotel', facts: 'hotel-lobby', names: 'exact' },
  { m: 'suite', facts: 'presidential-suite', names: 'suite' },
] as const)('buildScene($m) against the facts of its page', ({ m, facts: factsName, names }) => {
  const facts = json(`fixtures/prototype/${factsName}.json`);
  const { model: mm, built } = build(m, factsName);
  const floorFacts = facts.scene.floors as FloorFacts[];

  it('has the model floors, in order, at their model levels', () => {
    expect(built.floors.map(f => f.key)).toEqual(mm.floors.map(f => f.key));
    built.floors.forEach((f, i) => { expect(f.level).toBe(mm.floors[i]!.level); expect(f.modelLevel).toBe(mm.floors[i]!.level); });
  });

  it.each(floorFacts.map(f => f.key))('floor %s: colliders, walkables, late, rise and children equal the page', key => {
    const ff = floorFacts.find(f => f.key === key)!;
    const f = built.floors.find(x => x.key === key)!;
    const mine = f.colliders.map(c => ({ name: c.name, vertices: vcount(c) }));
    if (names === 'exact') {
      expect(mine).toEqual(ff.colliders.map(c => ({ name: c.name, vertices: c.vertices })));
      expect(f.rise.map(r => ({ name: r.mesh.name, scales: r.scales }))).toEqual(ff.rise.length ? ff.rise : f.rise.map(r => ({ name: r.mesh.name, scales: r.scales })));
    } else {
      // the suite page's seven meshes `solid`, `low` ... are `suite solid:follow`, `suite low:own` ... (one each here too)
      const mapped = ff.colliders.map(c => {
        const hits = mine.filter(x => x.name.startsWith(`${key} ${c.name}:`));
        expect(hits, c.name).toHaveLength(1);
        return { name: hits[0]!.name, vertices: c.vertices };
      });
      expect(mine).toEqual(expect.arrayContaining(mapped));
      expect(mine).toHaveLength(mapped.length);
    }
    expect(sum(mine.map(c => c.vertices))).toBe(ff.colliderVertices);
    expect(f.walkables.map(vcount)).toEqual(ff.walkables.map(w => w.vertices));
    expect(sum(f.walkables.map(vcount))).toBe(ff.walkableVertices);
    expect(f.late).toHaveLength(ff.lateWithoutFurniture);
    expect(f.group.children).toHaveLength(ff.groupChildren - (ff.late - ff.lateWithoutFurniture));
  });

  it('the tick lists have the page\'s sizes', () => {
    for (const [tick, list] of Object.entries(built.toggleObjects)) {
      const flip = facts.ticksFlip[tick];
      if (flip) expect(list.length, tick).toBe(flip.objects);
      else expect(list.length, tick).toBe(0);
    }
  });

  it('mesh names follow `<floor> <mesh>:<fit>`, the floor plates and stairs theirs', () => {
    for (const f of built.floors) {
      for (const r of f.rise) {
        expect(r.mesh.name).toMatch(new RegExp(`^${f.key} [a-z]+:(follow|own|top|clip)$`));
        expect(r.edges?.name).toBe(`${r.mesh.name} edges`);
      }
      for (const w of f.walkables) expect(w.name).toBe(`${f.key} floor plate`);
      for (const o of f.late) expect(o.name).toMatch(new RegExp(`^${f.key} (floor plate|tread lines|stair lines above|stair panels)$`));
    }
  });
});

describe('buildScene(house): the v1 values of DESIGN.md 17.2 (three 0.186.1, the provisional house model)', () => {
  const { built } = build('house', 'sukhumvit-house');
  const [ground, upper] = built.floors;
  const names = (ms: Mesh[]) => ms.map(m => m.name.replace(/^\w+ /, '')).sort();
  it('ground: 7 colliders with 6,936 vertices, 3 walkables (792), 4 late, 4 fitted', () => {
    expect(names(ground!.colliders)).toEqual(['glass:follow', 'pane:clip', 'pane:top', 'sill:clip', 'single:own', 'solid:follow', 'solid:top']);
    expect(sum(ground!.colliders.map(vcount))).toBe(6936);
    expect(ground!.walkables).toHaveLength(3);
    expect(sum(ground!.walkables.map(vcount))).toBe(792);
    expect(ground!.late).toHaveLength(4);
    expect(built.fitted.ground).toHaveLength(4);
  });
  it('upper: 5 colliders with 6,372 vertices, 1 walkable (588), 2 late, 2 fitted', () => {
    expect(names(upper!.colliders)).toEqual(['glass:follow', 'pane:clip', 'single:own', 'solid:follow', 'solid:top']);
    expect(sum(upper!.colliders.map(vcount))).toBe(6372);
    expect(upper!.walkables).toHaveLength(1);
    expect(sum(upper!.walkables.map(vcount))).toBe(588);
    expect(upper!.late).toHaveLength(2);
    expect(built.fitted.upper).toHaveLength(2);
  });
  it('ticks: plates 4 objects, glass 10, single 4; plinths 3; the ground plane', () => {
    expect(built.toggleObjects.plates).toHaveLength(4);
    expect(built.toggleObjects.glass).toHaveLength(10);
    expect(built.toggleObjects.single).toHaveLength(4);
    expect(built.plinths).toHaveLength(3);
    expect(built.groundPlane?.name).toBe('ground plane');
    expect((built.groundPlane!.material as MeshStandardMaterial).side).toBe(FrontSide);
    expect(built.groundPlane!.rotation.x).toBeCloseTo(-Math.PI / 2, 12);
    expect(built.floors.some(f => f.group.children.includes(built.groundPlane!))).toBe(false);
  });
  it('the house styles: glass and panes renderOrder 0, opacity 0.35; single 0.9 see-through; crease 40', () => {
    const glass = ground!.colliders.find(m => m.name === 'ground glass:follow')!;
    const pane = ground!.colliders.find(m => m.name === 'ground pane:top')!;
    const single = ground!.colliders.find(m => m.name === 'ground single:own')!;
    for (const m of [glass, pane]) {
      expect(m.renderOrder).toBe(0);
      const mat = m.material as MeshStandardMaterial;
      expect([mat.opacity, mat.transparent, mat.depthWrite, mat.roughness]).toEqual([0.35, true, false, 0.85]);
    }
    expect((single.material as MeshStandardMaterial).opacity).toBe(0.9);
    expect((ground!.rise.find(r => r.mesh === glass)!.edges!.material as Material & { opacity: number }).opacity).toBe(0.6);
  });
  it('the mesh classes of the ported checks find their meshes (tests/e2e/lib/target.ts app names)', () => {
    const all = built.floors.flatMap(f => f.colliders.map(c => c.name));
    expect(all.filter(n => / solid:follow$/.test(n))).toHaveLength(2);
    expect(all.filter(n => / solid:top$/.test(n))).toHaveLength(2);
    expect(all.filter(n => / pane:(top|clip)$/.test(n))).toHaveLength(3);
    expect(all.filter(n => / glass:follow$/.test(n))).toHaveLength(2);
    expect(all.filter(n => / single:own$/.test(n))).toHaveLength(2);
  });
});

describe('buildScene(features.model.json): every kind, fit, plinth, panels, deck', () => {
  const m = model('packages/viewer/test/fixtures/features.model.json');
  const pres = presentationOf('sukhumvit-house', m);
  const built = buildScene(m, { ...pres, partStyles: presentationOf(null, m).partStyles, creaseAngle: 25 });
  const [G, U] = built.floors;
  const byName = (name: string) => built.floors.flatMap(f => f.group.children).find(o => o.name === name) as Mesh;

  it('one mesh per mesh group and fit, in the order the groups first occur', () => {
    expect(G!.rise.map(r => r.mesh.name)).toEqual(['G solid:follow', 'G solid:top', 'G sill:clip', 'G pane:top', 'G pane:clip', 'G glass:own',
      'G mullion:own', 'G railing:own', 'G single:own', 'G step:own']);
    expect(U!.rise.map(r => r.mesh.name)).toEqual(['U solid:follow', 'U parapet:own', 'U balustrade:own', 'U low:own', 'U builtin:follow',
      'U deck:own', 'U post:own']);
    expect(G!.rise.map(r => [r.fit, r.scales])).toEqual([['scale', true], ['top', false], ['clip', false], ['top', false], ['clip', false],
      ['fixed', false], ['fixed', false], ['fixed', false], ['fixed', false], ['fixed', false]]);
  });
  it('fitName / fitOf: follow, own, top, clip', () => {
    expect(m.parts.map(p => fitName(fitOf(p)))).toContain('top');
    expect([fitName('scale'), fitName('fixed'), fitName('top'), fitName('clip')]).toEqual(['follow', 'own', 'top', 'clip']);
  });
  it('a deck is walked over, not into: no collider; everything else is', () => {
    expect(U!.colliders.map(c => c.name)).not.toContain('U deck:own');
    expect(U!.rise.map(r => r.mesh.name)).toContain('U deck:own');
    // drawn in front of the floor plate it lies on (the plate's polygonOffset is -1): -2, and no other part has one
    const offsets = built.floors.flatMap(f => f.rise.map(r => r.mesh)).map(o => {
      const mat = o.material as MeshStandardMaterial;
      return [o.name, mat.polygonOffset ? [mat.polygonOffsetFactor, mat.polygonOffsetUnits] : null];
    }).filter(([, po]) => po !== null);
    expect(offsets).toEqual([['U deck:own', [-2, -2]]]);
    expect(G!.colliders.map(c => c.name)).toEqual(['G solid:follow', 'G solid:top', 'G sill:clip', 'G pane:top', 'G pane:clip', 'G glass:own',
      'G mullion:own', 'G railing:own', 'G single:own', 'G step:own', 'G walk skins', 'G walk skins (glass)']);
  });
  it('skins: invisible, merged per kind; the glass skins go with the Glass tick', () => {
    const skin = byName('G walk skins'), glassSkin = byName('G walk skins (glass)');
    expect((skin.material as Material).visible).toBe(false);
    expect(built.toggleObjects.glass).toContain(glassSkin);
    expect(built.toggleObjects.glass).not.toContain(skin);
  });
  it('the Glass tick takes glass, panes and the balustrade (meshes and edges); Single-line the single parts', () => {
    const glassNames = built.toggleObjects.glass.map(o => o.name).sort();
    expect(glassNames).toEqual(['G glass:own', 'G glass:own edges', 'G pane:clip', 'G pane:clip edges', 'G pane:top', 'G pane:top edges',
      'G walk skins (glass)', 'U balustrade:own', 'U balustrade:own edges']);
    expect(built.toggleObjects.single.map(o => o.name)).toEqual(['G single:own', 'G single:own edges']);
  });
  it('materials: standard DoubleSide, glass transparent with renderOrder 3, railing see-through 0.5 renderOrder 2; edges', () => {
    const solid = byName('G solid:follow'), glass = byName('G glass:own'), railing = byName('G railing:own');
    const ms = (o: Mesh) => o.material as MeshStandardMaterial;
    expect([ms(solid).side, ms(solid).roughness, ms(solid).transparent, solid.renderOrder]).toEqual([DoubleSide, 0.85, false, 0]);
    expect([ms(glass).opacity, ms(glass).transparent, ms(glass).depthWrite, ms(glass).roughness, ms(glass).metalness, glass.renderOrder])
      .toEqual([0.3, true, false, 0.15, 0, 3]);
    expect([ms(railing).opacity, ms(railing).roughness, ms(railing).metalness, railing.renderOrder]).toEqual([0.5, 0.6, 0.2, 2]);
    expect(byName('U balustrade:own').renderOrder).toBe(3);
    const glassEdges = byName('G glass:own edges') as unknown as LineSegments;
    expect((glassEdges.material as Material & { opacity: number }).opacity).toBe(0.45);
    expect((byName('G solid:follow edges') as unknown as LineSegments).isLineSegments).toBe(true);
    const distinct = new Set(built.floors.flatMap(f => f.rise.map(r => r.mesh.material)));
    expect(distinct.size).toBe(G!.rise.length + U!.rise.length);           // one material per mesh (the replay patches each)
  });
  it('floor plates: one per slab part, FrontSide, polygonOffset -1, walkable and late, not colliders; the plinth', () => {
    for (const f of built.floors) for (const w of f.walkables) {
      const mat = w.material as MeshStandardMaterial;
      expect([mat.side, mat.polygonOffset, mat.polygonOffsetFactor, mat.polygonOffsetUnits, mat.roughness]).toEqual([FrontSide, true, -1, -1, 0.95]);
      expect(f.colliders).not.toContain(w);
      expect(f.late).toContain(w);
      expect(w.geometry.boundsTree).toBeDefined();
    }
    expect(built.plinths).toEqual([G!.walkables[0]]);
    expect(built.plinths[0]!.userData.floor).toBe('G');
  });
  it('stairs: tread strips at +0.012, faint lines above at +0.02, 0.15 m panels; all late', () => {
    const below = byName('G tread lines'), above = byName('G stair lines above'), panels = byName('U stair panels');
    const ys = (o: Mesh) => { const a = o.geometry.getAttribute('position'); const out = new Set<number>(); for (let i = 0; i < a.count; i++) out.add(Math.round(a.getY(i) * 1e4) / 1e4); return [...out].sort((x, y) => x - y); };
    expect(ys(below)).toEqual([0.612]);
    expect(ys(above)).toEqual([0.62]);
    expect(ys(panels)).toEqual([3.6, 3.75]);
    expect(below.geometry.getAttribute('position').count).toBe(12);           // 2 lines x 2 triangles
    expect((above as unknown as LineSegments).isLineSegments).toBe(true);
    expect(G!.late.map(o => o.name)).toEqual(['G floor plate', 'G tread lines', 'G stair lines above']);
    expect(U!.late.map(o => o.name)).toEqual(['U floor plate', 'U stair panels']);
  });
  it('geometry at the model level, plan (x, y) -> (x, z = -y); aDelay 0 - 1 over the non-slab parts, west to east', () => {
    const solid = byName('G solid:follow');
    solid.geometry.computeBoundingBox();
    const b = solid.geometry.boundingBox!;
    expect([b.min.x, b.max.x, b.min.y, b.max.y, b.min.z, b.max.z].map(v => Math.round(v * 1e6) / 1e6)).toEqual([0, 10, 0.6, 3.6, -8, 0]);
    let lo = 1, hi = 0;
    for (const f of built.floors) for (const r of f.rise) {
      const d = r.mesh.geometry.getAttribute('aDelay');
      expect(d.count).toBe(r.mesh.geometry.getAttribute('position').count);
      for (let i = 0; i < d.count; i++) { lo = Math.min(lo, d.getX(i)); hi = Math.max(hi, d.getX(i)); }
    }
    expect(lo).toBeGreaterThanOrEqual(0);
    expect(hi).toBeLessThanOrEqual(1);
    expect(hi - lo).toBeGreaterThan(0.5);
  });
  it('fitted meshes carry their per-vertex base, z0 / z1 and centre, edges too', () => {
    expect(built.fitted.G!.map(x => x.name)).toEqual(['G solid:top', 'G sill:clip', 'G pane:top', 'G pane:clip']);
    expect(built.fitted.U).toEqual([]);
    for (const mesh of built.fitted.G!) {
      const d = fitDataOf(mesh.geometry)!;
      expect(d.level).toBe(0.6);
      expect(d.base.length).toBe(mesh.geometry.getAttribute('position').count * 3);
      const edges = G!.rise.find(r => r.mesh === mesh)!.edges!;
      expect(fitDataOf(edges.geometry)!.base.length).toBe(edges.geometry.getAttribute('position').count * 3);
    }
    const lintel = fitDataOf(byName('G solid:top').geometry)!;
    expect([lintel.fit, lintel.z0[0], lintel.z1[0], lintel.cx[0], lintel.cz[0]]).toEqual(['top', expect.closeTo(2.1, 6), 3, 4.5, expect.closeTo(-0.1, 6)]);
  });
  it('every collider and walkable has its own BVH and raycast (no prototype patching)', () => {
    for (const f of built.floors) for (const m of [...f.colliders, ...f.walkables]) {
      expect(m.geometry.boundsTree).toBeDefined();
      expect(Object.prototype.hasOwnProperty.call(m, 'raycast')).toBe(true);
    }
    expect(Object.prototype.hasOwnProperty.call(Mesh.prototype, 'raycast')).toBe(true);
    expect(Mesh.prototype.raycast.name).not.toBe('acceleratedRaycast');
  });
});
