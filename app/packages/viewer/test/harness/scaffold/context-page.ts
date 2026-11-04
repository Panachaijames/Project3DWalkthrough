// Scaffold harness page: makeTestContext with the real WebGL renderer on the bank v2 fixture; one frame drawn, the middle
// pixel read back, a Walk-height ray hits a wall. Results in window.__kit for webgl.spec.ts.
import type { BuiltModel, Presentation } from '../../../src/contracts';
import { makeTestContext } from '../context';
import model from '../../../../../fixtures/models/bank-v2.model.json';
import presentation from '../../../../../fixtures/presentation/bank-sampeng-v2.json';

declare global { interface Window { __kit?: { pixel: number[]; floors: string[]; colliders: number; hit: string | null; disposed: boolean } | { error: string } } }

try {
  const ctx = makeTestContext({
    model: model as unknown as BuiltModel,
    presentation: presentation as unknown as Presentation,
    renderer: 'webgl',
    container: document.getElementById('app')!,
  });
  ctx.loop.frame();
  const gl = ctx.renderer.getContext();
  const px = new Uint8Array(4);
  gl.readPixels(Math.floor(gl.drawingBufferWidth / 2), Math.floor(gl.drawingBufferHeight / 2), 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, px);
  const floor = ctx.floors[0]!;
  const hit = ctx.readouts.cast(floor.key, [0, floor.level + 1.2, 0], [1, 0, 0], 100);
  window.__kit = { pixel: [...px], floors: ctx.floors.map(f => f.key), colliders: floor.colliders.length, hit: hit ? hit.name : null, disposed: false };
  (window as unknown as { __ctx: typeof ctx }).__ctx = ctx;
} catch (err) {
  window.__kit = { error: String(err) };
}
