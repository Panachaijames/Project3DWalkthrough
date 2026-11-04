// The replay's UI: the Build settings card, the steps list, the bar, the caption and the Build row of the side panel
// (port of build_replay.js "UI": the card markup, syncInputs, markSpeed, the input rule; apply's step list and caption).
// Owner: builder D. Texts word for word the prototype's. Drawing text (the intro title and facts, the layers, floor
// names, captions) goes in with textContent only (ui/dom.ts el()); the card and caption are absolute overlays inside the
// viewer root, the Build row goes into the panel's slot `build` (DESIGN.md 11.6). Selectors: the data-wt names of 11.6.
import type { FloorSettings, ReplayData, ReplaySpeed, SettingsMap, StepKey } from '../contracts';
import { DEFAULT_REPLAY_TEXTS } from '../model/presentation';
import { clear, el } from '../ui/dom';

/** The card's texts with the defaults of DESIGN.md 7.2 (the bank page's) where the stages file has none. */
export interface ReplayTexts { introTitle: string; layersTitle: string; stepTitles: Record<StepKey, string> }

const text = (v: unknown): v is string => typeof v === 'string' && v !== '';

export function replayTexts(stages: Pick<ReplayData, 'source' | 'introTitle' | 'layersTitle' | 'stepTitles'>): ReplayTexts {
  const src = stages.source ?? {};
  const files = Array.isArray(src.files) ? src.files.filter(f => typeof f === 'string') : [];
  const introTitle = typeof stages.introTitle === 'string' ? stages.introTitle
    : files.length ? files.join(' + ') : typeof src.file === 'string' ? src.file : '';
  const d = DEFAULT_REPLAY_TEXTS;
  const titles = { ...d.stepTitles };
  for (const k of Object.keys(titles) as StepKey[]) { const t = stages.stepTitles?.[k]; if (text(t)) titles[k] = t; }
  return { introTitle, layersTitle: text(stages.layersTitle) ? stages.layersTitle : d.layersTitle, stepTitles: titles };
}

/** The card's input rule: an empty or unreadable box keeps the old value; height 1 - 12 m, level -10 - 200 m. */
export function readSetting(raw: string, prop: keyof FloorSettings, old: number): number {
  // A browser reports an empty and an unreadable number box both as '', and Number('') would be 0.
  const s = raw.trim(), v = s === '' ? NaN : Number(s);
  if (!Number.isFinite(v)) return old;
  return prop === 'height' ? Math.max(1, Math.min(12, v)) : Math.max(-10, Math.min(200, v));
}

export interface CardFloor { key: string; name: string }

export interface ReplayUi {
  card: HTMLDivElement;
  settings: HTMLDivElement;
  play: HTMLDivElement;
  inputs: HTMLInputElement[];
  speed: HTMLButtonElement[];
  captions: HTMLInputElement;
  go: HTMLButtonElement;
  skipSettings: HTMLButtonElement;
  skip: HTMLButtonElement;
  steps: HTMLLIElement[];
  bar: HTMLElement;
  caption: HTMLDivElement;
  row: HTMLDivElement;
  again: HTMLButtonElement;
  open: HTMLButtonElement;
}

const button = (wt: string | undefined, label: string, attrs: Record<string, string> = {}): HTMLButtonElement =>
  el('button', { ...(wt ? { wt } : {}), text: label, attrs: { type: 'button', ...attrs } });

