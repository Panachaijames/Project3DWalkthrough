// The prototypes' own tests, unchanged, one at a time under the Edge lock (WORK_BREAKDOWN UI step 6; the foundation's I.7
// list plus the detector's own scores, ACCEPTANCE A-11). Logs go to %TEMP%\wt-ui\proto\<name>.txt. Usage: node proto-tests.mjs
import { spawnSync } from 'node:child_process';
import { mkdirSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const ROOT = 'C:/Users/DWP2/Desktop/Project walkthrough';
const OUT = path.join(process.env.TEMP, 'wt-uf', 'proto');
mkdirSync(OUT, { recursive: true });
const { acquire, release } = await import(pathToFileURL(`${ROOT}/app/tools/edge-lock.mjs`).href);
const PY = 'C:/Python314/python.exe';
const REF = path.join(process.env.TEMP, 'wt-u0', 'ref', 'proj', 'detector');
const RUNS = [
  ['viewers', 'node', ['viewer-modes/test_viewers.mjs']],
  ['bank', 'node', ['bank_test/test_bank.mjs']],
  ['suite', 'node', ['presidential_test/test_presidential.mjs']],
  ['house-openings', 'node', ['cad_test/test_house_openings.mjs']],
  ['house-furniture', 'node', ['cad_test/test_house_furniture.mjs']],
  ['hotel', 'node', ['hotel_test/test_hotel.mjs']],
  ['boxes', 'node', ['furniture/test_boxes.mjs']],
  ['max-bank', PY, ['-B', 'bank_test/test_bank_maxscript.py']],
  ['max-suite', PY, ['-B', 'presidential_test/test_presidential_maxscript.py']],
  ['max-hotel', PY, ['-B', 'hotel_test/test_hotel_maxscript.py']],
  ['detector', PY, ['-B', 'detector/run_all.py', path.join(OUT, 'detector-run')], { OPENINGS_DATA: REF }],
];
const only = process.argv.slice(2);
await acquire('uf-prototype-tests');
const summary = [];
try {
  for (const [name, cmd, args, env] of RUNS) {
    if (only.length && !only.includes(name)) continue;
    const t0 = Date.now();
    const r = spawnSync(cmd, args, { cwd: ROOT, env: { ...process.env, PYTHONIOENCODING: 'utf-8', ...(env ?? {}) },
      encoding: 'utf8', maxBuffer: 64 * 1024 * 1024, timeout: 30 * 60_000 });
    const text = `${r.stdout ?? ''}\n----- stderr -----\n${r.stderr ?? ''}`;
    writeFileSync(path.join(OUT, `${name}.txt`), text);
    const tail = text.trim().split(/\r?\n/).filter(Boolean).slice(-4).join(' | ');
    summary.push({ name, exit: r.status, seconds: Math.round((Date.now() - t0) / 1000), tail: tail.slice(0, 600) });
    console.log(`${r.status === 0 ? 'ok  ' : 'FAIL'} ${name} (exit ${r.status}, ${Math.round((Date.now() - t0) / 1000)} s): ${tail.slice(0, 300)}`);
  }
} finally {
  writeFileSync(path.join(OUT, 'summary.json'), JSON.stringify(summary, null, 1));
  release();
}
