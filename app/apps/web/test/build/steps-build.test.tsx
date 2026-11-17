// The Build page's last three steps against the mock API (docs/upload/DESIGN.md U-2 5d - 5f, U-3.4, U-11.1, U-12, U-14.3;
// ACCEPTANCE 2.3 U6): the pre-build checklist (each line to its step), Build with its progress, "Stopping..." after
// Cancel (Cancel disabled), a failed run's error and advice, the 3D preview made and disposed; the Check tools writing the
// right fixes (an ItemRef with every field from the plan entry; one whole-block ref; Esc and Delete; an opening fix; an
// outline suggestion; a grey family's kind), the diff after a rebuild; Save disabled in flight (a double click makes one
// version) and leading to the version; a DXF with hostile names walked through every step: no element injected.
import path from 'node:path';
import { gunzipSync } from 'node:zlib';
import { readFileSync } from 'node:fs';
import { act } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { BuildOverlay, PlanGeometry } from '@/upload/contracts';
import { fakeViewerLog, resetFakeViewer } from '../fake-viewer';
import { choose, click, enter, press, stubWebGL, text, typeInto, waitFor } from '../helpers';
import { createMockApi, type MockApi } from '../mock-api/core';
import { FIXTURES_DIR, readJson } from '../mock-api/fixtures';
import { HOSTILE } from '../mock-api/synthetic';
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
const PLAN1 = JSON.parse(gunzipSync(readFileSync(U('plan', 'bank1.plan.json.gz'))).toString('utf8')) as PlanGeometry;
let restoreClocks = () => undefined as void;
let restoreWebGL = () => undefined as void;
beforeEach(() => { restoreClocks = fastClocks(); fakePlan.reset(); resetFakeViewer(); restoreWebGL = stubWebGL(); });
afterEach(async () => { restoreClocks(); restoreWebGL(); await closeAll(); });

async function openStep(mock: MockApi, buildId: string, step: string) {
  const app = await openApp(`/projects/bank-sampeng/builds/${buildId}?step=${step}`, { mock });
  await waitFor(() => q(`[data-testid=build-page][data-step=${step}]`));
  return app;
}
const runs = (mock: MockApi, buildId: string) => mock.uploads.build('bank-sampeng', buildId)!.runs;

