#!/usr/bin/env node
// Runs the builder's Python (services/builder/.venv, or WALKTHROUGH_BUILDER_PYTHON) with -B -P, cwd = app/,
// PYTHONPATH=services/builder, PYTHONIOENCODING=utf-8, PYTHONUTF8=1, PYTHONDONTWRITEBYTECODE=1, OPENBLAS_NUM_THREADS=1,
// OMP_NUM_THREADS=1, MPLBACKEND=Agg and pytest's cache under WT_TMP (docs/upload/DESIGN.md U-3.5, U-10.1), passing every
// argument through; exits with Python's exit code. Never -I, -E or -s: the builder relies on PYTHONPATH, and a stand-in
// system Python keeps its libraries in the user site.
//   node tools/run-builder-py.mjs -m pytest services/builder/tests -q
//   node tools/run-builder-py.mjs tools/upload/make-reference.py --out <dir>
import { spawn } from 'node:child_process';
import { APP, builderEnv, builderPython } from './lib.mjs';

let python;
try { python = builderPython(); } catch (err) { console.error(`run-builder-py: ${err.message}`); process.exit(1); }
const child = spawn(python, ['-B', '-P', ...process.argv.slice(2)], { cwd: APP, env: builderEnv(), stdio: 'inherit' });
for (const sig of ['SIGINT', 'SIGTERM']) process.on(sig, () => child.kill(sig));
child.on('error', err => { console.error(`run-builder-py: ${err.message}`); process.exit(1); });
child.on('exit', (code, signal) => process.exit(code ?? (signal ? 1 : 0)));
