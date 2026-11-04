#!/usr/bin/env node
// Starts the API: uvicorn walkthrough_api.main:app on 127.0.0.1 from the venv, cwd app/ (DESIGN.md 2).
//   node tools/run-api.mjs --port 8710 [--reload] [--data <dir>] [--copy-data-from <dir>]
// WALKTHROUGH_DATA_DIR is `data` (app/data) unless set in the environment or given with --data. With --copy-data-from,
// the --data folder is first replaced by a fresh copy of that folder: Playwright's web server for the web specs uses it
// to serve a temp copy of app/data (Playwright starts web servers before globalSetup; DESIGN.md 18.42). The port is
// checked first: a taken port stops the run with a message.
import { spawn } from 'node:child_process';
import { cpSync, existsSync, rmSync } from 'node:fs';
import path from 'node:path';
import { APP, parseArgs, pyEnv, requireFreePort, venvPython } from './lib.mjs';

const args = parseArgs(process.argv.slice(2), { flags: ['port', 'data', 'copy-data-from'], switches: ['reload'] });
const port = Number(args.port ?? 8710);
if (!Number.isInteger(port) || port <= 0) { console.error(`run-api: bad --port ${args.port}`); process.exit(2); }
await requireFreePort(port, 'run-api');

const env = pyEnv();
if (args.data) env.WALKTHROUGH_DATA_DIR = args.data;
else env.WALKTHROUGH_DATA_DIR ??= 'data';

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

const uvicorn = ['-m', 'uvicorn', 'walkthrough_api.main:app', '--host', '127.0.0.1', '--port', String(port)];
if (args.reload) uvicorn.push('--reload', '--reload-dir', 'services/api/walkthrough_api');
console.log(`run-api: http://127.0.0.1:${port} (data ${env.WALKTHROUGH_DATA_DIR})`);
const child = spawn(venvPython(), uvicorn, { cwd: APP, env, stdio: 'inherit' });
for (const sig of ['SIGINT', 'SIGTERM']) process.on(sig, () => child.kill(sig));
child.on('error', err => { console.error(`run-api: ${err.message}`); process.exit(1); });
child.on('exit', (code, signal) => process.exit(code ?? (signal ? 1 : 0)));