describe('Build', () => {
  it('the checklist names what blocks and links to its step; once clear, Build runs with its progress to the result', async () => {
    const mock = createMockApi();
    const { build } = draftOf(mock, 'bank-sampeng', ['I1201.dwg', 'I1202.dwg'], { finish: true });
    const app = await openStep(mock, build.id, 'build');
    const item = await waitFor(() => q('[data-testid=checklist-item][data-id=layers]'));
    expect(text(item)).toContain('Look through the Layers step once');
    expect((q('[data-testid=run-build]') as HTMLButtonElement).disabled).toBe(true);
    await click(item.querySelector('[data-testid=checklist-link]'));
    await waitFor(() => app.router.state.location.search === '?step=layers');
    await waitFor(() => mock.uploads.build('bank-sampeng', build.id)!.layersReviewedAt !== null);
    await click(q('[data-testid=step-build]'));
    await waitFor(() => q('[data-testid=checklist-clear]'));
    await waitFor(() => !(q('[data-testid=run-build]') as HTMLButtonElement).disabled);
    await click(q('[data-testid=run-build]'));
    await waitFor(() => q('[data-testid=run-panel][data-kind=build]'));
    const statuses = new Set<string>();
    await waitFor(() => {
      const p = q('[data-testid=run-panel][data-kind=build]');
      if (p) statuses.add(p.dataset.status!);
      return q('[data-testid=build-result]');
    });
    expect(statuses.has('running') || statuses.has('queued')).toBe(true);
    const steps = qa('[data-testid=run-step]').map(s => s.dataset.step);
    expect(steps).toEqual(['ensure', 'align', 'detect:L1', 'detect:L2', 'walls', 'openings', 'furniture', 'outputs', 'validate']);
    expect(qa('[data-testid=run-step]').every(s => s.dataset.status === 'done')).toBe(true);
    expect(qa('[data-testid=result-floor]').map(r => r.dataset.key)).toEqual(['L1', 'L2']);
    expect(q('[data-testid=result-flags]')?.dataset.total).toBe('17');
    expect(q('[data-testid=result-topview]')?.getAttribute('src')).toBe(`/api/projects/bank-sampeng/builds/${build.id}/topview`);
    expect(q('[data-testid=step-check]')?.hasAttribute('disabled')).toBe(false);
  });

  it('Cancel: "Stopping..." and Cancel disabled until the run stops; then Cancelled', async () => {
    const mock = createMockApi();
    const { build } = draftOf(mock, 'bank-sampeng', ['I1201.dwg'], { finish: true, reviewed: true });
    mock.uploads.config.hold = true;
    mock.uploads.config.cancelAfter = 4;
    await openStep(mock, build.id, 'build');
    await waitFor(() => !(q('[data-testid=run-build]') as HTMLButtonElement).disabled);
    await click(q('[data-testid=run-build]'));
    const cancel = await waitFor(() => q('[data-testid=cancel-run]') as HTMLButtonElement | null);
    await click(cancel);
    await waitFor(() => q('[data-testid=run-stopping]'));
    expect(text(q('[data-testid=run-status]'))).toBe('Stopping...');
    expect((q('[data-testid=cancel-run]') as HTMLButtonElement).disabled).toBe(true);
    await waitFor(() => q('[data-testid=run-panel][data-status=cancelled]'));
    expect(q('[data-testid=cancel-run]')).toBeNull();
    expect(q('[data-testid=run-error]')?.getAttribute('data-code')).toBe('cancelled');
  });

  it('a failed run shows its error and what to change', async () => {
    const mock = createMockApi();
    const { build } = draftOf(mock, 'bank-sampeng', ['I1201.dwg'], { finish: true, reviewed: true });
    mock.uploads.config.failBuild = { code: 'area_empty', message: 'Level 1 has no walls in its area.' };
    await openStep(mock, build.id, 'build');
    await waitFor(() => !(q('[data-testid=run-build]') as HTMLButtonElement).disabled);
    await click(q('[data-testid=run-build]'));
    await waitFor(() => q('[data-testid=run-panel][data-status=failed]'));
    expect(text(q('[data-testid=run-error-message]'))).toBe('Level 1 has no walls in its area.');
    expect(text(q('[data-testid=run-advice]'))).toMatch(/area on the Floors step/);
    expect(q('[data-testid=run-step][data-step="detect:L1"]')?.dataset.status).toBe('failed');
  });

  it('the 3D preview: a viewer on the draft (version 0, heights by the host), disposed when closed', async () => {
    const mock = createMockApi();
    const { build } = draftOf(mock, 'bank-sampeng', ['I1201.dwg', 'I1202.dwg'], { built: true });
    await openStep(mock, build.id, 'build');
    await click(await waitFor(() => q('[data-testid=open-preview]')));
    await waitFor(() => window.__fakeViewer?.live() === 1);
    const made = fakeViewerLog.find(r => r.event === 'create')!;
    expect(made.options).toMatchObject({ build: 'skip', furnitureHeights: 'host' });
    expect([made.projectId, made.version, made.stamp]).toEqual(['bank-sampeng', 0, 'c3a9408304a2']);
    expect([made.heights, made.pictures, made.hasStages]).toEqual([{}, {}, true]);
    await waitFor(() => mock.requests.some(r => r.method === 'GET' && r.path === '/api/projects/bank-sampeng/versions/2'));
    await act(async () => { await new Promise(r => setTimeout(r, 20)); });
    expect(q('[data-testid=preview-deleted-boxes]')).toBeNull();      // v2 has no deleted boxes: no line
    await click(q('[data-testid=close-preview]'));
    await waitFor(() => window.__fakeViewer!.live() === 0);
    expect(q('[data-testid=draft-preview]')).toBeNull();
  });

  it("the 3D preview shows every box of the draft: one line says v2's deleted boxes are applied when it is saved", async () => {
    const mock = createMockApi();
    mock.setSaved('bank-sampeng', 2, {}, { 'L1-table-005': { removed: true } });     // closed: the table and its computer
    const { build } = draftOf(mock, 'bank-sampeng', ['I1201.dwg', 'I1202.dwg'], { built: true });
    await openStep(mock, build.id, 'build');
    await click(await waitFor(() => q('[data-testid=open-preview]')));
    const line = await waitFor(() => q('[data-testid=preview-deleted-boxes]'));
    expect(text(line)).toBe("v2's 2 deleted boxes are applied when you save, where the same box is in the same place.");
    expect(line.closest('[data-testid=draft-preview]')).not.toBeNull();
  });
});

