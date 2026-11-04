#!/usr/bin/env node
// Runs the app's own Python (services/api/.venv) with cwd = app/, PYTHONPATH=services/api, PYTHONIOENCODING=utf-8,
// PYTHONUTF8=1 and PYTHONDONTWRITEBYTECODE=1 (no __pycache__ anywhere), passing every argument through; exits with
// Python's exit code (DESIGN.md 2). Prototype Python (shapely) runs with the SYSTEM Python and -B instead.
//   node tools/run-py.mjs -m pytest services/api/tests -q
import { spawn } from 'node:child_process';
import { APP, pyEnv, venvPython } from './lib.mjs';

const child = spawn(venvPython(), process.argv.slice(2), { cwd: APP, env: pyEnv(), stdio: 'inherit' });
for (const sig of ['SIGINT', 'SIGTERM']) process.on(sig, () => child.kill(sig));
child.on('error', err => { console.error(`run-py: ${err.message}`); process.exit(1); });
child.on('exit', (code, signal) => process.exit(code ?? (signal ? 1 : 0)));
