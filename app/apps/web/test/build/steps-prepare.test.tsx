// The Build page's first three steps against the mock API (docs/upload/DESIGN.md U-2 5a - 5c, U-7.4, U-8, U-9, U-14.3;
// ACCEPTANCE 2.3 U6): Files (verdicts, notes, lost blocks, the units control disabled before the proposal, a units
// change re-reading one source and locking Floors), Layers (role labels and help, the close-to-walls chip, filters,
// apply to the rows shown, 400 rows windowed, layersReviewed with the first save), Floors (keys, levels rising, an area
// from a proposal or drawn, pad / match under Advanced, the level-tag list, align methods with points picked, the office
// select, a new floor). U7's canvas is replaced by test/build/fake-plan.tsx.
import path from 'node:path';
import { act } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { ROLES } from '@/build/roles';
import type { DrawingRead } from '@/upload/contracts';
import { choose, click, enter, settle, text, typeInto, waitFor } from '../helpers';
import { createMockApi } from '../mock-api/core';
import { FIXTURES_DIR, readJson } from '../mock-api/fixtures';
import { closeAll, draftOf, fastClocks, openApp, q, qa, settingsPuts, waitForPut } from './app';
import { fakePlan, lastCanvas } from './fake-plan';

vi.mock('@walkthrough/viewer', async () => vi.importActual('../fake-viewer'));
vi.mock('@/plan', async importOriginal => {
  const real = await importOriginal<typeof import('@/plan')>();
  const fake = await import('./fake-plan');
  return { ...real, PlanCanvas: fake.FakePlanCanvas, nearLayers: fake.fakeNearLayers, proposeAreas: fake.fakeProposeAreas };
});

vi.setConfig({ testTimeout: 60_000 });

const U = (...p: string[]) => path.join(FIXTURES_DIR, 'upload', ...p);
let restoreClocks = () => undefined as void;
beforeEach(() => { restoreClocks = fastClocks(); fakePlan.reset(); document.title = ''; });
afterEach(async () => { restoreClocks(); await closeAll(); });

