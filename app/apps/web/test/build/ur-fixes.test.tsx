// UR (the review-and-fix step of the upload milestone, docs/upload/contract-issues/UR.md): the staff screens' fixes against
// the mock API, each with the case a verifier found.
//   V3-1 / V3-2  the Save step's office select keeps the build saveable; "New office..." shows its name field;
//   V2-1         the Floors step's build options (outline suggestions, furniture pieces, the offset's Reset);
//   V2-2         the loss alert counts placements; V2-3 a settings save keeps the decoded plan (no refit);
//   V2-4 / V3-4 / V3-9  the reading can be cancelled and read again; a failed conversion shows 'failed' with its note;
//   V2-5 / V2-6 / V2-12  the Layers chip stays visible, suggestions to check are marked and filtered, the table fits;
//   V2-9         a frozen page says the API is not answering; V2-10 the upload rows; V2-11 the units select and votes;
//   V2-13        the Check step's hint, Fit / zoom and flag filter, the Floors hint line; V2-14 a run started elsewhere;
//   V2-15        a Thai name with a number makes no id '31'.
import path from 'node:path';
import { act } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { CANVAS_HINT } from '@/build/CheckStep';
import { STARTED_ELSEWHERE } from '@/build/BuildStep';
import { setUploadOptionsForTests } from '@/pages/UploadPage';
import type { BuildOverlay, Flag } from '@/upload/contracts';
import { choose, click, enter, press, text, typeInto, waitFor } from '../helpers';
import { createMockApi, type MockApi } from '../mock-api/core';
import { FIXTURES_DIR } from '../mock-api/fixtures';
import { closeAll, draftOf, fastClocks, openApp, q, qa, settingsPuts, waitForPut } from './app';
import { fakePlan, lastCanvas } from './fake-plan';

vi.mock('@walkthrough/viewer', async () => vi.importActual('../fake-viewer'));
vi.mock('@/plan', async importOriginal => {
  const real = await importOriginal<typeof import('@/plan')>();
  const fake = await import('./fake-plan');
  return { ...real, PlanCanvas: fake.FakePlanCanvas, nearLayers: fake.fakeNearLayers, proposeAreas: fake.fakeProposeAreas };
});
vi.setConfig({ testTimeout: 60_000 });

let restoreClocks = () => undefined as void;
beforeEach(() => { restoreClocks = fastClocks(); fakePlan.reset(); setUploadOptionsForTests({ sleep: async () => undefined, storage: () => null }); });
afterEach(async () => { restoreClocks(); setUploadOptionsForTests(null); await closeAll(); });

async function openStep(mock: MockApi, buildId: string, step: string) {
  const app = await openApp(`/projects/bank-sampeng/builds/${buildId}?step=${step}`, { mock });
  await waitFor(() => q(`[data-testid=build-page][data-step=${step}]`));
  return app;
}
const status = () => q('[data-testid=settings-status]')?.dataset.status;
const row = (layer: string) => q(`[data-testid=layer-row][data-layer="${CSS.escape(layer)}"]`);
const startRunElsewhere = (mock: MockApi, buildId: string) =>
  mock.handle({ method: 'POST', path: `/api/projects/bank-sampeng/builds/${buildId}/run`, headers: {}, body: '{}' });

