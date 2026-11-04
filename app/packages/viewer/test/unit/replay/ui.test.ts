// @vitest-environment happy-dom
// Builder D: the replay's DOM (build_replay.js's card, steps, bar, caption and Build row) with the selectors of DESIGN.md
// 11.6, the prototype's texts word for word, drawing text only ever as text, the card's input rule and the texts'
// defaults (DESIGN.md 7.2).
import { describe, expect, it } from 'vitest';
import type { ReplayData } from '../../../src/contracts';
import { DEFAULT_REPLAY_TEXTS } from '../../../src/model/presentation';
import { stepTimes } from '../../../src/replay/timeline';
import { buildUi, markSpeed, readSetting, renderCaption, renderSteps, replayTexts, setBar, syncInputs } from '../../../src/replay/ui';
import { card, stages } from './helpers';

describe('readSetting (the card input rule)', () => {
  it.each([
    ['', 'level', 3.7, 3.7], ['   ', 'height', 3.5, 3.5], ['abc', 'level', 4.8, 4.8], ['5.00', 'level', 4.8, 5],
    [' 2.25 ', 'height', 3, 2.25], ['0.5', 'height', 3, 1], ['15', 'height', 3, 12], ['12', 'height', 3, 12],
    ['-20', 'level', 0, -10], ['250', 'level', 0, 200], ['-10', 'level', 0, -10], ['1e1', 'height', 3, 10], ['Infinity', 'level', 1, 1],
  ] as const)('%j for %s (was %d) -> %d', (raw, prop, old, want) => {
    expect(readSetting(raw, prop, old)).toBe(want);
  });
});

describe('replayTexts (defaults: DESIGN.md 7.2)', () => {
  it('takes the bank page values when the file has none', () => {
    const t = replayTexts(stages('bank-v2'));
    expect(t.introTitle).toBe('I1201 - LEVEL 1 GENERAL ARRANGEMENT.dwg + I1202 - LEVEL 2 GENERAL ARRANGEMENT.dwg');
    expect(t.layersTitle).toBe('How the drawing was read');
    expect(t.stepTitles).toEqual(DEFAULT_REPLAY_TEXTS.stepTitles);
  });
  it('takes the file\'s own texts, source.file when there is no files list, and the defaults for missing step titles', () => {
    const t = replayTexts({ source: { file: 'Test Sukhumvit Residence.dwg' }, layersTitle: 'Layers found', stepTitles: { align: 'Line up the floors', raise: '' } });
    expect(t.introTitle).toBe('Test Sukhumvit Residence.dwg');
    expect(t.layersTitle).toBe('Layers found');
    expect(t.stepTitles.align).toBe('Line up the floors');
    expect(t.stepTitles.raise).toBe('Raise the walls');
    expect(replayTexts({ source: {}, introTitle: 'Given' }).introTitle).toBe('Given');
    expect(replayTexts({ source: {} }).introTitle).toBe('');
  });
});

