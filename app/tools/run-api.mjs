#!/usr/bin/env node
// Starts the API: uvicorn walkthrough_api.main:app on 127.0.0.1 from the venv, cwd app/ (DESIGN.md 2).
//   node tools/run-api.mjs --port 8710 [--reload (refused on Windows)] [--data <dir>] [--copy-data-from <dir>] [--seed-fresh]
// WALKTHROUGH_DATA_DIR is `data` (app/data) unless set in the environment or given with --data. With --copy-data-from,
// the --data folder is first replaced by a fresh copy of that folder: Playwright's web server for the web specs uses it
// to serve a temp copy of app/data (Playwright starts web servers before globalSetup; DESIGN.md 18.42). With
// --seed-fresh (the upload milestone, docs/upload/DESIGN.md U-15.3), the --data folder is first replaced by a freshly
// seeded store (`walkthrough_api.seed` from the prototype folders, read only), so every e2e run starts from the four seeded
// projects; it refuses app/data itself (it holds the furniture heights staff saved). The port is checked first: a taken
// port stops the run with a message. The builder's settings (WALKTHROUGH_BUILDER_PYTHON, WALKTHROUGH_LIBREDWG_DIR,
// WALKTHROUGH_CACHE_DIR, WALKTHROUGH_CACHE_MAX_GB, WALKTHROUGH_UPLOAD_MAX_BYTES, WALKTHROUGH_RUN_LOCK; U-13.5) pass
// through from the environment to the API, which hands them to the worker.
import { spawn, spawnSync } from 'node:child_process';
import { cpSync, existsSync, rmSync } from 'node:fs';
import path from 'node:path';
import { APP, PROTOTYPES, parseArgs, pyEnv, requireFreePort, venvPython } from './lib.mjs';

const args = parseArgs(process.argv.slice(2), { flags: ['port', 'data', 'copy-data-from'], switches: ['reload', 'seed-fresh'] });
if (args.reload && process.platform === 'win32') {
  // npm run dev no longer passes --reload (10 Nov 2026): on Windows uvicorn restarts its server with a CTRL_C_EVENT,
  // which reaches every program in the same terminal, this script included (its SIGINT handler then ends uvicorn), so
  // in the owner's PowerShell one saved .py file stopped the API, the web server and npm itself, and a terminal of its
  // own would not help (docs/upload/contract-issues/UI.md, UI-5). Refused rather than dropped: parseArgs ignores
  // unknown switches, so a dropped --reload would be accepted and silently do nothing.
  console.error('run-api: --reload does not work on Windows: uvicorn restarts its server with a Ctrl+C sent to the '
    + 'whole terminal, which stops this script and the API with it. Stop the API with Ctrl+C and start it again instead.');
  process.exit(2);
}
const port = Number(args.port ?? 8710);
if (!Number.isInteger(port) || port <= 0) { console.error(`run-api: bad --port ${args.port}`); process.exit(2); }
await requireFreePort(port, 'run-api');

const env = pyEnv();
if (args.data) env.WALKTHROUGH_DATA_DIR = args.data;
else env.WALKTHROUGH_DATA_DIR ??= 'data';

if (args['copy-data-from'] && args['seed-fresh']) {
  console.error('run-api: --copy-data-from and --seed-fresh are two ways to make the store: give one');
  process.exit(2);
}

if (args['copy-data-from']) {
  const from = path.resolve(APP, args['copy-data-from']);
  const to = path.resolve(APP, env.WALKTHROUGH_DATA_DIR);
  if (!existsSync(from)) { console.error(`run-api: no ${from} to copy (run npm run seed first)`); process.exit(1); }
  if (to === from || to.startsWith(from + path.sep) || from.startsWith(to + path.sep)) {
    console.error(`run-api: --data ${to} and --copy-data-from ${from} must be separate folders`);
    process.exit(2);
  }
  rmSync(to, { recursive: true, force: true });
  cpSync(from, to, { recursive: true });
  console.log(`run-api: copied ${from} -> ${to}`);
}

if (args['seed-fresh']) {
  const to = path.resolve(APP, env.WALKTHROUGH_DATA_DIR);
  const appData = path.resolve(APP, 'data');
  if (to === appData || to.startsWith(appData + path.sep) || appData.startsWith(to + path.sep)) {
    console.error(`run-api: --seed-fresh replaces the --data folder; it refuses ${to} (app/data holds staff-saved heights)`);
    process.exit(2);
  }
  rmSync(to, { recursive: true, force: true });
  const t0 = Date.now();
  const r = spawnSync(venvPython(), ['-m', 'walkthrough_api.seed', '--prototypes', PROTOTYPES, '--data', to, '--force'],
    { cwd: APP, env: pyEnv(), stdio: ['ignore', 'inherit', 'inherit'] });
  if (r.status !== 0) { console.error(`run-api: the seed into ${to} failed (exit ${r.status ?? r.signal})`); process.exit(1); }
  console.log(`run-api: seeded ${to} in ${((Date.now() - t0) / 1000).toFixed(1)} s`);
}

const uvicorn = ['-m', 'uvicorn', 'walkthrough_api.main:app', '--host', '127.0.0.1', '--port', String(port)];
if (args.reload) uvicorn.push('--reload', '--reload-dir', 'services/api/walkthrough_api');
console.log(`run-api: http://127.0.0.1:${port} (data ${env.WALKTHROUGH_DATA_DIR})`);
const child = spawn(venvPython(), uvicorn, { cwd: APP, env, stdio: 'inherit' });
for (const sig of ['SIGINT', 'SIGTERM']) process.on(sig, () => child.kill(sig));
child.on('error', err => { console.error(`run-api: ${err.message}`); process.exit(1); });
child.on('exit', (code, signal) => process.exit(code ?? (signal ? 1 : 0)));