// ================================================================================================================ Save
describe('V3-1 / V3-2 the office at save time', () => {
  it('picking the office of a project with none keeps the build saveable, and the version takes it', async () => {
    const mock = createMockApi();
    const { build } = draftOf(mock, 'bank-sampeng', ['I1201.dwg'], { built: true });
    const app = await openStep(mock, build.id, 'save');
    const select = await waitFor(() => q('[data-testid=save-office] [data-testid=office-select]'));
    await waitFor(() => select.querySelector('option[value="dwp-revit"]'));
    expect((q('[data-testid=save-build]') as HTMLButtonElement).disabled).toBe(false);
    await choose(select, 'dwp-revit');
    await waitForPut(mock, s => s.office === 'dwp-revit');
    await waitFor(() => q('[data-testid=remember-mapping]') && status() === 'saved');
    expect(q('[data-testid=save-stale]')).toBeNull();
    await waitFor(() => !(q('[data-testid=save-build]') as HTMLButtonElement).disabled);
    expect(settingsPuts(mock).length).toBe(1);
    await click(q('[data-testid=save-build]'));
    await waitFor(() => app.router.state.location.pathname === '/projects/bank-sampeng/v/3');
    expect(mock.uploads.versionSettings('bank-sampeng', 3)?.office).toBe('dwp-revit');
  });

  it('"New office..." shows its name field, sends nothing until the name gives an id, then keeps Save open', async () => {
    const mock = createMockApi();
    const { build } = draftOf(mock, 'bank-sampeng', ['I1201.dwg'], { built: true });
    await openStep(mock, build.id, 'save');
    const select = await waitFor(() => q('[data-testid=save-office] [data-testid=office-select]')) as HTMLSelectElement;
    await choose(select, '__new__');
    const field = await waitFor(() => q('[data-testid=new-office-name]'));
    expect(select.value).toBe('__new__');
    expect(settingsPuts(mock).length).toBe(0);
    await enter(field, 'Bangkok Studio');
    await waitForPut(mock, s => s.office === 'bangkok-studio');
    await waitFor(() => q('[data-testid=remember-mapping]') && status() === 'saved');
    expect(q('[data-testid=save-stale]')).toBeNull();
    expect(settingsPuts(mock).length).toBe(1);
  });

  it('on the Floors step, "New office..." keeps the office already set until a new name is given', async () => {
    const mock = createMockApi();
    const { build } = draftOf(mock, 'bank-sampeng', ['I1201.dwg'], { finish: true, reviewed: true });
    build.settings.office = 'dwp-revit';
    await openStep(mock, build.id, 'floors');
    const select = await waitFor(() => q('[data-testid=project-details] [data-testid=office-select]')) as HTMLSelectElement;
    await waitFor(() => select.value === 'dwp-revit');
    await choose(select, '__new__');
    await waitFor(() => q('[data-testid=new-office-name]'));
    expect(settingsPuts(mock).length).toBe(0);
    expect(mock.uploads.build('bank-sampeng', build.id)!.settings.office).toBe('dwp-revit');
    await choose(select, 'dwp-revit');                                   // back to the same office: still nothing sent
    expect(q('[data-testid=new-office-name]')).toBeNull();
    expect(settingsPuts(mock).length).toBe(0);
  });
});

// ============================================================================================================== Floors
describe('V2-1 the build options on the Floors step', () => {
  it('outline suggestions, furniture pieces and the offset\'s Reset are staff settings now', async () => {
    const mock = createMockApi();
    const { build } = draftOf(mock, 'bank-sampeng', ['I1201.dwg'], { finish: true, reviewed: true });
    build.settings.options.offset = [1.212, 0.348];                    // pinned from the project's versions (U-9.6)
    await openStep(mock, build.id, 'floors');
    const offset = await waitFor(() => q('[data-testid=option-offset]'));
    expect(offset.dataset.offset).toBe('1.212,0.348');
    await choose(q('[data-testid=option-outline-walls]'), 'suggest');
    await waitForPut(mock, s => s.options.outlineWalls === 'suggest');
    await choose(q('[data-testid=option-piece-layer]'), 'drawn');
    await waitForPut(mock, s => s.furniture.pieceLayer === 'drawn');
    await click(q('[data-testid=offset-reset]'));
    await waitForPut(mock, s => s.options.offset === 'auto');
    await waitFor(() => q('[data-testid=option-offset]')?.dataset.offset === 'auto');
    expect(q('[data-testid=offset-reset]')).toBeNull();
  });

  it('the hint line is always there, so the sheet does not move when Draw a box starts; the Source select fits', async () => {
    const mock = createMockApi();
    const { build } = draftOf(mock, 'bank-sampeng', ['I1201.dwg'], { finish: true, reviewed: true });
    await openStep(mock, build.id, 'floors');
    await waitFor(() => q('[data-testid=fake-canvas]'));
    const line = q('[data-testid=floors-tool-line]');
    expect(line?.nextElementSibling?.getAttribute('data-testid')).toBe('floors-canvas');
    await click(q('[data-testid=area-box]'));
    await click(await waitFor(() => q('[data-testid=area-draw]')));
    await waitFor(() => q('[data-testid=floors-tool]'));
    expect(q('[data-testid=floors-tool-line]')).toBe(line);                // the same line, not one more above the sheet
    expect(line?.nextElementSibling?.getAttribute('data-testid')).toBe('floors-canvas');
    expect(q('[data-testid=floor-source]')?.className).toContain('w-full');
  });
});

