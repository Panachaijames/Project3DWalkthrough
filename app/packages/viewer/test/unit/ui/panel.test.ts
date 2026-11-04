// @vitest-environment happy-dom
// Builder C: createPanel (DESIGN.md 8, 11.5, 11.6, 14, 17.2 ui): the slots in order with and without a floors row, the
// heading and the intro runs as text, the floor buttons (labels, aria-pressed, Orbit / Walk behaviour, bus mode / floorMode),
// the ticks the project has anything for (labels, title, state, bus toggles), the legend inline / lines, all against the
// prototype pages' captured facts (fixtures/prototype/*.json).
import path from 'node:path';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { BuiltModel, FloorKey, PanelApi, Presentation } from '../../../src/contracts';
import { createPanel } from '../../../src/ui/panel';
import { makeTestContext, type TestContext } from '../../harness/context';
import { APP, loadModel, loadPresentation, readText } from '../furniture/util';

interface Facts {
  heading: string; intro: { text: string; html: string }; floorButtons: { key: string; text: string; on: boolean }[];
  ticks: { id: string; label: string; checked: boolean; title: string | null }[];
  legend: { layout: 'inline' | 'lines'; items: { colour: string; text: string }[] };
}
const facts = (name: string) => JSON.parse(readText(path.join(APP, 'fixtures/prototype', `${name}.json`))) as Facts;
const VERSIONS = [
  { model: 'bank-v1', presentation: 'bank-sampeng-v1' },
  { model: 'bank-v2', presentation: 'bank-sampeng-v2' },
  { model: 'suite', presentation: 'presidential-suite' },
  { model: 'house', presentation: 'sukhumvit-house' },
  { model: 'hotel', presentation: 'hotel-lobby' },
] as const;

let live: TestContext[] = [];
afterEach(() => { for (const c of live) c.disposer.dispose(); live = []; vi.restoreAllMocks(); });
function mount(model: BuiltModel, presentation?: Presentation): { ctx: TestContext; panel: PanelApi } {
  const ctx = makeTestContext({ model, presentation });
  live.push(ctx);
  const panel = createPanel(ctx);
  ctx.panel = panel;
  return { ctx, panel };
}
const hex = (c: string) => {          // '#e3ddd3' or 'rgb(227, 221, 211)' -> '#e3ddd3'
  const m = /^rgb\((\d+),\s*(\d+),\s*(\d+)\)$/.exec(c.trim());
  return m ? '#' + m.slice(1).map(v => Number(v).toString(16).padStart(2, '0')).join('') : c.trim().toLowerCase();
};
const pressed = (panel: PanelApi) => [...panel.el.querySelectorAll('[data-wt=floors] [data-floor]')]
  .filter(b => b.getAttribute('aria-pressed') === 'true').map(b => b.getAttribute('data-floor'));

describe('createPanel: the slots', () => {
  it('two floors: title, intro, floors, modes, shows, legend, build, furniture; one floor: title, intro, shows, modes, legend, build, furniture', () => {
    const two = mount(loadModel('bank-v2'), loadPresentation('bank-sampeng-v2'));
    expect([...two.panel.el.children].map(s => s.getAttribute('data-slot'))).toEqual(['title', 'intro', 'floors', 'modes', 'shows', 'legend', 'build', 'furniture']);
    const one = mount(loadModel('suite'), loadPresentation('presidential-suite'));
    expect([...one.panel.el.children].map(s => s.getAttribute('data-slot'))).toEqual(['title', 'intro', 'shows', 'modes', 'legend', 'build', 'furniture']);
    expect(one.panel.slot('floors')).toBeTruthy();
    expect(one.panel.slot('floors').isConnected).toBe(false);
    expect(one.panel.el.querySelector('[data-wt=floors]')).toBeNull();
  });

  it('the panel is [data-wt=panel].wtv-panel in the root; data-furniture when the model has furniture (the shorter max-height)', () => {
    const f = mount(loadModel('bank-v2'), loadPresentation('bank-sampeng-v2'));
    expect(f.panel.el.getAttribute('data-wt')).toBe('panel');
    expect(f.panel.el.classList.contains('wtv-panel')).toBe(true);
    expect(f.panel.el.parentElement).toBe(f.ctx.ui.root);
    expect(f.panel.el.hasAttribute('data-furniture')).toBe(true);
    expect(mount(loadModel('bank-v1'), loadPresentation('bank-sampeng-v1')).panel.el.hasAttribute('data-furniture')).toBe(false);
  });
});

