// The project page's app bar in the upload milestone (docs/upload/DESIGN.md U-2 screen 3, U-14.1): "New version" leads to
// the Upload screen; the Drafts menu appears when the project has open drafts and leads to each.
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { resetFakeViewer } from '../fake-viewer';
import { click, stubWebGL, text, waitFor } from '../helpers';
import { createMockApi } from '../mock-api/core';
import { closeAll, draftOf, openApp, q, qa } from './app';

vi.mock('@walkthrough/viewer', async () => vi.importActual('../fake-viewer'));

let restoreWebGL = () => undefined as void;
beforeEach(() => { resetFakeViewer(); restoreWebGL = stubWebGL(); });
afterEach(async () => { restoreWebGL(); await closeAll(); });

describe('the project page\'s New version and Drafts', () => {
  it('New version leads to the Upload screen; no Drafts menu without an open draft', async () => {
    const app = await openApp('/projects/bank-sampeng/v/2');
    const link = await waitFor(() => q('a[data-testid=new-version]'));
    expect(link.getAttribute('href')).toBe('/projects/bank-sampeng/builds/new');
    await waitFor(() => app.mock.requests.some(r => r.path === '/api/projects/bank-sampeng/builds'));
    expect(q('[data-testid=drafts-menu]')).toBeNull();
    await click(link);
    await waitFor(() => q('[data-testid=upload-page]'));
  });

  it('with open drafts: the Drafts menu lists them (the files\' names, the status) and leads to each', async () => {
    const mock = createMockApi();
    const { build } = draftOf(mock, 'bank-sampeng', ['I1201 - LEVEL 1.dwg', 'I1202 - LEVEL 2.dwg'], { finish: true });
    const saved = draftOf(mock, 'bank-sampeng', ['old.dwg'], { built: true }).build;
    mock.handle({ method: 'POST', path: `/api/projects/bank-sampeng/builds/${saved.id}/save`, body: JSON.stringify({ label: 'v3', carryHeights: false, rememberMapping: false }) });
    const app = await openApp('/projects/bank-sampeng/v/2', { mock });
    const menu = await waitFor(() => q('[data-testid=drafts-menu]'));
    expect(text(menu)).toBe('Drafts (1)');
    await click(menu);
    // radix opens a dropdown on pointerdown; happy-dom's click alone may not: open it as a keyboard user does
    if (!q('[data-testid=drafts-list]')) menu.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true }));
    const items = await waitFor(() => (qa('[data-testid=draft-item]').length ? qa('[data-testid=draft-item]') : null));
    expect(items.map(i => i.dataset.buildId)).toEqual([build.id]);
    expect(text(items[0])).toContain('I1201 - LEVEL 1.dwg, I1202 - LEVEL 2.dwg');
    expect(items[0]!.getAttribute('href')).toBe(`/projects/bank-sampeng/builds/${build.id}`);
    void app;
  });
});