// =============================================================================================================== Files
describe('the Files step', () => {
  it('V2-2: a loss names the placements of lost blocks, never "4 items"', async () => {
    const mock = createMockApi();
    const { build, sources } = draftOf(mock, 'bank-sampeng', ['layout presidential test.dwg'], { finish: true });
    mock.uploads.config.conversionFixture[sources[0]!.sha1] = path.join(FIXTURES_DIR, 'upload', 'conversion', 'presidential.conversion.json');
    await openStep(mock, build.id, 'files');
    const alert = await waitFor(() => q('[data-testid=loss-advice]'));
    expect(text(alert)).toContain('4 placements of lost blocks are in the plan');
    expect(text(alert)).not.toContain('4 items did not come through');
    expect(text(q('[data-testid=source-notes]'))).toContain('8,254 of 142,182');
  });

  it('V2-4 / V3-4: the reading can be cancelled, then read again to a proposal', async () => {
    const mock = createMockApi();
    mock.uploads.config.hold = true;
    const { build } = draftOf(mock, 'bank-sampeng', ['I1201.dwg']);
    await openStep(mock, build.id, 'files');
    const cancel = await waitFor(() => q('[data-testid=run-panel][data-kind=prepare] [data-testid=cancel-run]'));
    await click(cancel);
    await waitFor(() => mock.requests.some(r => r.method === 'POST' && r.path.endsWith('/cancel')));
    await waitFor(() => q('[data-testid=run-panel][data-kind=prepare][data-status=cancelled]'));
    expect(text(q('[data-testid=run-advice]'))).toBe('The reading was cancelled: read the drawings again, or delete this draft.');
    mock.uploads.config.hold = false;
    await click(await waitFor(() => q('[data-testid=read-again]')));
    await waitFor(() => q('[data-testid=build-page]')?.dataset.revision === '1');
    expect(mock.uploads.build('bank-sampeng', build.id)!.runs.filter(r => r.info.kind === 'prepare').length).toBe(2);
    expect(q('[data-testid=read-again]')).toBeNull();
  });

  it('V3-9: a failed conversion shows "failed" with its note, and can be read again', async () => {
    const mock = createMockApi();
    mock.uploads.config.failPrepare = { code: 'convert_failed', message: 'it could not be converted: the converter took longer than 120 s and was stopped' };
    const { build } = draftOf(mock, 'bank-sampeng', ['I1201.dwg']);
    await openStep(mock, build.id, 'files');
    const badge = await waitFor(() => q('[data-testid=source-verdict][data-verdict=failed]'));
    expect(text(badge)).toBe('failed');
    expect(text(q('[data-testid=source-notes]'))).toContain('the converter took longer than 120 s');
    expect(q('[data-testid=read-again]')).not.toBeNull();
  });

  it('V2-11: no units change while a run goes; units against the door votes are said', async () => {
    const mock = createMockApi();
    const { build } = draftOf(mock, 'bank-sampeng', ['I1201.dwg'], { finish: true, reviewed: true });
    build.settings.sources[0]!.units = 'm';                              // metres on the bank's millimetre drawing
    await openStep(mock, build.id, 'files');
    const warn = await waitFor(() => q('[data-testid=units-against-votes]'));
    expect(text(warn)).toContain('measure right in millimetres');
    expect((q('[data-testid=units-select]') as HTMLSelectElement).disabled).toBe(false);
    mock.uploads.config.hold = true;
    expect(startRunElsewhere(mock, build.id).status).toBe(202);
    await act(async () => { await click(q('[data-testid=step-build]')); });
    await waitFor(() => q('[data-testid=checklist-item][data-level=warn]'));
    expect(text(q('[data-testid=checklist-item][data-level=warn]'))).toContain('I1201.dwg: its door symbols measure right in millimetres');
    await click(q('[data-testid=step-files]'));
    await waitFor(() => (q('[data-testid=units-select]') as HTMLSelectElement | null)?.disabled === true);
  });
});