describe('createPanel against the prototype pages (fixtures/prototype)', () => {
  for (const v of VERSIONS) {
    it(`${v.model}: heading, intro, floor buttons, ticks and legend as the page showed them`, () => {
      const f = facts(v.presentation);
      const { panel } = mount(loadModel(v.model), loadPresentation(v.presentation));
      const h1 = panel.el.querySelector('[data-wt=heading]')!;
      expect(h1.tagName).toBe('H1');
      expect(h1.textContent).toBe(f.heading);
      const intro = panel.el.querySelector('[data-wt=intro]')!;
      expect(intro.tagName).toBe('P');
      expect(intro.textContent).toBe(f.intro.text);
      expect(intro.innerHTML).toBe(f.intro.html);
      const buttons = [...panel.el.querySelectorAll('[data-wt=floors] [data-floor]')];
      expect(buttons.map(b => ({ key: b.getAttribute('data-floor') === 'all' ? 'both' : b.getAttribute('data-floor'), text: b.textContent,
        on: b.getAttribute('aria-pressed') === 'true' }))).toEqual(f.floorButtons);
      const ticks = [...panel.el.querySelectorAll<HTMLInputElement>('input[data-wt=toggle]')];
      expect(ticks.map(t => ({ id: t.getAttribute('data-toggle'), label: t.closest('label')!.textContent!.trim(), checked: t.checked,
        title: t.closest('label')!.getAttribute('title') }))).toEqual(f.ticks);
      for (const t of ticks) expect(t.type).toBe('checkbox');
      const legend = panel.el.querySelector<HTMLElement>('[data-wt=legend]')!;
      expect(legend.getAttribute('data-layout')).toBe(f.legend.layout);
      const items = f.legend.layout === 'lines'
        ? [...legend.children].map(d => ({ colour: hex((d.firstElementChild as HTMLElement).style.background), text: d.textContent }))
        : [...legend.children].map(s => ({ colour: hex((s as HTMLElement).style.background), text: (s.nextSibling as Text).textContent }));
      expect(items).toEqual(f.legend.items);
      expect(legend.textContent).toBe(f.legend.items.map(i => i.text).join(''));
    });
  }
});

describe('createPanel: text, never HTML', () => {
  it('an <img onerror> in the heading, an intro run, a legend item or a floor name stays text', () => {
    const bad = '<img src=x onerror="window.__pwned = 1">';
    const m = loadModel('bank-v2');
    m.floors[1]!.name = bad;
    const p: Presentation = { ...loadPresentation('bank-sampeng-v2'), heading: bad, intro: [{ text: bad }, { text: bad, bold: true }],
      legend: { layout: 'inline', items: [{ colour: '#e3ddd3', text: bad }] } };
    const { panel } = mount(m, p);
    expect(panel.el.querySelector('img')).toBeNull();
    expect(panel.el.querySelector('[data-wt=heading]')!.textContent).toBe(bad);
    expect(panel.el.querySelector('[data-wt=intro]')!.textContent).toBe(bad + bad);
    expect(panel.el.querySelector('[data-wt=intro] b')!.textContent).toBe(bad);
    expect(panel.el.querySelector('[data-wt=legend]')!.textContent).toBe(bad);
    expect(panel.el.querySelector('[data-floor="L2"]')!.textContent).toBe(bad);
    expect((window as unknown as { __pwned?: number }).__pwned).toBeUndefined();
  });
});

