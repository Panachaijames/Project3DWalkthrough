// Deleting a project, a version and a draft in the staff app (the owner's request of 12 Nov 2026;
// docs/contract-issues/DEL.md), over the mock API: the buttons and where they sit, the confirm texts, Cancel sends
// nothing, a delete that goes through moves on (the list, the latest remaining version), and a refusal shows its reason.
import { act } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { DRAFT_DELETE_TEXT, ONLY_VERSION_TEXT, projectDeleteText, versionDeleteText } from '@/components/DeleteActions';
import { resetFakeViewer } from './fake-viewer';
import { click, settle, stubWebGL, text, waitFor } from './helpers';
import { createMockApi, type MockApi } from './mock-api/core';
import { closeAll, draftOf, openApp, q, qa } from './build/app';

vi.mock('@walkthrough/viewer', async () => vi.importActual('./fake-viewer'));

const BANK = 'Bangkok Bank, Sampeng Branch';
let restoreWebGL = () => undefined as void;
let answer = true;
const asked: string[] = [];
const originalConfirm = window.confirm;
beforeEach(() => {
  resetFakeViewer();
  restoreWebGL = stubWebGL();
  answer = true;
  asked.length = 0;
  window.confirm = (message?: string) => { asked.push(String(message)); return answer; };
});
afterEach(async () => {
  restoreWebGL();
  window.confirm = originalConfirm;
  await closeAll();
});

const deletes = (mock: MockApi) => mock.requests.filter(r => r.method === 'DELETE').map(r => r.path);
const card = (id: string) => q(`[data-testid=project-card][data-project-id="${id}"]`);

/** Opens a radix dropdown as a keyboard user does (happy-dom's click alone may not). */
async function openMenu(trigger: HTMLElement | null, content: string): Promise<HTMLElement> {
  await click(trigger);
  if (!q(`[data-testid=${content}]`)) {
    await act(async () => { trigger!.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true })); });
  }
  return waitFor(() => q(`[data-testid=${content}]`));
}

describe('the confirm texts', () => {
  it('name what is lost and say it cannot be undone', () => {
    expect(projectDeleteText('TEST_BANK', 2, 1)).toBe('Delete TEST_BANK? Its 2 versions, 1 draft and uploaded drawings are removed from this computer. This cannot be undone.');
    expect(projectDeleteText('TEST_BANK', 1, 0)).toBe('Delete TEST_BANK? Its 1 version and uploaded drawings are removed from this computer. This cannot be undone.');
    expect(projectDeleteText('New', 0, 3)).toBe('Delete New? Its 3 drafts and uploaded drawings are removed from this computer. This cannot be undone.');
    expect(projectDeleteText('New', 0, 0)).toBe('Delete New? Its uploaded drawings are removed from this computer. This cannot be undone.');
    expect(projectDeleteText('X', 2, null)).toBe('Delete X? Its 2 versions, drafts and uploaded drawings are removed from this computer. This cannot be undone.');
    expect(versionDeleteText('TEST_BANK', 1)).toBe('Delete version 1 of TEST_BANK? This cannot be undone. Version numbers are not reused.');
    expect(DRAFT_DELETE_TEXT).toBe('Delete this draft? Its uploaded files stay with the project.');
  });
});