describe('Files', () => {
  it('verdicts, units with their door votes; the units select disabled until the proposal is in; a change re-reads that source', async () => {
    const mock = createMockApi();
    mock.uploads.config.adopt = false;
    const { build, sources } = draftOf(mock, 'bank-sampeng', ['I1201 - LEVEL 1.dwg', 'I1202 - LEVEL 2.dwg'], { finish: true });
    const app = await openApp(`/projects/bank-sampeng/builds/${build.id}?step=files`, { mock });
    await waitFor(() => qa('[data-testid=source-card] [data-testid=units-select]').length === 2);
    expect(document.title).toBe('Bangkok Bank, Sampeng Branch · draft · Walkthrough');
    const cards = qa('[data-testid=source-card]');
    expect(cards.map(c => text(c.querySelector('[data-testid=source-name]')))).toEqual(['I1201 - LEVEL 1.dwg', 'I1202 - LEVEL 2.dwg']);
    expect(cards.map(c => c.querySelector('[data-testid=source-verdict]')?.getAttribute('data-verdict'))).toEqual(['ok', 'ok']);
    await waitFor(() => text(cards[0]!.querySelector('[data-testid=units-votes]')) === 'Door votes: mm 16');
    expect(cards[0]!.querySelector('[data-testid=units-verdict]')?.getAttribute('data-verdict')).toBe('agree');
    const select = () => q('[data-testid=source-card] [data-testid=units-select]') as HTMLSelectElement;
    expect(select().disabled).toBe(true);                                       // revision 0: nothing can be saved
    expect(q('[data-testid=step-layers]')?.hasAttribute('disabled')).toBe(true);
    // the API adopts the proposal at the next request that sees the prepare done (the page keeps polling for it)
    mock.uploads.config.adopt = true;
    await waitFor(() => !select().disabled);
    expect(q('[data-testid=step-layers]')?.hasAttribute('disabled')).toBe(false);
    // a units change: saved (units and confirmed), that source read again; Floors locked meanwhile
    mock.uploads.config.hold = true;
    await choose(select(), 'in');
    const put = await waitForPut(mock, s => s.sources[0]!.units === 'in');
    expect(put.settings.sources[0]).toMatchObject({ sha1: sources[0]!.sha1, units: 'in', unitsConfirmed: true });
    await waitFor(() => q('[data-testid=units-rereading]'));
    await act(async () => { await app.router.navigate(`/projects/bank-sampeng/builds/${build.id}?step=floors`); });
    const lock = await waitFor(() => q('[data-testid=floors-locked]'));
    expect(text(lock)).toBe('Reading I1201 - LEVEL 1.dwg again in inches...');
    expect((q('[data-testid=floor-level]') as HTMLInputElement).disabled).toBe(true);
    mock.uploads.config.hold = false;
    await waitFor(() => !q('[data-testid=floors-locked]'));
    expect(mock.uploads.build('bank-sampeng', build.id)!.runs.at(-1)!.info.only).toEqual([sources[0]!.sha1]);
  });

  it('a loss: the red verdict, the AutoCAD advice, the lost blocks and their inserts on the sheet; Start again with other files', async () => {
    const mock = createMockApi();
    const { build, sources } = draftOf(mock, 'bank-sampeng', ['layout presidential test.dwg'], {});
    mock.uploads.config.conversionFixture[sources[0]!.sha1] = U('conversion', 'presidential.conversion.json');
    mock.uploads.finishRuns('bank-sampeng', build.id);
    const app = await openApp(`/projects/bank-sampeng/builds/${build.id}`, { mock });
    const card = await waitFor(() => q('[data-testid=source-card] [data-verdict=loss]')?.closest('[data-testid=source-card]'));
    expect(text(card.querySelector('[data-testid=loss-advice]'))).toContain('export a DXF from AutoCAD for a complete build');
    expect(text(card.querySelector('[data-testid=source-notes]'))).toContain('8,254 of 142,182');
    const lost = await waitFor(() => card.querySelector('[data-testid=lost-blocks]'));
    expect(lost.querySelectorAll('[data-testid=lost-block]').length).toBeGreaterThan(0);
    await click(card.querySelector('[data-testid=show-lost-sheet]'));
    const canvas = await waitFor(() => card.querySelector('[data-testid=fake-canvas]'));
    const report = readJson(U('conversion', 'presidential.conversion.json')) as { lostBlocks: { inserts: unknown[] }[] };
    expect(Number(canvas.getAttribute('data-flags'))).toBe(report.lostBlocks.reduce((a, b) => a + b.inserts.length, 0));
    await click(q('[data-testid=start-again]'));
    await waitFor(() => app.router.state.location.pathname === '/projects/bank-sampeng/builds/new');
    expect(app.router.state.location.search).toBe(`?from=${build.id}`);
  });
});

