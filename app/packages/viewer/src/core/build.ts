// buildScene: pure three.js, Node-testable (DESIGN.md 5.4). Owner: builder A.
// Exactly the bank page's code generalised (bank_test/src/make_html.py), with the house page's fitted pieces, plinths and
// stair panels (cad_test/src/make_html_cad_merged.py) and the presentation's styles:
//  1. per floor, the non-slab parts grouped by `style.mesh + ':' + fitName` (follow / own / top / clip), in the order the
//     groups first occur; each part extruded with its sweep delay, the group merged, creased normals, edges (a fitted group's
//     edges per part, merged, so that every edge vertex knows its part), a BVH; one material per mesh (the replay patches
//     each mesh's shader with its own floor's uniforms);
//  2. collider skins, merged per floor into one invisible mesh each for the non-glass and the glass skins;
//  3. one mesh per slab part (`<key> floor plate`, FrontSide, polygonOffset -1), walkable and late;
//  4. stairs (late): tread strips, faint lines above, 0.15 m panels;
//  5. the ground plane (presentation.groundPlane), in no floor.
// The floor groups and the ground plane are not added to a scene here (viewer.ts does that).
import {
  BufferGeometry, Color, DoubleSide, EdgesGeometry, Float32BufferAttribute, FrontSide, Group, LineBasicMaterial,
  LineSegments, MathUtils, Mesh, MeshBasicMaterial, MeshStandardMaterial, PlaneGeometry, type MeshStandardMaterialParameters,
} from 'three';
import { mergeGeometries, toCreasedNormals } from 'three/addons/utils/BufferGeometryUtils.js';
import type { BuildScene, BuiltScene, FitMode, FloorRecord, Part, PartStyle } from '../contracts';
import { extrudePart, planBounds, ringCentre, sweepDelay, type PlanBounds } from '../model/geometry';
import { withBvh } from './bvh';

/** fit ?? (follow ? 'scale' : 'fixed') (contracts.ts FitMode). */
export const fitOf = (p: Part): FitMode => p.fit ?? (p.follow ? 'scale' : 'fixed');
/** The mesh-name suffix of a fit mode: follow (scale), own (fixed), top, clip. */
export const fitName = (fit: FitMode): string => (fit === 'scale' ? 'follow' : fit === 'fixed' ? 'own' : fit);

/**
 * Per-vertex data of a fitted mesh or edges geometry (geometry.userData[FIT_KEY]), in the merged vertex order: the base
 * positions (as built, at the model level), and per vertex its part's z0 / z1 (m above the floor) and outline centre
 * (three.js x, z). core/heights.ts refits from these.
 */
export interface FitData {
  fit: 'top' | 'clip';
  /** The floor's model level (the geometry was built there). */
  level: number;
  base: Float32Array;
  z0: Float32Array;
  z1: Float32Array;
  cx: Float32Array;
  cz: Float32Array;
}
export const FIT_KEY = 'wtvFit';

const STAIR_BELOW = 0x3f8f4f, STAIR_LINES = 0x5aa65a;

function mergeAll(geos: BufferGeometry[], what: string): BufferGeometry {
  const merged = mergeGeometries(geos, false);
  if (!merged) throw new Error(`[viewer] build: could not merge ${what}`);
  return merged;
}

function fitData(fit: 'top' | 'clip', level: number, geometry: BufferGeometry, parts: Part[], counts: number[]): FitData {
  const base = Float32Array.from(geometry.getAttribute('position').array as ArrayLike<number>);
  const n = base.length / 3;
  const d: FitData = { fit, level, base, z0: new Float32Array(n), z1: new Float32Array(n), cx: new Float32Array(n), cz: new Float32Array(n) };
  let i = 0;
  parts.forEach((p, k) => {
    const [cx, cy] = ringCentre(p.o);
    for (let j = 0; j < counts[k]!; j++, i++) { d.z0[i] = p.z0; d.z1[i] = p.z1; d.cx[i] = cx; d.cz[i] = -cy; }
  });
  if (i !== n) throw new Error(`[viewer] build: fitted vertex count ${i} is not the merged ${n}`);
  return d;
}

/** "standard" (5.4): MeshStandardMaterial({ color, roughness 0.85, DoubleSide }), transparent with depthWrite false below opacity 1. */
export function partMaterial(style: PartStyle): MeshStandardMaterial {
  const opacity = style.see ?? style.opacity ?? 1;
  const params: MeshStandardMaterialParameters = { color: new Color(style.color), roughness: style.roughness ?? 0.85, side: DoubleSide };
  if (style.metalness !== undefined) params.metalness = style.metalness;
  if (opacity < 1) { params.transparent = true; params.opacity = opacity; params.depthWrite = false; }
  return new MeshStandardMaterial(params);
}

