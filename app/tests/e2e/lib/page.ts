// Input helpers on a Playwright Page, as viewer-modes/cdp.mjs pageApi (DESIGN.md 17.4; WORK_BREAKDOWN S.9). Scaffold.
// Keys and the mouse go through Playwright (real input events); touch and tap through a CDP session's
// Input.dispatchTouchEvent, exactly as cdp.mjs did (pointerType touch while maxTouchPoints stays 0): Playwright's own
// touchscreen refuses to work without hasTouch, and hasTouch would put the viewer in touch mode (DESIGN.md 17.4).
import type { CDPSession, Page } from '@playwright/test';
import { waitReady } from './target';

export const sleep = (ms: number) => new Promise<void>(r => setTimeout(r, ms));

/** The key codes the prototype tests press (cdp.mjs KEYS); Playwright sends the matching key and text. */
export type KeyCode = 'KeyW' | 'KeyA' | 'KeyS' | 'KeyD' | 'KeyP' | 'KeyC' | 'KeyE' | 'KeyQ' | 'Space' | 'Digit1' | 'Digit2' | 'Digit3'
  | 'Digit4' | 'Escape' | 'PageUp' | 'PageDown' | 'ShiftLeft' | 'ArrowUp' | 'ArrowDown' | 'ArrowLeft' | 'ArrowRight' | 'Enter' | 'Tab';

export interface PageApi {
  page: Page;
  /** Page errors and console errors seen since the last clearLogs(). */
  logs: string[];
  clearLogs(): void;
  keyDown(code: KeyCode): Promise<void>;
  keyUp(code: KeyCode): Promise<void>;
  /** Down, up, then 120 ms. */
  press(code: KeyCode): Promise<void>;
  /** Down, ms, up, then 80 ms. */
  hold(code: KeyCode, ms: number): Promise<void>;
  /** Move, press, release (clickCount), then 150 ms. */
  click(x: number, y: number, clickCount?: number): Promise<void>;
  dblclick(x: number, y: number): Promise<void>;
  /** CDP Input.dispatchTouchEvent; points are [x, y, id?]. */
  touch(type: 'touchStart' | 'touchMove' | 'touchEnd' | 'touchCancel', points: [number, number, number?][]): Promise<void>;
  tap(x: number, y: number): Promise<void>;
  shot(path: string): Promise<void>;
  /** The centre of the first element matching the selector, or null. */
  center(selector: string): Promise<[number, number] | null>;
  clickEl(selector: string): Promise<void>;
  tapEl(selector: string): Promise<void>;
  /** Navigate and wait until the viewer is ready on this target (lib/target.ts waitReady); clears the logs first. */
  goto(url: string): Promise<void>;
}

export async function pageApi(page: Page): Promise<PageApi> {
  let cdp: CDPSession | null = null;
  const session = async () => (cdp ??= await page.context().newCDPSession(page));
  const logs: string[] = [];
  page.on('pageerror', e => logs.push(`[exception] ${e.message}`));
  page.on('console', m => { if (m.type() === 'error' || m.type() === 'warning') logs.push(`[console.${m.type()}] ${m.text()}`); });

  const api: PageApi = {
    page,
    logs,
    clearLogs: () => { logs.length = 0; },
    keyDown: code => page.keyboard.down(code),
    keyUp: code => page.keyboard.up(code),
    press: async code => { await page.keyboard.down(code); await page.keyboard.up(code); await sleep(120); },
    hold: async (code, ms) => { await page.keyboard.down(code); await sleep(ms); await page.keyboard.up(code); await sleep(80); },
    click: async (x, y, clickCount = 1) => {
      await page.mouse.move(x, y);
      await page.mouse.down({ clickCount });
      await page.mouse.up({ clickCount });
      await sleep(150);
    },
    dblclick: async (x, y) => { await api.click(x, y, 1); await api.click(x, y, 2); },
    touch: async (type, points) => {
      const s = await session();
      await s.send('Input.dispatchTouchEvent', { type, touchPoints: points.map(([x, y, id]) => ({ x, y, id: id ?? 0 })) });
    },
    tap: async (x, y) => { await api.touch('touchStart', [[x, y]]); await sleep(60); await api.touch('touchEnd', []); await sleep(200); },
    shot: async path => { await page.screenshot({ path }); },
    center: selector => page.evaluate(s => {
      const e = document.querySelector(s);
      if (!e) return null;
      const r = e.getBoundingClientRect();
      return [r.left + r.width / 2, r.top + r.height / 2] as [number, number];
    }, selector),
    clickEl: async selector => {
      const c = await api.center(selector);
      if (!c) throw new Error(`no element ${selector}`);
      await api.click(c[0], c[1]);
    },
    tapEl: async selector => {
      const c = await api.center(selector);
      if (!c) throw new Error(`no element ${selector}`);
      await api.tap(c[0], c[1]);
    },
    goto: async url => {
      logs.length = 0;
      await page.goto(url);
      await waitReady(page);
    },
  };
  return api;
}
