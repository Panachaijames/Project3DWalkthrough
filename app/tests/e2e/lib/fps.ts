// Timed checks (DESIGN.md 3, 17.4; WORK_BREAKDOWN 0). Headless Edge draws with SwiftShader at 10 - 20 frames a second;
// a timed check that fails below 12 fps means "re-run it alone", not a defect. Scaffold.
//   timedDescribe('Walk', () => { test('W walks', async ({ page }) => { ... }); });
// tags every test inside with @timed, gives it one retry, and attaches the page's measured frame rate after each test.
import { test, type Page, type TestInfo } from '@playwright/test';

export const SLOW_FPS = 12;

/** Frames per second the page draws now, counted over `ms` with requestAnimationFrame. */
export async function measureFps(page: Page, ms = 1000): Promise<number> {
  return page.evaluate(duration => new Promise<number>(resolve => {
    let frames = 0;
    const t0 = performance.now();
    const step = (t: number) => {
      frames++;
      if (t - t0 >= duration) resolve(Math.round((frames * 1000 / (t - t0)) * 10) / 10);
      else requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  }), ms);
}

/** Measures the frame rate and attaches it to the test (annotation `fps` and an attachment). */
export async function attachFps(page: Page, testInfo: TestInfo, ms = 1000): Promise<number | null> {
  try {
    const fps = await measureFps(page, ms);
    const note = fps < SLOW_FPS ? `${fps} fps (below ${SLOW_FPS}: re-run alone before diagnosing)` : `${fps} fps`;
    testInfo.annotations.push({ type: 'fps', description: note });
    await testInfo.attach('fps', { body: note, contentType: 'text/plain' });
    return fps;
  } catch {
    return null;
  }
}

/** A describe block of timed checks: tag @timed, one retry, the frame rate attached after each test. */
export function timedDescribe(title: string, body: () => void): void {
  test.describe(title, { tag: '@timed' }, () => {
    test.describe.configure({ retries: 1 });
    test.afterEach(async ({ page }, testInfo) => { await attachFps(page, testInfo); });
    body();
  });
}
