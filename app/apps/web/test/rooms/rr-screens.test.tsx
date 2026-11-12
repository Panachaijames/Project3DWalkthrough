// RR (the rooms milestone's independent review and fix, area "web"; /wt-rr TRIAGE S1, S2 + S3, S10, S13): the Check and
// Save steps over the mock API (the reference building) with the plan canvas replaced by test/build/fake-plan.tsx.
// * S1: the plan column is sticky on a wide screen; Show (a flag, a fix row) brings the plan into view on a narrow one.
// * S2 + S3: a stair card that asks for a check has "Open this stair" (the tool Rooms and stairs, that stair's panel, the
//   plan on it); its kind line says "Stair" (the builder's title says the rest).
// * S10: the Save step and the changes list call the model's room names "room names", not "rooms".
// * S13: the room or stair open in a panel rides to the canvas on the overlay (plan/marks.ts) to be outlined.
import { act } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { DiffPanel } from '@/build/DiffPanel';
import { FLAG_IT_IS_FLOOR, FLAG_KIND_TEXT, FLAG_OPEN_STAIR, FlagList, type FlagRoomsActions } from '@/build/FlagList';
import { flagFix, isCutXHole, onPlate, spaceHolding, xHoleFloorFix } from '@/build/roomsFixes';
import { PLAN_COLUMN } from '@/build/CheckStep';
import { roomNamesText } from '@/build/SaveStep';
import { sel, TID } from '@/build/testids';
import { marksOf } from '@/plan/marks';
import { setUploadOptionsForTests } from '@/pages/UploadPage';
import type { BuildDiff, Flag } from '@/upload/contracts';
import { choose, click, render, text, waitFor } from '../helpers';
import { createMockApi, type MockApi } from '../mock-api/core';
import { readJson } from '../mock-api/fixtures';
import { referenceOverlay, ROOMS_FILES } from '../mock-api/rooms';
import { closeAll, draftOf, fastClocks, openApp, q, qa, waitForPut } from '../build/app';
import { fakePlan, lastCanvas } from '../build/fake-plan';

vi.mock('@walkthrough/viewer', async () => vi.importActual('../fake-viewer'));
vi.mock('@/plan', async importOriginal => {
  const real = await importOriginal<typeof import('@/plan')>();
  const fake = await import('../build/fake-plan');
  return { ...real, PlanCanvas: fake.FakePlanCanvas, nearLayers: fake.fakeNearLayers, proposeAreas: fake.fakeProposeAreas };
});
vi.setConfig({ testTimeout: 60_000 });

/** scrollIntoView calls (happy-dom does not scroll): the element and its options. */
let scrolled: [HTMLElement, unknown][] = [];
let restoreClocks = () => undefined as void;
const hadScroll = Object.getOwnPropertyDescriptor(HTMLElement.prototype, 'scrollIntoView');
beforeEach(() => {
  restoreClocks = fastClocks(); fakePlan.reset(); setUploadOptionsForTests({ sleep: async () => undefined, storage: () => null });
  scrolled = [];
  HTMLElement.prototype.scrollIntoView = function (this: HTMLElement, arg?: unknown) { scrolled.push([this, arg]); };
});
afterEach(async () => {
  restoreClocks(); setUploadOptionsForTests(null); await closeAll();
  if (hadScroll) Object.defineProperty(HTMLElement.prototype, 'scrollIntoView', hadScroll);
  else delete (HTMLElement.prototype as { scrollIntoView?: unknown }).scrollIntoView;
});

const REF_FILES = ['rooms-reference-ground.dxf', 'rooms-reference-upper.dxf'];
const PID = 'bank-sampeng';
const by = (id: string) => q(sel(id as never));
async function openStep(mock: MockApi, buildId: string, step: string) {
  const app = await openApp(`/projects/${PID}/builds/${buildId}?step=${step}`, { mock });
  await waitFor(() => q(`[data-testid=build-page][data-step=${step}]`));
  return app;
}
async function openCheck() {
  const mock = createMockApi();
  const { build } = draftOf(mock, PID, REF_FILES, { built: true });
  await openStep(mock, build.id, 'check');
  await waitFor(() => by(TID.checkRooms) && q('[data-testid=flag-list]'));
  return { mock, build };
}
const canvasBox = () => q('[data-testid=check-canvas]')!;