// ============================================================================================================== Layers
describe('the Layers step', () => {
  it('V2-5: the close-to-walls chip is never inside the truncated name', async () => {
    fakePlan.near = new Set(['A-FLOR']);
    const mock = createMockApi();
    const { build } = draftOf(mock, 'bank-sampeng', ['I1201.dwg'], { finish: true, reviewed: true });
    await openStep(mock, build.id, 'layers');
    await waitFor(() => row('A-FLOR')?.querySelector('[data-testid=role-select]:not([disabled])'));
    await choose(row('A-FLOR')!.querySelector('[data-testid=role-select]'), 'ignore');
    const chip = await waitFor(() => row('A-FLOR')!.querySelector('[data-testid=close-to-walls]'));
    expect(chip.closest('.truncate')).toBeNull();
    expect(chip.className).toContain('shrink-0');
    expect(row('A-FLOR')!.querySelector('[data-testid=layer-name] .truncate')?.textContent).toBe('A-FLOR');
  });

  it('V2-6 / V2-12: suggestions to check are marked and filtered; plain words; the table fits its width', async () => {
    const mock = createMockApi();
    const { build } = draftOf(mock, 'bank-sampeng', ['I1201.dwg'], { finish: true, reviewed: true });
    // the suggester's real answer for the bank's room-name layer (the mock's fixture is provisional)
    build.suggestions['G-ANNO-TEXT'] = { role: 'ignore', from: 'name', evidence: ['named like an ignore layer (*ANNO*)',
      'named like an ignore layer, but only texts (12), such as BA, BE, UP ...'] };
    await openStep(mock, build.id, 'layers');
    await waitFor(() => row('G-ANNO-TEXT'));
    const check = row('G-ANNO-TEXT')!.querySelector('[data-testid=suggestion-check]');
    expect(check?.getAttribute('title')).toContain('the name and the contents disagree');
    expect(row('A-WALL')!.querySelector('[data-testid=suggestion-check]')).toBeNull();
    expect(text(row('A-WALL')!.querySelector('[data-testid=layer-suggestion]'))).toBe('Walls · by name');
    await click(row('G-ANNO-TEXT'));
    expect(text(q('[data-testid=layer-check-reason]'))).toContain('Check this one: the name and the contents disagree');
    const all = qa('[data-testid=layer-row]').length;
    await click(q('[data-testid=layers-to-check]'));
    await waitFor(() => qa('[data-testid=layer-row]').length < all);
    expect(qa('[data-testid=layer-row]').every(r => r.querySelector('[data-testid=suggestion-check]'))).toBe(true);
    expect(qa('[data-testid=layer-row]').map(r => r.dataset.layer)).toContain('G-ANNO-TEXT');
    expect((qa('[data-testid=role-select]')[0] as HTMLSelectElement).className).toContain('w-full');
    expect(q('[data-testid=roles-legend]')?.textContent).toContain('Not built (kept as context)');
  });
});

