#!/usr/bin/env node
// A tiny store that holds the reference building of the rooms milestone as one saved version (docs/rooms/ACCEPTANCE.md
// 2.5; scaffold R0), for the browser specs (tests/e2e/stairs.spec.ts, rooms.spec.ts):
//
//   node tools/rooms/make-fixture-store.mjs --out <dir> [--id rooms-reference] [--stairs]
//
// It runs tools/rooms/fixture_store.py in the API's own Python (services/api/.venv), so the store's own create_project
// and create_version write the files and every check the API makes on a saved version has passed. <dir> must be new or
// empty and is never app/data. `--stairs` adds the three synthetic stair models as projects of their own. Exit code:
// Python's.
import { spawnSync } from 'node:child_process';
import path from 'node:path';
import { APP, pyEnv, venvPython } from '../lib.mjs';

const args = process.argv.slice(2);
if (!args.includes('--out')) {
  console.error('usage: node tools/rooms/make-fixture-store.mjs --out <dir> [--id <project id>] [--stairs]');
  process.exit(2);
}
const r = spawnSync(venvPython(), ['-B', path.join(APP, 'tools', 'rooms', 'fixture_store.py'), ...args],
  { cwd: APP, env: pyEnv(), stdio: 'inherit' });
if (r.error) { console.error(`make-fixture-store: ${r.error.message}`); process.exit(1); }
process.exit(r.status ?? 1);
