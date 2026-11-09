// The settings saver (docs/upload/DESIGN.md U-14.2, U-8.3, U-12.3; ACCEPTANCE 2.3 U6): 800 ms debounce, one request in
// flight, If-Match on the revision, a 412 met by applying this tab's changes again on the saved settings, a 413 met with
// "too many items set aside at once" (the changes dropped), 422 issues shown (the changes kept), layersReviewed carried
// by the next save or alone; and putSettings against the mock API (the If-Match header, 412 with the saved settings).
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import '@/api/client';
import { ApiError } from '@/api/client';
import type { BuildDetail, BuildSettings } from '@/upload/contracts';
import { createSettingsSaver, putSettings, SETTINGS_DEBOUNCE_MS, TOO_MANY_SET_ASIDE, type SettingsChange } from '@/upload/settingsSaver';
import { setRoles } from '@/build/settingsEdit';
import { createMockApi } from '../mock-api/core';
import { mockFetch } from '../mock-api/fetch';
import { FIXTURES_DIR } from '../mock-api/fixtures';

const BANK = JSON.parse(readFileSync(path.join(FIXTURES_DIR, 'upload', 'settings', 'bank.json'), 'utf8')) as BuildSettings;
const detailOf = (settings: BuildSettings, revision: number) => ({ settings, settingsRevision: revision }) as unknown as BuildDetail;

interface Put { settings: BuildSettings; revision: number; reviewed: boolean; resolve(d: BuildDetail): void; reject(e: unknown): void }

function harness(base: BuildSettings = BANK, revision = 1) {
  const puts: Put[] = [];
  const saved: BuildDetail[] = [];
  const saver = createSettingsSaver({
    base: { settings: base, revision },
    put: (settings, rev, reviewed) => new Promise<BuildDetail>((resolve, reject) => puts.push({ settings, revision: rev, reviewed, resolve, reject })),
    onSaved: d => saved.push(d),
  });
  return { saver, puts, saved };
}
const role = (name: string, r: BuildSettings['layers'][string]): SettingsChange => setRoles([name], r);

beforeEach(() => { vi.useFakeTimers(); });
afterEach(() => { vi.useRealTimers(); vi.unstubAllGlobals(); });

