#!/usr/bin/env node
// The acceptance runner of the rooms milestone (docs/rooms/WORK_BREAKDOWN.md R0 item 0; RI runs it). Scaffold R0.
//
//   node tools/rooms/acceptance/run.mjs --list
//   node tools/rooms/acceptance/run.mjs [--only <step>,<step>...] [--tmp <dir>] [--api-port 8748] [--web-port 5748]
//                                       [--out <result.json>] [--dry-run]
//
// upload-uf/ and upload-ur/ beside this file are the upload milestone's acceptance scripts exactly as its final check
// (UF) and its review (UR) ran them on 9 Nov 2026, copied from %TEMP%\wt-uf\scripts and %TEMP%\wt-ur\scripts, which can
// be cleared. They name those temp folders, the ports 5739 / 8739 and this machine's paths. This runner never edits
// them: for each step it writes a copy into <tmp>/scripts with
//   * %TEMP%\wt-uf and %TEMP%\wt-ur            -> <tmp> (default %TEMP%\wt-ri\acceptance), so both sets share one store;
//   * "$W/scripts/..." and "$W/acc/cases/..."  -> the step's own folder here (the scripts and cases are read in place);
//   * the ports 8739 and 5739                  -> --api-port and --web-port (RI's 8748 / 5748; never 8710 / 5710);
//   * the app folder                           -> this checkout's;
// runs it with bash (or node, for .mjs) from app/, and records its exit code, its seconds and the tail of its output.
// ONE JSON result is written at the end (and after every step, so a stopped run leaves what it had):
//   { format: 'rooms-acceptance/1', startedAt, finishedAt, tmp, ports, steps: [{ name, script, kind, exit, seconds, tail }] }
// `--dry-run` writes the copies and the result with every step "not run". Order matters: `acceptance` seeds a fresh
// store under <tmp>/acc and the later steps read it; `offline` needs `npm run build:offline:template` first (it reads
// dist/offline-template, which only the integration step writes).
//
// THE NEW STEPS of this milestone (the *-rooms builds, the gap report's new rows, upload-walk on the old versions against
// docs/rooms/reference/upload-walk-9nov/, the two-process builds) are RI's to add: append them to NEW_STEPS below, each
// { name, kind: 'new', run: [command, ...args] } run from app/ with WT_TMP = <tmp>.
import { spawnSync } from 'node:child_process';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const APP = path.resolve(HERE, '..', '..', '..');
const posix = p => p.replaceAll('\\', '/');
/** A Git Bash path: C:/x -> /c/x. */
const bashPath = p => posix(p).replace(/^([A-Za-z]):/, (_m, d) => `/${d.toLowerCase()}`);

/** The upload milestone's steps, in the order its integration ran them. */
const OLD_STEPS = [
  { name: 'suites', script: 'upload-ur/suites.sh', what: 'check:pins, typecheck, unit, builder, API, API with WT_INTEGRATION=1' },
  { name: 'acceptance', script: 'upload-ur/acceptance.sh', what: 'a served API over a freshly seeded store, the real worker, the eleven cases, A-9' },
  { name: 'acceptance-a12', script: 'upload-ur/acceptance-a12.sh', what: 'the two A-12 cases again with the office mapping' },
  { name: 'checks', script: 'upload-uf/acc-checks.sh', what: 'A-1, A-3 / A-4, A-8, A-9, A-10 and the version rows on the recorded cases' },
  { name: 'bank-time', script: 'upload-ur/bank-time.sh', what: "A-10: the bank's prepare on a cold cache" },
  { name: 'offline', script: 'upload-uf/offline.sh', what: 'the offline file of each of the eight saved versions' },
  { name: 'e2e', script: 'upload-ur/e2e.sh', what: 'every browser spec, the walk checks on the acceptance store' },
  { name: 'proto-tests', script: 'upload-ur/proto-tests.mjs', what: "the prototypes' own tests, one at a time under the Edge lock" },
];
/** RI's: the steps this milestone adds (tools/rooms/acceptance/rooms/; each run from app/ with WT_TMP = <tmp>). The new
 * steps' store is <tmp>/data, a copy of R0's copy of the upload milestone's store (%TEMP%\wt-r0\acc-9nov, made by
 * `rooms-builds` when missing), so one store holds the eight old versions and the new ones; the old `acceptance` step
 * keeps its own freshly seeded store under <tmp>/acc. */
