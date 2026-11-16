// The furniture pick (docs/boxes/DESIGN.md 2.2; taken out of hover.ts): the box under a screen point. Owner: builder C.
//   The nearest thing on the ray among the showing boxes and what hides them (walls, floor plates; glass, half see-through
//   and the invisible Walk skins hide nothing): a box, or null (nothing, or something in front of it). A deleted box, a
//   box of a hidden kind and a box of a hidden floor are not showing, so they are never picked. The hover label (hover.ts),
//   the Orbit click and the Walk / Ghost aim at the crosshair (select.ts) all use it.
import { Raycaster, Vector2, type Material, type Mesh, type Object3D } from 'three';
import type {} from 'three-mesh-bvh';
import type { ViewerContext } from '../contracts';
import type { FurnitureState, ItemState } from './types';

export interface Picker {
  /** A client (viewport) point as a root-relative one (all screen maths is root-relative). */
  rootPoint(clientX: number, clientY: number): { x: number; y: number };
  /** The box under a root-relative point; null also when the canvas has no size. */
  atRoot(x: number, y: number): ItemState | null;
  /** The box under a client (viewport) point. */
  atClient(clientX: number, clientY: number): ItemState | null;
  /** The box at the middle of the view (the Walk / Ghost crosshair), at most `reach` m from the eye. */
  atCentre(reach: number): ItemState | null;
}

/** Drawn now: the object and every parent are visible. */
export const showing = (obj: Object3D | null): boolean => { for (let n = obj; n; n = n.parent) if (!n.visible) return false; return true; };
const materialOf = (m: Mesh): Material | undefined => (Array.isArray(m.material) ? m.material[0] : m.material);

export function makePicker(ctx: ViewerContext, st: FurnitureState): Picker {
  const ray = new Raycaster(), ndc = new Vector2();
  ray.firstHitOnly = true;
  const pieceOf = (m: Object3D): ItemState | null => {
    const p = st.itemOf.get(String(m.userData.id));
    return p && p.mesh === m ? p : null;
  };
  function atNdc(nx: number, ny: number, reach: number): ItemState | null {
    ctx.camera.updateMatrixWorld();                                  // as the last frame drew it (a no-op between frames)
    ray.far = reach;
    ray.setFromCamera(ndc.set(nx, ny), ctx.camera);
    // The nearest thing on the ray among the boxes and what hides them (walls, floor plates; glass and the invisible
    // Walk skins do not hide anything).
    const hides = ctx.floors.filter(f => showing(f.group)).flatMap(f => f.colliders.concat(f.walkables))
      .filter(m => { const mat = materialOf(m); return !pieceOf(m) && !!mat && mat.visible !== false && !mat.transparent && showing(m); });
    const hit = ray.intersectObjects([...st.items.map(p => p.mesh).filter(showing), ...hides], false)[0];
    return hit ? pieceOf(hit.object) : null;
  }
  const rootPoint = (clientX: number, clientY: number) => {
    const base = ctx.ui.root.getBoundingClientRect();
    return { x: clientX - base.left, y: clientY - base.top };
  };
  function atRoot(x: number, y: number): ItemState | null {
    const r = ctx.rectOf(ctx.canvas);
    if (!r.width || !r.height) return null;
    return atNdc((x - r.left) / r.width * 2 - 1, -(y - r.top) / r.height * 2 + 1, Infinity);
  }
  return {
    rootPoint, atRoot,
    atClient: (clientX, clientY) => { const at = rootPoint(clientX, clientY); return atRoot(at.x, at.y); },
    atCentre: reach => atNdc(0, 0, reach),
  };
}
