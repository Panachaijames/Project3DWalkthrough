// The Downloads menu (DESIGN.md 15.3, 15.5): the three items word for word, in order, each a plain <a href download> to
// the version detail's URL, disabled when the version has none; the CSV and the offline file (made with the saved heights)
// wait, disabled, while a heights save is going; opening the menu calls onOpen (the page sends a waiting save at once).
import { act } from 'react';
import { MemoryRouter } from 'react-router';
import { describe, expect, it, vi } from 'vitest';
import { DownloadsMenu, type DownloadsMenuProps } from '@/components/DownloadsMenu';
import { API_DOWN_TITLE, HEIGHTS_PENDING_TITLE, heightsNotSavedTitle } from '@/lib/format';
import { render, text, waitFor } from './helpers';
import { createMockApi } from './mock-api/core';

vi.mock('@walkthrough/viewer', async () => vi.importActual('./fake-viewer'));

const mock = createMockApi();
const item = (key: string) => document.body.querySelector<HTMLElement>(`[data-testid=downloads-list] [data-download=${key}]`);

async function openMenu(props: DownloadsMenuProps) {
  // the API check answers 'yes' unless a test says otherwise (no request in these tests)
  const ui = (p: DownloadsMenuProps) => <MemoryRouter><DownloadsMenu probe={async () => true} {...p} /></MemoryRouter>;
  const v = await render(ui(props), { strict: false });
  const trigger = v.host.querySelector<HTMLButtonElement>('[data-testid=downloads-menu]')!;
  expect(text(trigger)).toBe('Downloads');
  await act(async () => { trigger.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true, cancelable: true })); });
  await waitFor(() => item('offlineHtml'));
  return { v, rerender: (p: DownloadsMenuProps) => v.rerender(ui(p)) };
}

describe('DownloadsMenu', () => {
  it('three items in order, word for word, linking to the version detail URLs with their file names', async () => {
    const detail = mock.version('bank-sampeng', 2)!;
    const onOpen = vi.fn();
    const m = await openMenu({ downloads: detail.downloads, onOpen });
    expect(onOpen).toHaveBeenCalledTimes(1);
    const items = [...document.body.querySelectorAll('[data-testid=downloads-list] [data-download]')];
    expect(items.map(e => [e.getAttribute('data-download'), text(e)])).toEqual([
      ['maxScript', '3ds Max script (.ms)'],
      ['furnitureCsv', 'Furniture list (CSV)'],
      ['offlineHtml', 'Offline viewer (HTML)'],
    ]);
    for (const [key, info] of [
      ['maxScript', detail.downloads.maxScript!],
      ['furnitureCsv', detail.downloads.furnitureCsv!],
      ['offlineHtml', detail.downloads.offlineHtml],
    ] as const) {
      const a = item(key)!;
      expect(a.tagName, key).toBe('A');
      expect(a.getAttribute('href'), key).toBe(info.url);
      expect(a.getAttribute('download'), key).toBe(info.fileName);
      expect(a.hasAttribute('data-disabled'), key).toBe(false);
    }
    expect(item('furnitureCsv')!.getAttribute('download')).toBe('BangkokBank-Sampeng_furniture_list.csv');
    expect(item('offlineHtml')!.getAttribute('download')).toBe('bank-sampeng-v2.html');
    await m.v.unmount();
  });

  it('a version without furniture: the CSV is disabled and has no link', async () => {
    const detail = mock.version('bank-sampeng', 1)!;
    expect(detail.downloads.furnitureCsv).toBeNull();
    const m = await openMenu({ downloads: detail.downloads });
    const csv = item('furnitureCsv')!;
    expect(csv.tagName).not.toBe('A');
    expect(csv.getAttribute('href')).toBeNull();
    expect(csv.getAttribute('aria-disabled')).toBe('true');
    expect(csv.hasAttribute('data-waiting')).toBe(false);
    expect(item('maxScript')!.getAttribute('href')).toBe(detail.downloads.maxScript!.url);
    await m.v.unmount();
  });

  it('the house has no Max script: that item is disabled', async () => {
    const detail = mock.version('sukhumvit-house', 1)!;
    const m = await openMenu({ downloads: detail.downloads });
    expect(item('maxScript')!.getAttribute('aria-disabled')).toBe('true');
    expect(item('maxScript')!.getAttribute('href')).toBeNull();
    expect(item('furnitureCsv')!.getAttribute('href')).toBe(detail.downloads.furnitureCsv!.url);
    await m.v.unmount();
  });

  it('while heights are saving the CSV and the offline file wait (disabled); the Max script does not', async () => {
    const detail = mock.version('hotel-lobby', 1)!;
    const m = await openMenu({ downloads: detail.downloads, heights: { status: 'saving', reason: null } });
    for (const key of ['furnitureCsv', 'offlineHtml']) {
      const e = item(key)!;
      expect(e.getAttribute('href'), key).toBeNull();
      expect(e.getAttribute('aria-disabled'), key).toBe('true');
      expect(e.hasAttribute('data-waiting'), key).toBe(true);
      expect(e.getAttribute('title'), key).toBe(HEIGHTS_PENDING_TITLE);
    }
    expect(item('maxScript')!.getAttribute('href')).toBe(detail.downloads.maxScript!.url);
    // saved: the links come back while the menu stays open
    await m.rerender({ downloads: detail.downloads, heights: { status: 'saved', reason: null } });
    expect(item('furnitureCsv')!.getAttribute('href')).toBe(detail.downloads.furnitureCsv!.url);
    expect(item('offlineHtml')!.getAttribute('href')).toBe(detail.downloads.offlineHtml.url);
    expect(item('offlineHtml')!.hasAttribute('data-waiting')).toBe(false);
    await m.v.unmount();
  });
  it('while the heights on screen are not saved (a failed save), the CSV and the offline file say so, disabled (fix step)', async () => {
    const detail = mock.version('hotel-lobby', 1)!;
    const m = await openMenu({ downloads: detail.downloads, heights: { status: 'error', reason: 'the store is busy' } });
    for (const key of ['furnitureCsv', 'offlineHtml']) {
      const e = item(key)!;
      expect(e.getAttribute('href'), key).toBeNull();
      expect(e.getAttribute('aria-disabled'), key).toBe('true');
      expect(e.getAttribute('title'), key).toBe(heightsNotSavedTitle('the store is busy'));
    }
    expect(item('maxScript')!.getAttribute('href')).toBe(detail.downloads.maxScript!.url);
    await m.v.unmount();
  });

  it('when the API does not answer, every item is disabled with that reason (fix step)', async () => {
    const detail = mock.version('bank-sampeng', 2)!;
    const m = await openMenu({ downloads: detail.downloads, probe: async () => false });
    await waitFor(() => item('maxScript')!.getAttribute('aria-disabled') === 'true');
    for (const key of ['maxScript', 'furnitureCsv', 'offlineHtml']) {
      expect(item(key)!.getAttribute('href'), key).toBeNull();
      expect(item(key)!.getAttribute('title'), key).toBe(API_DOWN_TITLE);
    }
    await m.v.unmount();
    const s2 = await openMenu({ downloads: detail.downloads, heights: { status: 'error', reason: 'x', unreachable: true } });
    expect(item('maxScript')!.getAttribute('title')).toBe(API_DOWN_TITLE);   // a save that found no API says the same
    await s2.v.unmount();
  });
});