describe('S1: the plan stays on screen while the flag list scrolls', () => {
  it('the plan column is sticky under the app bar on a wide screen, and scrolls by itself when taller than the window', async () => {
    await openCheck();
    const col = q('[data-testid=check-plan-column]')!;
    expect(col.contains(canvasBox())).toBe(true);
    expect(col.className).toBe(PLAN_COLUMN);
    for (const c of ['xl:sticky', 'xl:top-14', 'xl:self-start', 'xl:overflow-y-auto', 'xl:max-h-[calc(100svh-4.5rem)]']) expect(PLAN_COLUMN.split(' ')).toContain(c);
    // the flag list is in the other column
    expect(col.contains(q('[data-testid=flag-list]'))).toBe(false);
  });

  it('Show on the last flag focuses the plan on it and brings the plan into view (nearest: no jump when it is in view)', async () => {
    await openCheck();
    const shows = qa('[data-testid=flag] [data-testid=flag-show]');
    expect(shows.length).toBeGreaterThan(3);
    const last = shows.at(-1)!;
    const card = last.closest<HTMLElement>('[data-testid=flag]')!;
    expect(scrolled).toEqual([]);
    await click(last);
    await waitFor(() => lastCanvas().focus);
    expect(scrolled).toEqual([[canvasBox(), { block: 'nearest' }]]);
    expect(card.className).toContain('ring-2');
  });

  it('Show on a row of "Fixes on this floor" does the same', async () => {
    await openCheck();
    const gap = await waitFor(() => q('[data-testid=flag][data-kind=slab-gap]'));
    await click(gap.querySelector(sel(TID.flagOutdoors)));
    const row = await waitFor(() => q(`${sel(TID.fixRow)}[data-kind=room]`));
    scrolled = [];
    await click(row.querySelector('button[aria-label^="Show"]'));
    await waitFor(() => lastCanvas().focus);
    expect(scrolled.map(([el]) => el)).toEqual([canvasBox()]);
  });
});

describe('S2 + S3: the stair card opens its stair', () => {
  it('"Open this stair" on a stair card to check: the tool Rooms and stairs, the stair\'s panel, outlined on the plan', async () => {
    await openCheck();
    const card = await waitFor(() => q('[data-testid=flag][data-kind=stair]'));
    expect(card.dataset.severity).toBe('check');
    expect(text(card.querySelector('.text-muted-foreground'))).toBe('Stair');                 // the kind line (S3)
    expect(text(card.querySelector('[data-testid=flag-title]'))).toBe('Stair kept as lines');
    expect(by(TID.stairPanel)).toBeNull();
    await click(card.querySelector(`[data-testid=${FLAG_OPEN_STAIR}]`));
    const panel = await waitFor(() => by(TID.stairPanel));
    expect([panel.dataset.id, panel.dataset.state]).toEqual(['ground-ST2', 'lines']);
    expect((by(TID.checkTool) as HTMLSelectElement).value).toBe('rooms');
    await waitFor(() => lastCanvas().tool === 'rooms');
    lastCanvas().focus!.forEach((v, i) => expect(v).toBeCloseTo([0.1, 5, 6.1, 11][i]!, 9));  // the flag's point +- 3 m
    expect(marksOf(lastCanvas().overlay)?.pickedStair).toBe('ground-ST2');
    expect(scrolled.map(([el]) => el)).toEqual([canvasBox()]);
    expect(card.className).toContain('ring-2');
    // the panel works as when the stair is clicked on the plan
    await click(by(TID.stairPanelClose));
    await waitFor(() => !by(TID.stairPanel));
    expect(marksOf(lastCanvas().overlay)?.pickedStair ?? null).toBeNull();
  });

  it('the button only on a stair card that asks for a check and names its stair', async () => {
    const flags = (readJson(ROOMS_FILES.flags) as { flags: Flag[] }).flags;
    const stair = flags.find(f => f.kind === 'stair')!;
    const cards: Flag[] = [
      { ...stair, id: 'stair:a', severity: 'check' },
      { ...stair, id: 'stair:b', severity: 'info' },
      { ...stair, id: 'stair:c', severity: 'check', ref: {} },
    ];
    const opened: string[] = [];
    const v = await render(<FlagList flags={cards} onOpenStair={f => opened.push(f.id)} />);
    expect(qa(`[data-testid=${FLAG_OPEN_STAIR}]`).map(b => b.closest<HTMLElement>('[data-testid=flag]')!.dataset.id)).toEqual(['stair:a']);
    await click(q(`[data-testid=${FLAG_OPEN_STAIR}]`));
    expect(opened).toEqual(['stair:a']);
    expect(FLAG_KIND_TEXT.stair).toBe('Stair');
    await v.unmount();
    // no handler (another screen): no button
    const v2 = await render(<FlagList flags={cards} />);
    expect(q(`[data-testid=${FLAG_OPEN_STAIR}]`)).toBeNull();
    await v2.unmount();
  });
});

