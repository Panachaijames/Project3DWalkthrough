// The Upload screen (docs/upload/DESIGN.md U-2 screen 4, U-5.3; ACCEPTANCE 2.3 U6): files picked (.dwg / .dxf only), each
// sent in parts with its progress, Retry after a failure, Remove; Continue makes the build with the sources in the order
// picked and opens its Files step; "Use the files of v<n> again"; `?from=<build>` starts the draft from that one.
import { act } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { setUploadOptionsForTests } from '@/pages/UploadPage';
import { click, waitFor } from '../helpers';
import { createMockApi } from '../mock-api/core';
import { closeAll, draftOf, fastClocks, openApp, q, qa } from './app';

vi.mock('@walkthrough/viewer', async () => vi.importActual('../fake-viewer'));

let restoreClocks = () => undefined as void;
beforeEach(() => {
  restoreClocks = fastClocks();
  setUploadOptionsForTests({ sleep: async () => undefined, storage: () => null });
  localStorage.clear();
});
afterEach(async () => { restoreClocks(); setUploadOptionsForTests(null); await closeAll(); });

const dwg = (name: string, size: number) => new File([new Uint8Array([65, 67, 49, 48, 51, 50, ...Array(Math.max(0, size - 6)).fill(1)])], name, { lastModified: 1 });

async function pick(files: File[]) {
  const input = await waitFor(() => q('[data-testid=file-input]') as HTMLInputElement | null);
  await act(async () => {
    Object.defineProperty(input, 'files', { value: files, configurable: true });
    input.dispatchEvent(new Event('change', { bubbles: true }));
  });
}

describe('Upload', () => {
  it('two DWGs in parts with their progress, then Continue: the build with both, in the order picked, on its Files step', async () => {
    const mock = createMockApi();
    mock.uploads.config.partBytes = 100;
    const app = await openApp('/projects/bank-sampeng/builds/new', { mock });
    await waitFor(() => q('[data-testid=upload-page]'));
    expect(document.title).toBe('Bangkok Bank, Sampeng Branch · upload · Walkthrough');
    await pick([dwg('I1201 - LEVEL 1.dwg', 350), dwg('I1202 - LEVEL 2.dwg', 120)]);
    await waitFor(() => qa('[data-testid=upload-row][data-state=done]').length === 2);
    const rows = qa('[data-testid=upload-row]');
    expect(rows.map(r => r.dataset.name)).toEqual(['I1201 - LEVEL 1.dwg', 'I1202 - LEVEL 2.dwg']);
    expect(rows[0]!.querySelector('[data-testid=upload-status]')?.textContent).toBe('Uploaded');
    const parts = mock.requests.filter(r => r.method === 'PUT' && /\/parts\/\d+$/.test(r.path));
    expect(parts.length).toBe(4 + 2);
    const start = q('[data-testid=start-build]') as HTMLButtonElement;
    expect(start.disabled).toBe(false);
    expect(start.textContent).toContain('Continue with 2 files');
    await click(start);
    await waitFor(() => /\/projects\/bank-sampeng\/builds\/\d{8}T\d{6}-[0-9a-f]{6}$/.test(app.router.state.location.pathname));
    expect(app.router.state.location.search).toBe('?step=files');
    const created = JSON.parse(mock.requests.find(r => r.method === 'POST' && r.path === '/api/projects/bank-sampeng/builds')!.body!);
    expect(created.sources).toEqual(mock.uploads.sources('bank-sampeng').map(s => s.sha1));
    expect(created.from).toBeUndefined();
    await waitFor(() => q('[data-testid=files-step]'));
  });

  it('other files are refused by name; a failed upload offers Retry, which sends the rest; Remove takes a row away', async () => {
    const mock = createMockApi();
    mock.uploads.config.partBytes = 100;
    let failures = 1;
    const app = await openApp('/projects/bank-sampeng/builds/new', {
      mock,
      fetch: {
        intercept: (m, p) => {
          if (m === 'PUT' && p.endsWith('/parts/2') && failures > 0) {
            failures--;
            return new Response(JSON.stringify({ error: { code: 'bad_part', message: 'Part 2 went wrong.' } }), { status: 422, headers: { 'content-type': 'application/json' } });
          }
          return undefined;
        },
      },
    });
    await pick([dwg('plan.dwg', 250), new File(['x'], 'notes.txt')]);
    expect(q('[data-testid=upload-refused]')?.textContent).toContain('notes.txt');
    const failed = await waitFor(() => q('[data-testid=upload-row][data-state=failed]'));
    expect(failed.querySelector('[data-testid=upload-error]')?.textContent).toBe('Not uploaded: Part 2 went wrong.');
    expect((q('[data-testid=start-build]') as HTMLButtonElement).disabled).toBe(true);
    await click(failed.querySelector('[data-testid=upload-retry]'));
    await waitFor(() => q('[data-testid=upload-row][data-state=done]'));
    await pick([dwg('second.dwg', 50)]);
    await waitFor(() => qa('[data-testid=upload-row][data-state=done]').length === 2);
    await click(q('[data-testid=upload-row][data-name="second.dwg"] [data-testid=upload-remove]'));
    expect(qa('[data-testid=upload-row]').map(r => r.dataset.name)).toEqual(['plan.dwg']);
    void app;
  });

  it('a project with versions: "Use the files of v2 again" asks for a build of that version\'s files (the API says why it cannot)', async () => {
    const app = await openApp('/projects/bank-sampeng/builds/new');
    const reuse = await waitFor(() => q('[data-testid=reuse-files]'));
    expect(reuse.textContent).toBe('Use the files of v2 again');
    await click(reuse);
    await waitFor(() => q('[data-testid=start-error]'));
    const body = JSON.parse(app.mock.requests.find(r => r.method === 'POST' && r.path.endsWith('/builds'))!.body!);
    expect(body).toEqual({ sources: null, from: { kind: 'version', version: 2 } });
    expect(q('[data-testid=start-error]')?.textContent).toContain('A build needs at least one source file.');
  });

  it('?from=<build> (Start again with other files): the new draft starts from that draft\'s settings; open drafts are listed', async () => {
    const mock = createMockApi();
    const { build } = draftOf(mock, 'bank-sampeng', ['old.dwg'], { finish: true, reviewed: true });
    const app = await openApp(`/projects/bank-sampeng/builds/new?from=${build.id}`, { mock });
    await waitFor(() => q('[data-testid=open-drafts]'));
    expect(q('[data-testid=reuse-files]')).toBeNull();
    await pick([dwg('new.dwg', 30)]);
    await waitFor(() => q('[data-testid=upload-row][data-state=done]'));
    await click(q('[data-testid=start-build]'));
    await waitFor(() => app.router.state.location.pathname !== '/projects/bank-sampeng/builds/new');
    const body = JSON.parse(mock.requests.filter(r => r.method === 'POST' && r.path.endsWith('/builds')).at(-1)!.body!);
    expect(body.from).toEqual({ kind: 'build', build: build.id });
  });
});