describe('the project list', () => {
  it('a Delete on each card, beside (not inside) its link; Cancel sends nothing; OK deletes and the card goes', async () => {
    const mock = createMockApi();
    draftOf(mock, 'bank-sampeng', ['I1201.dwg'], { finish: true });
    await openApp('/projects', { mock });
    await waitFor(() => qa('[data-testid=project-card]').length === 4);
    for (const c of qa('[data-testid=project-card]')) {
      const del = c.querySelector('[data-testid=card-delete]');
      expect(del, c.dataset.projectId).not.toBeNull();
      expect(del!.closest('a')).toBeNull();
    }
    const button = card('bank-sampeng')!.querySelector<HTMLElement>('[data-testid=card-delete]')!;
    expect(button.getAttribute('aria-label')).toBe(`Delete ${BANK}`);
    answer = false;
    await click(button);
    await waitFor(() => asked.length === 1);
    expect(asked[0]).toBe(`Delete ${BANK}? Its 2 versions, 1 draft and uploaded drawings are removed from this computer. This cannot be undone.`);
    await settle(20);
    expect(deletes(mock)).toEqual([]);
    expect(card('bank-sampeng')).not.toBeNull();
    answer = true;
    await click(button);
    await waitFor(() => !card('bank-sampeng'));
    expect(deletes(mock)).toEqual(['/api/projects/bank-sampeng']);
    expect(qa('[data-testid=project-card]').length).toBe(3);
    expect(mock.project('bank-sampeng')).toBeNull();
  });

  it('a refusal shows its reason on the card, and the card stays', async () => {
    const mock = createMockApi();
    draftOf(mock, 'bank-sampeng', ['I1201.dwg']);                    // its reading is queued: the project is busy
    await openApp('/projects', { mock });
    const button = await waitFor(() => card('bank-sampeng')?.querySelector<HTMLElement>('[data-testid=card-delete]'));
    await click(button);
    const err = await waitFor(() => card('bank-sampeng')?.querySelector('[data-testid=card-delete-error]'));
    expect(text(err)).toBe(`${BANK} was not deleted: Wait for the build to finish (or cancel it), then delete the project.`);
    expect(qa('[data-testid=project-card]').length).toBe(4);
  });
});

