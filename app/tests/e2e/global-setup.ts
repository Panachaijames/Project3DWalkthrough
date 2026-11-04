// Playwright globalSetup (DESIGN.md 17.4): takes the machine-wide Edge lock (released by global-teardown.ts) and, for
// the real app run (E2E_TARGET=app with the e2e project), checks that the seed and the offline files exist. The temp
// data copy for the web specs is made by the API server's command (playwright.config.ts), which Playwright starts first.
// WT_SKIP_STORE_CHECK=1 skips the check (a builder running web specs against a mock API, before the seed exists).
import { existsSync, readdirSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { acquire } from '../../tools/edge-lock.mjs';

const APP = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');

export default async function globalSetup(): Promise<void> {
  await acquire(process.env.WT_STEP ?? `playwright (${process.env.WT_TMP ?? 'wt-e2e'})`);

  // Set by playwright.config.ts in this same process: the --project names given (empty = all).
  const projects = (process.env.WT_E2E_PROJECTS ?? '').split(',').filter(Boolean);
  const runsE2e = projects.length === 0 || projects.includes('e2e');
  if (process.env.E2E_TARGET === 'prototype' || !runsE2e || process.env.WT_SKIP_STORE_CHECK === '1') return;
  const missing: string[] = [];
  const store = path.join(APP, 'data', 'projects');
  if (!existsSync(store) || readdirSync(store).length === 0) missing.push('app/data/projects (run `npm run seed`)');
  const offline = path.join(APP, 'dist', 'offline');
  if (!existsSync(offline) || !readdirSync(offline).some(f => f.endsWith('.html'))) {
    missing.push('app/dist/offline/*.html (run `npm run build:offline`)');
  }
  if (missing.length) {
    throw new Error(`E2E_TARGET=app needs the seeded store and the offline files first; missing: ${missing.join('; ')}`);
  }
}
