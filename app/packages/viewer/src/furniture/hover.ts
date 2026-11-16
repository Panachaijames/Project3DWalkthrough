// The label under the pointer, Orbit only (DESIGN.md 12, 13; furniture_boxes.js "the label under the pointer"). Owner: C.
//   At most 20 times a second (50 ms throttle; the last position always gets its turn), not while dragging, not for touch,
//   not in Walk or Ghost (a mode change hides it at once). The nearest thing under the pointer among the boxes and what hides
//   them (walls, floor plates; glass, half see-through and the invisible Walk skins hide nothing): a box gets a label with
//   its kind, family, size in m (w x d x height, ", from <z0> m" when it does not stand on the floor) and floor, and, while
//   the doorways are kept clear, "does not stop you: in the approach of <ids>". The label is absolute in the root, at the
//   pointer + 14 / 18 px, kept inside the root (all screen maths root-relative). The pick itself is pick.ts's.
//   With editBoxes (docs/boxes/DESIGN.md 2.2, 2.3): a last line "Click to select", the pointer cursor while the pointer
//   rests on a box that a click would select, and no label while the box card is open. Without it, exactly as before.
import type { ViewerContext } from '../contracts';
import { clear, el } from '../ui/dom';
import type { Picker } from './pick';
import type { FurnitureState } from './types';

export interface HoverApi {
  readonly tip: HTMLDivElement;
  hide(): void;
}

export function installHover(ctx: ViewerContext, st: FurnitureState, pick: Picker): HoverApi {
  const tip = el('div', { wt: 'furniture-tip', style: { display: 'none' } });
  ctx.ui.root.append(tip);
  let pending: { x: number; y: number } | null = null, timer = 0;
  const mode = () => ctx.modes.mode;
  const cursor = (on: boolean) => { if (st.editBoxes) ctx.canvas.style.cursor = on ? 'pointer' : ''; };
  const hide = () => { pending = null; tip.style.display = 'none'; cursor(false); };

  function hover() {
    timer = 0;
    const at = pending;
    if (!at || mode() !== 'orbit') { hide(); return; }
    const { x, y } = pick.rootPoint(at.x, at.y);                    // root-relative
    const p = pick.atRoot(x, y);
    const selectable = !!p && !!st.select?.selectable();
    cursor(selectable);
    if (!p || st.select?.cardOpen()) { tip.style.display = 'none'; return; }
    const d = p.d, h = p.kind.height / 1000, z0 = p.z0mm / 1000;
    const kept = st.keepDoorways() && p.kind.blocks && p.approach.length > 0;   // it would stop you, but the doorway it stands in front of is kept clear
    clear(tip);
    tip.append(
      el('b', { text: p.kind.label }), el('br'), d.family, el('br'),
      el('span', { text: `${d.w.toFixed(2)} × ${d.d.toFixed(2)} × ${h.toFixed(2)} m${z0 > 0 ? ', from ' + z0.toFixed(2) + ' m' : ''} · ${p.fl.name || d.floor}` }),
    );
    if (kept) tip.append(el('br'), el('span', { text: `does not stop you: in the approach of ${p.approach.join(', ')}` }));
    if (selectable) tip.append(el('br'), el('span', { wt: 'furniture-tip-hint', text: 'Click to select' }));
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
