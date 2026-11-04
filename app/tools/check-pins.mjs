#!/usr/bin/env node
// `npm run check:pins` (DESIGN.md 2, 4; WORK_BREAKDOWN S.2): exits 1 unless
//  * every package of the frozen list (D-4.1, D-4.2) is declared with exactly its version (no range) in the package.json
//    that owns it, and the copy that workspace's code resolves (<workspace>/node_modules first, then app/node_modules)
//    is exactly that version. Other copies in package-lock.json (dependencies of a tool, e.g. the shadcn CLI's own
//    cn 0.2.6) are listed for information: our code never resolves them;
//  * `pip freeze` of services/api/.venv equals services/api/requirements.lock.txt (names compared PEP 503-normalised:
//    lower case, runs of -, _ and . as one -; pip prints pydantic_core, Pygments, typing_extensions).
// The table below IS the frozen list; app/CLAUDE.md repeats it. Nothing is added, removed or upgraded without the owner.
import { execFileSync } from 'node:child_process';
import { existsSync, readFileSync } from 'node:fs';
import path from 'node:path';
import { APP, venvPython } from './lib.mjs';

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

console.log(`node ${process.versions.node}, npm pins ${Object.keys(NPM_PINS).length}, python pins ${lockPins.size} (pip freeze lists ${frozen.size})`);
for (const n of notes) console.log(`check-pins: note: ${n}`);
if (problems.length) {
  for (const p of problems) console.error(`check-pins: ${p}`);
  process.exit(1);
}
console.log('check-pins: ok (every installed version equals the frozen list)');
