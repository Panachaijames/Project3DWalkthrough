// The furniture legend in the side panel's last slot (DESIGN.md 11.6, 12; furniture_boxes.js "the legend"). Owner: builder C.
//   title "Furniture boxes" with a master show tick; the note; "Keep doorways clear" (only when a piece stands in an approach);
//   one row per kind that has pieces, in the kinds table's order: show tick, swatch, "<label> (<count>)", the height box (mm),
//   the stops tick; Reset heights and Save list (CSV).
//   Typing: the number is selected on focus (a moment later, unless a key got in first: 640 must not become 40); a valid
//   number applies as you type; Enter or leaving the box keeps a good number; anything else, and Escape, go back to the height
//   from before you typed (which also undoes the half-typed numbers applied on the way: the 999 of 9999). Junk is marked
//   (data-bad) while typed; a height that differs from the model's is marked (data-edited).
// Every text goes in with textContent (ui/dom.ts el()); kind labels come from the model. Listeners through the disposer.
import type { ViewerContext } from '../contracts';
import { el } from '../ui/dom';
import { MAX_H, MIN_H, parseTypedHeight } from './logic';
import type { FurnitureState, KindState, LegendActions } from './types';

export interface LegendApi {
  readonly el: HTMLDivElement;
  /** The row follows the kind; keepText: the box being typed in keeps its text. */
  showRow(k: KindState, keepText?: boolean): void;
  /** The doorways tick follows the module's flag. */
  showKeep(): void;
}

interface Row { show: HTMLInputElement; height: HTMLInputElement; stops: HTMLInputElement }

const flag = (e: Element, name: string, on: boolean) => { if (on) e.setAttribute(name, ''); else e.removeAttribute(name); };
const is = (t: EventTarget | null, wt: string): t is HTMLInputElement =>
  !!t && typeof (t as Element).getAttribute === 'function' && (t as Element).getAttribute('data-wt') === wt;