describe('S13: the room picked on the plan is marked', () => {
  it('a room clicked with Rooms and stairs rides to the canvas as pickedRoom; closing the panel takes it away', async () => {
    await openCheck();
    expect(marksOf(lastCanvas().overlay)).toBeNull();
    await choose(by(TID.checkTool), 'rooms');
    await waitFor(() => lastCanvas().tool === 'rooms');
    await act(async () => { lastCanvas().onSpace!('ground-R002'); });
    await waitFor(() => by(TID.roomPanel));
    await waitFor(() => marksOf(lastCanvas().overlay)?.pickedRoom === 'ground-R002');
    expect(marksOf(lastCanvas().overlay)?.pickedStair ?? null).toBeNull();
    // a place with no room: nothing to outline
    await act(async () => { lastCanvas().onPoint!([20.5, 20.25]); });
    await waitFor(() => by(TID.roomPanel)?.dataset.id === '');
    await waitFor(() => !marksOf(lastCanvas().overlay)?.pickedRoom);
    await act(async () => { lastCanvas().onSpace!('ground-R001'); });
    await waitFor(() => marksOf(lastCanvas().overlay)?.pickedRoom === 'ground-R001');
    await click(by(TID.roomPanelClose));
    await waitFor(() => !by(TID.roomPanel) && marksOf(lastCanvas().overlay) === null);
  });
});

describe('S10: "room names" for the model\'s named rooms', () => {
  it('the Save step says "N room names" above the table of rooms closed', async () => {
    const mock = createMockApi();
    const { build } = draftOf(mock, PID, REF_FILES, { built: true });
    await openStep(mock, build.id, 'save');
    const line = await waitFor(() => q('[data-testid=save-counts]'));
    expect(text(line)).toMatch(/furniture pieces, \d[\d,]* room names?$/);
    expect(text(line)).not.toMatch(/\d rooms\b/);
    expect(roomNamesText(1)).toBe('1 room name');
    expect(roomNamesText(9)).toBe('9 room names');
    expect(roomNamesText(1234)).toBe('1,234 room names');
  });

  it('the changes list names the diff\'s "rooms" row and the added / removed names "room names"', async () => {
    const body = {
      counts: { L1: { rooms: [8, 9], 'rooms closed': [16, 17] } },
      partsAdded: [], partsRemoved: [], openingsAdded: [], openingsRemoved: [], openingsChanged: [], furnitureByKind: {},
      roomsAdded: ['BAR'], roomsRemoved: ['GYM'],
    } as BuildDiff['against'][number]['diff'];
    const diff: BuildDiff = { format: 'build-diff/1', against: [{ kind: 'previous-run', ref: '0002-build', diff: body }] };
    const v = await render(<DiffPanel diff={diff} against={0} onAgainst={() => undefined} draw={false} onDraw={() => undefined} floor="L1" />);
    expect(qa('tbody tr').map(r => text(r.querySelectorAll('td')[1]))).toEqual(['Room names', 'Rooms closed']);
    expect(text(q('[data-testid=diff-rooms]'))).toBe('Room names added: BAR. Room names removed: GYM.');
    await v.unmount();
  });
});