/** The card, the caption and the Build row (not yet in the page). */
export function buildUi(o: { floors: readonly CardFloor[]; stages: ReplayData; texts: ReplayTexts; steps: { key: StepKey; title: string }[] }): ReplayUi {
  const inputs: HTMLInputElement[] = [];
  const numberBox = (key: string, prop: 'level' | 'height'): HTMLInputElement => {
    const attrs: Record<string, string> = { type: 'number', step: '0.05', 'data-floor': key, 'data-prop': prop };
    if (prop === 'height') { attrs.min = '1'; attrs.max = '12'; }
    const i = el('input', { attrs });
    inputs.push(i);
    return i;
  };
  const floorRows = o.floors.map(f => el('tr', {}, [
    el('td', { text: f.name }), el('td', {}, [numberBox(f.key, 'level')]), el('td', {}, [numberBox(f.key, 'height')]),
  ]));
  const floorsTable = el('table', {}, [el('tbody', {}, [
    el('tr', {}, [el('th', { text: 'Floor' }), el('th', { text: 'Level (m)' }), el('th', { text: 'Wall height (m)' })]),
    ...floorRows,
  ])]);
  const layers = (o.stages.layers ?? []).map(([a, b]) => el('tr', {}, [el('td', { text: String(a) }), el('td', { text: String(b) })]));
  const speed = (['quick', 'normal', 'slow'] as ReplaySpeed[]).map(s =>
    button(undefined, s === 'quick' ? 'Quick' : s === 'normal' ? 'Normal' : 'Slow', { 'data-speed': s, 'aria-pressed': 'false' }));
  const captions = el('input', { wt: 'replay-captions', attrs: { type: 'checkbox' } });
  captions.checked = true;
  captions.defaultChecked = true;
  const go = button('replay-go', 'Generate 3D model');
  const skipSettings = button('replay-skip-settings', 'Skip: show the finished model');
  const settings = el('div', { wt: 'replay-settings' }, [
    el('h1', { text: 'Build the 3D model' }),
    el('p', { cls: 'br-file', wt: 'replay-file', text: o.texts.introTitle }),
    el('ul', { wt: 'replay-facts' }, (o.stages.intro ?? []).map(x => el('li', { text: String(x) }))),
    floorsTable,
    el('p', { cls: 'br-note', text: 'Read from the drawing. Change them if the drawing is wrong or not given.' }),
    el('details', { wt: 'replay-layers' }, [
      el('summary', { wt: 'replay-layers-title', text: o.texts.layersTitle }),
      el('table', {}, [el('tbody', {}, layers)]),
    ]),
    el('div', { cls: 'vm-label', text: 'Replay speed' }),
    el('div', { cls: 'vm-row', wt: 'replay-speed' }, speed),
    el('label', { style: { marginTop: '8px' } }, [captions, ' Explain each step']),
    go,
    skipSettings,
  ]);
  const steps = o.steps.map((s, i) => el('li', { attrs: { 'data-step': s.key, 'data-state': 'todo' } }, [el('i', { text: String(i + 1) }), s.title]));
  const bar = el('i');
  const skip = button('replay-skip', 'Skip to the model');
  const play = el('div', { wt: 'replay-play' }, [
    el('h1', { text: 'Building the model' }),
    el('ol', { wt: 'replay-steps' }, steps),
    el('div', { wt: 'replay-bar' }, [bar]),
    el('div', { cls: 'vm-row' }, [skip]),
  ]);
  play.style.display = 'none';
  const card = el('div', { wt: 'replay-card' }, [settings, play]);
  const caption = el('div', { wt: 'replay-caption' });
  // A row in the side panel to come back to this later.
  const again = button('replay-again', 'Replay the build');
  const open = button('replay-open', 'Build settings');
  const row = el('div', { wt: 'replay-row' }, [el('div', { cls: 'vm-label', text: 'Build' }), el('div', { cls: 'vm-row' }, [again, open])]);
  return { card, settings, play, inputs, speed, captions, go, skipSettings, skip, steps, bar, caption, row, again, open };
}

/** Each box shows its setting with two decimals. */
export function syncInputs(ui: ReplayUi, settings: SettingsMap): void {
  for (const i of ui.inputs) {
    const s = settings[i.getAttribute('data-floor') ?? ''];
    const prop = i.getAttribute('data-prop') === 'height' ? 'height' : 'level';
    if (s) i.value = s[prop].toFixed(2);
  }
}

/** The chosen replay speed is the pressed button. */
export function markSpeed(ui: ReplayUi, speed: ReplaySpeed): void {
  for (const b of ui.speed) b.setAttribute('aria-pressed', String(b.getAttribute('data-speed') === speed));
}

/** The step list (done ✓ / now / to do) and the caption `<b>Title.</b> caption`. */
export function renderSteps(ui: ReplayUi, steps: readonly { key: StepKey; t1: number }[], T: number, now: { key: StepKey }): void {
  ui.steps.forEach((li, i) => {
    const s = steps.find(x => x.key === li.getAttribute('data-step'));
    if (!s) return;
    const done = T >= s.t1, current = s.key === now.key && T < 1;
    li.setAttribute('data-state', done ? 'done' : current ? 'now' : 'todo');
    const mark = li.querySelector('i');
    if (mark) mark.textContent = done ? '✓' : String(i + 1);
  });
}

export function renderCaption(ui: ReplayUi, title: string, caption: string): void {
  clear(ui.caption);
  ui.caption.append(el('b', { text: `${title}.` }), ` ${caption}`);
}

/** The bar fills to T. */
export function setBar(ui: ReplayUi, T: number): void {
  ui.bar.style.width = `${(T * 100).toFixed(1)}%`;
}

export const show = (e: HTMLElement, on: boolean): void => { e.style.display = on ? 'block' : 'none'; };
