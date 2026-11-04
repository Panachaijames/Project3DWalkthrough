// Scaffold (complete; everyone uses it, nobody else edits it). A typed event bus: ctx.bus (InternalEvents) and
// ctx.events (the public ViewerEvents), DESIGN.md 11.5.
//
// emit() calls the listeners registered at the moment of the call, in registration order. A listener that throws does
// not stop the others: after all ran, the error is rethrown (an AggregateError when more than one threw).
// on() returns its own off(); the same function registered twice for one type is kept once.
import type { CreateEventBus, EventBus } from '../contracts';

export const createEventBus: CreateEventBus = <E>() => {
  const listeners = new Map<keyof E, Set<(payload: never) => void>>();

  const bus: EventBus<E> = {
    on<K extends keyof E>(type: K, fn: (payload: E[K]) => void): () => void {
      let set = listeners.get(type);
      if (!set) listeners.set(type, (set = new Set()));
      const entry = fn as (payload: never) => void;
      set.add(entry);
      return () => { listeners.get(type)?.delete(entry); };
    },

    emit<K extends keyof E>(type: K, payload: E[K]): void {
      const set = listeners.get(type);
      if (!set || set.size === 0) return;
      const errors: unknown[] = [];
      for (const fn of [...set]) {
        try { (fn as (p: E[K]) => void)(payload); } catch (err) { errors.push(err); }
      }
      if (errors.length === 1) throw errors[0];
      if (errors.length > 1) throw new AggregateError(errors, `[viewer] ${errors.length} listeners of '${String(type)}' failed`);
    },

    clear(): void {
      listeners.clear();
    },
  };
  return bus;
};
