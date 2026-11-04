// Fix step (review finding "parity-cad" 1): the transparent draw order of three 0.160 (the prototype pages), kept on three
// 0.186. three 0.186 keys the back-to-front sort on the clip-space z of each object's bounding-sphere centre (no divide by
// w), which flips the order of an object whose centre is behind the eye; core/sort.ts sorts by the NDC depth, as 0.160.
import { BoxGeometry, Matrix4, Mesh, MeshBasicMaterial, PerspectiveCamera, Scene, Vector4, type Object3D } from 'three';
import { describe, expect, it } from 'vitest';
import { ndcDepth, prototypeSort, usePrototypeTransparentSort, type SortItem } from '../../../src/core/sort';
import { kitContext } from './kit';

/** three 0.186's own key: the clip-space z of the bounding-sphere centre, before the divide. */
function clipZ(o: Mesh, camera: PerspectiveCamera): number {
  if (!o.geometry.boundingSphere) o.geometry.computeBoundingSphere();
  const m = new Matrix4().multiplyMatrices(camera.projectionMatrix, camera.matrixWorldInverse);
  return new Vector4().copy(o.geometry.boundingSphere!.center as unknown as Vector4).setW(1).applyMatrix4(o.matrixWorld).applyMatrix4(m).z;
}

let nextId = 1;
const item = (o: Mesh, camera: PerspectiveCamera, renderOrder = 0): SortItem => {
  if (!o.geometry.boundingSphere) o.geometry.computeBoundingSphere();
  return { id: nextId++, object: o as SortItem['object'], geometry: o.geometry, groupOrder: 0, renderOrder, z: clipZ(o, camera) };
};
/** three 0.186's reversePainterSortStable, for comparison. */
const threeOwn = (a: SortItem, b: SortItem) => a.groupOrder - b.groupOrder || a.renderOrder - b.renderOrder || (b.z - a.z) || a.id - b.id;

function eye(): PerspectiveCamera {
  const camera = new PerspectiveCamera(60, 1.5, 0.1, 1000);    // at the origin, looking down -z
  camera.updateMatrixWorld();
  return camera;
}
function mesh(z: number, depth: number): Mesh {
  const m = new Mesh(new BoxGeometry(1, 1, depth), new MeshBasicMaterial({ transparent: true, opacity: 0.5 }));
  m.position.set(0, 0, z);
  m.updateMatrixWorld();
  return m;
}

describe('prototypeSort: three 0.160 order of transparent objects', () => {
  it('an object whose centre is behind the eye is drawn first (0.160), not last (0.186)', () => {
    const camera = eye();
    const behind = mesh(2, 12);          // spans z -4 .. 8: seen in front of the eye, its centre behind it
    const front = mesh(-5, 1);
    const items = [item(front, camera), item(behind, camera)];
    expect([...items].sort(threeOwn).map(i => i.object)).toEqual([front, behind]);     // 0.186: the merged mesh last
    const sort = prototypeSort();
    sort.begin(camera);
    expect([...items].sort(sort.compare).map(i => i.object)).toEqual([behind, front]); // 0.160: first (NDC z > 1)
    expect(ndcDepth(items[1]!, new Matrix4().multiplyMatrices(camera.projectionMatrix, camera.matrixWorldInverse))).toBeGreaterThan(1);
  });

  it('in front of the eye both orders agree: far to near; renderOrder and groupOrder still come first', () => {
    const camera = eye();
    const near = mesh(-3, 1), far = mesh(-20, 1);
    const sort = prototypeSort();
    sort.begin(camera);
    const a = item(near, camera), b = item(far, camera);
    expect([a, b].sort(sort.compare).map(i => i.object)).toEqual([far, near]);
    expect([a, b].sort(threeOwn).map(i => i.object)).toEqual([far, near]);
    const late = item(far, camera, 1);
    expect([late, a].sort(sort.compare).map(i => i.object)).toEqual([near, far]);
    const grouped = { ...item(near, camera), groupOrder: -1 };
    expect([b, grouped].sort(sort.compare)[0]).toBe(grouped);
  });

  it('follows the camera of each render: scene.onBeforeRender hands it over, and a renderer gets the comparator', () => {
    const scene = new Scene();
    let compare: ((a: SortItem, b: SortItem) => number) | null = null;
    usePrototypeTransparentSort({ setTransparentSort(fn) { compare = fn; } }, scene);
    const camera = eye();
    const behind = mesh(2, 12), front = mesh(-5, 1);
    const items = [item(front, camera), item(behind, camera)];
    (scene.onBeforeRender as unknown as (...a: unknown[]) => void)(null, scene, camera, null);
    expect([...items].sort(compare!).map(i => i.object)).toEqual([behind, front]);
    const turned = eye();                                        // the same eye looking the other way (+z)
    turned.rotation.y = Math.PI;
    turned.updateMatrixWorld();
    (scene.onBeforeRender as unknown as (...a: unknown[]) => void)(null, scene, turned, null);
    const again = [item(front, turned), item(behind, turned)];
    expect(again.sort(compare!).map(i => i.object)).toEqual([front, behind]);  // `front` is behind this eye now
  });
});

describe('the house: the first Walk view (x 0, z 0.47, yaw -114.5 deg, eye 1.6 m)', () => {
  it("draws the window panes before the single-line piece seen through them, as the prototype page did", () => {
    const ctx = kitContext('house');
    const byName = (name: string) => {
      let found: Object3D | undefined;
      ctx.scene.traverse(o => { if (o.name === name) found = o; });
      expect(found, name).toBeDefined();
      return found as Mesh;
    };
    const pane = byName('ground pane:clip'), single = byName('ground single:own');
    const level = ctx.floors.find(f => f.key === 'ground')!.level;
    const camera = new PerspectiveCamera(60, 1400 / 880, 0.1, 500);
    camera.position.set(0, level + 1.6, 0.47);
    camera.rotation.set(0, -114.5 * Math.PI / 180, 0, 'YXZ');
    ctx.scene.updateMatrixWorld(true);
    camera.updateMatrixWorld();
    const items = [item(single, camera), item(pane, camera)];
    expect([...items].sort(threeOwn).map(i => i.object.name)).toEqual(['ground single:own', 'ground pane:clip']);
    const sort = prototypeSort();
    sort.begin(camera);
    expect([...items].sort(sort.compare).map(i => i.object.name)).toEqual(['ground pane:clip', 'ground single:own']);
  });
});
