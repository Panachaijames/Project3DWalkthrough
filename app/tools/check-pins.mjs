#!/usr/bin/env node
// `npm run check:pins` (DESIGN.md 2, 4; WORK_BREAKDOWN S.2): exits 1 unless
//  * every package of the frozen list (D-4.1, D-4.2) is declared with exactly its version (no range) in the package.json
//    that owns it, and the copy that workspace's code resolves (<workspace>/node_modules first, then app/node_modules)
//    is exactly that version. Other copies in package-lock.json (dependencies of a tool, e.g. the shadcn CLI's own
//    cn 0.2.6) are listed for information: our code never resolves them;
//  * `pip freeze` of services/api/.venv equals services/api/requirements.lock.txt (names compared PEP 503-normalised:
//    lower case, runs of -, _ and . as one -; pip prints pydantic_core, Pygments, typing_extensions);
//  * the upload milestone (docs/upload/DESIGN.md U-6.1, U-10.1; its scaffold U0): `pip freeze` of the builder's Python
//    (services/builder/.venv, or WALKTHROUGH_BUILDER_PYTHON) equals services/builder/requirements.lock.txt, and each
//    pinned package, IMPORTED in that interpreter, resolves to a file and its installed version equals the lock (so a
//    stand-in system Python with user-site libraries is caught too); every file of app/vendor/libredwg.manifest.json
//    (LibreDWG, extracted from its release zip) has its size and sha1.
// The table below IS the frozen list; app/CLAUDE.md repeats it. Nothing is added, removed or upgraded without the owner.
import { createHash } from 'node:crypto';
import { execFileSync } from 'node:child_process';
import { existsSync, readFileSync } from 'node:fs';
import path from 'node:path';
import { APP, builderEnv, builderPython, venvPython } from './lib.mjs';

export const NPM_PINS = {
  // D-4.1 runtime
  three: ['0.186.1', 'packages/viewer'],
  'three-mesh-bvh': ['0.9.16', 'packages/viewer'],
  react: ['19.3.1', 'apps/web'],
  'react-dom': ['19.3.1', 'apps/web'],
  'react-router': ['8.5.0', 'apps/web'],
  '@tanstack/react-query': ['5.104.5', 'apps/web'],
  'radix-ui': ['1.8.1', 'apps/web'],
  'class-variance-authority': ['0.7.1', 'apps/web'],
  cn: ['0.5.0', 'apps/web'],
  'lucide-react': ['1.59.0', 'apps/web'],
  tailwindcss: ['4.3.3', 'apps/web'],
  'tw-animate-css': ['1.4.0', 'apps/web'],
  // D-4.2 build and test (root devDependencies)
  typescript: ['6.0.3', '.'],
  vite: ['8.3.4', '.'],
  '@vitejs/plugin-react': ['6.1.2', '.'],
  'vite-plugin-singlefile': ['2.3.4', '.'],
  '@tailwindcss/vite': ['4.3.3', '.'],
  '@types/three': ['0.186.0', '.'],
  '@types/react': ['19.3.0', '.'],
  '@types/react-dom': ['19.3.0', '.'],
  '@types/node': ['24.19.2', '.'],
  '@hey-api/openapi-ts': ['0.99.0', '.'],
  shadcn: ['4.22.1', '.'],
  concurrently: ['10.0.6', '.'],
  vitest: ['5.0.5', '.'],
  'happy-dom': ['21.0.3', '.'],
  '@playwright/test': ['1.64.1', '.'],
  ajv: ['8.20.0', '.'],
};

const problems = [];
const notes = [];
const readJson = p => JSON.parse(readFileSync(p, 'utf8'));

