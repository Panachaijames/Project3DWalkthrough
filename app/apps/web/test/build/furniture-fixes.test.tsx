// After the final check of 9 Nov 2026 (docs/upload/contract-issues/UR.md, "After the final check (9 Nov)"), on the
// screens against the mock API:
//   * the Check step: the final check's grey families (the house's five, SmartTable, a HermanMiller_ family) given a kind
//     with their selects: the settings saved hold each family exactly as its flag shows it, and each select then shows
//     its kind; a word saved before in the acceptance settings' way ('TF2092 P') shows its kind and is replaced, not
//     kept beside the new one;
//   * the Floors step's build options: the furniture size limits (minSize, minDepth) with one line of help each, saved
//     the existing way; an empty depth is no limit; a value out of bounds is said on the step, and the save goes on
//     with the next change.
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { MIN_DEPTH_HELP, MIN_SIZE_HELP } from '@/build/FloorsStep';
import type { BuildOverlay, BuildSettings } from '@/upload/contracts';
import { resetFakeViewer } from '../fake-viewer';
import { choose, enter, stubWebGL, text, waitFor } from '../helpers';
import { createMockApi, type MockApi } from '../mock-api/core';
import { closeAll, draftOf, fastClocks, openApp, q, settingsPuts, waitForPut } from './app';
import { fakePlan } from './fake-plan';

vi.mock('@walkthrough/viewer', async () => vi.importActual('../fake-viewer'));
vi.mock('@/plan', async importOriginal => {
  const real = await importOriginal<typeof import('@/plan')>();
  const fake = await import('./fake-plan');
  return { ...real, PlanCanvas: fake.FakePlanCanvas, nearLayers: fake.fakeNearLayers, proposeAreas: fake.fakeProposeAreas };
});
vi.setConfig({ testTimeout: 60_000 });

let restoreClocks = () => undefined as void;
let restoreWebGL = () => undefined as void;
beforeEach(() => { restoreClocks = fastClocks(); fakePlan.reset(); resetFakeViewer(); restoreWebGL = stubWebGL(); });
afterEach(async () => { restoreClocks(); restoreWebGL(); await closeAll(); });

async function openStep(mock: MockApi, buildId: string, step: string) {
  const app = await openApp(`/projects/bank-sampeng/builds/${buildId}?step=${step}`, { mock });
  await waitFor(() => q(`[data-testid=build-page][data-step=${step}]`));
  return app;
}
const status = () => q('[data-testid=settings-status]')?.dataset.status;
const saved = (mock: MockApi, buildId: string): BuildSettings => mock.uploads.build('bank-sampeng', buildId)!.settings;

const HERMAN = 'HermanMiller_Seating_AER1A_NewAeron_WorkChair_ASize - SE101_Size Low-Hgt Range';
const SEVEN: [string, string][] = [
  ['TF2092P', 'sanitary'], ['TF0560P', 'sanitary'], ['A$C2619574F', 'sanitary'], ['A$C238E5230', 'bed'],
  ['A$C5BF14633', 'coffee-table'], ['SmartTable', 'bar-table'], [HERMAN, 'sofa'],
];
/** A grey-furniture flag in the overlay's own wording (out/overlay.py grey_furniture_flags). */
const greyFlag = (family: string, n: number, i: number): BuildOverlay['flags'][number] => ({
  id: `grey-furniture:L1:${String(i).padStart(12, '0')}`, kind: 'grey-furniture', floor: 'L1', severity: 'info',
  title: `${family}: ${n} grey box${n === 1 ? '' : 'es'}`,
  detail: `The furniture kit does not know what ${family} is, so its ${n} piece${n === 1 ? ' is' : 's are'} grey. Pick a kind for the family.`,
  at: [1 + i, 1], bbox: null, ref: { family },
});
const row = (family: string) => q(`[data-testid=furniture-family][data-family="${CSS.escape(family)}"]`);
const select = (family: string) => row(family)?.querySelector<HTMLSelectElement>('[data-testid=furniture-word-kind]') ?? null;

async function openCheck(words: Record<string, string[]> = {}) {
  const mock = createMockApi();
  mock.uploads.config.extraFlags = SEVEN.map(([family], i) => greyFlag(family, i + 1, i));
  const { build } = draftOf(mock, 'bank-sampeng', ['I1201.dwg', 'I1202.dwg'], { built: true });
  build.settings.furniture.words = words;
  build.results.forEach(r => { r.settings.furniture.words = words; });          // the result is not stale
  await openStep(mock, build.id, 'check');
  await waitFor(() => q('[data-testid=fake-canvas][data-overlay=L1]'));
  await waitFor(() => row(HERMAN));
  return { mock, build };
}