describe('the project page', () => {
  it('the "..." menu sits beside the version picker: Delete this version, then the latest remaining version opens', async () => {
    const app = await openApp('/projects/bank-sampeng/v/2');
    const trigger = await waitFor(() => q('[data-testid=project-actions]'));
    const bar = [...q('[data-testid=app-bar]')!.querySelectorAll('[data-testid]')].map(e => e.getAttribute('data-testid'));
    expect(bar.indexOf('project-actions')).toBe(bar.indexOf('version-picker') + 1);
    await openMenu(trigger, 'project-actions-list');
    const item = q('[data-testid=delete-version]')!;
    expect(text(item)).toBe('Delete this version (v2)');
    expect(item.hasAttribute('data-disabled')).toBe(false);
    answer = false;
    await click(item);
    await waitFor(() => asked.length === 1);
    expect(asked[0]).toBe(`Delete version 2 of ${BANK}? This cannot be undone. Version numbers are not reused.`);
    await settle(20);
    expect(deletes(app.mock)).toEqual([]);
    answer = true;
    await openMenu(q('[data-testid=project-actions]'), 'project-actions-list');
    await click(q('[data-testid=delete-version]'));
    await waitFor(() => app.router.state.location.pathname === '/projects/bank-sampeng/v/1');
    expect(deletes(app.mock)).toEqual(['/api/projects/bank-sampeng/versions/2']);
    await waitFor(() => q('[data-testid=project-page]')?.getAttribute('data-version') === '1');
    expect(app.mock.project('bank-sampeng')!.versions.map(v => v.version)).toEqual([1]);
    // the history entry of the deleted version was replaced
    expect(app.router.state.historyAction).toBe('REPLACE');
    // now the only version: the item is disabled and says to delete the project instead
    await openMenu(q('[data-testid=project-actions]'), 'project-actions-list');
    await waitFor(() => q('[data-testid=delete-version]')?.hasAttribute('data-disabled'));
    expect(text(q('[data-testid=delete-version-note]'))).toBe(ONLY_VERSION_TEXT);
    expect(text(q('[data-testid=delete-version]'))).toContain('Delete this version (v1)');
  });

  it('the only version cannot be deleted from the menu (nothing asked, nothing sent)', async () => {
    const app = await openApp('/projects/hotel-lobby/v/1');
    await openMenu(await waitFor(() => q('[data-testid=project-actions]')), 'project-actions-list');
    const item = q('[data-testid=delete-version]')!;
    expect(item.hasAttribute('data-disabled')).toBe(true);
    expect(text(q('[data-testid=delete-version-note]'))).toBe(ONLY_VERSION_TEXT);
    await click(item);
    await settle(20);
    expect(asked).toEqual([]);
    expect(deletes(app.mock)).toEqual([]);
  });

  it('Delete project: asks with the counts, deletes, and goes to the project list', async () => {
    const mock = createMockApi();
    draftOf(mock, 'bank-sampeng', ['a.dwg'], { finish: true });
    draftOf(mock, 'bank-sampeng', ['b.dwg'], { finish: true });
    const app = await openApp('/projects/bank-sampeng/v/1', { mock });
    await openMenu(await waitFor(() => q('[data-testid=project-actions]')), 'project-actions-list');
    expect(text(q('[data-testid=delete-project]'))).toBe('Delete project');
    await click(q('[data-testid=delete-project]'));
    await waitFor(() => app.router.state.location.pathname === '/projects');
    expect(asked).toEqual([`Delete ${BANK}? Its 2 versions, 2 drafts and uploaded drawings are removed from this computer. This cannot be undone.`]);
    expect(deletes(mock)).toEqual(['/api/projects/bank-sampeng']);
    await waitFor(() => qa('[data-testid=project-card]').length === 3);
    expect(card('bank-sampeng')).toBeNull();
    expect(app.router.state.historyAction).toBe('REPLACE');
  });

  it('a refusal shows the reason and the page stays', async () => {
    const mock = createMockApi();
    draftOf(mock, 'bank-sampeng', ['I1201.dwg']);                    // queued: busy
    const app = await openApp('/projects/bank-sampeng/v/2', { mock });
    await openMenu(await waitFor(() => q('[data-testid=project-actions]')), 'project-actions-list');
    await click(q('[data-testid=delete-version]'));
    const reason = await waitFor(() => q('[data-testid=delete-error-reason]'));
    expect(text(reason)).toBe('Version 2 was not deleted: Wait for the build to finish (or cancel it), then delete the version.');
    expect(app.router.state.location.pathname).toBe('/projects/bank-sampeng/v/2');
    await click(q('[data-testid=delete-error-close]'));
    expect(q('[data-testid=delete-error]')).toBeNull();
    // the project too
    await openMenu(q('[data-testid=project-actions]'), 'project-actions-list');
    await click(q('[data-testid=delete-project]'));
    await waitFor(() => text(q('[data-testid=delete-error-reason]')) === `${BANK} was not deleted: Wait for the build to finish (or cancel it), then delete the project.`);
    expect(app.router.state.location.pathname).toBe('/projects/bank-sampeng/v/2');
    expect(mock.project('bank-sampeng')!.versionCount).toBe(2);
  });

  it('the Drafts menu has a Delete per draft: the same confirm; Cancel sends nothing; OK deletes it', async () => {
    const mock = createMockApi();
    const one = draftOf(mock, 'bank-sampeng', ['a.dwg'], { finish: true }).build;
    const two = draftOf(mock, 'bank-sampeng', ['b.dwg'], { finish: true }).build;
    await openApp('/projects/bank-sampeng/v/2', { mock });
    const menu = await waitFor(() => q('[data-testid=drafts-menu]'));
    expect(text(menu)).toBe('Drafts (2)');
    await openMenu(menu, 'drafts-list');
    const del = (id: string) => q(`[data-testid=draft-item-delete][data-build-id="${id}"]`);
    expect(del(one.id)).not.toBeNull();
    expect(del(one.id)!.closest('a')).toBeNull();
    answer = false;
    await click(del(one.id));
    expect(asked).toEqual([DRAFT_DELETE_TEXT]);
    await settle(20);
    expect(deletes(mock)).toEqual([]);
    answer = true;
    await click(del(one.id));
    await waitFor(() => text(q('[data-testid=drafts-menu]')) === 'Drafts (1)');
    expect(deletes(mock)).toEqual([`/api/projects/bank-sampeng/builds/${one.id}`]);
    expect(mock.uploads.build('bank-sampeng', one.id)).toBeNull();
    expect(mock.uploads.build('bank-sampeng', two.id)).not.toBeNull();
  });

  it('a draft whose run is going cannot be deleted from the menu; a refusal shows its reason in the menu', async () => {
    const mock = createMockApi();
    const going = draftOf(mock, 'bank-sampeng', ['a.dwg']).build;     // its reading is queued
    const done = draftOf(mock, 'bank-sampeng', ['b.dwg'], { finish: true }).build;
    await openApp('/projects/bank-sampeng/v/2', {
      mock,
      fetch: {
        intercept: (m, p) => (m === 'DELETE' && p.endsWith(done.id)
          ? new Response(JSON.stringify({ error: { code: 'store_error', message: 'the disk is full' } }), { status: 500, headers: { 'content-type': 'application/json' } })
          : undefined),
      },
    });
    await openMenu(await waitFor(() => q('[data-testid=drafts-menu]')), 'drafts-list');
    expect(q(`[data-testid=draft-item-delete][data-build-id="${going.id}"]`)!.hasAttribute('data-disabled')).toBe(true);
    await click(q(`[data-testid=draft-item-delete][data-build-id="${done.id}"]`));
    const err = await waitFor(() => q('[data-testid=draft-delete-error]'));
    expect(text(err)).toBe('The draft was not deleted: the disk is full');
    expect(mock.uploads.build('bank-sampeng', done.id)).not.toBeNull();
  });
});