describe('Check', () => {
  async function openCheck(extraFlags: BuildOverlay['flags'] = []) {
    const mock = createMockApi();
    mock.uploads.config.extraFlags = extraFlags;
    const { build, sources } = draftOf(mock, 'bank-sampeng', ['I1201.dwg', 'I1202.dwg'], { built: true });
    const app = await openStep(mock, build.id, 'check');
    await waitFor(() => q('[data-testid=fake-canvas][data-overlay=L1]'));
    return { app, mock, build, sources };
  }

  it('Set aside the selected item: one ItemRef with every field from the plan entry; Restore takes it back; Esc and Delete', async () => {
    const { mock, sources } = await openCheck();
    const i = PLAN1.items.eid.findIndex((e, n) => e >= 0 && PLAN1.items.type[n] !== 5);
    const key = PLAN1.items.key[i]!;
    await act(async () => { lastCanvas().onSelect!([key], 'replace'); });
    expect(text(q('[data-testid=selection-count]'))).toBe('1 selected');
    await click(q('[data-testid=set-aside]'));
    const put = await waitForPut(mock, s => s.fixes.setAside.length === 1);
    expect(put.settings.fixes.setAside[0]).toEqual({
      floor: 'L1', source: sources[0]!.sha1, key, sig: PLAN1.items.sig[i], rsig: PLAN1.items.rsig[i],
      elementId: PLAN1.elementIds[PLAN1.items.eid[i]!], layer: PLAN1.layers[PLAN1.items.layer[i]!], note: '',
    });
    await waitFor(() => lastCanvas().setAside.has(key));
    expect(q(`[data-testid=set-aside-row][data-key="${key}"]`)).not.toBeNull();
    await act(async () => { lastCanvas().onSelect!([key], 'replace'); });
    await click(q('[data-testid=restore]'));
    await waitForPut(mock, s => s.fixes.setAside.length === 0 && settingsPuts(mock).length >= 2);
    // keyboard: Esc clears the selection, Delete sets it aside
    const other = PLAN1.items.key.find((k, n) => PLAN1.items.type[n] === 0 && k !== key)!;
    await act(async () => { lastCanvas().onSelect!([other], 'replace'); });
    await press(q('[data-testid=check-canvas]'), 'Escape');
    expect(text(q('[data-testid=selection-count]'))).toBe('0 selected');
    await act(async () => { lastCanvas().onSelect!([other], 'add'); });
    await press(q('[data-testid=check-canvas]'), 'Delete');
    await waitForPut(mock, s => s.fixes.setAside.length === 1 && s.fixes.setAside[0]!.key === other);
  });

  it('the whole-block pick mode: an item found inside a block selects its INSERT anchor; one ref in the settings', async () => {
    const { mock } = await openCheck();
    await choose(q('[data-testid=pick-mode]'), 'block');
    await waitFor(() => lastCanvas().pick === 'block');
    const child = PLAN1.items.key.find((k, n) => k.split('/').length === 3 && PLAN1.items.type[n] !== 5)!;
    await typeInto(q('[data-testid=find-items]'), child);
    await click(await waitFor(() => q(`[data-testid=find-result][data-key="${child}"]`)));
    const anchor = [...lastCanvas().selected][0]!;
    expect(child.startsWith(`${anchor}/`)).toBe(true);
    expect(PLAN1.items.type[PLAN1.items.key.indexOf(anchor)]).toBe(5);
    await click(q('[data-testid=set-aside]'));
    const put = await waitForPut(mock, s => s.fixes.setAside.length === 1);
    expect(put.settings.fixes.setAside.map(r => r.key)).toEqual([anchor]);
  });

  it('an opening: kind, head and sill -> fixes.openings with its ends as detected; from the canvas or its flag', async () => {
    const { mock } = await openCheck();
    const overlay = readJson(U('overlay', 'bank.overlay.json')) as BuildOverlay;
    const o = overlay.floors[0]!.openings[0]!;
    await act(async () => { lastCanvas().onOpening!(o.id); });
    const editor = await waitFor(() => q('[data-testid=opening-editor]'));
    expect(editor.dataset.opening).toBe(o.id);
    await choose(editor.querySelector('[data-testid=opening-kind]'), 'door');
    await enter(editor.querySelector('[data-testid=opening-head]'), '2.4');
    await click(editor.querySelector('[data-testid=opening-apply]'));
    const put = await waitForPut(mock, s => s.fixes.openings.length === 1);
    expect(put.settings.fixes.openings[0]).toEqual({ floor: 'L1', a: o.a, b: o.b, kind: 'door', head: 2.4, sill: null });
    const flag = q('[data-testid=flag][data-kind=opening] [data-testid=flag-opening]');
    await click(flag);
    await waitFor(() => q('[data-testid=opening-editor]'));
  });

  it('an outline suggestion: Wall / Glass / Refuse -> fixes.outlineEdges; a grey family -> furniture.words[kind]', async () => {
    const edge: [[number, number], [number, number]] = [[1, 2], [4, 2]];
    const { mock } = await openCheck([
      { id: 'outline-wall:L1:aaaaaaaaaaaa', kind: 'outline-wall', floor: 'L1', severity: 'check', title: 'A wall here?', detail: 'a free edge of a room outline', at: [2.5, 2], bbox: null, ref: { edge } },
      { id: 'grey-furniture:L1:bbbbbbbbbbbb', kind: 'grey-furniture', floor: 'L1', severity: 'info', title: 'Mystery-Box: 3 grey boxes', detail: 'The furniture kit does not know what Mystery-Box is, so its 3 pieces are grey. Pick a kind for the family.', at: null, bbox: null, ref: { family: 'Mystery-Box' } },
    ]);
    const outline = await waitFor(() => q('[data-testid=flag][data-kind=outline-wall]'));
    await click(outline.querySelector('[data-testid=outline-wall]'));
    await waitForPut(mock, s => s.fixes.outlineEdges.length === 1 && s.fixes.outlineEdges[0]!.as === 'wall');
    await waitFor(() => outline.querySelector('[data-testid=flag-outline]')?.getAttribute('data-as') === 'wall');
    await click(outline.querySelector('[data-testid=outline-refuse]'));
    const put = await waitForPut(mock, s => s.fixes.outlineEdges.length === 1 && s.fixes.outlineEdges[0]!.as === 'none');
    expect(put.settings.fixes.outlineEdges[0]).toEqual({ floor: 'L1', a: [1, 2], b: [4, 2], as: 'none' });
    const family = await waitFor(() => q('[data-testid=furniture-family][data-family="Mystery-Box"]'));
    expect(text(family)).toContain('3 pieces');
    await choose(family.querySelector('[data-testid=furniture-word-kind]'), 'cabinet');
    await waitForPut(mock, s => (s.furniture.words.cabinet ?? []).includes('Mystery-Box'));
  });

  it('Rebuild after a set-aside: the screen keeps the last result, then the diff against the previous build shows the change', async () => {
    const { mock, build } = await openCheck();
    const key = PLAN1.items.key.find((k, n) => PLAN1.items.type[n] === 0)!;
    await act(async () => { lastCanvas().onSelect!([key], 'replace'); });
    await click(q('[data-testid=set-aside]'));
    await waitForPut(mock, s => s.fixes.setAside.length === 1);
    await waitFor(() => q('[data-testid=check-stale]'));
    await waitFor(() => !(q('[data-testid=rebuild]') as HTMLButtonElement).disabled);
    await click(q('[data-testid=rebuild]'));
    await waitFor(() => runs(mock, build.id).filter(r => r.info.kind === 'build').length === 2);
    expect(q('[data-testid=fake-canvas]')).not.toBeNull();               // the last result stays on screen
    const row = await waitFor(() => q('[data-testid=diff-panel][data-against=previous-run] [data-testid=diff-row][data-floor=L1][data-what=parts]'));
    const [before, after] = [...row.querySelectorAll('td')].slice(2).map(td => Number(td.textContent));
    expect(before! - after!).toBe(1);
    await click(q('[data-testid=diff-draw]'));
    await waitFor(() => lastCanvas().diff !== null && lastCanvas().diff !== undefined);
  });

  it('the heights: a floor\'s wall height and the project\'s door head saved from the Check step', async () => {
    const { mock } = await openCheck();
    await enter(await waitFor(() => q('[data-testid=check-wall-height]')), '3.5');
    await enter(q('[data-testid=check-door-head]'), '2.3');
    await waitForPut(mock, s => s.floors[0]!.wallHeight === 3.5 && s.defaults.doorHead === 2.3);
  });
});

