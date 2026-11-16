// The deleted boxes in the legend, and the Restore list (docs/boxes/DESIGN.md 2.6). Owner: builder C. editBoxes only.
//   The line   [data-wt=furniture-removed], between the kind rows and the buttons, only while a box is deleted
//              ("3 boxes deleted · Restore…") or just after a Restore all ("All 12 boxes are back · Undo", until the next
//              delete or restore). With nothing deleted the legend has no such element.
//   The list   [data-wt=boxes-restore], an overlay in the root beside the side panel (z 7), its bottom edge above the
//              hint line, at most half the root high (it scrolls): one line per group (a deleted piece whose support is
//              not deleted, with the deleted pieces on it folded in) with Restore; Restore all in the footer on the left,
//              away from the × in the top right corner.
// Every drawing text (kind label, family, floor name, id) goes in with textContent (ui/dom.ts el()).
import type { ViewerContext } from '../contracts';
import { clear, el } from '../ui/dom';
import type { FurnitureState, LegendActions } from './types';

export interface RestoreApi {
  /** The line and the open list follow the deleted boxes. */
  refresh(): void;
}

const boxes = (n: number) => (n === 1 ? '1 box' : `${n} boxes`);

/** `place(line, on)`: the legend puts the line between its rows and its buttons, or takes it out. */
export function makeRestore(ctx: ViewerContext, st: FurnitureState, act: LegendActions,
  place: (line: HTMLDivElement, on: boolean) => void): RestoreApi {
  const text = el('span');
  const open = el('button', { wt: 'boxes-restore-open', attrs: { type: 'button' }, text: 'Restore…' });
  const undo = el('button', { wt: 'boxes-restore-undo', attrs: { type: 'button' }, text: 'Undo' });
  const line = el('div', { wt: 'furniture-removed' }, [text, open, undo]);

  const list = el('div', { wt: 'boxes-restore-list' });
  const close = el('button', { wt: 'boxes-restore-close', attrs: { type: 'button', 'aria-label': 'Close the list of deleted boxes' }, text: '×' });
  const all = el('button', { wt: 'boxes-restore-all', attrs: { type: 'button' }, text: 'Restore all' });
  const pop = el('div', { wt: 'boxes-restore', attrs: { role: 'dialog', 'aria-label': 'Deleted boxes' }, style: { display: 'none' } }, [
    el('div', { wt: 'boxes-restore-head' }, [el('b', { text: 'Deleted boxes' }), close]),
    list,
    el('div', { wt: 'boxes-restore-foot' }, [all]),
  ]);
  ctx.ui.root.append(pop);
  let shown = false;

  /** Beside the side panel; the bottom edge above the hint line's top. */
  function put(): void {
    const size = ctx.size(), panel = ctx.rectOf(ctx.panel.el), hint = ctx.rectOf(ctx.ui.hint);
    pop.style.bottom = (hint.height > 0 ? Math.max(12, size.height - hint.top + 8) : 12) + 'px';
    if (panel.width > 0 && panel.left + panel.width / 2 > size.width / 2) {
      pop.style.left = 'auto'; pop.style.right = Math.max(12, size.width - panel.left + 8) + 'px';
    } else {
      pop.style.right = 'auto'; pop.style.left = (panel.width > 0 ? panel.right + 8 : 12) + 'px';
    }
  }
  function fill(): void {
    clear(list);
    for (const g of st.groups()) {
      const p = st.itemOf.get(g.top);
      if (!p) continue;
      list.append(el('div', { wt: 'boxes-restore-row', attrs: { 'data-id': g.top } }, [
        el('span', { wt: 'boxes-restore-what' }, [
          `${p.kind.label} · ${p.d.family} · ${p.fl.name || p.d.floor}${g.on.length ? ` (+${g.on.length} on it)` : ''} `,
          el('small', { text: g.top }),
        ]),
        el('button', { wt: 'box-restore', attrs: { type: 'button' }, text: 'Restore' }),
      ]));
    }
  }
  function show(on: boolean): void {
    shown = on;
    pop.style.display = on ? 'flex' : 'none';
    if (on) { fill(); put(); }
  }

  const api: RestoreApi = {
    refresh() {
      const n = st.removedIds().size, back = n ? 0 : st.restoredAll();
      place(line, n > 0 || back > 0);
      text.textContent = n ? `${boxes(n)} deleted · ` : back === 1 ? '1 box is back · ' : `All ${back} boxes are back · `;
      open.style.display = n ? '' : 'none';
      undo.style.display = !n && back ? '' : 'none';
      if (shown) show(n > 0);                                       // the open list follows; nothing left: it closes
    },
  };

  ctx.disposer.listen(open, 'click', () => show(!shown));
  ctx.disposer.listen(undo, 'click', () => { act.undo(); });
  ctx.disposer.listen(close, 'click', () => show(false));
  ctx.disposer.listen(all, 'click', () => act.restoreAll());
  ctx.disposer.listen(list, 'click', e => {
    const t = e.target instanceof Element ? e.target.closest('[data-wt=box-restore]') : null;
    const id = t?.closest('[data-wt=boxes-restore-row]')?.getAttribute('data-id');
    if (id) act.restorePiece(id);
  });
  ctx.disposer.add(ctx.bus.on('resize', () => { if (shown) put(); }));
  // the replay hides the side panel: the list goes with it
  ctx.disposer.add(ctx.bus.on('replayPhase', ({ phase }) => { if (shown && (phase === 'settings' || phase === 'play')) show(false); }));
  ctx.disposer.add(() => pop.remove());
  return api;
}