export function makeLegend(ctx: ViewerContext, st: FurnitureState, act: LegendActions): LegendApi {
  const checkbox = (wt: string, title?: string, label?: string) => {
    const b = el('input', { wt, attrs: { type: 'checkbox', ...(label ? { 'aria-label': label } : {}) }, ...(title ? { title } : {}) });
    b.checked = true;
    return b;
  };
  const master = checkbox('furniture-all');
  const nApproach = st.inApproach.length;
  const keep = nApproach ? checkbox('furniture-keep') : null;        // none when no piece stands in an approach
  const rows = new Map<string, Row>();
  const rowEls = st.kinds.map(k => {
    const show = checkbox('kind-show', 'Show these boxes', `Show ${k.label}`);
    const height = el('input', {
      wt: 'kind-height', title: `Height in mm, ${MIN_H} to ${MAX_H}`,
      attrs: { type: 'text', inputmode: 'numeric', autocomplete: 'off', spellcheck: 'false', 'aria-label': `${k.label}: height in mm` },
    });
    const stops = checkbox('kind-stops', 'Walk stops you at these boxes', `${k.label}: Walk stops you`);
    rows.set(k.key, { show, height, stops });
    return el('div', { wt: 'furniture-row', attrs: { 'data-kind': k.key } }, [
      show,
      el('i', { wt: 'kind-swatch', style: { background: k.colour } }),
      el('span', { wt: 'kind-label', title: k.label, text: `${k.label} (${k.items.length})` }),
      height,
      stops,
    ]);
  });
  const resetBtn = el('button', { wt: 'furniture-reset', attrs: { type: 'button' }, text: 'Reset heights' });
  const saveBtn = el('button', { wt: 'furniture-save', attrs: { type: 'button' }, text: 'Save list (CSV)' });
  const block = el('div', { wt: 'furniture' }, [
    el('div', { wt: 'furniture-titlebar' }, [el('span', { wt: 'furniture-title', text: 'Furniture boxes' }), el('label', {}, [master, ' show'])]),
    el('div', { wt: 'furniture-note', text: 'Type a height in mm for each kind. Walk: boxes stop you; Ghost passes through.' }),
    keep ? el('label', {
      wt: 'furniture-door',
      title: `${nApproach} of the boxes stand in front of a door or a passage. Ticked: Walk is not stopped by them (they stay drawn), so every doorway can be walked through. Unticked: they stop you like any other box.`,
    }, [keep, ' Keep doorways clear']) : null,
    el('div', { wt: 'furniture-head' }, [el('span'), el('span'), el('span', { text: 'Kind' }), el('span', { text: 'mm' }),
      el('span', { title: 'Walk stops you at these boxes', text: 'stops' })]),
    ...rowEls,
    el('div', { wt: 'furniture-buttons' }, [resetBtn, saveBtn]),
  ]);

  const api: LegendApi = {
    el: block,
    showRow(k, keepText) {
      const r = rows.get(k.key);
      if (!r) return;
      r.show.checked = k.visible;
      r.stops.checked = k.blocks;
      if (!keepText) { r.height.value = String(k.height); flag(r.height, 'data-bad', false); }
      flag(r.height, 'data-edited', k.height !== k.defaultHeight);
      master.checked = st.kinds.every(x => x.visible);
      master.indeterminate = !master.checked && st.kinds.some(x => x.visible);
    },
    showKeep() { if (keep) keep.checked = st.keepDoorways(); },
  };

  // ---------------------------------------------------------------- typing a height
  const kindOfRow = (t: Element) => st.kindOf.get(t.closest('[data-wt=furniture-row]')?.getAttribute('data-kind') ?? '\u0000');
  const before = new Map<string, number>();                         // a kind's height when you clicked into its box
  ctx.disposer.listen(block, 'focusin', e => {
    const t = e.target;
    if (!is(t, 'kind-height')) return;
    const k = kindOfRow(t);
    if (!k) return;
    before.set(k.key, k.height);
    const v0 = t.value;                                             // the number is selected, so typing replaces it (after the click's own caret) - unless a key got in first
    const focused = () => (t.getRootNode() as Document | ShadowRoot).activeElement === t;      // the document's, or the shadow root's when the viewer lives in one
    ctx.disposer.timeout(() => { if (focused() && t.value === v0) t.select(); }, 0);
  });
  ctx.disposer.listen(block, 'input', e => {
    const t = e.target;
    if (!is(t, 'kind-height')) return;
    const k = kindOfRow(t);
    if (!k) return;
    const v = parseTypedHeight(t.value);
    flag(t, 'data-bad', v === null && t.value.trim() !== '');
    if (v !== null && v !== k.height) act.setHeight(k.key, v, true);       // applies as you type a valid number
  });
  // Enter or leaving the box keeps a good number; anything else (and Escape) goes back to the height from before you typed.
  const commit = (t: HTMLInputElement, cancel: boolean) => {
    const k = kindOfRow(t);
    if (!k) return;
    const v = cancel ? null : parseTypedHeight(t.value);
    const to = v !== null ? v : before.has(k.key) ? before.get(k.key)! : k.height;
    if (to !== k.height) act.setHeight(k.key, to); else api.showRow(k);
  };
  ctx.disposer.listen(block, 'focusout', e => { if (is(e.target, 'kind-height')) commit(e.target, false); });
  ctx.disposer.listen(block, 'keydown', e => {
    const t = e.target;
    if (!is(t, 'kind-height')) return;
    if (e.key === 'Enter') { commit(t, false); t.blur(); }
    else if (e.key === 'Escape') { commit(t, true); t.blur(); }
  });

  // ---------------------------------------------------------------- the ticks and the buttons
  ctx.disposer.listen(block, 'change', e => {
    const t = e.target;
    if (is(t, 'furniture-all')) act.setAllVisible(t.checked);
    else if (is(t, 'kind-show')) { const k = kindOfRow(t); if (k) act.setVisible(k.key, t.checked); }
    else if (is(t, 'kind-stops')) { const k = kindOfRow(t); if (k) act.setBlocks(k.key, t.checked); }
    else if (is(t, 'furniture-keep')) act.setKeepDoorways(t.checked);
  });
  ctx.disposer.listen(resetBtn, 'click', () => act.reset());
  ctx.disposer.listen(saveBtn, 'click', () => { act.saveCsv(); });

  return api;
}