describe('buildUi', () => {
  const data = stages('bank-v2');
  const floors = [{ key: 'L1', name: 'Level 1' }, { key: 'L2', name: 'Level 2' }];
  const texts = replayTexts(data);
  const steps = stepTimes(texts.stepTitles);

  it('builds the card the bank page had: texts, facts, the floors table, layers, speed, captions tick, buttons', () => {
    const ui = buildUi({ floors, stages: data, texts, steps });
    const facts = card('bank-sampeng-v2');
    const q = (s: string) => ui.card.querySelector(s);
    expect(ui.card.getAttribute('data-wt')).toBe('replay-card');
    expect(q('[data-wt=replay-settings] h1')!.textContent).toBe('Build the 3D model');
    expect(q('[data-wt=replay-file]')!.textContent).toBe(facts.introTitle);
    expect([...ui.card.querySelectorAll('[data-wt=replay-facts] li')].map(li => li.textContent)).toEqual(facts.facts);
    expect([...ui.card.querySelectorAll('[data-wt=replay-settings] > table th')].map(th => th.textContent)).toEqual(['Floor', 'Level (m)', 'Wall height (m)']);
    expect([...ui.card.querySelectorAll('[data-wt=replay-settings] > table td:first-child')].map(td => td.textContent)).toEqual(['Level 1', 'Level 2']);
    expect(q('.br-note')!.textContent).toBe('Read from the drawing. Change them if the drawing is wrong or not given.');
    expect(q('[data-wt=replay-layers-title]')!.textContent).toBe(facts.layersTitle);
    expect([...ui.card.querySelectorAll('[data-wt=replay-layers] tr')].map(tr => [...tr.children].map(td => td.textContent))).toEqual(facts.layers);
    expect(q('.vm-label')!.textContent).toBe('Replay speed');
    expect([...ui.card.querySelectorAll('[data-wt=replay-speed] [data-speed]')].map(b => [b.getAttribute('data-speed'), b.textContent])).toEqual([['quick', 'Quick'], ['normal', 'Normal'], ['slow', 'Slow']]);
    expect(ui.captions.type).toBe('checkbox');
    expect(ui.captions.checked).toBe(true);
    expect(ui.captions.parentElement!.textContent).toBe(' Explain each step');
    expect(ui.captions.parentElement!.style.marginTop).toBe('8px');
    expect(ui.go.textContent).toBe('Generate 3D model');
    expect(ui.skipSettings.textContent).toBe('Skip: show the finished model');
    expect(q('[data-wt=replay-play] h1')!.textContent).toBe('Building the model');
    expect(ui.play.style.display).toBe('none');
    expect(ui.skip.textContent).toBe('Skip to the model');
    expect(ui.steps.map(li => li.textContent)).toEqual(facts.stepList);
    expect(ui.steps.every(li => li.getAttribute('data-state') === 'todo')).toBe(true);
    expect(q('[data-wt=replay-bar] i')).toBe(ui.bar);
    expect(ui.caption.getAttribute('data-wt')).toBe('replay-caption');
    expect(ui.row.textContent).toBe('BuildReplay the buildBuild settings');
    expect(ui.again.getAttribute('data-wt')).toBe('replay-again');
    expect(ui.open.getAttribute('data-wt')).toBe('replay-open');
    for (const b of ui.card.querySelectorAll('button')) expect(b.getAttribute('type')).toBe('button');
  });

  it('has a level and a wall-height box per floor, as the selector map names them', () => {
    const ui = buildUi({ floors, stages: data, texts, steps });
    expect(ui.inputs.map(i => [i.getAttribute('data-floor'), i.getAttribute('data-prop'), i.type, i.step, i.min, i.max])).toEqual([
      ['L1', 'level', 'number', '0.05', '', ''], ['L1', 'height', 'number', '0.05', '1', '12'],
      ['L2', 'level', 'number', '0.05', '', ''], ['L2', 'height', 'number', '0.05', '1', '12'],
    ]);
    syncInputs(ui, { L1: { level: 0, height: 3.7 }, L2: { level: 3.7, height: 3.500000000000001 } });
    expect(ui.inputs.map(i => i.value)).toEqual(['0.00', '3.70', '3.70', '3.50']);
    document.body.append(ui.card);
    expect(document.querySelector('[data-wt=replay-card] input[data-floor="L2"][data-prop=height]')).toBe(ui.inputs[3]);
    ui.card.remove();
  });

  it('puts drawing text in as text, never as HTML', () => {
    const evil = '<img src=x onerror="window.__pwned = 1">';
    const bad: ReplayData = { ...data, source: { file: evil }, intro: [evil, '<b>bold?</b>'], layers: [[evil, `${evil} & more`]], layersTitle: evil };
    const ui = buildUi({ floors: [{ key: 'L1', name: evil }], stages: bad, texts: replayTexts(bad), steps: stepTimes({ ...texts.stepTitles, read: evil }) });
    document.body.append(ui.card);
    expect(ui.card.querySelectorAll('img, b').length).toBe(0);
    expect(ui.card.querySelector('[data-wt=replay-file]')!.textContent).toBe(evil);
    expect(ui.card.querySelector('[data-wt=replay-facts] li')!.textContent).toBe(evil);
    expect(ui.card.querySelector('[data-wt=replay-layers-title]')!.textContent).toBe(evil);
    expect(ui.card.querySelector('[data-wt=replay-settings] > table td')!.textContent).toBe(evil);
    expect(ui.steps[0]!.textContent).toBe(`1${evil}`);
    renderCaption(ui, evil, `${evil} caption`);
    expect(ui.caption.querySelectorAll('img').length).toBe(0);
    expect(ui.caption.querySelector('b')!.textContent).toBe(`${evil}.`);
    expect(ui.caption.textContent).toBe(`${evil}. ${evil} caption`);
    expect((window as unknown as { __pwned?: number }).__pwned).toBeUndefined();
    ui.card.remove();
  });

  it('marks the speed, the steps (done ✓ / now / to do) and the bar', () => {
    const ui = buildUi({ floors, stages: data, texts, steps });
    markSpeed(ui, 'quick');
    expect(ui.speed.map(b => b.getAttribute('aria-pressed'))).toEqual(['true', 'false', 'false']);
    markSpeed(ui, 'slow');
    expect(ui.speed.map(b => b.getAttribute('aria-pressed'))).toEqual(['false', 'false', 'true']);
    const T = (steps[2]!.t0 + steps[2]!.t1) / 2;
    renderSteps(ui, steps, T, steps[2]!);
    expect(ui.steps.map(li => li.getAttribute('data-state'))).toEqual(['done', 'done', 'now', 'todo', 'todo', 'todo', 'todo']);
    expect(ui.steps.map(li => li.querySelector('i')!.textContent)).toEqual(['✓', '✓', '3', '4', '5', '6', '7']);
    renderSteps(ui, steps, 1, steps[6]!);
    expect(ui.steps.every(li => li.getAttribute('data-state') === 'done')).toBe(true);
    expect(ui.steps.map(li => li.querySelector('i')!.textContent)).toEqual(Array(7).fill('✓'));
    renderSteps(ui, steps, 0, steps[0]!);
    expect(ui.steps.map(li => li.getAttribute('data-state'))).toEqual(['now', 'todo', 'todo', 'todo', 'todo', 'todo', 'todo']);
    setBar(ui, 0.4567);
    expect(ui.bar.style.width).toBe('45.7%');
    setBar(ui, 1);
    expect(ui.bar.style.width).toBe('100.0%');
  });
});
