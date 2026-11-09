// The New project screen (docs/upload/DESIGN.md U-2 screen 2, U-13.3; ACCEPTANCE 2.3 U6): validation, the id derived from
// the name and editable, the 40-character limit, 409 with the id the API suggests, 422 for a reserved id, the office
// select (an existing office, or a new office by name), and createProject leading to the Upload screen.
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { click, choose, typeInto, waitFor } from '../helpers';
import { createMockApi } from '../mock-api/core';
import { closeAll, openApp, q } from './app';

vi.mock('@walkthrough/viewer', async () => vi.importActual('../fake-viewer'));

beforeEach(() => { document.title = ''; });
afterEach(closeAll);

const posts = (mock: ReturnType<typeof createMockApi>) => mock.requests.filter(r => r.method === 'POST' && r.path === '/api/projects').map(r => JSON.parse(r.body!) as Record<string, unknown>);

describe('New project', () => {
  it('the title; the button on the list leads here', async () => {
    const app = await openApp('/projects');
    const link = await waitFor(() => q('a[data-testid=new-project]'));
    await click(link);
    await waitFor(() => q('[data-testid=new-project-page]'));
    expect(app.router.state.location.pathname).toBe('/projects/new');
    expect(document.title).toBe('New project · Walkthrough');
  });

  it('a name is needed; nothing is sent without one', async () => {
    const app = await openApp('/projects/new');
    await waitFor(() => q('[data-testid=new-project-page]'));
    await click(q('[data-testid=np-create]'));
    expect(q('[data-testid=np-name-error]')?.textContent).toBe('a project needs a name');
    expect(posts(app.mock)).toEqual([]);
  });

  it('the id follows the name (as the API derives it) until it is typed; more than 40 characters is refused before sending', async () => {
    const app = await openApp('/projects/new');
    await waitFor(() => q('[data-testid=np-name]'));
    await typeInto(q('[data-testid=np-name]'), 'Bangkok Bank Re-upload');
    expect((q('[data-testid=np-id]') as HTMLInputElement).value).toBe('bangkok-bank-re-upload');
    await typeInto(q('[data-testid=np-id]'), 'a'.repeat(41));
    expect(q('[data-testid=np-id-error]')?.textContent).toMatch(/at most 40 characters/);
    expect((q('[data-testid=np-create]') as HTMLButtonElement).disabled).toBe(true);
    await typeInto(q('[data-testid=np-id]'), 'a'.repeat(40));
    expect(q('[data-testid=np-id-error]')).toBeNull();
    await typeInto(q('[data-testid=np-name]'), 'Something else');
    expect((q('[data-testid=np-id]') as HTMLInputElement).value).toBe('a'.repeat(40));   // typed: no longer follows
    expect(posts(app.mock)).toEqual([]);
  });

  it('an id taken: 409 with the next free id offered; Use it, Create: the Upload screen of the new project', async () => {
    const mock = createMockApi();
    mock.handle({ method: 'POST', path: '/api/projects', body: JSON.stringify({ name: 'E2E Bank', id: 'e2e-bank' }) });
    const app = await openApp('/projects/new', { mock });
    await waitFor(() => q('[data-testid=np-name]'));
    await typeInto(q('[data-testid=np-name]'), 'E2E Bank');
    await typeInto(q('[data-testid=np-short-name]'), 'Bank');
    await typeInto(q('[data-testid=np-project-no]'), '26-0216');
    await click(q('[data-testid=np-create]'));
    const use = await waitFor(() => q('[data-testid=np-use-suggested]'));
    expect(q('[data-testid=np-error]')?.textContent).toContain('There is already a project e2e-bank.');
    expect(use.textContent).toBe('Use e2e-bank-2');
    await click(use);
    expect((q('[data-testid=np-id]') as HTMLInputElement).value).toBe('e2e-bank-2');
    await click(q('[data-testid=np-create]'));
    await waitFor(() => app.router.state.location.pathname === '/projects/e2e-bank-2/builds/new');
    await waitFor(() => q('[data-testid=upload-page]'));
    expect(posts(mock).at(-1)).toEqual({ name: 'E2E Bank', shortName: 'Bank', projectNo: '26-0216', office: null, newOfficeName: null, id: 'e2e-bank-2' });
  });

  it('a reserved id: the API\'s 422 reason inline', async () => {
    const app = await openApp('/projects/new');
    await waitFor(() => q('[data-testid=np-name]'));
    await typeInto(q('[data-testid=np-name]'), 'Another bank');
    await typeInto(q('[data-testid=np-id]'), 'bank-sampeng');
    await click(q('[data-testid=np-create]'));
    await waitFor(() => q('[data-testid=np-error]'));
    expect(q('[data-testid=np-error]')?.textContent).toContain('The id bank-sampeng is reserved.');
    expect(app.router.state.location.pathname).toBe('/projects/new');
  });

  it('the office select: the known offices + New office... (a name, made by createProject)', async () => {
    const app = await openApp('/projects/new');
    await waitFor(() => q('[data-testid=office-select] option[value=dwp-revit]'));
    const options = [...q('[data-testid=office-select]')!.querySelectorAll('option')].map(o => o.textContent);
    expect(options).toEqual(['No office', 'DWP (Revit)', 'New office...']);
    await choose(q('[data-testid=office-select]'), '__new__');
    const name = await waitFor(() => q('[data-testid=new-office-name]'));
    await typeInto(name, 'E2E Revit');
    await typeInto(q('[data-testid=np-name]'), 'E2E Tower');
    await click(q('[data-testid=np-create]'));
    await waitFor(() => app.router.state.location.pathname === '/projects/e2e-tower/builds/new');
    expect(posts(app.mock).at(-1)).toMatchObject({ office: null, newOfficeName: 'E2E Revit', id: 'e2e-tower' });
    expect(app.mock.uploads.offices().map(o => o.id)).toContain('e2e-revit');
  });

  it('an existing office goes by its id', async () => {
    const app = await openApp('/projects/new');
    await waitFor(() => q('[data-testid=office-select] option[value=dwp-revit]'));
    await choose(q('[data-testid=office-select]'), 'dwp-revit');
    await typeInto(q('[data-testid=np-name]'), 'Office tower');
    await click(q('[data-testid=np-create]'));
    await waitFor(() => app.router.state.location.pathname === '/projects/office-tower/builds/new');
    expect(posts(app.mock).at(-1)).toMatchObject({ office: 'dwp-revit', newOfficeName: null });
  });
});