describe('createSettingsSaver', () => {
  it('waits 800 ms of quiet, then sends one PUT with the changes on the saved revision', async () => {
    expect(SETTINGS_DEBOUNCE_MS).toBe(800);
    const { saver, puts } = harness();
    saver.change(role('A-WALL', 'glass'));
    expect(saver.state.settings.layers['A-WALL']).toBe('glass');     // on screen at once
    expect(saver.state.status).toBe('pending');
    await vi.advanceTimersByTimeAsync(500);
    saver.change(role('S-COLS', 'wall'));
    await vi.advanceTimersByTimeAsync(799);
    expect(puts.length).toBe(0);
    await vi.advanceTimersByTimeAsync(1);
    expect(puts.length).toBe(1);
    expect(puts[0]!.revision).toBe(1);
    expect(puts[0]!.settings.layers['A-WALL']).toBe('glass');
    expect(puts[0]!.settings.layers['S-COLS']).toBe('wall');
    expect(saver.state.status).toBe('saving');
  });

  it('one request at a time: a change made during a save goes after it, on the revision the API answered', async () => {
    const { saver, puts, saved } = harness();
    saver.change(role('A-WALL', 'glass'));
    await vi.advanceTimersByTimeAsync(800);
    saver.change(role('A-DOOR', 'other'));
    await vi.advanceTimersByTimeAsync(2000);
    expect(puts.length).toBe(1);                                     // still in flight
    puts[0]!.resolve(detailOf(puts[0]!.settings, 2));
    await vi.advanceTimersByTimeAsync(0);
    expect(saved.length).toBe(1);
    await vi.advanceTimersByTimeAsync(800);
    expect(puts.length).toBe(2);
    expect(puts[1]!.revision).toBe(2);
    expect(puts[1]!.settings.layers['A-WALL']).toBe('glass');
    expect(puts[1]!.settings.layers['A-DOOR']).toBe('other');
    puts[1]!.resolve(detailOf(puts[1]!.settings, 3));
    await vi.advanceTimersByTimeAsync(0);
    expect(saver.state.status).toBe('saved');
    expect(saver.state.revision).toBe(3);
  });

  it('412: takes the saved settings and revision from the answer, applies this tab\'s change on top, sends again at once', async () => {
    const { saver, puts } = harness();
    saver.change(role('A-WALL', 'glass'));
    await vi.advanceTimersByTimeAsync(800);
    const elsewhere = { ...BANK, layers: { ...BANK.layers, 'I-FURN': 'ignore' as const } };
    puts[0]!.reject(new ApiError(412, 'revision_conflict', 'changed elsewhere', { revision: 5, settings: elsewhere }));
    await vi.advanceTimersByTimeAsync(0);
    expect(puts.length).toBe(2);
    expect(puts[1]!.revision).toBe(5);
    expect(puts[1]!.settings.layers['I-FURN']).toBe('ignore');       // the other tab's change kept
    expect(puts[1]!.settings.layers['A-WALL']).toBe('glass');        // and this tab's applied again
  });

  it('413: "too many items set aside at once: set aside whole blocks instead", the change dropped', async () => {
    const { saver, puts } = harness();
    saver.change(role('A-WALL', 'glass'));
    await vi.advanceTimersByTimeAsync(800);
    puts[0]!.reject(new ApiError(413, 'body_too_large', 'The body is larger than 8 MiB.'));
    await vi.advanceTimersByTimeAsync(0);
    expect(TOO_MANY_SET_ASIDE).toBe('too many items set aside at once: set aside whole blocks instead');
    expect(saver.state.status).toBe('error');
    expect(saver.state.error).toBe(TOO_MANY_SET_ASIDE);
    expect(saver.state.settings.layers['A-WALL']).toBe('wall');      // back to what is saved
  });

  it('422 invalid_settings: the issues shown, the change kept on screen and sent with the next one', async () => {
    const { saver, puts } = harness();
    saver.change(role('A-WALL', 'glass'));
    await vi.advanceTimersByTimeAsync(800);
    puts[0]!.reject(new ApiError(422, 'invalid_settings', 'The settings cannot be used as they are.', { issues: [{ path: 'floors/1/level', message: 'levels must increase' }] }));
    await vi.advanceTimersByTimeAsync(0);
    expect(saver.state.status).toBe('error');
    expect(saver.state.issues).toEqual([{ path: 'floors/1/level', message: 'levels must increase' }]);
    expect(saver.state.settings.layers['A-WALL']).toBe('glass');
    saver.change(role('S-COLS', 'wall'));
    await vi.advanceTimersByTimeAsync(800);
    expect(puts.length).toBe(2);
    expect(puts[1]!.settings.layers['A-WALL']).toBe('glass');
  });

  it('the API not answering: the reason, and Retry sends the same changes', async () => {
    const { saver, puts } = harness();
    saver.change(role('A-WALL', 'glass'));
    await vi.advanceTimersByTimeAsync(800);
    puts[0]!.reject(new ApiError(0, 'network_error', 'the API did not answer (is it running?)'));
    await vi.advanceTimersByTimeAsync(0);
    expect(saver.state.error).toBe('the API did not answer (is it running?)');
    saver.retry();
    expect(puts.length).toBe(2);
    expect(puts[1]!.settings.layers['A-WALL']).toBe('glass');
  });

  it('layersReviewed rides on the next save; markReviewed sends it with no change; it goes once', async () => {
    const a = harness();
    a.saver.change(role('A-WALL', 'glass'), { layersReviewed: true });
    expect(a.saver.state.reviewPending).toBe(true);
    await vi.advanceTimersByTimeAsync(800);
    expect(a.puts[0]!.reviewed).toBe(true);
    a.puts[0]!.resolve(detailOf(a.puts[0]!.settings, 2));
    await vi.advanceTimersByTimeAsync(0);
    expect(a.saver.state.reviewPending).toBe(false);
    a.saver.change(role('S-COLS', 'wall'));
    await vi.advanceTimersByTimeAsync(800);
    expect(a.puts[1]!.reviewed).toBe(false);

    const b = harness();
    b.saver.markReviewed();
    b.saver.markReviewed();
    await vi.advanceTimersByTimeAsync(800);
    expect(b.puts.length).toBe(1);
    expect(b.puts[0]!.reviewed).toBe(true);
    expect(b.puts[0]!.settings).toEqual(BANK);                         // an otherwise unchanged save
  });

  it('rebase: settings saved elsewhere become the base, this tab\'s waiting change stays on top', async () => {
    const { saver, puts } = harness();
    saver.change(role('A-WALL', 'glass'));
    saver.rebase({ ...BANK, layers: { ...BANK.layers, 'Q-CASE': 'ignore' } }, 4);
    expect(saver.state.revision).toBe(4);
    expect(saver.state.settings.layers['Q-CASE']).toBe('ignore');
    expect(saver.state.settings.layers['A-WALL']).toBe('glass');
    saver.rebase(BANK, 3);                                            // older: ignored
    expect(saver.state.revision).toBe(4);
    await vi.advanceTimersByTimeAsync(800);
    expect(puts[0]!.revision).toBe(4);
  });

  it('close sends a change still waiting', async () => {
    const { saver, puts } = harness();
    saver.change(role('A-WALL', 'glass'));
    saver.close();
    expect(puts.length).toBe(1);
  });
});

describe('putSettings against the mock API', () => {
  it('sends If-Match: "<revision>" and layersReviewed; a stale revision gets 412 with the saved settings', async () => {
    vi.useRealTimers();
    const mock = createMockApi();
    vi.stubGlobal('fetch', mockFetch(mock));
    const src = mock.uploads.addSource('bank-sampeng', { name: 'I1201 - LEVEL 1 GENERAL ARRANGEMENT.dwg', bytes: Buffer.from('AC1032 one') });
    const b = mock.uploads.createBuildNow('bank-sampeng', [src.sha1], { finish: true });
    expect(b.revision).toBe(1);
    const next = { ...b.settings, layers: { ...b.settings.layers, 'A-WALL': 'glass' as const } };
    const d = await putSettings('bank-sampeng', b.id, next, 1, true);
    expect(d.settingsRevision).toBe(2);
    expect(d.layersReviewedAt).not.toBeNull();
    const put = mock.requests.filter(r => r.method === 'PUT').at(-1)!;
    expect(put.headers?.['if-match']).toBe('"1"');
    expect(JSON.parse(put.body!)).toMatchObject({ layersReviewed: true });
    const err = await putSettings('bank-sampeng', b.id, next, 1, false).then(() => null, (e: unknown) => e as ApiError);
    expect(err).toBeInstanceOf(ApiError);
    expect(err?.status).toBe(412);
    expect((err?.details as { revision: number }).revision).toBe(2);
  });
});
