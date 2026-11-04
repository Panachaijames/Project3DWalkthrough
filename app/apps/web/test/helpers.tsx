// Small DOM test helpers for the web unit tests (happy-dom, React 19; no testing library in the frozen list).
import { act, StrictMode, type ReactNode } from 'react';
import { createRoot, type Root } from 'react-dom/client';

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

export interface Mounted {
  host: HTMLDivElement;
  root: Root;
  rerender(ui: ReactNode): Promise<void>;
  unmount(): Promise<void>;
}

/** Renders into a fresh div in the document (StrictMode unless strict: false). */
export async function render(ui: ReactNode, { strict = true }: { strict?: boolean } = {}): Promise<Mounted> {
  const host = document.createElement('div');
  document.body.append(host);
  const root = createRoot(host);
  const wrap = (node: ReactNode) => (strict ? <StrictMode>{node}</StrictMode> : node);
  await act(async () => { root.render(wrap(ui)); });
  return {
    host,
    root,
    rerender: async node => { await act(async () => { root.render(wrap(node)); }); },
    unmount: async () => { await act(async () => { root.unmount(); }); host.remove(); },
  };
}

/** Lets pending promises, timers of `ms` and React updates run. */
export async function settle(ms = 0): Promise<void> {
  await act(async () => { await new Promise(r => setTimeout(r, ms)); });
}

/** Polls `check` (inside act) until it returns a truthy value or throws past the timeout (generous: the machine is shared). */
export async function waitFor<T>(check: () => T, { timeout = 15_000, interval = 10 } = {}): Promise<NonNullable<T>> {
  const t0 = Date.now();
  let last: unknown;
  for (;;) {
    try {
      const v = check();
      if (v) return v as NonNullable<T>;
      last = new Error('waitFor: check returned a falsy value');
    } catch (err) {
      last = err;
    }
    if (Date.now() - t0 > timeout) throw last;
    await settle(interval);
  }
}

/** Clicks an element (a real click event, inside act). */
export async function click(el: Element | null | undefined): Promise<void> {
  if (!el) throw new Error('click: no element');
  await act(async () => { (el as HTMLElement).click(); });
}

/** happy-dom has no WebGL: a minimal context so the fake viewer can start (returns the restore function). */
export function stubWebGL(opts: { fail?: () => boolean } = {}): () => void {
  const proto = HTMLCanvasElement.prototype as unknown as { getContext: (type: string) => unknown };
  const original = proto.getContext;
  proto.getContext = function getContext(type: string) {
    if (!/webgl/i.test(type)) return original.call(this, type);
    if (opts.fail?.()) return null;
    let lost = false;
    return {
      COLOR_BUFFER_BIT: 0x4000,
      clearColor() {},
      clear() {},
      isContextLost: () => lost,
      getExtension: (name: string) => (name === 'WEBGL_lose_context' ? { loseContext: () => { lost = true; } } : null),
    };
  };
  return () => { proto.getContext = original; };
}

export const text = (el: Element | null | undefined) => (el?.textContent ?? '').replace(/\s+/g, ' ').trim();
export const all = (root: ParentNode, selector: string) => [...root.querySelectorAll(selector)];