describe('the Check step: a grey family given a kind', () => {
  it('saves each of the final check\'s names exactly as its flag shows it; each select then shows its kind', async () => {
    const { mock, build } = await openCheck();
    for (const [family, n] of SEVEN.map(([f], i) => [f, i + 1] as const)) {
      expect(text(row(family)?.querySelector('.font-mono'))).toBe(family);              // the name as text, as drawn
      expect(text(row(family))).toContain(`${n} piece${n === 1 ? '' : 's'}`);
      expect(select(family)?.value).toBe('');
    }
    for (const [family, kind] of SEVEN) {
      await choose(select(family), kind);
      await waitForPut(mock, s => (s.furniture.words[kind] ?? []).includes(family));
    }
    await waitFor(() => status() === 'saved');
    expect(saved(mock, build.id).furniture.words).toEqual({
      sanitary: ['TF2092P', 'TF0560P', 'A$C2619574F'], bed: ['A$C238E5230'], 'coffee-table': ['A$C5BF14633'],
      'bar-table': ['SmartTable'], sofa: [HERMAN],
    });
    for (const [family, kind] of SEVEN) expect(select(family)?.value, family).toBe(kind);
    // No kind (grey) takes one out again
    await choose(select('A$C238E5230'), '');
    await waitForPut(mock, s => s.furniture.words.bed === undefined);
    await waitFor(() => status() === 'saved');
    expect(select('A$C238E5230')?.value).toBe('');
  });

  it('a word saved before in the acceptance settings\' way shows its kind and is replaced, not doubled', async () => {
    const { mock, build } = await openCheck({ sanitary: ['TF2092 P', 'klkjlll'], bed: ['A$C238 E5230'] });
    expect(select('TF2092P')?.value).toBe('sanitary');
    expect(select('A$C238E5230')?.value).toBe('bed');
    expect(select('TF0560P')?.value).toBe('');
    await choose(select('TF2092P'), 'cabinet');
    const put = await waitForPut(mock, s => (s.furniture.words.cabinet ?? []).includes('TF2092P'));
    expect(put.settings.furniture.words).toEqual({ sanitary: ['klkjlll'], bed: ['A$C238 E5230'], cabinet: ['TF2092P'] });
    await waitFor(() => status() === 'saved');
    expect(saved(mock, build.id).furniture.words.sanitary).toEqual(['klkjlll']);
    expect(select('TF2092P')?.value).toBe('cabinet');
  });
});

describe('the Floors step: the furniture size limits are build options', () => {
  it('shown with their help, saved the existing way; empty depth is no limit; out of bounds is said', async () => {
    const mock = createMockApi();
    const { build } = draftOf(mock, 'bank-sampeng', ['I1201.dwg'], { finish: true, reviewed: true });
    await openStep(mock, build.id, 'floors');
    const size = await waitFor(() => q('[data-testid=build-options] [data-testid=option-min-size]') as HTMLInputElement | null);
    const depth = q('[data-testid=build-options] [data-testid=option-min-depth]') as HTMLInputElement;
    expect([size.value, depth.value, depth.placeholder]).toEqual(['0.08', '', 'no limit']);
    const options = text(q('[data-testid=build-options]'));
    for (const t of ['Leave out furniture shorter than', MIN_SIZE_HELP, 'Leave out furniture thinner than', MIN_DEPTH_HELP]) {
      expect(options).toContain(t);
    }
    await enter(size, '0.25');
    await waitForPut(mock, s => s.furniture.minSize === 0.25 && s.furniture.minDepth === null);
    await enter(depth, '0,25');                                                    // a comma is a decimal point
    await waitForPut(mock, s => s.furniture.minSize === 0.25 && s.furniture.minDepth === 0.25);
    await waitFor(() => status() === 'saved');
    expect([saved(mock, build.id).furniture.minSize, saved(mock, build.id).furniture.minDepth]).toEqual([0.25, 0.25]);
    await enter(depth, '');
    await waitForPut(mock, s => s.furniture.minDepth === null && s.furniture.minSize === 0.25);
    await waitFor(() => status() === 'saved');
    expect(depth.value).toBe('');
    // out of bounds: said on the step at once; the API refuses it, and the next change saves
    const puts = settingsPuts(mock).length;
    await enter(size, '12');
    await waitFor(() => q('[data-testid=option-limit-issues]'));
    expect(text(q('[data-testid=option-limit-issues]'))).toBe('the smallest piece is 0 - 10 m');
    await waitFor(() => status() === 'error');
    expect(settingsPuts(mock).length).toBeGreaterThan(puts);
    await enter(size, '0.3');
    await waitForPut(mock, s => s.furniture.minSize === 0.3);
    await waitFor(() => status() === 'saved');
    expect(q('[data-testid=option-limit-issues]')).toBeNull();
    expect(saved(mock, build.id).furniture.minSize).toBe(0.3);
  });
});
