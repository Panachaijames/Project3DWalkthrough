// Shared helpers of the app's tools (scaffold). Paths are absolute; the app folder is the parent of tools/.
import { existsSync } from 'node:fs';
import net from 'node:net';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

export const APP = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
export const PROTOTYPES = path.resolve(APP, '..');

/** The API venv's Python (services/api/.venv). */
export function venvPython() {
  for (const p of ['services/api/.venv/Scripts/python.exe', 'services/api/.venv/bin/python']) {
    const abs = path.join(APP, p);
    if (existsSync(abs)) return abs;
  }
  throw new Error(`no Python venv under ${path.join(APP, 'services/api/.venv')}: see app/README.md (setup)`);
}

/** The environment the app's own Python runs with (DESIGN.md 2). */
export function pyEnv(extra = {}) {
  // pytest's cache (last-failed, node ids) under the run's WT_TMP, or none: never services/api/.pytest_cache inside app/
  // (D-3: everything a run writes goes under its WT_TMP; fix step, 3 Nov code review). pyproject.toml is frozen, so it
  // goes in through PYTEST_ADDOPTS (shlex-split by pytest: forward slashes, single quotes).
  const cache = process.env.WT_TMP
    ? `-o 'cache_dir=${path.join(process.env.WT_TMP, 'pytest-cache').replaceAll('\\', '/')}'`
    : '-p no:cacheprovider';
  return {
    ...process.env,
    PYTHONPATH: path.join(APP, 'services', 'api'),
    PYTHONIOENCODING: 'utf-8',
    PYTHONUTF8: '1',
    PYTHONDONTWRITEBYTECODE: '1',
    PYTEST_ADDOPTS: [process.env.PYTEST_ADDOPTS, cache].filter(Boolean).join(' '),
    ...extra,
  };
}

/** The builder's Python (docs/upload/DESIGN.md U-10.1): WALKTHROUGH_BUILDER_PYTHON (relative to app/ or absolute), by
 *  default the pinned venv services/builder/.venv. The venv is the only supported path; the system Python may stand in
 *  for a diagnosis only (its libraries are in the user site, so nothing here passes -I, -E or -s). */
export function builderPython() {
  const set = process.env.WALKTHROUGH_BUILDER_PYTHON;
  const candidates = set ? [set] : ['services/builder/.venv/Scripts/python.exe', 'services/builder/.venv/bin/python'];
  for (const p of candidates) {
    const abs = path.resolve(APP, p);
    if (existsSync(abs)) return abs;
  }
  throw new Error(`no builder Python at ${path.resolve(APP, candidates[0])}: see app/README.md (setup), or set WALKTHROUGH_BUILDER_PYTHON`);
}

/** The environment of every builder process (U-3.5, U-10.1): PYTHONPATH=services/builder, UTF-8 I/O, no bytecode, one
 *  OpenBLAS / OpenMP thread, matplotlib's Agg backend, and pytest's cache under WT_TMP (or none), as pyEnv does. */
export function builderEnv(extra = {}) {
  const cache = process.env.WT_TMP
    ? `-o 'cache_dir=${path.join(process.env.WT_TMP, 'pytest-cache').replaceAll('\\', '/')}'`
    : '-p no:cacheprovider';
  const env = {
    ...process.env,
    PYTHONPATH: path.join(APP, 'services', 'builder'),
    PYTHONIOENCODING: 'utf-8',
    PYTHONUTF8: '1',
    PYTHONDONTWRITEBYTECODE: '1',
    OPENBLAS_NUM_THREADS: '1',
    OMP_NUM_THREADS: '1',
    MPLBACKEND: 'Agg',
    PYTEST_ADDOPTS: [process.env.PYTEST_ADDOPTS, cache].filter(Boolean).join(' '),
    ...extra,
  };
  // never hide the user site from a stand-in system Python (U-10.1)
  delete env.PYTHONNOUSERSITE;
  return env;
}

/** Resolves true when nothing listens on 127.0.0.1:port (a bind test on the address every server here uses). */
export function portIsFree(port, host = '127.0.0.1') {
  return new Promise(resolve => {
    const srv = net.createServer();
    srv.once('error', () => resolve(false));
    srv.listen({ port, host, exclusive: true }, () => srv.close(() => resolve(true)));
  });
}

/** Exits with a message when the port is taken (every runner checks its port first: WORK_BREAKDOWN 0). */
export async function requireFreePort(port, who) {
  if (!(await portIsFree(port))) {
    console.error(`${who}: port ${port} on 127.0.0.1 is in use; stop whatever holds it or pick your own port (DESIGN.md 3)`);
    process.exit(1);
  }
}

/** Minimal --flag value / --switch parser. */
export function parseArgs(argv, { flags = [], switches = [] } = {}) {
  const out = { _: [] };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    const eq = a.indexOf('=');
    const name = a.startsWith('--') ? (eq > 0 ? a.slice(2, eq) : a.slice(2)) : null;
    if (name && flags.includes(name)) out[name] = eq > 0 ? a.slice(eq + 1) : argv[++i];
    else if (name && switches.includes(name)) out[name] = true;
    else out._.push(a);
  }
  return out;
}