describe('createPanel: the floor buttons', () => {
  it('Orbit / Ghost: a button sets the floor mode and marks itself; Walk: it changes the walked floor (All -> the first floor)', () => {
    const { ctx, panel } = mount(loadModel('bank-v2'), loadPresentation('bank-sampeng-v2'));
    const btn = (k: string) => panel.el.querySelector<HTMLButtonElement>(`[data-wt=floors] [data-floor="${k}"]`)!;
    expect(pressed(panel)).toEqual(['all']);
    btn('L1').click();
    expect(ctx.visibility.floorMode).toBe('L1');
    expect(ctx.floors.map(f => f.group.visible)).toEqual([true, false]);
    expect(pressed(panel)).toEqual(['L1']);
    btn('all').click();
    expect(ctx.visibility.floorMode).toBe('all');
    expect(pressed(panel)).toEqual(['all']);
    ctx.modes.state.mode = 'ghost';
    btn('L2').click();
    expect(ctx.visibility.floorMode).toBe('L2');
    expect(pressed(panel)).toEqual(['L2']);
    btn('all').click();
    const went: FloorKey[] = [];
    ctx.modes.state.mode = 'walk';
    ctx.modes.goToFloor = key => { went.push(key); };
    btn('L2').click();
    btn('all').click();
    expect(went).toEqual(['L2', 'L1']);
    expect(ctx.visibility.floorMode).toBe('all');
  });

  it('follows bus mode (Walk: the walked floor; else the floor mode) and bus floorMode', () => {
    const { ctx, panel } = mount(loadModel('hotel'), loadPresentation('hotel-lobby'));
    ctx.bus.emit('mode', { mode: 'walk', floor: 'F2' });
    expect(pressed(panel)).toEqual(['F2']);
    ctx.bus.emit('mode', { mode: 'walk', floor: 'F1' });
    expect(pressed(panel)).toEqual(['F1']);
    ctx.bus.emit('mode', { mode: 'orbit', floor: 'F1' });
    expect(pressed(panel)).toEqual(['all']);
    ctx.visibility.setFloorMode('F2');                             // emits floorMode
    expect(pressed(panel)).toEqual(['F2']);
    ctx.bus.emit('mode', { mode: 'ghost', floor: 'F1' });
    expect(pressed(panel)).toEqual(['F2']);
    panel.markFloors({ mode: 'walk', floor: 'F1' });
    expect(pressed(panel)).toEqual(['F1']);
  });

  it("the house's labels (Ground / Upper) and 'Both floors'", () => {
    const { panel } = mount(loadModel('house'), loadPresentation('sukhumvit-house'));
    expect([...panel.el.querySelectorAll('[data-wt=floors] button')].map(b => b.textContent)).toEqual(['Both floors', 'Ground', 'Upper']);
  });
});

describe('createPanel: the ticks', () => {
  it('only the ticks the project has anything for, in the pages\' order; a change goes to visibility.setToggle; bus toggles moves them', () => {
    const { ctx, panel } = mount(loadModel('hotel'), loadPresentation('hotel-lobby'));
    const tick = (n: string) => panel.el.querySelector<HTMLInputElement>(`input[data-wt=toggle][data-toggle=${n}]`)!;
    expect([...panel.el.querySelectorAll('input[data-wt=toggle]')].map(t => t.getAttribute('data-toggle'))).toEqual(['plates', 'glass', 'rooms', 'picture']);
    const set = vi.spyOn(ctx.visibility, 'setToggle');
    tick('glass').checked = false;
    tick('glass').dispatchEvent(new Event('change', { bubbles: true }));
    expect(set).toHaveBeenCalledWith('glass', false);
    expect(ctx.visibility.toggles.glass).toBe(false);
    ctx.visibility.setToggle('picture', true);                     // e.g. viewer.setToggle or ?picture=1
    expect(tick('picture').checked).toBe(true);
    ctx.bus.emit('toggles', { toggles: { plates: false, glass: true, rooms: true, single: true, picture: false } });
    expect([tick('plates').checked, tick('glass').checked, tick('picture').checked]).toEqual([false, true, false]);
  });

  it("the house: plates, glass, single (no room names in this DWG); the suite's Floor slab label", () => {
    const house = mount(loadModel('house'), loadPresentation('sukhumvit-house'));
    expect([...house.panel.el.querySelectorAll('input[data-wt=toggle]')].map(t => t.getAttribute('data-toggle'))).toEqual(['plates', 'glass', 'single']);
    const suite = mount(loadModel('suite'), loadPresentation('presidential-suite'));
    expect(suite.panel.el.querySelector('input[data-toggle=plates]')!.closest('label')!.textContent).toBe(' Floor slab');
  });
});

describe('createPanel: dispose', () => {
  it('takes its bus listeners off with the disposer', () => {
    const { ctx, panel } = mount(loadModel('bank-v2'), loadPresentation('bank-sampeng-v2'));
    const mark = vi.spyOn(panel, 'markFloors');
    ctx.disposer.dispose();
    live = [];
    ctx.bus.emit('mode', { mode: 'walk', floor: 'L2' });
    expect(mark).not.toHaveBeenCalled();
    expect(pressed(panel)).toEqual(['all']);
  });
});
