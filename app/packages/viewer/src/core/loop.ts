// The frame loop: replay -> modes -> sync -> render -> overlay (DESIGN.md 11.4), as each page's
// renderer.setAnimationLoop(() => { replay.tick(); modes.tick(); renderer.render(scene, camera); placeLabels(); }).
// Owner: builder A. Only viewer.ts registers hooks (11.4 step 8d). An error in a hook (or in render) goes to
// ctx.reportError and the loop goes on. `firstFrame` (not in the contract: viewer.ts's `ready`) resolves after the first
// frame was drawn, or when the loop is stopped for good.
import type { CreateLoop, LoopApi, TickPhase } from '../contracts';

export interface CoreLoop extends LoopApi {
  /** Resolves after the first frame (or on dispose, so that nothing waits forever). */
  readonly firstFrame: Promise<void>;
}

export const createLoop = ((ctx): CoreLoop => {
  const hooks: Record<TickPhase, ((now: number) => void)[]> = { replay: [], modes: [], sync: [], overlay: [] };
  let running = false;
  let resolveFirst!: () => void;
  const firstFrame = new Promise<void>(resolve => { resolveFirst = resolve; });
  const now0 = () => (typeof performance !== 'undefined' ? performance.now() : Date.now());

  const runPhase = (phase: TickPhase, now: number) => {
    for (const fn of hooks[phase].slice()) {
      try { fn(now); } catch (err) { ctx.reportError(err); }
    }
  };
  const frame = (now: number = now0()): void => {
    runPhase('replay', now);
    runPhase('modes', now);
    runPhase('sync', now);
    try { ctx.renderer.render(ctx.scene, ctx.camera); } catch (err) { ctx.reportError(err); }
    runPhase('overlay', now);
    resolveFirst();
  };

  const loop: CoreLoop = {
    add(phase, fn) {
      hooks[phase].push(fn);
      return () => { const i = hooks[phase].indexOf(fn); if (i >= 0) hooks[phase].splice(i, 1); };
    },
    start() {
      if (running || ctx.disposer.disposed) return;
      running = true;
      ctx.renderer.setAnimationLoop(t => frame(t));
    },
    stop() {
      if (!running) return;
      running = false;
      ctx.renderer.setAnimationLoop(null);
    },
    frame,
    get running() { return running; },
    firstFrame,
  };
  ctx.disposer.add(() => { loop.stop(); resolveFirst(); });
  return loop;
}) satisfies CreateLoop;