export function edgeMaterial(style: PartStyle): LineBasicMaterial {
  return new LineBasicMaterial({ color: new Color(style.edge), transparent: true, opacity: style.edgeOpacity ?? (style.glass ? 0.45 : 0.6) });
}

/** Flat x1, y1, x2, y2 segments -> strips `hw` * 2 wide lying at y (the bank page's tread lines). */
function strips(a: number[], y: number, hw: number): BufferGeometry {
  const pos: number[] = [];
  for (let i = 0; i + 3 < a.length; i += 4) {
    const dx = a[i + 2]! - a[i]!, dy = a[i + 3]! - a[i + 1]!, L = Math.hypot(dx, dy) || 1, nx = -dy / L * hw, ny = dx / L * hw;
    const p = [a[i]! + nx, y, -(a[i + 1]! + ny)], q = [a[i + 2]! + nx, y, -(a[i + 3]! + ny)];
    const r = [a[i + 2]! - nx, y, -(a[i + 3]! - ny)], s = [a[i]! - nx, y, -(a[i + 1]! - ny)];
    pos.push(...p, ...q, ...r, ...p, ...r, ...s);
  }
  const g = new BufferGeometry();
  g.setAttribute('position', new Float32BufferAttribute(pos, 3));
  g.computeVertexNormals();
  return g;
}

/** Flat segments -> upright quads from y to y + h (the house page's stair panels). */
function panels(a: number[], y: number, h: number): BufferGeometry {
  const pos: number[] = [];
  for (let i = 0; i + 3 < a.length; i += 4) {
    const x1 = a[i]!, y1 = a[i + 1]!, x2 = a[i + 2]!, y2 = a[i + 3]!;
    const p = [x1, y, -y1], q = [x2, y, -y2], r = [x2, y + h, -y2], s = [x1, y + h, -y1];
    pos.push(...p, ...q, ...r, ...p, ...r, ...s);
  }
  const g = new BufferGeometry();
  g.setAttribute('position', new Float32BufferAttribute(pos, 3));
  g.computeVertexNormals();
  return g;
}

function lines(a: number[], y: number): BufferGeometry {
  const pos: number[] = [];
  for (let i = 0; i + 3 < a.length; i += 4) pos.push(a[i]!, y, -a[i + 1]!, a[i + 2]!, y, -a[i + 3]!);
  const g = new BufferGeometry();
  g.setAttribute('position', new Float32BufferAttribute(pos, 3));
  return g;
}