describe('Layers', () => {
  async function openLayers(opts: { reviewed?: boolean; drawing?: DrawingRead } = {}) {
    const mock = createMockApi();
    const { build, sources } = draftOf(mock, 'bank-sampeng', ['I1201.dwg', 'I1202.dwg'], { finish: true, reviewed: opts.reviewed });
    const before = structuredClone(build.settings);
    const app = await openApp(`/projects/bank-sampeng/builds/${build.id}?step=layers`, {
      mock,
      fetch: opts.drawing ? {
        intercept: (m, p) => (m === 'GET' && p === `/api/projects/bank-sampeng/builds/${build.id}/sources/${sources[0]!.sha1}/drawing`
          ? new Response(JSON.stringify(opts.drawing), { headers: { 'content-type': 'application/json' } }) : undefined),
      } : undefined,
    });
    await waitFor(() => qa('[data-testid=layer-row]').length > 0 && q('[data-testid=layer-row] [data-testid=role-select]:not([disabled])'));
    return { app, mock, build, before };
  }
  const row = (name: string) => q(`[data-testid=layer-row][data-layer="${name}"]`);

  it('seeing the step once sends layersReviewed with no change; every row\'s select shows the 17 labels with their help', async () => {
    const { mock, build, before } = await openLayers();
    const put = await waitForPut(mock, (_s, u) => u.layersReviewed === true);
    expect(put.settings).toEqual(before);                                       // an otherwise unchanged save
    expect(settingsPuts(mock, build.id).length).toBe(1);
    await waitFor(() => mock.uploads.build('bank-sampeng', build.id)!.layersReviewedAt !== null);
    const options = [...row('A-WALL')!.querySelectorAll('[data-testid=role-select] option')];
    expect(options.map(o => o.textContent)).toEqual(ROLES.map(r => r.label));
    expect(options.map(o => o.getAttribute('title'))).toEqual(ROLES.map(r => r.help));
    expect((row('A-WALL')!.querySelector('[data-testid=role-select]') as HTMLSelectElement).value).toBe('wall');
    expect(row('A-WALL')!.querySelector('[data-testid=layer-suggestion]')?.getAttribute('data-from')).toBe('name');
  });

  it('a role changed with its select: saved with layersReviewed; the canvas lights the hovered layer', async () => {
    const { mock } = await openLayers({ reviewed: true });
    await choose(row('A-GLAZ-CWMG')!.querySelector('[data-testid=role-select]'), 'window');
    const put = await waitForPut(mock, s => s.layers['A-GLAZ-CWMG'] === 'window');
    expect(put.layersReviewed).toBe(true);
    expect(put.ifMatch).toBe('"1"');
    await act(async () => { row('S-COLS')!.dispatchEvent(new MouseEvent('mouseover', { bubbles: true })); });
    await waitFor(() => lastCanvas().highlightLayer !== null && lastCanvas().plan.layers[lastCanvas().highlightLayer!] === 'S-COLS');
  });

  it('filters (search, role, unmapped) and "apply to all rows shown"', async () => {
    const { mock } = await openLayers({ reviewed: true });
    const all = qa('[data-testid=layer-row]').length;
    await typeInto(q('[data-testid=layers-search]'), 'a-anno');
    await waitFor(() => qa('[data-testid=layer-row]').length === 3);
    expect(qa('[data-testid=layer-row]').map(r => r.dataset.layer)).toEqual(['A-ANNO-DIMS', 'A-ANNO-DIMS-100', 'A-ANNO-NOTE']);
    expect(q('[data-testid=apply-role-button]')?.textContent).toBe('Apply to 3');
    await choose(q('[data-testid=apply-role]'), 'other');
    await click(q('[data-testid=apply-role-button]'));
    await waitForPut(mock, s => ['A-ANNO-DIMS', 'A-ANNO-DIMS-100', 'A-ANNO-NOTE'].every(n => s.layers[n] === 'other'));
    await typeInto(q('[data-testid=layers-search]'), '');
    await choose(q('[data-testid=layers-role-filter]'), 'door');
    await waitFor(() => qa('[data-testid=layer-row]').length > 0 && qa('[data-testid=layer-row]').every(r => r.dataset.role === 'door'));
    await choose(q('[data-testid=layers-role-filter]'), '');
    await click(q('[data-testid=layers-unmapped]'));
    await waitFor(() => qa('[data-testid=layer-row]').length < all);
    const settings = mock.uploads.build('bank-sampeng', qa('[data-testid=build-page]')[0]!.dataset.buildId!)!.settings;
    expect(qa('[data-testid=layer-row]').every(r => !(r.dataset.layer! in settings.layers))).toBe(true);
  });

  it('an ignore row with items close to wall-role lines carries the chip', async () => {
    fakePlan.near = new Set(['A-FLOR']);
    const { mock } = await openLayers({ reviewed: true });
    expect(row('A-FLOR')!.querySelector('[data-testid=close-to-walls]')).toBeNull();      // other: no chip
    await choose(row('A-FLOR')!.querySelector('[data-testid=role-select]'), 'ignore');
    const chip = await waitFor(() => row('A-FLOR')!.querySelector('[data-testid=close-to-walls]'));
    expect(chip.getAttribute('title')).toBe('close to walls: ignoring it can change which doors and windows are found');
    expect(row('A-ANNO-DIMS')!.querySelector('[data-testid=close-to-walls]')).toBeNull();  // ignore, but not near
    await waitForPut(mock, s => s.layers['A-FLOR'] === 'ignore');
  });

  it('400 layers: the rows are windowed (a slice drawn, the rest spacers), scrolling shows the others', async () => {
    const base = readJson(U('drawing', 'bank1.drawing.json')) as DrawingRead;
    const proto = base.layers.find(l => l.name === 'A-WALL')!;
    const many = { ...base, layers: Array.from({ length: 400 }, (_, i) => ({ ...proto, name: `LAYER-${String(i).padStart(3, '0')}` })) };
    await openLayers({ reviewed: true, drawing: many });
    await waitFor(() => q('[data-testid=layers-count]')?.textContent?.startsWith('4'));
    expect(q('[data-testid=layers-table]')?.hasAttribute('data-windowed')).toBe(true);
    const drawn = () => qa('[data-testid=layer-row]').map(r => r.dataset.layer!);
    const total = Number(q('[data-testid=layers-count]')!.textContent!.split(' of ')[1]!.replace(/[^0-9]/g, ''));
    expect(total).toBeGreaterThan(400);
    expect(drawn().length).toBeLessThan(60);
    expect(drawn()).toContain('0');
    expect(drawn()).not.toContain('LAYER-305');
    const scroll = q('[data-testid=layers-scroll]')!;
    const at = [...many.layers.map(l => l.name)].indexOf('LAYER-305');
    await act(async () => { scroll.scrollTop = 36 * (at + 20); scroll.dispatchEvent(new Event('scroll')); });
    await settle();
    expect(drawn()).toContain('LAYER-305');
    expect(drawn()).not.toContain('0');
    expect(drawn().length).toBeLessThan(60);
  });
});

