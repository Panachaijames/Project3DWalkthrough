// R6 (docs/rooms/ACCEPTANCE.md 2.3 R6; DESIGN.md R-1.3, R-5.1, R-6.1 - R-6.4, R-12.6): the staff screens of the rooms
// milestone over the mock API (the reference building: test/mock-api/rooms.ts) with the plan canvas replaced by
// test/build/fake-plan.tsx (a test plays the canvas's callbacks): the line and its button on the Floors, Build and Check
// steps and the checklist's line; the Floors step's ceiling heights and the fold; the Build and Save steps' three
// counts; the Check step's ticks, counts, tools, panels, flag cards' buttons, the fixes list with Remove and "waiting for
// Rebuild", the set-aside tick, the Heights panel's ceiling height; the hint under an old plate-dropped flag; a lost
// floor first in the changes; each new flag kind with its text; drawing and staff text as text only.
import { act } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { DiffPanel } from '@/build/DiffPanel';
import { FLAG_KIND_TEXT, FlagList } from '@/build/FlagList';
import { RULES_EARLIER_TEXT, RULES_NEW_TEXT } from '@/build/settingsEdit';
import { sel, TID } from '@/build/testids';
import { marksOf } from '@/plan/marks';
import { setUploadOptionsForTests } from '@/pages/UploadPage';
import { NEW_RULES, OLD_RULES, type BuildDiff, type BuildSettings, type Flag } from '@/upload/contracts';
import { choose, click, enter, render, text, waitFor } from '../helpers';
import { createMockApi, type MockApi } from '../mock-api/core';
import { FIXTURES_DIR, readJson } from '../mock-api/fixtures';
import { ROOMS_FILES } from '../mock-api/rooms';
import { closeAll, draftOf, fastClocks, openApp, q, qa, settingsPuts, waitForPut } from '../build/app';
import { fakePlan, lastCanvas } from '../build/fake-plan';

vi.mock('@walkthrough/viewer', async () => vi.importActual('../fake-viewer'));
vi.mock('@/plan', async importOriginal => {
  const real = await importOriginal<typeof import('@/plan')>();
  const fake = await import('../build/fake-plan');
  return { ...real, PlanCanvas: fake.FakePlanCanvas, nearLayers: fake.fakeNearLayers, proposeAreas: fake.fakeProposeAreas };
});
vi.setConfig({ testTimeout: 60_000 });

let restoreClocks = () => undefined as void;
beforeEach(() => { restoreClocks = fastClocks(); fakePlan.reset(); setUploadOptionsForTests({ sleep: async () => undefined, storage: () => null }); });
afterEach(async () => { restoreClocks(); setUploadOptionsForTests(null); await closeAll(); });

const REF_FILES = ['rooms-reference-ground.dxf', 'rooms-reference-upper.dxf'];
const PID = 'bank-sampeng';
async function openStep(mock: MockApi, buildId: string, step: string) {
  const app = await openApp(`/projects/${PID}/builds/${buildId}?step=${step}`, { mock });
  await waitFor(() => q(`[data-testid=build-page][data-step=${step}]`));
  return app;
}
const status = () => q('[data-testid=settings-status]')?.dataset.status;
const saved = () => waitFor(() => status() === 'saved');
const lastPut = (mock: MockApi) => settingsPuts(mock).at(-1)!.settings;
const by = (id: string) => q(sel(id as never));
const canvas = () => waitFor(() => { try { return lastCanvas(); } catch { return null; } });

