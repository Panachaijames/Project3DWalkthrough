// createPanel: the side panel (DESIGN.md 11.5, 11.6, 14; the four generators' panel markup). Owner: builder C.
//   <div class="wtv-panel" data-wt="panel"> with its slots in order (contracts.ts PanelSlot): title (the heading, h1), intro
//   (the presentation's runs as text, bold runs in <b>), floors (only with more than one floor: All + one button per floor),
//   modes (B: after the floors row, or after the ticks when there is none), shows (the ticks the project has anything for),
//   legend (inline or one item a line), build (D), furniture (the furniture legend, last).
//   Floor buttons: in Walk they change the floor you walk on (All -> the first floor); otherwise they show or hide floors.
//   They follow the walked floor in Walk, else the floor mode (bus 'mode' / 'floorMode'); the active one has aria-pressed="true".
//   Ticks follow bus 'toggles' (an API call, ?picture=1). The side panel is shorter by 30 px when the model has furniture
//   (the pages' panel rule: its bottom edge stays above the hint line).
// Drawing and presentation text goes in with textContent only (ui/dom.ts el()).
import type { CreatePanel, FloorKey, PanelApi, PanelSlot, ToggleName, ViewMode } from '../contracts';
import { el } from './dom';

const TOGGLES: ToggleName[] = ['plates', 'glass', 'rooms', 'single', 'picture', 'ceilings'];   // ceilings: shown once visibility.has it (R4)

export const createPanel: CreatePanel = ctx => {
  const pres = ctx.presentation;
  const panel = el('div', { cls: 'wtv-panel', wt: 'panel' });
  if ((ctx.model.furniture ?? []).length) panel.setAttribute('data-furniture', '');
  const many = ctx.floors.length > 1;
  const order: PanelSlot[] = many
    ? ['title', 'intro', 'floors', 'modes', 'shows', 'legend', 'build', 'furniture']
    : ['title', 'intro', 'shows', 'modes', 'legend', 'build', 'furniture'];
  const slots = new Map<PanelSlot, HTMLDivElement>();
  for (const name of [...order, ...(many ? [] : (['floors'] as PanelSlot[]))]) {
    const slot = el('div', { attrs: { 'data-slot': name } });
    slots.set(name, slot);
    if (order.includes(name)) panel.append(slot);                    // a one-floor model's floors slot is never shown
  }
  const slot = (name: PanelSlot) => slots.get(name)!;

  // ---------------------------------------------------------------- heading and intro
  slot('title').append(el('h1', { wt: 'heading', text: pres.heading }));
  slot('intro').append(el('p', { wt: 'intro' }, pres.intro.map(run => (run.bold ? el('b', { text: run.text }) : run.text))));

  // ---------------------------------------------------------------- floor buttons
  const buttons = new Map<'all' | FloorKey, HTMLButtonElement>();
  if (many) {
    const row = el('div', { cls: 'wtv-row', wt: 'floors' });
    const add = (key: 'all' | FloorKey, text: string) => {
      const b = el('button', { attrs: { type: 'button', 'data-floor': key, 'aria-pressed': 'false' }, text });
      buttons.set(key, b);
      row.append(b);
    };
    add('all', pres.floorButtons.all);
    for (const f of ctx.floors) add(f.key, pres.floorButtons.labels[f.key] ?? f.name);
    slot('floors').append(row);
  }
  let last: { mode: ViewMode; floor: FloorKey } = { mode: 'orbit', floor: ctx.floors[0]?.key ?? '' };
  const markFloors = (state: { mode: ViewMode; floor: FloorKey }) => {
    last = { mode: state.mode, floor: state.floor };
    const key = state.mode === 'walk' ? state.floor : ctx.visibility.floorMode;
    for (const [f, b] of buttons) b.setAttribute('aria-pressed', String(f === key));
  };
  for (const [f, b] of buttons) {
    ctx.disposer.listen(b, 'click', () => {
      if (ctx.modes.mode === 'walk') { ctx.modes.goToFloor(f === 'all' ? ctx.floors[0]!.key : f); return; }
      ctx.visibility.setFloorMode(f);
      markFloors({ mode: ctx.modes.mode, floor: last.floor });
    });
  }

  // ---------------------------------------------------------------- ticks
  const ticks = new Map<ToggleName, HTMLInputElement>();
  const shown = TOGGLES.filter(name => ctx.visibility.has(name));
  if (shown.length) {
    const row = el('div', { cls: 'wtv-row', wt: 'shows' });
    for (const name of shown) {
      const box = el('input', { wt: 'toggle', attrs: { type: 'checkbox', 'data-toggle': name } });
      box.checked = !!ctx.visibility.toggles[name];
      ticks.set(name, box);
      row.append(el('label', name === 'picture' ? { title: pres.labels.pictureTitle } : {}, [box, ` ${pres.labels[name]}`]));
      ctx.disposer.listen(box, 'change', () => ctx.visibility.setToggle(name, box.checked));
    }
    slot('shows').append(row);
  }

  // ---------------------------------------------------------------- legend
  const swatch = (colour: string) => el('span', { style: { background: colour } });
  const legend = el('div', { wt: 'legend', attrs: { 'data-layout': pres.legend.layout } },
    pres.legend.layout === 'lines'
      ? pres.legend.items.map(item => el('div', {}, [swatch(item.colour), item.text]))
      : pres.legend.items.flatMap(item => [swatch(item.colour), item.text]));
  slot('legend').append(legend);

  ctx.ui.root.append(panel);

  // ---------------------------------------------------------------- following the modes and the visibility
  ctx.disposer.add(ctx.bus.on('mode', s => markFloors(s)));
  ctx.disposer.add(ctx.bus.on('floorMode', () => markFloors(last)));
  ctx.disposer.add(ctx.bus.on('toggles', ({ toggles }) => { for (const [name, box] of ticks) box.checked = !!toggles[name]; }));
  markFloors(last);

  const api: PanelApi = { el: panel, slot, markFloors };
  return api;
};
