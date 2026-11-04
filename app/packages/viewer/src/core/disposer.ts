// Scaffold (complete; everyone uses it, nobody else edits it). DESIGN.md 11.8: everything a viewer registers goes through
// the disposer, and dispose() undoes it.
//
// Order on dispose(): the undo steps (listeners removed, pending timeouts cleared, add() steps run, object URLs revoked)
// run in reverse registration order; then every tracked thing is disposed, also in reverse order ("at the end", so a
// step that still needs a geometry or a texture runs before it goes). Each step runs even when an earlier one threw; the
// failures are reported with console.error after the rest ran. dispose() is idempotent.
//
// After dispose(), a late registration is undone at once: listen() and timeout() do nothing, add() runs its step,
// track() disposes the thing, objectUrl() revokes the URL (e.g. an image that finished loading after the viewer went).
import type { CreateDisposer, Disposer } from '../contracts';

export const createDisposer: CreateDisposer = () => {
  const undo: (() => void)[] = [];
  const tracked = new Set<{ dispose(): void }>();
  const timers = new Map<number, ReturnType<typeof setTimeout>>();
  let nextTimer = 1;
  let disposed = false;

  const run = (steps: (() => void)[], errors: unknown[]) => {
    for (let i = steps.length - 1; i >= 0; i--) {
      try { steps[i]!(); } catch (err) { errors.push(err); }
    }
  };

  const disposer: Disposer = {
    listen(target: EventTarget, type: string, fn: (e: Event) => void, opts?: AddEventListenerOptions | boolean): void {
      if (disposed) return;
      target.addEventListener(type, fn, opts);
      // Removal names the capture flag as an options object: Node's EventTarget ignores a bare boolean there.
      const capture = typeof opts === 'boolean' ? opts : !!opts?.capture;
      undo.push(() => target.removeEventListener(type, fn, { capture }));
    },

    timeout(fn: () => void, ms: number): number {
      if (disposed) return 0;
      const id = nextTimer++;
      timers.set(id, setTimeout(() => { timers.delete(id); fn(); }, ms));
      return id;
    },

    clearTimeout(id: number): void {
      const handle = timers.get(id);
      if (handle === undefined) return;
      clearTimeout(handle);
      timers.delete(id);
    },

    track<T extends { dispose(): void }>(thing: T): T {
      if (disposed) thing.dispose();
      else tracked.add(thing);
      return thing;
    },

    add(step: () => void): void {
      if (disposed) step();
      else undo.push(step);
    },

    objectUrl(url: string): string {
      if (disposed) URL.revokeObjectURL(url);
      else undo.push(() => URL.revokeObjectURL(url));
      return url;
    },

    get disposed() { return disposed; },

    dispose(): void {
      if (disposed) return;
      disposed = true;
      const errors: unknown[] = [];
      for (const handle of timers.values()) clearTimeout(handle);
      timers.clear();
      run(undo.splice(0), errors);
      run([...tracked].map(t => () => t.dispose()), errors);
      tracked.clear();
      for (const err of errors) console.error('[viewer] dispose step failed:', err);
    },
  };
  return disposer;
};