describe('Floors', () => {
  async function openFloors(opts: { levelTags?: boolean } = {}) {
    const mock = createMockApi();
    const { build, sources } = draftOf(mock, 'bank-sampeng', ['I1201.dwg', 'I1202.dwg'], {});
    if (opts.levelTags) mock.uploads.config.drawingFixture[sources[1]!.sha1] = U('drawing', 'sukhumvit.drawing.json');
    mock.uploads.finishRuns('bank-sampeng', build.id);
    const app = await openApp(`/projects/bank-sampeng/builds/${build.id}?step=floors`, { mock });
    await waitFor(() => qa('[data-testid=floor-card]').length === 2 && !(q('[data-testid=floor-level]') as HTMLInputElement).disabled);
    return { app, mock, build, sources };
  }
  const card = (i: number) => q(`[data-testid=floor-card][data-index="${i}"]`)!;
  const field = (i: number, id: string) => card(i).querySelector<HTMLElement>(`[data-testid=${id}]`);

  it('levels typed (0 and 3.7, as A-7 types them), keys and names; levels must rise (said before the API refuses it)', async () => {
    const { mock } = await openFloors();
    expect(qa('[data-testid=floor-card]').map(c => c.dataset.key)).toEqual(['L1', 'L2']);
    await enter(field(0, 'floor-level'), '0');
    await enter(field(1, 'floor-level'), '3,7');
    await enter(field(1, 'floor-name'), 'Level 2 (mezzanine)');
    await waitForPut(mock, s => s.floors[1]!.name === 'Level 2 (mezzanine)' && s.floors[1]!.level === 3.7 && s.floors[0]!.level === 0);
    await enter(field(1, 'floor-level'), '-1');
    const issues = await waitFor(() => q('[data-testid=floor-issues]'));
    expect(text(issues)).toContain('the levels must rise floor by floor: Level 2 (mezzanine) is not above Level 1');
    await waitFor(() => q('[data-testid=settings-issues]'));          // the API's 422 shown too
    expect(text(q('[data-testid=settings-issues]'))).toContain('levels must increase');
    await enter(field(1, 'floor-key'), 'L 2');
    await waitFor(() => text(q('[data-testid=floor-issues]')).includes('"L 2" is not a floor key'));
  });

  it('an area: a box from a proposal (pad 0.5, match all by default), pad and match under Advanced, a box drawn on the sheet', async () => {
    const { mock } = await openFloors();
    await click(field(0, 'area-box'));
    const drawing = readJson(U('drawing', 'bank1.drawing.json')) as DrawingRead;
    await waitForPut(mock, s => s.floors[0]!.area.kind === 'box');
    const proposal = await waitFor(() => card(0).querySelector('[data-testid=area-proposal][data-id=a1]'));
    expect(proposal.textContent).toBe('a1 (plan, 19 x 28 m)');
    await click(proposal);
    const put = await waitForPut(mock, s => s.floors[0]!.area.kind === 'box' && s.floors[0]!.area.bbox[0] === drawing.areas[0]!.bbox[0]);
    expect(put.settings.floors[0]!.area).toEqual({ kind: 'box', bbox: drawing.areas[0]!.bbox, pad: 0.5, match: 'all' });
    const advanced = card(0).querySelector('[data-testid=area-advanced]')!;
    expect(text(advanced)).toContain('how far outside the box a line may reach');
    expect(text(advanced)).toContain('all: a line must lie wholly inside; any: one point inside is enough, for a plan that touches its neighbours');
    await enter(advanced.querySelector('[data-testid=area-pad]'), '1');
    await choose(advanced.querySelector('[data-testid=area-match]'), 'any');
    await waitForPut(mock, s => s.floors[0]!.area.kind === 'box' && s.floors[0]!.area.pad === 1 && s.floors[0]!.area.match === 'any');
    await click(field(0, 'area-draw'));
    await waitFor(() => lastCanvas().tool === 'draw-box');
    await act(async () => { lastCanvas().onBox!([5, 6, 1, 2]); });
    await waitForPut(mock, s => JSON.stringify(s.floors[0]!.area) === JSON.stringify({ kind: 'box', bbox: [1, 2, 5, 6], pad: 1, match: 'any' }));
    expect(lastCanvas().tool).toBe('pan');
  });

  it('the level-tag list: all the source\'s tags with their labels, by value; hover marks one on the sheet, a click takes it', async () => {
    const { mock } = await openFloors({ levelTags: true });
    const drawing = readJson(U('drawing', 'sukhumvit.drawing.json')) as DrawingRead;
    const tags = await waitFor(() => (card(1).querySelectorAll('[data-testid=level-tag]').length ? [...card(1).querySelectorAll<HTMLElement>('[data-testid=level-tag]')] : null));
    expect(tags.length).toBe(drawing.levelTags.length);
    const values = tags.map(t => Number(t.dataset.value));
    expect(values).toEqual([...values].sort((a, b) => a - b));
    const withLabel = drawing.levelTags.find(t => t.label)!;
    expect(tags.some(t => t.textContent!.includes(withLabel.label!))).toBe(true);
    const tag = tags.find(t => Number(t.dataset.value) === 4.8)!;
    await act(async () => { tag.dispatchEvent(new MouseEvent('mouseover', { bubbles: true })); });
    await waitFor(() => lastCanvas().focus !== null && (lastCanvas().flags ?? []).some(f => f.id === 'mark:level'));
    await click(tag);
    await waitForPut(mock, s => s.floors[1]!.level === 4.8);
  });

  it('alignment: grid, origin, or two points picked on both sheets; wall height default; a new floor; the office select', async () => {
    const { mock } = await openFloors();
    expect(card(0).querySelector('[data-testid=align-method]')).toBeNull();      // the first floor is the reference
    await choose(field(1, 'align-method'), 'grid');
    await waitForPut(mock, s => s.floors[1]!.align.method === 'grid');
    await choose(field(1, 'align-method'), 'points');
    await waitFor(() => field(1, 'align-pick-0-0'));
    await click(field(1, 'align-pick-0-0'));
    await waitFor(() => lastCanvas().tool === 'pick-point');
    await act(async () => { lastCanvas().onPick!([1.2346, 2]); });
    await click(field(1, 'align-pick-0-1'));
    await waitFor(() => lastCanvas().tool === 'pick-point');
    await act(async () => { lastCanvas().onPick!([75.25, 2]); });
    const put = await waitForPut(mock, s => s.floors[1]!.align.method === 'points' && (s.floors[1]!.align as { pairs: number[][][] }).pairs[0]![1]![0] === 75.25);
    expect((put.settings.floors[1]!.align as { pairs: unknown }).pairs).toEqual([[[1.235, 2], [75.25, 2]], [[0, 0], [0, 0]]]);
    // wall height: empty -> the default offered (next level - this level)
    await typeInto(field(0, 'floor-wall-height'), '');
    await enter(field(0, 'floor-wall-height'), '');
    const use = await waitFor(() => field(0, 'use-default-height'));
    expect(use.textContent).toBe('Use 3 m (to the next level)');               // the proposal's levels: 0 and 3.00
    await click(use);
    await waitForPut(mock, s => s.floors[0]!.wallHeight === 3);
    await click(q('[data-testid=add-floor]'));
    await waitForPut(mock, s => s.floors.length === 3 && s.floors[2]!.key === 'L3');
    await choose(q('[data-testid=project-details] [data-testid=office-select]'), 'dwp-revit');
    await waitForPut(mock, s => s.office === 'dwp-revit');
  });
});
