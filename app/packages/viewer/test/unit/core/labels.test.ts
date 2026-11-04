// @vitest-environment happy-dom
// Builder A: layoutLabels (the declutter, pure) and createLabels (DESIGN.md 13 "Labels", 11.5) in happy-dom: rows 0, +1,
// -1, +2, -2 of (h + 2) px, 2 px apart across and 1 px down, bigger rooms first, hidden when no row is free; shown on the
// top visible floor only, in Orbit, with the Room names tick, when there is no replay or it is done; drawing text as text.
import { afterAll, beforeAll, describe, expect, it } from 'vitest';
import type { ReplayApi } from '../../../src/contracts';
import { createLabels, layoutLabels } from '../../../src/core/labels';
import { kitContext } from './kit';

describe('layoutLabels (pure)', () => {
  const box = (x: number, y: number, w = 60, h = 16) => ({ x, y, w, h });
  it('a label alone keeps its spot', () => {
    expect(layoutLabels([box(100, 100)])).toEqual([0]);
    expect(layoutLabels([])).toEqual([]);
  });
  it('labels on one spot take the rows 0, +1, -1, +2, -2 of h + 2 px, the sixth is hidden', () => {
    expect(layoutLabels(Array.from({ length: 6 }, () => box(100, 100)))).toEqual([0, 18, -18, 36, -36, null]);
  });
  it('needs 2 px across and 1 px down between labels', () => {
    expect(layoutLabels([box(100, 100), box(162, 100)])).toEqual([0, 0]);     // 62 apart: 2 px gap
    expect(layoutLabels([box(100, 100), box(161, 100)])).toEqual([0, 18]);    // 1 px gap: moved a row down
    expect(layoutLabels([box(100, 100), box(100, 117)])).toEqual([0, 0]);     // 17 below: 1 px gap
    expect(layoutLabels([box(100, 100), box(100, 116.5)])).toEqual([0, 18]);
  });
  it('earlier (bigger) labels keep their spot; a row is taken only where it is free', () => {
    expect(layoutLabels([box(100, 100), box(100, 118), box(100, 100)])).toEqual([0, 0, -18]);
  });
});

describe('createLabels (happy-dom)', () => {
  const HOSTILE = '<img src=x onerror="window.__pwned = 1">';
  const width = Object.getOwnPropertyDescriptor(HTMLElement.prototype, 'offsetWidth');
  const height = Object.getOwnPropertyDescriptor(HTMLElement.prototype, 'offsetHeight');
  beforeAll(() => {
    Object.defineProperty(HTMLElement.prototype, 'offsetWidth', { configurable: true, get(this: HTMLElement) { return this.dataset.wt === 'room' ? 60 : 0; } });
    Object.defineProperty(HTMLElement.prototype, 'offsetHeight', { configurable: true, get(this: HTMLElement) { return this.dataset.wt === 'room' ? 16 : 0; } });
  });
  afterAll(() => {
    if (width) Object.defineProperty(HTMLElement.prototype, 'offsetWidth', width);
    if (height) Object.defineProperty(HTMLElement.prototype, 'offsetHeight', height);
  });
  const setup = () => {
    const root = document.createElement('div');
    document.body.append(root);
    const ctx = kitContext('bank-v2', { root });
    const labels = createLabels(ctx);
    const shown = () => labels.labels.filter(l => l.el.style.display === 'block');
    return { ctx, labels, root, shown };
  };

  it('one [data-wt=room] per room in the root, its text from the drawing as text; its CSS chunk added once', () => {
    const { ctx, labels, root } = setup();
    expect(labels.labels).toHaveLength(ctx.model.rooms.length);
    expect(root.querySelectorAll('[data-wt=room]')).toHaveLength(ctx.model.rooms.length);
    expect(labels.labels.map(l => l.el.textContent)).toEqual(ctx.model.rooms.map(r => r.label));
    expect((ctx as unknown as { kitStyles: string[] }).kitStyles.filter(s => s.includes('[data-wt=room]'))).toHaveLength(1);
    expect(labels.labels.every(l => l.p.y === 0)).toBe(true);
    ctx.disposer.dispose();
    expect(root.querySelectorAll('[data-wt=room]')).toHaveLength(0);
    root.remove();
  });

  it('drawing text stays text (an <img onerror> label makes no element)', () => {
    const root = document.createElement('div');
    document.body.append(root);
    const ctx = kitContext('bank-v2', { root });
    ctx.model.rooms[0]!.label = HOSTILE;
    const labels = createLabels(ctx);
    expect(labels.labels[0]!.el.textContent).toBe(HOSTILE);
    expect(root.querySelector('img')).toBeNull();
    ctx.disposer.dispose();
    root.remove();
  });

  it('Orbit, ticked, no replay: the top visible floor\'s labels show, none overlapping, inside the root', () => {
    const { ctx, labels, shown } = setup();
    labels.place();
    const on = shown();
    expect(on.length).toBeGreaterThanOrEqual(5);
    expect(on.every(l => l.floor === 'L2')).toBe(true);
    const boxes = on.map(l => { const x = parseFloat(l.el.style.left), y = parseFloat(l.el.style.top); return [x - 30, y - 8, x + 30, y + 8]; });
    for (let i = 0; i < boxes.length; i++) for (let j = i + 1; j < boxes.length; j++) {
      const [a, b] = [boxes[i]!, boxes[j]!];
      expect(a[0]! < b[2]! - 0.5 && b[0]! < a[2]! - 0.5 && a[1]! < b[3]! - 0.5 && b[1]! < a[3]! - 0.5).toBe(false);
    }
    ctx.visibility.setFloorMode('L1');
    labels.place();
    expect(shown().length).toBeGreaterThan(0);
    expect(shown().every(l => l.floor === 'L1')).toBe(true);
    ctx.disposer.dispose();
  });

  it('hidden with the tick off, in Walk / Ghost, while the replay is not done; the label lifts with the Walk level', () => {
    const { ctx, labels, shown } = setup();
    labels.place();
    const before = shown().length;
    expect(before).toBeGreaterThan(0);
    ctx.visibility.setToggle('rooms', false); labels.place(); expect(shown()).toHaveLength(0);
    ctx.visibility.setToggle('rooms', true);
    ctx.modes.mode = 'walk'; labels.place(); expect(shown()).toHaveLength(0);
    ctx.modes.mode = 'orbit';
    const replay = { phase: 'settings' } as ReplayApi;
    (ctx as { replay: ReplayApi | null }).replay = replay;
    labels.place(); expect(shown()).toHaveLength(0);
    (replay as { phase: string }).phase = 'done';
    labels.place(); expect(shown()).toHaveLength(before);
    (ctx as { replay: ReplayApi | null }).replay = null;
    const top = labels.labels.find(l => l.el.style.display === 'block')!;
    const y0 = parseFloat(top.el.style.top);
    ctx.heights.apply({ L1: { level: 0, height: 3.7 }, L2: { level: 5.5, height: 3.7 } });
    labels.place();
    if (top.el.style.display === 'block') expect(parseFloat(top.el.style.top)).toBeLessThan(y0);   // higher up on screen
    ctx.disposer.dispose();
  });
});
