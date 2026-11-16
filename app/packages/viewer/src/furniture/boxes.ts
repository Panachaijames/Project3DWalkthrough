// Furniture boxes: one unit box per piece, its materials, its placement and the colliders sync (DESIGN.md 12, 13;
// furniture_boxes.js "the boxes", place, sync). Owner: builder C.
//   Boxes   a unit box (1 m each way, base at y = 0) scaled to w x height x d and turned by rot, at (x, modelLevel + z0, -y)
//           in its floor's group (the Build settings move the group, so the box follows); named 'furn:<kind>:<id>'; in its
//           floor's 'late' list (it appears at the end of the build replay, like the floor plates).
//   Faces   MeshStandardMaterial(roughness 0.85, FrontSide, polygonOffset 1 / 1): single-sided, so Walk's rays from inside a
//           box meet none of its faces and a player whose eye is inside one walks out; a little behind their outline, so the
//           thin darker edges (colour x 0.4) are never eaten by them. No bounds tree (12 triangles).
//   Walk    a box is in its floor's colliders only while it stops you (stopsWalk); the arrays are the very ones Walk uses.
//   Deleted a deleted box (docs/boxes/DESIGN.md 2.4, 2.7) keeps its mesh: it is hidden, never a collider, and out of its
//           floor's 'late' list, so the build replay's fade never shows it (setRemoved, syncKind).
import { BoxGeometry, Color, EdgesGeometry, FrontSide, LineBasicMaterial, LineSegments, Mesh, MeshStandardMaterial } from 'three';
import type { ViewerContext } from '../contracts';
import type { ItemState, KindState, PieceDraft } from './types';

const D2R = Math.PI / 180;

/**
 * Makes the box of every piece, kind by kind (each kind's materials first, then its pieces in model order), puts it in its
 * floor group and 'late' list (not placed yet) and its item in its kind's `items`. Returns the items in the pieces' order.
 * An item is made together with its mesh, so none exists without one (fix step, first code review finding 14: the items
 * were made with `mesh: null` cast to Mesh and filled in here).
 */
export function makeBoxes(ctx: ViewerContext, kinds: KindState[], pieces: readonly PieceDraft[]): ItemState[] {
  const unit = ctx.disposer.track(new BoxGeometry(1, 1, 1).translate(0, 0.5, 0));
  const outline = ctx.disposer.track(new EdgesGeometry(unit));
  const made = new Map<PieceDraft, ItemState>();
  for (const k of kinds) {
    k.face = ctx.disposer.track(new MeshStandardMaterial({
      color: k.colour, roughness: 0.85, side: FrontSide, polygonOffset: true, polygonOffsetFactor: 1, polygonOffsetUnits: 1,
    }));
    k.edge = ctx.disposer.track(new LineBasicMaterial({ color: new Color(k.colour).multiplyScalar(0.4) }));
    for (const p of pieces) {
      if (p.kind !== k) continue;
      const m = new Mesh(unit, k.face);
      m.name = `furn:${k.key}:${p.d.id}`;
      m.rotation.y = p.d.rot * D2R;
      m.add(new LineSegments(outline, k.edge));
      m.userData = { id: p.d.id, kind: k.key, family: p.d.family, floor: p.d.floor, size: [] };
      const item: ItemState = { ...p, mesh: m, z0mm: 0, removed: false };
      k.items.push(item);
      made.set(p, item);
      p.fl.group.add(m);
      p.fl.late.push(m);
    }
  }
  return pieces.map(p => {
    const item = made.get(p);
    if (!item) throw new Error(`furniture: the kind of piece ${p.d.id} is not among the kinds given`);
    return item;
  });
}

/** Position, size and matrices of one box; z0mm is its resolved underside (mm). */
export function placeBox(p: ItemState, z0mm: number): void {
  const { d, mesh } = p, h = p.kind.height / 1000;
  p.z0mm = z0mm;
  mesh.position.set(d.x, p.fl.modelLevel + z0mm / 1000, -d.y);    // plan (x, y) -> three.js (x, z = -y)
  mesh.scale.set(d.w, h, d.d);
  mesh.userData.size = [d.w, d.d, h];
  mesh.updateWorldMatrix(true, true);                              // Walk and the hover label may raycast before the next frame
}

/**
 * The kind's show tick on its boxes (a deleted box is never shown), and each box in or out of its floor's colliders as
 * `stops` says. `replay`: the build replay is running and owns the visibility of the late objects, so only a deleted box
 * is hidden here; the replay's closing apply() shows the rest (docs/boxes/DESIGN.md 2.7).
 */
export function syncKind(k: KindState, stops: (p: ItemState) => boolean, replay = false): void {
  for (const p of k.items) {
    const col = p.fl.colliders, i = col.indexOf(p.mesh), want = stops(p);
    if (p.removed) p.mesh.visible = false;
    else if (!replay) p.mesh.visible = k.visible;
    if (want && i < 0) col.push(p.mesh);
    else if (!want && i >= 0) col.splice(i, 1);
  }
}

/**
 * Marks a piece deleted or back (docs/boxes/DESIGN.md 2.7): a deleted box leaves its floor's 'late' list (the replay fades
 * in whatever is in it), a restored one is pushed back. syncKind then hides or shows it and takes it out of the colliders.
 */
export function setRemoved(p: ItemState, on: boolean): void {
  p.removed = on;
  const late = p.fl.late, i = late.indexOf(p.mesh);
  if (on && i >= 0) late.splice(i, 1);
  else if (!on && i < 0) late.push(p.mesh);
}

/**
 * A kind whose every box is deleted has no mesh left in a 'late' list, so a replay that was fading when the last one went
 * never gives its two materials their own look back: apply() does (they are opaque, as makeBoxes made them).
 */
export function restoreLook(k: KindState): void {
  if (k.items.some(p => !p.removed)) return;
  for (const m of [k.face, k.edge]) {
    if (!m) continue;
    m.opacity = 1;
    if (m.transparent) { m.transparent = false; m.needsUpdate = true; }
  }
}