describe('a project with no version yet', () => {
  it('has a quiet Delete project that goes back to the list', async () => {
    const mock = createMockApi();
    mock.handle({ method: 'POST', path: '/api/projects', body: JSON.stringify({ name: 'Half made', shortName: 'Half', id: 'half-made' }) });
    expect(mock.project('half-made')).not.toBeNull();
    const app = await openApp('/projects/half-made', { mock });
    const button = await waitFor(() => q('[data-testid=no-versions] [data-testid=delete-project]'));
    await click(button);
    await waitFor(() => app.router.state.location.pathname === '/projects');
    expect(asked).toEqual(['Delete Half made? Its uploaded drawings are removed from this computer. This cannot be undone.']);
    expect(deletes(mock)).toEqual(['/api/projects/half-made']);
    expect(mock.project('half-made')).toBeNull();
  });
});

describe('the mock API (as the API)', () => {
  it('never gives a deleted version\'s number again, and answers 404 / 409 as the API does', () => {
    const mock = createMockApi();
    const req = (method: string, path: string, body?: unknown) => mock.handle({ method, path, body: body === undefined ? null : JSON.stringify(body) });
    expect(req('DELETE', '/api/projects/hotel-lobby/versions/1').status).toBe(409);
    expect(req('DELETE', '/api/projects/no-such/versions/1').status).toBe(404);
    expect(req('DELETE', '/api/projects/bank-sampeng/versions/9').status).toBe(404);
    expect(req('DELETE', '/api/projects/bank-sampeng/versions/2').status).toBe(204);
    expect(JSON.parse(req('GET', '/api/projects/bank-sampeng/versions/2').body.toString()).error.message).toBe("version 2 of 'bank-sampeng' was deleted");
    expect(mock.project('bank-sampeng')!.latestVersion).toBe(1);
    const b = draftOf(mock, 'bank-sampeng', ['x.dwg'], { built: true }).build;
    const saved = req('POST', `/api/projects/bank-sampeng/builds/${b.id}/save`, { label: 'v3', carryHeights: false, rememberMapping: false });
    expect(saved.status).toBe(201);
    expect(JSON.parse(saved.body.toString()).version).toBe(3);                // not 2 again
    expect(req('DELETE', '/api/projects/bank-sampeng').status).toBe(204);
    expect(req('GET', '/api/projects/bank-sampeng').status).toBe(404);
  });
});