describe('Save', () => {
  it('the default label, the summary, carry heights (ticked), the office select when there is none; Save once, then the version', async () => {
    const mock = createMockApi();
    const { build } = draftOf(mock, 'bank-sampeng', ['I1201.dwg', 'I1202.dwg'], { built: true });
    let release!: () => void;
    const gate = new Promise<void>(r => { release = r; });
    const app = await openApp(`/projects/bank-sampeng/builds/${build.id}?step=save`, {
      mock,
      fetch: { intercept: async (m, p) => { if (m === 'POST' && p.endsWith('/save')) await gate; return undefined; } },
    });
    const label = await waitFor(() => q('[data-testid=save-label]') as HTMLInputElement | null);
    expect(label.value).toMatch(/^\d{1,2} [A-Z][a-z]{2} \d{4}: built from I1201\.dwg, I1202\.dwg$/);
    expect(text(q('[data-testid=save-stamp]'))).toBe('c3a9408304a2');
    expect(q('[data-testid=carry-heights]')?.getAttribute('data-state')).toBe('checked');
    expect(q('[data-testid=remember-mapping]')).toBeNull();               // no office: the select instead
    expect(q('[data-testid=save-office] [data-testid=office-select]')).not.toBeNull();
    const save = q('[data-testid=save-build]') as HTMLButtonElement;
    await act(async () => { save.click(); save.click(); });
    await waitFor(() => (q('[data-testid=save-build]') as HTMLButtonElement).disabled);
    expect(q('[data-testid=save-build]')?.textContent).toBe('Saving...');
    release();
    await waitFor(() => app.router.state.location.pathname === '/projects/bank-sampeng/v/3');
    const saves = mock.requests.filter(r => r.method === 'POST' && r.path.endsWith('/save'));
    expect(saves.length).toBe(1);
    expect(JSON.parse(saves[0]!.body!)).toEqual({ label: label.value, carryHeights: true, rememberMapping: false });
    expect(mock.version('bank-sampeng', 3)?.label).toBe(label.value);
  });

  it('with an office: "Remember these layer roles for <office>"; a stale build cannot be saved until it is built again', async () => {
    const mock = createMockApi();
    const { build } = draftOf(mock, 'bank-sampeng', ['I1201.dwg'], { built: true });
    build.settings.office = 'dwp-revit';
    build.settings.layers['A-WALL'] = 'other';                            // the settings changed since the build (not
    build.revision++;                                                     // only the office: UR, V3-1)
    await openApp(`/projects/bank-sampeng/builds/${build.id}?step=save`, { mock });
    await waitFor(() => q('[data-testid=remember-mapping]'));
    await waitFor(() => text(q('[data-testid=remember-field]')) === 'Remember these layer roles for DWP (Revit)');
    expect(q('[data-testid=save-stale]')).not.toBeNull();
    expect((q('[data-testid=save-build]') as HTMLButtonElement).disabled).toBe(true);
  });

  it('a saved draft is read-only and links to its version', async () => {
    const mock = createMockApi();
    const { build } = draftOf(mock, 'bank-sampeng', ['I1201.dwg'], { built: true });
    expect(mock.handle({ method: 'POST', path: `/api/projects/bank-sampeng/builds/${build.id}/save`, body: JSON.stringify({ label: 'v3', carryHeights: false, rememberMapping: false }) }).status).toBe(201);
    await openApp(`/projects/bank-sampeng/builds/${build.id}?step=layers`, { mock });
    await waitFor(() => q('[data-testid=build-saved]'));
    expect(text(q('[data-testid=build-saved]'))).toContain('saved as v3');
    expect(qa('[data-testid=role-select]').every(s => (s as HTMLSelectElement).disabled)).toBe(true);
  });
});

