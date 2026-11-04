// apps/web/index.html (fix step, 3-4 Nov review): an icon in the page (no /favicon.ico request: a 404 and a console error
// on every load, findings "parity-cad" 3, "parity-revit-pictures" 2, "adversarial" 13), and the inline script that keeps
// the browser's harmless ResizeObserver-loop notification away from the window's other error listeners (Vite's dev
// client forwarded it to the terminal as "[Unhandled error]", "adversarial" 14). The script is run here as shipped; the
// same is checked in Edge by tests/e2e/web.spec.ts.
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { afterEach, describe, expect, it } from 'vitest';

const HTML = readFileSync(path.resolve(__dirname, '..', 'index.html'), 'utf8');
const LOOP = 'ResizeObserver loop completed with undelivered notifications.';
const cleanups: (() => void)[] = [];
afterEach(() => { while (cleanups.length) cleanups.pop()!(); });

describe('index.html', () => {
  it('has one icon of its own (a data: URL), so the browser asks for no /favicon.ico', () => {
    const icons = [...HTML.matchAll(/<link\s+rel="icon"\s+href="([^"]+)"/g)].map(m => m[1]!);
    expect(icons).toHaveLength(1);
    expect(icons[0]!.startsWith('data:image/')).toBe(true);
  });

  it('its inline script comes before the app (a classic script in the head) and stops only the ResizeObserver-loop notification', () => {
    const m = /<script id="benign-errors">([\s\S]*?)<\/script>/.exec(HTML);
    expect(m).not.toBeNull();
    expect(HTML.indexOf('<script id="benign-errors">')).toBeLessThan(HTML.indexOf('</head>'));
    expect(HTML.indexOf('<script id="benign-errors">')).toBeLessThan(HTML.indexOf('src="/src/main.tsx"'));
    // run it as the page does, registering on this window first; then a listener added later, as Vite's client is
    const added: [string, EventListenerOrEventListenerObject][] = [];
    const add = window.addEventListener.bind(window);
    window.addEventListener = ((type: string, fn: EventListenerOrEventListenerObject, o?: unknown) => { added.push([type, fn]); add(type, fn, o as boolean); }) as typeof window.addEventListener;
    try { new Function(m![1]!)(); } finally { window.addEventListener = add as typeof window.addEventListener; }
    cleanups.push(() => { for (const [type, fn] of added) window.removeEventListener(type, fn); });
    const seen: string[] = [];
    const later = (e: ErrorEvent) => seen.push(e.message);
    window.addEventListener('error', later);
    cleanups.push(() => window.removeEventListener('error', later));
    window.dispatchEvent(new ErrorEvent('error', { message: LOOP }));
    window.dispatchEvent(new ErrorEvent('error', { message: 'ResizeObserver loop limit exceeded' }));
    window.dispatchEvent(new ErrorEvent('error', { message: LOOP, error: new Error(LOOP) }));   // a real throw: reported
    window.dispatchEvent(new ErrorEvent('error', { message: 'a real error (test)' }));
    expect(seen).toEqual([LOOP, 'a real error (test)']);
  });
});