describe('the line on the Floors, Build and Check steps, and its button (R-1.3, R-12.6)', () => {
  it('a new draft is built the new way: the line says so, with no button; the checklist has no rules line', async () => {
    const mock = createMockApi();
    const { build } = draftOf(mock, PID, REF_FILES, { reviewed: true });
    expect(build.settings.options).toMatchObject(NEW_RULES);
    await openStep(mock, build.id, 'floors');
    const line = await waitFor(() => by(TID.rulesLine));
    expect(line.dataset.rules).toBe('new');
    expect(text(line)).toBe(RULES_NEW_TEXT);
    expect(by(TID.rulesUseNew)).toBeNull();
    await click(q('[data-testid=step-build]'));
    await waitFor(() => q('[data-testid=build-page][data-step=build]'));
    expect(by(TID.rulesLine)?.dataset.rules).toBe('new');
    expect(by(TID.checklistRules)).toBeNull();
  });

  it('a draft built the earlier way: the line with its button on the three steps; the button sets the three options in one save', async () => {
    const mock = createMockApi();
    const { build } = draftOf(mock, PID, ['I1201.dwg'], { built: true });
    // a settings document of before the milestone (no keys): the mock, as the API, writes the old values out
    const bank = readJson(`${FIXTURES_DIR}/upload/settings/bank.json`) as BuildSettings;
    build.settings = { ...build.settings, options: { ...bank.options } };
    build.revision++;
    await openStep(mock, build.id, 'build');
    await waitFor(() => by(TID.rulesLine)?.dataset.rules === 'earlier');
    expect(text(by(TID.rulesLine))).toContain(RULES_EARLIER_TEXT);
    const warn = await waitFor(() => by(TID.checklistRules));
    expect(warn.dataset.level).toBe('warn');
    expect(text(warn)).toContain(RULES_EARLIER_TEXT);
    for (const step of ['floors', 'check']) {
      await click(q(`[data-testid=step-${step}]`));
      await waitFor(() => q(`[data-testid=build-page][data-step=${step}]`) && by(TID.rulesLine)?.dataset.rules === 'earlier');
      expect(by(TID.rulesUseNew)).not.toBeNull();
    }
    await click(by(TID.rulesUseNew));
    const put = await waitForPut(mock, s => s.options.slabs === 'network');
    expect(put.settings.options).toMatchObject(NEW_RULES);
    expect(settingsPuts(mock).length).toBe(1);
    await waitFor(() => by(TID.rulesLine)?.dataset.rules === 'new');
  });

  it('the hint under an old-rule plate-dropped flag, with its button, while the draft is built the earlier way', async () => {
    const mock = createMockApi();
    const { build } = draftOf(mock, PID, ['I1201.dwg'], { built: true });
    build.settings = { ...build.settings, options: { ...build.settings.options, ...OLD_RULES } };
    build.revision++;
    await openStep(mock, build.id, 'check');
    const card = await waitFor(() => q('[data-testid=flag][data-kind=plate-dropped]'));
    const hint = card.querySelector<HTMLElement>(sel(TID.flagEarlierHint))!;
    expect(text(hint)).toContain(RULES_EARLIER_TEXT);
    await click(hint.querySelector('button'));
    await waitForPut(mock, s => s.options.slabs === 'network');
    await waitFor(() => !q(sel(TID.flagEarlierHint)));
  });
});

describe('the Floors step: ceiling heights and the fold "Earlier build rules" (R-5.1, R-12.6)', () => {
  it('each floor\'s ceiling height has the default as its placeholder; a typed one is saved, empty is null', async () => {
    const mock = createMockApi();
    const { build } = draftOf(mock, PID, REF_FILES, { reviewed: true });
    await openStep(mock, build.id, 'floors');
    const boxes = await waitFor(() => { const b = qa(`[data-testid=floor-card] ${sel(TID.ceilingHeight)}`); return b.length === 2 ? b : null; });
    expect(boxes.map(b => (b as HTMLInputElement).placeholder)).toEqual(['2.7', '2.7']);
    await enter(boxes[1], '2.6');
    await waitForPut(mock, s => s.floors[1]?.ceilingHeight === 2.6);
    await saved();
    await enter(boxes[1], '');
    await waitForPut(mock, s => s.floors[1]?.ceilingHeight === null);
  });

  it('the fold is closed; "the earlier way" writes OLD_RULES and hides the ceilings control; ceilings off writes off', async () => {
    const mock = createMockApi();
    const { build } = draftOf(mock, PID, REF_FILES, { reviewed: true });
    await openStep(mock, build.id, 'floors');
    const fold = await waitFor(() => by(TID.earlierRules)) as HTMLDetailsElement;
    expect(fold.tagName).toBe('DETAILS');
    expect(fold.open).toBe(false);
    expect((by(TID.rulesChoice) as HTMLSelectElement).value).toBe('new');
    expect((by(TID.ceilingsChoice) as HTMLSelectElement).value).toBe('on');
    await choose(by(TID.ceilingsChoice), 'off');
    await waitForPut(mock, s => s.options.ceilings === 'off' && s.options.slabs === 'network');
    await saved();
    await choose(by(TID.rulesChoice), 'earlier');
    const put = await waitForPut(mock, s => s.options.slabs === 'closed-rooms');
    expect(put.settings.options).toMatchObject(OLD_RULES);
    await waitFor(() => !by(TID.ceilingsChoice) && by(TID.rulesLine)?.dataset.rules === 'earlier');
    await saved();
    await choose(by(TID.rulesChoice), 'new');
    expect((await waitForPut(mock, s => s.options.slabs === 'network' && s.options.ceilings === 'auto')).settings.options).toMatchObject(NEW_RULES);
  });
});

