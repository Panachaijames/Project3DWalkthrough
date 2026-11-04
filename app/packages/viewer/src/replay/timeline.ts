// Step timing, captions, easing (port of viewer-modes/build_replay.js, its top: KEYS, WEIGHT, SPEEDS, ease, span;
// the bank page's caption `fill`, generalised by DESIGN.md 7.3). Owner: builder D. Pure: Node-testable.
import type { Ease, FillCaption, ReplaySpeed, SettingsMap, StepKey, StepTimes } from '../contracts';

/** The seven steps, in replay order. */
export const KEYS: readonly StepKey[] = ['read', 'sort', 'align', 'pair', 'merge', 'raise', 'finish'];
/** How long each step lasts, relative to the others (DESIGN.md 13 "Replay"). */
export const WEIGHT: Readonly<Record<StepKey, number>> = { read: 1.2, sort: 1.1, align: 1.5, pair: 1.3, merge: 1.0, raise: 2.3, finish: 1.4 };
/** Seconds for the whole replay. */
export const SPEEDS: Readonly<Record<ReplaySpeed, number>> = { quick: 9, normal: 20, slow: 40 };
/** The last frame is held this long before the hand-over to the viewer. */
export const HOLD_MS = 700;
/** A frame never advances the replay by more than this (s). */
export const DT_CAP = 0.1;

export const isSpeed = (v: unknown): v is ReplaySpeed => v === 'quick' || v === 'normal' || v === 'slow';

/**
 * Each step's share of the global progress T (0..1), from the weights, computed exactly as build_replay.js did
 * (a running sum divided by the total, so the floats are the prototype's to the last bit).
 */
export const stepTimes: StepTimes = titles => {
  const totalW = KEYS.reduce((a, k) => a + WEIGHT[k], 0);
  let acc = 0;
  return KEYS.map(key => {
    const t0 = acc / totalW;
    acc += WEIGHT[key];
    return { key, title: titles[key], t0, t1: acc / totalW };
  });
};

/** Cubic ease in-out. */
export const ease: Ease = t => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);

export const clamp01 = (t: number): number => Math.max(0, Math.min(1, t));

/** Local progress of t inside [a, b], clamped to 0..1. */
export const span = (t: number, a: number, b: number): number => clamp01((t - a) / (b - a));

/**
 * Caption placeholders (DESIGN.md 7.3): {<key>level} and {<key>height} -> the Build setting with toFixed(2);
 * {<key>level+} -> the same with a '+' in front when >= 0 (the house page's lv()). A key that is not a floor of the
 * settings is left as written (the bank page's fill).
 */
export const fillCaption: FillCaption = (template, settings) =>
  template.replace(/\{(\w+?)(level|height)(\+)?\}/g, (whole: string, key: string, prop: string, plus: string | undefined) => {
    const v = settingOf(settings, key, prop === 'level' ? 'level' : 'height');
    if (v === null) return whole;
    return (plus && v >= 0 ? '+' : '') + v.toFixed(2);
  });

function settingOf(settings: SettingsMap, key: string, prop: 'level' | 'height'): number | null {
  if (!Object.prototype.hasOwnProperty.call(settings, key)) return null;
  const s = settings[key];
  const v = s ? s[prop] : undefined;
  return typeof v === 'number' && Number.isFinite(v) ? v : null;
}
