// @vitest-environment happy-dom
// Builder B: the key rules of modes/input.ts on their own (DESIGN.md 11.5 "Keys", 17.2 modes "typing rule"):
// typing() is viewer_modes.js's (text, number and search boxes and untyped inputs keep every key; a slider or a list
// keeps only the arrows), ours() is D-11.5's (the window, the document, the body or anything inside the root).
import { afterEach, describe, expect, it } from 'vitest';
import { ours, typing } from '../../../src/modes/input';

const made: Element[] = [];
afterEach(() => { for (const e of made.splice(0)) e.remove(); });
function input(type: string | null): HTMLInputElement {
  const e = document.createElement('input');
  if (type !== null) e.type = type;
  document.body.append(e);
  made.push(e);
  return e;
}
function element<K extends keyof HTMLElementTagNameMap>(tag: K, parent: Element = document.body): HTMLElementTagNameMap[K] {
  const e = document.createElement(tag);
  parent.append(e);
  made.push(e);
  return e;
}

describe('typing(e): the keys a focused control keeps', () => {
  it('text, number, search boxes, untyped inputs and text areas keep every key', () => {
    for (const t of [input('text'), input('number'), input('search'), input(null), element('textarea')]) {
      for (const code of ['KeyW', 'Digit2', 'KeyP', 'Space', 'ArrowUp', 'Escape']) expect(typing({ target: t, code }), `${t.tagName} ${code}`).toBe(true);
    }
  });

  it('a slider or a list keeps only the arrow keys', () => {
    const range = input('range'), select = element('select');
    for (const t of [range, select]) {
      for (const code of ['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight']) expect(typing({ target: t, code })).toBe(true);
      for (const code of ['KeyW', 'Digit2', 'KeyP', 'Space', 'PageUp', 'Tab']) expect(typing({ target: t, code })).toBe(false);
    }
    expect(typing({ target: range })).toBe(false);                 // no code: not an arrow
  });

  it('checkboxes, buttons, the body, the canvas and no target at all do not', () => {
    for (const t of [input('checkbox'), element('button'), document.body, element('canvas'), element('div')]) {
      expect(typing({ target: t, code: 'KeyW' })).toBe(false);
    }
    expect(typing({ target: null, code: 'KeyW' })).toBe(false);
    expect(typing({ target: window, code: 'KeyW' })).toBe(false);    // no matches(): not a control
  });
});

describe("ours(e, root): the key is the viewer's", () => {
  it('the window, the document, the html and body elements, and anything inside the root', () => {
    const root = element('div');
    const inner = element('button', element('div', root));
    for (const target of [window, document, document.documentElement, document.body, root, inner, null]) {
      expect(ours({ target }, root)).toBe(true);
    }
  });

  it("not the host's own controls outside the root", () => {
    const root = element('div');
    const host = element('input');
    const bar = element('nav');
    const link = element('a', bar);
    for (const target of [host, bar, link]) expect(ours({ target }, root)).toBe(false);
  });
});
