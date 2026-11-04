// The label under the pointer, Orbit only (DESIGN.md 12, 13; furniture_boxes.js "the label under the pointer"). Owner: C.
//   At most 20 times a second (50 ms throttle; the last position always gets its turn), not while dragging, not for touch,
//   not in Walk or Ghost (a mode change hides it at once). The nearest thing under the pointer among the boxes and what hides
//   them (walls, floor plates; glass, half see-through and the invisible Walk skins hide nothing): a box gets a label with
//   its kind, family, size in m (w x d x height, ", from <z0> m" when it does not stand on the floor) and floor, and, while
//   the doorways are kept clear, "does not stop you: in the approach of <ids>". The label is absolute in the root, at the
//   pointer + 14 / 18 px, kept inside the root (all screen maths root-relative).
import { Raycaster, Vector2, type Material, type Mesh, type Object3D } from 'three';
import type {} from 'three-mesh-bvh';
import type { ViewerContext } from '../contracts';
import { clear, el } from '../ui/dom';
import type { FurnitureState, ItemState } from './types';

export interface HoverApi {
  readonly tip: HTMLDivElement;
  hide(): void;
}

const showing = (obj: Object3D | null) => { for (let n = obj; n; n = n.parent) if (!n.visible) return false; return true; };
const materialOf = (m: Mesh): Material | undefined => (Array.isArray(m.material) ? m.material[0] : m.material);

export function installHover(ctx: ViewerContext, st: FurnitureState): HoverApi {
  const tip = el('div', { wt: 'furniture-tip', style: { display: 'none' } });
  ctx.ui.root.append(tip);
  const ray = new Raycaster(), ndc = new Vector2();
  ray.firstHitOnly = true;
  let pending: { x: number; y: number } | null = null, timer = 0;
  const mode = () => ctx.modes.mode;
  const pieceOf = (m: Object3D): ItemState | null => {
    const p = st.itemOf.get(String(m.userData.id));
    return p && p.mesh === m ? p : null;
  };
  const hide = () => { pending = null; tip.style.display = 'none'; };

  function hover() {
    timer = 0;
    const at = pending;
    if (!at || mode() !== 'orbit') { hide(); return; }
    const base = ctx.ui.root.getBoundingClientRect(), r = ctx.rectOf(ctx.canvas);
    const x = at.x - base.left, y = at.y - base.top;                 // root-relative
    if (!r.width || !r.height) { tip.style.display = 'none'; return; }
    ctx.camera.updateMatrixWorld();                                  // as the last frame drew it (a no-op between frames)
    ray.setFromCamera(ndc.set((x - r.left) / r.width * 2 - 1, -(y - r.top) / r.height * 2 + 1), ctx.camera);
    // The nearest thing under the pointer among the boxes and what hides them (walls, floor plates; glass and the invisible
    // Walk skins do not hide anything).
    const hides = ctx.floors.filter(f => showing(f.group)).flatMap(f => f.colliders.concat(f.walkables))
      .filter(m => { const mat = materialOf(m); return !pieceOf(m) && !!mat && mat.visible !== false && !mat.transparent && showing(m); });
    const hit = ray.intersectObjects([...st.items.map(p => p.mesh).filter(showing), ...hides], false)[0];
    const p = hit ? pieceOf(hit.object) : null;
    if (!p) { tip.style.display = 'none'; return; }
    const d = p.d, h = p.kind.height / 1000, z0 = p.z0mm / 1000;
    const kept = st.keepDoorways() && p.kind.blocks && p.approach.length > 0;   // it would stop you, but the doorway it stands in front of is kept clear
    clear(tip);
    tip.append(
      el('b', { text: p.kind.label }), el('br'), d.family, el('br'),
      el('span', { text: `${d.w.toFixed(2)} × ${d.d.toFixed(2)} × ${h.toFixed(2)} m${z0 > 0 ? ', from ' + z0.toFixed(2) + ' m' : ''} · ${p.fl.name || d.floor}` }),
    );
    if (kept) tip.append(el('br'), el('span', { text: `does not stop you: in the approach of ${p.approach.join(', ')}` }));
    tip.style.display = 'block';
    const size = ctx.size();
    tip.style.left = Math.max(4, Math.min(x + 14, size.width - tip.offsetWidth - 8)) + 'px';
    tip.style.top = Math.max(4, Math.min(y + 18, size.height - tip.offsetHeight - 8)) + 'px';
  }

  ctx.disposer.listen(ctx.canvas, 'pointermove', e => {
    if (e.pointerType === 'touch' || e.buttons || mode() !== 'orbit') { hide(); return; }    // not while dragging, nor in Walk / Ghost
    pending = { x: e.clientX, y: e.clientY };
    if (!timer) timer = ctx.disposer.timeout(hover, 50);           // at most 20 times a second; the last position always gets its turn
  });
  ctx.disposer.listen(ctx.canvas, 'pointerleave', hide);
  ctx.disposer.listen(ctx.canvas, 'pointerdown', hide);
  ctx.disposer.listen(ctx.canvas, 'wheel', hide, { passive: true });
  // 2 / 3 (or a double-click) switch the mode under a still pointer: the label goes at once.
  ctx.disposer.add(ctx.bus.on('mode', s => { if (s.mode !== 'orbit') hide(); }));
  return { tip, hide };
}