export const buildScene: BuildScene = (model, presentation) => {
  const crease = presentation.creaseAngle;
  const bounds: PlanBounds = planBounds(model.parts.filter(p => p.kind !== 'slab'));
  const delayOf = (o: Part['o']) => { const [cx, cy] = ringCentre(o); return sweepDelay(cx, cy, bounds); };
  const built: BuiltScene = { floors: [], toggleObjects: { plates: [], glass: [], single: [] }, plinths: [], groundPlane: null, fitted: {} };

  for (const f of model.floors) {
    const level = f.level;
    const group = new Group();
    group.name = f.key;
    const rec: FloorRecord = {
      key: f.key, name: f.name, level, modelLevel: level, wallHeight: f.wallHeight, stack: f.stack ?? 'main',
      group, colliders: [], walkables: [], late: [], rise: [],
    };
    built.floors.push(rec);
    const fitted: Mesh[] = (built.fitted[f.key] = []);

    // 1. the non-slab parts, merged per mesh group and fit
    const groups = new Map<string, { style: PartStyle; fit: FitMode; parts: Part[] }>();
    for (const p of model.parts) {
      if (p.floor !== f.key || p.kind === 'slab') continue;
      const style = presentation.partStyles[p.kind];
      const fit = fitOf(p);
      const name = `${style.mesh}:${fitName(fit)}`;
      let entry = groups.get(name);
      if (!entry) groups.set(name, (entry = { style, fit, parts: [] }));
      entry.parts.push(p);
    }
    for (const [name, { style, fit, parts }] of groups) {
      const geos = parts.map(p => extrudePart(p, level, delayOf(p.o)));
      const merged = mergeAll(geos, `${f.key} ${name}`);
      const g = toCreasedNormals(merged, MathUtils.degToRad(crease));
      let e: BufferGeometry;
      if (fit === 'top' || fit === 'clip') {
        const edgeGeos = geos.map(x => new EdgesGeometry(x, crease));
        e = mergeAll(edgeGeos, `${f.key} ${name} edges`);
        g.userData[FIT_KEY] = fitData(fit, level, g, parts, geos.map(x => x.getAttribute('position').count));
        e.userData[FIT_KEY] = fitData(fit, level, e, parts, edgeGeos.map(x => x.getAttribute('position').count));
        edgeGeos.forEach(x => x.dispose());
      } else {
        e = new EdgesGeometry(merged, crease);
      }
      geos.forEach(x => x.dispose());
      if (merged !== g) merged.dispose();
      const mesh = new Mesh(g, partMaterial(style));
      mesh.name = `${f.key} ${name}`;
      mesh.renderOrder = style.renderOrder ?? 0;
      // Walked on or over (collider false: decks) means lying on the floor plate, which is drawn in front by its own
      // polygonOffset (-1, 3. below): such parts go in front of it again (-2, as the plan pictures), or the suite's 2 cm
      // terrace decks vanish under the plate (integration: seen in the prototype / app screenshots, DESIGN.md 18.13).
      if (style.collider === false) {
        const m = mesh.material as MeshStandardMaterial;
        m.polygonOffset = true; m.polygonOffsetFactor = -2; m.polygonOffsetUnits = -2;
      }
      const edges = new LineSegments(e, edgeMaterial(style));
      edges.name = `${mesh.name} edges`;
      withBvh(mesh);
      group.add(mesh, edges);
      if (style.collider !== false) rec.colliders.push(mesh);
      if (style.glass) built.toggleObjects.glass.push(mesh, edges);
      if (style.single) built.toggleObjects.single.push(mesh, edges);
      rec.rise.push({ mesh, edges, scales: fit === 'scale', fit });
      if (fit === 'top' || fit === 'clip') fitted.push(mesh);
    }

    // 2. the collider skins: invisible, merged per floor, the glass ones switched with the Glass tick
    for (const glass of [false, true]) {
      const skins = (model.colliderSkins[f.key] ?? []).filter(s => !!s.glass === glass);
      if (!skins.length) continue;
      const geos = skins.map(s => extrudePart(s, level, delayOf(s.o)));
      const merged = mergeAll(geos, `${f.key} skins`);
      geos.forEach(x => x.dispose());
      const mesh = withBvh(new Mesh(merged, new MeshBasicMaterial({ visible: false })));
      mesh.name = `${f.key} walk skins${glass ? ' (glass)' : ''}`;
      group.add(mesh);
      rec.colliders.push(mesh);
      if (glass) built.toggleObjects.glass.push(mesh);
    }

    // 3. the floor plates: one mesh per slab part, drawn slightly in front (no flicker against the walls below)
    for (const p of model.parts) {
      if (p.floor !== f.key || p.kind !== 'slab') continue;
      const style = presentation.partStyles.slab;
      const g = extrudePart(p, level, delayOf(p.o));
      g.computeVertexNormals();
      const mesh = withBvh(new Mesh(g, new MeshStandardMaterial({
        color: new Color(style.color), roughness: style.roughness ?? 0.95, side: FrontSide,
        polygonOffset: true, polygonOffsetFactor: -1, polygonOffsetUnits: -1,
      })));
      mesh.name = `${f.key} floor plate`;
      mesh.userData.floor = f.key;
      group.add(mesh);
      rec.walkables.push(mesh);
      rec.late.push(mesh);
      built.toggleObjects.plates.push(mesh);
      if (p.plinth) built.plinths.push(mesh);
    }

    // 4. the stairs (all shown at the end of the replay)
    const st = model.stairs[f.key];
    if (st?.below.length) {
      const mesh = new Mesh(strips(st.below, level + 0.012, 0.015), new MeshStandardMaterial({ color: STAIR_BELOW, side: DoubleSide }));
      mesh.name = `${f.key} tread lines`;
      group.add(mesh); rec.late.push(mesh);
    }
    if (st?.above.length) {
      const seg = new LineSegments(lines(st.above, level + 0.02), new LineBasicMaterial({ color: STAIR_LINES, transparent: true, opacity: 0.35 }));
      seg.name = `${f.key} stair lines above`;
      group.add(seg); rec.late.push(seg);
    }
    if (st?.panels?.length) {
      const mesh = new Mesh(panels(st.panels, level, 0.15), new MeshStandardMaterial({ color: STAIR_LINES, side: DoubleSide }));
      mesh.name = `${f.key} stair panels`;
      group.add(mesh); rec.late.push(mesh);
    }
  }

  // 5. the ground plane (the house's 80 x 50 m), at y = 0, in the scene rather than a floor group
  if (presentation.groundPlane) {
    const [w, d] = presentation.groundPlane.size;
    const plane = new Mesh(new PlaneGeometry(w, d), new MeshStandardMaterial({ color: new Color(presentation.groundPlane.colour) }));
    plane.rotation.x = -Math.PI / 2;
    plane.name = 'ground plane';
    built.groundPlane = plane;
  }
  return built;
};

/** Typed access to a geometry's fit data (core/heights.ts, tests). */
export function fitDataOf(g: BufferGeometry): FitData | undefined {
  return g.userData[FIT_KEY] as FitData | undefined;
}
