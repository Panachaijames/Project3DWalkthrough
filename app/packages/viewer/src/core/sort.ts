// The prototypes' draw order of transparent objects (three 0.160), kept with three 0.186. Owner: A (fix step, review
// finding "parity-cad" 1).
//
// three sorts the transparent render list back to front by a depth per object: the centre of its bounding sphere, through
// the camera's projection. three 0.160 (the prototype pages) used that point's NDC depth (Vector3.applyMatrix4 divides by
// w); three 0.186 uses its clip-space z before the divide (WebGLRenderer projectObject, `_vector4`). For a point in front of
// the eye both give the same order; for a point BEHIND the eye they flip: 0.160 drew such an object first (NDC z > 1, the
// farthest), 0.186 draws it last. A merged mesh (all of a floor's window panes, say) often has its centre behind the eye in
// Walk and Ghost: the house's first Walk view then drew the pane over the single-line piece seen through it (a grey-green
// band) where the page drew the piece over the pane (orange). This puts back 0.160's key: the same comparator as three's
// reversePainterSortStable (groupOrder, renderOrder, depth far to near, id), with the NDC depth.
import {
  Matrix4, Vector3, type BufferGeometry, type Camera, type Object3D, type Scene, type Sphere, type WebGLRenderer,
} from 'three';

/** The fields of three's RenderItem the comparator reads. */
export interface SortItem {
  id: number;
  object: Object3D & { boundingSphere?: Sphere | null };
  geometry: BufferGeometry | null;
  groupOrder: number;
  renderOrder: number;
  /** three 0.186's key (clip-space z): used only when the object has no bounding sphere. */
  z: number;
}

/** The NDC depth three 0.160 sorted by: the bounding-sphere centre through matrixWorld, then projection x view, divided by w. */
export function ndcDepth(item: SortItem, projScreen: Matrix4, out = new Vector3()): number {
  const o = item.object;
  const sphere = o.boundingSphere !== undefined ? o.boundingSphere : item.geometry?.boundingSphere;
  if (!sphere) return item.z;
  out.copy(sphere.center).applyMatrix4(o.matrixWorld).applyMatrix4(projScreen);
  return Number.isFinite(out.z) ? out.z : item.z;
}

export interface PrototypeSort {
  /** The transparent comparator (renderer.setTransparentSort). */
  readonly compare: (a: SortItem, b: SortItem) => number;
  /** What scene.onBeforeRender does: the camera of the render being sorted. */
  begin(camera: Camera): void;
}

export function prototypeSort(): PrototypeSort {
  const projScreen = new Matrix4(), v = new Vector3();
  let frame = 0;
  const keys = new WeakMap<object, { frame: number; z: number }>();
  const depth = (item: SortItem) => {
    const hit = keys.get(item.object);
    if (hit && hit.frame === frame) return hit.z;
    const z = ndcDepth(item, projScreen, v);
    keys.set(item.object, { frame, z });
    return z;
  };
  return {
    compare(a, b) {
      if (a.groupOrder !== b.groupOrder) return a.groupOrder - b.groupOrder;
      if (a.renderOrder !== b.renderOrder) return a.renderOrder - b.renderOrder;
      const za = depth(a), zb = depth(b);
      if (za !== zb) return zb - za;
      return a.id - b.id;
    },
    begin(camera) {
      // three calls scene.onBeforeRender after updating the camera's matrices and before it projects and sorts
      projScreen.multiplyMatrices(camera.projectionMatrix, camera.matrixWorldInverse);
      frame++;
    },
  };
}

/** Installs the prototypes' transparent order on a renderer drawing `scene` (any camera, photos included). */
export function usePrototypeTransparentSort(renderer: Pick<WebGLRenderer, 'setTransparentSort'>, scene: Scene): PrototypeSort {
  const sort = prototypeSort();
  const before = scene.onBeforeRender;
  (scene as unknown as { onBeforeRender: (r: unknown, s: unknown, camera: Camera, ...rest: unknown[]) => void }).onBeforeRender =
    function (this: Scene, r, s, camera, ...rest) {
      sort.begin(camera);
      (before as unknown as (...args: unknown[]) => void).call(this, r, s, camera, ...rest);
    };
  renderer.setTransparentSort(sort.compare);
  return sort;
}
