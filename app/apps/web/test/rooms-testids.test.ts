// The rooms scaffold's test aids (docs/rooms/DESIGN.md R-12.6; WORK_BREAKDOWN R0 item 6; frozen with them): the test ids
// are unique and well formed, and the plan canvas's signatures are the ones the design names.
import { describe, expect, expectTypeOf, it } from 'vitest';
import type { Vec2 } from '@walkthrough/viewer';
import { CHECK_TOOLS, TID, sel } from '@/build/testids';
import { EMPTY_PLAN_HOOK, PLAN_TEST_HOOK, setPlanTestHook, type PlanCanvasProps, type PlanShow, type PlanTestHook, type PlanTool } from '@/plan';

describe('build/testids.ts', () => {
  it('every id is unique, lower-case with hyphens, and none is one of the upload milestone ids it would shadow', () => {
    const ids = Object.values(TID);
    expect(new Set(ids).size).toBe(ids.length);
    for (const id of ids) expect(id).toMatch(/^[a-z]+(-[a-z]+)*$/);
    // `check-tool` is the existing select: the one id shared on purpose
    for (const old of ['flag', 'flag-list', 'set-aside-row', 'heights-panel', 'floor-card', 'check-step']) expect(ids).not.toContain(old);
    expect(TID.checkTool).toBe('check-tool');
    expect(sel(TID.rulesLine)).toBe('[data-testid="rules-line"]');
    expect(CHECK_TOOLS).toEqual(['pan', 'select', 'draw-line', 'rooms']);
  });
});

describe('plan/index.ts: the signatures of R-12.6', () => {
  it('has the two new tools, the callbacks, show and the hook', () => {
    expectTypeOf<PlanTool>().toEqualTypeOf<'pan' | 'select' | 'pick-point' | 'draw-box' | 'draw-line' | 'rooms'>();
    expectTypeOf<PlanCanvasProps['tool']>().toEqualTypeOf<PlanTool>();
    expectTypeOf<PlanCanvasProps['show']>().toEqualTypeOf<PlanShow | undefined>();
    expectTypeOf<PlanShow>().toEqualTypeOf<{ rooms: boolean; plate: boolean; furniture: boolean }>();
    expectTypeOf<NonNullable<PlanCanvasProps['onLine']>>().toEqualTypeOf<(a: Vec2, b: Vec2) => void>();
    expectTypeOf<NonNullable<PlanCanvasProps['onSpace']>>().toEqualTypeOf<(id: string) => void>();
    expectTypeOf<NonNullable<PlanCanvasProps['onStair']>>().toEqualTypeOf<(id: string) => void>();
    expectTypeOf<NonNullable<PlanCanvasProps['onClosing']>>().toEqualTypeOf<(index: number) => void>();
    expectTypeOf<NonNullable<PlanCanvasProps['onPoint']>>().toEqualTypeOf<(pt: Vec2) => void>();
    expectTypeOf<Window['__plan']>().toEqualTypeOf<PlanTestHook | undefined>();
    expectTypeOf<ReturnType<PlanTestHook['toPage']>>().toEqualTypeOf<Vec2 | null>();
  });

  it('the hook is installed only with VITE_WTV_TEST_HOOK', () => {
    setPlanTestHook(EMPTY_PLAN_HOOK);
    expect(window.__plan).toBe(PLAN_TEST_HOOK ? EMPTY_PLAN_HOOK : undefined);
    setPlanTestHook(null);
    expect(window.__plan).toBeUndefined();
    expect([EMPTY_PLAN_HOOK.toPage([1, 2]), EMPTY_PLAN_HOOK.spaces(), EMPTY_PLAN_HOOK.stairs()]).toEqual([null, [], []]);
  });
});
