// A stand-in for U7's plan canvas in the screen tests (vi.mock('@/plan') keeps decodePlan and replaces the canvas and the
// two helpers): the canvas renders a <div> naming what it was given and keeps its latest props, so a test can play the
// user's click on the plan (onSelect, onBox, onPick, onOpening) without U7's hit testing; nearLayers answers from a set
// of layer names a test chooses; proposeAreas from a list of boxes.
import type { JSX } from 'react';
import type { DecodedPlan, PlanCanvasProps } from '@/plan';
import type { Bbox } from '@/upload/contracts';

export const fakePlan: {
  /** The props of the canvases on screen, newest last, by data-testid of the box around them (or ''). */
  props: PlanCanvasProps[];
  /** Layer names nearLayers reports as close to the walls (count 1). */
  near: Set<string>;
  /** What proposeAreas answers. */
  areas: Bbox[];
  reset(): void;
} = {
  props: [],
  near: new Set(),
  areas: [],
  reset() { this.props.length = 0; this.near = new Set(); this.areas = []; },
};

export function FakePlanCanvas(props: PlanCanvasProps): JSX.Element {
  fakePlan.props.push(props);
  const highlight = props.highlightLayer ?? null;
  return (
    <div
      data-testid="fake-canvas"
      data-items={props.plan.count}
      data-tool={props.tool}
      data-pick={props.pick ?? 'item'}
      data-highlight={highlight === null ? '' : props.plan.layers[highlight]}
      data-area={props.area ? JSON.stringify(props.area) : ''}
      data-selected={[...props.selected].join('|')}
      data-set-aside={[...props.setAside].join('|')}
      data-flags={(props.flags ?? []).length}
      data-overlay={props.overlay?.key ?? ''}
      data-diff={props.diff ? '' : undefined}
      data-focus={props.focus ? props.focus.join(',') : ''}
    >
      {`fake canvas: ${props.plan.count} items`}
    </div>
  );
}

/** The latest canvas's props (throws when none is on screen). */
export function lastCanvas(): PlanCanvasProps {
  const p = fakePlan.props.at(-1);
  if (!p) throw new Error('no plan canvas rendered');
  return p;
}

export function fakeNearLayers(plan: DecodedPlan, wallLayers: ReadonlySet<number>, dist: number): Map<number, number> {
  void dist;
  const out = new Map<number, number>();
  plan.layers.forEach((n, i) => { if (!wallLayers.has(i)) out.set(i, fakePlan.near.has(n) ? 1 : 0); });
  return out;
}

export function fakeProposeAreas(plan: DecodedPlan, layers: ReadonlySet<number>): Bbox[] {
  void plan; void layers;
  return fakePlan.areas.slice();
}
