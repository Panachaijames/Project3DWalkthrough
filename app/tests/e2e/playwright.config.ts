// Playwright (DESIGN.md 3, 17.4; WORK_BREAKDOWN S.9). Frozen after the scaffold.
//
// Environment (every builder sets the first three to its own row of DESIGN.md 3):
//   WT_WEB_PORT  web dev server or harness server (default 5711)      WT_API_PORT  API (default 8711)
//   WT_TMP       everything a run writes (default %TEMP%\wt-e2e)       E2E_TARGET   app (default) | prototype
//   WT_SERVE     servers to start, comma list of api, web, harness. Default: `harness` with --project harness, none
//                with E2E_TARGET=prototype, else `api,web`. (A builder testing web pages against a mock API sets `web`.)
// Projects: e2e (tests/e2e/*.spec.ts), harness (packages/viewer/test/harness/**/*.spec.ts), scaffold (lib/smoke-*.spec.ts).
// Installed Edge (channel msedge), never a downloaded browser; never hasTouch / isMobile (touch goes through CDP:
// lib/page.ts). One worker. A check tagged @timed retries once (lib/fps.ts timedDescribe); nothing else retries.
// globalSetup takes the machine-wide Edge lock and globalTeardown releases it. Playwright starts the web servers BEFORE
// globalSetup, so the API's server command makes the temp data copy itself (DESIGN.md 18.42).
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { defineConfig, type PlaywrightTestConfig } from '@playwright/test';

const slash = (p: string) => p.replaceAll('\\', '/');
const HERE = slash(path.dirname(fileURLToPath(import.meta.url)));
const APP = slash(path.resolve(HERE, '../..'));
const TMP = slash(process.env.WT_TMP ?? path.join(os.tmpdir(), 'wt-e2e'));
const WEB_PORT = Number(process.env.WT_WEB_PORT ?? 5711);
const API_PORT = Number(process.env.WT_API_PORT ?? 8711);
const TARGET = process.env.E2E_TARGET === 'prototype' ? 'prototype' : 'app';

function projectArgs(): string[] {
  const out: string[] = [];
  const argv = process.argv;
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i]!;
    if (a === '--project' && argv[i + 1]) out.push(argv[i + 1]!);
    else if (a.startsWith('--project=')) out.push(a.slice('--project='.length));
  }
  return out;
}
const projects = projectArgs();
process.env.WT_E2E_PROJECTS = projects.join(',');   // read by global-setup.ts (same process)
const defaultServe = projects.length && projects.every(p => p === 'harness') ? 'harness'
  : TARGET === 'prototype' || (projects.length && projects.every(p => p === 'scaffold')) ? ''
  : 'api,web';
const serve = new Set((process.env.WT_SERVE ?? defaultServe).split(',').map(s => s.trim()).filter(Boolean));

const childEnv = (extra: Record<string, string>) => ({ ...process.env, WT_TMP: TMP, ...extra }) as Record<string, string>;
const webServer: NonNullable<PlaywrightTestConfig['webServer']> = [];
if (serve.has('api')) {
  webServer.push({
    command: `node tools/run-api.mjs --port ${API_PORT} --data "${TMP}/data" --copy-data-from data`,
    cwd: APP,
    url: `http://127.0.0.1:${API_PORT}/api/health`,
    reuseExistingServer: false,
    timeout: 60_000,
    env: childEnv({}),
  });
}
if (serve.has('web')) {
  webServer.push({
    command: `npx vite -c apps/web/vite.config.ts --port ${WEB_PORT} --strictPort`,
    cwd: APP,
    url: `http://127.0.0.1:${WEB_PORT}/`,
    reuseExistingServer: false,
    timeout: 120_000,
    env: childEnv({ WT_API_PORT: String(API_PORT), VITE_WTV_TEST_HOOK: '1' }),
  });
}
if (serve.has('harness')) {
  webServer.push({
    command: `npm run harness -- --port ${WEB_PORT}`,
    cwd: APP,
    url: `http://127.0.0.1:${WEB_PORT}/`,
    reuseExistingServer: false,
    timeout: 120_000,
    env: childEnv({}),
  });
}

export default defineConfig({
  outputDir: `${TMP}/pw-results`,
  globalSetup: `${HERE}/global-setup.ts`,
  globalTeardown: `${HERE}/global-teardown.ts`,
  workers: 1,
  fullyParallel: false,
  retries: 0,
  // Behaviour this design changes on purpose is checked only on the app (DESIGN.md 17.4).
  grepInvert: TARGET === 'prototype' ? /@app-only/ : undefined,
  timeout: 120_000,
  expect: { timeout: 15_000 },
  forbidOnly: true,
  reporter: [
    ['list'],
    ['json', { outputFile: `${TMP}/pw-report/results.json` }],
    ['html', { outputFolder: `${TMP}/pw-report/html`, open: 'never' }],
  ],
  use: {
    channel: 'msedge',
    headless: true,
    viewport: { width: 1400, height: 880 },
    acceptDownloads: true,
    baseURL: `http://127.0.0.1:${WEB_PORT}`,
    trace: 'retain-on-failure',
    launchOptions: {
      args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--allow-file-access-from-files'],
    },
  },
  webServer,
  projects: [
    { name: 'e2e', testDir: HERE, testMatch: /tests[\\/]e2e[\\/][^\\/]+\.spec\.ts$/ },
    { name: 'harness', testDir: `${APP}/packages/viewer/test/harness`, testMatch: /\.spec\.ts$/ },
    { name: 'scaffold', testDir: `${HERE}/lib`, testMatch: /smoke-[^\\/]+\.spec\.ts$/ },
  ],
});
