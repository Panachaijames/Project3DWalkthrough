// Builder C's harness page script (see furniture.html). The shared test context draws the model with the real WebGL renderer;
// C's own root, panel and furniture take the place of the kit's minimal root and slot panel, so the CSS, the panel sizes and
// the legend are the ones the viewer ships. Modes and the replay are not here (B and D): their panel rows are stand-ins of the
// same size (the pages' "Look around" and "Build" rows), so the panel holds what it holds on a page.
import { Vector3 } from 'three';
import type { BuiltModel, FurnitureApi, Presentation, ViewerContext } from '../../../src/contracts';
import { installFurniture } from '../../../src/furniture/index';
import { el } from '../../../src/ui/dom';
import { createPanel } from '../../../src/ui/panel';
import { createRoot } from '../../../src/ui/root';
import { makeTestContext, type TestContext } from '../context';
import mini from '../../../../../fixtures/models/mini.model.json';
import bank from '../../../../../fixtures/models/bank-v2.model.json';
import suite from '../../../../../fixtures/models/suite.model.json';
import house from '../../../../../fixtures/models/house.model.json';
import hotel from '../../../../../fixtures/models/hotel.model.json';
import bankP from '../../../../../fixtures/presentation/bank-sampeng-v2.json';
import suiteP from '../../../../../fixtures/presentation/presidential-suite.json';
import houseP from '../../../../../fixtures/presentation/sukhumvit-house.json';
import hotelP from '../../../../../fixtures/presentation/hotel-lobby.json';

export interface FurnHarness {
  ctx: ViewerContext;
  kit: TestContext;
  F: FurnitureApi | null;
  /** Files the viewer asked to download (the kit's options.download). */
  downloads: { blob: Blob; fileName: string }[];
  stamp: string;
  frames: number;
  /** Looks straight down at the model from above (a little to the south), as the hover checks want it. */
  viewFromAbove(): void;
  /** Viewport (client) coordinates of a three.js point. */
  screenAt(x: number, y: number, z: number): [number, number];
}
declare global { interface Window { __furn?: FurnHarness | { error: string } } }

const MODELS: Record<string, { model: unknown; presentation?: unknown; stamp: string; replay: boolean }> = {
  mini: { model: mini, stamp: 'a469ffbe5a93', replay: false },
  'bank-v2': { model: bank, presentation: bankP, stamp: 'c3a9408304a2', replay: true },
  suite: { model: suite, presentation: suiteP, stamp: 'f1b95c53eb3d', replay: true },
  house: { model: house, presentation: houseP, stamp: 'e43270cc0c9b', replay: true },
  hotel: { model: hotel, presentation: hotelP, stamp: '6ab030750886', replay: false },
};
const HINT_ORBIT = 'Drag to orbit · right-drag to pan · scroll to zoom · double-click a floor to walk there · 1 / 2 / 3: Orbit / Walk / Ghost · P: photo';

function hostReset(): void {                  // a reset like Tailwind 4's preflight, in @layer base (the staff app has one)
  const s = document.createElement('style');
  s.textContent = `@layer base { *, ::before, ::after { box-sizing: border-box; margin: 0; padding: 0; border: 0 solid; }
    h1, h2, h3 { font-size: inherit; font-weight: inherit; } ul, ol { list-style: none; }
    button, input, select { font: inherit; color: inherit; background-color: transparent; border-radius: 0; } }`;
  document.head.append(s);
}

/** The pages' "Look around" / "Build" rows (viewer_modes.js, build_replay.js), here only for their size. */
function standInRow(label: string, buttons: string[]): HTMLDivElement {
  return el('div', { attrs: { 'data-stand-in': label } }, [
    el('div', { text: label, style: { fontSize: '11px', letterSpacing: '.06em', textTransform: 'uppercase', color: 'var(--muted)', margin: '10px 0 4px' } }),
    el('div', { style: { display: 'flex', gap: '6px', flexWrap: 'wrap', alignItems: 'center' } }, buttons.map(t => el('button', { attrs: { type: 'button' }, text: t }))),
  ]);
}

try {
  const q = new URLSearchParams(location.search);
  const pick = MODELS[q.get('model') ?? 'mini'] ?? MODELS.mini!;
  if (q.get('reset') === 'tailwind') hostReset();
  const container = document.getElementById('app')!;
  const kit = makeTestContext({
    model: pick.model as BuiltModel, presentation: pick.presentation as Presentation | undefined, renderer: 'webgl', container, stamp: pick.stamp,
    // ?edit=1: the staff app's version page (options.editBoxes; docs/boxes/DESIGN.md 2.1): boxes can be selected and deleted
    options: { furnitureHeights: q.get('mode') === 'host' ? 'host' : 'local', noDownload: q.get('nodownload') === '1', ...(q.get('edit') === '1' ? { editBoxes: true } : {}) },
  });
  // C's root in place of the kit's: the canvas moves over, the kit's minimal root goes
  const ui = createRoot(container, kit.presentation.accent, pick.stamp, kit.disposer);
  ui.root.prepend(kit.canvas);
  kit.ui.root.remove();
  const ctx: ViewerContext = Object.assign({}, kit, {
    ui,
    size: () => ({ width: ui.root.clientWidth || 1400, height: ui.root.clientHeight || 880 }),
    rectOf: (e: Element) => {
      const r = e.getBoundingClientRect(), b = ui.root.getBoundingClientRect();
      return { left: r.left - b.left, top: r.top - b.top, right: r.right - b.left, bottom: r.bottom - b.top, width: r.width, height: r.height };
    },
    reportError: (err: unknown) => { ui.errorBox.textContent = 'Viewer error: ' + (err instanceof Error ? err.message : String(err)); ui.errorBox.hidden = false; },
  });
  ui.hint.textContent = HINT_ORBIT;
  ctx.panel = createPanel(ctx);
  ctx.panel.slot('modes').append(standInRow('Look around', ['Orbit', 'Walk', 'Ghost', 'Camera']));
  if (pick.replay) ctx.panel.slot('build').append(standInRow('Build', ['Replay the build', 'Build settings']));
  const F = installFurniture(ctx);
  ctx.furniture = F;

  // the drawing buffer follows the root (what core/context does in the viewer)
  const fit = () => {
    const { width, height } = ctx.size();
    kit.renderer.setSize(width, height, false);
    kit.camera.aspect = width / height;
    kit.camera.updateProjectionMatrix();
  };
  fit();
  const ro = new ResizeObserver(fit);
  ro.observe(ui.root);
  kit.disposer.add(() => ro.disconnect());
  const harness: FurnHarness = {
    ctx, kit, F, downloads: kit.kit.downloads, stamp: pick.stamp, frames: 0,
    viewFromAbove: () => {
      kit.camera.position.set(0, 40, 8); kit.controls.target.set(0, 0, 0); kit.camera.lookAt(0, 0, 0); kit.controls.update();
      kit.camera.updateMatrixWorld();
    },
    screenAt: (x, y, z) => {
      kit.camera.updateMatrixWorld();
      const v = new Vector3(x, y, z).project(kit.camera), b = ui.root.getBoundingClientRect();
      return [b.left + (v.x + 1) / 2 * b.width, b.top + (1 - v.y) / 2 * b.height];
    },
  };
  kit.loop.add('modes', () => { kit.controls.update(); harness.frames++; });
  kit.loop.start();
  window.__furn = harness;
} catch (err) {
  window.__furn = { error: err instanceof Error ? `${err.message}\n${err.stack}` : String(err) };
}
