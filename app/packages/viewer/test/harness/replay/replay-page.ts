// Replay harness page (builder D; DESIGN.md 17.4, WORK_BREAKDOWN D): the real installReplay on the shared test context
// with the real WebGL renderer, started in viewer.ts's order (DESIGN.md 11.4 step 8), for the Build card, play, skip,
// replay again, the camera path and the rise shader on the GPU. Served by `npm run harness -- --port 5724`:
//   /replay/replay.html?model=bank-v2|bank-v1|synthetic&build=settings|play|skip&speed=quick&captions=0&ground=1
// Exposes window.__build (the ReplayApi, as the test hook does), window.__replayCtx (the context) and
// window.__replayKit (pixels(): the rise shader checked pixel by pixel on the synthetic wall).
import { Vector3 } from 'three';
import type { AddressOptions, BuildStart, BuiltModel, Presentation, ReplayData } from '../../../src/contracts';
import { installReplay } from '../../../src/replay/index';
import { isSpeed } from '../../../src/replay/timeline';
import { makeTestContext, type TestContext } from '../context';
import bankV1 from '../../../../../fixtures/models/bank-v1.model.json';
import bankV2 from '../../../../../fixtures/models/bank-v2.model.json';
import bankV1Pres from '../../../../../fixtures/presentation/bank-sampeng-v1.json';
import bankV2Pres from '../../../../../fixtures/presentation/bank-sampeng-v2.json';
import bankV1Stages from '../../../../../fixtures/stages/bank-v1.stages.json';
import bankV2Stages from '../../../../../fixtures/stages/bank-v2.stages.json';
import { syntheticModel, syntheticStages } from './synthetic';

export interface ReplayKit {
  ready: true;
  model: string;
  /** Seeks T (or skips to the end with null), stops the loop, looks at the synthetic wall from 8 m and reads the pixel at each height (m) of its middle. */
  pixels(T: number | null, heights: number[]): number[][];
}
declare global { interface Window { __replayKit?: ReplayKit | { error: string }; __replayCtx?: TestContext } }

const SETS: Record<string, { model: BuiltModel; stages: ReplayData; presentation: Presentation }> = {
  'bank-v2': { model: bankV2 as unknown as BuiltModel, stages: bankV2Stages as unknown as ReplayData, presentation: bankV2Pres as unknown as Presentation },
  'bank-v1': { model: bankV1 as unknown as BuiltModel, stages: bankV1Stages as unknown as ReplayData, presentation: bankV1Pres as unknown as Presentation },
  synthetic: {
    model: syntheticModel, stages: syntheticStages,
    presentation: { documentTitle: 'Wall', heading: 'Wall', intro: [], accent: '#2f6f8f', legend: { layout: 'inline', items: [] }, camera: { kind: 'fixed', position: [12, 9, 14], target: [0, 1.5, 0], far: 600 } },
  },
};

try {
  const q = new URLSearchParams(location.search);
  const which = q.get('model') ?? 'bank-v2';
  const set = SETS[which];
  if (!set) throw new Error(`unknown model ${which}`);
  const presentation: Presentation = q.get('ground') === '1' ? { ...set.presentation, groundPlane: { size: [80, 50], colour: '#dfe3e0' } } : set.presentation;
  const ctx = makeTestContext({ model: set.model, presentation, stages: set.stages, renderer: 'webgl', container: document.getElementById('app')! });
  // What the real root (ui/root.ts) gives the replay's CSS: the custom properties, the page font, the size container.
  const root = ctx.ui.root;
  const vars = { '--bg': '#eef0f2', '--panel': '#ffffffee', '--ink': '#1d2329', '--muted': '#5b6670', '--line': '#d5dade', '--accent': ctx.presentation.accent };
  for (const [k, v] of Object.entries(vars)) root.style.setProperty(k, v);
  root.style.setProperty('container', 'wtv / size');
  root.style.font = '14px/1.4 system-ui, -apple-system, "Segoe UI", sans-serif';
  root.style.color = '#1d2329';
  // The kit's slot panel and hint, placed where the real ones are (top left; bottom), so the Build row can be clicked.
  Object.assign(ctx.panel.el.style, {
    position: 'absolute', top: '12px', left: '12px', width: '330px', padding: '12px 14px', background: 'var(--panel)',
    border: '1px solid var(--line)', borderRadius: '10px', zIndex: '6',
  });
  ctx.ui.hint.textContent = 'Drag to orbit · right-drag to pan · scroll to zoom';
  Object.assign(ctx.ui.hint.style, { position: 'absolute', left: '12px', bottom: '10px', fontSize: '12px', color: 'var(--muted)' });

  const replay = installReplay(ctx);
  ctx.replay = replay;
  // viewer.ts start-up, in the prototypes' order (DESIGN.md 11.4 step 8a - 8e)
  const b = q.get('build');
  const build: BuildStart = b === 'play' || b === 'skip' ? b : 'settings';
  const address: AddressOptions = {};
  const speed = q.get('speed');
  if (isSpeed(speed)) address.speed = speed;
  if (q.get('captions') === '0') address.captions = false;
  if (replay) replay.start(build, address); else ctx.visibility.applyFloor();
  ctx.visibility.applyToggles();
  ctx.modes.applyAddress(address);
  if (replay) ctx.loop.add('replay', now => replay.tick(now));
  ctx.loop.add('modes', now => ctx.modes.tick(now));
  ctx.loop.start();

  window.__replayCtx = ctx;
  window.__build = replay;
  window.__replayKit = {
    ready: true,
    model: which,
    pixels(T, heights) {
      ctx.loop.stop();
      if (!replay) throw new Error('no replay');
      if (T === null) replay.skip(); else replay.seek(T);
      ctx.camera.position.set(0, 1.5, 8);
      ctx.controls.target.set(0, 1.5, 0);
      ctx.camera.lookAt(0, 1.5, 0);
      ctx.camera.updateMatrixWorld();
      ctx.renderer.render(ctx.scene, ctx.camera);
      const gl = ctx.renderer.getContext();
      return heights.map(h => {
        const v = new Vector3(0, h, 0.15).project(ctx.camera);
        const x = Math.round((v.x + 1) / 2 * gl.drawingBufferWidth), y = Math.round((v.y + 1) / 2 * gl.drawingBufferHeight);
        const px = new Uint8Array(4);
        gl.readPixels(x, y, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, px);
        return [...px];
      });
    },
  };
} catch (err) {
  window.__replayKit = { error: String(err instanceof Error ? err.stack ?? err.message : err) };
}
