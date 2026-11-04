// @vitest-environment happy-dom
// Builder C: createRoot (DESIGN.md 11.6, 11.8, 18.17): the root element, its one constructed stylesheet in
// document.adoptedStyleSheets (and the <style> fallback where constructed sheets are missing), hint, error box, flags, the
// CSS variables, and nothing left after dispose.
import { afterEach, describe, expect, it } from 'vitest';
import { createDisposer } from '../../../src/core/disposer';
import { BASE_CSS } from '../../../src/ui/css';
import { createRoot } from '../../../src/ui/root';

const containers: HTMLElement[] = [];
const container = () => { const c = document.createElement('div'); document.body.append(c); containers.push(c); return c; };
afterEach(() => { for (const c of containers.splice(0)) c.remove(); document.adoptedStyleSheets = []; });

describe('createRoot', () => {
  it('puts <div class="wtv" data-wt="root" data-model-stamp> with the hint and the hidden error box into the container', () => {
    const c = container(), d = createDisposer();
    const ui = createRoot(c, '#8a6d3b', 'f1b95c53eb3d', d);
    expect(ui.root.parentElement).toBe(c);
    expect(ui.root.className).toBe('wtv');
    expect(ui.root.getAttribute('data-wt')).toBe('root');
    expect(ui.root.getAttribute('data-model-stamp')).toBe('f1b95c53eb3d');
    expect(ui.root.style.getPropertyValue('--accent')).toBe('#8a6d3b');
    expect(ui.hint.getAttribute('data-wt')).toBe('hint');
    expect(ui.hint.parentElement).toBe(ui.root);
    expect(ui.errorBox.getAttribute('data-wt')).toBe('error');
    expect(ui.errorBox.getAttribute('role')).toBe('alert');
    expect(ui.errorBox.hidden).toBe(true);
    expect(ui.root.hasAttribute('style') && !/[{}]/.test(ui.root.getAttribute('style')!)).toBe(true);   // CSSOM, no rules in the attribute
    d.dispose();
  });

  it('keeps its CSS in one constructed sheet in document.adoptedStyleSheets, BASE_CSS first; addStyle appends each chunk once', () => {
    const c = container(), d = createDisposer();
    const before = document.adoptedStyleSheets.length;
    const ui = createRoot(c, '#2f6f8f', 'x', d);
    expect(document.adoptedStyleSheets.length).toBe(before + 1);
    expect(ui.root.querySelector('style')).toBeNull();
    const sheet = document.adoptedStyleSheets.at(-1)!;
    const text = () => [...sheet.cssRules].map(r => r.cssText).join('\n');
    expect(sheet.cssRules.length).toBeGreaterThan(10);
    expect(text()).toContain('all: revert');
    ui.addStyle('.wtv .chunk-a { color: red; }');
    ui.addStyle('.wtv .chunk-a { color: red; }');
    ui.addStyle('.wtv .chunk-b { color: blue; }');
    expect(text().match(/chunk-a/g)!.length).toBe(1);
    expect(text().indexOf('all: revert')).toBeLessThan(text().indexOf('chunk-a'));
    expect(text().indexOf('chunk-a')).toBeLessThan(text().indexOf('chunk-b'));
    d.dispose();
    expect(document.adoptedStyleSheets.includes(sheet)).toBe(false);
    expect(c.children.length).toBe(0);
  });

  it('two viewers have two sheets; disposing one leaves the other and any sheet of the host page', () => {
    const host = new CSSStyleSheet();
    host.replaceSync('body { margin: 0 }');
    document.adoptedStyleSheets = [host];
    const d1 = createDisposer(), d2 = createDisposer();
    createRoot(container(), '#2f6f8f', 'a', d1);
    createRoot(container(), '#2f6f8f', 'b', d2);
    expect(document.adoptedStyleSheets.length).toBe(3);
    d1.dispose();
    expect(document.adoptedStyleSheets.length).toBe(2);
    expect(document.adoptedStyleSheets[0]).toBe(host);
    d2.dispose();
    expect(document.adoptedStyleSheets).toEqual([host]);
  });

  it('where constructed sheets are missing: one <style> inside the root, its text the chunks; removed with the root', () => {
    // a document without constructed sheets (an older engine): no adoptedStyleSheets on it
    Object.defineProperty(document, 'adoptedStyleSheets', { configurable: true, get: () => undefined, set: () => { throw new Error('no adopted sheets here'); } });
    try {
      const c = container(), d = createDisposer();
      const ui = createRoot(c, '#2f6f8f', 'x', d);
      const styles = ui.root.querySelectorAll('style');
      expect(styles.length).toBe(1);
      expect(styles[0]!.textContent).toBe(BASE_CSS);
      ui.addStyle('.wtv .chunk-c { color: red; }');
      expect(styles[0]!.textContent).toBe(BASE_CSS + '\n.wtv .chunk-c { color: red; }');
      d.dispose();
      expect(c.querySelector('style')).toBeNull();
      expect(document.querySelectorAll('style').length).toBe(0);
    } finally {
      delete (document as unknown as Record<string, unknown>).adoptedStyleSheets;
    }
    expect(Array.isArray(document.adoptedStyleSheets)).toBe(true);
    expect(document.adoptedStyleSheets.length).toBe(0);
  });

  it('flags: data-fp, data-camopen, data-crowded, data-touchui, data-replay on the root', () => {
    const d = createDisposer();
    const ui = createRoot(container(), '#2f6f8f', 'x', d);
    for (const f of ['fp', 'camopen', 'crowded', 'touchui', 'replay'] as const) {
      ui.setFlag(f, true);
      expect(ui.root.hasAttribute(`data-${f}`)).toBe(true);
      ui.setFlag(f, false);
      expect(ui.root.hasAttribute(`data-${f}`)).toBe(false);
    }
    d.dispose();
  });

  it('dispose leaves the container as it was (its own children stay)', () => {
    const c = container();
    c.append(document.createElement('span'));
    const d = createDisposer();
    createRoot(c, '#2f6f8f', 'x', d);
    expect(c.children.length).toBe(2);
    d.dispose();
    expect([...c.children].map(e => e.tagName)).toEqual(['SPAN']);
  });
});
