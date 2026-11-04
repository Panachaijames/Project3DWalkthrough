// @vitest-environment happy-dom
// Scaffold's tests of ui/dom.ts: text only, never HTML; styles through CSSOM.
import { describe, expect, it } from 'vitest';
import { clear, el } from '../../../src/ui/dom';

const HOSTILE = '<img src=x onerror="window.__pwned = 1">';

describe('el', () => {
  it('builds an element with class, data-wt, attributes, title and text', () => {
    const node = el('button', { cls: 'a b', wt: 'camera-btn', attrs: { 'aria-pressed': 'true', 'data-mode': 'walk' }, title: 'Camera', text: 'Camera' });
    expect(node.tagName).toBe('BUTTON');
    expect(node.className).toBe('a b');
    expect(node.getAttribute('data-wt')).toBe('camera-btn');
    expect(node.getAttribute('aria-pressed')).toBe('true');
    expect(node.dataset.mode).toBe('walk');
    expect(node.title).toBe('Camera');
    expect(node.textContent).toBe('Camera');
  });

  it('inserts drawing text as text, in text, title, attributes and string children', () => {
    const node = el('div', { text: HOSTILE, title: HOSTILE, attrs: { 'data-kind': HOSTILE } }, [HOSTILE, el('b', { text: HOSTILE })]);
    expect(node.querySelector('img')).toBeNull();
    expect(node.textContent).toBe(HOSTILE + HOSTILE + HOSTILE);
    expect(node.title).toBe(HOSTILE);
    expect(node.getAttribute('data-kind')).toBe(HOSTILE);
  });

  it('appends node and string children in order and skips null / undefined', () => {
    const node = el('ul', {}, [el('li', { text: 'one' }), null, 'two', undefined, el('li', { text: 'three' })]);
    expect(node.childNodes.length).toBe(3);
    expect(node.textContent).toBe('onetwothree');
  });

  it('sets styles through CSSOM, custom properties included, and never a style attribute string', () => {
    const node = el('div', { style: { width: '12px', display: 'none', '--accent': '#2f6f8f' } as Partial<CSSStyleDeclaration> });
    expect(node.style.width).toBe('12px');
    expect(node.style.display).toBe('none');
    expect(node.style.getPropertyValue('--accent')).toBe('#2f6f8f');
    expect(() => el('div', { attrs: { style: 'color: red' } })).toThrow(/not allowed/);
    expect(() => el('div', { attrs: { onclick: 'alert(1)' } })).toThrow(/not allowed/);
    expect(() => el('div', { attrs: { OnError: 'alert(1)' } })).toThrow(/not allowed/);
  });
});

describe('clear', () => {
  it('removes every child', () => {
    const node = el('div', {}, ['a', el('span', { text: 'b' }), 'c']);
    clear(node);
    expect(node.childNodes.length).toBe(0);
  });
});
