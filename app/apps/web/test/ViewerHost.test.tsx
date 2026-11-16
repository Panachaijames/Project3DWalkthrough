// ViewerHost with a fake `create` (DESIGN.md 15.4, 17.2 web): one viewer after StrictMode's double mount, disposed on
// unmount and on a project change (the old one before the new one, on the same div), a `create` that throws reported
// through onError with nothing to dispose, the latest callbacks used without re-creating the viewer.
import type { CreateViewer, HeightMap, PieceEditMap, Viewer, ViewerEvents, ViewerOptions, ViewerProject } from '@walkthrough/viewer';
import { describe, expect, it, vi } from 'vitest';
import { ViewerHost } from '@/components/ViewerHost';
import { render } from './helpers';

vi.mock('@walkthrough/viewer', async () => vi.importActual('./fake-viewer'));

interface Made {
  n: number;
  container: HTMLElement;
  /** Whether the container was still in the document when dispose() ran (null: not disposed). */
  connectedAtDispose: boolean | null;
  project: ViewerProject;
  options: ViewerOptions | undefined;
  disposed: boolean;
  handlers: Set<(e: ViewerEvents['heightschange']) => void>;
  emit(heights: HeightMap): void;
  /** step BX: the boxeschange listeners, and a deleted-boxes map sent to them. */
  boxHandlers: Set<(e: ViewerEvents['boxeschange']) => void>;
  emitBoxes(pieceEdits: PieceEditMap): void;
  viewer: Viewer;
}

function fakeCreate(opts: { throwFor?: (n: number) => boolean } = {}) {
  const made: Made[] = [];
  const log: string[] = [];
  let count = 0;
  const create = vi.fn<CreateViewer>((container, project, options) => {
    const n = ++count;
    if (opts.throwFor?.(n)) {
      log.push(`fail ${n}`);
      throw new Error(`create ${n} failed`);
    }
    const node = document.createElement('div');
    node.className = 'fake-root';
    node.dataset.n = String(n);
    container.append(node);
    const handlers = new Set<(e: ViewerEvents['heightschange']) => void>();
    const boxHandlers = new Set<(e: ViewerEvents['boxeschange']) => void>();
    const m: Made = {
      n, container, project, options, disposed: false, handlers, connectedAtDispose: null, boxHandlers,
      emit: heights => { for (const fn of [...handlers]) fn({ heights, source: 'typed' }); },
      emitBoxes: pieceEdits => { for (const fn of [...boxHandlers]) fn({ pieceEdits, source: 'removed' }); },
      viewer: {
        on: ((event: keyof ViewerEvents, fn: (e: never) => void) => {
          if (event === 'heightschange') handlers.add(fn);
          if (event === 'boxeschange') boxHandlers.add(fn);
          return () => { handlers.delete(fn); boxHandlers.delete(fn); };
        }) as Viewer['on'],
        dispose: () => {
          if (m.disposed) return;
          m.disposed = true;
          m.connectedAtDispose = container.isConnected;
          node.remove();
          log.push(`dispose ${n}`);
        },
      } as Viewer,
    };
    made.push(m);
    log.push(`create ${n}`);
    return m.viewer;
  });
  return { create, made, log, live: () => made.filter(m => !m.disposed) };
}

const project = (stamp: string) => ({ stamp, model: { floors: [] }, presentation: {} }) as unknown as ViewerProject;
const OPTIONS: ViewerOptions = { build: 'skip', furnitureHeights: 'host' };

