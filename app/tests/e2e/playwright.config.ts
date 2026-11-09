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
// globalSetup, so the API's server command makes its store itself (DESIGN.md 18.42).
// The upload milestone (docs/upload/DESIGN.md U-15.1, U-15.3; its scaffold U0): the API serves a FRESHLY SEEDED store in
// WT_TMP/data (`run-api.mjs --seed-fresh`, from the prototype folders; 180 s for the seed), so every run starts from the
// four seeded projects (specs that add projects use ids e2e-*); the builder's settings and WALKTHROUGH_CACHE_DIR =
// WT_TMP/cache go to the API and its worker; WT_UPLOAD_OFFLINE_DIR (the uploaded versions' offline files for
// upload-walk.spec.ts) passes through; globalTeardown cancels every open run through the API (U-3.4) before it lets go
// of the Edge lock.
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
  process.env.WT_E2E_API = `http://127.0.0.1:${API_PORT}`;   // read by global-teardown.ts (same process): cancel open runs
  webServer.push({
    command: `node tools/run-api.mjs --port ${API_PORT} --data "${TMP}/data" --seed-fresh`,
    cwd: APP,
    url: `http://127.0.0.1:${API_PORT}/api/health`,
    reuseExistingServer: false,
    timeout: 180_000,
    env: childEnv({
      WALKTHROUGH_CACHE_DIR: `${TMP}/cache`,
      WALKTHROUGH_BUILDER_PYTHON: process.env.WALKTHROUGH_BUILDER_PYTHON ?? 'services/builder/.venv/Scripts/python.exe',
      WALKTHROUGH_LIBREDWG_DIR: process.env.WALKTHROUGH_LIBREDWG_DIR ?? 'vendor/libredwg-0.14-win64',
      ...(process.env.WT_UPLOAD_OFFLINE_DIR ? { WT_UPLOAD_OFFLINE_DIR: process.env.WT_UPLOAD_OFFLINE_DIR } : {}),
    }),
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