// =============================================================================================================== Check
describe('the Check step', () => {
  async function openCheck(extraFlags: BuildOverlay['flags'] = []) {
    const mock = createMockApi();
    mock.uploads.config.extraFlags = extraFlags;
    const { build } = draftOf(mock, 'bank-sampeng', ['I1201.dwg', 'I1202.dwg'], { built: true });
    const app = await openStep(mock, build.id, 'check');
    await waitFor(() => q('[data-testid=fake-canvas][data-overlay=L1]'));
    return { app, mock, build };
  }

  it('V2-3: a settings save keeps the decoded plan, so the canvas keeps its view', async () => {
    const { mock } = await openCheck();
    const plan0 = lastCanvas().plan;
    const key = plan0.keyAt(0);
    await act(async () => { lastCanvas().onSelect!([key], 'replace'); });
    await click(q('[data-testid=set-aside]'));
    await waitForPut(mock, s => s.fixes.setAside.length === 1);
    await waitFor(() => status() === 'saved' && q('[data-testid=set-aside-row]'));
    expect(lastCanvas().plan).toBe(plan0);
    await click(q('[data-testid=restore-one]'));
    await waitForPut(mock, s => s.fixes.setAside.length === 0);
    await waitFor(() => status() === 'saved' && !q('[data-testid=set-aside-row]'));
    expect(lastCanvas().plan).toBe(plan0);
  });

  it('V2-13: the canvas says how it works and has Fit / zoom buttons; the flags filter by kind and severity', async () => {
    const flag = (id: string, kind: Flag['kind'], severity: Flag['severity']): Flag =>
      ({ id, kind, floor: 'L1', severity, title: id, detail: '', at: [1, 1], bbox: null, ref: {} });
    await openCheck([flag('single-line:L1:a', 'single-line', 'check'), flag('single-line:L1:b', 'single-line', 'check'),
      flag('plate-dropped:L1:c', 'plate-dropped', 'info')]);
    expect(text(q('[data-testid=canvas-help] p'))).toBe(CANVAS_HINT);
    expect(q('[data-testid=canvas-fit]')).not.toBeNull();
    expect(q('[data-testid=canvas-zoom-in]')).not.toBeNull();
    // the buttons press the canvas's own keys on its <canvas>
    const canvas = document.createElement('canvas');
    const keys: string[] = [];
    canvas.addEventListener('keydown', e => keys.push((e as KeyboardEvent).key));
    q('[data-testid=check-canvas]')!.appendChild(canvas);
    await click(q('[data-testid=canvas-zoom-in]'));
    await click(q('[data-testid=canvas-zoom-out]'));
    await click(q('[data-testid=canvas-fit]'));
    expect(keys).toEqual(['+', '-', 'f']);
    canvas.remove();
    const all = qa('[data-testid=flag]').length;
    await choose(q('[data-testid=flag-kind-filter]'), 'single-line');
    await waitFor(() => qa('[data-testid=flag]').length === 2);
    expect(qa('[data-testid=flag]').every(f => f.dataset.kind === 'single-line')).toBe(true);
    await choose(q('[data-testid=flag-kind-filter]'), '');
    await waitFor(() => qa('[data-testid=flag]').length === all);
    await click(q('[data-testid=flag-check-only]'));
    await waitFor(() => qa('[data-testid=flag]').length < all);
    expect(qa('[data-testid=flag]').every(f => f.dataset.severity === 'check')).toBe(true);
  });

  it('V3-5: a long set-aside list is windowed', async () => {
    const mock = createMockApi();
    const { build } = draftOf(mock, 'bank-sampeng', ['I1201.dwg', 'I1202.dwg'], { built: true });
    const src = build.sources[0]!;
    build.settings.fixes.setAside = Array.from({ length: 3000 }, (_, i) => ({ floor: 'L1', source: src, key: `K${i}`, sig: '0'.repeat(12), rsig: '', elementId: null, layer: 'A-WALL', note: '' }));
    await openStep(mock, build.id, 'check');
    await waitFor(() => q('[data-testid=set-aside-scroll]'));
    expect(q('[data-testid=set-aside-scroll]')?.hasAttribute('data-windowed')).toBe(true);
    expect(qa('[data-testid=set-aside-row]').length).toBeLessThan(40);
    expect(text(q('[data-testid=set-aside-list] h4'))).toBe('Set aside on this floor (3,000)');
  });
});

// ================================================================================================== runs and the API
describe('runs', () => {
  it('V2-14: Build in a tab that did not start the running build shows and polls that build', async () => {
    const mock = createMockApi();
    const { build } = draftOf(mock, 'bank-sampeng', ['I1201.dwg'], { built: true, reviewed: true });
    await openStep(mock, build.id, 'build');
    await waitFor(() => !(q('[data-testid=run-build]') as HTMLButtonElement).disabled);
    mock.uploads.config.hold = true;
    expect(startRunElsewhere(mock, build.id).status).toBe(202);            // another tab pressed Build
    await click(q('[data-testid=run-build]'));
    await waitFor(() => q('[data-testid=build-error]'));
    expect(text(q('[data-testid=build-error]'))).toBe(STARTED_ELSEWHERE);
    await waitFor(() => q('[data-testid=run-panel][data-kind=build][data-status=queued]'));
    mock.uploads.config.hold = false;
    await waitFor(() => q('[data-testid=run-panel][data-kind=build][data-status=done]'));
  });

  it('V2-9: while the API does not answer, the page says so; it goes once the API is back', async () => {
    const mock = createMockApi();
    const { build } = draftOf(mock, 'bank-sampeng', ['I1201.dwg'], { built: true, reviewed: true });
    mock.uploads.config.hold = true;
    expect(startRunElsewhere(mock, build.id).status).toBe(202);
    let down = false;
    const bad = () => new Response(JSON.stringify({ error: { code: 'bad_gateway', message: 'the API is not answering' } }),
      { status: 502, headers: { 'content-type': 'application/json' } });
    await openApp(`/projects/bank-sampeng/builds/${build.id}?step=build`, {
      mock, fetch: { intercept: (m, p) => (down && m === 'GET' && p.includes('/builds/') ? bad() : undefined) },
    });
    await waitFor(() => q('[data-testid=run-panel][data-kind=build]'));
    expect(q('[data-testid=api-not-answering]')).toBeNull();
    down = true;
    await waitFor(() => q('[data-testid=api-not-answering]'));
    expect(text(q('[data-testid=api-not-answering]'))).toContain('The API is not answering');
    down = false;
    await waitFor(() => !q('[data-testid=api-not-answering]'));
  });
});