describe('ViewerHost', () => {
  it('leaves one viewer after StrictMode mounts it twice on the same div', async () => {
    const f = fakeCreate();
    const p = project('aaaaaaaaaaaa');
    const v = await render(<ViewerHost project={p} options={OPTIONS} create={f.create} />);
    expect(f.create).toHaveBeenCalledTimes(2);
    expect(f.log).toEqual(['create 1', 'dispose 1', 'create 2']);
    expect(f.live().map(m => m.n)).toEqual([2]);
    const host = v.host.querySelector('[data-testid=viewer-host]');
    expect(host?.className).toBe('viewer-host');
    expect(f.made[0]!.container).toBe(host);
    expect(f.made[1]!.container).toBe(host);
    expect(host?.querySelectorAll('.fake-root').length).toBe(1);
    expect(f.made[1]!.project).toBe(p);
    expect(f.made[1]!.options).toBe(OPTIONS);
    expect(f.made[0]!.handlers.size).toBe(0);   // the first one's listener was taken off
    await v.unmount();
    expect(f.live()).toEqual([]);
    expect(f.made[1]!.handlers.size).toBe(0);
  });

  it('disposes on unmount and leaves the container as it was', async () => {
    const f = fakeCreate();
    const v = await render(<ViewerHost project={project('bbbbbbbbbbbb')} create={f.create} />, { strict: false });
    expect(f.log).toEqual(['create 1']);
    const host = v.host.querySelector('[data-testid=viewer-host]')!;
    expect(host.children.length).toBe(1);
    await v.rerender(null);
    expect(f.log).toEqual(['create 1', 'dispose 1']);
    expect(host.children.length).toBe(0);
    await v.unmount();
  });

  it('on unmount disposes while its container is still in the document (React takes the DOM out before effect cleanups)', async () => {
    const f = fakeCreate();
    const v = await render(<ViewerHost project={project('abababababab')} options={OPTIONS} create={f.create} />);
    expect(f.made.map(m => m.connectedAtDispose)).toEqual([true, null]);   // StrictMode's dispose: the div stays in place
    await v.rerender(null);
    expect(f.live()).toEqual([]);
    // OrbitControls removes its capturing keydown listener from canvas.getRootNode(): with the canvas already out of the
    // document that is the detached subtree, and the document's listener would stay (contract-issues/F.md F-5)
    expect(f.made.map(m => m.connectedAtDispose)).toEqual([true, true]);
    expect(f.log).toEqual(['create 1', 'dispose 1', 'create 2', 'dispose 2']);
    await v.unmount();
  });

  it('re-creates on a new project (a version change), disposing the old viewer first, on the same div', async () => {
    const f = fakeCreate();
    const p1 = project('111111111111');
    const p2 = project('222222222222');
    const v = await render(<ViewerHost project={p1} options={OPTIONS} create={f.create} />);
    f.log.length = 0;
    await v.rerender(<ViewerHost project={p2} options={OPTIONS} create={f.create} />);
    expect(f.log).toEqual(['dispose 2', 'create 3']);
    expect(f.live().map(m => m.project)).toEqual([p2]);
    expect(f.made[2]!.container).toBe(f.made[1]!.container);
    // the same project and options with new callbacks: nothing re-created
    f.log.length = 0;
    await v.rerender(<ViewerHost project={p2} options={OPTIONS} create={f.create} onHeightsChange={() => undefined} onError={() => undefined} />);
    expect(f.log).toEqual([]);
    // new options re-create too
    await v.rerender(<ViewerHost project={p2} options={{ ...OPTIONS }} create={f.create} />);
    expect(f.log).toEqual(['dispose 3', 'create 4']);
    await v.unmount();
    expect(f.live()).toEqual([]);
  });

  it('sends heightschange to the latest onHeightsChange without re-creating the viewer', async () => {
    const f = fakeCreate();
    const p = project('cccccccccccc');
    const first = vi.fn();
    const second = vi.fn();
    const v = await render(<ViewerHost project={p} options={OPTIONS} create={f.create} onHeightsChange={first} />);
    f.live()[0]!.emit({ table: 600 });
    expect(first).toHaveBeenCalledWith({ table: 600 });
    await v.rerender(<ViewerHost project={p} options={OPTIONS} create={f.create} onHeightsChange={second} />);
    expect(f.create).toHaveBeenCalledTimes(2);   // StrictMode's two, nothing since
    f.live()[0]!.emit({ seat: 300 });
    expect(second).toHaveBeenCalledWith({ seat: 300 });
    expect(first).toHaveBeenCalledTimes(1);
    await v.unmount();
  });

  it('step BX: sends boxeschange to the latest onPieceEditsChange without re-creating the viewer; the listener goes on dispose', async () => {
    const f = fakeCreate();
    const p = project('c0c0c0c0c0c0');
    const first = vi.fn();
    const second = vi.fn();
    const v = await render(<ViewerHost project={p} options={OPTIONS} create={f.create} onPieceEditsChange={first} />);
    expect(f.made[0]!.boxHandlers.size).toBe(0);   // StrictMode's first viewer: its listener was taken off
    f.live()[0]!.emitBoxes({ 'L1-seat-001': { removed: true } });
    expect(first).toHaveBeenCalledWith({ 'L1-seat-001': { removed: true } });
    await v.rerender(<ViewerHost project={p} options={OPTIONS} create={f.create} onPieceEditsChange={second} />);
    expect(f.create).toHaveBeenCalledTimes(2);
    f.live()[0]!.emitBoxes({});
    expect(second).toHaveBeenCalledWith({});
    expect(first).toHaveBeenCalledTimes(1);
    const last = f.live()[0]!;
    await v.unmount();
    expect(last.boxHandlers.size).toBe(0);
  });

  it('reports a create that throws through onError, with nothing to dispose', async () => {
    const f = fakeCreate({ throwFor: () => true });
    const onError = vi.fn();
    const onCreated = vi.fn();
    const v = await render(<ViewerHost project={project('dddddddddddd')} create={f.create} onError={onError} onCreated={onCreated} />, { strict: false });
    expect(onError).toHaveBeenCalledTimes(1);
    expect((onError.mock.calls[0]![0] as Error).message).toBe('create 1 failed');
    expect(onCreated).not.toHaveBeenCalled();
    expect(v.host.querySelector('[data-testid=viewer-host]')!.children.length).toBe(0);
    await v.unmount();
    expect(f.log).toEqual(['fail 1']);   // no dispose: there was nothing to dispose
  });

  it('under StrictMode a failed first mount and a good second one: onError, then onCreated with the viewer', async () => {
    const f = fakeCreate({ throwFor: n => n === 1 });
    const onError = vi.fn();
    const onCreated = vi.fn();
    const v = await render(<ViewerHost project={project('eeeeeeeeeeee')} create={f.create} onError={onError} onCreated={onCreated} />);
    expect(f.log).toEqual(['fail 1', 'create 2']);
    expect(onError).toHaveBeenCalledTimes(1);
    expect(onCreated).toHaveBeenCalledTimes(1);
    expect(onCreated.mock.calls[0]![0]).toBe(f.made[0]!.viewer);
    await v.unmount();
    expect(f.log).toEqual(['fail 1', 'create 2', 'dispose 2']);
  });

  // Without a `create` prop, ViewerHost calls the package's createViewer. In this file the package IS the fake viewer
  // (vi.mock above), so this checks ViewerHost's default and the fake's live / created counters, nothing about the real
  // viewer's DOM: drawing text as text is checked on the real viewer by tests/e2e/offline.spec.ts (hostile names) and the
  // viewer's own panel tests (fix step, first code review finding 13: this test asserted the fake's heading).
  it('calls the package createViewer when no create is given (the fake module here): one live viewer, disposed on unmount', async () => {
    const fake = await import('./fake-viewer');
    fake.resetFakeViewer();
    const { stubWebGL } = await import('./helpers');
    const restore = stubWebGL();
    try {
      const model = { floors: [{ key: 'L1', name: 'Level 1', level: 0, wallHeight: 3, slabThickness: 0.2 }], parts: [] };
      const p = { model, presentation: { heading: 'Heading' }, stamp: 'ffffffffffff' } as unknown as ViewerProject;
      const v = await render(<ViewerHost project={p} options={{ testHook: true }} />);
      expect(fake.fakeViewerLog.map(r => r.event)).toEqual(['create', 'dispose', 'create']);
      expect(window.__walkthrough?.live()).toBe(1);
      expect(window.__walkthrough?.created()).toBe(2);
      expect([fake.fakeViewerLog[2]!.stamp, fake.fakeViewerLog[2]!.options?.testHook]).toEqual(['ffffffffffff', true]);   // as given
      await v.unmount();
      expect(window.__walkthrough).toBeUndefined();
      expect(fake.fakeViewerLog.map(r => r.event)).toEqual(['create', 'dispose', 'create', 'dispose']);
    } finally {
      restore();
    }
  });
});
