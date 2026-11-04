// Builder A: the public events viewer.ts makes from the bus (DESIGN.md 11.5): modechange only on a change of mode or floor;
// heightschange only for the sources typed and reset (never api = setHeights, never tick = the doorways tick).
import { describe, expect, it, vi } from 'vitest';
import type { FurnitureApi, InternalEvents, ViewerEvents } from '../../../src/contracts';
import { createEventBus } from '../../../src/core/events';
import { bridgeEvents, guardFurniture } from '../../../src/viewer';

const setup = () => {
  const bus = createEventBus<InternalEvents>(), events = createEventBus<ViewerEvents>();
  bridgeEvents(bus, events);
  const mode = vi.fn(), heights = vi.fn();
  events.on('modechange', mode);
  events.on('heightschange', heights);
  return { bus, mode, heights };
};

describe('bridgeEvents', () => {
  it('modechange: the first, then only when the mode or the floor changes (not on a lens change)', () => {
    const { bus, mode } = setup();
    bus.emit('mode', { mode: 'orbit', floor: 'L1' });
    bus.emit('mode', { mode: 'orbit', floor: 'L1' });          // a HUD update (lens)
    bus.emit('mode', { mode: 'walk', floor: 'L1' });
    bus.emit('mode', { mode: 'walk', floor: 'L1' });
    bus.emit('mode', { mode: 'walk', floor: 'L2' });
    bus.emit('mode', { mode: 'orbit', floor: 'L2' });
    expect(mode.mock.calls.map(c => c[0])).toEqual([
      { mode: 'orbit', floor: 'L1' }, { mode: 'walk', floor: 'L1' }, { mode: 'walk', floor: 'L2' }, { mode: 'orbit', floor: 'L2' },
    ]);
  });
  it('heightschange: typed and reset only, with a copy of the heights', () => {
    const { bus, heights } = setup();
    const map = { table: 600 };
    bus.emit('furniture', { heights: map, source: 'api' });
    bus.emit('furniture', { heights: map, source: 'tick' });
    bus.emit('furniture', { heights: map, source: 'typed' });
    bus.emit('furniture', { heights: {}, source: 'reset' });
    expect(heights.mock.calls.map(c => c[0])).toEqual([{ heights: { table: 600 }, source: 'typed' }, { heights: {}, source: 'reset' }]);
    expect(heights.mock.calls[0]![0].heights).not.toBe(map);
  });
});

describe('Viewer.furniture after dispose (fix step, review finding "code" 12)', () => {
  const fake = () => {
    const calls: string[] = [];
    const api: FurnitureApi = {
      pieces: () => [], kinds: () => [], setHeight: () => { calls.push('setHeight'); return true; },
      setVisible: () => { calls.push('setVisible'); return true; }, setBlocks: () => { calls.push('setBlocks'); return true; },
      setKeepDoorways: () => { calls.push('setKeepDoorways'); return true; }, keepDoorways: () => true,
      reset: () => { calls.push('reset'); }, csv: () => 'csv', saveCsv: () => { calls.push('saveCsv'); return 'csv'; },
      meshOf: () => ({}) as never, apply: () => { calls.push('apply'); }, heights: () => ({ table: 600 }),
      setHeights: () => { calls.push('setHeights'); },
    };
    return { api, calls };
  };
  it('passes everything through while the viewer lives, and writes nothing once it is disposed', () => {
    let disposed = false;
    const { api, calls } = fake();
    const F = guardFurniture(api, () => disposed)!;
    expect(F.setHeight('table', 640)).toBe(true);
    F.reset();
    expect(calls).toEqual(['setHeight', 'reset']);
    disposed = true;
    expect([F.setHeight('table', 640), F.setVisible('table', false), F.setBlocks('table', false), F.setKeepDoorways(false)]).toEqual([false, false, false, false]);
    F.reset(); F.apply(); F.setHeights({ table: 640 });
    expect(F.saveCsv()).toBe('csv');                            // the text, no download
    expect(F.meshOf('x')).toBeNull();
    expect(calls).toEqual(['setHeight', 'reset']);              // nothing more reached the module
    expect(F.heights()).toEqual({ table: 600 });               // the reads answer the last state
    expect(guardFurniture(null, () => false)).toBeNull();
  });
});
