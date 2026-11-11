// Scaffold's tests of core/events.ts.
import { describe, expect, it, vi } from 'vitest';
import type { InternalEvents } from '../../../src/contracts';
import { createEventBus } from '../../../src/core/events';

describe('createEventBus', () => {
  it('delivers typed payloads to the listeners of that type only', () => {
    const bus = createEventBus<InternalEvents>();
    const onMode = vi.fn();
    const onResize = vi.fn();
    bus.on('mode', onMode);
    bus.on('resize', onResize);
    bus.emit('mode', { mode: 'walk', floor: 'L1' });
    expect(onMode).toHaveBeenCalledWith({ mode: 'walk', floor: 'L1' });
    expect(onResize).not.toHaveBeenCalled();
  });

  it('off() removes one listener; clear() removes all', () => {
    const bus = createEventBus<InternalEvents>();
    const a = vi.fn();
    const b = vi.fn();
    const offA = bus.on('resize', a);
    bus.on('resize', b);
    offA();
    offA();
    bus.emit('resize', { width: 10, height: 20 });
    expect(a).not.toHaveBeenCalled();
    expect(b).toHaveBeenCalledTimes(1);
    bus.clear();
    bus.emit('resize', { width: 10, height: 20 });
    expect(b).toHaveBeenCalledTimes(1);
  });

  it('calls the listeners registered when emit started, in order', () => {
    const bus = createEventBus<InternalEvents>();
    const calls: string[] = [];
    const late = () => calls.push('late');
    bus.on('replayPhase', () => { calls.push('first'); bus.on('replayPhase', late); });
    bus.on('replayPhase', () => calls.push('second'));
    bus.emit('replayPhase', { phase: 'play' });
    expect(calls).toEqual(['first', 'second']);
    bus.emit('replayPhase', { phase: 'done' });
    expect(calls).toEqual(['first', 'second', 'first', 'second', 'late']);
  });

  it('keeps calling the other listeners when one throws, then rethrows', () => {
    const bus = createEventBus<InternalEvents>();
    const after = vi.fn();
    bus.on('toggles', () => { throw new Error('boom'); });
    bus.on('toggles', after);
    const payload = { toggles: { plates: true, glass: true, rooms: true, single: true, picture: false, ceilings: true } };
    expect(() => bus.emit('toggles', payload)).toThrow('boom');
    expect(after).toHaveBeenCalledTimes(1);
    bus.on('toggles', () => { throw new Error('two'); });
    expect(() => bus.emit('toggles', payload)).toThrow(AggregateError);
  });

  it('emitting with no listeners does nothing', () => {
    const bus = createEventBus<InternalEvents>();
    expect(() => bus.emit('floorMode', { floorMode: 'all' })).not.toThrow();
  });
});