// ------------------------------------------------------------------------- the web parts of the builder's RR fixes
describe('CODE-1 + BRK-2: "It is floor" on the flag of an X mark cut as a shaft or a void', () => {
  /** The builder's flag (out/overlay.py, RR): kind hole-skipped, severity info, a bbox, ref {}. */
  const cutX = (id: string, over: Partial<Flag> = {}): Flag => ({
    id, kind: 'hole-skipped', floor: 'ground', severity: 'info', title: 'An X mark was cut as a shaft',
    detail: 'An X marks 4.0 m2 as a shaft: it was cut out of the floor. If it is floor, say so.', at: [4.2, 6.1], bbox: [3.2, 5.1, 5.2, 7.1], ref: {}, ...over,
  });

  it('the button only on that flag (not on the lowest floor\'s uncut void, nor on the large uncut one); its fix is "floor here" at the flag\'s point', async () => {
    const flags = [cutX('a'), cutX('b', { title: 'A void mark was not cut', bbox: null }), cutX('c', { severity: 'check', title: 'A large void mark was not cut' })];
    expect(flags.map(isCutXHole)).toEqual([true, false, false]);
    expect(xHoleFloorFix(flags[0]!)).toEqual({ floor: 'ground', at: [4.2, 6.1], name: null, slab: 'floor', ceiling: 'auto' });
    expect(xHoleFloorFix(flags[1]!)).toBeNull();
    const asked: string[] = [];
    const rooms: FlagRoomsActions = {
      fixOf: () => null, onCloseHere: () => undefined, onOutdoors: () => undefined, onNotDoorway: () => undefined, earlier: false, onUseNew: () => undefined,
      onItIsFloor: f => asked.push(f.id),
    };
    const v = await render(<FlagList flags={flags} rooms={rooms} />);
    expect(qa(`[data-testid=${FLAG_IT_IS_FLOOR}]`).map(b => b.closest<HTMLElement>('[data-testid=flag]')!.dataset.id)).toEqual(['a']);
    await click(q(`[data-testid=${FLAG_IT_IS_FLOOR}]`));
    expect(asked).toEqual(['a']);
    await v.unmount();
  });

  it('on the Check step: the button writes the room fix, the card then waits for the Rebuild and the button is off', async () => {
    const mock = createMockApi();
    const { build } = draftOf(mock, PID, REF_FILES, { built: true });
    // the upper floor's X void of the reference building (3.4 - 6.0 x 0.8 - 2.8): a hole in the plate there. The frozen
    // overlay has its flag once the builder flags every cut X hole (RR); else the mock adds one (not answered by a rebuild)
    const own = referenceOverlay().flags.find(f => isCutXHole(f) && f.floor === 'upper');
    const flag = own ?? cutX('hole-skipped:upper:rrcutx00001', { floor: 'upper', title: 'An X mark was cut as a void', at: [4.7, 1.8], bbox: [3.4, 0.8, 6.0, 2.8] });
    if (!own) mock.uploads.config.extraFlags = [flag];
    await openStep(mock, build.id, 'check');
    await waitFor(() => by(TID.checkRooms));
    await click(q('[data-testid=check-floor][data-key=upper]'));
    const card = await waitFor(() => q(`[data-testid=flag][data-id="${flag.id}"]`));
    const button = card.querySelector<HTMLButtonElement>(`[data-testid=${FLAG_IT_IS_FLOOR}]`)!;
    expect(button.disabled).toBe(false);
    await click(button);
    const put = await waitForPut(mock, s => (s.fixes.rooms ?? []).length === 1);
    expect(put.settings.fixes.rooms).toEqual([{ floor: 'upper', at: [flag.at![0], flag.at![1]], name: null, slab: 'floor', ceiling: 'auto' }]);
    await waitFor(() => card.querySelector(sel(TID.fixWaiting)) && button.disabled);
    expect(button.className).toContain('bg-primary');                                   // the answer given
    // flagFix finds the fix by the flag's box; the frozen overlay still has the hole: waiting while stale
    const s = put.settings, up = referenceOverlay().floors[1]!;
    expect(flagFix(flag, s, up, true)).toEqual({ what: 'floor', waiting: true });
    expect(flagFix(flag, s, up, false)).toEqual({ what: 'floor', waiting: false });
    expect(flagFix({ ...flag, at: [40, 40], bbox: [39, 39, 41, 41] }, s, up, true)).toBeNull();
    if (!own) return;
    // the mock's rebuild keeps the X void as floor: the flag goes, the fix is applied (no longer waiting)
    await waitFor(() => q('[data-testid=settings-status]')?.dataset.status === 'saved');
    await click(q('[data-testid=rebuild]'));
    await waitFor(() => !q(`[data-testid=flag][data-id="${flag.id}"]`) && !q('[data-testid=check-stale]'));
    const row = await waitFor(() => q(`${sel(TID.fixRow)}[data-kind=room]`));
    expect(row.dataset.waiting).toBeUndefined();
  });
});