const R = 'tools/rooms/acceptance/rooms';
const NEW_STEPS = [
  { name: 'rooms-builds', run: ['bash', `${R}/builds.sh`],
    what: 'the five drawings with the new rule, the tower and the new suite with their single lines set aside, RA-13 (served API, real worker)' },
  { name: 'rooms-offline', run: ['bash', `${R}/offline.sh`], what: 'the offline file of each new-rule version (dist template)' },
  { name: 'rooms-walks', run: ['bash', `${R}/walks.sh`],
    what: 'upload-walk with RA-6\'s probes and stairs.spec (RA-8, RA-10, RA-14 fpsGpu) on the new-rule files, in Edge' },
  { name: 'rooms-node', run: ['bash', `${R}/node.sh`], what: 'climb.test.ts on the real new-rule models, with the times (RA-10, RA-14)' },
  { name: 'rooms-golden', run: ['bash', `${R}/golden.sh`],
    what: 'WT_ACCEPTANCE=1: test_r_rooms_golden.py (RA-15, two processes) and every door undone (RA-18)' },
  { name: 'rooms-checks', run: ['node', 'tools/run-builder-py.mjs', `${R}/checks.py`],
    what: 'the result of RA-1 - RA-18 from the records into <tmp>/rooms-result.json (GAPS.md is written from it)' },
  { name: 'reference-checks', run: ['bash', `${R}/reference.sh`], what: 'outside.txt, versions.sha1, no new __pycache__ (RA-2, RA-16)' },
].map(s => ({ ...s, kind: 'new' }));

function args(argv) {
  const a = { only: null, tmp: path.join(os.tmpdir(), 'wt-ri', 'acceptance'), api: 8748, web: 5748, out: null, list: false, dry: false };
  for (let i = 0; i < argv.length; i++) {
    const k = argv[i];
    if (k === '--list') a.list = true;
    else if (k === '--dry-run') a.dry = true;
    else if (k === '--only') a.only = argv[++i].split(',');
    else if (k === '--tmp') a.tmp = path.resolve(argv[++i]);
    else if (k === '--api-port') a.api = Number(argv[++i]);
    else if (k === '--web-port') a.web = Number(argv[++i]);
    else if (k === '--out') a.out = path.resolve(argv[++i]);
    else { console.error(`unknown argument ${k}`); process.exit(2); }
  }
  a.out ??= path.join(a.tmp, 'result.json');
  return a;
}