// ============================================================================================================= uploads
describe('the Upload screen', () => {
  const dwg = (name: string, size: number) => new File([new Uint8Array([65, 67, 49, 48, 51, 50, ...Array(Math.max(0, size - 6)).fill(1)])], name, { lastModified: 1 });
  async function pick(files: File[]) {
    const input = await waitFor(() => q('[data-testid=file-input]') as HTMLInputElement | null);
    await act(async () => {
      Object.defineProperty(input, 'files', { value: files, configurable: true });
      input.dispatchEvent(new Event('change', { bubbles: true }));
    });
  }

  it('V2-10: a file refused for good has no Retry, says its size in MB, and the screen says to remove it', async () => {
    const mock = createMockApi();
    mock.uploads.config.maxUploadBytes = 1_000_000;
    await openApp('/projects/bank-sampeng/builds/new', { mock });
    await pick([dwg('huge.dwg', 1_500_000), dwg('plan.dwg', 40)]);
    await waitFor(() => q('[data-testid=upload-row][data-name="huge.dwg"][data-state=failed]') && q('[data-testid=upload-row][data-name="plan.dwg"][data-state=done]'));
    const huge = q('[data-testid=upload-row][data-name="huge.dwg"]')!;
    expect(huge.querySelector('[data-testid=upload-retry]')).toBeNull();
    expect(text(huge.querySelector('[data-testid=upload-error]'))).toBe('Not uploaded: huge.dwg is 1.5 MB; at most 1.0 MB can be uploaded');
    expect(text(q('[data-testid=remove-failed-hint]'))).toBe('Remove the file that was not uploaded to continue with the others.');
    expect((q('[data-testid=start-build]') as HTMLButtonElement).disabled).toBe(true);
    await click(huge.querySelector('[data-testid=upload-remove]'));
    await waitFor(() => !(q('[data-testid=start-build]') as HTMLButtonElement).disabled);
    expect(q('[data-testid=remove-failed-hint]')).toBeNull();
  });

  it('V2-8: leaving the screen mid-upload keeps the session (no cancel sent)', async () => {
    const mock = createMockApi();
    mock.uploads.config.partBytes = 1000;
    let release: () => void = () => undefined;
    const gate = new Promise<void>(r => { release = r; });
    const app = await openApp('/projects/bank-sampeng/builds/new', {
      mock, fetch: { intercept: async (m, p) => { if (m === 'PUT' && p.endsWith('/parts/2')) await gate; return undefined; } },
    });
    await pick([dwg('slow.dwg', 3500)]);
    await waitFor(() => mock.uploads.sessions().length === 1 && mock.uploads.sessions()[0]!.received.includes(1));
    await act(async () => { await app.router.navigate('/projects'); });
    release();
    await waitFor(() => q('[data-testid=projects-page]') || q('[data-testid=project-card]'));
    expect(mock.requests.some(r => r.method === 'DELETE' && r.path.startsWith('/api/uploads/'))).toBe(false);
    expect(mock.uploads.sessions().length).toBe(1);
  });
});

// ========================================================================================================= new project
describe('V2-15 a new project\'s id', () => {
  it('a Thai name with a number makes no id of its digits: the API derives project-<6 hex>', async () => {
    const mock = createMockApi();
    const app = await openApp('/projects/new', { mock });
    await typeInto(await waitFor(() => q('[data-testid=np-name]')), 'บ้านสุขุมวิท ซอย 31');
    await press(q('[data-testid=np-name]'), 'Enter');
    await act(async () => { (q('form') as HTMLFormElement).requestSubmit(); });
    await waitFor(() => /^\/projects\/project-[0-9a-f]{6}\/builds\/new$/.test(app.router.state.location.pathname));
    const body = JSON.parse(mock.requests.find(r => r.method === 'POST' && r.path === '/api/projects')!.body!);
    expect(body.id).toBeNull();
  });
});