describe('the Build and Save steps: rooms closed, names placed, stairs you can climb (R-12.6; from the overlay, R5.md D-3)', () => {
  it('one row per floor with the three counts', async () => {
    const mock = createMockApi();
    const { build } = draftOf(mock, PID, REF_FILES, { built: true });
    await openStep(mock, build.id, 'build');
    const rows = await waitFor(() => { const r = qa(sel(TID.roomCounts)); return r.length === 2 ? r : null; });
    const counts = rows.map(r => [r.dataset.key, ...[TID.countRooms, TID.countNames, TID.countStairs].map(t => text(r.querySelector(sel(t))))]);
    expect(counts).toEqual([['ground', '2', '4', '1'], ['upper', '1', '1', '0']]);
    await click(q('[data-testid=step-save]'));
    await waitFor(() => q('[data-testid=build-page][data-step=save]'));
    const saveRows = await waitFor(() => { const r = qa(`[data-testid=save-summary] ${sel(TID.roomCounts)}`); return r.length === 2 ? r : null; });
    expect(text(saveRows[0]!.querySelector(sel(TID.countRooms)))).toBe('2');
  });

  it('no counts with the old rule (the overlay has no rooms)', async () => {
    const mock = createMockApi();
    const { build } = draftOf(mock, PID, ['I1201.dwg'], { built: true });
    await openStep(mock, build.id, 'build');
    await waitFor(() => q('[data-testid=result-floors]'));
    await act(async () => { await new Promise(r => setTimeout(r, 50)); });
    expect(qa(sel(TID.roomCounts))).toEqual([]);
  });
});

