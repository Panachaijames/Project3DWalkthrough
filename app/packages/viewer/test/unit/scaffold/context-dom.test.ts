// @vitest-environment happy-dom
// Scaffold: the shared test context with a DOM (happy-dom): root, hint, error box, slot panel, flags, dispose.
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';
import type { BuiltModel } from '../../../src/contracts';
import { makeTestContext } from '../../harness/context';

const APP = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../../../..');
const model = (name: string) => JSON.parse(readFileSync(path.join(APP, 'fixtures/models', `${name}.model.json`), 'utf8')) as BuiltModel;

describe('makeTestContext (happy-dom)', () => {
  it('puts a root with hint, error box and the slot panel into the container, and takes it out again', () => {
    const container = document.createElement('div');
    document.body.append(container);
    const ctx = makeTestContext({ model: model('bank-v2'), container, stamp: 'c3a9408304a2' });
    expect(ctx.kit.dom).toBe(true);
    const root = container.querySelector('[data-wt=root]')!;
    expect(root.getAttribute('data-model-stamp')).toBe('c3a9408304a2');
    expect(root.querySelector('[data-wt=hint]')).not.toBeNull();
    expect(root.querySelector('canvas')).not.toBeNull();
    const slots = [...root.querySelectorAll('[data-wt=panel] [data-slot]')].map(s => s.getAttribute('data-slot'));
    expect(slots).toEqual(['title', 'intro', 'floors', 'modes', 'shows', 'legend', 'build', 'furniture']);
    ctx.ui.setFlag('camopen', true);
    expect(root.hasAttribute('data-camopen')).toBe(true);
    ctx.reportError(new Error('shown'));
    expect(ctx.ui.errorBox.hidden).toBe(false);
    expect(ctx.ui.errorBox.textContent).toBe('shown');
    ctx.disposer.dispose();
    expect(container.children.length).toBe(0);
    container.remove();
  });

  it('orders the slots of a one-floor model with modes after the ticks', () => {
    const ctx = makeTestContext({ model: model('suite') });
    const slots = [...ctx.panel.el.querySelectorAll('[data-slot]')].map(s => s.getAttribute('data-slot'));
    expect(slots).toEqual(['title', 'intro', 'shows', 'modes', 'legend', 'build', 'furniture']);
    ctx.disposer.dispose();
  });
});