describe('drawing text stays text (A-7 second test, in the unit tests)', () => {
  it('a DXF with hostile layer, block, text and file names through every step: shown as text, nothing injected', async () => {
    const mock = createMockApi();
    const file = 'x<img src=x onerror=alert(5)>.dxf';
    const { build } = draftOf(mock, 'bank-sampeng', [file], { built: true });
    const app = await openApp(`/projects/bank-sampeng/builds/${build.id}?step=files`, { mock });
    await waitFor(() => q('[data-testid=source-name]'));
    expect(text(q('[data-testid=source-name]'))).toBe(file);
    for (const step of ['layers', 'floors', 'build', 'check', 'save']) {
      await act(async () => { await app.router.navigate(`/projects/bank-sampeng/builds/${build.id}?step=${step}`); });
      await waitFor(() => q(`[data-testid=build-page][data-step=${step}]`));
      if (step === 'layers') {
        await waitFor(() => q(`[data-testid=layer-row][data-layer="${CSS.escape(HOSTILE.wall)}"]`));
        expect(text(q(`[data-testid=layer-row][data-layer="${CSS.escape(HOSTILE.door)}"] [data-testid=layer-name]`))).toBe(HOSTILE.door);
      }
      expect(document.querySelectorAll('img:not([data-testid=result-topview]):not([data-testid=card-thumbnail])').length).toBe(0);
      expect(document.querySelectorAll('script').length).toBe(0);
    }
    expect(document.body.textContent).toContain(file);
    expect((window as { __pwned?: unknown }).__pwned).toBeUndefined();
  });
});