// ---- npm
const lock = readJson(path.join(APP, 'package-lock.json'));
const manifests = {};
for (const ws of ['.', 'packages/viewer', 'apps/web']) manifests[ws] = readJson(path.join(APP, ws, 'package.json'));
for (const [name, [version, owner]] of Object.entries(NPM_PINS)) {
  const m = manifests[owner];
  const declared = (owner === '.' ? m.devDependencies : m.dependencies)?.[name];
  if (declared !== version) problems.push(`npm ${name}: ${owner}/package.json declares ${declared ?? 'nothing'}, the frozen list says ${version}`);
  const candidates = [...(owner === '.' ? [] : [path.join(owner, 'node_modules', name)]), path.join('node_modules', name)];
  const resolvedRel = candidates.find(rel => existsSync(path.join(APP, rel, 'package.json')));
  const installed = resolvedRel ? readJson(path.join(APP, resolvedRel, 'package.json')).version : null;
  if (installed !== version) problems.push(`npm ${name}: ${owner} resolves ${installed ?? 'nothing'}, the frozen list says ${version}`);
  for (const [key, entry] of Object.entries(lock.packages ?? {})) {
    if ((key === `node_modules/${name}` || key.endsWith(`/node_modules/${name}`)) && entry.version !== version) {
      const users = Object.entries(lock.packages).filter(([k, e]) => k && (e.dependencies?.[name] || e.peerDependencies?.[name]) && !k.startsWith('apps/') && !k.startsWith('packages/')).map(([k]) => k.replace(/^.*node_modules\//, ''));
      notes.push(`npm ${name}: another copy, ${key} ${entry.version}, used by ${users.join(', ') || '?'} (not resolved by ${owner})`);
    }
  }
}
for (const [ws, m] of Object.entries(manifests)) {
  for (const field of ['dependencies', 'devDependencies']) {
    for (const [name, spec] of Object.entries(m[field] ?? {})) {
      if (name.startsWith('@walkthrough/')) continue;
      if (!(name in NPM_PINS)) problems.push(`npm ${name}: in ${ws}/package.json ${field} but not on the frozen list`);
      if (!/^\d+\.\d+\.\d+$/.test(spec)) problems.push(`npm ${name}: ${ws}/package.json has the range "${spec}", not an exact version`);
    }
  }
}

// ---- Python
const norm = n => n.toLowerCase().replace(/[-_.]+/g, '-');
const parsePins = text => {
  const out = new Map();
  for (const raw of text.split(/\r?\n/)) {
    const line = raw.replace(/#.*/, '').trim();
    if (!line) continue;
    const m = /^([A-Za-z0-9][A-Za-z0-9._-]*)==([^\s;]+)$/.exec(line);
    if (!m) { problems.push(`python: cannot read the pin "${line}"`); continue; }
    out.set(norm(m[1]), m[2]);
  }
  return out;
};
const lockPins = parsePins(readFileSync(path.join(APP, 'services', 'api', 'requirements.lock.txt'), 'utf8'));
let frozen = new Map();
try {
  const text = execFileSync(venvPython(), ['-m', 'pip', 'freeze'], { cwd: APP, encoding: 'utf8', env: { ...process.env, PIP_DISABLE_PIP_VERSION_CHECK: '1', PYTHONIOENCODING: 'utf-8' } });
  frozen = parsePins(text);
} catch (err) {
  problems.push(`python: pip freeze failed: ${err.message}`);
}
for (const [name, version] of lockPins) {
  if (!frozen.has(name)) problems.push(`python ${name}: pinned ${version}, not installed`);
  else if (frozen.get(name) !== version) problems.push(`python ${name}: installed ${frozen.get(name)}, pinned ${version}`);
}
for (const [name, version] of frozen) if (!lockPins.has(name)) problems.push(`python ${name}: installed ${version}, not in requirements.lock.txt`);

// ---- the builder's Python (U-10.1)
//: PyPI distribution (normalised) -> the module it installs
const BUILDER_MODULES = {
  ezdxf: 'ezdxf', shapely: 'shapely', numpy: 'numpy', matplotlib: 'matplotlib', pillow: 'PIL', pytest: 'pytest',
  contourpy: 'contourpy', cycler: 'cycler', fonttools: 'fontTools', kiwisolver: 'kiwisolver', packaging: 'packaging',
  pyparsing: 'pyparsing', 'python-dateutil': 'dateutil', six: 'six', 'typing-extensions': 'typing_extensions',
  iniconfig: 'iniconfig', pluggy: 'pluggy', pygments: 'pygments', colorama: 'colorama',
};
const builderLock = parsePins(readFileSync(path.join(APP, 'services', 'builder', 'requirements.lock.txt'), 'utf8'));
let builderPy = null;
try { builderPy = builderPython(); } catch (err) { problems.push(`builder: ${err.message}`); }
let builderFrozen = new Map();
const builderModules = [];
if (builderPy) {
  const venv = path.join(APP, 'services', 'builder', '.venv');
  if (!path.resolve(builderPy).startsWith(path.resolve(venv) + path.sep)) {
    notes.push(`builder: WALKTHROUGH_BUILDER_PYTHON = ${builderPy}, not the pinned venv (a stand-in for a diagnosis only, U-10.1)`);
  }
  const penv = builderEnv({ PIP_DISABLE_PIP_VERSION_CHECK: '1' });
  try {
    builderFrozen = parsePins(execFileSync(builderPy, ['-B', '-m', 'pip', 'freeze'], { cwd: APP, encoding: 'utf8', env: penv }));
  } catch (err) {
    problems.push(`builder: pip freeze failed: ${err.message}`);
  }
  for (const [name, version] of builderLock) {
    if (!builderFrozen.has(name)) problems.push(`builder ${name}: pinned ${version}, not installed`);
    else if (builderFrozen.get(name) !== version) problems.push(`builder ${name}: installed ${builderFrozen.get(name)}, pinned ${version}`);
  }
  for (const [name, version] of builderFrozen) if (!builderLock.has(name)) problems.push(`builder ${name}: installed ${version}, not in services/builder/requirements.lock.txt`);
  const probe = [
    'import importlib, importlib.metadata as md, json, sys',
    `pairs = ${JSON.stringify(Object.entries(BUILDER_MODULES))}`,
    'out = {}',
    'for dist, mod in pairs:',
    '    try:',
    '        m = importlib.import_module(mod)',
    '        out[dist] = {"file": getattr(m, "__file__", None), "version": md.version(dist)}',
    '    except Exception as e:',
    '        out[dist] = {"error": f"{type(e).__name__}: {e}"}',
    'print(json.dumps({"python": sys.version.split()[0], "modules": out}))',
  ].join(String.fromCharCode(10));
  try {
    const res = JSON.parse(execFileSync(builderPy, ['-B', '-P', '-c', probe], { cwd: APP, encoding: 'utf8', env: builderEnv() }));
    if (res.python !== '3.14.3') problems.push(`builder: Python ${res.python}, pinned 3.14.3`);
    for (const [dist, info] of Object.entries(res.modules)) {
      const want = builderLock.get(dist);
      if (info.error) problems.push(`builder ${dist}: import ${BUILDER_MODULES[dist]} failed: ${info.error}`);
      else if (!info.file) problems.push(`builder ${dist}: ${BUILDER_MODULES[dist]} resolves to no file`);
      else if (want && info.version !== want) problems.push(`builder ${dist}: imports version ${info.version} from ${info.file}, pinned ${want}`);
      else builderModules.push(dist);
    }
    for (const dist of builderLock.keys()) if (!(dist in BUILDER_MODULES)) problems.push(`builder ${dist}: pinned, but check-pins does not know its module`);
  } catch (err) {
    problems.push(`builder: the import check failed: ${err.message}`);
  }
}

// ---- LibreDWG (U-6.1): the extracted files against the tracked manifest
const manPath = path.join(APP, 'vendor', 'libredwg.manifest.json');
let libredwgFiles = 0;
if (!existsSync(manPath)) problems.push('libredwg: no vendor/libredwg.manifest.json (npm run vendor:libredwg -- --zip <the release zip>)');
else {
  const man = readJson(manPath);
  const root = path.join(APP, man.folder);
  const rows = [...man.files, ...(man.licence?.sha1 ? [man.licence] : [])];
  for (const f of rows) {
    const p = path.join(root, f.path);
    if (!existsSync(p)) { problems.push(`libredwg: ${man.folder}/${f.path} is missing (npm run vendor:libredwg -- --zip <the release zip>)`); continue; }
    const data = readFileSync(p);
    const sha1 = createHash('sha1').update(data).digest('hex');
    if (data.length !== f.bytes || sha1 !== f.sha1) problems.push(`libredwg: ${man.folder}/${f.path} differs from the manifest`);
    else libredwgFiles++;
  }
  if (!man.licence?.sha1) notes.push('libredwg: the GPL-3.0 text (COPYING) is not fetched yet: the owner fetches it (vendor/LIBREDWG-LICENCE.txt)');
}

console.log(`node ${process.versions.node}, npm pins ${Object.keys(NPM_PINS).length}, python pins ${lockPins.size} (pip freeze lists ${frozen.size})`);
console.log(`builder pins ${builderLock.size} (pip freeze lists ${builderFrozen.size}, ${builderModules.length} imported at their pinned version), LibreDWG files ${libredwgFiles}`);
for (const n of notes) console.log(`check-pins: note: ${n}`);
if (problems.length) {
  for (const p of problems) console.error(`check-pins: ${p}`);
  process.exit(1);
}
console.log('check-pins: ok (every installed version equals the frozen list)');
