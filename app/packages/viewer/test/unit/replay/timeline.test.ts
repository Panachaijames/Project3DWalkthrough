// Builder D: the replay's timeline (DESIGN.md 7.3, 13 "Replay", 17.2 replay): step times from the weights, easing,
// caption placeholders (all three forms, unknown keys kept) and the bank's captions at the default settings against the
// facts captured from the prototype pages.
import { describe, expect, it } from 'vitest';
import type { SettingsMap, StepKey } from '../../../src/contracts';
import { DEFAULT_REPLAY_TEXTS } from '../../../src/model/presentation';
import { clamp01, DT_CAP, ease, fillCaption, HOLD_MS, isSpeed, KEYS, SPEEDS, span, stepTimes, WEIGHT } from '../../../src/replay/timeline';
import { card, stages } from './helpers';

describe('stepTimes', () => {
  it('splits 0..1 by the weights read 1.2, sort 1.1, align 1.5, pair 1.3, merge 1.0, raise 2.3, finish 1.4', () => {
    expect(KEYS).toEqual(['read', 'sort', 'align', 'pair', 'merge', 'raise', 'finish']);
    expect(WEIGHT).toEqual({ read: 1.2, sort: 1.1, align: 1.5, pair: 1.3, merge: 1.0, raise: 2.3, finish: 1.4 });
    const t = stepTimes(DEFAULT_REPLAY_TEXTS.stepTitles);
    expect(t.map(s => s.key)).toEqual(KEYS);
    expect(t[0]!.t0).toBe(0);
    expect(t[6]!.t1).toBe(1);
    for (let i = 1; i < t.length; i++) expect(t[i]!.t0).toBe(t[i - 1]!.t1);
    const total = 9.8;
    t.forEach(s => expect(s.t1 - s.t0).toBeCloseTo(WEIGHT[s.key] / total, 12));
    expect(t.map(s => s.title)).toEqual(KEYS.map(k => DEFAULT_REPLAY_TEXTS.stepTitles[k]));
  });

  it.each(['bank-sampeng-v1', 'bank-sampeng-v2', 'presidential-suite', 'sukhumvit-house'])('gives exactly the t0 / t1 the %s page had', name => {
    const facts = card(name);
    const titles = Object.fromEntries(facts.steps.map(s => [s.key, s.title])) as Record<StepKey, string>;
    const t = stepTimes(titles);
    expect(t.map(s => [s.key, s.title, s.t0, s.t1])).toEqual(facts.steps.map(s => [s.key, s.title, s.t0, s.t1]));
  });
});

describe('ease, span, speeds', () => {
  it('eases in and out (cubic), symmetric about 0.5', () => {
    expect(ease(0)).toBe(0);
    expect(ease(1)).toBe(1);
    expect(ease(0.5)).toBe(0.5);
    expect(ease(0.25)).toBeCloseTo(4 * 0.25 ** 3, 12);
    expect(ease(0.75)).toBeCloseTo(1 - Math.pow(-2 * 0.75 + 2, 3) / 2, 12);
    for (let i = 0; i <= 20; i++) { const x = i / 20; expect(ease(x) + ease(1 - x)).toBeCloseTo(1, 12); }
    for (let i = 1; i <= 100; i++) expect(ease(i / 100)).toBeGreaterThanOrEqual(ease((i - 1) / 100));
  });

  it('span gives the local progress inside [a, b], clamped', () => {
    expect(span(0.5, 0, 1)).toBe(0.5);
    expect(span(0.1, 0.2, 0.4)).toBe(0);
    expect(span(0.3, 0.2, 0.4)).toBeCloseTo(0.5, 12);
    expect(span(0.9, 0.2, 0.4)).toBe(1);
    expect(clamp01(-3)).toBe(0);
    expect(clamp01(7)).toBe(1);
  });

  it('keeps the timing constants of the prototype', () => {
    expect(SPEEDS).toEqual({ quick: 9, normal: 20, slow: 40 });
    expect(HOLD_MS).toBe(700);
    expect(DT_CAP).toBe(0.1);
    expect([isSpeed('quick'), isSpeed('normal'), isSpeed('slow'), isSpeed('fast'), isSpeed(undefined)]).toEqual([true, true, true, false, false]);
  });
});

describe('fillCaption', () => {
  const s: SettingsMap = { L1: { level: 0, height: 3.7 }, L2: { level: 3.7, height: 3.7 }, ground: { level: 0.9, height: 3.9 }, b1: { level: -3.2, height: 2.85 } };

  it('fills {<key>level} and {<key>height} with two decimals', () => {
    expect(fillCaption('rises to {L2level} m; walls {L1height} m', s)).toBe('rises to 3.70 m; walls 3.70 m');
    expect(fillCaption('{b1level} / {b1height}', s)).toBe('-3.20 / 2.85');
  });

  it('puts a + in front of {<key>level+} when it is not below 0 (the house page lv())', () => {
    expect(fillCaption('ground {groundlevel+} m, upper {b1level+} m', s)).toBe('ground +0.90 m, upper -3.20 m');
    expect(fillCaption('{L1level+}', s)).toBe('+0.00');
    expect(fillCaption('{L1level+}', { L1: { level: -0, height: 3 } })).toBe('+0.00');
  });

  it('leaves an unknown key as written, every occurrence replaced', () => {
    expect(fillCaption('{L9level} and {nolevel+} and {L2level}, {L2level}', s)).toBe('{L9level} and {nolevel+} and 3.70, 3.70');
    expect(fillCaption('{constructorlevel} {toStringheight}', s)).toBe('{constructorlevel} {toStringheight}');
    expect(fillCaption('no placeholders, {braces} kept', s)).toBe('no placeholders, {braces} kept');
  });

  it('reads keys that end like a property name (lazy key match)', () => {
    expect(fillCaption('{toplevellevel}', { toplevel: { level: 1.25, height: 3 } })).toBe('1.25');
  });

  it.each([['bank-v1', 'bank-sampeng-v1'], ['bank-v2', 'bank-sampeng-v2']])('gives the %s captions the page showed at the default settings', (st, page) => {
    const data = stages(st), facts = card(page);
    for (const step of facts.steps) expect(fillCaption(data.captions[step.key], facts.settings)).toBe(step.caption);
    // the bank's: 39 doors, rises to 3.70 m, lintels, glass partitions (bank_test/test_bank.mjs)
    const all = KEYS.map(k => fillCaption(data.captions[k], facts.settings));
    expect(all.some(c => c.includes('39 doors'))).toBe(true);
    expect(all.some(c => c.includes('rises to 3.70 m'))).toBe(true);
    expect(all.some(c => /lintels/.test(c))).toBe(true);
    expect(all.some(c => /glass partition/.test(c))).toBe(true);
  });
});