describe('the Check step (R-6.2, R-6.4, R-12.6)', () => {
  async function openCheck() {
    const mock = createMockApi();
    const { build } = draftOf(mock, PID, REF_FILES, { built: true });
    const app = await openStep(mock, build.id, 'check');
    await waitFor(() => by(TID.checkRooms));
    return { mock, build, app };
  }

  it('the counts of the floor on screen; the three ticks; the tools', async () => {
    await openCheck();
    const counts = () => [TID.checkRooms, TID.checkHoles, TID.checkStairsClimb, TID.checkStairs].map(t => text(by(t)));
    expect(counts()).toEqual(['2', '0', '1', '2']);
    await click(q('[data-testid=check-floor][data-key=upper]'));
    await waitFor(() => counts()[1] === '2');
    expect(counts()).toEqual(['1', '2', '0', '0']);
    expect((await canvas()).show).toEqual({ rooms: true, plate: true, furniture: true });
    await click(by(TID.showRooms));
    await waitFor(() => lastCanvas().show?.rooms === false);
    await click(by(TID.showPlate));
    await click(by(TID.showFurniture));
    await waitFor(() => lastCanvas().show?.furniture === false && lastCanvas().show?.plate === false);
    const tool = by(TID.checkTool) as HTMLSelectElement;
    expect([...tool.options].map(o => o.value).sort()).toEqual(['draw-line', 'pan', 'rooms', 'select']);
    await choose(tool, 'draw-line');
    await waitFor(() => lastCanvas().tool === 'draw-line' && by(TID.drawLineHint));
    await choose(tool, 'rooms');
    await waitFor(() => lastCanvas().tool === 'rooms' && !by(TID.drawLineHint));
  });

  it('"Draw a line" writes a closing line; it waits for the Rebuild in the list and on the plan, then is built', async () => {
    const { mock } = await openCheck();
    await choose(by(TID.checkTool), 'draw-line');
    await waitFor(() => lastCanvas().tool === 'draw-line');
    await act(async () => { lastCanvas().onLine!([8.9, 8.9], [11.8, 8.9]); });
    const put = await waitForPut(mock, s => (s.fixes.closings ?? []).length === 1);
    expect(put.settings.fixes.closings).toEqual([{ floor: 'ground', a: [8.9, 8.9], b: [11.8, 8.9], use: 'line' }]);
    const row = await waitFor(() => q(`${sel(TID.fixRow)}[data-kind=closing][data-index="0"]`));
    await waitFor(() => row.dataset.waiting === '' && row.querySelector(sel(TID.fixWaiting)));
    await waitFor(() => marksOf(lastCanvas().overlay)?.lines.length === 1);
    await saved();
    await click(q('[data-testid=rebuild]'));
    await waitFor(() => {
      const r = q(`${sel(TID.fixRow)}[data-kind=closing]`);
      return r && r.dataset.waiting === undefined && !q('[data-testid=check-stale]') ? r : null;
    });
    expect(marksOf(lastCanvas().overlay)).toBeNull();
    // the mock "built" it: the slab-gap flag is gone
    await waitFor(() => !q('[data-testid=flag][data-kind=slab-gap]'));
  });

  it('the flag cards: "Close it here", "It is outdoors", "Not a doorway: one room" write their fixes and show waiting', async () => {
    const { mock } = await openCheck();
    const gap = await waitFor(() => q('[data-testid=flag][data-kind=slab-gap]'));
    expect(gap.querySelector(sel(TID.flagCloseHere))).not.toBeNull();
    await click(gap.querySelector(sel(TID.flagOutdoors)));
    const put = await waitForPut(mock, s => (s.fixes.rooms ?? []).length === 1);
    expect(put.settings.fixes.rooms![0]).toMatchObject({ floor: 'ground', name: null, slab: 'none', ceiling: 'auto' });
    await waitFor(() => gap.querySelector(sel(TID.fixWaiting)) && (gap.querySelector(sel(TID.flagCloseHere)) as HTMLButtonElement).disabled);
    await saved();
    const door = q('[data-testid=flag][data-kind=doorway]')!;
    await click(door.querySelector(sel(TID.flagNotDoorway)));
    const put2 = await waitForPut(mock, s => (s.fixes.closings ?? []).length === 1);
    expect(put2.settings.fixes.closings).toEqual([{ floor: 'ground', a: [7, 5.6], b: [7, 6.8], use: 'none' }]);
    await waitFor(() => door.querySelector(sel(TID.fixWaiting)));
    await waitFor(() => marksOf(lastCanvas().overlay)?.removed.length === 1);
    // Remove in the list takes the doorway fix back
    await saved();
    const row = await waitFor(() => q(`${sel(TID.fixRow)}[data-kind=closing-removed]`));
    await click(row.querySelector(sel(TID.fixRemove)));
    await waitForPut(mock, s => (s.fixes.closings ?? []).length === 0 && (s.fixes.rooms ?? []).length === 1);
    await waitFor(() => !q(`${sel(TID.fixRow)}[data-kind=closing-removed]`));
  });

  it('the room panel: a name (text only), "No floor here", "No ceiling"; a place with no room: "Floor here", "It is outdoors"', async () => {
    const { mock } = await openCheck();
    await choose(by(TID.checkTool), 'rooms');
    await waitFor(() => lastCanvas().tool === 'rooms');
    await act(async () => { lastCanvas().onSpace!('ground-R002'); });
    const panel = await waitFor(() => by(TID.roomPanel));
    expect(panel.dataset.id).toBe('ground-R002');
    const [x, y] = panel.dataset.at!.split(',').map(Number);
    const hostile = 'Kitchen <img src=x onerror=alert(1)>';
    await enter(panel.querySelector(sel(TID.roomName)), hostile);
    const put = await waitForPut(mock, s => (s.fixes.rooms ?? []).some(r => r.name === hostile));
    expect(put.settings.fixes.rooms).toEqual([{ floor: 'ground', at: [x, y], name: hostile, slab: 'auto', ceiling: 'auto' }]);
    expect(document.querySelectorAll('img[src="x"], [onerror]').length).toBe(0);
    await saved();
    await click(by(TID.roomNoFloor));
    await waitForPut(mock, s => s.fixes.rooms?.[0]?.slab === 'none');
    await saved();
    await click(by(TID.roomNoCeiling));
    const put3 = await waitForPut(mock, s => s.fixes.rooms?.[0]?.ceiling === 'none');
    expect(put3.settings.fixes.rooms).toEqual([{ floor: 'ground', at: [x, y], name: hostile, slab: 'none', ceiling: 'none' }]);
    await waitFor(() => by(TID.roomPanel)?.querySelector(sel(TID.fixWaiting)));
    expect(text(q(`${sel(TID.fixRow)}[data-kind=room]`))).toContain(`named “${hostile}”, no floor here, no ceiling`);
    await saved();
    await act(async () => { lastCanvas().onPoint!([20.5, 20.25]); });
    const free = await waitFor(() => { const p = by(TID.roomPanel); return p?.dataset.id === '' ? p : null; });
    expect(free.dataset.at).toBe('20.5,20.25');
    await click(by(TID.roomFloorHere));
    const put4 = await waitForPut(mock, s => (s.fixes.rooms ?? []).length === 2);
    expect(put4.settings.fixes.rooms![1]).toEqual({ floor: 'ground', at: [20.5, 20.25], name: null, slab: 'floor', ceiling: 'auto' });
    await saved();
    await click(by(TID.roomOutdoors));
    await waitForPut(mock, s => s.fixes.rooms?.[1]?.slab === 'none');
    await click(by(TID.roomPanelClose));
    await waitFor(() => !by(TID.roomPanel));
  });

  it('the stair panel: "This is the bottom" then a pick, "Keep as lines", "Climb it as drawn", "Decide automatically"', async () => {
    const { mock } = await openCheck();
    await choose(by(TID.checkTool), 'rooms');
    await act(async () => { lastCanvas().onStair!('ground-ST2'); });
    const panel = await waitFor(() => by(TID.stairPanel));
    expect([panel.dataset.id, panel.dataset.state]).toEqual(['ground-ST2', 'lines']);
    await click(by(TID.stairBottom));
    await waitFor(() => lastCanvas().tool === 'pick-point' && by(TID.stairBottom)?.dataset.picking === '');
    await act(async () => { lastCanvas().onPick!([2.6, 6.4]); });
    const put = await waitForPut(mock, s => (s.fixes.stairs ?? []).length === 1);
    expect(put.settings.fixes.stairs![0]).toMatchObject({ floor: 'ground', bottom: [2.6, 6.4], use: 'auto' });
    await waitFor(() => lastCanvas().tool === 'rooms' && by(TID.stairBottom)?.dataset.picking === undefined);
    await waitFor(() => marksOf(lastCanvas().overlay)?.bottoms.length === 1);
    await saved();
    await click(by(TID.stairLines));
    await waitForPut(mock, s => s.fixes.stairs?.[0]?.use === 'lines' && !!s.fixes.stairs[0].bottom);
    await saved();
    await click(by(TID.stairClimb));
    await waitForPut(mock, s => s.fixes.stairs?.[0]?.use === 'climb');
    await saved();
    await click(by(TID.stairAuto));
    await waitForPut(mock, s => (s.fixes.stairs ?? []).length === 0);
  });

  it('a click on one of the app\'s closings takes it out (one room); a second click puts it back', async () => {
    const { mock } = await openCheck();
    await choose(by(TID.checkTool), 'rooms');
    await act(async () => { lastCanvas().onClosing!(0); });
    await waitForPut(mock, s => s.fixes.closings?.[0]?.use === 'none');
    await saved();
    await act(async () => { lastCanvas().onClosing!(0); });
    await waitForPut(mock, s => (s.fixes.closings ?? []).length === 0);
  });

  it('the set-aside tick "The floor runs past it" and the Heights panel\'s ceiling height', async () => {
    const mock = createMockApi();
    const { build } = draftOf(mock, PID, REF_FILES, { built: true });
    const ref = { floor: 'ground', source: build.sources[0]!, key: '100', sig: 'a'.repeat(12), rsig: '', elementId: null, layer: 'A-WALL', note: '' };
    const res = mock.handle({
      method: 'PUT', path: `/api/projects/${PID}/builds/${build.id}/settings`, headers: { 'if-match': `"${build.revision}"` },
      body: JSON.stringify({ settings: { ...build.settings, fixes: { ...build.settings.fixes, setAside: [ref] } }, layersReviewed: true }),
    });
    expect(res?.status).toBe(200);
    const before = settingsPuts(mock).length;
    await openStep(mock, build.id, 'check');
    const tick = await waitFor(() => q(`[data-testid=set-aside-row][data-key="100"] ${sel(TID.setAsideFloorPast)}`));
    expect(settingsPuts(mock).length).toBe(before);
    await click(tick);
    const put = await waitForPut(mock, s => s.fixes.setAside[0]?.floorPast === true);
    expect(put.settings.fixes.setAside).toEqual([{ ...ref, floorPast: true }]);
    await saved();
    const ceiling = await waitFor(() => q(`[data-testid=heights-panel] ${sel(TID.heightsCeiling)}[data-key=ground]`)) as HTMLInputElement;
    expect(ceiling.placeholder).toBe('2.7');
    await enter(ceiling, '2.55');
    await waitForPut(mock, s => s.floors[0]?.ceilingHeight === 2.55);
    expect(lastPut(mock).floors[1]?.ceilingHeight ?? null).toBeNull();
  });
});