describe('FID-3 + FID-5b: a place on the floor plate in no room offers "No floor here" and "No ceiling"', () => {
  /** A point of the ground floor's plate in no room and no unfloored area (scanned on the frozen overlay). */
  function plateOnly(): [number, number] {
    const g = referenceOverlay().floors[0]!;
    const xs = g.slabs.flatMap(s => s.o.map(p => p[0])), ys = g.slabs.flatMap(s => s.o.map(p => p[1]));
    for (let x = Math.min(...xs) + 0.125; x < Math.max(...xs); x += 0.25) {
      for (let y = Math.min(...ys) + 0.125; y < Math.max(...ys); y += 0.25) {
        const p: [number, number] = [Math.round(x * 1000) / 1000, Math.round(y * 1000) / 1000];
        if (onPlate(g, p) && !spaceHolding(g, p) && !(g.stairs ?? []).some(st => insideRing(st.outline, p))) return p;
      }
    }
    throw new Error('no plate in no room on the reference ground floor');
  }
  const insideRing = (o: [number, number][], p: [number, number]) => {
    let c = false;
    for (let i = 0, j = o.length - 1; i < o.length; j = i++) {
      const [xi, yi] = o[i]!, [xj, yj] = o[j]!;
      if ((yi > p[1]) !== (yj > p[1]) && p[0] < xj + ((p[1] - yj) * (xi - xj)) / (yi - yj)) c = !c;
    }
    return c;
  };

  it('on plate: the two ticks write slab none / ceiling none at the point; off the plate: "Floor here" and "It is outdoors" as before', async () => {
    const mock = createMockApi();
    const { build } = draftOf(mock, PID, REF_FILES, { built: true });
    await openStep(mock, build.id, 'check');
    await waitFor(() => by(TID.checkRooms));
    await choose(by(TID.checkTool), 'rooms');
    await waitFor(() => lastCanvas().tool === 'rooms');
    const p = plateOnly();
    await act(async () => { lastCanvas().onPoint!(p); });
    const panel = await waitFor(() => { const x = by(TID.roomPanel); return x?.dataset.id === '' ? x : null; });
    expect(panel.dataset.plate).toBe('');
    expect(text(panel)).toContain('floor plate in no room');
    expect(by(TID.roomFloorHere)).toBeNull();
    expect(by(TID.roomOutdoors)).toBeNull();
    await click(by(TID.roomNoCeiling));
    const put = await waitForPut(mock, s => (s.fixes.rooms ?? []).length === 1);
    expect(put.settings.fixes.rooms).toEqual([{ floor: 'ground', at: p, name: null, slab: 'auto', ceiling: 'none' }]);
    await waitFor(() => q('[data-testid=settings-status]')?.dataset.status === 'saved');
    await click(by(TID.roomNoFloor));
    await waitForPut(mock, s => s.fixes.rooms?.[0]?.slab === 'none' && s.fixes.rooms[0].ceiling === 'none');
    // off the plate (the existing test's point): the two buttons, no ticks
    await act(async () => { lastCanvas().onPoint!([20.5, 20.25]); });
    await waitFor(() => by(TID.roomPanel)?.dataset.at === '20.5,20.25');
    expect(by(TID.roomPanel)!.dataset.plate).toBeUndefined();
    expect(by(TID.roomFloorHere)).not.toBeNull();
    expect(by(TID.roomNoCeiling)).toBeNull();
    expect(onPlate(referenceOverlay().floors[0]!, [20.5, 20.25])).toBe(false);
  });
});