/** The text of one of the upload milestone's scripts, pointed at <tmp>, this checkout and these ports. */
export function retarget(text, { set, tmp, api, web }) {
  // RI: <tmp> as C:/... (Git Bash takes it, and so does a Windows Python given it inside `python -c` code, as
  // acc-checks.sh's A-9 print does; a /c/... path there is not found)
  const W = posix(tmp), dir = bashPath(path.join(HERE, set));
  return text
    .replaceAll(/"\$W\/scripts\//g, `"${dir}/`)
    .replaceAll(/\$W\/acc\/cases/g, `${dir}/cases`)
    .replaceAll(/\$TEMP\/wt-u[fr]/g, W)
    .replaceAll(/path\.join\(process\.env\.TEMP, 'wt-u[fr]',/g, `path.join(${JSON.stringify(posix(tmp))},`)
    .replaceAll(/os\.path\.join\(os\.environ\['TEMP'\],'wt-u[fr]',/g, `os.path.join(r'${posix(tmp)}',`)
    .replaceAll('/c/Users/DWP2/Desktop/Project walkthrough/app', bashPath(APP))
    .replaceAll("'C:/Users/DWP2/Desktop/Project walkthrough'", JSON.stringify(posix(path.resolve(APP, '..'))))
    .replaceAll(/\b8739\b/g, String(api))
    .replaceAll(/\b5739\b/g, String(web));
}

function main() {
  const a = args(process.argv.slice(2));
  const steps = [...OLD_STEPS.map(s => ({ ...s, kind: 'upload' })), ...NEW_STEPS];
  if (a.list) {
    for (const s of steps) console.log(`${s.name.padEnd(16)} ${s.kind.padEnd(7)} ${s.script ?? s.run.join(' ')}${s.what ? `  (${s.what})` : ''}`);
    return 0;
  }
  if ([5710, 8710].includes(a.api) || [5710, 8710].includes(a.web)) { console.error('never the owner\'s ports 5710 / 8710'); return 2; }
  if (posix(a.tmp).startsWith(posix(path.join(APP, 'data')))) { console.error('never app/data'); return 2; }
  const unknown = (a.only ?? []).filter(n => !steps.some(s => s.name === n));
  if (unknown.length) { console.error(`unknown step(s): ${unknown.join(', ')} (see --list)`); return 2; }
  for (const d of ['scripts', 'logs', 'acc']) mkdirSync(path.join(a.tmp, d), { recursive: true });
  const result = { format: 'rooms-acceptance/1', startedAt: new Date().toISOString(), finishedAt: null, tmp: posix(a.tmp),
    ports: { api: a.api, web: a.web }, dryRun: a.dry, steps: [] };
  // RI: with --only, the rows of the other steps already in the result file are kept (one result file for a run made in
  // parts); the rows of the steps run now are replaced.
  if (a.only && !a.dry) {
    try {
      const prev = JSON.parse(readFileSync(a.out, 'utf8'));
      if (prev.format === result.format) {
        result.startedAt = prev.startedAt ?? result.startedAt;
        result.steps = (prev.steps ?? []).filter(r => !a.only.includes(r.name));
      }
    } catch { /* no result file yet */ }
  }
  const save = () => {
    mkdirSync(path.dirname(a.out), { recursive: true });
    if (a.only && !a.dry) {                     // RI: another runner with --only may have written its rows meanwhile
      try {
        const now = JSON.parse(readFileSync(a.out, 'utf8'));
        const theirs = (now.steps ?? []).filter(r => !a.only.includes(r.name));
        const order = [...OLD_STEPS, ...NEW_STEPS].map(s => s.name);
        result.steps = [...theirs, ...result.steps.filter(r => a.only.includes(r.name))]
          .sort((x, y) => order.indexOf(x.name) - order.indexOf(y.name));
      } catch { /* none yet */ }
    }
    writeFileSync(a.out, `${JSON.stringify(result, null, 2)}\n`);
  };
  let failed = 0;
  for (const s of steps) {
    if (a.only && !a.only.includes(s.name)) continue;
    let cmd, argv;
    if (s.script) {
      const [set] = s.script.split('/');
      const copy = path.join(a.tmp, 'scripts', s.script.replace('/', '--'));
      writeFileSync(copy, retarget(readFileSync(path.join(HERE, s.script), 'utf8'), { set, tmp: a.tmp, api: a.api, web: a.web }));
      [cmd, argv] = s.script.endsWith('.mjs') ? [process.execPath, [copy]] : ['bash', [bashPath(copy)]];
    } else {
      [cmd, ...argv] = s.run;
    }
    const row = { name: s.name, kind: s.kind, script: s.script ?? s.run.join(' '), exit: null, seconds: null, tail: '' };
    result.steps.push(row);
    if (!a.dry) {
      console.log(`== ${s.name} ...`);
      const t0 = Date.now();
      const r = spawnSync(cmd, argv, { cwd: APP, env: { ...process.env, WT_TMP: a.tmp }, encoding: 'utf8', maxBuffer: 256 * 1024 * 1024 });
      row.exit = r.error ? -1 : r.status;
      row.seconds = Math.round((Date.now() - t0) / 100) / 10;
      const text = `${r.stdout ?? ''}${r.stderr ?? ''}${r.error ? `\n${r.error.message}` : ''}`;
      writeFileSync(path.join(a.tmp, 'logs', `${s.name}.txt`), text);
      row.tail = text.trim().split(/\r?\n/).slice(-12).join('\n');
      failed += row.exit === 0 ? 0 : 1;
      console.log(`== ${s.name}: exit ${row.exit} (${row.seconds} s)`);
    }
    save();
  }
  result.finishedAt = new Date().toISOString();
  save();
  console.log(`${a.dry ? 'dry run: ' : ''}${result.steps.length} step(s), ${failed} failed; result ${a.out}`);
  return failed ? 1 : 0;
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) process.exit(main());