describe('the flag cards and the list of changes (R-6.1, R-6.4)', () => {
  it('each new flag kind has its text; the builder\'s titles and sentences show as text', async () => {
    const flags = (readJson(ROOMS_FILES.flags) as { flags: Flag[] }).flags;
    expect(new Set(flags.map(f => f.kind))).toEqual(new Set(['slab-gap', 'room-open', 'room-names', 'doorway', 'stair', 'stairs-none', 'stair-clash', 'hole-skipped']));
    const v = await render(<FlagList flags={flags} />);
    for (const f of flags) {
      const card = q(`[data-testid=flag][data-id="${f.id}"]`)!;
      expect(text(card)).toContain(FLAG_KIND_TEXT[f.kind]);
      expect(text(card.querySelector('[data-testid=flag-title]'))).toBe(f.title);
    }
    await v.unmount();
  });

  it('a floor whose plate a Rebuild made 2 m2 smaller or more is the first row, whatever floor is on screen; the new keys have names', async () => {
    const body = {
      counts: { L1: { parts: [10, 12], 'rooms closed': [3, 4] }, L2: { 'stairs you can climb': [0, 1], 'plate area (m2)': [120.4, 98.2] } },
      partsAdded: [], partsRemoved: [], openingsAdded: [], openingsRemoved: [], openingsChanged: [], furnitureByKind: {}, roomsAdded: [], roomsRemoved: [],
    } as BuildDiff['against'][number]['diff'];
    const diff: BuildDiff = { format: 'build-diff/1', against: [{ kind: 'previous-run', ref: '0002-build', diff: body }] };
    const v = await render(<DiffPanel diff={diff} against={0} onAgainst={() => undefined} draw={false} onDraw={() => undefined} floor="L1" />);
    const rows = qa('tbody tr');
    expect(rows[0]!.dataset.testid).toBe(TID.lostFloor);
    expect(rows[0]!.dataset.key).toBe('L2');
    expect(text(rows[0])).toContain('Floor plate (m²)');
    expect(rows.slice(1).map(r => text(r.querySelectorAll('td')[1]))).toEqual(['parts', 'Rooms closed']);
    await v.unmount();
    // a plate 1.5 m2 smaller is no lost floor
    const small = { ...body, counts: { L2: { 'plate area (m2)': [120.4, 118.9] as [number, number] } } };
    const v2 = await render(<DiffPanel diff={{ ...diff, against: [{ ...diff.against[0]!, diff: small }] }} against={0} onAgainst={() => undefined} draw={false} onDraw={() => undefined} />);
    expect(q(sel(TID.lostFloor))).toBeNull();
    await v2.unmount();
  });
});
