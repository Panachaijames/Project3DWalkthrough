// Scaffold's tests of core/disposer.ts (DESIGN.md 17.2: every listen / timeout / track undone; idempotent).
import { afterEach, describe, expect, it, vi } from 'vitest';
import { createDisposer } from '../../../src/core/disposer';

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
});

describe('createDisposer', () => {
  it('removes every listener it added, with the same capture flag', () => {
    const d = createDisposer();
    const target = new EventTarget();
    const plain = vi.fn();
    const captured = vi.fn();
    d.listen(target, 'ping', plain);
    d.listen(target, 'ping', captured, { capture: true });
    target.dispatchEvent(new Event('ping'));
    expect(plain).toHaveBeenCalledTimes(1);
    expect(captured).toHaveBeenCalledTimes(1);
    d.dispose();
    target.dispatchEvent(new Event('ping'));
    expect(plain).toHaveBeenCalledTimes(1);
    expect(captured).toHaveBeenCalledTimes(1);
  });

  it('clears pending timeouts and keeps fired ones out of the way', () => {
    vi.useFakeTimers();
    const d = createDisposer();
    const early = vi.fn();
    const late = vi.fn();
    d.timeout(early, 10);
    d.timeout(late, 1000);
    vi.advanceTimersByTime(20);
    expect(early).toHaveBeenCalledTimes(1);
    d.dispose();
    vi.advanceTimersByTime(2000);
    expect(late).not.toHaveBeenCalled();
  });

  it('clearTimeout cancels one timer', () => {
    vi.useFakeTimers();
    const d = createDisposer();
    const fn = vi.fn();
    const id = d.timeout(fn, 50);
    expect(id).toBeGreaterThan(0);
    d.clearTimeout(id);
    d.clearTimeout(id);
    vi.advanceTimersByTime(100);
    expect(fn).not.toHaveBeenCalled();
  });

  it('runs add() steps in reverse order, then disposes tracked things last, in reverse order', () => {
    const d = createDisposer();
    const order: string[] = [];
    d.track({ dispose: () => order.push('track 1') });
    d.add(() => order.push('add 1'));
    d.track({ dispose: () => order.push('track 2') });
    d.add(() => order.push('add 2'));
    d.dispose();
    expect(order).toEqual(['add 2', 'add 1', 'track 2', 'track 1']);
  });

  it('tracks a thing once however often it is tracked, and returns it', () => {
    const d = createDisposer();
    const thing = { dispose: vi.fn() };
    expect(d.track(thing)).toBe(thing);
    d.track(thing);
    d.dispose();
    expect(thing.dispose).toHaveBeenCalledTimes(1);
  });

  it('revokes object URLs on dispose', () => {
    const revoke = vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {});
    const d = createDisposer();
    expect(d.objectUrl('blob:one')).toBe('blob:one');
    expect(revoke).not.toHaveBeenCalled();
    d.dispose();
    expect(revoke).toHaveBeenCalledWith('blob:one');
  });

  it('is idempotent', () => {
    const d = createDisposer();
    const step = vi.fn();
    const thing = { dispose: vi.fn() };
    d.add(step);
    d.track(thing);
    expect(d.disposed).toBe(false);
    d.dispose();
    d.dispose();
    expect(d.disposed).toBe(true);
    expect(step).toHaveBeenCalledTimes(1);
    expect(thing.dispose).toHaveBeenCalledTimes(1);
  });

  it('undoes a registration made after dispose at once', () => {
    vi.useFakeTimers();
    const revoke = vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {});
    const d = createDisposer();
    d.dispose();
    const target = new EventTarget();
    const fn = vi.fn();
    d.listen(target, 'ping', fn);
    target.dispatchEvent(new Event('ping'));
    expect(fn).not.toHaveBeenCalled();
    const late = vi.fn();
    expect(d.timeout(late, 10)).toBe(0);
    vi.advanceTimersByTime(20);
    expect(late).not.toHaveBeenCalled();
    const step = vi.fn();
    d.add(step);
    expect(step).toHaveBeenCalledTimes(1);
    const thing = { dispose: vi.fn() };
    d.track(thing);
    expect(thing.dispose).toHaveBeenCalledTimes(1);
    d.objectUrl('blob:late');
    expect(revoke).toHaveBeenCalledWith('blob:late');
  });

  it('runs every step even when one throws, and reports the failure', () => {
    const error = vi.spyOn(console, 'error').mockImplementation(() => {});
    const d = createDisposer();
    const after = vi.fn();
    const thing = { dispose: vi.fn() };
    d.track(thing);
    d.add(after);
    d.add(() => { throw new Error('boom'); });
    d.dispose();
    expect(after).toHaveBeenCalledTimes(1);
    expect(thing.dispose).toHaveBeenCalledTimes(1);
    expect(error).toHaveBeenCalledTimes(1);
    expect(String(error.mock.calls[0]?.[0])).toContain('[viewer] dispose step failed');
  });
});
